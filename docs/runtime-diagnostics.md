# Diagnóstico de memoria y rendimiento en Home Assistant

## Estado

Especificación e implementación incluidas desde `0.2.227`. Los ensayos A, B y C
cerraron el P0 de memoria para el escenario monousuario probado. `0.2.232`
refuerza la caja negra después de un bloqueo real del host durante un runner:
persiste heartbeats, identifica el arranque físico y acota la descarga AEMET.
`0.2.233` introduce el contrato diagnóstico `2.2`, con intervalos temporales
comparables para las cuatro fuentes meteorológicas.

## Objetivos

- Medir por separado el runner periódico y la carga fría del Predictor.
- Conservar los picos breves que las gráficas de Home Assistant pueden omitir.
- Confirmar que el proceso hijo del runner libera su memoria al terminar.
- Medir la memoria retenida por la caché compartida del Predictor.
- Evitar que el runner coincida con una petición del Predictor o con su caché
  meteorológica retenida.
- Producir un paquete descargable y seguro para análisis posterior.

## Persistencia y retención

Los eventos se escriben como JSON Lines en:

```text
/share/rainmapper/diagnostics/runtime_metrics.jsonl
```

El historial conserva como máximo 2.000 eventos y se compacta cuando supera
5 MiB. Cada línea es autocontenida. `0.2.232` escribe `schema_version=2.1` y
`0.2.233` escribe `2.2`. La escritura de diagnósticos nunca debe hacer fallar
una actualización o una predicción.

El paquete descargable contiene únicamente:

- `runtime_metrics.jsonl`;
- `runtime_summary.jsonl`;
- `runtime_anomalies.jsonl`;
- `runtime_state.json`;
- hasta 20 colas redactadas en `failed_operations/`;
- `last_run.log`;
- `manifest.json` con versión y fecha de exportación.

No incluye opciones, credenciales, observaciones, media, coordenadas privadas,
modelos ni históricos meteorológicos. Antes de añadir `last_run.log`, el
exportador conserva como máximo sus 2 MiB finales y oculta parámetros habituales
de credenciales y cabeceras Bearer.

## Métricas

Cada operación tiene un `operation_id`, un tipo y varias fases. Los snapshots
registran, cuando el sistema los expone:

- RSS actual y pico RSS del proceso;
- memoria actual, pico y límite del cgroup del add-on;
- `MemAvailable` del host;
- tiempo de CPU de usuario y sistema;
- CPU consumida como porcentaje equivalente de un núcleo durante la operación;
- temperatura de CPU;
- contadores `oom` y `oom_kill` del cgroup;
- tiempo de pared de la operación.

El coordinador `runner_action` mide toda la acción (`update`, `maps` o `all`) y
el consumo total del cgroup mientras viven sus procesos hijos. El proceso
`runner_update` añade fases antes del Parquet, después del Parquet, después del
catálogo y al finalizar; registra además filas, row groups y tamaños de los
artefactos. Tras acabar se guardan snapshots de recuperación a 60 y 600 segundos.

La carga física `predictor_weather_load` registra número de estaciones,
registros y tamaño del filtro. También conserva snapshots a 60 y 600 segundos
para observar la caché retenida. Las visitas que reutilizan la misma caché no
duplican una supuesta carga fría.

`predictor_weather_load` mide únicamente la lectura y materialización del
Parquet meteorológico compartido. No mide la latencia completa desde el clic en
el panel hasta que el navegador muestra la página: quedan fuera del monitor el
resto de `render_page()`, los cálculos de la vista, la generación/envío del HTML,
HA Ingress y el renderizado del navegador. El tiempo extremo a extremo debe
registrarse por separado hasta que exista instrumentación de la petición
completa.

### Ventana meteorológica temporal del Predictor (`0.2.229`)

La ruta normal ya no conserva todas las fechas de las estaciones espaciales
seleccionadas. Mantiene una sola ventana sustituible de 96 días:

- 90 días hasta la fecha objetivo, necesarios para la cobertura y las features
  existentes;
- 6 días posteriores precargados, de modo que los siete días de la pantalla
  semanal reutilizan una única lectura;
- filtros `local_date` inclusivos enviados junto a fuente/estación al lector
  Parquet, antes de construir objetos Python.

Predicción, Especies y una consulta de Fechas dentro de la semana actual
comparten esa ventana. Una fecha histórica fuera de ella se carga bajo demanda y
sustituye la anterior; volver a una vista actual vuelve a cargar los 96 días y
vacía explícitamente el diccionario antiguo para que otras instancias cacheadas
no retengan sus registros.

Historial es deliberadamente distinto: necesita evaluar episodios separados por
años. Calcula el intervalo mínimo entre el primer y último episodio, incluido el
lookback, y lo carga una sola vez para evitar una lectura de Parquet por episodio.
Ese intervalo amplio no se acumula: la siguiente vista actual lo sustituye por
la ventana de 96 días.

En el Ensayo B se materializaron 79.931 registros de 115 estaciones. Con esas
mismas estaciones, una ventana de 96 días tiene un máximo teórico de 11.040
registros, el 13,8 % (unas 7,2 veces menos objetos meteorológicos); faltantes y
estaciones con menor cobertura pueden reducirlo más. Es una estimación de
objetos retenidos, no una promesa equivalente de latencia o RSS: Arrow aún puede
leer row groups parcialmente y las vistas también calculan modelos y HTML.

`predictor_weather_load` v2 registra `window_start`, `window_end`, `window_days`
y `loaded_record_count`. La validación en RPi4 debe comparar una apertura fría,
navegación semanal caliente, una fecha histórica y el regreso a la semana
actual, comprobando tanto tiempos como memoria retenida.

## Cadencia de muestreo y espera de recuperación

La espera de 10 minutos no significa que el sistema escriba métricas de forma
continua durante todo ese periodo. El ciclo exacto es:

1. Al comenzar una operación se guarda un snapshot inicial.
2. Mientras el runner o una operación Predictor siguen activos, se toma una
   muestra cada 0,5 segundos. Estas muestras se agregan en memoria para conservar
   máximos y mínimos. Desde `0.2.232`, cada 10 segundos se persiste y sincroniza
   físicamente un `heartbeat` con la muestra actual y los extremos acumulados;
   un corte abrupto deja como máximo aproximadamente 10 segundos sin evidencia.
3. Las fases relevantes escriben eventos puntuales y, al terminar la operación,
   se detiene inmediatamente el muestreo periódico y se guarda el resumen.
4. Después del final solo se programan dos fotografías puntuales del sistema:
   una a los 60 segundos y otra a los 600 segundos. No existe muestreo continuo
   entre ambas.

El snapshot de 600 segundos permite comprobar si memoria, CPU y temperatura se
han recuperado, o cuánta memoria conserva la caché del Predictor. Para que se
escriba, el add-on debe continuar en ejecución: no reiniciarlo ni detenerlo
durante esos 10 minutos. No es necesario mantener abierta ninguna pantalla.

Una vez guardado `recovery_600s` o `retained_600s`, el registro permanece en
`/share/rainmapper/diagnostics/runtime_metrics.jsonl` hasta su compactación
acotada. El ZIP se puede descargar más tarde; no hay una ventana de descarga de
solo 10 minutos. Conviene esperar unos segundos adicionales tras los 10 minutos
antes de pulsar **Download diagnostics**.

## Evolución v2 publicada en `0.2.229` después de A–C

La implementación posterior a `0.2.228` mantuvo el JSONL v1 compatible y añadió
el contrato `schema_version: 2.0` en `0.2.229`. La prueba real está completada.
`0.2.232` amplía el contrato compatible a `2.1` con heartbeat y datos del host.

La evolución local posterior amplía el contrato a `2.2` sin reescribir ni
eliminar diagnósticos anteriores. La versión del esquema funciona como una
capacidad, no como un filtro de admisión:

- `2.1` y anteriores conservan métricas, estado, recursos y comparación A/B,
  pero la UI los identifica como **limited detail**;
- `2.2` añade `source_phase_intervals` para situar con inicio y fin reales las
  fases de AEMET, Meteoclimatic, Meteocat y Wunderground;
- el dashboard nunca infiere intervalos ausentes ni atribuye eventos de AEMET a
  otra fuente para completar un histórico antiguo;
- no hay que borrar `/share/rainmapper/diagnostics` al instalar `0.2.233`:
  mezclar ejecuciones 2.1 y 2.2 es el comportamiento previsto y permite
  comparar el antes y el después.

### Intervalos de las fuentes en el esquema 2.2

Cada medición interna de una fuente registra un evento inmediato
`source_phase_start` y, si termina, un `source_phase_complete`. El inicio deja
evidencia incluso si el host se interrumpe a mitad de la fase. Los intervalos
completos se copian además en el resumen compacto de la fuente con `source`,
`phase`, `phase_id`, `started_at`, `finished_at` y `duration_seconds`; por tanto,
el Gantt sobrevive a la rotación del JSONL de detalle mientras sobreviva el
resumen de la ejecución.

Los timestamps nuevos usan UTC ISO 8601 con sufijo `Z` y milisegundos. Así se
alinean rigurosamente con el inicio global de la operación aunque Home Assistant
use `Europe/Madrid` o cambie entre horario de invierno y verano.

La granularidad sigue las fases reales ya existentes en cada implementación,
no una lista artificial idéntica para todas:

- AEMET: petición/descarga, decodificación, parseo y normalización expuestas por
  su callback, además de las fases globales de Parquet y catálogo;
- Meteoclimatic: descarga/parseo, histórico incremental, lectura y escrituras;
- Meteocat: metadatos, condiciones, viento, precipitación, merge, incremental y
  escrituras;
- Wunderground: metadatos, scraping/API/fallback, merge incremental, lectura y
  escrituras.

Las cuatro fuentes se ejecutan en paralelo cuando la configuración lo permite.
Por eso sus intervalos conservan timestamps absolutos y luego se proyectan sobre
un eje transcurrido común; no se reconstruye el orden sumando duraciones.

### Medición correlacionada del Predictor

Cada apertura genera un `operation_id` de `predictor_request` y estas fases del
servidor:

1. `start` y `lock_acquired`;
2. `inputs_loaded` para perfiles y setales;
3. `predictor_render_started` y `body_rendered` para la vista;
4. `html_generated`;
5. `response_sent` y `finish`.

Una carga de modelo nueva crea una operación hija `predictor_model_load`. La
carga física del Parquet conserva `predictor_weather_load` y hereda el padre:
ambas quedan como suboperaciones de la petición completa. Cada petición
indica `cold_request` y el número de instancias ya cacheadas, pero no el ID de la
especie. Así se pueden restar las suboperaciones y distinguir entrada, modelos,
meteorología, cálculo/render del servidor y envío.

En ejecución remota, `cold_request` procede siempre del resultado autoritativo
del worker, no de la caché local de HA. El resumen también conserva
`runtime_cache_status`, bytes sincronizados, tiempo backend y versión del
worker. Esto importa porque «runtime reutilizado» y «Predictor caliente» no son
sinónimos: el runtime puede estar ya descargado y aun así el proceso tener que
cargar modelos o datos por primera vez.

Desde la corrección posterior a `0.2.237`, el resumen conserva además
`worker_response_cache_status` (`hit` o `miss`). Un runtime `reused` solo dice
que no se retransmitieron artefactos; un `hit` indica que la misma consulta ya
tenía una respuesta calculada dentro del runtime inmutable del worker.

Al terminar `load`, el navegador envía una única operación
`predictor_client_render` con Navigation Timing: inicio/fin de respuesta, DOM
interactive, DOMContentLoaded, load y tamaños transferidos. El endpoint solo
acepta campos numéricos predefinidos y un `operation_id` reciente creado por el
servidor. No recibe especie, área, ubicación ni predicción.

`load_event_ms` empieza cuando el navegador inicia la navegación dentro de
Ingress. No puede medir el tiempo anterior que Home Assistant tarde en crear o
mostrar el iframe después del clic. La comparación queda así:

- `predictor_request.wall_seconds`: RPi4 hasta terminar de escribir la respuesta;
- `response_start_ms`/`response_end_ms`: servidor + Ingress/red vistos por el
  navegador;
- `load_event_ms`: navegación y renderizado completos dentro del iframe;
- diferencia respecto al cronómetro manual desde el clic: trabajo previo de la
  interfaz de Home Assistant que el iframe no puede observar.

### Caja negra persistente

Todos los artefactos viven bajo `/share/rainmapper/diagnostics` y sobreviven a
reinicios, actualizaciones y backups normales de los datos del add-on:

- `runtime_metrics.jsonl`: detalle circular, máximo 2.000 eventos o 5 MiB;
- `runtime_summary.jsonl`: histórico acotado, máximo 20.000 resúmenes o 20 MiB;
- `runtime_anomalies.jsonl`: errores, degradaciones, interrupciones y nuevos OOM,
  máximo 5.000 registros o 10 MiB;
- `runtime_state.json`: escritura atómica del boot actual, operaciones y
  snapshots pendientes;
- `failed_operations/`: hasta 20 colas de log fallidas, redactadas y limitadas a
  los últimos 2 MiB cada una.

El muestreo de recursos continúa cada 0,5 s en memoria, pero `0.2.232` persiste
un heartbeat cada 10 s con los máximos/mínimos acumulados. Al cerrar una
operación se guardan además las fases relevantes y el resumen. Los snapshots de
60 y 600 s se registran en `runtime_state.json`; si el proceso reinicia antes de
capturarlos, se conservan como `snapshot_interrupted` en vez de desaparecer.

El arranque genera un `boot_id`, registra inicio/parada y reconcilia cualquier
operación pendiente como `interrupted`. No atribuye OOM sin evidencia: usa
`oom_attribution: unknown`; un OOM solo se marca cuando los contadores del cgroup
aumentan durante la operación. Un cierre escrito justo antes de morir no se
duplica como interrupción porque la reconciliación comprueba los resúmenes y
fases recientes.

Desde `0.2.232`, cada snapshot incorpora también el boot ID real del kernel y el
uptime del host. Al reconciliar un `runner_action` pendiente, se archiva de forma
redactada su `last_run.log` antes de que una ejecución posterior pueda
sobrescribirlo.

El ZIP añade resumen, anomalías, estado y logs fallidos al detalle y
`last_run.log` existentes. Su lectura de estado está cacheada por tamaño/mtime
para no releer el histórico en cada polling.

### Pestaña Diagnostics e histórico comparable

Esta sección es la especificación canónica de diseño, persistencia y operación
de la pestaña Diagnostics. No se mantiene un segundo documento de diseño para
evitar que retención, filtros y semántica de comparación diverjan.

`0.2.233` mueve **Runtime black box** fuera de Summary y crea una pestaña
**Diagnostics**. Summary conserva únicamente el estado operativo habitual. La
nueva pestaña ofrece:

- estado vivo: último éxito, fallo/interrupción, OOM, pico reciente del cgroup y
  operaciones pendientes;
- selectores **Execution A · baseline** y **Execution B · candidate**,
  inicialmente configurados con la ejecución anterior y la última del mismo
  tipo;
- comparación de duración, RSS, cgroup, memoria disponible del host,
  temperatura, CPU, OOM y recuperación a 60/600 segundos;
- deltas absolutos y porcentuales calculados como `B - A`, y porcentaje respecto
  a A. Menos duración, memoria o temperatura es mejor; más `MemAvailable` es
  mejor;
- valoración textual separada: `B is better`, `A is better`, `No change` o
  `Not assessed`. El color de la diferencia conserva la lectura rápida, pero no
  es necesario inferir por el signo qué ejecución resulta favorable;
- aviso cuando se comparan tipos, acciones del runner o vistas del Predictor no
  equivalentes;
- histórico reciente con fecha local, tipo, versión, estado y recursos;
- Gantt de fases y detalle de las cuatro fuentes: AEMET, Meteoclimatic, Meteocat
  y Wunderground. Cada fuente aparece plegada como una barra global y se puede
  desplegar independientemente para ver sus subfases. A y B comparten un eje X
  de tiempo transcurrido desde el inicio basado en la ventana más larga, con
  marcas y rejilla; por tanto, posiciones y longitudes se pueden comparar
  directamente. El pie distingue **Operational duration**, que termina cuando
  acaba el trabajo, de **Diagnostic window**, que puede prolongarse por las
  muestras de recuperación a 60 y 600 segundos;
- tabla de medias separadas de Runner y Predictor para las cinco versiones más
  recientes, con muestras, ejecuciones correctas, anomalías, duración, memoria,
  temperatura y `MemAvailable`.

La selección representa ejecuciones reconstruidas desde los JSONL persistentes,
no ficheros ZIP individuales. Descargar un ZIP sigue siendo una exportación bajo
demanda del conjunto de evidencias. Las selecciones A/B se conservan en
`sessionStorage` y sobreviven al refresco automático del panel cada cinco
segundos.

La tabla visible conserva las 20 ejecuciones más recientes dentro de un área con
cabecera fija, altura de 10 filas y scroll interno para las otras 10. Los
selectores A/B pueden usar hasta las 500 ejecuciones reconstruibles más
recientes; siete días no es ya un límite de diseño. Los eventos detallados
pueden rotar antes que sus resúmenes, en cuyo caso la comparación numérica sigue
siendo válida y la UI indica que no conserva fases suficientes para el Gantt.

La sección **Evolution** tiene dos modos:

- **Timeline**, con ventanas seleccionables de 7, 30, 90 días o todo lo aún
  retenido en `runtime_summary.jsonl`. Dibuja cada versión/carga como serie
  separada y permite elegir duración, cgroup, RSS, `MemAvailable`, temperatura
  o CPU.
- **By version**, para las cinco versiones más recientes. Representa la media y
  el rango mínimo-máximo de cada métrica, con el número de muestras en el punto.

Ambos modos filtran por Runner/Predictor y por carga comparable. Runner y
Predictor nunca se mezclan en una misma serie o media porque representan cargas
distintas; tampoco se fusionan acciones `all`/`update`/`maps` ni vistas del
Predictor con carga fría/caliente. Elegir «All» muestra líneas independientes,
no una media conjunta.

**Version averages** se organiza como `Type → Comparable workload → Version`.
Esta jerarquía impide comparar accidentalmente cargas distintas: `Runner · all`
queda abierto inicialmente y cada carga fría/caliente o vista del Predictor se
despliega por separado para mostrar sus versiones. Los acordeones conservan su
estado durante el refresco periódico del panel.

Las duraciones de Diagnostics se presentan en segundos cuando son inferiores a
un minuto y como `m:ss` cuando alcanzan un minuto. Las décimas se conservan en
comparaciones y detalles (`5:05.4`), mientras que el eje y la ventana temporal
usan segundos enteros (`5:05`). Este formato solo afecta a la presentación: los
JSONL siguen almacenando segundos numéricos y los históricos no se migran.

Los resúmenes compactos siguen bajo el límite circular de 20.000 registros/20
MiB. Las agregaciones por versión se calculan al leer el histórico y se cachean
por tamaño/mtime; no crean otro fichero ni añaden trabajo al runner. Las series
temporales también son compactas: excluyen fases, snapshots, hijos y el desglose
de fuentes. La opción «All retained» puede transferir más datos y por eso solo
se solicita explícitamente al seleccionarla.

El histórico se carga de forma diferida mediante
`/api/diagnostics/history?period=7|30|90|all` únicamente al abrir la pestaña
Diagnostics o cambiar la ventana temporal. El navegador reutiliza durante 60
segundos el periodo activo. Por tanto, el polling normal de Summary cada cinco
segundos no transporta ni vuelve a serializar el histórico.

Los topes teóricos de los tres JSONL estructurados suman 35 MiB: 5 MiB de
detalle, 20 MiB de resúmenes y 10 MiB de anomalías. Los logs fallidos tienen un
tope separado de 20 colas de hasta 2 MiB. En funcionamiento normal ocupan mucho
menos y son pequeños frente a los históricos meteorológicos o la carpeta de
media. El coste de las medias se produce al abrir/refrescar Diagnostics después
de cambiar un resumen, no durante cada heartbeat ni durante el procesamiento de
las fuentes.

### Prueba local con un ZIP descargado de HA

`rainmapper-ha-ui` monta `docker-data/` como `/share/rainmapper`, por lo que se
puede validar la interfaz con una copia de la caja negra real sin conectarse a
HA durante la prueba:

1. Descargar **Download diagnostics** en HA. Si macOS lo descomprime
   automáticamente, puede usarse la carpeta resultante; si se vuelve a comprimir
   con Finder, ignorar `__MACOSX/` y `.DS_Store`.
2. Conservar aparte cualquier `docker-data/diagnostics` local existente.
3. Copiar solamente `runtime_metrics.jsonl`, `runtime_summary.jsonl` y
   `runtime_anomalies.jsonl` a `docker-data/diagnostics/`.
4. No importar `runtime_state.json`: pertenece al boot real de HA y el entorno
   local podría reconciliar falsamente operaciones o snapshots pendientes.
5. Arrancar `./mushroom_lab_start.sh` y abrir
   `http://127.0.0.1:8101/#tab-diagnostics`.
6. Comprobar que cambiar A o B actualiza inmediatamente cabeceras, tabla y
   Gantt, y que la selección sobrevive al refresco.
7. Alternar Timeline entre 7/30/90 días y todo lo retenido; después cambiar a By
   version y verificar media/rango para una misma carga comparable.
8. Con un runner `2.2`, desplegar por separado las cuatro fuentes en ambos Gantt
   y en **Source and phase detail**. Comprobar que cada subfase queda dentro de
   la barra de su fuente y que A/B usa la misma escala.
9. Seleccionar como A un runner `2.1` y como B uno `2.2`. Las métricas deben
   seguir comparándose; A debe indicar **limited detail** y B **full source
   detail**, sin fases inventadas para A.

`manifest.json`, `last_run.log` y `failed_operations/` no son necesarios para
probar esta pantalla. Siguen siendo útiles para un análisis manual de incidentes.

El resumen compacto es la autoridad para comparaciones antiguas. Las fases se
añaden mientras sigan en la retención corta de `runtime_metrics.jsonl`; cuando
han rotado, la UI lo indica sin invalidar las métricas finales. Desde esta
evolución, `runner_action` pasa explícitamente su ID al proceso hijo
`runner_update`, que guarda en su resumen estado, filas, estaciones, duración y
timings internos de todas las fuentes. De este modo una ejecución `all` puede
agrupar la actualización hija y conservar la comparación multifuente incluso
después de rotar los eventos detallados. Los runners anteriores continúan
visibles, aunque pueden carecer de ese desglose.

Dentro de **Source and phase detail**, los resúmenes de AEMET, Meteoclimatic,
Meteocat y Wunderground son acordeones independientes y los eventos conservados
de la operación forman otro bloque independiente. Estos últimos nunca se
atribuyen a Wunderground por ser la última fuente presentada; las versiones
antiguas pueden contener eventos granulares únicamente de AEMET. En un
diagnóstico `2.2`, cada acordeón enseña sus intervalos retenidos; en un `2.1`,
el bloque conserva duraciones agregadas y declara explícitamente la limitación.

Los ficheros técnicos mantienen timestamps UTC con `Z` y milisegundos para poder
correlacionar eventos. La presentación del Control Panel los convierte a la zona
`RAINMAPPER_TIMEZONE` y al ISO local de las tarjetas Summary, con offset y
precisión de segundos. Como excepción deliberada, los extremos del eje de la
gráfica usan el formato regional del navegador, más breve para lectura visual.
Esta homogeneización de UI se implementó después de validar `0.2.232` y quedó
incluida en `0.2.233` junto con el resto de la ampliación diagnóstica.

La retención no es literalmente infinita. Descargar el ZIP o incluir `/share` en
un backup permite sacar el histórico del dispositivo; el detalle reciente rota,
pero los límites del resumen cubren más de un año del runner cada tres horas aun
contando sus snapshots, antes de hacer backups externos.

### Procedimiento de validación de la v2 en HA real

1. Instalar la release que incluya la v2 y comprobar en el panel que aparece
   **Runtime black box** sin operaciones pendientes inesperadas.
2. Tras un reinicio o un runner, abrir Predictor una vez en frío y anotar también
   el cronómetro manual desde el clic.
3. Abrir la misma vista una segunda vez para obtener una petición caliente.
4. Descargar el ZIP: las métricas de petición y cliente llegan inmediatamente.
   Esperar 10 minutos solo si se quieren incluir también los snapshots de
   retención/recuperación a 600 s.
5. Comparar por `operation_id` `predictor_request`, `predictor_model_load`,
   `predictor_weather_load` y `predictor_client_render`.
6. Reiniciar el add-on durante una prueba controlada y descargar otro ZIP para
   verificar `runtime_boot`, `interrupted` y `snapshot_interrupted`.
7. Confirmar que ninguna entrada contiene especie, setal, coordenadas,
   resultados, credenciales ni tokens.

Para validar específicamente un worker después de actualizar HA no hace falta
regenerar features ni reentrenar modelos. La primera apertura, si cambia el
runtime/fingerprint o no hay instancias cargadas, debe aparecer bajo la carga
comparable `recommender · cold`; repetir inmediatamente la misma apertura debe
aparecer como `recommender · warm`. Confirmar además que la primera conserva el
estado de sincronización y los bytes transferidos/reutilizados. Borrar cachés a
mano queda reservado a pruebas controladas: no forma parte del procedimiento
normal y nunca debe afectar GIS/DEM ni artefactos ML autoritativos.

### Resultado real de Predictor v2 en `0.2.229`

El usuario instaló `0.2.229`, recorrió Recomendador, Semana, Fechas e Historial
y exportó `rainmapper-diagnostics-20260808T020109Z.zip` a las 02:01:09 UTC
(SHA-256
`a4ecb8b8fc4d55639d9fab515e0387bb3f0eec14e4cdae7bc7f5b85d6e53844f`).
El ZIP contiene 20 peticiones Predictor correctas, ninguna anomalía, ningún OOM
y ningún snapshot u operación pendiente.

- La primera petición fría tardó 36,622 s en el servidor: las cuatro cargas de
  modelo sumaron aproximadamente 5,4 s, la ventana meteorológica 10,175 s y
  quedaron unos 21 s de predicción y render del servidor.
- Recomendador caliente tardó 4,947–5,187 s; Semana 6,681–13,261 s; una consulta
  con ventana ya cargada 0,989–1,941 s; cambiar la ventana histórica
  11,447–12,763 s; Historial caliente 3,45–6,181 s.
- La vista normal materializó 7.728 registros de 101 estaciones en 96 días,
  frente a los 79.931 registros de la carga anterior a la optimización. Las
  consultas históricas sustituyeron esa ventana; Historial llegó a 59.286
  registros y 3.402 días sin cargar el Parquet completo.
- El proceso pasó de 138,7 MiB RSS antes de la apertura a 299,6 MiB al terminar
  la petición fría. Tras recorrer rangos e Historial alcanzó 420,1 MiB RSS;
  máximo del cgroup 576,3 MiB, mínimo `MemAvailable` 1.793,6 MiB y temperatura
  máxima 51,61 °C. A 600 s permanecía estable/decreciente, alrededor de
  395,8 MiB RSS y 523,4 MiB de cgroup.

No apareció ninguna operación `predictor_client_render`. El diagnóstico mostró
que `../../diagnostics/predictor-client`, resuelta desde
`/api/hassio_ingress/<token>/mushrooms/predictor`, eliminaba también el segmento
`<token>` y enviaba el POST fuera del Ingress del add-on. `0.2.231` cambia la
referencia a `../diagnostics/predictor-client` y añade una regresión que resuelve
la URL tanto con prefijo HA Ingress como en acceso directo. Hasta validar esa
release, los tiempos anteriores son del servidor y no permiten separar todavía
Ingress/red/render del navegador.

### Incidente real de runner en `0.2.229` y refuerzo `0.2.232`

El runner programado `all` del 2026-08-08 comenzó a las 05:00:04 CEST. Liberó
cuatro instancias Predictor y entró en `runner_update`; la última línea de
`last_run.log`, a las 05:00:15, fue el inicio de la descarga de la URL de datos
de observaciones AEMET. Home Assistant dejó de responder y el usuario cortó
manualmente la alimentación aproximadamente a las 05:17.

Evidencia conservada:

- `rainmapper-diagnostics-20260808T032011Z.zip`, SHA-256
  `5121ba95e49bfd84ab2a3d435e8959d9b74ccf57ea606b52babee90b068dd9b2`;
- `supervisor_2026-08-08T03-29-11.092Z.log`, SHA-256
  `5d41153074b32fd6257cadd5893eda22b981420737f0a5728ee2ed1ec33a8bbf`.

Al comenzar había 1.434 MiB de `MemAvailable`, 488 MiB de cgroup, 46,74 °C y
contadores OOM a cero. Supervisor completó sus comprobaciones todavía a las
05:13:40. El arranque posterior y los códigos 255 simultáneos de todos los
add-ons corresponden al corte manual, no a una decisión automática de
Supervisor. No existe evidencia suficiente para atribuir el bloqueo a OOM,
temperatura, red, CPU o I/O: `0.2.229` acumulaba las muestras de 0,5 s solo en
memoria y no llegó a consolidar el resumen antes del corte.

`0.2.232` cierra ese hueco diagnóstico:

- `OperationMonitor` escribe y hace `fsync` de un heartbeat cada 10 s durante
  runner y Predictor, con muestra actual, extremos acumulados, boot ID del
  kernel y uptime del host;
- la secuencia completa AEMET (índice, espera y datos) tiene un deadline global
  de 90 s, además del timeout de socket, y ajusta el timeout restante durante la
  lectura por bloques;
- AEMET registra inicio/fin de descarga, decodificación, parseo y normalización,
  con tamaños, filas y tiempos pero sin URL ni credenciales;
- al reiniciar, una acción runner pendiente archiva automáticamente el log
  parcial redactado en `failed_operations/` antes de que otro runner lo
  sobrescriba.

Para repetir la prueba: instalar `0.2.232`, esperar a que el estado quede
estable, lanzar manualmente `all` y no abrir Predictor. Si vuelve a dejar de
responder, anotar la hora exacta; esperar solo mientras el sistema siga
accesible y cortar alimentación únicamente si es imprescindible. Tras el
arranque, descargar el ZIP antes de otra ejecución. Los heartbeats y el log
archivado sobrevivirán aunque haya comenzado un runner posterior.

### Validación real de `0.2.232` tras el incidente

El usuario instaló `0.2.232` y lanzó manualmente `all` el 2026-08-08 a las
06:25:31 CEST sin abrir el Predictor. La ejecución terminó correctamente a las
06:31:46, en 6:15 y con código 0. El ZIP esperado tras el snapshot de 600 s fue
`rainmapper-diagnostics-20260808T044217Z.zip`, SHA-256
`932ee6a28aeeb633f41355b1fc8c0654433e722203257bc7e1da8f4365ee4907`.

Resultados:

- actualización 4:53, mapas 58 s y publicación protegida completada;
- pico cgroup 1.445,4 MiB; pico RSS del hijo de actualización 1.238,0 MiB;
- mínimo `MemAvailable` 822,6 MiB y temperatura máxima 54,5 °C;
- cero OOM, OOM-kill, errores, degradaciones, reinicios o anomalías nuevas;
- recuperación a 60 s: cgroup 634,8 MiB y 2.096,1 MiB disponibles;
- recuperación a 600 s: cgroup 185,2 MiB y 2.007,8 MiB disponibles;
- estado final sin operaciones ni snapshots pendientes.

La nueva evidencia persistente quedó validada: 37 heartbeats del
`runner_action` y 27 del `runner_update`, con separación máxima de 11,9 s y sin
huecos. AEMET registró todas las fases previstas: descargó el índice en 0,33 s y
3,25 MB de datos en 0,62 s, parseó 9.754 registros y normalizó 9.459. Su updater
completo tardó 106,2 s por lectura, combinación y escritura del histórico; el
deadline de 90 s corresponde a la secuencia de red/decodificación/parseo, no al
procesamiento posterior. La caja negra `2.1` queda validada en HA real.

## Exclusión runner/Predictor

- Una petición del Predictor mantiene un lock durante su renderizado.
- El runner espera a que termine esa petición antes de arrancar.
- Al arrancar cualquier acción del runner se liberan las instancias y la caché
  meteorológica del Predictor.
- Mientras `RUN_STATE.running` sea verdadero, Predictor muestra un aviso y no
  inicia cálculos.
- Al terminar el runner, la siguiente consulta crea una caché nueva contra el
  Parquet vigente.

Esto garantiza la exclusión en el servidor; no depende de que el usuario mire
el schedule o cierre una pestaña en un momento concreto.

## Uso sin vigilancia manual

Los registros se crean solos tanto para ejecuciones manuales como programadas.
No es necesario mantener abierta la pantalla de Home Assistant ni observar sus
gráficas. Una vez terminada la prueba y transcurridos los 10 minutos de
recuperación, abrir el panel de Rainmapper y pulsar **Download diagnostics** en
la pestaña **Diagnostics**. El ZIP resultante se puede guardar y compartir para
analizarlo posteriormente.

## Procedimiento de validación en RPi4

### Ensayo A — runner real

1. Instalar la release corregida sin abrir Predictor.
2. Reiniciar el add-on y esperar 10 minutos para estabilizar el estado base.
3. Ejecutar manualmente la misma acción usada por el schedule, normalmente
   `all`.
4. Esperar a que termine; no es necesario vigilar la ejecución.
5. Dejar después 10 minutos de reposo para que se escriba `recovery_600s`.
6. Descargar el paquete con **Download diagnostics** desde el panel.
7. Verificar duración de `update` y `maps`, pico RSS, mínimo `MemAvailable`,
   temperatura, eventos OOM y retorno de memoria tras finalizar.

### Ensayo B — Predictor monousuario

1. Reiniciar el add-on conservando el Parquet generado en el ensayo A.
2. Esperar 10 minutos sin abrir Predictor.
3. Abrir la vista predeterminada y esperar a que finalice la carga fría.
4. Visitar Por especie, Consultar fecha e Historial y realizar varias consultas
   representativas.
5. No lanzar manualmente el runner durante este ensayo; el servidor bloqueará
   igualmente cualquier coincidencia accidental.
6. Cerrar o abandonar la vista y esperar al menos 10 minutos para capturar
   `retained_600s`; no es necesario mantener la pantalla abierta.
7. Descargar un segundo paquete de diagnóstico.

### Ensayo C — exclusión automática

1. Después de haber usado Predictor, lanzar `update` o esperar al siguiente
   schedule.
2. Comprobar que Predictor muestra el aviso de runner activo.
3. Confirmar en el diagnóstico que la caché se liberó antes del proceso hijo y
   que no hubo `oom_kill`.

## Resultado real — Ensayo A en RPi4 (`0.2.227`)

El primer paquete real se exportó el 2026-08-08, después de una ejecución
programada `all` iniciada a las 00:09:55 y finalizada correctamente a las
00:16:57 (hora local). Resultado:

- duración total: 421,3 s (7 min 2 s); `update`: 343,4 s y `maps`: 56,2 s;
- exit code 0, sin reinicios, `oom=0` y `oom_kill=0`;
- pico RSS del proceso hijo: 1.222,5 MiB; pico RSS histórico: 1.243,6 MiB;
- máximo observado del cgroup: 1.334,0 MiB y pico del cgroup: 1.347,8 MiB;
- mínimo `MemAvailable` del host: 670,0 MiB;
- temperatura máxima: 52,58 °C;
- Parquet: 625.529 filas, 1.222 row groups, 12,0 MiB y 28,2 s de generación;
- catálogo: generado correctamente, 79,3 KiB;
- Wunderground: 98/98 estaciones, cero fallos y cero errores de fallback;
- AEMET, Meteoclimatic, Meteocat, Tomap, GeoJSON y publicación MapLibre
  finalizaron correctamente.

La memoria del proceso hijo se liberó al terminar `update`: el cgroup bajó de
aproximadamente 999 MiB a 211 MiB y `MemAvailable` subió de 1.332 MiB a
2.108 MiB. En `recovery_60s` se observaron 495 MiB de cgroup, 34,6 MiB de RSS
del servidor y 2.123 MiB disponibles en el host; en `recovery_600s`, 510 MiB,
49,8 MiB y 2.027 MiB respectivamente. El cgroup quedó por encima de su lectura
inicial de 247 MiB, pero el RSS del servidor quedó muy por debajo de los
139 MiB iniciales y la memoria disponible del host terminó por encima del valor
inicial de 1.884 MiB. No hay indicios de fuga RSS del runner; la retención del
cgroup es compatible con caché de páginas, aunque las ejecuciones posteriores
permitirán comprobar que no exista crecimiento acumulativo.

Conclusión del Ensayo A: el runner cabe en la RPi4 en esta ejecución, termina con
margen amplio frente al intervalo de tres horas, regenera el layout filtrable y
recupera la memoria del proceso hijo sin OOM ni presión térmica preocupante. No
se cerró el P0 en ese momento porque todavía faltaban los ensayos B y C.

## Resultado real — Ensayo B en RPi4 (`0.2.228`)

El paquete se exportó el 2026-08-07 a las 23:44:48 UTC, antes de que comenzara
el siguiente runner programado. Contiene una única carga física del Predictor
con sus snapshots `retained_60s` y `retained_600s`, sin interferencia del runner:

- evidencia: `rainmapper-diagnostics-20260807T234448Z.zip`, SHA-256
  `04c1a35006e7d99f7425405f25a175d0ea2f9d184df76ffdcc254af11429d9b4`;

- subfase instrumentada `predictor_weather_load`: 8,667 s;
- tiempo manual extremo a extremo percibido por el usuario, desde pulsar el
  botón hasta ver la pantalla: al menos unos 30 s;
- 115 estaciones y 79.931 registros cargados desde un Parquet de 11,968 MiB;
- RSS del proceso: 241,4 MiB al inicio, pico observado posterior de 352,5 MiB y
  337,8 MiB a los 600 s;
- cgroup: 290,1 MiB al inicio, pico de 423,2 MiB y 409,4 MiB a los 600 s;
- `MemAvailable`: mínimo de 1.727,8 MiB durante la carga y 1.752,8 MiB a los
  600 s;
- temperatura máxima instrumentada: 48,69 °C; 44,79 °C a los 600 s;
- CPU de la subfase meteorológica: 10,676 s de CPU en 8,667 s de pared,
  equivalente al 123,2 % de un núcleo;
- `oom=0` y `oom_kill=0` en todos los eventos.

Entre 60 y 600 s el RSS solo cambió de 337,1 a 337,8 MiB y el cgroup de 407,1 a
409,4 MiB. La retención es estable y compatible con la caché meteorológica; no
se observa crecimiento acumulativo en esta ventana. El Ensayo B pasa en memoria,
temperatura y ausencia de OOM.

Los 8,667 s no representan la experiencia completa del usuario. La diferencia
respecto a los al menos 30 s observados queda pendiente de desglosar con un
monitor extremo a extremo de la petición y fases internas de renderizado. No se
debe presentar la subfase meteorológica como tiempo total de apertura.

## Resultado real — Ensayo C en RPi4 (`0.2.228`)

Durante el siguiente runner programado, el usuario intentó abrir el Predictor y
la aplicación mostró correctamente el aviso de que no estaba disponible porque
había un runner activo. Esto valida en HA real la puerta funcional de
`action_is_running()` y evita iniciar una predicción concurrente.

El paquete se exportó el 2026-08-08 a las 00:04:22 UTC, después de la recuperación
de 600 s:

- evidencia: `rainmapper-diagnostics-20260808T000422Z.zip`, SHA-256
  `49a396ae5c9585c4f0b20a01d73a8e22d856ca4e7c5b9a7ed2a38dfb83bd2278`;
- `predictor_cache_released` registró 4 instancias liberadas, sin error, 725 ms
  antes de que arrancara el proceso hijo `runner_update`;
- el runner programado `all` terminó con exit code 0 en 403,4 s (6 min 43 s):
  `update` 322,7 s y `maps` 56,9 s;
- pico RSS histórico del hijo: 1.300,7 MiB; máximo RSS actual agregado:
  1.283,2 MiB;
- máximo actual del cgroup: 1.432,6 MiB y pico del cgroup: 1.477,2 MiB;
- mínimo `MemAvailable`: 780,2 MiB; temperatura máxima: 50,15 °C;
- Parquet: 626.809 filas, 1.225 row groups y 12,004 MiB; catálogo: 79,304 KiB;
- Meteocat agotó el primer intento de condiciones por timeout, reintentó y
  completó correctamente; el resto del flujo funcional terminó sin fallos;
- `oom=0` y `oom_kill=0` en todos los eventos.

La liberación de referencias fue anterior al hijo, pero la memoria física del
servidor no volvió al sistema de inmediato: justo antes del runner seguía en
333,7 MiB RSS y el cgroup en 421,1 MiB. Esto elevó el pico del cgroup unos
129,4 MiB respecto al Ensayo A. Aun así, el margen real fue suficiente y no hubo
OOM. Al terminar `update`, el RSS del servidor había bajado a 168,6 MiB. En
`recovery_600s` quedó en 169,1 MiB, el cgroup en 456,2 MiB y `MemAvailable` en
1.825,8 MiB, solo unos 32 MiB por debajo del estado previo a abrir el Predictor.

Conclusión del Ensayo C: pasan tanto el bloqueo visible como la exclusión y
recuperación de recursos. El P0 de memoria se cierra para la RPi4 y el uso
monousuario ensayado, con runner cada tres horas y sin concurrencia deliberada.
La apertura extremo a extremo de al menos 30 s queda como problema de rendimiento
separado; la caja negra persistente queda como mejora de observabilidad.

Después de los ensayos, el usuario confirmó el 2026-08-08 que también había
completado la reconstrucción de features, el entrenamiento con el worker
actualizado y la promoción de los modelos junto con `ml_train_report.json`. Por
tanto, no queda una migración de artefactos ML pendiente para cerrar esta serie.

## Criterio de cierre

Los paquetes reales A–C confirman que:

- runner y Predictor terminan sin OOM, reinicio ni pérdida de conectividad;
- el runner finaliza con margen amplio respecto al intervalo de tres horas;
- la memoria vuelve cerca del estado base después del runner;
- las consultas repetidas no generan crecimiento acumulativo;
- temperatura y alimentación permanecen estables;
- el Parquet regenerado usa row groups filtrables.

El P0 queda cerrado dentro del alcance probado. No constituye una prueba de
carga multiusuario ni garantiza por sí solo el comportamiento tras futuros
cambios; el histórico persistente permitirá vigilar su evolución.

## Validación local

El 2026-08-08 pasó `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh` completo
para `0.2.228`: 469 tests, compilación Python, parseo JavaScript, fixtures
operativas y comprobación de whitespace. Esto valida los contratos y la
integración local; no sustituye los ensayos A–C sobre la RPi4.

Después de implementar localmente la caja negra v2 y la ventana meteorológica
temporal, el mismo smoke completo pasó de nuevo el 2026-08-08 con 484 tests y se
validó el Predictor de `0.2.229` en la RPi4. Tras el runner interrumpido y el
refuerzo diagnóstico, `0.2.232` pasó el smoke completo con 490 tests y se publicó
con digest
`sha256:bb819e5407f1c685eb75b05955841b3e35554d3467140a3ff56a2708eec721da`;
después quedó instalada y validada con el runner manual descrito arriba.

El ajuste local posterior que presenta los timestamps diagnósticos en la zona
horaria del Control Panel pasó el smoke completo con 495 tests. La pestaña
Diagnostics, la comparación A/B, la correlación padre/hijo, el resumen de las
cuatro fuentes y las medias por versión elevaron la suite local a 499 tests.
La evolución temporal/por versión, los rangos mínimo-máximo, el Gantt y la
corrección del evento `change` de los selectores A/B elevaron después la suite
local a 500 tests. El esquema `2.2`, la persistencia de intervalos para las
cuatro fuentes, los acordeones del Gantt y la compatibilidad explícita con `2.1`
elevaron después la suite a 501 tests. El conjunto final de `0.2.233`, incluido
el transporte y ciclo de vida del worker, pasó 511 tests y se publicó con digest
`sha256:8289ee5bc28983f238a0b7fcc0718f6ad8d40492629699b52157cb3d9e9013c9`.

La release `0.2.238` incorpora la distinción adicional
`worker_response_cache_status` para separar la reutilización del runtime de la
reutilización de una respuesta completa. La inferencia por lotes y las cachés
LRU acotadas pasaron el smoke completo con 530 tests. Los tags `0.2.238` y
`latest` se publicaron con digest multi-arquitectura
`sha256:90f87d105f08b0061c480dd8168126663cb947d4128771c70179b1379b7e5e0d`;
la medición real se documentará después de instalar HA `0.2.238` y worker
`1.0.1`.

### Validación real de `0.2.233` y esquema 2.2

El 2026-08-08 se instaló `0.2.233` en la RPi4 y se lanzó manualmente `Run all`.
La operación padre `runner_action` terminó correctamente en 362,690 s. Su pico
de cgroup fue 1.372,520 MiB, el mínimo `MemAvailable` 810,484 MiB, la temperatura
máxima 55,99 °C y no hubo OOM. El proceso hijo `runner_update` terminó en
279,793 s con un consumo medio equivalente al 91 % de un núcleo; en la RPi4 de
cuatro núcleos esto representa alrededor del 23 % de la capacidad total y es
coherente con el 89,4 % medido en `0.2.232`.

El resumen `2.2` conservó intervalos reales independientes para las cuatro
fuentes:

| Fuente | Duración | Filas | Estaciones |
|---|---:|---:|---:|
| AEMET | 91,754 s | 61.327 | 877 |
| Meteoclimatic | 57,753 s | 151.156 | 750 |
| Meteocat | 69,266 s | 326.043 | 202 |
| Wunderground | 17,937 s | 88.581 | 119 |

La recuperación quedó registrada como sigue:

| Momento | Cgroup actual | `MemAvailable` | RSS proceso | Temperatura |
|---|---:|---:|---:|---:|
| 60 s | 527,223 MiB | 2.215,707 MiB | 54,273 MiB | 51,12 °C |
| 600 s | 529,980 MiB | 2.183,270 MiB | 57,137 MiB | 47,71 °C |

No quedaron anomalías, operaciones ni snapshots pendientes. La estabilidad
entre 60 y 600 segundos confirma que los aproximadamente 530 MiB corresponden
al reposo recuperado del cgroup y no a una caída transitoria. La UI muestra por
diseño dos ejecuciones correlacionadas: `Runner` mide el flujo completo y
`Runner update` aísla el hijo meteorológico. Solo deben compararse operaciones y
acciones equivalentes; el aviso **Not a like-for-like comparison** impide
interpretar como regresión una pareja padre/hijo.
