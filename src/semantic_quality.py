"""Análisis de calidad guiados por tipos semánticos."""

from collections.abc import Mapping

from src.column_analysis import ColumnAnalysis
from src.inference import (
    SemanticInference,
    SemanticType,
    es_valor_booleano_compatible,
)
from src.quality import _calcular_outliers_iqr


def analizar_outliers_semanticos(
    analisis_columnas: Mapping[object, ColumnAnalysis],
    inferencias: Mapping[object, SemanticInference],
    factor_iqr: float = 1.5,
) -> dict:
    """
    Detecta outliers solo en columnas semánticamente numéricas.

    Reutiliza las conversiones temporales ya calculadas durante el análisis
    técnico. Los identificadores quedan excluidos aunque su dtype físico
    sea numérico.
    """
    resultado = {}

    for columna, inferencia in inferencias.items():
        if inferencia.semantic_type is not SemanticType.NUMERIC:
            continue

        analisis_columna = analisis_columnas.get(columna)

        if analisis_columna is None:
            continue

        conversion = analisis_columna.numeric_conversion

        if conversion is None:
            continue

        analisis_outliers = _calcular_outliers_iqr(
            conversion.converted_series,
            factor_iqr,
        )

        if analisis_outliers is not None:
            resultado[columna] = analisis_outliers

    return resultado



def _crear_resultado_incompatibilidad(
    tipo_semantico: SemanticType,
    cantidad_incompatibles: int,
    total_analizable: int,
) -> dict:
    """Construye las métricas agregadas de incompatibilidad semántica."""
    porcentaje = (
        cantidad_incompatibles / total_analizable * 100
        if total_analizable > 0
        else 0.0
    )

    return {
        "tipo_semantico": tipo_semantico.value,
        "cantidad_incompatibles": cantidad_incompatibles,
        "porcentaje_incompatibles": float(porcentaje),
    }


def analizar_incompatibilidades_semanticas(
    analisis_columnas: Mapping[object, ColumnAnalysis],
    inferencias: Mapping[object, SemanticInference],
) -> dict:
    """
    Detecta valores incompatibles con el tipo semántico asignado.

    Los nulos reales y textuales ya están excluidos de analyzable_series, por
    lo que no se consideran incompatibilidades de tipo. El resultado contiene
    únicamente métricas agregadas y solo incluye columnas con incompatibilidades.
    """
    resultado = {}

    for columna, inferencia in inferencias.items():
        tipo_semantico = inferencia.semantic_type

        if tipo_semantico not in {
            SemanticType.NUMERIC,
            SemanticType.DATE,
            SemanticType.DATETIME,
            SemanticType.BOOLEAN,
        }:
            continue

        analisis_columna = analisis_columnas.get(columna)

        if analisis_columna is None or analisis_columna.analyzable_count == 0:
            continue

        if tipo_semantico is SemanticType.NUMERIC:
            conversion = analisis_columna.numeric_conversion
            cantidad_incompatibles = (
                analisis_columna.analyzable_count
                if conversion is None
                else conversion.attempted_count - conversion.convertible_count
            )

        elif tipo_semantico in {SemanticType.DATE, SemanticType.DATETIME}:
            conversion = analisis_columna.datetime_conversion
            cantidad_incompatibles = (
                analisis_columna.analyzable_count
                if conversion is None
                else conversion.attempted_count - conversion.convertible_count
            )

        else:
            cantidad_incompatibles = sum(
                not es_valor_booleano_compatible(valor)
                for valor in analisis_columna.analyzable_series
            )

        if cantidad_incompatibles == 0:
            continue

        resultado[columna] = _crear_resultado_incompatibilidad(
            tipo_semantico,
            cantidad_incompatibles,
            analisis_columna.analyzable_count,
        )

    return resultado
