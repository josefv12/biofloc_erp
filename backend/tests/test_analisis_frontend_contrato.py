#!/usr/bin/env python3
"""FASE 16.14 — contrato del análisis tal como lo consume el panel visual.

No repite la verificación de fórmulas (eso es test_analisis_fase16_13.py). Aquí
se comprueba lo que el frontend necesita para no dibujar basura: que existan
todos los campos que lee el panel, que ningún número llegue como NaN/Infinity,
que cada indicador nulo venga con su motivo, y que las series tengan la forma
esperada en los escenarios de datos vacíos, de un solo punto y de varios puntos.

Prefijo [TEST_F16_14]. Elimina todo lo que crea.
"""
from __future__ import annotations

import io
import math
import sys
from datetime import date, datetime, timedelta, timezone

import psycopg2
import requests

from env_tests import ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS, DB_CONF

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_F16_14]"
R: list[tuple[str, bool, str]] = []
IDS: dict[str, list[int]] = {
    "estanques": [],
    "lotes": [],
    "biometrias": [],
    "mortalidades": [],
    "cosechas": [],
    "alimentaciones": [],
    "mediciones_agua": [],
    "mediciones_biofloc": [],
    "referencias_produccion": [],
    "referencias_agua": [],
    "productos": [],
}

# Indicadores que el panel lee por nombre. Si el backend renombra uno, el panel
# mostraría N/D en silencio; por eso se verifica la presencia de cada clave.
CLAVES_INDICADORES = [
    "peces_sembrados",
    "mortalidad_acumulada",
    "peces_cosechados",
    "poblacion_estimada",
    "supervivencia_porcentaje",
    "mortalidad_porcentaje",
    "ultima_biometria_id",
    "peso_promedio_g",
    "fecha_ultima_biometria",
    "peso_inicial_g",
    "dias_cultivo",
    "semana_cultivo",
    "ganancia_peso_g",
    "ganancia_diaria_g",
    "biomasa_inicial_kg",
    "biomasa_actual_kg",
    "alimento_real_acumulado_kg",
    "fca",
    "fca_disponible",
    "fca_motivo",
    "sgr_pct_dia",
    "densidad_kg_m3",
    "volumen_util_m3",
    "racion_diaria_recomendada_kg",
    "numero_raciones_diarias",
]

CLAVES_RAIZ = [
    "lote",
    "estanque",
    "especie",
    "etapa",
    "definiciones",
    "filtros",
    "indicadores",
    "pendientes",
    "referencia_produccion",
    "referencias_por_semana",
    "comparaciones",
    "evaluaciones",
    "recomendaciones",
    "productividad",
    "eficiencia",
    "finanzas",
    "estadisticas",
    "biometrias",
    "mortalidades",
    "serie_poblacion",
    "serie_biomasa",
    "serie_crecimiento",
    "serie_fca",
    "agua",
    "agua_serie",
    "biofloc",
    "biofloc_serie",
    "alimentacion_real_por_unidad",
    "alimentacion_real",
]

CLAVES_DEFINICIONES = [
    "zona_horaria",
    "dias_cultivo",
    "semana_cultivo",
    "unidad_masa_productiva",
    "biomasa_inicial_kg",
    "biomasa_actual_kg",
    "ganancia_peso_g",
    "ganancia_diaria_g",
    "alimento_real_acumulado_kg",
    "fca",
    "referencia_produccion",
    "racion_diaria_recomendada_kg",
    "numero_raciones_diarias",
    "poblacion_as_of",
    "serie_biomasa",
    "serie_fca",
    "alimento_convertible_kg",
    "estadisticas",
    "mediana",
    "variacion_porcentual",
    "comparacion_real_objetivo",
    "filtros_fecha",
    "estado_analitico",
    "cumplimiento_rango",
    "recomendaciones",
]

# Indicadores que, si son nulos, deben traer razón técnica (fca la trae aparte).
NULOS_CON_MOTIVO = [
    "biomasa_inicial_kg",
    "biomasa_actual_kg",
    "ganancia_peso_g",
    "ganancia_diaria_g",
    "alimento_real_acumulado_kg",
    "racion_diaria_recomendada_kg",
    "numero_raciones_diarias",
    "sgr_pct_dia",
    "densidad_kg_m3",
]


def check(name: str, ok: bool, detail: str = "") -> None:
    R.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" {detail}" if detail else ""))


def login(correo: str, password: str) -> str:
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"correo": correo, "password": password}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def db():
    return psycopg2.connect(**DB_CONF)


def numero_finito(valor) -> bool:
    """True si el valor es null o un número finito (nunca NaN ni Infinity)."""
    if valor is None:
        return True
    try:
        convertido = float(valor)
    except (TypeError, ValueError):
        return False
    return math.isfinite(convertido)


def revisar_invariantes(nombre: str, body: dict) -> None:
    faltantes = [clave for clave in CLAVES_RAIZ if clave not in body]
    check(f"{nombre}: estructura raíz completa", not faltantes, str(faltantes))

    ind = body.get("indicadores", {})
    faltantes_ind = [clave for clave in CLAVES_INDICADORES if clave not in ind]
    check(f"{nombre}: indicadores completos", not faltantes_ind, str(faltantes_ind))

    faltantes_def = [clave for clave in CLAVES_DEFINICIONES if clave not in body.get("definiciones", {})]
    check(f"{nombre}: definiciones completas", not faltantes_def, str(faltantes_def))

    no_finitos = [
        clave
        for clave, valor in ind.items()
        if clave not in {
            "fca_disponible",
            "fca_motivo",
            "fecha_ultima_biometria",
            "unidad_talla",
            "raciones_diarias_texto",
            "racion_basada_en_peso",
        }
        and not numero_finito(valor)
    ]
    check(f"{nombre}: sin NaN ni Infinity en indicadores", not no_finitos, str(no_finitos))

    sin_motivo = [
        clave
        for clave in NULOS_CON_MOTIVO
        if ind.get(clave) is None and clave not in body.get("pendientes", {})
    ]
    check(f"{nombre}: cada indicador nulo trae motivo", not sin_motivo, str(sin_motivo))

    check(
        f"{nombre}: fca coherente con fca_disponible y motivo",
        (ind.get("fca") is not None) == bool(ind.get("fca_disponible"))
        and (ind.get("fca_motivo") is None) == bool(ind.get("fca_disponible")),
        f'fca={ind.get("fca")} disp={ind.get("fca_disponible")} motivo={ind.get("fca_motivo")}',
    )
    productividad = body.get("productividad", {})
    eficiencia = body.get("eficiencia", {})
    finanzas = body.get("finanzas", {})
    check(
        f"{nombre}: bloques productividad/eficiencia/finanzas",
        all(
            clave in productividad
            for clave in ("biomasa_actual_kg", "ganancia_biomasa_kg", "peso_cosechado_kg")
        )
        and all(clave in eficiencia for clave in ("fca", "fca_disponible", "costo_por_kg_motivo"))
        and all(
            clave in finanzas
            for clave in ("ingresos_lote", "gastos_directos_lote", "costos_completos")
        ),
    )
    check(
        f"{nombre}: no inventa rentabilidad con costos incompletos",
        bool(finanzas.get("costos_completos"))
        or (
            finanzas.get("utilidad") is None
            and finanzas.get("margen_porcentaje") is None
            and eficiencia.get("costo_por_kg") is None
        ),
    )

    # Series: orden ascendente y valores graficables.
    bios = body.get("biometrias", [])
    fechas_bio = [fila["fecha_hora"] for fila in bios]
    check(f"{nombre}: biometrías ordenadas", fechas_bio == sorted(fechas_bio), str(fechas_bio))
    check(
        f"{nombre}: peso promedio graficable en toda la serie",
        all(numero_finito(fila["peso_promedio_g"]) and fila["peso_promedio_g"] is not None for fila in bios),
        str([fila["peso_promedio_g"] for fila in bios]),
    )
    check(
        f"{nombre}: serie de talla expuesta (sin conversión)",
        all("talla_promedio" in fila and "unidad_talla" in fila for fila in bios),
        str(list(bios[0].keys()) if bios else []),
    )
    check(
        f"{nombre}: estadísticas incluyen talla_promedio",
        "talla_promedio" in (body.get("estadisticas") or {}),
    )

    morts = body.get("mortalidades", [])
    acumuladas = [fila["acumulada"] for fila in morts]
    check(f"{nombre}: mortalidad acumulada no decrece", acumuladas == sorted(acumuladas), str(acumuladas))

    serie_agua = body.get("agua_serie", [])
    check(
        f"{nombre}: agua graficable con unidad",
        all(
            numero_finito(fila["valor"]) and fila["valor"] is not None and isinstance(fila["unidad"], str)
            for fila in serie_agua
        ),
        str(len(serie_agua)),
    )
    check(
        f"{nombre}: sin rango ⇒ estado indeterminado",
        all(
            (fila["fuera_de_rango"] is None)
            == (fila["valor_minimo"] is None and fila["valor_maximo"] is None)
            for fila in serie_agua
        ),
        str([(fila["valor_minimo"], fila["valor_maximo"], fila["fuera_de_rango"]) for fila in serie_agua]),
    )

    serie_bio = body.get("biofloc_serie", [])
    ultima_bio = body.get("biofloc")
    check(
        f"{nombre}: última biofloc = último punto de la serie",
        (ultima_bio is None and not serie_bio)
        or (ultima_bio is not None and serie_bio and ultima_bio["id"] == serie_bio[-1]["id"]),
        f'ultima={None if ultima_bio is None else ultima_bio["id"]} n={len(serie_bio)}',
    )

    unidades = [fila["unidad"] for fila in body.get("alimentacion_real_por_unidad", [])]
    check(f"{nombre}: alimento agrupado sin repetir unidad", len(unidades) == len(set(unidades)), str(unidades))

    estados = {"NORMAL", "ALERTA", "CRITICO", "SIN_REFERENCIA", "SIN_DATOS", None}
    cumplimientos = {"DENTRO_RANGO", "FUERA_RANGO", "NO_EVALUABLE"}
    claves_numericas = {
        "real",
        "objetivo",
        "minimo",
        "maximo",
        "diferencia_objetivo",
        "diferencia_objetivo_porcentaje",
        "desviacion_rango",
        "desviacion_rango_porcentaje",
    }
    evaluaciones = body.get("evaluaciones", [])
    check(
        f"{nombre}: evaluaciones con contrato y estados válidos",
        bool(evaluaciones)
        and all(
            {
                "indicador",
                "etiqueta",
                "estado_analitico",
                "cumplimiento_rango",
                "explicacion",
            }.issubset(fila)
            and fila["estado_analitico"] in estados
            and fila["cumplimiento_rango"] in cumplimientos
            for fila in evaluaciones
        ),
        str([(fila.get("indicador"), fila.get("estado_analitico")) for fila in evaluaciones]),
    )
    check(
        f"{nombre}: evaluaciones sin NaN ni Infinity",
        all(
            numero_finito(fila.get(clave))
            for fila in evaluaciones
            for clave in claves_numericas
        ),
    )
    check(
        f"{nombre}: recomendaciones trazables",
        all(
            {"indicador", "cumplimiento_rango", "motivo", "recomendacion"}.issubset(fila)
            and fila["cumplimiento_rango"] == "FUERA_RANGO"
            for fila in body.get("recomendaciones", [])
        ),
    )


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
        ("SELECT count(*) FROM biofloc.referencias_produccion WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.referencias_agua WHERE observaciones LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.productos WHERE nombre LIKE %s", (like,)),
        ("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (like,)),
    ]:
        cur.execute(sql, args)
        total += int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return total


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


def main() -> int:
    admin = login(ADMIN_USER, ADMIN_PASS)
    tecnico = login(TECNICO_USER, TECNICO_PASS)

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.estados_estanque WHERE nombre='DISPONIBLE' LIMIT 1")
    est_estado = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.estados_lote WHERE nombre='ACTIVO' LIMIT 1")
    lote_estado = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.especies ORDER BY id LIMIT 1")
    especie_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM biofloc.etapas_productivas ORDER BY orden LIMIT 1")
    etapa_id = cur.fetchone()[0]
    cur.execute(
        """
        SELECT p.id FROM biofloc.productos p
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE u.simbolo IN ('kg','g') ORDER BY p.id LIMIT 1
        """
    )
    fila = cur.fetchone()
    producto_masa = fila[0] if fila else None
    cur.execute(
        """
        SELECT p.id FROM biofloc.productos p
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE u.simbolo NOT IN ('kg','g') ORDER BY p.id LIMIT 1
        """
    )
    fila = cur.fetchone()
    producto_no_masa = fila[0] if fila else None
    cur.execute(
        """
        SELECT pa.id FROM biofloc.parametros_agua pa
        WHERE NOT EXISTS (
            SELECT 1 FROM biofloc.referencias_agua r
            WHERE r.especie_id=%s AND r.etapa_productiva_id=%s AND r.parametro_id=pa.id
        )
        ORDER BY pa.id LIMIT 2
        """,
        (especie_id, etapa_id),
    )
    libres = [row[0] for row in cur.fetchall()]
    param_con_ref = libres[0] if libres else None
    param_sin_ref = libres[1] if len(libres) > 1 else None

    if param_con_ref:
        cur.execute(
            """
            INSERT INTO biofloc.referencias_agua
                (especie_id, etapa_productiva_id, parametro_id, valor_minimo, valor_maximo, observaciones, activo)
            VALUES (%s, %s, %s, 5.0000, 8.0000, %s, TRUE) RETURNING id
            """,
            (especie_id, etapa_id, param_con_ref, PREF),
        )
        IDS["referencias_agua"].append(cur.fetchone()[0])

    cur.execute(
        """
        INSERT INTO biofloc.referencias_produccion
            (especie_id, etapa_productiva_id, semana_desde, semana_hasta, peso_esperado_g, tasa_alimentacion_pct, observaciones, activo)
        VALUES (%s, %s, 2, 3, 30.00, 3.500, %s, TRUE)
        ON CONFLICT (especie_id, etapa_productiva_id, semana_desde, semana_hasta) DO NOTHING
        RETURNING id
        """,
        (especie_id, etapa_id, PREF),
    )
    fila = cur.fetchone()
    if fila:
        IDS["referencias_produccion"].append(fila[0])
    conn.commit()
    cur.close()
    conn.close()

    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    now = datetime.now(timezone.utc)
    siembra_media = (date.today() - timedelta(days=14)).isoformat()

    # --- Escenario A: lote sin ningún dato -------------------------------
    est_a = crear_estanque(admin, f"E14A-{stamp}", est_estado)
    if est_a is None:
        return 1
    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"L14-VAC-{stamp}",
            "estanque_id": est_a,
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "estado_id": lote_estado,
            "fecha_siembra": siembra_media,
            "cantidad_sembrada": 800,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST lote sin datos", r.status_code == 201, str(r.status_code))
    if r.status_code != 201:
        cleanup()
        return 1
    lote_vacio = r.json()["id"]
    IDS["lotes"].append(lote_vacio)

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_vacio}", headers=H(tecnico), timeout=20)
    check("GET análisis lote sin datos", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        body = r.json()
        revisar_invariantes("sin datos", body)
        check(
            "sin datos: todas las series vacías",
            body["biometrias"] == []
            and body["mortalidades"] == []
            and body["agua"] == []
            and body["agua_serie"] == []
            and body["biofloc_serie"] == []
            and body["biofloc"] is None
            and body["alimentacion_real"] == []
            and body["alimentacion_real_por_unidad"] == [],
        )
        check("sin datos: FCA no disponible con motivo", body["indicadores"]["fca_motivo"] is not None)

    # --- Escenario B: lote con historia (varios puntos por serie) --------
    est_b = crear_estanque(admin, f"E14B-{stamp}", est_estado)
    if est_b is None:
        cleanup()
        return 1
    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"L14-FULL-{stamp}",
            "estanque_id": est_b,
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "estado_id": lote_estado,
            "fecha_siembra": siembra_media,
            "cantidad_sembrada": 1000,
            "peso_inicial_promedio_g": 2,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST lote con historia", r.status_code == 201, str(r.status_code))
    if r.status_code != 201:
        cleanup()
        return 1
    lote_full = r.json()["id"]
    IDS["lotes"].append(lote_full)

    for dias, muestra, peso in [(10, 20, 80.0), (6, 20, 100.0), (1, 25, 150.0)]:
        r = requests.post(
            f"{BASE}/api/v1/biometrias/",
            headers=H(admin),
            json={
                "lote_id": lote_full,
                "fecha_hora": (now - timedelta(days=dias)).isoformat(),
                "cantidad_muestra": muestra,
                "peso_total_muestra_g": peso,
                "observaciones": PREF,
            },
            timeout=20,
        )
        if r.status_code == 201:
            IDS["biometrias"].append(r.json()["id"])
    check("3 biometrías creadas", len(IDS["biometrias"]) == 3, str(len(IDS["biometrias"])))

    for dias, cantidad in [(9, 5), (3, 7)]:
        r = requests.post(
            f"{BASE}/api/v1/mortalidades/",
            headers=H(admin),
            json={
                "lote_id": lote_full,
                "fecha_hora": (now - timedelta(days=dias)).isoformat(),
                "cantidad": cantidad,
                "observaciones": PREF,
            },
            timeout=20,
        )
        if r.status_code == 201:
            IDS["mortalidades"].append(r.json()["id"])
    check("2 mortalidades creadas", len(IDS["mortalidades"]) == 2, str(len(IDS["mortalidades"])))

    if param_con_ref:
        for dias, valor in [(8, 6.0), (2, 9.5)]:
            r = requests.post(
                f"{BASE}/api/v1/mediciones-agua/",
                headers=H(admin),
                json={
                    "lote_id": lote_full,
                    "parametro_id": param_con_ref,
                    "fecha_hora": (now - timedelta(days=dias)).isoformat(),
                    "valor": valor,
                    "observaciones": PREF,
                },
                timeout=20,
            )
            if r.status_code == 201:
                IDS["mediciones_agua"].append(r.json()["id"])
    if param_sin_ref:
        r = requests.post(
            f"{BASE}/api/v1/mediciones-agua/",
            headers=H(admin),
            json={
                "lote_id": lote_full,
                "parametro_id": param_sin_ref,
                "fecha_hora": (now - timedelta(days=2)).isoformat(),
                "valor": 27.5,
                "observaciones": PREF,
            },
            timeout=20,
        )
        if r.status_code == 201:
            IDS["mediciones_agua"].append(r.json()["id"])

    for dias, volumen, cn in [(7, 12, 10), (2, 18, None)]:
        payload = {
            "lote_id": lote_full,
            "fecha_hora": (now - timedelta(days=dias)).isoformat(),
            "volumen_sedimentable": volumen,
            "unidad": "mL/L",
            "observaciones": PREF,
        }
        if cn is not None:
            payload["relacion_cn"] = cn
        r = requests.post(f"{BASE}/api/v1/mediciones-biofloc/", headers=H(admin), json=payload, timeout=20)
        if r.status_code == 201:
            IDS["mediciones_biofloc"].append(r.json()["id"])
    check("2 mediciones biofloc creadas", len(IDS["mediciones_biofloc"]) == 2, str(len(IDS["mediciones_biofloc"])))

    if producto_masa:
        for dias, cantidad in [(5, 1.5), (1, 2.0)]:
            r = requests.post(
                f"{BASE}/api/v1/alimentaciones/",
                headers=H(admin),
                json={
                    "lote_id": lote_full,
                    "producto_id": producto_masa,
                    "fecha_hora": (now - timedelta(days=dias)).isoformat(),
                    "cantidad": cantidad,
                    "observaciones": PREF,
                },
                timeout=20,
            )
            if r.status_code == 201:
                IDS["alimentaciones"].append(r.json()["id"])

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_full}", headers=H(admin), timeout=20)
    check("GET análisis lote con historia", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        body = r.json()
        revisar_invariantes("con historia", body)
        check("con historia: 3 puntos de peso", len(body["biometrias"]) == 3, str(len(body["biometrias"])))
        check(
            "con historia: 2 puntos de mortalidad con acumulado 12",
            len(body["mortalidades"]) == 2 and body["mortalidades"][-1]["acumulada"] == 12,
            str([fila["acumulada"] for fila in body["mortalidades"]]),
        )
        parametros = {fila["parametro_id"] for fila in body["agua_serie"]}
        check(
            "con historia: serie de agua por parámetro",
            len(body["agua_serie"]) == len(IDS["mediciones_agua"]) and len(parametros) == len(
                {p for p in [param_con_ref, param_sin_ref] if p}
            ),
            f'puntos={len(body["agua_serie"])} parametros={parametros}',
        )
        if param_con_ref:
            con_rango = [fila for fila in body["agua_serie"] if fila["parametro_id"] == param_con_ref]
            check(
                "con historia: rango 5-8 detecta 9.5 fuera y 6.0 dentro",
                sorted(fila["fuera_de_rango"] for fila in con_rango) == [False, True],
                str([(fila["valor"], fila["fuera_de_rango"]) for fila in con_rango]),
            )
        check(
            "con historia: biofloc con y sin C:N",
            len(body["biofloc_serie"]) == 2
            and sum(1 for fila in body["biofloc_serie"] if fila["relacion_cn"] is not None) == 1,
            str([fila["relacion_cn"] for fila in body["biofloc_serie"]]),
        )
        if producto_masa:
            check(
                "con historia: FCA disponible",
                body["indicadores"]["fca_disponible"] is True and body["indicadores"]["fca"] is not None,
                str(body["indicadores"]["fca_motivo"]),
            )
            check(
                "con historia: alimento real acumulado en kg",
                body["indicadores"]["alimento_real_acumulado_kg"] is not None,
            )
        if body["referencia_produccion"]:
            check(
                "con historia: referencia con peso esperado y tasa para comparar",
                body["referencia_produccion"]["peso_esperado_g"] is not None
                and body["referencia_produccion"]["tasa_alimentacion_pct"] is not None
                and body["indicadores"]["racion_diaria_recomendada_kg"] is not None,
                str(body["referencia_produccion"]),
            )
        else:
            check("con historia: referencia con peso esperado y tasa para comparar", True, "sin referencia; omitido")

    # --- Escenario C: un solo punto, sin referencia, unidad no másica ----
    est_c = crear_estanque(admin, f"E14C-{stamp}", est_estado)
    if est_c is None:
        cleanup()
        return 1
    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"L14-UNO-{stamp}",
            "estanque_id": est_c,
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "estado_id": lote_estado,
            "fecha_siembra": (date.today() - timedelta(days=120)).isoformat(),
            "cantidad_sembrada": 300,
            "peso_inicial_promedio_g": 5,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST lote de un punto", r.status_code == 201, str(r.status_code))
    if r.status_code != 201:
        cleanup()
        return 1
    lote_uno = r.json()["id"]
    IDS["lotes"].append(lote_uno)

    r = requests.post(
        f"{BASE}/api/v1/biometrias/",
        headers=H(admin),
        json={
            "lote_id": lote_uno,
            "fecha_hora": now.isoformat(),
            "cantidad_muestra": 10,
            "peso_total_muestra_g": 520.0,
            "observaciones": PREF,
        },
        timeout=20,
    )
    if r.status_code == 201:
        IDS["biometrias"].append(r.json()["id"])

    if producto_no_masa is None:
        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM biofloc.categorias_inventario ORDER BY id LIMIT 1")
        fila = cur.fetchone()
        cat_inv = fila[0] if fila else None
        cur.execute("SELECT id FROM biofloc.unidades WHERE simbolo NOT IN ('kg','g') ORDER BY id LIMIT 1")
        fila = cur.fetchone()
        uni_no_masa = fila[0] if fila else None
        cur.close()
        conn.close()
        if cat_inv and uni_no_masa:
            r = requests.post(
                f"{BASE}/api/v1/productos/",
                headers=H(admin),
                json={
                    "codigo": f"P14-{stamp}",
                    "nombre": f"{PREF} producto no másico",
                    "categoria_id": cat_inv,
                    "unidad_id": uni_no_masa,
                    "stock_minimo": "0.000",
                    "activo": True,
                },
                timeout=20,
            )
            if r.status_code == 201:
                producto_no_masa = r.json()["id"]
                IDS["productos"].append(producto_no_masa)

    if producto_no_masa:
        r = requests.post(
            f"{BASE}/api/v1/alimentaciones/",
            headers=H(admin),
            json={
                "lote_id": lote_uno,
                "producto_id": producto_no_masa,
                "fecha_hora": now.isoformat(),
                "cantidad": 3,
                "observaciones": PREF,
            },
            timeout=20,
        )
        if r.status_code == 201:
            IDS["alimentaciones"].append(r.json()["id"])

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_uno}", headers=H(tecnico), timeout=20)
    check("GET análisis lote de un punto", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        body = r.json()
        revisar_invariantes("un punto", body)
        check("un punto: serie de peso con 1 punto", len(body["biometrias"]) == 1, str(len(body["biometrias"])))
        check(
            "un punto: sin referencia para la semana",
            body["referencia_produccion"] is None
            and body["pendientes"].get("racion_diaria_recomendada_kg") == "SIN_REFERENCIA_PRODUCCION_APLICABLE",
            f'ref={body["referencia_produccion"]} pend={body["pendientes"].get("racion_diaria_recomendada_kg")}',
        )
        if producto_no_masa:
            check(
                "un punto: unidad no másica invalida el total en kg",
                body["indicadores"]["alimento_real_acumulado_kg"] is None
                and body["indicadores"]["fca_motivo"] == "UNIDAD_ALIMENTO_INCOMPATIBLE",
                str(body["indicadores"]["fca_motivo"]),
            )
            check(
                "un punto: alimentación real conserva su unidad",
                len(body["alimentacion_real"]) == 1 and body["alimentacion_real"][0]["unidad"] not in {"kg", "g"},
                str(body["alimentacion_real"]),
            )

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
        print("EXC", type(exc).__name__, str(exc)[:300])
        try:
            cleanup()
        except Exception:  # noqa: BLE001
            pass
        codigo = 1
    raise SystemExit(codigo)
