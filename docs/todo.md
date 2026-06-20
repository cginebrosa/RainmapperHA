# TODO

## Proximo paso recomendado
Revisar la ergonomia del panel Settings de MapLibre en movil o ampliar tests funcionales formales, segun se quiera priorizar UX o cobertura automatica.

## Prioridad alta
- [x] Corregir upsert de historicos incrementales por estacion/dia
  - Contexto: los incrementales no son append puro; las fuentes pueden reenviar una estacion/dia con valores corregidos o campos complementarios incompletos. El patron anterior `update` + `merge` por todas las columnas podia dejar duplicados logicos si la fila nueva traia `NaN`.
  - Ficheros relacionados: `incremental_upsert.py`, `Rainmapper.py`, `rainmapper-app/app/Rainmapper.py`, `tests/test_incremental_upsert.py`.
  - Criterio de aceptacion: una sola fila por `Codi Estació` + `Data Local`; valores nuevos no nulos mandan; `NaN` nuevo conserva valor antiguo no nulo.
  - Estado: resuelto y validado localmente con datos copiados de HA. Meteocat paso de 28 filas duplicadas a 0; Meteoclimatic y Wunderground se mantuvieron sin duplicados. `local_update.sh`, `MODE=maps`, unit tests y smoke test pasaron. Validado tambien en HA `0.2.77`: `Run update` termino con exit code 0, Meteocat quedo en 316685 filas y `Generate maps` publico correctamente `v=0.2.77`.

- [x] Corregir inconsistencia de version en la app HA
  - Contexto: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y `rainmapper-app/CHANGELOG.md` deben avanzar juntos en cada bump de version.
  - Ficheros relacionados: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: version alineada en metadata HA, labels Docker y changelog.
  - Estado: resuelto.

- [x] Validar MapLibre en movil tras los ultimos ajustes
  - Contexto: MapLibre funciona bien en movil segun validacion manual/reportada por el usuario; se mantiene publicado junto a Leaflet de momento. La `0.2.47` anade capas raster Hybrid/Topographic y requiere validacion visual especifica.
  - Ficheros relacionados: `maplibre-viewer/`, `rainmapper-app/app/maplibre-viewer/`.
  - Criterio de aceptacion: cambio de capa mantiene estaciones, cambio de periodo conserva vista, popup es usable y no desplaza/molesta.
  - Estado: validado manualmente por el usuario en movil; pendiente de confirmacion automatizada.

- [x] Validar MapLibre raster y Leaflet fallback en HA/iPhone
  - Contexto: MapLibre `0.2.53` incorpora Satellite+ como base por defecto, Hybrid raster, Topographic raster y estilos vectoriales; Leaflet se mantiene como fallback con Topographic/Hybrid.
  - Ficheros relacionados: `maplibre-viewer/`, `rainmapper-app/app/maplibre-viewer/`.
  - Criterio de aceptacion: Hybrid, Topographic y Satellite+ cargan correctamente, el cambio entre capas conserva marcadores, periodo, vista y popup en movil.
  - Estado: validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada. Leaflet queda como fallback publicado.
  - Riesgo si no se hace: decidir retirada de Leaflet sin confirmar que MapLibre cubre bien las capas raster que interesan.

- [x] Mantener sincronizadas raiz y app HA
  - Contexto: hay copias de scripts y visores en raiz y dentro de `rainmapper-app/app`.
  - Ficheros relacionados: `Rainmapper.py`, `Rainmapper_Client.py`, `tomap_to_geojson.py`, `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/app/`, `scripts/sync-app-files.sh`, `scripts/smoke-test.sh`.
  - Criterio de aceptacion: despues de cada cambio funcional, raiz y app contienen la misma version necesaria.
  - Estado: resuelto como practica operativa: usar `./scripts/sync-app-files.sh` para copiar raiz -> app HA y `./scripts/smoke-test.sh` para verificar sincronizacion.
  - Riesgo si no se hace: Docker local funciona pero HA no, o al reves.

- [x] Proteger el historico CSV antes de cambios de pandas
  - Contexto: `Data/*_incremental.csv` es el valor principal del proyecto.
  - Ficheros relacionados: `Rainmapper.py`, `Data/`, `/share/rainmapper/Data`, `scripts/backup-data.sh`, `scripts/check-history.py`, `docs/history-safety.md`.
  - Criterio de aceptacion: backup o prueba en directorio temporal antes de cambios que escriban historicos.
  - Estado: resuelto como practica operativa versionada. Antes de cambios que escriban CSV, usar backup/copia temporal y validar con `scripts/check-history.py`.

## Prioridad media
- [x] Decidir visor principal
  - Contexto: conviven Bokeh, Leaflet y MapLibre; MapLibre ya funciona bien en movil segun validacion manual/reportada por el usuario y desde `0.2.47` tambien soporta Hybrid/Topographic raster.
  - Ficheros relacionados: `Rainmapper_Client.py`, `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/app/web_server.py`.
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
  - Ficheros relacionados: `Rainmapper.py`, `rainmapper-app/app/Rainmapper.py`, `web_server.py`, `rainmapper-app/README.md`, `rainmapper-app/DOCS.md`.
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
  - Ficheros relacionados: `maplibre-viewer/`, `rainmapper-app/app/maplibre-viewer/`, `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: en HA/iPhone el slider filtra estaciones del periodo actual, conserva cambio de periodo/capa y no bloquea popups ni lectura del mapa.
  - Estado: validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada. El slider filtra sin romper cambio de periodo/capa ni popups segun esa validacion.

- [x] Validar vuelta a Satellite+ en MapLibre
  - Contexto: en `0.2.55`, despues de cambiar desde Satellite+ a otra capa, volver a Satellite+ no refrescaba la capa y quedaba la anterior.
  - Ficheros relacionados: `maplibre-viewer/app.js`, `maplibre-viewer/index.html`, `rainmapper-app/app/maplibre-viewer/`.
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
  - Ficheros relacionados: `maplibre-viewer/`, `rainmapper-app/app/maplibre-viewer/`.
  - Criterio de aceptacion: confirmar en local/HA/iPhone que activar 3D terrain funciona sobre Satellite+, Hybrid, Topographic y Liberty sin romper filtros, cambio de periodo, cambio de capa ni popups.
  - Estado: completado por decision del usuario el 2026-06-18; validado manualmente en local, HA, Mac e iPhone y queda como funcionalidad definitiva. En `0.2.77` se anade boton compacto `2D`/`3D` bajo `Generated`, atajo `t`, cola para el popup de altitud y cierre correcto sin bloquear hover. Riesgo aceptado: sigue dependiendo del DEM externo Terrarium/Mapzen hasta que se decida si hace falta DEM propio.

- [ ] Revisar ergonomia del panel Settings de MapLibre en movil
  - Contexto: al anadir badges de estado por fuente, el panel Settings necesita mas ancho. El ajuste actual evita solapes y funciona en iPhone, pero puede sentirse algo ancho.
  - Ficheros relacionados: `maplibre-viewer/style.css`, `rainmapper-app/app/maplibre-viewer/style.css`.
  - Criterio de aceptacion: tras usarlo en movil, decidir si se mantiene el ancho actual, se compactan los badges o se cambia Settings a un panel tipo drawer/bottom sheet.
  - Riesgo si no se hace: el panel sigue siendo funcional, pero podria ocupar demasiado mapa en pantallas pequenas.

- [x] Crear smoke tests automatizados
  - Contexto: no hay framework de tests completo, pero existe `scripts/smoke-test.sh`.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `README.md`, `docs/architecture.md`, `docs/codex-handoff.md`.
  - Criterio de aceptacion: comando unico que valide sintaxis Python, JS, conversion GeoJSON minima y wrappers shell.
  - Estado: resuelto con smoke test de sintaxis Python/JS/shell, conversion GeoJSON minima, version HA, sincronizacion raiz/app HA y whitespace Git.

- [x] Crear fixtures funcionales iniciales para GeoJSON
  - Contexto: Leaflet y MapLibre dependen de GeoJSON generado desde `Tomap`.
  - Ficheros relacionados: `tests/fixtures/`, `tests/test_tomap_to_geojson.py`, `tomap_to_geojson.py`, `scripts/smoke-test.sh`.
  - Criterio de aceptacion: tests versionados cubren estaciones ignoradas, coordenadas invalidas, columnas obligatorias y nombres de salida por periodo.
  - Estado: resuelto como primera cobertura formal con `unittest`, integrada en `./scripts/smoke-test.sh`.

- [ ] Separar core en paquete Python reutilizable
  - Contexto: scripts grandes y duplicados.
  - Ficheros relacionados: `rainmapper_core/`, `Rainmapper.py`, `rainmapper-app/app/Rainmapper.py`, `scripts/sync-app-files.sh`, `docs/core-refactor.md`.
  - Criterio de aceptacion: una unica fuente de verdad para core compartida por Docker local y HA.
  - Estado parcial: fases 1 y 2 iniciadas. `incremental_upsert` vive en `rainmapper_core/incremental_upsert.py` y `tomap_to_geojson` delega en `rainmapper_core/geojson.py`; los ficheros de raiz/app se mantienen como wrappers compatibles. Validado con unit tests, smoke test y Docker offline functional test.
  - Riesgo si no se hace: mantenimiento manual permanente.

- [x] Extraer generacion de CSV `Tomap` de `Rainmapper.py`
  - Contexto: hasta ahora `Generate maps`/`MODE=maps` solo consumia los `Tomap` existentes para generar Bokeh y GeoJSON. Si cambiaba una columna derivada de `Tomap`, como el numero de ultimos registros de lluvia por estacion, hacia falta `Run all`/`MODE=all` para reconstruirlos.
  - Nota: desde `0.2.67`, el numero de registros recientes se configura con `last_rains_history`; con `tomap_builder.py`, `Generate maps` deberia poder reconstruir ese historico sin `Run all`, pendiente de validacion local/HA.
  - Ficheros relacionados: `Rainmapper.py`, `tomap_builder.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `Rainmapper_Client.py`, `tomap_to_geojson.py`.
  - Estado: resuelto. `tomap_builder.py` reconstruye `Tomap` y `LastXX_rains.csv`; `MODE=maps`, `MODE=all` y `Generate maps` lo invocan antes de Bokeh/GeoJSON. En `Rainmapper.py` se han retirado el bloque ejecutable inline de generacion `Tomap` y los helpers legacy `create_grouped` y `create_last_rains`.
  - Validacion: tras ejecutar `local_update.sh`, `scripts/compare-tomap-builder.sh` confirma que `tomap_builder.py` reconstruye los mismos CSV `Tomap` que el flujo antiguo de `Rainmapper.py` para los datos locales actuales. `local_maps.sh` reconstruye `Tomap`, genera GeoJSON y arranca el servidor local correctamente. `Generate maps` en HA `0.2.74` fue validado manualmente por el usuario. Tras retirar el bloque inline, `local_all.sh` completo termina con `Rainmapper.py` exit code 0, reconstruye Tomap con `tomap_builder.py` y genera GeoJSON. Tras limpiar helpers legacy, `MAX_THREADS=3 ./local_update.sh` termina con exit code 0 y las descargas actuales quedan contenidas en sus incrementales.
  - Riesgo residual: si cambia el schema de historicos incrementales, hay que actualizar `tomap_builder.py` y sus tests.

- [ ] Mejorar observabilidad de Wunderground
  - Contexto: Wunderground es el cuello de botella, pero todavia no hay suficientes observaciones de tiempos y el rendimiento actual es aceptable.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos segun reporte del usuario; pendiente de confirmar automaticamente.
  - Observacion local 2026-06-19: despues de permitir que `docker-compose.yml` propague `MAX_THREADS`, `local_update.sh` paso de `385.69s` con `MAX_THREADS=1` a `196.82s` con `MAX_THREADS=2` y `81.20s` con `MAX_THREADS=3`; Wunderground paso de `0:06:02` a `0:03:03` y despues a `0:01:19`.
  - Ficheros relacionados: `Rainmapper.py`, `Data/metricas_wunderground.csv`.
  - Criterio de aceptacion: metricas revisables y comparables por ejecucion; validar en HA/RPi si `max_threads=2` o `3` reduce tiempos sin generar timeouts, carga excesiva ni fallos de fuentes; posible export futuro a InfluxDB/Grafana.
  - Estado: parcialmente mejorado. `source_status.json` guarda duraciones reales por fuente y la webUI las muestra; Meteocat guarda subtiempos de metadata, condiciones, precipitacion, merge y guardado. Tras observacion nocturna de schedules en HA sin problemas reportados por el usuario, `max_threads=3` queda como valor operativo recomendado; queda pendiente decidir si exportar metricas historicas a InfluxDB/Grafana.
  - Riesgo si no se hace: optimizacion a ciegas del scraper si el rendimiento empeora en el futuro.

- [ ] Definir estrategia legal/comercial para Wunderground antes de una app publica
  - Contexto: el scraping HTML actual funciona para uso propio, pero las condiciones de TWC/Wunderground consultadas el 2026-06-18 no lo hacen apto como base de una app comercial sin permiso escrito. La API/PWS Data Feed oficial tambien limita el uso a personal/no comercial salvo acuerdo separado, y el pricing publico de Weather Data APIs parte de un plan Standard de 500 USD/mes orientado a clientes empresariales.
  - Ficheros relacionados: `Rainmapper.py`, `util/`, futura API/app movil, documentacion de producto.
  - Criterio de aceptacion: antes de comercializar mapas o app, decidir entre retirar Wunderground, reemplazarlo por fuentes con licencia compatible, limitarlo a uso privado o negociar derechos con The Weather Company.
  - Riesgo si no se hace: dependencia de una fuente con coste/licencia incompatible con una app comercial.

- [ ] Revisar timeout del scraper Wunderground
  - Contexto: algunas estaciones pueden tardar o fallar, pero el tiempo global actual es aceptable y conviene acumular mas observaciones antes de cambiarlo.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos segun reporte del usuario; pendiente de confirmar automaticamente.
  - Ficheros relacionados: `Rainmapper.py`, `util/`.
  - Criterio de aceptacion: timeout configurable y errores registrados sin bloquear toda la ejecucion.
  - Riesgo si no se hace: estaciones lentas podrian penalizar todo el run si el rendimiento empeora.

- [x] Hacer Meteocat/Socrata mas tolerante a timeouts transitorios
  - Contexto: en HA `0.2.67`, un `Run all` fallo despues de Wunderground porque una consulta Meteocat XEMA a `analisi.transparenciacatalunya.cat` supero el timeout por defecto de 10s del cliente Socrata.
  - Ficheros relacionados: `Rainmapper.py`, `const.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper-app/config.yaml`.
  - Criterio de aceptacion: las llamadas Meteocat/Socrata usan timeout configurable y reintentos antes de fallar el run.
  - Estado: corregido en `0.2.68` con `meteocat_request_timeout` y `meteocat_max_attempts`; pendiente de validacion manual en HA.

- [x] Validar ejecucion degradada por fuente y exit code global
  - Contexto: actualmente `Rainmapper.py` ejecuta Meteoclimatic, Meteocat y Wunderground en futuros paralelos, pero cualquier excepcion propagada por una fuente hace fallar el `update` completo. Wunderground controla errores por estacion y muestra resumen; Meteoclimatic tolera fallos de patrones individuales si algun patron devuelve datos, pero aborta si no recupera ninguno; Meteocat reintenta desde `0.2.68`, pero aborta si agota intentos.
  - Objetivo: si una de las tres fuentes falla completamente, el proceso general deberia poder continuar con las fuentes que si funcionen, reutilizar o marcar claramente datos antiguos cuando proceda, y dejar trazabilidad visible.
  - Ficheros relacionados: `Rainmapper.py`, `rainmapper-app/app/web_server.py`, `run.sh`, `rainmapper-app/run.sh`, `tomap_to_geojson.py`, `maplibre-viewer/`, documentacion HA.
  - Estado parcial: desde `0.2.71`, la webUI muestra estado/exit code separado para Meteoclimatic, Meteocat y Wunderground. `Rainmapper.py` escribe `Data/source_status.json`; si una fuente falla completamente intenta reutilizar su incremental previo y marca la fuente como `STALE`; si no hay incremental utilizable la marca como `NOK`. El fichero se copia como `data/source_status.json` en Leaflet/MapLibre publicados, y MapLibre muestra badges junto al filtro `Source`. Desde `0.2.73`, el exit code global distingue `0` exito completo, `2` exito degradado con al menos una fuente usable y `1` fallo total/no recuperable; `Run all` debe continuar a `maps` cuando `update` devuelve `2`.
  - Validacion: `0.2.73` fue validada manualmente en HA con `Run all` completo, `Exit code 0` y mapas generados correctamente.
  - Validacion adicional: el caso degradado `Exit code 2` se da por validado de facto en local por decision del usuario, tras el fallo accidental de lectura/escritura provocado por iCloud que permitio comprobar continuidad del proceso y trazabilidad por fuente.
  - Estado: resuelto operativamente; una validacion HA con fallo simulado queda como comprobacion opcional, no como bloqueo.

- [x] Retirar Jawg Maps de Leaflet/MapLibre y de la configuracion
  - Contexto: Jawg Street/Terrain eran capas opcionales activadas con `jawgmaps_api_key`, pero MapLibre ya cubre las necesidades actuales con Satellite+, Hybrid, Topographic, Liberty y 3D terrain. Jawg anade gestion de API key, posible restriccion por dominio, dudas de uso no comercial y complejidad de documentacion/soporte.
  - Ficheros relacionados: `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/config.yaml`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, README/DOCS y docs de contexto.
  - Criterio de aceptacion: no aparece `jawgmaps_api_key` en opciones HA ni docs principales; `JAWGMAPS_API_KEY` deja de usarse en visores; Leaflet/MapLibre no muestran capas Jawg; quedan actualizadas las decisiones/documentacion indicando que se descarta Jawg por bajo valor frente a complejidad/licencia/API key.
  - Estado: resuelto en `0.2.69`.
  - Riesgo si no se hace: mantener una dependencia externa y una clave cliente visible que ya no aporta valor suficiente al flujo actual.

- [ ] Evaluar InfluxDB/Grafana para metricas
  - Contexto: el usuario ya tiene interes en analitica de tiempos de estaciones.
  - Ficheros relacionados: `Rainmapper.py`, futuro exporter.
  - Criterio de aceptacion: decision tecnica documentada.
  - Riesgo si no se hace: se acumulan CSV sin explotacion.

- [x] Validar imagen Docker HA preconstruida
  - Contexto: antes de usar GHCR, Home Assistant construia la app en la RPi durante installs/updates, y la barra de progreso de HA podia quedarse en 0% hasta terminar. El Mac construye mucho mas rapido que la RPi segun validacion manual/reportada por el usuario.
  - Ficheros relacionados: `.github/workflows/build-rainmapper-app.yml`, `rainmapper-app/Dockerfile`, `rainmapper-app/config.yaml`, GitHub Container Registry.
  - Criterio de aceptacion: publicar imagen multi-arch `amd64`/`arm64` en GHCR antes de hacer visible el update en HA; HA descarga `ghcr.io/cginebrosa/rainmapperha:<version>` sin build local.
  - Estado: el repo soporta imagen GHCR y Buildx local con limpieza de etiquetas antiguas. Validaciones en `0.2.57`, `0.2.60`, `0.2.61`/`0.2.62`/`0.2.63`/`0.2.65` fueron manuales/reportadas por el usuario; pendientes de confirmar automaticamente. El flujo normal pasa a Buildx local con `scripts/build-push-ha-image.sh`, dejando Actions como fallback manual.
  - Riesgo residual: requiere login Docker en GHCR desde el Mac y disciplina de publicar imagen antes del commit de version.

- [x] Validar filtros de visor para futura app movil
  - Contexto: antes de construir la app iOS/Android se quieren probar funciones utiles en el visor web actual.
  - Ficheros relacionados: `maplibre-viewer/`, `tomap_to_geojson.py`, `tests/test_tomap_to_geojson.py`.
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
  - Causa: `run.sh` local solo ejecutaba `Rainmapper_Client.py`; la generacion GeoJSON estaba en `web_server.py` de HA pero no en el wrapper local.
  - Ficheros relacionados: `run.sh`, `rainmapper-app/run.sh`, `Dockerfile`.
  - Estado: corregido; `maps/all` ejecuta tambien `tomap_to_geojson.py`.

- [ ] Tests funcionales formales incompletos
  - Sintoma: ya existen fixtures `unittest` offline para `tomap_to_geojson.py`, `tomap_builder.py`, `incremental_upsert.py` y un pipeline integrado `upsert -> Tomap -> GeoJSON`; tambien existe `scripts/docker-offline-functional-test.sh` para validar el pipeline dentro de Docker con datos temporales. No hay cobertura funcional formal para HA real, publicacion webUI o generacion completa Bokeh/visores servida desde HA.
  - Causa probable: proyecto evolucionado por validacion manual.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `scripts/docker-offline-functional-test.sh`, `tests/`, futuro set de fixtures HA/webUI.
  - Como reproducir: ejecutar `./scripts/smoke-test.sh` para checks rapidos y `./scripts/docker-offline-functional-test.sh` para validacion Docker offline; ninguna de las dos prueba HA real.
  - Criterio de solucion: ampliar pruebas funcionales para publicacion, webUI y/o ejecuciones controladas de HA sin depender de red.

- [x] Cache-buster obsoleto en assets del visor MapLibre
  - Sintoma: la pulsacion larga de altitud funcionaba en local pero no en mapas servidos desde HA.
  - Causa: se detecto un problema real de cache-buster (`maplibre-viewer/index.html` seguia referenciando `app.js?v=0.2.62` aunque la app HA estaba en `0.2.63`), pero Chrome limpio tambien fallo tras generar mapas, asi que la causa funcional final era el disparador `pointerdown` directo sobre canvas en HA.
  - Ficheros relacionados: `maplibre-viewer/index.html`, `leaflet-viewer/index.html`, `scripts/smoke-test.sh`.
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
- [ ] Confirmar si el repo debe quedar privado o publico para distribucion futura.
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
- API propia entre backend y app movil.
- Capa de permisos por usuario.
- Cache/CDN de GeoJSON publicados.
- Panel de calidad de estaciones basado en metricas Wunderground.
- Auto-deteccion de outliers de lluvia antes de publicar mapas.
- Migracion de historicos CSV a formato mas eficiente si crecen mucho, por ejemplo Parquet, pendiente de evaluar.
