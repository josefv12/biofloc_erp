"""Integridad histórica de unidades del catálogo de calidad de agua."""
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_servicio_bloquea_cambio_de_unidad_con_mediciones():
    source = (
        ROOT / "backend/app/services/parametro_agua_service.py"
    ).read_text(encoding="utf-8")
    assert "No se puede cambiar la unidad de un parámetro de agua que ya tiene mediciones históricas" in source
    assert "MedicionAgua.parametro_id == p.id" in source


def test_migracion_protege_unidad_historica_de_parametro_agua():
    source = (
        ROOT / "database/migrations/029_proteger_unidades_historicas_parametros_agua.sql"
    ).read_text(encoding="utf-8")
    assert "trg_validar_unidad_parametro_agua_historica" in source
    assert "NEW.unidad IS DISTINCT FROM OLD.unidad" in source
    assert "FROM biofloc.mediciones_agua" in source


def test_schema_final_protege_unidad_historica_de_parametro_agua():
    source = (
        ROOT / "database/biofloc_erp_v1_1_schema_final.sql"
    ).read_text(encoding="utf-8")
    assert "trg_validar_unidad_parametro_agua_historica" in source
    assert "biofloc.validar_unidad_parametro_agua_historica()" in source
