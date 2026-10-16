"""Inferencia semántica de columnas para DataQualityPy."""

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from src.column_analysis import ColumnAnalysis
from src.quality import nombre_indica_identificador


class SemanticType(str, Enum):
    """Tipos semánticos fundamentales reconocidos por DataQualityPy."""

    NUMERIC = "numerico"
    DATE = "fecha"
    DATETIME = "fecha_hora"
    BOOLEAN = "booleano_binario"
    CATEGORICAL = "categorico"
    IDENTIFIER = "identificador"
    FREE_TEXT = "texto_libre"


class InferenceConfidence(str, Enum):
    """Niveles cualitativos de confianza de una inferencia."""

    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baja"


@dataclass(frozen=True)
class SemanticInference:
    """Resultado de la inferencia semántica de una columna."""

    column_name: object
    semantic_type: SemanticType
    confidence: InferenceConfidence
    evidence: tuple[str, ...]
    source: str = "inferred"


def _es_booleano_nativo(analisis: ColumnAnalysis) -> bool:
    """Indica si Pandas ya representa la columna como booleana."""
    return analisis.pandas_dtype in {"bool", "boolean"}


def es_valor_booleano_compatible(valor: object) -> bool:
    """Indica si un valor es compatible con una representación booleana."""
    if isinstance(valor, (bool,)):
        return True

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return valor in {0, 1}

    if isinstance(valor, str):
        valor_normalizado = valor.strip().lower()
        return valor_normalizado in {
            "true",
            "false",
            "yes",
            "no",
            "si",
            "sí",
        }

    return False


def _es_booleano_textual(serie: pd.Series) -> bool:
    """Detecta representaciones textuales inequívocas de valores binarios."""
    if serie.empty:
        return False

    valores = {
        str(valor).strip().lower()
        for valor in serie
    }

    pares_booleanos = (
        {"true", "false"},
        {"yes", "no"},
        {"si", "no"},
        {"sí", "no"},
    )

    return valores in pares_booleanos


def _contiene_componente_horario(serie: pd.Series) -> bool:
    """Indica si una serie temporal contiene alguna hora distinta de medianoche."""
    if serie.empty:
        return False

    serie_valida = serie.dropna()

    if serie_valida.empty:
        return False

    return bool(
        (
            (serie_valida.dt.hour != 0)
            | (serie_valida.dt.minute != 0)
            | (serie_valida.dt.second != 0)
            | (serie_valida.dt.microsecond != 0)
        ).any()
    )


def _confianza_por_evidencia(
    *,
    evidencia_completa: bool,
    cantidad_evidencias: int,
    minimo_evidencias_confianza_alta: int,
) -> InferenceConfidence:
    """
    Asigna confianza a inferencias basadas en evidencia cuantificable.

    Una evidencia completa solo alcanza confianza ALTA cuando existe
    una cantidad mínima de observaciones analizables. Una muestra
    limitada mantiene como máximo confianza MEDIA.
    """
    if (
        evidencia_completa
        and cantidad_evidencias
        >= minimo_evidencias_confianza_alta
    ):
        return InferenceConfidence.HIGH

    return InferenceConfidence.MEDIUM


def _evidencia_muestra_limitada(
    *,
    cantidad_evidencias: int,
    minimo_evidencias_confianza_alta: int,
) -> tuple[str, ...]:
    """Explica cuándo la cantidad de evidencia limita la confianza."""
    if (
        cantidad_evidencias
        >= minimo_evidencias_confianza_alta
    ):
        return ()

    return (
        (
            f"Solo existen {cantidad_evidencias} valores analizables; "
            "la cantidad de evidencia limita la confianza de la "
            "inferencia."
        ),
    )


def _inferir_identificador(
    analisis: ColumnAnalysis,
    umbral_unicidad: float,
    minimo_evidencias_confianza_alta: int,
) -> SemanticInference | None:
    """Evalúa si una columna presenta evidencias suficientes de identificador."""
    nombre_indicativo = nombre_indica_identificador(analisis.name)

    if not nombre_indicativo or analisis.analyzable_count == 0:
        return None

    if analisis.unique_ratio < umbral_unicidad:
        return None

    confianza = _confianza_por_evidencia(
        evidencia_completa=(
            analisis.unique_ratio == 100.0
        ),
        cantidad_evidencias=(
            analisis.analyzable_count
        ),
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    evidencia = [
        "El nombre de la columna sugiere un identificador.",
        (
            "La proporción de valores únicos es "
            f"{analisis.unique_ratio:.2f}%."
        ),
    ]

    evidencia.extend(
        _evidencia_muestra_limitada(
            cantidad_evidencias=(
                analisis.analyzable_count
            ),
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    return SemanticInference(
        column_name=analisis.name,
        semantic_type=SemanticType.IDENTIFIER,
        confidence=confianza,
        evidence=tuple(evidencia),
    )


def _inferir_booleano(
    analisis: ColumnAnalysis,
    serie_evaluable: pd.Series,
) -> SemanticInference | None:
    """Evalúa si una columna representa información booleana o binaria."""
    if analisis.analyzable_count == 0:
        return None

    if _es_booleano_nativo(analisis):
        return SemanticInference(
            column_name=analisis.name,
            semantic_type=SemanticType.BOOLEAN,
            confidence=InferenceConfidence.HIGH,
            evidence=("Pandas representa la columna como booleana.",),
        )

    if analisis.unique_count != 2:
        return None

    if pd.api.types.is_numeric_dtype(serie_evaluable):
        valores = set(serie_evaluable.dropna().tolist())

        if valores == {0, 1}:
            return SemanticInference(
                column_name=analisis.name,
                semantic_type=SemanticType.BOOLEAN,
                confidence=InferenceConfidence.HIGH,
                evidence=("La columna contiene exclusivamente 0 y 1.",),
            )

    if _es_booleano_textual(serie_evaluable):
        return SemanticInference(
            column_name=analisis.name,
            semantic_type=SemanticType.BOOLEAN,
            confidence=InferenceConfidence.HIGH,
            evidence=(
                "La columna contiene exclusivamente un par booleano textual.",
            ),
        )

    return None


def _inferir_temporal(
    analisis: ColumnAnalysis,
    umbral_fecha: float,
    minimo_evidencias_confianza_alta: int,
) -> SemanticInference | None:
    """Evalúa las evidencias de fecha o fecha-hora."""
    conversion = analisis.datetime_conversion

    if conversion is None or conversion.attempted_count == 0:
        return None

    if conversion.success_ratio < umbral_fecha:
        return None

    confianza = _confianza_por_evidencia(
        evidencia_completa=(
            conversion.success_ratio == 100.0
        ),
        cantidad_evidencias=(
            conversion.attempted_count
        ),
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    tipo = (
        SemanticType.DATETIME
        if _contiene_componente_horario(
            conversion.converted_series
        )
        else SemanticType.DATE
    )

    evidencia = [
        (
            "La conversión temporal tuvo un éxito del "
            f"{conversion.success_ratio:.2f}%."
        )
    ]

    evidencia.extend(
        _evidencia_muestra_limitada(
            cantidad_evidencias=(
                conversion.attempted_count
            ),
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    return SemanticInference(
        column_name=analisis.name,
        semantic_type=tipo,
        confidence=confianza,
        evidence=tuple(evidencia),
    )


def _inferir_numerico(
    analisis: ColumnAnalysis,
    minimo_evidencias_confianza_alta: int,
) -> SemanticInference | None:
    """Evalúa las evidencias de contenido numérico."""
    conversion = analisis.numeric_conversion

    if conversion is None or conversion.attempted_count == 0:
        return None

    if conversion.success_ratio < 80.0:
        return None

    confianza = _confianza_por_evidencia(
        evidencia_completa=(
            conversion.success_ratio == 100.0
        ),
        cantidad_evidencias=(
            conversion.attempted_count
        ),
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    evidencia = [
        (
            "La conversión numérica tuvo un éxito del "
            f"{conversion.success_ratio:.2f}%."
        )
    ]

    evidencia.extend(
        _evidencia_muestra_limitada(
            cantidad_evidencias=(
                conversion.attempted_count
            ),
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    return SemanticInference(
        column_name=analisis.name,
        semantic_type=SemanticType.NUMERIC,
        confidence=confianza,
        evidence=tuple(evidencia),
    )


def _inferir_categorico(
    analisis: ColumnAnalysis,
    max_categorias: int,
    max_porcentaje_categorias: float,
    minimo_evidencias_confianza_alta: int,
) -> SemanticInference | None:
    """Evalúa si una columna presenta baja cardinalidad categórica."""
    if analisis.analyzable_count == 0:
        return None

    if (
        analisis.unique_count <= max_categorias
        and analisis.unique_ratio <= max_porcentaje_categorias
    ):
        confianza = (
            InferenceConfidence.HIGH
            if (
                analisis.analyzable_count
                >= minimo_evidencias_confianza_alta
            )
            else InferenceConfidence.MEDIUM
        )

        evidencia = [
            (
                f"La columna contiene {analisis.unique_count} valores "
                "distintos."
            ),
            (
                "La proporción de valores distintos es "
                f"{analisis.unique_ratio:.2f}%."
            ),
        ]

        evidencia.extend(
            _evidencia_muestra_limitada(
                cantidad_evidencias=(
                    analisis.analyzable_count
                ),
                minimo_evidencias_confianza_alta=(
                    minimo_evidencias_confianza_alta
                ),
            )
        )

        return SemanticInference(
            column_name=analisis.name,
            semantic_type=SemanticType.CATEGORICAL,
            confidence=confianza,
            evidence=tuple(evidencia),
        )

    return None


def _crear_inferencia_declarada(
    analisis: ColumnAnalysis,
    tipo_declarado: str,
) -> SemanticInference:
    """Crea el resultado para un tipo semántico declarado explícitamente."""
    return SemanticInference(
        column_name=analisis.name,
        semantic_type=SemanticType(tipo_declarado),
        confidence=InferenceConfidence.HIGH,
        evidence=(
            "El tipo semántico fue declarado explícitamente "
            "en la configuración.",
        ),
        source="declared",
    )


def inferir_tipo_semantico(
    analisis: ColumnAnalysis,
    serie_evaluable: pd.Series,
    *,
    tipo_declarado: str | None = None,
    umbral_unicidad: float = 90.0,
    umbral_fecha: float = 80.0,
    max_categorias: int = 20,
    max_porcentaje_categorias: float = 20.0,
    minimo_evidencias_confianza_alta: int = 3,
) -> SemanticInference:
    """
    Determina el tipo semántico de una columna.

    Un tipo declarado explícitamente tiene prioridad absoluta. Si no existe,
    se aplica la jerarquía:
    identificador -> booleano/binario -> fecha/fecha-hora ->
    numérico -> categórico -> texto libre.

    La confianza es cualitativa y expresa la solidez de las evidencias
    disponibles. No representa una puntuación de calidad ni una
    probabilidad estadística.

    Las inferencias basadas en unicidad, conversión o cardinalidad
    requieren una cantidad mínima de evidencias para alcanzar confianza
    ALTA. Los tipos declarados y los patrones booleanos inequívocos
    mantienen confianza ALTA independientemente del tamaño de la muestra.
    """
    if tipo_declarado is not None:
        return _crear_inferencia_declarada(
            analisis,
            tipo_declarado,
        )

    inferencia = _inferir_identificador(
        analisis,
        umbral_unicidad=umbral_unicidad,
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    if inferencia is not None:
        return inferencia

    inferencia = _inferir_booleano(
        analisis,
        serie_evaluable,
    )

    if inferencia is not None:
        return inferencia

    inferencia = _inferir_temporal(
        analisis,
        umbral_fecha=umbral_fecha,
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    if inferencia is not None:
        return inferencia

    inferencia = _inferir_numerico(
        analisis,
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    if inferencia is not None:
        return inferencia

    inferencia = _inferir_categorico(
        analisis,
        max_categorias=max_categorias,
        max_porcentaje_categorias=max_porcentaje_categorias,
        minimo_evidencias_confianza_alta=(
            minimo_evidencias_confianza_alta
        ),
    )

    if inferencia is not None:
        return inferencia

    return SemanticInference(
        column_name=analisis.name,
        semantic_type=SemanticType.FREE_TEXT,
        confidence=InferenceConfidence.MEDIUM,
        evidence=(
            "No se alcanzaron las evidencias mínimas de otro tipo semántico.",
        ),
    )