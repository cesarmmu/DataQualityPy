"""Pestaña Columnas de la interfaz de resultados de DataQualityPy."""

import streamlit as st

from ui.results_common import (
    ETIQUETAS_TIPOS,
    _formatear_porcentaje_ui,
    _tarjeta_indicador,
)
from ui.results_incidents import _preparar_incidencias_tabla


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


def mostrar_columnas(resultado: dict) -> object | None:
    """Muestra Columnas y devuelve la columna seleccionada para impresión."""

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

    return columna_seleccionada
