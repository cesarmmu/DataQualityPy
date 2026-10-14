"""Tests del análisis técnico reutilizable de columnas."""

import pandas as pd
import pytest

from src.column_analysis import (
    analizar_columna,
    analizar_columnas,
)


def test_analizar_columna_numerica_nativa():
    """Una columna numérica nativa debe conservar conversión numérica total."""
    serie = pd.Series(
        [10.0, 20.0, None, 30.0],
        name="precio",
    )

    resultado = analizar_columna(serie)

    assert resultado.name == "precio"
    assert resultado.total_rows == 4
    assert resultado.real_null_count == 1
    assert resultado.textual_null_count == 0
    assert resultado.analyzable_count == 3
    assert resultado.unique_count == 3
    assert resultado.unique_ratio == pytest.approx(100.0)

    assert resultado.numeric_conversion is not None
    assert resultado.numeric_conversion.attempted_count == 3
    assert resultado.numeric_conversion.convertible_count == 3
    assert resultado.numeric_conversion.success_ratio == pytest.approx(100.0)


def test_analizar_columna_numerica_almacenada_como_texto():
    """Una columna object numérica debe producir evidencia numérica."""
    serie = pd.Series(
        ["22", "38", "NA", "35", None, "54"],
        name="Age",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.pandas_dtype == "object"
    assert resultado.total_rows == 6
    assert resultado.real_null_count == 1
    assert resultado.textual_null_count == 1
    assert resultado.analyzable_count == 4

    assert resultado.numeric_conversion is not None
    assert resultado.numeric_conversion.attempted_count == 4
    assert resultado.numeric_conversion.convertible_count == 4
    assert resultado.numeric_conversion.success_ratio == pytest.approx(100.0)

    assert resultado.numeric_conversion.converted_series.tolist() == [
        22,
        38,
        35,
        54,
    ]


def test_analizar_columna_numerica_con_valor_incompatible():
    """La conversión debe medir valores incompatibles sin eliminarlos."""
    serie = pd.Series(
        ["10", "20", "error", "30"],
        name="cantidad",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.numeric_conversion is not None
    assert resultado.numeric_conversion.attempted_count == 4
    assert resultado.numeric_conversion.convertible_count == 3
    assert resultado.numeric_conversion.success_ratio == pytest.approx(75.0)

    convertida = resultado.numeric_conversion.converted_series

    assert convertida.iloc[0] == 10
    assert convertida.iloc[1] == 20
    assert pd.isna(convertida.iloc[2])
    assert convertida.iloc[3] == 30


def test_analizar_columna_detecta_nulos_textuales():
    """Los marcadores textuales de ausencia no deben ser analizables."""
    serie = pd.Series(
        ["Madrid", "NA", "", "  ", "null", None, "Sevilla"],
        name="ciudad",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.total_rows == 7
    assert resultado.real_null_count == 1
    assert resultado.textual_null_count == 4
    assert resultado.analyzable_count == 2
    assert resultado.unique_count == 2


def test_analizar_columna_fecha_textual():
    """Una columna textual de fechas debe generar evidencia temporal."""
    serie = pd.Series(
        [
            "01/01/2026",
            "15/02/2026",
            "NA",
            "31/03/2026",
        ],
        name="fecha",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.textual_null_count == 1
    assert resultado.analyzable_count == 3

    assert resultado.datetime_conversion is not None
    assert resultado.datetime_conversion.attempted_count == 3
    assert resultado.datetime_conversion.convertible_count == 3
    assert resultado.datetime_conversion.success_ratio == pytest.approx(100.0)


def test_analizar_columna_fecha_con_valor_incompatible():
    """La evidencia temporal debe conservar los fallos de conversión."""
    serie = pd.Series(
        [
            "01/01/2026",
            "texto_invalido",
            "31/03/2026",
        ],
        name="fecha",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.datetime_conversion is not None
    assert resultado.datetime_conversion.attempted_count == 3
    assert resultado.datetime_conversion.convertible_count == 2
    assert resultado.datetime_conversion.success_ratio == pytest.approx(
        200 / 3
    )


def test_analizar_columna_vacia():
    """Una columna sin valores analizables debe producir métricas coherentes."""
    serie = pd.Series(
        [None, None, None],
        name="vacia",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.total_rows == 3
    assert resultado.real_null_count == 3
    assert resultado.textual_null_count == 0
    assert resultado.analyzable_count == 0
    assert resultado.unique_count == 0
    assert resultado.unique_ratio == pytest.approx(0.0)
    assert resultado.numeric_conversion is None
    assert resultado.datetime_conversion is None


def test_analizar_columna_no_modifica_serie_original():
    """El análisis no debe alterar los datos originales."""
    serie = pd.Series(
        ["22", "NA", "35", None],
        name="Age",
        dtype="object",
    )

    original = serie.copy(deep=True)

    analizar_columna(serie)

    pd.testing.assert_series_equal(serie, original)


def test_analizar_columnas_procesa_dataframe_completo():
    """El análisis conjunto debe producir un resultado por columna."""
    datos = pd.DataFrame(
        {
            "edad": ["20", "30", "NA"],
            "ciudad": ["Madrid", "Sevilla", "Madrid"],
            "importe": [10.5, 20.0, 30.5],
        }
    )

    resultado = analizar_columnas(datos)

    assert set(resultado) == {
        "edad",
        "ciudad",
        "importe",
    }

    assert resultado["edad"].name == "edad"
    assert resultado["ciudad"].name == "ciudad"
    assert resultado["importe"].name == "importe"


def test_analizar_columnas_no_modifica_dataframe_original():
    """El análisis completo no debe alterar el DataFrame recibido."""
    datos = pd.DataFrame(
        {
            "edad": ["20", "NA", "40"],
            "fecha": ["01/01/2026", "NA", "03/01/2026"],
        }
    )

    original = datos.copy(deep=True)

    analizar_columnas(datos)

    pd.testing.assert_frame_equal(datos, original)


def test_analyzable_series_excluye_nulos_reales_y_textuales():
    """La serie analizable debe contener solo valores realmente analizables."""
    serie = pd.Series(
        ["22", "NA", None, "35", "", "54"],
        name="Age",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.analyzable_series.tolist() == ["22", "35", "54"]
    assert resultado.analyzable_count == 3


def test_analyzable_series_conserva_indices_originales():
    """La serie analizable debe conservar los índices de los valores válidos."""
    serie = pd.Series(
        ["Madrid", "NA", "Sevilla", None, "Bilbao"],
        index=[10, 20, 30, 40, 50],
        name="ciudad",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.analyzable_series.index.tolist() == [10, 30, 50]
    assert resultado.analyzable_series.tolist() == [
        "Madrid",
        "Sevilla",
        "Bilbao",
    ]


def test_analyzable_series_es_copia_independiente():
    """Modificar la serie analizable no debe alterar la serie original."""
    serie = pd.Series(
        ["22", "NA", "35", None],
        name="Age",
        dtype="object",
    )
    original = serie.copy(deep=True)

    resultado = analizar_columna(serie)
    resultado.analyzable_series.iloc[0] = "999"

    pd.testing.assert_series_equal(serie, original)

