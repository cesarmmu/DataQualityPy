"""Pruebas del motor de limpieza controlada de DataQualityPy."""

import pandas as pd
import pytest

from src.cleaning import CleaningError, ejecutar_plan_limpieza
from src.cleaning_plan import (
    CleaningOperation,
    CleaningPlan,
    CleaningPlanError,
)


def test_plan_ordena_familias_y_conserva_orden_interno():
    plan = CleaningPlan()

    duplicados = plan.crear_operacion(
        "duplicados",
        "eliminar_duplicados_completos",
    )
    texto_1 = plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "nombre",
    )
    nulos = plan.crear_operacion(
        "nulos",
        "moda",
        "categoria",
    )
    texto_2 = plan.crear_operacion(
        "texto",
        "mayusculas",
        "nombre",
    )
    sustitucion = plan.crear_operacion(
        "sustitucion",
        "reemplazar_valor",
        "categoria",
        {"origen": "A", "destino": "Activo"},
    )

    ordenadas = plan.operaciones_ordenadas()

    assert [op.id for op in ordenadas] == [
        texto_1.id,
        texto_2.id,
        sustitucion.id,
        nulos.id,
        duplicados.id,
    ]


def test_plan_permite_agregar_modificar_y_eliminar_operaciones():
    plan = CleaningPlan()

    operacion = plan.crear_operacion(
        "texto",
        "minusculas",
        "nombre",
    )

    modificada = plan.modificar_operacion(
        operacion.id,
        tipo="mayusculas",
    )

    assert len(plan) == 1
    assert modificada.id == operacion.id
    assert modificada.tipo == "mayusculas"

    eliminada = plan.eliminar_operacion(operacion.id)

    assert eliminada.id == operacion.id
    assert plan.esta_vacio()


def test_plan_rechaza_operacion_invalida():
    with pytest.raises(CleaningPlanError):
        CleaningOperation(
            familia="texto",
            tipo="operacion_inexistente",
            columna="nombre",
        )


def test_plan_rechaza_sustitucion_sin_origen():
    with pytest.raises(CleaningPlanError):
        CleaningOperation(
            familia="sustitucion",
            tipo="reemplazar_valor",
            columna="estado",
            parametros={"destino": "Activo"},
        )


def test_plan_serializa_en_orden_de_ejecucion():
    plan = CleaningPlan()

    plan.crear_operacion(
        "duplicados",
        "eliminar_duplicados_completos",
    )
    plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "nombre",
    )

    serializado = plan.a_dict()

    assert serializado["numero_operaciones"] == 2
    assert serializado["operaciones"][0]["familia"] == "texto"
    assert serializado["operaciones"][1]["familia"] == "duplicados"


def test_motor_no_modifica_dataframe_original():
    original = pd.DataFrame(
        {
            "nombre": ["  Ana  ", "Luis"],
        }
    )
    copia_esperada = original.copy(deep=True)

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "nombre",
    )

    limpio, _ = ejecutar_plan_limpieza(original, plan)

    pd.testing.assert_frame_equal(original, copia_esperada)
    assert limpio.loc[0, "nombre"] == "Ana"


def test_texto_normaliza_espacios_y_mayusculas():
    datos = pd.DataFrame(
        {
            "nombre": ["  Ana   María  ", "  luis  ", None],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "nombre",
    )
    plan.crear_operacion(
        "texto",
        "normalizar_espacios_internos",
        "nombre",
    )
    plan.crear_operacion(
        "texto",
        "mayusculas",
        "nombre",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio["nombre"].tolist()[:2] == ["ANA MARÍA", "LUIS"]
    assert pd.isna(limpio.loc[2, "nombre"])
    assert resultado.operaciones_ejecutadas == 3



def test_plan_admite_nuevas_operaciones_de_texto():
    plan = CleaningPlan()

    capitalizar = plan.crear_operacion(
        "texto",
        "capitalizar",
        "nombre",
    )
    titulo = plan.crear_operacion(
        "texto",
        "titulo",
        "direccion",
    )
    eliminar_tildes = plan.crear_operacion(
        "texto",
        "eliminar_tildes",
        "ciudad",
    )

    assert capitalizar.tipo == "capitalizar"
    assert titulo.tipo == "titulo"
    assert eliminar_tildes.tipo == "eliminar_tildes"
    assert len(plan) == 3


def test_texto_capitalizar_preserva_nulos():
    datos = pd.DataFrame(
        {
            "nombre": ["aNA MARÍA", "LUIS", None],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "capitalizar",
        "nombre",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[0, "nombre"] == "Ana maría"
    assert limpio.loc[1, "nombre"] == "Luis"
    assert pd.isna(limpio.loc[2, "nombre"])
    assert resultado.ejecuciones[0].registros_afectados == 2


def test_texto_formato_titulo_preserva_nulos():
    datos = pd.DataFrame(
        {
            "direccion": ["calle mayor 10", "AVENIDA DE AMÉRICA", None],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "titulo",
        "direccion",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[0, "direccion"] == "Calle Mayor 10"
    assert limpio.loc[1, "direccion"] == "Avenida De América"
    assert pd.isna(limpio.loc[2, "direccion"])
    assert resultado.ejecuciones[0].registros_afectados == 2


def test_texto_elimina_tildes_pero_conserva_enye_y_dieresis():
    datos = pd.DataFrame(
        {
            "texto": [
                "Árbol, canción y ÚLTIMO",
                "España, NIÑO y pingüino",
                None,
            ],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "eliminar_tildes",
        "texto",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[0, "texto"] == "Arbol, cancion y ULTIMO"
    assert limpio.loc[1, "texto"] == "España, NIÑO y pingüino"
    assert pd.isna(limpio.loc[2, "texto"])
    assert resultado.ejecuciones[0].registros_afectados == 1


def test_plan_valida_sustitucion_controlada_de_caracteres():
    plan = CleaningPlan()

    operacion = plan.crear_operacion(
        "texto",
        "sustituir_caracteres",
        "ciudad",
        {"origen": "_", "destino": " "},
    )

    assert operacion.tipo == "sustituir_caracteres"
    assert operacion.parametros == {"origen": "_", "destino": " "}


def test_plan_rechaza_parametros_invalidos_en_sustitucion_de_caracteres():
    plan = CleaningPlan()

    with pytest.raises(CleaningPlanError):
        plan.crear_operacion(
            "texto",
            "sustituir_caracteres",
            "ciudad",
            {"destino": " "},
        )

    with pytest.raises(CleaningPlanError):
        plan.crear_operacion(
            "texto",
            "sustituir_caracteres",
            "ciudad",
            {"origen": "", "destino": " "},
        )

    with pytest.raises(CleaningPlanError):
        plan.crear_operacion(
            "texto",
            "sustituir_caracteres",
            "ciudad",
            {"origen": "_"},
        )

    with pytest.raises(CleaningPlanError):
        plan.crear_operacion(
            "texto",
            "sustituir_caracteres",
            "ciudad",
            {"origen": "_", "destino": 1},
        )


def test_texto_sustituye_caracteres_dentro_del_valor_y_preserva_nulos():
    datos = pd.DataFrame(
        {
            "ciudad": [
                "MADRID_CENTRO",
                "MADRID_NORTE",
                "MADRID",
                None,
            ],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "sustituir_caracteres",
        "ciudad",
        {"origen": "_", "destino": " "},
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[0, "ciudad"] == "MADRID CENTRO"
    assert limpio.loc[1, "ciudad"] == "MADRID NORTE"
    assert limpio.loc[2, "ciudad"] == "MADRID"
    assert pd.isna(limpio.loc[3, "ciudad"])
    assert resultado.ejecuciones[0].registros_afectados == 2


def test_texto_sustitucion_de_caracteres_admite_destino_vacio():
    datos = pd.DataFrame(
        {
            "codigo": [
                "ABC-123",
                "DEF-456",
                None,
            ],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "sustituir_caracteres",
        "codigo",
        {"origen": "-", "destino": ""},
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[0, "codigo"] == "ABC123"
    assert limpio.loc[1, "codigo"] == "DEF456"
    assert pd.isna(limpio.loc[2, "codigo"])
    assert resultado.ejecuciones[0].registros_afectados == 2


def test_sustitucion_valor_y_sustitucion_por_nulo():
    datos = pd.DataFrame(
        {
            "estado": ["MAD", "ACT", "MAD", "OTRO"],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "sustitucion",
        "reemplazar_valor",
        "estado",
        {"origen": "MAD", "destino": "Madrid"},
    )
    plan.crear_operacion(
        "sustitucion",
        "reemplazar_por_nulo",
        "estado",
        {"origen": "OTRO"},
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio["estado"].tolist()[:3] == ["Madrid", "ACT", "Madrid"]
    assert pd.isna(limpio.loc[3, "estado"])
    assert resultado.ejecuciones[0].registros_afectados == 2
    assert resultado.ejecuciones[1].registros_afectados == 1


def test_conversion_numerica_correcta():
    datos = pd.DataFrame(
        {
            "cantidad": ["10", "20", "30"],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "conversion",
        "numerico",
        "cantidad",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert pd.api.types.is_numeric_dtype(limpio["cantidad"])
    assert limpio["cantidad"].tolist() == [10, 20, 30]
    assert resultado.operaciones_ejecutadas == 1


def test_conversion_incompatible_falla_sin_modificar_original():
    original = pd.DataFrame(
        {
            "cantidad": ["10", "ERROR", "30"],
        }
    )
    copia_esperada = original.copy(deep=True)

    plan = CleaningPlan()
    plan.crear_operacion(
        "conversion",
        "numerico",
        "cantidad",
    )

    with pytest.raises(CleaningError):
        ejecutar_plan_limpieza(original, plan)

    pd.testing.assert_frame_equal(original, copia_esperada)


def test_conversion_incompatible_a_nulo_requiere_autorizacion_explicita():
    datos = pd.DataFrame(
        {
            "cantidad": ["10", "ERROR", "30"],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "conversion",
        "numerico",
        "cantidad",
        {"incompatibles_a_nulo": True},
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[0, "cantidad"] == 10
    assert pd.isna(limpio.loc[1, "cantidad"])
    assert limpio.loc[2, "cantidad"] == 30
    assert resultado.ejecuciones[0].advertencias


def test_conversion_booleana_con_mapeo_explicito():
    datos = pd.DataFrame(
        {
            "activo": ["Sí", "No", "Sí", None],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "conversion",
        "booleano",
        "activo",
        {"mapeo": {"Sí": True, "No": False}},
    )

    limpio, _ = ejecutar_plan_limpieza(datos, plan)

    assert str(limpio["activo"].dtype) == "boolean"
    assert limpio.loc[0, "activo"] == True
    assert limpio.loc[1, "activo"] == False
    assert pd.isna(limpio.loc[3, "activo"])


def test_nulos_reemplazo_media_mediana_moda_y_valor():
    datos = pd.DataFrame(
        {
            "media": [10.0, 20.0, 15.0, None],
            "mediana": [10.0, 100.0, 55.0, None],
            "categoria": ["A", "A", "B", None],
            "manual": ["X", None, "Y", None],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion("nulos", "media", "media")
    plan.crear_operacion("nulos", "mediana", "mediana")
    plan.crear_operacion("nulos", "moda", "categoria")
    plan.crear_operacion(
        "nulos",
        "reemplazar_valor",
        "manual",
        {"valor": "SIN_DATO"},
    )

    limpio, _ = ejecutar_plan_limpieza(datos, plan)

    assert limpio.loc[2, "media"] == 15.0
    assert limpio.loc[2, "mediana"] == 55.0
    assert limpio.loc[3, "categoria"] == "A"
    assert limpio.loc[1, "manual"] == "SIN_DATO"
    assert limpio.loc[3, "manual"] == "SIN_DATO"


def test_nulos_eliminar_filas_registra_efecto_real():
    datos = pd.DataFrame(
        {
            "valor": [1, None, 3, None],
            "otra": ["a", "b", "c", "d"],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "nulos",
        "eliminar_filas",
        "valor",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)
    ejecucion = resultado.ejecuciones[0]

    assert len(limpio) == 2
    assert ejecucion.registros_afectados == 2
    assert ejecucion.filas_antes == 4
    assert ejecucion.filas_despues == 2


def test_outliers_elimina_solo_filas_fuera_de_iqr():
    datos = pd.DataFrame(
        {
            "valor": [10, 10, 11, 11, 12, 12, 100],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "outliers",
        "eliminar_filas",
        "valor",
        {"factor_iqr": 1.5},
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert 100 not in limpio["valor"].tolist()
    assert len(limpio) == 6
    assert resultado.ejecuciones[0].registros_afectados == 1


def test_duplicados_completos_conserva_primera_aparicion():
    datos = pd.DataFrame(
        {
            "id": [1, 1, 2, 2, 3],
            "nombre": ["A", "A", "B", "B", "C"],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "duplicados",
        "eliminar_duplicados_completos",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    esperado = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "nombre": ["A", "B", "C"],
        },
        index=[0, 2, 4],
    )

    pd.testing.assert_frame_equal(limpio, esperado)
    assert resultado.ejecuciones[0].registros_afectados == 2


def test_orden_real_texto_antes_de_sustitucion_y_duplicados():
    datos = pd.DataFrame(
        {
            "ciudad": [" MAD ", "MAD", "BCN"],
        }
    )

    plan = CleaningPlan()

    # Se añaden deliberadamente en orden contrario al de ejecución.
    plan.crear_operacion(
        "duplicados",
        "eliminar_duplicados_completos",
    )
    plan.crear_operacion(
        "sustitucion",
        "reemplazar_valor",
        "ciudad",
        {"origen": "MAD", "destino": "Madrid"},
    )
    plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "ciudad",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)

    assert limpio["ciudad"].tolist() == ["Madrid", "BCN"]
    assert [
        ejecucion.familia
        for ejecucion in resultado.ejecuciones
    ] == ["texto", "sustitucion", "duplicados"]


def test_error_en_operacion_posterior_no_modifica_original():
    original = pd.DataFrame(
        {
            "nombre": ["  Ana  ", "Luis"],
            "cantidad": ["10", "ERROR"],
        }
    )
    copia_esperada = original.copy(deep=True)

    plan = CleaningPlan()
    plan.crear_operacion(
        "texto",
        "eliminar_espacios_externos",
        "nombre",
    )
    plan.crear_operacion(
        "conversion",
        "numerico",
        "cantidad",
    )

    with pytest.raises(CleaningError):
        ejecutar_plan_limpieza(original, plan)

    pd.testing.assert_frame_equal(original, copia_esperada)


def test_resultado_resume_dimensiones_y_operaciones():
    datos = pd.DataFrame(
        {
            "id": [1, 1, 2],
            "nombre": ["A", "A", "B"],
        }
    )

    plan = CleaningPlan()
    plan.crear_operacion(
        "duplicados",
        "eliminar_duplicados_completos",
    )

    limpio, resultado = ejecutar_plan_limpieza(datos, plan)
    serializado = resultado.a_dict()

    assert resultado.filas_antes == 3
    assert resultado.columnas_antes == 2
    assert resultado.filas_despues == 2
    assert resultado.columnas_despues == 2
    assert resultado.operaciones_solicitadas == 1
    assert resultado.operaciones_ejecutadas == 1
    assert len(serializado["ejecuciones"]) == 1
    assert len(limpio) == 2
