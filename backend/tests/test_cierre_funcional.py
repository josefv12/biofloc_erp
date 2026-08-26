#!/usr/bin/env python3
"""Cierre funcional V1: catálogo de estados de estanque + dataset [DEMO].

- GET /estados-estanque (401/403/200). No hay POST (405 o 404 de ruta).
- Dataset [DEMO] produce series suficientes para graficar.
- leftover [DEMO] = 0 al terminar.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import requests

from env_tests import (
    ADMIN_PASS,
    ADMIN_USER,
    OPERARIO_PASS,
    OPERARIO_USER,
    TECNICO_PASS,
    TECNICO_USER,
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "demo"))
import datos_demo as demo  # noqa: E402

BASE = "http://127.0.0.1:8000"
R: list[tuple[str, bool, str]] = []


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


def main() -> int:
    r_no = requests.get(f"{BASE}/api/v1/estados-estanque/", timeout=20)
    check("GET estados-estanque sin JWT 403", r_no.status_code == 403, str(r_no.status_code))
    r_bad = requests.get(
        f"{BASE}/api/v1/estados-estanque/",
        headers={"Authorization": "Bearer token-invalido"},
        timeout=20,
    )
    check("GET estados-estanque token inválido 401", r_bad.status_code == 401, str(r_bad.status_code))

    admin = login(ADMIN_USER, ADMIN_PASS)
    tecnico = login(TECNICO_USER, TECNICO_PASS)
    operario = login(OPERARIO_USER, OPERARIO_PASS)

    r_a = requests.get(f"{BASE}/api/v1/estados-estanque/", headers=H(admin), timeout=20)
    check("GET ADMIN estados-estanque 200", r_a.status_code == 200, str(r_a.status_code))
    estados = r_a.json() if r_a.status_code == 200 else []
    check("catálogo estados-estanque no vacío", isinstance(estados, list) and len(estados) > 0, str(len(estados)))
    check(
        "incluye DISPONIBLE",
        any(row.get("nombre") == "DISPONIBLE" for row in estados),
        ",".join(row.get("nombre", "") for row in estados),
    )

    r_t = requests.get(f"{BASE}/api/v1/estados-estanque/", headers=H(tecnico), timeout=20)
    check("GET TECNICO estados-estanque 200", r_t.status_code == 200)
    r_o = requests.get(f"{BASE}/api/v1/estados-estanque/", headers=H(operario), timeout=20)
    check("GET OPERARIO estados-estanque 200", r_o.status_code == 200)

    r_post = requests.post(
        f"{BASE}/api/v1/estados-estanque/",
        headers=H(admin),
        json={"nombre": "[DEMO] no debe crearse"},
        timeout=20,
    )
    check(
        "POST estados-estanque no existe",
        r_post.status_code in (404, 405, 422),
        str(r_post.status_code),
    )

    demo.limpiar()
    try:
        ids = demo.cargar()
        lote_id = ids["lote_activo_id"]
        r_an = requests.get(f"{BASE}/api/v1/analisis/lotes/{lote_id}", headers=H(admin), timeout=30)
        check("análisis DEMO 200", r_an.status_code == 200, str(r_an.status_code))
        data = r_an.json() if r_an.status_code == 200 else {}
        bios = data.get("biometrias") or []
        check("DEMO biometrías >= 5", len(bios) >= 5, str(len(bios)))
        check(
            "DEMO talla en serie",
            bios and bios[-1].get("talla_promedio") is not None,
            str(bios[-1] if bios else None),
        )
        agua = data.get("agua_serie") or data.get("agua") or []
        check("DEMO agua >= 8 puntos", len(agua) >= 8, str(len(agua)))
        biofloc = data.get("biofloc_serie") or []
        if not biofloc and data.get("biofloc"):
            biofloc = [data["biofloc"]]
        check("DEMO biofloc >= 3 puntos", len(biofloc) >= 3, str(len(biofloc)))
        alim = data.get("alimentacion_real") or []
        check("DEMO alimentaciones >= 5", len(alim) >= 5, str(len(alim)))
        ind = data.get("indicadores") or {}
        check(
            "DEMO peso no es 0 por ausencia",
            ind.get("peso_promedio_g") not in (0, "0", 0.0),
            str(ind.get("peso_promedio_g")),
        )
        check("DEMO serie biomasa >= 5", len(data.get("serie_biomasa") or []) >= 5, str(len(data.get("serie_biomasa") or [])))
        check("DEMO serie población >= 2", len(data.get("serie_poblacion") or []) >= 2, str(len(data.get("serie_poblacion") or [])))
        check("DEMO serie FCA presente", isinstance(data.get("serie_fca"), list), str(type(data.get("serie_fca"))))
        check(
            "DEMO FCA null si no disponible",
            (not ind.get("fca_disponible") and ind.get("fca") is None) or bool(ind.get("fca_disponible")),
            f"disp={ind.get('fca_disponible')} fca={ind.get('fca')} motivo={ind.get('fca_motivo')}",
        )
        check("DEMO sin referencia de producción", data.get("referencia_produccion") is None, str(data.get("referencia_produccion")))
        r_comp = requests.get(
            f"{BASE}/api/v1/analisis/estanques?solo_activos=true",
            headers=H(admin),
            timeout=30,
        )
        check("comparativo DEMO 200", r_comp.status_code == 200, str(r_comp.status_code))
        estanques = (r_comp.json() or {}).get("estanques") or []
        demo_rows = [row for row in estanques if str(row.get("codigo", "")).startswith("[DEMO]")]
        check("comparativo incluye 2 estanques DEMO", len(demo_rows) >= 2, str(len(demo_rows)))
        r_hist = requests.get(
            f"{BASE}/api/v1/analisis/estanques",
            headers=H(admin),
            params={"estanque_id": ids["estanque_id"], "incluir_historial": "true", "solo_activos": "false"},
            timeout=30,
        )
        ciclos = (r_hist.json() or {}).get("ciclos") or []
        check("historial DEMO tiene 2 ciclos", len(ciclos) >= 2, str(len(ciclos)))
    except Exception as exc:  # noqa: BLE001
        check("cargar/verificar DEMO", False, str(exc)[:300])
    finally:
        leftover = demo.limpiar()
        check("LEFTOVER [DEMO]", leftover == 0, str(leftover))

    ok = sum(1 for _, bien, _ in R if bien)
    print(f"\nRESULT {ok}/{len(R)} OK")
    return 0 if ok == len(R) else 1


if __name__ == "__main__":
    raise SystemExit(main())
