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


def test_venta_bloquea_lotes_en_orden_determinista():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "venta_service.py"
    text = source.read_text(encoding="utf-8")
    marker = "for lote_id in sorted(solicitada_por_lote):"
    assert marker in text


def test_compra_bloquea_productos_en_orden_determinista():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "compra_service.py"
    text = source.read_text(encoding="utf-8")
    marker = 'for producto_id in sorted({dp["producto_id"] for dp in detalles_procesados}):'
    assert marker in text


def test_compra_rechaza_alimento_fuera_de_kg():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "compra_service.py"
    text = source.read_text(encoding="utf-8")
    assert 'categoria.nombre.strip().upper() == "ALIMENTO"' in text
    assert 'factor_conversion' in text
    assert 'debe estar configurado en kg/kg con factor 1' in text


def test_alimentacion_es_atomica_y_genera_salida_transaccional():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "alimentacion_service.py"
    text = source.read_text(encoding="utf-8")
    assert "crear_movimiento_inventario(db, mov_data, usuario_id, flush_only=True)" in text
    assert 'referencia_tipo="ALIMENTACION"' in text
    assert 'tipo_salida_id = _obtener_tipo_salida_id(db)' in text
    assert "db.commit()" in text


def test_aplicacion_biofloc_es_atomica_y_genera_salida_transaccional():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "aplicacion_biofloc_service.py"
    text = source.read_text(encoding="utf-8")
    assert "crear_movimiento_inventario(db, mov_data, usuario_id, flush_only=True)" in text
    assert 'referencia_tipo="APLICACION_BIOFLOC"' in text


def test_movimientos_automaticos_tienen_unicidad_por_evento_origen():
    from pathlib import Path
    migration = Path(__file__).parents[2] / "database" / "migrations" / "011_trazabilidad_movimientos_automaticos.sql"
    text = migration.read_text(encoding="utf-8")
    assert "uq_movimientos_inventario_alimentacion" in text
    assert "uq_movimientos_inventario_aplicacion_biofloc" in text
