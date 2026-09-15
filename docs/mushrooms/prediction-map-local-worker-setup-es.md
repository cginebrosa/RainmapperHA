# Mapa de predicción: volumen y aceptación HA local–worker

## Actualización vigente: caché privada integrada — 15/09/2026

El worker ya recibe referencias privadas y reutiliza objetos del Predictor, sin
montajes privados del Mac. HA conserva datos canónicos; solo publica pequeños
archivos modificados y reutiliza los hashes sellados de modelos/meteorología.
Seis consultas reales con paridad exacta después de reconstruir las imágenes.
[Funcionamiento, métricas, retención y límites](prediction-map-private-cache-es.md).
Las referencias siguientes a integración pendiente o montajes privados describen
la fase anterior del 14/09 y quedan sustituidas por esta aceptación local.

## Mapa unificado y permiso individual — 15/09/2026 (aplicado y validado localmente)

Decisión del usuario: en HA real el visor habitual incorporará la capa de
predicción. `/protected/maplibre/index.html` y el alias anterior
`/protected/prediction-map/index.html` sirven la misma composición del visor;
se conservan estaciones, meteorología y recursos compartidos.

`can_use_prediction_map` se guarda en la ficha de usuario, junto a Heatmap,
Métricas e IDW. Es explícito para **todos los roles**, incluidos administradores;
si falta, queda desactivado. La UI Usuarios permite activarlo o retirarlo.
La API exige la sesión existente y ese permiso en cada consulta: ningún bypass
por rol. El visor retira los controles cuando se refresca una sesión revocada.

No hay otro login ni otra persistencia: se reutilizan `/auth/*` y los ajustes
por dispositivo. Ejecutor, idioma y zona horaria siguen en esos ajustes;
retirar el permiso no los borra. La preview permanece aislada, sin auth real.

Validación: 13 pruebas de contrato/rutas, 343 de autenticación, navegador con
usuario básico autorizado, admin revocado, URL habitual, meteorología y
persistencia. Smoke completo: 1552 tests, 48 omitidos. Ambas imágenes reconstruidas
y contenedores recreados: 192 archivos HA y 100 worker coinciden con las fuentes.
Consulta real con usuario básico temporal: seis consultas local/worker, tres
especies con cálculo, paridad exacta, repetición/concurrencia/cancelación correctas.
Usuario y dispositivo temporales retirados; registros previos de usuarios iguales.
Coordinadores y volúmenes conservados. No publicado en HA real.
Informe: `docs/reports/prediction-map-user-permissions-2026-09-15.json`.

Prueba manual local: `http://127.0.0.1:8101/users` → usuario → **Prediction access**
→ **Save user**. Abrir/recargar `http://127.0.0.1:8101/protected/maplibre/index.html`
con la sesión habitual. No se ha activado automáticamente para usuarios existentes.

El puerto local sigue enlazado a `127.0.0.1:8101`; no es accesible directamente
desde iPhone. No exponer todo ese servidor a LAN: incluye administración local.
Si se habilita una prueba móvil local, limitarla al visor y API autenticadas.
Datos privados conectados a la caché por asociación y validados sin montajes
privados compartidos el 15/09; falta despliegue y puerta de aceptación de HA real.


## Base local consolidada — 15/09/2026

Los cambios del mapa y del editor descritos abajo ya están en las imágenes,
incluidos idiomas, ayuda, afinidades/AJAX, hover, colores, cabecera, canal online
y calendario. Las referencias históricas a copias puntuales pendientes de imagen
quedan superadas por esta construcción. Se mantienen dos mapas, sin sustituir
el meteorológico ni activar autenticación real en la preview.

Ambas imágenes se construyeron desde las mismas fuentes, se recrearon los
contenedores y se verificaron 192 archivos HA/100 worker dentro de imágenes y
contenedores. Smoke final: 1.551 tests, 48 omitidos, OK. Navegador y consultas
HA local–worker del 15/09 correctos, incluidas repetición/concurrencia/cancelación.
Datos y ambos coordinadores conservados. No se reinició durante los trabajos
que lanzó el usuario. [Informe y huellas](../reports/prediction-map-local-images-2026-09-15.json).

Etiquetas locales de esta base: `rainmapperha:local-base-20260915` y
`rainmapper-worker:local-base-20260915`. Código, configuración/JSON privados,
huellas y evidencia respaldados en `backups/local-base-20260915/`.
GIS, meteorología y modelos siguen en sus volúmenes; no se duplicaron sus GB.
Esto no autoriza publicación/instalación en HA real ni sustituye el circuito
local completo exigido antes de una release y su aceptación expresa.

Los wrappers `mushroom_lab_start.sh` y `mushroom_worker_start.sh` ahora incorporan
el overlay del mapa cuando existe su JSON local de configuración. Así los
arranques ordinarios conservan los montajes ya preparados. La construcción
explícita usada, sin lanzar el servicio runner, fue:

```bash
docker compose -f rainmapper-local/docker-compose.yml -f rainmapper-local/docker-compose.prediction-map-ha.yml build rainmapper-ha-ui
docker compose -f rainmapper-local/docker-compose.worker.yml -f rainmapper-local/docker-compose.prediction-map-worker.yml build rainmapper-worker
```

Después, con ambos carriles libres y las URLs preservadas, se recrearon solo
esos servicios con sus mismos overlays y `up -d --no-build --no-deps --force-recreate`.

## Calendario visible de la predicción — 15/09/2026

En el mapa, **Parámetros → Predicción → Zona horaria de la predicción** permite
seleccionar una zona IANA. Ayuda completa en ES/CA/EN. Se guarda al cerrar el
panel en `settings.prediction_timezone` del dispositivo, junto al ejecutor;
guardar parámetros desde el mapa meteorológico conserva ambos ajustes.

La zona seleccionada determina la fecha inicial y el «hoy» usado para limitar
la meteorología observada. No depende de la zona ni del idioma del navegador.
HA valida y transporta `calendar_timezone` en cada consulta online al worker;
el resultado devuelve la misma zona y el contrato rechaza discrepancias.
El popup la muestra debajo de la fecha. Los informes ya abiertos conservan la
zona con la que se calcularon; los cambios se aplican a nuevas consultas.

Sin preferencia guardada se usa el calendario anunciado por HA: en la instalación
local actual, `Europe/Madrid`. Para consumidores anteriores sin ese campo,
`calendar_timezone` del JSON del ejecutor sirve como valor predeterminado
(también `Europe/Madrid` si no existe). No hace falta editar JSON desde la UI.
La consulta explícita prevalece sobre la zona del contenedor y sus valores por
defecto. No modifica las fechas almacenadas en la meteorología ni su cobertura.

Incidencia resuelta: a las 00:10 del 15/09 en Madrid el worker seguía en día 14
UTC. `date.today()` rechazaba el corte 14/09 como no terminado y devolvía null
para toda la semana de especies que sí tenían modelo. El calendario explícito
permite ese corte; se sigue rechazando meteorología de hoy/futura. No se suprime
la abstención, no se inventan datos y no se requiere entrenamiento o precálculo
para resolver el desfase. La fecha seleccionada no sustituye al reloj real.

Pruebas: medianoche de verano/invierno, corte pasado admitido/futuro rechazado,
una preparación meteorológica para siete inferencias, zona de petición distinta
del ejecutor, validación IANA, respuesta ligada a petición y guardado por dispositivo.
Chrome con navegador Honolulu/mapa Kiritimati verifica fecha independiente,
zona visible, persistencia y aislamiento del mapa meteorológico.

Implementación y prueba del 14/09/2026. Alcance nacional conservado; este incremento
instala las dependencias **de los lectores actuales**, no acredita cobertura
ecológica nacional. GEODE y MFE fuera de Catalunya están descargados pero aún
requieren integración. No reducir territorio para presentar el paquete como completo.

## Instalación realizada

- `mushroom_map_volume.py` y `scripts/manage-prediction-map-volume.py` enumeran
  archivos desde índices/manifiestos existentes. No descargan ni regeneran GIS.
- Paquete público: 3.510 archivos, **14.538.214.301 bytes** lógicos. Generación
  `docker-media/rainmapper/prediction-map/generations/local-20260914/manifest.json`.
  Rutas relativas, tamaños, mtime en nanosegundos y SHA256. Se conservan los
  nombres relativos que necesitan los índices forestal, DEM y pH.
- Instalación local mediante enlaces duros: **cero bytes copiados**, archivos
  públicos compartidos en el mismo disco. Montajes de contenedores en solo lectura.
  No modificar esta generación ni sus originales enlazados en el sitio: una
  nueva edición necesita otra generación. El chequeo de tamaño/mtime detecta cambios.
- Se verifican hashes una vez al instalar. Segunda ejecución: cero transferencia
  y cero hashes completos; comprueba el recibo y metadatos. El modo copia permite
  un destino físico separado, probado con fixtures; no se ha duplicado aquí todo
  el volumen nacional para demostrarlo.
- El instalador rechaza rutas que escapen del volumen, manifiestos excesivos,
  hashes incorrectos y generaciones existentes distintas. Publica el recibo al
  terminar; conserva staging de un fallo para reanudar. No cambia una generación
  activa, no borra datos anteriores ni edita coordenadas/coordinadores.
- Perfiles, catálogos, mappings, modelos y meteorología son montajes privados
  separados de la asociación con HA local. No entran en el paquete público.
  Configuraciones en `docker-data/prediction-map/{local,worker}.json`; sin rutas
  del Mac dentro del JSON, sin credenciales. Worker seleccionado por su ID de
  asociación existente; no se añade ni sustituye coordinador.

**Qué sucederá con HA real:** este volumen no reemplaza `docker-data` ni los
datos de la RPi4. La prueba actual comparte mediante montajes privados de solo
lectura los JSON/meteorología locales y modelos de `docker-media`. En producción,
HA real seguirá siendo autoridad y el worker necesitará las generaciones privadas
de esa asociación, recibidas por el circuito de sincronización correspondiente.
La configuración del mapa solo está activada para HA local; no se ha conectado
al runtime privado de HA real. Integrar/reutilizar esa sincronización y comprobar
identidades coherentes de perfiles, modelos y meteorología sigue pendiente antes
de anunciarlo operativo con RPi4. Nunca usar la copia del Mac como sustitución
implícita de datos reales ni mezclar asociaciones. La cartografía pública sí
puede compartirse por identidad entre asociaciones del mismo worker.

## Sincronización privada y caché: requisito acordado, integración pendiente

**Histórico del 14/09. Integrado y validado localmente el 15/09** en
[la actualización de caché privada](prediction-map-private-cache-es.md).

El usuario confirma el 14/09 que una predicción debe aprovechar la meteorología
ya disponible por un precálculo y las fichas ya sincronizadas si no han cambiado
en HA. La RPi4 sigue siendo autoridad; el worker calcula. No descargar el histórico,
las fichas ni los modelos completos en cada clic.

**Base existente comprobada en código:**

- `rainmapper_core/mushroom_predictor_runtime.py`, `build_manifest`: el runtime
  incluye perfiles, modelos y meteorología. En el formato particionado referencia
  el catálogo y los objetos de las particiones de la generación. No incluye aún
  los catálogos de referencia y mappings específicos que necesita el mapa.
- `synchronize_runtime` reutiliza una generación con recibo válido sin descargar
  objetos ni recalcular sus hashes. Entre generaciones reutiliza archivos iguales
  por manifiesto y objetos por contenido; solo descarga los ausentes. La unidad
  actual de transferencia es el archivo/partición, no un parche de filas.
- `load_published_manifest_metadata` permite consultar la identidad publicada sin
  inspeccionar ni volver a hashear los archivos fuente en HA.
- `rainmapper_core/mushroom_worker_service.py`, `download_predictor_runtime`:
  mantiene runtimes lógicos por asociación y un almacén físico compartido de
  objetos. Actualmente obtiene el manifiesto completo si el job no lo aporta;
  cero bytes de objetos no significa cero bytes de control/manifiesto.
  Su endpoint exige autorización del job científico: el mapa necesita una
  integración autorizada propia, no fabricar ni reutilizar claims incompatibles.
- El mapa local lee rutas montadas y todavía no fija una referencia privada
  publicada en su solicitud. La paridad con esos montajes no valida sincronización
  RPi4–worker ni demuestra un clic sin transporte de datos.

**Contrato a implementar reutilizando esa base:**

1. HA entrega punto, fecha/horizonte y referencias compactas de los datos aprobados
   para su asociación. Si el worker ya tiene esas versiones verificadas, el clic
   no transfiere objetos ni el manifiesto completo, ni reconstruye TARs o hashes.
2. Si falta una versión, resolver metadatos y traer solo archivos/particiones
   ausentes o cambiados. Editar fichas/catálogos/mappings no debe provocar otra
   descarga de meteorología o modelos iguales. Separar sus identidades y la
   cartografía pública; no añadir GIS al bundle privado de cada consulta.
3. Reutilizar los datos del precálculo cuando coincidan identidad, corte y cobertura
   exigidos. Haber realizado un precálculo no prueba por sí solo que el worker
   tenga la última edición de HA. Su probabilidad agregada por área tampoco
   sustituye el cálculo de un punto arbitrario.
4. Preparar actualizaciones al publicarse cuando sea posible, fuera del clic.
   Si falta preparación al consultar, exponer espera/disponibilidad; no usar datos
   antiguos silenciosamente ni ejecutar el cálculo en RPi4 como fallback.
5. Fijar versiones coherentes durante toda la consulta; impedir que una limpieza
   retire archivos en uso y agrupar sincronizaciones simultáneas idénticas. Un
   hash coincidente no concede acceso: conservar autorización por asociación,
   aunque el almacén físico deduplique objetos. Preservar URLs y ediciones de HA.

**Aceptación pendiente del mapa:** repetición tras precálculo con cero objetos
transferidos; cambio de una ficha con transferencia solo del archivo afectado y
metadatos necesarios; nueva meteorología con descarga solo de particiones nuevas
o modificadas; modelos intactos sin descarga; reinicio con reutilización del recibo;
reparación acotada de un objeto inválido; sincronización concurrente única;
aislamiento de asociaciones y consulta coherente durante un cambio de generación.
Medir por separado bytes de control/manifiesto y objetos, preparación, cola y
cálculo, tanto en frío como con caché disponible. Evitar materializar payloads
grandes en HA para medirlos: comprobar límites antes de construirlos/encolarlos.

**Verificación de la base, 14/09:** cuatro pruebas dirigidas actuales de
`tests/test_mushroom_predictor_runtime.py` (`PredictorRuntimeTests`) pasan:
`test_reused_runtime_receipt_does_not_rehash_installed_files`,
`test_changed_runtime_reuses_unchanged_sealed_files_by_manifest`,
`test_runtime_reuses_worker_produced_objects_by_digest` y
`test_published_metadata_load_does_not_inspect_runtime_sources`.
Son fixtures del runtime existente, no aceptación de transporte del mapa.
Esta revisión solo documenta el siguiente contrato; no modifica código ejecutable,
no sincroniza HA real ni lanza entrenamiento, precálculo o descargas.

## Tamaño del paquete público actual

| Familia | GB decimales aproximados |
|---|---:|
| DEM Catalunya 5 m | 5,13 |
| DEM nacional 25 m | 4,59 |
| Cubiertas ICGC y auxiliar | 1,72 |
| MFE Catalunya e índice | 1,64 |
| SoilGrids | 0,60 |
| OpenLandMap pH | 0,38 |
| Geología ICGC | 0,29 |
| DEM Francia/Andorra, municipios, índices y documentación | 0,20 |

Estos 14,54 GB no contienen GEODE ni el MFE de las otras comunidades. No confundir
una generación portable con la finalización del mapa nacional. Tampoco sumar
sin más ZIP/originales a un supuesto tamaño operativo aún no preparado.

## Reproducción y persistencia local

### Edición de las reglas de suelo y pH

Actualización 14/09: Ecología → Suelos muestra la regla completa en V0 y Enriched.
Se distinguen afinidades antiguas de la regla operativa del mapa. Campos expuestos:

| Campo de ficha | Control |
|---|---|
| `ecology.soil_filter.require_soil_context` | Exigir tipo de suelo identificado |
| `accepted_soil_ids` | Suelos de apoyo, lista no exhaustiva |
| `conditional_soil_ids` | Suelos con admisión condicionada al pH |
| `excluded_soil_ids` | Suelos excluidos explícitamente |
| `ph_override_blocked_soil_ids` | Suelos que bloquean la excepción de pH |
| `ph_conflict` | No admitir excepciones / admitir solapamiento con suelo de apoyo |
| `review_ref` | Referencia que justifica la regla |
| `metadata.map_display_name` | Nombre en el mapa, en Metadatos |

Los seis campos abreviados de la tabla pertenecen también a `ecology.soil_filter`.
Hay un selector adicional de activación: desactivarlo elimina solo ese bloque
al guardar; sin regla se conservan los demás filtros. Abrir el editor no altera
datos. Las opciones de suelo proceden del catálogo local, no de semillas ni de
una lista de tipos hardcoded. Nombre del mapa vacío recupera el nombre común.
El POST conserva campos ausentes y usa `validate_soil_filter` con el catálogo
local antes del guardado con backup habitual. IDs inexistentes, solapamientos de
exclusión/apoyo o condicionados, modo inválido y referencia vacía se rechazan.

Revisión acotada a campos que consume el mapa: se detectaron estos siete del
bloque y el nombre de mapa; pH, hospedadores/hábitat, meses y altitud ya tenían
controles. No equivale a una auditoría de editabilidad de todo el esquema histórico.

Cuatro tests dirigidos de `AuthDeviceLimitTests` pasan: controles de suelo en
ambas vistas, guardado/validación/conservación de datos y las dos regresiones de
edición de pH. Nuevas pruebas usan copias temporales de datos/catálogos locales.
HTTP en 8101 y navegador de solo lectura correctos en 1600 y 390 px, capturas:
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/soil-controls-browser-N0RAwx/`.
Perfiles, catálogo, mappings y observaciones locales sin cambios de hash;
`require_soil_context` de aereus permanece `true`, decisión de cambio del usuario.

Se copiaron `web_server.py`, `mushroom_profiles_ui.py` y `mushroom_labels.json`
al contenedor y se reinició solo HA local. Backups previos bajo `/private/tmp/`:
`web-server-before-soil-controls.py`, `profiles-ui-before-soil-controls.py`,
`labels-before-soil-controls.json`. Como los ajustes visuales que siguen, estos
cambios aún no están incorporados a la imagen. No se modificó el worker ni HA real.

**Último ajuste, gráfica semanal, 14/09:** cabecera fija con curvas después del
selector de fecha, basadas en los siete días del resultado existente. Solo series
de las especies visibles y en temporada; colores asignados por identidad antes
de ordenar la lista. Cada fila con valores muestra el máximo semanal y primera
fecha del pico. Cero es válido; valores nulos interrumpen la línea sin unir sus
extremos, y especies sin cálculo no muestran curvas/máximos inventados. Pulsar
la gráfica selecciona el día, igual que el selector, sin nueva consulta.
Etiquetas ES/CA/EN en `mushroom-data/mushroom_labels.json`; sin cambios científicos.

`prediction_map_browser_check.mjs` pasa (17 peticiones de fixture): colores
constantes al reordenar, correspondencia curva/fila, máximo/fecha, huecos, cero,
sin modelo, filtro temporal, interacción de fecha y cabecera fija en ambos tamaños.
Capturas de gráfico escritorio/móvil en
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-dHibrF/`.
Recursos copiados al contenedor y **reiniciado solo HA local** para cargar las
nuevas traducciones; API autenticada tras reinicio: `worker_ready: true`.
Fuente y respuestas HTTP de 8101 coinciden:

| Recurso | SHA256 actual |
|---|---|
| `prediction-mode.js` | `e4ebf45c3b7022898f2433e855274bcac82ab305445c1aa6e987902d0847f772` |
| `prediction-mode.css` | `8aab1986c5d45f50acba8a0a5f63f1d4f4fd36d4e7733afa0fb5b6d32b55fb23` |
| `prediction-bootstrap.js` | `8199197d5d161ae149219265b9d62525984efc8658e95571bdda0b3dbe43a57f` |

Backups anteriores: `/private/tmp/prediction-map-before-weekly-chart` y
`/private/tmp/mushroom-labels-before-weekly-chart.json`. Las imágenes todavía
no incluyen estos recursos: persisten al reiniciar, no al recrear desde la imagen
anterior. Incorporarlos en la siguiente construcción local autorizada.
No se reinició el worker ni se alteraron datos privados o HA real.

**Último ajuste, cabecera fija del popup, 14/09:** el bloque hasta la fecha
inclusive está separado del contenedor desplazable de especies/avisos/detalles.
En mapas estrechos se desplaza el encuadre solo si el espacio vertical disponible
es menor que el objetivo de 500 px (limitado por la propia altura del mapa).
El punto consultado no cambia. La zona de resultados permite foco y scroll por
teclado; mover su scroll no desplaza el cierre ni la fecha.
Prueba actual `prediction_map_browser_check.mjs` correcta en escritorio/móvil,
con cabecera inmóvil, selector visible, cuerpo desplazable y selección de fechas
funcional. Capturas en
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-wUcPor/`.

Recursos copiados a HA local sin build/reinicio y verificados por respuesta HTTP
en 8101; estas huellas sustituyen la del ajuste anterior:

| Recurso | SHA256 del fuente y del recurso servido |
|---|---|
| `prediction-mode.js` | `94d455a9b7302900cc8427d65ec9f817be8a9149f618689895deb29a39b78a6e` |
| `prediction-mode.css` | `d3964f80f90e961268b69ab05eb287523fd9ba26948efd7ea0f4530953364d89` |
| `prediction-bootstrap.js` | `e17e58edfa91bb55c8ef8a6c72f4e6194ba962092092575fe5387962d4b666cc` |

Backup anterior en `/private/tmp/prediction-map-before-fixed-header`.
**La imagen no incorpora estos tres cambios todavía:** recrear desde ella pierde
los ajustes visuales. Incorporarlos en la siguiente construcción local autorizada.
Sin cambios en autenticación de preview, datos, cálculo, worker o HA real.

**Ajuste posterior de popup, 14/09:** aplicado en el código fuente y copiado al
contenedor HA local, sin reconstruir imagen ni reiniciar servicios. El archivo
`rainmapper_core/viewers/prediction-map/prediction-bootstrap.js` servido por HTTP
en el puerto 8101 coincide con el fuente:
`057f154a2148bff75c0a63054d47e7e3dd1e8ff2a9f2ef7a22292f63ba6dcc62`.
La imagen local todavía lleva la edición anterior de ese recurso: recrear el
contenedor desde ella pierde este ajuste. Incorporarlo en la próxima construcción
local autorizada; no considerar la imagen actual validada con el cambio visual.
Backup del recurso anterior: `/private/tmp/prediction-bootstrap-before-height-fix.js`.

Popup lateral desplazado dentro del mapa, flecha conservada en el punto y altura
de escritorio ligada al espacio disponible (sin el tope de 650 px con ancho
≥900 px). `tests/prediction_map_browser_check.mjs` pasa con MapLibre 4.7.1 local:
cuatro puntos próximos a bordes superiores/inferiores a ambos lados verifican
contenedor dentro del mapa, altura >650 px, flecha con error <2 px y cabecera sin
scroll inicial. También pasan móvil y regresión de la ruta meteorológica.
Evidencia visual de esta ejecución en
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-00dxrn/popup-desktop-edge.png`.
No se cambió cálculo, transporte, datos privados, autenticación ni worker.

Desde la raíz del repositorio, se superponen los archivos de configuración
explícitos a los Compose existentes. **Seleccionar solo estos servicios**, nunca
el runner meteorológico. Conservar el volumen `rainmapper-worker-data`.

```bash
docker compose -f rainmapper-local/docker-compose.yml -f rainmapper-local/docker-compose.prediction-map-ha.yml up -d --no-deps --no-build rainmapper-ha-ui
docker compose -f rainmapper-local/docker-compose.worker.yml -f rainmapper-local/docker-compose.prediction-map-worker.yml up -d --no-deps --no-build rainmapper-worker
```

Los overlays conservan montajes, identidad y URL del worker. `RAINMAPPER_MAP_VOLUME`
permite seleccionar otra generación preparada. Un `docker restart` conserva la
configuración; recrear con el Compose base sin overlay retira la configuración
del mapa de ese contenedor. No modifica sus datos persistidos.

Para preparar otro paquete, usar `plan` con un JSON administrativo del ejecutor,
raíz de fuentes y manifiesto de salida nuevo. Después `install` toma ese manifiesto,
la raíz de fuentes y un destino nuevo. Para transportar una generación sellada,
su `manifest.json` y su propia raíz sirven como origen de instalación, sin rutas
del Mac. `--link` solo cuando origen/destino comparten disco; fuera de ese caso
usar copia. Nunca apuntar a datos privados como si fueran cartografía pública.

En esta entrega las imágenes locales HA y worker se construyeron desde el mismo
código, para `linux/arm64`; once archivos de cálculo/contratos/lectores coinciden
por hash con el checkout dentro de ambos contenedores. No se validó AMD64 ni
instalación en una segunda máquina. No hubo publicación o cambio de versión HA.

## Aceptación realizada y límites

Prueba HTTP dentro de HA local, usando su autenticación normal con una sesión
temporal de prueba retirada al terminar. Worker existente con su token/asociación
persistidos. Script reproducible: `tests/prediction_map_container_check.py`,
solo para ejecución explícita dentro del contenedor HA local, nunca HA real.
No modifica contraseñas ni usa la autenticación ficticia de la preview.

- La Vansa y Montclar: mismas especies, probabilidades, abstenciones, suelo,
  meteorología y procedencia en los dos ejecutores; solo se excluyen de la
  comparación IDs de petición y métricas de tiempo/caché.
- Repetición y una consulta por ejecutor a la vez correctas; cancelación de
  entrega correcta. No se afirma interrupción instantánea de una inferencia.
- API sin sesión: 401; coordenadas inválidas: 400. Worker detenido: 503, sin
  fallback local. Worker arrancado de nuevo y recuperación comprobada.
- Disponibilidad exige los lectores geográficos configurados, meteorología y
  metadatos del modelo; no basta con abrir el índice de altitud. Capabilities
  identifica `prediction` cuando el ejecutor local tiene motor configurado.
- Ventanas temporales, filtro antes del modelo y null/0 conservados. Un modelo
  disponible puede abstenerse: no exigir probabilidad numérica a todas sus filas.

Última ejecución de La Vansa: primera consulta HA local **1,85 s total / 1,71 s
cálculo**, worker **2,05 / 1,79 s**. Repetida: HA local **1,45 / 1,25 s**,
worker **1,87 / 1,28 s**. Montclar concurrente: HA **2,68 / 2,59 s**, worker
**3,30 / 2,44 s**. Respuestas entre 23.879 y 25.644 bytes. Son pocas muestras en
el mismo Mac, con sondeo cada 0,2 s; no p50/p95, benchmark de RPi4 ni tiempo de render.

Memoria cgroup máxima desde recreación: HA local 778.915.840 bytes y worker
576.188.416 bytes. Incluye servicios completos y caché de páginas; no equivale a
RAM incremental por consulta. `io.stat` vacío no acredita cero lectura de los
montajes Docker del Mac; queda pendiente medir IO físico en el destino.

118 pruebas dirigidas: la única bloqueada por socket del sandbox pasó al
reejecutarla fuera. Tras el último ajuste, 19 pruebas de volumen/disponibilidad/API
correctas. No se repite revisión visual: Safari/iPhone y revisión a fondo aplazados
por el usuario, junto con árboles vecinos.

**RPi4: cálculo en el worker en principio**, sin fallback local. HA conserva
interfaz, permisos, coordinación y entrega. La configuración que activa cálculo
local aquí es de comparación; no trasladarla automáticamente a la RPi4. No es
necesario replicar allí este volumen completo para delegar las consultas del mapa.

Catálogo y mappings mantienen hashes v5. Perfiles conservan una edición posterior
de la UI, anterior a preparar este volumen: salmonicolor/quieticolor con
`host_abies_spp`. No restaurar el backup ni las cinco afinidades antiguas. Las
pruebas usan los perfiles actuales. URLs y credenciales de ambos coordinadores
idénticas por hash antes/después. Sin entrenamiento, precálculo, runner, promoción
de datos o publicación HA real. Preview 65517 conserva su sesión ficticia.

[Resultados, huellas y métricas](../reports/prediction-map-local-worker-integration-2026-09-14.json).

## Nombres de hospedadores por idioma, 14/09

El catálogo local ya contiene ES/CA/EN para los 115 hospedadores. Se corrige
`mushroom_map_forest.py` para devolver `labels` por idioma (tres cadenas de hasta
128 caracteres), conservando `label` español/científico para consumidores previos.
`prediction-mode.js` selecciona el idioma actual; sin traducción usa el científico,
y acepta respuestas antiguas con solo `label`. No hay equivalencias nuevas ni
cambios de perfiles, catálogo, mappings o filtrado ecológico. Las ediciones de
nombres refrescan el vocabulario sin invalidar la geometría.

Validación: 13 pruebas `test_mushroom_map_forest.py` pasan con `/usr/bin/python3`
y GDAL del worker, en `/tmp/host-label-check`, sin modificar datos geográficos.
La venv anfitriona omite estas pruebas por no tener GDAL; no cuenta como validación.
Prueba `prediction_map_browser_check.mjs` correcta (17 consultas de fixture),
incluido ES→EN→CA→ES, texto literal, fallback científico y respuestas antiguas;
cambiar idioma no genera consultas. Capturas en `prediction-map-browser-TUbMAZ`.
Lectura geográfica real del punto 41.98967, 1.90060: Encina/Alzina/Holm oak,
Roble pubescente/Roure martinenc/Downy oak, Madroño/Arboç/Strawberry tree.
Bloque forestal completo de ese punto: 743 bytes JSON UTF-8.

Aplicados los archivos en HA local y worker existente mediante copia con backups
en `/private/tmp/*before-localized-hosts*`. Reiniciados con worker idle en ambos
carriles. Las configuraciones de sus dos coordinadores conservaron exactamente
sus hashes y URLs. Verificados código efectivo de ambos contenedores y JS HTTP:

- Lector forestal: `6e0274e5537df4728780799dd4e374d62676003dc4a7dd6c6d7bd534395504c8`.
- JS: `dcf746cb2216a9ef5046fdb56e9fc2f5badd7420d479db6c403bb4e2b64fc042`.

No se han reconstruido imágenes ni publicado HA. Una recreación con las imágenes
anteriores perdería estas copias: incorporarlas en la siguiente construcción
autorizada. Recargar el visor y consultar de nuevo para recibir los nombres nuevos.

## Canal online del mapa y disponibilidad, 14/09

El usuario exige que el mapa comparta online/foreground y pueda calcular mientras
background ejecuta precálculo. El antiguo `busy` global detenía los sondeos al
coordinador con cualquier trabajo activo y su presencia caducaba a los 15 s.
Se reemplaza por una reserva global de foreground compartida entre reclamación
y ejecución de trabajos normales y consultas del mapa. Un único cálculo online
global, además del background existente; no se crean carriles por coordinador.
La reserva se libera si no hay trabajo, si falla transporte/cálculo y al finalizar.

Mientras online está ocupado, el mapa envía `action=busy` autenticada, sin
reclamar consultas. El broker distingue `worker_busy` de `executor_unavailable`;
no acepta trabajo en ese momento ni aplica fallback local. El aviso se traduce
a ES/CA/EN. Un coordinador anterior rechaza esa acción sin reclamar trabajo.
También se corrige el aviso inicial del visor: usa `data_mode` de capacidades,
sin presentar una predicción real como simulación por no tener aún resultado.

Diagnóstico observado: el precálculo `worker_job_UbGvg0cuhtud` pertenecía a
`primary`, no a HA local. Terminó y liberó background a 19:04:10 UTC. La tarjeta
de worker resumía solo foreground como idle; mejora de ambos estados en TODO.

Validación final: 23 pruebas dirigidas de consultas, API y servicio con dos
coordinadores; foreground y background simultáneos, mapa respeta reserva online,
errores liberan reserva. Son fixtures sin entrenamiento/precálculo real.
Navegador: 18 consultas fixture, ocupado distinguido y aviso inicial correcto.
Tras aplicar copias, consulta autenticada HA local→worker correcta en
41.98967, 1.90060: 1277,742 ms, 7 especies, modo prediction. Sesión temporal
retirada al terminar. No se inició ni canceló ningún trabajo científico real.

Huellas finales ejecutadas y cotejadas:

- `mushroom_map_worker.py`: `d701bf05419d95b4dbf5ef7a63850940832fb16233ce9187d60a2c545f54e221`.
- `mushroom_worker_service.py`: `0280c549c999b7742fbc0c17a31d661cb0f356b367c7b6de4f99e9014ff2ea3f`.

HA local y worker actualizados por copia, con backups en `/private/tmp`; worker
reiniciado solo tras verificar ambos carriles libres y configuraciones de sus
dos coordinadores idénticas antes/después. Sin build/publicación; incorporar
en próximas imágenes autorizadas. HA real no se ha actualizado.
