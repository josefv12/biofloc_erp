"""Pruebas unitarias de población disponible y reglas de ciclo del lote."""
from decimal import Decimal
from types import SimpleNamespace
from datetime import date

from fastapi import HTTPException

from app.services.analisis_service import FACTOR_A_KG, _alimento_kg
from app.schemas.analisis import AlimentoUnidadOut
from app.schemas.lote import sumar_meses, LoteOut
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


def test_fca_alimento_solo_kg():
    assert FACTOR_A_KG == {"kg": Decimal("1")}


def test_alimento_kg_rechaza_gramos():
    total, razon = _alimento_kg(
        [AlimentoUnidadOut(unidad="g", cantidad=Decimal("3.500"))]
    )
    assert total is None
    assert razon == "UNIDAD_ALIMENTO_INCOMPATIBLE"


def test_alimento_kg_suma_solo_kg():
    total, razon = _alimento_kg(
        [AlimentoUnidadOut(unidad="kg", cantidad=Decimal("0.5"))]
    )
    assert total == Decimal("0.500")
    assert razon is None


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


def test_ciclo_estimado_es_seis_meses_calendario():
    assert sumar_meses(date(2026, 9, 11), 6) == date(2027, 3, 11)
    assert sumar_meses(date(2026, 8, 31), 6) == date(2027, 2, 28)


def test_peso_promedio_cosecha_decimal_y_redondeo():
    assert _peso_promedio_g(Decimal("1.001"), 3) == Decimal("333.667")


def test_peso_promedio_no_depende_de_unidades_comerciales():
    assert _peso_promedio_g(Decimal("2.500"), 5) == Decimal("500.000")


def test_cosecha_cierre_usa_poblacion_historica():
    from pathlib import Path
    source = Path(__file__).parents[1] / "app" / "services" / "cosecha_service.py"
    text = source.read_text(encoding="utf-8")
    assert "obtener_poblacion_disponible(db, data.lote_id, lote.cantidad_sembrada, data.fecha_hora)" in text

def test_poblacion_historica_revalida_eventos_posteriores():
    from pathlib import Path
    migration = Path(__file__).parents[2] / "database" / "migrations" / "015_integridad_secuencia_poblacion.sql"
    text = migration.read_text(encoding="utf-8")
    assert "validar_secuencia_poblacion_historica" in text
    assert "MAX(salidas_acumuladas)" in text
    assert "UNION ALL" in text
    assert "mortalidades" in text and "cosechas" in text
    assert "DEFERRABLE INITIALLY IMMEDIATE" in text


def test_poblacion_historica_secuencia_usa_bloqueo_del_lote():
    from pathlib import Path
    migration = Path(__file__).parents[2] / "database" / "migrations" / "015_integridad_secuencia_poblacion.sql"
    text = migration.read_text(encoding="utf-8")
    assert "FROM biofloc.lotes" in text
    assert "FOR UPDATE" in text


def test_lote_rechaza_fecha_siembra_futura():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/services/lote_service.py").read_text(encoding="utf-8")
    assert 'validar_fecha_no_futura(data.fecha_siembra, "La fecha de siembra")' in source


def test_schema_final_tiene_guardia_de_siembra_no_futura():
    from pathlib import Path
    source = (Path(__file__).parents[2] / "database/biofloc_erp_v1_1_schema_final.sql").read_text(encoding="utf-8")
    assert "trg_validar_fecha_siembra_no_futura" in source
    assert "NOW() AT TIME ZONE 'America/Bogota'" in source


def test_listar_lotes_honra_filtro_activos():
    from pathlib import Path
    source = (Path(__file__).parents[1] / "app/services/lote_service.py").read_text(encoding="utf-8")
    assert 'if activos:' in source
    assert 'EstadoLote.nombre == "ACTIVO"' in source
