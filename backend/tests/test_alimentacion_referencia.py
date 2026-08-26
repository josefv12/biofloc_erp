"""Pruebas unitarias de calendario, referencias y fórmulas de alimentación (Etapa 2)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config.referencia_alimentacion_tilapia import (
    TABLA_ALIMENTACION_TILAPIA,
    obtener_fila_maestra,
    semana_productiva_alimentacion,
)
from app.services.alimentacion_referencia_service import (
    ParametrosReferenciaSemana,
    calcular_biomasa_kg,
    calcular_racion_en_fecha,
    calcular_racion_kg,
    calcular_racion_lote,
    especie_usa_tabla_maestra,
    peso_operativo_lote,
    resolver_parametros_semana,
)
from app.services.referencia_produccion_service import _precedencia, _resolver


def test_tabla_tiene_24_semanas():
    assert len(TABLA_ALIMENTACION_TILAPIA) == 24
    assert TABLA_ALIMENTACION_TILAPIA[0].semana == 1
    assert TABLA_ALIMENTACION_TILAPIA[-1].semana == 24
    assert TABLA_ALIMENTACION_TILAPIA[-1].peso_esperado_g == Decimal("500.0")


def test_semana_floor_dias_sobre_7_mas_1():
    assert semana_productiva_alimentacion(0) == 1
    assert semana_productiva_alimentacion(1) == 1
    assert semana_productiva_alimentacion(6) == 1
    assert semana_productiva_alimentacion(7) == 2
    assert semana_productiva_alimentacion(8) == 2
    assert semana_productiva_alimentacion(13) == 2
    assert semana_productiva_alimentacion(14) == 3


def test_calendario_siembra_19_agosto_2026():
    siembra = date(2026, 8, 19)
    casos = [
        (date(2026, 8, 19), 1),
        (date(2026, 8, 20), 1),
        (date(2026, 8, 25), 1),
        (date(2026, 8, 26), 2),
        (date(2026, 9, 1), 2),
        (date(2026, 9, 2), 3),
    ]
    for fecha, semana in casos:
        assert semana_productiva_alimentacion((fecha - siembra).days) == semana


def test_semana_no_recorta_a_24():
    assert semana_productiva_alimentacion(200) == 200 // 7 + 1


def test_semana_no_es_iso():
    """19/08/2026 es miércoles; la semana de cultivo no usa isocalendar."""
    siembra = date(2026, 8, 19)
    assert semana_productiva_alimentacion(0) == 1
    assert siembra.isocalendar().week == 34


def test_referencias_python_semana_1_2_10():
    s1 = obtener_fila_maestra(1)
    s2 = obtener_fila_maestra(2)
    s10 = obtener_fila_maestra(10)
    assert s1 is not None and s1.peso_esperado_g == Decimal("1.5")
    assert s2 is not None and s2.peso_esperado_g == Decimal("3.0")
    assert s10 is not None and s10.peso_esperado_g == Decimal("75.0")
    assert s10.tasa_alimentacion_pct == Decimal("4.0")
    assert s10.numero_raciones_unico == 4


def test_obtener_fila_maestra_no_desplaza_a_semana_anterior():
    assert obtener_fila_maestra(10).semana == 10
    assert obtener_fila_maestra(3).semana == 3
    assert obtener_fila_maestra(25) is None


def test_ejemplo_semana_1_3500_peces_guia_peso_esperado():
    """Guía de catálogo: 3500 peces × 1,5 g esperado × 10 % → 0,525 kg/día.

    No es la ración operativa del lote (esa usa peso inicial / biometría).
    """
    fila = obtener_fila_maestra(1)
    assert fila.peso_esperado_g == Decimal("1.5")
    assert fila.tasa_alimentacion_pct == Decimal("10.0")
    biomasa = calcular_biomasa_kg(3500, fila.peso_esperado_g)
    assert biomasa == Decimal("5.250")
    racion = calcular_racion_kg(biomasa, fila.tasa_alimentacion_pct)
    assert racion == Decimal("0.525")


def test_ejemplo_biometria_2g_mantiene_referencia_1_5g():
    fila = obtener_fila_maestra(1)
    biomasa_real = calcular_biomasa_kg(3500, Decimal("2"))
    assert biomasa_real == Decimal("7.000")
    racion = calcular_racion_kg(biomasa_real, fila.tasa_alimentacion_pct)
    assert racion == Decimal("0.700")
    assert fila.peso_esperado_g == Decimal("1.5")


def test_alimento_referencia_1000_peces_semana_1():
    fila = obtener_fila_maestra(1)
    assert fila.alimento_referencia_1000_peces_kg == Decimal("0.150")


def test_semana_8_valores():
    fila = obtener_fila_maestra(8)
    assert fila.fase == "Inicio"
    assert fila.peso_esperado_g == Decimal("45.0")
    assert fila.tasa_alimentacion_pct == Decimal("5.0")
    assert fila.raciones_texto == "4–5"
    assert fila.numero_raciones_unico is None


def _racion_semana_10(poblacion: int, peso_g: Decimal | None = None) -> tuple[Decimal, Decimal, Decimal]:
    fila = obtener_fila_maestra(10)
    assert fila is not None
    peso = peso_g if peso_g is not None else fila.peso_esperado_g
    biomasa = calcular_biomasa_kg(poblacion, peso)
    racion = calcular_racion_kg(biomasa, fila.tasa_alimentacion_pct)
    por_racion = (racion / Decimal(fila.numero_raciones_unico)).quantize(Decimal("0.001"))
    return biomasa, racion, por_racion


def test_caso_a_3000_peces_semana_10():
    biomasa, racion, por_racion = _racion_semana_10(3000)
    assert biomasa == Decimal("225.000")
    assert racion == Decimal("9.000")
    assert por_racion == Decimal("2.250")


def test_caso_b_5000_peces_semana_10():
    biomasa, racion, por_racion = _racion_semana_10(5000)
    assert biomasa == Decimal("375.000")
    assert racion == Decimal("15.000")
    assert por_racion == Decimal("3.750")


def test_caso_c_10000_peces_semana_10():
    biomasa, racion, por_racion = _racion_semana_10(10000)
    assert biomasa == Decimal("750.000")
    assert racion == Decimal("30.000")
    assert por_racion == Decimal("7.500")


def test_referencia_no_depende_de_cantidad_fija():
    _b3, r3, _ = _racion_semana_10(3000)
    _b5, r5, _ = _racion_semana_10(5000)
    _b10, r10, _ = _racion_semana_10(10000)
    assert r5 / r3 == Decimal("5") / Decimal("3")
    assert r10 / r3 == Decimal("10") / Decimal("3")


def test_caso_mortalidad_4800_peces_semana_10():
    biomasa, racion, por_racion = _racion_semana_10(4800)
    assert biomasa == Decimal("360.000")
    assert racion == Decimal("14.400")
    assert por_racion == Decimal("3.600")


def test_caso_biometria_82g_4800_peces_semana_10():
    biomasa, racion, por_racion = _racion_semana_10(4800, Decimal("82"))
    assert biomasa == Decimal("393.600")
    assert racion == Decimal("15.744")
    assert por_racion == Decimal("3.936")
    fila = obtener_fila_maestra(10)
    assert fila.peso_esperado_g == Decimal("75.0")


def test_especie_usa_tabla_maestra_solo_tilapia_roja():
    assert especie_usa_tabla_maestra("Tilapia roja") is True
    assert especie_usa_tabla_maestra("TILAPIA ROJA") is True
    assert especie_usa_tabla_maestra("Cachama") is False
    assert especie_usa_tabla_maestra(None) is False


@patch(
    "app.services.alimentacion_referencia_service.ref_svc.resolver_referencia_aplicable",
    return_value=None,
)
def test_resolver_otra_especie_sin_bd_es_nd(_mock_ref):
    db = MagicMock()
    params = resolver_parametros_semana(db, especie_id=99, etapa_productiva_id=1, semana=10)
    assert params is None


@patch("app.services.alimentacion_referencia_service.ref_svc.resolver_referencia_aplicable")
def test_resolver_no_convierte_semana_a_dias(mock_ref):
    """Semana 10 debe pedir fila 10, no 9. Solo PostgreSQL."""
    mock_ref.return_value = SimpleNamespace(
        id=10,
        peso_esperado_g=Decimal("75.0"),
        tasa_alimentacion_pct=Decimal("4.0"),
        raciones_min=4,
        raciones_max=4,
        fase="Levante",
    )
    db = MagicMock()
    params = resolver_parametros_semana(db, especie_id=1, etapa_productiva_id=1, semana=10)
    assert mock_ref.call_args.args[3] == 10
    assert params is not None
    assert params.semana == 10
    assert params.peso_esperado_g == Decimal("75.0")
    assert params.fuente == "REFERENCIA_PRODUCCION_BD"


@patch(
    "app.services.alimentacion_referencia_service.ref_svc.resolver_referencia_aplicable",
    return_value=None,
)
def test_resolver_tilapia_sin_bd_no_usa_python(_mock_ref):
    db = MagicMock()
    params = resolver_parametros_semana(db, especie_id=1, etapa_productiva_id=1, semana=10)
    assert params is None


def test_rango_raciones_no_promedia():
    fila = obtener_fila_maestra(1)
    assert fila.raciones_texto == "6–8"
    assert fila.numero_raciones_unico is None


def test_etapa_lote_no_bloquea_fase_por_semana():
    inicio = SimpleNamespace(id=1, semana_desde=1, semana_hasta=24, etapa_productiva_id=1)
    levante = SimpleNamespace(id=2, semana_desde=9, semana_hasta=16, etapa_productiva_id=2)
    elegida = _resolver([inicio, levante], 10, etapa_preferida_id=1)
    assert elegida.id == 2


def test_etapa_solo_desempata_misma_amplitud():
    a = SimpleNamespace(id=1, semana_desde=10, semana_hasta=10, etapa_productiva_id=1)
    b = SimpleNamespace(id=2, semana_desde=10, semana_hasta=10, etapa_productiva_id=2)
    assert _resolver([a, b], 10, etapa_preferida_id=2).id == 2
    assert _precedencia(a, 10, 1) < _precedencia(b, 10, 1)


def _params_semana_1() -> ParametrosReferenciaSemana:
    return ParametrosReferenciaSemana(
        semana=1,
        fase="Inicio",
        peso_esperado_g=Decimal("1.5"),
        tasa_alimentacion_pct=Decimal("10.0"),
        raciones_texto="6–8",
        raciones_min=6,
        raciones_max=8,
        numero_raciones_diarias=None,
        alimento_referencia_1000_peces_kg=Decimal("0.150"),
        referencia_bd_id=1,
        fuente="REFERENCIA_PRODUCCION_BD",
    )


def _params_semana_10() -> ParametrosReferenciaSemana:
    return ParametrosReferenciaSemana(
        semana=10,
        fase="Levante",
        peso_esperado_g=Decimal("75.0"),
        tasa_alimentacion_pct=Decimal("4.0"),
        raciones_texto="4",
        raciones_min=4,
        raciones_max=4,
        numero_raciones_diarias=4,
        alimento_referencia_1000_peces_kg=Decimal("3.000"),
        referencia_bd_id=10,
        fuente="REFERENCIA_PRODUCCION_BD",
    )


def _lote_alim() -> SimpleNamespace:
    return SimpleNamespace(id=1, especie_id=1, etapa_productiva_id=1, cantidad_sembrada=3500)


def test_peso_operativo_inicial_luego_biometria():
    assert peso_operativo_lote(Decimal("1"), None) == Decimal("1")
    assert peso_operativo_lote(Decimal("1"), Decimal("4")) == Decimal("4")
    assert peso_operativo_lote(Decimal("1"), Decimal("7")) == Decimal("7")
    assert peso_operativo_lote(None, None) is None


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3500)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_1(),
)
def test_caso_1_3500_sin_biometria_usa_peso_inicial(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=0,
        peso_inicial_g=Decimal("1"),
        peso_real_g=None,
    )
    assert resultado.peso_operativo_g == Decimal("1")
    assert resultado.peso_utilizado == "inicial"
    assert resultado.biomasa_para_racion_kg == Decimal("3.500")
    assert resultado.racion_diaria_kg == Decimal("0.3500")
    assert resultado.racion_diaria_g == Decimal("350.0")
    assert resultado.racion_por_comida_min_g == Decimal("43.75")
    assert resultado.racion_por_comida_max_g == Decimal("58.33")
    assert resultado.racion_por_comida_kg is None
    assert resultado.parametros is not None
    assert resultado.parametros.raciones_texto == "6–8"
    assert resultado.parametros.numero_raciones_diarias is None
    assert resultado.biomasa_esperada_kg == Decimal("5.250")


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3479)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_1(),
)
def test_caso_2_3479_sin_biometria(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=0,
        peso_inicial_g=Decimal("1"),
        peso_real_g=None,
    )
    assert resultado.peso_operativo_g == Decimal("1")
    assert resultado.biomasa_para_racion_kg == Decimal("3.479")
    assert resultado.racion_diaria_kg == Decimal("0.3479")
    assert resultado.racion_diaria_g == Decimal("347.9")
    assert resultado.racion_por_comida_min_g == Decimal("43.49")
    assert resultado.racion_por_comida_max_g == Decimal("57.98")
    assert resultado.racion_por_comida_min_kg == Decimal("0.0435")
    assert resultado.racion_por_comida_max_kg == Decimal("0.0580")
    assert resultado.biomasa_esperada_kg == Decimal("5.219")
    assert resultado.diferencia_peso_g == Decimal("-0.50")


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3479)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_1(),
)
def test_caso_3_biometria_4g_no_usa_esperado(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=0,
        peso_inicial_g=Decimal("1"),
        peso_real_g=Decimal("4"),
    )
    assert resultado.peso_operativo_g == Decimal("4")
    assert resultado.peso_utilizado == "real"
    assert resultado.biomasa_para_racion_kg == Decimal("13.916")
    assert resultado.racion_diaria_kg == Decimal("1.3916")
    assert resultado.parametros is not None
    assert resultado.parametros.peso_esperado_g == Decimal("1.5")


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3479)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_1(),
)
def test_caso_4_nueva_biometria_7g(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=0,
        peso_inicial_g=Decimal("1"),
        peso_real_g=Decimal("7"),
    )
    assert resultado.peso_operativo_g == Decimal("7")
    assert resultado.biomasa_para_racion_kg == Decimal("24.353")
    assert resultado.racion_diaria_kg == Decimal("2.4353")


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3000)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_10(),
)
def test_caso_5_semana_10_racion_exacta(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=63,
        peso_inicial_g=Decimal("1"),
        peso_real_g=Decimal("75"),
    )
    assert resultado.semana_productiva == 10
    assert resultado.peso_operativo_g == Decimal("75")
    assert resultado.biomasa_para_racion_kg == Decimal("225.000")
    assert resultado.racion_diaria_kg == Decimal("9.0000")
    assert resultado.racion_diaria_g == Decimal("9000.0")
    assert resultado.racion_por_comida_kg == Decimal("2.250")
    assert resultado.racion_por_comida_g == Decimal("2250.0")
    assert resultado.racion_por_comida_min_g is None
    assert resultado.parametros is not None
    assert resultado.parametros.numero_raciones_diarias == 4
    assert resultado.parametros.raciones_texto == "4"


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3479)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_1(),
)
def test_caso_6_rango_6_8_no_promedia(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=0,
        peso_inicial_g=Decimal("1"),
        peso_real_g=None,
    )
    assert resultado.parametros is not None
    assert resultado.parametros.raciones_texto == "6–8"
    assert resultado.parametros.numero_raciones_diarias is None
    assert resultado.racion_por_comida_kg is None
    assert resultado.racion_por_comida_min_g != resultado.racion_por_comida_max_g
    promedio = (resultado.racion_diaria_g or 0) / Decimal("7")
    assert resultado.racion_por_comida_min_g != promedio.quantize(Decimal("0.01"))


@patch("app.services.alimentacion_referencia_service.obtener_poblacion_disponible", return_value=3479)
@patch(
    "app.services.alimentacion_referencia_service.resolver_parametros_semana",
    return_value=_params_semana_1(),
)
def test_caso_7_sin_biometria_nunca_nd_si_hay_inicial(_mock_res, _mock_pob):
    resultado = calcular_racion_lote(
        MagicMock(),
        _lote_alim(),
        dias_cultivo=0,
        peso_inicial_g=Decimal("1.00"),
        peso_real_g=None,
    )
    assert resultado.peso_real_g is None
    assert resultado.peso_operativo_g == Decimal("1.00")
    assert resultado.peso_utilizado == "inicial"
    assert resultado.biomasa_para_racion_kg is not None
    assert resultado.racion_diaria_kg is not None


@patch("app.services.alimentacion_referencia_service.resolver_parametros_semana")
def test_racion_en_fecha_usa_peso_inicial_sin_biometria(mock_res):
    mock_res.return_value = _params_semana_1()
    lote = SimpleNamespace(
        especie_id=1,
        etapa_productiva_id=1,
        fecha_siembra=date(2026, 8, 19),
        peso_inicial_promedio_g=Decimal("1"),
    )
    racion = calcular_racion_en_fecha(
        MagicMock(),
        lote,
        fecha=date(2026, 8, 19),
        poblacion=3479,
        peso_real_hasta=None,
        peso_inicial_g=Decimal("1"),
    )
    assert racion == Decimal("0.3479")


def test_serie_comparativa_acepta_racion_operativa_4_decimales():
    """La ración operativa usa 4 decimales; el punto comparativo no debe rechazarla."""
    from app.schemas.alimentacion_referencia import AlimentacionComparativaPuntoOut

    punto = AlimentacionComparativaPuntoOut(
        fecha="2026-08-19",
        real_kg=Decimal("0.350"),
        recomendada_kg=Decimal("0.3489"),
        desviacion_kg=Decimal("0.001"),
        desviacion_porcentaje=Decimal("0.29"),
        semana_cultivo=1,
    )
    assert punto.recomendada_kg == Decimal("0.3489")
