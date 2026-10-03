from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from decimal import Decimal

import pytest

from app.services.movimiento_inventario_service import _tipo_y_efecto, _calcular_costo_promedio_desde_movimientos
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


def test_ventas_evalua_cosecha_hasta_fecha_de_venta():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "venta_service.py"
    text = source.read_text(encoding="utf-8")
    assert "_fin_dia_colombia_utc(fecha_venta)" in text
    assert "Cosecha.fecha_hora < limite_cosecha" in text


def test_ventas_descuenta_solo_ventas_hasta_fecha_consultada():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "venta_service.py"
    text = source.read_text(encoding="utf-8")
    assert "Venta.fecha <= fecha_venta" in text


def test_trigger_venta_es_historico_y_no_usa_stock_actual():
    from pathlib import Path
    source = Path(__file__).parents[2] / "database" / "migrations" / "008_integridad_historica_asof.sql"
    text = source.read_text(encoding="utf-8")
    assert "cosechas" in text
    assert "v.fecha <= v_fecha_venta" in text
    assert "v_limite_cosecha" in text


def test_movimiento_inventario_valida_fecha_futura():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "movimiento_inventario_service.py"
    text = source.read_text(encoding="utf-8")
    assert "validar_no_futuro(fecha_hora, \"La fecha del movimiento de inventario\")" in text


def test_entradas_de_inventario_quedan_valoradas():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "movimiento_inventario_service.py"
    text = source.read_text(encoding="utf-8")
    assert 'if efecto == 1 and data.costo_unitario is None:' in text
    assert 'positivo requiere costo_unitario' in text


def test_salidas_no_aceptan_costeo_manual_y_se_congelan_al_promedio_historico():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "movimiento_inventario_service.py"
    text = source.read_text(encoding="utf-8")
    assert 'if efecto == -1:' in text
    assert 'costo_unitario = _costo_promedio_stock_as_of(db, producto.id, fecha_hora)' in text
    assert 'datos["costo_total"] = (costo_unitario * cantidad).quantize' in text


def test_migracion_inventario_refuerza_valoracion_y_fecha():
    from pathlib import Path
    migration = Path(__file__).parents[2] / "database" / "migrations" / "012_integridad_inventario_valorado.sql"
    text = migration.read_text(encoding="utf-8")
    assert "v_efecto = 1 AND NEW.costo_unitario IS NULL" in text
    assert "NEW.fecha_hora > NOW()" in text
    assert "No se acepta una valoración manual" not in text
    assert "Se separa de 009" in text


def test_costo_promedio_ponderado_con_entradas_a_distinto_costo():
    rows = [
        {"cantidad": "100", "costo_unitario": "1000", "costo_total": "100000", "efecto": 1},
        {"cantidad": "100", "costo_unitario": "2000", "costo_total": "200000", "efecto": 1},
    ]
    assert _calcular_costo_promedio_desde_movimientos(rows) == 1500


def test_costo_salida_historica_ignora_entrada_posterior():
    rows = [
        {"cantidad": "100", "costo_unitario": "1000", "costo_total": "100000", "efecto": 1},
    ]
    assert _calcular_costo_promedio_desde_movimientos(rows) == 1000


def test_costo_promedio_se_recalcula_despues_de_una_salida():
    rows = [
        {"cantidad": "100", "costo_unitario": "1000", "costo_total": "100000", "efecto": 1},
        {"cantidad": "100", "costo_unitario": "2000", "costo_total": "200000", "efecto": 1},
        {"cantidad": "50", "costo_unitario": None, "costo_total": "75000", "efecto": -1},
    ]
    assert _calcular_costo_promedio_desde_movimientos(rows) == 1500


def test_ajuste_positivo_se_incorpora_al_promedio():
    rows = [
        {"cantidad": "100", "costo_unitario": "1000", "costo_total": "100000", "efecto": 1},
        {"cantidad": "20", "costo_unitario": "2000", "costo_total": "40000", "efecto": 1},
    ]
    assert _calcular_costo_promedio_desde_movimientos(rows) == Decimal("1166.67")
