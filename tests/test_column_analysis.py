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
    assert resultado.numeric_conversion.success_ratio == pytest.approx(
        100.0
    )


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
    assert resultado.numeric_conversion.success_ratio == pytest.approx(
        100.0
    )

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
    assert resultado.numeric_conversion.success_ratio == pytest.approx(
        75.0
    )

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
    assert resultado.datetime_conversion.success_ratio == pytest.approx(
        100.0
    )


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

    assert resultado.analyzable_series.tolist() == [
        "22",
        "35",
        "54",
    ]
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

    assert resultado.analyzable_series.index.tolist() == [
        10,
        30,
        50,
    ]
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


def test_metricas_cobertura_v6():
    """Las propiedades V6 deben resumir cobertura y ausencia de datos."""
    serie = pd.Series(
        ["Madrid", "NA", None, "Sevilla", ""],
        name="ciudad",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.null_count == 3
    assert resultado.null_ratio == pytest.approx(60.0)
    assert resultado.analyzable_count == 2
    assert resultado.analyzable_ratio == pytest.approx(40.0)


def test_frecuencia_dominante_v6():
    """El análisis debe conservar la frecuencia del valor dominante."""
    serie = pd.Series(
        [
            "Madrid",
            "Sevilla",
            "Madrid",
            "Bilbao",
            "Madrid",
            None,
        ],
        name="ciudad",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.most_frequent_value == "Madrid"
    assert resultado.most_frequent_count == 3
    assert resultado.most_frequent_ratio == pytest.approx(60.0)


def test_frecuencia_dominante_columna_sin_datos_v6():
    """Una columna sin datos analizables debe tener frecuencia vacía."""
    serie = pd.Series(
        [None, "NA", ""],
        name="vacia",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.most_frequent_value is None
    assert resultado.most_frequent_count == 0
    assert resultado.most_frequent_ratio == pytest.approx(0.0)


def test_failed_count_conversion_v6():
    """La conversión debe exponer directamente el número de fallos."""
    serie = pd.Series(
        ["10", "error", "20", "incorrecto", "30"],
        name="cantidad",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.numeric_conversion is not None
    assert resultado.numeric_conversion.attempted_count == 5
    assert resultado.numeric_conversion.convertible_count == 3
    assert resultado.numeric_conversion.failed_count == 2


def test_cardinalidad_repeticion_parcial_v6():
    """La cardinalidad debe distinguir repetición y exceso duplicado."""
    serie = pd.Series(
        ["A", "A", "A", "B", "C"],
        name="codigo",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.analyzable_count == 5
    assert resultado.unique_count == 3
    assert resultado.unique_ratio == pytest.approx(60.0)

    assert resultado.repeated_value_count == 3
    assert resultado.repeated_value_ratio == pytest.approx(60.0)

    assert resultado.duplicate_excess_count == 2
    assert resultado.duplicate_excess_ratio == pytest.approx(40.0)


def test_cardinalidad_columna_totalmente_unica_v6():
    """Una columna única no debe presentar ninguna repetición."""
    serie = pd.Series(
        ["A", "B", "C", "D"],
        name="codigo",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.analyzable_count == 4
    assert resultado.unique_count == 4
    assert resultado.unique_ratio == pytest.approx(100.0)

    assert resultado.repeated_value_count == 0
    assert resultado.repeated_value_ratio == pytest.approx(0.0)

    assert resultado.duplicate_excess_count == 0
    assert resultado.duplicate_excess_ratio == pytest.approx(0.0)


def test_cardinalidad_columna_constante_v6():
    """Una columna constante debe reflejar repetición y exceso duplicado."""
    serie = pd.Series(
        ["A", "A", "A", "A"],
        name="estado",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.analyzable_count == 4
    assert resultado.unique_count == 1
    assert resultado.unique_ratio == pytest.approx(25.0)

    assert resultado.repeated_value_count == 4
    assert resultado.repeated_value_ratio == pytest.approx(100.0)

    assert resultado.duplicate_excess_count == 3
    assert resultado.duplicate_excess_ratio == pytest.approx(75.0)


def test_cardinalidad_columna_sin_valores_analizables_v6():
    """Una columna vacía debe producir cardinalidad y repetición nulas."""
    serie = pd.Series(
        [None, "NA", "", "null"],
        name="vacia",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.analyzable_count == 0
    assert resultado.unique_count == 0
    assert resultado.unique_ratio == pytest.approx(0.0)

    assert resultado.repeated_value_count == 0
    assert resultado.repeated_value_ratio == pytest.approx(0.0)

    assert resultado.duplicate_excess_count == 0
    assert resultado.duplicate_excess_ratio == pytest.approx(0.0)

# ---------------------------------------------------------------------------
# V7-C1 — Patrones estructurales de texto
# ---------------------------------------------------------------------------


def test_patron_estructural_uniforme_v7():
    """C1 debe detectar un patrón textual uniforme sin inferir significado."""
    serie = pd.Series(
        ["ABC-1234", "XYZ-5678", "DEF-9012"],
        name="codigo",
        dtype="object",
    )

    resultado = analizar_columna(serie)
    patrones = resultado.structural_patterns

    assert patrones is not None
    assert patrones.analyzed_count == 3
    assert patrones.dominant_pattern == "AAA-NNNN"
    assert patrones.dominant_count == 3
    assert patrones.dominant_ratio == pytest.approx(100.0)
    assert patrones.distinct_pattern_count == 1
    assert patrones.pattern_frequencies == (("AAA-NNNN", 3),)


def test_patron_estructural_dominante_con_variante_v7():
    """C1 debe cuantificar variantes sin convertirlas en errores."""
    serie = pd.Series(
        ["ABC-1234", "XYZ-5678", "DEF-9012", "AB-3456"],
        name="codigo",
        dtype="object",
    )

    resultado = analizar_columna(serie)
    patrones = resultado.structural_patterns

    assert patrones is not None
    assert patrones.analyzed_count == 4
    assert patrones.dominant_pattern == "AAA-NNNN"
    assert patrones.dominant_count == 3
    assert patrones.dominant_ratio == pytest.approx(75.0)
    assert patrones.distinct_pattern_count == 2
    assert patrones.pattern_frequencies == (
        ("AAA-NNNN", 3),
        ("AA-NNNN", 1),
    )


def test_patron_estructural_con_espacios_y_simbolos_v7():
    """C1 debe representar espacios y conservar símbolos visibles."""
    serie = pd.Series(
        ["AB 123", "CD 456", "EF 789"],
        name="referencia",
        dtype="object",
    )

    resultado = analizar_columna(serie)
    patrones = resultado.structural_patterns

    assert patrones is not None
    assert patrones.dominant_pattern == "AASNNN"
    assert patrones.dominant_ratio == pytest.approx(100.0)
    assert patrones.distinct_pattern_count == 1


def test_patron_estructural_requiere_muestra_minima_v7():
    """Menos de tres valores analizables no deben producir patrón."""
    serie = pd.Series(
        ["ABC-1234", "XYZ-5678"],
        name="codigo",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.structural_patterns is None


def test_patron_estructural_descarta_texto_libre_largo_v7():
    """C1 no debe generar patrones para contenido predominantemente largo."""
    serie = pd.Series(
        [
            "Cliente solicita información adicional sobre el estado de su expediente.",
            "Pendiente de recibir la documentación necesaria para continuar el proceso.",
            "Se realizará una nueva revisión cuando se incorporen todos los documentos.",
        ],
        name="observaciones",
        dtype="object",
    )

    resultado = analizar_columna(serie)

    assert resultado.structural_patterns is None


def test_patron_estructural_cinco_digitos_no_infiere_significado_v7():
    """Cinco dígitos textuales son solo un patrón NNNNN para C1."""
    serie = pd.Series(
        ["28053", "28041", "28012"],
        name="valor",
        dtype="object",
    )

    resultado = analizar_columna(serie)
    patrones = resultado.structural_patterns

    assert patrones is not None
    assert patrones.dominant_pattern == "NNNNN"
    assert patrones.dominant_count == 3
    assert patrones.dominant_ratio == pytest.approx(100.0)
    assert patrones.distinct_pattern_count == 1


def test_patron_estructural_no_se_aplica_a_columna_numerica_v7():
    """Una columna físicamente numérica no debe recibir patrones de C1."""
    serie = pd.Series(
        [28053, 28041, 28012],
        name="valor",
        dtype="int64",
    )

    resultado = analizar_columna(serie)

    assert resultado.structural_patterns is None
