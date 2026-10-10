# Selección A/B/C/D: implementación local · 05/10/2026

Implementación disponible en HA local; primera actualización real fallida y
corrección aplicada localmente (detalle al final). Pendiente de completar una
actualización real, que solicita automáticamente el runner vía precálculo. No se ha publicado una versión
HA ni activado evidencia histórica real. Los estudios cerrados y las fuentes
privadas se conservan.

## Comportamiento

- `Competing selection` y `K value`, heredados del add-on salvo preferencia del
  dispositivo. Defaults efectivos comprobados: `false` y `4.0`.
- A: 12 meses móviles, B/C: 24 meses móviles, D: todo el histórico anterior a la
  consulta, incluido el año actual. A/B/D selección semanal; C diaria.
- Mayor Iₖ entre candidatos elegibles, con las guardas de temporada, aplicabilidad
  y recomendación existentes. La predicción habitual permanece como referencia.
- Comparación plegada inicialmente, con coincidencia y número de modelos
  distintos. Ausencias sin votos. Navegador comprobado a 320 y 390 píxeles.
- Sección «Selección histórica A/B/C/D» en Workers y trabajos, acción
  «Comprobar y actualizar». Trabajo independiente en el worker, cancelable,
  con estado, duración y resultado anterior conservado ante fallo.
- El runner, al solicitar el precálculo, pide también la comprobación histórica
  asíncrona, incluida la primera preparación. No depende de Competing selection
  ni requiere usar antes el botón manual.
  Entradas sin cambios no encolan otra evaluación. K no invalida la caché.

## Datos y recursos

Matrices nuevas en Parquet, caché de unidades de validación en SQLite y control /
resultado compacto en JSON. Los builders existentes conservan JSON por defecto.
Parquet conserva valores sin redondear, nulos y claves ausentes, y permite leer
las columnas necesarias. No se ha medido una mejora de tiempo global por formato.

Se comprueban observaciones, familias instaladas, contratos, código y datos
históricos utilizados. La lluvia posterior a los casos no invalida su revisión.
El resultado se comprueba de nuevo contra las entradas actuales antes de
publicarlo; reintentos entre publicación y cierre de cola son idempotentes.
Límite de transporte de evidencia: 1 MiB. Caché de inferencia por punto: 2 MiB.
La descarga histórica verifica archivos y manifiesto sin sincronizar GIS.

Las validaciones aisladas entrenan exclusivamente con años anteriores al año
evaluado; no usan los pesos instalados para «acertar» observaciones ya aprendidas.
Separación de episodios alrededor del cambio de año. El ajuste interno V6 limita
también su preprocesado al entrenamiento interno, distinto del antiguo estudio.
La caché nueva conserva unidades compatibles con este protocolo. **No se ha
importado el estudio cerrado a esta caché ni se afirma que sus ajustes sean
intercambiables.** Las ausencias por falta de soporte, perfil o frontera temporal
quedan en un informe privado del worker; el mapa recibe sólo recuentos.

## Verificación realizada

- Pruebas dirigidas de ventanas, ranking, K, comparación diaria/semanal,
  aislamiento temporal, caché y correcciones, límites de tamaño y datos inválidos.
- Integración sintética de cola, claim, recepción, rechazo de obsoletos,
  cancelación y reintento de publicación. Sin trabajos reales.
- Pruebas del transporte, empaquetado, builders y preferencias/dispositivo.
- 160 pruebas dirigidas en el conjunto inicial: 157 pasaron en sandbox; las tres
  que necesitaban abrir un puerto localhost pasaron al ejecutarlas con permiso.
  Cambios posteriores de transporte y auditoría cubiertos por pruebas dirigidas.
- Navegador `tests/prediction_map_browser_check.mjs`: pasó con los assets locales
  MapLibre, incluidas las comprobaciones nuevas de comparación y móvil.
  Capturas en `/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-q1ky9L`.
- 11 pruebas sintéticas adicionales dentro de la imagen reconstruida del worker:
  lectura Parquet, ajuste temporal mínimo, entrega acotada y reutilización SQLite.
- `git diff --check`: sin errores.

Comprobación de entradas reales, **sólo lectura**, con memo temporal aislada:
87 familias instaladas, 311 candidatos/horizontes y especificación de 73.087 bytes.
Primera comprobación en el Mac: 15,078 s; repetida con memo: 0,309 s.
Estos tiempos **no son** duración de la evaluación histórica ni una estimación
para la Raspberry Pi. No se generaron matrices ni se ajustaron modelos reales.

## HA local y worker — comprobación inicial

Reconstruidos y recreados ambos componentes. HA local responde HTTP 200.
Paridad comprobada de 27 archivos en HA y 20 en worker, sin diferencias:
`tmp/competing-selection-local-20261005/parity.json`.
Huella del procedimiento idéntica en repositorio y ambos contenedores:
`f53f2b5ee3e312d77138a19d690a5a9e4dde29b9a8af3b1661f7ec4aef27e28c`.

Se conservaron las huellas de `config/coordinator.json` y
`config/additional-coordinators.json`, y los destinos previos del worker:
principal `http://100.111.77.48:8100`, adicional local
`http://rainmapper-ha-ui:8100`. No se modificó su configuración.
Health local del worker: idle en ambas colas, capacidad histórica anunciada.
La revisión del registro HA desde otro proceso sólo acredita la capacidad
persistida; su memoria de heartbeats no sirve para comprobar conectividad viva.

## Pendiente de aceptación

El estado inicial era `not_prepared`; el primer intento posterior del usuario
falló (detalle a continuación). El próximo runner
que solicite precálculo puede iniciar una nueva actualización en HA local;
«Comprobar y actualizar» permite adelantarla opcionalmente. Hay que revisar duración, cobertura y
ausencias, artefacto recibido, activación y primera comparación real A/B/C/D.
Después, comprobar actualización incremental con una modificación autorizada.
No dar por validado ese recorrido antes de ejecutarlo. No hay autorización de
publicación ni de instalación en HA real.

Corrección posterior del 05/10: eliminada la condición que exigía estado previo
o default activado. La prueba integrada recorre la solicitud post-runner con
Competing selection=false y sin fichero de estado; encola la primera evaluación
y evita duplicarla en la siguiente solicitud. La comprobación no lanza trabajos
reales: transporte, entradas y cola están aislados. Sólo afecta al coordinador
y al texto de ayuda; no requiere reconstruir ni reiniciar el worker.
Corrección aplicada mediante reconstrucción/recreación de HA local: 11 pruebas
dirigidas pasaron, paridad de archivos comprobada de nuevo y HTTP local 200.

## Primer fallo real y corrección del 05/10

Trabajo `worker_job_ovu2GjZR5iwh8B9u`, reclamado por el worker local para HA local:
terminó fallido después de 233,303614 s, con progreso 15 %. El log identifica
`build-biology-v4-benchmark.py` → `mushroom_ml_benchmark_io.write` →
`ValueError: benchmark_metadata_limit`. No llegó a la evaluación de modelos:
falló preparando entradas V4. Registro conservado antes de recrear el worker:
`tmp/competing-selection-local-20261005/failed-history-job.json`.

La implementación trataba todo lo que no fuera `samples` como metadatos. V4
incluye `soil_variants.*.area_state_catalog`, un catálogo de datos compartidos
que excedía el límite del footer. Se corrige el diseño sin ampliar ese límite:

- Estados de suelo en filas del mismo Parquet, identificadas por variante y
  área/fecha; no se duplican por observación ni se reparten en archivos auxiliares.
- Footer conserva descriptores y recuentos; `metadata()` no carga el catálogo.
  `read()` lo restaura íntegro para los consumidores V4 y V3+.
- Límites separados de muestras/estados, registro, bytes sin comprimir y archivo;
  escritura por lotes con sustitución atómica del destino.
- Progreso del builder reenviado con microáreas/estados completados; fases
  diferenciadas V3/V4/V5, fixed/lag. Porcentajes de fase orientativos, no ETA.
- El error comienza por la excepción final y conserva el detalle acotado,
  evitando perder la causa cuando HA limita el texto visible.

Validación proporcional de la corrección:

- 55 pruebas iniciales (IO, runner, histórico y servicio worker), todas correctas.
- 20 pruebas tras ajustar límites (IO, runner, backend, entradas y empaquetado),
  todas correctas; dos del runner repetidas tras ajustar el texto de fase.
- 14 pruebas en la imagen final del worker, sin red y con datos sintéticos:
  incluye catálogo mayor de 2 MiB, recuperación exacta, mismo resultado de ambos
  consumidores, contadores, integración temporal y caché SQLite.
- HA local y worker reconstruidos y recreados desde el mismo código. Paridad
  de 27/20 archivos sin discrepancias; HTTP local 200 y ambas colas idle.
  Revisión de procedimiento idéntica en repositorio y ambos contenedores:
  `92ae3c28e7ff447a28aba422fc3ae89daa741ec5b5d10ee9da43a3dd680ca646`.
- Huellas de los dos ficheros de coordinadores exactamente iguales antes/después;
  destinos principal `http://100.111.77.48:8100` y local
  `http://rainmapper-ha-ui:8100` conservados.

No se relanzó el trabajo real ni se modificaron fuentes, modelos instalados o
el registro del fallo. Pendiente de comprobar el recorrido real completo en
la siguiente solicitud automática o manual. Sin release, commit ni push.

## Segundo fallo (V5), detalle del trabajo y comprobación V6

El siguiente trabajo del usuario, `worker_job_t5oFnnauV-ViJ346`, llegó a 34 % y
falló en V5: `history-inputs/MANIFEST.json` no existía. El preparador histórico
había omitido el manifiesto que sí crea el preparador operativo. Duración del
hilo: 269,235690 s. Registro conservado antes de recrear el worker:
`tmp/competing-selection-local-20261005/failed-history-v5-job.json`.

Corrección: el runner genera el manifiesto con revisión, snapshot de origen,
tamaños y huellas de los archivos V3/V4 efectivamente escritos. V5 comprueba
su existencia antes del cálculo y registra su ruta real, en vez de una ruta de
estudio fijada en el código. No se inventa ni omite la procedencia.

El detalle del trabajo también faltaba: lista y endpoint sólo admitían los tipos
anteriores. Ahora la selección histórica abre el mismo modal, con fase completa,
mensaje/contadores, porcentaje, duración y error. No se deduce una ETA de los
pesos orientativos de fase. El nombre mostrado distingue el worker de HA local.
El modal limita su altura al viewport y permite desplazar y partir texto largo.

Ampliación expresa del usuario: revisar también V6. Se comprobó en
`mushroom_ml_runtime_trainer.materialize_runtime_benchmarks` que V6 consume las
matrices V5; no necesita un manifiesto de otro directorio. Prueba nueva:

- Activa el workspace y ejecuta los tres preparadores reales V3/V4/V5 con
  fuentes meteorológicas y observaciones sintéticas, sin sustituir los builders.
  La planificación incluye V6 y activa correctamente su dependencia V5.
- Verifica archivos Parquet y procedencia generada; materializa perfiles.
- Recorre 24 combinaciones V6: fixed/lag × 365/30/60/90 días × estimadores
  por especie, compartido y partial pooling. Lee las columnas necesarias del
  Parquet producido y ajusta/evalúa casos sintéticos de años separados, con
  particiones internas disponibles, probabilidades finitas y reutilización SQLite.

Resultados: 27 pruebas dirigidas correctas; tras ampliar V6, prueba de cadena
completa correcta y 15 pruebas en la imagen final del worker, sin red ni datos
reales. Reconstruidos HA local y worker; paridad de 27/20 archivos y huella común
`51a67df196896d00af68e7fa522902e84c255cb82ade6cd6acda622d7eca3e0a`.
Los destinos y huellas de ambos coordinadores se conservaron exactamente.

Navegador sobre HA local final: clic al trabajo fallido, error y 34 % visibles,
cuadro dentro de la pantalla y sin desbordamiento horizontal a 1280 y 375 px;
cierre correcto y botón de cancelación oculto en un trabajo terminal.
También se verificó refresco de porcentaje y contadores con respuestas simuladas
exclusivamente en el navegador, sin modificar trabajos ni enviar POST.
Recibo/capturas: `tmp/competing-selection-local-20261005/job-detail-browser.json`
y `history-detail-{1280,375}.png`. Comprobador `check-job-detail.mjs`.
Paridad final repetida tras los ajustes de presentación; `git diff --check` limpio.

Las pruebas sintéticas no acreditan una evaluación completa de las observaciones
reales. No se relanzó ningún trabajo, no se reabrió el estudio cerrado ni se
publicó una release. Pendiente de la siguiente solicitud del usuario o runner.

## Tercer fallo (39 %): especie nueva en la validación interna V6

El trabajo `worker_job_zRl8ApHGn_5u68k2` falló después de 277,476881 s con
`ValueError: unknown hold-out species: boletus_edulis`. Log conservado antes
de recrear: `tmp/competing-selection-local-20261005/failed-history-v6-job.json`.
La traza llega a `historical_v6_config` y `pooled_design`: el entrenamiento de
una partición interna no contenía edulis, pero su validación posterior sí.
Las pruebas anteriores de 24 combinaciones no incluían esa aparición tardía;
por ello no acreditaban este caso. La nueva variante reprodujo el mismo error
antes de corregir el código.

Corrección en `rainmapper_core/mushroom_competing_tuning.py`: cada comparación
interna puntúa sólo especies presentes en su entrenamiento anterior. Si ninguna
de las especies de validación tiene soporte, no ajusta esa partición; si no queda
ninguna comparación utilizable, mantiene la configuración por defecto y lo
registra. No se introduce una especie futura en la codificación de entrenamiento
ni se suaviza el contrato de `pooled_design`. El ajuste exterior conserva todas
sus filas anteriores; edulis puede evaluarse en períodos posteriores con soporte.

`fit_temporal_unit` guarda en SQLite `tuning_diagnostics`: particiones totales y
utilizadas, uso de defaults y ocurrencias de validación sin soporte por especie.
Son ocurrencias entre particiones, no observaciones únicas. No se añaden filas
diagnósticas al contrato del mapa ni se eliminan observaciones fuente.

Pruebas de esta corrección:

- Cadena real de preparadores V3/V4/V5 y 24 combinaciones V6 con edulis tardío:
  una partición mixta, otra sin especies conocidas, predicción posterior de las
  tres especies para modelos compartidos y reutilización de diagnósticos SQLite.
- Pruebas dirigidas de selección interna: validación totalmente desconocida no
  ejecuta preprocesado ni ajuste; cambiar valores/etiquetas de casos sin soporte
  no altera la elección ni introduce esos casos en el preprocesado interno.
  Utilizan identificadores sintéticos independientes de aereus/caesarea.
- Caché con deliciosus: añadir un caso conserva familias independientes de
  aereus y períodos anteriores. Corregir una entrada antigua invalida las unidades
  de deliciosus y compartidas que la consumían; no las independientes de aereus.
- 29 pruebas dirigidas correctas en el Mac. 18 correctas dentro de la imagen
  reconstruida del worker, sin red ni fuentes reales.

Comandos de comprobación:

```sh
.venv/bin/python -m unittest tests.test_mushroom_competing_tuning tests.test_mushroom_competing_history tests.test_mushroom_competing_runner tests.test_mushroom_map_competing tests.test_mushroom_ml_benchmark_io
docker run --rm --network none --user 10001:10001 --entrypoint python -v /Users/carlosginebrosa/Developer/RainmapperHA/tests:/app/tests:ro rainmapper-worker:1.1.6 -m unittest tests.test_mushroom_competing_tuning tests.test_mushroom_competing_history tests.test_mushroom_competing_runner tests.test_mushroom_ml_benchmark_io
```

El usuario pide preparar una futura extensión a todas las especies y evitar
recálculos ajenos a la especie cambiada. Se documenta en la especificación central
la dependencia de modelos compartidos y la optimización pendiente por observación,
ajuste y predicción. La caché existente ya conserva unidades idénticas, pero la
preparación de variables y las unidades compartidas aún tienen alcance mayor.
No presentar esta corrección como una optimización incremental completa.

Activación local comprobada: HA y worker reconstruidos/recreados desde el mismo
código; HTTP local 200 y worker idle en ambos carriles. Paridad de 27 archivos HA
y 20 worker, sin diferencias (`tmp/competing-selection-local-20261005/parity.json`).
Procedimiento común repositorio/HA/worker:
`4fe21f2ade57df222a6916a7d96a2bd4d2f32b84f74d3ebfad6991a3bb90d721`.
Huellas de configuración de coordinadores idénticas antes/después:

- Principal: `5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10`.
- Adicional: `22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0`.

No se relanzó la evaluación real, entrenamiento operativo ni precálculo. No hay
cambios de UI en esta corrección; no se repitió navegador. Sigue pendiente que
el usuario complete el recorrido real, recepción y activación. El cambio de
procedimiento invalida las unidades con la huella antigua de forma conservadora;
no confundir esta migración de código con una actualización sólo de observaciones.
