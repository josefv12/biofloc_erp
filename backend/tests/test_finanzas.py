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


def test_finanzas_historical_uses_colombia_local_date_expression():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "finanzas_service.py"
    text = source.read_text(encoding="utf-8")
    assert "AT TIME ZONE 'America/Bogota'" in text
    assert "CAST(cos.fecha_hora AS date)" not in text
    assert "CAST(a.fecha_hora AS date)" not in text


def test_calculo_financiero_rechaza_kg_vendidos_superiores_a_cosechados():
    import pytest
    with pytest.raises(Exception):
        calcular_costos_financieros_lote(
            costo_alimento=Decimal("100000"),
            gastos_lote=Decimal("50000"),
            kg_cosechados=Decimal("100"),
            kg_vendidos=Decimal("101"),
            ventas=Decimal("500000"),
        )


def test_calculo_financiero_rechaza_cantidades_negativas():
    import pytest
    with pytest.raises(Exception):
        calcular_costos_financieros_lote(
            costo_alimento=Decimal("100000"),
            gastos_lote=Decimal("50000"),
            kg_cosechados=Decimal("100"),
            kg_vendidos=Decimal("-1"),
            ventas=Decimal("500000"),
        )


def test_calculo_financiero_rechaza_costos_negativos():
    import pytest

    casos = [
        {"costo_alimento": Decimal("-1"), "gastos_lote": Decimal("0"), "kg_cosechados": Decimal("100")},
        {"costo_alimento": Decimal("0"), "gastos_lote": Decimal("-1"), "kg_cosechados": Decimal("100")},
        {"costo_alimento": Decimal("0"), "gastos_lote": Decimal("0"), "kg_cosechados": Decimal("100"), "ventas": Decimal("-1")},
    ]
    for caso in casos:
        with pytest.raises(Exception):
            calcular_costos_financieros_lote(
                kg_vendidos=Decimal("0"),
                ventas=caso.get("ventas", Decimal("0")),
                costo_alimento=caso["costo_alimento"],
                gastos_lote=caso["gastos_lote"],
                kg_cosechados=caso["kg_cosechados"],
            )


def test_dashboard_timestamps_use_colombia_local_date():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app/services/dashboard_service.py"
    text = source.read_text(encoding="utf-8")
    assert "(AT TIME ZONE 'America/Bogota')::date" in text
    assert "CAST({col} AS date)" not in text
