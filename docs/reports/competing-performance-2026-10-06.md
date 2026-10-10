# Optimización de selección y comparación — en curso, 06/10/2026

Objetivo solicitado: selección y comparación completas en un máximo de diez
minutos con 5.000 observaciones, optimizando antes de aumentar recursos o usar
paralelismo. El 07/10 el usuario autoriza trabajo autónomo y después pruebas con
hasta cuatro núcleos y 8 GB, sin acciones destructivas. No se han aumentado los
recursos de ningún servicio. Para el volumen actual se busca preparación/selección
por debajo de un minuto. **El objetivo de 5.000 no está acreditado; el actual <1 minuto sólo se ha medido con evidencia reutilizada.**
También se pidió revisar la latencia de mantenimiento de observaciones y medir
los accesos JSON antes de decidir una migración. Las primeras mediciones locales
se detallan abajo; no se ha medido ni cambiado HA real.

## Evidencia inicial

El trabajo `worker_job_LPITwr69epXpspmS` terminó su cálculo en 1.494,729 s:
aproximadamente 17 min 33 s hasta guardar la generación y 7 min 22 s adicionales
para la comparación. El anterior de 7 min 45 s sólo preparó selección: su
artefacto no contenía comparaciones, aunque la UI ahora muestre el título nuevo.
Fuentes: estado local persistido, metadatos de `comparison.sqlite` del worker y
los snapshots conservados de ambos trabajos. No se repitieron sus entrenamientos.

Los 509.564 del contador significaban **accesos a variables reutilizadas**, no
variables distintas: se contaron 56.699 muestras creadas y 509.564 reutilizaciones.
Había 184 visitas objetivo, 169 con celdas de evidencia, 275 variantes candidatas
y 25.923 celdas. V6 compartido usa además observaciones de otras especies para
sus ajustes históricos; no equivale a 184 filas numéricas en todo el proceso.

La recepción del trabajo no activó su resultado: el snapshot tenía 549
observaciones y el archivo local pasó a 550. Se verificó un alta de
`lactarius_deliciosus` y una modificación de abundancia/altitud de otra observación
de esa especie, con setales sin cambios. No atribuir esa invalidación al vídeo.

## Cambios del worktree, todavía sin desplegar

- Auditoría nativa compartida por conjunto de evidencia previa; no por cada
  fecha/horizonte que consume exactamente el mismo conjunto. Sólo se calcula
  el alcance de especie necesario para este replay.
- Estadísticas y clasificaciones compartidas; B/C reutilizan el ranking, pero
  conservan sus resoluciones semanal/diaria. Plan semanal reutilizable, evidencia
  escalar inmutable y menos copias de diagnósticos no consumidos por el replay.
- Huellas meteorológicas/de variables compartidas entre estimadores del mismo
  perfil. Preparación de matriz de ajuste y codificación de tensores compartidas
  entre consumidores de las mismas filas. Las claves conservan los datos exactos.
- Materialización meteorológica por series, con reducción en el mismo orden de
  estaciones que el IDW escalar. Caché de conversiones limitada a 16 MiB. Sigue
  disponible la implementación escalar como referencia. Activación sólo en la
  preparación histórica, no cambio de la fórmula meteorológica del mapa.
- Eliminación del barrido completo de duplicados al corregir el primer día de
  una ventana: ese día no tiene predecesor dentro de ella. Ventanas temporales
  acotadas sin conservar una copia completa por cada constructor/microárea.
- V5 lee V3 y escribe matrices Parquet por lotes. Los originales siguen JSON.
  Codificación rápida sólo tras demostrar un límite superior de tamaño; fallback
  incremental en los demás casos. Matrices históricas V4/V5 pueden omitir las
  series diagnósticas ya consumidas, conservando X, etiquetas, calidad e identidad.
  Los exports científicos completos mantienen su comportamiento por defecto.
- Proyección de V5/V6 a las columnas realmente consumidas por los modelos
  instalados: 459/460 predictores, frente a 2.929/2.930. No se cambia su lookback
  físico ni se recorta la meteorología necesaria para producir esas columnas.
- Huellas de semanas persistidas con comprobación de los registros meteorológicos
  exactos y del productor. Reserva pequeña dentro del presupuesto SQLite ya
  existente; permiten reutilizar unidades aunque se hayan expulsado variables
  numéricas reconstruibles. Sin borrar resultados ni fuentes.
- Lectura privada V5/V6 mediante vistas de bloques numéricos inmutables; se
  conservan precisión float64, nulos y claves ausentes. La normalización de filas
  y construcción de matrices no vuelven a expandir todos los números a dicts.
- Lotes Parquet dimensionados por número de celdas, evitando repetir cientos
  de veces los metadatos de cada columna. V4 privado consume V3 por lotes.
  La selección descarta series ya consumidas; las proyecciones intermedias
  conservan su calidad requerida y el ajuste final sólo recibe su contrato.
- V3 genera filas por lotes y sus ventanas de área se calculan bajo demanda,
  con retención acotada. El pie Parquet actualiza los contadores finales y el
  esquema Arrow incrustado tras consumir el generador.
- Lectura meteorológica histórica desde lotes Arrow directamente a registros;
  evita acumular una tabla completa y sus copias Pandas. Conserva duplicados,
  metadatos iniciales de estación y valores ausentes como el lector anterior.
- V5 privado conserva una proyección numérica por área/fecha y los contadores
  de calidad; no retiene todas las ventanas diarias solapadas. Esa proyección
  se comparte entre fechas objetivo y horizontes sin repetir su construcción.

## Mediciones aisladas

Contenedores sin red, un núcleo y límite de RAM de 1 GiB; las primeras medidas
permitían el swap predeterminado de Docker. Las medidas indicadas expresamente
sin swap usan también `--memory-swap 1g`. Es un presupuesto del diagnóstico,
no una afirmación sobre límites asignados al worker existente. Fuentes/volumen
worker montados de sólo lectura. Salidas privadas en
`tmp/competing-speed-20261006/`. Ningún trabajo
operativo, entrenamiento o precálculo lanzado; las llamadas de ajuste están
bloqueadas explícitamente en los diagnósticos.

- Replay completo de 184 visitas usando probabilidades ya guardadas:
  **20,047 s sin profiler** (`fast-all-wall.json`). Auditorías nativas 63 creadas /
  1.176 reutilizadas; rankings 343 creados / 4.613 reutilizados.
- Comprobación completa contra el replay original: **408,847 → 20,047 s**,
  las 184 visitas con resultados exactamente iguales, incluidos Habitual,
  A/B/C/D, ausencias, métricas y ganadores. Recibo `full-replay-parity.json`.
  Sustituye la comprobación inicial limitada a dos casos.
- Dos diagnósticos de preparación llegaron al límite de 1 GiB antes de terminar
  V5. Docker registró `oom` para el primero; salida 137 en ambos. Sirvieron para
  localizar acumulación de filas y ventanas. No se elevaron recursos.
- Primera preparación completa tras lectura/escritura por lotes:
  **134,479 s sin profiler**, excluye ajustes y comparación
  (`prepare-streamed-result.json`). Conservaba aún las copias de ventanas y
  metadatos que se están retirando. Es una medición intermedia, no el resultado
  final ni una prueba de 5.000 observaciones.
- Preparación posterior: **63,491 s** (`prepare-slots-result.json`), sin ajustes
  ni comparación. Sus seis matrices coinciden con la referencia en valores,
  calidad y catálogos, salvo las columnas no consumidas y los diagnósticos
  explícitamente omitidos (`prepared-parity.json`). Es anterior al último cambio
  de tamaño de lote y lectura V4; la medición de esa revisión queda pendiente.
- La primera compactación provocó una regresión de V3 físico: faltaban 1.128
  asociaciones visita/familia. **Las mediciones `selection-sealed` y
  `selection-restored` no representan una selección completa y se descartan.**
  Se corrigió reutilizando las variables climáticas ya calculadas en V4 y
  aplicando su variante de suelo, manteniendo el cálculo habitual en inferencia.
- Tras corregirlo, la selección leyó **990 unidades anuales existentes**:
  94,279 s con huellas nuevas de V3 físico y **25,652 s** reutilizando todas las
  huellas. Con columnas compactas y contrato de ajuste: **25,713 s**.
  Excluyen preparación y comparación; no son tiempos desde cero.
  `selection-parity.json` acredita igualdad exacta de las 8.308 asociaciones
  visita/familia y sus claves, las 184 visitas y las 25.923 celdas de evidencia
  respecto a la generación original. Las últimas lecturas V3 por lotes/proyección
  todavía requieren repetir la comprobación correspondiente.
- Prueba sintética **sólo de E/S**, 35.000 filas (5.000 × 7), 460 columnas,
  metadatos basados en las filas reales, sin meteorología, ajustes ni replay:
  escritura 32,659 → **10,565 s**, archivo 144.478.328 → **34.422.820 bytes**;
  lectura y elegibilidad 4,771 → **3,193 s**; pico RSS 936,4 → **454,4 MiB**.
  Recibos `compact-scale.json` y `compact-scale-compact-groups-fit.json`.
  Se redujeron grupos Parquet y diagnósticos retenidos; números y elegibilidad
  se conservan. **No acredita el objetivo de diez minutos del proceso completo.**
- Primera medición conjunta (`integrated-bounded`): 108,500 s, con preparación
  de variables nueva y unidades de validación reutilizadas. Permitía swap;
  no acredita ejecución sin swap. Repetirla con swap deshabilitado reveló un
  pico en la carga meteorológica y después otro al acumular ventanas V5.
  Ambos terminaron por OOM, confirmado por eventos Docker, sin elevar recursos.
- Tras corregir esos dos puntos (`integrated-window-projection`), recorrido
  conjunto **102,375 s**, **sin swap**: preparación 62,689 s; hasta terminar
  selección 81,150 s; comparación 21,225 s. Leyó 990 unidades anuales ya
  existentes, sin ajustes ni inferencias nuevas. Cgroup: límite 1.073.741.824,
  pico 1.020.403.712 bytes, `memory.swap.peak=0`; RSS máximo 986,6 MiB.
  Igualdad exacta con la generación original: 184 visitas, 8.308 asociaciones
  visita/familia y sus claves, 25.923 celdas. Comparación completa idéntica al
  replay original. Sus seis matrices conservan valores, calidad y catálogos.
  Recibos `result.json`, `selection-parity.json`, `comparison-parity.json` y
  `history-inputs/prepared-parity.json` en esa carpeta. Todavía no consigue
  preparación más selección <1 minuto ni demuestra el objetivo de 5.000.
- Pruebas dirigidas aprobadas: igualdad exacta IDW multicanal, estaciones ausentes,
  lluvia duplicada en el límite y ET₀; cache/fit/tensor; roundtrip y límites de
  Parquet; replay y preparación de planes. La validación integrada y la paridad
  local de imágenes siguen pendientes de la revisión final.

### Continuación 07/10: distinguir caché y preparación de un productor nuevo

- `integrated-range-views`: 84,414 s, preparación 46,379 s, hasta selección
  64,125 s, comparación 20,289 s. Vistas de registros por fecha sin copiar cada
  diccionario de estación. Las seis matrices, generación y comparación coinciden.
- `integrated-column-check`: 86,099 s, preparación 47,885 s, hasta selección
  64,636 s, comparación 21,463 s; un núcleo/1 GiB/sin swap. Se memoiza la
  comprobación de columnas presentes en los bloques numéricos. Generación y
  comparación idénticas. Pico cgroup 995.414.016 bytes.
- Esas medidas reutilizaban huellas privadas del productor del diagnóstico.
  Con identidad nueva y caché privada vacía (`integrated-new-procedure`), el
  recorrido tardó **401,726 s**: preparación 47,936 s, hasta selección 380,352 s,
  comparación 21,374 s. Los 990 resultados de validación se reutilizaron, pero
  hubo que reconstruir las huellas de entradas semanales. Igualdad exacta de
  evidencia, visitas, 8.308 claves visita/familia y comparación. Productor
  `e259e5b0c98a4357d5a78704ed83d2f7c3fb9ea8988aa39f12602d224e10b9de`.
  No es una medición con nuevos ajustes de modelos. Recibos `result.json`,
  `selection-parity.json` y `comparison-parity.json` en esa carpeta.
- La reutilización inicial del suelo por área/fecha fue rechazada por la prueba
  de claves exactas (`integrated-shared-inputs`, 82,046 s, 194 unidades leídas).
  **Ejecución fallida, no cifra de rendimiento válida.** La versión siguiente
  exige igualdad de las series concretas de lluvia y ET₀ antes de reutilizar
  suelo; su validación real posterior se detalla a continuación.
- Auditoría de tamaño, sin materializar variables ni ajustar: 5.000 visitas
  repartidas entre las dos especies y las referencias actuales planifican
  **8.405.000 celdas semanales**; el contrato actual las rechaza por presupuesto.
  `scale-preflight-5000.json`. La meta exige cambiar la materialización y el
  contrato compacto; no basta con extrapolar tiempos ni aumentar límites.
- Paquetes reales privados: 8.308 paquetes, 284.620 celdas, 28.401.806 bytes de
  JSON; una prueba de compresión zlib nivel 1 los reduce a 3.635.510 bytes.
  `panel-storage.json`. Sólo mide payloads: excluye índices SQLite, generación
  y modelos. No se ha migrado ni comprimido el almacén original.
- `docker info` y `docker inspect rainmapper-worker` leídos el 07/10: Docker
  dispone de diez CPU y 11.209.805.824 bytes; el worker no tiene límites propios
  (`NanoCpus=0`, `Memory=0`, `MemorySwap=0`). Por tanto, 1 CPU/1 GiB describe
  los contenedores aislados de diagnóstico, no los recursos del trabajo original.

### Comprobaciones posteriores: entradas, calendarios y alcance

- Reutilización de suelo con firma exacta de lluvia/ET₀:
  `integrated-soil-input-guard`, **381,724 s**, preparación 47,452 s,
  hasta selección 361,276 s, comparación 20,448 s. Paridad completa aprobada.
- Ventanas V5/V6 preparadas una vez para sus horizontes; muestras privadas
  conservan X/calidad y omiten diagnósticos diarios repetidos. Vistas de
  estaciones acotadas a 16 ventanas. `integrated-runtime-windows`:
  **301,315 s**, preparación 47,112 s, hasta selección 280,382 s,
  comparación 20,933 s. Paridad completa aprobada.
- V3 reutiliza el índice de fechas de ventanas normales (máximo 16 ejes de
  366 días). Los valores se leen frescos y los ejes irregulares conservan
  el validador original. `integrated-calendar-cache`: **241,069 s**,
  preparación 41,203 s, hasta selección 220,866 s, comparación 20,203 s.
  Pico cgroup 1.023.569.920 bytes, sin swap. Productor
  `f96ef5c539ebf1c58910bedab7cfa49715aa55ac03aba3c16c9ef399ce42f39d`.
  Paridad exacta de generación, comparación y las seis matrices: se conservan
  variables consumidas, calidad, catálogos y claves.
- Mismo código con sus huellas guardadas: `integrated-calendar-warm`,
  **82,701 s**, preparación 40,708 s, hasta selección 62,785 s,
  comparación 19,916 s. Pico cgroup 1.004.679.168 bytes, sin swap. Generación
  y comparación idénticas; todavía no llega a preparación/selección <1 minuto.
- Todos esos recorridos reutilizan 990 unidades; ajustes/inferencia están
  bloqueados. **La generación original persistida registra 941 unidades
  calculadas y 49 reutilizadas.** Por tanto, no acreditan una aceleración
  equivalente del ajuste inicial ni el recorrido completo de 5.000 casos.
- `panel-usage.json`: replay real de 20,782 s y resultado idéntico;
  83.549 solicitudes, 1.320 paquetes y 21.381 celdas distintas consumidas,
  frente a 8.308 paquetes y 284.620 celdas almacenadas. Sólo 7,5 % de las
  celdas se utilizó para K=4. Una futura preparación bajo demanda debe
  conservar ajustes para no repetirlos; todavía no está implementada.
- Metadatos de los 87 modelos instalados seleccionados: 16.022.874 bytes en
  total, máximo individual 719.314 bytes (`installed-selected-model-sizes.json`).
  No se cargaron sus pesos. **No son tamaños de ajustes históricos ni medidas
  de memoria de inferencia**; no extrapolarlos como presupuesto suficiente.
- 43 pruebas dirigidas aprobadas tras ventanas/calendarios, luego 50 de
  `test_mushroom_competing*.py` (10,987 s). La reducción adicional por área pasó 21 pruebas y mantuvo paridad completa
  (`integrated-area-summaries`: 241,457 s, preparación 45,496 s, hasta selección
  221,156 s, comparación 20,301 s), pero **no mejoró el tiempo total** y subió
  memoria. Se retiró exclusivamente ese experimento; sus recibos se conservan.

### Cambios siguientes: ajustes y huellas compartidas

- Nueva caché privada de **ajustes históricos completos**, separada de las
  filas evaluadas. La identidad incluye las entradas/etiquetas/episodios del
  entrenamiento y el productor. Añadir o corregir un caso del año evaluado
  reutiliza el ajuste si su pasado no cambia. Corregir el entrenamiento lo
  invalida; las dependencias compartidas V6 siguen entrando en la identidad.
  Misma base SQLite de 256 MiB, memo de hasta 64 MiB, sin borrar resultados.
  Si no cabe una entrada, el proceso continúa sin memoizarla. No contiene ni
  carga pesos instalados: sólo los ajustes históricos generados por el worker.
- Pruebas sintéticas: misma predicción que el ajuste directo, reapertura de
  caché, cambio de etiquetas/valores/especies/episodios, corrupción y límite.
  V6 compartido/parcial conserva probabilidades, configuración y diagnóstico,
  con un ajuste y una selección interna en vez de repetirlos al añadir tests.
- V6 construye una matriz por escala y la comparte entre los tres valores de C;
  mantiene los nueve/tres candidatos y las reglas de desempate. Conserva una
  sola escala en memoria; no acumula matrices para ganar tiempo.
- Sellado de tensores por lote: una conversión a JSON por fila abastece las
  huellas de todos los estimadores y productores compatibles de esa matriz.
  Las claves SHA-256 son exactamente las anteriores; no se conserva una copia
  serializada de la matriz completa. Pruebas de equivalencia aprobadas.
- Identidad del productor de variables separada de ranking, replay y memo de
  ajustes. Los constructores numéricos, módulos ML, física y adaptadores siguen
  sellados; cambiar el comparador por sí solo ya no invalida meteorología/X.
- Diagnóstico real del conjunto iniciado: `integrated-batched-keys`, un núcleo,
  1 GiB, sin swap, ajuste/inferencia bloqueados y originales de sólo lectura.
  Pendiente completar/paridad y medir la repetición con las nuevas huellas.
- Preparado un diagnóstico de 5.000 filas sintéticas de observaciones. Sólo
  preparación, sin selección, ajuste ni comparación; pendiente ejecutar.
  El modo con fechas repetidas mide expansión de filas y E/S, no diversidad
  temporal. El modo desplazado aumenta ventanas distintas sin crear evidencia
  científica ni tocar observaciones reales.

## Latencia de observaciones: primeras medidas locales

`curl` contra HA local `127.0.0.1:8101`, sin modificar observaciones:
el endpoint de detalle de la observación investigada devolvió HTTP 200,
5.134 bytes y 0,040148 s; la página de mantenimiento filtrada a la especie,
HTTP 200, 2.644.999 bytes y 1,239986 s. El selector de especie envía el formulario
completo; la selección de fila usa el endpoint pequeño. Fuentes de código:
`selectObservationRow` / `serve_mushroom_observation_detail` en `web_server.py`,
render de filtros/modales en `mushroom_profiles_ui.py`.

Esto identifica dos caminos distintos y una página voluminosa. No demuestra
que los JSON causen los segundos observados en la RPi ni justifica por sí solo
migrar la base de datos. Fuentes originales y formato canónico sin cambios.

## Pendientes antes de dar por cerrado el rendimiento

Medir y verificar preparación final, selección/reutilización completa y recorrido
con 5.000 observaciones. Distinguir ejecución inicial, actualización de datos y
cambio exclusivo de K. Comprobar conservación de predicciones/gates/purgas.
Resolver el crecimiento de semanas/celdas y sus límites actuales mediante
compactación/procesamiento acotado, no elevando máximos. Revisar identidad del
código para no invalidar cálculos reutilizables por cambios de presentación o
replay; no aceptar unidades antiguas sin igualdad de sus entradas consumidas.
Reconstruir componentes locales afectados cuando el cambio esté validado,
conservar exactamente ambos coordinadores del worker y dejar el lanzamiento de
los trabajos operativos al usuario. Sin release.

### Huellas compartidas y primera prueba de volumen (07/10)

- `integrated-batched-keys`: 236,224 s; preparación 41,934 s; hasta selección
  216,019 s; comparación 20,205 s. `integrated-batched-warm`: 76,133 s;
  preparación 40,414 s; hasta selección 56,143 s; comparación 19,990 s.
  Los dos reutilizan 990 resultados anuales: no incluyen ajustes ni inferencia.
  Igualdad exacta de generación, todas las claves y comparación, recibos de paridad
  junto a cada `result.json`. La última usa 1 CPU/1 GiB, sin swap, pico cgroup
  1.003.331.584 bytes. Objetivo <1 minuto conseguido sólo con ese alcance.
- Cambios posteriores: V3 deja de retener el JSON de diagnósticos después de
  extraer altitudes escalares; cinco pruebas del runner aprobadas. La memo de
  ajustes incluye versiones Python/numpy/scipy/sklearn para no aceptar bundles
  incompatibles. No se ha reconstruido ni desplegado una imagen con estos cambios.
- `prepare-5000-replicated`: preparación sintética exclusivamente, 5.000 IDs
  distintos replicando fechas/sitios de 549 observaciones, sin ajuste, inferencia,
  selección ni comparación. Plan numérico 144.900.000 bytes. V3 fixed 19,974 s,
  V4 fixed 25,709 s, V3 lag 59,502 s; salida 137 en V4 lag. Evento Docker OOM
  a las 23:39:51 UTC, contenedor `unruffled_roentgen`. No existe resultado final.
  Se repite con telemetría de memoria y liberando las copias del propio generador
  sintético antes de atribuir toda la retención al código de producción.
  Esta prueba mide volumen de filas, no 5.000 lugares/fechas independientes.

- `prepare-5000-memory` volvió a terminar con salida 137 después de completar
  los 1.487 estados de suelo. El proceso retenía después todas las filas V4.
  V4 privado ahora genera filas por lotes y cuenta los perfiles por fila; no
  materializa una segunda matriz para calcular elegibilidad. También se libera
  la copia de observaciones del planificador antes de ejecutar los constructores.
  26 pruebas dirigidas aprobadas (runner, formato de matrices, V4).
- `prepare-5000-v4-stream`: **124,085 s**, 1 CPU/1 GiB/sin swap, preparación de
  5.000 filas completa; pico RSS 968,9 MiB y cgroup 1.068.998.656 bytes.
  Las seis matrices contienen 5.000 muestras fixed y 35.000 lag; las filas
  adicionales de V4 son el catálogo de suelo, no observaciones adicionales.
  No incluye selección, ajustes ni comparación. Recibo `result.json` en esa
  carpeta. Las fechas/sitios siguen siendo los 549 originales replicados.

### Materialización bajo demanda — trabajo posterior en curso

Las seis matrices actuales tras streaming V4 coinciden exactamente con la
referencia (`prepared-v4-stream/prepared-parity.json`); preparación real 41,515 s.
Se implementa un camino del runner que sella registros/contexto/productor sin
crear todas las X de semanas. Reutiliza resultados antiguos sólo con tensor y
huella numérica antigua exactos, y descarta migraciones imposibles por conjunto
de casos. Los ajustes nuevos quedan enlazados a la memo privada; la comparación
materializa únicamente miembros solicitados. Si un bundle no cabe en la memo,
consume el ajuste una vez y guarda sus predicciones, sin repetirlo después.
Paquetes parciales comprimidos con integridad, límite de 49 celdas y mezcla
transaccional; mismo presupuesto SQLite. Cuarenta pruebas dirigidas aprobadas,
incluida igualdad exacta eager/deferred en ambos contratos temporales y cero
reajustes. Falta validación integrada y ampliar la evidencia compacta para 5.000.
No se ha reconstruido ni desplegado esta revisión.

Medición de formato, datos sintéticos replicados, sin resultados científicos:
5.152 visitas, 4.732 casos con evidencia, 725.844 celdas y 232.624 enlaces de
unidades: generación JSON 19.798.543 bytes, zlib 5.808.995. Sólo las celdas en
columnas tipadas sin pérdida: 10.161.816 bytes crudos, 3.253.639 comprimidos,
4.338.188 en base64 (0,693 s). Recibos `generation-volume.json` y
`evidence-columns-volume.json`. Se estudia separar representación numérica
compacta de las estructuras Python, sin limitar ventanas de fechas ni forzar
actualizaciones por calendario; fuentes originales siguen JSON. Todavía no se
ha cambiado el contrato público ni sus límites.

### Columnas compactas implementadas, pendientes de integración completa

`mushroom_competing_columns.py` conserva probabilidades float64 y tres índices
uint16. Valida SHA-256, descompresión acotada, orden/unicidad, rangos y cardinalidad
antes de consumirlos. Una sola caché tipada; vistas de subconjuntos comparten sus
columnas e índice. Las estadísticas diarias se agregan por candidato con el mismo
orden de sumas. Se mantienen todas las fechas y ventanas arbitrarias: no se
introduce una caducidad diaria ni nuevos trabajos por calendario.

La evidencia grande usa columnas; la pequeña conserva el formato anterior.
Límite público de 16 MiB, con máximo numérico decodificado de 28 MB (dos millones
de celdas), índice de hasta 8 MB y base64 de hasta 14 MiB. El consumidor no crea
una lista Python por cada celda. No equiparar este límite con tamaño observado:
el diagnóstico de 5.152 visitas midió 4,34 MB de columnas base64. El legado sigue
limitado a 1 MiB/50.000 celdas. La generación privada se comprime incrementalmente
con techo de 32 MiB comprimidos/128 MiB de JSON, dentro del presupuesto SQLite
original de 96 MiB. El resultado sigue ligado a lote/snapshot/huella de calidad.
Fuentes originales y observaciones permanecen sin cambios.

48 pruebas dirigidas aprobadas incluyendo columnas, estadísticas y rankings
exactos para A/B/C/D y distintos K, representación >50.000 celdas, rechazo de
corrupción/bombas y almacenamiento privado. La comprobación integrada
`integrated-requested-panels` está en curso, sólo lectura de resultados reales y
con nuevos ajustes/inferencias bloqueados. Todavía no se ha desplegado.

## Actualización 07/10: índices de comparación y prueba de volumen

Sin despliegue ni aumento de recursos. La integración `integrated-requested-panels`
terminó en 234,760 s (41,176 preparación, 214,663 hasta selección y 20,097
comparación), con las 990 unidades antiguas reutilizadas y ajuste/inferencia
bloqueados. Igualdad exacta de claves, visitas, 25.923 celdas y comparación en
sus recibos `selection-parity.json` y `comparison-parity.json`. Esta prueba
acredita la migración/reutilización de paneles completos antiguos; la nueva
materialización parcial tiene pruebas sintéticas, no una ejecución operativa nueva.

Después se añadieron búsqueda por prefijos de fechas/grupos, auditoría nativa
sobre columnas (mismas métricas, orden, poblaciones y exclusiones) y reutilización
de semanas con iguales área, fecha, evidencia previa, K y todas las asignaciones
de familias a ajustes. Los siete resultados se conservan y cada visita sigue
contando por separado. Se cambia la representación, no el procedimiento.

- `replay-indexed-real.json`: **11,567 s**, 184 visitas, igualdad exacta con la
  comparación original de **408,847 s**; recibo `replay-indexed-real-parity.json`.
- `replay-5000-columnar/result.json`: prueba anterior detenida por su presupuesto
  de 580 s; no había terminado. No presentar como resultado completado.
- `replay-5000-indexed/result.json`: **36,270 s**, 5.000 visitas sintéticas
  repetidas de las 184 originales, 4.595 casos/704.897 celdas; 794 semanas
  resueltas y 32.883 reutilizaciones. Un núcleo/1 GiB/sin swap, máximo cgroup
  295.706.624 bytes. Sólo replay de probabilidades guardadas; no ajuste/inferencia.
  **No equivale a 5.000 lugares y fechas independientes.**
- La prueba `replay-5000-varied` desplaza fechas y grupos en cada réplica,
  usando probabilidades traducidas sólo para medir coste. Está en curso; muestra
  que reconstruir las estadísticas diarias por conjunto previo sigue siendo caro.
  No tiene interpretación científica ni acredita aún los diez minutos.
- La lectura/evaluación de matrices de 5.000 filas (`selection-5000-overhead`
  y `selection-5000-overhead-memory`) termina con salida 137. Evento Docker OOM
  confirmado en la primera. La instrumentación de la segunda localiza el salto
  al cargar V4 lag después de V3 lag: ~651 MB antes de V4. No es coste de ajuste:
  las llamadas de entrenamiento/inferencia están prohibidas en ambas pruebas.
  Se prepara una proyección de los diagnósticos ya consumidos, sin modificar X.

67 pruebas dirigidas pasan en la revisión de índices/auditoría; las siguientes
optimizaciones se están preparando como borradores aislados mientras finaliza
la medición activa para no mezclar versiones del código durante una ejecución.


Actualización 07/10 02:41: las estadísticas diarias ahora se preparan por
candidato una sola vez y las ventanas sólo seleccionan los días/grupos pertinentes.
`replay-statistics-real.json`: **8,378 s**, igualdad exacta con los resultados
originales; recibo `replay-statistics-real-parity.json`. La prueba de 5.000 con
fechas desplazadas todavía no ha terminado y no alcanza el objetivo.

La selección lee sólo la fuente y el perfil necesarios, conserva columnas tipadas
en V3/V4 y omite diagnósticos ya consumidos. Las proyecciones se han contrastado
con todos los perfiles de la prueba de constructores reales: mismas X, etiquetas,
identidades y exclusiones. `selection-5000-lazy/result.json` termina en **145,062 s**,
con 5.000 filas totales/1.681 visitas objetivo, 990 unidades, 1 CPU/1 GiB/sin swap.
Incluye lectura, particiones, huellas y coordinación; **los ajustes y predicciones
están sustituidos explícitamente**, por tanto no mide la selección numérica completa.
Alcanza el límite de memoria del diagnóstico pero ya no termina por OOM.

La localidad de caché también está medida: `cache-locality.json` simula las
35.000 fechas de emisión posibles, sin filtrar temporada/ausencias. Con 8 entradas
repite 9.528 auditorías; con 16 baja a 2.162 y con 32 a 2.140. Se prepara una
caché con límites tanto de entradas como de bytes, para cubrir esas semanas
solapadas sin crecer indefinidamente. Los nuevos borradores se prueban separados
de la medición activa de comparación. No se ha ampliado hardware ni desplegado.


## Mediciones adicionales, 07/10 02:55 Madrid

- `replay-5000-cache/result.json`: 302,973 s, 5.000 visitas sintéticas con fechas
  desplazadas cinco días por réplica y grupos distintos. 4.595 casos, 704.897
  celdas; sin ajustes/inferencia. 1 CPU/1 GiB/sin swap, pico cgroup 327.843.840 B.
  Auditoría nativa 53,909 s; ranking 166,443 s; resolución semanal 62,519 s.
- La revisión de estadísticas anterior (`replay-5000-statistics`) agotó el plazo
  de 580,552 s, con unas 3.680 visitas. Reutilizar prefijos y ampliar las entradas
  de las caches dentro de límites explícitos por bytes evitó repetir trabajo.
- `selection-5000-lazy-2g`: 145,818 s; duplicar RAM frente a 145,062 s con 1 GiB
  no mejora el tiempo. Sólo coordinación/huellas, sin ajustes ni comparación.
- `selection-5000-timed`: 147,083 s; lectura 26,403, particiones 17,896,
  `unit_keys` 62,577 y huellas de semanas 17,111 s. Huellas antiguas descartadas
  cuando ninguna población anterior puede coincidir y trabajo compartido por
  especie/perfil: `selection-5000-scoped` 139,284 s; lectura 26,090,
  particiones 17,806, claves 59,054 y huellas de semanas 17,016 s.
- Agregación tipada con `numpy.add.accumulate` mantiene el orden exacto de las
  sumas, incluidos errores Brier. `replay-aggregate-real` 8,342 s, salida idéntica
  a la referencia completa de 408,847 s. Nueva prueba de 5.000 en curso.
- Índice de particiones que prepara identidades, grupos y episodios una vez:
  `partition-parity.json`, 1.200 poblaciones de prueba exactamente iguales al
  algoritmo anterior, incluyendo grupos que cruzan años y especies. Medición
  de rendimiento en curso. No altera las purgas de 14 días.

No se han reconstruido/recreado servicios, lanzado trabajos operativos ni cambiado
observaciones privadas. Estas mediciones parciales no acreditan todavía la meta
completa de 10 minutos para 5.000 observaciones.


## 07/10 03:01 Madrid: agregación, particiones y huellas de ajustes

La comparación `replay-5000-aggregate` termina en **189,430 s** frente a
302,973 s, con salida exactamente igual (`parity.json`). 1 CPU/1 GiB/sin swap;
pico cgroup 316.493.824 B. El ranking baja de 166,443 a 52,448 s; auditoría y
resolución semanal se mantienen alrededor de 54 y 63 s. Probabilidades guardadas,
sin nuevos ajustes/inferencias; no confundir con ejecución completa.

`selection-5000-partitions`: 122,534 s, sólo lectura/coordinación/huellas (ajustes
sustituidos). El índice temporal tarda 1,041 s y sus 240 consultas 0,579 s frente
a 17,806 s de particiones independientes. Se han compartido además las huellas
exactas de entrenamiento con el recorrido de validación, sin volver a serializar
por estimador dentro de `Fits.key`. Pruebas dirigidas 35/35. La medición
`selection-5000-fit-seal` incluye ese coste antes omitido: 130,746 s; no acredita
el ahorro de ajustes completos porque sigue sustituyéndolos.

Se inicia `full-5000-cold`, con ajustes e inferencias numéricos reales sobre las
réplicas sintéticas de 549 filas, cachés completamente aisladas y 360 s de plazo.
Usa las seis matrices previamente preparadas; no incluye sus 124 s de construcción.
Sólo 1.681 de esas filas son de las dos especies objetivo. Es una prueba de coste,
no un resultado científico ni una modificación de modelos instalados. Integración
real de 990 unidades guardadas en curso por separado (`integrated-final-cache`).

Suite ampliada: 210 casos, 202 pasan en imagen worker; ocho de backend no pueden
importar la aplicación porque esa imagen no incluye Pillow. Se repiten en el
entorno de aplicación, sin añadir esa dependencia al worker.


## 07/10 03:07 Madrid: integración y defecto en memo de modelos

`integrated-final-cache` termina en 247,817 s, 990 unidades antiguas reutilizadas,
preparación 43,383 s, hasta selección 239,167 s. Las huellas semanales se
reconstruyen una vez bajo la identidad de variables nueva. Paridad exacta de
8.308 claves, 184 visitas, 25.923 celdas y comparación. Repetición con huellas
ya disponibles `integrated-final-warm`: 73,137 s total, 43,571 preparación,
64,755 hasta selección; **esta revisión no cumple aún <60 s** en esa medición.
Un núcleo, 1 GiB, sin swap. Productor
`87a476b5bd42c0d00b4920768f1a4b1dbfa3f67ab642d90f1109fffbcae3ac59`.

`full-5000-cold` alcanza su límite voluntario de 360,082 s tras 364 ajustes
externos; no termina selección. 1 CPU/2 GiB; matrices ya preparadas, 1.681
visitas objetivo de 5.000 filas. `fit_artifact` acumula sólo 49,233 s: la búsqueda
interna V6 se ejecuta fuera de ese contador. La reconstrucción de semanas al
no poder guardar modelos también consume tiempo. Las familias lentas 17–19,
29–31 y 31–33 son **V6 30/60/90 días**, no V5 (corregir la hipótesis inicial).

Defecto confirmado: `pickle` protocolo 5 entrega `PickleBuffer` para arrays
grandes. `_BoundedBuffer.write` llamaba `len(data)`, que lanza TypeError; el
productor lo trataba como modelo no cacheable y generaba semanas completas.
Reproducido con un array de 20.000 enteros, sin superar ningún límite.
Se corrige midiendo `data.raw().nbytes`; pruebas de persistencia y límite en bytes
para arrays C y Fortran. 23 pruebas dirigidas aprobadas. La nueva prueba fría
`full-5000-pickle-fix` tiene 580 s de presupuesto, sigue en curso; las primeras
106 estimaciones se guardan todas y no construyen semanas anticipadamente.

Hay borradores **no aplicados** para V5/SparseGroup en tmp. Nueve conjuntos
sintéticos mantienen coeficientes, toda la historia del objetivo y probabilidades
exactos; dos búsquedas V5 conservan configuración. El optimizador aislado pasa
1,454 → 0,944 s. No es todavía la medición del cuello principal V6.
Las ocho pruebas de backend pendientes pasan en `.venv`; 210 casos pertinentes
cubiertos entre los dos entornos. No se han desplegado estos cambios.


## Paralelismo acotado V6, prueba aislada

`parallel-draft-parity.json`: 3.438 filas de entrenamiento sintéticas de las 5.000,
159 columnas, V6 parcial 30 días fijo. 18 ajustes internos, 17,257 s secuencial
frente a 9,928 s con tres hilos. Coeficientes, interceptos, iteraciones, diagnósticos
y elección idénticos. BLAS a un hilo, Docker a 3 CPU/3 GiB. Es un borrador, no se
ha cambiado ni configurado el worker. Con el otro diagnóstico (1 CPU/2 GiB),
el máximo simultáneo queda en cuatro núcleos y 5 GiB. Meta total pendiente.


## 07/10 03:18 Madrid: causa dominante confirmada y revisión compacta

`full-5000-pickle-fix` llega al límite de 580,183 s sin completar selección.
372 ajustes externos; búsqueda histórica V6: **441,453 s/85 llamadas**, ajuste
externo 61,066 s, claves 17,721 s, inferencia 18,916 s. Ya no hay rechazos falsos
de cache ni semanas anticipadas. 1 CPU/2 GiB/sin swap, pico cgroup 1.506.545.664 B.

Alternativa comprobada: CSR sólo para las matrices de búsqueda interna V6. En
3.438 filas/159 columnas, los mismos 18 ajustes internos tardan 17,610 s densos
frente a 1,462 s dispersos. **No son bit a bit iguales:** diferencia máxima de
probabilidad interna 0,000032818; algunas diferencias sobreviven a seis decimales.
La configuración final coincide. Se ha ampliado a **84 validaciones anuales
sintéticas** terminadas por la referencia (80 + 4 posteriores), hasta 11.970
filas lag: mismas 84 configuraciones y mismos diagnósticos. Recibos
`sparse-v6-{diagnostic,folds,folds-later}.json`. No se presenta eso como prueba
universal de igualdad de búsquedas futuras próximas a un empate.

Se incorpora `compact_pooled_design` en `mushroom_competing_tuning.py`, evitando
materializar bloques cero mediante índices CSR; se activa sólo desde la búsqueda
histórica. La preparación/final fit/inferencia operativos siguen usando el
camino denso existente. La representación contiene exactamente las mismas columnas
y valores. Se incorporan también reutilización del preprocesamiento V5 por fold
y de grupos/logits en SparseGroup: estos dos mantienen coeficientes, iteraciones,
objetivos y probabilidades exactos en las nueve pruebas aisladas. 44 pruebas
dirigidas aprobadas. La variante paralela de tres hilos sigue como borrador,
no configurada en el servicio.

`full-5000-compact-tuning` en curso, matriz de 5.000 observaciones total/1.681
objetivo, 1 CPU/2 GiB, presupuesto 580 s. Preparación previa excluida del tiempo.
Se prepara además `prepare-target-5000-varied`: ahora **5.000 observaciones de
las dos especies objetivo**, con fechas desplazadas cinco días por ciclo; esta
carga evita confundir 5.000 filas totales con 5.000 visitas evaluadas. Fuentes
originales intactas. Aún no acredita el objetivo ni está desplegado.

## 07/10 03:37 Madrid: carga de 5.000 visitas objetivo y paralelismo limitado

`prepare-target-5000-varied`: **185,025 s**, 1 CPU/2 GiB/sin swap;
pico cgroup 1.076.367.360 B. Son 5.000 réplicas de las 184 observaciones de
las dos especies, con fechas desplazadas cinco días por ciclo. Seis matrices;
no incluye selección ni comparación. Esto sigue siendo una carga sintética,
no 5.000 observaciones independientes ni una evaluación científica nueva.

`full-5000-compact-tuning` (5.000 filas totales, 1.681 objetivo) se detiene por
su límite voluntario a 580,448 s: 589 intentos de ajuste externo, 300,453 s en
ajustes, 82,805 en búsqueda V6, 59,068 en claves y 58,196 en inferencia.
**Las 372 unidades numéricas completas comunes con la referencia densa son
exactamente iguales**, incluidas configuraciones y diagnósticos;
`full-5000-compact-tuning/numerical-parity.json`.

`full-target-5000-varied`, ya con las 5.000 visitas objetivo, alcanza su límite
a 418,230 s, sin terminar selección (368 ajustes). Preparación excluida.
1 CPU/2 GiB; 160,383 s de ajustes, 78,007 de inferencia, 58,349 búsqueda V6,
32,509 huellas de semanas, 29,486 claves. No acredita diez minutos.

Prototipo de búsqueda V5 con dos hilos, 15.799 filas y 310 columnas:
50,532 → 30,859 s en elastic-net y 2,926 → 1,976 s en sparse-group, mismas
elecciones (`v5-parallel-parity.json`). No se incorpora ese paralelismo interno:
se incorpora en su lugar una cola de **hasta cuatro ajustes/validaciones
independientes**, también entre años, con BLAS a un hilo. Comparte matrices
inmutables; la escritura de SQLite y la preparación de paneles permanecen en
el hilo principal. Opt-in `RAINMAPPER_HISTORY_FIT_WORKERS`, por defecto 1,
validado entre 1 y 4. Servicios todavía sin configurar/recrear.

Primera prueba a cuatro núcleos detenida voluntariamente mediante la alarma de
**su propio diagnóstico** a 68,755 s para corregir una barrera anual innecesaria;
ningún trabajo operativo fue cancelado. Su caché parcial se conserva.
La versión nueva deja ocupar la cola con años independientes sin cambiar el
orden de publicación ni la separación temporal. Pruebas con barrera de dos
hilos acreditan concurrencia real; comparación serial/paralela exacta y ninguna
escritura SQL desde los hilos numéricos.

Además, claves nuevas `row_sha256_v1`: cada fila de variables/etiqueta/identidad
se serializa y sella una sola vez por perfil, reutilizando su digest entre años
y estimadores. El caché de filas pertenece a un benchmark inmutable y está
acotado por MAX_SAMPLES. Los productores antiguos se consultan sólo mediante
sus claves originales exactas y las huellas semanales originales. No se omiten
ni redondean variables. 57 pruebas dirigidas pasan tras estos cambios.

`full-target-5000-digests-four` en curso: 4 CPU/8 GiB/sin swap, cachés privadas
frías y ajustes/inferencias reales; preparación de 185,025 s medida aparte.
No se da por cumplida la meta. Los contenedores de servicio siguen intactos,
coordinadores sin cambios y fuentes originales conservadas.

## 07/10 03:51 Madrid: eliminar diagnósticos descartados y evitar desborde a semanas masivas

`full-target-5000-digests-four` se detuvo mediante la alarma de su diagnóstico;
terminó tras esperar ajustes pendientes a 538,261 s, sin acabar selección.
**Los contadores de funciones se solapan entre hilos y no se pueden sumar como
un desglose de tiempo de pared.** Se habían intentado 506 ajustes. La huella por
filas empleaba 14,643 s frente a recorridos JSON repetidos. Pico cgroup
2.711.699.456 B, sin swap.

Causa adicional comprobada con SQLite en sólo lectura: 498 modelos guardados
ocupaban **67.107.690 bytes**, prácticamente el límite de 64 MiB. El rechazo de
las siguientes entradas activaba un fallback que materializaba semanas completas;
sólo cinco llamadas ya consumían 89,372 s. Se ha eliminado ese crecimiento
implícito: si no cabe un modelo necesario para diferir semanas, el trabajo informa
`history_fit_cache_budget` y se detiene antes de expandir el producto de semanas.
No incrementa los límites ni elimina archivos para continuar.

Compresión exacta de los mismos 498 modelos, con descompresión comparada byte a
byte (`fit-compression-codecs.json`):

| Códec | Bytes | Segundos de compresión |
| --- | ---: | ---: |
| zlib 1 anterior | 67.107.690 | 1,493 |
| zlib 6 | 62.336.107 | 2,860 |
| Zstandard | **52.990.972** | **0,311** |
| XZ 1 | 45.100.048 | 5,778 |

Se utiliza Zstandard a través de PyArrow, ya presente en el worker. Sobres
privados RMF2 con longitud descomprimida acotada a 32 MiB y paquete máximo 8 MiB;
se conserva lectura de zlib antiguo, SHA del paquete y validación del productor.
No se modifican modelos/observaciones originales ni entradas antiguas.

La validación histórica sólo consume la probabilidad de cada fila. Se añade
`probability_only=True` a la inferencia por lotes para omitir detalles de UI y
aplicabilidad que se descartaban. También lee vistas columnares en bloque.
Preprocesamiento, modelo, validación de valores y redondeo a seis decimales son
los mismos; por defecto la inferencia del mapa conserva el payload completo.
`inference-draft-parity.json`: **11 familias × 4.096 filas**, mismas probabilidades;
V5/V6 160 columnas pasan aproximadamente de 1,04–1,10 s a 0,03–0,08 s. Se
compara además el payload completo de muestras columnares y diccionarios.

69 pruebas dirigidas aprobadas tras estas correcciones. Se inicia
`complete-target-5000-probability-zstd`, con **preparación incluida en el mismo
proceso**, 4 CPU/8 GiB/sin swap. Esto conserva la reutilización del workspace
meteorológico entre preparación y comparación, como en el runner real. Sigue en
curso; **no acredita todavía la meta**.

El compose del worker local queda preparado con cpus=4, memoria=8 GiB, límite
de memoria+swap también 8 GiB y `RAINMAPPER_HISTORY_FIT_WORKERS=4`; configuración
compilada y comprobada, **todavía no aplicada al servicio**. Los coordinadores
persistidos y las imágenes en ejecución siguen sin cambios por esta revisión.

## 07/10 04:08 Madrid — límites y reutilización semanal

`complete-target-5000-probability-zstd` terminó con error `history_audit_limit` a 617,927 s, tras preparar en 172,511 s y completar 524 ajustes (521 persistidos). No llegó a comparación. Pico cgroup 3.365.482.496 bytes; 4 CPU/8 GiB/sin swap. Las 368 unidades comunes con `full-target-5000-varied` coinciden íntegramente (`numerical-parity.json`). No es una prueba completa aprobada.

La auditoría privada de ausencias ahora es gzip por streaming, conserva el contenido JSONL y el límite de 8 MiB en disco; límite adicional de 128 MiB descomprimidos. No se borró el diagnóstico original.

La reanudación privada `resume-target-5000-audit` se detuvo voluntariamente a 255,157 s al observar reconstrucción de semanas completas buscando unidades de productores antiguos que nunca existieron en esa caché. Se conservan ambos SQLite. Se añaden alias exactos de claves migradas y una marca sólo al completar la preparación: actualizaciones posteriores del mismo productor no vuelven a buscar aquellas generaciones antiguas. Los alias retienen la clave original usada por paneles.

Nuevas optimizaciones pendientes de medición completa:
- Huella de entrada por unión exacta de intervalos meteorológicos de la semana, evitando expandir 49 miembros para comprobar fuentes. Prueba comprueba que cubre desde el primer hasta el último registro de todos los miembros.
- Inferencia en lote de los siete miembros del candidato solicitado para una semana. Cache de 4 MiB comparte miembros entre observaciones con modelo, especie, área, fecha y horizonte idénticos; no usa etiquetas de observación.
- Reutilización del resultado completo entre reglas con el mismo ranking y resolución semanal; C y habitual mantienen semánticas separadas.
- Un pool global de búsqueda interna V5/V6 compartido por los ajustes históricos evita CPUs ociosas esperando el último ajuste. Sólo la ruta histórica opta por él; contenedor limitado a 4 CPUs y 8 GiB. Reducción de candidatos, scores y empates en el orden original.

94 pruebas dirigidas aprobadas (14,255 s). Incluyen paridad serial/paralela V5 y V6, reutilización de miembros y semanas frente a cálculo íntegro, fronteras meteorológicas, auditoría sin pérdida y alias de migración.

**En curso:** `complete-target-5000-week-reuse`, cachés frías, preparación incluida, 4 CPUs/8 GiB. No se han reconstruido los servicios ni lanzado trabajos operativos. Meta ≤600 s todavía no acreditada.

## 07/10 07:10 Madrid — prueba completa pendiente y comparación por lotes

`complete-target-5000-week-reuse` acabó por el límite privado del diagnóstico a
1.400,919 s, sin completar comparación. Preparación 173,456 s; selección terminada
a 763,778 s; 584 ajustes persistidos y 521 unidades completas comunes **exactas**
con la referencia precedente. Pico cgroup 3.539.005.440 bytes. El objetivo de
600 s sigue sin alcanzarse. Los contadores por función se solapan entre hilos.

Se observaron 33.625 lecturas/deserializaciones de modelos (86,86 s) y 34.313
inferencias pequeñas (210,68 s). Cambios posteriores, todavía sin desplegar:

- Caché LRU de modelos, hasta 64 entradas y 64 MiB de peso estimado conservador
  (3 × pickle descomprimido + 64 KiB por entrada). No es una cota exacta del RSS.
- Inferencia histórica de aplicabilidad compacta: conserva probabilidad, gates,
  z-score redondeado y estado; evita construir explicaciones descartadas. La
  respuesta completa del mapa sigue siendo el valor por defecto.
- Lotes de hasta 16 visitas/112 semanas, sólo de miembros solicitados por las
  reglas. Un miembro pendiente interrumpe la resolución; nunca se inyecta una
  probabilidad ficticia. Inferencias por modelo en tandas de hasta 256 filas.

Pruebas dirigidas nuevas: 26 pasan. Diagnóstico `target-64-single-week` frente a
`target-64-batched`: salida común exacta, 225 → 38 inferencias, 10 modelos leídos
en ambos. Tiempo total **19,803 → 20,314 s**; no es una mejora global.
Ambos reutilizan ajustes numéricos existentes y parten con entradas/paneles fríos.

`target-5000-batched` se detuvo voluntariamente mediante su alarma privada a
247,662 s, con 1.424 visitas procesadas: demasiado lento. Se preservaron cachés y
recibo. Ningún trabajo operativo cancelado. 87 modelos cargados, 1.613 inferencias
(6,471 s), 74.680 miembros construidos; pico RSS 755,508 MiB. Los miembros son
combinaciones fecha/horizonte/modelo, no nuevas observaciones. Se está midiendo
por funciones un tramo de 96 visitas para identificar el coste restante antes
de seguir modificando el diseño.


## 07/10 07:31 Madrid — costes medidos y nueva prueba fría

Perfiles aislados (cProfile, no comparar sus segundos con tiempos normales):

- Selección con ajustes numéricos existentes: 186,999 s. Trece lecturas Parquet
  consumían 32,085 s y 342.542 serializaciones de fila, 27,232 s. La nueva ruta
  conserva sólo las tres fuentes proyectadas de un contrato temporal y sella
  valores float64 little-endian con bitmap de nulos, sin JSON por valor. Distingue
  cero, nulo, signo de cero y cambios de un bit; rechaza no finitos. Marcador de
  clave `row_float64_le_v2`; no se acepta una clave vieja como equivalente sin
  pasar la comprobación de migración existente.
- Preparación: 410,773 s bajo cProfile, frente a 173,456 s normales anteriores.
  3.090.760 conversiones de fecha sumaban 24,99 s instrumentados. Se añade lectura
  ISO directa con fallback anterior, comprobando fechas malformadas/no rellenadas.
- Comparación 96 visitas, offset 700, modelos guardados y entradas/paneles fríos:
  59,233 → 48,667 → 46,832 s instrumentados. Los tres `comparison.json` son
  idénticos. SQLite pasa de 120.071 a 39.657 llamadas en el segundo perfil.
  El tercero añade ventanas raw acotadas y una transacción por lote. El coste
  restante sigue en series, copias y resoluciones reiniciadas; no basta para la meta.

La caché registra su procedencia desde la primera unidad, incluso si una
preparación se interrumpe. Las bases antiguas sin esa información conservan la
búsqueda conservadora. No se eliminan resultados ni se altera el origen.

77 pruebas de historia, cachés, lotes, comparación y scheduler pasan; 30 de V3 y
Parquet pasan. `inference-compact-status-parity.json`: once familias × 4.096 filas,
probabilidad y estado de aplicabilidad idénticos a la salida completa.

En curso `complete-target-5000-binary-batched`: preparación y ejecución completas,
cuatro ajustes concurrentes, 4 CPU, 8 GiB, sin swap, caches nuevas y sin modelos
instalados modificados. Su resultado todavía no acredita ningún tiempo.


## 07/10 07:43 Madrid — selección fría todavía supera la meta

`complete-target-5000-binary-batched`, código
`2a3460a0f7b1f5fc19945fdd4d0309f74774ccc92366adea6153cf63ecb96ecd`:
preparación 164,866 s; selección completada a 718,298 s. **584/584 unidades
numéricas exactas** frente a `complete-target-5000-week-reuse`.
Se detuvo voluntariamente con ALRM a 731,134 s porque la selección sola ya
excedía 600 s. El error del recibo es el límite del diagnóstico, no un fallo
operativo. Comparación incompleta; todos los archivos se conservan. 4 CPU,
8 GiB, cuatro ajustes concurrentes y pico cgroup 3.849.834.496 bytes, sin swap.

Ensayo privado `daily-template-verify-700`: para versiones V2/V3/V4 lag, una
plantilla de variables/calidad por corte y perfil se adapta a cada horizonte.
Se verifica cada fila contra una llamada al constructor original. En 96 visitas
no hay diferencias, tampoco en el `comparison.json` completo. 316 plantillas,
1.896 usos adicionales; 2.212 filas diarias en total. Todavía es un prototipo
privado, no una optimización desplegada. Su tiempo con doble construcción de
verificación no se compara con perfiles cProfile.


Ensayo `daily-template-profile-700`: 42,926 s con cProfile, frente a 46,832 s
sin plantillas; mismo `comparison.json`. `_series` pasa de 3.106 a 1.210 llamadas,
pero conserva 247 construcciones reales y muchas lecturas/decodificaciones.
La ganancia total es modesta; no atribuirle una aceleración de siete veces del
trabajo completo.

Diagnóstico de procesos: `check_process_diagnostic.py` compara nueve unidades
seriales frente a forkserver, exactas. El primer lanzador de volumen era
incorrecto: `runpy` exponía el script de medición como `__main__` y los hijos lo
repetían; se detuvo exclusivamente ese contenedor privado, conservando los
archivos como diagnóstico inválido. Cambiado el run name; `selection-process-5000-guarded`
usa procesos sólo para cálculo numérico, con SQLite exclusivamente en el padre.
Su arranque se solapó brevemente con el diagnóstico anterior antes de verificar
su parada efectiva: no usar este recibo como tiempo limpio de aceptación.
Permite comprobar igualdad y viabilidad; si se adopta exigirá una medición final
sin ese solapamiento. Ninguno de estos prototipos se ha desplegado.


## 07/10 08:01 Madrid — procesos descartados, cola acotada en evaluación

`selection-process-5000-guarded`: límite de 580 s y cierre a 647,832 s,
esperando ajustes pendientes; selección incompleta. 581 unidades persistidas,
581/581 exactas frente a `complete-target-5000-binary-batched`. Pico cgroup
4.756.942.848 bytes. No se adopta: no mejora el tiempo buscado. El solapamiento
inicial ya descrito impide utilizarlo como medición limpia de aceptación.

`check_queue_diagnostic.py`: 27 salidas numéricas exactas para la cola que
atraviesa familias manteniendo orden de publicación. Iniciado en contenedor
aislado `selection-global-lookahead-5000`: cuatro hilos de ajuste y cuatro
de tuning compartidos, hasta 16 operaciones pendientes; límite 4 CPU/8 GiB.
Preparación existente, ajustes fríos, comparación excluida. La nota privada
sella las copias experimentales: el `code_id` del recibo por sí solo no las
identifica. No hay cambios operativos ni prueba completa de rendimiento.


`selection-global-lookahead-5000` termina: selección **488,856 s**, total del
diagnóstico 490,516 s (incluye persistencia). 584/584 unidades numéricas exactas
frente a `complete-target-5000-binary-batched`; pico cgroup 3.777.695.744 bytes.
Preparación excluida: no comparar directamente con los 718,298 s que sí la
incluían. Mejora moderada; todavía no acredita los diez minutos completos.

Continuaciones privadas: `check_continuation_diagnostic.py` compara 48 semanas
con resolución original, fixed/lag, diaria/semanal, eager/lazy, planes preparados
y alternativas por aplicabilidad. Salida y llamadas de materialización exactas.
Iniciado perfil de 96 visitas `continuations-series16-700` con una caché separada
de series de 16 MiB, plantillas y continuaciones. Modelos existentes sólo lectura.


Perfiles de continuaciones (96 visitas, offset 700): 40,058 s con continuaciones
y caché de series independiente de 16 MiB; 38,749 s al recuperar semanas
equivalentes completadas durante una pausa. Ambos `comparison.json` exactos
respecto a `daily-template-profile-700`. El segundo vuelve a 186 semanas
calculadas/451 reutilizadas, frente a 347/290 antes de corregir la reutilización.
Son perfiles cProfile, no tiempos completos de aceptación.

En curso `continuations-cold-5000`, sin cProfile, 5.000 visitas sintéticas con
modelos históricos ya guardados y entradas/paneles nuevos, presupuesto 420 s.
No incluye preparación ni ajuste, no permite afirmar el objetivo completo.


## 07/10 08:26 Madrid — límite de la comparación fría y ensayos adicionales

`continuations-cold-5000` agotó 420 s: 4.144/5.000 visitas, 420,013 s reales,
comparación incompleta, RSS 819,609 MiB. 177 modelos cargados, 257.281 miembros
calculados y 251.913 reutilizados. Meteorología 77,285 s; inferencia 26,329 s.
No equivale a 5.000 visitas completas ni prueba de los diez minutos.

`volatile-series16-700`: 35,791 s instrumentados, salida de 96 visitas exacta,
frente a 38,749 s con persistencia de variables por horizonte. Caché temporal
acotada de 16 MiB, ventanas raw de 16 MiB, plantillas de 8 MiB. Aún privado.

Pruebas privadas: `check_physics_suffix_diagnostic.py`, 96 historiales exactos,
incluyendo huecos, sequía, saturación y límite de 90 días. Sólo se comparte el
sufijo si las reservas de ambas trayectorias son exactamente iguales; se
conserva el máximo conjunto de error de masa. `check_bulk_audit_diagnostic.py`,
630 evaluaciones completas exactas de estadísticas en bloques frente a escalares.
Poblaciones de ranking: ordinal big-endian + hash ASCII de longitud fija conserva
la comparación lexicográfica del par fecha/hash, evitando listas de cadenas.

Perfil de 96 visitas desde offset 3.500: `volatile-series16-3500` 32,594 s;
`bulk-compact-series16-3500` 30,028 s. Misma salida completa; sin cambios de reglas.
Iniciado `selection-process-lookahead-5000`: cola de 16 operaciones, cuatro
procesos de cálculo, 4 CPU/8 GiB, matrices preparadas pero ajustes nuevos.
No incluye preparación ni comparación. Los prototipos permanecen aislados.


### 07/10, 08:43 Madrid — ensayos aislados todavía sin integrar

`selection-process-lookahead-5000`: selección fría **467,508 s**, total con
publicación 469,148 s; preparación y comparación excluidas. **584/584 unidades
numéricas completas exactas** frente a `complete-target-5000-binary-batched`.
Pico cgroup 4.715.716.608 B, CPU 4, RAM 8 GiB, swap 0. Los procesos no quedan
adoptados por esta medición; mejora pequeña frente a la cola de hilos.

`parallel-bulk-cold-5000`: comparación de 5.000 visitas en cuatro particiones,
**152,437 s**, pico cgroup 3.212.554.240 B. Ajustes inmutables previos; entradas
y paneles semanales inicialmente vacíos. Bloques 73,082 / 149,408 / 90,414 /
102,256 s. No incluye preparación ni selección. Toda la ejecución quedó en un
contenedor aislado con límite total 4 CPU / 8 GiB, sin acceder a la red.
La primera verificación por lectura de paquetes (`parity.json`) **no coincide**:
el resolver original excluye 11 visitas de aereus por paquetes/días ausentes.
Hipótesis a comprobar: el evaluador por lotes había servido esas semanas desde
visitas equivalentes, y el verificador sólo buscaba el ID original. Preparado
`verify_parallel_comparison_area_reuse.py`: permite únicamente reutilizar un
paquete del mismo modelo/unidad, especie, área, día y horizonte, como las
entradas reales de `Builder._requests`; no reconstruye meteorología ni modelos.
No afirmar equivalencia global hasta ejecutar esa verificación.

En curso `selection-priority-process-5000`: mismos candidatos y particiones,
años grandes primero y familias costosas adelantadas. El prototipo restaura el
orden original de consumo de unidades antes de resumirlas; usa una lista privada
aún no adecuada para integrar sin un límite más estricto. No cambia servicios.
Meta completa ≤600 s todavía no acreditada.


`selection-priority-process-5000` detenido mediante ALRM del contenedor privado
a 286,058 s (111 ajustes persistidos); no terminó, ni demuestra una mejora.
Se conservan sus archivos. Adelantar años/familias no resuelve la espera FIFO:
la cola puede tener resultados acabados detrás del primero aún en ejecución.
Preparado `run_ready_diagnostic.py` para recoger cualquier resultado terminado,
con cola máxima 16 y cuatro procesos. Restaura el orden original al resumir.
No se ha modificado ningún trabajo operativo.


### 07/10, 09:13 Madrid — integración y prueba completa en curso

`verify_parallel_comparison_area_reuse.py` terminó: **salida completa exacta**,
35 reutilizaciones de paquete entre visitas del mismo modelo/unidad, especie,
área, día y horizonte. Verificación 169,254 s, sin reconstruir meteorología ni
ajustes. Corrige la hipótesis anterior; `parity-area-reuse.json` conserva el recibo.

`selection-ready-process-5000`: **348,377 s** selección, total 349,940 s con
publicación; preparación/comparación excluidas. **584/584 unidades completas
exactas**, visitas idénticas y evidencia agregada idéntica excepto updated_at.
Pico 4.629.532.672 B, sin swap, cuatro CPU/8 GiB. Recoger resultados terminados
evita esperas FIFO sin modificar ajustes ni el orden final de consumo.

Integrado en producción (worktree, no imágenes): continuaciones, cachés acotadas,
auditoría vectorizada, agregación meteorológica reutilizable, sufijos hídricos,
cola de procesos y comparación por particiones. Orden original de unidades
restaurado con cabeceras temporales SQLite acotadas a 16 MiB comprimidos; datos
numéricos conservados en UnitCache. La comparación conserva paneles duraderos y
fusiona sólo derivados de las particiones; temporales nuevos limitados al mismo
presupuesto conjunto de 96 MiB. No se cambian modelos instalados ni datos fuente.

Pruebas: 52 de comparación/reutilización/resolver/agua; 34 de integración
scheduler/runner/meteorología/particiones; 24 scheduler/particiones con procesos
reales y restauración de orden. Grupos solapados; no sumarlos. Una prueba previa
de reutilización entre aperturas detectó pérdida de persistencia de variables:
corregida con persist_features=True por defecto, False sólo en comparación.

En marcha `production-cold-5000-ready-parallel`, runner.main real, preparación,
ajustes y comparación desde cero, cuatro CPU/8 GiB, sin red. Preparación
**155,958 s**; resto pendiente. No sumar fases de ensayos aislados para afirmar
la meta de diez minutos. Muestra sintética de dos especies, no prueba de todas.


### 07/10, 09:31 Madrid — fallo de integración detectado y comprobación acotada

`production-cold-5000-ready-parallel` **no terminó**: preparación 155,958 s,
selección completa 489,725 s acumulados; publicación/transición a comparación
hasta 505,201 s. Falló a **581,027 s**, tras 3.602 visitas informadas, con SQLite
`attempt to write a readonly database`. El padre fusionaba la primera partición
acabada mientras otras todavía leían su base. Corregido: el padre espera el
cierre de todos los lectores antes de fusionar. Meta completa no acreditada.
Pico cgroup 4.828.180.480 B. **584/584 unidades numéricas exactas** frente a
`complete-target-5000-binary-batched` (`numerical-parity.json`).

`production-striped-cold-5000`: comparación fría aislada, mismos ajustes
inmutables, nuevo reparto alternado de bloques de 128 visitas y fusión tras
cerrar lectores. **144,246 s**, resultado completo exacto frente al resolver
original, sin error; pico 3.326.726.144 B, cuatro CPU/8 GiB, swap 0. El reparto
alternativo sigue privado: mejora pequeña frente a 152,437 s anterior.

Prueba privada de física diaria: 1.616 historiales y todos los campos exactos.
La variante de reutilización entre ventanas conserva 6.437.312 transiciones y
calcula 1.067.818; preparación real **150,064 s** frente a 155,958 s, ahorro pequeño.
No adoptada: complejidad adicional todavía no justificada. Las cifras son días
de estados derivados en ventanas solapadas, no observaciones adicionales.
`preparation-rolling-5000` conserva su recibo y archivos.

En curso perfil de preparación actual `preparation-integrated-profile` y
prototipo privado `weather_column_draft.py`: meteorología intermedia en columna
Parquet tipada y lectura proyectada. Sin migrar la BBDD canónica, sin cambios en
servicios ni modelos instalados. No afirmar mejora ni equivalencia del prototipo
antes de validarlo y medirlo.


### 07/10, 09:55 Madrid — preparación compacta integrada, pruebas y nueva imagen

El perfil de preparación detectó medias meteorológicas de áreas repetidas para
6.973 ventanas solapadas de V5 y serialización de metadatos diarios que ningún
ajuste usa. Preparación privada `preparation-compact-5000`: **123,644 s**, frente
a 155,958 s de la prueba completa anterior. `prepared-parity.json` verifica
**120.000 filas** de las seis matrices: variables, etiquetas, calidad y metadatos
necesarios exactos; los diagnósticos descartados no forman parte de esta igualdad.
Se conservan todos los datos fuente y los exports científicos habituales.

Integrados: columna Parquet tipada opcional para meteorología V3 histórica;
proyección de metadatos privados; medias completas de lluvia/ET0/balance por área
con ventanas por referencia y límites de memoria. Fallback original si los ejes
no coinciden. BBDD canónica JSON sin migrar.

Resumen de evidencia: 584 unidades / 1.017.902 celdas, salida exacta salvo fecha;
**7,052 → 3,772 s** en prueba privada. Se conserva el hash de cada visita en una
caché acotada y se empaqueta evidencia una sola vez. Archivo de generación
validado idéntico al decodificar; codificación/acotación/compresión **0,328 s**.

Comparación con reparto alternado de bloques de 128 integrada con barrera antes
de fusionar SQLite. `selection-cost-order-5000` terminó **348,486 s** contra
348,377 s de referencia; **584/584 unidades exactas**. Reordenar V5 antes que V6
no mejora; descartado, se conserva el orden previo.

**100 pruebas dirigidas pasan** (13,736 s). Worker reconstruido desde el código
integrado; HA local en construcción. Servicios todavía no recreados. Pendiente
prueba completa fría desde imagen nueva y paridad efectiva. No acreditar aún
≤600 s, ni generalizar la muestra sintética de dos especies a todas.


### 07/10, 14:34 Madrid — paridad en contenedores y prueba completa fría

La comprobación real detectó que el Dockerfile worker omitía
`mushroom_weather_series.py`; corregido, imagen reconstruida y servicio recreado.
No bastaba la prueba textual de empaquetado previa. Comprobación efectiva de
**74 archivos** de procedimiento idénticos al repositorio. Repo, HA local y
worker devuelven revisión `b2e5c0f4bda4c687bc0b5e68a211d869ab2ec732d849b3ad8d309fc720bae581`.
HA local HTTP 200. Límites worker efectivos: NanoCpus=4000000000, memoria y
MemorySwap=8589934592 (sin swap adicional). Configuraciones de coordinadores
antes/después idénticas: `coordinator.json` SHA256
`5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10`,
`additional-coordinators.json` SHA256
`22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0`.
Sin cambiar fuentes, modelos instalados ni lanzar trabajos operativos.

Otros 110 casos de mapa/modelos/backend pasan; se corrigió un nombre de módulo
inexistente en la invocación de pruebas, y las 8 pruebas reales de estado hídrico
pasan. Siete pruebas de empaquetado pasan tras corregir Dockerfile.

En marcha `final-image-cold-5000`, código `/app` de la imagen nueva, sin red,
4 CPU/8 GiB. Preparación completa **143,828 s** con carga inicial; continúa
selección. La preparación privada de 123,644 s no debe sustituir esta medición.
Pendientes resultado completo, unidades numéricas y comparación final exacta.


### 07/10, 14:39 Madrid — resultado completo desde imagen reconstruida

`final-image-cold-5000` finaliza correctamente en **639,737 s (10 min 40 s)**.
**No cumple aún ≤600 s**: exceso 39,737 s. Preparación 143,828 s, selección
340,382 s; resumen/empaquetado/comparación/publicación final 155,528 s.
La comparación completa es exactamente igual a la referencia del resolver
original. `numerical-parity.json` confirma **584/584 unidades numéricas
completas iguales** frente a `complete-target-5000-binary-batched`.

Cuatro CPU, límite de memoria 8 GiB, pico cgroup **5.062.926.336 B (4,715 GiB)**,
swap 0. Revisión del procedimiento antes/después idéntica
`b2e5c0f4bda4c687bc0b5e68a211d869ab2ec732d849b3ad8d309fc720bae581`.
Artefacto final 4.170.143 B, 990 unidades procesadas desde cero (584 con
predicciones comparables; las demás conservan sus ausencias justificadas),
0 reutilizadas en el resumen. Las exclusiones son por falta de antecedentes,
clase única, límites de episodios o perfil; no se han recortado observaciones
para cumplir tiempos. Muestra sintética de dos especies: no generalizar
a todas las especies ni a 5.000 visitas reales independientes.

El worker operativo queda idle en ambos carriles; ningún trabajo operativo
se ha lanzado para esta prueba. Datos fuente/modelos instalados conservados.
Pendiente recortar al menos 40 s más y conseguir margen, especialmente en
selección (53,2% del total), antes de acreditar la meta. No publicar release.
