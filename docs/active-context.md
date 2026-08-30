# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-31

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  El HEAD verificado antes del cierre documental es
  `28982edb5da3215398597bd550cf930d2ac3447f`; revalidarlo al comenzar.
- El código declara HA `0.2.284` y worker `1.0.31`.
- HA `0.2.284` y `latest` están publicados en GHCR con el mismo índice OCI
  `sha256:b00ec790287648c9fde654ee8430fabb708036ee9b7f8af2ab7a63c9eaf8708c`
  y manifests `linux/amd64` y `linux/arm64`.
- La última versión confirmada en HA real es `0.2.283`. Rainmapper real quedó
  parado voluntariamente; el usuario debe instalar y probar `0.2.284`.
- El worker privado no se publica. El contenedor local observado era `1.0.31`,
  conservaba identidad `worker_1a9a232c20fe2ee2`, volumen
  `rainmapper-worker-data`, estado healthy/idle y capacidad
  `predictor_precompute_v1`. Revalidar antes de afirmarlo en otra sesión.
- No hay entrenamientos programados. No tocar retención, datos reales, HA real
  ni lanzar entrenamientos, bumps, builds o publicaciones sin autorización.

## Resultado operativo entregado

El precálculo semanal del Predictor está implementado y validado localmente:

- SQLite regenerable con identidad científica separada del SHA-256 físico,
  validación de esquema, integridad y cobertura, y sustitución atómica;
- todas las especies y áreas, siete días y todas las versiones operativas;
  las respuestas multiversión se componen desde bloques por versión sin
  enumerar combinaciones;
- lookup primero en HA; un hit no crea job ni usa el worker; ausencia,
  corrupción, identidad distinta o cobertura insuficiente hacen fallback
  íntegro con selección explícita de ejecutor;
- artefacto HA bajo `/media/rainmapper/predictor_precompute`, fuera del backup;
- estado latest-wins, lanzamiento manual y solicitud asíncrona al terminar el
  runner meteorológico;
- estado visible en Workers y en la esquina superior derecha del Predictor.

El artefacto local de equivalencia ocupó `462974976` bytes, con 623 respuestas
y 143 payloads. Recommender, semana, multiversión de un área y
fecha/todas-las-áreas produjeron resultados científicamente idénticos al cálculo
vivo. Los lookups midieron 0,03–0,11 s frente a 0,15–31,34 s en cálculo vivo.

## Corrección final de presencia del worker

- En HA `0.2.283`, el worker enviaba heartbeat cada 5 s y HA lo declaraba
  desconectado exactamente a los 5 s. El jitter normal causaba ciclos de
  `En espera` durante 8–13 s, `Desconectado` aproximadamente 1 s y vuelta a
  `En espera`.
- `0.2.284` mantiene heartbeat cada 5 s y amplía el umbral de presencia a 15 s.
- La materialización de una solicitud pendiente ya no planifica ciencia dentro
  del request heartbeat. Se agenda fuera de la petición y solo una vez por
  `(worker_id, revision, artifact_id)`; el heartbeat responde sin esperar.
- El montaje real mostró `desired.json` del runner en revisión 1, asignado al
  M1, pero ningún job `predictor_precompute` materializado todavía. Esta es la
  primera situación que debe observarse tras instalar `0.2.284`.

## Validación y release

- Suite dirigida del servidor: 293 pruebas correctas.
- Smoke definitivo: 1.180 pruebas y todos los validadores correctos.
- `git diff --check` correcto.
- Release HA `0.2.284` publicada y verificada en GHCR; commit de release
  `28982edb5da3215398597bd550cf930d2ac3447f` publicado en `origin/inicial`.
- Worker `1.0.31` no cambió: la corrección pertenece al coordinador HA.

## Próximos pasos inmediatos

1. El usuario instala HA `0.2.284` y arranca Rainmapper.
2. Confirmar versión instalada y observar al menos varios minutos que el worker
   permanece `En espera` sin alternar con `Desconectado`; medir CPU y RAM en
   reposo. No afirmar mejora de memoria solo por la corrección: Python puede
   conservar memoria reservada.
3. Confirmar que la revisión 1 pendiente se materializa una sola vez y queda en
   cola o en ejecución sin bloquear heartbeats. Revisar logs si no aparece job.
4. Ejecutar el primer precálculo real en el worker: medir planificación,
   cálculo, transferencia y activación; verificar SQLite en
   `/media/rainmapper/predictor_precompute` y ausencia en el backup.
5. Probar hits con datos en las cuatro rutas equivalentes y un miss controlado
   que solicite ejecutor para el fallback.
6. Solo después, perfilar `Building weekly matrix` por especie y optimizar el
   coste dominante medido. Objetivo orientativo: menos de diez minutos.

## Riesgos y dudas activos

- `0.2.284` está publicada pero no instalada ni probada en HA real.
- El circuito real completo worker → transferencia → activación HA aún no se
  ha completado. El tamaño SQLite local fue ~442 MiB; transferencia, escritura
  en `/media` y consumo de la RPi4 deben medirse.
- La planificación se ejecuta una vez fuera del heartbeat, pero puede consumir
  CPU/RAM mientras prepara el job. Debe medirse separadamente del reposo.
- El fallback en HA real debe conservar siempre la selección explícita de
  ejecutor; nunca asumir cálculo pesado local en la RPi4.
- La UI de jobs todavía no ofrece duración integral ni ETA global fiables.
- El montaje real de `/share/rainmapper` ocupaba aproximadamente 1,12 GiB. Hay
  317,6 MiB revisables: 179,6 MiB en seis bundles de jobs completados/limpiados
  y un TAR legacy de runtime de 138 MiB. No borrar ni cambiar retención.
  El TAR solo podrá retirarse después de crear y verificar su sustituto bajo
  `/media/rainmapper/runtime-cache/predictor-runtime-archives`; al cierre no
  existía allí ningún TAR.
- El único batch ML de ~176 MiB está referenciado por V2/V3/V4/V5w/V6w y está
  protegido; no es residuo.

## Archivos relevantes

- Especificación: `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`.
- Artefacto/control: `rainmapper_core/mushroom_predictor_precompute.py` y
  `rainmapper_core/mushroom_predictor_precompute_control.py`.
- Lookup/composición: `rainmapper_core/mushroom_predictor_service.py` y
  `rainmapper_core/mushroom_ml_multiversion_comparison.py`.
- Coordinador/UI: `rainmapper-app/app/web_server.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py` y
  `rainmapper-app/app/mushroom_workers_ui.py`.
- Worker/jobs: `rainmapper_core/mushroom_worker_service.py`,
  `rainmapper_core/mushroom_worker_jobs.py` y
  `rainmapper_core/mushroom_worker_registry.py`.
- Rutas: `rainmapper_core/mushroom_paths.py`.
- Pruebas principales: `tests/test_mushroom_predictor_precompute.py`,
  `tests/test_mushroom_predictor_service.py`, `tests/test_mushroom_worker_jobs.py`
  y `tests/test_web_server_auth.py`.
- Release: `docs/release-flow.md`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo para prioridades completas.
- Cumplir `AGENTS.md` y usar Codebase Memory MCP antes de descubrir o cambiar
  código.
- Preservar cambios locales y ficheros no rastreados.
- No usar Tailscale; no tocar HA real, cambiar retención ni borrar datos.
- No lanzar entrenamientos ni hacer otro bump, build, publicación, instalación
  o release sin autorización explícita nueva.
- Aplicar validación proporcional y terminar con `git diff --check`.
