"""Tests del informe JSON de DataQualityPy V7."""

import json

import numpy as np
import pytest

from src.cleaning import CleaningResult
from src.json_report import generar_informe_json
from src.reaudit import ReauditComparison, ReauditResult
from src.reproducibility import DatasetReference, ExecutionManifest, RuntimeEnvironment


def _auditoria() -> dict:
    return {
        "dataset": {
            "archivo": "prueba.csv",
            "filas": 10,
            "columnas": 3,
            "memoria_bytes": 1024,
        },
        "resumen": {
            "total_incidencias": 1,
            "por_severidad": {
                "alta": 0,
                "media": 1,
                "baja": 0,
            },
        },
        "tipos_semanticos": {
            "precio": {
                "tipo": "numerico",
                "confianza": "alta",
                "fuente": "declared",
                "evidencias": [],
            }
        },
        "incidencias": [
            {
                "tipo": "incumplimiento_regla",
                "categoria": "validez",
                "severidad": "media",
                "columna": "precio",
                "regla": "min=0",
                "cantidad": 1,
                "porcentaje": 10.0,
                "mensaje": "La columna precio incumple la regla min=0.",
            }
        ],
        "perfil": {
            "nombres_columnas": ["precio"],
            "tipos_datos": {"precio": "object"},
            "valores_distintos": {"precio": 10},
        },
        "calidad": {
            "nulos": {},
            "reglas_negocio": {
                "precio": {
                    "min": {
                        "regla": "min",
                        "valores_incumplidos": 1,
                    }
                }
            },
        },
        "analisis_avanzado": {
            "columnas": {
                "precio": {
                    "patrones_estructurales": {
                        "analizados": 10,
                        "patron_dominante": "NN.NN",
                    }
                }
            },
            "claves_candidatas": [],
            "distribuciones": {},
            "diagnosticos": [
                {
                    "tipo_incidencia": "incumplimiento_regla",
                    "columna": "precio",
                    "explicacion": "Existe un valor bajo el mínimo.",
                    "explicacion_severidad": (
                        "La severidad procede de la incidencia."
                    ),
                    "evidencias": [],
                }
            ],
            "relaciones": {},
        },
    }


def _limpieza() -> CleaningResult:
    return CleaningResult(
        filas_antes=10,
        columnas_antes=3,
        filas_despues=10,
        columnas_despues=3,
        operaciones_solicitadas=0,
        operaciones_ejecutadas=0,
        ejecuciones=[],
    )


def _reauditoria(auditoria: dict) -> ReauditResult:
    posterior = dict(auditoria)
    posterior["incidencias"] = []

    return ReauditResult(
        audit_before=auditoria,
        audit_after=posterior,
        cleaning_result=_limpieza(),
        comparison=ReauditComparison(
            resolved=(auditoria["incidencias"][0],),
            persistent=(),
            new=(),
        ),
    )


def _manifiesto() -> ExecutionManifest:
    return ExecutionManifest(
        format_version="2.0",
        created_at="2026-10-18T12:00:00+02:00",
        dataset=DatasetReference(
            file_name="prueba.csv",
            file_extension=".csv",
            file_size=128,
            sha256="a" * 64,
        ),
        audit_configuration={
            "columnas_clave": [],
            "tipos_columnas": {},
            "reglas_columnas": {},
        },
        cleaning_plan=None,
        environment=RuntimeEnvironment(
            dataqualitypy="7.0.0",
            python="3.12.10",
            packages={
                "pandas": "2.3.3",
                "numpy": "2.5.3",
                "openpyxl": "3.1.5",
                "streamlit": "1.65.0",
            },
        ),
    )


def _leer(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def test_generar_informe_json_v7_conserva_auditoria_y_analisis_avanzado(
    tmp_path,
):
    auditoria = _auditoria()
    ruta = tmp_path / "informe.json"

    assert generar_informe_json(auditoria, ruta) == ruta
    contenido = _leer(ruta)

    assert list(contenido) == [
        "dataqualitypy",
        "dataset",
        "resumen",
        "tipos_semanticos",
        "incidencias",
        "perfil",
        "calidad",
        "analisis_avanzado",
    ]
    assert contenido["dataqualitypy"]["version_informe"] == "7.0"

    for clave in (
        "dataset",
        "resumen",
        "tipos_semanticos",
        "incidencias",
        "perfil",
        "calidad",
        "analisis_avanzado",
    ):
        assert contenido[clave] == auditoria[clave]


def test_json_v7_mantiene_compatibilidad_con_auditoria_sin_analisis_avanzado(
    tmp_path,
):
    auditoria = _auditoria()
    auditoria.pop("analisis_avanzado")
    ruta = tmp_path / "basico.json"

    generar_informe_json(auditoria, ruta)
    contenido = _leer(ruta)

    assert "analisis_avanzado" not in contenido
    assert contenido["incidencias"] == auditoria["incidencias"]


def test_json_v7_incluye_reauditoria_opcional(tmp_path):
    auditoria = _auditoria()
    reauditoria = _reauditoria(auditoria)
    ruta = tmp_path / "reauditoria.json"

    generar_informe_json(
        auditoria,
        ruta,
        resultado_reauditoria=reauditoria,
    )
    contenido = _leer(ruta)

    assert contenido["limpieza_reauditoria"] == reauditoria.a_dict()
    assert contenido["limpieza_reauditoria"]["comparacion"]["totales"] == {
        "resueltas": 1,
        "persistentes": 0,
        "nuevas": 0,
    }


def test_json_v7_incluye_reproducibilidad_opcional(tmp_path):
    auditoria = _auditoria()
    manifiesto = _manifiesto()
    ruta = tmp_path / "reproducible.json"

    generar_informe_json(
        auditoria,
        ruta,
        manifiesto_reproducibilidad=manifiesto,
    )
    contenido = _leer(ruta)

    assert contenido["reproducibilidad"] == manifiesto.a_dict()
    assert contenido["reproducibilidad"]["format_version"] == "2.0"
    assert (
        contenido["reproducibilidad"]["environment"]["dataqualitypy"]
        == "7.0.0"
    )


def test_json_v7_combina_reauditoria_y_reproducibilidad(tmp_path):
    auditoria = _auditoria()
    reauditoria = _reauditoria(auditoria)
    manifiesto = _manifiesto()
    ruta = tmp_path / "completo.json"

    generar_informe_json(
        auditoria,
        ruta,
        resultado_reauditoria=reauditoria,
        manifiesto_reproducibilidad=manifiesto,
    )
    contenido = _leer(ruta)

    assert "analisis_avanzado" in contenido
    assert "limpieza_reauditoria" in contenido
    assert "reproducibilidad" in contenido


def test_json_v7_no_incluye_filas_originales_en_ningun_bloque(tmp_path):
    auditoria = _auditoria()
    auditoria["datos"] = [{"precio": 10}]
    auditoria["dataset"]["rows"] = [{"precio": 10}]
    auditoria["analisis_avanzado"]["raw_data"] = [{"precio": 10}]
    ruta = tmp_path / "sin_filas.json"

    generar_informe_json(auditoria, ruta)
    contenido = _leer(ruta)
    texto = json.dumps(contenido, ensure_ascii=False)

    for clave in (
        "datos",
        "filas_originales",
        "registros",
        "raw_data",
        "rows",
    ):
        assert f'"{clave}"' not in texto


def test_json_v7_serializa_tipos_numpy(tmp_path):
    auditoria = _auditoria()

    auditoria["dataset"]["filas"] = np.int64(891)
    auditoria["resumen"]["total_incidencias"] = np.int32(7)
    auditoria["perfil"]["valores_distintos"]["precio"] = np.int64(5)
    auditoria["incidencias"][0]["porcentaje"] = np.float64(77.1044)
    auditoria["calidad"]["bandera_numpy"] = np.bool_(True)
    auditoria["analisis_avanzado"]["vector_numpy"] = np.array(
        [1, 2, 3],
        dtype=np.int64,
    )

    ruta = tmp_path / "tipos_numpy.json"

    generar_informe_json(auditoria, ruta)
    contenido = _leer(ruta)

    assert contenido["dataset"]["filas"] == 891
    assert contenido["resumen"]["total_incidencias"] == 7
    assert contenido["perfil"]["valores_distintos"]["precio"] == 5
    assert contenido["incidencias"][0]["porcentaje"] == pytest.approx(
        77.1044
    )
    assert contenido["calidad"]["bandera_numpy"] is True
    assert contenido["analisis_avanzado"]["vector_numpy"] == [1, 2, 3]


def test_json_v7_rechaza_reauditoria_de_tipo_incorrecto(tmp_path):
    with pytest.raises(TypeError, match="ReauditResult"):
        generar_informe_json(
            _auditoria(),
            tmp_path / "invalido.json",
            resultado_reauditoria={},  # type: ignore[arg-type]
        )


def test_json_v7_rechaza_manifiesto_de_tipo_incorrecto(tmp_path):
    with pytest.raises(TypeError, match="ExecutionManifest"):
        generar_informe_json(
            _auditoria(),
            tmp_path / "invalido.json",
            manifiesto_reproducibilidad={},  # type: ignore[arg-type]
        )