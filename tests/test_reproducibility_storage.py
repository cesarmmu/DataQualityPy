"""Tests de persistencia y verificación reproducible de DataQualityPy V6."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cleaning_plan import CleaningOperation, CleaningPlan
from src.reproducibility import (
    DatasetVerificationStatus,
    LEGACY_MANIFEST_FORMAT_VERSION,
    RuntimeEnvironment,
    VerificationStatus,
    ExecutionManifest,
    ReproducibilityError,
    cargar_manifiesto,
    crear_manifiesto,
    guardar_manifiesto,
    manifiesto_desde_dict,
    reconstruir_plan_manifiesto,
    verificar_dataset,
    verificar_reproducibilidad,
)


def _crear_dataset(
    tmp_path: Path,
    nombre: str = "datos.csv",
    contenido: str = "id,nombre\n1,Ana\n2,Luis\n",
) -> Path:
    """Crea un dataset temporal para las pruebas."""
    ruta = tmp_path / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _crear_manifiesto_basico(
    tmp_path: Path,
) -> tuple[Path, ExecutionManifest]:
    """Crea un dataset y su manifiesto reproducible."""
    dataset = _crear_dataset(tmp_path)

    manifiesto = crear_manifiesto(
        dataset,
        created_at="2026-10-14T10:00:00+02:00",
    )

    return dataset, manifiesto


def _crear_plan() -> CleaningPlan:
    """Crea un plan sencillo reutilizable."""
    plan = CleaningPlan()

    operacion = CleaningOperation(
        familia="texto",
        tipo="eliminar_espacios_externos",
        columna="nombre",
        parametros={},
    )

    plan.agregar_operacion(operacion)

    return plan


def test_manifiesto_desde_dict_reconstruye_manifiesto_v6(
    tmp_path: Path,
) -> None:
    _, original = _crear_manifiesto_basico(tmp_path)

    reconstruido = manifiesto_desde_dict(
        original.a_dict()
    )

    assert reconstruido.a_dict() == original.a_dict()


def test_manifiesto_desde_dict_requiere_diccionario_v6() -> None:
    with pytest.raises(
        ReproducibilityError,
        match="objeto JSON",
    ):
        manifiesto_desde_dict("no es un diccionario")


def test_manifiesto_desde_dict_rechaza_campo_faltante_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    del datos["created_at"]

    with pytest.raises(
        ReproducibilityError,
        match="estructura esperada",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_campo_extra_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["extra"] = True

    with pytest.raises(
        ReproducibilityError,
        match="estructura esperada",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_version_incompatible_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["format_version"] = "99.0"

    with pytest.raises(
        ReproducibilityError,
        match="no compatible",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_dataset_no_dict_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["dataset"] = "datos.csv"

    with pytest.raises(
        ReproducibilityError,
        match="objeto JSON",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_campo_dataset_faltante_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    del datos["dataset"]["sha256"]

    with pytest.raises(
        ReproducibilityError,
        match="estructura esperada",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_campo_dataset_extra_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["dataset"]["ruta"] = "C:/datos.csv"

    with pytest.raises(
        ReproducibilityError,
        match="estructura esperada",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_sha256_invalido_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["dataset"]["sha256"] = "no-es-un-hash"

    with pytest.raises(
        ReproducibilityError,
        match="sha256",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_tamano_negativo_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["dataset"]["file_size"] = -1

    with pytest.raises(
        ReproducibilityError,
        match="negativo",
    ):
        manifiesto_desde_dict(datos)


def test_manifiesto_desde_dict_rechaza_extension_invalida_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    datos = manifiesto.a_dict()
    datos["dataset"]["file_extension"] = "csv"

    with pytest.raises(
        ReproducibilityError,
        match="comenzar por",
    ):
        manifiesto_desde_dict(datos)


def test_guardar_manifiesto_crea_json_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    destino = tmp_path / "manifiestos" / "ejecucion.json"

    resultado = guardar_manifiesto(
        destino,
        manifiesto,
    )

    assert resultado == destino
    assert destino.is_file()


def test_guardar_manifiesto_conserva_contenido_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    destino = tmp_path / "ejecucion.json"

    guardar_manifiesto(
        destino,
        manifiesto,
    )

    datos = json.loads(
        destino.read_text(encoding="utf-8")
    )

    assert datos == manifiesto.a_dict()


def test_guardar_manifiesto_utiliza_utf8_v6(
    tmp_path: Path,
) -> None:
    dataset = _crear_dataset(
        tmp_path,
        nombre="información.csv",
    )

    manifiesto = crear_manifiesto(
        dataset,
        created_at="2026-10-14T10:00:00+02:00",
    )

    destino = tmp_path / "ejecución.json"

    guardar_manifiesto(
        destino,
        manifiesto,
    )

    texto = destino.read_text(encoding="utf-8")

    assert "información.csv" in texto


def test_guardar_manifiesto_requiere_extension_json_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    with pytest.raises(
        ReproducibilityError,
        match="extensión '.json'",
    ):
        guardar_manifiesto(
            tmp_path / "ejecucion.txt",
            manifiesto,
        )


def test_guardar_requiere_execution_manifest_v6(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ReproducibilityError,
        match="ExecutionManifest",
    ):
        guardar_manifiesto(
            tmp_path / "ejecucion.json",
            "manifiesto",  # type: ignore[arg-type]
        )


def test_cargar_manifiesto_recupera_contenido_v6(
    tmp_path: Path,
) -> None:
    _, original = _crear_manifiesto_basico(tmp_path)

    destino = tmp_path / "ejecucion.json"

    guardar_manifiesto(
        destino,
        original,
    )

    cargado = cargar_manifiesto(destino)

    assert cargado.a_dict() == original.a_dict()


def test_cargar_manifiesto_inexistente_v6(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ReproducibilityError,
        match="No se ha encontrado",
    ):
        cargar_manifiesto(
            tmp_path / "inexistente.json"
        )


def test_cargar_manifiesto_requiere_extension_json_v6(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ReproducibilityError,
        match="extensión '.json'",
    ):
        cargar_manifiesto(
            tmp_path / "ejecucion.txt"
        )


def test_cargar_manifiesto_rechaza_json_invalido_v6(
    tmp_path: Path,
) -> None:
    ruta = tmp_path / "invalido.json"
    ruta.write_text(
        "{contenido inválido",
        encoding="utf-8",
    )

    with pytest.raises(
        ReproducibilityError,
        match="JSON válido",
    ):
        cargar_manifiesto(ruta)


def test_manifiesto_persistido_con_plan_se_recupera_v6(
    tmp_path: Path,
) -> None:
    dataset = _crear_dataset(tmp_path)
    plan = _crear_plan()

    original = crear_manifiesto(
        dataset,
        cleaning_plan=plan,
        cleaning_plan_name="Plan nombres",
        created_at="2026-10-14T10:00:00+02:00",
    )

    destino = tmp_path / "ejecucion.json"

    guardar_manifiesto(
        destino,
        original,
    )

    cargado = cargar_manifiesto(destino)

    assert cargado.cleaning_plan is not None
    assert cargado.cleaning_plan.name == "Plan nombres"
    assert len(cargado.cleaning_plan.operations) == 1


def test_reconstruir_plan_manifiesto_sin_plan_devuelve_none_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    assert reconstruir_plan_manifiesto(
        manifiesto
    ) is None


def test_reconstruir_plan_manifiesto_recupera_operaciones_v6(
    tmp_path: Path,
) -> None:
    dataset = _crear_dataset(tmp_path)
    plan_original = _crear_plan()

    manifiesto = crear_manifiesto(
        dataset,
        cleaning_plan=plan_original,
        cleaning_plan_name="Plan reutilizable",
        created_at="2026-10-14T10:00:00+02:00",
    )

    reconstruido = reconstruir_plan_manifiesto(
        manifiesto
    )

    assert reconstruido is not None
    assert len(reconstruido.operaciones) == 1

    operacion = reconstruido.operaciones[0]

    assert operacion.familia == "texto"
    assert operacion.tipo == "eliminar_espacios_externos"
    assert operacion.columna == "nombre"


def test_reconstruir_plan_genera_ids_nuevos_v6(
    tmp_path: Path,
) -> None:
    dataset = _crear_dataset(tmp_path)
    plan_original = _crear_plan()

    id_original = plan_original.operaciones[0].id

    manifiesto = crear_manifiesto(
        dataset,
        cleaning_plan=plan_original,
        cleaning_plan_name="Plan reutilizable",
        created_at="2026-10-14T10:00:00+02:00",
    )

    reconstruido = reconstruir_plan_manifiesto(
        manifiesto
    )

    assert reconstruido is not None
    assert reconstruido.operaciones[0].id != id_original


def test_verificar_dataset_coincidente_v6(
    tmp_path: Path,
) -> None:
    dataset, manifiesto = _crear_manifiesto_basico(tmp_path)

    verificacion = verificar_dataset(
        dataset,
        manifiesto,
    )

    assert verificacion.status is DatasetVerificationStatus.MATCH
    assert verificacion.matches is True
    assert verificacion.expected_size == verificacion.actual_size
    assert (
        verificacion.expected_sha256
        == verificacion.actual_sha256
    )


def test_verificar_dataset_mismo_contenido_otro_nombre_v6(
    tmp_path: Path,
) -> None:
    dataset, manifiesto = _crear_manifiesto_basico(tmp_path)

    copia = tmp_path / "copia.csv"
    copia.write_bytes(dataset.read_bytes())

    verificacion = verificar_dataset(
        copia,
        manifiesto,
    )

    assert verificacion.status is DatasetVerificationStatus.MATCH
    assert verificacion.matches is True


def test_verificar_dataset_modificado_v6(
    tmp_path: Path,
) -> None:
    dataset, manifiesto = _crear_manifiesto_basico(tmp_path)

    dataset.write_text(
        "id,nombre\n1,Ana\n2,Luis\n3,Marta\n",
        encoding="utf-8",
    )

    verificacion = verificar_dataset(
        dataset,
        manifiesto,
    )

    assert verificacion.status is DatasetVerificationStatus.MISMATCH
    assert verificacion.matches is False
    assert (
        verificacion.actual_sha256
        != verificacion.expected_sha256
    )


def test_verificar_dataset_mismo_tamano_contenido_distinto_v6(
    tmp_path: Path,
) -> None:
    dataset = _crear_dataset(
        tmp_path,
        contenido="ABCDEF",
    )

    manifiesto = crear_manifiesto(
        dataset,
        created_at="2026-10-14T10:00:00+02:00",
    )

    dataset.write_text(
        "UVWXYZ",
        encoding="utf-8",
    )

    verificacion = verificar_dataset(
        dataset,
        manifiesto,
    )

    assert verificacion.actual_size == verificacion.expected_size
    assert verificacion.status is DatasetVerificationStatus.MISMATCH
    assert verificacion.matches is False


def test_verificar_dataset_inexistente_v6(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)

    with pytest.raises(
        ReproducibilityError,
        match="No se ha encontrado",
    ):
        verificar_dataset(
            tmp_path / "inexistente.csv",
            manifiesto,
        )


def test_verificar_requiere_manifiesto_valido_v6(
    tmp_path: Path,
) -> None:
    dataset = _crear_dataset(tmp_path)

    with pytest.raises(
        ReproducibilityError,
        match="ExecutionManifest",
    ):
        verificar_dataset(
            dataset,
            "manifiesto",  # type: ignore[arg-type]
        )

def test_cargar_manifiesto_v6_sigue_siendo_compatible(tmp_path: Path) -> None:
    _, actual = _crear_manifiesto_basico(tmp_path)
    datos = actual.a_dict()
    datos["format_version"] = LEGACY_MANIFEST_FORMAT_VERSION
    datos.pop("environment")
    cargado = manifiesto_desde_dict(datos)
    assert cargado.format_version == LEGACY_MANIFEST_FORMAT_VERSION
    assert cargado.environment is None
    assert "environment" not in cargado.a_dict()


def test_verificacion_reproducible_todo_coincide_v7(tmp_path: Path) -> None:
    dataset = _crear_dataset(tmp_path)
    plan = _crear_plan()
    manifiesto = crear_manifiesto(
        dataset, cleaning_plan=plan, cleaning_plan_name="Plan",
        created_at="2026-10-14T10:00:00+02:00",
    )
    resultado = verificar_reproducibilidad(
        manifiesto, dataset_path=dataset, audit_configuration={},
        cleaning_plan=plan, environment=manifiesto.environment,
    )
    assert resultado.dataset.status is VerificationStatus.MATCH
    assert resultado.audit_configuration.status is VerificationStatus.MATCH
    assert resultado.cleaning_plan.status is VerificationStatus.MATCH
    assert resultado.environment.status is VerificationStatus.MATCH
    assert resultado.matches is True


def test_verificacion_reproducible_detecta_diferencias_v7(tmp_path: Path) -> None:
    dataset = _crear_dataset(tmp_path)
    manifiesto = crear_manifiesto(
        dataset, audit_configuration={"factor_iqr": 2.0},
        created_at="2026-10-14T10:00:00+02:00",
    )
    dataset.write_text("id,nombre\n1,Ana\n3,Marta\n", encoding="utf-8")
    entorno_distinto = RuntimeEnvironment(
        dataqualitypy="0.0.0", python="0.0.0", packages={}
    )
    resultado = verificar_reproducibilidad(
        manifiesto, dataset_path=dataset, audit_configuration={},
        cleaning_plan=None, environment=entorno_distinto,
    )
    assert resultado.dataset.status is VerificationStatus.MISMATCH
    assert resultado.audit_configuration.status is VerificationStatus.MISMATCH
    assert resultado.cleaning_plan.status is VerificationStatus.MATCH
    assert resultado.environment.status is VerificationStatus.MISMATCH
    assert resultado.matches is False


def test_verificacion_reproducible_no_infiere_contexto_ausente_v7(
    tmp_path: Path,
) -> None:
    _, manifiesto = _crear_manifiesto_basico(tmp_path)
    resultado = verificar_reproducibilidad(manifiesto)
    assert resultado.dataset.status is VerificationStatus.UNAVAILABLE
    assert resultado.audit_configuration.status is VerificationStatus.UNAVAILABLE
    assert resultado.cleaning_plan.status is VerificationStatus.UNAVAILABLE


def test_manifiesto_v6_entorno_no_disponible_v7(tmp_path: Path) -> None:
    _, actual = _crear_manifiesto_basico(tmp_path)
    datos = actual.a_dict()
    datos["format_version"] = LEGACY_MANIFEST_FORMAT_VERSION
    datos.pop("environment")
    legado = manifiesto_desde_dict(datos)
    resultado = verificar_reproducibilidad(legado)
    assert resultado.environment.status is VerificationStatus.UNAVAILABLE
