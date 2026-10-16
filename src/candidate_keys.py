"""Evaluación de claves candidatas para DataQualityPy."""

from dataclasses import dataclass
from enum import Enum

from src.column_analysis import ColumnAnalysis
from src.inference import InferenceConfidence
from src.quality import nombre_indica_identificador


class CandidateKeyLevel(Enum):
    """Nivel de candidatura de una columna como clave."""

    NO_CANDIDATE = "no_candidata"
    POSSIBLE = "posible"
    STRONG = "fuerte"


@dataclass(frozen=True)
class CandidateKeyAnalysis:
    """Resultado de la evaluación de una columna como clave candidata."""

    column_name: object
    level: CandidateKeyLevel
    confidence: InferenceConfidence
    evidence: tuple[str, ...]


def _formatear_porcentaje(valor: float) -> str:
    """Formatea un porcentaje para utilizarlo en las evidencias."""
    if valor.is_integer():
        return f"{int(valor)} %"

    return f"{valor:.2f} %"


def _crear_evidencias_comunes(
    analisis: ColumnAnalysis,
) -> list[str]:
    """Construye las evidencias objetivas comunes de la evaluación."""
    evidencias = [
        (
            f"{analisis.unique_count} de "
            f"{analisis.analyzable_count} valores analizables "
            "son distintos."
        ),
        (
            "Unicidad: "
            f"{_formatear_porcentaje(analisis.unique_ratio)}."
        ),
        (
            "Cobertura: "
            f"{_formatear_porcentaje(analisis.analyzable_ratio)}."
        ),
    ]

    if analisis.null_count == 0:
        evidencias.append(
            "No existen valores nulos."
        )
    else:
        evidencias.append(
            (
                f"Existen {analisis.null_count} valores nulos "
                f"({_formatear_porcentaje(analisis.null_ratio)})."
            )
        )

    if analisis.duplicate_excess_count == 0:
        evidencias.append(
            "No existen duplicados adicionales entre los valores analizables."
        )
    else:
        evidencias.append(
            (
                f"Existen {analisis.duplicate_excess_count} "
                "duplicados adicionales entre los valores analizables."
            )
        )

    return evidencias


def _agregar_evidencia_nombre(
    analisis: ColumnAnalysis,
    evidencias: list[str],
) -> None:
    """
    Añade información semántica basada en el nombre de la columna.

    El nombre se utiliza únicamente como evidencia complementaria.
    Nunca modifica el nivel de candidatura calculado a partir de los
    datos observados.
    """
    if nombre_indica_identificador(analisis.name):
        evidencias.append(
            "El nombre de la columna sugiere un identificador."
        )


def _evaluar_nivel(
    analisis: ColumnAnalysis,
    umbral_posible: float,
    minimo_valores_fuerte: int,
) -> CandidateKeyLevel:
    """Determina el nivel de candidatura a partir de evidencias objetivas."""
    if analisis.analyzable_count == 0:
        return CandidateKeyLevel.NO_CANDIDATE

    if (
        analisis.unique_ratio == 100.0
        and analisis.null_count == 0
        and analisis.analyzable_count >= minimo_valores_fuerte
    ):
        return CandidateKeyLevel.STRONG

    if analisis.unique_ratio >= umbral_posible:
        return CandidateKeyLevel.POSSIBLE

    return CandidateKeyLevel.NO_CANDIDATE


def _evaluar_confianza(
    analisis: ColumnAnalysis,
    nivel: CandidateKeyLevel,
    minimo_valores_fuerte: int,
) -> InferenceConfidence:
    """
    Estima la confianza de la clasificación realizada.

    La confianza expresa la solidez de la interpretación, no una
    puntuación de calidad ni modifica el nivel de candidatura.
    """
    if nivel is CandidateKeyLevel.STRONG:
        return InferenceConfidence.HIGH

    if nivel is CandidateKeyLevel.POSSIBLE:
        if analisis.analyzable_count < minimo_valores_fuerte:
            return InferenceConfidence.LOW

        return InferenceConfidence.MEDIUM

    if analisis.analyzable_count == 0:
        return InferenceConfidence.HIGH

    return InferenceConfidence.HIGH


def _agregar_evidencia_clasificacion(
    analisis: ColumnAnalysis,
    nivel: CandidateKeyLevel,
    evidencias: list[str],
    umbral_posible: float,
    minimo_valores_fuerte: int,
) -> None:
    """Explica por qué la columna ha recibido su nivel de candidatura."""
    if nivel is CandidateKeyLevel.STRONG:
        evidencias.append(
            (
                "La columna presenta unicidad completa, "
                "cobertura completa y suficientes valores para "
                "considerarse una candidata fuerte."
            )
        )
        return

    if nivel is CandidateKeyLevel.POSSIBLE:
        if analisis.analyzable_count < minimo_valores_fuerte:
            evidencias.append(
                (
                    "El comportamiento es compatible con una clave, "
                    "pero existen pocos valores analizables para "
                    "sostener una candidatura fuerte."
                )
            )
            return

        if analisis.null_count > 0:
            evidencias.append(
                (
                    "La columna presenta una unicidad elevada, "
                    "pero contiene valores nulos y requiere revisión."
                )
            )
            return

        evidencias.append(
            (
                "La columna presenta una unicidad elevada, "
                "pero existen repeticiones que requieren revisión."
            )
        )
        return

    if analisis.analyzable_count == 0:
        evidencias.append(
            (
                "No existen valores analizables para evaluar "
                "la columna como clave candidata."
            )
        )
        return

    evidencias.append(
        (
            "La unicidad observada no alcanza el umbral "
            "establecido para considerarla una posible clave "
            f"({_formatear_porcentaje(umbral_posible)})."
        )
    )


def evaluar_clave_candidata(
    analisis: ColumnAnalysis,
    *,
    umbral_posible: float = 95.0,
    minimo_valores_fuerte: int = 3,
) -> CandidateKeyAnalysis:
    """
    Evalúa una columna como posible clave candidata.

    La clasificación se basa exclusivamente en evidencias observadas
    en los datos. El nombre de la columna se incorpora como contexto,
    pero nunca eleva ni reduce por sí mismo el nivel de candidatura.

    Reglas predeterminadas:

    - FUERTE:
      100 % de unicidad, ausencia de nulos y al menos tres valores
      analizables.

    - POSIBLE:
      al menos un 95 % de unicidad, pero sin cumplir todos los
      requisitos de una candidatura fuerte.

    - NO CANDIDATA:
      menos del 95 % de unicidad o ausencia total de valores
      analizables.

    Los umbrales pueden modificarse mediante parámetros sin alterar
    las evidencias originales almacenadas en ``ColumnAnalysis``.
    """
    nivel = _evaluar_nivel(
        analisis,
        umbral_posible,
        minimo_valores_fuerte,
    )

    confianza = _evaluar_confianza(
        analisis,
        nivel,
        minimo_valores_fuerte,
    )

    evidencias = _crear_evidencias_comunes(
        analisis
    )

    _agregar_evidencia_nombre(
        analisis,
        evidencias,
    )

    _agregar_evidencia_clasificacion(
        analisis,
        nivel,
        evidencias,
        umbral_posible,
        minimo_valores_fuerte,
    )

    return CandidateKeyAnalysis(
        column_name=analisis.name,
        level=nivel,
        confidence=confianza,
        evidence=tuple(evidencias),
    )


def evaluar_claves_candidatas(
    analisis_columnas: dict[object, ColumnAnalysis],
    *,
    umbral_posible: float = 95.0,
    minimo_valores_fuerte: int = 3,
) -> dict[object, CandidateKeyAnalysis]:
    """
    Evalúa como claves candidatas todas las columnas analizadas.

    La función reutiliza ``ColumnAnalysis`` y no modifica los datos
    originales ni configura automáticamente ninguna clave.
    """
    return {
        columna: evaluar_clave_candidata(
            analisis,
            umbral_posible=umbral_posible,
            minimo_valores_fuerte=minimo_valores_fuerte,
        )
        for columna, analisis in analisis_columnas.items()
    }