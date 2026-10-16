"""Tests para las funciones de perfilado de DataQualityPy."""

import pandas as pd
import pytest

from src.column_analysis import analizar_columnas
from src.inference import (
    InferenceConfidence,
    SemanticInference,
    SemanticType,
    inferir_tipo_semantico,
)
from src.profiler import (
    perfilar_columnas_semanticas,
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


def _crear_inferencia(
    columna: object,
    tipo: SemanticType,
) -> SemanticInference:
    """Crea una inferencia controlada para aislar los tests del perfilador."""
    return SemanticInference(
        column_name=columna,
        semantic_type=tipo,
        confidence=InferenceConfidence.HIGH,
        evidence=("Inferencia controlada para el test.",),
    )


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


def test_perfil_enriquecido_incluye_metricas_comunes_v6() -> None:
    """
    El perfil V6 debe exponer cobertura, cardinalidad,
    frecuencia y repetición.
    """
    datos = pd.DataFrame(
        {
            "ciudad": [
                "Madrid",
                "Madrid",
                "Sevilla",
                "NA",
                None,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    inferencias = {
        "ciudad": _crear_inferencia(
            "ciudad",
            SemanticType.CATEGORICAL,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    comun = resultado["ciudad"]["comun"]

    assert comun["filas"] == 5
    assert comun["valores_analizables"] == 3
    assert comun["cobertura_porcentaje"] == pytest.approx(60.0)

    assert comun["nulos_reales"] == 1
    assert comun["nulos_textuales"] == 1
    assert comun["nulos_totales"] == 2
    assert comun["nulos_porcentaje"] == pytest.approx(40.0)

    assert comun["valores_distintos"] == 2
    assert comun["unicidad_porcentaje"] == pytest.approx(200 / 3)

    assert comun["valor_mas_frecuente"] == "Madrid"
    assert comun["frecuencia_mas_alta"] == 2
    assert comun["frecuencia_mas_alta_porcentaje"] == pytest.approx(
        200 / 3
    )

    assert comun["valores_en_repeticion"] == 2
    assert comun["repeticion_porcentaje"] == pytest.approx(
        200 / 3
    )

    assert comun["exceso_duplicados"] == 1
    assert comun["exceso_duplicados_porcentaje"] == pytest.approx(
        100 / 3
    )


def test_perfil_enriquecido_numerico_v6() -> None:
    """El perfil numérico V6 debe reutilizar la conversión ya calculada."""
    datos = pd.DataFrame(
        {
            "importe": ["10", "20", "error", "30"],
        },
        dtype="object",
    )

    analisis = analizar_columnas(datos)

    inferencias = {
        "importe": _crear_inferencia(
            "importe",
            SemanticType.NUMERIC,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    especifico = resultado["importe"]["especifico"]

    assert especifico["valores_convertibles"] == 3
    assert especifico["valores_no_convertibles"] == 1
    assert especifico["conversion_porcentaje"] == pytest.approx(75.0)
    assert especifico["minimo"] == pytest.approx(10.0)
    assert especifico["maximo"] == pytest.approx(30.0)
    assert especifico["media"] == pytest.approx(20.0)
    assert especifico["mediana"] == pytest.approx(20.0)
    assert especifico["rango"] == pytest.approx(20.0)


def test_perfil_enriquecido_categorico_v6() -> None:
    """El perfil categórico V6 debe describir categorías y dominancia."""
    datos = pd.DataFrame(
        {
            "estado": [
                "Activo",
                "Activo",
                "Pendiente",
                "Activo",
                "Cerrado",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    inferencias = {
        "estado": _crear_inferencia(
            "estado",
            SemanticType.CATEGORICAL,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    especifico = resultado["estado"]["especifico"]

    assert especifico["numero_categorias"] == 3
    assert especifico["categoria_dominante"] == "Activo"
    assert especifico["frecuencia_dominante"] == 3
    assert especifico[
        "frecuencia_dominante_porcentaje"
    ] == pytest.approx(60.0)


def test_perfil_enriquecido_temporal_v6() -> None:
    """El perfil temporal V6 debe describir conversión y rango de fechas."""
    datos = pd.DataFrame(
        {
            "fecha": [
                "01/01/2026",
                "15/01/2026",
                "fecha_invalida",
                "31/01/2026",
            ],
        },
        dtype="object",
    )

    analisis = analizar_columnas(datos)

    inferencias = {
        "fecha": _crear_inferencia(
            "fecha",
            SemanticType.DATE,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    especifico = resultado["fecha"]["especifico"]

    assert especifico["valores_convertibles"] == 3
    assert especifico["valores_no_convertibles"] == 1
    assert especifico["conversion_porcentaje"] == pytest.approx(75.0)
    assert especifico["fecha_minima"] == pd.Timestamp("2026-01-01")
    assert especifico["fecha_maxima"] == pd.Timestamp("2026-01-31")
    assert especifico["rango_temporal"] == pd.Timedelta(days=30)


def test_perfil_enriquecido_texto_libre_v6() -> None:
    """El perfil de texto libre V6 debe describir longitudes."""
    datos = pd.DataFrame(
        {
            "comentario": [
                "Hola",
                "Texto medio",
                "Comentario bastante largo",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    inferencias = {
        "comentario": _crear_inferencia(
            "comentario",
            SemanticType.FREE_TEXT,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    especifico = resultado["comentario"]["especifico"]

    longitudes = datos["comentario"].str.len()

    assert especifico["longitud_minima"] == int(
        longitudes.min()
    )
    assert especifico["longitud_maxima"] == int(
        longitudes.max()
    )
    assert especifico["longitud_media"] == pytest.approx(
        float(longitudes.mean())
    )


def test_perfil_enriquecido_identificador_v6() -> None:
    """El perfil de identificador debe centrarse en unicidad y duplicación."""
    datos = pd.DataFrame(
        {
            "cliente_id": [
                "C001",
                "C002",
                "C002",
                "C003",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    inferencias = {
        "cliente_id": _crear_inferencia(
            "cliente_id",
            SemanticType.IDENTIFIER,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    especifico = resultado["cliente_id"]["especifico"]

    assert especifico["valores_distintos"] == 3
    assert especifico["unicidad_porcentaje"] == pytest.approx(75.0)
    assert especifico["valores_duplicados"] == 1
    assert especifico["duplicados_porcentaje"] == pytest.approx(
        25.0
    )

    assert "media" not in especifico
    assert "mediana" not in especifico


def test_perfil_enriquecido_no_modifica_datos_v6() -> None:
    """El perfilado enriquecido no debe modificar el dataset original."""
    datos = pd.DataFrame(
        {
            "importe": ["10", "20", "error", "30"],
            "ciudad": [
                "Madrid",
                "Madrid",
                "Sevilla",
                "Bilbao",
            ],
        }
    )

    original = datos.copy(deep=True)
    analisis = analizar_columnas(datos)

    inferencias = {
        "importe": _crear_inferencia(
            "importe",
            SemanticType.NUMERIC,
        ),
        "ciudad": _crear_inferencia(
            "ciudad",
            SemanticType.CATEGORICAL,
        ),
    }

    perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )