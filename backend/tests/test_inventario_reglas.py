from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.movimiento_inventario_service import _tipo_y_efecto
from app.services.validaciones_fecha import validar_fecha_no_futura, validar_no_futuro


def test_catalogo_movimientos_efecto_fijo():
    assert _tipo_y_efecto(SimpleNamespace(nombre="ENTRADA"), None) == 1
    assert _tipo_y_efecto(SimpleNamespace(nombre="SALIDA"), None) == -1


def test_ajuste_requiere_direccion():
    assert _tipo_y_efecto(SimpleNamespace(nombre="AJUSTE"), 1) == 1
    assert _tipo_y_efecto(SimpleNamespace(nombre="AJUSTE"), -1) == -1
    with pytest.raises(Exception):
        _tipo_y_efecto(SimpleNamespace(nombre="AJUSTE"), None)


def test_tipo_inventario_personalizado_no_permitido():
    with pytest.raises(Exception):
        _tipo_y_efecto(SimpleNamespace(nombre="AJUSTE_POS"), 1)


def test_fecha_hora_futura_rechazada():
    with pytest.raises(Exception):
        validar_no_futuro(datetime.now(timezone.utc) + timedelta(minutes=5))


def test_fecha_colombia_futura_rechazada():
    with pytest.raises(Exception):
        validar_fecha_no_futura(date.today() + timedelta(days=1))


def test_movimiento_salida_toma_bloqueo_antes_de_valorar():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "movimiento_inventario_service.py"
    text = source.read_text(encoding="utf-8")
    lock = "with_for_update()"
    outbound = text.index("if efecto == -1:")
    cost = text.index("_costo_promedio_stock_as_of", outbound)
    assert text.index(lock, outbound) < cost
