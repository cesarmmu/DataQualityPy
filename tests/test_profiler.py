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
    assert especifico["rango_temporal"] == pd.Timedelta(30, unit="D")


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

# ---------------------------------------------------------------------------
# V7-C1 — Integración de patrones estructurales en el perfilado
# ---------------------------------------------------------------------------


def test_perfil_incluye_patrones_estructurales_v7() -> None:
    """El perfil común debe exponer la evidencia estructural calculada por C1."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "ABC-1234",
                "XYZ-5678",
                "DEF-9012",
                "AB-3456",
            ],
        },
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "codigo": _crear_inferencia(
            "codigo",
            SemanticType.IDENTIFIER,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    patrones = resultado["codigo"]["comun"]["patrones_estructurales"]

    assert patrones["valores_analizados"] == 4
    assert patrones["patron_dominante"] == "AAA-NNNN"
    assert patrones["frecuencia_dominante"] == 3
    assert patrones["frecuencia_dominante_porcentaje"] == pytest.approx(75.0)
    assert patrones["numero_patrones"] == 2
    assert patrones["frecuencias"] == [
        {"patron": "AAA-NNNN", "frecuencia": 3},
        {"patron": "AA-NNNN", "frecuencia": 1},
    ]


def test_perfil_no_incluye_patrones_si_c1_no_aplica_v7() -> None:
    """El perfil común no debe inventar patrones cuando C1 no es aplicable."""
    datos = pd.DataFrame({"importe": [10, 20, 30, 40]})

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

    comun = resultado["importe"]["comun"]

    assert "patrones_estructurales" not in comun


def test_perfil_patron_cinco_digitos_no_infiere_significado_v7() -> None:
    """El perfil debe conservar NNNNN como evidencia puramente estructural."""
    datos = pd.DataFrame(
        {"valor": ["28053", "28041", "28012"]},
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "valor": _crear_inferencia(
            "valor",
            SemanticType.IDENTIFIER,
        )
    }

    resultado = perfilar_columnas_semanticas(
        analisis,
        inferencias,
    )

    patrones = resultado["valor"]["comun"]["patrones_estructurales"]

    assert patrones["patron_dominante"] == "NNNNN"
    assert patrones["frecuencia_dominante_porcentaje"] == pytest.approx(100.0)
    assert patrones["numero_patrones"] == 1
    assert "codigo_postal" not in patrones
    assert "tipo_semantico" not in patrones


# ---------------------------------------------------------------------------
# V7-C2 — Integración de compatibilidad semántica en el perfilado
# ---------------------------------------------------------------------------


def test_perfil_incluye_compatibilidad_semantica_v7() -> None:
    """El perfil común debe exponer las siete compatibilidades de C2."""
    datos = pd.DataFrame(
        {
            "contacto": [
                "ana@example.com",
                "usuario@dominio.es",
                "texto_invalido",
                "otro@dominio.org",
            ],
        },
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "contacto": _crear_inferencia(
            "contacto",
            SemanticType.IDENTIFIER,
        )
    }

    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    compatibilidad = resultado["contacto"]["comun"][
        "compatibilidad_semantica"
    ]

    assert compatibilidad["valores_analizados"] == 4
    assert set(compatibilidad["compatibilidades"]) == {
        "numeric",
        "date",
        "boolean",
        "email",
        "url",
        "ipv4",
        "uuid",
    }

    email = compatibilidad["compatibilidades"]["email"]
    assert email["valores_compatibles"] == 3
    assert email["porcentaje_compatible"] == pytest.approx(75.0)


def test_perfil_compatibilidad_semantica_excluye_nulos_v7() -> None:
    """C2 debe reflejar solo los valores analizables en el perfil común."""
    datos = pd.DataFrame(
        {"valor": ["10", "NA", None, "20", "", "30"]},
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "valor": _crear_inferencia("valor", SemanticType.IDENTIFIER)
    }

    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    compatibilidad = resultado["valor"]["comun"][
        "compatibilidad_semantica"
    ]
    numeric = compatibilidad["compatibilidades"]["numeric"]

    assert compatibilidad["valores_analizados"] == 3
    assert numeric["valores_compatibles"] == 3
    assert numeric["porcentaje_compatible"] == pytest.approx(100.0)


def test_perfil_no_incluye_compatibilidad_si_no_hay_analizables_v7() -> None:
    """El perfil no debe fabricar compatibilidades para una columna vacía."""
    datos = pd.DataFrame(
        {"vacia": [None, "NA", "", "null"]},
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "vacia": _crear_inferencia("vacia", SemanticType.CATEGORICAL)
    }

    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    comun = resultado["vacia"]["comun"]

    assert "compatibilidad_semantica" not in comun


def test_perfil_c2_cinco_digitos_no_infiere_significado_v7() -> None:
    """C2 puede observar compatibilidad numérica sin atribuir significado."""
    datos = pd.DataFrame(
        {"valor": ["28053", "28041", "28012"]},
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "valor": _crear_inferencia("valor", SemanticType.IDENTIFIER)
    }

    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    compatibilidad = resultado["valor"]["comun"][
        "compatibilidad_semantica"
    ]
    numeric = compatibilidad["compatibilidades"]["numeric"]

    assert numeric["valores_compatibles"] == 3
    assert numeric["porcentaje_compatible"] == pytest.approx(100.0)
    assert "codigo_postal" not in compatibilidad
    assert "tipo_semantico" not in compatibilidad


def test_perfil_c2_conserva_compatibilidades_solapadas_v7() -> None:
    """El perfil debe conservar compatibilidades simultáneas sin priorizarlas."""
    datos = pd.DataFrame(
        {"indicador": ["0", "1", "0", "1"]},
        dtype="object",
    )

    analisis = analizar_columnas(datos)
    inferencias = {
        "indicador": _crear_inferencia("indicador", SemanticType.BOOLEAN)
    }

    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    compatibilidades = resultado["indicador"]["comun"][
        "compatibilidad_semantica"
    ]["compatibilidades"]

    assert compatibilidades["numeric"][
        "porcentaje_compatible"
    ] == pytest.approx(100.0)
    assert compatibilidades["boolean"][
        "porcentaje_compatible"
    ] == pytest.approx(100.0)

# ---------------------------------------------------------------------------
# V7-C3 — Integración de coherencia entre tipo físico y contenido observado
# ---------------------------------------------------------------------------


def test_perfil_c3_object_numerico_expone_discrepancia_potencial_v7() -> None:
    """C3 debe exponer una discrepancia potencial con evidencia completa."""
    datos = pd.DataFrame({"importe": ["10", "20", "30", "40"]}, dtype="object")
    analisis = analizar_columnas(datos)
    inferencias = {"importe": _crear_inferencia("importe", SemanticType.NUMERIC)}
    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    coherencia = resultado["importe"]["comun"]["coherencia_tipo"]
    assert coherencia["tipo_fisico"] == "object"
    assert coherencia["tipo_observado"] == "numeric"
    assert coherencia["estado"] == "potential_mismatch"
    assert coherencia["porcentaje_evidencia"] == pytest.approx(100.0)
    assert coherencia["evidencias"]


def test_perfil_c3_numerico_fisico_expone_coherencia_v7() -> None:
    """C3 debe reconocer la coherencia entre dtype y contenido numérico."""
    datos = pd.DataFrame({"importe": [10, 20, 30, 40]}, dtype="int64")
    analisis = analizar_columnas(datos)
    inferencias = {"importe": _crear_inferencia("importe", SemanticType.NUMERIC)}
    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    coherencia = resultado["importe"]["comun"]["coherencia_tipo"]
    assert coherencia["tipo_fisico"] == "int64"
    assert coherencia["tipo_observado"] == "numeric"
    assert coherencia["estado"] == "coherent"
    assert coherencia["porcentaje_evidencia"] == pytest.approx(100.0)
    assert coherencia["evidencias"]


def test_perfil_c3_compatibilidad_parcial_es_evidencia_insuficiente_v7() -> None:
    """C3 no debe elevar una compatibilidad parcial a discrepancia."""
    datos = pd.DataFrame({"importe": ["10", "20", "error", "30"]}, dtype="object")
    analisis = analizar_columnas(datos)
    inferencias = {"importe": _crear_inferencia("importe", SemanticType.NUMERIC)}
    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    coherencia = resultado["importe"]["comun"]["coherencia_tipo"]
    assert coherencia["tipo_fisico"] == "object"
    assert coherencia["tipo_observado"] == "numeric"
    assert coherencia["estado"] == "insufficient_evidence"
    assert coherencia["porcentaje_evidencia"] == pytest.approx(75.0)
    assert coherencia["evidencias"]


def test_perfil_c3_identificador_numerico_textual_queda_protegido_v7() -> None:
    """Un identificador textual no debe convertirse en discrepancia numérica."""
    datos = pd.DataFrame({"cliente_id": ["1001", "1002", "1003", "1004"]}, dtype="object")
    analisis = analizar_columnas(datos)
    inferencias = {"cliente_id": _crear_inferencia("cliente_id", SemanticType.IDENTIFIER)}
    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    coherencia = resultado["cliente_id"]["comun"]["coherencia_tipo"]
    assert coherencia["tipo_fisico"] == "object"
    assert coherencia["tipo_observado"] is None
    assert coherencia["estado"] == "insufficient_evidence"
    assert coherencia["porcentaje_evidencia"] is None
    assert coherencia["evidencias"]


def test_perfil_c3_expone_estructura_completa_v7() -> None:
    """La integración debe conservar el contrato estructurado aprobado."""
    datos = pd.DataFrame({"activo": ["true", "false", "yes", "no"]}, dtype="object")
    analisis = analizar_columnas(datos)
    inferencias = {"activo": _crear_inferencia("activo", SemanticType.BOOLEAN)}
    resultado = perfilar_columnas_semanticas(analisis, inferencias)
    coherencia = resultado["activo"]["comun"]["coherencia_tipo"]
    assert set(coherencia) == {"tipo_fisico", "tipo_observado", "estado", "porcentaje_evidencia", "evidencias"}
    assert coherencia["tipo_observado"] == "boolean"
    assert coherencia["estado"] == "potential_mismatch"
    assert coherencia["porcentaje_evidencia"] == pytest.approx(100.0)
    assert isinstance(coherencia["evidencias"], list)
    assert coherencia["evidencias"]

