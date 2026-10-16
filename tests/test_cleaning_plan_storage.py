"""Tests de planes reutilizables de limpieza de DataQualityPy V6.2.4."""

import json

import pytest

from src.cleaning_plan import CleaningPlan
from src.cleaning_plan_storage import (
    FORMATO_PLAN_VERSION,
    CleaningPlanStorageError,
    StoredCleaningPlan,
    cargar_plan,
    cargar_plan_almacenado,
    crear_plan_almacenado,
    guardar_plan,
    plan_almacenado_desde_dict,
    reconstruir_plan,
)


FECHA_PRUEBA = "2026-10-14T10:00:00+02:00"


def _crear_plan_prueba() -> CleaningPlan:
    """Construye un plan representativo para los tests."""
    plan = CleaningPlan()

    plan.crear_operacion(
        familia="texto",
        tipo="eliminar_espacios_externos",
        columna="nombre",
    )

    plan.crear_operacion(
        familia="conversion",
        tipo="numerico",
        columna="importe",
    )

    plan.crear_operacion(
        familia="nulos",
        tipo="reemplazar_valor",
        columna="edad",
        parametros={"valor": 0},
    )

    plan.crear_operacion(
        familia="duplicados",
        tipo="eliminar_duplicados_completos",
        parametros={"conservar": "primero"},
    )

    return plan


def test_crear_plan_almacenado_v6() -> None:
    """Un CleaningPlan puede convertirse a representación persistente."""
    plan = _crear_plan_prueba()

    almacenado = crear_plan_almacenado(
        plan,
        "Plan de prueba",
        created_at=FECHA_PRUEBA,
    )

    assert isinstance(almacenado, StoredCleaningPlan)
    assert almacenado.format_version == FORMATO_PLAN_VERSION
    assert almacenado.name == "Plan de prueba"
    assert almacenado.created_at == FECHA_PRUEBA
    assert len(almacenado.operations) == 4


def test_formato_persistente_no_guarda_ids_internos_v6() -> None:
    """El formato reutilizable no conserva identificadores de operaciones."""
    plan = _crear_plan_prueba()

    almacenado = crear_plan_almacenado(
        plan,
        "Plan sin IDs",
        created_at=FECHA_PRUEBA,
    )

    datos = almacenado.a_dict()

    for operacion in datos["operations"]:
        assert set(operacion) == {
            "family",
            "type",
            "column",
            "parameters",
        }
        assert "id" not in operacion
        assert "orden_ejecucion" not in operacion


def test_serializacion_conserva_definicion_operaciones_v6() -> None:
    """La persistencia conserva familia, tipo, columna y parámetros."""
    plan = _crear_plan_prueba()

    almacenado = crear_plan_almacenado(
        plan,
        "Plan",
        created_at=FECHA_PRUEBA,
    )

    operaciones = almacenado.a_dict()["operations"]

    assert operaciones[0] == {
        "family": "texto",
        "type": "eliminar_espacios_externos",
        "column": "nombre",
        "parameters": {},
    }

    assert operaciones[-1] == {
        "family": "duplicados",
        "type": "eliminar_duplicados_completos",
        "column": None,
        "parameters": {"conservar": "primero"},
    }


def test_reconstruir_plan_genera_nuevos_ids_v6() -> None:
    """Un plan reutilizado recibe identificadores nuevos."""
    original = _crear_plan_prueba()

    almacenado = crear_plan_almacenado(
        original,
        "Plan",
        created_at=FECHA_PRUEBA,
    )

    reconstruido = reconstruir_plan(almacenado)

    ids_originales = {
        operacion.id
        for operacion in original.operaciones_ordenadas()
    }

    ids_nuevos = {
        operacion.id
        for operacion in reconstruido.operaciones_ordenadas()
    }

    assert ids_originales.isdisjoint(ids_nuevos)


def test_reconstruccion_conserva_operaciones_v6() -> None:
    """La reconstrucción conserva la definición funcional del plan."""
    original = _crear_plan_prueba()

    almacenado = crear_plan_almacenado(
        original,
        "Plan",
        created_at=FECHA_PRUEBA,
    )

    reconstruido = reconstruir_plan(almacenado)

    originales = original.operaciones_ordenadas()
    nuevas = reconstruido.operaciones_ordenadas()

    assert len(originales) == len(nuevas)

    for anterior, nueva in zip(originales, nuevas, strict=True):
        assert anterior.familia == nueva.familia
        assert anterior.tipo == nueva.tipo
        assert anterior.columna == nueva.columna
        assert anterior.parametros == nueva.parametros


def test_reconstruccion_devuelve_nuevo_plan_v6() -> None:
    """La carga nunca devuelve la misma instancia del plan original."""
    original = _crear_plan_prueba()

    almacenado = crear_plan_almacenado(
        original,
        "Plan",
        created_at=FECHA_PRUEBA,
    )

    reconstruido = reconstruir_plan(almacenado)

    assert reconstruido is not original
    assert isinstance(reconstruido, CleaningPlan)


def test_plan_vacio_puede_guardarse_y_reconstruirse_v6() -> None:
    """Un plan vacío sigue siendo una definición reutilizable válida."""
    plan = CleaningPlan()

    almacenado = crear_plan_almacenado(
        plan,
        "Plan vacío",
        created_at=FECHA_PRUEBA,
    )

    reconstruido = reconstruir_plan(almacenado)

    assert almacenado.operations == ()
    assert reconstruido.esta_vacio()


def test_nombre_se_normaliza_v6() -> None:
    """Los espacios externos del nombre no forman parte del plan."""
    almacenado = crear_plan_almacenado(
        CleaningPlan(),
        "  Limpieza clientes  ",
        created_at=FECHA_PRUEBA,
    )

    assert almacenado.name == "Limpieza clientes"


def test_nombre_vacio_es_invalido_v6() -> None:
    """Un plan reutilizable necesita un nombre descriptivo."""
    with pytest.raises(CleaningPlanStorageError):
        crear_plan_almacenado(
            CleaningPlan(),
            "   ",
            created_at=FECHA_PRUEBA,
        )


def test_fecha_iso_invalida_es_rechazada_v6() -> None:
    """La fecha persistida debe ser ISO 8601."""
    with pytest.raises(CleaningPlanStorageError):
        crear_plan_almacenado(
            CleaningPlan(),
            "Plan",
            created_at="14/10/2026",
        )


def test_plan_invalido_es_rechazado_v6() -> None:
    """La serialización exige un CleaningPlan real."""
    with pytest.raises(CleaningPlanStorageError):
        crear_plan_almacenado(
            None,  # type: ignore[arg-type]
            "Plan",
            created_at=FECHA_PRUEBA,
        )


def test_plan_desde_dict_valido_v6() -> None:
    """Una estructura JSON válida se convierte en StoredCleaningPlan."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan externo",
        "created_at": FECHA_PRUEBA,
        "operations": [
            {
                "family": "texto",
                "type": "minusculas",
                "column": "ciudad",
                "parameters": {},
            }
        ],
    }

    almacenado = plan_almacenado_desde_dict(datos)

    assert almacenado.name == "Plan externo"
    assert len(almacenado.operations) == 1
    assert almacenado.operations[0]["type"] == "minusculas"


def test_version_incompatible_es_rechazada_v6() -> None:
    """No se cargan silenciosamente formatos desconocidos."""
    datos = {
        "format_version": "99.0",
        "name": "Plan",
        "created_at": FECHA_PRUEBA,
        "operations": [],
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_campo_principal_faltante_es_rechazado_v6() -> None:
    """El documento debe contener todos los campos del formato."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan",
        "operations": [],
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_campo_principal_extra_es_rechazado_v6() -> None:
    """El formato no acepta metadatos desconocidos silenciosamente."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan",
        "created_at": FECHA_PRUEBA,
        "operations": [],
        "extra": True,
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_operacion_con_campo_faltante_es_rechazada_v6() -> None:
    """Cada operación debe contener su definición completa."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan",
        "created_at": FECHA_PRUEBA,
        "operations": [
            {
                "family": "texto",
                "type": "minusculas",
                "column": "nombre",
            }
        ],
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_operacion_con_campo_extra_es_rechazada_v6() -> None:
    """Los IDs internos no pueden infiltrarse en el formato persistente."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan",
        "created_at": FECHA_PRUEBA,
        "operations": [
            {
                "family": "texto",
                "type": "minusculas",
                "column": "nombre",
                "parameters": {},
                "id": "id-antiguo",
            }
        ],
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_parameters_debe_ser_diccionario_v6() -> None:
    """Los parámetros de una operación deben tener estructura de objeto."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan",
        "created_at": FECHA_PRUEBA,
        "operations": [
            {
                "family": "texto",
                "type": "minusculas",
                "column": "nombre",
                "parameters": [],
            }
        ],
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_operations_debe_ser_lista_v6() -> None:
    """El documento JSON representa las operaciones mediante una lista."""
    datos = {
        "format_version": FORMATO_PLAN_VERSION,
        "name": "Plan",
        "created_at": FECHA_PRUEBA,
        "operations": {},
    }

    with pytest.raises(CleaningPlanStorageError):
        plan_almacenado_desde_dict(datos)


def test_operacion_invalida_es_rechazada_al_reconstruir_v6() -> None:
    """La reconstrucción vuelve a validar las reglas de CleaningPlan."""
    almacenado = StoredCleaningPlan(
        format_version=FORMATO_PLAN_VERSION,
        name="Plan inválido",
        created_at=FECHA_PRUEBA,
        operations=(
            {
                "family": "texto",
                "type": "operacion_inexistente",
                "column": "nombre",
                "parameters": {},
            },
        ),
    )

    with pytest.raises(CleaningPlanStorageError):
        reconstruir_plan(almacenado)


def test_guardar_y_cargar_plan_json_v6(tmp_path) -> None:
    """Un plan puede completar el ciclo real guardar-cargar."""
    original = _crear_plan_prueba()
    ruta = tmp_path / "plan_clientes.json"

    guardada = guardar_plan(
        ruta,
        original,
        "Plan clientes",
        created_at=FECHA_PRUEBA,
    )

    cargado = cargar_plan(ruta)

    assert guardada == ruta
    assert ruta.exists()
    assert len(cargado) == len(original)

    originales = original.operaciones_ordenadas()
    cargadas = cargado.operaciones_ordenadas()

    for anterior, nueva in zip(originales, cargadas, strict=True):
        assert anterior.familia == nueva.familia
        assert anterior.tipo == nueva.tipo
        assert anterior.columna == nueva.columna
        assert anterior.parametros == nueva.parametros
        assert anterior.id != nueva.id


def test_archivo_json_contiene_formato_publico_v6(tmp_path) -> None:
    """El archivo físico contiene solo el contrato persistente definido."""
    plan = _crear_plan_prueba()
    ruta = tmp_path / "plan.json"

    guardar_plan(
        ruta,
        plan,
        "Plan",
        created_at=FECHA_PRUEBA,
    )

    datos = json.loads(
        ruta.read_text(encoding="utf-8")
    )

    assert set(datos) == {
        "format_version",
        "name",
        "created_at",
        "operations",
    }

    for operacion in datos["operations"]:
        assert "id" not in operacion
        assert "orden_ejecucion" not in operacion


def test_cargar_plan_almacenado_conserva_metadatos_v6(tmp_path) -> None:
    """Puede recuperarse la definición persistente sin reconstruir aún."""
    ruta = tmp_path / "plan.json"

    guardar_plan(
        ruta,
        CleaningPlan(),
        "Plan mensual",
        created_at=FECHA_PRUEBA,
    )

    almacenado = cargar_plan_almacenado(ruta)

    assert almacenado.name == "Plan mensual"
    assert almacenado.created_at == FECHA_PRUEBA
    assert almacenado.format_version == FORMATO_PLAN_VERSION


def test_extension_guardado_debe_ser_json_v6(tmp_path) -> None:
    """Los planes reutilizables se almacenan únicamente como JSON."""
    ruta = tmp_path / "plan.txt"

    with pytest.raises(CleaningPlanStorageError):
        guardar_plan(
            ruta,
            CleaningPlan(),
            "Plan",
            created_at=FECHA_PRUEBA,
        )


def test_extension_carga_debe_ser_json_v6(tmp_path) -> None:
    """La carga exige el formato físico previsto."""
    ruta = tmp_path / "plan.txt"
    ruta.write_text("{}", encoding="utf-8")

    with pytest.raises(CleaningPlanStorageError):
        cargar_plan(ruta)


def test_json_corrupto_es_rechazado_v6(tmp_path) -> None:
    """Un archivo JSON sintácticamente incorrecto produce error controlado."""
    ruta = tmp_path / "plan.json"
    ruta.write_text(
        "{contenido incorrecto",
        encoding="utf-8",
    )

    with pytest.raises(CleaningPlanStorageError):
        cargar_plan(ruta)


def test_archivo_inexistente_es_rechazado_v6(tmp_path) -> None:
    """La ausencia del archivo produce un error de almacenamiento controlado."""
    ruta = tmp_path / "no_existe.json"

    with pytest.raises(CleaningPlanStorageError):
        cargar_plan(ruta)