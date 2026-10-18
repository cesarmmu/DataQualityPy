# DataQualityPy V7 — Ficha Técnica

## 1. Identificación del proyecto

**Nombre:** DataQualityPy  
**Versión:** 7.0.0  
**Tipo de proyecto:** Aplicación Python para calidad de datos  
**Ámbito:** Análisis de datos / Data Quality / Data Profiling  
**Interfaz principal:** Streamlit  
**Interfaz adicional:** Línea de comandos  
**Formatos soportados:** CSV y XLSX  
**Estado:** Versión estable

DataQualityPy es una aplicación desarrollada en Python para auditar, analizar, explicar, limpiar y volver a verificar la calidad de datasets tabulares mediante un proceso controlado y reproducible.

El proyecto se ha desarrollado de forma incremental, separando el motor de análisis de la interfaz de usuario y manteniendo como principio fundamental que las decisiones de limpieza permanezcan bajo control explícito del usuario.

---

## 2. Objetivo

El objetivo de DataQualityPy es facilitar la identificación y tratamiento de problemas habituales de calidad de datos antes de utilizar un dataset en procesos de análisis, visualización, reporting o transformación.

La aplicación permite recorrer un flujo completo:

**ANALIZAR → DETECTAR → EXPLICAR → REVISAR → SIMULAR → LIMPIAR → REAUDITAR → COMPARAR → EXPORTAR**

El sistema no se limita a localizar incidencias. También proporciona información para comprenderlas, permite preparar un plan de limpieza, simularlo antes de ejecutarlo y volver a auditar el dataset resultante.

---

## 3. Problema que resuelve

Los datasets utilizados en proyectos de análisis pueden contener problemas como:

- valores nulos;
- nulos representados mediante texto;
- duplicados;
- inconsistencias de formato;
- espacios no deseados;
- diferencias de capitalización;
- valores atípicos;
- columnas constantes o vacías;
- tipos físicos poco coherentes con su contenido;
- patrones estructurales anómalos;
- posibles identificadores;
- inconsistencias respecto a reglas de negocio.

Corregir automáticamente estos problemas puede introducir modificaciones incorrectas o eliminar información válida.

DataQualityPy adopta un enfoque conservador: **detectar una anomalía no significa asumir que el dato es incorrecto**.

La aplicación proporciona evidencias, diagnósticos y recomendaciones, pero mantiene separadas las etapas de diagnóstico, recomendación, decisión y ejecución.

---

## 4. Tecnologías utilizadas

### Lenguaje

- Python 3.12.10

### Tratamiento y análisis de datos

- Pandas 2.3.3
- NumPy 2.5.3

### Excel

- openpyxl 3.1.5

### Interfaz

- Streamlit 1.65.0

### Testing

- pytest 9.1.1

### Control de versiones

- Git
- GitHub

### Formatos utilizados

- CSV
- XLSX
- JSON
- HTML

Las versiones utilizadas durante la validación final están fijadas en `requirements.txt`.

---

## 5. Arquitectura

DataQualityPy separa el motor de análisis de la capa de presentación.

La arquitectura principal se organiza en tres bloques:

```text
DataQualityPy
│
├── src/       Motor y lógica de dominio
├── ui/        Interfaz Streamlit
└── tests/     Suite automatizada
```

### Motor

`src/` contiene los componentes responsables de:

- carga de datos;
- configuración;
- perfilado;
- inferencia;
- calidad;
- incidencias;
- análisis avanzado;
- diagnósticos;
- recomendaciones;
- limpieza;
- simulación;
- reauditoría;
- reproducibilidad;
- generación de informes.

### Interfaz

`ui/` utiliza los resultados estructurados generados por el motor.

V7 modulariza la presentación de resultados en componentes especializados para:

- resumen;
- incidencias;
- columnas;
- cobertura;
- informes;
- impresión.

La lógica de dominio permanece independiente de Streamlit.

### Tests

`tests/` contiene la batería automatizada que valida los principales contratos funcionales del proyecto.

---

## 6. Funcionalidades principales

### Carga de datos

DataQualityPy permite trabajar con:

- archivos CSV;
- archivos XLSX;
- libros Excel con varias hojas.

La carga de CSV contempla distintos separadores y problemas habituales de codificación.

En Excel, el usuario puede seleccionar la hoja que desea auditar.

### Auditoría

La auditoría permite detectar y analizar, entre otros elementos:

- nulos;
- duplicados;
- columnas vacías;
- columnas constantes;
- inconsistencias textuales;
- outliers mediante IQR;
- información temporal;
- posibles identificadores;
- cardinalidad;
- unicidad;
- claves candidatas;
- distribuciones;
- relaciones entre columnas;
- reglas de negocio configurables.

### Configuración

Determinados parámetros de auditoría pueden configurarse para adaptar el comportamiento del motor al dataset analizado.

---

## 7. Análisis avanzado C1 / C2 / C3

V7 incorpora tres niveles complementarios de análisis.

### C1 — Patrones estructurales

C1 estudia la estructura observable de determinados valores textuales.

Permite detectar patrones dominantes y valores que presentan estructuras diferentes.

El resultado se utiliza como evidencia de diagnóstico.

Un patrón diferente no se considera automáticamente incorrecto:

**ANÓMALO ≠ INCORRECTO**

### C2 — Compatibilidad semántica

C2 estudia si los valores observados son compatibles con determinadas familias semánticas.

Entre ellas:

- numérico;
- fecha;
- booleano;
- correo electrónico;
- URL;
- IPv4;
- UUID.

Un mismo valor puede ser compatible con más de una interpretación.

Por ello, compatibilidad no equivale automáticamente a significado correcto.

### C3 — Coherencia de tipos

C3 compara el tipo físico de una columna con el contenido observado.

Este análisis permite localizar posibles discrepancias entre almacenamiento e información contenida.

DataQualityPy utiliza esta información como apoyo al diagnóstico y no realiza conversiones automáticas basándose únicamente en este análisis.

---

## 8. Explicabilidad

Una de las ampliaciones de V7 es el enriquecimiento de los diagnósticos.

Las incidencias pueden incorporar:

- explicación;
- contexto;
- evidencias;
- origen de las evidencias;
- explicación de severidad;
- posibles acciones.

El objetivo es que el usuario pueda comprender por qué se ha detectado una incidencia antes de decidir cómo actuar.

El flujo conceptual es:

```text
INCIDENCIA
    ↓
EVIDENCIAS
    ↓
DIAGNÓSTICO
    ↓
RECOMENDACIÓN
    ↓
DECISIÓN
    ↓
OPERACIÓN
```

DataQualityPy mantiene deliberadamente la separación:

**DIAGNOSTICAR ≠ RECOMENDAR ≠ DECIDIR ≠ EJECUTAR**

---

## 9. Limpieza y reauditoría

### Plan de limpieza

Las decisiones seleccionadas por el usuario se transforman en operaciones incorporadas a un plan de limpieza.

Las principales familias de operaciones son:

- texto;
- sustitución;
- conversión;
- valores nulos;
- outliers;
- duplicados.

El orden de ejecución está controlado:

**Texto → Sustitución → Conversión → Nulos → Outliers → Duplicados**

### Simulación

Antes de ejecutar el plan puede simularse su efecto.

Esto permite revisar las operaciones previstas antes de modificar la copia de trabajo.

**SIMULAR ≠ EJECUTAR**

### Ejecución

El dataset original no se sobrescribe.

La limpieza genera un nuevo resultado sobre el que pueden realizarse las siguientes fases del proceso.

### Reauditoría

Después de la limpieza, DataQualityPy puede ejecutar una nueva auditoría.

El sistema compara el estado anterior y posterior y clasifica las incidencias como:

- resueltas;
- pendientes;
- nuevas.

El flujo es:

```text
DATASET ORIGINAL
       ↓
  AUDITORÍA A
       ↓
    LIMPIEZA
       ↓
 DATASET LIMPIO
       ↓
  AUDITORÍA B
       ↓
COMPARACIÓN A ↔ B
```

La comparación no genera automáticamente una puntuación de mejora.

**LIMPIAR ≠ MEJORAR NECESARIAMENTE**

**COMPARAR ≠ PUNTUAR**

---

## 10. Reproducibilidad

V7 amplía el sistema de reproducibilidad mediante manifiestos de ejecución.

El formato actual del manifiesto es **2.0**.

Puede registrar:

- referencia del dataset;
- nombre del archivo;
- extensión;
- tamaño;
- SHA-256;
- configuración efectiva de auditoría;
- plan de limpieza;
- versión de DataQualityPy;
- versión de Python;
- versiones de dependencias relevantes.

La huella SHA-256 permite comprobar si el dataset utilizado coincide con el registrado originalmente.

DataQualityPy mantiene compatibilidad de lectura con manifiestos anteriores de V6.

La carga de un manifiesto no inicia automáticamente una auditoría ni una limpieza.

La reconstrucción de un plan tampoco implica su ejecución.

Principio aplicado:

**REPRODUCIBLE ≠ AUTOMÁTICO**

---

## 11. Informes

DataQualityPy V7 puede generar informes en:

- JSON;
- HTML;
- consola.

Los informes utilizan los resultados estructurados generados por el motor.

Pueden incorporar:

- información del dataset;
- resumen;
- perfil;
- calidad;
- tipos semánticos;
- incidencias;
- análisis avanzado;
- explicabilidad;
- limpieza;
- reauditoría;
- reproducibilidad.

La capa de informes presenta la información y evita recalcular la lógica de dominio.

---

## 12. Testing y validación

DataQualityPy dispone de una suite automatizada desarrollada con pytest.

La regresión completa final de V7 se ejecutó con:

```powershell
python -m pytest -W error::DeprecationWarning
```

Resultado:

```text
574 passed in 7.78s
```

Resultado final de validación:

```text
Tests ejecutados          574
Tests superados           574
Tests fallidos              0
Errores                     0
DeprecationWarning           0
```

Los tests cubren, entre otras áreas:

- carga;
- configuración;
- perfilado;
- calidad;
- inferencia;
- análisis avanzado;
- incidencias;
- diagnósticos;
- recomendaciones;
- limpieza;
- simulación;
- reauditoría;
- reproducibilidad;
- informes JSON;
- informes HTML;
- informes de consola;
- compatibilidad con comportamientos anteriores.

La interfaz Streamlit se ha validado funcionalmente durante el desarrollo.

La automatización específica de pruebas de interfaz queda como posible mejora futura.

---

## 13. Principios técnicos

Los principales criterios utilizados durante el desarrollo son:

- separación de responsabilidades;
- motor independiente de la interfaz;
- dataset original inmutable;
- comportamiento conservador;
- decisiones explícitas;
- simulación previa a la ejecución;
- trazabilidad;
- reproducibilidad;
- compatibilidad hacia atrás cuando resulta necesaria;
- APIs públicas estables;
- informes desacoplados de la lógica de dominio;
- testing automatizado;
- evolución incremental.

---

## 14. Resultado final

DataQualityPy V7.0.0 constituye una versión estable del proyecto.

El sistema integra en un mismo flujo:

```text
Auditoría
   ↓
Análisis avanzado
   ↓
Explicabilidad
   ↓
Recomendaciones
   ↓
Decisión del usuario
   ↓
Simulación
   ↓
Limpieza
   ↓
Reauditoría
   ↓
Comparación
   ↓
Informes y reproducibilidad
```

El resultado es una herramienta orientada a estudiar y tratar problemas de calidad de datos manteniendo la trazabilidad de las decisiones y evitando correcciones automáticas ante situaciones ambiguas.

---

## 15. Competencias demostradas

El desarrollo de DataQualityPy permite demostrar competencias relacionadas con distintas áreas técnicas.

### Python

- diseño modular;
- funciones y clases;
- dataclasses;
- excepciones;
- tipado;
- separación de responsabilidades;
- APIs internas y públicas;
- persistencia;
- procesamiento de archivos.

### Análisis de datos

- Pandas;
- NumPy;
- perfilado de datasets;
- calidad de datos;
- análisis de nulos;
- duplicados;
- outliers;
- cardinalidad;
- distribuciones;
- inferencia y análisis semántico;
- relaciones entre variables.

### Ingeniería de datos y calidad

- validación de datasets;
- trazabilidad;
- reglas de negocio;
- planes de transformación;
- comparación antes/después;
- integridad mediante SHA-256;
- reproducibilidad.

### Testing

- pytest;
- tests unitarios y funcionales;
- regresión;
- compatibilidad;
- validación de contratos;
- control de deprecaciones.

### Desarrollo de aplicaciones

- Streamlit;
- separación entre frontend y motor;
- modularización de vistas;
- interacción con CSV y Excel;
- generación de JSON y HTML.

### Ingeniería de software

- Git;
- GitHub;
- versionado;
- evolución incremental;
- refactorización;
- compatibilidad hacia atrás;
- documentación técnica;
- mantenimiento de una suite de regresión.

---

## Estado

**DataQualityPy V7.0.0 — versión estable**

```text
574 tests superados
0 DeprecationWarning
```
