"""
Biofloc ERP V1 - Punto de entrada de la aplicación FastAPI
Docs y OpenAPI se controlan con APP_ENV / ENABLE_DOCS (F15.7).
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
    tipos_equipo,
    estados_equipo,
    equipos,
    tipos_mantenimiento,
    mantenimientos,
    fallas,
    eventos_energia,
    tipos_alarma,
    niveles_alarma,
    estados_alarma,
    alarmas,
    dashboard,
    reportes,
)

settings = get_settings()
_docs = "/docs" if settings.docs_enabled else None
_redoc = "/redoc" if settings.docs_enabled else None
_openapi = "/openapi.json" if settings.docs_enabled else None

# --- Instancia de FastAPI ---
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sistema ERP especializado para piscicultura de tilapia roja en sistema Biofloc.",
    docs_url=_docs,
    redoc_url=_redoc,
    openapi_url=_openapi,
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
app.include_router(tipos_equipo.router, prefix="/api/v1/tipos-equipo", tags=["Tipos Equipo"])
app.include_router(estados_equipo.router, prefix="/api/v1/estados-equipo", tags=["Estados Equipo"])
app.include_router(equipos.router, prefix="/api/v1/equipos", tags=["Equipos"])
app.include_router(tipos_mantenimiento.router, prefix="/api/v1/tipos-mantenimiento", tags=["Tipos Mantenimiento"])
app.include_router(mantenimientos.router, prefix="/api/v1/mantenimientos", tags=["Mantenimientos"])
app.include_router(fallas.router, prefix="/api/v1/fallas", tags=["Fallas"])
app.include_router(eventos_energia.router, prefix="/api/v1/eventos-energia", tags=["Eventos Energía"])
app.include_router(tipos_alarma.router, prefix="/api/v1/tipos-alarma", tags=["Tipos Alarma"])
app.include_router(niveles_alarma.router, prefix="/api/v1/niveles-alarma", tags=["Niveles Alarma"])
app.include_router(estados_alarma.router, prefix="/api/v1/estados-alarma", tags=["Estados Alarma"])
app.include_router(alarmas.router, prefix="/api/v1/alarmas", tags=["Alarmas"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(reportes.router, prefix="/api/v1/reportes", tags=["Reportes"])


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

    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"

    return {
        "api": "ok",
        "database": db_status,
    }
