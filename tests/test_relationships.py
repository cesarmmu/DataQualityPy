"""Tests de relaciones entre columnas de DataQualityPy."""

import pandas as pd

from src.candidate_keys import (
    CandidateKeyAnalysis,
    CandidateKeyLevel,
    evaluar_claves_candidatas,
)
from src.column_analysis import (
    ColumnAnalysis,
    analizar_columnas,
)
from src.inference import InferenceConfidence
from src.relationships import (
    PresencePattern,
    RelationshipAnalysis,
    analizar_claves_compuestas,
    analizar_relaciones,
    analizar_relaciones_funcionales,
    analizar_relaciones_presencia,
)


def _preparar_evidencias(
    datos: pd.DataFrame,
) -> tuple[
    dict[object, ColumnAnalysis],
    dict[object, CandidateKeyAnalysis],
]:
    """Genera las evidencias previas necesarias para los tests."""
    analisis = analizar_columnas(datos)
    claves = evaluar_claves_candidatas(analisis)

    return analisis, claves


def test_clave_compuesta_fuerte_v6() -> None:
    """Detecta una clave fuerte formada por dos columnas."""
    datos = pd.DataFrame(
        {
            "factura": [
                "F1",
                "F1",
                "F2",
                "F2",
            ],
            "linea": [
                1,
                2,
                1,
                2,
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_claves_compuestas(
        datos,
        analisis,
        claves,
    )

    assert len(resultados) == 1

    resultado = resultados[0]

    assert resultado.columns == (
        "factura",
        "linea",
    )
    assert (
        resultado.level
        is CandidateKeyLevel.STRONG
    )
    assert (
        resultado.confidence
        is InferenceConfidence.HIGH
    )
    assert resultado.total_rows == 4
    assert resultado.analyzable_rows == 4
    assert resultado.null_rows == 0
    assert resultado.unique_combinations == 4
    assert resultado.uniqueness_ratio == 100.0
    assert resultado.duplicate_excess_count == 0
    assert resultado.evidence


def test_clave_compuesta_posible_por_nulos_v6() -> None:
    """
    Una combinación única entre filas analizables es POSIBLE
    cuando existen ausencias.
    """
    datos = pd.DataFrame(
        {
            "factura": [
                "F1",
                "F1",
                "F2",
                "F2",
            ],
            "linea": [
                1,
                2,
                1,
                None,
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_claves_compuestas(
        datos,
        analisis,
        claves,
    )

    assert len(resultados) == 1

    resultado = resultados[0]

    assert (
        resultado.level
        is CandidateKeyLevel.POSSIBLE
    )
    assert (
        resultado.confidence
        is InferenceConfidence.MEDIUM
    )
    assert resultado.analyzable_rows == 3
    assert resultado.null_rows == 1
    assert resultado.unique_combinations == 3
    assert resultado.uniqueness_ratio == 100.0


def test_clave_compuesta_posible_muestra_pequena_v6() -> None:
    """Una muestra inferior al mínimo produce confianza baja."""
    datos = pd.DataFrame(
        {
            "grupo": [
                "A",
                "B",
            ],
            "posicion": [
                1,
                2,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    claves: dict[
        object,
        CandidateKeyAnalysis,
    ] = {}

    resultados = analizar_claves_compuestas(
        datos,
        analisis,
        claves,
    )

    assert len(resultados) == 1

    resultado = resultados[0]

    assert (
        resultado.level
        is CandidateKeyLevel.POSSIBLE
    )
    assert (
        resultado.confidence
        is InferenceConfidence.LOW
    )
    assert resultado.analyzable_rows == 2


def test_no_devuelve_clave_compuesta_no_candidata_v6() -> None:
    """Las combinaciones con poca unicidad no se conservan."""
    datos = pd.DataFrame(
        {
            "grupo": [
                "A",
                "A",
                "A",
                "A",
            ],
            "tipo": [
                "X",
                "Y",
                "X",
                "Y",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_claves_compuestas(
        datos,
        analisis,
        claves,
    )

    assert resultados == ()


def test_clave_individual_fuerte_excluye_combinacion_v6() -> None:
    """Una clave individual fuerte evita combinaciones triviales."""
    datos = pd.DataFrame(
        {
            "id": [
                1,
                2,
                3,
                4,
            ],
            "provincia": [
                "Madrid",
                "Madrid",
                "Toledo",
                "Toledo",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    assert (
        claves["id"].level
        is CandidateKeyLevel.STRONG
    )

    resultados = analizar_claves_compuestas(
        datos,
        analisis,
        claves,
    )

    assert resultados == ()


def test_columna_constante_no_participa_en_clave_v6() -> None:
    """Las columnas constantes no generan claves compuestas."""
    datos = pd.DataFrame(
        {
            "grupo": [
                "A",
                "A",
                "B",
                "B",
            ],
            "constante": [
                "X",
                "X",
                "X",
                "X",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_claves_compuestas(
        datos,
        analisis,
        claves,
    )

    assert resultados == ()


def test_relacion_funcional_unidireccional_v6() -> None:
    """Detecta una relación funcional en la dirección correcta."""
    datos = pd.DataFrame(
        {
            "municipio": [
                "M1",
                "M1",
                "M2",
                "M2",
                "M3",
                "M3",
            ],
            "provincia": [
                "P1",
                "P1",
                "P1",
                "P1",
                "P2",
                "P2",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    pares = {
        (
            relacion.source_column,
            relacion.target_column,
        )
        for relacion in resultados
    }

    assert (
        "municipio",
        "provincia",
    ) in pares

    assert (
        "provincia",
        "municipio",
    ) not in pares


def test_relacion_funcional_bidireccional_v6() -> None:
    """Conserva ambas direcciones cuando ambas son consistentes."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "01",
                "01",
                "02",
                "02",
                "03",
                "03",
            ],
            "descripcion": [
                "Uno",
                "Uno",
                "Dos",
                "Dos",
                "Tres",
                "Tres",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    pares = {
        (
            relacion.source_column,
            relacion.target_column,
        )
        for relacion in resultados
    }

    assert (
        "codigo",
        "descripcion",
    ) in pares

    assert (
        "descripcion",
        "codigo",
    ) in pares


def test_relacion_funcional_confianza_alta_v6() -> None:
    """Una relación funcional perfecta obtiene confianza alta."""
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

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    relacion = next(
        resultado
        for resultado in resultados
        if (
            resultado.source_column
            == "codigo"
            and resultado.target_column
            == "descripcion"
        )
    )

    assert relacion.evaluable_rows == 4
    assert relacion.consistent_rows == 4
    assert relacion.consistency_ratio == 100.0
    assert (
        relacion.confidence
        is InferenceConfidence.HIGH
    )
    assert relacion.evidence


def test_relacion_funcional_bajo_umbral_no_se_devuelve_v6() -> None:
    """Una correspondencia débil no se devuelve como relación."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "A",
                "A",
                "B",
                "B",
                "B",
            ],
            "descripcion": [
                "X",
                "Y",
                "Z",
                "M",
                "N",
                "O",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    assert resultados == ()


def test_clave_fuerte_no_actua_como_origen_funcional_v6() -> None:
    """Una clave individual fuerte no genera relaciones triviales."""
    datos = pd.DataFrame(
        {
            "id": [
                1,
                2,
                3,
                4,
            ],
            "provincia": [
                "Madrid",
                "Madrid",
                "Toledo",
                "Toledo",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    assert all(
        relacion.source_column != "id"
        for relacion in resultados
    )


def test_origen_sin_repeticion_no_genera_relacion_v6() -> None:
    """Un origen sin valores repetidos no demuestra una relación."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "B",
                "C",
                "D",
            ],
            "grupo": [
                "X",
                "X",
                "Y",
                "Y",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    claves: dict[
        object,
        CandidateKeyAnalysis,
    ] = {}

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    assert all(
        relacion.source_column != "codigo"
        for relacion in resultados
    )


def test_presencia_coincidente_v6() -> None:
    """Detecta columnas cuya presencia y ausencia coinciden."""
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

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert len(resultados) == 1

    relacion = resultados[0]

    assert relacion.columns == (
        "telefono",
        "email",
    )
    assert (
        relacion.pattern
        is PresencePattern.COINCIDENCE
    )
    assert relacion.total_rows == 4
    assert relacion.both_present == 2
    assert (
        relacion.first_present_second_absent
        == 0
    )
    assert (
        relacion.first_absent_second_present
        == 0
    )
    assert relacion.both_absent == 2
    assert relacion.consistency_ratio == 100.0
    assert (
        relacion.confidence
        is InferenceConfidence.HIGH
    )


def test_presencia_complementaria_v6() -> None:
    """Detecta presencia complementaria entre dos columnas."""
    datos = pd.DataFrame(
        {
            "telefono": [
                "111",
                None,
                "222",
                None,
            ],
            "email": [
                None,
                "a@x.es",
                None,
                "b@x.es",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert len(resultados) == 1

    relacion = resultados[0]

    assert (
        relacion.pattern
        is PresencePattern.COMPLEMENTARY
    )
    assert relacion.both_present == 0
    assert (
        relacion.first_present_second_absent
        == 2
    )
    assert (
        relacion.first_absent_second_present
        == 2
    )
    assert relacion.both_absent == 0
    assert relacion.consistency_ratio == 100.0


def test_presencia_complementaria_exige_ambas_direcciones_v6() -> None:
    """
    Una columna siempre presente y otra siempre ausente
    no se interpreta como complementariedad.
    """
    datos = pd.DataFrame(
        {
            "informada": [
                "A",
                "B",
                "C",
                "D",
            ],
            "vacia": [
                None,
                None,
                None,
                None,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert resultados == ()


def test_presencia_completa_no_genera_patron_trivial_v6() -> None:
    """Dos columnas completas no generan coincidencia trivial."""
    datos = pd.DataFrame(
        {
            "nombre": [
                "Ana",
                "Luis",
                "Marta",
            ],
            "edad": [
                30,
                40,
                50,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert resultados == ()


def test_presencia_respeta_nulos_textuales_v6() -> None:
    """Los nulos textuales se consideran ausencia en las relaciones."""
    datos = pd.DataFrame(
        {
            "telefono": [
                "111",
                "NA",
                "222",
                "NA",
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

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert len(resultados) == 1

    relacion = resultados[0]

    assert (
        relacion.pattern
        is PresencePattern.COINCIDENCE
    )
    assert relacion.both_present == 2
    assert relacion.both_absent == 2
    assert relacion.consistency_ratio == 100.0


def test_dataset_vacio_no_genera_relaciones_presencia_v6() -> None:
    """Un dataset sin filas no genera patrones de presencia."""
    datos = pd.DataFrame(
        {
            "a": pd.Series(dtype="object"),
            "b": pd.Series(dtype="object"),
        }
    )

    analisis = analizar_columnas(datos)

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
    )

    assert resultados == ()


def test_analizar_relaciones_devuelve_contenedor_v6() -> None:
    """La API conjunta devuelve las tres familias de relaciones."""
    datos = pd.DataFrame(
        {
            "factura": [
                "F1",
                "F1",
                "F2",
                "F2",
            ],
            "linea": [
                1,
                2,
                1,
                2,
            ],
            "categoria": [
                "A",
                "A",
                "B",
                "B",
            ],
        }
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    resultado = analizar_relaciones(
        datos,
        analisis,
        claves,
    )

    assert isinstance(
        resultado,
        RelationshipAnalysis,
    )
    assert isinstance(
        resultado.composite_keys,
        tuple,
    )
    assert isinstance(
        resultado.functional_relationships,
        tuple,
    )
    assert isinstance(
        resultado.presence_relationships,
        tuple,
    )


def test_relaciones_no_modifican_dataframe_v6() -> None:
    """El análisis relacional no modifica el DataFrame original."""
    datos = pd.DataFrame(
        {
            "factura": [
                "F1",
                "F1",
                "F2",
                "F2",
            ],
            "linea": [
                1,
                2,
                1,
                2,
            ],
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

    original = datos.copy(
        deep=True
    )

    analisis, claves = _preparar_evidencias(
        datos
    )

    analizar_relaciones(
        datos,
        analisis,
        claves,
    )

    pd.testing.assert_frame_equal(
        datos,
        original,
    )


def test_umbral_relacion_funcional_configurable_v6() -> None:
    """El umbral funcional puede ajustarse explícitamente."""
    datos = pd.DataFrame(
        {
            "codigo": [
                "A",
                "A",
                "B",
                "B",
            ],
            "descripcion": [
                "X",
                "Y",
                "Z",
                "Z",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    claves: dict[
        object,
        CandidateKeyAnalysis,
    ] = {}

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
        umbral_consistencia=50.0,
    )

    relacion = next(
        resultado
        for resultado in resultados
        if (
            resultado.source_column
            == "codigo"
            and resultado.target_column
            == "descripcion"
        )
    )

    assert relacion.evaluable_rows == 4
    assert relacion.consistent_rows == 2
    assert relacion.consistency_ratio == 50.0
    assert (
        relacion.confidence
        is InferenceConfidence.MEDIUM
    )


def test_umbral_presencia_configurable_v6() -> None:
    """El umbral de presencia puede ajustarse explícitamente."""
    datos = pd.DataFrame(
        {
            "a": [
                "X",
                "X",
                None,
                None,
            ],
            "b": [
                "Y",
                None,
                "Y",
                None,
            ],
        }
    )

    analisis = analizar_columnas(datos)

    resultados = analizar_relaciones_presencia(
        datos,
        analisis,
        umbral_consistencia=50.0,
    )

    assert len(resultados) == 1

    relacion = resultados[0]

    assert (
        relacion.pattern
        is PresencePattern.COINCIDENCE
    )
    assert relacion.consistency_ratio == 50.0


def test_etiquetas_de_columna_no_string_v6() -> None:
    """El análisis admite etiquetas de columna que no sean str."""
    datos = pd.DataFrame(
        {
            10: [
                "A",
                "A",
                "B",
                "B",
            ],
            20: [
                "X",
                "X",
                "Y",
                "Y",
            ],
        }
    )

    analisis = analizar_columnas(datos)

    claves: dict[
        object,
        CandidateKeyAnalysis,
    ] = {}

    resultados = analizar_relaciones_funcionales(
        datos,
        analisis,
        claves,
    )

    pares = {
        (
            relacion.source_column,
            relacion.target_column,
        )
        for relacion in resultados
    }

    assert (10, 20) in pares
    assert (20, 10) in pares