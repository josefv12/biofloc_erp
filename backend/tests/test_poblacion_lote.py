"""Pruebas unitarias de población disponible (sin HTTP ni BD)."""
from decimal import Decimal
from types import SimpleNamespace

from fastapi import HTTPException

from app.services.analisis_service import FACTOR_A_KG, _alimento_kg
from app.schemas.analisis import AlimentoUnidadOut
from app.services.cosecha_service import _peso_promedio_g
from app.services.poblacion_lote import (
    calcular_poblacion_disponible,
    exigir_lote_en_produccion,
    mensaje_cosecha_excede,
    mensaje_mortalidad_excede,
)


def test_caso_a_disponible_400():
    assert calcular_poblacion_disponible(3500, 100, 3000) == 400


def test_caso_b_disponible_cosecha_3400():
    assert calcular_poblacion_disponible(3500, 100, 0) == 3400


def test_no_permite_exceso():
    assert 401 > calcular_poblacion_disponible(3500, 100, 3000)
    assert 3401 > calcular_poblacion_disponible(3500, 100, 0)


def test_mensajes_negocio():
    assert "500" in mensaje_mortalidad_excede(500, 400)
    assert "400" in mensaje_mortalidad_excede(500, 400)
    assert mensaje_cosecha_excede(3401, 3400) == (
        "No se pueden cosechar 3401 peces. La población disponible es 3400."
    )


def test_fca_factor_solo_g_y_kg():
    assert FACTOR_A_KG == {"kg": Decimal("1"), "g": Decimal("0.001")}


def test_alimento_kg_gramos_queda_en_3_decimales():
    total, razon = _alimento_kg(
        [AlimentoUnidadOut(unidad="g", cantidad=Decimal("3.500"))]
    )
    assert razon is None
    assert total == Decimal("0.004")

    total, razon = _alimento_kg(
        [
            AlimentoUnidadOut(unidad="kg", cantidad=Decimal("0.5")),
            AlimentoUnidadOut(unidad="g", cantidad=Decimal("500")),
        ]
    )
    assert razon is None
    assert total is not None
    assert total == Decimal("0.5") + Decimal("0.5")


def test_alimento_unidad_no_masica_no_se_convierte():
    total, razon = _alimento_kg(
        [AlimentoUnidadOut(unidad="mL", cantidad=Decimal("100"))]
    )
    assert total is None
    assert razon == "UNIDAD_ALIMENTO_INCOMPATIBLE"


def test_peso_promedio_cosecha_desde_peso_total():
    assert _peso_promedio_g(Decimal("150.000"), 3000) == Decimal("50.000")
    assert _peso_promedio_g(Decimal("170.000"), 3400) == Decimal("50.000")


def test_lote_activo_admite_registros():
    lote = SimpleNamespace(estado=SimpleNamespace(nombre="ACTIVO"), estado_id=1)
    exigir_lote_en_produccion(None, lote)  # type: ignore[arg-type]


def test_lote_finalizado_rechaza_registros():
    lote = SimpleNamespace(estado=SimpleNamespace(nombre="FINALIZADO"), estado_id=2)
    try:
        exigir_lote_en_produccion(None, lote)  # type: ignore[arg-type]
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "FINALIZADO" in str(exc.detail)
        return
    raise AssertionError("Debió rechazar el lote FINALIZADO")
