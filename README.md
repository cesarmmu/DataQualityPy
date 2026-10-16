# DataQualityPy

**DataQualityPy** es una aplicación desarrollada en Python para auditar, analizar y limpiar datasets de forma controlada.

El proyecto permite detectar problemas habituales de calidad de datos, revisar las incidencias encontradas, preparar un plan de limpieza configurable, simular su impacto, aplicarlo sobre una copia del dataset, volver a auditar el resultado y exportar tanto los datos limpios como la trazabilidad del proceso.

El dataset original nunca se sobrescribe.

## Flujo de trabajo

DataQualityPy V6 sigue el flujo:

**ANALIZAR → DETECTAR → REVISAR → LIMPIAR → VERIFICAR → EXPORTAR**

1. Se carga un dataset CSV o Excel.
2. DataQualityPy analiza su estructura y calidad.
3. Se presentan las incidencias detectadas.
4. El usuario decide qué operaciones de limpieza desea aplicar.
5. El plan se simula antes de modificar los datos.
6. La limpieza se ejecuta sobre una copia.
7. El resultado se vuelve a auditar.
8. Se comparan las incidencias antes y después de la limpieza.
9. Se exportan el dataset limpio y los informes de trazabilidad.

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
- incompatibilidades entre los datos y su tipo semántico;
- reglas de negocio configurables.

Los resultados se convierten en incidencias estructuradas que pueden consultarse desde la interfaz.

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

El usuario puede modificar esta interpretación mediante la configuración de la auditoría.

### Análisis avanzado V6

V6 amplía el perfilado con cardinalidad y unicidad, claves candidatas, niveles de confianza y evidencias, distribuciones y frecuencias, diagnósticos contextuales, posibles claves compuestas, relaciones funcionales y patrones de presencia.

### Diagnósticos y recomendaciones

V6 separa deliberadamente **DIAGNOSTICAR ≠ RECOMENDAR ≠ DECIDIR ≠ EJECUTAR**. Las recomendaciones se clasifican como **Limpiar**, **Revisar** o **Mantener** y nunca modifican el dataset por sí solas. Las operaciones que necesitan parámetros adicionales requieren información explícita del usuario.

### Limpieza configurable

DataQualityPy incorpora un motor de limpieza controlada y V6 amplía el flujo con recomendaciones, planes reutilizables y reproducibilidad.

Las operaciones se organizan en varias familias:

**Texto**

- eliminar espacios externos;
- normalizar espacios internos;
- convertir a minúsculas;
- convertir a mayúsculas;
- capitalizar;
- formato título;
- eliminar tildes;
- sustitución controlada de caracteres.

**Sustitución**

- reemplazo explícito de valores completos;
- normalización manual de categorías.

**Conversión**

- conversión a valores numéricos;
- fechas;
- fecha y hora;
- texto;
- booleanos.

**Valores nulos**

- mantener;
- eliminar registros;
- sustitución explícita;
- media;
- mediana;
- moda;
- conversión de determinados marcadores textuales a nulos reales.

**Outliers**

- detección mediante el criterio IQR;
- conservación por defecto;
- eliminación explícita de registros cuando el usuario lo autoriza.

**Duplicados**

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
- detectar errores antes de aplicar la limpieza;
- confirmar expresamente la ejecución.

El orden de ejecución del motor es:

**Texto → Sustitución → Conversión → Nulos → Outliers → Duplicados**

### Planes reutilizables

V6 permite guardar planes de limpieza en JSON y recuperarlos posteriormente. Cargar un plan no lo simula ni lo ejecuta automáticamente; ambas acciones siguen requiriendo decisiones explícitas del usuario.

## Verificación

Después de ejecutar el plan, DataQualityPy realiza automáticamente una nueva auditoría sobre el dataset limpio.

La aplicación compara ambos estados y clasifica las incidencias como:

- resueltas;
- pendientes;
- nuevas.

También muestra los cambios en filas y columnas y las operaciones realmente ejecutadas.

## Reproducibilidad

V6 incorpora manifiestos de ejecución que pueden registrar el dataset, su tamaño y huella SHA-256, la configuración efectiva de auditoría y el plan de limpieza cuando exista. Cargar un manifiesto no ejecuta automáticamente una auditoría ni una limpieza. La verificación del dataset y la recuperación de un plan son acciones explícitas e independientes.

## Exportación y trazabilidad

El dataset original no se modifica ni se sobrescribe.

DataQualityPy genera un nuevo archivo utilizando el sufijo:

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

Además del dataset limpio se generan dos informes:

```text
nombre_cleaning_report.html
nombre_cleaning_report.json
```

Estos informes permiten registrar:

- archivo y hoja de origen;
- dimensiones originales y finales;
- configuración utilizada;
- plan solicitado;
- operaciones realmente ejecutadas;
- registros afectados;
- incidencias antes y después;
- incidencias resueltas;
- incidencias pendientes;
- nuevas incidencias.

## Formatos soportados

Actualmente DataQualityPy trabaja con:

- CSV
- XLSX

La carga de CSV contempla distintos separadores y problemas habituales de codificación.

Los libros XLSX pueden contener varias hojas y el usuario selecciona cuál desea auditar.

## Interfaz

La interfaz principal está desarrollada con **Streamlit**.

Desde ella se puede:

- cargar el dataset;
- seleccionar una hoja de Excel;
- configurar la auditoría;
- ejecutar el análisis;
- consultar el resumen;
- revisar incidencias;
- estudiar perfiles, distribuciones y relaciones entre columnas;
- revisar diagnósticos y recomendaciones;
- consultar la cobertura de auditoría;
- generar informes;
- preparar y reutilizar planes de limpieza;
- simularlos y revisar su impacto;
- aplicarlo;
- verificar el resultado;
- descargar los archivos generados;
- crear, cargar y verificar manifiestos de reproducibilidad.

El motor de DataQualityPy permanece independiente de Streamlit.

## Línea de comandos

El proyecto conserva también una interfaz de línea de comandos para ejecutar auditorías sin utilizar Streamlit.

Ejemplo:

```powershell
python main.py data/input/ventas_prueba.csv
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
│   ├── incidents.py
│   ├── inference.py
│   ├── json_report.py
│   ├── loader.py
│   ├── profiler.py
│   ├── quality.py
│   ├── relationships.py
│   ├── report.py
│   ├── reproducibility.py
│   ├── semantic_quality.py
│   └── summary.py
│
├── tests/
│   └── test_*.py
│
└── ui/
    ├── audit_view.py
    ├── cleaning_view.py
    ├── home.py
    └── results.py
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

DataQualityPy V6 utiliza:

- Python 3.12
- Pandas
- NumPy
- openpyxl
- Streamlit
- pytest

Las versiones utilizadas durante el desarrollo están definidas en `requirements.txt`.

## Tests

El proyecto dispone de una batería automatizada de pruebas para el motor de DataQualityPy.

Estado de validación de V6:

```text
465 passed
```

La versión V6 fue validada funcionalmente con archivos CSV y libros Excel, así como con los flujos de recomendaciones, planes reutilizables, simulación y reproducibilidad.

La suite completa de V6 presenta un único `DeprecationWarning` conocido en una comparación temporal de un test, relacionado con una deprecación futura de NumPy/Pandas y sin impacto funcional en la aplicación.

Para ejecutar la batería completa:

```powershell
python -m pytest -q
```

## Principios de diseño

DataQualityPy se ha desarrollado siguiendo varios criterios:

- separación entre motor e interfaz;
- dataset original inmutable;
- limpieza únicamente bajo decisión explícita del usuario;
- separación entre diagnóstico, recomendación, decisión y ejecución;
- simulación previa a la limpieza;
- reutilización del resultado estructurado de auditoría;
- trazabilidad de las transformaciones;
- comportamiento conservador ante decisiones ambiguas;
- reproducibilidad verificable mediante SHA-256;
- funciones y módulos con responsabilidades diferenciadas;
- pruebas automatizadas del motor.

## Limitaciones actuales

DataQualityPy V6 está orientado principalmente a datasets tabulares CSV y XLSX.

En libros Excel complejos, la aplicación conserva las hojas no auditadas, pero no garantiza la conservación perfecta de elementos avanzados vinculados al rango modificado, como determinados gráficos, tablas de Excel, validaciones o estructuras complejas.

La interfaz de línea de comandos está orientada actualmente a la auditoría; el flujo completo de limpieza y exportación se realiza desde la interfaz Streamlit.

DataQualityPy no intenta decidir automáticamente cómo deben corregirse problemas ambiguos de calidad. La decisión final de limpieza corresponde al usuario.

Los análisis de relaciones entre columnas son heurísticos y deben interpretarse como apoyo al diagnóstico, no como reglas de negocio inferidas automáticamente.

La modularización adicional de algunas vistas de Streamlit queda como posible mejora estructural futura.

## Evolución

DataQualityPy se ha desarrollado de forma incremental:

- **V1** — núcleo inicial de auditoría.
- **V2** — ampliación del análisis, incidencias e informes.
- **V3** — consolidación del motor y del modelo estructurado de resultados.
- **V4** — interfaz gráfica mediante Streamlit.
- **V5** — auditoría configurable, limpieza controlada, reauditoría, exportación y trazabilidad.
- **V6** — perfilado avanzado, claves candidatas y relaciones, diagnósticos y recomendaciones, planes reutilizables, simulación enriquecida, UX integrada y reproducibilidad mediante manifiestos y SHA-256.

La documentación histórica de algunas fases del desarrollo se conserva en `docs/historico`.

## Estado del proyecto

**DataQualityPy V6 — versión estable candidata a release**

Validación automatizada:

```text
465 tests superados
```

Flujo funcional validado:

**ANALIZAR → DETECTAR → REVISAR → LIMPIAR → VERIFICAR → EXPORTAR**
