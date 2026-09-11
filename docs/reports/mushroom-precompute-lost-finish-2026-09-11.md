# Precálculo: pérdida de la notificación final — 11/09/2026

## Incidencia verificada

HA real `0.2.302` conservó `worker_job_5ryH9BEsc60-` en `running`, con
71,99/160 unidades, aunque el worker había liberado el carril. Los logs de
`docker logs --timestamps --tail 160 rainmapper-worker`, reconsultados durante
la corrección, registran estas horas UTC:

| Hora | Hecho |
| --- | --- |
| 01:46:36 | Asignación al worker principal. |
| 01:50:07 | Timeout del heartbeat hacia HA. |
| 01:50:35 | Fin del cálculo: 236,864562 s; entrada en fase `upload`. |
| 01:53:59 | `Connection refused`; liberación con `finish_acknowledged=false`. |
| 01:55:11 | Heartbeat restablecido. |

Terminó el **cálculo**, no el trabajo completo de entrega y confirmación.
71,99/160 era el último progreso recibido por HA, no la posición final del
cálculo en el worker. El SQLite de staging pasó la validación completa nativa:
27.369.472 bytes, 567 celdas, 483 miembros, identidad
`sha256:1bae9bbfcc72b67568f377a592ced3f0dffe99d2cdbcbc15105184b661e48543`.

La lectura de `/Volumes/share/rainmapper/mushroom-data/mushroom_worker_jobs.json`
confirmó posteriormente el abandono del operador: `cancelled`, fase
`Abandoned`, `finished_at=2026-09-11T02:09:56+00:00`. El intento de recuperación
puntual quedó descartado. No se reenvió ni activó el SQLite y no se lanzó otro
precálculo desde Codex.

La causa de los timeouts/rechazos de conexión sigue sin determinarse. Los
diagnósticos disponibles no justifican atribuirlos a OOM ni a un reinicio.

## Defecto y corrección local

`run_claimed_job`, dentro de `mushroom_worker_service.serve`, intentaba enviar
`finish` con reintentos acotados. Si fallaban, capturaba la excepción y liberaba
el carril sin conservar la notificación. El heartbeat posterior no reparaba
ese estado perdido.

La corrección incorpora `mushroom_worker_completion.PrecomputeCompletion`:

- Guarda el aviso terminal del precálculo antes de su primera entrega. Es el
  payload de la API `finish` existente, sin SQLite ni filas de predicción.
- Una posición persistente por coordinador, límite de 64 KiB, escritura
  atómica con fsync y permisos 0600. Guarda el token de asignación necesario
  para `finish`; no guarda el token permanente ni cambia destinos.
- Si se pierde la respuesta de éxito, conserva `complete`: un error de
  transporte posterior no lo sustituye por `failed`.
- Después de un heartbeat correcto, cuando ya terminó el hilo de ese trabajo,
  realiza un intento de entrega con timeout de 3 s. Los errores conservan el
  aviso para la siguiente vuelta, incluso tras reiniciar el servicio.
- Mientras quede un aviso pendiente, no reclama otro trabajo de fondo para
  ese coordinador. Los demás coordinadores y las consultas interactivas
  conservan su posibilidad de trabajar. Se vuelve a comprobar el aviso justo
  antes de reclamar, para cubrir la carrera con la salida del hilo anterior.
- La API de HA ya acepta `finish` repetido con el mismo estado. Si HA confirma
  abandono, un estado terminal diferente, otra asignación o que el trabajo ya
  no existe, se descarta únicamente el aviso obsoleto. No se reactiva el job
  ni se limpia un posible workspace de otra asignación.
- Ante una cancelación pendiente, se consulta `control` y se persiste/envía
  `cancelled` si HA la confirma. Errores de autenticación, conflictos
  desconocidos y respuestas inválidas no se consideran confirmaciones.
- La limpieza existente de jobs no borra el aviso. Tras aceptación se utiliza
  la limpieza nativa y su acuse en heartbeat. Los errores del aviso se registran
  como `job_finish_pending`, separados de los fallos de heartbeat.

El alcance es el cierre de precálculos. No añade reenvío automático de SQLite,
reentrenamiento, otro precálculo, recuperación del trabajo abandonado ni
cambios en modelos. Tampoco garantiza actualizar HA mientras HA sea inaccesible:
la reparación del estado ocurre cuando vuelve la comunicación.

## Validación y estado de entrega

`.venv/bin/python -m unittest discover -s tests -p 'test_mushroom_worker_*.py'`:
**160 pruebas correctas, 15,609 s** sobre el código de esta corrección.

Incluye diez pruebas del aviso persistente contra la cola real de trabajos:
éxito confirmado cuya respuesta se pierde, fallo pendiente, cancelación,
abandono, asignación antigua, desaparición del historial, autenticación,
límites, permisos y aislamiento entre coordinadores. Otra prueba ejecuta el
servicio real en un proceso independiente contra un servidor HTTP de pruebas:
rechaza `finish`, comprueba que no reclama otro precálculo, reinicia el servicio
y acepta el mismo aviso conservado. No ejecuta cálculo científico.

En esta primera validación la corrección estaba en el worktree y Dockerfile,
sin reconstruir, instalar ni publicar; HA real y el worker aún ejecutaban sus
imágenes anteriores. La reconstrucción autorizada posterior se registra al
final del informe. No se necesita un cambio de API en HA.

## Repetición lanzada por el usuario, sin instalar la corrección

El usuario prefirió repetir el precálculo con el worker existente. Codex
supervisó mediante logs y lectura de la cola/recibo montados, sin iniciar,
cancelar ni reenviar trabajos. `worker_job_T83NizH1i5bM` superó el último avance
71,99/160 del intento anterior y terminó correctamente:

- Asignación 02:26:54 UTC; cálculo 252,558316 s.
- Entrada en entrega 02:31:08; HA recibió el archivo a las 02:31:10.
- Timeout del heartbeat 02:31:15, durante la verificación/activación de HA.
- HA terminó de activar a las 02:32:07; heartbeat restablecido 02:32:08.
- Activación del worker y finalización 02:32:17; log
  `finish_acknowledged=true`; duración del hilo 323,942985 s.
- Cola de HA: `complete`, 100 %, sin error, revisión 113. Su recibo activo
  coincide con el guardado en el resultado del job:
  `sha256:367672a0e58a1c70ef8b3cbba785425c2821524a83cc9433843ed394e89801cd`.
  Artefacto `sha256:1bae9bbfcc72b67568f377a592ced3f0dffe99d2cdbcbc15105184b661e48543`,
  27.377.664 bytes; SHA-256
  `sha256:2b72666a59b400595d3851f63d4cd3f2891f4bb7b458827914aea4a83bec5bca`.

La telemetría separa 57,095007 s de publicación en HA y 10,047821 s de
activación en el worker. Los 1,578465 s restantes del viaje de entrega son una
estimación por diferencia, no una medición aislada del tiempo de red.

Esta repetición demuestra que el fallo final no se reproduce en todos los
intentos. También sitúa otro timeout durante la publicación en HA; la
coincidencia temporal no demuestra por sí sola su causa. No se instaló la
corrección y este éxito no valida su despliegue ni elimina el defecto de
notificación final identificado en el código anterior.

## Reconstrucción autorizada del worker y publicación de HA 0.2.303

Después de otra ejecución de runner/precálculo, el usuario confirmó su fin y
pidió reconstruir el worker y publicar HA. El worker privado `1.1.1` está
reconstruido/recreado con el código de esta corrección. Sus dos asociaciones
conservan URLs y huellas. HA local/worker: 145/77 Python efectivos coincidentes
con el worktree.

La imagen nueva pasó las diez pruebas del aviso y las cuarenta del servicio
mediante contenedores efímeros sin red externa, con tests montados de solo
lectura y sin datos operativos. Se probaron notificaciones y ciclo de servicio;
no se repitió entrenamiento ni precálculo científico. Smoke de release:
1.395 pruebas correctas en 62,506 s. La corrección ya está instalada en el
worker local; no se ha publicado una nueva imagen de worker en GHCR.

HA `0.2.303` publicada tras build con salida 0. Sus tags de versión y `latest`
comparten el índice
`sha256:4b70a512bca003f859e27379cd143cd5fb62fc6955d5f4632dfb50cce9ee97cf`,
verificado con manifests `linux/amd64` y `linux/arm64`. La instalación en HA
real queda a cargo del usuario; última versión real comprobada: `0.2.302`.
