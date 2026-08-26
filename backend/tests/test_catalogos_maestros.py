#!/usr/bin/env python3
"""Catálogo maestro de producción: especies y referencias.

Prefijo [TEST_CATALOGOS]. El administrador escribe; TECNICO y OPERARIO solo leen.
No siembra valores de especie ni de referencia fuera de este prefijo.
Al terminar, leftover = 0.
"""
from __future__ import annotations

import io
import math
import sys
from datetime import date, datetime, timedelta, timezone

import psycopg2
import requests

from env_tests import (
    ADMIN_PASS,
    ADMIN_USER,
    DB_CONF,
    OPERARIO_PASS,
    OPERARIO_USER,
    TECNICO_PASS,
    TECNICO_USER,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_CATALOGOS]"
R: list[tuple[str, bool, str]] = []
IDS: dict[str, list[int]] = {
    "especies": [],
    "referencias_produccion": [],
    "referencias_agua": [],
    "referencias_biofloc": [],
    "parametros_agua": [],
    "estanques": [],
    "lotes": [],
    "biometrias": [],
}


def check(name: str, ok: bool, detail: str = "") -> None:
    R.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" {detail}" if detail else ""))


def login(correo: str, password: str) -> str:
    r = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": correo, "password": password},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def db():
    return psycopg2.connect(**DB_CONF)


def cleanup() -> int:
    conn = db()
    cur = conn.cursor()
    order = [
        ("biometrias", IDS["biometrias"]),
        ("lotes", IDS["lotes"]),
        ("estanques", IDS["estanques"]),
        ("referencias_produccion", IDS["referencias_produccion"]),
        ("referencias_agua", IDS["referencias_agua"]),
        ("referencias_biofloc", IDS["referencias_biofloc"]),
        ("parametros_agua", IDS["parametros_agua"]),
        ("especies", IDS["especies"]),
    ]
    for tabla, ids in order:
        if not ids:
            continue
        cur.execute("DELETE FROM biofloc.auditoria WHERE tabla=%s AND registro_id = ANY(%s)", (tabla, ids))
        cur.execute(f"DELETE FROM biofloc.{tabla} WHERE id = ANY(%s)", (ids,))
    patron = f"{PREF}%"
    cur.execute("DELETE FROM biofloc.biometrias WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.lotes WHERE codigo LIKE %s OR observaciones LIKE %s", (patron, patron))
    cur.execute("DELETE FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s", (patron, patron))
    cur.execute("DELETE FROM biofloc.referencias_produccion WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.referencias_agua WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.referencias_biofloc WHERE observaciones LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.parametros_agua WHERE nombre LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.especies WHERE nombre_comun LIKE %s", (patron,))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    conn.commit()
    leftover_sql = """
        SELECT
          (SELECT COUNT(*) FROM biofloc.especies WHERE nombre_comun LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.referencias_produccion WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.referencias_agua WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.referencias_biofloc WHERE observaciones LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.parametros_agua WHERE nombre LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.lotes WHERE codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.estanques WHERE codigo LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s) +
          (SELECT COUNT(*) FROM biofloc.parametros_agua WHERE nombre LIKE 'AUDIT_PARAM_%%')
    """
    cur.execute(
        leftover_sql,
        (patron, patron, patron, patron, patron, patron, patron, f"%{PREF}%"),
    )
    leftover = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return leftover


def track(tabla: str, ident: int | None) -> None:
    if ident is not None:
        IDS[tabla].append(ident)


def main() -> int:
    try:
        admin = login(ADMIN_USER, ADMIN_PASS)
        tecnico = login(TECNICO_USER, TECNICO_PASS)
        operario = login(OPERARIO_USER, OPERARIO_PASS)
    except Exception as exc:
        print(f"[CRITICAL] Login falló: {exc}")
        return 1

    check("ADMIN GET especies", requests.get(f"{BASE}/api/v1/especies/", headers=H(admin), timeout=20).status_code == 200)
    check("TECNICO GET especies", requests.get(f"{BASE}/api/v1/especies/", headers=H(tecnico), timeout=20).status_code == 200)
    check("OPERARIO GET especies", requests.get(f"{BASE}/api/v1/especies/", headers=H(operario), timeout=20).status_code == 200)

    r_etapas = requests.get(f"{BASE}/api/v1/etapas-productivas/", headers=H(admin), timeout=20)
    check("GET etapas-productivas", r_etapas.status_code == 200 and len(r_etapas.json()) >= 1)
    r_estados = requests.get(f"{BASE}/api/v1/estados-lote/", headers=H(operario), timeout=20)
    check("OPERARIO GET estados-lote", r_estados.status_code == 200 and len(r_estados.json()) >= 1)

    etapa_id = r_etapas.json()[0]["id"]

    payload_sp = {
        "nombre_comun": f"{PREF} especie alfa",
        "nombre_cientifico": "Testus catalogus",
        "activo": True,
    }
    r_post_admin = requests.post(f"{BASE}/api/v1/especies/", json=payload_sp, headers=H(admin), timeout=20)
    check("POST ADMIN especie 201", r_post_admin.status_code == 201, str(r_post_admin.status_code))
    especie_id = r_post_admin.json()["id"] if r_post_admin.status_code == 201 else None
    track("especies", especie_id)

    if especie_id:
        cuerpo = r_post_admin.json()
        check(
            "especie incluye conteos de referencias",
            cuerpo.get("n_referencias_produccion") == 0 and cuerpo.get("n_referencias_agua") == 0,
            str(cuerpo),
        )

    r_tec_post = requests.post(f"{BASE}/api/v1/especies/", json={**payload_sp, "nombre_comun": f"{PREF} tec"}, headers=H(tecnico), timeout=20)
    check("POST TECNICO especie 403", r_tec_post.status_code == 403, str(r_tec_post.status_code))
    r_op_post = requests.post(f"{BASE}/api/v1/especies/", json={**payload_sp, "nombre_comun": f"{PREF} ope"}, headers=H(operario), timeout=20)
    check("POST OPERARIO especie 403", r_op_post.status_code == 403, str(r_op_post.status_code))

    if especie_id:
        r_put_admin = requests.put(
            f"{BASE}/api/v1/especies/{especie_id}",
            json={"nombre_cientifico": "Testus catalogus var. admin", "activo": True},
            headers=H(admin),
            timeout=20,
        )
        check("PUT ADMIN especie 200", r_put_admin.status_code == 200)
        r_put_tec = requests.put(
            f"{BASE}/api/v1/especies/{especie_id}",
            json={"activo": False},
            headers=H(tecnico),
            timeout=20,
        )
        check("PUT TECNICO especie 403", r_put_tec.status_code == 403)
        r_put_op = requests.put(
            f"{BASE}/api/v1/especies/{especie_id}",
            json={"activo": False},
            headers=H(operario),
            timeout=20,
        )
        check("PUT OPERARIO especie 403", r_put_op.status_code == 403)

        r_dup = requests.post(f"{BASE}/api/v1/especies/", json=payload_sp, headers=H(admin), timeout=20)
        check("especie duplicada 409", r_dup.status_code == 409, str(r_dup.status_code))

    r_inv = requests.post(
        f"{BASE}/api/v1/especies/",
        json={"nombre_comun": "   ", "activo": True},
        headers=H(admin),
        timeout=20,
    )
    check("especie inválida 422", r_inv.status_code == 422, str(r_inv.status_code))

    check(
        "GET 3 roles referencias-produccion",
        all(
            requests.get(f"{BASE}/api/v1/referencias-produccion/", headers=H(tok), timeout=20).status_code == 200
            for tok in (admin, tecnico, operario)
        ),
    )

    payload_ref = {
        "especie_id": especie_id,
        "etapa_productiva_id": etapa_id,
        "semana_desde": 0,
        "semana_hasta": 2,
        "peso_esperado_g": 12.5,
        "tasa_alimentacion_pct": 3.5,
        "observaciones": PREF,
        "activo": True,
    }
    r_ref_admin = requests.post(
        f"{BASE}/api/v1/referencias-produccion/", json=payload_ref, headers=H(admin), timeout=20
    )
    check("POST ADMIN referencia producción 201", r_ref_admin.status_code == 201, r_ref_admin.text[:200])
    ref_id = r_ref_admin.json()["id"] if r_ref_admin.status_code == 201 else None
    track("referencias_produccion", ref_id)

    r_ref_tec = requests.post(
        f"{BASE}/api/v1/referencias-produccion/", json=payload_ref, headers=H(tecnico), timeout=20
    )
    check("POST TECNICO referencia producción 403", r_ref_tec.status_code == 403)
    r_ref_op = requests.post(
        f"{BASE}/api/v1/referencias-produccion/", json=payload_ref, headers=H(operario), timeout=20
    )
    check("POST OPERARIO referencia producción 403", r_ref_op.status_code == 403)

    if ref_id:
        r_put_ref = requests.put(
            f"{BASE}/api/v1/referencias-produccion/{ref_id}",
            json={"observaciones": f"{PREF} actualizada", "activo": True},
            headers=H(admin),
            timeout=20,
        )
        check("PUT ADMIN referencia producción 200", r_put_ref.status_code == 200)
        r_put_full = requests.put(
            f"{BASE}/api/v1/referencias-produccion/{ref_id}",
            json={
                **payload_ref,
                "peso_esperado_g": 13.0,
                "tasa_alimentacion_pct": 4.6,
                "observaciones": f"{PREF} full payload",
            },
            headers=H(admin),
            timeout=20,
        )
        check("PUT ADMIN referencia producción payload completo 200", r_put_full.status_code == 200, r_put_full.text[:200])
        r_put_ref_tec = requests.put(
            f"{BASE}/api/v1/referencias-produccion/{ref_id}",
            json={"activo": False},
            headers=H(tecnico),
            timeout=20,
        )
        check("PUT TECNICO referencia producción 403", r_put_ref_tec.status_code == 403)

        r_dup_ref = requests.post(
            f"{BASE}/api/v1/referencias-produccion/", json=payload_ref, headers=H(admin), timeout=20
        )
        check("referencia producción duplicada 409", r_dup_ref.status_code == 409, str(r_dup_ref.status_code))

    r_rango = requests.post(
        f"{BASE}/api/v1/referencias-produccion/",
        json={**payload_ref, "semana_desde": 5, "semana_hasta": 1, "observaciones": PREF},
        headers=H(admin),
        timeout=20,
    )
    check("rango semanal inválido 422", r_rango.status_code == 422, str(r_rango.status_code))

    r_peso_neg = requests.post(
        f"{BASE}/api/v1/referencias-produccion/",
        json={**payload_ref, "semana_desde": 10, "semana_hasta": 11, "peso_esperado_g": -1, "observaciones": PREF},
        headers=H(admin),
        timeout=20,
    )
    check("peso negativo 422", r_peso_neg.status_code == 422, str(r_peso_neg.status_code))

    r_tasa_neg = requests.post(
        f"{BASE}/api/v1/referencias-produccion/",
        json={
            **payload_ref,
            "semana_desde": 12,
            "semana_hasta": 13,
            "tasa_alimentacion_pct": -0.1,
            "observaciones": PREF,
        },
        headers=H(admin),
        timeout=20,
    )
    check("tasa negativa 422", r_tasa_neg.status_code == 422, str(r_tasa_neg.status_code))

    r_agua_get = requests.get(f"{BASE}/api/v1/referencias-agua/", headers=H(tecnico), timeout=20)
    check("TECNICO GET referencias-agua 200", r_agua_get.status_code == 200)
    r_agua_tec = requests.post(
        f"{BASE}/api/v1/referencias-agua/",
        json={
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "parametro_id": 1,
            "valor_minimo": 1,
            "valor_maximo": 2,
            "observaciones": PREF,
        },
        headers=H(tecnico),
        timeout=20,
    )
    check("POST TECNICO referencias-agua 403", r_agua_tec.status_code == 403, str(r_agua_tec.status_code))
    r_agua_op = requests.post(
        f"{BASE}/api/v1/referencias-agua/",
        json={
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "parametro_id": 1,
            "valor_minimo": 1,
            "valor_maximo": 2,
            "observaciones": PREF,
        },
        headers=H(operario),
        timeout=20,
    )
    check("POST OPERARIO referencias-agua 403", r_agua_op.status_code == 403)

    if especie_id:
        r_sp = requests.get(f"{BASE}/api/v1/especies/{especie_id}", headers=H(admin), timeout=20)
        check(
            "conteo producción tras crear referencia",
            r_sp.status_code == 200 and r_sp.json().get("n_referencias_produccion") == 1,
            str(r_sp.json() if r_sp.status_code == 200 else r_sp.status_code),
        )

        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM biofloc.estados_estanque WHERE nombre='DISPONIBLE' LIMIT 1")
        est_estado = cur.fetchone()[0]
        cur.execute("SELECT id FROM biofloc.estados_lote WHERE nombre='ACTIVO' LIMIT 1")
        lote_estado = cur.fetchone()[0]
        cur.close()
        conn.close()

        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        r_est = requests.post(
            f"{BASE}/api/v1/estanques/",
            json={
                "codigo": f"{PREF}-E{ts}",
                "nombre": f"{PREF} estanque",
                "diametro": 8,
                "profundidad": 1.2,
                "estado_id": est_estado,
                "activo": True,
            },
            headers=H(admin),
            timeout=20,
        )
        check("estanque TEST para lote", r_est.status_code == 201, r_est.text[:160])
        estanque_id = r_est.json()["id"] if r_est.status_code == 201 else None
        track("estanques", estanque_id)

        if estanque_id:
            r_lote = requests.post(
                f"{BASE}/api/v1/lotes/",
                json={
                    "codigo": f"{PREF}-L{ts}",
                    "estanque_id": estanque_id,
                    "especie_id": especie_id,
                    "etapa_productiva_id": etapa_id,
                    "estado_id": lote_estado,
                    "fecha_siembra": (date.today() - timedelta(days=3)).isoformat(),
                    "cantidad_sembrada": 500,
                    "peso_inicial_promedio_g": 2.0,
                    "observaciones": PREF,
                },
                headers=H(admin),
                timeout=20,
            )
            check("lote usa especie del catálogo", r_lote.status_code == 201, r_lote.text[:200])
            lote_id = r_lote.json()["id"] if r_lote.status_code == 201 else None
            track("lotes", lote_id)

            if lote_id:
                ahora = datetime.now(timezone.utc)
                r_bio = requests.post(
                    f"{BASE}/api/v1/biometrias/",
                    json={
                        "lote_id": lote_id,
                        "fecha_hora": ahora.isoformat(),
                        "cantidad_muestra": 10,
                        "peso_total_muestra_g": 80,
                        "talla_promedio": 6.5,
                        "unidad_talla": "cm",
                        "observaciones": PREF,
                    },
                    headers=H(admin),
                    timeout=20,
                )
                check("biometría con talla", r_bio.status_code == 201, r_bio.text[:160])
                track("biometrias", r_bio.json()["id"] if r_bio.status_code == 201 else None)

                r_an = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=H(admin), timeout=20)
                check("análisis 200", r_an.status_code == 200, str(r_an.status_code))
                if r_an.status_code == 200:
                    data = r_an.json()
                    ref = data.get("referencia_produccion")
                    check(
                        "análisis resuelve referencia de la especie",
                        ref is not None and ref.get("id") == ref_id,
                        str(ref),
                    )
                    bios = data.get("biometrias") or []
                    check(
                        "serie de talla en análisis",
                        bios and bios[-1].get("talla_promedio") is not None and bios[-1].get("unidad_talla") == "cm",
                        str(bios[-1] if bios else None),
                    )
                    stats = data.get("estadisticas") or {}
                    check("estadísticas incluyen talla_promedio", "talla_promedio" in stats)
                    ind = data.get("indicadores") or {}
                    talla = ind.get("talla_promedio")
                    check(
                        "indicador talla no es 0 por ausencia",
                        talla is None or (isinstance(talla, (int, float, str)) and float(talla) == 6.5),
                        str(talla),
                    )
                    for fila in bios:
                        for clave in ("peso_promedio_g", "talla_promedio"):
                            val = fila.get(clave)
                            if val is None:
                                continue
                            num = float(val)
                            check(
                                f"sin NaN/Infinity en {clave}",
                                math.isfinite(num),
                                str(val),
                            )

    r_no_tok = requests.get(f"{BASE}/api/v1/especies/", timeout=20)
    check("sin token GET especies 403", r_no_tok.status_code == 403, str(r_no_tok.status_code))
    r_bad_tok = requests.get(
        f"{BASE}/api/v1/especies/",
        headers={"Authorization": "Bearer token-invalido"},
        timeout=20,
    )
    check("token inválido GET especies 401", r_bad_tok.status_code == 401, str(r_bad_tok.status_code))
    r_404 = requests.get(f"{BASE}/api/v1/especies/999999999", headers=H(admin), timeout=20)
    check("especie inexistente 404", r_404.status_code == 404, str(r_404.status_code))

    r_params = requests.get(f"{BASE}/api/v1/parametros-agua/?solo_activos=false", headers=H(admin), timeout=20)
    check("ADMIN GET parametros-agua 200", r_params.status_code == 200)
    textos = []
    param_semilla_id = None
    if r_params.status_code == 200:
        for fila in r_params.json():
            textos.extend(
                [
                    str(fila.get("nombre") or ""),
                    str(fila.get("unidad") or ""),
                    str(fila.get("descripcion") or ""),
                ]
            )
            if param_semilla_id is None and not str(fila.get("nombre") or "").startswith(PREF):
                param_semilla_id = fila["id"]
        mojibake = [t for t in textos if any(m in t for m in ("Ã", "Â", "â", "ï¿½"))]
        check("codificación parámetros de agua sin mojibake", not mojibake, str(mojibake[:8]))
        oxigeno = [fila for fila in r_params.json() if "Oxígeno" in (fila.get("nombre") or "")]
        grado = [fila for fila in r_params.json() if (fila.get("unidad") or "") == "°C"]
        check("Oxígeno disuelto con tilde", len(oxigeno) >= 1, str([f["nombre"] for f in oxigeno]))
        check("unidad °C presente", len(grado) >= 1, str([f.get("unidad") for f in r_params.json()[:8]]))

    r_params_tec = requests.post(
        f"{BASE}/api/v1/parametros-agua/",
        json={"nombre": f"{PREF} param tec", "unidad": "mg/L", "descripcion": "Prueba técnico", "activo": True},
        headers=H(tecnico),
        timeout=20,
    )
    check("POST TECNICO parametro-agua 201", r_params_tec.status_code == 201, str(r_params_tec.status_code))
    if r_params_tec.status_code == 201:
        track("parametros_agua", r_params_tec.json()["id"])

    r_params_op = requests.post(
        f"{BASE}/api/v1/parametros-agua/",
        json={"nombre": f"{PREF} param ope", "unidad": "mg/L", "activo": True},
        headers=H(operario),
        timeout=20,
    )
    check("POST OPERARIO parametro-agua 403", r_params_op.status_code == 403, str(r_params_op.status_code))

    r_params_admin = requests.post(
        f"{BASE}/api/v1/parametros-agua/",
        json={
            "nombre": f"{PREF} param admin",
            "unidad": "mg/L",
            "descripcion": "Concentración de prueba",
            "activo": True,
        },
        headers=H(admin),
        timeout=20,
    )
    check("POST ADMIN parametro-agua 201", r_params_admin.status_code == 201, str(r_params_admin.status_code))
    param_admin_id = r_params_admin.json()["id"] if r_params_admin.status_code == 201 else None
    track("parametros_agua", param_admin_id)
    if param_admin_id:
        r_put_param = requests.put(
            f"{BASE}/api/v1/parametros-agua/{param_admin_id}",
            json={"descripcion": "Concentración actualizada", "activo": True},
            headers=H(admin),
            timeout=20,
        )
        check("PUT ADMIN parametro-agua 200", r_put_param.status_code == 200)
        r_list_param = requests.get(
            f"{BASE}/api/v1/parametros-agua/?solo_activos=false", headers=H(operario), timeout=20
        )
        nombres = [fila["nombre"] for fila in r_list_param.json()] if r_list_param.status_code == 200 else []
        check("parámetro nuevo aparece en GET", f"{PREF} param admin" in nombres, str(nombres[-5:]))

    if especie_id:
        r_list_sp = requests.get(f"{BASE}/api/v1/especies/?solo_activos=false", headers=H(operario), timeout=20)
        nombres_sp = [fila["nombre_comun"] for fila in r_list_sp.json()] if r_list_sp.status_code == 200 else []
        check("especie nueva aparece en selector GET", f"{PREF} especie alfa" in nombres_sp)

        if param_semilla_id:
            r_agua_admin = requests.post(
                f"{BASE}/api/v1/referencias-agua/",
                json={
                    "especie_id": especie_id,
                    "etapa_productiva_id": etapa_id,
                    "parametro_id": param_semilla_id,
                    "valor_minimo": 6.0,
                    "valor_maximo": 8.5,
                    "observaciones": PREF,
                    "activo": True,
                },
                headers=H(admin),
                timeout=20,
            )
            check("POST ADMIN referencia agua 201", r_agua_admin.status_code == 201, r_agua_admin.text[:200])
            agua_id = r_agua_admin.json()["id"] if r_agua_admin.status_code == 201 else None
            track("referencias_agua", agua_id)
            if agua_id:
                r_put_agua = requests.put(
                    f"{BASE}/api/v1/referencias-agua/{agua_id}",
                    json={"observaciones": f"{PREF} agua ok", "activo": True},
                    headers=H(admin),
                    timeout=20,
                )
                check("PUT ADMIN referencia agua 200", r_put_agua.status_code == 200)
                r_list_agua = requests.get(
                    f"{BASE}/api/v1/referencias-agua/?solo_activos=false", headers=H(operario), timeout=20
                )
                ids_agua = [fila["id"] for fila in r_list_agua.json()] if r_list_agua.status_code == 200 else []
                check("referencia de agua nueva aparece", agua_id in ids_agua)

            r_agua_fk = requests.post(
                f"{BASE}/api/v1/referencias-agua/",
                json={
                    "especie_id": 999999999,
                    "etapa_productiva_id": etapa_id,
                    "parametro_id": param_semilla_id,
                    "valor_minimo": 1,
                    "valor_maximo": 2,
                    "observaciones": PREF,
                },
                headers=H(admin),
                timeout=20,
            )
            check("referencia agua especie inventada 404", r_agua_fk.status_code == 404, str(r_agua_fk.status_code))

        r_list_prod = requests.get(
            f"{BASE}/api/v1/referencias-produccion/?solo_activos=false", headers=H(operario), timeout=20
        )
        ids_prod = [fila["id"] for fila in r_list_prod.json()] if r_list_prod.status_code == 200 else []
        check("referencia de producción nueva aparece", ref_id in ids_prod if ref_id else False)

        check(
            "GET 3 roles referencias-biofloc",
            all(
                requests.get(f"{BASE}/api/v1/referencias-biofloc/", headers=H(tok), timeout=20).status_code == 200
                for tok in (admin, tecnico, operario)
            ),
        )
        payload_bio = {
            "especie_id": especie_id,
            "etapa_productiva_id": etapa_id,
            "indicador": "VOLUMEN_SEDIMENTABLE",
            "valor_minimo": 5,
            "valor_objetivo": 15,
            "valor_maximo": 40,
            "unidad": "mL/L",
            "observaciones": PREF,
            "activo": True,
        }
        r_bio_admin = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/", json=payload_bio, headers=H(admin), timeout=20
        )
        check("POST ADMIN referencia biofloc 201", r_bio_admin.status_code == 201, r_bio_admin.text[:220])
        bio_id = r_bio_admin.json()["id"] if r_bio_admin.status_code == 201 else None
        track("referencias_biofloc", bio_id)
        r_bio_tec = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/", json=payload_bio, headers=H(tecnico), timeout=20
        )
        check("POST TECNICO referencia biofloc 403", r_bio_tec.status_code == 403, str(r_bio_tec.status_code))
        r_bio_op = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/", json=payload_bio, headers=H(operario), timeout=20
        )
        check("POST OPERARIO referencia biofloc 403", r_bio_op.status_code == 403)
        if bio_id:
            r_put_bio = requests.put(
                f"{BASE}/api/v1/referencias-biofloc/{bio_id}",
                json={"observaciones": f"{PREF} biofloc", "activo": True},
                headers=H(admin),
                timeout=20,
            )
            check("PUT ADMIN referencia biofloc 200", r_put_bio.status_code == 200)
            r_put_bio_tec = requests.put(
                f"{BASE}/api/v1/referencias-biofloc/{bio_id}",
                json={"activo": False},
                headers=H(tecnico),
                timeout=20,
            )
            check("PUT TECNICO referencia biofloc 403", r_put_bio_tec.status_code == 403)
            r_list_bio = requests.get(
                f"{BASE}/api/v1/referencias-biofloc/?solo_activos=false", headers=H(operario), timeout=20
            )
            ids_bio = [fila["id"] for fila in r_list_bio.json()] if r_list_bio.status_code == 200 else []
            check("referencia Biofloc nueva aparece", bio_id in ids_bio)
        r_bio_dup = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/", json=payload_bio, headers=H(admin), timeout=20
        )
        check("referencia biofloc duplicada 409", r_bio_dup.status_code == 409, str(r_bio_dup.status_code))
        r_bio_rango = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/",
            json={**payload_bio, "indicador": "RELACION_CN", "valor_minimo": 20, "valor_maximo": 5},
            headers=H(admin),
            timeout=20,
        )
        check("referencia biofloc min>max 422", r_bio_rango.status_code == 422, str(r_bio_rango.status_code))
        r_bio_ind = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/",
            json={**payload_bio, "indicador": "CARBONO_INVENTADO"},
            headers=H(admin),
            timeout=20,
        )
        check("indicador biofloc inventado 422", r_bio_ind.status_code == 422, str(r_bio_ind.status_code))
        r_bio_fk = requests.post(
            f"{BASE}/api/v1/referencias-biofloc/",
            json={**payload_bio, "especie_id": 999999999, "indicador": "RELACION_CN"},
            headers=H(admin),
            timeout=20,
        )
        check("referencia biofloc especie inventada 404", r_bio_fk.status_code == 404, str(r_bio_fk.status_code))
        r_bio_404 = requests.get(f"{BASE}/api/v1/referencias-biofloc/999999999", headers=H(admin), timeout=20)
        check("referencia biofloc inexistente 404", r_bio_404.status_code == 404, str(r_bio_404.status_code))

    leftover = cleanup()
    check("LEFTOVER", leftover == 0, str(leftover))
    ok = sum(1 for _, bien, _ in R if bien)
    print(f"\nRESULT {ok}/{len(R)} OK")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
