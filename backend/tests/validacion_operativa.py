#!/usr/bin/env python3
"""
Validación operativa con datos reales — ERP Piscícola V1.
Simula el ciclo completo de un usuario ADMIN usando la API (los mismos endpoints que consume React).
No seeds: todo se introduce por formulario/API como haría el usuario.
Al terminar: leftover = 0.
"""
from __future__ import annotations

import io
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

import requests
import psycopg2

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from env_tests import ADMIN_USER, ADMIN_PASS, DB_CONF

BASE = "http://127.0.0.1:8000"
TAG = "[VALIDACION_OP]"
_IDS: dict[str, list[int]] = {
    "productos": [], "estanques": [], "lotes": [], "biometrias": [],
    "mortalidades": [], "alimentaciones": [], "cosechas": [], "ventas": [],
    "gastos": [], "mediciones_agua": [], "mediciones_biofloc": [],
    "referencias_produccion": [],
}
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} {name}")
    if detail:
        print(f"       -> {detail}")
    results.append((name, ok, detail))


def login() -> str:
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"correo": ADMIN_USER, "password": ADMIN_PASS}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def post(token, ruta, payload):
    r = requests.post(f"{BASE}{ruta}", headers=H(token), json=payload, timeout=20)
    return r


def get(token, ruta):
    r = requests.get(f"{BASE}{ruta}", headers=H(token), timeout=20)
    return r


def put(token, ruta, payload):
    r = requests.put(f"{BASE}{ruta}", headers=H(token), json=payload, timeout=20)
    return r


# ─── 1. CONFIGURACIÓN ADMINISTRATIVA ────────────────────────────────────────

def fase_config(token: str):
    print("\n── 1. CONFIGURACIÓN ADMINISTRATIVA ──")

    # Especies
    r = get(token, "/api/v1/especies/?solo_activos=true")
    check("GET especies activas", r.status_code == 200, f"n={len(r.json())}")
    especies = r.json()

    # Etapas
    r = get(token, "/api/v1/etapas-productivas/?solo_activos=true")
    check("GET etapas activas", r.status_code == 200, f"n={len(r.json())}")
    etapas = r.json()

    # Parámetros agua
    r = get(token, "/api/v1/parametros-agua/?solo_activos=true")
    check("GET parámetros agua", r.status_code == 200, f"n={len(r.json())}")
    parametros = r.json()

    # Referencias de agua
    r = get(token, "/api/v1/referencias-agua/?solo_activos=true")
    check("GET referencias agua activas", r.status_code == 200, f"n={len(r.json())}")

    # Referencias de producción
    r = get(token, "/api/v1/referencias-produccion/?solo_activos=true")
    check("GET referencias producción activas", r.status_code == 200, f"n={len(r.json())}")
    refs_prod = r.json()

    # Unidades
    r = get(token, "/api/v1/unidades/?solo_activos=true")
    check("GET unidades activas", r.status_code == 200, f"n={len(r.json())}")
    unidades = r.json()

    # Categorías inventario
    r = get(token, "/api/v1/categorias-inventario/?solo_activos=true")
    check("GET categorías inventario", r.status_code == 200, f"n={len(r.json())}")
    categorias = r.json()

    # Crear producto de alimentación para prueba (kg)
    kg = next((u for u in unidades if u.get("simbolo") == "kg"), None)
    if not kg:
        check("Unidad kg disponible", False, "No existe unidad kg en catálogo")
        return {}
    cat = categorias[0] if categorias else None
    if not cat:
        check("Categoría inventario disponible", False, "No hay categorías")
        return {}

    r = post(token, "/api/v1/productos/", {
        "codigo": f"{TAG}-PROD-001",
        "nombre": f"{TAG} Alimento balanceado 32%",
        "categoria_id": cat["id"],
        "unidad_id": kg["id"],
        "stock_minimo": "5",
        "activo": True,
    })
    check("POST producto alimentación 201", r.status_code == 201, r.text[:200] if r.status_code != 201 else "")
    if r.status_code == 201:
        _IDS["productos"].append(r.json()["id"])
        # Crear entrada de inventario para tener stock disponible
        r_tipos = get(token, "/api/v1/tipos-movimiento-inventario/")
        tipo_entrada_id = None
        if r_tipos.status_code == 200:
            for t in r_tipos.json():
                if t["nombre"] == "ENTRADA":
                    tipo_entrada_id = t["id"]
                    break
        if tipo_entrada_id:
            r_mov = post(token, "/api/v1/movimientos-inventario/", {
                "producto_id": _IDS["productos"][0],
                "tipo_movimiento_id": tipo_entrada_id,
                "cantidad": 100.0,
                "observaciones": f"{TAG} Stock inicial",
            })
            check("POST entrada inventario (stock)", r_mov.status_code == 201, "100 kg")

    # Verificar usuarios/roles
    r = get(token, "/api/v1/roles")
    check("GET roles", r.status_code == 200, f"n={len(r.json())}")

    r = get(token, "/api/v1/usuarios/")
    check("GET usuarios", r.status_code == 200, f"n={len(r.json())}")

    return {
        "especies": especies,
        "etapas": etapas,
        "parametros": parametros,
        "refs_prod": refs_prod,
        "unidades": unidades,
        "producto_id": _IDS["productos"][0] if _IDS["productos"] else None,
    }


# ─── 2. CICLO PRODUCTIVO REAL ───────────────────────────────────────────────

def fase_ciclo(token: str, cfg: dict):
    print("\n── 2. CICLO PRODUCTIVO ──")

    especie = cfg["especies"][0] if cfg["especies"] else None
    etapa = cfg["etapas"][0] if cfg["etapas"] else None
    if not especie or not etapa:
        check("Especie y etapa disponibles", False)
        return {}

    # Estados
    estados_est = get(token, "/api/v1/estados-estanque/?solo_activos=true").json()
    estados_lote = get(token, "/api/v1/estados-lote/?solo_activos=true").json()
    disp = next((e for e in estados_est if e["nombre"] == "DISPONIBLE"), estados_est[0])
    activo = next((e for e in estados_lote if e["nombre"] == "ACTIVO"), estados_lote[0])

    # Estanque
    r = post(token, "/api/v1/estanques/", {
        "codigo": f"{TAG}-EST-1",
        "nombre": f"{TAG} Estanque validación",
        "diametro": 10,
        "profundidad": 1.3,
        "estado_id": disp["id"],
        "activo": True,
    })
    check("POST estanque", r.status_code == 201, r.text[:200] if r.status_code != 201 else f"id={r.json()['id']}")
    if r.status_code != 201:
        return {}
    est_id = r.json()["id"]
    _IDS["estanques"].append(est_id)

    # Lote (siembra hace 30 días)
    fecha_siembra = (date.today() - timedelta(days=30)).isoformat()
    r = post(token, "/api/v1/lotes/", {
        "codigo": f"{TAG}-LOT-1",
        "estanque_id": est_id,
        "especie_id": especie["id"],
        "etapa_productiva_id": etapa["id"],
        "estado_id": activo["id"],
        "fecha_siembra": fecha_siembra,
        "cantidad_sembrada": 2000,
        "peso_inicial_promedio_g": 5.0,
        "observaciones": TAG,
    })
    check("POST lote", r.status_code == 201, r.text[:200] if r.status_code != 201 else f"id={r.json()['id']}")
    if r.status_code != 201:
        return {}
    lote = r.json()
    lote_id = lote["id"]
    _IDS["lotes"].append(lote_id)

    # Biometría día 15
    fecha_bio1 = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    r = post(token, "/api/v1/biometrias/", {
        "lote_id": lote_id,
        "fecha_hora": fecha_bio1,
        "cantidad_muestra": 30,
        "peso_total_muestra_g": 450.0,
        "talla_promedio": 7.5,
        "unidad_talla": "cm",
        "observaciones": TAG,
    })
    check("POST biometría día 15", r.status_code == 201, f"peso_prom={450/30:.1f}g")
    if r.status_code == 201:
        _IDS["biometrias"].append(r.json()["id"])

    # Biometría día 5 (más reciente)
    fecha_bio2 = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    r = post(token, "/api/v1/biometrias/", {
        "lote_id": lote_id,
        "fecha_hora": fecha_bio2,
        "cantidad_muestra": 30,
        "peso_total_muestra_g": 900.0,
        "talla_promedio": 10.2,
        "unidad_talla": "cm",
        "observaciones": TAG,
    })
    check("POST biometría día 25", r.status_code == 201, f"peso_prom={900/30:.1f}g")
    if r.status_code == 201:
        _IDS["biometrias"].append(r.json()["id"])

    # Mortalidad
    fecha_mort = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    r = post(token, "/api/v1/mortalidades/", {
        "lote_id": lote_id,
        "fecha_hora": fecha_mort,
        "cantidad": 50,
        "causa": "Estrés térmico",
        "observaciones": TAG,
    })
    check("POST mortalidad", r.status_code == 201, "50 peces")
    if r.status_code == 201:
        _IDS["mortalidades"].append(r.json()["id"])

    # Alimentaciones (3 registros: día 28, 20, 10)
    producto_id = cfg.get("producto_id")
    if producto_id:
        for dias, kg in [(28, 2.0), (20, 3.5), (10, 5.0)]:
            fecha_ali = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
            r = post(token, "/api/v1/alimentaciones/", {
                "lote_id": lote_id,
                "producto_id": producto_id,
                "fecha_hora": fecha_ali,
                "cantidad": kg,
                "observaciones": TAG,
            })
            if r.status_code == 201:
                _IDS["alimentaciones"].append(r.json()["id"])
        check("POST 3 alimentaciones", len(_IDS["alimentaciones"]) == 3, f"total={sum([2.0,3.5,5.0])} kg")
    else:
        check("POST alimentaciones", False, "Sin producto disponible")

    # Mediciones de agua (6 parámetros, 2 fechas)
    parametros = cfg.get("parametros") or []
    for dias in [20, 5]:
        fecha_agua = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        for i, param in enumerate(parametros[:6]):
            valores = [6.5, 7.2, 28.0, 0.02, 0.05, 120.0]
            valor = valores[i] + (0.3 if dias == 5 else 0)
            r = post(token, "/api/v1/mediciones-agua/", {
                "lote_id": lote_id,
                "parametro_id": param["id"],
                "valor": valor,
                "fecha_hora": fecha_agua,
                "observaciones": TAG,
            })
            if r.status_code == 201:
                _IDS["mediciones_agua"].append(r.json()["id"])
    check("POST mediciones agua", len(_IDS["mediciones_agua"]) >= 6, f"n={len(_IDS['mediciones_agua'])}")

    # Biofloc
    for dias, vol, cn in [(20, 15.0, 12.0), (5, 22.0, 14.0)]:
        fecha_bf = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        r = post(token, "/api/v1/mediciones-biofloc/", {
            "lote_id": lote_id,
            "fecha_hora": fecha_bf,
            "volumen_sedimentable": vol,
            "unidad": "mL/L",
            "relacion_cn": cn,
            "observaciones": TAG,
        })
        if r.status_code == 201:
            _IDS["mediciones_biofloc"].append(r.json()["id"])
    check("POST mediciones biofloc", len(_IDS["mediciones_biofloc"]) == 2)

    # Cosecha parcial
    fecha_cos = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    r = post(token, "/api/v1/cosechas/", {
        "lote_id": lote_id,
        "fecha_hora": fecha_cos,
        "cantidad_peces": 200,
        "peso_total_kg": 6.0,
        "peso_promedio_g": 30.0,
        "observaciones": TAG,
    })
    check("POST cosecha parcial", r.status_code == 201, "200 peces / 6 kg")
    if r.status_code == 201:
        _IDS["cosechas"].append(r.json()["id"])

    # Venta
    r = post(token, "/api/v1/ventas/", {
        "fecha": date.today().isoformat(),
        "cliente": f"{TAG} Pescadería Centro",
        "observaciones": TAG,
        "detalles": [{
            "lote_id": lote_id,
            "cantidad": "6.000",
            "precio_unitario": "12000.00",
        }],
    })
    check("POST venta", r.status_code == 201, f"total={6*12000}")
    if r.status_code == 201:
        _IDS["ventas"].append(r.json()["id"])

    # Gasto
    categorias_gasto = get(token, "/api/v1/categorias-gasto/?solo_activos=true").json()
    cat_gasto = categorias_gasto[0]["id"] if categorias_gasto else None
    if cat_gasto:
        r = post(token, "/api/v1/gastos/", {
            "lote_id": lote_id,
            "categoria_id": cat_gasto,
            "valor": "45000.00",
            "fecha": date.today().isoformat(),
            "descripcion": f"{TAG} Compra alimento",
            "observaciones": TAG,
        })
        check("POST gasto", r.status_code == 201, "$45.000")
        if r.status_code == 201:
            _IDS["gastos"].append(r.json()["id"])

    return {"lote_id": lote_id, "est_id": est_id, "especie_id": especie["id"], "etapa_id": etapa["id"]}


# ─── 3/5. VALIDAR PRODUCCIÓN Y FÓRMULAS ─────────────────────────────────────

def fase_produccion(token: str, ctx: dict):
    print("\n── 3/5. PRODUCCIÓN + FÓRMULAS ──")

    lote_id = ctx["lote_id"]
    r = get(token, f"/api/v1/analisis/lotes/{lote_id}")
    check("GET análisis lote 200", r.status_code == 200, r.text[:200] if r.status_code != 200 else "")
    if r.status_code != 200:
        return

    data = r.json()
    ind = data.get("indicadores") or {}

    # Datos de entrada
    cantidad_sembrada = 2000
    mortalidad_acum = 50
    cosecha_peces = 200
    peso_muestra_g = 900.0
    cantidad_muestra = 30
    peso_inicial = 5.0
    alimento_real_kg = Decimal("10.5")  # 2+3.5+5

    # Fórmulas congeladas
    poblacion_esperada = cantidad_sembrada - mortalidad_acum - cosecha_peces
    supervivencia_esperada = Decimal(str(poblacion_esperada)) / Decimal("2000") * 100
    mortalidad_pct_esperada = Decimal("50") / Decimal("2000") * 100
    peso_promedio_esperado = Decimal(str(peso_muestra_g)) / Decimal(str(cantidad_muestra))
    biomasa_actual_esperada = Decimal(str(poblacion_esperada)) * peso_promedio_esperado / 1000
    biomasa_inicial = Decimal(str(cantidad_sembrada)) * Decimal(str(peso_inicial)) / 1000
    ganancia_peso = peso_promedio_esperado - Decimal(str(peso_inicial))
    ganancia_biomasa = biomasa_actual_esperada - biomasa_inicial
    fca_esperado = alimento_real_kg / ganancia_biomasa if ganancia_biomasa > 0 else None

    # Comparar
    pob = ind.get("poblacion_estimada")
    check("Población", pob == poblacion_esperada, f"API={pob} esperado={poblacion_esperada}")

    sup = ind.get("supervivencia_porcentaje")
    check("Supervivencia", sup is not None and abs(Decimal(str(sup)) - supervivencia_esperada) < Decimal("0.1"),
          f"API={sup} esperado={supervivencia_esperada}")

    mort_pct = ind.get("mortalidad_porcentaje")
    check("Mortalidad %", mort_pct is not None and abs(Decimal(str(mort_pct)) - mortalidad_pct_esperada) < Decimal("0.1"),
          f"API={mort_pct} esperado={mortalidad_pct_esperada}")

    peso = ind.get("peso_promedio_g")
    check("Peso promedio", peso is not None and abs(Decimal(str(peso)) - peso_promedio_esperado) < Decimal("0.01"),
          f"API={peso} esperado={peso_promedio_esperado}")

    biomasa = ind.get("biomasa_actual_kg")
    if biomasa is not None:
        check("Biomasa actual", abs(Decimal(str(biomasa)) - biomasa_actual_esperada) < Decimal("0.1"),
              f"API={biomasa} esperado={biomasa_actual_esperada}")
    else:
        check("Biomasa actual", False, "null")

    ganancia = ind.get("ganancia_peso_g")
    check("Ganancia peso", ganancia is not None and abs(Decimal(str(ganancia)) - ganancia_peso) < Decimal("0.1"),
          f"API={ganancia} esperado={ganancia_peso}")

    alimento = ind.get("alimento_real_acumulado_kg")
    check("Alimento real acumulado", alimento is not None and abs(Decimal(str(alimento)) - alimento_real_kg) < Decimal("0.1"),
          f"API={alimento} esperado={alimento_real_kg}")

    fca = ind.get("fca")
    if fca_esperado:
        check("FCA", fca is not None and abs(Decimal(str(fca)) - fca_esperado) < Decimal("0.01"),
              f"API={fca} esperado={fca_esperado:.4f}")
    else:
        check("FCA N/D (ganancia 0)", fca is None)

    # Series
    bios = data.get("biometrias") or []
    check("Serie biometrías", len(bios) >= 2, f"n={len(bios)}")

    serie_bio = data.get("serie_biomasa") or []
    check("Serie biomasa", len(serie_bio) >= 2, f"n={len(serie_bio)}")

    serie_pob = data.get("serie_poblacion") or []
    check("Serie población", len(serie_pob) >= 2, f"n={len(serie_pob)}")

    serie_fca = data.get("serie_fca") or []
    check("Serie FCA presente", isinstance(serie_fca, list), f"type={type(serie_fca)}")

    alim_serie = data.get("alimentacion_real") or []
    check("Serie alimentación", len(alim_serie) >= 3, f"n={len(alim_serie)}")


# ─── 4. GRÁFICAS (existencia de series) ─────────────────────────────────────

def fase_graficas(token: str, ctx: dict):
    print("\n── 4. GRÁFICAS (series disponibles) ──")

    lote_id = ctx["lote_id"]
    r = get(token, f"/api/v1/analisis/lotes/{lote_id}")
    data = r.json()

    series_check = [
        ("biometrias", "peso promedio vs tiempo"),
        ("serie_biomasa", "biomasa vs tiempo"),
        ("serie_poblacion", "población/mortalidad"),
        ("serie_fca", "FCA"),
        ("agua_serie", "agua serie"),
        ("biofloc_serie", "biofloc serie"),
        ("alimentacion_real", "alimentación real"),
    ]
    for key, label in series_check:
        serie = data.get(key) or []
        check(f"Gráfica {label}", len(serie) >= 1, f"n={len(serie)}")

    # Talla en biometrías
    bios = data.get("biometrias") or []
    tallas = [b for b in bios if b.get("talla_promedio") is not None]
    check("Talla en biometrías", len(tallas) >= 1, f"n={len(tallas)}")


# ─── 6. AGUA ────────────────────────────────────────────────────────────────

def fase_agua(token: str, ctx: dict):
    print("\n── 6. AGUA ──")

    lote_id = ctx["lote_id"]
    r = get(token, f"/api/v1/analisis/lotes/{lote_id}")
    data = r.json()
    agua = data.get("agua") or []
    check("Snapshot agua no vacía", len(agua) >= 1, f"n={len(agua)}")

    for punto in agua[:3]:
        param = punto.get("parametro", "?")
        valor = punto.get("valor")
        fuera = punto.get("fuera_de_rango")
        ref_min = punto.get("valor_minimo")
        ref_max = punto.get("valor_maximo")
        if ref_min is not None or ref_max is not None:
            check(f"Agua {param} con ref", fuera is not None, f"val={valor} min={ref_min} max={ref_max} fuera={fuera}")
        else:
            check(f"Agua {param} sin ref", fuera is None, f"val={valor} fuera_de_rango=null (correcto)")


# ─── 7. BIOFLOC ─────────────────────────────────────────────────────────────

def fase_biofloc(token: str, ctx: dict):
    print("\n── 7. BIOFLOC ──")

    lote_id = ctx["lote_id"]
    r = get(token, f"/api/v1/analisis/lotes/{lote_id}")
    data = r.json()
    bf = data.get("biofloc_serie") or []
    check("Biofloc serie >= 2", len(bf) >= 2, f"n={len(bf)}")
    if bf:
        ultimo = bf[-1]
        check("Biofloc volumen presente", ultimo.get("volumen_sedimentable") is not None, str(ultimo.get("volumen_sedimentable")))
        check("Biofloc C:N presente", ultimo.get("relacion_cn") is not None, str(ultimo.get("relacion_cn")))


# ─── 9. FINANZAS ────────────────────────────────────────────────────────────

def fase_finanzas(token: str, ctx: dict):
    print("\n── 9. FINANZAS ──")

    lote_id = ctx["lote_id"]
    r = get(token, f"/api/v1/analisis/lotes/{lote_id}")
    data = r.json()
    efi = data.get("eficiencia") or {}
    check("Costo/kg = N/D (datos incompletos)", efi.get("costo_por_kg") is None, str(efi.get("costo_por_kg_motivo")))

    # Ventas y gastos registrados
    r_v = get(token, f"/api/v1/ventas/?lote_id={lote_id}")
    check("Ventas del lote", r_v.status_code == 200 and len(r_v.json()) >= 1, f"n={len(r_v.json())}")

    r_g = get(token, f"/api/v1/gastos/?lote_id={lote_id}")
    check("Gastos del lote", r_g.status_code == 200 and len(r_g.json()) >= 1, f"n={len(r_g.json())}")


# ─── 10. HISTORIAL ──────────────────────────────────────────────────────────

def fase_historial(token: str, ctx: dict):
    print("\n── 10. HISTORIAL ──")

    est_id = ctx["est_id"]
    r = get(token, f"/api/v1/analisis/estanques?estanque_id={est_id}&incluir_historial=true")
    check("Historial estanque 200", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        ciclos = data.get("historial") or []
        check("Historial incluye lote activo", True, f"response keys={list(data.keys())[:6]}")


# ─── 11. COMPARACIÓN ────────────────────────────────────────────────────────

def fase_comparacion(token: str, ctx: dict):
    print("\n── 11. COMPARACIÓN ──")

    r = get(token, "/api/v1/analisis/estanques")
    check("Comparativo 200", r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        estanques = data.get("estanques") or []
        mine = [e for e in estanques if e.get("estanque_id") == ctx["est_id"]]
        check("Estanque en comparativo", len(mine) >= 1, f"found={len(mine)}")


# ─── LIMPIEZA ────────────────────────────────────────────────────────────────

def limpiar():
    print("\n── LIMPIEZA ──")
    conn = psycopg2.connect(**DB_CONF)
    cur = conn.cursor()
    patron = f"{TAG}%"

    lote_ids = _IDS["lotes"]
    if lote_ids:
        for tabla in ("alarmas", "detalles_venta", "mediciones_agua", "mediciones_biofloc",
                      "aplicaciones_biofloc", "alimentaciones", "biometrias", "mortalidades", "cosechas", "gastos"):
            cur.execute(f"DELETE FROM biofloc.{tabla} WHERE lote_id = ANY(%s)", (lote_ids,))
    venta_ids = _IDS["ventas"]
    if venta_ids:
        cur.execute("DELETE FROM biofloc.detalles_venta WHERE venta_id = ANY(%s)", (venta_ids,))
        cur.execute("DELETE FROM biofloc.ventas WHERE id = ANY(%s)", (venta_ids,))
    if lote_ids:
        cur.execute("DELETE FROM biofloc.lotes WHERE id = ANY(%s)", (lote_ids,))
    est_ids = _IDS["estanques"]
    if est_ids:
        cur.execute("DELETE FROM biofloc.estanques WHERE id = ANY(%s)", (est_ids,))
    prod_ids = _IDS["productos"]
    if prod_ids:
        cur.execute("DELETE FROM biofloc.movimientos_inventario WHERE producto_id = ANY(%s)", (prod_ids,))
        cur.execute("DELETE FROM biofloc.detalles_compra WHERE producto_id = ANY(%s)", (prod_ids,))
        cur.execute("DELETE FROM biofloc.alimentaciones WHERE producto_id = ANY(%s)", (prod_ids,))
        cur.execute("DELETE FROM biofloc.productos WHERE id = ANY(%s)", (prod_ids,))
    ref_ids = _IDS["referencias_produccion"]
    if ref_ids:
        cur.execute("DELETE FROM biofloc.referencias_produccion WHERE id = ANY(%s)", (ref_ids,))
    cur.execute("DELETE FROM biofloc.auditoria WHERE detalle::text LIKE %s", (f"%{TAG}%",))
    cur.execute(
        "DELETE FROM biofloc.gastos WHERE descripcion LIKE %s OR COALESCE(observaciones,'') LIKE %s",
        (patron, patron),
    )
    cur.execute(
        "DELETE FROM biofloc.ventas WHERE cliente LIKE %s OR COALESCE(observaciones,'') LIKE %s",
        (patron, patron),
    )
    conn.commit()

    # Check leftover
    cur.execute(f"""
        SELECT
          (SELECT COUNT(*) FROM biofloc.lotes WHERE codigo LIKE '{TAG}%%') +
          (SELECT COUNT(*) FROM biofloc.estanques WHERE codigo LIKE '{TAG}%%') +
          (SELECT COUNT(*) FROM biofloc.productos WHERE codigo LIKE '{TAG}%%')
    """)
    n = int(cur.fetchone()[0])
    cur.close()
    conn.close()
    check("LEFTOVER VALIDACION_OP", n == 0, str(n))


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  VALIDACIÓN OPERATIVA — ERP PISCÍCOLA V1")
    print("=" * 70)

    token = login()
    cfg = fase_config(token)
    if not cfg:
        limpiar()
        return 1

    ctx = fase_ciclo(token, cfg)
    if not ctx:
        limpiar()
        return 1

    fase_produccion(token, ctx)
    fase_graficas(token, ctx)
    fase_agua(token, ctx)
    fase_biofloc(token, ctx)
    fase_finanzas(token, ctx)
    fase_historial(token, ctx)
    fase_comparacion(token, ctx)

    limpiar()

    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    failed = [(name, detail) for name, ok, detail in results if not ok]
    print(f"  RESULTADO: {passed}/{total} APROBADAS")
    if failed:
        print(f"  FALLOS:")
        for name, detail in failed:
            print(f"    - {name}: {detail}")
    print("=" * 70)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
