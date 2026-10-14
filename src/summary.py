"""Generación del resumen ejecutivo de la auditoría."""

SEVERIDADES = (
    "alta",
    "media",
    "baja",
)

CATEGORIAS = (
    "completitud",
    "unicidad",
    "estructura",
    "consistencia",
    "validez",
)

TIPOS_SEMANTICOS = (
    "numerico",
    "fecha",
    "fecha_hora",
    "booleano_binario",
    "categorico",
    "identificador",
    "texto_libre",
)

TIPOS_COMPATIBILIDAD_COMPROBABLE = {
    "numerico",
    "fecha",
    "fecha_hora",
    "booleano_binario",
}

TIPOS_CONSISTENCIA_TEXTO = {
    "categorico",
    "texto_libre",
}

MAX_INCIDENCIAS_PRINCIPALES = 5


def _contar_por_campo(
    incidencias: list[dict],
    campo: str,
    valores: tuple[str, ...],
) -> dict[str, int]:
    """Cuenta incidencias para un conjunto conocido de valores."""
    return {
        valor: sum(
            1
            for incidencia in incidencias
            if incidencia[campo] == valor
        )
        for valor in valores
    }


def _seleccionar_incidencias_principales(
    incidencias: list[dict],
    limite: int = MAX_INCIDENCIAS_PRINCIPALES,
) -> list[dict]:
    """Selecciona las incidencias principales por severidad."""
    principales = []

    for severidad in SEVERIDADES:
        for incidencia in incidencias:
            if incidencia["severidad"] != severidad:
                continue

            principales.append(incidencia)

            if len(principales) == limite:
                return principales

    return principales


def _contar_tipos_semanticos(
    tipos_semanticos: dict,
) -> dict[str, int]:
    """Cuenta columnas por tipo semántico manteniendo los siete tipos."""
    conteo = {
        tipo: 0
        for tipo in TIPOS_SEMANTICOS
    }

    for resultado in tipos_semanticos.values():
        tipo = resultado["tipo"]

        if tipo in conteo:
            conteo[tipo] += 1

    return conteo


def _obtener_tipos_presentes(
    tipos_semanticos: dict,
) -> set[str]:
    """Obtiene los tipos semánticos presentes en el dataset."""
    return {
        resultado["tipo"]
        for resultado in tipos_semanticos.values()
    }


def _generar_cobertura_auditoria(
    tipos_semanticos: dict,
    configuracion: dict,
) -> dict[str, list[str]]:
    """Clasifica la cobertura de los controles de auditoría."""
    aplicados = [
        "completitud",
        "unicidad_general",
    ]
    no_aplicables = []
    no_configurados = []

    tipos_presentes = _obtener_tipos_presentes(tipos_semanticos)

    if tipos_presentes & TIPOS_CONSISTENCIA_TEXTO:
        aplicados.append("consistencia_texto")
    else:
        no_aplicables.append("consistencia_texto")

    if "numerico" in tipos_presentes:
        aplicados.append("outliers")
    else:
        no_aplicables.append("outliers")

    if tipos_presentes & TIPOS_COMPATIBILIDAD_COMPROBABLE:
        aplicados.append("compatibilidad_semantica")
    else:
        no_aplicables.append("compatibilidad_semantica")

    if configuracion.get("columnas_clave"):
        aplicados.append("unicidad_clave")
    else:
        no_configurados.append("unicidad_clave")

    if configuracion.get("reglas_columnas"):
        aplicados.append("reglas_negocio")
    else:
        no_configurados.append("reglas_negocio")

    return {
        "controles_aplicados": aplicados,
        "controles_no_aplicables": no_aplicables,
        "controles_no_configurados": no_configurados,
    }


def generar_resumen_ejecutivo(
    incidencias: list[dict],
    tipos_semanticos: dict,
    calidad: dict,
    configuracion: dict,
) -> dict:
    """Genera el resumen ejecutivo estructurado V3 de la auditoría."""
    _ = calidad

    return {
        "total_incidencias": len(incidencias),
        "por_severidad": _contar_por_campo(
            incidencias,
            campo="severidad",
            valores=SEVERIDADES,
        ),
        "por_categoria": _contar_por_campo(
            incidencias,
            campo="categoria",
            valores=CATEGORIAS,
        ),
        "principales_incidencias": (
            _seleccionar_incidencias_principales(incidencias)
        ),
        "tipos_semanticos": _contar_tipos_semanticos(
            tipos_semanticos
        ),
        "cobertura_auditoria": _generar_cobertura_auditoria(
            tipos_semanticos,
            configuracion,
        ),
    }
