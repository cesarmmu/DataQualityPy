"""Persistencia de planes reutilizables de limpieza de DataQualityPy V6.

Este módulo permite serializar, guardar, recuperar y reconstruir planes
de limpieza sin almacenar identificadores internos de las operaciones.

El formato persistente contiene únicamente la definición necesaria para
recrear conscientemente un CleaningPlan nuevo y validado.

Este módulo:
- no modifica DataFrames;
- no ejecuta operaciones de limpieza;
- no guarda resultados de ejecución;
- no reutiliza identificadores de operaciones anteriores;
- reconstruye los planes mediante la API pública de CleaningPlan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from src.cleaning_plan import (
    CleaningPlan,
    CleaningPlanError,
)


FORMATO_PLAN_VERSION = "1.0"


class CleaningPlanStorageError(ValueError):
    """Error al serializar, guardar o recuperar un plan reutilizable."""


@dataclass(frozen=True)
class StoredCleaningPlan:
    """Representación persistente y reutilizable de un plan de limpieza."""

    format_version: str
    name: str
    created_at: str
    operations: tuple[Mapping[str, Any], ...]

    def a_dict(self) -> dict[str, Any]:
        """Devuelve una estructura preparada para serialización JSON."""
        return {
            "format_version": self.format_version,
            "name": self.name,
            "created_at": self.created_at,
            "operations": [
                {
                    "family": operacion["family"],
                    "type": operacion["type"],
                    "column": operacion["column"],
                    "parameters": dict(operacion["parameters"]),
                }
                for operacion in self.operations
            ],
        }


def _validar_nombre(nombre: str) -> str:
    """Valida y normaliza el nombre descriptivo del plan."""
    if not isinstance(nombre, str) or not nombre.strip():
        raise CleaningPlanStorageError(
            "'name' debe ser una cadena de texto no vacía."
        )

    return nombre.strip()


def _validar_fecha_creacion(created_at: str) -> str:
    """Comprueba que la fecha almacenada utilice formato ISO 8601."""
    if not isinstance(created_at, str) or not created_at.strip():
        raise CleaningPlanStorageError(
            "'created_at' debe ser una cadena de texto no vacía."
        )

    valor = created_at.strip()

    try:
        datetime.fromisoformat(valor)
    except ValueError as exc:
        raise CleaningPlanStorageError(
            "'created_at' debe utilizar un formato ISO 8601 válido."
        ) from exc

    return valor


def _serializar_operaciones(
    plan: CleaningPlan,
) -> tuple[Mapping[str, Any], ...]:
    """Extrae únicamente la definición reutilizable de las operaciones."""
    operaciones: list[Mapping[str, Any]] = []

    for operacion in plan.operaciones_ordenadas():
        operaciones.append(
            {
                "family": operacion.familia,
                "type": operacion.tipo,
                "column": operacion.columna,
                "parameters": dict(operacion.parametros),
            }
        )

    return tuple(operaciones)


def crear_plan_almacenado(
    plan: CleaningPlan,
    name: str,
    *,
    created_at: str | None = None,
) -> StoredCleaningPlan:
    """Construye la representación persistente de un CleaningPlan."""
    if not isinstance(plan, CleaningPlan):
        raise CleaningPlanStorageError(
            "'plan' debe ser una instancia de CleaningPlan."
        )

    nombre = _validar_nombre(name)

    fecha = (
        datetime.now().astimezone().isoformat(timespec="seconds")
        if created_at is None
        else _validar_fecha_creacion(created_at)
    )

    return StoredCleaningPlan(
        format_version=FORMATO_PLAN_VERSION,
        name=nombre,
        created_at=fecha,
        operations=_serializar_operaciones(plan),
    )


def _validar_operacion_almacenada(
    operacion: Any,
    indice: int,
) -> dict[str, Any]:
    """Valida la estructura básica de una operación persistida."""
    if not isinstance(operacion, dict):
        raise CleaningPlanStorageError(
            f"La operación {indice} debe ser un objeto JSON."
        )

    campos = {"family", "type", "column", "parameters"}

    faltantes = campos - set(operacion)
    if faltantes:
        raise CleaningPlanStorageError(
            f"La operación {indice} no contiene los campos obligatorios: "
            f"{sorted(faltantes)}."
        )

    extras = set(operacion) - campos
    if extras:
        raise CleaningPlanStorageError(
            f"La operación {indice} contiene campos no admitidos: "
            f"{sorted(extras)}."
        )

    parametros = operacion["parameters"]
    if not isinstance(parametros, dict):
        raise CleaningPlanStorageError(
            f"'parameters' de la operación {indice} debe ser un objeto JSON."
        )

    return {
        "family": operacion["family"],
        "type": operacion["type"],
        "column": operacion["column"],
        "parameters": dict(parametros),
    }


def plan_almacenado_desde_dict(
    datos: Any,
) -> StoredCleaningPlan:
    """Valida una estructura externa y crea un StoredCleaningPlan."""
    if not isinstance(datos, dict):
        raise CleaningPlanStorageError(
            "El contenido del plan debe ser un objeto JSON."
        )

    campos = {
        "format_version",
        "name",
        "created_at",
        "operations",
    }

    faltantes = campos - set(datos)
    if faltantes:
        raise CleaningPlanStorageError(
            "El plan no contiene los campos obligatorios: "
            f"{sorted(faltantes)}."
        )

    extras = set(datos) - campos
    if extras:
        raise CleaningPlanStorageError(
            "El plan contiene campos no admitidos: "
            f"{sorted(extras)}."
        )

    version = datos["format_version"]
    if version != FORMATO_PLAN_VERSION:
        raise CleaningPlanStorageError(
            "Versión de formato de plan no compatible: "
            f"'{version}'. Versión admitida: '{FORMATO_PLAN_VERSION}'."
        )

    nombre = _validar_nombre(datos["name"])
    fecha = _validar_fecha_creacion(datos["created_at"])

    operaciones_datos = datos["operations"]
    if not isinstance(operaciones_datos, list):
        raise CleaningPlanStorageError(
            "'operations' debe ser una lista."
        )

    operaciones = tuple(
        _validar_operacion_almacenada(operacion, indice)
        for indice, operacion in enumerate(
            operaciones_datos,
            start=1,
        )
    )

    return StoredCleaningPlan(
        format_version=version,
        name=nombre,
        created_at=fecha,
        operations=operaciones,
    )


def reconstruir_plan(
    almacenado: StoredCleaningPlan,
) -> CleaningPlan:
    """Reconstruye un CleaningPlan nuevo y completamente validado."""
    if not isinstance(almacenado, StoredCleaningPlan):
        raise CleaningPlanStorageError(
            "'almacenado' debe ser una instancia de StoredCleaningPlan."
        )

    if almacenado.format_version != FORMATO_PLAN_VERSION:
        raise CleaningPlanStorageError(
            "La versión del plan almacenado no es compatible."
        )

    plan = CleaningPlan()

    try:
        for operacion in almacenado.operations:
            plan.crear_operacion(
                familia=operacion["family"],
                tipo=operacion["type"],
                columna=operacion["column"],
                parametros=dict(operacion["parameters"]),
            )
    except (CleaningPlanError, KeyError, TypeError) as exc:
        raise CleaningPlanStorageError(
            f"No se pudo reconstruir el plan de limpieza: {exc}"
        ) from exc

    return plan


def guardar_plan(
    ruta: str | Path,
    plan: CleaningPlan,
    name: str,
    *,
    created_at: str | None = None,
) -> Path:
    """Guarda un plan reutilizable en formato JSON."""
    almacenado = crear_plan_almacenado(
        plan,
        name,
        created_at=created_at,
    )

    destino = Path(ruta)

    if destino.suffix.lower() != ".json":
        raise CleaningPlanStorageError(
            "Los planes reutilizables deben guardarse con extensión '.json'."
        )

    try:
        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destino.write_text(
            json.dumps(
                almacenado.a_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        raise CleaningPlanStorageError(
            f"No se pudo guardar el plan en '{destino}': {exc}"
        ) from exc

    return destino


def cargar_plan_almacenado(
    ruta: str | Path,
) -> StoredCleaningPlan:
    """Carga y valida un plan reutilizable desde un archivo JSON."""
    origen = Path(ruta)

    if origen.suffix.lower() != ".json":
        raise CleaningPlanStorageError(
            "Los planes reutilizables deben cargarse desde un archivo '.json'."
        )

    try:
        contenido = origen.read_text(encoding="utf-8")
    except OSError as exc:
        raise CleaningPlanStorageError(
            f"No se pudo leer el plan '{origen}': {exc}"
        ) from exc

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError as exc:
        raise CleaningPlanStorageError(
            f"El archivo '{origen}' no contiene un JSON válido."
        ) from exc

    return plan_almacenado_desde_dict(datos)


def cargar_plan(
    ruta: str | Path,
) -> CleaningPlan:
    """Carga un archivo reutilizable y reconstruye un CleaningPlan nuevo."""
    almacenado = cargar_plan_almacenado(ruta)
    return reconstruir_plan(almacenado)