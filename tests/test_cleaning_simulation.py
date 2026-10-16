"""Tests de simulación enriquecida de DataQualityPy V6.2.3."""

import pytest

from src.cleaning import CleaningExecution, CleaningResult
from src.cleaning_simulation import (
    CleaningSimulationError,
    CleaningSimulationSummary,
    OperationImpact,
    resumir_simulacion,
)


def _ejecucion(
    *,
    operacion_id: str = "op-1",
    familia: str = "texto",
    tipo: str = "minusculas",
    columna: str | None = "nombre",
    registros_afectados: int = 0,
    filas_antes: int = 10,
    filas_despues: int = 10,
    advertencias: list[str] | None = None,
) -> CleaningExecution:
    """Construye una ejecución configurable para los tests."""
    return CleaningExecution(
        operacion_id=operacion_id,
        familia=familia,
        tipo=tipo,
        columna=columna,
        parametros={},
        estado="ejecutada",
        registros_afectados=registros_afectados,
        filas_antes=filas_antes,
        filas_despues=filas_despues,
        advertencias=[] if advertencias is None else advertencias,
    )


def _resultado(
    *,
    filas_antes: int = 10,
    columnas_antes: int = 3,
    filas_despues: int = 10,
    columnas_despues: int = 3,
    operaciones_solicitadas: int = 0,
    operaciones_ejecutadas: int = 0,
    ejecuciones: list[CleaningExecution] | None = None,
) -> CleaningResult:
    """Construye un resultado configurable para los tests."""
    return CleaningResult(
        filas_antes=filas_antes,
        columnas_antes=columnas_antes,
        filas_despues=filas_despues,
        columnas_despues=columnas_despues,
        operaciones_solicitadas=operaciones_solicitadas,
        operaciones_ejecutadas=operaciones_ejecutadas,
        ejecuciones=[] if ejecuciones is None else ejecuciones,
    )


def test_simulacion_vacia_genera_resumen_sin_impacto_v6() -> None:
    """Un plan vacío produce un resumen válido sin cambios."""
    resultado = _resultado()

    resumen = resumir_simulacion(resultado)

    assert isinstance(resumen, CleaningSimulationSummary)
    assert resumen.rows_before == 10
    assert resumen.rows_after == 10
    assert resumen.rows_removed == 0
    assert resumen.columns_before == 3
    assert resumen.columns_after == 3
    assert resumen.columns_removed == 0
    assert resumen.operations_requested == 0
    assert resumen.operations_executed == 0
    assert resumen.operations_with_impact == 0
    assert resumen.operations_without_impact == 0
    assert resumen.total_affected_records == 0
    assert resumen.warnings == ()
    assert resumen.impacts == ()


def test_operacion_con_cambios_genera_impacto_v6() -> None:
    """Una operación que modifica registros se clasifica con impacto."""
    ejecucion = _ejecucion(
        registros_afectados=4,
    )
    resultado = _resultado(
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.operations_with_impact == 1
    assert resumen.operations_without_impact == 0
    assert resumen.total_affected_records == 4

    impacto = resumen.impacts[0]

    assert isinstance(impacto, OperationImpact)
    assert impacto.operation_id == "op-1"
    assert impacto.family == "texto"
    assert impacto.operation_type == "minusculas"
    assert impacto.column_name == "nombre"
    assert impacto.affected_records == 4
    assert impacto.changed is True


def test_operacion_sin_cambios_se_clasifica_sin_impacto_v6() -> None:
    """Una operación ejecutada con cero afectados no se considera fallida."""
    ejecucion = _ejecucion(
        registros_afectados=0,
    )
    resultado = _resultado(
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.operations_with_impact == 0
    assert resumen.operations_without_impact == 1
    assert resumen.impacts[0].changed is False
    assert resumen.impacts[0].rows_removed == 0


def test_cambio_textual_no_se_confunde_con_eliminacion_filas_v6() -> None:
    """Modificar valores no implica eliminar filas."""
    ejecucion = _ejecucion(
        registros_afectados=6,
        filas_antes=10,
        filas_despues=10,
    )
    resultado = _resultado(
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.total_affected_records == 6
    assert resumen.rows_removed == 0
    assert resumen.impacts[0].rows_removed == 0
    assert resumen.impacts[0].changed is True


def test_eliminacion_filas_calcula_impacto_individual_v6() -> None:
    """La reducción de filas se conserva en el impacto de la operación."""
    ejecucion = _ejecucion(
        familia="duplicados",
        tipo="eliminar_duplicados_completos",
        columna=None,
        registros_afectados=3,
        filas_antes=10,
        filas_despues=7,
    )
    resultado = _resultado(
        filas_antes=10,
        filas_despues=7,
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.rows_removed == 3
    assert resumen.impacts[0].rows_removed == 3
    assert resumen.impacts[0].affected_records == 3
    assert resumen.impacts[0].changed is True


def test_resumen_global_usa_dimensiones_iniciales_y_finales_v6() -> None:
    """El impacto global procede directamente del CleaningResult."""
    ejecucion_1 = _ejecucion(
        operacion_id="op-1",
        registros_afectados=5,
        filas_antes=20,
        filas_despues=20,
    )
    ejecucion_2 = _ejecucion(
        operacion_id="op-2",
        familia="outliers",
        tipo="eliminar_filas",
        columna="importe",
        registros_afectados=2,
        filas_antes=20,
        filas_despues=18,
    )

    resultado = _resultado(
        filas_antes=20,
        columnas_antes=5,
        filas_despues=18,
        columnas_despues=5,
        operaciones_solicitadas=2,
        operaciones_ejecutadas=2,
        ejecuciones=[ejecucion_1, ejecucion_2],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.rows_before == 20
    assert resumen.rows_after == 18
    assert resumen.rows_removed == 2
    assert resumen.columns_before == 5
    assert resumen.columns_after == 5
    assert resumen.columns_removed == 0


def test_total_afectados_es_acumulado_por_operacion_v6() -> None:
    """Los registros afectados se suman como impactos, no como filas únicas."""
    ejecucion_1 = _ejecucion(
        operacion_id="op-1",
        registros_afectados=4,
    )
    ejecucion_2 = _ejecucion(
        operacion_id="op-2",
        familia="conversion",
        tipo="texto",
        registros_afectados=3,
    )

    resultado = _resultado(
        operaciones_solicitadas=2,
        operaciones_ejecutadas=2,
        ejecuciones=[ejecucion_1, ejecucion_2],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.total_affected_records == 7
    assert resumen.operations_with_impact == 2


def test_operaciones_con_y_sin_impacto_se_cuentan_por_separado_v6() -> None:
    """El resumen distingue operaciones efectivas de operaciones sin cambios."""
    ejecuciones = [
        _ejecucion(
            operacion_id="op-1",
            registros_afectados=5,
        ),
        _ejecucion(
            operacion_id="op-2",
            registros_afectados=0,
        ),
        _ejecucion(
            operacion_id="op-3",
            registros_afectados=2,
        ),
    ]

    resultado = _resultado(
        operaciones_solicitadas=3,
        operaciones_ejecutadas=3,
        ejecuciones=ejecuciones,
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.operations_with_impact == 2
    assert resumen.operations_without_impact == 1
    assert resumen.total_affected_records == 7


def test_advertencias_se_conservan_en_impacto_v6() -> None:
    """Las advertencias permanecen asociadas a su operación."""
    ejecucion = _ejecucion(
        familia="conversion",
        tipo="numerico",
        registros_afectados=2,
        advertencias=[
            "2 valor(es) incompatible(s) se convirtieron explícitamente a nulo."
        ],
    )

    resultado = _resultado(
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.impacts[0].warnings == (
        "2 valor(es) incompatible(s) se convirtieron explícitamente a nulo.",
    )


def test_advertencias_globales_respetan_orden_ejecucion_v6() -> None:
    """El resumen global recopila advertencias en orden de ejecución."""
    ejecucion_1 = _ejecucion(
        operacion_id="op-1",
        advertencias=["Advertencia A"],
    )
    ejecucion_2 = _ejecucion(
        operacion_id="op-2",
        advertencias=["Advertencia B", "Advertencia C"],
    )

    resultado = _resultado(
        operaciones_solicitadas=2,
        operaciones_ejecutadas=2,
        ejecuciones=[ejecucion_1, ejecucion_2],
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.warnings == (
        "Advertencia A",
        "Advertencia B",
        "Advertencia C",
    )


def test_impactos_respetan_orden_de_ejecucion_v6() -> None:
    """Los impactos mantienen el mismo orden registrado por el motor."""
    ejecuciones = [
        _ejecucion(operacion_id="primera"),
        _ejecucion(operacion_id="segunda"),
        _ejecucion(operacion_id="tercera"),
    ]

    resultado = _resultado(
        operaciones_solicitadas=3,
        operaciones_ejecutadas=3,
        ejecuciones=ejecuciones,
    )

    resumen = resumir_simulacion(resultado)

    assert tuple(
        impacto.operation_id
        for impacto in resumen.impacts
    ) == (
        "primera",
        "segunda",
        "tercera",
    )


def test_columnas_eliminadas_se_calculan_desde_resultado_v6() -> None:
    """El resumen soporta reducciones estructurales si aparecen en el futuro."""
    resultado = _resultado(
        columnas_antes=5,
        columnas_despues=4,
    )

    resumen = resumir_simulacion(resultado)

    assert resumen.columns_removed == 1


def test_resultado_invalido_genera_error_v6() -> None:
    """La API exige una instancia real de CleaningResult."""
    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(
            None,  # type: ignore[arg-type]
        )


def test_filas_finales_mayores_que_iniciales_generan_error_v6() -> None:
    """El resumen rechaza una evolución incompatible con el motor actual."""
    resultado = _resultado(
        filas_antes=10,
        filas_despues=11,
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)


def test_columnas_finales_mayores_que_iniciales_generan_error_v6() -> None:
    """El motor actual no contiene operaciones que añadan columnas."""
    resultado = _resultado(
        columnas_antes=3,
        columnas_despues=4,
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)


def test_ejecutadas_no_pueden_superar_solicitadas_v6() -> None:
    """No puede haber más ejecuciones correctas que operaciones solicitadas."""
    resultado = _resultado(
        operaciones_solicitadas=0,
        operaciones_ejecutadas=1,
        ejecuciones=[_ejecucion()],
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)


def test_numero_ejecuciones_debe_coincidir_con_resultado_v6() -> None:
    """El contador ejecutado debe coincidir con las ejecuciones registradas."""
    resultado = _resultado(
        operaciones_solicitadas=2,
        operaciones_ejecutadas=2,
        ejecuciones=[_ejecucion()],
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)


def test_ejecucion_no_puede_aumentar_filas_v6() -> None:
    """Una ejecución individual no puede añadir filas actualmente."""
    ejecucion = _ejecucion(
        filas_antes=10,
        filas_despues=11,
    )

    resultado = _resultado(
        filas_antes=10,
        filas_despues=10,
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)


def test_metricas_negativas_generan_error_v6() -> None:
    """Las métricas estructurales no admiten valores negativos."""
    resultado = _resultado(
        filas_despues=-1,
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)


def test_registros_afectados_negativos_generan_error_v6() -> None:
    """Una ejecución no puede registrar un número negativo de afectados."""
    ejecucion = _ejecucion(
        registros_afectados=-1,
    )

    resultado = _resultado(
        operaciones_solicitadas=1,
        operaciones_ejecutadas=1,
        ejecuciones=[ejecucion],
    )

    with pytest.raises(CleaningSimulationError):
        resumir_simulacion(resultado)