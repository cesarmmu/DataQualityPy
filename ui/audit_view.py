"""Pantalla de auditoría de DataQualityPy V6."""

from pathlib import Path
import tempfile

import streamlit as st

from src.audit import auditar_dataset
from src.config import cargar_configuracion
from src.loader import ErrorCargaArchivo, cargar_archivo, obtener_hojas_excel


EXTENSIONES_ADMITIDAS = ["csv", "xlsx"]


def _guardar_archivo_temporal(archivo_subido) -> Path:
    """Guarda temporalmente el archivo recibido desde Streamlit."""

    extension = Path(archivo_subido.name).suffix

    temporal = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=extension,
    )

    try:
        temporal.write(archivo_subido.getbuffer())
    finally:
        temporal.close()

    return Path(temporal.name)


def _eliminar_archivo_temporal(ruta: Path) -> None:
    """Elimina el archivo temporal si todavía existe."""

    try:
        ruta.unlink(missing_ok=True)
    except OSError:
        pass


def _obtener_hojas_archivo(archivo_subido) -> list[str]:
    """Obtiene las hojas disponibles de un XLSX subido a Streamlit."""

    ruta_temporal = _guardar_archivo_temporal(archivo_subido)

    try:
        return obtener_hojas_excel(ruta_temporal)

    finally:
        _eliminar_archivo_temporal(ruta_temporal)


def _cargar_datos(
    archivo_subido,
    hoja: str | None = None,
):
    """Carga temporalmente el dataset seleccionado."""

    ruta_temporal = _guardar_archivo_temporal(archivo_subido)

    try:
        return cargar_archivo(
            ruta_temporal,
            hoja=hoja,
        )

    finally:
        _eliminar_archivo_temporal(ruta_temporal)


def _ejecutar_auditoria(
    archivo_subido,
    hoja: str | None = None,
    configuracion_usuario: dict | None = None,
) -> tuple:
    """Adapta el archivo de Streamlit y ejecuta el motor de auditoría."""

    datos = _cargar_datos(
        archivo_subido,
        hoja=hoja,
    )
    configuracion = cargar_configuracion(
        configuracion_usuario=configuracion_usuario,
    )

    resultado = auditar_dataset(
        datos,
        archivo_subido.name,
        configuracion,
    )

    return datos, resultado


def mostrar_auditoria() -> None:
    """Muestra la pantalla para seleccionar y analizar un dataset."""

    st.title("DataQualityPy")
    st.caption("Auditor de calidad de datos")

    if st.button("← Menú principal"):
        st.session_state["vista"] = "inicio"
        st.rerun()

    st.markdown("## Auditar dataset")
    st.write("Selecciona el dataset que quieres analizar.")

    archivo_subido = st.file_uploader(
        "Arrastra y suelta aquí tu archivo o selecciónalo desde tu equipo.",
        type=EXTENSIONES_ADMITIDAS,
        accept_multiple_files=False,
    )

    st.caption("Formatos admitidos: CSV y XLSX.")

    if archivo_subido is None:
        return

    st.success("Archivo cargado correctamente.")
    st.write(f"📄 **{archivo_subido.name}**")

    hoja_seleccionada = None
    extension = Path(archivo_subido.name).suffix.lower()

    if extension == ".xlsx":
        try:
            hojas_disponibles = _obtener_hojas_archivo(archivo_subido)

        except ErrorCargaArchivo as error:
            st.error(str(error))
            return

        if len(hojas_disponibles) == 1:
            hoja_seleccionada = hojas_disponibles[0]
            st.write(f"📑 **Hoja:** {hoja_seleccionada}")

        else:
            hoja_seleccionada = st.selectbox(
                "Hoja a auditar",
                options=hojas_disponibles,
            )

    try:
        datos_configuracion = _cargar_datos(
            archivo_subido,
            hoja=hoja_seleccionada,
        )

    except ErrorCargaArchivo as error:
        st.error(str(error))
        return

    st.markdown("### Configuración de auditoría")
    st.caption(
        "Opcional. Si no seleccionas ninguna opción, "
        "se utilizará la configuración estándar."
    )

    columnas_clave = st.multiselect(
        "Columnas clave",
        options=list(datos_configuracion.columns),
        help=(
            "Selecciona una o varias columnas que identifican "
            "un registro de forma única."
        ),
    )

    st.markdown("#### Tipos semánticos declarados")
    st.caption(
        "Opcional. Declara únicamente las columnas cuyo tipo semántico "
        "quieras fijar manualmente. El resto seguirá utilizando "
        "la inferencia automática."
    )

    etiquetas_tipos = {
        "Numérico": "numerico",
        "Fecha": "fecha",
        "Fecha y hora": "fecha_hora",
        "Booleano/binario": "booleano_binario",
        "Categórico": "categorico",
        "Identificador": "identificador",
        "Texto libre": "texto_libre",
    }

    columnas_tipo_declarado = st.multiselect(
        "Columnas con tipo semántico declarado",
        options=list(datos_configuracion.columns),
        help=(
            "Selecciona solo las columnas cuyo tipo semántico "
            "quieras establecer manualmente."
        ),
    )

    tipos_columnas = {}

    for columna in columnas_tipo_declarado:
        etiqueta_tipo = st.selectbox(
            f"Tipo semántico de {columna}",
            options=list(etiquetas_tipos.keys()),
            key=f"tipo_semantico_{columna}",
        )
        tipos_columnas[columna] = etiquetas_tipos[etiqueta_tipo]

    st.markdown("#### Reglas de negocio")
    st.caption(
        "Opcional. Define únicamente las reglas que quieras comprobar "
        "de forma explícita en determinadas columnas."
    )

    columnas_reglas = st.multiselect(
        "Columnas con reglas de negocio",
        options=list(datos_configuracion.columns),
        help=(
            "Selecciona las columnas para las que quieras definir "
            "un mínimo, un máximo o valores permitidos."
        ),
    )

    reglas_columnas = {}

    for columna in columnas_reglas:
        st.markdown(f"**{columna}**")

        usar_minimo = st.checkbox(
            "Definir mínimo",
            key=f"usar_minimo_{columna}",
        )
        usar_maximo = st.checkbox(
            "Definir máximo",
            key=f"usar_maximo_{columna}",
        )
        usar_valores = st.checkbox(
            "Definir valores permitidos",
            key=f"usar_valores_permitidos_{columna}",
        )

        reglas = {}

        if usar_minimo:
            minimo = st.number_input(
                f"Mínimo de {columna}",
                value=0.0,
                key=f"minimo_{columna}",
            )
            reglas["min"] = minimo

        if usar_maximo:
            maximo = st.number_input(
                f"Máximo de {columna}",
                value=0.0,
                key=f"maximo_{columna}",
            )
            reglas["max"] = maximo

        if usar_valores:
            valores_existentes = [
                valor
                for valor in datos_configuracion[columna].dropna().unique().tolist()
            ]

            valores_permitidos = st.multiselect(
                f"Valores permitidos de {columna}",
                options=valores_existentes,
                key=f"valores_permitidos_{columna}",
                help=(
                    "Selecciona uno o varios valores existentes "
                    "que se considerarán válidos para esta columna."
                ),
            )

            if valores_permitidos:
                reglas["valores_permitidos"] = valores_permitidos

        if reglas:
            reglas_columnas[columna] = reglas

    configuracion_usuario = {
        "columnas_clave": columnas_clave,
        "tipos_columnas": tipos_columnas,
        "reglas_columnas": reglas_columnas,
    }

    if st.button(
        "Analizar dataset",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Analizando dataset..."):
                datos, resultado = _ejecutar_auditoria(
                    archivo_subido,
                    hoja=hoja_seleccionada,
                    configuracion_usuario=configuracion_usuario,
                )

        except ErrorCargaArchivo as error:
            st.error(str(error))
            return

        except Exception as error:
            st.error(
                "No se ha podido completar la auditoría del dataset."
            )
            st.caption(str(error))
            return

        configuracion_efectiva = cargar_configuracion(
            configuracion_usuario=configuracion_usuario,
        )

        st.session_state["datos_auditoria"] = datos
        st.session_state["resultado_auditoria"] = resultado
        st.session_state["archivo_auditoria"] = archivo_subido.name
        st.session_state["archivo_original_bytes"] = bytes(
            archivo_subido.getbuffer()
        )
        st.session_state["hoja_auditoria"] = hoja_seleccionada
        st.session_state["configuracion_auditoria"] = configuracion_efectiva
        st.session_state["vista"] = "resultados"

        st.rerun()
