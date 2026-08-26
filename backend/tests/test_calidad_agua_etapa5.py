"""Etapa 5 — calidad de agua y Biofloc: rango inclusivo, etiquetas, aislamiento y alarmas.

Ejecutar:
  pytest tests/test_calidad_agua_etapa5.py

HTTP se omite si la API no está en http://127.0.0.1:8000.
No modifica el esquema PostgreSQL. Limpia fixtures [TEST_FIXTURE] al terminar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import psycopg2
import pytest
import requests

from env_tests import ADMIN_PASS, ADMIN_USER, DB_CONF
from lote_operativo import crear_lote_temporal, limpiar_fixtures

from app.services.evaluacion_analitica_service import (
    CumplimientoRango,
    EstadoAnalitico,
    evaluar_rango,
    recomendacion_agua,
)

BASE = "http://127.0.0.1:8000"


def _rango(**kwargs):
    return evaluar_rango(
        indicador=kwargs.get("indicador", "agua:1"),
        etiqueta=kwargs.get("etiqueta", "Oxígeno disuelto"),
        real=kwargs.get("real"),
        minimo=kwargs.get("minimo", Decimal("5")),
        maximo=kwargs.get("maximo", Decimal("8")),
        unidad=kwargs.get("unidad", "mg/L"),
        objetivo=kwargs.get("objetivo"),
    )


def test_caso_1_real_igual_minimo_dentro():
    ev = _rango(real=Decimal("5"))
    assert ev.cumplimiento_rango == CumplimientoRango.DENTRO_RANGO
    assert ev.estado_analitico is None


def test_caso_2_real_igual_maximo_dentro():
    ev = _rango(real=Decimal("8"))
    assert ev.cumplimiento_rango == CumplimientoRango.DENTRO_RANGO


def test_caso_3_real_bajo_minimo_fuera():
    ev = _rango(real=Decimal("4.99"))
    assert ev.cumplimiento_rango == CumplimientoRango.FUERA_RANGO
    rec = recomendacion_agua(ev)
    assert rec is not None
    assert "Oxígeno disuelto" in rec.recomendacion
    assert "agua:1" not in rec.recomendacion
    assert "Agua:1" not in rec.recomendacion
    for unidad in (" kg", " mg", " ml", " %"):
        assert unidad not in rec.recomendacion.lower()


def test_caso_4_real_sobre_maximo_fuera():
    ev = _rango(real=Decimal("8.01"))
    assert ev.cumplimiento_rango == CumplimientoRango.FUERA_RANGO
    rec = recomendacion_agua(ev)
    assert rec is not None
    assert "Oxígeno disuelto" in rec.recomendacion


def test_caso_5_sin_referencia_nd():
    ev = evaluar_rango(
        indicador="agua:1",
        etiqueta="Oxígeno disuelto",
        real=Decimal("5.8"),
        minimo=None,
        maximo=None,
        unidad="mg/L",
    )
    assert ev.estado_analitico == EstadoAnalitico.SIN_REFERENCIA
    assert ev.cumplimiento_rango == CumplimientoRango.NO_EVALUABLE
    assert "Sin referencia configurada" in ev.explicacion
    assert recomendacion_agua(ev) is None


def test_caso_6_sin_medicion_nd():
    ev = evaluar_rango(
        indicador="agua:1",
        etiqueta="Oxígeno disuelto",
        real=None,
        minimo=Decimal("5"),
        maximo=Decimal("8"),
        unidad="mg/L",
    )
    assert ev.estado_analitico == EstadoAnalitico.SIN_DATOS
    assert ev.real is None
    assert "Sin medición" in ev.explicacion
    assert recomendacion_agua(ev) is None


def test_caso_10_solidos_conserva_objetivo_informativo():
    ev = evaluar_rango(
        indicador="volumen_sedimentable",
        etiqueta="Sólidos sedimentables",
        real=Decimal("12"),
        minimo=Decimal("5"),
        maximo=Decimal("40"),
        objetivo=Decimal("15"),
        unidad="mL/L",
    )
    assert ev.cumplimiento_rango == CumplimientoRango.DENTRO_RANGO
    assert ev.objetivo == Decimal("15")
    assert ev.minimo == Decimal("5")
    assert ev.maximo == Decimal("40")
    assert ev.real == Decimal("12")


def test_objetivo_no_sustituye_rango():
    ev = evaluar_rango(
        indicador="volumen_sedimentable",
        etiqueta="Sólidos sedimentables",
        real=Decimal("15"),
        minimo=Decimal("5"),
        maximo=Decimal("40"),
        objetivo=Decimal("20"),
        unidad="mL/L",
    )
    assert ev.cumplimiento_rango == CumplimientoRango.DENTRO_RANGO
    assert ev.objetivo == Decimal("20")


def _api_ok() -> bool:
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _token() -> str:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": ADMIN_USER, "password": ADMIN_PASS},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_alarmas() -> int:
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.alarmas")
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def _ev(body: dict, indicador: str) -> dict:
    return next(row for row in body["evaluaciones"] if row["indicador"] == indicador)


@pytest.fixture(scope="module")
def api_token():
    if not _api_ok():
        pytest.skip("API no disponible en http://127.0.0.1:8000")
    try:
        token = _token()
    except Exception as exc:
        pytest.skip(f"No se pudo autenticar: {exc}")
    yield token
    limpiar_fixtures()


def test_caso_8_lote_b_no_hereda_mediciones_de_a(api_token):
    token = api_token
    lote_a = crear_lote_temporal(token, cantidad_sembrada=100)
    lote_a_id = lote_a["id"]
    params = requests.get(f"{BASE}/api/v1/parametros-agua/?solo_activos=true", headers=_h(token), timeout=20)
    params.raise_for_status()
    parametros = params.json() or []
    assert parametros, "Se necesita al menos un parámetro de agua en el catálogo"
    parametro_id = int(parametros[0]["id"])

    r_med = requests.post(
        f"{BASE}/api/v1/mediciones-agua/",
        headers=_h(token),
        json={
            "lote_id": lote_a_id,
            "parametro_id": parametro_id,
            "fecha_hora": _ahora(),
            "valor": 5.5,
            "observaciones": "[TEST_FIXTURE] etapa 5 lote A",
        },
        timeout=20,
    )
    assert r_med.status_code == 201, r_med.text
    medicion_id = int(r_med.json()["id"])

    r_cosecha = requests.post(
        f"{BASE}/api/v1/cosechas/",
        headers=_h(token),
        json={
            "lote_id": lote_a_id,
            "fecha_hora": _ahora(),
            "cantidad_peces": 100,
            "peso_total_kg": "5.000",
            "observaciones": "[TEST_FIXTURE] cierre etapa 5",
        },
        timeout=20,
    )
    assert r_cosecha.status_code == 201, r_cosecha.text

    lote_b = crear_lote_temporal(token, estanque_id=lote_a["estanque_id"], cantidad_sembrada=80)
    lote_b_id = lote_b["id"]

    an_a = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_a_id}", headers=_h(token), timeout=30)
    an_b = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_b_id}", headers=_h(token), timeout=30)
    assert an_a.status_code == 200, an_a.text
    assert an_b.status_code == 200, an_b.text
    ids_a = {row["id"] for row in an_a.json().get("agua_serie", [])}
    ids_b = {row["id"] for row in an_b.json().get("agua_serie", [])}
    assert medicion_id in ids_a
    assert medicion_id not in ids_b
    assert ids_b == set()


def test_caso_9_y_alarmas_get_analisis_no_crea_filas(api_token):
    token = api_token
    lote = crear_lote_temporal(token)
    lote_id = lote["id"]
    detalle = requests.get(f"{BASE}/api/v1/lotes/{lote_id}", headers=_h(token), timeout=20)
    detalle.raise_for_status()
    lote_json = detalle.json()
    params = requests.get(f"{BASE}/api/v1/parametros-agua/?solo_activos=true", headers=_h(token), timeout=20)
    params.raise_for_status()
    parametros = params.json() or []
    assert parametros
    oxigeno = next((p for p in parametros if "ox" in str(p.get("nombre", "")).lower()), parametros[0])
    parametro_id = int(oxigeno["id"])
    nombre = str(oxigeno["nombre"])

    refs = requests.get(
        f"{BASE}/api/v1/referencias-agua/",
        headers=_h(token),
        params={
            "especie_id": lote_json["especie_id"],
            "etapa_productiva_id": lote_json["etapa_productiva_id"],
            "parametro_id": parametro_id,
            "solo_activos": True,
        },
        timeout=20,
    )
    refs.raise_for_status()
    existentes = refs.json() or []
    created_ref = None
    if not existentes:
        r_ref = requests.post(
            f"{BASE}/api/v1/referencias-agua/",
            headers=_h(token),
            json={
                "especie_id": lote_json["especie_id"],
                "etapa_productiva_id": lote_json["etapa_productiva_id"],
                "parametro_id": parametro_id,
                "valor_minimo": "5",
                "valor_maximo": "8",
                "observaciones": "[TEST_FIXTURE] etapa 5 agua",
                "activo": True,
            },
            timeout=20,
        )
        if r_ref.status_code == 201:
            created_ref = int(r_ref.json()["id"])

    r_med = requests.post(
        f"{BASE}/api/v1/mediciones-agua/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "parametro_id": parametro_id,
            "fecha_hora": _ahora(),
            "valor": 4.5,
            "observaciones": "[TEST_FIXTURE] etapa 5 fuera",
        },
        timeout=20,
    )
    assert r_med.status_code == 201, r_med.text

    antes = _count_alarmas()
    r_an = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=_h(token), timeout=30)
    assert r_an.status_code == 200, r_an.text
    despues = _count_alarmas()
    assert despues == antes

    body = r_an.json()
    texto = str(body)
    assert "Agua:1" not in texto
    ev = _ev(body, f"agua:{parametro_id}")
    assert ev["etiqueta"] == nombre
    assert "agua:" not in (ev["etiqueta"] or "")
    if ev.get("cumplimiento_rango") == "FUERA_RANGO":
        recs = body.get("recomendaciones") or []
        rec = next((row for row in recs if row["indicador"] == ev["indicador"]), None)
        assert rec is not None
        assert nombre in rec["recomendacion"]
        assert "Agua:1" not in rec["recomendacion"]
        assert "agua:1" not in rec["recomendacion"]

    if created_ref:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.referencias_agua WHERE id = %s", (created_ref,))
        conn.commit()
        cur.close()
        conn.close()


def test_caso_10_http_solidos_real_min_max_objetivo(api_token):
    token = api_token
    lote = crear_lote_temporal(token)
    lote_id = lote["id"]
    detalle = requests.get(f"{BASE}/api/v1/lotes/{lote_id}", headers=_h(token), timeout=20)
    detalle.raise_for_status()
    lote_json = detalle.json()

    refs = requests.get(
        f"{BASE}/api/v1/referencias-biofloc/",
        headers=_h(token),
        params={
            "especie_id": lote_json["especie_id"],
            "etapa_productiva_id": lote_json["etapa_productiva_id"],
            "indicador": "VOLUMEN_SEDIMENTABLE",
            "solo_activos": True,
        },
        timeout=20,
    )
    refs.raise_for_status()
    existentes = refs.json() or []
    created_ref = None
    if existentes:
        ref = existentes[0]
    else:
        r_ref = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/",
            headers=_h(token),
            json={
                "especie_id": lote_json["especie_id"],
                "etapa_productiva_id": lote_json["etapa_productiva_id"],
                "indicador": "VOLUMEN_SEDIMENTABLE",
                "valor_minimo": "5",
                "valor_objetivo": "15",
                "valor_maximo": "40",
                "unidad": "mL/L",
                "observaciones": "[TEST_FIXTURE] etapa 5 biofloc",
                "activo": True,
            },
            timeout=20,
        )
        assert r_ref.status_code == 201, r_ref.text
        ref = r_ref.json()
        created_ref = int(ref["id"])

    r_med = requests.post(
        f"{BASE}/api/v1/mediciones-biofloc/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "volumen_sedimentable": 12,
            "unidad": ref.get("unidad") or "mL/L",
            "observaciones": "[TEST_FIXTURE] etapa 5 solidos",
        },
        timeout=20,
    )
    assert r_med.status_code == 201, r_med.text

    r_an = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=_h(token), timeout=30)
    assert r_an.status_code == 200, r_an.text
    ev = _ev(r_an.json(), "volumen_sedimentable")
    assert ev["etiqueta"] == "Sólidos sedimentables"
    assert ev["real"] is not None
    if ref.get("valor_minimo") is not None:
        assert ev["minimo"] is not None
    if ref.get("valor_maximo") is not None:
        assert ev["maximo"] is not None
    if ref.get("valor_objetivo") is not None:
        assert ev["objetivo"] is not None
    assert "Agua:1" not in str(r_an.json())

    if created_ref:
        conn = psycopg2.connect(**DB_CONF)
        cur = conn.cursor()
        cur.execute("DELETE FROM biofloc.referencias_biofloc WHERE id = %s", (created_ref,))
        conn.commit()
        cur.close()
        conn.close()
