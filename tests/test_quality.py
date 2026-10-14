"""Tests para las funciones de calidad de DataQualityPy."""

import pandas as pd
import pytest

from src.column_analysis import analizar_columnas
from src.semantic_quality import (
    analizar_incompatibilidades_semanticas,
    analizar_outliers_semanticos,
)
from src.inference import SemanticInference, inferir_tipo_semantico
from src.quality import (
    analizar_columnas_problematicas,
    analizar_duplicados,
    analizar_duplicados_clave,
    analizar_fechas,
    analizar_identificadores,
    analizar_nulos,
    analizar_nulos_textuales,
    analizar_outliers,
    analizar_texto,
)


def _generar_contexto_semantico(datos: pd.DataFrame) -> dict:
    """Genera análisis e inferencias para los tests semánticos."""
    analisis_columnas = analizar_columnas(datos)
    inferencias: dict[object, SemanticInference] = {}

    for columna, analisis in analisis_columnas.items():
        inferencias[columna] = inferir_tipo_semantico(
            analisis,
            analisis.analyzable_series,
        )

    return {
        "analisis": analisis_columnas,
        "inferencias": inferencias,
    }


def test_analizar_duplicados_detecta_una_fila_duplicada() -> None:
    """Comprueba que se detecte correctamente una fila duplicada."""
    datos = pd.DataFrame(
        {
            "producto": ["Portatil", "Raton", "Raton"],
            "precio": [900, 25, 25],
        }
    )

    resultado = analizar_duplicados(datos)

    assert resultado["filas_duplicadas"] == 1
    assert resultado["porcentaje_duplicados"] == pytest.approx(
        33.33333333333333
    )


def test_analizar_duplicados_sin_filas_duplicadas() -> None:
    """Comprueba el resultado cuando no existen filas duplicadas."""
    datos = pd.DataFrame(
        {
            "producto": ["Portatil", "Raton", "Teclado"],
            "precio": [900, 25, 50],
        }
    )

    resultado = analizar_duplicados(datos)

    assert resultado["filas_duplicadas"] == 0
    assert resultado["porcentaje_duplicados"] == pytest.approx(0.0)


def test_analizar_duplicados_clave_compuesta() -> None:
    """Comprueba duplicados y exclusiones en una clave compuesta."""
    datos = pd.DataFrame(
        {
            "id_cliente": [
                "C001",
                "C001",
                "C002",
                "C002",
                "C003",
                "C004",
            ],
            "fecha_pedido": [
                "01/09/2026",
                "01/09/2026",
                "02/09/2026",
                "03/09/2026",
                "N/A",
                "04/09/2026",
            ],
            "producto": [
                "Portatil",
                "Raton",
                "Teclado",
                "Monitor",
                "Silla",
                "Webcam",
            ],
        }
    )

    resultado = analizar_duplicados_clave(
        datos,
        columnas_clave=[
            "id_cliente",
            "fecha_pedido",
        ],
    )

    assert resultado["clave_configurada"] is True
    assert resultado["columnas_inexistentes"] == []
    assert resultado["registros_validos"] == 5
    assert resultado["registros_excluidos"] == 1
    assert resultado["registros_con_clave_duplicada"] == 2
    assert resultado["valores_clave_duplicados"] == 1
    assert resultado[
        "porcentaje_registros_duplicados"
    ] == pytest.approx(40.0)


def test_analizar_nulos_detecta_valores_nulos() -> None:
    """Comprueba el recuento y porcentaje de valores nulos."""
    datos = pd.DataFrame(
        {
            "producto": ["Portatil", "Raton", "Teclado", "Monitor"],
            "precio": [900, None, 50, None],
        }
    )

    resultado = analizar_nulos(datos)

    assert resultado["total_nulos"] == 2
    assert resultado["columnas_con_nulos"] == 1
    assert resultado["por_columna"]["producto"]["nulos"] == 0
    assert resultado["por_columna"]["precio"]["nulos"] == 2
    assert resultado["por_columna"]["precio"][
        "porcentaje_nulos"
    ] == pytest.approx(50.0)


def test_analizar_nulos_con_dataset_vacio() -> None:
    """Comprueba el análisis de nulos cuando no existen filas."""
    datos = pd.DataFrame(
        {
            "producto": pd.Series(dtype="object"),
            "precio": pd.Series(dtype="float64"),
        }
    )

    resultado = analizar_nulos(datos)

    assert resultado["total_nulos"] == 0
    assert resultado["columnas_con_nulos"] == 0
    assert resultado["por_columna"]["producto"]["nulos"] == 0
    assert resultado["por_columna"]["producto"][
        "porcentaje_nulos"
    ] == pytest.approx(0.0)
    assert resultado["por_columna"]["precio"]["nulos"] == 0
    assert resultado["por_columna"]["precio"][
        "porcentaje_nulos"
    ] == pytest.approx(0.0)


def test_analizar_nulos_textuales_detecta_marcadores() -> None:
    """Comprueba la detección de posibles nulos representados como texto."""
    datos = pd.DataFrame(
        {
            "estado": [
                "",
                "   ",
                "N/A",
                "NA",
                "null",
                "None",
                "-",
                "Correcto",
            ]
        }
    )

    resultado = analizar_nulos_textuales(datos)

    assert resultado["estado"][
        "total_posibles_nulos_textuales"
    ] == 7
    assert resultado["estado"][
        "porcentaje_posibles_nulos_textuales"
    ] == pytest.approx(87.5)
    assert resultado["estado"]["marcadores_detectados"] == {
        "espacios_en_blanco": 2,
        "n/a": 1,
        "na": 1,
        "null": 1,
        "none": 1,
        "-": 1,
    }


def test_analizar_identificadores_detecta_candidato() -> None:
    """Comprueba nombre, unicidad y exclusión de nulos textuales."""
    datos = pd.DataFrame(
        {
            "id_cliente": [
                "CLI001",
                "CLI002",
                "CLI003",
                "N/A",
                "CLI004",
            ],
            "producto": [
                "Portatil",
                "Raton",
                "Teclado",
                "Monitor",
                "Silla",
            ],
        }
    )

    resultado = analizar_identificadores(datos)

    assert "id_cliente" in resultado
    assert "producto" not in resultado

    identificador = resultado["id_cliente"]

    assert identificador["nombre_indicativo"] is True
    assert identificador["posible_identificador"] is True
    assert identificador["valores_no_nulos"] == 4
    assert identificador["valores_distintos"] == 4
    assert identificador["porcentaje_unicidad"] == pytest.approx(100.0)


def test_analizar_identificadores_reconoce_camelcase() -> None:
    """Comprueba nombres de identificador escritos en CamelCase."""
    datos = pd.DataFrame(
        {
            "PassengerId": [1, 2, 3, 4, 5],
            "Name": [
                "Ana",
                "Luis",
                "Marta",
                "Pedro",
                "Lucía",
            ],
        }
    )

    resultado = analizar_identificadores(datos)

    assert "PassengerId" in resultado

    identificador = resultado["PassengerId"]

    assert identificador["nombre_indicativo"] is True
    assert identificador["posible_identificador"] is True
    assert identificador["valores_no_nulos"] == 5
    assert identificador["valores_distintos"] == 5
    assert identificador["porcentaje_unicidad"] == pytest.approx(100.0)

    assert "Name" not in resultado


def test_analizar_columnas_problematicas() -> None:
    """Comprueba la detección de columnas vacías y constantes."""
    datos = pd.DataFrame(
        {
            "vacia": [None, None, None],
            "constante": ["España", "España", "España"],
            "normal": ["España", "Francia", "Italia"],
        }
    )

    resultado = analizar_columnas_problematicas(datos)

    assert resultado["columnas_vacias"] == ["vacia"]
    assert resultado["columnas_constantes"] == ["constante"]


def test_analizar_texto_detecta_posibles_problemas() -> None:
    """Comprueba espacios, categorías inconsistentes y cardinalidad."""
    datos = pd.DataFrame(
        {
            "categoria": [
                "Informatica",
                "informática",
                "INFORMATICA",
                " Informatica ",
                "Oficina",
                "N/A",
            ],
            "pais": [
                "España",
                "España",
                "España",
                "España",
                "España",
                "España",
            ],
        }
    )

    resultado = analizar_texto(datos)

    categoria = resultado["categoria"]

    assert categoria["valores_con_espacios"] == 1
    assert categoria["posibles_diferencias_mayusculas"] is True
    assert len(categoria["grupos_inconsistentes"]) == 1

    grupo = categoria["grupos_inconsistentes"][0]

    assert grupo["valor_normalizado"] == "informatica"
    assert grupo["cantidad_variantes"] == 4
    assert grupo["variantes"] == {
        "Informatica": 1,
        "informática": 1,
        "INFORMATICA": 1,
        " Informatica ": 1,
    }

    assert "N/A" not in grupo["variantes"]
    assert resultado["pais"]["baja_cardinalidad"] is True


def test_analizar_texto_con_cardinalidad_personalizada() -> None:
    """Comprueba los límites configurables de baja cardinalidad."""
    datos = pd.DataFrame(
        {
            "categoria": [
                "A",
                "A",
                "A",
                "A",
                "A",
                "A",
                "A",
                "A",
                "B",
                "B",
            ]
        }
    )

    resultado_predeterminado = analizar_texto(datos)
    resultado_max_categorias = analizar_texto(
        datos,
        max_categorias=1,
        max_porcentaje_categorias=20,
    )
    resultado_max_porcentaje = analizar_texto(
        datos,
        max_categorias=20,
        max_porcentaje_categorias=10,
    )

    assert (
        resultado_predeterminado["categoria"]["baja_cardinalidad"]
        is True
    )
    assert (
        resultado_max_categorias["categoria"]["baja_cardinalidad"]
        is False
    )
    assert (
        resultado_max_porcentaje["categoria"]["baja_cardinalidad"]
        is False
    )


def test_analizar_outliers_detecta_valor_atipico() -> None:
    """Comprueba la detección de un posible outlier mediante IQR."""
    datos = pd.DataFrame(
        {
            "valor": [2, 3, 3, 4, 4, 5, 50],
        }
    )

    resultado = analizar_outliers(datos)["valor"]

    assert resultado["q1"] == pytest.approx(3.0)
    assert resultado["q3"] == pytest.approx(4.5)
    assert resultado["iqr"] == pytest.approx(1.5)
    assert resultado["limite_inferior"] == pytest.approx(0.75)
    assert resultado["limite_superior"] == pytest.approx(6.75)
    assert resultado["cantidad_outliers"] == 1
    assert resultado["porcentaje_outliers"] == pytest.approx(
        14.285714285714285
    )


def test_analizar_outliers_con_factor_iqr_personalizado() -> None:
    """Comprueba que un factor IQR personalizado cambie los límites."""
    datos = pd.DataFrame(
        {
            "valor": [2, 3, 3, 4, 4, 5, 50],
        }
    )

    resultado = analizar_outliers(
        datos,
        factor_iqr=2.0,
    )["valor"]

    assert resultado["limite_inferior"] == pytest.approx(0.0)
    assert resultado["limite_superior"] == pytest.approx(7.5)
    assert resultado["cantidad_outliers"] == 1


def test_analizar_outliers_con_iqr_cero() -> None:
    """Comprueba el comportamiento cuando todos los valores son iguales."""
    datos = pd.DataFrame(
        {
            "valor": [5, 5, 5, 5],
        }
    )

    resultado = analizar_outliers(datos)["valor"]

    assert resultado["iqr"] == pytest.approx(0.0)
    assert resultado["cantidad_outliers"] == 0
    assert resultado["porcentaje_outliers"] == pytest.approx(0.0)


def test_analizar_outliers_semanticos_incluye_object_numerico() -> None:
    """Comprueba outliers en una columna object semánticamente numérica."""
    datos = pd.DataFrame(
        {
            "Age": [
                "20",
                "21",
                "22",
                "23",
                "24",
                "25",
                "100",
            ],
        },
        dtype="object",
    )

    contexto = _generar_contexto_semantico(datos)

    resultado = analizar_outliers_semanticos(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert "Age" in resultado
    assert resultado["Age"]["cantidad_outliers"] == 1
    assert resultado["Age"]["porcentaje_outliers"] == pytest.approx(
        14.285714285714285
    )


def test_analizar_outliers_semanticos_excluye_identificador() -> None:
    """Comprueba que un identificador numérico no se analice como magnitud."""
    datos = pd.DataFrame(
        {
            "cliente_id": [
                1001,
                1002,
                1003,
                1004,
                999999,
            ],
            "importe": [
                10,
                11,
                12,
                13,
                100,
            ],
        }
    )

    contexto = _generar_contexto_semantico(datos)

    resultado = analizar_outliers_semanticos(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert "cliente_id" not in resultado
    assert "importe" in resultado


def test_analizar_outliers_semanticos_respeta_factor_iqr() -> None:
    """Comprueba que la versión semántica respete el factor IQR."""
    datos = pd.DataFrame(
        {
            "valor": [2, 3, 3, 4, 4, 5, 50],
        }
    )

    contexto = _generar_contexto_semantico(datos)

    resultado = analizar_outliers_semanticos(
        contexto["analisis"],
        contexto["inferencias"],
        factor_iqr=2.0,
    )["valor"]

    assert resultado["limite_inferior"] == pytest.approx(0.0)
    assert resultado["limite_superior"] == pytest.approx(7.5)
    assert resultado["cantidad_outliers"] == 1


def test_analizar_outliers_semanticos_no_modifica_datos() -> None:
    """Comprueba que el análisis semántico no modifique el DataFrame."""
    datos = pd.DataFrame(
        {
            "Age": [
                "20",
                "21",
                "22",
                "23",
                "24",
                "25",
                "100",
            ],
        },
        dtype="object",
    )

    original = datos.copy(deep=True)
    contexto = _generar_contexto_semantico(datos)

    analizar_outliers_semanticos(
        contexto["analisis"],
        contexto["inferencias"],
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )


def test_analizar_fechas_detecta_columna_fecha() -> None:
    """Comprueba fechas válidas y una conversión fallida."""
    datos = pd.DataFrame(
        {
            "fecha_pedido": [
                "01/09/2026",
                "05/09/2026",
                "12/09/2026",
                "18/09/2026",
                "fecha incorrecta",
            ]
        }
    )

    resultado = analizar_fechas(datos)

    assert "fecha_pedido" in resultado

    fecha = resultado["fecha_pedido"]

    assert fecha["tipo_temporal"] == "fecha"
    assert fecha["valores_validos"] == 4
    assert fecha["valores_nulos"] == 0
    assert fecha["nulos_textuales"] == 0
    assert fecha["conversiones_fallidas"] == 1
    assert fecha["porcentaje_conversion"] == pytest.approx(80.0)
    assert fecha["fecha_minima"] == "2026-09-01"
    assert fecha["fecha_maxima"] == "2026-09-18"


def test_analizar_fechas_detecta_fecha_hora() -> None:
    """Comprueba fecha y hora, nulos textuales y errores de conversión."""
    datos = pd.DataFrame(
        {
            "fecha_operacion": [
                "01/09/2026 08:30:15",
                "02/09/2026 14:25:03",
                "N/A",
                "fecha incorrecta",
                "03/09/2026 00:00:00",
            ]
        }
    )

    resultado = analizar_fechas(
        datos,
        umbral_fecha=75,
    )

    assert "fecha_operacion" in resultado

    fecha = resultado["fecha_operacion"]

    assert fecha["tipo_temporal"] == "fecha_hora"
    assert fecha["valores_validos"] == 3
    assert fecha["valores_nulos"] == 0
    assert fecha["nulos_textuales"] == 1
    assert fecha["conversiones_fallidas"] == 1
    assert fecha["porcentaje_conversion"] == pytest.approx(75.0)
    assert fecha["fecha_minima"] == "2026-09-01 08:30:15"
    assert fecha["fecha_maxima"] == "2026-09-03 00:00:00"


def test_analizar_fechas_con_umbral_personalizado() -> None:
    """Comprueba que el umbral configurable afecte a la detección."""
    datos = pd.DataFrame(
        {
            "fecha_pedido": [
                "01/09/2026",
                "05/09/2026",
                "12/09/2026",
                "18/09/2026",
                "fecha incorrecta",
            ]
        }
    )

    resultado = analizar_fechas(
        datos,
        umbral_fecha=90,
    )

    assert resultado == {}


def test_analizar_fechas_descarta_texto_no_convertible() -> None:
    """Comprueba que una columna de texto normal no se trate como fecha."""
    datos = pd.DataFrame(
        {
            "producto": [
                "Portatil",
                "Raton",
                "Teclado",
                "Monitor",
                "Silla",
            ]
        }
    )

    resultado = analizar_fechas(datos)

    assert resultado == {}


def test_incompatibilidades_semanticas_detecta_numerico_incompatible() -> None:
    """Detecta un valor no convertible en una columna semánticamente numérica."""
    datos = pd.DataFrame(
        {
            "cantidad": ["10", "20", "30", "40", "error"],
        },
        dtype="object",
    )

    contexto = _generar_contexto_semantico(datos)

    resultado = analizar_incompatibilidades_semanticas(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert resultado["cantidad"]["tipo_semantico"] == "numerico"
    assert resultado["cantidad"]["cantidad_incompatibles"] == 1
    assert resultado["cantidad"]["porcentaje_incompatibles"] == pytest.approx(
        20.0
    )


def test_incompatibilidades_semanticas_detecta_fecha_incompatible() -> None:
    """Detecta un valor no convertible en una columna semánticamente temporal."""
    datos = pd.DataFrame(
        {
            "fecha_alta": [
                "01/01/2026",
                "15/02/2026",
                "31/03/2026",
                "20/04/2026",
                "fecha_invalida",
            ],
        },
        dtype="object",
    )

    contexto = _generar_contexto_semantico(datos)

    resultado = analizar_incompatibilidades_semanticas(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert resultado["fecha_alta"]["tipo_semantico"] == "fecha"
    assert resultado["fecha_alta"]["cantidad_incompatibles"] == 1
    assert resultado["fecha_alta"]["porcentaje_incompatibles"] == pytest.approx(
        20.0
    )


def test_incompatibilidades_semanticas_detecta_booleano_declarado() -> None:
    """Detecta valores incompatibles cuando el tipo booleano es declarado."""
    datos = pd.DataFrame(
        {
            "activo": ["Sí", "No", "Sí", "quizá"],
        },
        dtype="object",
    )
    analisis = analizar_columnas(datos)
    inferencias: dict[object, SemanticInference] = {
        "activo": inferir_tipo_semantico(
            analisis["activo"],
            analisis["activo"].analyzable_series,
            tipo_declarado="booleano_binario",
        )
    }

    resultado = analizar_incompatibilidades_semanticas(
        analisis,
        inferencias,
    )

    assert resultado["activo"]["tipo_semantico"] == "booleano_binario"
    assert resultado["activo"]["cantidad_incompatibles"] == 1
    assert resultado["activo"]["porcentaje_incompatibles"] == pytest.approx(
        25.0
    )


def test_incompatibilidades_semanticas_excluye_nulos_del_denominador() -> None:
    """Los nulos reales y textuales no deben contar como incompatibilidades."""
    datos = pd.DataFrame(
        {
            "cantidad": ["10", "20", "error", "NA", None],
        },
        dtype="object",
    )
    analisis = analizar_columnas(datos)
    inferencias: dict[object, SemanticInference] = {
        "cantidad": inferir_tipo_semantico(
            analisis["cantidad"],
            analisis["cantidad"].analyzable_series,
            tipo_declarado="numerico",
        )
    }

    resultado = analizar_incompatibilidades_semanticas(
        analisis,
        inferencias,
    )

    assert analisis["cantidad"].analyzable_count == 3
    assert resultado["cantidad"]["cantidad_incompatibles"] == 1
    assert resultado["cantidad"]["porcentaje_incompatibles"] == pytest.approx(
        100 / 3
    )


def test_incompatibilidades_semanticas_respeta_tipo_declarado() -> None:
    """Un tipo declarado debe permitir auditar datos físicamente incompatibles."""
    datos = pd.DataFrame(
        {
            "fecha_declarada": [10, 20, 30],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias: dict[object, SemanticInference] = {
        "fecha_declarada": inferir_tipo_semantico(
            analisis["fecha_declarada"],
            analisis["fecha_declarada"].analyzable_series,
            tipo_declarado="fecha",
        )
    }

    resultado = analizar_incompatibilidades_semanticas(
        analisis,
        inferencias,
    )

    assert resultado["fecha_declarada"]["tipo_semantico"] == "fecha"
    assert resultado["fecha_declarada"]["cantidad_incompatibles"] == 3
    assert resultado["fecha_declarada"]["porcentaje_incompatibles"] == pytest.approx(
        100.0
    )


def test_incompatibilidades_semanticas_omite_columnas_sin_problemas() -> None:
    """Una columna totalmente compatible no debe aparecer como incidencia."""
    datos = pd.DataFrame(
        {
            "cantidad": ["10", "20", "30", "40"],
        },
        dtype="object",
    )

    contexto = _generar_contexto_semantico(datos)

    resultado = analizar_incompatibilidades_semanticas(
        contexto["analisis"],
        contexto["inferencias"],
    )

    assert "cantidad" not in resultado


def test_incompatibilidades_semanticas_no_aplica_a_tipos_genericos() -> None:
    """Categorías, identificadores y texto libre no tienen incompatibilidad genérica."""
    datos = pd.DataFrame(
        {
            "cliente_id": ["C001", "C002", "C003", "C004"],
            "categoria": ["A", "A", "B", "B"],
            "comentario": [
                "Comentario completamente diferente número uno",
                "Segundo comentario con contenido independiente",
                "Una tercera observación distinta de las anteriores",
                "Texto libre correspondiente al cuarto registro",
            ],
        },
        dtype="object",
    )
    analisis = analizar_columnas(datos)
    inferencias: dict[object, SemanticInference] = {
        "cliente_id": inferir_tipo_semantico(
            analisis["cliente_id"],
            analisis["cliente_id"].analyzable_series,
            tipo_declarado="identificador",
        ),
        "categoria": inferir_tipo_semantico(
            analisis["categoria"],
            analisis["categoria"].analyzable_series,
            tipo_declarado="categorico",
        ),
        "comentario": inferir_tipo_semantico(
            analisis["comentario"],
            analisis["comentario"].analyzable_series,
            tipo_declarado="texto_libre",
        ),
    }

    resultado = analizar_incompatibilidades_semanticas(
        analisis,
        inferencias,
    )

    assert resultado == {}

