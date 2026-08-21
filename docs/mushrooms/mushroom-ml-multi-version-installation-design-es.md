# Varias versiones ML instaladas a la vez — diseño propuesto

Estado: **DISEÑO PROPUESTO, NO IMPLEMENTADO.** Discutido y acordado con el
usuario el 2026-08-20. No tocar código a partir de este documento sin
autorización explícita adicional.

Vocabulario (versión, perfil, estimador, modelo, generación, batch): ver
`docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.

## Motivación

Hoy solo puede haber una versión operativa "activa" a la vez. Activar una
versión completa nueva (V3, V4, o las V5/V6 windowed nuevas) sustituye a la
anterior por completo, tanto en el registro como en el runtime. El usuario
quiere: añadir observaciones, refrescar las versiones que le interese, y ver
cuál de ellas ajusta mejor la predicción — no mantener un historial de
generaciones de cada versión. Necesita poder tener varias versiones
instaladas simultáneamente, elegir cuál es la preferida por defecto en el
Predictor, cambiarla cuando quiera, y decidir explícitamente cuáles
participan en una consulta concreta — sin que el coste de una consulta
normal crezca por tener más versiones instaladas, y sin acumular nada sin
límite.

## Estado actual verificado (no supuesto — comprobado en código el 2026-08-20)

- `mushroom_ml_multiversion_transport.py::install_verified_result` escribe un
  **único** fichero `models_root/runtime-batch.json`, sobrescrito con
  `os.replace` cada vez. Lo usan tanto el reentrenamiento V2 habitual
  (`mushroom_local_full_update.py::run_local_full_update`, línea ~921) como
  `mushroom_ml_version_promotion.py::promote_candidate` para cualquier
  versión completa. No hay ningún slot separado para V2: comparten
  exactamente el mismo mecanismo y fichero.
- `mushroom_predictor_runtime.py:77` lee ese mismo fichero único como "el"
  manifest de runtime a servir.
- `mushroom_ml_version_registry.py::transition_active_generation` (línea
  ~538-545) pone explícitamente `status: "reference"` a la versión
  previamente activa y `status: "active"` a la nueva, además de actualizar
  el único puntero `active_version_id`/`active_operational_target`. Es doble
  bloqueo: registro y fichero.
- Los directorios de batches ya ajustados (`ml_models/batches/<batch_id>/`)
  **nunca se borran** al promocionar una versión nueva — solo cambia el
  puntero de cuál se lee.
- Cada versión ya guarda en su propio `generations[]` qué `batch_id`
  corresponde a cada generación registrada (`append_generation`,
  `mushroom_ml_version_registry.py`). Hoy esa lista puede crecer sin límite.
- Hay dos comprobaciones de frescura contra datos vivos actuales
  (`mushroom_rebuild_snapshot.verify_live_inputs(..., verify_weather_file_hashes=True)`):
  una en `mushroom_local_full_update.py::run_local_operational_candidate`
  (al preparar la candidata) y otra en
  `mushroom_ml_version_promotion.py::promote_candidate` (al activarla,
  líneas 75-92). Ambas existen para que la evidencia de hold-out (Brier,
  ROC-AUC, calibración) mostrada siga correspondiendo exactamente a los
  datos con los que se entrenó lo que se está instalando.
- No existe ninguna comprobación de frescura en el camino de predicción
  (`mushroom_ml_runtime_inference.py::predict_bundle` /
  `mushroom_ml_runtime_features.py::build_runtime_features`). Un modelo ya
  instalado se puede seguir usando indefinidamente para predecir sin
  volver a verificar nada.

## Hallazgo empírico 2026-08-20 — la evidencia mostrada puede quedar desincronizada del modelo instalado

Comprobado directamente sobre datos reales en `docker-data/mushroom-data/`,
no deducido:

- El batch realmente instalado tras pulsar "Reconstruir y reentrenar
  operativo" (`runtime-batch.json`, `batch_id: local_operational_...`) tiene
  `quality_catalog: null` — el reentrenamiento rápido **no genera ninguna
  evidencia de hold-out propia** (ni Brier, ni ROC-AUC, ni calibración).
- El registro (`active_operational_target`) seguía apuntando a una
  generación distinta, instalada antes mediante benchmark → preparar
  candidata → activar, con su propio `source_benchmark_batch_id`.
- `mushroom_ml_multiversion_comparison.py::_load_quality_catalog` cae de
  vuelta (fallback) a la evidencia de esa generación anterior cuando el
  batch activo no tiene la suya propia. El Predictor sigue mostrando Brier/
  ROC-AUC de un benchmark antiguo, con fechas de corte que no corresponden
  al modelo que realmente se usa para predecir ahora — sin ningún aviso de
  que la evidencia mostrada está desincronizada.
- Confirma que ROC-AUC/Brier de hold-out **solo** los genera el camino de
  benchmark (con su split train/test real); el reentrenamiento rápido nunca
  los produce, para ninguna versión.

## Alternativas descartadas explícitamente durante esta discusión

- **Reentrenamiento rápido (sin hold-out) para cualquier versión instalada,
  dejando el circuito de benchmark→preparar→activar como único camino
  para refrescar evidencia.** Descartada tras el hallazgo empírico anterior:
  obligar a repetir el circuito completo de 3 pasos cada vez que se añaden
  observaciones, para cada versión, es la complejidad exacta que el usuario
  pidió simplificar — y además el camino rápido ya demostró producir
  evidencia desincronizada en la práctica, no solo en teoría.
- **Calcular automáticamente todas las versiones instaladas en cada consulta
  del Predictor.** Descartada por coste: con seis o más perfiles instalados
  (p. ej. las tres ventanas de V5w + las tres de V6w), una consulta normal
  se volvería cada vez más lenta a medida que se instalan más versiones.
- **Conservar varias generaciones por versión con retención permanente**
  (una tras otra, cada vez que se refresca) **con borrado manual de las
  antiguas para evitar acumulación.** Descartada por sobreingeniería: el
  usuario no necesita comparar el histórico de una misma versión a lo largo
  del tiempo — necesita comparar **versiones distintas entre sí**, cada una
  con su estado actual. Sustituida por la regla siguiente, mucho más simple.

## Regla central: una versión, una generación

Cada versión (V2, V3, V4, V5w-30d, etc.) tiene **como máximo una generación
instalada a la vez**. Refrescarla con la acción unificada (punto 4)
**sustituye** esa generación en el sitio — no se acumula ninguna anterior.
No hace falta rollback, no hace falta historial de generaciones, no hace
falta borrado manual de generaciones sueltas: no hay nada que podar porque
nunca se acumula nada. Esto es una excepción explícita y deliberada a la
política de retención permanente de `generations[]` ya documentada
(`retention_policy.benchmark_generations: "permanent"`) — para estas
generaciones operativas de mantenimiento rutinario, la retención pasa a ser
"solo la última", no "todas para siempre". Los benchmarks archivados
(evidencia de exploración, tratados aparte en `docs/decisions.md`
2026-08-19) siguen su propia regla, ya explícita, de historia viva y
podable manualmente.

Comparar si una versión ha mejorado o empeorado al añadir observaciones se
hace mirando su evidencia actual (única) frente a la de **otras versiones**
instaladas a la vez — no frente a su propio pasado. Para eso ya sirve tener
varias versiones instaladas y seleccionables en el Predictor.

## Propuesta acordada (revisada tras el hallazgo empírico y la simplificación a una generación por versión)

1. **Instalación independiente por versión.** Cada versión guarda su propio
   `installed_generation_id` (como máximo una), sin relación con las demás.
   Refrescar o activar una no toca ni degrada el de ninguna otra.
2. **"Preferida" en vez de "activa".** El puntero único actual
   (`active_version_id`/`active_operational_target`) se reconvierte en
   `preferred_version_id`: decide qué se calcula por defecto en una consulta
   normal del Predictor. Cambiar la preferida es solo mover ese puntero —
   ninguna comprobación de frescura, ningún reentrenamiento. Si la preferida
   se queda sin generación instalada (desactivación), cae a **"ninguna"** —
   hay que fijar otra explícitamente, sin valor por defecto automático.
3. **Lectura en runtime sin coste oculto.** El Predictor deja de depender de
   un único `runtime-batch.json` global; resuelve el batch de cada versión
   con `installed_generation_id` directamente por su `batch_id`. Pero solo
   calcula lo que el selector marca: por defecto, solo la preferida (mismo
   coste que hoy). El selector multi-checkbox que ya existe en el Predictor
   (`mvv`) pasa a decidir qué se **calcula**, no solo qué se muestra.
4. **Reentrenar y generar evidencia se fusionan en una sola acción,
   seleccionable por versión, con atajo "marcar todas".** "Reconstruir y
   reentrenar operativo" pasa a: elegir una, varias, o todas las versiones
   instaladas de golpe, y generar también el hold-out real (reutilizando el
   mismo mecanismo que ya usa el benchmark) en la misma pasada, sobre los
   mismos datos vivos con los que se reentrena — **sustituyendo** la
   generación anterior de cada versión elegida, nunca acumulándola. Un solo
   botón deja artefactos y evidencia siempre sincronizados, sin el circuito
   manual de 3 pasos para el mantenimiento rutinario. El benchmark
   científico independiente (comparar candidatas *no instaladas*, sobre un
   snapshot inmutable, sin instalar nada) se mantiene aparte, como camino
   residual/opcional para explorar antes de decidir — no para mantenimiento.
5. **Desactivar/reactivar una versión, sin borrar nada por defecto.**
   "Desactivar" pone `installed_generation_id` a vacío para esa versión:
   deja de aparecer en el selector del Predictor y queda automáticamente
   fuera de "marcar todas". Su única generación y batch siguen en disco
   (nada que acumular, es solo una). "Reactivar" es igual de ligero: volver
   a apuntar `installed_generation_id` a esa misma generación — sin
   reentrenar ni comprobar frescura, porque no cambia el modelo, solo su
   visibilidad.
6. **Pantalla de todas las versiones del registro.** Motivo: hoy no hay
   ningún sitio en la UI donde ver todas las versiones que existen y su
   estado real — solo se ven las lanzables (checkboxes de benchmark) o las
   instaladas (Predictor). Si una queda fuera de esas dos listas (como pasó
   al retirar V5/V6 raw365/smooth-365 editando el registro a mano), queda
   invisible salvo leyendo el JSON directamente. Esta pantalla lista
   **todas** las `version_id` del registro con su estado real y la
   evidencia de su única generación (si tiene): activa/preferida,
   instalada-pero-no-preferida, desactivada, o nunca instalada — sin
   depender de `benchmark_available`/`operational_eligible`.
7. **Borrado definitivo de una versión, solo si no está activa/preferida.**
   Desde esa misma pantalla, una versión desactivada se puede borrar
   definitivamente: se elimina su única generación registrada y el
   directorio de batch en disco que le correspondía. **Nunca se toca la
   definición de contrato** (perfiles, contratos temporales, estimadores,
   declarados en código) — solo su estado entrenado. Si se borra la que no
   tocaba, se recupera igual que cualquier versión nunca instalada:
   benchmark → preparar candidata → activar, desde cero con datos vivos
   actuales. Misma excepción explícita a la retención permanente que la
   regla central de este documento.

## Qué no cambia

- El benchmark científico independiente (comparar candidatas no instaladas
  sobre snapshot inmutable, sin comprometer nada) se mantiene, como camino
  residual/opcional para exploración puntual — no para mantenimiento
  rutinario. Su propia historia archivada sigue la regla ya documentada de
  "historia viva, podable manualmente" (`docs/decisions.md`, 2026-08-19).
- Predecir con un modelo ya instalado nunca comprueba frescura ni recalcula
  nada de más.
- La comprobación de frescura solo tiene sentido cuando se instala algo
  *nuevo* (una candidata preparada antes); desactivar/reactivar una versión
  ya instalada no cambia el modelo, así que no la necesita.

**Deja de existir tal como está hoy**: el camino rápido de V2/altitude_v2
sin evidencia. Con la fusión del punto 4, V2 pasa a ser una versión más
seleccionable en la acción unificada, y también genera su propio hold-out
real al reentrenarse — deja de mostrar evidencia de un benchmark antiguo
desincronizada (el hallazgo empírico de esta misma sesión).

## Ficheros que tocaría implementar esto

- `mushroom_ml_version_registry.py`: esquema (`installed_generation_id` por
  versión — como máximo una generación viva, `preferred_version_id`
  sustituyendo a `active_version_id` para este propósito), validación,
  funciones de activar/desactivar/reactivar/borrar por versión que no
  toquen a las demás.
- `mushroom_ml_version_promotion.py`: `promote_candidate` deja de escribir
  el único `runtime-batch.json` global y de degradar la versión previa; al
  refrescar sustituye la generación anterior de esa versión (borra su
  batch) en vez de acumularla.
- `mushroom_local_full_update.py` / `run-mushroom-ml-multiversion-job.py`:
  el reentrenamiento operativo pasa a aceptar una, varias, o todas las
  versiones seleccionadas (con atajo "marcar todas") y a generar también
  hold-out real en la misma pasada, reutilizando el mecanismo que hoy solo
  usa el benchmark (`evaluate-biology-v5-raw-benchmark.py`/
  `evaluate-biology-v6-smooth-hierarchical.py` u equivalente por versión).
- `mushroom_predictor_runtime.py` / `mushroom_ml_multiversion_comparison.py`:
  resolver el manifest por versión instalada en vez de leer un único
  fichero; el selector de versiones decide qué se calcula.
- UI: `mushroom_predictor_ui.py` (selector con preferida premarcada),
  `mushroom_workers_ui.py`/`web_server.py` (selector multi-versión con
  "marcar todas", acciones de desactivar/reactivar/borrar por versión), y
  una pantalla nueva de "todas las versiones".

## Decisiones ya tomadas por el usuario (2026-08-20)

- **Migración de versiones ya en `reference`.** `status` es un único valor
  por versión (confirmado en `mushroom-data/mushroom_ml_version_registry.json`:
  cada versión tiene exactamente un estado; hoy mismo
  `biology_v5_raw_weather_discovery` y `biology_v6_smooth_hierarchical` están
  ambas en `reference` a la vez, pero cada una con un solo valor). Las
  versiones que hoy están en `reference` se migran como **instaladas
  automáticamente** (recuperan `installed_generation_id` con la generación
  que tenían activa cuando fueron desplazadas). Si una versión tuviera hoy
  más de una generación en `generations[]` (herencia del esquema anterior,
  sin la regla de una-sola-generación), la migración se queda solo con la
  que estuviera realmente instalada y descarta el resto.
- **Preferida sin generación instalada**: cae a **"ninguna"**, sin valor por
  defecto automático.
- **Una generación por versión, sin historial ni rollback.** Comparar se
  hace entre versiones distintas instaladas a la vez, no contra el pasado
  de la misma versión.

## Pendiente de resolver antes de implementar

- Coste real de generar hold-out para V2/V3/V4 dentro de la acción
  unificada: V5/V6 ya tienen script de evaluación propio
  (`evaluate-biology-v5-raw-benchmark.py`/
  `evaluate-biology-v6-smooth-hierarchical.py`); para V2/V3/V4 hay que
  confirmar si existe un mecanismo de hold-out equivalente reutilizable o
  hay que construirlo, y cuánto alarga el reentrenamiento "rápido" de hoy.
  A investigar en implementación, no requiere decisión del usuario salvo
  que el coste resulte relevante.
- Semántica exacta de "marcar todas las activas": si una versión desactivada
  se reactiva justo antes de pulsar el botón, debe entrar; si se desactiva
  a mitad de una ejecución en curso, no debería interrumpir lo que ya se
  había lanzado para ella.
