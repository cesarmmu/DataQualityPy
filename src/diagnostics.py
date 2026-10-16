"""Diagnóstico contextual y posibles acciones para DataQualityPy."""

from dataclasses import dataclass
from typing import Any, Mapping

from src.candidate_keys import (
    CandidateKeyAnalysis,
    CandidateKeyLevel,
)
from src.column_analysis import ColumnAnalysis
from src.distributions import ColumnDistribution
from src.inference import (
    SemanticInference,
    SemanticType,
)


@dataclass(frozen=True)
class Diagnostic:
    """Diagnóstico enriquecido asociado a una incidencia."""

    incident_type: str
    category: str
    severity: str
    column_name: object | None
    incident_message: str
    context: tuple[str, ...]
    possible_actions: tuple[str, ...]


def _formatear_porcentaje(valor: float) -> str:
    """Formatea un porcentaje para los mensajes de diagnóstico."""
    return f"{valor:.2f}".replace(".", ",") + " %"


def _contexto_clave_candidata(
    clave: CandidateKeyAnalysis | None,
) -> list[str]:
    """Genera contexto cuando la candidatura de clave es relevante."""
    if clave is None:
        return []

    if clave.level is CandidateKeyLevel.STRONG:
        return [
            (
                "La columna presenta un comportamiento compatible "
                "con una clave candidata fuerte."
            )
        ]

    if clave.level is CandidateKeyLevel.POSSIBLE:
        return [
            (
                "La columna presenta un comportamiento compatible "
                "con una posible clave candidata, pero requiere "
                "revisión antes de utilizarla como identificador."
            )
        ]

    return []


def _contexto_nulos(
    analisis: ColumnAnalysis | None,
    clave: CandidateKeyAnalysis | None,
    *,
    textual: bool,
) -> tuple[str, ...]:
    """Construye contexto para incidencias de valores ausentes."""
    contexto: list[str] = []

    if analisis is not None:
        contexto.append(
            (
                "La cobertura de valores analizables de la columna "
                f"es {_formatear_porcentaje(analisis.analyzable_ratio)}."
            )
        )

    contexto.extend(
        _contexto_clave_candidata(clave)
    )

    if (
        clave is not None
        and clave.level is CandidateKeyLevel.POSSIBLE
        and analisis is not None
        and analisis.null_count > 0
    ):
        contexto.append(
            (
                "Los valores ausentes impiden que la columna cumpla "
                "las condiciones de una candidata fuerte."
            )
        )

    if textual:
        contexto.append(
            (
                "Los posibles nulos textuales son representaciones "
                "de texto que el análisis interpreta como ausencia "
                "de información."
            )
        )

    return tuple(contexto)


def _acciones_nulos(
    clave: CandidateKeyAnalysis | None,
    *,
    textual: bool,
) -> tuple[str, ...]:
    """Propone acciones conservadoras para valores ausentes."""
    acciones = [
        "Revisar los registros afectados y su fuente de origen.",
    ]

    if textual:
        acciones.append(
            (
                "Comprobar si los marcadores textuales detectados "
                "representan realmente valores ausentes."
            )
        )
        acciones.append(
            (
                "Normalizar los marcadores únicamente después de "
                "confirmar su significado."
            )
        )
    else:
        acciones.append(
            (
                "Comprobar si los valores ausentes pueden recuperarse "
                "desde la fuente original."
            )
        )

    if (
        clave is not None
        and clave.level
        in {
            CandidateKeyLevel.STRONG,
            CandidateKeyLevel.POSSIBLE,
        }
    ):
        acciones.append(
            (
                "No utilizar la columna como clave hasta revisar "
                "los registros sin valor."
            )
        )

    return tuple(acciones)


def _contexto_filas_duplicadas() -> tuple[str, ...]:
    """Contextualiza duplicados completos de registros."""
    return (
        (
            "La incidencia afecta a filas completas que contienen "
            "los mismos valores en todas las columnas evaluadas."
        ),
    )


def _acciones_filas_duplicadas() -> tuple[str, ...]:
    """Propone acciones para filas completamente duplicadas."""
    return (
        "Revisar las filas duplicadas y su procedencia.",
        (
            "Comprobar si representan duplicados reales o registros "
            "válidos repetidos por el proceso de origen."
        ),
        (
            "Eliminar duplicados únicamente cuando pueda confirmarse "
            "que la repetición no aporta información válida."
        ),
    )


def _contexto_duplicados_clave() -> tuple[str, ...]:
    """Contextualiza duplicados según una clave configurada."""
    return (
        (
            "La combinación de columnas configurada como clave no "
            "identifica de forma única todos los registros evaluados."
        ),
    )


def _acciones_duplicados_clave() -> tuple[str, ...]:
    """Propone acciones para duplicados según una clave configurada."""
    return (
        "Revisar los registros que comparten la misma clave.",
        (
            "Comprobar si la clave configurada representa realmente "
            "la granularidad del dataset."
        ),
        (
            "Mantener los registros cuando las repeticiones sean "
            "válidas para el modelo de datos."
        ),
    )


def _contexto_clave_inexistente() -> tuple[str, ...]:
    """Contextualiza una clave configurada con columnas inexistentes."""
    return (
        (
            "La clave configurada no puede evaluarse porque una o "
            "varias de sus columnas no están presentes en el dataset."
        ),
    )


def _acciones_clave_inexistente() -> tuple[str, ...]:
    """Propone acciones ante una clave configurada no disponible."""
    return (
        "Revisar la configuración de columnas clave.",
        (
            "Comprobar si las columnas fueron renombradas, eliminadas "
            "o no están disponibles en la fuente actual."
        ),
        (
            "Actualizar la configuración únicamente después de "
            "confirmar la estructura correcta del dataset."
        ),
    )


def _contexto_columna_vacia() -> tuple[str, ...]:
    """Contextualiza una columna completamente vacía."""
    return (
        (
            "La columna no contiene valores analizables en ninguno "
            "de los registros evaluados."
        ),
        (
            "En su estado actual no aporta información observable "
            "para el análisis del dataset."
        ),
    )


def _acciones_columna_vacia() -> tuple[str, ...]:
    """Propone acciones para una columna completamente vacía."""
    return (
        "Comprobar si la ausencia de datos es esperada.",
        (
            "Revisar la fuente para confirmar si la columna debería "
            "contener información."
        ),
        (
            "Valorar su conservación o exclusión según su función "
            "en el modelo de datos."
        ),
    )


def _contexto_columna_constante(
    analisis: ColumnAnalysis | None,
) -> tuple[str, ...]:
    """Contextualiza una columna con un único valor distinto."""
    contexto = [
        (
            "La columna no presenta variación entre sus valores "
            "analizables."
        )
    ]

    if (
        analisis is not None
        and analisis.most_frequent_value is not None
    ):
        contexto.append(
            (
                "El valor observado es "
                f"'{analisis.most_frequent_value}' "
                f"({_formatear_porcentaje(
                    analisis.most_frequent_ratio
                )} de los valores analizables)."
            )
        )

    return tuple(contexto)


def _acciones_columna_constante() -> tuple[str, ...]:
    """Propone acciones para una columna constante."""
    return (
        (
            "Comprobar si la columna aporta contexto relevante "
            "aunque no presente variación."
        ),
        (
            "Valorar su exclusión únicamente si no resulta necesaria "
            "para el análisis o el modelo de datos."
        ),
    )


def _contexto_espacios_texto(
    inferencia: SemanticInference | None,
) -> tuple[str, ...]:
    """Contextualiza espacios externos en valores de texto."""
    contexto = [
        (
            "Los espacios al inicio o al final pueden provocar que "
            "valores visualmente iguales sean tratados como distintos."
        )
    ]

    if inferencia is not None:
        contexto.append(
            (
                "El tipo semántico asociado a la columna es "
                f"'{inferencia.semantic_type.value}'."
            )
        )

    return tuple(contexto)


def _acciones_espacios_texto() -> tuple[str, ...]:
    """Propone acciones para espacios externos."""
    return (
        "Revisar ejemplos de los valores afectados.",
        (
            "Valorar la eliminación de espacios externos cuando "
            "no formen parte significativa del dato."
        ),
        (
            "Comprobar el resultado antes de aplicar la normalización "
            "al conjunto de datos."
        ),
    )


def _contexto_inconsistencia_categorica(
    analisis: ColumnAnalysis | None,
    inferencia: SemanticInference | None,
) -> tuple[str, ...]:
    """Contextualiza posibles variantes de categorías."""
    contexto = [
        (
            "Se han detectado variantes textuales que podrían "
            "representar una misma categoría."
        )
    ]

    if analisis is not None:
        contexto.append(
            (
                "La columna contiene "
                f"{analisis.unique_count} valores distintos entre "
                f"{analisis.analyzable_count} valores analizables."
            )
        )

    if (
        inferencia is not None
        and inferencia.semantic_type
        is SemanticType.CATEGORICAL
    ):
        contexto.append(
            (
                "La inferencia semántica considera la columna "
                "categórica, por lo que la consistencia entre "
                "categorías resulta especialmente relevante."
            )
        )

    return tuple(contexto)


def _acciones_inconsistencia_categorica() -> tuple[str, ...]:
    """Propone acciones para variantes de categorías."""
    return (
        "Revisar los grupos de valores señalados como inconsistentes.",
        (
            "Confirmar qué variantes representan realmente la misma "
            "categoría."
        ),
        (
            "Normalizar categorías únicamente después de definir "
            "las equivalencias correctas."
        ),
    )


def _contexto_outliers(
    analisis: ColumnAnalysis | None,
) -> tuple[str, ...]:
    """Contextualiza valores atípicos detectados mediante IQR."""
    contexto = [
        (
            "Los valores han sido identificados como atípicos mediante "
            "el criterio IQR; esta condición no implica por sí sola "
            "que sean incorrectos."
        )
    ]

    if (
        analisis is not None
        and analisis.numeric_conversion is not None
    ):
        contexto.append(
            (
                "La evaluación se apoya en los valores que pueden "
                "interpretarse numéricamente."
            )
        )

    return tuple(contexto)


def _acciones_outliers() -> tuple[str, ...]:
    """Propone acciones conservadoras para valores atípicos."""
    return (
        "Revisar los registros afectados.",
        "Contrastar los valores con su fuente o contexto.",
        (
            "Mantener los valores cuando representen observaciones "
            "legítimas."
        ),
    )


def _contexto_incompatibilidad_tipo(
    analisis: ColumnAnalysis | None,
    inferencia: SemanticInference | None,
) -> tuple[str, ...]:
    """Contextualiza incompatibilidades con el tipo semántico."""
    contexto: list[str] = []

    if inferencia is not None:
        contexto.append(
            (
                "El tipo semántico asociado a la columna es "
                f"'{inferencia.semantic_type.value}'."
            )
        )

    if analisis is not None:
        contexto.append(
            (
                "La cobertura de valores analizables es "
                f"{_formatear_porcentaje(analisis.analyzable_ratio)}."
            )
        )

    contexto.append(
        (
            "Los valores incompatibles deben revisarse antes de "
            "realizar una conversión o corrección."
        )
    )

    return tuple(contexto)


def _acciones_incompatibilidad_tipo() -> tuple[str, ...]:
    """Propone acciones ante incompatibilidades semánticas."""
    return (
        "Revisar los valores incompatibles detectados.",
        (
            "Comprobar si corresponden a errores de captura, formatos "
            "alternativos o valores legítimos."
        ),
        (
            "Confirmar el tipo semántico antes de aplicar cualquier "
            "conversión."
        ),
    )


def _contexto_regla_negocio() -> tuple[str, ...]:
    """Contextualiza incumplimientos de reglas declaradas."""
    return (
        (
            "La incidencia procede de una regla de negocio configurada "
            "explícitamente para el dataset."
        ),
        (
            "Un incumplimiento indica una discrepancia respecto a la "
            "regla definida, no necesariamente un error del dato."
        ),
    )


def _acciones_regla_negocio() -> tuple[str, ...]:
    """Propone acciones ante incumplimientos de reglas de negocio."""
    return (
        "Revisar los valores que incumplen la regla configurada.",
        (
            "Confirmar que la regla continúa siendo válida para el "
            "dataset actual."
        ),
        (
            "Corregir únicamente los registros cuya invalidez pueda "
            "verificarse."
        ),
    )


def _contexto_conversion_fecha(
    analisis: ColumnAnalysis | None,
    inferencia: SemanticInference | None,
) -> tuple[str, ...]:
    """Contextualiza fallos de interpretación de fechas."""
    contexto = [
        (
            "Parte de los valores no puede interpretarse utilizando "
            "los criterios de conversión temporal aplicados."
        )
    ]

    if inferencia is not None:
        contexto.append(
            (
                "El tipo semántico asociado a la columna es "
                f"'{inferencia.semantic_type.value}'."
            )
        )

    if (
        analisis is not None
        and analisis.datetime_conversion is not None
    ):
        conversion = analisis.datetime_conversion

        contexto.append(
            (
                "La conversión temporal presenta "
                f"{conversion.failed_count} valores no convertibles."
            )
        )

    return tuple(contexto)


def _acciones_conversion_fecha() -> tuple[str, ...]:
    """Propone acciones ante fallos de conversión temporal."""
    return (
        "Revisar los valores que no pudieron interpretarse como fecha.",
        (
            "Comprobar si existen formatos de fecha diferentes, "
            "errores de captura o valores no temporales."
        ),
        (
            "Confirmar el formato esperado antes de aplicar una "
            "conversión."
        ),
    )


def _obtener_contexto_y_acciones(
    tipo: str,
    analisis: ColumnAnalysis | None,
    inferencia: SemanticInference | None,
    clave: CandidateKeyAnalysis | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Despacha la construcción del diagnóstico según la incidencia."""
    if tipo == "nulos_reales":
        return (
            _contexto_nulos(
                analisis,
                clave,
                textual=False,
            ),
            _acciones_nulos(
                clave,
                textual=False,
            ),
        )

    if tipo == "nulos_textuales":
        return (
            _contexto_nulos(
                analisis,
                clave,
                textual=True,
            ),
            _acciones_nulos(
                clave,
                textual=True,
            ),
        )

    if tipo == "filas_duplicadas":
        return (
            _contexto_filas_duplicadas(),
            _acciones_filas_duplicadas(),
        )

    if tipo == "clave_inexistente":
        return (
            _contexto_clave_inexistente(),
            _acciones_clave_inexistente(),
        )

    if tipo == "duplicados_clave":
        return (
            _contexto_duplicados_clave(),
            _acciones_duplicados_clave(),
        )

    if tipo == "columna_vacia":
        return (
            _contexto_columna_vacia(),
            _acciones_columna_vacia(),
        )

    if tipo == "columna_constante":
        return (
            _contexto_columna_constante(
                analisis
            ),
            _acciones_columna_constante(),
        )

    if tipo == "espacios_texto":
        return (
            _contexto_espacios_texto(
                inferencia
            ),
            _acciones_espacios_texto(),
        )

    if tipo == "inconsistencia_categorica":
        return (
            _contexto_inconsistencia_categorica(
                analisis,
                inferencia,
            ),
            _acciones_inconsistencia_categorica(),
        )

    if tipo == "outliers":
        return (
            _contexto_outliers(
                analisis
            ),
            _acciones_outliers(),
        )

    if tipo == "incompatibilidad_tipo":
        return (
            _contexto_incompatibilidad_tipo(
                analisis,
                inferencia,
            ),
            _acciones_incompatibilidad_tipo(),
        )

    if tipo == "incumplimiento_regla":
        return (
            _contexto_regla_negocio(),
            _acciones_regla_negocio(),
        )

    if tipo == "conversion_fecha":
        return (
            _contexto_conversion_fecha(
                analisis,
                inferencia,
            ),
            _acciones_conversion_fecha(),
        )

    return (
        (
            "No existe contexto específico para este tipo de incidencia.",
        ),
        (
            "Revisar la incidencia y los registros afectados.",
        ),
    )


def generar_diagnostico(
    incidencia: Mapping[str, Any],
    *,
    analisis: ColumnAnalysis | None = None,
    inferencia: SemanticInference | None = None,
    clave_candidata: CandidateKeyAnalysis | None = None,
    distribucion: ColumnDistribution = None,
) -> Diagnostic:
    """
    Enriquece una incidencia con contexto y posibles acciones.

    La función no modifica datos, no ejecuta operaciones de limpieza
    y no configura automáticamente claves ni reglas.

    ``distribucion`` forma parte de la interfaz para permitir utilizar
    evidencia de distribución cuando resulte relevante. En esta
    primera versión no genera incidencias nuevas por sí misma.
    """
    del distribucion

    tipo = str(
        incidencia.get(
            "tipo",
            "desconocida",
        )
    )

    categoria = str(
        incidencia.get(
            "categoria",
            "sin_categoria",
        )
    )

    severidad = str(
        incidencia.get(
            "severidad",
            "sin_severidad",
        )
    )

    columna = incidencia.get(
        "columna"
    )

    mensaje = str(
        incidencia.get(
            "mensaje",
            "",
        )
    )

    contexto, acciones = (
        _obtener_contexto_y_acciones(
            tipo,
            analisis,
            inferencia,
            clave_candidata,
        )
    )

    return Diagnostic(
        incident_type=tipo,
        category=categoria,
        severity=severidad,
        column_name=columna,
        incident_message=mensaje,
        context=contexto,
        possible_actions=acciones,
    )


def generar_diagnosticos(
    incidencias: list[dict[str, Any]],
    analisis_columnas: Mapping[
        Any,
        ColumnAnalysis,
    ],
    inferencias: Mapping[
        Any,
        SemanticInference,
    ],
    claves_candidatas: Mapping[
        Any,
        CandidateKeyAnalysis,
    ],
    distribuciones: Mapping[
        Any,
        ColumnDistribution,
    ],
) -> list[Diagnostic]:
    """
    Genera diagnósticos para una colección de incidencias.

    Las evidencias V6 se buscan por columna cuando la incidencia está
    asociada a una columna concreta. Las incidencias globales pueden
    diagnosticarse sin ``ColumnAnalysis`` ni inferencia semántica.
    """
    diagnosticos: list[Diagnostic] = []

    for incidencia in incidencias:
        columna = incidencia.get(
            "columna"
        )

        analisis = (
            analisis_columnas.get(columna)
            if columna is not None
            else None
        )

        inferencia = (
            inferencias.get(columna)
            if columna is not None
            else None
        )

        clave = (
            claves_candidatas.get(columna)
            if columna is not None
            else None
        )

        distribucion = (
            distribuciones.get(columna)
            if columna is not None
            else None
        )

        diagnosticos.append(
            generar_diagnostico(
                incidencia,
                analisis=analisis,
                inferencia=inferencia,
                clave_candidata=clave,
                distribucion=distribucion,
            )
        )

    return diagnosticos