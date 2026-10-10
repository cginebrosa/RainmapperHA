# Contexto activo — actualización 10/10/2026

## Release HA 0.2.336 · publicada, pendiente de instalar en HA real

El usuario aceptó el precálculo local completo de 2m47s y autorizó publicar.
Incluye optimización del precálculo/artefactos y selección/comparación de las K
del add-on y dispositivos activos, con estado de K preparadas y pendientes.
Smoke correcto: 2.128 pruebas, 55 omitidas, sin fallos. Fuentes efectivas de
HA/worker coinciden con la candidata aceptada; sin repetir trabajos operativos.
GHCR: `0.2.336` y `latest`, digest `8af3d7f7…`, manifests amd64/arm64.
Ver [informe de release](reports/release-ha-0.2.336-2026-10-10.md).
Instalación y prueba en HA real a cargo del usuario; el worker compatible ya
está actualizado. Coordinadores y observaciones privadas conservados.

## Precálculo local completo en 2m47s; K de selección/comparación probado

El usuario autorizó optimizar el precálculo semanal hacia dos minutos, con
agentes para cálculo y validación/entrega. No se han lanzado trabajos operativos
ni entrenamientos desde Codex. El usuario sigue lanzando los trabajos.
El worker mantiene sus coordinadores y su presupuesto de recursos.

Mediciones verificadas del artefacto existente y consultas aisladas: validación
completa en Mac 16,31→3,65 s, mismo manifiesto y hash; Lactarius/Urus
16,477→6,234 s y Caesarea/Olvan 16,062→6,173 s, respuesta completa idéntica
con semilla de proceso fija. La meteorología pasa de 21 preparaciones a tres
por consulta; las tres ventanas físicas distintas se conservan. Contextos y
catálogo se comparten por runtime; filtro de última área y dos ventanas exactas
de estaciones como máximo en la nueva caché preparatoria.
Estas medidas NO acreditan todavía dos minutos para el trabajo completo.
Evidencia privada: `tmp/jobs/precompute-performance-20261010/`.

Durante esta tarea el usuario detectó que cambiar K en el mapa no disparaba
la comparación al pulsar Workers. Causa confirmada: el formulario nativo no
envía la cabecera de dispositivo del mapa y caía en K del add-on. Corrección
implementada: el botón y el runner reúnen la K predeterminada y las preferencias
persistidas activas, muestran K requeridas/preparadas/pendientes y preparan
solo las comparaciones que falten, con una sola generación histórica. Se
mantiene el límite contractual de ocho K distintas y rechazo previo a encolar.
Los clics del mapa y guardar ajustes siguen sin iniciar trabajos. Contrato
multi-K exige worker actualizado. Compatibilidad probada con fuentes HEAD reales,
Builder/Workspace y datos sintéticos: 16 perfiles/contratos V2–V6, 48 filas runtime,
matriz y predicciones idénticas; SQLite reutiliza 2/2 unidades y un modelo con
cero nuevos ajustes. Alias sólo para SHA exacto del módulo revisado; otros
cambios siguen invalidando. Se mantiene soporte del contrato escalar de HA
0.2.335 para ese productor exacto; hashes desconocidos se rechazan.
194 pruebas de precálculo/runtime/worker y 70 de selección/compatibilidad pasan.
HA/worker locales reconstruidos y recreados desde el código candidato. Paridad
efectiva: 11 archivos relevantes de HA y ocho del worker coinciden; configuración,
coordinadores, recursos y archivos privados conservan sus huellas. Worker sano,
ambos turnos libres, capacidades históricas v2 y v3, cachés válidas. Navegador
local verificado en 1600/375/320 px: K visibles, desplegables y teclado correctos,
sin desbordamiento ni envío de formularios/trabajos. Recibos en
`tmp/jobs/precompute-performance-20261010/local-verification.json` y `browser.json`.
El usuario lanzó Selección y comparación (K 4→3→2), confirmó rapidez y lanzó
el precálculo local `worker_job_n_bieLDCRx9v`. Auditoría posterior de archivos
persistidos: completo, revisión 77, 167 s totales = 5 s de cola + 162 s de
ejecución. Cálculo 150,626 s, publicación HA local 4,009 s y activación worker
4,718 s. Validación completa del SQLite y cobertura exacta correctas: 10 especies,
65 áreas distintas, 141 pares especie/área × 7 días (10–16/10/2026) = 987 celdas,
sin ausencias; 896 miembros operativos y 1.134 consultas mediante 228 respuestas
distintas. HA y copia del coordinador local en worker coinciden en SHA-256
`0b4f27f447f6b64a04873f9488ecc7860048fa38bac9e8ef0b8704def4b555ee`.
Evidencia: `tmp/jobs/precompute-performance-20261010/local-complete-audit.json`
y `local-complete-artifact-metadata-metrics.json`. Sin relanzar trabajos.
El anterior artefacto de HA real tiene los mismos recuentos; su preparación
multiversión acumulada era 432,031 s frente a 68,251 s ahora. Las generaciones
instaladas y el coordinador difieren entre ambas instalaciones: no es una
comparación estricta con entradas idénticas ni acredita esos tiempos en RPi4.
Quedan 47 s para el objetivo de dos minutos. El usuario acepta el resultado y
autoriza la release 0.2.336, que contiene la corrección de K para HA. Instalación
en HA real pendiente; el worker actualizado conserva compatibilidad escalar.

Consulta del usuario sobre 11m47s de selección/comparación en HA real: la captura
indica 10m52s de cola y el log del worker confirma 55,981 s de ejecución del
trabajo `worker_job_5zcM2AC9Ucqe7Vjx`, tras el precálculo
`worker_job_LdHHuOWz4hJo`. No confundir duración total con tiempo de cálculo.

## Release HA 0.2.335 · publicada, pendiente de instalar en HA real

El usuario autorizó publicar tras la validación local del cambio de referencia.
Smoke correcto: 2.106 pruebas, 55 omitidas, sin fallos. Verificación de código
efectivo previa al bump: 251 archivos de HA y 150 del worker coinciden.
GHCR: tags `0.2.335` y `latest`, digest `addc77ee…`, manifests amd64/arm64.
Ver [informe de release](reports/release-ha-0.2.335-2026-10-10.md).
La instalación y prueba de HA real las realiza el usuario. El worker local ya
contiene el contrato compatible; no se publica otra versión del worker ni se
cambian sus coordinadores. No hace falta repetir una preparación compatible.

## Referencia actual para selección/Iₖ del mapa · incluida en 0.2.335

Usuario autorizó usar la última preparación disponible tanto en modo histórico
como en «Comprobar predicción». El IFF mantiene la fecha y meteorología
consultadas; A/B/C/D y sus Iₖ usan el corte de la preparación. Se conservan los
acumulados por fecha, su generación y sus lectores. No se ha cambiado ni
relanzado el proceso de preparación ni entrenamientos. Véase
[especificación](mushrooms/prediction-map-specification-es.md).
Cambio publicado en 0.2.335. HA local y worker reconstruidos
y recreados; paridad efectiva comprobada, coordinadores y configuración intactos.
87 pruebas dirigidas y navegador escritorio/móvil correctos. Consulta real local
de Olvan, 17/09/2019: IFF habitual idéntico con/sin Competing selection (54/100),
cinco Iₖ actuales, referencia 10/10/2026 y 90 visitas comparables. Evidencia y
observaciones privadas conservadas; huella del proceso de preparación sin cambios.
[Resultado](reports/competing-current-reference-local-2026-10-10.md).

## Release HA 0.2.334 · publicación anterior

El usuario confirmó que funciona en local y autorizó publicar. Smoke completo
correcto: 2.105 pruebas, 55 omitidas, sin fallos. La imagen 0.2.334 y `latest`
están verificadas en GHCR con digest `c3f5047c…` y manifests amd64/arm64.
Ver [informe de release](reports/release-ha-0.2.334-2026-10-10.md).
Incluye Competing selection, selección/comparación reutilizable, Iₖ histórico,
mejora del mantenimiento de observaciones y correcciones de vídeo/progreso.
El usuario instala y prueba en HA real; no se ha actualizado HA real desde aquí.
SQLite y optimización del precálculo semanal siguen pendientes independientes.

## Iₖ por fecha, reutilización e interfaz de observaciones · activados en local

El usuario autorizó acumulados compactos por fecha para mostrar los Iₖ de
comparación en modo histórico, dentro del mismo trabajo de selección y
comparación. Implementados en el worktree; sin tareas desde los clics del mapa.
Revisión posterior detectó y corrigió la búsqueda de cachés binarias como si
fueran antiguas claves JSON. Prueba de migración: 3/3 unidades reutilizadas,
ninguna recalculada; 97 pruebas dirigidas distintas correctas. Ver
[informe y límites](reports/competing-history-local-2026-10-10.md).

El usuario avisó de que terminó el trabajo del worker. Se comprobó `idle` en
ambas colas y se recrearon HA local y worker con las imágenes preparadas.
Paridad efectiva comprobada: 12 archivos en HA y ocho en worker coinciden con
el worktree; revisión `02c86d9f…`. Coordinadores persistidos y sus hashes
idénticos antes/después: principal `http://100.111.77.48:8100` y adicional
`http://rainmapper-ha-ui:8100`. Configuración efectiva conservada. Worker sano,
libre y con cachés válidas tras arrancar. Evidencia en
`tmp/jobs/local-activation-20261010/`. Tras la prueba del usuario se auditó el
trabajo `worker_job_WW5hw8Pr9iGqKNiM`: completo en 53,926 s, resultado activado,
control `ready`, recibo coincidente y acumulados históricos válidos para ambas
especies. Validación local aceptada; publicada HA 0.2.334, instalación real pendiente.

El usuario pidió revisar después el diagnóstico de `audit_database_ui_performance`.
Revisión terminada: código y huellas actuales contrastados con
`tmp/jobs/database-ui-performance-20261010/diagnosis.md`. Se confirma trabajo
repetido en el render del listado (30 lecturas de setales, 25 editores por página);
el ensayo aislado 602→65 ms en Mac no acredita la latencia del clic ni de la RPi4.
El usuario autorizó esa corrección y medir antes de decidir SQLite. Implementada:
una lectura de setales por render y editores cargados al abrirlos, con conservación
del borrador de campos. Cinco parejas medidas con 561 observaciones: mediana
708→45 ms al preparar la sección; HTML 2,45→0,98 MB. 31 pruebas dirigidas y
dos pruebas de navegador aisladas correctas. Imagen HA local reconstruida y
ahora activada: navegador contra HA local abrió el editor bajo demanda y
recibió la vista previa GIS/DEM correctamente, sin guardar cambios. Ver
[informe y límites](reports/observation-ui-performance-2026-10-10.md).
SQLite continúa pendiente de decisión; no hay migración ni cambios de datos.
El agente de precálculo es una investigación independiente; no se ha aplicado
ninguna optimización del precálculo en esta activación.

## Organización local autorizada el 10/10

El usuario pidió separar datos operativos, runtime, cachés, evidencias y temporales,
manteniendo las rutas hardcodeadas funcionales. Ver
[organización local](local-workspace-layout-es.md). Se han trasladado las pruebas
a `local/evidence/`, el runtime a `local/runtime/mushroom-lab/` y los SQLite/Parquet
de las pruebas de rendimiento a `local/cache/competing-speed-20261006/`.
Las rutas antiguas tienen accesos de compatibilidad; no seguirlos ni borrarlos
con una limpieza genérica de `tmp/`. Nuevos temporales en `tmp/jobs/`.
Originales, observaciones, estado operativo y fuentes archivadas se conservan.
No se ha activado borrado automático. Índice privado: `local/evidence/INDEX.md`;
recibos: `local/evidence/2026-10-10-local-organization/`.

Validación: 13.856 archivos inventariados conservados, 43 scripts auxiliares con
rutas corregidas y originales guardados, 23 pruebas dirigidas correctas y 439
accesos comprobados desde HA local. HA local recreado sólo para aplicar montajes,
misma imagen y configuración; worker sin reinicio y coordinadores conservados.
[Informe](reports/local-workspace-organization-2026-10-10.md). El usuario puede
lanzar Selección y comparación; no reiniciar servicios durante su trabajo.

La propuesta de comparación para cualquier K quedó aplazada expresamente:
se mantiene el trabajo de selección/comparación por K con reutilización.
El usuario lanza los trabajos; no reabrir optimización ni estudios cerrados.

## Prioridad activa: comprobación funcional de selección y comparación

El usuario exige **≤10 minutos para 5.000 observaciones**, optimizando primero.
Autoriza continuar autónomamente y utilizar hasta **4 núcleos y 8 GB**, sin
acciones destructivas. No cambiar destinos del worker ni publicar releases.
Trabajo **en curso, instalado sólo en local**; meta completa todavía no acreditada.

Actualización del usuario 07/10: considera asumible superar en 40 segundos el
objetivo para 5.000 registros y pide confirmar el funcionamiento antes de probar.
No seguir optimizando sólo para recortar esos 40 segundos. La medición continúa
siendo 639,737 s con muestra sintética de dos especies; no convertirla en prueba
de todas las especies. No hay autorización nueva de release ni de trabajo
operativo. Código efectivo revalidado en HA local y worker: misma revisión
`b2e5c0f4bda4c687bc0b5e68a211d869ab2ec732d849b3ad8d309fc720bae581`.

Alcance confirmado: TARGETS limita la preparación a aereus/caesarea. El mapa
conserva la predicción habitual y añade A/B/C/D con Competing selection activo.
La comparación común incluye habitual y sus I_k; el verde marca mayor I_k de
comparación (incluidos empates), sin sustituir el IFF principal. Un K personal
sin comparación preparada requiere ejecutar Selección y comparación desde el
mismo dispositivo: reutiliza el historial y prepara esa comparación. Ni pulsar
un punto ni guardar ajustes lanza ese trabajo. Sin preferencia se hereda el K
del add-on. Generalizar especies requiere ampliar alcance y validar modelos y
observaciones, no rehacer el motor genérico.

Última revisión de recibos: 07/10 14:39 Madrid. Evidencia privada en
`tmp/competing-speed-20261006/`; no extrapolar a otro código/imagen.

- Comparación de 184 visitas reales: **408,847 → 8,342 s**, salida exacta con
  probabilidades históricas ya guardadas. No incluye preparación ni selección.
- `selection-ready-process-5000`: selección fría **348,377 s**, preparación y
  comparación excluidas. **584/584 unidades numéricas completas exactas** frente
  a `complete-target-5000-binary-batched`; evidencia agregada también idéntica
  salvo fecha de actualización. Cuatro procesos, cola acotada de 16; recoge
  resultados terminados sin quedar bloqueada por el primero. Pico 4.629.532.672 B.
- `parallel-bulk-cold-5000`: comparación **152,437 s**, entradas/paneles fríos y
  modelos previos inmutables; cuatro particiones, pico 3.212.554.240 B.
  `parity-area-reuse.json` confirma **salida completa exacta** del resolver
  original: 35 paquetes servidos desde visitas equivalentes del mismo modelo,
  especie, área, fecha y horizonte. La primera comprobación buscaba sólo el ID
  original y excluía 11 visitas; sus archivos se conservan.
- Estas cifras son fases aisladas, **no acreditan ≤600 s completos**. La muestra
  de 5.000 es sintética, réplicas de 184 visitas de aereus/caesarea con fechas
  desplazadas; no son 5.000 visitas independientes ni todas las especies.

Última prueba completa `production-cold-5000-ready-parallel`: preparación
155,958 s, selección a 489,725 s; fallo SQLite a 581,027 s durante comparación.
**584/584 unidades exactas**. Corregida fusión prematura de particiones: ahora
se espera al cierre de todos los lectores. Comparación fría posterior privada
`production-striped-cold-5000`: 144,246 s, salida completa exacta, sin error,
pico 3.326.726.144 B. No es un trabajo completo de diez minutos.

**Última prueba completa (14:39 Madrid):** `final-image-cold-5000` termina
en **639,737 s (10 min 40 s)** desde imagen reconstruida. Preparación 143,828 s,
selección 340,382 s, resumen/comparación/publicación 155,528 s. **No cumple
≤600 s**, faltan 39,737 s y margen. Comparación completa exacta y **584/584
unidades numéricas completas iguales**. 4 CPU/8 GiB; pico 4,715 GiB, swap 0.
Revisión antes/después idéntica. Worker operativo idle en ambos carriles.

El usuario pidió dejar terminar y evaluar este resultado. No se ha modificado
código durante la prueba. Hay un borrador privado sin ejecutar de proyección
de matrices de prueba (`test_matrix_projection_draft.py`); no integrado ni
medido. La evaluación actual NO prueba el límite de diez minutos ni todas las
especies; muestra sintética de dos especies, datos fuente conservados.

Integrado en el worktree: selección con procesos
acotados y restauración del orden original mediante cabeceras SQLite temporales;
continuaciones del resolver semanal; comparación por lotes, estadísticas
vectorizadas exactas, cachés temporales limitadas de series/variables; agregación
meteorológica por área reutilizable; sufijos de reserva hídrica compartidos sólo
cuando coinciden exactamente; comparación en cuatro particiones y publicación
de paneles por el padre. Contratos operativos, horizontes, candidatos y ventanas
históricas conservados. Límite de paneles duraderos 96 MiB, modelos 64 MiB,
auditoría comprimida 8 MiB; matrices pendientes de ajuste hasta 1 GiB.

Validación integrada: 100 pruebas de preparación/selección/comparación/paquetes
pasan; otros 110 casos de mapa/modelos/backend pasan, con un nombre de módulo
hídrico erróneo en la invocación corregido con sus 8 pruebas reales, que pasan.
El control dentro de imagen detectó `mushroom_weather_series.py` ausente del
Dockerfile del worker; corregido y reconstruido. Siete pruebas de empaquetado
pasan después. Paridad efectiva: 74 archivos y revisión del procedimiento
`b2e5c0f4bda4c687bc0b5e68a211d869ab2ec732d849b3ad8d309fc720bae581`,
idéntica en repo/HA local/worker. HA local responde HTTP 200.

`RAINMAPPER_HISTORY_FIT_WORKERS` por defecto 1, opt-in 2–4; BLAS a un hilo.
Compose local **aplicado**: cuatro CPU, memoria 8589934592 bytes y swap adicional
0. HA local y worker reconstruidos/recreados; coordinadores primario
`http://100.111.77.48:8100` y secundario `http://rainmapper-ha-ui:8100` conservados,
archivos de configuración con las mismas huellas antes/después.
Usuario lanza trabajos operativos. JSON canónico sin migrar; latencia de UI de
observaciones pendiente de medición específica. No atribuir el cuello de botella
al formato de la BBDD sin medirlo.

Detalle y recibos anteriores: [informe de rendimiento](reports/competing-performance-2026-10-06.md).
Los apartados siguientes describen despliegues anteriores, no esta revisión.

## Vídeo de observación y cierre del progreso: corregidos en HA local

El MP4 aportado por el usuario fallaba en FFmpeg con `Invalid color space`:
H.264 con matriz de color reservada. Se añade un único reintento con copia de
paquetes y normalización de esa cabecera, conservando el original. La fecha
EXIF cero y la ausencia de GPS son independientes: se puede adjuntar mediante
«Cargar imagen/vídeo», sin importar metadatos. El guardado asíncrono comunica
ahora los fallos con HTTP 422 y mensaje visible, conservando el formulario.

El detalle de progreso muestra **Cerrar también durante la ejecución**; cerrar
sólo retira la ventana y detiene sus consultas de progreso, sin cancelar el trabajo.
HA local reconstruido/recreado y paridad efectiva de `web_server.py` comprobada;
worker no reiniciado. Prueba con el vídeo real y una copia aislada de la observación:
guardado correcto, sin DEM y sin modificar fecha/coordenadas/microárea.
Navegador aprobado para error visible y cierre del progreso; observación real
sin escrituras por estas pruebas. 353 pruebas de autenticación aprobadas y cinco
dirigidas aprobadas tras el último cambio. Sin release.

**Pendiente independiente:** cambiar coordenadas fuera de la cobertura DEM sigue
requiriendo revisar el flujo de ubicación. No se ha cambiado ese comportamiento.
La ejecución y recepción reales de selección/comparación siguen pendientes de
validación; esta corrección de interfaz no las acredita ni las interrumpe.
[Informe y recibos](reports/observation-video-local-2026-10-06.md).

## En curso: comparación común de Habitual y A/B/C/D, disponible en HA local

**Última revisión: optimización y cambio de panel terminados en HA local.**
El usuario canceló `worker_job_ZFACRJa4VG_0ze9s`; el worker confirmó cancelación
el 06/10 a las 19:34:03 UTC. Se reutilizan bases meteorológicas/ET₀, variables
persistidas por entradas consumidas y unidades compatibles del productor anterior
sólo con igualdad exacta de datos y semanas. Inferencia por lotes y progreso
global sin retrocesos entre familias. El mismo trabajo sigue preparando selección
y comparación; los clics del mapa no lanzan trabajos.
Workers: **Selección y comparación**, desplegable cerrado por defecto.
62 pruebas Mac / 37 en imagen worker aprobadas; navegador a 320/375/1600 px.
HA y worker reconstruidos/recreados, paridad efectiva 32/25 archivos, HTTP 200,
ambas vías libres y URLs/huellas de coordinadores conservadas. Revisión común:
`a36878ced3018d2d38432befcd06105f9947e684de8770c75725bb64fd93a4e1`.
Antes de recrear el worker se esperó la finalización del precálculo que ya estaba
atendiendo para el coordinador principal; no se lanzó ni canceló ese trabajo.
El usuario lanza ahora la selección y comparación. **Pendiente medir ejecución
real y validar el resumen común recibido**; no prometer duración a partir de la
microprueba sintética. Fuentes, límites y recibos:
[informe de reutilización](reports/competing-reuse-local-2026-10-06.md).

**Antecedentes de esta jornada (snapshots, no estado actual del worker):**
El trabajo cancelado superó tres horas; tenía avance real, 249 paquetes de 22
unidades en una lectura y ninguna generación común publicada. Se detectó
preparación repetida de meteorología/variables y progreso local mostrado como
si fuera global. Las verificaciones anteriores siguientes corresponden a las
revisiones previas y no sustituyen la validación indicada arriba.

Último acuerdo del usuario: conservar A/B/C/D como reglas que eligen modelos
por mayor Iₖ, añadir Iₖ de la selección habitual y comparar las cinco reglas
sobre las mismas visitas históricas. Recuadrar en verde la mayor nota común,
incluidos empates. La predicción principal sigue siendo la habitual. No volver
a confundir A con Habitual ni el Iₖ de selección con el Iₖ de comparación.

Estado comprobado en esta intervención:
- Implementación nueva de evaluación temporal común y semanas completas en el
  worker; cada visita pesa uno, horizontes 1/7; ausencias técnicas compartidas,
  abstenciones conservadas. Ventanas A 12 meses, B/C 24, D todo el histórico.
  Habitual reconstruye el orden nativo con evidencia anterior, sin usar Iₖ
  para elegir. Los ajustes históricos usan años anteriores al caso evaluado.
- Dos niveles privados de caché: unidades de validación y semanas completas.
  Cambiar sólo K reutiliza probabilidades y vuelve a resolver elecciones y
  métricas sin ajustar modelos. HA conserva hasta ocho resúmenes K de la misma
  generación de entradas. **Corrección posterior solicitada por el usuario:**
  el mapa sólo lee esos resultados; ningún clic ni cambio de ajustes dispara
  preparación histórica. El runner conserva las actualizaciones por entradas.
  El botón explícito de Workers usa la K personal del dispositivo o la heredada
  del add-on. La comparación sigue siendo la última fase del mismo trabajo.
- Ficha compacta Habitual + A/B/C/D con Iₖ de comparación, verde máximo/empates,
  detalles plegados de soporte y notas de selección. Defaults false/K=4 y
  preferencias personales conservados. Prueba de navegador completa aprobada,
  incluidos 320/390 px y verificaciones de que la ficha entra en pantalla.
- 83 pruebas dirigidas pasaron; 49 pasaron dentro de la nueva imagen worker,
  aislada de red/datos reales. Suite conjunta de autenticación/backend: 359
  pruebas, con una repetida y aprobada usando PYTHONPATH=tests por un import
  antiguo. Recibos y alcance exacto en el informe enlazado abajo.
- HA local y worker reconstruidos/recreados desde el código actual; paridad
  efectiva 30 archivos HA / 23 worker, sin diferencias. HA local HTTP 200;
  worker idle en esa comprobación inicial, antes del trabajo descrito abajo.
  Huella del procedimiento igual en Mac/HA/worker:
  `ce683820f90f3e87cb2e8cdee471ba4ff466acbd6f4bab468d79555965b8cdd5`.
- URLs y huellas persistidas de ambos coordinadores conservadas exactamente:
  principal `http://100.111.77.48:8100`, adicional `http://rainmapper-ha-ui:8100`.
- Planificación de entradas leída sin evaluar: 87 familias, 311 candidatos,
  184 visitas de las dos especies antes de elegibilidad; 317.608 celdas previstas,
  81.307.648 bytes estimados frente a límite SQLite de semanas 96 MiB. No son
  duración ni tamaño reales del cálculo. Ampliar especies requiere particionar
  y medir, no elevar límites ni prometer incrementalidad completa.
- El artefacto anterior ya existe en HA local: 573.310 bytes, corte 05/10,
  169 casos/275 candidatos/25.923 celdas. Esto corrige el contexto obsoleto que
  decía que todos los intentos habían fallado. **Ese artefacto todavía no tiene
  la nueva comparación común**; no acredita este nuevo recorrido.

Primera consulta real del usuario tras actualizar: la ficha muestra notas «—»
y comparación pendiente. Comprobado que solicitó automáticamente el trabajo
`worker_job_ZFACRJa4VG_0ze9s`, origen `map`, iniciado el 06/10 a las 16:16:08 UTC;
worker con carril de fondo ocupado por ese trabajo. Primera lectura: 10 %, V3
fixed, meteorología 105/111. No se lanzó otro trabajo ni se anunció finalización.
Última lectura: 33 %, V5 ventanas meteorológicas 800/1487, 259 s transcurridos;
seguía en ejecución. Recibo en
`tmp/competing-comparison-local-20261006/first-job-status.json`.
**Ese disparo desde el mapa fue rechazado por el usuario y retirado después.**
No se canceló ni reinició el trabajo existente. La corrección afecta sólo a HA;
no cambia el protocolo/huella ni invalida la preparación en curso.
Corrección desplegada y verificada en HA local: 17 pruebas dirigidas, luego ocho
de backend tras añadir herencia de K al botón de Workers; doce consultas con
distintos puntos/K no solicitan ningún trabajo histórico. HA reconstruido/
recreado, HTTP 200 y paridad 30/23 sin diferencias. Worker no reiniciado; el
trabajo anterior sigue activo. Última fase V3, semanas completas 15/17; la
telemetría de esa fase vuelve al 10 %, defecto de progreso pendiente, no reinicio.

Pendiente: lanzar el trabajo optimizado y medir primera preparación, cambio sólo
K, cobertura/ausencias, recepción/activación y ficha con resultados reales.
Codex no ha lanzado trabajos operativos ni estudios, entrenamiento operativo o
precálculo. No afirmar validado el recorrido con datos reales. La preparación
inicial del nuevo contrato necesita semanas históricas que el resumen anterior
no guardaba, y puede requerir ajustes aislados de validación nuevos. Su duración
no se conoce todavía; no confundirla con los 15,672 s de planificación.

Límite científico: comparación retrospectiva de reglas actuales usando el
contexto de áreas de visitas; no valida el punto pulsado ni reconstruye exactamente
las instalaciones históricas. Verde significa máximo descriptivo; no hay mínimo
de utilidad/evidencia acordado ni superioridad demostrada. Alcance aún aereus y
caesarea. Las familias compartidas pueden depender de otras especies, de modo
que invalidación por dependencias no equivale a aislamiento absoluto por especie.

[Especificación vigente](mushrooms/prediction-map-specification-es.md) ·
[Informe del 06/10](reports/competing-comparison-local-2026-10-06.md) ·
[Antecedentes y fallos corregidos del 05/10](reports/competing-selection-local-2026-10-05.md).
Sin release, commit ni push. Conservar fuentes privadas y cambios previos del
worktree. No abrir disco, WhatsApp, geografía ni release; no cambiar coordinadores.
Informar al usuario aproximadamente cada minuto: ha señalado repetidamente los
silencios durante esta implementación.

## Continuidad científica: estudio D completado el 05/10

El usuario delegó diseño y ejecución y pidió un agente. Estudio D terminado;
no quedan lotes en marcha. **No repetir los cálculos ni lanzar otro agente por
este cierre.** Se incorporaron 40 de las 42 observaciones objetivo anteriores
a 2022 mediante 294 ajustes históricos aislados. La primera observación de cada
especie se conserva como entrenamiento inicial: no tiene prevalencia previa para
el ranking nativo. No se eliminaron observaciones antiguas por conveniencia.

[Informe final D](agents/prediction-model-selection/resultados-D-2026-10-05.md).
D conserva selección semanal nativa, umbral 0,60, filtros y modelos finales;
amplía el histórico del ranking. I4 con k=4 deriva de la equivalencia expresada
por el usuario. Fórmula y mínimos se adoptaron como decisiones de diseño
delegadas antes de conocer D, no como reglas operativas.

| Especie | Precisión D | Detección D | Consejos ponderados D | I4 D | I4 B |
|---|---:|---:|---:|---:|---:|
| Aereus | 66,4% | 30,6% | 16,57 | −31,35 | −54,76 |
| Caesarea | 73,3% | 48,2% | 23,00 | −22,04 | +9,80 |

Ninguna alternativa supera conjuntamente utilidad y estabilidad. B de caesarea
conserva señal conjunta, pero se abstiene en toda la campaña 2025 y su intervalo
de I4 es amplio. D no emite consejos favorables de caesarea en 2026. No hay
promoción ni conclusión de que uno/dos años sean óptimos; tampoco justifica borrar
historia. Resultados retrospectivos exploratorios, sin confirmación independiente.

El snapshot meteorológico antiguo ya no estaba disponible. Para comparar con
igualdad se hizo un contraste nuevo A/B/C/D con meteorología local actual común,
la cohorte original de 116 casos, mismos modelos y geografía preparada. Los
resultados cerrados permanecen intactos. No cambió ninguna decisión A/B/C frente
a las guardadas; cambiaron sólo una probabilidad A y otra B en 2026. Aereus B
2025/26 usa fallback diario y D familia semanal: el efecto total incluye su
preparación nativa distinta, documentada antes del reintento; no mide historia
con matrices fijas. Caesarea y 2024 no entran en esa rama.

Ocho pruebas dirigidas y guardas pasadas; verificados 763 archivos de entrada,
294 ajustes sin fuga temporal/episodios y 812 emisiones por método. Revisión raíz:
19 huellas actuales y recálculo de utilidad/precisión/detección desde las emisiones
guardadas, sin volver a inferir ni entrenar. Evidencia privada:
`tmp/prediction-model-selection/D-2026-10-05/{closure.json,verification.json,root-review.json,analysis-common/results.json}`.
Unos 21 min 22 s de cálculo, pico 653 MiB RSS y unas 144 MiB de salidas.

La supervisión final funcionó dentro del sandbox midiendo el propio proceso;
no necesitó ps. Una antigua petición de permiso llegó después del cierre: la
sonda obsoleta fue rechazada por el guard antes de ejecutar su payload, añadió
0,52 s y no cambió los resultados; consta en `root-review.json`. No repetirla.
No hubo operaciones en HA, worker/coordinadores, descargas, precálculo,
regeneración geográfica, limpiezas o release. Próximo paso: comentar resultados
y decidir evidencia futura, sin ejecución ni promoción automática.

## Release actual: HA 0.2.333 instalada y funcionando, confirmada por el usuario

El usuario autorizó publicar con «publicamos version de HA» después de la
validación local de la medición por recorridos y su convivencia con las consultas.
GHCR verificado: `0.2.333` y `latest`, mismo digest
`sha256:3980114db78a60a0d44a720d51773af7f311607567e20f43ad9455fb18630832`,
con manifests `linux/amd64` y `linux/arm64`.

- Medición A→B→C… en 2D/3D, línea provisional, vértices arrastrables, Deshacer y
  Nueva. Pulsar el último punto termina/reanuda. Icono después de norte y antes
  de Créditos; sin permiso específico.
- Distancia horizontal, relieve aproximado y desniveles acumulados; cálculo
  Mapzen/Terrarium acotado e independiente de la exageración visual.
- Panel compacto ES/CA/EN, ayuda plegada y acciones en una fila; móvil comprobado
  a 320, 360 y 390 px. Un recorrido terminado conserva sus resultados y permite
  consultar predicciones, estaciones e información del terreno.
- HA local reconstruida/recreada y ocho huellas revalidadas contra el código
  aceptado. Navegador completo correcto y smoke definitivo: 1.911 pruebas,
  55 omitidas. Después sólo bump/cache-busters y documentación.
- Una publicación supervisada, salida 0 y GHCR verificado. Limpiezas Docker ya
  autorizadas: retirada de etiqueta local 0.2.332 y 5,796 GB de caché recuperados.
  Fuentes, observaciones privadas y volúmenes conservados.

[Informe y evidencias](reports/release-ha-0.2.333-2026-10-04.md).
El usuario confirmó el 04/10 «instalada 0.2.333 y funcionando». Instalación y
funcionamiento en HA real confirmados por el usuario; release cerrada.
Codex no ha instalado ni reiniciado HA real ni operado sobre el worker/coordinador.
No repetir publicación, entrenamiento ni precálculo.
El estudio D posterior adoptó I4 y mínimos por delegación del usuario; véase el
cierre científico superior. No se modifica la operación instalada.

## Release anterior: HA 0.2.332 instalada y funcionando, confirmada por el usuario

El usuario confirmó que la capa de áreas y microáreas funciona en HA local y
autorizó publicar con «pues publicamos version de HA». GHCR verificado el 04/10:
`0.2.332` y `latest`, mismo digest
`sha256:6e48babc0868d84a76509bb95cd0418ff778d8926f59df8f7e74b623703717b2`,
con manifests `linux/amd64` y `linux/arm64`.

Botón debajo de Observaciones; capa independiente y compatible con las demás.
Comparte `can_use_observations_map` en interfaz y API; sólo carga geometrías y
nombres al activarse. HA local reconstruida/recreada y aceptada; seis huellas
revalidadas antes del bump. 28 pruebas dirigidas, navegador escritorio/móvil y
smoke de release correcto: 1.911 pruebas, 55 omitidas. Después sólo cambiaron
versiones/cache-busters y documentación. Sin operaciones sobre el worker.

El usuario autorizó expresamente las dos limpiezas automáticas de Docker del
script de publicación. Se retiró la etiqueta local HA 0.2.331 y Buildx informó
de 6,486 GB recuperados. Esa autorización no amplía la auditoría de disco ni
permite retirar fuentes, datos privados o carpetas históricas.

[Informe y evidencias](reports/release-ha-0.2.332-2026-10-04.md).
El usuario confirmó el 04/10 «instalada y funcionando» tras publicar 0.2.332.
Instalación y funcionamiento en HA real confirmados por el usuario; Codex no ha
instalado ni reiniciado HA real. Release cerrada; no repetir publicación ni
lanzar trabajos operativos.
La discusión científica sigue pendiente, sin nueva métrica aprobada.

## Contexto de continuidad anterior a la publicación

Leer [codex-start-here.md](codex-start-here.md) y este documento basta para
continuar; [todo.md](todo.md) sólo amplía pendientes. **La revisión de utilidad
de las predicciones queda guardada para retomarla cuando el usuario lo pida.**
Los dos estudios están completados. No lanzar otro agente, experimentos,
entrenamientos, precálculos, limpiezas ni despliegues adicionales.
La auditoría del disco está detenida por decisión del usuario.

## Actualización posterior: capa de áreas conocidas · HA local · 04/10

- Usuario pidió y confirmó un botón con icono de área debajo de Observaciones,
  compatible con las demás capas, para mostrar áreas y microáreas conocidas.
  Implementado en HA local: contornos violetas/naranjas, relleno suave y nombres
  al acercarse. Comparte el permiso de Observaciones, confirmado por el usuario.
  [Especificación](mushrooms/prediction-map-specification-es.md).
- Lectura privada de `mushroom_known_sites.json` mediante
  `/api/mushrooms/prediction-map/known-sites`, sin trabajos ni modificaciones de
  las fichas. 72 áreas + 113 microáreas, 10.371 vértices, respuesta 411.808 bytes.
  Nueva implementación en `rainmapper_core/mushroom_map_known_sites.py` y
  `rainmapper_core/viewers/prediction-map/known-sites-mode.{js,css}`.
- Validación: 28 pruebas dirigidas, navegador compartido completo con casos de
  convivencia/cancelación/cambio de estilo/permisos y capturas escritorio/móvil.
  HA local reconstruida/recreada y SHA-256 coincidente en seis archivos; lectura
  del handler en el contenedor con los datos locales, HTTP sin sesión 401 y JS 200.
  Evidencia privada: `tmp/known-sites-map-20261004/validation.json`.
- El usuario probó HA local y confirmó que funciona; posteriormente autorizó la
  publicación 0.2.332 descrita arriba. Sin operación sobre el worker, entrenamiento
  ni precálculo. Cambios previos y archivos privados conservados. El estado Git
  histórico del cierre inferior precede a esta implementación y no describe el
  diff actual.
- Antes se diagnosticó el ejemplo Maçanet (41.77026, 2.68110): el lector local
  devuelve 10,2013 mm para el 03/10; la API original WU IMASSA32 confirmó 11,94 mm
  el 03/10 y 121,41 mm el 04/10. La ficha corta en el último día completo y excluye
  el día en curso. Usuario aceptó la explicación de lluvia de madrugada. No se
  cambió ese corte ni el SMI; incluir hoy provisional no está aprobado. IMAANE8
  aporta cero desde la fuente y 29,35 % del peso en ese punto, sin diagnóstico
  confirmado de avería ni modificación de la estación.

## Punto de continuidad: utilidad para aereus y caesarea

**Preferencia expresa:** el usuario prefiere 10 consejos favorables con nueve
aciertos a 40 con 30, siempre que haya una cantidad razonable de recomendaciones.
Evitar falsos favorables pesa más que detectar todas las oportunidades; no
aceptar «siempre desfavorable» como solución. El ejemplo no fija una precisión
mínima del 90%, un coste definitivo ni un número mínimo de consejos.

Propuesta exploratoria: `I_k = 100 × (TP − k × FP) / P`, con `P` = **todos los
favorables reales**, incluidos los no detectados. Sustituye en esta discusión
el denominador inicial de todos los casos; no se divide entre los consejos
favorables. Son puntos de utilidad, no porcentajes de acierto. Máximo 100,
abstención total 0 si hay positivos, y NE si `P = 0`; puede bajar de −100.
TP y FP son promedios entre siete horizontes, con peso total 1 por observación.

Valores sobre los resultados guardados del estudio de **selección del ganador**:

| Especie | Variante | k = 2 | k = 3 | k = 4 |
|---|---|---:|---:|---:|
| Caesarea | A | −12,65 | −31,43 | −50,20 |
| Caesarea | B | +23,67 | +16,73 | +9,80 |
| Caesarea | C | +17,55 | −2,45 | −22,45 |
| Aereus | A | +5,95 | −15,48 | −36,90 |
| Aereus | B | −9,52 | −32,14 | −54,76 |
| Aereus | C | −2,78 | −27,38 | −51,98 |

Denominadores: caesarea 35 favorables reales de 61 casos; aereus 36 de 55.
Los tres pesos se presentaron inicialmente como ilustrativos. El 05/10 el usuario
respondió **«Me resultan equivalentes»** al comparar, sobre las mismas
oportunidades, **10 consejos con 9 aciertos y 1 fallo** frente a **20 consejos con
17 aciertos y 3 fallos**. En esta fórmula, `9 − k = 17 − 3k` implica **k=4**:
un falso favorable resta cuatro aciertos. Es una equivalencia expresada por el
usuario y su traducción condicional a la fórmula; no aprueba por sí sola la
fórmula completa ni fija mínimos de índice, actividad o evidencia.
Sobre los mismos casos, respetar el primer ejemplo del usuario requiere
`9 − k > 30 − 10k`, es decir, `k > 7/3 ≈ 2,33`; k=2 invierte esa preferencia.
Un índice positivo requiere precisión mayor que `k/(1+k)`; eso no garantiza
cantidad suficiente ni fiabilidad. Un único acierto sobre una única oportunidad
puede dar 100 puntos sin constituir evidencia suficiente.

Estos eran los pendientes antes de D: fórmula, mínimo de índice,
cantidad/frecuencia de consejos, soporte independiente, incertidumbre y estabilidad
por campaña. La delegación posterior permitió cerrar su protocolo exploratorio;
el resultado está arriba. Distinguir
precisión `TP/(TP+FP)`, detección `TP/P`, frecuencia favorable `(TP+FP)/N` y
cobertura total (consejos favorables o desfavorables). El informe conserva ejemplos,
denominadores y límites; TODO también guarda k=2/3/4. No convertir la nueva
métrica, discutida después de ver resultados, en regla predeclarada del estudio.

### Propuesta D e inventario del 05/10

**Registro del diseño y autorización ya ejecutados; estudio cerrado arriba.**

**Autorización posterior del 05/10:** el usuario indica «pues sigue adelante,
decide tu como tiene que ser el estudio y lanza el agente. me voy a trabajar en
otra cosa mientras tanto». Se ha lanzado un único agente `estudio_d_historico`
para completar D, con libertad de fijar el diseño y los mínimos antes de sus
resultados. Autoriza nuevos ajustes históricos aislados estrictamente necesarios;
no repetir los cálculos cerrados de A/B/C ni realizar cambios operativos.
No necesita nuevas descargas. El usuario pide continuar pese a sus mensajes de
seguimiento: responder brevemente e incorporar indicaciones sin cerrar el trabajo.

Guardas encargadas: un proceso de cálculo/un hilo, máximo 8 GiB RSS,
60 minutos de cálculo supervisado y 512 MiB de salidas nuevas; sellar protocolo,
cardinalidad y presupuesto antes de cálculos largos. Conservar archivos originales
y privados, sin tocar HA, worker/coordinadores, geografía, precálculo, limpieza o
release. Sin otros agentes. D mantiene k=4 como criterio primario derivado de la
equivalencia expresada; sus mínimos se identificarán como decisiones de diseño
delegadas, no como cifras elegidas literalmente por el usuario. Comparación
exploratoria: resultados conocidos de 2024–2026 no constituyen confirmación nueva.

[Protocolo D previo](agents/prediction-model-selection/protocolo-D-2026-10-05.md)
revisado antes de calcular resultados. Diseño delegado: señal útil si I4≥5,
≥10 consejos ponderados, detección≥25% y ≥5 episodios recomendados; estabilidad
separada por campaña, sin veto adicional a FP al margen de k=4. Contraste principal
D−B, mejora material≥5 puntos; intervalos por episodios, sin convertirlos en
confirmación independiente. El agente prepara sólo evidencia histórica faltante
y evaluación D; A/B/C se leen, no se vuelven a ejecutar.

El usuario propone D con todos los años disponibles y pide comenzar. Se ha
realizado únicamente un inventario de los dos estudios guardados; ninguna nueva
inferencia, ajuste, descarga ni evaluación de D. Evidencia privada:
`tmp/prediction-model-selection/inventory-d-2026-10-05.json`.

El usuario precisa que hay pocas observaciones y rechaza descartarlas «porque
sí». **D mantiene como objetivo todo el histórico evaluable, no sólo lo ya
calculado.** 2022 es el inicio de los paneles guardados, no un corte científico
aprobado. No se ha retirado ninguna observación en esta revisión. Distinguir
aprovechar un caso para entrenamiento de disponer de una predicción válida para
medir su acierto; justificar cualquier imposibilidad por año/caso y soporte
anterior, sin excluir por comodidad o falta de un cálculo ya preparado.

- La cohorte conserva aereus desde 2016 y caesarea desde 2015. Las predicciones
  de ranking guardadas cubren 2022–2025. Se comprobaron las huellas de los doce
  archivos de seis paneles, ausencia de claves duplicadas y separación temporal,
  de observaciones y episodios frente a los roles de entrenamiento declarados.
- Subconjunto ya calculado y reutilizable, sin limitar con ello D: para evaluar
  2024, evidencia 2022–2023 (igual que B);
  para 2025, 2022–2024; para 2026, 2022–2025. En este último caso hay 54
  observaciones únicas de aereus y 58 de caesarea antes de exclusiones por perfil.
  No son visitas independientes por multiplicar modelos u horizontes.
- Las 168 claves de candidatos coinciden entre cortes, pero cambian 19, 17 y 24
  configuraciones de ajuste al comparar 2024/2025, 2025/2026 y 2024/2026.
  La ampliación reutilizable sería evidencia histórica de familias/procedimientos,
  no de una configuración fija. Mantener semanal y modelos finales de A/B,
  explicitar esta diferencia y fijar procedencia sin duplicar años antes de evaluar.
- Estos estudios no guardan paneles de ranking anteriores a 2022. Tener las
  observaciones antiguas no sustituye predicciones obtenidas sin aprender de sus
  resultados. Ampliar hasta esos años exigiría preparar esa evidencia y podría
  requerir nuevos ajustes históricos, todavía sin ejecutar. No hace falta que el
  usuario descargue datos nuevos para continuar el diseño.
- Al terminar el inventario D todavía no estaba implementada ni tenía resultados.
  La autorización posterior anterior abre únicamente el nuevo estudio D y sus
  ajustes históricos necesarios. No reabrir los cálculos cerrados ni trabajos
  operativos por el inventario.

## Investigaciones completadas y límites de la conclusión

- **Umbral favorable:** [informe](agents/prediction-thresholds/resultados-2026-10-03.md).
  Carpeta original `prediction/` renombrada a `prediction-thresholds/`.
  Subir el umbral no mejoró la precisión conjunta de aereus (76,7% → 76,1%);
  caesarea mantuvo el mismo umbral y resultado. No se promovió una alternativa.
- **Selección del ganador:** [informe ampliado](agents/prediction-model-selection/resultados-2026-10-04.md#indice-utilidad-oportunidades).
  A usa ranking reciente Y−1; B añade Y−2; C usa B con selección diaria.
  Mismos modelos finales por corte, sin nuevos ajustes en este segundo estudio.
  Las letras A/B del estudio de umbrales representan otros procedimientos.
- En selección, B de caesarea alcanza precisión 84,4% y detecta 37,6% de positivos;
  C, 74,2% y 57,6%; A, 57,0% y 24,9%. B/C son alternativas prometedoras con
  intercambios distintos. Aereus no mejora con B/C. No promover con esta evidencia
  no significa que A sea óptima ni que B/C carezcan de utilidad.
- Ninguna alternativa superó toda la regla de nominación del agente, fijada antes
  del cálculo. Era un filtro conservador, **no los costes elegidos por el usuario**.
  En caesarea B2025 hubo abstención completa: 175 emisiones vetadas por ROC de la
  familia semanal seleccionada y siete por huéspedes desconocidos. Posible
  investigación posterior: filtrar elegibilidad antes de elegir familia semanal
  o recuperar alternativas diarias. No se implementó ni se autoriza ahora.
- Cohorte externa: 116 observaciones distintas, 812 emisiones por variante,
  cortes 2024–2026; no 812 visitas independientes. Los 68 casos objetivo anteriores
  a 2024 se usaron para desarrollo. Los años externos ya habían influido en las
  hipótesis: **evidencia retrospectiva exploratoria**, no confirmación intacta.
  La reconstrucción meteorológica tampoco prueba disponibilidad exacta al emitir.
- Mantener el entrenamiento operativo existente: evaluación previa y ajuste final
  con todas las filas elegibles. El antiguo 30% no es una reserva independiente
  frente a ese ajuste final. La auditoría local encontró sólo una observación
  por especie ausente de todos los modelos pertinentes; ambas favorables y
  insuficientes para confirmar utilidad. No reevaluar el artefacto instalado sobre
  sus propias filas como prueba de generalización.
- Usuario aclaró: los 16 GBIF caesarea etiquetados `normal` son favorables igual
  que los demás; no excluir/penalizar por origen. El entrenamiento del 28/09
  explica artefactos anteriores a las últimas observaciones descargadas; no es
  motivo para relanzar trabajos.
- Verificaciones de los estudios, registradas en sus cierres: 11 pruebas en
  umbrales; 35 en selección, tres catálogos reproducidos, 812 emisiones de control
  y 19.514 comparaciones B/C. Unos 47 minutos conjuntos de lotes sobre un techo
  de 120, no una estimación; 8 GiB autorizados por proceso y 2 GiB de salidas.
  No se repiten cálculos ni tests de ejecución por este cierre documental.

## Estado operativo conocido y protecciones

- **HA 0.2.331 instalada y funcionando**, confirmado por el usuario. Release,
  paridad y pruebas locales cerradas; no hay release pendiente por los círculos.
  [Evidencia histórica](reports/release-ha-0.2.331-2026-10-03.md).
  No se inspeccionó nuevamente HA ni se acredita aquí su estado en tiempo real.
- Último worker documentado: **1.1.6**, primario `http://100.111.77.48:8100`,
  adicional `http://rainmapper-ha-ui:8100`, identidad `worker_1a9a232c20fe2ee2`.
  No cambiar coordinadores; no inferir que está ocioso. Si una tarea autorizada
  exige recrearlo, leer/conservar antes y verificar después el destino persistido.
- HA local conocido: `rainmapper-local-rainmapper-ha-ui-1`, puerto 8101;
  worker `rainmapper-worker`. No se inspeccionaron ni recrearon en este cierre.
  Usuario ya descargó datos a local; investigación aislada, sin sobrescribir HA.
- Geografía operativa: `docker-media/rainmapper/geography/` local,
  `/media/rainmapper/geography/` real y `geography/` en volumen worker.
  Conservar `geography-sources/` y todos los originales operativos. Raíces
  `mushroom-GIS-todelete/` y `mushroom-map-GIS-todelete/` retiradas con permiso
  el 03/10; no recrearlas ni reabrir geografía/WhatsApp/release cerrados.
- No SSH a la RPi4 sin petición expresa. Usar sólo montajes que el usuario ya
  haya hecho, tras verificar origen; no montar SMB por iniciativa propia.
  Rutas usadas antes: `/Volumes/share` y `/Volumes/media-1`, sin comprobarlas ahora.
- Conservar IFF como indicador, no tasa de acierto; IDW sin filtro espacial,
  SMI regulado + PM + una capa y suspensiones. Revalidar modo de recomendaciones
  si una tarea necesita interpretarlo. Política territorial y Campins/Qv3 cerrados:
  no deducir suelo por bosque/pH o por vecinos.
- No ejecutar `tmp/meteocat-repair-20260926/deploy_csv_decimal_fix.py`: candidata
  histórica que perdería datos nuevos. Data y PublicData no se sincronizan por
  copiar uno de ellos. Detalles científicos y operativos en `decisions.md`.

## Próximos pasos por prioridad, sólo con el alcance que pida el usuario

1. **Revisión de utilidad guardada en TODO:** discutir los requisitos anteriores
   y el futuro diseño de validación; no elegir peso por favorecer un resultado,
   no cambiar reglas retrospectivamente ni promover modelos.
2. Si se encarga otra investigación: separar la hipótesis de elegibilidad semanal
   de la elección de costes; congelar reglas antes de nueva evidencia. Predicciones
   prospectivas fechadas antes de las salidas, negativos explícitos y visitas
   registradas con independencia del consejo; muestra suficiente por determinar.
3. Pruebas funcionales del usuario pendientes: asignación de observaciones,
   recuperación GIS en setales e importación GBIF. Otros bloques aplazados:
   pérdida de worker/trabajo huérfano, duración del precálculo, consumidores MVC50
   originales, setales fuera de áreas y topónimos GBIF. No ejecutarlos por defecto.
4. **Disco detenido:** quedaron ~35,8 GB sin atribuir del balance histórico Finder
   de 305,36 GB; no conciliación exacta. Usuario indicó Fotos 2,6 GB y prefirió
   mediciones desde Terminal con permiso, pero después detuvo la auditoría.
   No volver a barrer disco ni restar esa cifra sin revisar ámbitos/solapamientos.
   La retirada de una sesión Codex de 524 MB sigue pendiente por error de CLI,
   con autorización previa conservada pero sin reanudar limpiezas. No editar
   SQLite a mano. Instaladores/DMG, Lightroom, Buildx y fuentes se conservan.

## Archivos, evidencia y cierre

- Informes, método y lanzadores: `docs/agents/prediction-thresholds/` y
  `docs/agents/prediction-model-selection/`; scripts aislados en
  `scripts/prediction_research/` y `scripts/prediction_model_selection/`.
- Evidencia privada: `tmp/prediction-research/` y
  `tmp/prediction-model-selection/`, con `analysis/results.json` y `closure.json`.
  Los cierres acreditan sus ejecuciones originales. Ediciones explicativas
  posteriores se registran en `tmp/prediction-model-selection/documentation-amendments/`;
  no reescribir sellos originales para hacerlos coincidir con documentación nueva.
- En esta sesión se aclararon tablas con cantidades/denominadores/porcentajes,
  interpretación de B/C y propuesta de utilidad. En el cierre: contexto compacto,
  TODO y decisiones; archivo del contexto sustituido. Cálculos aritméticos
  contrastados con JSON guardados; validación documental, no nueva prueba operativa.
- Git: HEAD `c28a514b` comprobado en este cierre; cambios documentales y de los
  estudios sin commit/push. Hay cambios de cierres anteriores ajenos a esta tarea.
  Privados: `mushroom-data/mushroom_observations.json` modificado y
  `mushroom_observations.json` raíz sin seguimiento: **no añadir, revertir ni copiar**.
- Historia retirada de la ventana activa:
  [archivo 04/10](reports/session-context-before-close-2026-10-04.md);
  [cierre anterior 03/10](reports/session-context-before-close-2026-10-03.md).
  Auditoría de disco y recibos siguen en `docs/reports/mac-disk-audit-2026-10-03.md`
  y `tmp/disk-audit-20261003/`; no releerlos al arrancar.
- Progreso breve aproximadamente cada minuto; verificar fuentes primarias sólo
  según la tarea elegida. Leer estos dos documentos no autoriza ejecutar pendientes.
