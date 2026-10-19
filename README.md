# DataQualityPy

**DataQualityPy** es una aplicación desarrollada en Python para **auditar, analizar, explicar, limpiar y volver a verificar la calidad de datasets tabulares** de forma controlada y reproducible.

Trabaja actualmente con archivos **CSV y XLSX** y ofrece una interfaz gráfica desarrollada con **Streamlit**, además de una interfaz de línea de comandos para auditorías.

El proyecto parte de una idea central: detectar una posible incidencia no significa decidir automáticamente cómo corregirla. El usuario conserva el control sobre las decisiones de limpieza y el dataset original nunca se sobrescribe.

## Flujo de trabajo

DataQualityPy V7 sigue el flujo:

**ANALIZAR → DETECTAR → EXPLICAR → REVISAR → SIMULAR → LIMPIAR → REAUDITAR → COMPARAR → EXPORTAR**

1. Se carga un dataset CSV o Excel.
2. DataQualityPy analiza su estructura, contenido y calidad.
3. Se realizan análisis avanzados de patrones, compatibilidad semántica y coherencia de tipos.
4. Las incidencias detectadas se presentan junto con evidencias y explicaciones.
5. El usuario revisa las recomendaciones y decide qué operaciones incorporar al plan de limpieza.
6. El plan se simula antes de modificar los datos.
7. La limpieza se ejecuta sobre una copia del dataset.
8. El resultado se vuelve a auditar.
9. Se comparan las incidencias antes y después de la limpieza.
10. Se pueden generar informes, exportar los datos limpios y conservar información de reproducibilidad.

## Principios de diseño

DataQualityPy separa deliberadamente conceptos que no deben confundirse:

**DIAGNOSTICAR ≠ RECOMENDAR ≠ DECIDIR ≠ EJECUTAR**

**REPRODUCIBLE ≠ AUTOMÁTICO**

**ANÓMALO ≠ INCORRECTO**

**SIMULAR ≠ REAUDITAR**

**LIMPIAR ≠ MEJORAR NECESARIAMENTE**

**COMPARAR ≠ PUNTUAR**

Otros criterios fundamentales son:

- separación entre motor e interfaz;
- dataset original inmutable;
- limpieza únicamente bajo decisión explícita del usuario;
- simulación previa a la ejecución;
- trazabilidad de las transformaciones;
- comportamiento conservador ante situaciones ambiguas;
- reutilización del resultado estructurado de auditoría;
- reproducibilidad verificable;
- módulos con responsabilidades diferenciadas;
- pruebas automatizadas del motor.

## Características principales

### Auditoría de calidad

DataQualityPy analiza, entre otros aspectos:

- valores nulos reales;
- valores nulos representados como texto;
- filas duplicadas;
- duplicados según columnas clave;
- columnas vacías o constantes;
- inconsistencias de texto;
- posibles valores atípicos mediante IQR;
- fechas y valores temporales;
- posibles identificadores;
- reglas de negocio configurables;
- cardinalidad y unicidad;
- claves candidatas;
- distribuciones y frecuencias;
- relaciones entre columnas.

Los resultados se transforman en incidencias estructuradas que pueden utilizarse desde la interfaz, los informes y el flujo de diagnóstico.

### Inferencia semántica

Además del tipo físico utilizado por Pandas, DataQualityPy puede inferir el significado probable de las columnas.

Entre los tipos contemplados se encuentran:

- numérico;
- fecha;
- fecha y hora;
- booleano/binario;
- categórico;
- identificador;
- texto libre.

La configuración de auditoría permite modificar esta interpretación cuando sea necesario.

### Análisis avanzado V7

V7 amplía el análisis con tres niveles complementarios.

#### C1 — Patrones estructurales

Permite observar patrones en valores textuales y detectar comportamientos estructurales atípicos.

Un patrón anómalo se interpreta como evidencia para revisión, no como prueba automática de error.

#### C2 — Compatibilidad semántica

Analiza si los valores observados son compatibles con familias como:

- numérico;
- fecha;
- booleano;
- correo electrónico;
- URL;
- IPv4;
- UUID.

La compatibilidad puede solaparse entre varias familias y no implica por sí misma que una interpretación sea la correcta.

#### C3 — Coherencia de tipos

Contrasta el tipo físico de la columna con el contenido observado.

Este análisis ayuda a localizar posibles discrepancias sin realizar conversiones automáticas.

### Explicabilidad y diagnósticos

Las incidencias pueden enriquecerse con información que permita comprender:

- qué se ha detectado;
- por qué se ha detectado;
- qué evidencias lo sustentan;
- por qué se ha asignado una determinada severidad;
- qué posibles acciones pueden revisarse.

La explicabilidad se mantiene separada de la decisión de limpieza.

### Recomendaciones

Las recomendaciones sirven como apoyo a la revisión y pueden clasificarse como:

- **Limpiar**;
- **Revisar**;
- **Mantener**.

Una recomendación nunca modifica los datos por sí sola.

Las operaciones que necesitan parámetros adicionales requieren información explícita del usuario.

## Limpieza configurable

Las operaciones de limpieza se organizan en varias familias.

### Texto

- eliminar espacios externos;
- normalizar espacios internos;
- convertir a minúsculas;
- convertir a mayúsculas;
- capitalizar;
- formato título;
- eliminar tildes;
- sustitución controlada de caracteres.

### Sustitución

- reemplazo explícito de valores;
- conversión controlada de determinados valores a nulo.

### Conversión

- numérico;
- fecha;
- fecha y hora;
- texto;
- booleano.

### Valores nulos

- eliminación de registros;
- sustitución explícita;
- media;
- mediana;
- moda.

### Outliers

- detección mediante el criterio IQR;
- conservación por defecto;
- eliminación explícita de registros cuando el usuario lo autoriza.

### Duplicados

- detección de filas completas duplicadas;
- eliminación conservando la primera aparición.

Las decisiones de limpieza nunca se aplican automáticamente.

## Plan de limpieza

Las operaciones seleccionadas se incorporan a un plan antes de modificar los datos.

DataQualityPy permite:

- revisar las operaciones solicitadas;
- eliminar decisiones del plan;
- estimar su impacto;
- simular conjuntamente las operaciones;
- detectar errores antes de ejecutar el plan;
- confirmar expresamente la limpieza.

El orden de ejecución del motor es:

**Texto → Sustitución → Conversión → Nulos → Outliers → Duplicados**

### Planes reutilizables

Los planes pueden almacenarse y recuperarse posteriormente.

Cargar o reconstruir un plan no implica ejecutarlo. La simulación y la ejecución siguen siendo acciones explícitas.

## Reauditoría

Después de ejecutar un plan de limpieza, DataQualityPy puede auditar de nuevo el dataset resultante.

La comparación entre la auditoría original y la reauditoría clasifica las incidencias como:

- resueltas;
- pendientes;
- nuevas.

También permite revisar cambios en las dimensiones del dataset y las operaciones realmente ejecutadas.

La comparación no genera una puntuación automática de mejora: eliminar una incidencia no significa necesariamente que el dataset sea mejor desde el punto de vista del negocio.

## Reproducibilidad

DataQualityPy V7 utiliza un manifiesto de ejecución para conservar información necesaria para reproducir y verificar el contexto de un análisis.

El manifiesto V7 puede registrar:

- referencia del dataset;
- nombre, extensión y tamaño;
- huella SHA-256;
- configuración efectiva de auditoría;
- plan de limpieza, cuando exista;
- versión de DataQualityPy;
- versión de Python;
- versiones de dependencias relevantes.

La versión actual del formato de manifiesto es **2.0**.

DataQualityPy mantiene compatibilidad de lectura con manifiestos anteriores de V6.

La verificación de un dataset compara su tamaño y SHA-256 con los valores registrados.

Cargar un manifiesto o reconstruir un plan de limpieza **no ejecuta automáticamente** una auditoría ni una limpieza.

## Informes y trazabilidad

V7 consolida la generación de informes a partir del resultado estructurado de auditoría.

Los informes pueden incorporar:

- información del dataset;
- resumen de auditoría;
- tipos semánticos;
- incidencias;
- perfil y calidad;
- análisis avanzado;
- explicabilidad;
- limpieza y reauditoría, cuando existan;
- reproducibilidad, cuando exista.

DataQualityPy dispone de salidas:

- JSON;
- HTML;
- consola.

Los informes presentan los resultados calculados por el motor y no recalculan la lógica de dominio.

## Exportación de datos limpios

El dataset original no se modifica ni se sobrescribe.

Los archivos limpios se generan utilizando el sufijo:

```text
_clean
```

Ejemplos:

```text
ventas.csv  → ventas_clean.csv
ventas.xlsx → ventas_clean.xlsx
```

Para archivos CSV se genera una salida compatible con UTF-8 BOM.

En archivos Excel con varias hojas, únicamente se sustituye el contenido tabular de la hoja auditada. Las demás hojas del libro se conservan.

## Formatos soportados

Actualmente DataQualityPy trabaja con:

- CSV;
- XLSX.

La carga de CSV contempla distintos separadores y problemas habituales de codificación.

Los libros XLSX pueden contener varias hojas y el usuario selecciona cuál desea auditar.

## Interfaz Streamlit

La interfaz gráfica está desarrollada con **Streamlit** y permanece separada del motor de DataQualityPy.

Desde ella se puede:

- cargar datasets;
- seleccionar hojas de Excel;
- configurar la auditoría;
- ejecutar el análisis;
- consultar el resumen;
- revisar incidencias;
- estudiar columnas y análisis avanzados;
- consultar diagnósticos y evidencias;
- revisar recomendaciones;
- consultar la cobertura de auditoría;
- generar informes;
- preparar planes de limpieza;
- simular su impacto;
- ejecutar la limpieza;
- reauditar el resultado;
- comparar incidencias;
- descargar archivos generados;
- crear, cargar y verificar información de reproducibilidad.

V7 modulariza la presentación de resultados en componentes especializados para resumen, incidencias, columnas, cobertura, informes e impresión.

## Dataset de demostración

El repositorio incluye varios archivos pequeños en `data/input/` para probar DataQualityPy sin necesidad de aportar datos externos.

El ejemplo principal es:

```text
data/input/calidad_prueba.csv
```

Este dataset contiene intencionadamente distintos problemas de calidad, como valores nulos, filas duplicadas, diferencias de capitalización e inconsistencias de espacios.

También se incluyen:

- `ventas_prueba.csv`, como dataset tabular sencillo;
- `ventas_prueba.xlsx`, para probar la carga de Excel;
- `excel_varias_hojas.xlsx`, para probar libros con varias hojas;
- `config_prueba.json`, como ejemplo de configuración personalizada.

## Línea de comandos

El proyecto conserva una interfaz de línea de comandos para ejecutar auditorías sin utilizar Streamlit.

Ejemplo principal:

```powershell
python main.py data/input/calidad_prueba.csv
```

Para generar informes adicionales:

```powershell
python main.py data/input/ventas_prueba.csv --json --html
```

También puede utilizarse una configuración personalizada:

```powershell
python main.py data/input/ventas_prueba.csv --config data/input/config_prueba.json
```

Para un archivo Excel puede indicarse la hoja:

```powershell
python main.py data/input/ventas_prueba.xlsx --hoja Ventas
```

## Estructura del proyecto

```text
DataQualityPy/
│
├── app.py
├── main.py
├── README.md
├── requirements.txt
│
├── data/
│   ├── input/
│   └── output/
│
├── docs/
│   └── historico/
│
├── src/
│   ├── audit.py
│   ├── business_rules.py
│   ├── candidate_keys.py
│   ├── cleaning.py
│   ├── cleaning_decisions.py
│   ├── cleaning_export.py
│   ├── cleaning_plan.py
│   ├── cleaning_plan_storage.py
│   ├── cleaning_recommendations.py
│   ├── cleaning_report.py
│   ├── cleaning_simulation.py
│   ├── column_analysis.py
│   ├── config.py
│   ├── diagnostics.py
│   ├── distributions.py
│   ├── html_report.py
│   ├── html_report_v7.py
│   ├── incidents.py
│   ├── inference.py
│   ├── json_report.py
│   ├── loader.py
│   ├── profiler.py
│   ├── quality.py
│   ├── reaudit.py
│   ├── relationships.py
│   ├── report.py
│   ├── report_v7.py
│   ├── reproducibility.py
│   ├── semantic_compatibility.py
│   ├── semantic_quality.py
│   ├── summary.py
│   └── type_coherence.py
│
├── tests/
│   └── test_*.py
│
└── ui/
    ├── audit_view.py
    ├── cleaning_view.py
    ├── home.py
    ├── results.py
    ├── results_columns.py
    ├── results_common.py
    ├── results_coverage.py
    ├── results_incidents.py
    ├── results_print.py
    ├── results_reports.py
    └── results_summary.py
```

## Instalación

Se recomienda utilizar un entorno virtual.

En Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución de la interfaz

Desde la raíz del proyecto:

```powershell
streamlit run app.py
```

Streamlit abrirá la aplicación en el navegador.

## Dependencias principales

DataQualityPy V7 ha sido validado con:

- Python 3.12.10;
- Pandas 2.3.3;
- NumPy 2.5.3;
- openpyxl 3.1.5;
- Streamlit 1.65.0;
- pytest 9.1.1.

Las versiones utilizadas están definidas en `requirements.txt`.

## Tests

El proyecto dispone de una batería automatizada de pruebas para el motor y sus principales contratos funcionales.

Estado final de validación de DataQualityPy V7:

```text
575 passed
0 failed
0 DeprecationWarning
```

La regresión completa final se ejecutó promoviendo los `DeprecationWarning` a errores:

```powershell
python -m pytest -W error::DeprecationWarning
```

Resultado:

```text
575 passed in 3.26s
```

La interfaz Streamlit se ha validado funcionalmente durante el desarrollo. La automatización específica de pruebas de UI queda como posible mejora futura.

## Limitaciones actuales

DataQualityPy V7 está orientado principalmente a datasets tabulares CSV y XLSX.

En libros Excel complejos, la aplicación conserva las hojas no auditadas, pero no garantiza la conservación perfecta de elementos avanzados vinculados al rango modificado, como determinados gráficos, tablas de Excel, validaciones o estructuras complejas.

La interfaz de línea de comandos está orientada principalmente a la auditoría; el flujo interactivo completo de revisión, limpieza y reauditoría se realiza desde Streamlit.

DataQualityPy no intenta decidir automáticamente cómo deben corregirse problemas ambiguos de calidad. La decisión final corresponde al usuario.

Los análisis de patrones, compatibilidad, coherencia y relaciones entre columnas son mecanismos de apoyo al diagnóstico y no deben interpretarse automáticamente como reglas de negocio.

## Evolución

DataQualityPy se ha desarrollado de forma incremental:

- **V1** — núcleo inicial de auditoría.
- **V2** — ampliación del análisis, incidencias e informes.
- **V3** — consolidación del motor y del modelo estructurado de resultados.
- **V4** — interfaz gráfica mediante Streamlit.
- **V5** — auditoría configurable, limpieza controlada, reauditoría, exportación y trazabilidad.
- **V6** — perfilado avanzado, claves candidatas y relaciones, diagnósticos y recomendaciones, planes reutilizables, simulación enriquecida, UX integrada y reproducibilidad mediante manifiestos y SHA-256.
- **V7** — análisis estructural y semántico avanzado, coherencia de tipos, explicabilidad ampliada, reauditoría formal, informes V7, reproducibilidad del entorno, compatibilidad de manifiestos y modularización de la interfaz de resultados.

## Estado del proyecto

**DataQualityPy V7.0.1 — versión estable**

Validación automatizada final:

```text
575 tests superados
0 DeprecationWarning
```

Flujo funcional:

**ANALIZAR → DETECTAR → EXPLICAR → REVISAR → SIMULAR → LIMPIAR → REAUDITAR → COMPARAR → EXPORTAR**


