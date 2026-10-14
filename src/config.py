"""Gestión de la configuración de DataQualityPy."""

import json
from pathlib import Path
from typing import Any


class ErrorConfiguracion(Exception):
    """Error producido al cargar o validar la configuración."""


CONFIGURACION_PREDETERMINADA = {
    "factor_iqr": 1.5,
    "umbral_fecha": 80,
    "max_categorias": 20,
    "max_porcentaje_categorias": 20,
    "umbral_identificador": 90,
    "columnas_clave": [],
    "tipos_columnas": {},
    "reglas_columnas": {},
}


def _es_numero(valor: Any) -> bool:
    """Indica si un valor es numérico, excluyendo booleanos."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _validar_columnas_clave(columnas_clave: Any) -> None:
    """Valida la configuración de las columnas utilizadas como clave."""
    if not isinstance(columnas_clave, list):
        raise ErrorConfiguracion(
            "El parámetro 'columnas_clave' debe ser una lista."
        )

    for columna in columnas_clave:
        if not isinstance(columna, str) or not columna.strip():
            raise ErrorConfiguracion(
                "El parámetro 'columnas_clave' debe contener "
                "únicamente nombres de columnas no vacíos."
            )

    if len(columnas_clave) != len(set(columnas_clave)):
        raise ErrorConfiguracion(
            "El parámetro 'columnas_clave' no puede contener "
            "nombres de columnas duplicados."
        )


TIPOS_SEMANTICOS_VALIDOS = {
    "numerico",
    "fecha",
    "fecha_hora",
    "booleano_binario",
    "categorico",
    "identificador",
    "texto_libre",
}


def _validar_tipos_columnas(tipos_columnas: Any) -> None:
    """Valida las declaraciones explícitas de tipos semánticos."""
    if not isinstance(tipos_columnas, dict):
        raise ErrorConfiguracion(
            "El parámetro 'tipos_columnas' debe ser un objeto."
        )

    for columna, tipo_semantico in tipos_columnas.items():
        if not isinstance(columna, str) or not columna.strip():
            raise ErrorConfiguracion(
                "El parámetro 'tipos_columnas' debe utilizar "
                "nombres de columnas no vacíos."
            )

        if not isinstance(tipo_semantico, str):
            raise ErrorConfiguracion(
                "Cada tipo declarado en 'tipos_columnas' debe ser "
                "una cadena de texto."
            )

        if tipo_semantico not in TIPOS_SEMANTICOS_VALIDOS:
            tipos_validos = ", ".join(sorted(TIPOS_SEMANTICOS_VALIDOS))
            raise ErrorConfiguracion(
                f"Tipo semántico no válido para la columna '{columna}': "
                f"'{tipo_semantico}'. Tipos admitidos: {tipos_validos}."
            )


REGLAS_COLUMNA_VALIDAS = {
    "min",
    "max",
    "valores_permitidos",
}


def _validar_reglas_columnas(reglas_columnas: Any) -> None:
    """Valida las reglas de negocio declaradas por columna."""
    if not isinstance(reglas_columnas, dict):
        raise ErrorConfiguracion(
            "El parámetro 'reglas_columnas' debe ser un objeto."
        )

    for columna, reglas in reglas_columnas.items():
        if not isinstance(columna, str) or not columna.strip():
            raise ErrorConfiguracion(
                "El parámetro 'reglas_columnas' debe utilizar "
                "nombres de columnas no vacíos."
            )

        if not isinstance(reglas, dict):
            raise ErrorConfiguracion(
                f"Reglas de la columna '{columna}' deben formar un objeto."
            )

        reglas_desconocidas = reglas.keys() - REGLAS_COLUMNA_VALIDAS

        if reglas_desconocidas:
            regla = sorted(reglas_desconocidas)[0]
            raise ErrorConfiguracion(
                f"Regla desconocida para la columna '{columna}': "
                f"'{regla}'."
            )

        if "min" in reglas and not _es_numero(reglas["min"]):
            raise ErrorConfiguracion(
                f"La regla 'min' de la columna '{columna}' "
                "debe tener un valor numérico."
            )

        if "max" in reglas and not _es_numero(reglas["max"]):
            raise ErrorConfiguracion(
                f"La regla 'max' de la columna '{columna}' "
                "debe tener un valor numérico."
            )

        if (
            "min" in reglas
            and "max" in reglas
            and reglas["min"] > reglas["max"]
        ):
            raise ErrorConfiguracion(
                f"La regla 'min' no puede ser mayor que la regla 'max' "
                f"en la columna '{columna}'."
            )

        if "valores_permitidos" in reglas:
            valores_permitidos = reglas["valores_permitidos"]

            if not isinstance(valores_permitidos, list):
                raise ErrorConfiguracion(
                    f"La regla 'valores_permitidos' de la columna "
                    f"'{columna}' debe ser una lista."
                )

            if not valores_permitidos:
                raise ErrorConfiguracion(
                    f"La regla 'valores_permitidos' de la columna "
                    f"'{columna}' no puede ser una lista vacía."
                )


def _validar_configuracion(configuracion: dict[str, Any]) -> None:
    """Valida los parámetros utilizados por el auditor."""
    factor_iqr = configuracion["factor_iqr"]

    if not _es_numero(factor_iqr) or factor_iqr <= 0:
        raise ErrorConfiguracion(
            "El parámetro 'factor_iqr' debe ser un número mayor que 0."
        )

    umbral_fecha = configuracion["umbral_fecha"]

    if (
        not _es_numero(umbral_fecha)
        or not 0 <= umbral_fecha <= 100
    ):
        raise ErrorConfiguracion(
            "El parámetro 'umbral_fecha' debe ser un número "
            "entre 0 y 100."
        )

    max_categorias = configuracion["max_categorias"]

    if (
        not isinstance(max_categorias, int)
        or isinstance(max_categorias, bool)
        or max_categorias < 1
    ):
        raise ErrorConfiguracion(
            "El parámetro 'max_categorias' debe ser "
            "un número entero mayor o igual que 1."
        )

    max_porcentaje = configuracion["max_porcentaje_categorias"]

    if (
        not _es_numero(max_porcentaje)
        or not 0 <= max_porcentaje <= 100
    ):
        raise ErrorConfiguracion(
            "El parámetro 'max_porcentaje_categorias' debe ser "
            "un número entre 0 y 100."
        )

    umbral_identificador = configuracion["umbral_identificador"]

    if (
        not _es_numero(umbral_identificador)
        or not 0 <= umbral_identificador <= 100
    ):
        raise ErrorConfiguracion(
            "El parámetro 'umbral_identificador' debe ser "
            "un número entre 0 y 100."
        )

    _validar_columnas_clave(
        configuracion["columnas_clave"]
    )

    _validar_tipos_columnas(
        configuracion["tipos_columnas"]
    )

    _validar_reglas_columnas(
        configuracion["reglas_columnas"]
    )


def cargar_configuracion(
    ruta_configuracion: str | Path | None = None,
    configuracion_usuario: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Carga y valida la configuración del auditor."""
    configuracion = CONFIGURACION_PREDETERMINADA.copy()

    if (
        ruta_configuracion is not None
        and configuracion_usuario is not None
    ):
        raise ErrorConfiguracion(
            "No se puede indicar simultáneamente una ruta de configuración "
            "y una configuración en memoria."
        )

    if ruta_configuracion is not None:
        ruta = Path(ruta_configuracion)

        if not ruta.is_file():
            raise ErrorConfiguracion(
                f"No se ha encontrado el archivo de configuración: '{ruta}'."
            )

        try:
            with ruta.open("r", encoding="utf-8") as archivo:
                configuracion_usuario = json.load(archivo)

        except json.JSONDecodeError as error:
            raise ErrorConfiguracion(
                f"El archivo de configuración '{ruta}' "
                "no contiene un JSON válido."
            ) from error

        except (OSError, UnicodeDecodeError) as error:
            raise ErrorConfiguracion(
                f"No se ha podido leer el archivo de configuración '{ruta}'."
            ) from error

    if configuracion_usuario is None:
        return configuracion

    if not isinstance(configuracion_usuario, dict):
        raise ErrorConfiguracion(
            "La configuración debe ser un objeto "
            "formado por pares de parámetro y valor."
        )

    parametros_desconocidos = (
        configuracion_usuario.keys()
        - CONFIGURACION_PREDETERMINADA.keys()
    )

    if parametros_desconocidos:
        parametros = ", ".join(
            sorted(parametros_desconocidos)
        )

        raise ErrorConfiguracion(
            "Se han encontrado parámetros de configuración "
            f"desconocidos: {parametros}."
        )

    configuracion.update(configuracion_usuario)

    _validar_configuracion(configuracion)

    return configuracion
