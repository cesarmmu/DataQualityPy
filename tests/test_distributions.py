"""Tests de distribuciones y frecuencias de DataQualityPy."""

import pandas as pd
import pytest

from src.column_analysis import (
    analizar_columna,
    analizar_columnas,
)
from src.distributions import (
    FrequencyDistribution,
    NumericDistribution,
    crear_distribucion_columna,
    crear_distribuciones,
)
from src.inference import (
    InferenceConfidence,
    SemanticInference,
    SemanticType,
)


def _crear_inferencia(
    nombre: object,
    tipo: SemanticType,
) -> SemanticInference:
    """Crea una inferencia semántica controlada para los tests."""
    return SemanticInference(
        column_name=nombre,
        semantic_type=tipo,
        confidence=InferenceConfidence.HIGH,
        evidence=("Inferencia controlada para test.",),
    )


def test_distribucion_categorica_v6() -> None:
    """Una columna categórica debe conservar frecuencias y porcentajes."""
    serie = pd.Series(
        [
            "Madrid",
            "Madrid",
            "Madrid",
            "Sevilla",
            "Sevilla",
            "Bilbao",
        ],
        name="ciudad",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "ciudad",
        SemanticType.CATEGORICAL,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        FrequencyDistribution,
    )

    assert resultado.total_values == 6
    assert resultado.total_distinct == 3
    assert resultado.shown_distinct == 3
    assert resultado.truncated is False

    assert resultado.values[0].value == "Madrid"
    assert resultado.values[0].count == 3
    assert resultado.values[0].ratio == pytest.approx(50.0)

    assert resultado.values[1].value == "Sevilla"
    assert resultado.values[1].count == 2
    assert resultado.values[1].ratio == pytest.approx(
        100 / 3
    )

    assert resultado.values[2].value == "Bilbao"
    assert resultado.values[2].count == 1
    assert resultado.values[2].ratio == pytest.approx(
        100 / 6
    )


def test_distribucion_booleana_v6() -> None:
    """Una columna booleana debe generar distribución de frecuencias."""
    serie = pd.Series(
        [True, False, True, True, False],
        name="activo",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "activo",
        SemanticType.BOOLEAN,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        FrequencyDistribution,
    )

    assert resultado.total_values == 5
    assert resultado.total_distinct == 2
    assert resultado.shown_distinct == 2
    assert resultado.truncated is False

    assert resultado.values[0].value is True
    assert resultado.values[0].count == 3
    assert resultado.values[0].ratio == pytest.approx(60.0)

    assert resultado.values[1].value is False
    assert resultado.values[1].count == 2
    assert resultado.values[1].ratio == pytest.approx(40.0)


def test_distribucion_frecuencias_ignora_nulos_v6() -> None:
    """Los nulos reales y textuales no deben entrar en las frecuencias."""
    serie = pd.Series(
        [
            "Madrid",
            "Madrid",
            "Sevilla",
            None,
            "NA",
            "",
        ],
        name="ciudad",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "ciudad",
        SemanticType.CATEGORICAL,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        FrequencyDistribution,
    )

    assert resultado.total_values == 3
    assert resultado.total_distinct == 2

    assert resultado.values[0].value == "Madrid"
    assert resultado.values[0].count == 2
    assert resultado.values[0].ratio == pytest.approx(
        200 / 3
    )

    assert resultado.values[1].value == "Sevilla"
    assert resultado.values[1].count == 1
    assert resultado.values[1].ratio == pytest.approx(
        100 / 3
    )


def test_distribucion_frecuencias_top_n_v6() -> None:
    """Una cardinalidad alta debe limitarse al Top N configurado."""
    serie = pd.Series(
        [
            "A",
            "A",
            "A",
            "B",
            "B",
            "C",
            "D",
            "E",
        ],
        name="categoria",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "categoria",
        SemanticType.CATEGORICAL,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
        max_values=3,
    )

    assert isinstance(
        resultado,
        FrequencyDistribution,
    )

    assert resultado.total_values == 8
    assert resultado.total_distinct == 5
    assert resultado.shown_distinct == 3
    assert resultado.truncated is True

    assert [
        valor.value
        for valor in resultado.values
    ] == [
        "A",
        "B",
        "C",
    ]


def test_distribucion_frecuencias_columna_vacia_v6() -> None:
    """Una columna categórica sin datos debe devolver distribución vacía."""
    serie = pd.Series(
        [None, "NA", "", "null"],
        name="categoria",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "categoria",
        SemanticType.CATEGORICAL,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        FrequencyDistribution,
    )

    assert resultado.values == ()
    assert resultado.total_values == 0
    assert resultado.total_distinct == 0
    assert resultado.shown_distinct == 0
    assert resultado.truncated is False


def test_distribucion_numerica_v6() -> None:
    """Una columna numérica debe generar intervalos coherentes."""
    serie = pd.Series(
        list(range(1, 101)),
        name="importe",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "importe",
        SemanticType.NUMERIC,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        NumericDistribution,
    )

    assert resultado.total_values == 100
    assert len(resultado.bins) >= 1
    assert len(resultado.bins) <= 20

    assert sum(
        intervalo.count
        for intervalo in resultado.bins
    ) == 100

    assert sum(
        intervalo.ratio
        for intervalo in resultado.bins
    ) == pytest.approx(100.0)


def test_distribucion_numerica_respeta_max_bins_v6() -> None:
    """El número de intervalos debe respetar el máximo configurado."""
    serie = pd.Series(
        list(range(1, 1001)),
        name="importe",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "importe",
        SemanticType.NUMERIC,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
        max_bins=5,
    )

    assert isinstance(
        resultado,
        NumericDistribution,
    )

    assert 1 <= len(resultado.bins) <= 5

    assert sum(
        intervalo.count
        for intervalo in resultado.bins
    ) == 1000


def test_distribucion_numerica_constante_v6() -> None:
    """Una columna numérica constante debe generar un único intervalo."""
    serie = pd.Series(
        [10, 10, 10, 10],
        name="cantidad",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "cantidad",
        SemanticType.NUMERIC,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        NumericDistribution,
    )

    assert resultado.total_values == 4
    assert len(resultado.bins) == 1

    intervalo = resultado.bins[0]

    assert intervalo.lower == pytest.approx(10.0)
    assert intervalo.upper == pytest.approx(10.0)
    assert intervalo.count == 4
    assert intervalo.ratio == pytest.approx(100.0)


def test_distribucion_numerica_unico_valor_v6() -> None:
    """Un único valor numérico debe producir un único intervalo."""
    serie = pd.Series(
        [25],
        name="cantidad",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "cantidad",
        SemanticType.NUMERIC,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        NumericDistribution,
    )

    assert resultado.total_values == 1
    assert len(resultado.bins) == 1

    intervalo = resultado.bins[0]

    assert intervalo.lower == pytest.approx(25.0)
    assert intervalo.upper == pytest.approx(25.0)
    assert intervalo.count == 1
    assert intervalo.ratio == pytest.approx(100.0)


def test_distribucion_numerica_excluye_incompatibles_v6() -> None:
    """
    Los valores no convertibles no deben incorporarse a la
    distribución numérica.
    """
    serie = pd.Series(
        [
            "10",
            "20",
            "error",
            "30",
            "40",
        ],
        name="cantidad",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "cantidad",
        SemanticType.NUMERIC,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert analisis.numeric_conversion is not None
    assert analisis.numeric_conversion.failed_count == 1

    assert isinstance(
        resultado,
        NumericDistribution,
    )

    assert resultado.total_values == 4

    assert sum(
        intervalo.count
        for intervalo in resultado.bins
    ) == 4


def test_distribucion_numerica_sin_conversion_v6() -> None:
    """
    Una inferencia numérica controlada sin conversión disponible
    debe devolver una distribución vacía de forma segura.
    """
    serie = pd.Series(
        [None, "NA", "", "null"],
        name="cantidad",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    assert analisis.numeric_conversion is None

    inferencia = _crear_inferencia(
        "cantidad",
        SemanticType.NUMERIC,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert isinstance(
        resultado,
        NumericDistribution,
    )

    assert resultado.total_values == 0
    assert resultado.bins == ()


@pytest.mark.parametrize(
    "tipo",
    [
        SemanticType.DATE,
        SemanticType.DATETIME,
        SemanticType.IDENTIFIER,
        SemanticType.FREE_TEXT,
    ],
)
def test_tipos_sin_distribucion_v6(
    tipo: SemanticType,
) -> None:
    """
    Los tipos excluidos de V6.1.4 no deben generar distribución.
    """
    serie = pd.Series(
        ["A", "B", "C", "D"],
        name="columna",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "columna",
        tipo,
    )

    resultado = crear_distribucion_columna(
        analisis,
        inferencia,
    )

    assert resultado is None


def test_crear_distribuciones_dataframe_v6() -> None:
    """La evaluación conjunta debe respetar cada tipo semántico."""
    datos = pd.DataFrame(
        {
            "ciudad": [
                "Madrid",
                "Madrid",
                "Sevilla",
                "Bilbao",
            ],
            "importe": [
                10,
                20,
                30,
                40,
            ],
            "comentario": [
                "A",
                "B",
                "C",
                "D",
            ],
        }
    )

    analisis = analizar_columnas(
        datos
    )

    inferencias = {
        "ciudad": _crear_inferencia(
            "ciudad",
            SemanticType.CATEGORICAL,
        ),
        "importe": _crear_inferencia(
            "importe",
            SemanticType.NUMERIC,
        ),
        "comentario": _crear_inferencia(
            "comentario",
            SemanticType.FREE_TEXT,
        ),
    }

    resultado = crear_distribuciones(
        analisis,
        inferencias,
    )

    assert set(resultado) == {
        "ciudad",
        "importe",
        "comentario",
    }

    assert isinstance(
        resultado["ciudad"],
        FrequencyDistribution,
    )

    assert isinstance(
        resultado["importe"],
        NumericDistribution,
    )

    assert resultado["comentario"] is None


def test_crear_distribuciones_omite_columna_sin_inferencia_v6() -> None:
    """Una columna sin inferencia semántica no debe incorporarse."""
    datos = pd.DataFrame(
        {
            "ciudad": [
                "Madrid",
                "Sevilla",
                "Bilbao",
            ],
            "sin_inferencia": [
                "A",
                "B",
                "C",
            ],
        }
    )

    analisis = analizar_columnas(
        datos
    )

    inferencias = {
        "ciudad": _crear_inferencia(
            "ciudad",
            SemanticType.CATEGORICAL,
        ),
    }

    resultado = crear_distribuciones(
        analisis,
        inferencias,
    )

    assert set(resultado) == {
        "ciudad",
    }


def test_distribuciones_no_modifican_dataframe_v6() -> None:
    """La creación de distribuciones no debe modificar los datos."""
    datos = pd.DataFrame(
        {
            "ciudad": [
                "Madrid",
                "Sevilla",
                "Madrid",
                None,
            ],
            "importe": [
                10,
                20,
                30,
                40,
            ],
        }
    )

    original = datos.copy(
        deep=True
    )

    analisis = analizar_columnas(
        datos
    )

    inferencias = {
        "ciudad": _crear_inferencia(
            "ciudad",
            SemanticType.CATEGORICAL,
        ),
        "importe": _crear_inferencia(
            "importe",
            SemanticType.NUMERIC,
        ),
    }

    crear_distribuciones(
        analisis,
        inferencias,
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )