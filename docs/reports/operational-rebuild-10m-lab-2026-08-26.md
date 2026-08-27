# Informe de laboratorio: rebuild operativo ≤10 minutos

Fecha: 2026-08-26

Estado: entregas A y B implementadas y validadas exclusivamente en local; sin
build, instalación, publicación, bump, release ni cambios en HA real o en el
worker normal.

## Alcance y salvaguardas

Se preservaron todos los cambios locales y ficheros no rastreados. No se usó
Tailscale, no se cambió la retención y no se hizo ningún borrado manual. Las
ejecuciones se hicieron con la imagen local existente
`rainmapperha:local-ha-ui`, sin levantar otro servicio worker. Para el smoke
extremo a extremo se copió de forma reversible el código actual dentro de ese
contenedor y se reinició solo HA local; `rainmapper-worker:1.0.17` conservó sus
tres días de uptime. Los datos continuaron en los volúmenes locales montados.

El objetivo sigue siendo reducir el flujo completo «Reconstruir y reentrenar
operativo» de aproximadamente 37 minutos a un máximo de 10, manteniendo
integridad, cancelación, retry, rollback y promoción atómica.

## Estado inicial medido

La línea base local persistida usó el mismo snapshot de 374 observaciones
elegibles, cinco versiones, once perfiles y 714 fits finales:

| Fase | Fría | Caliente |
|---|---:|---:|
| Total | 1.158,499 s | 1.168,757 s |
| Reconstrucción/verificación | 101,125 s | 101,130 s |
| Preparación | 808,503 s | 821,304 s |
| Entrenamiento final | 220,917 s | 222,255 s |
| Instalación/promoción | 3,287 s | 3,448 s |

La preparación, no los fits finales, era el cuello principal. La ejecución
caliente no la mejoraba.

## Telemetría añadida

`mushroom_performance_telemetry` mantiene tiempo monotónico por fase y
contadores acumulativos de bytes leídos/escritos, ficheros, peticiones, hashes,
copias y `fsync`. Se integró en snapshot, transporte de entrada y resultados,
trainer, hold-out, actualización local y ejecución multiversión. Los eventos se
persisten en los artefactos de telemetría del job; no dependen de la barra de
progreso de la UI.

También se redujeron publicaciones redundantes mediante telemetría coalescida
sin cambiar los puntos de control de cancelación. Estos cambios instrumentan
los cuellos de transporte/cola, pero no se ha acometido todavía su
compactación: las mediciones de preparación justificaron priorizar cálculo.

## Entrega A: tuning operativo congelado

Se separó el retune científico de la reconstrucción operativa. El catálogo de
tuning es inmutable, verificable y falla cerrado ante decisiones ausentes o
incompatibles; reconstruir sigue recalculando hold-out y ajustando los modelos
finales con los datos actuales, pero no repite silenciosamente la búsqueda
completa de hiperparámetros.

Evidencia:

- catálogo SHA-256
  `e9730b7c0e82ef37c321f5ea2cfc04f8e08f1ea6976b6d9559140291972f6e99`;
- 714 decisiones y 714 artefactos de origen verificados por hash;
- 5.292 fits internos máximos eliminados del plan actual;
- preparación completa: 459,101 s, mejora de aproximadamente 43--44 % frente
  a 808,503/821,304 s;
- residual medido: unos 360 s materializando repetidamente V3/V4/V5 y unos
  99 s en hold-out e informes.

La reducción no superaba por sí sola la puerta del 50 %, por lo que no se
amplió el catálogo y se pasó a eliminar la materialización redundante.

## Entrega B: workspace meteorológico y de suelo compartido

`OperationalWeatherWorkspace` vive únicamente durante una preparación
operativa dentro del mismo proceso. Las rutas científicas/directas siguen
construyendo todos sus artefactos de forma independiente.

El workspace:

1. deriva de las observaciones el intervalo máximo requerido;
2. carga una sola vez todos los registros meteorológicos de ese intervalo que
   cumplen el contrato espacial existente;
3. construye una serie IDW máxima y ET0 por microárea;
4. entrega a cada contrato una vista con sus fechas exactas;
5. conserva la semántica de estaciones ausentes en una ventana más corta y
   recalcula el borde izquierdo de lluvia, donde cambia la supresión de
   duplicados consecutivos;
6. conserva en memoria los estados de suelo operativos V4 y los reutiliza en
   V5.

No se filtran observaciones ni predictores. Se conservan los filtros previos:
radio máximo de 15 km, estaciones deshabilitadas por `stations.txt` y fechas
fuera del intervalo requerido. Todos los registros comprendidos dentro del
intervalo máximo se cargan. La ruta operativa materializa únicamente
`wv0033_0_30cm`; las otras cinco variantes de suelo continúan disponibles en el
benchmark científico y no eran consumidas por el entrenamiento operativo.

La selección de la variante operativa es explícita por identificador. Las
medias diarias siguen usando `statistics.fmean` para conservar incluso el orden
y redondeo del cálculo anterior.

## Medición de la entrega B

Ejecución reproducible:

- snapshot y meteorología congelados en `docker-data`;
- catálogo de A en
  `/private/tmp/rainmapper-delivery-a-prep.Rv1YI3/tuning-catalog.json`;
- salida conservada en
  `/private/tmp/rainmapper-weather-workspace-benchmark.ICspuS`;
- imagen local existente, `--network none`, sin servicio worker;
- una única preparación completa; no se repitió una pasada caliente ni se
  ejecutó el entrenamiento final/promoción.

Resultado:

| Medición | Tiempo |
|---|---:|
| Línea base fría | 808,503 s |
| Línea base caliente | 821,304 s |
| Entrega A | 459,101 s |
| Entrega B | ~185,4 s |

La entrega B ahorra aproximadamente 273,7 s adicionales, un 59,6 % respecto a
A y un 77,1--77,4 % respecto a las líneas base originales. Cumple el presupuesto
de preparación de 230 s de la especificación.

Contadores del workspace:

- intervalo máximo: `2011-11-11..2026-08-20`;
- 293 estaciones cargadas;
- 62 series máximas construidas;
- 124 reutilizaciones de serie y 124 de vista;
- 1.048 estados de suelo operativos cacheados.

## Smoke extremo a extremo: resultado frío y caliente

Se ejecutó desde la UI/API local el flujo real `Actualizacion local completa`
con las cinco versiones, once perfiles y 714 fits. El ejecutor fue
`Home Assistant local`; no intervino ningún worker externo.

Una primera tentativa terminó a los 133,5 s, antes del cálculo pesado, porque
el nuevo preparador no insertaba la raíz del repositorio en `sys.path` al
ejecutarse como `/app/scripts/...`. Se corrigió con el mismo bootstrap que ya
usan los otros scripts de jobs y se comprobó desde `/private/tmp` con entorno
vacío. No produjo candidato ni promoción multiversión.

Resultados válidos:

| Medición | Fría | Caliente |
|---|---:|---:|
| Total monotónico | 534,571 s | 473,654 s |
| Reconstrucción compute | 94,293 s | 91,104 s |
| ML v0 | 24,154 s | 19,267 s |
| Preparación operativa compartida | 260,947 s | 236,058 s |
| Fits operativos | ~149,8 s | ~122,1 s |
| Instalación/promoción | 3,263 s | 2,986 s |

Los tiempos de preparación suman el snapshot operativo y todas las subfases
desde `operational_preparation` hasta `prepared_selected_multiversion_inputs`.
Los fits incluyen la entrada del trainer y las cinco versiones. El total frío
fue 8 min 55 s y el caliente 7 min 54 s: ambos cumplen el máximo de 10 minutos.
Frente a los aproximadamente 37 minutos observados en HA real, la reducción
local es de unos 28--29 minutos, alrededor del 76--79 % según qué extremo de
comparación se use.

En ambas pasadas se obtuvieron 714/714 fits y cero fallos. La reconstrucción
verificó 9 artefactos con `comparison_status=equivalent`, ML v0 verificó 19
artefactos para ocho especies y la instalación multiversión terminó como
`verified_batch_installed`. Reconstrucción, ML v0 y multiversión se promovieron
solo después de verificar sus candidatos.

Telemetría fría/caliente persistida respectivamente en:

- `/share/rainmapper/mushroom-data/diagnostics/operational-performance/iOwVr93mtvPhrsNo.json`;
- `/share/rainmapper/mushroom-data/diagnostics/operational-performance/t6wbQC_Y-J78C_oq.json`.

Contadores totales frío/caliente:

| Contador | Fría | Caliente |
|---|---:|---:|
| Bytes leídos | 1.301.674.475 | 1.288.736.955 |
| Bytes escritos | 328.689.290 | 328.689.824 |
| Ficheros leídos | 5.595 | 5.390 |
| Ficheros escritos | 891 | 891 |
| Hashes | 2.473 | 2.473 |
| Bytes hasheados | 804.943.017 | 804.945.774 |
| Copias | 826 | 826 |
| Bytes copiados | 297.081.325 | 297.081.846 |
| `fsync` | 97 | 97 |
| Peticiones / persistencias de cola | 0 / 0 | 0 / 0 |

Los mayores costes restantes de preparación fría fueron hold-out V2--V5
(84,713 s), V3 fijo compartido (64,602 s), hold-out V6 (30,678 s), V4 lag
(26,917 s) y V5 (22,148 s). Las sucesivas versiones ya no reconstruyen una
base meteorológica completa: V3 lag, V4 y V5 reutilizan el workspace máximo.

## Integridad y equivalencia

La comparación se hizo contra
`/private/tmp/rainmapper-delivery-a-prep.Rv1YI3/prepared-frozen-final`:

- V3 fixed/lag: igualdad semántica exacta después de retirar únicamente rutas
  y metadatos de materialización;
- V4 fixed/lag: igualdad exacta de muestras, elegibilidad y estado de suelo
  `wv0033_0_30cm`; se normalizó la ausencia intencionada de las otras cinco
  variantes científicas;
- V5 fixed/lag: igualdad semántica exacta;
- hold-out V2--V5: 16.640 filas idénticas byte por byte, SHA-256
  `2c55f6ad3eca1696ee41bcb9ad5263f7ba323236ba03e8ed68b3ff21d02b2447`;
- hold-out V6: 10.656 filas idénticas byte por byte, SHA-256
  `2aba4cc28e020645d4c575561c97030e982d77078a623f1d503c51930a4d444c`.

Conteos observados durante la ejecución:

- V3 fixed: 417 muestras, 374 elegibles, 270/250 grupos 7d/14d;
- V3 lag: 2.919 muestras, 2.618 elegibles, 270/250 grupos 7d/14d;
- V4 fixed: 374 elegibles por bloque y 368 para suelo;
- V4 lag: 2.618 elegibles por bloque y 2.576 para suelo;
- V5 fixed/lag: 417/2.919 muestras.

## Validación automatizada

- 78 pruebas de workspace, IDW, preparación y contratos V3/V4/V5: correctas;
- cierre ampliado de 165 pruebas sobre telemetría, snapshots, transporte,
  resultados, catálogo, trainer, hold-out, workspace y contratos científicos:
  correctas en 18,948 s;
- cierre final tras el smoke y la corrección del bootstrap: 184 pruebas
  dirigidas correctas (94 flujo/telemetría/workspace/trainer/jobs, 39 Predictor
  web y 51 snapshot/transporte/resultados);
- compilación de todos los Python modificados: correcta;
- `git diff --check`: correcto.

La advertencia de joblib sobre detección de núcleos físicos en el sandbox no
alteró las pruebas; joblib usó el número de núcleos lógicos.

## Incidente Predictor observado y corrección local

La lectura del `share` montado mostró dos
consultas Edulis/Salteguet con 78 selecciones (V3 24, V4 24, V5 12 y V6 18)
fallando tras 2:33 y 2:08 con
`<urlopen error [Errno 32] Broken pipe>`. Consultas menores terminaron entre 9 y
19 s; una selección anterior de 24 modelos terminó en 11 s.

El worker envía la respuesta completa dentro de un único `POST /jobs/finish`,
con timeout de 3 s y retry transitorio de 120 s. HA limita el resultado
estructurado a 8 MiB más 64 KiB de envoltorio. La causa inmediata confirmada es
la rotura HTTP; queda pendiente medir el resultado de 78 modelos antes del
envío para distinguir con certeza si se supera el tamaño máximo o el tiempo de
escritura. No se tocó HA real ni el worker normal para investigarlo.

Una segunda reproducción independiente confirmó el mismo patrón con una
consulta semanal de Edulis para todas las zonas: empezó a las 18:33:40, terminó
fallida a las 18:36:52 y registró el mismo `Broken pipe`, sin resultado
persistido. La petición guardada llevaba `view=week`, `compare_models=false` y
cero selecciones multiversión; por tanto, el fallo no exige una comparación de
78 modelos. Una respuesta semanal anterior de Edulis ocupó 6,3 MiB con el
runtime anterior, suficientemente cerca del guardarraíl de 8 MiB para que una
respuesta V6 más rica pueda superarlo. Esto sigue siendo una inferencia de
tamaño muy sólida, no una medida del payload fallido: el worker no lo conserva
cuando falla `/jobs/finish`.

Se descartó añadir un protocolo de upload separado por ser una complejidad no
justificada para estos tamaños. La corrección local conserva el flujo actual
`worker -> POST finish -> validación y externalización atómica en HA`, pero:

- eleva el límite estructurado de 8 a 64 MiB; el límite HTTP de HA sigue
  derivándose de este valor y añade 64 KiB para el envoltorio;
- comprueba el tamaño en el worker antes de abrir el `POST`; excederlo produce
  un `ValueError` determinista y no entra en el retry transitorio de 120 s;
- concede 60 s únicamente al `finish` del Predictor; start, progress, control
  y los demás tipos de job conservan 3 s;
- conserva externalización provisional, validación contractual, tamaño,
  SHA-256 y escritura atómica existentes.

También se reprodujo y corrigió la navegación que generaba trabajos
redundantes. Había dos causas independientes: los selectores de especie y zona
ejecutaban `requestSubmit()` en cada cambio, y el controlador JavaScript
interceptaba cualquier enlace interno con `executor` como orden de cálculo.
Además, un enlace desde el recommender no enviaba versiones: el worker
calculaba la ruta preferida simple mientras la página intentaba leer la versión
preferida como resultado multiversión, por lo que el primer resultado aparecía
vacío y el siguiente `Predecir` repetía el cálculo con otra petición.

La implementación local resuelve una única selección de versiones tanto para
encolar como para renderizar. Los desplegables ya no envían el formulario; el
usuario puede cambiar especie, zona, fecha y versión y solo `Predecir` calcula.
Cambiar especie sí reconstruye inmediatamente las zonas válidas, en memoria y
sin worker, reutilizando el catálogo completo especie-zona incluido en el
recommender, también para especies fuera de temporada. Solo los enlaces
marcados expresamente lanzan un trabajo. El detalle dirigido ya contiene siete
días y sus celdas reutilizan el `job_id` terminado en vez de recalcular. El
selector de especie de Historial también espera ahora al botón `Buscar`.

Validación local de este bloque: 38 pruebas Predictor del servidor, 12 del
servicio Predictor, 44 de jobs/worker y una regresión específica de selección
remota; todas correctas. Además, una consulta local Edulis, V6, todas las zonas
y franja semanal terminó dos veces con HTTP 200 en 7,623 y 7,684 s, respuesta
de unos 348 KiB y sin errores visibles. Esto valida el cálculo y render local,
no el transporte remoto de un resultado grande; HA real y el worker normal no
se tocaron.

## Riesgos y trabajo pendiente

1. El objetivo de 10 minutos queda demostrado en HA local, no todavía en el
   transporte HA↔worker real. Subir el código puede reintroducir los costes de
   cola, upload por fichero y red medidos en la línea base remota.
2. Falta medir RSS máximo de B y proyectar memoria/tiempo con 4.000 y 40.000
   observaciones. El diseño evita una matriz global de cientos de miles de
   columnas, pero la salida JSON continúa siendo grande (862 MiB en esta
   preparación).
3. Cancelación, retry y rollback conservan sus rutas y pruebas dirigidas; el
   smoke demuestra verificación y promoción atómica, pero no provocó una
   cancelación ni un rollback durante una ejecución real.
4. Cola, uploads fragmentados y verificaciones repetidas siguen pendientes
   para el camino remoto. Las mediciones locales no justifican tocarlos antes
   de medir el mismo código en el worker normal después de una entrega.
5. Predictor está corregido y medido localmente, pero falta validar visualmente
   la navegación completa y medir un resultado remoto grande con el nuevo
   límite de 64 MiB.

## Decisión al cierre

Las entregas A+B superan la puerta final: 8 min 55 s en frío y 7 min 54 s en
caliente, con equivalencia, 714/714 fits, cero fallos y promoción verificada.
No se justifica ampliar ahora la refactorización con C, paralelismo o
compactación de cola. El siguiente paso, sujeto a decisión del usuario, es
preparar la entrega HA/worker y medir el camino remoto antes de optimizar el
transporte restante.
