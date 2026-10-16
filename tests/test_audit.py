"""Tests para la coordinación de la auditoría de DataQualityPy."""

import pandas as pd
import pytest

from src.audit import auditar_dataset
from src.config import cargar_configuracion


def test_auditar_dataset_genera_resultado_estructurado() -> None:
    """Comprueba la estructura principal del resultado de auditoría."""
    datos = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "producto": [
                "Portatil",
                "Raton",
                "Teclado",
            ],
            "precio": [
                899.99,
                24.50,
                49.99,
            ],
        }
    )

    configuracion = cargar_configuracion()

    resultado = auditar_dataset(
        datos,
        nombre_archivo="datos_prueba.csv",
        configuracion=configuracion,
    )

    assert set(resultado) == {
        "dataset",
        "perfil",
        "tipos_semanticos",
        "calidad",
        "incidencias",
        "resumen",
        "analisis_avanzado",
    }

    assert resultado["dataset"] == {
        "archivo": "datos_prueba.csv",
        "filas": 3,
        "columnas": 3,
        "memoria_bytes": resultado["dataset"]["memoria_bytes"],
    }

    assert set(resultado["perfil"]) == {
        "nombres_columnas",
        "tipos_datos",
        "valores_distintos",
        "estadisticas_numericas",
    }

    assert set(resultado["tipos_semanticos"]) == {
        "id",
        "producto",
        "precio",
    }

    assert set(resultado["calidad"]) == {
        "nulos",
        "nulos_textuales",
        "identificadores",
        "duplicados",
        "duplicados_clave",
        "columnas_problematicas",
        "texto",
        "outliers",
        "incompatibilidades_tipo",
        "reglas_negocio",
        "fechas",
    }

    assert isinstance(resultado["incidencias"], list)

    assert set(resultado["resumen"]) == {
        "total_incidencias",
        "por_severidad",
        "por_categoria",
        "principales_incidencias",
        "tipos_semanticos",
        "cobertura_auditoria",
    }

    assert resultado["resumen"]["total_incidencias"] == len(
        resultado["incidencias"]
    )

    analisis_avanzado = resultado["analisis_avanzado"]

    assert set(analisis_avanzado) == {
        "columnas",
        "claves_candidatas",
        "distribuciones",
        "diagnosticos",
        "relaciones",
    }

    assert set(analisis_avanzado["columnas"]) == {
        "id",
        "producto",
        "precio",
    }

    assert set(analisis_avanzado["claves_candidatas"]) == {
        "id",
        "producto",
        "precio",
    }

    assert set(analisis_avanzado["distribuciones"]) == {
        "id",
        "producto",
        "precio",
    }

    assert isinstance(
        analisis_avanzado["diagnosticos"],
        list,
    )

    assert set(analisis_avanzado["relaciones"]) == {
        "claves_compuestas",
        "relaciones_funcionales",
        "relaciones_presencia",
    }


def test_auditar_dataset_integra_inferencia_semantica() -> None:
    """
    Comprueba la integración entre inferencia semántica
    y perfilado numérico.
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
            "Age": [
                "22",
                "38",
                "NA",
                "35",
                "54",
            ],
            "fecha_alta": [
                "01/01/2026",
                "15/01/2026",
                "01/02/2026",
                "15/02/2026",
                "01/03/2026",
            ],
            "activo": [
                "Sí",
                "No",
                "Sí",
                "No",
                "Sí",
            ],
        }
    )

    configuracion = cargar_configuracion()

    resultado = auditar_dataset(
        datos,
        nombre_archivo="semantica.csv",
        configuracion=configuracion,
    )

    tipos = resultado["tipos_semanticos"]

    assert tipos["cliente_id"]["tipo"] == "identificador"
    assert tipos["cliente_id"]["confianza"] == "alta"

    assert tipos["Age"]["tipo"] == "numerico"
    assert tipos["Age"]["confianza"] == "alta"

    assert tipos["fecha_alta"]["tipo"] == "fecha"
    assert tipos["fecha_alta"]["confianza"] == "alta"

    assert tipos["activo"]["tipo"] == "booleano_binario"
    assert tipos["activo"]["confianza"] == "alta"

    estadisticas = resultado["perfil"][
        "estadisticas_numericas"
    ]

    assert "Age" in estadisticas
    assert "cliente_id" not in estadisticas
    assert "fecha_alta" not in estadisticas
    assert "activo" not in estadisticas

    assert estadisticas["Age"]["minimo"] == 22.0
    assert estadisticas["Age"]["maximo"] == 54.0
    assert estadisticas["Age"]["media"] == 37.25
    assert estadisticas["Age"]["mediana"] == 36.5


def test_auditar_dataset_conserva_dtype_fisico_de_age() -> None:
    """
    Comprueba que inferir Age como numérica no modifica el DataFrame original.
    """
    datos = pd.DataFrame(
        {
            "Age": [
                "22",
                "38",
                "NA",
                "35",
                None,
                "54",
            ],
        },
        dtype="object",
    )

    original = datos.copy(deep=True)

    configuracion = cargar_configuracion()

    resultado = auditar_dataset(
        datos,
        nombre_archivo="age.csv",
        configuracion=configuracion,
    )

    assert resultado["tipos_semanticos"]["Age"]["tipo"] == "numerico"

    assert datos["Age"].dtype == "object"

    pd.testing.assert_frame_equal(
        datos,
        original,
    )


def test_auditar_dataset_integra_outliers_semanticos() -> None:
    """
    Comprueba outliers en una columna object numérica
    y excluye identificadores numéricos.
    """
    datos = pd.DataFrame(
        {
            "cliente_id": [
                1001,
                1002,
                1003,
                1004,
                999999,
                1006,
                1007,
            ],
            "Age": [
                "20",
                "21",
                "22",
                "23",
                "24",
                "25",
                "100",
            ],
        }
    )

    configuracion = cargar_configuracion()

    resultado = auditar_dataset(
        datos,
        nombre_archivo="outliers_semanticos.csv",
        configuracion=configuracion,
    )

    tipos = resultado["tipos_semanticos"]
    outliers = resultado["calidad"]["outliers"]

    assert tipos["cliente_id"]["tipo"] == "identificador"
    assert tipos["Age"]["tipo"] == "numerico"

    assert "cliente_id" not in outliers
    assert "Age" in outliers

    assert outliers["Age"]["cantidad_outliers"] == 1
    assert outliers["Age"]["porcentaje_outliers"] == pytest.approx(
        100 / 7
    )


def test_auditar_dataset_respeta_umbral_fecha_configurado() -> None:
    """Comprueba que audit.py transmite umbral_fecha a la inferencia."""
    datos = pd.DataFrame(
        {
            "fecha_alta": [
                "01/01/2026",
                "15/02/2026",
                "31/03/2026",
                "20/04/2026",
                "valor_invalido",
            ],
        }
    )

    configuracion_80 = cargar_configuracion()
    configuracion_80["umbral_fecha"] = 80.0

    resultado_80 = auditar_dataset(
        datos,
        nombre_archivo="fechas_umbral_80.csv",
        configuracion=configuracion_80,
    )

    configuracion_90 = cargar_configuracion()
    configuracion_90["umbral_fecha"] = 90.0

    resultado_90 = auditar_dataset(
        datos,
        nombre_archivo="fechas_umbral_90.csv",
        configuracion=configuracion_90,
    )

    assert (
        resultado_80["tipos_semanticos"]["fecha_alta"]["tipo"]
        == "fecha"
    )
    assert (
        resultado_90["tipos_semanticos"]["fecha_alta"]["tipo"]
        not in {"fecha", "fecha_hora"}
    )


def test_auditar_dataset_integra_tipo_declarado_en_analisis_semantico() -> None:
    """
    Comprueba que un tipo declarado prevalece y se propaga
    al perfilado y a los outliers semánticos.
    """
    datos = pd.DataFrame(
        {
            "cliente_id": [
                1001,
                1002,
                1003,
                1004,
                1005,
                1006,
                999999,
            ],
        }
    )

    configuracion = cargar_configuracion()
    configuracion["tipos_columnas"] = {
        "cliente_id": "numerico",
    }

    resultado = auditar_dataset(
        datos,
        nombre_archivo="tipo_declarado.csv",
        configuracion=configuracion,
    )

    tipo = resultado["tipos_semanticos"]["cliente_id"]
    estadisticas = resultado["perfil"]["estadisticas_numericas"]
    outliers = resultado["calidad"]["outliers"]

    assert tipo["tipo"] == "numerico"
    assert tipo["confianza"] == "alta"
    assert tipo["fuente"] == "declared"
    assert tipo["evidencias"] == [
        "El tipo semántico fue declarado explícitamente "
        "en la configuración."
    ]

    assert "cliente_id" in estadisticas
    assert estadisticas["cliente_id"]["minimo"] == 1001.0
    assert estadisticas["cliente_id"]["maximo"] == 999999.0

    assert "cliente_id" in outliers
    assert outliers["cliente_id"]["cantidad_outliers"] == 1
    assert outliers["cliente_id"]["porcentaje_outliers"] == pytest.approx(
        100 / 7
    )


def test_auditar_dataset_integra_incompatibilidades_semanticas() -> None:
    """
    Comprueba la detección de incompatibilidades semánticas
    dentro del resultado completo de auditoría.
    """
    datos = pd.DataFrame(
        {
            "Age": [
                "20",
                "30",
                "40",
                "50",
                "error",
                "NA",
                None,
            ],
        },
        dtype="object",
    )

    configuracion = cargar_configuracion()

    resultado = auditar_dataset(
        datos,
        nombre_archivo="incompatibilidades.csv",
        configuracion=configuracion,
    )

    tipo = resultado["tipos_semanticos"]["Age"]
    incompatibilidades = resultado["calidad"]["incompatibilidades_tipo"]

    assert tipo["tipo"] == "numerico"
    assert tipo["confianza"] == "media"

    assert "Age" in incompatibilidades
    assert incompatibilidades["Age"]["tipo_semantico"] == "numerico"
    assert incompatibilidades["Age"]["cantidad_incompatibles"] == 1
    assert incompatibilidades["Age"][
        "porcentaje_incompatibles"
    ] == pytest.approx(20.0)


def test_auditar_dataset_genera_incidencia_por_incompatibilidad_semantica() -> None:
    """
    Comprueba el recorrido completo desde la incompatibilidad semántica
    hasta la incidencia estructurada de auditoría.
    """
    datos = pd.DataFrame(
        {
            "Age": [
                "20",
                "30",
                "40",
                "50",
                "error",
                "NA",
                None,
            ],
        },
        dtype="object",
    )

    configuracion = cargar_configuracion()

    resultado = auditar_dataset(
        datos,
        nombre_archivo="incidencia_incompatibilidad.csv",
        configuracion=configuracion,
    )

    incidencias = [
        incidencia
        for incidencia in resultado["incidencias"]
        if incidencia["tipo"] == "incompatibilidad_tipo"
    ]

    assert len(incidencias) == 1

    incidencia = incidencias[0]

    assert incidencia["categoria"] == "validez"
    assert incidencia["severidad"] == "alta"
    assert incidencia["columna"] == "Age"
    assert incidencia["cantidad"] == 1
    assert incidencia["porcentaje"] == pytest.approx(20.0)
    assert incidencia["mensaje"] == (
        "La columna 'Age' contiene 1 valor incompatible "
        "con el tipo semántico 'numerico' "
        "(20,00 % de los valores evaluables)."
    )


def test_auditar_dataset_integra_reglas_negocio() -> None:
    """
    Comprueba que las reglas configuradas se evalúen dentro
    del resultado estructurado de calidad.
    """
    datos = pd.DataFrame(
        {
            "Age": [
                "-5",
                "20",
                "120",
                "150",
                "error",
                "NA",
                None,
            ],
        },
        dtype="object",
    )

    configuracion = cargar_configuracion()
    configuracion["tipos_columnas"] = {
        "Age": "numerico",
    }
    configuracion["reglas_columnas"] = {
        "Age": {
            "min": 0,
            "max": 120,
        },
    }

    resultado = auditar_dataset(
        datos,
        nombre_archivo="reglas_negocio.csv",
        configuracion=configuracion,
    )

    reglas = resultado["calidad"]["reglas_negocio"]

    assert reglas == {
        "Age": {
            "min": {
                "valor_regla": 0,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(25.0),
            },
            "max": {
                "valor_regla": 120,
                "cantidad_incumplimientos": 1,
                "porcentaje_incumplimientos": pytest.approx(25.0),
            },
        },
    }


def test_auditar_dataset_genera_incidencias_por_reglas_negocio() -> None:
    """
    Comprueba el recorrido completo desde las reglas configuradas
    hasta las incidencias estructuradas de auditoría.
    """
    datos = pd.DataFrame(
        {
            "Age": [
                "-5",
                "20",
                "120",
                "150",
                "error",
                "NA",
                None,
            ],
        },
        dtype="object",
    )

    configuracion = cargar_configuracion()
    configuracion["tipos_columnas"] = {
        "Age": "numerico",
    }
    configuracion["reglas_columnas"] = {
        "Age": {
            "min": 0,
            "max": 120,
        },
    }

    resultado = auditar_dataset(
        datos,
        nombre_archivo="incidencias_reglas_negocio.csv",
        configuracion=configuracion,
    )

    incidencias = [
        incidencia
        for incidencia in resultado["incidencias"]
        if incidencia["tipo"] == "incumplimiento_regla"
    ]

    assert len(incidencias) == 2

    incidencia_min = incidencias[0]
    incidencia_max = incidencias[1]

    assert incidencia_min == {
        "tipo": "incumplimiento_regla",
        "categoria": "validez",
        "severidad": "alta",
        "columna": "Age",
        "cantidad": 1,
        "porcentaje": pytest.approx(25.0),
        "mensaje": (
            "La columna 'Age' contiene 1 valor que incumple "
            "la regla 'min=0' "
            "(25,00 % de los valores evaluables para la regla)."
        ),
    }

    assert incidencia_max == {
        "tipo": "incumplimiento_regla",
        "categoria": "validez",
        "severidad": "alta",
        "columna": "Age",
        "cantidad": 1,
        "porcentaje": pytest.approx(25.0),
        "mensaje": (
            "La columna 'Age' contiene 1 valor que incumple "
            "la regla 'max=120' "
            "(25,00 % de los valores evaluables para la regla)."
        ),
    }


def test_auditar_dataset_integra_resumen_ejecutivo_v3() -> None:
    """Comprueba tipos semánticos y cobertura en el resumen de una auditoría real."""
    datos = pd.DataFrame(
        {
            "id_cliente": [1, 2, 3, 4],
            "Age": ["20", "30", "40", "50"],
            "categoria": ["A", "B", "A", "B"],
        }
    )

    configuracion = cargar_configuracion()
    configuracion["tipos_columnas"] = {
        "id_cliente": "identificador",
        "Age": "numerico",
        "categoria": "categorico",
    }
    configuracion["columnas_clave"] = ["id_cliente"]
    configuracion["reglas_columnas"] = {
        "Age": {
            "min": 0,
            "max": 120,
        },
    }

    resultado = auditar_dataset(
        datos,
        nombre_archivo="resumen_v3.csv",
        configuracion=configuracion,
    )

    resumen = resultado["resumen"]

    assert resumen["tipos_semanticos"] == {
        "numerico": 1,
        "fecha": 0,
        "fecha_hora": 0,
        "booleano_binario": 0,
        "categorico": 1,
        "identificador": 1,
        "texto_libre": 0,
    }

    assert resumen["cobertura_auditoria"] == {
        "controles_aplicados": [
            "completitud",
            "unicidad_general",
            "consistencia_texto",
            "outliers",
            "compatibilidad_semantica",
            "unicidad_clave",
            "reglas_negocio",
        ],
        "controles_no_aplicables": [],
        "controles_no_configurados": [],
    }