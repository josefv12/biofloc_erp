"""Etapa 6C: catálogo productivo oficial en referencias_produccion."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.models.lote import Especie, EtapaProductiva
from app.models.referencia_produccion import ReferenciaProduccion
from app.services.alimentacion_referencia_service import (
    calcular_biomasa_kg,
    calcular_racion_kg,
    especie_usa_tabla_maestra,
    resolver_parametros_semana,
    texto_raciones,
)

OFICIAL = {
    1: (Decimal("1.5"), Decimal("10.0"), 6, 8, "Inicio", "6–8"),
    8: (Decimal("45.0"), Decimal("5.0"), 4, 5, "Inicio", "4–5"),
    9: (Decimal("57.5"), Decimal("4.5"), 4, 4, "Levante", "4"),
    10: (Decimal("75.0"), Decimal("4.0"), 4, 4, "Levante", "4"),
    24: (Decimal("500.0"), Decimal("1.0"), 2, 2, "Engorde", "2"),
}


def _ref(semana: int) -> SimpleNamespace:
    peso, tasa, r_min, r_max, fase, _texto = OFICIAL[semana]
    return SimpleNamespace(
        id=semana,
        peso_esperado_g=peso,
        tasa_alimentacion_pct=tasa,
        raciones_min=r_min,
        raciones_max=r_max,
        fase=fase,
    )


def test_texto_raciones_no_promedia_6_8():
    assert texto_raciones(6, 8) == "6–8"
    assert texto_raciones(6, 8) != "7"
    assert texto_raciones(4, 4) == "4"
    assert texto_raciones(4, 5) == "4–5"


@pytest.mark.parametrize("semana", [1, 8, 9, 10, 24])
def test_resolver_semanas_oficiales(semana):
    peso, tasa, r_min, r_max, fase, texto = OFICIAL[semana]
    with patch(
        "app.services.alimentacion_referencia_service.ref_svc.resolver_referencia_aplicable",
        return_value=_ref(semana),
    ):
        params = resolver_parametros_semana(MagicMock(), 1, 1, semana)
    assert params is not None
    assert params.peso_esperado_g == peso
    assert params.tasa_alimentacion_pct == tasa
    assert params.raciones_min == r_min
    assert params.raciones_max == r_max
    assert params.raciones_texto == texto
    assert params.fase == fase
    assert params.fuente == "REFERENCIA_PRODUCCION_BD"
    if r_min != r_max:
        assert params.numero_raciones_diarias is None
        assert "7" not in (params.raciones_texto or "")


def test_racion_semana_10_3000_5000_10000():
    peso, tasa, *_ = OFICIAL[10]
    casos = [(3000, Decimal("9.000")), (5000, Decimal("15.000")), (10000, Decimal("30.000"))]
    for poblacion, esperado in casos:
        biomasa = calcular_biomasa_kg(poblacion, peso)
        racion = calcular_racion_kg(biomasa, tasa)
        assert racion == esperado


def test_cachama_sin_referencia_es_nd():
    with patch(
        "app.services.alimentacion_referencia_service.ref_svc.resolver_referencia_aplicable",
        return_value=None,
    ):
        assert resolver_parametros_semana(MagicMock(), 99, 1, 10) is None


def test_misma_referencia_evaluacion_grafica_racion():
    """Peso esperado, gráfica y ración salen del mismo resolver."""
    with patch(
        "app.services.alimentacion_referencia_service.ref_svc.resolver_referencia_aplicable",
        return_value=_ref(10),
    ) as mock_ref:
        eval_params = resolver_parametros_semana(MagicMock(), 1, 2, 10)
        graf_params = resolver_parametros_semana(MagicMock(), 1, 2, 10)
        racion_params = resolver_parametros_semana(MagicMock(), 1, 2, 10)
    assert eval_params == graf_params == racion_params
    assert mock_ref.call_count == 3
    assert eval_params.peso_esperado_g == Decimal("75.0")
    assert eval_params.referencia_bd_id == 10


def test_tilapia_roja_24_semanas_activas_en_bd():
    db = None
    try:
        db = SessionLocal()
        especie = next(
            (row for row in db.query(Especie).all() if especie_usa_tabla_maestra(row.nombre_comun)),
            None,
        )
        if especie is None:
            pytest.skip("No hay especie Tilapia roja")
        refs = (
            db.query(ReferenciaProduccion)
            .filter(
                ReferenciaProduccion.especie_id == especie.id,
                ReferenciaProduccion.activo.is_(True),
            )
            .order_by(ReferenciaProduccion.semana_desde.asc())
            .all()
        )
        assert len(refs) == 24
        semanas = [row.semana_desde for row in refs]
        assert semanas == list(range(1, 25))
        assert all(row.semana_desde == row.semana_hasta for row in refs)
        cubiertas = set()
        for row in refs:
            for semana in range(row.semana_desde, row.semana_hasta + 1):
                assert semana not in cubiertas
                cubiertas.add(semana)
        etapas = {row.id: row.nombre for row in db.query(EtapaProductiva).all()}
        for semana, esperado in OFICIAL.items():
            params = resolver_parametros_semana(db, especie.id, refs[0].etapa_productiva_id, semana)
            peso, tasa, r_min, r_max, fase, texto = esperado
            assert params is not None
            assert params.peso_esperado_g == peso
            assert params.tasa_alimentacion_pct == tasa
            assert params.raciones_min == r_min
            assert params.raciones_max == r_max
            assert params.raciones_texto == texto
            assert params.fase == fase
            fila = next(row for row in refs if row.semana_desde == semana)
            etapa = etapas.get(fila.etapa_productiva_id)
            if semana <= 8:
                assert etapa == "Alevinaje"
                assert fase == "Inicio"
                assert etapa != fase
            elif semana <= 16:
                assert etapa == "Preengorde"
                assert fase == "Levante"
            else:
                assert etapa == "Engorde"
        antiguas = (
            db.query(ReferenciaProduccion)
            .filter(ReferenciaProduccion.id.in_([204, 205, 206, 207, 222, 223, 224, 225, 226, 227, 228, 229]))
            .all()
        )
        if antiguas:
            assert all(row.activo is False for row in antiguas)
    except SQLAlchemyError as exc:
        pytest.skip(f"BD no disponible: {exc}")
    finally:
        if db is not None:
            db.close()
