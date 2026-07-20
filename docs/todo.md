# TODO

Nota operativa: ejecutar tareas, tests y commits solo desde `/Users/carlosginebrosa/Developer/RainmapperHA`. No usar la copia antigua de iCloud/Mobile Documents.

Regla critica de release HA: cuando se prepare una version para que el usuario la pruebe en Home Assistant, el objetivo es desbloquear la prueba en HA cuanto antes sin dejar el repo incoherente. Orden operativo actual: revisar diff, ejecutar validacion local relevante, hacer bump de version/cache-busters, publicar y verificar la imagen `ghcr.io/cginebrosa/rainmapperha:<version>`, hacer commit/push inmediatamente y avisar al usuario. No retrasar la prueba por hashes en documentacion o cierre de continuidad; la documentacion viva se actualiza despues del release o en cierre de sesion.

Regla operativa de permisos: si el usuario pide explicitamente subir a Git o publicar una version HA, revisar primero estado/diff y validaciones necesarias; despues usar directamente permisos elevados para `git commit`, `git push`, build/push GHCR o comandos de red necesarios, evitando el intento normal que falla por sandbox.

Regla operativa GHCR: para listar o borrar versiones remotas de GitHub Packages/GHCR usar explicitamente la variable de entorno `GH_TOKEN`; no usar `git credential fill`/osxkeychain para la API de Packages porque puede devolver una credencial valida para `git push` pero sin permisos suficientes de Packages. Mantener siempre la version HA actual, `latest` y al menos el rollback inmediato antes de borrar versiones antiguas.

Regla critica del motor predictivo de setas: Codex no debe fijar umbrales, pesos, ventanas meteorologicas especificas por especie ni parametros del motor por intuicion o por extrapolacion no documentada. Cada valor predictivo debe estar soportado por evidencia documental verificable, codigo fuente real o por observaciones locales trazables en `mushroom_observations.json`. Si una fuente solo permite una deduccion general, documentarla como hipotesis de diseno y mantenerla fuera del motor numerico hasta validarla. Si Codex no ha podido leer el contenido real de una fuente, no puede usarla como soporte de un valor ni afirmar que la fuente dice algo concreto.

Regla UI setas 2026-07-04: la UI debe ser coherente con el resto de Rainmapper, usable para una persona y multiidioma. Cualquier texto visible nuevo del dominio setas debe tener labels en `mushroom-data/mushroom_labels.json` para `en`, `es` y `ca`. Las pantallas tecnicas crudas solo se aceptan si el usuario lo pide explicitamente.

## Estado operativo actual (2026-07-20)

### Prioridad inmediata

- [x] Validar localmente los recuentos derivados de `prediction_favorable`: 126
  features = 66 favorables/60 desfavorables, 0 discrepancias y 0 politicas
  desconocidas; el modelo usa 125 = 65/60 porque una observacion favorable esta
  en borrador. Queda como comprobacion opcional repetir la inspeccion en HA.
- [x] Revisar y consolidar el diff local completo del worker externo antes de
  versionarlo: autenticacion fail-closed, modo operacional condicionado a
  API+auth, paths de snapshots/GIS confinados, huella del manifest revalidada,
  JSON del protocolo acotado, paths privados rebasados en promocion y exclusion
  de `docker-data`/GIS comprobada en el empaquetado fuente. El coordinador se
  empaqueta sin habilitarse en HA y el pipeline HA sigue en `legacy` por
  defecto. Suite: 369 tests; validador: 0 errores/11 warnings conocidos.
- [x] Definir el alcance de una version HA normal que incorpore el coordinador
  y la UI: web/Ingress en `8099`, protocolo privado dedicado en `8100` sin
  publicacion host por defecto, autenticacion obligatoria y dos opciones HA
  separadas (`Enable external worker connections` y
  `Allow external rebuilds and promotion`), ambas apagadas por defecto. Los
  controles humanos del worker en la web exigen Ingress autenticado; el
  laboratorio permite explicitamente el acceso local. `--clear-token` elimina
  ahora la credencial sin necesitar que el coordinador responda. La separacion
  se valido con una sonda desde el contenedor worker real y el puerto `8100` no
  se publico en el Mac. El proceso worker antiguo no se reinicio para conservar
  sus jobs; sigue apuntando en memoria a `:8099` hasta que el launcher aplique
  la migracion preparada en su proximo arranque.
- [x] Inspeccionar el empaquetado local construido con el Dockerfile HA normal:
  contiene coordinador/UI/core y solo los assets `mushroom-data` ya
  versionados; no contiene `docker-data`, GIS/DEM, credenciales ni configuracion
  persistente del worker. La imagen worker tampoco contiene datasets. El
  fallback HA permanece en `legacy` por defecto. Smoke test completo: 369
  tests; validador: 0 errores/11 warnings conocidos.
- [x] Publicar con autorizacion expresa la version HA normal `0.2.208`:
  `0.2.208/latest` verificadas para amd64/arm64 con digest
  `sha256:68990c43959f31a9364b18aed2c053ef2487385d283251ba6c72302a166552ab`;
  import check correcto con conexiones/rebuilds `False`; commit `e2f117d`
  pusheado a `origin/inicial`. No se creo una imagen HA de desarrollo.
- [x] Instalar `0.2.208` en HA y confirmar arranque normal, opciones externas
  apagadas y reconstruccion HA local disponible antes de conectar el M1.
- [x] Publicar `8100` solo en LAN, activar conexiones externas, emparejar M1 y
  completar la prueba inocua de asignacion contra HA real en 13 s.
- [x] Publicar, con autorizacion expresa, la correccion `0.2.209` del refresco
  de Workers bajo Ingress y del resumen acumulativo de publicaciones
  programadas. `0.2.209/latest` comparten digest
  `sha256:cccf90938697f310476e5962f7165e0a3833a5ddc589d517670c70adbccec77b`;
  commit `4861dbb`; import check arm64 correcto con ambos flags en `False`.
- [x] Instalar `0.2.209` y aislar el comportamiento contra HA real: reposo,
  pagina Workers y asignacion estables; una prueba de entradas termina y
  devuelve la CPU a la normalidad, pero los clics repetidos lanzaban hashes
  concurrentes sobre 5,87 GiB y podian provocar watchdogs y salidas 137.
- [x] Publicar, con autorizacion expresa, `0.2.210`: preparacion de entradas en
  segundo plano, exclusion inmediata de duplicados, boton protegido, polling
  estable y cache privada de hashes GIS con invalidacion por fichero.
  `0.2.210/latest` comparten digest
  `sha256:a64644929735eef53ce254a99f303161c050f876459819a4455ce6bcd299bd23`;
  commit `6521245`; import check arm64
  `image_import_ok 0.2.210 False False True`; 374 tests y smoke test OK.
- [x] Instalar `0.2.210` y comprobar la preparacion en segundo plano y la
  finalizacion correcta de asignacion/envio. Se detecto que los mensajes flash
  de preparacion o conflicto quedaban visibles despues de terminar el trabajo.
- [x] Publicar, con autorizacion expresa, `0.2.211`: los avisos de actividad se
  refrescan con la cola y desaparecen al quedar inactiva, sin ocultar errores
  reales. `0.2.211/latest` comparten digest
  `sha256:0c7ed3477c904ba872f2ccc94109caf0e82a438675e9631e0784a57a488fc86b`;
  commit `74f1313`; import check arm64
  `image_import_ok 0.2.211 False False True`; 376 tests y smoke test OK.
- [x] Instalar `0.2.211` y comprobar reposo, asignacion, envio de entradas y
  conflicto por trabajo activo; los avisos transitorios desaparecen al terminar
  y los errores reales permanecen visibles.
- [ ] Incorporar mas observaciones historicas reales de `Boletus pinophilus`
  de distintos anos y setales, conservando procedencia y calidad.
- [ ] Revisar cobertura temporal/espacial y retomar el pipeline ML documentado en
  `docs/mushrooms/mushroom-ml-training-plan-es.md`.
- [ ] Comprobar cuando convenga que cancelar aborta una carga activa y que el
  Quick viewer MapLibre abre `rainmap.nomentero.com`.

### Plataforma de computo externo HA + M1

El prototipo local esta completo y esta linea vuelve a ser prioridad. Antes de
tocarla, leer `docs/mushrooms/mushroom-v0-external-worker-design-es.md`.

Orden obligatorio: revisar/consolidar local; preparar una version HA normal;
pedir autorizacion expresa; publicar/instalar; y solo despues probar M1 ↔ HA
real. La topologia Tailscale puede estudiarse antes, pero no puede validarse el
flujo funcional contra `0.2.207` porque no contiene el coordinador.

- [x] Documentar arquitectura general para reconstruccion, dataset,
  entrenamiento y evaluacion ML; protocolo outbound, Docker privado,
  Tailscale, seguridad, consistencia, fases y criterios de aceptacion.
- [x] Fijar HA + M1 como primera topologia. M5 y una posible VM en AWS quedan
  como destinos futuros, no como requisitos iniciales.
- [ ] Medir las cuatro fases de reconstruccion en HA y M1, el tamano de
  inputs/outputs vivos y el coste separado de dataset/baseline ML. Primer run
  M1 aislado del 2026-07-19: GIS/DEM 97,857 s, meteo 14,342 s, features 0,022 s,
  modelo 0,021 s y total 112,244 s; output 1,9 MB. Repeticion desde snapshot:
  102,407 s, 14,286 s, 0,021 s, 0,013 s y total 116,728 s. Faltan fases HA y
  costes ML. Las fases HA compartidas se mediran despues de instalar la version
  normal que incorpore el coordinador/pipeline; no mediante una imagen de
  desarrollo.
- [x] Extraer de `web_server.py` un pipeline comun en `rainmapper_core` sin
  cambiar el comportamiento de la reconstruccion HA y haciendo explicitas las
  rutas de entrada/salida. Existe ya el prototipo local
  `mushroom_rebuild_pipeline.py`, el CLI aislado y el adaptador opt-in
  `RAINMAPPER_MUSHROOM_REBUILD_PIPELINE=shared`. La imagen HA local aislada
  completo el job compartido en unos 41,7 s con 9/9 artefactos equivalentes;
  fallos en las cuatro fases, rollback de promocion y cancelacion estan
  cubiertos. El release HA sigue en `legacy`; decidir el cambio de default y su
  release es una tarea posterior y explicita.
- [x] Probar publicacion transaccional, fallos y cancelacion del adaptador HA
  compartido. Los nueve artefactos se generan en staging y se promocionan como
  unidad con rollback; un fallo real al entrar en Meteorologia despues de
  GIS/DEM y una cancelacion real al 1 % de GIS/DEM conservaron 9/9 artefactos y
  limpiaron temporales. Suite completa: 264 tests.
- [x] Definir contratos versionados `JobSpec`, `InputManifest` y
  `ResultManifest`; validar con un CLI local que el mismo snapshot produce
  resultados equivalentes. `InputManifest 0.1`, snapshot privado y comparador
  normalizado ya probados: 7 archivos vivos/meteo copiados, 10 GIS externos
  fijados por hash y 9/9 artefactos equivalentes contra HA `0.2.207`.
  `JobSpec 0.1` fija snapshot, GIS, alcance y salidas; `ResultManifest 0.1`
  verifica hashes, tamanos y contadores derivados. Run real contractual:
  114,671 s, 125/126/126/14 y 9/9 validos. Cambios controlados de spec y
  artefacto fueron rechazados. Suite completa: 269 tests.
- [x] Crear un arnes HA local que no pueda montar `docker-data` por defecto:
  Compose/servicio/puerto propios, runtime obligatorio bajo `/private/tmp`, GIS
  read-only, schedule y descargas desactivados. Validado con HTTP 200,
  Python 3.11.15/aarch64 y reconstruccion compartida completa.
- [x] Crear una imagen worker ligera y privada, sin GIS/DEM, y ejecutarla en el
  M1 sin GHCR: `rainmapper-worker:local-contract-test`, arm64, 151.477.088
  bytes, sin red, datos ni WebUI. Run contractual completo en 42,130 s,
  125/126/126/14 y 9/9 equivalente; usuario no-root y volumen persistente
  conservado/verificado desde un segundo contenedor.
- [x] Probar roundtrip local `docker save`/`docker load`: TAR privado de
  151.497.216 bytes, SHA-256
  `69a266478efdcdb45cb4e19afa928c5a10e917bb81a6745e9806bea4545829c2`;
  etiqueta restaurada con el mismo image ID/arquitectura/tamano y arranque
  `--pull never` contra `rainmapper-worker-data`, 9/9 valido. Falta repetir en
  daemon limpio u otro host porque la etiqueta original conservo las capas.
  Metricas: TAR 151,5 MB, `docker image inspect` 151,5 MB y almacenamiento local
  mostrado por `docker images` 616 MB. Suite completa actual: 272 tests.
- [x] Crear la base interactiva portable del worker: pedir/validar URL de HA,
  nombre y pairing, persistir identidad/configuracion y arrancar el Compose
  generico sin exigir edicion manual de `.env`. `mushroom_worker_start.sh`
  incluye `--help`, prompts autoexplicativos y modo no interactivo. Queda
  probarla en otro host y, si se elige, integrar Tailscale. Si se adopta
  Tailscale dentro de Docker, incluir en el mismo instalador su alta
  interactiva, volumen de estado y prueba de conectividad con HA.
- [x] Anadir control manual local del servicio headless mediante
  `mushroom_worker_start.sh`/`mushroom_worker_stop.sh`. El worker queda accesible
  solo en `127.0.0.1:8110`, informa `idle` y cache GIS valida, corre como UID
  10001 y se detiene con codigo 0 conservando `rainmapper-worker-data`. El
  endpoint es diagnostico JSON; no es UI ni implementa aun la API de jobs.
  Suite completa: 281 tests.
- [x] Anadir la primera pantalla local `Workers y trabajos` y una red Docker
  privada compartida. La UI detecta el health real, muestra HA/worker, cache,
  alcances e historial de jobs, permite reconstruir mediante el launcher HA
  existente y deshabilita honestamente el destino externo mientras anuncie
  `job_api: not_implemented`. Se probaron conectado/desconectado con HTTP 200;
  quedan ambos contenedores encendidos y exactamente dos imagenes. Suite
  Tras corregir el solapamiento de los radios, destino y alcance usan tarjetas
  seleccionables y el selector de especie solo aparece para ese alcance. Suite
  completa de esa iteracion: 289 tests.
- [x] Implementar identidad y registro local multi-worker: `worker_id`, nombre
  visible y maquina fisica persistidos en `rainmapper-worker-data`; heartbeat
  saliente a un registro de HA/UI habilitado solo en el Compose local; tarjetas
  y destinos generados desde una coleccion. El M1 se registro con el nombre
  fisico detectado; su ID opaco se conservo tras recrear el contenedor y no se
  versiona. El script admite `--name` para renombrarlo sin `.env`.
  No interviene Tailscale ni HA real. Suite completa: 296 tests.
- [x] Implementar la primera cola/claim local no destructiva. La UI encola un
  `worker_claim_probe` persistente para un `worker_id` exacto; el worker lo
  reclama outbound despues del heartbeat y la tabla muestra tipo, destino y
  `En cola`/`Reclamado`. Otro worker no puede reclamarlo, no se entrega dos
  veces y un job en cola sobrevivio al apagado/recreacion del contenedor. No
  ejecuta reconstruccion ni modifica el modelo. API solo local y aun sin
  autenticacion. Suite completa: 301 tests.
- [x] Hacer portable la seleccion del coordinador. El Compose ya no fija
  `RAINMAPPER_HA_URL`; el arranque ofrece `--help`, parametros de nombre/URL,
  token seguro y modo no interactivo, recupera configuracion del volumen y
  valida `/api/mushrooms/workers/ping` antes de guardarla. Si falta o no es
  accesible, guia para reintentar/cambiar/cancelar; un destino invalido no
  sustituye al valido. Primer arranque, reutilizacion sin parametros y claim
  posterior probados. El launcher del laboratorio imprime separadamente URL de
  UI y URL interna del worker. Suite completa: 306 tests.
- [x] Refrescar automaticamente disponibilidad e historial del worker. La UI
  consulta un endpoint ligero cada 2 s y reemplaza solo tarjetas, destinos y
  trabajos, conservando el formulario. Heartbeat cada 2 s, caducidad a 5 s y
  comprobacion inmediata al volver a la pestana. Parada real detectada en 3,25
  s; sin escrituras de metadata para heartbeats sin cambios. Suite: 308 tests.
- [x] Completar el ciclo persistente del probe: lease/token, inicio, `busy`,
  control, finalizacion, cancelacion cooperativa y forzada mediante subproceso,
  reasignacion solo antes de empezar y exclusion global de trabajo equivalente
  por `work_key`. Pruebas reales: duplicado rechazado, cancelacion normal,
  cancelacion forzada y finalizacion; sin modificar datos/modelo. Suite: 317.
- [x] Autenticar el protocolo local mediante pairing. La UI genera un unico
  codigo temporal activo de 10 minutos/uso unico; el launcher lo recibe por
  stdin o prompt oculto, persiste el token solo en el volumen y HA almacena
  unicamente SHA-256. Heartbeat y todas las rutas de jobs rechazan sin token; la
  UI muestra estado y permite revocar. Pairing, ciclo autenticado y reinicio sin
  nuevo codigo probados realmente. Suite: 325 tests.
- [x] Entregar localmente `JobSpec 0.1` y snapshot vivo por HTTP autenticado.
  `Probar envio de entradas` congela un bundle privado, el worker lo reclama
  outbound, exige Bearer + identidad + claim, descarga solo paths declarados,
  valida limites/tamanos/SHA-256 y activa atomicamente sus inputs persistentes.
  Prueba real: 7 ficheros y 111.031.244 bytes, cache GIS exacta reutilizada,
  estado final `Input bundle verified`, sin pipeline ni artefactos/modelo
  modificados. UI y worker quedan encendidos. Suite: 329 tests.
- [x] Crear la base local del volumen persistente versionado para datasets
  pesados: manifest, sincronizacion inicial desde fuente read-only, staging,
  hashes durante copia, activacion atomica y conservacion segura de la version
  anterior. `mushroom_gis_v0` sincronizo 10 ficheros/6.306.367.027 bytes,
  supero verificacion profunda y despues se reutilizo sin recopia. Un rebuild
  sin montar GIS del host termino en 42,033 s, 125/126/126/14 y 9/9
  equivalente. Fallos sinteticos preservan `current` y limpian staging. Suite
  completa: 278 tests.
- [x] Conectar la cache GIS al transporte HA. El coordinador sirve solo los
  paths declarados bajo Bearer/worker/claim; el worker compara el contrato,
  comprueba espacio, descarga directamente a staging, valida tamano/SHA-256 y
  activa atomicamente solo si falta o cambia la huella. Tests sinteticos cubren
  primera carga, reutilizacion sin GET, actualizacion, fallo preservando
  `current` y espacio insuficiente. Prueba real del 2026-07-20: cache existente
  de 10 ficheros/6.306.367.027 bytes reutilizada con
  `dataset_transferred_size_bytes: 0`. En esa iteracion aun no se habia hecho
  una transferencia real de 6,3 GB a un volumen nuevo; la prueba posterior se
  documenta en los puntos siguientes. Suite historica: 340 tests.
- [ ] Repetir portabilidad en un daemon limpio u otro host y comprobar alli que
  reemplazar la imagen conserva el volumen. En el M1 ya se ha probado un
  volumen completamente vacio: sincronizo 10 ficheros/6.306.367.027 bytes,
  supero verificacion profunda y el segundo job reutilizo la cache con cero
  bytes. El volumen aislado se conserva y su contenedor temporal esta detenido.
- [x] Completar el protocolo outbound sobre el snapshot ya entregado y
  verificado: `worker_candidate_rebuild` ejecuta el pipeline compartido en un
  area candidata privada y cancelable, publica progreso, sube por canal
  autenticado `ResultManifest` y nueve artefactos, y Rainmapper verifica
  contrato/rutas/tamanos/SHA-256/contadores antes de compararlos. Prueba real
  local del 2026-07-20: 7 inputs/111.031.244 bytes, cache GIS persistente
  reutilizada, 9/9 artefactos verificados y `equivalent`; las nueve huellas del
  modelo vivo no cambiaron. Ese primer candidato quedo privado (~2,0 MB), sin
  promocion automatica, y en esa iteracion el selector externo seguia
  deshabilitado. La tabla de
  trabajos muestra fecha/hora local y duracion calculada. Suite: 335 tests;
  validador: 0 errores/11 warnings conocidos.
- [ ] Comparar Tailscale del host con sidecar dentro de Docker usando la URL
  fija de HA, tokens/ACL e identidad propia por despliegue; no asumir que un
  contenedor evita las politicas de un Mac de trabajo.
- [x] Habilitar solo en el laboratorio local el destino externo operativo para
  una reconstruccion completa, despues de probar descarga GIS real a volumen
  vacio, cancelacion cooperativa/forzada, corte y recuperacion de red, rechazo
  de corrupcion/freshness y promocion atomica con rollback. El job operativo
  local termino en 49 s, fue 9/9 equivalente, mantuvo intacto el modelo hasta
  la promocion y conservo copia de los nueve artefactos anteriores. El flag
  `RAINMAPPER_WORKER_OPERATIONAL_ENABLED` solo esta activo en el Compose local;
  default y release HA permanecen deshabilitados. Las copias de promocion se
  limitan automaticamente a las dos mas recientes y no contienen GIS/DEM.
  Suite: 348 tests; validador: 0 errores/11 warnings conocidos.
- [x] Centralizar todos los lanzamientos visibles de reconstruccion en
  `Workers y trabajos`. El aviso `Modelo V0 desactualizado`, las acciones de
  modelo aprendido y el antiguo laboratorio GIS de Observaciones ya abren esa
  pagina con `pendientes`, `todas` o `una especie` preseleccionados y no arrancan
  trabajos por su cuenta. El ejecutor predeterminado se guarda en el registro
  privado como HA o `worker:<id>` exacto; si esta apagado/incompatible no hay
  fallback silencioso. `Una especie` sigue operativa en HA. La
  cabecera usa la misma barra superior compacta de acciones que el resto de
  pantallas. Revocar un worker elimina su credencial, heartbeat, registro,
  tarjeta y selector; si era el predeterminado se restablece HA. Suite: 356
  tests.
- [x] Implementar y validar en el worker externo local los alcances
  `pendientes` y `una especie`. El JobSpec transporta los IDs exactos de
  observacion/especie; la promocion mezcla solo esas filas/modelos con las
  nueve salidas vigentes antes de sustituirlas atomicamente. Las claves de
  trabajo impiden alcances activos solapados, pero permiten especies disjuntas
  en workers distintos. Pruebas reales: `una especie` y `pendientes` con una
  observacion se completaron y promocionaron; las otras 13 especies conservaron
  exactamente sus hashes. Un segundo job `pendientes` se cancelo durante
  Meteorologia al 55 % sin promocion. El estado pendiente se limpio solo tras
  la promocion correcta; la retencion podo la tercera copia y mantuvo dos.
  Suite: 359 tests; validador: 0 errores/11 warnings conocidos.
- [x] Publicar la version HA normal `0.2.208` con coordinador, pairing, UI,
  transporte y fallback HA, desactivada por defecto. Imagen multi-arch y
  commit/push verificados.
- [x] Instalar `0.2.208` en HA, verificar el fallback local, publicar `8100`
  solo en LAN, emparejar M1 y completar la prueba de asignacion en 13 s.
- [ ] Completar la ruta operativa M1 ↔ HA real por LAN/Tailscale. `0.2.211` ya
  esta instalada y se validaron reposo, asignacion, transporte de entradas,
  avisos, un candidato privado completo de 55 s y un job operacional completo
  de 49 s. Este ultimo fue verificado y promocionado manualmente con exito al
  modelo vivo, conservando la copia anterior. Faltan reconstruccion parcial,
  desconexion/reconexion, cancelacion, seguridad del endpoint, cache y
  freshness.
- [x] Implementar localmente progreso visible de promocion. El POST devuelve
  inmediatamente, la tarea continua en segundo plano, persiste fases/porcentaje
  y el polling muestra una barra en trabajos recientes; el estado `promoting`
  bloquea clics duplicados. Mantiene la revalidacion fail-closed de hashes GIS,
  la promocion atomica y el rollback.
- [x] Publicar con autorizacion expresa `0.2.212` y `latest`, digest multi-arch
  `sha256:9c7f70518ddd368ed42a67819df226a27e1726e7958e7b5309e02e810b326c8e`;
  manifests amd64/arm64 e import check
  `image_import_ok 0.2.212 False False True` verificados; 378 tests y smoke test
  OK. Instalada y comprobada la barra en HA real.
- [x] Implementar localmente descarte confirmado de candidatos terminales no
  promocionados. El modal explica el alcance destructivo; HA borra snapshot y
  resultado privados y mantiene un tombstone hasta que el worker elimina y
  acusa su directorio de job por heartbeat. No toca modelo vivo, rollback ni
  cache GIS/DEM; bloquea promociones activas y conserva cualquier artefacto de
  recuperacion dudoso. Suite completa: 386 tests; validador: 0 errores/11
  warnings conocidos. Publicado en `0.2.213`; falta reiniciar/reconstruir el
  worker y probarlo con un candidato terminal no promocionado.
- [x] Compactar localmente `Workers y trabajos` para HA + dos workers: tres
  tarjetas y tres destinos por fila en escritorio, herramientas tecnicas
  plegadas, titulo/subtitulo en una linea y retirada del acceso azul que solo
  desplazaba al formulario y de los textos redundantes de cabecera. La tabla
  ordena por cualquiera de sus columnas, usa instantes UTC al mezclar fechas y
  muestra `HA local` en lugar del ID aleatorio. Se retira tambien de
  Observaciones el desplegable GIS heredado, porque no identificaba un job y
  podia quedar vacio. Publicado en `0.2.213`, pendiente de instalar/probar.
- [x] Publicar con autorizacion expresa `0.2.213` y `latest`: digest multi-arch
  `sha256:d1380a800131986b6efefbbb3ad234b252086f4e802de90aed42f905ac9dc4dd`,
  manifests amd64/arm64 e import check
  `image_import_ok 0.2.213 False False True` verificados; smoke con 386 tests y
  validador 0 errores/11 warnings. Pendiente de instalar y probar en HA real.
- [ ] Medir las fases en HA con el pipeline/instrumentacion compartidos y
  comparar con M1 usando exactamente el mismo snapshot/dataset.
- [ ] Incorporar jobs separados `build_ml_dataset`, `train_ml_model` y
  `evaluate_ml_model`, reutilizando `dataset_id` y sin promocion automatica.
- [ ] Disenar, cuando existan varios algoritmos predictivos, un registro de
  modelos separado de los backups de promocion. Debe conservar algoritmo,
  parametros, codigo/contratos, snapshot y `dataset_id`, artefactos, metricas
  globales y por especie y estado (`candidate`, `active`, `archived` o
  `rejected`). La comparacion debe usar la misma validacion espacial/temporal y
  varias metricas, no un score opaco unico; activar o recuperar una version
  sera una seleccion humana explicita sin reutilizar como catalogo las dos
  copias de emergencia actuales.
- [ ] Cuando exista necesidad real, evaluar M5 o AWS repitiendo pruebas de
  arquitectura, red, privacidad, rendimiento y coste.

### Completado en el release 0.2.204

- [x] Habilitar `ingress_stream` y aceptar multipart tradicional o fragmentado
  manteniendo los limites de 100 MB por archivo y 500 MB por lote.
- [x] Mostrar porcentaje real durante la subida y estado indeterminado durante
  EXIF, generacion de preview y conversion FFmpeg; abortar cargas activas.
- [x] Corregir el Quick viewer MapLibre a `rainmap.nomentero.com`.
- [x] Ejecutar 236 tests y publicar/verificar `0.2.204`/`latest` para amd64 y
  arm64 con digest `sha256:ceaed487b93eb5a680b882a16caa6d4062dd038c53f6d2268e59f0903897e8c8`.
- [x] Validar `0.2.204` en HA con un video de 30,4 MB: subida, preview,
  asociacion y guardado totalmente funcionales; conversion FFmpeg en 5-10 s.

### Publicado en el release 0.2.205

- [x] Paginar observaciones en servidor, mostrar Area/Microarea por nombre y
  actualizar solo el panel de detalle al seleccionar una fila.
- [x] Mantener cargada la lista de especies y sustituir asincronamente solo el
  editor derecho, conservando vista, pestana, historial y nombres comunes.
- [x] Mantener el arbol de setales al cambiar de seleccion, regenerar solo
  editor/mapa y eliminar el salto inicial desde la ubicacion predeterminada.
- [x] Sustituir el meta-refresh del Control Panel por polling cada cinco
  segundos con firma de contenido, conservando pestana y scroll.
- [x] Ejecutar 244 tests y publicar/verificar `0.2.205`/`latest` para amd64 y
  arm64 con digest `sha256:a8eb573e809a49d172c4cc16ab9b73f511df575112d24d8883c76d02620aed9b`.
- [ ] Validacion de `0.2.205` sustituida por la prueba de `0.2.206`.

### Publicado en el release 0.2.206

- [x] Incorporar un selector de fechas con calendario y navegacion directa por
  mes y ano, manteniendo campos compactos y fechas visibles.
- [x] Compactar la lista y el detalle de observaciones, ampliar la miniatura y
  simplificar etiquetas para ganar espacio util.
- [x] Reorganizar estados e indicadores de especies, ampliar nombres y compactar
  verticalmente el editor sin reducir tipografias.
- [x] Homogeneizar las barras de acciones de las pantallas de mantenimiento y
  corregir el cierre prematuro de la confirmacion para desasociar medios.
- [x] Ejecutar 244 tests y publicar/verificar `0.2.206`/`latest` para amd64 y
  arm64 con digest `sha256:47da2be9cdfce2698f2d4825e7b25be50aabf1dddb355693846ff5f56343ef17`.
- [ ] Validacion de `0.2.206` sustituida por la prueba de `0.2.207`.

### Publicado en el release 0.2.207

- [x] Derivar el objetivo V0 favorable/desfavorable desde
  `prediction_favorable` en el catalogo de abundancia, sin migrar observaciones.
- [x] Hacer operativos los rebuilds de una especie y de todas mediante el job
  en background y el modal de progreso cancelable.
- [x] Informar progreso incremental en GIS/DEM, meteorologia, generacion de
  features y reconstruccion del modelo aprendido.
- [x] Compactar y localizar las pantallas de observaciones, especies, evidencia,
  parametros y calibracion, evitando IDs tecnicos en la interfaz funcional.
- [x] Ejecutar 250 tests y publicar/verificar `0.2.207`/`latest` para amd64 y
  arm64 con digest `sha256:a2047d39c8534c9d8e1a0066a5ff903e49733a0a98015fdb731081bf26af6781`.
- [x] Ejecutar `Reconstruir todas` en HA: las cuatro fases completan en 4 min
  44 s y el job/progreso en background quedan funcionalmente comprobados.
- [ ] Comprobar explicitamente los recuentos y casos de
  favorable/desfavorable producidos por el catalogo actualizado.

### Completado en el cierre 0.2.202

- [x] Implementar `HEAD` y rangos HTTP de un solo intervalo en media privada de
  observaciones, incluidos `206` y `416`.
- [x] Declarar `<source type="video/mp4">`, `playsinline` y poster en el visor.
- [x] Validar localmente un rango real sobre el MP4 asociado y ejecutar 229
  tests, validador de datos (0 errores, 11 warnings) y `git diff --check`.
- [x] Revisar `requirements.txt`: no requiere cambios; FFmpeg y ExifTool siguen
  correctamente instalados como paquetes del sistema en el Dockerfile.
- [x] Publicar HA `0.2.202` y `latest` para amd64/arm64 con digest
  `sha256:3ee510ee50793e252bbe5a6c05f722567da758f374d865ebd96a272c259ee7ed`.

### Release meteorologico estable

- [x] Publicar HA `0.2.194`: Wunderground pasa a API diaria JSON como fuente primaria con fallback scraper y contador `API fallback errors`.
- [x] Publicar/validar HA `0.2.195`: mejora Wunderground y ajustes UI; el usuario confirmo que funcionaba bien. Repo GitHub queda abierto por decision explicita.
- [x] Limpiar GHCR tras `0.2.195` sin cerrar repo, usando `GH_TOKEN` y conservando version activa/rollback/manifests auxiliares.
- [x] Documentar procedimiento de limpieza GHCR con `GH_TOKEN` en lugar de depender de `gh`.
- [x] Implementar MapLibre IDW con correccion DEM por celda para temperatura, badge `IDW DEM`/`IDW sin DEM`, setting `Zoom DEM` y popup largo con valores IDW puntuales.
- [x] Publicar HA `0.2.196` con MapLibre DEM IDW.
- [x] Publicar HA `0.2.197`: backfill mensual, backup de incrementales, pausas visibles, filtros por fuente/estacion y local HA UI con variables de entorno para claves.
- [x] Publicar HA `0.2.198`: Wunderground backfill mensual usa fechas locales exactas; el popup IDW incluye lluvia en `Valores IDW`.
- [x] Detectar y corregir bug de cache de `0.2.198`: el HTML cargaba `app.js?v=0.2.196` aunque la imagen tuviera el JS nuevo.
- [x] Publicar HA `0.2.199`: cache-busters MapLibre/Leaflet actualizados, `web_server.py` sirve el MapLibre protegido con `no-store` y reescribe query strings de assets a la version runtime. Commit `abe0d49`, digest `sha256:527673151e74d5c7a5ae2986eea6502b0f8014699ad4fdb3812cdc5ec2d64afb`.
- [x] Validar `0.2.199` localmente: tests unitarios relevantes, `node --check`, `sh -n`, `git diff --check`, inspeccion de imagen con `app.js?v=0.2.199` y `pointValues.rain`.
- [x] Validar en HA `0.2.199`: el usuario confirma que funciona; MapLibre protegido carga correctamente y el popup largo muestra `Pluja` en `Valores IDW`.
- [x] Limpiar GHCR de forma conservadora el 2026-07-18: eliminar las 60 entradas de `0.2.194`-`0.2.205`, conservar `0.2.207/latest`, rollback `0.2.206` y sus auxiliares multi-arch, y verificar los tres tags tras el borrado. El repo GitHub sigue publico.
- [ ] Continuar pruebas de backfill:
  - Wunderground: ventanas cortas, pausas y `backfill_station_filter` si solo hay estaciones nuevas.
  - AEMET: probar primero ventanas pequenas.
  - Meteoclimatic: no esperar historico real desde RSS.
  - Meteocat: no usar token por ahora; la clave encontrada no aplica al flujo Dades Obertes actual.
- [ ] Continuar `Parametros`/`Evidencia` y promocion manual solo despues de estabilizar el flujo actual de setales y observaciones.

## Notas historicas conservadas

Las notas siguientes son trazabilidad cronologica. No desplazan el estado
operativo anterior ni `docs/active-context.md`.

Nota de auditoria 2026-07-05: estado real contrastado con el repo antes de cierre. Rama `inicial`; ultimo commit pusheado antes de preparar este cierre `08797ae Document mushroom v0 evidence workflow`; version HA sigue en `0.2.180` en `rainmapper-app/config.yaml` y `rainmapper-app/Dockerfile`; no se ha hecho bump ni publicacion HA. `.github/workflows/build-rainmapper-app.yml` sigue siendo manual (`workflow_dispatch`). `rainmapper-local/docker-compose.yml` mantiene `rainmapper-ha-ui` en `127.0.0.1:8101`; `docker compose -f rainmapper-local/docker-compose.yml ps` no muestra servicios activos. Contrato operativo vigente de setas: datos vivos, artefactos v0 reconstruibles y estado del modelo bajo `mushroom-data/` (`docker-data/mushroom-data/` en local, `/share/rainmapper/mushroom-data/` en HA); `tmp/mushroom-lab/` queda solo para pruebas explicitas/QGIS. La pantalla `Parametros` tiene estructura de tres columnas en Ecologia/Suelos/Topografia/Fenologia; `Campo` puede calcularse desde observaciones guardadas y `GIS/DEM` requiere reconstruccion. La pantalla `Observaciones` captura hosts, bosque, suelo, habitat y orientacion observados; las ediciones/importaciones marcan especies pendientes y la cabecera muestra el boton rojo `Modelo v0 desactualizado`. Validaciones de cierre: validador de setas OK con 0 errores y 6 warnings conocidos, py_compile de UI/core v0 OK, tests de rutas/estado/observaciones/GIS/contexto/features/modelo/Marc/validator/web OK con 114 tests y `git diff --check` OK. Pendiente antes de HA: smoke completo o validacion de imagen si se publica version nueva.

Nota de auditoria 2026-07-02: estado real contrastado con el repo antes de cerrar continuidad. Rama `inicial`; commit de trabajo cerrado y pusheado `9c52bdf Document mushroom predictor v0 direction`, posterior a `76c5b5e Add batch GIS mapping reconstruction workflow`. La version HA sigue siendo `0.2.180` en `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y cache-busters; no se ha hecho bump ni publicacion HA. `.github/workflows/build-rainmapper-app.yml` sigue siendo fallback manual. `rainmapper-local/docker-compose.yml` contiene `rainmapper-ha-ui` contra `docker-data/`; tras ejecutar `./mushroom_lab_stop.sh`, Docker no muestra servicios activos y los datos quedan preservados. El PDF local `docs/mushrooms/literature/Marc_EstevezSpecies.pdf` queda ignorado/no versionado por ser un escaneo local; se versiona el resumen `marc-estevez-species-conclusions-es.md`. Validaciones de cierre: validador de setas OK con 0 errores y 7 warnings conocidos, tests GIS/validator OK, py_compile GIS/validator OK y `git diff --check` OK.

Nota de auditoria 2026-07-01: estado real contrastado con el repo antes de cerrar continuidad. La version HA sigue siendo `0.2.180` en `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y cache-busters; el ultimo commit pusheado es `ef9bbc6 Add GIS mappings lab UI`, posterior a la release `0.2.180` y sin bump de version HA. `.github/workflows/build-rainmapper-app.yml` es fallback manual; `scripts/build-push-ha-image.sh` sigue siendo el flujo normal de publicacion. `rainmapper-local/docker-compose.yml` contiene `rainmapper-ha-ui` para laboratorio local contra `docker-data/`, monta `mushroom-GIS/` como solo lectura y `tmp/` como `/app/tmp`; `docker compose -f rainmapper-local/docker-compose.yml ps` no muestra servicios activos en el cierre. No publicar nueva version HA sin peticion explicita del usuario.

Nota de continuidad 2026-06-28: version HA `0.2.172` publicada, instalada y validada correctamente en HA por el usuario en aquel cierre. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.172` y `latest`, digest multi-arch `sha256:acc20d71b82257e4c55736a5cbabbb935002ffd8b6c69b076040f222bfbcecd4`. `0.2.171` quedo publicada con imagen `ghcr.io/cginebrosa/rainmapperha:0.2.171`, digest multi-arch `sha256:d018069ece91716ea5d526c22a6c57c08652598d5f09e761c19a0c5f4a8edf1c`, ajusto `Archive species` para mostrar el `species_id` como solo lectura y ordeno visualmente la lista lateral de especies por `scientific_name`. `0.2.172` corrige la tarjeta `Weather model summary` del tab `General/Summary` de especies para leer las claves documentadas del `weather_model` real (`rain_7d_min_mm`, `temp_min_7d_optimal_min_c`, etc.), igual que el tab `Weather`. Decision defensiva: una especie activa no se borra directamente; primero debe archivarse, y solo una especie archivada puede eliminarse definitivamente con doble advertencia. La UI de especies sigue en iteracion hacia `docs/mushrooms/ui/profiles/mushroom-profiles-species.png`. `web_server.py` conserva rutas, POST, persistencia y orquestacion de validacion; las pantallas grandes de setas viven en `rainmapper-app/app/mushroom_profiles_ui.py`, `rainmapper-app/app/mushroom_catalogs_ui.py` y `rainmapper-app/app/mushroom_gis_mappings_ui.py`. El modulo comun de validacion es `rainmapper_core/mushroom_validation.py` y lo usan tanto la WebUI HA como `scripts/validate-mushroom-data.py`. `docs/mushrooms/ui/reference-catalogs/reference-catalog-domain-impact-reference.png` sigue pendiente como pantalla informativa/analitica futura, no bloquea el flujo principal de mantenimiento.

Nota de continuidad 2026-06-29: `0.2.173` publica las tabs superiores reales `Parameters`, `Calibration` y `Observations` de `/mushrooms/profiles`. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.173` y `latest`, digest multi-arch `sha256:80a527bd9e5917dfc4f088fc8ab000488cfc334867cf2ab8cc3bfdf6ac3cc35c`; pendiente de validar en HA. `Parameters` edita parcialmente bloques reales de la especie seleccionada (`weather_model`, `phenology`, `topography`, `scoring_weights` y `ecology.trophic_mode_id`) sin tocar identidad ni afinidades catalogadas; las afinidades completas siguen en `Species > Ecology`. `Calibration` edita parcialmente `prediction_confidence`, `metadata.review_status` y `metadata.requires_human_validation`, con cobertura de observaciones marcada como futura. `Observations` queda como workspace preparatorio sin persistencia nueva: no mezcla observaciones dentro de `mushroom_profiles.json` y deja explicito que hace falta definir store/schema/importacion/validacion. Validacion local: `python3 -m unittest tests.test_web_server_auth tests.test_mushroom_data_validator tests.test_mushroom_store` OK con 58 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `./scripts/smoke-test.sh` OK con 120 tests.

Nota de continuidad 2026-06-29: `0.2.174` publica el ajuste visual de `Parameters` hacia el mockup. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.174` y `latest`, digest multi-arch `sha256:285f789d6d28a9ab2a6be851beb634767d26430a4b5c6bffee80873305557b89`; pendiente de validar en HA. Cambios principales: `Climate model` mas estrecho, `Habitat model` con mas espacio, iconos por subbloque, labels humanas desde `mushroom-data/mushroom_labels.json` con `en/es/ca`, hosts separados en primarios/secundarios/otros y chips legibles para afinidades. Validacion local: `python3 -m unittest tests.test_web_server_auth tests.test_mushroom_data_validator tests.test_mushroom_store` OK con 59 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `./scripts/smoke-test.sh` OK con 121 tests.

Nota de continuidad 2026-06-29: `0.2.175` queda publicada y pusheada para validar en HA. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.175` y `latest`, digest multi-arch `sha256:883695d0d414d871857a219a904ea60effc3af6c64aa320b9bf5447d10389a7e`, commit `b52cd5c Release Home Assistant 0.2.175`. Cambios principales: `mushroom_parameter_labels.json` se sustituye por `mushroom_labels.json`; se añade `mushroom_observations.json` como store editable y validable; `Observations` pasa a mantenimiento real con alta/edicion, parsing de Google Maps o coordenadas decimales, archivado/restauracion/borrado permanente defensivo solo desde archivadas, y valores tabulados desde `mushroom_reference_catalogs.json`; se añade `ui_language` en `config.yaml` como base futura. Validacion local antes de publicar: `./scripts/smoke-test.sh` OK con 128 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `git diff --check` OK, GHCR digest verificado para `0.2.175/latest` e import check dentro de imagen OK (`imports_ok`, `mushroom_observations.json`). Pendiente de validar en HA.

Nota de continuidad 2026-06-29: `0.2.176` queda publicada y pusheada para validar en HA. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.176` y `latest`, digest multi-arch `sha256:4c35166beae9979e4d0aae465a18066272dd115b573d2b289a79e25cf4c04fd9`, commit `0c459e4 Release Home Assistant 0.2.176`. Cambios principales: `/mushrooms/catalogs` ya no muestra IDs raw largos en las tarjetas superiores de grupo; todos los grupos actuales leen su nombre humano desde `mushroom_labels.json` con claves `catalog_group.*`; no hay fallback silencioso para labels de grupo, de modo que una clave ausente aparece como `missing label: catalog_group.<grupo>`. Validacion local antes de publicar: `python3 -m py_compile rainmapper-app/app/mushroom_catalogs_ui.py rainmapper-app/app/web_server.py` OK, `python3 -m unittest tests.test_web_server_auth tests.test_mushroom_data_validator tests.test_mushroom_store` OK con 66 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `./scripts/smoke-test.sh` OK con 128 tests, GHCR digest verificado para `0.2.176/latest` e import check dentro de imagen OK (`image_import_ok`, `Altitude source`). Pendiente de validar visualmente en HA.

Nota de continuidad 2026-06-29: `0.2.177` queda publicada y pusheada para validar en HA. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.177` y `latest`, digest multi-arch `sha256:eabf0e92ed56a2767c326ecaad9dae673e35e21cc42e1b9dcffa574bfa0a85bc`, commit `4c0635f Release Home Assistant 0.2.177`. Cambios principales: `mushroom_labels.json` centraliza labels visibles del dominio `mushrooms` en `en`, `es` y `ca` para perfiles, parametros, calibracion, observaciones y reference catalogs; `run.sh` lee la opcion HA `ui_language` y exporta `RAINMAPPER_MUSHROOM_UI_LANGUAGE`; `/mushrooms/catalogs` cuenta referencias desde `mushroom_observations.json` para que los IDs tabulados usados en observaciones no aparezcan como unused. Validacion local antes de publicar: `python3 -m unittest tests.test_web_server_auth tests.test_mushroom_data_validator tests.test_mushroom_store` OK con 69 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `git diff --check` OK, `./scripts/smoke-test.sh` OK con 131 tests, render smoke en `ca` y `es` sin `missing label`, GHCR digest verificado e import check dentro de imagen OK (`image_import_ok`, `0.2.177`, `Observations`, `New observation`). Pendiente de validar visualmente en HA.

Nota de continuidad 2026-06-29: `0.2.178` queda publicada y pusheada para validar en HA. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.178` y `latest`, digest multi-arch `sha256:bf5d8ec22237edc7cc6b15403e8c057c0a726b4569248b2e701536d1ae08033f`, commit `96f835e Release Home Assistant 0.2.178`. Cambios principales: `Especies > Meteorologia` y `Especies > Puntuacion` dejan de mostrar keys raw del JSON y usan labels humanas desde `mushroom_labels.json`; los valores controlados de confianza/calibracion/revision/calidad se traducen con claves `value.*`; `General > Fenologia` muestra patrones de temporada desde catalogos traducidos y los chips de meses tienen ancho estable; se anade test de regresion para render ES sin `missing label`. Validacion local antes de publicar: `python3 -m unittest tests.test_web_server_auth tests.test_mushroom_data_validator tests.test_mushroom_store` OK con 70 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `git diff --check` OK, `./scripts/smoke-test.sh` OK con 132 tests, servidor local en `127.0.0.1:8100` verificado con idioma `es`, GHCR digest verificado para `0.2.178/latest` e import check dentro de imagen OK (`image_import_ok`, `0.2.178`, `Weather model`, `7d min rain`, `Not calibrated`). GHCR remoto limpiado usando `GH_TOKEN`: borradas 205 versiones antiguas (`0.2.176` hacia atras y auxiliares), 0 fallos; quedan 10 package versions correspondientes a `0.2.178/latest`, `0.2.177` y sus manifests auxiliares. Repositorio GitHub cerrado de nuevo como privado. Pendiente de validar visualmente en HA.

Nota de continuidad 2026-06-29: `0.2.179` queda publicada y pusheada para validar en HA. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.179` y `latest`, digest multi-arch `sha256:e914cc03517749d38203dd3deec5837ba4e0b2ffc825bbf8c69e4d0d003e6795`, commit `295fc0e Release Home Assistant 0.2.179`. Cambios principales: el tab interno `Especies > Fenologia` pasa a `Fenologia y Topografia`, separa visualmente Fenologia y Topografia, cambia meses principales/secundarios a pastillas editables, compacta retrasos y altitudes en grids 2x2, alinea patrones de temporada/orientaciones, reduce el nombre de especie en la lista lateral y anade la label `snowmelt_bonus` (`Bonus deshielo`). Validacion local antes de publicar: `python3 -m unittest tests.test_web_server_auth tests.test_mushroom_data_validator tests.test_mushroom_store` OK con 70 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `git diff --check` OK, `./scripts/smoke-test.sh` OK con 132 tests, servidor local en `127.0.0.1:8100` revisado con idioma `es`, GHCR digest verificado para `0.2.179/latest` e import check dentro de imagen OK (`image_import_ok`, `0.2.179`, `Bonus deshielo`). GHCR remoto limpiado usando `GH_TOKEN`: borradas 5 package versions antiguas de `0.2.177`, 0 fallos; quedan 10 package versions correspondientes a `0.2.179/latest`, `0.2.178` y sus manifests auxiliares. Pendiente de validar visualmente en HA.

Nota de continuidad 2026-06-29: `0.2.180` queda publicada, pusheada, instalada y funcionando en HA segun confirmacion del usuario. Imagen `ghcr.io/cginebrosa/rainmapperha:0.2.180` y `latest`, digest multi-arch `sha256:c5b59f5b534b08154b64bba94bc13a3d2aa8d74c2f10f9a3b7ccd84eecbe80b8`, commit `0415067 Release Home Assistant 0.2.180`. Cambios principales: el guardado del editor interno de especies vuelve al mismo tab tras guardar o tras errores de validacion; `Observaciones` usa filtros de fecha editables con date picker y autosubmit; `Parametros` separa los pesos de scoring en una seccion propia y reequilibra el layout; `Fenologia y Topografia` sustituye textareas de patrones de temporada/orientaciones por pastillas seleccionables desde catalogos traducidos; la lista lateral de especies muestra cabecera alineada `Conf./Prio./Rev.`, tooltips traducibles para cada pastilla y scroll interno para no crecer indefinidamente. Validacion local antes de publicar: primer `./scripts/smoke-test.sh` detecto cache-busters de visores en `0.2.179`; se corrigieron a `0.2.180` y el segundo `./scripts/smoke-test.sh` paso completo con 134 tests. Validaciones adicionales durante iteracion: `python3 -m unittest tests.test_web_server_auth` OK con 59 tests, `python3 scripts/validate-mushroom-data.py` OK con 0 errores y 7 warnings conocidos, `git diff --check` OK. GHCR digest verificado para `0.2.180/latest` e import check dentro de imagen OK (`image_import_ok 0.2.180`, labels `Conf.`/`Rev.`). GHCR remoto limpiado usando `GH_TOKEN`: borradas 5 package versions antiguas de `0.2.178`, 0 fallos; quedan 10 package versions correspondientes a `0.2.180/latest`, `0.2.179` rollback y sus manifests auxiliares.

Nota historica supersedida 2026-06-27: esta nota describia `0.2.150` como version actual y un fix local pendiente. Ese estado ya no es vigente. Se conserva solo como antecedente del primer hub de catalogos; el estado operativo verificado en el cierre actual es `0.2.180` segun las notas de continuidad anteriores.

## Proximo paso recomendado
Direccion acordada 2026-07-11: priorizar un pipeline ML real para
`boletus_aereus` sobre el refinamiento visual de `Parametros`. El modelo v0
actual es descriptivo y no entrena ningun estimador. El contrato propuesto vive
en `docs/mushrooms/mushroom-ml-training-plan-es.md`: agrupar observaciones por episodio,
reconstruir series meteorologicas diarias, generar features de distribucion y
variabilidad, entrenar un baseline binario y validar por setal/fecha sin fuga.
El usuario ampliara observaciones; hacen falta especialmente ausencias reales.

- [ ] Construir pipeline ML experimental para `boletus_aereus`
  - Contexto: existen 13 observaciones de la especie, pero solo una ausencia; el
    `mushroom_model_v0.json` actual resume evidencia y no es ML.
  - Criterio de aceptacion: dataset por episodio con serie diaria auditable,
    features meteorologicas/GIS/fenologicas versionadas, regresion logistica
    baseline, validacion agrupada y reporte honesto de muestra/gaps/metricas.
  - Restricciones: no fabricar negativos, no dividir observaciones del mismo setal y fecha,
    no inventar umbrales y no presentar resultados experimentales como
    probabilidades fiables.
  - Plan: `docs/mushrooms/mushroom-ml-training-plan-es.md`.

- [x] Crear mantenimiento de areas y microareas conocidas
  - Store privado: `mushroom_known_sites.json`, separado de reference catalogs.
  - UI: `/mushrooms/known-sites`, con arbol colapsable, mapa MapLibre,
    dibujo/edicion de poligonos, campos futuros, GIS/DEM comparativo, backups,
    validacion, archivado/restauracion/borrado defensivo y referencias.
  - Observaciones: selector opcional `micro_area_id`; el `area_id` se resuelve
    desde el store. Los contadores abren el modal compartido de observaciones.
  - Integridad: no archivar ni borrar entidades referenciadas; las propuestas
    GIS/DEM solo modifican el borrador hasta pulsar `Guardar`.

- [x] Integrar setales y coordenadas en el flujo de observaciones
  - El mapa de observacion muestra las areas/microareas visibles y permite
    seleccionar, crear y editar geometria sin abandonar el formulario.
  - El boton `Mapa` usa el borrador actual, tambien en nuevas observaciones y
    duplicados aun no guardados, y conserva la pila de retorno.
  - Se pueden seleccionar coordenadas manualmente, recuperar altitud DEM y
    confirmar el cambio; se usan IDs de origen catalogados existentes.
  - El modal de observaciones resalta fila y POI seleccionados y reutiliza el
    mismo componente para evidencia y setales.

- [x] Establecer una sola imagen por observacion y flujo de sustitucion EXIF
  - Permite desasociar, o desasociar y borrar si no existen otras referencias,
    siempre con confirmacion irreversible.
  - El preview compara imagen existente/nueva, datos EXIF y mapas; la nueva se
    aplica solo tras decidir el tratamiento de la anterior.

- [ ] Validar visualmente y cerrar el rediseño del formulario de observacion
  - Estructura vigente: columna izquierda con Observacion/Ubicacion/Validacion/
    Origen, columna derecha `Evidencia de campo`, pie compacto EXIF/acciones.
  - Ultimo ajuste: tipografia/pastillas derechas, icono y texto EXIF, botones
    inferiores. Pendiente confirmacion humana tras el rebuild local.

Seguimiento UI anterior: validar visualmente el flujo nuevo de `Parametros`
en tres columnas con datos reconstruidos reales, especialmente `Fenologia`, y
despues redisenar `Evidencia` para que no parezca una tabla puramente GIS
cuando mezcla Campo, GIS/DEM y coincidencias con perfil. El objetivo es que la
UI explique claramente si un valor viene del perfil, observador, GIS/DEM o
fuente literaria. `mushroom_profiles.json` conserva identidad, conocimiento
base y configuracion; el conocimiento aprendido desde observaciones vive en
artefactos reconstruibles bajo `mushroom-data/` junto al estado
`mushroom_model_v0_state.json`. La pantalla `Evidencia > Modelo aprendido`
queda como auditoria tecnica, no como lugar principal de mantenimiento. El
predictor v0 sigue limitado a vegetacion/host, suelo amplio, habitat, altitud
aproximada, temporada y meteorologia reconstruida; no convertir geologia fina ni
viento en scoring productivo sin evidencia suficiente. Usar
`docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`,
`docs/mushrooms/mushroom-predictor-design-es.md`,
`docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`,
`docs/mushrooms/mushroom-profiles-v0-candidate-build-es.md` y
`docs/mushrooms/literature/README.md`, separando fuente estructurada,
observaciones locales e hipotesis.

- [ ] Completar rediseño de `Parametros` con comparacion aprendida v0
  - Contexto: la pantalla ya tiene tabs internos y comparacion en tres columnas: perfil, evidencia v0 y valores emergentes. La evidencia v0 mezcla datos declarados por el observador y contexto GIS/DEM, por lo que los chips deben mostrar procedencia (`Campo`, `GIS/DEM` y origen literario del perfil cuando aplique) y no presentarse como evidencia puramente observacional.
  - Ficheros relacionados: `rainmapper-app/app/mushroom_profiles_ui.py`, `rainmapper-app/app/web_server.py`, `mushroom-data/mushroom_labels.json`, `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`.
  - Criterio de aceptacion: secciones de perfil, evidencia v0 y valores emergentes alineadas visualmente en Ecologia/Suelos/Topografia/Fenologia, labels multiidioma, chips compactos con fuente visible, sin perder inputs al guardar y sin que el modelo aprendido escriba perfiles automaticamente.
  - Estado: iniciado tras `0.2.180`; Ecologia/Suelos/Topografia/Fenologia tienen estructura base. Pendiente validar visualmente con datos reconstruidos tras el nuevo flujo completo de modelo v0. En modo v0 no existe tab `Meteorologia`; la meteorologia reconstruida se revisa desde `Evidencia > Meteorologia` y el modelo aprendido.

- [ ] Separar claramente Campo, GIS/DEM y mezcla en pantallas de evidencia y modelo v0
  - Contexto: el usuario detecto que llamar `GIS` a la evidencia de hosts/bosques confundia el origen real de los datos. Un host declarado en observacion y un host detectado por GIS/DEM son evidencias distintas; ambas pueden alimentar features/modelo v0, pero la UI debe mostrar fuente y soporte sin ocultar esa diferencia.
  - Ficheros relacionados: `rainmapper_core/mushroom_observation_features.py`, `rainmapper_core/mushroom_learned_model.py`, `rainmapper-app/app/mushroom_profiles_ui.py`, `mushroom-data/mushroom_observations.json`, `mushroom-data/mushroom_gis_mappings.json`, `docs/mushrooms/mushroom-predictor-design-es.md`.
  - Criterio de aceptacion: reconstruccion v0 conserva procedencia por valor; Parametros muestra fuente por chip; Evidencia diferencia declarados por observador, detectados por GIS/DEM y coincidencias mixtas; ninguna decision escribe perfiles automaticamente.
  - Estado: en curso. Las features/modelo v0 ya incorporan procedencia categorica y el laboratorio de observaciones pasa a reconstruir GIS/DEM + meteo + features + modelo. Pendiente rediseñar la pestanya `Evidencia` para que deje de parecer una tabla puramente GIS cuando incluye comparaciones con observaciones.

- [x] Añadir bosque, suelo, habitat y orientacion observados al alta/edicion de observaciones
  - Contexto: la observacion ya permitia declarar arboles observados, pero faltaban campos de campo directos para bosque, suelo, habitat y orientacion. Sin ellos, el modelo v0 solo podia aprender esas categorias desde GIS/DEM o inferencias posteriores.
  - Criterio de aceptacion: campos catalogados opcionales, guardados separados del contexto GIS, visibles en detalle y usados por features v0 con fuente `field`; no sustituyen mappings GIS ni modifican perfiles automaticamente.
  - Estado: implementado localmente tras `0.2.180`. Las observaciones existentes pueden completarse con el script de derivados y/o al editarse; los cambios marcan especies pendientes de reconstruccion del modelo v0.

- [ ] Definir flujo de promocion manual de candidatos de evidencia
  - Contexto: las decisiones de Evidencia guardan estado interno reversible, pero todavia no aplican cambios a perfiles.
  - Criterio de aceptacion futuro: mostrar candidatos/diffs por campo, permitir promover o descartar con confirmacion, validar el perfil completo y conservar trazabilidad/reversibilidad.
  - Estado: pendiente deliberado; no bloquear la revision visual de Evidencia.

- [ ] Añadir comparacion meteorologica IDW frente a estacion mas cercana
  - Contexto: algunas estaciones Wunderground pueden contener outliers historicos o datos inconsistentes. MapLibre ya tiene una capa IDW cliente para comparar estaciones dentro de un radio.
  - Criterio de aceptacion futuro: calcular evidencia meteorologica alternativa por IDW, idealmente radios 10 km y 15 km, para comparar con la estacion mas cercana y detectar outliers. No sustituir automaticamente la evidencia base hasta revisar resultados.
  - Estado: pendiente. Wunderground velocidad de viento historica queda disponible, pero direccion por scrape mensual y reconstruccion 2-3 años quedan como TODO; no usar viento como scoring v0 productivo todavia.

- [ ] Construir laboratorio local de observaciones reales de setas
  - Contexto: la literatura accesible no proporciona suficientes valores transferibles para fijar umbrales por especie. El enfoque cambia a usar fotos geolocalizadas y observaciones positivas/negativas reales del usuario como primera capa de evidencia local.
  - Ficheros relacionados: `docs/mushrooms/mushroom-local-observation-lab-es.md`, `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`, `tmp/mushroom-lab/`, `docker-data/`, `rainmapper-local/docker-compose.yml`, futuros scripts locales, `mushroom-data/mushroom_profiles.json`, `mushroom-data/mushroom_reference_catalogs.json`, `mushroom-data/mushroom_gis_mappings.json`, historicos HA copiados manualmente desde `/share/rainmapper/Data`.
  - Criterio de aceptacion: importar observaciones positivas y negativas desde fotos EXIF o CSV manual; reconstruir lluvia/temperatura/humedad/viento previos desde incrementales locales; cruzar coordenadas con DEM/coberturas/litologia locales; generar `species_parameter_candidates.json` y reportes por especie; no escribir en `/share/rainmapper` ni versionar fotos/coordenadas/historicos reales.
  - Fases: primero observaciones + meteorologia; despues DEM/topografia; despues cubiertas/vegetacion/litologia/suelo; finalmente candidatos de parametros por especie.
  - Estado: scaffold historico creado bajo `tmp/mushroom-lab/` y documentado; `rainmapper-ha-ui` permite trabajar contra `docker-data/` como copia local de `/share/rainmapper`; la pantalla de observaciones ya permite importar fotos EXIF con plantilla comun, importar varias fotos/carpeta, duplicar observaciones como plantilla sin guardar, recuperar EXIF desde duplicados, ordenar por cabeceras, seleccionar fila completa, ver todas las especies, preservar filtros/archivadas tras acciones y mantener IDs coherentes con la fecha final. Los perfiles y catalogos v0 ya estan promovidos a `mushroom-data/` con 21 especies y 12 IDs nuevos de catalogo. El flujo operativo v0 genera contexto, features, modelo y estado bajo `docker-data/mushroom-data/`; `tmp/mushroom-lab/` queda solo para pruebas locales explicitas/QGIS. `mushroom_learned_model_v0_build.sh` genera `mushroom_model_v0.json` con soporte positivo/negativo, ratios, procedencias y rangos por especie sin tocar perfiles.
  - Dependencia: `requirements.txt` incluye `Pillow==12.2.0` para leer EXIF desde la UI. Mantenerla mientras exista importacion/recuperacion EXIF en local o HA.

- [ ] Mostrar evidencia del modelo aprendido junto a parametros de especie
  - Contexto: `Evidencia > Modelo aprendido` ya resume por especie los calculos de `mushroom_model_v0.json`, pero como pantalla aislada solo sirve para auditoria. Para que ayude al mantenimiento, sus calculos deben aparecer al lado del parametro que se revisa.
  - Ficheros relacionados: `rainmapper-app/app/mushroom_profiles_ui.py`, `rainmapper-app/app/web_server.py`, `rainmapper_core/mushroom_learned_model.py`, `docker-data/mushroom-data/mushroom_model_v0.json`, `docker-data/mushroom-data/mushroom_model_v0_state.json`, `mushroom-data/mushroom_labels.json`, `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`, `docs/mushrooms/mushroom-predictor-design-es.md`, `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`.
  - Criterio de aceptacion: en `Parametros`, mostrar soporte observado junto a hosts, bosques, suelos, habitat, altitud, fenologia y meteorologia v0; en `Especies > General`, mostrar resumen compacto de observaciones usadas, gaps y contradicciones; en `Especies > Ecologia`, marcar declarado/observado/no observado junto a cada afinidad; en `Especies > Fenologia y Topografia`, comparar meses y altitud declarados contra lo observado. La UI debe ser multiidioma, compacta y humana; la vista tecnica de `Evidencia > Modelo aprendido` queda como detalle. No debe escribir perfiles automaticamente.
  - Estado: iniciado. La pantalla `Parametros` v0 tiene tabs internos (`Ecologia`, `Suelos`, `Topografia`, `Fenologia`) y estructura de tres columnas para perfil, evidencia v0 y valores emergentes. Pendiente validar visualmente con datos reconstruidos y redisenar `Evidencia`. El modelo aprendido actual es descriptivo: separa positivos/negativos, cuenta soporte categorico con procedencia (`field`/`gis`), calcula rangos numericos y reporta gaps. No predice ni calcula score operativo.

- [ ] Mejorar reconstruccion meteorologica de observaciones con IDW por radio
  - Contexto: el primer `observation_context_builder` usa la estacion diaria mas cercana con cobertura suficiente. Es simple y trazable, pero puede fallar si esa estacion tiene datos inconsistentes o huecos locales. El visor MapLibre ya tiene una capa IDW que estima metricas desde estaciones cercanas dentro de un radio.
  - Criterio de aceptacion: anadir un calculo experimental paralelo para observaciones que calcule lluvia, temperatura y humedad por IDW usando radios de 10 km y 15 km, manteniendo la estacion mas cercana como linea base y comparativa. La salida debe indicar estaciones usadas, cobertura, gaps, radio, potencia IDW, diferencias frente a nearest-station y alertas de outlier. No usar viento en la v0 salvo decision posterior.
  - Estado: pendiente. La pantalla de evidencia meteorologica ya muestra lluvia 7/14/21/30/60/90, temperatura 7/14/21/30, humedad 7/14/21/30 y altitud cuando estan en `observation_features_v0.json`. El reconstructor excluye lluvias diarias claramente anomalas de las sumas experimentales y las reporta como `rain_suspect_daily_*`; esto es un guardarrail de calidad de datos, no un umbral del predictor.

- [ ] Consolidar proyeccion operativa v0 de perfiles
  - Contexto: la fuente estructurada revisada expresa habitat en categorias amplias, no en parametros finos. La v0 debe usar `mushroom_profiles.json` como entidad principal y proyectar solo los campos activos, sin tirar el schema rico ni la UI actual.
  - Ficheros relacionados: `rainmapper_core/mushroom_profile_v0.py`, `scripts/audit-mushroom-profile-v0-source.py`, `mushroom-data/mushroom_profiles.json`, `mushroom-data/mushroom_reference_catalogs.json`, `docs/mushrooms/literature/marc-estevez-v0-source-normalized.json`, `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`, `docs/mushrooms/mushroom-v0-catalog-gap-audit-es.md`, `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`, `docs/mushrooms/mushroom-predictor-design-es.md`.
  - Criterio de aceptacion: la proyeccion v0 expone especie, fuente/estado, bosque/host asociado, suelo amplio, habitat, altitud/temporada aproximadas y revision/calibracion; no promociona pesos, umbrales meteorologicos ni litologia fina; aprovecha catalogos existentes y anade claves solo si faltan; deja la UI rica aparcada como vista avanzada/futura.
  - Estado: iniciado. Existe `rainmapper_core/mushroom_profile_v0.py` con proyeccion v0 no destructiva, `docs/mushrooms/literature/marc-estevez-v0-source-normalized.json` con 22 especies normalizadas y `scripts/audit-mushroom-profile-v0-source.py` para comparar contra perfiles/catalogos. El auditor confirma que los 11 perfiles actuales estan cubiertos y que hay 11 especies nuevas candidatas. Pendiente revisar el reporte, decidir altas/cambios de catalogo y definir la UI v0 de mantenimiento.

- [x] Definir contrato minimo de predictor v0
  - Contexto: el schema rico actual sigue existiendo, pero no debe gobernar la primera version del predictor. Hace falta una ficha v0 menor y explicable que use solo senales soportadas por fuente estructurada o por datos reconstruibles.
  - Criterio de aceptacion: proponer campos minimos para compatibilidad de especie, habitat/vegetacion/host, suelo amplio, altitud, temporada, meteorologia observable y estado de revision; documentar que pesos, ventanas finas y litologias exactas quedan como futuros candidatos, no como obligatorios.
  - Estado: iniciado/resuelto para el contrato base en `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md` y `rainmapper_core/mushroom_profile_v0.py`. Pendiente completar datos y UI v0.

- [ ] Disenar ciclo de enriquecimiento desde observaciones
  - Contexto: conforme haya observaciones reales, el laboratorio debe inferir posibles parametros nuevos, testearlos y proponerlos como candidatos. No debe aprender ni modificar scoring automaticamente.
  - Criterio de aceptacion: outputs reproducibles que muestren observaciones usadas, contexto GIS/DEM, meteorologia previa, candidato propuesto, soporte estadistico basico o evidencia disponible, gaps y estado de revision. La promocion al modelo debe ser manual y trazable.
  - Estado: pendiente. Debe consumir `observation_features_v0.json` y la proyeccion operativa v0, generando candidatos o avisos de evidencia insuficiente sin tocar perfiles.

- [ ] Aplicar decisiones revisadas de evidencia local a perfiles
  - Contexto: la pestanya `Evidencia` guarda decisiones reversibles (`Promover`, `Ignorar`, `Mantener`, `Dudoso`, `Confirmar`, `Reiniciar`) en `mushroom_evidence_decisions.json`, separadas de `mushroom_profiles.json`. Esto permite revisar sin modificar perfiles productivos.
  - Criterio de aceptacion futuro: accion explicita para aplicar decisiones revisadas a `mushroom_profiles.json`, con diff visible por especie/campo, backup previo, confirmacion humana, validacion completa y posibilidad de no aplicar decisiones dudosas o ignoradas. No debe escribir cambios automaticos al pulsar una decision individual de evidencia.
  - Estado: pendiente por decision del usuario. La pantalla actual solo persiste estados de revision y no toca perfiles.

- [ ] Disenar futuro recalculo no destructivo de candidatos desde observaciones
  - Contexto: en algun momento la ficha de especies podria tener una accion para recalcular parametros desde observaciones. No debe implementarse todavia en HA porque el pipeline local no esta validado.
  - Criterio de aceptacion futuro: boton o accion tipo `Recalcular candidatos desde observaciones`; mostrar valor actual, rango observado, candidato, numero de observaciones, positivas/negativas, confianza y huecos de datos; permitir aplicar manualmente campos concretos; no sobrescribir automaticamente perfiles completos.
  - Estado: documentado como futuro en `docs/mushrooms/mushroom-local-observation-lab-es.md`; pendiente validar laboratorio local.

- [ ] Subida de observaciones EXIF desde MapLibre para colaboradores actuales
  - Prioridad: media.
  - Contexto: los colaboradores actuales podrian aportar muchas mas observaciones subiendo fotos desde el visor protegido MapLibre. La app ya tiene usuarios/sesiones, permisos por usuario para funciones MapLibre y la UI de setas ya puede extraer EXIF con `Pillow==12.2.0`.
  - Diseno preliminar: anadir un permiso/toggle de usuario similar a los actuales de metricas, IDW y Heatmap, por ejemplo `can_upload_mushroom_observations`. Si esta activo, MapLibre muestra una accion para subir fotos EXIF de observaciones; si esta apagado, el visor no expone esa funcionalidad.
  - Criterio de aceptacion futuro: desde MapLibre protegido, un colaborador autorizado puede subir una o varias fotos; el backend valida que haya EXIF util, extrae fecha/coordenadas/altitud cuando existan, rellena observador/origen desde la sesion Rainmapper, y guarda la observacion como pendiente de revision y sin uso automatico en calibracion. El propietario debe poder validarla o descartarla desde mantenimiento de observaciones.
  - Compatibilidad: JPEG con EXIF de iPhone/Android debe ser el formato base. HEIC/HEIF no debe considerarse garantizado hasta probarlo en HA. Si se acepta HEIC/HEIF, valorar conversion server-side a JPEG preservando EXIF util antes de procesar o guardar metadata.
  - Riesgos: privacidad de coordenadas, limites de tamano/cantidad, validacion de fotos sin EXIF, decidir si se guardan imagenes originales, JPEG convertido o solo metadata. Preferencia inicial: no persistir imagen completa salvo decision explicita.

- [x] Construir `observation_context_builder` local para observaciones
  - Contexto: las observaciones de fotos reales pueden ser de anos anteriores, por lo que no basta consultar el GeoJSON actual. Hay que reconstruir las condiciones historicas desde incrementales copiados de HA.
  - Ficheros relacionados: `rainmapper_core/mushroom_observation_context.py`, `scripts/reconstruct-mushroom-observation-context.py`, `mushroom_observation_context_rebuild.sh`, `docker-data/Data/*_incremental.csv`, `docker-data/mushroom-data/mushroom_observations.json`, `docs/mushrooms/mushroom-local-observation-lab-es.md`, `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`.
  - Criterio de aceptacion: para cada observacion activa/valida usada en calibracion, calcular lluvia acumulada 1/7/14/21/30/60/90 dias, temperatura, humedad y viento disponibles en la fecha historica; marcar gaps por fuente/fecha/estacion; generar CSV/JSON y reporte humano reproducibles en `tmp/mushroom-lab/` sin tocar datos HA, perfiles productivos ni historicos.
  - Estado: implementacion inicial local completada el 2026-07-02 y rutas operativas migradas el 2026-07-05. El wrapper escribe `mushroom_observations_weather_features.json`, CSV y reporte markdown bajo `docker-data/mushroom-data/`. Metodo actual: estacion diaria mas cercana con datos en 90 dias, sin interpolacion ni mezcla de fuentes. Pendiente decidir si el siguiente POC permite fuente distinta para viento/lluvia/temperatura/humedad con trazabilidad separada.

- [ ] Reconstruir historico Wunderground y decidir papel del viento en setas v0
  - Contexto: Wunderground ya esta recuperando viento en ejecuciones actuales, pero las observaciones historicas de setas pueden caer en periodos donde el incremental local antiguo no conserva viento. Se podria reconstruir Wunderground de los ultimos 2-3 anos para mejorar cobertura historica.
  - Ficheros relacionados: `rainmapper_core/sources/wunderground/`, `docker-data/Data/Wunderground_incremental.csv`, `rainmapper_core/mushroom_observation_context.py`, `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`.
  - Criterio de aceptacion futuro: reconstruccion historica controlada con backup/check-history, sin duplicados por estacion/dia, preservando lluvia/temperatura/humedad/viento disponibles; si se usa direccion media, calcularla de forma circular como en Meteocat/Tomap y documentar limitaciones del scraping mensual diario.
  - Estado: TODO. Para la v0 micologica inicial, mantener el viento como campo reconstruible/gap trazable, pero no usarlo como factor de scoring ni bloquear candidatos hasta que haya cobertura y utilidad justificadas.

- [x] Unir meteorologia y GIS en features v0 por observacion
  - Contexto: antes de generar candidatos de parametros o pantallas de evidencia meteorologica hace falta un artefacto unico por observacion que combine meteorologia historica y `gis_context_v0`.
  - Ficheros relacionados: `rainmapper_core/mushroom_observation_features.py`, `scripts/build-mushroom-observation-features-v0.py`, `mushroom_observation_features_v0_build.sh`, `docker-data/mushroom-data/mushroom_observations_weather_features.json`, `docker-data/mushroom-data/mushroom_gis_observation_reconstruction.json`.
  - Criterio de aceptacion: unir por `observation_id`, conservar lluvia/temperatura/humedad/viento, hosts/bosques/suelo/habitat/altitud GIS v0 y separar `weather_gaps`, `gis_gaps`, `feature_gaps`; escribir JSON/CSV/reporte bajo `docker-data/mushroom-data/` sin tocar perfiles ni observaciones.
  - Estado: implementado el 2026-07-02 y migrado a rutas operativas `mushroom-data` el 2026-07-05. Este contrato queda como base para evidencia meteorologica y candidatos revisables.

- [ ] Seleccionar y probar capas GIS oficiales para el laboratorio de setas
  - Contexto: para calibrar habitats por coordenada hacen falta DEM/topografia, vegetacion/cubiertas, litologia/geologia y, si existe, suelo. Prioridad actual: Catalunya; fallback posterior: Peninsula Iberica espanola. Canarias, Baleares, Ceuta y Melilla quedan fuera de alcance por ahora para reducir complejidad.
  - Ficheros relacionados: `docs/mushrooms/gis-layer-inventory-es.md`, `tmp/mushroom-lab/input/gis/icgc/`, `tmp/mushroom-lab/input/gis/ign-cnig/`, `mushroom-data/mushroom_gis_mappings.json`, `docs/mushrooms/mushroom-predictor-design-es.md`, `docs/mushrooms/mushroom-local-observation-lab-es.md`.
  - Criterio de aceptacion: documentar por capa URL/descarga/servicio, licencia, cobertura, resolucion, formato, CRS, campos usados y mapping interno; preferir raster/vector descargado, WCS o WFS; usar WMS solo para inspeccion visual. Generar features GIS por observacion y reporte de gaps de mapping.
  - Estado: capas v0 Catalunya seleccionadas e inventariadas. MVC50 cubre hosts/vegetacion/habitat/substrato preferente y sera fuente principal de sustrato predictivo mediante `LLVA_Subst`; ICGC `geologia-territorial-50000-geologic-v3r0-202412` cubre geologia/litologia como apoyo/trazabilidad; ICGC `model-elevacions-terreny-topografic-catalunya-5m-2009-2018` cubre DEM/topografia. ICGC `sols-25000-v1r1-202512` queda descartada para v0 por cobertura parcial, poca utilidad predictiva frente a MVC50 y mapping poco directo contra IDs internos. `cobertes-sol-v1r0-2024` queda como candidata futura, no necesaria para v0. El reconstructor GIS local ya consulta observaciones contra MVC50, geologia y DEM y muestra gaps/valores crudos en la UI de observaciones. Pendiente: consolidar esa salida con meteorologia historica y definir el formato final de features experimentales por observacion.

- [ ] Disenar agregacion de codigos geologicos ICGC para mappings de litologia
  - Contexto: la capa GeoPackage `geologia-territorial-50000-geologic-v3r0-202412` aporta 1.055 codigos distintos en `Codi`. Mapearlos uno a uno no parece pragmatico para v0 y probablemente convenga agregarlos en familias litologicas o categorias predictivas revisables.
  - Ficheros relacionados: `docs/mushrooms/gis-layer-inventory-es.md`, `mushroom-data/mushroom_gis_mappings.json`, `mushroom-data/mushroom_reference_catalogs.json`, futuros outputs locales del `observation_context_builder`.
  - Criterio de aceptacion: una vez seleccionadas todas las capas v0 y consultadas observaciones reales, proponer una estrategia trazable para agrupar `Codi`/`Descripcio`/`Codi_protolit` en familias o `lithology_type_ids`, empezando por codigos observados. No usar reglas opacas ni textos libres sin mapping revisable.
  - Estado: pendiente hasta cerrar la lista de capas v0 y generar la primera muestra de features GIS por observacion.

- [ ] Crear pantalla `GIS mappings` para mantener mappings de capas GIS contra catalogos
  - Prioridad: alta.
  - Contexto: el reconstructor GIS ya puede detectar valores crudos de capas locales y necesita traducirlos a IDs internos para que el futuro predictor no dependa de textos externos. Esa traduccion debe ser mantenible por UI, no por campos libres ni edits manuales de JSON.
  - Ficheros relacionados: `mushroom-data/mushroom_gis_mappings.json`, `mushroom-data/mushroom_reference_catalogs.json`, `rainmapper_core/mushroom_gis_lab.py`, `rainmapper-app/app/mushroom_profiles_ui.py`, `rainmapper-app/app/mushroom_gis_mappings_ui.py`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: pantalla tipo hub titulada `GIS mappings`, metricas compactas, filtros por fuente/campo/estado, tabla de valores GIS crudos y detalle editable; los destinos deben ser selects cerrados contra `host_taxa`, `forest_types`, `soil_types`, `lithology_types` y `habitat_features`; guardar debe validar con `scripts/validate-mushroom-data.py`; valores sin mapping detectados por el reconstructor deben poder revisarse y mapearse sin escribir IDs libres.
  - Estado: primera UI implementada localmente en `/mushrooms/gis-mappings`. Lista mappings exactos y candidatos pendientes de la ultima reconstruccion, muestra metricas/filtros, edita destinos mediante pastillas/selectores cerrados contra catalogos, valida antes de guardar y muestra errores de guardado en ventana emergente. El contrato de estados queda definido: `accepted` usable y computable, `pending_review` persistido pendiente de decision pero sin salida computable, `ignored` revisado y descartado sin IDs. La UI ya permite filtrar mapeados/pendientes y ordenar la tabla; geologia usa `Codi` como clave y `Descripcio` como contexto. Pendiente posible alta manual de valores no detectados, auditoria batch de valores unicos por capa si hace falta y mantenimiento de mappings por patron si se decide conservarlos.

- [x] Preparar rutas persistentes HA para el reconstructor GIS antes de promoverlo a flujo real
  - Prioridad: alta antes de ejecutar reconstrucciones GIS como funcionalidad HA real.
  - Contexto: el reconstructor local escribia salidas experimentales en rutas resueltas de forma duplicada por modulo. Eso provoco que el rebuild completo del modelo v0 pudiera leer observaciones desde defaults vacios en vez de la copia persistente. Las rutas de datos maestros y laboratorio deben tener un contrato unico antes de promover el flujo a HA real.
  - Ficheros relacionados: `rainmapper_core/mushroom_paths.py`, `rainmapper_core/mushroom_gis_lab.py`, `rainmapper_core/mushroom_observation_context.py`, `rainmapper_core/mushroom_observation_features.py`, `rainmapper_core/mushroom_learned_model.py`, `rainmapper_core/mushroom_store.py`, `rainmapper-app/app/web_server.py`, `rainmapper-local/docker-compose.yml`, `docs/mushrooms/gis-layer-inventory-es.md`, futuro flujo HA del predictor.
  - Criterio de aceptacion: separar explicitamente tres tipos de salida: datos y artefactos persistentes utiles bajo `/share/rainmapper/mushroom-data/`; artefactos temporales de ejecucion bajo `/tmp` o ruta temporal controlada; artefactos locales/QGIS solo bajo `tmp/mushroom-lab/` en desarrollo. La ruta debe ser parametrizable por entorno y el flujo HA no debe depender de paths del repo ni de `tmp/` versionado/ignorado.
  - Estado: implementado y simplificado el 2026-07-05 mediante `rainmapper_core/mushroom_paths.py`. Contrato vigente: defaults en `mushroom-data/` o `/app/mushroom-data/`; datos vivos, artefactos v0 y estado del modelo en `/share/rainmapper/mushroom-data/`; `docker-data/` representa `/share/rainmapper` en local; `tmp/mushroom-lab/` queda para pruebas locales explicitas/QGIS. No mantener fallbacks a `mushroom-lab` para el modelo operativo.

- [x] Validar en HA el flujo `Create species`, `Duplicate species`, `Archive species`, `Restore species` y `Delete permanently`
  - Contexto: `0.2.171` implementa la primera version funcional de ciclo de vida de especies con estrategia defensiva. Una especie activa solo puede archivarse; el borrado permanente solo aparece para especies archivadas.
  - Criterio de aceptacion futuro: `Create species` crea una especie draft validada y la abre; `Duplicate species` clona desde la especie actual con nuevo ID/nombre y reset de metadata/calibracion a draft/no calibrada; `Archive species` muestra el ID como solo lectura, crea backup y mueve el perfil completo a `archived/mushroom_profiles_archived.json`; `Restore species` devuelve el perfil si el ID activo esta libre; `Delete permanently` elimina solo del archivo con doble advertencia.
  - Estado: implementado en `0.2.171`; validado por el usuario al confirmar `0.2.172` instalada y funcionando correctamente en HA el 2026-06-28.

- [x] Implementar archivado/restauracion de especies
  - Contexto: `0.2.163` anade alta guiada de especies, pero no implementa todavia `Delete species`. El borrado no debe ser fisico/directo porque una especie eliminada podria necesitar recuperarse o auditarse.
  - Criterio de aceptacion: `Delete species` debe pedir confirmacion explicita escribiendo el `species_id`, crear backup previo, mover el perfil completo a un area/fichero `archived` o `deleted`, validar el modelo completo tras la operacion y mostrar aviso visible. La UI debe incluir `Restore deleted species`, bloquear la restauracion si el `species_id` ya existe de nuevo en perfiles activos y volver a validar antes de guardar. Documentado tambien en `docs/mushrooms/ui/profiles/mushroom-profiles-maintenance.md`.
  - Estado: implementado en `0.2.169` con archivado previo obligatorio, restauracion desde archivo y borrado permanente solo para especies archivadas con doble advertencia; validado por el usuario al confirmar `0.2.172` instalada y funcionando correctamente en HA el 2026-06-28.

- [ ] Implementar archivado/restauracion de entradas de catalogo
  - Contexto: el mantenimiento de `mushroom_reference_catalogs.json` no debe permitir borrado fisico directo de IDs porque esos IDs son vocabulario computable usado por perfiles, GIS mappings, relaciones internas y futuras calibraciones del motor de prediccion.
  - Criterio de aceptacion: `Delete reference catalog` debe bloquearse si el ID esta usado por perfiles, GIS mappings o relaciones internas salvo migracion explicita; si no esta usado, debe archivar la entrada completa en un area/fichero `archived` o `deleted` con backup previo, confirmacion escribiendo el ID exacto, validacion global posterior y aviso visible. La UI debe incluir `Restore deleted reference catalog`, bloquear restauraciones si el ID ya existe en el catalogo activo y validar todo antes de persistir. Documentado tambien en `docs/mushrooms/ui/reference-catalogs/reference-catalog-maintenance-proposal.md`.
  - Estado: pendiente para una version posterior a `0.2.163`.

- [ ] Rediseñar el tab `Ecology` del mantenimiento de especies
  - Contexto: aunque `0.2.159` separa el formulario de especies en tabs, `Ecology` sigue siendo demasiado largo porque agrupa todos los bloques de afinidades en una sola vista vertical.
  - Criterio de aceptacion futuro: proponer un formato mas mantenible para `host_affinities`, `forest_type_affinities`, `soil_affinities`, `lithology_affinities` y `habitat_feature_affinities`, por ejemplo subtabs internas, panel maestro-detalle, chips editables por grupo o tablas compactas por afinidad. Debe evitar duplicados antes de seleccionar, mostrar etiquetas humanas de catalogo y no hacer crecer mucho `web_server.py`.
  - Estado: tarea de diseño; no resolver con mas campos apilados.

- [ ] Crear mantenimiento visual de etiquetas de campos de setas
  - Prioridad: baja.
  - Contexto: `mushroom-data/mushroom_labels.json` centraliza nombres humanos de parametros, observaciones y futuros campos de setas en `en`, `es` y `ca` para que la UI no muestre claves raw como `rain_7d_min_mm` o `location.precision_m`.
  - Criterio de aceptacion futuro: pantalla de mantenimiento para revisar claves sin etiqueta, editar traducciones por idioma, validar que cada entrada tenga fallback `en` y detectar claves obsoletas/no usadas.
  - Estado: tarea futura; no bloquear el ajuste visual de `Parameters`.

- [ ] Revisar schema climatico de especies al definir el motor de prediccion
  - Prioridad: media, diferida hasta disenar el modelo de prediccion.
  - Contexto: `mushroom_profiles.json` contiene parametros climaticos utiles para UI y calibracion, pero algunos campos necesitan semantica explicita antes de convertirlos en logica de prediccion. Ejemplos detectados: `rain_30d_saturation_penalty_mm` parece penalizacion por exceso/saturacion, no lluvia optima 30d; `snowmelt_bonus` representa deshielo y podria no pertenecer conceptualmente al bloque `rainfall`; quizas falten umbrales 30d de lluvia minima/optima si el modelo necesita humedad acumulada mas alla de 15 dias.
  - Criterio de aceptacion futuro: documentar significado, unidad y efecto esperado de cada parametro climatico; decidir si el modelo necesita lluvia 30d min/optima/max ademas de saturacion; ubicar deshielo como campo propio si procede; actualizar labels/schema/validador/tests sin romper perfiles existentes ni calibracion.
  - Estado: tarea futura; no bloquear la validacion visual de `0.2.179`.

- [x] Hacer configurable el idioma de los mantenimientos de setas
  - Prioridad: baja/media.
  - Contexto: `rainmapper-app/config.yaml` expone `ui_language` con valores `en`, `es` y `ca`.
  - Criterio de aceptacion: leer `ui_language` desde opciones HA, aplicar el idioma a labels de parametros, observaciones, species y reference catalogs, y evitar fallback silencioso en la UI para detectar claves ausentes como `missing label`.
  - Estado: implementado en `0.2.177` para el dominio `mushrooms`; `0.2.178` completa labels visibles de parametros/valores controlados pendientes en la pantalla interna de especies. Queda como tarea futura extender el mismo patron al Control Board y Users.

- [ ] Extender `ui_language` a Control Board y Users
  - Prioridad: baja/media.
  - Contexto: `0.2.177` aplica el idioma configurable solo al dominio `mushrooms`. El resto de pantallas HA siguen teniendo textos propios fuera de `mushroom_labels.json`.
  - Criterio de aceptacion futuro: definir diccionario de labels fuera del dominio de setas o un sistema equivalente, aplicar `ui_language` a Control Board y Users sin mezclar idiomas, y validar que los textos faltantes sean visibles durante desarrollo.
  - Estado: tarea futura; no bloquear validacion de `0.2.178`.

- [ ] Prever importacion de observaciones de floradas en JSON y CSV
  - Contexto: cuando se aborde la fase de observaciones/calibracion del predictor de setas, la UI/backend deberan permitir importar observaciones externas para calibrar perfiles. JSON debe ser el formato estructurado preferente; CSV deberia soportarse si es viable para carga masiva o datos historicos mantenidos fuera de Rainmapper.
  - Ficheros relacionados futuros: modelo de observaciones por definir, futura UI de observaciones/calibracion, `rainmapper_core/mushroom_store.py` o modulo equivalente, validador de observaciones, documentacion `docs/mushrooms/`.
  - Criterio de aceptacion futuro: definir un schema estable de observacion, validar especie/fecha/ubicacion/fuente/confianza, rechazar duplicados o marcarlos claramente, importar con previsualizacion y errores por fila, no mezclar observaciones con `mushroom_profiles.json` ni `mushroom_reference_catalogs.json`, y conservar backup/registro de importacion.
  - Estado: tarea futura; no implementar durante `0.2.159`.

## Prioridad alta
- [ ] Controlar `host_taxa.rank` desde catalogo/valores permitidos
  - Contexto: en `/mushrooms/catalogs`, el campo `Rango` de `host_taxa` se edita actualmente como texto libre. Esto permite valores accidentales como `Pepito`, aunque semanticamente representa el rango taxonomico del host (`family`, `genus`, `species`, etc.).
  - Ficheros relacionados: `mushroom-data/mushroom_reference_catalogs.json`, `scripts/validate-mushroom-data.py`, `rainmapper-app/app/mushroom_catalogs_ui.py`, `rainmapper-app/app/web_server.py`, `tests/test_mushroom_data_validator.py`, `tests/test_web_server_auth.py`, `docs/mushrooms/ui/reference-catalogs/reference-catalog-maintenance-proposal.md`.
  - Criterio de aceptacion: decidir si los rangos viven como nuevo grupo controlado del catalogo o como enum validado del schema; renderizar `Rango` como `<select>` en la UI; validar CLI/backend contra los valores permitidos; preservar valores existentes si aparece alguno no contemplado mostrando error o estado missing, no guardando silenciosamente texto libre.
  - Estado: pendiente deliberado; no implementado en este bloque para evitar cambiar schema/catalogos mientras se cerraba la UI del laboratorio.

- [ ] Repetir backfill manual AEMET cuando el diario publique los dias pendientes
  - Contexto: el 2026-06-24 se ejecuto `scripts/aemet-backfill-30-days.py` con un catalogo enriquecido AEMET. AEMET diario solo devolvia datos efectivos hasta `2026-06-20`; el fichero horario descargado desde HA aporto `2026-06-23` y `2026-06-24`. Se genero primero un resultado temporal con 25.067 filas, 851 estaciones y 0 duplicados `Codi Estació` + `Data Local`, pero quedaban sin cubrir `2026-06-21` y `2026-06-22`. Tras el fix de `0.2.114`, el artefacto local vigente es `tmp/aemet-backfill-0.2.114-output/Aemet_incremental.csv`.
  - Ficheros relacionados: `scripts/aemet-backfill-30-days.py`, `tmp/aemet-backfill-0.2.114-input/estacions_aemet.csv`, `tmp/aemet-backfill-0.2.114-input/Aemet_incremental_from_HA.csv`, `tmp/aemet-backfill-0.2.114-output/Aemet_incremental.csv`.
  - Criterio de aceptacion: regenerar backfill de 30 dias con `--station-catalog tmp/aemet-backfill-0.2.114-input/estacions_aemet.csv` o con un catalogo actualizado descargado de HA; si HA aporta dias horarios mas recientes, fusionar dando prioridad a HA; validar 0 duplicados estacion/dia y revisar rango antes de subir manualmente a HA. El helper ya respeta el limite AEMET de 15 dias por llamada (`MAX_DAILY_RANGE_DAYS = 15`), conserva el formato de coma decimal del catalogo existente y permite `--skip-inventory` para reutilizar un catalogo descargado de HA sin llamar de nuevo al inventario AEMET. `tests/test_aemet_backfill_script.py` cubre un rango de 30 dias dividido en dos chunks, preservacion de formato de catalogo y ejecucion con inventario omitido.
  - Estado: preparado localmente para `0.2.114`; seguir `docs/history-safety.md` y no escribir directamente en historicos reales. Incidente detectado el 2026-06-24: un run HA posterior volvio a dejar `Aemet_incremental.csv` sin el backfill manual y con filas duplicadas/horarias por estacion/dia. Causa en codigo: `rainmapper_core/create_aemet.py` reconstruia y sobrescribia `Aemet_incremental.csv` solo desde `Aemet_hourly_incremental.csv`; el backfill diario no vive en el historico horario y por tanto desaparecia en el siguiente run. Fix publicado en `0.2.114`: `run_update()` lee el `Aemet_incremental.csv` existente, lo fusiona con el diario reconstruido desde horas, deduplica por `Codi Estació` + `Data Local` y hace que las horas recientes ganen en caso de conflicto. Cubierto por tests de regresion en `tests/test_create_aemet.py`. Tras publicar `0.2.114`, se genero `tmp/aemet-backfill-0.2.114-output/Aemet_incremental.csv`: 22.774 filas, 850 estaciones con datos, 0 duplicados estacion/dia, rango `20260525`-`20260624`, conserva exactamente las 1.600 filas del incremental HA de entrada para `20260623` y `20260624`. El endpoint diario siguio sin aportar `20260621` y `20260622`.

- [ ] Incorporar informacion diaria de viento en los incrementales
  - Contexto: el predictor de floradas necesitara viento medio diario y direccion, porque la exposicion de una ladera cambia mucho segun viento dominante; tambien interesa maxima/racha para penalizar dias secos o agresivos. Los incrementales actuales no guardan viento. La recomendacion inicial es definir columnas opcionales y normalizadas en km/h, por ejemplo `wind_avg_kmh`, `wind_min_kmh`, `wind_max_kmh`, `wind_gust_kmh`, `wind_direction_deg`, `wind_gust_direction_deg`, `wind_observation_count` y, cuando aplique, `wind_source_height_m`. La direccion media debe calcularse como media circular, no media aritmetica simple.
  - Meteocat/XEMA: `docker-data/Data/variables_xema.csv` confirma variables diarias ya agregadas para viento: `1500`-`1505` medias diarias a 10/6/2 m, `1506`-`1511` direcciones medias y `1512`-`1517` rachas maximas y direccion de racha. Es la fuente mas directa; priorizar 10 m (`VVM10`, `DVM10`, `VVX10`, `DVVX10`) y usar 6/2 m como fallback si falta 10 m. Las unidades XEMA son m/s, asi que habra que convertir a km/h si se adopta ese schema normalizado. Importante: estas variables no estan en el recurso de lecturas `nzvn-apee`; se publican en el recurso diario `7bvh-jvq2` (`Dades meteorològiques diàries de la XEMA`).
  - Meteoclimatic: el parser ya extrae `wind_current`, `wind_max` y `wind_bearing` desde el feed, con viento en km/h y direccion en grados. Hoy `create_total_meteoclimatic()` no copia esos campos al formato Rainmapper. Con el modelo actual de una fila diaria por estacion se puede guardar viento actual/ultimo, maxima 24 h y direccion, pero no una media diaria fiable salvo que se guarden lecturas crudas por ejecucion o se agreguen varias ejecuciones del mismo dia.
  - Wunderground: el scraper ya parsea viento. En modo mensual, que es el modo operativo actual (`MONTHLY=True`), Wunderground agrega `SpeedHigh_kmh`, `SpeedAv_kmh` y `SpeedLow_kmh`, pero no entrega direccion. El usuario confirmo visualmente el 2026-06-24 que la direccion `Wind` solo aparece en la vista diaria por observacion. Decision del 2026-06-24: no redisenar Wunderground ahora para direccion porque obligaria a duplicar o sustituir el scrape mensual con observaciones diarias, aumentando el tiempo del cuello de botella principal. Mantener velocidad media/min/max desde mensual y dejar `wind_direction_deg` vacio en Wunderground.
  - AEMET: una muestra real del endpoint diario AEMET del `2026-06-20` devolvio `velmedia`, `racha`, `dir` y `horaracha`. El endpoint global horario `/observacion/convencional/todas` devolvio `429 Too Many Requests` durante la prueba del 2026-06-24, pero una consulta aislada por estacion a `/observacion/convencional/datos/estacion/0002I` confirmo payload horario con `vv`, `vmax`, `dv` y `dmax`, ademas de `prec`, `ta` y `hr`. En esa muestra `vv/vmax` venian en m/s y `dv/dmax` en grados reales (`84.0`, `96.0`, `344.0`, etc.), no en decenas de grado. El runtime AEMET puede guardar viento horario opcional y derivar diario desde el historico horario; si el endpoint global responde `429`, debe seguir degradando sin romper `Run all`.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/create_aemet.py`, `scripts/aemet-backfill-30-days.py`, `rainmapper_core/sources/meteoclimatic_local/`, `rainmapper_core/sources/wunderground/`, `docker-data/Data/variables_xema.csv`, `tests/test_create_aemet.py`, `tests/test_aemet_backfill_script.py`, futuros tests de Meteocat/Meteoclimatic/Wunderground.
  - Criterio de aceptacion: definir schema comun opcional sin romper Tomap/GeoJSON ni historicos existentes; ampliar cada fuente con backups/pruebas segun `docs/history-safety.md`; cubrir conversion de unidades, agregacion diaria y media circular de direccion con tests; documentar en HA que el viento medio es el dato principal, que rachas/direccion pueden depender de fuente y que algunas fuentes solo dan aproximacion. El futuro predictor debe tratar `wind_direction_deg`/`wind_avg_kmh` vacios como "dato no disponible" y excluir esa parte del scoring o aplicar menor confianza, nunca interpretar vacio como viento cero ni como direccion norte.
  - Estado: primer corte iniciado el 2026-06-24: se definieron helpers/columnas normalizadas de viento y se conectaron Meteocat/XEMA, Meteoclimatic, Wunderground mensual y AEMET horario opcional. Meteocat/XEMA consulta `7bvh-jvq2` para variables diarias de 10/6/2 m, convierte m/s a km/h y prioriza 10 m con fallback; en prueba local relleno viento hasta `2026-06-21` y dejo vacios `2026-06-22` a `2026-06-24`. Confirmado contra Socrata el 2026-06-24: `nzvn-apee` tiene lluvia/temperatura hasta `2026-06-24T02:00:00`, mientras `7bvh-jvq2` tiene viento diario `1503`/`1512` solo hasta `2026-06-21T00:00:00`; no es un bug de Rainmapper sino retraso del dataset diario. Validado localmente con incrementales reales bajados de HA el 2026-06-24: `Meteocat_incremental.csv` quedo en 317625 filas, 25 columnas, 0 duplicados estacion/dia y 792 filas con viento XEMA. Wunderground mensual aporta `wind_avg_kmh`, `wind_min_kmh` y `wind_max_kmh`, pero no direccion; prueba local real solo Wunderground con 99/99 estaciones OK dejo `Wunderground_incremental.csv` en 67751 filas, 27 columnas, 0 duplicados estacion/dia, 2272 filas con velocidad y 0 con direccion. AEMET horario por estacion confirma `vv/vmax/dv/dmax`; `0.2.114` queda publicada con viento normalizado por fuente y fix de preservacion de backfill AEMET. `0.2.115` se publico con propagacion de humedad/viento a popups, pero en HA se observo `Generate maps` demasiado lento (~4:28) y tabla MapLibre ilegible en desktop/movil; no darla por buena. `0.2.116` queda publicada con agregacion Tomap de periodo vectorizada y el usuario reporto `Generate maps` en 1:59. `0.2.118` queda publicada con historial diario MapLibre compacto, columna de dias restaurada, direccion cardinal y cabecera sticky; validada localmente con `smoke-test`, `git diff --check` e inspeccion GHCR, y validada visualmente en HA por el usuario el 2026-06-24. `0.2.119` queda publicada con alineacion de subcolumnas en el historial MapLibre y mejoras WebUI/AEMET. `0.2.120` queda publicada para validar el experimento heatmap MapLibre.

- [ ] Evaluar historico de observaciones crudas para Meteoclimatic
  - Contexto: Meteoclimatic entrega `wind_current`, `wind_max` y `wind_bearing` en cada lectura RSS, pero el incremental diario actual usa una sola fila por `Codi Estació` + `Data Local`. Cada run posterior del mismo dia puede sobrescribir la lectura anterior, de modo que `wind_avg_kmh` es solo una aproximacion basada en la ultima observacion recibida, no una media diaria calculada.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/sources/meteoclimatic_local/`, `rainmapper_core/incremental_upsert.py`, futuros tests de historico Meteoclimatic, `docs/history-safety.md`.
  - Criterio de aceptacion: decidir si vale la pena crear un historico crudo tipo AEMET para Meteoclimatic, por ejemplo `Meteoclimatic_observations_incremental.csv` keyed por estacion + timestamp de lectura, y derivar desde ahi un diario con media/min/max de viento, direccion media circular y maxima/racha 24 h. Debe preservar el incremental diario actual para compatibilidad o migrarlo de forma controlada con backup, copia temporal y `check-history.py`.
  - Estado: implementacion inicial local iniciada el 2026-06-24: `rainmapper_core/meteoclimatic_history.py` mantiene `Meteoclimatic_observations_incremental.csv` con observaciones crudas deduplicadas por `Codi Estació` + `Data Lectura`, y deriva el incremental diario calculando media/min/max de viento actual, racha maxima y direccion media circular. Mantiene lluvia/temperatura/humedad con semantica de ultima observacion del dia para no cambiar de golpe el significado historico de Meteoclimatic. Validado localmente con incrementales reales bajados de HA el 2026-06-24: antes no habia columnas `wind_*`; tras el run se creo `Meteoclimatic_observations_incremental.csv` con 511 observaciones, 0 duplicados estacion/timestamp, y `Meteoclimatic_incremental.csv` quedo en 125778 filas, 27 columnas, 0 duplicados estacion/dia. Pendiente observar varios runs para confirmar que el crudo acumula varias lecturas del mismo dia y que `wind_observation_count` sube por estacion/dia.

- [ ] Definir retencion para `Meteoclimatic_observations_incremental.csv`
  - Contexto: desde `0.2.114`, Meteoclimatic guarda observaciones crudas por ejecucion para poder calcular viento medio diario y direccion media circular. Ese fichero no se limpia automaticamente y puede crecer mas de lo previsto en HA si hay varios runs diarios y muchas estaciones activas.
  - Ficheros relacionados: `rainmapper_core/meteoclimatic_history.py`, `rainmapper_core/rainmapper.py`, `docs/history-safety.md`, futuros tests de retencion.
  - Criterio de aceptacion: definir una politica explicita de retencion para observaciones crudas, por ejemplo 60/90 dias o un parametro configurable; aplicar la poda solo despues de derivar el incremental diario; validar que no se pierden agregados diarios ya consolidados en `Meteoclimatic_incremental.csv`; cubrir con tests que la retencion elimina observaciones antiguas sin borrar las recientes ni crear duplicados. Si se decide conservar raw a largo plazo para analisis futuro, evaluar particionado mensual/anual en lugar de un CSV unico.
  - Estado: pendiente. No bloquear la validacion inicial de `0.2.114`, pero revisarlo pronto si el fichero crece rapido en HA.

- [ ] Evaluar historico comun de runs por fuente
  - Contexto: actualmente `Data/source_status.json` guarda solo el ultimo estado por fuente y Wunderground mantiene metricas propias por estacion. Tras investigar `429` de AEMET se anadieron localmente contadores persistentes especificos de AEMET (`Aemet_rate_limit_metrics.json`) para ultimas 24h y runs consecutivos, visibles en la WebUI. Puede ser util generalizar un historico comun por fuente para analitica operativa.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/create_aemet.py`, `rainmapper-app/app/web_server.py`, futuros tests de historial de fuente.
  - Criterio de aceptacion: definir un formato tipo `source_run_history.jsonl` o CSV con una fila por fuente/run (`run_id`, timestamp, fuente, status, exit_code, duracion, filas, estaciones, stale, error_type/error_message resumido), retencion acotada y resumen WebUI sin crecer indefinidamente. Debe preservar `source_status.json` como ultimo estado rapido para visores y WebUI.
  - Estado: idea futura. No mezclar con el ajuste local actual salvo que se decida convertir los contadores AEMET en una primera implementacion generica.

- [x] Corregir upsert de historicos incrementales por estacion/dia
  - Contexto: los incrementales no son append puro; las fuentes pueden reenviar una estacion/dia con valores corregidos o campos complementarios incompletos. El patron anterior `update` + `merge` por todas las columnas podia dejar duplicados logicos si la fila nueva traia `NaN`.
  - Ficheros relacionados: `rainmapper_core/incremental_upsert.py`, `rainmapper_core/rainmapper.py`, `tests/test_incremental_upsert.py`.
  - Criterio de aceptacion: una sola fila por `Codi Estació` + `Data Local`; valores nuevos no nulos mandan; `NaN` nuevo conserva valor antiguo no nulo.
  - Estado: resuelto y validado localmente con datos copiados de HA. Meteocat paso de 28 filas duplicadas a 0; Meteoclimatic y Wunderground se mantuvieron sin duplicados. `local_update.sh`, `MODE=maps`, unit tests y smoke test pasaron. Validado tambien en HA `0.2.77`: `Run update` termino con exit code 0, Meteocat quedo en 316685 filas y `Generate maps` publico correctamente `v=0.2.77`.

- [x] Corregir inconsistencia de version en la app HA
  - Contexto: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y `rainmapper-app/CHANGELOG.md` deben avanzar juntos en cada bump de version.
  - Ficheros relacionados: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: version alineada en metadata HA, labels Docker y changelog.
  - Estado: resuelto.

- [x] Validar MapLibre en movil tras los ultimos ajustes
  - Contexto: MapLibre funciona bien en movil segun validacion manual/reportada por el usuario; se mantiene publicado junto a Leaflet de momento. La `0.2.47` anade capas raster Hybrid/Topographic y requiere validacion visual especifica.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`.
  - Criterio de aceptacion: cambio de capa mantiene estaciones, cambio de periodo conserva vista, popup es usable y no desplaza/molesta.
  - Estado: validado manualmente por el usuario en movil; pendiente de confirmacion automatizada.

- [x] Validar MapLibre raster y Leaflet fallback en HA/iPhone
  - Contexto: MapLibre `0.2.53` incorpora Satellite+ como base por defecto, Hybrid raster, Topographic raster y estilos vectoriales; Leaflet se mantiene como fallback con Topographic/Hybrid.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper_core/viewers/leaflet-viewer/`.
  - Criterio de aceptacion: Hybrid, Topographic y Satellite+ cargan correctamente, el cambio entre capas conserva marcadores, periodo, vista y popup en movil.
  - Estado: validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada. Historico: Leaflet quedaba como fallback publicado durante la transicion; desde 2026-07-08 es legacy bajo `publish_to_www`.
  - Riesgo si no se hace: decidir retirada de Leaflet sin confirmar que MapLibre cubre bien las capas raster que interesan.

- [x] Mantener sincronizadas raiz y app HA
  - Contexto: antes habia copias de scripts y visores en raiz y dentro de `rainmapper-app/app`.
  - Ficheros relacionados: `rainmapper_core/`, `rainmapper-app/Dockerfile`, `rainmapper-app/app/web_server.py`, `scripts/smoke-test.sh`, `scripts/build-push-ha-image.sh`.
  - Criterio de aceptacion: una unica fuente de verdad para core y visores compartidos; `rainmapper-app/app` solo contiene codigo especifico de HA.
  - Estado: resuelto por refactor core/app/local. HA se construye desde la raiz del repositorio y `scripts/smoke-test.sh` valida que `rainmapper-app/app` no vuelva a contener copias de core.
  - Riesgo residual: el build HA ya no soporta usar `rainmapper-app` como contexto Docker aislado; debe usarse la raiz del repo.

- [x] Proteger el historico CSV antes de cambios de pandas
  - Contexto: `Data/*_incremental.csv` es el valor principal del proyecto.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `Data/`, `/share/rainmapper/Data`, `scripts/backup-data.sh`, `scripts/check-history.py`, `docs/history-safety.md`.
  - Criterio de aceptacion: backup o prueba en directorio temporal antes de cambios que escriban historicos.
  - Estado: resuelto como practica operativa versionada. Antes de cambios que escriban CSV, usar backup/copia temporal y validar con `scripts/check-history.py`.

## Prioridad media

- [ ] Definir politica completa de retencion y restauracion de backups JSON de setas
  - Contexto: los guardados de perfiles, catalogos y observaciones crean backups automaticos timestamped antes de escribir. Para evitar acumulacion indefinida, la implementacion operativa conserva de momento los ultimos 20 backups automaticos por fichero y excluye de esa poda los backups manuales marcados con `.keep`.
  - Ficheros relacionados: `rainmapper_core/mushroom_store.py`, `rainmapper-app/app/web_server.py`, `rainmapper-app/app/mushroom_profiles_ui.py`, `rainmapper-app/app/mushroom_catalogs_ui.py`, `/share/rainmapper/mushroom-data/backups`, `docker-data/mushroom-data/backups`.
  - Criterio de aceptacion futuro: decidir retencion definitiva por fichero y entorno, mostrar/listar backups relevantes en la UI, distinguir automaticos de manuales protegidos, permitir restauracion guiada con validacion previa, bloquear restauraciones peligrosas si el JSON no valida y documentar limpieza segura sin borrar observaciones reales ni backups marcados como `keep`.
  - Estado: tarea conceptual pendiente. La medida provisional limita automaticos a 20 por fichero y permite crear backups manuales `.keep` desde las pantallas de especies y catalogos.

- [x] Incorporar AEMET OpenData como fuente horaria reciente
  - Contexto: el 2026-06-23 se probo con `AEMET_API_KEY` el endpoint oficial `/opendata/api/observacion/convencional/todas`. La llamada global devuelve observaciones horarias recientes de las ultimas 12 horas para todas las estaciones recibidas, con `idema`, `lat`, `lon`, `alt`, `ubi`, `fint` y `prec`. Segun metadatos AEMET, `prec` es la precipitacion acumulada durante los 60 minutos anteriores a `fint`, en mm; `fint` viene en UTC. En pruebas reales se obtuvo un dataset de unas 10k filas, 798 estaciones para la fecha filtrada y lluvia no nula en 23 estaciones. AEMET puede devolver `429 Too Many Requests` si se llama repetidamente durante pruebas.
  - Ficheros relacionados: `rainmapper_core/create_aemet.py`, `rainmapper_core/rainmapper.py`, `rainmapper_core/geocoding.py`, `rainmapper_core/tomap.py`, `rainmapper_core/geojson.py`, `rainmapper-app/config.yaml`, `rainmapper-app/run.sh`, `rainmapper-local/run.sh`, `rainmapper_core/viewers/maplibre-viewer/`, `tests/test_create_aemet.py`, `tests/test_tomap_builder.py`, `tests/test_tomap_to_geojson.py`.
  - Plan original ya ejecutado:
    1. Configuracion: anadir opcion/env para `AEMET_API_KEY` y flag de fuente `aemet` sin hardcodear secretos ni imprimir la clave.
    2. Cliente: hacer una sola llamada por ejecucion a `/observacion/convencional/todas`, leer la URL temporal `datos`, parsear tolerando caracteres no UTF-8 en `ubi`, y no llamar nunca estacion por estacion.
    3. Normalizacion: convertir cada registro horario con `prec` numerica a schema Rainmapper usando codigo estable `AEMET:{idema}` o equivalente que no colisione con fuentes existentes; preservar `fint` UTC como instante de fin de periodo horario.
    4. Historico: guardar filas horarias AEMET en un historico propio o adaptar el modelo incremental con identidad `source + idema + fint`; no forzar `Data Local` diaria sin decidir antes como se acumulan horas UTC frente a dias locales.
    5. Acumulados: construir acumulados de 1/7/14/21/30/60/90 dias desde las horas guardadas, dejando explicita la zona horaria. Recomendacion inicial: almacenar todo en UTC y definir el corte de periodos con una conversion controlada a la zona operativa solo en el agregador, no durante descarga.
    6. Degradacion: si AEMET devuelve `429`, timeout o error temporal, marcar fuente como `STALE`/`NOK` segun haya historico previo y continuar `Run all` con el resto de fuentes.
    7. Backfill opcional: usar `/valores/climatologicos/diarios/.../todasestaciones` para completar dias cerrados. Ese endpoint trae `prec` diario como texto con coma decimal, puede publicarse con retraso, no trae coordenadas y requiere unir con `inventarioestaciones/todasestaciones`. Desde el helper local `scripts/aemet-backfill-30-days.py`, el backfill manual genera un `Aemet_incremental.csv` diario en `tmp/` por defecto y puede preservar metadatos enriquecidos si se le pasa `--station-catalog`.
    8. Creditos legales: cuando una estacion venga de AEMET, mostrar en su ficha `Fuente: AEMET` e indicar que Rainmapper elabora la informacion a partir de datos de la Agencia Estatal de Meteorologia. En el panel de informacion/creditos de MapLibre, anadir una referencia agregada a AEMET cuando haya datos AEMET cargados. Si el dato original trae fecha de actualizacion, mostrarla o conservarla en metadatos. Desde la revision de atribuciones del 2026-06-23, MapLibre muestra tambien atribucion por fuente para Meteocat, Meteoclimatic y Wunderground, y ya no muestra la fila generica `Source:` en las fichas.
  - Seguridad de historicos: antes de implementar escritura real, seguir `docs/history-safety.md`: backup o copia temporal, prueba offline con fixtures, `scripts/check-history.py` antes/despues y no ejecutar contra `/share/rainmapper/Data` sin validacion.
  - Criterio de aceptacion: con una sola llamada global AEMET por `Run all`, se anaden o actualizan observaciones horarias deduplicadas; las estaciones AEMET aparecen en `Tomap`/GeoJSON con `Source=AEMET`; los acumulados no mezclan mal UTC/dia local; `429` no rompe el pipeline; MapLibre muestra atribucion AEMET en fichas de estacion y creditos generales cuando aplica; tests cubren parseo, deduplicado, acumulacion y fallo degradado.
  - Estado: implementado, publicado y validado/dado por bueno en HA hasta `0.2.111` para el alcance actual. Existe `rainmapper_core/create_aemet.py`, ejecutable como `python -m rainmapper_core.create_aemet`, que genera `Aemet.csv`, `Aemet_current_daily.csv`, `Aemet_hourly_incremental.csv`, `estacions_aemet.csv` y `Aemet_incremental.csv`. El historico horario AEMET guarda `prec` como `rain_mm` y, desde `0.2.105`, tambien `ta` como `temp_celsius` y `hr` como `humidity_percent` cuando AEMET los entrega; el diario calcula `max_temp_celsius`, `min_temp_celsius`, `max_humidity_percent` y `min_humidity_percent` desde las horas disponibles. El catalogo `estacions_aemet.csv` se rellena con identificador, nombre, altitud y coordenadas de AEMET, y preserva `Comarca`, `Municipi` y `Provincia` cuando las coordenadas no cambian. El reverse geocoding se ha extraido a `rainmapper_core/geocoding.py` y ahora lo comparten las fuentes existentes y AEMET: cuando una estacion AEMET es nueva, le faltan `Municipi`/`Provincia` o cambian sus coordenadas, se consulta Google Maps usando la misma `GMAP_API_KEY` que el resto de fuentes. `Comarca` no se usa como condicion para reintentar porque Google no la devuelve de forma fiable; si llega, se conserva, pero no debe forzarse. El CLI de AEMET permite `--skip-station-enrichment` solo para pruebas temporales. `create_aemet` y `aemet_api_key` estan anadidos a la configuracion HA/local, con `create_aemet=false` por defecto. `rainmapper_core.rainmapper` puede ejecutar AEMET como cuarta fuente opcional y degradar por el mecanismo general de `source_status.json`. El helper local `scripts/aemet-backfill-30-days.py` queda disponible para generar un `Aemet_incremental.csv` de dias cerrados desde climatologia diaria AEMET, con salida segura en `tmp/` y sin escribir historicos reales por defecto. Tras validar `0.2.108` en HA, `0.2.109` integra AEMET en el Tomap/GeoJSON estandar de HA mediante `--include-aemet true`, por lo que `/protected/maplibre/index.html`, Leaflet y Bokeh usan los mismos datos de produccion con AEMET cuando exista `Aemet_incremental.csv`. El publicador experimental `/local/rainmapper-maplibre-aemet/index.html` queda desactivado por flag en codigo y debe retirarse definitivamente cuando la ruta estandar quede estable durante uso real. GeoJSON infiere `AEMET:` como `Source=AEMET`. MapLibre incluye AEMET en el selector de fuentes y atribucion en ficha/panel de creditos. Prueba real de flujo completo en `tmp/aemet-flow-test/` genero 9120 filas horarias, 802 estaciones en `estacions_aemet.csv`, 802 filas diarias, Tomap completo y 7 GeoJSON con `Source=AEMET`, sin tocar historicos reales. Prueba real con reverse geocoding en `tmp/aemet-geocode-test-v2/` genero 802 estaciones enriquecidas: 802/802 con `Municipi`, 800/802 con `Provincia` y 7/802 con `Comarca`; casos revisados: `REUS AEROPUERTO -> Reus`, `BARCELONA AEROPUERTO -> El Prat de Llobregat`. El usuario copio ese `estacions_aemet.csv` enriquecido a `/share/rainmapper/Data` en HA. En `0.2.103`, HA ya ejecuto AEMET cuando `create_aemet=true`, pero fallo la ruta experimental al generar Tomap porque `merge_dataframes()` hacia un `pd.merge` por todas las columnas y pandas rechazo mezclar tipos `object`/`float64` en `max_temp_celsius`; `0.2.104` cambia esa union a `pd.concat(...).drop_duplicates()` y anade test de regresion. Tras probar `0.2.104`, el visor experimental mostraba solo estaciones AEMET dentro del antiguo `DISPLAY_BOUNDS` Catalunya/este; `0.2.105` elimina el recorte regional en MapLibre: el visor solo descarta coordenadas no numericas o fuera del rango geografico valido, encuadra el mapa usando las features cargadas y muestra `Invalid: N` en la cabecera cuando alguna feature queda descartada por coordenadas invalidas. El usuario reporto que con este cambio ya aparecen todas o casi todas las estaciones AEMET en HA. `0.2.106` anade atribuciones visibles por fuente en popups y creditos, y elimina la fila generica `Source:` del popup. En HA `0.2.107`, un `Run all` solo AEMET mostro que `Aemet_current_daily.csv` queda con una fila por estacion, pero `Aemet_incremental.csv` duplicaba estacion/dia al mezclar historico horario leido de CSV con filas nuevas: pandas leia `local_date` como entero desde disco y las filas actuales lo traian como texto. `0.2.108` corrige ese duplicado y queda validada/dada por buena por el usuario. `0.2.109` queda publicada en GHCR; `0.2.110` queda publicada en GHCR con atribuciones AEMET/Meteocat ajustadas a datos elaborados por Rainmapper. `0.2.111` queda publicada y validada/dada por buena en HA con atribuciones Meteoclimatic/Wunderground alineadas al mismo criterio. Pendiente dejar correr unos dias y despues eliminar el publicador experimental.

- [ ] Eliminar definitivamente la ruta/proceso experimental AEMET `/local/rainmapper-maplibre-aemet`
  - Contexto: al pasar AEMET a produccion, el codigo conserva `publish_aemet_experimental_maplibre()` desactivado mediante `PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE = False` como rollback temporal. Esa via fue util durante la implantacion de AEMET como nueva fuente, pero ya no debe quedar como camino paralelo si la ruta estandar sigue estable.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper_core/geojson.py`, documentacion de continuidad.
  - Criterio de aceptacion: tras validar varios ciclos reales con AEMET en `/protected/maplibre/index.html`, retirar el flag, la funcion experimental, rutas temporales `rainmapper-maplibre-aemet`, referencias de WebUI/documentacion y cualquier instruccion operativa que sugiera usar el visor experimental. Mantener solo el pipeline AEMET de produccion (`create_aemet`, Tomap/GeoJSON estandar y fuente `AEMET` en MapLibre).
  - Estado: pendiente deliberado; no quitar todavia para poder reactivar el modo test AEMET si la ruta estandar fallase.

- [ ] Evaluar archivado/particionado anual de historicos CSV
  - Contexto: con AEMET integrado, el volumen de `Aemet_incremental.csv` ronda unas 21k filas por mes en el backfill manual inicial. No es urgente: con ese ritmo, los CSV actuales deberian aguantar 1-2 anos sin problema operativo, pero conviene prever una estrategia antes de que los historicos crezcan demasiado. Esta linea no es solo tecnica: Rainmapper esta orientado a boletaires, y el valor futuro del historico sera poder comparar lluvia, temperatura y altitud del periodo actual con los mismos periodos de anos anteriores, sabiendo en que momentos hubo floradas. El particionado debe facilitar consultas historicas comparativas, no limitarse a reducir tamano de ficheros.
  - Contexto boletaire futuro: ademas de lluvia/temperatura/altitud, habra que cruzar cada zona con habitats por tipo de seta. A medio plazo conviene buscar mapas/capas de tipo de suelo y tipo de vegetacion (pinos, abetos, matorral, bosque mixto, etc.) y cruzarlas con una base de datos de habitats de setas por altitud, suelo y vegetacion.
  - Capa predictiva futura: valorar una capa asistida por IA que dibuje en el mapa una probabilidad orientativa por tipo de seta y zona. Las senales candidatas serian epoca del ano, lluvia acumulada reciente, temperatura, altitud, tipo de suelo, vegetacion/habitat de cada seta y, si se consigue, registros historicos de floradas por zona para ajustar mejor el modelo.
  - Ficheros relacionados: `Data/*_incremental.csv`, `rainmapper_core/rainmapper.py`, `rainmapper_core/incremental_upsert.py`, `rainmapper_core/tomap.py`, `scripts/check-history.py`, `docs/history-safety.md`.
  - Criterio de aceptacion: definir si se particiona por ano (`Aemet_incremental_2026.csv` o subdirectorios), como se mantiene el archivo vigente para upserts diarios, como reconstruye `Tomap` los periodos 1/7/14/21/30/60/90 sin leer mas de lo necesario, como se consultan periodos equivalentes de anos anteriores para comparativas boletaires, como se integran capas futuras de altitud/suelo/vegetacion/habitat, como se podria publicar una capa de probabilidad por especie en MapLibre, y como se validan migraciones con backups y `check-history.py`.
  - Estado: mejora futura no urgente; no abordar hasta tener mas ciclos reales y una estimacion mejor del crecimiento por fuente.

- [x] Llevar perfiles de setas a HA y crear mantenimiento WebUI
  - Contexto: los defaults versionados del modelo viven en `mushroom-data/` (`mushroom_profiles.json`, `mushroom_reference_catalogs.json`, `mushroom_gis_mappings.json`). En HA, la copia viva editable debe mantenerse en `/share/rainmapper/mushroom-data/`; los defaults solo sirven para instalacion inicial, tests y recuperacion.
  - Ficheros relacionados: `mushroom-data/mushroom_profiles.json`, `mushroom-data/mushroom_reference_catalogs.json`, `mushroom-data/mushroom_gis_mappings.json`, `rainmapper_core/mushroom_store.py`, `scripts/validate-mushroom-data.py`, `tests/test_predictor_profiles.py`, `tests/test_mushroom_data_validator.py`, `tests/test_mushroom_store.py`, `rainmapper-app/app/web_server.py`, `rainmapper-app/Dockerfile`, `rainmapper-app/DOCS.md`, almacenamiento persistente en `/share/rainmapper/mushroom-data/`.
  - Criterio de aceptacion backend: incluir los tres JSON base en la imagen HA, copiar/sembrar defaults en `/share/rainmapper/mushroom-data/` si faltan, no sobrescribir ficheros persistentes durante actualizaciones, proteger guardados con `scripts/validate-mushroom-data.py`, escribir de forma atomica y conservar backups antes de reemplazar datos. `mushroom_gis_mappings.json` queda como dato validable/consultable en esta fase, sin editor completo hasta una fase posterior.
  - Estado: backend minimo implementado en `rainmapper_core/mushroom_store.py` y endpoints admin en `web_server.py`: validar, exportar, plantilla vacia e importar/reemplazar perfiles/catalogos. WebUI de catalogos implementada en `/mushrooms/catalogs` y primera WebUI de perfiles implementada en `/mushrooms/profiles` en `0.2.158`, con listado de especies, buscador, editor guiado, selects contra catalogos para ecologia, guardado validado con backup y panel avanzado JSON/import-export/plantilla. Pendiente posterior: validar visualmente en HA, mejorar ergonomia si hace falta y documentar uso en `rainmapper-app/DOCS.md`.

- [x] Revisar validaciones cruzadas del mantenimiento de catalogos de setas
  - Contexto: la WebUI de `mushroom_reference_catalogs.json` permite editar entradas de `host_taxa`, incluyendo `parent_id`, pero la pantalla no muestra todavia una validacion de formulario especifica que confirme que ese `parent_id` existe dentro del catalogo. El validador global debe seguir siendo la fuente de verdad, pero la UI necesita feedback mas claro antes/despues de guardar.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `scripts/validate-mushroom-data.py`, `mushroom-data/mushroom_reference_catalogs.json`, `docs/mushrooms/ui/reference-catalogs/reference-catalog-maintenance-proposal.md`, `tests/test_mushroom_data_validator.py`, `tests/test_web_server_auth.py`.
  - Criterio de aceptacion: para `host_taxa.parent_id`, bloquear o avisar claramente si el ID no existe en `catalogs.host_taxa`; aplicar el mismo criterio a referencias internas de catalogo (`forest_types.dominant_host_ids`, `forest_types.soil_bias_ids`, `lithology_types.parent_soil_tendency_ids`) y mostrar los errores en la pantalla junto al campo afectado o en un panel de cross references. Cubrir con tests.
  - Estado: implementado en `0.2.157` para `host_taxa.parent_id`, `forest_types.parent_id`, `forest_types.dominant_host_ids`, `forest_types.soil_bias_ids` y `lithology_types.parent_soil_tendency_ids`, con feedback visible en el detalle de catalogo y tests. No cambia datos automaticamente. Mantener abierta la revision conceptual de la metrica `Reference errors` y ampliar validaciones cuando se implemente mantenimiento GIS/modelo completo.

- [ ] Revisar semantica de `Reference errors` cuando el modelo de setas este completo
  - Contexto: la primera UI de catalogos mostro un contador `Broken refs` calculado por escaneo textual amplio y dio falsos positivos con campos GIS validos (`mapping_type` e `inputs` de reglas derivadas). El fix local lo sustituye por `Reference errors`, derivado de errores reales del validador, para que no contradiga `0 errors · 7 warnings`.
  - Criterio de aceptacion: cuando esten disenados el mantenimiento de perfiles, el mantenimiento GIS y el motor de prediccion, revisar si la metrica debe contar solo errores bloqueantes del validador, referencias faltantes por area (`profiles`, `catalogs`, `gis`) o tambien dependencias futuras del motor. La UI no debe volver a mostrar como rotas cadenas tecnicas GIS que no sean IDs internos de catalogo.
  - Estado: pendiente deliberado para fase posterior; no bloquear la publicacion del fix de ingress/catalogos.

- [ ] Normalizar codigos internos de todas las fuentes con prefijo de origen
  - Contexto: AEMET se normaliza internamente como `AEMET:{idema}` para evitar colisiones y permitir trazabilidad, aunque MapLibre lo muestra sin el prefijo. Las fuentes historicas todavia dependen de inferencias por forma del codigo (`ES...` largo para Meteoclimatic, `I...` para Wunderground, longitud 2 para Meteocat).
  - Ficheros relacionados: historicos `*_incremental.csv`, catalogos `estacions_*.csv`, `rainmapper_core/geojson.py`, `rainmapper_core/tomap.py`, `rainmapper_core/rainmapper.py`, visores y tests.
  - Criterio de aceptacion: definir prefijos estables por fuente, migrar historicos/catalogos con backup y pruebas segun `docs/history-safety.md`, mantener compatibilidad o migracion controlada de `ignore_stations_tomap.txt` y publicar GeoJSON con `Source` sin inferencias fragiles.
  - Estado: mejora futura. No mezclar con la validacion AEMET actual; requiere plan especifico de migracion de historicos.

- [ ] Validar MapLibre protegido en HA/Cloudflare
  - Contexto: la ruta protegida MapLibre ya fue validada manualmente en HA `0.2.82`: `/protected/maplibre/index.html` pide login, `admin` funciona desde Mac+iPhone y un usuario normal queda limitado a un dispositivo. La version `0.2.83` amplia el backend a `users.json` con `username`, `name`, `email`, roles `free/basic/pro/admin` y `max_devices`. El usuario valido en HA que el primer login crea `users.json`; despues se decide retirar por completo el formato antiguo.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper_core/viewers/maplibre-viewer/`, `users.example.json`, `tests/test_web_server_auth.py`, `rainmapper-app/DOCS.md`.
  - Criterio de aceptacion: publicar nueva version HA con `users.json` como unico formato, validar login por `username`, admin ilimitado, usuario `free` limitado por `max_devices`, reutilizacion de dispositivo registrado, gestion WebUI de usuarios/dispositivos desde Ingress/Home Assistant y GeoJSON inaccesible sin sesion. Cloudflared debe apuntar a `http://<HA_IP>:8099` para `rainmap.nomentero.com` y no depender de `/local/rainmapper-maplibre/index.html`. Tras uso real, decidir si se retira el fallback local de MapLibre o si se mantiene como emergencia protegida externamente por Cloudflare Access.
  - Estado: protegido basico validado manualmente en HA `0.2.82`; ampliacion `users.json`/`max_devices` publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.83`; retirada del formato antiguo y WebUI de gestion publicadas en `0.2.84`; correccion del auto-refresh publicada en `0.2.85`; gestion de contrasenas `Set password`/`Reset password` publicada como imagen `0.2.86`. El 2026-06-22 se comprobo la exposicion externa: `rainmap.nomentero.com/protected/maplibre/data/01d.geojson` devuelve `401` sin sesion, HTTP redirige a HTTPS, HSTS esta activo con `includeSubDomains`, y los subdominios fallback `leaflet.nomentero.com`/`maplibre.nomentero.com` quedan detras de Cloudflare Access tambien para GeoJSON. Pendiente de uso real con companeros usando login Rainmapper y de decidir si se retira el fallback local.

- [ ] Observar prueba externa con usuarios reales
  - Contexto: desde el 2026-06-22 hay dos companeros probando la ruta protegida con login Rainmapper. Se han creado cuatro usuarios: usuario propio con rol `admin` y limite configurado de 2 dispositivos; `Diegomovil`, `Diegopc` y `Ramonmovil` con rol `free` y 1 dispositivo cada uno. No se ha avisado a los companeros del limite de dispositivo para observar si comparten credenciales.
  - Ficheros relacionados: `/share/rainmapper/users.json`, `/share/rainmapper/devices.json`, WebUI `Users`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: los usuarios pueden entrar desde su dispositivo previsto; si comparten acceso o cambian de dispositivo/navegador, el bloqueo por `max_devices` queda visible y gestionable desde WebUI Users; no aparecen errores de sesion inesperados ni exposicion de GeoJSON sin login.
  - Estado: prueba en curso. HA ejecuta `Run all` con schedule `01:45 - 05:00 - 08:00 - 11:00 - 14:00 - 17:00 - 20:00 - 23:55`. `0.2.101` quedo validada manualmente para WebUI `Users`; `0.2.111` queda validada/dada por buena en HA con AEMET ya integrado en el visor protegido estandar. Pendiente observar varios ciclos reales y comportamiento de los usuarios externos.

- [x] Cerrar exposicion publica de repo, fallbacks y paquetes antiguos
  - Contexto: antes de compartir el visor con companeros, se reviso la seguridad externa. El repo publico exponia codigo y logica de descarga, y `maplibre.nomentero.com/local/rainmapper-maplibre/data/01d.geojson` llego a responder `200` con GeoJSON sin login antes de proteger el subdominio.
  - Ficheros relacionados: `docs/codex-handoff.md`, `docs/architecture.md`, `docs/decisions.md`; configuracion real en GitHub/GHCR/Cloudflare fuera del repo.
  - Criterio de aceptacion: repo GitHub privado; `rainmap.nomentero.com` fuerza HTTPS y mantiene datos protegidos por login Rainmapper; fallbacks `leaflet` y `maplibre` exigen Cloudflare Access; GHCR conserva solo la imagen actual necesaria para HA.
  - Estado: completado. HTTP->HTTPS activo, HSTS activo con `max-age=2592000; includeSubDomains`, `x-content-type-options: nosniff` presente, `router`, `leaflet` y `maplibre` redirigen a Cloudflare Access, y ruta protegida de datos en `rainmap` devuelve `401` sin sesion segun comprobaciones previas. `0.2.132` queda validada visualmente en HA el 2026-06-25. Tras esa validacion, se puso el repo GitHub en privado (`private=true`, `visibility=private`, rama `inicial`) y se limpio GHCR remoto borrando 75 versiones/entradas antiguas. Auditoria final: GHCR conserva solo `0.2.132,latest` con digest `sha256:801e77ff582afe64d47dd7f56935e424732ee687ab98b5436afaf789c49762ad` y cuatro auxiliares sin tag del mismo push multi-arch.

- [x] Validar identidad de usuario en cabecera MapLibre
  - Contexto: el visor MapLibre protegido ya recibe `username`, `name`, `email` y `role` en login y en `/auth/session`.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA, tras login y tras recargar una sesion guardada, la cabecera muestra fecha generada y `username (role)` en dos lineas compactas sin romper el layout movil.
  - Estado: implementado y validado manualmente en HA durante las validaciones posteriores hasta `0.2.111`; las capturas de uso muestran `username (role)` en la cabecera protegida. Pendiente solo de cobertura automatizada si se quiere fijar layout por test.

- [x] Ajustar umbral de hover MapLibre
  - Contexto: `0.2.87` muestra temporalmente el nivel de zoom en la cabecera de MapLibre, debajo de `Generated`, para decidir a partir de que zoom conviene activar el hover de estaciones.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: tras probar en HA, confirmar el valor de `maplibre_hover_zoom` y retirar el indicador temporal de zoom si ya no hace falta.
  - Estado: publicado inicialmente en `0.2.95` con umbral `7`; `0.2.135` lo hace configurable desde HA como `maplibre_hover_zoom` con default `6.0` y admite decimales. Pendiente de validar en HA/movil y retirar el indicador temporal si ya no hace falta.

- [x] Validar estacion con lluvia mas cercana en popup de terreno MapLibre
  - Contexto: el popup de terreno por pulsacion larga muestra altitud DEM y coordenadas del punto. Para aportar contexto sin reverse geocoding, se anade un bloque `Nearest rainy station` calculado en cliente desde las estaciones cargadas en el mapa para el periodo actual.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA/movil, una pulsacion larga muestra altitud, coordenadas, estacion con lluvia mas cercana, lluvia acumulada del periodo seleccionado, distancia, municipio/provincia de esa estacion y altitud de estacion; si no hay estaciones con lluvia en el mapa, muestra un mensaje explicito.
  - Estado: publicado en `0.2.96` y validado manualmente por el usuario en HA el 2026-06-25.

- [x] Validar settings MapLibre por dispositivo
  - Contexto: el visor MapLibre protegido guarda preferencias por `device_id` dentro de `/share/rainmapper/devices.json`, no en `users.json`, para que cada navegador/dispositivo conserve su configuracion independiente.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`, `tests/test_web_server_auth.py`.
  - Criterio de aceptacion: en HA, cambiar Settings y cerrar el panel guarda `period`, `min_rain_mm`, `map_style`, `language`, `last_rains_history`, `station_sources`, `terrain_enabled`, `terrain_exaggeration` y, solo bajo accion explicita, `map_view`; cambiar periodo desde la barra inferior, mover el mapa normalmente, usar el boton rapido de capas o usar el boton compacto `2D`/`3D` no debe escribir `devices.json`. Al recargar o volver a entrar desde el mismo dispositivo se restauran esos valores desde `devices.json`. Borrar el dispositivo desde la WebUI debe borrar tambien sus preferencias.
  - Estado: validado manualmente por el usuario en HA hasta `0.2.111`. Incluye persistencia por dispositivo en `devices.json`, boton rapido de seleccion de mapa entre `2D`/`3D` y la brujula sin persistir `map_style`, separacion equivalente entre periodo visible de la barra inferior y periodo preferido guardado desde Settings, selector de idioma ES/EN/CA y boton de Settings para guardar la vista actual como predeterminada (`map_view`) sin escribir continuamente al mover el mapa. Cubierto por tests backend de saneado/almacenamiento.

- [x] Validar i18n ES/EN/CA en MapLibre
  - Contexto: se decide no tocar de momento la WebUI HA y aplicar multiidioma solo al visor MapLibre, usando lenguaje de usuario no tecnico: lluvia/mapa/estacion/fuente/relieve.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/translations.json`, `rainmapper-app/app/web_server.py`, `tests/test_web_server_auth.py`, `tests/test_maplibre_translations.py`.
  - Criterio de aceptacion: en HA, cambiar idioma desde Settings actualiza textos visibles de MapLibre en ES/EN/CA, guarda `language` en `devices.json` al cerrar Settings y lo recupera al volver desde el mismo dispositivo. Los cambios rapidos de mapa/periodo/2D-3D fuera de Settings deben mantener el criterio actual de no persistir preferencias.
  - Estado: validado manualmente por el usuario en HA `0.2.99`: el selector de idioma funciona bien, `translations.json` se carga y el idioma queda como setting por dispositivo. Imagen publicada `ghcr.io/cginebrosa/rainmapperha:0.2.99` con digest `sha256:2ebebc6f0da239e22f23e7bb3e1eddddedf61fd1f172a11dcf76d7bdbb8a82b5`.

- [ ] Estudiar visita guiada MapLibre con globos contextuales
  - Contexto: `0.2.112` anade el boton final `?` con ayuda del mapa en ES/EN/CA. Una mejora mas guiada seria mostrar globos breves en el primer login de un dispositivo para explicar controles clave, o permitir lanzar la misma visita a voluntad desde la ayuda.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`, `rainmapper_core/viewers/maplibre-viewer/translations.json`, `rainmapper-app/app/web_server.py`, `tests/test_maplibre_translations.py`.
  - Criterio de aceptacion: definir si la visita aparece automaticamente solo una vez por dispositivo, si se activa manualmente desde el panel `?`, o ambas cosas. Si se persiste el estado, guardarlo por dispositivo en `devices.json` sin bloquear el mapa ni escribir continuamente. Los globos deben ser cerrables, no tapar controles criticos en movil, tener textos ES/EN/CA y quedar documentados en la ayuda del mapa.
  - Estado: idea futura. Priorizar una UX ligera: no convertir la ayuda en un tutorial obligatorio ni molesto para usuarios recurrentes.

- [ ] Explorar capas MapLibre por metrica y heatmap
  - Contexto: los GeoJSON por periodo ya incluyen, por estacion, lluvia acumulada (`Total`), temperatura maxima/minima, humedad maxima/minima, viento medio/direccion/racha y campos diarios recientes (`Pluja_Diaria_*`, `Temp_Max_*`, `Hum_Max_*`, `Wind_Avg_*`, etc.). Hoy MapLibre colorea puntos principalmente por precipitacion, pero esos mismos atributos permitirian capas exploratorias adicionales sin tocar historicos CSV ni backend.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`, `rainmapper_core/viewers/maplibre-viewer/translations.json`, `rainmapper-app/app/web_server.py`, futuros tests de settings backend si se promociona a produccion.
  - Criterio de aceptacion: validar primero en una ruta experimental no protegida, separada de los usuarios actuales, con un boton `Heatmap`, selector `Layer metric` (`Rain`, `Max temp`, `Min temp`, `Max humidity`, `Min humidity`, `Wind`), boton rapido de metrica similar al selector rapido de capas y sliders de opacidad/radio. Mantener el filtro existente de lluvia minima para los puntos, pero hacer que el heatmap use todas las estaciones validas del periodo filtradas por fuentes activas. El selector de metrica debe afectar siempre a puntos y leyenda; el boton `Heatmap` solo anade o quita la capa de densidad. La UI debe dejar claro que el heatmap es una densidad ponderada por estaciones, no una interpolacion meteorologica exacta. Si se promociona al visor protegido de produccion, todas las preferencias nuevas (`heatmap` activo/inactivo, metrica seleccionada, opacidad y radio) deben persistirse por `device_id` en `devices.json` igual que el resto de settings MapLibre, con defaults compatibles para dispositivos existentes.
  - Estado: experimento publicado en `0.2.120` y ampliado hasta `0.2.132`: se anadio una variante publica `/local/rainmapper-maplibre-heatmap/index.html` generada por el publicador HA con `experimentalHeatmap: true`. El codigo usa una fuente GeoJSON separada para el heatmap (`stations-heatmap`) con todas las estaciones validas del periodo filtradas por fuente activa, y otra fuente para puntos filtrados por lluvia minima/fuente. Tras validar visualmente `0.2.123`, `0.2.124` promociono la funcionalidad al visor protegido con restriccion UI completa. `0.2.125` corrige que los botones ocultos se mostrasen por CSS en usuarios no admin y ajusta la escala de metricas no lluvia a min/max real de las estaciones filtradas del periodo seleccionado; `0.2.126` hace que todas las metricas, incluida lluvia, traten valores ausentes como sin dato, no como cero, y excluye esas estaciones del heatmap de la metrica activa. `0.2.127` corrige la persistencia backend por `device_id` de metrica, heatmap activo/inactivo, opacidad, radio, intensidad y curva de peso en el visor protegido autenticado con usuario `admin`; los cambios de Settings se guardan al cerrar Settings, no en cada movimiento de slider. La ruta experimental publica muestra controles para pruebas pero no guarda preferencias en `/auth/device-settings`. `0.2.132` corrige el solapamiento horizontal del fondo sticky que tapaba letras de la cabecera; `0.2.130` ajusto el `top`/fondo de la cabecera sticky del historial para no dejar ver filas por encima; `0.2.129` habia restaurado el scroll completo del popup tras el scroller interno no deseado de `0.2.128`. `0.2.133` valida en HA que el acceso del visor protegido deja de depender directamente de `role=admin` y pasa a dos permisos por usuario en `users.json`/WebUI: `can_use_heatmap` para boton/pestana Heatmap y `can_use_layer_metrics` para boton rapido/selector `Layer metric`; los admins nuevos se crean con ambos permisos activos por defecto. `0.2.134` valida en HA el ajuste de espaciado que evita que la cabecera sticky del historial tape el titulo del desplegable. `0.2.135` publica defaults HA para dispositivos sin settings guardados (`maplibre_heatmap_weight_curve=soft`, `maplibre_heatmap_opacity=65`, `maplibre_heatmap_radius=90`, `maplibre_heatmap_intensity=70`) y un boton para restaurar esos defaults desde Settings, pero en HA se detecta que el backend pisa los valores ausentes del device con radio/intensidad `100`. `0.2.136` corrige usuarios/dispositivos nuevos preservando la ausencia de esos campos en `devices.json`, pero en HA se detecta que el reset puede seguir usando un `config.js` protegido cacheado si se cambian defaults y solo se reinicia la app. `0.2.137` sirve ese `config.js` con `Cache-Control: no-store, max-age=0` y queda validada/dada por buena en HA para que reset recoja cambios de `config.yaml` tras reinicio sin limpiar cache manualmente.

- [ ] Afinar parametros recomendados de IDW MapLibre tras pruebas reales
  - Contexto: la capa experimental `IDW` debe interpretarse como campo meteorologico aproximado, no como densidad de estaciones. El radio de influencia y el tamano de celda se configuran en km desde `config.yaml`; los valores iniciales son solo punto de partida para pruebas en HA.
  - Ficheros relacionados: `rainmapper-app/config.yaml`, `rainmapper-app/DOCS.md`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `docs/decisions.md`.
  - Criterio de aceptacion: tras validar visualmente lluvia, temperatura, humedad y viento en varios niveles de zoom, documentar valores recomendados para `maplibre_estimated_field_radius_*_km`, `maplibre_estimated_field_grid_*_cell_km`, potencia de suavizado y opacidad. Si en zooms bajos el coste o la granularidad no son satisfactorios, estudiar un multiplicador configurable por nivel/rango de zoom para aumentar el tamano efectivo de celda sin perder resolucion fisica en zoom medio.
  - Estado: pendiente de pruebas reales en HA. `0.2.144` muestra en Settings el valor tecnico efectivo seleccionado para facilitar estas pruebas. `0.2.145` anade cache por clave de calculo para evitar recalcados IDW duplicados. Viento se trata de momento como variable escalar igual que el resto; una visualizacion vectorial con flechas queda como mejora futura.

- [ ] Reutilizar el patron IDW para futuras capas calculadas en cliente
  - Contexto: el predictor de floradas de setas probablemente necesitara pintar una capa derivada de datos meteorologicos, terreno y reglas de scoring. La capa IDW ya establece un patron para calcular en el dispositivo, no en la Raspberry Pi, y limitar el trabajo al viewport visible.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `docs/architecture.md`, futuros datos/configuracion del predictor.
  - Criterio de aceptacion: antes de implementar el predictor, definir source/layer propios, permiso de acceso, settings por dispositivo, parametros tecnicos en `config.yaml`, cache por clave de calculo, invalidacion explicita cuando cambien datos/filtros y debounce para eventos de mapa. Evitar recalcular la capa si la clave de periodo, vista, metrica/fuente y parametros no cambia.
  - Estado: idea futura documentada a partir del patron IDW.

- [x] Validar controles compactos MapLibre en movil
  - Contexto: en iPhone, la columna derecha de botones flotantes ocupaba demasiada altura y la leyenda podia acercarse mas al borde izquierdo.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA/movil, los botones de la derecha quedan compactos sin perder facilidad de pulsacion, con separacion visual minima de 1px, margen derecho reducido y paneles laterales de Settings/mapas/creditos correctamente alineados. La leyenda queda mas pegada a la izquierda sin cortarse.
  - Estado: validado manualmente por el usuario en HA `0.2.100`. Incluye botones moviles de 34px, separacion de 1px, margen derecho de 6px, leyenda a 4px del margen izquierdo y etiquetas compactas `1d`/`7d`/... en la barra inferior. Imagen publicada `ghcr.io/cginebrosa/rainmapperha:0.2.100` con digest `sha256:03b2d0cc42a08069bddbb7f6a4e7cee05aae5345dd29a40438a79e4d1b8f5134`.

- [ ] Validar zoom visible temporal MapLibre
  - Contexto: se ha anadido localmente un indicador `Zoom X.XX` en la cabecera compacta de MapLibre para confirmar el umbral real de hover.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA/movil el zoom visible cambia al hacer zoom y permite confirmar que `maplibre_hover_zoom` es adecuado.
  - Estado: publicado en `0.2.95` con umbral `7`; `0.2.135` lo hace configurable desde HA como `maplibre_hover_zoom` con default `6.0` y admite decimales. Retirar el indicador al fijar el umbral definitivo.

- [x] Crear gestion WebUI de usuarios y dispositivos
  - Contexto: el backend ya soporta roles `free`, `basic`, `pro`, `admin`, `username`, `name`, `email`, `max_devices` opcional y permisos MapLibre `can_use_heatmap`/`can_use_layer_metrics`/`can_use_estimated_field` en `users.json`; la WebUI local anade una pagina `Users`.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper-app/DOCS.md`, `/share/rainmapper/users.json`, `/share/rainmapper/devices.json`.
  - Criterio de aceptacion: desde la webUI HA se pueden listar usuarios, crear/desactivar/borrar usuarios, cambiar rol, cambiar `max_devices`, cambiar permisos MapLibre de heatmap/metrica/IDW, establecer una nueva contrasena, forzar cambio de contrasena y gestionar dispositivos asociados. Borrar un usuario debe borrar tambien todos sus dispositivos asociados.
  - Requisito especifico: para cada usuario debe poder borrarse un dispositivo concreto o borrar todos sus dispositivos.
  - Estado: implementado y validado manualmente en HA hasta `0.2.101`. La pagina `Users` permite crear usuarios, editar nombre/email/rol/status/max_devices, establecer nuevas contrasenas, forzar cambio de contrasena mediante `must_change_password`, borrar dispositivos individuales o todos los de un usuario y borrar el usuario junto con sus dispositivos. En `0.2.101` se publica y valida una mejora de `Users` con cabecera fija, boton manual `Refresh` sin refrescar navegador, busqueda tipo texto libre sobre usuarios/dispositivos y preservacion de posicion de scroll al refrescar. Cambios posteriores: la pagina tambien permite activar/desactivar permisos `Heatmap access`, `Metric selector access` y `Estimated field access`, y los admins nuevos nacen con esos permisos activos. Cubierto por `tests/test_web_server_auth.py`.

- [ ] Revisar arquitectura de permisos de funcionalidades
  - Contexto: actualmente hay pocos permisos funcionales y se han anadido directamente en `users.json` como flags por usuario (`can_use_heatmap`, `can_use_layer_metrics`, `can_use_estimated_field`). Esto es pragmatico para la fase actual, pero no escala bien si aparecen mas funcionalidades, mapas, zonas, modulos o perfiles comerciales.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `users.example.json`, `rainmapper-app/DOCS.md`, `/share/rainmapper/users.json`, futuro `/share/rainmapper/permission_profiles.json` o equivalente.
  - Criterio de aceptacion: definir un modelo donde los permisos base vivan a nivel de perfil/tipo de usuario en un JSON separado, por ejemplo `free/basic/pro/admin` con capacidades declarativas, y donde cada usuario pueda tener overrides opcionales para activar/desactivar permisos concretos sin duplicar toda la matriz. Mantener compatibilidad de lectura con los flags actuales y documentar una migracion conservadora.
  - Estado: deuda arquitectonica documentada. Con la entrada de `can_use_estimated_field` ya hay tres flags independientes; antes de anadir mas permisos conviene definir perfiles/tipos de usuario y overrides por usuario.

- [x] Decidir visor principal
  - Contexto: conviven Bokeh, Leaflet y MapLibre; MapLibre ya funciona bien en movil segun validacion manual/reportada por el usuario y desde `0.2.47` tambien soporta Hybrid/Topographic raster.
  - Ficheros relacionados: `rainmapper_core/bokeh_maps.py`, `rainmapper_core/viewers/`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: definir si Bokeh queda como legacy, si Leaflet sigue activo y si MapLibre pasa a principal.
  - Estado: MapLibre queda como visor principal recomendado tras validar `0.2.53`; Leaflet se mantiene publicado como fallback. Bokeh sigue como referencia/compatibilidad.
  - Riesgo aceptado: complejidad y mantenimiento de varios visores hasta nueva revision.

- [x] Retirar `/local/rainmapper-mobile`
  - Contexto: la ruta legacy ya no se usa porque Cloudflare redirige a `rainmapper-leaflet` y `rainmapper-maplibre` segun reporte del usuario; pendiente de confirmar fuera del repositorio.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper-app/DOCS.md`, `README.md`, `rainmapper-app/README.md`.
  - Criterio de aceptacion: dejar de publicar `/local/rainmapper-mobile` y limpiar la carpeta antigua al publicar mapas.
  - Estado: resuelto en version `0.2.42`.

- [x] Homogeneizar idioma de logs y UI
  - Contexto: la webUI visible de HA, metadata HA, changelog y logs operativos principales del core quedan en ingles desde `0.2.46`.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper-app/app/web_server.py`, `rainmapper-app/README.md`, `rainmapper-app/DOCS.md`.
  - Criterio de aceptacion: idioma definido para superficies de usuario final y logs operativos.
  - Estado: resuelto para webUI/changelog/logs operativos. README/DOCS de la app HA quedan en espanol de momento por ser documentacion de uso propio, no distribucion publica.
  - Riesgo residual: si la app se distribuye publicamente, convendra traducir README/DOCS a ingles.

- [x] Validar portabilidad del enlace App settings
  - Contexto: funciona en la instalacion actual, pero dependia de slug/fallback y de una unica ruta.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: probado en otra instalacion HA o documentado como limitacion.
  - Estado: mejorado en `0.2.44`; la pagina App settings muestra el enlace recomendado calculado con Supervisor self-info y deja las rutas alternativas en una seccion avanzada. Queda validar en otra instalacion si aparece la ocasion.

- [x] Revisar documentacion/enlaces tras elegir MapLibre como visor principal
  - Contexto: MapLibre queda como visor principal recomendado; Leaflet se mantiene publicado como fallback y Bokeh como referencia/compatibilidad.
  - Ficheros relacionados: `README.md`, `rainmapper-app/README.md`, `rainmapper-app/DOCS.md`, `docs/codex-handoff.md`, `docs/todo.md`.
  - Criterio de aceptacion: la documentacion de uso presenta MapLibre primero y no induce a pensar que los tres visores tienen el mismo rol operativo.
  - Estado: resuelto.

- [x] Validar filtro de lluvia minima en MapLibre
  - Contexto: se ha anadido un panel `Settings` al visor MapLibre con slider `Min rain` para validar la UX antes de llevar el concepto a la futura app cross-platform.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: en HA/iPhone el slider filtra estaciones del periodo actual, conserva cambio de periodo/capa y no bloquea popups ni lectura del mapa.
  - Estado: validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada. El slider filtra sin romper cambio de periodo/capa ni popups segun esa validacion.

- [x] Validar vuelta a Satellite+ en MapLibre
  - Contexto: en `0.2.55`, despues de cambiar desde Satellite+ a otra capa, volver a Satellite+ no refrescaba la capa y quedaba la anterior.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/index.html`.
  - Criterio de aceptacion: en HA/iPhone, Satellite+ vuelve a cargar correctamente tras alternar con Hybrid, Topographic y Liberty.
  - Estado: corregido en `0.2.56` y validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada.

- [x] Validar parada limpia SIGTERM en Home Assistant
  - Contexto: Supervisor aviso que Rainmapper `0.2.54` no manejaba SIGTERM durante update y termino con codigo 143.
  - Ficheros relacionados: `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: al actualizar/reiniciar la app HA, Supervisor no muestra warning de SIGTERM y el proceso sale con codigo 0; si hay un job activo, la app intenta esperar a que termine antes de cerrar.
  - Estado: corregido en `0.2.55` y validado manualmente por el usuario; pendiente de confirmacion automatizada. Ya no aparece el warning de SIGTERM del Supervisor segun esa validacion.

## Prioridad baja
- [x] Estabilizar MapLibre 3D terrain
  - Contexto: MapLibre puede inclinar/rotar el mapa, pero el relieve real requiere una fuente DEM. Se ha anadido un toggle `3D terrain` y slider `Exaggeration` en Settings usando DEM externo Terrarium/Mapzen.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`.
  - Criterio de aceptacion: confirmar en local/HA/iPhone que activar 3D terrain funciona sobre Satellite+, Hybrid, Topographic y Liberty sin romper filtros, cambio de periodo, cambio de capa ni popups.
  - Estado: completado por decision del usuario el 2026-06-18; validado manualmente en local, HA, Mac e iPhone y queda como funcionalidad definitiva. En `0.2.77` se anade boton compacto `2D`/`3D` bajo `Generated`, atajo `t`, cola para el popup de altitud y cierre correcto sin bloquear hover. Riesgo aceptado: sigue dependiendo del DEM externo Terrarium/Mapzen hasta que se decida si hace falta DEM propio.

- [x] Revisar ergonomia del panel Settings de MapLibre en movil
  - Contexto: al anadir badges de estado por fuente, el panel Settings necesita mas ancho. El ajuste actual evita solapes y funciona en iPhone, pero puede sentirse algo ancho.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/style.css`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/index.html`.
  - Criterio de aceptacion: tras usarlo en movil, decidir si se mantiene el ancho actual, se compactan los badges o se cambia Settings a un panel tipo drawer/bottom sheet.
  - Estado: resuelto en `0.2.81` a nivel visual/operativo y validado manualmente en HA en versiones posteriores hasta `0.2.111`. El visor MapLibre pasa a una UI mas moderna con cabecera clara, controles flotantes, panel Settings claro y compacto en dos columnas, selector inferior de periodo, leyenda vertical dinamica, creditos en boton de informacion y popups claros.

- [x] Crear smoke tests automatizados
  - Contexto: no hay framework de tests completo, pero existe `scripts/smoke-test.sh`.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `README.md`, `docs/architecture.md`, `docs/codex-handoff.md`.
  - Criterio de aceptacion: comando unico que valide sintaxis Python, JS, conversion GeoJSON minima y wrappers shell.
  - Estado: resuelto con smoke test de sintaxis Python/JS/shell, conversion GeoJSON minima, version HA, sincronizacion raiz/app HA y whitespace Git.

- [x] Crear fixtures funcionales iniciales para GeoJSON
  - Contexto: Leaflet y MapLibre dependen de GeoJSON generado desde `Tomap`.
  - Ficheros relacionados: `tests/fixtures/`, `tests/test_tomap_to_geojson.py`, `rainmapper_core/geojson.py`, `scripts/smoke-test.sh`.
  - Criterio de aceptacion: tests versionados cubren estaciones ignoradas, coordenadas invalidas, columnas obligatorias y nombres de salida por periodo.
  - Estado: resuelto como primera cobertura formal con `unittest`, integrada en `./scripts/smoke-test.sh`.

- [x] Separar core en paquete Python reutilizable
  - Contexto: scripts grandes y duplicados.
  - Ficheros relacionados: `rainmapper_core/`, `rainmapper-app/Dockerfile`, `rainmapper-app/app/web_server.py`, `docs/core-refactor.md`.
  - Criterio de aceptacion: una unica fuente de verdad para core compartida por Docker local y HA.
  - Estado: resuelto en alcance conservador. `incremental_upsert` vive en `rainmapper_core/incremental_upsert.py`, `rainmapper_core.tomap` y `rainmapper_core.geojson` son entrypoints canonicos; los wrappers raiz/HA de Tomap y GeoJSON fueron retirados, la configuracion Python compartida vive en `rainmapper_core/config/`, Bokeh vive en `rainmapper_core/bokeh_maps.py`, los visores compartidos viven en `rainmapper_core/viewers/`, el runner principal vive en `rainmapper_core/rainmapper.py`, Bokeh vive en `rainmapper_core/bokeh_maps.py`, los wrappers Python raiz fueron retirados, y las librerias internas de fuente viven en `rainmapper_core/sources/`. El runtime Docker local vive en `rainmapper-local/`, con wrappers/rutas compatibles en raiz. HA se construye desde la raiz del repo y `rainmapper-app/app` queda solo para `web_server.py`. Validado con unit tests, smoke test, Docker offline functional test, `./local_update.sh` real con exit code 0, HA 0.2.79 antes de retirar las ultimas copias y HA 0.2.80 con `Run all` manual correcto tras cerrar la refactorizacion core/app/local.
  - Riesgo si no se hace: mantenimiento manual permanente.

- [x] Extraer generacion de CSV `Tomap` de `Rainmapper.py`
  - Contexto: hasta ahora `Generate maps`/`MODE=maps` solo consumia los `Tomap` existentes para generar Bokeh y GeoJSON. Si cambiaba una columna derivada de `Tomap`, como el numero de ultimos registros de lluvia por estacion, hacia falta `Run all`/`MODE=all` para reconstruirlos.
  - Nota: desde `0.2.67`, el numero de registros recientes se configura con `last_rains_history`; con `rainmapper_core.tomap`, `Generate maps` deberia poder reconstruir ese historico sin `Run all`, pendiente de validacion local/HA.
  - Ficheros relacionados: `rainmapper_core/tomap.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper_core/bokeh_maps.py`, `rainmapper_core/geojson.py`.
  - Estado: resuelto. `python -m rainmapper_core.tomap` reconstruye `Tomap` y `LastXX_rains.csv`; `MODE=maps`, `MODE=all` y `Generate maps` lo invocan antes de Bokeh/GeoJSON. En `Rainmapper.py` se han retirado el bloque ejecutable inline de generacion `Tomap` y los helpers legacy `create_grouped` y `create_last_rains`.
  - Validacion: tras ejecutar `local_update.sh`, `scripts/compare-tomap-builder.sh` confirma que `rainmapper_core.tomap` reconstruye los mismos CSV `Tomap` que el flujo antiguo de `Rainmapper.py` para los datos locales actuales. `local_maps.sh` reconstruye `Tomap`, genera GeoJSON y arranca el servidor local correctamente. `Generate maps` en HA `0.2.74` fue validado manualmente por el usuario. Tras retirar el bloque inline, `local_all.sh` completo termina con `rainmapper_core.rainmapper` exit code 0, reconstruye Tomap con `rainmapper_core.tomap` y genera GeoJSON. Tras limpiar helpers legacy, `MAX_THREADS=3 ./local_update.sh` termina con exit code 0 y las descargas actuales quedan contenidas en sus incrementales.
  - Riesgo residual: si cambia el schema de historicos incrementales, hay que actualizar `rainmapper_core.tomap` y sus tests.

- [ ] Mejorar observabilidad de Wunderground
  - Contexto: Wunderground es el cuello de botella, pero todavia no hay suficientes observaciones de tiempos y el rendimiento actual es aceptable.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos segun reporte del usuario; pendiente de confirmar automaticamente.
  - Observacion local 2026-06-19: despues de permitir que `docker-compose.yml` propague `MAX_THREADS`, `local_update.sh` paso de `385.69s` con `MAX_THREADS=1` a `196.82s` con `MAX_THREADS=2` y `81.20s` con `MAX_THREADS=3`; Wunderground paso de `0:06:02` a `0:03:03` y despues a `0:01:19`.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `Data/metricas_wunderground.csv`.
  - Criterio de aceptacion: metricas revisables y comparables por ejecucion; validar en HA/RPi si `max_threads=2` o `3` reduce tiempos sin generar timeouts, carga excesiva ni fallos de fuentes; posible export futuro a InfluxDB/Grafana.
  - Estado: parcialmente mejorado. `source_status.json` guarda duraciones reales por fuente y la webUI las muestra; Meteocat guarda subtiempos de metadata, condiciones, precipitacion, merge y guardado. Tras observacion nocturna de schedules en HA sin problemas reportados por el usuario, `max_threads=3` queda como valor operativo recomendado; queda pendiente decidir si exportar metricas historicas a InfluxDB/Grafana.
  - Riesgo si no se hace: optimizacion a ciegas del scraper si el rendimiento empeora en el futuro.

- [ ] Definir estrategia legal/comercial para Wunderground antes de una app publica
  - Contexto: el scraping HTML actual funciona para uso propio, pero las condiciones de TWC/Wunderground consultadas el 2026-06-18 no lo hacen apto como base de una app comercial sin permiso escrito. La API/PWS Data Feed oficial tambien limita el uso a personal/no comercial salvo acuerdo separado, y el pricing publico de Weather Data APIs parte de un plan Standard de 500 USD/mes orientado a clientes empresariales.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/sources/wunderground/`, futura API/app movil, documentacion de producto.
  - Criterio de aceptacion: antes de comercializar mapas o app, decidir entre retirar Wunderground, reemplazarlo por fuentes con licencia compatible, limitarlo a uso privado o negociar derechos con The Weather Company.
  - Riesgo si no se hace: dependencia de una fuente con coste/licencia incompatible con una app comercial.

- [ ] Revisar timeout del scraper Wunderground
  - Contexto: algunas estaciones pueden tardar o fallar, pero el tiempo global actual es aceptable y conviene acumular mas observaciones antes de cambiarlo.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos segun reporte del usuario; pendiente de confirmar automaticamente.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/sources/wunderground/`.
  - Criterio de aceptacion: timeout configurable y errores registrados sin bloquear toda la ejecucion.
  - Riesgo si no se hace: estaciones lentas podrian penalizar todo el run si el rendimiento empeora.

- [x] Hacer Meteocat/Socrata mas tolerante a timeouts transitorios
  - Contexto: en HA `0.2.67`, un `Run all` fallo despues de Wunderground porque una consulta Meteocat XEMA a `analisi.transparenciacatalunya.cat` supero el timeout por defecto de 10s del cliente Socrata.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/config/const.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper-app/config.yaml`.
  - Criterio de aceptacion: las llamadas Meteocat/Socrata usan timeout configurable y reintentos antes de fallar el run.
  - Estado: corregido en `0.2.68` con `meteocat_request_timeout` y `meteocat_max_attempts`; pendiente de validacion manual en HA.

- [x] Validar ejecucion degradada por fuente y exit code global
  - Contexto: `rainmapper_core.rainmapper` ejecuta Meteoclimatic, Meteocat, Wunderground y AEMET opcional en futuros paralelos. Wunderground controla errores por estacion y muestra resumen; Meteoclimatic tolera fallos de patrones individuales si algun patron devuelve datos, pero aborta si no recupera ninguno; Meteocat reintenta desde `0.2.68`; AEMET debe degradar si hay error temporal/429.
  - Objetivo: si una fuente falla completamente, el proceso general deberia poder continuar con las fuentes que si funcionen, reutilizar o marcar claramente datos antiguos cuando proceda, y dejar trazabilidad visible.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper-app/app/web_server.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper_core/geojson.py`, `rainmapper_core/viewers/maplibre-viewer/`, documentacion HA.
  - Estado parcial: desde `0.2.71`, la webUI muestra estado/exit code separado para Meteoclimatic, Meteocat y Wunderground; desde la integracion AEMET tambien muestra AEMET. `rainmapper_core.rainmapper` escribe `Data/source_status.json`; si una fuente falla completamente intenta reutilizar su incremental previo y marca la fuente como `STALE`; si no hay incremental utilizable la marca como `NOK`. El fichero se copia como `data/source_status.json` en Leaflet/MapLibre publicados, y MapLibre muestra badges junto al filtro `Source`. Desde `0.2.73`, el exit code global distingue `0` exito completo, `2` exito degradado con al menos una fuente usable y `1` fallo total/no recuperable; `Run all` debe continuar a `maps` cuando `update` devuelve `2`.
  - Validacion: `0.2.73` fue validada manualmente en HA con `Run all` completo, `Exit code 0` y mapas generados correctamente.
  - Validacion adicional: el caso degradado `Exit code 2` se da por validado de facto en local por decision del usuario, tras el fallo accidental de lectura/escritura provocado por iCloud que permitio comprobar continuidad del proceso y trazabilidad por fuente.
  - Estado: resuelto operativamente; una validacion HA con fallo simulado queda como comprobacion opcional, no como bloqueo.

- [x] Retirar Jawg Maps de Leaflet/MapLibre y de la configuracion
  - Contexto: Jawg Street/Terrain eran capas opcionales activadas con `jawgmaps_api_key`, pero MapLibre ya cubre las necesidades actuales con Satellite+, Hybrid, Topographic, Liberty y 3D terrain. Jawg anade gestion de API key, posible restriccion por dominio, dudas de uso no comercial y complejidad de documentacion/soporte.
  - Ficheros relacionados: `rainmapper_core/viewers/leaflet-viewer/`, `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper-app/config.yaml`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, README/DOCS y docs de contexto.
  - Criterio de aceptacion: no aparece `jawgmaps_api_key` en opciones HA ni docs principales; `JAWGMAPS_API_KEY` deja de usarse en visores; Leaflet/MapLibre no muestran capas Jawg; quedan actualizadas las decisiones/documentacion indicando que se descarta Jawg por bajo valor frente a complejidad/licencia/API key.
  - Estado: resuelto en `0.2.69`.
  - Riesgo si no se hace: mantener una dependencia externa y una clave cliente visible que ya no aporta valor suficiente al flujo actual.

- [ ] Evaluar InfluxDB/Grafana para metricas
  - Contexto: el usuario ya tiene interes en analitica de tiempos de estaciones.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, futuro exporter.
  - Criterio de aceptacion: decision tecnica documentada.
  - Riesgo si no se hace: se acumulan CSV sin explotacion.

- [x] Validar imagen Docker HA preconstruida
  - Contexto: antes de usar GHCR, Home Assistant construia la app en la RPi durante installs/updates, y la barra de progreso de HA podia quedarse en 0% hasta terminar. El Mac construye mucho mas rapido que la RPi segun validacion manual/reportada por el usuario.
  - Ficheros relacionados: `.github/workflows/build-rainmapper-app.yml`, `rainmapper-app/Dockerfile`, `rainmapper-app/config.yaml`, GitHub Container Registry.
  - Criterio de aceptacion: publicar imagen multi-arch `amd64`/`arm64` en GHCR antes de hacer visible el update en HA; HA descarga `ghcr.io/cginebrosa/rainmapperha:<version>` sin build local.
  - Estado: el repo soporta imagen GHCR y Buildx local con limpieza de etiquetas antiguas. Validaciones en `0.2.57`, `0.2.60`, `0.2.61`/`0.2.62`/`0.2.63`/`0.2.65` fueron manuales/reportadas por el usuario; pendientes de confirmar automaticamente. El flujo normal pasa a Buildx local con `scripts/build-push-ha-image.sh`, dejando Actions como fallback manual. Procedimiento de validacion: ejecutar `./scripts/smoke-test.sh` una sola vez antes del build/push; no repetirlo tras publicar si solo se actualiza documentacion con el digest. Repetirlo solo si despues del primer smoke se toca codigo runtime, configuracion HA, assets de visor, scripts o ficheros incluidos en la imagen. Regla operativa de release HA: despues de publicar y verificar GHCR, hacer commit/push del bump y avisar al usuario en cuanto HA pueda detectar la version; completar la documentacion de continuidad despues, mientras el usuario descarga/instala/prueba.
  - Riesgo residual: requiere login Docker en GHCR desde el Mac y disciplina de publicar imagen antes del commit de version.

- [x] Validar filtros de visor para futura app movil
  - Contexto: antes de construir la app iOS/Android se quieren probar funciones utiles en el visor web actual.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper_core/geojson.py`, `tests/test_tomap_to_geojson.py`.
  - Criterio de aceptacion: MapLibre permite filtrar por lluvia minima y por fuente de estacion; el GeoJSON incluye `Source` para no repetir inferencias en clientes futuros.
  - Estado: filtro de lluvia minima en `0.2.54`; filtro Meteocat/Meteoclimatic/Wunderground y `Source` en GeoJSON en `0.2.58`; ajuste defensivo `Unknown` y Meteocat longitud 2 en `0.2.59`. Cubierto parcialmente por `tests/test_tomap_to_geojson.py` para inferencia `Source`; validacion visual del visor pendiente de automatizar.

- [x] Disenar futura app iOS/Android
  - Contexto: objetivo a largo plazo incluye app movil con autenticacion y permisos.
  - Ficheros relacionados: `docs/mobile-app-architecture.md`.
  - Criterio de aceptacion: arquitectura propuesta para API, auth, permisos y serving de mapas.
  - Ideas funcionales iniciales:
    - Lista de estaciones favoritas para mostrar en el mapa solo esas estaciones.
    - Filtro por cantidad minima de lluvia en el periodo seleccionado para mostrar solo estaciones que superen ese umbral.
  - Estado: resuelto a nivel de diseno inicial; no implementado.
  - Riesgo si no se hace: el visor publico actual no controla quien accede a que.

- [x] Documentar direccion Cloudflare + app cross-platform
  - Contexto: se quiere explorar futura app iOS/Android sin depender de Home Assistant como backend publico.
  - Ficheros relacionados: `docs/mobile-app-architecture.md`, `docs/decisions.md`, `docs/codex-handoff.md`.
  - Criterio de aceptacion: documentar Cloudflare R2, Worker API, React Native/MapLibre, pruebas sin stores y primer MVP recomendado.
  - Estado: resuelto a nivel de arquitectura; pendiente de implementacion.

## Bugs abiertos
- [x] Docker local dejaba GeoJSON obsoletos en `MODE=maps/all`
  - Sintoma: tras ejecutar Docker local en `MODE=all`, `docker-data/Tomap` se actualizaba pero `docker-data/PublicData/*.geojson` mantenia fechas antiguas, por lo que MapLibre local no mostraba lecturas recientes.
  - Causa historica: `run.sh` local solo ejecutaba el generador Bokeh; la generacion GeoJSON estaba en `web_server.py` de HA pero no en el wrapper local. Actualmente el generador Bokeh se ejecuta como `python -m rainmapper_core.bokeh_maps`.
  - Ficheros relacionados: `run.sh`, `rainmapper-app/run.sh`, `Dockerfile`.
  - Estado: corregido; `maps/all` ejecuta tambien `rainmapper_core.geojson`.

- [ ] Tests funcionales formales incompletos
  - Sintoma: ya existen fixtures `unittest` offline para `rainmapper_core.geojson`, `rainmapper_core.tomap`, un pipeline integrado `upsert -> Tomap -> GeoJSON`; tambien existe `scripts/docker-offline-functional-test.sh` para validar el pipeline dentro de Docker con datos temporales. No hay cobertura funcional formal para HA real, publicacion webUI o generacion completa Bokeh/visores servida desde HA.
  - Causa probable: proyecto evolucionado por validacion manual.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `scripts/docker-offline-functional-test.sh`, `tests/`, futuro set de fixtures HA/webUI.
  - Como reproducir: ejecutar `./scripts/smoke-test.sh` para checks rapidos y `./scripts/docker-offline-functional-test.sh` para validacion Docker offline; ninguna de las dos prueba HA real.
  - Criterio de solucion: ampliar pruebas funcionales para publicacion, webUI y/o ejecuciones controladas de HA sin depender de red.

- [x] Cache-buster obsoleto en assets del visor MapLibre
  - Sintoma: la pulsacion larga de altitud funcionaba en local pero no en mapas servidos desde HA.
  - Causa: se detecto un problema real de cache-buster (`rainmapper_core/viewers/maplibre-viewer/index.html` seguia referenciando `app.js?v=0.2.62` aunque la app HA estaba en `0.2.63`), pero Chrome limpio tambien fallo tras generar mapas, asi que la causa funcional final era el disparador `pointerdown` directo sobre canvas en HA.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/leaflet-viewer/index.html`, `scripts/smoke-test.sh`.
  - Estado: corregido en `0.2.65`; el smoke test valida que los cache-busters internos de los visores coinciden con la version HA y MapLibre usa eventos propios del mapa mas `contextmenu` para la pulsacion larga. Validado manualmente por el usuario en HA tanto en iPhone como en Safari para Mac; pendiente de confirmacion automatizada.

## Validaciones pendientes
Nota: las validaciones marcadas como resueltas en esta seccion son, salvo que se indique un script concreto, validaciones manuales/reportadas por el usuario y no pruebas automatizadas reproducibles solo desde el repositorio.

- [x] `docker compose build rainmapper` tras cambios de Docker local.
- [x] `docker compose run --rm -e MODE=help rainmapper`.
- [x] `docker compose run --rm -e MODE=all rainmapper` en datos de prueba antes de tocar historicos reales.
- [x] Actualizacion HA desde GitHub tras bump de version.
- [x] `Run all` desde webUI HA.
- [x] `Run all` HA `0.2.73` con semantica nueva: caso normal validado con `Exit code 0` y mapas generados correctamente.
- [x] Schedule con varias horas y dias.
- [x] Leaflet en iPhone: cambio periodo conserva posicion, popups y leyenda.
- [x] MapLibre en movil: estilos, marcadores tras cambio de capa, popup, bounds.
- [x] `ignore_stations_tomap.txt`: estacion ignorada desaparece de Leaflet/MapLibre pero sigue en historico.
- [x] Reconstruccion desde cero con poco historico.
- [x] `./local_all.sh`: build local, `MODE=all`, servidor HTTP local y MapLibre con datos actuales; validado manualmente por el usuario el 2026-06-18 a las 00:37 con 432 estaciones en el periodo de 1 dia, pendiente de confirmacion automatizada.

## Preguntas pendientes para el usuario
- [x] Confirmar si MapLibre debe sustituir a Leaflet como visor principal o si ambos se mantienen.
- [x] Confirmar cuando retirar la ruta legacy `/local/rainmapper-mobile`.
- [x] Confirmar si el repo debe quedar privado o publico para distribucion futura.
  - Estado: confirmado el 2026-06-22; repo privado. Para la instalacion HA actual se mantiene GHCR accesible.
- [x] Confirmar si Jawg permite restringir token por dominio y si se usara en publico.
  - Estado: se decide retirar Jawg de momento; no hace falta investigar restricciones de token mientras no se use.
- [x] Confirmar idioma final de UI visible HA/changelog: ingles.
- [x] Confirmar si los logs internos del core deben quedar tambien en ingles.

## Ideas futuras
- App iOS/Android con login y autorizacion por mapa/zona.
- Prototipo cross-platform con React Native + MapLibre consumiendo Cloudflare Worker API.
- Publicacion de GeoJSON a Cloudflare R2 con manifiesto `latest.json`.
- Favoritos de estaciones y filtro por lluvia minima en la futura app movil.
- Revisar modelo de limites por plan para `Last rains history`, separando registros publicados en GeoJSON de registros visibles por usuario o suscripcion.
- API propia externa entre backend publico y app movil. No confundir con la API ligera interna del add-on HA (`/auth/*`, `/protected/maplibre/*`, WebUI), que ya existe y sirve el visor protegido actual.
- Capa de permisos por usuario.
- Cache/CDN de GeoJSON publicados.
- Panel de calidad de estaciones basado en metricas Wunderground.
- Auto-deteccion de outliers de lluvia antes de publicar mapas.
- Migracion de historicos CSV a formato mas eficiente si crecen mucho, por ejemplo Parquet, pendiente de evaluar.
