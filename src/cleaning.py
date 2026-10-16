"""
DataQualityPy - Motor de limpieza controlada.

Ejecuta un CleaningPlan sobre una COPIA del DataFrame recibido.
Nunca modifica el DataFrame original.

El módulo no depende de Streamlit. Devuelve el DataFrame limpio junto con
un resultado estructurado de ejecución que podrá utilizarse posteriormente
para trazabilidad, informes y comparación antes/después.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.cleaning_plan import (
    CleaningOperation,
    CleaningPlan,
    CleaningPlanError,
)


class CleaningError(RuntimeError):
    """Error durante la ejecución controlada de una limpieza."""


@dataclass
class CleaningExecution:
    """Resultado real de la ejecución de una operación."""

    operacion_id: str
    familia: str
    tipo: str
    columna: str | None
    parametros: dict[str, Any]
    estado: str
    registros_afectados: int = 0
    filas_antes: int = 0
    filas_despues: int = 0
    advertencias: list[str] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CleaningResult:
    """Resumen estructurado de una ejecución completa."""

    filas_antes: int
    columnas_antes: int
    filas_despues: int
    columnas_despues: int
    operaciones_solicitadas: int
    operaciones_ejecutadas: int
    ejecuciones: list[CleaningExecution] = field(default_factory=list)

    def a_dict(self) -> dict[str, Any]:
        return {
            "filas_antes": self.filas_antes,
            "columnas_antes": self.columnas_antes,
            "filas_despues": self.filas_despues,
            "columnas_despues": self.columnas_despues,
            "operaciones_solicitadas": self.operaciones_solicitadas,
            "operaciones_ejecutadas": self.operaciones_ejecutadas,
            "ejecuciones": [
                ejecucion.a_dict()
                for ejecucion in self.ejecuciones
            ],
        }


def _validar_columna(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> None:
    if operacion.columna is None:
        return

    if operacion.columna not in dataframe.columns:
        raise CleaningError(
            f"La columna '{operacion.columna}' no existe en el dataset."
        )


def _mascara_cambio(
    antes: pd.Series,
    despues: pd.Series,
) -> pd.Series:
    """
    Devuelve una máscara de posiciones cuyo valor cambió.

    Considera equivalentes dos valores nulos.
    """
    ambos_nulos = antes.isna() & despues.isna()
    iguales = antes.eq(despues).fillna(False)
    return ~(ambos_nulos | iguales)


def _serie_texto_preservando_nulos(serie: pd.Series) -> pd.Series:
    """Convierte valores no nulos a texto conservando los nulos reales."""
    resultado = serie.copy()
    mascara = resultado.notna()
    resultado.loc[mascara] = resultado.loc[mascara].astype(str)
    return resultado


def _ejecutar_texto(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> int:
    columna = operacion.columna
    if columna is None:
        raise CleaningError("La operación de texto requiere una columna.")

    antes = dataframe[columna].copy()
    despues = _serie_texto_preservando_nulos(antes)

    mascara = despues.notna()

    if operacion.tipo == "eliminar_espacios_externos":
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.strip()
        )

    elif operacion.tipo == "normalizar_espacios_internos":
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.replace(r"\s+", " ", regex=True)
        )

    elif operacion.tipo == "minusculas":
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.lower()
        )

    elif operacion.tipo == "mayusculas":
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.upper()
        )

    elif operacion.tipo == "capitalizar":
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.capitalize()
        )

    elif operacion.tipo == "titulo":
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.title()
        )

    elif operacion.tipo == "eliminar_tildes":
        traduccion_tildes = str.maketrans(
            "áéíóúÁÉÍÓÚ",
            "aeiouAEIOU",
        )
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.translate(traduccion_tildes)
        )

    elif operacion.tipo == "sustituir_caracteres":
        origen = operacion.parametros["origen"]
        destino = operacion.parametros["destino"]
        despues.loc[mascara] = (
            despues.loc[mascara]
            .astype(str)
            .str.replace(origen, destino, regex=False)
        )

    else:
        raise CleaningError(
            f"Operación de texto no soportada: '{operacion.tipo}'."
        )

    cambios = _mascara_cambio(antes, despues)
    dataframe[columna] = despues
    return int(cambios.sum())


def _mascara_valor(
    serie: pd.Series,
    valor: Any,
) -> pd.Series:
    if pd.isna(valor):
        return serie.isna()

    try:
        return serie.eq(valor).fillna(False)
    except (TypeError, ValueError):
        return pd.Series(False, index=serie.index)


def _ejecutar_sustitucion(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> int:
    columna = operacion.columna
    if columna is None:
        raise CleaningError("La sustitución requiere una columna.")

    origen = operacion.parametros["origen"]
    mascara = _mascara_valor(dataframe[columna], origen)
    afectados = int(mascara.sum())

    if afectados == 0:
        return 0

    if operacion.tipo == "reemplazar_valor":
        destino = operacion.parametros["destino"]
        dataframe.loc[mascara, columna] = destino

    elif operacion.tipo == "reemplazar_por_nulo":
        dataframe.loc[mascara, columna] = pd.NA

    else:
        raise CleaningError(
            f"Operación de sustitución no soportada: '{operacion.tipo}'."
        )

    return afectados


def _conversion_numerica(
    serie: pd.Series,
    permitir_incompatibles_a_nulo: bool,
) -> tuple[pd.Series, list[str]]:
    convertida = pd.to_numeric(serie, errors="coerce")
    incompatibles = serie.notna() & convertida.isna()
    cantidad = int(incompatibles.sum())

    if cantidad and not permitir_incompatibles_a_nulo:
        valores = (
            serie.loc[incompatibles]
            .astype(str)
            .drop_duplicates()
            .head(10)
            .tolist()
        )
        raise CleaningError(
            "La conversión a numérico contiene "
            f"{cantidad} valor(es) incompatible(s). "
            f"Ejemplos: {valores}. "
            "Resuelve esos valores previamente o autoriza explícitamente "
            "su conversión a nulo."
        )

    advertencias: list[str] = []
    if cantidad:
        advertencias.append(
            f"{cantidad} valor(es) incompatible(s) se convirtieron "
            "explícitamente a nulo."
        )

    return convertida, advertencias


def _conversion_fecha(
    serie: pd.Series,
    formato: str | None,
    permitir_incompatibles_a_nulo: bool,
) -> tuple[pd.Series, list[str]]:
    kwargs: dict[str, Any] = {"errors": "coerce"}

    if formato:
        kwargs["format"] = formato

    convertida = pd.to_datetime(serie, **kwargs)
    incompatibles = serie.notna() & convertida.isna()
    cantidad = int(incompatibles.sum())

    if cantidad and not permitir_incompatibles_a_nulo:
        valores = (
            serie.loc[incompatibles]
            .astype(str)
            .drop_duplicates()
            .head(10)
            .tolist()
        )
        raise CleaningError(
            "La conversión de fecha contiene "
            f"{cantidad} valor(es) incompatible(s). "
            f"Ejemplos: {valores}. "
            "Resuelve esos valores previamente o autoriza explícitamente "
            "su conversión a nulo."
        )

    advertencias: list[str] = []
    if cantidad:
        advertencias.append(
            f"{cantidad} valor(es) incompatible(s) se convirtieron "
            "explícitamente a nulo."
        )

    return convertida, advertencias


def _conversion_texto(
    serie: pd.Series,
) -> tuple[pd.Series, list[str]]:
    convertida = serie.astype("string")
    return convertida, []


def _conversion_booleana(
    serie: pd.Series,
    mapeo: dict[Any, Any] | None,
    permitir_incompatibles_a_nulo: bool,
) -> tuple[pd.Series, list[str]]:
    if mapeo:
        temporal = serie.map(
            lambda valor: mapeo.get(valor, valor)
            if not pd.isna(valor)
            else valor
        )
    else:
        temporal = serie.copy()

    verdaderos = {True, 1, "1", "true", "True", "TRUE"}
    falsos = {False, 0, "0", "false", "False", "FALSE"}

    def convertir(valor: Any) -> Any:
        if pd.isna(valor):
            return pd.NA
        if valor in verdaderos:
            return True
        if valor in falsos:
            return False
        return pd.NA

    convertida = temporal.map(convertir).astype("boolean")
    incompatibles = temporal.notna() & convertida.isna()
    cantidad = int(incompatibles.sum())

    if cantidad and not permitir_incompatibles_a_nulo:
        valores = (
            temporal.loc[incompatibles]
            .astype(str)
            .drop_duplicates()
            .head(10)
            .tolist()
        )
        raise CleaningError(
            "La conversión a booleano contiene "
            f"{cantidad} valor(es) incompatible(s). "
            f"Ejemplos: {valores}. "
            "Define un mapeo explícito o autoriza su conversión a nulo."
        )

    advertencias: list[str] = []
    if cantidad:
        advertencias.append(
            f"{cantidad} valor(es) incompatible(s) se convirtieron "
            "explícitamente a nulo."
        )

    return convertida, advertencias


def _ejecutar_conversion(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> tuple[int, list[str]]:
    columna = operacion.columna
    if columna is None:
        raise CleaningError("La conversión requiere una columna.")

    antes = dataframe[columna].copy()
    permitir_nulo = bool(
        operacion.parametros.get(
            "incompatibles_a_nulo",
            False,
        )
    )

    if operacion.tipo == "numerico":
        despues, advertencias = _conversion_numerica(
            antes,
            permitir_nulo,
        )

    elif operacion.tipo in {"fecha", "fecha_hora"}:
        formato = operacion.parametros.get("formato")
        despues, advertencias = _conversion_fecha(
            antes,
            formato,
            permitir_nulo,
        )

        if operacion.tipo == "fecha":
            # Se conserva dtype datetime64 para mantener operaciones
            # vectorizadas y compatibilidad con pandas.
            despues = despues.dt.normalize()

    elif operacion.tipo == "texto":
        despues, advertencias = _conversion_texto(antes)

    elif operacion.tipo == "booleano":
        despues, advertencias = _conversion_booleana(
            antes,
            operacion.parametros.get("mapeo"),
            permitir_nulo,
        )

    else:
        raise CleaningError(
            f"Conversión no soportada: '{operacion.tipo}'."
        )

    cambios = _mascara_cambio(antes, despues)
    dataframe[columna] = despues
    return int(cambios.sum()), advertencias


def _ejecutar_nulos(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> int:
    columna = operacion.columna
    if columna is None:
        raise CleaningError("El tratamiento de nulos requiere una columna.")

    mascara = dataframe[columna].isna()
    cantidad_nulos = int(mascara.sum())

    if cantidad_nulos == 0:
        return 0

    if operacion.tipo == "eliminar_filas":
        dataframe.drop(
            index=dataframe.index[mascara],
            inplace=True,
        )
        return cantidad_nulos

    if operacion.tipo == "reemplazar_valor":
        dataframe.loc[mascara, columna] = operacion.parametros["valor"]
        return cantidad_nulos

    serie_no_nula = dataframe.loc[~mascara, columna]

    if operacion.tipo == "media":
        numerica = pd.to_numeric(serie_no_nula, errors="coerce")
        if numerica.notna().sum() != len(serie_no_nula):
            raise CleaningError(
                f"No puede calcularse la media de '{columna}' porque "
                "contiene valores no numéricos."
            )
        if numerica.empty:
            raise CleaningError(
                f"No puede calcularse la media de '{columna}' "
                "porque no hay valores disponibles."
            )
        valor = numerica.mean()

    elif operacion.tipo == "mediana":
        numerica = pd.to_numeric(serie_no_nula, errors="coerce")
        if numerica.notna().sum() != len(serie_no_nula):
            raise CleaningError(
                f"No puede calcularse la mediana de '{columna}' porque "
                "contiene valores no numéricos."
            )
        if numerica.empty:
            raise CleaningError(
                f"No puede calcularse la mediana de '{columna}' "
                "porque no hay valores disponibles."
            )
        valor = numerica.median()

    elif operacion.tipo == "moda":
        moda = serie_no_nula.mode(dropna=True)
        if moda.empty:
            raise CleaningError(
                f"No puede calcularse la moda de '{columna}' "
                "porque no hay valores disponibles."
            )
        valor = moda.iloc[0]

    else:
        raise CleaningError(
            f"Tratamiento de nulos no soportado: '{operacion.tipo}'."
        )

    dataframe.loc[mascara, columna] = valor
    return cantidad_nulos


def _ejecutar_outliers(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> int:
    columna = operacion.columna
    if columna is None:
        raise CleaningError("La eliminación de outliers requiere una columna.")

    serie = pd.to_numeric(dataframe[columna], errors="coerce")
    valores_validos = serie.dropna()

    if valores_validos.empty:
        return 0

    factor_iqr = operacion.parametros.get("factor_iqr", 1.5)
    try:
        factor_iqr = float(factor_iqr)
    except (TypeError, ValueError) as exc:
        raise CleaningError(
            "'factor_iqr' debe ser un valor numérico."
        ) from exc

    if factor_iqr <= 0:
        raise CleaningError("'factor_iqr' debe ser mayor que cero.")

    q1 = valores_validos.quantile(0.25)
    q3 = valores_validos.quantile(0.75)
    iqr = q3 - q1

    limite_inferior = q1 - factor_iqr * iqr
    limite_superior = q3 + factor_iqr * iqr

    mascara = serie.notna() & (
        (serie < limite_inferior)
        | (serie > limite_superior)
    )
    cantidad = int(mascara.sum())

    if cantidad:
        dataframe.drop(
            index=dataframe.index[mascara],
            inplace=True,
        )

    return cantidad


def _ejecutar_duplicados(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> int:
    if operacion.tipo != "eliminar_duplicados_completos":
        raise CleaningError(
            f"Operación de duplicados no soportada: '{operacion.tipo}'."
        )

    conservar = operacion.parametros.get("conservar", "primero")
    if conservar != "primero":
        raise CleaningError(
            "Solo se admite conservar la primera aparición "
            "de los duplicados completos."
        )

    mascara = dataframe.duplicated(keep="first")
    cantidad = int(mascara.sum())

    if cantidad:
        dataframe.drop(
            index=dataframe.index[mascara],
            inplace=True,
        )

    return cantidad


def _ejecutar_operacion(
    dataframe: pd.DataFrame,
    operacion: CleaningOperation,
) -> tuple[int, list[str]]:
    _validar_columna(dataframe, operacion)

    if operacion.familia == "texto":
        return _ejecutar_texto(dataframe, operacion), []

    if operacion.familia == "sustitucion":
        return _ejecutar_sustitucion(dataframe, operacion), []

    if operacion.familia == "conversion":
        return _ejecutar_conversion(dataframe, operacion)

    if operacion.familia == "nulos":
        return _ejecutar_nulos(dataframe, operacion), []

    if operacion.familia == "outliers":
        return _ejecutar_outliers(dataframe, operacion), []

    if operacion.familia == "duplicados":
        return _ejecutar_duplicados(dataframe, operacion), []

    raise CleaningError(
        f"Familia de limpieza no soportada: '{operacion.familia}'."
    )


def ejecutar_plan_limpieza(
    dataframe: pd.DataFrame,
    plan: CleaningPlan,
) -> tuple[pd.DataFrame, CleaningResult]:
    """
    Ejecuta un plan completo sobre una copia del DataFrame.

    La ejecución es transaccional desde el punto de vista del llamador:
    si cualquier operación falla, se lanza CleaningError y no se devuelve
    un DataFrame parcialmente limpiado. El DataFrame original nunca se
    modifica.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise CleaningError("'dataframe' debe ser un pandas.DataFrame.")

    if not isinstance(plan, CleaningPlan):
        raise CleaningError("'plan' debe ser una instancia de CleaningPlan.")

    trabajo = dataframe.copy(deep=True)
    filas_iniciales, columnas_iniciales = trabajo.shape
    ejecuciones: list[CleaningExecution] = []

    try:
        operaciones = plan.operaciones_ordenadas()
    except CleaningPlanError as exc:
        raise CleaningError(
            f"El plan de limpieza no es válido: {exc}"
        ) from exc

    for operacion in operaciones:
        filas_antes = len(trabajo)

        try:
            afectados, advertencias = _ejecutar_operacion(
                trabajo,
                operacion,
            )
        except Exception as exc:
            if isinstance(exc, CleaningError):
                mensaje = str(exc)
            else:
                mensaje = (
                    f"{type(exc).__name__}: {exc}"
                )

            raise CleaningError(
                "No se pudo ejecutar la operación "
                f"'{operacion.tipo}'"
                + (
                    f" sobre la columna '{operacion.columna}'"
                    if operacion.columna is not None
                    else ""
                )
                + f". Motivo: {mensaje}"
            ) from exc

        ejecuciones.append(
            CleaningExecution(
                operacion_id=operacion.id,
                familia=operacion.familia,
                tipo=operacion.tipo,
                columna=operacion.columna,
                parametros=dict(operacion.parametros),
                estado="ejecutada",
                registros_afectados=afectados,
                filas_antes=filas_antes,
                filas_despues=len(trabajo),
                advertencias=advertencias,
            )
        )

    resultado = CleaningResult(
        filas_antes=filas_iniciales,
        columnas_antes=columnas_iniciales,
        filas_despues=len(trabajo),
        columnas_despues=trabajo.shape[1],
        operaciones_solicitadas=len(operaciones),
        operaciones_ejecutadas=len(ejecuciones),
        ejecuciones=ejecuciones,
    )

    return trabajo, resultado

