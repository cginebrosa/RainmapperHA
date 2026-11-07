# Coordenadas: validación local del 04/11/2026

Estado actualizado el 07/11/2026: candidata preparada en HA local para el runner
del usuario; HA real no se ha actualizado. La revisión posterior del 07/11 al
final de este informe sustituye la imagen y las cifras de la validación inicial.

## Incidente utilizado

Snapshot aportado por el usuario en `docker-data/ha-coordinate-jump-20261104/Data`.
Generación verificada: `20261103T100716028590Z-9d098ebf3f73`.
Estación Meteoclimatic `ESCAT4300000043003B`, Tarragona-Fortí St. Jordi:

- Catálogo aceptado: `41.12, 1.27`, altitud 16 m.
- Pendiente: `41.20, 1.45`, distancia aproximada 17.499 km.
- Ocho filas de la estación en un lote de 7223 filas. Otros tres lotes pendientes:
  AEMET, Meteocat y Wunderground.

Se copió únicamente la generación activa y los pendientes a un directorio
temporal; no se modificó el snapshot recibido ni los datos operativos.
El archivado común completó los cuatro lotes sin un pin manual para Tarragona.
Conservó las mediciones no vacías originales de las ocho filas, utilizó la
ubicación aceptada y mantuvo iguales los hashes de 42 particiones. Repetirlo no
produjo un nuevo commit. Los hashes de los pendientes originales se comprobaron
antes y después. La copia temporal se eliminó.

Tiempo observado en Python nativo del Mac: **11.686 s** para archivar los cuatro
lotes. No es una medida de Raspberry Pi ni del runner completo. Estado diagnóstico
producido: **19253 bytes**; incluye las incidencias de todas las fuentes del lote,
no sólo Tarragona.

## Comprobaciones ejecutadas

- 104 pruebas dirigidas: protección de coordenadas, pendientes, writer, pipeline,
  TXT Meteoclimatic, AEMET, CSV vivo, GeoJSON, integración web y traducciones: OK.
- Chrome/MapLibre, componente real de revisión con API aislada: OK para borde
  ámbar, dos marcadores, aceptación pendiente, geometría publicada sin cambio
  inmediato, rechazo de propuesta obsoleta, ausencia de botón para no administradores
  y retirada de marcadores/perfil temporal.
- Comprobación general final: **2180 tests**, 134,864 s en la suite Python;
  script `scripts/smoke-test.sh` terminado con `Smoke test passed`, exit 0.
  Incluye además sintaxis, versiones, fixtures y controles de whitespace.

## Imagen y ejecución de HA local

Imagen `rainmapperha:local-ha-ui`, arquitectura `arm64`, reconstruida desde la
candidata de `inicial`:
`sha256:38a2000d8e5ba372e6d5cd31f604aa80dd088d3f1520ffab498020b2c734324b`.
Se recreó únicamente `rainmapper-local-rainmapper-ha-ui-1`; se verificaron los
12 archivos efectivos afectados por SHA-256 contra el checkout. Huella del
módulo nuevo `rainmapper_core/weather_coordinates.py`:
`e7cd92acd81983c61f9ec1c855e44084e19678a0448798151e957178e7f7c65b`.

Las claves y montajes de datos se conservaron; agenda local desactivada. Compose
base de `inicial`, sin el override MCP de la rama LLM. La portada respondió HTTP
200 y la consulta de coordenadas sin sesión HTTP 401. Worker y contenedor MCP
separado no se reconstruyeron ni recrearon.

Se repitió el caso real dentro de ese contenedor con otra copia temporal de la
generación activa y los pendientes, esta vez incluyendo el cierre de CSV:

- Cuatro lotes archivados y confirmados en **14,479 s**.
- Ocho filas de Tarragona conservadas; **160 campos no geográficos** no vacíos
  coincidentes con los pendientes, coordenadas aceptadas `41.12, 1.27`.
- **42 de 46 particiones** mantuvieron exactamente su hash.
- Sin pendientes tras cerrar los CSV; repetir el archivo no creó otra generación.
- Estado de excepciones de **20.261 bytes**: AEMET 34, Meteocat 1,
  Meteoclimatic 1. Son las incidencias de esos lotes históricos y del catálogo
  del snapshot, no una auditoría de las respuestas actuales de los proveedores.
- CURRENT y pendientes originales intactos; copia temporal eliminada al salir.

Estos tiempos son del Mac/Docker local, no de la Raspberry Pi ni de una descarga
completa. La prueba de navegador usa el componente real con una API aislada;
no sustituye la comprobación operativa del usuario en el visor local.

El traslado posterior a la carpeta raíz en `inicial` conservó las huellas de los
28 archivos pendientes; no cambió el código ya validado. No se repite el smoke
por ese traslado ni por los ajustes exclusivamente documentales.

Codex no lanzó un runner operativo, entrenamiento, precálculo, publicación de
imagen HA ni instalación en HA real durante esa validación inicial.

## Revisión posterior del 07/11: runner del usuario y mejoras del mapa

El usuario ejecutó el runner local a las 16:52 y aportó su log completo. Terminó
con exit 2: Meteoclimatic y Meteocat reutilizaron respectivamente 104.106 y 33.547
filas anteriores después de fallar la captura Parquet. Los errores fueron
`Expected bytes, got a 'float' object` en `Latitud` y `Altitud`.

Se reprodujeron ambos errores con la candidata anterior: la protección de
coordenadas introducía valores numéricos en columnas que conservaban texto del
proveedor/CSV. Era una regresión del cambio, ausente en los casos numéricos de
las pruebas iniciales. `protect_frame` normaliza ahora latitud, longitud y altitud
antes de aplicar correcciones, incluidos replays sin salto; las mediciones
meteorológicas no cambian. Dos pruebas nuevas cubren el recorrido hasta el
Parquet real, con tipos mixtos, coma decimal y ausencia de corrección geográfica.

La recuperación de Tarragona-Fortí St.Jordi (`ESCAT4300000043003B`) sí ocurrió
en ese run, antes del fallo de captura: evento `recovered` a las 16:52:25,
línea del TXT comentada automáticamente, registro en `41.12, 1.27` y GeoJSON
de 21 días sin excepción. No se deduce de ello que la descarga completa acabara bien.

El mapa incorpora el buscador agrupado de ubicaciones en revisión, marcadores
con punta anclada al punto exacto y controles para ver cada ubicación o ambas.
Se corrigió además el texto oscuro de los detalles sobre fondo oscuro.

Validación de la revisión:

- Smoke completo: **2182 tests, 55 omitidos**, 135,416 s; exit 0.
- Chrome/MapLibre en 1280×900 y 390×844: búsqueda por nombre sin acentos y código,
  agrupación, estación oculta por filtros, resultado vacío, desaparición del
  contador, puntas a menos de 2 px de la coordenada proyectada, contraste de
  detalles, controles de enfoque, permisos y rechazo de propuesta obsoleta: OK.
- Imagen local reconstruida/recreada:
  `sha256:518879564b646ee719a9c7b66bd7dd75ad72fd209db195b13bc6c9a573b76dec`.
  **13 archivos efectivos** coinciden con `inicial`; HTML, JS y CSS servidos por
  HTTP contienen las mejoras. Claves y volúmenes conservados; worker intacto.
- SHA-256 `weather_coordinates.py`:
  `d924f3a86b5070cc969492138f5b18c7c73e6200113bb500a2ab4f9c61b19242`.
- Dentro de la imagen, captura aislada sobre lecturas locales recientes, con
  metadata textual y un salto inducido: **7192 filas Meteoclimatic** en 0,542 s
  y **1494 Meteocat** en 0,149 s, todas capturadas en Parquet. Se verificaron
  coordenadas corregidas, columnas numéricas y mediciones sin cambios.
  Los tiempos corresponden sólo a protección/captura, no a descarga ni archivado.
- Los hashes de los ficheros operativos leídos quedaron intactos. Las copias
  temporales se eliminaron; las capturas visuales no forman parte del repo.

La comprobación independiente de Wunderground está en
[el informe de API del 07/11](wunderground-api-check-2026-11-07.md).
Pendiente repetir el runner operativo con esta imagen y aceptación del usuario.

## Ajuste posterior de cabecera del 07/11

El usuario detectó que el botón añadía una línea a la cabecera y pidió ocultarlo
en pantallas estrechas. Ahora comparte fila con el título, sin aumentar la altura;
el botón y su lista se ocultan con ancho de pantalla menor o igual a 640 px.

- Chrome, usando la cabecera HTML real con resumen, fecha y usuario: misma altura
  con y sin botón a 1280, 768, 641, 640 y 390 px; sin desbordamiento horizontal.
  El botón queda alineado con el título en escritorio y oculto a 640/390 px.
  Una lista abierta también se oculta al estrechar la pantalla. Continúan pasando
  las comprobaciones de búsqueda, marcadores, aceptación y permisos.
- Smoke completo del ajuste final: **2182 tests, 55 omitidos**, 132,187 s; exit 0.
- HA local reconstruido/recreado desde `inicial`:
  `sha256:dae5603b4bf448915c0c7e24c52a10e1e0f6d5518de3633e6f9194568514c3f3`.
  Los 13 archivos efectivos coinciden; HTML, JS y CSS servidos por HTTP verificados.
  Variables y montajes idénticos antes/después; worker intacto.
- SHA-256 de `index.html`:
  `8c1b692082965bcfaabf3a720290b97e0f0ad22479c6a8d22733609c1daf8fd1`.
- SHA-256 de `style.css`:
  `60358c4c5e79e48c92970f60e2beac0f3a0b15d37271e133654268283806f0d5`.
- No quedan perfiles temporales de Chrome. No se generaron capturas de pantalla
  ni copias de datos para este ajuste. La imagen local anterior ya no existe.

## Regresión de reutilización de altitudes: runner del 07/11 a las 17:22

**Primera corrección incompleta.** Las pruebas de esta sección omitían el
agregador de Meteoclimatic. El siguiente runner detectó el segundo efecto de la
normalización, explicado y corregido en la sección siguiente.

El runner iniciado por el usuario a las 17:22:27 volvió a consultar altitudes de
Meteoclimatic para estaciones existentes. Se registraron **752 estaciones** con
`Fetching altitude for station`; las 752 ya estaban en el catálogo local de
1.137 estaciones. No eran altas nuevas.

La regresión se introdujo al normalizar las coordenadas a números para resolver
la captura Parquet. `refresh_estacions_meteoclimatic` seguía leyendo el catálogo
con `decimal=','`, pero el fichero contenía coordenadas como texto con punto;
comparaba, por ejemplo, `41.43` con `"41.43"`. Esto invalidaba la reutilización de
metadata y provocaba consultas a Google Maps incluso con la misma posición.
La suite anterior no cubría este recorrido entre el catálogo previo y el guard.

Se detuvo únicamente el subproceso descargador local para cortar las consultas.
El runner completó el archivado de los pendientes de AEMET, Meteocat y
Wunderground, y terminó a las 17:26:06 con **exit 1**, duración 3 min 39 s.
Ese resultado corresponde a la interrupción deliberada y no acredita una
ejecución completa correcta. Meteoclimatic no llegó a reescribir su catálogo:
se comprobó la misma fecha de modificación antes/después y quedó conservado
el SHA-256 `42458cbba939698c39d8c806780655edf6d2e9fc2772dcb2f4ac650c916c604a`.

La corrección normaliza latitud, longitud y altitud de ambos lados antes de
compararlos, admite punto/coma decimal y conserva la metadata válida del catálogo.
Las estaciones nuevas, posiciones efectivamente distintas o altitudes ausentes
continúan consultándose. No se modificó la protección de 1 km.

Validaciones específicas:

- Dos pruebas nuevas fallaron con el código anterior y pasan con el corregido.
  La principal recorre protección, reutilización del catálogo, segunda ejecución
  sobre el CSV reescrito, combinación de metadata, captura Parquet y archivado.
  Comprueba coordenadas, altitud, lluvia y ausencia de llamadas de geocodificación.
  La segunda distingue una estación sin cambios de una trasladada, otra sin
  altitud y otra nueva. Las pruebas se ejecutaron con `FutureWarning` como error.
- Replay aislado de las **752 estaciones del log**, usando sus posiciones
  guardadas como entrada numérica: **752 llamadas simuladas antes; 0 después**.
  Duraciones de la función: 0,274 s antes y 0,164 s después; no son tiempos de
  descarga. El replay prueba el cambio de representación con posición idéntica;
  no comprueba por sí solo todas las coordenadas que publica hoy el proveedor.
- Cero peticiones reales durante el diagnóstico. El CSV operativo mantuvo su
  hash; la copia temporal se eliminó. Se conservaron también los dos snapshots
  JSON de observaciones.
- Imagen local reconstruida/recreada:
  `sha256:755d1586ee9f3174913e099ec773703257b5dfe6a9745ece46fe4d6de5ea14bf`.
  Los 13 archivos efectivos coinciden con el worktree. SHA-256 de `rainmapper.py`:
  `8d7fb4f5b591f7705d0ebafe83c5e79e510ce0ec5173285000d7b3fb51eee214`.
  Las dos pruebas específicas pasan también **dentro de esa imagen**, en 0,160 s,
  con metadata y archivo Parquet aislados; sus temporales se eliminan al terminar.
- El usuario confirmó mediante captura que HA real usa `max_threads: 1`.
  Local omitía ese valor y utilizaba 3 por defecto: por eso sus logs se intercalaban.
  Se establece explícitamente 1 en `rainmapper-local/options.local-ha-ui.json` y
  se verifica `RAINMAPPER_MAX_THREADS=1` en el proceso efectivo del servidor local.
  Este parámetro controla tanto las fuentes simultáneas como los hilos internos
  de Wunderground; con 1, ambas ejecuciones son secuenciales.
- Smoke completo: **2184 tests, 55 omitidos**, 133,787 s, exit 0. La comprobación
  específica añade además igualdad de coordenadas, altitud y lluvia entre el
  pendiente capturado y la partición Parquet finalmente archivada.

No se ha publicado ninguna imagen en HA real. Falta el runner completo del
usuario con esta candidata; las pruebas aisladas y el smoke no lo sustituyen.

## Segundo fallo: redondeo de coordenadas en el agregador, 07/11 a las 17:33

El usuario volvió a lanzar el runner a las 17:33:55. AEMET terminó en 12,661 s;
Meteoclimatic volvió a consultar altitudes. Se detuvo sólo el descargador local:
**229 estaciones consultadas**, final a las 17:35:32, exit 1 y duración 1 min 37 s.
El catálogo Meteoclimatic mantuvo el hash de la sección anterior.

Al revisar el recorrido que las pruebas anteriores omitían, se encontró
`create_total_meteoclimatic`: aplicaba `round(1)` a todas las columnas numéricas.
Antes las coordenadas eran texto y no se redondeaban; tras la normalización,
Barcelona-Rectoret pasaba de `41.43, 2.10` a `41.4, 2.1`. La comparación numérica
con el catálogo detectaba entonces una posición realmente distinta, fabricada
por ese redondeo. Por eso la primera corrección no bastaba. Ambos efectos fueron
regresiones introducidas por el cambio de tipos, no nuevas estaciones del proveedor.

Se conserva la normalización de ambos lados del catálogo y se restringe el
redondeo del agregador a las mediciones: latitud, longitud y altitud mantienen
su precisión. No se cambia el umbral de protección ni se acepta ningún traslado.

La nueva prueba ejecuta **las funciones reales de creación y guardado incremental
de Meteoclimatic**, incluido el agregador, hasta el archivado y cierre del CSV.
Falló con la primera corrección al intentar geocodificar y pasa con la definitiva.
Comprueba dos ejecuciones: la segunda idéntica no genera otro commit de histórico.
Las tres pruebas específicas pasan dentro del contenedor con `FutureWarning`
tratado como error (0,403 s).

El usuario autorizó una prueba real pequeña con Google Maps disponible y sin
consultas masivas. Se ejecutaron dos pasadas con **dos estaciones**:

| Estación | Coordenadas RSS recibidas | Resultado |
| --- | --- | --- |
| Barcelona-Rectoret, `ESCAT0800000008017D` | 41.43, 2.10 | Posición y altitud 385 m conservadas |
| Godelleta, `ESPVA4600000046388A` | 39.43, -0.68 | Posición y altitud 281 m conservadas |

- Cada pasada ejecutó la creación, normalización, agregación, enriquecimiento,
  guardado incremental y archivo Parquet de esas dos estaciones, con RSS real.
- Duraciones: **2,460 s** y **2,439 s**. Son tiempos para dos estaciones e incluyen
  la pausa de 2 s entre patrones; no extrapolarlos a la fuente completa ni a la RPi.
- Se recibieron cuatro respuestas RSS en total. **Cero enriquecimientos Google
  Maps**: se reutilizó el catálogo. La prueba tenía un máximo explícito de dos
  enriquecimientos permitido, compartido entre ambas pasadas, para cortar una regresión.
- Posición, altitud y lluvia coinciden entre la salida de la fuente y el Parquet
  archivado. El catálogo operativo mantuvo su hash; se utilizó una copia temporal
  de 1.137 estaciones y un histórico de prueba pequeño, eliminados al terminar.
- Imagen local reconstruida/recreada:
  `sha256:653bc208d1e4d0b6518547d66e991bdaa4cc4d8be80e6d3097efdd5cfff373dd`.
  Los 13 archivos efectivos coinciden con el worktree; se conserva `max_threads: 1`.
  SHA-256 de `rainmapper.py`:
  `e5b94aca8dad6defc8242c3f15c6a3b21438421e9816c0d3d9bc151b73b27210`.
- Smoke final: **2185 tests, 55 omitidos**, 136,191 s, exit 0.

No se ha relanzado un runner completo ni tocado HA real después de la parada.
La validación real final está limitada a esas dos estaciones y las pruebas de
regresión descritas; no debe presentarse como éxito de todas las fuentes.

## Runner del usuario del 07/11 a las 21:44 y 17 avisos de AEMET

El log aportado por el usuario registra una ejecución local completa entre
21:44:37 y 21:48:07, **3 min 30 s, exit 0**, y publicación local de siete GeoJSON.
Meteoclimatic termina en **16,647 s**, con 890 estaciones recibidas entre los seis
patrones y 0,2 s de gestión del catálogo. No aparece ningún mensaje `Fetching
altitude` en este log. Esta ejecución aporta la validación completa que faltaba
en la sección anterior para la regresión de consultas de altitud. No demuestra
que todos los proveedores entreguen lecturas recientes: Wunderground todavía
registra respuestas antiguas y tres estaciones fallidas.

Los **17 avisos AEMET no corresponden a saltos de coordenadas**. Comprobado en
`docker-data/Data/weather-coordinate-state.json`: todos tienen `reason=unlocated`,
`evidence=pending`, `accepted=null`, `received=null`, `distance_km=null` y
`first_seen=2026-11-07T15:52:53.923509+00:00` (16:52:53 en Madrid). Es la fecha
de detección por el control, no la fecha de aparición del problema en el proveedor.

Se cotejaron los 17 códigos con los CSV actuales y con la copia
`docker-data/ha-coordinate-jump-20261104/Data/`:

- Las 17 ya tienen registros diarios con latitud y longitud vacías en el
  `Aemet_incremental.csv` de esa copia, y no figuran en su `estacions_aemet.csv`.
- Tampoco figuran en el catálogo ni en los CSV horarios actuales. El estado de
  diarios oficiales conserva nombre, provincia y altitud, pero no latitud/longitud.
- El backup `backfill_incrementals_20260924_212006/Aemet_incremental.csv` ya
  contiene Montserrat (`0158O`) y La Bisbal (`0294B`) sin coordenadas. Para las
  otras 15 se ha comprobado la copia del 4 de noviembre; no se ha establecido
  cuándo comenzaron a faltar sus coordenadas.
- `create_aemet.build_station_catalog` construye el catálogo desde las horarias
  y conserva las entradas existentes. `weather_official_backfill.normalize_aemet_climatology`
  toma latitud/longitud únicamente de ese catálogo. Por tanto, los registros
  diarios de estaciones ausentes del catálogo quedan sin posición.
- `weather_coordinates.Guard.observe` registra el caso sin posición como
  `unlocated`; el resumen lo suma bajo «excepciones activas» junto a los saltos.
  Hay que distinguir ambos casos al interpretar el log: aquí no hay un traslado
  propuesto que aceptar. Tampoco se ha comprobado que AEMET carezca de esas
  coordenadas en otros recursos de su API.

Diagnóstico de sólo lectura sobre datos y código, sin peticiones Google Maps ni
temporales. No se modifica el descargador, el estado de excepciones ni HA real.

### Contraste posterior con la API original, 07/11 a las 21:56

La inspección anterior de los CSV no permitía atribuir la ausencia de coordenadas
al proveedor. Se consultaron directamente, una vez cada uno, estos recursos:

- `https://opendata.aemet.es/opendata/api/observacion/convencional/todas`:
  HTTP/API 200, 10.641 filas de 856 estaciones. **15 de las 17 excepciones sí
  aparecen en la respuesta original**, con coordenadas: 195 filas en conjunto.
  Al pasarlas por `normalize_observations`, quedan cero filas. Las muestras
  impresas de cada uno de esos 15 códigos tienen `prec` ausente o nulo; el
  normalizador descarta cualquier fila sin precipitación numérica antes de
  conservar la metadata. Por eso tampoco llegan al catálogo construido después.
- `https://opendata.aemet.es/opendata/api/valores/climatologicos/inventarioestaciones/todasestaciones`:
  HTTP/API 200, 926 estaciones. **Las 17 tienen latitud y longitud en el
  inventario**, incluidas Montserrat (`0158O`) y La Bisbal (`0294B`), que no
  aparecen en la respuesta horaria de esta consulta. El inventario devuelve
  coordenadas en grados/minutos/segundos con hemisferio, por ejemplo Montserrat
  `413540N`, `015021E`.

La condición `not isinstance(rain, (int, float))` seguida de `continue` está tanto
en `HEAD:rainmapper_core/create_aemet.py:420` como en el worktree, línea 421.
Es una limitación previa del descargador, ahora visible por el control nuevo.
El diagnóstico correcto es que la metadata se obtiene demasiado tarde, después
del filtro de lluvia, y no se completa con el inventario climatológico. No debe
interpretarse como ausencia de coordenadas en AEMET.

Corrección identificada, aún no implementada: conservar metadata válida de la
respuesta horaria independientemente de la disponibilidad de precipitación, y
completar las estaciones que falten desde el inventario oficial mediante una
consulta conjunta reutilizable. Mantener el dato de lluvia ausente como ausente,
sin convertirlo en cero, y aplicar la protección de coordenadas también a la
metadata recuperada.

La comprobación hizo cuatro peticiones AEMET (índice y datos de cada recurso),
cero peticiones Google Maps, sin escribir archivos temporales ni modificar los
datos operativos. El inventario completo tardó 0,299 s en esta consulta local;
no es una medición de la RPi ni una garantía de latencia futura.

Consulta de precisión a las 21:59: se comprobó explícitamente la presencia de la
clave `prec`, además de su valor. En las 195 filas de esas 15 estaciones (13 por
estación) **la clave no existe**: cero valores nulos, textos o números. Por tanto,
«precipitación no numérica» describía la condición del código, pero no el dato
recibido: en esta respuesta la precipitación está ausente. Las otras dos estaciones
siguen ausentes de la respuesta horaria.

El estado local `Aemet_official_daily_state.json` contiene para esas 15 estaciones
28 días con temperaturas máximas/mínimas y datos de humedad, sin ningún campo
`Total` de precipitación. Montserrat y La Bisbal sí tienen `Total` numérico en 24
días del estado diario. Esto no permite afirmar que las otras 15 carezcan de
pluviómetro: sólo verifica qué datos tenemos en estas respuestas y en la caché
diaria actual. La consulta adicional hizo dos peticiones AEMET, sin guardar
temporales ni modificar datos operativos.

## Corrección AEMET y aceptación técnica local, 07/11 a las 22:15–22:19

Implementado en `create_aemet.py` y `aemet_station_inventory.py`:

- Se conservan observaciones con identificador/fecha válidos sin exigir lluvia.
  Coordenadas, temperatura, humedad y viento siguen disponibles. La lluvia
  ausente/inválida/negativa es nula, no cero; no se generan días de sólo metadata.
- En el solape horario, los campos ausentes conservan la medición previa; una
  corrección numérica explícita, incluido cero, tiene prioridad.
- El catálogo se completa sólo para ubicaciones que falten, con una consulta
  global de inventario. Se validan DMS, origen HTTPS, tamaño (512 KiB), cardinalidad
  (1.200 estaciones) y plazo total (30 s). No hay reintentos por estación.
- La evidencia original pasa por la protección de coordenadas. El inventario no
  reemplaza ubicaciones válidas del catálogo por sus coordenadas menos precisas.
- Un fallo de inventario conserva las mediciones y el catálogo existente,
  registra el resultado en el informe diario y deja la fuente `PARTIAL`.
- Se conserva el enriquecimiento Google habitual y su persistencia. Las fichas
  resueltas se reutilizan; la comarca vacía no fuerza llamadas nuevas.

Imagen local `sha256:0f183c847ef3fafb1be6476efa5aca31b79b8f15cb49d6973064ac97c42cdf5d`,
reconstruida y recreada desde `inicial`; entorno y montajes conservados, sin
reiniciar worker ni MCP. Paridad final de 14 archivos comprobada. Huellas efectivas:

- `create_aemet.py`: `ae48cd590fcd398615fab2434131e325326c7562762359349118bd092e19ddec`.
- `aemet_station_inventory.py`: `44668c4839d9b798997780930c412877edabdfcb220454de58961b3c64259a96`.

### Pruebas y alcance

- **59 tests dirigidos** pasan en host con `FutureWarning` tratado como error.
  Dentro de la imagen pasan **57**; las dos pruebas de API web usan la estructura
  del repositorio y se ejecutaron en host. Un primer intento de incluirlas dentro
  del paquete temporal falló por faltar esa ruta de pruebas, antes de hacer
  consultas reales. El paquete se eliminó y se corrigió el alcance del ensayo.
- La integración reproduce diarios ya archivados sin ubicación, recuperación
  horaria/inventario, caída del inventario, rechazo de coordenadas fuera de región,
  salto de ubicación y retorno, conservación de lluvia, segundo runner, cierre
  CSV, histórico Parquet y GeoJSON. Usa servicios externos simulados.
- **Dos ejecuciones reales completas de la fuente AEMET**, con copias temporales
  de los CSV y estados actuales, enriquecimiento Google desactivado e histórico
  pequeño aislado: **12,325 s** y **12,055 s**. Archivado/cierre posterior:
  **9,755 s** y **5,830 s**. Son tiempos locales; no representan la RPi ni el
  archivado de todo el histórico real.
- Resultado en ambas: 9.787 observaciones horarias, 25.984 filas diarias,
  **las 17 estaciones ubicadas en Parquet y GeoJSON**, cero excepciones AEMET.
  Conservadas las 848 ubicaciones del catálogo previo y **123.088 filas diarias
  ajenas a las claves actualizadas**. El inventario tarda 0,340 s la primera vez;
  la segunda no hace esa consulta (comprobación del catálogo: 0,005 s).
- El catálogo pasa de 848 a **891 estaciones**: 21 incorporaciones desde las
  horarias y 22 desde inventario. Son fichas ausentes del CSV de estaciones, no
  necesariamente estaciones nuevas en AEMET. De las 37 estaciones diarias
  ausentes de ese CSV, 20 ya tenían ubicación aceptada en el catálogo Parquet.
- Por ello se añadió una tercera descarga, **12,652 s**, con copia del catálogo
  Parquet real como referencia de ubicaciones aceptadas. También resuelve las
  17 excepciones, conserva las ubicaciones anteriores y no abre otras excepciones
  AEMET. Archivado aislado: 10,658 s. Google desactivado.
- **Google real limitado a Port Ainé y Montserrat**, usando respuestas AEMET
  reales ya descargadas: dos enriquecimientos la primera vez y cero la segunda.
  Cada enriquecimiento usa la función habitual de elevación y geocodificación
  inversa. Duraciones con archivo pequeño: 0,692 s y 0,114 s. No extrapolarlas al
  conjunto. El primer runner operativo puede completar metadata de las 43 fichas
  incorporadas; las 848 anteriores ya tenían municipio y provincia.
- La suite completa pasa: **2.191 tests, 55 omitidos, 132,545 s**. El primer
  intento dentro del sandbox falló en siete tests de sockets/procesos por permisos;
  se repitió fuera. Los demás checks del smoke pasaron; su chequeo final detectó
  un blanco al final de documentación, corregido y revalidado con `git diff
  --check` sin repetir pruebas ejecutables.

Las pruebas reales ejecutaron el mismo `run_update` que usa el runner, con el
alcance Google indicado, seguido del archivado normal sobre el directorio de
prueba. No se lanzó `all` ni se modificaron los CSV/estados operativos: hashes
comparados antes/después. Copias, fixtures e históricos de prueba eliminados.
La imagen habitual queda preparada para el runner del usuario. No se publicó ni
actualizó HA real, ni se hizo commit/push.

## Runner completo y aviso de tipos GeoJSON — 07/11, 22:29

El runner local lanzado por el usuario termina a las **22:29:04**, exit **0**, en
**3 min 9 s**. Publica siete GeoJSON y confirma **17 recuperaciones AEMET, cero
excepciones AEMET activas**. Meteocat y Wunderground tampoco tienen excepciones
de coordenadas; Roda de Ter sigue retenida en 41,99/2,32 frente a 49,99/2,32.

El aviso `DtypeWarning: Columns (11) have mixed types` corresponde a
`Ultima Lectura` de `01_Tomap_Last_day.csv`: 2.049 filas y 415 columnas, con 2.048
fechas textuales y una vacía al final, Meteocat ZD, la Tosa d'Alp (2.478 m).
La lectura de las primeras 2.048 filas no avisa; al incluir la última se reproduce
el aviso por inferencia de tipos entre bloques. La fecha ausente ya estaba
publicada como `null`; no se observó corrupción de lluvia ni de coordenadas.

`geojson.convert_file` ahora declara sólo esa columna como texto. Se añadió una
prueba de 2.049 filas y 415 columnas que fallaba antes con el aviso elevado a
error y comprueba después fechas, `null` y precipitación conservados.

- **22 pruebas dirigidas** de GeoJSON y coordenadas: correctas, 2,533 s.
- Imagen local reconstruida y recreada:
  `sha256:3eb225afa47a5da27deef74ffaaa3ad99726a1f70a6978cacf82b2ed6bd44c1d`.
  `geojson.py` efectivo:
  `f027750ddd048534af50e946beaaa87566ea334fb23c335f91eefcc6873769a3`.
  Los hashes efectivos de `create_aemet.py` y `aemet_station_inventory.py`
  siguen siendo los documentados en el apartado anterior.
- Conversión de los **siete CSV reales dentro de esa imagen**, en directorio
  temporal y con `DtypeWarning` elevado a error: **4,3 s**, sin ese aviso.
  Comparación exacta de todas las features con los GeoJSON publicados por el
  usuario: idénticas, incluidas coordenadas, propiedades y orden. Recuentos:
  2.040 / 2.097 / 2.107 / 2.130 / 2.134 / 2.153 / 2.155.
- Hashes de los siete CSV y siete GeoJSON publicados iguales antes/después;
  salida temporal eliminada. Sin descargas de fuentes ni llamadas Google.
- Entorno y montajes del contenedor conservados; worker y MCP no recreados.
  Interfaz local responde HTTP 200. Sin publicación ni actualización de HA real.

La suite completa anterior acredita el arreglo AEMET previo; después de este
cambio acotado se ejecutaron las pruebas dirigidas y la comparación real. El
usuario propone copiar otra vez `Data` de HA real para repetir el runner local.

## Runner desde la copia de HA y compatibilidad Pandas — 07/11, 22:37

El usuario volvió a copiar `Data` de HA real y lanzó `all`: **22:37:11–22:40:08**,
**2 min 57 s**, exit **0**, con la imagen `3eb225afa47a`. Tiempos por fuente:
AEMET **23,193 s**, Meteoclimatic **16,649 s**, Meteocat **5,956 s** y Wunderground
**88,498 s**. Archivado posterior: 29 s; Tomap: 6,5 s; GeoJSON: 4,4 s.

AEMET actualizó 23.217 filas oficiales de 28 fechas, dos fechas pendientes de
publicación y ningún bloque fallido. El inventario completó 22 ubicaciones,
cero pendientes. El catálogo persistido contiene 891 estaciones con municipio
y provincia; ejecutar sólo el enriquecimiento con un sustituto que rechaza
cualquier consulta demuestra **cero llamadas necesarias** y catálogo intacto.

Las 17 estaciones investigadas tienen posiciones coincidentes en
`estacions_aemet.csv`, el catálogo Parquet activo y `90d.geojson`. Se resolvió
`CURRENT.json` para identificar la generación `20261107T213943059930Z-d87bef171d89`
y se comprobó el hash de su catálogo
`stations-7b1771a1260a404bc6ea2cc6194dad024dd9da3e49c90ccc8da800408bc9485b.parquet`.
El fichero raíz legado `weather_stations_catalog.parquet` no representa esa
generación activa; no usarlo para evaluar el resultado actual.

Se publicaron siete GeoJSON sin `DtypeWarning`. AEMET, Meteocat y Wunderground
quedan sin excepciones; Roda de Ter permanece protegida. En esta ejecución no
se registraron eventos de recuperación AEMET, aunque las 17 posiciones finales
están verificadas. Las cuatro fuentes figuran `OK`; Wunderground todavía tiene
106 respuestas antiguas, 102 recuperaciones de datos más recientes mediante
compresión alternativa y tres estaciones fallidas: IBAG57, IFUENT4 e IMONTF44.
Esto no acredita que todas sus observaciones estén actualizadas.

### Corrección posterior del aviso Pandas

El runner mostró `FutureWarning` en la concatenación de `create_wunderground`
introducida para separar metadata nueva y cacheada. Se reprodujo con el recorrido
real de normalización, protección y escritura: cuando uno de los grupos está
vacío, conserva los tipos del CSV y se concatena con coordenadas ya numéricas.
El adaptador ahora procesa directamente el único grupo presente y concatena
sólo cuando los dos contienen filas, conservando el orden posterior.

La prueba descubrió además que una comarca completamente vacía puede llegar
como columna numérica y avisar al asignarle texto o `None`. La protección común
prepara como texto/nulos únicamente los campos geográficos no numéricos cuando
necesita reemplazarlos; las mediciones no cambian de tipo.

- Reproducción previa fallida con `FutureWarning` elevado a error; tras el ajuste
  pasan los casos de metadata toda nueva, toda cacheada y mixta, con salto y
  recuperación. Verifican lluvia, coordenadas, CSV y captura Parquet. Sólo la
  metadata nueva puede retirar la excepción. Otra prueba cubre topónimos
  aceptados sobre columnas vacías, conservando el dataframe original y la lluvia.
- **89 pruebas dirigidas**, correctas en 4,411 s. Se conservan avisos ajenos al
  caso en otras pruebas; no se han silenciado globalmente los avisos de Pandas.
- **Smoke completo correcto:** 2.194 tests, 55 omitidos, 132,511 s, exit 0;
  también correctos los checks de sintaxis, fixtures, versiones y whitespace.
- Imagen reconstruida y recreada:
  `sha256:63ad03aa9e289f327218182f3090183a7d17ea2f126ffb50383d33c47409003c`.
  Paridad de 14 archivos efectivos, entorno y montajes conservados, worker y
  MCP sin recrear. Huellas efectivas:
  `rainmapper.py` = `4f558c0e8df214ecbfa0a63f1bbde4247d285468d7794156fd95b8665332ab87`;
  `weather_coordinates.py` = `ed1ba088e56b3df4e4cdf4f85afa26310615848081ed991177a18fe8b211442d`.
- La integración anterior también pasa dentro de esa imagen en 0,145 s,
  ejecutando sus funciones efectivas. Pruebas sin consultas externas y con
  directorios temporales eliminados al terminar. No se repitió el runner
  operativo ni se tocó HA real. La candidata posterior al ajuste se valida con
  estas pruebas; el runner completo anterior corresponde a `3eb225afa47a`.

## Runner completo posterior al ajuste Pandas — 07/11, 22:48

El usuario lanzó `all` sobre la imagen `63ad03aa9e28`, comprobada en el contenedor:
**22:48:34–22:51:25**, **2 min 51 s**, exit **0**. El log no contiene `FutureWarning`,
`DtypeWarning` ni traceback. Cuatro fuentes `OK` y siete GeoJSON publicados.

Tiempos: AEMET **12,767 s**, Meteoclimatic **17,522 s**, Meteocat **6,231 s**,
Wunderground **103,568 s**. AEMET solicita **cero estaciones al inventario** y
mantiene 891 fichas con municipio y provincia completos; inventario y
enriquecimiento figuran como 0,0 s en el log. Tampoco hay líneas `Fetching altitude`.

Se verificaron otra vez las 17 posiciones AEMET en CSV, catálogo Parquet de la
generación activa `20261107T215100786839Z-9427f35f0981` (hash comprobado) y mapa de
90 días. Sin excepciones AEMET. Roda de Ter sigue en 41,99/2,32 y conserva su marca
de revisión en el GeoJSON.

Wunderground mantiene 106 respuestas antiguas, 102 recuperaciones mediante otra
compresión y los fallos de IBAG57, IFUENT4 e IMONTF44. Su estado global `OK` no
significa que todas las estaciones tengan lecturas actuales. Esta revisión fue
de lectura, sin nuevas descargas, temporales ni cambios de código; documentación
actualizada y comprobada con `git diff --check`. Sin publicación en HA real.
