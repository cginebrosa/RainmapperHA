# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado exacto al cierre — 2026-08-28

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
- HA `0.2.272` quedó publicada en GHCR. Los tags `0.2.272` y `latest` comparten
  el índice OCI
  `sha256:d54ec58efa88b01c650d9c1f6a23fc754419d491e0856365a58cd1fad52d433a`
  y contienen manifests `linux/amd64` y `linux/arm64`.
- No se ha tocado HA real, el worker normal, la retención ni los datos reales.
  La instalación y la ejecución real quedan en manos del usuario.

- Workspace `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
- HEAD local y remoto: `29aca9c9504aa836efff4ea3406726d302dfd6aa`
  (`Release Home Assistant 0.2.271`).
- HA real está en `0.2.271`, según confirmación del usuario. El worker normal
  observado es `rainmapper-worker:1.0.21`, `healthy`, con identidad
  `worker_1a9a232c20fe2ee2`.
- La release nueva aún no está confirmada como instalada en HA real. El estado
  confirmado es HA `0.2.271` hasta que el usuario informe de la actualización;
  el único worker ya está en `1.0.22`.
- La opción real **Apply ML storage retention** permanece activa. No cambiarla,
  no borrar datos manualmente y no ampliar retención sin una decisión nueva.
- No se usó Tailscale. El `share` real se consultó solo en lectura para el
  diagnóstico. No se modificaron HA real, el worker ni sus datos desde Codex.

## Predictor 0.2.271: resultado y límite actual

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

## Fallo real de Reconstruir y reentrenar operativo

No repetir la cadena real hasta corregir y validar localmente el alcance. La
ejecución del 2026-08-28 no promocionó modelos nuevos; los modelos operativos
anteriores permanecen protegidos por la promoción atómica.

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

## Próximos pasos, en orden

1. Validar la ejecución del mismo plan por ambos transportes y comparar fits,
   métricas y artefactos; no usar HA real para esta comprobación.
2. Corregir la telemetría/UI para duración total, duración de fase y tiempos de
   reconciliación, bundle, claim, worker, verificación y transición.
3. Solo tras pruebas dirigidas, smoke completo y una cadena local correcta,
    proponer las versiones HA/worker necesarias. No hacer bump, build,
    publicación, instalación ni prueba real sin autorización explícita.

## Riesgos y dudas activos

- **Política para especie nueva sin tuning:** sigue siendo una decisión
  científica abierta. Un fallback implícito comprometería reproducibilidad.
- **Lote local no representa la ruta remota:** incluye Cantharellus por el
  criterio de filas y no debe usarse como prueba de equivalencia.
- **Duraciones engañosas:** los contadores actuales excluyen preparación y
  transiciones; el presupuesto de 10 minutos se mide desde la pulsación hasta
  la promoción final.
- **SoilGrids/GIS sin atribución suficiente:** el trabajo dedicó 3 min 55 s
  antes del claim, pero no existe desglose persistido. Verificar también si el
  aviso de cuatro microáreas incompletas desapareció tras la reconciliación.
- **Carrera de finalización ML v0:** el cierre repetido con el mismo estado final
  es ahora idempotente; un retry que intente cambiarlo sigue rechazándose. La
  prueba local cubre ambos casos, pero no se ha revalidado en el worker real.
- **Predictor frío:** 35–40 s sigue lejos del objetivo de 10 s. El hit HA es
  correcto; quedan por separar cálculo frío y renderizado caliente.
- **Integridad:** conservar snapshots, hashes, cancelación, retry, rollback,
  promoción atómica y retención. No arreglar el fallo relajando gates.

## Validación y entrega ya completadas

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
