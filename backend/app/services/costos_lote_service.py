from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.costos_lote import CostosLoteOut, CostoLoteDetalle

D2 = Decimal("0.01")
D3 = Decimal("0.001")


def _d(value, quant):
    return Decimal(str(value or 0)).quantize(quant, rounding=ROUND_HALF_UP)


def obtener_costos_lote(db: Session, lote_id: int) -> CostosLoteOut:
    lote = db.execute(text("""
        SELECT id, codigo, estanque_id, cantidad_sembrada
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
                SELECT SUM(mi.costo_total)
                FROM biofloc.movimientos_inventario mi
                WHERE mi.referencia_tipo = 'SIEMBRA'
                  AND mi.referencia_id = :lote_id
                  AND mi.costo_total IS NOT NULL
            ), (
                SELECT SUM(g.valor)
                FROM biofloc.gastos g
                JOIN biofloc.categorias_gasto cg ON cg.id = g.categoria_id
                WHERE g.lote_id = :lote_id
                  AND cg.nombre = 'ALEVINOS'
            ), 0) AS alevinos,
            COALESCE((
                SELECT SUM(mi.costo_total)
                FROM biofloc.movimientos_inventario mi
                JOIN biofloc.aplicaciones_biofloc ab
                  ON ab.id = mi.referencia_id
                WHERE mi.referencia_tipo = 'APLICACION_BIOFLOC'
                  AND mi.referencia_id IS NOT NULL
                  AND ab.lote_id = :lote_id
                  AND mi.costo_total IS NOT NULL
            ), 0)
            +
            COALESCE((
                SELECT SUM(mi.costo_total)
                FROM biofloc.movimientos_inventario mi
                JOIN biofloc.acondicionamientos_biofloc_estanque ac
                  ON ac.id = mi.referencia_id
                WHERE mi.referencia_tipo = 'ACONDICIONAMIENTO_BIOFLOC'
                  AND mi.referencia_id IS NOT NULL
                  AND ac.lote_id = :lote_id
                  AND mi.costo_total IS NOT NULL
            ), 0) AS biofloc_insumos,
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
    biofloc_insumos = _d(row["biofloc_insumos"], D2)
    otros = _d(row["otros_costos"], D2)
    # Los insumos Biofloc salen de inventario como costo directo del lote.
    # Se agregan a otros_costos_directos para no dejar ese consumo fuera
    # del costo por kg sin romper el contrato actual de la API.
    otros_sin_biofloc = otros
    otros = otros_sin_biofloc + biofloc_insumos
    directo = alimento + alevinos + otros
    kg_cosechados = _d(row["kg_cosechados"], D3)
    kg_vendidos = _d(row["kg_vendidos"], D3)
    costo_por_kg = (directo / kg_cosechados).quantize(D2, rounding=ROUND_HALF_UP) if kg_cosechados > 0 else None
    peces_sembrados = int(lote["cantidad_sembrada"] or 0)
    costo_por_pez = (directo / Decimal(peces_sembrados)).quantize(D2, rounding=ROUND_HALF_UP) if peces_sembrados > 0 else None
    costo_ventas = (kg_vendidos * costo_por_kg).quantize(D2, rounding=ROUND_HALF_UP) if costo_por_kg is not None else Decimal("0.00")
    ventas = _d(row["ventas"], D2)
    utilidad = (ventas - costo_ventas).quantize(D2, rounding=ROUND_HALF_UP) if costo_por_kg is not None else None
    margen = ((utilidad / ventas) * 100).quantize(D2, rounding=ROUND_HALF_UP) if utilidad is not None and ventas else None

    detalle_rows = db.execute(text("""
        SELECT
            mi.fecha_hora::text AS fecha,
            CASE
                WHEN mi.referencia_tipo = 'SIEMBRA' THEN 'Alevinos'
                WHEN mi.referencia_tipo = 'ALIMENTACION' THEN 'Alimento'
                WHEN mi.referencia_tipo IN ('ACONDICIONAMIENTO_BIOFLOC', 'APLICACION_BIOFLOC') THEN 'Biofloc'
                ELSE 'Inventario'
            END AS categoria,
            COALESCE(p.nombre, 'Producto #' || mi.producto_id::text) AS concepto,
            mi.cantidad,
            COALESCE(u.simbolo, '') AS unidad,
            mi.costo_unitario,
            mi.costo_total,
            mi.referencia_tipo,
            mi.referencia_id
        FROM biofloc.movimientos_inventario mi
        JOIN biofloc.productos p ON p.id = mi.producto_id
        LEFT JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE mi.costo_total > 0
          AND (
            (mi.referencia_tipo = 'SIEMBRA' AND mi.referencia_id = :lote_id)
            OR (mi.referencia_tipo = 'ALIMENTACION' AND EXISTS (
                SELECT 1 FROM biofloc.alimentaciones a
                WHERE a.id = mi.referencia_id AND a.lote_id = :lote_id
            ))
            OR (mi.referencia_tipo = 'ACONDICIONAMIENTO_BIOFLOC' AND EXISTS (
                SELECT 1 FROM biofloc.acondicionamientos_biofloc_estanque ac
                WHERE ac.id = mi.referencia_id AND ac.lote_id = :lote_id
            ))
            OR (mi.referencia_tipo = 'APLICACION_BIOFLOC' AND EXISTS (
                SELECT 1 FROM biofloc.aplicaciones_biofloc ab
                WHERE ab.id = mi.referencia_id AND ab.lote_id = :lote_id
            ))
          )
        ORDER BY mi.fecha_hora, mi.id
    """), {"lote_id": lote_id}).mappings().all()

    gasto_rows = db.execute(text("""
        SELECT
            g.fecha::text AS fecha,
            CASE WHEN cg.nombre = 'ALEVINOS' THEN 'Alevinos' ELSE 'Otros' END AS categoria,
            g.descripcion AS concepto,
            NULL::numeric AS cantidad,
            NULL::text AS unidad,
            NULL::numeric AS costo_unitario,
            g.valor AS costo_total,
            'GASTO' AS referencia_tipo,
            g.id AS referencia_id
        FROM biofloc.gastos g
        JOIN biofloc.categorias_gasto cg ON cg.id = g.categoria_id
        WHERE g.lote_id = :lote_id
          AND g.valor > 0
        ORDER BY g.fecha, g.id
    """), {"lote_id": lote_id}).mappings().all()

    detalle = [
        CostoLoteDetalle(
            fecha=str(r["fecha"]),
            categoria=str(r["categoria"]),
            concepto=str(r["concepto"]),
            cantidad=_d(r["cantidad"], D3) if r["cantidad"] is not None else None,
            unidad=str(r["unidad"]) if r["unidad"] else None,
            costo_unitario=_d(r["costo_unitario"], D2) if r["costo_unitario"] is not None else None,
            costo_total=_d(r["costo_total"], D2),
            referencia_tipo=str(r["referencia_tipo"]) if r["referencia_tipo"] else None,
            referencia_id=int(r["referencia_id"]) if r["referencia_id"] is not None else None,
        )
        for r in [*detalle_rows, *gasto_rows]
    ]
    detalle.sort(key=lambda r: (r.fecha, r.referencia_id or 0))

    return CostosLoteOut(
        lote_id=int(lote["id"]), codigo=str(lote["codigo"]), estanque_id=int(lote["estanque_id"]),
        alevinos=alevinos, alimento=alimento, biofloc_insumos=biofloc_insumos, otros_costos_directos=otros,
        costo_directo_lote=directo,
        costos_estanque_no_asignados=_d(row["costos_estanque"], D2),
        kg_alimento_suministrado=_d(row["alimento_suministrado"], D3),
        peces_sembrados=peces_sembrados, costo_por_pez=costo_por_pez,
        kg_cosechados=kg_cosechados, costo_por_kg=costo_por_kg,
        ventas=ventas, kg_vendidos=kg_vendidos, costo_ventas_estimado=costo_ventas,
        utilidad_bruta_estimada=utilidad, margen_bruto_estimado_pct=margen,
        detalle=detalle,
    )
