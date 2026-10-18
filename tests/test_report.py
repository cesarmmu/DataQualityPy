"""Pruebas de la presentación en consola de DataQualityPy V3."""

from src.report import (
    generar_informe,
    mostrar_incompatibilidades_semanticas,
    mostrar_reglas_negocio,
    mostrar_resumen_ejecutivo,
    mostrar_tipos,
)


def _dataset() -> dict:
    return {
        "archivo": "datos.csv",
        "filas": 4,
        "columnas": 3,
        "memoria_bytes": 512,
    }


def _perfil() -> dict:
    return {
        "nombres_columnas": ["id_cliente", "Age", "categoria"],
        "tipos_datos": {
            "id_cliente": "int64",
            "Age": "object",
            "categoria": "object",
        },
        "valores_distintos": {
            "id_cliente": 4,
            "Age": 4,
            "categoria": 2,
        },
        "estadisticas_numericas": {},
    }


def _tipos_semanticos() -> dict:
    return {
        "id_cliente": {
            "tipo": "identificador",
            "confianza": "alta",
            "fuente": "inferred",
            "evidencias": ["Nombre y unicidad compatibles con identificador."],
        },
        "Age": {
            "tipo": "numerico",
            "confianza": "alta",
            "fuente": "declared",
            "evidencias": [
                "El tipo semántico fue declarado explícitamente "
                "en la configuración."
            ],
        },
        "categoria": {
            "tipo": "categorico",
            "confianza": "media",
            "fuente": "inferred",
            "evidencias": ["Cardinalidad compatible con categoría."],
        },
    }


def _resumen() -> dict:
    return {
        "total_incidencias": 1,
        "por_severidad": {
            "alta": 0,
            "media": 1,
            "baja": 0,
        },
        "por_categoria": {
            "completitud": 0,
            "unicidad": 0,
            "estructura": 0,
            "consistencia": 0,
            "validez": 1,
        },
        "principales_incidencias": [
            {
                "severidad": "media",
                "mensaje": "La columna Age contiene valores incompatibles.",
            }
        ],
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
            ],
            "controles_no_aplicables": [],
            "controles_no_configurados": [
                "unicidad_clave",
                "reglas_negocio",
            ],
        },
    }


def _calidad() -> dict:
    return {
        "nulos": {
            "total_nulos": 0,
            "columnas_con_nulos": 0,
            "por_columna": {
                "id_cliente": {"nulos": 0, "porcentaje_nulos": 0.0},
                "Age": {"nulos": 0, "porcentaje_nulos": 0.0},
                "categoria": {"nulos": 0, "porcentaje_nulos": 0.0},
            },
        },
        "nulos_textuales": {},
        "identificadores": {},
        "duplicados": {
            "filas_duplicadas": 0,
            "porcentaje_duplicados": 0.0,
        },
        "duplicados_clave": {
            "clave_configurada": False,
            "columnas_clave": [],
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
        "texto": {},
        "outliers": {},
        "incompatibilidades_tipo": {
            "Age": {
                "tipo_semantico": "numerico",
                "valores_evaluados": 4,
                "valores_incompatibles": 1,
                "porcentaje_incompatibles": 25.0,
            }
        },
        "reglas_negocio": {
            "Age": {
                "min": {
                    "regla": "min",
                    "valor_configurado": 0,
                    "valores_evaluados": 3,
                    "valores_incumplidos": 1,
                    "porcentaje_incumplimiento": 33.3333333333,
                }
            }
        },
        "fechas": {},
    }


def _incidencias() -> list[dict]:
    return [
        {
            "tipo": "incompatibilidad_tipo",
            "categoria": "validez",
            "severidad": "media",
            "columna": "Age",
            "cantidad": 1,
            "porcentaje": 25.0,
            "mensaje": "La columna Age contiene valores incompatibles.",
        }
    ]


def test_resumen_ejecutivo_muestra_tipos_semanticos_y_cobertura(
    capsys,
) -> None:
    """El resumen V3 presenta tipos semánticos y cobertura."""
    mostrar_resumen_ejecutivo(_dataset(), _resumen())

    salida = capsys.readouterr().out

    assert "TIPOS SEMÁNTICOS" in salida
    assert "Numérico: 1" in salida
    assert "Categórico: 1" in salida
    assert "Identificador: 1" in salida

    assert "COBERTURA DE AUDITORÍA" in salida
    assert "Controles aplicados:" in salida
    assert "Completitud" in salida
    assert "Compatibilidad semántica" in salida
    assert "Controles no configurados:" in salida
    assert "Unicidad por clave" in salida
    assert "Reglas de negocio" in salida


def test_mostrar_tipos_incluye_dtype_tipo_confianza_y_origen(
    capsys,
) -> None:
    """La sección de tipos combina información física y semántica."""
    mostrar_tipos(_perfil(), _tipos_semanticos())

    salida = capsys.readouterr().out

    assert "TIPOS DE DATOS Y TIPOS SEMÁNTICOS" in salida
    assert "Age:" in salida
    assert "Dtype físico: object" in salida
    assert "Tipo semántico: Numérico" in salida
    assert "Confianza: Alta" in salida
    assert "Origen: Declarado" in salida
    assert "Valores distintos: 4" in salida


def test_mostrar_incompatibilidades_semanticas_presenta_resultados(
    capsys,
) -> None:
    """Las incompatibilidades ya calculadas se presentan sin reinterpretarlas."""
    mostrar_incompatibilidades_semanticas(_calidad())

    salida = capsys.readouterr().out

    assert "INCOMPATIBILIDADES DE TIPO SEMÁNTICO" in salida
    assert "Age:" in salida
    assert "Tipo semántico: Numérico" in salida
    assert "Valores evaluados: 4" in salida
    assert "Valores incompatibles: 1" in salida
    assert "25,00 %" in salida


def test_mostrar_incompatibilidades_semanticas_sin_resultados(
    capsys,
) -> None:
    """La ausencia de incompatibilidades se comunica claramente."""
    calidad = _calidad()
    calidad["incompatibilidades_tipo"] = {}

    mostrar_incompatibilidades_semanticas(calidad)

    salida = capsys.readouterr().out

    assert "INCOMPATIBILIDADES DE TIPO SEMÁNTICO" in salida
    assert "No se han detectado incompatibilidades semánticas." in salida


def test_mostrar_reglas_negocio_presenta_incumplimientos(
    capsys,
) -> None:
    """Las reglas de negocio muestran el resultado ya calculado."""
    mostrar_reglas_negocio(_calidad())

    salida = capsys.readouterr().out

    assert "REGLAS DE NEGOCIO" in salida
    assert "Age:" in salida
    assert "Regla: min" in salida
    assert "Valor configurado: 0" in salida
    assert "Valores evaluados: 3" in salida
    assert "Valores incumplidos: 1" in salida
    assert "33,33 %" in salida


def test_mostrar_reglas_negocio_sin_incumplimientos(
    capsys,
) -> None:
    """La ausencia de incumplimientos se comunica claramente."""
    calidad = _calidad()
    calidad["reglas_negocio"] = {}

    mostrar_reglas_negocio(calidad)

    salida = capsys.readouterr().out

    assert "REGLAS DE NEGOCIO" in salida
    assert "No se han detectado incumplimientos de reglas de negocio." in salida


def test_generar_informe_integra_secciones_v3(capsys) -> None:
    """El informe completo incorpora las nuevas secciones de V3."""
    resultado = {
        "dataset": _dataset(),
        "perfil": _perfil(),
        "tipos_semanticos": _tipos_semanticos(),
        "calidad": _calidad(),
        "incidencias": _incidencias(),
        "resumen": _resumen(),
    }

    generar_informe(resultado)

    salida = capsys.readouterr().out

    assert "RESUMEN EJECUTIVO" in salida
    assert "TIPOS DE DATOS Y TIPOS SEMÁNTICOS" in salida
    assert "13. INCOMPATIBILIDADES DE TIPO SEMÁNTICO" in salida
    assert "14. REGLAS DE NEGOCIO" in salida
    assert "15. INCIDENCIAS DETECTADAS" in salida
    assert "FIN DEL INFORME" in salida


def test_generar_informe_v7_muestra_explicabilidad(capsys) -> None:
    resultado = {
        "dataset": _dataset(), "perfil": _perfil(),
        "tipos_semanticos": _tipos_semanticos(), "calidad": _calidad(),
        "incidencias": _incidencias(), "resumen": _resumen(),
        "analisis_avanzado": {
            "diagnosticos": [{
                "tipo_incidencia": "incompatibilidad_tipo",
                "columna": "Age",
                "explicacion": "Se observaron valores no compatibles.",
                "explicacion_severidad": "Afecta al 25 % de los valores.",
                "evidencias": [{"clave": "ratio", "etiqueta": "Porcentaje", "valor": "25 %", "fuente": "calidad"}],
            }]
        },
    }
    generar_informe(resultado)
    salida = capsys.readouterr().out
    assert "16. ANÁLISIS AVANZADO Y EXPLICABILIDAD" in salida
    assert "¿Por qué se ha detectado?" in salida
    assert "¿Por qué tiene esta severidad?" in salida
    assert "Evidencias del diagnóstico" in salida


def test_generar_informe_v7_muestra_reauditoria_y_reproducibilidad(capsys) -> None:
    resultado = {
        "dataset": _dataset(), "perfil": _perfil(),
        "tipos_semanticos": _tipos_semanticos(), "calidad": _calidad(),
        "incidencias": _incidencias(), "resumen": _resumen(),
    }
    reauditoria = {
        "comparacion": {
            "resueltas": [{}], "persistentes": [], "nuevas": [],
            "totales": {"resueltas": 1, "persistentes": 0, "nuevas": 0},
        }
    }
    manifiesto = {
        "format_version": "2.0", "created_at": "2026-10-18T12:00:00+02:00",
        "dataset": {"file_name": "datos.csv", "sha256": "a" * 64},
        "environment": {"dataqualitypy": "7.0.0", "python": "3.12.10"},
    }
    generar_informe(
        resultado,
        resultado_reauditoria=reauditoria,
        manifiesto_reproducibilidad=manifiesto,
    )
    salida = capsys.readouterr().out
    assert "17. LIMPIEZA Y REAUDITORÍA" in salida
    assert "Incidencias resueltas: 1" in salida
    assert "18. REPRODUCIBILIDAD" in salida
    assert "SHA-256:" in salida
    assert "DataQualityPy: 7.0.0" in salida


def test_generar_informe_v7_no_inventa_bloques_opcionales(capsys) -> None:
    resultado = {
        "dataset": _dataset(), "perfil": _perfil(),
        "tipos_semanticos": _tipos_semanticos(), "calidad": _calidad(),
        "incidencias": _incidencias(), "resumen": _resumen(),
    }
    generar_informe(resultado)
    salida = capsys.readouterr().out
    assert "16. ANÁLISIS AVANZADO Y EXPLICABILIDAD" not in salida
    assert "17. LIMPIEZA Y REAUDITORÍA" not in salida
    assert "18. REPRODUCIBILIDAD" not in salida
