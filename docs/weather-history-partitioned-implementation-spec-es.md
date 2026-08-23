# Especificación de histórico meteorológico particionado

Estado: **IMPLEMENTADO**. Diseño original revisado el 2026-08-12 para una RPi4
con 4 GiB de RAM; contrato de recuperación de entregas autosuficientes añadido
el 2026-08-23. Este documento no autoriza por sí mismo nuevas promociones,
compactaciones ni escrituras en HA.

## Objetivo y restricciones

Sustituir la doble función actual de los cuatro `*_incremental.csv` por:

1. cuatro colas vivas de 180 fechas locales;
2. un histórico Parquet completo, particionado y transaccional;
3. consumidores que leen una generación coherente mediante un manifiesto.

La implementación debe cumplir simultáneamente:

- conservar exactamente todas las claves y valores útiles del candidato;
- no convertir error, vacío, variable ausente o estación inexistente en cero;
- no borrar un valor histórico útil cuando una lectura nueva trae `NaN`;
- no cargar ni reescribir cinco millones de filas en cada runner;
- mantener el archivador por debajo de `128 MiB` RSS adicionales y `256 MiB`
  absolutos en la RPi4; el objetivo es `64/192 MiB`;
- no exponer a Predictor, Tomap o workers una mezcla de generaciones;
- permitir rollback sin reconstruir el histórico;
- mantener el histórico dentro del almacenamiento persistente y respaldado de
  HA cuando se autorice su promoción.

## Correcciones al diseño preliminar

La revisión de código y de los artefactos reales detectó estos puntos que el
diseño preliminar no resolvía:

1. **Bootstrap**. El Parquet candidato actual de 82 MiB solo tiene 14 columnas.
   No contiene varios metadatos ni el contrato completo de viento. AEMET,
   cuatro fuentes tienen 27 columnas legacy en los candidatos actuales. El
   bootstrap del corte actual parte de los cuatro CSV completos ya reconciliados
   en `rebase-trials/20260811T114432Z/candidate/`; usar los tres `candidate/`
   originales más `current/Meteoclimatic_incremental.csv` perdería 301 filas
   incorporadas durante el rebase. La
   migración inicial debe normalizarlos al schema canónico de 28 columnas por
   chunks, añadiendo `source` y dejando a null únicamente las columnas realmente
   ausentes. El Parquet antiguo solo sirve como referencia de paridad, nunca
   como única fuente.
2. **Atomicidad de dataset**. Sustituir `source/year` directamente, uno tras
   otro, permitiría que un lector viera unos años nuevos y otros antiguos. Las
   particiones deben ser inmutables y una generación debe publicarse cambiando
   un puntero/manifiesto pequeño mediante `os.replace()`.
3. **Carga normal**. Reaplicar las 228.470 filas de los 180 días en cada runner
   sigue siendo innecesario. La ruta normal debe archivar solo el lote fresco o
   corregido. La cola completa se reserva para reparación explícita.
4. **Crash entre CSV e histórico**. Cada lote fresco debe escribirse primero en
   un journal `pending` atómico. Tras un reinicio se reaplica al CSV vivo y al
   histórico; la operación es idempotente.
5. **Primer despliegue**. No se puede confiar en que la primera ejecución de la
   RPi lea y compacte el AEMET de 714 MiB. Las cuatro colas compactadas deben
   prepararse y validarse en la migración, y solo sustituirse después de
   promover/verificar el histórico.
6. **Catálogo**. El catálogo actual solo guarda nombre/coordenadas/altitud y se
   obtiene de la primera fila encontrada. Necesita `first_date`, `last_date` y
   metadata vigente determinista para no llenar el top-N histórico con
   estaciones que todavía no existían. Las exclusiones por mala calidad siguen
   siendo reglas externas explícitas; no se deducen de ausencia de datos.
7. **Cachés**. Predictor invalida hoy por el `mtime` de un único Parquet. Debe
   invalidar por `generation_id`. Un runner idempotente puede confirmar una
   generación válida sin cambiar su mtime; frescura no debe equivaler a
   “archivo reescrito”.
8. **Reconstrucción ML**. `station_filter=None` carga hoy el Parquet completo en
   pandas. Cambiar el path por un directorio sin cambiar esa conducta volvería
   a agotar memoria. La reconstrucción debe consumir batches o rangos/estaciones
   previamente acotados.
9. **Snapshots/workers**. Actualmente el snapshot prefiere un solo
   `weather_daily.parquet`; el materializador de runtime copia únicamente los
   CSV legacy. Hay que versionar el contrato, enumerar manifiesto/particiones y
   usar caché por hash para no transferir todo en cada job.
10. **Concurrencia y limpieza**. Predictor puede leer mientras el runner escribe
    y HA puede iniciar un backup. Los ficheros ya publicados no se sobrescriben
    ni se borran inmediatamente. La limpieza solo elimina objetos no
    referenciados por las generaciones retenidas y tras un periodo de gracia.
11. **Corte contra HA vivo**. El laboratorio parte de un snapshot, mientras los
    runners de HA siguen actualizando los CSV. La promoción no puede copiar sin
    más la generación del laboratorio: debe reconciliar un snapshot fresco y
    estable de HA y hacer el cambio dentro de una ventana de mantenimiento
    explícitamente autorizada, sin perder las filas aparecidas durante el
    backfill.
12. **Instalación virgen — tarea futura, no prioritaria**. El flujo actual no es
    autónomo: `partitioned_weather_history` nace desactivado y la primera
    generación de esta instalación se preparó mediante una migración externa.
    No existe una fecha de inicio meteorológica universal. El alcance necesario
    debe derivarse de la observación de setas más antigua que se quiera soportar
    y del máximo lookback exigido por el contrato biológico. Queda pendiente
    decidir, cuando el resto del sistema esté cerrado, si el bootstrap usa una
    semilla verificada, un trabajo separado reanudable o una combinación. Este
    inciso no forma parte de la reparación ni del benchmark actuales.

## Autorreparación de una instalación existente

En una instalación existente, cada runner conserva el solape normal de siete
días y además mantiene una cola persistente
`official-weather-gap-repair.json`:

- agrupa días ausentes en bloques máximos de 15 días;
- ejecuta como máximo un bloque debido por fuente y runner;
- persiste intentos, último error y siguiente reintento;
- aplica espera creciente con máximo de siete días;
- solo retira un día cuando aparece realmente en la generación archivada;
- apaga el estado degradado cuando no quedan rangos pendientes;
- no convierte una respuesta vacía, un error o una estación inexistente en
  lluvia cero.

La reparación siempre se archiva en el histórico particionado completo. Después
se reaplica el lote al CSV vivo con su retención normal de 180 días. Por tanto,
un bloque más antiguo queda corregido en el histórico aunque aporte cero filas
al CSV vivo; uno reciente actualiza ambos. Si el proceso se interrumpe después
de archivar y antes de cerrar el CSV, el lote durable permanece pendiente y el
siguiente runner completa esa segunda fase antes de reconocerlo.

Los adaptadores no son iguales. Meteocat usa el contrato histórico ya probado:
dos consultas de red por bloque de 15 días —lluvia y condiciones— con pausa de
cinco segundos. AEMET usa climatología diaria, cuyo máximo de API también es 15
días; el backfill masivo anterior agrupaba dos peticiones como un lote mensual y
empleaba una pausa mínima estable de dos segundos. La autocuración será más
conservadora: como máximo una petición AEMET de 15 días por runner. El flujo
diario AEMET normal sigue siendo distinto y usa observaciones horarias globales.

El estado batch produce salida degradada no bloqueante y un informe persistente;
su presentación específica en Diagnostics y Errors queda pendiente. Una
instalación existente reiniciada reanuda la cola sin intervención.
AEMET requiere que el usuario haya configurado su API key para descargar nuevos
datos; Meteocat no requiere token. Si falta la key, el histórico existente
sigue siendo válido y la cola AEMET permanece pendiente con motivo legible, sin
degradar ni falsificar los datos de otras fuentes.

## Arquitectura final

### Colas vivas

Se conservan los nombres actuales:

```text
Data/Aemet_incremental.csv
Data/Meteocat_incremental.csv
Data/Meteoclimatic_incremental.csv
Data/Wunderground_incremental.csv
```

Cada fichero contiene el día local actual y las 179 fechas locales anteriores,
usando `Europe/Madrid`. Es un corte de calendario inclusivo, no 4.320 horas.
Una fecha sin filas no se inventa. Un registro con clave inválida o fecha futura
no se elimina silenciosamente: debe fallar la validación y quedar reportado.

Los intradía son contratos separados:

- AEMET horario: siete fechas cerradas más la actual;
- Meteoclimatic snapshots: siete fechas cerradas más la actual.

Los CSV vivos sirven para descarga/upsert, reintentos y recuperación. No son el
histórico canónico y ningún consumidor histórico puede hacer fallback
silencioso a ellos.

### Layout físico del histórico

```text
Data/weather-history/
├── CURRENT.json
├── manifests/
│   └── <generation_id>.json
├── parts/
│   ├── source=aemet/year=2026/data-<sha256>.parquet
│   ├── source=meteocat/year=2026/data-<sha256>.parquet
│   └── ...
├── catalogs/
│   └── stations-<sha256>.parquet
├── pending/
│   └── source=<source>/batch-<id>.parquet
├── leases/
│   └── <generation_id>/<lease_id>.json
└── locks/
    └── writer.lock
```

Las rutas `source=.../year=...` son organización física. Los lectores no deben
hacer glob ni inferir por Hive: abren únicamente los ficheros enumerados en el
manifiesto activo. Cada Parquet conserva físicamente `source`,
`station_code` y `local_date`.

Con el candidato actual hay 46 particiones. La mayor es `aemet/2024`, con
302.955 filas; por tanto una actualización fuente/año puede probarse sin cargar
los cinco millones de filas.

### Schema diario

Orden canónico de columnas:

```text
station_code, reading_datetime, station_name, county, municipality, province,
local_date, local_time, lat, lon, altitude, last_reading, variable, rain_mm,
unit, max_temp_celsius, min_temp_celsius, max_humidity_percent,
min_humidity_percent, wind_avg_kmh, wind_min_kmh, wind_max_kmh,
wind_gust_kmh, wind_direction_deg, wind_gust_direction_deg,
wind_observation_count, wind_source_height_m, source
```

Contrato:

- clave única: `(source, station_code, local_date)`;
- `source` solo admite `aemet`, `meteocat`, `meteoclimatic` o `wunderground`;
  se deriva del fichero/proveedor, nunca de texto libre contenido en una fila;
- `local_date`: string estricta `YYYYMMDD`; el año se deriva de ella;
- `reading_datetime`, `last_reading` y `local_time` conservan el formato
  normalizado vigente; no se reinterpretan zonas horarias durante el bootstrap;
- strings normalizados sin transformar ausencia en texto vacío significativo;
- numéricos como `float64` para compatibilidad con el contrato actual;
- orden dentro de partición: `station_code`, `local_date`;
- si un lote contiene varias filas para la misma clave, el orden de entrada es
  vinculante: la última fila gana en sus valores no nulos y hereda los valores
  útiles anteriores en el resto. El informe cuenta esas claves colapsadas;
- compresión inicial: Snappy;
- `row_group_size` inicial: 8.192 filas; comparar 8.192/4.096/2.048 en benchmark
  y cambiarlo solo con resultados documentados;
- supresión de lluvia repetida y límites de calidad se aplican después, en el
  consumidor/feature correspondiente. El histórico conserva el valor diario
  normalizado original y su procedencia.

El merge normal no admite borrados implícitos. Un null fresco significa
"conservar el valor útil anterior". Esta implementación no incorpora borrados.
Si en el futuro hay que retirar una fila o vaciar deliberadamente un dato
erróneo, requerirá una especificación separada de tombstone/corrección,
versionada, auditada y fuera de la ruta normal de descarga.

### Manifiesto y commit transaccional

Cada `manifests/<generation_id>.json` es inmutable e incluye como mínimo:

```json
{
  "schema_version": "weather_history_manifest_v1",
  "generation_id": "...",
  "previous_generation_id": "...",
  "created_at": "...",
  "data_schema_version": "weather_daily_v1",
  "key": ["source", "station_code", "local_date"],
  "partitions": [
    {
      "source": "aemet",
      "year": 2026,
      "path": "parts/source=aemet/year=2026/data-<sha>.parquet",
      "sha256": "...",
      "size_bytes": 0,
      "rows": 0,
      "min_local_date": "20260101",
      "max_local_date": "20261231"
    }
  ],
  "catalog": {"path": "...", "sha256": "...", "rows": 0},
  "totals": {"rows": 0, "size_bytes": 0},
  "update_report": {}
}
```

La validación exige exactamente una entrada por `(source, year)`, paths
relativos contenidos bajo `weather-history/`, hashes/tamaños coincidentes,
schema idéntico, rangos contenidos en el año declarado y totales recalculados.
Un manifiesto con particiones duplicadas, desconocidas o no ordenadas de forma
determinista no se publica.

`CURRENT.json` contiene el `generation_id`, path y SHA-256 del manifiesto. Para
publicar:

1. escribir y cerrar cada partición con nombre temporal, calcular su SHA-256 y
   moverla al nombre inmutable `data-<sha256>.parquet`;
2. validar schema, claves, rangos, filas y hashes;
3. escribir y validar el catálogo versionado;
4. escribir/fsync el manifiesto inmutable;
5. escribir/fsync un `CURRENT.json` temporal;
6. hacer `os.replace()` y fsync del directorio.

Los temporales se crean en el mismo filesystem y directorio final para que el
rename sea atómico. Si ya existe el nombre por contenido, se verifican tamaño y
hash y se reutiliza; nunca se sobrescribe. La atomicidad de `os.replace()` en el
filesystem real de HA forma parte de las pruebas de prepromoción.

Un lector abre `CURRENT.json` una vez y mantiene ese manifiesto durante toda su
operación. Nunca vuelve a resolver `CURRENT` a mitad de una consulta. El
`generation_id` es único y sortable —UTC más prefijo del hash lógico—, pero el
hash validado del manifiesto, no el nombre, es la identidad de contenido.

### Catálogo de estaciones

El catálogo versionado forma parte de la misma generación. Campos mínimos:

```text
source, station_code, station_name, lat, lon, altitude,
first_date, last_date, metadata_date
```

La metadata se obtiene del registro válido más reciente, no de la primera fila.
Durante el bootstrap debe generarse un informe de cambios de nombre,
coordenadas o altitud por estación. Ningún conflicto material se resuelve
silenciosamente; se conserva la metadata diaria y se documenta la decisión del
catálogo.

Una clave histórica que nunca tenga latitud y longitud válidas conserva todas
sus filas en el histórico, pero no entra en el catálogo seleccionable. Se
reporta por separado para evitar que Predictor o mapas intenten usarla y para
que su ausencia no se interprete como estación inexistente ni lluvia cero.

Auditoría del candidato actual: 1.998 claves históricas de estación, de las que
1.942 tienen coordenadas válidas y entran en el catálogo. Entre estas, 138
muestran alguna variación de coordenadas superior a un metro, ninguna supera
un kilómetro y el máximo observado es aproximadamente 226 m. Esto permite usar
la metadata válida más reciente en este candidato, pero el bootstrap debe
repetir la auditoría y bloquear la migración si aparece un desplazamiento
material nuevo.

Las 21 estaciones Wunderground retiradas por calidad deben materializarse en
una denylist compartida por selección meteorológica y mapas, partiendo de la
lista explícita ya acordada; no se vuelve a deducir la lista por vacíos. Sus
filas pueden conservarse para auditoría, pero no vuelven a ser elegibles por
aparecer en el catálogo.

Para una predicción histórica, la preselección filtra primero las estaciones
cuyo intervalo `[first_date, last_date]` intersecta la ventana solicitada y
después aplica distancia/top-N. No existir en una fecha produce fallback a otra
estación, nunca una fila artificial.

## Algoritmo de actualización normal

La unidad de trabajo es el lote fresco de una fuente, no toda la cola viva. La
ruta normal se divide deliberadamente en dos procesos que no se solapan:

1. `update-sources` descarga y normaliza las filas frescas/corregidas.
2. Antes de modificar su CSV vivo, materializa un pending canónico, inmutable y
   content-addressed. Después puede aplicar idempotentemente el pending al CSV,
   pero todavía no ejecuta la retención de 180 fechas.
3. `update-sources` termina y libera toda su memoria. El archivador no se llama
   como una función más dentro de `rainmapper.py`: se ejecuta en un proceso
   corto separado.
4. `archive-pending` adquiere `writer.lock`, resuelve una vez la generación y
   procesa todos los pending válidos, secuencialmente por partición.
5. Publica como máximo una generación nueva que contiene todos los lotes de ese
   ciclo. Las particiones no tocadas se reutilizan por referencia.
6. Reaplica idempotentemente cada pending al CSV correspondiente y compacta ese
   CSV mediante escritura streaming a 180 fechas. Que `update-sources` ya lo
   aplicara no cambia el resultado.
7. Solo después de confirmar histórico y CSV elimina el pending, libera el lock
   y emite métricas.

El wrapper ejecuta `archive-pending` antes de una descarga nueva para drenar un
crash anterior y otra vez después de `update-sources`, incluso si este último
terminó con código 1 o 2 y dejó lotes completos de otras fuentes. El código
combinado es conservador: un fallo del archivador o de `update-sources` es 1;
si ambos terminan correctamente pero hubo proveedor degradado, es 2; en otro
caso es 0. `maps` solo puede empezar después de la segunda comprobación. Un
exit 2 puede conservar la política vigente de mapas con la última generación
válida; un fallo del archivador es exit 1 y bloquea mapas.

Los modos `update` y `once` significan siempre pre-drain, descarga y post-drain;
no pueden devolver éxito dejando un pending sin intentar archivar. `all` añade
mapas únicamente después de ese flujo. El modo independiente `maps` es de solo
lectura: fija y valida la generación activa, pero no descarga, archiva ni
repara estado pendiente.

El backfill mensual administrativo es una secuencia de transacciones, no una
única transacción gigante. Cada ventana ejecuta `update-sources` y su post-drain
antes de la pausa y de abrir la ventana siguiente. No se empieza la siguiente
si el archivador falló o queda un pending normal de la misma fuente. Así se
conservan el orden de correcciones, el límite de disco y la regla de un único
pending por fuente; un código 2 puede acumularse como resultado degradado del
backfill, pero cada lote válido queda cerrado ventana a ventana.

Todo el flujo anterior mantiene un `run.lock` de filesystem exclusivo desde el
pre-drain hasta el post-drain. En un backfill mensual cubre también las pausas y
toda la secuencia, para que el scheduled runner no se intercale entre ventanas.
El lock de thread del servidor web no basta porque scheduler, CLI y web son
procesos distintos. El orden global es siempre `run.lock` y después
`writer.lock`; reparación/GC que no descargan solo usan `writer.lock`. La espera
por `run.lock` tiene timeout y devuelve estado “busy” explícito, nunca inicia
otra descarga en paralelo. Al ser `flock`, un proceso muerto libera el lock.

### Contrato del pending

- El adaptador de cada fuente debe exponer las claves realmente tocadas. Está
  prohibido usar como lote el incremental completo ya fusionado. AEMET y
  Meteoclimatic pueden incluir los siete días cerrados más el actual que hayan
  reconstruido; no incluyen automáticamente los 180 días.
- Normalizar primero en orden de llegada, adjuntar un ordinal y colapsar claves
  repetidas con “último no nulo gana”. Ordenar por clave solo después de esa
  operación, para no perder la precedencia original.
- `source`, clave y fecha son obligatorios; `local_date` es `YYYYMMDD`, `source`
  debe coincidir con el adaptador y todo numérico no nulo debe ser finito. Un
  `NaN` canónico se convierte en null; infinito o clave inválida rechazan el
  lote. Ausencia remota no crea pending.
- `batch_id` se deriva de la versión del contrato, fuente y una serialización
  lógica determinista de las 28 columnas ya colapsadas/ordenadas. No depende de
  mtime, path ni del hash no contractual de pandas.
- El sidecar incluye hash, filas, años/rangos, claves colapsadas, ordinal final,
  run id y fecha. Data y sidecar se escriben/fsync y se renombran en el mismo
  filesystem.
- El constructor acepta batches y genera runs ordenados de tamaño acotado. Un
  lote inesperadamente grande usa merge externo multipaso con fan-in máximo;
  nunca hace `sort_values()` o `sort_by()` sobre todo el lote. Antes de una
  descarga nueva no puede quedar otro pending normal de la misma fuente.

### Merge de una partición

Cada partición anterior y su pending del año están estrictamente ordenados por
`(station_code, local_date)`; `source` es constante. El escritor implementa un
merge de dos cursores:

- copia directamente slices contiguos de filas históricas no afectadas;
- materializa las 28 columnas solo para claves coincidentes o nuevas;
- una lectura nueva no nula gana y un null conserva el valor histórico;
- comprueba orden estricto y duplicados también entre límites de batches;
- acumula como máximo un row group y un número limitado de fragmentos; no crea
  una lista Python de todas las claves, filas o slices;
- al agotarse el pending, copia el resto de batches históricos sin convertirlos
  a objetos Python;
- procesa una sola partición simultáneamente y cierra/libera el writer antes de
  pasar a la siguiente.

Se compararán row groups de 8.192, 4.096 y 2.048 filas y diccionarios solo para
columnas de baja cardinalidad. También se puede prototipar un join Arrow por
batch, pero solo se acepta si conserva orden, semántica no nula y el gate de
memoria. Quedan prohibidos pandas, `MultiIndex`, sets con todas las claves y un
full outer join de la partición anual.

Antes de publicar, el writer verifica en streaming schema exacto, fuente/año,
orden, unicidad, filas esperadas, rango de fechas y valores finitos. Calcula el
SHA leyendo secuencialmente el fichero cerrado, hace fsync del fichero y del
directorio y solo entonces lo añade al manifiesto. Una colisión de nombre por
contenido se verifica y se reutiliza; nunca se sobrescribe.

El catálogo completo es pequeño y puede cargarse, pero solo se modifican las
estaciones del pending: `first_date`/`last_date`, y metadata válida más reciente.
Una corrección antigua no reemplaza metadata posterior. Una coordenada nueva a
más de 1 km de la vigente pone el lote en cuarentena salvo override auditado;
no se cambia silenciosamente. Las 56 claves históricas sin coordenadas siguen
fuera del catálogo hasta recibir coordenadas válidas.

Cada manifiesto de update registra los `batch_id` aplicados. Si el proceso cae
después de cambiar `CURRENT` pero antes de actualizar/compactar el CSV, la
recuperación detecta el receipt en la generación, omite el merge histórico,
reaplica el CSV y solo entonces elimina el pending. Mientras exista un pending
ya confirmado no se permite otro commit que oculte ese receipt.

Si el merge demuestra semánticamente cero cambios, reutiliza las particiones y
catálogo y no necesita otra generación: reaplica/compacta el CSV y elimina el
pending al final. No se reescribe una partición solo para comparar su hash.

Si no hay filas nuevas pero todas las fuentes habilitadas fueron comprobadas y
la generación activa valida, el update puede terminar correctamente sin crear
otra generación. El runner debe usar el resultado explícito del archivador, no
comparar mtimes.

### Recuperación y backfills

- Al empezar, procesar todos los pending válidos antes de una descarga nueva.
- Si falta un pending por un crash antiguo, existe un modo explícito de
  reparación que reaplica la cola de 180 días; no es la ruta normal.
- Un backfill administrativo puede tocar cualquier año. Se archiva primero en
  sus particiones históricas y después se aplica la retención normal al CSV;
  nunca se descarta por ser anterior a 180 días antes de quedar confirmado.
- Fallo de archivado: conservar pending, CSV y generación anterior; exit code 1
  y `all` no ejecuta mapas.
- Fallo solo de compactación después de commit: conservar CSV sin compactar,
  reportar estado degradado y permitir reintento; el histórico ya es válido.
- Fallo de un proveedor antes de producir lote: no tocar su partición ni crear
  ceros. Conservar el estado degradado de fuente y la política actual que
  permite mapas con la última generación válida cuando el exit code global sea
  2. Un fallo del archivador no es degradado de proveedor: es exit code 1.

## Contrato de lectura común

Crear una API única, sin lógica duplicada entre consumidores:

```python
resolve_weather_generation(data_dir) -> WeatherGeneration

pin_weather_generation(data_dir, generation_id=None) -> context manager

read_weather_history(
    data_dir,
    *,
    columns,
    sources=None,
    station_filter=None,
    start_date=None,
    end_date=None,
) -> pandas.DataFrame

iter_weather_history(..., batch_size=...) -> Iterator[pyarrow.RecordBatch]
```

Reglas:

- `read_weather_history` selecciona particiones por fuente/año antes de leer;
- una lectura interactiva exige rango de fechas y/o estaciones;
- una lectura completa solo se permite mediante `iter_weather_history`;
- `read_weather_history` mantiene el pin durante la lectura; los iteradores,
  snapshots y jobs largos deben usar explícitamente el context manager;
- identidad de caché: `(generation_id, manifest_sha256)`, no mtime ni tamaño
  agregado;
- la ruta normal valida siempre SHA de `CURRENT`/manifiesto y metadata de los
  objetos seleccionados. No recalcula los hashes de las 46 particiones en cada
  consulta: los objetos nuevos ya fueron verificados antes del commit y los
  heredados conservan su hash. Snapshot, restore, bootstrap y auditoría sí
  ejecutan validación exhaustiva; un servicio puede cachear una verificación
  por identidad de contenido, nunca solo por mtime;
- falta de `CURRENT`, hash incorrecto, partición ausente o schema incompatible
  son errores explícitos. No hay fallback silencioso a CSV vivos para
  Predictor histórico, reconstrucción o entrenamiento.

## Adaptación por consumidor

### Tomap/MapLibre

Tomap pide las columnas actuales y una ventana inclusiva de 90 días. El lector
abre como máximo los años intersectados de cada fuente. La agregación, los siete
Tomap, Last rains, GeoJSON y MapLibre no cambian. Se mantiene la prueba de
paridad de los ocho CSV frente a la ruta legacy.

No se añade por defecto un `weather_recent.parquet`: duplicaría estado y otro
commit. Solo se considerará como caché derivada reconstruible si el benchmark
demuestra que leer las particiones recientes no cumple el tiempo objetivo.

### Predictor

- Sustituir `weather_daily.parquet`/mtime por manifiesto/`generation_id`.
- Mantener filtros de estaciones y fechas.
- Hacer la selección de catálogo sensible a `first_date/last_date`.
- Una ventana entre diciembre y enero selecciona ambos años automáticamente.
- Las columnas de viento nuevas no modifican por sí solas el contrato ML.

### Reconstrucción y entrenamiento

`build_observation_weather_features()` no puede concatenar el histórico entero.
Debe precomputar las estaciones y ventanas necesarias a partir del catálogo y
las observaciones, o iterar batches y acumular solo los registros relevantes.
El entrenamiento continúa consumiendo features reconstruidas, no particiones
directamente. Debe demostrarse paridad de features antes/después.

### Catálogo

`generate_stations_catalog_parquet()` y `load_stations_catalog()` deben usar el
manifiesto. El catálogo forma parte de la generación; ya no se decide su
obsolescencia comparando dos mtimes.

### Snapshots y workers

- Subir la versión del manifiesto de snapshot.
- Congelar un `generation_id` y enumerar manifiesto, catálogo y particiones con
  tamaño/SHA.
- Reutilizar el mecanismo de caché persistente por contenido para descargar
  solo particiones nuevas; no copiar 100 MiB en cada job.
- `verify_snapshot()` valida todos los hashes y rechaza paths que escapen raíz.
- `materialize_ha_test_runtime()` debe copiar/materializar el dataset
  particionado; hoy solo copia CSV legacy incluso cuando el snapshot contiene
  Parquet.
- Mantener compatibilidad de lectura con snapshots legacy durante la migración,
  pero no producir nuevos snapshots parciales disfrazados de completos.

## Locking, limpieza, backup y disco

- `run.lock` serializa pipelines completos de actualización entre scheduler,
  CLI y web. Se adquiere antes de inspeccionar pending o tocar un CSV y se
  mantiene hasta cerrar el post-drain. Nunca se adquiere después de
  `writer.lock`.
- `fcntl.flock()` exclusivo sobre `writer.lock` evita escritores, backfills y
  GC concurrentes.
- Para crear o renovar un lease, el lector toma brevemente el mismo lock en
  modo compartido, resuelve `CURRENT` y publica el lease antes de soltarlo. La
  lectura larga ya no mantiene lock: usa los objetos inmutables fijados. Esto
  cierra la carrera resolver-generación/limpiar-partición.
- Conservar como mínimo las generaciones actual y anterior completas.
- Un lease contiene generación, PID/job, creación, renovación y expiración. La
  limpieza respeta todos los leases no expirados; un proceso largo los renueva
  y un crash queda recuperable por TTL. La creación/eliminación del lease
  también es atómica.
- No eliminar ficheros no referenciados inmediatamente. Usar un periodo de
  gracia superior a la duración máxima observada de snapshot/backup y nunca
  limpiar mientras haya un job que referencia esa generación.
- Antes de escribir, calcular espacio requerido para pending, nuevas
  particiones, catálogo y margen configurable. Si no cabe, fallar antes de
  crear temporales grandes.
- Hay dos preflights. Antes de descargar, la fuente exige un mínimo configurable
  para su chunk acotado, runs externos, pending y reemplazo atómico del CSV. Ya
  conocido el pending, el archivador calcula otro límite conservador con las
  particiones tocadas, output/row groups, catálogo, manifiesto y temporal del
  CSV. El margen libre reservado para HA no se considera utilizable.
- El tamaño de un lote y de cada run está acotado por configuración. Una fuente
  que exceda el presupuesto se parte en chunks transaccionales y ordenados; no
  se permite descubrir tarde que una ventana administrativa necesita un
  temporal ilimitado.
- La limpieza solo actúa bajo `weather-history/`, con paths resueltos y
  validados. Nunca usa globs destructivos sobre `Data/`.
- El backup de HA debe capturar `CURRENT`, manifiestos retenidos y todos sus
  ficheros. Los nombres inmutables y la gracia evitan que una copia en curso
  pierda una partición referenciada.
- Un backup de filesystem que no pueda coordinar locks podría capturar un
  `CURRENT` nuevo sin alguna partición recién creada si su recorrido ya pasó
  por `parts/`. Por ello el restore empieza con validación estricta. Una
  herramienta administrativa `repair-current-after-restore` puede enumerar
  manifiestos, verificar todos sus objetos y apuntar atómicamente a la
  generación completa más reciente. Esta recuperación es explícita y deja
  informe; la operación normal nunca hace ese fallback silenciosamente.
- La poda normal conserva `CURRENT`, su predecesora inmediata y todas las
  generaciones con lease. Si falta cualquier manifiesto que debería retener,
  falla antes de borrar nada; no interpreta la ausencia como permiso de poda.
- Una entrega compacta y autosuficiente que omita el historial de generaciones
  debe publicar una nueva raíz con `previous_generation_id: null`. El comando
  administrativo `python -m rainmapper_core.weather_history_rebase --data-dir
  <Data>` verifica íntegramente los objetos activos, escribe un manifiesto raíz
  nuevo y sustituye `CURRENT` atómicamente; no copia ni elimina objetos. Es
  idempotente cuando `CURRENT` ya es raíz.
- El rebase a raíz no es una reparación genérica ni debe debilitar la poda. Se
  usa únicamente cuando se ha auditado que la entrega pretende ser
  autosuficiente y contiene todos los objetos del manifiesto activo. Para una
  instalación que ya conserva esos objetos se copia primero el manifiesto y
  `CURRENT.json` al final.

## Bootstrap y migración

La migración no ocurre dentro del primer runner de producción y la generación
del laboratorio nunca se promueve directamente si HA ha seguido actualizando:

1. Verificar hashes de los cuatro CSV completos del último rebase validado. Para
   el corte actual son los de `rebase-trials/20260811T114432Z/candidate/` y suman
   5.025.368 filas. No mezclar snapshots de momentos distintos.
2. Construir por chunks una partición por fuente/año con schema completo.
3. Validar cada partición contra su CSV: claves, filas, nulls, valores, rango,
   estaciones y hash.
4. Construir catálogo e informe de conflictos de metadata.
5. Publicar la primera generación solo en el laboratorio.
6. Comparar con el Parquet antiguo en sus 14 columnas comunes y con los CSV en
   las columnas nuevas.
7. Probar lectores, Tomap, Predictor, reconstrucción, snapshots y fallos.
8. Preparar una release de compatibilidad con lector y escritor particionados
   detrás de feature flags. Antes de `CURRENT` continúa usando el contrato
   legacy; no puede empezar a escribir un histórico parcial por su cuenta.
9. En el corte autorizado, impedir temporalmente que el scheduled runner
   escriba, obtener y hashear una copia estable de los cuatro CSV reales de HA y
   registrar su fecha de corte. No basta con cuatro copias tomadas mientras el
   runner puede modificarlas.
10. Reconciliar esa copia fresca con la generación del laboratorio aplicando el
    mismo upsert no nulo y las mismas reglas de deduplicación; validar claves y
    rangos añadidos. Generar de este estado exacto los cuatro CSV vivos de 180
    fechas. Ninguna fila aparecida en HA después del snapshot inicial se pierde.
    La generación, ordenación y compactación inicial se ejecutan íntegramente en
    el M1. HA recibe en el cutover únicamente los cuatro candidatos ya reducidos
    y verificados; su primer runner particionado no procesa ni divide los CSV
    históricos completos.
11. Solo con autorización: backup/rollback, copiar las particiones/manifiesto
    reconciliados, activar `CURRENT`, sustituir conjuntamente las colas por sus
    candidatos compactados, habilitar el escritor particionado y verificar los
    consumidores antes de reanudar el scheduled runner.
12. Si la ventana no permite completar y verificar el corte, restaurar flags y
    reanudar el runner legacy; no dejar un modo híbrido que actualice CSV pero
    no el histórico activo.
13. Mantener temporalmente el monolítico y backups completos para rollback. Su
    eliminación es otra acción explícita posterior.

## Situación del código local actual

`rainmapper_core/weather_history.py` demuestra correctamente la semántica de
upsert no nulo y atomicidad de un único fichero, pero su escritor monolítico
superó el presupuesto de RAM. Se pueden reutilizar normalización y tests de
semántica; no se debe publicar:

- `upsert_weather_history_parquet()` como ruta operativa final;
- `update_weather_history_from_live_queues()` reaplicando cuatro colas;
- la llamada monolítica actual al final de `rainmapper.py`.

`generate_weather_daily_parquet()` queda como utilidad legacy/laboratorio, no
como paso normal del runner particionado.

## Orden de implementación para Sol-Medium

Estado 2026-08-12: fases A–C implementadas y validadas exclusivamente en el
laboratorio local. La fase E está integrada detrás del feature flag, pendiente
de la simulación completa y del gate arm64. La fase C dispone de contrato ligero, pending por sort
externo, merge de cursores/slices, catálogo, receipts, commit, fallos inyectados
y reparación post-restore. El benchmark `aemet/2024` selecciona 8.192 filas por
row group: 3,167 s, +48.398.336 bytes RSS y 166.313.984 bytes absolutos en Mac,
con salida de 2.006.676 bytes. El gate arm64/RPi4 sigue siendo obligatorio.
Nada se ha ejecutado, publicado ni promovido en HA.

### Fase A — Contratos y lector

1. Crear tipos de manifiesto y validadores en un módulo nuevo, sin modificar aún
   el runner.
2. Implementar `resolve_weather_generation`, selección fuente/año y lectores
   dataframe/batch.
3. Añadir fixtures de dos fuentes/dos años y pruebas de manifest corrupto,
   cambio de año, filtros, generación estable y path traversal.

### Fase B — Bootstrap local

4. Crear una herramienta dentro del audit lab que lea por chunks los cuatro CSV
   completos de un mismo rebase validado y produzca la
   generación inicial en una carpeta nueva mediante sort/merge externo. Los
   temporales se contabilizan, se reutilizan por hash y se eliminan únicamente
   después de verificar la salida.
5. No sobrescribir el candidato Parquet ni los CSV.
6. Emitir un JSON reproducible con hashes, memoria, tiempo y paridad por
   fuente/año.

### Fase C — Escritor y recuperación

7. Extraer schema, columnas, claves y tipos a un módulo de contrato ligero. El
   CLI del archivador no puede importar pandas, ni directa ni indirectamente;
   una prueba lo comprueba mediante `sys.modules`.
8. Implementar el constructor streaming de pending, incluidos runs externos,
   ordinal y fingerprint lógico reproducible.
9. Implementar el merge Arrow por cursores/slices, validación streaming, lock,
   catálogo incremental y commit de `CURRENT`, con inyección de fallos entre
   cada paso. No conectarlo todavía al runner.
10. Verificar idempotencia, receipts, correcciones, `NaN`, infinitos, altas,
   backfill antiguo, batch enorme, crash, dos escritores, lector concurrente,
   leases y no-op semántico. Un null normal nunca borra un valor histórico.
11. Medir en proceso limpio primero fixtures y después `aemet/2024`, con matriz
    8.192/4.096/2.048 y diccionarios acotados.
12. Implementar y probar `repair-current-after-restore` sobre backups
    artificialmente interrumpidos, sin habilitar GC destructivo.

### Fase D — Consumidores

13. Migrar Tomap y conservar la paridad de ocho productos.
14. Migrar catálogo/Predictor y sustituir mtime por `generation_id`.
15. Hacer streaming/bounded la reconstrucción ML y comprobar features.
16. Versionar snapshots/workers y su caché de particiones.

Estado local de la fase D:

- [x] Tomap selecciona por manifiesto únicamente la ventana inclusiva de 90
  días y conserva la ruta monolítica cuando el flag está apagado.
- [x] Predictor y catálogo usan `(generation_id, manifest_sha256)` como identidad
  de caché y leen solo estaciones/fechas acotadas.
- [x] La reconstrucción ML preselecciona estaciones del catálogo a ≤15 km de
  alguna observación y carga únicamente el intervalo global necesario de 120
  días; la lectura dataframe ilimitada queda rechazada.
- [x] Snapshot `0.2` congela `CURRENT`, manifiesto, catálogo y particiones con
  hashes, los verifica exhaustivamente y los materializa en runtimes/workers.
  Los snapshots legacy `0.1` siguen siendo aceptados.
- [x] Probados cruce 31-dic/1-ene, identidad de generación y transporte completo.
  La batería conjunta de consumidores/snapshots pasa 107 pruebas.

### Fase E — Runner y colas

17. Refactorizar cada fuente para exponer únicamente sus claves tocadas y crear
    el pending antes de escribir el CSV vivo.
18. Separar el wrapper en pre-drain, `update-sources`, archivador aislado y
    `maps`; retirar la llamada monolítica de `rainmapper.py`. Aplicarlo también
    a `update`/`once` y cerrar cada ventana del backfill mensual antes de abrir
    la siguiente. Añadir `run.lock` cross-process con timeout y orden de locks
    fijo antes de habilitar cualquier ruta.
19. Medir los CSV vivos reales de 180 fechas. Si el upsert pandas supera el gate
    end-to-end, sustituir lectura/upsert/compactación por merge CSV streaming.
    La salida conserva orden de columnas, formato decimal y deduplicación legacy
    acordados; se compara byte/lógicamente contra el resultado actual en
    fixtures y copias reales.
20. Implementar retención diaria, todavía desactivada por feature flag.
21. Simular un runner completo sobre copias locales y activar la retención solo
    después de verificar el histórico.

Estado local de la fase E:

- [x] Las cuatro fuentes capturan únicamente sus filas tocadas en un pending
  durable antes de modificar el CSV. AEMET conserva como lote sus siete fechas
  cerradas más la actual.
- [x] Con el feature flag activo, AEMET no lee, fusiona ni reescribe el CSV
  diario completo dentro del descargador; devuelve únicamente el lote reciente.
  Esto elimina el pico Mac medido de 468.615.168 bytes de la ruta pandas.
- [x] El archivador corre como proceso separado, actualiza primero la generación
  particionada, reaplica después el pending al CSV vivo mediante merge streaming
  y solo entonces confirma/elimina el pending.
- [x] `update`, `once`, `all`, la UI web y cada ventana mensual usan
  pre/post-drain y `run.lock` cross-process. El propietario web propaga al hijo
  que ya mantiene el lock y lo libera en `finally`, también ante excepciones.
- [x] El merge CSV conserva formato decimal legacy, orden, deduplicación no nula,
  permisos del fichero y retención inclusiva `T-179…T`; un CSV inicial no
  ordenado se rechaza sin sobrescribirlo.
- [x] El M1 generó candidatos ordenados reproducibles desde la generación
  canónica: 227.406 filas y 43.797.307 bytes en total. Dos ejecuciones produjeron
  los mismos SHA-256. Manifiesto:
  `docker-data/audits/mushroom-weather-backfill-20260811/reports/weather_live_csv_candidates.json`.
- [x] Añadido el preflight configurable anterior a las llamadas remotas y una
  única matriz probada de códigos 0/1/2 compartida por wrapper/UI.
- [x] Simulado el cierre transaccional de cuatro fuentes sobre copias locales:
  10,484 s, 175.013.888 bytes RSS absolutos, solo cuatro particiones `2026`
  modificadas, 227.406 filas vivas conservadas y cero pending al terminar. El
  delta de 113.901.568 bytes corresponde al proceso combinado que también crea
  pending; las mediciones aisladas son +48.398.336 bytes para writer y ~5 MiB
  para el merge CSV. Informe: `reports/weather_partitioned_cycle_simulation.json`.
- [ ] Ejecutar el gate equivalente en arm64/RPi4 y probar un runner completo
  únicamente cuando deje de estar prohibido para este laboratorio.

La creación inicial de particiones y colas compactadas pertenece al M1. No hay
ruta autorizada en la que la primera ejecución de HA ordene o divida los CSV
históricos completos.

## Pruebas y puertas de aceptación

### Correctitud

- cero pérdida de claves respecto a los cuatro candidatos;
- cero duplicados por clave canónica;
- paridad exacta de valores/nulls comunes y columnas nuevas desde CSV;
- `NaN` fresco conserva valor anterior;
- ausencia/error no crea fila ni lluvia cero;
- idempotencia de pending y de commit;
- solo cambian hashes de particiones realmente afectadas;
- el mismo lote produce el mismo `batch_id` y su reintento no crea generación;
- ventanas 90/120/150/180 que crucen el 31 de diciembre;
- siete Tomap + Last rains equivalentes;
- features actuales/históricas, gaps, fallback 15 km y estaciones excluidas
  equivalentes;
- snapshots reproducibles y workers capaces de reutilizar particiones.

### Fallos y concurrencia

- matar el proceso antes/después de cada escritura conserva `CURRENT` válido;
- un lector en bucle nunca observa mezcla de generaciones;
- dos escritores: uno espera/falla limpiamente, nunca escriben simultáneamente;
- scheduler, web y CLI simultáneos: solo uno obtiene `run.lock`; los demás
  esperan hasta el timeout o terminan como busy sin descargar ni tocar CSV;
- matar al propietario libera `run.lock`, y ninguna prueba invierte el orden
  `run.lock` → `writer.lock`;
- `update`, `once` y cada ventana del backfill drenan su lote; un fallo del
  archivador impide la ventana siguiente y `all` no ejecuta mapas;
- combinaciones de códigos fuente/archivador `0/1/2` producen el código final y
  la política de mapas especificados, sin ocultar un fallo de persistencia;
- partición, catálogo o manifiesto corrupto bloquean publicación;
- rollback consiste en cambiar `CURRENT` a una generación retenida y verificar;
- una simulación de corte incorpora deltas posteriores al snapshot inicial de
  HA y demuestra que no se pierde ninguna clave al compactar las colas;
- un backup interrumpido se rechaza y la reparación explícita selecciona la
  generación completa más reciente sin inventar ni modificar datos;

### Recursos RPi4

- el archivador se mide en un proceso limpio y separado, después de terminar
  `update-sources`; no se acepta una medición contaminada por el high-water mark
  de pandas del descargador;
- objetivo del archivador: incremento RSS `< 64 MiB` y RSS absoluto `< 192 MiB`;
- hard gate del archivador: incremento RSS `< 128 MiB` y RSS absoluto
  `< 256 MiB`; alcanzar cualquiera de esos límites rechaza la implementación;
- objetivo end-to-end de cada proceso normal del pipeline: RSS absoluto
  `< 256 MiB`; hard gate `< 384 MiB`. Descarga, CSV y compactación también se
  miden; separar procesos evita sumar sus picos, pero no los exime del gate;
- nunca cargar juntas las cuatro colas ni el histórico completo;
- escribir solo pending, catálogo y particiones tocadas;
- informar tiempo, RSS, bytes leídos/escritos y espacio temporal por fase;
- medir también el pico end-to-end de cada fuente —descarga, upsert CSV,
  pending, archivado y compactación—; cumplir el gate del archivador no basta
  para autorizar el runner completo;
- el RSS de macOS sirve para comparar implementaciones, pero el gate definitivo
  se valida en la arquitectura arm64/RPi4 o en un contenedor con límite de
  memoria representativo antes de cualquier release;
- medir además `memory.current`/pico del contenedor, `MemAvailable`, swap y
  major faults. Si no hay margen seguro antes de iniciar, aplazar el archivado;
- evidencia actual del Mac: importar pandas/PyArrow deja ~93 MiB RSS y recorrer
  `aemet/2024` por batches de 8.192 elevó el pico unos 25 MiB. Esto hace
  plausible el objetivo, pero no sustituye el gate arm64;
- importar solo PyArrow/Parquet dejó ~45 MiB RSS en la misma medición. El
  archivador debe aproximarse a ese baseline mediante el módulo de contrato
  ligero; “no usar pandas” incluye no importarlo accidentalmente;
- si una partición anual no cumple, subdividir únicamente esa fuente/año por
  bloques deterministas de estación. No volver al monolítico ni particionar por
  día/mes indiscriminadamente.

### Prohibiciones durante la implementación local

- no ejecutar el runner real;
- no escribir en HA;
- no promover CSV, Parquet, modelos ni versiones;
- no compactar/borrar los candidatos completos;
- no cambiar red/Tailscale;
- no usar fallback CSV silencioso para producir artefactos históricos;
- no limpiar ficheros versionados sin una prueba explícita de referencias.
