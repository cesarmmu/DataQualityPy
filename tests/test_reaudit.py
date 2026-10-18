"""Tests de reauditoría y comparación antes/después de DataQualityPy V7."""

import pandas as pd
import pytest

from src.audit import auditar_dataset
from src.cleaning import CleaningResult, ejecutar_plan_limpieza
from src.cleaning_plan import CleaningPlan
from src.config import cargar_configuracion
from src.reaudit import (
    IncidentComparison,
    ReauditComparison,
    ReauditError,
    comparar_incidencias,
    reauditar_despues_limpieza,
)


def _incidencia(
    tipo: str,
    columna: str | None = None,
    *,
    regla: str | None = None,
    cantidad: int | None = 1,
    porcentaje: float | None = 10.0,
    severidad: str = "media",
) -> dict:
    resultado = {
        "tipo": tipo,
        "categoria": "prueba",
        "severidad": severidad,
        "columna": columna,
        "cantidad": cantidad,
        "porcentaje": porcentaje,
        "mensaje": f"Incidencia {tipo} en {columna}",
    }
    if regla is not None:
        resultado["regla"] = regla
    return resultado


def _resultado_limpieza_vacio(filas: int = 1, columnas: int = 1) -> CleaningResult:
    return CleaningResult(
        filas_antes=filas,
        columnas_antes=columnas,
        filas_despues=filas,
        columnas_despues=columnas,
        operaciones_solicitadas=0,
        operaciones_ejecutadas=0,
        ejecuciones=[],
    )


def test_comparacion_clasifica_resueltas_persistentes_y_nuevas_v7():
    antes = [
        _incidencia("nulos_reales", "edad"),
        _incidencia("espacios_texto", "nombre"),
        _incidencia("filas_duplicadas"),
    ]
    despues = [
        _incidencia("nulos_reales", "edad", cantidad=2, porcentaje=2.0),
        _incidencia("filas_duplicadas", cantidad=1, porcentaje=1.0),
        _incidencia("outliers", "salario"),
    ]

    comparacion = comparar_incidencias(antes, despues)

    assert isinstance(comparacion, ReauditComparison)
    assert [item["tipo"] for item in comparacion.resolved] == ["espacios_texto"]
    assert [item.before["tipo"] for item in comparacion.persistent] == [
        "nulos_reales",
        "filas_duplicadas",
    ]
    assert [item["tipo"] for item in comparacion.new] == ["outliers"]


def test_persistencia_no_depende_de_cantidad_porcentaje_severidad_o_mensaje_v7():
    antes = _incidencia(
        "nulos_reales",
        "edad",
        cantidad=25,
        porcentaje=25.0,
        severidad="alta",
    )
    despues = _incidencia(
        "nulos_reales",
        "edad",
        cantidad=3,
        porcentaje=3.0,
        severidad="baja",
    )
    despues["mensaje"] = "Mensaje posterior diferente"

    comparacion = comparar_incidencias([antes], [despues])

    assert comparacion.resolved_count == 0
    assert comparacion.new_count == 0
    assert comparacion.persistent_count == 1
    assert isinstance(comparacion.persistent[0], IncidentComparison)
    assert comparacion.persistent[0].before["cantidad"] == 25
    assert comparacion.persistent[0].after["cantidad"] == 3


def test_reglas_distintas_en_misma_columna_tienen_identidad_independiente_v7():
    antes = [
        _incidencia("incumplimiento_regla", "edad", regla="min=18"),
        _incidencia("incumplimiento_regla", "edad", regla="max=65"),
    ]
    despues = [
        _incidencia("incumplimiento_regla", "edad", regla="max=65"),
    ]

    comparacion = comparar_incidencias(antes, despues)

    assert comparacion.resolved_count == 1
    assert comparacion.resolved[0]["regla"] == "min=18"
    assert comparacion.persistent_count == 1
    assert comparacion.persistent[0].before["regla"] == "max=65"


def test_identidades_duplicadas_generan_error_explicito_v7():
    incidencia = _incidencia("nulos_reales", "edad")

    with pytest.raises(ReauditError):
        comparar_incidencias([incidencia, dict(incidencia)], [])


def test_comparacion_vacia_es_valida_v7():
    comparacion = comparar_incidencias([], [])

    assert comparacion.resolved == ()
    assert comparacion.persistent == ()
    assert comparacion.new == ()
    assert comparacion.a_dict()["totales"] == {
        "resueltas": 0,
        "persistentes": 0,
        "nuevas": 0,
    }


def test_incidencia_sin_tipo_es_rechazada_v7():
    with pytest.raises(ReauditError):
        comparar_incidencias([{"columna": "edad"}], [])


def test_reauditoria_real_resuelve_espacios_de_texto_v7():
    datos = pd.DataFrame({"nombre": [" Ana ", "Luis"]})
    configuracion = cargar_configuracion()
    auditoria_antes = auditar_dataset(datos, "datos.csv", configuracion)

    assert any(
        incidencia["tipo"] == "espacios_texto"
        and incidencia["columna"] == "nombre"
        for incidencia in auditoria_antes["incidencias"]
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "nombre",
    )
    limpio, resultado_limpieza = ejecutar_plan_limpieza(datos, plan)

    resultado = reauditar_despues_limpieza(
        auditoria_antes,
        limpio,
        resultado_limpieza,
        "datos.csv",
        configuracion,
    )

    assert any(
        incidencia["tipo"] == "espacios_texto"
        and incidencia["columna"] == "nombre"
        for incidencia in resultado.comparison.resolved
    )
    assert not any(
        incidencia["tipo"] == "espacios_texto"
        and incidencia["columna"] == "nombre"
        for incidencia in resultado.audit_after["incidencias"]
    )


def test_reauditoria_conserva_resultado_limpieza_y_auditorias_v7():
    datos = pd.DataFrame({"valor": [1, 2, 3]})
    configuracion = cargar_configuracion()
    auditoria_antes = auditar_dataset(datos, "datos.csv", configuracion)
    resultado_limpieza = _resultado_limpieza_vacio(3, 1)

    resultado = reauditar_despues_limpieza(
        auditoria_antes,
        datos.copy(deep=True),
        resultado_limpieza,
        "datos.csv",
        configuracion,
    )

    assert resultado.audit_before is auditoria_antes
    assert resultado.cleaning_result is resultado_limpieza
    assert resultado.audit_after["dataset"]["archivo"] == "datos.csv"
    assert resultado.a_dict()["resultado_limpieza"] == resultado_limpieza.a_dict()


def test_reauditoria_rechaza_dataset_limpio_invalido_v7():
    with pytest.raises(ReauditError):
        reauditar_despues_limpieza(
            {"incidencias": []},
            None,  # type: ignore[arg-type]
            _resultado_limpieza_vacio(),
            "datos.csv",
            {},
        )


def test_reauditoria_rechaza_resultado_original_sin_incidencias_v7():
    with pytest.raises(ReauditError):
        reauditar_despues_limpieza(
            {},
            pd.DataFrame({"valor": [1]}),
            _resultado_limpieza_vacio(),
            "datos.csv",
            {},
        )
