"""Lote operativo temporal y aislado para suites HTTP.

Cada llamada crea un estanque y un lote con sufijo único [TEST_FIXTURE].
No reutiliza DEMO, TEST_FIXTURE previo ni producción real.
El caller DEBE invocar limpiar_fixtures() al terminar.
"""
from __future__ import annotations

import uuid
from typing import Any

import psycopg2
import requests

from env_tests import ADMIN_PASS, ADMIN_USER, DB_CONF

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_FIXTURE]"

_CREATED: list[dict[str, Any]] = []

TABLAS_LOTE = (
    "alarmas",
    "detalles_venta",
    "gastos",
    "mediciones_agua",
    "mediciones_biofloc",
    "aplicaciones_biofloc",
    "alimentaciones",
    "biometrias",
    "mortalidades",
    "cosechas",
)


def _login() -> str:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": ADMIN_USER, "password": ADMIN_PASS},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _producto_masa_existente() -> int | None:
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id FROM biofloc.productos p
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE p.activo IS TRUE AND u.simbolo IN ('kg', 'g')
        ORDER BY p.id LIMIT 1
        """
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return int(row[0]) if row else None


def _crear_producto_fixture(token: str, simbolo: str = "kg") -> int:
    suffix = uuid.uuid4().hex[:8]
    cats = requests.get(
        f"{BASE}/api/v1/categorias-inventario/?solo_activos=true", headers=_h(token), timeout=20
    )
    cats.raise_for_status()
    unids = requests.get(f"{BASE}/api/v1/unidades/?solo_activos=true", headers=_h(token), timeout=20)
    unids.raise_for_status()
    categorias = cats.json() or []
    unidades = unids.json() or []
    if not categorias or not unidades:
        raise RuntimeError("Faltan categorías o unidades para crear producto de prueba.")
    unidad = next((u for u in unidades if u.get("simbolo") == simbolo), None)
    if not unidad:
        raise RuntimeError(f"No hay unidad {simbolo} en catálogo para pruebas de alimentación.")
    r = requests.post(
        f"{BASE}/api/v1/productos/",
        headers=_h(token),
        json={
            "codigo": f"{PREF}-PROD-{suffix}",
            "nombre": f"{PREF} alimento temporal {simbolo}",
            "categoria_id": categorias[0]["id"],
            "unidad_id": unidad["id"],
            "stock_minimo": "0",
            "activo": True,
        },
        timeout=20,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"POST producto fixture: {r.status_code} {r.text[:300]}")
    producto_id = int(r.json()["id"])
    _CREATED.append({"producto_id": producto_id})
    return producto_id


def asegurar_stock(token: str | None = None, producto_id: int = 0, cantidad: float = 100.0) -> None:
    """Asegura stock mínimo para un producto creando una ENTRADA si es necesario."""
    token = token or _login()
    conn = _db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.tipos_movimiento_inventario WHERE nombre = 'ENTRADA'")
    tipo_id = cur.fetchone()[0]
    cur.execute(
        "SELECT COALESCE(stock_actual, 0) FROM biofloc.vista_stock_productos WHERE producto_id = %s",
        (producto_id,)
    )
    row = cur.fetchone()
    stock = float(row[0]) if row else 0.0
    cur.close()
    conn.close()
    if stock >= cantidad:
        return
    necesita = cantidad - stock + 10
    r = requests.post(
        f"{BASE}/api/v1/movimientos-inventario/",
        headers=_h(token),
        json={
            "producto_id": producto_id,
            "tipo_movimiento_id": tipo_id,
            "cantidad": necesita,
            "observaciones": f"{PREF} Stock setup",
        },
        timeout=20,
    )
    r.raise_for_status()


def obtener_producto_activo(token: str | None = None) -> int:
    """Producto activo con unidad de masa; crea fixture temporal si el catálogo está vacío."""
    existente = _producto_masa_existente()
    if existente:
        return existente
    token = token or _login()
    r = requests.get(f"{BASE}/api/v1/productos/?solo_activos=true", headers=_h(token), timeout=20)
    r.raise_for_status()
    productos = r.json() or []
    if productos:
        return int(productos[0]["id"])
    return _crear_producto_fixture(token)


def _db():
    return psycopg2.connect(**DB_CONF)


def crear_producto_masa(token: str | None = None, simbolo: str = "kg") -> int:
    """Producto de prueba en la unidad indicada (kg o g)."""
    token = token or _login()
    return _crear_producto_fixture(token, simbolo=simbolo)


def crear_lote_temporal(
    token: str | None = None,
    *,
    cantidad_sembrada: int = 1000,
    estanque_id: int | None = None,
    fecha_siembra: str = "2026-01-15",
) -> dict[str, Any]:
    """Crea estanque + lote únicos. No reutiliza filas existentes."""
    token = token or _login()
    suffix = uuid.uuid4().hex[:8]
    codigo_est = f"{PREF}-E-{suffix}"
    codigo_lote = f"{PREF}-L-{suffix}"

    especies = requests.get(f"{BASE}/api/v1/especies/?solo_activos=true", headers=_h(token), timeout=20)
    especies.raise_for_status()
    etapas = requests.get(f"{BASE}/api/v1/etapas-productivas/?solo_activos=true", headers=_h(token), timeout=20)
    etapas.raise_for_status()
    estados_lote = requests.get(f"{BASE}/api/v1/estados-lote/?solo_activos=true", headers=_h(token), timeout=20)
    estados_lote.raise_for_status()
    estados_est = requests.get(f"{BASE}/api/v1/estados-estanque/?solo_activos=true", headers=_h(token), timeout=20)
    estados_est.raise_for_status()

    especie = (especies.json() or [None])[0]
    etapa = (etapas.json() or [None])[0]
    estados = estados_lote.json() or []
    estado_lote = next((row for row in estados if row.get("nombre") == "ACTIVO"), estados[0] if estados else None)
    estados_e = estados_est.json() or []
    estado_est = next((row for row in estados_e if row.get("nombre") == "DISPONIBLE"), estados_e[0] if estados_e else None)
    if not all([especie, etapa, estado_lote, estado_est]):
        raise RuntimeError("Faltan catálogos semilla para crear un lote temporal de prueba.")

    if estanque_id is None:
        est = requests.post(
            f"{BASE}/api/v1/estanques/",
            headers=_h(token),
            json={
                "codigo": codigo_est,
                "nombre": f"{PREF} estanque temporal {suffix}",
                "diametro": 8,
                "profundidad": 1.2,
                "estado_id": estado_est["id"],
                "activo": True,
            },
            timeout=20,
        )
        if est.status_code not in (200, 201):
            raise RuntimeError(f"POST estanque fixture: {est.status_code} {est.text[:300]}")
        estanque_id = est.json()["id"]
    else:
        codigo_est = ""

    lote = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=_h(token),
        json={
            "codigo": codigo_lote,
            "estanque_id": estanque_id,
            "especie_id": especie["id"],
            "etapa_productiva_id": etapa["id"],
            "estado_id": estado_lote["id"],
            "fecha_siembra": fecha_siembra,
            "cantidad_sembrada": cantidad_sembrada,
            "observaciones": PREF,
        },
        timeout=20,
    )
    if lote.status_code not in (200, 201):
        raise RuntimeError(f"POST lote fixture: {lote.status_code} {lote.text[:300]}")
    data = lote.json()
    fixture = {
        "id": data["id"],
        "fecha_siembra": data["fecha_siembra"],
        "cantidad_sembrada": data["cantidad_sembrada"],
        "codigo": data["codigo"],
        "estanque_id": estanque_id,
        "codigo_estanque": codigo_est,
    }
    _CREATED.append(fixture)
    return fixture


def asegurar_lote(token: str | None = None) -> tuple:
    """Compatibilidad: (id, fecha_siembra, cantidad_sembrada, codigo). Siempre crea uno nuevo."""
    fixture = crear_lote_temporal(token)
    return (fixture["id"], fixture["fecha_siembra"], fixture["cantidad_sembrada"], fixture["codigo"])


def _borrar_lotes(cur, lote_ids: list[int]) -> None:
    if not lote_ids:
        return
    cur.execute("SELECT venta_id FROM biofloc.detalles_venta WHERE lote_id = ANY(%s)", (lote_ids,))
    ventas = list({row[0] for row in cur.fetchall()})
    for tabla in TABLAS_LOTE:
        cur.execute(f"DELETE FROM biofloc.{tabla} WHERE lote_id = ANY(%s)", (lote_ids,))
    if ventas:
        cur.execute(
            "DELETE FROM biofloc.detalles_venta WHERE venta_id = ANY(%s)",
            (ventas,),
        )
        cur.execute("DELETE FROM biofloc.ventas WHERE id = ANY(%s)", (ventas,))
    cur.execute(
        "DELETE FROM biofloc.auditoria WHERE tabla = 'lotes' AND registro_id = ANY(%s)",
        (lote_ids,),
    )
    cur.execute("DELETE FROM biofloc.lotes WHERE id = ANY(%s)", (lote_ids,))


def _borrar_estanques(cur, estanque_ids: list[int]) -> None:
    if not estanque_ids:
        return
    cur.execute(
        "DELETE FROM biofloc.auditoria WHERE tabla = 'estanques' AND registro_id = ANY(%s)",
        (estanque_ids,),
    )
    cur.execute("DELETE FROM biofloc.estanques WHERE id = ANY(%s)", (estanque_ids,))


def _borrar_productos(cur, producto_ids: list[int]) -> None:
    if not producto_ids:
        return
    cur.execute("DELETE FROM biofloc.movimientos_inventario WHERE producto_id = ANY(%s)", (producto_ids,))
    cur.execute("DELETE FROM biofloc.detalles_compra WHERE producto_id = ANY(%s)", (producto_ids,))
    cur.execute("DELETE FROM biofloc.alimentaciones WHERE producto_id = ANY(%s)", (producto_ids,))
    cur.execute(
        "DELETE FROM biofloc.auditoria WHERE tabla = 'productos' AND registro_id = ANY(%s)",
        (producto_ids,),
    )
    cur.execute("DELETE FROM biofloc.productos WHERE id = ANY(%s)", (producto_ids,))


def _limpiar_por_prefijo(cur, prefijo: str) -> None:
    patron = f"{prefijo}%"
    cur.execute(
        "SELECT id FROM biofloc.lotes WHERE codigo LIKE %s OR COALESCE(observaciones,'') LIKE %s",
        (patron, patron),
    )
    lote_ids = [row[0] for row in cur.fetchall()]
    _borrar_lotes(cur, lote_ids)
    cur.execute(
        "DELETE FROM biofloc.gastos WHERE descripcion LIKE %s OR COALESCE(observaciones,'') LIKE %s OR COALESCE(proveedor,'') LIKE %s",
        (patron, patron, patron),
    )
    cur.execute(
        "DELETE FROM biofloc.ventas WHERE cliente LIKE %s OR COALESCE(observaciones,'') LIKE %s",
        (patron, patron),
    )
    cur.execute("SELECT id FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s", (patron, patron))
    _borrar_estanques(cur, [row[0] for row in cur.fetchall()])
    cur.execute("SELECT id FROM biofloc.especies WHERE nombre_comun LIKE %s", (patron,))
    especies = [row[0] for row in cur.fetchall()]
    if especies:
        for tabla in ("referencias_agua", "referencias_produccion", "referencias_biofloc"):
            cur.execute(f"DELETE FROM biofloc.{tabla} WHERE especie_id = ANY(%s)", (especies,))
        cur.execute("DELETE FROM biofloc.especies WHERE id = ANY(%s)", (especies,))
    cur.execute("SELECT id FROM biofloc.productos WHERE codigo LIKE %s OR nombre LIKE %s", (patron, patron))
    _borrar_productos(cur, [row[0] for row in cur.fetchall()])
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{prefijo}%",))


def limpiar_lote_temporal(lote_id: int, estanque_id: int | None = None) -> None:
    conn = _db()
    cur = conn.cursor()
    _borrar_lotes(cur, [lote_id])
    if estanque_id:
        _borrar_estanques(cur, [estanque_id])
    conn.commit()
    cur.close()
    conn.close()


def limpiar_fixtures() -> int:
    """Elimina fixtures creados en este proceso y cualquier residual [TEST_FIXTURE]."""
    conn = _db()
    cur = conn.cursor()
    lote_ids = [row["id"] for row in _CREATED if row.get("id")]
    estanque_ids = [row["estanque_id"] for row in _CREATED if row.get("estanque_id")]
    producto_ids = [row["producto_id"] for row in _CREATED if row.get("producto_id")]
    _borrar_lotes(cur, lote_ids)
    _borrar_estanques(cur, estanque_ids)
    _borrar_productos(cur, producto_ids)
    _limpiar_por_prefijo(cur, PREF)
    conn.commit()
    cur.close()
    conn.close()
    _CREATED.clear()
    return leftover_test_fixture()


def leftover_demo() -> int:
    return _count_prefijo("[DEMO]")


def leftover_test_fixture() -> int:
    return _count_prefijo(PREF)


def leftover_audit() -> int:
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.parametros_agua WHERE nombre LIKE 'AUDIT_PARAM_%%') +
          (SELECT COUNT(*) FROM biofloc.estanques WHERE codigo LIKE 'EST-AUDIT-%%') +
          (SELECT COUNT(*) FROM biofloc.lotes WHERE codigo LIKE 'LOT-AUDIT-%%') +
          (SELECT COUNT(*) FROM biofloc.auditoria
             WHERE detalle::text LIKE '%%AUDIT_PARAM_%%'
                OR detalle::text LIKE '%%EST-AUDIT-%%'
                OR detalle::text LIKE '%%LOT-AUDIT-%%')
        """
    )
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def leftover_test_residuos() -> int:
    """Productos y registros con prefijos TEST_/F16_/TEST- sin ser TEST_FIXTURE."""
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.productos
             WHERE codigo LIKE 'TEST-%%'
                OR codigo LIKE '[F16_%%'
                OR codigo LIKE 'P14-%%'
                OR nombre ILIKE '%%Alimento Test%%'
                OR nombre LIKE '[TEST_%%'
                OR nombre LIKE '[F16_%%') +
          (SELECT COUNT(*) FROM biofloc.lotes
             WHERE codigo LIKE 'TEST-%%' OR codigo LIKE 'F16-%%' OR codigo LIKE 'TEST_%%') +
          (SELECT COUNT(*) FROM biofloc.estanques
             WHERE codigo LIKE 'TEST-%%' OR codigo LIKE 'F16-%%')
        """
    )
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def _limpiar_productos_prueba(cur) -> None:
    cur.execute(
        """
        SELECT id FROM biofloc.productos
         WHERE codigo LIKE 'TEST-%%'
            OR codigo LIKE '[F16_%%'
            OR codigo LIKE 'P14-%%'
            OR nombre ILIKE '%%Alimento Test%%'
            OR nombre LIKE '[TEST_%%'
            OR nombre LIKE '[F16_%%'
        """
    )
    producto_ids = [row[0] for row in cur.fetchall()]
    if not producto_ids:
        return
    cur.execute(
        "DELETE FROM biofloc.movimientos_inventario WHERE producto_id = ANY(%s)",
        (producto_ids,),
    )
    cur.execute(
        "DELETE FROM biofloc.detalles_compra WHERE producto_id = ANY(%s)",
        (producto_ids,),
    )
    cur.execute(
        "DELETE FROM biofloc.alimentaciones WHERE producto_id = ANY(%s)",
        (producto_ids,),
    )
    cur.execute("DELETE FROM biofloc.productos WHERE id = ANY(%s)", (producto_ids,))


def leftover_laboratorio() -> dict[str, int]:
    return {
        "DEMO": leftover_demo(),
        "TEST_FIXTURE": leftover_test_fixture(),
        "AUDIT": leftover_audit(),
        "TEST_RESIDUOS": leftover_test_residuos(),
    }


def _count_prefijo(prefijo: str) -> int:
    patron = f"{prefijo}%"
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.lotes WHERE codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.especies WHERE nombre_comun LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.ventas WHERE cliente LIKE %s OR COALESCE(observaciones,'') LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.gastos WHERE descripcion LIKE %s OR COALESCE(observaciones,'') LIKE %s)
        """,
        (patron, patron, patron, patron, patron, patron, patron, patron),
    )
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def limpiar_laboratorio() -> dict[str, int]:
    """Limpia DEMO, TEST_FIXTURE y residual AUDIT de laboratorio. No toca catálogos semilla."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo"))
    from datos_demo import limpiar as limpiar_demo  # noqa: E402

    limpiar_demo()
    conn = _db()
    cur = conn.cursor()
    _limpiar_por_prefijo(cur, PREF)
    cur.execute("SELECT id FROM biofloc.lotes WHERE codigo LIKE 'LOT-AUDIT-%%'")
    _borrar_lotes(cur, [row[0] for row in cur.fetchall()])
    cur.execute("SELECT id FROM biofloc.estanques WHERE codigo LIKE 'EST-AUDIT-%%'")
    _borrar_estanques(cur, [row[0] for row in cur.fetchall()])
    cur.execute("DELETE FROM biofloc.parametros_agua WHERE nombre LIKE 'AUDIT_PARAM_%%'")
    cur.execute(
        """
        DELETE FROM biofloc.auditoria
         WHERE detalle::text LIKE '%%AUDIT_PARAM_%%'
            OR detalle::text LIKE '%%EST-AUDIT-%%'
            OR detalle::text LIKE '%%LOT-AUDIT-%%'
            OR detalle::text LIKE '%%[TEST_FIXTURE]%%'
            OR detalle::text LIKE '%%[DEMO]%%'
            OR detalle::text LIKE '%%[TEST_CATALOGOS]%%'
            OR detalle::text LIKE '%%TEST-PROD-%%'
            OR detalle::text LIKE '%%Alimento Test%%'
        """
    )
    _limpiar_productos_prueba(cur)
    conn.commit()
    cur.close()
    conn.close()
    _CREATED.clear()
    return leftover_laboratorio()
