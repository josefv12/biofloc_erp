"""Gestión de usuarios. Escritura y lectura solo vía router ADMINISTRADOR."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.security import get_password_hash
from app.models.auditoria import Auditoria
from app.models.rol import Rol
from app.models.usuario import Usuario
from app.schemas.usuario import RolOut, UsuarioCreate, UsuarioOut, UsuarioUpdate

MENSAJE_ULTIMO_ADMIN = (
    "No se puede desactivar ni cambiar el rol del último administrador activo."
)


def _registrar_auditoria(db: Session, usuario_id: int, accion: str, registro_id: int, detalle: dict):
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            tabla="usuarios",
            registro_id=registro_id,
            accion=accion,
            detalle=detalle,
        )
    )


def _rol_nombre(db: Session, rol_id: int) -> Rol:
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if not rol.activo:
        raise HTTPException(status_code=409, detail=f"El rol '{rol.nombre}' no está activo")
    return rol


def _es_admin(db: Session, usuario: Usuario) -> bool:
    rol = db.query(Rol).filter(Rol.id == usuario.rol_id).first()
    return bool(rol and rol.nombre == "ADMINISTRADOR")


def _admins_activos(db: Session) -> int:
    return (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "ADMINISTRADOR", Usuario.activo.is_(True))
        .count()
    )


def _to_out(db: Session, row: Usuario) -> UsuarioOut:
    rol = db.query(Rol).filter(Rol.id == row.rol_id).first()
    return UsuarioOut(
        id=row.id,
        nombre=row.nombre,
        correo=row.correo,
        rol_id=row.rol_id,
        rol=rol.nombre if rol else "UNKNOWN",
        activo=row.activo,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def listar_roles(db: Session, solo_activos: bool = True) -> list[RolOut]:
    q = db.query(Rol)
    if solo_activos:
        q = q.filter(Rol.activo.is_(True))
    return [RolOut.model_validate(row) for row in q.order_by(Rol.id.asc()).all()]


def listar_usuarios(db: Session, solo_activos: bool = False) -> list[UsuarioOut]:
    q = db.query(Usuario)
    if solo_activos:
        q = q.filter(Usuario.activo.is_(True))
    filas = q.order_by(Usuario.nombre.asc(), Usuario.id.asc()).all()
    return [_to_out(db, row) for row in filas]


def obtener_usuario(db: Session, usuario_id: int) -> UsuarioOut:
    row = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _to_out(db, row)


def crear_usuario(db: Session, data: UsuarioCreate, actor_id: int) -> UsuarioOut:
    existente = db.query(Usuario).filter(Usuario.correo == data.correo).first()
    if existente:
        raise HTTPException(status_code=409, detail=f"Ya existe un usuario con el correo '{data.correo}'")
    rol = _rol_nombre(db, data.rol_id)
    row = Usuario(
        nombre=data.nombre,
        correo=data.correo,
        password_hash=get_password_hash(data.password),
        rol_id=rol.id,
        activo=data.activo,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear el usuario") from exc
    _registrar_auditoria(
        db,
        actor_id,
        "INSERT",
        row.id,
        {"nombre": row.nombre, "correo": row.correo, "rol_id": row.rol_id, "activo": row.activo},
    )
    db.commit()
    db.refresh(row)
    return _to_out(db, row)


def _protege_ultimo_admin(db: Session, row: Usuario, data: UsuarioUpdate) -> None:
    if not _es_admin(db, row) or not row.activo:
        return
    desactiva = data.activo is False
    cambia_rol = False
    if data.rol_id is not None and data.rol_id != row.rol_id:
        nuevo = _rol_nombre(db, data.rol_id)
        cambia_rol = nuevo.nombre != "ADMINISTRADOR"
    if (desactiva or cambia_rol) and _admins_activos(db) <= 1:
        raise HTTPException(status_code=409, detail=MENSAJE_ULTIMO_ADMIN)


def actualizar_usuario(db: Session, usuario_id: int, data: UsuarioUpdate, actor_id: int) -> UsuarioOut:
    row = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    _protege_ultimo_admin(db, row, data)

    if data.correo is not None and data.correo != row.correo:
        choque = db.query(Usuario).filter(Usuario.correo == data.correo, Usuario.id != row.id).first()
        if choque:
            raise HTTPException(status_code=409, detail=f"Ya existe un usuario con el correo '{data.correo}'")

    cambios: dict = {}
    if data.nombre is not None and data.nombre != row.nombre:
        row.nombre = data.nombre
        cambios["nombre"] = data.nombre
    if data.correo is not None and data.correo != row.correo:
        row.correo = data.correo
        cambios["correo"] = data.correo
    if data.rol_id is not None and data.rol_id != row.rol_id:
        rol = _rol_nombre(db, data.rol_id)
        row.rol_id = rol.id
        cambios["rol_id"] = rol.id
        cambios["rol"] = rol.nombre
    if data.activo is not None and data.activo != row.activo:
        row.activo = data.activo
        cambios["activo"] = data.activo
    if data.password is not None:
        row.password_hash = get_password_hash(data.password)
        cambios["password"] = "actualizada"

    if cambios:
        _registrar_auditoria(db, actor_id, "UPDATE", row.id, cambios)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="No se pudo actualizar el usuario") from exc
        db.refresh(row)
    return _to_out(db, row)
