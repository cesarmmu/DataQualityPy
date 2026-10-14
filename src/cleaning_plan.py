"""
DataQualityPy - Plan de limpieza controlada.

Este módulo define y valida las operaciones que forman un plan de limpieza.
No modifica DataFrames ni ejecuta transformaciones sobre los datos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


class CleaningPlanError(ValueError):
    """Error de definición o validación de un plan de limpieza."""


ORDEN_FAMILIAS: dict[str, int] = {
    "texto": 1,
    "sustitucion": 2,
    "conversion": 3,
    "nulos": 4,
    "outliers": 5,
    "duplicados": 6,
}


OPERACIONES_ADMITIDAS: dict[str, set[str]] = {
    "texto": {
        "eliminar_espacios_externos",
        "normalizar_espacios_internos",
        "minusculas",
        "mayusculas",
        "capitalizar",
        "titulo",
        "eliminar_tildes",
        "sustituir_caracteres",
    },
    "sustitucion": {
        "reemplazar_valor",
        "reemplazar_por_nulo",
    },
    "conversion": {
        "numerico",
        "fecha",
        "fecha_hora",
        "texto",
        "booleano",
    },
    "nulos": {
        "eliminar_filas",
        "reemplazar_valor",
        "media",
        "mediana",
        "moda",
    },
    "outliers": {
        "eliminar_filas",
    },
    "duplicados": {
        "eliminar_duplicados_completos",
    },
}


COLUMNAS_OBLIGATORIAS: set[str] = {
    "texto",
    "sustitucion",
    "conversion",
    "nulos",
    "outliers",
}


def _validar_texto_no_vacio(valor: Any, nombre: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise CleaningPlanError(
            f"'{nombre}' debe ser una cadena de texto no vacía."
        )
    return valor.strip()


def _validar_parametros(
    familia: str,
    tipo: str,
    parametros: dict[str, Any],
) -> None:
    if not isinstance(parametros, dict):
        raise CleaningPlanError("'parametros' debe ser un diccionario.")

    if familia == "texto" and tipo == "sustituir_caracteres":
        if "origen" not in parametros:
            raise CleaningPlanError(
                "La sustitución de caracteres requiere el parámetro 'origen'."
            )

        origen = parametros["origen"]
        if not isinstance(origen, str) or origen == "":
            raise CleaningPlanError(
                "El parámetro 'origen' debe ser una cadena de texto no vacía."
            )

        if "destino" not in parametros:
            raise CleaningPlanError(
                "La sustitución de caracteres requiere el parámetro 'destino'."
            )

        if not isinstance(parametros["destino"], str):
            raise CleaningPlanError(
                "El parámetro 'destino' debe ser una cadena de texto."
            )

    elif familia == "sustitucion":
        if "origen" not in parametros:
            raise CleaningPlanError(
                "Las sustituciones requieren el parámetro 'origen'."
            )

        if tipo == "reemplazar_valor" and "destino" not in parametros:
            raise CleaningPlanError(
                "La sustitución de valor requiere el parámetro 'destino'."
            )

    elif familia == "conversion":
        if tipo in {"fecha", "fecha_hora"}:
            formato = parametros.get("formato")
            if formato is not None and not isinstance(formato, str):
                raise CleaningPlanError(
                    "El parámetro opcional 'formato' debe ser texto."
                )

        if tipo == "booleano":
            mapeo = parametros.get("mapeo")
            if mapeo is not None and not isinstance(mapeo, dict):
                raise CleaningPlanError(
                    "El parámetro opcional 'mapeo' debe ser un diccionario."
                )

    elif familia == "nulos":
        if tipo == "reemplazar_valor" and "valor" not in parametros:
            raise CleaningPlanError(
                "El tratamiento de nulos por valor requiere el parámetro 'valor'."
            )

    elif familia == "duplicados":
        conservar = parametros.get("conservar", "primero")
        if conservar != "primero":
            raise CleaningPlanError(
                "En V5 los duplicados completos solo pueden eliminarse "
                "conservando la primera aparición."
            )


@dataclass
class CleaningOperation:
    """Representa una operación individual de limpieza."""

    familia: str
    tipo: str
    columna: str | None = None
    parametros: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    orden_ejecucion: int = field(init=False)

    def __post_init__(self) -> None:
        self.familia = _validar_texto_no_vacio(self.familia, "familia")
        self.tipo = _validar_texto_no_vacio(self.tipo, "tipo")

        if self.familia not in ORDEN_FAMILIAS:
            raise CleaningPlanError(
                f"Familia de limpieza no admitida: '{self.familia}'."
            )

        tipos_admitidos = OPERACIONES_ADMITIDAS[self.familia]
        if self.tipo not in tipos_admitidos:
            raise CleaningPlanError(
                f"Operación '{self.tipo}' no admitida para la familia "
                f"'{self.familia}'."
            )

        if self.familia in COLUMNAS_OBLIGATORIAS:
            self.columna = _validar_texto_no_vacio(
                self.columna,
                "columna",
            )
        elif self.columna is not None:
            self.columna = _validar_texto_no_vacio(
                self.columna,
                "columna",
            )

        if not isinstance(self.parametros, dict):
            raise CleaningPlanError("'parametros' debe ser un diccionario.")

        self.parametros = dict(self.parametros)
        _validar_parametros(
            self.familia,
            self.tipo,
            self.parametros,
        )

        if self.familia == "duplicados":
            self.parametros.setdefault("conservar", "primero")

        self.orden_ejecucion = ORDEN_FAMILIAS[self.familia]

    def a_dict(self) -> dict[str, Any]:
        """Devuelve una representación serializable de la operación."""
        return asdict(self)


@dataclass
class CleaningPlan:
    """Colección validada y ordenable de operaciones de limpieza."""

    operaciones: list[CleaningOperation] = field(default_factory=list)

    def __post_init__(self) -> None:
        operaciones_validadas: list[CleaningOperation] = []

        for operacion in self.operaciones:
            if not isinstance(operacion, CleaningOperation):
                raise CleaningPlanError(
                    "Todas las operaciones del plan deben ser "
                    "instancias de CleaningOperation."
                )
            operaciones_validadas.append(operacion)

        self.operaciones = operaciones_validadas
        self._validar_ids_unicos()

    def _validar_ids_unicos(self) -> None:
        ids = [operacion.id for operacion in self.operaciones]
        if len(ids) != len(set(ids)):
            raise CleaningPlanError(
                "El plan contiene operaciones con identificadores duplicados."
            )

    def agregar_operacion(
        self,
        operacion: CleaningOperation,
    ) -> CleaningOperation:
        """Añade una operación ya validada al plan."""
        if not isinstance(operacion, CleaningOperation):
            raise CleaningPlanError(
                "'operacion' debe ser una instancia de CleaningOperation."
            )

        if any(
            existente.id == operacion.id
            for existente in self.operaciones
        ):
            raise CleaningPlanError(
                f"Ya existe una operación con id '{operacion.id}'."
            )

        self.operaciones.append(operacion)
        return operacion

    def crear_operacion(
        self,
        familia: str,
        tipo: str,
        columna: str | None = None,
        parametros: dict[str, Any] | None = None,
    ) -> CleaningOperation:
        """Crea, valida y añade una nueva operación al plan."""
        operacion = CleaningOperation(
            familia=familia,
            tipo=tipo,
            columna=columna,
            parametros={} if parametros is None else parametros,
        )
        return self.agregar_operacion(operacion)

    def obtener_operacion(self, operacion_id: str) -> CleaningOperation:
        """Obtiene una operación por su identificador."""
        for operacion in self.operaciones:
            if operacion.id == operacion_id:
                return operacion

        raise CleaningPlanError(
            f"No existe ninguna operación con id '{operacion_id}'."
        )

    def eliminar_operacion(self, operacion_id: str) -> CleaningOperation:
        """Elimina una operación y devuelve la operación eliminada."""
        operacion = self.obtener_operacion(operacion_id)
        self.operaciones.remove(operacion)
        return operacion

    def modificar_operacion(
        self,
        operacion_id: str,
        *,
        familia: str | None = None,
        tipo: str | None = None,
        columna: str | None = None,
        parametros: dict[str, Any] | None = None,
    ) -> CleaningOperation:
        """
        Sustituye una operación conservando su identificador.

        Los campos no indicados mantienen su valor actual.
        """
        actual = self.obtener_operacion(operacion_id)

        nueva = CleaningOperation(
            id=actual.id,
            familia=actual.familia if familia is None else familia,
            tipo=actual.tipo if tipo is None else tipo,
            columna=actual.columna if columna is None else columna,
            parametros=(
                dict(actual.parametros)
                if parametros is None
                else parametros
            ),
        )

        indice = self.operaciones.index(actual)
        self.operaciones[indice] = nueva
        return nueva

    def operaciones_ordenadas(self) -> list[CleaningOperation]:
        """
        Devuelve las operaciones en el orden lógico de ejecución de V5.

        Dentro de una misma familia se conserva el orden en el que las
        operaciones fueron añadidas al plan.
        """
        return sorted(
            self.operaciones,
            key=lambda operacion: operacion.orden_ejecucion,
        )

    def esta_vacio(self) -> bool:
        """Indica si el plan no contiene operaciones."""
        return not self.operaciones

    def __len__(self) -> int:
        return len(self.operaciones)

    def a_dict(self, ordenar: bool = True) -> dict[str, Any]:
        """Devuelve el plan en una estructura serializable."""
        operaciones = (
            self.operaciones_ordenadas()
            if ordenar
            else list(self.operaciones)
        )

        return {
            "numero_operaciones": len(operaciones),
            "operaciones": [
                operacion.a_dict()
                for operacion in operaciones
            ],
        }
