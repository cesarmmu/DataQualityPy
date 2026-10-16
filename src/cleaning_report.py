"""Informes de trazabilidad de limpieza de DataQualityPy V6."""

from __future__ import annotations

from datetime import datetime
from html import escape
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.cleaning import CleaningResult


class ErrorInformeLimpieza(Exception):
    """Error al construir o generar un informe de limpieza."""


def generar_nombres_informes(nombre_original: str | Path) -> tuple[str, str]:
    """Genera los nombres JSON y HTML del informe de limpieza."""
    stem = Path(nombre_original).stem
    return (
        f"{stem}_cleaning_report.json",
        f"{stem}_cleaning_report.html",
    )


def _serializar_valor(valor: Any) -> Any:
    """Convierte valores frecuentes de pandas/numpy a JSON."""
    if valor is None:
        return None

    if isinstance(valor, (str, int, float, bool)):
        return valor

    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.isoformat()

    if isinstance(valor, Path):
        return str(valor)

    if isinstance(valor, dict):
        return {
            str(clave): _serializar_valor(contenido)
            for clave, contenido in valor.items()
        }

    if isinstance(valor, (list, tuple, set)):
        return [_serializar_valor(elemento) for elemento in valor]

    if hasattr(valor, "item"):
        try:
            return _serializar_valor(valor.item())
        except (ValueError, AttributeError):
            pass

    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    return str(valor)


def _incidencias(resultado_auditoria: dict[str, Any]) -> list[dict[str, Any]]:
    """Obtiene las incidencias serializables de un resultado de auditoría."""
    incidencias = resultado_auditoria.get("incidencias", [])
    if not isinstance(incidencias, list):
        return []
    return [
        _serializar_valor(incidencia)
        for incidencia in incidencias
        if isinstance(incidencia, dict)
    ]


def _identidad_incidencia(incidencia: dict[str, Any]) -> tuple[str, str, str]:
    """Define la identidad funcional usada en la verificación de limpieza."""
    return (
        str(incidencia.get("tipo", "")),
        str(incidencia.get("categoria", "")),
        str(incidencia.get("columna", "")),
    )


def comparar_incidencias(
    resultado_antes: dict[str, Any],
    resultado_despues: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Clasifica incidencias resueltas, pendientes y nuevas."""
    antes = _incidencias(resultado_antes)
    despues = _incidencias(resultado_despues)

    mapa_antes = {_identidad_incidencia(i): i for i in antes}
    mapa_despues = {_identidad_incidencia(i): i for i in despues}

    claves_antes = set(mapa_antes)
    claves_despues = set(mapa_despues)

    return {
        "resueltas": [
            mapa_antes[clave]
            for clave in mapa_antes
            if clave not in claves_despues
        ],
        "pendientes": [
            mapa_despues[clave]
            for clave in mapa_despues
            if clave in claves_antes
        ],
        "nuevas": [
            mapa_despues[clave]
            for clave in mapa_despues
            if clave not in claves_antes
        ],
    }


def construir_trazabilidad_limpieza(
    *,
    nombre_archivo: str,
    hoja: str | None,
    filas_originales: int,
    columnas_originales: int,
    filas_limpias: int,
    columnas_limpias: int,
    plan_solicitado: dict[str, Any] | list[dict[str, Any]],
    resultado_limpieza: CleaningResult | dict[str, Any],
    resultado_auditoria_antes: dict[str, Any],
    resultado_auditoria_despues: dict[str, Any],
    configuracion_auditoria: dict[str, Any] | None = None,
    generado_en: datetime | None = None,
) -> dict[str, Any]:
    """Construye la fuente única de trazabilidad para JSON y HTML."""
    if isinstance(resultado_limpieza, CleaningResult):
        ejecucion = resultado_limpieza.a_dict()
    elif isinstance(resultado_limpieza, dict):
        ejecucion = resultado_limpieza
    else:
        raise ErrorInformeLimpieza(
            "'resultado_limpieza' debe ser CleaningResult o dict."
        )

    cambios = comparar_incidencias(
        resultado_auditoria_antes,
        resultado_auditoria_despues,
    )

    instante = generado_en or datetime.now().astimezone()

    trazabilidad = {
        "metadatos": {
            "aplicacion": "DataQualityPy",
            "version": "V6",
            "generado_en": instante.isoformat(),
            "original_modificado": False,
        },
        "origen": {
            "archivo": nombre_archivo,
            "hoja": hoja,
            "filas": int(filas_originales),
            "columnas": int(columnas_originales),
        },
        "resultado": {
            "filas": int(filas_limpias),
            "columnas": int(columnas_limpias),
            "filas_eliminadas": max(
                0,
                int(filas_originales) - int(filas_limpias),
            ),
        },
        "configuracion_auditoria": configuracion_auditoria or {},
        "plan_solicitado": plan_solicitado,
        "ejecucion": ejecucion,
        "verificacion": {
            "incidencias_antes": len(
                _incidencias(resultado_auditoria_antes)
            ),
            "incidencias_despues": len(
                _incidencias(resultado_auditoria_despues)
            ),
            "resueltas": cambios["resueltas"],
            "pendientes": cambios["pendientes"],
            "nuevas": cambios["nuevas"],
        },
    }
    return _serializar_valor(trazabilidad)


def generar_json_limpieza(trazabilidad: dict[str, Any]) -> str:
    """Genera el informe JSON de trazabilidad."""
    try:
        return json.dumps(
            _serializar_valor(trazabilidad),
            ensure_ascii=False,
            indent=2,
        )
    except (TypeError, ValueError) as error:
        raise ErrorInformeLimpieza(
            "No se ha podido generar el informe JSON."
        ) from error


def _texto(valor: Any) -> str:
    return escape("" if valor is None else str(valor))


def _tabla_incidencias(
    titulo: str,
    incidencias: list[dict[str, Any]],
) -> str:
    filas = []
    for incidencia in incidencias:
        filas.append(
            "<tr>"
            f"<td>{_texto(incidencia.get('tipo'))}</td>"
            f"<td>{_texto(incidencia.get('categoria'))}</td>"
            f"<td>{_texto(incidencia.get('columna'))}</td>"
            f"<td>{_texto(incidencia.get('severidad'))}</td>"
            "</tr>"
        )

    contenido = (
        "".join(filas)
        if filas
        else '<tr><td colspan="4">Sin incidencias.</td></tr>'
    )

    return f"""
    <section>
      <h3>{escape(titulo)} ({len(incidencias)})</h3>
      <table>
        <thead>
          <tr><th>Tipo</th><th>Categoría</th><th>Columna</th><th>Severidad</th></tr>
        </thead>
        <tbody>{contenido}</tbody>
      </table>
    </section>
    """


def generar_html_limpieza(trazabilidad: dict[str, Any]) -> str:
    """Genera un informe HTML legible desde la misma trazabilidad."""
    origen = trazabilidad["origen"]
    resultado = trazabilidad["resultado"]
    ejecucion = trazabilidad["ejecucion"]
    verificacion = trazabilidad["verificacion"]
    metadatos = trazabilidad["metadatos"]

    operaciones = ejecucion.get("ejecuciones", [])
    filas_operaciones = []
    for operacion in operaciones:
        filas_operaciones.append(
            "<tr>"
            f"<td>{_texto(operacion.get('familia'))}</td>"
            f"<td>{_texto(operacion.get('tipo'))}</td>"
            f"<td>{_texto(operacion.get('columna'))}</td>"
            f"<td>{_texto(operacion.get('registros_afectados', 0))}</td>"
            f"<td>{_texto(operacion.get('estado'))}</td>"
            "</tr>"
        )

    operaciones_html = (
        "".join(filas_operaciones)
        if filas_operaciones
        else '<tr><td colspan="5">Sin operaciones ejecutadas.</td></tr>'
    )

    hoja = origen.get("hoja") or "No aplica"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Informe de limpieza - DataQualityPy</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #222; }}
h1, h2, h3 {{ margin-bottom: 8px; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 16px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
.metric {{ border: 1px solid #e1e1e1; border-radius: 6px; padding: 12px; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0 20px; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f4f4f4; }}
small {{ color: #666; }}
</style>
</head>
<body>
<h1>DataQualityPy — Informe de limpieza</h1>
<p><small>Generado: {_texto(metadatos.get("generado_en"))}</small></p>

<div class="card">
<h2>Origen</h2>
<p><strong>Archivo:</strong> {_texto(origen.get("archivo"))}</p>
<p><strong>Hoja:</strong> {_texto(hoja)}</p>
<p>El archivo original no ha sido modificado.</p>
</div>

<div class="card">
<h2>Resultado</h2>
<div class="grid">
<div class="metric"><strong>Filas</strong><br>{_texto(origen.get("filas"))} → {_texto(resultado.get("filas"))}</div>
<div class="metric"><strong>Columnas</strong><br>{_texto(origen.get("columnas"))} → {_texto(resultado.get("columnas"))}</div>
<div class="metric"><strong>Filas eliminadas</strong><br>{_texto(resultado.get("filas_eliminadas"))}</div>
</div>
</div>

<div class="card">
<h2>Ejecución</h2>
<p>Operaciones solicitadas: {_texto(ejecucion.get("operaciones_solicitadas", 0))} ·
Operaciones ejecutadas: {_texto(ejecucion.get("operaciones_ejecutadas", 0))}</p>
<table>
<thead><tr><th>Familia</th><th>Operación</th><th>Columna</th><th>Registros afectados</th><th>Estado</th></tr></thead>
<tbody>{operaciones_html}</tbody>
</table>
</div>

<div class="card">
<h2>Verificación</h2>
<p>Incidencias: {_texto(verificacion.get("incidencias_antes"))} → {_texto(verificacion.get("incidencias_despues"))}</p>
{_tabla_incidencias("Resueltas", verificacion.get("resueltas", []))}
{_tabla_incidencias("Pendientes", verificacion.get("pendientes", []))}
{_tabla_incidencias("Nuevas", verificacion.get("nuevas", []))}
</div>
</body>
</html>
"""


def guardar_informes_limpieza(
    trazabilidad: dict[str, Any],
    directorio: str | Path,
    nombre_original: str | Path,
) -> tuple[Path, Path]:
    """Guarda JSON y HTML de trazabilidad en el directorio indicado."""
    destino = Path(directorio)
    destino.mkdir(parents=True, exist_ok=True)

    nombre_json, nombre_html = generar_nombres_informes(nombre_original)
    ruta_json = destino / nombre_json
    ruta_html = destino / nombre_html

    try:
        ruta_json.write_text(
            generar_json_limpieza(trazabilidad),
            encoding="utf-8",
        )
        ruta_html.write_text(
            generar_html_limpieza(trazabilidad),
            encoding="utf-8",
        )
    except OSError as error:
        raise ErrorInformeLimpieza(
            "No se han podido guardar los informes de limpieza."
        ) from error

    return ruta_json, ruta_html

