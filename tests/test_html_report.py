"""Tests para la generación del informe HTML."""

import pandas as pd

from src.html_report import (
    generar_informe_html,
    generar_mapa_nulos_html,
    preparar_mapa_nulos,
)


def _crear_resultado_auditoria() -> dict:
    """Crea un resultado mínimo válido para probar el informe HTML."""
    return {
        "dataset": {
            "archivo": "prueba.csv",
            "filas": 3,
            "columnas": 2,
            "memoria_bytes": 512,
        },
        "tipos_semanticos": {
            "id": {
                "tipo": "identificador",
                "confianza": "alta",
                "fuente": "inferred",
                "evidencias": [
                    "Nombre y unicidad compatibles con identificador."
                ],
            },
            "categoria": {
                "tipo": "categorico",
                "confianza": "media",
                "fuente": "inferred",
                "evidencias": [
                    "Cardinalidad compatible con categoría."
                ],
            },
        },
        "perfil": {
            "nombres_columnas": [
                "id",
                "categoria",
            ],
            "tipos_datos": {
                "id": "int64",
                "categoria": "object",
            },
            "valores_distintos": {
                "id": 3,
                "categoria": 3,
            },
            "estadisticas_numericas": {
                "id": {
                    "minimo": 1.0,
                    "maximo": 3.0,
                    "media": 2.0,
                    "mediana": 2.0,
                    "desviacion_estandar": 1.0,
                    "q1": 1.5,
                    "q3": 2.5,
                }
            },
        },
        "calidad": {
            "nulos": {
                "total_nulos": 1,
                "columnas_con_nulos": 1,
                "por_columna": {
                    "id": {
                        "nulos": 0,
                        "porcentaje_nulos": 0.0,
                    },
                    "categoria": {
                        "nulos": 1,
                        "porcentaje_nulos": 33.333333,
                    },
                },
            },
            "nulos_textuales": {
                "categoria": {
                    "total_posibles_nulos_textuales": 1,
                    "porcentaje_posibles_nulos_textuales": 33.333333,
                    "marcadores_detectados": {
                        "espacios_en_blanco": 1,
                    },
                }
            },
            "identificadores": {
                "id": {
                    "posible_identificador": True,
                    "valores_no_nulos": 3,
                    "valores_distintos": 3,
                    "porcentaje_unicidad": 100.0,
                    "nombre_indicativo": True,
                }
            },
            "duplicados": {
                "filas_duplicadas": 0,
                "porcentaje_duplicados": 0.0,
            },
            "duplicados_clave": {
                "columnas_clave": [],
                "clave_configurada": False,
                "columnas_inexistentes": [],
                "registros_validos": 0,
                "registros_excluidos": 0,
                "registros_con_clave_duplicada": 0,
                "valores_clave_duplicados": 0,
                "porcentaje_registros_duplicados": 0.0,
            },
            "columnas_problematicas": {
                "columnas_vacias": [],
                "columnas_constantes": [],
            },
            "texto": {
                "categoria": {
                    "valores_con_espacios": 0,
                    "posibles_diferencias_mayusculas": False,
                    "baja_cardinalidad": False,
                    "grupos_inconsistentes": [],
                }
            },
            "outliers": {
                "id": {
                    "q1": 1.5,
                    "q3": 2.5,
                    "iqr": 1.0,
                    "limite_inferior": 0.0,
                    "limite_superior": 4.0,
                    "cantidad_outliers": 0,
                    "porcentaje_outliers": 0.0,
                }
            },
            "incompatibilidades_tipo": {
                "categoria": {
                    "tipo_semantico": "categorico",
                    "valores_evaluados": 2,
                    "valores_incompatibles": 1,
                    "porcentaje_incompatibles": 50.0,
                }
            },
            "reglas_negocio": {
                "id": {
                    "min": {
                        "regla": "min",
                        "valor_regla": 1,
                        "cantidad_incumplimientos": 1,
                        "porcentaje_incumplimientos": 33.333333,
                    }
                }
            },
            "fechas": {},
        },
        "incidencias": [
            {
                "tipo": "nulos_reales",
                "categoria": "completitud",
                "severidad": "media",
                "columna": "categoria",
                "cantidad": 1,
                "porcentaje": 33.333333,
                "mensaje": (
                    "La columna 'categoria' contiene "
                    "1 valor nulo."
                ),
            }
        ],
        "resumen": {
            "total_incidencias": 1,
            "por_severidad": {
                "alta": 0,
                "media": 1,
                "baja": 0,
            },
            "por_categoria": {
                "completitud": 1,
                "unicidad": 0,
                "estructura": 0,
                "consistencia": 0,
                "validez": 0,
            },
            "tipos_semanticos": {
                "numerico": 0,
                "fecha": 0,
                "fecha_hora": 0,
                "booleano_binario": 0,
                "categorico": 1,
                "identificador": 1,
                "texto_libre": 0,
            },
            "cobertura_auditoria": {
                "controles_aplicados": [
                    "completitud",
                    "unicidad_general",
                    "consistencia_texto",
                ],
                "controles_no_aplicables": [
                    "outliers",
                    "compatibilidad_semantica",
                ],
                "controles_no_configurados": [
                    "unicidad_clave",
                    "reglas_negocio",
                ],
            },
            "principales_incidencias": [
                {
                    "tipo": "nulos_reales",
                    "categoria": "completitud",
                    "severidad": "media",
                    "columna": "categoria",
                    "cantidad": 1,
                    "porcentaje": 33.333333,
                    "mensaje": (
                        "La columna 'categoria' contiene "
                        "1 valor nulo."
                    ),
                }
            ],
        },
    }


def test_generar_informe_html(tmp_path):
    """Comprueba la generación y estructura principal del HTML."""
    datos = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "categoria": [
                "A",
                None,
                "",
            ],
        }
    )

    resultado = _crear_resultado_auditoria()
    ruta_salida = tmp_path / "informe.html"

    ruta_generada = generar_informe_html(
        resultado,
        datos,
        ruta_salida,
    )

    assert ruta_generada == ruta_salida
    assert ruta_salida.exists()

    contenido = ruta_salida.read_text(
        encoding="utf-8",
    )

    secciones_esperadas = [
        "Resumen ejecutivo",
        "Mapa de valores ausentes",
        "Perfil del dataset",
        "Calidad del dataset",
        "Incidencias detectadas",
        "Estadísticas numéricas",
        "Posibles valores atípicos",
        "Generado por DataQualityPy",
    ]

    for seccion in secciones_esperadas:
        assert seccion in contenido


def test_mapa_nulos_distingue_estados():
    """Comprueba los tres estados del mapa de valores ausentes."""
    datos = pd.DataFrame(
        {
            "valor": [
                "dato",
                None,
                "",
            ]
        }
    )

    mapa = preparar_mapa_nulos(datos)["mapa"]

    assert mapa["valor"].tolist() == [
        0,
        1,
        2,
    ]

    html = generar_mapa_nulos_html(datos)

    assert "Dato válido" in html
    assert "Nulo real" in html
    assert "Posible nulo textual" in html


def test_mapa_nulos_limita_a_200_filas():
    """Comprueba el límite y el muestreo distribuido del mapa."""
    datos = pd.DataFrame(
        {
            "valor": range(500),
        }
    )

    resultado = preparar_mapa_nulos(datos)

    mapa = resultado["mapa"]

    assert resultado["filas_totales"] == 500
    assert resultado["filas_mostradas"] == 200
    assert resultado["muestra"] is True
    assert len(mapa) == 200

    assert mapa.index[0] == 0
    assert mapa.index[-1] == 499


def test_html_v3_muestra_tipos_semanticos_y_cobertura(tmp_path):
    """Comprueba la presentación del perfil semántico y la cobertura V3."""
    datos = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "categoria": ["A", None, ""],
        }
    )
    resultado = _crear_resultado_auditoria()
    ruta_salida = tmp_path / "informe_v3.html"

    generar_informe_html(
        resultado,
        datos,
        ruta_salida,
    )

    contenido = ruta_salida.read_text(encoding="utf-8")

    assert "Tipos semánticos" in contenido
    assert "Cobertura de auditoría" in contenido
    assert "Dtype físico" in contenido
    assert "Tipo semántico" in contenido
    assert "Confianza" in contenido
    assert "Origen" in contenido
    assert "Identificador" in contenido
    assert "Categórico" in contenido
    assert "Alta" in contenido
    assert "Media" in contenido
    assert "Inferido" in contenido
    assert "Controles aplicados" in contenido
    assert "Controles no aplicables" in contenido
    assert "Controles no configurados" in contenido


def test_html_v3_muestra_incompatibilidades_y_reglas_negocio(tmp_path):
    """Comprueba las nuevas subsecciones de validez de V3."""
    datos = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "categoria": ["A", None, ""],
        }
    )
    resultado = _crear_resultado_auditoria()
    ruta_salida = tmp_path / "informe_validez_v3.html"

    generar_informe_html(
        resultado,
        datos,
        ruta_salida,
    )

    contenido = ruta_salida.read_text(encoding="utf-8")

    assert "Incompatibilidades de tipo semántico" in contenido
    assert "Reglas de negocio" in contenido
    assert "Valores incompatibles" in contenido
    assert "Incumplimientos" in contenido
    assert "min" in contenido


def test_html_v3_sin_incidencias_mantiene_resumen_semantico_y_cobertura(
    tmp_path,
):
    """Comprueba que un dataset limpio conserva el resumen V3 completo."""
    datos = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "categoria": ["A", "B", "C"],
        }
    )
    resultado = _crear_resultado_auditoria()
    resultado["incidencias"] = []
    resultado["resumen"]["total_incidencias"] = 0
    resultado["resumen"]["por_severidad"] = {
        "alta": 0,
        "media": 0,
        "baja": 0,
    }
    resultado["resumen"]["principales_incidencias"] = []

    ruta_salida = tmp_path / "informe_limpio_v3.html"

    generar_informe_html(
        resultado,
        datos,
        ruta_salida,
    )

    contenido = ruta_salida.read_text(encoding="utf-8")

    assert "No se han detectado incidencias de calidad." in contenido
    assert "Tipos semánticos" in contenido
    assert "Cobertura de auditoría" in contenido
    assert "Identificador" in contenido
    assert "Categórico" in contenido

