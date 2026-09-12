from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.costos_lote import CostosLoteOut

D2 = Decimal("0.01")
D3 = Decimal("0.001")


def _d(value, quant):
    return Decimal(str(value or 0)).quantize(quant, rounding=ROUND_HALF_UP)


def obtener_costos_lote(db: Session, lote_id: int) -> CostosLoteOut:
    lote = db.execute(text("""
        SELECT id, codigo, estanque_id
        FROM biofloc.lotes
        WHERE id = :id
    """), {"id": lote_id}).mappings().first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    row = db.execute(text("""
        SELECT
            COALESCE((
                SELECT SUM(mi.costo_total)
                FROM biofloc.movimientos_inventario mi
                JOIN biofloc.alimentaciones a ON a.id = mi.referencia_id
                WHERE mi.referencia_tipo = 'ALIMENTACION'
                  AND mi.referencia_id IS NOT NULL
                  AND a.lote_id = :lote_id
                  AND mi.costo_total IS NOT NULL
            ), 0) AS alimento,
            COALESCE((
                SELECT SUM(
                    CASE LOWER(TRIM(u.simbolo))
                        WHEN 'kg' THEN a.cantidad
                        WHEN 'g' THEN a.cantidad / 1000
                        ELSE 0
                    END
                )
                FROM biofloc.alimentaciones a
                JOIN biofloc.productos p ON p.id = a.producto_id
                JOIN biofloc.unidades u ON u.id = p.unidad_id
                WHERE a.lote_id = :lote_id
            ), 0) AS alimento_suministrado,
            COALESCE((
                SELECT SUM(g.valor)
                FROM biofloc.gastos g
                JOIN biofloc.categorias_gasto cg ON cg.id = g.categoria_id
                WHERE g.lote_id = :lote_id
                  AND cg.nombre = 'ALEVINOS'
            ), 0) AS alevinos,
            COALESCE((
                SELECT SUM(g.valor)
                FROM biofloc.gastos g
                JOIN biofloc.categorias_gasto cg ON cg.id = g.categoria_id
                WHERE g.lote_id = :lote_id
                  AND cg.nombre <> 'ALEVINOS'
            ), 0) AS otros_costos,
            COALESCE((
                SELECT SUM(c.peso_total_kg)
                FROM biofloc.cosechas c
                WHERE c.lote_id = :lote_id
            ), 0) AS kg_cosechados,
            COALESCE((
                SELECT SUM(d.cantidad)
                FROM biofloc.detalles_venta d
                WHERE d.lote_id = :lote_id
            ), 0) AS kg_vendidos,
            COALESCE((
                SELECT SUM(d.subtotal)
                FROM biofloc.detalles_venta d
                WHERE d.lote_id = :lote_id
            ), 0) AS ventas,
            COALESCE((
                SELECT SUM(g.valor)
                FROM biofloc.gastos g
                WHERE g.estanque_id = :estanque_id
            ), 0) AS costos_estanque
    """), {"lote_id": lote_id, "estanque_id": lote["estanque_id"]}).mappings().one()

    alimento = _d(row["alimento"], D2)
    alevinos = _d(row["alevinos"], D2)
    otros = _d(row["otros_costos"], D2)
    directo = alimento + alevinos + otros
    kg_cosechados = _d(row["kg_cosechados"], D3)
    kg_vendidos = _d(row["kg_vendidos"], D3)
    costo_por_kg = (directo / kg_cosechados).quantize(D2, rounding=ROUND_HALF_UP) if kg_cosechados > 0 else None
    costo_ventas = (kg_vendidos * costo_por_kg).quantize(D2, rounding=ROUND_HALF_UP) if costo_por_kg is not None else Decimal("0.00")
    ventas = _d(row["ventas"], D2)
    utilidad = (ventas - costo_ventas).quantize(D2, rounding=ROUND_HALF_UP) if costo_por_kg is not None else None
    margen = ((utilidad / ventas) * 100).quantize(D2, rounding=ROUND_HALF_UP) if utilidad is not None and ventas else None

    return CostosLoteOut(
        lote_id=int(lote["id"]), codigo=str(lote["codigo"]), estanque_id=int(lote["estanque_id"]),
        alevinos=alevinos, alimento=alimento, otros_costos_directos=otros,
        costo_directo_lote=directo,
        costos_estanque_no_asignados=_d(row["costos_estanque"], D2),
        kg_alimento_suministrado=_d(row["alimento_suministrado"], D3),
        kg_cosechados=kg_cosechados, costo_por_kg=costo_por_kg,
        ventas=ventas, kg_vendidos=kg_vendidos, costo_ventas_estimado=costo_ventas,
        utilidad_bruta_estimada=utilidad, margen_bruto_estimado_pct=margen,
    )
