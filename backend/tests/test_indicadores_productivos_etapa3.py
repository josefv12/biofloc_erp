"""Etapa 3 — indicadores productivos del lote (sin HTTP ni BD)."""
from decimal import Decimal

from app.services.indicadores_lote import (
    biomasa_kg,
    ganancia_biomasa_productiva_kg,
    ganancia_diaria_g,
    mortalidad_pct,
    sgr_pct_dia,
    supervivencia_biologica_pct,
)
from app.services.poblacion_lote import calcular_poblacion_disponible


def test_biomasa_inicial_3500_x_1g():
    assert biomasa_kg(3500, Decimal("1")) == Decimal("3.500")


def test_biomasa_actual_3400_x_28g():
    assert biomasa_kg(3400, Decimal("28")) == Decimal("95.200")


def test_biomasa_actual_3500_x_28g():
    assert biomasa_kg(3500, Decimal("28")) == Decimal("98.000")


def test_supervivencia_100_muertos():
    assert supervivencia_biologica_pct(3500, 100) == Decimal("97.14")
    assert mortalidad_pct(3500, 100) == Decimal("2.86")


def test_cosecha_parcial_no_baja_supervivencia():
    assert calcular_poblacion_disponible(3500, 100, 3000) == 400
    assert supervivencia_biologica_pct(3500, 100) == Decimal("97.14")
    assert mortalidad_pct(3500, 100) == Decimal("2.86")


def test_sin_mortalidad_ni_cosecha_ni_biometria():
    assert calcular_poblacion_disponible(3500, 0, 0) == 3500
    assert supervivencia_biologica_pct(3500, 0) == Decimal("100.00")
    assert mortalidad_pct(3500, 0) == Decimal("0.00")
    assert biomasa_kg(3500, Decimal("1")) == Decimal("3.500")


def test_gpd_dia_cero_nd():
    valor, motivo = ganancia_diaria_g(Decimal("27"), 0)
    assert valor is None
    assert motivo == "DIAS_CULTIVO_CERO"


def test_sgr_dia_cero_nd():
    valor, motivo = sgr_pct_dia(Decimal("1"), Decimal("28"), 0)
    assert valor is None
    assert motivo == "DIAS_CULTIVO_CERO"


def test_sgr_peso_no_positivo_nd():
    valor, motivo = sgr_pct_dia(Decimal("0"), Decimal("28"), 27)
    assert valor is None
    assert motivo == "SGR_REQUIERE_PESOS_POSITIVOS_Y_DIAS"
    valor, motivo = sgr_pct_dia(Decimal("1"), Decimal("-1"), 27)
    assert valor is None
    assert motivo == "SGR_REQUIERE_PESOS_POSITIVOS_Y_DIAS"


def test_sgr_caso_biometria_dia_27():
    valor, motivo = sgr_pct_dia(Decimal("1"), Decimal("28"), 27)
    assert motivo is None
    assert valor == Decimal("12.3415")


def test_gpd_caso_biometria_dia_27():
    valor, motivo = ganancia_diaria_g(Decimal("27"), 27)
    assert motivo is None
    assert valor == Decimal("1.000000")


def test_fca_sin_alimento_nd():
    ganancia, _ = ganancia_biomasa_productiva_kg(
        Decimal("98.000"), Decimal("3.500"), Decimal("0"),
        hay_cosecha=False, cosecha_con_peso=False,
    )
    assert ganancia == Decimal("94.500")
    from app.services.analisis_service import _fca_oficial, RAZON_SIN_ALIMENTO

    fca, motivo = _fca_oficial(None, RAZON_SIN_ALIMENTO, ganancia, None)
    assert fca is None
    assert motivo == RAZON_SIN_ALIMENTO
    fca, motivo = _fca_oficial(Decimal("0"), None, ganancia, None)
    assert fca is None
    assert motivo == RAZON_SIN_ALIMENTO


def test_fca_sin_ganancia_nd():
    from app.services.analisis_service import _fca_oficial, FCA_GANANCIA_NO_POSITIVA

    fca, motivo = _fca_oficial(Decimal("2"), None, Decimal("0"), None)
    assert fca is None
    assert motivo == FCA_GANANCIA_NO_POSITIVA
    fca, motivo = _fca_oficial(Decimal("2"), None, Decimal("-1"), None)
    assert fca is None
    assert motivo == FCA_GANANCIA_NO_POSITIVA


def test_biomasa_productiva_con_cosecha():
    ganancia, motivo = ganancia_biomasa_productiva_kg(
        Decimal("95.200"), Decimal("3.500"), Decimal("84.000"),
        hay_cosecha=True, cosecha_con_peso=True,
    )
    assert motivo is None
    assert ganancia == Decimal("175.700")
