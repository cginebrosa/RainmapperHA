# Active Context

Ventana operativa para continuar RainmapperHA sin depender de conversaciones
anteriores. Este documento describe el estado actual, no el historial completo.

## Repositorio y release estable

- Workspace unico:
  `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- `HEAD` y `origin/inicial`: `7480012` (`Close Rainmapper session after HA
  0.2.207 validation`).
- Release HA instalado/publicado: `0.2.207`.
- Commit del release: `bbf43aa Release Home Assistant 0.2.207`.
- Imagen: `ghcr.io/cginebrosa/rainmapperha:0.2.207` y `latest`, digest
  `sha256:a2047d39c8534c9d8e1a0066a5ff903e49733a0a98015fdb731081bf26af6781`.
- GHCR conserva 10 entradas: release actual `0.2.207/latest`, rollback
  `0.2.206` y sus auxiliares multi-arch/attestation.
- El repositorio GitHub sigue publico por decision explicita del usuario.
- No se ha hecho commit, bump, release ni publicacion durante el desarrollo
  local del worker. No hacerlo sin peticion expresa.

El worktree esta deliberadamente sucio con todo el prototipo local del worker
externo. No limpiar, revertir ni sobrescribir esos cambios. Antes de continuar,
ejecutar `git status --short` y revisar el diff existente como trabajo valioso
del usuario.

## Correccion clave: no existe una imagen HA de desarrollo

No hay, ni se quiere crear, una imagen de desarrollo/sideload de Home Assistant.
Introducirla complicaria innecesariamente el despliegue y la continuidad.

La `0.2.207` instalada en HA sabe reconstruir localmente, pero no contiene el
coordinador nuevo: no tiene pairing de workers, heartbeats, cola/claims,
transporte de snapshots/datasets/resultados, pagina `Workers y trabajos` ni
promocion de candidatos externos. Por tanto, es imposible hacer una prueba
funcional M1 ↔ HA real con `0.2.207`.

Orden viable a partir de este cierre:

1. Revisar y consolidar el gran diff local; mantener el fallback HA y todos los
   flags externos seguros por defecto.
2. Definir el alcance/configuracion de una version HA normal que incorpore el
   coordinador, la UI y los tres alcances del worker.
3. Solo con autorizacion expresa del usuario: hacer bump, validar, publicar,
   commit/push e instalar esa nueva version normal en HA.
4. Emparejar el worker M1 con HA real mediante LAN/Tailscale y ejecutar las
   pruebas end-to-end completas, parciales, cancelacion, desconexion,
   freshness, cache y promocion.
5. Medir entonces las fases en HA con la instrumentacion compartida y comparar
   HA/M1 sobre el mismo snapshot/dataset.

La topologia Tailscale puede estudiarse antes del release, pero no se puede
validar el flujo funcional contra HA real hasta que HA contenga el coordinador.

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
  release HA `0.2.207` no incorpora ni habilita esta ruta.

## Validacion local de cierre

Resultados comprobados el 2026-07-20 tras consolidar el diff:

- `.venv/bin/python -m unittest discover -s tests`: **369 tests OK**.
- `.venv/bin/python scripts/validate-mushroom-data.py`: **0 errores y 11
  warnings conocidos**.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: **OK**, incluidos los
  369 tests, sintaxis Python/JavaScript/shell, versiones y fixtures.
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

Estado: consolidacion local completada y validada, aun sin commit ni release.

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
4. Pedir autorizacion expresa antes de bump/release/GHCR/commit/push e
   instalacion.

### P2 — Prueba M1 ↔ HA real tras instalar esa version

- Emparejar M1 con una URL privada de HA y verificar identidad/ACL.
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

- El prototipo es grande y el worktree no esta versionado; una limpieza o
  revert accidental perderia trabajo.
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
