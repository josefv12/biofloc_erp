"""Comparación de solo lectura: tabla Python vs referencias_produccion (Tilapia roja)."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.config.referencia_alimentacion_tilapia import TABLA_ALIMENTACION_TILAPIA
from app.core.database import SessionLocal
from app.models.lote import Especie, EtapaProductiva
from app.services.alimentacion_referencia_service import (
    comparar_tabla_maestra_con_bd,
    especie_usa_tabla_maestra,
)


def test_comparar_python_vs_bd_tilapia_solo_lectura():
    db = None
    try:
        db = SessionLocal()
        especie = next(
            (row for row in db.query(Especie).all() if especie_usa_tabla_maestra(row.nombre_comun)),
            None,
        )
        if especie is None:
            pytest.skip("No hay especie Tilapia roja en el catálogo")
        etapa = db.query(EtapaProductiva).order_by(EtapaProductiva.orden).first()
        if etapa is None:
            pytest.skip("No hay etapas productivas")
        filas = comparar_tabla_maestra_con_bd(db, especie.id, etapa.id)
        assert len(filas) == 24
        assert [fila["semana"] for fila in filas] == [row.semana for row in TABLA_ALIMENTACION_TILAPIA]
        print("Semana | Peso Py | Peso BD | Tasa Py | Tasa BD | Rac Py | Rac BD | Fase Py | Fase BD")
        for fila in filas:
            print(
                f"{fila['semana']:6} | {fila['peso_python']} | {fila['peso_bd']} | "
                f"{fila['tasa_python']} | {fila['tasa_bd']} | {fila['raciones_python']} | "
                f"{fila['raciones_bd']} | {fila['fase_python']} | {fila['fase_bd']}"
            )
        coinciden_peso = sum(1 for fila in filas if fila["coincide_peso"])
        coinciden_tasa = sum(1 for fila in filas if fila["coincide_tasa"])
        coinciden_raciones = sum(1 for fila in filas if fila["coincide_raciones"])
        coinciden_fase = sum(1 for fila in filas if fila["coincide_fase"])
        sin_bd = sum(1 for fila in filas if fila["referencia_bd_id"] is None)
        print(
            f"coinciden_peso={coinciden_peso} coinciden_tasa={coinciden_tasa} "
            f"coinciden_raciones={coinciden_raciones} coinciden_fase={coinciden_fase} "
            f"semanas_sin_bd={sin_bd}"
        )
        assert all(isinstance(fila["peso_python"], Decimal) for fila in filas)
        assert coinciden_peso == 24
        assert coinciden_tasa == 24
        assert coinciden_raciones == 24
        assert coinciden_fase == 24
        assert sin_bd == 0
    except SQLAlchemyError as exc:
        pytest.skip(f"BD no disponible para comparación: {exc}")
    finally:
        if db is not None:
            db.close()
