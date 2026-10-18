"""Extensiones V7 para la presentación de informes en consola."""

from __future__ import annotations

from typing import Any


def _a_dict(valor: Any) -> dict[str, Any]:
    if isinstance(valor, dict):
        return valor
    metodo = getattr(valor, "a_dict", None)
    if callable(metodo):
        resultado = metodo()
        if isinstance(resultado, dict):
            return resultado
    raise TypeError("El bloque V7 debe ser un diccionario o exponer a_dict().")


def mostrar_analisis_avanzado(analisis: dict[str, Any] | None) -> None:
    if not analisis:
        return
    print()
    print("16. ANÁLISIS AVANZADO Y EXPLICABILIDAD")
    print("-" * 60)
    diagnosticos = analisis.get("diagnosticos", [])
    if not diagnosticos:
        print("No hay diagnósticos explicables disponibles.")
        return
    for diagnostico in diagnosticos:
        columna = diagnostico.get("columna")
        tipo = diagnostico.get("tipo_incidencia", "incidencia")
        encabezado = tipo if columna is None else f"{tipo} · {columna}"
        print(f"- {encabezado}")
        explicacion = diagnostico.get("explicacion")
        if explicacion:
            print(f"  ¿Por qué se ha detectado? {explicacion}")
        severidad = diagnostico.get("explicacion_severidad")
        if severidad:
            print(f"  ¿Por qué tiene esta severidad? {severidad}")
        evidencias = diagnostico.get("evidencias", [])
        if evidencias:
            print("  Evidencias del diagnóstico:")
            for evidencia in evidencias:
                etiqueta = evidencia.get("etiqueta", evidencia.get("clave", "Evidencia"))
                print(f"    - {etiqueta}: {evidencia.get('valor')}")


def mostrar_reauditoria(resultado_reauditoria: Any | None) -> None:
    if resultado_reauditoria is None:
        return
    datos = _a_dict(resultado_reauditoria)
    comparacion = datos.get("comparacion", {})
    totales = comparacion.get("totales", {})
    print()
    print("17. LIMPIEZA Y REAUDITORÍA")
    print("-" * 60)
    print(f"Incidencias resueltas: {totales.get('resueltas', len(comparacion.get('resueltas', [])))}")
    print(f"Incidencias persistentes: {totales.get('persistentes', len(comparacion.get('persistentes', [])))}")
    print(f"Incidencias nuevas: {totales.get('nuevas', len(comparacion.get('nuevas', [])))}")
    if comparacion.get("persistentes"):
        print("Persistentes (antes → después):")
        for item in comparacion["persistentes"]:
            antes = item.get("antes", {})
            despues = item.get("despues", {})
            print(f"  - {antes.get('mensaje', antes.get('tipo', 'Incidencia'))}")
            print(f"    → {despues.get('mensaje', despues.get('tipo', 'Incidencia'))}")


def mostrar_reproducibilidad(
    manifiesto: Any | None,
    verificacion: Any | None = None,
) -> None:
    if manifiesto is None and verificacion is None:
        return
    print()
    print("18. REPRODUCIBILIDAD")
    print("-" * 60)
    if manifiesto is not None:
        datos = _a_dict(manifiesto)
        print(f"Formato del manifiesto: {datos.get('format_version', 'no disponible')}")
        print(f"Creado: {datos.get('created_at', 'no disponible')}")
        dataset = datos.get("dataset", {})
        if dataset:
            print(f"Dataset: {dataset.get('file_name', 'no disponible')}")
            print(f"SHA-256: {dataset.get('sha256', 'no disponible')}")
        entorno = datos.get("environment")
        if entorno:
            print(f"DataQualityPy: {entorno.get('dataqualitypy', 'no disponible')}")
            print(f"Python: {entorno.get('python', 'no disponible')}")
    if verificacion is not None:
        datos_verificacion = _a_dict(verificacion)
        estado = datos_verificacion.get("status", datos_verificacion.get("estado"))
        if estado is not None:
            print(f"Verificación: {estado}")
        componentes = datos_verificacion.get("components", datos_verificacion.get("componentes", {}))
        if isinstance(componentes, dict):
            for nombre, detalle in componentes.items():
                if isinstance(detalle, dict):
                    valor = detalle.get("status", detalle.get("estado", "no_disponible"))
                else:
                    valor = detalle
                print(f"  - {nombre}: {valor}")
