"""Reauditoría y comparación antes/después de DataQualityPy V7.

Este módulo vuelve a auditar un dataset ya limpiado y compara sus incidencias
con las de una auditoría anterior. No ejecuta limpiezas, no decide por el
usuario y no asigna puntuaciones de mejora.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.audit import auditar_dataset
from src.cleaning import CleaningResult


class ReauditError(ValueError):
    """Error al construir o ejecutar una reauditoría."""


@dataclass(frozen=True)
class IncidentComparison:
    """Una incidencia presente tanto antes como después de la limpieza."""

    before: dict[str, Any]
    after: dict[str, Any]

    def a_dict(self) -> dict[str, Any]:
        return {
            "antes": dict(self.before),
            "despues": dict(self.after),
        }


@dataclass(frozen=True)
class ReauditComparison:
    """Clasificación estructurada de incidencias antes/después."""

    resolved: tuple[dict[str, Any], ...]
    persistent: tuple[IncidentComparison, ...]
    new: tuple[dict[str, Any], ...]

    @property
    def resolved_count(self) -> int:
        return len(self.resolved)

    @property
    def persistent_count(self) -> int:
        return len(self.persistent)

    @property
    def new_count(self) -> int:
        return len(self.new)

    def a_dict(self) -> dict[str, Any]:
        return {
            "resueltas": [dict(item) for item in self.resolved],
            "persistentes": [item.a_dict() for item in self.persistent],
            "nuevas": [dict(item) for item in self.new],
            "totales": {
                "resueltas": self.resolved_count,
                "persistentes": self.persistent_count,
                "nuevas": self.new_count,
            },
        }


@dataclass(frozen=True)
class ReauditResult:
    """Resultado completo de reauditar un dataset después de limpiarlo."""

    audit_before: dict[str, Any]
    audit_after: dict[str, Any]
    cleaning_result: CleaningResult
    comparison: ReauditComparison

    def a_dict(self) -> dict[str, Any]:
        return {
            "auditoria_antes": self.audit_before,
            "auditoria_despues": self.audit_after,
            "resultado_limpieza": self.cleaning_result.a_dict(),
            "comparacion": self.comparison.a_dict(),
        }


def _validar_incidencia(incidencia: dict[str, Any]) -> None:
    if not isinstance(incidencia, dict):
        raise ReauditError("Cada incidencia debe ser un diccionario.")

    if not incidencia.get("tipo"):
        raise ReauditError("Cada incidencia debe definir un 'tipo'.")


def _identidad_incidencia(incidencia: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Devuelve la identidad estable de una incidencia para compararla.

    Cantidad, porcentaje, severidad y mensaje se excluyen deliberadamente:
    pueden cambiar tras una limpieza sin que cambie la naturaleza del problema.
    """
    _validar_incidencia(incidencia)
    return (
        incidencia.get("tipo"),
        incidencia.get("columna"),
        incidencia.get("regla"),
    )


def _indexar_incidencias(
    incidencias: list[dict[str, Any]],
    origen: str,
) -> dict[tuple[Any, Any, Any], dict[str, Any]]:
    if not isinstance(incidencias, list):
        raise ReauditError(
            f"Las incidencias de '{origen}' deben estar contenidas en una lista."
        )

    indice: dict[tuple[Any, Any, Any], dict[str, Any]] = {}

    for incidencia in incidencias:
        identidad = _identidad_incidencia(incidencia)
        if identidad in indice:
            raise ReauditError(
                "No puede compararse la reauditoría porque existen dos "
                f"incidencias con la misma identidad en '{origen}': {identidad}."
            )
        indice[identidad] = incidencia

    return indice


def comparar_incidencias(
    incidencias_antes: list[dict[str, Any]],
    incidencias_despues: list[dict[str, Any]],
) -> ReauditComparison:
    """Compara dos colecciones de incidencias sin inferir causalidad."""
    antes = _indexar_incidencias(incidencias_antes, "antes")
    despues = _indexar_incidencias(incidencias_despues, "despues")

    resueltas = tuple(
        incidencia
        for identidad, incidencia in antes.items()
        if identidad not in despues
    )

    persistentes = tuple(
        IncidentComparison(
            before=incidencia,
            after=despues[identidad],
        )
        for identidad, incidencia in antes.items()
        if identidad in despues
    )

    nuevas = tuple(
        incidencia
        for identidad, incidencia in despues.items()
        if identidad not in antes
    )

    return ReauditComparison(
        resolved=resueltas,
        persistent=persistentes,
        new=nuevas,
    )


def _extraer_incidencias(
    resultado_auditoria: dict[str, Any],
    nombre: str,
) -> list[dict[str, Any]]:
    if not isinstance(resultado_auditoria, dict):
        raise ReauditError(f"'{nombre}' debe ser un resultado de auditoría.")

    incidencias = resultado_auditoria.get("incidencias")
    if not isinstance(incidencias, list):
        raise ReauditError(
            f"'{nombre}' no contiene una lista válida de incidencias."
        )

    return incidencias


def reauditar_despues_limpieza(
    resultado_original: dict[str, Any],
    datos_limpios: pd.DataFrame,
    resultado_limpieza: CleaningResult,
    nombre_archivo: str | Path,
    configuracion: dict[str, Any],
) -> ReauditResult:
    """Reaudita el dataset limpio y compara sus incidencias con las originales."""
    incidencias_antes = _extraer_incidencias(
        resultado_original,
        "resultado_original",
    )

    if not isinstance(datos_limpios, pd.DataFrame):
        raise ReauditError("'datos_limpios' debe ser un pandas.DataFrame.")

    if not isinstance(resultado_limpieza, CleaningResult):
        raise ReauditError(
            "'resultado_limpieza' debe ser una instancia de CleaningResult."
        )

    if not isinstance(configuracion, dict):
        raise ReauditError("'configuracion' debe ser un diccionario.")

    resultado_posterior = auditar_dataset(
        datos_limpios,
        nombre_archivo,
        configuracion,
    )
    incidencias_despues = _extraer_incidencias(
        resultado_posterior,
        "resultado_posterior",
    )

    comparacion = comparar_incidencias(
        incidencias_antes,
        incidencias_despues,
    )

    return ReauditResult(
        audit_before=resultado_original,
        audit_after=resultado_posterior,
        cleaning_result=resultado_limpieza,
        comparison=comparacion,
    )
