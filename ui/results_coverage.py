"""Pestaña Cobertura de los resultados de DataQualityPy."""

import streamlit as st

from ui.results_common import _tarjeta_indicador


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


def mostrar_cobertura(resultado: dict) -> tuple[list[dict], str]:
    """Muestra la pestaña Cobertura y devuelve el estado visible para impresión."""

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

    return cobertura_filtrada, str(estado_seleccionado)

