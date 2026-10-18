"""Pestaña Incidencias de la interfaz de resultados de DataQualityPy."""

import streamlit as st

from ui.results_common import (
    ETIQUETAS_CATEGORIAS,
    ETIQUETAS_SEVERIDADES,
    ETIQUETAS_TIPOS_INCIDENCIA,
    _formatear_etiqueta,
    _tarjeta_indicador,
)


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


def _buscar_diagnostico_incidencia(
    resultado: dict,
    incidencia: dict,
) -> dict | None:
    """Localiza el diagnóstico ya calculado para una incidencia."""
    diagnosticos = (
        resultado.get("analisis_avanzado", {})
        .get("diagnosticos", [])
    )

    for diagnostico in diagnosticos:
        if (
            diagnostico.get("tipo_incidencia") == incidencia.get("tipo")
            and diagnostico.get("columna") == incidencia.get("columna")
            and diagnostico.get("mensaje_incidencia") == incidencia.get("mensaje")
        ):
            return diagnostico

    return None


def _mostrar_explicabilidad_diagnostico(
    diagnostico: dict | None,
) -> None:
    """Muestra la explicación y evidencias V7 de un diagnóstico."""
    if not diagnostico:
        return

    explicacion = diagnostico.get("explicacion")
    explicacion_severidad = diagnostico.get("explicacion_severidad")
    evidencias = diagnostico.get("evidencias") or []

    if explicacion:
        st.markdown("#### ¿Por qué se ha detectado?")
        st.write(explicacion)

    if explicacion_severidad:
        st.markdown("#### ¿Por qué tiene esta severidad?")
        st.write(explicacion_severidad)

    if evidencias:
        st.markdown("#### Evidencias del diagnóstico")
        filas = [
            {
                "Evidencia": evidencia.get(
                    "etiqueta",
                    evidencia.get("clave", ""),
                ),
                "Valor": evidencia.get("valor", ""),
                "Fuente": evidencia.get("fuente", ""),
            }
            for evidencia in evidencias
        ]
        st.dataframe(
            filas,
            use_container_width=True,
            hide_index=True,
        )


def _mostrar_detalle_incidencia(
    resultado: dict,
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

    diagnostico = _buscar_diagnostico_incidencia(
        resultado,
        incidencia,
    )
    _mostrar_explicabilidad_diagnostico(diagnostico)


def mostrar_incidencias(
    resultado: dict,
) -> tuple[list[dict], str, str, str] | None:
    """Muestra Incidencias y devuelve el estado necesario para imprimir."""

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

        _mostrar_detalle_incidencia(
            resultado,
            incidencias_filtradas,
        )

    else:
        st.info(
            "No hay incidencias que coincidan con los filtros seleccionados."
        )

    st.divider()

    return (
        incidencias_filtradas,
        severidad,
        categoria,
        columna,
    )
