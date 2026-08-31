# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-31

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  El HEAD anterior a esta release era
  `fdce07efab314c1efb78f8bab27aa8da3a502013`; revalidar HEAD al comenzar.
- El código declara HA `0.2.286` y worker `1.0.33`.
- HA `0.2.286` y `latest` están publicados en GHCR con el mismo índice OCI
  `sha256:57783c36e1a6f6f8fe577f6066676a1a3e2983a80f9df2ddc7639755edfdbc37`
  y manifests `linux/amd64` y `linux/arm64`.
- HA real ejecuta `0.2.286` según confirmación del usuario. Hay un precálculo
  real en curso sobre worker `1.0.33`; alcanzó `20.88/143` y 19 % total sin
  repetir el rechazo de cobertura que antes aparecía al 11 %.
- El worker privado no se publica. Está reconstruido localmente como `1.0.33`,
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

## E2E real y corrección 0.2.286/1.0.33

- El job real `worker_job_WLFWlFqhHJtU`, cobertura
  `2026-08-31` → `2026-09-06`, falló tras 6 min 11 s al 10 % visible con
  `Base prediction is outside planned coverage.`
- HA `0.2.285` corrigió la vista semanal, pero el segundo E2E real reveló que la
  ruta consulta-fecha/todas-las-áreas y varias ayudas internas aún comparaban
  contra `date.today()` del worker UTC. El job de revisión 3 falló al 11 % con
  `amanita_caesarea/breda/2026-08-30` fuera de la cobertura planificada
  `2026-08-31` → `2026-09-06`.
- `PredictorService` usa ahora el `issue_date` sellado en consulta por área,
  comparaciones preferida/multiversión, semana, prewarm meteorológico y
  retargeting. `date.today()` queda únicamente como valor por defecto al
  normalizar una petición que no trae fecha.
- El precálculo remoto ya no hace peticiones síncronas de control/progreso en
  cada callback científico. Una telemetría de fondo coalesce el último estado
  con cadencia de 10 s, conserva cancelación y vacía el progreso antes de subir
  el resultado. Los timeouts observados en el job fallido ya no bloquean el
  cálculo.
- Los jobs remotos `predictor_precompute_v1` enlazan al mismo modal de detalle
  que los locales; el servidor puede construir ese detalle desde el estado
  persistido del job externo.
- Un job fallido o cancelado de la revisión vigente aparece como terminal en
  Workers, panel y Predictor, conserva su error y no se reclasifica como `En
  cola`. El reconciliador reconoce también jobs terminales de la misma revisión
  para no relanzarlos tras reiniciar HA; una petición manual o del runner crea
  una revisión nueva.

## Validación y release

- 423 pruebas dirigidas correctas.
- Smoke definitivo: 1.185 pruebas, compiladores, validadores y fixtures
  correctos.
- `git diff --check` correcto antes de la release; repetir tras documentación.
- Worker `1.0.33` construido y verificado healthy/idle, con identidad, volumen
  y capacidades conservados.
- HA `0.2.286` publicada y verificada en GHCR; falta instalarla y validar el E2E.

## Próximos pasos inmediatos

1. Dejar terminar el precálculo real ya iniciado sobre worker `1.0.33` y
   registrar resultado, duración, tamaño transferido y activación del SQLite.
2. Confirmar que el SQLite queda activo en `/media`, que HA sirve hits en las
   cuatro rutas y que un miss solicita ejecutor para fallback.
3. Rediseñar el modal de progreso: hoy mezcla `20.88/143`, grupo, consulta,
   especie/área, tres etapas, progreso total, progreso de paso y dos ETA sin una
   jerarquía comprensible. Antes de tocarlo, definir nombres y unidades para
   avance global, etapa de publicación y subpaso científico.
4. Medir por separado preparación, cálculo, telemetría, transferencia y
   activación. Comparar el tramo inicial con los ~90 s locales; el E2E fallido
   tardó 6 min 11 s hasta el primer rechazo y registró timeouts de heartbeat.
5. Solo después, perfilar `Building weekly matrix` por especie y optimizar el
   coste dominante medido. Objetivo orientativo: menos de diez minutos.

## Riesgos y dudas activos

- `0.2.286` está instalada y ha superado el punto del fallo anterior, pero el
  E2E sigue en curso: no afirmar todavía que cálculo, transferencia, validación
  y activación hayan terminado correctamente.
- El circuito worker → transferencia → activación HA todavía no ha completado
  un E2E real. El SQLite local de referencia ocupó 462.974.976 bytes.
- La coalescencia elimina espera de red del callback, pero su mejora temporal
  real debe medirse; no asumir que explica todo el diferencial local/remoto.
- La UI de jobs aún no ofrece duración integral ni ETA global científicamente
  fiables. El modal actual funciona, pero su combinación de fracciones,
  porcentajes, fases y ETA no resulta comprensible para el usuario.
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
