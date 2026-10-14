"""Funciones para analizar la calidad de los datasets."""

import re
import unicodedata

import pandas as pd

MARCADORES_NULOS_TEXTUALES = {
    "n/a",
    "na",
    "null",
    "none",
    "-",
}

TERMINOS_IDENTIFICADOR = {
    "id",
    "codigo",
    "cod",
    "numero",
    "num",
    "referencia",
    "ref",
}


def es_nulo_textual(valor: object) -> bool:
    """Indica si un valor representa un posible nulo como texto."""
    if not isinstance(valor, str):
        return False

    valor_limpio = valor.strip()

    if valor_limpio == "":
        return True

    return valor_limpio.lower() in MARCADORES_NULOS_TEXTUALES


def nombre_indica_identificador(nombre_columna: object) -> bool:
    """Indica si el nombre de una columna sugiere un identificador."""
    nombre = str(nombre_columna).strip()

    nombre_separado = re.sub(
        r"(?<=[a-záéíóúüñ0-9])(?=[A-ZÁÉÍÓÚÜÑ])",
        " ",
        nombre,
    ).lower()

    componentes = [
        componente
        for componente in re.split(r"[\s_-]+", nombre_separado)
        if componente
    ]

    return any(
        componente in TERMINOS_IDENTIFICADOR
        for componente in componentes
    )


def _normalizar_categoria(valor: str) -> str:
    """Normaliza un texto para comparar posibles variantes categóricas."""
    valor_limpio = valor.strip().lower()

    valor_descompuesto = unicodedata.normalize(
        "NFKD",
        valor_limpio,
    )

    return "".join(
        caracter
        for caracter in valor_descompuesto
        if not unicodedata.combining(caracter)
    )


def _detectar_inconsistencias_categoricas(
    serie: pd.Series,
) -> list[dict]:
    """Agrupa variantes textuales que podrían representar una categoría."""
    grupos = {}

    for valor in serie:
        valor_original = str(valor)

        if es_nulo_textual(valor_original):
            continue

        valor_normalizado = _normalizar_categoria(valor_original)

        if valor_normalizado not in grupos:
            grupos[valor_normalizado] = {}

        variantes = grupos[valor_normalizado]

        variantes[valor_original] = (
            variantes.get(valor_original, 0) + 1
        )

    grupos_inconsistentes = []

    for valor_normalizado, variantes in grupos.items():
        if len(variantes) < 2:
            continue

        grupos_inconsistentes.append(
            {
                "valor_normalizado": valor_normalizado,
                "variantes": variantes,
                "cantidad_variantes": len(variantes),
            }
        )

    return grupos_inconsistentes


def _texto_contiene_hora(valor: object) -> bool:
    """Indica si un texto de fecha contiene un componente horario."""
    if not isinstance(valor, str):
        return False

    valor_limpio = valor.strip()

    patron_hora = re.compile(
        r"(?:^|\s|T)"
        r"\d{1,2}:\d{2}"
        r"(?::\d{2}(?:[.,]\d+)?)?"
        r"(?:\s*[APap][Mm])?"
        r"(?:\s*(?:Z|[+-]\d{2}:?\d{2}))?"
        r"(?:$|\s)"
    )

    return bool(patron_hora.search(valor_limpio))


def analizar_nulos(datos: pd.DataFrame) -> dict:
    """Analiza los valores nulos del dataset."""
    total_filas = len(datos)
    por_columna = {}

    for columna in datos.columns:
        nulos = int(datos[columna].isna().sum())

        porcentaje_nulos = (
            (nulos / total_filas) * 100
            if total_filas > 0
            else 0.0
        )

        por_columna[columna] = {
            "nulos": nulos,
            "porcentaje_nulos": float(porcentaje_nulos),
        }

    total_nulos = int(datos.isna().sum().sum())

    columnas_con_nulos = sum(
        1
        for resultado in por_columna.values()
        if resultado["nulos"] > 0
    )

    return {
        "total_nulos": total_nulos,
        "columnas_con_nulos": columnas_con_nulos,
        "por_columna": por_columna,
    }


def analizar_nulos_textuales(datos: pd.DataFrame) -> dict:
    """Detecta posibles valores ausentes conservados como texto."""
    resultado = {}

    columnas_texto = datos.select_dtypes(include=["object", "string"])

    for columna in columnas_texto.columns:
        serie = columnas_texto[columna].dropna().astype(str)

        if serie.empty:
            continue

        marcadores_detectados = {}

        for valor in serie:
            if not es_nulo_textual(valor):
                continue

            valor_limpio = valor.strip()
            valor_normalizado = valor_limpio.lower()

            if valor_limpio == "":
                marcador = "espacios_en_blanco"
            else:
                marcador = valor_normalizado

            marcadores_detectados[marcador] = (
                marcadores_detectados.get(marcador, 0) + 1
            )

        total_posibles = sum(marcadores_detectados.values())

        if total_posibles == 0:
            continue

        porcentaje_posibles = (
            (total_posibles / len(datos)) * 100
            if len(datos) > 0
            else 0.0
        )

        resultado[columna] = {
            "total_posibles_nulos_textuales": total_posibles,
            "porcentaje_posibles_nulos_textuales": float(
                porcentaje_posibles
            ),
            "marcadores_detectados": marcadores_detectados,
        }

    return resultado


def analizar_identificadores(
    datos: pd.DataFrame,
    umbral_unicidad: float = 90,
) -> dict:
    """Detecta columnas que podrían funcionar como identificadores."""
    resultado = {}

    for columna in datos.columns:
        nombre_indicativo = nombre_indica_identificador(columna)

        if not nombre_indicativo:
            continue

        serie = datos[columna].dropna()

        if pd.api.types.is_object_dtype(
            serie
        ) or isinstance(serie.dtype, pd.StringDtype):
            mascara_valida = ~serie.map(es_nulo_textual)
            serie = serie[mascara_valida]

        valores_no_nulos = len(serie)

        if valores_no_nulos == 0:
            valores_distintos = 0
            porcentaje_unicidad = 0.0
        else:
            valores_distintos = int(serie.nunique())
            porcentaje_unicidad = (
                valores_distintos / valores_no_nulos
            ) * 100

        posible_identificador = (
            valores_no_nulos > 0
            and porcentaje_unicidad >= umbral_unicidad
        )

        resultado[columna] = {
            "posible_identificador": bool(
                posible_identificador
            ),
            "valores_no_nulos": valores_no_nulos,
            "valores_distintos": valores_distintos,
            "porcentaje_unicidad": float(
                porcentaje_unicidad
            ),
            "nombre_indicativo": nombre_indicativo,
        }

    return resultado


def analizar_duplicados(datos: pd.DataFrame) -> dict:
    """Analiza las filas duplicadas del dataset."""
    total_filas = len(datos)
    filas_duplicadas = int(datos.duplicated().sum())

    porcentaje_duplicados = (
        (filas_duplicadas / total_filas) * 100
        if total_filas > 0
        else 0.0
    )

    return {
        "filas_duplicadas": filas_duplicadas,
        "porcentaje_duplicados": float(porcentaje_duplicados),
    }


def analizar_duplicados_clave(
    datos: pd.DataFrame,
    columnas_clave: list[str],
) -> dict:
    """Analiza duplicados según una clave simple o compuesta."""
    resultado = {
        "columnas_clave": columnas_clave.copy(),
        "clave_configurada": bool(columnas_clave),
        "columnas_inexistentes": [],
        "registros_validos": 0,
        "registros_excluidos": 0,
        "registros_con_clave_duplicada": 0,
        "valores_clave_duplicados": 0,
        "porcentaje_registros_duplicados": 0.0,
    }

    if not columnas_clave:
        return resultado

    columnas_inexistentes = [
        columna
        for columna in columnas_clave
        if columna not in datos.columns
    ]

    if columnas_inexistentes:
        resultado["columnas_inexistentes"] = columnas_inexistentes
        return resultado

    datos_clave = datos[columnas_clave].copy()

    mascara_excluidos = datos_clave.isna().any(axis=1)

    for columna in columnas_clave:
        serie = datos_clave[columna]

        if pd.api.types.is_object_dtype(
            serie
        ) or isinstance(serie.dtype, pd.StringDtype):
            mascara_excluidos = (
                mascara_excluidos
                | serie.map(es_nulo_textual)
            )

    datos_validos = datos_clave.loc[~mascara_excluidos]

    registros_validos = len(datos_validos)
    registros_excluidos = int(mascara_excluidos.sum())

    resultado["registros_validos"] = registros_validos
    resultado["registros_excluidos"] = registros_excluidos

    if registros_validos == 0:
        return resultado

    mascara_duplicados = datos_validos.duplicated(
        subset=columnas_clave,
        keep=False,
    )

    registros_con_clave_duplicada = int(
        mascara_duplicados.sum()
    )

    if registros_con_clave_duplicada > 0:
        claves_duplicadas = (
            datos_validos.loc[mascara_duplicados, columnas_clave]
            .drop_duplicates()
        )

        valores_clave_duplicados = len(claves_duplicadas)
    else:
        valores_clave_duplicados = 0

    porcentaje_registros_duplicados = (
        registros_con_clave_duplicada
        / registros_validos
    ) * 100

    resultado.update(
        {
            "registros_con_clave_duplicada": (
                registros_con_clave_duplicada
            ),
            "valores_clave_duplicados": (
                valores_clave_duplicados
            ),
            "porcentaje_registros_duplicados": float(
                porcentaje_registros_duplicados
            ),
        }
    )

    return resultado


def analizar_columnas_problematicas(datos: pd.DataFrame) -> dict:
    """Detecta columnas completamente vacías y columnas constantes."""
    columnas_vacias = []
    columnas_constantes = []

    for columna in datos.columns:
        serie = datos[columna]

        if serie.isna().all():
            columnas_vacias.append(columna)
        elif serie.nunique(dropna=True) == 1:
            columnas_constantes.append(columna)

    return {
        "columnas_vacias": columnas_vacias,
        "columnas_constantes": columnas_constantes,
    }


def analizar_texto(
    datos: pd.DataFrame,
    max_categorias: int = 20,
    max_porcentaje_categorias: float = 20,
) -> dict:
    """Analiza posibles problemas de calidad en columnas de texto."""
    resultado = {}

    columnas_texto = datos.select_dtypes(include=["object", "string"])

    for columna in columnas_texto.columns:
        serie = columnas_texto[columna].dropna().astype(str)

        valores_con_espacios = int(
            serie.ne(serie.str.strip()).sum()
        )

        valores_unicos = serie.unique()
        valores_normalizados_mayusculas = (
            serie.str.lower().unique()
        )

        posibles_diferencias_mayusculas = (
            len(valores_normalizados_mayusculas)
            < len(valores_unicos)
        )

        serie_valida = serie[
            ~serie.map(es_nulo_textual)
        ]

        valores_distintos = int(serie_valida.nunique())
        total_valores = len(serie_valida)

        porcentaje_distintos = (
            (valores_distintos / total_valores) * 100
            if total_valores > 0
            else 0.0
        )

        baja_cardinalidad = (
            valores_distintos <= max_categorias
            and porcentaje_distintos <= max_porcentaje_categorias
        )

        grupos_inconsistentes = (
            _detectar_inconsistencias_categoricas(serie)
        )

        resultado[columna] = {
            "valores_con_espacios": valores_con_espacios,
            "posibles_diferencias_mayusculas": bool(
                posibles_diferencias_mayusculas
            ),
            "baja_cardinalidad": bool(baja_cardinalidad),
            "grupos_inconsistentes": grupos_inconsistentes,
        }

    return resultado


def _calcular_outliers_iqr(
    serie: pd.Series,
    factor_iqr: float,
) -> dict | None:
    """Calcula posibles valores atípicos de una serie numérica mediante IQR."""
    serie_limpia = serie.dropna()

    if serie_limpia.empty:
        return None

    q1 = float(serie_limpia.quantile(0.25))
    q3 = float(serie_limpia.quantile(0.75))
    iqr = q3 - q1

    limite_inferior = q1 - (factor_iqr * iqr)
    limite_superior = q3 + (factor_iqr * iqr)

    if iqr == 0:
        cantidad_outliers = 0
    else:
        mascara_outliers = (
            (serie_limpia < limite_inferior)
            | (serie_limpia > limite_superior)
        )
        cantidad_outliers = int(mascara_outliers.sum())

    total_valores = len(serie_limpia)

    porcentaje_outliers = (
        (cantidad_outliers / total_valores) * 100
        if total_valores > 0
        else 0.0
    )

    return {
        "q1": q1,
        "q3": q3,
        "iqr": float(iqr),
        "limite_inferior": float(limite_inferior),
        "limite_superior": float(limite_superior),
        "cantidad_outliers": cantidad_outliers,
        "porcentaje_outliers": float(porcentaje_outliers),
    }


def analizar_outliers(
    datos: pd.DataFrame,
    factor_iqr: float = 1.5,
) -> dict:
    """Detecta outliers en columnas numéricas físicas mediante IQR."""
    resultado = {}

    columnas_numericas = datos.select_dtypes(include="number")

    for columna in columnas_numericas.columns:
        analisis = _calcular_outliers_iqr(
            columnas_numericas[columna],
            factor_iqr,
        )

        if analisis is not None:
            resultado[columna] = analisis

    return resultado


def analizar_fechas(
    datos: pd.DataFrame,
    umbral_fecha: float = 80,
) -> dict:
    """Detecta y analiza columnas que contienen fechas o fecha y hora."""
    resultado = {}

    for columna in datos.columns:
        serie_original = datos[columna]
        valores_nulos = int(serie_original.isna().sum())

        if pd.api.types.is_datetime64_any_dtype(serie_original):
            serie_fechas = serie_original.dropna()

            if serie_fechas.empty:
                continue

            valores_validos = len(serie_fechas)
            nulos_textuales = 0
            conversiones_fallidas = 0
            porcentaje_conversion = 100.0

            contiene_hora = bool(
                (
                    (serie_fechas.dt.hour != 0)
                    | (serie_fechas.dt.minute != 0)
                    | (serie_fechas.dt.second != 0)
                    | (serie_fechas.dt.microsecond != 0)
                ).any()
            )

        elif pd.api.types.is_object_dtype(
            serie_original
        ) or isinstance(serie_original.dtype, pd.StringDtype):
            serie_no_nula = serie_original.dropna()

            if serie_no_nula.empty:
                continue

            mascara_nulos_textuales = serie_no_nula.map(
                es_nulo_textual
            )

            nulos_textuales = int(
                mascara_nulos_textuales.sum()
            )

            serie_evaluable = serie_no_nula.loc[
                ~mascara_nulos_textuales
            ]

            if serie_evaluable.empty:
                continue

            serie_convertida = pd.to_datetime(
                serie_evaluable,
                format="mixed",
                errors="coerce",
                dayfirst=True,
            )

            valores_validos = int(
                serie_convertida.notna().sum()
            )
            conversiones_fallidas = int(
                serie_convertida.isna().sum()
            )

            total_evaluable = len(serie_evaluable)

            porcentaje_conversion = (
                (valores_validos / total_evaluable) * 100
                if total_evaluable > 0
                else 0.0
            )

            if porcentaje_conversion < umbral_fecha:
                continue

            serie_fechas = serie_convertida.dropna()

            if serie_fechas.empty:
                continue

            valores_originales_validos = serie_evaluable.loc[
                serie_convertida.notna()
            ]

            contiene_hora = bool(
                valores_originales_validos.map(
                    _texto_contiene_hora
                ).any()
            )

        else:
            continue

        tipo_temporal = (
            "fecha_hora"
            if contiene_hora
            else "fecha"
        )

        fecha_minima = serie_fechas.min()
        fecha_maxima = serie_fechas.max()

        formato_salida = (
            "%Y-%m-%d %H:%M:%S"
            if tipo_temporal == "fecha_hora"
            else "%Y-%m-%d"
        )

        resultado[columna] = {
            "tipo_temporal": tipo_temporal,
            "valores_validos": int(valores_validos),
            "valores_nulos": valores_nulos,
            "nulos_textuales": int(nulos_textuales),
            "conversiones_fallidas": int(
                conversiones_fallidas
            ),
            "porcentaje_conversion": float(
                porcentaje_conversion
            ),
            "fecha_minima": fecha_minima.strftime(
                formato_salida
            ),
            "fecha_maxima": fecha_maxima.strftime(
                formato_salida
            ),
        }

    return resultado
