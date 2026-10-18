"""Elementos compartidos de la interfaz de resultados de DataQualityPy."""

from html import escape


ETIQUETAS_CATEGORIAS = {
    "completitud": "Completitud",
    "unicidad": "Unicidad",
    "estructura": "Estructura",
    "consistencia": "Consistencia",
    "validez": "Validez",
}

ETIQUETAS_TIPOS = {
    "numerico": "Numérico",
    "fecha": "Fecha",
    "fecha_hora": "Fecha y hora",
    "booleano_binario": "Booleano/binario",
    "categorico": "Categórico",
    "identificador": "Identificador",
    "texto_libre": "Texto libre",
}

ETIQUETAS_SEVERIDADES = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}

ETIQUETAS_TIPOS_INCIDENCIA = {
    "nulos_reales": "Valores nulos",
    "nulos_textuales": "Posibles nulos textuales",
    "filas_duplicadas": "Filas duplicadas",
    "clave_inexistente": "Clave inexistente",
    "duplicados_clave": "Duplicados según clave",
    "columna_vacia": "Columna vacía",
    "columna_constante": "Columna constante",
    "espacios_texto": "Espacios en texto",
    "inconsistencia_categorica": "Inconsistencia categórica",
    "outliers": "Valores atípicos",
    "incompatibilidad_tipo": "Incompatibilidad de tipo",
    "incumplimiento_regla": "Incumplimiento de regla",
    "conversion_fecha": "Conversión de fecha",
}


def _formatear_etiqueta(valor: str, etiquetas: dict[str, str]) -> str:
    """Devuelve una etiqueta legible garantizando siempre un texto."""

    if valor == "Todas":
        return "Todas"

    return etiquetas.get(valor, valor)


def _tarjeta_indicador(
    etiqueta: str,
    valor: object,
    color_acento: str | None = None,
) -> str:
    """Construye una tarjeta visual para un indicador ya calculado."""

    borde_acento = (
        f"border-left:4px solid {color_acento};"
        if color_acento
        else ""
    )

    # El HTML se mantiene en una sola línea para evitar que Markdown
    # interprete las propiedades CSS indentadas como bloques de código.
    return (
        f'<div style="border:1px solid rgba(128,128,128,0.35);'
        f'{borde_acento}border-radius:8px;padding:14px 16px;'
        f'min-height:86px;box-sizing:border-box;">'
        f'<div style="font-size:1.65rem;font-weight:700;line-height:1.15;'
        f'margin-bottom:5px;">{escape(str(valor))}</div>'
        f'<div style="font-size:0.9rem;opacity:0.78;">'
        f'{escape(etiqueta)}</div></div>'
    )


def _formatear_porcentaje_ui(valor: object) -> str:
    """Formatea porcentajes V6.1 para su presentación."""

    try:
        return f"{float(str(valor)):.2f} %".replace(".", ",")
    except (TypeError, ValueError):
        return "—"
