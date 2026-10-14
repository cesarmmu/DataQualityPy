"""Tests para la generación del informe JSON V3."""

import json

from src.json_report import generar_informe_json


def test_generar_informe_json_v3(tmp_path):
    """Comprueba que el informe JSON conserva el contrato completo de V3."""
    resultado_auditoria = {
        "dataset": {
            "archivo": "prueba.csv",
            "filas": 10,
            "columnas": 3,
            "memoria_bytes": 1024,
        },
        "resumen": {
            "total_incidencias": 2,
            "por_severidad": {
                "alta": 0,
                "media": 2,
                "baja": 0,
            },
            "por_categoria": {
                "completitud": 0,
                "unicidad": 0,
                "estructura": 0,
                "consistencia": 0,
                "validez": 2,
            },
            "principales_incidencias": [],
            "tipos_semanticos": {
                "numerico": 1,
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
                    "outliers",
                    "compatibilidad_semantica",
                    "reglas_negocio",
                ],
                "controles_no_aplicables": [],
                "controles_no_configurados": [
                    "unicidad_clave",
                ],
            },
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
            "producto": {
                "tipo": "categorico",
                "confianza": "media",
                "fuente": "inferred",
                "evidencias": [
                    "Cardinalidad compatible con categoría."
                ],
            },
            "precio": {
                "tipo": "numerico",
                "confianza": "alta",
                "fuente": "declared",
                "evidencias": [
                    "El tipo semántico fue declarado explícitamente "
                    "en la configuración."
                ],
            },
        },
        "incidencias": [
            {
                "tipo": "incompatibilidad_tipo",
                "categoria": "validez",
                "severidad": "media",
                "columna": "precio",
                "cantidad": 1,
                "porcentaje": 10.0,
                "mensaje": (
                    "La columna precio contiene valores incompatibles."
                ),
            },
            {
                "tipo": "incumplimiento_regla",
                "categoria": "validez",
                "severidad": "media",
                "columna": "precio",
                "cantidad": 1,
                "porcentaje": 11.11,
                "mensaje": "La columna precio incumple la regla min=0.",
            },
        ],
        "perfil": {
            "nombres_columnas": [
                "id",
                "producto",
                "precio",
            ],
            "tipos_datos": {
                "id": "int64",
                "producto": "object",
                "precio": "object",
            },
            "valores_distintos": {
                "id": 10,
                "producto": 8,
                "precio": 10,
            },
            "estadisticas_numericas": {
                "precio": {
                    "min": -5.0,
                    "max": 100.0,
                    "media": 45.0,
                    "mediana": 42.0,
                    "desviacion_estandar": 20.0,
                }
            },
        },
        "calidad": {
            "nulos": {},
            "nulos_textuales": {},
            "identificadores": {},
            "duplicados": {},
            "duplicados_clave": {},
            "columnas_problematicas": {},
            "texto": {},
            "outliers": {},
            "incompatibilidades_tipo": {
                "precio": {
                    "tipo_semantico": "numerico",
                    "valores_evaluados": 10,
                    "valores_incompatibles": 1,
                    "porcentaje_incompatibles": 10.0,
                }
            },
            "reglas_negocio": {
                "precio": {
                    "min": {
                        "regla": "min",
                        "valor_configurado": 0,
                        "valores_evaluados": 9,
                        "valores_incumplidos": 1,
                        "porcentaje_incumplimiento": 11.11,
                    }
                }
            },
            "fechas": {},
        },
    }

    ruta_salida = tmp_path / "informe.json"

    ruta_generada = generar_informe_json(
        resultado_auditoria,
        ruta_salida,
    )

    assert ruta_generada == ruta_salida
    assert ruta_salida.exists()

    with ruta_salida.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        contenido = json.load(archivo)

    assert list(contenido) == [
        "dataqualitypy",
        "dataset",
        "resumen",
        "tipos_semanticos",
        "incidencias",
        "perfil",
        "calidad",
    ]

    assert contenido["dataqualitypy"]["version_informe"] == "3.0"
    assert contenido["dataset"] == resultado_auditoria["dataset"]
    assert contenido["resumen"] == resultado_auditoria["resumen"]
    assert (
        contenido["tipos_semanticos"]
        == resultado_auditoria["tipos_semanticos"]
    )
    assert contenido["incidencias"] == resultado_auditoria["incidencias"]
    assert contenido["perfil"] == resultado_auditoria["perfil"]
    assert contenido["calidad"] == resultado_auditoria["calidad"]

    assert (
        contenido["resumen"]["tipos_semanticos"]
        == resultado_auditoria["resumen"]["tipos_semanticos"]
    )
    assert (
        contenido["resumen"]["cobertura_auditoria"]
        == resultado_auditoria["resumen"]["cobertura_auditoria"]
    )
    assert (
        contenido["calidad"]["incompatibilidades_tipo"]
        == resultado_auditoria["calidad"]["incompatibilidades_tipo"]
    )
    assert (
        contenido["calidad"]["reglas_negocio"]
        == resultado_auditoria["calidad"]["reglas_negocio"]
    )


def test_informe_json_no_incluye_filas_originales(tmp_path):
    """Comprueba que el JSON no incorpora datos originales del dataset."""
    resultado_auditoria = {
        "dataset": {
            "archivo": "prueba.csv",
            "filas": 2,
            "columnas": 2,
            "memoria_bytes": 128,
        },
        "resumen": {
            "total_incidencias": 0,
            "por_severidad": {
                "alta": 0,
                "media": 0,
                "baja": 0,
            },
            "por_categoria": {
                "completitud": 0,
                "unicidad": 0,
                "estructura": 0,
                "consistencia": 0,
                "validez": 0,
            },
            "principales_incidencias": [],
            "tipos_semanticos": {
                "numerico": 1,
                "fecha": 0,
                "fecha_hora": 0,
                "booleano_binario": 0,
                "categorico": 0,
                "identificador": 1,
                "texto_libre": 0,
            },
            "cobertura_auditoria": {
                "controles_aplicados": [
                    "completitud",
                    "unicidad_general",
                    "outliers",
                    "compatibilidad_semantica",
                ],
                "controles_no_aplicables": [
                    "consistencia_texto",
                ],
                "controles_no_configurados": [
                    "unicidad_clave",
                    "reglas_negocio",
                ],
            },
        },
        "tipos_semanticos": {
            "id": {
                "tipo": "identificador",
                "confianza": "alta",
                "fuente": "inferred",
                "evidencias": [],
            },
            "importe": {
                "tipo": "numerico",
                "confianza": "alta",
                "fuente": "inferred",
                "evidencias": [],
            },
        },
        "incidencias": [],
        "perfil": {
            "nombres_columnas": ["id", "importe"],
            "tipos_datos": {
                "id": "int64",
                "importe": "float64",
            },
            "valores_distintos": {
                "id": 2,
                "importe": 2,
            },
            "estadisticas_numericas": {},
        },
        "calidad": {
            "nulos": {},
            "nulos_textuales": {},
            "identificadores": {},
            "duplicados": {},
            "duplicados_clave": {},
            "columnas_problematicas": {},
            "texto": {},
            "outliers": {},
            "incompatibilidades_tipo": {},
            "reglas_negocio": {},
            "fechas": {},
        },
    }

    ruta_salida = tmp_path / "informe_sin_filas.json"

    generar_informe_json(
        resultado_auditoria,
        ruta_salida,
    )

    with ruta_salida.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        contenido = json.load(archivo)

    claves_prohibidas = {
        "datos",
        "filas_originales",
        "registros",
        "raw_data",
        "rows",
    }

    assert claves_prohibidas.isdisjoint(contenido)
    assert claves_prohibidas.isdisjoint(contenido["dataset"])

