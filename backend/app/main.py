"""
Biofloc ERP V1 - Punto de entrada de la aplicación FastAPI
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_db
from app.routers import (
    auth,
    estanques,
    lotes,
    biometrias,
    mortalidades,
    alimentaciones,
    cosechas,
    parametros_agua,
    referencias_agua,
    mediciones_agua,
    tipos_aplicacion_biofloc,
    mediciones_biofloc,
    aplicaciones_biofloc,
    categorias_inventario,
    unidades,
    productos,
    tipos_movimiento_inventario,
    movimientos_inventario,
    compras,
    alertas,
    categorias_gasto,
    gastos,
    ventas,
)

settings = get_settings()

# --- Instancia de FastAPI ---
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sistema ERP especializado para piscicultura de tilapia roja en sistema Biofloc.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(estanques.router, prefix="/api/v1/estanques", tags=["Estanques"])
app.include_router(lotes.router, prefix="/api/v1/lotes", tags=["Lotes"])
app.include_router(biometrias.router, prefix="/api/v1/biometrias", tags=["Biometrías"])
app.include_router(mortalidades.router, prefix="/api/v1/mortalidades", tags=["Mortalidades"])
app.include_router(alimentaciones.router, prefix="/api/v1/alimentaciones", tags=["Alimentaciones"])
app.include_router(cosechas.router, prefix="/api/v1/cosechas", tags=["Cosechas"])
app.include_router(parametros_agua.router, prefix="/api/v1/parametros-agua", tags=["Parámetros Agua"])
app.include_router(referencias_agua.router, prefix="/api/v1/referencias-agua", tags=["Referencias Agua"])
app.include_router(mediciones_agua.router, prefix="/api/v1/mediciones-agua", tags=["Mediciones Agua"])
app.include_router(tipos_aplicacion_biofloc.router, prefix="/api/v1/tipos-aplicacion-biofloc", tags=["Tipos Aplicación Biofloc"])
app.include_router(mediciones_biofloc.router, prefix="/api/v1/mediciones-biofloc", tags=["Mediciones Biofloc"])
app.include_router(aplicaciones_biofloc.router, prefix="/api/v1/aplicaciones-biofloc", tags=["Aplicaciones Biofloc"])
app.include_router(categorias_inventario.router, prefix="/api/v1/categorias-inventario", tags=["Categorías Inventario"])
app.include_router(unidades.router, prefix="/api/v1/unidades", tags=["Unidades"])
app.include_router(productos.router, prefix="/api/v1/productos", tags=["Productos"])
app.include_router(tipos_movimiento_inventario.router, prefix="/api/v1/tipos-movimiento-inventario", tags=["Tipos Movimiento Inventario"])
app.include_router(movimientos_inventario.router, prefix="/api/v1/movimientos-inventario", tags=["Movimientos Inventario"])
app.include_router(compras.router, prefix="/api/v1/compras", tags=["Compras"])
app.include_router(alertas.router, prefix="/api/v1/alertas", tags=["Alarmas Inventario"])
app.include_router(categorias_gasto.router, prefix="/api/v1/categorias-gasto", tags=["Categorías Gasto"])
app.include_router(gastos.router, prefix="/api/v1/gastos", tags=["Gastos"])
app.include_router(ventas.router, prefix="/api/v1/ventas", tags=["Ventas"])


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
def root():
    """Información básica de la aplicación."""
    return {
        "status": "ok",
        "application": settings.app_name,
        "version": settings.app_version,
    }


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Verifica el estado de la API y la conectividad con PostgreSQL.

    Retorna:
    - api: siempre "ok" si la aplicación está en pie.
    - database: "ok" si la consulta de prueba tiene éxito, "unavailable" si falla.
    """
    db_status = "unavailable"
    db_detail = None

    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_detail = str(exc)

    response = {
        "api": "ok",
        "database": db_status,
    }

    if db_detail:
        response["database_error"] = db_detail

    return response
