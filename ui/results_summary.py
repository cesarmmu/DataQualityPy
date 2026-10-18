"""Pestaña Resumen de la interfaz de resultados de DataQualityPy."""

import streamlit as st

from ui.results_common import (
    ETIQUETAS_CATEGORIAS,
    ETIQUETAS_TIPOS,
    _tarjeta_indicador,
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

        proporcion = cantidad / maximo if maximo > 0 else 0.0
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


def mostrar_resumen(resultado: dict) -> None:
    """Muestra el contenido de la pestaña Resumen."""

    resumen = resultado["resumen"]

    st.markdown("## Resumen de auditoría")
    _mostrar_tarjetas_resumen(resumen)
    st.divider()
    _mostrar_distribuciones(resumen)
    st.divider()
    _mostrar_principales_incidencias(resumen)
    st.divider()
    _mostrar_cobertura_resumida(resumen)
