"""Tests para las funciones de perfilado de DataQualityPy."""

import pandas as pd
import pytest

from src.column_analysis import analizar_columnas
from src.inference import inferir_tipo_semantico
from src.profiler import (
    perfilar_dataset,
    perfilar_numericas,
    perfilar_numericas_semanticas,
)
from src.quality import es_nulo_textual


def _generar_inferencias(
    datos: pd.DataFrame,
) -> dict:
    """Genera análisis e inferencias para los tests de perfilado."""
    analisis_columnas = analizar_columnas(datos)
    inferencias = {}

    for columna, analisis in analisis_columnas.items():
        serie_evaluable = datos[columna].dropna()

        if (
            pd.api.types.is_object_dtype(serie_evaluable)
            or isinstance(serie_evaluable.dtype, pd.StringDtype)
        ):
            mascara_nulos_textuales = serie_evaluable.map(
                es_nulo_textual
            )
            serie_evaluable = serie_evaluable.loc[
                ~mascara_nulos_textuales
            ]

        inferencias[columna] = inferir_tipo_semantico(
            analisis,
            serie_evaluable,
        )

    return {
        "analisis": analisis_columnas,
        "inferencias": inferencias,
    }


def test_perfilar_dataset() -> None:
    """Comprueba el perfil estructural básico de un dataset."""
    datos = pd.DataFrame(
        {
            "producto": ["Portatil", "Raton", "Raton"],
            "precio": [900.0, 25.0, 25.0],
        }
    )

    resultado = perfilar_dataset(datos)

    assert resultado["filas"] == 3
    assert resultado["columnas"] == 2
    assert resultado["nombres_columnas"] == [
        "producto",
        "precio",
    ]
    assert resultado["tipos_datos"]["producto"] == "object"
    assert resultado["tipos_datos"]["precio"] == "float64"
    assert resultado["valores_distintos"]["producto"] == 2
    assert resultado["valores_distintos"]["precio"] == 2
    assert resultado["memoria_bytes"] > 0


def test_perfilar_numericas() -> None:
    """Comprueba las estadísticas de una columna numérica."""
    datos = pd.DataFrame(
        {
            "valor": [10.0, 20.0, 30.0, 40.0],
        }
    )

    resultado = perfilar_numericas(datos)["valor"]

    assert resultado["minimo"] == pytest.approx(10.0)
    assert resultado["maximo"] == pytest.approx(40.0)
    assert resultado["media"] == pytest.approx(25.0)
    assert resultado["mediana"] == pytest.approx(25.0)
    assert resultado["desviacion_estandar"] == pytest.approx(
        12.909944487358056
    )
    assert resultado["q1"] == pytest.approx(17.5)
    assert resultado["q3"] == pytest.approx(32.5)


def test_perfilar_numericas_ignora_columna_vacia() -> None:
    """Comprueba que una columna numérica vacía no genere estadísticas."""
    datos = pd.DataFrame(
        {
            "valor": [10.0, 20.0, 30.0],
            "vacia": [None, None, None],
        }
    )

    resultado = perfilar_numericas(datos)

    assert "valor" in resultado
    assert "vacia" not in resultado


def test_perfilar_numericas_semanticas_incluye_object_numerico() -> None:
    """
    Comprueba que una columna object semánticamente numérica
    genere estadísticas descriptivas.
    """
    datos = pd.DataFrame(
        {
            "Age": [
                "20",
                "30",
                "NA",
                "40",
                None,
                "50",
            ],
        },
        dtype="object",
    )

    contexto = _generar_inferencias(datos)

    resultado = perfilar_numericas_semanticas(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert "Age" in resultado

    estadisticas = resultado["Age"]

    assert estadisticas["minimo"] == pytest.approx(20.0)
    assert estadisticas["maximo"] == pytest.approx(50.0)
    assert estadisticas["media"] == pytest.approx(35.0)
    assert estadisticas["mediana"] == pytest.approx(35.0)
    assert estadisticas["q1"] == pytest.approx(27.5)
    assert estadisticas["q3"] == pytest.approx(42.5)


def test_perfilar_numericas_semanticas_excluye_identificador() -> None:
    """
    Comprueba que un identificador numérico no reciba
    estadísticas de magnitud.
    """
    datos = pd.DataFrame(
        {
            "cliente_id": [
                1001,
                1002,
                1003,
                1004,
                1005,
            ],
            "importe": [
                10.0,
                20.0,
                30.0,
                40.0,
                50.0,
            ],
        }
    )

    contexto = _generar_inferencias(datos)

    resultado = perfilar_numericas_semanticas(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert "cliente_id" not in resultado
    assert "importe" in resultado


def test_perfilar_numericas_semanticas_no_modifica_datos() -> None:
    """Comprueba que el perfilado semántico no altere el DataFrame."""
    datos = pd.DataFrame(
        {
            "Age": [
                "20",
                "NA",
                "30",
                None,
                "40",
            ],
        },
        dtype="object",
    )

    original = datos.copy(deep=True)

    contexto = _generar_inferencias(datos)

    perfilar_numericas_semanticas(
        contexto["analisis"],
        contexto["inferencias"],
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )