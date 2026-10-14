"""Pantalla principal de DataQualityPy V4."""

import streamlit as st


def mostrar_inicio() -> None:
    """Muestra el menú principal de DataQualityPy."""

    st.title("DataQualityPy")
    st.caption("Auditor de calidad de datos")

    st.markdown("### ¿Qué quieres hacer?")

    st.write("")

    if st.button(
        "🔎 Auditar dataset",
        type="primary",
        use_container_width=True,
    ):
        st.session_state["vista"] = "auditar"
        st.rerun()

    st.button(
        "⇄ Comparar datasets",
        disabled=True,
        use_container_width=True,
        help="Opción no disponible en esta versión.",
    )

    st.button(
        "◷ Histórico",
        disabled=True,
        use_container_width=True,
        help="Opción no disponible en esta versión.",
    )