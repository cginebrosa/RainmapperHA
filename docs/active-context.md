# Active Context

Ventana operativa para continuar RainmapperHA. No reconstruir el estado actual
desde conversaciones, memorias ni informes históricos: revalidar siempre código,
datos y runtime. Las razones duraderas viven en `docs/decisions.md` y las
especificaciones temáticas enlazadas.

## Estado al cierre — 2026-08-18

- Prueba real posterior a instalar `0.2.260` y regenerar: el primer Predictor
  remoto terminó en 31 s (`worker_job_mT-fAwgl9nsH`) y materializó el runtime
  `sha256:5d828e31ef1f3165e5741b82419851dd51d0aaa33016fa5678c86c92fc1c398f`.
  Las dos consultas siguientes fallaron a los 27 s y 20 s porque el worker
  `1.0.12` solo evitaba el tar mientras existía el almacén transitorio de
  modelos recién entrenados; tras consumirlo ignoraba el runtime actual,
  descargaba otra vez el tar completo y este era rechazado por no coincidir
  con el manifiesto. Corrección local pendiente de nueva versión del worker:
  usar sincronización delta si existe runtime actual u objetos transitorios y
  recurrir al protocolo por fichero, con los mismos hashes, si el tar es
  inválido. No preparar ni publicar esa release sin autorización explícita.

- HA `0.2.260` publicada tras smoke completo de 894 pruebas. `0.2.260` y
  `latest` comparten el índice OCI
  `sha256:c9ad3fcc04f47d39f1bb6f9f0e848f34670e0af5c6eeaf9babb54e527f3e281a`,
  con manifests `linux/amd64`
  `sha256:35d685d57a7110ed49464f13889b7f1f93c9ea574176e9a4d61d149986b2f2c4`
  y `linux/arm64`
  `sha256:8667d0ee1f37dba8fc7edf253a7ddbad0956f28e23f2b25b922a88c3aae41cdf`.
  El worker privado no se publicó en ningún registro: su imagen local arm64
  `rainmapper-worker:1.0.12` quedó construida y validada con digest
  `sha256:451f8c9c706af37c527013f946428fe94142b352f79f9a31c1e2fd30112d8056`.

- Correcciones locales aún no publicadas tras la prueba real del Predictor
  remoto: (1) la vigencia ignora el hash binario de
  `mushroom_observation_features_v0.json`, porque es una salida derivada cuya
  promoción rebasa rutas privadas a rutas vivas, pero sigue comprobando sus
  entradas autoritativas; (2) la comprobación UI usa la identidad inmutable de
  la generación `weather-history` y no relee todos sus parquet; (3) el runtime
  remoto se transporta en un único tar verificado, con fallback al protocolo
  antiguo; (4) el worker conserva por SHA-256 los modelos v0/sombra/V2–V6 que
  acaba de producir y los enlaza a la caché Predictor antes de descargar.
  Evidencia real que motivó el cambio: runtime de 518 ficheros/143.698.035
  bytes; 464 modelos/96.055.695 bytes y transferencia redundante de 96.018.385
  bytes. El job frío tardó 607,695 s, con solo 16,831 s de backend Predictor;
  la consulta caliente posterior tardó 19,120 s.
- Estas correcciones no formaban parte de `0.2.259`; quedaron publicadas en HA
  `0.2.260` y construidas en el worker privado local `1.0.12` tras autorización
  explícita del usuario.
- Workspace verificado:
  `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- HA `0.2.258` está instalada. La regeneración real posterior confirmó la
  corrección de alcance: ML v0 entrenó 8 especies y el V2–V6 enlazado planificó
  436 fits, con 433 artefactos y únicamente las 3 no convergencias sparse-group
  conocidas.
- La activación manual de esa generación fue rechazada porque el runner
  programado `action=all` actualizó `weather-history/CURRENT.json` a las
  05:04:52 CEST, después de terminar V2–V6 a las 03:12:53 CEST. El control de
  frescura funcionó; el candidato ya no coincidía con las entradas vivas.
- Cambio local aún no publicado: al completar un V2–V6 enlazado, el coordinador
  inicia automáticamente la misma promoción completa, atómica y con rollback
  que antes exigía el botón. Fallos y trabajos no enlazados no se promocionan.
- La línea completa de corrección quedó registrada y enviada a `origin/inicial`
  en el commit `c5b51e8`. No limpiar, resetear, sustituir ni borrar datos vivos,
  cachés, artefactos o ficheros locales ajenos a Git.
- HA `0.2.257` fue instalada por el usuario. La primera regeneración real terminó
  sus tres jobs, pero la generación completa no se activó y no debe activarse:
  el V2–V6 encadenado volvió a planificar especies no entrenadas por ML v0.
  `0.2.257` y `latest` comparten el índice OCI
  `sha256:67a4d38890591adbc53bb441ff39ae2c9a544f5d78aefe45f74560daa4d86bc5`,
  verificado con manifests `linux/amd64`
  `sha256:7a06463088ee099da9e2c99f4097276f5385dbf11c066de01d2d3f56683613b6`
  y `linux/arm64`
  `sha256:d3db4a35f734fe23d36bce42b8f3587ff87fb602cd96b82bf3d12cf8852022fc`.
- El worker normal fue actualizado in situ a `1.0.11` sin cambiar su volumen
  persistente `rainmapper-worker-data`. Revalidado en
  `http://127.0.0.1:8110/health`: `healthy`, `idle`, identidad
  `worker_1a9a232c20fe2ee2`, caché GIS válida de 6.341.520.039 bytes y caché
  Predictor válida de 147.194.751 bytes. Imagen local
  `sha256:94466c8365b729e43df4329eae1702bd76a05bd72340f9372878f963381baa8d`.
- El worker real usa la dirección Tailscale de HA porque está fuera de la LAN.
  La prohibición operativa es que Codex no use Tailscale ni exponga SMB; no
  significa retirar o cambiar esa URL persistente del worker.
- Candidato real pendiente, sin activar: reconstrucción
  `worker_job_WhIQATkr6XU_S6nx`, ML v0 `worker_job_QmRb2Se7Gxwpq-FO` y V2–V6
  `worker_job_lpQr8P_ab4aFsha0`, batch `local_v2_v6_20260817T232733Z`.
  ML v0 entrenó 8 especies, pero V2–V6 recibió 16 y produjo 868 intentos:
  487 correctos y 381 fallidos. El alcance exacto de las 8 entrenadas habría
  producido 432 intentos: 429 correctos y las tres no convergencias sparse-group
  conocidas. No promover este candidato ni repetir todavía la regeneración real.
- Corrección publicada e instalada en HA `0.2.258`: el resultado ML guarda `trained_species` validado
  por HA y el job V2–V6 enlazado consume exactamente ese conjunto; si falta lo
  rechaza. Gate local: 241 pruebas dirigidas y smoke completo 886/886, incluidos
  fixtures, sintaxis y `git diff --check`. `0.2.258` y `latest` comparten el
  índice OCI `sha256:ccf54f9a4596a3bb15d7009fd8d92778874850c445a004d5a6b1db44a4966928`,
  con manifests `linux/amd64`
  `sha256:9c45b6b046b2529b7eda5ede51e8d77c2d245572dcd649da5be476632a34ff1b`
  y `linux/arm64`
  `sha256:18bc28f384b686b98a3344fcc9ea7f0c9c32485085c38607c30f1c3e5afa623c`.
  Commits publicados: corrección `bce180d`, release `be674d1`. El worker
  `1.0.11` es compatible y no necesita otro cambio.
- Ninguna V2–V6 está validada como preferida o ganadora. V2 alimenta la tarjeta
  histórica únicamente por orden cronológico. Todas siguen experimentales y
  deben mostrarse con calidad hold-out, aplicabilidad y cautelas propias.

## Corrección implementada localmente

- La regeneración ya no depende de JSON del laboratorio. Cada ejecución congela
  un snapshot fresco de observaciones, catálogos, mapeos GIS, histórico
  meteorológico y entradas auxiliares; el worker deriva de él V2–V6.
- La acción única `Reconstruir y reentrenar todo` mantiene tres pasos:
  reconstrucción común, entrenamiento ML v0 y lote comparativo V2–V6. No se ha
  añadido una acción parcial para el tercer paso.
- `lag_event` conserva un solo ajuste por especie + contrato + estimador; los
  horizontes 1/2/3/7 filtran las probabilidades del mismo hold-out y nunca
  reentrenan.
- Cada batch nuevo guarda `training-input-manifest.json`, con hashes e identidad
  de entrada pero sin datos brutos ni rutas privadas. El Predictor compara esa
  identidad con las entradas vivas y avisa si la generación está
  `stale`, `unknown` o `invalid`; solo omite el aviso cuando está `current`.
- La copia temporal recibida desde el worker se elimina solo después de una
  instalación íntegra y verificada. Si la instalación falla, queda retenida
  para diagnóstico.
- Las imágenes públicas se han reducido a código, dependencias y defaults. HA
  incluye una plantilla de observaciones vacía; no contiene observaciones,
  snapshots, hold-outs, benchmarks ni modelos entrenados. El worker tampoco
  incorpora esos datos.
- Especificación vinculante:
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.

## Runtime local restaurado y ejecutor HA local

- El montaje temporal que introducía el worker ficticio `Validación local`, HA
  en `8103` y worker en `8111` fue retirado. También se eliminó su volumen
  temporal; el worker normal y su volumen persistente no se modificaron.
- El HA local ordinario vuelve a ser `http://127.0.0.1:8101/`. Muestra el mismo
  registro de workers que el HA real, pero `M1 Personal` aparece desconectado
  porque el proceso normal del worker mantiene una única conexión saliente con
  el HA real de la RPi4. No se reempareja ni se cambia esa URL para usar el HA
  local.
- Se reintroduce una capacidad distinta y explícita para el laboratorio:
  `RAINMAPPER_LOCAL_HA_COMPUTE_ENABLED=true`. Solo
  `rainmapper-local/docker-compose.yml` la activa. El default de la imagen HA y
  el HA real permanece desactivado y coordinador-only.
- Cuando está activa, la UI ofrece `Home Assistant local`. El cálculo se ejecuta
  dentro del contenedor HA local sobre la CPU del M1, sin crear ni emparejar un
  worker. Encadena tres identidades de trabajo —reconstrucción, ML v0 y V2–V6—
  desde snapshots inmutables y realiza una única promoción del conjunto al
  final. Un fallo conserva la generación anterior y limpia el staging local.
- El camino ordinario de producción no cambia: el HA de la RPi4 coordina y el
  worker M1 ejecuta los mismos tres contratos. La UI y el backend no permiten
  promocionar la generación completa hasta que el V2–V6 enlazado haya terminado.
- La regeneración real por el ejecutor HA local terminó correctamente en
  18m45s. Encadenó las tres fases y activó una sola generación completa; el
  batch V2–V6 instalado es `local_v2_v6_20260817T171541Z`. La promoción local
  es automática al final de la cadena, no existe un botón posterior.
- Después de esa prueba se añadió progreso real dentro del tramo V2–V6 usando
  los contadores por fit que ya emite el trainer. El 58–90% muestra fits
  completados/planificados, versión, especie, éxitos y fallos; no simula tiempo.
- La preparación dinámica ya emitía ocho hitos y el worker remoto los publicaba,
  pero el ejecutor `Home Assistant local` los descartaba al lanzar el preparador
  sin `--progress-jsonl`. El camino local queda conectado al mismo JSONL: el
  50–58% informa paso y fase de V3/V4/V5/V6. Además reenvía los eventos internos
  ya disponibles: microáreas, cortes de área, comparación/dataset y split V6,
  aunque varios de esos eventos compartan porcentaje global. Los porcentajes
  representan fases y unidades terminadas, no una estimación de tiempo
  transcurrido o restante.
- La primera reconstrucción posterior al cambio V5/V6 v2 falló a los 23m12s y
  86%: el registro persistente del laboratorio aún declaraba V5/V6 v1 mientras
  el runtime solo materializaba v2. No hubo promoción y el descriptor anterior
  `local_v2_v6_20260817T171541Z` permaneció intacto. En este laboratorio de una
  sola instalación se alineó `docker-data` con los contratos v2. El runtime
  valida ahora la cobertura completa del plan antes de ajustar modelos y el
  ejecutor HA local hace esa prevalidación antes de iniciar la reconstrucción.
  En arranques posteriores, `ensure_seeded()` actualiza las definiciones de
  contrato desde la imagen conservando estados, historial y generaciones; una
  futura revisión contractual no requiere copiar el registro persistente a mano.
- La repetición posterior terminó y promocionó correctamente el batch
  `local_v2_v6_20260817T213901Z`, snapshot
  `sha256:c7e7b4f5e538604737bc4119c2acc7a4a7644c8f87b333d02caaee6bd8c369e3`.
  El manifiesto instalado valida contra el registro v2, contiene 487 artefactos
  de 868 fits planificados y conserva 381 fits fallidos: 378 por especies con
  una sola clase entrenable y tres por no convergencia sparse-group. Edulis
  dispone de ambos contratos en V2–V6; V5 usa
  `raw_primary_plus_physical_state` y V6 `smooth_weather_physical_state`.
  `runtime-batch.json`, catálogo de calidad y manifiesto de entradas quedaron
  instalados; `.local-full-update` quedó vacío.
- El desglose posterior corrigió una interpretación inicial: nueve especies
  aportan artefactos por especie, no tres. Siete especies con solo 1–4 filas
  elegibles, todas favorables, entraron indebidamente porque V2–V6 usaba la
  selección general de la UI en vez de `trained_species`; sus 54 fits por
  especie explican los 378 rechazos. La planificación queda corregida para usar
  solo especies con al menos diez filas y ambas clases. Las tres no
  convergencias restantes son únicamente V5 lag sparse-group de Amanita
  caesarea, Boletus aereus y Lactarius deliciosus; sus demás artefactos existen.
- El Predictor resume antes del detalle cuatro niveles: utilizables en dominio
  que mejoran prevalencia, evidencia débil, extrapolaciones/no utilizables y
  abstenciones meteorológicas. Para la consulta Edulis/Salteguet/2026-08-20 se
  verificaron 11/7/55/72 miembros respectivamente. Los 72 no son fallos de
  modelos: h1–h3 requieren cortes meteorológicos 17–19 de agosto aún incompletos
  en la copia local; h7 dispone de 21/21 días. El texto técnico
  `runtime_feature_gates_failed` ya no se muestra y el detalle queda plegado.
- La imagen local final está reconstruida y el contenedor canónico está mapeado
  en `8101`. El smoke final pasó 863 pruebas; compilación Python/JS/shell,
  fixtures y `git diff --check` pasaron. La auditoría confirmó cero modelos
  entrenados y cero datasets generados en las imágenes; HA solo lleva una
  plantilla de observaciones vacía. No se publicó ni versionó nada.
- El batch `local_v2_v6_20260817T171541Z` está `current/inputs_match`; su
  manifiesto coincide con el SHA-256 registrado
  `53cdbf1dda9ea2d9e56ed155737c79f6047ff38ede36a2f5ab44de580d92de8f`,
  declara `operational_candidate_trained=false`, no referencia el snapshot
  antiguo y dejó vacío `docker-data/.local-full-update`.
- Sus 244 artefactos `lag_event` tienen horizontes `[1,2,3,7]`, sin claves
  duplicadas por versión, especie, contrato, perfil y estimador.

## P0 cerrado localmente — detenerse antes de release

1. La fila «Ventana ciega fija de 7 días» pertenecía al comparador legado
   `MushroomModelComparator`, alimentado por
   `nearest_station_single_source_daily`; no era el miembro V2 `common_idw` del
   batch. Sus 18 episodios frente a 20 procedían de dos huecos de la estación
   única; el IDW común recupera ambos. La tarjeta resuelve ahora exclusivamente
   los artefactos V2 instalados del batch y no degrada al comparador legado.
2. MapLibre contaba soporte de lluvia por valor truthy y descartaba `0.0`; N/A
   sí debe excluirse. La corrección cuenta ceros finitos con su peso IDW y
   mantiene N/A fuera. La prueba de regresión está en `tests/test_maplibre_idw.py`.
3. V5/V6 anteriores no cumplían la intención de «todas las variables». Los
   contratos v2 materializan por microárea estaciones habilitadas → IDW → ET0,
   balance y SMI → agregado de área. V5 usa ocho canales diarios y estados
   escalares; V6 suaviza los ocho y conserva los escalares. El Predictor usa la
   misma ruta y el runtime remoto empaqueta `stations.txt` para conservar las
   fuentes habilitadas.
4. Validación: 54 pruebas dirigidas, suite completa 871/871, smoke completo y
   `git diff --check` verdes. Una construcción real desechable materializó V5
   v2 para 593 área/corte (395 muestras fixed y 1.580 lag); se detuvo la
   reevaluación exhaustiva posterior para no gastar CPU/tokens innecesarios.
5. Próximo paso: detenerse e informar. Preparar o publicar una release requiere
   autorización explícita nueva.

La secuencia de entrega acordada separa riesgos:

1. Primera entrega urgente HA+worker: corrección V2–V6, manifiesto, promoción
   completa, limpieza, resumen del Predictor y progreso del ejecutor local.
2. Release posterior solo del worker: multicoordinador completo, probado antes
   con dos HAs locales aislados.
3. Release HA posterior únicamente si hace falta añadir la protección `409`
   durante una revocación con job activo. El resto del worker multicoordinador
   debe conservar compatibilidad con el HA publicado en el primer paso.

## Evolución acordada, todavía no implementada

- El worker externo evolucionará de una única URL/token a varias asociaciones
  de coordinador independientes. Esto permitirá que el mismo M1 permanezca
  emparejado con el HA real y el HA local sin sustituir la URL existente ni
  crear un worker temporal.
- Seguirá existiendo un único `worker_id`, volumen, caché y slot global de
  ejecución. Los heartbeats serán independientes y los claims se arbitrarán de
  forma justa; cada job y sus resultados permanecerán ligados al coordinador
  de origen.
- El máximo se persistirá como parámetro configurable `max_coordinators`, con
  default 4; no será una constante rígida. Revocar desde un HA eliminará su
  credencial server-side y el worker purgará solo esa asociación al recibir un
  `401` inequívoco en el ciclo siguiente. Fallos de red o `5xx` no borrarán
  credenciales.
- El diseño completo y sus pruebas de aceptación están en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`. No está
  implementado en worker `1.0.10` y no autoriza cambios en el M1 o HA reales.

## Investigación ML ya cerrada para este gate

- V5 conserva 12.280 predicciones hold-out fila a fila y el análisis de falsos
  positivos/negativos compartidos. Gana 2 y pierde 32 de 34 comparaciones contra
  el mejor miembro V2/V3/V4. No respalda dos ventanas meteorológicas estables ni
  un estado temporal; queda experimental.
- V6 probó curvas suaves por especie, una curva compartida y pooling parcial.
  Gana 4 y pierde 30 de 34 contra el mejor V2/V3/V4/V5. No justifica ahora un
  jerárquico general ni cambiar el Predictor.
- No añadir otra familia ni un ensemble en este gate. Un ensemble futuro debe
  superar al mejor miembro individual por especie y contrato. Nunca usar Brier
  medio entre especies.
- Informes vigentes:
  - `docs/reports/V2_V3_V4_V5_raw_weather_report001.md`;
  - `docs/reports/V2_V3_V4_V5_V6_smooth_hierarchical_report001.md`;
  - `docs/reports/V2_V3_V4_consensus_report002.md`.

## Riesgos y dudas activos

- El Predictor local dejó de repetir la validación del manifiesto de 487
  artefactos y la carga de bundles dentro de una misma petición. La consulta de
  referencia medida bajó de 116,011 s en caliente a 13,185 s; el cambio al día
  siguiente dentro del mismo proceso tardó 12,435 s. El smoke completo pasó
  881 pruebas y `git diff --check` quedó limpio. La imagen HA local se
  reconstruyó después sin tocar HA real ni el worker normal: el endpoint en
  `127.0.0.1:8101` devolvió `200`, con 22,992 s para 2026-08-18 y 16,184 s para
  2026-08-19 ya en caliente; los logs no mostraron errores de aplicación.
- La pestaña «Por especie» reveló primero un `UnboundLocalError`: `_render_week`
  conservaba una referencia copiada a la variable `area`, inexistente en esa
  vista. Tras retirarla, la cuadrícula aún tardaba unos siete minutos porque
  reconstruía 14 ventanas solapadas por área. El runtime prepara ahora una sola
  serie IDW de 96 días por área y corta de ella las 8 fechas de corte únicas de
  la semana. En el HA local reconstruido, Edulis devolvió tabla HTTP `200` de
  349.019 bytes en 26,013 s, sin la excepción. El smoke posterior pasó 883
  pruebas y `git diff --check` quedó limpio.
- La ventana runtime queda ligada al contrato: V2/V3 actuales 90 días IDW sin
  estado físico; V4 90 días y físicos solo en perfiles que los declaran; V5/V6
  mantienen 365 días mediante la constante canónica
  `mushroom_ml_raw_weather.LOOKBACK_DAYS`. No se ha retirado balance/SMI de
  V2/V3 como posibilidad: queda preservada y probada la activación por un futuro
  perfil explícito `IDW + estado físico`, que deberá entrenarse y compararse
  separadamente.
- Los resultados actuales no autorizan concluir que 365 días «no sirven».
  V5/V6-365 queda intacto como control reproducible; queda pendiente un nuevo
  V5/V6-90 emparejado sobre las mismas filas y splits para medir específicamente
  la aportación de los días 91–365.

- [CERRADA] El falso vacío MapLibre descartaba ceros finitos al contar soporte;
  N/A se excluye y no propaga `NaN`.
- [CERRADA] `model_not_trained` pertenecía al bundle legado de estación única,
  con 18 episodios elegibles; el batch V2 común IDW es otro artefacto.
- La instalación real sigue sin la corrección V2–V6. No afirmar que su Predictor
  incorpora toda la información disponible.
- Los batches anteriores no tienen identidad de entrenamiento; su vigencia debe
  mostrarse como no verificable, no asumirse actual.
- La prueba larga puede rondar 20 minutos y el coste crecerá mientras V2–V6
  sigan activas. Reducir versiones en el futuro reducirá el coste.
- El soporte por especie/campaña sigue siendo pequeño. V5/V6 y cualquier ranking
  son diagnósticos, no promoción ni causalidad.
- El worktree mezcla muchos bloques. Revisar el alcance antes de commit/release
  y preservar los PDF científicos no rastreados.
- La imagen ya no copia observaciones, pero el repositorio público sigue
  rastreando `mushroom-data/mushroom_observations.json` con datos semilla. No se
  modificó en esta sesión. Revisar privacidad por separado antes de asumir que
  el repositorio completo carece de observaciones.
- La autocuración meteorológica y la reparación histórica amplia siguen sin una
  validación de producción independiente de esta corrección multiversión.

## Archivos relevantes

- Continuidad: `docs/codex-start-here.md`, este documento y `docs/todo.md`.
- Decisiones y arquitectura: `docs/decisions.md`, `docs/architecture.md`.
- Runtime: `rainmapper-app/app/web_server.py`,
  `rainmapper_core/mushroom_worker_jobs.py`,
  `rainmapper_core/mushroom_worker_service.py` y
  `rainmapper_core/mushroom_worker_transport.py`.
- Snapshot/training: `rainmapper_core/mushroom_rebuild_snapshot.py`,
  `scripts/prepare-mushroom-ml-multiversion-inputs.py` y
  `scripts/run-mushroom-ml-multiversion-job.py`.
- Instalación/validación del batch:
  `rainmapper_core/mushroom_ml_model_catalog.py` y
  `rainmapper_core/mushroom_ml_multiversion_transport.py`.
- Vigencia/UI: `rainmapper_core/mushroom_ml_training_freshness.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py`,
  `mushroom-data/mushroom_labels.json`.
- Diagnóstico IDW: `rainmapper_core/viewers/maplibre-viewer/app.js`, funciones
  `estimatedFieldUsableFeatures`, `estimateFieldCellValue`,
  `estimatedFieldPointMetricValue` y `buildIdwPointValues`.
- Empaquetado: `rainmapper-app/Dockerfile`, `rainmapper-worker/Dockerfile` y
  `rainmapper-app/defaults/mushroom_observations.json`.
- Pruebas principales: `tests/test_mushroom_ml_training_freshness.py`,
  `tests/test_mushroom_ml_multiversion_transport.py`,
  `tests/test_mushroom_worker_jobs.py`,
  `tests/test_mushroom_worker_transport.py` y
  `tests/test_mushroom_worker_packaging.py`.

## Reglas para continuar

- Leer primero `docs/codex-start-here.md` y este documento; `docs/todo.md` solo
  si hacen falta prioridades completas.
- Comprobar `pwd`, rama y `git status`; preservar todos los cambios y no usar
  comandos destructivos.
- Consultar Codebase Memory MCP antes de descubrir o cambiar código.
- Responder siempre a los mensajes del usuario mientras se trabaja.
- Codex no usa Tailscale. No cambiar la URL Tailscale persistida del worker real
  sin orden explícita.
- No tocar HA real, worker normal, GHCR ni releases durante la prueba local.
- Tras superar el gate local, detenerse e informar. Preparar o publicar releases
  exige una nueva autorización explícita del usuario y seguir
  `docs/release-flow.md`.
