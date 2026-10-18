"""Análisis técnico reutilizable de columnas para DataQualityPy."""

from dataclasses import dataclass

import pandas as pd

from src.quality import es_nulo_textual


@dataclass
class ConversionAnalysis:
    """Resultado del análisis de una posible conversión de datos."""

    attempted_count: int
    convertible_count: int
    success_ratio: float
    converted_series: pd.Series

    @property
    def failed_count(self) -> int:
        """Devuelve el número de valores que no pudieron convertirse."""
        return self.attempted_count - self.convertible_count


@dataclass(frozen=True)
class StructuralPatternAnalysis:
    """Resultado descriptivo del análisis de patrones estructurales de texto."""

    analyzed_count: int
    dominant_pattern: str
    dominant_count: int
    dominant_ratio: float
    distinct_pattern_count: int
    pattern_frequencies: tuple[tuple[str, int], ...]


@dataclass
class ColumnAnalysis:
    """Evidencias técnicas obtenidas al analizar una columna."""

    name: object
    pandas_dtype: str
    total_rows: int

    real_null_count: int
    textual_null_count: int
    analyzable_count: int

    unique_count: int
    unique_ratio: float

    most_frequent_value: object | None
    most_frequent_count: int
    most_frequent_ratio: float

    repeated_value_count: int
    repeated_value_ratio: float

    duplicate_excess_count: int
    duplicate_excess_ratio: float

    analyzable_series: pd.Series

    numeric_conversion: ConversionAnalysis | None
    datetime_conversion: ConversionAnalysis | None
    structural_patterns: StructuralPatternAnalysis | None

    @property
    def null_count(self) -> int:
        """Devuelve el total de nulos reales y nulos textuales."""
        return self.real_null_count + self.textual_null_count

    @property
    def null_ratio(self) -> float:
        """Devuelve el porcentaje total de valores nulos."""
        if self.total_rows == 0:
            return 0.0

        return float(
            (self.null_count / self.total_rows) * 100
        )

    @property
    def analyzable_ratio(self) -> float:
        """Devuelve el porcentaje de valores disponibles para análisis."""
        if self.total_rows == 0:
            return 0.0

        return float(
            (self.analyzable_count / self.total_rows) * 100
        )


def _obtener_serie_evaluable(
    serie: pd.Series,
) -> tuple[pd.Series, int]:
    """
    Obtiene los valores utilizables para análisis.

    Excluye nulos reales y posibles nulos conservados como texto,
    sin modificar la serie original.
    """
    serie_no_nula = serie.dropna()

    if serie_no_nula.empty:
        return serie_no_nula.copy(), 0

    if not (
        pd.api.types.is_object_dtype(serie_no_nula)
        or isinstance(serie_no_nula.dtype, pd.StringDtype)
    ):
        return serie_no_nula.copy(), 0

    mascara_nulos_textuales = serie_no_nula.map(
        es_nulo_textual
    )

    textual_null_count = int(
        mascara_nulos_textuales.sum()
    )

    serie_evaluable = serie_no_nula.loc[
        ~mascara_nulos_textuales
    ].copy()

    return serie_evaluable, textual_null_count


def _analizar_frecuencia(
    serie: pd.Series,
) -> tuple[object | None, int, float]:
    """
    Obtiene la frecuencia dominante de una serie analizable.

    Devuelve el valor más frecuente, su número de apariciones y el
    porcentaje que representa sobre los valores analizables.
    """
    if serie.empty:
        return None, 0, 0.0

    frecuencias = serie.value_counts(dropna=True)

    if frecuencias.empty:
        return None, 0, 0.0

    most_frequent_value = frecuencias.index[0]
    most_frequent_count = int(frecuencias.iloc[0])

    most_frequent_ratio = (
        (most_frequent_count / len(serie)) * 100
        if len(serie) > 0
        else 0.0
    )

    return (
        most_frequent_value,
        most_frequent_count,
        float(most_frequent_ratio),
    )


def _analizar_repeticion(
    serie: pd.Series,
) -> tuple[int, float, int, float]:
    """
    Calcula métricas descriptivas de repetición y duplicación.

    ``repeated_value_count`` cuenta todas las filas cuyo valor aparece
    más de una vez.

    ``duplicate_excess_count`` cuenta únicamente las apariciones que
    exceden la primera de cada valor.

    Ejemplo::

        A, A, A, B, C

        repeated_value_count = 3
        duplicate_excess_count = 2

    Los porcentajes se calculan sobre los valores analizables.
    """
    analyzable_count = len(serie)

    if analyzable_count == 0:
        return 0, 0.0, 0, 0.0

    frecuencias = serie.value_counts(dropna=True)

    frecuencias_repetidas = frecuencias.loc[
        frecuencias > 1
    ]

    repeated_value_count = int(
        frecuencias_repetidas.sum()
    )

    duplicate_excess_count = int(
        (frecuencias_repetidas - 1).sum()
    )

    repeated_value_ratio = (
        repeated_value_count
        / analyzable_count
        * 100
    )

    duplicate_excess_ratio = (
        duplicate_excess_count
        / analyzable_count
        * 100
    )

    return (
        repeated_value_count,
        float(repeated_value_ratio),
        duplicate_excess_count,
        float(duplicate_excess_ratio),
    )


def _analizar_conversion_numerica(
    serie: pd.Series,
) -> ConversionAnalysis | None:
    """Prueba una interpretación numérica sin modificar los datos originales."""
    if serie.empty:
        return None

    if pd.api.types.is_numeric_dtype(serie):
        serie_convertida = serie.copy()
        attempted_count = len(serie_convertida)

        return ConversionAnalysis(
            attempted_count=attempted_count,
            convertible_count=attempted_count,
            success_ratio=100.0,
            converted_series=serie_convertida,
        )

    if not (
        pd.api.types.is_object_dtype(serie)
        or isinstance(serie.dtype, pd.StringDtype)
    ):
        return None

    serie_convertida = pd.to_numeric(
        serie,
        errors="coerce",
    )

    attempted_count = len(serie)
    convertible_count = int(
        serie_convertida.notna().sum()
    )

    success_ratio = (
        (convertible_count / attempted_count) * 100
        if attempted_count > 0
        else 0.0
    )

    return ConversionAnalysis(
        attempted_count=attempted_count,
        convertible_count=convertible_count,
        success_ratio=float(success_ratio),
        converted_series=serie_convertida,
    )


def _analizar_conversion_datetime(
    serie: pd.Series,
) -> ConversionAnalysis | None:
    """Prueba una interpretación temporal sin modificar los datos originales."""
    if serie.empty:
        return None

    if pd.api.types.is_datetime64_any_dtype(serie):
        serie_convertida = serie.copy()
        attempted_count = len(serie_convertida)

        return ConversionAnalysis(
            attempted_count=attempted_count,
            convertible_count=attempted_count,
            success_ratio=100.0,
            converted_series=serie_convertida,
        )

    if not (
        pd.api.types.is_object_dtype(serie)
        or isinstance(serie.dtype, pd.StringDtype)
    ):
        return None

    serie_convertida = pd.to_datetime(
        serie,
        format="mixed",
        errors="coerce",
        dayfirst=True,
    )

    attempted_count = len(serie)
    convertible_count = int(
        serie_convertida.notna().sum()
    )

    success_ratio = (
        (convertible_count / attempted_count) * 100
        if attempted_count > 0
        else 0.0
    )

    return ConversionAnalysis(
        attempted_count=attempted_count,
        convertible_count=convertible_count,
        success_ratio=float(success_ratio),
        converted_series=serie_convertida,
    )


def _es_serie_textual(serie: pd.Series) -> bool:
    """Indica si una serie puede analizarse como contenido textual."""
    return bool(
        pd.api.types.is_object_dtype(serie)
        or isinstance(serie.dtype, pd.StringDtype)
    )


def _crear_patron_estructural(valor: object) -> str:
    """Representa la estructura visible de un valor textual."""
    texto = str(valor)
    patron = []
    for caracter in texto:
        if caracter.isalpha():
            patron.append("A")
        elif caracter.isdigit():
            patron.append("N")
        elif caracter == " ":
            patron.append("S")
        else:
            patron.append(caracter)
    return "".join(patron)


def _analizar_patrones_estructurales(
    serie: pd.Series,
    *,
    longitud_maxima: int = 50,
    minimo_valores: int = 3,
) -> StructuralPatternAnalysis | None:
    """Describe patrones estructurales observados en contenido textual."""
    if serie.empty or not _es_serie_textual(serie):
        return None

    textos = serie.astype("string").dropna()
    if len(textos) < minimo_valores:
        return None

    longitudes = textos.str.len()
    dentro_limite = longitudes <= longitud_maxima
    if float(dentro_limite.mean()) < 0.5:
        return None

    textos_analizables = textos.loc[dentro_limite]
    if len(textos_analizables) < minimo_valores:
        return None

    patrones = textos_analizables.map(_crear_patron_estructural)
    frecuencias = patrones.value_counts(dropna=False)
    if frecuencias.empty:
        return None

    analyzed_count = len(patrones)
    dominant_pattern = str(frecuencias.index[0])
    dominant_count = int(frecuencias.iloc[0])
    dominant_ratio = dominant_count / analyzed_count * 100
    pattern_frequencies = tuple(
        (str(patron), int(cantidad))
        for patron, cantidad in frecuencias.items()
    )

    return StructuralPatternAnalysis(
        analyzed_count=analyzed_count,
        dominant_pattern=dominant_pattern,
        dominant_count=dominant_count,
        dominant_ratio=float(dominant_ratio),
        distinct_pattern_count=len(frecuencias),
        pattern_frequencies=pattern_frequencies,
    )


def analizar_columna(
    serie: pd.Series,
    nombre: object | None = None,
) -> ColumnAnalysis:
    """
    Analiza técnicamente una columna sin decidir su tipo semántico.

    El resultado contiene evidencias reutilizables por el motor de
    inferencia, perfilado y otros componentes de la auditoría.
    """
    nombre_columna = (
        serie.name
        if nombre is None
        else nombre
    )

    total_rows = len(serie)
    real_null_count = int(serie.isna().sum())

    serie_evaluable, textual_null_count = (
        _obtener_serie_evaluable(serie)
    )

    analyzable_count = len(serie_evaluable)

    unique_count = int(
        serie_evaluable.nunique(dropna=True)
    )

    unique_ratio = (
        (unique_count / analyzable_count) * 100
        if analyzable_count > 0
        else 0.0
    )

    (
        most_frequent_value,
        most_frequent_count,
        most_frequent_ratio,
    ) = _analizar_frecuencia(
        serie_evaluable
    )

    (
        repeated_value_count,
        repeated_value_ratio,
        duplicate_excess_count,
        duplicate_excess_ratio,
    ) = _analizar_repeticion(
        serie_evaluable
    )

    numeric_conversion = (
        _analizar_conversion_numerica(
            serie_evaluable
        )
    )

    datetime_conversion = (
        _analizar_conversion_datetime(
            serie_evaluable
        )
    )

    structural_patterns = (
        _analizar_patrones_estructurales(
            serie_evaluable
        )
    )

    return ColumnAnalysis(
        name=nombre_columna,
        pandas_dtype=str(serie.dtype),
        total_rows=total_rows,
        real_null_count=real_null_count,
        textual_null_count=textual_null_count,
        analyzable_count=analyzable_count,
        unique_count=unique_count,
        unique_ratio=float(unique_ratio),
        most_frequent_value=most_frequent_value,
        most_frequent_count=most_frequent_count,
        most_frequent_ratio=most_frequent_ratio,
        repeated_value_count=repeated_value_count,
        repeated_value_ratio=repeated_value_ratio,
        duplicate_excess_count=duplicate_excess_count,
        duplicate_excess_ratio=duplicate_excess_ratio,
        analyzable_series=serie_evaluable,
        numeric_conversion=numeric_conversion,
        datetime_conversion=datetime_conversion,
        structural_patterns=structural_patterns,
    )


def analizar_columnas(
    datos: pd.DataFrame,
) -> dict[object, ColumnAnalysis]:
    """Analiza todas las columnas de un DataFrame una sola vez."""
    return {
        columna: analizar_columna(
            datos[columna],
            nombre=columna,
        )
        for columna in datos.columns
    }