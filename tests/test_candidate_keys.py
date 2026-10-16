"""Tests de evaluación de claves candidatas de DataQualityPy."""

import pandas as pd
import pytest

from src.candidate_keys import (
    CandidateKeyLevel,
    evaluar_clave_candidata,
    evaluar_claves_candidatas,
)
from src.column_analysis import (
    analizar_columna,
    analizar_columnas,
)
from src.inference import InferenceConfidence


def test_clave_candidata_fuerte_v6() -> None:
    """Una columna completamente única y completa debe ser fuerte."""
    serie = pd.Series(
        ["C001", "C002", "C003", "C004"],
        name="cliente_id",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert resultado.column_name == "cliente_id"
    assert resultado.level is CandidateKeyLevel.STRONG
    assert resultado.confidence is InferenceConfidence.HIGH


def test_clave_candidata_fuerte_sin_nombre_identificador_v6() -> None:
    """
    Una columna puede ser candidata fuerte aunque su nombre
    no sugiera explícitamente un identificador.
    """
    serie = pd.Series(
        [
            "a@ejemplo.es",
            "b@ejemplo.es",
            "c@ejemplo.es",
            "d@ejemplo.es",
        ],
        name="email",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert resultado.level is CandidateKeyLevel.STRONG
    assert resultado.confidence is InferenceConfidence.HIGH


def test_clave_candidata_posible_por_repeticion_v6() -> None:
    """Una unicidad elevada con repeticiones debe quedar como posible."""
    valores = [
        f"C{i:03d}"
        for i in range(1, 99)
    ]
    valores.extend(
        [
            "C001",
            "C002",
        ]
    )

    serie = pd.Series(
        valores,
        name="referencia",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.analyzable_count == 100
    assert analisis.unique_count == 98
    assert analisis.unique_ratio == pytest.approx(98.0)

    assert resultado.level is CandidateKeyLevel.POSSIBLE
    assert resultado.confidence is InferenceConfidence.MEDIUM


def test_clave_candidata_posible_con_nulos_v6() -> None:
    """
    Una columna única entre sus valores presentes no debe ser fuerte
    si contiene valores nulos.
    """
    serie = pd.Series(
        ["A001", "A002", "A003", None],
        name="codigo",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.unique_ratio == pytest.approx(100.0)
    assert analisis.null_count == 1

    assert resultado.level is CandidateKeyLevel.POSSIBLE
    assert resultado.confidence is InferenceConfidence.MEDIUM


def test_clave_candidata_posible_en_umbral_v6() -> None:
    """El 95 % de unicidad debe incluirse en el nivel posible."""
    valores = [
        f"V{i:03d}"
        for i in range(1, 96)
    ]
    valores.extend(
        [
            "V001",
            "V002",
            "V003",
            "V004",
            "V005",
        ]
    )

    serie = pd.Series(
        valores,
        name="referencia",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.analyzable_count == 100
    assert analisis.unique_count == 95
    assert analisis.unique_ratio == pytest.approx(95.0)

    assert resultado.level is CandidateKeyLevel.POSSIBLE
    assert resultado.confidence is InferenceConfidence.MEDIUM


def test_clave_no_candidata_por_debajo_umbral_v6() -> None:
    """Una unicidad inferior al 95 % no debe generar candidatura."""
    valores = [
        f"V{i:03d}"
        for i in range(1, 95)
    ]
    valores.extend(
        [
            "V001",
            "V002",
            "V003",
            "V004",
            "V005",
            "V006",
        ]
    )

    serie = pd.Series(
        valores,
        name="referencia",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.analyzable_count == 100
    assert analisis.unique_count == 94
    assert analisis.unique_ratio == pytest.approx(94.0)

    assert resultado.level is CandidateKeyLevel.NO_CANDIDATE
    assert resultado.confidence is InferenceConfidence.HIGH


def test_clave_candidata_muestra_pequena_v6() -> None:
    """
    Una muestra demasiado pequeña puede ser compatible con una clave,
    pero no debe clasificarse como fuerte.
    """
    serie = pd.Series(
        ["A001", "A002"],
        name="codigo",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.analyzable_count == 2
    assert analisis.unique_ratio == pytest.approx(100.0)

    assert resultado.level is CandidateKeyLevel.POSSIBLE
    assert resultado.confidence is InferenceConfidence.LOW


def test_clave_no_candidata_columna_constante_v6() -> None:
    """Una columna constante no debe considerarse clave candidata."""
    serie = pd.Series(
        ["Activo", "Activo", "Activo", "Activo"],
        name="estado",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.unique_count == 1
    assert analisis.unique_ratio == pytest.approx(25.0)

    assert resultado.level is CandidateKeyLevel.NO_CANDIDATE
    assert resultado.confidence is InferenceConfidence.HIGH


def test_clave_no_candidata_columna_vacia_v6() -> None:
    """Una columna sin valores analizables no puede ser clave candidata."""
    serie = pd.Series(
        [None, "NA", "", "null"],
        name="codigo",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.analyzable_count == 0

    assert resultado.level is CandidateKeyLevel.NO_CANDIDATE
    assert resultado.confidence is InferenceConfidence.HIGH


def test_nombre_identificador_es_solo_evidencia_v6() -> None:
    """
    Un nombre indicativo de identificador no debe elevar una columna
    con baja unicidad.
    """
    serie = pd.Series(
        [
            "C001",
            "C001",
            "C001",
            "C002",
            "C002",
        ],
        name="cliente_id",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert analisis.unique_ratio == pytest.approx(40.0)
    assert resultado.level is CandidateKeyLevel.NO_CANDIDATE

    assert any(
        "nombre de la columna sugiere un identificador"
        in evidencia
        for evidencia in resultado.evidence
    )


def test_evidencias_clave_fuerte_v6() -> None:
    """Una candidata fuerte debe conservar evidencias explicables."""
    serie = pd.Series(
        ["C001", "C002", "C003", "C004"],
        name="cliente_id",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    resultado = evaluar_clave_candidata(analisis)

    assert any(
        "4 de 4 valores analizables son distintos"
        in evidencia
        for evidencia in resultado.evidence
    )

    assert any(
        "Unicidad: 100 %"
        in evidencia
        for evidencia in resultado.evidence
    )

    assert any(
        "Cobertura: 100 %"
        in evidencia
        for evidencia in resultado.evidence
    )

    assert any(
        "No existen valores nulos"
        in evidencia
        for evidencia in resultado.evidence
    )


def test_umbral_posible_configurable_v6() -> None:
    """El umbral de candidatura posible debe poder configurarse."""
    serie = pd.Series(
        [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "A",
        ],
        name="codigo",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    resultado_defecto = evaluar_clave_candidata(
        analisis
    )

    resultado_personalizado = evaluar_clave_candidata(
        analisis,
        umbral_posible=90.0,
    )

    assert analisis.unique_ratio == pytest.approx(90.0)

    assert (
        resultado_defecto.level
        is CandidateKeyLevel.NO_CANDIDATE
    )

    assert (
        resultado_personalizado.level
        is CandidateKeyLevel.POSSIBLE
    )


def test_minimo_valores_fuerte_configurable_v6() -> None:
    """El mínimo de observaciones para candidatura fuerte es configurable."""
    serie = pd.Series(
        ["A001", "A002"],
        name="codigo",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    resultado_defecto = evaluar_clave_candidata(
        analisis
    )

    resultado_personalizado = evaluar_clave_candidata(
        analisis,
        minimo_valores_fuerte=2,
    )

    assert (
        resultado_defecto.level
        is CandidateKeyLevel.POSSIBLE
    )

    assert (
        resultado_personalizado.level
        is CandidateKeyLevel.STRONG
    )


def test_evaluar_claves_candidatas_dataframe_v6() -> None:
    """La evaluación conjunta debe devolver un resultado por columna."""
    datos = pd.DataFrame(
        {
            "cliente_id": [
                "C001",
                "C002",
                "C003",
                "C004",
            ],
            "estado": [
                "Activo",
                "Activo",
                "Pendiente",
                "Activo",
            ],
            "referencia": [
                "R001",
                "R002",
                "R003",
                "R004",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    resultado = evaluar_claves_candidatas(
        analisis
    )

    assert set(resultado) == {
        "cliente_id",
        "estado",
        "referencia",
    }

    assert (
        resultado["cliente_id"].level
        is CandidateKeyLevel.STRONG
    )

    assert (
        resultado["estado"].level
        is CandidateKeyLevel.NO_CANDIDATE
    )

    assert (
        resultado["referencia"].level
        is CandidateKeyLevel.STRONG
    )


def test_evaluacion_claves_no_modifica_datos_v6() -> None:
    """La evaluación de claves no debe modificar el dataset original."""
    datos = pd.DataFrame(
        {
            "cliente_id": [
                "C001",
                "C002",
                "C003",
                "C004",
            ],
            "estado": [
                "Activo",
                "Pendiente",
                "Activo",
                "Cerrado",
            ],
        }
    )

    original = datos.copy(deep=True)

    analisis = analizar_columnas(datos)

    evaluar_claves_candidatas(
        analisis
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )