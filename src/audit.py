"""Coordinación de la auditoría de calidad de datos."""

from pathlib import Path
from typing import Any

import pandas as pd

from src.business_rules import evaluar_reglas_negocio
from src.candidate_keys import (
    CandidateKeyAnalysis,
    evaluar_claves_candidatas,
)
from src.column_analysis import (
    ColumnAnalysis,
    analizar_columnas,
)
from src.diagnostics import (
    Diagnostic,
    generar_diagnosticos,
)
from src.distributions import (
    FrequencyDistribution,
    NumericDistribution,
    crear_distribuciones,
)
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
from src.relationships import (
    RelationshipAnalysis,
    analizar_relaciones,
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


def _serializar_conversion(
    conversion: Any,
) -> dict[str, Any] | None:
    """
    Serializa las métricas de una posible conversión.

    La serie convertida no se incorpora al resultado público porque
    pertenece a la evidencia técnica interna y no es necesaria para
    representar los resultados de la auditoría.
    """
    if conversion is None:
        return None

    return {
        "valores_evaluados": conversion.attempted_count,
        "valores_convertibles": conversion.convertible_count,
        "valores_no_convertibles": conversion.failed_count,
        "porcentaje_exito": conversion.success_ratio,
    }


def _serializar_analisis_columna(
    analisis: ColumnAnalysis,
) -> dict[str, Any]:
    """Serializa el análisis técnico enriquecido de una columna."""
    return {
        "tipo_fisico": analisis.pandas_dtype,
        "filas_totales": analisis.total_rows,
        "nulos_reales": analisis.real_null_count,
        "nulos_textuales": analisis.textual_null_count,
        "nulos_totales": analisis.null_count,
        "porcentaje_nulos": analisis.null_ratio,
        "valores_analizables": analisis.analyzable_count,
        "porcentaje_analizable": analisis.analyzable_ratio,
        "valores_distintos": analisis.unique_count,
        "porcentaje_unicidad": analisis.unique_ratio,
        "valor_mas_frecuente": analisis.most_frequent_value,
        "frecuencia_valor_mas_frecuente": (
            analisis.most_frequent_count
        ),
        "porcentaje_valor_mas_frecuente": (
            analisis.most_frequent_ratio
        ),
        "valores_en_repeticion": analisis.repeated_value_count,
        "porcentaje_valores_en_repeticion": (
            analisis.repeated_value_ratio
        ),
        "duplicados_adicionales": (
            analisis.duplicate_excess_count
        ),
        "porcentaje_duplicados_adicionales": (
            analisis.duplicate_excess_ratio
        ),
        "conversion_numerica": _serializar_conversion(
            analisis.numeric_conversion
        ),
        "conversion_temporal": _serializar_conversion(
            analisis.datetime_conversion
        ),
    }


def _serializar_analisis_columnas(
    analisis_columnas: dict[object, ColumnAnalysis],
) -> dict:
    """Serializa el análisis técnico de todas las columnas."""
    return {
        columna: _serializar_analisis_columna(analisis)
        for columna, analisis in analisis_columnas.items()
    }


def _serializar_clave_candidata(
    analisis: CandidateKeyAnalysis,
) -> dict[str, Any]:
    """Serializa la evaluación de una clave candidata individual."""
    return {
        "nivel": analisis.level.value,
        "confianza": analisis.confidence.value,
        "evidencias": list(analisis.evidence),
    }


def _serializar_claves_candidatas(
    claves_candidatas: dict[object, CandidateKeyAnalysis],
) -> dict:
    """Serializa las claves candidatas individuales."""
    return {
        columna: _serializar_clave_candidata(analisis)
        for columna, analisis in claves_candidatas.items()
    }


def _serializar_distribucion(
    distribucion: FrequencyDistribution
    | NumericDistribution
    | None,
) -> dict[str, Any] | None:
    """Serializa una distribución de frecuencias o numérica."""
    if distribucion is None:
        return None

    if isinstance(distribucion, FrequencyDistribution):
        return {
            "tipo": "frecuencias",
            "total_valores": distribucion.total_values,
            "total_distintos": distribucion.total_distinct,
            "distintos_mostrados": distribucion.shown_distinct,
            "truncada": distribucion.truncated,
            "valores": [
                {
                    "valor": valor.value,
                    "frecuencia": valor.count,
                    "porcentaje": valor.ratio,
                }
                for valor in distribucion.values
            ],
        }

    if isinstance(distribucion, NumericDistribution):
        return {
            "tipo": "numerica",
            "total_valores": distribucion.total_values,
            "intervalos": [
                {
                    "limite_inferior": intervalo.lower,
                    "limite_superior": intervalo.upper,
                    "frecuencia": intervalo.count,
                    "porcentaje": intervalo.ratio,
                }
                for intervalo in distribucion.bins
            ],
        }

    return None


def _serializar_distribuciones(
    distribuciones: dict,
) -> dict:
    """Serializa las distribuciones calculadas por columna."""
    return {
        columna: _serializar_distribucion(distribucion)
        for columna, distribucion in distribuciones.items()
    }


def _serializar_diagnostico(
    diagnostico: Diagnostic,
) -> dict[str, Any]:
    """Serializa un diagnóstico contextual."""
    return {
        "tipo_incidencia": diagnostico.incident_type,
        "categoria": diagnostico.category,
        "severidad": diagnostico.severity,
        "columna": diagnostico.column_name,
        "mensaje_incidencia": diagnostico.incident_message,
        "contexto": list(diagnostico.context),
        "acciones_posibles": list(
            diagnostico.possible_actions
        ),
    }


def _serializar_diagnosticos(
    diagnosticos: list[Diagnostic],
) -> list[dict[str, Any]]:
    """Serializa todos los diagnósticos contextuales."""
    return [
        _serializar_diagnostico(diagnostico)
        for diagnostico in diagnosticos
    ]


def _serializar_relaciones(
    relaciones: RelationshipAnalysis,
) -> dict[str, Any]:
    """Serializa las relaciones detectadas entre columnas."""
    claves_compuestas = [
        {
            "columnas": list(relacion.columns),
            "nivel": relacion.level.value,
            "confianza": relacion.confidence.value,
            "filas_totales": relacion.total_rows,
            "filas_analizables": relacion.analyzable_rows,
            "filas_con_nulos": relacion.null_rows,
            "combinaciones_distintas": (
                relacion.unique_combinations
            ),
            "porcentaje_unicidad": (
                relacion.uniqueness_ratio
            ),
            "duplicados_adicionales": (
                relacion.duplicate_excess_count
            ),
            "evidencias": list(relacion.evidence),
        }
        for relacion in relaciones.composite_keys
    ]

    relaciones_funcionales = [
        {
            "columna_origen": relacion.source_column,
            "columna_destino": relacion.target_column,
            "filas_evaluables": relacion.evaluable_rows,
            "filas_consistentes": relacion.consistent_rows,
            "porcentaje_consistencia": (
                relacion.consistency_ratio
            ),
            "confianza": relacion.confidence.value,
            "evidencias": list(relacion.evidence),
        }
        for relacion in relaciones.functional_relationships
    ]

    relaciones_presencia = [
        {
            "columnas": list(relacion.columns),
            "patron": relacion.pattern.value,
            "filas_totales": relacion.total_rows,
            "ambas_presentes": relacion.both_present,
            "primera_presente_segunda_ausente": (
                relacion.first_present_second_absent
            ),
            "primera_ausente_segunda_presente": (
                relacion.first_absent_second_present
            ),
            "ambas_ausentes": relacion.both_absent,
            "porcentaje_consistencia": (
                relacion.consistency_ratio
            ),
            "confianza": relacion.confidence.value,
            "evidencias": list(relacion.evidence),
        }
        for relacion in relaciones.presence_relationships
    ]

    return {
        "claves_compuestas": claves_compuestas,
        "relaciones_funcionales": relaciones_funcionales,
        "relaciones_presencia": relaciones_presencia,
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

    resultado_incompatibilidades_tipo = (
        analizar_incompatibilidades_semanticas(
            analisis_columnas,
            inferencias,
        )
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
        "incompatibilidades_tipo": (
            resultado_incompatibilidades_tipo
        ),
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

    # ---------------------------------------------------------
    # V6.1 - Análisis avanzado
    # ---------------------------------------------------------

    claves_candidatas = evaluar_claves_candidatas(
        analisis_columnas
    )

    distribuciones = crear_distribuciones(
        analisis_columnas,
        inferencias,
    )

    diagnosticos = generar_diagnosticos(
        incidencias,
        analisis_columnas,
        inferencias,
        claves_candidatas,
        distribuciones,
    )

    relaciones = analizar_relaciones(
        datos,
        analisis_columnas,
        claves_candidatas,
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
        "analisis_avanzado": {
            "columnas": _serializar_analisis_columnas(
                analisis_columnas
            ),
            "claves_candidatas": (
                _serializar_claves_candidatas(
                    claves_candidatas
                )
            ),
            "distribuciones": _serializar_distribuciones(
                distribuciones
            ),
            "diagnosticos": _serializar_diagnosticos(
                diagnosticos
            ),
            "relaciones": _serializar_relaciones(
                relaciones
            ),
        },
    }