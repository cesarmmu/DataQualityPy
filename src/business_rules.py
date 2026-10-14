"""Evaluación de reglas de negocio configurables para DataQualityPy."""

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.column_analysis import ColumnAnalysis
from src.inference import SemanticInference, SemanticType


def _crear_resultado_regla(
    valor_regla: Any,
    cantidad_incumplimientos: int,
    total_evaluable: int,
) -> dict[str, Any]:
    """Construye el resultado agregado de una regla incumplida."""
    porcentaje = (
        (cantidad_incumplimientos / total_evaluable) * 100
        if total_evaluable > 0
        else 0.0
    )

    return {
        "valor_regla": valor_regla,
        "cantidad_incumplimientos": cantidad_incumplimientos,
        "porcentaje_incumplimientos": float(porcentaje),
    }


def _evaluar_limite_numerico(
    analisis: ColumnAnalysis,
    valor_regla: int | float,
    *,
    es_minimo: bool,
) -> dict[str, Any] | None:
    """Evalúa un límite numérico sobre los valores convertibles."""
    conversion = analisis.numeric_conversion

    if conversion is None:
        return None

    serie_numerica = conversion.converted_series.dropna()

    if serie_numerica.empty:
        return None

    if es_minimo:
        mascara_incumplimientos = serie_numerica < valor_regla
    else:
        mascara_incumplimientos = serie_numerica > valor_regla

    cantidad_incumplimientos = int(mascara_incumplimientos.sum())

    if cantidad_incumplimientos == 0:
        return None

    return _crear_resultado_regla(
        valor_regla,
        cantidad_incumplimientos,
        len(serie_numerica),
    )


def _evaluar_valores_permitidos(
    analisis: ColumnAnalysis,
    valores_permitidos: list[Any],
) -> dict[str, Any] | None:
    """Evalúa por igualdad exacta los valores permitidos configurados."""
    serie_evaluable = analisis.analyzable_series

    if serie_evaluable.empty:
        return None

    mascara_incumplimientos = ~serie_evaluable.isin(valores_permitidos)
    cantidad_incumplimientos = int(mascara_incumplimientos.sum())

    if cantidad_incumplimientos == 0:
        return None

    return _crear_resultado_regla(
        valores_permitidos,
        cantidad_incumplimientos,
        len(serie_evaluable),
    )


def evaluar_reglas_negocio(
    analisis_columnas: Mapping[object, ColumnAnalysis],
    inferencias: Mapping[object, SemanticInference],
    reglas_columnas: Mapping[object, Mapping[str, Any]],
) -> dict[object, dict[str, dict[str, Any]]]:
    """
    Evalúa las reglas de negocio explícitas configuradas por columna.

    Los nulos reales y textuales ya están excluidos de ``analyzable_series``.
    Los límites min/max sólo se aplican a columnas semánticamente numéricas
    y excluyen del denominador los valores incompatibles con ese tipo.
    """
    resultados: dict[object, dict[str, dict[str, Any]]] = {}

    for columna, reglas in reglas_columnas.items():
        if columna not in analisis_columnas:
            raise ValueError(
                f"La columna configurada '{columna}' no existe "
                "en el conjunto de datos."
            )

        analisis = analisis_columnas[columna]
        inferencia = inferencias.get(columna)

        resultados_columna: dict[str, dict[str, Any]] = {}

        if (
            inferencia is not None
            and inferencia.semantic_type is SemanticType.NUMERIC
        ):
            if "min" in reglas:
                resultado_min = _evaluar_limite_numerico(
                    analisis,
                    reglas["min"],
                    es_minimo=True,
                )

                if resultado_min is not None:
                    resultados_columna["min"] = resultado_min

            if "max" in reglas:
                resultado_max = _evaluar_limite_numerico(
                    analisis,
                    reglas["max"],
                    es_minimo=False,
                )

                if resultado_max is not None:
                    resultados_columna["max"] = resultado_max

        if "valores_permitidos" in reglas:
            resultado_permitidos = _evaluar_valores_permitidos(
                analisis,
                reglas["valores_permitidos"],
            )

            if resultado_permitidos is not None:
                resultados_columna["valores_permitidos"] = (
                    resultado_permitidos
                )

        if resultados_columna:
            resultados[columna] = resultados_columna

    return resultados
