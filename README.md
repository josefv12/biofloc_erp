# Biofloc ERP

Sistema web para la gestión operativa, productiva, de inventario y financiera de una unidad piscícola con enfoque Biofloc.

## Arquitectura

- **Frontend:** React + TypeScript + Vite, desplegado en Vercel.
- **Backend:** FastAPI + SQLAlchemy, desplegado en Render.
- **Base de datos:** PostgreSQL en Neon.
- **Autenticación:** JWT + RBAC por roles.

## Módulos

- Dashboard y análisis productivo.
- Estanques, lotes, siembra, biometrías, mortalidades y cosechas.
- Calidad de agua y Biofloc.
- Alimentación con actualización transaccional del inventario.
- Inventario, productos, unidades, compras y movimientos.
- Ventas por lote de biomasa cosechada.
- Gastos y finanzas operativas.
- Equipos, mantenimiento, fallas y eventos de energía.
- Alarmas y reportes.
- Auditoría de operaciones críticas.

## Unidades de inventario

Cada producto tiene:

- `unidad_id`: unidad interna/canónica de almacenamiento.
- `unidad_comercial_id`: unidad que ve y captura el usuario.
- `factor_conversion`: cantidad de unidades internas contenidas en una unidad comercial.

Ejemplo: alimento almacenado en gramos y comprado/vendido comercialmente en kilogramos usa `g` como unidad interna, `kg` como unidad comercial y factor `1000`.

Los movimientos históricos no se reinterpretan: una vez que un producto tiene movimientos, sus unidades y factor de conversión quedan protegidos.

## Costos y finanzas

El sistema maneja los costos como **estimaciones operativas**, no como contabilidad financiera formal.

- El costo de alimento de un lote proviene del `costo_total` de las salidas de inventario generadas por sus alimentaciones.
- Los demás costos directos se toman de gastos asociados al lote.
- `costo_produccion` = alimento + gastos directos del lote.
- `costo_por_kg` = costo de producción / kg cosechados.
- `costo_ventas_estimado` (COGS) = kg vendidos × costo por kg.
- `utilidad_bruta` = ventas − costo de ventas estimado.
- Los gastos a nivel de estanque se mantienen separados hasta definir una regla explícita de asignación entre lotes; no se reparten arbitrariamente.

En el dashboard, **costo de producción de lotes** y **costo de ventas estimado** son indicadores distintos: el primero representa el costo acumulado de producción de los lotes con ventas en el periodo y el segundo solo la parte atribuible a la biomasa vendida.

## Ventas

Las ventas representan **biomasa cosechada en kg** y se relacionan directamente con un lote. No descuentan productos del inventario de alimento.

El sistema calcula automáticamente la disponibilidad:

`biomasa disponible = biomasa cosechada - biomasa ya vendida`

La regla se valida en el servicio y también mediante trigger PostgreSQL para proteger operaciones concurrentes o realizadas fuera de la API.

## Ciclo productivo

Para la estimación de cosecha se utiliza un ciclo de **6 meses calendario**, no un número fijo de días.

Ejemplo:

`11/09/2026 → 11/03/2027`

## Base de datos y migraciones

Para una instalación nueva:

1. Ejecutar `database/biofloc_erp_v1_1_schema_final.sql`.
2. Ejecutar las migraciones de `database/migrations` en orden numérico/cronológico.
3. Verificar que las columnas, restricciones e índices esperados existan antes de iniciar el backend.

Migraciones numeradas de integridad actualmente auditadas:

- `002_unidades_comerciales_productos.sql` — unidades internas/comerciales y conversión.
- `003_integridad_concurrencia.sql` — controles de concurrencia de población y stock.
- `004_control_ventas_y_unidades.sql` — controles de ventas y unidades.
- `005_fix_advisory_lock_lote_activo.sql` — bloqueo para impedir dos lotes activos simultáneos en un estanque.
- `006_indices_costeo_financiero.sql` — índices de costos y finanzas.
- `007_costos_lote_estanque_y_consumo_alimento.sql` — costos por lote/estanque y consumo de alimento.
- `008_integridad_historica_asof.sql` — integridad histórica de eventos.
- `009_inventario_ajuste_costeo.sql` — ajustes y costeo histórico de inventario.
- `010_integridad_produccion.sql` — integridad temporal y productiva.
- `011_trazabilidad_movimientos_automaticos.sql` — trazabilidad evento ↔ inventario.
- `012_integridad_inventario_valorado.sql` — integridad del inventario valorizado.
- `013_catalogo_gasto_alevinos.sql` — categoría de gasto de alevinos.
- `014_integridad_trazabilidad_movimientos.sql` — validaciones adicionales de trazabilidad.
- `015_integridad_secuencia_poblacion.sql` — secuencia histórica de población.
- `016_integridad_eventos_operativos.sql` — fechas no futuras en fallas, mantenimientos y energía.
- `017_idempotencia_movimientos_automaticos.sql` — una salida/entrada automática por referencia.
- `018_referencias_semana_minima.sql` — referencias productivas desde semana 1.
- `019_integridad_temporal_cierre_lote.sql` — coherencia entre fecha de cierre y eventos del lote.
- `020_integridad_fecha_siembra.sql` — impide siembras futuras.
- `021_referencias_raciones_positivas.sql` — impide raciones cero/negativas.
- `022_integridad_fecha_gasto.sql` — impide gastos futuros.
- `023_integridad_fechas_financieras_inventario.sql` — segunda barrera temporal para compras, ventas e inventario.
- `024_proteger_unidades_historicas_producto.sql` — impide cambiar unidades/factor tras movimientos.
- `025_inmutabilidad_historicos_inventario.sql` — refuerza la inmutabilidad de movimientos y registros ligados a inventario.

También existen migraciones con nombre de fecha para cambios de unidades, catálogos y referencias productivas; deben ejecutarse después de las numeradas según su orden cronológico y solo sobre una base compatible.

Las migraciones son manuales en la V1. Antes de aplicarlas a una base existente, revisar qué migraciones ya fueron ejecutadas para evitar repetir cambios no idempotentes.
## Backend local

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Variables principales: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `APP_ENV` y `ENABLE_DOCS`.

No subir `.env` al repositorio.

## Frontend local

```bash
cd frontend
npm ci
npm run dev
```

Para producción, `VITE_API_BASE_URL` puede apuntar al backend de Render. Si no se define, el frontend usa el backend de producción configurado en `frontend/src/api/client.ts`.

## Calidad

El repositorio incluye pruebas de backend y un workflow de GitHub Actions que comprueba:

- sintaxis Python del backend;
- pruebas automatizadas disponibles en `backend/tests`;
- instalación reproducible de dependencias frontend;
- compilación TypeScript/Vite.

Las pruebas que requieren PostgreSQL deben ejecutarse contra una base de pruebas configurada y nunca contra la base de producción.
