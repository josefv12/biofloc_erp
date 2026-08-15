from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import get_current_user

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 1. Buscar usuario por correo
    user = db.query(Usuario).filter(Usuario.correo == request.correo).first()
    
    # 2. Si no existe, error genérico
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # 3. Si existe pero inactivo
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    # 4. Verificar password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # 5. Obtener el rol
    rol = db.query(Rol).filter(Rol.id == user.rol_id).first()
    rol_nombre = rol.nombre if rol else "UNKNOWN"
    
    # 6. Generar JWT
    access_token = create_access_token(
        data={"sub": str(user.id), "rol": rol_nombre}
    )
    
    # 7. Registrar en auditoria (OMITIDO POR CHECK CONSTRAINT)
    # limitación identificada: CHECK (accion IN ('INSERT', 'UPDATE', 'DELETE'))
    # No se puede insertar 'LOGIN' ya que violaría la restricción del esquema original.
    
    # 8. Devolver token
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    rol = db.query(Rol).filter(Rol.id == current_user.rol_id).first()
    
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "correo": current_user.correo,
        "rol": rol.nombre if rol else "UNKNOWN",
        "activo": current_user.activo
    }
