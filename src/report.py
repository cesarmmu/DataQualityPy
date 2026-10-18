"""Presentación en consola de los resultados de DataQualityPy."""


def _formatear_porcentaje(valor: float) -> str:
    """Formatea un porcentaje con dos decimales."""
    return f"{valor:.2f}".replace(".", ",") + " %"


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


def _formatear_numero(valor: float) -> str:
    """Formatea un número decimal con dos decimales."""
    return f"{valor:.2f}".replace(".", ",")


def _formatear_entero(valor: int) -> str:
    """Formatea un entero con separador de miles."""
    return f"{valor:,}".replace(",", ".")


def mostrar_resumen_ejecutivo(
    dataset: dict,
    resumen: dict,
) -> None:
    """Muestra el resumen ejecutivo de la auditoría."""
    print()
    print("RESUMEN EJECUTIVO")
    print("-" * 60)
    print(
        "Dataset: "
        f"{_formatear_entero(dataset['filas'])} filas · "
        f"{_formatear_entero(dataset['columnas'])} columnas"
    )
    print()

    total = resumen["total_incidencias"]

    print(
        "Incidencias detectadas: "
        f"{_formatear_entero(total)}"
    )

    por_severidad = resumen["por_severidad"]

    print(
        "  Altas:   "
        f"{_formatear_entero(por_severidad['alta'])}"
    )
    print(
        "  Medias:  "
        f"{_formatear_entero(por_severidad['media'])}"
    )
    print(
        "  Bajas:   "
        f"{_formatear_entero(por_severidad['baja'])}"
    )

    print()
    print("Incidencias por categoría:")

    etiquetas_categorias = {
        "completitud": "Completitud",
        "unicidad": "Unicidad",
        "estructura": "Estructura",
        "consistencia": "Consistencia",
        "validez": "Validez",
    }

    for categoria, etiqueta in etiquetas_categorias.items():
        cantidad = resumen["por_categoria"][categoria]
        print(
            f"  {etiqueta}: "
            f"{_formatear_entero(cantidad)}"
        )

    print()
    print("TIPOS SEMÁNTICOS")

    etiquetas_tipos = {
        "numerico": "Numérico",
        "fecha": "Fecha",
        "fecha_hora": "Fecha y hora",
        "booleano_binario": "Booleano/binario",
        "categorico": "Categórico",
        "identificador": "Identificador",
        "texto_libre": "Texto libre",
    }

    for tipo, etiqueta in etiquetas_tipos.items():
        cantidad = resumen["tipos_semanticos"][tipo]
        print(
            f"  {etiqueta}: "
            f"{_formatear_entero(cantidad)}"
        )

    print()
    print("COBERTURA DE AUDITORÍA")

    cobertura = resumen["cobertura_auditoria"]
    etiquetas_controles = {
        "completitud": "Completitud",
        "unicidad_general": "Unicidad general",
        "consistencia_texto": "Consistencia de texto",
        "outliers": "Valores atípicos",
        "compatibilidad_semantica": "Compatibilidad semántica",
        "unicidad_clave": "Unicidad por clave",
        "reglas_negocio": "Reglas de negocio",
    }

    grupos_cobertura = (
        ("controles_aplicados", "Controles aplicados:"),
        ("controles_no_aplicables", "Controles no aplicables:"),
        ("controles_no_configurados", "Controles no configurados:"),
    )

    for clave, titulo in grupos_cobertura:
        print(titulo)
        controles = cobertura[clave]

        if not controles:
            print("  - Ninguno")
            continue

        for control in controles:
            print(
                "  - "
                + etiquetas_controles.get(
                    control,
                    control,
                )
            )

    principales = resumen["principales_incidencias"]

    if principales:
        print()
        print("Principales incidencias:")

        for incidencia in principales:
            print(
                f"  [{incidencia['severidad'].upper()}] "
                f"{incidencia['mensaje']}"
            )
    elif total == 0:
        print()
        print("No se han detectado incidencias de calidad.")


def mostrar_resumen(
    dataset: dict,
    perfil: dict,
) -> None:
    """Muestra la información estructural principal del dataset."""
    print()
    print("1. RESUMEN DEL DATASET")
    print("-" * 60)
    print(f"Archivo: {dataset['archivo']}")
    print(
        "Filas: "
        f"{_formatear_entero(dataset['filas'])}"
    )
    print(
        "Columnas: "
        f"{_formatear_entero(dataset['columnas'])}"
    )
    print(
        "Memoria utilizada: "
        f"{_formatear_memoria(dataset['memoria_bytes'])}"
    )
    print("Nombres de columnas:")

    for columna in perfil["nombres_columnas"]:
        print(f"  - {columna}")


def mostrar_tipos(
    perfil: dict,
    tipos_semanticos: dict,
) -> None:
    """Muestra los tipos físicos y semánticos de cada columna."""
    print()
    print("2. TIPOS DE DATOS Y TIPOS SEMÁNTICOS")
    print("-" * 60)

    etiquetas_tipos = {
        "numerico": "Numérico",
        "fecha": "Fecha",
        "fecha_hora": "Fecha y hora",
        "booleano_binario": "Booleano/binario",
        "categorico": "Categórico",
        "identificador": "Identificador",
        "texto_libre": "Texto libre",
    }
    etiquetas_origen = {
        "inferred": "Inferido",
        "declared": "Declarado",
    }

    for columna in perfil["nombres_columnas"]:
        tipo_fisico = perfil["tipos_datos"][columna]
        distintos = perfil["valores_distintos"][columna]
        semantica = tipos_semanticos[columna]

        print(f"{columna}:")
        print(f"  - Dtype físico: {tipo_fisico}")
        print(
            "  - Tipo semántico: "
            f"{etiquetas_tipos.get(semantica['tipo'], semantica['tipo'])}"
        )
        print(
            "  - Confianza: "
            f"{semantica['confianza'].capitalize()}"
        )
        print(
            "  - Origen: "
            f"{etiquetas_origen.get(semantica['fuente'], semantica['fuente'])}"
        )
        print(
            "  - Valores distintos: "
            f"{_formatear_entero(distintos)}"
        )


def mostrar_nulos(calidad: dict) -> None:
    """Muestra el análisis de valores nulos reales."""
    resultado = calidad["nulos"]

    print()
    print("3. VALORES NULOS REALES")
    print("-" * 60)
    print(
        "Total de valores nulos: "
        f"{_formatear_entero(resultado['total_nulos'])}"
    )
    print(
        "Columnas con nulos: "
        f"{_formatear_entero(resultado['columnas_con_nulos'])}"
    )

    columnas_con_nulos = [
        (columna, detalle)
        for columna, detalle in resultado["por_columna"].items()
        if detalle["nulos"] > 0
    ]

    if not columnas_con_nulos:
        print("No se han detectado valores nulos reales.")
        return

    for columna, detalle in columnas_con_nulos:
        print(
            f"  - {columna}: "
            f"{_formatear_entero(detalle['nulos'])} "
            f"({_formatear_porcentaje(
                detalle['porcentaje_nulos']
            )})"
        )


def mostrar_nulos_textuales(calidad: dict) -> None:
    """Muestra posibles valores ausentes conservados como texto."""
    resultado = calidad["nulos_textuales"]

    print()
    print("4. POSIBLES NULOS TEXTUALES")
    print("-" * 60)

    if not resultado:
        print("No se han detectado posibles nulos textuales.")
        return

    for columna, detalle in resultado.items():
        print(
            f"{columna}: "
            f"{_formatear_entero(
                detalle['total_posibles_nulos_textuales']
            )} "
            f"({_formatear_porcentaje(
                detalle['porcentaje_posibles_nulos_textuales']
            )})"
        )

        marcadores = detalle["marcadores_detectados"]

        if marcadores:
            print("  Marcadores detectados:")

            for marcador, cantidad in marcadores.items():
                print(
                    f"    - {marcador}: "
                    f"{_formatear_entero(cantidad)}"
                )


def mostrar_identificadores(calidad: dict) -> None:
    """Muestra las columnas que podrían actuar como identificadores."""
    resultado = calidad["identificadores"]

    print()
    print("5. POSIBLES IDENTIFICADORES")
    print("-" * 60)

    identificadores = {
        columna: detalle
        for columna, detalle in resultado.items()
        if detalle["posible_identificador"]
    }

    if not identificadores:
        print("No se han detectado posibles identificadores.")
        return

    for columna, detalle in identificadores.items():
        print(f"{columna}:")
        print(
            "  - Valores no nulos evaluados: "
            f"{_formatear_entero(
                detalle['valores_no_nulos']
            )}"
        )
        print(
            "  - Valores distintos: "
            f"{_formatear_entero(
                detalle['valores_distintos']
            )}"
        )
        print(
            "  - Porcentaje de unicidad: "
            f"{_formatear_porcentaje(
                detalle['porcentaje_unicidad']
            )}"
        )


def mostrar_duplicados(calidad: dict) -> None:
    """Muestra el análisis de filas completamente duplicadas."""
    resultado = calidad["duplicados"]

    print()
    print("6. FILAS DUPLICADAS")
    print("-" * 60)
    print(
        "Filas duplicadas: "
        f"{_formatear_entero(resultado['filas_duplicadas'])}"
    )
    print(
        "Porcentaje de duplicados: "
        f"{_formatear_porcentaje(
            resultado['porcentaje_duplicados']
        )}"
    )


def mostrar_duplicados_clave(calidad: dict) -> None:
    """Muestra el análisis de duplicados según la clave configurada."""
    resultado = calidad["duplicados_clave"]

    print()
    print("7. DUPLICADOS SEGÚN CLAVE")
    print("-" * 60)

    if not resultado["clave_configurada"]:
        print("No se ha configurado ninguna clave de análisis.")
        return

    print(
        "Columnas clave: "
        + ", ".join(resultado["columnas_clave"])
    )

    if resultado["columnas_inexistentes"]:
        print(
            "Columnas inexistentes: "
            + ", ".join(resultado["columnas_inexistentes"])
        )
        return

    print(
        "Registros válidos: "
        f"{_formatear_entero(resultado['registros_validos'])}"
    )
    print(
        "Registros excluidos: "
        f"{_formatear_entero(resultado['registros_excluidos'])}"
    )
    print(
        "Registros con clave duplicada: "
        f"{_formatear_entero(
            resultado['registros_con_clave_duplicada']
        )}"
    )
    print(
        "Valores de clave duplicados: "
        f"{_formatear_entero(
            resultado['valores_clave_duplicados']
        )}"
    )
    print(
        "Porcentaje de registros duplicados: "
        f"{_formatear_porcentaje(
            resultado['porcentaje_registros_duplicados']
        )}"
    )


def mostrar_columnas_problematicas(calidad: dict) -> None:
    """Muestra columnas completamente vacías y constantes."""
    resultado = calidad["columnas_problematicas"]

    print()
    print("8. COLUMNAS VACÍAS Y CONSTANTES")
    print("-" * 60)

    vacias = resultado["columnas_vacias"]
    constantes = resultado["columnas_constantes"]

    if vacias:
        print("Columnas completamente vacías:")

        for columna in vacias:
            print(f"  - {columna}")
    else:
        print("No se han detectado columnas completamente vacías.")

    if constantes:
        print("Columnas constantes:")

        for columna in constantes:
            print(f"  - {columna}")
    else:
        print("No se han detectado columnas constantes.")


def mostrar_estadisticas_numericas(perfil: dict) -> None:
    """Muestra estadísticas descriptivas de columnas numéricas."""
    resultado = perfil["estadisticas_numericas"]

    print()
    print("9. ESTADÍSTICAS NUMÉRICAS")
    print("-" * 60)

    if not resultado:
        print("No hay columnas numéricas para analizar.")
        return

    etiquetas = (
        ("minimo", "Mínimo"),
        ("maximo", "Máximo"),
        ("media", "Media"),
        ("mediana", "Mediana"),
        ("desviacion_estandar", "Desviación estándar"),
        ("q1", "Q1"),
        ("q3", "Q3"),
    )

    for columna, estadisticas in resultado.items():
        print(f"{columna}:")

        for clave, etiqueta in etiquetas:
            print(
                f"  - {etiqueta}: "
                f"{_formatear_numero(estadisticas[clave])}"
            )


def mostrar_texto(calidad: dict) -> None:
    """Muestra el análisis de texto y categorías."""
    resultado = calidad["texto"]

    print()
    print("10. ANÁLISIS DE TEXTO Y CATEGORÍAS")
    print("-" * 60)

    if not resultado:
        print("No hay columnas de texto para analizar.")
        return

    for columna, detalle in resultado.items():
        print(f"{columna}:")
        print(
            "  - Valores con espacios exteriores: "
            f"{_formatear_entero(
                detalle['valores_con_espacios']
            )}"
        )
        print(
            "  - Baja cardinalidad: "
            f"{'Sí' if detalle['baja_cardinalidad'] else 'No'}"
        )

        grupos = detalle["grupos_inconsistentes"]

        if grupos:
            print("  - Posibles inconsistencias categóricas:")

            for grupo in grupos:
                variantes = ", ".join(
                    f"{repr(valor)} ({cantidad})"
                    for valor, cantidad
                    in grupo["variantes"].items()
                )
                print(f"      {variantes}")
        elif detalle["posibles_diferencias_mayusculas"]:
            print(
                "  - Se han detectado posibles diferencias "
                "de mayúsculas y minúsculas."
            )


def mostrar_outliers(calidad: dict) -> None:
    """Muestra los posibles valores atípicos detectados mediante IQR."""
    resultado = calidad["outliers"]

    print()
    print("11. POSIBLES VALORES ATÍPICOS")
    print("-" * 60)

    columnas_con_outliers = {
        columna: detalle
        for columna, detalle in resultado.items()
        if detalle["cantidad_outliers"] > 0
    }

    if not columnas_con_outliers:
        print("No se han detectado posibles valores atípicos.")
        return

    for columna, detalle in columnas_con_outliers.items():
        print(f"{columna}:")
        print(
            "  - Posibles valores atípicos: "
            f"{_formatear_entero(
                detalle['cantidad_outliers']
            )}"
        )
        print(
            "  - Porcentaje: "
            f"{_formatear_porcentaje(
                detalle['porcentaje_outliers']
            )}"
        )
        print(
            "  - Q1: "
            f"{_formatear_numero(detalle['q1'])}"
        )
        print(
            "  - Q3: "
            f"{_formatear_numero(detalle['q3'])}"
        )
        print(
            "  - IQR: "
            f"{_formatear_numero(detalle['iqr'])}"
        )
        print(
            "  - Límite inferior: "
            f"{_formatear_numero(
                detalle['limite_inferior']
            )}"
        )
        print(
            "  - Límite superior: "
            f"{_formatear_numero(
                detalle['limite_superior']
            )}"
        )


def mostrar_fechas(calidad: dict) -> None:
    """Muestra el análisis de columnas temporales."""
    resultado = calidad["fechas"]

    print()
    print("12. ANÁLISIS DE FECHAS")
    print("-" * 60)

    if not resultado:
        print("No se han detectado columnas de fecha.")
        return

    for columna, detalle in resultado.items():
        tipo_temporal = (
            "Fecha y hora"
            if detalle["tipo_temporal"] == "fecha_hora"
            else "Fecha"
        )

        print(f"{columna}:")
        print(f"  - Tipo temporal: {tipo_temporal}")
        print(
            "  - Valores válidos: "
            f"{_formatear_entero(detalle['valores_validos'])}"
        )
        print(
            "  - Valores nulos: "
            f"{_formatear_entero(detalle['valores_nulos'])}"
        )
        print(
            "  - Posibles nulos textuales: "
            f"{_formatear_entero(detalle['nulos_textuales'])}"
        )
        print(
            "  - Conversiones fallidas: "
            f"{_formatear_entero(
                detalle['conversiones_fallidas']
            )}"
        )
        print(
            "  - Porcentaje de conversión: "
            f"{_formatear_porcentaje(
                detalle['porcentaje_conversion']
            )}"
        )
        print(
            "  - Fecha mínima: "
            f"{detalle['fecha_minima']}"
        )
        print(
            "  - Fecha máxima: "
            f"{detalle['fecha_maxima']}"
        )



def mostrar_incompatibilidades_semanticas(calidad: dict) -> None:
    """Muestra incompatibilidades con los tipos semánticos asignados."""
    resultado = calidad["incompatibilidades_tipo"]

    print()
    print("13. INCOMPATIBILIDADES DE TIPO SEMÁNTICO")
    print("-" * 60)

    if not resultado:
        print("No se han detectado incompatibilidades semánticas.")
        return

    etiquetas_tipos = {
        "numerico": "Numérico",
        "fecha": "Fecha",
        "fecha_hora": "Fecha y hora",
        "booleano_binario": "Booleano/binario",
        "categorico": "Categórico",
        "identificador": "Identificador",
        "texto_libre": "Texto libre",
    }

    for columna, detalle in resultado.items():
        tipo = detalle["tipo_semantico"]

        print(f"{columna}:")
        print(
            "  - Tipo semántico: "
            f"{etiquetas_tipos.get(tipo, tipo)}"
        )
        print(
            "  - Valores evaluados: "
            f"{_formatear_entero(detalle['valores_evaluados'])}"
        )
        print(
            "  - Valores incompatibles: "
            f"{_formatear_entero(detalle['valores_incompatibles'])}"
        )
        print(
            "  - Porcentaje: "
            f"{_formatear_porcentaje(detalle['porcentaje_incompatibles'])}"
        )


def mostrar_reglas_negocio(calidad: dict) -> None:
    """Muestra los incumplimientos de reglas de negocio ya calculados."""
    resultado = calidad["reglas_negocio"]

    print()
    print("14. REGLAS DE NEGOCIO")
    print("-" * 60)

    if not resultado:
        print("No se han detectado incumplimientos de reglas de negocio.")
        return

    for columna, reglas in resultado.items():
        print(f"{columna}:")

        for nombre_regla, detalle in reglas.items():
            regla = detalle.get("regla", nombre_regla)
            print(f"  - Regla: {regla}")

            if "valor_configurado" in detalle:
                print(
                    "    Valor configurado: "
                    f"{detalle['valor_configurado']}"
                )

            print(
                "    Valores evaluados: "
                f"{_formatear_entero(detalle['valores_evaluados'])}"
            )
            print(
                "    Valores incumplidos: "
                f"{_formatear_entero(detalle['valores_incumplidos'])}"
            )
            print(
                "    Porcentaje: "
                f"{_formatear_porcentaje(
                    detalle['porcentaje_incumplimiento']
                )}"
            )

def mostrar_incidencias(incidencias: list[dict]) -> None:
    """Muestra las incidencias estructuradas de la auditoría."""
    print()
    print("15. INCIDENCIAS DETECTADAS")
    print("-" * 60)

    if not incidencias:
        print("No se han detectado incidencias de calidad.")
        return

    for incidencia in incidencias:
        severidad = incidencia["severidad"].upper()
        categoria = incidencia["categoria"].capitalize()

        print(
            f"[{severidad}] [{categoria}] "
            f"{incidencia['mensaje']}"
        )


def generar_informe(
    resultado_auditoria: dict,
    *,
    resultado_reauditoria=None,
    manifiesto_reproducibilidad=None,
    verificacion_reproducibilidad=None,
) -> None:
    """Genera el informe completo de auditoría en consola."""
    dataset = resultado_auditoria["dataset"]
    perfil = resultado_auditoria["perfil"]
    calidad = resultado_auditoria["calidad"]
    tipos_semanticos = resultado_auditoria["tipos_semanticos"]
    incidencias = resultado_auditoria["incidencias"]
    resumen = resultado_auditoria["resumen"]

    print()
    print("=" * 60)
    print("DATAQUALITYPY - INFORME DE CALIDAD DE DATOS")
    print("=" * 60)

    mostrar_resumen_ejecutivo(
        dataset,
        resumen,
    )
    mostrar_resumen(
        dataset,
        perfil,
    )
    mostrar_tipos(perfil, tipos_semanticos)
    mostrar_nulos(calidad)
    mostrar_nulos_textuales(calidad)
    mostrar_identificadores(calidad)
    mostrar_duplicados(calidad)
    mostrar_duplicados_clave(calidad)
    mostrar_columnas_problematicas(calidad)
    mostrar_estadisticas_numericas(perfil)
    mostrar_texto(calidad)
    mostrar_outliers(calidad)
    mostrar_fechas(calidad)
    mostrar_incompatibilidades_semanticas(calidad)
    mostrar_reglas_negocio(calidad)
    mostrar_incidencias(incidencias)

    from src.report_v7 import (
        mostrar_analisis_avanzado,
        mostrar_reauditoria,
        mostrar_reproducibilidad,
    )

    mostrar_analisis_avanzado(
        resultado_auditoria.get("analisis_avanzado")
    )
    mostrar_reauditoria(resultado_reauditoria)
    mostrar_reproducibilidad(
        manifiesto_reproducibilidad,
        verificacion_reproducibilidad,
    )

    print()
    print("=" * 60)
    print("FIN DEL INFORME")
    print("=" * 60)