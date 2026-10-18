"""Tests de recomendaciones de limpieza de DataQualityPy V6.2.1."""

from src.cleaning_recommendations import (
    CleaningActionType,
    CleaningRecommendation,
    generar_recomendaciones_limpieza,
    generar_recomendaciones_limpieza_dataset,
)
from src.diagnostics import Diagnostic


def _diagnostico(
    tipo: str,
    columna: object | None = "columna_prueba",
) -> Diagnostic:
    """Construye un diagnóstico mínimo válido para los tests."""
    return Diagnostic(
        incident_type=tipo,
        category="categoria_prueba",
        severity="media",
        column_name=columna,
        incident_message="Incidencia de prueba",
        context=("Contexto de prueba",),
        possible_actions=("Acción de prueba",),
    )


def test_recomendacion_ejecutable_requiere_familia_y_operacion_v6() -> None:
    """Una recomendación solo es ejecutable si define familia y operación."""
    ejecutable = CleaningRecommendation(
        incident_type="prueba",
        column_name="columna",
        title="Ejecutable",
        explanation="Prueba",
        action_type=CleaningActionType.CLEAN,
        family="texto",
        operation_type="minusculas",
    )

    incompleta = CleaningRecommendation(
        incident_type="prueba",
        column_name="columna",
        title="Incompleta",
        explanation="Prueba",
        action_type=CleaningActionType.CLEAN,
        family="conversion",
        operation_type=None,
    )

    assert ejecutable.executable is True
    assert incompleta.executable is False


def test_nulos_reales_ofrecen_alternativas_controladas_v6() -> None:
    """Los nulos reales ofrecen conservación y tratamientos soportados."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("nulos_reales")
    )

    operaciones = {
        recomendacion.operation_type
        for recomendacion in recomendaciones
        if recomendacion.executable
    }

    assert len(recomendaciones) == 6
    assert recomendaciones[0].action_type is CleaningActionType.KEEP
    assert {
        "eliminar_filas",
        "reemplazar_valor",
        "media",
        "mediana",
        "moda",
    }.issubset(operaciones)


def test_reemplazo_manual_de_nulos_requiere_usuario_v6() -> None:
    """El valor usado para reemplazar nulos nunca se decide automáticamente."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("nulos_reales")
    )

    reemplazo = next(
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.operation_type == "reemplazar_valor"
    )

    assert reemplazo.family == "nulos"
    assert reemplazo.requires_user_input is True
    assert reemplazo.executable is True


def test_nulos_textuales_requieren_seleccion_explicita_v6() -> None:
    """La conversión de marcadores textuales necesita decisión del usuario."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("nulos_textuales")
    )

    conversion = next(
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.action_type is CleaningActionType.CLEAN
    )

    assert conversion.family == "sustitucion"
    assert conversion.operation_type == "reemplazar_por_nulo"
    assert conversion.requires_user_input is True
    assert conversion.executable is True


def test_duplicados_completos_tienen_operacion_segura_v6() -> None:
    """Los duplicados completos pueden eliminarse conservando el primero."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("filas_duplicadas", None)
    )

    eliminar = next(
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.action_type is CleaningActionType.CLEAN
    )

    assert eliminar.family == "duplicados"
    assert eliminar.operation_type == "eliminar_duplicados_completos"
    assert eliminar.parameters == {"conservar": "primero"}
    assert eliminar.requires_user_input is False
    assert eliminar.executable is True


def test_clave_inexistente_solo_recomienda_revision_v6() -> None:
    """Una clave inexistente no genera transformaciones del dataset."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("clave_inexistente", None)
    )

    assert len(recomendaciones) == 1
    assert recomendaciones[0].action_type is CleaningActionType.REVIEW
    assert recomendaciones[0].executable is False


def test_duplicados_clave_no_generan_eliminacion_automatica_v6() -> None:
    """Los duplicados por clave permanecen como decisión de revisión."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("duplicados_clave")
    )

    assert any(
        recomendacion.action_type is CleaningActionType.REVIEW
        for recomendacion in recomendaciones
    )
    assert not any(
        recomendacion.executable
        for recomendacion in recomendaciones
    )


def test_columna_vacia_no_genera_eliminacion_automatica_v6() -> None:
    """Una columna vacía puede revisarse, pero no se elimina automáticamente."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("columna_vacia")
    )

    assert any(
        recomendacion.action_type is CleaningActionType.KEEP
        for recomendacion in recomendaciones
    )
    assert any(
        recomendacion.action_type is CleaningActionType.REVIEW
        for recomendacion in recomendaciones
    )
    assert not any(
        recomendacion.executable
        for recomendacion in recomendaciones
    )


def test_columna_constante_no_genera_eliminacion_automatica_v6() -> None:
    """Una columna constante requiere revisión contextual."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("columna_constante")
    )

    assert any(
        recomendacion.action_type is CleaningActionType.KEEP
        for recomendacion in recomendaciones
    )
    assert any(
        recomendacion.action_type is CleaningActionType.REVIEW
        for recomendacion in recomendaciones
    )
    assert not any(
        recomendacion.executable
        for recomendacion in recomendaciones
    )


def test_espacios_texto_ofrecen_operaciones_del_motor_v6() -> None:
    """Los problemas de espacios se vinculan con operaciones existentes."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("espacios_texto")
    )

    operaciones = {
        recomendacion.operation_type
        for recomendacion in recomendaciones
        if recomendacion.executable
    }

    assert "eliminar_espacios_externos" in operaciones
    assert "normalizar_espacios_internos" in operaciones


def test_inconsistencia_categorica_no_decide_equivalencias_v6() -> None:
    """La unificación categórica exige que el usuario decida la equivalencia."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("inconsistencia_categorica")
    )

    sustitucion = next(
        recomendacion
        for recomendacion in recomendaciones
        if (
            recomendacion.family == "sustitucion"
            and recomendacion.operation_type == "reemplazar_valor"
        )
    )

    assert sustitucion.requires_user_input is True
    assert sustitucion.executable is True


def test_outliers_incluyen_conservar_revisar_y_eliminar_v6() -> None:
    """Los outliers no se convierten directamente en una eliminación."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("outliers")
    )

    tipos = {
        recomendacion.action_type
        for recomendacion in recomendaciones
    }

    assert CleaningActionType.KEEP in tipos
    assert CleaningActionType.REVIEW in tipos
    assert CleaningActionType.CLEAN in tipos

    eliminar = next(
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.action_type is CleaningActionType.CLEAN
    )

    assert eliminar.family == "outliers"
    assert eliminar.operation_type == "eliminar_filas"


def test_incompatibilidad_tipo_no_decide_tipo_destino_v6() -> None:
    """La recomendación no decide automáticamente el tipo de conversión."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("incompatibilidad_tipo")
    )

    conversion = next(
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.family == "conversion"
    )

    assert conversion.operation_type is None
    assert conversion.requires_user_input is True
    assert conversion.executable is False


def test_incumplimiento_regla_no_inventa_operacion_generica_v6() -> None:
    """Una regla de negocio necesita una corrección contextual."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("incumplimiento_regla")
    )

    assert any(
        recomendacion.action_type is CleaningActionType.REVIEW
        for recomendacion in recomendaciones
    )
    assert not any(
        recomendacion.executable
        for recomendacion in recomendaciones
    )


def test_conversion_fecha_ofrece_fecha_y_fecha_hora_v6() -> None:
    """Los problemas temporales ofrecen las dos conversiones soportadas."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("conversion_fecha")
    )

    operaciones = {
        recomendacion.operation_type
        for recomendacion in recomendaciones
        if recomendacion.executable
    }

    assert operaciones == {"fecha", "fecha_hora"}

    conversiones = [
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.family == "conversion"
    ]

    assert all(
        recomendacion.requires_user_input
        for recomendacion in conversiones
    )


def test_tipo_desconocido_devuelve_revision_segura_v6() -> None:
    """Una incidencia futura desconocida nunca inventa una transformación."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("incidencia_futura")
    )

    assert len(recomendaciones) == 1

    recomendacion = recomendaciones[0]

    assert recomendacion.incident_type == "incidencia_futura"
    assert recomendacion.action_type is CleaningActionType.REVIEW
    assert recomendacion.executable is False
    assert recomendacion.family is None
    assert recomendacion.operation_type is None


def test_recomendaciones_conservan_columna_del_diagnostico_v6() -> None:
    """Las recomendaciones mantienen la referencia a la columna afectada."""
    recomendaciones = generar_recomendaciones_limpieza(
        _diagnostico("espacios_texto", "nombre_cliente")
    )

    assert all(
        recomendacion.column_name == "nombre_cliente"
        for recomendacion in recomendaciones
    )


def test_generacion_dataset_agrega_recomendaciones_en_orden_v6() -> None:
    """La API de dataset agrega los resultados respetando el orden recibido."""
    diagnosticos = (
        _diagnostico("clave_inexistente", None),
        _diagnostico("espacios_texto", "nombre"),
    )

    recomendaciones = generar_recomendaciones_limpieza_dataset(
        diagnosticos
    )

    assert recomendaciones
    assert recomendaciones[0].incident_type == "clave_inexistente"
    assert recomendaciones[0].column_name is None

    recomendaciones_espacios = [
        recomendacion
        for recomendacion in recomendaciones
        if recomendacion.incident_type == "espacios_texto"
    ]

    assert recomendaciones_espacios
    assert all(
        recomendacion.column_name == "nombre"
        for recomendacion in recomendaciones_espacios
    )


def test_generacion_dataset_vacio_devuelve_tupla_vacia_v6() -> None:
    """Un conjunto vacío de diagnósticos produce un resultado vacío."""
    recomendaciones = generar_recomendaciones_limpieza_dataset(())

    assert recomendaciones == ()

def test_recomendacion_v7_mantiene_defaults_de_trazabilidad() -> None:
    recomendacion = CleaningRecommendation(incident_type="prueba", column_name="columna", title="Prueba", explanation="Explicación", action_type=CleaningActionType.REVIEW)
    assert recomendacion.diagnostic_explanation == ""
    assert recomendacion.severity_explanation == ""

def test_recomendaciones_v7_propagan_trazabilidad() -> None:
    diagnostico = Diagnostic(incident_type="incompatibilidad_tipo", category="validez", severity="media", column_name="importe", incident_message="Incidencia", context=(), possible_actions=(), explanation="Explicación diagnóstica V7.", severity_explanation="Explicación de severidad V7.")
    recomendaciones = generar_recomendaciones_limpieza(diagnostico)
    assert recomendaciones
    assert all(r.diagnostic_explanation == diagnostico.explanation for r in recomendaciones)
    assert all(r.severity_explanation == diagnostico.severity_explanation for r in recomendaciones)

def test_trazabilidad_v7_no_cambia_logica_de_conversion() -> None:
    diagnostico = Diagnostic(incident_type="incompatibilidad_tipo", category="validez", severity="alta", column_name="importe", incident_message="Incidencia", context=(), possible_actions=(), explanation="Posible discrepancia.", severity_explanation="Severidad alta.")
    recomendaciones = generar_recomendaciones_limpieza(diagnostico)
    conversion = next(r for r in recomendaciones if r.family == "conversion")
    assert conversion.diagnostic_explanation == diagnostico.explanation
    assert conversion.severity_explanation == diagnostico.severity_explanation
    assert conversion.action_type is CleaningActionType.CLEAN
    assert conversion.operation_type is None
    assert conversion.requires_user_input is True
    assert conversion.executable is False

def test_trazabilidad_v7_se_propaga_en_generacion_dataset() -> None:
    primero = Diagnostic(incident_type="clave_inexistente", category="estructura", severity="alta", column_name=None, incident_message="Clave inexistente", context=(), possible_actions=(), explanation="Explicación primera.", severity_explanation="Severidad primera.")
    segundo = Diagnostic(incident_type="espacios_texto", category="consistencia", severity="baja", column_name="nombre", incident_message="Espacios", context=(), possible_actions=(), explanation="Explicación segunda.", severity_explanation="Severidad segunda.")
    recomendaciones = generar_recomendaciones_limpieza_dataset((primero, segundo))
    for diagnostico in (primero, segundo):
        asociadas = [r for r in recomendaciones if r.incident_type == diagnostico.incident_type]
        assert asociadas
        assert all(r.diagnostic_explanation == diagnostico.explanation for r in asociadas)
        assert all(r.severity_explanation == diagnostico.severity_explanation for r in asociadas)

