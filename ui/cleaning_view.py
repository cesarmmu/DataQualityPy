"""Interfaz de preparación de limpieza controlada de DataQualityPy V5."""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Any

import pandas as pd
import streamlit as st

from src.audit import auditar_dataset
from src.cleaning import CleaningError, ejecutar_plan_limpieza
from src.cleaning_plan import CleaningPlan, CleaningPlanError
from src.cleaning_export import (
    ErrorExportacionLimpieza,
    exportar_dataset_limpio,
)
from src.cleaning_report import (
    construir_trazabilidad_limpieza,
    generar_html_limpieza,
    generar_json_limpieza,
    generar_nombres_informes,
)


TIPOS_TEXTO = {"object", "string"}

NOMBRES_OPERACIONES = {
    "eliminar_espacios_externos": "Eliminar espacios externos",
    "normalizar_espacios_internos": "Normalizar espacios internos",
    "minusculas": "Convertir a minúsculas",
    "mayusculas": "Convertir a MAYÚSCULAS",
    "capitalizar": "Capitalizar",
    "titulo": "Formato título",
    "eliminar_tildes": "Eliminar tildes",
    "sustituir_caracteres": "Sustituir caracteres",
    "reemplazar_valor": "Reemplazar valor",
    "reemplazar_por_nulo": "Reemplazar por nulo real",
    "numerico": "Convertir a numérico",
    "fecha": "Convertir a fecha",
    "fecha_hora": "Convertir a fecha y hora",
    "texto": "Convertir a texto",
    "booleano": "Convertir a booleano",
    "eliminar_filas": "Eliminar filas",
    "media": "Rellenar con media",
    "mediana": "Rellenar con mediana",
    "moda": "Rellenar con moda",
    "eliminar_duplicados_completos": "Eliminar duplicados completos",
}


def _obtener_plan() -> CleaningPlan:
    """Obtiene o inicializa el plan de limpieza de la sesión."""
    plan = st.session_state.get("plan_limpieza")
    if not isinstance(plan, CleaningPlan):
        plan = CleaningPlan()
        st.session_state["plan_limpieza"] = plan
    return plan


def _columnas_texto(datos: pd.DataFrame) -> list[str]:
    """Devuelve las columnas de texto disponibles."""
    return [
        str(columna)
        for columna in datos.columns
        if (
            pd.api.types.is_object_dtype(datos[columna])
            or isinstance(datos[columna].dtype, pd.StringDtype)
        )
    ]


def _tipo_semantico(resultado: dict[str, Any], columna: str) -> str:
    info = resultado.get("tipos_semanticos", {}).get(columna, {})
    return str(info.get("tipo", "No determinado"))


def _valor_visible(valor: Any) -> str:
    if pd.isna(valor):
        return "<NULO>"
    texto = str(valor)
    if texto != "" and texto.strip() == "":
        return "<ESPACIOS EN BLANCO>"
    if texto == "":
        return "<CADENA VACÍA>"
    return texto if len(texto) <= 80 else f"{texto[:77]}..."


def _valores_distintos(serie: pd.Series, limite: int = 200) -> list[Any]:
    """Obtiene valores no nulos conservando su representación original."""
    valores = serie.dropna().drop_duplicates().tolist()
    return valores[:limite]


def _contar_valor(serie: pd.Series, valor: Any) -> int:
    try:
        return int(serie.eq(valor).fillna(False).sum())
    except (TypeError, ValueError):
        return 0


def _operacion_equivalente(
    plan: CleaningPlan,
    familia: str,
    tipo: str,
    columna: str,
    parametros: dict[str, Any] | None = None,
) -> bool:
    parametros = {} if parametros is None else parametros
    return any(
        operacion.familia == familia
        and operacion.tipo == tipo
        and operacion.columna == columna
        and operacion.parametros == parametros
        for operacion in plan.operaciones
    )


def _agregar_operacion(
    plan: CleaningPlan,
    familia: str,
    tipo: str,
    columna: str,
    parametros: dict[str, Any] | None = None,
) -> None:
    parametros = {} if parametros is None else parametros

    if _operacion_equivalente(
        plan,
        familia,
        tipo,
        columna,
        parametros,
    ):
        st.info("Esa operación ya forma parte del plan.")
        return

    try:
        plan.crear_operacion(
            familia,
            tipo,
            columna,
            parametros,
        )
    except CleaningPlanError as exc:
        st.error(str(exc))
        return

    st.session_state["plan_limpieza"] = plan
    st.session_state.pop("simulacion_limpieza", None)
    st.session_state["mensaje_plan_limpieza"] = "Operación añadida al plan."
    st.rerun()


def _mostrar_cabecera(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
) -> None:
    st.title("🧹 Preparar limpieza")
    st.caption(
        "Define únicamente las transformaciones que quieras aplicar. "
        "El dataset original no se modifica."
    )

    archivo = st.session_state.get(
        "archivo_auditoria",
        resultado.get("dataset", {}).get("archivo", "Dataset"),
    )
    hoja = st.session_state.get("hoja_auditoria")

    columnas = st.columns(4)
    columnas[0].metric("Archivo", archivo)
    columnas[1].metric("Filas", f"{len(datos):,}".replace(",", "."))
    columnas[2].metric("Columnas", len(datos.columns))
    columnas[3].metric(
        "Incidencias",
        len(resultado.get("incidencias", [])),
    )

    if hoja is not None:
        st.caption(f"Hoja de Excel auditada: **{hoja}**")

    st.info(
        "Trabajaremos sobre una copia en memoria. "
        "El archivo y los datos originales permanecerán sin cambios."
    )


def _mostrar_texto(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    st.subheader("Texto")
    st.caption(
        "Normaliza formato y caracteres de columnas de texto. "
        "Ninguna transformación se selecciona automáticamente."
    )

    columnas_texto = _columnas_texto(datos)
    if not columnas_texto:
        st.info("El dataset no contiene columnas de texto.")
        return

    problemas_texto = resultado.get("calidad", {}).get("texto", {})
    sugeridas = [
        columna
        for columna in columnas_texto
        if columna in problemas_texto
        and (
            problemas_texto[columna].get("valores_con_espacios", 0) > 0
            or problemas_texto[columna].get(
                "posibles_diferencias_mayusculas",
                False,
            )
            or problemas_texto[columna].get("grupos_inconsistentes")
        )
    ]

    columna = st.selectbox(
        "Columna",
        columnas_texto,
        index=(
            columnas_texto.index(sugeridas[0])
            if sugeridas
            else 0
        ),
        key="limpieza_texto_columna",
    )

    info = problemas_texto.get(columna, {})
    tipo = _tipo_semantico(resultado, columna)
    espacios = int(info.get("valores_con_espacios", 0))
    diferencias = bool(
        info.get("posibles_diferencias_mayusculas", False)
    )
    grupos = info.get("grupos_inconsistentes", [])

    c1, c2, c3 = st.columns(3)
    c1.metric("Tipo semántico", tipo)
    c2.metric("Valores con espacios", espacios)
    c3.metric("Grupos inconsistentes", len(grupos))

    if diferencias:
        st.caption(
            "La auditoría ha detectado posibles diferencias de "
            "mayúsculas/minúsculas."
        )

    serie = datos[columna]

    with st.expander("Ver muestra de valores actuales"):
        muestra = serie.dropna().astype(str).drop_duplicates().head(10)
        if muestra.empty:
            st.caption("No hay valores no nulos para mostrar.")
        else:
            st.dataframe(
                pd.DataFrame({"Valor actual": muestra.tolist()}),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("**Espacios**")
    col_a, col_b = st.columns(2)

    if col_a.button(
        "Añadir: eliminar espacios externos",
        use_container_width=True,
        key=f"txt_strip_{columna}",
    ):
        _agregar_operacion(
            plan,
            "texto",
            "eliminar_espacios_externos",
            columna,
        )

    if col_b.button(
        "Añadir: normalizar espacios internos",
        use_container_width=True,
        key=f"txt_spaces_{columna}",
    ):
        _agregar_operacion(
            plan,
            "texto",
            "normalizar_espacios_internos",
            columna,
        )

    st.markdown("**Formato de mayúsculas y minúsculas**")
    formato = st.radio(
        "Transformación",
        [
            "Mantener",
            "minúsculas",
            "MAYÚSCULAS",
            "Capitalizar",
            "Formato título",
        ],
        horizontal=True,
        key=f"txt_case_{columna}",
    )

    mapa_formato = {
        "minúsculas": "minusculas",
        "MAYÚSCULAS": "mayusculas",
        "Capitalizar": "capitalizar",
        "Formato título": "titulo",
    }

    if formato != "Mantener":
        if st.button(
            "Añadir formato al plan",
            key=f"txt_case_add_{columna}",
        ):
            _agregar_operacion(
                plan,
                "texto",
                mapa_formato[formato],
                columna,
            )

    st.markdown("**Otros ajustes controlados**")
    col_c, col_d = st.columns(2)

    if col_c.button(
        "Añadir: eliminar tildes",
        use_container_width=True,
        key=f"txt_accents_{columna}",
    ):
        _agregar_operacion(
            plan,
            "texto",
            "eliminar_tildes",
            columna,
        )

    with col_d:
        with st.popover("Sustituir caracteres", use_container_width=True):
            origen = st.text_input(
                "Texto o carácter de origen",
                key=f"txt_char_from_{columna}",
            )
            destino = st.text_input(
                "Destino",
                key=f"txt_char_to_{columna}",
                help="Puede dejarse vacío para eliminar el carácter.",
            )

            if origen:
                afectados = int(
                    serie.dropna()
                    .astype(str)
                    .str.contains(origen, regex=False)
                    .sum()
                )
                st.caption(
                    f"Valores actuales afectados: {afectados}"
                )

                ejemplos = (
                    serie.dropna()
                    .astype(str)
                    .loc[
                        lambda s: s.str.contains(
                            origen,
                            regex=False,
                        )
                    ]
                    .drop_duplicates()
                    .head(5)
                )
                if not ejemplos.empty:
                    previa = pd.DataFrame(
                        {
                            "Antes": ejemplos.tolist(),
                            "Después": [
                                valor.replace(origen, destino)
                                for valor in ejemplos.tolist()
                            ],
                        }
                    )
                    st.dataframe(
                        previa,
                        use_container_width=True,
                        hide_index=True,
                    )

            if st.button(
                "Añadir sustitución de caracteres",
                key=f"txt_char_add_{columna}",
            ):
                _agregar_operacion(
                    plan,
                    "texto",
                    "sustituir_caracteres",
                    columna,
                    {"origen": origen, "destino": destino},
                )


def _hay_conflicto_sustitucion(
    plan: CleaningPlan,
    columna: str,
    origen: Any,
    destino: Any,
) -> bool:
    for operacion in plan.operaciones:
        if (
            operacion.familia == "sustitucion"
            and operacion.columna == columna
            and operacion.parametros.get("origen") == origen
        ):
            destino_existente = (
                None
                if operacion.tipo == "reemplazar_por_nulo"
                else operacion.parametros.get("destino")
            )
            if destino_existente != destino:
                return True
    return False


def _mostrar_sustituciones(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    st.subheader("Sustituciones")
    st.caption(
        "Define equivalencias explícitas entre valores. "
        "DataQualityPy no agrupa categorías automáticamente."
    )

    columnas = [str(columna) for columna in datos.columns]
    columna = st.selectbox(
        "Columna para sustitución",
        columnas,
        key="limpieza_sust_columna",
    )
    serie = datos[columna]

    valores = _valores_distintos(serie)
    if not valores:
        st.info("La columna no contiene valores no nulos.")
        return

    indice = st.selectbox(
        "Valor de origen",
        range(len(valores)),
        format_func=lambda i: _valor_visible(valores[i]),
        key=f"sust_origen_{columna}",
    )
    origen = valores[indice]
    afectados = _contar_valor(serie, origen)

    st.caption(
        f"Registros actuales con este valor: **{afectados}** · "
        f"Tipo semántico: **{_tipo_semantico(resultado, columna)}**"
    )

    modo = st.radio(
        "Destino",
        [
            "Valor existente",
            "Nuevo valor",
            "Nulo real",
        ],
        horizontal=True,
        key=f"sust_modo_{columna}",
    )

    destino: Any = None
    tipo_operacion = "reemplazar_por_nulo"

    if modo == "Valor existente":
        candidatos = [
            valor
            for valor in valores
            if valor != origen
        ]
        if candidatos:
            indice_destino = st.selectbox(
                "Valor de destino",
                range(len(candidatos)),
                format_func=lambda i: _valor_visible(candidatos[i]),
                key=f"sust_dest_exist_{columna}",
            )
            destino = candidatos[indice_destino]
            tipo_operacion = "reemplazar_valor"
        else:
            st.info(
                "No hay otro valor existente disponible. "
                "Utiliza Nuevo valor o Nulo real."
            )

    elif modo == "Nuevo valor":
        destino = st.text_input(
            "Nuevo valor",
            key=f"sust_dest_new_{columna}",
        )
        tipo_operacion = "reemplazar_valor"

    if modo != "Valor existente" or candidatos:
        texto_destino = (
            "<NULO REAL>"
            if modo == "Nulo real"
            else _valor_visible(destino)
        )
        st.caption(
            f"Vista previa: {_valor_visible(origen)} → {texto_destino}"
        )

        if st.button(
            "Añadir sustitución al plan",
            key=f"sust_add_{columna}",
        ):
            if (
                tipo_operacion == "reemplazar_valor"
                and destino == origen
            ):
                st.warning(
                    "El valor de origen y el de destino son iguales."
                )
            elif _hay_conflicto_sustitucion(
                plan,
                columna,
                origen,
                destino,
            ):
                st.warning(
                    "Ya existe en el plan otra sustitución para "
                    "ese mismo valor de origen."
                )
            else:
                parametros = {"origen": origen}
                if tipo_operacion == "reemplazar_valor":
                    parametros["destino"] = destino

                _agregar_operacion(
                    plan,
                    "sustitucion",
                    tipo_operacion,
                    columna,
                    parametros,
                )



def _reemplazar_operacion_familia_columna(
    plan: CleaningPlan,
    familia: str,
    tipo: str,
    columna: str,
    parametros: dict[str, Any] | None = None,
) -> None:
    """Mantiene una sola decisión de una familia por columna."""
    parametros = {} if parametros is None else parametros
    anteriores = [
        operacion.id
        for operacion in plan.operaciones
        if operacion.familia == familia
        and operacion.columna == columna
    ]
    for operacion_id in anteriores:
        plan.eliminar_operacion(operacion_id)

    try:
        plan.crear_operacion(familia, tipo, columna, parametros)
    except CleaningPlanError as exc:
        st.error(str(exc))
        return

    st.session_state["plan_limpieza"] = plan
    st.session_state.pop("simulacion_limpieza", None)
    st.session_state["mensaje_plan_limpieza"] = "Decisión actualizada en el plan."
    st.rerun()


def _valores_incompatibles_conversion(
    serie: pd.Series,
    destino: str,
    formato: str | None = None,
) -> tuple[pd.Series, int, float, list[str]]:
    """Calcula incompatibilidades sin modificar los datos."""
    no_nulos = serie.notna()

    if destino == "numerico":
        convertida = pd.to_numeric(serie, errors="coerce")
        incompatibles = no_nulos & convertida.isna()

    elif destino in {"fecha", "fecha_hora"}:
        kwargs: dict[str, Any] = {"errors": "coerce"}
        if formato:
            kwargs["format"] = formato
        convertida = pd.to_datetime(serie, **kwargs)
        incompatibles = no_nulos & convertida.isna()

    elif destino == "booleano":
        verdaderos = {True, 1, "1", "true", "True", "TRUE"}
        falsos = {False, 0, "0", "false", "False", "FALSE"}
        compatibles = serie.map(
            lambda valor: (
                True
                if pd.isna(valor)
                else valor in verdaderos or valor in falsos
            )
        )
        incompatibles = no_nulos & ~compatibles

    else:
        incompatibles = pd.Series(False, index=serie.index)

    cantidad = int(incompatibles.sum())
    base = int(no_nulos.sum())
    porcentaje = round(cantidad / base * 100, 2) if base else 0.0
    ejemplos = (
        serie.loc[incompatibles]
        .astype(str)
        .drop_duplicates()
        .head(10)
        .tolist()
    )
    return incompatibles, cantidad, porcentaje, ejemplos


def _datos_antes_de_nulos(
    datos: pd.DataFrame,
    plan: CleaningPlan,
) -> tuple[pd.DataFrame, str | None]:
    """
    Devuelve el estado previsto justo antes de ejecutar la familia Nulos.

    Se aplican únicamente las operaciones anteriores del plan:
    Texto -> Sustitución -> Conversión.
    """
    operaciones_previas = [
        operacion
        for operacion in plan.operaciones_ordenadas()
        if operacion.orden_ejecucion < 4
    ]

    if not operaciones_previas:
        return datos.copy(deep=True), None

    plan_previo = CleaningPlan(operaciones=list(operaciones_previas))

    try:
        previstos, _ = ejecutar_plan_limpieza(datos, plan_previo)
    except CleaningError as exc:
        return datos.copy(deep=True), str(exc)

    return previstos, None


def _mostrar_nulos(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    st.subheader("Nulos")
    st.caption(
        "Decide de forma explícita cómo tratar los nulos reales y, "
        "si existen, los posibles marcadores textuales de nulo."
    )

    nulos_textuales = resultado.get("calidad", {}).get(
        "nulos_textuales",
        {},
    )

    candidatas = [
        str(columna)
        for columna in datos.columns
        if datos[columna].isna().any()
        or columna in nulos_textuales
    ]

    if not candidatas:
        st.success("La auditoría no ha detectado nulos que requieran revisión.")
        return

    columna = st.selectbox(
        "Columna",
        candidatas,
        key="limpieza_nulos_columna",
    )

    serie_original = datos[columna]
    datos_previstos, error_previo = _datos_antes_de_nulos(datos, plan)

    if error_previo:
        st.error(
            "No puede calcularse el estado previsto anterior al tratamiento "
            f"de nulos. Motivo: {error_previo}"
        )
        serie_prevista = serie_original
    else:
        serie_prevista = datos_previstos[columna]

    reales_originales = int(serie_original.isna().sum())
    reales_previstos = int(serie_prevista.isna().sum())
    porcentaje_previsto = (
        round(reales_previstos / len(serie_prevista) * 100, 2)
        if len(serie_prevista)
        else 0.0
    )

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Nulos reales previstos",
        reales_previstos,
        delta=(
            reales_previstos - reales_originales
            if reales_previstos != reales_originales
            else None
        ),
    )
    c2.metric("Porcentaje previsto", f"{porcentaje_previsto:.2f} %")
    c3.metric("Tipo semántico", _tipo_semantico(resultado, columna))

    if reales_previstos != reales_originales:
        st.caption(
            f"Dataset original: {reales_originales} nulos reales. "
            f"Estado previsto antes de Nulos: {reales_previstos}. "
            "La previsión incorpora Texto, Sustituciones y Conversiones "
            "ya incluidas en el plan."
        )

    info_textual = nulos_textuales.get(columna, {})
    marcadores = info_textual.get("marcadores_detectados", {})

    if marcadores:
        with st.expander("Nulos textuales detectados", expanded=True):
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Marcador": marcador, "Registros": cantidad}
                        for marcador, cantidad in marcadores.items()
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
            seleccion = st.multiselect(
                "Convertir estos marcadores a nulo real",
                list(marcadores.keys()),
                key=f"nulos_textuales_{columna}",
            )
            if st.button(
                "Añadir conversión de marcadores al plan",
                key=f"nulos_textuales_add_{columna}",
            ):
                añadidas = 0
                valores_reales: list[Any] = []

                for marcador in seleccion:
                    if marcador == "espacios_en_blanco":
                        valores_reales.extend(
                            serie_original.loc[
                                serie_original.notna()
                                & serie_original.astype(str).str.strip().eq("")
                            ]
                            .drop_duplicates()
                            .tolist()
                        )
                    else:
                        valores_reales.extend(
                            serie_original.loc[
                                serie_original.notna()
                                & serie_original.astype(str)
                                .str.strip()
                                .str.lower()
                                .eq(str(marcador).lower())
                            ]
                            .drop_duplicates()
                            .tolist()
                        )

                for valor in valores_reales:
                    if not _operacion_equivalente(
                        plan,
                        "sustitucion",
                        "reemplazar_por_nulo",
                        columna,
                        {"origen": valor},
                    ):
                        plan.crear_operacion(
                            "sustitucion",
                            "reemplazar_por_nulo",
                            columna,
                            {"origen": valor},
                        )
                        añadidas += 1

                st.session_state["plan_limpieza"] = plan
                st.session_state.pop("simulacion_limpieza", None)

                if añadidas:
                    st.session_state["mensaje_plan_limpieza"] = (
                        f"{añadidas} conversión(es) de marcador añadida(s)."
                    )
                    st.rerun()
                else:
                    st.info("No se añadieron operaciones nuevas.")

    st.markdown("**Tratamiento de nulos reales**")
    opcion = st.radio(
        "Decisión",
        [
            "Mantener",
            "Eliminar filas",
            "Reemplazar por un valor",
            "Media",
            "Mediana",
            "Moda",
        ],
        horizontal=True,
        key=f"nulos_accion_{columna}",
    )

    if opcion == "Mantener":
        st.caption("No se añadirá ninguna operación para los nulos reales.")
        return

    parametros: dict[str, Any] = {}
    mapa = {
        "Eliminar filas": "eliminar_filas",
        "Reemplazar por un valor": "reemplazar_valor",
        "Media": "media",
        "Mediana": "mediana",
        "Moda": "moda",
    }
    tipo = mapa[opcion]
    operacion_valida = error_previo is None

    if opcion == "Reemplazar por un valor":
        valor = st.text_input(
            "Valor de reemplazo",
            key=f"nulos_valor_{columna}",
        )
        parametros["valor"] = valor

    if opcion in {"Media", "Mediana"}:
        no_nulos = serie_prevista.dropna()
        numerica = pd.to_numeric(no_nulos, errors="coerce")

        if numerica.notna().sum() != len(no_nulos):
            operacion_valida = False
            st.warning(
                "Esta opción no puede aplicarse porque, después de las "
                "operaciones anteriores del plan, todavía existen valores "
                "no numéricos en la columna."
            )
        elif numerica.empty:
            operacion_valida = False
            st.warning(
                "Esta opción no puede aplicarse porque no hay valores "
                "numéricos disponibles para calcularla."
            )
        else:
            estimado = (
                numerica.mean()
                if opcion == "Media"
                else numerica.median()
            )
            st.caption(
                "Valor previsto que se utilizaría: "
                f"{estimado:g}"
            )

    if opcion == "Moda":
        moda = serie_prevista.dropna().mode()
        if moda.empty:
            operacion_valida = False
            st.warning(
                "No puede calcularse la moda porque no hay valores "
                "disponibles."
            )
        else:
            st.caption(
                f"Moda prevista: {_valor_visible(moda.iloc[0])}"
            )

    if reales_previstos == 0:
        operacion_valida = False
        st.info(
            "En el estado previsto no existen nulos reales que tratar "
            "en esta columna."
        )

    if st.button(
        "Guardar tratamiento de nulos",
        key=f"nulos_add_{columna}",
        disabled=not operacion_valida,
    ):
        _reemplazar_operacion_familia_columna(
            plan,
            "nulos",
            tipo,
            columna,
            parametros,
        )

def _mostrar_conversiones(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    st.subheader("Conversiones")
    st.caption(
        "Convierte tipos de forma controlada. Los valores incompatibles "
        "nunca se descartan silenciosamente."
    )

    columnas = [str(columna) for columna in datos.columns]
    columna = st.selectbox(
        "Columna",
        columnas,
        key="limpieza_conversion_columna",
    )
    serie = datos[columna]

    c1, c2, c3 = st.columns(3)
    c1.metric("dtype actual", str(serie.dtype))
    c2.metric("Tipo semántico", _tipo_semantico(resultado, columna))
    c3.metric("Valores no nulos", int(serie.notna().sum()))

    etiqueta_destino = st.selectbox(
        "Tipo de destino",
        [
            "Numérico",
            "Fecha",
            "Fecha y hora",
            "Texto",
            "Booleano",
        ],
        key=f"conversion_destino_{columna}",
    )
    mapa_destino = {
        "Numérico": "numerico",
        "Fecha": "fecha",
        "Fecha y hora": "fecha_hora",
        "Texto": "texto",
        "Booleano": "booleano",
    }
    destino = mapa_destino[etiqueta_destino]
    parametros: dict[str, Any] = {}

    formato: str | None = None
    if destino in {"fecha", "fecha_hora"}:
        formato_ui = st.selectbox(
            "Formato de fecha",
            [
                "Automático",
                "DD/MM/YYYY",
                "YYYY-MM-DD",
                "MM/DD/YYYY",
                "Personalizado",
            ],
            key=f"conversion_formato_{columna}",
        )
        formatos = {
            "DD/MM/YYYY": "%d/%m/%Y",
            "YYYY-MM-DD": "%Y-%m-%d",
            "MM/DD/YYYY": "%m/%d/%Y",
        }
        if formato_ui == "Personalizado":
            formato = st.text_input(
                "Formato strptime",
                placeholder="%d/%m/%Y %H:%M:%S",
                key=f"conversion_formato_custom_{columna}",
            ) or None
        else:
            formato = formatos.get(formato_ui)

        if formato is not None:
            parametros["formato"] = formato
        elif formato_ui == "Automático":
            st.warning(
                "El modo automático puede ser ambiguo en fechas como "
                "01/02/2026. Si conoces el formato, es preferible indicarlo."
            )

    if destino == "texto":
        st.info(
            "La conversión a texto no puede recuperar ceros a la izquierda "
            "que ya se hubieran perdido en una conversión anterior."
        )

    incompatibles, cantidad, porcentaje, ejemplos = (
        _valores_incompatibles_conversion(
            serie,
            destino,
            formato,
        )
    )
    compatibles = int(serie.notna().sum()) - cantidad

    a, b, c = st.columns(3)
    a.metric("Convertibles", compatibles)
    b.metric("Incompatibles", cantidad)
    c.metric("% incompatibles", f"{porcentaje:.2f} %")

    if ejemplos:
        st.warning(
            "Ejemplos incompatibles: "
            + ", ".join(ejemplos[:10])
        )

    if destino == "booleano" and cantidad:
        st.caption(
            "Para valores booleanos no estándar, corrígelos antes mediante "
            "Sustituciones o autoriza su conversión a nulo."
        )

    permitir_nulo = False
    if cantidad:
        permitir_nulo = st.checkbox(
            "Autorizo convertir los valores incompatibles a nulo real",
            key=f"conversion_nulo_{columna}_{destino}",
        )
        parametros["incompatibles_a_nulo"] = permitir_nulo

    if st.button(
        "Guardar conversión",
        key=f"conversion_add_{columna}_{destino}",
    ):
        if cantidad and not permitir_nulo:
            st.warning(
                "Resuelve primero los valores incompatibles o autoriza "
                "explícitamente su conversión a nulo."
            )
        else:
            _reemplazar_operacion_familia_columna(
                plan,
                "conversion",
                destino,
                columna,
                parametros,
            )


def _mostrar_outliers(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    st.subheader("Outliers")
    st.caption(
        "La decisión predeterminada es conservarlos. Solo se eliminan "
        "filas cuando lo autorizas expresamente."
    )

    outliers = resultado.get("calidad", {}).get("outliers", {})
    if not outliers:
        st.success(
            "La auditoría no ha detectado columnas numéricas semánticas "
            "con outliers IQR."
        )
        return

    columnas = list(outliers.keys())
    columna = st.selectbox(
        "Columna",
        columnas,
        key="limpieza_outliers_columna",
    )
    info = outliers[columna]

    cantidad = int(info.get("cantidad_outliers", 0))
    porcentaje = float(info.get("porcentaje_outliers", 0.0))
    q1 = info.get("q1")
    q3 = info.get("q3")
    iqr = info.get("iqr")
    inferior = info.get("limite_inferior")
    superior = info.get("limite_superior")

    a, b, c, d = st.columns(4)
    a.metric("Outliers", cantidad)
    b.metric("Porcentaje", f"{porcentaje:.2f} %")
    c.metric("Q1", f"{q1:g}" if q1 is not None else "—")
    d.metric("Q3", f"{q3:g}" if q3 is not None else "—")

    st.caption(
        f"IQR: {iqr:g} · Límites: {inferior:g} a {superior:g}"
        if None not in {iqr, inferior, superior}
        else "Límites IQR no disponibles."
    )

    serie = pd.to_numeric(datos[columna], errors="coerce")
    mascara = serie.notna()
    if inferior is not None and superior is not None:
        mascara &= (serie < inferior) | (serie > superior)
        afectados = datos.loc[mascara].head(20)
        if not afectados.empty:
            with st.expander("Ver registros afectados"):
                st.dataframe(
                    afectados,
                    use_container_width=True,
                    hide_index=True,
                )

    if cantidad == 0:
        st.info("No hay outliers que eliminar en esta columna.")
        return

    decision = st.radio(
        "Decisión",
        ["Mantener", "Eliminar filas con outliers"],
        horizontal=True,
        key=f"outliers_accion_{columna}",
    )

    if decision == "Eliminar filas con outliers":
        st.warning(
            f"Se eliminarían aproximadamente {cantidad} filas. "
            "El impacto final puede ser menor si otras operaciones eliminan "
            "antes alguno de esos registros."
        )
        if st.button(
            "Añadir eliminación de outliers",
            key=f"outliers_add_{columna}",
        ):
            factor = (
                st.session_state.get("configuracion_auditoria", {})
                .get("factor_iqr", 1.5)
            )
            _reemplazar_operacion_familia_columna(
                plan,
                "outliers",
                "eliminar_filas",
                columna,
                {"factor_iqr": factor},
            )


def _mostrar_duplicados(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    st.subheader("Duplicados")
    st.caption(
        "Los duplicados completos pueden eliminarse conservando la primera "
        "aparición. Los duplicados por clave se muestran solo para revisión."
    )

    info = resultado.get("calidad", {}).get("duplicados", {})
    cantidad = int(info.get("filas_duplicadas", 0))
    porcentaje = float(info.get("porcentaje_duplicados", 0.0))

    c1, c2 = st.columns(2)
    c1.metric("Filas duplicadas completas", cantidad)
    c2.metric("Porcentaje", f"{porcentaje:.2f} %")

    if cantidad:
        afectados = datos.loc[
            datos.duplicated(keep=False)
        ].head(20)
        with st.expander("Ver registros duplicados"):
            st.dataframe(
                afectados,
                use_container_width=True,
                hide_index=True,
            )

        decision = st.radio(
            "Duplicados completos",
            ["Mantener", "Eliminar conservando la primera aparición"],
            horizontal=True,
            key="duplicados_completos_accion",
        )
        if (
            decision == "Eliminar conservando la primera aparición"
            and st.button(
                "Añadir eliminación de duplicados completos",
                key="duplicados_add",
            )
        ):
            existentes = [
                op.id
                for op in plan.operaciones
                if op.familia == "duplicados"
            ]
            for operacion_id in existentes:
                plan.eliminar_operacion(operacion_id)
            plan.crear_operacion(
                "duplicados",
                "eliminar_duplicados_completos",
                None,
                {"conservar": "primero"},
            )
            st.session_state["plan_limpieza"] = plan
            st.session_state.pop("simulacion_limpieza", None)
            st.session_state["mensaje_plan_limpieza"] = "Decisión actualizada en el plan."
            st.rerun()
    else:
        st.success("No se han detectado duplicados completos.")

    clave = resultado.get("calidad", {}).get("duplicados_clave", {})
    columnas_clave = clave.get("columnas_clave", [])
    if columnas_clave:
        st.divider()
        st.markdown("**Duplicados por clave configurada — solo revisión**")
        st.caption(
            "Clave: " + " + ".join(str(c) for c in columnas_clave)
        )
        registros = int(
            clave.get("registros_con_clave_duplicada", 0)
        )
        st.metric("Registros con clave duplicada", registros)

        if all(col in datos.columns for col in columnas_clave):
            validos = datos[columnas_clave].notna().all(axis=1)
            mascara = (
                validos
                & datos.loc[validos, columnas_clave]
                .duplicated(keep=False)
                .reindex(datos.index, fill_value=False)
            )
            vista = datos.loc[mascara].head(20)
            if not vista.empty:
                st.dataframe(
                    vista,
                    use_container_width=True,
                    hide_index=True,
                )
        st.info(
            "DataQualityPy no elimina automáticamente duplicados por clave."
        )

def _descripcion_operacion(operacion: Any) -> str:
    nombre = NOMBRES_OPERACIONES.get(
        operacion.tipo,
        operacion.tipo.replace("_", " ").capitalize(),
    )

    if operacion.tipo == "sustituir_caracteres":
        return (
            f"{nombre}: "
            f"{operacion.parametros.get('origen')!r} → "
            f"{operacion.parametros.get('destino')!r}"
        )

    if operacion.familia == "sustitucion":
        origen = _valor_visible(
            operacion.parametros.get("origen")
        )
        if operacion.tipo == "reemplazar_por_nulo":
            return f"{nombre}: {origen} → <NULO REAL>"
        destino = _valor_visible(
            operacion.parametros.get("destino")
        )
        return f"{nombre}: {origen} → {destino}"

    if operacion.familia == "nulos" and operacion.tipo == "reemplazar_valor":
        return f"{nombre}: {_valor_visible(operacion.parametros.get('valor'))}"

    if operacion.familia == "conversion":
        formato = operacion.parametros.get("formato")
        return f"{nombre}" + (f" · formato {formato}" if formato else "")

    if operacion.familia == "outliers":
        return (
            f"{nombre} · IQR × "
            f"{operacion.parametros.get('factor_iqr', 1.5)}"
        )

    return nombre


def _mostrar_plan(
    datos: pd.DataFrame,
    plan: CleaningPlan,
) -> None:
    st.subheader("Plan de limpieza")

    if plan.esta_vacio():
        st.info(
            "Todavía no has añadido ninguna operación al plan."
        )
        return

    operaciones = plan.operaciones_ordenadas()
    columnas_afectadas = {
        operacion.columna
        for operacion in operaciones
        if operacion.columna is not None
    }

    c1, c2, c3 = st.columns(3)
    c1.metric("Operaciones", len(operaciones))
    c2.metric("Columnas afectadas", len(columnas_afectadas))
    c3.metric("Dataset original", f"{len(datos)} filas")

    st.caption(
        "Las operaciones se muestran en el mismo orden lógico "
        "en el que las ejecutará el motor."
    )

    for numero, operacion in enumerate(operaciones, start=1):
        contenedor = st.container(border=True)
        with contenedor:
            izquierda, derecha = st.columns([6, 1])
            with izquierda:
                st.markdown(
                    f"**{numero}. {_descripcion_operacion(operacion)}**"
                )
                st.caption(
                    f"Familia: {operacion.familia} · "
                    f"Columna: {operacion.columna or 'Dataset completo'}"
                )
            with derecha:
                if st.button(
                    "Eliminar",
                    key=f"plan_del_{operacion.id}",
                    use_container_width=True,
                ):
                    plan.eliminar_operacion(operacion.id)
                    st.session_state["plan_limpieza"] = plan
                    st.session_state.pop("simulacion_limpieza", None)
                    st.session_state.pop("confirmar_aplicar_limpieza", None)
                    st.rerun()

    st.divider()
    st.markdown("**Simulación del plan**")
    st.caption(
        "La simulación se ejecuta sobre una copia temporal. "
        "No modifica el dataset auditado."
    )

    if st.button(
        "Simular plan",
        use_container_width=True,
        key="limpieza_simular",
    ):
        try:
            datos_simulados, ejecucion = ejecutar_plan_limpieza(
                datos,
                plan,
            )
        except (CleaningError, CleaningPlanError) as exc:
            st.session_state.pop("simulacion_limpieza", None)
            st.error(f"No se puede ejecutar el plan: {exc}")
        else:
            st.session_state["simulacion_limpieza"] = {
                "datos": datos_simulados,
                "resultado": ejecucion,
            }
            st.session_state["seccion_limpieza"] = (
                f"Plan de limpieza ({len(plan)})"
            )
            st.rerun()

    simulacion = st.session_state.get("simulacion_limpieza")
    if simulacion is not None:
        datos_simulados = simulacion["datos"]
        ejecucion = simulacion["resultado"]

        a, b, c = st.columns(3)
        a.metric("Filas antes", len(datos))
        b.metric("Filas previstas", len(datos_simulados))
        c.metric(
            "Filas eliminadas",
            len(datos) - len(datos_simulados),
        )

        st.success(
            f"Plan ejecutable: "
            f"{len(ejecucion.ejecuciones)} operaciones simuladas."
        )

        st.dataframe(
            datos_simulados.head(20),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "La simulación confirma que el plan puede ejecutarse sobre una "
            "copia. Para hacerlo definitivo, utiliza el bloque Aplicar limpieza."
        )



def _resumen_verificacion_limpieza(
    resultado_original: dict[str, Any],
    resultado_limpio: dict[str, Any],
    datos_originales: pd.DataFrame,
    datos_limpios: pd.DataFrame,
) -> pd.DataFrame:
    """Prepara una verificación compacta antes/después de la limpieza."""
    return pd.DataFrame(
        [
            {"Indicador": "Filas", "Antes": len(datos_originales), "Después": len(datos_limpios)},
            {"Indicador": "Columnas", "Antes": len(datos_originales.columns), "Después": len(datos_limpios.columns)},
            {"Indicador": "Incidencias", "Antes": len(resultado_original.get("incidencias", [])), "Después": len(resultado_limpio.get("incidencias", []))},
            {"Indicador": "Nulos reales", "Antes": resultado_original.get("calidad", {}).get("nulos", {}).get("total_nulos", 0), "Después": resultado_limpio.get("calidad", {}).get("nulos", {}).get("total_nulos", 0)},
            {"Indicador": "Duplicados completos", "Antes": resultado_original.get("calidad", {}).get("duplicados", {}).get("filas_duplicadas", 0), "Después": resultado_limpio.get("calidad", {}).get("duplicados", {}).get("filas_duplicadas", 0)},
        ]
    )


def _aplicar_plan_y_reauditar(
    datos: pd.DataFrame,
    resultado_original: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    """Aplica el plan sobre copia y reaudita automáticamente el resultado."""
    try:
        datos_limpios, resultado_limpieza = ejecutar_plan_limpieza(datos, plan)
    except CleaningError as exc:
        st.error(f"No se ha podido aplicar el plan: {exc}")
        return

    configuracion = st.session_state.get("configuracion_auditoria", {})
    nombre_archivo = st.session_state.get(
        "archivo_auditoria",
        resultado_original.get("dataset", {}).get("archivo", "dataset"),
    )

    try:
        resultado_auditoria_limpio = auditar_dataset(
            datos_limpios,
            nombre_archivo,
            configuracion,
        )
    except Exception as exc:
        st.error(
            "La limpieza se ejecutó sobre una copia, pero la reauditoría "
            f"automática no pudo completarse: {exc}"
        )
        return

    st.session_state["datos_limpios"] = datos_limpios
    st.session_state["resultado_limpieza"] = resultado_limpieza
    st.session_state["resultado_auditoria_limpio"] = resultado_auditoria_limpio
    st.session_state["plan_limpieza_aplicado"] = plan.a_dict()
    st.session_state["limpieza_aplicada"] = True
    st.success(
        "Limpieza aplicada sobre una copia y reauditoría completada. "
        "El dataset original permanece intacto."
    )


def _clave_incidencia(incidencia: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Identifica una incidencia por su naturaleza y columna."""
    return (
        incidencia.get("tipo"),
        incidencia.get("categoria"),
        incidencia.get("columna"),
    )


def _tabla_incidencias_verificacion(
    incidencias: list[dict[str, Any]],
) -> pd.DataFrame:
    """Convierte incidencias en una tabla breve para la verificación."""
    return pd.DataFrame(
        [
            {
                "Tipo": incidencia.get("tipo", "—"),
                "Categoría": incidencia.get("categoria", "—"),
                "Columna": incidencia.get("columna") or "General",
                "Severidad": incidencia.get("severidad", "—"),
            }
            for incidencia in incidencias
        ]
    )


def _mostrar_cambios_incidencias(
    resultado_original: dict[str, Any],
    resultado_limpio: dict[str, Any],
) -> None:
    """Muestra qué incidencias se resolvieron, permanecen o aparecieron."""
    originales = resultado_original.get("incidencias", [])
    limpias = resultado_limpio.get("incidencias", [])

    claves_originales = {_clave_incidencia(item) for item in originales}
    claves_limpias = {_clave_incidencia(item) for item in limpias}

    resueltas = [
        item for item in originales
        if _clave_incidencia(item) not in claves_limpias
    ]
    nuevas = [
        item for item in limpias
        if _clave_incidencia(item) not in claves_originales
    ]
    permanecen = [
        item for item in limpias
        if _clave_incidencia(item) in claves_originales
    ]

    st.markdown("**Resultado de la reauditoría**")

    c1, c2, c3 = st.columns(3)
    c1.metric("Incidencias resueltas", len(resueltas))
    c2.metric("Incidencias pendientes", len(permanecen))
    c3.metric("Incidencias nuevas", len(nuevas))

    if resueltas:
        with st.expander(f"Incidencias resueltas ({len(resueltas)})"):
            st.dataframe(
                _tabla_incidencias_verificacion(resueltas),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("La reauditoría no identifica incidencias resueltas.")

    if nuevas:
        with st.expander(f"Incidencias nuevas ({len(nuevas)})"):
            st.dataframe(
                _tabla_incidencias_verificacion(nuevas),
                use_container_width=True,
                hide_index=True,
            )

    with st.expander(f"Incidencias pendientes ({len(permanecen)})"):
        if permanecen:
            st.dataframe(
                _tabla_incidencias_verificacion(permanecen),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("No quedan incidencias pendientes.")


def _mostrar_resultado_limpieza(
    datos_originales: pd.DataFrame,
    resultado_original: dict[str, Any],
) -> None:
    """Muestra la verificación posterior a la aplicación del plan."""
    datos_limpios = st.session_state.get("datos_limpios")
    resultado_limpio = st.session_state.get("resultado_auditoria_limpio")
    resultado_limpieza = st.session_state.get("resultado_limpieza")

    if datos_limpios is None or resultado_limpio is None or resultado_limpieza is None:
        return

    st.divider()
    st.subheader("Verificación de la limpieza")
    st.caption(
        "Comparación de control entre la auditoría original y la "
        "reauditoría automática del dataset limpio."
    )
    st.dataframe(
        _resumen_verificacion_limpieza(
            resultado_original, resultado_limpio, datos_originales, datos_limpios
        ),
        use_container_width=True,
        hide_index=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Filas originales", len(datos_originales))
    c2.metric("Filas limpias", len(datos_limpios))
    c3.metric(
        "Operaciones ejecutadas",
        getattr(resultado_limpieza, "operaciones_ejecutadas", 0),
    )

    antes = len(resultado_original.get("incidencias", []))
    despues = len(resultado_limpio.get("incidencias", []))
    if despues < antes:
        st.success(f"Incidencias: {antes} → {despues}.")
    elif despues == antes:
        st.info(f"Incidencias: {antes} → {despues}.")
    else:
        st.warning(
            f"Incidencias: {antes} → {despues}. "
            "La limpieza ha generado nuevas incidencias que conviene revisar."
        )

    _mostrar_cambios_incidencias(resultado_original, resultado_limpio)

    with st.expander("Vista previa del dataset limpio"):
        st.dataframe(datos_limpios.head(20), use_container_width=True, hide_index=True)

    _mostrar_exportacion_limpieza(
        datos_originales,
        resultado_original,
        datos_limpios,
        resultado_limpio,
        resultado_limpieza,
    )



def _preparar_archivos_exportacion(
    datos_originales: pd.DataFrame,
    resultado_original: dict[str, Any],
    datos_limpios: pd.DataFrame,
    resultado_limpio: dict[str, Any],
    resultado_limpieza: Any,
) -> dict[str, Any]:
    """Genera en memoria el dataset limpio y los informes V5.5."""
    nombre_archivo = st.session_state.get(
        "archivo_auditoria",
        resultado_original.get("dataset", {}).get("archivo", "dataset.csv"),
    )
    bytes_original = st.session_state.get("archivo_original_bytes")

    if not isinstance(bytes_original, (bytes, bytearray)):
        raise ErrorExportacionLimpieza(
            "No se conserva una copia del archivo original en esta sesión. "
            "Vuelve a auditar el archivo para habilitar la exportación V5.5."
        )

    hoja = st.session_state.get("hoja_auditoria")
    configuracion = st.session_state.get("configuracion_auditoria", {})
    plan_aplicado = st.session_state.get("plan_limpieza_aplicado", {})

    trazabilidad = construir_trazabilidad_limpieza(
        nombre_archivo=nombre_archivo,
        hoja=hoja,
        filas_originales=len(datos_originales),
        columnas_originales=len(datos_originales.columns),
        filas_limpias=len(datos_limpios),
        columnas_limpias=len(datos_limpios.columns),
        plan_solicitado=plan_aplicado,
        resultado_limpieza=resultado_limpieza,
        resultado_auditoria_antes=resultado_original,
        resultado_auditoria_despues=resultado_limpio,
        configuracion_auditoria=configuracion,
    )

    with tempfile.TemporaryDirectory() as directorio:
        temporal = Path(directorio)
        ruta_original = temporal / Path(nombre_archivo).name
        ruta_original.write_bytes(bytes(bytes_original))

        resultado_exportacion = exportar_dataset_limpio(
            datos_limpios,
            ruta_original,
            hoja=hoja,
        )
        datos_exportados = resultado_exportacion.ruta.read_bytes()

    nombre_json, nombre_html = generar_nombres_informes(nombre_archivo)
    json_informe = generar_json_limpieza(trazabilidad).encode("utf-8")
    html_informe = generar_html_limpieza(trazabilidad).encode("utf-8")

    return {
        "dataset": datos_exportados,
        "nombre_dataset": resultado_exportacion.nombre_archivo,
        "mime_dataset": (
            "text/csv"
            if resultado_exportacion.formato == "csv"
            else (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        ),
        "json": json_informe,
        "nombre_json": nombre_json,
        "html": html_informe,
        "nombre_html": nombre_html,
    }


def _mostrar_exportacion_limpieza(
    datos_originales: pd.DataFrame,
    resultado_original: dict[str, Any],
    datos_limpios: pd.DataFrame,
    resultado_limpio: dict[str, Any],
    resultado_limpieza: Any,
) -> None:
    """Muestra las descargas del dataset limpio y su trazabilidad."""
    st.divider()
    st.subheader("Exportar resultados")
    st.caption(
        "Descarga el dataset limpio y los informes de trazabilidad. "
        "El archivo original permanece intacto."
    )

    try:
        archivos = _preparar_archivos_exportacion(
            datos_originales,
            resultado_original,
            datos_limpios,
            resultado_limpio,
            resultado_limpieza,
        )
    except Exception as exc:
        st.warning(str(exc))
        return

    c1, c2, c3 = st.columns(3)

    c1.download_button(
        "Descargar dataset limpio",
        data=archivos["dataset"],
        file_name=archivos["nombre_dataset"],
        mime=archivos["mime_dataset"],
        use_container_width=True,
        key="descargar_dataset_limpio",
    )
    c2.download_button(
        "Descargar informe HTML",
        data=archivos["html"],
        file_name=archivos["nombre_html"],
        mime="text/html",
        use_container_width=True,
        key="descargar_informe_limpieza_html",
    )
    c3.download_button(
        "Descargar informe JSON",
        data=archivos["json"],
        file_name=archivos["nombre_json"],
        mime="application/json",
        use_container_width=True,
        key="descargar_informe_limpieza_json",
    )

    st.success(
        "Exportación preparada: dataset limpio, informe HTML e informe JSON."
    )

def _mostrar_aplicacion_final(
    datos: pd.DataFrame,
    resultado: dict[str, Any],
    plan: CleaningPlan,
) -> None:
    """Muestra confirmación, aplicación y reauditoría de cierre de V5.4."""
    st.divider()
    st.subheader("Aplicar limpieza")

    if plan.esta_vacio():
        st.info("Añade al menos una operación antes de aplicar la limpieza.")
        return

    simulacion = st.session_state.get("simulacion_limpieza")
    if simulacion is None:
        st.info(
            "Simula el plan completo antes de aplicar la limpieza. "
            "La aplicación definitiva permanecerá bloqueada hasta entonces."
        )
        return

    if "datos" not in simulacion or "resultado" not in simulacion:
        st.error(
            "La simulación guardada no es válida. Vuelve a simular el plan "
            "antes de aplicar la limpieza."
        )
        return

    st.success("La simulación es válida. El plan puede aplicarse sobre una copia.")
    st.caption("El archivo y el DataFrame originales no se sobrescriben ni se modifican.")

    confirmar = st.checkbox(
        "Confirmo que quiero aplicar este plan de limpieza sobre una copia",
        key="confirmar_aplicar_limpieza",
    )
    if st.button(
        "Aplicar limpieza y reauditar",
        type="primary",
        disabled=not confirmar,
        key="aplicar_limpieza_final",
    ):
        _aplicar_plan_y_reauditar(datos, resultado, plan)

    _mostrar_resultado_limpieza(datos, resultado)

def mostrar_preparar_limpieza() -> None:
    """Muestra la pantalla de preparación del plan de limpieza."""
    datos = st.session_state.get("datos_auditoria")
    resultado = st.session_state.get("resultado_auditoria")

    if not isinstance(datos, pd.DataFrame) or resultado is None:
        st.error(
            "No hay una auditoría disponible para preparar la limpieza."
        )
        if st.button("Volver a auditoría"):
            st.session_state["vista"] = "auditar"
            st.rerun()
        return

    plan = _obtener_plan()

    _mostrar_cabecera(datos, resultado)

    mensaje_plan = st.session_state.pop("mensaje_plan_limpieza", None)
    if mensaje_plan:
        st.success(mensaje_plan)

    if st.button("← Volver a resultados", key="limpieza_volver"):
        st.session_state["vista"] = "resultados"
        st.rerun()

    st.divider()

    etiqueta_plan = f"Plan de limpieza ({len(plan)})"
    secciones = [
        "Texto",
        "Sustituciones",
        "Nulos",
        "Conversiones",
        "Outliers",
        "Duplicados",
        etiqueta_plan,
    ]

    seccion_guardada = st.session_state.get("seccion_limpieza", "Texto")
    if seccion_guardada.startswith("Plan de limpieza"):
        seccion_guardada = etiqueta_plan
    if seccion_guardada not in secciones:
        seccion_guardada = "Texto"

    seccion = st.radio(
        "Sección de limpieza",
        secciones,
        index=secciones.index(seccion_guardada),
        horizontal=True,
        key="navegacion_limpieza",
        label_visibility="collapsed",
    )
    st.session_state["seccion_limpieza"] = seccion

    if seccion == "Texto":
        _mostrar_texto(datos, resultado, plan)
    elif seccion == "Sustituciones":
        _mostrar_sustituciones(datos, resultado, plan)
    elif seccion == "Nulos":
        _mostrar_nulos(datos, resultado, plan)
    elif seccion == "Conversiones":
        _mostrar_conversiones(datos, resultado, plan)
    elif seccion == "Outliers":
        _mostrar_outliers(datos, resultado, plan)
    elif seccion == "Duplicados":
        _mostrar_duplicados(datos, resultado, plan)
    else:
        _mostrar_plan(datos, plan)
        _mostrar_aplicacion_final(datos, resultado, plan)
