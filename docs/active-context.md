# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado operativo al cierre — 2026-08-29

- Workspace `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  El HEAD previo a esta release era
  `877c71dee0245f38e6e440e59467af9fb217893f`; revalidar HEAD y worktree al
  continuar.
- La versión exacta instalada en HA real no se ha revalidado después de la
  última prueba del usuario. HA `0.2.280` está publicada y pendiente de
  instalación confirmada.
- `0.2.280` y `latest` comparten el índice OCI
  `sha256:91dba9bf08c2d428a0541814d348c4eaaf3b367746a2d14f4a6b07fb3a3789c6`
  con manifests `linux/amd64` y `linux/arm64`.
- El único worker es local al M1 y no se publica en GHCR. Está reconstruido como
  `rainmapper-worker:1.0.29` e `idle`, con identidad
  `worker_1a9a232c20fe2ee2`, volumen `rainmapper-worker-data` y cachés GIS y
  Predictor válidas. Revalidar runtime antes de reutilizar estos datos.
- La retención ML real permanece activa por decisión del usuario. No cambiarla,
  no borrar datos manualmente y no relajar hashes, cancelación, retry, rollback
  ni promoción atómica.
- No existen entrenamientos programados. El usuario inicia manualmente una
  reconstrucción/reentrenamiento cuando añade observaciones.
- La última tentativa manual falló al subir el resultado de
  `Reconstrucción operativa completa` tras 2 min 9 s. El worker registró
  `name 'HTTPError' is not defined`: `_post_bytes` intentaba capturar un rechazo
  HTTP de HA sin importar la excepción y destruyó su código y detalle. La
  reconstrucción ya había terminado y superado su verificación local. El runner
  anterior creó la generación `20260828T192626159381Z-4c6df0e9daed`, con seis
  filas más que `20260828T090352707610Z-6ae4e0b0dba3`, y terminó unos 33 minutos
  antes del claim; no hay evidencia de que causara el rechazo. Worker `1.0.26`
  corrige el import y conserva el detalle si vuelve a ocurrir.
- La repetición posterior sí completó los tres jobs: reconstrucción en 1 min
  39 s, ML v0 en 29 s y multiversión en 11 min 20 s. En el tercero, el worker
  reclamó el job a las 20:36:18 UTC y HA confirmó 638 objetos y 90.087.316
  bytes en caché a las 20:47:36 UTC. Por tanto, la fase `Uploading` de la UI no
  representaba once minutos de transferencia de red: incluía trabajo previo y
  verificación posterior sin fases visibles suficientemente precisas.
- HA `0.2.278` y worker `1.0.28` derivan el snapshot encadenado mediante
  hardlinks de los inputs inmutables y solo calculan hashes de los inputs
  nuevos. La entrega multiversión anuncia `Uploading` antes de la primera
  petición, acepta gzip acotado y devuelve recibos por ruta; los reintentos
  omiten objetos ya verificados en HA. No atribuir mejora real hasta instalar
  HA y medir una nueva cadena iniciada por el usuario.
- La cadena medida con esas optimizaciones siguió mostrando alrededor de un
  minuto entre ML v0 y la aparición del job multiversión. La causa comprobada
  en código es que HA materializaba el catálogo de tuning antes de persistir el
  job. `0.2.279` crea primero un job visible en estado de preparación; el worker
  `1.0.29` persiste el catálogo de la generación recién entrenada y HA lo
  reutiliza por manifest/hash en la siguiente cadena. Un batch antiguo aún usa
  el recorrido completo una vez.
- El último entrenamiento llegó al final del cálculo multiversión y falló al
  iniciar la entrega: el worker registró `HTTP Error 404: Not Found: Not found.`
  El endpoint TAR estaba implementado y anunciado, pero faltaba en
  `MUSHROOM_WORKER_PROTOCOL_POST_PATHS`, por lo que el listener dedicado lo
  rechazaba antes de llegar al handler. HA `0.2.279` corrige la allowlist.
- Tras instalar esa corrección, reconstrucción (1 min 37 s) y ML v0 (26 s)
  completaron, pero el coordinador abortó el tercer job al 1 % en 1 s. El error
  exacto era la ausencia de
  `batches/operational_20260828T203505Z/tuning-catalog.json`: el manifest del
  batch lo declaraba, pero el fichero no existía. HA `0.2.280` reconstruye el
  catálogo desde los modelos del mismo batch cuando falta; si existe, mantiene
  intactas las validaciones de hash e identidad.

## Resultado principal de la sesión

La unificación de `OperationalTrainingScope` está implementada y validada:

- el alcance se calcula después de agregar filas en episodios área/fecha y de
  aplicar los gates científicos;
- el plan serializable sella scope, catálogo, versiones, perfiles, fits y
  tuning; local, HA y worker consumen esas identidades sin redescubrir especies;
- diez filas elegibles de Cantharellus forman nueve episodios y producen la
  exclusión reproducible `insufficient_area_episodes`;
- cobertura de tuning, retry, cancelación, rollback y promoción atómica tienen
  pruebas centinela.

La comparación de los inputs actuales local/HA encontró 439 filas científicas
idénticas, pero inicialmente scopes distintos. La causa confirmada era que la
identidad incluía metadatos volátiles de los artefactos. La revisión `.2` ahora:

- identifica features exclusivamente por sus filas científicas ordenadas;
- identifica known-sites por su contenido científico, omitiendo recursivamente
  solo `generated_at` y `updated_at`;
- sigue invalidando el scope si cambia una feature, altitud u otro valor
  científico.

Con los inputs reales actuales ambas rutas producen:

- scope:
  `sha256:47d934d7c4fadde8b533efc35964b833d4e0f9710ee1dc4cebc4e4275830ec07`;
- features:
  `sha256:df7d79e259967d3d2096c38193287b1bc8e2190c83078b3c08c9f973118e1218`;
- known-sites:
  `sha256:d4427532f4ef84cb42040a086edd993361487bf06aac2939fc0dd865783793dc`;
- ocho especies admitidas; Cantharellus conserva 15 filas, diez elegibles y
  nueve episodios.

## Validación real y rendimiento observado

La cadena real con HA `0.2.275` y worker `1.0.24` completó reconstrucción, ML v0,
V2–V6 y promoción. La meteorología no cambió porque el scheduled runner no se
activó. Duraciones declaradas por job:

- reconstrucción: 1 min 45 s;
- ML v0: 33 s;
- entrenamiento V2–V6: 10 min 15 s.

La CPU de la RPi4 volvió a su nivel habitual al terminar. Estas duraciones no
son el total integral desde la pulsación: la UI todavía pierde preparación y
transiciones entre jobs.

Predictor real sobre la generación promocionada:

- recommender frío: 29,0 s de trabajo, 23,9 s de cálculo;
- cambio de día reutilizado: 0,6 s, cálculo menor de 0,1 s;
- fecha nueva: 12,0 s, 9,4 s de cálculo;
- consulta multiversión fría: 29,0 s, 23,6 s de cálculo.

El usuario percibió una mejora clara. El camino frío sigue por encima del
objetivo de 10 s y no debe optimizarse sin telemetría por fase.

## Validación de código completada

- smoke definitivo de HA `0.2.280` sobre 1.100 pruebas y todos los validadores;
- siete pruebas de empaquetado tras los bumps mecánicos;
- imagen HA multiarch publicada y verificada con el mismo digest en versión y
  `latest`;
- worker `1.0.29` reconstruido conservando identidad, volumen y cachés; health
  local confirma versión, `idle` y ambas cachés válidas;

- 49 pruebas dirigidas de scope, ML y worker;
- 327 pruebas de integración local/HA/worker/resultados/web;
- siete pruebas de empaquetado del worker;
- smoke completo: 1.089 pruebas y todos los validadores correctos;
- igualdad del scope comprobada directamente con los mismos inputs actuales;
- `git diff --check` correcto antes del commit `8085e46`.

No repetir el smoke por cambios exclusivamente documentales. Revalidar de forma
proporcional si cambia código, imagen, datos o configuración.

## Próximos pasos

1. El usuario instalará HA `0.2.280`; comprobar versión y worker `1.0.29`
   reconocido antes de iniciar cualquier job.
2. El usuario, no Codex, lanzará la cadena real. Medirla por marcas monotónicas y contadores de
   peticiones/bytes; comparar en especial preparación, transferencia y
   verificación/promoción. No usar el texto `Uploading` como cronómetro de red.
3. No hace falta reentrenar para validar la corrección de identidad: ya se
   comparó directamente con los mismos inputs local/HA.
4. Cuando el usuario añada observaciones podrá lanzar voluntariamente una cadena
   real. Si se mide, anotar hora de pulsación y promoción porque la UI aún no
   ofrece tiempo integral fiable.
5. Mantener en TODO la corrección de tiempo/progreso. Es un problema de
   observabilidad: no se ha demostrado que afecte al rendimiento científico.
6. Antes de cerrar la equivalencia total, comparar en dos ejecuciones con
   inputs idénticos scope, plan, fits, métricas y artefactos.
7. El siguiente bloque de optimización recomendado es instrumentar el Predictor
   frío por fases; actuar solo sobre la fase dominante medida.

## Riesgos y dudas activos

- **Rechazo HTTP original irrecuperable:** el `NameError` del worker ocultó el
  código y detalle enviados por HA. `1.0.26` evita volver a perderlos, pero no
  demuestra si el rechazo fue transitorio o reproducible.
- **Runner anterior:** el histórico cambió y la generación nueva fue el input de
  la reconstrucción, pero el runner terminó unos 33 minutos antes. La relación
  causal con el rechazo HTTP no está demostrada.
- **UI de trabajos:** duración no incluye toda la preparación/pausas y el
  porcentaje puede retroceder al cambiar de escala de fase. No usar porcentaje
  ni suma de duraciones mostradas como ETA o tiempo integral.
- **Optimización pendiente de validación real:** la suite valida el job visible,
  el catálogo persistido, gzip acotado, TAR comprimido, recibos, reanudación y
  fallback, pero falta medir una cadena real con HA `0.2.280`.
- **Equivalencia completa:** scope e identidades ya coinciden; todavía no se ha
  archivado una comparación exacta de fits, métricas y artefactos de local y
  remoto ejecutados sobre el mismo snapshot final.
- **Especie nueva sin tuning:** el runtime falla cerrado en preflight y conserva
  el modelo vivo. Sigue abierta la política científica para admitirla mediante
  benchmark previo o configuración base explícita.
- **WAN:** telemetría/progreso ya no bloquea el cálculo y la entrega final es
  reintentable e idempotente, pero faltan métricas de peticiones, bytes y espera
  de red por fase.
- **Predictor frío:** 29 s observados siguen lejos del objetivo; no atribuir el
  coste a red, cálculo o render sin instrumentación.

## Archivos relevantes

- Scope canónico: `rainmapper_core/mushroom_operational_training_scope.py`.
- Plan/transporte: `rainmapper_core/mushroom_ml_multiversion_plan.py`,
  `rainmapper_core/mushroom_ml_multiversion_transport.py`.
- Orquestación HA/local: `rainmapper-app/app/web_server.py`,
  `rainmapper_core/mushroom_local_full_update.py`.
- Worker/entrega: `rainmapper_core/mushroom_worker_service.py`,
  `rainmapper_core/mushroom_worker_transport.py`,
  `rainmapper_core/mushroom_worker_results.py`.
- Pruebas del scope: `tests/test_mushroom_operational_training_scope.py`.
- Especificación vinculante:
  `docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`.
- Predictor: `rainmapper_core/mushroom_predictor_service.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py`.
- Optimización Predictor:
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`.
- Releases: `docs/release-flow.md`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo para prioridades completas.
- Cumplir `AGENTS.md`: usar Codebase Memory MCP antes de descubrir o cambiar
  código y reindexar únicamente si el grafo conserva símbolos retirados.
- Comprobar `pwd`, rama y `git status`; preservar absolutamente todos los
  cambios locales y ficheros no rastreados.
- No usar Tailscale, no tocar HA real, no cambiar retención y no borrar datos.
- No ejecutar una cadena real ni hacer bump, build, publicación, instalación o
  release sin autorización explícita nueva.
- Aplicar validación proporcional y terminar siempre con `git diff --check`.
