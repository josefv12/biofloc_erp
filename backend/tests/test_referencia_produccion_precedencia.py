"""Precedencia al resolver referencias_produccion solapadas (sin BD)."""
from types import SimpleNamespace

from app.services.referencia_produccion_service import _precedencia, _resolver


def _ref(ref_id: int, desde: int, hasta: int) -> SimpleNamespace:
    return SimpleNamespace(id=ref_id, semana_desde=desde, semana_hasta=hasta, activo=True)


def test_semana_1_prefiere_rango_0_1_sobre_1_2():
    candidatas = [_ref(1, 0, 1), _ref(2, 1, 2)]
    elegida = _resolver(candidatas, 1)
    assert elegida.id == 1


def test_semana_10_prefiere_rango_9_10_sobre_10_11():
    candidatas = [_ref(1, 9, 10), _ref(2, 10, 11)]
    elegida = _resolver(candidatas, 10)
    assert elegida.id == 1


def test_semana_10_exacta_gana_sobre_rangos_amplios():
    candidatas = [_ref(1, 9, 10), _ref(2, 10, 10), _ref(3, 10, 11)]
    elegida = _resolver(candidatas, 10)
    assert elegida.id == 2


def test_precedencia_exacta_es_mejor_que_ancla_fin():
    assert _precedencia(_ref(1, 10, 10), 10) < _precedencia(_ref(2, 9, 10), 10)


def test_cobertura_semana_desde_hasta_inclusivo():
    candidatas = [_ref(1, 9, 16)]
    assert _resolver(candidatas, 9).id == 1
    assert _resolver(candidatas, 10).id == 1
    assert _resolver(candidatas, 16).id == 1
    assert _resolver(candidatas, 8) is None
    assert _resolver(candidatas, 17) is None

