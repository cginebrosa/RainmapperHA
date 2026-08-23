# TODO

Prioridades vigentes. El estado inmediato está en `docs/active-context.md`;
este fichero distingue trabajo cerrado de próximas entregas.

## P0 — Estabilizar Predictor multiversión y coherencia científica

- [x] Migrar el registro local a `installed_generation_id` independiente por
  versión y `preferred_version_id` como valor operativo por defecto.
- [x] Adaptar resolución de batches, instalación, promoción, rollback y
  regeneración conjunta de V2/V3/V4/V5w/V6w.
- [x] Regenerar e instalar localmente las cinco versiones y seleccionar V4 como
  preferida, sin despliegue real ni release.
- [x] Hacer que `Consultar fecha` compare las versiones marcadas, identifique
  algoritmo-versión por escenario fixed/lag y conserve la auditoría completa
  (Brier, delta, ROC-AUC, soporte, evidencia y aplicabilidad), ayudas y franja
  semanal.
- [ ] Reproducir y cerrar la divergencia entre la ficha multiversión y la franja
  semanal: hoy la ficha usa los ganadores seleccionados, mientras la franja se
  calcula por una ruta auxiliar de la preferida. Trazar también qué muestran
  exactamente `Esta semana`, `Por especie`, el recommender y `Historial`.
- [x] Añadir al criterio de elegibilidad ROC-AUC `>= 0,55`, además de mejorar
  estrictamente Brier/prevalencia y estar dentro del dominio aceptado. Si ningún
  candidato supera todos los gates, el escenario se abstiene y expone los
  motivos por aplicabilidad, Brier y ROC-AUC.
- [ ] Medir de nuevo, sin navegación concurrente del usuario, el recommender y
  las demás pestañas; confirmar que solo calculan la versión preferida, aplicar
  reutilización/caché donde proceda y mostrar overlay de carga en toda
  recomputación provocada por cambiar la preferida.
- [x] Sustituir la ocultación propuesta de `Consenso estadístico` por un
  veredicto explícito entre familias metodológicas elegibles: alto/moderado/bajo
  según separación, o `sin contraste` cuando solo existe una familia; mostrar
  además el acuerdo interno entre variantes sin contarlo como independencia.
- [ ] Revalidar visualmente en todos los caminos iniciales y posteriores a
  `Predecir` los veredictos, criterios de ayuda, espaciado y plegado automático
  de versiones sin algoritmos elegidos.
- [ ] Ejecutar pruebas dirigidas finales de selección, abstención, coherencia de
  resumen/detalle y UI; reservar el smoke completo para la entrega relevante.

## P0 — Retención permanente de almacenamiento ML y worker

Especificación vinculante:
`docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`.

- [ ] **No cerrar este bloque hasta que esté implementado, instalado en HA real
  y probado allí.** Una implementación o validación exclusivamente local no
  completa la tarea.
- [x] Implementado localmente: mover la caché TAR del runtime remoto desde
  `ml_models/.predictor-runtime-archives` a
  `/media/rainmapper/runtime-cache/predictor-runtime-archives`, con permisos
  privados, configuración explícita, fallback local seguro y sin retorno
  silencioso a `/share`.
- [x] Implementado localmente: auditor/reconciliador idempotente con modo `dry-run` y modo
  `apply` separado para bundles, resultados privados, staging, huérfanos y
  trabajos terminales; conservar resumen y motivo de cada decisión.
- [x] Implementado localmente: retirar con identidad validada los
  `ml_models/candidates` y `promotion-history` del flujo legacy de activación
  manual desde benchmark.
- [x] Implementado localmente: construir el conjunto de referencias vivas y
  podar únicamente generaciones y batches no protegidos por una generación
  instalada.
- [x] Implementado y probado localmente: reducir `.worker-promotion-backups` a una copia de rollback y demostrar la
  restauración correcta por versión.
- [x] Implementado localmente: todo benchmark nuevo pasa inmediatamente a
  `evidence_only`, con informe, hold-out, calidad e identidad, sin ruta de
  preparación/activación operativa.
- [x] Implementado localmente: acotar los payloads completos del Predictor a últimos 10 o 24 h,
  retirando atómicamente sus referencias y mostrando `detalle expirado` sin
  romper el historial ligero de 50 jobs.
- [x] Implementado localmente: exponer en Diagnostics tamaños, categorías, referencias protectoras,
  huérfanos, expirados, TAR vigente, último reconciliado y espacio recuperable.
- [x] Ratificado e implementado localmente: conservar 24 horas los resultados
  pesados de ejecuciones operativas fallidas, canceladas o interrumpidas; el
  resumen ligero permanece en la cola.
- [x] Consolidar las pruebas dirigidas finales de rutas/permisos, integridad,
  mantenimiento autopromocionado, poda legacy, `evidence_only`, expiración y
  dry-run idempotente: 312 pruebas correctas.
- [x] Ejecutar `git diff --check` sobre el worktree completo en el cierre
  documental del 2026-08-23: correcto.
- [ ] Completar integración remota y smoke completo antes de cualquier build
  autorizado; repetir `git diff --check` si después cambia el worktree.
- [ ] Ejecutar en HA real el `dry-run`, revisar el informe con el usuario y
  detenerse para autorización explícita antes de cualquier `apply` destructivo.
- [ ] Tras autorización, instalar la implementación, aplicar la migración,
  verificar las cinco generaciones V2/V3/V4/V5w/V6w, probar predicción fría y
  caliente en el worker, reinicio/reutilización del TAR, rollback, Diagnostics y
  tamaños finales; documentar la evidencia observada antes de marcar completado.

## P1 — Auditoría de deuda y código obsoleto

- [ ] Después de cerrar la retención, auditar el código completo por rutas
  legacy, flags sin consumidor, adaptadores monoversión, duplicaciones y parches
  acumulados. Hacer inventario con referencias/call paths antes de borrar y
  separar esa limpieza del despliegue de almacenamiento actual.

## P0 — Separar entrenamiento operativo y benchmark científico

- [x] Documentar la propuesta, UI objetivo, promoción y entrega por fases en
  `docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`.
- [x] Acordar que la separación no cambia el V2 operativo: seguirá activo hasta
  que el usuario promocione explícitamente una generación compatible.
- [x] Acordar dos acciones principales: `Reconstruir y reentrenar operativo` y
  `Ejecutar benchmark científico`; `Ver comparación` será contextual al job.
- [x] Mapear con Codebase Memory la cadena externa y
  `mushroom_local_full_update`, incluidos planificación, transporte,
  instalación, promoción, rollback y UI.
- [x] Introducir identidades separadas para job operativo y benchmark.
- [x] Resolver el plan operativo desde la generación activa; inicialmente debe
  producir todo V2 fixed/lag requerido por el Predictor.
- [x] Retirar V3–V6 de la reconstrucción habitual sin borrar sus contratos,
  generaciones ni capacidad de reproducción.
- [x] Mantener el job V2–V6 actual como benchmark manual independiente, sin
  promoción automática.
- [x] Añadir tests que demuestren continuidad del V2 instalado, completitud,
  frescura, fallo/rollback y paridad entre worker y ejecutor HA local.
- [x] Adaptar UI y labels `en/es/ca` solo después de cerrar el backend.
- [x] Ejecutar pruebas dirigidas, smoke completo y `git diff --check`.
- [x] Detenerse antes de release y pedir autorización explícita.

## P0 — Correcciones y features tras release 0.2.262 (publicadas en 0.2.263)

- [x] Corregir elegibilidad de especies duplicada entre HA local y worker
  (`eligible_training_species` pública, reutilizada en
  `create_mushroom_ml_multiversion_job`).
- [x] Implementar perfiles de ventana predictiva 30/60/90 días en V5/V6,
  retirando raw365/smooth-365 a `status: reference`.
- [x] Corregir bug crítico: `predict_bundle` no aplicaba el preprocesador
  suave a V6 windowed (`runtime_model_incompatible` en vivo).
- [x] Añadir botón "Borrar" al historial de benchmarks (borrado real de
  disco, con confirmación).
- [x] Eliminar la redundancia de `haversine_km` en `mushroom_weather_idw.py`
  (rendimiento).
- [x] Ejecutar en vivo el benchmark V4 por HA local: 216/216 fits, 0 fallos.
  La ruta específica disparada desde el worker real sigue pendiente y aparece
  en `docs/active-context.md`.
- [x] Ejecutar el benchmark científico completo de V5w/V6w: 174/174 fits,
  0 fallos; `lactarius_deliciosus` converge en las tres ventanas y 90 días
  domina en el benchmark observado.
- [x] Commit, push, bump y publicación de todo lo anterior en HA `0.2.263`;
  el worker local está reconstruido como `1.0.16`.

## P1 — Informe persistente y benchmark seleccionable

- [x] Persistir selección, snapshot, plan, métricas, predicciones hold-out y
  artefactos de cada benchmark.
- [x] Medir duración por fit, versión, perfil y estimador. Falta ejecutar un
  benchmark nuevo para atribuir los 40 minutos observados con esta telemetría.
- [x] Añadir `Ver comparación` e historial de benchmarks.
- [x] Mostrar por especie/contrato/horizonte/estimador Brier, prevalencia,
  delta emparejado, ROC-AUC, calibración, soporte, fallos y duración.
- [x] No crear Brier medio entre especies ni declarar un ganador universal.
- [x] Permitir seleccionar versiones/perfiles compatibles sin que el benchmark
  modifique el Predictor.
- [x] No preseleccionar perfiles, conservar la selección lanzada y evitar que un
  benchmark V3 prepare o evalúe V4–V6.
- [x] Añadir cancelación cooperativa del benchmark HA local.
- [x] Conservar en la fila terminada los perfiles exactos y contadores del
  informe; usar `Ver informe` para uno, `Ver comparación` para varios y
  refrescar el historial al terminar.

## P1 — V3 physical / V3+

- [x] Registrar un perfil/feature set nuevo; no modificar los bundles V3 core.
- [x] Mantener idénticas filas, targets, splits, contratos y estimadores de V3.
- [x] Añadir únicamente balance hídrico y SMI derivados causalmente del mismo
  IDW, con paridad entrenamiento/inferencia.
- [x] Ejecutar en HA local la comparación real V3 core frente a V3+ físico
  sobre soporte emparejado: 216/216 fits correctos y 0 fallos.
- [ ] Solo si el bloque físico mejora repetidamente, comparar después
  `+balance`, `+SMI` y `+balance+SMI`.

## Histórico retirado — Promoción genérica desde benchmark

Este flujo pertenecía al diseño anterior. La UI, handlers, módulo de promoción,
candidatos e historial persistente se retiran: un benchmark solo produce
evidencia y cualquier cambio operativo entra por el mantenimiento completo.

- [x] Documentar el contrato genérico de perfil, candidata, generación completa,
  gates y rollback en
  `docs/mushrooms/mushroom-ml-generic-profile-promotion-plan-es.md`.
- [x] Materializar en código qué artefactos constituyen una generación
  operacional completa para cualquier perfil elegible.
- [x] Exigir `operational_eligible`, integridad, compatibilidad, paridad y
  entradas vivas coincidentes.
- [x] Añadir promoción humana explícita, transaccional y con rollback desde el
  informe; nunca promocionar una celda aislada elegida retrospectivamente.
- [x] Implementar el primer objetivo como versión completa `biology_v3`, con
  V3 core y V3+ físico instalados y visibles conjuntamente en Predictor.
- [x] Reconstruir HA local con autorización y validar que el informe V3/V3+
  ofrece `Preparar candidata completa`.
- [x] Ejecutar candidata y promoción V3 desde la UI y comprobar sus perfiles
  fixed/lag en Predictor.
- [x] Cancelado por retirada de la ruta: ya no existe rollback de versión desde
  la UI de benchmarks.
- [x] Hacer que el entrenamiento habitual resuelva dinámicamente todos los
  perfiles de la versión promovida.
- [x] Declarar los conjuntos completos técnicamente operativos: V4 tiene
  `extended_weather` + `climatic_balance`; V5w y V6w tienen sus tres perfiles
  30/60/90. El registro vigente marca todos esos perfiles como
  `operational_eligible`; las V5/V6 legacy permanecen inelegibles.

## P1 — Varias versiones ML instaladas a la vez (implementación local; estabilización pendiente)

- [x] Implementar `installed_generation_id` independiente por versión (no
  degradar las demás al activar una).
- [x] Reconvertir el puntero único actual en `preferred_version_id`
  (solo valor por defecto, sin frescura ni reentrenamiento).
- [x] Predictor: resolver el batch de cada versión instalada directamente por
  su `batch_id`, sin depender de un único `runtime-batch.json` global; el
  selector de versiones decide qué se calcula (nunca todas por defecto).
- [x] Reemplazar benchmark→preparar candidata→instalar por dos flujos: benchmark
  científico `evidence_only` para evaluar cambios de versión/perfil/feature/
  estimador/contrato y mantenimiento completo que reentrena las versiones
  instaladas seleccionadas y produce evidencia hold-out sincronizada.
- [x] Retirar el rollback manual por versión desde benchmarks. Conservar solo
  rollback transaccional durante la instalación y el backup más reciente del
  rebuild completo.
- [x] Resolver la migración del estado instalado local (registro y
  `runtime-batch.json` actuales) antes de tocar código.
- [ ] Incorporar al manifiesto el vector de revisiones acordado
  (`observations`, generación/manifiesto meteo, sites, estaciones, catálogos,
  GIS y contrato) y actualizarlo atómicamente desde cada escritor autorizado.
- [ ] Separar comprobación rápida de vigencia y auditoría profunda: Predictor,
  promoción y cambio de preferida comparan revisiones y avisan; no recorren ni
  rehashean todos los datasets. La auditoría explícita conserva hashes
  completos e integridad.
- [ ] Implementar caché meteorológica persistente por digest en el worker y
  transferencia incremental con contadores de objetos/bytes reutilizados y
  descargados. Probar corrupción, cambio de manifest, objeto ausente y
  limpieza acotada antes de usarla fuera del laboratorio.
- [ ] Revalidar el gate de inputs vivos tras la migración multiversión:
  mantener una comprobación rápida no bloqueante para uso diario y reservar
  hashes profundos para ingestión, instalación y auditoría explícita. Confirmar
  contra el código actual qué parte ya existe antes de cerrar esta tarea.

## P2 — Ventanas y coste científico

- [x] Sacar V5/V6-365 del circuito operativo — 2026-08-19: las definiciones
  `biology_v5_raw_weather_discovery` y
  `biology_v6_smooth_hierarchical` pasaron a `status: reference`; sus
  sustitutas operativas son las variantes windowed 30/60/90 y sus benchmarks
  archivados siguen siendo evidencia histórica válida; ver
  `docs/decisions.md`.
- [ ] Retirar definitivamente las definiciones V5/V6 no-windowed de 365 días:
  eliminar sus entradas del registro, adaptadores y ramas de compatibilidad y
  actualizar las pruebas que aún las mantienen. Antes, demostrar que ninguna
  generación instalada, puntero activo/preferido, manifiesto o ruta de runtime
  las referencia. La tarea no autoriza borrar informes de benchmark históricos:
  su conservación o migración debe decidirse y documentarse por separado.
- [x] Separar el spin-up necesario para SMI de la ventana predictiva —
  2026-08-19: `biology_v5_windowed_raw_weather` y
  `biology_v6_windowed_smooth_hierarchical`, 3 perfiles 30/60/90 días cada
  una, balance/SMI compartido con calentamiento de 365 días sin cambios.
- [x] Evaluar V5-30/60/90 y V6-30/60/90 sobre las mismas filas y splits —
  2026-08-19: implementado como perfiles que compiten dentro de cada versión;
  la ejecución real completa y su resultado quedan registrados en el punto
  siguiente.
- [x] Ejecutar el benchmark científico completo con datos reales de
  `biology_v5_windowed_raw_weather` y
  `biology_v6_windowed_smooth_hierarchical` — 2026-08-21: 6 perfiles,
  9 especies, 174/174 fits y 0 fallos. `lactarius_deliciosus` converge en las
  tres ventanas y 90 días domina claramente para esa especie en la ejecución
  observada. Esto confirma convergencia, no un ganador universal por versión.
- [ ] Investigar si recalcular balance/SMI de forma independiente por
  ventana (en vez de compartirlo entre las 3, como se implementó ahora)
  aísla mejor la señal de cada ventana — pendiente explícito, no implementado.
- [ ] Mantener estos experimentos fuera de la reconstrucción habitual.
- [ ] No ensayar ensemble salvo que se materialice y supere al mejor miembro
  individual por especie y contrato.

## P2 — Rendimiento predictor y entrenamiento

- [x] Perfilar una consulta real del Predictor y un benchmark real completo
  ante la pregunta de reescribir el kernel en C — 2026-08-20: no se reescribe
  nada en C (sklearn/NumPy ya delegan en BLAS/LAPACK); se elimina la única
  redundancia fácil de bajo riesgo encontrada (`haversine_km` recalculado dos
  veces por estación en `mushroom_weather_idw.py`). Ver `docs/decisions.md`.
- [ ] Perfilar en detalle la fase "preparación de inputs compartidos /
  evaluación de filas hold-out" de un benchmark científico completo — es la
  fase que domina el tiempo de reloj (varios minutos), no el ajuste de los
  modelos en sí (suma de fits medida en manifiestos: segundos, no minutos).
  No perfilado todavía.
- [ ] Evitar reconstrucción redundante del snapshot del coordinador entre
  jobs encadenados de "Reconstruir y reentrenar operativo": el paso 1→2
  (`create_mushroom_ml_train_job`, `web_server.py:12937-13009`) ya es barato
  (solo traspasa `features.json`+`known_sites.json`), pero el paso 1→3
  (`create_mushroom_ml_multiversion_job`, `web_server.py:13235-13252`)
  reconstruye desde cero con `mushroom_rebuild_snapshot.create_snapshot` un
  snapshot casi idéntico al del paso 1 (rehash+copia de `observations.json`,
  `reference_catalogs.json`, `gis_mappings.json`, `registry.json`,
  `known_sites.json`, `stations.txt` y cada partición meteo), sin
  comprobar si ya es el mismo. El dataset GIS y la transferencia de red del
  histórico meteo ya están deduplicados (`mushroom_worker_dataset_cache.py`,
  `mushroom_worker_transport.py:416-458`); falta extender ese mismo patrón
  de fingerprint al *bundling* del coordinador. No es el cuello de botella
  principal hoy (I/O de disco + rehash, no transferencia de red), pero
  crecerá con el histórico meteo. El rehash de origen no es necesario para
  ficheros sin cambios: `_copy_snapshot_file`
  (`mushroom_rebuild_snapshot.py:213`) rehashea siempre origen+destino sin
  condición; el dataset GIS ya resuelve esto con `gis_file_records()`
  (línea 132) cacheando el hash por identidad de filesystem (tamaño +
  `mtime_ns`/`ctime_ns`/inodo) y solo rehasheando si cambia — mismo patrón
  aplicable a particiones meteo, que son inmutables salvo la del año en
  curso. El rehash del destino tras copiar sí es una comprobación de
  integridad legítima; si no hace falta copiar (fichero sin cambios),
  bastaría un `os.link` en vez de `shutil.copy2` + rehash. El coordinador
  corre en una RPi4 (almacenamiento limitado): cada `shutil.copy2` sin
  cambios es escritura real evitable, no solo coste de CPU — motivo
  adicional para priorizar esto si el histórico meteo sigue creciendo.
  Investigado 2026-08-22, no implementado.

## P2 — Worker multicoordinador

- [x] Documentar el diseño en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- [ ] Implementar migración atómica de asociaciones, máximo configurable,
  heartbeats independientes, slot global, arbitraje justo y aislamiento por
  coordinador/job.
- [ ] Probar primero con dos HAs locales aislados. No modificar el worker M1 ni
  HA reales sin autorización.

## P2 — Datos y meteorología

- [x] Parche mínimo `ready-to-upload-root-fix` instalado en HA y raíz
  `20260823T003617919308Z-58903f62a763` verificada íntegramente. El runner
  manual superó `archive pending before update` y creó la hija válida
  `20260823T004654212246Z-59a50ee60e80`, enlazada a esa raíz y verificada con
  todos sus objetos.
- [x] Añadir `rainmapper_core.weather_history_rebase` y pruebas dirigidas para
  convertir de forma verificada e idempotente una generación activa en raíz
  autosuficiente sin copiar los objetos Parquet.
- [ ] Corregir `_BoundedTableWriter` antes de otro backfill masivo para que no
  materialice grupos Parquet de 128 filas; conservar 8.192 como granularidad
  contractual y demostrar igualdad lógica, hashes y rendimiento.
- [ ] Perfilar y reducir el post-drain meteorológico observado (2 min 14 s en el
  runner real del 2026-08-23) sin debilitar archivo, poda ni verificación.
- [ ] Incorporar las cuatro salidas negativas recientes cuando la plataforma
  esté alineada y crear un snapshot nuevo; no sobrescribir
  `mushroom-ml-snapshot-20260816`.
- [ ] Validar en producción la autocuración meteorológica en una entrega
  independiente.
- [ ] Revisar el umbral especial de soporte IDW de lluvia.
- [ ] Corregir el matching geológico por subcadena (`gres`/`negres`) antes
  de usar esos proxies.

## P3 — Integridad y privacidad

- [ ] Revisar por separado la privacidad de
  `mushroom-data/mushroom_observations.json`, rastreado en el repositorio.
- [ ] Añadir sanity checks confirmables para temporada, altitud y primera
  observación especie-área/microárea.
- [ ] Auditar identificaciones automáticas antiguas potencialmente
  contaminantes.

## Trabajo cerrado que condiciona el P0

- [x] V2 usa meteorología IDW común; el comparador legado de estación única ya
  no suplanta su tarjeta.
- [x] MapLibre cuenta ceros finitos en el soporte IDW y excluye N/A.
- [x] V5/V6 v2 consumen IDW, ET0, balance y SMI con paridad de inferencia.
- [x] El worker reutiliza por SHA-256 los modelos que acaba de entrenar y evita
  volver a descargar el runtime completo.
- [x] `lag_event` operativo vuelve a cubrir h1..h7 sin multiplicar fits.
- [x] HA `0.2.261` fue publicada y worker privado local `1.0.14` construido.
- [x] El batch revalidado `local_v2_v6_20260818T162939Z` contiene 432
  artefactos de 436 fits planificados y cuatro fallos V5.

## Riesgos

- No basta con eliminar V2–V6 de la cadena actual: debe seguir construyéndose
  el conjunto completo que necesita el V2 operativo.
- Un benchmark antiguo sigue siendo auditable, pero no promocionable si sus
  entradas ya no coinciden con las vivas.
- El soporte por especie/campaña es pequeño; los rankings son diagnósticos.
- Preservar todos los cambios, datos, cachés y ficheros no rastreados.
- No usar Tailscale, tocar HA real/worker normal ni publicar releases sin
  autorización explícita.
