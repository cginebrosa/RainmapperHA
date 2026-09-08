# Handoff: integridad y rendimiento de transferencias HA--worker

Estado: auditoría de solo lectura cerrada el 8 de septiembre de 2026. Este
documento **no describe una optimización ya implementada**. Define el trabajo
posterior que debe medirse y validarse antes de modificar el protocolo.

## Resumen ejecutivo

La propuesta de calcular SHA-256 mientras se transfieren los bytes es correcta,
pero Rainmapper ya lo hace en parte. El mayor margen no consiste en retirar las
comprobaciones semánticas, sino en evitar que HA materialice cuerpos completos
en memoria, eliminar una segunda lectura dedicada únicamente al SHA cuando ya
existe un digest fiable y revisar el coste de la durabilidad por fichero en los
lotes multiversión.

El objetivo debe conservar estas propiedades:

- autenticación, autorización y límites antes de aceptar contenido;
- escritura en un fichero temporal y promoción con `os.replace`;
- tamaño y SHA-256 extremo a extremo;
- allowlist de rutas y correspondencia con job, claim y artefacto esperado;
- validación semántica del SQLite, manifiesto o modelo antes de activarlo;
- reintentos idempotentes y conservación del último artefacto operativo.

SHA-256 demuestra identidad de bytes. No sustituye `PRAGMA quick_check`, las
comprobaciones de esquema, cardinalidad, contexto, propietario del job o
identidad del artefacto.

## Comportamiento actual comprobado

### Descarga HA -> worker

`rainmapper_core/mushroom_worker_transport.py::_download_file` ya lee bloques de
1 MiB, los escribe y llama a `digest.update(chunk)` en el mismo bucle. Al final
comprueba tamaño y digest. Este camino ya tiene la lectura única deseada y no
debe rediseñarse sin una medición que muestre otro problema.

### Publicación del precálculo worker -> HA

El emisor, `rainmapper_core/mushroom_worker_service.py`, transmite el SQLite por
bloques de 1 MiB, pero necesita enviar un `X-Rainmapper-SHA256` previamente
conocido.

En HA, `rainmapper-app/app/web_server.py::read_request_body` lee actualmente
todo el cuerpo HTTP en un `bytes`. La ruta de recepción lo convierte después en
`io.BytesIO` y lo entrega a
`rainmapper_core/mushroom_predictor_precompute_control.py::publish_received_artifact`.
Esta función vuelve a recorrer los bytes mientras escribe el temporal y calcula
el digest. A continuación invoca
`rainmapper_core/mushroom_predictor_precompute.py::validate_artifact`, que hace
la validación semántica del SQLite y termina calculando otra vez el SHA-256
desde el fichero.

Por tanto, en este sentido sí existe una lectura de disco dedicada al hash que
puede evitarse y también una copia completa del payload en memoria que conviene
eliminar. El SQLite operativo comprobado en esta sesión mide `30.478.336` bytes.

### Resultados genéricos de reconstrucción

`rainmapper_core/mushroom_rebuild_contracts.py::build_result_manifest` crea un
manifiesto con tamaño y SHA-256. En recepción,
`rainmapper_core/mushroom_worker_results.py::_write_exact` calcula el digest a
la vez que escribe el temporal. Después,
`rainmapper_core/mushroom_rebuild_contracts.py::verify_result_manifest` vuelve
a verificar los ficheros preparados. Antes de retirar esa segunda lectura hay
que distinguir la validación de identidad de la validación semántica y mantener
un recibo fuerte de los bytes realmente persistidos.

### Lotes de entrenamiento multiversión

El batch operativo `operational_20260908T000329Z` ocupa aproximadamente `94M`
y contiene 642 ficheros. Los bundles están limitados a 16 MiB por
`RESULT_BUNDLE_MAX_BYTES`.

El emisor construye cada `tar.gz` en un `io.BytesIO`. HA recibe primero el cuerpo
HTTP completo y
`rainmapper_core/mushroom_ml_multiversion_transport.py::receive_result_bundle`
abre otro `BytesIO`; además, cada miembro se materializa con
`extracted.read()`, se hashea, se escribe y ejecuta `os.fsync` individualmente.
Las asignaciones intermedias deben eliminarse. Que los cientos de `fsync` sean
el coste principal es una **hipótesis**, no un hecho medido todavía.

Este transporte ya dispone de una optimización valiosa:
`_matches_received_digest` solo reutiliza un recibo cuando coinciden digest,
tamaño, dispositivo, inode, `mtime_ns` y `ctime_ns`; si no, vuelve a calcular el
hash. Es más robusta que una caché basada únicamente en tamaño y fecha de
modificación y debe conservarse o reforzarse.

## Propuesta concreta

### 1. Instrumentar antes de cambiar

Persistir tiempos y bytes por fase, como mínimo:

1. lectura de red;
2. hash y escritura temporal;
3. `flush`/`fsync`;
4. validación semántica;
5. promoción atómica;
6. confirmación al worker.

El servicio ya expone campos como `upload_round_trip_seconds`,
`ha_publish_seconds` y `estimated_transfer_seconds`, pero no permiten atribuir
el tiempo interno de HA a esas fases. El job terminado de referencia ya había
sido compactado y no se pudo recuperar un desglose histórico más fino.

### 2. Precálculo: recepción realmente incremental

La ruta debe autenticar y autorizar el job antes de leer el payload y después
copiar directamente `socket -> temporal` en bloques acotados, actualizando
tamaño y SHA-256 en el mismo bucle. No debe crear el `bytes` completo ni un
`BytesIO` intermedio.

No se recomienda depender de trailers HTTP a través del ingress de HA. Un
protocolo sencillo en dos fases evita exigir que el emisor conozca el SHA antes
de comenzar:

1. `upload`: el worker lee una sola vez, transmite y calcula su SHA; HA escribe
   el temporal, calcula el suyo y devuelve tamaño, SHA y un identificador del
   staging;
2. `finalize`: el worker compara ambos valores y envía una petición pequeña con
   su digest; HA comprueba la igualdad, valida semánticamente una vez y promueve
   con `os.replace`.

Si la API mantiene el hash previo en cabecera por compatibilidad, al menos debe
pasarse el digest ya calculado por la recepción a `validate_artifact` y evitar
que esta vuelva a leer los 30,5 MB solo para producir el mismo SHA.

### 3. Resultados genéricos y multiversión

- Aplicar el mismo patrón de recibo fuerte al resultado genérico antes de
  eliminar rehashes.
- Consumir el tar comprimido como stream o mediante un spool acotado, no como
  varios objetos `bytes` completos.
- Copiar cada miembro por bloques mientras se calcula su hash; no usar
  `extracted.read()` sin límite.
- Medir por separado el coste de los 642 `fsync`. Solo después decidir si puede
  sustituirse la durabilidad individual por una barrera de staging/lote que
  conserve recuperación tras caída y reintentos idempotentes.
- Mantener los límites de bundle y rechazar el tamaño declarado antes de
  materializarlo.

### 4. Caché de hashes

No introducir una caché ingenua `size + mtime -> SHA`. Para artefactos
inmutables y direccionados por contenido, conservar el digest sellado en el
manifiesto. Para ficheros mutables, reutilizarlo solo con una identidad fuerte
como la recepción actual: tamaño, dispositivo, inode, `mtime_ns` y `ctime_ns`,
o recalcularlo si cambia cualquiera de esos datos.

## Orden recomendado de implementación

1. Añadir telemetría y obtener una línea base en la Raspberry Pi 4.
2. Hacer incremental la recepción del SQLite de precálculo y eliminar su rehash
   redundante, manteniendo toda la validación semántica.
3. Aplicar recibos equivalentes a los resultados genéricos.
4. Convertir los bundles multiversión a lectura/escritura acotada.
5. Evaluar la estrategia de `fsync` con pruebas de interrupción reales.

Esta secuencia reduce primero memoria y E/S con un cambio acotado y deja el
protocolo de muchos ficheros, de mayor riesgo, para después.

## Criterios mínimos de aceptación

- El SHA del emisor y el calculado durante la recepción coinciden antes de
  promover.
- Tamaño incorrecto, hash incorrecto, cuerpo truncado, exceso de límite,
  reintento duplicado y credencial/job incorrectos son rechazados.
- Una caída en cualquier punto conserva el artefacto activo anterior y deja un
  staging recuperable o limpiable de forma segura.
- El SQLite promovido supera la misma validación semántica actual.
- No se carga en memoria un cuerpo completo ni un miembro grande del tar.
- Se mide RSS, bytes leídos de disco y duración por fase en HA real; no basta
  con un benchmark en el Mac.
- La mejora no aumenta la CPU ni las escrituras totales de la Raspberry Pi 4.

## Alcance de la release actual

HA `0.2.297` y el worker local `1.1.0` no incorporan esta optimización. La
release conserva el protocolo validado. Este documento es el punto de partida
para el próximo cambio, que exigirá nuevamente paridad local HA--worker y el
circuito completo correspondiente antes de publicar otra versión.
