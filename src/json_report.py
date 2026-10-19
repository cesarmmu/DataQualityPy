"""Generación del informe de auditoría en formato JSON de DataQualityPy V7."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.reaudit import ReauditResult
from src.reproducibility import ExecutionManifest


VERSION_INFORME = "7.0"
CLAVES_DATOS_CRUDOS = {"datos", "filas_originales", "registros", "raw_data", "rows"}


def _sin_datos_crudos(valor: Any) -> Any:
    """Copia una estructura excluyendo claves reservadas para filas originales."""
    if isinstance(valor, dict):
        return {
            clave: _sin_datos_crudos(contenido)
            for clave, contenido in valor.items()
            if clave not in CLAVES_DATOS_CRUDOS
        }

    if isinstance(valor, list):
        return [_sin_datos_crudos(item) for item in valor]

    if isinstance(valor, tuple):
        return [_sin_datos_crudos(item) for item in valor]

    return valor


def _convertir_tipo_json(valor: Any) -> Any:
    """Convierte tipos NumPy no serializables a tipos compatibles con JSON."""
    if isinstance(valor, np.integer):
        return int(valor)

    if isinstance(valor, np.floating):
        return float(valor)

    if isinstance(valor, np.bool_):
        return bool(valor)

    if isinstance(valor, np.ndarray):
        return valor.tolist()

    raise TypeError(
        f"Object of type {type(valor).__name__} is not JSON serializable"
    )


def _preparar_contenido_json(
    resultado_auditoria: dict[str, Any],
    *,
    resultado_reauditoria: ReauditResult | None = None,
    manifiesto_reproducibilidad: ExecutionManifest | None = None,
) -> dict[str, Any]:
    """Prepara la estructura serializable del informe JSON V7."""
    contenido: dict[str, Any] = {
        "dataqualitypy": {"version_informe": VERSION_INFORME},
        "dataset": _sin_datos_crudos(resultado_auditoria["dataset"]),
        "resumen": _sin_datos_crudos(resultado_auditoria["resumen"]),
        "tipos_semanticos": _sin_datos_crudos(resultado_auditoria["tipos_semanticos"]),
        "incidencias": _sin_datos_crudos(resultado_auditoria["incidencias"]),
        "perfil": _sin_datos_crudos(resultado_auditoria["perfil"]),
        "calidad": _sin_datos_crudos(resultado_auditoria["calidad"]),
    }

    if "analisis_avanzado" in resultado_auditoria:
        contenido["analisis_avanzado"] = _sin_datos_crudos(
            resultado_auditoria["analisis_avanzado"]
        )

    if resultado_reauditoria is not None:
        if not isinstance(resultado_reauditoria, ReauditResult):
            raise TypeError(
                "'resultado_reauditoria' debe ser una instancia de ReauditResult."
            )

        contenido["limpieza_reauditoria"] = _sin_datos_crudos(
            resultado_reauditoria.a_dict()
        )

    if manifiesto_reproducibilidad is not None:
        if not isinstance(manifiesto_reproducibilidad, ExecutionManifest):
            raise TypeError(
                "'manifiesto_reproducibilidad' debe ser una instancia de "
                "ExecutionManifest."
            )

        contenido["reproducibilidad"] = _sin_datos_crudos(
            manifiesto_reproducibilidad.a_dict()
        )

    return contenido


def generar_documento_json(
    resultado_auditoria: dict[str, Any],
    *,
    resultado_reauditoria: ReauditResult | None = None,
    manifiesto_reproducibilidad: ExecutionManifest | None = None,
) -> str:
    """Genera en memoria el informe JSON V7 como texto."""
    contenido = _preparar_contenido_json(
        resultado_auditoria,
        resultado_reauditoria=resultado_reauditoria,
        manifiesto_reproducibilidad=manifiesto_reproducibilidad,
    )

    return json.dumps(
        contenido,
        ensure_ascii=False,
        indent=2,
        default=_convertir_tipo_json,
    )


def generar_informe_json(
    resultado_auditoria: dict[str, Any],
    ruta_salida: str | Path,
    *,
    resultado_reauditoria: ReauditResult | None = None,
    manifiesto_reproducibilidad: ExecutionManifest | None = None,
) -> Path:
    """Genera un informe JSON V7 con los bloques disponibles de la ejecución."""
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    documento = generar_documento_json(
        resultado_auditoria,
        resultado_reauditoria=resultado_reauditoria,
        manifiesto_reproducibilidad=manifiesto_reproducibilidad,
    )

    ruta_salida.write_text(documento, encoding="utf-8")

    return ruta_salida