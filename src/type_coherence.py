"""Análisis de coherencia entre tipo físico y contenido observado."""

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from src.column_analysis import ColumnAnalysis
from src.inference import SemanticInference, SemanticType
from src.semantic_compatibility import (
    SemanticCompatibilityAnalysis,
    SemanticCompatibilityType,
    analizar_compatibilidad_semantica,
)


class ObservedContentType(str, Enum):
    """Familias de contenido consideradas por V7-C3."""

    NUMERIC = "numeric"
    DATE = "date"
    BOOLEAN = "boolean"


class TypeCoherenceStatus(str, Enum):
    """Estados conservadores de coherencia físico-contenido."""

    COHERENT = "coherent"
    POTENTIAL_MISMATCH = "potential_mismatch"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class TypeCoherenceAnalysis:
    """Resultado estructurado del análisis de coherencia de tipos."""

    physical_type: str
    observed_type: ObservedContentType | None
    status: TypeCoherenceStatus
    evidence_ratio: float | None
    evidence: tuple[str, ...]


def _tipo_fisico(analisis: ColumnAnalysis) -> str:
    """Clasifica el dtype físico en las familias relevantes para C3."""
    dtype = pd.api.types.pandas_dtype(analisis.pandas_dtype)

    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"

    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"

    if pd.api.types.is_numeric_dtype(dtype):
        return "numeric"

    if pd.api.types.is_object_dtype(dtype) or isinstance(dtype, pd.StringDtype):
        return "text"

    return "other"


def _tipo_observado_desde_inferencia(
    inferencia: SemanticInference,
) -> ObservedContentType | None:
    """Limita C3 a las tres familias aprobadas."""
    if inferencia.semantic_type is SemanticType.NUMERIC:
        return ObservedContentType.NUMERIC

    if inferencia.semantic_type in {SemanticType.DATE, SemanticType.DATETIME}:
        return ObservedContentType.DATE

    if inferencia.semantic_type is SemanticType.BOOLEAN:
        return ObservedContentType.BOOLEAN

    return None


def _tipo_compatibilidad(
    tipo_observado: ObservedContentType,
) -> SemanticCompatibilityType:
    """Relaciona una familia C3 con su evidencia C2."""
    if tipo_observado is ObservedContentType.NUMERIC:
        return SemanticCompatibilityType.NUMERIC

    if tipo_observado is ObservedContentType.DATE:
        return SemanticCompatibilityType.DATE

    return SemanticCompatibilityType.BOOLEAN


def _obtener_ratio(
    compatibilidad: SemanticCompatibilityAnalysis,
    tipo_observado: ObservedContentType,
) -> float | None:
    """Obtiene de C2 el porcentaje compatible para la familia observada."""
    tipo_c2 = _tipo_compatibilidad(tipo_observado)

    for evidencia in compatibilidad.compatibilities:
        if evidencia.compatibility_type is tipo_c2:
            return evidencia.compatible_ratio

    return None


def analizar_coherencia_tipo(
    analisis: ColumnAnalysis,
    inferencia: SemanticInference,
) -> TypeCoherenceAnalysis:
    """
    Evalúa la coherencia entre el dtype físico y el contenido observado.

    C3 es deliberadamente conservador: solo considera contenido NUMERIC,
    DATE y BOOLEAN; exige compatibilidad C2 del 100 %; protege identificadores
    y otros tipos semánticos; y no diagnostica errores ni recomienda cambios.
    """
    physical_type = analisis.pandas_dtype
    familia_fisica = _tipo_fisico(analisis)

    if analisis.analyzable_count == 0:
        return TypeCoherenceAnalysis(
            physical_type=physical_type,
            observed_type=None,
            status=TypeCoherenceStatus.INSUFFICIENT_EVIDENCE,
            evidence_ratio=None,
            evidence=("No existen valores analizables en la columna.",),
        )

    tipo_observado = _tipo_observado_desde_inferencia(inferencia)

    if tipo_observado is None:
        return TypeCoherenceAnalysis(
            physical_type=physical_type,
            observed_type=None,
            status=TypeCoherenceStatus.INSUFFICIENT_EVIDENCE,
            evidence_ratio=None,
            evidence=(
                "El tipo semántico inferido no pertenece a las familias "
                "evaluadas por C3.",
            ),
        )

    compatibilidad = analizar_compatibilidad_semantica(analisis)
    ratio = _obtener_ratio(compatibilidad, tipo_observado)

    if ratio is None or ratio < 100.0:
        return TypeCoherenceAnalysis(
            physical_type=physical_type,
            observed_type=tipo_observado,
            status=TypeCoherenceStatus.INSUFFICIENT_EVIDENCE,
            evidence_ratio=ratio,
            evidence=(
                "La compatibilidad observada no alcanza el 100 % requerido "
                "por C3.",
            ),
        )

    if familia_fisica == tipo_observado.value:
        return TypeCoherenceAnalysis(
            physical_type=physical_type,
            observed_type=tipo_observado,
            status=TypeCoherenceStatus.COHERENT,
            evidence_ratio=ratio,
            evidence=(
                "El tipo físico y el contenido observado pertenecen a la "
                "misma familia.",
            ),
        )

    if familia_fisica == "text":
        return TypeCoherenceAnalysis(
            physical_type=physical_type,
            observed_type=tipo_observado,
            status=TypeCoherenceStatus.POTENTIAL_MISMATCH,
            evidence_ratio=ratio,
            evidence=(
                "La columna se almacena como texto, pero el 100 % de los "
                f"valores analizables es compatible con {tipo_observado.value}.",
            ),
        )

    return TypeCoherenceAnalysis(
        physical_type=physical_type,
        observed_type=tipo_observado,
        status=TypeCoherenceStatus.INSUFFICIENT_EVIDENCE,
        evidence_ratio=ratio,
        evidence=(
            "C3 no establece una discrepancia automática entre estas "
            "familias físicas y observadas.",
        ),
    )
