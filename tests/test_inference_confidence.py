"""Tests de confianza cualitativa de inferencias para DataQualityPy V6.1.7."""

import pandas as pd

from src.candidate_keys import evaluar_claves_candidatas
from src.column_analysis import analizar_columnas
from src.inference import (
    InferenceConfidence,
    SemanticType,
    inferir_tipo_semantico,
)
from src.relationships import (
    analizar_relaciones_funcionales,
    analizar_relaciones_presencia,
)


def _inferir_columna(
    datos: pd.DataFrame,
    columna: object,
    *,
    tipo_declarado: str | None = None,
):
    """Analiza una columna y ejecuta su inferencia semántica."""
    analisis = analizar_columnas(datos)
    analisis_columna = analisis[columna]

    return inferir_tipo_semantico(
        analisis_columna,
        analisis_columna.analyzable_series,
        tipo_declarado=tipo_declarado,
    )


def test_identificador_completo_con_muestra_suficiente_confianza_alta_v6() -> None:
    """Un identificador completo con muestra suficiente alcanza ALTA."""
    datos = pd.DataFrame(
        {
            "id_cliente": [
                1001,
                1002,
                1003,
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "id_cliente",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.IDENTIFIER
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.HIGH
    )


def test_identificador_completo_con_muestra_pequena_confianza_media_v6() -> None:
    """Un identificador perfecto con solo dos valores queda en MEDIA."""
    datos = pd.DataFrame(
        {
            "id_cliente": [
                1001,
                1002,
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "id_cliente",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.IDENTIFIER
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.MEDIUM
    )
    assert any(
        "limita la confianza" in evidencia
        for evidencia in inferencia.evidence
    )


def test_fecha_completa_con_muestra_suficiente_confianza_alta_v6() -> None:
    """Tres fechas convertibles al 100 % permiten confianza ALTA."""
    datos = pd.DataFrame(
        {
            "fecha_evento": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "fecha_evento",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.DATE
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.HIGH
    )


def test_fecha_completa_con_muestra_pequena_confianza_media_v6() -> None:
    """Dos fechas perfectas no bastan para confianza ALTA."""
    datos = pd.DataFrame(
        {
            "fecha_evento": [
                "2026-01-01",
                "2026-01-02",
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "fecha_evento",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.DATE
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.MEDIUM
    )
    assert any(
        "limita la confianza" in evidencia
        for evidencia in inferencia.evidence
    )


def test_numerico_completo_con_muestra_pequena_confianza_media_v6() -> None:
    """Una conversión numérica perfecta pequeña queda en MEDIA."""
    datos = pd.DataFrame(
        {
            "importe": [
                "10.5",
                "20.5",
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "importe",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.NUMERIC
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.MEDIUM
    )
    assert any(
        "limita la confianza" in evidencia
        for evidencia in inferencia.evidence
    )


def test_booleano_inequivoco_pequeno_mantiene_confianza_alta_v6() -> None:
    """Un patrón booleano inequívoco mantiene ALTA con dos valores."""
    datos = pd.DataFrame(
        {
            "activo": [
                0,
                1,
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "activo",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.BOOLEAN
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.HIGH
    )


def test_tipo_declarado_mantiene_confianza_alta_con_muestra_pequena_v6() -> None:
    """Un tipo declarado explícitamente mantiene confianza ALTA."""
    datos = pd.DataFrame(
        {
            "valor": [
                "A",
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "valor",
        tipo_declarado="categorico",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.CATEGORICAL
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.HIGH
    )
    assert inferencia.source == "declared"


def test_texto_libre_por_descarte_mantiene_confianza_media_v6() -> None:
    """El texto libre inferido por descarte mantiene confianza MEDIA."""
    datos = pd.DataFrame(
        {
            "comentario": [
                "Texto libre suficientemente largo número uno",
                "Otro comentario completamente diferente",
                "Una tercera observación de contenido textual",
                "Cuarta frase sin relación categórica",
                "Quinto texto para aumentar la cardinalidad",
            ],
        }
    )

    inferencia = _inferir_columna(
        datos,
        "comentario",
    )

    assert (
        inferencia.semantic_type
        is SemanticType.FREE_TEXT
    )
    assert (
        inferencia.confidence
        is InferenceConfidence.MEDIUM
    )


def test_relacion_funcional_perfecta_con_muestra_suficiente_confianza_alta_v6() -> None:
    """Una relación funcional perfecta y suficiente alcanza ALTA."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "A",
                "B",
                "B",
            ],
            "descripcion": [
                "Alpha",
                "Alpha",
                "Beta",
                "Beta",
            ],
        }
    )

    analisis = analizar_columnas(datos)
    claves = evaluar_claves_candidatas(
        analisis
    )

    relaciones = (
        analizar_relaciones_funcionales(
            datos,
            analisis,
            claves,
        )
    )

    relacion = next(
        resultado
        for resultado in relaciones
        if (
            resultado.source_column
            == "codigo"
            and resultado.target_column
            == "descripcion"
        )
    )

    assert (
        relacion.consistency_ratio
        == 100.0
    )
    assert (
        relacion.confidence
        is InferenceConfidence.HIGH
    )


def test_relacion_funcional_muestra_inferior_al_minimo_confianza_media_v6() -> None:
    """Una relación perfecta queda en MEDIA si no alcanza el mínimo configurado."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "A",
                "B",
                "B",
            ],
            "descripcion": [
                "Alpha",
                "Alpha",
                "Beta",
                "Beta",
            ],
        }
    )

    analisis = analizar_columnas(datos)
    claves = evaluar_claves_candidatas(
        analisis
    )

    relaciones = (
        analizar_relaciones_funcionales(
            datos,
            analisis,
            claves,
            minimo_evidencias_confianza_alta=5,
        )
    )

    relacion = next(
        resultado
        for resultado in relaciones
        if (
            resultado.source_column
            == "codigo"
            and resultado.target_column
            == "descripcion"
        )
    )

    assert (
        relacion.consistency_ratio
        == 100.0
    )
    assert (
        relacion.confidence
        is InferenceConfidence.MEDIUM
    )
    assert any(
        "limita la confianza" in evidencia
        for evidencia in relacion.evidence
    )


def test_presencia_perfecta_con_muestra_suficiente_confianza_alta_v6() -> None:
    """Un patrón perfecto de presencia con muestra suficiente alcanza ALTA."""
    datos = pd.DataFrame(
        {
            "telefono": [
                "111",
                None,
                "222",
                None,
            ],
            "email": [
                "a@x.es",
                None,
                "b@x.es",
                None,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    relaciones = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert len(relaciones) == 1

    relacion = relaciones[0]

    assert (
        relacion.consistency_ratio
        == 100.0
    )
    assert (
        relacion.confidence
        is InferenceConfidence.HIGH
    )


def test_presencia_perfecta_con_muestra_pequena_confianza_media_v6() -> None:
    """Un patrón perfecto de presencia con dos filas queda en MEDIA."""
    datos = pd.DataFrame(
        {
            "telefono": [
                "111",
                None,
            ],
            "email": [
                "a@x.es",
                None,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    relaciones = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert len(relaciones) == 1

    relacion = relaciones[0]

    assert (
        relacion.consistency_ratio
        == 100.0
    )
    assert (
        relacion.confidence
        is InferenceConfidence.MEDIUM
    )
    assert any(
        "limita la confianza" in evidencia
        for evidencia in relacion.evidence
    )