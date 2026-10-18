"""Coordinador de las pantallas de resultados de DataQualityPy V7."""

import streamlit as st

from ui.results_columns import mostrar_columnas
from ui.results_coverage import mostrar_cobertura
from ui.results_incidents import mostrar_incidencias
from ui.results_reports import mostrar_informes
from ui.results_print import (
    mostrar_boton_imprimir_cobertura,
    mostrar_boton_imprimir_incidencias,
    mostrar_boton_imprimir_informe_completo,
    mostrar_boton_imprimir_resumen,
    mostrar_botones_imprimir_columnas,
)
from ui.results_summary import mostrar_resumen


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


def _reiniciar_auditoria() -> None:
    """Limpia el estado asociado a la auditoría actual."""
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


def _preparar_limpieza() -> None:
    """Abre la vista de limpieza desde la auditoría actual."""
    st.session_state.pop("simulacion_limpieza", None)
    st.session_state["vista"] = "limpieza"
    st.rerun()


def _mostrar_navegacion_acciones() -> None:
    """Muestra las acciones principales disponibles desde resultados."""
    columna_nueva, columna_limpieza = st.columns([1, 1])

    with columna_nueva:
        if st.button(
            "← Nueva auditoría",
            use_container_width=True,
        ):
            _reiniciar_auditoria()

    with columna_limpieza:
        if st.button(
            "🧹 Preparar limpieza",
            type="primary",
            use_container_width=True,
        ):
            _preparar_limpieza()


def _aplicar_estilos_pestanas() -> None:
    """Aplica el estilo visual de la navegación principal."""
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
            transition:
                background-color 0.15s ease,
                border-color 0.15s ease !important;
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
        div[data-testid="stTabs"]
        [role="tablist"] > div:last-child:not([role="tab"]) {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def mostrar_resultados(resultado: dict) -> None:
    """Muestra las cinco áreas de resultados de DataQualityPy."""
    _mostrar_cabecera(resultado)
    _mostrar_navegacion_acciones()

    st.divider()
    _aplicar_estilos_pestanas()

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
        mostrar_resumen(resultado)
        st.divider()
        mostrar_boton_imprimir_resumen(resultado)

    with tab_incidencias:
        estado_incidencias = mostrar_incidencias(resultado)
        if estado_incidencias is not None:
            (
                incidencias_filtradas,
                severidad,
                categoria,
                columna,
            ) = estado_incidencias
            mostrar_boton_imprimir_incidencias(
                resultado,
                incidencias_filtradas,
                severidad,
                categoria,
                columna,
            )

    with tab_columnas:
        columna_seleccionada = mostrar_columnas(resultado)
        if columna_seleccionada is not None:
            st.divider()
            mostrar_botones_imprimir_columnas(
                resultado,
                columna_seleccionada,
            )

    with tab_cobertura:
        cobertura_filtrada, estado_seleccionado = mostrar_cobertura(resultado)
        mostrar_boton_imprimir_cobertura(
            resultado,
            cobertura_filtrada,
            estado_seleccionado,
        )

    with tab_informes:
        mostrar_informes(
            resultado,
            mostrar_boton_imprimir_informe_completo,
        )
