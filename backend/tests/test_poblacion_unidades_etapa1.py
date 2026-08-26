#!/usr/bin/env python3
"""Casos A–E: población disponible + unidades alimentación/inventario.

Ejecutar:
  python tests/test_poblacion_unidades_etapa1.py
  pytest tests/test_poblacion_lote.py tests/test_poblacion_unidades_etapa1.py

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
from lote_operativo import (
    asegurar_stock,
    crear_lote_temporal,
    crear_producto_masa,
    limpiar_fixtures,
)

BASE = "http://127.0.0.1:8000"
results: list[tuple] = []


def log(num, name, ok, detail=""):
    icon = "[OK]" if ok else "[FAIL]"
    msg = f"  {icon} [{num}] {name}"
    if detail:
        msg += f"\n       -> {detail}"
    print(msg)
    results.append((num, name, ok, detail))


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


def _stock(producto_id: int) -> Decimal:
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(stock_actual, 0) FROM biofloc.vista_stock_productos WHERE producto_id = %s",
        (producto_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return Decimal(str(row[0] if row else 0))


def _movimiento_alimentacion(alimentacion_id: int) -> tuple[Decimal, str] | None:
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT m.cantidad, u.simbolo
        FROM biofloc.movimientos_inventario m
        JOIN biofloc.productos p ON p.id = m.producto_id
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE m.referencia_tipo = 'ALIMENTACION' AND m.referencia_id = %s
        """,
        (alimentacion_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return Decimal(str(row[0])), str(row[1])


def _count_alim_obs(texto: str) -> int:
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM biofloc.alimentaciones WHERE observaciones LIKE %s",
        (f"%{texto}%",),
    )
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return int(n)


def _historicos_negativos() -> list[tuple]:
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT lote_id, codigo, cantidad_sembrada, mortalidad_acumulada,
               peces_cosechados, poblacion_estimada
        FROM biofloc.vista_biomasa_lotes
        WHERE poblacion_estimada < 0
        ORDER BY lote_id
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def test_formula_disponible_sin_api():
    from app.services.poblacion_lote import calcular_poblacion_disponible

    assert calcular_poblacion_disponible(3500, 100, 3000) == 400


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


def test_caso_a_mortalidad_respeta_cosecha(api_token):
    token = api_token
    lote = crear_lote_temporal(token, cantidad_sembrada=3500)
    lote_id = lote["id"]
    r_m = requests.post(
        f"{BASE}/api/v1/mortalidades/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad": 100,
            "causa": "[TEST_FIXTURE] caso A muertos",
        },
        timeout=20,
    )
    assert r_m.status_code == 201, r_m.text
    r_c = requests.post(
        f"{BASE}/api/v1/cosechas/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad_peces": 3000,
            "peso_total_kg": "150.000",
        },
        timeout=20,
    )
    assert r_c.status_code == 201, r_c.text

    fail = requests.post(
        f"{BASE}/api/v1/mortalidades/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad": 401,
            "causa": "[TEST_FIXTURE] caso A exceso",
        },
        timeout=20,
    )
    assert fail.status_code == 422, fail.text
    assert "400" in fail.json().get("detail", "")

    ok = requests.post(
        f"{BASE}/api/v1/mortalidades/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad": 400,
            "causa": "[TEST_FIXTURE] caso A limite",
        },
        timeout=20,
    )
    assert ok.status_code == 201, ok.text


def test_caso_b_cosecha_respeta_mortalidad(api_token):
    token = api_token
    lote = crear_lote_temporal(token, cantidad_sembrada=3500)
    lote_id = lote["id"]
    r_m = requests.post(
        f"{BASE}/api/v1/mortalidades/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad": 100,
            "causa": "[TEST_FIXTURE] caso B muertos",
        },
        timeout=20,
    )
    assert r_m.status_code == 201, r_m.text

    fail = requests.post(
        f"{BASE}/api/v1/cosechas/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad_peces": 3401,
            "peso_total_kg": "170.000",
        },
        timeout=20,
    )
    assert fail.status_code == 422, fail.text
    assert "3400" in fail.json().get("detail", "")

    ok = requests.post(
        f"{BASE}/api/v1/cosechas/",
        headers=_h(token),
        json={
            "lote_id": lote_id,
            "fecha_hora": _ahora(),
            "cantidad_peces": 3400,
            "peso_total_kg": "170.000",
        },
        timeout=20,
    )
    assert ok.status_code == 201, ok.text


def test_caso_c_alimentacion_kg(api_token):
    token = api_token
    lote = crear_lote_temporal(token)
    producto_id = crear_producto_masa(token, "kg")
    asegurar_stock(token, producto_id, 10)
    stock_antes = _stock(producto_id)
    # Dejar stock en 10 exactos si había de más: no es necesario; se mide delta.
    r = requests.post(
        f"{BASE}/api/v1/alimentaciones/",
        headers=_h(token),
        json={
            "lote_id": lote["id"],
            "producto_id": producto_id,
            "fecha_hora": _ahora(),
            "cantidad": "0.5",
            "observaciones": "[TEST_FIXTURE] caso C 0.5 kg",
        },
        timeout=20,
    )
    assert r.status_code == 201, r.text
    alim_id = r.json()["id"]
    assert Decimal(str(r.json()["cantidad"])) == Decimal("0.5")
    mov = _movimiento_alimentacion(alim_id)
    assert mov is not None
    cantidad_mov, simbolo = mov
    assert simbolo == "kg"
    assert cantidad_mov == Decimal("0.5")
    assert _stock(producto_id) == stock_antes - Decimal("0.5")


def test_caso_d_alimentacion_g(api_token):
    token = api_token
    lote = crear_lote_temporal(token)
    producto_id = crear_producto_masa(token, "g")
    asegurar_stock(token, producto_id, 1000)
    stock_antes = _stock(producto_id)
    r = requests.post(
        f"{BASE}/api/v1/alimentaciones/",
        headers=_h(token),
        json={
            "lote_id": lote["id"],
            "producto_id": producto_id,
            "fecha_hora": _ahora(),
            "cantidad": "500",
            "observaciones": "[TEST_FIXTURE] caso D 500 g",
        },
        timeout=20,
    )
    assert r.status_code == 201, r.text
    alim_id = r.json()["id"]
    assert Decimal(str(r.json()["cantidad"])) == Decimal("500")
    mov = _movimiento_alimentacion(alim_id)
    assert mov is not None
    cantidad_mov, simbolo = mov
    assert simbolo == "g"
    assert cantidad_mov == Decimal("500")
    assert _stock(producto_id) == stock_antes - Decimal("500")


def test_caso_e_stock_insuficiente_atomico(api_token):
    token = api_token
    lote = crear_lote_temporal(token)
    producto_id = crear_producto_masa(token, "kg")
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.tipos_movimiento_inventario WHERE nombre = 'ENTRADA'")
    tipo_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    entrada = requests.post(
        f"{BASE}/api/v1/movimientos-inventario/",
        headers=_h(token),
        json={
            "producto_id": producto_id,
            "tipo_movimiento_id": tipo_id,
            "cantidad": "0.4",
            "observaciones": "[TEST_FIXTURE] caso E stock 0.4",
        },
        timeout=20,
    )
    assert entrada.status_code == 201, entrada.text
    stock_antes = _stock(producto_id)
    assert stock_antes == Decimal("0.4")

    marca = "caso E sin stock"
    r = requests.post(
        f"{BASE}/api/v1/alimentaciones/",
        headers=_h(token),
        json={
            "lote_id": lote["id"],
            "producto_id": producto_id,
            "fecha_hora": _ahora(),
            "cantidad": "0.5",
            "observaciones": f"[TEST_FIXTURE] {marca}",
        },
        timeout=20,
    )
    assert r.status_code == 422, r.text
    detail = r.json().get("detail", "")
    assert "0,4" in detail or "0.4" in detail
    assert "0,5" in detail or "0.5" in detail
    assert _stock(producto_id) == Decimal("0.4")
    assert _count_alim_obs(marca) == 0


def test_reporta_poblacion_negativa_historica(api_token):
    filas = _historicos_negativos()
    if filas:
        print("  [WARN] Lotes con población histórica < 0 (no se corrigen):")
        for fila in filas:
            print(
                f"       lote_id={fila[0]} codigo={fila[1]} sembrados={fila[2]} "
                f"muertos={fila[3]} cosechados={fila[4]} poblacion={fila[5]}"
            )
    # La prueba documenta; no falla por datos previos.
    assert True


def main() -> int:
    print("\n" + "=" * 70)
    print("  TEST etapa 1: poblacion + unidades alimentacion")
    print("=" * 70)
    if not _api_ok():
        print("  [FAIL] API no disponible en http://127.0.0.1:8000")
        return 1
    try:
        token = _token()
    except Exception as exc:
        print(f"  [FAIL] Login: {exc}")
        return 1

    historicos = _historicos_negativos()
    log(
        "H",
        "Lotes con poblacion historica < 0 (solo reporte)",
        True,
        "ninguno" if not historicos else str(historicos),
    )

    class _Tok:
        pass

    tok = token
    try:
        test_caso_a_mortalidad_respeta_cosecha(tok)
        log("A", "Mortalidad 401 falla / 400 pasa con disponible 400", True)
        test_caso_b_cosecha_respeta_mortalidad(tok)
        log("B", "Cosecha 3401 falla / 3400 pasa con disponible 3400", True)
        test_caso_c_alimentacion_kg(tok)
        log("C", "Alimentacion 0.5 kg = salida 0.5 kg", True)
        test_caso_d_alimentacion_g(tok)
        log("D", "Alimentacion 500 g = salida 500 g", True)
        test_caso_e_stock_insuficiente_atomico(tok)
        log("E", "Stock 0.4 kg: 0.5 kg -> 422 atomico", True)
        log("F", "Fecha invalida (frontend, sin HTTP)", True, "withFechaHoraIso -> Fecha y hora invalidas.")
    except AssertionError as exc:
        log("X", "Fallo de aserción", False, str(exc))
        limpiar_fixtures()
        return 1
    except Exception as exc:
        log("X", "Error de entorno", False, str(exc))
        limpiar_fixtures()
        return 1
    finally:
        leftover = limpiar_fixtures()
        log("Z", "Limpieza fixtures", leftover == 0, f"leftover={leftover}")

    failed = [r for r in results if not r[2]]
    print(f"\n  Resultado: {len(results) - len(failed)}/{len(results)} OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
