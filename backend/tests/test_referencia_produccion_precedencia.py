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



def test_referencia_no_admite_semana_cero_en_servicio():
    from fastapi import HTTPException
    from app.services.referencia_produccion_service import _validar_rango
    try:
        _validar_rango(0, 1)
    except HTTPException as exc:
        assert exc.status_code == 422
        assert ">= 1" in str(exc.detail)
        return
    raise AssertionError("La semana 0 no debe ser una referencia productiva válida")


def test_update_de_referencia_valida_rango_de_raciones_con_valor_existente():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/services/referencia_produccion_service.py").read_text(encoding="utf-8")
    assert 'cambios.get("raciones_min", row.raciones_min)' in source
    assert 'cambios.get("raciones_max", row.raciones_max)' in source
    assert "raciones_max no puede ser menor que raciones_min" in source
