#!/usr/bin/env python3
"""FASE 16.15 — motor analítico avanzado y series históricas.

Verifica con datos deterministas:
  · población as-of (siembra − mortalidades − cosechas hasta la fecha);
  · biomasa histórica y ganancia de biomasa por biometría;
  · supervivencia y mortalidad históricas;
  · alimentación en kg, g y unidades no convertibles, con acumulado;
  · FCA histórico punto por punto (nunca el FCA final arrastrado);
  · referencia de producción resuelta por la semana de cada punto;
  · comparación real vs objetivo con diferencia absoluta y porcentual;
  · estadística descriptiva con n = 0, n = 1 y n > 1;
  · filtros fecha_desde / fecha_hasta y rango invertido;
  · comparativo por estanque y resumen de granja.

Usa una especie propia de prueba para que ninguna referencia sembrada
interfiera con los valores esperados. Prefijo [TEST_F16_15]; borra todo.
"""
from __future__ import annotations

import io
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import psycopg2
import requests

from env_tests import ADMIN_USER, ADMIN_PASS, OPERARIO_USER, OPERARIO_PASS, DB_CONF

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_F16_15]"
R: list[tuple[str, bool, str]] = []
IDS: dict[str, list[int]] = {
    "mediciones_agua": [],
    "mediciones_biofloc": [],
    "alimentaciones": [],
    "biometrias": [],
    "mortalidades": [],
    "cosechas": [],
    "lotes": [],
    "estanques": [],
    "productos": [],
    "referencias_produccion": [],
    "referencias_agua": [],
    "parametros_agua": [],
    "especies": [],
}


def check(name: str, ok: bool, detail: str = "") -> None:
    R.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" -> {detail}" if detail else ""))


def eq(name: str, obtenido, esperado) -> None:
    check(name, obtenido == esperado, f"obtenido={obtenido!r} esperado={esperado!r}")


def dec(valor) -> Decimal | None:
    return None if valor is None else Decimal(str(valor))


def login(correo: str, password: str) -> str:
    r = requests.post(
        f"{BASE}/api/v1/auth/login", json={"correo": correo, "password": password}, timeout=20
    )
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def db():
    return psycopg2.connect(**DB_CONF)


def cleanup() -> None:
    conn = db()
    cur = conn.cursor()
    for tabla in [
        "mediciones_agua",
        "mediciones_biofloc",
        "alimentaciones",
        "biometrias",
        "mortalidades",
        "cosechas",
        "lotes",
        "estanques",
        "productos",
        "referencias_produccion",
        "referencias_agua",
        "parametros_agua",
        "especies",
    ]:
        ids = IDS[tabla]
        if not ids:
            continue
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla=%s AND registro_id = ANY(%s)", (tabla, ids))
        cur.execute(f"DELETE FROM biofloc.{tabla} WHERE id = ANY(%s)", (ids,))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    conn.commit()
    cur.close()
    conn.close()


def leftover() -> int:
    conn = db()
    cur = conn.cursor()
    like = f"%{PREF}%"
    total = 0
    for sql, args in [
        ("SELECT count(*) FROM biofloc.lotes WHERE observaciones LIKE %s OR codigo LIKE %s", (like, like)),
        ("SELECT count(*) FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s", (like, like)),
        ("SELECT count(*) FROM biofloc.especies WHERE nombre_comun LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.parametros_agua WHERE nombre LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.referencias_produccion WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.referencias_agua WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.productos WHERE nombre LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.biometrias WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.mortalidades WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.cosechas WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.alimentaciones WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.mediciones_agua WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.mediciones_biofloc WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (like,)),
    ]:
        cur.execute(sql, args)
        total += int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return total


class Ambiente:
    """Catálogos temporales necesarios para que los valores sean deterministas."""

    def __init__(self, stamp: str) -> None:
        conn = db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO biofloc.especies (nombre_comun, nombre_cientifico, activo) "
            "VALUES (%s, %s, TRUE) RETURNING id",
            (f"{PREF} especie {stamp}", "Testus analyticus"),
        )
        self.especie_id = cur.fetchone()[0]
        IDS["especies"].append(self.especie_id)

        cur.execute("SELECT id FROM biofloc.etapas_productivas ORDER BY orden LIMIT 1")
        self.etapa_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM biofloc.estados_estanque WHERE nombre='DISPONIBLE' LIMIT 1")
        self.estado_estanque = cur.fetchone()[0]
        cur.execute("SELECT id FROM biofloc.estados_lote WHERE nombre='ACTIVO' LIMIT 1")
        self.estado_lote = cur.fetchone()[0]

        # Referencias de producción por semana: 1, 2 y 3-4.
        for desde, hasta, peso, tasa in [(1, 1, "8.00", "5.000"), (2, 2, "18.00", "4.000"), (3, 4, "28.00", "3.000")]:
            cur.execute(
                """
                INSERT INTO biofloc.referencias_produccion
                    (especie_id, etapa_productiva_id, semana_desde, semana_hasta,
                     peso_esperado_g, tasa_alimentacion_pct, observaciones, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id
                """,
                (self.especie_id, self.etapa_id, desde, hasta, peso, tasa, PREF),
            )
            IDS["referencias_produccion"].append(cur.fetchone()[0])

        # Dos parámetros de agua propios: uno con referencia y otro sin.
        cur.execute(
            "INSERT INTO biofloc.parametros_agua (nombre, unidad, activo) VALUES (%s, %s, TRUE) RETURNING id",
            (f"{PREF} OD {stamp}", "mg/L"),
        )
        self.param_con_ref = cur.fetchone()[0]
        IDS["parametros_agua"].append(self.param_con_ref)
        cur.execute(
            "INSERT INTO biofloc.parametros_agua (nombre, unidad, activo) VALUES (%s, %s, TRUE) RETURNING id",
            (f"{PREF} Temp {stamp}", "°C"),
        )
        self.param_sin_ref = cur.fetchone()[0]
        IDS["parametros_agua"].append(self.param_sin_ref)

        cur.execute(
            """
            INSERT INTO biofloc.referencias_agua
                (especie_id, etapa_productiva_id, parametro_id, valor_minimo, valor_maximo, observaciones, activo)
            VALUES (%s, %s, %s, 5.0000, 8.0000, %s, TRUE) RETURNING id
            """,
            (self.especie_id, self.etapa_id, self.param_con_ref, PREF),
        )
        IDS["referencias_agua"].append(cur.fetchone()[0])

        # Productos de alimento: kg, g y una unidad no convertible.
        cur.execute("SELECT id FROM biofloc.categorias_inventario ORDER BY id LIMIT 1")
        categoria = cur.fetchone()[0]
        self.producto_kg = self._producto(cur, categoria, "kg", f"PKG-{stamp}", "alimento kg")
        self.producto_g = self._producto(cur, categoria, "g", f"PG-{stamp}", "alimento g")
        self.producto_l = self._producto(cur, categoria, None, f"PL-{stamp}", "insumo no convertible")

        conn.commit()
        cur.close()
        conn.close()

    def _producto(self, cur, categoria: int, simbolo: str | None, codigo: str, etiqueta: str) -> int | None:
        if simbolo is None:
            cur.execute("SELECT id FROM biofloc.unidades WHERE simbolo NOT IN ('kg','g') ORDER BY id LIMIT 1")
        else:
            cur.execute("SELECT id FROM biofloc.unidades WHERE simbolo=%s LIMIT 1", (simbolo,))
        fila = cur.fetchone()
        if not fila:
            return None
        cur.execute(
            """
            INSERT INTO biofloc.productos (codigo, nombre, categoria_id, unidad_id, stock_minimo, activo)
            VALUES (%s, %s, %s, %s, 0, TRUE) RETURNING id
            """,
            (codigo, f"{PREF} {etiqueta}", categoria, fila[0]),
        )
        ident = cur.fetchone()[0]
        IDS["productos"].append(ident)
        return ident


def crear_estanque(admin: str, codigo: str, estado_id: int) -> int | None:
    r = requests.post(
        f"{BASE}/api/v1/estanques/",
        headers=H(admin),
        json={
            "codigo": codigo,
            "nombre": f"{PREF} {codigo}",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": estado_id,
            "activo": True,
        },
        timeout=20,
    )
    if r.status_code != 201:
        check(f"POST estanque {codigo}", False, str(r.status_code))
        return None
    ident = r.json()["id"]
    IDS["estanques"].append(ident)
    return ident


def crear_lote(admin: str, amb: Ambiente, estanque_id: int, codigo: str, siembra: date, cantidad: int, peso_inicial) -> int | None:
    payload = {
        "codigo": codigo,
        "estanque_id": estanque_id,
        "especie_id": amb.especie_id,
        "etapa_productiva_id": amb.etapa_id,
        "estado_id": amb.estado_lote,
        "fecha_siembra": siembra.isoformat(),
        "cantidad_sembrada": cantidad,
        "observaciones": PREF,
    }
    if peso_inicial is not None:
        payload["peso_inicial_promedio_g"] = peso_inicial
    r = requests.post(f"{BASE}/api/v1/lotes/", headers=H(admin), json=payload, timeout=20)
    if r.status_code != 201:
        check(f"POST lote {codigo}", False, f"{r.status_code} {r.text[:200]}")
        return None
    ident = r.json()["id"]
    IDS["lotes"].append(ident)
    return ident


def post(admin: str, ruta: str, tabla: str, payload: dict) -> int | None:
    r = requests.post(f"{BASE}{ruta}", headers=H(admin), json=payload, timeout=20)
    if r.status_code != 201:
        check(f"POST {ruta}", False, f"{r.status_code} {r.text[:200]}")
        return None
    ident = r.json()["id"]
    IDS[tabla].append(ident)
    return ident


def analisis(token: str, lote_id: int, **params) -> requests.Response:
    return requests.get(
        f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=H(token), params=params, timeout=30
    )


def main() -> int:
    admin = login(ADMIN_USER, ADMIN_PASS)
    operario = login(OPERARIO_USER, OPERARIO_PASS)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    amb = Ambiente(stamp)
    now = datetime.now(timezone.utc)
    hoy = date.today()

    # ================= Lote sin datos =================
    est_vacio = crear_estanque(admin, f"E15V-{stamp}", amb.estado_estanque)
    if est_vacio is None:
        return 1
    lote_vacio = crear_lote(admin, amb, est_vacio, f"L15-VAC-{stamp}", hoy - timedelta(days=10), 500, None)
    if lote_vacio is None:
        cleanup()
        return 1

    r = analisis(operario, lote_vacio)
    check("GET análisis lote sin datos", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        b = r.json()
        eq("vacío: sin serie de biomasa", b["serie_biomasa"], [])
        eq("vacío: sin serie de FCA", b["serie_fca"], [])
        eq("vacío: población con solo el punto de siembra", len(b["serie_poblacion"]), 1)
        punto = b["serie_poblacion"][0]
        eq("vacío: punto de siembra", punto["evento"], "SIEMBRA")
        eq("vacío: población en siembra", punto["poblacion_estimada"], 500)
        eq("vacío: supervivencia en siembra", dec(punto["supervivencia_porcentaje"]), Decimal("100.00"))
        eq("vacío: estadística de peso con n=0", b["estadisticas"]["peso_promedio_g"]["n"], 0)
        eq(
            "vacío: n=0 sin variación",
            b["estadisticas"]["peso_promedio_g"]["variacion_motivo"],
            "SERIE_VACIA",
        )
        check(
            "vacío: n=0 deja todos los descriptivos en null",
            all(
                b["estadisticas"]["peso_promedio_g"][clave] is None
                for clave in ["primero", "ultimo", "promedio", "minimo", "maximo", "mediana"]
            ),
        )
        eq(
            "vacío: n=1 no permite variación",
            b["estadisticas"]["poblacion_estimada"]["variacion_motivo"],
            "SERIE_CON_UN_SOLO_PUNTO",
        )
        eq("vacío: comparación de peso sin real", b["comparaciones"]["peso_g"]["motivo"], "SIN_BIOMETRIA")

    # ================= Lote con historia controlada =================
    # siembra: hoy-21, 2000 peces, 5 g/pez  → biomasa inicial 10.000 kg
    est_full = crear_estanque(admin, f"E15F-{stamp}", amb.estado_estanque)
    if est_full is None:
        cleanup()
        return 1
    lote = crear_lote(admin, amb, est_full, f"L15-FULL-{stamp}", hoy - timedelta(days=21), 2000, 5)
    if lote is None:
        cleanup()
        return 1

    post(admin, "/api/v1/mortalidades/", "mortalidades", {
        "lote_id": lote, "fecha_hora": (now - timedelta(days=20)).isoformat(),
        "cantidad": 10, "observaciones": PREF,
    })
    bio1 = post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote, "fecha_hora": (now - timedelta(days=18)).isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 100, "observaciones": PREF,
    })
    post(admin, "/api/v1/mortalidades/", "mortalidades", {
        "lote_id": lote, "fecha_hora": (now - timedelta(days=15)).isoformat(),
        "cantidad": 20, "observaciones": PREF,
    })
    post(admin, "/api/v1/cosechas/", "cosechas", {
        "lote_id": lote, "fecha_hora": (now - timedelta(days=12)).isoformat(),
        "cantidad_peces": 100, "peso_total_kg": 1.5, "observaciones": PREF,
    })
    bio2 = post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote, "fecha_hora": (now - timedelta(days=10)).isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 200, "observaciones": PREF,
    })
    bio3 = post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote, "fecha_hora": (now - timedelta(days=1)).isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 300, "observaciones": PREF,
    })
    for dias, cantidad in [(19, 2), (11, 3), (2, 5)]:
        post(admin, "/api/v1/alimentaciones/", "alimentaciones", {
            "lote_id": lote, "producto_id": amb.producto_kg,
            "fecha_hora": (now - timedelta(days=dias)).isoformat(),
            "cantidad": cantidad, "observaciones": PREF,
        })
    # Alimento en gramos después de la última biometría: 1500 g = 1.5 kg.
    post(admin, "/api/v1/alimentaciones/", "alimentaciones", {
        "lote_id": lote, "producto_id": amb.producto_g,
        "fecha_hora": now.isoformat(), "cantidad": 1500, "observaciones": PREF,
    })
    for dias, valor, parametro in [
        (8, 6.0, amb.param_con_ref),
        (5, 9.5, amb.param_con_ref),
        (2, 4.0, amb.param_con_ref),
        (2, 27.5, amb.param_sin_ref),
    ]:
        post(admin, "/api/v1/mediciones-agua/", "mediciones_agua", {
            "lote_id": lote, "parametro_id": parametro,
            "fecha_hora": (now - timedelta(days=dias)).isoformat(),
            "valor": valor, "observaciones": PREF,
        })
    for dias, volumen, cn in [(6, 10, 12), (2, 20, None)]:
        payload = {
            "lote_id": lote, "fecha_hora": (now - timedelta(days=dias)).isoformat(),
            "volumen_sedimentable": volumen, "unidad": "mL/L", "observaciones": PREF,
        }
        if cn is not None:
            payload["relacion_cn"] = cn
        post(admin, "/api/v1/mediciones-biofloc/", "mediciones_biofloc", payload)

    r = analisis(admin, lote)
    check("GET análisis lote con historia", r.status_code == 200, str(r.status_code))
    if r.status_code != 200:
        cleanup()
        return 1
    b = r.json()
    ind = b["indicadores"]

    # --- Indicadores puntuales (fórmulas congeladas) ---
    eq("biomasa inicial 2000×5/1000", dec(ind["biomasa_inicial_kg"]), Decimal("10.000"))
    eq("población actual 2000−30−100", ind["poblacion_estimada"], 1870)
    eq("biomasa actual 1870×30/1000", dec(ind["biomasa_actual_kg"]), Decimal("56.100"))
    eq("alimento real 2+3+5 kg + 1500 g", dec(ind["alimento_real_acumulado_kg"]), Decimal("11.500"))
    eq("FCA 11.5/(56.1−10)", dec(ind["fca"]), Decimal("0.2495"))
    eq("semana de cultivo actual", ind["semana_cultivo"], 3)
    eq("supervivencia 1870/2000", dec(ind["supervivencia_porcentaje"]), Decimal("93.50"))
    eq("mortalidad 30/2000", dec(ind["mortalidad_porcentaje"]), Decimal("1.50"))
    eq("ración 56.100×3/100", dec(ind["racion_diaria_recomendada_kg"]), Decimal("1.683"))

    # --- Serie de peso con referencia de su propia semana ---
    bios = b["biometrias"]
    eq("serie de peso con 3 puntos", len(bios), 3)
    eq("pesos promedio de la serie", [dec(p["peso_promedio_g"]) for p in bios],
       [Decimal("10.000"), Decimal("20.000"), Decimal("30.000")])
    eq("semanas de los puntos", [p["semana_cultivo"] for p in bios], [1, 2, 3])
    eq("peso esperado por semana", [dec(p["peso_esperado_g"]) for p in bios],
       [Decimal("8.00"), Decimal("18.00"), Decimal("28.00")])
    eq("diferencia real − esperado", [dec(p["diferencia_peso_g"]) for p in bios],
       [Decimal("2.000"), Decimal("2.000"), Decimal("2.000")])
    eq("diferencia porcentual", [dec(p["diferencia_peso_pct"]) for p in bios],
       [Decimal("25.00"), Decimal("11.11"), Decimal("7.14")])
    eq("referencias por semana resueltas", [f["semana_cultivo"] for f in b["referencias_por_semana"]], [1, 2, 3])
    check(
        "cada semana usa su propia referencia",
        len({f["referencia_id"] for f in b["referencias_por_semana"]}) == 3,
        str([f["referencia_id"] for f in b["referencias_por_semana"]]),
    )
    eq("comparación actual real 30 vs objetivo 28", 
       (dec(b["comparaciones"]["peso_g"]["real"]), dec(b["comparaciones"]["peso_g"]["objetivo"]),
        dec(b["comparaciones"]["peso_g"]["diferencia"]), dec(b["comparaciones"]["peso_g"]["diferencia_porcentaje"])),
       (Decimal("30.000000"), Decimal("28.000000"), Decimal("2.000000"), Decimal("7.14")))

    # --- Población as-of, mortalidad y supervivencia históricas ---
    pobl = b["serie_poblacion"]
    eq("serie de población con 7 eventos", len(pobl), 7)
    eq("eventos en orden",
       [p["evento"] for p in pobl],
       ["SIEMBRA", "MORTALIDAD", "BIOMETRIA", "MORTALIDAD", "COSECHA", "BIOMETRIA", "BIOMETRIA"])
    eq("población as-of por evento",
       [p["poblacion_estimada"] for p in pobl],
       [2000, 1990, 1990, 1970, 1870, 1870, 1870])
    eq("supervivencia as-of",
       [dec(p["supervivencia_porcentaje"]) for p in pobl],
       [Decimal("100.00"), Decimal("99.50"), Decimal("99.50"), Decimal("98.50"),
        Decimal("93.50"), Decimal("93.50"), Decimal("93.50")])
    eq("mortalidad acumulada en la serie de mortalidades",
       [(p["cantidad"], p["acumulada"], dec(p["mortalidad_porcentaje"])) for p in b["mortalidades"]],
       [(10, 10, Decimal("0.50")), (20, 30, Decimal("1.50"))])

    # --- Biomasa histórica con población as-of ---
    biomasa = b["serie_biomasa"]
    eq("serie de biomasa con 3 puntos", len(biomasa), 3)
    eq("población usada en cada punto", [p["poblacion_estimada"] for p in biomasa], [1990, 1870, 1870])
    eq("biomasa por fecha", [dec(p["biomasa_kg"]) for p in biomasa],
       [Decimal("19.900"), Decimal("37.400"), Decimal("56.100")])
    eq("ganancia de biomasa por fecha", [dec(p["ganancia_biomasa_kg"]) for p in biomasa],
       [Decimal("9.900"), Decimal("27.400"), Decimal("46.100")])
    check(
        "biomasa histórica no repite la biomasa actual",
        dec(biomasa[0]["biomasa_kg"]) != dec(ind["biomasa_actual_kg"]),
    )

    # --- Alimentación: unidad original, kg y acumulado ---
    alim = b["alimentacion_real"]
    eq("4 alimentaciones", len(alim), 4)
    eq("unidades originales conservadas", [p["unidad"] for p in alim], ["kg", "kg", "kg", "g"])
    eq("cantidad en kg por registro", [dec(p["cantidad_kg"]) for p in alim],
       [Decimal("2.000"), Decimal("3.000"), Decimal("5.000"), Decimal("1.500")])
    eq("acumulado en kg", [dec(p["acumulado_kg"]) for p in alim],
       [Decimal("2.000"), Decimal("5.000"), Decimal("10.000"), Decimal("11.500")])
    check("producto etiquetado sin consultar catálogo",
          all(p["producto_nombre"].startswith(PREF) and p["producto_codigo"] for p in alim))
    eq("total por unidad sin mezclar",
       sorted((f["unidad"], dec(f["cantidad"])) for f in b["alimentacion_real_por_unidad"]),
       [("g", Decimal("1500.000")), ("kg", Decimal("10.000"))])

    # --- FCA histórico punto por punto ---
    fca = b["serie_fca"]
    eq("serie de FCA con 3 puntos", len(fca), 3)
    eq("alimento acumulado as-of de cada punto",
       [dec(p["alimento_real_acumulado_kg"]) for p in fca],
       [Decimal("2.000"), Decimal("5.000"), Decimal("10.000")])
    eq("FCA histórico calculado por punto", [dec(p["fca"]) for p in fca],
       [Decimal("0.2020"), Decimal("0.1825"), Decimal("0.2169")])
    check("FCA histórico no arrastra el FCA final",
          dec(fca[-1]["fca"]) != dec(ind["fca"]),
          f'ultimo={fca[-1]["fca"]} actual={ind["fca"]}')
    check("todos los puntos de FCA disponibles", all(p["fca_disponible"] for p in fca))

    # --- Estadística descriptiva (n > 1) ---
    est = b["estadisticas"]
    eq("peso: n, promedio, mín, máx, último",
       (est["peso_promedio_g"]["n"], dec(est["peso_promedio_g"]["promedio"]),
        dec(est["peso_promedio_g"]["minimo"]), dec(est["peso_promedio_g"]["maximo"]),
        dec(est["peso_promedio_g"]["ultimo"])),
       (3, Decimal("20.000000"), Decimal("10.000000"), Decimal("30.000000"), Decimal("30.000000")))
    eq("peso: mediana de 10, 20, 30", dec(est["peso_promedio_g"]["mediana"]), Decimal("20.000000"))
    eq("peso: variación 10 → 30", dec(est["peso_promedio_g"]["variacion_porcentual"]), Decimal("200.00"))
    eq("biomasa: variación 19.9 → 56.1", dec(est["biomasa_kg"]["variacion_porcentual"]), Decimal("181.91"))
    eq("volumen sedimentable: variación 10 → 20",
       dec(est["volumen_sedimentable"]["variacion_porcentual"]), Decimal("100.00"))
    eq("relación C:N con un solo dato", est["relacion_cn"]["n"], 1)
    eq("unidad declarada en las estadísticas de biomasa", est["biomasa_kg"]["unidad"], "kg")

    # --- Estadística de agua con y sin referencia ---
    agua_est = {fila["parametro_id"]: fila for fila in est["agua"]}
    con_ref = agua_est.get(amb.param_con_ref)
    sin_ref = agua_est.get(amb.param_sin_ref)
    check("estadísticas de agua por parámetro", con_ref is not None and sin_ref is not None)
    if con_ref:
        eq("agua con referencia: n", con_ref["estadisticas"]["n"], 3)
        eq("agua con referencia: promedio (6+9.5+4)/3",
           dec(con_ref["estadisticas"]["promedio"]), Decimal("6.500000"))
        eq("agua con referencia: mínimo y máximo",
           (dec(con_ref["estadisticas"]["minimo"]), dec(con_ref["estadisticas"]["maximo"])),
           (Decimal("4.000000"), Decimal("9.500000")))
        eq("agua con referencia: 2 de 3 fuera de rango", con_ref["fuera_de_rango_n"], 2)
        eq("agua con referencia: porcentaje fuera",
           dec(con_ref["fuera_de_rango_porcentaje"]), Decimal("66.67"))
        eq("agua con referencia: rango declarado",
           (dec(con_ref["valor_minimo"]), dec(con_ref["valor_maximo"])),
           (Decimal("5.0000"), Decimal("8.0000")))
    if sin_ref:
        eq("agua sin referencia: sin conteo de fuera de rango", sin_ref["fuera_de_rango_n"], None)
        eq("agua sin referencia: marcada sin referencia", sin_ref["con_referencia"], False)
        eq("agua sin referencia: estadísticas presentes", sin_ref["estadisticas"]["n"], 1)

    # --- Filtros de fecha ---
    desde_bio3 = (hoy - timedelta(days=1)).isoformat()
    r = analisis(admin, lote, fecha_desde=desde_bio3)
    check("GET con fecha_desde", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        f = r.json()
        eq("fecha_desde recorta la serie de peso", [p["id"] for p in f["biometrias"]], [bio3])
        eq("fecha_desde no recorta indicadores",
           dec(f["indicadores"]["fca"]), Decimal("0.2495"))
        eq("as-of se mantiene completo tras filtrar",
           dec(f["serie_fca"][0]["alimento_real_acumulado_kg"]), Decimal("10.000"))
        eq("biomasa filtrada conserva su valor as-of",
           dec(f["serie_biomasa"][0]["biomasa_kg"]), Decimal("56.100"))
        eq("estadísticas se recalculan sobre la ventana", f["estadisticas"]["peso_promedio_g"]["n"], 1)
        eq("filtros informados en la respuesta", f["filtros"]["fecha_desde"], desde_bio3)

    hasta_bio1 = (hoy - timedelta(days=18)).isoformat()
    r = analisis(admin, lote, fecha_hasta=hasta_bio1)
    check("GET con fecha_hasta", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        f = r.json()
        eq("fecha_hasta recorta la serie de peso", [p["id"] for p in f["biometrias"]], [bio1])
        eq("mortalidad visible conserva su acumulado real",
           [p["acumulada"] for p in f["mortalidades"]], [10])
        eq("alimento visible conserva su acumulado real",
           [dec(p["acumulado_kg"]) for p in f["alimentacion_real"]], [Decimal("2.000")])

    r = analisis(admin, lote, fecha_desde=hoy.isoformat(), fecha_hasta=(hoy - timedelta(days=5)).isoformat())
    eq("rango invertido rechazado con 422", r.status_code, 422)

    r = analisis(admin, lote, fecha_desde=(hoy + timedelta(days=1)).isoformat())
    if r.status_code == 200:
        f = r.json()
        eq("ventana sin datos deja series vacías",
           (len(f["biometrias"]), len(f["serie_biomasa"]), len(f["serie_fca"])), (0, 0, 0))
        eq("ventana sin datos: estadísticas n=0", f["estadisticas"]["biomasa_kg"]["n"], 0)

    # ================= Alimento no convertible y semana sin referencia =========
    est_l = crear_estanque(admin, f"E15L-{stamp}", amb.estado_estanque)
    if est_l is None:
        cleanup()
        return 1
    lote_l = crear_lote(admin, amb, est_l, f"L15-INC-{stamp}", hoy - timedelta(days=120), 300, 5)
    if lote_l is None:
        cleanup()
        return 1
    post(admin, "/api/v1/biometrias/", "biometrias", {
        "lote_id": lote_l, "fecha_hora": now.isoformat(),
        "cantidad_muestra": 10, "peso_total_muestra_g": 520, "observaciones": PREF,
    })
    if amb.producto_l:
        post(admin, "/api/v1/alimentaciones/", "alimentaciones", {
            "lote_id": lote_l, "producto_id": amb.producto_l,
            "fecha_hora": now.isoformat(), "cantidad": 3, "observaciones": PREF,
        })
    r = analisis(admin, lote_l)
    check("GET análisis con alimento no convertible", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        f = r.json()
        eq("alimento no convertible: total en null", f["indicadores"]["alimento_real_acumulado_kg"], None)
        eq("alimento no convertible: cantidad_kg null", f["alimentacion_real"][0]["cantidad_kg"], None)
        eq("alimento no convertible: acumulado null", f["alimentacion_real"][0]["acumulado_kg"], None)
        eq("alimento no convertible: marcado", f["alimentacion_real"][0]["convertible_a_kg"], False)
        eq("FCA no disponible por unidad", f["indicadores"]["fca_motivo"], "UNIDAD_ALIMENTO_INCOMPATIBLE")
        eq("FCA histórico también sin unidad convertible",
           [p["fca_motivo"] for p in f["serie_fca"]], ["UNIDAD_ALIMENTO_INCOMPATIBLE"])
        eq("semana 18 sin referencia", f["biometrias"][0]["peso_esperado_g"], None)
        eq("comparación sin objetivo", f["comparaciones"]["peso_g"]["motivo"],
           "SIN_REFERENCIA_PRODUCCION_APLICABLE")
        eq("referencia por semana sin coincidencia",
           [fila["motivo"] for fila in f["referencias_por_semana"]],
           ["SIN_REFERENCIA_PRODUCCION_APLICABLE"] * len(f["referencias_por_semana"]))
        eq("peso: una sola medición",
           f["estadisticas"]["peso_promedio_g"]["variacion_motivo"], "SERIE_CON_UN_SOLO_PUNTO")
        eq("biomasa histórica de un punto 300×52/1000",
           dec(f["serie_biomasa"][0]["biomasa_kg"]), Decimal("15.600"))

    # ================= Comparativo por estanque =================
    est_sin_lote = crear_estanque(admin, f"E15S-{stamp}", amb.estado_estanque)
    r = requests.get(f"{BASE}/api/v1/analisis/estanques", headers=H(operario), timeout=60)
    check("GET comparativo de estanques", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        c = r.json()
        filas = {fila["estanque_id"]: fila for fila in c["estanques"]}
        fila = filas.get(est_full)
        check("comparativo incluye el estanque con lote activo", fila is not None)
        if fila:
            eq("comparativo: biomasa del lote activo", dec(fila["biomasa_actual_kg"]), Decimal("56.100"))
            eq("comparativo: FCA del lote activo", dec(fila["fca"]), Decimal("0.2495"))
            eq("comparativo: población y semana",
               (fila["poblacion_estimada"], fila["semana_cultivo"]), (1870, 3))
            eq("comparativo: supervivencia", dec(fila["supervivencia_porcentaje"]), Decimal("93.50"))
            eq("comparativo: agua 2 parámetros, 1 con referencia, 1 fuera de rango",
               (fila["agua_parametros_medidos"], fila["agua_parametros_con_referencia"],
                fila["agua_parametros_fuera_de_rango"]), (2, 1, 1))
        vacio = filas.get(est_sin_lote)
        check("comparativo incluye estanque sin lote", vacio is not None)
        if vacio:
            eq("estanque sin lote: motivo", vacio["sin_lote_activo_motivo"], "SIN_LOTE_ACTIVO")
            eq("estanque sin lote: indicadores en null",
               (vacio["biomasa_actual_kg"], vacio["poblacion_estimada"], vacio["fca"]), (None, None, None))
        eq("resumen de granja: FCA sin regla de agregación",
           (c["resumen"]["fca"], c["resumen"]["fca_motivo"]), (None, "SIN_REGLA_DE_AGREGACION_DE_FCA"))
        check("resumen de granja: totales incluyen los lotes de prueba",
              c["resumen"]["peces_sembrados"] >= 2800 and c["resumen"]["poblacion_estimada"] >= 2000,
              str(c["resumen"]["peces_sembrados"]))
        check("resumen de granja: supervivencia agregada presente",
              c["resumen"]["supervivencia_porcentaje"] is not None)

    cleanup()
    left = leftover()
    check("leftover = 0", left == 0, str(left))

    fallidos = [nombre for nombre, ok, _ in R if not ok]
    print(f"\nRESULT {len(R) - len(fallidos)}/{len(R)} OK")
    if fallidos:
        print("FAILED:", "; ".join(fallidos))
        return 1
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    except Exception as exc:  # noqa: BLE001
        print("EXC", type(exc).__name__, str(exc)[:400])
        try:
            cleanup()
        except Exception:  # noqa: BLE001
            pass
        codigo = 1
    raise SystemExit(codigo)
