"""Pantallas de resultados de DataQualityPy V6."""

from pathlib import Path
from html import escape
import json
import re
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components

from src.html_report import generar_documento_html


ETIQUETAS_CATEGORIAS = {
    "completitud": "Completitud",
    "unicidad": "Unicidad",
    "estructura": "Estructura",
    "consistencia": "Consistencia",
    "validez": "Validez",
}

ETIQUETAS_TIPOS = {
    "numerico": "Numérico",
    "fecha": "Fecha",
    "fecha_hora": "Fecha y hora",
    "booleano_binario": "Booleano/binario",
    "categorico": "Categórico",
    "identificador": "Identificador",
    "texto_libre": "Texto libre",
}

ETIQUETAS_SEVERIDADES = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}

ETIQUETAS_TIPOS_INCIDENCIA = {
    "nulos_reales": "Valores nulos",
    "nulos_textuales": "Posibles nulos textuales",
    "filas_duplicadas": "Filas duplicadas",
    "clave_inexistente": "Clave inexistente",
    "duplicados_clave": "Duplicados según clave",
    "columna_vacia": "Columna vacía",
    "columna_constante": "Columna constante",
    "espacios_texto": "Espacios en texto",
    "inconsistencia_categorica": "Inconsistencia categórica",
    "outliers": "Valores atípicos",
    "incompatibilidad_tipo": "Incompatibilidad de tipo",
    "incumplimiento_regla": "Incumplimiento de regla",
    "conversion_fecha": "Conversión de fecha",
}


def _formatear_etiqueta(valor: str, etiquetas: dict[str, str]) -> str:
    """Devuelve una etiqueta legible garantizando siempre un texto."""

    if valor == "Todas":
        return "Todas"

    return etiquetas.get(valor, valor)



def _imprimir_vista_actual() -> None:
    """Abre el diálogo de impresión del navegador para la vista actual."""

    components.html(
        """
        <script>
            window.parent.print();
        </script>
        """,
        height=0,
        width=0,
    )



def _html_resumen_imprimible(resultado: dict) -> str:
    """Construye una versión del Resumen optimizada para impresión."""

    dataset = resultado["dataset"]
    resumen = resultado["resumen"]
    severidades = resumen["por_severidad"]
    cobertura = resumen["cobertura_auditoria"]

    def grafico_barras_vertical(
        datos: dict,
        etiquetas: dict[str, str],
        etiqueta_y: str,
    ) -> str:
        """Crea un gráfico de barras vertical para la impresión."""

        if etiqueta_y == "Incidencias":
            orden = [
                "completitud",
                "consistencia",
                "estructura",
                "unicidad",
                "validez",
            ]
        else:
            orden = [
                "booleano_binario",
                "categorico",
                "fecha",
                "fecha_hora",
                "identificador",
                "numerico",
                "texto_libre",
            ]

        elementos = [
            (
                escape(etiquetas.get(clave, clave)),
                int(datos.get(clave, 0)),
            )
            for clave in orden
        ]

        if not elementos:
            return '<div>Sin datos</div>'

        ancho = 560
        alto = 285
        margen_izq = 45
        margen_der = 12
        margen_sup = 20
        margen_inf = 82
        ancho_plot = ancho - margen_izq - margen_der
        alto_plot = alto - margen_sup - margen_inf

        maximo_datos = max(cantidad for _, cantidad in elementos)
        maximo_eje = max(1, maximo_datos)

        # Escala sencilla de enteros para conservar la lectura del gráfico.
        divisiones = min(4, maximo_eje)
        paso_x = ancho_plot / len(elementos)
        ancho_barra = min(76, paso_x * 0.76)

        svg = [
            f'<svg class="dq-print-chart" viewBox="0 0 {ancho} {alto}" '
            'role="img" aria-label="Gráfico de barras">'
        ]

        for i in range(divisiones + 1):
            valor = maximo_eje * i / divisiones
            y = margen_sup + alto_plot - (alto_plot * i / divisiones)

            svg.append(
                f'<line x1="{margen_izq}" y1="{y:.2f}" '
                f'x2="{ancho - margen_der}" y2="{y:.2f}" '
                'class="dq-chart-grid"/>'
            )

            etiqueta_tick = (
                str(int(round(valor)))
                if abs(valor - round(valor)) < 0.001
                else f"{valor:.1f}"
            )
            svg.append(
                f'<text x="{margen_izq - 8}" y="{y + 4:.2f}" '
                'text-anchor="end" class="dq-chart-tick">'
                f'{etiqueta_tick}</text>'
            )

        svg.append(
            f'<line x1="{margen_izq}" y1="{margen_sup}" '
            f'x2="{margen_izq}" y2="{margen_sup + alto_plot}" '
            'class="dq-chart-axis"/>'
        )
        svg.append(
            f'<line x1="{margen_izq}" y1="{margen_sup + alto_plot}" '
            f'x2="{ancho - margen_der}" y2="{margen_sup + alto_plot}" '
            'class="dq-chart-axis"/>'
        )

        for indice, (etiqueta, cantidad) in enumerate(elementos):
            centro_x = margen_izq + paso_x * (indice + 0.5)
            altura_barra = alto_plot * cantidad / maximo_eje
            y_barra = margen_sup + alto_plot - altura_barra
            x_barra = centro_x - ancho_barra / 2

            if cantidad > 0:
                svg.append(
                    f'<rect x="{x_barra:.2f}" y="{y_barra:.2f}" '
                    f'width="{ancho_barra:.2f}" height="{altura_barra:.2f}" '
                    'rx="2" class="dq-chart-bar"/>'
                )

            if cantidad > 0:
                valor_y = max(margen_sup + 11, y_barra - 6)
                svg.append(
                    f'<text x="{centro_x:.2f}" y="{valor_y:.2f}" '
                    'text-anchor="middle" class="dq-chart-value">'
                    f'{cantidad}</text>'
                )

            etiqueta_x = centro_x
            etiqueta_y_pos = margen_sup + alto_plot + 17
            svg.append(
                f'<text x="{etiqueta_x:.2f}" y="{etiqueta_y_pos:.2f}" '
                f'transform="rotate(-90 {etiqueta_x:.2f} {etiqueta_y_pos:.2f})" '
                'text-anchor="end" class="dq-chart-label">'
                f'{etiqueta}</text>'
            )

        svg.append("</svg>")
        return "".join(svg)

    incidencias_html = []

    for incidencia in resumen["principales_incidencias"]:
        severidad = escape(
            ETIQUETAS_SEVERIDADES.get(
                incidencia.get("severidad", ""),
                str(incidencia.get("severidad", "")),
            )
        )
        mensaje = escape(str(incidencia.get("mensaje", "")))

        incidencias_html.append(
            f"""
            <div class="dq-print-incident">
                <strong>{severidad.upper()}</strong>
                <span>{mensaje}</span>
            </div>
            """
        )

    if not incidencias_html:
        incidencias_html.append(
            '<div class="dq-print-incident">No se han detectado incidencias.</div>'
        )

    return dedent(f"""
<style>
    .dq-print-summary {{
        display: none;
    }}

    @media print {{
        body * {{
            visibility: hidden !important;
        }}

        .dq-print-summary,
        .dq-print-summary * {{
            visibility: visible !important;
        }}

        .dq-print-summary {{
            display: block !important;
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
            color: #172033 !important;
            background: #ffffff !important;
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 10.5pt !important;
            line-height: 1.35 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        .dq-print-summary h1 {{
            margin: 0 0 2px !important;
            font-size: 22pt !important;
        }}

        .dq-print-summary h2 {{
            margin: 14px 0 7px !important;
            font-size: 14pt !important;
        }}

        .dq-print-subtitle,
        .dq-print-dataset {{
            color: #657084 !important;
        }}

        .dq-print-dataset {{
            margin-bottom: 14px !important;
        }}

        .dq-print-metrics {{
            display: grid !important;
            grid-template-columns: repeat(4, 1fr) !important;
            gap: 8px !important;
        }}

        .dq-print-metric {{
            border: 1px solid #d9e0ea !important;
            border-radius: 7px !important;
            padding: 8px 10px !important;
            break-inside: avoid !important;
        }}

        .dq-print-metric strong {{
            display: block !important;
            font-size: 17pt !important;
        }}

        .dq-print-distributions {{
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 18px !important;
        }}

        .dq-print-block {{
            break-inside: avoid !important;
        }}

        .dq-print-chart {{
            display: block !important;
            width: 100% !important;
            height: auto !important;
            overflow: visible !important;
        }}

        .dq-chart-grid {{
            stroke: #dfe5ec !important;
            stroke-width: 1 !important;
        }}

        .dq-chart-axis {{
            stroke: #8b95a5 !important;
            stroke-width: 1 !important;
        }}

        .dq-chart-bar {{
            fill: #4c83b6 !important;
        }}

        .dq-chart-tick,
        .dq-chart-label,
        .dq-chart-axis-title {{
            fill: #4b5565 !important;
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 11px !important;
        }}

        .dq-chart-value {{
            fill: #172033 !important;
            font-family: Arial, Helvetica, sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
        }}

        .dq-print-bar-row {{
            margin-bottom: 6px !important;
        }}

        .dq-print-bar-head {{
            display: flex !important;
            justify-content: space-between !important;
            margin-bottom: 2px !important;
        }}

        .dq-print-bar-bg {{
            display: block !important;
            width: 100% !important;
            height: 9px !important;
            border-radius: 5px !important;
            background: #e8edf3 !important;
            overflow: hidden !important;
        }}

        .dq-print-bar-value {{
            display: block !important;
            min-height: 9px !important;
            border-radius: 5px !important;
            background: #4c83b6 !important;
        }}

        .dq-print-incident {{
            margin-bottom: 6px !important;
            padding: 7px 9px !important;
            border-left: 3px solid #4c83b6 !important;
            background: #f6f8fb !important;
            break-inside: avoid !important;
        }}

        .dq-print-incident strong {{
            margin-right: 5px !important;
        }}

        .dq-print-coverage {{
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 8px !important;
        }}

        @page {{
            size: A4;
            margin: 14mm;
        }}
    }}
</style>

<div class="dq-print-summary">
    <h1>DATAQUALITYPY</h1>
    <div class="dq-print-subtitle">
        Resumen de auditoría de calidad de datos
    </div>
    <div class="dq-print-dataset">
        {escape(str(dataset["archivo"]))} ·
        {dataset["filas"]} filas ·
        {dataset["columnas"]} columnas
    </div>

    <h2>Resumen de incidencias</h2>
    <div class="dq-print-metrics">
        <div class="dq-print-metric">
            <strong>{resumen["total_incidencias"]}</strong>Incidencias
        </div>
        <div class="dq-print-metric">
            <strong>{severidades["alta"]}</strong>Altas
        </div>
        <div class="dq-print-metric">
            <strong>{severidades["media"]}</strong>Medias
        </div>
        <div class="dq-print-metric">
            <strong>{severidades["baja"]}</strong>Bajas
        </div>
    </div>

    <div class="dq-print-distributions">
        <div class="dq-print-block">
            <h2>Incidencias por categoría</h2>
            {grafico_barras_vertical(resumen["por_categoria"], ETIQUETAS_CATEGORIAS, "Incidencias")}
        </div>
        <div class="dq-print-block">
            <h2>Tipos semánticos</h2>
            {grafico_barras_vertical(resumen["tipos_semanticos"], ETIQUETAS_TIPOS, "Columnas")}
        </div>
    </div>

    <div class="dq-print-block">
        <h2>Principales incidencias</h2>
        {"".join(incidencias_html)}
    </div>

    <div class="dq-print-block">
        <h2>Cobertura de auditoría</h2>
        <div class="dq-print-coverage">
            <div class="dq-print-metric">
                <strong>{len(cobertura["controles_aplicados"])}</strong>
                Controles aplicados
            </div>
            <div class="dq-print-metric">
                <strong>{len(cobertura["controles_no_aplicables"])}</strong>
                No aplicables
            </div>
            <div class="dq-print-metric">
                <strong>{len(cobertura["controles_no_configurados"])}</strong>
                No configurados
            </div>
        </div>
    </div>
</div>
""")


def _boton_imprimir_resumen(resultado: dict) -> None:
    """Muestra un botón de impresión cuyo clic abre directamente la vista imprimible."""

    contenido = _html_resumen_imprimible(resultado)

    documento = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>DataQualityPy_Resumen</title>
<style>
    html, body {{
        margin: 0;
        padding: 0;
        background: #ffffff;
    }}

    @media print {{
        @page {{
            size: A4;
            margin: 14mm;
        }}
    }}
</style>
</head>
<body>
{contenido}
<script>
    window.onload = function() {{
        window.focus();
        setTimeout(function() {{
            window.print();
            setTimeout(function() {{
                window.close();
            }}, 150);
        }}, 150);
    }};
</script>
</body>
</html>"""

    documento_json = json.dumps(documento).replace("</", "<\\/")

    components.html(
        f"""
        <button id="dq-print-summary-button"
                onclick="imprimirResumen()"
                class="dq-print-button">
            🖨️ Imprimir resumen
        </button>

        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color-scheme: dark;
                font-family:
                    "Source Sans 3",
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;
            }}

            .dq-print-button {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.35rem;
                min-height: 38px;
                padding: 0.45rem 0.85rem;
                border: 1px solid rgba(250, 250, 250, 0.20);
                border-radius: 0.5rem;
                background: rgb(38, 39, 48);
                color: rgb(250, 250, 250);
                font-family: inherit;
                font-size: 14px;
                font-weight: 400;
                line-height: 1.2;
                white-space: nowrap;
                cursor: pointer;
                transition:
                    border-color 120ms ease,
                    background-color 120ms ease;
            }}

            .dq-print-button:hover {{
                border-color: rgba(250, 250, 250, 0.38);
                background: rgb(49, 51, 63);
            }}

            .dq-print-button:active {{
                background: rgb(58, 60, 73);
            }}

            .dq-print-button:focus-visible {{
                outline: 2px solid rgba(117, 183, 246, 0.9);
                outline-offset: 2px;
            }}
        </style>

        <script>
            function imprimirResumen() {{
                const contenido = {documento_json};
                const ventana = window.open("", "_blank");

                if (!ventana) {{
                    alert("El navegador ha bloqueado la ventana de impresión.");
                    return;
                }}

                ventana.document.open();
                ventana.document.write(contenido);
                ventana.document.close();
            }}
        </script>
        """,
        height=50,
        width=220,
    )




def _html_incidencias_imprimible(
    resultado: dict,
    incidencias: list[dict],
    severidad: str,
    categoria: str,
    columna: str,
) -> str:
    """Construye la vista imprimible de Incidencias."""

    dataset = resultado["dataset"]

    total = len(incidencias)
    altas = sum(1 for item in incidencias if item["severidad"] == "alta")
    medias = sum(1 for item in incidencias if item["severidad"] == "media")
    bajas = sum(1 for item in incidencias if item["severidad"] == "baja")

    filas = []
    for item in incidencias:
        porcentaje = item.get("porcentaje")
        porcentaje_texto = (
            f"{porcentaje:.2f} %"
            if porcentaje is not None
            else "—"
        )

        filas.append(
            f"""
            <tr>
                <td>{escape(str(ETIQUETAS_TIPOS_INCIDENCIA.get(item["tipo"], item["tipo"])))}</td>
                <td>{escape(str(ETIQUETAS_CATEGORIAS.get(item["categoria"], item["categoria"])))}</td>
                <td>{escape(str(ETIQUETAS_SEVERIDADES.get(item["severidad"], item["severidad"])))}</td>
                <td>{escape(str(item["columna"] or "General"))}</td>
                <td>{escape(str(item["cantidad"] if item["cantidad"] is not None else "—"))}</td>
                <td>{escape(porcentaje_texto)}</td>
            </tr>
            """
        )

    if filas:
        tabla = f"""
        <table class="dq-print-table">
            <thead>
                <tr>
                    <th>Tipo</th>
                    <th>Categoría</th>
                    <th>Severidad</th>
                    <th>Columna</th>
                    <th>Cantidad</th>
                    <th>Porcentaje</th>
                </tr>
            </thead>
            <tbody>
                {"".join(filas)}
            </tbody>
        </table>
        """
    else:
        tabla = (
            '<div class="dq-print-info">'
            'No hay incidencias que coincidan con los filtros seleccionados.'
            '</div>'
        )

    detalle_html = ""
    if incidencias:
        indice = st.session_state.get("detalle_incidencia", 0)
        try:
            indice = int(indice)
        except (TypeError, ValueError):
            indice = 0

        indice = max(0, min(indice, len(incidencias) - 1))
        item = incidencias[indice]

        cantidad = (
            str(item["cantidad"])
            if item["cantidad"] is not None
            else "—"
        )
        porcentaje = (
            f'{item["porcentaje"]:.2f} %'
            if item["porcentaje"] is not None
            else "—"
        )

        detalle_html = f"""
        <section class="dq-print-section">
            <h2>Detalle de incidencia</h2>

            <div class="dq-print-detail-grid">
                <div>
                    <span>Tipo</span>
                    <strong>{escape(str(ETIQUETAS_TIPOS_INCIDENCIA.get(item["tipo"], item["tipo"])))}</strong>
                </div>
                <div>
                    <span>Categoría</span>
                    <strong>{escape(str(ETIQUETAS_CATEGORIAS.get(item["categoria"], item["categoria"])))}</strong>
                </div>
                <div>
                    <span>Severidad</span>
                    <strong>{escape(str(ETIQUETAS_SEVERIDADES.get(item["severidad"], item["severidad"])))}</strong>
                </div>
            </div>

            <div class="dq-print-detail-line">
                <strong>Columna:</strong> {escape(str(item["columna"] or "General"))}
            </div>
            <div class="dq-print-detail-line">
                <strong>Cantidad afectada:</strong> {escape(cantidad)}
            </div>
            <div class="dq-print-detail-line">
                <strong>Porcentaje:</strong> {escape(porcentaje)}
            </div>

            <div class="dq-print-message">
                {escape(str(item["mensaje"]))}
            </div>
        </section>
        """

    filtro_severidad = (
        "Todas"
        if severidad == "Todas"
        else ETIQUETAS_SEVERIDADES.get(severidad, severidad)
    )
    filtro_categoria = (
        "Todas"
        if categoria == "Todas"
        else ETIQUETAS_CATEGORIAS.get(categoria, categoria)
    )

    return dedent(f"""
    <style>
        .dq-print-incidents {{
            color: #172033;
            background: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10.5pt;
            line-height: 1.35;
        }}

        .dq-print-incidents h1 {{
            margin: 0 0 2px;
            font-size: 22pt;
        }}

        .dq-print-incidents h2 {{
            margin: 14px 0 7px;
            font-size: 14pt;
        }}

        .dq-print-subtitle,
        .dq-print-dataset {{
            color: #657084;
        }}

        .dq-print-dataset {{
            margin-bottom: 14px;
        }}

        .dq-print-metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }}

        .dq-print-metric {{
            border: 1px solid #d9e0ea;
            border-radius: 7px;
            padding: 8px 10px;
            break-inside: avoid;
        }}

        .dq-print-metric strong {{
            display: block;
            font-size: 17pt;
        }}

        .dq-print-filters {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }}

        .dq-print-filter {{
            border: 1px solid #d9e0ea;
            border-radius: 7px;
            padding: 7px 9px;
        }}

        .dq-print-filter span,
        .dq-print-detail-grid span {{
            display: block;
            color: #657084;
            font-size: 8.5pt;
            margin-bottom: 2px;
        }}

        .dq-print-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
        }}

        .dq-print-table th {{
            text-align: left;
            background: #f1f4f8;
            border: 1px solid #d9e0ea;
            padding: 6px;
        }}

        .dq-print-table td {{
            border: 1px solid #d9e0ea;
            padding: 6px;
            vertical-align: top;
        }}

        .dq-print-section {{
            break-inside: avoid;
        }}

        .dq-print-detail-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 8px;
        }}

        .dq-print-detail-grid > div {{
            border: 1px solid #d9e0ea;
            border-radius: 7px;
            padding: 7px 9px;
        }}

        .dq-print-detail-line {{
            margin: 5px 0;
        }}

        .dq-print-message,
        .dq-print-info {{
            margin-top: 8px;
            padding: 8px 10px;
            border-left: 3px solid #4c83b6;
            background: #f6f8fb;
        }}

        @media print {{
            .dq-print-incidents {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            @page {{
                size: A4;
                margin: 14mm;
            }}
        }}
    </style>

    <div class="dq-print-incidents">
        <h1>DATAQUALITYPY</h1>
        <div class="dq-print-subtitle">
            Incidencias de auditoría de calidad de datos
        </div>
        <div class="dq-print-dataset">
            {escape(str(dataset["archivo"]))} ·
            {dataset["filas"]} filas ·
            {dataset["columnas"]} columnas
        </div>

        <h2>Resumen de incidencias</h2>
        <div class="dq-print-metrics">
            <div class="dq-print-metric"><strong>{total}</strong>Incidencias</div>
            <div class="dq-print-metric"><strong>{altas}</strong>Altas</div>
            <div class="dq-print-metric"><strong>{medias}</strong>Medias</div>
            <div class="dq-print-metric"><strong>{bajas}</strong>Bajas</div>
        </div>

        <section class="dq-print-section">
            <h2>Filtros aplicados</h2>
            <div class="dq-print-filters">
                <div class="dq-print-filter">
                    <span>Severidad</span>
                    <strong>{escape(str(filtro_severidad))}</strong>
                </div>
                <div class="dq-print-filter">
                    <span>Categoría</span>
                    <strong>{escape(str(filtro_categoria))}</strong>
                </div>
                <div class="dq-print-filter">
                    <span>Columna</span>
                    <strong>{escape(str(columna))}</strong>
                </div>
            </div>
        </section>

        <section class="dq-print-section">
            <h2>Listado de incidencias</h2>
            {tabla}
        </section>

        {detalle_html}
    </div>
    """)


def _boton_imprimir_incidencias(
    resultado: dict,
    incidencias: list[dict],
    severidad: str,
    categoria: str,
    columna: str,
) -> None:
    """Botón e impresión específica para la pestaña Incidencias."""

    contenido = _html_incidencias_imprimible(
        resultado,
        incidencias,
        severidad,
        categoria,
        columna,
    )

    documento = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>DataQualityPy_Incidencias</title>
<style>
    html, body {{
        margin: 0;
        padding: 0;
        background: #ffffff;
    }}
</style>
</head>
<body>
{contenido}
<script>
    window.onload = function() {{
        window.focus();
        setTimeout(function() {{
            window.print();
            setTimeout(function() {{
                window.close();
            }}, 150);
        }}, 150);
    }};
</script>
</body>
</html>"""

    documento_json = json.dumps(documento).replace("</", "<\\/")

    components.html(
        f"""
        <button onclick="imprimirIncidencias()" class="dq-print-button">
            🖨️ Imprimir incidencias
        </button>

        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color-scheme: dark;
                font-family:
                    "Source Sans 3",
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;
            }}

            .dq-print-button {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.35rem;
                min-height: 38px;
                padding: 0.45rem 0.85rem;
                border: 1px solid rgba(250, 250, 250, 0.20);
                border-radius: 0.5rem;
                background: rgb(38, 39, 48);
                color: rgb(250, 250, 250);
                font-family: inherit;
                font-size: 14px;
                font-weight: 400;
                line-height: 1.2;
                white-space: nowrap;
                cursor: pointer;
                transition:
                    border-color 120ms ease,
                    background-color 120ms ease;
            }}

            .dq-print-button:hover {{
                border-color: rgba(250, 250, 250, 0.38);
                background: rgb(49, 51, 63);
            }}

            .dq-print-button:active {{
                background: rgb(58, 60, 73);
            }}

            .dq-print-button:focus-visible {{
                outline: 2px solid rgba(117, 183, 246, 0.9);
                outline-offset: 2px;
            }}
        </style>

        <script>
            function imprimirIncidencias() {{
                const contenido = {documento_json};
                const ventana = window.open("", "_blank");

                if (!ventana) {{
                    alert("El navegador ha bloqueado la ventana de impresión.");
                    return;
                }}

                ventana.document.open();
                ventana.document.write(contenido);
                ventana.document.close();
            }}
        </script>
        """,
        height=50,
        width=230,
    )



def _preparar_html_informe_para_impresion(html: str) -> str:
    """Adapta el HTML autónomo existente a una salida A4 imprimible."""

    estilos_impresion = """
    <style id="dq-print-full-report">
        @page {
            size: A4;
            margin: 14mm;
        }

        @media print {
            h1, h2, h3, h4, h5, h6 {
                break-after: avoid-page !important;
                page-break-after: avoid !important;
            }

            h1 + *, h2 + *, h3 + *, h4 + *, h5 + *, h6 + * {
                break-before: avoid-page !important;
                page-break-before: avoid !important;
            }

            table {
                break-inside: avoid-page !important;
                page-break-inside: avoid !important;
            }

            thead {
                display: table-header-group;
            }

            tr, .card, .metric-card, .summary-card, .section-card {
                break-inside: avoid-page !important;
                page-break-inside: avoid !important;
            }
            
            .dq-keep-together-print {
                break-inside: avoid-page !important;
                page-break-inside: avoid !important;
            }
            html,
            body {
                width: auto !important;
                min-width: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                background: #ffffff !important;
                color: #172033 !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            body {
                font-size: 9.5pt !important;
                line-height: 1.32 !important;
            }

            main,
            .container,
            .content,
            .report,
            .report-container,
            .page,
            section,
            article {
                max-width: none !important;
                width: auto !important;
            }

            h1 {
                font-size: 22pt !important;
                margin-top: 0 !important;
            }

            /* Cabecera del informe: compacta para aprovechar la primera página. */
            header.cabecera {
                padding: 14px 18px !important;
                margin: 0 0 10px 0 !important;
                min-height: 0 !important;
                break-inside: avoid-page !important;
                page-break-inside: avoid !important;
            }

            header.cabecera h1 {
                margin: 0 0 4px 0 !important;
                font-size: 20pt !important;
                line-height: 1.05 !important;
            }

            header.cabecera p {
                margin: 2px 0 !important;
                line-height: 1.15 !important;
            }

            /* Tipos semánticos comienza expresamente en una página nueva. */
            .dq-start-new-page-print {
                break-before: page !important;
                page-break-before: always !important;
            }

            h2 {
                font-size: 15pt !important;
            }

            h3 {
                font-size: 11.5pt !important;
            }

            table {
                width: 100% !important;
                max-width: 100% !important;
                table-layout: auto !important;
                font-size: 8pt !important;
            }

            th,
            td {
                padding: 4px 5px !important;
                overflow-wrap: anywhere !important;
                word-break: normal !important;
            }

            pre,
            code {
                white-space: pre-wrap !important;
                overflow-wrap: anywhere !important;
            }

            .card,
            .metric,
            .panel,
            .section,
            table,
            tr,
            figure {
                break-inside: avoid;
                page-break-inside: avoid;
            }

            a {
                color: inherit !important;
                text-decoration: none !important;
            }

            * {
                box-shadow: none !important;
            }
        }
    </style>
    """

    if "</head>" in html:
        html = html.replace(
            "</head>",
            estilos_impresion + "\n</head>",
            1,
        )
    else:
        html = estilos_impresion + html

    # Nombre de la pestaña/documento de impresión.
    if re.search(r"<title>.*?</title>", html, flags=re.I | re.S):
        html = re.sub(
            r"<title>.*?</title>",
            "<title>DataQualityPy_Informe_Completo</title>",
            html,
            count=1,
            flags=re.I | re.S,
        )
    elif "<head>" in html:
        html = html.replace(
            "<head>",
            "<head><title>DataQualityPy_Informe_Completo</title>",
            1,
        )

    # Al cerrar el diálogo de impresión (guardar o cancelar), cerramos
    # la pestaña auxiliar y regresamos a DataQualityPy.
    script_cierre = """
    <script id="dq-print-full-report-script">
        (function () {
            let impresionLanzada = false;

            function marcarBloqueTiposSemanticos() {
                const titulos = Array.from(
                    document.querySelectorAll("h1, h2, h3, h4, h5, h6")
                );

                const titulo = titulos.find(function (elemento) {
                    return elemento.textContent.trim() === "Tipos semánticos";
                });

                if (!titulo) {
                    return;
                }

                /*
                 * En el HTML autónomo, "Resumen ejecutivo", "Principales
                 * incidencias" y "Tipos semánticos" pertenecen a la misma
                 * sección. No debemos mover toda la sección: solo marcamos
                 * el propio título de Tipos semánticos para que empiece
                 * expresamente una página nueva.
                 *
                 * El conjunto título + tarjetas se mantiene unido mediante
                 * las reglas de encabezados y tarjetas ya existentes.
                 */
                titulo.classList.add("dq-start-new-page-print");
            }

            function cerrarVentana() {
                setTimeout(function () {
                    window.close();
                }, 150);
            }

            window.addEventListener("afterprint", cerrarVentana);

            window.addEventListener("load", function () {
                if (impresionLanzada) {
                    return;
                }

                impresionLanzada = true;
                marcarBloqueTiposSemanticos();

                setTimeout(function () {
                    window.focus();
                    window.print();
                }, 350);
            });
        })();
    </script>
    """

    if "</body>" in html:
        html = html.replace(
            "</body>",
            script_cierre + "\n</body>",
            1,
        )
    else:
        html += script_cierre

    return html


def _boton_imprimir_informe_completo(html: str) -> None:
    """Muestra el botón normalizado de impresión del informe completo."""

    documento = _preparar_html_informe_para_impresion(html)
    documento_json = json.dumps(documento).replace("</", "<\\/")

    components.html(
        f"""
        <button onclick="imprimirInformeCompleto()" class="dq-print-button">
            🖨️ Imprimir informe completo
        </button>

        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color-scheme: dark;
                font-family:
                    "Source Sans 3",
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;
            }}

            .dq-print-button {{
                display: flex;
                width: 100%;
                box-sizing: border-box;
                align-items: center;
                justify-content: center;
                gap: 0.35rem;
                min-height: 38px;
                padding: 0.45rem 0.85rem;
                border: 1px solid rgba(250, 250, 250, 0.20);
                border-radius: 0.5rem;
                background: rgb(38, 39, 48);
                color: rgb(250, 250, 250);
                font-family: inherit;
                font-size: 14px;
                font-weight: 400;
                line-height: 1.2;
                white-space: nowrap;
                cursor: pointer;
                transition:
                    border-color 120ms ease,
                    background-color 120ms ease;
            }}

            .dq-print-button:hover {{
                border-color: rgba(250, 250, 250, 0.38);
                background: rgb(49, 51, 63);
            }}

            .dq-print-button:active {{
                background: rgb(58, 60, 73);
            }}

            .dq-print-button:focus-visible {{
                outline: 2px solid rgba(117, 183, 246, 0.9);
                outline-offset: 2px;
            }}
        </style>

        <script>
            function imprimirInformeCompleto() {{
                const contenido = {documento_json};
                const ventana = window.open("", "_blank");

                if (!ventana) {{
                    alert("El navegador ha bloqueado la ventana de impresión.");
                    return;
                }}

                ventana.document.open();
                ventana.document.write(contenido);
                ventana.document.close();
            }}
        </script>
        """,
        height=50,
        width=None,
    )



def _mostrar_cabecera(resultado: dict) -> None:
    """Muestra la identificación general de la auditoría."""

    dataset = resultado["dataset"]

    st.title("DataQualityPy")
    st.caption("Auditor de calidad de datos")

    st.write(f"📄 **{dataset['archivo']}**")

    hoja = st.session_state.get("hoja_auditoria")
    if hoja is not None:
        st.write(f"📑 **Hoja:** {hoja}")

    st.caption(
        f"{dataset['filas']} filas · "
        f"{dataset['columnas']} columnas"
    )


def _tarjeta_indicador(
    etiqueta: str,
    valor: object,
    color_acento: str | None = None,
) -> str:
    """Construye una tarjeta visual para un indicador ya calculado."""

    borde_acento = (
        f"border-left:4px solid {color_acento};"
        if color_acento
        else ""
    )

    # El HTML se mantiene en una sola línea para evitar que Markdown
    # interprete las propiedades CSS indentadas como bloques de código.
    return (
        f'<div style="border:1px solid rgba(128,128,128,0.35);'
        f'{borde_acento}border-radius:8px;padding:14px 16px;'
        f'min-height:86px;box-sizing:border-box;">'
        f'<div style="font-size:1.65rem;font-weight:700;line-height:1.15;'
        f'margin-bottom:5px;">{escape(str(valor))}</div>'
        f'<div style="font-size:0.9rem;opacity:0.78;">'
        f'{escape(etiqueta)}</div></div>'
    )


def _mostrar_tarjetas_resumen(resumen: dict) -> None:
    """Muestra los principales indicadores de incidencias como tarjetas."""

    severidades = resumen["por_severidad"]

    tarjetas = (
        ("Incidencias", resumen["total_incidencias"], None),
        ("Altas", severidades["alta"], "#d9534f"),
        ("Medias", severidades["media"], "#d99a1b"),
        ("Bajas", severidades["baja"], "#4c83b6"),
    )

    for columna, (etiqueta, valor, color) in zip(st.columns(4), tarjetas):
        with columna:
            st.markdown(
                _tarjeta_indicador(etiqueta, valor, color),
                unsafe_allow_html=True,
            )


def _mostrar_distribucion(
    datos: dict,
    etiquetas: dict,
) -> None:
    """Representa visualmente una distribución ya calculada por V3."""

    maximo = max(datos.values(), default=0)

    for clave, cantidad in datos.items():
        etiqueta = etiquetas.get(clave, clave)

        columna_etiqueta, columna_valor = st.columns([4, 1])

        with columna_etiqueta:
            st.write(etiqueta)

        with columna_valor:
            st.write(f"**{cantidad}**")

        proporcion = (
            cantidad / maximo
            if maximo > 0
            else 0.0
        )

        st.progress(proporcion)


def _mostrar_distribuciones(resumen: dict) -> None:
    """Muestra como gráficos las distribuciones ya calculadas por V3."""

    datos_categorias = {
        ETIQUETAS_CATEGORIAS.get(clave, clave): cantidad
        for clave, cantidad in resumen["por_categoria"].items()
    }

    datos_tipos = {
        ETIQUETAS_TIPOS.get(clave, clave): cantidad
        for clave, cantidad in resumen["tipos_semanticos"].items()
    }

    columna_categorias, columna_tipos = st.columns(2)

    with columna_categorias:
        st.markdown("### Incidencias por categoría")
        st.bar_chart(
            datos_categorias,
            x_label="Categoría",
            y_label="Incidencias",
        )

    with columna_tipos:
        st.markdown("### Tipos semánticos")
        st.bar_chart(
            datos_tipos,
            x_label="Tipo semántico",
            y_label="Columnas",
        )


def _mostrar_principales_incidencias(resumen: dict) -> None:
    """Muestra las incidencias principales seleccionadas por V3."""

    st.markdown("### Principales incidencias")

    incidencias = resumen["principales_incidencias"]

    if not incidencias:
        st.success("No se han detectado incidencias.")
        return

    st.dataframe(
        incidencias,
        use_container_width=True,
        hide_index=True,
    )


def _mostrar_cobertura_resumida(resumen: dict) -> None:
    """Muestra el resumen de cobertura generado por V3 como tarjetas."""

    st.markdown("### Cobertura de auditoría")

    cobertura = resumen["cobertura_auditoria"]

    tarjetas = (
        ("Controles aplicados", len(cobertura["controles_aplicados"]), "#4c83b6"),
        ("No aplicables", len(cobertura["controles_no_aplicables"]), None),
        ("No configurados", len(cobertura["controles_no_configurados"]), None),
    )

    for columna, (etiqueta, valor, color) in zip(st.columns(3), tarjetas):
        with columna:
            st.markdown(
                _tarjeta_indicador(etiqueta, valor, color),
                unsafe_allow_html=True,
            )


def _mostrar_resumen(resultado: dict) -> None:
    """Muestra la pestaña Resumen."""

    resumen = resultado["resumen"]

    st.markdown("## Resumen de auditoría")

    _mostrar_tarjetas_resumen(resumen)

    st.divider()

    _mostrar_distribuciones(resumen)

    st.divider()

    _mostrar_principales_incidencias(resumen)

    st.divider()

    _mostrar_cobertura_resumida(resumen)

    st.divider()

    _boton_imprimir_resumen(resultado)


def _filtrar_incidencias(
    incidencias: list[dict],
    severidad: str,
    categoria: str,
    columna: str,
) -> list[dict]:
    """Filtra incidencias sin modificar los resultados de la auditoría."""

    resultado = incidencias

    if severidad != "Todas":
        resultado = [
            incidencia
            for incidencia in resultado
            if incidencia["severidad"] == severidad
        ]

    if categoria != "Todas":
        resultado = [
            incidencia
            for incidencia in resultado
            if incidencia["categoria"] == categoria
        ]

    if columna != "Todas":
        if columna == "General":
            resultado = [
                incidencia
                for incidencia in resultado
                if incidencia["columna"] is None
            ]
        else:
            resultado = [
                incidencia
                for incidencia in resultado
                if incidencia["columna"] == columna
            ]

    return resultado


def _preparar_incidencias_tabla(
    incidencias: list[dict],
) -> list[dict]:
    """Prepara las incidencias para su presentación en la interfaz."""

    filas = []

    for incidencia in incidencias:
        porcentaje = incidencia["porcentaje"]

        filas.append(
            {
                "Tipo": ETIQUETAS_TIPOS_INCIDENCIA.get(
                    incidencia["tipo"],
                    incidencia["tipo"],
                ),
                "Categoría": ETIQUETAS_CATEGORIAS.get(
                    incidencia["categoria"],
                    incidencia["categoria"],
                ),
                "Severidad": ETIQUETAS_SEVERIDADES.get(
                    incidencia["severidad"],
                    incidencia["severidad"],
                ),
                "Columna": (
                    incidencia["columna"]
                    if incidencia["columna"] is not None
                    else "General"
                ),
                "Cantidad": incidencia["cantidad"],
                "Porcentaje": (
                    f"{porcentaje:.2f} %"
                    if porcentaje is not None
                    else ""
                ),
                "Mensaje": incidencia["mensaje"],
            }
        )

    return filas


def _mostrar_contadores_incidencias(
    incidencias: list[dict],
) -> None:
    """Muestra los contadores de incidencias por severidad."""

    total = len(incidencias)
    altas = sum(
        1
        for incidencia in incidencias
        if incidencia["severidad"] == "alta"
    )
    medias = sum(
        1
        for incidencia in incidencias
        if incidencia["severidad"] == "media"
    )
    bajas = sum(
        1
        for incidencia in incidencias
        if incidencia["severidad"] == "baja"
    )

    tarjetas = (
        ("Incidencias", total, None),
        ("Altas", altas, "#d9534f"),
        ("Medias", medias, "#d99a1b"),
        ("Bajas", bajas, "#4c83b6"),
    )

    for columna, (etiqueta, valor, color) in zip(st.columns(4), tarjetas):
        with columna:
            st.markdown(
                _tarjeta_indicador(etiqueta, valor, color),
                unsafe_allow_html=True,
            )


def _mostrar_filtros_incidencias(
    incidencias: list[dict],
) -> tuple[str, str, str]:
    """Muestra los filtros disponibles para las incidencias."""

    categorias_presentes = sorted(
        {
            incidencia["categoria"]
            for incidencia in incidencias
        }
    )

    columnas_presentes = sorted(
        {
            incidencia["columna"]
            for incidencia in incidencias
            if incidencia["columna"] is not None
        }
    )

    hay_incidencias_generales = any(
        incidencia["columna"] is None
        for incidencia in incidencias
    )

    opciones_severidad = [
        "Todas",
        "alta",
        "media",
        "baja",
    ]

    opciones_categoria = [
        "Todas",
        *categorias_presentes,
    ]

    opciones_columna = ["Todas"]

    if hay_incidencias_generales:
        opciones_columna.append("General")

    opciones_columna.extend(columnas_presentes)

    columna_severidad, columna_categoria, columna_columna = st.columns(3)

    with columna_severidad:
        severidad = st.selectbox(
            "Severidad",
            opciones_severidad,
            format_func=lambda valor: _formatear_etiqueta(
                str(valor),
                ETIQUETAS_SEVERIDADES,
            ),
            key="filtro_incidencias_severidad",
        )

    with columna_categoria:
        categoria = st.selectbox(
            "Categoría",
            opciones_categoria,
            format_func=lambda valor: _formatear_etiqueta(
                str(valor),
                ETIQUETAS_CATEGORIAS,
            ),
            key="filtro_incidencias_categoria",
        )

    with columna_columna:
        columna = st.selectbox(
            "Columna",
            opciones_columna,
            key="filtro_incidencias_columna",
        )

    return str(severidad), str(categoria), str(columna)


def _mostrar_detalle_incidencia(
    incidencias: list[dict],
) -> None:
    """Permite seleccionar y consultar el detalle de una incidencia."""

    if not incidencias:
        return

    st.markdown("### Detalle de incidencia")

    opciones = list(range(len(incidencias)))

    indice = st.selectbox(
        "Selecciona una incidencia",
        opciones,
        format_func=lambda posicion: (
            f"{int(posicion) + 1}. "
            f"{ETIQUETAS_TIPOS_INCIDENCIA.get(
                incidencias[int(posicion)]['tipo'],
                incidencias[int(posicion)]['tipo'],
            )}"
            f" · "
            f"{incidencias[int(posicion)]['columna'] or 'General'}"
        ),
        key="detalle_incidencia",
    )

    incidencia = incidencias[int(indice)]

    columna_tipo, columna_categoria, columna_severidad = st.columns(3)

    columna_tipo.write(
        "**Tipo**  \n"
        f"{ETIQUETAS_TIPOS_INCIDENCIA.get(
            incidencia['tipo'],
            incidencia['tipo'],
        )}"
    )

    columna_categoria.write(
        "**Categoría**  \n"
        f"{ETIQUETAS_CATEGORIAS.get(
            incidencia['categoria'],
            incidencia['categoria'],
        )}"
    )

    columna_severidad.write(
        "**Severidad**  \n"
        f"{ETIQUETAS_SEVERIDADES.get(
            incidencia['severidad'],
            incidencia['severidad'],
        )}"
    )

    st.write(
        "**Columna:** "
        f"{incidencia['columna'] or 'General'}"
    )

    if incidencia["cantidad"] is not None:
        st.write(
            "**Cantidad afectada:** "
            f"{incidencia['cantidad']}"
        )

    if incidencia["porcentaje"] is not None:
        st.write(
            "**Porcentaje:** "
            f"{incidencia['porcentaje']:.2f} %"
        )

    st.info(incidencia["mensaje"])


def _mostrar_incidencias(resultado: dict) -> None:
    """Muestra la pestaña Incidencias."""

    incidencias = resultado["incidencias"]

    st.markdown("## Incidencias")

    _mostrar_contadores_incidencias(incidencias)

    st.divider()

    if not incidencias:
        st.success("No se han detectado incidencias.")
        return

    st.markdown("### Filtros")

    severidad, categoria, columna = _mostrar_filtros_incidencias(
        incidencias
    )

    incidencias_filtradas = _filtrar_incidencias(
        incidencias,
        severidad,
        categoria,
        columna,
    )

    st.caption(
        f"Mostrando {len(incidencias_filtradas)} "
        f"de {len(incidencias)} incidencias."
    )

    st.markdown("### Listado de incidencias")

    if incidencias_filtradas:
        st.dataframe(
            _preparar_incidencias_tabla(incidencias_filtradas),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        _mostrar_detalle_incidencia(incidencias_filtradas)

    else:
        st.info(
            "No hay incidencias que coincidan con los filtros seleccionados."
        )

    st.divider()

    _boton_imprimir_incidencias(
        resultado,
        incidencias_filtradas,
        severidad,
        categoria,
        columna,
    )



def _contar_incidencias_columna(
    incidencias: list[dict],
    columna: object,
) -> int:
    """Cuenta las incidencias asociadas a una columna."""

    return sum(
        1
        for incidencia in incidencias
        if incidencia["columna"] == columna
    )


def _preparar_tabla_columnas(resultado: dict) -> list[dict]:
    """Prepara la visión general de columnas usando resultados de V3."""

    perfil = resultado["perfil"]
    tipos_semanticos = resultado["tipos_semanticos"]
    incidencias = resultado["incidencias"]

    filas = []

    for columna in perfil["nombres_columnas"]:
        semantica = tipos_semanticos[columna]

        filas.append(
            {
                "Columna": columna,
                "Tipo físico": perfil["tipos_datos"].get(columna, ""),
                "Tipo semántico": ETIQUETAS_TIPOS.get(
                    semantica["tipo"],
                    semantica["tipo"],
                ),
                "Confianza": str(semantica["confianza"]).capitalize(),
                "Origen": (
                    "Declarado"
                    if semantica["fuente"] == "declared"
                    else "Inferido"
                ),
                "Valores distintos": perfil["valores_distintos"].get(
                    columna,
                    "",
                ),
                "Incidencias": _contar_incidencias_columna(
                    incidencias,
                    columna,
                ),
            }
        )

    return filas


def _mostrar_evidencias_columna(semantica: dict) -> None:
    """Muestra las evidencias utilizadas por la inferencia V3."""

    st.markdown("### Evidencias")

    evidencias = semantica["evidencias"]

    if not evidencias:
        st.caption("No hay evidencias adicionales registradas.")
        return

    for evidencia in evidencias:
        st.write(f"• {evidencia}")


def _buscar_estadisticas_columna(
    estadisticas: object,
    columna: object,
) -> dict | None:
    """Localiza las estadísticas V3 de una columna sin recalcularlas."""

    if isinstance(estadisticas, dict):
        directas = estadisticas.get(columna)

        if isinstance(directas, dict):
            return directas

        for clave_lista in (
            "columnas",
            "estadisticas",
            "resultados",
        ):
            elementos = estadisticas.get(clave_lista)

            if isinstance(elementos, list):
                for elemento in elementos:
                    if not isinstance(elemento, dict):
                        continue

                    nombre = (
                        elemento.get("columna")
                        or elemento.get("nombre")
                    )

                    if nombre == columna:
                        return {
                            clave: valor
                            for clave, valor in elemento.items()
                            if clave not in {"columna", "nombre"}
                        }

    if isinstance(estadisticas, list):
        for elemento in estadisticas:
            if not isinstance(elemento, dict):
                continue

            nombre = elemento.get("columna") or elemento.get("nombre")

            if nombre == columna:
                return {
                    clave: valor
                    for clave, valor in elemento.items()
                    if clave not in {"columna", "nombre"}
                }

    return None


def _formatear_valor_estadistico(valor: object) -> str:
    """Formatea para impresión un valor estadístico como se muestra en pantalla."""

    if isinstance(valor, (int, float)):
        numero = float(valor)

        if numero.is_integer():
            return str(int(numero))

        return f"{numero:.4f}".rstrip("0").rstrip(".")

    return str(valor)


def _formatear_nombre_estadistica(nombre: object) -> str:
    """Convierte una clave técnica de estadística en una etiqueta legible."""

    equivalencias = {
        "min": "Mínimo",
        "max": "Máximo",
        "media": "Media",
        "mean": "Media",
        "mediana": "Mediana",
        "median": "Mediana",
        "desv_std": "Desviación estándar",
        "std": "Desviación estándar",
        "q1": "Q1",
        "q3": "Q3",
    }

    clave = str(nombre)

    return equivalencias.get(
        clave,
        clave.replace("_", " ").capitalize(),
    )


def _mostrar_estadisticas_columna(
    resultado: dict,
    columna: object,
) -> None:
    """Muestra estadísticas ya calculadas por V3 cuando están disponibles."""

    estadisticas = _buscar_estadisticas_columna(
        resultado["perfil"]["estadisticas_numericas"],
        columna,
    )

    st.markdown("### Estadísticas disponibles")

    if not estadisticas:
        semantica = resultado.get("tipos_semanticos", {}).get(columna, {})
        tipo_semantico = semantica.get("tipo")

        if tipo_semantico == "identificador":
            mensaje = (
                "No se muestran estadísticas numéricas porque esta columna "
                "ha sido clasificada como Identificador."
            )
        elif tipo_semantico in {"fecha", "fecha_hora"}:
            mensaje = (
                "No se muestran estadísticas numéricas porque esta columna "
                "ha sido clasificada como temporal."
            )
        elif tipo_semantico == "booleano_binario":
            mensaje = (
                "No se muestran estadísticas numéricas porque esta columna "
                "ha sido clasificada como Booleana/binaria."
            )
        elif tipo_semantico == "categorico":
            mensaje = (
                "No se muestran estadísticas numéricas porque esta columna "
                "ha sido clasificada como Categórica."
            )
        elif tipo_semantico == "texto_libre":
            mensaje = (
                "No se muestran estadísticas numéricas porque esta columna "
                "ha sido clasificada como Texto libre."
            )
        else:
            mensaje = "No hay estadísticas numéricas disponibles para esta columna."

        st.caption(mensaje)
        return

    filas = [
        {
            "Estadística": _formatear_nombre_estadistica(clave),
            "Valor": valor,
        }
        for clave, valor in estadisticas.items()
    ]

    st.dataframe(
        filas,
        use_container_width=True,
        hide_index=True,
    )


def _mostrar_incidencias_columna(
    resultado: dict,
    columna: object,
) -> None:
    """Muestra las incidencias asociadas a la columna seleccionada."""

    st.markdown("### Incidencias asociadas")

    incidencias = [
        incidencia
        for incidencia in resultado["incidencias"]
        if incidencia["columna"] == columna
    ]

    if not incidencias:
        st.success(
            "No se han detectado incidencias asociadas "
            "a esta columna."
        )
        return

    st.dataframe(
        _preparar_incidencias_tabla(incidencias),
        use_container_width=True,
        hide_index=True,
    )


def _formatear_porcentaje_ui(valor: object) -> str:
    """Formatea porcentajes V6.1 para su presentación."""
    try:
        return f"{float(valor):.2f} %".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _mostrar_perfil_avanzado_columna(resultado: dict, columna: object) -> None:
    """Muestra perfil enriquecido, cardinalidad y candidatura de clave V6.1."""
    avanzado = resultado.get("analisis_avanzado", {})
    analisis = avanzado.get("columnas", {}).get(columna)
    clave = avanzado.get("claves_candidatas", {}).get(columna)

    if not analisis:
        return

    st.markdown("### Perfil avanzado")
    tarjetas = (
        ("Cobertura", _formatear_porcentaje_ui(analisis.get("porcentaje_analizable"))),
        ("Unicidad", _formatear_porcentaje_ui(analisis.get("porcentaje_unicidad"))),
        ("Nulos totales", analisis.get("nulos_totales", 0)),
        ("Duplicados adicionales", analisis.get("duplicados_adicionales", 0)),
        ("Valor más frecuente", analisis.get("valor_mas_frecuente") or "—"),
    )
    for bloque, (etiqueta, valor) in zip(st.columns(5), tarjetas):
        with bloque:
            st.markdown(_tarjeta_indicador(etiqueta, valor), unsafe_allow_html=True)

    if clave:
        st.markdown("#### Clave candidata")
        nivel = str(clave.get("nivel", "no_candidata")).replace("_", " ").capitalize()
        confianza = str(clave.get("confianza", "")).capitalize()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(_tarjeta_indicador("Candidatura", nivel), unsafe_allow_html=True)
        with c2:
            st.markdown(_tarjeta_indicador("Confianza", confianza), unsafe_allow_html=True)
        with st.expander("Ver evidencias de candidatura"):
            for evidencia in clave.get("evidencias", []):
                st.write(f"• {evidencia}")


def _mostrar_distribucion_columna(resultado: dict, columna: object) -> None:
    """Muestra la distribución V6.1 disponible para la columna."""
    distribucion = (
        resultado.get("analisis_avanzado", {})
        .get("distribuciones", {})
        .get(columna)
    )
    if not distribucion:
        return

    st.markdown("### Distribución")
    if distribucion.get("tipo") == "frecuencias":
        filas = [
            {
                "Valor": item.get("valor"),
                "Frecuencia": item.get("frecuencia"),
                "Porcentaje": _formatear_porcentaje_ui(item.get("porcentaje")),
            }
            for item in distribucion.get("valores", [])
        ]
        if filas:
            st.dataframe(filas, use_container_width=True, hide_index=True)
        if distribucion.get("truncada"):
            st.caption("Se muestran únicamente los valores más frecuentes.")
        return

    if distribucion.get("tipo") == "numerica":
        filas = [
            {
                "Desde": item.get("limite_inferior"),
                "Hasta": item.get("limite_superior"),
                "Frecuencia": item.get("frecuencia"),
                "Porcentaje": _formatear_porcentaje_ui(item.get("porcentaje")),
            }
            for item in distribucion.get("intervalos", [])
        ]
        if filas:
            st.dataframe(filas, use_container_width=True, hide_index=True)


def _mostrar_diagnosticos_columna(resultado: dict, columna: object) -> None:
    """Muestra el contexto V6.1 asociado a incidencias de una columna."""
    diagnosticos = [
        item
        for item in resultado.get("analisis_avanzado", {}).get("diagnosticos", [])
        if item.get("columna") == columna
    ]
    if not diagnosticos:
        return

    st.markdown("### Diagnóstico contextual")
    for indice, diagnostico in enumerate(diagnosticos, start=1):
        titulo = diagnostico.get("mensaje_incidencia") or f"Diagnóstico {indice}"
        with st.expander(titulo):
            if diagnostico.get("contexto"):
                st.markdown("**Contexto**")
                for texto in diagnostico["contexto"]:
                    st.write(f"• {texto}")
            if diagnostico.get("acciones_posibles"):
                st.markdown("**Posibles acciones**")
                for texto in diagnostico["acciones_posibles"]:
                    st.write(f"• {texto}")


def _mostrar_relaciones_avanzadas(resultado: dict) -> None:
    """Muestra las relaciones V6.1 detectadas entre columnas."""
    relaciones = resultado.get("analisis_avanzado", {}).get("relaciones", {})
    if not relaciones:
        return

    claves = relaciones.get("claves_compuestas", [])
    funcionales = relaciones.get("relaciones_funcionales", [])
    presencia = relaciones.get("relaciones_presencia", [])

    st.markdown("### Relaciones entre columnas")
    if not (claves or funcionales or presencia):
        st.caption("No se han detectado relaciones relevantes con los criterios V6.1.")
        return

    if claves:
        st.markdown("#### Claves candidatas compuestas")
        st.dataframe([
            {
                "Columnas": " + ".join(map(str, item.get("columnas", []))),
                "Nivel": str(item.get("nivel", "")).replace("_", " " ).capitalize(),
                "Confianza": str(item.get("confianza", "")).capitalize(),
                "Unicidad": _formatear_porcentaje_ui(item.get("porcentaje_unicidad")),
            }
            for item in claves
        ], use_container_width=True, hide_index=True)

    if funcionales:
        st.markdown("#### Relaciones funcionales")
        st.dataframe([
            {
                "Origen": item.get("columna_origen"),
                "Destino": item.get("columna_destino"),
                "Consistencia": _formatear_porcentaje_ui(item.get("porcentaje_consistencia")),
                "Confianza": str(item.get("confianza", "")).capitalize(),
            }
            for item in funcionales
        ], use_container_width=True, hide_index=True)

    if presencia:
        st.markdown("#### Patrones de presencia")

        filas_presencia = [
            {
                "Columnas": " + ".join(map(str, item.get("columnas", []))),
                "Patrón": str(item.get("patron", "")).capitalize(),
                "Consistencia": _formatear_porcentaje_ui(
                    item.get("porcentaje_consistencia")
                ),
                "Confianza": str(item.get("confianza", "")).capitalize(),
            }
            for item in presencia
        ]

        limite_visible = 5
        st.dataframe(
            filas_presencia[:limite_visible],
            use_container_width=True,
            hide_index=True,
        )

        if len(filas_presencia) > limite_visible:
            restantes = len(filas_presencia) - limite_visible
            with st.expander(
                f"Ver {restantes} patrón"
                f"{'es' if restantes != 1 else ''} de presencia adicional"
                f"{'es' if restantes != 1 else ''}"
            ):
                st.dataframe(
                    filas_presencia[limite_visible:],
                    use_container_width=True,
                    hide_index=True,
                )


def _mostrar_detalle_columna(
    resultado: dict,
    columna: object,
) -> None:
    """Muestra el detalle disponible de una columna."""
    perfil = resultado["perfil"]
    semantica = resultado["tipos_semanticos"][columna]

    st.markdown("### Detalle de columna")
    tarjetas = (
        ("Tipo físico", perfil["tipos_datos"].get(columna, "")),
        ("Tipo semántico", ETIQUETAS_TIPOS.get(semantica["tipo"], semantica["tipo"])),
        ("Confianza", str(semantica["confianza"]).capitalize()),
        ("Origen", "Declarado" if semantica["fuente"] == "declared" else "Inferido"),
        ("Valores distintos", perfil["valores_distintos"].get(columna, "")),
    )
    for bloque, (etiqueta, valor) in zip(st.columns(5), tarjetas):
        with bloque:
            st.markdown(_tarjeta_indicador(etiqueta, valor), unsafe_allow_html=True)

    st.divider()
    _mostrar_perfil_avanzado_columna(resultado, columna)
    st.divider()
    _mostrar_evidencias_columna(semantica)
    st.divider()
    _mostrar_estadisticas_columna(resultado, columna)
    st.divider()
    _mostrar_distribucion_columna(resultado, columna)
    st.divider()
    _mostrar_incidencias_columna(resultado, columna)
    _mostrar_diagnosticos_columna(resultado, columna)


def _html_resumen_columnas_imprimible(resultado: dict) -> str:
    """Construye la impresión de la vista general de columnas."""

    dataset = resultado["dataset"]
    filas = _preparar_tabla_columnas(resultado)

    cuerpo = []
    for fila in filas:
        cuerpo.append(
            f"""
            <tr>
                <td>{escape(str(fila["Columna"]))}</td>
                <td>{escape(str(fila["Tipo físico"]))}</td>
                <td>{escape(str(fila["Tipo semántico"]))}</td>
                <td>{escape(str(fila["Confianza"]))}</td>
                <td>{escape(str(fila["Origen"]))}</td>
                <td>{escape(str(fila["Valores distintos"]))}</td>
                <td>{escape(str(fila["Incidencias"]))}</td>
            </tr>
            """
        )

    return dedent(f"""
    <style>
        .dq-print-columns {{
            color: #172033;
            background: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10.5pt;
            line-height: 1.35;
        }}

        .dq-print-columns h1 {{
            margin: 0 0 2px;
            font-size: 22pt;
        }}

        .dq-print-columns h2 {{
            margin: 14px 0 7px;
            font-size: 14pt;
        }}

        .dq-print-subtitle,
        .dq-print-dataset {{
            color: #657084;
        }}

        .dq-print-dataset {{
            margin-bottom: 14px;
        }}

        .dq-print-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
        }}

        .dq-print-table th {{
            text-align: left;
            background: #f1f4f8;
            border: 1px solid #d9e0ea;
            padding: 6px;
        }}

        .dq-print-table td {{
            border: 1px solid #d9e0ea;
            padding: 6px;
            vertical-align: top;
        }}

        @media print {{
            .dq-print-columns {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            @page {{
                size: A4;
                margin: 14mm;
            }}
        }}
    </style>

    <div class="dq-print-columns">
        <h1>DATAQUALITYPY</h1>
        <div class="dq-print-subtitle">
            Resumen de columnas
        </div>
        <div class="dq-print-dataset">
            {escape(str(dataset["archivo"]))} ·
            {dataset["filas"]} filas ·
            {dataset["columnas"]} columnas
        </div>

        <h2>Vista general</h2>

        <table class="dq-print-table">
            <thead>
                <tr>
                    <th>Columna</th>
                    <th>Tipo físico</th>
                    <th>Tipo semántico</th>
                    <th>Confianza</th>
                    <th>Origen</th>
                    <th>Valores distintos</th>
                    <th>Incidencias</th>
                </tr>
            </thead>
            <tbody>
                {"".join(cuerpo)}
            </tbody>
        </table>
    </div>
    """)


def _html_columna_imprimible(resultado: dict, columna: object) -> str:
    """Construye la impresión del detalle de una columna."""

    dataset = resultado["dataset"]
    perfil = resultado["perfil"]
    semantica = resultado["tipos_semanticos"][columna]

    evidencias = semantica["evidencias"]
    if evidencias:
        evidencias_html = "".join(
            f"<li>{escape(str(evidencia))}</li>"
            for evidencia in evidencias
        )
        evidencias_html = f"<ul>{evidencias_html}</ul>"
    else:
        evidencias_html = (
            '<div class="dq-print-info">'
            'No hay evidencias adicionales registradas.'
            '</div>'
        )

    estadisticas = _buscar_estadisticas_columna(
        perfil["estadisticas_numericas"],
        columna,
    )

    if estadisticas:
        estadisticas_html = "".join(
            f"""
            <tr>
                <td>{escape(str(_formatear_nombre_estadistica(clave)))}</td>
                <td>{escape(str(_formatear_valor_estadistico(valor)))}</td>
            </tr>
            """
            for clave, valor in estadisticas.items()
        )
        estadisticas_html = f"""
        <table class="dq-print-table dq-print-stats">
            <thead>
                <tr>
                    <th>Estadística</th>
                    <th>Valor</th>
                </tr>
            </thead>
            <tbody>{estadisticas_html}</tbody>
        </table>
        """
    else:
        estadisticas_html = (
            '<div class="dq-print-info">'
            'V3 no ha generado estadísticas numéricas para esta columna.'
            '</div>'
        )

    incidencias = [
        incidencia
        for incidencia in resultado["incidencias"]
        if incidencia["columna"] == columna
    ]

    if incidencias:
        filas_incidencias = []
        for item in _preparar_incidencias_tabla(incidencias):
            filas_incidencias.append(
                f"""
                <tr>
                    <td>{escape(str(item.get("Tipo", "")))}</td>
                    <td>{escape(str(item.get("Categoría", "")))}</td>
                    <td>{escape(str(item.get("Severidad", "")))}</td>
                    <td>{escape(str(item.get("Columna", "")))}</td>
                    <td>{escape(str(item.get("Cantidad", "")))}</td>
                    <td>{escape(str(item.get("Porcentaje", "")))}</td>
                    <td>{escape(str(item.get("Mensaje", "")))}</td>
                </tr>
                """
            )

        incidencias_html = f"""
        <table class="dq-print-table dq-print-incidents-table">
            <thead>
                <tr>
                    <th>Tipo</th>
                    <th>Categoría</th>
                    <th>Severidad</th>
                    <th>Columna</th>
                    <th>Cantidad</th>
                    <th>Porcentaje</th>
                    <th>Mensaje</th>
                </tr>
            </thead>
            <tbody>{"".join(filas_incidencias)}</tbody>
        </table>
        """
    else:
        incidencias_html = (
            '<div class="dq-print-info">'
            'No se han detectado incidencias asociadas a esta columna.'
            '</div>'
        )

    tipo_semantico = ETIQUETAS_TIPOS.get(
        semantica["tipo"],
        semantica["tipo"],
    )
    origen = (
        "Declarado"
        if semantica["fuente"] == "declared"
        else "Inferido"
    )

    return dedent(f"""
    <style>
        .dq-print-column {{
            color: #172033;
            background: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10.5pt;
            line-height: 1.35;
        }}

        .dq-print-column h1 {{
            margin: 0 0 2px;
            font-size: 22pt;
        }}

        .dq-print-column h2 {{
            margin: 14px 0 7px;
            font-size: 14pt;
        }}

        .dq-print-subtitle,
        .dq-print-dataset {{
            color: #657084;
        }}

        .dq-print-dataset {{
            margin-bottom: 14px;
        }}

        .dq-print-metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }}

        .dq-print-metric {{
            border: 1px solid #d9e0ea;
            border-radius: 7px;
            padding: 8px 10px;
            break-inside: avoid;
        }}

        .dq-print-metric span {{
            display: block;
            color: #657084;
            font-size: 8.5pt;
            margin-bottom: 2px;
        }}

        .dq-print-metric strong {{
            display: block;
        }}

        .dq-print-line {{
            margin-top: 8px;
        }}

        .dq-print-section {{
            break-inside: avoid;
        }}

        .dq-print-section ul {{
            margin: 5px 0 0 18px;
            padding: 0;
        }}

        .dq-print-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
        }}

        .dq-print-table th {{
            text-align: left;
            background: #f1f4f8;
            border: 1px solid #d9e0ea;
            padding: 6px;
        }}

        .dq-print-table td {{
            border: 1px solid #d9e0ea;
            padding: 6px;
            vertical-align: top;
        }}

        .dq-print-stats {{
            max-width: 430px;
        }}

        .dq-print-incidents-table {{
            font-size: 8pt;
            table-layout: auto;
        }}

        .dq-print-incidents-table th,
        .dq-print-incidents-table td {{
            padding: 5px;
        }}

        .dq-print-incidents-table th:last-child,
        .dq-print-incidents-table td:last-child {{
            width: 34%;
        }}

        .dq-print-info {{
            padding: 8px 10px;
            border-left: 3px solid #4c83b6;
            background: #f6f8fb;
        }}

        @media print {{
            .dq-print-column {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            @page {{
                size: A4;
                margin: 14mm;
            }}
        }}
    </style>

    <div class="dq-print-column">
        <h1>DATAQUALITYPY</h1>
        <div class="dq-print-subtitle">
            Detalle de columna · {escape(str(columna))}
        </div>
        <div class="dq-print-dataset">
            {escape(str(dataset["archivo"]))} ·
            {dataset["filas"]} filas ·
            {dataset["columnas"]} columnas
        </div>

        <h2>Perfil de columna</h2>
        <div class="dq-print-metrics">
            <div class="dq-print-metric">
                <span>Tipo físico</span>
                <strong>{escape(str(perfil["tipos_datos"].get(columna, "")))}</strong>
            </div>
            <div class="dq-print-metric">
                <span>Tipo semántico</span>
                <strong>{escape(str(tipo_semantico))}</strong>
            </div>
            <div class="dq-print-metric">
                <span>Confianza</span>
                <strong>{escape(str(semantica["confianza"]).capitalize())}</strong>
            </div>
            <div class="dq-print-metric">
                <span>Origen</span>
                <strong>{escape(origen)}</strong>
            </div>
        </div>

        <div class="dq-print-line">
            <strong>Valores distintos:</strong>
            {escape(str(perfil["valores_distintos"].get(columna, "")))}
        </div>

        <section class="dq-print-section">
            <h2>Evidencias</h2>
            {evidencias_html}
        </section>

        <section class="dq-print-section">
            <h2>Estadísticas disponibles</h2>
            {estadisticas_html}
        </section>

        <section class="dq-print-section">
            <h2>Incidencias asociadas</h2>
            {incidencias_html}
        </section>
    </div>
    """)


def _boton_impresion_columnas(
    etiqueta: str,
    titulo: str,
    contenido: str,
    funcion_js: str,
    ancho: int = 300,
) -> None:
    """Botón común para las dos impresiones de Columnas."""

    documento = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{escape(titulo)}</title>
<style>
    html, body {{
        margin: 0;
        padding: 0;
        background: #ffffff;
    }}
</style>
</head>
<body>
{contenido}
<script>
    window.onload = function() {{
        window.focus();
        setTimeout(function() {{
            window.print();
            setTimeout(function() {{
                window.close();
            }}, 150);
        }}, 150);
    }};
</script>
</body>
</html>"""

    documento_json = json.dumps(documento).replace("</", "<\\/")

    components.html(
        f"""
        <button onclick="{funcion_js}()" class="dq-print-button">
            🖨️ {escape(etiqueta)}
        </button>

        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color-scheme: dark;
                font-family:
                    "Source Sans 3",
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;
            }}

            .dq-print-button {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.35rem;
                min-height: 38px;
                padding: 0.45rem 0.85rem;
                border: 1px solid rgba(250, 250, 250, 0.20);
                border-radius: 0.5rem;
                background: rgb(38, 39, 48);
                color: rgb(250, 250, 250);
                font-family: inherit;
                font-size: 14px;
                font-weight: 400;
                line-height: 1.2;
                white-space: nowrap;
                cursor: pointer;
                transition:
                    border-color 120ms ease,
                    background-color 120ms ease;
            }}

            .dq-print-button:hover {{
                border-color: rgba(250, 250, 250, 0.38);
                background: rgb(49, 51, 63);
            }}

            .dq-print-button:active {{
                background: rgb(58, 60, 73);
            }}

            .dq-print-button:focus-visible {{
                outline: 2px solid rgba(117, 183, 246, 0.9);
                outline-offset: 2px;
            }}
        </style>

        <script>
            function {funcion_js}() {{
                const contenido = {documento_json};
                const ventana = window.open("", "_blank");

                if (!ventana) {{
                    alert("El navegador ha bloqueado la ventana de impresión.");
                    return;
                }}

                ventana.document.open();
                ventana.document.write(contenido);
                ventana.document.close();
            }}
        </script>
        """,
        height=50,
        width=ancho,
    )



def _mostrar_columnas(resultado: dict) -> None:
    """Muestra la pestaña Columnas."""

    columnas = resultado["perfil"]["nombres_columnas"]

    st.markdown("## Columnas")

    st.markdown("### Vista general")

    st.dataframe(
        _preparar_tabla_columnas(resultado),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    if not columnas:
        st.info("El dataset no contiene columnas.")
        return

    columna_seleccionada = st.selectbox(
        "Selecciona una columna",
        columnas,
        key="detalle_columna",
    )

    _mostrar_detalle_columna(
        resultado,
        columna_seleccionada,
    )

    st.divider()
    _mostrar_relaciones_avanzadas(resultado)

    st.divider()

    columna_imprimir_resumen, columna_imprimir_detalle = st.columns(2)

    with columna_imprimir_resumen:
        _boton_impresion_columnas(
            "Imprimir resumen de columnas",
            "DataQualityPy_Columnas",
            _html_resumen_columnas_imprimible(resultado),
            "imprimirResumenColumnas",
            300,
        )

    with columna_imprimir_detalle:
        _boton_impresion_columnas(
            "Imprimir columna seleccionada",
            "DataQualityPy_Columna",
            _html_columna_imprimible(
                resultado,
                columna_seleccionada,
            ),
            "imprimirColumnaSeleccionada",
            300,
        )


ETIQUETAS_CONTROLES = {
    "completitud": "Completitud",
    "unicidad_general": "Unicidad general",
    "consistencia_texto": "Consistencia de texto",
    "outliers": "Valores atípicos",
    "compatibilidad_semantica": "Compatibilidad semántica",
    "unicidad_clave": "Unicidad de clave",
    "reglas_negocio": "Reglas de negocio",
}

ETIQUETAS_ESTADOS_COBERTURA = {
    "aplicado": "Aplicado",
    "no_aplicable": "No aplicable",
    "no_configurado": "No configurado",
}


def _preparar_cobertura(resultado: dict) -> list[dict]:
    """Prepara el detalle de cobertura ya calculado por V3."""

    cobertura = resultado["resumen"]["cobertura_auditoria"]

    grupos = (
        ("controles_aplicados", "aplicado"),
        ("controles_no_aplicables", "no_aplicable"),
        ("controles_no_configurados", "no_configurado"),
    )

    filas = []

    for clave_grupo, estado in grupos:
        for control in cobertura[clave_grupo]:
            filas.append(
                {
                    "control": control,
                    "estado": estado,
                }
            )

    return filas


def _mostrar_resumen_cobertura(resultado: dict) -> None:
    """Muestra los contadores de cobertura generados por V3 como tarjetas."""

    cobertura = resultado["resumen"]["cobertura_auditoria"]

    tarjetas = (
        (
            "Controles aplicados",
            len(cobertura["controles_aplicados"]),
            "#4c83b6",
        ),
        (
            "No aplicables",
            len(cobertura["controles_no_aplicables"]),
            None,
        ),
        (
            "No configurados",
            len(cobertura["controles_no_configurados"]),
            None,
        ),
    )

    for columna, (etiqueta, valor, color) in zip(st.columns(3), tarjetas):
        with columna:
            st.markdown(
                _tarjeta_indicador(etiqueta, valor, color),
                unsafe_allow_html=True,
            )



def _mostrar_explicacion_cobertura() -> None:
    """Explica el significado de los estados de cobertura."""

    st.markdown("### Significado de los estados")

    st.write(
        "**Aplicado:** el control se ha ejecutado durante la auditoría "
        "porque correspondía al dataset o a su configuración."
    )
    st.write(
        "**No aplicable:** el control forma parte de DataQualityPy, "
        "pero no correspondía aplicarlo a este dataset."
    )
    st.write(
        "**No configurado:** el control requiere una configuración "
        "específica que no se ha definido para esta auditoría."
    )



def _html_cobertura_imprimible(
    resultado: dict,
    cobertura_filtrada: list[dict],
    estado_seleccionado: str,
) -> str:
    """Construye la vista imprimible de Cobertura."""

    dataset = resultado["dataset"]
    cobertura_resumen = resultado["resumen"]["cobertura_auditoria"]
    cobertura_total = _preparar_cobertura(resultado)

    aplicados = len(cobertura_resumen["controles_aplicados"])
    no_aplicables = len(cobertura_resumen["controles_no_aplicables"])
    no_configurados = len(cobertura_resumen["controles_no_configurados"])

    estado_texto = (
        "Todos"
        if estado_seleccionado == "todos"
        else ETIQUETAS_ESTADOS_COBERTURA.get(
            estado_seleccionado,
            estado_seleccionado,
        )
    )

    filas = []
    for fila in cobertura_filtrada:
        filas.append(
            f"""
            <tr>
                <td>{escape(str(ETIQUETAS_CONTROLES.get(
                    fila["control"],
                    fila["control"],
                )))}</td>
                <td>{escape(str(ETIQUETAS_ESTADOS_COBERTURA.get(
                    fila["estado"],
                    fila["estado"],
                )))}</td>
            </tr>
            """
        )

    if filas:
        tabla = f"""
        <table class="dq-print-table">
            <thead>
                <tr>
                    <th>Control</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
                {"".join(filas)}
            </tbody>
        </table>
        """
    else:
        tabla = (
            '<div class="dq-print-info">'
            'No hay controles que coincidan con el filtro seleccionado.'
            '</div>'
        )

    return dedent(f"""
    <style>
        .dq-print-coverage {{
            color: #172033;
            background: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10.5pt;
            line-height: 1.35;
        }}

        .dq-print-coverage h1 {{
            margin: 0 0 2px;
            font-size: 22pt;
        }}

        .dq-print-coverage h2 {{
            margin: 14px 0 7px;
            font-size: 14pt;
        }}

        .dq-print-subtitle,
        .dq-print-dataset {{
            color: #657084;
        }}

        .dq-print-dataset {{
            margin-bottom: 14px;
        }}

        .dq-print-metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }}

        .dq-print-metric {{
            border: 1px solid #d9e0ea;
            border-radius: 7px;
            padding: 8px 10px;
            break-inside: avoid;
        }}

        .dq-print-metric strong {{
            display: block;
            font-size: 17pt;
        }}

        .dq-print-filter {{
            max-width: 220px;
            border: 1px solid #d9e0ea;
            border-radius: 7px;
            padding: 7px 9px;
            margin-bottom: 7px;
        }}

        .dq-print-filter span {{
            display: block;
            color: #657084;
            font-size: 8.5pt;
            margin-bottom: 2px;
        }}

        .dq-print-caption {{
            color: #657084;
            margin-bottom: 8px;
        }}

        .dq-print-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
        }}

        .dq-print-table th {{
            text-align: left;
            background: #f1f4f8;
            border: 1px solid #d9e0ea;
            padding: 6px;
        }}

        .dq-print-table td {{
            border: 1px solid #d9e0ea;
            padding: 6px;
            vertical-align: top;
        }}

        .dq-print-section {{
            break-inside: avoid;
        }}

        .dq-print-explanation {{
            margin: 5px 0;
        }}

        .dq-print-info {{
            padding: 8px 10px;
            border-left: 3px solid #4c83b6;
            background: #f6f8fb;
        }}

        @media print {{
            .dq-print-coverage {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            @page {{
                size: A4;
                margin: 14mm;
            }}
        }}
    </style>

    <div class="dq-print-coverage">
        <h1>DATAQUALITYPY</h1>
        <div class="dq-print-subtitle">
            Cobertura de auditoría
        </div>
        <div class="dq-print-dataset">
            {escape(str(dataset["archivo"]))} ·
            {dataset["filas"]} filas ·
            {dataset["columnas"]} columnas
        </div>

        <h2>Resumen de cobertura</h2>
        <div class="dq-print-metrics">
            <div class="dq-print-metric">
                <strong>{aplicados}</strong>
                Controles aplicados
            </div>
            <div class="dq-print-metric">
                <strong>{no_aplicables}</strong>
                No aplicables
            </div>
            <div class="dq-print-metric">
                <strong>{no_configurados}</strong>
                No configurados
            </div>
        </div>

        <section class="dq-print-section">
            <h2>Detalle de controles</h2>

            <div class="dq-print-filter">
                <span>Estado</span>
                <strong>{escape(str(estado_texto))}</strong>
            </div>

            <div class="dq-print-caption">
                Mostrando {len(cobertura_filtrada)}
                de {len(cobertura_total)} controles.
            </div>

            {tabla}
        </section>

        <section class="dq-print-section">
            <h2>Significado de los estados</h2>

            <div class="dq-print-explanation">
                <strong>Aplicado:</strong>
                el control se ha ejecutado durante la auditoría porque
                correspondía al dataset o a su configuración.
            </div>

            <div class="dq-print-explanation">
                <strong>No aplicable:</strong>
                el control forma parte de DataQualityPy, pero no correspondía
                aplicarlo a este dataset.
            </div>

            <div class="dq-print-explanation">
                <strong>No configurado:</strong>
                el control requiere una configuración específica que no se
                ha definido para esta auditoría.
            </div>
        </section>
    </div>
    """)


def _boton_imprimir_cobertura(
    resultado: dict,
    cobertura_filtrada: list[dict],
    estado_seleccionado: str,
) -> None:
    """Muestra el botón normalizado de impresión de Cobertura."""

    contenido = _html_cobertura_imprimible(
        resultado,
        cobertura_filtrada,
        estado_seleccionado,
    )

    documento = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>DataQualityPy_Cobertura</title>
<style>
    html, body {{
        margin: 0;
        padding: 0;
        background: #ffffff;
    }}
</style>
</head>
<body>
{contenido}
<script>
    window.onload = function() {{
        window.focus();
        setTimeout(function() {{
            window.print();
            setTimeout(function() {{
                window.close();
            }}, 150);
        }}, 150);
    }};
</script>
</body>
</html>"""

    documento_json = json.dumps(documento).replace("</", "<\\/")

    components.html(
        f"""
        <button onclick="imprimirCobertura()" class="dq-print-button">
            🖨️ Imprimir cobertura
        </button>

        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color-scheme: dark;
                font-family:
                    "Source Sans 3",
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    sans-serif;
            }}

            .dq-print-button {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.35rem;
                min-height: 38px;
                padding: 0.45rem 0.85rem;
                border: 1px solid rgba(250, 250, 250, 0.20);
                border-radius: 0.5rem;
                background: rgb(38, 39, 48);
                color: rgb(250, 250, 250);
                font-family: inherit;
                font-size: 14px;
                font-weight: 400;
                line-height: 1.2;
                white-space: nowrap;
                cursor: pointer;
                transition:
                    border-color 120ms ease,
                    background-color 120ms ease;
            }}

            .dq-print-button:hover {{
                border-color: rgba(250, 250, 250, 0.38);
                background: rgb(49, 51, 63);
            }}

            .dq-print-button:active {{
                background: rgb(58, 60, 73);
            }}

            .dq-print-button:focus-visible {{
                outline: 2px solid rgba(117, 183, 246, 0.9);
                outline-offset: 2px;
            }}
        </style>

        <script>
            function imprimirCobertura() {{
                const contenido = {documento_json};
                const ventana = window.open("", "_blank");

                if (!ventana) {{
                    alert("El navegador ha bloqueado la ventana de impresión.");
                    return;
                }}

                ventana.document.open();
                ventana.document.write(contenido);
                ventana.document.close();
            }}
        </script>
        """,
        height=50,
        width=230,
    )



def _mostrar_cobertura(resultado: dict) -> None:
    """Muestra la pestaña Cobertura."""

    st.markdown("## Cobertura de auditoría")

    _mostrar_resumen_cobertura(resultado)

    st.divider()

    cobertura = _preparar_cobertura(resultado)

    estados_presentes = [
        estado
        for estado in (
            "aplicado",
            "no_aplicable",
            "no_configurado",
        )
        if any(
            fila["estado"] == estado
            for fila in cobertura
        )
    ]

    opciones_estado = ["todos", *estados_presentes]

    estado_seleccionado = st.selectbox(
        "Estado",
        opciones_estado,
        format_func=lambda valor: (
            "Todos"
            if valor == "todos"
            else ETIQUETAS_ESTADOS_COBERTURA.get(
                str(valor),
                str(valor),
            )
        ),
        key="filtro_cobertura_estado",
    )

    if estado_seleccionado == "todos":
        cobertura_filtrada = cobertura
    else:
        cobertura_filtrada = [
            fila
            for fila in cobertura
            if fila["estado"] == estado_seleccionado
        ]

    st.caption(
        f"Mostrando {len(cobertura_filtrada)} "
        f"de {len(cobertura)} controles."
    )

    tabla = [
        {
            "Control": ETIQUETAS_CONTROLES.get(
                fila["control"],
                fila["control"],
            ),
            "Estado": ETIQUETAS_ESTADOS_COBERTURA.get(
                fila["estado"],
                fila["estado"],
            ),
        }
        for fila in cobertura_filtrada
    ]

    st.markdown("### Detalle de controles")

    if tabla:
        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No hay controles que coincidan con el filtro seleccionado."
        )

    st.divider()

    _mostrar_explicacion_cobertura()

    st.divider()

    _boton_imprimir_cobertura(
        resultado,
        cobertura_filtrada,
        estado_seleccionado,
    )


def _generar_json_descarga(resultado: dict) -> str:
    """Genera en memoria el JSON v3.0 para su descarga."""

    contenido = {
        "dataqualitypy": {
            "version_informe": "3.0",
        },
        "dataset": resultado["dataset"],
        "resumen": resultado["resumen"],
        "tipos_semanticos": resultado["tipos_semanticos"],
        "incidencias": resultado["incidencias"],
        "perfil": resultado["perfil"],
        "calidad": resultado["calidad"],
    }

    return json.dumps(
        contenido,
        ensure_ascii=False,
        indent=2,
    )


def _nombre_base_informe(resultado: dict) -> str:
    """Obtiene un nombre base seguro a partir del archivo auditado."""

    nombre = str(resultado["dataset"]["archivo"])
    return Path(nombre).stem


def _mostrar_informes(resultado: dict) -> None:
    """Muestra la pestaña Informes."""

    st.markdown("## Informes")

    datos = st.session_state.get("datos_auditoria")

    if datos is None:
        st.error(
            "No están disponibles los datos originales de esta auditoría. "
            "Realiza una nueva auditoría para generar los informes."
        )
        return

    nombre_base = _nombre_base_informe(resultado)

    st.write(
        "Descarga los informes generados a partir de esta misma auditoría."
    )

    st.divider()

    html = generar_documento_html(
        resultado,
        datos,
    )
    json_informe = _generar_json_descarga(resultado)

    columna_html, columna_json, columna_impresion = st.columns(3)

    with columna_html:
        st.markdown("### Informe HTML")
        st.write("Informe completo y autónomo en formato HTML.")
        st.download_button(
            "⬇ Descargar informe HTML",
            data=html,
            file_name=f"{nombre_base}_auditoria.html",
            mime="text/html",
            use_container_width=True,
        )

    with columna_json:
        st.markdown("### Informe JSON")
        st.write(
            "Resultado estructurado de la auditoría "
            "en formato JSON v3.0."
        )
        st.download_button(
            "⬇ Descargar informe JSON",
            data=json_informe,
            file_name=f"{nombre_base}_auditoria.json",
            mime="application/json",
            use_container_width=True,
        )

    with columna_impresion:
        st.markdown("### Informe completo")
        st.write(
            "Versión completa de la auditoría preparada "
            "para impresión."
        )
        _boton_imprimir_informe_completo(html)


def _mostrar_pendiente(nombre: str) -> None:
    """Muestra temporalmente una pestaña todavía no implementada."""

    st.markdown(f"## {nombre}")
    st.info(
        f"La pestaña {nombre} se incorporará "
        "en el siguiente bloque de implementación."
    )


def mostrar_resultados(resultado: dict) -> None:
    """Muestra las cinco áreas de resultados de DataQualityPy."""

    _mostrar_cabecera(resultado)

    columna_nueva, columna_limpieza = st.columns([1, 1])

    with columna_nueva:
        if st.button(
            "← Nueva auditoría",
            use_container_width=True,
        ):
            claves_estado = [
                "resultado_auditoria",
                "datos_auditoria",
                "archivo_auditoria",
                "hoja_auditoria",
                "configuracion_auditoria",
                "plan_limpieza",
                "simulacion_limpieza",
                "datos_limpios",
                "resultado_limpieza",
                "resultado_auditoria_limpio",
            ]
            for clave in claves_estado:
                st.session_state.pop(clave, None)

            st.session_state["vista"] = "auditar"
            st.rerun()

    with columna_limpieza:
        if st.button(
            "🧹 Preparar limpieza",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.pop("simulacion_limpieza", None)
            st.session_state["vista"] = "limpieza"
            st.rerun()

    st.divider()

    # Navegación principal de resultados.
    # Se estilizan los atributos ARIA de las pestañas para no depender
    # de la estructura interna concreta de BaseWeb.
    st.markdown(
        """
        <style>
        /* Barra de navegación */
        div[data-testid="stTabs"] [role="tablist"] {
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.35rem !important;
            padding: 0.38rem !important;
            margin: 0.15rem 0 0.75rem 0 !important;
            width: auto !important;
            border: 1px solid rgba(128, 128, 128, 0.28) !important;
            border-radius: 12px !important;
            background: rgba(128, 128, 128, 0.08) !important;
            box-shadow: none !important;
        }

        /* Cada opción */
        div[data-testid="stTabs"] [role="tab"] {
            min-height: 2.65rem !important;
            height: 2.65rem !important;
            padding: 0 1rem !important;
            margin: 0 !important;
            border: 1px solid transparent !important;
            border-radius: 8px !important;
            background: transparent !important;
            box-shadow: none !important;
            font-weight: 600 !important;
            transition: background-color 0.15s ease, border-color 0.15s ease !important;
        }

        div[data-testid="stTabs"] [role="tab"]:hover {
            background: rgba(128, 128, 128, 0.14) !important;
            border-color: rgba(128, 128, 128, 0.20) !important;
        }

        /* Pestaña activa: bloque visible, no simple subrayado */
        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: rgba(77, 163, 255, 0.14) !important;
            border-color: rgba(77, 163, 255, 0.58) !important;
            box-shadow: inset 3px 0 0 #4da3ff !important;
        }

        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] p,
        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] span {
            color: #4da3ff !important;
            font-weight: 700 !important;
        }

        /* Oculta el indicador inferior nativo de BaseWeb. */
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] [role="tablist"] > div:last-child:not([role="tab"]) {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    (
        tab_resumen,
        tab_incidencias,
        tab_columnas,
        tab_cobertura,
        tab_informes,
    ) = st.tabs(
        [
            "Resumen",
            "Incidencias",
            "Columnas",
            "Cobertura",
            "Informes",
        ]
    )

    with tab_resumen:
        _mostrar_resumen(resultado)

    with tab_incidencias:
        _mostrar_incidencias(resultado)

    with tab_columnas:
        _mostrar_columnas(resultado)

    with tab_cobertura:
        _mostrar_cobertura(resultado)

    with tab_informes:
        _mostrar_informes(resultado)

