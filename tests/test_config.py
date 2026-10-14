"""Tests para la configuración de DataQualityPy."""

import json
from pathlib import Path

import pytest

from src.config import ErrorConfiguracion, cargar_configuracion


def test_cargar_configuracion_predeterminada() -> None:
    """Comprueba los valores predeterminados del auditor."""
    configuracion = cargar_configuracion()

    assert configuracion == {
        "factor_iqr": 1.5,
        "umbral_fecha": 80,
        "max_categorias": 20,
        "max_porcentaje_categorias": 20,
        "umbral_identificador": 90,
        "columnas_clave": [],
        "tipos_columnas": {},
        "reglas_columnas": {},
    }


def test_cargar_configuracion_parcial(tmp_path: Path) -> None:
    """Comprueba que un JSON parcial conserve los valores restantes."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "factor_iqr": 2.0,
            }
        ),
        encoding="utf-8",
    )

    configuracion = cargar_configuracion(ruta)

    assert configuracion == {
        "factor_iqr": 2.0,
        "umbral_fecha": 80,
        "max_categorias": 20,
        "max_porcentaje_categorias": 20,
        "umbral_identificador": 90,
        "columnas_clave": [],
        "tipos_columnas": {},
        "reglas_columnas": {},
    }


def test_cargar_configuracion_completa(tmp_path: Path) -> None:
    """Comprueba la carga de una configuración completa válida."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "factor_iqr": 2.0,
                "umbral_fecha": 90,
                "max_categorias": 15,
                "max_porcentaje_categorias": 10,
                "umbral_identificador": 95,
                "columnas_clave": [
                    "id_cliente",
                    "fecha_pedido",
                ],
                "tipos_columnas": {
                    "id_cliente": "identificador",
                    "fecha_pedido": "fecha",
                },
            }
        ),
        encoding="utf-8",
    )

    configuracion = cargar_configuracion(ruta)

    assert configuracion == {
        "factor_iqr": 2.0,
        "umbral_fecha": 90,
        "max_categorias": 15,
        "max_porcentaje_categorias": 10,
        "umbral_identificador": 95,
        "columnas_clave": [
            "id_cliente",
            "fecha_pedido",
        ],
        "tipos_columnas": {
            "id_cliente": "identificador",
            "fecha_pedido": "fecha",
        },
        "reglas_columnas": {},
    }


def test_cargar_configuracion_archivo_inexistente(
    tmp_path: Path,
) -> None:
    """Comprueba el error si el archivo de configuración no existe."""
    ruta = tmp_path / "no_existe.json"

    with pytest.raises(
        ErrorConfiguracion,
        match="No se ha encontrado el archivo de configuración",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_json_invalido(
    tmp_path: Path,
) -> None:
    """Comprueba el tratamiento de un JSON mal formado."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        '{"factor_iqr": 2.0,',
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="no contiene un JSON válido",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_parametro_desconocido(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de parámetros desconocidos."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "factor_irq": 2.0,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="parámetros de configuración desconocidos",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_valor_fuera_de_rango(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un valor fuera del rango permitido."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "umbral_fecha": 120,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'umbral_fecha'.*entre 0 y 100",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_tipo_incorrecto(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un tipo de dato incorrecto."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "max_categorias": 20.5,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'max_categorias'.*número entero",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_umbral_identificador_invalido(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un umbral de identificador inválido."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "umbral_identificador": 120,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'umbral_identificador'.*entre 0 y 100",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_tipos_columnas_validos(
    tmp_path: Path,
) -> None:
    """Comprueba la aceptación de los siete tipos semánticos."""
    ruta = tmp_path / "config.json"
    tipos_columnas = {
        "importe": "numerico",
        "fecha_alta": "fecha",
        "fecha_evento": "fecha_hora",
        "activo": "booleano_binario",
        "estado": "categorico",
        "cliente_id": "identificador",
        "comentario": "texto_libre",
    }
    ruta.write_text(
        json.dumps({"tipos_columnas": tipos_columnas}),
        encoding="utf-8",
    )

    configuracion = cargar_configuracion(ruta)

    assert configuracion["tipos_columnas"] == tipos_columnas


def test_cargar_configuracion_tipos_columnas_debe_ser_objeto(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de tipos_columnas si no es un objeto."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"tipos_columnas": ["Age", "numerico"]}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'tipos_columnas'.*objeto",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_rechaza_nombre_columna_vacio(
    tmp_path: Path,
) -> None:
    """Comprueba que los nombres declarados no estén vacíos."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"tipos_columnas": {"   ": "numerico"}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'tipos_columnas'.*nombres de columnas no vacíos",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_rechaza_tipo_semantico_no_textual(
    tmp_path: Path,
) -> None:
    """Comprueba que el tipo semántico declarado sea texto."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"tipos_columnas": {"Age": 123}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="Cada tipo declarado.*cadena de texto",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_rechaza_tipo_semantico_desconocido(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de alias o tipos no admitidos."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"tipos_columnas": {"Age": "numeric"}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="Tipo semántico no válido.*Age.*numeric",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_reglas_columnas_validas(
    tmp_path: Path,
) -> None:
    """Comprueba la aceptación de las reglas de negocio de V3."""
    ruta = tmp_path / "config.json"
    reglas_columnas = {
        "Age": {
            "min": 0,
            "max": 120,
        },
        "precio": {
            "min": 0,
        },
        "estado": {
            "valores_permitidos": [
                "Activo",
                "Inactivo",
                "Pendiente",
            ],
        },
    }
    ruta.write_text(
        json.dumps({"reglas_columnas": reglas_columnas}),
        encoding="utf-8",
    )

    configuracion = cargar_configuracion(ruta)

    assert configuracion["reglas_columnas"] == reglas_columnas


def test_cargar_configuracion_reglas_columnas_debe_ser_objeto(
    tmp_path: Path,
) -> None:
    """Comprueba que reglas_columnas sea un objeto JSON."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"reglas_columnas": ["Age", {"min": 0}]}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'reglas_columnas'.*objeto",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_reglas_rechaza_nombre_columna_vacio(
    tmp_path: Path,
) -> None:
    """Comprueba que una regla no pueda declarar una columna vacía."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"reglas_columnas": {"   ": {"min": 0}}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'reglas_columnas'.*nombres de columnas no vacíos",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_reglas_de_columna_deben_ser_objeto(
    tmp_path: Path,
) -> None:
    """Comprueba que las reglas de cada columna formen un objeto."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"reglas_columnas": {"Age": ["min", 0]}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="Reglas de la columna 'Age'.*objeto",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_rechaza_regla_desconocida(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de reglas no admitidas en V3."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"reglas_columnas": {"Age": {"minimo": 0}}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="Regla desconocida.*Age.*minimo",
    ):
        cargar_configuracion(ruta)


@pytest.mark.parametrize("valor", ["0", None, True, False])
def test_cargar_configuracion_rechaza_min_no_numerico(
    tmp_path: Path,
    valor: object,
) -> None:
    """Comprueba que min sea numérico y no booleano."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"reglas_columnas": {"Age": {"min": valor}}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'min'.*Age.*numérico",
    ):
        cargar_configuracion(ruta)


@pytest.mark.parametrize("valor", ["120", None, True, False])
def test_cargar_configuracion_rechaza_max_no_numerico(
    tmp_path: Path,
    valor: object,
) -> None:
    """Comprueba que max sea numérico y no booleano."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps({"reglas_columnas": {"Age": {"max": valor}}}),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'max'.*Age.*numérico",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_rechaza_min_mayor_que_max(
    tmp_path: Path,
) -> None:
    """Comprueba que el límite mínimo no supere al máximo."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "reglas_columnas": {
                    "Age": {
                        "min": 121,
                        "max": 120,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'min'.*no puede ser mayor.*'max'.*Age",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_acepta_min_igual_a_max(
    tmp_path: Path,
) -> None:
    """Comprueba que los límites inclusivos puedan ser iguales."""
    ruta = tmp_path / "config.json"
    reglas_columnas = {
        "puntuacion": {
            "min": 5,
            "max": 5,
        },
    }
    ruta.write_text(
        json.dumps({"reglas_columnas": reglas_columnas}),
        encoding="utf-8",
    )

    configuracion = cargar_configuracion(ruta)

    assert configuracion["reglas_columnas"] == reglas_columnas


def test_cargar_configuracion_valores_permitidos_debe_ser_lista(
    tmp_path: Path,
) -> None:
    """Comprueba que valores_permitidos sea una lista JSON."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "reglas_columnas": {
                    "estado": {
                        "valores_permitidos": "Activo",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'valores_permitidos'.*estado.*lista",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_rechaza_valores_permitidos_vacios(
    tmp_path: Path,
) -> None:
    """Comprueba que valores_permitidos contenga al menos un valor."""
    ruta = tmp_path / "config.json"
    ruta.write_text(
        json.dumps(
            {
                "reglas_columnas": {
                    "estado": {
                        "valores_permitidos": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ErrorConfiguracion,
        match="'valores_permitidos'.*estado.*vacía",
    ):
        cargar_configuracion(ruta)


def test_cargar_configuracion_acepta_reglas_combinadas(
    tmp_path: Path,
) -> None:
    """Comprueba que una columna pueda combinar las tres reglas."""
    ruta = tmp_path / "config.json"
    reglas_columnas = {
        "puntuacion": {
            "min": 0,
            "max": 10,
            "valores_permitidos": [
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
            ],
        },
    }
    ruta.write_text(
        json.dumps({"reglas_columnas": reglas_columnas}),
        encoding="utf-8",
    )

    configuracion = cargar_configuracion(ruta)

    assert configuracion["reglas_columnas"] == reglas_columnas

