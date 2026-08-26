#!/usr/bin/env python3
"""Contrato de ficha de estanque: análisis, series, N/D, comparación e historial.

Usa el dataset [DEMO] aislado y lo limpia al terminar.
No calcula indicadores en el cliente: verifica que el API los entregue.
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

import requests

from env_tests import ADMIN_PASS, ADMIN_USER

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo"))
import datos_demo as demo  # noqa: E402

BASE = "http://127.0.0.1:8000"
R: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    R.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" {detail}" if detail else ""))


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


def _es_numero_finito(valor) -> bool:
    if valor is None:
        return True
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return False
    return math.isfinite(n)


def main() -> int:
    admin = login()
    demo.limpiar()
    try:
        ids = demo.cargar()
        estanque_id = ids["estanque_id"]
        lote_id = ids["lote_activo_id"]

        r_est = requests.get(f"{BASE}/api/v1/estanques/{estanque_id}", headers=H(admin), timeout=20)
        check("GET estanque DEMO 200", r_est.status_code == 200, str(r_est.status_code))
        estanque = r_est.json() if r_est.status_code == 200 else {}
        check("estanque código [DEMO]", str(estanque.get("codigo", "")).startswith("[DEMO]"), str(estanque.get("codigo")))

        r_lotes = requests.get(
            f"{BASE}/api/v1/lotes/",
            headers=H(admin),
            params={"estanque_id": estanque_id},
            timeout=20,
        )
        lotes = r_lotes.json() if r_lotes.status_code == 200 else []
        check("lotes del estanque >= 2", isinstance(lotes, list) and len(lotes) >= 2, str(len(lotes)))

        r_an = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=H(admin), timeout=30)
        check("análisis lote 200", r_an.status_code == 200, str(r_an.status_code))
        data = r_an.json() if r_an.status_code == 200 else {}
        ind = data.get("indicadores") or {}
        efi = data.get("eficiencia") or {}
        fin = data.get("finanzas") or {}

        for campo in (
            "peces_sembrados",
            "poblacion_estimada",
            "dias_cultivo",
            "semana_cultivo",
            "peso_promedio_g",
            "biomasa_actual_kg",
            "supervivencia_porcentaje",
            "mortalidad_porcentaje",
            "fca_disponible",
            "alimento_real_acumulado_kg",
        ):
            check(f"indicador {campo} presente", campo in ind, str(ind.keys()))

        check("peso no es 0 por ausencia", ind.get("peso_promedio_g") not in (0, "0", 0.0), str(ind.get("peso_promedio_g")))
        check(
            "FCA N/D si no disponible",
            (not ind.get("fca_disponible") and ind.get("fca") is None) or bool(ind.get("fca_disponible")),
            f"disp={ind.get('fca_disponible')} fca={ind.get('fca')}",
        )
        check("utilidad N/D", fin.get("utilidad") is None, str(fin.get("utilidad")))
        check("margen N/D", fin.get("margen_porcentaje") is None, str(fin.get("margen_porcentaje")))

        for serie, minimo in (
            ("biometrias", 5),
            ("serie_biomasa", 5),
            ("serie_poblacion", 2),
            ("agua_serie", 8),
            ("biofloc_serie", 3),
            ("alimentacion_real", 5),
        ):
            puntos = data.get(serie) or []
            check(f"serie {serie} >= {minimo}", len(puntos) >= minimo, str(len(puntos)))
            if serie == "agua_serie":
                por_param: dict = {}
                for p in puntos:
                    if isinstance(p, dict) and p.get("fecha_hora"):
                        por_param.setdefault(p.get("parametro_id"), []).append(p["fecha_hora"])
                check(
                    f"serie {serie} ordenada por parámetro",
                    all(fechas == sorted(fechas) for fechas in por_param.values()),
                    str({k: v[:2] for k, v in por_param.items()}),
                )
            else:
                fechas = [p.get("fecha_hora") for p in puntos if isinstance(p, dict) and p.get("fecha_hora")]
                check(f"serie {serie} ordenada", fechas == sorted(fechas), str(fechas[:3]))

        for punto in data.get("serie_biomasa") or []:
            check("biomasa finita", _es_numero_finito(punto.get("biomasa_kg")), str(punto.get("biomasa_kg")))
        for punto in data.get("serie_fca") or []:
            check("FCA punto finito o null", _es_numero_finito(punto.get("fca")), str(punto.get("fca")))

        agua = data.get("agua") or []
        check("agua snapshot no vacía", len(agua) >= 1, str(len(agua)))
        for fila in agua:
            unidad = str(fila.get("unidad") or "")
            check("unidad agua sin mojibake", "Â" not in unidad and "Ã" not in unidad, unidad)
            if fila.get("valor_minimo") is None and fila.get("valor_maximo") is None:
                check("agua sin ref => fuera_de_rango null", fila.get("fuera_de_rango") is None, str(fila.get("fuera_de_rango")))

        check("biofloc serie presente", len(data.get("biofloc_serie") or []) >= 3, str(len(data.get("biofloc_serie") or [])))
        check("referencias producción DEMO ausentes", data.get("referencia_produccion") is None)

        r_comp = requests.get(
            f"{BASE}/api/v1/analisis/estanques",
            headers=H(admin),
            params={"solo_activos": "true"},
            timeout=30,
        )
        check("comparativo 200", r_comp.status_code == 200, str(r_comp.status_code))
        resumen = (r_comp.json() or {}).get("resumen") or {}
        check("FCA granja es null", resumen.get("fca") is None, str(resumen.get("fca")))
        check(
            "motivo FCA granja",
            resumen.get("fca_motivo") == "SIN_REGLA_DE_AGREGACION_DE_FCA",
            str(resumen.get("fca_motivo")),
        )

        r_hist = requests.get(
            f"{BASE}/api/v1/analisis/estanques",
            headers=H(admin),
            params={"estanque_id": estanque_id, "incluir_historial": "true", "solo_activos": "false"},
            timeout=30,
        )
        ciclos = (r_hist.json() or {}).get("ciclos") or []
        check("historial ciclos >= 2", len(ciclos) >= 2, str(len(ciclos)))
        check("eficiencia presente", "fca_disponible" in efi, str(efi.keys()))
    except Exception as exc:  # noqa: BLE001
        check("ficha estanque", False, str(exc)[:400])
    finally:
        leftover = demo.limpiar()
        check("LEFTOVER [DEMO]", leftover == 0, str(leftover))

    ok = sum(1 for _, bien, _ in R if bien)
    print(f"\nRESULT {ok}/{len(R)} OK")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
