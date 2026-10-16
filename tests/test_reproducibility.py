"""Tests de reproducibilidad de DataQualityPy V6.4."""

import hashlib

import pytest

from src.cleaning_plan import CleaningPlan
from src.reproducibility import (
    HASH_ALGORITHM,
    HASH_BLOCK_SIZE,
    MANIFEST_FORMAT_VERSION,
    DatasetReference,
    ExecutionManifest,
    ReproducibilityError,
    calcular_sha256,
    crear_manifiesto,
)


FECHA_PRUEBA = "2026-10-14T10:00:00+02:00"


def _crear_dataset(tmp_path, contenido: str = "a,b\n1,2\n"):
    """Crea un dataset físico sencillo para los tests."""
    ruta = tmp_path / "datos.csv"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _crear_plan() -> CleaningPlan:
    """Crea un plan sencillo reutilizable."""
    plan = CleaningPlan()
    plan.crear_operacion(
        familia="texto",
        tipo="eliminar_espacios_externos",
        columna="nombre",
    )
    return plan


def test_crear_manifiesto_basico_v6(tmp_path) -> None:
    """Puede construirse un manifiesto sin plan de limpieza."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    assert isinstance(manifiesto, ExecutionManifest)
    assert manifiesto.format_version == MANIFEST_FORMAT_VERSION
    assert manifiesto.created_at == FECHA_PRUEBA
    assert isinstance(manifiesto.dataset, DatasetReference)
    assert manifiesto.cleaning_plan is None


def test_referencia_dataset_conserva_metadatos_v6(tmp_path) -> None:
    """La referencia identifica nombre, extensión y tamaño físico."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.dataset.file_name == "datos.csv"
    assert manifiesto.dataset.file_extension == ".csv"
    assert manifiesto.dataset.file_size == ruta.stat().st_size


def test_configuracion_predeterminada_se_guarda_completa_v6(tmp_path) -> None:
    """El manifiesto conserva toda la configuración efectiva."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.audit_configuration == {
        "factor_iqr": 1.5,
        "umbral_fecha": 80,
        "max_categorias": 20,
        "max_porcentaje_categorias": 20,
        "umbral_identificador": 90,
        "columnas_clave": [],
        "tipos_columnas": {},
        "reglas_columnas": {},
    }


def test_configuracion_parcial_se_completa_v6(tmp_path) -> None:
    """Una personalización parcial conserva también los defaults efectivos."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        audit_configuration={"factor_iqr": 2.0},
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.audit_configuration["factor_iqr"] == 2.0
    assert manifiesto.audit_configuration["umbral_fecha"] == 80
    assert manifiesto.audit_configuration["max_categorias"] == 20
    assert manifiesto.audit_configuration["columnas_clave"] == []


def test_configuracion_compleja_se_conserva_v6(tmp_path) -> None:
    """Claves, tipos y reglas forman parte del manifiesto reproducible."""
    ruta = _crear_dataset(tmp_path)

    configuracion = {
        "columnas_clave": ["id"],
        "tipos_columnas": {
            "id": "identificador",
            "importe": "numerico",
        },
        "reglas_columnas": {
            "importe": {
                "min": 0,
                "max": 1000,
            },
            "estado": {
                "valores_permitidos": ["activo", "inactivo"],
            },
        },
    }

    manifiesto = crear_manifiesto(
        ruta,
        audit_configuration=configuracion,
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.audit_configuration["columnas_clave"] == ["id"]
    assert manifiesto.audit_configuration["tipos_columnas"] == {
        "id": "identificador",
        "importe": "numerico",
    }
    assert manifiesto.audit_configuration["reglas_columnas"] == {
        "importe": {
            "min": 0,
            "max": 1000,
        },
        "estado": {
            "valores_permitidos": ["activo", "inactivo"],
        },
    }


def test_configuracion_invalida_es_rechazada_v6(tmp_path) -> None:
    """El manifiesto reutiliza la validación oficial de configuración."""
    ruta = _crear_dataset(tmp_path)

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            audit_configuration={"factor_iqr": -1},
            created_at=FECHA_PRUEBA,
        )


def test_parametro_configuracion_desconocido_es_rechazado_v6(
    tmp_path,
) -> None:
    """No se almacenan parámetros ajenos al auditor."""
    ruta = _crear_dataset(tmp_path)

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            audit_configuration={"desconocido": 123},
            created_at=FECHA_PRUEBA,
        )


def test_dataset_inexistente_es_rechazado_v6(tmp_path) -> None:
    """El manifiesto exige un archivo de origen existente."""
    ruta = tmp_path / "no_existe.csv"

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            created_at=FECHA_PRUEBA,
        )


def test_fecha_invalida_es_rechazada_v6(tmp_path) -> None:
    """La fecha del manifiesto debe utilizar ISO 8601."""
    ruta = _crear_dataset(tmp_path)

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            created_at="14/10/2026",
        )


def test_manifiesto_puede_incluir_plan_limpieza_v6(tmp_path) -> None:
    """Un plan puede incorporarse mediante el formato reutilizable V6.2.4."""
    ruta = _crear_dataset(tmp_path)
    plan = _crear_plan()

    manifiesto = crear_manifiesto(
        ruta,
        cleaning_plan=plan,
        cleaning_plan_name="Limpieza clientes",
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.cleaning_plan is not None
    assert manifiesto.cleaning_plan.name == "Limpieza clientes"
    assert manifiesto.cleaning_plan.created_at == FECHA_PRUEBA
    assert len(manifiesto.cleaning_plan.operations) == 1


def test_plan_no_conserva_id_original_v6(tmp_path) -> None:
    """El manifiesto guarda definición reutilizable, no identidad interna."""
    ruta = _crear_dataset(tmp_path)
    plan = _crear_plan()

    operacion_original = plan.operaciones_ordenadas()[0]

    manifiesto = crear_manifiesto(
        ruta,
        cleaning_plan=plan,
        cleaning_plan_name="Plan",
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.cleaning_plan is not None

    datos = manifiesto.cleaning_plan.a_dict()
    operacion_guardada = datos["operations"][0]

    assert "id" not in operacion_guardada
    assert "orden_ejecucion" not in operacion_guardada
    assert operacion_original.id not in str(operacion_guardada)


def test_plan_requiere_nombre_v6(tmp_path) -> None:
    """Un plan incluido debe tener nombre reutilizable."""
    ruta = _crear_dataset(tmp_path)

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            cleaning_plan=_crear_plan(),
            created_at=FECHA_PRUEBA,
        )


def test_nombre_plan_sin_plan_es_rechazado_v6(tmp_path) -> None:
    """No se acepta metadata de plan cuando no existe plan."""
    ruta = _crear_dataset(tmp_path)

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            cleaning_plan_name="Plan inexistente",
            created_at=FECHA_PRUEBA,
        )


def test_tipo_plan_invalido_es_rechazado_v6(tmp_path) -> None:
    """El manifiesto exige un CleaningPlan real."""
    ruta = _crear_dataset(tmp_path)

    with pytest.raises(ReproducibilityError):
        crear_manifiesto(
            ruta,
            cleaning_plan="plan",  # type: ignore[arg-type]
            cleaning_plan_name="Plan",
            created_at=FECHA_PRUEBA,
        )


def test_a_dict_genera_estructura_serializable_v6(tmp_path) -> None:
    """El manifiesto puede convertirse a una estructura persistible."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        cleaning_plan=_crear_plan(),
        cleaning_plan_name="Plan",
        created_at=FECHA_PRUEBA,
    )

    datos = manifiesto.a_dict()

    assert set(datos) == {
        "format_version",
        "created_at",
        "dataset",
        "audit_configuration",
        "cleaning_plan",
    }

    assert datos["dataset"] == {
        "file_name": "datos.csv",
        "file_extension": ".csv",
        "file_size": ruta.stat().st_size,
        "sha256": calcular_sha256(ruta),
    }

    assert isinstance(datos["audit_configuration"], dict)
    assert isinstance(datos["cleaning_plan"], dict)


def test_a_dict_sin_plan_utiliza_null_v6(tmp_path) -> None:
    """La ausencia de plan queda explícitamente representada."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.a_dict()["cleaning_plan"] is None


def test_configuracion_del_manifiesto_es_independiente_v6(tmp_path) -> None:
    """Cambiar la entrada original después no altera el manifiesto."""
    ruta = _crear_dataset(tmp_path)

    configuracion = {
        "columnas_clave": ["id"],
        "tipos_columnas": {
            "id": "identificador",
        },
    }

    manifiesto = crear_manifiesto(
        ruta,
        audit_configuration=configuracion,
        created_at=FECHA_PRUEBA,
    )

    configuracion["columnas_clave"].append("otro")
    configuracion["tipos_columnas"]["otro"] = "texto_libre"

    assert manifiesto.audit_configuration["columnas_clave"] == ["id"]
    assert manifiesto.audit_configuration["tipos_columnas"] == {
        "id": "identificador",
    }


def test_a_dict_devuelve_copia_independiente_configuracion_v6(
    tmp_path,
) -> None:
    """Modificar la representación externa no altera el manifiesto."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        audit_configuration={
            "columnas_clave": ["id"],
            "reglas_columnas": {
                "estado": {
                    "valores_permitidos": ["A", "B"],
                }
            },
        },
        created_at=FECHA_PRUEBA,
    )

    datos = manifiesto.a_dict()

    datos["audit_configuration"]["columnas_clave"].append("otro")
    datos["audit_configuration"]["reglas_columnas"]["estado"][
        "valores_permitidos"
    ].append("C")

    assert manifiesto.audit_configuration["columnas_clave"] == ["id"]
    assert manifiesto.audit_configuration["reglas_columnas"]["estado"][
        "valores_permitidos"
    ] == ["A", "B"]


def test_algoritmo_sha256_declarado_v6() -> None:
    """La identificación reproducible utiliza explícitamente SHA-256."""
    assert HASH_ALGORITHM == "sha256"


def test_tamano_bloque_hash_es_positivo_v6() -> None:
    """El cálculo por bloques utiliza un tamaño válido."""
    assert isinstance(HASH_BLOCK_SIZE, int)
    assert HASH_BLOCK_SIZE > 0


def test_calcular_sha256_coincide_con_hashlib_v6(tmp_path) -> None:
    """La función pública produce la huella SHA-256 esperada."""
    contenido = b"DataQualityPy V6\nreproducibilidad\n"
    ruta = tmp_path / "datos.bin"
    ruta.write_bytes(contenido)

    esperado = hashlib.sha256(contenido).hexdigest()

    assert calcular_sha256(ruta) == esperado


def test_sha256_tiene_formato_hexadecimal_v6(tmp_path) -> None:
    """La huella SHA-256 contiene 64 caracteres hexadecimales."""
    ruta = _crear_dataset(tmp_path)

    huella = calcular_sha256(ruta)

    assert len(huella) == 64
    assert all(caracter in "0123456789abcdef" for caracter in huella)


def test_sha256_archivo_vacio_v6(tmp_path) -> None:
    """También puede identificarse correctamente un archivo vacío."""
    ruta = tmp_path / "vacio.csv"
    ruta.write_bytes(b"")

    esperado = hashlib.sha256(b"").hexdigest()

    assert calcular_sha256(ruta) == esperado


def test_sha256_archivo_mayor_que_un_bloque_v6(tmp_path) -> None:
    """El cálculo por bloques conserva la huella de archivos mayores."""
    contenido = b"A" * (HASH_BLOCK_SIZE + 137)
    ruta = tmp_path / "grande.bin"
    ruta.write_bytes(contenido)

    esperado = hashlib.sha256(contenido).hexdigest()

    assert calcular_sha256(ruta) == esperado


def test_sha256_mismo_contenido_misma_huella_v6(tmp_path) -> None:
    """Dos archivos con contenido idéntico producen la misma huella."""
    contenido = b"id,nombre\n1,Ana\n"

    ruta_1 = tmp_path / "uno.csv"
    ruta_2 = tmp_path / "dos.csv"

    ruta_1.write_bytes(contenido)
    ruta_2.write_bytes(contenido)

    assert calcular_sha256(ruta_1) == calcular_sha256(ruta_2)


def test_sha256_contenido_distinto_huella_distinta_v6(tmp_path) -> None:
    """Una modificación del contenido cambia la identificación SHA-256."""
    ruta_1 = tmp_path / "uno.csv"
    ruta_2 = tmp_path / "dos.csv"

    ruta_1.write_bytes(b"a,b\n1,2\n")
    ruta_2.write_bytes(b"a,b\n1,3\n")

    assert calcular_sha256(ruta_1) != calcular_sha256(ruta_2)


def test_sha256_no_depende_del_nombre_archivo_v6(tmp_path) -> None:
    """La huella representa contenido, no nombre ni ruta."""
    contenido = b"a,b\n1,2\n"

    ruta_1 = tmp_path / "original.csv"
    ruta_2 = tmp_path / "copia.xlsx"

    ruta_1.write_bytes(contenido)
    ruta_2.write_bytes(contenido)

    assert calcular_sha256(ruta_1) == calcular_sha256(ruta_2)


def test_calcular_sha256_archivo_inexistente_es_rechazado_v6(
    tmp_path,
) -> None:
    """No se calcula una huella para un archivo inexistente."""
    with pytest.raises(ReproducibilityError):
        calcular_sha256(tmp_path / "no_existe.csv")


def test_manifiesto_incorpora_sha256_v6(tmp_path) -> None:
    """La referencia del dataset incluye su huella exacta."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto.dataset.sha256 == calcular_sha256(ruta)


def test_manifiesto_sha256_cambia_si_cambia_dataset_v6(tmp_path) -> None:
    """Dos contenidos distintos producen manifiestos con huellas distintas."""
    ruta = _crear_dataset(
        tmp_path,
        contenido="a,b\n1,2\n",
    )

    manifiesto_1 = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    ruta.write_text(
        "a,b\n1,3\n",
        encoding="utf-8",
    )

    manifiesto_2 = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    assert manifiesto_1.dataset.sha256 != manifiesto_2.dataset.sha256


def test_manifiesto_conserva_sha256_aunque_archivo_cambie_v6(
    tmp_path,
) -> None:
    """La referencia conserva la huella capturada al crear el manifiesto."""
    ruta = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        ruta,
        created_at=FECHA_PRUEBA,
    )

    huella_original = manifiesto.dataset.sha256

    ruta.write_text(
        "contenido modificado",
        encoding="utf-8",
    )

    assert manifiesto.dataset.sha256 == huella_original
    assert calcular_sha256(ruta) != huella_original