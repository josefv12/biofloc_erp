"""Etapa 4 — cosecha parcial/total, cierre FINALIZADO e aislamiento entre ciclos.

Ejecutar:
  pytest tests/test_poblacion_lote.py tests/test_indicadores_productivos_etapa3.py tests/test_cosecha_cierre_etapa4.py

HTTP se omite si la API no está en http://127.0.0.1:8000.
No modifica el esquema PostgreSQL. Limpia fixtures [TEST_FIXTURE] al terminar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
import requests

from env_tests import ADMIN_PASS, ADMIN_USER
from lote_operativo import crear_lote_temporal, limpiar_fixtures

BASE = "http://127.0.0.1:8000"


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


def _detail(resp: requests.Response) -> str:
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    return str(body.get("detail", resp.text))


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


def _mortalidad(token: str, lote_id: int, cantidad: int) -> requests.Response:
    return requests.post(
        f"{BASE}/api/v1/mortalidades/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad": cantidad,
            "causa": "[TEST_FIXTURE] etapa 4",
        },
        timeout=20,
    )


def _cosecha(token: str, lote_id: int, cantidad: int, peso_kg: str) -> requests.Response:
    return requests.post(
        f"{BASE}/api/v1/cosechas/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad_peces": cantidad,
            "peso_total_kg": peso_kg,
            "observaciones": "[TEST_FIXTURE] etapa 4",
        },
        timeout=20,
    )


def _lote(token: str, lote_id: int) -> dict:
    r = requests.get(f"{BASE}/api/v1/lotes/{lote_id}", headers=_h(token), timeout=20)
    r.raise_for_status()
    return r.json()


def _analisis(token: str, lote_id: int) -> dict:
    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=_h(token), timeout=20)
    r.raise_for_status()
    return r.json()


def test_caso_a_cosecha_parcial_sigue_activo(api_token):
    token = api_token
    lote = crear_lote_temporal(token, cantidad_sembrada=3500)
    lote_id = lote["id"]
    assert _mortalidad(token, lote_id, 100).status_code == 201
    r_c = _cosecha(token, lote_id, 3000, "150.000")
    assert r_c.status_code == 201, r_c.text
    promedio = Decimal(str(r_c.json().get("peso_promedio_g")))
    assert promedio == Decimal("50.000")

    data = _lote(token, lote_id)
    assert data["estado"]["nombre"] == "ACTIVO"
    assert data.get("fecha_cierre") in (None, "")

    ind = _analisis(token, lote_id)["indicadores"]
    assert ind["poblacion_estimada"] == 400
    assert Decimal(str(ind["supervivencia_porcentaje"])) == Decimal("97.14")
    assert Decimal(str(ind["mortalidad_porcentaje"])) == Decimal("2.86")


def test_caso_b_cosecha_total_pasa_a_finalizado(api_token):
    token = api_token
    lote = crear_lote_temporal(token, cantidad_sembrada=3500)
    lote_id = lote["id"]
    assert _mortalidad(token, lote_id, 100).status_code == 201
    r_c = _cosecha(token, lote_id, 3400, "170.000")
    assert r_c.status_code == 201, r_c.text

    data = _lote(token, lote_id)
    assert data["estado"]["nombre"] == "FINALIZADO"
    assert data.get("fecha_cierre") not in (None, "")

    ind = _analisis(token, lote_id)["indicadores"]
    assert ind["poblacion_estimada"] == 0
    assert Decimal(str(ind["supervivencia_porcentaje"])) == Decimal("97.14")
    assert Decimal(str(ind["mortalidad_porcentaje"])) == Decimal("2.86")


def test_caso_c_exceso_422_mensaje_exacto(api_token):
    token = api_token
    lote = crear_lote_temporal(token, cantidad_sembrada=3500)
    lote_id = lote["id"]
    assert _mortalidad(token, lote_id, 100).status_code == 201
    fail = _cosecha(token, lote_id, 3401, "170.000")
    assert fail.status_code == 422, fail.text
    assert _detail(fail) == "No se pueden cosechar 3401 peces. La población disponible es 3400."
    assert _lote(token, lote_id)["estado"]["nombre"] == "ACTIVO"


def test_caso_d_lote_b_no_hereda_ciclo_a(api_token):
    token = api_token
    lote_a = crear_lote_temporal(token, cantidad_sembrada=3500)
    assert _mortalidad(token, lote_a["id"], 100).status_code == 201
    r_c = _cosecha(token, lote_a["id"], 3400, "170.000")
    assert r_c.status_code == 201, r_c.text
    assert _lote(token, lote_a["id"])["estado"]["nombre"] == "FINALIZADO"

    lote_b = crear_lote_temporal(
        token,
        cantidad_sembrada=5000,
        estanque_id=lote_a["estanque_id"],
        fecha_siembra="2026-08-19",
    )
    assert _lote(token, lote_b["id"])["estado"]["nombre"] == "ACTIVO"
    assert _lote(token, lote_a["id"])["estado"]["nombre"] == "FINALIZADO"

    ind_b = _analisis(token, lote_b["id"])["indicadores"]
    assert ind_b["peces_sembrados"] == 5000
    assert ind_b["mortalidad_acumulada"] == 0
    assert ind_b["peces_cosechados"] == 0
    assert ind_b["poblacion_estimada"] == 5000

    ind_a = _analisis(token, lote_a["id"])["indicadores"]
    assert ind_a["peces_cosechados"] == 3400
    assert ind_a["mortalidad_acumulada"] == 100


def test_caso_e_lote_cerrado_rechaza_operaciones(api_token):
    token = api_token
    lote = crear_lote_temporal(token, cantidad_sembrada=3500)
    lote_id = lote["id"]
    assert _mortalidad(token, lote_id, 100).status_code == 201
    assert _cosecha(token, lote_id, 3400, "170.000").status_code == 201
    assert _lote(token, lote_id)["estado"]["nombre"] == "FINALIZADO"

    alim = requests.post(
        f"{BASE}/api/v1/alimentaciones/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "producto_id": 1,
            "fecha_hora": _ahora(),
            "cantidad": "0.5",
        },
        timeout=20,
    )
    assert alim.status_code == 422, alim.text
    assert "ACTIVO" in _detail(alim)
    if "stock" in _detail(alim).lower():
        pytest.fail("La alimentación en lote cerrado no debe llegar a validar inventario")

    bio = requests.post(
        f"{BASE}/api/v1/biometrias/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad_muestra": 10,
            "peso_total_muestra_g": 280,
        },
        timeout=20,
    )
    assert bio.status_code == 422, bio.text
    assert "ACTIVO" in _detail(bio)

    mort = _mortalidad(token, lote_id, 1)
    assert mort.status_code == 422, mort.text
    assert "ACTIVO" in _detail(mort)

    params = requests.get(
        f"{BASE}/api/v1/parametros-agua/?solo_activos=true", headers=_h(token), timeout=20
    )
    params.raise_for_status()
    parametros = params.json() or []
    if parametros:
        agua = requests.post(
            f"{BASE}/api/v1/mediciones-agua/",
            headers=_h(token),
            json={
                "lote_id": lote_id,
                "parametro_id": parametros[0]["id"],
                "fecha_hora": _ahora(),
                "valor": "7.0",
            },
            timeout=20,
        )
        assert agua.status_code == 422, agua.text
        assert "ACTIVO" in _detail(agua)

    floc = requests.post(
        f"{BASE}/api/v1/mediciones-biofloc/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "volumen_sedimentable": "10",
            "unidad": "mL/L",
        },
        timeout=20,
    )
    assert floc.status_code == 422, floc.text
    assert "ACTIVO" in _detail(floc)

    tipos = requests.get(
        f"{BASE}/api/v1/tipos-aplicacion-biofloc/?solo_activos=true",
        headers=_h(token),
        timeout=20,
    )
    tipos.raise_for_status()
    catalogo_tipos = tipos.json() or []
    if catalogo_tipos:
        apl = requests.post(
            f"{BASE}/api/v1/aplicaciones-biofloc/",
            headers=_h(token),
            json={
                "lote_id": lote_id,
                "tipo_aplicacion_id": catalogo_tipos[0]["id"],
                "fecha_hora": _ahora(),
            },
            timeout=20,
        )
        assert apl.status_code == 422, apl.text
        assert "ACTIVO" in _detail(apl)
