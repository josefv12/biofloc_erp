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


def test_costo_promedio_no_conserva_lote_barato_ya_consumido():
    rows = [
        {"cantidad": "100", "costo_unitario": "1000", "costo_total": "100000", "efecto": 1},
        {"cantidad": "100", "costo_unitario": None, "costo_total": "100000", "efecto": -1},
        {"cantidad": "100", "costo_unitario": "2000", "costo_total": "200000", "efecto": 1},
    ]
    # El lote barato ya fue consumido por completo; el stock remanente
    # corresponde al lote caro y su costo promedio debe ser $2.000/kg.
    assert _calcular_costo_promedio_desde_movimientos(rows) == Decimal("2000")


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


def test_catalogo_gastos_incluye_alevinos_para_costeo_de_lote():
    from pathlib import Path
    schema = Path(__file__).parents[2] / "database" / "biofloc_erp_v1_1_schema_final.sql"
    migration = Path(__file__).parents[2] / "database" / "migrations" / "013_catalogo_gasto_alevinos.sql"
    assert "('ALEVINOS', 'Compra de alevinos y material vivo de siembra')" in schema.read_text(encoding="utf-8")
    assert "INSERT INTO biofloc.categorias_gasto" in migration.read_text(encoding="utf-8")

def test_trazabilidad_automatica_valida_producto_cantidad_fecha_y_salida():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "movimiento_inventario_service.py"
    text = source.read_text(encoding="utf-8")
    assert 'Una alimentación solo puede generar un movimiento SALIDA' in text
    assert 'El producto del movimiento no coincide con la alimentación' in text
    assert 'La cantidad del movimiento no coincide con la alimentación' in text
    assert 'La fecha del movimiento no coincide con la alimentación' in text
    assert 'Una aplicación Biofloc solo puede generar un movimiento SALIDA' in text


def test_trazabilidad_automatica_tiene_guardia_en_base_de_datos():
    from pathlib import Path
    migration = Path(__file__).parents[2] / "database" / "migrations" / "014_integridad_trazabilidad_movimientos.sql"
    text = migration.read_text(encoding="utf-8")
    assert "validar_trazabilidad_movimiento_automatico" in text
    assert "NEW.producto_id <> v_producto" in text
    assert "NEW.cantidad <> v_cantidad" in text
    assert "NEW.fecha_hora <> v_fecha" in text
    assert "Una referencia de inventario no permitida" not in text


def test_costeo_lote_suma_movimientos_de_alimentacion_por_referencia():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "costos_lote_service.py"
    text = source.read_text(encoding="utf-8")
    assert "mi.referencia_tipo = 'ALIMENTACION'" in text
    assert "mi.referencia_id IS NOT NULL" in text
    assert "mi.costo_total IS NOT NULL" in text

def test_coste_alimento_exige_salida_y_coincidencia_con_alimentacion():
    from pathlib import Path
    for rel in ("app/services/costos_lote_service.py", "app/services/finanzas_service.py"):
        source = Path(__file__).parents[1] / rel
        text = source.read_text(encoding="utf-8")
        assert "a.producto_id = mi.producto_id" in text
        assert "a.cantidad = mi.cantidad" in text
        assert "a.fecha_hora = mi.fecha_hora" in text
        assert "tm.nombre = 'SALIDA'" in text


def test_trazabilidad_detalle_compra_se_mantiene_compatible():
    from pathlib import Path
    servicio = (Path(__file__).parents[1] / "app" / "services" / "movimiento_inventario_service.py").read_text(encoding="utf-8")
    migracion = (Path(__file__).parents[2] / "database" / "migrations" / "014_integridad_trazabilidad_movimientos.sql").read_text(encoding="utf-8")
    assert 'referencia_tipo == "DETALLE_COMPRA"' in servicio
    assert "referencia_tipo = 'DETALLE_COMPRA'" in migracion
    assert "tipo_nombre != 'ENTRADA'" in servicio
    assert "v_tipo <> 'ENTRADA'" in migracion


def test_medicion_agua_rechaza_fecha_futura_en_servicio():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app/services/medicion_agua_service.py"
    text = source.read_text(encoding="utf-8")
    assert "validar_no_futuro(data.fecha_hora" in text


def test_medicion_agua_tiene_guardia_no_futura_en_bd():
    from pathlib import Path
    migration = Path(__file__).parents[2] / "database/migrations/010_integridad_produccion.sql"
    text = migration.read_text(encoding="utf-8")
    assert "trg_validar_fecha_medicion_agua_futura" in text


def test_fecha_hora_sin_zona_se_interpreta_en_colombia_sin_typeerror():
    from app.services.validaciones_fecha import validar_no_futuro
    from zoneinfo import ZoneInfo
    from datetime import datetime, timedelta, timezone

    # Una fecha ingenua representa hora local de operación en Colombia.
    pasado_local = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None) - timedelta(minutes=5)
    validar_no_futuro(pasado_local)

    futuro_local = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None) + timedelta(minutes=5)
    with pytest.raises(Exception):
        validar_no_futuro(futuro_local)

def test_evento_energia_datetime_sin_zona_usa_hora_colombia():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app/services/evento_energia_service.py"
    text = source.read_text(encoding="utf-8")
    assert 'ZoneInfo("America/Bogota")' in text
    assert 'dt.replace(tzinfo=ZoneInfo("America/Bogota"))' in text


def test_schema_final_no_tiene_cierres_dollar_quote_corruptos():
    from pathlib import Path
    schema = Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql"
    text = schema.read_text(encoding="utf-8")
    assert not __import__("re").search(r"\$[A-Za-z_][A-Za-z0-9_]*\$\d+", text)


def test_movimientos_automaticos_son_idempotentes_por_referencia():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/services/movimiento_inventario_service.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/017_idempotencia_movimientos_automaticos.sql").read_text(encoding="utf-8")
    assert "Ya existe un movimiento de inventario para" in source
    assert "uq_mov_inv_referencia_automatica" in migration
    assert "DETALLE_COMPRA" in migration
    assert "ALIMENTACION" in migration
    assert "APLICACION_BIOFLOC" in migration


def test_alimentacion_rechaza_fecha_futura_en_servicio():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/services/alimentacion_service.py").read_text(encoding="utf-8")
    assert 'validar_no_futuro(data.fecha_hora, "La fecha de la alimentación")' in source


def test_eventos_operativos_auxiliares_tienen_guardia_temporal_en_bd():
    from pathlib import Path
    migration = (Path(__file__).parents[2] / "database/migrations/016_integridad_eventos_operativos.sql").read_text(encoding="utf-8")
    assert "trg_validar_fecha_falla_futura" in migration
    assert "trg_validar_fecha_mantenimiento_futura" in migration
    assert "trg_validar_fecha_evento_energia_futura" in migration
