"""Distribuciones y frecuencias para DataQualityPy."""

from dataclasses import dataclass
from typing import Any

import numpy as np

from src.column_analysis import ColumnAnalysis
from src.inference import SemanticInference, SemanticType


@dataclass(frozen=True)
class FrequencyValue:
    """Frecuencia observada para un valor concreto."""

    value: Any
    count: int
    ratio: float


@dataclass(frozen=True)
class FrequencyDistribution:
    """Distribución de frecuencias de una columna discreta."""

    values: tuple[FrequencyValue, ...]
    total_values: int
    total_distinct: int
    shown_distinct: int
    truncated: bool


@dataclass(frozen=True)
class NumericBin:
    """Intervalo de una distribución numérica."""

    lower: float
    upper: float
    count: int
    ratio: float


@dataclass(frozen=True)
class NumericDistribution:
    """Distribución por intervalos de una columna numérica."""

    bins: tuple[NumericBin, ...]
    total_values: int


ColumnDistribution = FrequencyDistribution | NumericDistribution | None


def _crear_distribucion_frecuencias(
    analisis: ColumnAnalysis,
    *,
    max_values: int = 10,
) -> FrequencyDistribution:
    """
    Construye una distribución de frecuencias limitada a los valores
    más frecuentes.

    Los porcentajes se calculan sobre los valores analizables de la
    columna. El límite afecta únicamente a los valores mostrados y no
    modifica las métricas originales.
    """
    serie = analisis.analyzable_series
    total_values = analisis.analyzable_count
    total_distinct = analisis.unique_count

    if total_values == 0:
        return FrequencyDistribution(
            values=(),
            total_values=0,
            total_distinct=0,
            shown_distinct=0,
            truncated=False,
        )

    frecuencias = serie.value_counts(
        dropna=True,
    )

    frecuencias_mostradas = frecuencias.head(
        max_values
    )

    valores = tuple(
        FrequencyValue(
            value=valor,
            count=int(conteo),
            ratio=float(
                conteo / total_values * 100
            ),
        )
        for valor, conteo in frecuencias_mostradas.items()
    )

    shown_distinct = len(valores)

    return FrequencyDistribution(
        values=valores,
        total_values=total_values,
        total_distinct=total_distinct,
        shown_distinct=shown_distinct,
        truncated=shown_distinct < total_distinct,
    )


def _crear_intervalo_constante(
    valor: float,
    total_values: int,
) -> NumericDistribution:
    """Construye una distribución numérica para un único valor."""
    return NumericDistribution(
        bins=(
            NumericBin(
                lower=valor,
                upper=valor,
                count=total_values,
                ratio=100.0,
            ),
        ),
        total_values=total_values,
    )


def _calcular_bordes_histograma(
    valores: np.ndarray,
    *,
    max_bins: int = 20,
) -> np.ndarray:
    """
    Calcula bordes adaptativos para una distribución numérica.

    Se utiliza la regla de Freedman-Diaconis como primera opción.
    Cuando no produce una partición útil se recurre a Sturges.
    El número final de intervalos se limita para mantener una
    distribución diagnóstica y representable.
    """
    bordes = np.histogram_bin_edges(
        valores,
        bins="fd",
    )

    numero_intervalos = len(bordes) - 1

    if numero_intervalos <= 1:
        bordes = np.histogram_bin_edges(
            valores,
            bins="sturges",
        )
        numero_intervalos = len(bordes) - 1

    if numero_intervalos > max_bins:
        bordes = np.histogram_bin_edges(
            valores,
            bins=max_bins,
        )

    return bordes


def _crear_distribucion_numerica(
    analisis: ColumnAnalysis,
    *,
    max_bins: int = 20,
) -> NumericDistribution:
    """
    Construye una distribución numérica por intervalos.

    Se utilizan únicamente los valores convertibles a número. Los
    valores incompatibles permanecen registrados en ``ColumnAnalysis``
    como fallos de conversión y no se incorporan al histograma.
    """
    conversion = analisis.numeric_conversion

    if conversion is None:
        return NumericDistribution(
            bins=(),
            total_values=0,
        )

    serie_numerica = (
        conversion.converted_series.dropna()
    )

    total_values = len(serie_numerica)

    if total_values == 0:
        return NumericDistribution(
            bins=(),
            total_values=0,
        )

    valores = serie_numerica.to_numpy(
        dtype=float,
    )

    minimo = float(np.min(valores))
    maximo = float(np.max(valores))

    if minimo == maximo:
        return _crear_intervalo_constante(
            minimo,
            total_values,
        )

    bordes = _calcular_bordes_histograma(
        valores,
        max_bins=max_bins,
    )

    conteos, bordes = np.histogram(
        valores,
        bins=bordes,
    )

    intervalos = tuple(
        NumericBin(
            lower=float(bordes[indice]),
            upper=float(bordes[indice + 1]),
            count=int(conteo),
            ratio=float(
                conteo / total_values * 100
            ),
        )
        for indice, conteo in enumerate(conteos)
    )

    return NumericDistribution(
        bins=intervalos,
        total_values=total_values,
    )


def crear_distribucion_columna(
    analisis: ColumnAnalysis,
    inferencia: SemanticInference,
    *,
    max_values: int = 10,
    max_bins: int = 20,
) -> ColumnDistribution:
    """
    Crea la distribución adecuada según el tipo semántico.

    Tipos soportados:

    - CATEGORICAL y BOOLEAN:
      distribución de frecuencias.

    - NUMERIC:
      distribución por intervalos.

    Los tipos DATE, DATETIME, IDENTIFIER y FREE_TEXT no generan
    distribución en esta fase.
    """
    tipo = inferencia.semantic_type

    if tipo in {
        SemanticType.CATEGORICAL,
        SemanticType.BOOLEAN,
    }:
        return _crear_distribucion_frecuencias(
            analisis,
            max_values=max_values,
        )

    if tipo is SemanticType.NUMERIC:
        return _crear_distribucion_numerica(
            analisis,
            max_bins=max_bins,
        )

    return None


def crear_distribuciones(
    analisis_columnas: dict[Any, ColumnAnalysis],
    inferencias: dict[Any, SemanticInference],
    *,
    max_values: int = 10,
    max_bins: int = 20,
) -> dict[Any, ColumnDistribution]:
    """
    Construye las distribuciones de las columnas disponibles.

    Cada columna utiliza su análisis técnico y su inferencia semántica.
    Las columnas sin inferencia asociada no se incluyen en el resultado.
    """
    distribuciones: dict[Any, ColumnDistribution] = {}

    for columna, analisis in analisis_columnas.items():
        inferencia = inferencias.get(
            columna
        )

        if inferencia is None:
            continue

        distribuciones[columna] = (
            crear_distribucion_columna(
                analisis,
                inferencia,
                max_values=max_values,
                max_bins=max_bins,
            )
        )

    return distribuciones