"""Generación del informe de auditoría en formato JSON."""

import json
from pathlib import Path


VERSION_INFORME = "3.0"


def _preparar_contenido_json(
    resultado_auditoria: dict,
) -> dict:
    """Prepara la estructura que se almacenará en el informe JSON."""
    return {
        "dataqualitypy": {
            "version_informe": VERSION_INFORME,
        },
        "dataset": resultado_auditoria["dataset"],
        "resumen": resultado_auditoria["resumen"],
        "tipos_semanticos": resultado_auditoria["tipos_semanticos"],
        "incidencias": resultado_auditoria["incidencias"],
        "perfil": resultado_auditoria["perfil"],
        "calidad": resultado_auditoria["calidad"],
    }


def generar_informe_json(
    resultado_auditoria: dict,
    ruta_salida: str | Path,
) -> Path:
    """Genera un archivo JSON con el resultado de la auditoría."""
    ruta_salida = Path(ruta_salida)

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    contenido = _preparar_contenido_json(
        resultado_auditoria
    )

    with ruta_salida.open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            contenido,
            archivo,
            ensure_ascii=False,
            indent=2,
        )

    return ruta_salida
