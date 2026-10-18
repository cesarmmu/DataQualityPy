"""Infraestructura compartida de impresión para las vistas de resultados."""

from html import escape
import json
import re
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components

from ui.results_common import (
    ETIQUETAS_CATEGORIAS,
    ETIQUETAS_SEVERIDADES,
    ETIQUETAS_TIPOS,
    ETIQUETAS_TIPOS_INCIDENCIA,
)
from ui.results_columns import (
    _buscar_estadisticas_columna,
    _formatear_nombre_estadistica,
    _formatear_valor_estadistico,
    _preparar_tabla_columnas,
)
from ui.results_coverage import (
    ETIQUETAS_CONTROLES,
    ETIQUETAS_ESTADOS_COBERTURA,
    _preparar_cobertura,
)
from ui.results_incidents import _preparar_incidencias_tabla


_CSS_BOTON_IMPRESION = """
    html, body {
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
    }

    .dq-print-button {
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
    }

    .dq-print-button:hover {
        border-color: rgba(250, 250, 250, 0.38);
        background: rgb(49, 51, 63);
    }

    .dq-print-button:active {
        background: rgb(58, 60, 73);
    }

    .dq-print-button:focus-visible {
        outline: 2px solid rgba(117, 183, 246, 0.9);
        outline-offset: 2px;
    }
"""


def _construir_documento_imprimible(
    titulo: str,
    contenido: str,
    estilos_documento: str = "",
) -> str:
    """Construye el documento HTML autónomo que abrirá el diálogo de impresión."""

    return f"""<!DOCTYPE html>
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
{estilos_documento}
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


def mostrar_boton_impresion(
    etiqueta: str,
    titulo: str,
    contenido: str,
    funcion_js: str,
    ancho: int | None = 300,
    *,
    id_boton: str | None = None,
    estilos_documento: str = "",
    ancho_completo: bool = False,
) -> None:
    """Muestra el botón común que abre un documento autónomo para imprimir."""

    documento = _construir_documento_imprimible(
        titulo,
        contenido,
        estilos_documento,
    )
    documento_json = json.dumps(documento).replace("</", "<\\/")

    atributo_id = f' id="{escape(id_boton)}"' if id_boton else ""
    css_ancho = """
        width: 100%;
        box-sizing: border-box;
    """ if ancho_completo else ""

    components.html(
        f"""
        <button{atributo_id} onclick="{funcion_js}()" class="dq-print-button">
            🖨️ {escape(etiqueta)}
        </button>

        <style>
            {_CSS_BOTON_IMPRESION}

            .dq-print-button {{
                {css_ancho}
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


def preparar_html_informe_para_impresion(html: str) -> str:
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


def mostrar_boton_imprimir_informe_completo(html: str) -> None:
    """Muestra el botón normalizado de impresión del informe completo."""

    documento = preparar_html_informe_para_impresion(html)
    documento_json = json.dumps(documento).replace("</", "<\\/")

    components.html(
        f"""
        <button onclick="imprimirInformeCompleto()" class="dq-print-button">
            🖨️ Imprimir informe completo
        </button>

        <style>
            {_CSS_BOTON_IMPRESION}

            .dq-print-button {{
                display: flex;
                width: 100%;
                box-sizing: border-box;
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

# ---------------------------------------------------------------------------
# Impresiones específicas de las pestañas de resultados
# ---------------------------------------------------------------------------

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

    mostrar_boton_impresion(
        etiqueta="Imprimir resumen",
        titulo="DataQualityPy_Resumen",
        contenido=contenido,
        funcion_js="imprimirResumen",
        ancho=220,
        id_boton="dq-print-summary-button",
        estilos_documento="""
    @media print {
        @page {
            size: A4;
            margin: 14mm;
        }
    }
""",
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

    mostrar_boton_impresion(
        etiqueta="Imprimir incidencias",
        titulo="DataQualityPy_Incidencias",
        contenido=contenido,
        funcion_js="imprimirIncidencias",
        ancho=230,
    )

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

    mostrar_boton_impresion(
        etiqueta=etiqueta,
        titulo=titulo,
        contenido=contenido,
        funcion_js=funcion_js,
        ancho=ancho,
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

    mostrar_boton_impresion(
        etiqueta="Imprimir cobertura",
        titulo="DataQualityPy_Cobertura",
        contenido=contenido,
        funcion_js="imprimirCobertura",
        ancho=230,
    )

def mostrar_boton_imprimir_resumen(resultado: dict) -> None:
    """Muestra la impresión de la pestaña Resumen."""
    _boton_imprimir_resumen(resultado)


def mostrar_boton_imprimir_incidencias(
    resultado: dict,
    incidencias: list[dict],
    severidad: str,
    categoria: str,
    columna: str,
) -> None:
    """Muestra la impresión de Incidencias respetando los filtros visibles."""
    _boton_imprimir_incidencias(
        resultado,
        incidencias,
        severidad,
        categoria,
        columna,
    )


def mostrar_botones_imprimir_columnas(
    resultado: dict,
    columna: object,
) -> None:
    """Muestra las dos impresiones disponibles en la pestaña Columnas."""
    columna_resumen, columna_detalle = st.columns(2)

    with columna_resumen:
        _boton_impresion_columnas(
            "Imprimir resumen de columnas",
            "DataQualityPy_Columnas",
            _html_resumen_columnas_imprimible(resultado),
            "imprimirResumenColumnas",
            300,
        )

    with columna_detalle:
        _boton_impresion_columnas(
            "Imprimir columna seleccionada",
            "DataQualityPy_Columna",
            _html_columna_imprimible(resultado, columna),
            "imprimirColumnaSeleccionada",
            300,
        )


def mostrar_boton_imprimir_cobertura(
    resultado: dict,
    cobertura_filtrada: list[dict],
    estado_seleccionado: str,
) -> None:
    """Muestra la impresión de Cobertura respetando el filtro visible."""
    _boton_imprimir_cobertura(
        resultado,
        cobertura_filtrada,
        estado_seleccionado,
    )

