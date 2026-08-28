# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado exacto al cierre — 2026-08-28

### Alcance científico estable y release HA 0.2.276 / worker 1.0.25

- La cadena real con HA `0.2.275` y worker `1.0.24` terminó correctamente:
  reconstrucción en 1 min 45 s, ML v0 en 33 s y entrenamiento V2–V6 en
  10 min 15 s. Los tres trabajos promocionaron la generación y la carga de la
  RPi4 volvió a su nivel habitual al terminar. La meteorología no cambió porque
  el scheduled runner no llegó a activarse.
- El Predictor real quedó operativo sobre la generación promocionada. Se
  observaron un recommender frío de 29,0 s (23,9 s de cálculo), reutilización
  al cambiar de día en 0,6 s (cálculo menor de 0,1 s), una fecha nueva en
  12,0 s (9,4 s de cálculo) y una consulta multiversión fría en 29,0 s
  (23,6 s de cálculo).
- La comparación de los inputs actuales local/HA encontró 439 filas científicas
  idénticas, pero inicialmente scopes distintos. La causa confirmada era que la
  identidad incluía `generated_at`, `updated_at` y la envoltura/ruta del
  artefacto, aunque las filas y el contenido científico de known-sites fueran
  iguales.
- `OperationalTrainingScope` revisión `.2` identifica ahora solo las filas
  científicas ordenadas y el contenido científico de known-sites, eliminando
  recursivamente esos timestamps volátiles. Cambiar una feature o una altitud
  sigue invalidando el scope.
- Con los inputs reales actuales, local y HA producen exactamente el scope
  `sha256:47d934d7c4fadde8b533efc35964b833d4e0f9710ee1dc4cebc4e4275830ec07`;
  comparten identidades de features
  `sha256:df7d79e259967d3d2096c38193287b1bc8e2190c83078b3c08c9f973118e1218`
  y known-sites
  `sha256:d4427532f4ef84cb42040a086edd993361487bf06aac2939fc0dd865783793dc`.
  El scope contiene ocho especies. El centinela Cantharellus conserva 15 filas,
  diez elegibles, nueve episodios y exclusión `insufficient_area_episodes`.
- Pasan 49 pruebas dirigidas de scope/ML/worker, 327 pruebas de integración
  local/HA/worker/resultados/web, siete de empaquetado del worker y el smoke
  completo de 1.089 pruebas.
- HA `0.2.276` está publicada. `0.2.276` y `latest` comparten el índice OCI
  `sha256:70013bb4d17dfca0ec46652398da39119c00e9e78790dd4941b71f5692635b36`
  y manifests `linux/amd64` y `linux/arm64`.
- El worker local `1.0.25` está `healthy` e `idle`, con la identidad conservada
  `worker_1a9a232c20fe2ee2`, el volumen persistente y las cachés GIS/Predictor
  válidas. No se publica en GHCR.
- HA real aún no tiene confirmada la instalación de `0.2.276`. No atribuirle
  validación real hasta que el usuario la confirme. No es necesario repetir una
  reconstrucción para validar el cambio de identidad: la igualdad se comprobó
  directamente con los mismos inputs actuales.

### Release preparada tras la tercera validación real: HA 0.2.275 y worker 1.0.24

- La tercera cadena real con HA `0.2.274` y worker `1.0.23` completó
  reconstrucción y ML v0, pero V2–V6 falló al 90 % después de 13 min 24 s. El
  error exacto del worker fue `HTTP Error 409: Conflict` durante
  `Uploading active operational models`; no hubo promoción.
- La causa confirmada era una entrega repetida después de una respuesta perdida:
  HA ya conservaba el fichero recibido y rechazaba siempre el segundo intento
  porque la ruta existía. HA `0.2.275` compara tamaño y SHA-256: acepta como
  idempotente un duplicado idéntico y mantiene el 409 si el contenido difiere.
- Worker `1.0.24` desacopla control/progreso del callback científico mediante
  un único intercambio en segundo plano, conserva solo el último progreso y
  limita la cadencia normal a 10 s. Los heartbeats locales pasan de 2 a 5 s.
  La entrega final continúa reintentándose hasta recuperar al coordinador o
  recibir cancelación.
- El worker local `1.0.24` está activo con la misma identidad
  `worker_1a9a232c20fe2ee2`, el mismo volumen persistente y cachés GIS/Predictor
  válidas. No se publica en GHCR.
- HA `0.2.275` está publicada. `0.2.275` y `latest` comparten el índice OCI
  `sha256:64f0cbda06a3b0addcb507bf0efac494d98e14d725f73e50d37c6075840e1e6b`
  con manifests `linux/amd64` y `linux/arm64`.
- La siguiente validación real se hará después del scheduled runner y de la
  actualización meteorológica. Permitirá validar transporte, duración y
  equivalencia contractual; las métricas no se compararán como igualdad exacta
  con un entrenamiento que usó otro snapshot meteorológico.

### Tercera validación real: HA 0.2.274 y worker 1.0.23

- El único worker fue actualizado localmente a `1.0.23`, conservando identidad,
  volumen y cachés; HA real lo reconoció con esa versión y el usuario lanzó una
  nueva cadena. No se publicó el worker en GHCR.
- La UI no representa una duración integral de la cadena: el contador pierde
  aproximadamente un minuto de preparación en HA al pasar al job remoto. Dentro
  del job V2–V6 la duración sí se conserva entre fases, pero no incluye la
  preparación anterior ni las transiciones entre jobs.
- El porcentaje tampoco es global ni monótono. En V2–V6 mostró `81 %` durante
  `Reusing sealed local inputs` y después bajó a `20 %` al empezar
  `Building V3 fixed-window inputs`; más tarde mostró `37 %` en
  `Building V5 raw-weather inputs`. Son escalas internas de fase presentadas en
  una única columna y no permiten estimar avance total ni ETA.
- La preparación observada fue aproximadamente: algo más de un minuto antes del
  job; `Reusing sealed local inputs`, 1 min 43 s hasta 81 %; después la duración
  del mismo job siguió acumulándose. La reutilización del bundle ML v0 sí tardó
  solo 1–2 s, lo que confirma que los bundles no tienen el mismo coste.
- En el worker, el bundle V2–V6 materializó 38 ficheros y 52 MiB. Los objetos
  sellados con recibo se validan por metadatos y se enlazan; durante esta pasada
  solo se creó un recibo nuevo para un objeto de 319.193 bytes. Por tanto, el
  retraso de casi dos minutos no se explica por hashing masivo.
- Control y progreso siguen siendo llamadas síncronas de hasta 3 s. Con un
  callback por fichero, un timeout que supera el intervalo de coalescencia puede
  hacer que el siguiente fichero vuelva a bloquear. Los logs registraron
  heartbeats intermitentes fallidos; esta telemetría ya no aborta el cálculo en
  `1.0.23`, pero todavía puede ralentizar una fase local.
- ML v0 fue reclamado a `16:11:43Z` y verificado a `16:14:23Z`; el usuario
  observó unos 15–20 s de entrenamiento y unos 120 s de subida. Tras verificar
  el resultado hubo 71 s hasta reclamar V2–V6 y el heartbeat permaneció fallido
  durante 66 s. La CPU de HA subió aproximadamente al 35 % en esa transición.
  Esto demuestra una pausa/respuesta degradada del coordinador, pero todavía no
  atribuye por sí solo el coste exacto entre ingesta, verificación y preparación.
- La cadena terminó fallando al 90 % durante la entrega V2–V6; la causa y la
  corrección publicada se resumen en la sección anterior. Sigue pendiente una
  cadena completa para comparar scope, plan, fits, métricas, artefactos y
  promoción frente a la cadena local.

### Segunda validación real de HA 0.2.274: cálculo correcto hasta la entrega

- El usuario instaló HA `0.2.274` y lanzó una cadena real con el worker
  `1.0.22`. Reconstrucción terminó en 5 min 46 s y ML v0 en 1 min 50 s, con
  ocho especies. V2–V6 alcanzó el 90 % y falló después de 12 min 34 s según la
  UI; no hubo promoción.
- El error exacto del worker fue `<urlopen error timed out>` a
  `2026-08-28T12:23:03Z`. Los logs registraron además timeouts intermitentes de
  heartbeat durante el mismo trabajo. Es un fallo de transporte en la entrega,
  distinto del rechazo de scope corregido en HA `0.2.274`.
- La CPU de la RPi4 se mantuvo aproximadamente en 26–31 % durante el trabajo y
  volvió al 11 % al terminar. Esto vincula la carga al job, pero no demuestra
  por sí solo qué proporción corresponde a telemetría, hashing, recepción o
  verificación. Queda pendiente medir bytes y peticiones por fase.
- Cambio incorporado al worker local `1.0.23`: los timeouts
  transitorios de control/progreso no abortan el cálculo; cuando un resultado
  ya está calculado, reconstrucción, ML v0 y V2–V6 reintentan su entrega sin
  límite hasta recuperar el coordinador o recibir cancelación. Descargas,
  claim, inicio y demás comunicaciones conservan sus límites actuales; no se
  añade cola ni estado persistente nuevo.
- Pasan 98 pruebas dirigidas del worker y el smoke completo de 1.085 pruebas.
  Se hizo bump y build local de `1.0.23`, sin publicación en GHCR.

### Hotfix HA 0.2.273 y validación local posterior

- El primer reentrenamiento del laboratorio con HA `0.2.272` completó la
  reconstrucción y ML v0, pero falló al verificar ML v0 con
  `name 're' is not defined`. La causa era un `re.fullmatch` añadido al validar
  `operational_scope_id` sin importar `re` en
  `rainmapper_core/mushroom_worker_results.py`.
- El hotfix añade el import y una prueba centinela que acepta una identidad
  operacional SHA-256 válida. Pasan las 32 pruebas dirigidas de resultados,
  scope y actualización local, y el smoke completo de 1.079 pruebas.
- El laboratorio se reconstruyó con HA `0.2.273`. Con la copia local actual de
  weather-history, observaciones, known-sites, registro y catálogo, la cadena
  local terminó correctamente entre `10:06:51Z` y `10:16:18Z`, sin fases
  fallidas.
- El scope realmente ejecutado fue
  `sha256:ee11675beb09ab1a8b2609a346c895f7ae853cdbce7c7d1870028d52c4b2c699`
  y el plan
  `sha256:fa280ce72e935ea888f3ccad04eaee01a210bcb0df1cb4a160b488c686601ea6`.
  El lote `local_operational_20260828T101432Z` ejecutó 636/636 fits, cero
  fallos, ocho especies, cinco versiones y once perfiles.
- La promoción atómica instaló las generaciones de ese lote para V2, V3, V4,
  V5 windowed y V6 windowed; todos sus gates persistidos figuran como
  `passed`. La versión preferida sigue siendo Biology V4.
- Un Predictor local posterior terminó con HTTP 200, sin OOM, usando un nuevo
  fingerprint de runtime. La primera petición fría tardó 29,617 s; el usuario
  confirmó que varias predicciones locales posteriores funcionan a velocidad
  razonable.
- HA `0.2.274` está publicada en GHCR. Los tags `0.2.274` y `latest` comparten
  el índice OCI
  `sha256:899d45f797952218ea865e40d3293247ab14d8d6f3e6e53ea7f807595f0fd001`
  y contienen manifests `linux/amd64` y `linux/arm64`.
- El usuario va a instalar HA `0.2.274`; no darla por instalada hasta que lo
  confirme. Después ejecutará el reentrenamiento en HA real con el único worker
  `1.0.22`, y Codex comparará los resultados local/remoto.

### Implementación y release posterior al cierre

- Se implementó `OperationalTrainingScope` canónico después de la agregación
  por área/fecha y los gates científicos, junto con un plan serializable que
  sella scope, catálogo, versiones, perfiles y fits. Local, HA y worker consumen
  esas identidades y rechazan redescubrimientos o divergencias.
- El caso centinela de Cantharellus queda excluido de forma reproducible: diez
  filas elegibles forman nueve episodios y producen
  `insufficient_area_episodes`.
- Con los mismos inputs locales, registro y catálogo, dos serializaciones de la
  ruta producen exactamente el scope
  `sha256:45f5aad288480362ccbb9baf5fb6bdebddce944fdfea0184d5a763fe2b88a865`
  y el plan
  `sha256:be5d22b4e0897f0940d39a1203fc1be4c695b3c1102d8a8344a56fab7810e13f`.
  El plan contiene ocho especies, cinco versiones, once perfiles y 636 fits.
- Una preparación local no destructiva materializó los ocho inputs V2–V6 con
  esas mismas identidades y sin especies fuera del scope. No ejecutó
  reconstrucción, entrenamiento, instalación ni promoción.
- Pasan 84 pruebas dirigidas de scope/transporte/worker, 301 de HA/local/runtime
  y el smoke local completo de 1.078 pruebas. Falta comparar fits ejecutados,
  métricas y artefactos entre ambos ejecutores antes de considerar cerrada la
  validación.
- El único worker se actualizó a `1.0.22` con el script oficial conservando
  `rainmapper-worker-data`, la identidad `worker_1a9a232c20fe2ee2` y sus
  cachés. Quedó `healthy`, `idle`, con GIS y Predictor válidos; el heartbeat se
  restauró tras el reinicio.
- HA `0.2.272` y worker `1.0.22` fueron la primera release de la unificación;
  el hotfix de HA vigente para instalar es `0.2.274`. El worker no necesitó
  bump y permanece en `1.0.22`.

- Workspace `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
- HEAD local y remoto antes del commit del hotfix: `71c818c`. El worktree
  contiene exclusivamente el hotfix/versionado HA `0.2.274`, sus pruebas y esta
  actualización documental.
- HA real tiene `0.2.273` instalada, según el usuario. La instalación de
  `0.2.274` queda en manos del
  usuario. El único worker confirmado es `rainmapper-worker:1.0.22`, con
  identidad `worker_1a9a232c20fe2ee2`.
- La opción real **Apply ML storage retention** permanece activa. No cambiarla,
  no borrar datos manualmente y no ampliar retención sin una decisión nueva.
- No se usó Tailscale. El `share` real se consultó solo en lectura para el
  diagnóstico. No se modificaron HA real, el worker ni sus datos desde Codex.

## Predictor 0.2.271: referencia histórica y límite aún vigente

- HA puede reutilizar un resultado Predictor persistido si coinciden
  exactamente worker, petición normalizada y fingerprint del runtime. Antes de
  renderizar verifica referencia externa, tamaño, SHA-256 y petición embebida.
  Un fallo de identidad, integridad o retención vuelve al flujo remoto normal.
- La UI muestra, alineados con la versión preferida, tiempo total del trabajo,
  tiempo de cálculo y si el resultado es nuevo o reutilizado.
- Validación real confirmada: repetición exacta con `Trabajo de predicción:
  0,6 s`, `cálculo <0,1 s` y `resultado reutilizado`. No se creó un segundo
  cálculo científico para ese hit.
- El usuario percibe todavía 6–8 s en caliente. La diferencia queda fuera del
  contador del trabajo; la hipótesis pendiente es transferencia y renderizado
  del HTML grande (la respuesta observada ronda 2 MiB y contiene detalle
  técnico plegado). No presentarlo como causa confirmada hasta medir navegador,
  ingress, tamaño transferido y render.
- Las consultas frías reales siguen alrededor de 35–40 s. Una medición anterior
  atribuyó unos 27,1 s al backend, principalmente 58 comparaciones; la siguiente
  optimización fría debe seguir la telemetría y no reintroducir cálculos de
  versiones o áreas fuera del contrato.
- Diseño de continuación:
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`.

## Fallo real anterior de Reconstruir y reentrenar operativo

Este apartado conserva el diagnóstico de la ejecución anterior. El alcance ya
está unificado y la cadena local `0.2.273` está validada; la siguiente cadena
real está autorizada y la inicia el usuario. Aquella ejecución no promocionó
modelos nuevos y los modelos operativos anteriores quedaron protegidos por la
promoción atómica.

Cronología persistida en
`/share/rainmapper/mushroom-data/mushroom_worker_jobs.json`:

| Trabajo | Job | Creado | Inicio worker | Fin | Resultado |
| --- | --- | --- | --- | --- | --- |
| Reconstrucción | `worker_job__jzW0-RdZtK6ddfO` | 04:41:46 | 04:45:41 | 04:52:08 | completo |
| ML v0 | `worker_job_X5QMGP-Z1hOzYgar` | 04:52:15 | 04:52:18 | 04:54:19 | completo |
| V2–V6 operativo | `worker_job_OuWNhJzwf9ZuGdgq` | 04:55:46 | 04:56:04 | 05:02:05 | fallido |

- Tiempo real desde la pulsación hasta el fallo: 20 min 19 s.
- La UI enseñó 6 min 27 s para reconstrucción y 2 min 1 s para ML v0 porque
  calcula desde `started_at`; ocultó 3 min 55 s previos al primer claim y 1 min
  27 s antes de crear V2–V6. Debe mostrar duración total desde `created_at` y
  duración de fase como magnitudes separadas.
- La fase inicial incluyó reconciliación SoilGrids y preparación del bundle. La
  atribución interna exacta no quedó persistida; no afirmar cuánto correspondió
  a SoilGrids, GIS, hashing o copia hasta instrumentarlo.
- El tercer trabajo mostró `Reusing sealed local inputs`: el handoff local
  sellado funcionó y evitó volver a descargar los inputs inmutables.
- Error completo del worker:

```text
KeyError: altitude_v2|fixed_gap_7d_altitude_v2|common_idw|
logistic_regression_reduced_v1|cantharellus_cibarius_sl
```

- El log del worker también registró que ML v0 había sido aceptado como
  completo por HA y después un intento de `finish` recibió HTTP 409 (`Worker
  job cannot finish from its current state`). La cadena continuó, por lo que no
  causó el fallo científico, pero es una carrera/retry que debe diagnosticarse.

## Causa confirmada: alcance local y remoto divergente

No había diferencia de observaciones:

- local y HA real contenían las mismas 15 observaciones de
  `cantharellus_cibarius_sl`;
- ambas producían 10 filas inicialmente elegibles;
- ML v0 remoto las agregó en 9 episodios área/fecha y omitió la especie porque
  el mínimo es 10 episodios.

La diferencia procede de dos implementaciones de orquestación dentro del mismo
source y de catálogos instalados distintos:

1. La ruta local usa `mushroom_local_full_update.eligible_training_species()`,
   que cuenta filas y seleccionó Cantharellus.
2. `mushroom_ml_trainer.run()` vuelve a decidir tras agregar episodios y puede
   omitir una especie antes seleccionada.
3. La cadena remota usa `linked_ml_trained_species_ids()` y selló las ocho
   especies realmente entrenadas por ML v0.
4. La preparación/hold-out V2–V6 recorrió de nuevo el snapshot completo,
   ignoró esas ocho especies y solicitó tuning para Cantharellus.
5. El lote real instalado `operational_20260825T221049Z` contiene ocho especies,
   636/636 fits y ninguna decisión para Cantharellus.
6. El lote local `local_operational_20260827T225123Z` contiene nueve especies,
   714/714 fits y sí contiene la clave exacta, por lo que enmascaró el defecto.

La solución acordada no es añadir una clave ni filtrar solo el caso observado.
Debe existir un único `OperationalTrainingScope`, calculado una vez después de
la agregación y los gates científicos, sellado con el snapshot y consumido por
local, HA y worker durante reconstrucción, ML v0, preparación, hold-out,
entrenamiento, verificación y promoción.

Especificación vinculante para la siguiente sesión:
`docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`.

## Fallo de la primera validación real de HA 0.2.273

La reconstrucción y ML v0 terminaron, con ocho especies entrenadas. El trabajo
operativo V2–V6 posterior falló al 20 % con:

`Operational preparation inputs do not match the sealed scope`.

La causa está confirmada en el código y no es una diferencia de observaciones:

- ML v0 remoto normalizaba el JSON de features para representar sus rutas
  finales, calculaba el scope sobre esa representación y la sellaba;
- V2–V6 recibía después el JSON original de la reconstrucción y `known-sites`
  vivo;
- el scope identifica el contenido canónico completo de ambos JSON, incluidas
  sus rutas de metadatos, por lo que el worker rechazó correctamente la mezcla;
- local no sufría el defecto porque scope, ML v0 y V2–V6 consumían el mismo
  `training-features.json` normalizado.

La corrección publicada en HA `0.2.274` captura, antes de la limpieza normal
del bundle de ML v0, los bytes exactos de `features.json` y
`known_sites.json`, comprueba sus digests sellados y los entrega a V2–V6.
Antes de construir el plan se vuelve a
validar que esos dos contenidos producen exactamente el scope certificado. No
se ha cambiado la retención ni se ha relajado ningún gate.

## Próximos pasos, en orden

1. Instalar HA `0.2.275` cuando el usuario lo decida; el worker local `1.0.24`
   ya está activo.
2. Después de la actualización meteorológica, repetir una única cadena real.
3. Al terminar, comparar scope, plan, 636 fits, métricas, artefactos,
   verificación y generaciones promocionadas frente al lote local
   `local_operational_20260828T101432Z`.
4. Ejecutar las mismas predicciones en HA y comparar resultados, fingerprint,
   frío/caliente, backend, transferencia y memoria con las mediciones locales.
5. Corregir después la telemetría/UI pendiente de tiempos de preparación,
   cola, claim, worker, verificación y transición.

## Riesgos y dudas activos

- **Política para especie nueva sin tuning:** sigue siendo una decisión
  científica abierta. Un fallback implícito comprometería reproducibilidad.
- **Equivalencia remota aún no demostrada:** HA `0.2.274` superó la preparación
  del scope y llegó al 90 % de V2–V6, pero la entrega terminó primero por timeout
  y después por un 409 de reentrega antes de verificación y promoción. Falta una
  cadena real completa con HA `0.2.275` y worker `1.0.24`.
- **Duraciones engañosas:** los contadores actuales excluyen preparación y
  transiciones; el presupuesto de 10 minutos se mide desde la pulsación hasta
  la promoción final.
- **SoilGrids/GIS sin atribución suficiente:** el trabajo dedicó 3 min 55 s
  antes del claim, pero no existe desglose persistido. Verificar también si el
  aviso de cuatro microáreas incompletas desapareció tras la reconciliación.
- **Carrera de finalización ML v0:** el cierre repetido con el mismo estado final
  es ahora idempotente; un retry que intente cambiarlo sigue rechazándose. La
  prueba local cubre ambos casos, pero no se ha revalidado en la nueva cadena
  real.
- **Predictor frío:** 35–40 s sigue lejos del objetivo de 10 s. El hit HA es
  correcto; quedan por separar cálculo frío y renderizado caliente.
- **Integridad:** conservar snapshots, hashes, cancelación, retry, rollback,
  promoción atómica y retención. No arreglar el fallo relajando gates.

## Validación y entrega ya completadas

- Release HA `0.2.275` y worker local `1.0.24`: 117 pruebas dirigidas de worker
  y transportes, 7 de empaquetado y smoke completo de 1.086 pruebas superados
  antes de los bumps mecánicos. La publicación necesitó reintentos por
  `DeadlineExceeded` y una cancelación solicitada al desconectar Internet; la
  ejecución final publicó ambos tags y se verificó el índice OCI y las dos
  arquitecturas. El worker quedó `idle`, con identidad, volumen y cachés
  conservados.
- Release HA `0.2.274`: handoff exacto ML v0→V2–V6; 271 pruebas del
  servidor HA y 49 pruebas transversales de scope, preparación, cola y ruta
  local; smoke completo de 1.082 pruebas superado. `0.2.274` y `latest`
  comparten el índice OCI
  `sha256:899d45f797952218ea865e40d3293247ab14d8d6f3e6e53ea7f807595f0fd001`
  con manifests `linux/amd64` y `linux/arm64`. El worker sigue en `1.0.22`.
- Release HA 0.2.271: 298 pruebas dirigidas de cola/coordinador/UI y smoke
  completo de 1.071 pruebas; compilación, etiquetas JSON y
  `git diff --check` correctos.
- La release añadió reutilización persistente exacta del Predictor y su
  telemetría visual. El worker permaneció en 1.0.21.
- El proceso local anterior, con su propia ruta divergente, midió 548,095 s
  (9 min 8,1 s), 714/714 fits y cero fallos. Es evidencia de rendimiento, no de
  equivalencia con la cadena remota.
- La retención ML real había ejecutado `mode=apply removed=74 errors=0` y siguió
  operativa. No repetir ni complementar con borrados manuales.

## Archivos relevantes

- Especificación inmediata:
  `docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`.
- Orquestación HA/local: `rainmapper-app/app/web_server.py`,
  `rainmapper_core/mushroom_local_full_update.py`.
- Alcance y ML v0: `rainmapper_core/mushroom_ml_trainer.py`,
  `rainmapper_core/mushroom_worker_jobs.py`.
- Preparación/evaluación V2–V6:
  `scripts/prepare-mushroom-ml-multiversion-inputs.py`,
  `scripts/evaluate-biology-v5-raw-benchmark.py`,
  `rainmapper_core/mushroom_ml_holdout.py`.
- Tuning: `rainmapper_core/mushroom_ml_tuning_catalog.py`,
  `rainmapper_core/mushroom_ml_runtime_trainer.py`.
- Worker/handoff: `rainmapper_core/mushroom_worker_service.py`,
  `rainmapper_core/mushroom_worker_transport.py`,
  `docs/mushrooms/mushroom-worker-chained-job-local-handoff-spec-es.md`.
- Predictor: `rainmapper-app/app/mushroom_predictor_ui.py`,
  `rainmapper_core/mushroom_predictor_service.py`,
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`.
- Autocura SoilGrids: `rainmapper_core/mushroom_soilgrids_reconciler.py`,
  `docs/mushrooms/mushroom-soilgrids-autocure-spec-es.md`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo para prioridades completas.
- Cumplir `AGENTS.md`: usar Codebase Memory MCP antes de descubrir o cambiar
  código y reindexar únicamente si el grafo conserva símbolos retirados.
- Comprobar `pwd`, rama y `git status`; preservar todos los cambios y ficheros
  no rastreados.
- Trabajar primero en el laboratorio local. No crear workers nuevos, no usar
  Tailscale, no tocar HA real ni el worker normal, no cambiar retención y no
  borrar datos.
- No ejecutar otra cadena real ni hacer bump, build, publicación, instalación o
  release sin autorización explícita nueva.
- Aplicar validación proporcional y terminar siempre con `git diff --check`.
