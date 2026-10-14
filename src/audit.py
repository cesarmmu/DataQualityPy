"""Coordinación de la auditoría de calidad de datos."""

from pathlib import Path
from typing import Any

import pandas as pd

from src.business_rules import evaluar_reglas_negocio
from src.column_analysis import analizar_columnas
from src.incidents import generar_incidencias
from src.inference import (
    SemanticInference,
    inferir_tipo_semantico,
)
from src.profiler import (
    perfilar_dataset,
    perfilar_numericas_semanticas,
)
from src.quality import (
    analizar_columnas_problematicas,
    analizar_duplicados,
    analizar_duplicados_clave,
    analizar_fechas,
    analizar_identificadores,
    analizar_nulos,
    analizar_nulos_textuales,
    analizar_texto,
)
from src.semantic_quality import (
    analizar_incompatibilidades_semanticas,
    analizar_outliers_semanticos,
)
from src.summary import generar_resumen_ejecutivo


def _inferir_tipos_semanticos(
    datos: pd.DataFrame,
    analisis_columnas: dict,
    configuracion: dict[str, Any],
) -> dict[object, SemanticInference]:
    """Infiere el tipo semántico de todas las columnas del dataset."""
    resultados = {}

    tipos_declarados = configuracion["tipos_columnas"]

    for columna, analisis in analisis_columnas.items():
        resultados[columna] = inferir_tipo_semantico(
            analisis,
            analisis.analyzable_series,
            tipo_declarado=tipos_declarados.get(columna),
            umbral_unicidad=configuracion[
                "umbral_identificador"
            ],
            umbral_fecha=configuracion["umbral_fecha"],
            max_categorias=configuracion["max_categorias"],
            max_porcentaje_categorias=configuracion[
                "max_porcentaje_categorias"
            ],
        )

    return resultados


def _serializar_tipos_semanticos(
    inferencias: dict[object, SemanticInference],
) -> dict:
    """Convierte las inferencias internas a una estructura serializable."""
    return {
        columna: {
            "tipo": inferencia.semantic_type.value,
            "confianza": inferencia.confidence.value,
            "fuente": inferencia.source,
            "evidencias": list(inferencia.evidence),
        }
        for columna, inferencia in inferencias.items()
    }


def auditar_dataset(
    datos: pd.DataFrame,
    nombre_archivo: str | Path,
    configuracion: dict[str, Any],
) -> dict:
    """Ejecuta la auditoría y devuelve un resultado estructurado."""
    analisis_columnas = analizar_columnas(datos)

    inferencias = _inferir_tipos_semanticos(
        datos,
        analisis_columnas,
        configuracion,
    )

    tipos_semanticos = _serializar_tipos_semanticos(
        inferencias
    )

    perfil = perfilar_dataset(datos)

    perfil_numerico = perfilar_numericas_semanticas(
        analisis_columnas,
        inferencias,
    )

    resultado_nulos = analizar_nulos(datos)
    resultado_nulos_textuales = analizar_nulos_textuales(datos)

    resultado_identificadores = analizar_identificadores(
        datos,
        umbral_unicidad=configuracion[
            "umbral_identificador"
        ],
    )

    resultado_duplicados = analizar_duplicados(datos)

    resultado_duplicados_clave = analizar_duplicados_clave(
        datos,
        columnas_clave=configuracion["columnas_clave"],
    )

    resultado_columnas = analizar_columnas_problematicas(
        datos
    )

    resultado_texto = analizar_texto(
        datos,
        max_categorias=configuracion["max_categorias"],
        max_porcentaje_categorias=(
            configuracion["max_porcentaje_categorias"]
        ),
    )

    resultado_outliers = analizar_outliers_semanticos(
        analisis_columnas,
        inferencias,
        factor_iqr=configuracion["factor_iqr"],
    )

    resultado_incompatibilidades_tipo = analizar_incompatibilidades_semanticas(
        analisis_columnas,
        inferencias,
    )

    resultado_reglas_negocio = evaluar_reglas_negocio(
        analisis_columnas,
        inferencias,
        configuracion["reglas_columnas"],
    )

    resultado_fechas = analizar_fechas(
        datos,
        umbral_fecha=configuracion["umbral_fecha"],
    )

    calidad = {
        "nulos": resultado_nulos,
        "nulos_textuales": resultado_nulos_textuales,
        "identificadores": resultado_identificadores,
        "duplicados": resultado_duplicados,
        "duplicados_clave": resultado_duplicados_clave,
        "columnas_problematicas": resultado_columnas,
        "texto": resultado_texto,
        "outliers": resultado_outliers,
        "incompatibilidades_tipo": resultado_incompatibilidades_tipo,
        "reglas_negocio": resultado_reglas_negocio,
        "fechas": resultado_fechas,
    }

    incidencias = generar_incidencias(
        calidad,
        total_filas=perfil["filas"],
    )

    resumen = generar_resumen_ejecutivo(
        incidencias,
        tipos_semanticos,
        calidad,
        configuracion,
    )

    return {
        "dataset": {
            "archivo": Path(nombre_archivo).name,
            "filas": perfil["filas"],
            "columnas": perfil["columnas"],
            "memoria_bytes": perfil["memoria_bytes"],
        },
        "perfil": {
            "nombres_columnas": perfil["nombres_columnas"],
            "tipos_datos": perfil["tipos_datos"],
            "valores_distintos": perfil["valores_distintos"],
            "estadisticas_numericas": perfil_numerico,
        },
        "tipos_semanticos": tipos_semanticos,
        "calidad": calidad,
        "incidencias": incidencias,
        "resumen": resumen,
    }