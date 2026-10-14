"""Tests para el resumen ejecutivo V3 de DataQualityPy."""

from src.summary import generar_resumen_ejecutivo


def _tipos_semanticos_base() -> dict:
    """Devuelve tipos semánticos representativos para los tests."""
    return {
        "id_cliente": {
            "tipo": "identificador",
            "confianza": "alta",
            "evidencia": "Identificador.",
            "origen": "inferred",
        },
        "edad": {
            "tipo": "numerico",
            "confianza": "alta",
            "evidencia": "Numérico.",
            "origen": "inferred",
        },
        "fecha_alta": {
            "tipo": "fecha",
            "confianza": "alta",
            "evidencia": "Fecha.",
            "origen": "inferred",
        },
        "activo": {
            "tipo": "booleano_binario",
            "confianza": "alta",
            "evidencia": "Booleano.",
            "origen": "inferred",
        },
        "categoria": {
            "tipo": "categorico",
            "confianza": "media",
            "evidencia": "Categórico.",
            "origen": "inferred",
        },
        "comentario": {
            "tipo": "texto_libre",
            "confianza": "media",
            "evidencia": "Texto libre.",
            "origen": "inferred",
        },
    }


def _calidad_base() -> dict:
    """Devuelve una estructura mínima de calidad para el resumen."""
    return {
        "duplicados": {},
        "nulos": {},
        "nulos_textuales": {},
        "identificadores": {},
        "columnas_problematicas": {},
        "texto": {},
        "outliers": {},
        "incompatibilidades_tipo": {},
        "reglas_negocio": {},
        "fechas": {},
    }


def _configuracion_base() -> dict:
    """Devuelve la configuración relevante para cobertura."""
    return {
        "columnas_clave": [],
        "reglas_columnas": {},
    }


def test_generar_resumen_ejecutivo_conserva_recuentos_y_principales() -> None:
    """Conserva los recuentos V2 y la selección de incidencias principales."""
    incidencias = [
        {
            "tipo": "outliers",
            "categoria": "validez",
            "severidad": "baja",
            "columna": "precio",
            "cantidad": 2,
            "porcentaje": 10.0,
            "mensaje": "Incidencia baja.",
        },
        {
            "tipo": "nulos_textuales",
            "categoria": "completitud",
            "severidad": "alta",
            "columna": "observaciones",
            "cantidad": 10,
            "porcentaje": 100.0,
            "mensaje": "Incidencia alta.",
        },
        {
            "tipo": "filas_duplicadas",
            "categoria": "unicidad",
            "severidad": "media",
            "columna": None,
            "cantidad": 2,
            "porcentaje": 10.0,
            "mensaje": "Incidencia media 1.",
        },
        {
            "tipo": "espacios_texto",
            "categoria": "consistencia",
            "severidad": "media",
            "columna": "categoria",
            "cantidad": 2,
            "porcentaje": 10.0,
            "mensaje": "Incidencia media 2.",
        },
        {
            "tipo": "columna_constante",
            "categoria": "estructura",
            "severidad": "baja",
            "columna": "pais",
            "cantidad": None,
            "porcentaje": None,
            "mensaje": "Incidencia baja 2.",
        },
        {
            "tipo": "conversion_fecha",
            "categoria": "validez",
            "severidad": "media",
            "columna": "fecha",
            "cantidad": 2,
            "porcentaje": 10.0,
            "mensaje": "Incidencia media 3.",
        },
    ]

    resumen = generar_resumen_ejecutivo(
        incidencias,
        _tipos_semanticos_base(),
        _calidad_base(),
        _configuracion_base(),
    )

    assert resumen["total_incidencias"] == 6
    assert resumen["por_severidad"] == {
        "alta": 1,
        "media": 3,
        "baja": 2,
    }
    assert resumen["por_categoria"] == {
        "completitud": 1,
        "unicidad": 1,
        "estructura": 1,
        "consistencia": 1,
        "validez": 2,
    }

    principales = resumen["principales_incidencias"]
    assert len(principales) == 5
    assert [
        incidencia["severidad"]
        for incidencia in principales
    ] == [
        "alta",
        "media",
        "media",
        "media",
        "baja",
    ]


def test_resumen_cuenta_los_siete_tipos_semanticos() -> None:
    """Cuenta todos los tipos semánticos y conserva los tipos ausentes a cero."""
    tipos_semanticos = _tipos_semanticos_base()
    tipos_semanticos["momento"] = {
        "tipo": "fecha_hora",
        "confianza": "alta",
        "evidencia": "Fecha y hora.",
        "origen": "inferred",
    }

    resumen = generar_resumen_ejecutivo(
        [],
        tipos_semanticos,
        _calidad_base(),
        _configuracion_base(),
    )

    assert resumen["tipos_semanticos"] == {
        "numerico": 1,
        "fecha": 1,
        "fecha_hora": 1,
        "booleano_binario": 1,
        "categorico": 1,
        "identificador": 1,
        "texto_libre": 1,
    }


def test_cobertura_con_controles_aplicados_y_no_configurados() -> None:
    """Clasifica controles aplicables y controles que requieren configuración."""
    resumen = generar_resumen_ejecutivo(
        [],
        _tipos_semanticos_base(),
        _calidad_base(),
        _configuracion_base(),
    )

    assert resumen["cobertura_auditoria"] == {
        "controles_aplicados": [
            "completitud",
            "unicidad_general",
            "consistencia_texto",
            "outliers",
            "compatibilidad_semantica",
        ],
        "controles_no_aplicables": [],
        "controles_no_configurados": [
            "unicidad_clave",
            "reglas_negocio",
        ],
    }


def test_cobertura_marca_outliers_no_aplicable_sin_numericos() -> None:
    """Outliers no es aplicable cuando no existen columnas numéricas."""
    tipos_semanticos = {
        "categoria": {
            "tipo": "categorico",
            "confianza": "alta",
            "evidencia": "Categórico.",
            "origen": "inferred",
        },
        "comentario": {
            "tipo": "texto_libre",
            "confianza": "media",
            "evidencia": "Texto libre.",
            "origen": "inferred",
        },
    }

    resumen = generar_resumen_ejecutivo(
        [],
        tipos_semanticos,
        _calidad_base(),
        _configuracion_base(),
    )

    cobertura = resumen["cobertura_auditoria"]
    assert "outliers" in cobertura["controles_no_aplicables"]
    assert "outliers" not in cobertura["controles_aplicados"]


def test_cobertura_marca_compatibilidad_no_aplicable_sin_tipos_comprobables() -> None:
    """Compatibilidad no aplica sin tipos numérico, temporal o booleano."""
    tipos_semanticos = {
        "categoria": {
            "tipo": "categorico",
            "confianza": "alta",
            "evidencia": "Categórico.",
            "origen": "inferred",
        },
        "id": {
            "tipo": "identificador",
            "confianza": "alta",
            "evidencia": "Identificador.",
            "origen": "inferred",
        },
        "comentario": {
            "tipo": "texto_libre",
            "confianza": "media",
            "evidencia": "Texto libre.",
            "origen": "inferred",
        },
    }

    resumen = generar_resumen_ejecutivo(
        [],
        tipos_semanticos,
        _calidad_base(),
        _configuracion_base(),
    )

    cobertura = resumen["cobertura_auditoria"]
    assert (
        "compatibilidad_semantica"
        in cobertura["controles_no_aplicables"]
    )
    assert (
        "compatibilidad_semantica"
        not in cobertura["controles_aplicados"]
    )


def test_cobertura_marca_consistencia_texto_no_aplicable_sin_texto() -> None:
    """Consistencia textual no aplica sin columnas textuales o categóricas."""
    tipos_semanticos = {
        "edad": {
            "tipo": "numerico",
            "confianza": "alta",
            "evidencia": "Numérico.",
            "origen": "inferred",
        },
        "activo": {
            "tipo": "booleano_binario",
            "confianza": "alta",
            "evidencia": "Booleano.",
            "origen": "inferred",
        },
    }

    resumen = generar_resumen_ejecutivo(
        [],
        tipos_semanticos,
        _calidad_base(),
        _configuracion_base(),
    )

    cobertura = resumen["cobertura_auditoria"]
    assert (
        "consistencia_texto"
        in cobertura["controles_no_aplicables"]
    )
    assert "consistencia_texto" not in cobertura["controles_aplicados"]


def test_cobertura_marca_unicidad_clave_aplicada_si_esta_configurada() -> None:
    """La unicidad por clave figura aplicada cuando existe configuración."""
    configuracion = _configuracion_base()
    configuracion["columnas_clave"] = ["id_cliente"]

    resumen = generar_resumen_ejecutivo(
        [],
        _tipos_semanticos_base(),
        _calidad_base(),
        configuracion,
    )

    cobertura = resumen["cobertura_auditoria"]
    assert "unicidad_clave" in cobertura["controles_aplicados"]
    assert (
        "unicidad_clave"
        not in cobertura["controles_no_configurados"]
    )


def test_cobertura_marca_reglas_negocio_aplicadas_si_estan_configuradas() -> None:
    """Las reglas de negocio figuran aplicadas cuando existe alguna regla."""
    configuracion = _configuracion_base()
    configuracion["reglas_columnas"] = {
        "edad": {
            "min": 0,
            "max": 120,
        },
    }

    resumen = generar_resumen_ejecutivo(
        [],
        _tipos_semanticos_base(),
        _calidad_base(),
        configuracion,
    )

    cobertura = resumen["cobertura_auditoria"]
    assert "reglas_negocio" in cobertura["controles_aplicados"]
    assert (
        "reglas_negocio"
        not in cobertura["controles_no_configurados"]
    )


def test_resumen_sin_incidencias_mantiene_estructura_completa() -> None:
    """Un dataset sin incidencias conserva todo el contrato del resumen V3."""
    resumen = generar_resumen_ejecutivo(
        [],
        _tipos_semanticos_base(),
        _calidad_base(),
        _configuracion_base(),
    )

    assert resumen["total_incidencias"] == 0
    assert resumen["por_severidad"] == {
        "alta": 0,
        "media": 0,
        "baja": 0,
    }
    assert resumen["por_categoria"] == {
        "completitud": 0,
        "unicidad": 0,
        "estructura": 0,
        "consistencia": 0,
        "validez": 0,
    }
    assert resumen["principales_incidencias"] == []
    assert "tipos_semanticos" in resumen
    assert "cobertura_auditoria" in resumen
