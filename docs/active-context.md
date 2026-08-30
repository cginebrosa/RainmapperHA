# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-31

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  El HEAD anterior a esta release era
  `c02b4b8b6ca39f72deedcb0caf6f1d8e5d2d8eef`; revalidar HEAD al comenzar.
- El código declara HA `0.2.285` y worker `1.0.32`.
- HA `0.2.285` y `latest` están publicados en GHCR con el mismo índice OCI
  `sha256:aa4a1d39bffd501288b0ffb630d85bb8907818cdce3fc25bef3759c87c0c2333`
  y manifests `linux/amd64` y `linux/arm64`.
- La última versión confirmada en HA real es `0.2.284`. El usuario todavía debe
  instalar `0.2.285` y repetir el precálculo real.
- El worker privado no se publica. Está reconstruido localmente como `1.0.32`,
  healthy/idle, con identidad `worker_1a9a232c20fe2ee2`, volumen
  `rainmapper-worker-data`, cachés válidas y capacidad
  `predictor_precompute_v1`.
- No hay entrenamientos programados. No tocar retención, datos reales, HA real
  ni lanzar entrenamientos, bumps, builds o publicaciones sin autorización.

## Resultado operativo entregado

El precálculo semanal SQLite sigue implementado con identidad científica,
integridad/cobertura, sustitución atómica, lookup en HA, cobertura de todas las
versiones y fallback íntegro. El artefacto se publica bajo
`/media/rainmapper/predictor_precompute`, fuera del backup. La ejecución manual
y el trigger asíncrono posterior al runner usan el worker predeterminado.

HA `0.2.284` estabilizó la presencia del worker y eliminó el cálculo pesado de
la petición heartbeat. La UI Workers volvió a abrir rápidamente en la RPi4.

## Primer E2E real y corrección 0.2.285/1.0.32

- El job real `worker_job_WLFWlFqhHJtU`, cobertura
  `2026-08-31` → `2026-09-06`, falló tras 6 min 11 s al 10 % visible con
  `Base prediction is outside planned coverage.`
- No estaba realmente en 0/143: el porcentaje entero ocultaba el avance dentro
  del primer grupo. El worker en UTC construía la semana desde `date.today()`
  (`2026-08-30`) mientras HA había planificado desde su `issue_date`
  (`2026-08-31`). El escritor rechazó correctamente la fila fuera de cobertura.
- `PredictorService` usa ahora siempre el `issue_date` sellado. El error de
  cobertura incluye especie, área y fecha, y el progreso admite fracciones para
  mostrar avance desde el primer grupo.
- El precálculo remoto ya no hace peticiones síncronas de control/progreso en
  cada callback científico. Una telemetría de fondo coalesce el último estado
  con cadencia de 10 s, conserva cancelación y vacía el progreso antes de subir
  el resultado. Los timeouts observados en el job fallido ya no bloquean el
  cálculo.
- Los jobs remotos `predictor_precompute_v1` enlazan al mismo modal de detalle
  que los locales; el servidor puede construir ese detalle desde el estado
  persistido del job externo.

## Validación y release

- 385 pruebas dirigidas correctas.
- Smoke definitivo: 1.181 pruebas, compiladores, validadores y fixtures
  correctos.
- `git diff --check` correcto antes de la release; repetir tras documentación.
- Worker `1.0.32` construido y verificado healthy/idle, con identidad, volumen
  y capacidades conservados.
- HA `0.2.285` publicada y verificada en GHCR; falta instalarla y validar el E2E.

## Próximos pasos inmediatos

1. Instalar HA `0.2.285` y confirmar la versión en runtime.
2. Lanzar un único precálculo real sobre worker `1.0.32` y comprobar que el
   modal muestra especie/área/paso y progreso desde el primer grupo.
3. Medir por separado preparación, cálculo, telemetría, transferencia y
   activación. Comparar el tramo inicial con los ~90 s locales; el E2E fallido
   tardó 6 min 11 s hasta el primer rechazo y registró timeouts de heartbeat.
4. Verificar que el SQLite queda activo en `/media`, que HA sirve hits en las
   cuatro rutas y que un miss solicita ejecutor para fallback.
5. Solo después, perfilar `Building weekly matrix` por especie y optimizar el
   coste dominante medido. Objetivo orientativo: menos de diez minutos.

## Riesgos y dudas activos

- `0.2.285` está publicada pero aún no instalada ni probada en HA real.
- El circuito worker → transferencia → activación HA todavía no ha completado
  un E2E real. El SQLite local de referencia ocupó 462.974.976 bytes.
- La coalescencia elimina espera de red del callback, pero su mejora temporal
  real debe medirse; no asumir que explica todo el diferencial local/remoto.
- La UI de jobs aún no ofrece duración integral ni ETA global científicamente
  fiables.
- El fallback en HA real debe conservar selección explícita de ejecutor; nunca
  asumir cálculo pesado local en la RPi4.
- `/share/rainmapper` contenía 317,6 MiB revisables: seis bundles terminales
  (179,6 MiB) y un TAR legacy (138 MiB). No borrar ni cambiar retención. El TAR
  solo puede retirarse tras verificar su sustituto bajo `/media`.

## Archivos relevantes

- Especificación: `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`.
- Artefacto/control: `rainmapper_core/mushroom_predictor_precompute.py` y
  `rainmapper_core/mushroom_predictor_precompute_control.py`.
- Lookup/fecha: `rainmapper_core/mushroom_predictor_service.py`.
- Telemetría worker: `rainmapper_core/mushroom_worker_service.py`.
- Coordinador/UI: `rainmapper-app/app/web_server.py` y
  `rainmapper-app/app/mushroom_workers_ui.py`.
- Pruebas: `tests/test_mushroom_predictor_precompute.py`,
  `tests/test_mushroom_predictor_service.py` y `tests/test_web_server_auth.py`.
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
