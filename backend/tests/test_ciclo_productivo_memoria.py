"""Ciclo productivo end-to-end en memoria. Sin PostgreSQL, sin lote 659, sin HTTP."""
from decimal import Decimal

from app.config.referencia_alimentacion_tilapia import semana_productiva_alimentacion
from app.schemas.analisis import AlimentoUnidadOut
from app.services.alimentacion_referencia_service import (
    calcular_alimento_por_racion,
    calcular_racion_operativa,
    peso_operativo_lote,
    texto_raciones,
)
from app.services.analisis_service import FACTOR_A_KG, _alimento_kg, _fca_oficial
from app.services.indicadores_lote import (
    biomasa_kg,
    ganancia_biomasa_productiva_kg,
    ganancia_diaria_g,
    sgr_pct_dia,
    supervivencia_biologica_pct,
)
from app.services.poblacion_lote import calcular_poblacion_disponible

SEMBRADOS = 3500
PESO_INICIAL = Decimal("1.000")
TASA_S1 = Decimal("10.0")


def _ciclo(*, mort: int, cosecha_peces: int, cosecha_kg: Decimal, peso_bio, alimento_g: Decimal, dias: int):
    poblacion = calcular_poblacion_disponible(SEMBRADOS, mort, cosecha_peces)
    peso_op = peso_operativo_lote(PESO_INICIAL, peso_bio)
    b_ini = biomasa_kg(SEMBRADOS, PESO_INICIAL)
    b_op = biomasa_kg(poblacion, peso_op) if peso_op is not None else None
    b_act = biomasa_kg(poblacion, peso_bio) if peso_bio is not None else None
    ganancia, _ = ganancia_biomasa_productiva_kg(
        b_act, b_ini, cosecha_kg, hay_cosecha=cosecha_peces > 0, cosecha_con_peso=cosecha_kg > 0
    )
    alimento, razon = _alimento_kg([AlimentoUnidadOut(unidad="g", cantidad=alimento_g)]) if alimento_g else (None, "SIN_ALIMENTO")
    fca, fca_m = _fca_oficial(alimento, razon, ganancia, None)
    gpd, _ = ganancia_diaria_g(
        (peso_bio - PESO_INICIAL) if peso_bio is not None else None, dias
    )
    sgr, _ = sgr_pct_dia(PESO_INICIAL, peso_bio, dias)
    surv = supervivencia_biologica_pct(SEMBRADOS, mort)
    racion = calcular_racion_operativa(b_op, TASA_S1) if b_op is not None else (None, None)
    return {
        "poblacion": poblacion,
        "peso_op": peso_op,
        "b_ini": b_ini,
        "b_op": b_op,
        "b_act": b_act,
        "ganancia": ganancia,
        "alimento": alimento,
        "fca": fca,
        "fca_m": fca_m,
        "gpd": gpd,
        "sgr": sgr,
        "surv": surv,
        "racion_kg": racion[0],
        "semana": semana_productiva_alimentacion(dias),
    }


def test_a_crear_lote_sin_eventos():
    r = _ciclo(mort=0, cosecha_peces=0, cosecha_kg=Decimal("0"), peso_bio=None, alimento_g=Decimal("0"), dias=2)
    assert r["poblacion"] == 3500
    assert r["peso_op"] == PESO_INICIAL
    assert r["b_ini"] == Decimal("3.500")
    assert r["b_op"] == Decimal("3.500")
    assert r["b_act"] is None
    assert r["gpd"] is None
    assert r["sgr"] is None
    assert r["fca"] is None
    assert r["surv"] == Decimal("100.00")
    assert r["semana"] == 1


def test_b_poblacion_sembrados_menos_mort_menos_cosecha():
    assert calcular_poblacion_disponible(3500, 21, 100) == 3379


def test_c_sin_bio_una_bio_y_empate_id():
    assert peso_operativo_lote(PESO_INICIAL, None) == PESO_INICIAL
    assert peso_operativo_lote(PESO_INICIAL, Decimal("1.500")) == Decimal("1.500")
    from app.services.analisis_service import elegir_ultima_biometria
    from datetime import datetime, timezone

    mismo = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    ultima = elegir_ultima_biometria(
        [{"id": 1, "fecha_hora": mismo}, {"id": 2, "fecha_hora": mismo}]
    )
    assert ultima["id"] == 2


def test_d_alimento_g_a_kg_y_fca_usa_real():
    total, razon = _alimento_kg([AlimentoUnidadOut(unidad="g", cantidad=Decimal("1918"))])
    assert razon is None
    assert total == Decimal("1.918")
    assert FACTOR_A_KG["g"] == Decimal("0.001")
    assert FACTOR_A_KG["kg"] == Decimal("1")


def test_e_mortalidad_baja_poblacion_no_es_cosecha():
    r = _ciclo(mort=21, cosecha_peces=0, cosecha_kg=Decimal("0"), peso_bio=Decimal("1.500"), alimento_g=Decimal("1918"), dias=2)
    assert r["poblacion"] == 3479
    assert r["b_act"] == Decimal("5.219")
    assert r["surv"] == Decimal("99.40")


def test_f_cosecha_parcial_entra_en_fca_y_no_baja_supervivencia():
    r = _ciclo(
        mort=21,
        cosecha_peces=100,
        cosecha_kg=Decimal("0.150"),
        peso_bio=Decimal("1.500"),
        alimento_g=Decimal("1918"),
        dias=2,
    )
    assert r["poblacion"] == 3379
    assert r["surv"] == Decimal("99.40")
    assert r["ganancia"] == Decimal("1.719")
    assert r["fca"] is not None


def test_g_fca_oficial_no_usa_racion():
    r = _ciclo(mort=21, cosecha_peces=0, cosecha_kg=Decimal("0"), peso_bio=Decimal("1.500"), alimento_g=Decimal("1918"), dias=2)
    assert r["alimento"] == Decimal("1.918")
    assert r["ganancia"] == Decimal("1.719")
    assert r["fca"] == Decimal("1.1158")
    recomendada = r["racion_kg"]
    assert recomendada != r["alimento"]


def test_h_i_gpd_sgr_oficiales():
    r = _ciclo(mort=21, cosecha_peces=0, cosecha_kg=Decimal("0"), peso_bio=Decimal("1.500"), alimento_g=Decimal("1918"), dias=2)
    assert r["gpd"] == Decimal("0.250000")
    assert r["sgr"] == Decimal("20.2733")


def test_j_supervivencia_ignora_cosecha():
    assert supervivencia_biologica_pct(3500, 21) == Decimal("99.40")
    assert calcular_poblacion_disponible(3500, 21, 3479) == 0
    assert supervivencia_biologica_pct(3500, 21) == Decimal("99.40")


def test_k_biomasas_no_se_mezclan_sin_biometria():
    r = _ciclo(mort=0, cosecha_peces=0, cosecha_kg=Decimal("0"), peso_bio=None, alimento_g=Decimal("0"), dias=1)
    assert r["b_ini"] == Decimal("3.500")
    assert r["b_op"] == Decimal("3.500")
    assert r["b_act"] is None


def test_racion_s1_no_promedia_6_8():
    assert texto_raciones(6, 8) == "6–8"
    biomasa = biomasa_kg(3479, Decimal("1.500"))
    kg, g = calcular_racion_operativa(biomasa, TASA_S1)
    exact, _, min_kg, max_kg, _, _ = calcular_alimento_por_racion(kg, g, 6, 8)
    assert exact is None
    assert min_kg is not None and max_kg is not None
    assert min_kg < max_kg
