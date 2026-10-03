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
    assert 'tipo_nombre != "ENTRADA"' in servicio
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


def test_evento_no_puede_superar_cierre_del_lote():
    from datetime import date, datetime
    from fastapi import HTTPException
    from app.services.validaciones_fecha import validar_no_despues_cierre
    try:
        validar_no_despues_cierre(datetime(2026, 10, 2, 0, 1), date(2026, 10, 1), "Evento")
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "cierre" in str(exc.detail).lower()
        return
    raise AssertionError("Un evento posterior al cierre debe ser rechazado")


def test_final_schema_cierra_correctamente_los_dollar_quotes_de_funciones():
    from pathlib import Path
    import re
    source = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert not re.search(r"END;\n(\$[A-Za-z_][A-Za-z0-9_]*\$)\n", source)
    assert "validar_evento_no_despues_cierre" in source
    assert "trg_validar_cierre_no_anterior_eventos" in source


def test_schema_final_tiene_guardias_temporales_financieras_e_inventario():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "trg_validar_fecha_compra_no_futura" in source
    assert "trg_validar_fecha_venta_no_futura" in source
    assert "trg_validar_fecha_movimiento_no_futura" in source


def test_schema_final_protege_unidades_de_producto_con_historico():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "trg_validar_unidad_producto_historica" in source
    assert "movimientos_inventario WHERE producto_id = OLD.id" in source


def test_schema_final_refuerza_inmutabilidad_de_historicos_inventario():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "trg_inmutabilidad_movimientos_inventario" in source
    assert "trg_inmutabilidad_alimentaciones" in source
    assert "trg_inmutabilidad_aplicaciones_biofloc" in source


def test_equipos_exigen_catalogos_activos_y_respaldo_operativo():
    from pathlib import Path
    equipo = (Path(__file__).parents[1] / "app/services/equipo_service.py").read_text(encoding="utf-8")
    energia = (Path(__file__).parents[1] / "app/services/evento_energia_service.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/033_integridad_equipos_respaldo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "Tipo de equipo {tipo_equipo_id} está inactivo" in equipo
    assert "Estado de equipo {estado_id} está inactivo" in equipo
    assert "El equipo de respaldo está inactivo" in energia
    assert 'equipo.estado.nombre != "OPERATIVO"' in energia
    assert "trg_validar_catalogos_equipo_activos" in migration
    assert "trg_validar_equipo_respaldo_operativo" in migration
    assert "trg_validar_catalogos_equipo_activos" in schema
    assert "trg_validar_equipo_respaldo_operativo" in schema


def test_equipos_respetan_fecha_de_adquisicion_en_historicos():
    from pathlib import Path
    for rel in ("app/services/falla_service.py", "app/services/mantenimiento_service.py", "app/services/evento_energia_service.py"):
        source = (Path(__file__).parents[1] / rel).read_text(encoding="utf-8")
        assert "fecha_adquisicion" in source
    migration = (Path(__file__).parents[2] / "database/migrations/034_integridad_fecha_adquisicion_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "trg_validar_fecha_adquisicion_equipo" in migration
    assert "trg_validar_falla_no_antes_adquisicion" in migration
    assert "trg_validar_mantenimiento_no_antes_adquisicion" in migration
    assert "trg_validar_respaldo_no_antes_adquisicion" in migration
    assert "trg_validar_fecha_adquisicion_equipo" in schema
    assert "trg_validar_respaldo_no_antes_adquisicion" in schema


def test_estado_baja_es_terminal_y_desactiva_equipo():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/services/equipo_service.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/035_transicion_estado_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert 'estado_actual == "BAJA"' in source
    assert 'estado_nuevo.nombre == "BAJA"' in source
    assert "trg_validar_transicion_estado_equipo" in migration
    assert "NEW.activo := FALSE" in migration
    assert "trg_validar_transicion_estado_equipo" in schema


def test_duracion_evento_energia_es_derivada_y_protegida():
    from pathlib import Path
    service = (Path(__file__).parents[1] / "app/services/evento_energia_service.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/035_transicion_estado_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "duracion_minutos es un campo calculado" in service
    assert "trg_validar_duracion_evento_energia" in migration
    assert "trg_validar_duracion_evento_energia" in schema


def test_fallas_historicas_son_inmutables():
    from pathlib import Path
    router = (Path(__file__).parents[1] / "app/routers/fallas.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/035_transicion_estado_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert 'status_code=405' in router
    assert "trg_inmutabilidad_fallas" in migration
    assert "trg_inmutabilidad_fallas" in schema

    
def test_tipos_mantenimiento_protegen_historico_y_exigen_catalogo_activo():
    from pathlib import Path
    service = (Path(__file__).parents[1] / "app/services/mantenimiento_service.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/035_transicion_estado_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "está inactivo" in service
    assert "trg_validar_tipo_mantenimiento_historico" in migration
    assert "trg_validar_tipo_mantenimiento_activo" in migration
    assert "trg_validar_tipo_mantenimiento_historico" in schema
    assert "trg_validar_tipo_mantenimiento_activo" in schema

    
def test_nombres_catalogos_equipo_no_reinterpretan_historicos():
    from pathlib import Path
    migration = (Path(__file__).parents[2] / "database/migrations/035_transicion_estado_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "trg_validar_tipo_equipo_historico" in migration
    assert "trg_validar_estado_equipo_historico" in migration
    assert "trg_validar_tipo_equipo_historico" in schema
    assert "trg_validar_estado_equipo_historico" in schema
    assert "'OPERATIVO', 'BAJA', 'FUERA_DE_SERVICIO'" in migration

    
def test_catalogos_agua_biofloc_exigen_activos_y_protegen_historicos():
    from pathlib import Path
    aplicacion = (Path(__file__).parents[1] / "app/services/aplicacion_biofloc_service.py").read_text(encoding="utf-8")
    referencia = (Path(__file__).parents[1] / "app/services/referencia_agua_service.py").read_text(encoding="utf-8")
    migration = (Path(__file__).parents[2] / "database/migrations/035_transicion_estado_equipo.sql").read_text(encoding="utf-8")
    schema = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "tipo de aplicación Biofloc está inactivo" in aplicacion
    assert "parámetro de agua está inactivo" in referencia
    assert "trg_validar_nombre_parametro_agua_historico" in migration
    assert "trg_validar_parametro_agua_referencia_activo" in migration
    assert "trg_validar_tipo_aplicacion_biofloc_activo" in migration
    assert "trg_validar_nombre_parametro_agua_historico" in schema
    assert "trg_validar_parametro_agua_referencia_activo" in schema
    assert "trg_validar_tipo_aplicacion_biofloc_activo" in schema
