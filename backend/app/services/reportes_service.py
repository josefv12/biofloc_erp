"""Reportes ERP: SOLO LECTURA. Filas detalladas + joins reales. Agregaciones en PostgreSQL.

No escribe auditoría ni movimientos.
No duplica KPIs del Dashboard: devuelve tablas de registros.
No suma cantidades de unidades distintas.
Ventas → detalles_venta → lotes (sin producto_id).
Trazabilidad compra: movimientos.referencia_tipo='DETALLE_COMPRA'.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.indicadores_lote import supervivencia_biologica_pct

from app.schemas.reportes import (
    UnidadCantidadOut,
    VentaFilaOut, ReporteVentasOut,
    CompraFilaOut, ReporteComprasOut,
    GastoFilaOut, ReporteGastosOut,
    InventarioFilaOut, ReporteInventarioOut,
    MovimientoFilaOut, ReporteMovimientosOut,
    CompraInventarioFilaOut, ReporteComprasInventarioOut,
    ProduccionFilaOut, ReporteProduccionOut,
    AguaFilaOut, ReporteAguaOut,
    BioflocMedicionFilaOut, BioflocAplicacionFilaOut, ReporteBioflocOut,
    AlimentacionFilaOut, ReporteAlimentacionOut,
    EquipoFilaOut, ReporteEquiposOut,
    MantenimientoFilaOut, ReporteMantenimientosOut,
    FallaFilaOut, ReporteFallasOut,
    EnergiaFilaOut, ReporteEnergiaOut,
    AlarmaFilaOut, ReporteAlarmasOut,
)

D2 = Decimal("0.01")
D3 = Decimal("0.001")
D4 = Decimal("0.0001")
LIMITE = 2000
NOTA_AGUA = (
    "fuera_de_rango usa referencias_agua de la especie y etapa ACTUAL del lote; "
    "no es un histórico de etapa al momento de la medición."
)


def _d2(v) -> Decimal:
    if v is None:
        return Decimal("0.00")
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _d2n(v):
    if v is None:
        return None
    return Decimal(str(v)).quantize(D2, rounding=ROUND_HALF_UP)


def _d3(v) -> Decimal:
    if v is None:
        return Decimal("0.000")
    return Decimal(str(v)).quantize(D3, rounding=ROUND_HALF_UP)


def _d3n(v):
    if v is None:
        return None
    return Decimal(str(v)).quantize(D3, rounding=ROUND_HALF_UP)


def _d4n(v):
    if v is None:
        return None
    return Decimal(str(v)).quantize(D4, rounding=ROUND_HALF_UP)


def _i(v) -> int:
    return int(v or 0)


def _now():
    return datetime.now(timezone.utc)


def _params(fecha_desde, fecha_hasta, extra=None) -> dict:
    p = {"lim": LIMITE}
    if fecha_desde is not None:
        p["fecha_desde"] = fecha_desde
    if fecha_hasta is not None:
        p["fecha_hasta"] = fecha_hasta
    if extra:
        p.update(extra)
    return p


def _filtro(col: str, fecha_desde, fecha_hasta, *, ts: bool = False) -> str:
    expr = f"CAST({col} AS date)" if ts else col
    s = ""
    if fecha_desde is not None:
        s += f" AND {expr} >= :fecha_desde"
    if fecha_hasta is not None:
        s += f" AND {expr} <= :fecha_hasta"
    return s


def _one(db: Session, sql: str, params: dict):
    return db.execute(text(sql), params).mappings().first() or {}


def _rows(db: Session, sql: str, params: dict):
    return list(db.execute(text(sql), params).mappings())


# ── ventas (detalle → lote) ──────────────────────────────────────────────────
def ventas(db: Session, fecha_desde=None, fecha_hasta=None,
           cliente: Optional[str] = None, lote_id: Optional[int] = None,
           registrado_por: Optional[int] = None) -> ReporteVentasOut:
    extra = {}
    extra_sql = ""
    if cliente:
        extra["cliente"] = f"%{cliente}%"
        extra_sql += " AND v.cliente ILIKE :cliente"
    if lote_id is not None:
        extra["lote_id"] = lote_id
        extra_sql += " AND d.lote_id = :lote_id"
    if registrado_por is not None:
        extra["registrado_por"] = registrado_por
        extra_sql += " AND v.registrado_por = :registrado_por"
    p = _params(fecha_desde, fecha_hasta, extra)
    fv = _filtro("v.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n,
               COUNT(DISTINCT v.id) AS n_ventas,
               COALESCE(SUM(d.subtotal), 0) AS suma
        FROM detalles_venta d
        JOIN ventas v ON v.id = d.venta_id
        WHERE 1=1 {fv} {extra_sql}
    """, p)
    rows = _rows(db, f"""
        SELECT v.id AS venta_id, d.id AS detalle_id, v.fecha, v.cliente,
               d.lote_id, l.codigo AS lote_codigo, d.cantidad, d.precio_unitario,
               d.subtotal, v.total AS venta_total, v.registrado_por, u.nombre AS registrado_por_nombre
        FROM detalles_venta d
        JOIN ventas v ON v.id = d.venta_id
        JOIN lotes l ON l.id = d.lote_id
        LEFT JOIN usuarios u ON u.id = v.registrado_por
        WHERE 1=1 {fv} {extra_sql}
        ORDER BY v.fecha DESC, v.id DESC, d.id
        LIMIT :lim
    """, p)
    filas = [
        VentaFilaOut(
            venta_id=_i(r["venta_id"]), detalle_id=_i(r["detalle_id"]), fecha=r["fecha"],
            cliente=r["cliente"], lote_id=_i(r["lote_id"]), lote_codigo=str(r["lote_codigo"]),
            cantidad=_d3(r["cantidad"]), precio_unitario=_d2(r["precio_unitario"]),
            subtotal=_d2(r["subtotal"]), venta_total=_d2(r["venta_total"]),
            registrado_por=_i(r["registrado_por"]), registrado_por_nombre=r["registrado_por_nombre"],
        ) for r in rows
    ]
    return ReporteVentasOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), suma_subtotales=_d2(tot.get("suma")), n_ventas=_i(tot.get("n_ventas")),
        filas=filas,
    )


# ── compras (detalle → producto → unidad) ────────────────────────────────────
def compras(db: Session, fecha_desde=None, fecha_hasta=None,
            proveedor: Optional[str] = None, producto_id: Optional[int] = None,
            registrado_por: Optional[int] = None) -> ReporteComprasOut:
    extra, extra_sql = {}, ""
    if proveedor:
        extra["proveedor"] = f"%{proveedor}%"
        extra_sql += " AND c.proveedor ILIKE :proveedor"
    if producto_id is not None:
        extra["producto_id"] = producto_id
        extra_sql += " AND d.producto_id = :producto_id"
    if registrado_por is not None:
        extra["registrado_por"] = registrado_por
        extra_sql += " AND c.registrado_por = :registrado_por"
    p = _params(fecha_desde, fecha_hasta, extra)
    fc = _filtro("c.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COUNT(DISTINCT c.id) AS n_compras, COALESCE(SUM(d.subtotal), 0) AS suma
        FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id
        WHERE 1=1 {fc} {extra_sql}
    """, p)
    por_u = _rows(db, f"""
        SELECT un.simbolo AS unidad, COALESCE(SUM(d.cantidad), 0) AS cantidad
        FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id
        JOIN productos p ON p.id = d.producto_id
        JOIN unidades un ON un.id = p.unidad_id
        WHERE 1=1 {fc} {extra_sql}
        GROUP BY un.simbolo
        ORDER BY un.simbolo
    """, p)
    rows = _rows(db, f"""
        SELECT c.id AS compra_id, d.id AS detalle_id, c.fecha, c.proveedor,
               d.producto_id, p.codigo AS producto_codigo, p.nombre AS producto_nombre,
               un.simbolo AS unidad, d.cantidad, d.precio_unitario, d.subtotal,
               c.total AS compra_total, c.registrado_por, u.nombre AS registrado_por_nombre
        FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id
        JOIN productos p ON p.id = d.producto_id
        JOIN unidades un ON un.id = p.unidad_id
        LEFT JOIN usuarios u ON u.id = c.registrado_por
        WHERE 1=1 {fc} {extra_sql}
        ORDER BY c.fecha DESC, c.id DESC, d.id
        LIMIT :lim
    """, p)
    filas = [
        CompraFilaOut(
            compra_id=_i(r["compra_id"]), detalle_id=_i(r["detalle_id"]), fecha=r["fecha"],
            proveedor=r["proveedor"], producto_id=_i(r["producto_id"]),
            producto_codigo=str(r["producto_codigo"]), producto_nombre=str(r["producto_nombre"]),
            unidad=str(r["unidad"]), cantidad=_d3(r["cantidad"]),
            precio_unitario=_d2(r["precio_unitario"]), subtotal=_d2(r["subtotal"]),
            compra_total=_d2(r["compra_total"]), registrado_por=_i(r["registrado_por"]),
            registrado_por_nombre=r["registrado_por_nombre"],
        ) for r in rows
    ]
    return ReporteComprasOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), suma_subtotales=_d2(tot.get("suma")), n_compras=_i(tot.get("n_compras")),
        cantidad_por_unidad=[UnidadCantidadOut(unidad=str(r["unidad"]), cantidad=_d3(r["cantidad"])) for r in por_u],
        filas=filas,
    )


# ── gastos ───────────────────────────────────────────────────────────────────
def gastos(db: Session, fecha_desde=None, fecha_hasta=None,
           categoria_id: Optional[int] = None, lote_id: Optional[int] = None,
           proveedor: Optional[str] = None, registrado_por: Optional[int] = None) -> ReporteGastosOut:
    extra, extra_sql = {}, ""
    if categoria_id is not None:
        extra["categoria_id"] = categoria_id
        extra_sql += " AND g.categoria_id = :categoria_id"
    if lote_id is not None:
        extra["lote_id"] = lote_id
        extra_sql += " AND g.lote_id = :lote_id"
    if proveedor:
        extra["proveedor"] = f"%{proveedor}%"
        extra_sql += " AND g.proveedor ILIKE :proveedor"
    if registrado_por is not None:
        extra["registrado_por"] = registrado_por
        extra_sql += " AND g.registrado_por = :registrado_por"
    p = _params(fecha_desde, fecha_hasta, extra)
    fg = _filtro("g.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(g.valor), 0) AS total
        FROM gastos g WHERE 1=1 {fg} {extra_sql}
    """, p)
    rows = _rows(db, f"""
        SELECT g.id AS gasto_id, g.fecha, g.categoria_id, cg.nombre AS categoria,
               g.descripcion, g.proveedor, g.valor, g.lote_id, l.codigo AS lote_codigo,
               g.registrado_por, u.nombre AS registrado_por_nombre
        FROM gastos g
        JOIN categorias_gasto cg ON cg.id = g.categoria_id
        LEFT JOIN lotes l ON l.id = g.lote_id
        LEFT JOIN usuarios u ON u.id = g.registrado_por
        WHERE 1=1 {fg} {extra_sql}
        ORDER BY g.fecha DESC, g.id DESC
        LIMIT :lim
    """, p)
    filas = [
        GastoFilaOut(
            gasto_id=_i(r["gasto_id"]), fecha=r["fecha"], categoria_id=_i(r["categoria_id"]),
            categoria=str(r["categoria"]), descripcion=str(r["descripcion"]), proveedor=r["proveedor"],
            valor=_d2(r["valor"]), lote_id=r["lote_id"], lote_codigo=r["lote_codigo"],
            registrado_por=_i(r["registrado_por"]), registrado_por_nombre=r["registrado_por_nombre"],
        ) for r in rows
    ]
    return ReporteGastosOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), total_valor=_d2(tot.get("total")), filas=filas,
    )


# ── inventario snapshot (vista_stock_productos; filtros sobre alias x) ──────
def inventario(db: Session, fecha_desde=None, fecha_hasta=None,
               clasificacion: Optional[str] = None, solo_activos: bool = True) -> ReporteInventarioOut:
    extra, extra_sql = {}, ""
    if solo_activos:
        extra_sql += " AND x.activo = TRUE"
    if clasificacion:
        extra["clasificacion"] = clasificacion
        extra_sql += " AND x.clasificacion = :clasificacion"
    p = _params(fecha_desde, fecha_hasta, extra)
    base = f"""
        SELECT v.producto_id, v.codigo, v.nombre, v.unidad, v.stock_actual, v.stock_minimo,
               p.activo, p.categoria_id, c.nombre AS categoria_nombre,
               CASE
                 WHEN v.stock_actual <= 0 THEN 'SIN_STOCK'
                 WHEN v.stock_actual <= v.stock_minimo THEN 'STOCK_BAJO'
                 ELSE 'NORMAL'
               END AS clasificacion
        FROM vista_stock_productos v
        JOIN productos p ON p.id = v.producto_id
        LEFT JOIN categorias_inventario c ON c.id = p.categoria_id
    """
    tot = _one(db, f"SELECT COUNT(*) AS n FROM ({base}) x WHERE 1=1 {extra_sql}", p)
    rows = _rows(db, f"""
        SELECT * FROM ({base}) x WHERE 1=1 {extra_sql}
        ORDER BY x.codigo
        LIMIT :lim
    """, p)
    filas = [
        InventarioFilaOut(
            producto_id=_i(r["producto_id"]), codigo=str(r["codigo"]), nombre=str(r["nombre"]),
            unidad=str(r["unidad"]), stock_actual=_d3(r["stock_actual"]), stock_minimo=_d3(r["stock_minimo"]),
            clasificacion=str(r["clasificacion"]), activo=bool(r["activo"]),
            categoria_id=_i(r["categoria_id"]), categoria_nombre=r["categoria_nombre"],
        ) for r in rows
    ]
    return ReporteInventarioOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), filas=filas,
    )


def movimientos(db: Session, fecha_desde=None, fecha_hasta=None,
                producto_id: Optional[int] = None,
                referencia_tipo: Optional[str] = None) -> ReporteMovimientosOut:
    extra, extra_sql = {}, ""
    if producto_id is not None:
        extra["producto_id"] = producto_id
        extra_sql += " AND mi.producto_id = :producto_id"
    if referencia_tipo:
        extra["referencia_tipo"] = referencia_tipo
        extra_sql += " AND mi.referencia_tipo = :referencia_tipo"
    p = _params(fecha_desde, fecha_hasta, extra)
    fm = _filtro("mi.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(mi.costo_total), 0) AS costo
        FROM movimientos_inventario mi WHERE 1=1 {fm} {extra_sql}
    """, p)
    rows = _rows(db, f"""
        SELECT mi.id AS movimiento_id, mi.fecha_hora, mi.producto_id, p.codigo AS producto_codigo,
               p.nombre AS producto_nombre, un.simbolo AS unidad, tmi.nombre AS tipo,
               tmi.afecta_stock, mi.cantidad, mi.costo_unitario, mi.costo_total,
               mi.referencia_tipo, mi.referencia_id, mi.registrado_por, u.nombre AS registrado_por_nombre
        FROM movimientos_inventario mi
        JOIN productos p ON p.id = mi.producto_id
        JOIN unidades un ON un.id = p.unidad_id
        JOIN tipos_movimiento_inventario tmi ON tmi.id = mi.tipo_movimiento_id
        LEFT JOIN usuarios u ON u.id = mi.registrado_por
        WHERE 1=1 {fm} {extra_sql}
        ORDER BY mi.fecha_hora DESC, mi.id DESC
        LIMIT :lim
    """, p)
    filas = [
        MovimientoFilaOut(
            movimiento_id=_i(r["movimiento_id"]), fecha_hora=r["fecha_hora"],
            producto_id=_i(r["producto_id"]), producto_codigo=str(r["producto_codigo"]),
            producto_nombre=str(r["producto_nombre"]), unidad=str(r["unidad"]),
            tipo=str(r["tipo"]), afecta_stock=int(r["afecta_stock"]), cantidad=_d3(r["cantidad"]),
            costo_unitario=_d2n(r["costo_unitario"]), costo_total=_d2n(r["costo_total"]),
            referencia_tipo=r["referencia_tipo"], referencia_id=r["referencia_id"],
            registrado_por=_i(r["registrado_por"]), registrado_por_nombre=r["registrado_por_nombre"],
        ) for r in rows
    ]
    return ReporteMovimientosOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), suma_costo_total=_d2(tot.get("costo")), filas=filas,
    )


def compras_inventario(db: Session, fecha_desde=None, fecha_hasta=None) -> ReporteComprasInventarioOut:
    p = _params(fecha_desde, fecha_hasta)
    fc = _filtro("c.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id WHERE 1=1 {fc}
    """, p)
    rows = _rows(db, f"""
        SELECT c.id AS compra_id, d.id AS detalle_id, c.fecha, c.proveedor,
               d.producto_id, p.codigo AS producto_codigo, un.simbolo AS unidad,
               d.cantidad, d.subtotal, mi.id AS movimiento_id,
               mi.referencia_tipo, tmi.nombre AS tipo_movimiento
        FROM detalles_compra d
        JOIN compras c ON c.id = d.compra_id
        JOIN productos p ON p.id = d.producto_id
        JOIN unidades un ON un.id = p.unidad_id
        LEFT JOIN movimientos_inventario mi
          ON mi.referencia_tipo = 'DETALLE_COMPRA' AND mi.referencia_id = d.id
        LEFT JOIN tipos_movimiento_inventario tmi ON tmi.id = mi.tipo_movimiento_id
        WHERE 1=1 {fc}
        ORDER BY c.fecha DESC, c.id DESC, d.id
        LIMIT :lim
    """, p)
    filas = [
        CompraInventarioFilaOut(
            compra_id=_i(r["compra_id"]), detalle_id=_i(r["detalle_id"]), fecha=r["fecha"],
            proveedor=r["proveedor"], producto_id=_i(r["producto_id"]),
            producto_codigo=str(r["producto_codigo"]), unidad=str(r["unidad"]),
            cantidad=_d3(r["cantidad"]), subtotal=_d2(r["subtotal"]),
            movimiento_id=r["movimiento_id"], referencia_tipo=r["referencia_tipo"],
            tipo_movimiento=r["tipo_movimiento"],
        ) for r in rows
    ]
    return ReporteComprasInventarioOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), filas=filas,
    )


# ── producción (lotes + vistas) ──────────────────────────────────────────────
def produccion(db: Session, fecha_desde=None, fecha_hasta=None,
               lote_id: Optional[int] = None) -> ReporteProduccionOut:
    extra, extra_sql = {}, ""
    if lote_id is not None:
        extra["lote_id"] = lote_id
        extra_sql += " AND l.id = :lote_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    fs = _filtro("l.fecha_siembra", fecha_desde, fecha_hasta)
    tot = _one(db, f"SELECT COUNT(*) AS n FROM lotes l WHERE 1=1 {fs} {extra_sql}", p)
    rows = _rows(db, f"""
        SELECT l.id AS lote_id, l.codigo, el.nombre AS estado, e.codigo AS estanque_codigo,
               es.nombre_comun AS especie, ep.nombre AS etapa, l.fecha_siembra, l.cantidad_sembrada,
               v.mortalidad_acumulada, v.peces_cosechados, v.poblacion_estimada,
               ub.fecha_hora AS ultima_biometria_fecha, ub.peso_promedio_g
        FROM lotes l
        JOIN estados_lote el ON el.id = l.estado_id
        JOIN estanques e ON e.id = l.estanque_id
        JOIN especies es ON es.id = l.especie_id
        JOIN etapas_productivas ep ON ep.id = l.etapa_productiva_id
        JOIN vista_biomasa_lotes v ON v.lote_id = l.id
        LEFT JOIN vista_ultima_biometria ub ON ub.lote_id = l.id
        WHERE 1=1 {fs} {extra_sql}
        ORDER BY l.codigo
        LIMIT :lim
    """, p)
    filas = [
        ProduccionFilaOut(
            lote_id=_i(r["lote_id"]), codigo=str(r["codigo"]), estado=str(r["estado"]),
            estanque_codigo=str(r["estanque_codigo"]), especie=str(r["especie"]), etapa=str(r["etapa"]),
            fecha_siembra=r["fecha_siembra"], cantidad_sembrada=_i(r["cantidad_sembrada"]),
            mortalidad_acumulada=_i(r["mortalidad_acumulada"]), peces_cosechados=_i(r["peces_cosechados"]),
            poblacion_estimada=_i(r["poblacion_estimada"]),
            supervivencia_porcentaje=supervivencia_biologica_pct(
                _i(r["cantidad_sembrada"]), _i(r["mortalidad_acumulada"])
            ),
            ultima_biometria_fecha=r["ultima_biometria_fecha"], peso_promedio_g=_d3n(r["peso_promedio_g"]),
        ) for r in rows
    ]
    return ReporteProduccionOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), filas=filas,
    )


def agua(db: Session, fecha_desde=None, fecha_hasta=None,
         lote_id: Optional[int] = None, parametro_id: Optional[int] = None) -> ReporteAguaOut:
    extra, extra_sql = {}, ""
    if lote_id is not None:
        extra["lote_id"] = lote_id
        extra_sql += " AND mw.lote_id = :lote_id"
    if parametro_id is not None:
        extra["parametro_id"] = parametro_id
        extra_sql += " AND mw.parametro_id = :parametro_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    fwa = _filtro("mw.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"SELECT COUNT(*) AS n FROM mediciones_agua mw WHERE 1=1 {fwa} {extra_sql}", p)
    rows = _rows(db, f"""
        SELECT mw.id AS medicion_id, mw.fecha_hora, mw.lote_id, l.codigo AS lote_codigo,
               pa.nombre AS parametro, pa.unidad, mw.valor, r.valor_minimo, r.valor_maximo,
               CASE
                 WHEN r.id IS NULL THEN NULL
                 WHEN r.valor_minimo IS NOT NULL AND mw.valor < r.valor_minimo THEN TRUE
                 WHEN r.valor_maximo IS NOT NULL AND mw.valor > r.valor_maximo THEN TRUE
                 ELSE FALSE
               END AS fuera_de_rango,
               mw.registrado_por
        FROM mediciones_agua mw
        JOIN lotes l ON l.id = mw.lote_id
        JOIN parametros_agua pa ON pa.id = mw.parametro_id
        LEFT JOIN referencias_agua r
          ON r.especie_id = l.especie_id
         AND r.etapa_productiva_id = l.etapa_productiva_id
         AND r.parametro_id = mw.parametro_id
         AND r.activo = TRUE
        WHERE 1=1 {fwa} {extra_sql}
        ORDER BY mw.fecha_hora DESC, mw.id DESC
        LIMIT :lim
    """, p)
    filas = [
        AguaFilaOut(
            medicion_id=_i(r["medicion_id"]), fecha_hora=r["fecha_hora"], lote_id=_i(r["lote_id"]),
            lote_codigo=str(r["lote_codigo"]), parametro=str(r["parametro"]), unidad=str(r["unidad"]),
            valor=_d4n(r["valor"]) or Decimal("0.0000"),
            valor_minimo=_d4n(r["valor_minimo"]), valor_maximo=_d4n(r["valor_maximo"]),
            fuera_de_rango=r["fuera_de_rango"], registrado_por=_i(r["registrado_por"]),
        ) for r in rows
    ]
    return ReporteAguaOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), nota=NOTA_AGUA, filas=filas,
    )


def biofloc(db: Session, fecha_desde=None, fecha_hasta=None,
            lote_id: Optional[int] = None) -> ReporteBioflocOut:
    extra = {}
    extra_mb = ""
    extra_ab = ""
    if lote_id is not None:
        extra["lote_id"] = lote_id
        extra_mb = " AND mb.lote_id = :lote_id"
        extra_ab = " AND ab.lote_id = :lote_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    fmb = _filtro("mb.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    fab = _filtro("ab.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    meds = _rows(db, f"""
        SELECT mb.id AS medicion_id, mb.fecha_hora, mb.lote_id, l.codigo AS lote_codigo,
               mb.volumen_sedimentable, mb.unidad, mb.relacion_cn, mb.registrado_por
        FROM mediciones_biofloc mb
        JOIN lotes l ON l.id = mb.lote_id
        WHERE 1=1 {fmb} {extra_mb}
        ORDER BY mb.fecha_hora DESC, mb.id DESC
        LIMIT :lim
    """, p)
    apls = _rows(db, f"""
        SELECT ab.id AS aplicacion_id, ab.fecha_hora, ab.lote_id, l.codigo AS lote_codigo,
               t.nombre AS tipo_aplicacion, ab.producto_id, ab.cantidad, ab.unidad, ab.registrado_por
        FROM aplicaciones_biofloc ab
        JOIN lotes l ON l.id = ab.lote_id
        JOIN tipos_aplicacion_biofloc t ON t.id = ab.tipo_aplicacion_id
        WHERE 1=1 {fab} {extra_ab}
        ORDER BY ab.fecha_hora DESC, ab.id DESC
        LIMIT :lim
    """, p)
    mediciones = [
        BioflocMedicionFilaOut(
            medicion_id=_i(r["medicion_id"]), fecha_hora=r["fecha_hora"], lote_id=_i(r["lote_id"]),
            lote_codigo=str(r["lote_codigo"]), volumen_sedimentable=_d2(r["volumen_sedimentable"]),
            unidad=str(r["unidad"]), relacion_cn=_d3n(r["relacion_cn"]),
            registrado_por=_i(r["registrado_por"]),
        ) for r in meds
    ]
    aplicaciones = [
        BioflocAplicacionFilaOut(
            aplicacion_id=_i(r["aplicacion_id"]), fecha_hora=r["fecha_hora"], lote_id=_i(r["lote_id"]),
            lote_codigo=str(r["lote_codigo"]), tipo_aplicacion=str(r["tipo_aplicacion"]),
            producto_id=r["producto_id"], cantidad=_d4n(r["cantidad"]), unidad=r["unidad"],
            registrado_por=_i(r["registrado_por"]),
        ) for r in apls
    ]
    return ReporteBioflocOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        total_registros=len(mediciones) + len(aplicaciones), generado_en=_now(),
        mediciones=mediciones, aplicaciones=aplicaciones,
    )


def alimentacion(db: Session, fecha_desde=None, fecha_hasta=None,
                 lote_id: Optional[int] = None) -> ReporteAlimentacionOut:
    extra, extra_sql = {}, ""
    if lote_id is not None:
        extra["lote_id"] = lote_id
        extra_sql += " AND a.lote_id = :lote_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    fa = _filtro("a.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"SELECT COUNT(*) AS n FROM alimentaciones a WHERE 1=1 {fa} {extra_sql}", p)
    por_u = _rows(db, f"""
        SELECT un.simbolo AS unidad, COALESCE(SUM(a.cantidad), 0) AS cantidad
        FROM alimentaciones a
        JOIN productos p ON p.id = a.producto_id
        JOIN unidades un ON un.id = p.unidad_id
        WHERE 1=1 {fa} {extra_sql}
        GROUP BY un.simbolo ORDER BY un.simbolo
    """, p)
    rows = _rows(db, f"""
        SELECT a.id AS alimentacion_id, a.fecha_hora, a.lote_id, l.codigo AS lote_codigo,
               a.producto_id, p.codigo AS producto_codigo, un.simbolo AS unidad,
               a.cantidad, a.observaciones, a.registrado_por, u.nombre AS registrado_por_nombre
        FROM alimentaciones a
        JOIN lotes l ON l.id = a.lote_id
        JOIN productos p ON p.id = a.producto_id
        JOIN unidades un ON un.id = p.unidad_id
        LEFT JOIN usuarios u ON u.id = a.registrado_por
        WHERE 1=1 {fa} {extra_sql}
        ORDER BY a.fecha_hora DESC, a.id DESC
        LIMIT :lim
    """, p)
    filas = [
        AlimentacionFilaOut(
            alimentacion_id=_i(r["alimentacion_id"]), fecha_hora=r["fecha_hora"],
            lote_id=_i(r["lote_id"]), lote_codigo=str(r["lote_codigo"]),
            producto_id=_i(r["producto_id"]), producto_codigo=str(r["producto_codigo"]),
            unidad=str(r["unidad"]), cantidad=_d3(r["cantidad"]), observaciones=r["observaciones"],
            registrado_por=_i(r["registrado_por"]), registrado_por_nombre=r["registrado_por_nombre"],
        ) for r in rows
    ]
    return ReporteAlimentacionOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(),
        cantidad_por_unidad=[UnidadCantidadOut(unidad=str(r["unidad"]), cantidad=_d3(r["cantidad"])) for r in por_u],
        filas=filas,
    )


def equipos(db: Session, fecha_desde=None, fecha_hasta=None,
            activo: Optional[bool] = None) -> ReporteEquiposOut:
    extra_sql = ""
    p = _params(fecha_desde, fecha_hasta)
    if activo is not None:
        p["activo"] = activo
        extra_sql = " AND eq.activo = :activo"
    tot = _one(db, f"SELECT COUNT(*) AS n FROM equipos eq WHERE 1=1 {extra_sql}", p)
    rows = _rows(db, f"""
        SELECT eq.id AS equipo_id, eq.codigo, eq.nombre, te.nombre AS tipo, ee.nombre AS estado,
               eq.ubicacion, eq.activo
        FROM equipos eq
        JOIN tipos_equipo te ON te.id = eq.tipo_equipo_id
        JOIN estados_equipo ee ON ee.id = eq.estado_id
        WHERE 1=1 {extra_sql}
        ORDER BY eq.codigo
        LIMIT :lim
    """, p)
    filas = [
        EquipoFilaOut(
            equipo_id=_i(r["equipo_id"]), codigo=str(r["codigo"]), nombre=str(r["nombre"]),
            tipo=str(r["tipo"]), estado=str(r["estado"]), ubicacion=r["ubicacion"], activo=bool(r["activo"]),
        ) for r in rows
    ]
    return ReporteEquiposOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), filas=filas,
    )


def mantenimientos(db: Session, fecha_desde=None, fecha_hasta=None,
                   equipo_id: Optional[int] = None) -> ReporteMantenimientosOut:
    extra, extra_sql = {}, ""
    if equipo_id is not None:
        extra["equipo_id"] = equipo_id
        extra_sql += " AND m.equipo_id = :equipo_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    fm = _filtro("m.fecha", fecha_desde, fecha_hasta)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(m.costo), 0) AS total
        FROM mantenimientos m WHERE 1=1 {fm} {extra_sql}
    """, p)
    rows = _rows(db, f"""
        SELECT m.id AS mantenimiento_id, m.fecha, m.equipo_id, eq.codigo AS equipo_codigo,
               tm.nombre AS tipo, m.descripcion, m.costo, m.observaciones, m.registrado_por
        FROM mantenimientos m
        JOIN equipos eq ON eq.id = m.equipo_id
        JOIN tipos_mantenimiento tm ON tm.id = m.tipo_mantenimiento_id
        WHERE 1=1 {fm} {extra_sql}
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT :lim
    """, p)
    filas = [
        MantenimientoFilaOut(
            mantenimiento_id=_i(r["mantenimiento_id"]), fecha=r["fecha"], equipo_id=_i(r["equipo_id"]),
            equipo_codigo=str(r["equipo_codigo"]), tipo=str(r["tipo"]), descripcion=str(r["descripcion"]),
            costo=_d2(r["costo"]), observaciones=r["observaciones"], registrado_por=_i(r["registrado_por"]),
        ) for r in rows
    ]
    return ReporteMantenimientosOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), total_costo=_d2(tot.get("total")), filas=filas,
    )


def fallas(db: Session, fecha_desde=None, fecha_hasta=None,
           equipo_id: Optional[int] = None) -> ReporteFallasOut:
    extra, extra_sql = {}, ""
    if equipo_id is not None:
        extra["equipo_id"] = equipo_id
        extra_sql += " AND f.equipo_id = :equipo_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    ff = _filtro("f.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"""
        SELECT COUNT(*) AS n, COALESCE(SUM(f.costo), 0) AS total
        FROM fallas f WHERE 1=1 {ff} {extra_sql}
    """, p)
    rows = _rows(db, f"""
        SELECT f.id AS falla_id, f.fecha_hora, f.equipo_id, eq.codigo AS equipo_codigo,
               f.descripcion, f.impacto, f.solucion, f.costo, f.registrada_por
        FROM fallas f
        JOIN equipos eq ON eq.id = f.equipo_id
        WHERE 1=1 {ff} {extra_sql}
        ORDER BY f.fecha_hora DESC, f.id DESC
        LIMIT :lim
    """, p)
    filas = [
        FallaFilaOut(
            falla_id=_i(r["falla_id"]), fecha_hora=r["fecha_hora"], equipo_id=_i(r["equipo_id"]),
            equipo_codigo=str(r["equipo_codigo"]), descripcion=str(r["descripcion"]),
            impacto=r["impacto"], solucion=r["solucion"], costo=_d2(r["costo"]),
            registrada_por=_i(r["registrada_por"]),
        ) for r in rows
    ]
    return ReporteFallasOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), total_costo=_d2(tot.get("total")), filas=filas,
    )


def energia(db: Session, fecha_desde=None, fecha_hasta=None,
            tipo: Optional[str] = None) -> ReporteEnergiaOut:
    extra, extra_sql = {}, ""
    if tipo:
        extra["tipo"] = f"%{tipo}%"
        extra_sql += " AND ev.tipo ILIKE :tipo"
    p = _params(fecha_desde, fecha_hasta, extra)
    fe = _filtro("ev.fecha_hora_inicio", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"SELECT COUNT(*) AS n FROM eventos_energia ev WHERE 1=1 {fe} {extra_sql}", p)
    rows = _rows(db, f"""
        SELECT ev.id AS evento_id, ev.fecha_hora_inicio, ev.fecha_hora_fin, ev.tipo,
               ev.duracion_minutos, ev.respaldo_activado, ev.equipo_respaldo_id,
               ev.observaciones, ev.registrado_por
        FROM eventos_energia ev
        WHERE 1=1 {fe} {extra_sql}
        ORDER BY ev.fecha_hora_inicio DESC, ev.id DESC
        LIMIT :lim
    """, p)
    filas = [
        EnergiaFilaOut(
            evento_id=_i(r["evento_id"]), fecha_hora_inicio=r["fecha_hora_inicio"],
            fecha_hora_fin=r["fecha_hora_fin"], tipo=str(r["tipo"]),
            duracion_minutos=r["duracion_minutos"], respaldo_activado=bool(r["respaldo_activado"]),
            equipo_respaldo_id=r["equipo_respaldo_id"], observaciones=r["observaciones"],
            registrado_por=r["registrado_por"],
        ) for r in rows
    ]
    return ReporteEnergiaOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), filas=filas,
    )


def alarmas(db: Session, fecha_desde=None, fecha_hasta=None,
            estado_alarma_id: Optional[int] = None,
            tipo_alarma_id: Optional[int] = None) -> ReporteAlarmasOut:
    extra, extra_sql = {}, ""
    if estado_alarma_id is not None:
        extra["estado_alarma_id"] = estado_alarma_id
        extra_sql += " AND a.estado_alarma_id = :estado_alarma_id"
    if tipo_alarma_id is not None:
        extra["tipo_alarma_id"] = tipo_alarma_id
        extra_sql += " AND a.tipo_alarma_id = :tipo_alarma_id"
    p = _params(fecha_desde, fecha_hasta, extra)
    fa = _filtro("a.fecha_hora", fecha_desde, fecha_hasta, ts=True)
    tot = _one(db, f"SELECT COUNT(*) AS n FROM alarmas a WHERE 1=1 {fa} {extra_sql}", p)
    rows = _rows(db, f"""
        SELECT a.id AS alarma_id, a.fecha_hora, ta.nombre AS tipo, na.nombre AS nivel,
               ea.nombre AS estado, a.titulo, a.mensaje, a.equipo_id, eq.codigo AS equipo_codigo,
               a.lote_id, l.codigo AS lote_codigo, a.evento_energia_id, a.atendida_por, a.fecha_atencion
        FROM alarmas a
        JOIN tipos_alarma ta ON ta.id = a.tipo_alarma_id
        JOIN niveles_alarma na ON na.id = a.nivel_alarma_id
        JOIN estados_alarma ea ON ea.id = a.estado_alarma_id
        LEFT JOIN equipos eq ON eq.id = a.equipo_id
        LEFT JOIN lotes l ON l.id = a.lote_id
        WHERE 1=1 {fa} {extra_sql}
        ORDER BY a.fecha_hora DESC, a.id DESC
        LIMIT :lim
    """, p)
    filas = [
        AlarmaFilaOut(
            alarma_id=_i(r["alarma_id"]), fecha_hora=r["fecha_hora"], tipo=str(r["tipo"]),
            nivel=str(r["nivel"]), estado=str(r["estado"]), titulo=str(r["titulo"]),
            mensaje=str(r["mensaje"]), equipo_id=r["equipo_id"], equipo_codigo=r["equipo_codigo"],
            lote_id=r["lote_id"], lote_codigo=r["lote_codigo"], evento_energia_id=r["evento_energia_id"],
            atendida_por=r["atendida_por"], fecha_atencion=r["fecha_atencion"],
        ) for r in rows
    ]
    return ReporteAlarmasOut(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, total_registros=_i(tot.get("n")),
        generado_en=_now(), filas=filas,
    )
