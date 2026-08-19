# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos y runtime
antes de afirmar estado presente; `docs/decisions.md` conserva la historia y
las razones duraderas.

## Estado al cierre — 2026-08-19 (release fases 1–4 publicada)

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  Commit `f679f87` "Release Home Assistant 0.2.262" pusheado a `origin/inicial`;
  `git status` limpio.
- HA `0.2.262` y `latest` publicados en GHCR con índice OCI
  `sha256:4eb81b7ff91d966fce128642e039c7f3af9278a824bb95a38c5774a859a85037`,
  manifests `linux/amd64` (`sha256:21f5357bf4cbf969e8a9ac7461da6c5813c709c741e72765737236e4e16d2391`)
  y `linux/arm64` (`sha256:e8f3c072396dfd7956ce16a5cce6a282a30f457136cd1fc342941e48502a1d8c`)
  verificados con `docker buildx imagetools inspect` para ambas etiquetas.
  Publica el conjunto coherente de fases 1–4 (separación operativo/benchmark,
  candidatas/promoción genéricas, Biology V3+ físico, selección de score por
  menor Brier entre todos los estimadores, y las correcciones de catálogo de
  calidad/evidencia de lluvia significativa).
- Bloqueo de empaquetado del worker corregido: `rainmapper-worker/Dockerfile`
  ahora copia y compila `mushroom_ml_biology_v3_physical.py` y
  `mushroom_ml_benchmark_reports.py`. `mushroom_ml_version_promotion.py`
  confirmado como coordinación exclusiva de HA (importado solo por
  `web_server.py`) y no se incluyó en el worker.
- Worker privado local reconstruido como `rainmapper-worker:1.0.15` y validado
  antes de sustituir el contenedor sano: contenedor candidato efímero
  (volumen y red aislados) respondió `/health` con `worker_version=1.0.15` y
  anunció `ml_job_purpose_v1` y `ml_benchmark_report_v1` junto al resto de
  capacidades esperadas. Contenedor real `rainmapper-worker` recreado con
  `1.0.15` reutilizando el volumen `rainmapper-worker-data`; quedó `healthy`
  conservando identidad (`worker_1a9a232c20fe2ee2`, "M1 Personal"), dataset
  cache válido (12 ficheros, ~6,34 GB) y predictor cache válido. Rollback
  exacto disponible: imagen local `rainmapper-worker:1.0.14` intacta.
- Gate ejecutado: 949 pruebas (`.venv/bin/python -m unittest discover -s
  tests`) y smoke canónico (`PYTHON_BIN=.venv/bin/python
  ./scripts/smoke-test.sh`) pasaron antes y después del bump; `git diff
  --check` limpio en ambos.
- No se tocó HA real (instalación en el add-on de producción sigue pendiente
  de que el usuario la ejecute), GHCR no se limpió, no se usó Tailscale y no
  se tocaron históricos meteorológicos.
- Pendiente: el usuario debe instalar/actualizar `0.2.262` en HA real cuando lo
  decida; no hay bloqueo técnico conocido para ello.

## Hallazgo de rendimiento que motiva el siguiente trabajo

- La última cadena mostrada por el usuario empleó aproximadamente 2 min 29 s en
  reconstrucción, 1 min 12 s en ML v0 y 39 min 45 s en V2–V6.
- El manifiesto primario
  `/Volumes/share/rainmapper/mushroom-data/ml_models/batches/local_v2_v6_20260818T162939Z/manifest.json`
  fue revalidado en este cierre: 436 fits planificados, 432 correctos, cuatro
  fallidos y 432 artefactos.
- V2/V3 planifican 96 fits cada uno; V4 192; V5 32 y V6 20. Los 436 son
  artefactos superiores, no todo el trabajo interno: V5 realiza selección
  interna de configuraciones y folds. El bucle superior actual es secuencial.
- No existe todavía instrumentación de duración por fit/estimador. Por tanto,
  V5 y la repetición V2–V4 son sospechosos razonables, no un reparto temporal
  demostrado.

## Fases 1–4 implementadas; fase 4 desplegada en HA local para prueba UI

La propuesta canónica está en
`docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`.

- La UI y el backend separan `Reconstruir y reentrenar operativo` de `Ejecutar
  benchmark científico` en los ejecutores externo y HA local.
- `job_purpose=operational` resuelve todos los perfiles técnicos de la versión
  activa. Hoy sigue siendo `altitude_v2`, con su perfil `common_idw` y sus dos
  contratos fixed/lag; cualquier fit fallido invalida el candidato.
- El transporte externo verifica el resultado operativo y lo deja en staging.
  Solo la promoción conjunta instala `runtime-batch.json`, publica rebuild+ML
  v0, libera caché y limpia pendientes; un fallo previo restaura el descriptor
  anterior y elimina el batch nuevo. El ejecutor local aplica el mismo rollback
  compensatorio.
- `job_purpose=benchmark` mantiene V2–V6 bajo demanda sobre snapshot inmutable.
  Se archiva en `ml_models/benchmarks/<batch_id>`, no escribe el runtime, no
  libera caché y nunca inicia promoción automática.
- Los workers destinados a cualquiera de los dos jobs deben anunciar
  `ml_job_purpose_v1`; así un worker antiguo no puede interpretar el nuevo
  contrato como el job multiversión anterior ni esperar instalación al cerrar
  un benchmark.
- El benchmark permite seleccionar cualquier conjunto no vacío de perfiles
  comparables del registro. La selección se valida y queda fijada en el job,
  plan, manifiesto e informe; el mismo contrato se usa en worker y HA local.
  La UI parte sin perfiles marcados, conserva exactamente la selección tras
  lanzar y muestra ese alcance en la fila del trabajo. La preparación y la
  evaluación hold-out materializan solo el perfil seleccionado y sus
  dependencias; elegir V3 ya no construye ni evalúa V4, V5 o V6.
- Los benchmarks locales en ejecución ofrecen cancelación. El coordinador
  señala el evento, termina el subproceso de preparación o entrenamiento en un
  punto controlado, limpia el directorio temporal y registra `cancelled` sin
  modificar el runtime del Predictor.
- El historial de benchmarks conserva todos los informes y su orden, pero la UI
  limita el bloque a unos cuatro registros visibles y ofrece desplazamiento
  vertical interno para que no alargue la página de workers. El sondeo de estado
  no recarga la página al terminar un benchmark y conserva el scroll vertical y
  horizontal de trabajos recientes cuando actualiza su progreso; los informes
  nuevos se incorporan al historial mediante `Actualizar`.
- Cada benchmark archiva `benchmark-report.json` y
  `holdout-predictions.jsonl`, ambos verificados por hash junto a snapshot,
  plan, artefactos y métricas. El worker debe anunciar además
  `ml_benchmark_report_v1`.
- Cada fit registra estado y duración. El informe contextual (`Ver informe`
  para un solo perfil, `Ver comparación` para varios) muestra
  por especie, contrato, horizonte y estimador Brier, prevalencia, delta,
  ROC-AUC, calibración, soporte, abstenciones, fallos y duración. El historial
  se reconstruye desde `ml_models/benchmarks/`, sobrevive a la cola de jobs y
  no calcula medias entre especies ni declara un ganador universal. Al cerrar
  un job local, la fila conserva su selección exacta, muestra los contadores
  archivados y provoca una recarga única para incorporar el informe al
  historial sin esperar una recarga manual.
- Desde un informe que contenga todos los perfiles técnicos de una versión, la
  UI permite `Preparar candidata completa`. La preparación verifica que los
  inputs vivos sigan siendo idénticos al snapshot y reutiliza los bundles ya
  ajustados del benchmark, cambiando solo identidad y hashes del empaquetado;
  no repite preparación, entrenamiento ni hold-out. Queda en
  `ml_models/candidates/` sin tocar Predictor.
  Un botón posterior activa explícitamente la versión completa; las métricas
  son orientativas y no existe ganador ni promoción automática.
- El primer objetivo es `biology_v3`: la candidata y su generación incluyen a
  la vez `core` y `common_idw_plus_physical_state`. Predictor muestra fixed y
  lag de ambos perfiles; no existe un perfil principal oculto.
- La promoción revalida frescura, plan, hashes y carga de todos los bundles,
  guarda journal y copias del registro/descriptor anteriores, instala el batch,
  cambia `active_operational_target`, libera caché y ofrece rollback exacto.
- Primera comparación controlada implementada y ejecutada en HA local:
  - `V3 core`: columnas IDW actuales;
  - `biology_v3/common_idw_plus_physical_state` (`Biology V3+ físico`): mismas
    filas, targets, splits, contratos y estimadores, añadiendo balance hídrico
    y SMI derivados del mismo IDW. Usa 365 días únicamente para inicializar el
    estado físico y conserva la ventana predictiva V3 de 90 días.
- V3+ se materializa de forma separada en entrenamiento e inferencia con el
  mismo contrato de columnas, no incorpora las variables meteorológicas
  extendidas de V4 y ahora declara `operational_eligible=true` junto a V3 core.
  Esa marca significa ejecutabilidad técnica, no aprobación científica. Seleccionarlo
  prepara V3 y la fuente física requerida, pero no V5/V6.
- Los requisitos de entrada (`lookback`, ventana predictiva, estado físico,
  variante de suelo e inputs preparados) están declarados por perfil en el
  registro. El plan para convertir este primer corte en promoción extensible a
  cualquier versión actual o futura está en
  `docs/mushrooms/mushroom-ml-generic-profile-promotion-plan-es.md`.
- `Biology V3` no significa que hoy entren variables directas de huésped,
  bosque o sustrato. Introduce principalmente contratos de muestra/target y
  validación relacionada con floradas; V4–V6 heredan esa línea y añaden otros
  cambios. Por eso comparar versiones completas no aísla causalmente qué
  familia de variables ayudó.
- Ya se comparó el bloque físico conjunto. Solo si aporta mejora
  repetible se abrirán ablaciones balance/SMI y después ventanas V5 30/60/90.

El benchmark conjunto real quedó archivado como
`benchmark_v2_v6_20260818T215411Z`: V3 core y V3+ físico, 9 especies, 216/216
fits correctos, 0 fallos, 864 métricas, 3.328 predicciones hold-out y 22,843989
s acumulados de ajuste. Su snapshot es `sha256:267921ac…` y el SHA-256 del
informe es `e5f8322e…`; `operational_candidate_trained=false`, por lo que no
modificó Predictor.

## Próximo paso

Las fases 1 y 2 quedan validadas localmente. Con autorización explícita se construyó la imagen
`rainmapperha:local-ha-ui` y se recreó únicamente el servicio HA local en
`127.0.0.1:8101`, incluida una segunda reconstrucción local que instaló las
correcciones de selección, alcance y cancelación. La comprobación HTTP muestra
los seis perfiles inicialmente desmarcados y únicamente V3 al solicitar
`biology_v3/core`; no quedó ningún benchmark activo.

El benchmark local real V3 finalizado el 18-08-2026 archivó
`benchmark_v2_v6_20260818T203721Z`: 1 perfil (`Biology V3 core`), 9 especies,
108/108 fits correctos, 0 fallos, 432 métricas y 1.672 predicciones hold-out.
El ajuste sumó 10,498202 s y el job completo duró 2 min 34 s. El informe
verificado tiene identidad `sha256:82c1ec…` y declara
`operational_candidate_trained=false`; por tanto no modificó Predictor. Este
resultado sustituye la duda anterior sobre el coste: un V3 aislado no consume
los 40 minutos observados en la cadena completa.

La corrección posterior de trazabilidad de la fila, acción contextual e
historial está implementada. En aquella validación, el conjunto dirigido pasó
244 pruebas y el smoke completo 921, incluida compilación Python/JS/shell y
`git diff --check`.
La imagen local final `rainmapperha:local-ha-ui`, digest
`sha256:4f38ed3469599fbed950cd6899ea94e66c70fd072824a98f46d4fd3f35d1cc38`,
quedó reconstruida y el servicio volvió a levantarse en `127.0.0.1:8101`. La
comprobación HTTP del informe archivado muestra 108/108 ajustes, 0 fallos, 432
métricas, 1.672 predicciones hold-out y 10,498 s de ajuste, sin acción de
promoción. No se hizo bump,
publicación, instalación en HA real ni cambio del worker normal.

El primer corte de fase 3 está implementado en el worktree. Las pruebas
dirigidas cubren registro, planificación, preparación limitada, soporte
emparejado, runtime trainer y paridad campo a campo entre entrenamiento e
inferencia. En aquella validación el smoke completo pasó 928 pruebas y
`git diff --check`. El benchmark conjunto ya se ejecutó, aunque todavía no se
ha revisado su evidencia por especie y contrato para afirmar si el bloque
físico mejora V3. Con
autorización explícita se reconstruyó únicamente la imagen local
`rainmapperha:local-ha-ui` (digest
`sha256:e93fa688ee83ff63ba598961488ba5470c90f4132c7a0ba02c570a6872ee4867`) y se
recreó `rainmapper-local-rainmapper-ha-ui-1` en `127.0.0.1:8101`. La respuesta
HTML confirma V3+ en español y los siete perfiles sin atributo `checked`.

La fase 4 se incorporó después y el 2026-08-19 se reconstruyó de nuevo solo la
imagen local `rainmapperha:local-ha-ui`, ahora con digest
`sha256:9a8ef34815da5816321bab31bfa49ecf2a5e8fd4ea2621425d9ca2948d843811`.
El contenedor responde desde dentro con HTTP 200; la UI muestra siete perfiles
inicialmente desmarcados. Al abrir el informe conjunto V3/V3+ aparece
`Preparar candidata completa · Biology V3`. No se ha preparado candidata ni se
ha cambiado Predictor. El smoke completo actual pasa 935 pruebas.

## Riesgos y dudas activos

- El corte 2026-08-19 generaliza la autoridad del score: para cada especie,
  perfil y contrato se elige el menor Brier validado que mejora la prevalencia
  entre **todos** los estimadores disponibles, no solo LR/RF. La UI elimina
  «referencia histórica V2», las marcas de sombra y el texto de desacuerdo
  específico LR/RF. V4, V5 y V6 pasan a candidatas técnicamente promocionables
  como versiones completas; la migración del registro convierte instalaciones
  persistentes que aún las guardaban como `proposed` sin alterar la versión V3
  activa ni sus generaciones. V4 hereda la evidencia ecológica V3 y V5/V6 la
  derivan causalmente de raw365 sobre los 90 días anteriores. Esto no cambia las
  conclusiones científicas desfavorables históricas ni implica promoción
  automática. Las pruebas dirigidas y el smoke completo pasan 944 tests. Con
  autorización explícita se reconstruyó únicamente HA local: imagen y
  contenedor ejecutan el mismo digest
  `sha256:ead6e5aad21db2a6f6e432dc89083d8c5bd1c5ce6e2807fc6c8e44b8fe08fcad`.
  El registro persistente conserva V3 activa y migró V4–V6 a `candidate`; la UI
  responde y muestra sus cuatro perfiles operativos completos. Falta la
  revalidación visual del usuario.

- La primera promoción local V3 reveló dos pérdidas de contrato en el Predictor:
  la candidata operativa no transportaba el `quality-catalog.json` del benchmark
  fuente y la comparación no reenviaba a interpretación la evidencia
  `significant_rain_found_90d` calculada por el adaptador. El resultado observable
  era ausencia de Brier y un falso veto de lluvia pese a existir acumulados y
  días desde lluvia significativa. La corrección conserva el catálogo científico
  por hash (con fallback verificado para la generación V3 ya instalada), separa
  metadatos ecológicos de inputs del modelo, elimina el texto V2 fijo y oculta la
  reactivación de una candidata ya promovida. Este contrato queda documentado
  como obligatorio para V4 y versiones futuras. La suite dirigida pasó 28
  pruebas tras la corrección booleana final y el smoke completo 939;
  `git diff --check` quedó limpio. Se reconstruyó
  únicamente `rainmapperha:local-ha-ui` con digest
  `sha256:21f9a1dc2c88709e73e9a4d84dcd6dcbcc459ff9e6f5bcfd40aa455e4b5a84bc`.
  El contenedor local responde HTTP 200 y, dentro del runtime V3 activo, el
  fallback verificado resuelve las 864 entradas del catálogo científico. Una
  consulta real Edulis/Salteguet para 2026-08-20 muestra Brier por estimador,
  lluvia significativa a 4/9 días y compatibilidad ecológica, sin el falso veto.

- La activación local V4 reveló que el mismo síntoma podía reaparecer cuando un
  adaptador añadía otro nivel alrededor de la evidencia ecológica: la tabla
  conservaba probabilidades, Brier y acumulados, pero la interpretación recibía
  el evento como ausente, activaba incompatibilidad ecológica y anulaba el rango.
  La extracción ya recorre de forma genérica todos los mappings anidados de
  `quality`. Una prueba transversal ejercita todas las versiones operativas
  registradas V2–V6 y exige Brier disponible, lluvia reciente, compatibilidad y
  rango final; no hay excepciones por nombre de versión. El smoke completo
  posterior pasa 949 pruebas y `git diff --check` queda limpio. La imagen HA
  local se reconstruyó después con digest
  `sha256:a8d5961b316d19aca2aa41b8f35a7f797c302909879f903f530b3301673f50c8`;
  raíz, Predictor y Workers responden HTTP 200. La validación real posterior
  mostró que el adaptador diario V4 no anidaba esa evidencia: la eliminaba al
  reconstruir `quality`, por lo que el recorrido recursivo no podía encontrarla.
  El adaptador propaga ahora explícitamente los cuatro campos del contrato
  ecológico y la prueba atraviesa la materialización diaria real. Tras 949
  pruebas y `git diff --check`, se reconstruyó únicamente HA local con digest
  `sha256:ed92aa1b2f7ed008324a7010819be65371316da615f5f35d1292d50c6d5f86ec`.
  Una consulta real Edulis/Salteguet del 2026-08-20 devuelve lluvia encontrada,
  búsqueda completa, 9/4 días desde lluvia, `recent_event` y compatibilidad
  ecológica. Falta revalidación visual del usuario.

- La cadena nueva promociona reconstrucción, ML v0 y V2 fixed/lag como una
  unidad. La completitud se deriva del registro activo y se revalida al recibir
  el resultado; V3–V6 ya no se preparan ni entrenan en el camino habitual.
- Un benchmark conserva validez histórica con su snapshot, pero no puede
  promocionarse si observaciones o entradas meteorológicas vivas cambiaron.
- Debe decidirse y versionarse qué constituye una generación operacional
  completa para perfiles futuros; no se promocionan celdas aisladas elegidas
  retrospectivamente.
- El soporte por especie/campaña es pequeño y el mismo hold-out no debe usarse
  indefinidamente para inventar sucesivos ganadores.
- V3 core y V3+ ya son técnicamente elegibles como una única versión completa.
  Esa marca no expresa superioridad científica: la candidata se prepara y la
  versión se activa solo mediante dos decisiones humanas separadas.
- V5/V6 conservan 365 días como control contractual. Separar el spin-up del SMI
  de la ventana predictiva y probar 30/60/90 requiere contratos nuevos.
- La instrumentación por fit/versión/perfil/estimador ya existe y el V3 aislado
  real quedó medido. Todavía falta repetir perfiles más costosos si se quiere
  atribuir el resto de los 40 min históricos de la cadena V2–V6 completa.
- No usar Tailscale, no tocar HA real o worker normal y no manipular históricos
  meteorológicos sin seguir `docs/history-safety.md`.

## Archivos relevantes

- Diseño nuevo:
  `docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`.
- Contratos actuales:
  `docs/mushrooms/mushroom-ml-contract-versions-es.md`,
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md` y
  `mushroom-data/mushroom_ml_version_registry.json`.
- Coordinación/UI: `rainmapper-app/app/web_server.py` y
  `rainmapper-app/app/mushroom_workers_ui.py`.
- Jobs: `rainmapper_core/mushroom_worker_jobs.py`,
  `rainmapper_core/mushroom_worker_service.py` y
  `rainmapper_core/mushroom_local_full_update.py`.
- Plan/training: `rainmapper_core/mushroom_ml_multiversion_plan.py`,
  `rainmapper_core/mushroom_ml_runtime_trainer.py` y
  `rainmapper_core/mushroom_ml_holdout.py`.
- Informe persistente: `rainmapper_core/mushroom_ml_benchmark_reports.py` y
  `rainmapper_core/mushroom_ml_quality_catalog.py`.
- Transporte/promoción:
  `rainmapper_core/mushroom_ml_multiversion_transport.py` y
  `rainmapper_core/mushroom_worker_results.py`.
- UI Predictor: `rainmapper-app/app/mushroom_predictor_ui.py` y
  `rainmapper_core/mushroom_predictor_service.py`.
- Pruebas iniciales: `tests/test_mushroom_worker_jobs.py`,
  `tests/test_mushroom_local_full_update.py`,
  `tests/test_mushroom_ml_multiversion_input_preparation.py`,
  `tests/test_mushroom_ml_multiversion_plan.py`,
  `tests/test_mushroom_ml_multiversion_transport.py`,
  `tests/test_mushroom_ml_benchmark_reports.py`,
  `tests/test_mushroom_ml_quality_catalog.py`,
  `tests/test_mushroom_ml_runtime_trainer.py` y
  `tests/test_web_server_auth.py`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo si hacen falta las prioridades completas.
- Comprobar `pwd`, rama y `git status`; preservar absolutamente todos los
  cambios y ficheros no rastreados.
- Usar Codebase Memory MCP antes de descubrir o cambiar código.
- Mantener actualizaciones de proceso muy breves para conservar tokens.
- No preparar ni publicar releases sin autorización explícita nueva.
