# Diagnóstico de memoria y rendimiento en Home Assistant

## Estado

Especificación e implementación incluidas en la release `0.2.227`, publicada el
2026-08-07 para validar el runner y el Predictor en la RPi4 antes de cerrar el P0
de memoria. Los ensayos A, B y C reales están completados y el P0 de memoria se
cierra para el escenario monousuario probado. No requiere una imagen de
desarrollo ni vigilancia manual durante las ejecuciones.

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

`predictor_weather_load` mide únicamente la lectura y materialización del
Parquet meteorológico compartido. No mide la latencia completa desde el clic en
el panel hasta que el navegador muestra la página: quedan fuera del monitor el
resto de `render_page()`, los cálculos de la vista, la generación/envío del HTML,
HA Ingress y el renderizado del navegador. El tiempo extremo a extremo debe
registrarse por separado hasta que exista instrumentación de la petición
completa.

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

## Evolución pendiente después de los ensayos A–C

No modificar la instrumentación actual hasta terminar A–C: cambiarla durante la
serie impediría comparar los paquetes bajo el mismo contrato. Después deben
abordarse dos mejoras distintas.

### Afinar la medición de carga fría del Predictor

La operación actual `predictor_weather_load` es una subfase interna y no puede
usarse como tiempo total de apertura. Añadir una operación correlacionada para
la petición completa del Predictor que distinga, como mínimo:

1. entrada en el manejador HTTP y carga de perfiles/setales;
2. inicialización y carga de modelos;
3. carga o reutilización de la caché meteorológica;
4. cálculos de la vista solicitada;
5. generación del HTML y envío de la respuesta;
6. tiempo de navegación/renderizado del navegador, medido aparte del servidor.

Debe registrar si la petición es fría o caliente y permitir separar tiempo de
RPi4, HA Ingress/red y cliente. No debe añadir observaciones, ubicaciones ni
resultados predictivos privados al diagnóstico.

### Convertir el diagnóstico en una caja negra persistente

El JSONL actual sobrevive a reinicios y actualizaciones porque vive en `/share`,
pero no es un histórico indefinido: rota a 2.000 eventos o 5 MiB, los snapshots
diferidos solo existen como temporizadores en memoria y `last_run.log` se
sobrescribe. Una muerte del contenedor puede conservar el inicio de una
operación, pero perder su cierre y los snapshots pendientes sin explicar la
interrupción.

La evolución debe mantener bajo el coste de CPU, escrituras y almacenamiento:

- conservar un nivel detallado circular para las operaciones recientes;
- guardar además un resumen histórico pequeño por operación, con versión,
  inicio/fin, resultado, duración, picos, OOM y recuperación;
- persistir atómicamente operaciones y snapshots pendientes; al arrancar,
  reconciliarlos y marcar como `interrupted` lo que no terminó, sin inventar la
  causa si no existe evidencia de OOM;
- registrar arranque/parada e identificador de arranque para correlacionar
  reinicios del add-on o de la RPi4;
- agregar un muestreo de fondo ligero en memoria y escribir solo resúmenes
  periódicos o anomalías, evitando un log continuo de alta frecuencia;
- conservar por `operation_id` una cola acotada de logs de operaciones fallidas,
  en lugar de depender únicamente del último runner;
- incluir detalle reciente, histórico resumido, interrupciones y anomalías en
  el ZIP, manteniendo la redacción de secretos y el contenido privado fuera;
- mostrar en el panel la última ejecución correcta, último fallo/interrupción,
  último OOM y máximos recientes.

La conservación realmente indefinida no puede depender solo del almacenamiento
de la RPi4: los resúmenes deben poder incluirse en backups o copiarse fuera del
dispositivo. La retención detallada seguirá siendo acotada; lo que se conserva a
largo plazo son resúmenes y anomalías suficientes para explicar qué ocurrió.

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
se cerró el P0 en ese momento porque todavía faltaban los ensayos B y C.

## Resultado real — Ensayo B en RPi4 (`0.2.228`)

El paquete se exportó el 2026-08-07 a las 23:44:48 UTC, antes de que comenzara
el siguiente runner programado. Contiene una única carga física del Predictor
con sus snapshots `retained_60s` y `retained_600s`, sin interferencia del runner:

- evidencia: `rainmapper-diagnostics-20260807T234448Z.zip`, SHA-256
  `04c1a35006e7d99f7425405f25a175d0ea2f9d184df76ffdcc254af11429d9b4`;

- subfase instrumentada `predictor_weather_load`: 8,667 s;
- tiempo manual extremo a extremo percibido por el usuario, desde pulsar el
  botón hasta ver la pantalla: al menos unos 30 s;
- 115 estaciones y 79.931 registros cargados desde un Parquet de 11,968 MiB;
- RSS del proceso: 241,4 MiB al inicio, pico observado posterior de 352,5 MiB y
  337,8 MiB a los 600 s;
- cgroup: 290,1 MiB al inicio, pico de 423,2 MiB y 409,4 MiB a los 600 s;
- `MemAvailable`: mínimo de 1.727,8 MiB durante la carga y 1.752,8 MiB a los
  600 s;
- temperatura máxima instrumentada: 48,69 °C; 44,79 °C a los 600 s;
- CPU de la subfase meteorológica: 10,676 s de CPU en 8,667 s de pared,
  equivalente al 123,2 % de un núcleo;
- `oom=0` y `oom_kill=0` en todos los eventos.

Entre 60 y 600 s el RSS solo cambió de 337,1 a 337,8 MiB y el cgroup de 407,1 a
409,4 MiB. La retención es estable y compatible con la caché meteorológica; no
se observa crecimiento acumulativo en esta ventana. El Ensayo B pasa en memoria,
temperatura y ausencia de OOM.

Los 8,667 s no representan la experiencia completa del usuario. La diferencia
respecto a los al menos 30 s observados queda pendiente de desglosar con un
monitor extremo a extremo de la petición y fases internas de renderizado. No se
debe presentar la subfase meteorológica como tiempo total de apertura.

## Resultado real — Ensayo C en RPi4 (`0.2.228`)

Durante el siguiente runner programado, el usuario intentó abrir el Predictor y
la aplicación mostró correctamente el aviso de que no estaba disponible porque
había un runner activo. Esto valida en HA real la puerta funcional de
`action_is_running()` y evita iniciar una predicción concurrente.

El paquete se exportó el 2026-08-08 a las 00:04:22 UTC, después de la recuperación
de 600 s:

- evidencia: `rainmapper-diagnostics-20260808T000422Z.zip`, SHA-256
  `49a396ae5c9585c4f0b20a01d73a8e22d856ca4e7c5b9a7ed2a38dfb83bd2278`;
- `predictor_cache_released` registró 4 instancias liberadas, sin error, 725 ms
  antes de que arrancara el proceso hijo `runner_update`;
- el runner programado `all` terminó con exit code 0 en 403,4 s (6 min 43 s):
  `update` 322,7 s y `maps` 56,9 s;
- pico RSS histórico del hijo: 1.300,7 MiB; máximo RSS actual agregado:
  1.283,2 MiB;
- máximo actual del cgroup: 1.432,6 MiB y pico del cgroup: 1.477,2 MiB;
- mínimo `MemAvailable`: 780,2 MiB; temperatura máxima: 50,15 °C;
- Parquet: 626.809 filas, 1.225 row groups y 12,004 MiB; catálogo: 79,304 KiB;
- Meteocat agotó el primer intento de condiciones por timeout, reintentó y
  completó correctamente; el resto del flujo funcional terminó sin fallos;
- `oom=0` y `oom_kill=0` en todos los eventos.

La liberación de referencias fue anterior al hijo, pero la memoria física del
servidor no volvió al sistema de inmediato: justo antes del runner seguía en
333,7 MiB RSS y el cgroup en 421,1 MiB. Esto elevó el pico del cgroup unos
129,4 MiB respecto al Ensayo A. Aun así, el margen real fue suficiente y no hubo
OOM. Al terminar `update`, el RSS del servidor había bajado a 168,6 MiB. En
`recovery_600s` quedó en 169,1 MiB, el cgroup en 456,2 MiB y `MemAvailable` en
1.825,8 MiB, solo unos 32 MiB por debajo del estado previo a abrir el Predictor.

Conclusión del Ensayo C: pasan tanto el bloqueo visible como la exclusión y
recuperación de recursos. El P0 de memoria se cierra para la RPi4 y el uso
monousuario ensayado, con runner cada tres horas y sin concurrencia deliberada.
La apertura extremo a extremo de al menos 30 s queda como problema de rendimiento
separado; la caja negra persistente queda como mejora de observabilidad.

Después de los ensayos, el usuario confirmó el 2026-08-08 que también había
completado la reconstrucción de features, el entrenamiento con el worker
actualizado y la promoción de los modelos junto con `ml_train_report.json`. Por
tanto, no queda una migración de artefactos ML pendiente para cerrar esta serie.

## Criterio de cierre

Los paquetes reales A–C confirman que:

- runner y Predictor terminan sin OOM, reinicio ni pérdida de conectividad;
- el runner finaliza con margen amplio respecto al intervalo de tres horas;
- la memoria vuelve cerca del estado base después del runner;
- las consultas repetidas no generan crecimiento acumulativo;
- temperatura y alimentación permanecen estables;
- el Parquet regenerado usa row groups filtrables.

El P0 queda cerrado dentro del alcance probado. No constituye una prueba de
carga multiusuario ni garantiza por sí solo el comportamiento tras futuros
cambios; el histórico persistente permitirá vigilar su evolución.

## Validación local

El 2026-08-08 pasó `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh` completo
para `0.2.228`: 469 tests, compilación Python, parseo JavaScript, fixtures
operativas y comprobación de whitespace. Esto valida los contratos y la
integración local; no sustituye los ensayos A–C sobre la RPi4.
