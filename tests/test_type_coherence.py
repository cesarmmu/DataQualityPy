"""Tests dirigidos del análisis de coherencia de tipos V7-C3."""

import pandas as pd
import pytest

from src.column_analysis import analizar_columna
from src.inference import InferenceConfidence, SemanticInference, SemanticType
from src.type_coherence import (
    ObservedContentType,
    TypeCoherenceStatus,
    analizar_coherencia_tipo,
)


def _crear_inferencia(nombre: object, tipo: SemanticType) -> SemanticInference:
    """Crea una inferencia controlada para aislar los tests de C3."""
    return SemanticInference(
        column_name=nombre,
        semantic_type=tipo,
        confidence=InferenceConfidence.HIGH,
        evidence=("Inferencia controlada para el test.",),
    )


def test_c3_object_numerico_total_es_discrepancia_potencial_v7() -> None:
    serie = pd.Series(["10", "20", "30", "40"], name="importe", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("importe", SemanticType.NUMERIC)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.physical_type == "object"
    assert resultado.observed_type is ObservedContentType.NUMERIC
    assert resultado.status is TypeCoherenceStatus.POTENTIAL_MISMATCH
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_object_fecha_total_es_discrepancia_potencial_v7() -> None:
    serie = pd.Series(
        ["01/01/2026", "15/02/2026", "31/03/2026"],
        name="fecha",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("fecha", SemanticType.DATE)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.DATE
    assert resultado.status is TypeCoherenceStatus.POTENTIAL_MISMATCH
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_object_datetime_total_es_discrepancia_potencial_v7() -> None:
    serie = pd.Series(
        [
            "2026-01-01 08:30:00",
            "2026-01-02 12:15:00",
            "2026-01-03 18:45:00",
        ],
        name="instante",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("instante", SemanticType.DATETIME)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.DATE
    assert resultado.status is TypeCoherenceStatus.POTENTIAL_MISMATCH
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_object_booleano_total_es_discrepancia_potencial_v7() -> None:
    serie = pd.Series(["true", "false", "yes", "no"], name="activo", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("activo", SemanticType.BOOLEAN)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.BOOLEAN
    assert resultado.status is TypeCoherenceStatus.POTENTIAL_MISMATCH
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_numerico_fisico_y_semantico_es_coherente_v7() -> None:
    serie = pd.Series([10, 20, 30, 40], name="importe", dtype="int64")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("importe", SemanticType.NUMERIC)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.NUMERIC
    assert resultado.status is TypeCoherenceStatus.COHERENT
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_datetime_fisico_y_semantico_es_coherente_v7() -> None:
    serie = pd.Series(
        pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        name="fecha",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("fecha", SemanticType.DATE)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.DATE
    assert resultado.status is TypeCoherenceStatus.COHERENT
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_booleano_fisico_y_semantico_es_coherente_v7() -> None:
    serie = pd.Series([True, False, True, False], name="activo", dtype="bool")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("activo", SemanticType.BOOLEAN)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.BOOLEAN
    assert resultado.status is TypeCoherenceStatus.COHERENT
    assert resultado.evidence_ratio == pytest.approx(100.0)


def test_c3_compatibilidad_parcial_es_evidencia_insuficiente_v7() -> None:
    serie = pd.Series(["10", "20", "error", "30"], name="importe", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("importe", SemanticType.NUMERIC)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is ObservedContentType.NUMERIC
    assert resultado.status is TypeCoherenceStatus.INSUFFICIENT_EVIDENCE
    assert resultado.evidence_ratio == pytest.approx(75.0)


def test_c3_identificador_numerico_textual_queda_protegido_v7() -> None:
    serie = pd.Series(
        ["1001", "1002", "1003", "1004"], name="cliente_id", dtype="object"
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("cliente_id", SemanticType.IDENTIFIER)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is None
    assert resultado.status is TypeCoherenceStatus.INSUFFICIENT_EVIDENCE
    assert resultado.evidence_ratio is None


def test_c3_cinco_digitos_no_infiere_conversion_numerica_v7() -> None:
    serie = pd.Series(["28053", "28041", "28012"], name="valor", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("valor", SemanticType.IDENTIFIER)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is None
    assert resultado.status is TypeCoherenceStatus.INSUFFICIENT_EVIDENCE
    assert resultado.evidence_ratio is None


def test_c3_email_no_participa_en_coherencia_de_tipo_v7() -> None:
    serie = pd.Series(
        ["ana@example.com", "pepe@example.com", "luz@example.org"],
        name="contacto",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("contacto", SemanticType.FREE_TEXT)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is None
    assert resultado.status is TypeCoherenceStatus.INSUFFICIENT_EVIDENCE
    assert resultado.evidence_ratio is None


def test_c3_columna_sin_valores_analizables_v7() -> None:
    serie = pd.Series([None, "NA", "", "null"], name="vacia", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("vacia", SemanticType.CATEGORICAL)
    resultado = analizar_coherencia_tipo(analisis, inferencia)
    assert resultado.observed_type is None
    assert resultado.status is TypeCoherenceStatus.INSUFFICIENT_EVIDENCE
    assert resultado.evidence_ratio is None
