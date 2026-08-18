#!/usr/bin/env python3
"""FASE 16.17 — productividad, eficiencia, finanzas trazables e historial."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import requests

import test_analisis_fase16_15 as base
from env_tests import ADMIN_PASS, ADMIN_USER, OPERARIO_PASS, OPERARIO_USER

PREF = "[TEST_F16_17]"
BASE = "http://127.0.0.1:8000"
RESULTADOS: list[tuple[str, bool]] = []
FIN_IDS: dict[str, list[int]] = {"detalles_venta": [], "ventas": [], "gastos": []}


def check(nombre: str, condicion: bool, detalle="") -> None:
    RESULTADOS.append((nombre, condicion))
    print(f"[{'OK' if condicion else 'FAIL'}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def igual(nombre: str, real, esperado) -> None:
    check(nombre, real == esperado, f"real={real!r} esperado={esperado!r}")


def dec(valor) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def post(token: str, ruta: str, tabla: str, payload: dict) -> int:
    ident = base.post(token, ruta, tabla, payload)
    if ident is None:
        raise RuntimeError(f"No se pudo crear {ruta}")
    return ident


def crear_finanzas(lote_id: int) -> None:
    conn = base.db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.usuarios WHERE correo=%s", (ADMIN_USER,))
    usuario_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.categorias_gasto ORDER BY id LIMIT 1")
    categoria_id = cur.fetchone()[0]
    hoy = date.today()
    cur.execute(
        """
        INSERT INTO biofloc.ventas(fecha, cliente, total, observaciones, registrado_por)
        VALUES (%s, %s, 100000, %s, %s) RETURNING id
        """,
        (hoy, f"{PREF} cliente", PREF, usuario_id),
    )
    venta_id = cur.fetchone()[0]
    FIN_IDS["ventas"].append(venta_id)
    cur.execute(
        """
        INSERT INTO biofloc.detalles_venta(venta_id, cantidad, precio_unitario, subtotal, lote_id)
        VALUES (%s, 20, 5000, 100000, %s) RETURNING id
        """,
        (venta_id, lote_id),
    )
    FIN_IDS["detalles_venta"].append(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO biofloc.gastos
          (fecha, categoria_id, lote_id, descripcion, valor, proveedor, observaciones, registrado_por)
        VALUES (%s, %s, %s, %s, 25000, %s, %s, %s) RETURNING id
        """,
        (hoy, categoria_id, lote_id, f"{PREF} gasto directo", PREF, PREF, usuario_id),
    )
    FIN_IDS["gastos"].append(cur.fetchone()[0])
    conn.commit()
    cur.close()
    conn.close()


def limpiar_restos_prefijo() -> None:
    """Recupera también una ejecución interrumpida de esta fase."""
    conn = base.db()
    cur = conn.cursor()
    patron = f"{PREF}%"
    cur.execute("SELECT id FROM biofloc.lotes WHERE observaciones LIKE %s", (patron,))
    lotes = [fila[0] for fila in cur.fetchall()]
    if lotes:
        cur.execute(
            "DELETE FROM biofloc.detalles_venta WHERE lote_id = ANY(%s) RETURNING venta_id",
            (lotes,),
        )
        ventas = list({fila[0] for fila in cur.fetchall()})
        for tabla in (
            "mediciones_agua", "mediciones_biofloc", "aplicaciones_biofloc",
            "alimentaciones", "biometrias", "mortalidades", "cosechas", "alarmas", "gastos",
        ):
            cur.execute(f"DELETE FROM biofloc.{tabla} WHERE lote_id = ANY(%s)", (lotes,))
        cur.execute("DELETE FROM biofloc.lotes WHERE id = ANY(%s)", (lotes,))
        if ventas:
            cur.execute("DELETE FROM biofloc.ventas WHERE id = ANY(%s)", (ventas,))
    cur.execute("DELETE FROM biofloc.gastos WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.ventas WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.referencias_produccion WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.referencias_agua WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.productos WHERE nombre LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.parametros_agua WHERE nombre LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.estanques WHERE nombre LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.especies WHERE nombre_comun LIKE %s", (patron,))
    conn.commit()
    cur.close()
    conn.close()


def cleanup() -> int:
    conn = base.db()
    cur = conn.cursor()
    for tabla in ("detalles_venta", "gastos", "ventas"):
        ids = FIN_IDS[tabla]
        if ids:
            cur.execute(f"DELETE FROM biofloc.{tabla} WHERE id = ANY(%s)", (ids,))
    conn.commit()
    cur.close()
    conn.close()
    base.cleanup()
    limpiar_restos_prefijo()
    conn = base.db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.estanques WHERE nombre LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.lotes WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.productos WHERE nombre LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.ventas WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.gastos WHERE observaciones LIKE %s)
        """,
        tuple(f"{PREF}%" for _ in range(5)),
    )
    leftover = cur.fetchone()[0]
    cur.close()
    conn.close()
    return leftover


def sin_no_finitos(valor) -> bool:
    if isinstance(valor, dict):
        return all(sin_no_finitos(item) for item in valor.values())
    if isinstance(valor, list):
        return all(sin_no_finitos(item) for item in valor)
    if isinstance(valor, float):
        return math.isfinite(valor)
    if isinstance(valor, str) and valor.lower() in {"nan", "infinity", "-infinity"}:
        return False
    return True


def main() -> int:
    limpiar_restos_prefijo()
    base.PREF = PREF
    admin = base.login(ADMIN_USER, ADMIN_PASS)
    operario = base.login(OPERARIO_USER, OPERARIO_PASS)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    amb = base.Ambiente(stamp)
    hoy = date.today()
    siembra = hoy - timedelta(days=14)
    est = base.crear_estanque(admin, f"E17-{stamp}", amb.estado_estanque)
    lote = base.crear_lote(admin, amb, est, f"L17-{stamp}", siembra, 1000, 10)
    if not est or not lote:
        cleanup()
        return 1
    ahora = datetime.now(timezone.utc)

    post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote, "fecha_hora": (ahora - timedelta(days=7)).isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 200, "observaciones": PREF,
    })
    post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote, "fecha_hora": ahora.isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 300, "observaciones": PREF,
    })
    post(admin, "/api/v1/mortalidades/", "mortalidades", {
        "lote_id": lote, "fecha_hora": (ahora - timedelta(days=5)).isoformat(),
        "cantidad": 20, "causa": PREF, "observaciones": PREF,
    })
    post(admin, "/api/v1/cosechas/", "cosechas", {
        "lote_id": lote, "fecha_hora": (ahora - timedelta(days=1)).isoformat(),
        "cantidad_peces": 50, "peso_total_kg": 12.5, "observaciones": PREF,
    })
    for dias, cantidad in ((8, 4), (2, 5)):
        post(admin, "/api/v1/alimentaciones/", "alimentaciones", {
            "lote_id": lote, "producto_id": amb.producto_kg,
            "fecha_hora": (ahora - timedelta(days=dias)).isoformat(),
            "cantidad": cantidad, "observaciones": PREF,
        })
    crear_finanzas(lote)

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote}", headers=base.H(admin), timeout=30)
    igual("GET análisis", r.status_code, 200)
    data = r.json()
    igual("población congelada", data["indicadores"]["poblacion_estimada"], 930)
    igual("biomasa inicial", dec(data["indicadores"]["biomasa_inicial_kg"]), Decimal("10.000"))
    igual("biomasa actual", dec(data["productividad"]["biomasa_actual_kg"]), Decimal("27.900"))
    igual("ganancia de biomasa", dec(data["productividad"]["ganancia_biomasa_kg"]), Decimal("17.900"))
    igual("producción cosechada", dec(data["productividad"]["peso_cosechado_kg"]), Decimal("12.500"))
    igual("peces producidos/cosechados", data["productividad"]["peces_cosechados"], 50)
    igual("alimento real", dec(data["eficiencia"]["alimento_real_acumulado_kg"]), Decimal("9.000"))
    igual("FCA congelado", dec(data["eficiencia"]["fca"]), Decimal("0.5028"))
    igual("crecimiento histórico", [dec(p["ganancia_peso_g"]) for p in data["serie_crecimiento"]], [Decimal("10.000"), Decimal("20.000")])
    igual("población as-of final", data["serie_poblacion"][-1]["poblacion_estimada"], 930)
    igual("ingreso trazable", dec(data["finanzas"]["ingresos_lote"]), Decimal("100000.00"))
    igual("gasto directo trazable", dec(data["finanzas"]["gastos_directos_lote"]), Decimal("25000.00"))
    igual("costos completos no inventados", data["finanzas"]["costos_completos"], False)
    igual("utilidad no inventada", data["finanzas"]["utilidad"], None)
    igual("costo/kg no inventado", data["eficiencia"]["costo_por_kg"], None)
    check("sin NaN ni Infinity", sin_no_finitos(data))

    comp = requests.get(f"{BASE}/api/v1/analisis/estanques", headers=base.H(operario), params={
        "solo_activos": "false", "estanque_id": est, "incluir_historial": "true",
    }, timeout=30)
    igual("operario puede comparar", comp.status_code, 200)
    comparativo = comp.json()
    igual("comparativo filtrado", len(comparativo["estanques"]), 1)
    igual("historial del estanque", [c["lote_id"] for c in comparativo["ciclos"]], [lote])
    igual("comparativo reutiliza FCA", dec(comparativo["estanques"][0]["eficiencia"]["fca"]), Decimal("0.5028"))
    igual("dashboard analítico cosechado", dec(comparativo["resumen"]["peso_cosechado_kg"]), Decimal("12.500"))
    igual("FCA granja sigue N/D", comparativo["resumen"]["fca"], None)

    igual("sin credenciales 403", requests.get(f"{BASE}/api/v1/analisis/lotes/{lote}", timeout=20).status_code, 403)
    igual(
        "token inválido 401",
        requests.get(
            f"{BASE}/api/v1/analisis/lotes/{lote}",
            headers={"Authorization": "Bearer token-invalido"},
            timeout=20,
        ).status_code,
        401,
    )
    igual("lote inexistente 404", requests.get(f"{BASE}/api/v1/analisis/lotes/999999999", headers=base.H(admin), timeout=20).status_code, 404)
    igual("estanque_id inválido 422", requests.get(f"{BASE}/api/v1/analisis/estanques", headers=base.H(admin), params={"estanque_id": 0}, timeout=20).status_code, 422)

    leftover = cleanup()
    igual("LEFTOVER", leftover, 0)
    ok = sum(1 for _, bien in RESULTADOS if bien)
    print(f"\nRESULT {ok}/{len(RESULTADOS)} OK")
    return 0 if ok == len(RESULTADOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
