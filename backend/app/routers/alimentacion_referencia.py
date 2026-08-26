"""API de contexto de alimentación. El catálogo vive en referencias_produccion."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.referencia_alimentacion_tilapia import BASE_PECES_REFERENCIA, ESPECIE_REFERENCIA
from app.core.database import get_db
from app.models.lote import Especie
from app.models.usuario import Usuario
from app.schemas.alimentacion_referencia import (
    ContextoAlimentacionLoteOut,
    FilaReferenciaAlimentacionOut,
    TablaReferenciaAlimentacionOut,
)
from app.services.alimentacion_referencia_service import filas_catalogo_oficial
from app.services.analisis_service import _calcular_indicadores, _cargar_lote
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get(
    "/maestra",
    response_model=TablaReferenciaAlimentacionOut,
    summary="Catálogo productivo oficial (referencias_produccion)",
)
def obtener_tabla_maestra(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
) -> TablaReferenciaAlimentacionOut:
    especie = (
        db.query(Especie)
        .filter(Especie.nombre_comun == ESPECIE_REFERENCIA, Especie.activo.is_(True))
        .first()
    )
    filas_raw = filas_catalogo_oficial(db, especie.id) if especie is not None else []
    filas = [FilaReferenciaAlimentacionOut(**fila) for fila in filas_raw]
    return TablaReferenciaAlimentacionOut(
        version="referencias_produccion",
        especie=ESPECIE_REFERENCIA,
        semanas=len(filas),
        base_peces_referencia=BASE_PECES_REFERENCIA,
        nota=(
            "Fuente oficial: referencias_produccion. Una fila por semana. "
            "Un rango de raciones (6–8) se muestra como rango; no se promedia."
        ),
        filas=filas,
    )


@router.get(
    "/contexto/lotes/{lote_id}",
    response_model=ContextoAlimentacionLoteOut,
    summary="Contexto de alimentación del lote activo",
)
def contexto_alimentacion_lote(
    lote_id: int,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
) -> ContextoAlimentacionLoteOut:
    lote = _cargar_lote(db, lote_id)
    ctx = _calcular_indicadores(db, lote)
    ref = ctx.referencia_alimentacion
    motivo = None
    if ref is None:
        motivo = ctx.pendientes.get("racion_diaria_recomendada_kg") or "SIN_REFERENCIA_PRODUCCION_APLICABLE"
    return ContextoAlimentacionLoteOut(lote_id=lote_id, referencia_activa=ref, motivo=motivo)
