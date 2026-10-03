"""Integridad del estado activo del catálogo de parámetros de agua."""
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_servicio_rechaza_parametro_agua_inactivo():
    source = (
        ROOT / "backend/app/services/medicion_agua_service.py"
    ).read_text(encoding="utf-8")
    assert "if not parametro.activo:" in source
    assert "no admite nuevas mediciones" in source


def test_migracion_bloquea_parametro_agua_inactivo():
    source = (
        ROOT / "database/migrations/031_mediciones_parametro_agua_activo.sql"
    ).read_text(encoding="utf-8")
    assert "trg_validar_parametro_agua_activo" in source
    assert "AND activo = TRUE" in source


def test_schema_final_bloquea_parametro_agua_inactivo():
    source = (
        ROOT / "database/biofloc_erp_v1_1_schema_final.sql"
    ).read_text(encoding="utf-8")
    assert "trg_validar_parametro_agua_activo" in source
    assert "biofloc.validar_parametro_agua_activo()" in source
