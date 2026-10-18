"""Pestaña de informes de los resultados de DataQualityPy."""

from collections.abc import Callable
from pathlib import Path

import streamlit as st

from src.html_report import generar_documento_html
from src.json_report import VERSION_INFORME, generar_documento_json


def _nombre_base_informe(resultado: dict) -> str:
    """Obtiene un nombre base seguro a partir del archivo auditado."""

    nombre = str(resultado["dataset"]["archivo"])
    return Path(nombre).stem


def mostrar_informes(
    resultado: dict,
    mostrar_boton_impresion: Callable[[str], None],
) -> str | None:
    """Muestra la pestaña Informes y devuelve el HTML generado."""

    st.markdown("## Informes")

    datos = st.session_state.get("datos_auditoria")

    if datos is None:
        st.error(
            "No están disponibles los datos originales de esta auditoría. "
            "Realiza una nueva auditoría para generar los informes."
        )
        return None

    nombre_base = _nombre_base_informe(resultado)

    st.write(
        "Descarga los informes generados a partir de esta misma auditoría."
    )

    st.divider()

    html = generar_documento_html(
        resultado,
        datos,
    )
    json_informe = generar_documento_json(resultado)

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
            f"en formato JSON v{VERSION_INFORME}."
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
        mostrar_boton_impresion(html)

    return html
