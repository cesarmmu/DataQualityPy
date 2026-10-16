"""Recomendaciones de limpieza de DataQualityPy V6.

Este módulo traduce los diagnósticos de auditoría en recomendaciones
estructuradas de limpieza.

Las recomendaciones son deterministas e informativas:
- no modifican el dataset;
- no modifican el plan de limpieza;
- no crean operaciones automáticamente;
- no ejecutan transformaciones;
- no sustituyen la decisión del usuario.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from src.diagnostics import Diagnostic


class CleaningActionType(Enum):
    """Naturaleza general de una recomendación de limpieza."""

    REVIEW = "revisar"
    KEEP = "mantener"
    CLEAN = "limpiar"


@dataclass(frozen=True)
class CleaningRecommendation:
    """Recomendación estructurada derivada de un diagnóstico."""

    incident_type: str
    column_name: object | None
    title: str
    explanation: str
    action_type: CleaningActionType
    family: str | None = None
    operation_type: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_user_input: bool = False

    @property
    def executable(self) -> bool:
        """Indica si existe una operación de limpieza asociada."""
        return (
            self.family is not None
            and self.operation_type is not None
        )


def _recomendacion(
    diagnostico: Diagnostic,
    *,
    title: str,
    explanation: str,
    action_type: CleaningActionType,
    family: str | None = None,
    operation_type: str | None = None,
    parameters: dict[str, Any] | None = None,
    requires_user_input: bool = False,
) -> CleaningRecommendation:
    """Construye una recomendación conservando el origen diagnóstico."""
    return CleaningRecommendation(
        incident_type=diagnostico.incident_type,
        column_name=diagnostico.column_name,
        title=title,
        explanation=explanation,
        action_type=action_type,
        family=family,
        operation_type=operation_type,
        parameters={} if parameters is None else dict(parameters),
        requires_user_input=requires_user_input,
    )


def _mantener(
    diagnostico: Diagnostic,
    explanation: str,
) -> CleaningRecommendation:
    """Construye una recomendación explícita de conservación."""
    return _recomendacion(
        diagnostico,
        title="Mantener sin cambios",
        explanation=explanation,
        action_type=CleaningActionType.KEEP,
    )


def _revisar(
    diagnostico: Diagnostic,
    *,
    title: str,
    explanation: str,
) -> CleaningRecommendation:
    """Construye una recomendación de revisión sin operación automática."""
    return _recomendacion(
        diagnostico,
        title=title,
        explanation=explanation,
        action_type=CleaningActionType.REVIEW,
    )


def _recomendaciones_nulos_reales(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para valores nulos reales."""
    return (
        _mantener(
            diagnostico,
            "Conservar los valores nulos cuando sean válidos "
            "para el significado de la columna.",
        ),
        _recomendacion(
            diagnostico,
            title="Eliminar filas con valores nulos",
            explanation=(
                "Eliminar los registros afectados cuando su pérdida "
                "sea aceptable para el análisis."
            ),
            action_type=CleaningActionType.CLEAN,
            family="nulos",
            operation_type="eliminar_filas",
        ),
        _recomendacion(
            diagnostico,
            title="Reemplazar por un valor",
            explanation=(
                "Sustituir los valores nulos por un valor indicado "
                "explícitamente por el usuario."
            ),
            action_type=CleaningActionType.CLEAN,
            family="nulos",
            operation_type="reemplazar_valor",
            requires_user_input=True,
        ),
        _recomendacion(
            diagnostico,
            title="Rellenar con la media",
            explanation=(
                "Usar la media cuando la columna pueda tratarse "
                "numéricamente y esta decisión sea adecuada."
            ),
            action_type=CleaningActionType.CLEAN,
            family="nulos",
            operation_type="media",
        ),
        _recomendacion(
            diagnostico,
            title="Rellenar con la mediana",
            explanation=(
                "Usar la mediana cuando la columna pueda tratarse "
                "numéricamente y esta decisión sea adecuada."
            ),
            action_type=CleaningActionType.CLEAN,
            family="nulos",
            operation_type="mediana",
        ),
        _recomendacion(
            diagnostico,
            title="Rellenar con la moda",
            explanation=(
                "Usar el valor más frecuente cuando resulte apropiado "
                "para la columna."
            ),
            action_type=CleaningActionType.CLEAN,
            family="nulos",
            operation_type="moda",
        ),
    )


def _recomendaciones_nulos_textuales(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para marcadores textuales de nulo."""
    return (
        _mantener(
            diagnostico,
            "Conservar los marcadores textuales si representan "
            "información válida y no valores ausentes.",
        ),
        _recomendacion(
            diagnostico,
            title="Convertir marcador a nulo real",
            explanation=(
                "Seleccionar explícitamente qué marcador textual debe "
                "interpretarse como un valor nulo real."
            ),
            action_type=CleaningActionType.CLEAN,
            family="sustitucion",
            operation_type="reemplazar_por_nulo",
            requires_user_input=True,
        ),
    )


def _recomendaciones_filas_duplicadas(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para filas completamente duplicadas."""
    return (
        _mantener(
            diagnostico,
            "Conservar las filas duplicadas si las repeticiones son "
            "válidas dentro del contexto del dataset.",
        ),
        _recomendacion(
            diagnostico,
            title="Eliminar duplicados completos",
            explanation=(
                "Eliminar las repeticiones completas conservando "
                "la primera aparición."
            ),
            action_type=CleaningActionType.CLEAN,
            family="duplicados",
            operation_type="eliminar_duplicados_completos",
            parameters={"conservar": "primero"},
        ),
    )


def _recomendaciones_clave_inexistente(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones cuando una clave configurada no existe."""
    return (
        _revisar(
            diagnostico,
            title="Revisar la configuración de la clave",
            explanation=(
                "Comprobar que las columnas configuradas como clave "
                "existen realmente en el dataset."
            ),
        ),
    )


def _recomendaciones_duplicados_clave(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para duplicados según una clave configurada."""
    return (
        _mantener(
            diagnostico,
            "Conservar los registros si la repetición de la clave "
            "es válida para el modelo de datos.",
        ),
        _revisar(
            diagnostico,
            title="Revisar registros con clave duplicada",
            explanation=(
                "Examinar los registros afectados antes de decidir "
                "si representan duplicados reales o repeticiones válidas."
            ),
        ),
    )


def _recomendaciones_columna_vacia(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para columnas completamente vacías."""
    return (
        _mantener(
            diagnostico,
            "Conservar la columna si forma parte de una estructura "
            "que deba mantenerse.",
        ),
        _revisar(
            diagnostico,
            title="Revisar posible eliminación de la columna",
            explanation=(
                "Una columna completamente vacía puede ser prescindible, "
                "pero debe confirmarse su función antes de eliminarla."
            ),
        ),
    )


def _recomendaciones_columna_constante(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para columnas con un único valor."""
    return (
        _mantener(
            diagnostico,
            "Conservar la columna si el valor constante aporta contexto "
            "o tiene significado estructural.",
        ),
        _revisar(
            diagnostico,
            title="Revisar posible eliminación de la columna",
            explanation=(
                "Una columna constante puede aportar poca información "
                "analítica, pero no debe eliminarse sin revisar su función."
            ),
        ),
    )


def _recomendaciones_espacios_texto(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para problemas de espacios en texto."""
    return (
        _mantener(
            diagnostico,
            "Conservar los espacios si forman parte deliberada "
            "del contenido textual.",
        ),
        _recomendacion(
            diagnostico,
            title="Eliminar espacios externos",
            explanation=(
                "Eliminar espacios situados al principio o al final "
                "de los valores de texto."
            ),
            action_type=CleaningActionType.CLEAN,
            family="texto",
            operation_type="eliminar_espacios_externos",
        ),
        _recomendacion(
            diagnostico,
            title="Normalizar espacios internos",
            explanation=(
                "Reducir secuencias de espacios internos cuando "
                "representen inconsistencias de formato."
            ),
            action_type=CleaningActionType.CLEAN,
            family="texto",
            operation_type="normalizar_espacios_internos",
        ),
    )


def _recomendaciones_inconsistencia_categorica(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para posibles inconsistencias categóricas."""
    return (
        _mantener(
            diagnostico,
            "Conservar las categorías si sus diferencias representan "
            "valores conceptualmente distintos.",
        ),
        _revisar(
            diagnostico,
            title="Revisar categorías similares",
            explanation=(
                "Comprobar si las variantes detectadas representan "
                "la misma categoría antes de unificarlas."
            ),
        ),
        _recomendacion(
            diagnostico,
            title="Sustituir una categoría por otra",
            explanation=(
                "Definir explícitamente el valor de origen y el valor "
                "de destino para unificar una categoría."
            ),
            action_type=CleaningActionType.CLEAN,
            family="sustitucion",
            operation_type="reemplazar_valor",
            requires_user_input=True,
        ),
        _recomendacion(
            diagnostico,
            title="Normalizar formato de texto",
            explanation=(
                "Aplicar una normalización de mayúsculas o minúsculas "
                "cuando las diferencias sean únicamente de formato."
            ),
            action_type=CleaningActionType.CLEAN,
            family="texto",
            operation_type="minusculas",
            requires_user_input=True,
        ),
    )


def _recomendaciones_outliers(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para valores atípicos detectados por IQR."""
    return (
        _mantener(
            diagnostico,
            "Conservar los valores atípicos cuando sean observaciones "
            "válidas y relevantes para el análisis.",
        ),
        _revisar(
            diagnostico,
            title="Revisar los valores atípicos",
            explanation=(
                "Examinar los registros afectados antes de decidir "
                "si representan errores o valores extremos válidos."
            ),
        ),
        _recomendacion(
            diagnostico,
            title="Eliminar filas con outliers",
            explanation=(
                "Eliminar las filas identificadas mediante el criterio IQR "
                "solo cuando se haya confirmado que no deben conservarse."
            ),
            action_type=CleaningActionType.CLEAN,
            family="outliers",
            operation_type="eliminar_filas",
        ),
    )


def _recomendaciones_incompatibilidad_tipo(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para valores incompatibles con el tipo esperado."""
    return (
        _mantener(
            diagnostico,
            "Conservar los valores si la incompatibilidad refleja "
            "una característica legítima de la columna.",
        ),
        _revisar(
            diagnostico,
            title="Revisar valores incompatibles",
            explanation=(
                "Examinar los valores que no son compatibles con el "
                "tipo esperado antes de realizar una conversión."
            ),
        ),
        _recomendacion(
            diagnostico,
            title="Corregir valores mediante sustitución",
            explanation=(
                "Sustituir explícitamente valores incompatibles cuando "
                "se conozca su representación correcta."
            ),
            action_type=CleaningActionType.CLEAN,
            family="sustitucion",
            operation_type="reemplazar_valor",
            requires_user_input=True,
        ),
        _recomendacion(
            diagnostico,
            title="Convertir al tipo adecuado",
            explanation=(
                "Seleccionar explícitamente el tipo de destino y decidir "
                "cómo tratar los valores que no puedan convertirse."
            ),
            action_type=CleaningActionType.CLEAN,
            family="conversion",
            operation_type=None,
            requires_user_input=True,
        ),
    )


def _recomendaciones_incumplimiento_regla(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para incumplimientos de reglas de negocio."""
    return (
        _mantener(
            diagnostico,
            "Conservar el valor únicamente si se confirma que la regla "
            "de negocio no es aplicable en ese caso.",
        ),
        _revisar(
            diagnostico,
            title="Revisar incumplimiento de regla",
            explanation=(
                "Comprobar el registro y la regla de negocio antes de "
                "decidir cualquier corrección."
            ),
        ),
        _revisar(
            diagnostico,
            title="Corregir según la regla de negocio",
            explanation=(
                "La corrección depende de la regla concreta y no dispone "
                "de una operación genérica segura."
            ),
        ),
    )


def _recomendaciones_conversion_fecha(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Recomendaciones para problemas de conversión de fechas."""
    return (
        _mantener(
            diagnostico,
            "Conservar los valores originales si no deben interpretarse "
            "como fechas.",
        ),
        _revisar(
            diagnostico,
            title="Revisar formato de fecha",
            explanation=(
                "Comprobar el formato real de los valores y las posibles "
                "ambigüedades antes de convertirlos."
            ),
        ),
        _recomendacion(
            diagnostico,
            title="Convertir a fecha",
            explanation=(
                "Convertir la columna a fecha utilizando, cuando se conozca, "
                "un formato explícito."
            ),
            action_type=CleaningActionType.CLEAN,
            family="conversion",
            operation_type="fecha",
            requires_user_input=True,
        ),
        _recomendacion(
            diagnostico,
            title="Convertir a fecha y hora",
            explanation=(
                "Convertir la columna a fecha y hora cuando los valores "
                "contengan también información temporal."
            ),
            action_type=CleaningActionType.CLEAN,
            family="conversion",
            operation_type="fecha_hora",
            requires_user_input=True,
        ),
    )


_RECOMMENDATION_BUILDERS = {
    "nulos_reales": _recomendaciones_nulos_reales,
    "nulos_textuales": _recomendaciones_nulos_textuales,
    "filas_duplicadas": _recomendaciones_filas_duplicadas,
    "clave_inexistente": _recomendaciones_clave_inexistente,
    "duplicados_clave": _recomendaciones_duplicados_clave,
    "columna_vacia": _recomendaciones_columna_vacia,
    "columna_constante": _recomendaciones_columna_constante,
    "espacios_texto": _recomendaciones_espacios_texto,
    "inconsistencia_categorica": _recomendaciones_inconsistencia_categorica,
    "outliers": _recomendaciones_outliers,
    "incompatibilidad_tipo": _recomendaciones_incompatibilidad_tipo,
    "incumplimiento_regla": _recomendaciones_incumplimiento_regla,
    "conversion_fecha": _recomendaciones_conversion_fecha,
}


def generar_recomendaciones_limpieza(
    diagnostico: Diagnostic,
) -> tuple[CleaningRecommendation, ...]:
    """Genera recomendaciones para un diagnóstico.

    Si aparece en el futuro un tipo de incidencia que todavía no dispone
    de reglas específicas, se devuelve una recomendación segura de revisión
    en lugar de inventar una transformación.
    """
    constructor = _RECOMMENDATION_BUILDERS.get(
        diagnostico.incident_type
    )

    if constructor is not None:
        return constructor(diagnostico)

    return (
        _revisar(
            diagnostico,
            title="Revisar la incidencia",
            explanation=(
                "Este tipo de incidencia no dispone todavía de una "
                "recomendación específica de limpieza. Debe revisarse "
                "antes de realizar cualquier transformación."
            ),
        ),
    )


def generar_recomendaciones_limpieza_dataset(
    diagnosticos: Iterable[Diagnostic],
) -> tuple[CleaningRecommendation, ...]:
    """Genera recomendaciones para todos los diagnósticos de un dataset."""
    recomendaciones: list[CleaningRecommendation] = []

    for diagnostico in diagnosticos:
        recomendaciones.extend(
            generar_recomendaciones_limpieza(diagnostico)
        )

    return tuple(recomendaciones)