"""Punto de entrada de DataQualityPy V5."""

import streamlit as st

from ui.audit_view import mostrar_auditoria
from ui.cleaning_view import mostrar_preparar_limpieza
from ui.home import mostrar_inicio
from ui.results import mostrar_resultados


def configurar_aplicacion() -> None:
    """Configura los parámetros generales de la interfaz."""

    st.set_page_config(
        page_title="DataQualityPy",
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def inicializar_estado() -> None:
    """Inicializa el estado mínimo de navegación."""

    if "vista" not in st.session_state:
        st.session_state["vista"] = "inicio"


def main() -> None:
    """Ejecuta la interfaz de DataQualityPy V5."""

    configurar_aplicacion()
    inicializar_estado()

    vista = st.session_state["vista"]

    if vista == "auditar":
        mostrar_auditoria()

    elif vista == "resultados":
        resultado = st.session_state.get("resultado_auditoria")

        if resultado is None:
            st.session_state["vista"] = "auditar"
            st.rerun()

        mostrar_resultados(resultado)

    elif vista == "limpieza":
        resultado = st.session_state.get("resultado_auditoria")
        datos = st.session_state.get("datos_auditoria")

        if resultado is None or datos is None:
            st.session_state["vista"] = "auditar"
            st.rerun()

        mostrar_preparar_limpieza()

    else:
        mostrar_inicio()


if __name__ == "__main__":
    main()
