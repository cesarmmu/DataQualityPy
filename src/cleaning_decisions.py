"""Conversión de recomendaciones en decisiones de limpieza de DataQualityPy V6.

Este módulo conecta las recomendaciones de limpieza con las operaciones
validadas por CleaningPlan.

Responsabilidades:
- comprobar que una recomendación puede convertirse en una operación;
- incorporar las decisiones explícitas del usuario;
- construir una CleaningOperation validada;
- añadirla al plan únicamente mediante una acción explícita.

Este módulo:
- no modifica DataFrames;
- no ejecuta transformaciones;
- no decide automáticamente por el usuario;
- no duplica las validaciones propias de CleaningOperation.
"""

from __future__ import annotations

from typing import Any

from src.cleaning_plan import (
    CleaningOperation,
    CleaningPlan,
)
from src.cleaning_recommendations import (
    CleaningActionType,
    CleaningRecommendation,
)


class CleaningDecisionError(ValueError):
    """Error al convertir una recomendación en una decisión de limpieza."""


def _validar_recomendacion_limpiable(
    recomendacion: CleaningRecommendation,
) -> None:
    """Comprueba que la recomendación representa una posible limpieza."""
    if not isinstance(recomendacion, CleaningRecommendation):
        raise CleaningDecisionError(
            "'recomendacion' debe ser una instancia de "
            "CleaningRecommendation."
        )

    if recomendacion.action_type is not CleaningActionType.CLEAN:
        raise CleaningDecisionError(
            "Solo las recomendaciones de tipo 'limpiar' pueden "
            "convertirse en operaciones de limpieza."
        )

    if recomendacion.family is None:
        raise CleaningDecisionError(
            "La recomendación no define una familia de limpieza."
        )


def _resolver_familia(
    recomendacion: CleaningRecommendation,
) -> str:
    """Devuelve la familia después de comprobar que está definida."""
    familia = recomendacion.family

    if familia is None:
        raise CleaningDecisionError(
            "La recomendación no define una familia de limpieza."
        )

    return familia


def _resolver_tipo_operacion(
    recomendacion: CleaningRecommendation,
    operation_type: str | None,
) -> str:
    """Resuelve la operación final respetando la decisión del usuario."""
    tipo_recomendado = recomendacion.operation_type

    if operation_type is None:
        if tipo_recomendado is None:
            raise CleaningDecisionError(
                "La recomendación requiere seleccionar una operación "
                "de limpieza."
            )
        return tipo_recomendado

    if not isinstance(operation_type, str) or not operation_type.strip():
        raise CleaningDecisionError(
            "'operation_type' debe ser una cadena de texto no vacía."
        )

    tipo_usuario = operation_type.strip()

    if (
        tipo_recomendado is not None
        and tipo_usuario != tipo_recomendado
        and not recomendacion.requires_user_input
    ):
        raise CleaningDecisionError(
            "La operación propuesta por esta recomendación está "
            "completamente definida y no puede sustituirse por otra."
        )

    return tipo_usuario


def _resolver_parametros(
    recomendacion: CleaningRecommendation,
    parameters: dict[str, Any] | None,
) -> dict[str, Any]:
    """Combina parámetros propuestos y decisiones explícitas del usuario."""
    if parameters is not None and not isinstance(parameters, dict):
        raise CleaningDecisionError(
            "'parameters' debe ser un diccionario."
        )

    parametros = dict(recomendacion.parameters)

    if parameters is not None:
        parametros.update(parameters)

    return parametros


def crear_operacion_desde_recomendacion(
    recomendacion: CleaningRecommendation,
    *,
    operation_type: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> CleaningOperation:
    """Convierte una recomendación aceptada en una operación validada.

    La función no añade la operación a ningún plan.

    Las validaciones específicas de familia, tipo, columna y parámetros
    siguen siendo responsabilidad de CleaningOperation.
    """
    _validar_recomendacion_limpiable(recomendacion)

    familia = _resolver_familia(recomendacion)
    tipo = _resolver_tipo_operacion(
        recomendacion,
        operation_type,
    )
    parametros = _resolver_parametros(
        recomendacion,
        parameters,
    )

    return CleaningOperation(
        familia=familia,
        tipo=tipo,
        columna=(
            None
            if recomendacion.column_name is None
            else str(recomendacion.column_name)
        ),
        parametros=parametros,
    )


def agregar_recomendacion_al_plan(
    plan: CleaningPlan,
    recomendacion: CleaningRecommendation,
    *,
    operation_type: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> CleaningOperation:
    """Convierte una recomendación y añade la operación al plan.

    El plan solo se modifica después de que la operación haya sido
    construida y validada correctamente.
    """
    if not isinstance(plan, CleaningPlan):
        raise CleaningDecisionError(
            "'plan' debe ser una instancia de CleaningPlan."
        )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        operation_type=operation_type,
        parameters=parameters,
    )

    return plan.agregar_operacion(operacion)