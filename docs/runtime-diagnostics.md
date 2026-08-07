# Diagnóstico de memoria y rendimiento en Home Assistant

## Estado

Especificación e implementación local completadas el 2026-08-07 para validar el
runner y el Predictor en la RPi4 antes de cerrar el P0 de memoria. Está pendiente
de incluirse en la siguiente release normal que autorice el usuario. No requiere
una imagen de desarrollo ni vigilancia manual durante las ejecuciones.

## Objetivos

- Medir por separado el runner periódico y la carga fría del Predictor.
- Conservar los picos breves que las gráficas de Home Assistant pueden omitir.
- Confirmar que el proceso hijo del runner libera su memoria al terminar.
- Medir la memoria retenida por la caché compartida del Predictor.
- Evitar que el runner coincida con una petición del Predictor o con su caché
  meteorológica retenida.
- Producir un paquete descargable y seguro para análisis posterior.

## Persistencia y retención

Los eventos se escriben como JSON Lines en:

```text
/share/rainmapper/diagnostics/runtime_metrics.jsonl
```

El historial conserva como máximo 2.000 eventos y se compacta cuando supera
5 MiB. Cada línea es autocontenida y usa `schema_version=1.0`. La escritura de
diagnósticos nunca debe hacer fallar una actualización o una predicción.

El paquete descargable contiene únicamente:

- `runtime_metrics.jsonl`;
- `last_run.log`;
- `manifest.json` con versión y fecha de exportación.

No incluye opciones, credenciales, observaciones, media, coordenadas privadas,
modelos ni históricos meteorológicos. Antes de añadir `last_run.log`, el
exportador conserva como máximo sus 2 MiB finales y oculta parámetros habituales
de credenciales y cabeceras Bearer.

## Métricas

Cada operación tiene un `operation_id`, un tipo y varias fases. Los snapshots
registran, cuando el sistema los expone:

- RSS actual y pico RSS del proceso;
- memoria actual, pico y límite del cgroup del add-on;
- `MemAvailable` del host;
- tiempo de CPU de usuario y sistema;
- CPU consumida como porcentaje equivalente de un núcleo durante la operación;
- temperatura de CPU;
- contadores `oom` y `oom_kill` del cgroup;
- tiempo de pared de la operación.

El coordinador `runner_action` mide toda la acción (`update`, `maps` o `all`) y
el consumo total del cgroup mientras viven sus procesos hijos. El proceso
`runner_update` añade fases antes del Parquet, después del Parquet, después del
catálogo y al finalizar; registra además filas, row groups y tamaños de los
artefactos. Tras acabar se guardan snapshots de recuperación a 60 y 600 segundos.

La carga física `predictor_weather_load` registra número de estaciones,
registros y tamaño del filtro. También conserva snapshots a 60 y 600 segundos
para observar la caché retenida. Las visitas que reutilizan la misma caché no
duplican una supuesta carga fría.

## Exclusión runner/Predictor

- Una petición del Predictor mantiene un lock durante su renderizado.
- El runner espera a que termine esa petición antes de arrancar.
- Al arrancar cualquier acción del runner se liberan las instancias y la caché
  meteorológica del Predictor.
- Mientras `RUN_STATE.running` sea verdadero, Predictor muestra un aviso y no
  inicia cálculos.
- Al terminar el runner, la siguiente consulta crea una caché nueva contra el
  Parquet vigente.

Esto garantiza la exclusión en el servidor; no depende de que el usuario mire
el schedule o cierre una pestaña en un momento concreto.

## Uso sin vigilancia manual

Los registros se crean solos tanto para ejecuciones manuales como programadas.
No es necesario mantener abierta la pantalla de Home Assistant ni observar sus
gráficas. Una vez terminada la prueba y transcurridos los 10 minutos de
recuperación, abrir el panel de Rainmapper y pulsar **Download diagnostics** en
las acciones rápidas o en la pestaña **Logs**. El ZIP resultante se puede guardar
y compartir para analizarlo posteriormente.

## Procedimiento de validación en RPi4

### Ensayo A — runner real

1. Instalar la release corregida sin abrir Predictor.
2. Reiniciar el add-on y esperar 10 minutos para estabilizar el estado base.
3. Ejecutar manualmente la misma acción usada por el schedule, normalmente
   `all`.
4. Esperar a que termine; no es necesario vigilar la ejecución.
5. Dejar después 10 minutos de reposo para que se escriba `recovery_600s`.
6. Descargar el paquete con **Download diagnostics** desde el panel.
7. Verificar duración de `update` y `maps`, pico RSS, mínimo `MemAvailable`,
   temperatura, eventos OOM y retorno de memoria tras finalizar.

### Ensayo B — Predictor monousuario

1. Reiniciar el add-on conservando el Parquet generado en el ensayo A.
2. Esperar 10 minutos sin abrir Predictor.
3. Abrir la vista predeterminada y esperar a que finalice la carga fría.
4. Visitar Por especie, Consultar fecha e Historial y realizar varias consultas
   representativas.
5. No lanzar manualmente el runner durante este ensayo; el servidor bloqueará
   igualmente cualquier coincidencia accidental.
6. Cerrar o abandonar la vista y esperar al menos 10 minutos para capturar
   `retained_600s`; no es necesario mantener la pantalla abierta.
7. Descargar un segundo paquete de diagnóstico.

### Ensayo C — exclusión automática

1. Después de haber usado Predictor, lanzar `update` o esperar al siguiente
   schedule.
2. Comprobar que Predictor muestra el aviso de runner activo.
3. Confirmar en el diagnóstico que la caché se liberó antes del proceso hijo y
   que no hubo `oom_kill`.

## Criterio de cierre

El P0 solo se cierra después de revisar los paquetes reales de la RPi4 y
confirmar que:

- runner y Predictor terminan sin OOM, reinicio ni pérdida de conectividad;
- el runner finaliza con margen amplio respecto al intervalo de tres horas;
- la memoria vuelve cerca del estado base después del runner;
- las consultas repetidas no generan crecimiento acumulativo;
- temperatura y alimentación permanecen estables;
- el Parquet regenerado usa row groups filtrables.

Los límites numéricos definitivos se fijarán con la primera medición real, no
por extrapolación desde el Mac.

## Validación local

El 2026-08-07 pasó `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh` completo
para `0.2.227`: 462 tests, compilación Python, parseo JavaScript, fixtures operativas y
comprobación de whitespace. Esto valida los contratos y la integración local;
no sustituye los ensayos A–C sobre la RPi4.
