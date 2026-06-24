# Codex Handoff

## Ruta real del proyecto

La copia activa y valida del repositorio esta en:

```text
/Users/carlosginebrosa/Developer/RainmapperHA
```

No usar como fuente de verdad la copia antigua bajo iCloud/Mobile Documents:

```text
/Users/carlosginebrosa/Library/Mobile Documents/com~apple~CloudDocs/MyCloudDesktop/Programming/Source Code/RainmapperHA
```

Esa copia quedo desfasada durante la refactorizacion y puede provocar lecturas, tests o commits contra un arbol equivocado. Antes de tocar codigo o documentacion, verificar `pwd` y `git status` en la ruta real anterior.

## Objetivo de la app
RainmapperHA empaqueta Rainmapper como app de Home Assistant. La app descarga datos meteorologicos de varias fuentes, preserva historico en CSV, genera ficheros intermedios `Tomap`, crea mapas HTML clasicos y publica visores web modernos basados en GeoJSON para consultar lluvia acumulada por estacion.

Objetivo a largo plazo: convertir Rainmapper en una plataforma estable para recopilar, preservar, analizar y visualizar datos meteorologicos de multiples fuentes, automatizada desde Home Assistant, con visores web moviles y, mas adelante, una app iOS/Android con autenticacion, permisos de acceso y posible control comercial por mapas o zonas.

## Estado actual del proyecto
El proyecto tiene dos empaquetados principales:

- Docker local para Mac/desarrollo en `rainmapper-local/`, con wrappers shell de compatibilidad en la raiz.
- App de Home Assistant en `rainmapper-app/`.

La app de Home Assistant esta configurada para funcionar como servicio `serve`, con webUI por ingress/sidebar, schedule interno, ejecuciones manuales `update`, `maps` y `all`, publicacion en `/config/www`, visores Bokeh, Leaflet y MapLibre, metricas basicas de Wunderground y fichero manual para ignorar estaciones anomalas en los GeoJSON. El funcionamiento en la instalacion real de HA ha sido validado manualmente por el usuario hasta la version `0.2.113`; esa validacion no es reproducible solo desde el repositorio. `0.2.113` queda validada/dada por buena en HA con ajustes MapLibre de ayuda movil y badges de fuente en dos lineas. `0.2.114` queda publicada con viento normalizado y preservacion de backfill AEMET; `0.2.115` no debe considerarse buena por rendimiento/legibilidad; `0.2.116` corrigio el rendimiento de Tomap y el usuario reporto `Generate maps` en 1:59; `0.2.117` mejoro el formato del historial diario pero perdio la columna de dias y la cabecera sticky; `0.2.118` esta publicada para corregir esos dos puntos y queda validada visualmente en HA por el usuario el 2026-06-24. `0.2.119` queda publicada en GHCR con alineacion de subcolumnas en historial MapLibre, diagnostico/contadores AEMET 429 y botones `Update only` por fuente en WebUI. `0.2.120` queda publicada en GHCR y pusheada a GitHub para validar en HA el experimento MapLibre heatmap; digest multi-arch `0.2.120/latest`: `sha256:9efce7f58351b4c1f3634cc7ce33e9ef389310544dc887caa199fd310f0ab2ad`. Incluye ruta publica separada `/local/rainmapper-maplibre-heatmap/index.html`, boton `Heatmap`, selector/boton rapido de metrica, slider de opacidad y heatmap con todas las estaciones validas del periodo, sin cambiar el visor protegido por defecto. `0.2.109` publico AEMET integrado en el visor protegido estandar; `0.2.110` publico la redaccion de atribuciones AEMET/Meteocat como informacion/datos elaborados por Rainmapper. `0.2.111` queda validada/dada por buena en HA con Meteoclimatic/Wunderground alineados al mismo criterio de informacion elaborada por Rainmapper.

El repositorio GitHub `cginebrosa/RainmapperHA` se hizo privado el 2026-06-22 para no exponer codigo, rutas ni logica de uso de datos, especialmente Wunderground. Importante: tras hacer el repo privado se comprobo que Home Assistant no detecta updates nuevos porque necesita leer metadata del repo (`repository.yaml`, `config.yaml`, changelog); al volver a ponerlo publico detecto `0.2.101`. El flujo operativo actual para actualizar HA es publicar imagen GHCR, subir commit de version, hacer el repo publico temporalmente para que HA detecte la version, actualizar/validar en HA y volver a privado. Auditoria real del 2026-06-24: la API de GitHub devuelve `private=false`, `visibility=public` y rama por defecto `inicial`; por tanto volver a privado queda pendiente tras validar en HA la version vigente. El paquete GHCR `ghcr.io/cginebrosa/rainmapperha` se mantiene accesible para que Home Assistant pueda descargar la imagen preconstruida. `0.2.120/latest` queda publicado con digest multi-arch `sha256:9efce7f58351b4c1f3634cc7ce33e9ef389310544dc887caa199fd310f0ab2ad`. `0.2.119` queda como rollback inmediato con digest multi-arch `sha256:d6220a7ce7b186b7c598cbadadcb2f11c3d3bf41de3b33c5272dfcf2d993fe95`; `0.2.118` queda como ultima version validada visualmente en HA con digest `sha256:07ce37c45de5f705aeb1621f4fb680a7b2c9360014ee1ccbb95322e7815d0e96`. No limpiar GHCR remoto hasta validar `0.2.120` en HA. Cloudflare se endurecio operacionalmente fuera del repo: redireccion HTTP->HTTPS, HSTS `max-age=2592000; includeSubDomains`, `nosniff` y Cloudflare Access delante de `router.nomentero.com`, `leaflet.nomentero.com` y `maplibre.nomentero.com`. La ruta principal `rainmap.nomentero.com/protected/maplibre/index.html` queda servida por HTTPS y los GeoJSON protegidos siguen devolviendo `401` sin sesion Rainmapper.

AEMET OpenData esta implementado como fuente opcional de descarga, pero tras validar `0.2.108` se decide integrarlo en el Tomap/GeoJSON estandar de HA. `rainmapper_core/create_aemet.py` genera `Aemet.csv`, `Aemet_hourly_incremental.csv`, `Aemet_current_daily.csv`, `Aemet_incremental.csv` y `estacions_aemet.csv`. Desde `0.2.105`, el historico horario guarda lluvia (`prec`), temperatura (`ta`) y humedad (`hr`) cuando AEMET los entrega, y el diario calcula max/min de temperatura y humedad desde las horas disponibles. En `0.2.109`, los comandos HA de mapas pasan `--include-aemet true` a `rainmapper_core.tomap`, por lo que `/protected/maplibre/index.html`, Leaflet y Bokeh consumen el dataset estandar con AEMET cuando existe `Aemet_incremental.csv`. El publicador experimental `/local/rainmapper-maplibre-aemet/index.html` queda desactivado por flag en codigo como rollback temporal, no eliminado todavia; hay tarea pendiente para retirarlo definitivamente tras validar la ruta estandar. El reverse geocoding vive en `rainmapper_core/geocoding.py` y lo comparten las fuentes existentes y AEMET. AEMET consulta Google Maps con la misma `GMAP_API_KEY` cuando una estacion es nueva, le faltan `Municipi`/`Provincia` o cambian sus coordenadas; `--skip-station-enrichment` queda solo para pruebas temporales. La prueba temporal real `tmp/aemet-geocode-test-v2/` genero 802 estaciones enriquecidas, con `Municipi` en todas, `Provincia` en 800 y `Comarca` solo en 7; `Comarca` no debe tratarse como fiable desde Google ni dispara reintentos por si sola. El usuario ya copio manualmente ese `estacions_aemet.csv` enriquecido a `/share/rainmapper/Data` en HA antes de probar `0.2.102`.

Prueba externa en curso desde el 2026-06-22: el usuario ha dado acceso a dos companeros mediante login Rainmapper, usando cuatro usuarios en `/share/rainmapper/users.json`: un usuario propio con rol `admin` y limite configurado de 2 dispositivos, `Diegomovil` con rol `free` y 1 dispositivo, `Diegopc` con rol `free` y 1 dispositivo, y `Ramonmovil` con rol `free` y 1 dispositivo. No se ha avisado a los companeros del limite de dispositivo para observar si comparten credenciales; si lo hacen, nuevos dispositivos deberian quedar bloqueados por `max_devices` y las incidencias deberian verse en `devices.json`/WebUI Users. La instalacion HA ejecuta `Run all` aproximadamente cada 3 horas con schedule `01:45 - 05:00 - 08:00 - 11:00 - 14:00 - 17:00 - 20:00 - 23:55`.

El desarrollo actual esta en fase de operacion y mejora incremental de visores. Leaflet y MapLibre se mantienen publicados ambos; el usuario ha reportado que funcionan bien en iPhone, pendiente de confirmar con pruebas automatizadas o reproducibles desde el repo. Bokeh se mantiene como referencia y compatibilidad. La duplicidad fisica principal entre raiz y `rainmapper-app/app` fue retirada: la imagen HA se construye desde la raiz del repositorio y `rainmapper-app/app` queda reservado para codigo especifico de HA.

Regla operativa de colaboracion: cuando el usuario pida primero una explicacion o valoracion y ademas solicite documentarlo, responder primero con la explicacion util para liberar su tiempo. Despues, mientras el usuario lee/procesa la respuesta, actualizar la documentacion de continuidad/todo que corresponda. No retrasar una respuesta conceptual por hacer antes la documentacion, salvo que la documentacion sea el objetivo unico de la peticion.

## Stack tecnologico detectado
Confirmado en el repositorio:

- Lenguaje principal: Python 3.11.
- Scripts de datos: Python, pandas, numpy, requests, BeautifulSoup, lxml.
- Mapas clasicos: Bokeh 3.2.2 y Google Maps.
- Visores nuevos: HTML/CSS/JavaScript estatico.
- Leaflet viewer: Leaflet 1.9.4 via CDN.
- MapLibre viewer: MapLibre GL JS 4.7.1 via CDN, con estilos raster/vectoriales y capa Satellite+.
- Contenedores: Docker y Docker Compose.
- Home Assistant: app/add-on con `config.yaml`, ingress y `run.sh`.
- Persistencia: CSV en filesystem, principalmente `/share/rainmapper` en HA y `docker-data` en Docker local.
- Testing formal: existe `scripts/smoke-test.sh` para validaciones rapidas y `tests/` con `unittest` para fixtures funcionales offline de GeoJSON, `rainmapper_core.tomap`, upsert incremental y pipeline `upsert -> Tomap -> GeoJSON`; no se ha detectado `pytest`, `package.json`, Makefile ni framework de test completo.
- Lint/format formal: pendiente de confirmar. No se ha detectado configuracion dedicada.

## Documentos de referencia
`codex-handoff.md` es el punto de entrada, pero no contiene todo el contexto. Antes de cambios relevantes hay que leer tambien los documentos relacionados que apliquen, especialmente arquitectura, tareas, decisiones e historico/seguridad de datos.

- [architecture.md](architecture.md)
- [todo.md](todo.md)
- [decisions.md](decisions.md)
- [history-safety.md](history-safety.md)
- [mobile-app-architecture.md](mobile-app-architecture.md)
- [core-refactor.md](core-refactor.md)

Tambien existen documentos de uso:

- [../README.md](../README.md)
- [../README_DOCKER.md](../README_DOCKER.md)
- [../rainmapper-app/README.md](../rainmapper-app/README.md)
- [../rainmapper-app/DOCS.md](../rainmapper-app/DOCS.md)
- [../rainmapper-app/CHANGELOG.md](../rainmapper-app/CHANGELOG.md)

## Estructura relevante del proyecto
- `rainmapper_core/rainmapper.py`: implementacion principal de descarga, normalizacion, historico y estado por fuente; entrypoint canonico `python -m rainmapper_core.rainmapper`.
- `rainmapper_core/`: paquete compartido iniciado para reducir duplicidad raiz/app HA de forma conservadora. Contiene ya la implementacion real de upsert incremental, reconstruccion Tomap, conversion GeoJSON, generacion Bokeh, configuracion Python compartida bajo `rainmapper_core/config/`, visores compartidos bajo `rainmapper_core/viewers/` y librerias internas por fuente bajo `rainmapper_core/sources/`.
- `rainmapper_core/incremental_upsert.py`: helper comun para actualizar historicos incrementales por clave `Codi Estació` + `Data Local`, evitando duplicados logicos y conservando valores antiguos cuando una descarga nueva trae `NaN`.
- `rainmapper_core/tomap.py`: entrypoint canonico para reconstruir CSV `Tomap` desde historicos incrementales `Data/` sin descargar datos nuevos; se ejecuta con `python -m rainmapper_core.tomap`.
- `rainmapper_core/bokeh_maps.py`: generacion de mapas HTML clasicos con Bokeh; entrypoint canonico `python -m rainmapper_core.bokeh_maps`.
- `rainmapper_core/geojson.py`: entrypoint canonico para convertir CSV `Tomap` a GeoJSON para Leaflet/MapLibre; se ejecuta con `python -m rainmapper_core.geojson`.
- `rainmapper-local/`: runtime Docker local y scripts especificos de pruebas locales.
- `run.sh`: wrapper compatible de raiz hacia `rainmapper-local/run.sh`.
- `local_update.sh`: wrapper compatible de raiz hacia `rainmapper-local/local_update.sh`; refresca descargas actuales e incrementales sin reconstruir `Tomap` ni arrancar servidor local.
- `local_all.sh`: wrapper compatible de raiz hacia `rainmapper-local/local_all.sh`; ejecuta `MODE=all` y arranca un servidor HTTP local para probar MapLibre/Leaflet.
- `local_maps.sh`: wrapper compatible de raiz hacia `rainmapper-local/local_maps.sh`; ejecuta `MODE=maps` y arranca un servidor HTTP local sin descargar datos nuevos.
- `rainmapper-local/Dockerfile`: imagen Docker local.
- `rainmapper-local/docker-compose.yml`: runner Docker local con volumenes persistentes; permite probar concurrencia local con `MAX_THREADS=<n>`. La raiz mantiene `docker-compose.yml` como include de compatibilidad.
- `rainmapper_core/viewers/leaflet-viewer/`: fuente canonica del visor Leaflet.
- `rainmapper_core/viewers/maplibre-viewer/`: fuente canonica del visor MapLibre.
- `scripts/smoke-test.sh`: smoke test versionado para validar sintaxis, GeoJSON minimo con `ignore_stations_tomap.txt`, reconstruccion con poco historico, versiones y empaquetado HA sin copias de core.
- `scripts/build-push-ha-image.sh`: publica desde el Mac la imagen multi-arch de la app HA en GHCR usando Docker Buildx; sube tags `<version>` y `latest`, y limpia etiquetas locales versionadas antiguas conservando por defecto las dos ultimas mas `latest`. No limpia versiones remotas de GHCR.
- `scripts/compare-tomap-builder.sh`: reconstruye `Tomap` con `python -m rainmapper_core.tomap` en un directorio temporal y compara el resultado con `docker-data/Tomap`.
- `scripts/docker-offline-functional-test.sh`: prueba funcional Docker sin red; construye la imagen local, monta datos temporales, ejecuta `rainmapper_core.tomap` y `rainmapper_core.geojson` dentro del contenedor y valida salidas sin tocar `docker-data`.
- `tests/`: tests funcionales offline con `unittest`; cubren `rainmapper_core.geojson`, `rainmapper_core.tomap`, `rainmapper_core.incremental_upsert`, AEMET/backfill, viento, historico Meteoclimatic, traducciones MapLibre, auth web y un pipeline integrado `upsert -> Tomap -> GeoJSON`.
- `scripts/backup-data.sh`: crea backups `.tar.gz` de `Data` o de una raiz de datos Rainmapper.
- `scripts/check-history.py`: valida CSV historicos y permite comparar una copia antes/despues.
- `docs/mobile-app-architecture.md`: arquitectura inicial propuesta para futura app iOS/Android con API, auth, permisos, favoritos y filtro de lluvia minima.
- `docs/core-refactor.md`: notas vivas de la refactorizacion conservadora para reducir duplicidad raiz/app HA sin romper entrypoints.
- `rainmapper-app/`: app de Home Assistant, Dockerfile, metadata y wrapper de arranque.
- `rainmapper-app/app/`: codigo especifico de HA; actualmente solo `web_server.py`.
- `rainmapper-app/app/web_server.py`: webUI, schedule, publicacion a `/config/www`, controles de estaciones y ejecucion de jobs.
- `Data/`, `Tomap/`, `Plots/`: datos generados locales. Estan ignorados por Git.
- `docker-data/`: datos persistentes del Docker local. Esta ignorado por Git.

## Ficheros clave

### `rainmapper_core/rainmapper.py`
- Proposito: descarga datos de Meteocat, Meteoclimatic, Wunderground y AEMET opcional; actualiza historicos; guarda metricas de Wunderground; escribe `source_status.json`. Se ejecuta con `python -m rainmapper_core.rainmapper`; el wrapper raiz `Rainmapper.py` fue retirado.
- Estado actual: funcional, con argumentos CLI para fuentes, fechas, threads, intentos, log completo Wunderground y patrones Meteoclimatic multiples. Importa configuracion desde `rainmapper_core.config`, actualiza historicos con `rainmapper_core.incremental_upsert`, usando una sola fila por fuente/estacion/dia. La generacion `Tomap` ya no vive en el runner; esa responsabilidad esta en `rainmapper_core.tomap`. El fichero de estaciones ignoradas para mapas nuevos se aplica en `rainmapper_core.geojson`, no directamente aqui. Tras moverlo al core se valido con `python -m rainmapper_core.rainmapper --help`, tests, smoke test, Docker offline functional test, `./local_update.sh` real con exit code 0 y HA 0.2.79.
- Riesgos: contiene mucha logica acoplada, pandas sobre CSV historicos y scraping de Wunderground. No tocar sin preservar historicos y probar con Docker local.

### `rainmapper_core/config/`
- Proposito: configuracion Python compartida por Docker local y HA.
- Estado actual: contiene la implementacion real de `rainmapper_core/config/const.py`, `rainmapper_core/config/config.py` y `rainmapper_core/config/config_wunderground.py`. `rainmapper_core/config/const.py` conserva rutas runtime historicas calculando la raiz del entorno desde `rainmapper_core/config`.
- Riesgos: cambios en `rainmapper_core/config/const.py` afectan rutas `Data`, `Tomap`, `Plots`, defaults de fuentes, threads y parametros de historico; validar siempre imports y Docker local.

### `rainmapper_core/incremental_upsert.py`
- Proposito: centraliza el upsert de historicos CSV incrementales.
- Estado actual: la implementacion vive en `rainmapper_core/incremental_upsert.py`; no hay wrapper raiz; se importa desde `rainmapper_core.incremental_upsert`. Define la identidad logica de lectura como `Codi Estació` + `Data Local`. La fila nueva manda para valores no nulos; si la fila nueva trae `NaN`, conserva el valor antiguo no nulo. Esto evita duplicados como los detectados en Meteocat cuando lluvia y condiciones llegan con distinta disponibilidad.
- Riesgos: cualquier cambio aqui afecta directamente a `Data/*_incremental.csv`; validar siempre con backup/copia temporal y `scripts/check-history.py`.

### `rainmapper_core/tomap.py`
- Proposito: reconstruye `Tomap/*.csv` y `LastXX_rains.csv` desde `Data/*_incremental.csv`, sin descargar datos nuevos.
- Estado actual: la implementacion y el entrypoint canonico viven en `rainmapper_core/tomap.py`; los wrappers `tomap_builder.py` y `rainmapper-app/app/tomap_builder.py` se retiraron. Es la ruta activa de generacion `Tomap`; permite que `MODE=maps`, `MODE=all` y `Generate maps` regeneren `Tomap` antes de Bokeh/GeoJSON. Carga sus defaults desde `rainmapper_core.config.const`, incluido `_minimum_rain_tomap = 0`, por lo que estaciones sin lluvia siguen saliendo en los mapas. El bloque ejecutable equivalente y los helpers legacy ya se retiraron de `Rainmapper.py`.
- Estado publicado desde `0.2.115` y optimizado en `0.2.116`: los periodos agregan max/min de temperatura/humedad, viento medio ponderado por `wind_observation_count` si existe, racha maxima y direccion media circular; `LastXX_rains.csv` anade `Hum_*_NN` y `Wind_*_NN` para detalle diario, manteniendo compatibilidad con CSV/dataframes antiguos sin columnas `wind_*`.
- Riesgos: si cambia el schema de historicos incrementales, hay que revisar este builder y los tests asociados.

### `rainmapper_core/bokeh_maps.py`
- Proposito: genera mapas HTML clasicos Bokeh desde `Tomap`.
- Estado actual: entrypoint canonico `python -m rainmapper_core.bokeh_maps`; el wrapper raiz `Rainmapper_Client.py` fue retirado. Se publica en `/local/Plots`.
- Riesgos: depende de Google Maps API key y Bokeh. A medio plazo puede quedar como compatibilidad si Leaflet/MapLibre sustituyen su uso.

### `rainmapper_core/geojson.py`
- Proposito: convierte los siete CSV `Tomap` a GeoJSON para visores nuevos.
- Estado actual: la implementacion y el entrypoint canonico viven en `rainmapper_core/geojson.py`; los wrappers `tomap_to_geojson.py` y `rainmapper-app/app/tomap_to_geojson.py` se retiraron. Soporta 1, 7, 14, 21, 30, 60 y 90 dias; incluye metadata de generacion; permite ignorar estaciones desde `ignore_stations_tomap.txt`.
- Riesgos: si cambia el schema de `Tomap`, hay que actualizar este conversor y validar ambos visores.

### `rainmapper-app/app/web_server.py`
- Proposito: webUI HA, endpoints de ejecucion, schedule, publicacion de mapas, estado, logs, controles de errores Wunderground.
- Estado actual: pieza central de la app HA. Sirve modo `serve` en puerto 8099 e ingress.
- Riesgos: mucha responsabilidad en un unico fichero. Cambios aqui pueden afectar schedule, webUI, publicacion y acciones manuales.

### `rainmapper-local/run.sh`
- Proposito: entrypoint Docker local. Traduce variables de entorno a argumentos de `python -m rainmapper_core.rainmapper`, `python -m rainmapper_core.bokeh_maps` y `python -m rainmapper_core.geojson`. `run.sh` en raiz es solo un wrapper compatible.
- Estado actual: soporta modos `once/update`, `maps`, `all`, `help`, `schedule`. En `maps/all` genera Bokeh y GeoJSON en `docker-data/PublicData` para que MapLibre/Leaflet locales no lean datos obsoletos. La validacion del 2026-06-18 con `./local_all.sh` y 432 estaciones en `01d` fue manual/reportada por el usuario; pendiente de confirmar de forma automatizada.
- Riesgos: el modo `schedule` local es distinto del modo `serve` de HA; no confundir.

### `rainmapper-app/run.sh`
- Proposito: entrypoint de HA. Lee `/data/options.json`, prepara `/share/rainmapper`, crea symlinks, exporta variables y arranca el modo elegido.
- Estado actual: crea `stations.txt` e `ignore_stations_tomap.txt` si no existen y respeta los ficheros existentes. En modos no-serve `maps/all`, genera tambien GeoJSON en `/share/rainmapper/PublicData`.
- Riesgos: tocarlo puede romper persistencia de datos o reinstalaciones de HA.

### `rainmapper-app/config.yaml`
- Proposito: metadata, opciones y schema de Home Assistant.
- Estado actual: version `0.2.124`, ingress, sidebar, imagen preconstruida `ghcr.io/cginebrosa/rainmapperha`, opciones de schedule, Google Maps API key, AEMET API key, mapas, fuentes y publish. La webUI muestra la version runtime en el panel de estado, agrupa las tarjetas de status en filas explicitas, muestra estado separado por fuente (`Meteoclimatic`, `Meteocat`, `Wunderground`, `AEMET`) y los enlaces de visores incluyen cache-buster de version para evitar cargas obsoletas en HA. La validacion de `Run all`, logs en ingles y schedule en la instalacion real de Home Assistant es manual/reportada por el usuario; pendiente de confirmar automaticamente. `0.2.124` esta publicada en GHCR y pendiente de instalacion/validacion HA; `0.2.123` queda publicada y validada visualmente en la ruta heatmap experimental. `0.2.116` corrigio el rendimiento de Tomap tras el problema de `0.2.115`. En `0.2.113`, se valida en HA el ajuste de ayuda movil MapLibre y los badges de fuente en dos lineas para conservar visible el contador de estaciones. En `0.2.112`, se publica en GHCR la ayuda `?` de MapLibre y la documentacion HA actualizada. En `0.2.111`, se alinean las atribuciones Meteoclimatic/Wunderground al criterio de informacion elaborada por Rainmapper y queda validada/dada por buena en HA por el usuario. En `0.2.109`, AEMET pasa al Tomap/GeoJSON estandar de HA y se desactiva la ruta experimental publica.
- Riesgos: cualquier cambio de schema puede afectar updates de HA. Revisar compatibilidad de opciones existentes.

### `rainmapper-app/Dockerfile`
- Proposito: construye imagen de la app HA.
- Estado actual: usa Python 3.11 slim. Version alineada con `rainmapper-app/config.yaml` en `0.2.124`; tambien copia `users.example.json` para inicializar usuarios si falta configuracion persistente.
- Riesgos: puede confundir updates o diagnostico de version si labels/env no se actualizan junto con `config.yaml` en futuros bumps.

### `rainmapper_core/viewers/leaflet-viewer/`
- Proposito: visor Leaflet estatico.
- Estado actual: funcional, con capas Topographic/Hybrid, leyenda, selector de periodo, popups moviles y preservacion de vista al cambiar periodo.
- Riesgos: se publica solo en `/local/rainmapper-leaflet`; la ruta legacy `/local/rainmapper-mobile` fue retirada. Las redirecciones Cloudflare hacia los visores actuales fueron reportadas por el usuario y quedan pendientes de confirmar fuera del repositorio.

### `rainmapper_core/viewers/maplibre-viewer/`
- Proposito: visor principal MapLibre con mapas vectoriales/raster.
- Estado actual: funcional, con Satellite+ raster/vectorial por defecto, Hybrid raster, Topographic raster, OpenFreeMap Liberty, boton para orientar de nuevo al norte, consulta de altitud DEM por pulsacion larga con bloque local de estacion con lluvia mas cercana, panel de settings con selector de mapa, filtros cliente por lluvia minima, fuente de estacion y terreno 3D, y boton final `?` en la barra derecha para abrir la ayuda del mapa. En `0.2.81` se moderniza la UI: cabecera clara, controles flotantes, selector inferior de periodo, leyenda vertical dinamica, creditos en boton de informacion y popups claros. En `0.2.82`, el usuario valida en HA que `/protected/maplibre/index.html` funciona con login: `admin` puede entrar desde Mac+iPhone y un usuario de prueba queda limitado a un dispositivo. La version `0.2.83` amplia esa autenticacion a `users.json` con `username`, `name`, `email`, roles `free/basic/pro/admin` y `max_devices`; esa linea de autenticacion queda validada manualmente en versiones posteriores hasta `0.2.111`.
- Estado publicado: los popups muestran resumen de periodo con temperatura, humedad, viento medio/direccion y racha si existen; el historial diario muestra una tabla compacta con fecha, dias, lluvia, temperatura, humedad y viento. En `0.2.118`, la cabecera del historial queda sticky al hacer scroll. La ayuda `?` y traducciones ES/EN/CA ya se actualizaron para funcionalidades visibles del mapa.
- Heatmap publicado en `0.2.124`: la variante publica separada `/local/rainmapper-maplibre-heatmap/index.html`, activada por `window.RAINMAPPER_CONFIG.experimentalHeatmap`, se mantiene para pruebas sin autenticacion ni persistencia backend. El visor protegido `/protected/maplibre/index.html` tambien incluye controles de heatmap, pero solo para usuarios `admin`: boton `HM`, selector `Layer metric` (`Rain`, `Max temp`, `Min temp`, `Max humidity`, `Min humidity`, `Wind`), boton rapido de metrica similar al panel rapido de capas y pestaña `Heatmap` en Settings con metrica, opacidad, radio, intensidad y curva de peso (`Lineal`, `Suave`, `Fuerte`). Usuarios no admin no ven boton heatmap, boton de metricas ni pestana/seccion `Heatmap`, y el query string `?heatmap=1` ya no activa la funcion. La metrica seleccionada afecta siempre a puntos y leyenda; el boton `Heatmap` solo anade o quita la capa de densidad. El heatmap se dibuja por encima de los puntos para inspeccionar mejor la densidad. En el visor protegido admin, `heatmap` activo/inactivo, metrica, opacidad, radio, intensidad y curva de peso se persisten por `device_id` en `/auth/device-settings`.
- Riesgos: MapLibre queda como visor principal recomendado por decision de proyecto, con Leaflet mantenido como fallback. Las validaciones en HA/iPhone son manuales/reportadas por el usuario y no estan automatizadas. Satellite+ mezcla tiles Esri con orientacion vectorial OpenFreeMap y puede requerir ajustes visuales futuros si se detectan problemas. En `0.2.56` se corrige la vuelta a Satellite+ tras cambiar a otra capa clonando el objeto de estilo antes de pasarlo a MapLibre. El terreno 3D usa DEM externo Terrarium/Mapzen, esta apagado por defecto y depende de disponibilidad/CORS/rendimiento del proveedor externo hasta decidir si se generan tiles DEM propios.

### `rainmapper-local/docker-compose.yml`
- Proposito: ejecucion Docker local con volumenes en `docker-data`. `docker-compose.yml` en raiz incluye este fichero para mantener comandos antiguos.
- Estado actual: build local `rainmapperha:test`, modo por defecto `once`, variables de entorno y volumenes persistentes.
- Riesgos: no incluye datos en Git; requiere `docker-data/stations.txt` y API keys locales segun uso.

### `rainmapper-local/local_maps.sh`
- Proposito: prueba local rapida de cambios de visores sin descargar datos nuevos. `local_maps.sh` en raiz es solo un wrapper compatible.
- Estado actual: construye la imagen Docker local, ejecuta `MODE=maps` y arranca un servidor HTTP local para abrir MapLibre/Leaflet con los `Tomap` existentes.
- Riesgos: usa los datos ya presentes en `docker-data/Tomap`; si esos CSV estan obsoletos, el visor tambien mostrara datos obsoletos.

## Funcionalidades ya implementadas
- Docker local reproducible para Mac/desarrollo: `rainmapper-local/Dockerfile`, `rainmapper-local/docker-compose.yml`, `rainmapper-local/run.sh`, con wrappers compatibles en raiz.
- App Home Assistant instalable desde repo GitHub: `repository.yaml`, `rainmapper-app/config.yaml`.
- Modo `serve` con webUI e ingress/sidebar: `rainmapper-app/app/web_server.py`.
- Ejecuciones manuales `update`, `maps`, `all`: `web_server.py`, `run.sh`.
- Schedule interno con multiples horas y dias de semana: `web_server.py`, `config.yaml`.
- Persistencia en `/share/rainmapper`: `rainmapper-app/run.sh`.
- Publicacion de mapas a `/config/www`: `web_server.py`.
- Mapas Bokeh publicados en `/local/Plots`: `rainmapper_core.bokeh_maps`, `web_server.py`.
- Leaflet viewer publicado en `/local/rainmapper-leaflet/index.html`: `rainmapper_core/viewers/leaflet-viewer/`, `web_server.py`.
- MapLibre viewer operativo en `/protected/maplibre/index.html`: `rainmapper_core/viewers/maplibre-viewer/`, `web_server.py`. Durante la validacion de Cloudflared/puerto 8099 se mantiene temporalmente `/local/rainmapper-maplibre/index.html` como fallback funcional. Operativamente, el subdominio externo `maplibre.nomentero.com` ya queda protegido con Cloudflare Access, por lo que ese fallback externo no debe servir UI ni GeoJSON sin login de Cloudflare. No borrar todavia el fallback local del codigo hasta decidirlo explicitamente.
- GeoJSON para 1/7/14/21/30/60/90 dias: `rainmapper_core.geojson`.
- Ignorar estaciones anomalas en GeoJSON sin borrar historico: `ignore_stations_tomap.txt`, `rainmapper_core.geojson`.
- Filtros en MapLibre: settings del visor aplica filtros cliente por lluvia minima y por fuente de estacion sobre el periodo cargado para validar UX de futura app movil.
- Popups de estacion en Leaflet/MapLibre: muestran el resumen de estacion, lluvia acumulada, ultima lluvia del historico disponible (`DD/MM/AAAA · mm`) y un desplegable cerrado por defecto con los ultimos registros disponibles en el GeoJSON. El historico anade `Days ago`, mantiene cabecera sticky al hacer scroll y resalta visualmente las filas con lluvia. El visor detecta dinamicamente columnas `Data_Pluja_XX`; MapLibre incluye en Settings el control `Last rains history` para limitar cuantas filas se muestran. Rainmapper genera por defecto 30 registros recientes por estacion, configurable en HA con `last_rains_history` y en Docker local con `RAINMAPPER_LAST_RAINS_HISTORY`/`LAST_RAINS_HISTORY`.
- Terreno 3D en MapLibre: settings permite activar `3D terrain` y ajustar `Exaggeration` usando un DEM externo Terrarium/Mapzen como fuente `raster-dem`. El visor incluye un control flotante `2D`/`3D`, y en escritorio la tecla `t` alterna el mismo estado. No se incluye ningun DEM en la imagen Docker. Validado manualmente por el usuario en local, HA, Mac e iPhone; queda como funcionalidad definitiva por decision del 2026-06-18, aceptando la dependencia externa hasta que se decida si hace falta DEM propio.
- Consulta de altitud en MapLibre: una pulsacion larga sobre el mapa muestra un popup con cola apuntando al punto consultado y la altitud del DEM leyendo directamente el tile Terrarium externo y decodificando el pixel RGB. Se evita `queryTerrainElevation` para esta lectura porque en una prueba manual en Urus/Cerdanya (`42.35406, 1.85317`) devolvio `-4 m` aunque el tile DEM crudo devolvia unos `1259 m`; esta observacion queda pendiente de confirmar automaticamente. En HA no se disparaba la ventana incluso con Chrome limpio y tras generar mapas, por lo que `0.2.65` cambia el disparador de pulsacion larga a eventos propios de MapLibre y `contextmenu`, y ademas alinea los cache-busters internos de los visores. El cierre del popup de terreno limpia el estado activo igual que los popups de estacion para no bloquear el hover posterior en escritorio. En `0.2.77`, el usuario valida que MapLibre funciona bien en HA, Mac e iPhone tras anadir la cola del popup de terreno y el boton `2D`/`3D`; pendiente de confirmar mediante prueba automatizada o reproducible.
- `Source` en GeoJSON: `rainmapper_core.geojson` anade fuente inferida por codigo de estacion (`AEMET:` para AEMET, `ES...` de longitud minima 15 para Meteoclimatic, `I...` para Wunderground, codigos de longitud 2 para Meteocat, resto `Unknown`). Si aparece `Unknown`, el conversor emite un `WARNING` en stdout. Queda documentada como mejora futura la normalizacion de todos los codigos internos con prefijo de fuente para retirar inferencias fragiles.
- Autenticacion ligera MapLibre: `web_server.py` protege `/protected/maplibre/data/*.geojson` y `source_status.json`. En `0.2.82`, la ruta protegida fue validada manualmente en HA con `admin` desde Mac+iPhone y un usuario normal limitado a un dispositivo. La version `0.2.83` cambia el formato principal a `/share/rainmapper/users.json` con `username` para login, `name`, `email`, `password`, `role`, `enabled`, `max_devices` y `must_change_password`; el usuario valido en HA que el primer login creaba `users.json` desde la configuracion anterior. Despues se decide retirar completamente el formato anterior: `users.json` queda como unico formato soportado. Roles soportados: `free`, `basic`, `pro`, `admin`. Limites por defecto: `free=1`, `basic=2`, `pro=3`, `admin=0` ilimitado, con posible override por usuario. `run.sh` crea `users.json` desde `users.example.json` si no existe, y crea `devices.json` vacio si falta. La WebUI local incluye una pagina `Users` para usar desde Ingress/Home Assistant, con creacion de usuarios, activacion/desactivacion de acceso, cambios de rol/max_devices, establecimiento de nuevas contrasenas, reset obligatorio de contrasena y borrado de dispositivos individuales o todos los de un usuario. `Set password` guarda una contrasena definida por el administrador y borra dispositivos. `Reset password` marca `must_change_password=true`, borra dispositivos y obliga al usuario a elegir una contrasena distinta tras autenticarse con la actual. Aplica al servidor HA; el visor Docker local sigue siendo estatico para pruebas. Los tests `tests/test_web_server_auth.py` cubren JSON, limites por dispositivo, funciones de gestion y saneado de settings. La autenticacion y gestion quedan validadas manualmente en versiones posteriores hasta `0.2.111`.
- Settings MapLibre por dispositivo: el visor protegido puede guardar preferencias dentro del registro del `device_id` en `/share/rainmapper/devices.json`, bajo la clave `settings`. Los endpoints protegidos `/auth/device-settings` leen/escriben solo para el dispositivo autenticado y saneando campos permitidos. Los settings actuales saneados por backend son `period`, `min_rain_mm`, `map_style`, `language`, `last_rains_history`, `station_sources`, `terrain_enabled`, `terrain_exaggeration` y `map_view` (`lng`, `lat`, `zoom`, `bearing`, `pitch`). El visor carga esos settings tras validar sesion y antes de cargar datos; guarda al cerrar el panel Settings solo si se ha modificado algun control del propio panel. Mover el mapa normalmente, cambiar periodo desde la barra inferior, cambiar mapa desde el boton rapido o usar el boton compacto `2D`/`3D` no escribe `devices.json`. `map_view` solo se guarda cuando el usuario pulsa explicitamente en Settings el boton para establecer la vista actual como predeterminada y despues se guarda/cierra Settings. Esta persistencia aplica al servidor HA protegido; el visor Docker local sigue sin auth. En `0.2.98`, se anade un boton rapido de seleccion de mapa entre `2D`/`3D` y la brujula; cambia el mapa visible sin persistir `map_style` en `devices.json`. El selector de dias sigue el mismo criterio: la barra inferior cambia solo el periodo visible, mientras que el selector dentro de Settings actualiza el periodo preferido que se guarda. En `0.2.99`, se publica y valida en HA el selector de idioma ES/EN/CA para MapLibre usando lenguaje de usuario no tecnico; las cadenas viven en `rainmapper_core/viewers/maplibre-viewer/translations.json`, se cargan desde el visor con fallback minimo en JS y se publican/permiten tambien en `/protected/maplibre/translations.json`. En `0.2.100`, se compactan y validan en HA los controles flotantes moviles de MapLibre, se reduce el margen derecho de los botones, se acerca la leyenda al margen izquierdo y la barra inferior usa etiquetas compactas `1d`/`7d`/... sin espacio.
- Estado por fuente: `rainmapper_core.rainmapper` escribe `Data/source_status.json` con el ultimo estado de Meteoclimatic, Meteocat, Wunderground y AEMET. Si una fuente falla completamente, el update intenta continuar con el incremental previo y marca la fuente como `STALE`; si no hay incremental utilizable la marca como `NOK`. La webUI de HA muestra esas tarjetas de estado desde `0.2.71` y ahora tambien muestra duraciones reales por fuente, filas (`rows`) y estaciones (`stations`) cuando el origen lo proporciona; Meteocat guarda ademas subtiempos reales de metadata, condiciones, precipitacion, merge y guardado. MapLibre muestra badges de estado junto al filtro `Source`, usando `stations` para el numero visible de fuente cuando esta disponible. Por decision del usuario, los tiempos de proceso no son relevantes para el visor de mapas.
- Wunderground full log configurable y resumen de errores: `rainmapper_core.rainmapper`, `config.yaml`.
- Upsert incremental por fuente: `rainmapper_core.rainmapper` usa `rainmapper_core/incremental_upsert.py` para mantener como maximo una fila por `Codi Estació` + `Data Local`. Validacion local 2026-06-19 con datos copiados de HA: Meteocat paso de 316699 filas y 28 filas duplicadas por clave a 316685 filas y 0 duplicados; Meteoclimatic y Wunderground quedaron sin duplicados y con las claves actuales contenidas. Validacion HA `0.2.77`: `Run update` termino con exit code 0, Meteocat quedo en 316685 filas, Meteoclimatic en 122970 y Wunderground en 67299; `Generate maps` termino con exit code 0 y publico visores `v=0.2.77`.
- Control webUI para desactivar/reactivar estaciones Wunderground por 404 o parse error: `web_server.py`.
- Metricas de tiempos por estacion Wunderground en `Data/metricas_wunderground.csv`: `rainmapper_core.rainmapper`.
- Meteoclimatic con multiples patrones separados por coma, punto y coma o ` - `: `rainmapper_core.rainmapper`.
- Google Maps API key por variable/opcion, sin hardcode confirmado en ficheros inspeccionados.
- Jawg Maps retirado desde `0.2.69`: ya no hay `jawgmaps_api_key`, variable `JAWGMAPS_API_KEY` ni capas Jawg en Leaflet/MapLibre.
- Satellite+ en MapLibre combina Esri World Imagery con carreteras, limites y etiquetas vectoriales de OpenFreeMap.
- Terrain 3D en MapLibre queda como funcionalidad definitiva, apagada por defecto, validada manualmente en local, HA e iPhone. Sigue dependiendo del DEM externo Terrarium/Mapzen; si esa dependencia falla o el rendimiento empeora, estudiar DEM propio.

## Funcionalidades parcialmente implementadas
- Leaflet y MapLibre: funcionales en el codigo y validados manualmente en iPhone/HA segun reporte del usuario; pendiente de confirmacion automatizada. MapLibre `0.2.53` queda como visor principal recomendado; Leaflet se mantiene publicado como fallback. Bokeh sigue como referencia/compatibilidad.
- Sustitucion futura de Bokeh: Leaflet/MapLibre ya existen, pero Bokeh sigue publicado y documentado.
- Ruta legacy `/local/rainmapper-mobile`: retirada del repo/app. Cloudflare redirigia a `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre` segun reporte del usuario; desde la autenticacion ligera de MapLibre, la ruta recomendada para MapLibre pasa a ser `/protected/maplibre/index.html`.
- App settings link: usa Supervisor self-info; muestra el enlace recomendado por defecto y deja rutas alternativas en una seccion avanzada.
- Versionado HA: `config.yaml`, labels Docker, banner runtime y cache-busters de visores estan alineados en `0.2.120`.
- Internacionalizacion: la webUI visible de HA, metadata HA, changelog y logs operativos principales del core estan en ingles. README/DOCS de la app HA siguen en espanol porque de momento la app es de uso propio; no hay sistema i18n.
- MapLibre protegido muestra en la cabecera el usuario autenticado y su rol (`free`, `basic`, `pro` o `admin`) en una segunda linea compacta bajo la fecha generada, usando `username (role)` y el payload existente de login o `/auth/session`.

## Funcionalidades pendientes
- Decidir retirada de Bokeh o mantenerlo como referencia.
- Crear tests automaticos mas completos; existe smoke test versionado, cobertura `unittest` offline para GeoJSON, Tomap, upsert incremental, auth backend y pipeline `upsert -> Tomap -> GeoJSON`, y una prueba Docker offline versionada. Faltan fixtures funcionales de HA/webUI/publicacion real.
- Mejorar separacion entre core de datos, webUI y visores.
- Extraccion de CSV `Tomap`: `python -m rainmapper_core.tomap` reconstruye `Tomap` desde historicos sin descargar datos nuevos, y `MODE=maps`/`Generate maps` lo invocan antes de Bokeh/GeoJSON. Validacion local inicial: tras `local_update.sh`, `scripts/compare-tomap-builder.sh` confirma que el builder genera los mismos `Tomap` que el flujo antiguo; `local_maps.sh` reconstruye `Tomap`, genera GeoJSON y arranca el servidor local correctamente. `Generate maps` en HA `0.2.74` fue validado manualmente por el usuario. El bloque ejecutable inline y los helpers legacy de `Rainmapper.py` ya fueron retirados; `local_all.sh` completo queda validado en local con `rainmapper_core.rainmapper` exit code 0, reconstruccion Tomap por `rainmapper_core.tomap` y GeoJSON generado.
- Imagen Docker HA multi-arch preconstruida en GHCR desde `0.2.57`; el repo confirma `image: ghcr.io/cginebrosa/rainmapperha` y el script `scripts/build-push-ha-image.sh`. La instalacion rapida en HA, el progreso de Supervisor, la poca utilidad del cache de GitHub Actions y la limpieza local observada son validaciones manuales/reportadas por el usuario; pendientes de confirmar automaticamente. Desde `0.2.60`, el flujo normal documentado es publicar la imagen desde el Mac con `scripts/build-push-ha-image.sh` antes de subir el commit de version; GitHub Actions queda como fallback manual. `0.2.120` y `latest` se publicaron el 2026-06-24 con digest multi-arch `sha256:9efce7f58351b4c1f3634cc7ce33e9ef389310544dc887caa199fd310f0ab2ad`. `0.2.118` queda como ultima version validada en HA con digest `sha256:07ce37c45de5f705aeb1621f4fb680a7b2c9360014ee1ccbb95322e7815d0e96`; se conserva `0.2.119` como rollback inmediato hasta validar `0.2.120`. No limpiar remoto hasta que HA haya descargado/arrancado `0.2.120` correctamente.
- Analitica historica de metricas Wunderground, posiblemente con InfluxDB/Grafana.
- Gestion WebUI de usuarios y dispositivos: interfaz HA implementada para crear/desactivar/borrar usuarios, cambiar rol/max_devices, establecer nueva contrasena, forzar cambio de contrasena y borrar uno o todos los dispositivos de un usuario. `Delete user` borra tambien todos sus dispositivos asociados. En `0.2.101` se publica y valida manualmente en HA una cabecera fija en `Users` con vuelta a inicio, refresh manual sin recargar el navegador, busqueda libre por contenido de usuarios/dispositivos y preservacion de scroll al refrescar.
- Autenticacion/autorizacion real para una futura app publica iOS/Android.
- Definir modelo de producto/acceso si se venden mapas o zonas.
- Ideas para futura app iOS/Android: favoritos de estaciones y filtro por lluvia minima en el periodo seleccionado.
- Arquitectura inicial de app movil documentada en [mobile-app-architecture.md](mobile-app-architecture.md), con direccion preferente de prototipo Cloudflare R2 + Worker API + React Native/MapLibre.
- Ejecucion degradada por fuente: desde `0.2.71`, el core escribe `source_status.json`, reutiliza incrementales previos si una fuente falla, la webUI muestra estado/exit code por fuente y MapLibre muestra badges de estado junto al selector `Source`. Desde `0.2.73`, el exit code global distingue `0` exito completo, `2` exito degradado y `1` fallo total/no recuperable. El caso normal `Run all` con `Exit code 0` y mapas correctos fue validado manualmente en HA; el caso degradado `Exit code 2` se da por validado de facto en local por decision del usuario tras el fallo accidental de lectura/escritura provocado por iCloud. Una validacion HA con fallo simulado queda como comprobacion opcional.

## Bugs abiertos o problemas conocidos
- La duplicidad de scripts entre raiz y `rainmapper-app/app` fue retirada. Riesgo residual: el build HA depende de construir desde la raiz del repo, no desde `rainmapper-app` como contexto aislado.
- Tests formales offline existen en `tests/` para GeoJSON, Tomap, upsert incremental y pipeline `upsert -> Tomap -> GeoJSON`; `scripts/docker-offline-functional-test.sh` cubre el pipeline dentro de Docker con volumenes temporales. Faltan pruebas funcionales completas de HA/webUI/publicacion real.
- La app HA `serve` maneja SIGTERM/SIGINT desde `0.2.55`: `run.sh` usa `exec` para que Python sea PID 1; `web_server.py` detiene el scheduler, espera al job activo antes de cerrar y solo fuerza el subprocess si llega una segunda senal.
- Wunderground es el cuello de botella principal. Prueba local del 2026-06-19 tras corregir `docker-compose.yml` para propagar el override: `MAX_THREADS=1` tardo `385.69s`, `MAX_THREADS=2` tardo `196.82s` y `MAX_THREADS=3` tardo `81.20s` en `local_update.sh`. Validacion manual en HA/RPi con `max_threads=2`: Meteoclimatic ~62s, Meteocat ~26s, Wunderground ~3m39s, total ~5m43s, sin carga relevante de CPU/memoria reportada por el usuario. Tras dejar correr schedules nocturnos con `max_threads=3` sin problemas reportados, `max_threads=3` queda como valor operativo recomendado en HA; `1` queda como modo conservador si aparecen timeouts o carga. Se detecto que los logs `start_count/end_count` usan un temporizador global compartido y no son metricas fiables con hilos; usar `source_status.json` para duraciones reales.
- Las claves usadas por codigo cliente web serian visibles en navegador; por eso se ha retirado Jawg Maps y cualquier futura clave de tiles cliente debera justificarse y restringirse por dominio si el proveedor lo permite.
- Los historicos CSV son el valor central del proyecto; no deben borrarse ni reescribirse sin backup. Ver [history-safety.md](history-safety.md).
- Algunas carpetas generadas (`Data`, `Tomap`, `Plots`, `docker-data`, `docker-empty-test`) existen localmente pero estan ignoradas por Git.
- El DEM propio de Land/TwoNav `Iberia_HighResolution.CDEM` no fue reconocido por `gdalinfo` en una prueba manual fuera del repo; Land tampoco permitio exportarlo correctamente segun reporte del usuario. Pendiente de confirmar si se retoma. La via recomendada para 3D es validar primero DEM externo y, si aporta valor, estudiar IGN/CNIG/Copernicus o una exportacion estandar GeoTIFF/HGT/ASC.

## Variables de entorno y configuracion
- `GH_TOKEN`: token local de GitHub usado para operaciones autenticadas contra GitHub/GHCR desde este Mac, como listar/borrar versiones del paquete `ghcr.io/cginebrosa/rainmapperha` o verificar la visibilidad del repo. En la sesion de terminal del usuario esta disponible desde `~/.zshrc`, pero los comandos no interactivos lanzados por Codex pueden no heredarlo. Para usarlo desde Codex sin exponer el valor, ejecutar los comandos GitHub/GHCR como `zsh -ic '...'` y referenciar `$GH_TOKEN` dentro de ese comando. Comprobar disponibilidad sin revelar el secreto con `zsh -ic 'test -n "$GH_TOKEN" && printf "GH_TOKEN is available\n"'`. No imprimir, guardar ni versionar el valor del token.
- `GMAP_API_KEY`: clave Google Maps; usada por `rainmapper_core/config/const.py`, `rainmapper_core/rainmapper.py`, mapas Bokeh y por `get_googlemaps()` para obtener altitud, municipio/localidad y provincia cuando se detectan estaciones nuevas o cambios de coordenadas. Obligatoria si se usan funciones que requieren Google Maps; no debe ir en Git.
- `SODAPY_APPTOKEN`: token Socrata/Meteocat mencionado solo en codigo comentado; actualmente no se usa porque `socrata_token` se fija a `None`. Pendiente de confirmar si debe reactivarse en el futuro.
- `SUPERVISOR_TOKEN`: token inyectado por Home Assistant; usado por `web_server.py` para consultar self-info del addon. Lo proporciona HA.
- `RAINMAPPER_MODE` / `MODE`: modo Docker local (`once`, `update`, `maps`, `all`, `schedule`, `help`).
- `RAINMAPPER_SCHEDULE_TIME` / `SCHEDULE_TIME`: hora o horas de schedule local/HA segun wrapper.
- `RAINMAPPER_TIMEZONE` / `TIMEZONE`: zona horaria, por defecto `Europe/Madrid`.
- `RAINMAPPER_DAYS_INIT` / `DAYS_INIT`: inicio de rango relativo de dias.
- `RAINMAPPER_DAYS_END` / `DAYS_END`: fin de rango relativo de dias.
- `RAINMAPPER_METEOCAT_REQUEST_TIMEOUT` / `METEOCAT_REQUEST_TIMEOUT`: timeout por intento en peticiones Meteocat/Socrata, por defecto 30 segundos.
- `RAINMAPPER_METEOCAT_MAX_ATTEMPTS` / `METEOCAT_MAX_ATTEMPTS`: numero de intentos por peticion Meteocat/Socrata, por defecto 3.
- `RAINMAPPER_CREATE_WUNDERGROUND` / `CREATE_WUNDERGROUND`: activa Wunderground.
- `RAINMAPPER_CREATE_METEOCLIMATIC` / `CREATE_METEOCLIMATIC`: activa Meteoclimatic.
- `RAINMAPPER_CREATE_METEOCAT` / `CREATE_METEOCAT`: activa Meteocat.
- `RAINMAPPER_METEOCLIMATIC_PATTERN` / `METEOCLIMATIC_PATTERN`: patron o patrones RSS Meteoclimatic.
- `RAINMAPPER_MAX_THREADS` / `MAX_THREADS`: threads Wunderground.
- `RAINMAPPER_MAX_ATTEMPTS` / `MAX_ATTEMPTS`: reintentos Wunderground.
- `RAINMAPPER_WUNDERGROUND_FULL_LOG` / `WUNDERGROUND_FULL_LOG`: log detallado por estacion.
- `RAINMAPPER_LAST_RAINS_HISTORY` / `LAST_RAINS_HISTORY`: numero de registros recientes de lluvia que se generan para popups de estaciones; en HA se configura con `last_rains_history`.
- `RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE`: fichero de estaciones ignoradas al generar GeoJSON.

## Riesgos operativos por fuente
- Meteocat/Socrata: actualmente se consulta sin app token (`socrata_token = None`). Esto puede aplicar limites estrictos de frecuencia/tamano y provocar fallos transitorios, especialmente en consultas grandes. El rango operativo de 7 dias mitiga parcialmente este riesgo. Si los fallos se repiten, valorar reactivar `SODAPY_APPTOKEN` o reducir/fragmentar consultas.
- Wunderground: actualmente se obtiene por scraping HTML y es el cuello de botella principal. La alternativa oficial PWS/Data Feed de The Weather Company requiere API key y queda descartada para el plan actual por coste/enfoque enterprise visible en pricing publico. Ademas, las condiciones de uso de TWC/Wunderground consultadas el 2026-06-18 limitan los servicios y el PWS Data Feed a uso personal/no comercial, prohiben copiar/monitorizar datos con scrapers para propositos comerciales o no autorizados sin permiso escrito, y exigen acuerdo separado para cualquier uso comercial del Data Feed. Por tanto, los datos Wunderground no deben usarse como base de una app comercial sin permiso/acuerdo escrito de TWC; si se comercializa Rainmapper, habra que retirar Wunderground, sustituirlo por fuentes con licencia compatible o negociar derechos.

## Comandos importantes
Instalar dependencias Python localmente:

```bash
pip install -r requirements.txt
```

Crear venv local: pendiente de confirmar. El repositorio contiene `.venv` local ignorado, pero no hay comando documentado de creacion.

Build Docker local:

```bash
docker compose build rainmapper
```

Ejecucion Docker local por defecto:

```bash
docker compose run --rm rainmapper
```

Ayuda del script dentro de Docker:

```bash
docker compose run --rm -e MODE=help rainmapper
```

Ejecutar update local:

```bash
docker compose run --rm -e MODE=update rainmapper
```

Generar mapas local:

```bash
docker compose run --rm -e MODE=maps rainmapper
```

Ejecutar update + maps local:

```bash
docker compose run --rm -e MODE=all rainmapper
```

Preparar datos persistentes Docker local:

```bash
mkdir -p docker-data/Data docker-data/Tomap docker-data/Plots docker-data/PublicData
cp stations.example.txt docker-data/stations.txt
```

Smoke test:

```bash
./scripts/smoke-test.sh
```

Sincronizacion raiz -> app HA:

```text
No aplica. La duplicidad fisica principal fue retirada; HA se construye desde la raiz del repo y `rainmapper-app/app` queda solo para codigo especifico de HA (`web_server.py`). No reintroducir `scripts/sync-app-files.sh` ni `scripts/sync-manifest.sh`.
```

Validaciones sintacticas usadas/recomendadas:

```bash
./scripts/smoke-test.sh
python -m unittest tests.test_web_server_auth
python -m py_compile rainmapper_core/rainmapper.py rainmapper_core/bokeh_maps.py rainmapper_core/geojson.py rainmapper-app/app/web_server.py
node --check rainmapper_core/viewers/leaflet-viewer/app.js
node --check rainmapper_core/viewers/maplibre-viewer/app.js
git diff --check
```

Lint/format:

```text
pendiente de confirmar
```

Despliegue Home Assistant:

```text
Regla operativa para bumps HA: priorizar que la version quede disponible en Home Assistant antes de documentar el cierre. Orden recomendado: ejecutar la validacion minima local necesaria, publicar la imagen GHCR versionada/latest con scripts/build-push-ha-image.sh, verificar el digest, hacer commit/push del bump para que HA detecte el update, avisar al usuario inmediatamente de que la version ya esta disponible en HA, y solo entonces completar la documentacion de continuidad mientras el usuario descarga/instala/prueba. No retrasar la disponibilidad en HA por documentar primero.

Despliegue manual confirmado: hacer Check for updates en Home Assistant y actualizar la app desde la UI de HA. No hay comando CLI de despliegue confirmado.
```

Validacion estandar antes de publicar imagen HA:

```text
Procedimiento estandar: para un bump/publicacion HA, ejecutar ./scripts/smoke-test.sh una sola vez despues de aplicar cambios y antes de scripts/build-push-ha-image.sh. Tras publicar imagen y subir el bump a GitHub, avisar al usuario sin esperar a terminar documentacion extensa. Si el build/push termina bien y despues solo se actualiza documentacion con el digest publicado, no repetir el smoke completo; basta con revisar el diff/estado y commitear. Repetir ./scripts/smoke-test.sh solo si despues del primer smoke se toca codigo runtime, configuracion HA, assets de visor, scripts o cualquier fichero que entre en la imagen.
```

Limpieza remota GHCR tras release HA:

```text
Procedimiento estandar: despues de publicar una nueva imagen con scripts/build-push-ha-image.sh, subir el commit de version y validar en HA que la nueva version descarga y arranca correctamente, borrar del paquete GHCR las versiones remotas antiguas. Conservar solo la ultima version validada, latest y las entradas auxiliares sin tag del mismo push multi-arch. No borrar la version que declare rainmapper-app/config.yaml ni sus entradas auxiliares mientras HA pueda necesitar reinstalarla.
```

## Flujo de ejecucion de la app
1. Home Assistant arranca `rainmapper-app/run.sh`.
2. `run.sh` lee `/data/options.json`, crea `/share/rainmapper` y sus subcarpetas, crea `stations.txt` e `ignore_stations_tomap.txt` si faltan y no sobrescribe los existentes.
3. `run.sh` crea symlinks hacia `/app/Data`, `/app/Tomap`, `/app/Plots`, `/app/PublicData` y exporta variables.
4. En modo recomendado `serve`, arranca `web_server.py` en `0.0.0.0:8099`; el manifiesto HA publica tambien `8099/tcp` para acceso LAN/Cloudflared ademas de ingress.
5. La webUI permite lanzar `update`, `maps` o `all`.
6. `update` ejecuta `python -m rainmapper_core.rainmapper` y actualiza CSV historicos y estado por fuente; `maps`/`all` reconstruyen `Tomap` con `rainmapper_core.tomap`.
7. `maps` ejecuta `python -m rainmapper_core.bokeh_maps`, genera Bokeh HTML y despues `rainmapper_core.geojson` para los visores nuevos.
8. Si `publish_to_www` esta activo, la app copia HTML y visores a `/config/www`.
9. HA sirve Bokeh como `/local/Plots`, Leaflet como `/local/rainmapper-leaflet` y MapLibre desde el servidor Rainmapper en `/protected/maplibre/index.html` con datos protegidos en `/protected/maplibre/data/*`. Para Cloudflared, el `service` debe apuntar a `http://<HA_IP>:8099`.

## Integraciones externas
- Meteocat / Socrata: usado desde `rainmapper_core.rainmapper` y `rainmapper_core/sources/sodapy_local`. Lecturas de lluvia/temperatura/humedad usan el recurso `nzvn-apee` (`Dades meteorològiques de la XEMA`). Las variables diarias de viento XEMA `1503`-`1517` existen en metadata pero no tienen filas en `nzvn-apee`; se publican en el recurso diario `7bvh-jvq2` (`Dades meteorològiques diàries de la XEMA`). Confirmado contra Socrata el 2026-06-24: `nzvn-apee` tenia lluvia/temperatura hasta `2026-06-24T02:00:00`, mientras `7bvh-jvq2` tenia viento diario `1503`/`1512` solo hasta `2026-06-21T00:00:00`, por lo que los dias recientes pueden quedar sin viento Meteocat hasta que se publique el agregado diario.
- Meteoclimatic RSS: usado desde `rainmapper_core/sources/meteoclimatic_local`; `meteoclimatic_pattern` filtra estaciones. El feed entrega `wind_current`, `wind_max` y `wind_bearing` por lectura. El 2026-06-24 se inicio un rediseño para no machacar el viento del mismo dia: `rainmapper_core/meteoclimatic_history.py` guarda `Meteoclimatic_observations_incremental.csv` con observaciones crudas deduplicadas por `Codi Estació` + `Data Lectura`, y deriva el incremental diario calculando media/min/max de viento actual, racha maxima y direccion media circular. Lluvia/temperatura/humedad conservan semantica de ultima observacion del dia para no cambiar de golpe el significado historico de Meteoclimatic. Validado localmente el 2026-06-24 con incrementales reales bajados de HA: `Meteoclimatic_observations_incremental.csv` quedo con 511 observaciones y 0 duplicados estacion/timestamp; `Meteoclimatic_incremental.csv` quedo con 125778 filas, 27 columnas y 0 duplicados estacion/dia. Pendiente observar varios runs para confirmar acumulacion de varias lecturas del mismo dia.
- Wunderground: scraping via `requests`, `BeautifulSoup` y parser local en `rainmapper_core/sources/wunderground`. En modo mensual operativo (`MONTHLY=True`) la tabla trae `SpeedHigh_kmh`, `SpeedAv_kmh` y `SpeedLow_kmh`, pero no direccion. El usuario confirmo el 2026-06-24 que `Wind` solo aparece en la vista diaria por observacion; no inventar direccion en mensual. Decision del 2026-06-24: no redisenar Wunderground ahora para direccion porque duplicaria o sustituiria el scrape mensual con observaciones diarias y aumentaria el tiempo del cuello de botella principal. Mantener velocidad media/min/max desde mensual y dejar `wind_direction_deg` vacio para Wunderground; el futuro predictor debe tratar valores de viento/direccion vacios como dato no disponible, no como viento cero ni direccion norte. Prueba local real del 2026-06-24 solo Wunderground, con backup previo `backups/rainmapper-docker-data-20260624-052903.tar.gz`: 99/99 estaciones OK, `Wunderground_incremental.csv` quedo con 67751 filas, 27 columnas, 0 duplicados estacion/dia, 2272 filas con velocidad y 0 con direccion.
- AEMET OpenData: evaluado el 2026-06-23 como posible nuevo origen. Endpoint operativo recomendado: `/opendata/api/observacion/convencional/todas`, con API key en cabecera `api_key`. Devuelve observaciones horarias recientes de las ultimas 12 horas para todas las estaciones, con `idema`, `lat`, `lon`, `alt`, `ubi`, `fint` y `prec`; `prec` es lluvia acumulada durante los 60 minutos anteriores a `fint`, en UTC. Debe llamarse una sola vez por ejecucion, no por estacion, y deduplicar por `AEMET + idema + fint`. Si devuelve `429 Too Many Requests`, saltar AEMET en esa ejecucion sin romper `Run all` y reintentar en el siguiente schedule. El 2026-06-24 el endpoint global devolvio `429` durante pruebas de viento, pero una llamada aislada a `/opendata/api/observacion/convencional/datos/estacion/0002I` confirmo que el payload horario incluye `vv`, `vmax`, `dv` y `dmax`, ademas de `prec`, `ta` y `hr`; en esa muestra `vv/vmax` venian en m/s y `dv/dmax` en grados reales (`84.0`, `96.0`, `344.0`, etc.). El endpoint diario `/opendata/api/valores/climatologicos/diarios/datos/.../todasestaciones` sirve para backfill manual de dias cerrados cuando AEMET lo publica; tiene retraso, no trae coordenadas y requiere unir con `inventarioestaciones/todasestaciones`. `scripts/aemet-backfill-30-days.py` genera localmente `Aemet_incremental.csv`, `estacions_aemet.csv` y `aemet_backfill_summary.json` en `tmp/aemet-backfill-<timestamp>/` por defecto, sin escribir `Data/`; acepta `--station-catalog` para conservar municipio/provincia/comarca ya enriquecidos y `--existing-incremental` para fusionar con un historico descargado de HA. Primera implementacion runtime: `rainmapper_core/create_aemet.py` genera `Aemet.csv`, `Aemet_current_daily.csv`, `Aemet_hourly_incremental.csv`, `estacions_aemet.csv` y `Aemet_incremental.csv`; `estacions_aemet.csv` preserva campos manuales `Comarca`, `Municipi` y `Provincia` si las coordenadas no cambian; `rainmapper_core/geocoding.py` centraliza el reverse geocoding usado por las fuentes existentes y AEMET; `create_aemet=false` por defecto en HA/local; `rainmapper_core.rainmapper` lo ejecuta como cuarta fuente opcional. Tras validar `0.2.108`, HA genera el Tomap/GeoJSON estandar con `--include-aemet true`, de modo que `/protected/maplibre/index.html`, Leaflet y Bokeh incluyen AEMET cuando existe `Aemet_incremental.csv`. `tomap.py` mantiene AEMET excluido por defecto para usos locales/controlados si no se pasa el flag. El publicador experimental `/local/rainmapper-maplibre-aemet/index.html` queda en codigo pero desactivado por `PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE = False`; retirarlo definitivamente cuando la ruta estandar quede validada. GeoJSON infiere `AEMET:` como `Source=AEMET`; MapLibre tiene AEMET en selector y creditos. Nota legal: al publicar datos AEMET en visores/exports, mostrar atribucion visible. Recomendacion inicial para MapLibre: `Fuente: AEMET` e `Informacion elaborada por Rainmapper a partir de datos de la Agencia Estatal de Meteorologia` en la ficha de estaciones AEMET, y una referencia agregada en el panel de creditos cuando el dataset cargado contenga datos AEMET. Desde la revision de atribuciones del 2026-06-23, MapLibre muestra atribucion especifica por fuente en cada popup, retira la fila generica `Source:` y anade creditos agregados para Meteocat, Meteoclimatic y Wunderground. Meteocat usa siempre texto en catalan: `Font: Generalitat de Catalunya. Departament de Territori, Habitatge i Transicio Ecologica. METEOCAT. Dades meteorologiques de la XEMA. Dades elaborades per Rainmapper.` Meteoclimatic usa castellano: `Fuente: Informacion elaborada por Rainmapper a partir de datos de Meteoclimatic (www.meteoclimatic.net)`. Wunderground usa ingles: `Source: Information elaborated by Rainmapper from Weather Underground data`. Meteoclimatic y Wunderground siguen como atribuciones conservadoras hasta encontrar/acordar texto legal exacto.
- Google Maps: `googlemaps` Python client y Bokeh `gmap`; clave en `GMAP_API_KEY`/`gmap_api_key`.
- Home Assistant Supervisor API: `web_server.py` usa `SUPERVISOR_TOKEN` para resolver informacion del addon.
- OpenTopoMap / Esri / OpenFreeMap / Terrarium DEM: proveedores de tiles/estilos/relieve para visores.
- Cloudflare/domain externo: usado operacionalmente para exponer HA/visor, pero no hay configuracion de Cloudflare versionada en el repo. Estado verificado el 2026-06-22: HTTP redirige a HTTPS, HSTS esta activo con `max-age=2592000; includeSubDomains`, `x-content-type-options: nosniff` aparece en las respuestas, `router.nomentero.com` redirige a Cloudflare Access y los fallbacks `leaflet.nomentero.com`/`maplibre.nomentero.com` tambien redirigen a Cloudflare Access tanto para `index.html` como para `data/01d.geojson`. `rainmap.nomentero.com/protected/maplibre/data/01d.geojson` devuelve `401 Authentication required` sin sesion. Para MapLibre protegido, Cloudflared debe apuntar a `http://<HA_IP>:8099`; mantener `rainmap.nomentero.com/protected/maplibre/index.html` como URL normal.

## Decisiones importantes ya tomadas
Resumen:

- Home Assistant se ejecuta en modo `serve` para mantener sidebar y webUI.
- Los datos historicos viven fuera del contenedor.
- Docker local en Mac se conserva como entorno de pruebas.
- Bokeh, Leaflet y MapLibre conviven; Leaflet y MapLibre se mantienen publicados de momento.
- Los visores nuevos usan GeoJSON generado desde `Tomap`.
- Las estaciones anomalas se ignoran en GeoJSON mediante fichero manual, sin borrar historico.
- Wunderground usa `max_threads=3` como valor operativo recomendado en HA/RPi tras validacion manual; `1` queda como modo conservador de diagnostico.
- El repo GitHub deberia quedar privado salvo ventanas operativas para que HA detecte updates; auditoria real del 2026-06-24 indica que ahora mismo esta publico (`private=false`, `visibility=public`). El paquete GHCR debe quedar accesible para HA. `0.2.120/latest` esta publicado con digest multi-arch `sha256:9efce7f58351b4c1f3634cc7ce33e9ef389310544dc887caa199fd310f0ab2ad`; GHCR conserva tambien `0.2.119`, `0.2.118` y `0.2.117` como rollback remoto hasta validar la nueva version. Tras validar `0.2.120` en HA, volver a poner el repo privado y limpiar versiones remotas antiguas conservando solo la version vigente, `latest` y las entradas auxiliares del mismo push multi-arch.
- Los fallbacks externos Leaflet/MapLibre se mantienen disponibles como emergencia, pero protegidos por Cloudflare Access.

Detalle en [decisions.md](decisions.md).

## Riesgos antes de continuar
- No borrar ni limpiar `Data`, `Tomap`, `Plots`, `/share/rainmapper` ni `docker-data` sin backup explicito.
- No modificar `rainmapper-app/run.sh` sin revisar persistencia y symlinks.
- No modificar `rainmapper_core/rainmapper.py` sin revisar impacto en historicos incrementales; ya no existe wrapper raiz `Rainmapper.py`.
- Validar que `rainmapper-app/app` siga conteniendo solo codigo especifico de HA y que el build HA use la raiz del repo; usar `./scripts/smoke-test.sh`.
- Todo script o modulo nuevo (`.py`, `.sh` u otros) debe incluir documentacion interna en ingles: cabecera de proposito y comentarios/docstrings breves en funciones o bloques no obvios.
- Cada nueva funcionalidad visible de MapLibre debe actualizar tambien la ayuda del visor (`?`) y sus traducciones en `rainmapper_core/viewers/maplibre-viewer/translations.json` para ES/EN/CA. El test `tests/test_maplibre_translations.py` valida que las claves existan en los tres idiomas, pero no sustituye la revision humana del contenido.
- No introducir API keys reales en Git.
- No volver a hacer publico el repo salvo necesidad operativa concreta y temporal. Si se hace privado tambien GHCR, Home Assistant necesitara autenticacion para descargar imagenes.
- Tras cada nueva version HA validada, borrar de GHCR las versiones remotas antiguas para no acumular basura en GitHub Packages. No borrar en GHCR la version que declare `rainmapper-app/config.yaml` ni sus entradas auxiliares multi-arch sin confirmar antes que HA ya usa otra version validada.
- No basar una futura app comercial en datos Wunderground obtenidos por scraping ni por PWS Data Feed sin permiso/acuerdo escrito de The Weather Company.
- Validar cambios de visores en movil real, especialmente iPhone.
- Ejecutar `./scripts/smoke-test.sh` antes de cerrar cambios relevantes.
- Antes de tocar pandas o escritura CSV, usar `./scripts/backup-data.sh` y `./scripts/check-history.py` sobre una copia.

## Proximo paso recomendado
Validado manualmente en HA hasta `0.2.113`: el visor MapLibre protegido restaura settings por dispositivo desde `devices.json`, guarda cambios solo al cerrar Settings tras modificar controles del panel, cambia mapa desde el boton rapido de layers sin persistir `map_style`, mantiene la separacion entre periodo visible y periodo preferido, permite guardar explicitamente `map_view` como vista predeterminada sin escribir continuamente al mover el mapa, soporta selector de idioma ES/EN/CA, muestra controles moviles compactos, la WebUI `Users` refresca/busca correctamente sin perder scroll, AEMET esta integrado en el visor protegido estandar, no duplica diarios por tipos mixtos en `local_date`, y `source_status.json` incluye `stations`. `0.2.113` queda validada/dada por buena en HA con ayuda movil MapLibre ajustada y badges de fuente en dos lineas. El 2026-06-24 se publico `0.2.114` en GHCR con digest multi-arch `sha256:24736a7b4f6b9a64a65a586cb41ed7b378efc2cbd8c9e0634b0152cdad49a9d1`; despues se valido que preserva el backfill manual AEMET tras un run AEMET. `0.2.119` queda publicada en GHCR con digest multi-arch `sha256:d6220a7ce7b186b7c598cbadadcb2f11c3d3bf41de3b33c5272dfcf2d993fe95`, con alineacion de subcolumnas en historial MapLibre, diagnostico/contadores AEMET 429 y botones `Update only` por fuente en WebUI. `0.2.120` queda publicada en GHCR con digest multi-arch `sha256:9efce7f58351b4c1f3634cc7ce33e9ef389310544dc887caa199fd310f0ab2ad`, con experimento MapLibre heatmap en ruta separada. `0.2.121` queda publicada en GHCR con digest multi-arch `sha256:dcc820f91e3f05d0d80dbe43f55213c821ea75292a3833f37fb38934ca5bb0aa`, con heatmap mas amplio, radio ajustable, heatmap por encima de puntos y filtro de fuentes respetado. `0.2.122` queda publicada en GHCR con digest multi-arch `sha256:aeb39767d061671d1b75d810115d93e13dc9cd0776035e77f184ed3a577ee18e`, con lectura de incrementales usando inferencia completa para evitar `DtypeWarning` de pandas. `0.2.123` queda publicada en GHCR con digest multi-arch `sha256:89118fb88892ef2910eea09b8e72c3c460040d0d24d39b73801cd82d2a81a590`, con pestaña `Heatmap` en Settings para ajustar metrica, opacidad, radio, intensidad y curva de peso en la ruta experimental. `0.2.124` queda publicada en GHCR con digest multi-arch `sha256:9586b5c682bc1b170798d927c7abbdbbaa7269fe9204da06baa5b9b758d4cbbc`, con promocion controlada del heatmap al visor protegido solo para usuarios `admin`, ocultacion completa para no-admin y persistencia por `device_id` solo en admin protegido. Siguiente paso recomendado: instalar/actualizar `0.2.124` en HA, validar admin vs usuario no-admin, confirmar que desaparece el warning de pandas y despues cerrar la ventana operativa poniendo el repo privado y limpiando GHCR remoto.

Actualizacion del 2026-06-24: tras subir el backfill AEMET de `tmp/aemet-backfill-0.2.114-output/Aemet_incremental.csv`, un run AEMET en HA preservo el rango `20260525`-`20260624`, no creo duplicados y relleno viento en filas recientes generadas desde horario. `0.2.120` queda publicada en GHCR con digest multi-arch `sha256:9efce7f58351b4c1f3634cc7ce33e9ef389310544dc887caa199fd310f0ab2ad` y commit `049ad83` pusheado a `origin/inicial`. `0.2.121` queda publicada en GHCR con digest multi-arch `sha256:dcc820f91e3f05d0d80dbe43f55213c821ea75292a3833f37fb38934ca5bb0aa` y commit `db0062c` pusheado a `origin/inicial`. `0.2.122` queda publicada en GHCR con digest multi-arch `sha256:aeb39767d061671d1b75d810115d93e13dc9cd0776035e77f184ed3a577ee18e` y commit `ca4db1a` pusheado a `origin/inicial`. `0.2.123` queda publicada en GHCR con digest multi-arch `sha256:89118fb88892ef2910eea09b8e72c3c460040d0d24d39b73801cd82d2a81a590` y commit `2d9be32` pusheado a `origin/inicial`. `0.2.124` queda publicada en GHCR con digest multi-arch `sha256:9586b5c682bc1b170798d927c7abbdbbaa7269fe9204da06baa5b9b758d4cbbc` y commit `52b6ea6` pusheado a `origin/inicial`. Siguiente paso recomendado: instalarla/validarla en HA y despues volver a poner el repo privado y limpiar GHCR remoto.

Backfill manual AEMET pendiente/operativo: el 2026-06-24 se genero inicialmente `tmp/aemet-backfill-30d-through-20260620/Aemet_incremental_merged_for_HA.csv` uniendo el backfill diario AEMET (`2026-05-22` a `2026-06-20`) con `tmp/aemet-backfill-30d-through-20260620/Aemet_incremental_from_HA.csv` (`2026-06-23` y `2026-06-24`). Ese resultado tuvo 25.067 filas, 851 estaciones y 0 duplicados por `Codi Estació` + `Data Local`, pero un run HA posterior lo machaco por el bug corregido en `0.2.114`. Tras publicar `0.2.114`, se preparo un nuevo fichero local listo para subida manual: `tmp/aemet-backfill-0.2.114-output/Aemet_incremental.csv`, generado con `tmp/aemet-backfill-0.2.114-input/estacions_aemet.csv` y `tmp/aemet-backfill-0.2.114-input/Aemet_incremental_from_HA.csv`. Resultado: 22.774 filas, 850 estaciones con datos, 0 duplicados estacion/dia, rango `20260525`-`20260624`, y conserva exactamente las 1.600 filas del incremental HA de entrada para `20260623` y `20260624`. El endpoint diario de AEMET siguio sin aportar `20260621` y `20260622`. El helper divide rangos en tramos de 15 dias (`MAX_DAILY_RANGE_DAYS = 15`) por el limite de AEMET; `tests/test_aemet_backfill_script.py` cubre el caso de 30 dias dividido en dos chunks.

Incidente AEMET detectado el 2026-06-24 tras un run HA posterior: `Aemet_incremental.csv` volvio a perder el backfill manual y aparecieron filas duplicadas/horarias por estacion/dia. Causa localizada en `rainmapper_core/create_aemet.py`: `run_update()` reconstruia y sobrescribia `Aemet_incremental.csv` solo desde `Aemet_hourly_incremental.csv`; el backfill diario no vive en el historico horario. Fix publicado desde `0.2.114`: leer el `Aemet_incremental.csv` existente, fusionarlo con el diario reconstruido desde horas, deduplicar por `Codi Estació` + `Data Local` y hacer que la fila reconstruida desde horas recientes gane cuando hay conflicto. Tests de regresion anadidos en `tests/test_create_aemet.py`.

Nueva linea de trabajo AEMET iniciada: la fuente ya existe como opcion desactivada por defecto y fue probada contra la API real en `tmp/aemet-flow-test/` sin tocar historicos reales; el flujo temporal completo genero `estacions_aemet.csv`, `Aemet_incremental.csv`, Tomap y GeoJSON con `Source=AEMET`. Tras validar `0.2.108`, se decide promover AEMET al dataset estandar: `0.2.109` pasa `--include-aemet true` en los comandos HA de mapas y el visor protegido deja de depender de una ruta experimental separada. La ruta experimental `/local/rainmapper-maplibre-aemet/index.html` no se borra aun: queda desactivada por flag en `web_server.py` para poder reactivarla si hiciera falta volver al modo test, y hay tarea pendiente para eliminarla definitivamente. El reverse geocoding AEMET ya esta integrado con el helper comun y se ejecuta como las otras fuentes cuando una estacion es nueva, le falta municipio/provincia o cambian sus coordenadas. En `0.2.106`, MapLibre muestra atribucion por fuente en los popups y creditos, incluyendo Meteocat en catalan con el formato Generalitat/XEMA, y mantiene Meteoclimatic/Wunderground como atribuciones conservadoras. En `0.2.107`, el popup AEMET oculta visualmente el prefijo interno `AEMET:` y se pulen creditos AEMET/Meteoclimatic con `Fuente:`. En `0.2.108`, se corrige el duplicado de `Aemet_incremental.csv` causado por tipos mixtos en `local_date`, se anade `stations` a `source_status.json` y queda validada/dada por buena en HA. En `0.2.110`, la atribucion visible cambia de datos modificados a datos elaborados por Rainmapper para Meteocat y explicita que AEMET se elabora a partir de datos de la Agencia Estatal de Meteorologia. Despues se alinea Meteoclimatic/Wunderground al mismo criterio: Meteoclimatic en castellano y Wunderground en ingles, indicando que Rainmapper elabora la informacion a partir de datos de esas fuentes. Queda documentada como mejora futura la normalizacion de todos los codigos internos con prefijo de fuente para retirar inferencias fragiles; no abordarla sin plan de migracion y backups de historicos.

## Prompt recomendado para nueva sesion de Codex
"Lee primero docs/codex-handoff.md. Después consulta docs/architecture.md, docs/todo.md y docs/decisions.md. No modifiques código todavía. Primero resume el objetivo de la app, el estado actual, los ficheros clave, lo que funciona, lo que falta y el siguiente paso recomendado."
