"""Tests para las funciones de carga de DataQualityPy."""

from pathlib import Path

import pandas as pd
import pytest

from src.loader import ErrorCargaArchivo, cargar_archivo


def test_cargar_archivo_csv(tmp_path: Path) -> None:
    """Comprueba la carga correcta de un archivo CSV."""
    ruta = tmp_path / "datos.csv"
    ruta.write_text(
        "producto,precio\nPortatil,900\nRaton,25\n",
        encoding="utf-8",
    )

    datos = cargar_archivo(ruta)

    assert isinstance(datos, pd.DataFrame)
    assert datos.shape == (2, 2)
    assert datos["producto"].tolist() == ["Portatil", "Raton"]


def test_cargar_archivo_excel(tmp_path: Path) -> None:
    """Comprueba la carga correcta de un archivo Excel."""
    ruta = tmp_path / "datos.xlsx"

    datos_originales = pd.DataFrame(
        {
            "producto": ["Portatil", "Raton"],
            "precio": [900, 25],
        }
    )
    datos_originales.to_excel(ruta, index=False)

    datos = cargar_archivo(ruta)

    assert isinstance(datos, pd.DataFrame)
    assert datos.shape == (2, 2)
    assert datos["precio"].tolist() == [900, 25]


def test_cargar_archivo_inexistente(tmp_path: Path) -> None:
    """Comprueba el error al intentar cargar un archivo inexistente."""
    ruta = tmp_path / "no_existe.csv"

    with pytest.raises(
        ErrorCargaArchivo,
        match="No se ha encontrado el archivo",
    ):
        cargar_archivo(ruta)


def test_cargar_archivo_extension_no_compatible(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de extensiones no compatibles."""
    ruta = tmp_path / "datos.txt"
    ruta.write_text("contenido", encoding="utf-8")

    with pytest.raises(
        ErrorCargaArchivo,
        match="Formato de archivo no compatible",
    ):
        cargar_archivo(ruta)


def test_cargar_archivo_excel_invalido(tmp_path: Path) -> None:
    """Comprueba el tratamiento de un archivo Excel inválido."""
    ruta = tmp_path / "datos.xlsx"
    ruta.write_text(
        "Este archivo no es realmente un Excel.",
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorCargaArchivo,
        match="No se ha podido leer el archivo",
    ):
        cargar_archivo(ruta)


def test_cargar_csv_separado_por_punto_y_coma(
    tmp_path: Path,
) -> None:
    """Comprueba la detección del separador punto y coma."""
    ruta = tmp_path / "datos_punto_coma.csv"
    ruta.write_text(
        "producto;categoria;precio\n"
        "Portatil;Informatica;899.99\n"
        "Raton;Informatica;24.50\n",
        encoding="utf-8",
    )

    datos = cargar_archivo(ruta)

    assert datos.shape == (2, 3)
    assert datos.columns.tolist() == [
        "producto",
        "categoria",
        "precio",
    ]
    assert datos["precio"].tolist() == [899.99, 24.50]


def test_cargar_csv_separado_por_tabulador(
    tmp_path: Path,
) -> None:
    """Comprueba la detección del separador tabulador."""
    ruta = tmp_path / "datos_tabulador.csv"
    ruta.write_text(
        "producto\tcategoria\tprecio\n"
        "Portatil\tInformatica\t899.99\n"
        "Raton\tInformatica\t24.50\n",
        encoding="utf-8",
    )

    datos = cargar_archivo(ruta)

    assert datos.shape == (2, 3)
    assert datos.columns.tolist() == [
        "producto",
        "categoria",
        "precio",
    ]


def test_cargar_csv_separado_por_barra_vertical(
    tmp_path: Path,
) -> None:
    """Comprueba la detección del separador barra vertical."""
    ruta = tmp_path / "datos_barra.csv"
    ruta.write_text(
        "producto|categoria|precio\n"
        "Portatil|Informatica|899.99\n"
        "Raton|Informatica|24.50\n",
        encoding="utf-8",
    )

    datos = cargar_archivo(ruta)

    assert datos.shape == (2, 3)
    assert datos.columns.tolist() == [
        "producto",
        "categoria",
        "precio",
    ]


def test_cargar_csv_codificacion_cp1252(
    tmp_path: Path,
) -> None:
    """Comprueba la carga de un CSV con codificación Windows-1252."""
    ruta = tmp_path / "datos_cp1252.csv"
    ruta.write_text(
        "producto;categoria;pais\n"
        "Portátil;Informática;España\n"
        "Ratón;Informática;España\n",
        encoding="cp1252",
    )

    datos = cargar_archivo(ruta)

    assert datos.shape == (2, 3)
    assert datos["producto"].tolist() == ["Portátil", "Ratón"]
    assert datos["categoria"].tolist() == [
        "Informática",
        "Informática",
    ]
    assert datos["pais"].tolist() == ["España", "España"]


def test_cargar_csv_vacio(tmp_path: Path) -> None:
    """Comprueba el tratamiento de un archivo CSV vacío."""
    ruta = tmp_path / "datos_vacios.csv"
    ruta.write_text("", encoding="utf-8")

    with pytest.raises(
        ErrorCargaArchivo,
        match="está vacío",
    ):
        cargar_archivo(ruta)


def test_cargar_csv_separador_no_admitido(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un separador CSV no admitido."""
    ruta = tmp_path / "datos_separador_invalido.csv"
    ruta.write_text(
        "producto^categoria^precio\n"
        "Portatil^Informatica^899.99\n"
        "Raton^Informatica^24.50\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorCargaArchivo,
        match="No se ha podido identificar el separador",
    ):
        cargar_archivo(ruta)


def test_cargar_csv_malformado(tmp_path: Path) -> None:
    """Comprueba el tratamiento de un CSV con estructura inconsistente."""
    ruta = tmp_path / "datos_malformados.csv"
    ruta.write_text(
        "producto,categoria,precio\n"
        "Portatil,Informatica,899.99\n"
        "Raton,Informatica,24.50\n"
        "Teclado,Informatica,49.99,VALOR_EXTRA\n"
        "Monitor,Informatica,229.00\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorCargaArchivo,
        match="No se ha podido interpretar correctamente",
    ):
        cargar_archivo(ruta)


def test_cargar_csv_una_columna(tmp_path: Path) -> None:
    """Comprueba la carga correcta de un CSV de una sola columna."""
    ruta = tmp_path / "una_columna.csv"
    ruta.write_text(
        "valor\n"
        "2\n"
        "3\n"
        "3\n"
        "4\n"
        "4\n"
        "5\n"
        "50\n",
        encoding="utf-8",
    )

    datos = cargar_archivo(ruta)

    assert isinstance(datos, pd.DataFrame)
    assert datos.shape == (7, 1)
    assert datos.columns.tolist() == ["valor"]
    assert datos["valor"].tolist() == [
        2,
        3,
        3,
        4,
        4,
        5,
        50,
    ]


def test_cargar_csv_preserva_nulos_textuales(
    tmp_path: Path,
) -> None:
    """Comprueba que el CSV preserve posibles nulos como texto."""
    ruta = tmp_path / "nulos_textuales.csv"
    ruta.write_text(
        "id,estado\n"
        "1,N/A\n"
        "2,NA\n"
        "3,null\n"
        "4,None\n"
        "5,-\n"
        "6,\n",
        encoding="utf-8",
    )

    datos = cargar_archivo(ruta)

    assert datos["estado"].tolist() == [
        "N/A",
        "NA",
        "null",
        "None",
        "-",
        "",
    ]
    assert datos["estado"].isna().sum() == 0


def test_cargar_excel_varias_hojas_sin_seleccion(
    tmp_path: Path,
) -> None:
    """Comprueba que un Excel multih hoja requiera seleccionar hoja."""
    ruta = tmp_path / "varias_hojas.xlsx"

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "indicador": ["Ventas", "Clientes"],
                "valor": [12500, 48],
            }
        ).to_excel(
            writer,
            sheet_name="Resumen",
            index=False,
        )

        pd.DataFrame(
            {
                "producto": ["Portatil", "Raton"],
                "precio": [899.99, 24.50],
            }
        ).to_excel(
            writer,
            sheet_name="Ventas",
            index=False,
        )

    with pytest.raises(
        ErrorCargaArchivo,
        match="contiene varias hojas",
    ):
        cargar_archivo(ruta)


def test_cargar_excel_hoja_seleccionada(
    tmp_path: Path,
) -> None:
    """Comprueba la carga de una hoja concreta de un Excel."""
    ruta = tmp_path / "varias_hojas.xlsx"

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "indicador": ["Ventas", "Clientes"],
                "valor": [12500, 48],
            }
        ).to_excel(
            writer,
            sheet_name="Resumen",
            index=False,
        )

        pd.DataFrame(
            {
                "producto": ["Portatil", "Raton", "Teclado"],
                "precio": [899.99, 24.50, 49.99],
            }
        ).to_excel(
            writer,
            sheet_name="Ventas",
            index=False,
        )

    datos = cargar_archivo(
        ruta,
        hoja="Ventas",
    )

    assert isinstance(datos, pd.DataFrame)
    assert datos.shape == (3, 2)
    assert datos.columns.tolist() == [
        "producto",
        "precio",
    ]
    assert datos["producto"].tolist() == [
        "Portatil",
        "Raton",
        "Teclado",
    ]


def test_cargar_excel_hoja_inexistente(
    tmp_path: Path,
) -> None:
    """Comprueba el error al solicitar una hoja Excel inexistente."""
    ruta = tmp_path / "varias_hojas.xlsx"

    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "indicador": ["Ventas", "Clientes"],
                "valor": [12500, 48],
            }
        ).to_excel(
            writer,
            sheet_name="Resumen",
            index=False,
        )

        pd.DataFrame(
            {
                "producto": ["Portatil", "Raton"],
                "precio": [899.99, 24.50],
            }
        ).to_excel(
            writer,
            sheet_name="Ventas",
            index=False,
        )

    with pytest.raises(
        ErrorCargaArchivo,
        match="La hoja 'Facturas' no existe",
    ):
        cargar_archivo(
            ruta,
            hoja="Facturas",
        )