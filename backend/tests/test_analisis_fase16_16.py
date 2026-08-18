#!/usr/bin/env python3
"""FASE 16.16 — estado analítico explicable.

Prueba el contrato DATOS → REGLA → ESTADO/CUMPLIMIENTO → RECOMENDACIÓN sin
repetir las fórmulas históricas cubiertas por 16.13 y 16.15.
"""
from __future__ import annotations

import io
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import psycopg2
import requests

from env_tests import ADMIN_USER, ADMIN_PASS, DB_CONF

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000"
PREF = "[TEST_F16_16]"
RESULTADOS: list[tuple[str, bool]] = []
IDS: dict[str, list[int]] = {
    tabla: []
    for tabla in [
        "mediciones_agua",
        "mediciones_biofloc",
        "alimentaciones",
        "biometrias",
        "mortalidades",
        "lotes",
        "estanques",
        "productos",
        "referencias_produccion",
        "referencias_agua",
        "parametros_agua",
        "especies",
    ]
}


def check(nombre: str, condicion: bool, detalle="") -> None:
    RESULTADOS.append((nombre, condicion))
    print(f"[{'OK' if condicion else 'FAIL'}] {nombre}" + (f" -> {detalle}" if detalle else ""))


def igual(nombre: str, real, esperado) -> None:
    check(nombre, real == esperado, f"real={real!r} esperado={esperado!r}")


def dec(valor):
    return None if valor is None else Decimal(str(valor))


def conexion():
    return psycopg2.connect(**DB_CONF)


def login() -> str:
    respuesta = requests.post(
        f"{BASE}/api/v1/auth/login",
        json={"correo": ADMIN_USER, "password": ADMIN_PASS},
        timeout=20,
    )
    respuesta.raise_for_status()
    return respuesta.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def limpiar() -> None:
    conn = conexion()
    cur = conn.cursor()
    for tabla in [
        "mediciones_agua",
        "mediciones_biofloc",
        "alimentaciones",
        "biometrias",
        "mortalidades",
        "lotes",
        "estanques",
        "productos",
        "referencias_produccion",
        "referencias_agua",
        "parametros_agua",
        "especies",
    ]:
        if not IDS[tabla]:
            continue
        cur.execute(
            "DELETE FROM biofloc.auditoria WHERE tabla=%s AND registro_id=ANY(%s)",
            (tabla, IDS[tabla]),
        )
        cur.execute(f"DELETE FROM biofloc.{tabla} WHERE id=ANY(%s)", (IDS[tabla],))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{PREF}%",))
    conn.commit()
    cur.close()
    conn.close()


def leftover() -> int:
    conn = conexion()
    cur = conn.cursor()
    patron = f"%{PREF}%"
    consultas = [
        ("SELECT count(*) FROM biofloc.lotes WHERE codigo LIKE %s OR observaciones LIKE %s", (patron, patron)),
        ("SELECT count(*) FROM biofloc.estanques WHERE codigo LIKE %s OR nombre LIKE %s", (patron, patron)),
        ("SELECT count(*) FROM biofloc.especies WHERE nombre_comun LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.parametros_agua WHERE nombre LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.referencias_produccion WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.referencias_agua WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.productos WHERE nombre LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.biometrias WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.mortalidades WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.alimentaciones WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.mediciones_agua WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.mediciones_biofloc WHERE observaciones LIKE %s", (patron,)),
        ("SELECT count(*) FROM biofloc.auditoria WHERE detalle::text LIKE %s", (patron,)),
    ]
    total = 0
    for sql, params in consultas:
        cur.execute(sql, params)
        total += int(cur.fetchone()[0])
    cur.close()
    conn.close()
    return total


class Ambiente:
    def __init__(self, marca: str):
        conn = conexion()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO biofloc.especies(nombre_comun,nombre_cientifico,activo) "
            "VALUES(%s,'Testus explicabilis',TRUE) RETURNING id",
            (f"{PREF} especie {marca}",),
        )
        self.especie = cur.fetchone()[0]
        IDS["especies"].append(self.especie)
        cur.execute("SELECT id FROM biofloc.etapas_productivas ORDER BY orden LIMIT 1")
        self.etapa = cur.fetchone()[0]
        cur.execute("SELECT id FROM biofloc.estados_estanque WHERE nombre='DISPONIBLE'")
        self.estado_estanque = cur.fetchone()[0]
        cur.execute("SELECT id FROM biofloc.estados_lote WHERE nombre='ACTIVO'")
        self.estado_lote = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO biofloc.referencias_produccion
                (especie_id,etapa_productiva_id,semana_desde,semana_hasta,
                 peso_esperado_g,tasa_alimentacion_pct,observaciones,activo)
            VALUES(%s,%s,1,4,20,4,%s,TRUE) RETURNING id
            """,
            (self.especie, self.etapa, PREF),
        )
        IDS["referencias_produccion"].append(cur.fetchone()[0])

        self.parametros = []
        for nombre, con_ref in [("Dentro", True), ("Fuera", True), ("Sin referencia", False)]:
            cur.execute(
                "INSERT INTO biofloc.parametros_agua(nombre,unidad,activo) "
                "VALUES(%s,'mg/L',TRUE) RETURNING id",
                (f"{PREF} {nombre} {marca}",),
            )
            parametro = cur.fetchone()[0]
            IDS["parametros_agua"].append(parametro)
            self.parametros.append(parametro)
            if con_ref:
                cur.execute(
                    """
                    INSERT INTO biofloc.referencias_agua
                        (especie_id,etapa_productiva_id,parametro_id,
                         valor_minimo,valor_maximo,observaciones,activo)
                    VALUES(%s,%s,%s,5,8,%s,TRUE) RETURNING id
                    """,
                    (self.especie, self.etapa, parametro, PREF),
                )
                IDS["referencias_agua"].append(cur.fetchone()[0])

        cur.execute("SELECT id FROM biofloc.categorias_inventario ORDER BY id LIMIT 1")
        categoria = cur.fetchone()[0]
        cur.execute("SELECT id FROM biofloc.unidades WHERE simbolo='kg' LIMIT 1")
        unidad = cur.fetchone()[0]
        cur.execute(
            """
            INSERT INTO biofloc.productos
                (codigo,nombre,categoria_id,unidad_id,stock_minimo,activo)
            VALUES(%s,%s,%s,%s,0,TRUE) RETURNING id
            """,
            (f"F1616-{marca}", f"{PREF} alimento", categoria, unidad),
        )
        self.producto = cur.fetchone()[0]
        IDS["productos"].append(self.producto)
        conn.commit()
        cur.close()
        conn.close()


def post(token: str, ruta: str, tabla: str, payload: dict) -> int:
    respuesta = requests.post(
        f"{BASE}{ruta}", headers=headers(token), json=payload, timeout=20
    )
    if respuesta.status_code != 201:
        raise RuntimeError(f"{ruta}: {respuesta.status_code} {respuesta.text[:300]}")
    ident = respuesta.json()["id"]
    IDS[tabla].append(ident)
    return ident


def crear_lote(token: str, amb: Ambiente, marca: str, dias: int, peso: Decimal | None) -> int:
    estanque = post(
        token,
        "/api/v1/estanques/",
        "estanques",
        {
            "codigo": f"{PREF}-{marca}",
            "nombre": f"{PREF} {marca}",
            "diametro": 8,
            "profundidad": 1.2,
            "estado_id": amb.estado_estanque,
            "activo": True,
        },
    )
    lote = post(
        token,
        "/api/v1/lotes/",
        "lotes",
        {
            "codigo": f"{PREF}-L-{marca}",
            "estanque_id": estanque,
            "especie_id": amb.especie,
            "etapa_productiva_id": amb.etapa,
            "estado_id": amb.estado_lote,
            "fecha_siembra": (date.today() - timedelta(days=dias)).isoformat(),
            "cantidad_sembrada": 1000,
            "peso_inicial_promedio_g": 5,
            "observaciones": PREF,
        },
    )
    if peso is not None:
        post(
            token,
            "/api/v1/biometrias/",
            "biometrias",
            {
                "lote_id": lote,
                "fecha_hora": datetime.now(timezone.utc).isoformat(),
                "cantidad_muestra": 10,
                "peso_total_muestra_g": str(peso * 10),
                "observaciones": PREF,
            },
        )
    return lote


def evaluaciones(cuerpo: dict) -> dict[str, dict]:
    return {fila["indicador"]: fila for fila in cuerpo["evaluaciones"]}


def main() -> int:
    token = login()
    marca = datetime.now(timezone.utc).strftime("%H%M%S")
    amb = Ambiente(marca)
    ahora = datetime.now(timezone.utc)

    lote_menor = crear_lote(token, amb, f"MEN-{marca}", 10, Decimal("15"))
    lote_igual = crear_lote(token, amb, f"IGU-{marca}", 10, Decimal("20"))
    lote_mayor = crear_lote(token, amb, f"MAY-{marca}", 10, Decimal("30"))
    lote_sin_obj = crear_lote(token, amb, f"SINOBJ-{marca}", 70, Decimal("30"))
    lote_vacio = crear_lote(token, amb, f"VAC-{marca}", 10, None)

    for parametro, valor in zip(amb.parametros, [6, 3, 7]):
        post(
            token,
            "/api/v1/mediciones-agua/",
            "mediciones_agua",
            {
                "lote_id": lote_mayor,
                "parametro_id": parametro,
                "fecha_hora": ahora.isoformat(),
                "valor": valor,
                "observaciones": PREF,
            },
        )
    post(
        token,
        "/api/v1/alimentaciones/",
        "alimentaciones",
        {
            "lote_id": lote_mayor,
            "producto_id": amb.producto,
            "fecha_hora": ahora.isoformat(),
            "cantidad": 5,
            "observaciones": PREF,
        },
    )
    post(
        token,
        "/api/v1/mortalidades/",
        "mortalidades",
        {
            "lote_id": lote_mayor,
            "fecha_hora": ahora.isoformat(),
            "cantidad": 10,
            "observaciones": PREF,
        },
    )
    post(
        token,
        "/api/v1/mediciones-biofloc/",
        "mediciones_biofloc",
        {
            "lote_id": lote_mayor,
            "fecha_hora": ahora.isoformat(),
            "volumen_sedimentable": 12,
            "unidad": "mL/L",
            "relacion_cn": 10,
            "observaciones": PREF,
        },
    )

    conn = conexion()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.alarmas")
    alarmas_antes = int(cur.fetchone()[0])
    cur.close()
    conn.close()

    cuerpos = {}
    for nombre, lote in [
        ("menor", lote_menor),
        ("igual", lote_igual),
        ("mayor", lote_mayor),
        ("sin_obj", lote_sin_obj),
        ("vacio", lote_vacio),
    ]:
        respuesta = requests.get(
            f"{BASE}/api/v1/analisis/lotes/{lote}", headers=headers(token), timeout=30
        )
        igual(f"GET {nombre}", respuesta.status_code, 200)
        cuerpos[nombre] = respuesta.json()

    ev_menor = evaluaciones(cuerpos["menor"])["peso_promedio_g"]
    ev_igual = evaluaciones(cuerpos["igual"])["peso_promedio_g"]
    ev_mayor = evaluaciones(cuerpos["mayor"])["peso_promedio_g"]
    ev_sin_obj = evaluaciones(cuerpos["sin_obj"])["peso_promedio_g"]
    igual("peso menor: diferencia", dec(ev_menor["diferencia_objetivo"]), Decimal("-5.000000"))
    igual("peso menor: desviación", dec(ev_menor["diferencia_objetivo_porcentaje"]), Decimal("-25.00"))
    igual("peso igual: diferencia cero", dec(ev_igual["diferencia_objetivo"]), Decimal("0.000000"))
    igual("peso mayor: diferencia", dec(ev_mayor["diferencia_objetivo"]), Decimal("10.000000"))
    igual("peso no se clasifica por el signo", ev_mayor["estado_analitico"], None)
    igual("peso sin objetivo", ev_sin_obj["estado_analitico"], "SIN_REFERENCIA")
    igual("peso sin objetivo no inventa rango", (ev_sin_obj["minimo"], ev_sin_obj["maximo"]), (None, None))

    ev = evaluaciones(cuerpos["mayor"])
    agua_dentro = ev[f"agua:{amb.parametros[0]}"]
    agua_fuera = ev[f"agua:{amb.parametros[1]}"]
    agua_sin_ref = ev[f"agua:{amb.parametros[2]}"]
    igual(
        "agua dentro de rango sin estado de severidad",
        (agua_dentro["cumplimiento_rango"], agua_dentro["estado_analitico"]),
        ("DENTRO_RANGO", None),
    )
    igual("agua fuera de rango sin severidad", (agua_fuera["cumplimiento_rango"], agua_fuera["estado_analitico"]), ("FUERA_RANGO", None))
    igual("agua desviación contra mínimo", dec(agua_fuera["desviacion_rango"]), Decimal("-2.000000"))
    igual("agua objetivo explícitamente null", agua_fuera["objetivo"], None)
    igual("agua sin referencia", (agua_sin_ref["estado_analitico"], agua_sin_ref["cumplimiento_rango"]), ("SIN_REFERENCIA", "NO_EVALUABLE"))
    check("no se emitió ALERTA/CRITICO", all(f["estado_analitico"] not in {"ALERTA", "CRITICO"} for f in cuerpos["mayor"]["evaluaciones"]))

    alimento = ev["alimentacion_diaria_kg"]
    igual("alimentación último día real", dec(alimento["real"]), Decimal("5.000000"))
    igual("alimentación recomendada actual", dec(alimento["objetivo"]), Decimal("1.188000"))
    igual("alimentación diferencia backend", dec(alimento["diferencia_objetivo"]), Decimal("3.812000"))
    check("alimentación informa ambas fechas", alimento["fecha_real"] is not None and alimento["fecha_referencia"] is not None)

    igual("FCA disponible solo como real", (ev["fca"]["real"] is not None, ev["fca"]["objetivo"]), (True, None))
    igual("FCA disponible queda sin referencia", ev["fca"]["estado_analitico"], "SIN_REFERENCIA")
    ev_vacio = evaluaciones(cuerpos["vacio"])
    igual("FCA no disponible", ev_vacio["fca"]["estado_analitico"], "SIN_DATOS")
    igual("mortalidad sin referencia", ev["mortalidad_porcentaje"]["estado_analitico"], "SIN_REFERENCIA")
    igual("supervivencia sin referencia", ev["supervivencia_porcentaje"]["estado_analitico"], "SIN_REFERENCIA")
    igual("biofloc sin referencia", ev["volumen_sedimentable"]["estado_analitico"], "SIN_REFERENCIA")
    igual("C:N sin referencia", ev["relacion_cn"]["estado_analitico"], "SIN_REFERENCIA")
    igual("lote vacío: agua sin datos", ev_vacio["agua"]["estado_analitico"], "SIN_DATOS")
    igual("lote vacío: peso sin datos", ev_vacio["peso_promedio_g"]["estado_analitico"], "SIN_DATOS")

    recomendaciones = cuerpos["mayor"]["recomendaciones"]
    igual("una recomendación por agua fuera", len(recomendaciones), 1)
    igual("recomendación trazable", recomendaciones[0]["cumplimiento_rango"], "FUERA_RANGO")
    check(
        "recomendación no inventa cantidad",
        all(
            unidad not in recomendaciones[0]["recomendacion"].lower()
            for unidad in [" kg", " mg", " ml", " %"]
        ),
    )
    igual("lote vacío sin recomendaciones", cuerpos["vacio"]["recomendaciones"], [])

    conn = conexion()
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM biofloc.alarmas")
    alarmas_despues = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    igual("GET analítico no crea alarmas", alarmas_despues, alarmas_antes)

    limpiar()
    igual("leftover = 0", leftover(), 0)
    fallos = [nombre for nombre, ok in RESULTADOS if not ok]
    print(f"\nRESULT {len(RESULTADOS) - len(fallos)}/{len(RESULTADOS)} OK")
    if fallos:
        print("FAILED:", "; ".join(fallos))
        return 1
    return 0


if __name__ == "__main__":
    try:
        salida = main()
    except Exception as exc:  # noqa: BLE001
        print("EXC", type(exc).__name__, str(exc))
        try:
            limpiar()
        except Exception:  # noqa: BLE001
            pass
        salida = 1
    raise SystemExit(salida)
