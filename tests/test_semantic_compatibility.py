"""Tests dirigidos de compatibilidad semántica básica V7-C2."""

import pandas as pd
import pytest

from src.column_analysis import analizar_columna
from src.semantic_compatibility import (
    SemanticCompatibilityType,
    analizar_compatibilidad_semantica,
)


def _evidencia_por_tipo(resultado):
    """Indexa las evidencias por tipo de compatibilidad."""
    return {
        evidencia.compatibility_type: evidencia
        for evidencia in resultado.compatibilities
    }


def test_compatibilidad_numerica_total_v7():
    serie = pd.Series(["10", "20.5", "-3", "40"], name="importe", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.NUMERIC]
    assert resultado.analyzed_count == 4
    assert evidencia.compatible_count == 4
    assert evidencia.compatible_ratio == pytest.approx(100.0)


def test_compatibilidad_numerica_parcial_v7():
    serie = pd.Series(["10", "20", "error", "30"], name="cantidad", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.NUMERIC]
    assert evidencia.compatible_count == 3
    assert evidencia.compatible_ratio == pytest.approx(75.0)


def test_compatibilidad_fecha_total_v7():
    serie = pd.Series(["01/01/2026", "15/02/2026", "31/03/2026"], name="fecha", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.DATE]
    assert resultado.analyzed_count == 3
    assert evidencia.compatible_count == 3
    assert evidencia.compatible_ratio == pytest.approx(100.0)


def test_compatibilidad_fecha_parcial_v7():
    serie = pd.Series(["01/01/2026", "texto_invalido", "31/03/2026"], name="fecha", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.DATE]
    assert evidencia.compatible_count == 2
    assert evidencia.compatible_ratio == pytest.approx(200 / 3)


def test_compatibilidad_booleana_textual_v7():
    serie = pd.Series(["true", "FALSE", "yes", "No", "sí", "si"], name="activo", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.BOOLEAN]
    assert evidencia.compatible_count == 6
    assert evidencia.compatible_ratio == pytest.approx(100.0)


def test_compatibilidad_booleana_cero_uno_v7():
    serie = pd.Series([0, 1, 0, 1], name="indicador", dtype="int64")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.BOOLEAN]
    assert evidencia.compatible_count == 4
    assert evidencia.compatible_ratio == pytest.approx(100.0)


def test_compatibilidad_email_basica_v7():
    serie = pd.Series([
        "ana@example.com", "usuario.prueba@dominio.es",
        "sin-arroba.example.com", "otro@dominio.org",
    ], name="contacto", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.EMAIL]
    assert evidencia.compatible_count == 3
    assert evidencia.compatible_ratio == pytest.approx(75.0)


def test_compatibilidad_url_solo_http_https_v7():
    serie = pd.Series([
        "https://example.com", "http://example.org/ruta",
        "ftp://example.net", "example.com",
    ], name="url", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.URL]
    assert evidencia.compatible_count == 2
    assert evidencia.compatible_ratio == pytest.approx(50.0)


def test_compatibilidad_ipv4_valida_limites_v7():
    serie = pd.Series([
        "192.168.1.1", "0.0.0.0", "255.255.255.255",
        "256.1.1.1", "192.168.1",
    ], name="ip", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.IPV4]
    assert evidencia.compatible_count == 3
    assert evidencia.compatible_ratio == pytest.approx(60.0)


def test_compatibilidad_uuid_estandar_v7():
    serie = pd.Series([
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "no-es-un-uuid",
    ], name="identificador", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.UUID]
    assert evidencia.compatible_count == 2
    assert evidencia.compatible_ratio == pytest.approx(200 / 3)


def test_c2_excluye_nulos_reales_y_textuales_v7():
    serie = pd.Series(["10", "NA", None, "20", "", "30"], name="valor", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencia = _evidencia_por_tipo(resultado)[SemanticCompatibilityType.NUMERIC]
    assert resultado.analyzed_count == 3
    assert evidencia.compatible_count == 3
    assert evidencia.compatible_ratio == pytest.approx(100.0)


def test_c2_columna_sin_valores_analizables_v7():
    serie = pd.Series([None, "NA", "", "null"], name="vacia", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    assert resultado.analyzed_count == 0
    assert resultado.compatibilities == ()


def test_c2_conserva_todas_las_compatibilidades_v7():
    serie = pd.Series(["texto", "otro", "valor"], name="generica", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    tipos = {e.compatibility_type for e in resultado.compatibilities}
    assert tipos == set(SemanticCompatibilityType)
    assert len(resultado.compatibilities) == 7


def test_c2_cinco_digitos_no_infiere_codigo_postal_v7():
    serie = pd.Series(["28053", "28041", "28012"], name="valor", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencias = _evidencia_por_tipo(resultado)
    assert evidencias[SemanticCompatibilityType.NUMERIC].compatible_ratio == pytest.approx(100.0)
    assert set(evidencias) == set(SemanticCompatibilityType)


def test_c2_permite_compatibilidades_solapadas_v7():
    serie = pd.Series(["0", "1", "0", "1"], name="indicador", dtype="object")
    resultado = analizar_compatibilidad_semantica(analizar_columna(serie))
    evidencias = _evidencia_por_tipo(resultado)
    assert evidencias[SemanticCompatibilityType.NUMERIC].compatible_ratio == pytest.approx(100.0)
    assert evidencias[SemanticCompatibilityType.BOOLEAN].compatible_ratio == pytest.approx(100.0)
