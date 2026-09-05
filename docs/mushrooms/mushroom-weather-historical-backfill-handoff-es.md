# Handoff: recuperación de meteorología histórica para el laboratorio micológico

> **Estado: OBSOLETO como plan de ejecución; conservado como auditoría.** El
> backfill y el cutover fuente/año ya se completaron y validaron en HA. No
> repetir descargas ni promover estos candidatos: producción ha seguido
> avanzando. El estado operativo y los próximos pasos están en
> `docs/active-context.md`; la evidencia detallada está en `PROGRESS.md` dentro
> del laboratorio.

Fecha de auditoría: 2026-08-11.

Este documento deja preparado el trabajo para otra sesión de Codex. El alcance
de esta sesión ha sido exclusivamente de lectura y planificación: **no se ha
descargado meteorología, no se ha modificado Home Assistant y no se ha mezclado
nada con el Parquet operativo**. Los únicos artefactos nuevos de análisis están
en `docker-data`, que es el espacio local de juego y está ignorado por Git.

## Conclusión que debe conservar la próxima sesión

El benchmark parte de 275 episodios micológicos elegibles. En la copia auditada,
127 no tienen meteorología local utilizable para el contrato actual. Esto no
significa que las fuentes oficiales carezcan de esos datos: significa que no
están materializados con cobertura suficiente en el
`weather_daily.parquet` local.

Los 127 episodios afectados pertenecen a 2012–2022. Antes de rediseñar o
descartar el modelo hay que intentar recuperar su meteorología histórica. El
fallback a otra estación ya existente solo recupera episodios cuando el Parquet
contiene una alternativa válida para el corte requerido; no puede recuperar
años que el Parquet no contiene.

## Snapshot y resultados reproducibles

El inventario se calculó sobre estos inputs:

| Input | SHA-256 |
|---|---|
| `docker-data/mushroom-data/mushroom_observation_features_v0.json` | `e5f24d8c5acfe5da013e39b7e7eae4a3c590d310537eedc14a8f661fadab05f3` |
| `docker-data/mushroom-data/mushroom_known_sites.json` | `ef9363a1ae3c37cdb8ed72109e925ddd7f2e508cb06e4ac35563b9ac530d2ac7` |
| `docker-data/Data/weather_stations_catalog.parquet` | `caa9d5b8c0d6c8ac8d198c9589c98795526be9a96741e7af62d510a3d7022b62` |

Resultados:

- 275 episodios elegibles;
- 127 episodios sin meteorología utilizable;
- 18 áreas afectadas;
- 40 ventanas consolidadas por área para auditar después la selección;
- 7 ventanas globales mínimas para cuantificar la necesidad estricta;
- 6.617 días-área que consultar, sin deduplicar días entre áreas;
- 2.536 días naturales en esas ventanas mínimas;
- tres rangos continuos de backfill, uno por fuente, que comienzan el
  2012-06-19 y terminan justo antes del histórico local ya materializado;
- 408 parejas área/estación candidatas a un máximo de 15 km en el catálogo
  actual.

Distribución de los 127 episodios:

| Año | Episodios | Año | Episodios |
|---:|---:|---:|---:|
| 2012 | 10 | 2019 | 14 |
| 2013 | 5 | 2020 | 23 |
| 2016 | 3 | 2021 | 30 |
| 2017 | 2 | 2022 | 30 |
| 2018 | 10 |  |  |

| Área | Episodios | Área | Episodios |
|---|---:|---|---:|
| Bagà | 4 | Campelles | 2 |
| Coll de la Batalla | 11 | Ermita Ascensió | 15 |
| Guils | 7 | La Gavarra | 6 |
| Llambilles | 2 | Molló | 2 |
| Olvan | 21 | Planoles | 1 |
| Prats de Lluçanès | 2 | Puertomingalvo | 2 |
| Rectoria de la Selva | 1 | Riu de Cerdanya | 13 |
| Rubio | 1 | Salteguet | 8 |
| Sant Joan | 18 | Selva del Camp | 11 |

## Contrato de ventana histórica

Para cada episodio observado en `T`, el inventario pide datos crudos desde
`T-150 días` hasta `T`, ambos inclusive: 151 días naturales. Los 150 días son
un margen de adquisición, no una nueva feature ni permiso para mirar el futuro.
Cada contrato de ML debe seguir aplicando después su propio corte libre de
fugas, por ejemplo el gap fijo o la fecha de emisión.

Este margen cubre:

- la búsqueda actual de eventos hasta 90 días atrás;
- el gap fijo de siete días;
- posibles comparaciones posteriores con 120–150 días de contexto;
- huecos pequeños sin obligar a repetir inmediatamente la descarga.

Las ventanas individuales que se solapan dentro de un área se han fusionado.
Por eso algunos tramos consolidados superan 151 días: representan varias
observaciones próximas, no una ventana mayor asignada a una sola observación.
Esos 40 tramos por área sirven para auditar cobertura y selección. Al fusionar
sus solapamientos quedan 7 ventanas globales mínimas que suman 2.536 días. Sin
embargo, **el backfill no debe limitarse a esos huecos ni volver a descargar lo
que ya existe**. El contrato acordado es complementar cada fuente hacia atrás:

| Fuente | Backfill que se intentará | Histórico local que se conserva |
|---|---|---|
| Meteocat | 2012-06-19 — 2016-12-19 | 2016-12-20 — 2026-08-10 |
| Wunderground | 2012-06-19 — 2023-07-31 | 2023-08-01 — 2026-08-11 |
| AEMET | 2012-06-19 — 2026-05-24 | 2026-05-25 — 2026-08-11 |
| Meteoclimatic | excluido: no hay API histórica validada | 2023-09-28 — 2026-08-11 |

El inicio común, 2012-06-19, son 150 días antes de la primera observación
actual, 2012-11-16. Cada fin es el día anterior al comienzo del histórico local
de esa fuente. La descarga abarca todas sus estaciones conocidas. Lo que la API
conserve se incorporará; lo que ya no exista quedará registrado como ausencia.

El resultado provisional será la unión del histórico actual y el recuperado,
deduplicada por `(source, station_id, local_date)`. No se elimina, sustituye ni
olvida ninguna fila existente. Los descargadores pueden y deben fragmentar cada
rango internamente según el límite del servicio.

## Inventarios locales preparados

Directorio único de trabajo:

`docker-data/audits/mushroom-weather-backfill-20260811/`

| Fichero | Uso |
|---|---|
| `summary.json` | Contrato, hashes y recuentos globales. |
| `missing_weather_episodes_150d.csv` | Los 127 episodios; incluye especie, área, fecha, `T-150…T`, clase, microáreas, coordenadas y motivo del gap. |
| `historical_backfill_missing_ranges_all_stations.csv` | Contrato canónico por fuente: inicio común 2012-06-19, frontera con el histórico local existente, todas las estaciones y regla de unión sin pérdida. |
| `global_download_windows_150d_all_stations.csv` | Las 7 ventanas mínimas de necesidad estricta. Se conservan para auditoría y para estimar recuperación, no como alcance final de adquisición. |
| `merged_download_windows_150d_by_area.csv` | Los 40 tramos consolidados por área para auditar después cobertura y selección. Incluye especies, fechas observadas y cantidad de candidatas actuales por fuente. |
| `candidate_stations_within_15km.csv` | Estaciones candidatas actuales para el selector posterior, con distancia, cota y fuente. No limita qué estaciones se descargan. |

El catálogo actual encuentra al menos una candidata a 15 km para todas las
áreas. **Ese radio no limita la descarga**: se adquiere el histórico de todas
las estaciones conocidas que el servicio permita consultar. Los 15 km son solo
el límite máximo del selector posterior. Dentro de ese radio las candidatas se
procesan por distancia ascendente y se prefiere la estación más cercana que
tenga histórico utilizable para la ventana y las variables requeridas. El
número de filas candidatas para esa auditoría posterior es: Meteocat 57, AEMET 27,
Wunderground 156 y Meteoclimatic 168. Son relaciones área/estación, no estaciones
únicas: corresponden respectivamente a 35, 17, 72 y 94 identificadores únicos.

Dos columnas del inventario de candidatas permanecen deliberadamente a
`False`: `historical_existence_verified` y
`historical_variable_coverage_verified`. La cercanía en el catálogo de 2026 no
demuestra que la estación existiera en 2012–2022 ni que publicara lluvia,
temperatura y humedad. La descarga debe verificar ambas cosas.
El CSV ya está ordenado por `area_id` y `distance_km` ascendente, por lo que su
orden dentro de cada área es también el orden de intento previsto.

## Herramientas históricas ya existentes

La revisión de código confirma que **sí existen backfills reutilizables**. No
hay que diseñar tres descargadores desde cero:

| Fuente | Backfill existente | Qué se puede reutilizar | Límite relevante |
|---|---|---|---|
| Meteocat | Modo administrativo mensual de `run.sh`/web UI | Ventanas `days_init/days_end`, consultas Socrata, normalización y upsert incremental | Está acoplado al runner; para el laboratorio hay que aislarlo y dirigir su salida a `docker-data`. |
| Wunderground | Mismo modo mensual + cliente `daily_api.py` | Fechas locales exactas, histórico diario por PWS, filtro de estaciones, normalización y upsert | Hay que iterar toda la lista PWS conocida y aceptar que algunas estaciones no existían. |
| AEMET | `scripts/aemet-backfill-30-days.py` | Climatología diaria de todas las estaciones, chunks de 15 días, inventario, merge y deduplicación | El actualizador horario normal no sirve para 2012–2026; se usa el helper ampliándolo/orquestándolo. |
| Meteoclimatic | No hay backfill remoto histórico | `meteoclimatic_history.py` acumula observaciones recibidas y deriva el diario | El feed actual no permite reconstruir los años anteriores. |

El modo mensual crea antes una copia de los `*_incremental.csv` en
`Data/backups/backfill_incrementals_<timestamp>` y ejecuta cada ventana con
pausa visible. `rainmapper_core/incremental_upsert.py` ya fusiona por estación y
día: los valores nuevos no nulos prevalecen y un `NaN` nuevo conserva el valor
histórico útil. AEMET dispone además de `merge_existing_incremental` y
`merge_daily_incremental`, ambos pensados para conservar backfills manuales.

No se encontraron directorios de salida de backfill separados ni en la copia
local `docker-data/Data/backups` ni en el `Data/backups` montado de HA durante
esta auditoría de solo lectura. Eso no prueba que nunca se ejecutaran: los datos
pueden estar ya integrados en los incrementales. Los rangos presentes en el
Parquet son la referencia que se debe complementar.

### AEMET: helper histórico reutilizable

Existe `scripts/aemet-backfill-30-days.py`. El nombre es histórico, pero el
argumento `--days` admite cualquier número positivo y `--end-date` fija el día
final. El helper:

- consulta climatología diaria de AEMET;
- fragmenta automáticamente cada rango en tramos inclusivos de 15 días mediante
  `split_date_ranges`, respetando el límite del endpoint;
- obtiene o reutiliza el inventario de estaciones;
- normaliza y deduplica `Aemet_incremental.csv`;
- puede preservar un catálogo con `--station-catalog`, omitir otra consulta de
  inventario con `--skip-inventory` y fusionar un incremental existente con
  `--existing-incremental`;
- está cubierto por `tests/test_aemet_backfill_script.py`.

Para este laboratorio hay que pasar siempre un `--output-dir` dentro del
directorio de auditoría en `docker-data`; su default bajo `tmp/` no debe usarse
para una reconstrucción larga. Que el endpoint devuelva todas las estaciones es
precisamente el comportamiento deseado. Falta un wrapper dirigido por el rango
AEMET 2012-06-19 — 2026-05-24, que internamente reutilice los chunks inclusivos
de 15 días, con caché reanudable y salida provisional por fuente; no debe filtrar
la adquisición por distancia o por las candidatas actuales. Al terminar se une
con el histórico AEMET local conservándolo íntegramente.

`rainmapper_core/create_aemet.py` no sustituye ese helper: es el actualizador
horario/incremental operativo. Preserva backfills diarios ya incorporados, pero
no es la herramienta adecuada para reconstruir 2012–2022.

### Wunderground: API diaria y backfill mensual

`rainmapper_core/sources/wunderground/daily_api.py` ya implementa la llamada a
`https://api.weather.com/v2/pws/history/daily` con `station_id`, fecha inicial y
fecha final, además de normalización imperial a métrico.

El core acepta `--wunderground_local_start_date`,
`--wunderground_local_end_date` y `--backfill_station_filter`. La aplicación
orquesta ventanas mensuales en:

- `rainmapper-app/run.sh`: `month_backfill_windows`, backup de incrementales y
  ejecución de las ventanas;
- `rainmapper-app/app/web_server.py`: `monthly_backfill_windows` y supervisión
  del modo administrativo;
- `rainmapper-app/config.yaml`: `backfill_months_enabled`, `months_init`,
  `months_end`, `months_interval`, `backfill_pause_seconds` y
  `backfill_station_filter`;
- `rainmapper-app/DOCS.md`: configuración y formato
  `wunderground::ID1,ID2`;
- `tests/test_wunderground_daily_api.py` y `tests/test_web_server_auth.py`.

Pese a su nombre histórico, `backfill_station_filter` no está condicionado por
el modo mensual: limita cualquier update Wunderground mientras tenga valor. Se
debe restaurar a vacio al terminar. Ninguna otra fuente meteorológica consume
actualmente el filtro.

Este mecanismo es relativo a meses y está integrado en un update completo. No
debe ejecutarse en HA para el laboratorio. Conviene reutilizar su cliente y su
normalización desde un wrapper local dirigido por el manifiesto global, iterando
todas las PWS de la lista de estaciones conocida, no solo las cercanas a las
áreas actuales. Una PWS solo es recuperable si ya existía y la cuenta/API
conserva ese período.

### Meteocat: consultas por fecha, sin helper histórico aislado

No existe un script dedicado equivalente al de AEMET. El core ya consulta los
datasets públicos Socrata con rangos derivados de `days_init/days_end`:

- lecturas XEMA: `nzvn-apee`;
- agregados diarios XEMA: `7bvh-jvq2`;
- funciones de descarga y normalización en
  `rainmapper_core/rainmapper.py`, incluyendo `process_meteocat`,
  `get_results_rain_xema` y `get_results_conditions_xema`.

Por tanto hay piezas reutilizables, pero el runner normal tiene efectos
laterales sobre incrementales. La consulta de la red completa es adecuada para
esta adquisición; lo que debe aislarse son sus escrituras y demás efectos. El filtro
`backfill_station_filter` actualmente se aplica exclusivamente a Wunderground,
tanto en backfills como en updates normales, y solo está preparado
sintácticamente para extenderse a otras fuentes. La próxima sesión debe extraer o
envolver la lógica Meteocat en un descargador local dirigido por las ventanas
globales, sin filtro espacial, con salida únicamente provisional.

### Meteoclimatic: no tratarlo como archivo histórico

La integración disponible consume el feed/RSS operativo. No se ha encontrado
un descargador histórico fiable y versionado. Sus estaciones pueden ayudar a
describir proximidad actual, pero no deben contarse como fuente de recuperación
de 2012–2022 salvo que se identifique y valide un archivo histórico separado.

## Secuencia recomendada para la próxima sesión

1. Leer `summary.json` y todos los manifiestos CSV del directorio; comprobar que los hashes siguen
   correspondiendo al snapshot que se quiere auditar.
2. Crear debajo del mismo directorio `raw/meteocat`, `raw/aemet`,
   `raw/wunderground` y `normalized/`. No crear copias fuera de `docker-data`.
3. Consumir `historical_backfill_missing_ranges_all_stations.csv` y descargar
   para cada fuente su tramo anterior faltante de **todas las estaciones
   conocidas** disponibles en Meteocat, AEMET y la lista configurada de PWS
   Wunderground. Fragmentar por el límite de cada API y reanudar desde caché. No
   aplicar aquí el radio de 15 km ni seleccionar una estación por área. No usar
   Meteoclimatic como histórico sin verificar antes otra API o archivo.
4. Guardar cada respuesta cruda con fuente, estación, intervalo, timestamp,
   estado HTTP y checksum. Marcar explícitamente `station_not_existing`,
   `empty_period`, `variable_missing`, `request_failed` y `recovered`.
5. Normalizar sin sobrescribir el Parquet operativo. Unir el backfill
   provisional con una copia del histórico actual, mantener identidad
   `(source, station_id, local_date)`, deduplicar sin descartar filas existentes
   y conservar unidades originales y normalizadas, flags de calidad y
   procedencia.
6. Construir un Parquet provisional con la red completa. Después, y solo
   después, volver a ejecutar el selector sensible al corte: ordenar estaciones
   por distancia para cada área, elegir la más cercana utilizable y hacer
   fallback hasta 15 km. Medir recuperación por episodio, contrato, año, área,
   especie, clase, fuente y variable.
7. Comparar por separado: cobertura actual, cobertura después de fallback con
   el Parquet actual y cobertura después del backfill provisional.
8. Solo después decidir si algún dato se integra. No escribir ni promover nada
   en HA durante esta auditoría.

## Puerta de promoción a Home Assistant

Todo el proceso anterior se ejecuta en el lab local, usando exclusivamente
`docker-data`. Para cada fuente deben coexistir, sin sobrescrituras:

1. respuestas crudas cacheadas;
2. backfill normalizado;
3. copia del CSV histórico actual procedente de HA;
4. CSV histórico candidato resultante de la unión;
5. informe de comparación y validación.

Antes de considerar una promoción, el candidato debe cumplir:

- cero duplicados por `Codi Estació` + `Data Local` dentro de cada fuente;
- ninguna clave ni valor útil preexistente desaparece;
- fechas, unidades, coordenadas y códigos de estación normalizados;
- recuentos antes/backfill/después explicados por fuente;
- huecos y errores de API registrados, no convertidos silenciosamente en cero;
- reconstrucción local de `weather_daily.parquet`, artefactos micológicos y
  benchmark completada con resultados coherentes;
- `scripts/check-history.py` y las validaciones específicas de fuente sin
  errores.

La promoción será una tarea posterior y explícita. Antes de copiar los CSV
candidatos a HA se hará backup de los históricos reales y se guardará el informe
antes/después. Tras la copia, se reconstruirá el Parquet y se verificará que sus
rangos y recuentos coincidan con el candidato local. Hasta superar esta puerta,
los ficheros de HA son de solo lectura.

## Criterios de aceptación

- descarga reanudable, idempotente y cacheada;
- adquisición completa de todas las estaciones conocidas de cada servicio, sin
  filtro espacial; selección posterior determinista por menor distancia entre
  las estaciones con serie histórica utilizable, registrando cada salto y su
  motivo;
- conservación íntegra del histórico local actual y unión idempotente del
  backfill; ningún resultado vacío o error puede borrar una fila existente;
- ninguna escritura en HA ni en los datos operativos;
- ningún cero inventado para una petición fallida o una estación inexistente;
- lluvia ausente dentro de una serie válida conserva el contrato acordado,
  pero la ausencia total de histórico se registra como cobertura insuficiente;
- trazabilidad completa de fuente, estación, fecha, variables, unidades y
  calidad;
- informe antes/después que no confunda “dato descargado” con “episodio
  utilizable por todos los contratos”.

## Trabajo separado: Ordino

Ordino no forma parte de este backfill meteorológico. Su episodio de 2026 tiene
meteorología, pero el DEM 5 m de Catalunya devuelve `NoData` fuera de su
cobertura y no permite calcular la altitud representativa del área. La solución
es un DEM secundario transfronterizo trazable; no inferir la cota desde el
nombre ni añadir una excepción hardcoded.

Referencias oficiales para validar los clientes, límites y disponibilidad:
[Meteocat — Dades obertes](https://www.meteo.cat/wpweb/serveis/dades-obertes/),
[AEMET OpenData](https://opendata.aemet.es/dist/) y
[Weather Company — PWS Historical](https://developer.weather.com/docs/openapi/pws-historical-2-0).
