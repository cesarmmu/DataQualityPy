"""Bloques V7 para el informe HTML de DataQualityPy.

Este módulo contiene únicamente presentación. No recalcula auditorías,
no ejecuta limpieza y no interpreta una comparación como puntuación.
"""

from __future__ import annotations

from html import escape
from typing import Any

from src.reaudit import ReauditResult
from src.reproducibility import ExecutionManifest


def _texto(valor: Any, defecto: str = "No disponible") -> str:
    if valor is None or valor == "":
        return escape(defecto)
    return escape(str(valor))


def _generar_diagnosticos_html(diagnosticos: list[dict[str, Any]]) -> str:
    if not diagnosticos:
        return ""

    elementos: list[str] = []
    for diagnostico in diagnosticos:
        evidencias = diagnostico.get("evidencias") or []
        evidencias_html = "".join(
            "<li><strong>"
            + _texto(e.get("etiqueta") or e.get("clave"), "Evidencia")
            + ":</strong> "
            + _texto(e.get("valor"))
            + (" <small>(" + _texto(e.get("fuente")) + ")</small>" if e.get("fuente") else "")
            + "</li>"
            for e in evidencias
            if isinstance(e, dict)
        )
        columna = diagnostico.get("columna")
        columna_html = f" · Columna: <strong>{_texto(columna)}</strong>" if columna is not None else ""
        elementos.append(f"""
        <article class="v7-tarjeta">
            <h3>{_texto(diagnostico.get('tipo_incidencia'), 'Diagnóstico')}{columna_html}</h3>
            <p><strong>¿Por qué se ha detectado?</strong><br>{_texto(diagnostico.get('explicacion'))}</p>
            <p><strong>¿Por qué tiene esta severidad?</strong><br>{_texto(diagnostico.get('explicacion_severidad'))}</p>
            {('<p><strong>Evidencias del diagnóstico</strong></p><ul>' + evidencias_html + '</ul>') if evidencias_html else ''}
        </article>
        """)

    return f"""
    <section>
        <h2>Explicabilidad de los diagnósticos</h2>
        <p class="descripcion">Evidencias y explicaciones asociadas a las incidencias detectadas. No constituyen decisiones automáticas de limpieza.</p>
        {''.join(elementos)}
    </section>
    """


def _generar_analisis_avanzado_html(analisis: dict[str, Any]) -> str:
    if not analisis:
        return ""

    columnas = analisis.get("columnas") or {}
    claves = analisis.get("claves_candidatas") or []
    distribuciones = analisis.get("distribuciones") or {}
    relaciones = analisis.get("relaciones") or {}

    return f"""
    <section>
        <h2>Análisis avanzado</h2>
        <p class="descripcion">Observaciones estructurales y contextuales. Una anomalía o discrepancia observada no implica por sí sola que el dato sea incorrecto.</p>
        <div class="datos-generales cuatro-columnas-v7">
            <div><span>Columnas analizadas</span><strong>{len(columnas)}</strong></div>
            <div><span>Claves candidatas</span><strong>{len(claves)}</strong></div>
            <div><span>Distribuciones</span><strong>{len(distribuciones)}</strong></div>
            <div><span>Relaciones</span><strong>{len(relaciones)}</strong></div>
        </div>
    </section>
    """


def _incidencia_breve(incidencia: dict[str, Any]) -> str:
    columna = incidencia.get("columna")
    sufijo = f" · {_texto(columna)}" if columna is not None else ""
    return f"<li><strong>{_texto(incidencia.get('tipo'))}</strong>{sufijo}: {_texto(incidencia.get('mensaje'))}</li>"


def _generar_reauditoria_html(resultado: ReauditResult | None) -> str:
    if resultado is None:
        return ""
    if not isinstance(resultado, ReauditResult):
        raise TypeError("'resultado_reauditoria' debe ser una instancia de ReauditResult.")

    comparacion = resultado.comparison
    resueltas = "".join(_incidencia_breve(i) for i in comparacion.resolved)
    nuevas = "".join(_incidencia_breve(i) for i in comparacion.new)
    persistentes = "".join(
        "<li><strong>" + _texto(c.before.get("tipo")) + "</strong>"
        + (" · " + _texto(c.before.get("columna")) if c.before.get("columna") is not None else "")
        + ": antes " + _texto(c.before.get("cantidad"))
        + " / " + _texto(c.before.get("porcentaje")) + "%"
        + " → después " + _texto(c.after.get("cantidad"))
        + " / " + _texto(c.after.get("porcentaje")) + "%</li>"
        for c in comparacion.persistent
    )

    return f"""
    <section>
        <h2>Limpieza y reauditoría</h2>
        <p class="descripcion">Comparación objetiva entre la auditoría anterior y posterior a la limpieza. Persistente no significa fracaso y una incidencia nueva no se atribuye automáticamente a la limpieza.</p>
        <div class="tarjetas-resumen">
            <div class="tarjeta"><div class="tarjeta-valor">{comparacion.resolved_count}</div><div class="tarjeta-etiqueta">Resueltas</div></div>
            <div class="tarjeta"><div class="tarjeta-valor">{comparacion.persistent_count}</div><div class="tarjeta-etiqueta">Persistentes</div></div>
            <div class="tarjeta"><div class="tarjeta-valor">{comparacion.new_count}</div><div class="tarjeta-etiqueta">Nuevas</div></div>
        </div>
        {('<h3>Resueltas</h3><ul>' + resueltas + '</ul>') if resueltas else ''}
        {('<h3>Persistentes</h3><ul>' + persistentes + '</ul>') if persistentes else ''}
        {('<h3>Nuevas</h3><ul>' + nuevas + '</ul>') if nuevas else ''}
    </section>
    """


def _generar_reproducibilidad_html(manifiesto: ExecutionManifest | None) -> str:
    if manifiesto is None:
        return ""
    if not isinstance(manifiesto, ExecutionManifest):
        raise TypeError("'manifiesto_reproducibilidad' debe ser una instancia de ExecutionManifest.")

    datos = manifiesto.a_dict()
    dataset = datos.get("dataset") or {}
    entorno = datos.get("environment") or {}
    paquetes = entorno.get("packages") or {}
    paquetes_html = "".join(
        f"<li>{_texto(nombre)}: {_texto(version)}</li>"
        for nombre, version in paquetes.items()
    )

    return f"""
    <section>
        <h2>Reproducibilidad</h2>
        <p class="descripcion">Información de trazabilidad de la ejecución. Reproducible no significa automático.</p>
        <div class="datos-generales dos-columnas">
            <div><span>Formato del manifiesto</span><strong>{_texto(datos.get('format_version'))}</strong></div>
            <div><span>Creado</span><strong>{_texto(datos.get('created_at'))}</strong></div>
            <div><span>Dataset</span><strong>{_texto(dataset.get('file_name'))}</strong></div>
            <div><span>SHA-256</span><strong class="v7-hash">{_texto(dataset.get('sha256'))}</strong></div>
            <div><span>DataQualityPy</span><strong>{_texto(entorno.get('dataqualitypy'))}</strong></div>
            <div><span>Python</span><strong>{_texto(entorno.get('python'))}</strong></div>
        </div>
        {('<h3>Paquetes relevantes</h3><ul>' + paquetes_html + '</ul>') if paquetes_html else ''}
    </section>
    """


def generar_bloques_v7_html(
    resultado_auditoria: dict[str, Any],
    *,
    resultado_reauditoria: ReauditResult | None = None,
    manifiesto_reproducibilidad: ExecutionManifest | None = None,
) -> str:
    """Genera los bloques adicionales de presentación introducidos en V7."""
    analisis = resultado_auditoria.get("analisis_avanzado") or {}
    return "".join(
        (
            _generar_analisis_avanzado_html(analisis),
            _generar_diagnosticos_html(analisis.get("diagnosticos") or []),
            _generar_reauditoria_html(resultado_reauditoria),
            _generar_reproducibilidad_html(manifiesto_reproducibilidad),
        )
    )
