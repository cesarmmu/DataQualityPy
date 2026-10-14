"""Punto de entrada de DataQualityPy."""

import argparse
from pathlib import Path

from src.audit import auditar_dataset
from src.config import ErrorConfiguracion, cargar_configuracion
from src.html_report import generar_informe_html
from src.json_report import generar_informe_json
from src.loader import ErrorCargaArchivo, cargar_archivo
from src.report import generar_informe


DIRECTORIO_SALIDA = Path("data/output")


def obtener_argumentos() -> argparse.Namespace:
    """Obtiene los argumentos recibidos desde la línea de comandos."""
    parser = argparse.ArgumentParser(
        description=(
            "DataQualityPy - Auditor automático de calidad de datos"
        )
    )

    parser.add_argument(
        "archivo",
        help=(
            "Ruta del archivo CSV o Excel que se desea analizar"
        ),
    )

    parser.add_argument(
        "--hoja",
        help=(
            "Nombre de la hoja de Excel que se desea analizar"
        ),
    )

    parser.add_argument(
        "--config",
        help=(
            "Ruta de un archivo JSON con la configuración "
            "personalizada del auditor"
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Genera también un informe de auditoría "
            "en formato JSON"
        ),
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help=(
            "Genera también un informe de auditoría "
            "en formato HTML"
        ),
    )

    return parser.parse_args()


def _crear_ruta_salida(
    ruta_archivo: Path,
    extension: str,
) -> Path:
    """Construye la ruta de un informe generado por DataQualityPy."""
    nombre_salida = (
        f"{ruta_archivo.stem}_auditoria.{extension}"
    )

    return DIRECTORIO_SALIDA / nombre_salida


def main() -> None:
    """Ejecuta la aplicación DataQualityPy."""
    argumentos = obtener_argumentos()
    ruta_archivo = Path(argumentos.archivo)

    try:
        configuracion = cargar_configuracion(argumentos.config)

        datos = cargar_archivo(
            ruta_archivo,
            hoja=argumentos.hoja,
        )

        resultado_auditoria = auditar_dataset(
            datos,
            nombre_archivo=ruta_archivo.name,
            configuracion=configuracion,
        )

        generar_informe(resultado_auditoria)

        if argumentos.json:
            ruta_json = _crear_ruta_salida(
                ruta_archivo,
                extension="json",
            )

            generar_informe_json(
                resultado_auditoria,
                ruta_json,
            )

            print()
            print(
                "Informe JSON generado: "
                f"{ruta_json}"
            )

        if argumentos.html:
            ruta_html = _crear_ruta_salida(
                ruta_archivo,
                extension="html",
            )

            generar_informe_html(
                resultado_auditoria,
                datos,
                ruta_html,
            )

            print()
            print(
                "Informe HTML generado: "
                f"{ruta_html}"
            )

    except (ErrorCargaArchivo, ErrorConfiguracion) as error:
        print(f"ERROR: {error}")


if __name__ == "__main__":
    main()
