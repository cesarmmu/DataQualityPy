"""Resumen enriquecido de simulaciones de limpieza de DataQualityPy V6.

Este módulo interpreta un CleaningResult ya generado por el motor de
limpieza y construye un resumen estructurado del impacto previsto.

Responsabilidades:
- resumir el impacto global de una simulación;
- describir el impacto de cada operación;
- distinguir operaciones con y sin efecto;
- calcular filas eliminadas;
- recopilar advertencias de ejecución.

Este módulo:
- no recibe ni modifica DataFrames;
- no ejecuta planes de limpieza;
- no recalcula incidencias;
- no realiza una nueva auditoría;
- no decide si debe aplicarse un plan.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.cleaning import CleaningExecution, CleaningResult


class CleaningSimulationError(ValueError):
    """Error al construir el resumen de una simulación de limpieza."""


@dataclass(frozen=True)
class OperationImpact:
    """Impacto observado de una operación durante la simulación."""

    operation_id: str
    family: str
    operation_type: str
    column_name: str | None
    affected_records: int
    rows_before: int
    rows_after: int
    rows_removed: int
    changed: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class CleaningSimulationSummary:
    """Resumen estructurado del impacto previsto de un plan de limpieza."""

    rows_before: int
    rows_after: int
    rows_removed: int
    columns_before: int
    columns_after: int
    columns_removed: int
    operations_requested: int
    operations_executed: int
    operations_with_impact: int
    operations_without_impact: int
    total_affected_records: int
    warnings: tuple[str, ...]
    impacts: tuple[OperationImpact, ...]


def _validar_entero_no_negativo(
    valor: int,
    nombre: str,
) -> None:
    """Comprueba que una métrica estructural sea un entero no negativo."""
    if not isinstance(valor, int) or isinstance(valor, bool) or valor < 0:
        raise CleaningSimulationError(
            f"'{nombre}' debe ser un entero no negativo."
        )


def _validar_resultado(
    resultado: CleaningResult,
) -> None:
    """Valida la estructura mínima necesaria del resultado."""
    if not isinstance(resultado, CleaningResult):
        raise CleaningSimulationError(
            "'resultado' debe ser una instancia de CleaningResult."
        )

    _validar_entero_no_negativo(
        resultado.filas_antes,
        "filas_antes",
    )
    _validar_entero_no_negativo(
        resultado.filas_despues,
        "filas_despues",
    )
    _validar_entero_no_negativo(
        resultado.columnas_antes,
        "columnas_antes",
    )
    _validar_entero_no_negativo(
        resultado.columnas_despues,
        "columnas_despues",
    )
    _validar_entero_no_negativo(
        resultado.operaciones_solicitadas,
        "operaciones_solicitadas",
    )
    _validar_entero_no_negativo(
        resultado.operaciones_ejecutadas,
        "operaciones_ejecutadas",
    )

    if resultado.filas_despues > resultado.filas_antes:
        raise CleaningSimulationError(
            "'filas_despues' no puede ser mayor que 'filas_antes' "
            "en el motor de limpieza actual."
        )

    if resultado.columnas_despues > resultado.columnas_antes:
        raise CleaningSimulationError(
            "'columnas_despues' no puede ser mayor que "
            "'columnas_antes' en el motor de limpieza actual."
        )

    if resultado.operaciones_ejecutadas > resultado.operaciones_solicitadas:
        raise CleaningSimulationError(
            "'operaciones_ejecutadas' no puede superar "
            "'operaciones_solicitadas'."
        )

    if resultado.operaciones_ejecutadas != len(resultado.ejecuciones):
        raise CleaningSimulationError(
            "'operaciones_ejecutadas' no coincide con el número "
            "de ejecuciones registradas."
        )


def _validar_ejecucion(
    ejecucion: CleaningExecution,
) -> None:
    """Valida los datos mínimos de una ejecución individual."""
    if not isinstance(ejecucion, CleaningExecution):
        raise CleaningSimulationError(
            "Todas las ejecuciones deben ser instancias de "
            "CleaningExecution."
        )

    _validar_entero_no_negativo(
        ejecucion.registros_afectados,
        "registros_afectados",
    )
    _validar_entero_no_negativo(
        ejecucion.filas_antes,
        "filas_antes de ejecución",
    )
    _validar_entero_no_negativo(
        ejecucion.filas_despues,
        "filas_despues de ejecución",
    )

    if ejecucion.filas_despues > ejecucion.filas_antes:
        raise CleaningSimulationError(
            "Una ejecución no puede aumentar el número de filas "
            "con las operaciones admitidas actualmente."
        )


def _crear_impacto(
    ejecucion: CleaningExecution,
) -> OperationImpact:
    """Convierte una ejecución del motor en un impacto estructurado."""
    _validar_ejecucion(ejecucion)

    filas_eliminadas = (
        ejecucion.filas_antes
        - ejecucion.filas_despues
    )

    return OperationImpact(
        operation_id=ejecucion.operacion_id,
        family=ejecucion.familia,
        operation_type=ejecucion.tipo,
        column_name=ejecucion.columna,
        affected_records=ejecucion.registros_afectados,
        rows_before=ejecucion.filas_antes,
        rows_after=ejecucion.filas_despues,
        rows_removed=filas_eliminadas,
        changed=ejecucion.registros_afectados > 0,
        warnings=tuple(ejecucion.advertencias),
    )


def _recopilar_advertencias(
    impactos: tuple[OperationImpact, ...],
) -> tuple[str, ...]:
    """Recopila advertencias manteniendo el orden de ejecución."""
    advertencias: list[str] = []

    for impacto in impactos:
        advertencias.extend(impacto.warnings)

    return tuple(advertencias)


def resumir_simulacion(
    resultado: CleaningResult,
) -> CleaningSimulationSummary:
    """Construye un resumen enriquecido a partir de CleaningResult.

    ``total_affected_records`` representa la suma de los registros afectados
    por cada operación. No equivale necesariamente al número de filas únicas
    modificadas, ya que una misma fila puede verse afectada por varias
    operaciones del plan.
    """
    _validar_resultado(resultado)

    impactos = tuple(
        _crear_impacto(ejecucion)
        for ejecucion in resultado.ejecuciones
    )

    operaciones_con_impacto = sum(
        1
        for impacto in impactos
        if impacto.changed
    )

    operaciones_sin_impacto = sum(
        1
        for impacto in impactos
        if not impacto.changed
    )

    total_registros_afectados = sum(
        impacto.affected_records
        for impacto in impactos
    )

    filas_eliminadas = (
        resultado.filas_antes
        - resultado.filas_despues
    )

    columnas_eliminadas = (
        resultado.columnas_antes
        - resultado.columnas_despues
    )

    advertencias = _recopilar_advertencias(impactos)

    return CleaningSimulationSummary(
        rows_before=resultado.filas_antes,
        rows_after=resultado.filas_despues,
        rows_removed=filas_eliminadas,
        columns_before=resultado.columnas_antes,
        columns_after=resultado.columnas_despues,
        columns_removed=columnas_eliminadas,
        operations_requested=resultado.operaciones_solicitadas,
        operations_executed=resultado.operaciones_ejecutadas,
        operations_with_impact=operaciones_con_impacto,
        operations_without_impact=operaciones_sin_impacto,
        total_affected_records=total_registros_afectados,
        warnings=advertencias,
        impacts=impactos,
    )