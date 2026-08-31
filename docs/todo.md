# TODO

Prioridades vigentes. El estado inmediato está en `docs/active-context.md`;
este fichero distingue trabajo cerrado de próximas entregas.

## P0 — Unificar el alcance operativo local, HA y worker

Especificación vinculante:
`docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`.

- [x] Reproducir y diagnosticar el fallo real de la cadena completa del
  2026-08-28: 20 min 19 s hasta fallar V2–V6 por una decisión de tuning ausente
  para Cantharellus.
- [x] Demostrar que local y HA real partían de las mismas observaciones, pero
  no del mismo alcance efectivo ni del mismo catálogo instalado.
- [x] Documentar la refactorización estructural y preservar promoción atómica,
  rollback e instalación anterior al fallo.
- [x] Crear un `OperationalTrainingScope` canónico después de agregar episodios
  y aplicar todos los gates científicos; debe incluir especies admitidas,
  excluidas y motivos.
- [x] Sellar ese alcance dentro de un plan/manifiesto serializable único. Local
  debe ejecutar exactamente el plan que recibiría el worker; solo puede variar
  el transporte.
- [x] Obligar a ML v0, preparación, hold-out, tuning, fits, métricas,
  verificación y promoción a consumir la lista sellada, sin volver a descubrir
  especies desde el snapshot. La reconstrucción de features precede por diseño
  al cálculo del scope y conserva el snapshot que este identifica.
- [x] Añadir preflight de cobertura completa del catálogo de tuning antes del
  trabajo pesado y decidir la política científica para una especie elegible
  nueva sin tuning congelado: fallar cerrado con las claves ausentes, sin
  sintetizar ni copiar decisiones implícitas.
- [x] Corregir la carrera/retry de `finish` que dejó un HTTP 409 después de que
  HA ya hubiese aceptado el resultado ML v0.
- [ ] Corregir la telemetría temporal y de progreso de la cadena completa:
  mostrar duración integral desde la pulsación/preparación en HA hasta promoción,
  espera/claim, duración del job remoto y duración de fase como magnitudes
  separadas; persistir el desglose de SoilGrids, GIS, bundle, worker,
  verificación y transición entre jobs. La duración actual pierde la preparación
  al crear/reclamar el job remoto y no suma las pausas entre jobs.
- [ ] Sustituir el porcentaje por fase presentado como total por un progreso
  global monótono. Caso real: V2–V6 pasó de `81 %` en reutilización de inputs a
  `20 %` al construir V3 y luego a `37 %` al construir V5; mientras no se
  corrija, no usar esa columna para estimar avance ni ETA.
- [x] Desacoplar control/progreso del camino de cálculo local: una llamada HTTP
  síncrona de hasta 3 s no debe bloquear cada fichero o callback. Conservar
  cancelación, último progreso coalescido y la espera indefinida solo para la
  entrega de un resultado ya calculado.
- [ ] Añadir métricas de peticiones, bytes, espera de red y cálculo por fase
  para atribuir el coste WAN sin inferirlo de CPU o tráfico agregado.
- [x] Añadir pruebas centinela de 10 filas que agregan a 9 episodios, igualdad
  local/remoto, cobertura de tuning, cancelación, retry, rollback y promoción
  atómica.
- [ ] Validar en laboratorio ambas rutas con los mismos datos, registro y
  catálogo; exigir igualdad de scope, plan, fits, métricas y artefactos, además
  de un total desde pulsación hasta promoción de como máximo 10 minutos. Scope
  e identidades científicas ya coinciden exactamente con los inputs reales;
  faltan comparar fits, métricas y artefactos de dos ejecuciones equivalentes y
  medir el tiempo integral.
- [x] Preparar con autorización HA `0.2.275` y worker local `1.0.24`; publicar
  HA en GHCR y conservar identidad, volumen y cachés del único worker.
- [x] Instalar HA `0.2.275` y ejecutar una validación real completa:
  reconstrucción, ML v0, V2–V6, promoción y Predictor terminaron correctamente.
  La meteorología no cambió porque el scheduled runner no llegó a activarse.
- [x] Publicar la corrección final de identidad científica en HA `0.2.276` y
  reconstruir el worker local `1.0.25`, conservando identidad, volumen y cachés.
- [x] Confirmar la instalación de HA `0.2.276`; no hace falta repetir una
  reconstrucción para la identidad, ya validada directamente con los mismos
  inputs actuales local/HA.
- [x] Diagnosticar antes de otro reentrenamiento el último fallo real de
  `Reconstrucción operativa completa`: terminó al 55 % en 2 min 9 s después de
  que corriera un runner meteorológico. El error fue `name 'HTTPError' is not
  defined` al capturar un rechazo de subida cuyo detalle quedó destruido. El
  histórico sí cambió en seis filas y el runner acabó unos 33 minutos antes; no
  hay causalidad demostrada. Worker `1.0.26` conserva el error HTTP si se repite.

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
- [x] Reproducir y cerrar la divergencia entre la ficha multiversión y la franja
  semanal: hoy la ficha usa los ganadores seleccionados, mientras la franja se
  calcula por una ruta auxiliar de la preferida. Trazar también qué muestran
  exactamente `Esta semana`, `Por especie`, el recommender y `Historial`.
- [x] Añadir al criterio de elegibilidad ROC-AUC `>= 0,55`, además de mejorar
  estrictamente Brier/prevalencia y estar dentro del dominio aceptado. Si ningún
  candidato supera todos los gates, el escenario se abstiene y expone los
  motivos por aplicabilidad, Brier y ROC-AUC.
- [ ] Medir de nuevo, sin navegación concurrente del usuario, el recommender y
  las demás pestañas; confirmar que solo calculan la versión preferida, aplicar
  reutilización/caché donde proceda. Localmente los cambios de especie, zona,
  fecha y versión ya esperan a `Predecir`, la especie actualiza sus zonas sin
  worker y el detalle semanal reutiliza su resultado terminado. En HA real se
  observaron 29,0 s para un recommender frío, 12,0 s para una fecha nueva y
  0,6 s para un resultado exacto reutilizado; falta instrumentar por fases y
  medir de forma controlada el resto de pestañas.
- [x] Persistir y reutilizar en HA resultados Predictor exactos por worker,
  petición normalizada y fingerprint del runtime, verificando tamaño, SHA-256
  y petición embebida; mostrar tiempo total, cálculo y reutilización en la UI.
  En HA real 0.2.271, una repetición exacta informó 0,6 s de trabajo y menos de
  0,1 s de cálculo sin crear un nuevo cálculo científico.
- [ ] Separar y medir los 6–8 s percibidos en una repetición exacta entre
  ingress, transferencia y renderizado del detalle técnico grande. No atribuir
  la causa sin instrumentación.
- [ ] Ejecutar la especificación de optimización del camino frío en
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`:
  agregar primero la telemetría por fase y contadores, después implementar
  caché semántica persistente y acotada, y abordar workspace meteorológico
  común o inferencia por lotes únicamente según la fase dominante medida.
  Objetivos: Recommender frío <=10 s y detalle ya calculado <=1 s, con
  equivalencia contractual y científica completa.
- [x] Implementar y validar localmente el precálculo semanal distribuido definido en
  `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`: todas las
  especies, áreas, siete días, V0 y todas las versiones operativas instaladas;
  SQLite verificado, estado deseado latest-wins, ejecución manual, publicación
  coordinada, lookup en HA, fallback íntegro y trigger asíncrono del runner.
  Cuatro rutas con datos dieron equivalencia científica exacta en local.
- [x] Externalizar del claim las selecciones operativas que superaban 64 KiB,
  servirlas por endpoint autenticado y ligado al claim, y reconstruir el worker
  privado como `1.0.31` sin perder identidad ni volumen.
- [x] Impedir que una revisión pendiente reconstruya repetidamente su plan en
  cada heartbeat; conservar un solo intento por
  `(worker_id, revision, artifact_id)` y mantener en cola el job creado.
- [x] Publicar HA `0.2.284` con margen de presencia de 15 s para heartbeat cada
  5 s y materialización pendiente fuera de la petición heartbeat. Smoke
  definitivo: 1.180 pruebas; digest multiarch verificado en continuidad.
- [x] Instalar HA `0.2.284` y comenzar el E2E real con el worker privado
  `1.0.31`: presencia estable y apertura barata de Workers confirmadas. El
  primer job falló tras 6 min 11 s porque el worker UTC construía desde
  `date.today()` y no desde el `issue_date` sellado; la telemetría síncrona
  además bloqueaba callbacks durante timeouts de red.
- [x] Publicar HA `0.2.285` y reconstruir el worker privado como `1.0.32` con
  fecha anclada al contrato, progreso fraccional, detalle remoto y telemetría
  coalescida en segundo plano. Smoke: 1.181 pruebas; índice multiarch
  `sha256:aa4a1d39bffd501288b0ffb630d85bb8907818cdce3fc25bef3759c87c0c2333`.
- [x] Instalar HA `0.2.285` y repetir el E2E real con worker `1.0.32`. El job
  llegó al 11 % y demostró que consulta-fecha/todas-las-áreas y ayudas internas
  aún usaban el calendario UTC del worker; tras fallar, la revisión aparecía
  incorrectamente `En cola` y podía reintentarse después de reiniciar HA.
- [x] Publicar HA `0.2.286` y reconstruir el worker privado como `1.0.33`:
  todas las rutas internas consumen el `issue_date` sellado y los estados
  terminales de la revisión vigente se conservan sin replanificación. Smoke:
  1.185 pruebas; índice multiarch
  `sha256:57783c36e1a6f6f8fe577f6066676a1a3e2983a80f9df2ddc7639755edfdbc37`.
- [x] Instalar HA `0.2.286` y lanzar el E2E real con worker `1.0.33`. La
  ejecución alcanzó `20.88/143` y 19 % sin repetir el rechazo de fecha que antes
  aparecía al 11 %.
- [ ] Completar ese E2E: medir preparación/cálculo/telemetría/transferencia y
  activación, confirmar SQLite en `/media/rainmapper/predictor_precompute`, hits
  servidos por HA, fallback con selección explícita de ejecutor y ausencia del
  SQLite en el backup.
- [ ] Rediseñar el modal del precálculo para distinguir con lenguaje claro el
  avance global, la etapa 1/3–3/3 y el subpaso científico. El modal actual
  mezcla fracción decimal sobre 143, dos porcentajes, especie/área, fase y dos
  ETA sin explicar su relación; conservar trazabilidad sin exponer jerga como
  `query:` o claves internas como mensaje principal.
- [x] Auditar en solo lectura el backup real de `/share/rainmapper`: ocupa
  1.125 GiB y no contiene batches ML antiguos; el único batch está activo y
  protegido.
- [ ] Corregir, con autorización separada, el ciclo de vida de seis input
  bundles ya completados (179,6 MiB medidos en el montaje real) y retirar el
  TAR legacy del runtime (138 MiB)
  únicamente después de verificar su sustituto en `/media`. No borrar ni
  cambiar retención antes.
- [ ] Perfilar `Building weekly matrix` por especie después del E2E real.
  Optimizar solo el coste dominante medido; objetivo operativo de referencia,
  no gate demostrado, inferior a diez minutos.
- [x] Redactar, revisar contra la arquitectura actual y enlazar en continuidad
  la especificación del precálculo semanal. Quedaron explícitos lookup
  coordinator-first, `artifact_id` frente a SHA-256, leases del runtime,
  recuperación tras reinicio y activación HA→worker.
- [x] Ajustar la vista por especie/todas las áreas para que las abstenciones
  operativas largas envuelvan sin solapar el badge de fiabilidad, incluido el
  layout responsive. Prueba dirigida correcta al cierre de 2026-08-29.
- [x] Unificar la selección por defecto entre el job remoto y el render para
  que el primer clic desde el recommender no muestre un resultado vacío ni
  obligue a repetir `Predecir`.
- [x] Elevar localmente el resultado Predictor a 64 MiB, añadir preflight en el
  worker y timeout de 60 s solo para `finish`, conservando validación, SHA-256,
  externalización y escritura atómica.
- [x] Sustituir la ocultación propuesta de `Consenso estadístico` por un
  veredicto explícito entre familias metodológicas elegibles: alto/moderado/bajo
  según separación, o `sin contraste` cuando solo existe una familia; mostrar
  además el acuerdo interno entre variantes sin contarlo como independencia.
- [x] Revalidar visualmente en todos los caminos iniciales y posteriores a
  `Predecir` los veredictos, criterios de ayuda, espaciado y plegado automático
  de versiones sin algoritmos elegidos.
- [x] Ejecutar pruebas dirigidas finales de selección, abstención, coherencia de
  resumen/detalle y UI; reservar el smoke completo para la entrega relevante.

## P0 — Retención permanente de almacenamiento ML y worker

Especificación vinculante:
`docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`.

- [x] **Gate de instalación real completado.** HA `0.2.266` está instalado
  según confirmación del usuario; el reconciliador real ejecutó
  `mode=apply removed=74 errors=0`, el Predictor funcionó después y la cadena
  operativa completa produjo las cinco versiones sin fallos de ajuste.
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
- [x] Completar integración remota y smoke completo antes del build autorizado:
  1.006 pruebas correctas y `git diff --check`; HA `0.2.265` y worker `1.0.17`
  publicados/reconstruidos sin activar el reconciliado destructivo. El parche
  HA migra de forma respaldada el registro persistente 1.0 que bloqueó el
  arranque correcto de `0.2.264`.
- [x] Revisar la reconciliación real y obtener autorización explícita antes del
  `apply`: el usuario habilitó **Apply ML storage retention** y el arranque
  retiró 74 entradas con cero errores. No hubo borrado manual.
- [x] Instalar la migración y ejecutar en HA real el mantenimiento completo:
  374 observaciones, ocho especies, cinco versiones, 636/636 ajustes y cero
  fallos; promoción y limpieza terminal completadas según la cola persistente.
- [ ] Cerrar la evidencia operativa secundaria sin repetir el entrenamiento:
  confirmar visualmente las cinco versiones y la desaparición del aviso de
  identidad desconocida, registrar tamaños finales de Diagnostics y comprobar
  reutilización de la caché TAR tras reinicio. Probar rollback solo dentro de
  un ensayo explícitamente autorizado y seguro; no bloquear el perfil local de
  rendimiento por esa prueba destructiva.

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

- [ ] Rebasar la optimización de rendimiento sobre el alcance unificado. La
  última cadena real no es una línea base válida de éxito: falló tras 20 min
  19 s por divergencia de scope. La medición local de 548,095 s demuestra que
  el cálculo cabe en el presupuesto, pero no demuestra equivalencia remota.
  El handoff sellado sí quedó observado (`Reusing sealed local inputs`).

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
- [ ] Optimizar el reentrenamiento operativo multiversión después de validar y
  desplegar la generación actual. Seguir este orden y medir cada paso antes de
  avanzar al siguiente:
  1. Perfilar una reconstrucción y reentrenamiento completos con `py-spy` o
     `cProfile`, separando preparación, evaluación hold-out y ajuste de
     artefactos.
  2. Paralelizar de forma acotada los cálculos independientes por
     área/cutoff y los fits de modelos, evitando paralelismo anidado y
     sobreasignación de CPU/memoria.
  3. Reutilizar ventanas meteorológicas, balances y estados de suelo
     compartidos para eliminar cálculos repetidos entre versiones, perfiles y
     contratos.
  4. Vectorizar con NumPy los bucles que el perfil confirme como dominantes y
     volver a medir tiempo, memoria y equivalencia numérica.
  5. Solo si sigue existiendo un núcleo de Python puro dominante, evaluar una
     implementación compilada y acotada (Cython, Numba o extensión C/Rust),
     manteniendo compatibilidad `amd64`/`arm64` y Python 3.11.
- [ ] Reducir a **10 minutos como máximo extremo a extremo** la acción remota
  `Reconstruir y reentrenar operativo` con el M1 Pro y su Docker habitual, sin
  relajar hashes, trazabilidad, cancelación, rollback ni promoción atómica.
  Auditoría real del 2026-08-25 (374 observaciones elegibles, ocho especies y
  las cinco versiones instaladas): tres jobs encadenados consumieron 35 min
  55 s hasta terminar el multiversión — reconstrucción 3 min 30 s, ML v0
  1 min 18 s y multiversión 30 min 56 s — y la promoción enlazada terminó
  aproximadamente 1 min 15 s después. El ajuste observado en UI fue solo de
  unos 2--3 minutos; el tiempo dominante está fuera de los fits.

  Hallazgos confirmados que deben tratarse como un único perfil transversal:

  1. **Transporte de resultados fragmentado:** el lote operativo contiene 636
     artefactos y produjo 642 POST secuenciales para 173,4 MiB. El primer
     fichero recibido quedó fechado a las 00:26:50 y el último a las 00:41:41:
     14 min 51 s de entrega. El JSONL grande de predicciones (86,9 MB) necesitó
     alrededor de 1 min 49 s, mientras que los 636 modelos pequeños consumieron
     12 min 43 s (unos 1,2 s/fichero). El cuello es el coste fijo: `urlopen`
     nuevo, `read_bytes`, validación y un `fsync` por fichero, no el volumen.
     `RainmapperHandler` conserva HTTP/1.0 por defecto, sin conexión persistente.
  2. **Cola sobredimensionada en cada señal de telemetría:**
     `mushroom_worker_jobs.json` medía 5.390.231 bytes y 4.123.442 bytes de su
     representación compacta correspondían a 43 copias de manifiestos de
     runtime. `poll_job`, `update_progress` y
     `update_candidate_promotion_progress` cargan y reescriben toda la cola con
     indentación, `fsync` y `replace`. El worker consulta control cada dos
     segundos, y una publicación puede provocar además otra reescritura de
     progreso; durante un job de media hora esto supone varios GB lógicos de
     escritura aunque cambien unos pocos bytes. También ejecuta la limpieza de
     resultados Predictor en cada escritura.
  3. **La validación/promoción amplifica el mismo patrón:**
     `Validating live inputs (n/64)` publica una actualización por cada una de
     las 52 entradas del snapshot y los 12 ficheros GIS; cada callback vuelve a
     persistir los 5,39 MB de cola. `verify_live_inputs` rehashea además los
     ficheros meteorológicos porque esa llamada usa el valor por defecto
     `verify_weather_file_hashes=True`, aun cuando el contrato ya incluye la
     identidad de la generación meteorológica. La cache GIS sí evita el hash
     profundo cuando conserva la misma identidad de filesystem.
  4. **Verificación repetida de los mismos bytes:** cada fichero se valida al
     recibirlo y `_verified_result` vuelve a hashear todos los declarados;
     después vuelve a hashear los artefactos al recorrer el manifiesto del
     batch. `finalize_result` hace esa pasada al completar el upload y
     `install_verified_result` la repite antes de copiar todo el batch a su
     destino. En el worker, el manifiesto de resultados y la cache de objetos
     vuelven a recorrer/hash-ear los modelos. La seguridad es necesaria, pero
     no todas estas pasadas aportan una frontera de confianza nueva.
  5. **Preparación previa secuencial y sin tiempos persistentes:** los 15 min
     56 s anteriores al primer fichero subido mezclan descarga, preparación y
     fits; hoy no hay marcas que permitan repartirlos con precisión. El
     preparador ejecuta en serie ocho etapas: V3 fija/lag, V4 fija/lag, V5,
     hold-out V2--V5 y hold-out V6. Los monitores releen además el JSONL de
     progreso completo cada 0,5 s. Debe perfilarse por etapa y por
     área/cutoff, no atribuirse todo ese tramo al trainer.
  6. **El patrón no es exclusivo del multiversión:** los resultados de
     reconstrucción y ML v0 usan también un POST y `fsync` por fichero (aunque
     son aproximadamente 10 y 20, respectivamente); el bundle de entrada usa
     un GET por fichero y el probe de transporte aún publica control+progreso
     sin coalescer. El Predictor ya demostró el problema y desactivó su
     telemetría fina porque las rondas HTTP dominaban el cálculo local.

  Orden de implementación y validación:

  1. Añadir cronometraje monotónico persistente por fase y contadores de bytes,
     ficheros, peticiones, hashes, copias y fsync; fijar presupuesto orientativo
     de 2 min reconstrucción, 4 min preparación+fits, 2 min transferencia y
     2 min verificación/promoción, con total duro de 10 min en cache caliente.
  2. Sacar de la cola los manifiestos inmutables repetidos (referencia por
     fingerprint) y separar lease/progreso volátil del historial durable.
     Persistir solo cambios visibles o checkpoints espaciados; consultar
     cancelación sin reescribir y no ejecutar housekeeping en cada tick.
  3. Sustituir los 642 uploads por un paquete efímero determinista y reanudable
     en chunks de 8--16 MiB (o transporte equivalente), conservando el
     manifiesto lógico. HA debe limitar tamaño/recuento, rechazar traversal y
     enlaces, verificar digest antes de extraer en staging y borrar el paquete
     temporal tras promoción/rollback; no debe aumentar backups permanentes.
  4. Sellar el staging tras una única verificación completa y emitir un recibo
     ligado a su manifiesto/digest. Reutilizarlo en instalación, eliminar el
     segundo hash de artefactos dentro de `_verified_result` y copiar/promover
     una sola vez sin debilitar la frontera worker→HA.
     **Implementación local 2026-08-28, aún sin build/despliegue:** los puntos 3
     y 4 están cubiertos para multiversión mediante TAR sin compresión limitados
     a 16 MiB, fallback del fichero grande, validación por miembro y recibos
     ligados a tamaño/digest/device/inode/mtime/ctime. La promoción meteorológica
     usa identidad inmutable y publica ocho checkpoints en vez de 64. Mantener
     abierta la tarea hasta medir HA↔worker real y abordar la cola durable.
  5. Reutilizar inputs preparados por `snapshot_id` + perfiles + versión de
     contrato, compartir cargas/cálculos meteorológicos entre etapas y leer el
     JSONL incrementalmente desde un offset. Solo después paralelizar ramas y
     fits independientes de forma acotada, siguiendo el plan de cinco pasos
     anterior y evitando paralelismo anidado.
  6. Aplicar la misma auditoría a candidate/ML v0, bundles, heartbeats,
     Predictor y benchmark. Validar cache fría/caliente, igualdad contractual y
     numérica, cancelación, retry interrumpido, rollback, ausencia de residuos
     y que HA/Predictor no pierdan capacidad de respuesta durante el proceso.
  Investigado con código, cola y artefactos reales montados el 2026-08-26.
  Entregas A y B implementadas en laboratorio: catálogo operativo congelado y
  workspace meteorológico/suelo compartido. La preparación bajó de 459,101 s
  tras A a aproximadamente 185,4 s tras B; los ocho artefactos operativos son
  semánticamente idénticos y los hold-out V2--V6 son idénticos byte por byte.
  El smoke extremo a extremo local terminó en 8 min 55 s frío y 7 min 54 s
  caliente, con 714/714 fits, cero fallos, reconstrucción equivalente y
  promoción verificada. La puerta local de 10 minutos queda cumplida; la tarea
  continúa abierta hasta medir el camino remoto HA↔worker, donde cola y upload
  todavía pueden añadir coste. Evidencia completa en
  `docs/reports/operational-rebuild-10m-lab-2026-08-26.md`.
- [x] Terminar y validar localmente la autocura SoilGrids previa al snapshot
  operativo. Corrige la inicialización cuando falta `manifest.json`, crea una
  fase persistente/cancelable y degrada por microárea sin bloquear el
  reentreno. El proceso completo reparó 4/4 pendientes en 14,539 s, sin red ni
  avisos, y dejó 63/63 microáreas completas antes del snapshot. Pasan 1.056
  pruebas; ver `docs/mushrooms/mushroom-soilgrids-autocure-spec-es.md`.
- [x] Medir el proceso local completo con la imagen reconstruida y los 396
  registros elegibles. Terminó en 548,095 s frente a la línea base fresca de
  706,503 s (−158,408 s; −22,4 %), con 714/714 fits, cero fallos y generación
  completa activa. La caché registró 204 matrices, 510 reutilizaciones y
  72.139.352 bytes. SoilGrids reparó 4/4 pendientes en 14,539 s y dejó 63/63
  completas. La instalación/promoción atómica terminó en 3,270 s. Evidencia:
  `diagnostics/operational-performance/6uCH9V-0EoMEf0SC.json` y batch
  `local_operational_20260827T225123Z`.
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
