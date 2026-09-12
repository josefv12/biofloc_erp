"""Pruebas unitarias de costos y rentabilidad estimada por lote."""
from decimal import Decimal

from app.services.finanzas_service import calcular_costos_financieros_lote


def test_calculo_financiero_lote_completo():
    resultado = calcular_costos_financieros_lote(
        costo_alimento=Decimal("35000"),
        gastos_lote=Decimal("1750000"),
        kg_cosechados=Decimal("170"),
        kg_vendidos=Decimal("30"),
        ventas=Decimal("360000"),
    )

    assert resultado["costo_produccion"] == Decimal("1785000.00")
    assert resultado["costo_por_kg"] == Decimal("10500.00")
    assert resultado["costo_ventas_estimado"] == Decimal("315000.00")
    assert resultado["utilidad_bruta"] == Decimal("45000.00")
    assert resultado["margen_bruto_pct"] == Decimal("12.50")


def test_calculo_financiero_sin_cosecha_no_inventa_costo_por_kg():
    resultado = calcular_costos_financieros_lote(
        costo_alimento=Decimal("10000"),
        gastos_lote=Decimal("5000"),
        kg_cosechados=Decimal("0"),
        kg_vendidos=Decimal("0"),
        ventas=Decimal("0"),
    )

    assert resultado["costo_produccion"] == Decimal("15000.00")
    assert resultado["costo_por_kg"] is None
    assert resultado["costo_ventas_estimado"] == Decimal("0.00")
    assert resultado["utilidad_bruta"] is None
    assert resultado["margen_bruto_pct"] is None


def test_calculo_financiero_admite_costos_cero():
    resultado = calcular_costos_financieros_lote(
        costo_alimento=Decimal("0"),
        gastos_lote=Decimal("0"),
        kg_cosechados=Decimal("100"),
        kg_vendidos=Decimal("25"),
        ventas=Decimal("300000"),
    )

    assert resultado["costo_produccion"] == Decimal("0.00")
    assert resultado["costo_por_kg"] == Decimal("0.00")
    assert resultado["costo_ventas_estimado"] == Decimal("0.00")
    assert resultado["utilidad_bruta"] == Decimal("300000.00")
    assert resultado["margen_bruto_pct"] == Decimal("100.00")
