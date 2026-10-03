from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.movimiento_inventario_service import _calcular_promedio_ponderado_movil
from app.services.validaciones_temporales import validar_evento_no_futuro, validar_evento_lote
from app.services.cosecha_service import _validar_coherencia_peso
from app.services.aplicacion_biofloc_service import _validar_producto_para_cantidad


def movimiento(cantidad, costo_unitario, afecta):
    return {
        "cantidad": Decimal(str(cantidad)),
        "costo_unitario": None if costo_unitario is None else Decimal(str(costo_unitario)),
        "costo_total": None,
        "afecta_stock": afecta,
        "id": 1,
    }


def test_promedio_ponderado_movil_no_reutiliza_compras_ya_consumidas():
    rows = [
        movimiento(100, 10000, 1),
        movimiento(90, 10000, -1),
        movimiento(10, 20000, 1),
    ]

    # Quedan 20 kg: 10 kg a $10.000 y 10 kg a $20.000.
    assert _calcular_promedio_ponderado_movil(rows) == Decimal("15000.00")


def test_promedio_ponderado_movil_rechaza_entrada_sin_costo():
    rows = [movimiento(10, None, 1)]
    with pytest.raises(HTTPException) as exc:
        _calcular_promedio_ponderado_movil(rows)
    assert exc.value.status_code == 422


def test_evento_futuro_se_rechaza():
    futuro = datetime.now(timezone.utc) + timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        validar_evento_no_futuro(futuro, "la alimentación")
    assert exc.value.status_code == 422


def test_evento_historico_de_lote_se_acepta():
    ayer = date.today() - timedelta(days=1)
    validar_evento_lote(ayer, date.today() - timedelta(days=10), "la biometría")


def test_evento_anterior_a_siembra_se_rechaza():
    ayer = date.today() - timedelta(days=1)
    with pytest.raises(HTTPException) as exc:
        validar_evento_lote(ayer, date.today(), "la biometría")
    assert exc.value.status_code == 422


def test_cosecha_coherente_se_acepta():
    _validar_coherencia_peso(Decimal("500"), 1000, Decimal("500"))


def test_cosecha_inconsistente_se_rechaza():
    with pytest.raises(HTTPException) as exc:
        _validar_coherencia_peso(Decimal("700"), 1000, Decimal("500"))
    assert exc.value.status_code == 422


def test_cosecha_con_diferencia_dentro_de_tolerancia_se_acepta():
    _validar_coherencia_peso(Decimal("550"), 1000, Decimal("500"))


def test_aplicacion_biofloc_con_cantidad_positiva_exige_producto():
    with pytest.raises(HTTPException) as exc:
        _validar_producto_para_cantidad(Decimal("5"), None)
    assert exc.value.status_code == 422


def test_aplicacion_biofloc_sin_producto_permite_cantidad_nula():
    _validar_producto_para_cantidad(None, None)


def test_aplicacion_biofloc_con_producto_y_cantidad_positiva_se_acepta():
    _validar_producto_para_cantidad(Decimal("5"), 10)
