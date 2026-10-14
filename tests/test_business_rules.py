"""Tests para las reglas de negocio configurables de DataQualityPy."""

import pandas as pd
import pytest

from src.business_rules import evaluar_reglas_negocio
from src.column_analysis import analizar_columnas
from src.inference import (
    InferenceConfidence,
    SemanticInference,
    SemanticType,
)


def _crear_inferencia(
    columna: object,
    tipo: SemanticType,
) -> SemanticInference:
    """Crea una inferencia mínima para aislar las reglas de negocio."""
    return SemanticInference(
        column_name=columna,
        semantic_type=tipo,
        confidence=InferenceConfidence.HIGH,
        evidence=("Tipo semántico fijado para la prueba.",),
        source="declared",
    )


def test_sin_reglas_devuelve_resultado_vacio() -> None:
    """Comprueba que no se generen resultados sin reglas configuradas."""
    datos = pd.DataFrame({"Age": ["20", "30", "40"]})
    analisis = analizar_columnas(datos)
    inferencias = {
        "Age": _crear_inferencia("Age", SemanticType.NUMERIC),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {},
    )

    assert resultado == {}


def test_regla_min_numerica_detecta_incumplimientos() -> None:
    """Comprueba una regla mínima sobre una columna numérica textual."""
    datos = pd.DataFrame(
        {
            "Age": ["20", "-5", "0", "30"],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "Age": _crear_inferencia("Age", SemanticType.NUMERIC),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {"Age": {"min": 0}},
    )

    assert resultado == {
        "Age": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(25.0),
            },
        },
    }


def test_regla_max_numerica_detecta_incumplimientos() -> None:
    """Comprueba una regla máxima inclusiva."""
    datos = pd.DataFrame(
        {
            "Age": ["20", "120", "121", "999"],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "Age": _crear_inferencia("Age", SemanticType.NUMERIC),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {"Age": {"max": 120}},
    )

    assert resultado == {
        "Age": {
            "max": {
                "valor_regla": 120,
                "cantidad_incumplimientos": 2,
                "porcentaje_incumplimientos": pytest.approx(50.0),
            },
        },
    }


def test_min_y_max_son_inclusivos() -> None:
    """Comprueba que los valores exactamente en los límites sean válidos."""
    datos = pd.DataFrame(
        {
            "puntuacion": ["0", "5", "10"],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "puntuacion": _crear_inferencia(
            "puntuacion",
            SemanticType.NUMERIC,
        ),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {
            "puntuacion": {
                "min": 0,
                "max": 10,
            },
        },
    )

    assert resultado == {}


def test_min_excluye_nulos_e_incompatibles_del_denominador() -> None:
    """Comprueba que completitud e incompatibilidad no se dupliquen."""
    datos = pd.DataFrame(
        {
            "Age": ["20", "-5", "abc", "NA", None],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "Age": _crear_inferencia("Age", SemanticType.NUMERIC),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {"Age": {"min": 0}},
    )

    assert resultado == {
        "Age": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(50.0),
            },
        },
    }


def test_min_max_no_se_aplican_a_tipo_no_numerico() -> None:
    """Comprueba que los límites numéricos sólo se apliquen a NUMERIC."""
    datos = pd.DataFrame(
        {
            "codigo": [1, 2, 3],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "codigo": _crear_inferencia(
            "codigo",
            SemanticType.IDENTIFIER,
        ),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {
            "codigo": {
                "min": 2,
                "max": 2,
            },
        },
    )

    assert resultado == {}


def test_valores_permitidos_detecta_incumplimientos_exactos() -> None:
    """Comprueba la comparación exacta de valores permitidos."""
    datos = pd.DataFrame(
        {
            "estado": [
                "Activo",
                "Inactivo",
                "activo",
                " Activo ",
            ],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "estado": _crear_inferencia(
            "estado",
            SemanticType.CATEGORICAL,
        ),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {
            "estado": {
                "valores_permitidos": [
                    "Activo",
                    "Inactivo",
                ],
            },
        },
    )

    assert resultado == {
        "estado": {
            "valores_permitidos": {
                "valor_regla": [
                    "Activo",
                    "Inactivo",
                ],
                "cantidad_incumplimientos": 2,
                "porcentaje_incumplimientos": pytest.approx(50.0),
            },
        },
    }


def test_valores_permitidos_excluye_nulos_del_denominador() -> None:
    """Comprueba que los nulos no se contabilicen como incumplimientos."""
    datos = pd.DataFrame(
        {
            "estado": [
                "Activo",
                "Desconocido",
                "NA",
                None,
            ],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "estado": _crear_inferencia(
            "estado",
            SemanticType.CATEGORICAL,
        ),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {
            "estado": {
                "valores_permitidos": [
                    "Activo",
                    "Inactivo",
                ],
            },
        },
    )

    assert resultado == {
        "estado": {
            "valores_permitidos": {
                "valor_regla": [
                    "Activo",
                    "Inactivo",
                ],
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(50.0),
            },
        },
    }


def test_reglas_combinadas_se_evalúan_independientemente() -> None:
    """Comprueba que cada regla conserve su propio resultado."""
    datos = pd.DataFrame(
        {
            "puntuacion": [0, 5, 11, -1],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "puntuacion": _crear_inferencia(
            "puntuacion",
            SemanticType.NUMERIC,
        ),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {
            "puntuacion": {
                "min": 0,
                "max": 10,
                "valores_permitidos": [0, 5, 10],
            },
        },
    )

    assert resultado == {
        "puntuacion": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(25.0),
            },
            "max": {
                "valor_regla": 10,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(25.0),
            },
            "valores_permitidos": {
                "valor_regla": [0, 5, 10],
                "cantidad_incumplimientos": 2,
                "porcentaje_incumplimientos": pytest.approx(50.0),
            },
        },
    }


def test_regla_sin_incumplimientos_no_aparece_en_resultado() -> None:
    """Comprueba que el resultado sólo contenga hallazgos reales."""
    datos = pd.DataFrame(
        {
            "Age": [20, 30, 40],
        }
    )
    analisis = analizar_columnas(datos)
    inferencias = {
        "Age": _crear_inferencia("Age", SemanticType.NUMERIC),
    }

    resultado = evaluar_reglas_negocio(
        analisis,
        inferencias,
        {
            "Age": {
                "min": 0,
                "max": 120,
            },
        },
    )

    assert resultado == {}


def test_columna_configurada_ausente_genera_error_claro() -> None:
    """Comprueba que una regla no pueda apuntar silenciosamente a otra tabla."""
    datos = pd.DataFrame({"Age": [20, 30]})
    analisis = analizar_columnas(datos)
    inferencias = {
        "Age": _crear_inferencia("Age", SemanticType.NUMERIC),
    }

    with pytest.raises(
        ValueError,
        match="columna configurada.*precio.*no existe",
    ):
        evaluar_reglas_negocio(
            analisis,
            inferencias,
            {"precio": {"min": 0}},
        )
