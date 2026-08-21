# TODO

Prioridades vigentes. El estado inmediato está en `docs/active-context.md`;
este fichero distingue trabajo cerrado de próximas entregas.

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

## P0 — Correcciones y features tras release 0.2.262 (worktree, sin publicar)

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
- [ ] Ejecutar en vivo el benchmark V4 (HA local o worker) para confirmar el
  fix de elegibilidad de especies.
- [ ] Ejecutar el benchmark científico completo de V5w/V6w para confirmar
  que desaparecen los fallos de convergencia.
- [ ] Commit, push, bump y publicación de todo lo anterior — pendiente de
  autorización explícita.

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

## P1 — Promoción genérica desde benchmark

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
- [ ] Ejecutar candidata, promoción, cuatro salidas fixed/lag y rollback desde
  la UI.
- [x] Hacer que el entrenamiento habitual resuelva dinámicamente todos los
  perfiles de la versión promovida.
- [ ] Para V4–V6, declarar qué conjunto completo de perfiles es técnicamente
  operativo antes de habilitarlo. V3 y V3+ ya son elegibles conjuntamente;
  V4–V6 todavía no.

## P1 — Varias versiones ML instaladas a la vez (diseño acordado 2026-08-20, sin implementar)

- [ ] Implementar `installed_generation_id` independiente por versión (no
  degradar las demás al activar una).
- [ ] Reconvertir el puntero único actual en `preferred_version_id`
  (solo valor por defecto, sin frescura ni reentrenamiento).
- [ ] Predictor: resolver el batch de cada versión instalada directamente por
  su `batch_id`, sin depender de un único `runtime-batch.json` global; el
  selector de versiones decide qué se calcula (nunca todas por defecto).
- [ ] Mantener benchmark→preparar candidata→activar como único camino para
  instalar o refrescar una versión con evidencia comparativa; sin atajos de
  reentrenamiento silencioso para V3/V4/V5w/V6w.
- [ ] Rollback por versión, sin restaurar el registro entero ni un
  descriptor único.
- [ ] Resolver la migración del estado ya instalado hoy (registro y
  `runtime-batch.json` actuales) antes de tocar código.
  Diseño completo, hechos verificados y alternativas descartadas en
  `docs/mushrooms/mushroom-ml-multi-version-installation-design-es.md`. Glosario
  de vocabulario (versión/perfil/modelo/generación) en la sección
  "Vocabulario" de `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.

## P2 — Ventanas y coste científico

- [x] Conservar V5/V6-365 como controles reproducibles — 2026-08-19: en vez de
  esto se retiraron a `status: reference` (nunca se borran, sus benchmarks
  archivados siguen siendo válidos); ver `docs/decisions.md`.
- [x] Separar el spin-up necesario para SMI de la ventana predictiva —
  2026-08-19: `biology_v5_windowed_raw_weather` y
  `biology_v6_windowed_smooth_hierarchical`, 3 perfiles 30/60/90 días cada
  una, balance/SMI compartido con calentamiento de 365 días sin cambios.
- [x] Evaluar V5-30/60/90 y V6-30/60/90 sobre las mismas filas y splits —
  2026-08-19: implementado como perfiles que compiten dentro de cada versión;
  falta ejecutar el benchmark real y revisar sus métricas (ver pendiente
  nuevo abajo).
- [ ] Ejecutar el benchmark científico completo (todas las especies/contratos)
  de `biology_v5_windowed_raw_weather` y `biology_v6_windowed_smooth_hierarchical`
  con datos reales y revisar si alguna ventana (30/60/90) domina por
  especie/contrato. Verificación parcial 2026-08-19 con datos reales locales:
  reducir la ventana sí mejora la convergencia de
  `sparse_group_logistic_raw365_v1` (p.ej. `amanita_caesarea` converge en
  60/90d pero no en 30d), pero `lactarius_deliciosus` sigue sin converger en
  las 3 ventanas (30/60/90) — no es un problema de dimensionalidad en su
  caso, requiere investigación aparte. V6 no mostró ningún fallo de
  convergencia en la muestra probada.
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

## P2 — Worker multicoordinador

- [x] Documentar el diseño en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- [ ] Implementar migración atómica de asociaciones, máximo configurable,
  heartbeats independientes, slot global, arbitraje justo y aislamiento por
  coordinador/job.
- [ ] Probar primero con dos HAs locales aislados. No modificar el worker M1 ni
  HA reales sin autorización.

## P2 — Datos y meteorología

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
