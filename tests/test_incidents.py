"""Tests para el sistema de incidencias de DataQualityPy."""

import pytest

from src.incidents import generar_incidencias


def _crear_calidad_vacia() -> dict:
    """Crea una estructura mínima de calidad sin incidencias."""
    return {
        "nulos": {
            "total_nulos": 0,
            "columnas_con_nulos": 0,
            "por_columna": {},
        },
        "nulos_textuales": {},
        "identificadores": {},
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
        "texto": {},
        "outliers": {},
        "incompatibilidades_tipo": {},
        "reglas_negocio": {},
        "fechas": {},
    }


def test_generar_incidencias_crea_incidencia_de_nulos() -> None:
    """Comprueba la estructura y severidad de una incidencia."""
    calidad = _crear_calidad_vacia()
    calidad["nulos"] = {
        "total_nulos": 2,
        "columnas_con_nulos": 1,
        "por_columna": {
            "precio": {
                "nulos": 2,
                "porcentaje_nulos": 20.0,
            }
        },
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=10,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert set(incidencia) == {
        "tipo",
        "categoria",
        "severidad",
        "columna",
        "cantidad",
        "porcentaje",
        "mensaje",
    }

    assert incidencia["tipo"] == "nulos_reales"
    assert incidencia["categoria"] == "completitud"
    assert incidencia["severidad"] == "alta"
    assert incidencia["columna"] == "precio"
    assert incidencia["cantidad"] == 2
    assert incidencia["porcentaje"] == 20.0


@pytest.mark.parametrize(
    ("porcentaje", "severidad"),
    [
        (4.99, "baja"),
        (5.0, "media"),
        (19.99, "media"),
        (20.0, "alta"),
    ],
)
def test_incompatibilidad_tipo_clasifica_severidad_por_porcentaje(
    porcentaje: float,
    severidad: str,
) -> None:
    """Comprueba los límites de severidad de incompatibilidades."""
    calidad = _crear_calidad_vacia()
    calidad["incompatibilidades_tipo"] = {
        "Age": {
            "tipo_semantico": "numerico",
            "cantidad_incompatibles": 1,
            "porcentaje_incompatibles": porcentaje,
        }
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=100,
    )

    assert len(incidencias) == 1
    assert incidencias[0]["tipo"] == "incompatibilidad_tipo"
    assert incidencias[0]["categoria"] == "validez"
    assert incidencias[0]["severidad"] == severidad


def test_generar_incidencia_de_incompatibilidad_numerica() -> None:
    """Comprueba una incompatibilidad con tipo semántico numérico."""
    calidad = _crear_calidad_vacia()
    calidad["incompatibilidades_tipo"] = {
        "Age": {
            "tipo_semantico": "numerico",
            "cantidad_incompatibles": 1,
            "porcentaje_incompatibles": 20.0,
        }
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=7,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["tipo"] == "incompatibilidad_tipo"
    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "alta"
    assert incidencia["columna"] == "Age"
    assert incidencia["cantidad"] == 1
    assert incidencia["porcentaje"] == 20.0
    assert incidencia["mensaje"] == (
        "La columna 'Age' contiene 1 valor incompatible "
        "con el tipo semántico 'numerico' "
        "(20,00 % de los valores evaluables)."
    )


def test_generar_incidencia_de_incompatibilidad_temporal() -> None:
    """Comprueba una incompatibilidad con tipo semántico fecha."""
    calidad = _crear_calidad_vacia()
    calidad["incompatibilidades_tipo"] = {
        "fecha_alta": {
            "tipo_semantico": "fecha",
            "cantidad_incompatibles": 2,
            "porcentaje_incompatibles": 10.0,
        }
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=25,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["tipo"] == "incompatibilidad_tipo"
    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "media"
    assert incidencia["columna"] == "fecha_alta"
    assert incidencia["cantidad"] == 2
    assert incidencia["porcentaje"] == 10.0


def test_generar_incidencia_de_incompatibilidad_booleana() -> None:
    """Comprueba una incompatibilidad con tipo semántico booleano."""
    calidad = _crear_calidad_vacia()
    calidad["incompatibilidades_tipo"] = {
        "activo": {
            "tipo_semantico": "booleano_binario",
            "cantidad_incompatibles": 1,
            "porcentaje_incompatibles": 2.5,
        }
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=50,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["tipo"] == "incompatibilidad_tipo"
    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "baja"
    assert incidencia["columna"] == "activo"
    assert incidencia["cantidad"] == 1
    assert incidencia["porcentaje"] == 2.5


def test_no_genera_incidencia_si_no_hay_incompatibilidades() -> None:
    """Comprueba que una auditoría compatible no crea incidencia."""
    calidad = _crear_calidad_vacia()

    incidencias = generar_incidencias(
        calidad,
        total_filas=10,
    )

    assert incidencias == []


def test_incompatibilidad_temporal_evitar_duplicar_conversion_fecha() -> None:
    """
    Comprueba que una incompatibilidad semántica temporal prevalece
    sobre la incidencia heredada de conversión de fecha.
    """
    calidad = _crear_calidad_vacia()
    calidad["incompatibilidades_tipo"] = {
        "fecha_alta": {
            "tipo_semantico": "fecha",
            "cantidad_incompatibles": 1,
            "porcentaje_incompatibles": 20.0,
        }
    }
    calidad["fechas"] = {
        "fecha_alta": {
            "valores_validos": 4,
            "conversiones_fallidas": 1,
        }
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=5,
    )

    assert len(incidencias) == 1
    assert incidencias[0]["tipo"] == "incompatibilidad_tipo"
    assert incidencias[0]["columna"] == "fecha_alta"


@pytest.mark.parametrize(
    ("porcentaje", "severidad"),
    [
        (4.99, "baja"),
        (5.0, "media"),
        (19.99, "media"),
        (20.0, "alta"),
    ],
)
def test_incumplimiento_regla_clasifica_severidad_por_porcentaje(
    porcentaje: float,
    severidad: str,
) -> None:
    """Comprueba los límites de severidad de reglas de negocio."""
    calidad = _crear_calidad_vacia()
    calidad["reglas_negocio"] = {
        "Age": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": porcentaje,
            },
        },
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=100,
    )

    assert len(incidencias) == 1
    assert incidencias[0]["tipo"] == "incumplimiento_regla"
    assert incidencias[0]["categoria"] == "validez"
    assert incidencias[0]["severidad"] == severidad


def test_generar_incidencia_de_regla_min() -> None:
    """Comprueba la incidencia generada por un límite mínimo."""
    calidad = _crear_calidad_vacia()
    calidad["reglas_negocio"] = {
        "Age": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": 25.0,
            },
        },
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=7,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["tipo"] == "incumplimiento_regla"
    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "alta"
    assert incidencia["columna"] == "Age"
    assert incidencia["cantidad"] == 1
    assert incidencia["porcentaje"] == 25.0
    assert incidencia["mensaje"] == (
        "La columna 'Age' contiene 1 valor que incumple "
        "la regla 'min=0' "
        "(25,00 % de los valores evaluables para la regla)."
    )


def test_generar_incidencia_de_regla_max() -> None:
    """Comprueba la incidencia generada por un límite máximo."""
    calidad = _crear_calidad_vacia()
    calidad["reglas_negocio"] = {
        "Age": {
            "max": {
                "valor_regla": 120,
                "cantidad_incumplimientos": 2,
                "porcentaje_incumplimientos": 10.0,
            },
        },
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=25,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["tipo"] == "incumplimiento_regla"
    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "media"
    assert incidencia["columna"] == "Age"
    assert incidencia["cantidad"] == 2
    assert incidencia["porcentaje"] == 10.0
    assert incidencia["mensaje"] == (
        "La columna 'Age' contiene 2 valores que incumplen "
        "la regla 'max=120' "
        "(10,00 % de los valores evaluables para la regla)."
    )


def test_generar_incidencia_de_valores_permitidos() -> None:
    """Comprueba la incidencia sin volcar la lista de valores permitidos."""
    calidad = _crear_calidad_vacia()
    calidad["reglas_negocio"] = {
        "estado": {
            "valores_permitidos": {
                "valor_regla": [
                    "Activo",
                    "Inactivo",
                    "Pendiente",
                ],
                "cantidad_incumplimientos": 2,
                "porcentaje_incumplimientos": 20.0,
            },
        },
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=10,
    )

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["tipo"] == "incumplimiento_regla"
    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "alta"
    assert incidencia["columna"] == "estado"
    assert incidencia["cantidad"] == 2
    assert incidencia["porcentaje"] == 20.0
    assert incidencia["mensaje"] == (
        "La columna 'estado' contiene 2 valores que incumplen "
        "la regla 'valores_permitidos' "
        "(20,00 % de los valores evaluables para la regla)."
    )
    assert "Activo" not in incidencia["mensaje"]
    assert "Inactivo" not in incidencia["mensaje"]
    assert "Pendiente" not in incidencia["mensaje"]


def test_reglas_multiples_generan_incidencias_independientes() -> None:
    """Comprueba una incidencia independiente por regla incumplida."""
    calidad = _crear_calidad_vacia()
    calidad["reglas_negocio"] = {
        "Age": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": 25.0,
            },
            "max": {
                "valor_regla": 120,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": 25.0,
            },
        },
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=7,
    )

    assert len(incidencias) == 2
    assert [incidencia["tipo"] for incidencia in incidencias] == [
        "incumplimiento_regla",
        "incumplimiento_regla",
    ]
    assert [incidencia["columna"] for incidencia in incidencias] == [
        "Age",
        "Age",
    ]
    assert [incidencia["cantidad"] for incidencia in incidencias] == [
        1,
        1,
    ]
    assert "min=0" in incidencias[0]["mensaje"]
    assert "max=120" in incidencias[1]["mensaje"]


def test_no_genera_incidencia_si_no_hay_reglas_incumplidas() -> None:
    """Comprueba que una auditoría sin incumplimientos no cree incidencia."""
    calidad = _crear_calidad_vacia()

    incidencias = generar_incidencias(
        calidad,
        total_filas=10,
    )

    assert incidencias == []

