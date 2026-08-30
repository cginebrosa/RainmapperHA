# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-30

- Workspace verificado: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama
  `inicial`. El HEAD previo al commit de esta entrega era
  `32ee344d8f150d6400fe3e522bbf345bab5d4c9e`; revalidar HEAD al continuar.
- El código declara HA `0.2.281` y worker `1.0.30`.
- HA `0.2.281` y `latest` están publicados con el mismo índice OCI
  `sha256:892fa5accda4b2588c7e6abc65a91b6058155a9d43893fe032a00cb1dc415fd0`
  y manifests `linux/amd64` y `linux/arm64`. La instalación en HA real no
  está confirmada; corresponde al usuario.
- El worker no se publica. Se reconstruyó localmente como `1.0.30`, conservando
  identidad `worker_1a9a232c20fe2ee2` y volumen `rainmapper-worker-data`. Su
  health local confirmó `idle`, versión `1.0.30` y capacidad
  `predictor_precompute_v1`; revalidar antes de afirmar estado futuro.
- La retención ML real permanece activa por decisión del usuario. No cambiarla,
  no borrar datos manualmente y no relajar hashes, cancelación, retry, rollback
  ni promoción atómica.
- No existen entrenamientos programados. El usuario inicia manualmente los
  entrenamientos reales.

## Resultado principal

El precálculo semanal del Predictor quedó implementado y validado localmente:

- SQLite regenerable con identidad científica separada del SHA-256 del fichero,
  validación de esquema, cobertura, integridad y sustitución atómica;
- cobertura de todas las especies y áreas, siete días y todas las versiones
  operativas instaladas; las respuestas multiversión se componen desde los
  bloques precalculados sin enumerar combinaciones;
- lookup primero en HA, hits sin job y fallback íntegro al Predictor vivo ante
  miss, invalidez o cobertura insuficiente;
- estado deseado latest-wins, job manual desde el panel, ejecución local de
  laboratorio y capacidad equivalente en el worker privado;
- publicación verificada, transferencia y activación coordinadas; almacenamiento
  HA en `/media/rainmapper/predictor_precompute`, fuera del backup del add-on;
- estado visible tanto en Workers como en la esquina superior derecha del
  Predictor (`usado`, `en curso`, `no disponible`, etc.);
- el runner meteorológico solicita el precálculo de forma asíncrona al terminar
  sus tareas, sin esperar su cálculo.

El artefacto local validado tras actualizar la meteorología tenía:

- `artifact_id`:
  `sha256:2cefebb587df908064786dc9980e9447c1b9349152c70460b090ddaef8ddbbea`;
- SHA-256 del fichero:
  `sha256:3138636eaa498c1af7767121d4998008d1b4cd0d532fd10a6fe01234f893f0d6`;
- tamaño `462974976` bytes, 623 respuestas y 143 payloads;
- `quick_check`, cobertura, contadores y SHA correctos.

La comparación automática local cubrió cuatro rutas con datos: recommender,
semana, multiversión de un área y consulta de fecha/todas las áreas. Las cuatro
fueron científicamente idénticas entre SQLite y cálculo vivo, ignorando solo la
telemetría de ejecución; los hashes comparados coincidieron. Los lookups tardaron
0,03–0,11 s y los cálculos vivos 0,15–31,34 s. El usuario también validó la
navegación local y confirmó su mejora.

## Validación y release

- Smoke completo definitivo: 1.164 pruebas y todos los validadores correctos.
- Pruebas dirigidas de empaquetado detectaron y corrigieron la ausencia inicial
  de los dos módulos de precálculo en la imagen privada del worker; 322 pruebas
  dirigidas pasaron después.
- `git diff --check` correcto antes de preparar el commit.
- Worker privado `1.0.30` reconstruido y health verificado.
- Imagen HA `0.2.281` publicada y verificada en GHCR para amd64/arm64; versión y
  `latest` comparten digest.
- No repetir el smoke por cambios exclusivamente documentales o por el commit.

## Próxima prueba real

1. El usuario instala HA `0.2.281`.
2. Confirmar en la UI la versión instalada y que HA reconoce el worker `1.0.30`
   con `predictor_precompute_v1`.
3. Lanzar manualmente un precálculo real. Verificar que calcula en el worker
   preferido, publica el SQLite en `/media/rainmapper/predictor_precompute` y HA
   lo activa sin incluirlo en el backup.
4. Comparar consultas con datos en las cuatro rutas ya verificadas localmente;
   deben indicar `Precálculo: usado` y responder desde HA sin usar el worker.
5. Forzar o esperar un miss controlado y comprobar que la UI pregunta dónde
   ejecutar el fallback; HA real no debe asumir el cálculo pesado local.
6. Medir duración, tamaño y transferencia reales. La optimización de
   `Building weekly matrix` queda para después de este E2E.

## Riesgos y deuda activos

- La instalación de HA `0.2.281` y el circuito worker→HA no se han validado aún
  en el entorno real.
- El SQLite local ocupa unos 442 MiB; la transferencia real y el comportamiento
  de `/media` en la RPi4 deben medirse, no estimarse.
- La construcción local observada rondó catorce minutos y concentra tiempo en
  `Building weekly matrix` por especie. Falta perfilado antes de optimizar.
- La UI de trabajos aún hereda limitaciones históricas de duración integral y
  ETA; no inferir costes de red solo por el nombre de una fase.
- El fallback en HA real debe conservar la selección explícita de ejecutor; es
  especialmente importante cuando el SQLite no cubre una consulta.

## Archivos relevantes

- Especificación: `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`.
- Artefacto/control: `rainmapper_core/mushroom_predictor_precompute.py` y
  `rainmapper_core/mushroom_predictor_precompute_control.py`.
- Predictor: `rainmapper_core/mushroom_predictor_service.py`,
  `rainmapper_core/mushroom_ml_multiversion_comparison.py` y
  `rainmapper-app/app/mushroom_predictor_ui.py`.
- Worker/coordinador: `rainmapper_core/mushroom_worker_jobs.py`,
  `rainmapper_core/mushroom_worker_service.py`,
  `rainmapper_core/mushroom_worker_registry.py` y
  `rainmapper-app/app/web_server.py`.
- Pruebas: `tests/test_mushroom_predictor_precompute.py`,
  `tests/test_mushroom_predictor_service.py`,
  `tests/test_mushroom_worker_jobs.py` y `tests/test_web_server_auth.py`.
- Release: `docs/release-flow.md`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo para prioridades completas.
- Cumplir `AGENTS.md` y usar Codebase Memory MCP antes de descubrir o cambiar
  código.
- Preservar todos los cambios locales y ficheros no rastreados.
- No usar Tailscale, no tocar HA real, no cambiar retención y no borrar datos.
- No lanzar entrenamientos ni hacer otro bump, build, publicación, instalación
  o release sin autorización explícita nueva.
- Aplicar validación proporcional y terminar siempre con `git diff --check`.
