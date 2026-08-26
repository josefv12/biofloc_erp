"""Regresión: última biometría determinista y GPD histórico en America/Bogota.

Sin HTTP y sin PostgreSQL.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.services.analisis_service import (
    SQL_ULTIMA_BIOMETRIA_LOTE,
    TZ,
    _dias_semana,
    _fecha_local,
    elegir_ultima_biometria,
)


def test_sql_ultima_biometria_es_determinista():
    sql = " ".join(SQL_ULTIMA_BIOMETRIA_LOTE.split())
    assert "FROM biometrias" in sql
    assert "ORDER BY fecha_hora DESC, id DESC" in sql
    assert "vista_ultima_biometria" not in sql
    assert "LIMIT 1" in sql


def test_empate_fecha_hora_gana_id_mayor():
    mismo = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    ganadora = elegir_ultima_biometria(
        [
            {"id": 10, "fecha_hora": mismo, "peso_promedio_g": "10.000"},
            {"id": 11, "fecha_hora": mismo, "peso_promedio_g": "20.000"},
        ]
    )
    assert ganadora is not None
    assert ganadora["id"] == 11
    assert ganadora["peso_promedio_g"] == "20.000"


def test_fecha_mas_reciente_gana_aunque_id_sea_menor():
    ganadora = elegir_ultima_biometria(
        [
            {"id": 99, "fecha_hora": datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)},
            {"id": 5, "fecha_hora": datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)},
        ]
    )
    assert ganadora is not None
    assert ganadora["id"] == 5


def test_fecha_local_utc_madrugada_cae_en_dia_bogota_anterior():
    utc = datetime(2026, 8, 22, 4, 0, tzinfo=timezone.utc)
    assert utc.date() == date(2026, 8, 22)
    assert utc.astimezone(ZoneInfo("America/Bogota")).date() == date(2026, 8, 21)
    assert _fecha_local(utc) == date(2026, 8, 21)
    assert TZ.key == "America/Bogota"


def test_gpd_historico_usa_fecha_bogota_no_date_naive_del_instante():
    siembra = date(2026, 8, 19)
    utc = datetime(2026, 8, 22, 4, 0, tzinfo=timezone.utc)
    dias_incorrectos, _ = _dias_semana(siembra, utc.date())
    dias_oficiales, _ = _dias_semana(siembra, _fecha_local(utc))
    assert dias_incorrectos == 3
    assert dias_oficiales == 2
