# Especificación de implementación — Météo-France en Rainmapper

**Estado:** propuesta lista para implementar; todavía no describe código ya
incorporado.

**Fecha:** 9 de septiembre de 2026

**Ámbito inicial:** corredor Quérigut–Formiguères–Les Angles–Font-Romeu.

**Documento de contexto:**
`rainmapper_meteofrance_infoclimat_implementation.md`. Este documento concreta
la implementación y prevalece sobre aquel cuando haya diferencias técnicas.

## 1. Decisión ejecutiva

Rainmapper incorporará `meteofrance` como quinta fuente meteorológica mediante
los CSV climatológicos diarios y abiertos de Météo-France. La primera red tendrá
solamente:

| Departamento | NUM_POSTE | Estación | Altitud | Papel inicial |
|---|---:|---|---:|---|
| 66 | `66202001` | Targasonne / Thémis | 1600 m | Font-Romeu y Cerdanya francesa |
| 66 | `66082004` | Formiguères | 1495 m | Capcir y aproximación a Quérigut |

Railleu queda expresamente fuera de la lista inicial. D09 y cualquier estación
adicional se incorporarán sólo cuando una microárea concreta y las distancias
operativas lo justifiquen.

No hace falta una clave ni una cuenta de Météo-France para esta entrega. Se
usará el dataset público diario de data.gouv.fr; no se integrarán de momento ni
la API climatológica por pedidos ni la API de observaciones en tiempo real.

La descarga de Météo-France no se añadirá al bloque monolítico de
`rainmapper_core.rainmapper`. Tendrá un ejecutable Python separado y será el
runner común quien lo invoque. La ejecución programada de `run.sh`, el botón
general de la WebUI y «Actualizar sólo Météo-France» deben recorrer exactamente
el mismo orquestador.

## 2. Hechos comprobados que condicionan el diseño

### 2.1 Fuente oficial

El dataset oficial publica datos diarios controlados, en `csv.gz`, separados
por departamento, periodo y bloque de variables. Météo-France indica que los
dos últimos años se actualizan diariamente, pero «actualización diaria del
recurso» no significa que la última jornada meteorológica disponible sea ayer:
la fecha máxima de las filas puede ir retrasada.

Fuente oficial:

<https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes>

Fichas oficiales de las dos estaciones:

- <https://donneespubliques.meteofrance.fr/metadonnees_publiques/fiches/fiche_66202001.pdf>
- <https://donneespubliques.meteofrance.fr/metadonnees_publiques/fiches/fiche_66082004.pdf>

Los ficheros D66 descargados el 8 de septiembre de 2026 ocupaban
aproximadamente 422 KiB (`RR-T-Vent`) y 225 KiB (`autres-parametres`). En ambos,
la última fecha observada para las estaciones seleccionadas era 2026-09-06.
Esto es evidencia de una ejecución, no una garantía permanente del proveedor.

Los encabezados reales contienen, entre otros:

```text
RR-T-Vent: NUM_POSTE;NOM_USUEL;LAT;LON;ALTI;AAAAMMJJ;RR;...;TN;...;TX;...;FFM;...;FXI;...;FXI3S;...
autres-parametres: NUM_POSTE;NOM_USUEL;LAT;LON;ALTI;AAAAMMJJ;...;UN;...;UX;...;UM;...
```

### 2.2 Contrato actual de Rainmapper

El histórico particionado usa la clave:

```text
(source, station_code, local_date)
```

Las fuentes admitidas hoy son `aemet`, `meteocat`, `meteoclimatic` y
`wunderground` (`rainmapper_core/weather_history_contract.py`). Los CSV vivos,
el cargador meteorológico del predictor, Tomap, GeoJSON, MapLibre, los filtros
de dispositivos y el runtime del worker contienen enumeraciones o artefactos
cerrados que también deben ampliarse.

El predictor declara como corte deseado `issue_date - 1 día`, limita estaciones
a 15 km y prefiere una estación elegible que tenga completos lluvia,
temperaturas y humedades en ese corte
(`rainmapper_core/mushroom_observation_context.py`). La selección y los modelos
IDW no deben saltarse esos contratos al añadir Francia.

La lista Wunderground local contiene ya `IFONTR8` e `IFORMI6`
(`docker-data/stations.txt`). Son las estaciones que deben permitir comprobar
el caso mixto en el que Wunderground llega a D−1 y Météo-France sólo a D−2.

### 2.3 Orquestación actual

Hay actualmente dos caminos que forman comandos de actualización:

- `rainmapper-app/run.sh`, para arranque y programación;
- `rainmapper-app/app/web_server.py`, para la WebUI.

Ambos llaman al módulo monolítico `rainmapper_core.rainmapper`. La WebUI también
mantiene listas explícitas de cuatro fuentes, mensajes de progreso, tarjetas de
estado y etiquetas de tiempos. La integración no estará completa si sólo se
añade el descargador.

## 3. Qué significa realmente el desfase de dos días

Se medirán dos magnitudes distintas:

```text
publication_lag_days = fecha_local_de_ejecución - última_fecha_MF
predictor_gap_days    = máximo(0, corte_deseado_D-1 - última_fecha_MF)
```

Ejemplo: si el 8 de septiembre el fichero termina el día 6:

- el desfase de publicación es 2 días;
- al predictor sólo le falta 1 día respecto a su corte deseado, el día 7.

Confundir ambas cantidades haría que la interfaz exagerase el problema o que el
modelo desplazase su corte sin necesidad.

### 3.1 Regla de predicción

La integración **no cambiará el corte global de D−1 a D−2**. La regla será:

1. Para cada día y variable, sólo participan estaciones con un valor realmente
   observado. Una ausencia de Météo-France no se convierte al ingerir en cero,
   no se copia desde D−2 y no se rellena con Wunderground bajo identidad
   `meteofrance`.
2. Si `IFORMI6`, `IFONTR8` u otra estación elegible aporta D−1, el predictor
   conserva D−1. Météo-France puede participar en los días anteriores de la
   ventana, pero no obliga a retrasar la predicción.
3. Si ninguna estación elegible a menos de 15 km aporta un D−1 completo, la
   salida debe indicar el corte efectivo. Sólo una variante de modelo diseñada
   y entrenada para ese horizonte puede retroceder al último día completo.
4. Si la variante no admite ese horizonte o se supera la antigüedad tolerada,
   se devuelve una abstención por meteorología incompleta. No se presenta una
   recomendación basada en un día inexistente.
5. El payload de predicción y el precálculo deben exponer
   `desired_weather_cutoff`, `effective_weather_cutoff`, `weather_gap_days` y
   las fuentes/estaciones que cubrieron el último día.

El contrato actual declara `missing_rain_effective_mm: 0.0` en determinados
cálculos de características. Precisamente por ello la integración debe impedir
que una falta del último día pase inadvertida como «no llovió»: se comprobará
la completitud del corte antes de construir o recomendar una predicción.

Hay que implementar esa comprobación expresamente. Hoy `select_station()`
prefiere una estación completa en el día requerido, pero, si ninguna lo está,
puede devolver la estación elegible más cercana; además, las coberturas mínimas
permiten hasta 2 ausencias en 21 días y 9 en 90. Son reglas útiles para huecos
internos, pero no bastan por sí solas para distinguir «falta precisamente ayer»
de «ayer no llovió».

### 3.2 Efecto por tipo de uso

| Uso | Efecto del retraso de Météo-France |
|---|---|
| Entrenamiento histórico | Normalmente ninguno cuando la jornada ya está publicada; sí puede cambiar la estación elegida o el IDW al añadir una serie oficial nueva. |
| Predicción con WU completo en D−1 | Météo-France complementa la ventana anterior; WU cubre el último día. No se retrasa todo el predictor. |
| Predicción sólo con MF y MF termina en D−2 | Se declara hueco de un día; se usa una variante de horizonte compatible o se abstiene. |
| MapLibre | Puede mostrar la estación, pero siempre con fecha observada, antigüedad y aviso visual si va retrasada. |
| Preprocesado/precálculo | Debe persistir el corte efectivo y la razón de cualquier veto; no puede ocultar el desfase. |

### 3.3 Clasificación de frescura

La descarga y la frescura son estados distintos:

| Resultado de descarga | `freshness_status` | Estado operativo |
|---|---|---|
| Éxito y `publication_lag_days <= expected` | `EXPECTED` | `OK`, salida 0 |
| Éxito y `expected < lag <= stale_after` | `DELAYED` | `OK` con aviso amarillo, salida 0 |
| Éxito pero `lag > stale_after` | `STALE` | `STALE`, salida 2 si hay datos reutilizables |
| Fallo y existe histórico anterior | se conserva el último conocido | `STALE`, salida 2 |
| Fallo y no existe dato utilizable | `UNKNOWN` | `NOK`, salida 1 |

Los valores iniciales propuestos son 2 días esperados y 4 días para considerar
la fuente obsoleta. Son umbrales operativos configurables, no permisos para
inventar D−1 ni para alterar el horizonte del modelo.

## 4. Configuración de Home Assistant

Se añadirán a `options` y `schema` de `rainmapper-app/config.yaml` exactamente
estas opciones:

| Opción | Tipo | Inicial | Uso |
|---|---|---:|---|
| `create_meteofrance` | `bool` | `false` | Activa la fuente tras validar localmente el despliegue. |
| `meteofrance_request_timeout` | `int` | `30` | Timeout por petición HTTP, en segundos. |
| `meteofrance_max_attempts` | `int` | `3` | Intentos acotados por recurso. |
| `meteofrance_expected_publication_lag_days` | `int` | `2` | Umbral informativo de retraso normal. |
| `meteofrance_stale_after_days` | `int` | `4` | A partir de qué antigüedad se marca `STALE`. |

Validaciones:

- timeout: entero positivo;
- intentos: entre 1 y 5;
- retrasos: enteros no negativos;
- `meteofrance_stale_after_days` debe ser mayor o igual que
  `meteofrance_expected_publication_lag_days`.

No se añadirá:

- `meteofrance_api_key`, porque los CSV públicos no la necesitan;
- una URL mutable en `config.yaml`;
- una lista de departamentos duplicada: los departamentos salen del fichero de
  estaciones;
- un ajuste que fuerce al predictor a D−2.

`rainmapper-local/options.local-ha-ui.json` incorporará las mismas opciones para
que HA local sea una prueba fiel. La fuente permanecerá desactivada por defecto
hasta que existan fichero de estaciones y pruebas de extremo a extremo.

## 5. Lista persistente de estaciones

Se creará una lista separada de la de Wunderground:

```text
/share/rainmapper/meteofrance_stations.txt
```

y el enlace interno:

```text
/app/meteofrance_stations.txt
```

La imagen incluirá `/app/meteofrance_stations.example.txt`, pero `run.sh` sólo
copiará el ejemplo si el fichero persistente no existe. Una actualización de la
imagen nunca sobrescribirá la selección del usuario.

Formato, una estación activa por línea:

```text
# department;NUM_POSTE;label
66;66202001;Targasonne / Themis
66;66082004;Formigueres
```

Reglas:

- líneas vacías y líneas cuyo primer carácter útil sea `#` se ignoran;
- departamento metropolitano: dos dígitos;
- `NUM_POSTE`: ocho dígitos, conservados como texto;
- la pareja departamento/código se valida y los duplicados se rechazan;
- el nombre es sólo una ayuda humana; el nombre, coordenadas y altitud
  operativos proceden del fichero oficial;
- una lista vacía con la fuente activada es error de configuración, no una
  petición para descargar Francia entera.

`Railleu` no aparecerá ni siquiera activa por defecto. Añadir D09 en el futuro
será tan sencillo como agregar líneas válidas; el descargador agrupará por
departamento y descargará cada recurso una sola vez.

## 6. Arquitectura de código

### 6.1 Módulos

La separación mínima será:

```text
rainmapper_core/
  create_meteofrance.py       # CLI y ciclo de una ejecución MF
  meteofrance_source.py       # catálogo, descarga, parser y normalización puros
  weather_source_runtime.py   # estado/tiempos compartidos, extraído del monolito
  weather_update_runner.py    # orquestador común de todas las fuentes
```

Responsabilidades:

- `meteofrance_source.py` no conoce HTML ni Home Assistant. Recibe opciones,
  descubre recursos, descarga, filtra y devuelve filas canónicas e informes.
- `create_meteofrance.py` controla pending, upsert, escrituras atómicas, estado,
  diagnósticos y código de salida.
- `weather_source_runtime.py` centraliza `SourceTimings`, intervalos,
  `record_source_status` y actualización atómica por fuente. Así el proceso
  independiente emite el mismo contrato que las fuentes existentes.
- `weather_update_runner.py` es el único responsable del orden transaccional y
  de combinar códigos de salida.

No se moverán las cuatro fuentes existentes a módulos nuevos sólo para esta
entrega. El runner podrá seguir llamando una vez al proceso legacy para ellas y
llamar después al proceso Météo-France. La descarga francesa no se importará ni
se ejecutará desde el `ThreadPoolExecutor` del monolito.

### 6.2 Un único runner real

Tanto `run.sh` como `web_server.command_for("update")` invocarán:

```text
python -m rainmapper_core.weather_update_runner ...
```

El runner ejecutará procesos hijos, no código de proveedor embebido:

```text
lock meteorológico
→ archivar pending anterior
→ preflight de disco
→ inicializar estado de las cinco fuentes
→ proceso legacy para las cuatro fuentes existentes
→ python -m rainmapper_core.create_meteofrance (si está habilitada)
→ archivar pending nuevo
→ mantenimiento oficial habilitado
→ combinar resultados
```

La primera versión los ejecutará secuencialmente. Evita carreras sobre
`source_status.json`, los CSV vivos y pending, y limita CPU/memoria en la
Raspberry Pi. El tamaño observado de D66 no justifica paralelizar otro proceso.

El modo «Actualizar sólo Météo-France» ejecutará el mismo runner con:

```text
--only-source meteofrance
```

y no arrancará el monolito legacy. Los demás botones conservarán su
comportamiento, pero pasarán también por el orquestador común. El runner no
cambiará opciones persistidas al ejecutar un `only-source`.

### 6.3 Variables que prepara `run.sh`

`run.sh` leerá las cinco opciones y exportará:

```text
RAINMAPPER_CREATE_METEOFRANCE
RAINMAPPER_METEOFRANCE_STATIONS_FILE=/app/meteofrance_stations.txt
RAINMAPPER_METEOFRANCE_REQUEST_TIMEOUT
RAINMAPPER_METEOFRANCE_MAX_ATTEMPTS
RAINMAPPER_METEOFRANCE_EXPECTED_PUBLICATION_LAG_DAYS
RAINMAPPER_METEOFRANCE_STALE_AFTER_DAYS
```

Además:

- creará el fichero persistente sólo si falta;
- conservará el fichero al recrear el contenedor;
- mostrará en el banner si la fuente está habilitada, su ruta, timeout,
  intentos y umbrales de frescura;
- no imprimirá claves, cabeceras HTTP completas ni URLs firmadas;
- pasará `days_init`/`days_end` al runner. El descargador puede recibir un
  recurso de dos años, pero sólo normaliza y hace upsert de las fechas
  incluidas en la ventana solicitada.

Interfaz CLI normativa del runner:

```text
--create-meteofrance true|false
--meteofrance-stations-file /app/meteofrance_stations.txt
--meteofrance-request-timeout 30
--meteofrance-max-attempts 3
--meteofrance-expected-publication-lag-days 2
--meteofrance-stale-after-days 4
--days-init -7
--days-end 0
--only-source meteofrance             # sólo cuando se pulsa el botón específico
```

El runner trasladará al proceso `create_meteofrance.py` únicamente sus
argumentos propios, el directorio de datos, la ventana y el identificador padre
de diagnóstico. No le pasará credenciales de otros proveedores.

La reconstrucción histórica completa no se ligará al backfill mensual general.
Será una acción administrativa explícita del CLI Météo-France con fechas,
preflight y resumen previo; una actualización diaria no releerá ni reescribirá
innecesariamente toda la historia.

## 7. Descubrimiento y descarga

### 7.1 Recursos

El cliente consultará los metadatos actuales del dataset mediante la API de
data.gouv.fr y seleccionará por metadatos, no por UUID ni URL hardcodeados:

```text
departamento seleccionado
+ periodo que contiene la ventana solicitada
+ bloque RR-T-Vent
+ bloque autres-parametres
+ formato csv.gz
```

Para la actualización normal se elegirá el periodo reciente que contiene los
dos últimos años. Para un backfill se resolverán todos los periodos que se
solapen con el intervalo pedido.

Antes de publicar nada se verificará:

- exactamente un recurso inequívoco por departamento, periodo y bloque;
- HTTP correcto, tamaño no vacío y gzip válido;
- separador `;` y columnas obligatorias;
- fechas plausibles y `NUM_POSTE` solicitados presentes;
- par coherente `RR-T-Vent` + `autres-parametres`.

Si falta o es ambiguo uno de los dos bloques, la actualización de ese
departamento no se publica. Se conserva el incremental anterior y se informa
como `STALE`; no se crea una mezcla parcial con humedad antigua y lluvia nueva.

### 7.2 Recursos limitados

El parser recorrerá el gzip como stream CSV y descartará de inmediato estaciones
no incluidas en la lista. Sólo materializará las filas de las estaciones
seleccionadas y las claves necesarias para unir ambos bloques. No se cargará un
departamento completo en pandas ni se persistirá una copia raw permanente.

Se guardará únicamente un manifiesto diagnóstico pequeño con URL pública,
fecha de actualización anunciada, tamaño, hash, filas leídas/seleccionadas y
rango de fechas. El preflight rechazará el lote antes de descargar si los
metadatos exceden el presupuesto de disco disponible.

Los reintentos serán acotados, con espera creciente y aleatoria sólo para
errores transitorios. Errores de esquema, gzip, ambigüedad o validación no se
reintentan como si fueran fallos de red.

## 8. Normalización y artefactos

### 8.1 Unión y mapeo

Los dos bloques se unen por:

```text
(NUM_POSTE, AAAAMMJJ)
```

Mapeo:

| Météo-France | Campo canónico | Regla |
|---|---|---|
| `NUM_POSTE` | `station_code` | texto, sin perder ceros |
| `AAAAMMJJ` | `local_date` | fecha diaria publicada, sin desplazar zona horaria |
| `NOM_USUEL` | `station_name` | texto oficial |
| `LAT`, `LON`, `ALTI` | `lat`, `lon`, `altitude` | numéricos validados |
| `RR` | `rain_mm` | mm |
| `TN`, `TX` | temperaturas mínima/máxima | °C |
| `UN`, `UX` | humedades mínima/máxima | % |
| `FFM` | `wind_avg_kmh` | m/s × 3,6 |
| `FXI3S`, si no `FXI` | `wind_gust_kmh` | m/s × 3,6 |
| dirección asociada a la racha elegida | `wind_gust_direction_deg` | grados |

Los vacíos permanecen `null`. Los campos `Q*` se validan y resumen en el
diagnóstico, pero no se copian como columnas repetidas en cada fila del contrato
operativo. Nunca se rellena un `null` con cero durante la ingestión.

### 8.2 Nombres de salida

```text
Data/Meteofrance.csv
Data/Meteofrance_incremental.csv
Data/estacions_meteofrance.csv
Data/diagnostics/meteofrance-latest.json
```

Identificadores:

- fuente canónica y partición: `meteofrance`;
- clave de `source_status.json`: `Meteofrance`;
- etiqueta visible: `Météo-France`.

El incremental usa el esquema legacy compatible con el resto de Rainmapper y
el pending se normaliza al contrato canónico. Antes de tocar un CSV vivo se
captura su versión pendiente; todas las escrituras usan temporal + `os.replace`.

El upsert es por `(meteofrance, station_code, local_date)` y sigue la regla
existente de conservar valores anteriores cuando una reedición nueva trae un
campo nulo. Una corrección oficial no duplica la jornada.

## 9. Histórico, mapas y predictor

La integración debe añadir `meteofrance` en todos los puntos cerrados, como
mínimo:

- `weather_history_contract.KNOWN_SOURCES`;
- `weather_live_csv.LIVE_CSV_FILES`;
- `mushroom_observation_context.DAILY_INCREMENTAL_FILES`;
- lector/archivo/pending/mantenimiento del histórico particionado;
- catálogo `weather_stations_catalog.parquet`;
- Tomap y su ruta de compatibilidad CSV;
- detección explícita de fuente en `geojson.py`;
- filtros, atribución y estados en `viewers/maplibre-viewer/app.js`;
- snapshots de inputs de entrenamiento y artefactos de precálculo;
- manifest del runtime del predictor y `service_paths` del worker.

No se inferirá Météo-France por la longitud del código: un `NUM_POSTE` puede
colisionar conceptualmente con otros identificadores. El campo `Source` se
conservará explícito de extremo a extremo. Si una ruta legacy necesita prefijo
en `Codi Estació`, se utilizará `METEOFRANCE:<NUM_POSTE>` sólo en esa
representación y se ocultará en la interfaz, sin cambiar la clave canónica.

`meteofrance_stations.txt` se incluirá en el manifest inmutable del runtime, al
igual que hoy se incluye `stations.txt`, para que coordinador y worker
reconstruyan exactamente la misma selección de estaciones. El hash del fichero
formará parte de la identidad del runtime.

### 9.1 Coincidencia geográfica con Wunderground

Météo-France y Wunderground conservarán identidades independientes; no son la
misma observación ni una sustituye silenciosamente a la otra. Antes de activar
la fuente en modelos IDW se ejecutará un informe de sensibilidad para las parejas
próximas a Formiguères y Font-Romeu:

- distancia horizontal y diferencia de altitud;
- disponibilidad por variable y día;
- efecto de incluir ambas frente a cada fuente por separado;
- frecuencia con la que cambia la estación elegida.

No se introducirá un radio arbitrario de «deduplicación física» sin ese informe.
Si se demuestra doble ponderación perjudicial, la solución deberá formar grupos
físicos explícitos o equilibrar por fuente; no se descartará una serie sólo por
tener un nombre parecido.

## 10. Estado, diagnósticos y mensajes

### 10.1 `source_status.json`

Météo-France usará los campos comunes existentes:

```text
status, exit_code, message, rows, stations, stale_data_used, enabled,
updated_at, started_at, finished_at, duration_seconds, timings,
phase_intervals
```

y un resumen específico, pequeño:

```text
freshness_status
publication_lag_days
expected_publication_lag_days
stale_after_days
desired_predictor_cutoff
latest_source_date
predictor_gap_days
stations_complete_at_desired_cutoff
resources_downloaded
selected_rows
rejected_rows
```

El detalle por estación y recurso irá en
`Data/diagnostics/meteofrance-latest.json`, no duplicado dentro del estado que
la WebUI consulta frecuentemente.

La actualización de estado será un merge atómico por fuente. Un proceso no
puede borrar el estado de las otras cuatro. El runner inicializa las cinco
entradas como `PENDING`; un origen desactivado termina en `DISABLED` sin borrar
datos previos.

### 10.2 Fases y tarjeta de tiempos

`SourceTimings` registrará intervalos reales y no estimaciones:

| Campo | Etiqueta WebUI |
|---|---|
| `station_list_seconds` | station list |
| `resource_discovery_seconds` | discovery |
| `download_seconds` | download |
| `parse_filter_seconds` | parse/filter |
| `join_seconds` | join |
| `normalize_seconds` | normalize |
| `pending_capture_seconds` | pending |
| `read_incremental_seconds` | read incr. |
| `upsert_incremental_seconds` | upsert |
| `write_outputs_seconds` | write |

Cada fase emitirá `source_phase_start` y `source_phase_complete` con el mismo
`RAINMAPPER_PARENT_OPERATION_ID` del runner. Al finalizar emitirá
`source_complete`. Así la tarjeta temporal y el Gantt diagnóstico no dependerán
sólo de analizar texto del log.

### 10.3 Mensajes de progreso

El proceso imprimirá líneas humanas breves y eventos estructurados equivalentes:

```text
Start processing Meteofrance
Meteofrance station list: 2 active stations in 1 department
Meteofrance resources: discovering D66 latest daily pair
Processing Meteofrance stations 1 of 2
Meteofrance freshness: latest=2026-09-06 publication_lag=2 predictor_gap=1
Meteofrance update finished: status=OK rows=... stations=2
```

No se imprimirá una línea por fila. La WebUI reconocerá al menos el inicio, el
contador de estaciones y la finalización para actualizar `current_step` y la
barra de progreso.

### 10.4 WebUI y MapLibre

Se añadirán `Meteofrance`/`Météo-France` en:

- `UPDATE_SOURCE_FLAGS` y `source_flag_value`;
- `DEVICE_SETTING_SOURCES`;
- tarjetas, tabla y recuento de fuentes;
- lista de fuentes del Gantt;
- parser de progreso;
- filtro de fuentes de MapLibre;
- estado de fuente dentro del visor;
- atribución: «Información elaborada por Rainmapper a partir de datos de
  Météo-France — Licence Ouverte 2.0».

La tarjeta específica mostrará:

- estado operativo;
- frescura `EXPECTED`, `DELAYED` o `STALE`;
- última fecha oficial;
- desfase de publicación y hueco para el predictor por separado;
- estaciones completas en D−1, por ejemplo `1/2`;
- filas, estaciones, duración, mensaje y desglose de tiempos;
- botón «Actualizar sólo Météo-France».

MapLibre mostrará en cada popup la fecha del dato y «hace N días». Una estación
Météo-France retrasada puede visualizarse, pero el amarillo/rojo de frescura no
se sustituye por un `OK` genérico de descarga.

## 11. Errores y códigos de salida

Reglas del proceso Météo-France:

- `0`: fuente desactivada o actualización utilizable dentro de las reglas;
- `2`: hay datos anteriores reutilizables, pero falla la actualización o están
  obsoletos;
- `1`: fuente activada sin datos utilizables o error de configuración/esquema.

Reglas del runner completo:

- una fuente degradada no borra las salidas válidas de las demás;
- el código combinado conserva la semántica actual de éxito, degradado y fallo;
- un fallo de archive/pending es fatal y no se continúa escribiendo live;
- el mantenimiento oficial sólo corre después de archivar correctamente;
- Météo-France se añade al mantenimiento de huecos cuando exista un reparador
  específico por periodos públicos; no se reutiliza a ciegas el cliente de
  Meteocat o AEMET;
- una descarga correcta sin filas de ninguna estación seleccionada es `NOK`, no
  un éxito de cero filas;
- una descarga sin cambios, pero con estaciones y fecha máxima verificadas, sí
  es un `OK` idempotente.

## 12. Seguridad, persistencia y operación

- No hay secreto Météo-France en la primera entrega.
- Sólo se aceptan HTTPS de data.gouv.fr/Météo-France descubiertos desde el
  dataset oficial; se validan redirecciones y tipo de contenido.
- Los nombres de recurso nunca se convierten directamente en rutas locales.
- Los temporales se crean dentro de una carpeta acotada y se eliminan al
  finalizar.
- No se cambia ninguna URL de coordinador ni asociación persistida de worker.
- No se toca `mushroom-data/mushroom_observations.json`.
- La imagen HA copia el ejemplo de estaciones y los módulos, pero el catálogo
  operativo sigue en `/share/rainmapper`.
- Logs y diagnósticos no guardan el contenido íntegro de los CSV ni repiten
  metadatos por fila.

## 13. Pruebas requeridas

### 13.1 Unitarias

- parser de ambos bloques con `;`, gzip, nulos, decimales y códigos como texto;
- unión por estación/fecha, precedencia `FXI3S`/`FXI` y conversión m/s→km/h;
- lista de estaciones, comentarios, duplicados y errores;
- descubrimiento inequívoco de recursos con fixtures de metadata;
- reintentos sólo de errores transitorios;
- upsert idempotente y conservación de valores no nulos anteriores;
- merge atómico de `source_status.json` sin perder otras fuentes;
- matriz `EXPECTED`/`DELAYED`/`STALE` y ambos cálculos de desfase;
- códigos 0/1/2 con y sin fallback.

### 13.2 Contrato e integración

- `meteofrance` admitido en Parquet, pending, live reapply y catálogo;
- ejecución full y `--only-source meteofrance` desde el mismo runner;
- paridad entre comando programado y WebUI;
- tarjeta, tiempos, Gantt, mensajes y `source_status.json`;
- Tomap/GeoJSON/MapLibre con fuente, fecha, filtro y atribución correctos;
- runtime del worker incluye el histórico y la lista de estaciones con hashes
  verificables;
- reinicio/recreación conserva `meteofrance_stations.txt`.

### 13.3 Predicción

Casos mínimos fechados y deterministas:

1. MF llega a D−2 y WU a D−1: corte efectivo D−1, último día cubierto por WU.
2. MF y WU llegan a D−1: ambas series disponibles y selección/IDW auditable.
3. Sólo MF a D−2: horizonte efectivo explícito o abstención, nunca D−1 igual a
   lluvia cero implícita.
4. Ninguna estación completa dentro de 15 km: abstención existente, sin ampliar
   radio.
5. Una fuente carece de humedad en D−1: no cuenta como día completo para un
   modelo que exija lluvia, temperaturas y humedad.
6. Retraining con y sin MF: informe de cambios de estación, cobertura,
   características y decisiones por especie antes de promover modelos.

### 13.4 Validación operativa antes de HA real

Cuando se implemente código, la aceptación exigirá:

1. tests dirigidos del proveedor, contrato, runner y UI;
2. reconstruir desde el mismo worktree HA local y worker local;
3. comprobar dentro de ambos contenedores versión/huella efectiva;
4. ejecutar actualización Météo-France local y auditar CSV, pending, Parquet,
   estado y diagnósticos;
5. generar mapas y comprobar la estación en MapLibre;
6. ejecutar el circuito local de entrenamiento/precálculo afectado por el nuevo
   histórico y auditar recepción/activación;
7. sólo entonces proponer una versión HA real.

No se repetirá la suite completa, entrenamiento o precálculo durante la fase
puramente documental ni antes de existir código que cambie los artefactos.

## 14. Orden de implementación

1. Añadir contrato, lista persistente y parser con fixtures reales recortados.
2. Implementar `create_meteofrance.py`, escrituras atómicas, pending y estados.
3. Extraer el runtime común de estados/tiempos y crear
   `weather_update_runner.py`.
4. Hacer que `run.sh` y `web_server.py` usen el mismo runner.
5. Integrar histórico, catálogo, Tomap, GeoJSON y MapLibre.
6. Integrar runtime de worker, entrenamiento y precálculo.
7. Ejecutar la matriz de desfase y el informe de sensibilidad MF/WU.
8. Validar todo el circuito local y presentar resultados antes de activar la
   fuente por defecto o preparar una release.

## 15. Criterio de terminado

La integración no se considerará terminada sólo porque existan
`Meteofrance_incremental.csv` o dos estaciones en el mapa. Estará terminada
cuando una misma ejecución pueda demostrar, de extremo a extremo:

- qué recursos oficiales descargó;
- qué estaciones y fechas aceptó;
- qué antigüedad tiene el dato y qué hueco deja para el predictor;
- qué escribió en live, pending y Parquet;
- qué fuente cubrió el corte de cada predicción;
- por qué una predicción se publicó, retrocedió de horizonte o se abstuvo;
- que HA local, worker local, WebUI, MapLibre y artefactos persistidos describen
  el mismo estado.
