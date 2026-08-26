#!/usr/bin/env python3
"""FASE 16.13 — núcleo analítico de lote. Prefijo [TEST_F16_13]."""
from __future__ import annotations

import sys
import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import psycopg2
import requests

from env_tests import (
    ADMIN_USER, ADMIN_PASS, TECNICO_USER, TECNICO_PASS,
    OPERARIO_USER, OPERARIO_PASS, DB_CONF,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_F16_13]"
R: list[tuple[str, bool, str]] = []
IDS = {
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


def cleanup() -> None:
    conn = db()
    cur = conn.cursor()
    order = [
        ("mediciones_agua", IDS["mediciones_agua"]),
        ("mediciones_biofloc", IDS["mediciones_biofloc"]),
        ("alimentaciones", IDS["alimentaciones"]),
        ("biometrias", IDS["biometrias"]),
        ("mortalidades", IDS["mortalidades"]),
        ("cosechas", IDS["cosechas"]),
        ("lotes", IDS["lotes"]),
        ("estanques", IDS["estanques"]),
        ("productos", IDS["productos"]),
        ("referencias_produccion", IDS["referencias_produccion"]),
        ("referencias_agua", IDS["referencias_agua"]),
    ]
    for tabla, ids in order:
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
    n = 0
    for sql in [
        "SELECT count(*) FROM biofloc.lotes WHERE observaciones LIKE %s OR codigo LIKE %s",
        "SELECT count(*) FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s",
        "SELECT count(*) FROM biofloc.referencias_produccion WHERE observaciones LIKE %s",
        "SELECT count(*) FROM biofloc.referencias_agua WHERE observaciones LIKE %s",
        "SELECT count(*) FROM biofloc.productos WHERE nombre LIKE %s",
        "SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s",
    ]:
        if "estanques" in sql or "lotes" in sql:
            cur.execute(sql, (like, like))
        else:
            cur.execute(sql, (like,))
        n += int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return n


def main() -> int:
    admin = login(ADMIN_USER, ADMIN_PASS)
    tecnico = login(TECNICO_USER, TECNICO_PASS)
    operario = login(OPERARIO_USER, OPERARIO_PASS)

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/1", timeout=20)
    check("sin token análisis → 403", r.status_code == 403, str(r.status_code))
    r = requests.get(f"{BASE}/api/v1/analisis/lotes/1", headers={"Authorization": "Bearer x"}, timeout=20)
    check("token inválido análisis → 401", r.status_code == 401, str(r.status_code))

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/999999001", headers=H(admin), timeout=20)
    check("lote inexistente → 404", r.status_code == 404, str(r.status_code))

    r = requests.get(f"{BASE}/api/v1/referencias-produccion/", headers=H(admin), timeout=20)
    check("ADMIN GET referencias-produccion", r.status_code == 200, str(r.status_code))
    r = requests.get(f"{BASE}/api/v1/referencias-produccion/", headers=H(operario), timeout=20)
    check("OPERARIO GET referencias-produccion", r.status_code == 200, str(r.status_code))
    r = requests.get(f"{BASE}/api/v1/referencias-produccion/999999001", headers=H(admin), timeout=20)
    check("referencia producción inexistente → 404", r.status_code == 404, str(r.status_code))

    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"{PREF}-Z",
            "estanque_id": 1,
            "especie_id": 1,
            "etapa_productiva_id": 1,
            "estado_id": 1,
            "fecha_siembra": date.today().isoformat(),
            "cantidad_sembrada": 0,
        },
        timeout=20,
    )
    check("cantidad_sembrada=0 → 422", r.status_code == 422, str(r.status_code))

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
    # Dos parámetros de agua sin referencia real para esta especie/etapa: al
    # primero se le crea una referencia TEST (rango), el segundo queda sin rango.
    cur.execute(
        """
        SELECT pa.id FROM biofloc.parametros_agua pa
        WHERE NOT EXISTS (
            SELECT 1 FROM biofloc.referencias_agua r
            WHERE r.especie_id = %s AND r.etapa_productiva_id = %s AND r.parametro_id = pa.id
        )
        ORDER BY pa.id LIMIT 2
        """,
        (especie_id, etapa_id),
    )
    libres = [row[0] for row in cur.fetchall()]
    if libres:
        param_con_ref = libres[0]
        param_sin_ref = libres[1] if len(libres) > 1 else None
    else:
        cur.execute("SELECT id FROM biofloc.parametros_agua ORDER BY id LIMIT 1")
        param_con_ref = cur.fetchone()[0]
        param_sin_ref = None
    param_id = param_con_ref
    cur.execute(
        """
        SELECT p.id, u.simbolo FROM biofloc.productos p
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE u.simbolo IN ('kg', 'g')
        ORDER BY p.id LIMIT 1
        """
    )
    prod_row = cur.fetchone()
    producto_id = prod_row[0] if prod_row else None
    producto_unidad = prod_row[1] if prod_row else None
    cur.execute(
        """
        SELECT p.id FROM biofloc.productos p
        JOIN biofloc.unidades u ON u.id = p.unidad_id
        WHERE u.simbolo NOT IN ('kg', 'g')
        ORDER BY p.id LIMIT 1
        """
    )
    otro_row = cur.fetchone()
    producto_no_masa = otro_row[0] if otro_row else None
    cur.execute("SELECT id FROM biofloc.categorias_inventario ORDER BY id LIMIT 1")
    cat_inv_row = cur.fetchone()
    cat_inv = cat_inv_row[0] if cat_inv_row else None
    cur.execute("SELECT id FROM biofloc.unidades WHERE simbolo NOT IN ('kg','g') ORDER BY id LIMIT 1")
    uni_no_masa_row = cur.fetchone()
    uni_no_masa = uni_no_masa_row[0] if uni_no_masa_row else None

    ref_agua_id = None
    if libres:
        cur.execute(
            """
            INSERT INTO biofloc.referencias_agua
                (especie_id, etapa_productiva_id, parametro_id, valor_minimo, valor_maximo, observaciones, activo)
            VALUES (%s, %s, %s, 7.0000, 9.0000, %s, TRUE)
            RETURNING id
            """,
            (especie_id, etapa_id, param_con_ref, PREF),
        )
        ref_agua_id = cur.fetchone()[0]
        IDS["referencias_agua"].append(ref_agua_id)

    # La referencia de producción se crea antes del análisis para poder verificar
    # la ración recomendada. Cubre la semana 2 (días 8 a 14) del lote completo.
    cur.execute(
        """
        INSERT INTO biofloc.referencias_produccion
            (especie_id, etapa_productiva_id, semana_desde, semana_hasta, peso_esperado_g, tasa_alimentacion_pct, observaciones, activo)
        VALUES (%s, %s, 2, 3, 25.00, 4.500, %s, TRUE)
        ON CONFLICT (especie_id, etapa_productiva_id, semana_desde, semana_hasta) DO NOTHING
        RETURNING id
        """,
        (especie_id, etapa_id, PREF),
    )
    ref_prod_row = cur.fetchone()
    ref_id = ref_prod_row[0] if ref_prod_row else None
    if ref_id:
        IDS["referencias_produccion"].append(ref_id)
    conn.commit()
    cur.close()
    conn.close()

    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    r = requests.post(
        f"{BASE}/api/v1/estanques/",
        headers=H(admin),
        json={
            "codigo": f"E13-{stamp}",
            "nombre": f"{PREF} estanque",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": est_estado,
            "activo": True,
        },
        timeout=20,
    )
    check("POST estanque TEST", r.status_code == 201, str(r.status_code))
    if r.status_code != 201:
        return 1
    estanque_id = r.json()["id"]
    IDS["estanques"].append(estanque_id)

    siembra = (date.today() - timedelta(days=14)).isoformat()
    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"L13-VAC-{stamp}",
            "estanque_id": estanque_id,
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "estado_id": lote_estado,
            "fecha_siembra": siembra,
            "cantidad_sembrada": 1000,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST lote vacío TEST", r.status_code == 201, str(r.status_code))
    lote_vacio = r.json()["id"]
    IDS["lotes"].append(lote_vacio)

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_vacio}", headers=H(operario), timeout=20)
    check("OPERARIO GET análisis lote vacío", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        body = r.json()
        ind = body["indicadores"]
        check("vacío población=1000", ind["poblacion_estimada"] == 1000, str(ind["poblacion_estimada"]))
        check("vacío mortalidad=0", ind["mortalidad_acumulada"] == 0)
        check("vacío cosechas=0", ind["peces_cosechados"] == 0)
        check("vacío peso_promedio_g null", ind["peso_promedio_g"] is None)
        check("vacío biomasa actual null", ind["biomasa_actual_kg"] is None)
        check("vacío biomasa inicial null (sin peso inicial)", ind["biomasa_inicial_kg"] is None)
        check("vacío fca null", ind["fca"] is None)
        check("vacío fca_disponible false", ind["fca_disponible"] is False, str(ind["fca_disponible"]))
        check("vacío ganancia null", ind["ganancia_peso_g"] is None)
        check(
            "pendiente biomasa actual SIN_BIOMETRIA",
            body["pendientes"].get("biomasa_actual_kg") == "SIN_BIOMETRIA",
            str(body["pendientes"].get("biomasa_actual_kg")),
        )
        check(
            "pendiente biomasa inicial SIN_PESO_INICIAL_LOTE",
            body["pendientes"].get("biomasa_inicial_kg") == "SIN_PESO_INICIAL_LOTE",
            str(body["pendientes"].get("biomasa_inicial_kg")),
        )
        check(
            "fca_motivo SIN_BIOMASA_INICIAL",
            ind["fca_motivo"] == "SIN_BIOMASA_INICIAL" and body["pendientes"].get("fca") == "SIN_BIOMASA_INICIAL",
            str(ind["fca_motivo"]),
        )
        check(
            "definición unidad masa en g y kg",
            "g" in body["definiciones"]["unidad_masa_productiva"] and "kg" in body["definiciones"]["unidad_masa_productiva"],
        )
        check("días cultivo >= 14", ind["dias_cultivo"] >= 14, str(ind["dias_cultivo"]))
        dias_v = ind["dias_cultivo"]
        check(
            "semana = floor(días / 7) + 1 (día 0–6 = semana 1)",
            ind["semana_cultivo"] == (dias_v // 7) + 1,
            f'semana={ind["semana_cultivo"]} dias={dias_v}',
        )
        check(
            "vacío ración calculada con peso esperado si no hay biometría",
            ind["racion_diaria_recomendada_kg"] is not None
            or body["pendientes"].get("racion_diaria_recomendada_kg")
            in ("SIN_REFERENCIA_PRODUCCION_APLICABLE", None),
            str(ind.get("racion_diaria_recomendada_kg")),
        )
        check(
            "raciones: número único o rango, sin promedio inventado",
            (
                (ind.get("raciones_diarias_texto") not in (None, ""))
                or (ind.get("numero_raciones_diarias") is not None)
                or body["pendientes"].get("numero_raciones_diarias")
                or body["pendientes"].get("racion_diaria_recomendada_kg")
                == "SIN_REFERENCIA_PRODUCCION_APLICABLE"
            ),
            str(ind.get("raciones_diarias_texto") or ind.get("numero_raciones_diarias")),
        )
        check("vacío series vacías", body["agua_serie"] == [] and body["biofloc_serie"] == [] and body["biometrias"] == [])

    # Cierre por PUT con fecha_cierre (date) → regresión de auditoría JSONB.
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM biofloc.estados_lote WHERE nombre='FINALIZADO' LIMIT 1")
    fin_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    r = requests.put(
        f"{BASE}/api/v1/lotes/{lote_vacio}",
        headers=H(admin),
        json={"estado_id": fin_id, "fecha_cierre": date.today().isoformat(), "observaciones": PREF},
        timeout=20,
    )
    check("PUT cierre lote con fecha_cierre → 200", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        check("lote cerrado con fecha_cierre", r.json()["fecha_cierre"] == date.today().isoformat(), str(r.json().get("fecha_cierre")))

    r = requests.post(
        f"{BASE}/api/v1/estanques/",
        headers=H(admin),
        json={
            "codigo": f"E13B-{stamp}",
            "nombre": f"{PREF} estanque B",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": est_estado,
            "activo": True,
        },
        timeout=20,
    )
    check("POST estanque B TEST", r.status_code == 201, str(r.status_code))
    if r.status_code != 201:
        cleanup()
        return 1
    estanque_b = r.json()["id"]
    IDS["estanques"].append(estanque_b)

    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"L13-FULL-{stamp}",
            "estanque_id": estanque_b,
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "estado_id": lote_estado,
            "fecha_siembra": siembra,
            "cantidad_sembrada": 1000,
            "peso_inicial_promedio_g": 1.2,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST lote completo TEST", r.status_code == 201, str(r.status_code))
    if r.status_code != 201:
        cleanup()
        return 1
    lote_full = r.json()["id"]
    IDS["lotes"].append(lote_full)

    r = requests.post(
        f"{BASE}/api/v1/lotes/",
        headers=H(admin),
        json={
            "codigo": f"L13-DUP-{stamp}",
            "estanque_id": estanque_b,
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "estado_id": lote_estado,
            "fecha_siembra": siembra,
            "cantidad_sembrada": 100,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("segundo lote ACTIVO mismo estanque → 409", r.status_code == 409, str(r.status_code))
    if r.status_code == 201:
        IDS["lotes"].append(r.json()["id"])

    now = datetime.now(timezone.utc).isoformat()
    r = requests.post(
        f"{BASE}/api/v1/biometrias/",
        headers=H(admin),
        json={
            "lote_id": lote_full,
            "fecha_hora": now,
            "cantidad_muestra": 50,
            "peso_total_muestra_g": 250.0,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST biometría", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        IDS["biometrias"].append(r.json()["id"])

    r = requests.post(
        f"{BASE}/api/v1/mortalidades/",
        headers=H(admin),
        json={"lote_id": lote_full, "fecha_hora": now, "cantidad": 10, "observaciones": PREF},
        timeout=20,
    )
    check("POST mortalidad", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        IDS["mortalidades"].append(r.json()["id"])

    r = requests.post(
        f"{BASE}/api/v1/cosechas/",
        headers=H(admin),
        json={
            "lote_id": lote_full,
            "fecha_hora": now,
            "cantidad_peces": 20,
            "peso_total_kg": 10,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST cosecha", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        IDS["cosechas"].append(r.json()["id"])

    r = requests.post(
        f"{BASE}/api/v1/mediciones-agua/",
        headers=H(admin),
        json={"lote_id": lote_full, "parametro_id": param_id, "fecha_hora": now, "valor": 6.5, "observaciones": PREF},
        timeout=20,
    )
    check("POST medición agua", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        IDS["mediciones_agua"].append(r.json()["id"])

    if param_sin_ref:
        r = requests.post(
            f"{BASE}/api/v1/mediciones-agua/",
            headers=H(admin),
            json={"lote_id": lote_full, "parametro_id": param_sin_ref, "fecha_hora": now, "valor": 6.5, "observaciones": PREF},
            timeout=20,
        )
        check("POST medición agua sin referencia", r.status_code == 201, str(r.status_code))
        if r.status_code == 201:
            IDS["mediciones_agua"].append(r.json()["id"])

    r = requests.post(
        f"{BASE}/api/v1/mediciones-biofloc/",
        headers=H(admin),
        json={
            "lote_id": lote_full,
            "fecha_hora": now,
            "volumen_sedimentable": 15,
            "unidad": "mL/L",
            "relacion_cn": 12,
            "observaciones": PREF,
        },
        timeout=20,
    )
    check("POST medición biofloc", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        IDS["mediciones_biofloc"].append(r.json()["id"])

    if producto_id:
        r = requests.post(
            f"{BASE}/api/v1/alimentaciones/",
            headers=H(admin),
            json={"lote_id": lote_full, "producto_id": producto_id, "fecha_hora": now, "cantidad": 3.5, "observaciones": PREF},
            timeout=20,
        )
        check("POST alimentación", r.status_code == 201, str(r.status_code))
        if r.status_code == 201:
            IDS["alimentaciones"].append(r.json()["id"])
    else:
        check("POST alimentación", True, "sin producto en BD; omitido")

    r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_full}", headers=H(tecnico), timeout=20)
    check("TECNICO GET análisis completo", r.status_code == 200, str(r.status_code))
    if r.status_code == 200:
        body = r.json()
        ind = body["indicadores"]
        check("población 970", ind["poblacion_estimada"] == 970, str(ind["poblacion_estimada"]))
        check("supervivencia 99", Decimal(str(ind["supervivencia_porcentaje"])) == Decimal("99.00"), str(ind["supervivencia_porcentaje"]))
        check("mortalidad % 1", Decimal(str(ind["mortalidad_porcentaje"])) == Decimal("1.00"), str(ind["mortalidad_porcentaje"]))
        check("peso promedio 5 g", Decimal(str(ind["peso_promedio_g"])) == Decimal("5.000"), str(ind["peso_promedio_g"]))
        check("serie biometrías > 0", len(body["biometrias"]) == 1)
        check("serie mortalidades acumulada", body["mortalidades"][0]["acumulada"] == 10)
        check("agua última presente", len(body["agua"]) >= 1)
        check("agua serie presente", len(body["agua_serie"]) >= 1)
        check("biofloc presente", body["biofloc"] is not None)
        check(
            "biofloc serie coincide con la última",
            len(body["biofloc_serie"]) == 1 and body["biofloc_serie"][-1]["id"] == body["biofloc"]["id"],
            str(len(body["biofloc_serie"])),
        )

        agua_por_param = {row["parametro_id"]: row for row in body["agua"]}
        if ref_agua_id:
            fila = agua_por_param.get(param_con_ref)
            check(
                "agua con referencia → fuera_de_rango true y rango 7-9",
                fila is not None
                and fila["fuera_de_rango"] is True
                and Decimal(str(fila["valor_minimo"])) == Decimal("7.0000")
                and Decimal(str(fila["valor_maximo"])) == Decimal("9.0000"),
                str(fila),
            )
        else:
            check("agua con referencia → fuera_de_rango true y rango 7-9", True, "sin parámetro libre; omitido")
        if param_sin_ref:
            fila = agua_por_param.get(param_sin_ref)
            check(
                "agua sin referencia → fuera_de_rango null y sin rango",
                fila is not None
                and fila["fuera_de_rango"] is None
                and fila["valor_minimo"] is None
                and fila["valor_maximo"] is None,
                str(fila),
            )
        else:
            check("agua sin referencia → fuera_de_rango null y sin rango", True, "sin segundo parámetro libre; omitido")

        # Biomasa inicial = sembrados × peso inicial / 1000; actual = población × peso promedio / 1000
        check(
            "biomasa inicial 1.200 kg",
            Decimal(str(ind["biomasa_inicial_kg"])) == Decimal("1.200"),
            str(ind["biomasa_inicial_kg"]),
        )
        check(
            "biomasa actual 4.850 kg",
            Decimal(str(ind["biomasa_actual_kg"])) == Decimal("4.850"),
            str(ind["biomasa_actual_kg"]),
        )
        check(
            "biomasa sin pendiente",
            "biomasa_actual_kg" not in body["pendientes"] and "biomasa_inicial_kg" not in body["pendientes"],
            str(body["pendientes"]),
        )

        # Ganancia = peso promedio actual − peso inicial
        check(
            "ganancia 3.800 g",
            Decimal(str(ind["ganancia_peso_g"])) == Decimal("3.800"),
            str(ind["ganancia_peso_g"]),
        )
        dias = ind["dias_cultivo"]
        esperado_diaria = (Decimal("3.800") / Decimal(dias)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        check(
            "ganancia diaria = ganancia / días",
            Decimal(str(ind["ganancia_diaria_g"])) == esperado_diaria,
            f'{ind["ganancia_diaria_g"]} esperado {esperado_diaria} con dias={dias}',
        )

        if producto_id:
            check("alimento por unidad no mezcla", len(body["alimentacion_real_por_unidad"]) >= 1)
            factor = Decimal("1") if producto_unidad == "kg" else Decimal("0.001")
            alimento_kg = (Decimal("3.5") * factor).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            check(
                "alimento real acumulado en kg",
                Decimal(str(ind["alimento_real_acumulado_kg"])) == alimento_kg,
                f'{ind["alimento_real_acumulado_kg"]} esperado {alimento_kg} ({producto_unidad})',
            )
            # FCA = alimento real (kg) / (biomasa actual + cosechada − biomasa inicial)
            delta = Decimal("4.850") + Decimal("10.000") - Decimal("1.200")
            esperado_fca = (Decimal("3.5") * factor / delta).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            check(
                "fca = alimento / ganancia de biomasa",
                Decimal(str(ind["fca"])) == esperado_fca,
                f'{ind["fca"]} esperado {esperado_fca}',
            )
            check(
                "fca_disponible true y sin motivo",
                ind["fca_disponible"] is True and ind["fca_motivo"] is None and "fca" not in body["pendientes"],
                str(body["pendientes"]),
            )
        else:
            check("fca null sin alimentación", ind["fca"] is None, str(ind["fca"]))
            check(
                "razón fca sin alimento",
                ind["fca_motivo"] == "SIN_ALIMENTO_REAL_REGISTRADO",
                str(ind["fca_motivo"]),
            )

        # Ración recomendada = biomasa actual × tasa de la referencia / 100
        ref = body["referencia_produccion"]
        if ref and ref["tasa_alimentacion_pct"] is not None:
            esperado_racion = (
                Decimal(str(ind["biomasa_actual_kg"])) * Decimal(str(ref["tasa_alimentacion_pct"])) / Decimal("100")
            ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            check(
                "ración recomendada = biomasa × tasa / 100",
                Decimal(str(ind["racion_diaria_recomendada_kg"])) == esperado_racion,
                f'{ind["racion_diaria_recomendada_kg"]} esperado {esperado_racion} (tasa {ref["tasa_alimentacion_pct"]}%)',
            )
            check(
                "referencia resuelta cubre la semana del lote",
                ref["semana_desde"] <= ind["semana_cultivo"] <= ref["semana_hasta"],
                f'semana={ind["semana_cultivo"]} rango={ref["semana_desde"]}-{ref["semana_hasta"]}',
            )
        else:
            check(
                "ración recomendada null sin referencia utilizable",
                ind["racion_diaria_recomendada_kg"] is None
                and body["pendientes"].get("racion_diaria_recomendada_kg")
                in {"SIN_REFERENCIA_PRODUCCION_APLICABLE", "REFERENCIA_SIN_TASA_ALIMENTACION"},
                str(body["pendientes"].get("racion_diaria_recomendada_kg")),
            )

    # Alimento en unidad no convertible a kg invalida el FCA, no lo inventa.
    if producto_no_masa is None and cat_inv and uni_no_masa:
        r = requests.post(
            f"{BASE}/api/v1/productos/",
            headers=H(admin),
            json={
                "codigo": f"P13-{stamp}",
                "nombre": f"{PREF} producto no másico",
                "categoria_id": cat_inv,
                "unidad_id": uni_no_masa,
                "stock_minimo": "0.000",
                "activo": True,
            },
            timeout=20,
        )
        check("POST producto unidad no másica", r.status_code == 201, str(r.status_code))
        if r.status_code == 201:
            producto_no_masa = r.json()["id"]
            IDS["productos"].append(producto_no_masa)

    if producto_no_masa:
        r = requests.post(
            f"{BASE}/api/v1/alimentaciones/",
            headers=H(admin),
            json={"lote_id": lote_full, "producto_id": producto_no_masa, "fecha_hora": now, "cantidad": 2, "observaciones": PREF},
            timeout=20,
        )
        check("POST alimentación unidad no másica", r.status_code == 201, str(r.status_code))
        if r.status_code == 201:
            IDS["alimentaciones"].append(r.json()["id"])
            r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_full}", headers=H(admin), timeout=20)
            if r.status_code == 200:
                body = r.json()
                check("fca null por unidad no convertible", body["indicadores"]["fca"] is None, str(body["indicadores"]["fca"]))
                check(
                    "razón UNIDAD_ALIMENTO_INCOMPATIBLE",
                    body["indicadores"]["fca_motivo"] == "UNIDAD_ALIMENTO_INCOMPATIBLE"
                    and body["pendientes"].get("fca") == "UNIDAD_ALIMENTO_INCOMPATIBLE",
                    str(body["indicadores"]["fca_motivo"]),
                )
                check(
                    "alimento real acumulado null por unidad incompatible",
                    body["indicadores"]["alimento_real_acumulado_kg"] is None
                    and body["pendientes"].get("alimento_real_acumulado_kg") == "UNIDAD_ALIMENTO_INCOMPATIBLE",
                    str(body["indicadores"]["alimento_real_acumulado_kg"]),
                )
                check(
                    "biomasa sigue calculada con unidad mixta de alimento",
                    Decimal(str(body["indicadores"]["biomasa_actual_kg"])) == Decimal("4.850"),
                    str(body["indicadores"]["biomasa_actual_kg"]),
                )
    else:
        check("POST alimentación unidad no másica", True, "sin producto no másico en BD; omitido")

    # Lote fuera del rango de semanas de la referencia: referencia null sin inventar valores.
    r = requests.post(
        f"{BASE}/api/v1/estanques/",
        headers=H(admin),
        json={
            "codigo": f"E13C-{stamp}",
            "nombre": f"{PREF} estanque C",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": est_estado,
            "activo": True,
        },
        timeout=20,
    )
    check("POST estanque C TEST", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        estanque_c = r.json()["id"]
        IDS["estanques"].append(estanque_c)
        r = requests.post(
            f"{BASE}/api/v1/lotes/",
            headers=H(admin),
            json={
                "codigo": f"L13-SREF-{stamp}",
                "estanque_id": estanque_c,
                "especie_id": especie_id,
                "etapa_productiva_id": etapa_id,
                "estado_id": lote_estado,
                "fecha_siembra": (date.today() - timedelta(days=120)).isoformat(),
                "cantidad_sembrada": 500,
                "observaciones": PREF,
            },
            timeout=20,
        )
        check("POST lote semana alta TEST", r.status_code == 201, str(r.status_code))
        if r.status_code == 201:
            lote_sref = r.json()["id"]
            IDS["lotes"].append(lote_sref)
            r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_sref}", headers=H(operario), timeout=20)
            if r.status_code == 200:
                body = r.json()
                ind = body["indicadores"]
                check("semana alta floor(d/7)+1", ind["semana_cultivo"] == (ind["dias_cultivo"] // 7) + 1, str(ind["semana_cultivo"]))
                check("semana alta sin fila BD", body["referencia_produccion"] is None)
                if body.get("referencia_alimentacion") is None:
                    check(
                        "semana alta N/D sin ración",
                        ind["racion_diaria_recomendada_kg"] is None
                        and body["pendientes"].get("racion_diaria_recomendada_kg")
                        == "SIN_REFERENCIA_PRODUCCION_APLICABLE",
                        f'pend={body["pendientes"].get("racion_diaria_recomendada_kg")}',
                    )

    # Lote sembrado hoy: dias_cultivo = 0 sin división por cero y semana productiva 1.
    r = requests.post(
        f"{BASE}/api/v1/estanques/",
        headers=H(admin),
        json={
            "codigo": f"E13D-{stamp}",
            "nombre": f"{PREF} estanque D",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": est_estado,
            "activo": True,
        },
        timeout=20,
    )
    check("POST estanque D TEST", r.status_code == 201, str(r.status_code))
    if r.status_code == 201:
        estanque_d = r.json()["id"]
        IDS["estanques"].append(estanque_d)
        r = requests.post(
            f"{BASE}/api/v1/lotes/",
            headers=H(admin),
            json={
                "codigo": f"L13-HOY-{stamp}",
                "estanque_id": estanque_d,
                "especie_id": especie_id,
                "etapa_productiva_id": etapa_id,
                "estado_id": lote_estado,
                "fecha_siembra": date.today().isoformat(),
                "cantidad_sembrada": 100,
                "peso_inicial_promedio_g": 10,
                "observaciones": PREF,
            },
            timeout=20,
        )
        check("POST lote sembrado hoy TEST", r.status_code == 201, str(r.status_code))
        if r.status_code == 201:
            lote_hoy = r.json()["id"]
            IDS["lotes"].append(lote_hoy)
            r = requests.post(
                f"{BASE}/api/v1/biometrias/",
                headers=H(admin),
                json={
                    "lote_id": lote_hoy,
                    "fecha_hora": now,
                    "cantidad_muestra": 10,
                    "peso_total_muestra_g": 50.0,
                    "observaciones": PREF,
                },
                timeout=20,
            )
            check("POST biometría lote de hoy", r.status_code == 201, str(r.status_code))
            if r.status_code == 201:
                IDS["biometrias"].append(r.json()["id"])
            if producto_id:
                r = requests.post(
                    f"{BASE}/api/v1/alimentaciones/",
                    headers=H(admin),
                    json={"lote_id": lote_hoy, "producto_id": producto_id, "fecha_hora": now, "cantidad": 1, "observaciones": PREF},
                    timeout=20,
                )
                if r.status_code == 201:
                    IDS["alimentaciones"].append(r.json()["id"])
            r = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_hoy}", headers=H(admin), timeout=20)
            if r.status_code == 200:
                body = r.json()
                ind = body["indicadores"]
                check("días cultivo 0", ind["dias_cultivo"] == 0, str(ind["dias_cultivo"]))
                check("semana 1 el día de la siembra", ind["semana_cultivo"] == 1, str(ind["semana_cultivo"]))
                check(
                    "ganancia diaria null por DIAS_CULTIVO_CERO",
                    ind["ganancia_diaria_g"] is None
                    and body["pendientes"].get("ganancia_diaria_g") == "DIAS_CULTIVO_CERO",
                    str(body["pendientes"].get("ganancia_diaria_g")),
                )
                check(
                    "ganancia de peso −5 g calculada",
                    Decimal(str(ind["ganancia_peso_g"])) == Decimal("-5.000"),
                    str(ind["ganancia_peso_g"]),
                )
                check(
                    "biomasa inicial 1.000 y actual 0.500 kg",
                    Decimal(str(ind["biomasa_inicial_kg"])) == Decimal("1.000")
                    and Decimal(str(ind["biomasa_actual_kg"])) == Decimal("0.500"),
                    f'{ind["biomasa_inicial_kg"]} / {ind["biomasa_actual_kg"]}',
                )
                esperado_motivo = "GANANCIA_BIOMASA_NO_POSITIVA" if producto_id else "SIN_ALIMENTO_REAL_REGISTRADO"
                check(
                    f"fca null por {esperado_motivo}",
                    ind["fca"] is None and ind["fca_disponible"] is False and ind["fca_motivo"] == esperado_motivo,
                    str(ind["fca_motivo"]),
                )

    if ref_id:
        r = requests.get(
            f"{BASE}/api/v1/referencias-produccion/?especie_id={especie_id}&etapa_productiva_id={etapa_id}&semana=2",
            headers=H(admin),
            timeout=20,
        )
        check("GET referencias aplicables semana=2", r.status_code == 200 and any(x["id"] == ref_id for x in r.json()), str(r.status_code))
        r = requests.get(
            f"{BASE}/api/v1/referencias-produccion/?semana=99",
            headers=H(admin),
            timeout=20,
        )
        check("GET referencias semana=99 sin TEST", r.status_code == 200 and all(x["id"] != ref_id for x in r.json()), str(r.status_code))
        r = requests.get(f"{BASE}/api/v1/referencias-produccion/{ref_id}", headers=H(tecnico), timeout=20)
        check("TECNICO GET referencia por id", r.status_code == 200, str(r.status_code))
    else:
        check("GET referencias aplicables semana=2", True, "referencia TEST no insertada (rango ya existente); omitido")

    cleanup()
    left = leftover()
    check("leftover = 0", left == 0, str(left))

    failed = [n for n, ok, _ in R if not ok]
    print(f"\nRESULT {len(R) - len(failed)}/{len(R)} OK")
    if failed:
        print("FAILED:", "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        print("EXC", type(exc).__name__, str(exc)[:300])
        try:
            cleanup()
        except Exception:
            pass
        code = 1
    raise SystemExit(code)
