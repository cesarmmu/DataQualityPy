"""Generación del informe de auditoría en formato HTML."""

from html import escape
from pathlib import Path

import pandas as pd

from src.quality import es_nulo_textual
from src.html_report_v7 import generar_bloques_v7_html


MAX_FILAS_MAPA = 200

ESTADO_VALIDO = 0
ESTADO_NULO_REAL = 1
ESTADO_NULO_TEXTUAL = 2


def _formatear_entero(valor: int) -> str:
    """Formatea un entero con separador de miles español."""
    return f"{int(valor):,}".replace(",", ".")


def _formatear_porcentaje(valor: float) -> str:
    """Formatea un porcentaje con dos decimales."""
    return f"{float(valor):.2f}".replace(".", ",") + " %"


def _formatear_numero(valor: float) -> str:
    """Formatea un número con dos decimales."""
    return f"{float(valor):.2f}".replace(".", ",")


def _formatear_memoria(bytes_memoria: int) -> str:
    """Convierte bytes a una unidad de memoria legible."""
    if bytes_memoria < 1024:
        return f"{bytes_memoria} bytes"

    if bytes_memoria < 1024**2:
        valor = bytes_memoria / 1024
        unidad = "KB"
    elif bytes_memoria < 1024**3:
        valor = bytes_memoria / 1024**2
        unidad = "MB"
    else:
        valor = bytes_memoria / 1024**3
        unidad = "GB"

    return f"{valor:.2f} {unidad}".replace(".", ",")


def _seleccionar_filas_mapa(
    datos: pd.DataFrame,
    max_filas: int = MAX_FILAS_MAPA,
) -> pd.DataFrame:
    """Selecciona filas distribuidas para representar el dataset."""
    total_filas = len(datos)

    if total_filas <= max_filas:
        return datos.copy()

    posiciones = [
        round(
            indice * (total_filas - 1) / (max_filas - 1)
        )
        for indice in range(max_filas)
    ]

    return datos.iloc[posiciones].copy()


def preparar_mapa_nulos(
    datos: pd.DataFrame,
    max_filas: int = MAX_FILAS_MAPA,
) -> dict:
    """Prepara la matriz de estados para el mapa de valores ausentes."""
    datos_muestra = _seleccionar_filas_mapa(
        datos,
        max_filas=max_filas,
    )

    mapa = pd.DataFrame(
        ESTADO_VALIDO,
        index=datos_muestra.index,
        columns=datos_muestra.columns,
        dtype="int8",
    )

    mapa = mapa.mask(
        datos_muestra.isna(),
        ESTADO_NULO_REAL,
    )

    columnas_texto = datos_muestra.select_dtypes(
        include=["object", "string"]
    )

    for columna in columnas_texto.columns:
        mascara_nulos_textuales = (
            columnas_texto[columna]
            .map(es_nulo_textual)
            .fillna(False)
        )

        mapa.loc[
            mascara_nulos_textuales,
            columna,
        ] = ESTADO_NULO_TEXTUAL

    return {
        "mapa": mapa,
        "filas_totales": len(datos),
        "filas_mostradas": len(datos_muestra),
        "muestra": len(datos) > len(datos_muestra),
    }


def _estilo_celda_mapa(valor: int) -> str:
    """Devuelve el estilo visual correspondiente a una celda."""
    estilos = {
        ESTADO_VALIDO: (
            "background-color: #dff2e1; "
            "color: transparent;"
        ),
        ESTADO_NULO_REAL: (
            "background-color: #f6d6d6; "
            "color: transparent;"
        ),
        ESTADO_NULO_TEXTUAL: (
            "background-color: #f9e8b4; "
            "color: transparent;"
        ),
    }

    return estilos.get(valor, "")


def generar_mapa_nulos_html(
    datos: pd.DataFrame,
) -> str:
    """Genera el mapa visual de valores ausentes sin depender de Jinja2."""
    resultado_mapa = preparar_mapa_nulos(datos)
    mapa = resultado_mapa["mapa"].reset_index(drop=True)

    cabeceras = "".join(
        f"<th>{escape(str(columna))}</th>"
        for columna in mapa.columns
    )

    filas_html = []

    for _, fila in mapa.iterrows():
        celdas = []

        for valor in fila:
            estilo = _estilo_celda_mapa(int(valor))
            celdas.append(
                f'<td style="{estilo}">&nbsp;</td>'
            )

        filas_html.append(
            "<tr>" + "".join(celdas) + "</tr>"
        )

    tabla_html = f"""
    <table class="mapa-nulos">
        <thead>
            <tr>
                {cabeceras}
            </tr>
        </thead>
        <tbody>
            {''.join(filas_html)}
        </tbody>
    </table>
    """

    filas_mostradas = _formatear_entero(
        resultado_mapa["filas_mostradas"]
    )
    filas_totales = _formatear_entero(
        resultado_mapa["filas_totales"]
    )

    if resultado_mapa["muestra"]:
        texto_muestra = (
            f"Se muestran {filas_mostradas} registros "
            "distribuidos de un total de "
            f"{filas_totales}."
        )
    else:
        texto_muestra = (
            f"Se muestran los {filas_mostradas} "
            "registros del dataset."
        )

    return f"""
    <div class="bloque-mapa">
        <p class="descripcion">{texto_muestra}</p>

        <div class="leyenda-mapa">
            <span class="leyenda-item">
                <span class="leyenda-color valido"></span>
                Dato válido
            </span>
            <span class="leyenda-item">
                <span class="leyenda-color nulo-real"></span>
                Nulo real
            </span>
            <span class="leyenda-item">
                <span class="leyenda-color nulo-textual"></span>
                Posible nulo textual
            </span>
        </div>

        <div class="contenedor-mapa">
            {tabla_html}
        </div>
    </div>
    """


def _generar_tarjeta(
    valor: int,
    etiqueta: str,
    clase: str = "",
) -> str:
    """Genera una tarjeta del resumen ejecutivo."""
    clase_html = f" tarjeta-{clase}" if clase else ""

    return f"""
    <div class="tarjeta{clase_html}">
        <div class="tarjeta-valor">
            {_formatear_entero(valor)}
        </div>
        <div class="tarjeta-etiqueta">
            {escape(etiqueta)}
        </div>
    </div>
    """


def _etiqueta_tipo_semantico(tipo: str) -> str:
    """Devuelve una etiqueta legible para un tipo semántico."""
    etiquetas = {
        "numerico": "Numérico",
        "fecha": "Fecha",
        "fecha_hora": "Fecha y hora",
        "booleano_binario": "Booleano/binario",
        "categorico": "Categórico",
        "identificador": "Identificador",
        "texto_libre": "Texto libre",
    }
    return etiquetas.get(tipo, str(tipo))


def _etiqueta_confianza(confianza: str) -> str:
    """Devuelve una etiqueta legible para el nivel de confianza."""
    etiquetas = {
        "alta": "Alta",
        "media": "Media",
        "baja": "Baja",
    }
    return etiquetas.get(confianza, str(confianza).capitalize())


def _etiqueta_origen(origen: str) -> str:
    """Devuelve una etiqueta legible para el origen del tipo semántico."""
    etiquetas = {
        "inferred": "Inferido",
        "declared": "Declarado",
    }
    return etiquetas.get(origen, str(origen))


def _etiqueta_control(control: str) -> str:
    """Convierte el identificador interno de un control en texto legible."""
    etiquetas = {
        "completitud": "Completitud",
        "unicidad_general": "Unicidad general",
        "unicidad_clave": "Unicidad por clave",
        "consistencia_texto": "Consistencia de texto",
        "outliers": "Valores atípicos",
        "compatibilidad_semantica": "Compatibilidad semántica",
        "reglas_negocio": "Reglas de negocio",
    }
    return etiquetas.get(control, str(control).replace("_", " ").capitalize())


def _generar_lista_controles(controles: list[str]) -> str:
    """Genera una lista HTML para un estado de cobertura."""
    if not controles:
        return "<p>Ninguno.</p>"

    elementos = "".join(
        f"<li>{escape(_etiqueta_control(control))}</li>"
        for control in controles
    )
    return f"<ul>{elementos}</ul>"


def _generar_resumen_html(
    dataset: dict,
    resumen: dict,
) -> str:
    """Genera la sección de resumen ejecutivo V3."""
    por_severidad = resumen["por_severidad"]

    tarjetas = "".join(
        [
            _generar_tarjeta(
                resumen["total_incidencias"],
                "Incidencias",
            ),
            _generar_tarjeta(
                por_severidad["alta"],
                "Altas",
                "alta",
            ),
            _generar_tarjeta(
                por_severidad["media"],
                "Medias",
                "media",
            ),
            _generar_tarjeta(
                por_severidad["baja"],
                "Bajas",
                "baja",
            ),
        ]
    )

    principales = resumen["principales_incidencias"]

    if principales:
        elementos = "".join(
            (
                '<li class="incidencia-resumen '
                f"severidad-{escape(incidencia['severidad'])}\">"
                f"<strong>"
                f"{escape(incidencia['severidad'].upper())}"
                f"</strong> "
                f"{escape(incidencia['mensaje'])}"
                "</li>"
            )
            for incidencia in principales
        )

        bloque_principales = f"""
        <h3>Principales incidencias</h3>
        <ul class="lista-incidencias">
            {elementos}
        </ul>
        """
    else:
        bloque_principales = """
        <p class="sin-incidencias">
            No se han detectado incidencias de calidad.
        </p>
        """

    tipos = resumen["tipos_semanticos"]
    tarjetas_tipos = "".join(
        _generar_tarjeta(
            tipos[tipo],
            _etiqueta_tipo_semantico(tipo),
        )
        for tipo in (
            "numerico",
            "fecha",
            "fecha_hora",
            "booleano_binario",
            "categorico",
            "identificador",
            "texto_libre",
        )
    )

    cobertura = resumen["cobertura_auditoria"]
    cobertura_html = f"""
    <h3>Cobertura de auditoría</h3>
    <div class="tres-columnas">
        <div class="panel">
            <h4>Controles aplicados</h4>
            {_generar_lista_controles(cobertura['controles_aplicados'])}
        </div>
        <div class="panel">
            <h4>Controles no aplicables</h4>
            {_generar_lista_controles(cobertura['controles_no_aplicables'])}
        </div>
        <div class="panel">
            <h4>Controles no configurados</h4>
            {_generar_lista_controles(cobertura['controles_no_configurados'])}
        </div>
    </div>
    """

    return f"""
    <section>
        <h2>Resumen ejecutivo</h2>

        <p class="resumen-dataset">
            Dataset:
            <strong>{_formatear_entero(dataset['filas'])}</strong>
            filas ·
            <strong>{_formatear_entero(dataset['columnas'])}</strong>
            columnas
        </p>

        <div class="tarjetas">
            {tarjetas}
        </div>

        {bloque_principales}

        <h3>Tipos semánticos</h3>
        <div class="tarjetas">
            {tarjetas_tipos}
        </div>

        {cobertura_html}
    </section>
    """


def _generar_perfil_html(
    dataset: dict,
    perfil: dict,
    tipos_semanticos: dict,
) -> str:
    """Genera el perfil estructural y semántico del dataset."""
    filas_tabla = []

    for columna in perfil["nombres_columnas"]:
        inferencia = tipos_semanticos[columna]
        filas_tabla.append(
            "<tr>"
            f"<td>{escape(str(columna))}</td>"
            f"<td>{escape(str(perfil['tipos_datos'][columna]))}</td>"
            f"<td>{escape(_etiqueta_tipo_semantico(inferencia['tipo']))}</td>"
            f"<td>{escape(_etiqueta_confianza(inferencia['confianza']))}</td>"
            f"<td>{escape(_etiqueta_origen(inferencia['fuente']))}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(perfil['valores_distintos'][columna])}"
            "</td>"
            "</tr>"
        )

    return f"""
    <section>
        <h2>Perfil del dataset</h2>

        <div class="datos-generales">
            <div>
                <span>Archivo</span>
                <strong>{escape(str(dataset['archivo']))}</strong>
            </div>
            <div>
                <span>Filas</span>
                <strong>{_formatear_entero(dataset['filas'])}</strong>
            </div>
            <div>
                <span>Columnas</span>
                <strong>{_formatear_entero(dataset['columnas'])}</strong>
            </div>
            <div>
                <span>Memoria utilizada</span>
                <strong>
                    {_formatear_memoria(dataset['memoria_bytes'])}
                </strong>
            </div>
        </div>

        <h3>Columnas</h3>

        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Dtype físico</th>
                        <th>Tipo semántico</th>
                        <th>Confianza</th>
                        <th>Origen</th>
                        <th>Valores distintos</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(filas_tabla)}
                </tbody>
            </table>
        </div>
    </section>
    """


def _generar_completitud_html(calidad: dict) -> str:
    """Genera el bloque de completitud."""
    nulos = calidad["nulos"]
    nulos_textuales = calidad["nulos_textuales"]

    filas = []

    for columna, detalle in nulos["por_columna"].items():
        textual = nulos_textuales.get(columna, {})
        cantidad_textual = textual.get(
            "total_posibles_nulos_textuales",
            0,
        )
        porcentaje_textual = textual.get(
            "porcentaje_posibles_nulos_textuales",
            0.0,
        )

        if detalle["nulos"] == 0 and cantidad_textual == 0:
            continue

        filas.append(
            "<tr>"
            f"<td>{escape(str(columna))}</td>"
            f'<td class="numero">{_formatear_entero(detalle["nulos"])}</td>'
            f'<td class="numero">'
            f'{_formatear_porcentaje(detalle["porcentaje_nulos"])}</td>'
            f'<td class="numero">{_formatear_entero(cantidad_textual)}</td>'
            f'<td class="numero">'
            f"{_formatear_porcentaje(porcentaje_textual)}</td>"
            "</tr>"
        )

    if filas:
        detalle_html = f"""
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Nulos reales</th>
                        <th>% nulos reales</th>
                        <th>Posibles nulos textuales</th>
                        <th>% nulos textuales</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(filas)}
                </tbody>
            </table>
        </div>
        """
    else:
        detalle_html = """
        <p class="sin-incidencias">
            No se han detectado valores ausentes.
        </p>
        """

    return f"""
    <div class="subseccion">
        <h3>Completitud</h3>
        <p>
            Valores nulos reales:
            <strong>{_formatear_entero(nulos['total_nulos'])}</strong>.
            Columnas afectadas:
            <strong>
                {_formatear_entero(nulos['columnas_con_nulos'])}
            </strong>.
        </p>
        {detalle_html}
    </div>
    """


def _generar_unicidad_html(calidad: dict) -> str:
    """Genera el bloque de unicidad."""
    duplicados = calidad["duplicados"]
    clave = calidad["duplicados_clave"]

    if not clave["clave_configurada"]:
        clave_html = """
        <p class="descripcion">
            No se ha configurado ninguna clave para analizar
            duplicados por columnas seleccionadas.
        </p>
        """
    elif clave["columnas_inexistentes"]:
        inexistentes = ", ".join(
            escape(str(columna))
            for columna in clave["columnas_inexistentes"]
        )
        clave_html = f"""
        <p>
            Clave configurada:
            <strong>
                {escape(', '.join(clave['columnas_clave']))}
            </strong>.
        </p>
        <p>
            Columnas inexistentes:
            <strong>{inexistentes}</strong>.
        </p>
        """
    else:
        clave_html = f"""
        <p>
            Clave configurada:
            <strong>
                {escape(', '.join(clave['columnas_clave']))}
            </strong>.
        </p>
        <div class="datos-generales">
            <div>
                <span>Registros válidos</span>
                <strong>
                    {_formatear_entero(clave['registros_validos'])}
                </strong>
            </div>
            <div>
                <span>Registros excluidos</span>
                <strong>
                    {_formatear_entero(clave['registros_excluidos'])}
                </strong>
            </div>
            <div>
                <span>Registros con clave duplicada</span>
                <strong>
                    {_formatear_entero(
                        clave['registros_con_clave_duplicada']
                    )}
                </strong>
            </div>
            <div>
                <span>Claves duplicadas distintas</span>
                <strong>
                    {_formatear_entero(
                        clave['valores_clave_duplicados']
                    )}
                </strong>
            </div>
        </div>
        """

    return f"""
    <div class="subseccion">
        <h3>Unicidad</h3>

        <div class="datos-generales">
            <div>
                <span>Filas duplicadas completas</span>
                <strong>
                    {_formatear_entero(
                        duplicados['filas_duplicadas']
                    )}
                </strong>
            </div>
            <div>
                <span>Porcentaje de duplicados</span>
                <strong>
                    {_formatear_porcentaje(
                        duplicados['porcentaje_duplicados']
                    )}
                </strong>
            </div>
        </div>

        {clave_html}
    </div>
    """


def _generar_estructura_html(calidad: dict) -> str:
    """Genera el bloque de estructura."""
    problematicas = calidad["columnas_problematicas"]
    identificadores = calidad["identificadores"]

    posibles = [
        (columna, detalle)
        for columna, detalle in identificadores.items()
        if detalle["posible_identificador"]
    ]

    def lista_columnas(columnas: list) -> str:
        if not columnas:
            return "<span>Ninguna</span>"

        return "<ul>" + "".join(
            f"<li>{escape(str(columna))}</li>"
            for columna in columnas
        ) + "</ul>"

    if posibles:
        filas = "".join(
            "<tr>"
            f"<td>{escape(str(columna))}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['valores_no_nulos'])}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['valores_distintos'])}</td>"
            f'<td class="numero">'
            f"{_formatear_porcentaje(detalle['porcentaje_unicidad'])}</td>"
            "</tr>"
            for columna, detalle in posibles
        )

        identificadores_html = f"""
        <h4>Posibles identificadores</h4>
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Valores evaluados</th>
                        <th>Valores distintos</th>
                        <th>Unicidad</th>
                    </tr>
                </thead>
                <tbody>{filas}</tbody>
            </table>
        </div>
        """
    else:
        identificadores_html = """
        <h4>Posibles identificadores</h4>
        <p>No se han detectado posibles identificadores.</p>
        """

    return f"""
    <div class="subseccion">
        <h3>Estructura</h3>

        <div class="dos-columnas">
            <div class="panel">
                <h4>Columnas completamente vacías</h4>
                {lista_columnas(problematicas['columnas_vacias'])}
            </div>
            <div class="panel">
                <h4>Columnas constantes</h4>
                {lista_columnas(problematicas['columnas_constantes'])}
            </div>
        </div>

        {identificadores_html}
    </div>
    """


def _generar_consistencia_html(calidad: dict) -> str:
    """Genera el bloque de consistencia textual y categórica."""
    texto = calidad["texto"]

    if not texto:
        return """
        <div class="subseccion">
            <h3>Consistencia</h3>
            <p>No hay columnas de texto para analizar.</p>
        </div>
        """

    filas = []

    for columna, detalle in texto.items():
        grupos = detalle["grupos_inconsistentes"]

        if grupos:
            grupos_texto = []

            for grupo in grupos:
                variantes = ", ".join(
                    f"{escape(str(valor))} "
                    f"({_formatear_entero(cantidad)})"
                    for valor, cantidad
                    in grupo["variantes"].items()
                )
                grupos_texto.append(variantes)

            inconsistencias = "<br>".join(grupos_texto)
        else:
            inconsistencias = "—"

        filas.append(
            "<tr>"
            f"<td>{escape(str(columna))}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['valores_con_espacios'])}</td>"
            f"<td>{'Sí' if detalle['baja_cardinalidad'] else 'No'}</td>"
            f"<td>{inconsistencias}</td>"
            "</tr>"
        )

    return f"""
    <div class="subseccion">
        <h3>Consistencia</h3>
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Valores con espacios exteriores</th>
                        <th>Baja cardinalidad</th>
                        <th>Posibles inconsistencias categóricas</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(filas)}
                </tbody>
            </table>
        </div>
    </div>
    """


def _generar_validez_temporal_html(calidad: dict) -> str:
    """Genera el bloque de validez temporal."""
    fechas = calidad["fechas"]

    if not fechas:
        return """
        <div class="subseccion">
            <h4>Validez temporal</h4>
            <p>No se han detectado columnas de fecha.</p>
        </div>
        """

    filas = []

    for columna, detalle in fechas.items():
        tipo = (
            "Fecha y hora"
            if detalle["tipo_temporal"] == "fecha_hora"
            else "Fecha"
        )

        filas.append(
            "<tr>"
            f"<td>{escape(str(columna))}</td>"
            f"<td>{tipo}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['valores_validos'])}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['valores_nulos'])}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['nulos_textuales'])}</td>"
            f'<td class="numero">'
            f"{_formatear_entero(detalle['conversiones_fallidas'])}</td>"
            f'<td class="numero">'
            f"{_formatear_porcentaje(detalle['porcentaje_conversion'])}</td>"
            f"<td>{escape(str(detalle['fecha_minima']))}</td>"
            f"<td>{escape(str(detalle['fecha_maxima']))}</td>"
            "</tr>"
        )

    return f"""
    <div class="subseccion">
        <h4>Validez temporal</h4>
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Tipo</th>
                        <th>Válidos</th>
                        <th>Nulos reales</th>
                        <th>Nulos textuales</th>
                        <th>Fallos de conversión</th>
                        <th>% conversión</th>
                        <th>Mínimo</th>
                        <th>Máximo</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(filas)}
                </tbody>
            </table>
        </div>
    </div>
    """


def _generar_incompatibilidades_semanticas_html(
    calidad: dict,
) -> str:
    """Representa incompatibilidades con el tipo semántico asignado."""
    incompatibilidades = calidad["incompatibilidades_tipo"]

    if not incompatibilidades:
        contenido = """
        <p class="sin-incidencias">
            No se han detectado incompatibilidades de tipo semántico.
        </p>
        """
    else:
        filas = []

        for columna, detalle in incompatibilidades.items():
            filas.append(
                "<tr>"
                f"<td>{escape(str(columna))}</td>"
                f"<td>{escape(_etiqueta_tipo_semantico(detalle['tipo_semantico']))}</td>"
                f'<td class="numero">'
                f"{_formatear_entero(detalle['valores_evaluados'])}</td>"
                f'<td class="numero">'
                f"{_formatear_entero(detalle['valores_incompatibles'])}</td>"
                f'<td class="numero">'
                f"{_formatear_porcentaje(detalle['porcentaje_incompatibles'])}</td>"
                "</tr>"
            )

        contenido = f"""
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Tipo semántico</th>
                        <th>Valores evaluados</th>
                        <th>Valores incompatibles</th>
                        <th>Porcentaje</th>
                    </tr>
                </thead>
                <tbody>{''.join(filas)}</tbody>
            </table>
        </div>
        """

    return f"""
    <div class="subseccion">
        <h4>Incompatibilidades de tipo semántico</h4>
        {contenido}
    </div>
    """


def _generar_reglas_negocio_html(calidad: dict) -> str:
    """Representa los incumplimientos de reglas de negocio configuradas."""
    reglas = calidad["reglas_negocio"]

    if not reglas:
        contenido = """
        <p class="sin-incidencias">
            No se han detectado incumplimientos de reglas de negocio.
        </p>
        """
    else:
        filas = []

        for columna, reglas_columna in reglas.items():
            for nombre_regla, detalle in reglas_columna.items():
                valor = detalle["valor_regla"]

                if isinstance(valor, list):
                    valor_texto = ", ".join(str(elemento) for elemento in valor)
                else:
                    valor_texto = str(valor)

                filas.append(
                    "<tr>"
                    f"<td>{escape(str(columna))}</td>"
                    f"<td>{escape(str(nombre_regla))}</td>"
                    f"<td>{escape(valor_texto)}</td>"
                    f'<td class="numero">'
                    f"{_formatear_entero(detalle['cantidad_incumplimientos'])}</td>"
                    f'<td class="numero">'
                    f"{_formatear_porcentaje(detalle['porcentaje_incumplimientos'])}</td>"
                    "</tr>"
                )

        contenido = f"""
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Regla</th>
                        <th>Valor configurado</th>
                        <th>Incumplimientos</th>
                        <th>Porcentaje</th>
                    </tr>
                </thead>
                <tbody>{''.join(filas)}</tbody>
            </table>
        </div>
        """

    return f"""
    <div class="subseccion">
        <h4>Reglas de negocio</h4>
        {contenido}
    </div>
    """


def _generar_validez_html(calidad: dict) -> str:
    """Agrupa las comprobaciones de validez disponibles en V3."""
    return f"""
    <div class="subseccion">
        <h3>Validez</h3>
        {_generar_validez_temporal_html(calidad)}
        {_generar_incompatibilidades_semanticas_html(calidad)}
        {_generar_reglas_negocio_html(calidad)}
    </div>
    """


def _generar_calidad_html(calidad: dict) -> str:
    """Agrupa las dimensiones principales de calidad."""
    return f"""
    <section>
        <h2>Calidad del dataset</h2>

        {_generar_completitud_html(calidad)}
        {_generar_unicidad_html(calidad)}
        {_generar_estructura_html(calidad)}
        {_generar_consistencia_html(calidad)}
        {_generar_validez_html(calidad)}
    </section>
    """


def _generar_estadisticas_numericas_html(
    perfil: dict,
) -> str:
    """Genera la tabla de estadísticas numéricas."""
    estadisticas = perfil["estadisticas_numericas"]

    if not estadisticas:
        contenido = """
        <p>No hay columnas numéricas para analizar.</p>
        """
    else:
        filas = []

        for columna, detalle in estadisticas.items():
            filas.append(
                "<tr>"
                f"<td>{escape(str(columna))}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['minimo'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['maximo'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['media'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['mediana'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['desviacion_estandar'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['q1'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['q3'])}</td>"
                "</tr>"
            )

        contenido = f"""
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Mínimo</th>
                        <th>Máximo</th>
                        <th>Media</th>
                        <th>Mediana</th>
                        <th>Desviación estándar</th>
                        <th>Q1</th>
                        <th>Q3</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(filas)}
                </tbody>
            </table>
        </div>
        """

    return f"""
    <section>
        <h2>Estadísticas numéricas</h2>
        {contenido}
    </section>
    """


def _generar_outliers_html(calidad: dict) -> str:
    """Genera la sección de posibles valores atípicos."""
    outliers = calidad["outliers"]

    detectados = {
        columna: detalle
        for columna, detalle in outliers.items()
        if detalle["cantidad_outliers"] > 0
    }

    if not detectados:
        contenido = """
        <p class="sin-incidencias">
            No se han detectado posibles valores atípicos.
        </p>
        """
    else:
        filas = []

        for columna, detalle in detectados.items():
            filas.append(
                "<tr>"
                f"<td>{escape(str(columna))}</td>"
                f'<td class="numero">'
                f"{_formatear_entero(detalle['cantidad_outliers'])}</td>"
                f'<td class="numero">'
                f"{_formatear_porcentaje(detalle['porcentaje_outliers'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['q1'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['q3'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['iqr'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['limite_inferior'])}</td>"
                f'<td class="numero">'
                f"{_formatear_numero(detalle['limite_superior'])}</td>"
                "</tr>"
            )

        contenido = f"""
        <div class="contenedor-tabla">
            <table class="tabla-informe">
                <thead>
                    <tr>
                        <th>Columna</th>
                        <th>Cantidad</th>
                        <th>Porcentaje</th>
                        <th>Q1</th>
                        <th>Q3</th>
                        <th>IQR</th>
                        <th>Límite inferior</th>
                        <th>Límite superior</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(filas)}
                </tbody>
            </table>
        </div>
        """

    return f"""
    <section>
        <h2>Posibles valores atípicos</h2>
        <p class="descripcion">
            Los valores se señalan mediante el criterio IQR.
            DataQualityPy no modifica los datos.
        </p>
        {contenido}
    </section>
    """


def _generar_incidencias_html(
    incidencias: list[dict],
) -> str:
    """Genera la sección de incidencias agrupadas por severidad."""
    if not incidencias:
        return """
        <section>
            <h2>Incidencias detectadas</h2>
            <p class="sin-incidencias">
                No se han detectado incidencias de calidad.
            </p>
        </section>
        """

    bloques = []

    for severidad in ("alta", "media", "baja"):
        incidencias_severidad = [
            incidencia
            for incidencia in incidencias
            if incidencia["severidad"] == severidad
        ]

        if not incidencias_severidad:
            continue

        elementos = []

        for incidencia in incidencias_severidad:
            columna = incidencia.get("columna")

            if columna is None:
                columna_html = ""
            else:
                columna_html = (
                    '<span class="etiqueta-columna">'
                    f"{escape(str(columna))}"
                    "</span>"
                )

            elementos.append(
                '<li class="incidencia-detalle '
                f"severidad-{severidad}\">"
                '<div class="incidencia-meta">'
                f'<span class="etiqueta-categoria">'
                f"{escape(str(incidencia['categoria']).capitalize())}"
                "</span>"
                f"{columna_html}"
                "</div>"
                f"<p>{escape(str(incidencia['mensaje']))}</p>"
                "</li>"
            )

        bloques.append(
            f"""
            <div class="grupo-incidencias">
                <h3>{severidad.capitalize()}</h3>
                <ul class="lista-incidencias">
                    {''.join(elementos)}
                </ul>
            </div>
            """
        )

    return f"""
    <section>
        <h2>Incidencias detectadas</h2>
        {''.join(bloques)}
    </section>
    """


def _obtener_estilos_html() -> str:
    """Devuelve los estilos generales del informe HTML."""
    return """
    :root {
        font-family: "Segoe UI", Arial, sans-serif;
        color: #24303f;
        background: #f4f6f8;
    }

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        background: #f4f6f8;
        line-height: 1.5;
    }

    .contenedor {
        width: min(1200px, calc(100% - 40px));
        margin: 32px auto;
    }

    .cabecera {
        background: #243b53;
        color: white;
        padding: 32px;
        border-radius: 12px;
        margin-bottom: 24px;
    }

    .cabecera h1 {
        margin: 0;
        font-size: 2rem;
        letter-spacing: 0.04em;
    }

    .cabecera p {
        margin: 6px 0 0;
    }

    .archivo {
        opacity: 0.85;
    }

    section {
        background: white;
        padding: 28px;
        margin-bottom: 24px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    h2 {
        margin-top: 0;
        color: #243b53;
    }

    h3 {
        margin-top: 28px;
        color: #334e68;
    }

    h4 {
        color: #486581;
        margin-bottom: 10px;
    }

    .descripcion,
    .resumen-dataset {
        color: #627d98;
    }

    .subseccion {
        padding-top: 4px;
        margin-top: 22px;
        border-top: 1px solid #e6edf3;
    }

    .tarjetas {
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(150px, 1fr));
        gap: 16px;
        margin: 22px 0;
    }

    .tarjeta {
        padding: 18px;
        border: 1px solid #d9e2ec;
        border-radius: 10px;
        background: #f8fafc;
    }

    .tarjeta-valor {
        font-size: 1.8rem;
        font-weight: 700;
    }

    .tarjeta-etiqueta {
        color: #627d98;
    }

    .tarjeta-alta {
        border-left: 5px solid #c94c4c;
    }

    .tarjeta-media {
        border-left: 5px solid #d59b2d;
    }

    .tarjeta-baja {
        border-left: 5px solid #4f7cac;
    }

    .lista-incidencias {
        padding-left: 0;
        list-style: none;
    }

    .incidencia-resumen,
    .incidencia-detalle {
        padding: 12px 14px;
        margin-bottom: 8px;
        border-radius: 7px;
        background: #f8fafc;
    }

    .incidencia-detalle p {
        margin: 7px 0 0;
    }

    .incidencia-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .etiqueta-categoria,
    .etiqueta-columna {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.78rem;
        background: #e9eff5;
        color: #486581;
    }

    .severidad-alta {
        border-left: 4px solid #c94c4c;
    }

    .severidad-media {
        border-left: 4px solid #d59b2d;
    }

    .severidad-baja {
        border-left: 4px solid #4f7cac;
    }

    .sin-incidencias {
        padding: 14px;
        background: #eef7ef;
        border-radius: 7px;
    }

    .leyenda-mapa {
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        margin: 16px 0;
    }

    .leyenda-item {
        display: inline-flex;
        align-items: center;
        gap: 7px;
    }

    .leyenda-color {
        width: 18px;
        height: 18px;
        border: 1px solid #bcccdc;
        border-radius: 3px;
    }

    .valido {
        background: #dff2e1;
    }

    .nulo-real {
        background: #f6d6d6;
    }

    .nulo-textual {
        background: #f9e8b4;
    }

    .contenedor-mapa,
    .contenedor-tabla {
        overflow-x: auto;
        margin-top: 16px;
    }

    .mapa-nulos {
        border-collapse: collapse;
        width: 100%;
    }

    .mapa-nulos th,
    .mapa-nulos td {
        border: 1px solid #d9e2ec;
        min-width: 34px;
        height: 18px;
        padding: 0;
    }

    .mapa-nulos th {
        padding: 8px;
        background: #f0f4f8;
        color: #334e68;
        font-size: 0.82rem;
        white-space: nowrap;
    }

    .datos-generales {
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px;
        margin-top: 18px;
    }

    .datos-generales div,
    .panel {
        padding: 14px;
        background: #f8fafc;
        border: 1px solid #d9e2ec;
        border-radius: 8px;
    }

    .datos-generales span {
        display: block;
        color: #627d98;
        font-size: 0.85rem;
        margin-bottom: 4px;
    }

    .datos-generales strong {
        word-break: break-word;
    }

    .dos-columnas,
    .tres-columnas {
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(240px, 1fr));
        gap: 14px;
    }

    .tabla-informe {
        width: 100%;
        border-collapse: collapse;
    }

    .tabla-informe th,
    .tabla-informe td {
        padding: 10px 12px;
        border-bottom: 1px solid #d9e2ec;
        text-align: left;
        vertical-align: top;
    }

    .tabla-informe th {
        background: #f0f4f8;
        color: #334e68;
        white-space: nowrap;
    }

    .tabla-informe tbody tr:hover {
        background: #f8fafc;
    }

    .tabla-informe .numero {
        text-align: right;
        white-space: nowrap;
    }

    .pie-informe {
        text-align: center;
        color: #829ab1;
        padding: 8px 0 30px;
        font-size: 0.9rem;
    }

    @media (max-width: 700px) {
        .contenedor {
            width: min(100% - 20px, 1200px);
            margin: 10px auto;
        }

        .cabecera,
        section {
            padding: 20px;
            border-radius: 8px;
        }
    }
    """


def generar_documento_html(
    resultado_auditoria: dict,
    datos: pd.DataFrame,
    *,
    resultado_reauditoria=None,
    manifiesto_reproducibilidad=None,
) -> str:
    """Construye el documento HTML completo de la auditoría."""
    dataset = resultado_auditoria["dataset"]
    perfil = resultado_auditoria["perfil"]
    tipos_semanticos = resultado_auditoria["tipos_semanticos"]
    calidad = resultado_auditoria["calidad"]
    incidencias = resultado_auditoria["incidencias"]
    resumen = resultado_auditoria["resumen"]

    nombre_archivo = escape(str(dataset["archivo"]))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>DataQualityPy - {nombre_archivo}</title>

    <style>
        {_obtener_estilos_html()}
    </style>
</head>

<body>
    <main class="contenedor">
        <header class="cabecera">
            <h1>DATAQUALITYPY</h1>
            <p>Informe de calidad de datos</p>
            <p class="archivo">{nombre_archivo}</p>
        </header>

        {_generar_resumen_html(dataset, resumen)}

        <section>
            <h2>Mapa de valores ausentes</h2>
            {generar_mapa_nulos_html(datos)}
        </section>

        {_generar_perfil_html(dataset, perfil, tipos_semanticos)}

        {_generar_calidad_html(calidad)}

        {_generar_incidencias_html(incidencias)}

        {_generar_estadisticas_numericas_html(perfil)}

        {_generar_outliers_html(calidad)}

        {generar_bloques_v7_html(
            resultado_auditoria,
            resultado_reauditoria=resultado_reauditoria,
            manifiesto_reproducibilidad=manifiesto_reproducibilidad,
        )}

        <footer class="pie-informe">
            Generado por DataQualityPy
        </footer>
    </main>
</body>
</html>
"""


def generar_informe_html(
    resultado_auditoria: dict,
    datos: pd.DataFrame,
    ruta_salida: str | Path,
    *,
    resultado_reauditoria=None,
    manifiesto_reproducibilidad=None,
) -> Path:
    """Genera y guarda el informe de auditoría en formato HTML."""
    ruta_salida = Path(ruta_salida)

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    contenido = generar_documento_html(
        resultado_auditoria,
        datos,
        resultado_reauditoria=resultado_reauditoria,
        manifiesto_reproducibilidad=manifiesto_reproducibilidad,
    )

    ruta_salida.write_text(
        contenido,
        encoding="utf-8",
    )

    return ruta_salida
