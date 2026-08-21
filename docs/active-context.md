# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos y runtime
antes de afirmar estado presente; `docs/decisions.md` conserva la historia y
las razones duraderas, `docs/project-archive.md` el detalle histórico ya
cerrado (fases 1-4, bugs de catálogo/evidencia ecológica de la primera
promoción V3/V4).

## Estado al cierre — 2026-08-21

- Rama `inicial`, workspace `/Users/carlosginebrosa/Developer/RainmapperHA`.
  Release HA `0.2.263` publicada (GHCR, digest `sha256:74577ddc8bed0aee6edc
  7c930ca797697a0af3107bbc7338f4cb6afbea8e07eb`, `linux/amd64`+`linux/arm64`
  verificados en ambos tags `0.2.263` y `latest`) y commit/push de este
  worktree en curso en la misma sesión. Pendiente que el usuario instale
  `0.2.263` en HA real.
- Confirmación en vivo de los 6 puntos (benchmarks reales en el laboratorio
  local, contenedor `rainmapper-local-rainmapper-ha-ui-1`, ruta HA-local
  `run_local_benchmark`, no worker):
  1. **Elegibilidad de especies**: el benchmark `benchmark_v2_v6_20260821T181031Z`
     (solo `biology_v4`, 9 especies, 216/216 fits, 0 fallos) confirma que la
     ruta HA-local sigue bien, pero **no** ejercita el código antes roto
     (`create_mushroom_ml_multiversion_job` sin `triggered_by_job_id`, ruta
     worker) — eso solo se puede confirmar relanzando el mismo benchmark
     disparado desde un worker real. Pendiente explícito.
  2. **Convergencia V5w/V6w**: el benchmark `benchmark_v2_v6_20260821T202156Z`
     (V5w+V6w completos, 6 perfiles, 9 especies, 174/174 fits, 0 fallos)
     confirma que `lactarius_deliciosus` ya no falla en ninguna de las 3
     ventanas ni contrato temporal (antes fallaba en las 3 ventanas de V5w
     raw). La ventana de 90 días domina claramente para esta especie
     (Brier hasta 0.03-0.09 vs prevalencia 0.183, AUC~1.0). Confirmado por
     fit/convergencia, ya que ambas rutas (HA-local y worker) ejecutan el
     mismo script `run-mushroom-ml-multiversion-job.py` sin divergencia de
     código para esta parte.
- Bug de datos descubierto y corregido en el laboratorio local (no releíble,
  no afecta código): el usuario añadió observaciones de un área nueva
  ("Setcases", `boletus_edulis`/`boletus_pinophilus`) sin copiar el área
  correspondiente a `docker-data/mushroom-data/mushroom_known_sites.json` —
  las observaciones quedaban huérfanas (0 filas en
  `mushroom_observation_features_v0.json`). Ya corregido por el usuario
  (área + 2 micro-áreas presentes). Pendiente: reconstruir + reentrenar en
  local para que esas observaciones entren en el dataset.
- Verificado el despliegue del worker: el contenedor `rainmapper-worker`
  corriendo en esta máquina (imagen `1.0.15`) **es el worker real M1**
  emparejado con HA real (`config/coordinator.json` →
  `http://100.111.77.48:8100`, identidad `M1 Personal` /
  `MacBook Pro de Carlos`), no una instancia de laboratorio. No se publica a
  GHCR — se reconstruye localmente en esta misma máquina. Su Dockerfile
  (`rainmapper-worker/Dockerfile`) es una copia curada de `rainmapper_core`:
  incluye los ficheros de los puntos 2/3/6 (V5w/V6w, `predict_bundle`, IDW)
  pero **no** incluye `mushroom_local_full_update.py` — el fix de
  elegibilidad (punto 1) vive enteramente en código HA y no necesita
  reconstrucción del worker. Credenciales/identidad/jobs persisten en el
  volumen externo `rainmapper-worker-data`, independiente de la imagen —
  bump a `1.0.16` no las pierde.
- `docs/release-flow.md` actualizado: el segundo smoke test tras el bump de
  versión se sustituye por verificación manual (`grep`) de los 3 sitios de
  versión + cache-busters, ya que el resto de comprobaciones no depende de
  esos ficheros y ya se validó en el primer smoke test del flujo.
- Trabajo de los 6 puntos, ya publicado en `0.2.263`:
  1. **Bug corregido** — elegibilidad de especies duplicada entre HA local y
     worker: `mushroom_local_full_update.eligible_training_species` se hizo
     pública y `create_mushroom_ml_multiversion_job` la reutiliza en vez de
     `web_server.eligible_model_species_ids`. Detalle: `docs/decisions.md`
     2026-08-19 "Elegibilidad de especies duplicada...".
  2. **Feature nueva** — perfiles de ventana predictiva 30/60/90 días en V5/V6
     (`biology_v5_windowed_raw_weather`, `biology_v6_windowed_smooth_hierarchical`),
     retirando `biology_v5_raw_weather_discovery`/`biology_v6_smooth_hierarchical`
     a `status: reference` + `benchmark_available: false`. Motivado por fallos
     reales de convergencia de V5 raw365 por dimensionalidad. Detalle:
     `docs/decisions.md` 2026-08-19 "Perfiles de ventana predictiva...",
     `docs/mushrooms/mushroom-ml-contract-versions-es.md`.
  3. **Bug crítico corregido** (encontrado probando la feature anterior en
     vivo) — `mushroom_ml_runtime_inference.predict_bundle` no aplicaba el
     preprocesador suave a V6 windowed (`runtime_model_incompatible` en
     Predictor). Detalle: `docs/decisions.md` 2026-08-20.
  4. **Feature nueva** — botón "Borrar" en el historial de benchmarks:
     borrado real de disco (`mushroom_ml_benchmark_reports.delete_report`),
     con confirmación en UI. Decisión explícita del usuario de no retener
     benchmarks para siempre. Detalle: `docs/decisions.md` 2026-08-19
     "Los benchmarks científicos archivados son historia viva...".
  5. **Diseño, no implementado** — instalación de varias versiones ML a la
     vez (una versión = una generación, `preferred_version_id` en vez de
     puntero único, activar/desactivar/borrar por versión, refrescar una o
     varias "de una pasada"). Glosario de vocabulario (versión/perfil/
     modelo/generación) añadido en la sección "Vocabulario" de
     `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`. Documento
     completo: `docs/mushrooms/mushroom-ml-multi-version-installation-design-es.md`.
  6. **Rendimiento** — perfilado real (cProfile) de una consulta del
     Predictor y de un benchmark completo, a raíz de la pregunta de si
     convenía reescribir el kernel en C. Conclusión: no se reescribe nada en
     C (sklearn/NumPy ya delegan en BLAS/LAPACK); se corrigió la única
     redundancia fácil/bajo riesgo encontrada (`haversine_km` recalculado dos
     veces por estación en `mushroom_weather_idw.py`). Detalle:
     `docs/decisions.md` 2026-08-20 "Perfilado de predictor y entrenamiento...".

## Pendiente inmediato

- Reconstruir la imagen del worker M1 a `1.0.16` en esta misma máquina (sin
  push a GHCR) para llevar los fixes de V5w/V6w, `predict_bundle` e IDW;
  preservar el volumen `rainmapper-worker-data` (token/identidad/jobs).
- Relanzar el benchmark V4 disparado desde el worker real (no HA-local) para
  confirmar definitivamente el fix de elegibilidad de especies en la ruta
  que estaba rota — pendiente explícito, no confirmado todavía por esa vía.
- Reconstruir + reentrenar en local para que las observaciones de Setcases
  (área ya corregida en `known_sites.json`) entren en el dataset de
  entrenamiento.
- Instalación/actualización de HA real a `0.2.263` — pendiente de que el
  usuario la ejecute; sin bloqueo técnico conocido.
- Perfilar en detalle la fase "preparación de inputs compartidos /
  evaluación de filas hold-out" de un benchmark completo: es la fase que
  realmente domina el tiempo de reloj (varios minutos), no el ajuste de
  modelos (segundos según manifiestos) — no perfilada todavía.
- Implementación (no diseño) de la instalación de varias versiones ML a la
  vez — explícitamente diferida, ver `docs/todo.md` P1.
- Investigar si recalcular balance/SMI por ventana (en vez de compartirlo
  entre 30/60/90) aísla mejor la señal — pendiente explícito, no iniciado.

## Riesgos y dudas activos

- El usuario está borrando manualmente batches huérfanos en
  `/Volumes/share/rainmapper/mushroom-data/ml_models/batches/` en HA real
  (ocupación grande, backups que crecen) — **no tocar ese share** ni actuar
  ahí salvo petición explícita nueva.
- El registro ML solo admite retirada a nivel de versión completa
  (`status`), nunca de perfil individual — cualquier diseño futuro debe
  respetar esa restricción (verificado en código, no es preferencia).
- No usar Tailscale, no tocar HA real ni el worker normal, no manipular
  históricos meteorológicos sin `docs/history-safety.md`, no publicar
  release sin autorización explícita nueva.

## Archivos relevantes

- Diseño multi-versión: `docs/mushrooms/mushroom-ml-multi-version-installation-design-es.md`.
- Contratos ML: `docs/mushrooms/mushroom-ml-contract-versions-es.md`,
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`,
  `docs/mushrooms/mushroom-ml-biology-v5-raw-weather-discovery-spec-es.md`,
  `docs/mushrooms/mushroom-ml-biology-v6-smooth-hierarchical-spec-es.md`,
  `mushroom-data/mushroom_ml_version_registry.json`.
- Ventanas V5/V6: `rainmapper_core/mushroom_ml_raw_weather.py`,
  `rainmapper_core/mushroom_ml_smooth_hierarchical.py`,
  `rainmapper_core/mushroom_ml_runtime_trainer.py`,
  `rainmapper_core/mushroom_ml_runtime_features.py`,
  `rainmapper_core/mushroom_ml_runtime_inference.py`,
  `rainmapper_core/mushroom_ml_multiversion_comparison.py`,
  `scripts/prepare-mushroom-ml-multiversion-inputs.py`,
  `scripts/evaluate-biology-v5-raw-benchmark.py`,
  `scripts/evaluate-biology-v6-smooth-hierarchical.py`.
- Elegibilidad de especies: `rainmapper_core/mushroom_local_full_update.py`,
  `rainmapper-app/app/web_server.py`.
- Borrado de benchmarks: `rainmapper_core/mushroom_ml_benchmark_reports.py`,
  `rainmapper-app/app/mushroom_workers_ui.py`.
- Rendimiento IDW: `rainmapper_core/mushroom_weather_idw.py`.
- Coordinación/UI general: `rainmapper-app/app/mushroom_predictor_ui.py`,
  `rainmapper-app/app/mushroom_workers_ui.py`.
- Labels: `mushroom-data/mushroom_labels.json`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo si hacen falta las prioridades completas.
- Comprobar `pwd`, rama y `git status`; preservar absolutamente todos los
  cambios y ficheros no rastreados.
- Usar Codebase Memory MCP antes de descubrir o cambiar código.
- Mantener actualizaciones de proceso muy breves para conservar tokens.
- No preparar ni publicar releases sin autorización explícita nueva.
