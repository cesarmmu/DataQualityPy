"""Reproducibilidad de ejecuciones de DataQualityPy V6.

Este módulo define el manifiesto reproducible de una ejecución.

El manifiesto conserva:
- metadatos básicos de la ejecución;
- identificación del dataset de origen;
- huella SHA-256 del contenido del dataset;
- configuración efectiva del auditor;
- definición reutilizable opcional del plan de limpieza.

Este módulo:
- no ejecuta auditorías;
- no ejecuta planes de limpieza;
- no modifica datasets;
- no almacena resultados completos de auditoría;
- no implica ejecución automática al recuperar un manifiesto.

La huella SHA-256 se utiliza exclusivamente para identificar de forma estable
el contenido del dataset y comprobar posteriormente si un archivo conserva
exactamente el mismo contenido. No se utiliza como mecanismo de seguridad.
"""

from __future__ import annotations

import hashlib
import json
import sys
from importlib import metadata
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from src import __version__
from src.cleaning_plan import CleaningPlan
from src.cleaning_plan_storage import (
    StoredCleaningPlan,
    crear_plan_almacenado,
    plan_almacenado_desde_dict,
    reconstruir_plan,
)
from src.config import ErrorConfiguracion, cargar_configuracion


LEGACY_MANIFEST_FORMAT_VERSION = "1.0"
MANIFEST_FORMAT_VERSION = "2.0"
SUPPORTED_MANIFEST_FORMAT_VERSIONS = {LEGACY_MANIFEST_FORMAT_VERSION, MANIFEST_FORMAT_VERSION}
DATAQUALITYPY_VERSION = __version__
RELEVANT_PACKAGES = ("pandas", "numpy", "openpyxl", "streamlit")
HASH_ALGORITHM = "sha256"
HASH_BLOCK_SIZE = 1024 * 1024


class ReproducibilityError(ValueError):
    """Error al construir o validar información reproducible."""


class DatasetVerificationStatus(Enum):
    """Resultado de verificar un dataset frente a un manifiesto."""

    MATCH = "coincide"
    MISMATCH = "no_coincide"


class VerificationStatus(Enum):
    """Estado común de una comparación reproducible V7."""

    MATCH = "coincide"
    MISMATCH = "diferente"
    UNAVAILABLE = "no_disponible"


@dataclass(frozen=True)
class RuntimeEnvironment:
    """Versiones mínimas necesarias para interpretar una ejecución."""

    dataqualitypy: str
    python: str
    packages: Mapping[str, str]

    def a_dict(self) -> dict[str, Any]:
        return {
            "dataqualitypy": self.dataqualitypy,
            "python": self.python,
            "packages": dict(self.packages),
        }


@dataclass(frozen=True)
class ComponentVerification:
    """Comparación de un componente del contexto reproducible."""

    status: VerificationStatus
    expected: Any = None
    actual: Any = None
    detail: str = ""

    @property
    def matches(self) -> bool:
        return self.status is VerificationStatus.MATCH


@dataclass(frozen=True)
class ReproducibilityVerification:
    """Resultado global, explicable y no ejecutivo de reproducibilidad."""

    dataset: ComponentVerification
    audit_configuration: ComponentVerification
    cleaning_plan: ComponentVerification
    environment: ComponentVerification

    @property
    def matches(self) -> bool:
        componentes = (
            self.dataset,
            self.audit_configuration,
            self.cleaning_plan,
            self.environment,
        )
        disponibles = [
            item for item in componentes
            if item.status is not VerificationStatus.UNAVAILABLE
        ]
        return bool(disponibles) and all(item.matches for item in disponibles)


@dataclass(frozen=True)
class DatasetReference:
    """Identificación reproducible del dataset utilizado en una ejecución."""

    file_name: str
    file_extension: str
    file_size: int
    sha256: str

    def a_dict(self) -> dict[str, Any]:
        """Devuelve una representación serializable."""
        return {
            "file_name": self.file_name,
            "file_extension": self.file_extension,
            "file_size": self.file_size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class ExecutionManifest:
    """Manifiesto reproducible de una ejecución de DataQualityPy."""

    format_version: str
    created_at: str
    dataset: DatasetReference
    audit_configuration: Mapping[str, Any]
    cleaning_plan: StoredCleaningPlan | None = None
    environment: RuntimeEnvironment | None = None

    def a_dict(self) -> dict[str, Any]:
        """Devuelve el manifiesto como estructura serializable."""
        datos = {
            "format_version": self.format_version,
            "created_at": self.created_at,
            "dataset": self.dataset.a_dict(),
            "audit_configuration": _copiar_configuracion(
                self.audit_configuration
            ),
            "cleaning_plan": (
                self.cleaning_plan.a_dict()
                if self.cleaning_plan is not None
                else None
            ),
        }
        if self.format_version != LEGACY_MANIFEST_FORMAT_VERSION:
            datos["environment"] = (
                self.environment.a_dict()
                if self.environment is not None
                else None
            )
        return datos


@dataclass(frozen=True)
class DatasetVerification:
    """Resultado detallado de verificar un dataset."""

    status: DatasetVerificationStatus
    expected_size: int
    actual_size: int
    expected_sha256: str
    actual_sha256: str

    @property
    def matches(self) -> bool:
        """Indica si el dataset coincide exactamente con el esperado."""
        return self.status is DatasetVerificationStatus.MATCH


def _copiar_configuracion(
    configuracion: Mapping[str, Any],
) -> dict[str, Any]:
    """Copia defensivamente la configuración reproducible."""
    copia = dict(configuracion)

    columnas_clave = copia.get("columnas_clave")
    if isinstance(columnas_clave, list):
        copia["columnas_clave"] = list(columnas_clave)

    tipos_columnas = copia.get("tipos_columnas")
    if isinstance(tipos_columnas, dict):
        copia["tipos_columnas"] = dict(tipos_columnas)

    reglas_columnas = copia.get("reglas_columnas")
    if isinstance(reglas_columnas, dict):
        copia["reglas_columnas"] = {
            columna: (
                {
                    regla: (
                        list(valor)
                        if isinstance(valor, list)
                        else valor
                    )
                    for regla, valor in reglas.items()
                }
                if isinstance(reglas, dict)
                else reglas
            )
            for columna, reglas in reglas_columnas.items()
        }

    return copia


def _validar_fecha_iso(fecha: str) -> str:
    """Valida una fecha ISO 8601."""
    if not isinstance(fecha, str) or not fecha.strip():
        raise ReproducibilityError(
            "'created_at' debe ser una cadena de texto no vacía."
        )

    valor = fecha.strip()

    try:
        datetime.fromisoformat(valor)
    except ValueError as exc:
        raise ReproducibilityError(
            "'created_at' debe utilizar un formato ISO 8601 válido."
        ) from exc

    return valor


def _validar_sha256(valor: Any) -> str:
    """Valida una huella SHA-256 hexadecimal."""
    if not isinstance(valor, str):
        raise ReproducibilityError(
            "'sha256' debe ser una cadena de texto."
        )

    sha256 = valor.strip().lower()

    if len(sha256) != 64:
        raise ReproducibilityError(
            "'sha256' debe contener 64 caracteres hexadecimales."
        )

    try:
        int(sha256, 16)
    except ValueError as exc:
        raise ReproducibilityError(
            "'sha256' debe ser una huella hexadecimal válida."
        ) from exc

    return sha256


def _validar_tamano_archivo(valor: Any) -> int:
    """Valida el tamaño persistido de un archivo."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ReproducibilityError(
            "'file_size' debe ser un número entero."
        )

    if valor < 0:
        raise ReproducibilityError(
            "'file_size' no puede ser negativo."
        )

    return valor


def _validar_nombre_archivo(valor: Any) -> str:
    """Valida el nombre persistido de un archivo."""
    if not isinstance(valor, str) or not valor.strip():
        raise ReproducibilityError(
            "'file_name' debe ser una cadena de texto no vacía."
        )

    return valor.strip()


def _validar_extension(valor: Any) -> str:
    """Valida la extensión persistida de un archivo."""
    if not isinstance(valor, str):
        raise ReproducibilityError(
            "'file_extension' debe ser una cadena de texto."
        )

    extension = valor.strip().lower()

    if extension and not extension.startswith("."):
        raise ReproducibilityError(
            "'file_extension' debe comenzar por '.'."
        )

    return extension


def calcular_sha256(dataset_path: str | Path) -> str:
    """Calcula la huella SHA-256 del contenido de un archivo."""
    ruta = Path(dataset_path)

    if not ruta.is_file():
        raise ReproducibilityError(
            f"No se ha encontrado el dataset de origen: '{ruta}'."
        )

    hash_archivo = hashlib.sha256()

    try:
        with ruta.open("rb") as archivo:
            while True:
                bloque = archivo.read(HASH_BLOCK_SIZE)

                if not bloque:
                    break

                hash_archivo.update(bloque)
    except OSError as exc:
        raise ReproducibilityError(
            f"No se pudo leer el dataset '{ruta}' para calcular "
            "su huella SHA-256."
        ) from exc

    return hash_archivo.hexdigest()


def _crear_referencia_dataset(
    dataset_path: str | Path,
) -> DatasetReference:
    """Construye la referencia reproducible de un archivo de origen."""
    ruta = Path(dataset_path)

    if not ruta.is_file():
        raise ReproducibilityError(
            f"No se ha encontrado el dataset de origen: '{ruta}'."
        )

    try:
        tamano = ruta.stat().st_size
    except OSError as exc:
        raise ReproducibilityError(
            f"No se pudo obtener información del dataset '{ruta}'."
        ) from exc

    sha256 = calcular_sha256(ruta)

    return DatasetReference(
        file_name=ruta.name,
        file_extension=ruta.suffix.lower(),
        file_size=tamano,
        sha256=sha256,
    )


def _dataset_reference_desde_dict(
    datos: Any,
) -> DatasetReference:
    """Reconstruye y valida una referencia de dataset persistida."""
    if not isinstance(datos, dict):
        raise ReproducibilityError(
            "'dataset' debe ser un objeto JSON."
        )

    campos_esperados = {
        "file_name",
        "file_extension",
        "file_size",
        "sha256",
    }

    campos_recibidos = set(datos)

    if campos_recibidos != campos_esperados:
        faltantes = campos_esperados - campos_recibidos
        extras = campos_recibidos - campos_esperados

        detalles: list[str] = []

        if faltantes:
            detalles.append(
                "faltan: " + ", ".join(sorted(faltantes))
            )

        if extras:
            detalles.append(
                "sobran: " + ", ".join(sorted(extras))
            )

        raise ReproducibilityError(
            "La referencia del dataset no tiene la estructura "
            f"esperada ({'; '.join(detalles)})."
        )

    return DatasetReference(
        file_name=_validar_nombre_archivo(
            datos["file_name"]
        ),
        file_extension=_validar_extension(
            datos["file_extension"]
        ),
        file_size=_validar_tamano_archivo(
            datos["file_size"]
        ),
        sha256=_validar_sha256(
            datos["sha256"]
        ),
    )


def _resolver_configuracion(
    audit_configuration: dict[str, Any] | None,
) -> dict[str, Any]:
    """Obtiene y valida la configuración efectiva del auditor."""
    try:
        configuracion = cargar_configuracion(
            configuracion_usuario=audit_configuration
        )
    except ErrorConfiguracion as exc:
        raise ReproducibilityError(
            f"La configuración de auditoría no es válida: {exc}"
        ) from exc

    return _copiar_configuracion(configuracion)


def _crear_plan_reproducible(
    cleaning_plan: CleaningPlan | None,
    cleaning_plan_name: str | None,
    created_at: str,
) -> StoredCleaningPlan | None:
    """Convierte opcionalmente un CleaningPlan a formato reutilizable."""
    if cleaning_plan is None:
        if cleaning_plan_name is not None:
            raise ReproducibilityError(
                "No puede indicarse 'cleaning_plan_name' sin un "
                "'cleaning_plan'."
            )
        return None

    if not isinstance(cleaning_plan, CleaningPlan):
        raise ReproducibilityError(
            "'cleaning_plan' debe ser una instancia de CleaningPlan."
        )

    if cleaning_plan_name is None:
        raise ReproducibilityError(
            "Debe indicarse 'cleaning_plan_name' cuando se incluye "
            "un plan de limpieza."
        )

    try:
        return crear_plan_almacenado(
            cleaning_plan,
            cleaning_plan_name,
            created_at=created_at,
        )
    except ValueError as exc:
        raise ReproducibilityError(
            f"No se pudo preparar el plan de limpieza: {exc}"
        ) from exc


def obtener_entorno_actual() -> RuntimeEnvironment:
    """Obtiene únicamente las versiones relevantes para reproducibilidad."""
    paquetes: dict[str, str] = {}
    for paquete in RELEVANT_PACKAGES:
        try:
            paquetes[paquete] = metadata.version(paquete)
        except metadata.PackageNotFoundError:
            paquetes[paquete] = "no_disponible"

    return RuntimeEnvironment(
        dataqualitypy=__version__,
        python=sys.version.split()[0],
        packages=paquetes,
    )


def _entorno_desde_dict(datos: Any) -> RuntimeEnvironment:
    """Reconstruye y valida el entorno mínimo persistido en V7."""
    if not isinstance(datos, dict):
        raise ReproducibilityError("'environment' debe ser un objeto JSON.")
    esperados = {"dataqualitypy", "python", "packages"}
    if set(datos) != esperados:
        raise ReproducibilityError(
            "El entorno no tiene la estructura esperada."
        )
    if not isinstance(datos["dataqualitypy"], str) or not datos["dataqualitypy"]:
        raise ReproducibilityError("La versión de DataQualityPy no es válida.")
    if not isinstance(datos["python"], str) or not datos["python"]:
        raise ReproducibilityError("La versión de Python no es válida.")
    if not isinstance(datos["packages"], dict):
        raise ReproducibilityError("'packages' debe ser un objeto JSON.")
    paquetes: dict[str, str] = {}
    for nombre, version in datos["packages"].items():
        if not isinstance(nombre, str) or not isinstance(version, str):
            raise ReproducibilityError("Las versiones de paquetes no son válidas.")
        paquetes[nombre] = version
    return RuntimeEnvironment(
        dataqualitypy=datos["dataqualitypy"],
        python=datos["python"],
        packages=paquetes,
    )


def crear_manifiesto(
    dataset_path: str | Path,
    *,
    audit_configuration: dict[str, Any] | None = None,
    cleaning_plan: CleaningPlan | None = None,
    cleaning_plan_name: str | None = None,
    created_at: str | None = None,
) -> ExecutionManifest:
    """Construye un manifiesto reproducible de una ejecución."""
    fecha = (
        datetime.now().astimezone().isoformat(timespec="seconds")
        if created_at is None
        else _validar_fecha_iso(created_at)
    )

    dataset = _crear_referencia_dataset(dataset_path)
    configuracion = _resolver_configuracion(audit_configuration)

    plan_almacenado = _crear_plan_reproducible(
        cleaning_plan,
        cleaning_plan_name,
        fecha,
    )

    return ExecutionManifest(
        format_version=MANIFEST_FORMAT_VERSION,
        created_at=fecha,
        dataset=dataset,
        audit_configuration=configuracion,
        cleaning_plan=plan_almacenado,
        environment=obtener_entorno_actual(),
    )


def manifiesto_desde_dict(
    datos: Any,
) -> ExecutionManifest:
    """Reconstruye manifiestos V6 (1.0) y V7 (2.0)."""
    if not isinstance(datos, dict):
        raise ReproducibilityError("El manifiesto debe ser un objeto JSON.")

    version = datos.get("format_version")
    if version not in SUPPORTED_MANIFEST_FORMAT_VERSIONS:
        raise ReproducibilityError(
            "Versión de manifiesto no compatible: "
            f"'{version}'. Versiones admitidas: "
            f"{', '.join(sorted(SUPPORTED_MANIFEST_FORMAT_VERSIONS))}."
        )

    campos_esperados = {
        "format_version", "created_at", "dataset",
        "audit_configuration", "cleaning_plan",
    }
    if version == MANIFEST_FORMAT_VERSION:
        campos_esperados.add("environment")

    campos_recibidos = set(datos)
    if campos_recibidos != campos_esperados:
        faltantes = campos_esperados - campos_recibidos
        extras = campos_recibidos - campos_esperados
        detalles: list[str] = []
        if faltantes:
            detalles.append("faltan: " + ", ".join(sorted(faltantes)))
        if extras:
            detalles.append("sobran: " + ", ".join(sorted(extras)))
        raise ReproducibilityError(
            "El manifiesto no tiene la estructura esperada "
            f"({'; '.join(detalles)})."
        )

    fecha = _validar_fecha_iso(datos["created_at"])
    dataset = _dataset_reference_desde_dict(datos["dataset"])
    configuracion_datos = datos["audit_configuration"]
    if not isinstance(configuracion_datos, dict):
        raise ReproducibilityError(
            "'audit_configuration' debe ser un objeto JSON."
        )
    try:
        configuracion = cargar_configuracion(
            configuracion_usuario=configuracion_datos
        )
    except ErrorConfiguracion as exc:
        raise ReproducibilityError(
            "La configuración almacenada en el manifiesto "
            f"no es válida: {exc}"
        ) from exc

    plan_datos = datos["cleaning_plan"]
    if plan_datos is None:
        plan = None
    else:
        try:
            plan = plan_almacenado_desde_dict(plan_datos)
        except ValueError as exc:
            raise ReproducibilityError(
                "El plan de limpieza almacenado en el manifiesto "
                f"no es válido: {exc}"
            ) from exc

    entorno = (
        None
        if version == LEGACY_MANIFEST_FORMAT_VERSION
        else _entorno_desde_dict(datos["environment"])
    )

    return ExecutionManifest(
        format_version=version,
        created_at=fecha,
        dataset=dataset,
        audit_configuration=_copiar_configuracion(configuracion),
        cleaning_plan=plan,
        environment=entorno,
    )

def guardar_manifiesto(
    ruta: str | Path,
    manifiesto: ExecutionManifest,
) -> Path:
    """Guarda un manifiesto reproducible en formato JSON."""
    if not isinstance(manifiesto, ExecutionManifest):
        raise ReproducibilityError(
            "'manifiesto' debe ser una instancia de "
            "ExecutionManifest."
        )

    destino = Path(ruta)

    if destino.suffix.lower() != ".json":
        raise ReproducibilityError(
            "El manifiesto debe guardarse con extensión '.json'."
        )

    try:
        destino.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with destino.open(
            "w",
            encoding="utf-8",
        ) as archivo:
            json.dump(
                manifiesto.a_dict(),
                archivo,
                ensure_ascii=False,
                indent=2,
            )
    except (OSError, TypeError) as exc:
        raise ReproducibilityError(
            f"No se pudo guardar el manifiesto en '{destino}'."
        ) from exc

    return destino


def cargar_manifiesto(
    ruta: str | Path,
) -> ExecutionManifest:
    """Carga y valida un manifiesto reproducible desde JSON."""
    origen = Path(ruta)

    if origen.suffix.lower() != ".json":
        raise ReproducibilityError(
            "El manifiesto debe tener extensión '.json'."
        )

    try:
        with origen.open(
            "r",
            encoding="utf-8",
        ) as archivo:
            datos = json.load(archivo)
    except FileNotFoundError as exc:
        raise ReproducibilityError(
            f"No se ha encontrado el manifiesto: '{origen}'."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ReproducibilityError(
            f"El archivo '{origen}' no contiene JSON válido."
        ) from exc
    except OSError as exc:
        raise ReproducibilityError(
            f"No se pudo leer el manifiesto '{origen}'."
        ) from exc

    return manifiesto_desde_dict(datos)


def reconstruir_plan_manifiesto(
    manifiesto: ExecutionManifest,
) -> CleaningPlan | None:
    """Reconstruye conscientemente el plan almacenado.

    Esta función únicamente reconstruye el objeto CleaningPlan.
    No simula ni ejecuta ninguna operación de limpieza.
    """
    if not isinstance(manifiesto, ExecutionManifest):
        raise ReproducibilityError(
            "'manifiesto' debe ser una instancia de "
            "ExecutionManifest."
        )

    if manifiesto.cleaning_plan is None:
        return None

    try:
        return reconstruir_plan(
            manifiesto.cleaning_plan
        )
    except ValueError as exc:
        raise ReproducibilityError(
            "No se pudo reconstruir el plan de limpieza "
            f"del manifiesto: {exc}"
        ) from exc


def verificar_dataset(
    dataset_path: str | Path,
    manifiesto: ExecutionManifest,
) -> DatasetVerification:
    """Verifica un dataset frente a la referencia del manifiesto.

    Un archivo existente cuyo contenido no coincide devuelve MISMATCH.
    La ausencia del archivo o un problema técnico produce
    ReproducibilityError.

    El nombre del archivo no interviene en la coincidencia: se comparan
    tamaño y SHA-256 del contenido.
    """
    if not isinstance(manifiesto, ExecutionManifest):
        raise ReproducibilityError(
            "'manifiesto' debe ser una instancia de "
            "ExecutionManifest."
        )

    ruta = Path(dataset_path)

    if not ruta.is_file():
        raise ReproducibilityError(
            f"No se ha encontrado el dataset a verificar: '{ruta}'."
        )

    try:
        tamano_actual = ruta.stat().st_size
    except OSError as exc:
        raise ReproducibilityError(
            f"No se pudo obtener información del dataset '{ruta}'."
        ) from exc

    sha256_actual = calcular_sha256(ruta)

    referencia = manifiesto.dataset

    coincide = (
        tamano_actual == referencia.file_size
        and sha256_actual == referencia.sha256
    )

    estado = (
        DatasetVerificationStatus.MATCH
        if coincide
        else DatasetVerificationStatus.MISMATCH
    )

    return DatasetVerification(
        status=estado,
        expected_size=referencia.file_size,
        actual_size=tamano_actual,
        expected_sha256=referencia.sha256,
        actual_sha256=sha256_actual,
    )

_NOT_PROVIDED = object()


def _comparar_valores(esperado: Any, actual: Any, detalle: str) -> ComponentVerification:
    estado = VerificationStatus.MATCH if esperado == actual else VerificationStatus.MISMATCH
    return ComponentVerification(estado, esperado, actual, detalle)


def verificar_reproducibilidad(
    manifiesto: ExecutionManifest,
    *,
    dataset_path: str | Path | None = None,
    audit_configuration: dict[str, Any] | object = _NOT_PROVIDED,
    cleaning_plan: CleaningPlan | None | object = _NOT_PROVIDED,
    environment: RuntimeEnvironment | None = None,
) -> ReproducibilityVerification:
    """Compara un manifiesto con el contexto actual sin ejecutar acciones.

    Un componente no suministrado, o no presente en un manifiesto legado,
    se marca como ``no_disponible`` en lugar de inferirse.
    """
    if not isinstance(manifiesto, ExecutionManifest):
        raise ReproducibilityError(
            "'manifiesto' debe ser una instancia de ExecutionManifest."
        )

    if dataset_path is None:
        dataset = ComponentVerification(
            VerificationStatus.UNAVAILABLE,
            expected=manifiesto.dataset.a_dict(),
            detail="No se ha proporcionado un dataset actual.",
        )
    else:
        verificacion = verificar_dataset(dataset_path, manifiesto)
        dataset = ComponentVerification(
            VerificationStatus.MATCH
            if verificacion.matches
            else VerificationStatus.MISMATCH,
            expected={
                "file_size": verificacion.expected_size,
                "sha256": verificacion.expected_sha256,
            },
            actual={
                "file_size": verificacion.actual_size,
                "sha256": verificacion.actual_sha256,
            },
            detail="Comparación por tamaño y SHA-256 del contenido.",
        )

    if audit_configuration is _NOT_PROVIDED:
        configuracion = ComponentVerification(
            VerificationStatus.UNAVAILABLE,
            expected=_copiar_configuracion(manifiesto.audit_configuration),
            detail="No se ha proporcionado la configuración actual.",
        )
    else:
        if not isinstance(audit_configuration, dict):
            raise ReproducibilityError(
                "'audit_configuration' debe ser un diccionario."
            )
        actual_config = _resolver_configuracion(audit_configuration)
        configuracion = _comparar_valores(
            _copiar_configuracion(manifiesto.audit_configuration),
            actual_config,
            "Comparación de la configuración efectiva del auditor.",
        )

    if cleaning_plan is _NOT_PROVIDED:
        plan = ComponentVerification(
            VerificationStatus.UNAVAILABLE,
            expected=(
                manifiesto.cleaning_plan.a_dict()
                if manifiesto.cleaning_plan is not None
                else None
            ),
            detail="No se ha proporcionado el estado actual del plan.",
        )
    elif cleaning_plan is None:
        plan = _comparar_valores(
            manifiesto.cleaning_plan.a_dict()
            if manifiesto.cleaning_plan is not None
            else None,
            None,
            "Comparación de presencia del plan de limpieza.",
        )
    else:
        if not isinstance(cleaning_plan, CleaningPlan):
            raise ReproducibilityError(
                "'cleaning_plan' debe ser CleaningPlan, None o no indicarse."
            )
        nombre = (
            manifiesto.cleaning_plan.name
            if manifiesto.cleaning_plan is not None
            else "Plan actual"
        )
        actual_stored = _crear_plan_reproducible(
            cleaning_plan, nombre, manifiesto.created_at
        )
        esperado_plan = (
            manifiesto.cleaning_plan.a_dict()
            if manifiesto.cleaning_plan is not None
            else None
        )
        actual_plan = actual_stored.a_dict() if actual_stored is not None else None
        plan = _comparar_valores(
            esperado_plan, actual_plan,
            "Comparación de la definición reutilizable del plan.",
        )

    if manifiesto.environment is None:
        entorno = ComponentVerification(
            VerificationStatus.UNAVAILABLE,
            detail="El manifiesto legado no contiene versiones de entorno.",
        )
    else:
        actual_environment = environment or obtener_entorno_actual()
        entorno = _comparar_valores(
            manifiesto.environment.a_dict(),
            actual_environment.a_dict(),
            "Comparación de DataQualityPy, Python y paquetes relevantes.",
        )

    return ReproducibilityVerification(
        dataset=dataset,
        audit_configuration=configuracion,
        cleaning_plan=plan,
        environment=entorno,
    )

