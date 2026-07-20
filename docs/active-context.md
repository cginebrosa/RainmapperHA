# Active Context

Ventana operativa para continuar RainmapperHA sin depender de conversaciones
anteriores. Este documento describe el estado actual, no el historial completo.

## Repositorio y release estable

- Workspace unico:
  `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Commit de release presente en `inicial` y `origin/inicial`: `6521245`
  (`Release Home Assistant 0.2.210`).
- Release HA instalada y usada para aislar el problema: `0.2.209`; release
  publicada pendiente de instalar: `0.2.210`.
- Imagen: `ghcr.io/cginebrosa/rainmapperha:0.2.210` y `latest`, digest
  `sha256:a64644929735eef53ce254a99f303161c050f876459819a4455ce6bcd299bd23`.
- Manifests verificados: `linux/amd64`
  `sha256:af74419a980cb581bbd80328c06a05d9d01751d9292ce803cd82d00a083c3009`
  y `linux/arm64`
  `sha256:8c0aeb44d84bef4356dbe655493dbbeedbeebf0b897ef5b982205fb4cd6c55f4`.
- El repositorio GitHub sigue publico por decision explicita del usuario.
- El usuario autorizo expresamente el 2026-07-20 el bump, publicacion y
  commit/push de `0.2.210` para cerrar cuanto antes la fase de workers.

El codigo de release esta versionado. Antes de continuar, ejecutar
`git status --short`; no limpiar, revertir ni sobrescribir cualquier cambio
local nuevo que aparezca.

## Correccion clave: no existe una imagen HA de desarrollo

No hay, ni se quiere crear, una imagen de desarrollo/sideload de Home Assistant.
Introducirla complicaria innecesariamente el despliegue y la continuidad.

No se creo ni se debe crear una imagen HA de desarrollo. `0.2.208` introdujo el
coordinador normal, `0.2.209` corrigio su refresco bajo Ingress y `0.2.210`
controla la interaccion de Workers y la preparacion costosa de entradas sin
cambiar los flags seguros ni el fallback HA.

La `0.2.208` arranco con ambos interruptores apagados. Despues se publico
`8100` solo en la LAN, se activo `Enable external worker connections`, se
emparejo M1 y la prueba inocua de asignacion termino correctamente en 13 s.
En `0.2.209` se comprobo que Rainmapper, el worker y la pagina en reposo son
estables, al igual que una asignacion. Una sola prueba de envio de entradas
consume aproximadamente un nucleo mientras calcula los hashes de 5,87 GiB,
termina correctamente y devuelve la CPU a la normalidad. Los clics repetidos
antes de ver respuesta iniciaban varias preparaciones sincronas concurrentes,
agotaban la CPU de HA y provocaban timeouts de watchdog y salidas 137 de otros
add-ons. `0.2.210` prepara el bundle en segundo plano, impide duplicados con un
lock no bloqueante, desactiva inmediatamente el boton y reutiliza una cache
privada de hashes GIS validada por metadatos del fichero.

`Allow external rebuilds and promotion` permanece apagado. Siguiente orden:

1. Instalar `0.2.210`; con worker encendido y la pagina abierta, confirmar que
   el reposo sigue estable.
2. Ejecutar una sola prueba de asignacion.
3. Ejecutar una sola prueba de envio de entradas: la UI debe responder de
   inmediato indicando preparacion; la primera pasada puede usar un nucleo y
   debe volver a la normalidad al terminar. Repetirla solo despues para
   confirmar que reutiliza la cache de hashes.
4. Probar corte/reconexion sin revocar la credencial.
5. Activar reconstrucciones externas y validar primero un candidato privado de
   una especie, sin promocion automatica.
6. Probar despues alcances, cancelacion, freshness, cache y promocion manual.
7. Medir las fases en HA y M1 sobre el mismo snapshot/dataset.

La conexion actual usa HTTP en la LAN privada. No publicar `8100` en el router;
Tailscale/TLS/ACL queda como endurecimiento posterior.

## Estado del worker externo local

El prototipo funciona enteramente en el laboratorio Docker local y no depende
de HA real:

- UI Rainmapper local: `http://127.0.0.1:8101`.
- Coordinador local, solo en la red Docker: `http://rainmapper-ha-ui:8100`.
- Health local del worker: `http://127.0.0.1:8110/health`.
- Inicio/parada: `./mushroom_worker_start.sh` y
  `./mushroom_worker_stop.sh`.
- Imagen generica privada: `rainmapper-worker`; servicio/contenedor
  `rainmapper-worker`; volumen persistente `rainmapper-worker-data`.
- El launcher admite `--help`, nombre, URL del coordinador, pairing y modo no
  interactivo; recupera la configuracion no secreta y la identidad desde el
  volumen. El token permanente se guarda separado bajo `secrets/`.
- El worker es headless: la interfaz humana y la autoridad permanecen en
  Rainmapper.
- La comunicacion es outbound desde el worker. Rainmapper conserva la fuente de
  verdad de datos vivos, jobs y artefactos aceptados.
- Pairing temporal de un solo uso, Bearer permanente por worker, registro
  multi-worker, heartbeat, deteccion desconectado, revocacion y ejecutor
  predeterminado estan implementados localmente.
- La cola persistente implementa lease/claim, inicio, progreso, finalizacion,
  cancelacion cooperativa y forzada, y reasignacion solo antes del inicio.
- Un `work_key` impide ejecuciones activas solapadas. Especies disjuntas pueden
  ejecutarse en paralelo; los alcances completos o con especies comunes se
  bloquean.
- La pagina `Workers y trabajos` centraliza los lanzamientos y conserva HA como
  fallback. No existe fallback silencioso si el ejecutor predeterminado esta
  desconectado o no es compatible.
- Alcances externos locales operativos: todas las especies elegibles,
  pendientes y una especie.
- El aviso `Modelo V0 desactualizado` y las antiguas acciones de Observaciones
  navegan a `Workers y trabajos` con el alcance preseleccionado; ya no lanzan un
  rebuild directamente.

### Pipeline, datasets y promocion

- HA y worker usan el pipeline unico
  `rainmapper_core/mushroom_rebuild_pipeline.py`; la ruta HA estable continua
  en `legacy` salvo flag opt-in.
- Contratos versionados locales: `InputManifest 0.1`, `JobSpec 0.1` y
  `ResultManifest 0.1`.
- El snapshot vivo se congela en Rainmapper. El worker descarga solo paths
  declarados, valida tamaños/SHA-256 y nunca monta directamente `docker-data`.
- La imagen no contiene GIS/DEM. El dataset semiestatico se sincroniza desde
  Rainmapper a staging solo si falta o cambia el fingerprint, se valida y se
  activa atomicamente en el volumen persistente.
- Cache actual probada: `mushroom_gis_v0`, 10 ficheros,
  6.306.367.027 bytes. Primera carga a volumen vacio y reutilizacion posterior
  con cero bytes transferidos verificadas.
- El worker genera nueve artefactos candidatos privados, sube manifest y bytes,
  y Rainmapper vuelve a validar contrato, hashes, tamaños y contadores.
- La promocion siempre es explicita. Una promocion completa o parcial instala
  atomica y conjuntamente los nueve artefactos; la parcial mezcla solo las
  observaciones/especies declaradas con el ultimo modelo vivo.
- Antes de instalar los artefactos, HA elimina referencias auxiliares del
  worker y rebasa las rutas de metadatos a las rutas autoritativas del
  coordinador. Los datos privados existentes no se reescribieron durante la
  auditoria.
- Las promociones se serializan para que trabajos disjuntos no pierdan cambios.
- Se conservan como maximo dos copias recuperables de los nueve artefactos
  derivados anteriores (aproximadamente 2 MB por copia, sin GIS/DEM). La poda
  ocurre solo tras una promocion correcta.
- Los equivalentes de `external_worker_connections_enabled=true` y
  `external_worker_rebuilds_enabled=true` estan solo en el Compose local. La
  `0.2.208` ya incorpora la ruta en HA. En la instalacion real solo esta activa
  la primera opcion para las pruebas inocuas; la opcion operacional sigue
  desactivada.

## Validacion local de cierre

Resultados comprobados el 2026-07-20 tras consolidar el diff y sus correcciones
posteriores:

- `.venv/bin/python -m unittest discover -s tests`: **374 tests OK**.
- `.venv/bin/python scripts/validate-mushroom-data.py`: **0 errores y 11
  warnings conocidos**.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: **OK**, incluidos los
  374 tests, sintaxis Python/JavaScript/shell, versiones y fixtures.
- Las imagenes locales HA/worker se inspeccionaron sin montar volumenes: no
  contienen `docker-data`, GIS/DEM, credenciales ni configuracion persistente
  del worker. HA contiene solo los assets `mushroom-data` ya versionados.
- Reconstruccion externa completa local, transferencia GIS a volumen vacio,
  reutilizacion de cache, corte/reconexion, cancelacion, corrupcion/freshness,
  retorno de 9/9 artefactos y promocion manual atomica: verificadas.
- Alcance `una especie` para `cantharellus_lutescens`: completado y
  promocionado.
- Alcance `pendientes` para la misma unica observacion: completado y
  promocionado.
- Los hashes de las otras 13 especies permanecieron exactamente iguales.
- Segundo job `pendientes`: cancelado cooperativamente en Meteorologia al 55 %,
  sin promocion.
- La retencion elimino la tercera copia y mantuvo las dos mas recientes.
- La web y el protocolo quedaron separados: `8099` rechaza las rutas del
  worker, `8100` solo acepta el protocolo cerrado y exige Bearer. Una sonda
  manual desde el contenedor worker existente alcanzo `8100` dentro de la red
  Docker; ese puerto no se publico en el Mac.
- El proceso worker que llevaba horas activo no se reinicio para no reclamar ni
  alterar jobs conservados. Sigue usando en memoria la URL antigua `:8099` y
  registra 404; el proximo arranque mediante `mushroom_worker_start.sh` migrara
  la URL local persistida a `:8100` antes de conectarse.
- No quedan rebuilds candidatos activos. La cola local conserva tres probes de
  transporte antiguos en `claimed`; no son reconstrucciones ni modifican el
  modelo. No borrarlos sin revisar/autorizar.

Los contenedores locales se reconstruyeron con el codigo actual y quedaron
encendidos al cerrar, pero la proxima sesion debe comprobar su estado real en
vez de asumirlo.

### Objetivo `prediction_favorable`

La derivacion se verifico explicitamente en los datos locales actuales:

- features: 126 filas = 66 favorables + 60 desfavorables;
- 0 discrepancias respecto a `prediction_favorable` del catalogo;
- 0 valores sin politica conocida;
- modelo entrenable: 125 filas = 65 favorables + 60 desfavorables.

La diferencia es `obs_20241109_0005` (`cantharellus_lutescens`): es favorable
pero sigue en borrador y se excluye del entrenamiento. Sigue pendiente, si se
considera necesario, comprobar visual/operativamente estos recuentos en HA; no
confundirlo con la validacion local ya cerrada.

## Prioridades siguientes

### P0 — Consolidar el prototipo antes de publicar nada

Estado: consolidacion completada, publicada en `0.2.208`, instalada y probada
contra M1 real; el refresco se publico en `0.2.209` y el control de interaccion
y preparacion pesada en `0.2.210`.

1. La API permanece apagada por defecto, la autenticacion es fail-closed y el
   modo operacional exige simultaneamente API y autenticacion. HA expone dos
   opciones separadas: `Enable external worker connections` y
   `Allow external rebuilds and promotion`, ambas desactivadas por defecto.
2. Se confinan los paths de snapshots/GIS, se verifica la huella del manifest,
   se acota el JSON del protocolo y se evita conservar paths privados del
   worker tras una promocion.
3. El empaquetado fuente excluye `docker-data` y `mushroom-GIS`; la imagen HA
   incluye el coordinador pero no lo habilita. La comprobacion final de la
   imagen construida corresponde a P1, antes de publicar.
4. Preparar un checkpoint/commit solo cuando el usuario lo pida. No mezclar un
   release apresurado con el cierre documental.

### P1 — Preparar una version HA normal para la prueba real

1. Topologia interna definida: web/Ingress permanece en `8099`; el protocolo
   del worker usa un listener dedicado `8100`, no publicado por defecto en HA,
   con rutas cerradas y autenticacion obligatoria. Los controles humanos del
   worker en `8099` solo aceptan Ingress autenticado de HA.
2. Elegir y validar como primera exposicion privada el puerto host de `8100`
   mediante LAN/Tailscale y su ACL/TLS. Comparar Tailscale del host frente a
   sidecar Docker. El sidecar favorece
   portabilidad, pero no elude politicas del Mac ni debe ser requisito para la
   primera prueba si LAN/Tailscale del host basta.
3. Imagen HA local construida con el Dockerfile normal e inspeccionada sin
   volumenes: incluye coordinador/UI/core, no contiene datos privados ni
   GIS/DEM y la reconstruccion local HA sigue disponible en `legacy` por
   defecto.
4. Bump, GHCR y commit/push de `0.2.210` completados con autorizacion expresa.
   `0.2.210` y `latest` comparten el digest multi-arch verificado
   `sha256:a64644929735eef53ce254a99f303161c050f876459819a4455ce6bcd299bd23`;
   import check arm64: `image_import_ok 0.2.210 False False True`.

### P2 — Prueba M1 ↔ HA real

- M1 ya esta emparejado por LAN con HA real y la prueba de asignacion termino
  correctamente en 13 s.
- Instalar `0.2.210` y comprobar primero el reposo, una asignacion y una sola
  preparacion de entradas; repetir esta ultima solo tras completarse para
  verificar la cache.
- Probar todas, pendientes y una especie.
- Probar cancelacion cooperativa/forzada, worker apagado, corte/reconexion,
  duplicados/solapes, stale result, cache presente/ausente y promocion manual.
- Verificar que HA reconstruye localmente aunque no haya worker.
- Medir tiempos por fase HA/M1 con el mismo snapshot y dataset.

### P3 — Portabilidad y ML posteriores

- Repetir `docker load` y bootstrap en otro daemon/host sin reutilizar capas ni
  volumen; probar tambien una actualizacion real del dataset semiestatico.
- Solo despues incorporar jobs separados `build_ml_dataset`, `train_ml_model`
  y `evaluate_ml_model`, sin promocion automatica.
- M5 y AWS quedan diferidos.

## Riesgos y dudas abiertas

- El prototipo grande ya esta versionado en `e2f117d`; los datos persistentes y
  GIS/DEM siguen fuera de Git y no deben limpiarse.
- La equivalencia local no sustituye una prueba en HA/Raspberry ni una prueba
  de red real.
- Falta elegir y validar en HA real la publicacion privada de `8100`, su
  ACL/TLS y la topologia Tailscale inicial; el protocolo ya no comparte el
  listener web `8099`.
- No se ha demostrado aun portabilidad en un daemon/host realmente limpio.
- La auditoria local no encontro secretos ni datos GIS/vivos incorporados al
  contexto de imagen. Antes de publicar sigue siendo obligatorio inspeccionar
  la imagen HA construida y su configuracion efectiva.
- `docker save/load` mueve la imagen, no el volumen persistente; un host nuevo
  debe reconstruir cache/configuracion mediante bootstrap y sincronizacion.
- Los datasets GIS/DEM requieren revisar licencias/atribucion antes de cualquier
  redistribucion fuera del entorno privado.
- El modelo V0 sigue siendo descriptivo/auditable, no un modelo ML predictivo.

## Archivos relevantes

Diseno y continuidad:

- `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
- `docs/mushrooms/mushroom-ml-training-plan-es.md`
- `docs/decisions.md`
- `docs/todo.md`

UI/coordinador:

- `rainmapper-app/app/web_server.py`
- `rainmapper-app/app/mushroom_workers_ui.py`
- `rainmapper-app/app/mushroom_profiles_ui.py`
- `rainmapper-app/app/mushroom_known_sites_ui.py`

Worker y despliegue local:

- `rainmapper-worker/`
- `mushroom_worker_start.sh`
- `mushroom_worker_stop.sh`
- `mushroom_lab_start.sh`
- `rainmapper-local/docker-compose.yml`
- `rainmapper-local/docker-compose.worker-local.yml`

Core compartido:

- `rainmapper_core/mushroom_rebuild_pipeline.py`
- `rainmapper_core/mushroom_rebuild_contracts.py`
- `rainmapper_core/mushroom_rebuild_snapshot.py`
- `rainmapper_core/mushroom_rebuild_comparison.py`
- `rainmapper_core/mushroom_worker_*.py`

Pruebas:

- `tests/test_mushroom_rebuild_*.py`
- `tests/test_mushroom_worker_*.py`
- `tests/test_web_server_auth.py`

## Reglas innegociables de continuidad

- Trabajar exclusivamente en el workspace indicado.
- Usar siempre `.venv/bin/python` (Python 3.11), nunca el Python del sistema.
- No revertir ni sobrescribir cambios locales existentes.
- No borrar, sustituir ni versionar datos privados de
  `docker-data/mushroom-data` ni GIS/DEM.
- No hacer bump, release, limpieza GHCR ni cambios destructivos sin peticion
  expresa.
- No crear una imagen HA de desarrollo como atajo.
- Mantener siempre la reconstruccion local de HA como fallback.
- Todo texto visible nuevo de setas debe existir en
  `mushroom-data/mushroom_labels.json` para `en`, `es` y `ca`.
