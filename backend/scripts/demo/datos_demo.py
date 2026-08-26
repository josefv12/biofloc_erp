#!/usr/bin/env python3
"""Helper de laboratorio para suites automatizadas (cierre / ficha).

NO forma parte del arranque de la API ni del flujo normal del ERP.
Tras cada suite debe invocarse limpiar() y leftover debe ser 0.
No usar para poblar producción.

Uso (solo pruebas):

  python backend/scripts/demo/datos_demo.py cargar
  python backend/scripts/demo/datos_demo.py limpiar
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR / "tests"))
load_dotenv(BACKEND_DIR / ".env")

from env_tests import ADMIN_PASS, ADMIN_USER, DB_CONF  # noqa: E402

BASE = "http://127.0.0.1:8000"
PREF = "[DEMO]"
ESPECIE_DEMO = f"{PREF} especie visual"


def login() -> str:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": ADMIN_USER, "password": ADMIN_PASS},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def db():
    return psycopg2.connect(**DB_CONF)


def post(token: str, ruta: str, payload: dict) -> dict:
    r = requests.post(f"{BASE}{ruta}", headers=H(token), json=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{ruta}: {r.status_code} {r.text[:400]}")
    return r.json()


def put(token: str, ruta: str, payload: dict) -> dict:
    r = requests.put(f"{BASE}{ruta}", headers=H(token), json=payload, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"PUT {ruta}: {r.status_code} {r.text[:400]}")
    return r.json()


def get_json(token: str, ruta: str):
    r = requests.get(f"{BASE}{ruta}", headers=H(token), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"GET {ruta}: {r.status_code} {r.text[:400]}")
    return r.json()


def iso(dias_atras: int, horas: int = 10) -> str:
    momento = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return momento.replace(hour=horas, minute=0, second=0, microsecond=0).isoformat()


def fecha(dias_atras: int) -> str:
    return (date.today() - timedelta(days=dias_atras)).isoformat()


def _ya_existe() -> bool:
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.lotes WHERE codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.especies WHERE nombre_comun LIKE %s)
        """,
        (f"{PREF}%", f"{PREF}%", f"{PREF}%", f"{PREF}%"),
    )
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n > 0


def leftover() -> int:
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.lotes WHERE codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.estanques WHERE codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.especies WHERE nombre_comun LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.ventas WHERE cliente LIKE %s OR COALESCE(observaciones,'') LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.gastos WHERE descripcion LIKE %s OR COALESCE(observaciones,'') LIKE %s)
        """,
        (f"{PREF}%", f"{PREF}%", f"{PREF}%", f"{PREF}%", f"{PREF}%", f"{PREF}%", f"{PREF}%"),
    )
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def _biometrias(token: str, lote_id: int, puntos: list[tuple[int, float, float]]) -> None:
    for dias, peso_promedio_g, talla in puntos:
        post(
            token,
            "/api/v1/biometrias/",
            {
                "lote_id": lote_id,
                "fecha_hora": iso(dias),
                "cantidad_muestra": 10,
                "peso_total_muestra_g": round(peso_promedio_g * 10, 3),
                "talla_promedio": talla,
                "unidad_talla": "cm",
                "observaciones": PREF,
            },
        )


def _mortalidades(token: str, lote_id: int, puntos: list[tuple[int, int]]) -> None:
    for dias, cantidad in puntos:
        post(
            token,
            "/api/v1/mortalidades/",
            {
                "lote_id": lote_id,
                "fecha_hora": iso(dias, 11),
                "cantidad": cantidad,
                "causa": PREF,
                "observaciones": PREF,
            },
        )


def _alimentaciones(token: str, lote_id: int, producto_id: int, puntos: list[tuple[int, float]]) -> None:
    for dias, cantidad in puntos:
        post(
            token,
            "/api/v1/alimentaciones/",
            {
                "lote_id": lote_id,
                "producto_id": producto_id,
                "fecha_hora": iso(dias, 16),
                "cantidad": cantidad,
                "observaciones": PREF,
            },
        )


def _agua(token: str, lote_id: int, parametro_ids: list[int], fechas: list[int]) -> None:
    bases = {
        0: 6.4,
        1: 7.3,
        2: 27.8,
        3: 0.35,
        4: 0.12,
        5: 88.0,
    }
    for i, parametro_id in enumerate(parametro_ids):
        base = bases.get(i, 1.0)
        for j, dias in enumerate(fechas):
            post(
                token,
                "/api/v1/mediciones-agua/",
                {
                    "lote_id": lote_id,
                    "parametro_id": parametro_id,
                    "fecha_hora": iso(dias, 8 + (i % 3)),
                    "valor": round(base + j * 0.08, 3),
                    "observaciones": PREF,
                },
            )


def _biofloc(token: str, lote_id: int, puntos: list[tuple[int, float, float | None]]) -> None:
    for dias, volumen, cn in puntos:
        post(
            token,
            "/api/v1/mediciones-biofloc/",
            {
                "lote_id": lote_id,
                "fecha_hora": iso(dias, 9),
                "volumen_sedimentable": volumen,
                "unidad": "mL/L",
                "relacion_cn": cn,
                "observaciones": PREF,
            },
        )


def _resolver_producto_masa(token: str) -> int:
    """Producto activo con unidad kg/g; crea uno [DEMO] solo para la suite si no existe ninguno."""
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id FROM biofloc.productos p
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE p.activo IS TRUE AND u.simbolo IN ('kg', 'g')
        ORDER BY p.id LIMIT 1
        """
    )
    prod = cur.fetchone()
    cur.close()
    conn.close()
    if prod:
        return int(prod[0])

    categorias = get_json(token, "/api/v1/categorias-inventario/?solo_activos=true")
    unidades = get_json(token, "/api/v1/unidades/?solo_activos=true")
    if not categorias or not unidades:
        raise RuntimeError("Faltan categorías o unidades de inventario para alimentación [DEMO].")
    kg = next((u for u in unidades if u.get("simbolo") == "kg"), None)
    if not kg:
        raise RuntimeError("No hay unidad kg en catálogo para alimentación [DEMO].")
    producto = post(
        token,
        "/api/v1/productos/",
        {
            "codigo": f"{PREF}-ALIM-001",
            "nombre": f"{PREF} alimento laboratorio",
            "categoria_id": categorias[0]["id"],
            "unidad_id": kg["id"],
            "stock_minimo": "0",
            "activo": True,
        },
    )
    return int(producto["id"])


def cargar() -> dict:
    if _ya_existe():
        raise RuntimeError(f"Ya existen registros {PREF}. Ejecute primero: python datos_demo.py limpiar")

    token = login()
    especie = post(
        token,
        "/api/v1/especies/",
        {"nombre_comun": ESPECIE_DEMO, "nombre_cientifico": None, "activo": True},
    )
    etapas = get_json(token, "/api/v1/etapas-productivas/?solo_activos=true")
    estados = get_json(token, "/api/v1/estados-lote/?solo_activos=true")
    if not etapas or not estados:
        raise RuntimeError("Faltan catálogos de etapa o estado de lote (semilla del sistema).")
    etapa = etapas[0]
    estado_activo = next((row for row in estados if row["nombre"] == "ACTIVO"), estados[0])
    estado_fin = next((row for row in estados if row["nombre"] == "FINALIZADO"), None)

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.estados_estanque WHERE nombre='DISPONIBLE' LIMIT 1")
    estado_estanque = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.parametros_agua WHERE activo IS TRUE ORDER BY id LIMIT 6")
    parametros = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    producto_id = _resolver_producto_masa(token)

    categorias = get_json(token, "/api/v1/categorias-gasto/?solo_activos=true")
    categoria_gasto = categorias[0]["id"] if categorias else None

    nombres_utiles = {
        "oxígeno": None,
        "oxigeno": None,
        "ph": None,
        "temperatura": None,
        "amonio": None,
        "nitrito": None,
        "alcalinidad": None,
    }
    r_params = get_json(token, "/api/v1/parametros-agua/?solo_activos=true")
    for row in r_params:
        clave = row["nombre"].lower()
        for nombre in list(nombres_utiles):
            if nombre in clave and nombres_utiles[nombre] is None:
                nombres_utiles[nombre] = row["id"]
    parametro_ids = [pid for pid in nombres_utiles.values() if pid]
    seen: list[int] = []
    for pid in parametro_ids:
        if pid not in seen:
            seen.append(pid)
    parametro_ids = seen or parametros[:6]

    estanque1 = post(
        token,
        "/api/v1/estanques/",
        {
            "codigo": f"{PREF}-EST-1",
            "nombre": f"{PREF} estanque ciclo completo",
            "diametro": 10,
            "profundidad": 1.4,
            "estado_id": estado_estanque,
            "activo": True,
        },
    )
    estanque2 = post(
        token,
        "/api/v1/estanques/",
        {
            "codigo": f"{PREF}-EST-2",
            "nombre": f"{PREF} estanque comparación",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": estado_estanque,
            "activo": True,
        },
    )

    historico = post(
        token,
        "/api/v1/lotes/",
        {
            "codigo": f"{PREF}-LOTE-0",
            "estanque_id": estanque1["id"],
            "especie_id": especie["id"],
            "etapa_productiva_id": etapa["id"],
            "estado_id": estado_activo["id"],
            "fecha_siembra": fecha(120),
            "cantidad_sembrada": 900,
            "peso_inicial_promedio_g": 10.0,
            "observaciones": PREF,
        },
    )
    hid = historico["id"]
    _biometrias(token, hid, [(110, 18.0, 4.2), (95, 42.0, 6.1), (85, 78.0, 8.0), (75, 125.0, 10.2)])
    _mortalidades(token, hid, [(108, 18), (88, 11)])
    _alimentaciones(token, hid, producto_id, [(109, 2.0), (96, 4.5), (84, 7.0), (76, 9.2)])
    _agua(token, hid, parametro_ids[:4], [105, 90, 78])
    _biofloc(token, hid, [(100, 16.0, 11.0), (82, 21.0, 13.0)])
    post(
        token,
        "/api/v1/cosechas/",
        {
            "lote_id": hid,
            "fecha_hora": iso(72, 14),
            "cantidad_peces": 400,
            "peso_total_kg": 48.0,
            "peso_promedio_g": 120.0,
            "observaciones": PREF,
        },
    )
    post(
        token,
        "/api/v1/ventas/",
        {
            "fecha": fecha(71),
            "cliente": f"{PREF} cliente ciclo 0",
            "observaciones": PREF,
            "detalles": [{"lote_id": hid, "cantidad": 48.0, "precio_unitario": 12000}],
        },
    )
    if categoria_gasto:
        post(
            token,
            "/api/v1/gastos/",
            {
                "fecha": fecha(80),
                "categoria_id": categoria_gasto,
                "lote_id": hid,
                "descripcion": f"{PREF} gasto directo ciclo 0",
                "valor": 180000,
                "proveedor": PREF,
                "observaciones": PREF,
            },
        )
    if estado_fin:
        put(
            token,
            f"/api/v1/lotes/{hid}",
            {"estado_id": estado_fin["id"], "fecha_cierre": fecha(70), "observaciones": PREF},
        )

    activo = post(
        token,
        "/api/v1/lotes/",
        {
            "codigo": f"{PREF}-LOTE-1",
            "estanque_id": estanque1["id"],
            "especie_id": especie["id"],
            "etapa_productiva_id": etapa["id"],
            "estado_id": estado_activo["id"],
            "fecha_siembra": fecha(56),
            "cantidad_sembrada": 1000,
            "peso_inicial_promedio_g": 12.0,
            "observaciones": PREF,
        },
    )
    aid = activo["id"]
    _biometrias(
        token,
        aid,
        [
            (49, 15.0, 4.0),
            (42, 22.0, 4.8),
            (35, 32.0, 5.7),
            (28, 45.0, 6.8),
            (21, 62.0, 8.0),
            (14, 85.0, 9.2),
            (7, 115.0, 10.4),
            (2, 150.0, 11.5),
        ],
    )
    _mortalidades(token, aid, [(45, 20), (25, 10), (10, 6)])
    _alimentaciones(
        token,
        aid,
        producto_id,
        [(48, 1.5), (41, 2.0), (34, 2.6), (27, 3.4), (20, 4.4), (13, 5.6), (6, 7.0), (1, 8.5)],
    )
    _agua(token, aid, parametro_ids, [50, 36, 22, 10, 2])
    _biofloc(
        token,
        aid,
        [(47, 15.0, 10.0), (33, 18.0, 12.0), (19, 22.0, 13.5), (8, 24.0, 14.0), (1, 26.0, 15.0)],
    )
    if categoria_gasto:
        post(
            token,
            "/api/v1/gastos/",
            {
                "fecha": fecha(12),
                "categoria_id": categoria_gasto,
                "lote_id": aid,
                "descripcion": f"{PREF} gasto directo ciclo activo",
                "valor": 95000,
                "proveedor": PREF,
                "observaciones": PREF,
            },
        )

    comparacion = post(
        token,
        "/api/v1/lotes/",
        {
            "codigo": f"{PREF}-LOTE-2",
            "estanque_id": estanque2["id"],
            "especie_id": especie["id"],
            "etapa_productiva_id": etapa["id"],
            "estado_id": estado_activo["id"],
            "fecha_siembra": fecha(42),
            "cantidad_sembrada": 600,
            "peso_inicial_promedio_g": 11.0,
            "observaciones": PREF,
        },
    )
    cid = comparacion["id"]
    _biometrias(token, cid, [(35, 16.0, 4.1), (21, 28.0, 5.4), (10, 48.0, 7.0), (1, 70.0, 8.3)])
    _mortalidades(token, cid, [(30, 8), (9, 4)])
    _alimentaciones(token, cid, producto_id, [(34, 1.2), (20, 2.1), (9, 3.3), (1, 4.0)])
    _agua(token, cid, parametro_ids[:4], [32, 16, 3])
    _biofloc(token, cid, [(28, 14.0, None), (12, 17.0, 11.5), (2, 19.0, 12.0)])

    resumen = {
        "especie_id": especie["id"],
        "estanque_id": estanque1["id"],
        "estanque2_id": estanque2["id"],
        "lote_historico_id": hid,
        "lote_activo_id": aid,
        "lote_comparacion_id": cid,
    }
    print(
        f"Cargado {PREF}: {estanque1['codigo']} (lotes 0 histórico + 1 activo) y {estanque2['codigo']} "
        f"(lote 2). Especie '{ESPECIE_DEMO}'. Sin referencias inventadas."
    )
    return resumen


def limpiar() -> int:
    patron = f"{PREF}%"
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.lotes WHERE codigo LIKE %s OR observaciones LIKE %s", (patron, patron))
    lotes = [row[0] for row in cur.fetchall()]
    if lotes:
        cur.execute("SELECT venta_id FROM biofloc.detalles_venta WHERE lote_id = ANY(%s)", (lotes,))
        ventas = list({row[0] for row in cur.fetchall()})
        cur.execute("DELETE FROM biofloc.detalles_venta WHERE lote_id = ANY(%s)", (lotes,))
        if ventas:
            cur.execute("DELETE FROM biofloc.ventas WHERE id = ANY(%s)", (ventas,))
        cur.execute("DELETE FROM biofloc.gastos WHERE lote_id = ANY(%s)", (lotes,))
        for tabla in (
            "alarmas",
            "mediciones_agua",
            "mediciones_biofloc",
            "aplicaciones_biofloc",
            "alimentaciones",
            "biometrias",
            "mortalidades",
            "cosechas",
        ):
            cur.execute(f"DELETE FROM biofloc.{tabla} WHERE lote_id = ANY(%s)", (lotes,))
        cur.execute("DELETE FROM biofloc.lotes WHERE id = ANY(%s)", (lotes,))
    cur.execute(
        "DELETE FROM biofloc.gastos WHERE descripcion LIKE %s OR COALESCE(observaciones,'') LIKE %s",
        (patron, patron),
    )
    cur.execute(
        "DELETE FROM biofloc.ventas WHERE cliente LIKE %s OR COALESCE(observaciones,'') LIKE %s",
        (patron, patron),
    )
    cur.execute("DELETE FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s", (patron, patron))
    cur.execute("SELECT id FROM biofloc.especies WHERE nombre_comun LIKE %s", (patron,))
    especies = [row[0] for row in cur.fetchall()]
    if especies:
        for tabla in ("referencias_agua", "referencias_produccion", "referencias_biofloc"):
            cur.execute(f"DELETE FROM biofloc.{tabla} WHERE especie_id = ANY(%s)", (especies,))
        cur.execute("DELETE FROM biofloc.especies WHERE id = ANY(%s)", (especies,))
    cur.execute("SELECT id FROM biofloc.productos WHERE codigo LIKE %s OR nombre LIKE %s", (patron, patron))
    productos = [row[0] for row in cur.fetchall()]
    if productos:
        cur.execute("DELETE FROM biofloc.movimientos_inventario WHERE producto_id = ANY(%s)", (productos,))
        cur.execute("DELETE FROM biofloc.detalles_compra WHERE producto_id = ANY(%s)", (productos,))
        cur.execute("DELETE FROM biofloc.alimentaciones WHERE producto_id = ANY(%s)", (productos,))
        cur.execute("DELETE FROM biofloc.productos WHERE id = ANY(%s)", (productos,))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    conn.commit()
    cur.close()
    conn.close()
    n = leftover()
    print(f"Limpieza {PREF} terminada. leftover={n}")
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="Datos productivos [DEMO], sin referencias inventadas.")
    parser.add_argument("accion", choices=("cargar", "limpiar"))
    args = parser.parse_args()
    try:
        if args.accion == "cargar":
            cargar()
        else:
            limpiar()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
