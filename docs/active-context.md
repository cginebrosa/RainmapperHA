# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-09-02

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  HEAD revalidado antes de los cambios locales:
  `5004b7261edab39c022f150fec3881e8c458c954`.
- El código declara HA `0.2.291` y worker `1.0.37`.
- HA `0.2.291` y `latest` están publicados en GHCR con el mismo índice OCI
  `sha256:59264468522dfeb46e6e9530636b1904e51ec851449d12c7d75f7d6d86cdf45d`
  y manifests `linux/amd64` y `linux/arm64`.
- Tras la última actualización, el usuario confirma el 2026-09-01 que la
  aplicación funciona correctamente y que varios runners programados han
  completado sus precálculos. Esta confirmación es observación del usuario; la
  versión instalada y el estado del worker no se han consultado de nuevo desde
  esta sesión.
- El worker privado no se publica. Está reconstruido localmente como `1.0.37`,
  healthy/idle, con identidad `worker_1a9a232c20fe2ee2`, volumen
  `rainmapper-worker-data`, cachés GIS y Predictor válidas y ambas lanes idle.
  El endpoint local confirmó `worker_version=1.0.37`, dataset y caché Predictor
  válidos, y ambas lanes idle tras la reconstrucción.
- No hay entrenamientos programados. No tocar retención, datos reales, HA real
  ni lanzar entrenamientos, bumps, builds o publicaciones sin autorización.

## Release HA 0.2.291 / worker privado 1.0.37

- La continuidad con un precálculo anterior desactualizado y la prohibición de
  cálculo científico en línea en HA real están implementadas en el worktree.
  Una diferencia de fingerprint ya no descarta por sí sola el SQLite: si la
  consulta está completa se reutiliza y la UI muestra fecha/hora,
  `desactualizado` y `necesita actualizarse`. Si no hay hit, HA real termina con
  indisponibilidad antes de ejecutar localmente o crear un job remoto. El
  laboratorio local conserva el cálculo explícitamente habilitado para pruebas.
- La release quedó validada con 1.229 pruebas, smoke completo, comprobaciones de
  sintaxis, versiones, cache-busters, fixtures y shell. El flujo real local
  reutilizó el SQLite anterior y mostró su fecha/hora y `necesita actualizarse`
  sin informar cálculo nuevo. La imagen multiarch y el worker se verificaron
  después de construirlos; no se lanzó ni monitorizó ningún precálculo local.
- Los trabajos locales de reconstrucción/entrenamiento y precálculo permanecen
  solo en `MUSHROOM_REBUILD_JOBS`: desaparecen al reiniciar el contenedor o una
  hora después de terminar. El usuario observó esta pérdida tras reconstruir
  HA; queda pendiente persistir ese historial sin mezclarlo con esta corrección.
- La selección multiversión ya está implementada en el worktree para las tres
  vistas operativas. `Esta semana` aplica el conjunto elegido a todas las
  especies candidatas; `Por especie`, a todas sus áreas y siete días; y la
  selección se conserva al cambiar de pestaña, día, especie, área o ficha.
  El lector SQLite compone estos resultados con los miembros operativos ya
  precalculados, sin volver a ejecutar inferencia.
- La primera prueba visual detectó que `Esta semana` y `Por especie` mostraban
  el encabezado multiversión pero ninguna casilla: la UI estaba leyendo el
  catálogo descriptivo embebido en el resultado precalculado, que no contiene
  el inventario de artefactos instalados. El selector lee ahora exclusivamente
  el registro local vigente, mientras el resultado sigue saliendo del SQLite.
  La entrada directa y ambas vistas resuelven además la preferida vigente como
  selección explícita cuando la URL no trae `mvv`; así un cambio V4→V3 no deja
  que el resultado precalculado conserve implícitamente V4. Las cinco opciones
  se presentan como casillas compactas V2/V3/V4/V5w/V6w; el nombre largo queda
  en el detalle técnico y en el tooltip.
- La actualización local completa fallaba antes de preparar V2--V6 cuando el
  lote instalado contenía un `tuning-catalog.json` copiado de un lote anterior.
  El coordinador descarta y elimina ese fichero incoherente, reconstruye los
  ajustes desde los artefactos verificados del lote instalado y mantiene la
  validación estricta para cualquier catálogo que sí declare pertenecer al lote
  actual. El fichero incoherente del lote local
  `local_operational_20260828T101432Z` se eliminó con autorización. La
  reconstrucción contra esos modelos reales produjo 636 ajustes en 6,3 s, sin
  lanzar entrenamiento.
- El selector `Preferida` de `Consultar fecha` estaba integrado en el formulario
  GET de la consulta. Cambiarlo y pulsar `Predecir` elegía esa versión para la
  consulta, pero no ejecutaba el POST ya existente que persiste
  `preferred_version_id`; por eso el badge superior seguía mostrando V4.
- La UI local muestra ahora la preferida realmente guardada y añade la acción
  explícita `Usar como preferida`. El selector de preferencia y las casillas de
  versiones incluidas son estados independientes. Esa acción no predice ni
  navega: persiste únicamente una versión instalada, actualiza el badge y
  libera la caché del Predictor. Solo `Predecir` o una navegación que necesite
  cargar resultados ejecutan una consulta.
  Ya no republica el runtime: el registro empaquetado conserva un default
  interno estable, separado del puntero de UI, porque el precálculo contiene
  todas las versiones instaladas. V4→V6→V4
  conserva la misma huella; cambiar un modelo sí la cambia. El esquema interno
  de publicación `1.2` fuerza una única regeneración local del formato anterior
  sin modificar el manifiesto consumido por el worker. La imagen HA local se
  reconstruyó después de cerrar la validación y el cambio quedó publicado en
  HA `0.2.291`.
- `Lanzar precálculo` desde el panel principal muestra ahora el mismo indicador
  de preparación que la acción equivalente de `Workers y trabajos`. El envío
  se intercepta, espera dos frames para que el navegador pinte el modal y usa
  un POST asíncrono; el modal permanece durante toda la espera y la página solo
  se recarga cuando el servidor confirma la solicitud. Si falla, muestra el
  error y permite cerrar y reintentar. El endpoint conserva el POST clásico
  para clientes sin JavaScript y devuelve JSON al cliente asíncrono. La imagen
  HA local se reconstruyó y el contenedor activo contiene el formulario, el
  doble frame de pintado y la cabecera asíncrona; no se lanzó un precálculo para
  comprobar una corrección puramente de interacción.
- En el modal de avance, `Cerrar` retira inmediatamente el diálogo antes de
  recargar el resumen de un trabajo completado. La recarga espera dos frames,
  evitando que una respuesta lenta de HA haga parecer bloqueado el botón.
- La validación servida encontró un último desacoplamiento: el lector SQLite
  componía correctamente V3/V4 para `Esta semana` y `Por especie`, pero esas
  vistas entregaban a los helpers visuales el sobre multiversión completo en
  vez de su `operational_comparison`. El resultado era una tabla vacía o con
  apariencia de V4 aunque las casillas fueran correctas. `PreparedPredictor`
  conserva el contrato y la UI extrae ahora el resultado operativo anidado en
  un único punto, igual que ya hacía `Consultar fecha`.
- Validación final del cambio de UI, servicio y precálculo: 414 pruebas pasan.
  Incluyen preferencia asíncrona sin predicción ni navegación, independencia
  entre preferida y versiones incluidas, selección global del recomendador,
  semana multiversión y composición de ambas vistas desde SQLite. También
  pasan la compilación de los cuatro módulos modificados y `git diff --check`.
  La imagen `rainmapperha:local-ha-ui` se reconstruyó y el contenedor quedó
  activo. La respuesta servida de `Esta semana` con V3+V4 contiene cinco
  casillas compactas, conserva ambas selecciones y muestra ganadores V3 y V4
  desde el precálculo. `Por especie` usa el mismo resultado operativo y
  `Consultar fecha` mantiene la acción separada de preferencia. El usuario
  confirmó la validación visual y el cambio quedó incluido en HA `0.2.291`.

## Auditoría de almacenamiento local — 2026-09-01

- El workspace ocupa `19.184.004 KiB` (`18,30 GiB`). El desglose, las fuentes
  y la propuesta conservadora están en
  `docs/storage-audit-local-2026-09-01.md`; no se borró nada durante la
  auditoría.
- El reconciliador protege el lote instalado
  `local_operational_20260901T123855Z` y declara `1.857.696.686 bytes`
  recuperables en nueve lotes antiguos, ocho resultados y dos bundles
  huérfanos.
- Hay además unos `256 MiB` de staging de precálculo abandonado. El precálculo
  activo de `442 MiB` permanece en `/media` y no se debe tocar.
- `docker-data/audits` suma `6,52 GiB`. No participa en runtime, pero conserva
  evidencia enlazada desde informes; requiere una decisión explícita de
  conservar, archivar o eliminar.

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
- La retirada posterior de copias legacy se ejecutó con autorización explícita
  el 2026-09-01 y queda documentada en la sección de almacenamiento.

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

- La suite final completa pasó: 1.201 pruebas, además de compilación, JSON,
  shell, fixtures y comprobaciones de diff. Las 385 pruebas dirigidas de jobs,
  worker, servidor web, almacenamiento y empaquetado también pasan tras la
  nueva persistencia.
- `git diff --check` correcto tras código y pruebas; repetir al cierre.
- Worker `1.0.34` construido y verificado healthy/idle, con identidad, volumen,
  cachés y capacidades conservados. Ambas lanes estaban idle en la comprobación.
- HA `0.2.287` publicada, verificada en GHCR e instalada en HA real con worker
  `1.0.34` conectado. El primer push agotó el plazo
  después de subir capas y no creó el tag; un reintento completó ambos tags con
  el índice multiarch indicado arriba.
- HA `0.2.288` publicada y verificada en GHCR con el índice multiarch indicado
  en el histórico. Worker `1.0.35` reconstruido y verificado healthy/idle
  conservando identidad, volumen y cachés. HA real se actualizó a `0.2.288`.

## Correcciones publicadas en 0.2.289

- La cancelación del precálculo queda sellada también en `desired.json`: una
  revisión cancelada no se vuelve a materializar después de reiniciar
  Rainmapper o Home Assistant, y una entrega tardía se rechaza.
- El resumen del precálculo se refresca junto con la tabla de trabajos, de modo
  que pasa de `Calculando` a `Listo` sin una recarga manual.
- La tabla denomina `Espera` al tiempo previo a ejecutar para separarlo del
  tiempo efectivo de cálculo.
- El smoke final pasó 1.204 pruebas, sintaxis, fixtures y comprobación de diff.
  `0.2.289` y `latest` comparten el índice OCI
  `sha256:67d6abd75624474bf8703fe4b75fae6b9c8d396756b22e8cc7f03cfdcee62769`
  con manifests `linux/amd64` y `linux/arm64`.
- El worker no cambió y permanece en `1.0.35`.

## Observación del Predictor tras el precálculo real

- El fallo se reprodujo el 2026-09-01 al volver de `Consultar fecha` a
  `Esta semana`. Los diagnósticos reales registran un miss
  `request_not_precomputed` de 203,986 s y otra petición que esperó 72,076 s el
  bloqueo global. El proceso siguió calculando después del timeout del cliente;
  no hubo OOM ni participación del worker.
- La causa está localizada: el recomendador es global para todas las especies,
  pero el artefacto lo almacena una vez con la primera especie y el lookup
  incluía en la clave la especie seleccionada que llegaba desde la consulta por
  fecha. Había una segunda divergencia: el SQLite conserva como `issue_date` el
  inicio de su semana, mientras la petición UI usa el día actual. Al cruzar la
  medianoche, todas las lecturas frías de un artefacto aún vigente podían caer
  al fallback aunque la cobertura siguiera siendo válida.
- El cambio publicado en HA `0.2.291` canoniza el `issue_date` de lectura al
  ancla del artefacto durante toda su cobertura y, sólo para `recommender`, la
  especie global. `Por especie` conserva su identidad específica. La respuesta
  mantiene fecha y especie solicitadas como estado de UI. Además, un cálculo
  local sin `job_id` ofrece `Dejar de esperar` en vez de un botón de cancelación
  inutilizable y avisa de que el servidor puede terminar lo ya iniciado.
- Validación local fría sobre el SQLite real de 441 MiB, tras reiniciar HA para
  vaciar la caché en memoria: `Consultar fecha` Aereus/Olvan respondió en 1,87 s
  y el regreso a `Esta semana` en 0,33 s; ambas páginas declararon
  `Precálculo: usado` y cálculo `<0,1 s`.

## Validación real estable y limpieza de `/share` — 2026-09-01

- El usuario confirmó funcionamiento correcto y varios precálculos completados
  por runners programados tras la actualización.
- Con backup previo confirmado por el usuario y autorización explícita, se
  retiraron aproximadamente 405,6 MiB reconstruibles de `/share`: 328,6 MiB de
  `ml_models`, 39,3 MiB de resultados privados terminales, 18,8 MiB del rollback
  duplicado de promoción y 18,8 MiB de seis artefactos raíz reconstruibles.
- Antes del borrado, los seis artefactos y el rollback se compararon byte a byte
  con `/media`; la transición constaba completada con 691 ficheros,
  276.957.056 bytes y cero conflictos. No se borraron meteorología,
  observaciones, perfiles, catálogos, imágenes/vídeos ni backups.
- Después de la limpieza, `/share/rainmapper/mushroom-data` ocupaba 191.044 KiB.
  No se ha cambiado la política de retención.

## Limpieza equivalente del laboratorio local — 2026-09-01

- Con autorización explícita se retiraron únicamente copias reconstruibles del
  montaje local `/share`: `ml_models`, el precálculo legacy, bundles/resultados
  terminales y artefactos raíz ya trasladados. Se conservaron observaciones,
  meteorología, perfiles, catálogos, credenciales, imágenes/vídeos y backups.
- El montaje local `/share/rainmapper/mushroom-data` bajó de unos 2,34 GiB a
  174.440 KiB (unos 170 MiB). Los derivados permanecen en el montaje local
  `/media/rainmapper`; no se cambió retención ni se tocó HA real.
- La copia canónica del registro usada por la publicación científica se guarda
  en el caché de runtime de `/media`, no en `/share`; conserva un default
  interno estable y no sigue los cambios del puntero de preferencia de la UI.

## Validación local del cambio de identidad — 2026-09-01

- Pasan 88 pruebas dirigidas de publicación/runtime, servicio, precálculo,
  persistencia de preferencia y señal de artefacto desactualizado.
- La prueba específica V4→V6→V4 conserva el fingerprint y reutiliza la
  publicación canónica; al modificar un modelo, el fingerprint cambia.
- Compilan los módulos y pruebas modificados. `git diff --check` queda limpio.
  No se lanzó entrenamiento, precálculo, build, instalación ni release.

## Próximos pasos inmediatos

1. Validar manualmente en navegador que V4→V6→V4 conserva el precálculo vigente
   después de reconstruir HA local con autorización. No hacer bump, build ni
   release sin autorización.
2. Mantener la versión real estable y observar los runners programados.
3. En una futura cadena real completa, confirmar la
   reducción de las esperas de 1--2 minutos. Las pruebas demuestran que se han
   eliminado llamadas repetidas, pero no sustituyen esa medición real.
4. Medir el siguiente backup para cuantificar la reducción comprimida real.
5. En la siguiente ejecución real, revisar la instrumentación ya instalada en
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

## Regresión real de cola en 0.2.287/1.0.34 y corrección 0.2.288/1.0.35

- El precálculo real `worker_job_JkpxgP8ZE0LB` fue reclamado, sincronizó
  selecciones y runtime, pero falló antes del cálculo científico con `timed
  out`. Rainmapper quedó sin responder durante el atasco; HA siguió operativo.
- La cola monolítica real tenía 50 jobs y unos 26 MiB. `runtime_manifest`
  aportaba 11.085.080 bytes compactos y `operational_selections` 9.479.877;
  cada progreso analizaba y reescribía el documento completo bajo `RUN_LOCK`.
- La corrección publicada introduce cola v2: `/share` conserva sólo el índice y
  estado ligero; manifiesto y selecciones reconstruibles viven por job en
  `/media/rainmapper/mushroom-derived/worker/job-payloads`. Al salir un job de
  la cola se elimina también su payload. El histórico v1 se descarta en la
  primera apertura sin analizar el JSON grande; por ello el despliegue debe
  hacerse sin trabajos activos.
- Una simulación con los 50 jobs reales dejó el índice en 472.783 bytes y una
  escritura estable en 0,009 s sobre disco local. La migración descartable de
  una copia del JSON v1 tardó 0,001 s y produjo una cola vacía de 72 bytes.
- Los hitos de progreso del precálculo usan ahora la telemetría coalescida y
  tolerante a fallos de transporte. Un timeout de UI no aborta el cálculo; la
  entrega final continúa siendo estricta.

## Riesgos y dudas activos

- Se comprobó en el laboratorio local que Edulis/La Masella V6w devolvía
  `76,69–85,55%` para 2026-09-01 y `78,07–86,19%` para 2026-09-02 mediante el
  selector multiversión, mientras el comparador heredado usado por Historial
  se abstenía en esas mismas fechas. No era una diferencia de meteorología: las
  dos ejecuciones se hicieron consecutivamente dentro del mismo contenedor y
  sobre los mismos montajes. Historial se ha conectado al selector
  multiversión canónico; sus predicciones y resúmenes anteriores no deben
  considerarse una evaluación válida del Predictor actual.
- El smoke posterior a la reconstrucción local confirmó para Historial de
  Edulis con sólo V6w: 45 episodios, 28 veredictos evaluables, 26 correctos
  (`93%`), 9 favorables no detectados y `Smooth Partial–V6w` como fuente en las
  45 filas. Sustituye al resultado incorrecto anterior de 45 abstenciones,
  `0%` y 29 no detectados.
- Ese resumen retrospectivo se retira porque reutilizaba observaciones que
  también podían haber intervenido en entrenamiento. El contrato nuevo del
  catálogo de calidad `1.1` conserva, por modelo exacto, la matriz de
  clasificación sobre filas hold-out con los cortes operativos 0,60/0,40.
  Historial muestra casos probados, favorables acertados/encontrados y
  desfavorables acertados/encontrados como porcentaje y fracción. El listado
  de episodios permanece debajo como auditoría retrospectiva independiente.

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
- La canonización del recomendador y `Dejar de esperar` están sólo en el
  worktree: aún requieren validación local completa y una release autorizada.
- La limpieza autorizada ya terminó. No hay autorización para retirar más datos
  ni para cambiar retención.

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
