"""Tests de decisiones de limpieza de DataQualityPy V6.2.2."""

import pytest

from src.cleaning_decisions import (
    CleaningDecisionError,
    agregar_recomendacion_al_plan,
    crear_operacion_desde_recomendacion,
)
from src.cleaning_plan import (
    CleaningOperation,
    CleaningPlan,
    CleaningPlanError,
)
from src.cleaning_recommendations import (
    CleaningActionType,
    CleaningRecommendation,
)


def _recomendacion(
    *,
    action_type: CleaningActionType = CleaningActionType.CLEAN,
    family: str | None = "texto",
    operation_type: str | None = "minusculas",
    column_name: object | None = "nombre",
    parameters: dict | None = None,
    requires_user_input: bool = False,
) -> CleaningRecommendation:
    """Construye una recomendación configurable para los tests."""
    return CleaningRecommendation(
        incident_type="incidencia_prueba",
        column_name=column_name,
        title="Recomendación de prueba",
        explanation="Explicación de prueba",
        action_type=action_type,
        family=family,
        operation_type=operation_type,
        parameters={} if parameters is None else parameters,
        requires_user_input=requires_user_input,
    )


def test_crea_operacion_desde_recomendacion_completa_v6() -> None:
    """Una recomendación completa genera una CleaningOperation válida."""
    recomendacion = _recomendacion()

    operacion = crear_operacion_desde_recomendacion(recomendacion)

    assert isinstance(operacion, CleaningOperation)
    assert operacion.familia == "texto"
    assert operacion.tipo == "minusculas"
    assert operacion.columna == "nombre"
    assert operacion.parametros == {}


def test_crear_operacion_no_modifica_ningun_plan_v6() -> None:
    """Crear una operación aislada no incorpora nada a un plan."""
    plan = CleaningPlan()
    recomendacion = _recomendacion()

    operacion = crear_operacion_desde_recomendacion(recomendacion)

    assert isinstance(operacion, CleaningOperation)
    assert plan.esta_vacio()
    assert len(plan) == 0


def test_recomendacion_keep_no_puede_convertirse_v6() -> None:
    """Una decisión de mantener nunca genera una operación."""
    recomendacion = _recomendacion(
        action_type=CleaningActionType.KEEP,
        family=None,
        operation_type=None,
    )

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(recomendacion)


def test_recomendacion_review_no_puede_convertirse_v6() -> None:
    """Una recomendación de revisión nunca genera una operación."""
    recomendacion = _recomendacion(
        action_type=CleaningActionType.REVIEW,
        family=None,
        operation_type=None,
    )

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(recomendacion)


def test_recomendacion_clean_sin_familia_es_invalida_v6() -> None:
    """Una limpieza sin familia no puede materializarse."""
    recomendacion = _recomendacion(
        family=None,
        operation_type=None,
        requires_user_input=True,
    )

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(recomendacion)


def test_operacion_pendiente_debe_ser_seleccionada_v6() -> None:
    """Una recomendación sin tipo exige que el usuario seleccione uno."""
    recomendacion = _recomendacion(
        family="conversion",
        operation_type=None,
        requires_user_input=True,
    )

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(recomendacion)


def test_usuario_selecciona_tipo_conversion_v6() -> None:
    """El usuario puede completar explícitamente una conversión pendiente."""
    recomendacion = _recomendacion(
        family="conversion",
        operation_type=None,
        column_name="importe",
        requires_user_input=True,
    )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        operation_type="numerico",
    )

    assert operacion.familia == "conversion"
    assert operacion.tipo == "numerico"
    assert operacion.columna == "importe"


def test_usuario_puede_cambiar_operacion_si_requiere_decision_v6() -> None:
    """Una recomendación abierta permite seleccionar otra operación válida."""
    recomendacion = _recomendacion(
        family="texto",
        operation_type="minusculas",
        requires_user_input=True,
    )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        operation_type="titulo",
    )

    assert operacion.tipo == "titulo"


def test_usuario_no_puede_cambiar_operacion_cerrada_v6() -> None:
    """Una recomendación completa no puede sustituirse arbitrariamente."""
    recomendacion = _recomendacion(
        family="texto",
        operation_type="minusculas",
        requires_user_input=False,
    )

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(
            recomendacion,
            operation_type="mayusculas",
        )


def test_mismo_tipo_es_valido_en_recomendacion_cerrada_v6() -> None:
    """Repetir explícitamente el tipo ya propuesto no altera la decisión."""
    recomendacion = _recomendacion(
        operation_type="minusculas",
        requires_user_input=False,
    )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        operation_type="minusculas",
    )

    assert operacion.tipo == "minusculas"


def test_parametros_recomendados_se_conservan_v6() -> None:
    """Los parámetros incluidos en la recomendación llegan a la operación."""
    recomendacion = _recomendacion(
        family="duplicados",
        operation_type="eliminar_duplicados_completos",
        column_name=None,
        parameters={"conservar": "primero"},
    )

    operacion = crear_operacion_desde_recomendacion(recomendacion)

    assert operacion.parametros == {"conservar": "primero"}


def test_parametros_usuario_completan_recomendacion_v6() -> None:
    """Los parámetros explícitos del usuario completan la recomendación."""
    recomendacion = _recomendacion(
        family="nulos",
        operation_type="reemplazar_valor",
        column_name="edad",
        requires_user_input=True,
    )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        parameters={"valor": 0},
    )

    assert operacion.familia == "nulos"
    assert operacion.tipo == "reemplazar_valor"
    assert operacion.parametros == {"valor": 0}


def test_parametros_usuario_complementan_parametros_propuestos_v6() -> None:
    """Los parámetros del usuario se combinan con los ya recomendados."""
    recomendacion = _recomendacion(
        family="sustitucion",
        operation_type="reemplazar_valor",
        parameters={"origen": "MADRID"},
        requires_user_input=True,
    )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        parameters={"destino": "Madrid"},
    )

    assert operacion.parametros == {
        "origen": "MADRID",
        "destino": "Madrid",
    }


def test_parametros_usuario_prevalecen_sobre_propuestos_v6() -> None:
    """Una decisión explícita puede completar o ajustar parámetros abiertos."""
    recomendacion = _recomendacion(
        family="conversion",
        operation_type="fecha",
        column_name="fecha_alta",
        parameters={"formato": "%d/%m/%Y"},
        requires_user_input=True,
    )

    operacion = crear_operacion_desde_recomendacion(
        recomendacion,
        parameters={"formato": "%Y-%m-%d"},
    )

    assert operacion.parametros["formato"] == "%Y-%m-%d"


def test_parametros_no_diccionario_generan_error_decision_v6() -> None:
    """La capa de decisión rechaza parámetros con estructura incorrecta."""
    recomendacion = _recomendacion()

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(
            recomendacion,
            parameters="incorrecto",  # type: ignore[arg-type]
        )


def test_tipo_operacion_vacio_genera_error_decision_v6() -> None:
    """Una selección de operación vacía no es una decisión válida."""
    recomendacion = _recomendacion(
        family="conversion",
        operation_type=None,
        requires_user_input=True,
    )

    with pytest.raises(CleaningDecisionError):
        crear_operacion_desde_recomendacion(
            recomendacion,
            operation_type="   ",
        )


def test_cleaning_operation_valida_tipo_real_del_plan_v6() -> None:
    """Las operaciones inexistentes siguen siendo rechazadas por el plan."""
    recomendacion = _recomendacion(
        family="conversion",
        operation_type=None,
        requires_user_input=True,
    )

    with pytest.raises(CleaningPlanError):
        crear_operacion_desde_recomendacion(
            recomendacion,
            operation_type="tipo_inexistente",
        )


def test_cleaning_operation_valida_parametros_obligatorios_v6() -> None:
    """La validación de parámetros obligatorios permanece en CleaningOperation."""
    recomendacion = _recomendacion(
        family="nulos",
        operation_type="reemplazar_valor",
        column_name="edad",
        requires_user_input=True,
    )

    with pytest.raises(CleaningPlanError):
        crear_operacion_desde_recomendacion(recomendacion)


def test_columna_no_textual_se_convierte_a_texto_v6() -> None:
    """Una etiqueta de columna válida de pandas se materializa como texto."""
    recomendacion = _recomendacion(
        column_name=123,
    )

    operacion = crear_operacion_desde_recomendacion(recomendacion)

    assert operacion.columna == "123"


def test_agregar_recomendacion_incorpora_operacion_al_plan_v6() -> None:
    """La acción explícita de agregar incorpora la operación validada."""
    plan = CleaningPlan()
    recomendacion = _recomendacion()

    operacion = agregar_recomendacion_al_plan(
        plan,
        recomendacion,
    )

    assert len(plan) == 1
    assert plan.obtener_operacion(operacion.id) is operacion


def test_agregar_conversion_completada_al_plan_v6() -> None:
    """Una decisión pendiente puede completarse y añadirse al plan."""
    plan = CleaningPlan()
    recomendacion = _recomendacion(
        family="conversion",
        operation_type=None,
        column_name="importe",
        requires_user_input=True,
    )

    operacion = agregar_recomendacion_al_plan(
        plan,
        recomendacion,
        operation_type="numerico",
    )

    assert len(plan) == 1
    assert operacion.familia == "conversion"
    assert operacion.tipo == "numerico"


def test_error_de_decision_no_modifica_plan_v6() -> None:
    """Una decisión incompleta no deja operaciones parciales en el plan."""
    plan = CleaningPlan()
    recomendacion = _recomendacion(
        family="conversion",
        operation_type=None,
        requires_user_input=True,
    )

    with pytest.raises(CleaningDecisionError):
        agregar_recomendacion_al_plan(
            plan,
            recomendacion,
        )

    assert plan.esta_vacio()
    assert len(plan) == 0


def test_error_de_validacion_no_modifica_plan_v6() -> None:
    """Una operación rechazada por CleaningOperation no altera el plan."""
    plan = CleaningPlan()
    recomendacion = _recomendacion(
        family="nulos",
        operation_type="reemplazar_valor",
        column_name="edad",
        requires_user_input=True,
    )

    with pytest.raises(CleaningPlanError):
        agregar_recomendacion_al_plan(
            plan,
            recomendacion,
        )

    assert plan.esta_vacio()
    assert len(plan) == 0


def test_plan_invalido_genera_error_decision_v6() -> None:
    """La API de agregado exige una instancia real de CleaningPlan."""
    recomendacion = _recomendacion()

    with pytest.raises(CleaningDecisionError):
        agregar_recomendacion_al_plan(
            None,  # type: ignore[arg-type]
            recomendacion,
        )