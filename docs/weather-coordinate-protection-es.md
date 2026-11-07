# Protección y revisión de coordenadas meteorológicas

Implementación candidata del 04/11/2026, pendiente de aceptación en HA local.
No implica que HA real tenga ya esta funcionalidad. Sustituye el criterio
anterior que permitía ciertos saltos por tener destino dentro de España aproximada.

## Criterio común

La identidad es **fuente + código de estación**. Se compara con la última
ubicación aceptada, priorizando el catálogo del histórico particionado. Si
todavía no existe ese catálogo, se utiliza el registro local de estaciones.

- Un salto de más de **1 km** conserva la ubicación aceptada y abre una excepción.
  La descarga y el archivado continúan. Las coordenadas rechazadas son evidencia
  diagnóstica, nunca la nueva referencia del catálogo o la posición del mapa.
- Los saltos sucesivos se comparan siempre con la referencia aceptada. Una nueva
  ubicación estable, aunque se repita indefinidamente, requiere aceptación humana.
- Una respuesta nueva del proveedor que vuelve a estar dentro de 1 km retira la
  excepción. Releer un CSV, reconstruir días o reproducir un pendiente corregido
  **no** demuestra recuperación del proveedor.
- Las coordenadas y la metadata geográfica se corrigen antes de escribir los
  registros de estaciones o enriquecerlos por geocodificación. No se conservan
  altitud, municipio o provincia del punto rechazado como si fueran del aceptado.
  Cuando falta metadata fiable queda vacía hasta el enriquecimiento normal.
- Latitud, longitud y altitud se normalizan a columnas numéricas, también cuando
  no hay un salto que corregir. Así la captura Parquet admite metadata original
  en texto junto a valores corregidos numéricos, sin mezclar tipos en una columna.
- Al sustituir metadata geográfica, municipio, provincia y comarca admiten
  explícitamente texto y ausencias, aunque el CSV haya inferido una columna
  numérica por estar completamente vacía. Las mediciones mantienen sus tipos.
- Los consumidores del catálogo deben comparar esas coordenadas como números.
  Meteoclimatic normaliza también su CSV de estaciones, admitiendo decimales con
  punto o coma. Una diferencia de representación (`"41.43"` frente a `41.43`)
  no invalida la altitud ni provoca consultas de geocodificación. Conserva la
  altitud, municipio y provincia guardados cuando la posición coincide y la
  metadata cumple sus comprobaciones de validez; las estaciones nuevas, cambios
  efectivos de posición o metadata pendiente mantienen el enriquecimiento habitual.
- La agregación de Meteoclimatic redondea sólo las mediciones meteorológicas.
  **Latitud, longitud y altitud conservan su precisión**: el antiguo `round(1)`
  global empezaba a redondearlas después de convertirlas a números, por ejemplo
  `41.43` → `41.4`, y aparentaba un traslado antes del enriquecimiento.
- No cambian lluvia, temperatura, humedad o viento. El archivado sólo modifica
  las filas tocadas por los pendientes; no recorre ni traslada todo el histórico.

La política está en `rainmapper_core/weather_coordinates.py`. Los cuatro
adaptadores actuales la utilizan y el archivado tiene una defensa común para
pendientes anteriores. Una fuente futura debe llamar a `protect_frame(...,
fresh=True)` con metadata original del proveedor antes de guardar su registro.
La captura de filas reconstruidas utiliza `fresh=False`. La política no contiene
reglas de saltos específicas para una fuente.

### Cobertura geográfica y estaciones nuevas

`weather_coordinate_policy.json` contiene envolventes aproximadas para península,
Baleares, Canarias y Melilla; **no son fronteras administrativas**.
`Data/weather_coordinate_policy.json` puede sustituirlas. Ya no autorizan un
salto superior a 1 km de una estación conocida.

Una estación nueva sin referencia y con coordenadas inválidas o fuera de esas
envolventes se registra como incidencia sin ubicación aceptada. No se inventa un
punto ni se dibuja en el mapa. Una respuesta original válida dentro del ámbito
permite incorporarla. Se puede consultar la incidencia en el log; la revisión
desde una ficha del mapa requiere una estación que tenga ubicación aceptada.
La protección no puede reconstruir por sí sola una referencia que ya estuviera
corrompida antes de disponer de un catálogo fiable.

### Particularidad de Wunderground

La metadata conservada en su caché no sirve para retirar excepciones. Sólo para
las estaciones con excepción se vuelve a solicitar la cabecera de ubicación del
proveedor. Las demás conservan su reutilización habitual de metadata y la
descarga de observaciones por API. El fallback HTML de observaciones y los
reintentos de compresión no cambian. Una caché no revela un traslado que el
proveedor todavía no haya comunicado mediante metadata descargada.

El adaptador protege por separado la metadata nueva y la reutilizada. Si todas
las filas pertenecen a un solo grupo, lo procesa directamente; sólo concatena
cuando ambos grupos tienen filas. Así evita unir columnas normalizadas con un
grupo vacío que aún conserve los tipos originales del CSV. No cambia qué
evidencia puede retirar una excepción ni el orden de las filas.

## Revisar y aceptar desde el mapa

El GeoJSON de los mapas de periodos incluye, sólo para estaciones afectadas:

- `coordinate_exception: true`;
- `coordinate_since`: comienzo del seguimiento;
- `coordinate_acceptance_pending`: decisión guardada pendiente del runner.

La geometría sigue siendo el punto aceptado. No se publican la ubicación
rechazada ni el historial de decisiones en esos GeoJSON. El visor MapLibre
conserva el color de precipitación y añade un **borde ámbar**. La ficha explica
la incidencia y desde cuándo se sigue. El estado desaparecerá en la siguiente
publicación después de la recuperación o de aplicar la aceptación.

La cabecera muestra **Ubicaciones en revisión · N** junto al título, sin añadir
altura, cuando el periodo cargado incluye estaciones afectadas. El botón y su
lista se ocultan en pantallas de hasta 640 px de ancho; la revisión se utiliza
desde escritorio. Abre una lista agrupada por fuente, con búsqueda
por nombre, código o fuente (sin distinguir acentos). Incluye las estaciones
ocultas por los filtros de lluvia/fuente y por el encuadre; al seleccionar una,
se centra su posición aceptada y abre la ficha con un marcador temporal. No
modifica los filtros ni hace llamadas adicionales a proveedores. El recuento
corresponde al GeoJSON del periodo, no a todas las incidencias del servidor ni
a estaciones sin ubicación aceptada que no se pueden dibujar.

En una sesión de administrador del visor protegido aparece **Revisar ubicación**:

1. Abre una consulta actual al servidor, independiente de la antigüedad del mapa.
2. Muestra las posiciones aceptada y propuesta en el mapa, sus coordenadas,
   distancia y fecha de detección. Las etiquetas tienen una punta y un punto
   anclados a la coordenada exacta: azul para la aceptada y ámbar para la propuesta.
   **Ver aceptada**, **Ver propuesta** y **Ver ambas** permiten acercarse a cada
   punto o recuperar la vista conjunta. Los detalles tienen contraste explícito
   sobre el fondo oscuro, también en móvil.
3. **Conservar ubicación actual** cierra la revisión sin modificar nada.
4. **Aceptar traslado** guarda la decisión con usuario, fecha y ambas posiciones.
   Se muestra «Traslado aceptado, pendiente del siguiente runner».

El servidor exige una sesión de administrador tanto para consultar como para
aceptar. Ocultar el botón no es el control de autorización. La aceptación lleva
una revisión de la incidencia: si cambió la propuesta o la incidencia desapareció,
responde 409 y hay que revisarla de nuevo. No se aceptan coordenadas arbitrarias
enviadas por el navegador: se acepta exactamente la propuesta que guarda HA.

La aceptación se activa al comienzo del **siguiente runner de actualización**,
antes de procesar pendientes. Una aceptación durante un runner queda para el
siguiente; no interrumpe una escritura en curso. El catálogo y los datos publicados
se actualizan por el circuito normal. La aceptación sigue pendiente hasta que
la nueva ubicación queda persistida en el catálogo (o en el registro de estaciones
si se ejecuta sin histórico particionado). Los mapas ya publicados no se desplazan
inmediatamente al pulsar el botón. Esta revisión se ofrece en los mapas de
periodos publicados; no se ha añadido al visor histórico ni al mapa de predicción.

Endpoints del servidor web, no del listener de workers:

- `GET /api/weather/coordinates?source=…&station_code=…`;
- `POST /api/weather/coordinates/accept`, cuerpo con `source`, `station_code`
  y `revision`, máximo 2 KiB.

## Log, persistencia y recuperación

El runner web/programado escribe **un bloque Coordenadas al final**, antes del
código de salida y duración. Agrupa por fuente las excepciones activas y las
recuperaciones/aceptaciones aplicadas en esa ejecución. Cada excepción muestra
código, nombre, referencia aceptada, última posición recibida, distancia, comienzo
del seguimiento y tiempo transcurrido. También indica las aceptaciones pendientes.
El runner shell del add-on imprime el mismo resumen al salir.

`Data/weather-coordinate-state.json` guarda exclusivamente las excepciones,
aceptaciones en transición y una auditoría acotada a los últimos **200 eventos**.
No contiene series meteorológicas ni el historial de todos los saltos recibidos.
Los contadores por fuente de recuperaciones y aceptaciones aplicadas del runner
se guardan aparte del detalle acotado, para no perder el total al superar 200 eventos.
El comienzo de seguimiento de una excepción antigua del TXT es nuevo: se marca
expresamente que su antigüedad anterior es desconocida. No se inventa la fecha
original del fallo.

La escritura utiliza bloqueo entre hilos/procesos y sustitución atómica. Límites:
4096 entradas por colección y 2 MiB para el estado serializado. La codificación
se comprueba incrementalmente antes de escribir. No se añaden llamadas de
geocodificación ni lecturas de todas las particiones al resolver un pendiente.

El manifiesto del histórico conserva las correcciones aplicadas a los lotes aún
sin confirmar: `coordinate_policies` contiene cada política por hash y
`coordinate_policy_by_batch` referencia ese hash. El cierre del CSV utiliza la
misma política aunque se haya recuperado la estación o cambiado una decisión
después del commit de `CURRENT.json`. Se mantiene la lectura de receipts antiguos
`fixed_coordinates_by_batch`. Los pendientes originales son inmutables.

### Compatibilidad con el TXT Meteoclimatic

`/share/rainmapper/meteoclimatic-fixed-coordinates.txt` sigue admitido como referencia
explícita. Al recibir metadata original dentro del margen, su línea se comenta
automáticamente; se conserva el texto y las demás entradas. Editar un pin sigue
siendo una decisión explícita del operador. Para la gestión ordinaria se utiliza
la revisión del mapa y ya no es necesario añadir manualmente cada nuevo salto.
Comentar una línea no desactiva la protección común de 1 km.

## Validación

Las pruebas dirigidas cubren saltos sucesivos, identidades por fuente, recuperación
únicamente con metadata original, recuperación del TXT, filas horarias antiguas,
datos inválidos, concurrencia, autorización, aceptación obsoleta, aplicación en
el siguiente runner, replay después de `CURRENT` y anotación mínima del GeoJSON.
La prueba `MeteoclimaticStationCacheTests` recorre protección, reutilización del
catálogo anterior con tipos/decimales mixtos, una segunda ejecución sobre el CSV
reescrito, combinación de metadata, captura Parquet y archivado. Verifica que
se conservan coordenadas, altitudes y lluvia sin consultas externas innecesarias,
y que un cambio real, una altitud ausente o una estación nueva siguen consultándose.
No basta con validar sólo la conversión de tipos o sólo la escritura Parquet.
La prueba del procesamiento completo ejecuta también `create_meteoclimatic`, su
agregador real y `save_incremental_meteoclimatic`, antes de cerrar los pendientes.
Repite el recorrido para comprobar que una segunda lectura idéntica no vuelve
a consultar metadata ni altera coordenadas, altitud o lluvia. Sólo se sustituyen
los servicios externos; una consulta inesperada a Google hace fallar la prueba.
`tests/coordinate_review_browser_check.mjs` comprueba el componente real de revisión
en Chrome/MapLibre con una API aislada y elimina su perfil temporal al terminar.

La evidencia y los límites de la aceptación local se registran en
[el informe de validación](reports/weather-coordinates-local-2026-11-04.md).

## AEMET: ubicaciones y observaciones sin lluvia

El descargador conserva metadata y otras variables aunque el horario no incluya
precipitación. Completa las ubicaciones que falten con el inventario oficial de
AEMET y pasa esa respuesta por la misma protección que las horarias. Así, los
avisos `unlocated` pueden resolverse con evidencia original del proveedor; una
relectura de pendientes no los retira. Las coordenadas aceptadas siguen protegidas
por el umbral de 1 km, también cuando la estación no mide lluvia en esa respuesta.
Véase el [contrato de descarga y catálogo](../rainmapper-app/DOCS.md#estaciones-sin-precipitación-y-catálogo-de-ubicaciones).
