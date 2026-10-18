"""Tests del diagnóstico contextual de DataQualityPy."""

import pandas as pd

from src.candidate_keys import (
    CandidateKeyLevel,
    evaluar_clave_candidata,
)
from src.column_analysis import (
    analizar_columna,
    analizar_columnas,
)
from src.diagnostics import (
    Diagnostic,
    DiagnosticEvidence,
    generar_diagnostico,
    generar_diagnosticos,
)
from src.distributions import crear_distribuciones
from src.inference import (
    InferenceConfidence,
    SemanticInference,
    SemanticType,
)


def _crear_inferencia(
    nombre: object,
    tipo: SemanticType,
) -> SemanticInference:
    """Crea una inferencia controlada para los tests."""
    return SemanticInference(
        column_name=nombre,
        semantic_type=tipo,
        confidence=InferenceConfidence.HIGH,
        evidence=("Inferencia controlada para test.",),
    )


def _crear_incidencia(
    tipo: str,
    *,
    columna: object | None = "columna",
    categoria: str = "validez",
    severidad: str = "media",
    mensaje: str = "Incidencia de prueba.",
) -> dict[str, object]:
    """Crea una incidencia compatible con incidents.py."""
    return {
        "tipo": tipo,
        "categoria": categoria,
        "severidad": severidad,
        "columna": columna,
        "cantidad": 1,
        "porcentaje": 10.0,
        "mensaje": mensaje,
    }


def test_diagnostico_nulos_reales_v6() -> None:
    """Los nulos reales deben recibir contexto y acciones."""
    serie = pd.Series(
        ["A", "B", None, "C"],
        name="codigo",
        dtype="object",
    )

    analisis = analizar_columna(serie)
    clave = evaluar_clave_candidata(
        analisis
    )

    incidencia = _crear_incidencia(
        "nulos_reales",
        columna="codigo",
        categoria="completitud",
        mensaje=(
            "La columna 'codigo' contiene 1 valor nulo."
        ),
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        clave_candidata=clave,
    )

    assert isinstance(
        resultado,
        Diagnostic,
    )

    assert resultado.incident_type == "nulos_reales"
    assert resultado.category == "completitud"
    assert resultado.column_name == "codigo"
    assert resultado.incident_message == (
        "La columna 'codigo' contiene 1 valor nulo."
    )

    assert any(
        "cobertura" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "posible clave candidata" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "impiden" in texto.lower()
        and "candidata fuerte" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "no utilizar" in accion.lower()
        and "como clave" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_nulos_textuales_v6() -> None:
    """Los nulos textuales deben explicarse como posibles ausencias."""
    serie = pd.Series(
        ["Madrid", "NA", "Sevilla", ""],
        name="ciudad",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    incidencia = _crear_incidencia(
        "nulos_textuales",
        columna="ciudad",
        categoria="completitud",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
    )

    assert any(
        "nulos textuales" in texto.lower()
        and "ausencia" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "marcadores textuales" in accion.lower()
        for accion in resultado.possible_actions
    )

    assert any(
        "normalizar" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_filas_duplicadas_v6() -> None:
    """Los duplicados completos deben distinguirse de una clave."""
    incidencia = _crear_incidencia(
        "filas_duplicadas",
        columna=None,
        categoria="unicidad",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert resultado.column_name is None

    assert any(
        "filas completas" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "duplicados reales" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_clave_inexistente_v6() -> None:
    """Una clave inexistente debe orientar a revisar configuración."""
    incidencia = _crear_incidencia(
        "clave_inexistente",
        columna=None,
        categoria="estructura",
        severidad="alta",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert any(
        "no puede evaluarse" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "configuración" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_duplicados_clave_v6() -> None:
    """Los duplicados de clave deben contextualizar la unicidad."""
    incidencia = _crear_incidencia(
        "duplicados_clave",
        columna=None,
        categoria="unicidad",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert any(
        "no identifica de forma única" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "granularidad" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_columna_vacia_v6() -> None:
    """Una columna vacía debe explicarse sin ordenar eliminarla."""
    incidencia = _crear_incidencia(
        "columna_vacia",
        columna="sin_datos",
        categoria="estructura",
        severidad="alta",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert any(
        "no contiene valores analizables" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "conservación o exclusión" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_columna_constante_v6() -> None:
    """Una columna constante debe mostrar su valor dominante."""
    serie = pd.Series(
        ["España", "España", "España"],
        name="pais",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    incidencia = _crear_incidencia(
        "columna_constante",
        columna="pais",
        categoria="estructura",
        severidad="baja",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
    )

    assert any(
        "no presenta variación" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "españa" in texto.lower()
        and "100,00 %" in texto
        for texto in resultado.context
    )

    assert any(
        "contexto relevante" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_espacios_texto_v6() -> None:
    """Los espacios externos deben contextualizar su efecto."""
    serie = pd.Series(
        ["Madrid ", "Sevilla", "Bilbao"],
        name="ciudad",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    inferencia = _crear_inferencia(
        "ciudad",
        SemanticType.CATEGORICAL,
    )

    incidencia = _crear_incidencia(
        "espacios_texto",
        columna="ciudad",
        categoria="consistencia",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )

    assert any(
        "visualmente iguales" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "categorico" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "espacios externos" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_inconsistencia_categorica_v6() -> None:
    """Las variantes categóricas deben recibir contexto semántico."""
    serie = pd.Series(
        [
            "Madrid",
            "madrid",
            "MADRID",
            "Sevilla",
        ],
        name="ciudad",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    inferencia = _crear_inferencia(
        "ciudad",
        SemanticType.CATEGORICAL,
    )

    incidencia = _crear_incidencia(
        "inconsistencia_categorica",
        columna="ciudad",
        categoria="consistencia",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )

    assert any(
        "misma categoría" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "4 valores distintos" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "categórica" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "equivalencias" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_outliers_v6() -> None:
    """Un outlier debe explicarse sin considerarlo error."""
    serie = pd.Series(
        [10, 11, 12, 13, 1000],
        name="importe",
    )

    analisis = analizar_columna(serie)

    incidencia = _crear_incidencia(
        "outliers",
        columna="importe",
        categoria="validez",
        severidad="baja",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
    )

    assert any(
        "criterio iqr" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "no implica" in texto.lower()
        and "incorrectos" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "observaciones legítimas" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_incompatibilidad_tipo_v6() -> None:
    """Una incompatibilidad debe preservar la decisión del usuario."""
    serie = pd.Series(
        ["10", "20", "error", "30"],
        name="cantidad",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    inferencia = _crear_inferencia(
        "cantidad",
        SemanticType.NUMERIC,
    )

    incidencia = _crear_incidencia(
        "incompatibilidad_tipo",
        columna="cantidad",
        categoria="validez",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )

    assert any(
        "numerico" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "antes de realizar una conversión" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "confirmar el tipo semántico" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_incumplimiento_regla_v6() -> None:
    """Una regla de negocio no debe convertir el dato en error automático."""
    incidencia = _crear_incidencia(
        "incumplimiento_regla",
        columna="edad",
        categoria="validez",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert any(
        "regla de negocio" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "no necesariamente un error" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "continúa siendo válida" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_conversion_fecha_v6() -> None:
    """Los fallos de fecha deben utilizar la evidencia temporal."""
    serie = pd.Series(
        [
            "2026-01-01",
            "2026-02-01",
            "fecha_invalida",
            "2026-03-01",
        ],
        name="fecha",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    inferencia = _crear_inferencia(
        "fecha",
        SemanticType.DATE,
    )

    incidencia = _crear_incidencia(
        "conversion_fecha",
        columna="fecha",
        categoria="validez",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )

    assert any(
        "criterios de conversión temporal" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "fecha" in texto.lower()
        for texto in resultado.context
    )

    assert any(
        "formatos de fecha diferentes" in accion.lower()
        for accion in resultado.possible_actions
    )


def test_diagnostico_tipo_desconocido_v6() -> None:
    """Una incidencia futura debe recibir un diagnóstico seguro."""
    incidencia = _crear_incidencia(
        "incidencia_futura",
        columna="dato",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert resultado.incident_type == "incidencia_futura"

    assert resultado.context == (
        (
            "No existe contexto específico para este tipo "
            "de incidencia."
        ),
    )

    assert resultado.possible_actions == (
        "Revisar la incidencia y los registros afectados.",
    )


def test_diagnostico_con_evidencias_opcionales_ausentes_v6() -> None:
    """El diagnóstico debe funcionar sin evidencias V6 opcionales."""
    incidencia = _crear_incidencia(
        "nulos_reales",
        columna="codigo",
        categoria="completitud",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert isinstance(
        resultado,
        Diagnostic,
    )

    assert resultado.incident_type == "nulos_reales"

    assert len(
        resultado.possible_actions
    ) >= 1


def test_generar_diagnosticos_v6() -> None:
    """El procesamiento conjunto debe asociar evidencias por columna."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "B",
                None,
                "C",
            ],
            "importe": [
                10,
                20,
                30,
                1000,
            ],
        }
    )

    analisis = analizar_columnas(
        datos
    )

    inferencias = {
        "codigo": _crear_inferencia(
            "codigo",
            SemanticType.IDENTIFIER,
        ),
        "importe": _crear_inferencia(
            "importe",
            SemanticType.NUMERIC,
        ),
    }

    claves = {
        columna: evaluar_clave_candidata(
            resultado
        )
        for columna, resultado in analisis.items()
    }

    distribuciones = crear_distribuciones(
        analisis,
        inferencias,
    )

    incidencias = [
        _crear_incidencia(
            "nulos_reales",
            columna="codigo",
            categoria="completitud",
        ),
        _crear_incidencia(
            "outliers",
            columna="importe",
            categoria="validez",
            severidad="baja",
        ),
        _crear_incidencia(
            "filas_duplicadas",
            columna=None,
            categoria="unicidad",
        ),
    ]

    resultado = generar_diagnosticos(
        incidencias,
        analisis,
        inferencias,
        claves,
        distribuciones,
    )

    assert len(resultado) == 3

    assert [
        diagnostico.incident_type
        for diagnostico in resultado
    ] == [
        "nulos_reales",
        "outliers",
        "filas_duplicadas",
    ]

    assert resultado[0].column_name == "codigo"
    assert resultado[1].column_name == "importe"
    assert resultado[2].column_name is None


def test_diagnosticos_no_modifican_datos_v6() -> None:
    """El diagnóstico no debe modificar el DataFrame original."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "B",
                None,
                "C",
            ],
            "importe": [
                10,
                20,
                30,
                1000,
            ],
        }
    )

    original = datos.copy(
        deep=True
    )

    analisis = analizar_columnas(
        datos
    )

    inferencias = {
        "codigo": _crear_inferencia(
            "codigo",
            SemanticType.IDENTIFIER,
        ),
        "importe": _crear_inferencia(
            "importe",
            SemanticType.NUMERIC,
        ),
    }

    claves = {
        columna: evaluar_clave_candidata(
            resultado
        )
        for columna, resultado in analisis.items()
    }

    distribuciones = crear_distribuciones(
        analisis,
        inferencias,
    )

    incidencias = [
        _crear_incidencia(
            "nulos_reales",
            columna="codigo",
            categoria="completitud",
        ),
        _crear_incidencia(
            "outliers",
            columna="importe",
            categoria="validez",
        ),
    ]

    generar_diagnosticos(
        incidencias,
        analisis,
        inferencias,
        claves,
        distribuciones,
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )


def test_diagnostico_preserva_metadatos_incidencia_v6() -> None:
    """El diagnóstico debe conservar los metadatos principales."""
    incidencia = _crear_incidencia(
        "outliers",
        columna="importe",
        categoria="validez",
        severidad="baja",
        mensaje="Mensaje original de la incidencia.",
    )

    resultado = generar_diagnostico(
        incidencia
    )

    assert resultado.incident_type == "outliers"
    assert resultado.category == "validez"
    assert resultado.severity == "baja"
    assert resultado.column_name == "importe"
    assert resultado.incident_message == (
        "Mensaje original de la incidencia."
    )


def test_clave_fuerte_aporta_contexto_v6() -> None:
    """Una clave fuerte debe aparecer como evidencia contextual."""
    serie = pd.Series(
        ["C001", "C002", "C003", "C004"],
        name="cliente_id",
        dtype="object",
    )

    analisis = analizar_columna(serie)

    clave = evaluar_clave_candidata(
        analisis
    )

    assert clave.level is CandidateKeyLevel.STRONG

    incidencia = _crear_incidencia(
        "nulos_reales",
        columna="cliente_id",
        categoria="completitud",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        clave_candidata=clave,
    )

    assert any(
        "clave candidata fuerte" in texto.lower()
        for texto in resultado.context
    )

# ---------------------------------------------------------------------------
# V7-B4.2 — Evidencias estructuradas y explicaciones básicas
# ---------------------------------------------------------------------------


def _evidencias_por_clave(
    diagnostico: Diagnostic,
) -> dict[str, DiagnosticEvidence]:
    """Indexa las evidencias de un diagnóstico por su clave estable."""
    return {
        evidencia.key: evidencia
        for evidencia in diagnostico.evidence
    }


def test_diagnostic_v7_mantiene_defaults_explicables() -> None:
    """El contrato V7 debe conservar defaults compatibles con V6."""
    diagnostico = Diagnostic(
        incident_type="prueba",
        category="validez",
        severity="baja",
        column_name="dato",
        incident_message="Mensaje.",
        context=(),
        possible_actions=(),
    )

    assert diagnostico.evidence == ()
    assert diagnostico.explanation == ""


def test_nulos_reales_generan_evidencias_v7() -> None:
    """Los nulos reales deben exponer medidas objetivas de completitud."""
    serie = pd.Series(
        ["A", "B", None, "C"],
        name="codigo",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    clave = evaluar_clave_candidata(analisis)

    resultado = generar_diagnostico(
        _crear_incidencia(
            "nulos_reales",
            columna="codigo",
            categoria="completitud",
        ),
        analisis=analisis,
        clave_candidata=clave,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["null_count"].value == 1
    assert evidencias["null_count"].source == "column_analysis"
    assert evidencias["analyzable_count"].value == 3
    assert evidencias["analyzable_ratio"].value == 75.0
    assert "candidate_key_level" in evidencias
    assert "1 valores nulos" in resultado.explanation
    assert "75,00 %" in resultado.explanation


def test_columna_constante_genera_evidencias_v7() -> None:
    """Una constante debe registrar cardinalidad y valor dominante."""
    serie = pd.Series(
        ["España", "España", "España"],
        name="pais",
        dtype="object",
    )
    analisis = analizar_columna(serie)

    resultado = generar_diagnostico(
        _crear_incidencia(
            "columna_constante",
            columna="pais",
            categoria="estructura",
        ),
        analisis=analisis,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["unique_count"].value == 1
    assert evidencias["most_frequent_value"].value == "España"
    assert evidencias["most_frequent_ratio"].value == 100.0
    assert "no determina" in resultado.explanation.lower()
    assert "innecesaria" in resultado.explanation.lower()


def test_inconsistencia_categorica_genera_evidencia_semantica_v7() -> None:
    """La inconsistencia categórica debe conservar evidencia semántica."""
    serie = pd.Series(
        ["Madrid", "madrid", "MADRID", "Sevilla"],
        name="ciudad",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "ciudad",
        SemanticType.CATEGORICAL,
    )

    resultado = generar_diagnostico(
        _crear_incidencia(
            "inconsistencia_categorica",
            columna="ciudad",
            categoria="consistencia",
        ),
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["unique_count"].value == 4
    assert evidencias["semantic_type"].value == "categorico"
    assert evidencias["semantic_confidence"].value == "alta"
    assert "no demuestra" in resultado.explanation.lower()
    assert "equivalentes" in resultado.explanation.lower()


def test_conversion_fecha_genera_evidencias_v7() -> None:
    """Los fallos temporales deben quedar cuantificados como evidencia."""
    serie = pd.Series(
        [
            "2026-01-01",
            "2026-02-01",
            "fecha_invalida",
            "2026-03-01",
        ],
        name="fecha",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("fecha", SemanticType.DATE)

    resultado = generar_diagnostico(
        _crear_incidencia(
            "conversion_fecha",
            columna="fecha",
            categoria="validez",
        ),
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["datetime_attempted_count"].value == 4
    assert evidencias["datetime_convertible_count"].value == 3
    assert evidencias["datetime_failed_count"].value == 1
    assert evidencias["datetime_success_ratio"].value == 75.0
    assert "1 valores" in resultado.explanation
    assert "información ambigua" in resultado.explanation


def test_outliers_explicacion_v7_no_los_declara_incorrectos() -> None:
    """La explicación V7 debe mantener atípico distinto de incorrecto."""
    serie = pd.Series(
        [10, 11, 12, 13, 1000],
        name="importe",
    )
    analisis = analizar_columna(serie)

    resultado = generar_diagnostico(
        _crear_incidencia(
            "outliers",
            columna="importe",
            categoria="validez",
        ),
        analisis=analisis,
    )

    assert "estadísticamente atípicos" in resultado.explanation
    assert "no determina que sean incorrectas" in resultado.explanation
    assert "eliminar" not in resultado.explanation.lower()


def test_incompatibilidad_tipo_explicacion_v7_es_conservadora() -> None:
    """La incompatibilidad no debe convertirse en error automático."""
    serie = pd.Series(
        ["10", "20", "error", "30"],
        name="cantidad",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia(
        "cantidad",
        SemanticType.NUMERIC,
    )

    resultado = generar_diagnostico(
        _crear_incidencia(
            "incompatibilidad_tipo",
            columna="cantidad",
            categoria="validez",
        ),
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["semantic_type"].value == "numerico"
    assert "no como prueba automática de error" in resultado.explanation
    assert "convertir" not in resultado.explanation.lower()


def test_incidencia_global_conserva_evidencia_del_incidente_v7() -> None:
    """Las incidencias globales pueden aportar evidencia sin columna."""
    incidencia = _crear_incidencia(
        "filas_duplicadas",
        columna=None,
        categoria="unicidad",
    )

    resultado = generar_diagnostico(incidencia)
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["incident_cantidad"].value == 1
    assert evidencias["incident_porcentaje"].value == 10.0
    assert all(
        evidencia.source == "incident"
        for evidencia in resultado.evidence
    )
    assert "no determina por sí sola" in resultado.explanation


def test_tipo_desconocido_tiene_fallback_explicable_v7() -> None:
    """Una incidencia futura debe mantener un fallback prudente."""
    resultado = generar_diagnostico(
        _crear_incidencia(
            "incidencia_futura",
            columna="dato",
        )
    )

    assert resultado.evidence == ()
    assert "información limitada" in resultado.explanation.lower()
    assert "mensaje y contexto" in resultado.explanation.lower()


# ---------------------------------------------------------------------------
# V7-B4.3 — Evidencias avanzadas C1/C2/C3
# ---------------------------------------------------------------------------


def test_b4_3_c1_inconsistencia_categorica_aporta_patrones_v7() -> None:
    """C1 aporta estructura sin convertir una variante en equivalencia."""
    serie = pd.Series(
        ["ABC-1234", "XYZ-5678", "DEF-9012", "AB-3456"],
        name="categoria",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("categoria", SemanticType.CATEGORICAL)
    incidencia = _crear_incidencia(
        "inconsistencia_categorica",
        columna="categoria",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["dominant_structural_pattern"].value == "AAA-NNNN"
    assert evidencias["dominant_structural_pattern_ratio"].value == 75.0
    assert evidencias["distinct_structural_pattern_count"].value == 2
    assert all(
        evidencias[clave].source == "structural_patterns"
        for clave in {
            "dominant_structural_pattern",
            "dominant_structural_pattern_ratio",
            "distinct_structural_pattern_count",
        }
    )
    assert "no demuestran que los valores sean equivalentes" in resultado.explanation


def test_b4_3_c2_c3_incompatibilidad_numerica_total_v7() -> None:
    """C2 y C3 explican una posible discrepancia sin ordenar conversión."""
    serie = pd.Series(["10", "20", "30", "40"], name="importe", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("importe", SemanticType.NUMERIC)
    incidencia = _crear_incidencia("incompatibilidad_tipo", columna="importe")

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["numeric_compatibility_count"].value == 4
    assert evidencias["numeric_compatibility"].value == 100.0
    assert evidencias["numeric_compatibility"].source == "semantic_compatibility"
    assert evidencias["physical_type"].value == "object"
    assert evidencias["observed_type"].value == "numeric"
    assert evidencias["type_coherence_status"].value == "potential_mismatch"
    assert evidencias["type_coherence_evidence_ratio"].value == 100.0
    assert evidencias["type_coherence_status"].source == "type_coherence"
    assert "posible discrepancia" in resultado.explanation.lower()
    assert "deba convertirse" in resultado.explanation.lower()


def test_b4_3_c3_incompatibilidad_parcial_es_evidencia_insuficiente_v7() -> None:
    """Una compatibilidad parcial no autoriza a concluir un cambio de tipo."""
    serie = pd.Series(["10", "20", "error", "30"], name="importe", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("importe", SemanticType.NUMERIC)
    incidencia = _crear_incidencia("incompatibilidad_tipo", columna="importe")

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["numeric_compatibility"].value == 75.0
    assert evidencias["type_coherence_status"].value == "insufficient_evidence"
    assert evidencias["type_coherence_evidence_ratio"].value == 75.0
    assert "no permite establecer una discrepancia concluyente" in resultado.explanation.lower()


def test_b4_3_conversion_fecha_combina_c2_y_c3_v7() -> None:
    """La conversión temporal usa compatibilidad y coherencia sin declarar invalidez."""
    serie = pd.Series(
        ["01/01/2026", "15/02/2026", "31/03/2026"],
        name="fecha",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("fecha", SemanticType.DATE)
    incidencia = _crear_incidencia("conversion_fecha", columna="fecha")

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["date_compatibility_count"].value == 3
    assert evidencias["date_compatibility"].value == 100.0
    assert evidencias["observed_type"].value == "date"
    assert evidencias["type_coherence_status"].value == "potential_mismatch"
    assert "compatibilidad observada" in resultado.explanation.lower()
    assert "deba convertirse" in resultado.explanation.lower()
    assert "fecha inválida" not in resultado.explanation.lower()


def test_b4_3_c3_tipo_fisico_coherente_v7() -> None:
    """C3 conserva el estado coherente cuando tipo físico y contenido coinciden."""
    serie = pd.Series([10, 20, 30, 40], name="importe", dtype="int64")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("importe", SemanticType.NUMERIC)
    incidencia = _crear_incidencia("incompatibilidad_tipo", columna="importe")

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["physical_type"].value == "int64"
    assert evidencias["observed_type"].value == "numeric"
    assert evidencias["type_coherence_status"].value == "coherent"
    assert "resultan coherentes" in resultado.explanation.lower()


def test_b4_3_identificador_numerico_textual_queda_protegido_v7() -> None:
    """Un identificador textual numérico no se interpreta como conversión necesaria."""
    serie = pd.Series(
        ["1001", "1002", "1003", "1004"],
        name="cliente_id",
        dtype="object",
    )
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("cliente_id", SemanticType.IDENTIFIER)
    incidencia = _crear_incidencia("incompatibilidad_tipo", columna="cliente_id")

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert "numeric_compatibility" not in evidencias
    assert evidencias["observed_type"].value is None
    assert evidencias["type_coherence_status"].value == "insufficient_evidence"
    assert evidencias["type_coherence_evidence_ratio"].value is None
    assert "no permite establecer una discrepancia concluyente" in resultado.explanation.lower()


def test_b4_3_cinco_digitos_no_adquiere_significado_de_negocio_v7() -> None:
    """C1 puede describir NNNNN sin convertirlo en código postal ni número."""
    serie = pd.Series(["28053", "28041", "28012"], name="valor", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("valor", SemanticType.IDENTIFIER)
    incidencia = _crear_incidencia("incompatibilidad_tipo", columna="valor")

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    assert evidencias["dominant_structural_pattern"].value == "NNNNN"
    assert "numeric_compatibility" not in evidencias
    assert evidencias["type_coherence_status"].value == "insufficient_evidence"
    assert "postal" not in resultado.explanation.lower()


def test_b4_3_evidencias_avanzadas_son_selectivas_v7() -> None:
    """Incidencias no relacionadas no reciben un volcado de C1/C2/C3."""
    serie = pd.Series(["10", "20", "30", None], name="dato", dtype="object")
    analisis = analizar_columna(serie)
    inferencia = _crear_inferencia("dato", SemanticType.NUMERIC)
    incidencia = _crear_incidencia(
        "nulos_reales",
        columna="dato",
        categoria="completitud",
    )

    resultado = generar_diagnostico(
        incidencia,
        analisis=analisis,
        inferencia=inferencia,
    )
    evidencias = _evidencias_por_clave(resultado)

    claves_avanzadas = {
        "dominant_structural_pattern",
        "dominant_structural_pattern_ratio",
        "distinct_structural_pattern_count",
        "numeric_compatibility",
        "date_compatibility",
        "boolean_compatibility",
        "physical_type",
        "observed_type",
        "type_coherence_status",
        "type_coherence_evidence_ratio",
    }
    assert claves_avanzadas.isdisjoint(evidencias)

# ---------------------------------------------------------------------------
# V7-B5.3 - Explicación de severidad
# ---------------------------------------------------------------------------


def test_b5_diagnostic_mantiene_default_de_explicacion_severidad() -> None:
    """El nuevo campo conserva compatibilidad al construir Diagnostic."""
    diagnostico = Diagnostic(
        incident_type="prueba",
        category="validez",
        severity="baja",
        column_name="dato",
        incident_message="Mensaje.",
        context=(),
        possible_actions=(),
    )

    assert diagnostico.severity_explanation == ""


def test_b5_severidad_baja_explica_limite_4_99_por_ciento() -> None:
    """Un porcentaje inferior al 5 % explica la severidad baja recibida."""
    incidencia = _crear_incidencia(
        "nulos_reales",
        categoria="completitud",
        severidad="baja",
    )
    incidencia["porcentaje"] = 4.99

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "baja"
    assert "4,99 %" in resultado.severity_explanation
    assert "inferior al 5 %" in resultado.severity_explanation
    assert "severidad baja" in resultado.severity_explanation


def test_b5_severidad_media_explica_limite_inferior_5_por_ciento() -> None:
    """El 5 % pertenece al intervalo de severidad media."""
    incidencia = _crear_incidencia(
        "espacios_texto",
        categoria="consistencia",
        severidad="media",
    )
    incidencia["porcentaje"] = 5.0

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "media"
    assert "5,00 %" in resultado.severity_explanation
    assert "igual o superior al 5 %" in resultado.severity_explanation
    assert "inferior al 20 %" in resultado.severity_explanation


def test_b5_severidad_media_explica_limite_superior_19_99_por_ciento() -> None:
    """El 19,99 % sigue perteneciendo al intervalo medio."""
    incidencia = _crear_incidencia(
        "incompatibilidad_tipo",
        severidad="media",
    )
    incidencia["porcentaje"] = 19.99

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "media"
    assert "19,99 %" in resultado.severity_explanation
    assert "inferior al 20 %" in resultado.severity_explanation


def test_b5_severidad_alta_explica_limite_20_por_ciento() -> None:
    """El 20 % inicia el intervalo de severidad alta."""
    incidencia = _crear_incidencia(
        "conversion_fecha",
        severidad="alta",
    )
    incidencia["porcentaje"] = 20.0

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "alta"
    assert "20,00 %" in resultado.severity_explanation
    assert "igual o superior al 20 %" in resultado.severity_explanation
    assert "severidad alta" in resultado.severity_explanation


def test_b5_severidad_fija_se_explica_sin_recalcular() -> None:
    """Una severidad fija describe la regla existente del motor."""
    incidencia = _crear_incidencia(
        "outliers",
        severidad="baja",
    )

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "baja"
    assert "severidad baja fija" in resultado.severity_explanation
    assert "no recalcula la severidad" in resultado.severity_explanation


def test_b5_discrepancia_en_severidad_fija_conserva_valor_recibido() -> None:
    """El diagnóstico explica una discrepancia fija sin corregirla por su cuenta."""
    incidencia = _crear_incidencia(
        "columna_constante",
        categoria="estructura",
        severidad="alta",
    )

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "alta"
    assert "severidad fija baja" in resultado.severity_explanation
    assert "incidencia recibida indica 'alta'" in resultado.severity_explanation
    assert "conserva el valor recibido" in resultado.severity_explanation


def test_b5_porcentaje_ausente_no_inventa_justificacion() -> None:
    """Sin porcentaje, B5 declara que no puede explicar el nivel asignado."""
    incidencia = _crear_incidencia(
        "filas_duplicadas",
        columna=None,
        categoria="unicidad",
        severidad="media",
    )
    incidencia["porcentaje"] = None

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "media"
    assert "no se dispone del porcentaje" in resultado.severity_explanation


def test_b5_tipo_no_catalogado_no_inventa_explicacion_severidad() -> None:
    """Un tipo desconocido no recibe una justificación de severidad inventada."""
    incidencia = _crear_incidencia(
        "tipo_no_catalogado",
        severidad="media",
    )

    resultado = generar_diagnostico(incidencia)

    assert resultado.severity == "media"
    assert resultado.severity_explanation == ""

