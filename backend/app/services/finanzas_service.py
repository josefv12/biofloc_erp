from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.finanzas import DashboardFinanzasOut, FinanzasLoteOut

D2 = Decimal("0.01")
D3 = Decimal("0.001")
ZERO = Decimal("0")


def _d2(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(D2, rounding=ROUND_HALF_UP)


def _d3(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(D3, rounding=ROUND_HALF_UP)


def _params(fecha_desde: Optional[date], fecha_hasta: Optional[date]) -> dict:
    return {k: v for k, v in (("fecha_desde", fecha_desde), ("fecha_hasta", fecha_hasta)) if v is not None}


def calcular_finanzas(
    db: Session,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> DashboardFinanzasOut:
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise HTTPException(status_code=422, detail="fecha_desde debe ser <= fecha_hasta")

    p = _params(fecha_desde, fecha_hasta)
    where_sale = ""
    if fecha_desde is not None:
        where_sale += " AND v.fecha >= :fecha_desde"
    if fecha_hasta is not None:
        where_sale += " AND v.fecha <= :fecha_hasta"

    rows = db.execute(text(f"""
        SELECT
            l.id AS lote_id,
            l.codigo,
            v.fecha AS fecha_venta,
            d.id AS detalle_id,
            d.cantidad AS kg_vendidos,
            d.subtotal AS ventas,
            COALESCE((
                SELECT SUM(cos.peso_total_kg)
                FROM biofloc.cosechas cos
                WHERE cos.lote_id = l.id
                  AND CAST(cos.fecha_hora AS date) <= v.fecha
            ), 0) AS kg_cosechados,
            COALESCE((
                SELECT SUM(mi.costo_total)
                FROM biofloc.movimientos_inventario mi
                JOIN biofloc.alimentaciones a
                  ON a.id = mi.referencia_id
                WHERE mi.referencia_tipo = 'ALIMENTACION'
                  AND a.lote_id = l.id
                  AND CAST(a.fecha_hora AS date) <= v.fecha
                  AND mi.costo_total IS NOT NULL
            ), 0) AS costo_alimento,
            COALESCE((
                SELECT SUM(g.valor)
                FROM biofloc.gastos g
                WHERE g.lote_id = l.id AND g.fecha <= v.fecha
            ), 0) AS gastos_lote
        FROM biofloc.detalles_venta d
        JOIN biofloc.ventas v ON v.id = d.venta_id
        JOIN biofloc.lotes l ON l.id = d.lote_id
        WHERE 1=1 {where_sale}
        ORDER BY l.id, v.fecha, d.id
    """), p).mappings().all()

    lotes = {}
    total_ventas = ZERO
    total_cogs = ZERO
    total_kg = ZERO

    for r in rows:
        lote_id = int(r["lote_id"])
        ventas = Decimal(str(r["ventas"] or 0))
        kg_vendidos = Decimal(str(r["kg_vendidos"] or 0))
        kg_cosechados = Decimal(str(r["kg_cosechados"] or 0))
        alimento = Decimal(str(r["costo_alimento"] or 0))
        gastos_lote = Decimal(str(r["gastos_lote"] or 0))
        costo_produccion = alimento + gastos_lote
        costo_por_kg = costo_produccion / kg_cosechados if kg_cosechados > ZERO else ZERO
        cogs = kg_vendidos * costo_por_kg

        item = lotes.setdefault(lote_id, {
            "codigo": str(r["codigo"]),
            "ventas": ZERO,
            "kg_vendidos": ZERO,
            "kg_cosechados": ZERO,
            "costo_alimento": ZERO,
            "gastos_lote": ZERO,
            "costo_produccion": ZERO,
            "costo_ventas_estimado": ZERO,
        })
        item["ventas"] += ventas
        item["kg_vendidos"] += kg_vendidos
        item["kg_cosechados"] = max(item["kg_cosechados"], kg_cosechados)
        item["costo_alimento"] = max(item["costo_alimento"], alimento)
        item["gastos_lote"] = max(item["gastos_lote"], gastos_lote)
        item["costo_produccion"] = max(item["costo_produccion"], costo_produccion)
        item["costo_ventas_estimado"] += cogs

        total_ventas += ventas
        total_cogs += cogs
        total_kg += kg_vendidos

    # Es el costo acumulado de producción de los lotes que tienen ventas en el
    # periodo consultado. No debe confundirse con COGS/costo de ventas: el COGS
    # solo representa la parte del costo de producción correspondiente a los kg
    # vendidos.
    total_production_cost = sum(
        (item["costo_produccion"] for item in lotes.values()),
        ZERO,
    )

    gasto_periodo = db.execute(text("""
        SELECT COALESCE(SUM(g.valor), 0)
        FROM biofloc.gastos g
        WHERE g.lote_id IS NULL
          AND g.estanque_id IS NULL
          AND (:fecha_desde IS NULL OR g.fecha >= :fecha_desde)
          AND (:fecha_hasta IS NULL OR g.fecha <= :fecha_hasta)
    """), {"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}).scalar()
    gastos_operativos = Decimal(str(gasto_periodo or 0))

    utilidad_bruta = total_ventas - total_cogs
    utilidad_neta = utilidad_bruta - gastos_operativos
    margen_bruto = (utilidad_bruta / total_ventas * 100) if total_ventas else None
    margen_neto = (utilidad_neta / total_ventas * 100) if total_ventas else None
    costo_promedio = total_cogs / total_kg if total_kg else ZERO

    salida = []
    for lote_id, x in sorted(lotes.items(), key=lambda kv: kv[1]["ventas"], reverse=True):
        utilidad = x["ventas"] - x["costo_ventas_estimado"]
        margen = (utilidad / x["ventas"] * 100) if x["ventas"] else None
        salida.append(FinanzasLoteOut(
            lote_id=lote_id,
            codigo=x["codigo"],
            ventas=_d2(x["ventas"]),
            kg_vendidos=_d3(x["kg_vendidos"]),
            kg_cosechados=_d3(x["kg_cosechados"]),
            costo_alimento=_d2(x["costo_alimento"]),
            gastos_lote=_d2(x["gastos_lote"]),
            costo_produccion=_d2(x["costo_produccion"]),
            costo_por_kg=_d2(x["costo_produccion"] / x["kg_cosechados"] if x["kg_cosechados"] else 0),
            costo_ventas_estimado=_d2(x["costo_ventas_estimado"]),
            utilidad_bruta=_d2(utilidad),
            margen_bruto_pct=(Decimal(str(margen)).quantize(D2, rounding=ROUND_HALF_UP) if margen is not None else None),
        ))

    return DashboardFinanzasOut(
        periodo_desde=fecha_desde,
        periodo_hasta=fecha_hasta,
        ventas=_d2(total_ventas),
        costo_ventas_estimado=_d2(total_cogs),
        utilidad_bruta=_d2(utilidad_bruta),
        gastos_operativos=_d2(gastos_operativos),
        utilidad_neta=_d2(utilidad_neta),
        margen_bruto_pct=(Decimal(str(margen_bruto)).quantize(D2, rounding=ROUND_HALF_UP) if margen_bruto is not None else None),
        margen_neto_pct=(Decimal(str(margen_neto)).quantize(D2, rounding=ROUND_HALF_UP) if margen_neto is not None else None),
        kg_vendidos=_d3(total_kg),
        costo_promedio_kg_vendido=_d2(costo_promedio),
        costo_produccion_lotes=_d2(total_production_cost),
        lotes_con_ventas=len(lotes),
        lotes=salida,
        metodologia=(
            "Costo por lote: el alimento se toma del costo registrado en cada salida de inventario generada por una alimentación del lote; "
            "por tanto, solo se imputa al lote el alimento realmente suministrado. Los demás costos directos se toman de gastos asociados al lote. "
            "Los costos registrados a nivel de estanque se conservan separados para su posterior asignación entre lotes, evitando repartirlos arbitrariamente. "
            "El costo por kg se obtiene sobre kg cosechados acumulados hasta cada venta; el costo de ventas es kg vendidos × costo promedio/kg. "
            "Costo producción de lotes corresponde al costo acumulado de producción de los lotes con ventas en el periodo; no es COGS."
        ),
    )
