# Plan de almacenamiento y retención meteorológica

Estado: implementación parcial local, documentada el 2026-08-11. Las retenciones
intradía, la ampliación del schema Parquet, la lectura Parquet de Tomap, la
barrera de frescura del runner y una prueba funcional del upsert monolítico
están implementados en el worktree. Ese upsert queda descartado para HA por
memoria. La compactación de los cuatro incrementales diarios todavía no está
implementada ni desplegada.

La especificación revisada y vinculante para sustituir el upsert monolítico por
un dataset transaccional fuente/año está en
`docs/weather-history-partitioned-implementation-spec-es.md`. En caso de
discrepancia, esa especificación posterior prevalece para la implementación.

## Problema

Los cuatro `*_incremental.csv` diarios cumplen hoy dos funciones incompatibles:

1. son el área de trabajo que el runner relee y reescribe en cada actualización;
2. son el único histórico desde el que se regenera `weather_daily.parquet`.

Después del backfill, mantener ambas funciones obliga al runner a procesar en
cada ejecución más de cinco millones de filas CSV, aunque MapLibre solo use 90
días y el Predictor consulte ventanas acotadas. Recortar los CSV sin separar
antes la segunda función destruiría el histórico usado por observaciones
antiguas, reconstrucción y entrenamiento.

## Cambios locales ya realizados

### AEMET intradía

`rainmapper_core/create_aemet.py` conserva siete fechas locales cerradas más la
fecha actual en `Aemet_hourly_incremental.csv`. El corte ocurre después de
fusionar y deduplicar el horario y antes de reconstruir los diarios. Solo se
reemplazan claves diarias realmente reconstruidas; una fecha o estación ausente
no produce una fila ni lluvia cero.

La prueba offline del camino real redujo 968.752 filas/50 fechas a 152.013
filas/8 fechas (`2026-08-04…2026-08-11`), sin duplicados y preservando 57.164
claves diarias anteriores al corte. Informe reproducible:
`docker-data/audits/mushroom-weather-backfill-20260811/reports/aemet_runtime_retention_verification.json`.

### Meteoclimatic intradía

Meteoclimatic no descarga histórico remoto. Cada ejecución recibe el snapshot
RSS actual y lo añadía indefinidamente a
`Meteoclimatic_observations_incremental.csv`; después reconstruía el diario con
el último snapshot para lluvia/temperatura/humedad y todos los snapshots del día
para el viento.

El worktree local conserva ahora siete fechas locales cerradas más la actual,
después del merge/deduplicación y antes del agregado diario. Sobre los CSV reales
de HA, leídos sin escribirlos, el corte reduce 223.428 filas/49 fechas a 36.330
filas/8 fechas y reconstruye 4.542 filas diarias idénticas. El upsert de la ruta
normal conserva las 152.862 claves diarias existentes. Informe:
`docker-data/audits/mushroom-weather-backfill-20260811/reports/meteoclimatic_retention_audit.json`.

### Escrituras atómicas

`rainmapper_core/atomic_io.py` escribe primero en un temporal del mismo
directorio, sincroniza y sustituye el destino al terminar. Se usa en los cinco
CSV AEMET, los incrementales diarios de Meteocat/Meteoclimatic/Wunderground, el
incremental de snapshots Meteoclimatic, catálogos de estaciones y snapshots
actuales. Una prueba de fallo confirma que una serialización interrumpida no
corrompe el destino ni deja temporales.

La batería dirigida conjunta pasa 102 pruebas y `git diff --check`. Nada de lo
anterior se ha ejecutado en HA, publicado o desplegado.

## Consumidores y ventanas reales

| Consumidor | Ruta actual comprobada | Necesidad |
|---|---|---|
| Actualizador de fuentes | fusiona cada descarga con su `*_incremental.csv` | día actual, correcciones recientes y margen para reintentos |
| Generador de `weather_daily.parquet` | relee los cuatro CSV completos y regenera el Parquet desde cero | actualmente convierte CSV; es el cuello de botella |
| Tomap/MapLibre | `tomap.py` lee 90 días filtrados del Parquet; `geojson.py` convierte Tomap a GeoJSON; MapLibre carga esos GeoJSON | periodos de 1, 7, 15, 21, 30, 60 y 90 días |
| Predictor actual/futuro | `load_daily_weather_parquet()` con filtros de estaciones y fechas | serie de 120 días y precarga corta |
| Predictor de una fecha antigua | el mismo Parquet con los 120 días anteriores a la fecha consultada | histórico completo consultable por fecha |
| Reconstrucción de artefactos | `build_observation_weather_features()` carga el Parquet completo cuando existe | todas las observaciones y sus ventanas previas |
| Entrenamiento/benchmark | consume los artefactos de features producidos por reconstrucción | todos los episodios elegibles, incluidos los antiguos |
| Snapshots/workers | prefieren transportar `weather_daily.parquet`; CSV solo como compatibilidad | entrada reproducible y verificada por manifiesto |
| Catálogo de estaciones | consume `weather_stations_catalog.parquet` | una fila por fuente/estación |

Por tanto, los consumidores ML y Tomap ya usan el Parquet en el worktree. No
hay que migrar los consumidores ML desde CSV: hay que conservar su contrato y
cambiar cómo se mantiene ese Parquet.

La ruta del runner en el worktree ya no llama a
`generate_weather_daily_parquet()` en cada actualización. Lee en chunks solo la
cola de 180 fechas de los CSV vivos y la aplica al Parquet canónico mediante
upsert. El generador completo queda fuera de esa ruta normal.

## Medición del candidato actual

Referencia: fecha local `2026-08-11`. La ventana de 180 fechas incluye desde
`2026-02-13`; la de 150, desde `2026-03-15`.

| Fuente | Filas completas | CSV completo | Filas en 180 días | CSV 180 días estimado |
|---|---:|---:|---:|---:|
| AEMET | 4.136.139 | 714 MiB | 144.352 | 24,9 MiB |
| Meteocat | 614.151 | 106 MiB | 31.977 | 5,5 MiB |
| Wunderground | 121.941 | 22,8 MiB | 16.928 | 3,2 MiB |
| Meteoclimatic | 152.836 | 29,5 MiB | 34.912 | 6,7 MiB |
| Total | 5.025.067 | 872,4 MiB | 228.169 | 40,3 MiB |

Los tamaños de la cola son estimaciones lineales; habrá que materializarlos en
el lab antes de promover. Esta medición corresponde al snapshot inicial. El
rebase posterior y coherente incorpora 301 filas y deja 5.025.368; esa es la
base del bootstrap particionado. El Parquet candidato combinado de las 5.025.067 filas
ocupa 85.905.884 bytes, aproximadamente 81,9 MiB.

## Arquitectura propuesta

### 1. Incrementales vivos acotados

Conservar en cada `*_incremental.csv` 180 fechas locales: 179 fechas cerradas
más la fecha actual. Es una frontera de calendario local, no las últimas 4.320
horas. La ventana supera:

- los 90 días máximos de MapLibre;
- los 120 días que usa actualmente el contrato meteorológico ML;
- el margen mínimo de 150 días acordado para Predictor y análisis;
- varios ciclos fallidos del runner y correcciones tardías normales.

El recorte no crea fechas, estaciones ni ceros. Se ejecuta después del upsert
por `(fuente, estación, fecha local)` y conserva valores previos útiles cuando
la lectura fresca trae `NaN`.

### 2. [REEMPLAZADA] Prueba de `weather_daily.parquet` monolítico

Esta opción se ensayó para conservar el archivo y contrato que ya consumen
Predictor, reconstrucción y workers:

```text
/share/rainmapper/Data/weather_daily.parquet
```

El archivo completo debe vivir en almacenamiento persistente y respaldado de
HA, no únicamente en `docker-data`. Deja de regenerarse desde los CSV y pasa a
actualizarse mediante upsert por `(source, station_code, local_date)`:

- las filas nuevas o corregidas de la cola viva se fusionan con el histórico;
- los valores nuevos no nulos ganan;
- un `NaN` fresco no borra un valor histórico útil;
- error remoto, estación inexistente y periodo vacío son ausencia de fila,
  nunca lluvia cero;
- la salida conserva orden `(source, station_code, local_date)`, row groups
pequeños y sustitución atómica.

El upsert monolítico está implementado en `rainmapper_core/weather_history.py`.
Procesa el Parquet existente por batches, nunca relee los CSV históricos para
reconstruirlo, y aplica la clave `(source, station_code, local_date)`. Un valor
nuevo no nulo gana; un valor nuevo ausente conserva el anterior. Las claves
nuevas se añaden ordenadas al final y una escritura fallida no sustituye el
destino. Si todavía no existe histórico, una instalación nueva se inicializa
atómicamente únicamente con las colas vivas disponibles.

Prueba con el candidato real: se conservaron exactamente las `5.025.368` filas
y todas las columnas históricas; las `228.470` claves de la cola de 180 fechas
coincidieron con el histórico, no se insertó ninguna inesperada y el resultado
reciente fue igual al merge no nulo esperado. El SHA del candidato base quedó
intacto. Informes en `reports/weather_history_upsert_validation.json` y
`reports/weather_history_live_queue_validation.json`.

La pasada de cola completa marcó 20,4 s de carga, 138,6 s de upsert y un pico
de 2,06 GiB bajo la carga combinada del validador. Aunque parte corresponda a la
comparación, el diseño se descarta para una RPi4 con 4 GiB totales: obliga a
reescribir cinco millones de filas y deja demasiado poco margen a HA/Docker.

La semántica no nula y sus tests son reutilizables. El escritor monolítico y su
conexión actual en `rainmapper.py` no son publicables.

### 3. Histórico particionado obligatorio

El histórico final usa un dataset particionado y versionado:

```text
weather-history/parts/source=<fuente>/year=<AAAA>/data-<sha>.parquet
```

Un manifiesto inmutable y `CURRENT.json` forman una tabla lógica transaccional:
una consulta de enero o febrero incluye automáticamente el final del año
anterior. Solo se escriben nuevas versiones de las particiones tocadas. El
contrato completo, pending, catálogo, lectores, snapshots y gates está en
`docs/weather-history-partitioned-implementation-spec-es.md`.

### 4. Tomap/MapLibre y catálogo

Tomap ha dejado de abrir los cuatro CSV y lee directamente
`weather_daily.parquet` con un filtro inclusivo de los últimos 90 días y solo las
columnas necesarias. El resto de la cadena no cambia: Tomap agregado → GeoJSON →
MapLibre. Así todos los consumidores principales parten de un único histórico
canónico y los CSV quedan como colas de ingestión/recuperación.

El runner `all` garantiza el orden: ejecuta y espera el subproceso `update`, y
solo después ejecuta el subproceso `maps`. `rainmapper.py` genera el Parquet al
final de `update`. Se han reforzado además estos contratos:

1. La generación Parquet ya no queda en un warning: ausencia, excepción o mtime
   anterior al inicio del update producen exit code 1. El orquestador corta
   `all` antes de `maps`; una ejecución manual de `maps` puede usar el último
   Parquet válido siempre que cumpla el schema Tomap.
2. El schema Parquet incorpora todas las columnas que Tomap agrega y que
   MapLibre muestra: `wind_avg_kmh`, `wind_gust_kmh`, `wind_min_kmh`, `wind_max_kmh`,
   `wind_direction_deg`, `wind_gust_direction_deg`,
   `wind_observation_count` y `wind_source_height_m`, además de metadatos de la
   lectura: `Data Lectura`, `Ultima Lectura`, `Hora Local`, `Comarca`,
   `Municipi`, `Provincia`, `Variable` y `Unitat`. La migración exige paridad
   completa, sin perder viento ni contexto de estación al cambiar de lector.

La prueba de migración construye en paralelo la antigua entrada CSV y la nueva
entrada Parquet y compara semánticamente los ocho CSV resultantes: siete
periodos Tomap y Last rains. Todos coinciden.

La ampliación del schema es compatible con los consumidores existentes: cargan
columnas conocidas por nombre o transportan el fichero como artefacto opaco. No
hay validación de una lista cerrada. No se cambian features ni modelos por añadir
las columnas; solo sería necesario reconstruir/reentrenar si posteriormente ML
empezase a consumir alguna de ellas. En particular, el loader ML actual deja la
dirección del viento en `None` aunque el registro interno admita ese campo.

`weather_stations_catalog.parquet` continúa siendo un artefacto ligero. El
Predictor ya consulta el histórico con filtros de:

- estaciones top-N dentro del radio permitido;
- `target_date - 119 días` hasta el final solicitado y su precarga;
- el intervalo solicitado dentro del Parquet.

El catálogo debe conservar `first_date`, `last_date` y estado de elegibilidad.
Una estación histórica o retirada puede seguir siendo necesaria para reproducir
una observación antigua, pero no puede desplazar a una estación activa dentro
del top-N de una predicción actual. Las 21 estaciones Wunderground retiradas por
calidad permanecen excluidas de la selección, aunque su procedencia se conserve
en manifiestos de auditoría.

La reconstrucción continúa leyendo el Parquet completo; el entrenamiento
continúa consumiendo los artefactos reconstruidos. No deben usar como histórico
los CSV vivos.

El fallback actual de `load_daily_weather_parquet()` a los CSV debe eliminarse
de las rutas de reconstrucción, entrenamiento y consulta histórica. Si falta o
no valida el dataset canónico, esas operaciones deben fallar de forma explícita;
usar silenciosamente 180 días produciría artefactos parciales que parecerían
completos. Un fallback a los CSV vivos solo puede admitirse para productos
operativos recientes y con estado degradado visible.

### 5. Copias de seguridad y espacio

El histórico canónico debe estar en `share` mientras no exista una copia externa
verificada con restauración probada. Unos 82 MiB de Parquet respaldado son un
coste razonable frente a incluir además unos 872 MiB de CSV redundante en cada
backup. `docker-data` sigue siendo laboratorio, no copia de seguridad.

No deben conservarse en HA las respuestas raw, candidatos ni copias intermedias
del backfill. Solo el histórico Parquet validado, los CSV vivos, el catálogo y
los artefactos operativos.

## Flujo futuro del runner

1. Descargar la lectura normal de la fuente.
2. Normalizarla sin convertir ausencia/error en cero.
3. Fusionarla y deduplicarla con el CSV vivo.
4. Retener 180 fechas locales y escribir el CSV vivo atómicamente.
5. Aplicar el pending fresco a las particiones fuente/año y publicar una nueva
   generación atómica. La ventana de 180 días queda como recuperación explícita
   si se pierde un pending.
6. Verificar claves, filas, rango y checksum antes de considerar actualizado el
   histórico; un fallo conserva el Parquet anterior y marca estado degradado.
7. Generar Tomap leyendo del manifiesto histórico solo los últimos 90 días.
8. Refrescar el catálogo si aparecen estaciones nuevas.

El Parquet histórico deja de regenerarse desde cero a partir de los CSV en cada
ejecución. El fallo de la actualización histórica debe marcar el runner como
degradado, conservar el archivo anterior y mantener la cola viva para reintento.

## Migración segura

No se puede recortar ningún CSV diario antes de completar esta secuencia:

1. Congelar en el lab los cuatro candidatos y sus hashes.
2. Validar el `weather_daily.parquet` monolítico candidato por fuente, claves,
   valores, rangos y layout.
3. Implementar y probar el upsert atómico Parquet + cola viva sin regeneración
   desde los CSV completos.
4. Cambiar Tomap para leer 90 días filtrados del Parquet y probar paridad de
   todos sus periodos frente a los CSV completos.
5. Probar consultas que crucen el 31 de diciembre para ventanas de 90, 120, 150
   y 180 días.
6. Probar paridad de features para observaciones antiguas, recientes, con gaps,
   estaciones retiradas y fallback hasta 15 km.
7. Confirmar que snapshots/workers siguen transportando el mismo Parquet y
   manifiesto sin fallback CSV accidental.
8. Reconstruir artefactos y repetir el benchmark ML exclusivamente en el lab.
9. Simular el runner completo en una copia local: actualización, archivado,
   compactación, MapLibre, catálogo y Parquet.
10. Medir tiempo, RSS máximo, bytes leídos/escritos y tamaño de backup del
    diseño particionado; rechazarlo si el archivador aislado alcanza 128 MiB
    adicionales o 256 MiB absolutos. El objetivo es 64/192 MiB.
11. Preparar backup y rollback reales siguiendo `docs/history-safety.md`.
12. Solo con autorización explícita, promover primero el histórico y después
    activar la retención diaria. Nunca al revés.

## Puertas de aceptación

- Cero pérdida de claves históricas respecto al candidato aprobado.
- Cero duplicados de `(source, station_code, local_date)`.
- Paridad de valores útiles; `NaN` fresco no borra histórico útil.
- Ningún error, vacío o estación inexistente convertido en lluvia cero.
- MapLibre conserva resultados para 1/7/15/21/30/60/90 días.
- Predictor conserva ventanas completas actuales, históricas y entre años.
- Reconstrucción y entrenamiento producen los mismos inputs antes y después del
  cambio de mantenimiento del Parquet.
- Un fallo durante escritura conserva el Parquet y CSV anteriores.
- Restauración del histórico desde backup verificada antes de borrar cualquier
  CSV completo.
- El runner deja de leer y reescribir los 872 MiB de CSV históricos en cada run.

## Decisiones pendientes

- Confirmar 180 días como retención viva definitiva después de medir el runner
  local; 150 es el mínimo funcional y 180 el margen recomendado.
- Medir el diseño particionado en la mayor partición real y durante un update
  completo; subdividir por bloques de estación solo si una partición anual no
  cumple el gate de memoria.
- Medir el impacto real del dataset Parquet en las copias HA y confirmar su
  restauración.
- Medir Tomap con el Parquet candidato completo en una simulación local del
  runner y validar ventanas que crucen el cambio de año.
