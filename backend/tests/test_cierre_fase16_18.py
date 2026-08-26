#!/usr/bin/env python3
"""FASE 16.18 — auditoría de cierre del ERP V1.

No introduce reglas de negocio: verifica sobre el sistema en marcha que

  · las fórmulas congeladas siguen dando exactamente el mismo resultado;
  · las unidades no se mezclan (g, kg y unidades no convertibles);
  · el mismo indicador coincide en análisis, comparativo y reportes;
  · lo que no se puede calcular viaja como null con motivo, nunca como 0;
  · REAL vs RANGO no se convierte en severidad inventada;
  · el análisis no crea alarmas ni movimientos de inventario;
  · el RBAC lo aplica el backend, no la UI;
  · los errores 401/403/404/409/422 no filtran SQL ni trazas.

Prefijo [TEST_F16_18]; al terminar LEFTOVER = 0.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import requests

# Importar la suite base también reconfigura stdout a UTF-8.
import test_analisis_fase16_15 as base
from env_tests import (
    ADMIN_PASS,
    ADMIN_USER,
    OPERARIO_PASS,
    OPERARIO_USER,
    TECNICO_PASS,
    TECNICO_USER,
)

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_F16_18]"
RESULTADOS: list[tuple[str, bool]] = []
FIN_IDS: dict[str, list[int]] = {"detalles_venta": [], "ventas": [], "gastos": []}

FUGAS = ("psycopg", "sqlalchemy", "traceback", "select ", "insert ", "update ", "integrityerror")


def check(nombre: str, condicion: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, bool(condicion)))
    print(f"[{'OK' if condicion else 'FAIL'}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def igual(nombre: str, obtenido, esperado) -> None:
    check(nombre, obtenido == esperado, f"obtenido={obtenido!r} esperado={esperado!r}")


def dec(valor) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def post(token: str, ruta: str, tabla: str, payload: dict) -> int:
    ident = base.post(token, ruta, tabla, payload)
    if ident is None:
        raise RuntimeError(f"No se pudo crear {ruta}")
    return ident


def get(token: str, ruta: str, **params) -> requests.Response:
    return requests.get(f"{BASE}{ruta}", headers=base.H(token), params=params, timeout=30)


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


def detalle_limpio(respuesta: requests.Response) -> bool:
    texto = respuesta.text.lower()
    return not any(fuga in texto for fuga in FUGAS)


def crear_finanzas(lote_id: int) -> None:
    """Venta y gasto imputados al lote: la única base trazable de finanzas."""
    conn = base.db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.usuarios WHERE correo=%s", (ADMIN_USER,))
    usuario_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.categorias_gasto ORDER BY id LIMIT 1")
    categoria_id = cur.fetchone()[0]
    hoy = date.today()
    cur.execute(
        "INSERT INTO biofloc.ventas(fecha, cliente, total, observaciones, registrado_por) "
        "VALUES (%s, %s, 80000, %s, %s) RETURNING id",
        (hoy, f"{PREF} cliente", PREF, usuario_id),
    )
    venta_id = cur.fetchone()[0]
    FIN_IDS["ventas"].append(venta_id)
    cur.execute(
        "INSERT INTO biofloc.detalles_venta(venta_id, cantidad, precio_unitario, subtotal, lote_id) "
        "VALUES (%s, 16, 5000, 80000, %s) RETURNING id",
        (venta_id, lote_id),
    )
    FIN_IDS["detalles_venta"].append(cur.fetchone()[0])
    cur.execute(
        "INSERT INTO biofloc.gastos"
        "(fecha, categoria_id, lote_id, descripcion, valor, proveedor, observaciones, registrado_por) "
        "VALUES (%s, %s, %s, %s, 30000, %s, %s, %s) RETURNING id",
        (hoy, categoria_id, lote_id, f"{PREF} gasto directo", PREF, PREF, usuario_id),
    )
    FIN_IDS["gastos"].append(cur.fetchone()[0])
    conn.commit()
    cur.close()
    conn.close()


def contar(sql: str, args: tuple) -> int:
    conn = base.db()
    cur = conn.cursor()
    cur.execute(sql, args)
    total = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return total


def limpiar_restos_prefijo() -> None:
    """Recupera una ejecución interrumpida antes de volver a medir."""
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
    cur.execute("DELETE FROM biofloc.estanques WHERE nombre LIKE %s OR codigo LIKE %s", (patron, patron))
    cur.execute("DELETE FROM biofloc.especies WHERE nombre_comun LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
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
    return contar(
        """
        SELECT
          (SELECT COUNT(*) FROM biofloc.estanques WHERE nombre LIKE %s OR codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.lotes WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.productos WHERE nombre LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.especies WHERE nombre_comun LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.ventas WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.gastos WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s)
        """,
        tuple([f"{PREF}%"] * 6 + [f"%{PREF}%"] * 2),
    )


def evaluacion(cuerpo: dict, indicador: str) -> dict | None:
    for item in cuerpo["evaluaciones"]:
        if item["indicador"] == indicador:
            return item
    return None


def main() -> int:
    base.PREF = PREF
    limpiar_restos_prefijo()
    admin = base.login(ADMIN_USER, ADMIN_PASS)
    tecnico = base.login(TECNICO_USER, TECNICO_PASS)
    operario = base.login(OPERARIO_USER, OPERARIO_PASS)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    amb = base.Ambiente(stamp)
    ahora = datetime.now(timezone.utc)
    hoy = date.today()

    cod_a = f"E18A-{stamp}"
    est_a = base.crear_estanque(admin, cod_a, amb.estado_estanque)
    est_sin_lote = base.crear_estanque(admin, f"E18B-{stamp}", amb.estado_estanque)
    est_vacio = base.crear_estanque(admin, f"E18C-{stamp}", amb.estado_estanque)
    est_unidad = base.crear_estanque(admin, f"E18D-{stamp}", amb.estado_estanque)
    if not all((est_a, est_sin_lote, est_vacio, est_unidad)):
        cleanup()
        return 1

    # Lote completo: 1000 peces, 10 g iniciales, 14 días de cultivo (semana 3).
    lote = base.crear_lote(admin, amb, est_a, f"L18A-{stamp}", hoy - timedelta(days=14), 1000, 10)
    lote_vacio = base.crear_lote(admin, amb, est_vacio, f"L18C-{stamp}", hoy - timedelta(days=3), 500, None)
    lote_unidad = base.crear_lote(admin, amb, est_unidad, f"L18D-{stamp}", hoy - timedelta(days=7), 100, 5)
    if not all((lote, lote_vacio, lote_unidad)):
        cleanup()
        return 1

    for dias, muestra, peso in ((7, 10, 200), (0, 10, 300)):
        post(admin, "/api/v1/biometrias/", "biometrias", {
            "lote_id": lote, "fecha_hora": (ahora - timedelta(days=dias)).isoformat(),
            "cantidad_muestra": muestra, "peso_total_muestra_g": peso, "observaciones": PREF,
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
    for dias, valor, parametro in ((3, 6.0, amb.param_con_ref), (1, 9.0, amb.param_con_ref), (1, 27.5, amb.param_sin_ref)):
        post(admin, "/api/v1/mediciones-agua/", "mediciones_agua", {
            "lote_id": lote, "parametro_id": parametro,
            "fecha_hora": (ahora - timedelta(days=dias)).isoformat(),
            "valor": valor, "observaciones": PREF,
        })
    post(admin, "/api/v1/mediciones-biofloc/", "mediciones_biofloc", {
        "lote_id": lote, "fecha_hora": (ahora - timedelta(days=2)).isoformat(),
        "volumen_sedimentable": 15, "unidad": "mL/L", "relacion_cn": 12, "observaciones": PREF,
    })
    crear_finanzas(lote)

    # Lote con alimento en unidad no convertible junto a kg.
    post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote_unidad, "fecha_hora": ahora.isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 100, "observaciones": PREF,
    })
    post(admin, "/api/v1/alimentaciones/", "alimentaciones", {
        "lote_id": lote_unidad, "producto_id": amb.producto_kg,
        "fecha_hora": (ahora - timedelta(days=2)).isoformat(), "cantidad": 2, "observaciones": PREF,
    })
    post(admin, "/api/v1/alimentaciones/", "alimentaciones", {
        "lote_id": lote_unidad, "producto_id": amb.producto_l,
        "fecha_hora": (ahora - timedelta(days=1)).isoformat(), "cantidad": 3, "observaciones": PREF,
    })

    # ---------------- Fórmulas congeladas ----------------
    r = get(admin, f"/api/v1/analisis/lotes/{lote}")
    igual("análisis del lote responde 200", r.status_code, 200)
    if r.status_code != 200:
        cleanup()
        return 1
    cuerpo = r.json()
    ind = cuerpo["indicadores"]
    igual("peso promedio = 300 g / 10 peces", dec(ind["peso_promedio_g"]), Decimal("30.000"))
    igual("población = 1000 − 20 − 50", ind["poblacion_estimada"], 930)
    igual("supervivencia = (1000 − 20) / 1000 × 100", dec(ind["supervivencia_porcentaje"]), Decimal("98.00"))
    igual("mortalidad = 20 / 1000 × 100", dec(ind["mortalidad_porcentaje"]), Decimal("2.00"))
    igual("biomasa inicial = 1000 × 10 g / 1000", dec(ind["biomasa_inicial_kg"]), Decimal("10.000"))
    igual("biomasa actual = 930 × 30 g / 1000", dec(ind["biomasa_actual_kg"]), Decimal("27.900"))
    igual("ganancia de peso = 30 − 10", dec(ind["ganancia_peso_g"]), Decimal("20.000"))
    igual("ganancia diaria = 20 / 14 días", dec(ind["ganancia_diaria_g"]), Decimal("1.428571"))
    igual("ración = 27.900 kg × 3 % / 100", dec(ind["racion_diaria_recomendada_kg"]), Decimal("0.837"))
    igual("alimento real = 4 kg + 5 kg", dec(ind["alimento_real_acumulado_kg"]), Decimal("9.000"))
    igual("FCA = 9 / (27.900 + 12.500 − 10.000)", dec(ind["fca"]), Decimal("0.2961"))
    igual("días de cultivo", ind["dias_cultivo"], 14)
    # Semana = floor(días / 7) + 1: 14 días son la semana 3. Tasa de la ref 3–4 = 3 %.
    igual("semana de cultivo = floor(14 / 7) + 1", ind["semana_cultivo"], 3)
    igual("referencia de la semana 3", dec(cuerpo["referencia_produccion"]["tasa_alimentacion_pct"]), Decimal("3.000"))
    check("sin NaN ni Infinity en el análisis", sin_no_finitos(cuerpo))

    # ---------------- Productividad y eficiencia separadas ----------------
    prod = cuerpo["productividad"]
    efi = cuerpo["eficiencia"]
    igual("productividad: biomasa actual", dec(prod["biomasa_actual_kg"]), Decimal("27.900"))
    igual("productividad: ganancia de biomasa", dec(prod["ganancia_biomasa_kg"]), Decimal("30.400"))
    igual("productividad: cosecha en kg", dec(prod["peso_cosechado_kg"]), Decimal("12.500"))
    igual("productividad: peces cosechados", prod["peces_cosechados"], 50)
    check("productividad no expone FCA ni costos", "fca" not in prod and "costo_por_kg" not in prod)
    igual("eficiencia: FCA reutilizado", dec(efi["fca"]), Decimal("0.2961"))
    igual("eficiencia: alimento real en kg", dec(efi["alimento_real_acumulado_kg"]), Decimal("9.000"))
    igual("eficiencia: FCA disponible", efi["fca_disponible"], True)
    check("eficiencia no duplica la cosecha", "peso_cosechado_kg" not in efi)

    # ---------------- Finanzas trazables ----------------
    fin = cuerpo["finanzas"]
    igual("ingresos imputados al lote", dec(fin["ingresos_lote"]), Decimal("80000.00"))
    igual("gastos directos del lote", dec(fin["gastos_directos_lote"]), Decimal("30000.00"))
    igual("costos incompletos declarados", fin["costos_completos"], False)
    igual("utilidad no inventada", fin["utilidad"], None)
    igual("margen no inventado", fin["margen_porcentaje"], None)
    igual("costo por kg no inventado", efi["costo_por_kg"], None)
    check("cada N/D financiero trae motivo",
          all(fin[clave] for clave in ("utilidad_motivo", "margen_motivo", "costos_completos_motivo")))

    # ---------------- REAL vs RANGO sin severidad inventada ----------------
    agua_ref = evaluacion(cuerpo, f"agua:{amb.param_con_ref}")
    agua_sin_ref = evaluacion(cuerpo, f"agua:{amb.param_sin_ref}")
    igual("agua fuera de rango se marca como incumplimiento",
          agua_ref and agua_ref["cumplimiento_rango"], "FUERA_RANGO")
    igual("fuera de rango no se convierte en ALERTA",
          agua_ref and agua_ref["estado_analitico"], None)
    igual("agua con rango informa mínimo y máximo",
          agua_ref and (dec(agua_ref["minimo"]), dec(agua_ref["maximo"])),
          (Decimal("5.0000"), Decimal("8.0000")))
    igual("agua sin referencia queda SIN_REFERENCIA",
          agua_sin_ref and agua_sin_ref["estado_analitico"], "SIN_REFERENCIA")
    igual("agua sin referencia no evalúa rango",
          agua_sin_ref and agua_sin_ref["cumplimiento_rango"], "NO_EVALUABLE")
    check("ninguna evaluación inventa severidad",
          all(item["estado_analitico"] not in ("ALERTA", "CRITICO") for item in cuerpo["evaluaciones"]))
    check("recomendación de agua es trazable y sin cantidades",
          any(rec["indicador"] == f"agua:{amb.param_con_ref}" for rec in cuerpo["recomendaciones"]))
    cn = evaluacion(cuerpo, "relacion_cn")
    igual("C:N sin objetivo inventado", cn and cn["objetivo"], None)
    igual("C:N real conservado sin severidad",
          cn and (dec(cn["real"]), cn["estado_analitico"]),
          (Decimal("12.000"), "SIN_REFERENCIA"))

    # ---------------- Alimentación: real vs recomendado ----------------
    alim = evaluacion(cuerpo, "alimentacion_diaria_kg")
    igual("alimento real del último día registrado", dec(alim["real"]), Decimal("5.000"))
    igual("objetivo = ración recomendada vigente", dec(alim["objetivo"]), Decimal("1.116"))
    check("se informan ambas fechas",
          bool(alim["fecha_real"]) and bool(alim["fecha_referencia"]) and alim["fecha_real"] != alim["fecha_referencia"],
          f"real={alim['fecha_real']} referencia={alim['fecha_referencia']}")

    # ---------------- Unidades: nunca se mezclan ----------------
    r_unidad = get(admin, f"/api/v1/analisis/lotes/{lote_unidad}")
    igual("análisis con unidad no convertible responde 200", r_unidad.status_code, 200)
    unidad = r_unidad.json()
    igual("alimento no se suma entre unidades incompatibles",
          unidad["indicadores"]["alimento_real_acumulado_kg"], None)
    igual("motivo de alimento por unidad",
          unidad["pendientes"].get("alimento_real_acumulado_kg"),
          "UNIDAD_ALIMENTO_INCOMPATIBLE")
    igual("FCA nunca se estima sin alimento convertible",
          (unidad["indicadores"]["fca"], unidad["indicadores"]["fca_motivo"]),
          (None, "UNIDAD_ALIMENTO_INCOMPATIBLE"))
    unidades_alimento = [fila["unidad"] for fila in unidad["alimentacion_real_por_unidad"]]
    check("los totales de alimento no colapsan unidades distintas",
          len(unidades_alimento) == 2 and "kg" in unidades_alimento, str(unidades_alimento))
    check("el registro no convertible no recibe equivalencia en kg",
          any(fila["cantidad_kg"] is None for fila in unidad["alimentacion_real"]))

    # ---------------- N/D nunca es 0 ----------------
    r_vacio = get(admin, f"/api/v1/analisis/lotes/{lote_vacio}")
    igual("lote sin datos no rompe el análisis", r_vacio.status_code, 200)
    vacio = r_vacio.json()["indicadores"]
    check("lote sin datos deja los indicadores en null",
          all(vacio[clave] is None for clave in
              ("peso_promedio_g", "biomasa_actual_kg", "biomasa_inicial_kg", "ganancia_peso_g", "fca")),
          str({k: vacio[k] for k in ("peso_promedio_g", "biomasa_actual_kg", "fca")}))
    igual("lote sin biometría explica el motivo",
          r_vacio.json()["pendientes"].get("biomasa_actual_kg"), "SIN_BIOMETRIA")

    r_sin_lote = get(admin, "/api/v1/analisis/estanques", solo_activos="false", estanque_id=est_sin_lote)
    igual("estanque sin lote no genera error", r_sin_lote.status_code, 200)
    filas_sin_lote = r_sin_lote.json()["estanques"]
    igual("estanque sin lote aparece una vez", len(filas_sin_lote), 1)
    fila = filas_sin_lote[0]
    igual("estanque sin lote no inventa lote", fila["lote_id"], None)
    check("estanque sin lote no reporta ceros",
          all(fila[clave] is None for clave in
              ("biomasa_actual_kg", "supervivencia_porcentaje", "fca", "peso_promedio_g")),
          str({k: fila[k] for k in ("biomasa_actual_kg", "supervivencia_porcentaje", "fca")}))

    produccion = get(admin, "/api/v1/dashboard/produccion").json()
    surv_granja = produccion["supervivencia_pct_activos"]
    check("dashboard no publica supervivencia 0 sin siembra",
          surv_granja is None or Decimal(str(surv_granja)) > 0
          or produccion["poblacion_estimada_activos"] == 0,
          f"supervivencia={surv_granja} poblacion={produccion['poblacion_estimada_activos']}")
    check("supervivencia N/D viene con motivo",
          surv_granja is not None or bool(produccion["supervivencia_pct_activos_motivo"]))

    # ---------------- Un mismo indicador en tres endpoints ----------------
    comp = get(operario, "/api/v1/analisis/estanques", solo_activos="false", estanque_id=est_a,
               incluir_historial="true")
    igual("comparativo accesible en lectura", comp.status_code, 200)
    comparativo = comp.json()
    fila_a = comparativo["estanques"][0]
    igual("comparativo repite la población del análisis", fila_a["poblacion_estimada"], 930)
    igual("comparativo repite la biomasa", dec(fila_a["biomasa_actual_kg"]), Decimal("27.900"))
    igual("comparativo repite la supervivencia", dec(fila_a["supervivencia_porcentaje"]), Decimal("98.00"))
    igual("comparativo repite el FCA", dec(fila_a["eficiencia"]["fca"]), Decimal("0.2961"))
    igual("historial del estanque trae su ciclo", [c["lote_id"] for c in comparativo["ciclos"]], [lote])
    igual("FCA de granja sigue sin definirse", comparativo["resumen"]["fca"], None)

    reporte = get(admin, "/api/v1/reportes/produccion", lote_id=lote)
    igual("reporte de producción responde 200", reporte.status_code, 200)
    fila_rep = reporte.json()["filas"][0]
    igual("reporte repite población, supervivencia y peso",
          (fila_rep["poblacion_estimada"], dec(fila_rep["supervivencia_porcentaje"]), dec(fila_rep["peso_promedio_g"])),
          (930, Decimal("98.00"), Decimal("30.000")))

    sin_historial = get(admin, "/api/v1/analisis/estanques", solo_activos="true")
    igual("comparativo de granja no arrastra historial", sin_historial.json()["ciclos"], [])

    # ---------------- El análisis no escribe ----------------
    igual("el análisis no crea alarmas automáticas",
          contar("SELECT COUNT(*) FROM biofloc.alarmas WHERE lote_id = ANY(%s)",
                 ([lote, lote_vacio, lote_unidad],)), 0)
    igual("la alimentación no genera movimientos de inventario",
          contar("SELECT COUNT(*) FROM biofloc.movimientos_inventario WHERE producto_id = ANY(%s)",
                 ([amb.producto_kg, amb.producto_g, amb.producto_l],)), 0)

    # ---------------- RBAC aplicado por el backend ----------------
    estanque_nuevo = {
        "codigo": f"{PREF} E18X-{stamp}", "nombre": f"{PREF} E18X-{stamp}",
        "diametro": 8, "profundidad": 1.2, "estado_id": amb.estado_estanque, "activo": True,
    }
    igual("operario no crea estanques",
          requests.post(f"{BASE}/api/v1/estanques/", headers=base.H(operario), json=estanque_nuevo, timeout=20).status_code, 403)
    igual("técnico no crea estanques",
          requests.post(f"{BASE}/api/v1/estanques/", headers=base.H(tecnico), json=estanque_nuevo, timeout=20).status_code, 403)
    igual("técnico sí edita estanques",
          requests.put(f"{BASE}/api/v1/estanques/{est_unidad}", headers=base.H(tecnico),
                       json={"nombre": f"{PREF} E18D editado"}, timeout=20).status_code, 200)
    igual("operario no edita estanques",
          requests.put(f"{BASE}/api/v1/estanques/{est_unidad}", headers=base.H(operario),
                       json={"nombre": f"{PREF} E18D operario"}, timeout=20).status_code, 403)
    igual("operario no crea lotes",
          requests.post(f"{BASE}/api/v1/lotes/", headers=base.H(operario), json={
              "codigo": f"{PREF} L18X-{stamp}", "estanque_id": est_sin_lote, "especie_id": amb.especie_id,
              "etapa_productiva_id": amb.etapa_id, "estado_id": amb.estado_lote,
              "fecha_siembra": hoy.isoformat(), "cantidad_sembrada": 10, "observaciones": PREF,
          }, timeout=20).status_code, 403)
    igual("operario no registra biometrías",
          requests.post(f"{BASE}/api/v1/biometrias/", headers=base.H(operario), json={
              "lote_id": lote_unidad, "fecha_hora": ahora.isoformat(),
              "cantidad_muestra": 5, "peso_total_muestra_g": 50, "observaciones": PREF,
          }, timeout=20).status_code, 403)
    mort_operario = requests.post(f"{BASE}/api/v1/mortalidades/", headers=base.H(operario), json={
        "lote_id": lote_unidad, "fecha_hora": ahora.isoformat(),
        "cantidad": 1, "causa": PREF, "observaciones": PREF,
    }, timeout=20)
    igual("operario sí registra mortalidades", mort_operario.status_code, 201)
    if mort_operario.status_code == 201:
        base.IDS["mortalidades"].append(mort_operario.json()["id"])
    igual("operario lee el análisis", get(operario, f"/api/v1/analisis/lotes/{lote}").status_code, 200)

    # ---------------- Errores limpios ----------------
    sin_token = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote}", timeout=20)
    igual("sin credenciales 403", sin_token.status_code, 403)
    token_malo = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote}",
                              headers={"Authorization": "Bearer token-invalido"}, timeout=20)
    igual("token inválido 401", token_malo.status_code, 401)
    no_existe = get(admin, "/api/v1/analisis/lotes/999999999")
    igual("lote inexistente 404", no_existe.status_code, 404)
    duplicado = requests.post(f"{BASE}/api/v1/estanques/", headers=base.H(admin), json={
        "codigo": cod_a, "nombre": f"{PREF} duplicado", "diametro": 8,
        "profundidad": 1.2, "estado_id": amb.estado_estanque, "activo": True,
    }, timeout=20)
    igual("código de estanque duplicado 409", duplicado.status_code, 409)
    invalido = requests.post(f"{BASE}/api/v1/biometrias/", headers=base.H(admin), json={
        "lote_id": lote, "fecha_hora": ahora.isoformat(),
        "cantidad_muestra": 0, "peso_total_muestra_g": 10, "observaciones": PREF,
    }, timeout=20)
    igual("muestra inválida 422", invalido.status_code, 422)
    rango_invertido = get(admin, f"/api/v1/analisis/lotes/{lote}",
                          fecha_desde=hoy.isoformat(), fecha_hasta=(hoy - timedelta(days=5)).isoformat())
    igual("rango de fechas invertido 422", rango_invertido.status_code, 422)
    check("ningún error filtra SQL ni trazas",
          all(detalle_limpio(resp) for resp in
              (sin_token, token_malo, no_existe, duplicado, invalido, rango_invertido)))

    leftover = cleanup()
    igual("LEFTOVER", leftover, 0)
    ok = sum(1 for _, bien in RESULTADOS if bien)
    print(f"\nRESULT {ok}/{len(RESULTADOS)} OK")
    return 0 if ok == len(RESULTADOS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
