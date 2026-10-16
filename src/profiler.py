"""Perfilado estructural, estadístico y semántico de datasets."""

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.column_analysis import ColumnAnalysis
from src.inference import SemanticInference, SemanticType


def perfilar_dataset(datos: pd.DataFrame) -> dict[str, Any]:
    """
    Genera el perfil estructural general de un DataFrame.

    Esta función conserva la interfaz histórica de DataQualityPy para
    mantener la compatibilidad con los informes y tests existentes.
    """
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
    """
    Calcula estadísticas descriptivas de una serie numérica.

    Los valores nulos se excluyen del cálculo. Si no existen valores
    disponibles, devuelve un diccionario vacío.
    """
    serie_limpia = serie.dropna()

    if serie_limpia.empty:
        return {}

    minimo = float(serie_limpia.min())
    maximo = float(serie_limpia.max())

    return {
        "minimo": minimo,
        "maximo": maximo,
        "media": float(serie_limpia.mean()),
        "mediana": float(serie_limpia.median()),
        "desviacion_estandar": float(serie_limpia.std()),
        "q1": float(serie_limpia.quantile(0.25)),
        "q3": float(serie_limpia.quantile(0.75)),
        "rango": maximo - minimo,
    }


def perfilar_numericas(
    datos: pd.DataFrame,
) -> dict[str, dict[str, float | int]]:
    """
    Genera estadísticas descriptivas de columnas numéricas físicas.

    Se conserva como interfaz compatible con las versiones anteriores
    de DataQualityPy.
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
    analisis_columnas: Mapping[Any, ColumnAnalysis],
    inferencias: Mapping[Any, SemanticInference],
) -> dict[Any, dict[str, float | int]]:
    """
    Genera estadísticas para columnas semánticamente numéricas.

    Reutiliza la conversión numérica calculada durante el análisis de
    columnas. Los identificadores numéricos quedan excluidos porque su
    tipo semántico no es NUMERIC.

    Las claves se tipan como Any porque pandas permite etiquetas de
    columna de distintos tipos y el perfilador no impone un tipo
    concreto para dichas etiquetas.
    """
    resultado: dict[Any, dict[str, float | int]] = {}

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


def _crear_perfil_comun(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """
    Construye las métricas comunes de perfilado de una columna.

    Estas métricas representan hechos observables y no incluyen
    diagnósticos, recomendaciones ni decisiones sobre la calidad.
    """
    return {
        "tipo_pandas": analisis.pandas_dtype,
        "filas": analisis.total_rows,
        "valores_analizables": analisis.analyzable_count,
        "cobertura_porcentaje": analisis.analyzable_ratio,
        "nulos_reales": analisis.real_null_count,
        "nulos_textuales": analisis.textual_null_count,
        "nulos_totales": analisis.null_count,
        "nulos_porcentaje": analisis.null_ratio,
        "valores_distintos": analisis.unique_count,
        "unicidad_porcentaje": analisis.unique_ratio,
        "valor_mas_frecuente": analisis.most_frequent_value,
        "frecuencia_mas_alta": analisis.most_frequent_count,
        "frecuencia_mas_alta_porcentaje": (
            analisis.most_frequent_ratio
        ),
        "valores_en_repeticion": (
            analisis.repeated_value_count
        ),
        "repeticion_porcentaje": (
            analisis.repeated_value_ratio
        ),
        "exceso_duplicados": (
            analisis.duplicate_excess_count
        ),
        "exceso_duplicados_porcentaje": (
            analisis.duplicate_excess_ratio
        ),
    }


def _crear_perfil_numerico(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """Construye el perfil específico de una columna numérica."""
    conversion = analisis.numeric_conversion

    if conversion is None:
        return {}

    estadisticas = _calcular_estadisticas_numericas(
        conversion.converted_series
    )

    if not estadisticas:
        return {}

    return {
        "valores_convertibles": conversion.convertible_count,
        "valores_no_convertibles": conversion.failed_count,
        "conversion_porcentaje": conversion.success_ratio,
        **estadisticas,
    }


def _crear_perfil_temporal(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """Construye el perfil específico de una columna temporal."""
    conversion = analisis.datetime_conversion

    if conversion is None:
        return {}

    serie_temporal = conversion.converted_series.dropna()

    perfil = {
        "valores_convertibles": conversion.convertible_count,
        "valores_no_convertibles": conversion.failed_count,
        "conversion_porcentaje": conversion.success_ratio,
    }

    if serie_temporal.empty:
        return perfil

    fecha_minima = serie_temporal.min()
    fecha_maxima = serie_temporal.max()

    perfil.update(
        {
            "fecha_minima": fecha_minima,
            "fecha_maxima": fecha_maxima,
            "rango_temporal": fecha_maxima - fecha_minima,
        }
    )

    return perfil


def _crear_perfil_texto(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """Construye métricas de longitud para una columna de texto."""
    serie = analisis.analyzable_series

    if serie.empty:
        return {}

    longitudes = serie.astype("string").str.len().dropna()

    if longitudes.empty:
        return {}

    return {
        "longitud_minima": int(longitudes.min()),
        "longitud_maxima": int(longitudes.max()),
        "longitud_media": float(longitudes.mean()),
    }


def _crear_perfil_categorico(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """Construye el perfil específico de una columna categórica."""
    return {
        "numero_categorias": analisis.unique_count,
        "categoria_dominante": analisis.most_frequent_value,
        "frecuencia_dominante": analisis.most_frequent_count,
        "frecuencia_dominante_porcentaje": (
            analisis.most_frequent_ratio
        ),
    }


def _crear_perfil_identificador(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """Construye el perfil específico de una columna identificadora."""
    return {
        "valores_distintos": analisis.unique_count,
        "unicidad_porcentaje": analisis.unique_ratio,
        "valores_duplicados": analisis.duplicate_excess_count,
        "duplicados_porcentaje": (
            analisis.duplicate_excess_ratio
        ),
    }


def _crear_perfil_especifico(
    analisis: ColumnAnalysis,
    inferencia: SemanticInference,
) -> dict[str, Any]:
    """
    Selecciona el perfil específico según el tipo semántico inferido.

    La inferencia determina qué estadísticas tienen sentido, evitando
    aplicar métricas de magnitud a identificadores numéricos.
    """
    tipo_semantico = inferencia.semantic_type

    if tipo_semantico is SemanticType.NUMERIC:
        return _crear_perfil_numerico(analisis)

    if tipo_semantico in {
        SemanticType.DATE,
        SemanticType.DATETIME,
    }:
        return _crear_perfil_temporal(analisis)

    if tipo_semantico is SemanticType.CATEGORICAL:
        return _crear_perfil_categorico(analisis)

    if tipo_semantico is SemanticType.IDENTIFIER:
        return _crear_perfil_identificador(analisis)

    if tipo_semantico is SemanticType.FREE_TEXT:
        return _crear_perfil_texto(analisis)

    return {}


def perfilar_columnas_semanticas(
    analisis_columnas: Mapping[Any, ColumnAnalysis],
    inferencias: Mapping[Any, SemanticInference],
) -> dict[Any, dict[str, Any]]:
    """
    Genera un perfil enriquecido para cada columna del dataset.

    Cada perfil contiene una sección común y otra específica adaptada
    al tipo semántico inferido. La función describe los datos, pero no
    genera diagnósticos ni propone acciones de limpieza.

    Las etiquetas de columna pueden ser de cualquier tipo admitido por
    pandas. El perfilador conserva esas etiquetas sin transformarlas.
    """
    resultado: dict[Any, dict[str, Any]] = {}

    for columna, analisis in analisis_columnas.items():
        inferencia = inferencias.get(columna)

        perfil: dict[str, Any] = {
            "comun": _crear_perfil_comun(analisis),
            "especifico": {},
        }

        if inferencia is not None:
            perfil["especifico"] = _crear_perfil_especifico(
                analisis,
                inferencia,
            )

        resultado[columna] = perfil

    return resultado