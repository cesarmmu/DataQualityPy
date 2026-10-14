"""Perfilado general y numérico de datasets."""

from typing import Any

import pandas as pd

from src.column_analysis import ColumnAnalysis
from src.inference import SemanticInference, SemanticType


def perfilar_dataset(datos: pd.DataFrame) -> dict[str, Any]:
    """Genera el perfil estructural general de un DataFrame."""
    return {
        "filas": len(datos),
        "columnas": len(datos.columns),
        "nombres_columnas": list(datos.columns),
        "tipos_datos": {
            columna: str(tipo)
            for columna, tipo in datos.dtypes.items()
        },
        "valores_distintos": {
            columna: int(datos[columna].nunique(dropna=False))
            for columna in datos.columns
        },
        "memoria_bytes": int(
            datos.memory_usage(deep=True).sum()
        ),
    }


def _calcular_estadisticas_numericas(
    serie: pd.Series,
) -> dict[str, float | int]:
    """Calcula estadísticas descriptivas de una serie numérica."""
    serie_limpia = serie.dropna()

    if serie_limpia.empty:
        return {}

    return {
        "minimo": float(serie_limpia.min()),
        "maximo": float(serie_limpia.max()),
        "media": float(serie_limpia.mean()),
        "mediana": float(serie_limpia.median()),
        "desviacion_estandar": float(serie_limpia.std()),
        "q1": float(serie_limpia.quantile(0.25)),
        "q3": float(serie_limpia.quantile(0.75)),
    }


def perfilar_numericas(
    datos: pd.DataFrame,
) -> dict[str, dict[str, float | int]]:
    """
    Genera estadísticas descriptivas de columnas numéricas físicas.

    Se conserva como interfaz compatible con V2.
    """
    resultado = {}

    columnas_numericas = datos.select_dtypes(
        include="number"
    ).columns

    for columna in columnas_numericas:
        estadisticas = _calcular_estadisticas_numericas(
            datos[columna]
        )

        if estadisticas:
            resultado[columna] = estadisticas

    return resultado


def perfilar_numericas_semanticas(
    analisis_columnas: dict[object, ColumnAnalysis],
    inferencias: dict[object, SemanticInference],
) -> dict[object, dict[str, float | int]]:
    """
    Genera estadísticas para columnas semánticamente numéricas.

    Reutiliza la conversión temporal calculada durante el análisis de
    columnas. Los identificadores numéricos quedan excluidos porque su
    tipo semántico no es NUMERIC.
    """
    resultado = {}

    for columna, inferencia in inferencias.items():
        if inferencia.semantic_type is not SemanticType.NUMERIC:
            continue

        analisis = analisis_columnas.get(columna)

        if analisis is None:
            continue

        conversion = analisis.numeric_conversion

        if conversion is None:
            continue

        estadisticas = _calcular_estadisticas_numericas(
            conversion.converted_series
        )

        if estadisticas:
            resultado[columna] = estadisticas

    return resultado