# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-31

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  HEAD revalidado antes de los cambios locales:
  `6a4defcd45226731ef2dd5a92f0526f2f62a8d19`.
- El código declara HA `0.2.287` y worker `1.0.34`.
- HA `0.2.287` y `latest` están publicados en GHCR con el mismo índice OCI
  `sha256:e72606a9fe95667252f45c864a921989bfa2e95c14d1adff5a1e26fb2d79569c`
  y manifests `linux/amd64` y `linux/arm64`.
- HA real no se modificó durante esta entrega. Su última versión confirmada por
  el usuario es `0.2.286`; el usuario confirmó que ahora no hay precálculos.
- El worker privado no se publica. Está reconstruido localmente como `1.0.34`,
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

## Cambios publicados en 0.2.287

- El modal de precálculo distingue avance global, etapa y subpaso científico;
  especie y área quedan como trazabilidad secundaria. Las fichas de los siete
  días abren el mismo modal durante cálculo o recuperación.
- Los jobs remotos de reconstrucción, ML v0 y V2--V6 enlazan a su modal de
  progreso. El estado local ya no presenta como `En cola` un deseo sin job.
- La preparación SoilGrids limita a 10 s las consultas persistidas de
  cancelación/progreso y conserva siempre el estado final. La cadena
  reconstrucción → ML v0 → V2--V6 omite la reconciliación completa entre
  sucesores; la conserva al terminar la cadena o si falla la preparación.
- Los datos propios y fuentes continúan en `/share`: meteorología,
  observaciones, fotos/vídeos, perfiles, catálogos, zonas, mappings,
  credenciales, cola y registro de versiones.
- Los derivados nuevos viven en
  `/media/rainmapper/mushroom-derived`: artefactos de reconstrucción, modelos,
  bundles, resultados privados y cuerpos pesados de Predictor. Precálculo,
  GIS/SoilGrids y caché TAR ya estaban en `/media`.
- La transición copia y verifica artefactos legacy sin sobrescribir destinos
  diferentes ni borrar el origen. Un recibo en `/media` evita repetir el
  inventario en cada arranque; si `/media` se pierde, el recibo desaparece y la
  recuperación se vuelve a evaluar.
- Validado un arranque aislado con `/share` y `/media` vacíos: la app inicia,
  siembra únicamente defaults editables en `/share` y muestra Predictor sin
  modelos instalados. En el laboratorio real de desarrollo se copiaron 6.670
  ficheros sin conflictos ni errores y el segundo arranque no repitió la copia.
- HA real no se modificó. La reducción efectiva del backup requiere retirar
  posteriormente las copias legacy de `/share`, sólo con autorización y tras
  validar la versión instalada.

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

- Smoke local actual: 1.199 pruebas correctas, además de compilación, JSON,
  transición con datos legacy y arranque con `/media` vacío. Las 370 pruebas
  dirigidas de jobs, worker y servidor web también pasan tras la nueva
  telemetría.
- `git diff --check` correcto tras código y pruebas; repetir al cierre.
- Worker `1.0.34` construido y verificado healthy/idle, con identidad, volumen,
  cachés y capacidades conservados. Ambas lanes estaban idle en la comprobación.
- HA `0.2.287` publicada y verificada en GHCR. El primer push agotó el plazo
  después de subir capas y no creó el tag; un reintento completó ambos tags con
  el índice multiarch indicado arriba. Falta instalarla y validar en HA real.

## Próximos pasos inmediatos

1. Instalar HA `0.2.287` sólo con autorización explícita y comprobar la UI, el
   almacenamiento derivado y la compatibilidad con worker `1.0.34`.
2. Tras instalar esa versión, medir una cadena real completa para confirmar la
   reducción de las esperas de 1--2 minutos. Las pruebas demuestran que se han
   eliminado llamadas repetidas, pero no sustituyen esa medición real.
3. Verificar rutas y Predictor sobre `/media`; sólo entonces autorizar, si se
   desea, la retirada de copias legacy de `/share` para reducir el backup.
4. En la siguiente ejecución real, revisar la instrumentación ya instalada en
   el worker. Registra cinco transiciones por precálculo, resumen de fases,
   número de polls vacíos antes del claim y tiempo real hasta liberar el hilo.
   No escribe por predicción ni añade llamadas a HA.

## Diagnóstico de los precálculos posteriores al reentrenamiento

- El job creado a las `17:06:25` no fue reclamado por el worker hasta las
  `17:40:15`: `33 min 50 s` ocurrieron antes de empezar la ejecución. La UI
  mezclaba `created_at` para la hora visible con `started_at` para la duración;
  ahora muestra por separado `Antes de ejecutar` y `Ejecución`.
- En ese job los avisos de sklearn sí coincidieron con el cálculo: 331 líneas
  entre `17:40:32` y `17:57:35`. Una consulta representativa, los seis tipos de
  pipeline y los ocho RandomForest V0 no reprodujeron el aviso de forma
  aislada. No hay evidencia suficiente para atribuirlo aún a un estimador
  concreto.
- Los dos runtimes lentos retenidos por el worker tienen los mismos modelos,
  contratos y datos de perfiles/observaciones. Sólo cambiaron 13 ficheros de
  rol meteorológico (5.279.670 frente a 5.277.740 bytes en esos ficheros). El
  runtime rápido anterior ya no está retenido, por lo que no puede hacerse una
  comparación binaria completa con él.
- La instrumentación local del worker mide sincronización de selecciones,
  runtime, preparación del servicio, cálculo, subida/publicación, activación y
  total. No modifica filtros de avisos ni la inferencia: localizar el estimador
  exacto del aviso sigue pendiente de una reproducción que lo dispare.

## Riesgos y dudas activos

- La causa de los `33 min 50 s` anteriores al claim no está demostrada con los
  datos históricos disponibles. La siguiente ejecución instrumentada
  distinguirá entre polls de cola vacíos y un carril/hilo retenido.
- El aviso sklearn está localizado temporalmente pero no en un estimador
  concreto. No se ha ocultado el aviso ni cambiado el runtime para evitar
  atribuirlo sin evidencia.
- La coalescencia elimina espera de red del callback, pero su mejora temporal
  real debe medirse; no asumir que explica todo el diferencial local/remoto.
- La tabla ya separa el tiempo anterior a ejecutar del tiempo de ejecución. La
  ETA global continúa siendo orientativa y debe contrastarse con una ejecución
  real instrumentada.
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
