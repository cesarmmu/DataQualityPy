"""Tests del motor de inferencia semántica."""

import pandas as pd

from src.column_analysis import analizar_columna
from src.inference import (
    InferenceConfidence,
    SemanticType,
    es_valor_booleano_compatible,
    inferir_tipo_semantico,
)


def _analizar_e_inferir(
    serie: pd.Series,
    **kwargs,
):
    """Analiza una serie e infiere su tipo semántico."""
    analisis = analizar_columna(serie)

    serie_evaluable = serie.dropna()

    if serie_evaluable.dtype == "object" or isinstance(
        serie_evaluable.dtype,
        pd.StringDtype,
    ):
        from src.quality import es_nulo_textual

        mascara_nulos_textuales = serie_evaluable.map(
            es_nulo_textual
        )
        serie_evaluable = serie_evaluable.loc[
            ~mascara_nulos_textuales
        ]

    return inferir_tipo_semantico(
        analisis,
        serie_evaluable,
        **kwargs,
    )


def test_infiere_identificador_numerico():
    """Un ID numérico único debe interpretarse como identificador."""
    serie = pd.Series(
        [1001, 1002, 1003, 1004],
        name="cliente_id",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.IDENTIFIER
    assert resultado.confidence is InferenceConfidence.HIGH
    assert resultado.source == "inferred"


def test_infiere_identificador_textual():
    """Un código textual único puede funcionar como identificador."""
    serie = pd.Series(
        ["A001", "A002", "A003", "A004"],
        name="codigo_cliente",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.IDENTIFIER
    assert resultado.confidence is InferenceConfidence.HIGH


def test_no_fuerza_identificador_sin_unicidad_suficiente():
    """El nombre indicativo no basta si la unicidad es insuficiente."""
    serie = pd.Series(
        [1, 1, 1, 2],
        name="cliente_id",
    )

    resultado = _analizar_e_inferir(
        serie,
        umbral_unicidad=90,
    )

    assert resultado.semantic_type is not SemanticType.IDENTIFIER


def test_infiere_booleano_nativo():
    """Una columna booleana nativa debe reconocerse con confianza alta."""
    serie = pd.Series(
        [True, False, True, False],
        name="activo",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.BOOLEAN
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_booleano_binario_numerico():
    """Los valores 0 y 1 deben poder interpretarse como binarios."""
    serie = pd.Series(
        [0, 1, 0, 1, 1, 0],
        name="activo",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.BOOLEAN
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_booleano_textual():
    """Un par booleano textual inequívoco debe reconocerse."""
    serie = pd.Series(
        ["Sí", "No", "Sí", "No"],
        name="activo",
        dtype="object",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.BOOLEAN
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_fecha_textual():
    """Una columna textual formada por fechas debe reconocerse."""
    serie = pd.Series(
        [
            "01/01/2026",
            "15/02/2026",
            "31/03/2026",
            "20/04/2026",
        ],
        name="fecha_alta",
        dtype="object",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.DATE
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_fecha_hora_nativa():
    """Una columna temporal con componente horario debe ser fecha-hora."""
    serie = pd.Series(
        pd.to_datetime(
            [
                "2026-01-01 10:30:00",
                "2026-01-02 14:45:00",
                "2026-01-03 08:15:00",
            ]
        ),
        name="fecha_evento",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.DATETIME
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_numerico_nativo():
    """Una columna numérica nativa debe reconocerse como numérica."""
    serie = pd.Series(
        [10.5, 20.0, 30.5, 40.0],
        name="precio",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.NUMERIC
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_numerico_almacenado_como_texto():
    """Una columna object numérica debe reconocerse semánticamente."""
    serie = pd.Series(
        ["22", "38", "NA", "35", None, "54"],
        name="Age",
        dtype="object",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.NUMERIC
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_numerico_con_conversion_parcial():
    """Una conversión suficiente pero imperfecta debe reducir confianza."""
    serie = pd.Series(
        ["10", "20", "30", "40", "error"],
        name="cantidad",
        dtype="object",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.NUMERIC
    assert resultado.confidence is InferenceConfidence.MEDIUM


def test_infiere_categorico():
    """Una columna de baja cardinalidad debe reconocerse como categórica."""
    serie = pd.Series(
        ["Madrid"] * 5
        + ["Sevilla"] * 5
        + ["Valencia"] * 5
        + ["Bilbao"] * 5,
        name="ciudad",
        dtype="object",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.CATEGORICAL
    assert resultado.confidence is InferenceConfidence.HIGH


def test_infiere_texto_libre():
    """Texto de alta cardinalidad debe terminar como texto libre."""
    serie = pd.Series(
        [
            "Comentario completamente diferente número uno",
            "Segundo comentario con contenido independiente",
            "Una tercera observación distinta de las anteriores",
            "Texto libre correspondiente al cuarto registro",
            "Quinto comentario con información específica",
        ],
        name="comentario",
        dtype="object",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.FREE_TEXT
    assert resultado.confidence is InferenceConfidence.MEDIUM


def test_identificador_tiene_prioridad_sobre_numerico():
    """La jerarquía debe evitar tratar un identificador como magnitud."""
    serie = pd.Series(
        [1001, 1002, 1003, 1004],
        name="id",
    )

    resultado = _analizar_e_inferir(serie)

    assert resultado.semantic_type is SemanticType.IDENTIFIER
    assert resultado.semantic_type is not SemanticType.NUMERIC


def test_umbral_fecha_permite_conversion_temporal_al_80_por_ciento():
    """El umbral temporal debe aceptar una conversión que alcance el 80 %."""
    serie = pd.Series(
        [
            "01/01/2026",
            "15/02/2026",
            "31/03/2026",
            "20/04/2026",
            "valor_invalido",
        ],
        name="fecha_alta",
        dtype="object",
    )

    resultado = _analizar_e_inferir(
        serie,
        umbral_fecha=80.0,
    )

    assert resultado.semantic_type is SemanticType.DATE
    assert resultado.confidence is InferenceConfidence.MEDIUM


def test_umbral_fecha_rechaza_conversion_temporal_por_debajo_del_umbral():
    """Una conversión temporal del 80 % no debe superar un umbral del 90 %."""
    serie = pd.Series(
        [
            "01/01/2026",
            "15/02/2026",
            "31/03/2026",
            "20/04/2026",
            "valor_invalido",
        ],
        name="fecha_alta",
        dtype="object",
    )

    resultado = _analizar_e_inferir(
        serie,
        umbral_fecha=90.0,
    )

    assert resultado.semantic_type is not SemanticType.DATE
    assert resultado.semantic_type is not SemanticType.DATETIME


def test_tipo_declarado_tiene_prioridad_sobre_inferencia_automatica():
    """Una declaración explícita debe prevalecer sobre las evidencias."""
    serie = pd.Series(
        [1001, 1002, 1003, 1004],
        name="cliente_id",
    )

    resultado = _analizar_e_inferir(
        serie,
        tipo_declarado="numerico",
    )

    assert resultado.semantic_type is SemanticType.NUMERIC
    assert resultado.confidence is InferenceConfidence.HIGH
    assert resultado.source == "declared"


def test_tipo_declarado_conserva_evidencia_de_su_origen():
    """El resultado debe explicar que el tipo procede de configuración."""
    serie = pd.Series(
        ["Madrid", "Sevilla", "Valencia", "Bilbao"],
        name="ciudad",
        dtype="object",
    )

    resultado = _analizar_e_inferir(
        serie,
        tipo_declarado="texto_libre",
    )

    assert resultado.semantic_type is SemanticType.FREE_TEXT
    assert resultado.source == "declared"
    assert resultado.evidence == (
        "El tipo semántico fue declarado explícitamente "
        "en la configuración.",
    )


def test_sin_tipo_declarado_mantiene_inferencia_automatica():
    """La ausencia de declaración debe conservar el comportamiento previo."""
    serie = pd.Series(
        ["22", "38", "NA", "35", None, "54"],
        name="Age",
        dtype="object",
    )

    resultado = _analizar_e_inferir(
        serie,
        tipo_declarado=None,
    )

    assert resultado.semantic_type is SemanticType.NUMERIC
    assert resultado.confidence is InferenceConfidence.HIGH
    assert resultado.source == "inferred"


def test_valores_booleanos_nativos_son_compatibles():
    """True y False deben ser compatibles con el tipo booleano."""
    assert es_valor_booleano_compatible(True)
    assert es_valor_booleano_compatible(False)


def test_valores_binarios_numericos_son_compatibles():
    """Solo 0 y 1 deben aceptarse como representaciones numéricas booleanas."""
    assert es_valor_booleano_compatible(0)
    assert es_valor_booleano_compatible(1)
    assert es_valor_booleano_compatible(0.0)
    assert es_valor_booleano_compatible(1.0)

    assert not es_valor_booleano_compatible(2)
    assert not es_valor_booleano_compatible(-1)


def test_valores_booleanos_textuales_son_compatibles():
    """Las representaciones textuales admitidas deben normalizarse."""
    valores_compatibles = (
        "true",
        "FALSE",
        " Yes ",
        "no",
        "SI",
        " Sí ",
    )

    for valor in valores_compatibles:
        assert es_valor_booleano_compatible(valor)


def test_valores_ajenos_al_vocabulario_booleano_son_incompatibles():
    """Un valor no reconocido no debe considerarse booleano compatible."""
    valores_incompatibles = (
        "quizá",
        "activo",
        "2",
        "",
        None,
    )

    for valor in valores_incompatibles:
        assert not es_valor_booleano_compatible(valor)

