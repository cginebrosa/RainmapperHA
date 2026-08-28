# Decisions

## 2026-08-29 - [VIGENTE][RELEASE] HA 0.2.279 publicada y worker local 1.0.29

- HA `0.2.279` y `latest` comparten el índice OCI
  `sha256:da7a0d034e22542a4f95c01fc02e68cdd0474212f624793f2b35390012941967`,
  con manifests `linux/amd64` y `linux/arm64`.
- El worker privado se reconstruyó como `1.0.29`, conservando la identidad
  `worker_1a9a232c20fe2ee2`, el volumen `rainmapper-worker-data` y las cachés GIS
  y Predictor válidas.
- La preparación del job multiversión se persiste antes de materializar sus
  inputs, de modo que el trabajo previo deja de ser un intervalo invisible en
  la UI.
- Cada generación operativa nueva persiste su catálogo de tuning y la siguiente
  cadena lo valida por manifest y hash, evitando releer y deserializar todos los
  modelos instalados. Las generaciones antiguas conservan el fallback completo.
- El fallo real del último entrenamiento no ocurrió durante los fits: al acabar
  el cálculo, HA rechazó el primer TAR con `404: Not found.` porque
  `/api/mushrooms/workers/jobs/multiversion-result-bundle` no figuraba en la
  allowlist del listener dedicado. `0.2.279` permite esa ruta y añade una prueba
  centinela.
- Validación definitiva: smoke completo con 1.099 pruebas y todos los
  validadores, 295 pruebas dirigidas de protocolo/resultados, siete pruebas de
  empaquetado y `git diff --check` correcto.

## 2026-08-29 - [VIGENTE][RELEASE] HA 0.2.278 publicada y worker local 1.0.28

- HA `0.2.278` y `latest` comparten el índice OCI
  `sha256:f793d2f75bc1ead6924efe61a4aedac179ba4385294ee6a0f14f388b0b7f534c`
  con manifests `linux/amd64` y `linux/arm64`.
- Los snapshots encadenados reutilizan por hardlink los inputs inmutables. La
  entrega multiversión usa gzip acotado, expone `Uploading` antes de transferir
  y reanuda desde recibos por ruta sin reenviar objetos ya verificados.
- El worker privado se reconstruyó como `1.0.28`, conservando identidad
  `worker_1a9a232c20fe2ee2`, volumen `rainmapper-worker-data` y cachés GIS y
  Predictor; quedó `idle`.
- El smoke definitivo pasó 1.096 pruebas y todos los validadores; después de
  los bumps mecánicos pasaron siete pruebas de empaquetado. La instalación de
  HA y cualquier entrenamiento real quedan en manos del usuario.

## 2026-08-28 - [REEMPLAZADA][RELEASE] HA 0.2.277 publicada y worker local 1.0.27

- HA `0.2.277` y `latest` comparten el índice OCI
  `sha256:a1a1b5da33bb4a2155b2d73c4bc0f0c82ed797b532637874e020fce9f85402b4`
  con manifests `linux/amd64` y `linux/arm64`.
- Agrupa los resultados multiversión en TAR sin compresión de hasta 16 MiB,
  conserva fallback para ficheros grandes, valida cada miembro y reutiliza
  recibos ligados a la identidad del fichero. La promoción usa identidad de
  generación meteorológica y ocho checkpoints persistentes.
- El worker privado se reconstruyó como `1.0.27`, conservando identidad
  `worker_1a9a232c20fe2ee2`, volumen `rainmapper-worker-data` y caches GIS y
  Predictor; quedó `healthy` e `idle`.
- El smoke definitivo pasó 1.092 pruebas y todos los validadores. La instalación
  de HA y el entrenamiento real quedan en manos del usuario.

## 2026-08-28 - [REEMPLAZADA][RELEASE] HA 0.2.276 publicada y worker local 1.0.25

- HA `0.2.276` y `latest` comparten el índice OCI
  `sha256:70013bb4d17dfca0ec46652398da39119c00e9e78790dd4941b71f5692635b36`
  con manifests `linux/amd64` y `linux/arm64`.
- Su instalación en HA real queda en manos del usuario y no está confirmada al
  cierre. La última versión confirmada allí es `0.2.275`.
- El único worker es privado y local al M1; no se publica en GHCR. Se reconstruyó
  como `1.0.25` conservando identidad `worker_1a9a232c20fe2ee2`, volumen y
  cachés, y quedó `healthy` e `idle`.
- La release pasó, antes de los bumps mecánicos, 49 pruebas dirigidas, 327 de
  integración, siete de empaquetado y el smoke completo de 1.089 pruebas.
  Commit publicado: `8085e464fdca686cc57c2026163ac08d8cdb6374`.

## 2026-08-28 - [VIGENTE][ML] La identidad del scope representa ciencia, no envolturas de artefacto

- Features se identifican por las filas científicas ordenadas. Known-sites se
  identifica por su contenido científico omitiendo recursivamente solo
  `generated_at` y `updated_at`.
- Rutas, timestamps de generación y timestamps de reconciliación no pueden
  cambiar el scope si el contenido científico es idéntico. Una feature, altitud
  u otro valor científico distinto sí debe invalidarlo.
- Esta decisión corrige una divergencia comprobada: local y HA tenían las mismas
  439 filas y contenido científico, pero producían scopes distintos por sus
  metadatos volátiles.
- Con los inputs reales actuales ambas rutas producen el scope
  `sha256:47d934d7c4fadde8b533efc35964b833d4e0f9710ee1dc4cebc4e4275830ec07`.

## 2026-08-28 - [VIGENTE][WORKER] Telemetría no bloqueante y entrega final recuperable

- Control y progreso se desacoplan del callback científico mediante un único
  intercambio en segundo plano, coalesciendo el último progreso y limitando la
  cadencia normal. Un timeout de telemetría no aborta ni serializa el cálculo.
- Una vez calculado un resultado, la entrega se reintenta hasta recuperar al
  coordinador o recibir cancelación. HA acepta como idempotente una reentrega
  byte a byte idéntica y rechaza con conflicto cualquier contenido distinto.
- No se generaliza una espera infinita a todas las comunicaciones: claim,
  descargas e inicio conservan sus límites para no introducir una cola
  persistente ni una máquina de estados más compleja.

## 2026-08-28 - [VIGENTE][UX] Tiempo y porcentaje inexactos permanecen como deuda de observabilidad

- La UI actual pierde preparación y pausas entre jobs, y presenta porcentajes
  internos de fase como si fueran progreso total; por eso el porcentaje puede
  retroceder.
- La corrección queda en TODO. No bloquea entrenamiento ni Predictor y no existe
  evidencia de que el contador visual reduzca el rendimiento científico.
- Hasta corregirla, medir una cadena con hora de pulsación y promoción final;
  no usar la suma de duraciones mostradas ni el porcentaje como ETA integral.

## 2026-08-28 - [REEMPLAZADA][RELEASE] HA 0.2.272 publicada y worker 1.0.22 instalado

- HA `0.2.272` está publicada en GHCR. `0.2.272` y `latest` comparten el índice
  OCI `sha256:d54ec58efa88b01c650d9c1f6a23fc754419d491e0856365a58cd1fad52d433a`
  y contienen manifests `linux/amd64` y `linux/arm64`.
- El único worker se actualizó a `1.0.22` con el script oficial y el volumen
  `rainmapper-worker-data`. Conservó la identidad
  `worker_1a9a232c20fe2ee2`; quedó `healthy`, `idle`, con GIS y Predictor
  válidos y heartbeat restaurado.
- Antes del bump pasó el smoke completo de 1.078 pruebas; después, 301 pruebas
  dirigidas de scope, worker, empaquetado y HA. No se tocó HA real, el worker
  normal, la retención ni los datos reales.
- La instalación de HA y los entrenamientos comparativos quedan pendientes de
  las acciones del usuario. Hasta su confirmación, el estado HA conocido sigue
  siendo `0.2.271`; el worker está confirmado en `1.0.22`.

## 2026-08-28 - [VIGENTE][ML] Un único alcance sellado gobierna local, HA y worker

- El conjunto de especies operativo se calcula una sola vez, después de la
  agregación canónica de episodios y de todos los gates científicos. El
  resultado incluye admitidas, excluidas y motivos, y queda sellado con el
  snapshot y el plan.
- Reconstrucción, ML v0, preparación, hold-out, tuning, entrenamiento,
  verificación y promoción deben consumir ese alcance exacto. Ningún paso puede
  redescubrir especies recorriendo de nuevo las observaciones.
- La ruta local ejecutará el mismo plan serializable que la ruta HA/worker. La
  diferencia permitida es el transporte, no el contenido científico ni la
  selección.
- Antes del trabajo pesado se comprobará que el catálogo de tuning cubre todo
  el alcance. Una carencia es visible y preserva los modelos vivos; no autoriza
  decisiones implícitas ni una promoción parcial.
- Diseño vinculante:
  `docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`.

## 2026-08-28 - [REEMPLAZADA][ML] Compartir source y scripts garantizaba equivalencia local/remota

- La ejecución real demostró que compartir repositorio, primitivas y scripts no
  basta: `mushroom_local_full_update` decidió por filas, ML v0 volvió a decidir
  por episodios y V2–V6 recorrió otra vez el snapshot.
- Catálogos instalados diferentes ocultaron localmente el defecto. La sustituye
  la decisión de alcance y plan únicos; una validación local solo prueba la ruta
  remota cuando ambas ejecutan ese mismo plan sobre idénticos inputs y catálogo.

## 2026-08-28 - [DUDA][ML] Alta de una especie elegible sin tuning congelado

- Falta decidir si una especie recién elegible exige benchmark previo o puede
  entrar mediante una configuración base explícita y versionada.
- Hasta resolverlo no se copiará tuning de otra especie ni se sintetizará un
  fallback. El preflight debe exponer el hueco y preservar la generación viva.

## 2026-08-28 - [VIGENTE][PREDICTOR] HA reutiliza únicamente resultados exactos persistidos

- La clave liga worker, petición normalizada y fingerprint del runtime. Antes
  del uso se verifican referencia externa, tamaño, SHA-256 y petición embebida;
  cualquier discrepancia ejecuta el camino remoto normal.
- Se conserva la retención existente y la UI distingue trabajo, cálculo y
  resultado reutilizado. En HA real 0.2.271 se observó un hit de 0,6 s con
  cálculo inferior a 0,1 s.

## 2026-08-28 - [VIGENTE][TELEMETRÍA] El presupuesto operativo empieza en created_at

- Los 10 minutos se miden desde la pulsación/creación hasta la promoción final,
  no desde que el worker reclama cada job.
- La UI debe separar duración total, espera/claim y duración de fase. La cadena
  fallida ocultó 3 min 55 s antes del primer claim y 1 min 27 s entre ML v0 y
  V2–V6 al mostrar solo tiempos desde `started_at`.

## 2026-08-28 - [REEMPLAZADA][RELEASE] HA 0.2.271 instalada; worker 1.0.21 conservado

- HA 0.2.271 está instalada en HA real según confirmación del usuario; el
  worker normal observado es 1.0.21 y conserva su identidad y volumen.
- `0.2.271` y `latest` comparten el índice OCI
  `sha256:31c53e089935804892d057c3ef01470de7e5dd0abde3db1d7a34ddc1e64d6bfd`
  con manifests `linux/amd64` y `linux/arm64`; commit `29aca9c`.
- Antes de la release pasaron 298 pruebas dirigidas y el smoke completo de
  1.071 pruebas. La release incorpora reutilización exacta persistida del
  Predictor y telemetría visual; no modifica la retención.

## 2026-08-27 - [REEMPLAZADA][RELEASE] HA 0.2.267 y worker privado 1.0.18

- La optimización local de `Reconstruir y reentrenar operativo` queda entregada
  sin relajar hashes, cancelación, retry, rollback ni promoción atómica. El
  recorrido completo midió 534,571 s en frío y 473,654 s en caliente, con
  714/714 ajustes, cero fallos y equivalencia de artefactos; el detalle y la
  telemetría por fase están en
  `docs/reports/operational-rebuild-10m-lab-2026-08-26.md`.
- El smoke definitivo previo al bump pasó 1.035 pruebas en 53,394 s, además de
  compilación y validadores. Después del bump pasaron las siete pruebas de
  empaquetado dirigidas y `git diff --check`.
- `ghcr.io/cginebrosa/rainmapperha:0.2.267` y `latest` comparten el índice OCI
  `sha256:5efdf1cacdf98e6fb6f402fa2731792cda3091c7a61b0853c0873b2a5b88fe9c`,
  verificado con manifests `linux/amd64` y `linux/arm64`.
- El worker normal fue recreado como `1.0.18` sobre el volumen externo
  `rainmapper-worker-data`. Conservó la identidad
  `worker_1a9a232c20fe2ee2`, los fingerprints de dataset y Predictor, y quedó
  `healthy`, `idle`. La imagen local arm64 tiene ID
  `sha256:2aeaaeab26802c25f0511ca0e44342429a66a52476108db8a7e667c515fbfdfe`.
- El paquete privado `~/Desktop/RainmapperWorker-1.0.18/` contiene un TAR arm64
  de 293 MiB con SHA-256
  `7af6d4ce271bb97d040b9604c0a889f5e601233b7bbd244203f56ad4ab764c34`;
  no contiene ni modifica el volumen persistente.
- HA real no fue instalado ni probado, no se lanzó trabajo contra él, no se usó
  Tailscale, no se cambiaron opciones de retención y no se borraron datos.
- La entrega de código y documentación quedó publicada en `origin/inicial` con
  el commit `4b6422d`.

## 2026-08-23 - [VIGENTE][PARCHE] HA 0.2.265 migra de forma respaldada el registro ML 1.0

- La instalación HA de `0.2.264` encontró el registro persistente creado por
  `0.2.263` con esquema 1.0. El seeding rechazó el esquema antes de escribir y
  el reconciliador quedó en `dry-run`, `removed=0`, `errors=1`; el usuario
  detuvo el add-on. No se ejecutó `apply` ni se borraron datos.
- `0.2.265` valida la estructura legacy, conserva todas sus generaciones,
  convierte únicamente el objetivo operacional explícito en generación
  instalada/preferida y guarda antes una copia byte a byte
  `mushroom_ml_version_registry.schema-1.0.backup.json`. Si no puede demostrar
  una migración segura, no modifica el registro original.
- Pruebas dirigidas: 278 correctas. Smoke definitivo: 1.006 pruebas y todos los
  validadores correctos. `git diff --check`: correcto.
- `0.2.265` y `latest` comparten el digest multiarch
  `sha256:f0c2fee0a90ac365d36cdfd05412475a0357b9483d45648efed46cfbefc511ba`;
  commit publicado `a14560b`. El worker permanece en `1.0.17` y no se
  reconstruyó ni reemparejó para este parche.
- Pendiente: validar el arranque en HA con `mode=dry-run removed=0 errors=0` y
  revisar el informe antes de cualquier autorización de `apply`.

## 2026-08-23 - [REEMPLAZADA][RELEASE] HA 0.2.264 y worker 1.0.17 publicados sin instalación HA

- El usuario autorizó publicar conjuntamente el bloque transversal validado.
  El smoke definitivo previo al bump pasó 1.003 pruebas en 48,411 s, además de
  compilación, validadores de sintaxis/fixtures y `git diff --check`.
- `ghcr.io/cginebrosa/rainmapperha:0.2.264` y `latest` comparten el índice
  multiarch
  `sha256:3835fa0fe59889873386661f31e1823a77a0b174ef89d8e6772ae14efa195dc5`,
  con manifests `linux/amd64` y `linux/arm64`. El commit `ea75d95` está
  publicado en la rama `inicial`.
- El worker normal se reconstruyó como `1.0.17` reutilizando el volumen externo
  `rainmapper-worker-data`; conservó `worker_id: worker_1a9a232c20fe2ee2`,
  quedó sano e idle y el usuario confirmó que HA lo ve. La imagen local
  `1.0.16` se retiró solo después de esa comprobación; no se tocó el volumen.
- El paquete privado arm64 contiene el TAR con SHA-256
  `90e4ce8abd2ddbdda7df0e820d3e2710c76cebe2c43485badf88134fe02e0df8`.
- La imagen HA no se instaló ni probó en HA real. No se usó Tailscale, no se
  borraron datos y `ml_storage_reconciliation_apply` permanece deshabilitado.
  La instalación y cualquier `apply` requieren autorizaciones posteriores y
  separadas.

## 2026-08-23 - [OBSOLETA][ML] Benchmark como candidata instalable y rollback manual por versión

- Queda retirada la arquitectura en la que un benchmark se archivaba como
  candidata completa, se preparaba, activaba y revertía manualmente desde la
  UI. También quedan obsoletos su módulo específico, handlers públicos,
  `ml_models/candidates` y `promotion-history` como estados operativos vivos.
- La sustituyen dos flujos: mantenimiento completo autopromocionado para las
  versiones instaladas y benchmark científico compactado a evidencia no
  instalable. El rollback que permanece es transaccional durante instalación y
  el único backup del rebuild completo, no una acción del historial científico.
- Los documentos que describen la promoción genérica anterior se conservan
  como diseño histórico y deben leerse con su nota de reemplazo.

## 2026-08-23 - [VIGENTE][ALMACENAMIENTO ML] Auditoría automática primero; borrado solo mediante gate explícito

- La caché TAR del Predictor es regenerable y vive fuera de `/share`, en
  `/media/rainmapper/runtime-cache/predictor-runtime-archives`; GIS/DEM continúa
  separado en `/media/rainmapper/mushroom-GIS`.
- Un reconciliador común calcula primero un plan y solo aplica eliminaciones si
  `ml_storage_reconciliation_apply` está activado. Su valor predeterminado es
  `false`; por tanto, el primer arranque del add-on Rainmapper y los hooks del
  ciclo de vida escriben diagnóstico `dry-run`, no limpian datos.
- La instalación conserva rollback transaccional mientras está en curso y un
  único backup del rebuild completo después. Solo quedan protegidos de forma
  permanente los batches referenciados por una generación instalada.
- Todo benchmark verificado se compacta inmediatamente a `evidence_only`; no
  existe ya un candidato operativo derivado del benchmark. Los resultados
  pesados de ejecuciones operativas fallidas, canceladas o interrumpidas se
  conservan 24 horas, y los payloads del Predictor los últimos 10 o las últimas
  24 horas, lo que proteja más.
- La implementación y las pruebas locales no autorizan migración, instalación,
  build o release. Evidencia y estado exacto:
  `docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`.

## 2026-08-23 - [VIGENTE][HISTÓRICO METEO] Promover solo una generación oficial reparada, compacta y sin pérdida

- La generación de HA descargada el 23 de agosto no contenía la reparación
  oficial auditada: AEMET carecía de humedad en 2012–2025 y Meteocat mantenía
  particiones dispersas después de 2016. El IDW consumía correctamente esa
  entrada, pero no podía recuperar métricas inexistentes.
- La promoción manual debe reemplazar únicamente `weather-history`, con
  Rainmapper detenido. Los CSV diarios vivos permanecen en HA y el primer
  runner posterior debe ejecutarse manualmente tras verificar la generación.
- La entrega válida está en
  `docker-data/audits/ha-weather-history-check-20260823/ready-to-upload-final/weather-history`.
  Sus objetos activos contienen 46 particiones, 5.480.224 filas y 49.590.594
  bytes. Tras detectar que el primer manifiesto compacto conservaba una
  referencia a un predecesor no entregado, `CURRENT` se rebasó de forma
  verificada a la raíz `20260823T003617919308Z-58903f62a763`, con los mismos
  objetos y `previous_generation_id: null`.
- Una entrega autosuficiente que omite generaciones históricas debe publicar
  una raíz independiente; no debe conservar referencias a manifiestos no
  incluidos ni restaurar objetos antiguos solo para satisfacer la poda. La
  corrección mínima para una instalación que ya tiene los objetos está en
  `ready-to-upload-root-fix/weather-history` y se aplica manifiesto primero,
  `CURRENT.json` al final.
- AEMET y Meteocat superan la puerta de cero claves antiguas perdidas;
  Wunderground y Meteoclimatic conservan exactamente sus objetos de HA. El
  preparador ML recupera las 374 observaciones con target operativo.
- Una reconstrucción masiva no se promoverá directamente si el merge vuelve a
  materializar grupos de 128 filas. Debe corregirse el escritor o compactarse
  transaccionalmente a la granularidad contractual de 8.192 filas, verificando
  igualdad lógica y todos los hashes antes de activar el resultado.
- Evidencia:
  `docs/reports/mushroom-weather-history-repair-audit-2026-08-23.md`.

## 2026-08-23 - [VIGENTE][ML] Selección operativa, fiabilidad, consenso y aplicabilidad son contratos separados

- Ventana fija y retardo/evento eligen ganadores independientemente. Los gates
  son disponibilidad/probabilidad válida, aplicabilidad aceptable, Brier
  estrictamente mejor que prevalencia y ROC-AUC >= 0,55. El ranking posterior
  prioriza mayor mejora Brier, menor Brier y mayor ROC-AUC. Si no hay candidato
  elegible, el escenario se abstiene y conserva motivos por gate.
- La fiabilidad estadística califica al ganador mediante ROC-AUC, mejora relativa
  Brier, tamaño/clases del hold-out y aplicabilidad. El consenso no reutiliza esa
  etiqueta: mide separación entre familias metodológicas elegibles. Variantes
  Smooth Species/Shared/Partial pertenecen a una sola familia logística; su
  acuerdo se informa como interno, no como replicación independiente.
- La UI ofrece veredictos visibles y mantiene debajo la evidencia por escenario.
  Solo se abren automáticamente los detalles de versiones con algoritmos
  elegidos; las demás versiones incluidas permanecen plegadas y auditables.
- La aplicabilidad actual aprende mínimo, máximo, media y desviación por columna,
  pero clasifica con dos constantes de política no calibradas: 5 % de columnas
  fuera del rango o una salida a 3 sigma. No describen si lluvia/temperatura son
  ecológicamente buenas o malas; solo el soporte estadístico marginal del
  artefacto. Se auditarán antes de discutir cualquier cambio.
- Diseño y fórmulas completos:
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.

## 2026-08-22 - [VIGENTE][ML] Ventana predictiva y calentamiento físico son contratos distintos; retirar V5/V6-365 legacy

- Las versiones operativas son `biology_v5_windowed_raw_weather` y
  `biology_v6_windowed_smooth_hierarchical`. Cada una tiene perfiles
  predictivos de 30, 60 y 90 días. El modelo recibe únicamente los retardos
  meteorológicos de su ventana y los escalares físicos declarados; no recibe
  365 días de canales diarios como variables predictivas.
- `weather_lookback_days=365` se conserva solo para los perfiles que necesitan
  calentamiento causal del estado físico: ET0, balance hídrico, fracción de
  agua del suelo/SMI y resúmenes derivados. Ese histórico puede prepararse o
  cachearse una vez y compartirse; `predictive_window_days=30|60|90` determina
  las columnas que ve cada modelo. Los perfiles sin estado físico no deben
  solicitar 365 días por defecto.
- Las definiciones no-windowed `biology_v5_raw_weather_discovery` y
  `biology_v6_smooth_hierarchical` siguen actualmente en el registro como
  `status: reference` por compatibilidad. Se decide retirarlas definitivamente
  en una tarea posterior, una vez demostrado que ninguna generación instalada,
  puntero, manifiesto, adaptador o ruta runtime las referencia.
- Esta decisión reemplaza la cláusula «nunca se borran del registro» de la
  decisión de 2026-08-19. La retirada de los contratos legacy no autoriza
  borrar informes de benchmark históricos; su conservación o migración se
  decide aparte.

## 2026-08-22 - [VIGENTE][ML][ARQUITECTURA] Multiversión rutinaria por revisiones y caché; benchmark reservado a contratos nuevos

- Una vez instaladas las versiones actuales, el mantenimiento ordinario debe
  permitir reentrenar una, varias o todas las versiones instaladas y producir
  en la misma pasada artefactos y evidencia hold-out sincronizada. El benchmark
  científico independiente queda para añadir o modificar versiones, perfiles,
  features, estimadores o contratos, no como requisito de cada mantenimiento.
- La frescura rutinaria se decide comparando un vector pequeño de revisiones
  (`observations`, generación/manifiesto meteorológico, sites, estaciones,
  catálogos, GIS y contrato de entrenamiento). Un cambio posterior al
  entrenamiento genera un aviso trazable; no desencadena una comprobación
  profunda ni invalida automáticamente un artefacto íntegro.
- Los hashes completos siguen protegiendo la entrada de objetos, manifests,
  instalación y auditorías explícitas. Promocionar, cambiar la versión
  preferida o consultar el Predictor no debe releer todo el histórico.
- El worker debe mantener una caché meteorológica persistente por digest y
  descargar solo objetos ausentes o modificados. El coordinador debe evitar
  copiar y rehashear snapshots equivalentes. Esta optimización no permite
  mutar históricos ni omitir verificaciones de integridad al ingresar objetos.
- El estado instalado actual sigue siendo monoversión hasta implementar la
  migración documentada; esta decisión describe el objetivo, no afirma que el
  runtime actual ya lo cumpla.

## 2026-08-19 - [OBSOLETA][ML] `lactarius_deliciosus` no converge en ninguna ventana V5w 30/60/90

- Verificación parcial con datos reales locales del perfil
  `biology_v5_windowed_raw_weather`: reducir la ventana predictiva sí resuelve
  la no convergencia de `sparse_group_logistic_raw365_v1` para varias especies
  (p.ej. `amanita_caesarea` converge en 60/90d pero no en 30d — coherente con
  un problema de dimensionalidad frente a muestras), pero `lactarius_deliciosus`
  sigue sin converger en las 3 ventanas (30/60/90d).
- No se ha investigado la causa: al no ser un problema de dimensionalidad (ya
  se probó la ventana más corta posible sin éxito), debe tratarse de otra
  cosa — posible desbalance de clases, colinealidad específica de esa
  especie, o insuficiente soporte real. Sin datos suficientes para afirmar
  cuál. Pendiente explícito en `docs/todo.md` (P2 — Ventanas y coste
  científico).
- Resolución posterior: el benchmark completo del 2026-08-21 terminó con
  174/174 fits y 0 fallos; `lactarius_deliciosus` convergió en las tres
  ventanas. La duda dejó de describir el estado actual.

## 2026-08-20 - [VIGENTE][ML][RENDIMIENTO] Perfilado de predictor y entrenamiento: no se reescribe en C, se elimina redundancia en haversine

- Motivo: el usuario reportó tiempos de 10-12s por consulta del Predictor y 5-6 minutos por entrenamiento de versión completa, y preguntó si convenía reescribir en C el kernel de predicción/entrenamiento.
- Medido con `cProfile` sobre una consulta real del Predictor (`MushroomMLPredictor`, especie `boletus_edulis`): tiempo total 1.9s. Desglose: IDW meteorológico (`mushroom_weather_idw.py`) ~0.86s con **104.086 llamadas** a `haversine_km`, carga de artefactos joblib ~0.57s, predicción real del modelo ~0.22s. No hay cuello de botella algorítmico "puro Python" que justifique una reescritura en C: sklearn/NumPy ya delegan en BLAS/LAPACK compilado; el coste real es I/O (carga de artefactos) y una redundancia de cálculo evitable en el IDW.
- Medido sobre un benchmark real completo (suma de duraciones de fit reportadas en manifiestos): V4 41.5s, V3 22.3s, V5w 79.6s, V6w 10.6s, V2 11.0s — la suma de todos los fits está muy por debajo de los 5-6 minutos de reloj de pared que percibe el usuario. Confirmado en vivo (dos comprobaciones seguidas durante una ejecución real) que la fase que domina el tiempo de reloj es la preparación de inputs compartidos / evaluación de filas hold-out (`Preparing shared inputs — Evaluating selected V2--V5 hold-out rows`), no el ajuste de los modelos en sí.
- Decisión: no se reescribe nada en C. Se corrige la única redundancia identificada como fácil y de bajo riesgo: en `rainmapper_core/mushroom_weather_idw.py`, `build_daily_weather_idw_series` y `build_daily_rain_idw_series` recalculaban `haversine_km` una vez por estación para filtrar por radio y luego otra vez por estación y por día/métrica dentro de `estimate_daily_weather_idw`/`estimate_daily_rain_idw`. Ahora la distancia se calcula una sola vez por estación (`station_distances_km`) y se propaga como parámetro opcional (`Mapping[StationKey, float] | None`) a ambas funciones de estimación; si no se pasa, cada función sigue calculando la distancia como antes (compatible con otros llamadores).
- Verificado: 960 tests y `git diff --check` limpios tras el cambio.
- Pendiente explícito (no abordado ahora): investigar por qué la fase de preparación de inputs compartidos / evaluación hold-out domina el tiempo de reloj de un benchmark completo — no se ha perfilado esa fase en detalle, solo se ha confirmado en vivo que es donde se concentra el tiempo. Ver `docs/todo.md`.

## 2026-08-20 - [VIGENTE][BUG CORREGIDO] predict_bundle no aplicaba el preprocesador suave a V6 windowed

- Síntoma real: tras preparar y activar `biology_v6_windowed_smooth_hierarchical` como versión completa, el Predictor mostraba `runtime_model_incompatible` en las 6 combinaciones (3 ventanas × 2 contratos).
- Causa: `mushroom_ml_runtime_inference.py::predict_bundle` decidía si aplicar el `SmoothLagPreprocessor` comprobando `artifact_ref.version_id == "biology_v6_smooth_hierarchical"` (comparación exacta, solo la versión retirada). Para el version_id nuevo caía al `elif isinstance(preprocessor, Mapping)`, que tampoco aplicaba (el preprocesador es una instancia de clase, no un `Mapping`), y acababa alimentando al modelo la fila cruda sin proyectar — sklearn rechazaba la forma y el error genérico se mostraba como incompatibilidad.
- Es el mismo patrón de dispatch explícito por `version_id` ya documentado en la entrada de perfiles de ventana; este era un tercer sitio (además de `mushroom_ml_runtime_trainer.py` y `mushroom_ml_runtime_features.py`) que se pasó por alto en la primera implementación porque solo se ejercita en el camino de inferencia real del Predictor, no en el benchmark/entrenamiento.
- Corregido cambiando la comprobación a `in {"biology_v6_smooth_hierarchical", smooth.WINDOWED_VERSION_ID}`. Verificado con datos reales: fit + `predict_bundle` para 2 especies × 3 ventanas × 3 estimadores (18 combinaciones) devuelven probabilidades válidas sin excepción. 960 pruebas y `git diff --check` limpios.
- De paso se completaron dos referencias cosméticas que solo afectaban a etiquetas de UI (no a la inferencia): `VERSION_CAUTIONS` en `mushroom_ml_quality_catalog.py` y los diccionarios de nombre corto/descripción en `mushroom_predictor_ui.py`, que no tenían entrada para los dos version_id nuevos y por tanto mostraban el version_id crudo en vez de una etiqueta corta.

## 2026-08-19 - [VIGENTE][EXCEPCIÓN EXPLÍCITA] Los benchmarks científicos archivados son historia viva, no retención permanente

- Decisión explícita del usuario: "no quiero tener benchmarks para siempre... tiene que ser una historia viva. Así puedo mantener únicamente los que sean interesantes." Se añade un botón "Borrar" por fila en "Historial de benchmarks" que elimina físicamente `ml_models/benchmarks/<batch_id>/` (informe, predicciones hold-out, artefactos) del disco. Es irreversible y requiere confirmación en la UI.
- Verificado antes de implementar: `retention_policy.benchmark_generations: "permanent"` del registro **no aplica hoy** a estos directorios. Los batches de benchmark en `ml_models/benchmarks/` nunca se registran como `generations` dentro de una versión (las 7 versiones del registro tienen `generations: []` vacío); esa política protege únicamente generaciones ya registradas mediante `append_generation`, que hoy no se usa para benchmarks. Por tanto, borrar un batch de benchmark archivado **no contradice** la política de retención documentada tal como está escrita — es una historia paralela, no cubierta por esa regla.
- Salvaguarda: `mushroom_ml_benchmark_reports.delete_report` solo borra un directorio bajo `ml_models/benchmarks/<batch_id>/` cuyo `manifest.json` declare `job_purpose: "benchmark"` — nunca un batch operativo ni una candidata (`ml_models/candidates/`), y valida el `batch_id` contra el mismo patrón que `load_report`/`list_reports` para evitar traversal.
- Si en el futuro se implementa el registro de `generations` para benchmarks (hoy sin consumidores), esta excepción debe revisarse explícitamente: no debe poder borrarse un batch que ya esté registrado como generación permanente.

## 2026-08-19 - [REEMPLAZADA] Perfiles de ventana predictiva 30/60/90 días en V5/V6, retirando raw365/smooth-365

Reemplazada por la decisión vigente del 2026-08-22. La implementación de
ventanas permanece válida; queda reemplazada la retención «nunca borrar» de las
definiciones V5/V6-365 legacy.

- Motivo: el benchmark real de Biology V4 en producción reveló, por una vía
  distinta, que V5 (`sparse_group_logistic_raw365_v1`) no converge para 4/9
  especies (`"did not converge within 1000 iterations"`), muy probablemente
  por la altísima dimensionalidad (~2.557 columnas) de alimentar 365 valores
  diarios crudos por canal frente a pocas muestras por especie. Esto reabrió
  una discusión previa (con Codex, sin cerrar entonces) sobre separar el
  calentamiento físico de 365 días de la ventana que realmente ve el modelo,
  documentada como pendiente en `docs/todo.md`.
- Sustituye explícitamente la decisión "Ventanas runtime por contrato y
  experimento físico V2/V3 preservado" (2026-08-18) en la parte que exigía
  conservar V5/V6-365 hasta una comparación emparejada previa contra V5/V6-90.
  Se decide retirar V5/V6-365 directamente, sin esa comparación previa, dado
  que ya se observó que el diseño de 365 días crudos da señales
  contradictorias (convergencia nula en varias especies) y complica la
  interpretación. El resto de esa decisión (V2/V3/V4 a 90 días, cálculo de
  ET0/balance/SMI por perfil, `LOOKBACK_DAYS` como constante canónica) sigue
  vigente sin cambios.
- Diseño: `biology_v5_raw_weather_discovery` y `biology_v6_smooth_hierarchical`
  pasan a `status: "reference"` y `benchmark_available: false`, con
  `operational_eligible: false` en todos sus perfiles — **nunca se borran**
  del registro (`retention_policy.deactivation_action:
  change_status_to_reference_never_delete`), así que los benchmarks ya
  archivados que los referencian siguen siendo válidos e íntegros para
  lectura/comparación histórica.
- Se crean dos versiones nuevas, cada una con 3 perfiles que compiten entre sí
  únicamente por la ventana predictiva (30/60/90 días de meteorología cruda):
  `biology_v5_windowed_raw_weather` (perfiles `raw_window_{30,60,90}d_plus_physical_state`,
  mismos estimadores y contratos temporales que el V5 retirado) y
  `biology_v6_windowed_smooth_hierarchical` (perfiles
  `smooth_window_{30,60,90}d_plus_physical_state`, mismos estimadores que el
  V6 retirado). No se acuñan contratos temporales nuevos: los perfiles de
  ventana reutilizan los mismos `temporal_contract_id` y
  `derived_feature_contract_id` que las versiones retiradas, porque describen
  la misma forma de entrada preparada (serie de área de 365 días); solo cambia
  qué subconjunto de columnas ve cada perfil, igual que ya convivían seis
  variantes de perfil bajo un mismo contrato en el V5 original.
- Balance hídrico y SMI se mantienen **comunes/compartidos** entre las 3
  ventanas: siguen calculándose con el calentamiento de 365 días de siempre
  (sin tocar `mushroom_climatic_water_balance.py`/`mushroom_soil_water_state.py`),
  y solo se exponen al modelo como los 7 escalares `PHYSICAL_STATE_SCALARS`
  agregados — nunca las series diarias completas de balance/SMI/ETO. Lo único
  que se recorta a 30/60/90 días son las columnas crudas de lluvia,
  temperatura y humedad (`RAW_CHANNELS`).
  **Pendiente de investigar** (no implementado): si recalcular balance/SMI de
  forma independiente por cada ventana (en vez de compartir el mismo valor de
  365 días entre las tres) aísla mejor cuánta señal aporta cada ventana, a
  costa de dejar de ser comparable con V3+ físico.
- Implementación: `mushroom_ml_raw_weather.windowed_feature_columns`/
  `windowed_profile_id` (V5) y los parámetros nuevos `channels`/`window_days`
  de `mushroom_ml_smooth_hierarchical.smooth_lag_basis`/`raw_columns`/
  `SmoothLagPreprocessor` (V6, con valores por defecto que preservan el
  comportamiento exacto del perfil retirado). `mushroom_ml_runtime_trainer.py`
  (`_columns`, `fit_artifact`, `_fit_v6`), `mushroom_ml_runtime_features.py`
  (inferencia del Predictor) y `mushroom_ml_multiversion_comparison.py`
  (`_weather_requirements`) añaden ramas paralelas para los dos version_id
  nuevos, siguiendo el mismo patrón explícito por versión que ya usaba el
  código (no hay despacho genérico). `mushroom_ml_multiversion_plan.build_plan`
  no requirió cambios: es genérico sobre `catalog_entries`.
- Validado: 957 pruebas (`unittest discover -s tests`), `git diff --check`
  limpio, y una prueba manual de `fit_artifact` end-to-end para un perfil de
  cada versión nueva confirma el recorte real de columnas (159 para V5-30d,
  309 antes de compresión B-spline para V6-60d).

## 2026-08-19 - [VIGENTE][BUG CORREGIDO] Elegibilidad de especies duplicada entre HA local y worker para benchmarks V2–V6

- Síntoma real observado por el usuario: un benchmark científico de Biology V4
  lanzado en HA real contra el worker M1 (`create_mushroom_ml_multiversion_job`,
  rama sin `triggered_by_job_id`) planificó 384 fits sobre 16 especies con 168
  fallos (`"Runtime artifact requires both classes"`), lo que bloqueó
  `Preparar candidata completa` con `"Operational batch does not contain every
  required artifact"` (`mushroom_ml_multiversion_transport.py:194-209`). El
  mismo benchmark lanzado como "Home Assistant local"
  (`mushroom_local_full_update.run_local_benchmark`) sobre el mismo dataset
  dio 216/216 fits sin fallos.
- Causa verificada: **no era un problema de datos** — las observaciones de
  `docker-data/mushroom-data/` y `/share/rainmapper/mushroom-data/` son
  idénticas byte a byte (comprobado con diff). El problema era que existían
  dos funciones de elegibilidad de especies distintas para el mismo concepto
  ("especies entrenables para un benchmark/operativo V2–V6"):
  - Ruta HA local: `mushroom_local_full_update._eligible_training_species`
    (ahora pública, `eligible_training_species`), que exige ≥10 filas válidas
    en `mushroom_observation_features_v0.json` y **ambas clases**
    (`favorable`/`unfavorable`) representadas por especie.
  - Ruta worker sin job de rebuild vinculado: `web_server.py`, función
    `eligible_model_species_ids(observations)` (`web_server.py:14632`), que
    solo exige `validation_status=valid`, `calibration_use=include` y
    coordenadas — sin mínimo de filas ni comprobación de clase. Esta función
    sigue siendo correcta para su uso original (alcance amplio de ML v0), pero
    no era apta para decidir el plan de un benchmark/operativo V2–V6.
- Corrección aplicada: `create_mushroom_ml_multiversion_job` (rama sin
  `triggered_by_job_id`, `web_server.py:13193-13196`) ahora llama a
  `mushroom_local_full_update.eligible_training_species(feature_path)`, la
  misma función que usa la ruta HA local. Las demás llamadas a
  `eligible_model_species_ids` (ML v0, pendientes de reconstrucción, etc.) no
  se han tocado porque responden a un alcance distinto y correcto.
- Validado con 949 pruebas (`unittest discover -s tests`) y `git diff --check`
  limpio. Pendiente: repetir el benchmark V4 vía worker para confirmar que
  ahora también resuelve 9 especies (o el conjunto que corresponda con datos
  vivos) sin fallos, igual que en HA local.

## 2026-08-19 - [VIGENTE][FASE 4 EN PRUEBA LOCAL] La unidad de promoción es la versión completa

- `operational_eligible` significa que el runtime puede entrenar, verificar y
  ejecutar el perfil; no significa que haya ganado el benchmark.
- La elección final es humana y las métricas son orientativas. El benchmark no
  prepara, instala ni activa modelos automáticamente.
- Se activa `version_id/generation_id`, incluyendo todos los perfiles técnicos
  de esa versión. Para `biology_v3` son V3 core y V3+ físico, cada uno con fixed
  y lag visibles en Predictor; no hay un perfil principal implícito.
- `Preparar candidata completa` reentrena sobre entradas vivas y archiva el
  resultado sin tocar runtime. `Activar versión completa` es una segunda acción
  confirmada. La promoción guarda journal y copias anteriores, y ofrece rollback
  exacto de registro y descriptor.
- El contrato es declarativo: para habilitar otra versión deben estar definidos
  todos sus perfiles operativos, inputs, adaptador y política de miembros. No se
  añaden ramas de promoción basadas en el nombre `Vx`.
- Smoke completo (935 pruebas), `git diff --check`, reconstrucción HA local y
  presencia contextual de la acción de candidata están validados. Queda que el
  usuario ejecute candidata, activación, cuatro salidas y rollback reales.

## 2026-08-18 - [VIGENTE CON AMPLIACIÓN 2026-08-19][FASES 1 Y 2] Separar operación y benchmark científico

- La reconstrucción habitual dejará de entrenar automáticamente todo V2–V6.
  Ajustará únicamente la generación que alimenta el Predictor; mientras no se
  promocione otra, V2 continúa operativo y completo en fixed/lag.
- V2–V6 seguirán registrados y reproducibles mediante un benchmark bajo
  demanda, ligado a snapshot inmutable y sin promoción automática.
- Habrá dos acciones principales: `Reconstruir y reentrenar operativo` y
  `Ejecutar benchmark científico`. `Ver comparación` será una acción del job
  terminado, con informe persistente por especie/contrato/horizonte/estimador.
- Un benchmark podrá ofrecer promoción humana explícita de una generación
  completa, nunca de una celda aislada. Exigirá elegibilidad operativa,
  integridad, paridad, completitud y entradas vivas compatibles. La ampliación
  del 2026-08-19 habilita V3 core y V3+ conjuntamente; V4–V6 siguen sin ser
  técnicamente elegibles.
- El primer experimento controlado será V3 core frente a un perfil nuevo
  V3 physical/V3+: mismas filas, targets, splits, contratos y estimadores; la
  única adición será balance hídrico y SMI derivados del IDW. No se modifica
  silenciosamente V3 core.
- Solo si el bloque físico mejora de forma repetible se abrirán ablaciones de
  balance/SMI y variantes V5 de 30/60/90 días. V5/V6-365 se conservan como
  controles históricos reproducibles.
- La implementación se divide en separación de jobs, informe seleccionable,
  V3 physical, promoción genérica y experimentos posteriores. Antes de release
  se requiere autorización explícita.
- La fase 1 usa `job_purpose=operational|benchmark`. El flujo operativo resuelve
  la versión activa del registro (`altitude_v2` actualmente), prepara solo sus
  fuentes fixed/lag y exige todos sus artefactos sin fallos. El benchmark manual
  conserva V2–V6 y se archiva sin escribir `runtime-batch.json`.
- El transporte ya no instala al completar una subida. Un resultado operativo
  queda verificado en staging y se instala únicamente dentro de la promoción
  conjunta; si esta falla antes de completar la generación se restaura el
  descriptor runtime anterior y se elimina el batch nuevo. El flujo local usa
  la misma política compensatoria.
- La UI separa ambas acciones. Solo un job operativo enlazado puede disparar la
  promoción automática; un benchmark terminado nunca la dispara. Los workers
  destinados al flujo completo deben declarar `ml_job_purpose_v1`.
- La fase 2 valida una selección no vacía de perfiles comparables y la conserva
  en job, plan, manifiesto e informe. Cada batch científico archiva sus
  predicciones hold-out, métricas sin promediar especies, fallos y duraciones
  por fit/versión/perfil/estimador. `Ver comparación` y el historial leen ese
  archivo persistente, no la retención temporal de la cola.
- Un resultado científico externo debe declarar `ml_benchmark_report_v1`; HA
  verifica identidad y hashes del informe y de sus predicciones antes de
  archivarlo. Este contrato no concede elegibilidad ni promoción automática.
- Especificación:
  `docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`.

## 2026-08-18 - [VIGENTE][INTERPRETACIÓN] Biology V3 no equivale a covariables biológicas directas

- V3 introduce principalmente contratos de muestra/target, preservación de
  observaciones y validación por grupos de florada. Sus variables activas son
  fundamentalmente meteorológicas; no incorpora por ese nombre huésped,
  bosque o sustrato.
- V4–V6 heredan esa línea contractual y añaden simultáneamente otras variables,
  representaciones y algoritmos. Comparar versiones completas no permite
  atribuir causalmente la mejora a una sola familia.
- Las comparaciones futuras deben mantener filas, splits, contratos y
  estimadores y cambiar un único bloque predeclarado siempre que sea posible.

## 2026-08-18 - [VIGENTE][RELEASE] HA 0.2.261 y worker privado local 1.0.14

- Publican el contrato operativo `lag_event` con horizontes 1..7, eliminando
  los falsos `model_not_installed` de h4/h5/h6 sin multiplicar los ajustes.
- Gate: 51 pruebas dirigidas, smoke completo 898/898 y `git diff --check`.
- HA `0.2.261` y `latest` comparten
  `sha256:ad0dc1fba3ea7a420b05cc9ca4bcae9d035ebb0aefccd9680dd4892f7467aec2`,
  con `linux/amd64` `sha256:5a5a2e10fcfa33e0829ec3af5d411b24c8b53ab6cb6cef7c7fc095032a1a209c`
  y `linux/arm64` `sha256:dd9a1b0c66fa518164c2ee5c12c5c3b28e2fdf75f732022ed8a252cf67def4bf`.
  El worker arm64 local `1.0.14` tiene imagen
  `sha256:a9dda8c58eda5b91087ed651decc777b9f03d0fcf382ec308e90a6c44461606c`
  y no se publicó en ningún registro.

## 2026-08-18 - [VIGENTE][CONTRATO] Lag operativo cubre toda la semana 1..7

- Los horizontes operativos de `lag_event` son los siete enteros 1..7. Los
  cortes 1/2/3/7 son diagnósticos de calidad y no pueden crear huecos de modelo
  en h4/h5/h6.
- Sigue existiendo un único ajuste por especie+contrato+perfil+estimador; añadir
  las filas y referencias intermedias no multiplica el número de fits.
- Evidencia del defecto: el runtime real declaraba 215 artefactos lag y todos
  llevaban `supported_horizons=[1,2,3,7]`; por eso el Predictor interpretaba los
  días 4–6 como `model_not_installed` y volvía a encontrar el mismo artefacto en
  h7.

## 2026-08-18 - [VIGENTE][RELEASE] Worker privado local 1.0.13

- Despliega la reutilización del runtime actual y el fallback verificado por
  fichero cuando el tar no concuerda con su manifest.
- Se recreó el contenedor conservando el volumen: servicio `idle`, caché GIS
  válida de 12 ficheros/6.341.520.039 bytes y caché Predictor válida de
  143.696.061 bytes con fingerprint
  `sha256:5d828e31ef1f3165e5741b82419851dd51d0aaa33016fa5678c86c92fc1c398f`.
- Gate: smoke completo 896/896 y `git diff --check`. Imagen arm64 local
  `rainmapper-worker:1.0.13`, digest
  `sha256:230737ae0328425997b698d4c830ecf3489c121b5cc241cf394d8042bb634f41`;
  no se publicó en ningún registro.

## 2026-08-18 - [VIGENTE][FIX] El runtime actual también fuerza sincronización delta

- El tar completo solo se intenta cuando el worker no conserva ni una versión
  actual del runtime ni objetos transitorios producidos por entrenamiento.
  Cualquiera de las dos fuentes puede evitar descargas por SHA-256.
- Si un tar está corrupto o no concuerda con su manifiesto, el Predictor no
  falla directamente: vuelve al transporte por fichero, que verifica tamaños y
  hashes mediante el mismo contrato.
- Evidencia real: tras una primera sincronización correcta en 31 s, dos jobs
  calientes fallaron al descargar de nuevo 143,7 MB y rechazar el tar. El
  runtime actual seguía presente en el volumen del worker.

## 2026-08-18 - [VIGENTE][RELEASE] HA 0.2.260 y worker privado local 1.0.12

- La carga fría del Predictor reutiliza por SHA-256 los modelos creados por el
  mismo worker y usa sincronización delta cuando existe ese almacén local; el
  tar único queda para runtimes sin objetos reutilizables.
- La comprobación UI de vigencia confía en la identidad inmutable de la
  generación meteorológica y no trata el rebasing de una salida derivada como
  cambio de sus entradas autoritativas.
- Gate: smoke completo 894/894 y `git diff --check`. HA `0.2.260` y `latest`
  comparten `sha256:c9ad3fcc04f47d39f1bb6f9f0e848f34670e0af5c6eeaf9babb54e527f3e281a`,
  con `linux/amd64` `sha256:35d685d57a7110ed49464f13889b7f1f93c9ea574176e9a4d61d149986b2f2c4`
  y `linux/arm64` `sha256:8667d0ee1f37dba8fc7edf253a7ddbad0956f28e23f2b25b922a88c3aae41cdf`.
  El worker no se publicó en registro: imagen local arm64 `1.0.12`, digest
  `sha256:451f8c9c706af37c527013f946428fe94142b352f79f9a31c1e2fd30112d8056`.

Nota de auditoria 2026-07-20: este fichero es un log cronologico/historico. Las
entradas antiguas se conservan para trazabilidad y pueden describir fases ya
reemplazadas; prevalece siempre la decision vigente mas reciente. Este fichero
no declara el estado operativo actual: para versiones instaladas, prioridades y
riesgos hay que leer `docs/active-context.md`. El repo GitHub continúa público.
Datos vivos/privados bajo
`docker-data/mushroom-data` en local y `/share/rainmapper/mushroom-data` en HA,
y GIS/DEM bajo `/media/rainmapper/mushroom-GIS`, no deben borrarse,
sobrescribirse ni versionarse. Toda UI de setas debe ser humana, coherente y
multiidioma mediante labels `en`, `es` y `ca`.

## 2026-08-18 - [VIGENTE][ARQUITECTURA] El worker reutiliza los modelos que entrena

- Una prueba real posterior a la regeneración produjo un runtime Predictor de
  518 ficheros y 143.698.035 bytes. Aunque el mismo worker acababa de entrenar
  los modelos, su limpieza terminal eliminaba los directorios de trabajo y la
  caché Predictor descargó desde HA 96.018.385 bytes de modelos ya producidos.
- Antes de limpiar un job ML v0 o V2–V6, el worker conserva sus modelos en un
  almacén transitorio dirigido por SHA-256. La materialización del runtime busca
  primero la versión Predictor anterior y después esos objetos locales; solo
  descarga los hashes ausentes. Tras enlazarlos en una versión inmutable, poda
  el almacén transitorio para no acumular generaciones.
- HA ofrece además un único tar content-addressed y verificado por manifest. Es
  respaldo para ficheros ausentes, resultados creados por otro worker o cachés
  perdidas; trabajadores antiguos conservan el fallback de una petición por
  fichero.
- La vigencia de entrenamiento no considera el JSON derivado de features como
  entrada autoritativa binaria: la promoción cambia únicamente metadatos de
  rutas al rebasarlo. Observaciones, catálogos, GIS, estaciones, perfiles,
  registro y generación meteorológica continúan comprobándose. Para la alerta
  UI, la meteorología particionada usa su generación y digest de manifest
  inmutables; las promociones siguen realizando la validación profunda.

## 2026-08-18 - [VIGENTE CON FASE 1] La generación externa completa se promociona automáticamente

- «Reconstruir y reentrenar operativo» ya es una única intención del usuario y
  encadena reconstrucción, ML v0 y la generación activa V2 fixed/lag. Una segunda aprobación al final no
  aporta una revisión adicional: la promoción ejecuta validaciones automáticas.
- La regeneración real de HA `0.2.258` terminó V2–V6 a las 03:12:53 CEST. Antes
  de la activación manual, el runner programado `source=schedule`, `action=all`
  actualizó `weather-history/CURRENT.json` a las 05:04:52 CEST. La promoción se
  rechazó correctamente por hash y fingerprint obsoletos, pero se perdió una
  cadena de cálculo válida por una ventana de espera innecesaria.
- Tras completar el entrenamiento operativo enlazado, HA inicia inmediatamente la promoción
  completa usando el ID del ML v0 padre. La propia operación exige que el ML
  proceda de una reconstrucción `full_update` y que su generación V2 esté completa.
- Se conservan el chequeo de frescura, la verificación de manifests, la
  instalación atómica, el rollback de artefactos si falla ML y la liberación de
  caché. No se reintenta automáticamente una cadena pesada si las entradas ya
  cambiaron.
- Los jobs fallidos, los benchmarks V2–V6, las reconstrucciones
  parciales y los experimentos quedan fuera de esta automatización. El botón
  manual puede permanecer como recuperación ante un fallo al iniciar la
  promoción, no como paso normal del flujo completo.

## 2026-08-18 - [VIGENTE][CORREGIDO EN HA 0.2.258] El V2–V6 enlazado debe heredar las especies entrenadas

- En la primera regeneración real con HA `0.2.257`, ML v0 recibió 9 especies y
  entrenó 8, pero el coordinador reconstruyó para V2–V6 una lista independiente
  de 16 mediante `eligible_model_species_ids(observations)`. El job real
  `worker_job_lpQr8P_ab4aFsha0` demuestra ese alcance y terminó con 868 fits:
  487 correctos y 381 fallidos. La generación completa no fue activada.
- No es un defecto del trainer ni del worker. La ruta local ya limitaba el
  alcance; faltaba hacerlo en el flujo externo HA→worker. La corrección guarda
  en el job ML el `trained_species` procedente del manifiesto que HA ya verificó
  y obliga al preparador enlazado a consumir exactamente esa lista. No confía en
  el conteo declarado por el worker ni recalcula elegibilidad desde observaciones.
- Aplicando el filtro al manifiesto real, las 8 especies entrenadas representan
  432 fits: 429 artefactos y únicamente 3 fallos sparse-group conocidos
  (Amanita caesarea, Boletus aereus y Lactarius deliciosus). Los otros 436
  intentos no debían planificarse.
- Validación local: 241 pruebas dirigidas y smoke completo con 886 pruebas,
  compilación Python/JS/shell, fixtures y `git diff --check` correctos. La
  corrección se publicó en HA `0.2.258`; worker `1.0.11` no cambia. Los tags
  `0.2.258` y `latest` comparten el índice OCI
  `sha256:ccf54f9a4596a3bb15d7009fd8d92778874850c445a004d5a6b1db44a4966928`,
  con `linux/amd64`
  `sha256:9c45b6b046b2529b7eda5ede51e8d77c2d245572dcd649da5be476632a34ff1b`
  y `linux/arm64`
  `sha256:18bc28f384b686b98a3344fcc9ea7f0c9c32485085c38607c30f1c3e5afa623c`.
  Corrección `bce180d`, release `be674d1`. No activar el candidato de `0.2.257`
  ni relanzar producción hasta instalar `0.2.258`.

## 2026-08-18 - [VIGENTE][RELEASE] HA 0.2.257 publicada y worker privado 1.0.11 actualizado

- El usuario autorizó expresamente la entrega HA+worker después de validar el
  Predictor local. El gate previo superó 883 pruebas, compilación Python/JS/shell,
  fixtures y `git diff --check`.
- `ghcr.io/cginebrosa/rainmapperha:0.2.257` y `latest` comparten el índice OCI
  `sha256:67a4d38890591adbc53bb441ff39ae2c9a544f5d78aefe45f74560daa4d86bc5`.
  Se verificaron los manifests `linux/amd64`
  `sha256:7a06463088ee099da9e2c99f4097276f5385dbf11c066de01d2d3f56683613b6`
  y `linux/arm64`
  `sha256:d3db4a35f734fe23d36bce42b8f3587ff87fb602cd96b82bf3d12cf8852022fc`.
- El worker normal se recreó únicamente con la imagen privada `1.0.11`, imagen
  local `sha256:94466c8365b729e43df4329eae1702bd76a05bd72340f9372878f963381baa8d`,
  conservando `rainmapper-worker-data`, identidad y cachés. El endpoint local lo
  revalidó `healthy`, `idle` y con las capacidades esperadas. No se usó
  Tailscale ni se modificó HA real.
- Código, bump y contratos quedaron publicados en `origin/inicial`, commit
  `c5b51e8`. HA `0.2.257` todavía debe instalarse y validarse en la RPi4; no se
  considera instalada ni dada por buena por el hecho de estar en GHCR.

## 2026-08-18 - [REEMPLAZADA][ML][RENDIMIENTO] Ventanas runtime por contrato y experimento físico V2/V3 preservado

- Los 365 días diarios de V5/V6 son el alcance congelado de esos experimentos,
  no una ventana biológica respaldada por la literatura ni el default del
  Predictor. V2/V3 actuales materializan 90 días IDW; V4 materializa 90 días y
  solo calcula estado físico para perfiles que lo declaran; únicamente V5/V6
  conservan 365 días.
- El runtime decide ET0, balance y SMI por el perfil exacto instalado. Omitir
  ese cálculo cuando las columnas no forman parte del bundle evita trabajo que
  se descartaba, pero no elimina la implementación ni su posible uso.
- Se preserva como experimento futuro una variante explícita V2/V3
  `IDW + estado físico`, entrenada y comparada como perfil/contrato distinto
  frente a V2/V3 `common_idw`/`core`. No se puede añadir balance/SMI a un bundle
  ya entrenado ni sustituir silenciosamente sus variables actuales.
- La evidencia local revisada concentra retardos meteorológicos de fructificación
  en semanas y aproximadamente un mes; 90 días es un máximo conservador para
  meteorología diaria, sujeto a comparación científica. Esto no demuestra que
  los días 91–365 carezcan de señal. **Sustituida el 2026-08-19** por
  «Perfiles de ventana predictiva 30/60/90 días en V5/V6, retirando raw365/
  smooth-365»: en vez de exigir la comparación emparejada previa contra
  V5/V6-90, se retiran directamente V5/V6-365 (a `status: reference`,
  `benchmark_available: false`, `operational_eligible: false` en todos sus
  perfiles) y se sustituyen por versiones nuevas con 3 perfiles de ventana
  compitiendo entre sí. La cláusula posterior de conservar para siempre las
  definiciones legacy queda reemplazada por la decisión vigente del
  2026-08-22. Señales de ciclo previo
  como NDVI, huésped o fuego deben entrar como variables ecológicas explícitas,
  no como 275 días meteorológicos extra por defecto.
- `mushroom_ml_raw_weather.LOOKBACK_DAYS` es la única constante canónica de la
  longitud V5/V6. No es un ajuste de UI: cambiarla altera columnas y exige un
  contrato nuevo y reentrenado.
- El Predictor valida una vez el manifiesto inmutable por petición, reutiliza
  su índice y los bundles verificados por hash. En la misma consulta local de
  referencia pasó de 116,011 s en caliente a 13,185 s; cambiar al día siguiente
  dentro del mismo proceso tardó 12,435 s. Estas cifras son del entorno local,
  no una garantía para HA real.

## 2026-08-17 - [DUDA][IDW][ML] Vacío IDW en Salteguet y modelo fijo no entrenado

- Salteguet muestra lluvia IDW `-` para 2026-08-17 aunque hay estaciones
  cercanas con `0.0`; IALP87 aparece `N/A`.
- El código filtra estaciones con valor no finito antes de interpolar: un
  `N/A` aislado no entra en la media ni propaga `NaN`. Para lluvia existe además
  un umbral de soporte ponderado; si no se alcanza, devuelve `null` aun con
  estaciones finitas. Falta reproducir el punto exacto antes de modificarlo.
- «Ventana ciega fija de 7 días · model_not_trained» pertenece al bloque
  operativo/sombra. No está demostrado que sea el miembro V2 del batch, que sí
  contiene artefactos `altitude_v2`. Edulis tiene 27 episodios, pero el tramo
  temporal de entrenamiento solo contiene una clase; falta trazar la omisión.
- Ambas dudas bloquean la release. No hay autorización de publicación.

## 2026-08-17 - [VIGENTE][RELEASES] Separación del arreglo urgente y la migración multicoordinador

- La primera entrega HA+worker incluirá únicamente el cierre urgente ya
  validable en local: regeneración V2–V6 desde snapshot fresco, manifiesto de
  entrenamiento, promoción completa única, limpieza de staging, resumen de
  confianza del Predictor y progreso granular del ejecutor HA local.
- La migración de credenciales se publicará después en una release independiente
  del worker, tras probar el mismo worker contra dos coordinadores HA locales
  aislados. No se mezcla esa migración sensible con la corrección urgente.
- El HA de la primera entrega debe seguir siendo compatible con ese worker. Una
  release HA adicional se reserva para la protección `409` al revocar durante
  un job activo, si la revisión del protocolo confirma que necesita cambio en
  el coordinador.
- `0.2.257` y `1.0.11` son candidatos secuenciales, no versiones asumidas ni
  reservadas. Todo bump, build o publicación requiere primero cerrar las
  validaciones y recibir autorización explícita del usuario.

## 2026-08-17 - [VIGENTE][DISEÑO PENDIENTE][ARQUITECTURA] Un worker podrá atender varios coordinadores

- El objetivo futuro sustituye la limitación de una sola conexión del worker,
  no el runtime instalado: worker `1.0.10` continúa siendo monocoordinador.
- Una instalación conservará un único `worker_id`, volumen, caché y slot global
  de ejecución, con URL y token aislados por coordinador. El M1 podrá atender
  al HA real y al laboratorio local sin reemparejar, cambiar la URL real ni
  crear identidades o volúmenes temporales.
- Los heartbeats serán independientes; los claims se arbitrarán justamente y
  cada job se comunicará solo con su coordinador de origen. Reconstrucción, ML
  v0 y V2–V6 seguirán encadenados con una única promoción completa.
- El número máximo de asociaciones será el parámetro persistente
  `max_coordinators`, default 4, configurable desde el arranque/CLI y validado;
  no una constante rígida. Seguirá habiendo un solo job pesado concurrente.
- Una revocación desde HA elimina primero la credencial del servidor. Ante el
  `401` inequívoco del siguiente heartbeat/consulta, el worker eliminará solo
  la asociación correspondiente. Timeout, DNS, desconexión o `5xx` nunca
  borrarán credenciales. Con un job de ese HA activo, la revocación se rechazará
  con `409` hasta cancelarlo o finalizarlo correctamente.
- El worker no tendrá UI propia. Pairing y revocación normal se inician desde
  cada coordinador; el script/CLI local permitirá listar y olvidar una
  asociación inaccesible sin revelar secretos.
- Especificación y criterios de aceptación:
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.

## 2026-08-17 - [VIGENTE PARA EL RUNTIME ACTUAL][ARQUITECTURA] Un worker real y un ejecutor HA exclusivo del laboratorio local

- El worker M1 conserva una sola identidad, un solo volumen y una sola conexión
  saliente al HA real de la RPi4. No se reempareja alternativamente con el HA
  local ni se mantiene un segundo worker ficticio para pruebas.
- El montaje temporal `Validación local` y los puertos `8103`/`8111` no forman
  parte de la arquitectura. El HA local canónico vuelve a `8101` y comparte el
  registro histórico, aunque vea desconectado el M1 mientras este sirve al HA
  real.
- Para poder validar en el M1 sin alterar el worker normal, únicamente el compose
  local activa `RAINMAPPER_LOCAL_HA_COMPUTE_ENABLED=true`. Esta opción ejecuta
  dentro del contenedor HA local los mismos contratos y scripts que el worker;
  la imagen/despliegue HA real permanece coordinador-only por defecto.
- Tanto el camino del worker como el ejecutor HA local encadenan tres trabajos:
  reconstrucción, ML v0 y V2–V6. Solo existe una promoción de la generación
  completa y no se habilita hasta terminar los tres. No se publica un candidato
  parcial ni se hace fallback silencioso desde un worker desconectado.
- Preparar o publicar una release requiere una autorización explícita posterior
  del usuario, incluso si el gate local termina correctamente.

## 2026-08-17 - [VIGENTE][ML][ARQUITECTURA] Regeneración V2–V6 reproducible y aviso de vigencia

- Se elimina la dependencia operativa de los JSON del snapshot de laboratorio
  `mushroom-ml-snapshot-20260816`. Cada regeneración construye sus entradas
  V2–V6 desde el snapshot fresco creado por HA y consumido por el worker.
- No se añade una reconstrucción parcial: la acción existente encadena
  reconstrucción, ML v0 y V2–V6 para mantener todas las versiones alineadas con
  la misma información disponible.
- V2, V3, V4, V5 y V6 tienen el mismo estatus experimental. V2 aparece primero
  únicamente por cronología y continuidad de UI; no es la versión preferida ni
  el baseline que deba ganar por defecto.
- El batch guarda una identidad de entradas con hashes, sin datos brutos ni
  rutas privadas. El Predictor usa esa identidad para avisar si la generación
  está desactualizada o no puede verificarse.
- Las copias temporales de resultados solo se borran tras instalación íntegra;
  los fallos se conservan para diagnóstico.
- Las imágenes públicas contienen código, dependencias y defaults. HA incluye
  una plantilla de observaciones vacía; ninguna imagen incorpora observaciones,
  snapshots, hold-outs, benchmarks o modelos entrenados.
- Esta decisión reemplaza únicamente la dependencia runtime del snapshot fijo
  descrita en entradas anteriores. El snapshot de 2026-08-16 sigue vigente como
  evidencia científica inmutable para reproducir aquellos informes.

## 2026-08-17 - [VIGENTE][RELEASE] HA 0.2.256 y worker privado 1.0.10

- El usuario autorizó publicar la pareja validada localmente. El smoke previo
  superó 845 pruebas. Durante esta sesión el usuario mostró HA `0.2.256` y
  worker M1 `1.0.10` ya instalados y emparejados; esta observación no fue
  revalidada directamente por Codex contra los hosts al cierre.
- `ghcr.io/cginebrosa/rainmapperha:0.2.256` y `latest` comparten el índice OCI
  `sha256:880c2edb4a384f0e3585d9bb9c82417e988a8d2c48799f5aab2a2c7548e86665`,
  verificado con manifiestos `linux/amd64`
  `sha256:aba74127fe736b439b6941f6e786898a6bd702c1c82ca6487cfecec3e7224443`
  y `linux/arm64`
  `sha256:ee203b3579e1095beaa38de367db1c34b0c1851a190f9ddbff291fef2c80cb6c`.
- El worker sigue siendo privado y no se publica en GHCR. La imagen arm64
  `rainmapper-worker:1.0.10` tiene digest local
  `sha256:b56d68e5de63b90b120155ab23554390a8e40e6102798c4bb1fd4df18872fdd4`.
  El TAR del paquete `~/Desktop/RainmapperWorker-1.0.10/` tiene SHA-256
  `b582120db939a6e5823095b243430119d5cd993d94b57dc0c7962d93d3da2de2`;
  no contiene el volumen persistente y el paquete anterior no se sobrescribe.
- Orden de instalación: worker `1.0.10` primero y HA `0.2.256` después. El
  coordinador HA `0.2.254` ya validaba capacidades como una lista abierta bajo
  schema `0.1`, por lo que acepta las dos capacidades nuevas del worker. Así,
  cuando arranque HA `0.2.256`, ya encontrará un ejecutor V2--V6 compatible.
- La regeneración real completó reconstrucción y ML v0, pero el paso V2–V6
  falló porque `0.2.256` dependía de un fichero del laboratorio ausente en HA.
  La release permanece como estado instalado, pero su regeneración multiversión
  queda corregida solo en local y exige una release posterior antes de repetirla
  en producción.

## 2026-08-16 - [VIGENTE][ML] `lag_event` ajusta un modelo y proyecta sus horizontes

- Un modelo ajustado se define por especie, contrato temporal y estimador. En
  `lag_event`, `horizon_days` es una variable predictiva del contrato, no la
  identidad de cuatro modelos distintos.
- Las métricas y el consenso de horizontes 1/2/3/7 se calculan filtrando las
  probabilidades del mismo hold-out del modelo completo. Está prohibido volver
  a ajustar por horizonte.
- El comportamiento anterior —modelo completo más cuatro reentrenamientos—
  queda **[OBSOLETA]**: multiplicaba el coste aproximadamente por cinco y
  respondía a otra pregunta científica. Su JSON se conserva como evidencia con
  `decision_eligible=false`.
- La corrección mantiene exactamente cobertura, particiones y métricas del
  modelo completo; `lag/groups7` baja de 650,68 s a unos 157 s. Una prueba
  cuenta las evaluaciones para impedir la regresión.

## 2026-08-16 - [VIGENTE][ML] Calidad antes que acuerdo y sin Brier medio

- La selección se hace por especie, contrato temporal y estimador. No se usa un
  Brier medio entre especies ni se escoge un algoritmo por un agregado pooled.
- El consenso se estudia solo después de identificar algoritmos que superan la
  prevalencia de entrenamiento en el mismo hold-out. Dos modelos parecidos que
  predicen peor no forman una combinación útil.
- RF+ET es la pareja con mayor acuerdo bruto, pero no queda seleccionada. Un
  ensemble futuro debe materializar su probabilidad y superar al mejor miembro
  individual antes de poder activarse.
- El informe vigente es
  `docs/reports/V2_V3_V4_consensus_report002.md`. El informe 001 queda
  **[REEMPLAZADA]** para decisiones.

## 2026-08-16 - [VIGENTE][BIOLOGY V3/V4] Meteorología IDW común para comparar versiones

- V2, V3 y V4 se comparan con las mismas filas y la misma meteorología espacial:
  lluvia, Tmin, Tmax, RHmin y RHmax por IDW diario de todas las fuentes
  disponibles, radio 15 km, potencia 2 y mínimo una estación válida.
- Tmin/Tmax se corrigen a la altitud DEM de cada microárea antes de ponderar;
  RHmin/RHmax no tienen corrección altitudinal. Después se agrega por área.
- La reproducción V2 operativa de estación única se conserva como referencia,
  pero no se usa para atribuir a la versión diferencias causadas por otra base
  meteorológica.
- Procedencia, cobertura, distancias, estaciones y motivos de descarte son
  calidad auditable y nunca entran en `X`. Lluvia ausente no equivale de forma
  general a cero; solo el duplicado positivo suprimido con causa conocida usa
  la excepción ya acordada.

## 2026-08-16 - [VIGENTE][ML][DATOS] Snapshot canónico, versiones persistentes y huella

- `docker-data/mushroom-data/` contiene los ficheros canónicos de trabajo local;
  `docker-data/audits/<generación>/` conserva fuentes, derivados, hashes y
  evidencia inmutable. `/private/tmp` es solo scratch y nunca fuente de una
  instalación.
- El snapshot científico vigente es `mushroom-ml-snapshot-20260816`: 395
  observaciones, 59 microáreas, 352 filas fixed y 1.408 tareas lag elegibles. Su
  manifiesto fija los benchmarks y comparaciones de aquellos informes. No es
  una dependencia de una regeneración instalada; esa parte queda reemplazada
  por la decisión de snapshot fresco por job del 2026-08-17.
- V2/V3/V4 y futuras versiones se registran de forma genérica y se preservan
  aunque dejen de ser operativas. Los estados no se codifican con condicionales
  específicos de versión.
- Bundles nuevos usan contrato de columnas e identidad semántica por área. Un
  cambio de nombre/nota no invalida; geometría, pertenencia, posición o altitud
  invalidan las áreas afectadas. Bundles legacy sin esa identidad mantienen la
  barrera estricta de hash bruto.
- Los bundles legacy pueden bloquearse ante cambios de `known_sites`; queda
  prohibido relajar la barrera o parchearlos. Los batches nuevos comparan la
  identidad de entrenamiento del snapshot fresco y muestran su vigencia en la
  UI.

## 2026-08-19 - [VIGENTE][ML] Selección genérica y promoción manual V4–V6

- V4, V5 y V6 pasan a estado técnico `candidate`, con predicción operativa y
  todos los perfiles declarados de cada versión marcados como elegibles.
- La elegibilidad significa que entrenamiento, artefactos e inferencia tienen
  contrato implementado; no significa superioridad científica ni recomendación.
- La activación continúa siendo manual y en dos pasos: candidata completa y
  confirmación separada de la versión completa. No se promociona por métricas.
- Para cada especie, perfil y contrato, cualquier estimador declarado puede
  aportar el score si su Brier hold-out mejora la prevalencia y no está excluido
  para la entrada. Gana el menor Brier; se elimina la distinción LR/RF frente a
  modelos sombra en el dictamen operativo.
- V4 hereda explícitamente la evidencia ecológica V3. V5/V6 calculan desde su
  raw365 el evento significativo de los 90 días previos y su edad al target,
  sin añadir esos campos a `X`.

## 2026-08-16 - [SUSTITUIDA 2026-08-19][BIOLOGY V4] V4 permanece propuesta, no candidata

- V4 core reproduce V3 y valida el comparador. La meteorología ampliada y el
  balance no mejoran Brier consistentemente entre especies; SoilGrids empeora
  generalmente predicción y continuidad.
- Balance y suelo se conservan, materializan, entrenan y documentan como
  experimentales, pero quedan desactivados para predicción. Desactivar nunca
  significa borrar o dejar de validar.
- Dos observaciones revisadas ya cambian ganadores y dejan `boletus_edulis` sin
  dos clases en la partición de grupos 7. El soporte no permite promoción.
- Esta era una recomendación científica conservadora. La decisión del
  2026-08-19 permite que el usuario la active manualmente sin presentarla como
  ganadora ni eliminar esa evidencia histórica.

## 2026-08-16 - [VIGENTE][HISTÓRICO METEO] Autocuración acotada de huecos oficiales

- Una instalación existente conserva el solape diario de siete días y añade un
  detector de días completos ausentes de Meteocat y AEMET más allá de ese
  margen. No interpreta el alta o baja de una estación como hueco de red.
- Los huecos se guardan en una cola persistente, agrupados en bloques máximos de
  15 días. Cada runner procesa como máximo un bloque debido por fuente y aplica
  espera de 1/2/4/7 días ante fallos.
- Meteocat mantiene dos consultas por bloque —lluvia y condiciones— y una pausa
  de cinco segundos. AEMET usa climatología diaria con una sola petición de
  hasta 15 días por runner; no se identifica este contrato conservador con el
  backfill masivo histórico, que agrupaba dos peticiones como un mes.
- Toda reparación se archiva primero en el histórico particionado. Después se
  reaplica al CSV vivo de 180 días y solo entonces se reconoce el lote. Un
  bloque antiguo repara el histórico aunque no altere el CSV; un reinicio entre
  fases conserva el pendiente y permite terminarlo en el runner siguiente.
- El resultado pendiente es degradado, no fatal, y queda en estado e informe
  persistentes. La presentación específica en Diagnostics/Errors queda
  pendiente. La implementación está validada solo en local y no está desplegada
  en HA.
- El bootstrap histórico de una instalación virgen queda fuera de este alcance
  y continúa como tarea futura no prioritaria.

## 2026-08-13 - [VIGENTE SALVO AUTORIDAD LR/RF, SUSTITUIDA 2026-08-19][BIOLOGY V3] Tres ejes, extremos meteorológicos y consenso entre estimadores

- La nomenclatura canónica separa tres ejes: **contrato temporal**
  (`fixed_gap_7d_biology_v3` o `lag_event_biology_v3`), **estimador ML**
  (seis algoritmos) y **especie**. Un modelo ajustado es una combinación
  especie × contrato × estimador. Las especies no se denominan modelos y los
  contratos no se denominan algoritmos.
- Los seis estimadores reciben exactamente las mismas columnas activas dentro
  de un contrato y una comparación. La antigua separación LR/RF frente a
  estimadores experimentales queda sustituida por la regla genérica del
  2026-08-19.
- El Brier se calcula y decide por especie. Los agregados entre especies son
  solo diagnósticos y nunca seleccionan estimador. Cada Brier se contrasta con
  la prevalencia de entrenamiento de esa misma especie.
- El consenso se mide fila a fila entre las 15 parejas de estimadores sobre el
  mismo hold-out. Se publican diferencia de probabilidad, coincidencia respecto
  a 0,5 y proporciones de consenso alto/moderado/bajo con los umbrales ya usados
  por el Predictor. No se inventa una única etiqueta agregada por especie.
- La matriz activa no contiene medias meteorológicas. Usa lluvia IDW acumulada,
  racha seca, temperatura máxima/mínima y humedad relativa máxima/mínima. Las
  medias continúan materializadas, registradas y validadas, pero quedan
  inactivas y fuera de `X`.
- Temperatura usa los extremos de los siete días anteriores al corte, con
  corrección por altitud. Humedad relativa usa extremos en ventanas 0–3, 4–7,
  8–14 y 15–21; conserva el selector V2 sensible al corte. Así se mantiene la
  secuencia conjunta con la lluvia sin imponer un mínimo de milímetros.
- No aparece un ganador universal. En `lag_event`, el ganador por Brier es
  estable entre agrupaciones 7/14: LR para Amanita caesarea, KNN para Boletus
  aereus y Morchella, RF para B. edulis y B. pinophilus, y HGB para Lactarius
  deliciosus. RF+ET es la pareja que más coincide de forma sistemática, pero
  el consenso solo se considera útil cuando ambos superan la prevalencia.
- El soporte sigue siendo pequeño: las filas de `lag_event` repiten cada
  observación por horizonte y no cuentan como observaciones independientes.
  Ningún resultado autoriza entrenar o promover un candidato operativo.

## 2026-08-13 - [VIGENTE][BIOLOGY V3] Validación temporal y gate operativo

- La validación principal usa un corte cronológico 70/30 por especie y mantiene
  enteros los grupos de florada especie+área de hasta 14 días. La repetición con
  7 días mide sensibilidad; ninguna observación se fusiona, elimina o cruza el
  corte dentro de su grupo.
- `fixed_gap_7d_biology_v3` es la vista principal por corresponder a la salida
  semanal. `lag_event_biology_v3` se conserva como diagnóstico para horizontes
  1, 2, 3 y 7, no como una competición para escoger el score más favorable.
- Las comparaciones activan todo, quitan lluvia, temperatura o humedad relativa
  por separado, quitan temperatura+humedad y usan solo meteorología. Son pruebas
  de contribución, no instrucciones para borrar variables.
- Una promoción futura exige V2/V3 sobre las mismas filas, mejora de Brier
  repetible con grupos de 7 y 14 días, calibración/log loss no peores y ausencia
  de regresiones graves por especie cuando exista soporte suficiente.
- Mes y altitud directa permanecen inactivos en `X`, materializados y
  validados; la altitud continúa aplicándose a la corrección de temperatura.
  Las conclusiones preliminares basadas solo en LR y Brier combinado entre
  especies quedan reemplazadas por la matriz de seis estimadores por especie.

## 2026-08-13 - [OBSOLETA][GIS] Eliminar la copia local `mushroom-GIS-HA`

- `mushroom-GIS-HA` fue una copia mínima de preparación para HA, no una raíz
  consumida por el código. La resolución vigente usa la variable explícita,
  `/media/rainmapper/mushroom-GIS`, `/share/rainmapper/mushroom-GIS` como
  fallback controlado y `mushroom-GIS/` en el repositorio de trabajo.
- Antes de borrarla se comprobó que no estaba versionada, no tenía procesos con
  ficheros abiertos y que sus diez ficheros de datos eran idénticos byte a byte
  a los existentes en `mushroom-GIS`; los otros dos eran `.DS_Store`.
- Se eliminó con autorización explícita el 2026-08-13, recuperando unos 5,9 GB,
  y se retiró su regla de `.gitignore` para que una reaparición no quede oculta.
- Estado `OBSOLETA` significa aquí que la carpeta/concepto queda retirado. La
  fuente local vigente es `mushroom-GIS/`; no recrear `mushroom-GIS-HA`.

## 2026-08-13 - [VIGENTE][CONTINUIDAD] El MCP Codebase no requiere autorización

- Consultar el MCP Codebase es una acción no destructiva y está autorizada por
  defecto. No pedir permiso antes de búsquedas, trazas o lectura del grafo.
- Se mantiene la obligación de consultar antes de acciones destructivas,
  escrituras en HA no autorizadas o ampliaciones materiales de alcance.

## 2026-08-13 - [VIGENTE][GIS][UI] La altitud DEM de microárea se materializa al cambiar su geometría

- Crear una microárea o cambiar su polígono calcula automáticamente mínimo,
  máximo y media de altitud mediante una malla 5x5 dentro de la geometría y los
  guarda en `known_sites` con método, fecha y fuentes DEM. Guardar sin cambio
  geométrico reutiliza el valor materializado.
- Benchmarks, entrenamiento y predicción leen la altitud guardada; no consultan
  el DEM repetidamente. La media representativa de un área sigue siendo la
  media de las altitudes DEM medias de todas sus microáreas configuradas.
- La operación automática solo acepta altitud. Vegetación, suelo, orientación y
  demás sugerencias GIS permanecen en el flujo explícito de revisión humana.
- Las dos rutas de mantenimiento —pantalla de áreas y edición/creación desde el
  mapa de observaciones— aplican la misma regla en HA `0.2.255`, cuya imagen
  está publicada pero aún no instalada. El `known_sites` vivo de HA sí fue
  materializado con backup previo y validación 58/58.
- La cadena se amplía con el MDT25 del IGN, hoja MTN50 592, como tercer
  respaldo. Una carga masiva sobre copia local resolvió 58/58 microáreas: 396
  muestras del DEM Catalunya, 9 del DEM Andorra y 15 del IGN.
  `puertomingalvo_pm_arriba` queda en 1.329,6 m de media y
  `puertomingalvo_mas_del_sapo` en 1.279,9 m. No se infiere una altitud desde
  observaciones ni nombres; si ninguna cobertura responde se conserva
  `no_data`.

## 2026-08-13 - [VIGENTE][GIS][BIOLOGY V3] DEM oficial de Andorra como fallback transfronterizo

- El DEM ICGC de Catalunya conserva prioridad. Si devuelve ausencia o `NoData`,
  Rainmapper consulta el Model Digital d'Elevacions oficial de Andorra; si
  tampoco aporta cota, mantiene `area_altitude_missing`.
- La fuente andorrana es un raster de 5 m del Govern d'Andorra/CREAF, basado en
  cartografía de 1995, con NTF / Lambert zona III (`EPSG:27563`) y elevaciones
  originales en decímetros.
- Para operación se usa un GeoTIFF derivado autocontenido: CRS embebido, metros
  `Float32`, fondo `32768` convertido en `NoData=-9999`, compresión DEFLATE y
  hash `10e9a27d97c7e3fb05b9411e8604cdd3674df128d61fbabf6a491a64ed5bbb22`.
- Validación independiente: en `obs_20260613_0001` el DEM devuelve 2073,5 m y
  el GPS del iPhone registró 2080 m, una diferencia de 6,5 m. El centro del área
  Ordino devuelve 2063,2 m.
- El derivado forma parte del dataset GIS inmutable transportado al worker y se
  reutiliza por hash en su caché. No se empaqueta en la imagen ni se transporta
  el RAR. La ausencia de licencia explícita de redistribución obliga a mantener
  los binarios fuera de Git y de releases.
- Evidencia y contrato de formato completos en `mushroom-GIS/dem-andorra/README.md`.

## 2026-08-13 - [SUSTITUIDA POR V2][BIOLOGY V3] La lluvia es IDW diaria en la microárea

- Biology V3 usa siempre una estimación espacial IDW de lluvia en el punto
  representativo de la microárea, no la estación más cercana ni un IDW solo
  cuando discrepan estaciones.
- Contrato `daily_rain_idw_radius15km_power2_v1`: radio 15 km, potencia 2 y
  distancia mínima de peso 0,1 km. Participan todas las estaciones activas con
  valor diario utilizable.
- Un cero observado es cero. Ausencia, error, valor negativo, más de 300 mm/día,
  repetición positiva consecutiva suprimida y estación retirada no participan.
  Sin contribuyentes el día queda ausente; nunca se fabrica lluvia cero.
- La fórmula coincide con MapLibre, pero el gate visual dependiente de la escala
  de color no forma parte del modelo. Prueba local real: `46,003 mm` sumando IDW
  diario y `46,059 mm` con los acumulados Tomap redondeados para la misma
  ventana/punto.
- La serie se materializa por microárea/fecha y conserva procedencia técnica
  fuera de X. Su agregación al área se rige por la decisión siguiente.
- Implementado en módulos nuevos y cubierto por pruebas; no cambia Altitude
  V2, HA ni ningún modelo promovido.

## 2026-08-15 - [VIGENTE][BIOLOGY V3/V4] Un duplicado positivo suprimido representa 0 mm

- Se conserva el IDW diario por microárea, radio 15 km, potencia 2 y agregación
  posterior por la media diaria de todas las microáreas del área.
- La decisión de calidad ya adoptada se hace efectiva y versionada: si la
  lectura de lluvia es `N/A` porque el proceso la identificó específicamente
  como repetición positiva del día anterior, esa estación aporta `0 mm` ese
  día. Es más probable que el sensor no registrase nueva lluvia que repetir
  exactamente un acumulado diario positivo.
- No se generaliza la regla: `N/A` sin esa causa, errores, negativos, valores
  mayores de 300 mm/día y estaciones retiradas siguen sin participar. Si no
  queda ningún contribuyente real o imputado, el día continúa ausente.
- Nuevos IDs:
  `daily_rain_idw_radius15km_power2_duplicate_zero_v2` y
  `area_daily_mean_microarea_idw_duplicate_zero_v2`.
- Calidad publica por separado días observados, ausentes, suprimidos e
  imputados por duplicado. Ninguno de esos contadores entra en `X`.
- El cambio está probado y aplicado solo al código y benchmarks locales; no se
  ha desplegado en HA/M1 ni se ha reconstruido un modelo operativo.

## 2026-08-13 - [VIGENTE][BIOLOGY V3] El área contextualiza la florada pero no segmenta el modelo

- Biology V3 aprende un modelo común por especie con observaciones procedentes
  de todas las áreas. `area_id` identifica el lugar donde se materializa la
  meteorología y se emite la predicción, pero no entra en X ni crea modelos
  separados por área.
- La unidad original de evidencia es la observación. Las vistas canónicas por
  microárea, fecha o área permanecen para resolver conflictos y auditar el
  target, pero no sustituyen varias observaciones por una única fila de
  entrenamiento ni reducen el recuento de evidencia disponible.
- Una florada pertenece a una especie y un área y puede contener múltiples
  observaciones. Como regla biológica general, una florada corta puede durar
  hasta 7 días y una larga hasta 14; su continuidad concreta depende de si se
  mantienen las condiciones de lluvia, temperatura y humedad. Estas ventanas
  relacionan muestras y validan ambos tipos de duración, pero no agregan ni
  eliminan observaciones. El contrato 7/14 es común a las especies objetivo;
  posibles excepciones por especie se conservarán como evidencia y solo
  cambiarán el contrato si los datos y la literatura lo justifican.
- Todas las observaciones se conservan. Las observaciones relacionadas pueden
  compartir un identificador de grupo para impedir que una misma florada cruce
  train/test, pero siguen siendo muestras separadas. Los informes publican por
  separado observaciones, fechas, áreas y grupos de validación.
- La lluvia es una condición biológica necesaria pero no suficiente. El modelo
  debe aprender cuánta lluvia, durante qué periodo y bajo qué combinación de
  temperatura y humedad resulta favorable; no se codifica un umbral biológico
  fijo como gate. Los gates del benchmark son exclusivamente de disponibilidad
  y calidad de medición.
- Una variable deja de participar en la predicción mediante estado de registro,
  no borrándola. Se sigue calculando, validando, comparando y documentando para
  que pueda reactivarse sin reconstruir su significado.

## 2026-08-15 - [VIGENTE][BIOLOGY V4] Cierre local sin candidatura operativa

- Biology V4 queda técnicamente cerrada y permanece `proposed`: no se elimina,
  no sustituye V2/V3 y conserva contratos, benchmarks, informes y variables
  para reevaluación futura.
- La comparación V2/V3/V4 usa filas idénticas, seis estimadores, especies y
  contratos separados. No existe Brier medio entre especies. El balance V4 no
  mejora Brier de forma estable: es desfavorable en fixed y aproximadamente
  equilibrado en lag, con direcciones distintas por especie.
- El balance sí reduce el parpadeo global de probabilidades diarias en ambos
  contratos y particiones 7/14, pero ese beneficio no compensa la ausencia de
  mejora predictiva consistente.
- El depósito SoilGrids `wv0033_0_30cm`, reconstruido por microárea y fecha,
  empeora continuidad en conjunto y tampoco fue ganador en Brier. Se conserva
  experimental, materializado, entrenable y validable, pero no seleccionado.
- Solo hay 50 etiquetas especie–área–fecha en las secuencias semanales del
  hold-out; no se aprende ni activa una capa de continuidad con tan poco
  soporte. Su contrato permanece desactivado para poder reabrirlo.
- La paridad local train/inferencia es exacta sobre 399 muestras fixed y 1.596
  lag para core, balance y suelo. La paridad de empaquetado HA–worker pertenece
  a una futura integración.
- Al no superar el gate no se entrena candidato V4, no se promociona nada y no
  se toca HA, M1, GHCR ni el `known_sites` operativo.

## 2026-08-13 - [VIGENTE CON SEMÁNTICA V2][BIOLOGY V3/V4] La lluvia del área es la media de sus microáreas

- Contrato vigente `area_daily_mean_microarea_idw_duplicate_zero_v2` (sustituye
  a `area_daily_mean_microarea_idw_v1` solo en el tratamiento de duplicados): cada día del área es la media
  aritmética de los IDW disponibles de todas sus microáreas configuradas. Una
  microárea ausente se omite; solo queda ausente si ninguna aporta valor.
- No se usa el IDW del centroide del área porque ese centroide es una geometría
  calculada y no un punto real de evidencia.
- El modelo acepta el resultado como lluvia canónica: sin penalización,
  intervalo de incertidumbre ni advertencia por la procedencia de las
  estaciones. AEMET, Meteocat, Meteoclimatic y Wunderground participan si sus
  datos superan las mismas reglas de validez.
- La procedencia de estaciones se conserva únicamente para reproducción y
  auditoría técnica; no entra en X ni modifica la predicción.
- Auditoría reproducible sobre 7.262 días-área: diferencia frente al centroide
  mediana 0,001 mm, p95 0,62 mm, p99 1,89 mm, máximo 7,89 mm; la dispersión
  entre microáreas llegó a 43,94 mm.
- Evidencia:
  `docker-data/audits/mushroom-weather-backfill-20260811/reports/biology-v3-area-idw-20260813.json`.

## 2026-08-13 - [VIGENTE][BIOLOGY V3] La incertidumbre se expresa en la predicción, no en cautelas operativas

- Una predicción futura siempre contiene incertidumbre. Biology V3 debe
  expresarla mediante probabilidades calibradas y un dictamen claro, no mediante
  una sucesión de reservas sobre cada dato ya aceptado por contrato.
- La lluvia media IDW, la corrección térmica y las demás entradas canónicas se
  usan como datos del modelo una vez superadas sus reglas de validez. No reciben
  penalizaciones ni advertencias repetidas por ser estimaciones.
- Procedencia, estaciones contribuyentes, dispersión y otros diagnósticos se
  conservan para reproducción y auditoría interna; no debilitan el resultado ni
  aparecen como un «sí, pero» en la predicción ordinaria.
- La UI solo muestra una advertencia cuando existe una incidencia accionable o
  el cálculo no puede realizarse. La ausencia total de un dato obligatorio puede
  provocar abstención; la mera naturaleza probabilística del futuro, no.

## 2026-08-13 - [REEMPLAZADA][BIOLOGY V3] La unidad operativa era especie, área y fecha

- Un episodio de entrenamiento es `(species_id, area_id, observed_at)` porque
  responde a «¿merecía la pena ir a algún lugar de esta área para esta especie
  en esta fecha?».
- Antes de formar el episodio se canonicalizan duplicados por
  `(species_id, micro_area_id, observed_at)`. Las filas originales, abundancias,
  conflictos e IDs se conservan como evidencia.
- El episodio es favorable si alguna microárea conocida fue favorable;
  desfavorable si todas las conocidas fueron desfavorables; desconocido si
  ninguna aportó target conocido. Un episodio mixto conserva sus recuentos y no
  se presenta como si toda el área hubiera respondido igual.
- Reconciliación sobre 399 filas: 348 unidades canónicas, 278 episodios (188 F,
  87 D, 3 desconocidos), 275 entrenables, 9 mixtos reales entre microáreas y 2
  conflictos internos. Los antiguos 275/11 eran la vista entrenable agrupada
  antes de canonicalizar; no hubo pérdida ni cambio de datos.
- Reemplazada el mismo día por la decisión «El área contextualiza la florada
  pero no segmenta el modelo»: esta agrupación se conserva como vista de
  evidencia y auditoría, pero las observaciones originales son las muestras de
  aprendizaje y no se fusionan.

## 2026-08-13 - [REEMPLAZADA][ML] Toda actualización operativa reconstruye y reentrena globalmente

- Reemplazada como dirección futura el 2026-08-18 por la separación entre
  entrenamiento operativo y benchmark científico. Sigue describiendo el
  comportamiento implementado hasta que se complete esa migración.
- Si cambian observaciones y se quiere incorporarlas al Predictor, se
  reconstruyen todos los artefactos y se reentrenan todos los modelos. La regla
  no depende de que existan 399 o 39.999 observaciones.
- La UI no ofrece reconstrucción por especie, solo pendientes ni generación de
  artefactos aislada. No se mantienen controles cuyo texto no corresponda al
  efecto real del servidor.
- Se conserva una única acción humana: `Reconstruir y reentrenar todo`,
  ejecutada por el worker externo para no cargar la RPi4.
- Motivo: un artefacto regenerado sin reentrenar no actualiza el modelo; los
  candidatos parciales pueden mezclar generaciones y conservar relaciones
  eliminadas, como ocurrió con la observación corregida Edulis/Olvan.
- Implementado y publicado en HA `0.2.252`, commit `8010b89`.

## 2026-08-13 - [VIGENTE][ARQUITECTURA] Dos jobs diagnósticos, un flujo y una activación conjunta

- La actualización completa conserva `worker_candidate_rebuild` y
  `worker_ml_train_v0` como jobs separados. Así mantienen diagnósticos, progreso,
  errores y resultados independientes sin obligar a refactorizar los motores.
- Al terminar verificado el candidato global, el coordinador crea
  automáticamente el training y le entrega el `features.json` candidato. No
  entrena sobre el artefacto vivo anterior.
- Los dos resultados se activan como una sola generación lógica: el coordinador
  reserva ambos, promociona artefactos y modelos, invalida la caché y limpia
  pendientes únicamente tras el éxito completo.
- Si falla la promoción de modelos, se restauran los artefactos previos; la
  promoción de modelos también revierte destinos escritos parcialmente.
- Esta decisión reemplaza el workflow manual sin chaining de 2026-08-03, pero
  conserva su separación técnica entre rebuild y training.

## 2026-08-13 - [VIGENTE][UX] Las discordancias ecológicas avisan, no prohíben

- Fecha fuera de meses habituales, altitud discordante o primera observación de
  una especie en un área/microárea deben producir un aviso evidente y
  confirmable al crear, editar o importar observaciones.
- El usuario puede aceptar la excepción. El sistema no reclasifica, descarta ni
  corrige automáticamente: las especies pueden fructificar fuera de los rangos
  habituales.
- El Predictor tampoco debe tratar `fuera de temporada` como una verdad absoluta
  cuando existan condiciones compatibles; debe expresarlo como cautela.
- Estado de implementación: pendiente. La decisión y el comportamiento deseado
  son vigentes; los cambios UI pertenecen al bloque posterior a Biology V3 o a
  una tarea independiente.

## 2026-08-11 - [VIGENTE][DATOS] Backfill histórico completo por fuente, aislado en el lab

- La recuperación meteorológica no se limita a las ventanas concretas de las
  observaciones ni a estaciones situadas dentro de 15 km. Se descargan todas
  las estaciones conocidas de cada servicio histórico para no tener que repetir
  la adquisición al añadir áreas, cambiar el selector o comparar otros modelos.
- El inicio común es `2012-06-19`, 150 días antes de la primera observación
  actual (`2012-11-16`). Cada fuente termina el día anterior al inicio de su
  histórico local ya materializado: Meteocat `2016-12-19`, Wunderground
  `2023-07-31` y AEMET `2026-05-24`.
- Meteoclimatic queda excluido de la descarga remota histórica mientras no haya
  una API o archivo validado. Sus datos locales existentes se conservan.
- El backfill complementa, no reemplaza, el histórico actual. La unión usa
  fuente, estación y fecha local; conserva filas y valores útiles previos, y
  nunca convierte silenciosamente una estación inexistente, un periodo vacío o
  un error de API en precipitación cero.
- El radio de 15 km es una regla posterior de selección: sobre el Parquet
  candidato se elige la estación históricamente utilizable más cercana y se
  hace fallback hasta ese límite. No es un filtro de adquisición.
- Descarga, normalización, unión, reconstrucción y benchmark se realizan primero
  y exclusivamente en
  `docker-data/audits/mushroom-weather-backfill-20260811/`, con respuestas
  crudas cacheadas y candidatos separados. HA permanece en solo lectura.
- Promover CSV a HA será una tarea posterior y explícita: exige backup,
  comprobación de cero pérdidas/duplicados, validación de unidades y rangos,
  reconstrucción coherente y comparación antes/después con rollback disponible.
- Contrato y manifiestos:
  `docs/mushrooms/mushroom-weather-historical-backfill-handoff-es.md`.

## 2026-08-11 - [VIGENTE][DISEÑO] El sucesor ML predice utilidad de salida y separa calidad

- El target operativo responde a si merecía la pena realizar una salida en el
  área y fecha: `scarce` o superior es favorable, `very_scarce/absent` es
  desfavorable y `pending/no visitado/no buscado` es desconocido.
- La unidad derivada canonicaliza primero especie, microárea y fecha; después
  agrega a área conservando número de microáreas favorables, desfavorables y
  desconocidas, conflictos y episodios mixtos. Un área es favorable si alguna
  microárea comprobada justificó la salida, pero la evidencia local no se
  elimina.
- Los contratos altitude v2 se congelan como referencia. Cualquier cambio de
  target, unidad o lista de columnas recibe nuevos IDs y no puede cargar bundles
  v2 por fallback.
- Cobertura, huecos, supresiones y censura son controles de calidad, no señal
  biológica. Permanecen auditables y deciden elegibilidad, pero no entran en la
  matriz X.
- La auditoría del snapshot actual produce 399 observaciones, 350 incluibles,
  275 episodios y 122 con meteorología utilizable para el corte fijo. Estas
  cifras son checks ligados a hashes, no constantes del producto.
- La implementación especificada termina en un benchmark sucesor; no entrena,
  promociona ni publica modelos. Referencias:
  `docs/mushrooms/mushroom-ml-v3-data-audit-es.md` y
  `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`.

## 2026-08-08 - Esquema diagnóstico 2.2 y Gantt multifuente

Estado: IMPLEMENTADO Y VALIDADO EN LOCAL; PENDIENTE DE AGRUPAR EN UNA RELEASE HA.

Decisión:

- Conservar todos los diagnósticos `2.1` ya existentes en HA. No borrarlos ni
  migrarlos destructivamente: siguen siendo válidos para métricas, anomalías,
  evolución y comparación A/B.
- Tratar la versión del esquema como capacidades. La UI marca `2.1` como
  **limited detail** y `2.2` como **full source detail**, sin inventar fases que
  una ejecución antigua no registró.
- Instrumentar las fases reales de AEMET, Meteoclimatic, Meteocat y
  Wunderground con inicio inmediato y final, y persistir los intervalos
  completos también en el resumen compacto de cada fuente.
- Usar timestamps UTC inequívocos para alinear fases paralelas con la operación
  global y evitar desplazamientos por zona horaria o DST.
- Representar cada fuente como un grupo plegable sobre el mismo eje temporal
  A/B. Al desplegarlo aparecen solo sus subfases; el detalle textual usa también
  un acordeón independiente por fuente.
- Mantener los eventos globales separados de los intervalos de las fuentes. Un
  evento de AEMET nunca se coloca bajo Wunderground por orden de presentación.

Motivo: las duraciones agregadas permiten saber qué fuente fue lenta, pero no
distinguen descarga, parseo, incremental o escritura, ni permiten representar
correctamente cuatro trabajos paralelos. Los intervalos reales permiten localizar
la fase responsable sin sacrificar los históricos previos. La especificación y
el procedimiento de validación viven en `docs/runtime-diagnostics.md`.

## 2026-08-08 - Diagnostics como observabilidad histórica comparable

Estado: IMPLEMENTADO Y VALIDADO EN LOCAL; PENDIENTE DE AGRUPAR EN UNA RELEASE HA.

Decisión:

- Sacar la caja negra de Summary y concentrar estado, evolución, comparación
  A/B, Gantt, histórico y descarga en una pestaña Diagnostics.
- No fijar siete días como horizonte único. La evolución temporal permite
  7/30/90 días o toda la retención compacta; el análisis por release conserva
  las cinco versiones más recientes disponibles.
- Separar siempre Runner de Predictor y subdividir por carga comparable. Las
  medias entre acciones, vistas o cargas frías/calientes no son válidas.
- Mantener dos planos de datos: detalle corto para fases/Gantt y resumen largo
  para series y agregados. Las comparaciones antiguas sobreviven aunque roten
  sus fases, pero la UI no inventa un Gantt cuando falta detalle.
- Representar por versión media y rango mínimo-máximo junto al número de
  muestras. Una sola ejecución se muestra como muestra única, no como evidencia
  de una tendencia.
- Cargar el histórico de forma diferida y por periodo mediante el endpoint de
  Diagnostics. Summary mantiene su polling ligero.
- Usar SVG/HTML nativo, sin incorporar una dependencia de gráficas ni una base
  de datos temporal mientras el JSONL acotado cubra el uso monousuario en RPi4.

Motivo: comparar solo ejecuciones sueltas o una ventana fija de siete días no
permite atribuir una mejora/regresión a una versión si esta se instaló antes de
esa ventana. La separación entre detalle reciente y resúmenes compactos permite
conservar contexto histórico con coste acotado y sin aumentar el trabajo del
runner. La especificación completa vive en `docs/runtime-diagnostics.md`.

## 2026-08-07 - Medición automática y exclusión runner/Predictor en RPi4

Estado: INCLUIDO EN `0.2.227` PUBLICADA; PENDIENTE DE VALIDACIÓN EN RPi4.

Decisión:

- Registrar en JSONL acotado las cargas frías del Predictor, el proceso de
  actualización y la acción completa del runner, incluyendo memoria del proceso,
  cgroup, host, CPU, temperatura, duración y contadores OOM.
- Tomar muestras durante las operaciones y snapshots de memoria retenida o
  recuperada a 60 y 600 segundos. El diagnóstico es best-effort y nunca puede
  hacer fallar una predicción o actualización.
- Impedir el solapamiento mediante un lock común. Antes de lanzar un runner se
  eliminan las instancias de Predictor, su histórico meteorológico compartido y
  se fuerza una recolección de basura. Predictor muestra un aviso multiidioma
  mientras el runner está activo.
- Exponer desde el panel un ZIP limitado a métricas, último log y manifiesto; no
  exportar configuración, credenciales, observaciones, media, modelos ni datos
  meteorológicos.
- No cerrar el P0 por estimaciones locales. Seguir el ensayo de
  `docs/runtime-diagnostics.md` y revisar los ZIP reales de la RPi4.

Motivo: las gráficas de Home Assistant pueden omitir picos breves y obligaban a
vigilar manualmente. La medición persistente permite comparar runner y Predictor
por separado y comprobar tanto el pico como la recuperación posterior.

## 2026-08-07 - Corrección P0: predicate pushdown exige row groups filtrables

Estado: INCLUIDO EN `0.2.227` PUBLICADA; PENDIENTE DE VALIDACIÓN EN RPi4.

Decision:

- Conservar el filtro top-5 a ≤15 km, pero ordenar `weather_daily.parquet` por
  `(source, station_code, local_date)` y escribir row groups de 512 filas de
  forma atómica. El Parquet operativo existente tras instalar `0.2.226` contiene
  las 625.434 filas en un único row group y
  `pd.read_parquet(..., filters=...)` todavía puede leerlo completo antes de
  filtrar.
- Rechazar el layout monolítico en la ruta interactiva antes de materializar el
  DataFrame. La UI muestra un mensaje multiidioma para ejecutar primero una
  actualización meteorológica; nunca hace fallback a cargar todos los CSV.
- Crear/refrescar el catálogo ligero en streaming si falta o está obsoleto.
- Incluir el filtro normalizado en la clave de caché, usar locks single-flight y
  hacer que instancias existentes vuelvan a consultar mtime antes de predecir.
- Entre las cinco estaciones más próximas, elegir la de mayor cobertura en la
  ventana de features ya existente de 30 días y usar distancia como desempate.
  Esto evita añadir un umbral meteorológico nuevo.

Medición local: el Parquet monolítico filtrado alcanzó 318,2 MiB de RSS máximo;
el mismo conjunto con row groups de 512 alcanzó 236,1 MiB y materializó 70.490
registros/100 estaciones. La prueba arm64/RPi4 sigue siendo obligatoria antes de
cerrar el P0.

## 2026-08-07 - P0 Predictor/RPi4: filtro espacial top-5 estaciones a ≤15 km por micro-área

Estado: REEMPLAZADA PARCIALMENTE por la corrección de row groups anterior. El
filtro espacial se conserva, pero por sí solo no resolvía el pico de lectura.

Decision:

- Filtrar `weather_daily.parquet` a las ~100 estaciones relevantes (top-5 a ≤15 km
  de cada micro-área del modelo) antes de materializar objetos `DailyWeatherRecord`.
- No usar LRU, chunks por fechas ni particionado del parquet en esta fase.
- La caché `_shared_weather_stations` con invalidación por mtime (ya en 0.2.225) se
  mantiene; ahora guardará ~100 estaciones en lugar de 1.932.
- Nuevo artefacto `weather_stations_catalog.parquet`: una fila por estación con
  coordenadas y metadatos (~100 KB), generado por el runner junto al parquet diario.
- `select_station()` ampliada para intentar hasta 5 candidatas en orden de distancia
  cuando la más cercana no tiene cobertura suficiente.

Mediciones (docker-data, 2026-08-06):

| Variante | Estaciones | Filas | Estimación RAM |
|---|---|---|---|
| Actual | 1.932 | 625.434 | ~358 MiB |
| Top-5 ≤15 km / micro-área | 100 | 70.490 | ~40 MiB |

Las 46 micro-áreas del modelo quedan cubiertas. Reducción esperada: 89%.

Motivo:

- La materialización completa del histórico provoca un pico cercano a 1 GB en RPi4,
  causando pérdida de conectividad y necesidad de corte físico de alimentación.
- El filtro espacial es el mínimo cambio efectivo: elimina el 89% de los objetos sin
  afectar al modelo, al worker ni al pipeline de entrenamiento.

Alternativas descartadas para esta fase:
- Chunks por ventana de 120 días: sin filtro espacial, los últimos 120 días siguen
  conteniendo 1.765 estaciones (124.938 filas). Beneficio menor del 80%.
- LRU de ventanas: útil como segunda optimización, no como primera.
- Particionar el parquet por estación: mejora I/O futuro, no resuelve el pico inmediato.

Ver diseño detallado en `docs/mushrooms/mushroom-predictor-design-es.md`, sección 0.4.

## 2026-08-03 - [REEMPLAZADA] Worker job ml_train_v0: dos jobs separados, no chaining automatico

Estado: REEMPLAZADA el 2026-08-13 por chaining automático del coordinador y
promoción conjunta. Sigue vigente únicamente la separación técnica de los dos
jobs para diagnóstico.

Decision:

- `rebuild_v0` genera el artefacto de features (`mushroom_observation_features_v0.json`).
  `ml_train_v0` entrena modelos scikit-learn a partir de ese artefacto. Son dos jobs
  independientes, no un job monolitico.
- El campo `triggered_by_job_id` (cadena vacia = trigger manual) es el gancho para
  chaining futuro en el coordinador. No implementado aun; trigger es siempre manual.
- `work_key = "ml_train:v0:{features_digest}"`: si el usuario lanza dos jobs sobre
  el mismo features.json, el segundo es rechazado como duplicado activo.
- `promotion_eligible = True` siempre para ml_train. La promocion es manual desde la
  UI "Workers y trabajos" (boton "Promote models").
- Sin freshness check durante la promocion de ml_train: el freshness check verifica
  que inputs de reconstruccion (observaciones, GIS, weather) no han cambiado desde
  el snapshot; no aplica a training, que solo usa el artefacto de features ya generado.
- El bundle de inputs son 3 ficheros planos escritos por el coordinador:
  `job_spec.json`, `features.json`, `known_sites.json`. Sin estructura de snapshot GIS.
- La imagen worker instala `numpy==2.4.6 pandas==2.2.2 scikit-learn==1.9.0`.
- Staging usa prefijo `ml.{job_id}` para evitar colision con directorios de resultado
  de rebuild que usan solo `{job_id}`.
- Endpoints separados para evitar confusion: `/api/mushrooms/workers/jobs/ml-result-file`
  y `/api/mushrooms/workers/jobs/ml-result-complete`.

Motivo:

- Separar reconstruccion y entrenamiento permite reutilizar el mismo artefacto de
  features para multiples runs de training sin repetir GIS/DEM ni meteorologia.
- El chaining automatico requiere logica de coordinador no implementada; la separacion
  permite entregar el primer training sin esa complejidad.

Consecuencias:

- `mushroom_worker_jobs.py`, `mushroom_worker_results.py`, `mushroom_worker_transport.py`,
  `mushroom_worker_service.py`, `web_server.py`, `mushroom_workers_ui.py` y
  `rainmapper-worker/Dockerfile` modificados.
- Nuevo script `scripts/run-mushroom-ml-train-job.py` (subprocess del worker).
- 9 labels nuevos en `mushroom_labels.json` (`ui.worker_ml_train*`).

## 2026-08-03 - UI Predictor completada (Fase 4)

Estado: VIGENTE

Decision:

- Pantalla "Predictor" en `mushroom_predictor_ui.py` con 4 vistas:
  "Esta semana", "Por especie", "Consultar fecha", "Historial".
- Historial con tarjetas de estadisticas clicables que filtran por correct/FN/FP.
- Cache lazy por especie en `web_server.py`; modelos joblib cargados bajo demanda.
- Al faltar joblib (modelos no entrenados), `raise ImportError` en lugar de
  `sys.exit()` para no matar el servidor.

Bugs corregidos durante implementacion:

- numpy 1.25.2 → 2.4.6 para compatibilidad con joblib generado por scikit-learn 1.9.0.
- scikit-learn 1.9.0 anadido a `requirements.txt`.
- Historial usaba key `date`; corregido a `observed_at`.
- Estadisticas FN/FP usaban key `actual_label`; corregido a `actual`.
- Columna "Real" mostraba etiqueta de 3 vias; corregida a binaria favorable/no favorable.

## 2026-08-02 - Analisis de viabilidad ML: 8 especies, corte 2018+, Meteocat

Estado: VIGENTE

Decision:

- Dataset disponible al 2026-08-02: 772 observaciones (126 `include` + 646
  `review` pendientes de revision). Con corte 2018+ y fuente weather Meteocat,
  8 especies alcanzan el umbral minimo de ≥20 observaciones para un primer
  modelo con sentido.
- Especies viables (observaciones ≥20 desde 2018): Boletus edulis 152, Boletus
  aereus 151, Boletus pinophilus 100, Lactarius deliciosus 93, Amanita caesarea
  77, Hygrophorus marzuolus 66, Cantharellus cibarius s.l. 28, Morchella elata
  complex 22.
- Las 9 especies restantes tienen entre 2 y 7 observaciones y no entran en
  el modelo v1.
- Corte 2018+: Meteocat (XEMA) proporciona datos desde 2016-12-20. Las
  observaciones anteriores a 2018 son pocas (≤19 por especie) y no justifican
  el coste de revision para el modelo predictivo v1.
- Fuente weather confirmada para el modelo: Meteocat es la unica fuente con
  historico util para el periodo 2017-2022. Wunderground y Meteoclimatic tienen
  cobertura mas limitada hacia atras.
- Umbral empirico de observaciones: 22 (Morchella elata complex) se considera
  limite con incertidumbre alta; 66+ (Hygrophorus marzuolus) es un punto de
  partida comodo. Se usa ≥20 como criterio de entrada al modelo v1.
- El framing "primera especie: boletus_aereus" del plan ML original estaba
  escrito con 13 observaciones. Con el dataset actual, B. edulis lidera (152
  obs) y B. aereus queda en segundo lugar (151 obs). Ambas son candidatas
  igualmente validas para el primer modelo.

Motivo:

- La campana de importacion masiva de fotos de campo (646 observaciones)
  amplio el dataset de forma significativa en agosto 2026.
- Sin datos meteorologicos historicos, una observacion antigua no aporta al
  modelo predictivo aunque este bien documentada; la revision manual no
  justifica ese coste para el modelo v1.

Consecuencias:

- `docs/mushrooms/mushroom-ml-training-plan-es.md` actualizado: alcance
  multi-especie, tabla de 8 especies viables, corte 2018+, Meteocat confirmado
  como fuente weather, umbral empirico documentado.
- Las 646 observaciones importadas estan en estado `review` y deben revisarse
  antes de usarlas en calibracion o entrenamiento.
- Las observaciones pre-2018 siguen siendo validas como contexto y para futura
  expansion de cobertura weather, pero no entran en el modelo v1.

## 2026-07-20 - Publicacion HA 0.2.208 con coordinador externo

Estado: PUBLICADA, PENDIENTE DE INSTALAR EN HA

Decision y resultado:

- El usuario autorizo expresamente el paso de release. Se publico la imagen HA
  normal `ghcr.io/cginebrosa/rainmapperha:0.2.208` y `latest`, sin crear una
  imagen de desarrollo/sideload.
- Ambos tags apuntan al digest multi-arch
  `sha256:68990c43959f31a9364b18aed2c053ef2487385d283251ba6c72302a166552ab`,
  con manifests `linux/amd64`
  `sha256:82cb3d9584862b8e5bcd85fb8acc6fcd3923e5cb8cf9de633c7017560d660410`
  y `linux/arm64`
  `sha256:0be801513e0a0a397a8363731ea868d4ee5c8bb85c57640205fbc605fffbb724`.
- La importacion remota arm64 cargo coordinador/UI/core y confirmo version
  `0.2.208`, conexiones externas `False` y reconstrucciones externas `False`.
- Commit `e2f117d Release Home Assistant 0.2.208` pusheado a
  `origin/inicial`.

Validacion previa:

- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: OK, 369 tests.
- Tests focalizados de empaquetado/configuracion/auth: 167 OK.
- Validador micologico: 0 errores/11 warnings conocidos.
- Sin secretos, datos privados, GIS/DEM ni ficheros grandes en el contenido
  versionado o en las imagenes.

Pendiente:

- Instalar `0.2.208` en HA, comprobar arranque/fallback con ambos interruptores
  apagados y solo despues configurar privadamente `8100` y emparejar el M1.

## 2026-07-20 - Listener privado y dos interruptores para workers externos

Estado: VIGENTE

Decision:

- La web y el Ingress conservan `8099`. El protocolo headless del worker usa
  un segundo listener dedicado en `8100`; cada listener aplica una lista
  cerrada de rutas y rechaza las del otro.
- `8100/tcp` se declara en la app HA pero queda sin publicar por defecto. La
  instalacion real debera asignarle un puerto host privado y limitarlo mediante
  LAN/Tailscale, ACL y TLS segun la topologia elegida.
- La configuracion HA muestra dos opciones independientes:
  `Enable external worker connections` arranca el listener y
  `Allow external rebuilds and promotion` autoriza trabajo operativo. Ambas
  quedan desactivadas por defecto y la autenticacion Bearer es obligatoria.
- Los controles humanos de workers que permanecen en `8099` solo aceptan el
  proxy Ingress autenticado de Home Assistant. El laboratorio local habilita
  su acceso directo mediante un flag explicito que no se activa en HA.
- Borrar el token persistido del worker es una operacion local y no depende de
  que el coordinador anterior siga accesible.

Consecuencias:

- Una sonda manual desde el contenedor worker alcanzo `8100` por la red Docker;
  el host solo publico la web de laboratorio y `8099` rechazo el protocolo. El
  proceso worker antiguo no se reinicio y conserva en memoria `:8099` hasta que
  el launcher migre su configuracion en el proximo arranque. Suite: 369 tests;
  validador: 0 errores/11 warnings conocidos.
- El empaquetado local construido con el Dockerfile HA normal quedo
  inspeccionado sin volumenes: no contiene datos privados/GIS ni credenciales y
  conserva el fallback `legacy`. Quedan para P1 la eleccion/prueba de la
  publicacion privada, ACL y TLS reales. No se ha autorizado ningun bump,
  release, commit/push ni instalacion.

## 2026-07-20 - Cierre seguro del coordinador antes del empaquetado HA

Estado: VIGENTE

Decision:

- La API del worker permanece deshabilitada por defecto; la autenticacion es
  obligatoria por defecto y el modo operacional exige API y autenticacion.
- Los mensajes JSON del protocolo se limitan a 64 KiB; los uploads de
  artefactos conservan limites separados.
- Todo path recibido en manifests de snapshots/GIS debe ser relativo,
  normalizado y quedar dentro de su raiz. Se recalcula tambien la huella de
  identidad del manifest.
- Una promocion externa elimina paths auxiliares del worker y rebasa los
  metadatos conocidos a las rutas autoritativas de HA antes de instalar los
  nueve artefactos.
- `docker-data` y `mushroom-GIS` permanecen fuera del contexto de imagen. El
  coordinador puede empaquetarse en la siguiente imagen HA sin quedar
  habilitado hasta definir la opcion y la exposicion privada.

Consecuencias:

- La suite consolidada queda en 366 tests y el validador en 0 errores/11
  warnings conocidos.
- La topologia del puerto de HA, TLS/ACL Tailscale y la inspeccion de la imagen
  construida siguen siendo P1 y bloquean cualquier publicacion, no este cierre
  local.

## 2026-07-20 - Version HA normal antes de probar el worker contra HA real

Estado: VIGENTE

Decision:

- No existe ni se creara una imagen HA de desarrollo/sideload para probar el
  worker.
- La release `0.2.207` no contiene el coordinador, pairing, registro/heartbeat,
  cola, transporte ni UI del worker; por ello no puede participar en una prueba
  funcional M1 ↔ HA real.
- Primero se revisara y consolidara el prototipo local. Despues se preparara una
  version HA normal con coordinador, UI, los tres alcances y fallback HA.
- Bump, build/push, commit/push e instalacion solo se haran tras una peticion
  expresa del usuario.
- Solo despues de instalar esa version se emparejara el M1 con HA real y se
  probaran red, seguridad, cache, reconstruccion completa/parcial,
  cancelacion, freshness y promocion.
- La topologia Tailscale del host/sidecar puede estudiarse antes, pero no se
  presentara como una prueba funcional contra `0.2.207`.

Motivo:

- Probar HA real antes de que HA contenga el coordinador es circular e
  imposible; introducir una imagen paralela de desarrollo crearia complejidad
  operacional que el usuario ha descartado.

Consecuencias:

- Queda REEMPLAZADO cualquier orden anterior que situara la prueba M1 ↔ HA real
  antes de la nueva version HA.
- La reconstruccion local de HA permanece siempre como fallback y no depende de
  que exista un worker disponible.

## 2026-07-18 - Limpieza conservadora de GHCR tras 0.2.207

Estado: COMPLETADA

- Se eliminaron 60 package versions de `0.2.194` a `0.2.205`, incluidos sus
  auxiliares sin tag.
- GHCR conserva 10 entradas: `0.2.207/latest`, rollback `0.2.206` y los cuatro
  manifests auxiliares multi-arch/attestation de cada push.
- Tras la limpieza, `0.2.207`, `latest` y `0.2.206` respondieron anonimamente
  con HTTP 200 y `docker buildx imagetools inspect` confirmo `amd64`, `arm64` y
  attestations.
- El repo GitHub continua publico y no se modificaron releases ni versiones.
- Actualización 2026-08-13: tras validar HA `0.2.252`, se eliminaron 110
  entradas antiguas. GHCR conserva exactamente 10: `0.2.252/latest`, rollback
  `0.2.251` y los cuatro manifests auxiliares de cada índice. Ambos tags
  versionados siguen resolviendo `linux/amd64`, `linux/arm64` y attestations.
- Actualización 2026-08-14: con `0.2.254` instalada y `0.2.255` publicada pero
  todavía no instalada, se eliminaron las diez entradas de `0.2.251` y
  `0.2.252`. Se conservaron 15 entradas: `0.2.255/latest`, la activa `0.2.254`,
  `0.2.253` como rollback de la activa y los cuatro auxiliares de cada índice.
  Los cuatro tags consultables se verificaron después del borrado; mantienen
  índices OCI con `linux/amd64`, `linux/arm64` y attestations, y
  `0.2.255/latest` comparten el digest
  `sha256:6f91231bb721d2bdffeb56e05c77573e1f08350ef0e851271b57856c3c782de2`.

## 2026-07-18 - Objetivo V0 gobernado por el catalogo de abundancia

Estado: VIGENTE

Decision:

- Las observaciones guardan `flush_abundance`; no guardan un segundo objetivo
  manual ni requieren migracion.
- Cada entrada de `catalogs.observation_flush_abundance` define el entero
  tecnico `prediction_favorable` (`0`/`1`). El pipeline deriva de ahi el
  objetivo favorable/desfavorable y lo materializa en artefactos reconstruibles.
- `analysis_result` (`present`/`absent`) conserva su significado biologico y de
  compatibilidad, pero no es el objetivo de entrenamiento V0.
- La politica, mapping y huella del catalogo se incluyen en los artefactos y el
  modelo para auditar cada reconstruccion.
- Una reconstruccion debe fallar de forma explicita si falta el campo o no es
  un entero 0/1; no se permite un fallback hardcoded silencioso.

Motivo:

- La utilidad predictiva buscada es decidir si una salida merece la visita, no
  solo si hubo algun ejemplar.
- Mantener la regla en el catalogo permite cambiar la politica sin duplicar
  datos derivados en las observaciones ni usar textos traducibles como claves.

Consecuencias:

- El catalogo persistente de HA debe actualizarse antes de reconstruir con una
  politica nueva.
- La UI puede mostrar Favorable/Desfavorable junto a la abundancia original sin
  anadir otra columna ni alterar el JSON fuente.
- Falta verificar explicitamente en HA los recuentos finales de todas las
  abundancias tras la reconstruccion `0.2.207`.

## 2026-07-18 - Plataforma privada de computo externo para reconstruccion y ML

Estado: VIGENTE

Decision:

- Generalizar el worker V0 a una plataforma de jobs privados para
  reconstruccion, construccion de datasets, entrenamiento y evaluacion ML.
- La primera topologia sera solo HA + Mac M1. M5 y una posible VM en AWS quedan
  como destinos futuros y no bloquean la primera implementacion.
- Conservar la reconstruccion V0 local de HA como fallback permanente. El
  entrenamiento ML experimental puede esperar al worker sin fallback en la
  Raspberry ni afectar al modelo activo.
- HA y el worker deben llamar a pipelines compartidos en `rainmapper_core`, con
  entradas/salidas explicitas; no se aceptan implementaciones paralelas.
- Separar `rebuild_v0`, `build_ml_dataset`, `train_ml_model` y
  `evaluate_ml_model` para reutilizar datasets inmutables sin repetir GIS/DEM o
  meteorologia en cada entrenamiento.
- El primer worker ejecutara en el M1 una imagen ligera, sin GIS/DEM ni otros
  datasets pesados semiestaticos. HA conserva su copia autoritativa; el worker
  los sincroniza la primera vez a un volumen persistente versionado y despues
  solo cuando cambia el manifest.
- Imagen, servicio/contenedor y volumen usaran nombres genericos
  `rainmapper-worker:<version>`, `rainmapper-worker` y
  `rainmapper-worker-data`; no llevaran sufijos M1/M5 ni configuracion del host.
  La imagen y el Compose seran identicos al moverlos. El primer arranque solo
  necesitara bootstrap seguro de HA/Tailscale, generara una identidad opaca y
  creara o reutilizara el volumen persistente.
- La imagen se construira y transferira de forma privada con Docker; no se
  publicara en GHCR ni en Internet. `docker save/load` no transporta el volumen;
  un host nuevo lo reconstruye desde HA o mediante una exportacion privada
  separada y validada.
- HA seguira siendo fuente de verdad de datos vivos, jobs y artefactos
  operativos aceptados. El worker iniciara conexiones, descargara snapshots y
  subira resultados; nunca escribira directamente en las rutas vivas.
- La comunicacion usara una URL Tailscale fija de HA. Se evaluaran Tailscale en
  el host y Tailscale dentro del despliegue Docker; esta segunda opcion favorece
  portabilidad, pero requiere un spike de red/permisos y no elude las politicas
  de un equipo de trabajo.
- Una reconstruccion V0 obsoleta se rechaza. Un run ML puede conservarse como
  candidato historico ligado a su snapshot/dataset, pero ningun modelo se
  activa automaticamente: la promocion sera humana, explicita y reversible.

Motivo:

- La reconstruccion completa medida por el usuario tarda aproximadamente 40 s
  en un M1 Pro y 4 min 44 s en HA/Raspberry Pi.
- El mayor coste inicial esta en reconstruccion GIS/meteo y features; despues,
  validacion cruzada y experimentos ML pueden reutilizar la misma capacidad sin
  duplicar transporte, seguridad ni coordinacion.

Consecuencias:

- No cambia el release HA actual. Desde el 2026-07-19 existe un prototipo local
  del pipeline comun y un CLI de salida aislada. El mismo dia se anadio
  `InputManifest 0.1`,
  snapshot privado con hashes y comparacion semantica automatica; los nueve
  artefactos resultaron equivalentes a HA `0.2.207`. Despues se conecto
  `web_server.py` al pipeline mediante un flag opt-in, con `legacy` como default;
  una imagen HA local aislada completo la ruta compartida en unos 41,7 s y
  mantuvo equivalencia 9/9 sin tocar datos vivos. El adaptador compartido
  genera los nueve artefactos en staging, los promociona con rollback y solo
  entonces limpia el estado pendiente. Se verificaron fallos unitarios en las
  cuatro fases, rollback durante promocion, un fallo real en Meteorologia
  despues de GIS/DEM y cancelacion real al 1 % de GIS/DEM; en ambos runs reales
  se conservaron los nueve artefactos aceptados y se limpiaron temporales.
- `JobSpec 0.1` y `ResultManifest 0.1` quedan implementados localmente. El job
  fija snapshot, datasets, alcance y nueve salidas; el resultado liga sus nueve
  hashes/tamanos al job y comprueba contadores derivados de los JSON. Un run
  real dio 9/9 artefactos validos y equivalentes; alterar el snapshot declarado
  o un artefacto hizo fallar la validacion.
- La ruta compartida sigue siendo opt-in y `legacy` continua como default. No
  se cambiara ese default ni se publicara una version HA sin una decision y
  validacion explicitas.
- Pipeline, snapshot y contratos de job/resultado ya estan verificados en
  local. La primera imagen `rainmapper-worker:local-contract-test` tambien queda
  validada en arm64: 151.477.088 bytes, contenido minimo, ejecucion no-root sin
  red, job completo en 42,130 s y 9/9 artefactos equivalentes. El volumen
  `rainmapper-worker-data` sobrevivio al reemplazo del contenedor y fue
  verificado desde una instancia nueva. La cache GIS versionada y su transporte
  autenticado se probaron despues localmente; Tailscale sigue pospuesto hasta
  cerrar fallos/freshness y primera descarga grande real.
- El roundtrip local `docker save/load` queda comprobado: TAR de 151.497.216
  bytes y SHA-256
  `69a266478efdcdb45cb4e19afa928c5a10e917bb81a6745e9806bea4545829c2`;
  `docker load` restauro una etiqueta retirada con el mismo image ID y esta
  reutilizo el volumen 9/9 sin red ni pull. Esto valida formato y arranque
  local, no sustituye una futura prueba en daemon limpio u otro host, porque la
  etiqueta original mantuvo las capas durante el ensayo.
- La sincronizacion de datasets pesados usa staging, hashes y activacion
  atomica. Un fallo conserva la version anterior y no inicia el calculo. Desde
  el 2026-07-19 esa semantica esta implementada y probada localmente para
  `mushroom_gis_v0`: 10 ficheros/6.306.367.027 bytes en
  `rainmapper-worker-data`, verificacion profunda valida, reutilizacion
  superficial sin recopia y rebuild sin montaje GIS del host en 42,033 s con
  equivalencia 9/9. Desde el 2026-07-20 el coordinador sirve ademas manifest y
  bytes por un endpoint ligado a Bearer/worker/claim y a los paths exactos del
  JobSpec. El worker compara fingerprint, comprueba espacio, transmite
  directamente a staging y activa atomicamente. Tests sinteticos validan carga
  ausente, reutilizacion sin red, cambio y fallo conservando la version activa.
  Una prueba real posterior partio de un volumen nuevo aislado, transfirio los
  10 ficheros/6.306.367.027 bytes, supero verificacion profunda y en un segundo
  job reutilizo la cache con cero bytes. El volumen habitual no se sustituyo ni
  borro. Sigue pendiente una segunda version real del dataset y repetir la
  portabilidad en otro host/daemon.
- La primera UI solo necesitara HA/M1. M5 y AWS requeriran sus propias pruebas
  de arquitectura, privacidad, red, rendimiento y coste cuando se incorporen.
- La interfaz humana se centraliza en la UI de Rainmapper, no en el contenedor
  headless. La primera pantalla local `Workers y trabajos` consulta el health
  real mediante la red Docker privada `rainmapper-local-compute`, conserva HA
  como destino operativo y deja visible pero deshabilitada la ejecucion externa
  hasta que el worker anuncie una API de jobs compatible. La consulta directa
  inicial de un unico health queda reemplazada por registro/heartbeat outbound:
  cada instalacion persiste `worker_id` y nombre visible en su volumen, anuncia
  aparte la maquina fisica y la UI renderiza una coleccion de workers. El nombre
  humano nunca sustituye al ID opaco. No se simulara un envio externo ni se
  duplicara la logica de reconstruccion.
- La identidad de trabajo se separa de la asignacion: un `work_key` derivado de
  tipo, alcance y snapshot impide dos ejecuciones equivalentes activas aunque
  apunten a workers distintos. Un claim usa lease/token y queda revocado al
  reasignar antes del inicio; despues del inicio se cancela y se crea otro
  intento. El calculo corre en un subproceso supervisado para permitir
  cancelacion cooperativa o forzada sin detener heartbeats. HA puede cercar y
  rechazar resultados de un worker incomunicado, pero no matar fisicamente un
  contenedor remoto sin un canal de administracion adicional.
- El alta local usa pairing, no copia manual de tokens: Rainmapper muestra un
  unico codigo temporal activo de 10 minutos/uso unico y el launcher lo recibe
  por stdin o prompt oculto. HA guarda solo el hash del token permanente por
  `worker_id`; el token real vive exclusivamente en el volumen del worker.
  Heartbeat y API de jobs exigen Bearer, una nueva alta rota la credencial y la
  UI puede revocarla. Revocar da de baja tambien el registro/heartbeat visible
  y restablece HA si ese worker era el ejecutor predeterminado; el historial de
  jobs conserva el nombre del destino. La URL de ping sigue siendo publica solo para descubrir
  compatibilidad y que hace falta pairing, no para ejecutar trabajos.
- La entrega de inputs del worker se hace por pulls HTTP autenticados y
  autorizados tambien por el claim del job. Rainmapper congela `JobSpec 0.1`,
  manifest y datos vivos en un bundle privado; el worker solo puede pedir paths
  declarados, descarga a staging con limites y SHA-256 y exige la huella GIS
  exacta antes de persistir. La prueba local real transfirio 7 ficheros y
  111.031.244 bytes sin montar `docker-data`, ejecutar el pipeline ni modificar
  el modelo. Si falta la version GIS requerida, el mismo contrato descarga solo
  los paths declarados a staging, valida SHA-256 y activa la version de forma
  transaccional antes de iniciar el calculo.
- Desde el 2026-07-20 el protocolo local ejecuta ademas un rebuild candidato
  completo. El worker usa el pipeline compartido en un subproceso cancelable,
  publica progreso, sube primero `ResultManifest` y despues las nueve rutas
  exactas. Rainmapper vuelve a autorizar por Bearer/worker/claim, valida contrato,
  tamanos, hashes y contadores, guarda solo un candidato privado y lo compara
  contra los artefactos vivos. La primera prueba real termino 9/9 `equivalent`;
  las nueve huellas vivas permanecieron intactas.
- Una validacion local integral posterior comprobo cancelacion cooperativa y
  forzada durante GIS/DEM, limpieza de parciales, corte/reconexion de la red
  Docker con continuacion del mismo job, reintentos idempotentes y rechazo de
  corrupcion o inputs obsoletos. La promocion operativa es siempre manual: HA
  vuelve a validar el candidato y la freshness, instala atomicamente las nueve
  rutas, conserva los artefactos anteriores en una copia por `job_id` y solo
  despues limpia el estado pendiente. El primer job operativo local completo
  termino en 49 s, fue 9/9 equivalente y se promociono con copia de seguridad y
  recibo auditable. Para evitar acumulacion, solo se conservan las dos copias de
  promocion mas recientes; cada una contiene los nueve artefactos derivados
  (aproximadamente 2 MB), no GIS/DEM. La poda de copias anteriores ocurre
  unicamente despues de una promocion exitosa.
- El selector externo se habilita exclusivamente en el Compose del laboratorio
  mediante `RAINMAPPER_WORKER_OPERATIONAL_ENABLED=true`. Admite alcance
  completo, pendientes y una especie. En alcances parciales, Rainmapper crea
  antes de la promocion un conjunto completo mezclando solo los IDs declarados
  por el JobSpec con las salidas vivas; despues sustituye atomicamente las nueve
  rutas. El valor por defecto, el release HA y sus rutas de fallback no cambian.
  Habilitarlo en HA real exige una decision/release posterior y una prueba
  Tailscale.
- La unica entrada visible para iniciar reconstrucciones pasa a ser `Workers y
  trabajos`. El aviso de modelo desactualizado y las antiguas acciones de
  Observaciones/modelo aprendido navegan alli con el alcance preseleccionado;
  no lanzan una reconstruccion al hacer clic. La pagina conserva `Todas`,
  `Pendientes` y `Una especie` para HA.
- El registro privado multi-worker conserva tambien un
  `default_executor`: `home_assistant` o `worker:<worker_id>`. Es una
  preseleccion explicita, no una politica de failover. Si ese worker esta
  desconectado, no emparejado, sin API compatible o no admite el alcance, la UI
  bloquea el envio, explica el motivo y permite elegir manualmente HA u otro
  destino. Nunca cambia a HA en silencio. Dos reconstrucciones externas sobre
  especies disjuntas pueden ejecutarse en paralelo, pero una completa o dos
  alcances con especies comunes se rechazan mientras sigan activos. Sus
  promociones se serializan para que cada mezcla parcial lea el ultimo modelo
  aceptado y no pierda el resultado disjunto promocionado justo antes.
- La barra superior de `Workers y trabajos` contiene las acciones compactas de
  emparejamiento y ejecutor predeterminado, siguiendo el mismo patron visual de
  las pantallas de mantenimiento. La seleccion parcial externa se habilito solo
  despues de validar contrato, mezcla, cancelacion y promocion local.
- El diseno completo y sus preguntas abiertas quedan en
  `docs/mushrooms/mushroom-v0-external-worker-design-es.md`.

## 2026-07-11 - Cache-busting runtime del MapLibre protegido

Estado: VIGENTE

Decision:

- El `index.html` protegido de MapLibre debe servirse con `Cache-Control:
  no-store`.
- `web_server.py` debe reescribir los query strings de assets del visor
  protegido a `RAINMAPPER_APP_VERSION`.
- Los cache-busters versionados de `index.html` siguen actualizandose con cada
  release, pero la ruta protegida no debe depender solo de ese valor estatico.

Motivo:

- En `0.2.198`, la imagen contenia el codigo nuevo del popup IDW con
  `pointValues.rain`, pero el HTML seguia referenciando `app.js?v=0.2.196`.
- En navegadores/HA esto podia cargar JavaScript antiguo aunque la imagen nueva
  estuviera instalada.

Consecuencias:

- Si un cambio de MapLibre no aparece en HA, comprobar primero el HTML servido,
  el query string de assets y la cache antes de modificar el calculo.
- `0.2.198` queda reemplazada funcionalmente por `0.2.199` para esta parte.

## 2026-07-11 - Backfill mensual con ventanas locales exactas

Estado: VIGENTE

Decision:

- `backfill_months_enabled` activa reconstrucciones por ventanas mensuales.
- Antes del primer lanzamiento se hace backup de incrementales.
- `months_init`, `months_end`, `months_interval` y
  `backfill_pause_seconds` controlan el rango, tamano de ventana y pausa.
- `Current step` debe mostrar tambien las pausas entre ventanas.
- Wunderground en modo backfill mensual recibe fechas locales exactas
  `YYYY-MM-DD` de la ventana; no debe aplicar el desplazamiento/relectura del
  modo normal por dias.
- El modo normal por dias mantiene deliberadamente la relectura de mes anterior
  cuando el rango cruza mes, para refrescar datos recientes que Wunderground
  puede cerrar tarde.

Motivo:

- El primer backfill mensual reutilizo la logica normal de Wunderground y
  repitio llamadas de meses adyacentes, por ejemplo julio de 2024 en dos
  ventanas consecutivas.
- Ese comportamiento es util en updates normales cercanos a cambios de mes,
  pero no en una reconstruccion administrativa por ventanas exactas.

Consecuencias:

- Hay dos comportamientos deliberados: backfill mensual exacto y update normal
  tolerante/relector.
- Para reconstrucciones largas, el coste esperado sigue siendo estacion x mes;
  usar filtros, ventanas pequenas y pausas.

## 2026-07-11 - Filtro de estaciones por fuente en backfill

Estado: VIGENTE

Decision:

- `backfill_station_filter` acepta entradas con separador `source::ids`.
- Ejemplo: `wunderground::ICANIL20`.
- Los IDs multiples se separan por coma.

Motivo:

- Reconstruir historico completo por todas las estaciones es innecesario cuando
  solo se han anadido una o dos estaciones.
- El separador `::` evita ambiguedades razonables si algun ID externo contiene
  `:`.

Consecuencias:

- Wunderground ya se puede probar de forma acotada por estacion.
- La sintaxis conserva sitio para extender el filtro a otras fuentes sin crear
  parametros separados por fuente.

## 2026-07-11 - Valores IDW puntuales en popup MapLibre

Estado: VIGENTE

Decision:

- El popup de click largo debe mostrar `Valores IDW` antes de la estacion con
  lluvia mas cercana.
- Debe calcular y mostrar todas las metricas relevantes del punto, no solo la
  metrica seleccionada en el mapa.
- Orden actual: lluvia, temperatura, temperatura corregida por DEM, humedad y
  viento/racha.
- Si el punto no tiene soporte IDW para una metrica, mostrar `-`.

Motivo:

- El color del overlay ayuda por zonas, pero para consultar un punto concreto el
  usuario necesita valores numericos sin cambiar de selector de variable.

Consecuencias:

- El calculo extra se ejecuta solo al click largo, no en cada render continuo.
- La lluvia debe aparecer aunque el mapa tenga seleccionada otra metrica.

## 2026-07-11 - API keys locales y Meteocat

Estado: VIGENTE

Decision:

- El entorno local puede pasar `GMAP_API_KEY` y `AEMET_API_KEY` desde variables
  de entorno si las opciones HA locales no las tienen.
- No guardar claves reales en el repo.
- No anadir de momento una clave Meteocat a `config.yaml`.

Motivo:

- La clave detectada era de Meteocat, pero el flujo actual usa Dades Obertes de
  GENCAT; no sirve para resolver el limite historico de esa fuente sin cambiar
  la integracion.

Consecuencias:

- AEMET local no deberia fallar por ausencia de variable si existe en `.venv` o
  en el entorno que arranca Docker.
- Meteocat historico con token queda descartado por ahora.

Actualizacion 2026-07-10: `0.2.194` cambia Wunderground para usar la API diaria JSON como fuente primaria de datos mensuales, con fallback al scraper HTML solo cuando la API no devuelve datos. Para que el rendimiento mejore realmente, los metadatos de estacion se leen de `estacions_wunderground.csv` y solo se consulta HTML si falta cache o si la API falla. Prueba local con 99 estaciones: `scrape_seconds=8.2s`, `Updated stations: 99`, `Failed stations: 0`, `API fallback errors: 6` para `ICASCA2`, `IPUIGR11` e `IQUERA1` en dos cortes mensuales. Estado de release: REEMPLAZADA por versiones posteriores; la decision de API primaria Wunderground sigue VIGENTE.

Actualizacion 2026-07-11: la correccion por altitud de la capa MapLibre `IDW`
deja de ser una aproximacion por altitud media de estaciones y pasa a usar DEM
Terrarium/Mapzen por celda, solo para metricas de temperatura. El calculo se
mantiene en navegador, acotado por viewport y limites conservadores de
celdas/tiles; si el DEM externo no esta disponible o excede esos limites, el
visor vuelve al IDW normal. La cabecera del mapa solo muestra estado cuando el
usuario tiene IDW activo, esta mirando temperatura y la correccion esta
activada: badge verde `IDW DEM` si se usa DEM, badge rojo `IDW sin DEM` si hay
fallback. Con correccion desactivada o metrica no temperatura, no muestra badge.
Se anade `maplibre_estimated_field_dem_zoom` como default HA y setting por
dispositivo (`8|9|10`, default `9`), mas globos de ayuda traducidos solo en los
settings IDW para evaluar el patron antes de llevarlo al resto de paneles.
Estado de release: REEMPLAZADA por `0.2.199`; la decision tecnica DEM sigue
VIGENTE. Publicado originalmente en imagen HA `0.2.196` y `latest`, digest
multi-arch
`sha256:98ff4f9399cf0ef9f8b3bf8b513b92c9977ac6f520fbbc634af6a39374ba4284`;
la validacion activa ya no es esta version sino `0.2.199`.

## 2026-07-10 - GHCR multi-arch y repo publico durante instalacion HA

Estado: VIGENTE

Decision:

- Mantener el repositorio GitHub abierto/publico durante la deteccion,
  instalacion o update de Home Assistant cuando HA necesite leer metadata desde
  GitHub.
- No limpiar GHCR hasta que el usuario confirme que la version HA actual instala
  y arranca.
- Al limpiar GHCR, conservar siempre la version activa, `latest`, el rollback
  inmediato y las entradas auxiliares sin tag asociadas a los manifests
  multi-arch/attestations de esas versiones.
- Si HA devuelve `manifest unknown` para una version recien publicada, verificar
  primero con `docker buildx imagetools inspect` y con acceso anonimo al
  manifest GHCR antes de hacer bump de version.

Motivo:

- Tras publicar `0.2.193`, una limpieza GHCR borro manifests auxiliares sin tag
  del push multi-arch. Docker local seguia pudiendo mostrar informacion parcial
  si habia cache/autenticacion, pero HA fallo con `manifest unknown`.
- Republicar la misma etiqueta `0.2.193` restauro los manifests necesarios sin
  cambiar codigo ni version.

Consecuencias:

- La limpieza GHCR debe ser conservadora y consciente de la estructura
  multi-arch, no solo de tags visibles.
- No cerrar el repo ni tocar el paquete mientras HA esta instalando.

## 2026-07-09 - Fotos de observaciones como media persistente

Estado: VIGENTE

Decision:

- Guardar fotos reducidas de observaciones bajo
  `mushroom-data/media/observation-photos/<year>/<nombre-original>`.
- Conservar nombre original de la imagen dentro de una carpeta anual para evitar
  carpetas por observacion y mantener trazabilidad con `source.name`.
- Mantener las fotos y JSON operativo fuera de Git; en local viven bajo
  `docker-data/mushroom-data/` y en HA bajo `/share/rainmapper/mushroom-data/`.
- El preview EXIF de alta/edicion/duplicado es un modal separado: cancelar no
  modifica el formulario; aceptar aplica fecha, coordenadas, altitud y origenes
  al formulario, pero nada se escribe al JSON hasta `Guardar observacion`.
- Las miniaturas abren modal interno de imagen/EXIF; no se abre una pestana
  externa del navegador.

Motivo:

- El usuario quiere poder auditar posteriormente la foto usada para posicionar
  cada observacion sin guardar originales enormes.
- Una imagen alrededor de 1-2 MB por observacion es aceptable para el volumen
  previsto.
- La aplicacion debe evitar aplicar por error datos de una foto equivocada.

Consecuencias:

- Al mover datos locales a HA para validar fotos, copiar tanto
  `mushroom_observations.json` como `mushroom-data/media/`.
- Los campos de origen de ubicacion/altitud deben derivarse del flujo EXIF y
  ser visibles/editables con cuidado; si una observacion antigua tiene foto
  asociada cuyo EXIF coincide, puede reconstruirse como foto/EXIF.

## 2026-07-05 - `mushroom-data` como fuente operativa unica de setas

Estado: VIGENTE

Decision:

- Centralizar datos micologicos vivos, artefactos v0 reconstruibles y estado del modelo bajo `/share/rainmapper/mushroom-data/`; en desarrollo local esto es `docker-data/mushroom-data/`.
- Dejar `tmp/mushroom-lab/` solo para pruebas locales explicitas, QGIS o scripts exploratorios. No usar `mushroom-lab` para artefactos estables del modelo v0.
- No mantener fallbacks de lectura a rutas antiguas del modelo. Si falta `mushroom-data/mushroom_model_v0.json`, la UI debe tratar el modelo como pendiente y reconstruirlo desde las observaciones actuales.
- Persistir el estado de especies pendientes en `mushroom-data/mushroom_model_v0_state.json`.
- Al subir este trabajo a HA, reemplazar los datos de especies, observaciones, catalogos, mappings, labels y artefactos v0 por la copia validada local de `mushroom-data`; no mezclarla con datos micologicos antiguos de HA.

Motivo:

- El proyecto ya no esta en una fase de laboratorio separada para estas piezas. Mantener rutas paralelas (`mushroom-data`, `mushroom-lab/working`, defaults versionados) hizo que pantallas distintas leyeran estados distintos y genero confusion sobre si el modelo estaba actualizado.
- Home Assistant tendra menos CPU que el Mac local; por eso el estado pendiente permite reconstrucciones manuales y acotadas por especies, pero sin ocultar que el modelo esta desactualizado.

## 2026-07-04 - Modelo aprendido v0 como evidencia descriptiva

Estado: VIGENTE

Decision:

- Mantener `mushroom_model_v0.json` como salida descriptiva/auditable del laboratorio local.
- No tratarlo todavia como predictor operativo ni como modelo ML supervisado completo.
- Generarlo desde observaciones locales reconstruidas, separando positivos y negativos cuando existan.
- Mostrar soporte, ratios, gaps y rangos observados por especie.
- No escribir `mushroom_profiles.json` desde el modelo aprendido.
- No fijar pesos, umbrales ni ventanas meteorologicas por especie a partir de pocas observaciones.

Motivo:

- El usuario quiere empezar a aprender desde las observaciones ya disponibles sin esperar miles de datos.
- Con pocas observaciones, el valor real esta en ver relaciones, contradicciones y gaps, no en producir una puntuacion aparentemente definitiva.
- La v0 debe seguir siendo explicable y trazable.

Consecuencias:

- La pantalla `Evidencia > Modelo aprendido` es una auditoria tecnica.
- El valor principal debe aparecer junto al parametro revisado: `Parametros`, `Especies > General`, `Especies > Ecologia` y `Fenologia y Topografia`.
- Cualquier promocion de candidatos al perfil debe ser manual, visible y reversible.

## 2026-07-04 - Reconstruccion de modelo v0 desde observaciones, no solo GIS

Estado: VIGENTE

Decision:

- El laboratorio de observaciones deja de tratarse como una accion aislada de "reconstruir GIS".
- La accion visible debe reconstruir el modelo v0 local desde las observaciones seleccionadas o visibles:
  GIS/DEM por observacion, contexto meteorologico, features v0 unificadas y modelo aprendido v0.
- Las features v0 deben conservar la procedencia de los valores cuando sea posible:
  `field` para lo declarado por el observador y `gis` para lo inferido por capas GIS/DEM.
- La pantalla `Parametros` debe comparar perfil, evidencia v0 y valores emergentes mostrando la fuente dentro de cada chip.
- "Evidencia observacional" no debe usarse para una mezcla de observacion de campo y GIS si no se distingue la procedencia.

Motivo:

- El usuario necesita ver juntos los tres puntos de vista: parametros declarados de la especie, lo observado en campo y lo que dicen GIS/DEM.
- Una observacion puede no declarar todos los arboles o rasgos presentes, y GIS puede aportar contexto adicional; a la vez, GIS puede ser incompleto o depender de mappings.
- Llamar "GIS" al flujo completo confundia el objetivo real y ocultaba que el resultado alimenta el modelo v0 aprendido.

Consecuencias:

- El modelo aprendido v0 sigue sin escribir perfiles automaticamente.
- Cualquier promocion futura de valores debe ser manual y mostrar soporte por fuente.
- La pantalla `Evidencia` debe distinguir mejor en futuras iteraciones entre evidencia declarada por observador, evidencia GIS/DEM y coincidencias mixtas.
- La entrada de observaciones debe distinguir siempre campo (`field`) de GIS/DEM (`gis`) en features/modelo; el formulario ya captura hosts, bosque, suelo, habitat y orientacion observados como evidencia de campo opcional.

## 2026-07-04 - Evidencia local no modifica perfiles automaticamente

Estado: VIGENTE

Decision:

- Las decisiones de evidencia GIS (`promover`, `ignorar`, `mantener`, `dudoso`, `confirmar`, `reiniciar`) guardan estado de revision interno.
- Ese estado permite ordenar el trabajo humano y evitar repetir decisiones.
- No cambia automaticamente hosts, bosques, suelos, habitat, altitud, fenologia ni meteorologia en el perfil.

Motivo:

- Evita contaminar perfiles productivos con inferencias prematuras.
- Permite iterar con observaciones reales sin convertir cada gap o candidato en dato productivo.

Consecuencias:

- Hace falta una fase futura de "candidatos/diff/promocion" para aplicar cambios al perfil.
- Esa fase debe mostrar de donde sale cada propuesta y permitir revertir.

## 2026-07-04 - Directiva UI multiidioma y usable

Estado: VIGENTE

Decision:

- Toda pantalla nueva o modificada del dominio setas debe ser coherente con el look and feel existente, usable para una persona y multiidioma.
- No se aceptan paneles tecnicos crudos salvo acuerdo explicito con el usuario.
- Estados, decisiones, botones, cabeceras y ayudas visibles deben tener labels traducibles.

Motivo:

- El mantenimiento de especies/catalogos/evidencias va a crecer y debe seguir siendo operable.
- La UI de Rainmapper ya soporta `ui_language`; romper esa regla crea deuda inmediata.

Consecuencias:

- Antes de hardcodear texto visible en `mushroom_profiles_ui.py`, revisar si pertenece a `mushroom_labels.json`.
- Las futuras pantallas de evidencias/modelo deben priorizar comparacion visual y claridad, no dumps JSON.

## 2026-06-27 - Mantener JSON de setas como defaults versionados y copia editable en HA

Estado: VIGENTE

Decision:

- Tratar `mushroom-data/mushroom_profiles.json`, `mushroom-data/mushroom_reference_catalogs.json` y `mushroom-data/mushroom_gis_mappings.json` como defaults versionados empaquetados con la app.
- En Home Assistant, mantener la copia viva editable en `/share/rainmapper/mushroom-data/`.
- La UI de administracion de setas debe editar la copia persistente, no los defaults de la imagen.
- En primer arranque o primera activacion del modulo, si faltan ficheros persistentes, copiarlos desde los defaults; si existen, no sobrescribirlos al actualizar.
- El futuro motor de prediccion debe leer primero `/share/rainmapper/mushroom-data/` y usar los defaults versionados solo como fallback.
- Las pantallas de mantenimiento de perfiles y catalogos deben prever importacion/exportacion JSON y exportacion de una plantilla vacia del modelo.
- La primera fase de UI de mantenimiento cubre `mushroom_profiles.json` y `mushroom_reference_catalogs.json`; `mushroom_gis_mappings.json` queda como dato versionado, validable y consultable para impacto, pero sin editor completo hasta una fase posterior.
- Los valores controlados no ecologicos, como `review_status`, confidence y prioridades de calibracion, son contrato del modelo/validador/backend, no un campo `controlled_values` dentro de los JSON de perfiles.
- Estados validos de `metadata.review_status`: `draft`, `needs_review`, `reviewed`, `validated`, `deprecated`.

Motivo:

- Los perfiles y catalogos necesitan mantenimiento desde HA sin perder cambios en actualizaciones.
- Los defaults versionados siguen dando una base reproducible, testeable y recuperable.
- La importacion/exportacion permite mantenimiento externo, backup manual y migraciones controladas.

Consecuencias:

- Cualquier guardado desde UI debe validar antes de persistir, crear backup con timestamp y escribir de forma atomica.
- Importar un JSON debe mostrar resumen de cambios antes de confirmar y bloquear referencias rotas.
- Exportar plantilla vacia debe preservar `schema_version`, `model_purpose`, estructura raiz y grupos/campos principales, pero sin datos de especies o catalogos.
- No modificar automaticamente perfiles al importar catalogos, ni catalogos al importar perfiles, salvo flujo de migracion explicito y confirmado.
- En pruebas locales, la unica copia operativa es `docker-data/mushroom-data/`,
  porque representa `/share/rainmapper/mushroom-data/` y es lo que lee la UI.
  Los scripts de mantenimiento que afecten a datos visibles deben apuntar por
  defecto a esa copia viva mediante `rainmapper_core.mushroom_paths`; los
  defaults versionados se actualizan solo con una opcion explicita.
- Cuando se decida subir el modulo de setas a HA, los datos micologicos vivos
  de HA no son fuente de verdad para especies, observaciones, catalogos ni
  mappings. En esta fase la fuente de verdad funcional es la copia local
  `docker-data/mushroom-data/`; el despliegue debe reemplazar en HA:
  `mushroom_profiles.json`, `mushroom_observations.json`,
  `mushroom_reference_catalogs.json`, `mushroom_gis_mappings.json` y
  `mushroom_labels.json` por los equivalentes locales validados.
- Ese reemplazo no afecta a `users.json`, `devices.json`, historicos
  meteorologicos, ficheros de estaciones ni datos de lectura de fuentes
  meteorologicas bajo `/share/rainmapper/Data/`.

Estado de implementacion:

- Commit `54a86d0` introduce los defaults versionados, documentacion, validador y tests.
- La capa backend minima queda en `rainmapper_core/mushroom_store.py`.
- La imagen HA copia `mushroom-data/` y `scripts/validate-mushroom-data.py` a `/app/`.
- Endpoints admin disponibles en `rainmapper-app/app/web_server.py`: `GET/POST /api/mushrooms/validate`, `GET /api/mushrooms/export?file=profiles|catalogs|gis&source=current|persistent|default`, `GET /api/mushrooms/template?file=profiles|catalogs` y `POST /api/mushrooms/import` con `{file, data}`.
- `POST /api/mushrooms/import` solo permite `profiles` y `catalogs`; `gis` queda solo lectura en esta fase.
- Primera UI WebUI de catalogos disponible en `/mushrooms/catalogs`: hub de metricas, filtros por grupo, busqueda, tabla de IDs, creacion de entradas nuevas por grupo con plantilla minima validada, detalle con JSON editable por entrada, panel de validacion cruzada y bloque avanzado de import/export/plantilla JSON del catalogo completo.
- La UI de catalogos usa POST server-side por ingress HA, igual que `Users`; los endpoints JSON quedan como base para futuras pantallas cliente.
- Primera release HA que incluye backend/store y UI de catalogos: `0.2.150`, imagen `ghcr.io/cginebrosa/rainmapperha:0.2.150/latest`, digest multi-arch `sha256:35e42628eeb0937ec800608e9251fa0ef8148d4f6a626aea52a13a341ba71c0f`, commit `ecf2ed8`. Validacion local: `./scripts/smoke-test.sh` OK con 97 tests. Validacion HA: no cerrarla como buena por 404 en HA ingress al pulsar `Mushroom catalogs`; fix local aplicado con rutas relativas, seeding de defaults al arrancar y contador `Reference errors` derivado del validador para evitar falsos positivos GIS.
- La semantica exacta de `Reference errors` debe revisarse cuando esten completos el mantenimiento de perfiles, el mantenimiento GIS y el motor de prediccion; por ahora no debe contar cadenas tecnicas GIS que no sean IDs internos de catalogo.

## 2026-06-28 - Borrado defensivo de especies mediante archivado previo

Decision:

- No permitir borrado irreversible directo de una especie activa desde `mushroom_profiles.json`.
- El flujo soportado es activo -> archivado -> restaurado o borrado permanente desde archivo.
- Las especies archivadas se guardan fuera del JSON activo, en `/share/rainmapper/mushroom-data/archived/mushroom_profiles_archived.json`.
- `Restore species` solo puede restaurar si el `species_id` no existe ya en perfiles activos.
- `Delete permanently` solo aparece para especies archivadas y debe mostrar doble advertencia de navegador, incluyendo que no se puede deshacer.

Motivo:

- `species_id` es clave estable del modelo de prediccion; borrar un perfil activo por error podria romper mantenimiento, calibracion futura u observaciones asociadas.
- Archivado conserva recuperacion y auditoria practica sin contaminar el JSON activo que consume el motor.
- El borrado permanente queda disponible para limpiar pruebas, pero requiere una accion previa defensiva.

Consecuencias:

- La UI debe presentar `Archive species` para perfiles activos, no `Delete species` directo.
- El archivo de especies archivadas no forma parte del modelo predictor activo; se usa solo para mantenimiento.
- Si en el futuro hay observaciones/calibraciones vinculadas, el archivado/restauracion debera validar tambien esas referencias.

Actualizacion 2026-06-28: `0.2.169` no debe cerrarse como buena para este flujo porque en HA los modales de `New species`, `Duplicate species` y `Restore species` quedaban visibles pero no interactivos por una colision de `z-index` del backdrop heredada de los modales antiguos de Users. `0.2.170` corrige esa capa y queda como version a validar para el ciclo de vida defensivo.

Actualizacion 2026-06-28: desde `0.2.171`, `Archive species` no requiere reescribir manualmente el `species_id`. La UI muestra el ID seleccionado en solo lectura y el POST confia en el `species_id` oculto de la accion seleccionada. La confirmacion defensiva queda en el modal y el `confirm()` del navegador; el requisito de escribir el ID se retira porque era redundante y poco ergonomico para mantenimiento HA local.

## 2026-06-29 - Observaciones de setas como store propio y calibracion futura

Decision:

- Guardar observaciones de floradas en `mushroom-data/mushroom_observations.json`, separado de `mushroom_profiles.json` y `mushroom_reference_catalogs.json`.
- Mantener los valores tabulados de observaciones en `mushroom_reference_catalogs.json`, no hardcodeados en UI/backend.
- Usar `mushroom_labels.json` como diccionario general de labels de setas, sustituyendo el antiguo `mushroom_parameter_labels.json`.
- Tratar el alta/edicion de observaciones como mantenimiento HA server-side, con validacion global antes de persistir y backup atomico como perfiles/catalogos.
- Aplicar estrategia defensiva al borrado: una observacion activa solo puede archivarse; el borrado permanente solo existe desde observaciones archivadas y exige doble confirmacion de navegador mas confirmacion backend por `observation_id`.
- Mantener `calibration_use`, `validation_status` y `source_quality` como conceptos separados: uso en calibracion, aceptacion/validacion y fiabilidad del origen no significan lo mismo.

Motivo:

- Las observaciones seran la base para calibrar o confirmar si los parametros de especies son correctos frente a datos reales de campo.
- Separarlas de perfiles evita mezclar modelo teorico con evidencia observada.
- Los catalogos tabulados permiten cambiar opciones de abundancia, origen, validacion o uso sin tocar codigo.

Consecuencias:

- `rainmapper_core/mushroom_store.py` debe sembrar y validar tambien `observations`.
- `scripts/validate-mushroom-data.py` valida especies, coordenadas, fechas, catalogos de observacion y rangos de calidad.
- La UI inicial de `Observations` cubre alta, edicion, archivo, restauracion y borrado permanente; importacion CSV/JSON queda como tarea futura.
- `ui_language` queda disponible en `config.yaml`; desde `0.2.177` se aplica al dominio `mushrooms` via `RAINMAPPER_MUSHROOM_UI_LANGUAGE` tras reiniciar el add-on. Control Board y Users quedan fuera de esta primera fase.

Estado:

- Publicado en HA `0.2.175`, imagen/digest documentados en la nota de auditoria superior de su cierre; pendiente de validacion operativa en Home Assistant.
- Publicado en HA `0.2.176`: los grupos de reference catalogs se etiquetan desde `mushroom_labels.json` (`catalog_group.*`) para todos los catalogos actuales, sin fallback silencioso; si falta una clave, la UI muestra `missing label: catalog_group.<grupo>`. Imagen/digest/commit documentados en la nota de auditoria superior; pendiente de validacion visual en HA.
- Publicado en HA `0.2.177`: labels visibles de perfiles, parametros, calibracion, observaciones y reference catalogs se leen desde `mushroom_labels.json` segun `ui_language`; `/mushrooms/catalogs` cuenta referencias desde `mushroom_observations.json` para evitar falsos unused en catalogos de observaciones. Imagen/digest/commit documentados en la nota de auditoria superior; pendiente de validacion visual en HA.
- Publicado en HA `0.2.178`: la pantalla interna `Especies` traduce labels de meteorologia/scoring y valores controlados mediante `mushroom_labels.json` (`value.*`), y el resumen `General` traduce patrones de temporada desde catalogos. Imagen/digest/commit documentados en la nota de auditoria superior; pendiente de validacion visual en HA.
- Publicado en HA `0.2.179`: el tab interno de especies `Fenologia y Topografia` separa secciones, usa pastillas editables para meses, compacta retrasos/altitudes en grids 2x2 y anade label para `snowmelt_bonus`. Queda pendiente revisar el schema climatico cuando se defina el motor de prediccion: semantica de saturacion 30d, lluvia acumulada 30d y ubicacion conceptual de deshielo.
- Publicado y validado en HA `0.2.180`: el editor de especies conserva el tab interno tras guardar o tras errores de validacion; los filtros de observaciones son editables; los pesos de scoring se separan del modelo de habitat en Parametros; patrones de temporada y orientaciones pasan a pastillas catalogadas traducidas; la lista lateral de especies anade cabecera `Conf./Prio./Rev.`, tooltips y scroll interno.

## 2026-06-29 - Evidencia obligatoria para el motor predictivo de setas

Decision:

- No fijar parametros numericos del futuro motor predictivo de setas por intuicion de Codex.
- No convertir una deduccion general de literatura en umbral, peso o ventana especifica por especie sin fuente documental verificable o calibracion local.
- No asumir que una fuente contiene un dato si no se ha podido leer su contenido real.
- No presentar como decision tecnica un supuesto que no se pueda demostrar con documentacion, codigo fuente real o datos locales trazables.
- Mantener una biblioteca/manifiesto de fuentes en `docs/mushrooms/literature/README.md`, separando PDFs locales reales, fuentes open access bloqueadas para descarga automatica y referencias `DOI-only`.
- Si una fuente no esta disponible como texto completo local, la documentacion debe decirlo y limitar las conclusiones al nivel de evidencia realmente revisado.

Motivo:

- El motor de prediccion afectara decisiones operativas y no debe apoyarse en parametros inventados.
- Rainmapper ya tiene datos meteorologicos amplios; el reto es elegir features y calibrarlas con evidencia, no aumentar el schema por especulacion.
- Las observaciones reales deben convertirse en la fuente principal para ajustar el modelo local cuando la literatura no proporcione valores transferibles a Cataluna.

Consecuencias:

- `docs/mushrooms/mushroom-predictor-design-es.md` debe distinguir evidencia, hipotesis y decisiones pendientes.
- Cualquier implementacion futura del motor debe poder explicar de donde sale cada parametro: fuente documental, valor global conservador o calibracion local.
- Las fuentes bloqueadas por Cloudflare/Anubis/paywall no deben guardarse como falsos PDFs ni tratarse como leidas completas.
- Si no hay evidencia suficiente, la salida correcta del motor o de la documentacion es "datos insuficientes", no un parametro inventado.

## 2026-07-02 - Perfiles v0 promovidos dentro del schema rico

Decision:

- Promover la primera carga v0 a `mushroom-data/mushroom_profiles.json`.
- Mantener la estructura rica completa de `mushroom_profiles.json`, pero
  tratar como activos v0 solo ecologia amplia, temporada, altitud amplia y
  estado de revision/calibracion.
- Conservar la UI rica actual como vista avanzada/aparcada. La futura UI v0
  debe mostrar solo campos activos, no borrar ni reescribir el trabajo rico.
- Si el schema rico exige campos numericos para validar, permitir placeholders
  marcados explicitamente como `v0_placeholder`. La proyeccion v0 no debe
  usarlos como pesos ni parametros.
- Conservar afinidades enriquecidas antiguas que no proceden de la fuente v0
  dentro de los arrays ricos, pero marcarlas con `v0_active: false` para que la
  proyeccion v0 las ignore.
- Promover tambien los gaps de catalogo v0 a
  `mushroom-data/mushroom_reference_catalogs.json`, siempre referenciandolos en
  los perfiles productivos que los solicitaron para no introducir warnings de
  catalogo sin uso.

Motivo:

- El usuario quiere evitar tirar el trabajo ya hecho en perfiles, catalogos y
  UI, pero tambien necesita una v0 operativa y explicable.
- La fuente normalizada cubre 21 especies, incluyendo las 11 iniciales y 10
  especies incorporadas en esta promocion.
- Los catalogos iniciales cubrian la mayor parte de la v0. Los gaps detectados
  se promocionan de forma controlada junto con sus referencias de perfil.

Estado:

- Implementado `scripts/build-mushroom-profile-v0-candidate.py`.
- Documentado en `docs/mushrooms/mushroom-profiles-v0-candidate-build-es.md`.
- `mushroom-data/mushroom_profiles.json` contiene 21 perfiles productivos.
- `mushroom-data/mushroom_reference_catalogs.json` contiene los 12 IDs nuevos
  necesarios para cerrar los gaps v0 iniciales, con 32 referencias desde
  perfiles.
- El script sigue generando salidas revisables en
  `tmp/mushroom-lab/working/profiles/` y reporte en
  `tmp/mushroom-lab/output/reports/`.
- Cubierto por `tests.test_mushroom_profile_v0_candidate_builder`.
- No hay bump de version HA ni publicacion de imagen por esta decision.

## 2026-07-04 - Retirar `v0_catalog_gap_promoted` como origen visible

Decision:

- Eliminar `v0_catalog_gap_promoted` de los perfiles productivos y del builder
  candidato v0.
- Mantener los IDs de catalogo ya promovidos y las referencias desde perfiles,
  pero no tratarlos como un origen ecologico separado.
- No mostrar `Catalogo v0` como origen en la UI. Los origenes operativos deben
  quedar limitados a fuentes comprensibles para revision humana: perfil
  original, Marc Estevez, observacion de campo y GIS/DEM.

Motivo:

- `v0_catalog_gap_promoted` era metadato tecnico de una migracion: indicaba que
  un ID faltaba en catalogos y fue creado para poder representar una senal de la
  fuente v0.
- Ese flag no aporta fuerza ecologica ni evidencia adicional. Mantenerlo en la
  UI confundia el origen real de la afinidad con un detalle de construccion.
- El proyecto aun tiene pocas especies y pocas observaciones; es mejor retirar
  ahora el ruido tecnico que arrastrarlo hasta HA.

Consecuencias:

- El builder puede seguir usando `catalog_gap_candidates` como entrada historica
  para asegurar referencias validas, pero no escribira flags ni notas de
  promocion en cada afinidad.
- La auditoria historica queda en Git, en la fuente normalizada de Marc y en
  esta decision, no en campos visibles de mantenimiento.

## 2026-07-04 - Marc Estevez como fuente documental primaria reutilizable

Decision:

- Crear `scripts/apply-mushroom-literature-source.py` para aplicar fuentes
  literarias normalizadas a afinidades ecologicas de perfiles.
- Usar `source_ids` como metadato minimo de procedencia dentro de cada afinidad,
  sin crear una estructura grande de evidencias persistidas.
- Aplicar la fuente normalizada de Marc Estevez como `relationship: primary`
  para cada afinidad listada.
- Mantener `affinity: 0.0` + `v0_placeholder: true` solo cuando haya que crear
  una fila nueva para cumplir el schema rico, sin tratarlo como peso numerico.

Motivo:

- Marc Estevez es la fuente documental mas fiable disponible en esta fase. Si
  lista una afinidad, la ficha debe reflejarla como afinidad fuerte salvo que
  una fuente normalizada futura marque explicitamente lo contrario.
- La UI necesita mostrar de donde sale una relacion (`Marc`) sin mezclarlo con
  evidencia local viva (`Obs`, `GIS/DEM`) ni con detalles tecnicos de catalogo.
- El mismo flujo debe poder reutilizarse si se anade otra fuente literaria
  fiable o nuevas especies.

Consecuencias:

- `source_ids` es procedencia documental, no parametro del motor numerico.
- Observaciones y GIS/DEM seguiran entrando por el modelo v0 aprendido o por
  promocion manual revisable, no por este script.
- La operativa queda documentada en
  `docs/mushrooms/mushroom-literature-source-apply-es.md`.

## 2026-07-01 - GIS mappings como contrato revisable entre capas locales y catalogos internos

Decision:

- Mantener `mushroom-data/mushroom_gis_mappings.json` como contrato revisable entre valores crudos de capas GIS y IDs internos de `mushroom_reference_catalogs.json`.
- Preferir la seccion `exact_value_mappings` para capas locales activas como MVC50 y geologia 1:50.000.
- Identificar cada mapping por `source_id`, `field` y `raw_value`.
- No permitir IDs de destino como texto libre en UI: los destinos se eligen mediante opciones cerradas contra `host_taxa`, `forest_types`, `soil_types`, `lithology_types` y `habitat_features`.
- Mantener tres estados cerrados de revision:
  - `accepted`: revisado, usable y computable.
  - `pending_review`: persistido para no perderlo, pero pendiente de decision; puede tener IDs propuestos, pero no emite salida computable.
  - `ignored`: revisado y descartado; no emite IDs y evita que el valor vuelva a aparecer como candidato pendiente.
- El reconstructor GIS lee mappings, pero no debe escribirlos automaticamente. La escritura ocurre desde la pantalla `GIS mappings`.
- Para `geology_50000`, mapear por `Codi` y mostrar `Descripcio` como contexto humano; no crear mappings independientes para `Descripcio` si el codigo ya identifica la unidad.

Motivo:

- El futuro predictor debe comparar datos GIS contra catalogos internos estables, no contra textos crudos de proveedores externos.
- Los valores GIS observados en campo real necesitan revision humana, trazabilidad y posibilidad de descarte.
- Persistir `pending_review` e `ignored` evita perder trabajo entre reconstrucciones y evita que el mismo valor reaparezca continuamente como nuevo.

Consecuencias:

- `accepted` es el unico estado que alimenta features computables del laboratorio y futuro motor.
- `pending_review` e `ignored` deben conservarse como valores conocidos sin salida computable.
- La UI `/mushrooms/gis-mappings` debe mantener filtros por mapeado/pendiente, busqueda, ordenacion, fila seleccionada visible, detalle editable, modal visible de errores y selector de IDs restringido a grupos relevantes.
- Nota supersedida por la decision del 2026-07-05: el contrato persistente ya queda resuelto. Las salidas HA reutilizables de setas viven bajo `/share/rainmapper/mushroom-data/`; `tmp/mushroom-lab/` queda para pruebas locales/QGIS.

Estado:

- Implementado localmente en commit `ef9bbc6 Add GIS mappings lab UI`.
- Validado en esa implementacion con `py_compile`, `git diff --check`, `tests.test_mushroom_store`, `tests.test_mushroom_data_validator` y `scripts/validate-mushroom-data.py` con 0 errores y 7 warnings conocidos.
- No hay bump de version HA ni publicacion de imagen por esta decision.

## 2026-07-04 - Rutas micologicas centralizadas para HA y laboratorio local

Decision historica, supersedida en parte por la decision del 2026-07-05 `mushroom-data` como fuente operativa unica:

- Centralizar la resolucion de rutas de setas en `rainmapper_core/mushroom_paths.py`.
- Mantener un unico contrato conceptual:
  - defaults versionados: `mushroom-data/` en repo o `/app/mushroom-data/` en imagen HA;
  - datos vivos editables: `/share/rainmapper/mushroom-data/`;
  - artefactos derivados del modelo v0: desde 2026-07-05 tambien `/share/rainmapper/mushroom-data/`;
  - desarrollo local: `docker-data/` representa `/share/rainmapper`;
  - `tmp/` queda para artefactos temporales/locales no persistentes, como QGIS o pruebas aisladas.
- Los modulos `mushroom_store`, `mushroom_gis_lab`, `mushroom_observation_context`, `mushroom_observation_features` y `mushroom_learned_model` deben usar este helper en vez de repetir heuristicas propias.
- Se conserva compatibilidad con overrides por entorno (`RAINMAPPER_SHARE_ROOT`, `RAINMAPPER_MUSHROOM_DATA_DIR`, rutas concretas de artefactos y `RAINMAPPER_WEATHER_DATA_DIR`). No reintroducir `RAINMAPPER_MUSHROOM_LAB_DIR` para artefactos operativos estables.

Motivo:

- El rebuild completo del modelo v0 podia vaciar el modelo aprendido si un modulo leia defaults vacios en vez de la copia persistente con observaciones.
- Tener la logica de rutas repetida en cada builder aumenta el riesgo de que HA, Docker local y scripts lean/escriban sitios distintos.

Consecuencias:

- Antes de subir este flujo a HA, la ruta contractual para datos maestros, features, modelos reconstruibles y estado es `/share/rainmapper/mushroom-data/`.
- `docker-data/mushroom-data/` es la representacion local de ese contrato.
- Los defaults versionados solo sirven para seed/fallback, tests y recuperacion; no deben ganar prioridad sobre datos persistentes existentes.

## 2026-07-04 - Rebuild v0 con progreso visible y tiempos

Decision:

- La accion de reconstruir modelo v0 desde Observaciones no debe bloquear la pagina hasta terminar.
- El POST arranca un job en segundo plano y vuelve inmediatamente a la pantalla con una ventana modal de progreso.
- La ventana consulta `/api/mushrooms/rebuild-status` y muestra:
  - fase actual y numero de fase;
  - porcentaje total;
  - porcentaje de fase;
  - tiempo total transcurrido;
  - tiempo de la fase actual;
  - ETA total y ETA de fase cuando hay progreso medible;
  - mensaje final o error.
- La ventana no se cierra automaticamente. El boton `Close` solo aparece cuando el job termina o falla, para poder leer el tiempo final real.
- El paso GIS/DEM reporta progreso por observacion mediante callback. Las fases meteorologia, features y modelo aprendido reportan inicio/fin de fase y tiempos, sin inventar progreso interno.

Motivo:

- En Mac el rebuild puede parecer rapido, pero en Home Assistant puede tardar bastante mas.
- El usuario necesita saber si la reconstruccion sigue viva, que paso esta ejecutando y cuanto tarda cada fase antes de promover el flujo a HA.

Consecuencias:

- El estado del job es en memoria y sirve para feedback operativo de la WebUI; los artefactos persistentes operativos son JSON/CSV bajo `mushroom-data/`.
- Si se reinicia el servidor durante un job, se pierde la ventana de estado pero no cambia el contrato de datos.
- Si una fase futura necesita progreso interno fiable, debe exponer callback o contadores; no simular porcentajes tecnicos sin soporte.

## 2026-07-04 - Vista V0 como default operativo de setas

Decision:

- La WebUI de mantenimiento de setas entra por defecto en vista `V0` cuando la
  URL no trae `view`.
- La vista `Enriched` sigue existiendo, pero debe pedirse explicitamente con
  `view=enriched` desde el conmutador.
- Los enlaces y selectores de especie deben preservar `view=v0` para no saltar
  accidentalmente a `Enriched` al navegar entre especies o secciones.

Motivo:

- La revision diaria de observaciones, evidencia, parametros y modelo v0 se
  esta haciendo sobre el contrato operacional v0. Que `Enriched` sea el default
  confundia el estado visual y ocultaba si se estaba trabajando en el contrato
  productivo o en el perfil rico completo.

## 2026-06-29 - Laboratorio local como base del predictor de floradas

Decision:

- Cambiar el enfoque del motor de setas desde literatura incompleta hacia evidencia local reproducible.
- Crear un laboratorio local bajo `tmp/mushroom-lab/`, ignorado por Git, para procesar fotos geolocalizadas, observaciones positivas/negativas, historicos meteorologicos copiados de HA y capas DEM/GIS.
- Usar `docker-data/` como copia mutable local de `/share/rainmapper` cuando se quiera capturar observaciones con la WebUI real sin tocar Home Assistant.
- Mantener los datos reales del laboratorio fuera del repo: fotos, coordenadas, historicos HA y capas GIS no se versionan.
- Generar primero condiciones observadas y parametros candidatos experimentales, no cambios automaticos sobre `mushroom_profiles.json`.
- Posponer cualquier boton productivo de UI para recalcular parametros hasta validar el pipeline local.
- Usar la UI local de observaciones como herramienta de captura rapida, no como fuente productiva hasta que el usuario decida subir version HA.

Motivo:

- Las fuentes bibliograficas localizadas no bastan para fijar umbrales por especie transferibles a Catalunya.
- El usuario dispone de fotos geolocalizadas y observaciones reales de los ultimos anos, incluidas posibles salidas negativas.
- Rainmapper ya tiene los historicos meteorologicos necesarios para reconstruir lluvia, temperatura, humedad y viento previo a cada observacion.
- Las capas oficiales de ICGC/ICC e IGN/CNIG pueden aportar DEM, topografia, cubiertas, vegetacion, litologia y suelos.

Consecuencias:

- El siguiente trabajo debe empezar por copiar historicos HA a `tmp/mushroom-lab/input/ha-data/` y construir un extractor local.
- Para acelerar la captura manual, la UI de observaciones puede importar fotos EXIF, duplicar observaciones como plantilla sin guardar, recuperar EXIF desde duplicados, importar varias fotos/carpeta, ordenar la tabla por cabeceras, seleccionar filas completas y preservar filtros/archivadas despues de acciones; esos guardados siguen siendo datos locales cuando se usa `rainmapper-ha-ui` montando `docker-data/`.
- El primer POC debe resolver observaciones + meteorologia antes de anadir DEM/GIS.
- DEM/GIS se incorporan despues como enriquecimiento local, preferentemente con raster/vector descargados o WCS/WFS; WMS sirve para visualizar, no como fuente primaria de atributos.
- Un futuro boton de UI deberia llamarse conceptualmente `Recalcular candidatos desde observaciones`, mostrar diferencias y requerir aplicacion manual campo a campo. No debe sobrescribir parametros de especie automaticamente.
- La documentacion canonica de este flujo es `docs/mushrooms/mushroom-local-observation-lab-es.md`.

## 2026-06-30 - `mushroom_gis_mappings.json` como contrato de traduccion GIS

Decision:

- Mantener `mushroom_gis_mappings.json` como pieza necesaria para el predictor espacial.
- Usarlo para traducir codigos externos de capas GIS oficiales a IDs internos de `mushroom_reference_catalogs.json`.
- No depender en el motor de nombres crudos de capas externas ni de textos libres.
- No completar mappings por intuicion: cada mapping debe provenir de una capa concreta, campo concreto y valor externo comprobado.
- Si una coordenada cae en una clase externa sin mapping, el motor debe reportar un gap de GIS y reducir confianza si procede, no inventar una equivalencia.

Motivo:

- Los perfiles de especie expresan ecologia en vocabulario interno estable.
- Las capas oficiales describen territorio con codigos y nomenclaturas propias.
- Sin una capa de traduccion, cualquier cambio de fuente GIS obligaria a tocar perfiles o codigo del predictor.

Consecuencias:

- El laboratorio GIS debe documentar fuente, licencia, cobertura, resolucion, CRS, capa, campo y valores usados.
- ICGC/ICC queda como primera fuente candidata para Catalunya: DEM, cubiertas, vegetacion/habitats, geologia/litologia y suelos si existe capa util.
- IGN/CNIG queda como fuente candidata estatal: MDT/DEM, SIOSE/coberturas y otras capas descargables o consultables por WFS/WCS.
- WMS puede usarse para inspeccion visual, pero no debe ser fuente primaria del calculo porque devuelve imagen y no atributos estructurados.
- La UI de catalogos debe seguir mostrando impacto de dominio y referencias GIS, pero una UI completa para mappings puede esperar hasta elegir fuentes GIS definitivas.

## 2026-06-30 - Duplicado de observaciones como plantilla no persistida

Decision:

- `Duplicar` una observacion no debe crear un registro nuevo inmediatamente.
- Debe abrir una plantilla prellenada sin `observation_id`.
- El `observation_id` se genera solo al guardar, usando la fecha final de la observacion.
- Si desde la plantilla duplicada se sube una o varias fotos EXIF, las observaciones creadas usan fecha, coordenadas, altitud y origen de cada foto.

Motivo:

- El formato operativo `obs_YYYYMMDD_NNNN` solo tiene sentido si la fecha del ID coincide con la fecha real guardada.
- Duplicar es una herramienta de velocidad para registrar varias especies de una misma salida o reutilizar una observacion como plantilla de importacion EXIF.
- Crear primero y editar despues genera IDs incoherentes cuando se cambia fecha o se recupera EXIF de otra foto.

Consecuencias:

- El backend conserva un handler defensivo para `duplicate_observation`, pero el flujo normal de UI usa query `duplicate_from` y formulario `create_observation`.
- Guardar desde duplicado puede crear una o varias observaciones.
- Las acciones de observaciones deben preservar filtros, ordenacion, especie seleccionada, observacion seleccionada y estado del panel de archivadas.

## 2026-06-30 - Importacion EXIF de observaciones y subida colaborativa futura

Decision:

- Mantener `Pillow==12.2.0` en `requirements.txt` mientras exista importacion o recuperacion EXIF desde observaciones.
- La UI de observaciones puede importar una o varias fotos JPEG con EXIF, usando una plantilla comun para observador, experiencia, calidad, abundancia, validacion, especie y uso en calibracion.
- Los campos extraidos automaticamente desde EXIF son fecha de observacion, latitud, longitud, altitud si existe, `source.type = photo_exif`, `location.source = photo_exif` y `source.label` basado en el nombre del archivo.
- Si una foto no tiene EXIF util de fecha/GPS, no se deben inventar coordenadas ni fecha.
- HEIC/HEIF no queda garantizado por esta decision. Si se necesita soportarlo, evaluar conversion server-side a JPEG preservando EXIF util y documentar dependencias extra en HA.
- La subida futura desde MapLibre para colaboradores debe quedar detras de un permiso/toggle de usuario, por ejemplo `can_upload_mushroom_observations`, similar a metricas, IDW y Heatmap.
- Las observaciones subidas por colaboradores deben quedar pendientes de revision y fuera de calibracion automatica hasta validacion manual del propietario.

Motivo:

- Las fotos geolocalizadas del usuario son la via mas rapida para construir una base local de observaciones historicas.
- Duplicar observaciones y recuperar EXIF reduce mucho el tiempo de carga cuando una salida contiene varias especies.
- La subida colaborativa puede acelerar la recopilacion, pero introduce riesgos de privacidad, calidad de datos y validacion.

Consecuencias:

- El laboratorio local puede crecer con datos reales sin tocar HA productivo si se usa `rainmapper-ha-ui` contra `docker-data/`.
- No persistir imagenes completas salvo decision explicita posterior; la preferencia inicial es guardar metadata/observacion.
- Validar tamano, cantidad, EXIF ausente y permisos antes de exponer esta funcionalidad en MapLibre.
- Documentacion relacionada: `docs/mushrooms/mushroom-local-observation-lab-es.md`, `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`, `docs/mushrooms/mushroom-predictor-design-es.md` y `docs/todo.md`.

## 2026-06-27 - Compactar panel expandido de usuarios sin cambiar contratos backend

Decision:

- Ajustar solo el contenido del usuario expandido en Home Assistant `Users`, sin redisenar toda la pantalla.
- Mantener `User details`, `Permissions` y `Audit` dentro del formulario `update_user` para no romper el guardado actual.
- Convertir `Permissions` en un grid de tarjetas con metadata centralizada para que nuevos permisos puedan anadirse sin duplicar markup.
- Mover `Security` a un bloque separado y compacto, preservando los forms/handlers actuales de `Set password`, `Reset password` y `Delete user`.
- Trackear la especificacion y referencia visual en `docs/ui/rainmapper-user_panel_redesign.md` y `docs/ui/rainmapper-user_panel_redesign.png`.

Motivo:

- La version accordion de `Users` funciona, pero el panel expandido seguia ocupando demasiado espacio y dejaba mucho desbalance visual entre detalles, permisos, seguridad, dispositivos y auditoria.
- Los permisos van a crecer si la app evoluciona, por lo que conviene preparar una UI en tarjetas sin cambiar todavia el modelo backend.
- Evitar cambios de endpoints o backend reduce el riesgo en una pantalla sensible de administracion.

Consecuencias:

- Los nombres de campos POST y `admin_action` existentes se conservan: `update_user`, `set_password`, `reset_password`, `delete_user`, `delete_device` y `delete_all_devices`.
- La auditoria sigue siendo informativa y compacta dentro del formulario de guardado.
- La seguridad queda visualmente separada para evitar forms anidados, manteniendo confirmaciones existentes.
- La validacion relevante debe hacerse dentro de HA/ingress por anchura real de pantalla y estilos de Home Assistant.

Estado:

Publicado inicialmente en imagen HA `0.2.148` con digest multi-arch `sha256:a2fcab2222519150bd20a3f9cbb1949736b03384e1c6b79f36ef50d79d28c821` y commit `48629ff`. En HA se detecto que el acordeon aparecia totalmente desplegado porque `.user-panel { display: grid; }` pisaba el atributo `hidden`, y ademas el JS podia abrir/restaurar automaticamente un usuario al cargar. `0.2.149` corrige el comportamiento: todos los usuarios nacen cerrados, pulsar un usuario abierto lo cierra, abrir un usuario cierra todos los demas y el refresh manual deja el listado cerrado. Imagen HA `0.2.149` publicada con digest multi-arch `sha256:3a488f597e34d2caba2c30edc90f5426813eb0c19858e2dcd679b197abda474b` y commit `039e615`. Validacion local: `python3 -m unittest tests.test_web_server_auth` OK y `./scripts/smoke-test.sh` OK. Instalada y validada/dada por buena en HA por el usuario el 2026-06-27.

## 2026-06-27 - Redisenar Control Panel HA como dashboard con tabs internos

Decision:

- Redisenar el Control Panel principal de Rainmapper dentro de Home Assistant como un dashboard compacto con tabs internos: `Summary`, `Data sources`, `Viewers`, `Maps`, `Logs` y `Errors`.
- Mantener la WebUI del Control Panel en ingles, aunque los documentos/mockups de trabajo puedan estar en castellano.
- Usar HTML/CSS/JS server-side generado desde `rainmapper-app/app/web_server.py`, sin dependencias frontend nuevas, para mantener compatibilidad con HA ingress.
- Preservar todos los handlers y acciones existentes: `Run update`, `Generate maps`, `Run all`, `App settings`, `Users`, `Update only` por fuente, abrir visores, abrir mapas, abrir log, `Disable all` y `Enable all`.
- No anadir confirmacion a `Disable all` / `Enable all`, porque son acciones reversibles y el usuario rechazo introducir friccion de seguridad ahi.

Motivo:

- El panel anterior era funcional pero demasiado alto y dificil de escanear conforme crecen fuentes, mapas, logs y errores.
- Home Assistant ya proporciona navegacion lateral; anadir una segunda sidebar dentro de Rainmapper seria mas pesado y menos coherente dentro de ingress.
- Los tabs internos permiten separar resumen, fuentes, visores, mapas, logs y errores sin perder acceso rapido a las acciones operativas principales.
- Mantener contratos POST y endpoints evita riesgo innecesario en una pantalla de control ya usada en produccion.

Consecuencias:

- El codigo de `web_server.py` crece con helpers server-side pequenos para renderizar fragments del dashboard, tablas, tarjetas, listas de mapas y preview de logs.
- La UX se valida en HA/ingress, no solo en HTML local, porque los estilos y anchuras reales dependen del contenedor de Home Assistant.
- Futuras mejoras del panel deben preservar primero los handlers existentes y anadir tests que comprueben enlaces/acciones criticas.

Estado:

Publicado en imagen HA `0.2.147` con digest multi-arch `sha256:368c910b9a31fba587c1e1cbca0201395feeecca3bf9e8884f62ccc08a76feef` y commit `9ffecab`. Validacion local: `./scripts/smoke-test.sh` OK. El usuario reporto el 2026-06-27 que la `0.2.147` parece funcionar bien en HA.

## 2026-06-25 - Mantener permisos funcionales simples por usuario solo como fase actual

Decision:

- Aceptar temporalmente `can_use_heatmap`, `can_use_layer_metrics` y `can_use_estimated_field` como flags directos por usuario en `users.json`.
- No seguir acumulando muchos flags independientes en cada usuario sin revisar antes el modelo de permisos.
- Si crece el numero de funcionalidades protegidas, definir una arquitectura de permisos por perfil/tipo de usuario en un JSON separado, con overrides opcionales por usuario.

Motivo:

- Ahora solo hay pocas funciones con permisos y el cambio por usuario es simple, compatible y facil de operar desde la WebUI.
- Si la app evoluciona hacia mas funcionalidades, mapas, zonas o perfiles comerciales, duplicar permisos en cada usuario seria fragil y dificil de mantener.
- Separar identidad de usuario, perfil base y overrides deja una ruta mas limpia hacia perfiles `free/basic/pro/admin` u otros modelos futuros.

Consecuencias:

- El modelo actual es suficiente para la fase inmediata de heatmap/metrica, pero queda marcado como deuda arquitectonica.
- Antes de anadir mas permisos funcionales, revisar un posible `permission_profiles.json` o equivalente persistido en `/share/rainmapper`.
- Cualquier migracion futura debe mantener compatibilidad con los flags existentes y defaults actuales: admins con permisos activos por defecto y resto de roles sin permisos experimentales salvo override.

## 2026-06-24 - Backfill manual AEMET con climatologia diaria

Decision:

- Se anade `scripts/aemet-backfill-30-days.py` como helper local para generar `Aemet_incremental.csv` de dias cerrados desde el endpoint diario de climatologia AEMET.
- El helper queda fuera del pipeline HA normal: por defecto escribe en `tmp/aemet-backfill-<timestamp>/`, no toca `Data/` y no modifica el historico horario AEMET.
- Para conservar metadatos enriquecidos se debe pasar `--station-catalog` apuntando al `estacions_aemet.csv` actual; para fusionar con un historico ya descargado de HA se puede pasar `--existing-incremental`.
- La subida a HA sigue siendo manual y debe tratarse como operacion sobre historicos: revisar salida y aplicar `docs/history-safety.md` antes de reemplazar CSV reales.

## 2026-06-23 - Promover AEMET al visor estandar protegido

Decision:

- Tras validar/dar por buena `0.2.108` en HA, AEMET pasa a formar parte del Tomap/GeoJSON estandar generado por la app HA.
- Los comandos de mapas de HA ejecutan `rainmapper_core.tomap` con `--include-aemet true`, de modo que `/protected/maplibre/index.html`, Leaflet y Bokeh consumen el mismo dataset de produccion con AEMET cuando exista `Aemet_incremental.csv`.
- Mantener `rainmapper_core.tomap` con AEMET excluido por defecto para pruebas locales/controladas; la promocion a produccion se decide en los comandos HA, no cambiando el default global del modulo.
- Desactivar la ruta experimental publica `/local/rainmapper-maplibre-aemet/index.html` mediante `PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE = False`, sin borrar todavia el codigo del publicador.
- Dejar documentada como tarea pendiente la retirada definitiva del publicador experimental AEMET cuando la ruta estandar quede validada durante uso real.

Motivo:

- La ruta experimental ya permitio validar integracion AEMET, bounds dinamicos, contador de coordenadas invalidas, atribuciones y duplicados diarios.
- Mantener dos visores con datasets distintos deja de aportar valor operativo y puede confundir las pruebas con usuarios reales.
- Conservar temporalmente el codigo experimental desactivado permite volver rapido al modo test si la promocion a produccion descubre un problema inesperado.

Consecuencias:

- El numero de estaciones del visor protegido aumentara cuando AEMET este habilitado y haya `Aemet_incremental.csv`.
- `Generate maps` y `Run all` en HA regeneran el dataset estandar incluyendo AEMET; si `create_aemet=false` o falta historico AEMET, el resultado sigue funcionando con el resto de fuentes.
- En la siguiente publicacion, la WebUI deberia dejar de mostrar el enlace `AEMET test viewer` porque la carpeta experimental se limpia al publicar.
- Hay que eliminar mas adelante el flag y `publish_aemet_experimental_maplibre()` para no dejar codigo de rollback indefinidamente.

## 2026-06-23 - Guardar la vista inicial MapLibre solo por accion explicita

Decision:

- Anadir en Settings de MapLibre protegido una accion explicita `Set current view as default` / `Usar vista actual por defecto`.
- Guardar en `devices.json` la vista elegida (`lng`, `lat`, `zoom`, `bearing`, `pitch`) como `map_view`, saneada por el backend.
- Al abrir o refrescar el visor protegido, si el dispositivo tiene `map_view`, restaurar esa vista en lugar de hacer `fitBounds()` a todos los datos.
- No guardar automaticamente cada movimiento, zoom o pan del mapa.

Motivo:

- Con AEMET, el dataset cubre mucho mas territorio y el encuadre automatico inicial muestra "demasiado mapa".
- Guardar cada movimiento escribiria con frecuencia en `/share/rainmapper/devices.json` en la Raspberry Pi 4. La preferencia debe ser deliberada y de baja frecuencia, igual que los ajustes persistidos al cerrar Settings.

Consecuencias:

- La vista por defecto se actualiza solo cuando el usuario pulsa el boton en Settings y cierra el panel, no al navegar normalmente por el mapa.
- Si no hay vista guardada, se mantiene el comportamiento anterior de encuadrar los datos cargados.
- La ruta experimental/fallback sin autenticacion no usa settings de dispositivo y por tanto conserva el encuadre automatico.

## 2026-06-23 - Atribuciones visibles por fuente en MapLibre

Decision:

- Mostrar atribucion especifica por fuente en la ficha de cada estacion MapLibre y retirar la fila generica `Source:` del popup.
- Mantener AEMET en castellano: `Fuente: AEMET - Informacion elaborada por Rainmapper a partir de datos de la Agencia Estatal de Meteorologia`.
- Mostrar Meteocat siempre en catalan, con el formato de fuente indicado por la Generalitat y el organismo/dataset XEMA: `Font: Generalitat de Catalunya. Departament de Territori, Habitatge i Transicio Ecologica. METEOCAT. Dades meteorologiques de la XEMA. Dades elaborades per Rainmapper.`
- Mostrar Meteoclimatic de forma conservadora y en castellano como `Fuente: Informacion elaborada por Rainmapper a partir de datos de Meteoclimatic (www.meteoclimatic.net)` hasta localizar un texto legal mas especifico para el RSS usado por Rainmapper.
- Mostrar Wunderground de forma conservadora y en ingles como `Source: Information elaborated by Rainmapper from Weather Underground data` hasta definir un texto contractual/legal concreto; esta atribucion no cambia la decision previa de no basar una app comercial en Wunderground sin acuerdo escrito.
- Incluir las mismas fuentes en el panel de creditos/informacion del visor.

Motivo:

- La Generalitat exige atribuir la reutilizacion de datos abiertos indicando `Generalitat de Catalunya`, el departamento y, si aplica, el organismo o entidad autonoma. Para XEMA, el dataset publico identifica el departamento `Territori, Habitatge i Transicio Ecologica` y `METEOCAT` como organismo/fuente.
- AEMET ya estaba atribuido; al anadir mas fuentes, la fila `Source:` duplicaba informacion y era menos clara que una atribucion visible.
- Meteoclimatic y Wunderground requieren revision adicional de terminos/formato exacto, pero en la fase privada actual es preferible mostrar al menos una fuente visible antes que ocultarla.

Consecuencias:

- Los creditos de MapLibre mezclan textos en distintos idiomas deliberadamente: AEMET y Meteoclimatic en castellano, Meteocat en catalan y Wunderground en ingles.
- Antes de publicar Rainmapper fuera del uso privado actual, revisar de nuevo Meteoclimatic y Wunderground y sustituir las atribuciones conservadoras por el texto legal/acuerdo aplicable.
- El codigo del visor MapLibre es compartido; desde la promocion de AEMET, el protected estandar usa el dataset con AEMET. La ruta experimental queda apagada y solo deberia reactivarse como rollback temporal.

## 2026-06-23 - Usar AEMET OpenData horario como nueva fuente candidata

Decision:

- Usar como candidato principal de AEMET el endpoint global `/opendata/api/observacion/convencional/todas`.
- Llamarlo como maximo una vez por ejecucion de `Run all`/schedule, nunca por estacion.
- Tratar `fint` como timestamp UTC de fin de la hora observada.
- Tratar `prec` como lluvia horaria acumulada durante los 60 minutos anteriores a `fint`.
- Deduplicar por `AEMET + idema + fint`.
- Guardar primero observaciones horarias y construir acumulados de periodo desde nuestro historico, no asumir que la respuesta es un dia completo.
- Si AEMET devuelve `429 Too Many Requests` u otro fallo temporal, la fuente debe degradar sin romper el pipeline completo.
- Dejar el endpoint diario de climatologia como posible backfill futuro de dias cerrados, no como fuente operativa inmediata.
- Si se muestran datos AEMET en visores o exports para terceros, mostrar atribucion visible a AEMET. Para estaciones AEMET en MapLibre, la ficha de estacion debe incluir al menos `Fuente: AEMET`; si el dato se mezcla o transforma dentro de Rainmapper, usar el texto ampliado `Informacion elaborada utilizando, entre otras, la obtenida de la Agencia Estatal de Meteorologia`. El panel de creditos/informacion del visor debe incluir una referencia agregada a AEMET cuando el dataset cargado contenga alguna estacion AEMET.

Motivo:

- El schedule real de HA ejecuta `Run all` unas 8 veces al dia, por lo que una llamada global cada 3 horas encaja con el endpoint horario sin hacer scraping agresivo.
- La respuesta trae en el mismo registro `idema`, coordenadas, nombre de estacion y lluvia horaria, suficiente para integrarla sin llamadas por estacion.
- El endpoint diario puede ser util para completar historicos, pero se publica con retraso, no trae coordenadas en el registro de datos y requiere unir con el inventario de estaciones.
- AEMET aplica limites de uso: durante pruebas manuales varias llamadas seguidas llegaron a `429`.
- La nota legal oficial de AEMET permite reutilizacion comercial y no comercial, pero exige no desnaturalizar la informacion, citar a AEMET como fuente, mencionar fecha de actualizacion cuando conste, conservar metadatos aplicables y no sugerir patrocinio, participacion o apoyo de AEMET.

Consecuencias:

- La implementacion debe ser muy conservadora con llamadas externas: una llamada de indice, una descarga de la URL temporal `datos`, sin bucles por estacion.
- El historico AEMET no debe mezclarse ingenuamente con historicos diarios existentes hasta definir el corte UTC/local. El plan inicial es almacenar UTC y hacer la conversion/control de periodos en el agregador.
- Cualquier escritura de historicos CSV para AEMET debe seguir `docs/history-safety.md`: backup o copia temporal, fixtures, validacion de estructura y deduplicado antes de tocar datos reales.
- Los CSV exploratorios en `tmp/aemet-test/` son solo material temporal de analisis y no forman parte del pipeline.
- La integracion debe preservar en los datos publicados metadatos suficientes para atribucion: `Source=AEMET`, timestamp de observacion `fint` en UTC y, si esta disponible, timestamp de generacion/actualizacion del dataset. `estacions_aemet.csv` actua como catalogo persistente de estaciones y debe preservar campos enriquecidos manualmente, como `Comarca`, `Municipi` y `Provincia`, aunque AEMET no los entregue en el endpoint horario. No usar logo AEMET salvo que venga integrado o se revise expresamente su uso; texto es suficiente para la primera version.
- Durante la validacion inicial, `tomap.py` excluia AEMET por defecto y solo lo incluia con `--include-aemet true`; la WebUI HA publicaba una variante experimental `/local/rainmapper-maplibre-aemet/index.html`. Tras validar `0.2.108`, HA pasa a generar el Tomap estandar con `--include-aemet true` y la ruta experimental queda desactivada por flag como rollback temporal.
- El reverse geocoding vive en `rainmapper_core/geocoding.py` y lo comparten las fuentes existentes y AEMET. AEMET debe seguir el mismo criterio operativo que Meteoclimatic/Wunderground: consultar Google Maps cuando la estacion sea nueva, falten `Municipi`/`Provincia` o cambien sus coordenadas. El enriquecimiento usa `GMAP_API_KEY`/`RAINMAPPER_GMAP_API_KEY`, preserva campos ya rellenados si las coordenadas no cambian y evita resultados tecnicos tipo `plus_code` cuando hay alternativas. `Comarca` no queda disponible de forma fiable desde Google y no se usa como condicion para repetir llamadas; si llega, se conserva. El CLI de AEMET permite `--skip-station-enrichment` solo para pruebas temporales.

Estado:

Diseno aceptado por el usuario como direccion para continuar. Primera implementacion completada de forma opcional y desactivada por defecto: `rainmapper_core/create_aemet.py`, opciones `create_aemet`/`aemet_api_key`, integracion opcional en `rainmapper_core.rainmapper`, consumo bajo flag en `tomap.py`, inferencia `Source=AEMET` en GeoJSON, atribucion AEMET en MapLibre y ruta experimental `/local/rainmapper-maplibre-aemet/index.html`. El 2026-06-23 se ejecuto una prueba real temporal con reverse geocoding en `tmp/aemet-geocode-test-v2/`: 802 estaciones, 802 con `Municipi`, 800 con `Provincia` y 7 con `Comarca`; `REUS AEROPUERTO` quedo como `Reus`, coherente con la localidad esperada. Durante la primera prueba HA, `0.2.103` ejecuto AEMET pero fallo la publicacion experimental al reconstruir Tomap por un `pd.merge` sobre columnas opcionales con tipos distintos (`object`/`float64`). La union de fuentes en Tomap debe tratarse como union de filas, no como join relacional por todas las columnas; desde `0.2.104`, `merge_dataframes()` usa `pd.concat(...).drop_duplicates()` para aceptar fuentes con columnas opcionales heterogeneas. Desde `0.2.105`, AEMET persiste tambien temperatura `ta` y humedad `hr` horarias cuando existen, agregandolas como max/min diarios, y MapLibre deja de recortar estaciones por bounds regionales: solo descarta coordenadas geograficamente invalidas y muestra `Invalid: N`. `0.2.108` queda validada/dada por buena en HA y se decide integrar AEMET en el visor protegido estandar, manteniendo el publicador experimental desactivado solo como rollback temporal.

## 2026-06-22 - La ruta activa del repo es `/Users/carlosginebrosa/Developer/RainmapperHA`

Decision:

- Usar `/Users/carlosginebrosa/Developer/RainmapperHA` como unica copia activa para desarrollo, tests, builds, documentacion y commits.
- No usar la copia antigua situada bajo iCloud/Mobile Documents porque quedo desfasada y puede provocar ediciones sobre un arbol incorrecto.

Motivo:

- Durante la sesion se detecto que el entorno podia arrancar en la ruta antigua de iCloud mientras el repositorio actualizado vivia en `~/Developer/RainmapperHA`.
- Documentar la ruta evita repetir el problema en futuras sesiones de Codex.

Consecuencias:

- Antes de cualquier cambio relevante, comprobar `pwd` y `git status` en la ruta real.
- Si una herramienta apunta a la ruta iCloud, corregir el `workdir` antes de leer o escribir ficheros.

## 2026-06-21 - Proteger MapLibre y GeoJSON con autenticacion ligera

Estado: VIGENTE para MapLibre protegido y autenticacion ligera; REEMPLAZADA
desde 2026-07-08 en lo relativo a mantener Leaflet publico como fallback por
defecto.

Decision:

- MapLibre pasa a abrirse desde `/protected/maplibre/index.html` en la webUI de Home Assistant.
- Los GeoJSON y `source_status.json` de MapLibre se sirven desde `/protected/maplibre/data/*` y requieren sesion valida.
- Leaflet se mantenia publicado en `/local/rainmapper-leaflet` como fallback sin autenticacion durante la transicion; desde 2026-07-08 queda como salida legacy bajo `publish_to_www`.
- Los usuarios se gestionan de forma manual en `/share/rainmapper/users.json`.
- Historial de formato: primero se considero un fichero plano separado por punto y coma. Esa decision queda reemplazada por `users.json` como formato unico.
- `users.json` permite campos extensibles: `username`, `name`, `email`, `password`, `role`, `enabled`, `max_devices` y `must_change_password`. `username` es el identificador de login; `name` es el nombre de la persona; `email` queda como contacto.
- Roles soportados: `free`, `basic`, `pro` y `admin`.
- Limites por defecto: `free=1`, `basic=2`, `pro=3`, `admin=0`; `0` significa dispositivos ilimitados. El campo `max_devices` permite sobrescribir el limite por usuario.
- El primer login de un usuario registra un `device_id` generado por el navegador en `/share/rainmapper/devices.json`; nuevos dispositivos se aceptan hasta el limite del usuario. Los dispositivos ya registrados pueden reutilizarse aunque el usuario haya alcanzado su limite.
- En HA, `run.sh` crea `users.json` desde `users.example.json` y `devices.json` vacio si faltan, sin sobrescribir ficheros existentes.
- La WebUI HA incorpora una pagina `Users`, pensada para acceso por Ingress/Home Assistant, para crear usuarios, borrar usuarios, activar/desactivar acceso, editar rol/max_devices, establecer nuevas contrasenas, forzar cambio de contrasena y borrar dispositivos de forma granular. `Delete user` borra tambien todos sus dispositivos asociados. `Set password` guarda una contrasena definida por el administrador y borra dispositivos; `Reset password` marca `must_change_password=true`, borra dispositivos y obliga al usuario a elegir una contrasena distinta tras autenticarse con la actual.

Motivo:

- Evitar compartir un enlace publico sin control durante pruebas con terceros.
- Mantener una solucion simple y reversible antes de construir una gestion real de usuarios, permisos o suscripciones.
- Proteger los datos en servidor, no solo ocultar controles en JavaScript.

Alternativas descartadas:

- Proteger solo el HTML del visor: insuficiente, porque los GeoJSON seguirian accesibles directamente.
- Implementar ya una base de datos de usuarios completa: excesivo para la fase actual de pruebas privadas.
- Usar cookies de sesion como unico mecanismo: se evita de momento para mantener un flujo simple y portable entre Safari, Chrome, Firefox y Android/iOS usando `localStorage` + cabeceras.

Consecuencias:

- Si un usuario con limite de dispositivos borra datos del navegador, generara un nuevo `device_id` y puede quedar bloqueado hasta que se limpie o desactive un registro anterior en `devices.json`.
- El add-on HA publica `8099/tcp` para que Cloudflared pueda apuntar al servidor Rainmapper con `service: http://<HA_IP>:8099`; las reglas externas de Cloudflare para MapLibre deben apuntar a `/protected/maplibre/index.html`, no a `/local/rainmapper-maplibre/index.html`.
- La limpieza defensiva de `/config/www/rainmapper-maplibre/data` queda preparada en codigo, pero aplazada temporalmente para mantener `/local/rainmapper-maplibre/index.html` como fallback funcional mientras se valida Cloudflared/puerto 8099.
- Las contrasenas en claro de `users.json` se migran automaticamente a hash PBKDF2 al primer login correcto.
- El formato antiguo separado por punto y coma se retira tras validar la migracion en la unica instalacion HA activa. Desde este punto, `users.json` es el unico formato soportado.
- El visor Docker local queda sin autenticacion para mantenerlo como entorno rapido de pruebas.
- Modificado el 2026-06-22: los fallbacks externos `leaflet.nomentero.com` y `maplibre.nomentero.com` quedan detras de Cloudflare Access. El fallback local `/local/rainmapper-maplibre` sigue existiendo en HA, pero ya no debe quedar expuesto externamente sin login de Cloudflare.

Estado:

Implementado en varios pasos. La proteccion basica de MapLibre fue validada manualmente por el usuario en HA `0.2.82`: `admin` pudo entrar desde Mac e iPhone, y un usuario normal quedo limitado a un dispositivo. La ampliacion a `users.json` con `username`, `name`, `email`, roles `free/basic/pro/admin` y `max_devices` esta publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.83` y cubierta por `tests/test_web_server_auth.py`. El usuario valido en HA que el login creaba `users.json` desde el formato anterior; despues se decide retirar completamente el formato anterior para evitar ambiguedades futuras. La WebUI de gestion queda publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.84`; la correccion del auto-refresh de formularios queda publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.85`; la gestion clara de `Set password`/`Reset password` queda publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.86` y pendiente de validacion HA.

## 2026-06-20 - Retirar wrappers raiz `Rainmapper.py` y `Rainmapper_Client.py`

Decision:

- Se eliminan `Rainmapper.py` y `Rainmapper_Client.py` de la raiz.
- Docker local, Home Assistant y la webUI ejecutan directamente `python -m rainmapper_core.rainmapper` y `python -m rainmapper_core.bokeh_maps`.
- La imagen HA deja de copiar wrappers Python de raiz; solo copia `stations.example.txt`, `rainmapper_core/`, `web_server.py` y `run.sh`.

Motivo:

- Los wrappers ya no aportaban compatibilidad operativa suficiente y mantenian la confusion sobre donde vive el codigo real.
- El core ya esta empaquetado como modulo ejecutable y el build HA se hace desde la raiz del repositorio.

Consecuencias:

- Cualquier uso manual antiguo `python Rainmapper.py ...` debe cambiarse por `python -m rainmapper_core.rainmapper ...`.
- Cualquier uso manual antiguo `python Rainmapper_Client.py` debe cambiarse por `python -m rainmapper_core.bokeh_maps`.
- Los wrappers shell (`run.sh`, `local_all.sh`, `local_maps.sh`, `local_update.sh`) se mantienen como interfaz comoda de usuario.

## 2026-06-20 - Retirar wrappers raiz de configuracion e incremental upsert

Decision:

- Se eliminan `const.py`, `config.py`, `config_wunderground.py` e `incremental_upsert.py` de la raiz.
- El codigo y los tests importan directamente desde `rainmapper_core.config` y `rainmapper_core.incremental_upsert`.
- La imagen HA deja de copiar esos wrappers desde la raiz.

Motivo:

- Ya no hay codigo interno que dependa de los imports legacy top-level.
- Mantener esos wrappers en la raiz creaba confusion sobre donde vive la configuracion real.
- La raiz queda reservada a entrypoints shell de usuario que siguen aportando compatibilidad, como `run.sh` y `local_*.sh`; los entrypoints Python se ejecutan con `python -m rainmapper_core...`.

Consecuencias:

- Cualquier uso manual antiguo `from const import ...` o `from incremental_upsert import ...` debe cambiarse a imports desde `rainmapper_core`.
- Este cambio requiere validar Docker local, smoke test y build HA porque afecta al contenido copiado a la imagen.

## 2026-06-20 - Construir HA desde la raiz y retirar copias fisicas de core

Sustituye la decision operativa anterior de sincronizar raiz -> `rainmapper-app/app` con `scripts/sync-app-files.sh`.

Decision:

- `rainmapper-app/Dockerfile` se construye con la raiz del repositorio como contexto.
- La imagen HA copia `rainmapper_core/`, wrappers raiz, configuracion compartida y los modulos HA de `rainmapper-app/app/` directamente desde la raiz.
- `rainmapper-app/app` queda reservado a codigo especifico de HA; actualmente contiene `web_server.py`, `mushroom_catalogs_ui.py`, `mushroom_profiles_ui.py` y `mushroom_gis_mappings_ui.py`.
- `scripts/sync-app-files.sh` y `scripts/sync-manifest.sh` se retiran.

Motivo:

- Eliminar la duplicidad fisica que obligaba a sincronizar manualmente o mediante script.
- Evitar que HA y Docker local puedan quedar con versiones distintas del core.
- Hacer que `requirements.txt` tenga una sola fuente de verdad para el build HA.

Alternativas descartadas:

- Mantener copias HA sincronizadas: resuelto temporalmente, pero seguia generando confusion y trabajo recurrente.
- Convertir ya todo en paquete instalable Python: se pospone; el build desde raiz resuelve la duplicidad con menos riesgo.

Consecuencias:

- El build HA ya no soporta usar `rainmapper-app` como contexto Docker aislado; debe usarse la raiz del repo.
- `scripts/build-push-ha-image.sh` y `.github/workflows/build-rainmapper-app.yml` usan ese contexto raiz.
- `scripts/smoke-test.sh` valida que no vuelvan copias de core a `rainmapper-app/app`.

## 2026-06-20 - Retirar wrappers raiz/HA de Tomap y GeoJSON

Se eliminan los wrappers `tomap_builder.py` y `tomap_to_geojson.py` de la raiz y sus copias en `rainmapper-app/app`.

Decision:

- `rainmapper_core.tomap` se ejecuta directamente con `python -m rainmapper_core.tomap`.
- `rainmapper_core.geojson` se ejecuta directamente con `python -m rainmapper_core.geojson`.
- Docker local, Home Assistant, webUI, smoke test y pruebas Docker offline pasan a usar esos modulos core.

Motivo:

- Tomap y GeoJSON ya son piezas del core y no necesitan wrappers historicos en raiz.
- Reducir entrypoints duplicados evita confusion sobre donde vive la implementacion real.

Alternativas descartadas:

- Mantener wrappers por compatibilidad: ya no aportan suficiente valor frente a la confusion que generan.
- Renombrar comandos de usuario locales: se pospone; `local_maps.sh` y `local_all.sh` siguen siendo la interfaz comoda para pruebas.

Consecuencias:

- Cualquier uso manual antiguo `python tomap_builder.py` o `python tomap_to_geojson.py` debe cambiarse por `python -m rainmapper_core.tomap` o `python -m rainmapper_core.geojson`.
- Sustituida por la decision posterior de construir HA desde la raiz: la imagen HA copia `rainmapper_core/` durante el build, pero no se versiona una copia fisica en `rainmapper-app/app`.

## 2026-06-20 - Mover `Rainmapper.py` a `rainmapper_core/rainmapper.py`

Se mueve la implementacion real del runner principal de descarga y actualizacion al paquete compartido `rainmapper_core`.

Decision:

- `rainmapper_core/rainmapper.py` pasa a ser la unica implementacion real de descarga, historicos, estado por fuente y metricas.
- `Rainmapper.py` queda como wrapper compatible que ejecuta `rainmapper_core.rainmapper`; HA lo copia desde la raiz durante el build.
- No se parte todavia la logica interna del runner; esta fase solo elimina la duplicidad real raiz/app HA.

Motivo:

- `Rainmapper.py` era el ultimo bloque grande con implementacion duplicada entre raiz y HA.
- Mantener el nombre historico como wrapper evita romper Docker local, HA, scripts existentes y uso manual.

Alternativas descartadas:

- Renombrarlo a `runner.py`: descartado por preferencia del proyecto y porque `rainmapper.py` describe mejor el modulo principal.
- Partir fuentes/CLI/estado en la misma fase: descartado para no mezclar movimiento estructural con reescritura funcional.

Consecuencias:

- Sustituida por la decision posterior de construir HA desde la raiz: no queda copia versionada de `rainmapper_core/` dentro de `rainmapper-app/app`.
- Validado localmente con smoke, Docker offline y `local_update.sh`; HA 0.2.79 valido el movimiento antes de retirar las ultimas copias.

## 2026-06-20 - Mover Bokeh y visores compartidos a `rainmapper_core`

Se mueve la implementacion compartida de mapas clasicos Bokeh y los visores web estaticos al paquete core.

Decision:

- `Rainmapper_Client.py` queda como entrypoint compatible y la implementacion real pasa a `rainmapper_core/bokeh_maps.py`.
- Los visores pasan a:
  - `rainmapper_core/viewers/leaflet-viewer/`
  - `rainmapper_core/viewers/maplibre-viewer/`
- Se retiran las rutas compatibles `leaflet-viewer/` y `maplibre-viewer/` de la raiz; las pruebas locales usan directamente `rainmapper_core/viewers/...`.
- `web_server.py` publica directamente desde `/app/rainmapper_core/viewers/leaflet-viewer` y `/app/rainmapper_core/viewers/maplibre-viewer`, por lo que se retiran las copias separadas `rainmapper-app/app/leaflet-viewer` y `rainmapper-app/app/maplibre-viewer`.

Motivo:

- Bokeh y visores son compartidos por Docker local y Home Assistant, no especificos de ningun runtime.
- Moverlos como bloques coherentes reduce la estructura hibrida sin tocar todavia `web_server.py`, URLs publicas ni Dockerfile de HA.

Alternativas descartadas:

- Mantener copias separadas en `rainmapper-app/app`: descartado tras validar que `web_server.py` puede publicar directamente desde `rainmapper_core/viewers`.
- Eliminar rutas compatibles de raiz: se descarta temporalmente porque romperia comandos locales, documentacion y pruebas existentes.

## 2026-06-20 - Mover configuracion Python compartida a `rainmapper_core/config`

Se mueve la implementacion real de `rainmapper_core/config/const.py`, `rainmapper_core/config/config.py` y `rainmapper_core/config/config_wunderground.py` a `rainmapper_core/config/`.

Motivo:

- Son configuracion compartida por Docker local y Home Assistant.
- Mantenerlas en raiz perpetua la estructura hibrida que se quiere reducir en la fase 5.
- Moverlas como bloque coherente evita una secuencia indefinida de micro-refactors.

Decision:

- Crear `rainmapper_core/config/`.
- Mantener wrappers compatibles en raiz y en `rainmapper-app/app`.
- Actualizar imports internos para usar `rainmapper_core.config`.
- Mantener los wrappers aunque el codigo interno ya no dependa de ellos, para no romper usos manuales o scripts externos con imports historicos.

Detalle importante:

- `rainmapper_core/config/const.py` mantiene nombres historicos con guion bajo (`_DATA_PATH`, `_max_threads`, etc.). La decision posterior del 2026-06-20 retira el wrapper raiz, por lo que el import canonico es `rainmapper_core.config.const`.
- La implementacion movida calcula `_script_path` como la raiz del runtime, no como `rainmapper_core/config`, para conservar rutas `Data`, `Tomap` y `Plots`.

Alternativas descartadas:

- Eliminar wrappers en la misma fase: mas limpio a largo plazo, pero menos conservador. Se pospone hasta que no haya riesgo de romper usos externos o hasta una fase de limpieza dedicada.
- Mover constantes una a una: descartado porque prolonga la refactorizacion sin aportar seguridad adicional.

## 2026-06-20 - Mover runtime Docker local a `rainmapper-local`

### Decision
Mover los ficheros especificos del Docker local a `rainmapper-local/` y mantener wrappers compatibles en la raiz para no romper comandos habituales.

Quedan en `rainmapper-local/`:

- `Dockerfile`
- `docker-compose.yml`
- `run.sh`
- `local_all.sh`
- `local_maps.sh`
- `local_update.sh`

La raiz conserva `local_all.sh`, `local_maps.sh`, `local_update.sh` y `run.sh` como wrappers, y `docker-compose.yml` como include de compatibilidad. No se conserva `Dockerfile` en raiz para evitar builds directos incorrectos con `docker build .`; la ruta canonica es `rainmapper-local/Dockerfile`.

### Motivo
Avanzar la fase 5 hacia la estructura `core/app/local` sin tocar todavia la imagen de Home Assistant ni la logica de descarga. Esto separa responsabilidades de carpetas sin mezclarlo con cambios funcionales.

### Alternativas consideradas
Mover tambien la app HA en el mismo paso, eliminar wrappers de raiz inmediatamente, o mantener todo el runtime local en raiz hasta una reestructuracion completa.

### Consecuencias
Los comandos antiguos desde raiz siguen funcionando, pero la ubicacion canonica del runtime local pasa a ser `rainmapper-local/`. La fase siguiente puede centrarse en mover mas codigo compartido a `rainmapper_core/` sin arrastrar Docker local en la raiz.

### Ficheros afectados
- `rainmapper-local/`
- `Dockerfile`
- `docker-compose.yml`
- `run.sh`
- `local_all.sh`
- `local_maps.sh`
- `local_update.sh`
- `docs/core-refactor.md`
- `docs/architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Implementada en alcance conservador. Pendiente de validacion final y commit.

## 2026-06-20 - Mantener estructura hibrida, pero mover librerias internas por fuente

### Decision
Mantener de momento la estructura actual del repositorio:

- Scripts/entrypoints locales en la raiz.
- Paquete compartido progresivo en `rainmapper_core/`.
- Paquete de Home Assistant en `rainmapper-app/`.
- Copia operativa empaquetada en `rainmapper-app/app`, sincronizada desde la raiz.

Modificacion posterior de la misma fase: mover las librerias internas acopladas a fuentes dentro de `rainmapper_core/sources/`:

- `sodapy_local/` -> `rainmapper_core/sources/sodapy_local/`
- `meteoclimatic_local/` -> `rainmapper_core/sources/meteoclimatic_local/`
- `util/` -> `rainmapper_core/sources/wunderground/`

### Motivo
La estructura no es la ideal a largo plazo, pero funciona como transicion segura. Cambiar ahora carpetas, imports, Dockerfiles y contexto de build de Home Assistant en el mismo bloque aumentaria el riesgo sin aportar una mejora funcional inmediata.

El build de HA y el fallback de GitHub Actions usan `rainmapper-app` como contexto Docker. Hacer que la imagen copie directamente ficheros desde la raiz requeriria cambiar ese flujo y podria afectar instalacion/publicacion en HA, asi que esa parte se mantiene sin cambios.

Mover las librerias completas por fuente reduce duplicidad y aclara donde viven los clientes/helpers de ingesta sin partir todavia la logica de `Rainmapper.py`. Se evita mover constantes o funciones una por una.

### Alternativas consideradas
Reorganizar ya el repositorio hacia una estructura tipo `src/`, dejar las librerias internas en raiz hasta el refactor completo de `Rainmapper.py`, o cambiar el Dockerfile de HA para construir desde la raiz del repo.

### Consecuencias
La duplicidad fisica raiz/app HA se mantiene por ahora, pero queda controlada operativamente con `scripts/sync-manifest.sh`, `scripts/sync-app-files.sh` y `scripts/smoke-test.sh`.

La reorganizacion global de carpetas queda aplazada hasta que el core este mas separado y haya mas cobertura alrededor de `Rainmapper.py`. Las librerias de fuente ya no deben importarse desde rutas top-level antiguas.

### Ficheros afectados
- `scripts/sync-manifest.sh`
- `scripts/sync-app-files.sh`
- `scripts/smoke-test.sh`
- `rainmapper_core/sources/`
- `Rainmapper.py`
- `docs/core-refactor.md`
- `docs/architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Confirmada como criterio conservador para cerrar Fase 3 inicial.

## 2026-06-19 - Upsert incremental por estacion y dia

### Decision
Actualizar los historicos `Data/*_incremental.csv` con una regla comun en `rainmapper_core/incremental_upsert.py`: la identidad logica de una lectura diaria es `Codi Estació` + `Data Local`.

La fila nueva manda para todos los valores no nulos. Si una descarga nueva trae `NaN` en una columna, se conserva el valor antiguo no nulo de esa misma estacion/dia.

### Motivo
El patron anterior combinaba `csv_old.update(csv)` por `Codi Estació` + `Data Local` con un `merge` posterior por todas las columnas. Eso evitaba duplicados exactos, pero podia dejar duplicados logicos cuando una fila nueva tenia `NaN` en temperatura/humedad y la antigua tenia valores. Se detecto en Meteocat con datos reales copiados de HA: 28 filas duplicadas por clave, algunas recientes de junio de 2026.

### Alternativas consideradas
Mantener `merge` por todas las columnas, hacer append puro, quedarse siempre con la fila mas completa o migrar ya a SQLite/Parquet.

### Consecuencias
El CSV sigue siendo el formato persistente, pero la semantica de actualizacion queda explicita y testeada. Se limpian duplicados existentes cuando el incremental se vuelve a guardar. La migracion a SQLite/Parquet queda pospuesta hasta que haya una razon clara de rendimiento, consulta o integridad.

### Ficheros afectados
- `rainmapper_core/incremental_upsert.py`
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `tests/test_incremental_upsert.py`

### Estado
Implementada y validada localmente con datos copiados de HA. `MAX_THREADS=3 ./local_update.sh` termino con exit code 0; Meteocat quedo en 316685 filas y 0 duplicados por clave; Meteoclimatic y Wunderground quedaron con 0 duplicados. `MODE=maps`, tests unitarios y `./scripts/smoke-test.sh` pasaron correctamente. Validada tambien en HA `0.2.77`: `Run update` termino con exit code 0, Meteocat quedo en 316685 filas y `Generate maps` publico visores con `v=0.2.77`.

## 2026-06-19 - Medir duraciones por fuente con temporizadores locales

### Decision
Guardar duraciones reales por fuente en `Data/source_status.json` usando temporizadores locales por proceso, y mostrarlas en la webUI de Home Assistant. Para Meteocat se guardan ademas subtiempos de metadata, condiciones, precipitacion, merge y guardado.

MapLibre no debe mostrar tiempos de proceso; el visor solo necesita estado operativo por fuente para saber si los datos publicados son frescos, degradados o desconocidos.

### Motivo
Al ejecutar fuentes en paralelo, los logs basados en `start_count()`/`end_count()` no son metricas fiables porque usan un temporizador global compartido. En el log de HA `0.2.75`, Meteocat mostraba subtiempos y un supuesto final incoherentes porque otros hilos podian pisar el temporizador.

### Alternativas consideradas
Seguir interpretando los tiempos del log, rehacer todo el sistema de logging, o mostrar todas las metricas tambien en MapLibre.

### Consecuencias
La webUI pasa a ser el sitio operativo para comparar duraciones por fuente y diagnosticar cuellos de botella. Los logs antiguos siguen siendo utiles como trazas humanas, pero no como base para decisiones de rendimiento cuando hay hilos.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/app/web_server.py`
- `docs/codex-handoff.md`
- `docs/architecture.md`
- `docs/todo.md`

### Estado
Implementada y validada en Docker local con `MAX_THREADS=2 ./local_update.sh`: `source_status.json` incluye duraciones reales para Meteoclimatic, Meteocat y Wunderground, y subtiempos para Meteocat. Pendiente de validar visualmente en HA tras bump/publicacion.

## 2026-06-19 - Extraer Tomap de forma conservadora

### Decision
Crear `tomap_builder.py` como script independiente para reconstruir CSV `Tomap` desde historicos incrementales `Data/`, y usarlo en `MODE=maps`/`Generate maps` antes de generar Bokeh y GeoJSON.

Modificacion del 2026-06-19: tras validar `Generate maps` en HA `0.2.74`, se retira el bloque ejecutable inline de generacion `Tomap` de `Rainmapper.py`. Despues de validar `Run all` y la actualizacion local de incrementales, se eliminan tambien los helpers legacy `create_grouped` y `create_last_rains` de `Rainmapper.py`.

### Motivo
Permite regenerar mapas y GeoJSON tras cambios de formato o de `last_rains_history` sin descargar datos nuevos ni ejecutar un `Run all`. Mantener `Rainmapper.py` intacto reduce el riesgo inicial porque el flujo historico de `Run all` sigue disponible mientras se valida el nuevo builder.

### Alternativas consideradas
Eliminar directamente el bloque `Tomap` de `Rainmapper.py`, importar funciones desde `Rainmapper.py`, o esperar a una separacion completa del core en paquete reutilizable.

### Consecuencias
La ruta activa de generacion `Tomap` pasa a ser `tomap_builder.py`. `Rainmapper.py` queda centrado en descarga, historicos y estado por fuente.

### Ficheros afectados
- `tomap_builder.py`
- `run.sh`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `scripts/sync-app-files.sh`
- `tests/test_tomap_builder.py`

### Estado
Implementada. `Run all` local queda validado con `local_all.sh`, `Generate maps` queda validado en HA, y la limpieza de helpers legacy queda validada con `MAX_THREADS=3 ./local_update.sh`, comprobando que las descargas actuales quedan contenidas en sus incrementales.

## 2026-06-18 - No basar una app comercial en Wunderground sin acuerdo escrito

### Decision
Mantener Wunderground como fuente operativa de uso propio por ahora, pero no considerarlo una fuente valida para una futura app comercial sin permiso/acuerdo escrito de The Weather Company.

### Motivo
La API PWS/Data Feed oficial de The Weather Company requiere API key y el pricing publico de Weather Data APIs muestra un plan Standard de 500 USD/mes, con enfoque enterprise, lo que no encaja con el proyecto actual. Ademas, las condiciones de uso de TWC/Wunderground consultadas el 2026-06-18 limitan el uso general de los servicios y el PWS Data Feed a uso personal/no comercial, prohiben copiar/monitorizar datos mediante scrapers para fines comerciales o no autorizados sin permiso escrito, y exigen acuerdo separado para uso comercial del Data Feed.

### Alternativas consideradas
Usar la API PWS oficial de The Weather Company, usar scraping HTML de Wunderground como fuente comercial, buscar endpoints no oficiales usados por la web, sustituir Wunderground por fuentes con licencia compatible o negociar derechos.

### Consecuencias
La optimizacion de Wunderground puede seguir teniendo sentido para uso privado y para la instalacion actual, pero la arquitectura comercial futura debe prever retirar Wunderground, reemplazarlo por otra fuente o negociar licencia. Cualquier investigacion de endpoints no oficiales queda como opcion tecnica de alto riesgo y no como base comercial.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper_core/sources/wunderground/`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Confirmada como restriccion de estrategia. No implica cambios de codigo inmediatos.

## 2026-06-18 - Permitir update degradado por fuente con estado explicito

### Decision
Si una fuente completa falla durante `update`, Rainmapper intenta continuar usando su incremental previo y marca la fuente como `STALE` en `Data/source_status.json`. Si no hay incremental utilizable, la marca como `NOK`. La webUI de Home Assistant muestra estado y exit code por fuente.

Modificacion del 2026-06-18: el exit code global debe distinguir tres estados: `0` exito completo, `2` exito degradado con al menos una fuente habilitada usable y `1` fallo total/no recuperable. `Run all` debe continuar a `maps` cuando `update` devuelve `2`, pero conservar `2` como resultado final.

### Motivo
Un fallo temporal de Meteocat, Meteoclimatic o Wunderground no deberia impedir publicar datos actualizados de las otras fuentes. Al mismo tiempo, no se deben publicar mapas parciales o con datos reutilizados sin una senal visible.

### Alternativas consideradas
Mantener el fallo global inmediato ante cualquier excepcion de fuente, o silenciar el fallo y publicar mapas sin trazabilidad.

### Consecuencias
Los mapas pueden combinar datos frescos con incrementales previos si una fuente cae, pero la webUI deja trazabilidad visible. MapLibre muestra badges de estado por fuente cuando `source_status.json` esta publicado. El exit code `2` permite automatizaciones y webUI distinguir exito degradado sin tratarlo como fallo total.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/CHANGELOG.md`

### Estado
Implementada parcialmente en `0.2.71` y ampliada con semantica global `0/2/1` tras la decision del 2026-06-18; pendiente de validacion HA con fallo real o simulado.

## 2026-06-17 - Ejecutar Home Assistant en modo serve (fecha aproximada)

### Decision
La app de Home Assistant debe arrancar normalmente en `mode: serve`.

### Motivo
Permite tener la app viva en sidebar, webUI por ingress, schedule interno y botones manuales sin depender de arrancar contenedores puntuales.

### Alternativas consideradas
Ejecutar contenedores de un solo uso con `update` o `all` desde automatizaciones externas.

### Consecuencias
El contenedor queda abierto, pero consume pocos recursos. La webUI pasa a ser el punto operativo principal.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`

### Estado
Confirmada.

## 2026-06-17 - Persistir datos fuera del contenedor (fecha aproximada)

### Decision
Los datos viven en `/share/rainmapper` en Home Assistant y en `docker-data` en Docker local.

### Motivo
Evitar perder historicos y configuraciones al actualizar/reinstalar la app.

### Alternativas consideradas
Guardar datos dentro de la imagen/contenedor.

### Consecuencias
Los updates no deben machacar `stations.txt`, `ignore_stations_tomap.txt` ni historicos CSV. Hay que tener cuidado con permisos y symlinks.

### Ficheros afectados
- `rainmapper-app/run.sh`
- `docker-compose.yml`
- `.gitignore`

### Estado
Confirmada.

## 2026-06-17 - Mantener Docker local para pruebas en Mac (fecha aproximada)

### Decision
Conservar un Docker local separado del paquete HA.

### Motivo
Permite probar cambios de core y mapas antes de llevarlos a Home Assistant/RPi.

### Alternativas consideradas
Desarrollar directamente sobre la app HA.

### Consecuencias
Hay duplicidad de scripts entre raiz y app HA. Se gana seguridad operativa a costa de sincronizacion manual.

### Ficheros afectados
- `Dockerfile`
- `docker-compose.yml`
- `run.sh`
- `rainmapper-app/app/`

### Estado
Confirmada, revisable.

## 2026-06-17 - Publicar mapas en /config/www (fecha aproximada)

### Decision
Cuando `publish_to_www` esta activo, la app copia mapas y visores a `/config/www` para servirlos como `/local/...`.

### Motivo
Permite abrir mapas desde HA, movil y enlaces externos via dominio/Cloudflare.

### Alternativas consideradas
Servir solo desde la webUI/ingress de la app.

### Consecuencias
Los mapas pueden quedar accesibles por URL publica si HA esta publicado. La autorizacion granular no esta implementada todavia.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`

### Estado
REEMPLAZADA parcialmente por la decision 2026-07-08: `/config/www` queda solo
para salidas legacy cuando `publish_to_www=true`.

## 2026-06-17 - Mantener Bokeh, Leaflet y MapLibre durante transicion (fecha aproximada)

### Decision
No retirar Bokeh todavia; publicar tambien Leaflet y MapLibre. MapLibre queda como visor principal recomendado y Leaflet como fallback.

### Motivo
Bokeh es la referencia historica. Leaflet funciona bien en movil segun validacion manual/reportada por el usuario; pendiente de confirmacion automatizada. MapLibre permite mapas vectoriales mas nitidos y desde `0.2.47` tambien puede cubrir las capas raster Hybrid y Topographic que antes estaban solo en Leaflet. Desde `0.2.48`, MapLibre tambien prueba Satellite+, combinando imagen Esri con orientacion vectorial OpenFreeMap.

### Alternativas consideradas
Eliminar Bokeh inmediatamente o sustituir Leaflet por MapLibre de golpe.

### Consecuencias
Hay mas mantenimiento, pero se puede comparar comportamiento y calidad antes de migrar. MapLibre ya esta validado manualmente como funcional en movil segun reporte del usuario; pendiente de confirmacion automatizada. Modificado en `0.2.47`: MapLibre incorpora Hybrid raster por defecto y Topographic raster, manteniendo los estilos vectoriales. Modificado en `0.2.48`: se descarta Tracestrack por ahora porque requiere app key para vector maps; el coste/condiciones exactas quedan pendientes de confirmar si se retoma. Se prueba Satellite+ con OpenFreeMap sobre imagen Esri. Modificado en `0.2.53`: MapLibre queda como visor principal recomendado tras validacion manual en HA/iPhone; Leaflet sigue publicado como fallback.

### Ficheros afectados
- `Rainmapper_Client.py`
- `tomap_to_geojson.py`
- `leaflet-viewer/`
- `maplibre-viewer/`
- `rainmapper-app/app/web_server.py`

### Estado
REEMPLAZADA por la decision 2026-07-08. MapLibre protegido sigue siendo el
visor principal; Bokeh, Leaflet publico y visores publicos antiguos quedan como
legacy opcional bajo `publish_to_www`.

## 2026-06-17 - Retirar ruta legacy rainmapper-mobile

### Decision
Dejar de publicar `/local/rainmapper-mobile` desde la app de Home Assistant.

### Motivo
La ruta legacy ya no se utiliza. Cloudflare tenia redirecciones hacia `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre` segun reporte del usuario. Modificado por la decision del 2026-06-21: MapLibre debe exponerse mediante `/protected/maplibre/index.html`; Leaflet se mantiene en `/local/rainmapper-leaflet` como fallback.

### Alternativas consideradas
Mantener `/local/rainmapper-mobile` indefinidamente como alias de compatibilidad.

### Consecuencias
Se reduce una ruta duplicada y se simplifica la publicacion. En la siguiente generacion de mapas se elimina cualquier carpeta antigua `/config/www/rainmapper-mobile` que quedara publicada.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `README.md`
- `rainmapper-app/README.md`
- `rainmapper-app/DOCS.md`

### Estado
Confirmada.

## 2026-06-17 - App settings con enlaces fallback

### Decision
La pagina `/settings` de la webUI muestra el enlace recomendado a la configuracion de la app y rutas fallback en vez de redirigir automaticamente a una unica URL.

### Motivo
La ruta de configuracion de Home Assistant puede variar por version o por formato de slug. Una redireccion automatica a una sola URL podia funcionar en una instalacion y fallar en otra sin dejar alternativas visibles.

### Alternativas consideradas
Mantener la redireccion automatica a `/config/app/<slug>/config`.

### Consecuencias
Abrir la configuracion requiere un clic adicional, pero la pagina es mas portable y da opciones visibles si cambia la ruta o el slug. Modificado en `0.2.44`: solo se muestra el enlace recomendado por defecto; los fallbacks quedan en una seccion avanzada porque en la instalacion actual solo funciona el recomendado.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`

### Estado
Confirmada, modificada en `0.2.44`.

## 2026-06-17 - Ingles para webUI HA y changelog

### Decision
Usar ingles para los textos visibles de la webUI de Home Assistant, metadata de la app HA y `rainmapper-app/CHANGELOG.md`.

### Motivo
Home Assistant y el changelog son superficies de usuario/soporte donde conviene mantener un idioma consistente y portable.

### Alternativas consideradas
Mantener mezcla de ingles/espanol o traducir tambien todos los logs internos en el mismo cambio.

### Consecuencias
La version `0.2.45` corrige los textos visibles detectados y traduce entradas antiguas del changelog. Modificado en `0.2.46`: los logs operativos principales del core tambien pasan a ingles, incluyendo progreso y resumen Wunderground. README/DOCS de la app HA se mantienen en espanol de momento porque la app es principalmente de uso propio y no una distribucion publica para terceros.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Confirmada.

## 2026-06-17 - Usar GeoJSON como capa comun para visores nuevos (fecha aproximada)

### Decision
Leaflet y MapLibre consumen GeoJSON generado desde `Tomap`.

### Motivo
Separar datos de visualizacion, reutilizar los mismos datos para varios visores y preparar una futura app movil.

### Alternativas consideradas
Parsear directamente CSV `Tomap` en navegador o seguir solo con HTML Bokeh.

### Consecuencias
`tomap_to_geojson.py` se vuelve pieza clave. Cambios en `Tomap` requieren revisar el conversor.

### Ficheros afectados
- `tomap_to_geojson.py`
- `rainmapper_core/viewers/leaflet-viewer/app.js`
- `rainmapper_core/viewers/maplibre-viewer/app.js`

### Estado
Confirmada.

## 2026-06-18 - Usar terreno 3D en MapLibre con DEM externo

### Decision
Anadir `3D terrain`, apagado por defecto, en MapLibre usando una fuente externa Terrarium/Mapzen como `raster-dem`. Modificado el 2026-06-18: tras validacion manual en local, HA e iPhone, deja de considerarse prototipo experimental y queda como funcionalidad definitiva.

### Motivo
MapLibre permite inclinar/rotar la camara, pero para relieve real necesita tiles DEM codificados. Los mapas actuales Satellite+, Hybrid, Topographic y Liberty no contienen elevacion usable por si mismos. El fichero local `Iberia_HighResolution.CDEM` no fue reconocido por GDAL y Land no permitio exportarlo correctamente durante una prueba manual fuera del repo; pendiente de confirmar si se retoma esa via.

### Alternativas consideradas
Incluir un DEM dentro de la imagen Docker, convertir primero datos IGN/CNIG/Copernicus, usar el CDEM de Land/TwoNav o no probar 3D.

### Consecuencias
No se aumenta el tamano de la imagen Docker. La opcion queda dependiente de un proveedor externo; si esa dependencia falla, rinde mal o se quiere mas control, se estudiara generar tiles DEM propios y servirlos fuera de la imagen, por ejemplo desde `/config/www` o Cloudflare R2.

### Ficheros afectados
- `rainmapper_core/viewers/maplibre-viewer/`
- `docs/codex-handoff.md`
- `docs/architecture.md`
- `docs/todo.md`

### Estado
Funcionalidad definitiva, apagada por defecto. Validacion manual/reportada en local, HA e iPhone; pendiente solo de observacion operativa de rendimiento/dependencia externa.

## 2026-06-17 - Crear smoke test versionado

### Decision
Mantener un comando unico `./scripts/smoke-test.sh` para validaciones rapidas del repositorio.

### Motivo
El proyecto no tiene framework de tests completo y hay riesgo recurrente de errores de sintaxis, metadata HA desalineada o copias raiz/app HA desincronizadas.

### Alternativas consideradas
Seguir ejecutando comandos manuales sueltos en cada sesion.

### Consecuencias
El smoke test no sustituye pruebas funcionales en Docker/HA ni validacion movil, pero deja una red basica repetible para cambios pequenos y medianos.

### Ficheros afectados
- `scripts/smoke-test.sh`
- `README.md`
- `docs/architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Confirmada.

## 2026-06-17 - Sincronizacion operativa raiz/app HA sin refactor

### Decision
Mantener la duplicidad actual entre raiz y `rainmapper-app/app`, pero anadir `scripts/sync-app-files.sh` como comando explicito para copiar scripts raiz y visores a la app HA.

### Motivo
La duplicidad todavia existe y una refactorizacion estructural del core seria mas amplia. Un comando versionado reduce errores manuales mientras se mantiene el flujo actual.

### Alternativas consideradas
Refactorizar ya el core en un paquete Python unico o seguir copiando ficheros manualmente.

### Consecuencias
`scripts/sync-app-files.sh` sincroniza raiz -> app HA y `scripts/smoke-test.sh` verifica que las copias quedan identicas. No elimina la deuda arquitectonica; solo la mitiga operativamente.

### Ficheros afectados
- `scripts/sync-app-files.sh`
- `scripts/smoke-test.sh`
- `README.md`
- `docs/codex-handoff.md`
- `docs/architecture.md`
- `docs/todo.md`

### Estado
Confirmada.

## 2026-06-17 - Proteger historicos antes de cambios de escritura CSV

### Decision
Antes de cambios que puedan escribir o reestructurar historicos CSV, se debe trabajar con backup o copia temporal y validar la salida con `scripts/check-history.py`.

### Motivo
Los CSV historicos son el activo central del proyecto y pueden corromperse si hay errores en pandas, merges, deduplicado, fechas o escritura de columnas.

### Alternativas consideradas
Confiar solo en validacion manual despues de ejecutar contra datos reales.

### Consecuencias
Los cambios de core de datos llevan un paso operativo adicional, pero reducen el riesgo de perdida o corrupcion de historicos.

### Ficheros afectados
- `scripts/backup-data.sh`
- `scripts/check-history.py`
- `docs/history-safety.md`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Confirmada.

## 2026-06-17 - Ignorar estaciones anomalas con fichero manual (fecha aproximada)

### Decision
Crear `ignore_stations_tomap.txt` y aplicarlo solo al generar GeoJSON.

### Motivo
Permite ocultar estaciones con outliers sin borrar ni alterar historicos. Si el outlier caduca del periodo, la estacion puede volver quitandola del fichero.

### Alternativas consideradas
Borrar datos historicos, filtrar automaticamente outliers o desactivar descarga de la estacion.

### Consecuencias
El control es manual. Afecta solo Leaflet/MapLibre, no Bokeh ni historicos.

### Ficheros afectados
- `tomap_to_geojson.py`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `README.md`
- `rainmapper-app/DOCS.md`

### Estado
Confirmada.

## 2026-06-17 - Mantener stations.txt fuera de la imagen (fecha aproximada)

### Decision
`stations.txt` se crea/preserva en `/share/rainmapper` o `docker-data`, no dentro de la imagen como unica fuente editable.

### Motivo
Permite anadir/quitar estaciones Wunderground sin reconstruir imagen.

### Alternativas consideradas
Incluir `stations.txt` fijo en Docker.

### Consecuencias
La primera instalacion debe crear una plantilla si falta. Los updates no deben sobrescribir el fichero del usuario.

### Ficheros afectados
- `rainmapper-app/run.sh`
- `docker-compose.yml`
- `stations.example.txt`

### Estado
Confirmada.

## 2026-06-17 - Usar Wunderground con un thread por defecto en RPi (fecha aproximada; reemplazada el 2026-06-20)

### Decision
Mantener `max_threads: 1` por defecto.

Modificacion 2026-06-20: esta decision queda reemplazada. Tras pruebas locales comparativas y observacion nocturna de schedules en Home Assistant/RPi sin problemas reportados, `max_threads: 3` pasa a ser el valor operativo recomendado. `max_threads: 1` queda como modo conservador de diagnostico si aparecen timeouts, errores de Wunderground o carga excesiva.

### Motivo
La RPi no debe cargarse excesivamente. El scraper es el cuello de botella, pero estabilidad y baja carga pesan mas que paralelizar agresivamente.

### Alternativas consideradas
Subir threads para acelerar scraping.

### Consecuencias
La ejecucion completa tarda mas, pero la carga es estable. Se anaden metricas para entender donde optimizar. El rendimiento actual reportado por el usuario es aceptable: update completo + generacion de mapas tarda unos 7 minutos; pendiente de confirmar automaticamente. Por eso, cambios de timeout/observabilidad quedan en baja prioridad hasta acumular mas datos.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `docker-compose.yml`
- `Rainmapper.py`

### Estado
Reemplazada el 2026-06-20 por `max_threads: 3` como valor operativo recomendado.

## 2026-06-17 - Guardar metricas de Wunderground en CSV (fecha aproximada)

### Decision
Guardar tiempos por estacion en `Data/metricas_wunderground.csv`.

### Motivo
Permite analizar estaciones lentas sin depender solo del log y prepara posible explotacion futura en Grafana/InfluxDB.

### Alternativas consideradas
Solo log, InfluxDB inmediato.

### Consecuencias
Se acumula otro CSV operativo. InfluxDB queda como mejora futura.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`

### Estado
Confirmada.

## 2026-06-17 - Soportar multiples patrones Meteoclimatic (fecha aproximada)

### Decision
`meteoclimatic_pattern` acepta varios patrones separados por coma, punto y coma o ` - `.

### Motivo
Permite recuperar varias zonas RSS sin cambiar codigo.

### Alternativas consideradas
Un solo patron fijo en `rainmapper_core/config/const.py`.

### Consecuencias
Hay un pequeno delay entre peticiones para no golpear el feed. Algunos prefijos pueden no estar soportados por Meteoclimatic aunque el codigo los acepte.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/config.yaml`

### Estado
Confirmada.

## 2026-06-17 - API keys solo por entorno/configuracion (fecha aproximada)

### Decision
No guardar API keys reales en Git. Google se configura por variables/opciones. Modificada el 2026-06-18: Jawg Maps queda retirado y ya no se configura.

### Motivo
Evitar exposicion de credenciales. Ya hubo una alerta historica por una Google API key antigua.

### Alternativas consideradas
Hardcodear claves en scripts o HTML.

### Consecuencias
Cada instalacion debe configurar sus propias claves. En mapas cliente, tokens de tiles pueden ser visibles en navegador y deben restringirse por dominio si el proveedor lo permite; por esa razon se evita mantener proveedores opcionales con token cliente si no aportan valor claro.

### Ficheros afectados
- `rainmapper_core/config/const.py`
- `rainmapper-app/config.yaml`
- `rainmapper_core/viewers/leaflet-viewer/config.js`
- `rainmapper_core/viewers/maplibre-viewer/config.js`

### Estado
Confirmada, modificada para retirar Jawg.

## 2026-06-18 - Retirar Jawg Maps

### Decision
Eliminar las capas Jawg Street/Terrain de Leaflet y MapLibre, y retirar `jawgmaps_api_key`/`JAWGMAPS_API_KEY` de la configuracion.

### Motivo
MapLibre ya cubre el uso actual con Satellite+, Hybrid, Topographic, Liberty y el prototipo 3D. Jawg anadia una API key visible en cliente, dudas de uso/licencia y complejidad de soporte sin aportar valor suficiente.

### Alternativas consideradas
Mantener Jawg como capa opcional o investigar restricciones de token por dominio antes de decidir.

### Consecuencias
Los selectores de mapas quedan mas simples y no hay token Jawg que gestionar. Si en el futuro se necesita otro proveedor con clave cliente, se documentara como nueva decision y se evaluara licencia, costes y restricciones de dominio.

### Ficheros afectados
- `leaflet-viewer/`
- `maplibre-viewer/`
- `docker-compose.yml`
- `rainmapper-app/config.yaml`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `README.md`
- `rainmapper-app/README.md`
- `rainmapper-app/DOCS.md`

### Estado
Confirmada en `0.2.69`.

## 2026-06-17 - Exponer visor por dominio/Cloudflare sin auth propia por ahora (fecha aproximada)

### Decision
Usar dominio/Cloudflare para acceder a HA/visor, pero no implementar aun autenticacion propia de Rainmapper.

### Motivo
Permite compartir y probar el visor rapidamente.

### Alternativas consideradas
Construir backend/app con auth antes de publicar visores.

### Consecuencias
Es valido para pruebas privadas, pero no para producto publico con permisos por usuario/mapa. Hay que resolverlo antes de una app iOS/Android publica.

### Ficheros afectados
- No hay configuracion Cloudflare versionada en el repo.
- `rainmapper-app/app/web_server.py` publica contenido en `/config/www`.

### Estado
Confirmada para pruebas, revisable antes de publicacion.

## 2026-06-17 - Futura app movil con API propia antes de producto publico

### Decision
Para una futura app iOS/Android publica o bajo suscripcion, no depender directamente de Home Assistant como backend publico. Mantener HA como motor privado de generacion y disenar una API/backend externo intermedio para autenticacion, permisos, filtros y serving controlado de datos. Esto no contradice la API interna que ya existe en el add-on HA para el visor MapLibre protegido (`/auth/*`, `/protected/maplibre/*`).

### Motivo
Los visores actuales y GeoJSON protegidos funcionan bien para uso privado, pero no dan el nivel de control comercial por usuario, mapa o zona que requeriria una app publica. Una app comercial necesita autorizacion en un backend externo, revocacion de acceso y una forma segura de aplicar favoritos y filtros sin exponer rutas internas de HA.

### Alternativas consideradas
Consumir directamente los GeoJSON publicados en `/local/...` desde la app movil, convertir HA en backend publico, o migrar inmediatamente todos los datos a una base de datos nueva.

### Consecuencias
La primera fase de app movil deberia definir API, auth y permisos antes de producto publico. La migracion a base de datos queda como fase posterior si GeoJSON/CSV dejan de ser suficientes.

### Ficheros afectados
- `docs/mobile-app-architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Propuesta inicial confirmada a nivel de diseno; pendiente de implementacion.

## 2026-06-17 - Cloudflare y app cross-platform como direccion de prototipo movil

### Decision
Para explorar la futura app iOS/Android, tomar como direccion preferente de prototipo una arquitectura con Cloudflare R2 para artefactos GeoJSON, Cloudflare Worker como API ligera y React Native + MapLibre React Native como app cross-platform.

### Motivo
Cloudflare forma parte del acceso externo actual segun reporte del usuario; pendiente de confirmar fuera del repositorio. Encaja con artefactos GeoJSON estaticos/cacheables. Workers evita operar un VPS en la primera fase. React Native permite una base comun iOS/Android y MapLibre alinea la app con el visor principal recomendado del proyecto.

### Alternativas consideradas
App nativa separada Swift/Kotlin, PWA, FastAPI en VPS, Supabase/Firebase como backend principal o consumo directo de GeoJSON publicados por Home Assistant.

### Consecuencias
La app futura deberia consumir una API controlada, no rutas `/local/...` de Home Assistant. Hay que definir estructura R2, manifiesto `latest.json`, endpoints minimos y una estrategia de auth/permisos antes de producto publico. La implementacion no es inmediata y puede revisarse si el prototipo muestra limitaciones.

### Ficheros afectados
- `docs/mobile-app-architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Confirmada como direccion de diseno/prototipo; pendiente de implementacion.

## 2026-06-17 - Usar imagen preconstruida GHCR para la app HA

### Decision
Configurar la app de Home Assistant para usar la imagen preconstruida `ghcr.io/cginebrosa/rainmapperha:<version>` y publicar imagen multi-arch `amd64`/`arm64` con GitHub Actions.

### Motivo
Home Assistant estaba construyendo la imagen en la Raspberry Pi en cada update, con tiempos observados cercanos a 3 minutos incluso para cambios pequenos. La documentacion oficial de Home Assistant recomienda contenedores preconstruidos como metodo preferido porque el usuario solo descarga la imagen final y evita builds locales lentos.

### Alternativas consideradas
Mantener build local en HA, construir manualmente en Mac y subir imagen a mano, o posponer la preconstruccion hasta una fase mas estable.

### Consecuencias
Los updates de HA pasan a depender de que exista en GHCR la imagen de la version correspondiente antes de actualizar en HA. El paquete GHCR debe ser accesible para Home Assistant; si queda privado, habra que hacerlo publico o configurar autenticacion. La mejora de velocidad de instalacion/update en RPi fue validada manualmente por el usuario; pendiente de confirmacion automatizada. GitHub Actions con cache no resulto util segun esa observacion manual, por lo que se reemplazo como flujo normal por build/push local desde Mac.

### Ficheros afectados
- `.github/workflows/build-rainmapper-app.yml`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Implementada en `0.2.57`. La descarga de `ghcr.io/cginebrosa/rainmapperha:0.2.57` sin build local fue validada manualmente por el usuario; pendiente de confirmacion automatizada. Modificada en `0.2.58` para anadir cache Buildx/GHA en futuras Actions. Reemplazada como flujo normal en `0.2.60` por build/push local con Buildx antes del commit de version, dejando GitHub Actions como fallback manual.

## 2026-06-17 - Publicar imagen HA con Buildx local antes del commit de version

### Decision
Usar `scripts/build-push-ha-image.sh` como flujo normal para publicar desde el Mac la imagen multi-arch `ghcr.io/cginebrosa/rainmapperha:<version>` antes de hacer commit/push del cambio de version visible para Home Assistant. GitHub Actions queda disponible solo como workflow manual de fallback.

### Motivo
GitHub Actions con cache siguio tardando alrededor de 7 minutos y Home Assistant detecta el update en cuanto ve `config.yaml`, aunque la imagen todavia no este publicada. Publicar localmente primero elimina esa ventana y aprovecha que el Mac construye mas rapido que la Raspberry Pi.

### Alternativas consideradas
Mantener GitHub Actions automatico y esperar a que termine, construir en Home Assistant, o subir imagen manual sin script versionado.

### Consecuencias
El flujo de release exige login Docker contra GHCR en el Mac y disciplina de publicar imagen antes de subir el commit de version. A cambio, HA no deberia ofrecer un update cuyo tag de imagen aun no exista. GitHub Actions deja de ejecutarse automaticamente en cada push de `rainmapper-app`. El script publica la etiqueta versionada y `latest`; Home Assistant usa la etiqueta versionada. Desde el ajuste posterior a `0.2.60`, el script limpia etiquetas locales versionadas antiguas del mismo repositorio y conserva por defecto las dos ultimas mas `latest`. El smoke completo debe ejecutarse una vez antes del build/push; no se repite tras publicar si solo se actualiza documentacion con el digest, salvo que se toque codigo runtime, configuracion HA, assets, scripts o ficheros incluidos en la imagen despues de ese smoke.

Actualizacion operativa 2026-06-28, reforzada el 2026-06-29: el criterio de "version disponible para probar en HA" requiere tanto imagen GHCR publicada/verificada como commit de bump pusheado a GitHub. HA detecta la version desde `config.yaml` en GitHub, por lo que dejar el commit solo localmente o retrasar el push para documentar mantiene al usuario bloqueado. En releases de prueba HA, despues de verificar GHCR debe hacerse commit/push inmediato de los artefactos de release y avisar al usuario. Antes de ese aviso queda prohibida cualquier actualizacion de documentacion de continuidad. "Documentacion minima", "solo digest", "rapida" o "para evitar contradicciones" son excepciones falsas y no sustituyen el cierre posterior. No hay excepciones documentales antes de desbloquear HA; despues del aviso hay que completar continuidad real con estado, version, digest, validaciones y pendientes mientras el usuario instala/prueba.

Actualizacion operativa 2026-06-28: por las restricciones del sandbox de Codex, `git commit` puede requerir escritura elevada en `.git` y `git push`/GHCR requieren red. Cuando el usuario pida explicitamente subir a Git o publicar una version HA, primero se revisa estado/diff y se ejecutan las validaciones necesarias; despues se usan directamente permisos elevados para `git commit`, `git push`, build/push GHCR o comandos de red necesarios, evitando intentos previos que ya se sabe que fallaran por sandbox.

### Ficheros afectados
- `scripts/build-push-ha-image.sh`
- `.github/workflows/build-rainmapper-app.yml`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/decisions.md`

### Estado
Implementado en `0.2.60`: Home Assistant instalo la imagen publicada localmente desde GHCR sin build local segun validacion manual del usuario; pendiente de confirmacion automatizada. Modificado despues de validar `0.2.60` para anadir limpieza local de etiquetas antiguas al script de publicacion.

## 2026-06-17 - Exponer fuente de estacion en GeoJSON y filtros del visor

### Decision
Anadir propiedad `Source` a los GeoJSON generados e incorporar en MapLibre Settings un filtro por fuentes Meteocat, Meteoclimatic y Wunderground, junto al filtro existente de lluvia minima.

### Motivo
La futura app iOS/Android necesitara filtros de estaciones sin depender de logica duplicada en cada cliente. Los CSV `Tomap` actuales no traen una columna de origen, pero los codigos reales permiten una inferencia razonablemente conservadora sin tocar historicos: Meteoclimatic empieza por `ES` y tiene longitud larga, aproximada como minimo 15 caracteres; Wunderground empieza por `I`; Meteocat se limita a codigos de longitud 2. Cualquier otro codigo queda como `Unknown` y se avisa en stdout al convertir GeoJSON.

### Alternativas consideradas
Filtrar solo en el cliente por patrones de codigo, o modificar el pipeline principal `Rainmapper.py` para anadir origen a los historicos.

### Consecuencias
Los visores pueden usar `Source` directamente y el cliente futuro tendra un contrato de datos mas claro. La inferencia sigue acoplada al formato actual de codigos; si una fuente cambia su nomenclatura, habra que ajustar `tomap_to_geojson.py` y sus tests. No se modifica el historico CSV. `Unknown` se mantiene visible como filtro separado en MapLibre para no ocultar datos inesperados.

### Ficheros afectados
- `rainmapper_core/geojson.py`
- `rainmapper_core/viewers/maplibre-viewer/`
- `tests/test_tomap_to_geojson.py`

### Estado
Implementada en `0.2.58`; modificada en `0.2.59` para clasificar Meteocat solo con codigos de longitud 2 y avisar por `Unknown`. La inferencia esta cubierta por `tests/test_tomap_to_geojson.py`; la validacion visual en Home Assistant/iPhone fue reportada por el usuario y queda pendiente de automatizar.

## 2026-06-22 - Cerrar exposicion publica manteniendo actualizaciones HA

### Decision
Hacer privado el repo GitHub `cginebrosa/RainmapperHA`, mantener accesible el paquete GHCR necesario para Home Assistant, proteger los fallbacks externos con Cloudflare Access y endurecer el dominio con redireccion HTTPS y HSTS.

### Motivo
Antes de compartir el visor con companeros, se reviso el riesgo de exposicion. El repo publico permitia ver codigo, rutas y logica de descarga, incluyendo Wunderground. Ademas, antes de proteger el fallback externo, `https://maplibre.nomentero.com/local/rainmapper-maplibre/data/01d.geojson` devolvia `200` con GeoJSON sin login. Para uso privado y pruebas con terceros, la UI principal debe ir por login Rainmapper y los fallbacks no deben saltarse la autenticacion.

### Alternativas consideradas
Dejar el repo publico, borrar el fallback externo, hacer privado tambien GHCR, o retirar todos los subdominios fallback del tunel Cloudflared. Se descarta hacer privado GHCR por ahora porque Home Assistant descarga `ghcr.io/cginebrosa/rainmapperha:<version>` sin autenticacion de registry. Se descarta retirar los fallbacks porque el usuario quiere conservarlos como emergencia si falla la ruta principal.

### Consecuencias
El codigo deja de estar disponible publicamente y un tercero no puede anadir facilmente el repo como add-on repository en Home Assistant. Home Assistant puede seguir descargando la imagen versionada mientras GHCR siga accesible. Los fallbacks `leaflet.nomentero.com` y `maplibre.nomentero.com` siguen existiendo, pero requieren Cloudflare Access, igual que `router.nomentero.com`. HSTS con `includeSubDomains` obliga a que los subdominios actuales y futuros del dominio sigan funcionando por HTTPS. Si se quiere hacer privado GHCR en el futuro, habra que resolver autenticacion de registry desde HA o aceptar publicar temporalmente cada version.

### Verificaciones
- HTTP redirige a HTTPS para `rainmap.nomentero.com` y subdominios revisados.
- HSTS activo con `strict-transport-security: max-age=2592000; includeSubDomains`.
- `x-content-type-options: nosniff` presente.
- `router.nomentero.com` redirige a Cloudflare Access.
- `leaflet.nomentero.com/local/rainmapper-leaflet/index.html` y `data/01d.geojson` redirigen a Cloudflare Access.
- `maplibre.nomentero.com/local/rainmapper-maplibre/index.html` y `data/01d.geojson` redirigen a Cloudflare Access.
- `rainmap.nomentero.com/protected/maplibre/data/01d.geojson` devuelve `401 Authentication required` sin sesion.
- El 2026-06-22, `ghcr.io/cginebrosa/rainmapperha:0.2.100` seguia resolviendo manifest multi-arch `linux/amd64` y `linux/arm64` despues de la limpieza.
- El 2026-06-24, tras validar `0.2.111`, GHCR se limpio de nuevo: quedaron `0.2.111`, `latest` y cuatro entradas auxiliares sin tag del mismo push multi-arch/attestation. `ghcr.io/cginebrosa/rainmapperha:0.2.111` resolvio como index OCI con `linux/amd64` y `linux/arm64`. El repo remoto se verifico como `private`.
- El 2026-06-24 se publico `ghcr.io/cginebrosa/rainmapperha:0.2.112` y `latest` con digest multi-arch `sha256:37f841c9004ab879227d2cc67ee6f836d1e8c4adc14ae609ba9b7cf41b3637f7`, verificado como index OCI con `linux/amd64` y `linux/arm64`; quedo superado por `0.2.113` antes de validarse en HA.
- El 2026-06-24 se publico `ghcr.io/cginebrosa/rainmapperha:0.2.113` y `latest` con digest multi-arch `sha256:b8bdf0a9b433932c4fc7af012cd7d0876ea6d821aa7131b5e81458031c831627`, verificado como index OCI con `linux/amd64` y `linux/arm64`, y despues quedo validado/dado por bueno en HA.

### GHCR
Se borraron 179 versiones/entradas antiguas del paquete `rainmapperha` en GHCR. En ese momento quedaron `0.2.100`, `latest` y cuatro entradas auxiliares sin tag asociadas al mismo push multi-arch. El 2026-06-24 se repitio la limpieza tras validar `0.2.111`: quedaron `0.2.111`, `latest` y cuatro entradas auxiliares sin tag asociadas al mismo push multi-arch/attestation. Ese mismo dia se publicaron `0.2.112` y `0.2.113`; tras validar `0.2.113` en HA, se limpio GHCR de nuevo y quedaron solo `0.2.113`, `latest` y cuatro entradas auxiliares sin tag del mismo push multi-arch/attestation.

Auditoria real del 2026-06-24 tras publicar `0.2.118`: GHCR conserva `0.2.118,latest` con digest multi-arch `sha256:07ce37c45de5f705aeb1621f4fb680a7b2c9360014ee1ccbb95322e7815d0e96` y `0.2.117` como rollback con digest multi-arch `sha256:e12749d4b16a48c362f731eb4f03dbb850b71988061602396c51293ad0350d65`; cada una conserva cuatro entradas auxiliares sin tag del push multi-arch/attestation. Para futuras releases HA, la limpieza remota de GHCR pasa a ser parte del procedimiento estandar despues de validar la nueva version en HA: conservar solo la version actual, `latest`, el rollback inmediato y las entradas auxiliares de esos pushes multi-arch. No borrar la version que declare `rainmapper-app/config.yaml` ni sus entradas auxiliares mientras HA pueda necesitar reinstalarla. Actualizacion 2026-06-25: `0.2.137` queda validada/dada por buena en HA con digest multi-arch `sha256:539c879d2c7f9dfc282d671b71c627a858b48d59778e3195ec2d0254accee928`; GHCR remoto queda limpio tras borrar las versiones/entradas antiguas de `0.2.134`, `0.2.135` y `0.2.136`, y conserva solo `0.2.137`, `latest` y cuatro auxiliares sin tag del mismo push multi-arch.

Actualizacion 2026-06-29: despues de publicar `0.2.178`, la limpieza remota GHCR debe usar explicitamente `GH_TOKEN` desde el entorno local. No usar `git credential fill`/osxkeychain para la API de Packages: puede devolver una credencial valida para Git pero insuficiente para listar/borrar package versions. Reintentado con `GH_TOKEN`, se borraron 205 package versions antiguas con 0 fallos y quedaron 10 entradas: `0.2.178/latest`, `0.2.177` como rollback inmediato y sus manifests auxiliares sin tag. Tras publicar `0.2.179`, se borraron las 5 entradas de `0.2.177` con 0 fallos y quedaron `0.2.179/latest`, `0.2.178` rollback y sus manifests auxiliares. Tras publicar `0.2.180`, se borraron las 5 entradas de `0.2.178` con 0 fallos y quedaron `0.2.180/latest`, `0.2.179` rollback y sus manifests auxiliares.

Procedimiento vigente para limpiar GHCR desde esta maquina: no depender de
`gh`, porque puede no estar instalado. Usar `curl` con `GH_TOKEN` ya presente en
el entorno local. Primero listar y auditar:

```bash
zsh -ic 'curl -fsSL \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/users/cginebrosa/packages/container/rainmapperha/versions?per_page=100" \
  -o /tmp/rainmapperha-ghcr-versions.json'

jq -r '.[] | [.id, (.metadata.container.tags|join(",")), .name, .created_at] | @tsv' \
  /tmp/rainmapperha-ghcr-versions.json
```

Conservar la version activa, el tag `latest`, el rollback inmediato y todas las
entradas sin tag asociadas a esos dos pushes multi-arch/attestation. Borrar solo
los IDs auditados como antiguos:

```bash
zsh -ic 'set -euo pipefail
ids=(ID_ANTIGUO_1 ID_ANTIGUO_2)
for id in $ids; do
  printf "Deleting GHCR package version %s\n" "$id"
  curl -fsSL -X DELETE \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer $GH_TOKEN" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/users/cginebrosa/packages/container/rainmapperha/versions/$id" \
    >/dev/null
done'
```

Despues de borrar, volver a listar y verificar manifests con
`docker buildx imagetools inspect` para la version activa, `latest` y el
rollback. El 2026-07-11, tras validar `0.2.195` en HA, se uso este metodo y
GHCR quedo con 10 entradas: `0.2.195/latest`, rollback `0.2.194` y sus
auxiliares multi-arch/attestation.

### Ficheros afectados
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/decisions.md`

### Estado
Completado operacionalmente el 2026-06-22 y revisado de nuevo el 2026-06-24. `0.2.113` quedo validado en HA y limpio en GHCR en su momento. Actualizacion 2026-06-25: `0.2.137` queda validada/dada por buena en HA; despues se puso el repo remoto en privado (`private=true`, `visibility=private`, rama `inicial`) y se limpio GHCR remoto conservando solo `0.2.137`, `latest` y cuatro auxiliares sin tag del mismo push multi-arch.

## 2026-06-26 - Capa MapLibre IDW calculada en cliente

### Decision
Anadir una capa experimental `IDW` en MapLibre para estimar un campo zonal de la metrica activa. La capa se calcula en el navegador solo para el viewport visible, se renderiza como `fill` GeoJSON con opacidad configurable y queda protegida por el permiso de usuario `can_use_estimated_field`.

### Motivo
El heatmap nativo de MapLibre usa densidad ponderada; por tanto, zonas con muchas estaciones pueden verse mas intensas que zonas con valores meteorologicos mayores pero menos estaciones. Para lluvia, temperatura, humedad y velocidad de viento se quiere una lectura aproximada de promedio espacial, no de concentracion de observaciones.

### Consecuencias
La Raspberry Pi no calcula la interpolacion; solo sirve el GeoJSON de estaciones y `config.js`. La carga pasa al dispositivo cliente y se limita al area visible. Los settings por dispositivo controlan activacion, opacidad, radio fisico, calidad, suavizado y correccion por altitud. Los parametros tecnicos de radios en km, radio fisico maximo, tamano fisico de celda en km, potencia IDW y gradiente termico viven en `rainmapper-app/config.yaml` para ajustar pruebas en HA sin publicar una nueva imagen. Las metricas ausentes/no numericas no participan en la interpolacion; las temperaturas negativas son valores validos. El viento se trata inicialmente como escalar, dejando una posible visualizacion vectorial con flechas para una fase posterior.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `rainmapper_core/viewers/maplibre-viewer/`
- `users.example.json`
- `tests/test_web_server_auth.py`

### Estado
Publicado inicialmente en imagen HA `0.2.138` con digest multi-arch `sha256:c16e87c8e86186e09dc04f77759ffe2c1f1cbf0fa97e6b5e015364d38530cd17`. `0.2.139` intento limitar el azul de lluvia cero, pero en HA siguio mostrando un comportamiento demasiado parecido y expuso problemas de sincronizacion entre botones `Heatmap`/`IDW`. `0.2.140` corrigio la incompatibilidad Heatmap/IDW, hizo que los botones rapidos no persistieran, mantuvo persistencia solo desde Settings, paso radio y tamano de celda IDW a km configurables (`maplibre_estimated_field_radius_*_km`, `maplibre_estimated_field_grid_*_cell_km`) y evito que lluvia cero generase area visible por si sola. `0.2.141` y `0.2.142` ajustaron el refresco visual del source/layer IDW. `0.2.143` movio IDW por encima de los circulos de estacion para que la opacidad pueda taparlos. `0.2.144` mostro en Settings los valores efectivos de radio, celda y potencia `p` procedentes de `config.yaml`. `0.2.145` optimizo el refresco IDW con cache por clave de calculo para evitar recalcados duplicados y reconstrucciones innecesarias al alternar capas o refrescar estilo.

La implementacion de `0.2.145` hace que `updateEstimatedFieldLayer()` evite recalcados duplicados con una clave de calculo que incluye periodo, revision de datos, metrica, escala, viewport, canvas, fuentes activas y parametros IDW; si la clave no cambia reutiliza el GeoJSON calculado. Tambien limita a uno los callbacks `idle` pendientes cuando el estilo MapLibre aun no esta listo y evita reconstruir la capa de estaciones al activar IDW. Esta pauta queda documentada en `docs/architecture.md` como patron para futuras capas calculadas en cliente, por ejemplo el predictor de floradas de setas.

## 2026-06-27 - Redisenar WebUI Users como accordion server-side

### Decision
Refactorizar la pagina Home Assistant `Users` a una lista compacta tipo accordion, generada desde helpers Python en `rainmapper-app/app/web_server.py`, sin introducir framework frontend ni build step. Mantener todos los contratos POST existentes y anadir salvaguardas de confirmacion para acciones sensibles.

### Motivo
La tabla original funcionaba, pero ocupaba demasiado espacio por usuario y era dificil de mantener cuando habia varios dispositivos. La WebUI vive dentro de Home Assistant/ingress, por lo que conviene conservar HTML/CSS/JS embebido y dependencias cero. Helpers Python pequenos dan suficiente estructura sin crear una arquitectura frontend separada.

### Consecuencias
Cada usuario se muestra como una fila compacta con resumen, permisos y ultimo dispositivo visto; solo un usuario queda expandido cada vez. La creacion pasa a modal. Las acciones `Save user`, `Set password`, `Reset password`, `Delete user`, `Delete device` y `Delete all devices` requieren confirmacion del navegador. `users.json` incorpora campos de auditoria `created_at`, `updated_at` y `last_change`; los timestamps siguen en formato UTC `...Z`, ahora generados con `datetime.now(UTC)` para evitar `datetime.utcnow()` deprecado. La UI debe validarse dentro de Home Assistant porque el espacio real depende del iframe/ingress.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `tests/test_web_server_auth.py`
- `docs/ui/user-management-redesign.md`
- `docs/ui/user-management-accordion-prototype.png`

### Estado
Publicado en imagen HA `0.2.146` con digest multi-arch `sha256:fefbc22459cd8e388f6660ac533293557f157a33e3a1f8dc1cb781359a6c8ca8` y commit `ab5b2dd`. Validacion local: `./scripts/smoke-test.sh` OK. Validada/dada por buena en HA el 2026-06-27.

## 2026-07-01 - Predictor de setas v0 con senales amplias y calibracion progresiva

### Decision
No deshacer el trabajo de catalogos, observaciones, GIS mappings, DEM ni
reconstructor, pero usar una v0 del predictor de setas con menos parametros y
mas alineada con la literatura fiable disponible. La v0 debe trabajar con
senales amplias de habitat: vegetacion/bosque asociado, arbol huesped cuando
aplique, suelo acido/siliceo, calcario/basico, arenoso, humedo, yesifero o
variable, altitud aproximada, temporada y rasgos simples de habitat.

Las capas GIS siguen siendo necesarias para clasificar cada punto del mapa en
esas caracteristicas internas. La meteorologia de los incrementales de
Rainmapper se combina despues con esa aptitud estatica para estimar si hay
condiciones recientes de fructificacion. La geologia fina queda como
trazabilidad o apoyo, no como eje del scoring inicial.

### Motivo
La literatura y guias de campo accesibles al usuario describen las especies en
terminos ecologicos amplios, no como dependencia de codigos geologicos
detallados. Intentar mapear miles de clases GIS finas antes de tener un modelo
simple validable aumenta mantenimiento sin aportar necesariamente poder
predictivo. Un modelo v0 pequeno permite explicar resultados, revisar errores y
usar observaciones reales para enriquecer solo lo que demuestre valor.

### Consecuencias
`mushroom_gis_mappings.json` puede conservar litologias y mappings detallados,
pero el batch masivo de geologia debe priorizar tendencias edaficas amplias,
por ejemplo mediante `geology_soil_tendency_mappings`.

Aclaracion posterior del 2026-07-02: la v0 no debe interpretarse como reinicio
en un JSON paralelo que sustituya el mantenimiento existente. `mushroom_profiles.json`
sigue siendo la entidad principal y la v0 se expresa como proyeccion operativa
de campos activos, iniciada en `rainmapper_core/mushroom_profile_v0.py` y
documentada en `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`.
La fuente estructurada revisada debe alimentar esos campos activos y catalogos
compartidos, no descartar el perfil rico ni la UI actual.

El schema rico y los campos ya existentes en `mushroom_profiles.json` quedan
como compatibilidad, UI rica aparcada y posible arquitectura futura, no como
contrato numerico de la v0. La v0 no se considera incompleta por no rellenar
cada parametro fino. La promocion de parametros adicionales solo debe ocurrir
cuando haya soporte documental o patrones locales reproducibles a partir de
observaciones y meteorologia historica.

Las observaciones reales no modifican automaticamente el modelo. Generan
candidatos o hipotesis reproducibles: ventanas de lluvia observadas, rangos
altitudinales locales, asociaciones de bosque/suelo o gaps de datos. Cada
candidato debe testearse en laboratorio y promocionarse manualmente si encaja
con datos y literatura disponible.

Actualizacion posterior del 2026-07-02: la UI de mantenimiento no se reinicia
ni se duplica en otra aplicacion. `/mushrooms/profiles` incorpora dos modos
sobre la misma estructura de datos: `Enriched`, que mantiene el editor completo
existente, y `V0`, que filtra la vista a los campos operativos de la v0 y oculta
campos aparcados. La vista `V0` es conservadora con la persistencia: no permite
guardar un formulario completo mientras haya campos ocultos para evitar
perdidas por POST parcial. La edicion completa, raw JSON e import/export quedan
en `Enriched`.

### Ficheros afectados
- `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`
- `docs/mushrooms/mushroom-predictor-design-es.md`
- `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`
- `rainmapper_core/mushroom_profile_v0.py`
- `mushroom-data/mushroom_gis_mappings.json`
- `rainmapper-app/app/mushroom_profiles_ui.py`
- `rainmapper-app/app/web_server.py`
- `scripts/validate-mushroom-data.py`

### Estado
Decision documentada localmente durante la fase de laboratorio GIS. No hay bump
de version HA ni publicacion de imagen asociada.

## 2026-07-02 - UX humana por defecto en pantallas de mantenimiento

### Decision
Las pantallas nuevas de mantenimiento deben ser coherentes con el look&feel
existente, usables por una persona y orientadas a decisiones claras. La UI no
debe exponer por defecto dumps tecnicos, tablas crudas interminables ni textos
que obliguen a interpretar estructuras internas si existe una forma razonable
de presentar metricas, estados, acciones y contexto humano.

Las vistas tecnicas crudas siguen permitidas, pero solo cuando el usuario lo
pida explicitamente o se acuerde como modo avanzado/laboratorio. En ese caso
deben quedar separadas del flujo principal y no sustituir a una pantalla de
mantenimiento entendible.

### Motivo
RainmapperHA se opera desde una UI local/HA para mantenimiento real, no solo
como inspeccion de artefactos JSON. En el predictor de setas, especialmente,
los flujos de evidencia, GIS mappings y perfiles v0 necesitan ayudar a decidir
que revisar, promover, ignorar o mantener, no obligar a leer payloads tecnicos.

### Consecuencias
- Cualquier nueva pestaña o pantalla debe empezar por resumen, estados y
  acciones claras.
- Los detalles tecnicos pueden existir como `details`, modo avanzado o descarga,
  pero no como experiencia primaria.
- Si una sesion Codex propone una UI tecnica cruda, debe pedir acuerdo explicito
  antes de implementarla.

## 2026-07-02 - UI multiidioma por defecto

### Decision
Las pantallas visibles de RainmapperHA deben tratarse como multiidioma por
defecto. En el dominio de setas, cualquier texto visible nuevo debe salir de
`mushroom-data/mushroom_labels.json` mediante los helpers de labels existentes
(`ui_label`, `value_label`, etc.) y debe incluir al menos `en`, `es` y `ca`.

Esto aplica tambien a estados, decisiones, acciones, cabeceras, tooltips,
mensajes de ayuda y textos de pestanyas. Los textos hardcoded en Python solo
son aceptables para identificadores tecnicos no visibles, tests internos o
mensajes temporales de desarrollo que no formen parte de la UI.

### Motivo
El add-on ya expone `ui_language` y la WebUI de setas se usa en varios idiomas.
Mezclar textos fijos con labels traducibles degrada la experiencia y hace que
las revisiones futuras sean mas caras, especialmente en pantallas de
mantenimiento donde estados y acciones deben ser claros.

### Consecuencias
- Cualquier feature nueva de UI debe anadir sus labels junto con el cambio.
- Los tests deben aceptar el idioma por defecto o verificar explicitamente el
  idioma que se este cargando.
- Si aparece un `missing label: ...` durante desarrollo, debe resolverse antes
  de cerrar la tarea salvo que sea una prueba deliberada de deteccion.

## 2026-07-02 - Mapa hibrido externo para revision de evidencia local

### Estado
REEMPLAZADA el 2026-07-13 para los mapas internos de observaciones, evidencia,
EXIF y setales. Google Maps se conserva solo como enlace externo auxiliar.

### Decision
La pestanya `Evidencia` de especies puede usar Google Maps embebido en modales
de revision para inspeccionar observaciones concretas que alimentan un ID GIS
observado. El mapa debe ser hibrido/satelite, con zoom, y cada observacion debe
poder abrirse tambien en la pantalla interna de Observaciones.

Esta decision aplica solo a la revision manual en navegador. No convierte
Google Maps en dependencia del motor de scoring ni del reconstructor GIS.

### Motivo
Para decidir si un host, bosque, suelo o habitat observado por GIS debe
promocionarse al perfil, el contexto visual del punto es mas util que un mapa
abstracto. Google Maps hibrido resuelve esa inspeccion con poca infraestructura
y sin redisenyar la UI de observaciones.

### Consecuencias
- Al abrir el modal, el navegador consulta Google Maps con la coordenada
  seleccionada.
- El artefacto `gis_observation_reconstruction.json` puede guardar `location`
  para que la revision sea autocontenida; la UI puede usar
  `mushroom_observations.json` como fallback si el artefacto es antiguo.
- Si se necesita revision offline o sin dependencia externa, se debera crear
  una alternativa MapLibre con tiles/ortofoto controlados.

## 2026-07-04 - Derivados de fecha persistidos en observaciones

### Decision
Las observaciones de setas pueden guardar un bloque `derived` con campos
baratos calculados desde `observed_at`. La version inicial persiste:

- `derived.month`: mes numerico `1-12`.
- `derived.season`: estacion simple `winter`, `spring`, `summer` o `autumn`.

Estos campos se calculan mediante una rutina comun antes de guardar una
observacion desde alta manual, edicion, duplicado/plantilla o importacion EXIF.
Las observaciones existentes se pueden migrar una vez con
`scripts/update-mushroom-observation-derived-fields.py`.

### Motivo
En HA interesa reducir trabajo repetido durante reconstrucciones del modelo v0.
El proyecto acepta esta desnormalizacion controlada porque tenemos mas margen
de disco que de CPU. `observed_at` sigue siendo la fuente canonica y los campos
derivados son regenerables.

### Consecuencias
- Los rebuilds pueden leer `month` y `season` ya persistidos, con fallback a
  calculo en memoria para artefactos antiguos.
- El validador permite `derived` y comprueba que `month` y `season` tengan
  valores validos si existen.
- La estacion simple no sustituye a `phenology.main_months`,
  `secondary_months` ni `season_pattern_ids`; solo describe la fecha concreta
  de una observacion.

## 2026-07-04 - Guardado comun de perfiles y contexto de campo ampliado

### Decision
El guardado de perfiles de especie debe pasar por una normalizacion comun antes
de persistir. En esta fase se centraliza solo metadata de guardado
(`metadata.updated_at`, `metadata.updated_by`) para los caminos de formulario
completo, JSON raw, parametros y calibracion. No se recalculan parametros ni se
promociona evidencia automaticamente.

Las observaciones de campo pueden declarar, ademas de arboles observados:

- `site_context.observed_forest_type_ids`
- `site_context.observed_soil_tendency_ids`
- `site_context.observed_habitat_feature_ids`
- `site_context.observed_aspect_ids`

Estos valores son opcionales, catalogados y representan lo que declara el
observador. El joiner v0 los marca como fuente `field`; GIS/DEM sigue marcado
como fuente `gis`.

### Motivo
La UI y el modelo comparativo necesitan los tres puntos de vista: parametros de
la especie, evidencia declarada por observador y evidencia GIS/DEM. Sin bosque,
suelo, habitat y orientacion en la observacion, parte de esa evidencia nunca
podria ser observacional.

### Consecuencias
- `Enriched` debe ir siempre con `view=enriched` en URL; como `V0` es default,
  omitir `view` ya no significa enriched.
- Guardar desde cualquier subflujo de perfil preserva la vista activa.
- Las observaciones enriquecidas no modifican perfiles; solo alimentan features
  v0 y modelo aprendido descriptivo.

## 2026-07-05 - Capas GIS pesadas fuera de share en HA

### Decision
En Home Assistant, las capas GIS/DEM pesadas usadas para reconstruir contexto de
observaciones de setas deben vivir en:

```text
/media/rainmapper/mushroom-GIS/
```

El add-on declara acceso a `media`. El resolver GIS respeta primero
`RAINMAPPER_MUSHROOM_GIS_ROOT` si se fuerza explicitamente; sin override, busca
`/media/rainmapper/mushroom-GIS/` antes que otras copias locales/controladas.

### Motivo
`/share` entra como unidad completa en backups de Home Assistant y del add-on de
Google Drive Backup. Mantener 5-6 GB de capas GIS bajo `/share` infla backups,
puede agotar cuota remota y no aporta valor porque esas capas son copiables y
no son datos vivos editados por la UI.

### Consecuencias
- `/share/rainmapper` queda para historicos meteorologicos, datos operativos,
  JSON de setas y artefactos v0.
- `/media/rainmapper/mushroom-GIS` queda para capas pesadas no versionadas.
- Los backups de HA pueden incluir `share` sin arrastrar las capas GIS, siempre
  que no quede una copia residual en `/share/rainmapper/mushroom-GIS`.

## 2026-07-08 - Publicacion publica legacy controlada por `publish_to_www`

### Estado
VIGENTE.

### Decision
`publish_to_www` pasa a ser el unico interruptor para salidas publicas legacy:

- Bokeh/Google Maps HTML en `Plots`.
- Copia publica de Bokeh en `/config/www/Plots` y acceso `/local/Plots`.
- Leaflet publico en `/config/www/rainmapper-leaflet`.
- Heatmap/MapLibre publico experimental antiguo.

El valor por defecto es `false`. Con `false`, Rainmapper sigue reconstruyendo
Tomap y GeoJSON en `PublicData`, y el visor operativo recomendado sigue siendo
MapLibre protegido en `/protected/maplibre/index.html` con datos desde
`/protected/maplibre/data/*`. No existe un parametro separado
`generate_bokeh_maps`.

### Motivo
Las salidas publicas Bokeh/Leaflet/heatmap eran transicion/compatibilidad. Ya no
son necesarias para el uso normal y anadian tiempo al `run_all`, superficie de
exposicion publica y complejidad de configuracion.

### Consecuencias
- Las carpetas antiguas de `/config/www` pueden eliminarse; si se reactiva
  `publish_to_www=true`, las salidas legacy se regeneran.
- La limpieza es tolerante: no es problema que
  `/config/www/rainmapper-mobile` o `/config/www/rainmapper-maplibre-aemet` no
  existan.
- El visor protegido no debe depender de `/config/www`; consume `PublicData`
  mediante rutas protegidas.

## 2026-07-13 - Setales como jerarquia espacial propia del predictor

### Estado
VIGENTE.

### Decision
Los setales se modelan en un store propio, separado de reference catalogs, con
dos niveles: area y microarea. Ambos niveles pueden tener geometria poligonal y
contexto GIS/DEM propio. Las observaciones guardan solamente `micro_area_id`;
el area superior se resuelve desde el store y no se duplica.

La primera fase predictiva se limita a setales conocidos. Areas y microareas
son entidades del predictor, no una copia de campos observados. Sus valores
GIS/DEM mantienen procedencia y no sobrescriben observaciones de campo.

### Motivo
Una zona general como Olvan agrupa microareas ecologicamente diferentes. El
modelo necesita poder aprender tanto contexto de area como diferencias de
microarea, y necesita separar la prediccion en lugares conocidos de una futura
busqueda de nuevos setales.

### Consecuencias
- `mushroom_known_sites.json` tiene ciclo de vida, backups y validacion propios.
- No se puede archivar ni borrar un area/microarea referenciada.
- Aplicar una propuesta GIS/DEM modifica el formulario, pero solo `Guardar`
  persiste el cambio.
- Descubrir nuevos setales queda fuera de la primera fase ML.

## 2026-07-13 - Un unico MapLibre reutilizable para observaciones y setales

### Estado
VIGENTE. Reemplaza para estos flujos internos la decision del 2026-07-02 de
usar un mapa Google embebido como visor principal de revision.

### Decision
El mapa interno de observaciones, evidencia, preview EXIF y mantenimiento de
setales debe reutilizar el mismo nucleo MapLibre y variar su comportamiento
segun el contexto de llamada. Debe conservar una pila de retorno para cerrar un
modal o mantenimiento exactamente donde se abrio: formulario con borrador,
fila seleccionada, filtros, orden y posicion de scroll.

El mapa muestra areas/microareas visibles, permite asignarlas y, cuando el
contexto lo autoriza, crear o editar geometria. En modo geometrico se desactivan
popups que puedan interceptar los clics. En modo normal, un solo popup combina
observacion, area y microarea.

### Motivo
Duplicar mapas y modales produjo comportamientos divergentes, perdida de
contexto y mas codigo que mantener. El flujo habitual parte de una observacion
o foto EXIF, por lo que definir/asignar el setal debe poder hacerse sin salir de
ese trabajo.

### Consecuencias
- Satellite+ es la base inicial; se conservan Topografico, Hybrid, 3D, capas y
  brujula.
- El boton `Mapa` usa las coordenadas actuales del borrador, incluso antes de
  guardar una observacion nueva o duplicada.
- La seleccion manual de coordenadas consulta tambien altitud DEM y requiere
  confirmacion.
- Google Maps queda como enlace externo auxiliar, no como componente interno
  principal de estos flujos.

## 2026-07-13 - Una imagen asociada por observacion

### Estado
VIGENTE.

### Decision
Mientras no exista un caso de uso validado para multiples fotos, cada
observacion puede tener como maximo una imagen asociada. Sustituirla exige
comparar imagen existente y nueva, revisar sus EXIF y decidir explicitamente si
la anterior solo se desasocia o tambien se borra.

El borrado de fichero solo se ofrece cuando ninguna otra observacion lo
referencia. Desasociar y borrar son acciones irreversibles con modal de
confirmacion claro.

### Motivo
Varias imagenes con fechas o coordenadas distintas vuelven ambiguo que dato
representa la observacion y complican el flujo EXIF. Tambien era facil heredar
por error la foto de una observacion al duplicarla.

### Consecuencias
- El preview EXIF debe mostrar imagen existente y nueva como opciones
  seleccionables, con datos/mapa de la activa.
- `Aplicar datos EXIF` solo esta habilitado para la imagen nueva.
- La precision original se conserva en JSON; los redondeos son solo de UI.

## 2026-08-04 - Artefacto weather_daily.parquet como fuente canónica de datos meteorológicos para el predictor

### Estado
IMPLEMENTADO PARCIALMENTE (0.2.221). La caché con invalidación por mtime se
añadió en 0.2.22x, pero el OOM del Predictor no está resuelto: el parquet evita
leer varios CSV y compartir una copia por especie, pero el histórico completo
sigue expandiéndose a objetos Python y queda retenido en memoria.

### Decisión
El runner generará al final de cada actualización un único fichero
`weather_daily.parquet` combinando las cuatro fuentes meteorológicas
(Meteocat/XEMA, Meteoclimatic, Wunderground, AEMET). Este fichero sustituye
la lectura directa de los CSV incrementales en el predictor y en la generación
de artefactos de features ML.

Columnas del Parquet:
- `Codi Estació`, `source`, `Data Local`
- `Latitud`, `Longitud`, `Altitud`
- `Total` (precipitación mm)
- `max_temp_celsius`, `min_temp_celsius`
- `max_humidity_percent`, `min_humidity_percent`
- `wind_avg_kmh`, `wind_gust_kmh`

Los CSV incrementales siguen siendo la fuente de verdad histórica y no se
eliminan. El Parquet es un artefacto de lectura generado a partir de ellos.

### Motivo
Los cuatro CSV incrementales suman ~116 MB. `load_daily_weather_stations()`
los carga enteros en memoria para cada predicción aunque solo se necesite una
fracción de los datos. Con 7+ especies entrenadas, esto multiplicaba la carga
por el número de instancias de `MushroomMLPredictor` activas, causando OOM en
la RPi.

Parquet intentaba resolver dos problemas a la vez:
1. **Tamaño**: compresión columnar reduce ~116 MB de CSV a ~15-20 MB.
2. **Fuente única**: un solo fichero consolidado elimina la necesidad de leer
   y mergear 4 CSV en cada acceso.

La caché compartida a nivel de módulo (`_shared_weather_stations`) evita una
copia completa por especie, pero no es una solución válida para la RPi4 mientras
retenga las 622k filas expandidas. Debe sustituirse por lecturas filtradas y una
caché de ventanas acotada.

### Detalles de implementación a tener en cuenta
- **AEMET usa coma decimal** en `Latitud`/`Longitud` en su CSV
  (`"40,95806"`). La normalización ocurre en el runner al generar el Parquet;
  los consumidores reciben floats limpios y no necesitan saber esto.
- **Meteocat no tiene** `wind_min_kmh` ni `wind_max_kmh`. Esas columnas
  quedan como `NaN` para las filas de Meteocat; no se añaden al Parquet
  (no están en la lista de columnas seleccionadas).
- El Parquet se regenera entero en cada run — no hay append incremental.
  Es correcto: Parquet no está diseñado para append row a row.
- La columna `source` (`meteocat`, `meteoclimatic`, `wunderground`, `aemet`)
  permite filtrar por fuente sin joins adicionales.

### Ficheros afectados
- `rainmapper_core/rainmapper.py` — añadir paso de generación de Parquet al
  final del runner
- `rainmapper_core/mushroom_observation_context.py` — nueva función
  `load_daily_weather_parquet(data_dir)` que lee el Parquet; modificar
  `load_daily_weather_stations()` para usarla como fuente si el Parquet existe
- `rainmapper_core/mushroom_ml_predictor.py` — el caché compartido
  `_shared_weather_stations` sigue igual, solo cambia de dónde carga los datos

### Consecuencias
- La primera apertura lee un fichero comprimido pequeño, pero eso no limita la
  RAM: el loader expande todo el histórico a objetos Python.
- La generación de artefactos de features también se beneficia.
- Si el Parquet no existe (primera instalación o datos corruptos), fallback
  a los CSV para no romper el sistema.
- El worker de ML no se ve afectado: recibe las features ya calculadas.
- **Caché con invalidación por mtime** (añadido 2026-08-06): `_get_shared_weather_stations()`
  compara el `st_mtime` del parquet en cada petición al predictor. Si el runner
  ha regenerado el fichero desde la última carga, la caché se invalida
  automáticamente y se recarga. Sin este mecanismo, un proceso HA sin reiniciar
  durante semanas podría mostrar datos meteorológicos obsoletos en el predictor.

### Revisión 2026-08-06: incidente P0 de memoria

La afirmación anterior de que la apertura cargaba solo ~15-20 MB confundía el
tamaño comprimido en disco con la representación expandida en memoria.

Medición sobre la copia local fresca de HA:

- parquet de 3,5 MiB, 622.069 filas y un row group;
- 1.948 estaciones y 622.033 `DailyWeatherRecord` construidos;
- `ru_maxrss` de 95.731.712 a 929.153.024 bytes: incremento aproximado de
  795 MiB;
- unos 247 MiB de asignaciones Python todavía trazadas después de `gc`, sin
  incluir toda la memoria nativa ni la retenida por allocators.

Además, la carga fría no está serializada bajo `ThreadingHTTPServer` y las
instancias ya inicializadas pueden conservar referencias al histórico anterior
después de cambiar el parquet.

Decisión pendiente de implementación: separar el catálogo ligero de estaciones
del histórico y usar chunks de caché de 120 días filtrados por las estaciones
necesarias, manteniendo las features del modelo en 30 días. Recomendador/Por
especie reutilizan el contexto actual; Consulta por fecha carga un contexto
anclado solo cuando no haya cobertura; volver a las vistas actuales reactiva su
contexto. Historial/backtest agrupa ventanas por episodio. La LRU será pequeña e
invalidada por fingerprint. El fallback web a CSV debe fallar de forma acotada
en lugar de cargar el histórico completo. Diseño y validación detallados en
`docs/mushrooms/mushroom-predictor-design-es.md`, sección 0.

Hasta validar el arreglo en una imagen arm64 y en RPi4, no abrir Predictor de
forma remota ni considerar 0.2.221/0.2.225 como solución completa del OOM.

## 2026-07-13 - Pipeline ML posterior a estabilizar observaciones y setales

### Estado
VIGENTE.

### Decision
El modelo v0 actual sigue siendo descriptivo. El primer entrenamiento ML sera
un experimento por una especie con suficiente muestra, construido a partir de
episodios por especie, microarea y fecha, meteorologia diaria auditable y
validacion agrupada sin fuga. No se fabricaran negativos ni se fijaran ventanas
o umbrales por intuicion.

### Duda abierta
DUDA.

Todavia debe decidirse con datos reales si la unidad final de prediccion sera
microarea, area o una combinacion jerarquica de ambas. La geometria y el store
se han preparado para poder comparar esas alternativas sin redisenarlos.

## 2026-07-15 - Entrega de video privado compatible con Safari e ingress HA

### Estado
VIGENTE.

### Decision
La ruta privada de media de observaciones debe admitir `HEAD` y peticiones HTTP
`Range` de un solo intervalo. Una respuesta parcial valida usa `206`,
`Accept-Ranges: bytes`, `Content-Range` y la longitud exacta del fragmento; un
rango invalido o no satisfacible devuelve `416`. El visor declara explicitamente
`video/mp4`, `playsinline` y el poster JPEG.

FFmpeg y ExifTool son dependencias ejecutables del sistema instaladas en
`rainmapper-app/Dockerfile`. No se incorporan a `requirements.txt`, reservado
para paquetes Python importables.

### Motivo
Safari, especialmente a traves del ingress de Home Assistant, necesita entrega
parcial para iniciar y desplazar la reproduccion de MP4. El archivo normalizado
ya tiene tamano y codec adecuados; recomprimirlo mas no resuelve el contrato
HTTP.

### Consecuencias
- Los GET completos siguen devolviendo `200`; los parciales devuelven `206`.
- El soporte actual no acepta rangos multiples en una misma cabecera.
- La validacion local no sustituye la prueba real tras proxies de HA.
- Cambiar dependencias multimedia exige revisar el Dockerfile y ambas
  arquitecturas, no anadir nombres de binarios a `requirements.txt`.

## 2026-08-08 - Ciclo de vida recuperable de observaciones y media

### Estado
VIGENTE.

### Decision
Archivar una observacion conserva toda su media. Borrar definitivamente una
observacion o una imagen registra primero los paths candidatos en
`maintenance/observation_media_cleanup_queue.json`, guarda el cambio de datos y
despues vuelve a contar referencias entre observaciones activas y archivadas.
Un fichero solo se elimina cuando el contador es cero. Si `unlink` falla, el
trabajo permanece en la cola y se reintenta al arrancar Rainmapper o al ejecutar
otra accion de mantenimiento de perfiles.

Las mutaciones de perfiles y observaciones se serializan dentro del proceso web.
El movimiento activa -> archivada escribe primero la copia archivada; la
restauracion escribe primero la copia activa. Los errores controlados restauran
el fichero ya escrito. Ante un corte no recuperable se prefiere una posible
duplicacion a perder la unica copia de una observacion.

### Motivo
La auditoria del 2026-08-08 encontro 141 fotos sin referencia (558,1 MiB). El
borrado anterior a 2026-08-02 no limpiaba media y la primera correccion no tenia
reintento tras fallos parciales. La cola hace visible y recuperable esa ventana
sin poner en riesgo archivos compartidos.

### Validacion
- 486 tests unitarios OK.
- `tests.test_web_server_auth`: 177 tests OK.
- `./scripts/smoke-test.sh` OK.
- Cobertura nueva de media fisica, referencias compartidas, fallo/reintento de
  borrado y rollback de los dos stores.

## 2026-08-08 - Acotar artefactos reconstruibles de Docker Desktop

Estado: VIGENTE

- `build-push-ha-image.sh` conserva localmente solo el tag HA versionado más
  reciente y `latest`; los rollbacks se conservan en GHCR, no duplicados en el
  Mac.
- Tras cada publicación, la parte privada/reclamable de la caché Buildx se acota
  a 8 GiB mediante `docker buildx prune --max-used-space`. Docker puede mostrar
  además capas compartidas con imágenes conservadas. No se eliminan imágenes en
  uso, contenedores ni volúmenes; el coste de una capa eliminada es solo
  reconstruirla o descargarla de nuevo.
- `docker-offline-functional-test.sh` elimina al terminar su imagen temporal
  `rainmapperha:test`, salvo opt-in explícito con
  `KEEP_DOCKER_TEST_IMAGE=1`.
- La limpieza nunca toca `rainmapper-worker-data`, el worker activo ni
  `rainmapperha:local-ha-ui`, porque contienen estado o sirven al laboratorio
  local.

Resultado de la limpieza inicial, 2026-08-08:

- GHCR pasó de 75 a 10 entradas. Se conservaron `0.2.229`, instalada en HA como
  rollback operativo, y `0.2.231/latest`, pendiente de instalar, junto con los
  cuatro manifests auxiliares de cada índice. Los dos índices se verificaron con
  plataformas `linux/amd64` y `linux/arm64`.
- Docker local eliminó `rainmapperha:test` (imagen temporal de 13,5 GB),
  `ghcr.io/cginebrosa/rainmapperha:0.2.230` y
  `rainmapper-worker:0.2.225`. La primera procedía de una prueba offline cuyo
  `trap` solo eliminaba el directorio temporal, no la imagen construida.
- La caché Buildx pasó de 29,43 GB reclamables a 7,271 GB privados/reclamables.
  Docker informa además 4,913 GB compartidos con las imágenes conservadas; no
  son una segunda ocupación exclusiva de la caché.
- Se conservaron y verificaron el worker activo y healthy, el volumen
  `rainmapper-worker-data` de 11,11 GB, `rainmapper-worker:0.2.228-arm64/local`,
  `rainmapperha:local-ha-ui` y `ghcr.io/cginebrosa/rainmapperha:0.2.231/latest`.
## 2026-08-08 - Transporte Parquet y retencion acotada de bundles del worker

Estado: IMPLEMENTADO Y PUBLICADO EN HA `0.2.233`; WORKER `1.0.0` CONSTRUIDO Y
VALIDADO LOCALMENTE.

Decision:

- Los CSV incrementales meteorologicos siguen siendo la fuente autoritativa de
  descarga y actualizacion. No se cambia ese pipeline.
- Los snapshots de reconstruccion enviados por HA al worker prefieren el
  artefacto derivado `weather_daily.parquet`. Solo incluyen los cuatro CSV como
  fallback cuando el Parquet aun no existe.
- El protocolo del worker continua siendo dirigido por manifest y no cambia su
  esquema. La release HA y la imagen worker mantienen versiones independientes;
  HA `0.2.232` convivio con worker `0.2.228`.
- La imagen worker `0.2.228` contiene el lector Parquet en el codigo, pero no el
  motor `pyarrow`. La siguiente imagen worker debe instalar `pyarrow==25.0.0`.
  Es una dependencia de runtime, no una modificacion del protocolo.
- El registro persistente del job es el historial. El bundle privado de entrada
  se elimina tras una prueba de transporte terminal, un fallo/cancelacion o una
  promocion correcta. Se conserva mientras un candidato completo siga pendiente
  de promocion o descarte.
- Antes de encolar cualquier trabajo externo, el coordinador reconcilia bundles
  terminales, resultados ya promocionados, staging abandonado y bundles
  huerfanos antiguos. No depende del reinicio del add-on. Si encuentra restos,
  limpiezas remotas pendientes o errores, lo añade al mensaje visible del
  lanzamiento; la reparacion nunca es silenciosa.
- El historial conserva los 50 jobs mas recientes. Descartar o limpiar cambia
  su estado persistente, pero no elimina la fila. La UI carga los 50 dentro de
  una tabla con cabecera fija y altura aproximada de 10 filas.
- Tras recibir el acuse `finish` de HA, el worker elimina su directorio privado
  del job y confirma esa limpieza en el heartbeat siguiente. HA puede volver a
  solicitar la limpieza de jobs terminales antiguos sin tocar la cache GIS/DEM.
- Un resultado privado promocionado en HA se elimina despues de persistir el
  resultado de promocion; solo se aceptan borrados con receipt coincidente. Los
  candidatos pendientes y los dos backups de rollback se conservan.
- Las versiones son independientes. La siguiente imagen worker inicia la serie
  propia `1.0.0`, fijada como valor predeterminado de su Dockerfile; HA no debe
  inferir compatibilidad por similitud numerica. El
  heartbeat anuncia `weather_parquet_v1` y `terminal_job_cleanup_v1`; un worker
  sin la primera capacidad recibe automaticamente el snapshot CSV compatible.

Motivo:

- En HA los cuatro CSV copiados por cada reconstruccion ocupaban aproximadamente
  113--116 MB, frente a unos 12 MB del Parquet ya generado por el runner. Ademas,
  conservar una copia por job habia acumulado unos 2,8 GB sin aportar historial
  adicional al JSON de la cola.

Consecuencias:

- El transporte habitual baja alrededor de un 89 % sin migrar el almacenamiento
  autoritativo ni el proceso incremental.
- La compatibilidad CSV queda disponible para instalaciones y workers antiguos.
- La limpieza posterior a fallos se recupera en el siguiente lanzamiento a un
  worker y queda anunciada al usuario.

Validacion local:

- `./scripts/smoke-test.sh`: OK, 511 tests unitarios mas validadores de sintaxis,
  empaquetado HA, GeoJSON, historicos y backups.
- Worker M1 `rainmapper-worker:1.0.0` construido y arrancado healthy; anuncia
  `weather_parquet_v1` y `terminal_job_cleanup_v1`. Se retiraron sus tags locales
  legados `local` y `0.2.228-arm64` sin tocar el volumen persistente GIS/DEM.
- HA `0.2.233` publicada para `linux/amd64` y `linux/arm64` con digest
  `sha256:8289ee5bc28983f238a0b7fcc0718f6ad8d40492629699b52157cb3d9e9013c9`;
  pendiente de instalación y validación en la RPi4.
# 2026-08-09 - Predictor remoto con selección informada y diagnóstico en HA

- `MushroomMLPredictor` permanece como motor único en `rainmapper_core`.
- Se añade una fachada sin HTML compartida por HA y worker; no se duplica la
  inferencia en la aplicación ni se ejecuta Python en el navegador.
- HA es la autoridad de selección, progreso, resultados y caja negra. El worker
  solo sincroniza un runtime inmutable, calcula y devuelve telemetría.
- La entrada al Predictor presenta Auto/Manual. Auto recomienda el ejecutor
  compatible y libre con menor tiempo típico comparable; también se muestran
  última/típica fría y caliente y número de muestras.
- La comunicación continúa siendo saliente y autenticada desde el worker. El
  navegador no conoce credenciales ni endpoints privados del worker.
- Las versiones de HA y worker son independientes; la compatibilidad se negocia
  por capacidad y contratos (`predictor_v1`, features y formato de modelo).
- Diseño completo: `docs/mushrooms/mushroom-remote-predictor-design-es.md`.
- Implementación inicial: contratos 1.0, runtime SHA-256 incremental, capacidad
  `predictor_v1`, trabajo interactivo, selección Auto/Manual, progreso y
  estadísticas autoritativas en HA. Publicada en HA `0.2.234` sin alinear las
  versiones independientes de HA y worker.
- Prueba local real: M1 frío 2,5944 s con 15.808.259 bytes sincronizados; segunda
  ejecución 0,2505 s, caché reutilizada y cero bytes transferidos. HA conservó y
  renderizó ambos resultados.
- La entrada del panel se resuelve en un modal que conserva el enlace directo
  como fallback, transforma la selección en progreso y navega al Predictor solo
  cuando la respuesta está lista. El refresco periódico del panel no destruye el
  modal ni el trabajo en curso.
- La elección del ejecutor forma parte de la sesión de navegación del Predictor:
  pestañas y formularios la conservan, y sus esperas también usan el modal. Solo
  se vuelve a elegir por petición expresa o cuando el ejecutor deja de estar
  disponible; en ese caso HA refresca los candidatos antes de mostrarlos.
- `worker_predictor_v1` es un trabajo interactivo y se etiqueta como tal en el
  historial de workers. No representa una reconstrucción ni una promoción del
  modelo, aunque use la misma infraestructura de cola y transporte.
- La futura publicación del Predictor adopta una política server-side de dos
  capacidades: selección manual de ejecutor y permiso para ejecutar en HA. Las
  dos están fijadas ahora a `True` mediante constantes internas porque el panel
  privado de HA no proporciona una identidad Rainmapper; no son opciones del
  add-on y todavía no existe una regla activa por rol. Todo el flujo consume
  `PredictorExecutionPolicy`, por lo que una integración autenticada futura solo
  tendrá que obtener esos dos valores del rol o del usuario. El objetivo previsto
  para usuarios no administrativos es Auto + worker-only, sin fallback silencioso
  a la RPi: si no hay worker compatible y libre, el Predictor se declarará
  temporalmente no disponible.
- Evolución aprobada para una fase posterior: ofrecer el Predictor como feature
  autorizable desde MapLibre, manteniendo HA como único gateway y a los workers
  sin exposición entrante. Ver límites de permisos, privacidad, capacidad y
  caché en el documento de diseño.
- HA `0.2.234` publicada para `linux/amd64` y `linux/arm64`, tag de versión y
  `latest` con digest
  `sha256:431338d23b568ffb3671768766075aae52e2326b6d90a64ecf0aafc10af71199`.
- Validación HA real: ejecución correcta tanto en HA como en M1, con 40,2 s
  habituales para HA (1 muestra) y 3,6 s para M1 (2 muestras); Auto recomienda
  M1 y mantiene HA como alternativa manual.
- Se difiere expresamente cualquier cambio de topología de red. En una fase
  posterior se diseñará una URL de coordinador anunciada y agnóstica de LAN,
  VPN o proxy, entregada durante el emparejamiento y separada del perfil de lab.
  Hasta entonces el puerto privado `8100` es estable: cambiar su publicación
  requiere reconfigurar los workers existentes.
- La duración comparable se denomina **Operational duration** y conserva
  `wall_seconds`; no incluye las muestras posteriores. El Gantt separa esa cifra
  de **Diagnostic window (includes recovery samples)**. Los segundos se
  presentan como `m:ss` a partir de un minuto, conservando décimas donde el dato
  las tiene, sin migrar ni redondear los JSONL autoritativos.
- Recent history mantiene 20 ejecuciones pero limita el viewport a 10 filas con
  cabecera fija y scroll. Version averages usa la jerarquía Type → carga
  comparable → versiones, porque la comparación primaria debe ser entre la
  misma operación/carga en distintas releases; `Runner · all` se abre por
  defecto y el estado de los acordeones sobrevive al refresco del panel.
- Esta presentación se publica en HA `0.2.235`. Los tags `0.2.235` y `latest`
  comparten el digest multi-arquitectura
  `sha256:1489ab946820d780d8c810c21d02e051427a3cb2cd7e6835574bb71f824598ff`,
  verificado con manifests `linux/amd64` y `linux/arm64`. Queda pendiente su
  instalación y validación visual en la RPi4.
- Validación real posterior: el job remoto de `0.2.235` guardó correctamente
  `cold: true`, runtime sincronizado, 12.630.650 bytes y 5,8632 s de backend,
  pero el resumen diagnóstico omitió esos campos y lo agrupó como `warm` por
  defecto. La corrección HA propaga al cierre del monitor el estado autoritativo
  del worker, incluso si el monitor se reconstruye; el contrato y la imagen
  worker `1.0.0` ya eran suficientes y no se versionan.
- HA `0.2.236` publica la corrección con 518 tests. Los tags `0.2.236` y
  `latest` comparten el digest multi-arquitectura
  `sha256:1f02a833721b793e366b6818db020a9a9d1dbcca174465c00f7d2b09c1e96602`,
  verificado para `linux/amd64` y `linux/arm64`; queda pendiente comprobar en HA
  real una apertura remota fría seguida de otra caliente.

# 2026-08-09 - Sesión de ejecutor y caché de consultas del Predictor

- La validación de HA `0.2.237` demuestra que los enlaces sí conservaron el
  ejecutor M1 y que el worker reutilizó el runtime sin transferir archivos. La
  aparente selección de HA era visual: el estilo global de `form` anulaba el
  atributo HTML `hidden` y superponía una lista recalculada al progreso real.
- Selección y progreso pasan a ser estados excluyentes del modal. La navegación
  interna ejecuta directamente con el ejecutor fijado; solo «Cambiar ejecutor»
  o la indisponibilidad real vuelven a mostrar opciones.
- Reutilizar el runtime no equivale a reutilizar una respuesta. Se incorporan
  cachés LRU ligadas al fingerprint: 512 resultados área/fecha por especie y 32
  respuestas completas por servicio. La caja negra distingue ahora
  `runtime_cache_status` de `worker_response_cache_status`.
- Rankings, matriz semanal e historial agrupan sus filas y aplican cada modelo
  sklearn una vez por lote. No cambian features, probabilidades ni contrato;
  únicamente eliminan inferencias unitarias repetidas.
- Medición directa con los datos locales actuales del M1: ranking de 8 áreas,
  2,7817 s inicial y 0,0002 s repetido; matriz de 56 área/día, 2,6998 s inicial y
  0,0012 s repetida. Estos tiempos son backend puro y todavía deberán validarse
  extremo a extremo con la siguiente imagen worker y release HA.
- Worker `1.0.1` construido y validado healthy en el M1 con capacidad
  `predictor_v1`, caché GIS/DEM válida y coordinador de producción conservado.
  La imagen arm64 tiene ID
  `sha256:cab9d6b76d537f5104b57d1aebce63f8c01df624406b05ea0906cd7207d15103`;
  el paquete M5 exportado tiene SHA-256
  `d7038586920e8e4616588195abe8a837b016c24defe63bcff7479fc80008a35d`.
- HA `0.2.238` publicada para `linux/amd64` y `linux/arm64`. Los tags de
  versión y `latest` comparten el digest
  `sha256:90f87d105f08b0061c480dd8168126663cb947d4128771c70179b1379b7e5e0d`.
  El smoke previo pasó 530 tests y validadores; queda pendiente la validación
  funcional de ambas imágenes en HA real y M5.

# 2026-08-09 - [VIGENTE] El progreso del Predictor es presentación, no protocolo

- Una reproducción dentro del worker calculó la matriz semanal de 56 filas en
  2,617 s y la repetición cacheada en 0,001 s. Los jobs reales empleaban entre
  117 y 134 s aun reutilizando runtime y sin transportar archivos.
- [REEMPLAZADA] La implementación granular anterior hacía dos llamadas
  síncronas a HA por callback
  (cancelación y progreso), con un callback por área/día. El M1 no era más lento
  que la RPi4; estaba esperando al coordinador.
- Los jobs interactivos dejan de publicar progreso granular. Conservan inicio y
  final duraderos; la espera visual y su ETA se calculan exclusivamente en el
  navegador y no afirman representar porcentaje real del backend.
- La observabilidad autoritativa permanece en el resultado final y en la caja
  negra de HA. Cualquier futura traza detallada de fases se agregará en memoria
  en el worker y se enviará una sola vez al completar.
- El cambio de runtime se identifica como worker `1.0.2`; HA `0.2.239` está
  publicada con el nuevo modal y pendiente de validación conjunta en la RPi4.

# 2026-08-09 - [VIGENTE] El Predictor público será worker-only

- El panel privado de HA conserva por ahora selección manual y ejecución en HA;
  ambas capacidades de política son constantes internas `True`, no opciones del
  add-on ni permisos de usuario.
- Una futura integración autenticada en MapLibre asignará Auto a los usuarios
  normales y ejecutará exclusivamente en workers `predictor_v1` disponibles.
- No habrá fallback silencioso a HA/RPi4 cuando falte capacidad externa. Se
  mostrará indisponibilidad o se usará una cola expresamente acotada.
- El navegador seguirá hablando con el gateway de HA y nunca con un worker
  directamente. HA conserva autorización, jobs, resultados y Diagnostics.
- La exposición multiusuario requiere antes límites de concurrencia, rate
  limiting y caché compartida de respuestas. El objetivo no es únicamente
  mejorar latencia, sino proteger la RPi4 al escalar.

# 2026-08-09 - [DUDA] Fuente futura de permisos del Predictor

- Queda deliberadamente sin decidir si la selección manual y el permiso de usar
  HA se derivarán del rol Admin hardcoded, de campos por usuario o de perfiles.
- No existe hoy un mantenimiento de tipos de perfil que justifique añadir esa
  complejidad, y el panel privado por Ingress no aporta identidad Rainmapper.
- Hasta abordar la UI pública, no convertir estas políticas en opciones del
  add-on ni abrir un mantenimiento nuevo.

# 2026-08-09 - [VIGENTE] Telemetría acotada y promoción GIS con caché segura

- Reconstrucción y entrenamiento externos conservan solo el evento de progreso
  más reciente y publican control/progreso como máximo cada 2 s. Antes del
  cierre fuerzan la última comprobación de cancelación y el progreso pendiente.
- La promoción sigue verificando inputs autoritativos, pero reutiliza hashes GIS
  ligados a tamaño, mtime, ctime, dispositivo e inode. Si cambia cualquiera de
  esos campos, recalcula el SHA-256 completo del archivo afectado.
- Así se evita releer habitualmente los 5,87 GiB GIS durante la promoción sin
  aceptar como válida una caché cuya identidad de sistema haya cambiado.
- Worker M1 `1.0.3` construido y validado healthy/idle con identidad y cachés
  persistentes conservadas. HA `0.2.241` publicada para `linux/amd64` y
  `linux/arm64`; `0.2.241` y `latest` comparten el digest
  `sha256:cb33dc2854f51a2a42eb10de93deeabbf12711c9da6282bbe8c9971f7af1f3d5`.
- Smoke completo: 538 tests y validadores correctos.

# 2026-08-10 - [VIGENTE] El target V0 mide una salida minimamente interesante

- `prediction_target` no significa presencia biologica ni hallazgo de cualquier
  carpoforo. Clasifica si la florada observada alcanza una utilidad minima para
  recomendar una salida de recoleccion.
- La frontera autoritativa del catalogo es `scarce=1`, `very_scarce=0` y
  `absent=0`. Un hallazgo testimonial de uno o dos ejemplares puede conservar
  `analysis_result=present` y ser, al mismo tiempo, operacionalmente
  `unfavorable`.
- El entrenador conserva el holdout cronologico solo cuando ambos tramos tienen
  las dos clases, evalua con CV estratificada sobre todos los episodios y
  reajusta los modelos productivos con todos los episodios elegibles.
- El Predictor aplica la fenologia autoritativa de cada especie antes de cargar
  modelo o meteorologia y excluye del recomendador las fechas fuera de temporada.
- HA `0.2.242` y worker `1.0.4` incorporan esta politica. M1 queda healthy/idle
  con identidad y caches persistentes conservadas; el paquete arm64 privado del
  M5 queda preparado en el Escritorio.
- `0.2.242` y `latest` comparten el digest GHCR
  `sha256:3abd516d7aeac7bd4f8bfeacc2d96be2823f339a6c5d31cdc62caaf64ebc562b`
  y contienen manifests `linux/amd64` y `linux/arm64` verificados.
- Smoke completo: 543 tests y validadores correctos.

# 2026-08-10 - [VIGENTE] El siguiente hito es endurecer ML con el dataset actual

- La reconstrucción y el reentrenamiento reales de HA `0.2.242` han terminado.
  El siguiente trabajo no es ampliar el dataset ni Diagnostics: es pulir los
  modelos actuales y comparar alternativas más gestionables y explicables.
- No hay por ahora más observaciones de salidas ni más cobertura meteorológica.
  El benchmark debe trabajar con el snapshot actual sin fabricar negativos ni
  esperar a que crezca la muestra.
- El caso centinela Aereus/Coll de la Batalla/2026-08-14 produjo 71% mediante
  media no ponderada de LR 98% y RF 44%. El Parquet estaba completo hasta la
  fecha de emisión; cuatro días posteriores aún desconocidos hicieron caer
  artificialmente a cero `heat_stress_days` y `dry_spell_days`.
- La evaluación temporal de Aereus fue peor que azar: ROC-AUC `0,3818` para LR,
  `0,4545` para RF y accuracy `0,1875` para el ensemble. Esos modelos no deben
  conservar igual peso ni presentarse como probabilidades calibradas.
- Se priorizan tratamiento explícito de gaps, abstención, reducción a pocas
  variables, validación temporal reproducible y comparación con baselines. Se
  evaluarán LR reducida, árboles restringidos y un enfoque híbrido de
  elegibilidad ecológica más score estadístico antes de modelos más complejos.
- Diagnóstico y plan vinculante:
  `docs/mushrooms/mushroom-ml-model-hardening-plan-es.md`.

# 2026-08-10 - [VIGENTE] Los modelos nuevos se compararán sobre un benchmark temporal congelado

- La pregunta común es `P(florada en T | meteorología observada hasta T-h)`.
  No se utilizan predicciones meteorológicas ni se convierten días futuros en
  ceros observados.
- El artefacto unido conserva las series meteorológicas diarias en JSON, pero
  estas siguen fuera del CSV y del estimador operativo v0.
- `mushroom_ml_experiments.py` materializa muestras con fecha objetivo, fecha
  de corte y horizonte 0..6; todos los horizontes de un episodio y todas las
  áreas de una misma fecha/especie permanecen en una única partición temporal.
- `lag_event_v1` es la primera hipótesis de variables compactas: bandas de
  lluvia disjuntas, edad de eventos conocidos, condiciones posteriores y
  rachas observadas con censura explícita. No se promociona automáticamente.
- Cualquier comparación futura debe fijar hash del benchmark, feature set,
  estimador, hiperparámetros, semilla, imputación, calibración y métricas. El
  contrato completo está en
  `docs/mushrooms/mushroom-ml-experiment-contract-es.md`.

# 2026-08-10 - [VIGENTE] Fixed-gap y lag-event convivirán como modelos shadow

- `fixed_gap_7d_v1` oculta siempre `T-6..T` y calcula todas sus variables con
  corte `T-7`; `lag_event_v1` usa el corte de emisión y horizontes 0..6.
- Ambos usan las mismas familias LR reducida y RF restringido. Sus bundles se
  generan en el job de entrenamiento, se promocionan junto al modelo operativo
  y se incluyen en el runtime remoto, pero nunca sustituyen automáticamente
  `mushroom_ml_v0`.
- «Consultar fecha» ofrece una comparación opt-in con corte, LR, RF y resultado
  por contrato. Los scores shadow no son probabilidades calibradas y no cambian
  la recomendación oficial.
- La plausibilidad de casos concretos sirve para falsar modelos, no para
  validarlos. La decisión futura exigirá métricas temporales, casos centinela y
  predicciones prospectivas contrastadas sobre el terreno.

# 2026-08-10 - [VIGENTE] La lluvia tolera huecos y la estación debe ser elegible

- El artefacto experimental conserva 120 días y busca eventos hasta 90; una
  edad no encontrada vale 90 («90 o más»), nunca `null`.
- Lluvia ausente o explícitamente descartada aporta `0 mm` efectivos, pero se
  conservan días observados, ausentes y suprimidos. Temperatura y humedad se
  agregan solo sobre valores disponibles y mantienen cobertura propia.
- `lag_event_v1` corta en ayer o en el último día completo anterior y usa
  horizontes 1..7.
- Desde el centroide del área se prueban estaciones por cercanía hasta 15 km.
  La primera que alcance 19/21 y 81/90 de lluvia y 19/21 de temperatura y
  humedad es elegible; si ninguna cumple, el Predictor se abstiene.
- El contrato no pertenece solo al entrenamiento: el Predictor usa los mismos
  constructores versionados, tratamiento de lluvia, corte efectivo y selector
  de estación. La salida shadow conserva variables, coberturas y estación para
  poder auditar esa paridad.
- Un shadow puede ajustarse con el dataset completo cuando éste contiene las
  dos clases aunque su partición cronológica train/test no las contenga. En ese
  caso queda marcado sin validación temporal; la evaluación estratificada puede
  seguir disponible, pero una promoción deberá considerar expresamente esa
  limitación. Nunca se divide una misma fecha para fabricar clases a ambos lados.

# 2026-08-10 - [VIGENTE] La evaluación shadow principal es estratificada y la temporal es diagnóstica

- El 70/30 principal aproxima por separado la proporción de favorables y
  desfavorables, con semilla fija `42` y agrupación indivisible por especie y
  fecha objetivo.
- El 70/30 cronológico se conserva como diagnóstico secundario de deriva. Si
  train o test tienen una sola clase, queda marcado no disponible y no se
  fuerza un corte que divida episodios de una misma fecha.
- Los bundles de consulta se reajustan con todos los episodios después de la
  evaluación. Promoción y calibración deben considerar tanto el resultado
  estratificado como la disponibilidad del diagnóstico temporal.
- Esta decisión reemplaza la evaluación shadow exclusivamente cronológica; no
  cambia el corte meteorológico de `fixed_gap_7d_v1` ni `lag_event_v1`.

# 2026-08-10 - [VIGENTE] Fixed-gap y lag-event sustituyen al v0 en la decisión visible

- `mushroom_ml_v0` no es válido como predictor futuro porque sus ventanas
  terminan en la fecha objetivo. Se conserva como baseline interno durante la
  transición, pero deja de decidir tarjetas, rankings, semana, Historial y
  factores meteorológicos visibles.
- `fixed_gap_7d_v1` y `lag_event_v1` conviven como pareja operativa. Sus LR, RF
  y medias no ponderadas permanecen auditables y no se presentan como
  probabilidades calibradas.
- Cada bundle incorpora métricas fuera de muestra. Por especie y contrato solo
  aporta referencia el estimador con menor Brier entre los que superan la
  prevalencia; si ninguno la supera, el Predictor se abstiene.
- Una diferencia LR/RF de al menos 20 puntos fuerza consenso bajo. El dictamen
  combina ese estado estadístico con cobertura, estación, temporada, evento de
  lluvia y retraso de fructificación mediante reglas deterministas y
  versionadas, nunca mediante texto libre generado.
- Un score estadístico no puede producir «favorable» si el perfil de la especie
  define una ventana de fructificación y no existe lluvia significativa en 90
  días o el evento queda más allá de su máximo. Esta barrera ecológica es común
  a todas las especies y deja los scores brutos visibles solo para auditoría.
- Para cada corte se prefiere la estación elegible más cercana que tenga ese día
  completo. Una estación globalmente válida pero retrasada se salta en favor de
  la siguiente elegible dentro de 15 km; solo se retrocede el corte si ninguna
  candidata dispone del día requerido.
- «Consultar fecha» conserva el detalle técnico de ambos modelos, elimina las
  barras meteorológicas del v0 y muestra dictamen resumido arriba y explicación
  debajo. Las vistas compactas usan el mismo contrato y enlazan al detalle.
- La implementación se valida primero en local. La publicación posterior exige
  actualizar juntos HA y workers porque ambos ejecutan el contrato, sin
  cambiar red, Tailscale ni la autoridad de HA.

# 2026-08-10 - [VIGENTE] El Predictor conserva señales no validadas y audita el dominio

- La prevalencia es un control de calibración sobre salidas seleccionadas por
  el observador, no la frecuencia real de floradas entre todos los días-área.
  No silencia por completo una señal útil para el barrido sistemático.
- Si ningún estimador mejora el Brier de prevalencia, el Predictor distingue
  señal favorable no validada, desfavorable no validada o no interpretable.
  Su rango bruto queda visible únicamente en la auditoría técnica: no participa
  en rankings ni se presenta como recomendación o probabilidad calibrada.
- Los bundles `1.1` conservan soporte de variables y predicciones holdout. Una
  LR que recibe una variable fuera del rango y a seis o más desviaciones
  estándar queda excluida; un conflicto validado de 50 puntos o más fuerza
  abstención.
- Para episodios conocidos del 30% test, Predictor e Historial muestran los
  scores del modelo que no vio el episodio. Para episodios train muestran el
  ajuste final y advierten que no es una comprobación histórica independiente.
- Los días no visitados y las especies no buscadas siguen siendo desconocidos,
  nunca negativas sintéticas. El éxito futuro se medirá también por ranking,
  recuperación de floradas, precisión top-k y recomendaciones prospectivas.

# 2026-08-10 - [VIGENTE] El laboratorio compara seis estimadores sin promoverlos por votación

- LR y RF mantienen provisionalmente la autoridad del dictamen para no cambiar
  el contrato operativo mientras se analiza el nuevo laboratorio.
- ET, HGB, KNN por distancia y SVM RBF calibrada se entrenan como modelos sombra
  sobre las mismas muestras y particiones. Sus scores, Brier y ROC-AUC aparecen
  en el detalle técnico, identificados con `*`, pero no votan ni alteran el
  rango de referencia.
- La SVM exige al menos dos ejemplos de cada clase en la partición train para
  poder calibrarse en dos folds. Si no se cumple, se omite para ese contrato y
  especie y se muestra el motivo; no se cambian particiones ni se sintetizan
  observaciones. Actualmente ocurre solo en Marçot/`fixed_gap_7d_v1`.
- Ningún candidato se promociona porque gane una métrica aislada. Se comparan
  estabilidad entre contratos y horizontes, Brier frente a prevalencia,
  capacidad de recuperar episodios favorables y falsos avisos prospectivos.

# 2026-08-10 - [VIGENTE] El dictamen separa ecología, estadística y acción

- La compatibilidad ecológica, el soporte estadístico y el dictamen práctico
  son ejes diferentes del payload de interpretación y de la UI. «Confianza» se
  sustituye por evidencia ecológica y soporte estadístico para evitar que un
  veto fiable parezca consenso entre modelos.
- Una barrera ecológica incompatible decide «poco probable» aunque la capa
  estadística se abstenga. En ese caso los scores descartados no aparecen en
  la cabecera; permanecen auditables en la tabla técnica.
- Solo se muestra rango validado cuando al menos un estimador operativo mejora
  prevalencia y está dentro de dominio. Una sola familia validada produce
  soporte limitado; no se calcula consenso aunque aparezca en ambos contratos.
- La explicación textual rica se conserva y se divide conceptualmente en
  meteorología/ecología y estadística: evento, momento, estación, dominio,
  prevalencia, desacuerdo y condición histórica siguen siendo visibles.
- Las mismas reglas alimentan fecha, semana, especie, recomendador e Historial.
  Los modelos sombra nunca votan por acumulación ni superan un veto ecológico.
- La mejor sombra por Brier de cada contrato sí se resume como señal
  experimental favorable, desfavorable, incierta o contradictoria. Se muestran
  estimadores, rango y cautela fuera de dominio, pero esa señal no cambia el
  dictamen ni el orden de las vistas compactas hasta una promoción explícita.
- Si la ecología es compatible y la capa operativa se abstiene, el título es
  «Incierto — condiciones compatibles»; la dirección bruta de LR/RF y la señal
  experimental quedan diferenciadas en la explicación y auditoría.
# [VIGENTE] El posible LLM del worker será solo un narrador local opcional

- El Predictor determinista conserva toda la autoridad sobre compatibilidad
  ecológica, soporte estadístico, señales experimentales y dictamen.
- Un futuro worker podrá anunciar `predictor_narrative_v1` para redactar el
  resultado estructurado con un LLM pequeño y local, pero no podrá alterar el
  dictamen, seleccionar modelos, anular vetos ni inventar valores.
- La capacidad será independiente de la imagen base y siempre tendrá fallback
  al texto determinista; no se autoriza todavía instalar ni descargar modelos.
- Contrato y despliegue gradual:
  `docs/mushrooms/mushroom-worker-local-llm-narrator-design-es.md`.

# 2026-08-11 - [VIGENTE] Retención intradía meteorológica y escritura atómica

- `Aemet_hourly_incremental.csv` y
  `Meteoclimatic_observations_incremental.csv` conservan en producción
  siete fechas locales cerradas más la fecha actual. Se retienen fechas de
  calendario completas, no una ventana móvil de 168 horas.
- El corte ocurre después de fusionar/deduplicar y antes de reconstruir el
  diario. Una estación, fecha o variable ausente no crea filas ni lluvia cero.
- Los incrementales diarios preservan todas las claves anteriores: solo se
  actualizan las fechas realmente reconstruidas.
- Los CSV meteorológicos críticos se escriben mediante temporal en el mismo
  directorio y sustitución atómica. Un fallo de serialización conserva el
  destino anterior.
- La política fue validada primero en el M1 y después desplegada y comprobada
  mediante runners ordinarios e idempotencia en HA/RPi4.

## 2026-08-11 - [REEMPLAZADA] Separar cola viva e histórico monolítico

- Los cuatro CSV diarios no deben seguir siendo simultáneamente área de trabajo
  e histórico canónico. Tras el backfill superarían 5 millones de filas y unos
  872 MiB, mientras el Parquet equivalente ocupa unos 82 MiB.
- La propuesta recomendada conserva 180 fechas locales en los CSV vivos como
  colas de ingestión/recuperación y convierte el `weather_daily.parquet`
  monolítico actual en histórico canónico con upsert atómico.
- Predictor, reconstrucción y workers ya consumen ese Parquet; entrenamiento
  consume los artefactos reconstruidos. Tomap es la excepción actual: debe
  cambiar de los CSV a una lectura Parquet filtrada a 90 días.
- El runner `all` ya ejecuta `update` antes de `maps`. Antes del cambio se debe
  completar el schema de viento y bloquear publicación si la actualización no
  confirma un Parquet válido/fresco.
- Particionar por fuente/año queda como alternativa solo si el monolítico no
  cumple el presupuesto medido de RAM/tiempo.
- No se autoriza todavía compactar los CSV diarios. Antes deben migrarse y
  validarse claves/valores, frescura, cruces de año, MapLibre, features,
  rebuild, entrenamiento, snapshots de workers, backup y rollback.
- Diseño detallado y puerta de aceptación:
  `docs/weather-storage-retention-plan-es.md`.

## 2026-08-12 - [VIGENTE] Histórico meteorológico transaccional fuente/año

- Se mantiene la separación entre cuatro CSV vivos de 180 fechas y el
  histórico canónico, pero se descarta el upsert monolítico para la RPi4 de
  4 GiB. La prueba conservó los datos, pero su pico de memoria no deja margen
  operativo seguro a Home Assistant, Docker y los demás servicios.
- El histórico se organiza en particiones inmutables `source/year` y se publica
  como una generación completa mediante manifiesto y `CURRENT.json` atómico.
  Los lectores nunca hacen glob ni observan una mezcla de generaciones.
- El bootstrap parte de los cuatro CSV completos de un mismo rebase validado.
  Para el corte actual son los de `rebase-trials/20260811T114432Z/candidate/`,
  con 5.025.368 filas. Mezclar los `candidate/` originales con `current/`
  perdería 301 filas del rebase. Los cuatro legacy tienen 27 columnas y se
  normalizan al schema canónico de 28 con `source`.
  El Parquet candidato antiguo solo tiene 14 y no puede recuperar
  metadata/viento.
- La ruta normal archiva únicamente el lote fresco/corregido, previamente
  persistido como pending idempotente. Cada partición se fusiona como flujos
  ordenados, sin cargar el año completo en pandas. La cola de 180 fechas se
  reaplica solo en reparación explícita.
- Catálogo temporal, Predictor, reconstrucción, Tomap, snapshots y workers
  deben migrar al manifiesto; cachés se invalidan por `generation_id`.
- Revisión Sol-High: el archivador corre aislado después de `update-sources`.
  Objetivo: menos de 64 MiB RSS adicionales y 192 MiB absolutos; hard gate:
  menos de 128/256 MiB. Cada proceso normal del pipeline tiene objetivo menor
  de 256 MiB absolutos y hard gate menor de 384 MiB. Si una partición anual no
  cumple, se subdivide esa fuente/año por bloques deterministas de estación.
- No se autoriza compactar CSV reales ni promover el dataset. Especificación:
  `docs/weather-history-partitioned-implementation-spec-es.md`.
- El cutover deberá reconciliar una copia fresca y estable de los CSV de HA
  durante una ventana de mantenimiento autorizada. La generación del lab no se
  promueve directamente mientras el scheduled runner siga avanzando. Los jobs
  largos fijan su generación mediante leases y el GC empieza en modo audit-only.
- Estado local 2026-08-12: fases A–C implementadas con contrato ligero sin
  pandas, pending por sort externo, merge por cursores/slices, catálogo,
  receipts, commit, recuperación y reparación post-restore explícita. Benchmark
  Mac `aemet/2024`, row group 8.192: 3,167 s, +48.398.336 bytes RSS y
  2.006.676 bytes de salida. El gate arm64/RPi4 continúa siendo obligatorio.
  La captura por fuente, archivador aislado,
  pre/post-drain, `run.lock` y compactación streaming de los CSV vivos están
  integrados detrás de un feature flag desactivado por defecto; falta la
  validación arm64 antes de considerarlos publicables. Tomap, Predictor,
  catálogo, reconstrucción acotada y snapshots `0.2` consumen ya la generación
  por manifiesto en modo particionado. Una simulación local disposable de las
  cuatro fuentes conservó las 227.406 filas vivas, modificó solo las cuatro
  particiones 2026, cerró todos los pending y alcanzó 175.013.888 bytes RSS
  absolutos. No se ejecutó el runner ni se tocó HA.
- El split y la compactación inicial de los CSV vivos se ejecutan en el M1. El
  cutover autorizado entregará a HA candidatos de 180 fechas ya ordenados y
  validados; la RPi4 no cargará con el procesamiento inicial de los históricos
  completos.
- Revisión operativa 2026-08-13: el cutover descrito ya se ejecutó. Histórico,
  CSV vivos y colas intradía están desplegados; consumidores, runner ordinario,
  idempotencia y recursos de la RPi4 fueron validados y los schedules están
  activos. Las frases anteriores en futuro se conservan como trazabilidad del
  diseño, no como trabajo pendiente.

# 2026-08-11 - [VIGENTE] Temperatura corregida a la altitud representativa del área

- Se crean los contratos `fixed_gap_7d_altitude_v2` y
  `lag_event_altitude_v2`; los v1 se conservan como referencia reproducible.
- Toda temperatura se transforma antes de construir variables mediante
  `T_area = T_station + (z_station - z_area) / 100 * 0,65 °C` tanto en
  entrenamiento como en inferencia. La lectura meteorológica cruda no se
  modifica.
- `z_station` procede del catálogo meteorológico. `z_area` es la media de las
  altitudes DEM medias materializadas de todas las microáreas que pertenecen al
  área. No se usa el DEM puntual del centroide ni se consulta el DEM en vivo.
- La altitud representativa se calcula desde el conjunto completo de
  microáreas, no desde las observadas en el episodio; así no varía con la
  cobertura de una salida concreta.
- El gradiente de 0,65 °C/100 m forma parte del contrato versionado y coincide
  con el valor actual de MapLibre. No es una variable aprendida ni una opción
  dinámica de la consulta.
- Si falta la altitud de estación o área, las variables térmicas corregidas son
  ausentes. Está prohibido usar en silencio la lectura cruda en un bundle v2.
- Se retiran de v2 `heat_stress_observed_at_cutoff` y su censura, basados en el
  umbral global hardcoded de 28 °C. Se añaden temperatura máxima media y
  temperatura media de siete días, continuas y corregidas. Cada modelo aprende
  el comportamiento térmico por especie sin umbrales manuales por especie.
- La respuesta técnica conserva altitud de estación, altitud representativa,
  offset y gradiente para auditar cada predicción.

## 2026-08-11 - [VIGENTE] La auditoría fuera de dominio muestra magnitud y soporte

- El detalle técnico del Predictor no reduce una extrapolación al identificador
  interno de la variable. Para toda variable fuera de dominio muestra nombre
  legible, valor consultado, mínimo y máximo observados durante el entrenamiento
  y distancia respecto a la media aprendida en desviaciones estándar.
- Las unidades dependen del contrato de la variable: días, milímetros, grados,
  porcentaje, metros o recuentos. Las variables futuras desconocidas conservan
  un fallback legible y muestran igualmente sus valores y rango.
- `heat_stress_observed_at_cutoff` mide una racha de días, no una temperatura.
  Su umbral de 28 °C no fue aprendido ni procede de una fuente biológica citada:
  se introdujo como hipótesis experimental en HA 0.2.215 y fue heredado por los
  contratos v1. No se presenta en la UI como si fuese soporte aprendido. Los
  contratos `*_altitude_v2` posteriores ya lo sustituyen por variables térmicas
  continuas corregidas por altitud; v1 permanece solo como referencia.
- Para cada variable se muestra también `Δ`, calculado contra el límite de
  entrenamiento rebasado: positivo por encima del máximo y negativo por debajo
  del mínimo. El tooltip distingue valor actual, rango de entrenamiento, delta
  físico y distancia estadística en `σ`.
- Se listan todas las variables fuera de dominio; las que superan el umbral
  severo quedan marcadas explícitamente. Solo estas últimas activan exclusiones
  de estimadores o cautela en la interpretación.
- Caso centinela: Pinícola/Guils, 2026-08-14. `lag_event_v1` observa 14 días
  consecutivos por encima de 28 °C frente a un rango de entrenamiento 0–12,
  equivalente a 6,484 desviaciones estándar respecto a su media aprendida.

## 2026-08-10 - Predictor por contratos e interpretación separada

Estado: PUBLICADO EN HA `0.2.243`; WORKER M1 `1.0.5` ACTUALIZADO; PENDIENTE DE
INSTALAR Y VALIDAR EN HA REAL.

Decisión:

- Retirar de la recomendación visible el contrato v0 que necesita
  meteorología hasta la fecha objetivo y usar `fixed_gap_7d_v1` y
  `lag_event_v1` con los mismos constructores durante entrenamiento e
  inferencia.
- Separar dictamen práctico, compatibilidad/evidencia ecológica y soporte
  estadístico operativo. Los scores brutos permanecen para auditoría, pero no
  se muestran como probabilidades calibradas ni pueden anular un veto.
- Mantener ET, HGB, KNN y SVM como shadows. Su mejor señal validada se muestra
  de forma genérica y explícitamente experimental, sin modificar dictamen ni
  ranking.
- Usar el contrato meteorológico documentado: 120 días conservados, búsqueda
  de eventos hasta 90, cobertura explícita, tolerancia a huecos aislados y
  salto a una estación suficientemente completa hasta 15 km.
- Publicación HA verificada con digest
  `sha256:39c64c072d57259544a9290d15e117e811c38411cf3044afa5bb2cfd0af107cf`
  para `0.2.243` y `latest`, ambos con `linux/amd64` y `linux/arm64`.
# 2026-08-13 - [VIGENTE] La identidad de una generación se calcula con su forma viva final

- En el flujo reconstrucción → entrenamiento → promoción, el features candidato
  se serializa antes de entrenar con las mismas rutas y metadata que tendrá al
  quedar vivo. Los modelos guardan el hash de ese contenido final exacto.
- Preparación y promoción comparten una única función canónica de rebase. No se
  permite que la promoción modifique después del entrenamiento ningún byte que
  forme parte de la identidad verificada por el Predictor.
- El Predictor conserva la validación estricta: ante una discrepancia de hash
  bloquea la consulta en lugar de mezclar artefactos y modelos. La corrección es
  regenerar y promover conjuntamente, no relajar el control.
- Los errores técnicos completos se conservan para diagnóstico, pero las rutas
  y hashes largos deben envolver dentro del modal de la UI.

# 2026-08-13 - [VIGENTE] Altitude V2 exige rebuild y training compatibles

- El soporte de los tipos de job no demuestra compatibilidad del contrato ML.
  Worker `1.0.7` podía reconstruir y entrenar, pero produjo features sin
  `weather_station_altitude_m` y bundles V1; HA `0.2.253` ya solicitaba V2.
- Altitude V2 se cierra solo cuando el mismo pipeline materializa altitud de
  estación, entrena `fixed_gap_7d_altitude_v2` y `lag_event_altitude_v2`, y el
  Predictor consume esos bundles contra el mismo hash de features.
- El resultado de training declara `shadow_feature_set_ids`. El coordinador
  debe rechazar cualquier promoción que no declare exactamente ambos contratos
  V2, aunque los hashes internos sean coherentes.
- La corrección requiere worker `1.0.8` y una reconstrucción completa; no se
  reparan ni renombran bundles V1 y no se mezclan modelos individuales.
- Las versiones HA, worker y contrato ML son independientes. Su genealogía
  permanente vive en `docs/mushrooms/mushroom-ml-contract-versions-es.md` y no
  se elimina al compactar el contexto activo.
- La barrera se publica en HA `0.2.254`; `0.2.254` y `latest` comparten
  `sha256:bcc72af6fe60bffd0a75246c5ca6726ef42a9a1852c7fa8fabdcef81b9b8b362`
  con manifests `linux/amd64` y `linux/arm64`.
- Validación de producción completada: HA `0.2.254` y worker `1.0.8`
  reconstruyeron, entrenaron y promovieron conjuntamente altitude V2. M1 es el
  ejecutor ordinario. La RPi4 ejecutó una semana completa en 97,608 s, sin OOM,
  con máximo aproximado de 577 MiB y 46,25 °C; por tanto HA queda VIGENTE como
  fallback administrativo lento, no como ruta automática preferida.

# 2026-08-13 - [REEMPLAZADA] Worker 1.0.7 no necesitaba actualización

- La conclusión se basaba en que `1.0.7` anunciaba y ejecutaba rebuild y
training. La prueba real demostró que no incluía el contrato altitude V2 de
extremo a extremo. Queda reemplazada por la decisión anterior.

# 2026-08-23 - [VIGENTE] Dos únicos flujos ML y evidencia de benchmark no instalable

- El mantenimiento rutinario de las versiones instaladas es un único flujo:
  rebuild completo, ML v0 y entrenamiento multiversión se verifican y
  autopromocionan conjuntamente. No existen reconstrucciones operativas
  parciales ni promociones manuales aisladas.
- Un benchmark científico sirve para comparar contratos y conservar evidencia.
  Tras verificarse pasa inmediatamente a `evidence_only`; la UI mantiene
  Historial, Ver informe y Borrar, pero no prepara, activa ni revierte versiones.
- Las antiguas rutas de candidato desde benchmark, activación manual y rollback
  por versión, junto con `ml_models/candidates` y `promotion-history`, son
  legacy. El reconciliador solo las elimina tras validar identidad y nunca en
  modo `dry-run`.
- Los únicos batches protegidos permanentemente son los referenciados por una
  `installed_generation_id`. La instalación conserva rollback transaccional
  mientras está en curso y un único backup del rebuild completo después.
- Los resultados pesados de ejecuciones operativas fallidas, canceladas o
  interrumpidas se conservan 24 horas para diagnóstico; después queda el
  resumen ligero del job.
- Esta decisión fue desplegada en HA `0.2.266`. El reconciliador real ejecutó
  `mode=apply removed=74 errors=0` tras autorización del usuario y la cadena
  completa posterior instaló las cinco versiones con 636/636 ajustes y cero
  fallos. Esto no autoriza nuevas limpiezas manuales, builds ni releases.

# 2026-08-23 - [VIGENTE] Auditar deuda de código como entrega separada

- Tras cerrar e instalar la política de retención se hará una auditoría completa
  del source para localizar rutas legacy, flags sin consumidor, adaptadores
  monoversión, duplicaciones y parches acumulados.
- La auditoría empezará por referencias y call paths y no mezclará eliminaciones
  amplias con el despliegue actual de almacenamiento.

# 2026-08-26 - [VIGENTE] El selector operativo procede del registro instalado

- Las versiones disponibles para reconstrucción no se codifican como una lista
  fija en la UI ni en la cadena de jobs. Se derivan del registro activo y pueden
  seleccionarse como cualquier subconjunto instalado de V2, V3, V4, V5w y V6w.
- La selección atraviesa sin alterarse rebuild, ML v0, entrenamiento
  multiversión y promoción. Esto permite reentrenar solo una versión cuando sea
  necesario sin desinstalar las demás.
- `preferred_version_id` permanece separado: determina las vistas operativas
  normales, pero no restringe una comparación multiversión explícita.
- La regla quedó publicada en HA `0.2.266`; el ensayo local y la ejecución real
  completa reconocieron las cinco versiones.

# 2026-08-26 - [VIGENTE] Retención ML activa en HA real mediante el reconciliador

- El usuario habilitó **Apply ML storage retention**. La primera evidencia real
  registró 74 eliminaciones y cero errores, y Predictor y entrenamiento
  continuaron funcionando después.
- La caché TAR regenerable permanece fuera de `/share`, bajo `/media`, para no
  incorporarse al backup de HA. Los datos persistentes solo se eliminan por el
  plan auditado y las reglas de identidad; no se complementa con borrados
  manuales.
- El valor por defecto del producto sigue siendo `false`. La opción real activa
  no debe cambiarse sin decisión nueva del usuario.

# 2026-08-26 - [VIGENTE] Presupuesto de diez minutos y optimización transversal antes que C

- `Reconstruir y reentrenar operativo` debe tardar como máximo diez minutos
  extremo a extremo en el M1 Pro dentro de Docker, conservando hashes,
  trazabilidad, cancelación, retry, rollback y promoción atómica.
- La ejecución real tardó unos 37 minutos, pero los fits observados ocuparon
  solo 2–3. Los cuellos confirmados son microllamadas y `fsync` por artefacto,
  reescritura de una cola de 5,39 MB en cada tick, validaciones/rehashes
  repetidos y preparación secuencial sin telemetría suficiente.
- El orden vinculante es: instrumentar; compactar cola y telemetría; agrupar la
  transferencia de forma segura y reanudable; sellar/reutilizar verificación;
  compartir preparación; y solo entonces paralelizar de forma acotada.
- C, Cython, Numba o Rust solo se evaluarán si un perfil posterior demuestra un
  núcleo Python puro dominante. No se compila por intuición ni se debilita el
  contrato de seguridad para alcanzar el presupuesto.
## 2026-08-28 - [VIGENTE][RELEASE] Hotfix HA 0.2.273 publicado y cadena local validada

- HA `0.2.273` corrige el `NameError` de la verificación de
  `operational_scope_id`; el worker permanece en `1.0.22` porque su artefacto no
  necesitó cambios.
- `0.2.273` y `latest` comparten el índice OCI
  `sha256:6d1f21df2006df46888f6099cb1f135386ab25ce3a9d11497459c02aad374af1`
  con manifests `linux/amd64` y `linux/arm64`.
- La cadena local definitiva ejecutó el mismo scope sellado en V0 y V2–V6:
  ocho especies, cinco versiones, once perfiles y 636/636 fits sin fallos. La
  promoción atómica instaló todas las generaciones del lote y un Predictor frío
  posterior terminó con HTTP 200.
- La instalación y el inicio de la cadena real corresponden al usuario. La
  equivalencia local/remoto no queda demostrada hasta comparar esa ejecución.

## 2026-08-28 - [VIGENTE] El handoff operativo reutiliza los inputs exactos de ML v0

- Un `OperationalTrainingScope` identifica el contenido canónico completo de
  features y `known-sites`, no solo sus filas o especies. Dos representaciones
  con metadatos de rutas distintos no son el mismo input sellado.
- La cadena HA→worker debe capturar los bytes exactos y comprobar los digests
  del bundle de ML v0 antes de su limpieza normal. V2–V6 incorpora esas copias
  al snapshot y valida que reproducen íntegramente el scope certificado.
- No se admite reconstruir el input desde el candidato original, leer de nuevo
  `known-sites` vivo ni relajar la comparación del scope. La decisión conserva
  retención, gates, retry, rollback y promoción atómica.
- La primera cadena real de HA `0.2.273` reveló el defecto al fallar V2–V6 con
  `Operational preparation inputs do not match the sealed scope`; no hubo
  promoción. La corrección se publicó en HA `0.2.274`; `0.2.274` y `latest`
  comparten el índice OCI
  `sha256:899d45f797952218ea865e40d3293247ab14d8d6f3e6e53ea7f807595f0fd001`
  con manifests `linux/amd64` y `linux/arm64`. El worker permanece en `1.0.22`.

## 2026-08-28 - [VIGENTE] Un resultado calculado espera al coordinador sin reentrenar

- Los fallos transitorios de telemetría de un job remoto no invalidan ni
  detienen su cálculo local. Los rechazos de contrato, integridad o autorización
  siguen siendo errores terminales.
- Una vez generado el resultado de reconstrucción, ML v0 o V2–V6, el worker lo
  conserva y reintenta la entrega sin plazo hasta recuperar comunicación con el
  coordinador o recibir una cancelación normal/forzada.
- El alcance se limita a telemetría y entrega final. No cambia claim, descarga
  de inputs, inicio, retención ni promoción; tampoco introduce una cola o un
  estado persistente nuevos.
- Motiva la decisión el fallo real de V2–V6 de HA `0.2.274` al 90 % con
  `<urlopen error timed out>` después de completar el trabajo costoso.
- Una segunda ejecución llegó también al 90 % y falló con `HTTP Error 409:
  Conflict`: una respuesta perdida permitió que HA conservara un fichero, pero
  el retry era rechazado solo porque la ruta ya existía. HA `0.2.275` acepta el
  mismo tamaño y SHA-256 como reentrega idempotente y rechaza contenido distinto.
- Worker `1.0.24` ejecuta control/progreso en un único intercambio de fondo,
  conserva el último estado coalescido y usa una cadencia normal de 10 s. El
  callback científico no espera la latencia del coordinador; cancelación y
  errores terminales se propagan en el siguiente punto de control.
- HA `0.2.275` y `latest` se publicaron con el índice OCI
  `sha256:64f0cbda06a3b0addcb507bf0efac494d98e14d725f73e50d37c6075840e1e6b`
  y manifests `linux/amd64` y `linux/arm64`. El worker no se publica: se
  reconstruyó localmente como `1.0.24`, conservando identidad, volumen y cachés.

## 2026-08-28 - [VIGENTE] Duración integral y progreso global no se infieren de fases

- La lista de trabajos debe mostrar por separado duración integral de la cadena,
  preparación en HA, espera/claim, ejecución remota, transferencia, verificación
  y duración de la fase actual. Cambiar de `created_at` a `started_at` no puede
  ocultar tiempo ya consumido.
- El progreso total debe ser monótono. Un porcentaje interno de una fase no se
  presenta como total: la validación real mostró una bajada visible de `81 %` a
  `20 %` al pasar de reutilización de inputs a construcción de V3.
- Control y progreso son observabilidad y no forman parte del coste científico.
  Deben conservar cancelación y el último estado útil sin bloquear el cálculo
  local durante el timeout de cada petición al coordinador.
- Hasta implementar y validar estas reglas, la columna de porcentaje no sirve
  para estimar avance o ETA y la duración de cada fila solo describe el intervalo
  que su ancla actual cubre, no el tiempo total desde la acción del usuario.
