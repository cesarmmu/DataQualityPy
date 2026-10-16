"""Análisis de relaciones entre columnas para DataQualityPy."""

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Any, Mapping

import pandas as pd

from src.candidate_keys import (
    CandidateKeyAnalysis,
    CandidateKeyLevel,
)
from src.column_analysis import ColumnAnalysis
from src.inference import InferenceConfidence


@dataclass(frozen=True)
class CompositeKeyAnalysis:
    """Resultado del análisis de una clave candidata compuesta."""

    columns: tuple[object, object]
    level: CandidateKeyLevel
    confidence: InferenceConfidence
    total_rows: int
    analyzable_rows: int
    null_rows: int
    unique_combinations: int
    uniqueness_ratio: float
    duplicate_excess_count: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class FunctionalRelationship:
    """Correspondencia funcional observada entre dos columnas."""

    source_column: object
    target_column: object
    evaluable_rows: int
    consistent_rows: int
    consistency_ratio: float
    confidence: InferenceConfidence
    evidence: tuple[str, ...]


class PresencePattern(Enum):
    """Patrón observado de presencia o ausencia entre columnas."""

    COINCIDENCE = "coincidencia"
    COMPLEMENTARY = "complementariedad"


@dataclass(frozen=True)
class PresenceRelationship:
    """Patrón de presencia o ausencia observado entre dos columnas."""

    columns: tuple[object, object]
    pattern: PresencePattern
    total_rows: int
    both_present: int
    first_present_second_absent: int
    first_absent_second_present: int
    both_absent: int
    consistency_ratio: float
    confidence: InferenceConfidence
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class RelationshipAnalysis:
    """Conjunto de relaciones detectadas en un dataset."""

    composite_keys: tuple[CompositeKeyAnalysis, ...]
    functional_relationships: tuple[
        FunctionalRelationship,
        ...,
    ]
    presence_relationships: tuple[
        PresenceRelationship,
        ...,
    ]


def _formatear_porcentaje(valor: float) -> str:
    """Formatea un porcentaje para utilizarlo como evidencia."""
    if valor.is_integer():
        return f"{int(valor)} %"

    return f"{valor:.2f} %"


def _crear_mascara_analizable(
    analisis: ColumnAnalysis,
    indice: pd.Index,
) -> pd.Series:
    """
    Construye una máscara booleana de presencia de valores analizables.

    Se reutiliza ``analyzable_series`` para respetar tanto los nulos
    reales como los nulos textuales reconocidos por DataQualityPy.
    """
    mascara = pd.Series(
        False,
        index=indice,
        dtype=bool,
    )

    mascara.loc[
        analisis.analyzable_series.index
    ] = True

    return mascara


def _es_columna_elegible_clave_compuesta(
    analisis: ColumnAnalysis,
    clave_individual: CandidateKeyAnalysis | None,
) -> bool:
    """Indica si una columna puede participar en una clave compuesta."""
    if analisis.analyzable_count == 0:
        return False

    if analisis.unique_count <= 1:
        return False

    if (
        clave_individual is not None
        and clave_individual.level is CandidateKeyLevel.STRONG
    ):
        return False

    return True


def _clasificar_clave_compuesta(
    *,
    analyzable_rows: int,
    null_rows: int,
    uniqueness_ratio: float,
    umbral_posible: float,
    minimo_valores_fuerte: int,
) -> CandidateKeyLevel:
    """Clasifica una combinación de columnas como clave candidata."""
    if analyzable_rows == 0:
        return CandidateKeyLevel.NO_CANDIDATE

    if (
        uniqueness_ratio == 100.0
        and null_rows == 0
        and analyzable_rows >= minimo_valores_fuerte
    ):
        return CandidateKeyLevel.STRONG

    if uniqueness_ratio >= umbral_posible:
        return CandidateKeyLevel.POSSIBLE

    return CandidateKeyLevel.NO_CANDIDATE


def _confianza_clave_compuesta(
    *,
    level: CandidateKeyLevel,
    analyzable_rows: int,
    minimo_valores_fuerte: int,
) -> InferenceConfidence:
    """Asigna confianza a una clave candidata compuesta."""
    if level is CandidateKeyLevel.STRONG:
        return InferenceConfidence.HIGH

    if level is CandidateKeyLevel.POSSIBLE:
        if analyzable_rows < minimo_valores_fuerte:
            return InferenceConfidence.LOW

        return InferenceConfidence.MEDIUM

    return InferenceConfidence.HIGH


def _crear_evidencias_clave_compuesta(
    *,
    columns: tuple[object, object],
    analyzable_rows: int,
    null_rows: int,
    unique_combinations: int,
    uniqueness_ratio: float,
    duplicate_excess_count: int,
    level: CandidateKeyLevel,
) -> tuple[str, ...]:
    """Construye las evidencias de una clave candidata compuesta."""
    primera, segunda = columns

    evidencias = [
        (
            f"La combinación '{primera}' + '{segunda}' presenta "
            f"{unique_combinations} combinaciones distintas entre "
            f"{analyzable_rows} filas analizables."
        ),
        (
            "Unicidad conjunta: "
            f"{_formatear_porcentaje(uniqueness_ratio)}."
        ),
    ]

    if null_rows == 0:
        evidencias.append(
            "No existen filas con ausencia en la combinación."
        )
    else:
        evidencias.append(
            (
                f"Existen {null_rows} filas con al menos un valor "
                "ausente en la combinación."
            )
        )

    if duplicate_excess_count == 0:
        evidencias.append(
            "No existen combinaciones duplicadas adicionales."
        )
    else:
        evidencias.append(
            (
                f"Existen {duplicate_excess_count} combinaciones "
                "duplicadas adicionales."
            )
        )

    if level is CandidateKeyLevel.STRONG:
        evidencias.append(
            "La combinación cumple las condiciones de candidatura fuerte."
        )
    elif level is CandidateKeyLevel.POSSIBLE:
        evidencias.append(
            (
                "La combinación cumple las condiciones de candidatura "
                "posible y requiere revisión."
            )
        )

    return tuple(evidencias)


def analizar_claves_compuestas(
    datos: pd.DataFrame,
    analisis_columnas: Mapping[
        Any,
        ColumnAnalysis,
    ],
    claves_individuales: Mapping[
        Any,
        CandidateKeyAnalysis,
    ],
    *,
    umbral_posible: float = 95.0,
    minimo_valores_fuerte: int = 3,
) -> tuple[CompositeKeyAnalysis, ...]:
    """
    Detecta claves candidatas compuestas formadas por dos columnas.

    Solo se conservan las combinaciones clasificadas como FUERTE o
    POSIBLE. Las columnas que ya constituyen una clave individual
    fuerte se excluyen para evitar combinaciones triviales.
    """
    columnas_elegibles = [
        columna
        for columna, analisis in analisis_columnas.items()
        if (
            columna in datos.columns
            and _es_columna_elegible_clave_compuesta(
                analisis,
                claves_individuales.get(columna),
            )
        )
    ]

    resultados: list[CompositeKeyAnalysis] = []
    total_rows = len(datos)

    for primera, segunda in combinations(
        columnas_elegibles,
        2,
    ):
        analisis_primera = analisis_columnas[
            primera
        ]
        analisis_segunda = analisis_columnas[
            segunda
        ]

        mascara_primera = _crear_mascara_analizable(
            analisis_primera,
            datos.index,
        )
        mascara_segunda = _crear_mascara_analizable(
            analisis_segunda,
            datos.index,
        )

        mascara_conjunta = (
            mascara_primera
            & mascara_segunda
        )

        analyzable_rows = int(
            mascara_conjunta.sum()
        )
        null_rows = total_rows - analyzable_rows

        if analyzable_rows == 0:
            continue

        combinaciones = datos.loc[
            mascara_conjunta,
            [primera, segunda],
        ]

        unique_combinations = int(
            combinaciones.drop_duplicates().shape[0]
        )

        uniqueness_ratio = float(
            unique_combinations
            / analyzable_rows
            * 100
        )

        duplicate_excess_count = (
            analyzable_rows
            - unique_combinations
        )

        level = _clasificar_clave_compuesta(
            analyzable_rows=analyzable_rows,
            null_rows=null_rows,
            uniqueness_ratio=uniqueness_ratio,
            umbral_posible=umbral_posible,
            minimo_valores_fuerte=minimo_valores_fuerte,
        )

        if level is CandidateKeyLevel.NO_CANDIDATE:
            continue

        confidence = _confianza_clave_compuesta(
            level=level,
            analyzable_rows=analyzable_rows,
            minimo_valores_fuerte=minimo_valores_fuerte,
        )

        columns = (
            primera,
            segunda,
        )

        resultados.append(
            CompositeKeyAnalysis(
                columns=columns,
                level=level,
                confidence=confidence,
                total_rows=total_rows,
                analyzable_rows=analyzable_rows,
                null_rows=null_rows,
                unique_combinations=unique_combinations,
                uniqueness_ratio=uniqueness_ratio,
                duplicate_excess_count=duplicate_excess_count,
                evidence=_crear_evidencias_clave_compuesta(
                    columns=columns,
                    analyzable_rows=analyzable_rows,
                    null_rows=null_rows,
                    unique_combinations=unique_combinations,
                    uniqueness_ratio=uniqueness_ratio,
                    duplicate_excess_count=duplicate_excess_count,
                    level=level,
                ),
            )
        )

    return tuple(resultados)


def _es_origen_elegible_relacion_funcional(
    analisis: ColumnAnalysis,
    clave_individual: CandidateKeyAnalysis | None,
) -> bool:
    """Indica si una columna puede actuar como origen funcional."""
    if analisis.analyzable_count == 0:
        return False

    if analisis.unique_count < 2:
        return False

    if (
        clave_individual is not None
        and clave_individual.level is CandidateKeyLevel.STRONG
    ):
        return False

    if analisis.repeated_value_count == 0:
        return False

    return True


def _calcular_filas_consistentes(
    pares: pd.DataFrame,
    source_column: object,
    target_column: object,
) -> int:
    """
    Calcula cuántas filas pertenecen a valores de origen consistentes.

    Un valor de origen es consistente cuando todos sus registros
    evaluables se asocian a un único valor de destino.
    """
    origen = pares[source_column]
    destino = pares[target_column]

    tabla = pd.DataFrame(
        {
            "_origen": origen.to_numpy(),
            "_destino": destino.to_numpy(),
        },
        index=pares.index,
    )

    distintos_destino = (
        tabla.groupby(
            "_origen",
            dropna=False,
            sort=False,
        )["_destino"]
        .nunique(
            dropna=False
        )
    )

    origenes_consistentes = distintos_destino[
        distintos_destino == 1
    ].index

    if len(origenes_consistentes) == 0:
        return 0

    return int(
        tabla["_origen"]
        .isin(origenes_consistentes)
        .sum()
    )


def _confianza_relacion(
    *,
    porcentaje: float,
    cantidad_evidencias: int,
    minimo_evidencias_confianza_alta: int,
) -> InferenceConfidence:
    """
    Asigna confianza provisional a una relación detectada.

    Una relación prácticamente completa solo alcanza confianza ALTA
    cuando existe una cantidad mínima de observaciones evaluables.
    """
    if (
        porcentaje >= 99.0
        and cantidad_evidencias
        >= minimo_evidencias_confianza_alta
    ):
        return InferenceConfidence.HIGH

    return InferenceConfidence.MEDIUM


def _evidencia_muestra_limitada(
    *,
    cantidad_evidencias: int,
    minimo_evidencias_confianza_alta: int,
) -> tuple[str, ...]:
    """Explica cuándo el tamaño de muestra limita la confianza."""
    if (
        cantidad_evidencias
        >= minimo_evidencias_confianza_alta
    ):
        return ()

    return (
        (
            f"Solo existen {cantidad_evidencias} observaciones "
            "evaluables; la cantidad de evidencia limita la "
            "confianza de la relación."
        ),
    )


def _crear_evidencias_relacion_funcional(
    *,
    source_column: object,
    target_column: object,
    evaluable_rows: int,
    consistent_rows: int,
    consistency_ratio: float,
    minimo_evidencias_confianza_alta: int,
) -> tuple[str, ...]:
    """Construye evidencias para una correspondencia funcional."""
    evidencias = [
        (
            f"Se evaluaron {evaluable_rows} filas con valores "
            "analizables en ambas columnas."
        ),
        (
            f"{consistent_rows} filas mantienen una asociación "
            f"consistente de '{source_column}' hacia "
            f"'{target_column}'."
        ),
        (
            "Consistencia observada: "
            f"{_formatear_porcentaje(consistency_ratio)}."
        ),
        (
            "La relación describe una correspondencia observada y "
            "no implica causalidad ni que alguna columna deba eliminarse."
        ),
    ]

    evidencias.extend(
        _evidencia_muestra_limitada(
            cantidad_evidencias=evaluable_rows,
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    return tuple(evidencias)


def analizar_relaciones_funcionales(
    datos: pd.DataFrame,
    analisis_columnas: Mapping[
        Any,
        ColumnAnalysis,
    ],
    claves_individuales: Mapping[
        Any,
        CandidateKeyAnalysis,
    ],
    *,
    umbral_consistencia: float = 95.0,
    minimo_evidencias_confianza_alta: int = 3,
) -> tuple[FunctionalRelationship, ...]:
    """
    Detecta correspondencias funcionales simples entre columnas.

    Las relaciones se analizan de forma dirigida: A → B y B → A son
    hallazgos independientes.
    """
    resultados: list[
        FunctionalRelationship
    ] = []

    columnas = [
        columna
        for columna in analisis_columnas
        if columna in datos.columns
    ]

    for source_column in columnas:
        analisis_origen = analisis_columnas[
            source_column
        ]

        if not _es_origen_elegible_relacion_funcional(
            analisis_origen,
            claves_individuales.get(
                source_column
            ),
        ):
            continue

        mascara_origen = _crear_mascara_analizable(
            analisis_origen,
            datos.index,
        )

        for target_column in columnas:
            if target_column == source_column:
                continue

            analisis_destino = analisis_columnas[
                target_column
            ]

            if analisis_destino.analyzable_count == 0:
                continue

            if analisis_destino.unique_count <= 1:
                continue

            mascara_destino = _crear_mascara_analizable(
                analisis_destino,
                datos.index,
            )

            mascara_conjunta = (
                mascara_origen
                & mascara_destino
            )

            evaluable_rows = int(
                mascara_conjunta.sum()
            )

            if evaluable_rows == 0:
                continue

            pares = datos.loc[
                mascara_conjunta,
                [
                    source_column,
                    target_column,
                ],
            ]

            consistent_rows = (
                _calcular_filas_consistentes(
                    pares,
                    source_column,
                    target_column,
                )
            )

            consistency_ratio = float(
                consistent_rows
                / evaluable_rows
                * 100
            )

            if (
                consistency_ratio
                < umbral_consistencia
            ):
                continue

            resultados.append(
                FunctionalRelationship(
                    source_column=source_column,
                    target_column=target_column,
                    evaluable_rows=evaluable_rows,
                    consistent_rows=consistent_rows,
                    consistency_ratio=consistency_ratio,
                    confidence=_confianza_relacion(
                        porcentaje=consistency_ratio,
                        cantidad_evidencias=evaluable_rows,
                        minimo_evidencias_confianza_alta=(
                            minimo_evidencias_confianza_alta
                        ),
                    ),
                    evidence=(
                        _crear_evidencias_relacion_funcional(
                            source_column=source_column,
                            target_column=target_column,
                            evaluable_rows=evaluable_rows,
                            consistent_rows=consistent_rows,
                            consistency_ratio=consistency_ratio,
                            minimo_evidencias_confianza_alta=(
                                minimo_evidencias_confianza_alta
                            ),
                        )
                    ),
                )
            )

    return tuple(resultados)


def _crear_evidencias_presencia(
    *,
    columns: tuple[object, object],
    pattern: PresencePattern,
    total_rows: int,
    both_present: int,
    first_present_second_absent: int,
    first_absent_second_present: int,
    both_absent: int,
    consistency_ratio: float,
    minimo_evidencias_confianza_alta: int,
) -> tuple[str, ...]:
    """Construye evidencias para un patrón de presencia o ausencia."""
    primera, segunda = columns

    if pattern is PresencePattern.COINCIDENCE:
        descripcion = (
            "Las columnas tienden a estar informadas o ausentes "
            "de forma coincidente."
        )
    else:
        descripcion = (
            "Las columnas tienden a presentar información de forma "
            "complementaria."
        )

    evidencias = [
        (
            f"Se evaluaron {total_rows} filas para "
            f"'{primera}' y '{segunda}'."
        ),
        descripcion,
        (
            f"Ambas presentes: {both_present}; "
            f"primera presente y segunda ausente: "
            f"{first_present_second_absent}; "
            f"primera ausente y segunda presente: "
            f"{first_absent_second_present}; "
            f"ambas ausentes: {both_absent}."
        ),
        (
            "Consistencia del patrón: "
            f"{_formatear_porcentaje(consistency_ratio)}."
        ),
    ]

    evidencias.extend(
        _evidencia_muestra_limitada(
            cantidad_evidencias=total_rows,
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    return tuple(evidencias)


def analizar_relaciones_presencia(
    datos: pd.DataFrame,
    analisis_columnas: Mapping[
        Any,
        ColumnAnalysis,
    ],
    *,
    umbral_consistencia: float = 95.0,
    minimo_evidencias_confianza_alta: int = 3,
) -> tuple[PresenceRelationship, ...]:
    """
    Detecta patrones simples de presencia y ausencia entre columnas.

    Se omiten pares completamente informados porque su coincidencia de
    presencia sería trivial.
    """
    if len(datos) == 0:
        return ()

    columnas = [
        columna
        for columna in analisis_columnas
        if columna in datos.columns
    ]

    resultados: list[
        PresenceRelationship
    ] = []

    total_rows = len(datos)

    for primera, segunda in combinations(
        columnas,
        2,
    ):
        analisis_primera = analisis_columnas[
            primera
        ]
        analisis_segunda = analisis_columnas[
            segunda
        ]

        if (
            analisis_primera.null_count == 0
            and analisis_segunda.null_count == 0
        ):
            continue

        presencia_primera = (
            _crear_mascara_analizable(
                analisis_primera,
                datos.index,
            )
        )
        presencia_segunda = (
            _crear_mascara_analizable(
                analisis_segunda,
                datos.index,
            )
        )

        both_present = int(
            (
                presencia_primera
                & presencia_segunda
            ).sum()
        )

        first_present_second_absent = int(
            (
                presencia_primera
                & ~presencia_segunda
            ).sum()
        )

        first_absent_second_present = int(
            (
                ~presencia_primera
                & presencia_segunda
            ).sum()
        )

        both_absent = int(
            (
                ~presencia_primera
                & ~presencia_segunda
            ).sum()
        )

        coincidence_ratio = float(
            (
                both_present
                + both_absent
            )
            / total_rows
            * 100
        )

        complementarity_ratio = float(
            (
                first_present_second_absent
                + first_absent_second_present
            )
            / total_rows
            * 100
        )

        pattern: PresencePattern | None = None
        consistency_ratio = 0.0

        if (
            coincidence_ratio
            >= umbral_consistencia
        ):
            pattern = (
                PresencePattern.COINCIDENCE
            )
            consistency_ratio = (
                coincidence_ratio
            )

        elif (
            complementarity_ratio
            >= umbral_consistencia
            and first_present_second_absent > 0
            and first_absent_second_present > 0
        ):
            pattern = (
                PresencePattern.COMPLEMENTARY
            )
            consistency_ratio = (
                complementarity_ratio
            )

        if pattern is None:
            continue

        columns = (
            primera,
            segunda,
        )

        resultados.append(
            PresenceRelationship(
                columns=columns,
                pattern=pattern,
                total_rows=total_rows,
                both_present=both_present,
                first_present_second_absent=(
                    first_present_second_absent
                ),
                first_absent_second_present=(
                    first_absent_second_present
                ),
                both_absent=both_absent,
                consistency_ratio=consistency_ratio,
                confidence=_confianza_relacion(
                    porcentaje=consistency_ratio,
                    cantidad_evidencias=total_rows,
                    minimo_evidencias_confianza_alta=(
                        minimo_evidencias_confianza_alta
                    ),
                ),
                evidence=_crear_evidencias_presencia(
                    columns=columns,
                    pattern=pattern,
                    total_rows=total_rows,
                    both_present=both_present,
                    first_present_second_absent=(
                        first_present_second_absent
                    ),
                    first_absent_second_present=(
                        first_absent_second_present
                    ),
                    both_absent=both_absent,
                    consistency_ratio=consistency_ratio,
                    minimo_evidencias_confianza_alta=(
                        minimo_evidencias_confianza_alta
                    ),
                ),
            )
        )

    return tuple(resultados)


def analizar_relaciones(
    datos: pd.DataFrame,
    analisis_columnas: Mapping[
        Any,
        ColumnAnalysis,
    ],
    claves_individuales: Mapping[
        Any,
        CandidateKeyAnalysis,
    ],
    *,
    umbral_clave_posible: float = 95.0,
    minimo_valores_fuerte: int = 3,
    umbral_relacion_funcional: float = 95.0,
    umbral_presencia: float = 95.0,
    minimo_evidencias_confianza_alta: int = 3,
) -> RelationshipAnalysis:
    """
    Ejecuta el análisis conjunto de relaciones entre columnas.

    El resultado reúne claves candidatas compuestas, correspondencias
    funcionales y patrones de presencia o ausencia. El análisis es
    descriptivo y no modifica los datos ni configura relaciones de
    forma automática.
    """
    claves_compuestas = (
        analizar_claves_compuestas(
            datos,
            analisis_columnas,
            claves_individuales,
            umbral_posible=(
                umbral_clave_posible
            ),
            minimo_valores_fuerte=(
                minimo_valores_fuerte
            ),
        )
    )

    relaciones_funcionales = (
        analizar_relaciones_funcionales(
            datos,
            analisis_columnas,
            claves_individuales,
            umbral_consistencia=(
                umbral_relacion_funcional
            ),
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    relaciones_presencia = (
        analizar_relaciones_presencia(
            datos,
            analisis_columnas,
            umbral_consistencia=(
                umbral_presencia
            ),
            minimo_evidencias_confianza_alta=(
                minimo_evidencias_confianza_alta
            ),
        )
    )

    return RelationshipAnalysis(
        composite_keys=claves_compuestas,
        functional_relationships=(
            relaciones_funcionales
        ),
        presence_relationships=(
            relaciones_presencia
        ),
    )