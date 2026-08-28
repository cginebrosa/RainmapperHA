# Entrega local sellada entre trabajos encadenados del worker

Fecha de evidencia: 2026-08-28. Estado: especificación tras ejecución real; no desplegada.

## Problema observado

Una reconstrucción operativa remota se divide actualmente en tres trabajos autónomos:

1. reconstrucción de artefactos;
2. entrenamiento ML v0;
3. entrenamiento multiversión V2--V6.

La separación conserva cancelación, retry y promoción atómica, pero cada trabajo vuelve
a preparar un directorio aislado, descargar o materializar entradas y verificarlas. En
la ejecución real observada:

- la reconstrucción `worker_job_W-DEAqj5hmiInR7D` tardó 7 min 21 s;
- el ML v0 `worker_job_ysdIPlkM32sI91wy` tardó 2 min 28 s;
- el tercer trabajo declaró 56 entradas y 61.392.025 bytes;
- las etapas reutilizaban el mismo dataset GIS sellado, de 12 ficheros,
  6.341.520.039 bytes y fingerprint
  `sha256:5b537ffebbb9c17ce380ee21257204465eb1e310a159a05a224d74b65c7fe729`;
- el monitor de red no mostró una transferencia masiva durante la fase presentada como
  `Downloading immutable inputs`: la fase también cubría comprobación y materialización;
- el tercer trabajo terminó fallando porque el contrato operativo omitía
  `tuning-catalog.json`, no por red.

Por tanto hay dos defectos distintos: una etiqueta de fase imprecisa y trabajo local
redundante; además se detectó una omisión concreta del catálogo de ajuste.

## Objetivo

Cuando dos etapas consecutivas se ejecuten en el mismo worker, la siguiente debe consumir
la salida sellada local de la anterior sin volver a subirla a HA y descargarla. HA conserva
la copia canónica y sigue siendo el fallback para otro worker, pérdida de caché o retry.

No se fusionan los trabajos. Se conserva un límite durable entre etapas para poder
cancelar, reintentar, auditar, descartar y promover de forma atómica.

## Contrato propuesto

Cada salida encadenable se publica en el worker como un conjunto direccionado por
contenido:

- fingerprint global del conjunto;
- manifiesto de rutas, tamaños y SHA-256;
- identidad del trabajo productor y propósito;
- recibo local de verificación escrito atómicamente y sincronizado a disco;
- estado de retención: `leased`, `releasable` o `canonicalized`.

El trabajo consumidor recibe tanto la referencia canónica de HA como una referencia
opcional al productor. Si coincide el worker, fingerprint, manifiesto y recibo:

1. enlaza o copia localmente los objetos sin rehashearlos;
2. registra `input_source=local_sealed_handoff`;
3. no solicita esos bytes a HA.

Si cualquier comprobación falla, descarta el atajo y usa la descarga canónica. Nunca usa
un objeto local cuyo manifiesto o recibo no coincidan exactamente.

## Cambios de ejecución

El worker necesita un almacén local común de objetos por SHA-256, separado de los
directorios efímeros de cada trabajo. La limpieza del directorio de un trabajo no debe
borrar objetos con una lease activa de un consumidor. HA puede ordenar la limpieza tras
recibir el acuse terminal del último trabajo de la cadena.

La reconstrucción debe publicar localmente features y demás salidas que necesita ML v0.
ML v0 debe publicar sus modelos y metadatos para V2--V6. El tercer trabajo debe reutilizar
además el snapshot meteorológico/GIS ya sellado cuando su fingerprint sea idéntico.

No se incluye el resultado final de Predictor en este almacén; conserva su transporte
dedicado, límite y SHA-256.

## Fases y telemetría

La UI no debe llamar `Downloading` a toda la preparación. Debe separar:

- `Resolving immutable inputs`;
- `Reusing sealed local inputs`;
- `Verifying unsealed inputs`;
- `Downloading missing inputs`;
- `Materializing job workspace`.

Cada fase persiste duración monotónica y contadores de ficheros y bytes reutilizados,
hasheados, descargados, enlazados y copiados. También registra fingerprint, productor y
motivo de fallback. Así se podrá distinguir red, hashes, copias y espera de control.

## Integridad, retry, cancelación y rollback

- HA sigue siendo la autoridad y nunca se sustituye por una caché únicamente local.
- El recibo solo se escribe después de verificar todo el conjunto y hacer `fsync`.
- Un retry puede usar el conjunto sellado; si no existe, descarga de HA.
- La cancelación libera la lease del consumidor, no el objeto mientras otro trabajo lo use.
- La promoción final continúa verificando el candidato recibido por HA y es atómica.
- La limpieza conserva al menos el productor mientras exista una cadena activa o una
  promoción pendiente.

## Criterios de aceptación

- En una cadena completa sobre el mismo worker, las etapas dos y tres transfieren cero
  bytes de entradas ya producidas o ya selladas localmente.
- Una reutilización sellada realiza cero hashes de contenido; puede leer manifiesto y
  recibo y comprobar metadatos estructurales.
- Cambiar de worker o borrar la caché provoca fallback correcto a HA.
- Corromper un objeto o recibo impide su reutilización y no altera la copia viva.
- La UI refleja por separado bytes reutilizados, verificados y descargados.
- Se mantienen las mismas especies, perfiles, particiones, métricas y artefactos finales.
- El flujo completo debe quedar en 10 minutos o menos; si el cálculo científico por sí
  solo supera el presupuesto, se informa por fase en vez de ocultarlo como transporte.

## Incidencia del catálogo de ajuste

El trabajo multiversión operativo exige un catálogo de ajuste congelado derivado del lote
instalado. La cadena remota no lo incluía en `extra_inputs` ni en el comando de preparación.
La corrección debe sellarlo como `snapshot/inputs/extra/tuning-catalog.json` y pasar
`--tuning-catalog`. No es aceptable relajar la validación, porque entrenaría con decisiones
distintas sin hacerlo visible.

## Implementación local inicial

La primera entrega local añade un almacén común de entradas inmutables por SHA-256.
Cada objeto se descarga a un temporal, se comprueba, se sincroniza y solo entonces se
publica mediante `replace`; el recibo de verificación se escribe después. Un trabajo
posterior enlaza el objeto sellado y no lo descarga ni lo hashea de nuevo. Las entradas
de ML v0 declaran ahora hash y tamaño para que sus features puedan reutilizarse en el
trabajo V2--V6.

El presupuesto de 1 GiB es blando: nunca elimina los objetos protegidos por la operación
actual, aunque el conjunto sea mayor. Solo poda por antigüedad objetos no protegidos al
terminar de materializar. Por ello no introduce un límite de observaciones ni modifica
la opción de retención de modelos; limita residuos reutilizables entre operaciones.

El manifiesto y el job spec siguen descargándose y validándose por trabajo, pero son JSON
pequeños. Los objetos GIS conservan su caché versionada y los meteorológicos adquieren el
mismo recibo sellado. Queda pendiente medir una cadena remota completa después de release;
la validación de esta entrega es local.
