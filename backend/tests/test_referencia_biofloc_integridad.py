"""Integridad de unidades canónicas de referencias Biofloc."""
from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_schema_create_rechaza_unidad_biofloc_incompatible():
    from app.schemas.referencia_biofloc import ReferenciaBioflocCreate
    import pytest

    with pytest.raises(Exception):
        ReferenciaBioflocCreate(
            especie_id=1,
            etapa_productiva_id=1,
            indicador="VOLUMEN_SEDIMENTABLE",
            unidad="mg/L",
        )
    with pytest.raises(Exception):
        ReferenciaBioflocCreate(
            especie_id=1,
            etapa_productiva_id=1,
            indicador="RELACION_CN",
            unidad="mL/L",
        )


def test_servicio_update_valida_unidad_segun_indicador():
    source = (
        ROOT / "backend/app/services/referencia_biofloc_service.py"
    ).read_text(encoding="utf-8")
    assert 'unidad_esperada = "mL/L" if row.indicador == "VOLUMEN_SEDIMENTABLE" else "C:N"' in source


def test_migracion_unidades_canonicas_biofloc():
    source = (
        ROOT / "database/migrations/030_unidades_canonicas_referencias_biofloc.sql"
    ).read_text(encoding="utf-8")
    assert "trg_validar_unidad_referencia_biofloc" in source
    assert "VOLUMEN_SEDIMENTABLE" in source
    assert "RELACION_CN" in source
    assert "'mL/L'" in source
    assert "'C:N'" in source


def test_schema_final_unidades_canonicas_biofloc():
    source = (
        ROOT / "database/biofloc_erp_v1_1_schema_final.sql"
    ).read_text(encoding="utf-8")
    assert "trg_validar_unidad_referencia_biofloc" in source
    assert "(indicador = 'VOLUMEN_SEDIMENTABLE' AND unidad = 'mL/L')" in source
    assert "(indicador = 'RELACION_CN' AND unidad = 'C:N')" in source
