"""Generación de incidencias a partir de los análisis de calidad."""


def _clasificar_severidad_por_porcentaje(
    porcentaje: float,
) -> str:
    """Clasifica la severidad según el porcentaje afectado."""
    if porcentaje < 5:
        return "baja"

    if porcentaje < 20:
        return "media"

    return "alta"


def _calcular_porcentaje(
    cantidad: int,
    total: int,
) -> float:
    """Calcula un porcentaje evitando divisiones entre cero."""
    if total == 0:
        return 0.0

    return (cantidad / total) * 100


def _formatear_porcentaje_mensaje(porcentaje: float) -> str:
    """Formatea un porcentaje para incluirlo en un mensaje."""
    return f"{porcentaje:.2f}".replace(".", ",") + " %"


def _texto_cantidad(
    cantidad: int,
    singular: str,
    plural: str,
) -> str:
    """Devuelve una cantidad acompañada del singular o plural adecuado."""
    termino = singular if cantidad == 1 else plural
    return f"{cantidad} {termino}"


def _columna_es_nula_textual_completa(
    columna: str,
    nulos_textuales: dict,
) -> bool:
    """Indica si todos los registros de una columna son nulos textuales."""
    resultado = nulos_textuales.get(columna)

    if resultado is None:
        return False

    porcentaje = resultado[
        "porcentaje_posibles_nulos_textuales"
    ]

    return porcentaje == 100.0


def generar_incidencias(
    calidad: dict,
    total_filas: int,
) -> list[dict]:
    """Genera incidencias estructuradas a partir de la calidad analizada."""
    incidencias = []

    columnas_vacias = set(
        calidad["columnas_problematicas"]["columnas_vacias"]
    )

    # Valores nulos reales
    for columna, resultado in calidad["nulos"]["por_columna"].items():
        cantidad = resultado["nulos"]

        if cantidad == 0 or columna in columnas_vacias:
            continue

        porcentaje = resultado["porcentaje_nulos"]

        incidencias.append(
            {
                "tipo": "nulos_reales",
                "categoria": "completitud",
                "severidad": (
                    _clasificar_severidad_por_porcentaje(
                        porcentaje
                    )
                ),
                "columna": columna,
                "cantidad": cantidad,
                "porcentaje": porcentaje,
                "mensaje": (
                    f"La columna '{columna}' contiene "
                    f"{_texto_cantidad(
                        cantidad,
                        'valor nulo',
                        'valores nulos',
                    )} "
                    f"({_formatear_porcentaje_mensaje(porcentaje)} "
                    "de los registros)."
                ),
            }
        )

    # Posibles nulos textuales
    for columna, resultado in calidad["nulos_textuales"].items():
        cantidad = resultado[
            "total_posibles_nulos_textuales"
        ]
        porcentaje = resultado[
            "porcentaje_posibles_nulos_textuales"
        ]

        if cantidad == 0:
            continue

        incidencias.append(
            {
                "tipo": "nulos_textuales",
                "categoria": "completitud",
                "severidad": (
                    _clasificar_severidad_por_porcentaje(
                        porcentaje
                    )
                ),
                "columna": columna,
                "cantidad": cantidad,
                "porcentaje": porcentaje,
                "mensaje": (
                    f"La columna '{columna}' contiene "
                    f"{_texto_cantidad(
                        cantidad,
                        'posible nulo textual',
                        'posibles nulos textuales',
                    )} "
                    f"({_formatear_porcentaje_mensaje(porcentaje)} "
                    "de los registros)."
                ),
            }
        )

    # Filas completamente duplicadas
    resultado_duplicados = calidad["duplicados"]
    cantidad_duplicados = resultado_duplicados[
        "filas_duplicadas"
    ]

    if cantidad_duplicados > 0:
        porcentaje = resultado_duplicados[
            "porcentaje_duplicados"
        ]

        incidencias.append(
            {
                "tipo": "filas_duplicadas",
                "categoria": "unicidad",
                "severidad": (
                    _clasificar_severidad_por_porcentaje(
                        porcentaje
                    )
                ),
                "columna": None,
                "cantidad": cantidad_duplicados,
                "porcentaje": porcentaje,
                "mensaje": (
                    "Se ha detectado "
                    f"{_texto_cantidad(
                        cantidad_duplicados,
                        'fila duplicada',
                        'filas duplicadas',
                    )} "
                    f"({_formatear_porcentaje_mensaje(porcentaje)} "
                    "de los registros)."
                ),
            }
        )

    # Duplicados según una clave configurada
    resultado_clave = calidad["duplicados_clave"]

    if resultado_clave["clave_configurada"]:
        columnas_inexistentes = resultado_clave[
            "columnas_inexistentes"
        ]

        if columnas_inexistentes:
            columnas = ", ".join(columnas_inexistentes)

            incidencias.append(
                {
                    "tipo": "clave_inexistente",
                    "categoria": "estructura",
                    "severidad": "alta",
                    "columna": None,
                    "cantidad": len(columnas_inexistentes),
                    "porcentaje": None,
                    "mensaje": (
                        "No se ha podido analizar la clave "
                        "configurada porque no existen las columnas: "
                        f"{columnas}."
                    ),
                }
            )

        else:
            cantidad = resultado_clave[
                "registros_con_clave_duplicada"
            ]

            if cantidad > 0:
                porcentaje = resultado_clave[
                    "porcentaje_registros_duplicados"
                ]
                nombre_clave = " + ".join(
                    resultado_clave["columnas_clave"]
                )

                incidencias.append(
                    {
                        "tipo": "duplicados_clave",
                        "categoria": "unicidad",
                        "severidad": (
                            _clasificar_severidad_por_porcentaje(
                                porcentaje
                            )
                        ),
                        "columna": None,
                        "cantidad": cantidad,
                        "porcentaje": porcentaje,
                        "mensaje": (
                            "Se han detectado "
                            f"{_texto_cantidad(
                                cantidad,
                                'registro duplicado',
                                'registros duplicados',
                            )} "
                            "para la clave "
                            f"'{nombre_clave}' "
                            f"({_formatear_porcentaje_mensaje(porcentaje)} "
                            "de los registros válidos)."
                        ),
                    }
                )

    # Columnas completamente vacías
    for columna in calidad[
        "columnas_problematicas"
    ]["columnas_vacias"]:
        incidencias.append(
            {
                "tipo": "columna_vacia",
                "categoria": "estructura",
                "severidad": "alta",
                "columna": columna,
                "cantidad": None,
                "porcentaje": None,
                "mensaje": (
                    f"La columna '{columna}' está "
                    "completamente vacía."
                ),
            }
        )

    # Columnas constantes
    for columna in calidad[
        "columnas_problematicas"
    ]["columnas_constantes"]:
        if _columna_es_nula_textual_completa(
            columna,
            calidad["nulos_textuales"],
        ):
            continue

        incidencias.append(
            {
                "tipo": "columna_constante",
                "categoria": "estructura",
                "severidad": "baja",
                "columna": columna,
                "cantidad": None,
                "porcentaje": None,
                "mensaje": (
                    f"La columna '{columna}' contiene "
                    "un único valor distinto."
                ),
            }
        )

    # Problemas e inconsistencias de texto
    for columna, resultado in calidad["texto"].items():
        cantidad_espacios = resultado["valores_con_espacios"]

        if cantidad_espacios > 0:
            porcentaje = _calcular_porcentaje(
                cantidad_espacios,
                total_filas,
            )

            incidencias.append(
                {
                    "tipo": "espacios_texto",
                    "categoria": "consistencia",
                    "severidad": (
                        _clasificar_severidad_por_porcentaje(
                            porcentaje
                        )
                    ),
                    "columna": columna,
                    "cantidad": cantidad_espacios,
                    "porcentaje": porcentaje,
                    "mensaje": (
                        f"La columna '{columna}' contiene "
                        f"{_texto_cantidad(
                            cantidad_espacios,
                            'valor con espacios',
                            'valores con espacios',
                        )} "
                        "al inicio o al final "
                        f"({_formatear_porcentaje_mensaje(porcentaje)} "
                        "de los registros)."
                    ),
                }
            )

        grupos_inconsistentes = resultado[
            "grupos_inconsistentes"
        ]

        if grupos_inconsistentes:
            incidencias.append(
                {
                    "tipo": "inconsistencia_categorica",
                    "categoria": "consistencia",
                    "severidad": "media",
                    "columna": columna,
                    "cantidad": len(grupos_inconsistentes),
                    "porcentaje": None,
                    "mensaje": (
                        f"La columna '{columna}' contiene posibles "
                        "inconsistencias entre variantes de categorías."
                    ),
                }
            )

    # Posibles valores atípicos
    for columna, resultado in calidad["outliers"].items():
        cantidad = resultado["cantidad_outliers"]

        if cantidad == 0:
            continue

        incidencias.append(
            {
                "tipo": "outliers",
                "categoria": "validez",
                "severidad": "baja",
                "columna": columna,
                "cantidad": cantidad,
                "porcentaje": resultado[
                    "porcentaje_outliers"
                ],
                "mensaje": (
                    f"La columna '{columna}' contiene "
                    f"{_texto_cantidad(
                        cantidad,
                        'posible valor atípico',
                        'posibles valores atípicos',
                    )} "
                    "según el criterio IQR."
                ),
            }
        )

    # Incompatibilidades con el tipo semántico asignado
    columnas_con_incompatibilidad_semantica = set()

    for columna, resultado in calidad[
        "incompatibilidades_tipo"
    ].items():
        cantidad = resultado["cantidad_incompatibles"]

        if cantidad == 0:
            continue

        porcentaje = resultado["porcentaje_incompatibles"]
        tipo_semantico = resultado["tipo_semantico"]

        columnas_con_incompatibilidad_semantica.add(columna)

        incidencias.append(
            {
                "tipo": "incompatibilidad_tipo",
                "categoria": "validez",
                "severidad": (
                    _clasificar_severidad_por_porcentaje(
                        porcentaje
                    )
                ),
                "columna": columna,
                "cantidad": cantidad,
                "porcentaje": porcentaje,
                "mensaje": (
                    f"La columna '{columna}' contiene "
                    f"{_texto_cantidad(
                        cantidad,
                        'valor incompatible',
                        'valores incompatibles',
                    )} "
                    "con el tipo semántico "
                    f"'{tipo_semantico}' "
                    f"({_formatear_porcentaje_mensaje(porcentaje)} "
                    "de los valores evaluables)."
                ),
            }
        )

    # Incumplimientos de reglas de negocio configuradas
    for columna, reglas in calidad["reglas_negocio"].items():
        for nombre_regla, resultado in reglas.items():
            cantidad = resultado["cantidad_incumplimientos"]

            if cantidad == 0:
                continue

            porcentaje = resultado["porcentaje_incumplimientos"]

            if nombre_regla in {"min", "max"}:
                descripcion_regla = (
                    f"{nombre_regla}={resultado['valor_regla']}"
                )
            else:
                descripcion_regla = nombre_regla

            incidencias.append(
                {
                    "tipo": "incumplimiento_regla",
                    "categoria": "validez",
                    "severidad": (
                        _clasificar_severidad_por_porcentaje(
                            porcentaje
                        )
                    ),
                    "columna": columna,
                    "cantidad": cantidad,
                    "porcentaje": porcentaje,
                    "mensaje": (
                        f"La columna '{columna}' contiene "
                        f"{_texto_cantidad(
                            cantidad,
                            'valor que incumple',
                            'valores que incumplen',
                        )} "
                        f"la regla '{descripcion_regla}' "
                        f"({_formatear_porcentaje_mensaje(porcentaje)} "
                        "de los valores evaluables para la regla)."
                    ),
                }
            )

    # Conversiones de fecha fallidas
    for columna, resultado in calidad["fechas"].items():
        if columna in columnas_con_incompatibilidad_semantica:
            continue

        cantidad_fallos = resultado["conversiones_fallidas"]

        if cantidad_fallos == 0:
            continue

        total_evaluable = (
            resultado["valores_validos"]
            + cantidad_fallos
        )

        porcentaje = _calcular_porcentaje(
            cantidad_fallos,
            total_evaluable,
        )

        incidencias.append(
            {
                "tipo": "conversion_fecha",
                "categoria": "validez",
                "severidad": (
                    _clasificar_severidad_por_porcentaje(
                        porcentaje
                    )
                ),
                "columna": columna,
                "cantidad": cantidad_fallos,
                "porcentaje": porcentaje,
                "mensaje": (
                    f"La columna '{columna}' contiene "
                    f"{_texto_cantidad(
                        cantidad_fallos,
                        'valor que no pudo',
                        'valores que no pudieron',
                    )} "
                    "interpretarse como fecha "
                    f"({_formatear_porcentaje_mensaje(porcentaje)} "
                    "de los valores evaluables)."
                ),
            }
        )

    return incidencias