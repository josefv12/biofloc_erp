"""Dashboard ERP: capa de SOLO LECTURA. Agregaciones en PostgreSQL.

No escribe auditoría, movimientos ni ninguna tabla.
No calcula utilidad (no hay costo de ventas).
No suma stock entre unidades incompatibles.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.schemas.dashboard import (
    PeriodoOut, TotalNOut, NombreNOut, NombreTotalOut,
    UnidadStockOut, UnidadMovimientoOut, LoteVentaOut, UltimaBiometriaOut,
    DashboardResumenOut, DashboardInventarioOut, DashboardComprasOut,
    DashboardVentasOut, DashboardGastosOut, DashboardEquiposOut,
    DashboardEnergiaOut, DashboardAlarmasOut, DashboardProduccionOut,
)

D2 = Decimal("0.01")
D3 = Decimal("0.001")


def _d2(v) -> Decimal:
    if v is None:
        return Decimal("0.00")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _d3(v) -> Decimal:
    if v is None:
        return Decimal("0.000")
    return Decimal(str(v)).quantize(D3, rounding=ROUND_HALF_UP)


def _i(v) -> int:
    return int(v or 0)


def _params(fecha_desde: Optional[date], fecha_hasta: Optional[date]) -> dict:
    p = {}
    if fecha_desde is not None:
        p["fecha_desde"] = fecha_desde
    if fecha_hasta is not None:
        p["fecha_hasta"] = fecha_hasta
    return p


def _filtro(col: str, fecha_desde: Optional[date], fecha_hasta: Optional[date], *, ts: bool = False) -> str:
    expr = f"CAST({col} AS date)" if ts else col
    s = ""
    if fecha_desde is not None:
        s += f" AND {expr} >= :fecha_desde"
    if fecha_hasta is not None:
        s += f" AND {expr} <= :fecha_hasta"
    return s


def _one(db: Session, sql: str, params: dict):
    row = db.execute(text(sql), params).mappings().first()
    return row or {}


def _rows(db: Session, sql: str, params: dict):
    return list(db.execute(text(sql), params).mappings())


def _periodo(fecha_desde, fecha_hasta) -> PeriodoOut:
    return PeriodoOut(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


def _nombre_n(rows, nombre_key="nombre", n_key="n") -> list[NombreNOut]:
    return [NombreNOut(nombre=str(r[nombre_key]), n=_i(r[n_key])) for r in rows]


def _nombre_total(rows) -> list[NombreTotalOut]:
    return [NombreTotalOut(nombre=str(r["nombre"]), n=_i(r["n"]), total=_d2(r["total"])) for r in rows]


# ── resumen ──────────────────────────────────────────────────────────────────
def resumen(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardResumenOut:
    p = _params(fecha_desde, fecha_hasta)
    fv = _filtro("v.fecha", fecha_desde, fecha_hasta)
    fg = _filtro("g.fecha", fecha_desde, fecha_hasta)
    fc = _filtro("c.fecha", fecha_desde, fecha_hasta)
    fm = _filtro("m.fecha", fecha_desde, fecha_hasta)
    fe = _filtro("ev.fecha_hora_inicio", fecha_desde, fecha_hasta, ts=True)
    row = _one(db, f"""
        SELECT
          (SELECT COUNT(*) FROM ventas v WHERE 1=1 {fv}) AS ventas_n,
          (SELECT COALESCE(SUM(v.total), 0) FROM ventas v WHERE 1=1 {fv}) AS ventas_total,
          (SELECT COUNT(*) FROM gastos g WHERE 1=1 {fg}) AS gastos_n,
          (SELECT COALESCE(SUM(g.valor), 0) FROM gastos g WHERE 1=1 {fg}) AS gastos_total,
          (SELECT COUNT(*) FROM compras c WHERE 1=1 {fc}) AS compras_n,
          (SELECT COALESCE(SUM(c.total), 0) FROM compras c WHERE 1=1 {fc}) AS compras_total,
          (SELECT COUNT(*) FROM productos WHERE activo = TRUE) AS productos_activos,
          (SELECT COUNT(*) FROM vista_stock_productos v
             JOIN productos p ON p.id = v.producto_id
            WHERE p.activo = TRUE AND v.stock_actual <= 0) AS productos_sin_stock,
          (SELECT COUNT(*) FROM vista_stock_productos v
             JOIN productos p ON p.id = v.producto_id
            WHERE p.activo = TRUE AND v.stock_actual > 0 AND v.stock_actual <= v.stock_minimo) AS productos_stock_bajo,
          (SELECT COUNT(*) FROM alarmas a
             JOIN estados_alarma e ON e.id = a.estado_alarma_id
            WHERE e.nombre = 'PENDIENTE') AS alarmas_pendientes,
          (SELECT COUNT(*) FROM equipos WHERE activo = TRUE) AS equipos_activos,
          (SELECT COUNT(*) FROM equipos eq
             JOIN estados_equipo ee ON ee.id = eq.estado_id
            WHERE eq.activo = TRUE AND ee.nombre = 'OPERATIVO') AS equipos_operativos,
          (SELECT COUNT(*) FROM mantenimientos m WHERE 1=1 {fm}) AS mantenimientos_periodo,
          (SELECT COUNT(*) FROM eventos_energia ev WHERE 1=1 {fe}) AS eventos_energia_periodo,
          (SELECT COUNT(*) FROM lotes l
             JOIN estados_lote el ON el.id = l.estado_id
            WHERE el.nombre = 'ACTIVO') AS lotes_activos
    """, p)
    return DashboardResumenOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        ventas=TotalNOut(n=_i(row.get("ventas_n")), total=_d2(row.get("ventas_total"))),
        gastos=TotalNOut(n=_i(row.get("gastos_n")), total=_d2(row.get("gastos_total"))),
        compras=TotalNOut(n=_i(row.get("compras_n")), total=_d2(row.get("compras_total"))),
        productos_activos=_i(row.get("productos_activos")),
        productos_sin_stock=_i(row.get("productos_sin_stock")),
        productos_stock_bajo=_i(row.get("productos_stock_bajo")),
        alarmas_pendientes=_i(row.get("alarmas_pendientes")),
        equipos_activos=_i(row.get("equipos_activos")),
        equipos_operativos=_i(row.get("equipos_operativos")),
        mantenimientos_periodo=_i(row.get("mantenimientos_periodo")),
        eventos_energia_periodo=_i(row.get("eventos_energia_periodo")),
        lotes_activos=_i(row.get("lotes_activos")),
    )


# ── inventario ───────────────────────────────────────────────────────────────
def inventario(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardInventarioOut:
    p = _params(fecha_desde, fecha_hasta)
    snap = _one(db, """
        SELECT
          COUNT(*) FILTER (WHERE p.activo = TRUE) AS productos_activos,
          COUNT(*) FILTER (WHERE p.activo = FALSE) AS productos_inactivos,
          COUNT(*) FILTER (WHERE p.activo = TRUE AND v.stock_actual <= 0) AS sin_stock,
          COUNT(*) FILTER (WHERE p.activo = TRUE AND v.stock_actual > 0 AND v.stock_actual <= v.stock_minimo) AS stock_bajo,
          COUNT(*) FILTER (WHERE p.activo = TRUE AND v.stock_actual > v.stock_minimo) AS normal
        FROM vista_stock_productos v
        JOIN productos p ON p.id = v.producto_id
    """, {})
    stock_u = _rows(db, """
        SELECT v.unidad, COUNT(*) AS n_productos, COALESCE(SUM(v.stock_actual), 0) AS stock
        FROM vista_stock_productos v
        JOIN productos p ON p.id = v.producto_id
        WHERE p.activo = TRUE
        GROUP BY v.unidad
        ORDER BY v.unidad
    """, {})
    fm = _filtro("mi.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    mov = _rows(db, f"""
        SELECT u.simbolo AS unidad, tmi.afecta_stock,
               COUNT(*) AS n,
               COALESCE(SUM(mi.cantidad), 0) AS cantidad,
               COALESCE(SUM(mi.costo_total), 0) AS costo
        FROM movimientos_inventario mi
        JOIN productos p ON p.id = mi.producto_id
        JOIN unidades u ON u.id = p.unidad_id
        JOIN tipos_movimiento_inventario tmi ON tmi.id = mi.tipo_movimiento_id
        WHERE 1=1 {fm}
        GROUP BY u.simbolo, tmi.afecta_stock
        ORDER BY u.simbolo
    """, p)
    tot = _one(db, f"""
        SELECT
          COUNT(*) FILTER (WHERE tmi.afecta_stock = 1) AS n_entradas,
          COUNT(*) FILTER (WHERE tmi.afecta_stock = -1) AS n_salidas,
          COALESCE(SUM(mi.costo_total) FILTER (WHERE tmi.afecta_stock = 1), 0) AS costo_entradas,
          COALESCE(SUM(mi.costo_total) FILTER (WHERE tmi.afecta_stock = -1), 0) AS costo_salidas
        FROM movimientos_inventario mi
        JOIN tipos_movimiento_inventario tmi ON tmi.id = mi.tipo_movimiento_id
        WHERE 1=1 {fm}
    """, p)
    entradas, salidas = [], []
    for r in mov:
        item = UnidadMovimientoOut(
            unidad=str(r["unidad"]), n=_i(r["n"]), cantidad=_d3(r["cantidad"]), costo=_d2(r["costo"]),
        )
        if int(r["afecta_stock"]) == 1:
            entradas.append(item)
        else:
            salidas.append(item)
    return DashboardInventarioOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        productos_activos=_i(snap.get("productos_activos")),
        productos_inactivos=_i(snap.get("productos_inactivos")),
        productos_sin_stock=_i(snap.get("sin_stock")),
        productos_stock_bajo=_i(snap.get("stock_bajo")),
        productos_normal=_i(snap.get("normal")),
        stock_por_unidad=[
            UnidadStockOut(unidad=str(r["unidad"]), n_productos=_i(r["n_productos"]), stock=_d3(r["stock"]))
            for r in stock_u
        ],
        entradas=entradas,
        salidas=salidas,
        n_entradas=_i(tot.get("n_entradas")),
        n_salidas=_i(tot.get("n_salidas")),
        costo_entradas=_d2(tot.get("costo_entradas")),
        costo_salidas=_d2(tot.get("costo_salidas")),
    )


# ── compras ──────────────────────────────────────────────────────────────────
def compras(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardComprasOut:
    p = _params(fecha_desde, fecha_hasta)
    fc = _filtro("c.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(c.total), 0) AS total
        FROM compras c WHERE 1=1 {fc}
    """, p)
    n = _i(tot.get("n"))
    total = _d2(tot.get("total"))
    promedio = (total / n).quantize(D2, rounding=ROUND_HALF_UP) if n else Decimal("0.00")
    top = _rows(db, f"""
        SELECT COALESCE(NULLIF(TRIM(c.proveedor), ''), '(sin proveedor)') AS nombre,
               COUNT(*) AS n, COALESCE(SUM(c.total), 0) AS total
        FROM compras c WHERE 1=1 {fc}
        GROUP BY 1
        ORDER BY total DESC, n DESC
        LIMIT 5
    """, p)
    det = _one(db, f"""
        SELECT COUNT(DISTINCT d.producto_id) AS productos_distintos
        FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id
        WHERE 1=1 {fc}
    """, p)
    cant_u = _rows(db, f"""
        SELECT u.simbolo AS unidad, COUNT(*) AS n_productos, COALESCE(SUM(d.cantidad), 0) AS stock
        FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id
        JOIN productos p ON p.id = d.producto_id
        JOIN unidades u ON u.id = p.unidad_id
        WHERE 1=1 {fc}
        GROUP BY u.simbolo
        ORDER BY u.simbolo
    """, p)
    return DashboardComprasOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        n_compras=n,
        total=total,
        promedio=promedio,
        top_proveedores=_nombre_total(top),
        productos_distintos=_i(det.get("productos_distintos")),
        cantidad_por_unidad=[
            UnidadStockOut(unidad=str(r["unidad"]), n_productos=_i(r["n_productos"]), stock=_d3(r["stock"]))
            for r in cant_u
        ],
    )


# ── ventas ───────────────────────────────────────────────────────────────────
def ventas(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardVentasOut:
    p = _params(fecha_desde, fecha_hasta)
    fv = _filtro("v.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(v.total), 0) AS total
        FROM ventas v WHERE 1=1 {fv}
    """, p)
    n = _i(tot.get("n"))
    total = _d2(tot.get("total"))
    ticket = (total / n).quantize(D2, rounding=ROUND_HALF_UP) if n else Decimal("0.00")
    cant = _one(db, f"""
        SELECT COALESCE(SUM(d.cantidad), 0) AS cantidad
        FROM detalles_venta d
        JOIN ventas v ON v.id = d.venta_id
        WHERE 1=1 {fv}
    """, p)
    clientes = _rows(db, f"""
        SELECT COALESCE(NULLIF(TRIM(v.cliente), ''), '(sin cliente)') AS nombre,
               COUNT(*) AS n, COALESCE(SUM(v.total), 0) AS total
        FROM ventas v WHERE 1=1 {fv}
        GROUP BY 1
        ORDER BY total DESC, n DESC
        LIMIT 5
    """, p)
    lotes = _rows(db, f"""
        SELECT l.id AS lote_id, l.codigo, COUNT(*) AS n,
               COALESCE(SUM(d.cantidad), 0) AS cantidad,
               COALESCE(SUM(d.subtotal), 0) AS subtotal
        FROM detalles_venta d
        JOIN ventas v ON v.id = d.venta_id
        JOIN lotes l ON l.id = d.lote_id
        WHERE 1=1 {fv}
        GROUP BY l.id, l.codigo
        ORDER BY subtotal DESC
        LIMIT 10
    """, p)
    return DashboardVentasOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        n_ventas=n,
        total=total,
        ticket_promedio=ticket,
        cantidad_vendida=_d3(cant.get("cantidad")),
        top_clientes=_nombre_total(clientes),
        por_lote=[
            LoteVentaOut(
                lote_id=_i(r["lote_id"]), codigo=str(r["codigo"]), n=_i(r["n"]),
                cantidad=_d3(r["cantidad"]), subtotal=_d2(r["subtotal"]),
            )
            for r in lotes
        ],
    )


# ── gastos ───────────────────────────────────────────────────────────────────
def gastos(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardGastosOut:
    p = _params(fecha_desde, fecha_hasta)
    fg = _filtro("g.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(g.valor), 0) AS total
        FROM gastos g WHERE 1=1 {fg}
    """, p)
    n = _i(tot.get("n"))
    total = _d2(tot.get("total"))
    promedio = (total / n).quantize(D2, rounding=ROUND_HALF_UP) if n else Decimal("0.00")
    cats = _rows(db, f"""
        SELECT cg.nombre, COUNT(*) AS n, COALESCE(SUM(g.valor), 0) AS total
        FROM gastos g
        JOIN categorias_gasto cg ON cg.id = g.categoria_id
        WHERE 1=1 {fg}
        GROUP BY cg.nombre
        ORDER BY total DESC, cg.nombre
    """, p)
    lote = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(g.valor), 0) AS total
        FROM gastos g
        WHERE g.lote_id IS NOT NULL {fg}
    """, p)
    prov = _rows(db, f"""
        SELECT COALESCE(NULLIF(TRIM(g.proveedor), ''), '(sin proveedor)') AS nombre,
               COUNT(*) AS n, COALESCE(SUM(g.valor), 0) AS total
        FROM gastos g WHERE 1=1 {fg}
        GROUP BY 1
        ORDER BY total DESC, n DESC
        LIMIT 5
    """, p)
    return DashboardGastosOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        n_gastos=n,
        total=total,
        promedio=promedio,
        por_categoria=_nombre_total(cats),
        asociados_a_lote=TotalNOut(n=_i(lote.get("n")), total=_d2(lote.get("total"))),
        top_proveedores=_nombre_total(prov),
    )


# ── equipos ──────────────────────────────────────────────────────────────────
def equipos(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardEquiposOut:
    p = _params(fecha_desde, fecha_hasta)
    snap = _one(db, """
        SELECT COUNT(*) AS n_equipos,
               COUNT(*) FILTER (WHERE activo = TRUE) AS n_activos
        FROM equipos
    """, {})
    por_est = _rows(db, """
        SELECT ee.nombre, COUNT(eq.id) AS n
        FROM estados_equipo ee
        LEFT JOIN equipos eq ON eq.estado_id = ee.id
        GROUP BY ee.nombre
        ORDER BY ee.nombre
    """, {})
    por_tipo = _rows(db, """
        SELECT te.nombre, COUNT(eq.id) AS n
        FROM tipos_equipo te
        LEFT JOIN equipos eq ON eq.tipo_equipo_id = te.id
        GROUP BY te.nombre
        ORDER BY te.nombre
    """, {})
    fm = _filtro("m.fecha", fecha_desde, fecha_hasta)
    ff = _filtro("f.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    mant = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(m.costo), 0) AS total
        FROM mantenimientos m WHERE 1=1 {fm}
    """, p)
    fall = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(f.costo), 0) AS total,
               COUNT(DISTINCT f.equipo_id) AS equipos_con_fallas
        FROM fallas f WHERE 1=1 {ff}
    """, p)
    return DashboardEquiposOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        n_equipos=_i(snap.get("n_equipos")),
        n_activos=_i(snap.get("n_activos")),
        por_estado=_nombre_n(por_est),
        por_tipo=_nombre_n(por_tipo),
        mantenimientos_periodo=TotalNOut(n=_i(mant.get("n")), total=_d2(mant.get("total"))),
        fallas_periodo=TotalNOut(n=_i(fall.get("n")), total=_d2(fall.get("total"))),
        equipos_con_fallas_periodo=_i(fall.get("equipos_con_fallas")),
    )


# ── energía ──────────────────────────────────────────────────────────────────
def energia(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardEnergiaOut:
    p = _params(fecha_desde, fecha_hasta)
    fe = _filtro("ev.fecha_hora_inicio", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n,
               COUNT(*) FILTER (WHERE ev.fecha_hora_fin IS NULL) AS n_abiertos,
               COUNT(*) FILTER (WHERE ev.respaldo_activado = TRUE) AS n_respaldo,
               COALESCE(SUM(ev.duracion_minutos) FILTER (WHERE ev.duracion_minutos IS NOT NULL), 0) AS duracion
        FROM eventos_energia ev
        WHERE 1=1 {fe}
    """, p)
    tipos = _rows(db, f"""
        SELECT COALESCE(NULLIF(TRIM(ev.tipo), ''), '(sin tipo)') AS nombre, COUNT(*) AS n
        FROM eventos_energia ev
        WHERE 1=1 {fe}
        GROUP BY 1
        ORDER BY n DESC, nombre
    """, p)
    return DashboardEnergiaOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        n_eventos=_i(tot.get("n")),
        n_abiertos=_i(tot.get("n_abiertos")),
        n_respaldo_activado=_i(tot.get("n_respaldo")),
        duracion_minutos_cerrados=_i(tot.get("duracion")),
        por_tipo=_nombre_n(tipos),
    )


# ── alarmas ──────────────────────────────────────────────────────────────────
def alarmas(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardAlarmasOut:
    p = _params(fecha_desde, fecha_hasta)
    fa = _filtro("a.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    por_est = _rows(db, """
        SELECT ea.nombre, COUNT(a.id) AS n
        FROM estados_alarma ea
        LEFT JOIN alarmas a ON a.estado_alarma_id = ea.id
        GROUP BY ea.id, ea.nombre
        ORDER BY ea.id
    """, {})
    por_niv = _rows(db, """
        SELECT na.nombre, COUNT(a.id) AS n
        FROM niveles_alarma na
        LEFT JOIN alarmas a ON a.nivel_alarma_id = na.id
        GROUP BY na.nombre, na.prioridad
        ORDER BY na.prioridad
    """, {})
    por_tipo = _rows(db, """
        SELECT ta.nombre, COUNT(a.id) AS n
        FROM tipos_alarma ta
        LEFT JOIN alarmas a ON a.tipo_alarma_id = ta.id
        GROUP BY ta.nombre
        ORDER BY ta.nombre
    """, {})
    snap = _one(db, """
        SELECT
          COUNT(*) FILTER (WHERE equipo_id IS NOT NULL) AS con_equipo,
          COUNT(*) FILTER (WHERE evento_energia_id IS NOT NULL) AS con_energia,
          COUNT(*) FILTER (WHERE lote_id IS NOT NULL) AS con_lote
        FROM alarmas
    """, {})
    creadas = _one(db, f"SELECT COUNT(*) AS n FROM alarmas a WHERE 1=1 {fa}", p)
    creadas_tipo = _rows(db, f"""
        SELECT ta.nombre, COUNT(a.id) AS n
        FROM alarmas a
        JOIN tipos_alarma ta ON ta.id = a.tipo_alarma_id
        WHERE 1=1 {fa}
        GROUP BY ta.nombre
        ORDER BY n DESC, ta.nombre
    """, p)
    creadas_nivel = _rows(db, f"""
        SELECT na.nombre, COUNT(a.id) AS n
        FROM alarmas a
        JOIN niveles_alarma na ON na.id = a.nivel_alarma_id
        WHERE 1=1 {fa}
        GROUP BY na.nombre
        ORDER BY n DESC, na.nombre
    """, p)
    return DashboardAlarmasOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        snapshot_por_estado=_nombre_n(por_est),
        snapshot_por_nivel=_nombre_n(por_niv),
        snapshot_por_tipo=_nombre_n(por_tipo),
        snapshot_con_equipo=_i(snap.get("con_equipo")),
        snapshot_con_evento_energia=_i(snap.get("con_energia")),
        snapshot_con_lote=_i(snap.get("con_lote")),
        creadas_periodo=_i(creadas.get("n")),
        creadas_por_tipo=_nombre_n(creadas_tipo),
        creadas_por_nivel=_nombre_n(creadas_nivel),
    )


# ── producción / agua / biofloc / alimentación ───────────────────────────────
def produccion(db: Session, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> DashboardProduccionOut:
    p = _params(fecha_desde, fecha_hasta)
    lotes_e = _rows(db, """
        SELECT el.nombre, COUNT(l.id) AS n
        FROM estados_lote el
        LEFT JOIN lotes l ON l.estado_id = el.id
        GROUP BY el.nombre
        ORDER BY el.nombre
    """, {})
    est_e = _rows(db, """
        SELECT ee.nombre, COUNT(e.id) AS n
        FROM estados_estanque ee
        LEFT JOIN estanques e ON e.estado_id = ee.id
        GROUP BY ee.nombre
        ORDER BY ee.nombre
    """, {})
    act = _one(db, """
        SELECT COUNT(*) AS n,
               COALESCE(SUM(v.poblacion_estimada), 0) AS poblacion,
               COALESCE(SUM(v.cantidad_sembrada), 0) AS sembrada
        FROM vista_biomasa_lotes v
        JOIN lotes l ON l.id = v.lote_id
        JOIN estados_lote el ON el.id = l.estado_id
        WHERE el.nombre = 'ACTIVO'
    """, {})
    sembrada = _i(act.get("sembrada"))
    poblacion = _i(act.get("poblacion"))
    # Sin peces sembrados el porcentaje no existe: se informa null con motivo,
    # nunca 0, que se leería como mortalidad total.
    if sembrada > 0:
        surv = (Decimal(poblacion) / Decimal(sembrada) * Decimal("100")).quantize(D2, rounding=ROUND_HALF_UP)
        surv_motivo = None
    else:
        surv = None
        surv_motivo = "SIN_PECES_SEMBRADOS_EN_LOTES_ACTIVOS"
    fa = _filtro("a.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    fc = _filtro("c.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    fmo = _filtro("m.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    fwa = _filtro("mw.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    fmb = _filtro("mb.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    fab = _filtro("ab.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    alim = _one(db, f"SELECT COUNT(*) AS n FROM alimentaciones a WHERE 1=1 {fa}", p)
    alim_u = _rows(db, f"""
        SELECT u.simbolo AS unidad, COUNT(*) AS n_productos, COALESCE(SUM(a.cantidad), 0) AS stock
        FROM alimentaciones a
        JOIN productos p ON p.id = a.producto_id
        JOIN unidades u ON u.id = p.unidad_id
        WHERE 1=1 {fa}
        GROUP BY u.simbolo
        ORDER BY u.simbolo
    """, p)
    cos = _one(db, f"""
        SELECT COUNT(*) AS n,
               COALESCE(SUM(c.cantidad_peces), 0) AS peces,
               COALESCE(SUM(c.peso_total_kg), 0) AS peso_kg
        FROM cosechas c WHERE 1=1 {fc}
    """, p)
    mort = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(m.cantidad), 0) AS peces
        FROM mortalidades m WHERE 1=1 {fmo}
    """, p)
    agua = _one(db, f"SELECT COUNT(*) AS n FROM mediciones_agua mw WHERE 1=1 {fwa}", p)
    fuera = _one(db, f"""
        SELECT COUNT(*) AS n
        FROM mediciones_agua mw
        JOIN lotes l ON l.id = mw.lote_id
        JOIN referencias_agua r
          ON r.especie_id = l.especie_id
         AND r.etapa_productiva_id = l.etapa_productiva_id
         AND r.parametro_id = mw.parametro_id
         AND r.activo = TRUE
        WHERE 1=1 {fwa}
          AND (
            (r.valor_minimo IS NOT NULL AND mw.valor < r.valor_minimo)
            OR (r.valor_maximo IS NOT NULL AND mw.valor > r.valor_maximo)
          )
    """, p)
    bio = _one(db, f"SELECT COUNT(*) AS n FROM mediciones_biofloc mb WHERE 1=1 {fmb}", p)
    apl = _one(db, f"SELECT COUNT(*) AS n FROM aplicaciones_biofloc ab WHERE 1=1 {fab}", p)
    bios = _rows(db, """
        SELECT v.lote_id, l.codigo, v.fecha_hora, v.peso_promedio_g
        FROM vista_ultima_biometria v
        JOIN lotes l ON l.id = v.lote_id
        ORDER BY l.codigo
        LIMIT 20
    """, {})
    ultimas = []
    for r in bios:
        fh = r["fecha_hora"]
        ultimas.append(UltimaBiometriaOut(
            lote_id=_i(r["lote_id"]),
            codigo=str(r["codigo"]),
            fecha_hora=fh.isoformat() if fh is not None else None,
            peso_promedio_g=_d3(r["peso_promedio_g"]) if r["peso_promedio_g"] is not None else None,
        ))
    return DashboardProduccionOut(
        periodo=_periodo(fecha_desde, fecha_hasta),
        lotes_por_estado=_nombre_n(lotes_e),
        estanques_por_estado=_nombre_n(est_e),
        lotes_activos=_i(act.get("n")),
        poblacion_estimada_activos=poblacion,
        supervivencia_pct_activos=surv,
        supervivencia_pct_activos_motivo=surv_motivo,
        alimentaciones_periodo=_i(alim.get("n")),
        alimentacion_por_unidad=[
            UnidadStockOut(unidad=str(r["unidad"]), n_productos=_i(r["n_productos"]), stock=_d3(r["stock"]))
            for r in alim_u
        ],
        cosechas_periodo=_i(cos.get("n")),
        cosechas_peces=_i(cos.get("peces")),
        cosechas_peso_total_kg=_d3(cos.get("peso_kg")),
        mortalidades_periodo=_i(mort.get("n")),
        mortalidades_peces=_i(mort.get("peces")),
        mediciones_agua_periodo=_i(agua.get("n")),
        mediciones_agua_fuera_rango=_i(fuera.get("n")),
        mediciones_biofloc_periodo=_i(bio.get("n")),
        aplicaciones_biofloc_periodo=_i(apl.get("n")),
        ultimas_biometrias=ultimas,
    )
