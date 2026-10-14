"""Funciones para la carga de datasets en DataQualityPy."""

import csv
from pathlib import Path

import pandas as pd


class ErrorCargaArchivo(Exception):
    """Error producido al cargar un archivo de datos."""


CODIFICACIONES_CSV = ("utf-8", "cp1252")
DELIMITADORES_CSV = ",;\t|"
DELIMITADORES_NO_ADMITIDOS = "^"
TAMANO_MUESTRA_CSV = 8192


def _leer_muestra_csv(ruta_archivo: Path) -> tuple[str, str]:
    """Lee una muestra del CSV y devuelve el texto y su codificación."""
    archivo_vacio = False

    for codificacion in CODIFICACIONES_CSV:
        try:
            with ruta_archivo.open(
                "r",
                encoding=codificacion,
                newline="",
            ) as archivo:
                muestra = archivo.read(TAMANO_MUESTRA_CSV)

            if not muestra.strip():
                archivo_vacio = True
                break

            return muestra, codificacion

        except UnicodeDecodeError:
            continue

        except OSError as error:
            raise ErrorCargaArchivo(
                f"No se ha podido leer el archivo '{ruta_archivo}'."
            ) from error

    if archivo_vacio:
        raise ErrorCargaArchivo(
            f"El archivo CSV '{ruta_archivo}' está vacío."
        )

    raise ErrorCargaArchivo(
        f"No se ha podido interpretar la codificación "
        f"del archivo CSV '{ruta_archivo}'."
    )


def _detectar_delimitador_por_cabecera(
    muestra: str,
) -> str | None:
    """Busca un delimitador claro en la primera línea no vacía."""
    lineas = [
        linea
        for linea in muestra.splitlines()
        if linea.strip()
    ]

    if not lineas:
        return None

    cabecera = lineas[0]

    apariciones = {
        delimitador: cabecera.count(delimitador)
        for delimitador in DELIMITADORES_CSV
    }

    maximo_apariciones = max(apariciones.values())

    if maximo_apariciones == 0:
        return None

    candidatos_maximos = [
        delimitador
        for delimitador, cantidad in apariciones.items()
        if cantidad == maximo_apariciones
    ]

    if len(candidatos_maximos) != 1:
        return None

    return candidatos_maximos[0]


def _parece_csv_una_columna(muestra: str) -> bool:
    """Indica si la muestra parece corresponder a un CSV de una columna."""
    lineas = [
        linea
        for linea in muestra.splitlines()
        if linea.strip()
    ]

    if not lineas:
        return False

    for linea in lineas:
        if any(
            delimitador in linea
            for delimitador in DELIMITADORES_CSV
        ):
            return False

        if any(
            delimitador in linea
            for delimitador in DELIMITADORES_NO_ADMITIDOS
        ):
            return False

    return True


def _detectar_delimitador_csv(muestra: str) -> str | None:
    """Detecta el delimitador de un CSV a partir de una muestra."""
    try:
        dialecto = csv.Sniffer().sniff(
            muestra,
            delimiters=DELIMITADORES_CSV,
        )
        return dialecto.delimiter

    except csv.Error:
        delimitador = _detectar_delimitador_por_cabecera(muestra)

        if delimitador is not None:
            return delimitador

        if _parece_csv_una_columna(muestra):
            return None

        raise ErrorCargaArchivo(
            "No se ha podido identificar el separador "
            "del archivo CSV."
        )



def obtener_metadatos_csv(
    ruta_archivo: str | Path,
) -> dict[str, str | None]:
    """Devuelve codificación y delimitador detectados en un CSV."""
    ruta = Path(ruta_archivo)

    if not ruta.is_file():
        raise ErrorCargaArchivo(
            f"No se ha encontrado el archivo: '{ruta}'."
        )

    muestra, codificacion = _leer_muestra_csv(ruta)
    delimitador = _detectar_delimitador_csv(muestra)

    return {
        "codificacion": codificacion,
        "delimitador": delimitador,
    }


def cargar_csv(ruta_archivo: str | Path) -> pd.DataFrame:
    """Carga un CSV preservando posibles marcadores textuales de ausencia."""
    ruta = Path(ruta_archivo)

    metadatos = obtener_metadatos_csv(ruta)
    codificacion = metadatos["codificacion"]
    delimitador = metadatos["delimitador"]

    try:
        if delimitador is None:
            return pd.read_csv(
                ruta,
                encoding=codificacion,
                keep_default_na=False,
            )

        return pd.read_csv(
            ruta,
            sep=delimitador,
            encoding=codificacion,
            keep_default_na=False,
        )

    except pd.errors.EmptyDataError as error:
        raise ErrorCargaArchivo(
            f"El archivo CSV '{ruta}' está vacío."
        ) from error

    except pd.errors.ParserError as error:
        raise ErrorCargaArchivo(
            f"No se ha podido interpretar correctamente "
            f"el archivo CSV '{ruta}'."
        ) from error

    except (UnicodeDecodeError, OSError) as error:
        raise ErrorCargaArchivo(
            f"No se ha podido leer el archivo CSV '{ruta}'."
        ) from error



def obtener_hojas_excel(ruta_archivo: str | Path) -> list[str]:
    """Devuelve las hojas disponibles de un archivo Excel."""
    ruta = Path(ruta_archivo)

    if not ruta.is_file():
        raise ErrorCargaArchivo(
            f"No se ha encontrado el archivo: '{ruta}'."
        )

    if ruta.suffix.lower() != ".xlsx":
        raise ErrorCargaArchivo(
            f"El archivo '{ruta}' no es un archivo Excel .xlsx."
        )

    try:
        with pd.ExcelFile(ruta) as libro:
            hojas = list(libro.sheet_names)

        if not hojas:
            raise ErrorCargaArchivo(
                f"El archivo Excel '{ruta}' no contiene hojas."
            )

        return hojas

    except ErrorCargaArchivo:
        raise

    except Exception as error:
        raise ErrorCargaArchivo(
            f"No se han podido obtener las hojas del archivo Excel '{ruta}'. "
            "El archivo puede estar dañado o no tener un formato válido."
        ) from error


def cargar_excel(
    ruta_archivo: str | Path,
    hoja: str | None = None,
) -> pd.DataFrame:
    """Carga una hoja de un archivo Excel."""
    ruta = Path(ruta_archivo)

    try:
        with pd.ExcelFile(ruta) as libro:
            hojas_disponibles = libro.sheet_names

            if not hojas_disponibles:
                raise ErrorCargaArchivo(
                    f"El archivo Excel '{ruta}' no contiene hojas."
                )

            if hoja is None:
                if len(hojas_disponibles) > 1:
                    hojas = "\n".join(
                        f"- {nombre}"
                        for nombre in hojas_disponibles
                    )

                    raise ErrorCargaArchivo(
                        f"El archivo Excel '{ruta}' contiene varias hojas.\n\n"
                        f"Hojas disponibles:\n{hojas}\n\n"
                        "Indica la hoja que deseas analizar "
                        "con el argumento --hoja."
                    )

                hoja_seleccionada = hojas_disponibles[0]

            else:
                hoja_seleccionada = hoja

            if hoja_seleccionada not in hojas_disponibles:
                hojas = "\n".join(
                    f"- {nombre}"
                    for nombre in hojas_disponibles
                )

                raise ErrorCargaArchivo(
                    f"La hoja '{hoja_seleccionada}' no existe "
                    f"en el archivo Excel '{ruta}'.\n\n"
                    f"Hojas disponibles:\n{hojas}"
                )

            return pd.read_excel(
                libro,
                sheet_name=hoja_seleccionada,
                keep_default_na=False,
            )

    except ErrorCargaArchivo:
        raise

    except Exception as error:
        raise ErrorCargaArchivo(
            f"No se ha podido leer el archivo Excel '{ruta}'. "
            "El archivo puede estar dañado o no tener un formato válido."
        ) from error


def cargar_archivo(
    ruta_archivo: str | Path,
    hoja: str | None = None,
) -> pd.DataFrame:
    """Carga un dataset utilizando el lector adecuado según su extensión."""
    ruta = Path(ruta_archivo)

    if not ruta.is_file():
        raise ErrorCargaArchivo(
            f"No se ha encontrado el archivo: '{ruta}'."
        )

    extension = ruta.suffix.lower()

    if extension not in {".csv", ".xlsx"}:
        raise ErrorCargaArchivo(
            f"Formato de archivo no compatible: '{ruta.suffix}'. "
            "DataQualityPy admite archivos .csv y .xlsx."
        )

    try:
        if extension == ".csv":
            return cargar_csv(ruta)

        return cargar_excel(
            ruta,
            hoja=hoja,
        )

    except ErrorCargaArchivo:
        raise

    except Exception as error:
        raise ErrorCargaArchivo(
            f"No se ha podido leer el archivo '{ruta}'. "
            "El archivo puede estar dañado o no tener un formato válido."
        ) from error