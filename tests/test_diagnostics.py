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