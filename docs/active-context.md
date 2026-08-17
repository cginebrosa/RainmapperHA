# Active Context

Ventana operativa para continuar RainmapperHA. El histórico y las razones
duraderas viven en `docs/decisions.md`; los detalles científicos están en los
informes y especificaciones enlazados. No reconstruir el estado desde mensajes
de sesiones anteriores.

## Estado operativo actual — release preparada 2026-08-17

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
  El worktree contiene muchos cambios locales y ficheros nuevos de esta línea
  de trabajo. Son deliberados: preservarlos y no limpiar, resetear ni sustituir.
- El último estado documentado, no revalidado contra los hosts reales en esta
  sesión, sitúa HA en `0.2.254` y el worker M1 en `1.0.8`. Altitude
  V2 es la generación operativa instalada. M1 es el ejecutor ordinario y HA el
  fallback lento ya validado (~98 s y ~577 MiB en la prueba semanal).
- HA `0.2.255` está publicada pero no instalada. Worker `1.0.9` existe solo
  como imagen local. Ambos son anteriores al cierre actual de V3/V4 y deben
  saltarse; no instalarlos ni reutilizarlos para la actualización final.
- El Predictor operativo está temporalmente desalineado: los bundles antiguos
  validan el hash bruto de `mushroom_known_sites.json`, mientras el fichero de
  HA ya contiene la nueva microárea y los contextos DEM/SoilGrids. El error de
  huella es real y no se resuelve relajando la barrera. Requiere reconstrucción
  y entrenamiento coordinados desde el mismo snapshot cuando el usuario
  autorice la actualización completa.
- Única escritura realizada en HA durante esta línea: actualización autorizada
  de `/share/rainmapper/mushroom-data/mushroom_known_sites.json` por SMB, con
  sustitución atómica y lectura de retorno. Hash instalado `bb96c4c...`;
  backup `mushroom_known_sites.pre-dem-soilgrids-20260816T0320.json`, hash
  `e1da0f7e...`. Hay 59/59 microáreas con DEM y 59/59 con SoilGrids completo.
  `tor_tor` tiene altitud DEM media 1.800,7 m. No se modificaron observaciones,
  modelos, worker ni releases en HA.
- Fuente canónica local actual: `docker-data/mushroom-data/`.
  `mushroom_observations.json` tiene 395 observaciones y SHA
  `50b189080395...`; `mushroom_known_sites.json` tiene SHA `bb96c4c1a0b...`.
  El scheduled runner meteorológico no consume ni modifica `known_sites`.

## Resultado local cerrado

### Integración multiversión local HA 0.2.256 / worker 1.0.10

- Las fuentes quedan versionadas como HA `0.2.256` y worker `1.0.10`. HA
  `0.2.256` está publicada en GHCR pero todavía no instalada; el worker
  `1.0.10` está construido, validado y empaquetado de forma privada, pero no
  instalado. El último estado documentado de los hosts reales sigue siendo HA
  `0.2.254` y worker M1 `1.0.8`; `0.2.255`/`1.0.9` siguen descartadas.
- El registro genérico expone V2--V6 mediante perfiles, contratos temporales,
  estimadores y ámbito por especie/compartido. Una entrada no es seleccionable
  hasta que exista su artefacto exacto en una generación inmutable; nunca cae
  silenciosamente a V2.
- Predictor conserva las explicaciones existentes y añade comparación de
  miembros instalados. Cada probabilidad se presenta por separado: no hay
  promedio, consenso implícito ni cambio del ranking operativo.
- `fixed_gap` conserva horizonte 7. `lag_event` crea un único artefacto por
  especie+contrato+estimador y reutiliza ese ajuste en horizontes 1/2/3/7.
- El flujo completo de HA mantiene dos salidas separadas: primero reconstruye y
  entrena el V2 operativo promocionable; al terminar encadena un job V2--V6
  no operativo para Comparar. El segundo consume los seis benchmarks del
  snapshot canónico, transporta entradas y resultados con tamaño+SHA-256 por
  fichero, instala el batch de comparación atómicamente y declara
  `operational_candidate_trained=false`.
- El worker anuncia `ml_multiversion_training_v1` y HA rechaza asignar el job a
  un worker que no lo declare. El usuario conserva el control: todavía no se ha
  lanzado ninguna regeneración ni entrenamiento.
- Validación local de esta pareja: smoke completo correcto, `845/845` pruebas,
  compilación y `git diff --check` correctos; HA local responde y worker local
  `1.0.10` está sano, conectado e inactivo.
- Especificación: `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.
  Implementación principal: `mushroom_ml_model_catalog.py`,
  `mushroom_ml_runtime_trainer.py`, `mushroom_ml_runtime_inference.py`,
  `mushroom_ml_runtime_features.py` y
  `mushroom_ml_multiversion_comparison.py`.

### Meteorología común y reparación oficial

- La reconstrucción local oficial quedó cerrada con generación
  `20260815T225412516277Z-b7d0a13766a8` y manifiesto SHA
  `0e64ac77e322...`. AEMET no conserva días completos de red ausentes;
  Meteocat solo carece de 2020-02-01, 2020-02-02 y 2020-11-25, fechas cuya API
  devuelve cero filas incluso aisladas. Este histórico reparado no se ha
  promovido a HA y deberá rebasarse contra un snapshot fresco antes de hacerlo.
- El código local de autocuración oficial detecta huecos posteriores al solape
  ordinario, mantiene cola durable, bloques máximos de 15 días, backoff y cierre
  automático. Meteocat usa dos consultas por bloque y pausa; AEMET limita una
  petición de climatología por runner. Está probado localmente, no desplegado.
- V2/V3/V4 se comparan con la misma capa meteorológica: IDW de área usando
  AEMET, Meteocat, Meteoclimatic y Wunderground; radio 15 km, potencia 2 y una
  contribución válida como mínimo. Tmin/Tmax se corrigen a la altitud DEM de la
  microárea antes de ponderar; RHmin/RHmax no se corrigen. Lluvia vacía no se
  convierte genéricamente en cero. Calidad/procedencia nunca entra en `X`.
- El IDW se materializa como serie larga por microárea, prefiltra estaciones a
  15 km, reutiliza ET0 y corta ventanas exactas. La optimización conserva hashes
  de muestras y sirve tanto al benchmark como a futuros datasets de training.

### Biology V3/V4 y comparación

- Biology V3 está implementada localmente: `predictive_features`, `quality` y
  `metadata` separados; las pruebas impiden que calidad o área entren en `X`.
  `fixed_gap_7d_biology_v3` y `lag_event_biology_v3` conservan observaciones y
  publican gates/motivos legibles. No existe candidato V3 entrenado ni promovido.
- Biology V4 está implementada y cerrada como `proposed`: meteorología
  ampliada, balance climático, estado hídrico SoilGrids experimental,
  continuidad y paridad train/inferencia. V4 core reproduce V3; el balance no
  mejora Brier consistentemente y SoilGrids suele empeorar predicción y
  continuidad. El suelo se conserva evaluable pero desactivado.
- Snapshot canónico de evidencia:
  `docker-data/audits/mushroom-ml-snapshot-20260816/`. Su `MANIFEST.json`
  registra fuentes, hashes, benchmarks y comparaciones. V3 fixed: 395 muestras,
  352 elegibles. V3 lag: 1.580 tareas, 1.408 elegibles. V4 core/meteo/balance
  conserva las mismas filas; las variantes profundas de suelo pierden algunas.
- Comparaciones canónicas cerradas sobre filas idénticas:
  `comparison-fixed-groups7.json`, `comparison-fixed-groups14.json`,
  `comparison-lag-groups7.json` y `comparison-lag-groups14.json`. Incluyen V2,
  V3 y V4, seis algoritmos, especies y grupos de florada 7/14. No contienen
  modelos (`operational_model_written=false`).
- `lag_event` ajusta un único modelo por especie+contrato+estimador. Horizonte
  1/2/3/7 forma parte de `X`; sus métricas filtran predicciones del mismo
  hold-out sin reentrenar. El bucle anterior multiplicaba cinco veces el coste
  y era semánticamente incorrecto. `lag/groups7` completo bajó de 650,68 s a
  unos 157 s. El artefacto pre-corrección se conserva con
  `decision_eligible=false` y no puede fundamentar decisiones.
- Informe canónico: `docs/reports/V2_V3_V4_consensus_report002.md`. El informe
  001 es histórico. No hay ganador universal ni Brier medio válido. RF+ET es la
  pareja con más acuerdo bruto, pero pierde fuerza al exigir que ambos superen
  prevalencia; ningún ensemble está validado contra su mejor miembro.
- Dos observaciones revisadas ya cambian patrones: RF pasa a 4/4 para
  `boletus_pinophilus` en V3 y ambas V4; `boletus_edulis` queda sin dos clases en
  train para grupos 7 y solo es evaluable con grupos 14. El soporte sigue siendo
  insuficiente para promover V4 o fijar un consenso.
- Validación final: 801/801 pruebas locales y `git diff --check` correcto.

### Biology V5 raw weather discovery

- Se implementó el experimento local no operativo de 365 días raw con los
  cinco canales IDW comunes y una ablación ET0+balance. Usa Elastic Net y
  sparse-group logistic; no escribe modelos ni entrena candidato operativo.
- Artefactos auditables:
  `docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/`. Conservan 395
  filas fixed, 1.580 tareas lag, 12.280 predicciones hold-out con clave única y
  falsos positivos/negativos compartidos. En lag cada ajuste se realiza una
  vez y 1/2/3/7 son filtros de las mismas probabilidades.
- En 34 contextos especie+contrato+partición, el mejor V5 vence 2 y pierde 32
  frente al mejor miembro individual V2/V3/V4. Las victorias son únicamente
  `boletus_edulis` en grupos de 14 días; no hay mejora general.
- La sensibilidad por campaña solo supera a la vez prevalencia y fenología en
  ambos contratos para `amanita_caesarea`, `boletus_pinophilus` y
  `cantharellus_cibarius_sl`. La selección sigue siendo muy densa y no define
  ventanas interpretables. La ablación sin calendario está ejecutada y 25/25
  remuestreos agrupados terminaron en los 32 contextos evaluables; 3.330 celdas
  estables siguen distribuidas casi uniformemente por retardo.
- Los 87 errores compartidos deduplicados están dominados por `unknown_phase`;
  onset/decline/between-visits no justifican todavía un modelo de estado. No se
  justifica promover GAM/DLNM, estado o jerarquía. Si se hace otro diagnóstico
  después de cerrar los gates, la jerarquía es la prioridad por el soporte
  desigual entre especies.
- Informe: `docs/reports/V2_V3_V4_V5_raw_weather_report001.md`. V5 está en el
  registro genérico como `proposed`, sin generaciones ni capacidad operativa.

### Biology V6 smooth hierarchical

- Se ejecutó el ensayo posterior con diez bases B-spline sobre el eje
  `log1p(retardo)` por cada uno de los cinco canales raw: 50 exposiciones en
  lugar de 1.825 días libres. Compara modelo suave por especie, compartido y
  pooling parcial, siempre sin calendario en el perfil principal.
- V6 gana 4 y pierde 30 de 34 comparaciones contra el mejor miembro individual
  V2/V3/V4/V5. Pooling parcial supera al compartido 44/52, pero frente al suave
  por especie gana 15 y pierde 19; no justifica jerarquía general.
- Las victorias son dos de `hygrophorus_latitabundus` fixed mediante pooling
  parcial (test n=4), y mejoras pequeñas lag/groups7 de `amanita_caesarea` y
  `cantharellus_cibarius_sl` mediante modelo por especie. Son hipótesis, no
  gates de promoción.
- El modelo conjunto puede producir diagnósticos para especies cuyo train
  individual tiene una sola clase, pero esos casos no se cuentan como
  victorias sin comparador anterior evaluable.
- Artefactos:
  `docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/`; informe:
  `docs/reports/V2_V3_V4_V5_V6_smooth_hierarchical_report001.md`. V6 está
  registrada como `proposed`, sin generación ni modelo operativo.

### Integración local HA/worker V2--V6

- El laboratorio local usa HA `0.2.256` y worker `1.0.10`. La imagen HA ya está
  publicada y el worker está empaquetado de forma privada; no se ha modificado
  ninguna instalación real. El
  flujo completo desde `Reconstruir y reentrenar todo` encadena reconstrucción,
  entrenamiento del V2 operativo y lote comparativo no operativo V2--V6.
- Segunda prueba completa real: reconstrucción `worker_job_f5MlfHlN64MBz4SD`
  en 1 min 22 s; V2 `worker_job_hBck2X-aHr8jv4Qa` en 22 s, con 8 especies;
  comparación `worker_job_kMfaeOPFlPgbU7Ty` en 2 min 15 s. Esta última ejecutó
  922 combinaciones, instaló 489 modelos válidos y registró 433 combinaciones
  sin soporte/clases suficientes. El lote
  `local_v2_v6_20260816T181123Z` conserva `active=false` y
  `operational_candidate_trained=false`.
- El usuario promovió manualmente solo la segunda generación completa. La
  reconstrucción y el V2 quedaron `promoted`; el lote V2--V6 siguió siendo
  exclusivamente comparativo. Desapareció `model_input_identity_mismatch`.
- La primera prueba del Predictor descubrió que el claim embebía las 489
  entradas del manifiesto y excedía 64 KiB. El protocolo ahora devuelve un
  resumen acotado y descarga el manifiesto completo por el endpoint autenticado
  de runtime; todas las respuestas de control proyectan también el job compacto.
  El worker conserva en memoria el manifiesto descargado durante la solicitud.
- El botón de cancelación del modal apuntaba a `./predictor/jobs/cancel`; ahora
  usa `./mushrooms/predictor/jobs/cancel`. Se verificó una cancelación real y el
  coordinador respondió `cancelled`.
- La ficha simplificada que `available_predictor_executors()` entregaba al
  selector omitía `capabilities`; por ello el gate rechazaba falsamente V2--V6
  aunque M1 anunciase `predictor_multiversion_v1`. La ficha conserva ahora esas
  capacidades. Se verificó Auto -> M1 con V6 `lag-h1 / Smooth Species`: terminó
  en 3 s y mantuvo la selección multiversión completa.
- Prueba real posterior: primera solicitud válida en 12 s con caché de ficheros
  reutilizada y servicio frío; la siguiente terminó en menos de 1 s, con
  `assignment_revision=1`, `runtime_transferred_size_bytes=0` y sin errores de
  identidad. Validación actual: 841/841 pruebas locales y `git diff --check`.

## Próximos pasos, en orden

1. Congelar V6 y repetirlo cuando existan nuevas campañas/visitas. No añadir
   otra familia ahora: V5 pierde 32/34 y V6 30/34; el cuello de botella vuelve
   a ser soporte independiente por especie y campaña.

2. Mantener V2/V3/V4 vivas mediante el registro genérico. No escoger una pareja
   por acuerdo: cualquier ensemble debe superar al mejor algoritmo individual
   por especie y contrato. V4 permanece `proposed` y no pasa el gate actual.
3. Cuando la plataforma vuelva a estar alineada, el usuario incorporará cuatro
   salidas negativas recientes en cuatro microáreas y cuatro especies. Crear un
   snapshot inmutable nuevo, no sobrescribir este, y repetir las comparaciones
   para medir sensibilidad.
4. Instalar primero el worker `1.0.10`, comprobar que conserva identidad/caché
   y queda en espera; después actualizar HA a `0.2.256`. Este orden evita abrir
   la nueva UI con un worker aún incapaz de ejecutar V2--V6. HA `0.2.254`
   acepta listas de capacidades adicionales con el mismo schema `0.1`.
5. Tras instalar ambos, validar versión/capacidades, Predictor normal y
   Comparar. Solo entonces lanzar desde HA la regeneración completa autorizada;
   no entrenar ni promover nada durante la instalación.

## Rediseño local de comparación V2--V6 completado

- Decisión semántica: `active` describe únicamente qué generación alimenta el
  runtime heredado. V2--V6 tienen el mismo estatus experimental: ninguna es
  válida, aceptada, preferida, promovida o ganadora. V2 aparece en la tarjeta
  superior únicamente porque fue la primera implementación conectada a ella;
  ese orden cronológico no aporta prioridad estadística.
- El selector principal se reduce a V2/V3/V4/V5/V6 y expande internamente todos
  los perfiles, contratos, horizontes y estimadores instalados. El detalle
  exacto queda desplegable.
- Se añade un catálogo de calidad calculado directamente desde las predicciones
  hold-out fila a fila de los snapshots canónicos. Mantiene separadas especie,
  contrato, horizonte y estimador; no promedia Brier entre especies.
- Cada escenario se ordena primero por evidencia frente a la prevalencia y
  después por Brier. Se muestran `n_test`, ausencia de ambas clases y casos no
  evaluables; es un ranking diagnóstico, no una promoción.
- Cada artefacto comparativo conserva soporte min/max/media/desviación de sus
  variables. La inferencia informa cuántas quedan fuera del dominio observado y
  las cinco extrapolaciones más extremas. El porcentaje no debe interpretarse
  como fiable cuando la aplicabilidad es mala.
- Las tarjetas por versión muestran rango de probabilidades (nunca una media),
  desacuerdo, evidencia hold-out y cautelas específicas de V2--V6. Debajo se
  presenta el mismo desglose para todas las versiones: filas por
  perfil+contrato+horizonte y columnas por algoritmo, con predicción actual,
  evidencia hold-out frente a prevalencia y aplicabilidad de dominio.
- La tarjeta principal aclara que muestra V2 solo por herencia cronológica, no
  porque V2 sea el Predictor preferido o haya ganado la comparación.
- Al cambiar de especie en `Consultar fecha` se limpia siempre el área anterior.
  El servicio normaliza además cualquier pareja especie+área no observada a
  `todas las áreas`, y el render no puede mostrar un resultado para una pareja
  incompatible. Nunca debe reaparecer un área de la especie anterior por URL,
  respuesta preparada o caché.
- Lote instalado: `local_v2_v6_20260816T192516Z`, snapshot canónico
  `sha256:1ac18a...f9037a9`, 922 ajustes planificados, 489 disponibles y 433 no
  entrenables. `active=false` y `operational_candidate_trained=false`.
- El lote tardó 2 min 38 s de extremo a extremo. La primera predicción remota
  completa transfirió 78.642.346 bytes y sincronizó la caché; la repetición con
  V2--V6 conservó las cinco selecciones, reutilizó caché y transfirió 0 bytes.
- Validación visual estructural remota: cinco tarjetas de versión, cinco
  rankings (`fixed-h7`, `lag-h1/h2/h3/h7`), las cinco casillas seleccionadas,
  cautelas, evidencia hold-out y aplicabilidad de dominio. El selector se ha
  corregido a una rejilla adaptable con checkboxes compactos.
- Validación final local: 845/845 pruebas superadas con las imágenes finales.
  La reproducción remota de `Aereus` con el área incompatible `Molló` se
  normaliza a `todas las áreas`, no conserva la opción inválida y no renderiza
  `Aereus/Molló`. Una consulta válida `Aereus/Olvan` termina correctamente y
  muestra los cinco desgloses V2--V6 por contrato y algoritmo, con evidencia
  hold-out y aplicabilidad de dominio. HA responde y el worker está sano.

## Artefactos de release preparados el 2026-08-17

- HA `0.2.256` y `latest` están publicados en
  `ghcr.io/cginebrosa/rainmapperha` con el mismo índice OCI
  `sha256:880c2edb4a384f0e3585d9bb9c82417e988a8d2c48799f5aab2a2c7548e86665`.
  Se verificaron los manifiestos `linux/amd64`
  `sha256:aba74127fe736b439b6941f6e786898a6bd702c1c82ca6487cfecec3e7224443`
  y `linux/arm64`
  `sha256:ee203b3579e1095beaa38de367db1c34b0c1851a190f9ddbff291fef2c80cb6c`.
- Worker `1.0.10`: imagen privada `linux/arm64`, etiqueta OCI y variable de
  entorno `1.0.10`, digest local
  `sha256:b56d68e5de63b90b120155ab23554390a8e40e6102798c4bb1fd4df18872fdd4`.
  El paquete está en `~/Desktop/RainmapperWorker-1.0.10/`; su TAR ocupa 294 MB
  y tiene SHA-256
  `b582120db939a6e5823095b243430119d5cd993d94b57dc0c7962d93d3da2de2`.
  El paquete anterior del Escritorio no se sobrescribió.
- El smoke previo a publicación superó 845 pruebas, compilación, validadores y
  `git diff --check`. El TAR superó su checksum, el Compose se normalizó sin
  errores y un contenedor efímero importó servicio y registro multiversión.
- Ningún host real se ha actualizado todavía y no se ha lanzado regeneración.

## Riesgos y dudas activas

- El Predictor local ya está alineado con la reconstrucción promovida. El
  manifiesto multiversión aumenta el runtime hasta unos 129 MiB/545 ficheros;
  la primera sincronización puede ser lenta, pero las siguientes deben usar
  caché y transferir 0 bytes.
- El soporte por especie es pequeño. Dos revisiones cambiaron ganadores y
  `boletus_edulis` pierde una partición evaluable. Toda conclusión es provisional.
- V5 raw pierde 32/34 comparaciones contra el mejor miembro actual y su
  selección es demasiado densa. Mantenerlo experimental; no usarlo para
  desbloquear una versión HA o decidir el Predictor.
- Los cuatro horizontes lag reutilizan observaciones; nunca contarlos como
  muestras independientes ni entrenar un modelo distinto por horizonte.
- La continuidad física de una florada no autoriza suavizar etiquetas. Solo hay
  unas 50 etiquetas semanales útiles para aprender estado; no inventar reglas.
- El balance V4 ayuda a continuidad pero no al Brier de forma general; SoilGrids
  empeora habitualmente. Conservar ambos, documentar y mantener desactivados.
- El histórico reparado y la autocuración están solo en local. Los runners de HA
  siguen avanzando, por lo que una promoción futura exige rebase fresco.
- `0.2.255` y worker `1.0.9` son artefactos obsoletos para esta integración.
- El worktree es grande y mixto. Revisar por alcance antes de cualquier commit;
  no eliminar ficheros no rastreados ni asumir que todos pertenecen al último
  bloque.

## Archivos relevantes

- Arranque y prioridades: `docs/codex-start-here.md`, `docs/todo.md`.
- Decisiones: `docs/decisions.md`.
- Arquitectura: `docs/architecture.md`.
- Informe V4: `docs/reports/V4_report001.md`.
- Consenso canónico: `docs/reports/V2_V3_V4_consensus_report002.md`.
- Genealogía y ciclo de vida:
  `docs/mushrooms/mushroom-ml-contract-versions-es.md` y
  `docs/mushrooms/mushroom-ml-version-lifecycle-es.md`.
- Especificaciones V3/V4:
  `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md` y
  `docs/mushrooms/mushroom-ml-biology-v4-implementation-spec-es.md`.
- Caché SoilGrids:
  `docs/mushrooms/biology-v4-soilgrids-cache-contract-es.md`.
- Núcleo meteorológico: `rainmapper_core/mushroom_weather_idw.py`.
- Constructores/evaluador: `rainmapper_core/mushroom_ml_biology_v3.py`,
  `rainmapper_core/mushroom_ml_biology_v4.py` y
  `rainmapper_core/mushroom_ml_biology_v3_evaluation.py`.
- Scripts: `scripts/build-biology-v3-benchmark.py`,
  `scripts/build-biology-v4-benchmark.py` y
  `scripts/evaluate-biology-v2-v3-v4.py`.
- Autocuración oficial: `rainmapper_core/weather_official_repair_state.py`,
  `rainmapper_core/weather_official_maintenance.py` y
  `scripts/repair-official-weather-history.py`.

## Reglas para la continuación

- Leer primero `docs/codex-start-here.md` y este documento; consultar
  `docs/todo.md` solo para prioridades completas.
- Consultar MCP Codebase sin pedir permiso. Responder siempre a comentarios del
  usuario mientras continúa el trabajo.
- No usar Tailscale; HA está accesible mediante shares SMB montados.
- Preservar todos los cambios locales. No usar comandos destructivos.
- La prueba local ya promovió una generación V2 solicitada por el usuario. No
  modificar HA/worker reales, releases o GHCR sin autorización explícita; el
  lote V2--V6 nunca se promueve como operativo.

## Validación habitual

```bash
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Una release exige además `docs/release-flow.md` y sus comprobaciones completas.
