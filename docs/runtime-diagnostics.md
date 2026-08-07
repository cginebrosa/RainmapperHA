# Diagnóstico de memoria y rendimiento en Home Assistant

## Estado

Especificación e implementación incluidas en la release `0.2.227`, publicada el
2026-08-07 para validar el runner y el Predictor en la RPi4 antes de cerrar el P0
de memoria. Sigue pendiente la validación en la RPi4 real. No requiere una imagen
de desarrollo ni vigilancia manual durante las ejecuciones.

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

## Cadencia de muestreo y espera de recuperación

La espera de 10 minutos no significa que el sistema escriba métricas de forma
continua durante todo ese periodo. El ciclo exacto es:

1. Al comenzar una operación se guarda un snapshot inicial.
2. Mientras el runner o la carga física del Predictor siguen activos, se toma
   una muestra cada 0,5 segundos. Estas muestras se agregan en memoria para
   conservar máximos y mínimos; no se escribe una línea al fichero cada medio
   segundo.
3. Las fases relevantes escriben eventos puntuales y, al terminar la operación,
   se detiene inmediatamente el muestreo periódico y se guarda el resumen.
4. Después del final solo se programan dos fotografías puntuales del sistema:
   una a los 60 segundos y otra a los 600 segundos. No existe muestreo continuo
   entre ambas.

El snapshot de 600 segundos permite comprobar si memoria, CPU y temperatura se
han recuperado, o cuánta memoria conserva la caché del Predictor. Para que se
escriba, el add-on debe continuar en ejecución: no reiniciarlo ni detenerlo
durante esos 10 minutos. No es necesario mantener abierta ninguna pantalla.

Una vez guardado `recovery_600s` o `retained_600s`, el registro permanece en
`/share/rainmapper/diagnostics/runtime_metrics.jsonl` hasta su compactación
acotada. El ZIP se puede descargar más tarde; no hay una ventana de descarga de
solo 10 minutos. Conviene esperar unos segundos adicionales tras los 10 minutos
antes de pulsar **Download diagnostics**.

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

## Resultado real — Ensayo A en RPi4 (`0.2.227`)

El primer paquete real se exportó el 2026-08-08, después de una ejecución
programada `all` iniciada a las 00:09:55 y finalizada correctamente a las
00:16:57 (hora local). Resultado:

- duración total: 421,3 s (7 min 2 s); `update`: 343,4 s y `maps`: 56,2 s;
- exit code 0, sin reinicios, `oom=0` y `oom_kill=0`;
- pico RSS del proceso hijo: 1.222,5 MiB; pico RSS histórico: 1.243,6 MiB;
- máximo observado del cgroup: 1.334,0 MiB y pico del cgroup: 1.347,8 MiB;
- mínimo `MemAvailable` del host: 670,0 MiB;
- temperatura máxima: 52,58 °C;
- Parquet: 625.529 filas, 1.222 row groups, 12,0 MiB y 28,2 s de generación;
- catálogo: generado correctamente, 79,3 KiB;
- Wunderground: 98/98 estaciones, cero fallos y cero errores de fallback;
- AEMET, Meteoclimatic, Meteocat, Tomap, GeoJSON y publicación MapLibre
  finalizaron correctamente.

La memoria del proceso hijo se liberó al terminar `update`: el cgroup bajó de
aproximadamente 999 MiB a 211 MiB y `MemAvailable` subió de 1.332 MiB a
2.108 MiB. En `recovery_60s` se observaron 495 MiB de cgroup, 34,6 MiB de RSS
del servidor y 2.123 MiB disponibles en el host; en `recovery_600s`, 510 MiB,
49,8 MiB y 2.027 MiB respectivamente. El cgroup quedó por encima de su lectura
inicial de 247 MiB, pero el RSS del servidor quedó muy por debajo de los
139 MiB iniciales y la memoria disponible del host terminó por encima del valor
inicial de 1.884 MiB. No hay indicios de fuga RSS del runner; la retención del
cgroup es compatible con caché de páginas, aunque las ejecuciones posteriores
permitirán comprobar que no exista crecimiento acumulativo.

Conclusión del Ensayo A: el runner cabe en la RPi4 en esta ejecución, termina con
margen amplio frente al intervalo de tres horas, regenera el layout filtrable y
recupera la memoria del proceso hijo sin OOM ni presión térmica preocupante. No
se cierra todavía el P0 global: faltan reconstruir/reentrenar los modelos y
completar los ensayos B y C del Predictor.

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
