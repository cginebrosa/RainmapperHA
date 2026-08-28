# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado operativo al cierre — 2026-08-28

- Workspace `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  El cierre de código está publicado en `origin/inicial` con commit
  `8085e464fdca686cc57c2026163ac08d8cdb6374`. El worktree estaba limpio al
  iniciar este cierre documental; comprobarlo de nuevo al continuar.
- HA real confirmada por el usuario: `0.2.275`. HA `0.2.276` está publicada en
  GHCR, pero su instalación real no está confirmada todavía.
- `0.2.276` y `latest` comparten el índice OCI
  `sha256:70013bb4d17dfca0ec46652398da39119c00e9e78790dd4941b71f5692635b36`
  con manifests `linux/amd64` y `linux/arm64`.
- El único worker es local al M1 y no se publica en GHCR. Está reconstruido como
  `rainmapper-worker:1.0.25`, `healthy` e `idle`, con identidad
  `worker_1a9a232c20fe2ee2`, volumen `rainmapper-worker-data` y cachés GIS y
  Predictor válidas. Revalidar runtime antes de reutilizar estos datos.
- La retención ML real permanece activa por decisión del usuario. No cambiarla,
  no borrar datos manualmente y no relajar hashes, cancelación, retry, rollback
  ni promoción atómica.
- No existen entrenamientos programados. El usuario inicia manualmente una
  reconstrucción/reentrenamiento cuando añade observaciones.
- La última tentativa manual del cierre, posterior a la ejecución de un runner
  meteorológico, falló en el primer job `Reconstrucción operativa completa` al
  55 % tras 2 min 9 s. La captura no muestra el error concreto. No se ha
  comprobado si el runner cambió datos ni existe evidencia suficiente para
  atribuirle el fallo.

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

- 49 pruebas dirigidas de scope, ML y worker;
- 327 pruebas de integración local/HA/worker/resultados/web;
- siete pruebas de empaquetado del worker;
- smoke completo: 1.089 pruebas y todos los validadores correctos;
- igualdad del scope comprobada directamente con los mismos inputs actuales;
- `git diff --check` correcto antes del commit `8085e46`.

No repetir el smoke por cambios exclusivamente documentales. Revalidar de forma
proporcional si cambia código, imagen, datos o configuración.

## Próximos pasos

1. Antes de repetir el entrenamiento, obtener el detalle o log exacto de la
   reconstrucción fallida al 55 % y determinar si falló meteorología, transporte
   u otra fase. No corregir ni atribuir causa basándose solo en la captura.
2. El usuario puede instalar HA `0.2.276`. Después comprobar únicamente versión,
   arranque, worker `1.0.25` disponible y una predicción conocida. Codex no puede
   instalarla en HA real.
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

- **Instalación pendiente:** HA real `0.2.276` no está confirmada. No atribuirle
  validación de runtime hasta que el usuario la instale y lo confirme.
- **Reconstrucción fallida tras runner:** el último intento terminó al 55 % en
  el primer job. Solo están confirmados tipo, porcentaje y duración; falta el
  mensaje de error. La relación con el runner meteorológico es una hipótesis.
- **UI de trabajos:** duración no incluye toda la preparación/pausas y el
  porcentaje puede retroceder al cambiar de escala de fase. No usar porcentaje
  ni suma de duraciones mostradas como ETA o tiempo integral.
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
