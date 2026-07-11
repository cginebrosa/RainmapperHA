# Architecture

## Workspace real

La ruta de trabajo valida es `/Users/carlosginebrosa/Developer/RainmapperHA`. La copia antigua en iCloud/Mobile Documents no debe usarse para desarrollo, validacion ni commits porque puede estar desfasada.

## Resumen tecnico
RainmapperHA es una aplicacion Python empaquetada en Docker y Home Assistant. El core descarga y normaliza datos meteorologicos en CSV. Una segunda capa genera GeoJSON para visores modernos y, si se activa legado publico, mapas HTML clasicos con Bokeh. La app de Home Assistant anade webUI, schedule interno, MapLibre protegido, publicacion legacy opcional a `/config/www` e integracion con ingress/sidebar.

La arquitectura actual no separa completamente dominio, infraestructura y UI: todavia hay scripts grandes, aunque la duplicidad fisica entre raiz y `rainmapper-app/app` ya fue retirada. Aun asi, el flujo esta estabilizado y funciona como pipeline de ficheros.

## Stack tecnologico
- Lenguaje: Python 3.11, JavaScript estatico, HTML, CSS, shell.
- Runtime Python: `python:3.11-slim` en Docker.
- Gestor de paquetes Python: `pip` con `requirements.txt`.
- Sistema de build: Dockerfile y Docker Compose.
- Librerias Python principales: pandas, numpy, requests, BeautifulSoup, lxml, googlemaps, bokeh, pytz, Pillow.
- Librerias UI: Leaflet 1.9.4 via CDN, MapLibre GL JS 4.7.1 via CDN.
- Librerias de estado JS: no detectadas.
- Librerias de routing JS: no detectadas.
- Librerias de validacion: pendiente de confirmar; no se ha detectado framework dedicado.
- Librerias HTTP/API: `requests`, `rainmapper_core.sources.sodapy_local`, `googlemaps`.
- Librerias de testing: `unittest` de la libreria estandar en `tests/`; no se ha detectado `pytest`.
- Base de datos: no hay base de datos detectada; persistencia por CSV.
- Despliegue: GitHub como repositorio de app HA y GHCR como registry de imagenes preconstruidas; Home Assistant descarga `ghcr.io/cginebrosa/rainmapperha:<version>` cuando existe la imagen publicada.

## Estructura de carpetas
- `rainmapper-app/`: paquete de Home Assistant.
- `rainmapper-app/app/`: codigo especifico de Home Assistant que entra en la imagen HA (`web_server.py`, `mushroom_catalogs_ui.py`, `mushroom_profiles_ui.py`, `mushroom_gis_mappings_ui.py`). El core, store/validador de setas y visores se copian desde las rutas canonicas de raiz durante el build.
- `rainmapper-local/`: runtime Docker local y scripts especificos de pruebas locales.
- `rainmapper-local/docker-compose.yml`: compose local con el servicio historico `rainmapper` y el servicio `rainmapper-ha-ui`, que levanta la WebUI HA contra `docker-data/` para pruebas locales sin tocar Home Assistant.
- `rainmapper_core/viewers/leaflet-viewer/`: fuente canonica del visor Leaflet.
- `rainmapper_core/viewers/maplibre-viewer/`: fuente canonica del visor MapLibre.
- `scripts/`: utilidades versionadas de desarrollo; contiene `smoke-test.sh`, `docker-offline-functional-test.sh`, `backup-data.sh`, `build-push-ha-image.sh`, `check-history.py`, `compare-tomap-builder.sh`, `aemet-backfill-30-days.py`, `reconstruct-mushroom-gis-mappings.py`, `reconstruct-mushroom-observation-context.py`, `build-mushroom-observation-features-v0.py`, `build-mushroom-learned-model-v0.py`, `build-mushroom-profile-v0-candidate.py`, `audit-mushroom-profile-v0-source.py` y `validate-mushroom-data.py`.
- `local_update.sh`: wrapper compatible de raiz hacia `rainmapper-local/local_update.sh`; runner local solo update, util para refrescar descargas actuales e incrementales sin reconstruir `Tomap` ni publicar visores.
- `rainmapper_core/sources/meteoclimatic_local/`: cliente local Meteoclimatic.
- `rainmapper_core/sources/sodapy_local/`: copia local/adaptada de Socrata client.
- `rainmapper_core/sources/wunderground/`: parser/scraper Wunderground.
- `rainmapper_core/create_aemet.py`: cliente/normalizador AEMET OpenData.
- `rainmapper_core/config/`: configuracion Python compartida (`const`, `config`, `config_wunderground`) usada por Docker local y HA.
- `Data/`: CSV historicos locales, ignorados por Git.
- `Tomap/`: CSV intermedios para mapas, ignorados por Git.
- `Plots/`: HTML Bokeh generados, ignorados por Git.
- `docker-data/`: volumenes locales Docker, ignorados por Git.
- `docs/`: documentacion de continuidad.

## Punto de entrada de la aplicacion
Hay varios entry points segun entorno:

- Docker local: `rainmapper-local/Dockerfile` ejecuta `/app/run.sh`, copiado desde `rainmapper-local/run.sh`. La raiz conserva wrappers de compatibilidad.
- Home Assistant: `rainmapper-app/Dockerfile` ejecuta `/run.sh`.
- Core de datos: `python -m rainmapper_core.rainmapper` como entrypoint canonico; implementacion en `rainmapper_core/rainmapper.py`.
- Paquete compartido de core: `rainmapper_core/`.
- Configuracion Python compartida: `rainmapper_core/config/`, sin wrappers raiz.
- Upsert de historicos incrementales: `rainmapper_core/incremental_upsert.py`.
- Reconstruccion Tomap sin descarga: `rainmapper_core/tomap.py` como entrypoint canonico ejecutable con `python -m rainmapper_core.tomap`.
- Mapas Bokeh: `python -m rainmapper_core.bokeh_maps` como entrypoint canonico; implementacion en `rainmapper_core/bokeh_maps.py`.
- GeoJSON: `rainmapper_core/geojson.py` como entrypoint canonico ejecutable con `python -m rainmapper_core.geojson`.
- WebUI HA: `rainmapper-app/app/web_server.py`.
- Flujo setas v0: wrappers raiz `mushroom_gis_mappings_rebuild.sh`, `mushroom_observation_context_rebuild.sh`, `mushroom_observation_features_v0_build.sh` y `mushroom_learned_model_v0_build.sh`.
- Leaflet: `rainmapper_core/viewers/leaflet-viewer/index.html` y `app.js`, desde la ruta canonica.
- MapLibre: `rainmapper_core/viewers/maplibre-viewer/index.html` y `app.js`, desde la ruta canonica.

## Flujo principal
1. Se arrancan Docker local o app HA.
2. El wrapper prepara rutas y variables de entorno.
3. En HA, `serve` arranca `web_server.py`.
4. El usuario pulsa `Run update`, `Generate maps` o `Run all`, o el schedule dispara una accion.
5. `python -m rainmapper_core.rainmapper` descarga datos y actualiza CSV historicos/incrementales.
6. `python -m rainmapper_core.tomap` reconstruye CSV `Tomap` para los periodos acumulados desde historicos incrementales sin descargar datos nuevos, delegando en `rainmapper_core/tomap.py`.
7. En `MODE=maps`, `MODE=all` y `Generate maps`, `python -m rainmapper_core.tomap` reconstruye `Tomap` antes de generar salidas publicables.
8. Si `publish_to_www=true`, `python -m rainmapper_core.bokeh_maps` genera HTML Bokeh en `Plots`.
9. `python -m rainmapper_core.geojson` genera GeoJSON desde `Tomap` delegando en `rainmapper_core/geojson.py`.
10. `web_server.py` deja GeoJSON en `PublicData` y sirve MapLibre protegido; solo publica HTML/visores legacy en `/config/www` si `publish_to_www=true`.
11. Home Assistant debe usar como visor operativo `/protected/maplibre/index.html` y datos `/protected/maplibre/data/*`. Bokeh, Leaflet publico y visores publicos antiguos son legado opcional bajo `/local/...` cuando `publish_to_www=true`.

## Componentes, modulos o capas principales

### Core de descarga y datos
- Ruta: `rainmapper_core/rainmapper.py`; entrypoint `python -m rainmapper_core.rainmapper`.
- Responsabilidad: descarga Meteocat, Meteoclimatic, Wunderground y AEMET opcional; actualiza historicos; escribe estado por fuente; metricas Wunderground.
- Dependencias: pandas, requests, BeautifulSoup, googlemaps y helpers de fuente en `rainmapper_core/sources/`.
- Relacion: alimenta `rainmapper_core.bokeh_maps` y `rainmapper_core.geojson`. Desde `0.2.71`, registra en `Data/source_status.json` el resultado de cada fuente y puede continuar con incrementales previos si una fuente falla completamente. El estado por fuente incluye duraciones reales medidas con temporizadores locales; no usar los logs `start_count/end_count` como metrica fiable cuando hay paralelismo porque comparten un temporizador global.

### Upsert incremental
- Ruta: `rainmapper_core/incremental_upsert.py`, sin wrapper raiz.
- Responsabilidad: combinar descargas actuales con historicos `Data/*_incremental.csv` sin crear duplicados por `Codi Estació` + `Data Local`.
- Regla: la fila nueva manda para valores no nulos; si la descarga nueva trae `NaN`, se conserva el valor antiguo no nulo para no perder campos complementarios como temperatura/humedad de Meteocat.
- Relacion: usado por `rainmapper_core.rainmapper` en Meteocat, Meteoclimatic y Wunderground antes de reescribir los CSV incrementales.

### Configuracion Python compartida
- Ruta: `rainmapper_core/config/`, sin wrappers raiz.
- Responsabilidad: defaults de ejecucion, rutas runtime, flags de fuentes y configuracion del parser Wunderground.
- Relacion: `rainmapper_core/rainmapper.py`, `rainmapper_core.bokeh_maps`, `rainmapper_core.tomap` y helpers Wunderground importan ya desde `rainmapper_core.config`.

### Generador Bokeh
- Ruta: `rainmapper_core/bokeh_maps.py`; entrypoint `python -m rainmapper_core.bokeh_maps`.
- Responsabilidad: leer `Tomap` y generar HTML Bokeh en `Plots`.
- Dependencias: Bokeh, pandas, Google Maps key.
- Relacion: salida legacy generada/publicada solo cuando `publish_to_www=true`.

### Reconstructor Tomap
- Ruta: `rainmapper_core/tomap.py`, sin wrappers raiz/HA; ejecutable con `python -m rainmapper_core.tomap`.
- Responsabilidad: leer historicos `Data/*_incremental.csv` y reconstruir `Tomap/*.csv` y `LastXX_rains.csv` sin ejecutar descargas.
- Dependencias: pandas, pathlib, constantes locales.
- Relacion: `run.sh`, `rainmapper-app/run.sh` y `Generate maps` de la webUI lo ejecutan antes de `python -m rainmapper_core.bokeh_maps` y `python -m rainmapper_core.geojson`. Es la ruta activa de generacion `Tomap`; el bloque ejecutable inline y los helpers legacy de `Rainmapper.py` ya fueron retirados. Los Tomap de periodo agregan lluvia, temperatura/humedad max/min, viento medio, racha y direccion media circular cuando esas columnas existen en los incrementales. `LastXX_rains.csv` expone detalle diario con lluvia, temperatura, humedad y viento para popups.

### Conversor GeoJSON
- Ruta: `rainmapper_core/geojson.py`, sin wrappers raiz/HA; ejecutable con `python -m rainmapper_core.geojson`.
- Responsabilidad: convertir CSV `Tomap` a GeoJSON por periodo, inferir `Source`, aplicar `ignore_stations_tomap.txt` y escribir metadata de generacion.
- Dependencias: pandas, json, pathlib.
- Relacion: produce datos para MapLibre protegido y, si `publish_to_www=true`, para Leaflet legacy.

### WebUI HA
- Rutas: `rainmapper-app/app/web_server.py`, `rainmapper-app/app/mushroom_catalogs_ui.py`, `rainmapper-app/app/mushroom_profiles_ui.py` y `rainmapper-app/app/mushroom_gis_mappings_ui.py`.
- Responsabilidad: servidor HTTP, webUI, acciones, schedule, publicacion, logs, status, enable/disable estaciones, rutas protegidas de MapLibre y pantallas server-rendered de mantenimiento de setas.
- Dependencias: stdlib HTTP, subprocess, threading, json, pathlib.
- Relacion: `web_server.py` orquesta rutas, POST, persistencia, validacion y publicacion; los modulos `mushroom_*_ui.py` concentran render server-side de pantallas grandes para evitar que `web_server.py` siga creciendo. En HA se mantiene `ingress_port: 8099` para la webUI y tambien se publica `8099/tcp` como puerto de app para que Cloudflared pueda apuntar a `http://<HA_IP>:8099` sin usar `/local`.

### Wrapper HA
- Ruta: `rainmapper-app/run.sh`.
- Responsabilidad: leer opciones HA, crear persistencia, symlinks, exportar variables, arrancar modo.
- Dependencias: shell, Python para leer JSON de opciones.
- Relacion: entrypoint del contenedor HA.

### Wrapper Docker local
- Ruta: `rainmapper-local/run.sh`; `run.sh` en raiz es un wrapper compatible.
- Responsabilidad: ejecutar Rainmapper localmente en Docker y mapear variables cortas/largas.
- Dependencias: shell, Python para calculo schedule.
- Relacion: entorno seguro de pruebas en Mac. En `maps/all`, ejecuta `python -m rainmapper_core.geojson` y, si corresponde por configuracion legacy, `python -m rainmapper_core.bokeh_maps`, dejando GeoJSON actualizado en `docker-data/PublicData` para los visores locales.

### Runner local completo
- Ruta: `rainmapper-local/local_all.sh`; `local_all.sh` en raiz es un wrapper compatible.
- Responsabilidad: automatizar la secuencia de prueba local: `docker compose build rainmapper`, `docker compose run --rm -e MODE=all rainmapper` y servidor HTTP local para abrir visores.
- Dependencias: Docker Compose y `python3`.
- Relacion: acceso rapido a `http://127.0.0.1:8080/rainmapper_core/viewers/maplibre-viewer/` y `http://127.0.0.1:8080/rainmapper_core/viewers/leaflet-viewer/` tras regenerar datos locales.

### WebUI HA local
- Ruta: `rainmapper-local/docker-compose.yml`, servicio `rainmapper-ha-ui`.
- Responsabilidad: levantar la WebUI de Home Assistant en local usando `rainmapper-app/Dockerfile` y montando `docker-data/` como `/share/rainmapper`.
- Puerto local: `http://127.0.0.1:8101`.
- Relacion: permite cargar observaciones reales/historicas de setas, importar EXIF y probar flujos de mantenimiento sin escribir en la instalacion HA real. Usa `rainmapper-local/options.local-ha-ui.json` como opciones de add-on y `tmp/mushroom-lab/runtime/config-www` como `/config/www`; esa ruta de `tmp/` es runtime local, no fuente operativa del modelo v0.
- Estado verificado 2026-07-05: `docker compose -f rainmapper-local/docker-compose.yml ps` no muestra servicios activos. Los datos locales siguen preservados en `docker-data/`.

### Flujo de setas v0
- Rutas principales:
  - `rainmapper_core/mushroom_observation_context.py`
  - `rainmapper_core/mushroom_observation_features.py`
  - `rainmapper_core/mushroom_learned_model.py`
  - `rainmapper_core/mushroom_paths.py`
  - `scripts/reconstruct-mushroom-observation-context.py`
  - `scripts/build-mushroom-observation-features-v0.py`
  - `scripts/build-mushroom-learned-model-v0.py`
- Wrappers raiz:
  - `mushroom_observation_context_rebuild.sh`
  - `mushroom_observation_features_v0_build.sh`
  - `mushroom_learned_model_v0_build.sh`
- Responsabilidad: reconstruir contexto GIS/DEM/meteorologico de observaciones locales, unir features v0 y generar una salida aprendida descriptiva por especie.
- Contrato de rutas: `mushroom_paths.py` centraliza defaults (`mushroom-data/` o `/app/mushroom-data/`) y toda la copia operativa de setas bajo `/share/rainmapper/mushroom-data/`. En Docker local, `docker-data/` representa `/share/rainmapper`. `tmp/mushroom-lab/` queda reservado para pruebas locales explicitas, no para artefactos estables del modelo v0.
- Flujo reproducible: primero `./mushroom_observation_context_rebuild.sh`, despues `./mushroom_observation_features_v0_build.sh`, despues `./mushroom_learned_model_v0_build.sh`.
- Salidas locales principales: `docker-data/mushroom-data/mushroom_gis_observation_reconstruction.json`, `docker-data/mushroom-data/mushroom_observations_weather_features.json`, `docker-data/mushroom-data/mushroom_observation_features_v0.json`, `docker-data/mushroom-data/mushroom_model_v0.json`, `docker-data/mushroom-data/mushroom_model_v0_state.json` y reportes bajo `docker-data/mushroom-data/reports/`.
- Media operativa: las fotos reducidas de observaciones se guardan bajo
  `docker-data/mushroom-data/media/observation-photos/<year>/<nombre-original>`
  en local y bajo `/share/rainmapper/mushroom-data/media/observation-photos/`
  en HA. Son datos persistentes ignorados por Git y deben copiarse junto con
  `mushroom_observations.json` cuando se quiera replicar el estado local en HA.
- Relacion con perfiles: no modifica `mushroom-data/mushroom_profiles.json`. La WebUI muestra la evidencia para revision humana y futura promocion manual.
- WebUI: el rebuild completo desde Observaciones arranca un job en segundo plano y expone progreso por `/api/mushrooms/rebuild-status`, con tiempos y ETA para medir coste real en HA sin congelar la pagina.
- Diferencia con `mushroom_gis_mappings_rebuild.sh`: ese wrapper reconstruye candidatos de mappings para capas GIS, no reconstruye observaciones ni modelos por especie.

### Runner local solo mapas
- Ruta: `rainmapper-local/local_maps.sh`; `local_maps.sh` en raiz es un wrapper compatible.
- Responsabilidad: automatizar la secuencia de prueba local sin descargar datos nuevos: `docker compose build rainmapper`, `docker compose run --rm -e MODE=maps rainmapper` y servidor HTTP local para abrir visores.
- Dependencias: Docker Compose y `python3`.
- Relacion: permite iterar rapido cambios de Leaflet/MapLibre. Desde la extraccion conservadora de `rainmapper_core.tomap`, `MODE=maps` reconstruye `Tomap` desde `docker-data/Data` antes de generar Bokeh/GeoJSON; si no hay lecturas para el dia actual, el periodo de 1 dia puede quedar vacio aunque existan `Tomap` anteriores.

### Comparador Tomap
- Ruta: `scripts/compare-tomap-builder.sh`.
- Responsabilidad: reconstruir `Tomap` en un directorio temporal con `python -m rainmapper_core.tomap` y compararlo con `docker-data/Tomap`.
- Relacion: sirve para validar que el builder reproduce los `Tomap` actuales sin sobrescribirlos; despues de retirar el bloque inline de `Rainmapper.py`, ya no compara contra una generacion legacy nueva.

### Empaquetado HA sin copia de core
- Ruta: `rainmapper-app/Dockerfile`, `scripts/build-push-ha-image.sh` y checks de empaquetado en `scripts/smoke-test.sh`.
- Responsabilidad: construir la imagen HA desde la raiz del repositorio, copiando `rainmapper_core/`, `mushroom-data/`, `scripts/validate-mushroom-data.py`, wrappers raiz, configuracion compartida y los modulos HA de `rainmapper-app/app/`.
- Relacion: `rainmapper-app/app` queda reservado para codigo especifico de HA; el smoke test falla si vuelven a aparecer copias de core no permitidas en esa carpeta.

### Leaflet viewer
- Ruta canonica: `rainmapper_core/viewers/leaflet-viewer/`.
- En HA se publica directamente desde `/app/rainmapper_core/viewers/leaflet-viewer`.
- Responsabilidad: visor web movil basado en Leaflet y GeoJSON.
- Dependencias: Leaflet CDN, tiles raster.
- Relacion: publicado a `/local/rainmapper-leaflet`.

### MapLibre viewer
- Ruta canonica: `rainmapper_core/viewers/maplibre-viewer/`.
- En HA se publica directamente desde `/app/rainmapper_core/viewers/maplibre-viewer`.
- Responsabilidad: visor web principal con mapas vectoriales/raster, filtros cliente de estaciones, terreno 3D opcional y overlays calculados en cliente.
- Dependencias: MapLibre GL JS CDN, Esri raster Hybrid/Satellite, OpenTopoMap raster, OpenFreeMap y DEM externo Terrarium/Mapzen para terreno 3D, consultas puntuales de altitud y correccion DEM del IDW de temperatura.
- Relacion: los assets estaticos se siguen publicando en `/local/rainmapper-maplibre`, pero la ruta operativa recomendada en HA es `/protected/maplibre/index.html`; los GeoJSON se sirven por `/protected/maplibre/data/*` con autenticacion ligera. Satellite+ es la capa inicial recomendada; combina imagen Esri con orientacion vectorial OpenFreeMap. Desde `0.2.58`, Settings permite elegir mapa base, filtrar por lluvia minima y filtrar por fuente de estacion. Desde `0.2.71`, el filtro `Source` muestra badges de estado por fuente si existe `data/source_status.json`; en escritorio, la ficha de estacion tambien aparece por hover desde el umbral global `maplibre_hover_zoom` de HA, por defecto `6.0` y configurable con decimales, sin cambiar el comportamiento tactil de movil. En `0.2.81` la UI se moderniza con cabecera clara, controles flotantes, selector inferior de periodo, leyenda vertical dinamica y popups claros; el popup de estacion se mantiene/refresca al cambiar de periodo si la estacion sigue visible tras filtros. Los popups de estacion muestran resumen de lluvia, temperatura, humedad y viento del periodo, y un historial diario compacto cuando el GeoJSON incluye esos campos. El visor incluye un boton de orientacion norte que solo resetea el `bearing`. Los defaults globales del heatmap para dispositivos sin settings guardados se leen de HA (`maplibre_heatmap_weight_curve`, `maplibre_heatmap_opacity`, `maplibre_heatmap_radius`, `maplibre_heatmap_intensity`) y despues cada dispositivo puede sobrescribirlos en `devices.json` al guardar Settings. El terreno 3D se activa desde Settings, esta apagado por defecto y se reaplica al cambiar de estilo porque `setStyle` reemplaza las fuentes del mapa. Una pulsacion larga sobre el mapa consulta altitud DEM leyendo directamente el tile Terrarium externo y decodificando el pixel RGB, no mediante `queryTerrainElevation`; el disparador usa eventos MapLibre y `contextmenu` para funcionar tanto en local como servido desde HA.

### MapLibre client-computed overlays
- Ruta principal: `rainmapper_core/viewers/maplibre-viewer/app.js`.
- Responsabilidad: calcular en el navegador capas derivadas del GeoJSON ya cargado, sin anadir carga de calculo a la Raspberry Pi.
- Patron actual: la capa `IDW` usa los puntos visibles del periodo activo y calcula un GeoJSON `fill` para el viewport actual. El calculo se ejecuta en cliente, se refresca con debounce al terminar movimientos/zoom, y se limita al canvas visible mediante `map.unproject()`.
- Contrato de datos: los valores no numericos o ausentes se excluyen; lluvia cero es un valor valido para el promedio solo cerca de lluvia real, pero no crea area visible por si sola; temperaturas negativas son validas. El viento se trata temporalmente como escalar.
- Configuracion: los settings por dispositivo guardan activacion, opacidad, radio, calidad, suavizado y correccion de altitud. Los valores tecnicos viven en `rainmapper-app/config.yaml`: radios en km, radio maximo, tamano de celda por calidad, potencia IDW y gradiente termico.
- Correccion DEM: la correccion de altitud del IDW solo se aplica a metricas de temperatura. El navegador descarga tiles Terrarium/Mapzen acotados al viewport, decodifica la altitud DEM por celda y corrige cada estacion hacia esa altitud con el gradiente configurado. Si la metrica no es temperatura, no se muestra estado ni se aplica correccion. Si la correccion esta activada pero el DEM no puede cargarse o excede los limites conservadores de celdas/tiles, el visor vuelve al IDW normal y muestra el badge rojo `IDW sin DEM`; cuando la correccion DEM se usa, muestra el badge verde `IDW DEM`. Esta descarga/correccion ocurre en el navegador y no anade trabajo a la Raspberry Pi.
- Render: `IDW` se inserta como source/layer GeoJSON propios (`estimated-field`, `station-estimated-field`) y se mueve por encima de `station-circles` para que su opacidad sea real. Heatmap e IDW son modos visuales incompatibles.
- Refresco y rendimiento: `updateEstimatedFieldLayer()` centraliza el refresco. Mantiene una clave de calculo con periodo, revision de datos, metrica, escala, viewport, canvas, fuentes activas y parametros IDW; si la clave no cambia reutiliza el GeoJSON anterior y solo reaplica source/layer/opacidad. Mientras el estilo MapLibre no esta listo, solo permite un `idle` pendiente para no acumular callbacks. Los cambios que alteran datos filtrados llaman a `invalidateEstimatedFieldData()`.
- Reutilizacion futura: una capa calculada en cliente para el predictor de floradas de setas deberia seguir este mismo patron: permiso explicito, settings por dispositivo, parametros tecnicos en `config.yaml`, calculo limitado al viewport, cache por clave de calculo, debounce de eventos de mapa y separacion clara entre datos base observados y capa derivada.

## Modelo de datos
Persistencia por CSV:

- Historicos incrementales en `Data/*_incremental.csv`.
- Identidad logica de una fila incremental: `Codi Estació` + `Data Local`. Debe existir como maximo una fila por fuente/estacion/dia; `rainmapper_core.incremental_upsert` aplica esta regla.
- Listados/metadata de estaciones en `Data/estacions_*.csv`.
- CSV preparados para mapas en `Tomap/01_Tomap_Last_day.csv`, `02_Tomap_Last_week.csv`, etc.
- Ultimos registros en `Tomap/LastXX_rains.csv`; por defecto `Last30_rains.csv`, configurable con `RAINMAPPER_LAST_RAINS_HISTORY` o la opcion HA `last_rains_history`.
- Metricas Wunderground en `Data/metricas_wunderground.csv`.
- Estado de fuentes en `Data/source_status.json`, con entradas para Meteoclimatic, Meteocat, Wunderground y AEMET. Estados actuales: `OK`, `DISABLED`, `STALE`, `NOK` y `PENDING`. `STALE` indica que la fuente fallo pero se reutilizo incremental previo. El payload puede incluir `duration_seconds`, `started_at`, `finished_at`, `rows`, `stations` y `timings`; los subtiempos actuales se usan especialmente para Meteocat.
- GeoJSON generados en `PublicData/*.geojson`. MapLibre protegido los consume desde `/protected/maplibre/data/*` para exigir login. Leaflet recibe copia publica en `/local/rainmapper-leaflet/data` solo cuando `publish_to_www=true`.

Campos relevantes detectados o usados:

- `Codi Estació` / codigo de estacion.
- `Source` en GeoJSON, inferido por `rainmapper_core.geojson` desde el codigo de estacion: `AEMET:` para AEMET, `ES...` con longitud minima 15 para Meteoclimatic, `I...` para Wunderground, codigos de longitud 2 para Meteocat, resto `Unknown` con aviso en stdout.
- `Latitud`, `Longitud`.
- lluvia acumulada por periodo.
- municipio/provincia/altitud.
- temperatura/humedad max/min de periodo cuando existe en incrementales (`max_temp_celsius`, `min_temp_celsius`, `max_humidity_percent`, `min_humidity_percent`).
- viento normalizado opcional en km/h y grados (`wind_avg_kmh`, `wind_min_kmh`, `wind_max_kmh`, `wind_gust_kmh`, `wind_direction_deg`, `wind_gust_direction_deg`, `wind_observation_count`, `wind_source_height_m`). Los datos vacios significan "no disponible", no calma ni direccion norte.
- historico diario para popup (`Data_Pluja_XX`, `Pluja_Diaria_XX`, `Temp_Max_XX`, `Temp_Min_XX`, `Hum_Max_XX`, `Hum_Min_XX`, `Wind_Avg_XX`, `Wind_Dir_XX`, `Wind_Gust_XX`, `Wind_Gust_Dir_XX`, `Wind_Max_XX`, `Wind_Min_XX`, `Wind_Obs_XX`). La configuracion por defecto genera hasta 30 registros, `last_rains_history` permite cambiarlo en HA, y los visores detectan dinamicamente cuantos hay en el GeoJSON.

Schemas completos: pendiente de confirmar en detalle leyendo todos los CSV y funciones pandas.

## Gestion de estado

### Autenticacion ligera MapLibre
- Usuarios manuales en `/share/rainmapper/users.json`, con `username`, `name`, `email`, `password`, `role`, `enabled`, `max_devices`, `must_change_password`, `can_use_heatmap`, `can_use_layer_metrics` y `can_use_estimated_field`. `username` es el identificador de login; `name` es el nombre de la persona; `email` es contacto.
- En HA, `run.sh` crea `users.json` desde `/app/users.example.json` si no existe `users.json`; no sobrescribe usuarios existentes.
- `users.json` es el unico formato de usuarios soportado; no hay formato alternativo ni ruta de migracion.
- Dispositivos y sesiones en `/share/rainmapper/devices.json`, generado por la app como JSON vacio si no existe.
- Cada entrada de `/share/rainmapper/devices.json` puede incluir `settings` del visor MapLibre para ese `device_id`. Los campos saneados por el backend en `rainmapper-app/app/web_server.py` son `period`, `min_rain_mm`, `map_style`, `language`, `last_rains_history`, `station_sources`, `terrain_enabled`, `terrain_exaggeration`, `layer_metric`, `heatmap_enabled`, `heatmap_opacity`, `heatmap_radius_scale`, `heatmap_intensity_scale`, `heatmap_weight_curve`, `estimated_field_enabled`, `estimated_field_opacity`, `estimated_field_radius`, `estimated_field_quality`, `estimated_field_smoothing`, `estimated_field_altitude_correction` y `map_view`. El backend solo permite leer/escribir esos settings para el dispositivo autenticado mediante `/auth/device-settings` y sanea los valores antes de persistirlos.
- Roles soportados: `free`, `basic`, `pro` y `admin`.
- Limites por defecto: `free=1`, `basic=2`, `pro=3`, `admin=0`; `0` significa dispositivos ilimitados. `max_devices` puede sobrescribir el limite por usuario.
- `can_use_heatmap` autoriza el boton `Heatmap` y la pestana/seccion `Heatmap` en Settings; `can_use_layer_metrics` autoriza el boton rapido de metrica/capa y el selector `Layer metric`; `can_use_estimated_field` autoriza el boton `IDW` y la pestana/seccion `IDW` en Settings. Si faltan en usuarios existentes, se aplican defaults compatibles: usuarios `admin` con permisos activos y resto de roles sin ellos. Al crear usuarios `admin`, la WebUI activa estos permisos por defecto.
- Limitacion consciente: estos permisos estan embebidos ahora en cada usuario porque solo hay pocas funcionalidades protegidas. Al existir ya tres flags (`can_use_heatmap`, `can_use_layer_metrics`, `can_use_estimated_field`), revisar la arquitectura hacia perfiles/tipos de usuario con permisos declarados en un JSON separado, manteniendo `users.json` para identidad y overrides opcionales por usuario antes de seguir anadiendo permisos independientes.
- El visor guarda `device_id` y token de sesion en `localStorage`, y envia `Authorization: Bearer ...` + `X-Rainmapper-Device` al pedir GeoJSON.
- Si se borran datos del navegador, un usuario con limite de dispositivos puede quedar bloqueado porque se genera un nuevo `device_id`; se resuelve limpiando/deshabilitando un registro anterior en `devices.json`.
- La WebUI HA incluye una pagina `Users`, pensada para acceso por Ingress/Home Assistant, para crear usuarios, borrar usuarios, activar/desactivar acceso, cambiar rol/max_devices, cambiar permisos MapLibre de heatmap/metrica, establecer nuevas contrasenas, forzar cambio de contrasena y borrar dispositivos individuales o todos los de un usuario. `Delete user` borra tambien todos sus dispositivos asociados. `Set password` guarda una contrasena definida por el administrador y borra los dispositivos del usuario. `Reset password` marca `must_change_password=true`, borra dispositivos y obliga al usuario a elegir una contrasena distinta tras autenticarse con la actual.
- Esta autenticacion ligera aplica al servidor HA. El visor Docker local sigue siendo estatico para pruebas y lee `docker-data/PublicData`. Los tests de backend viven en `tests/test_web_server_auth.py`; cubren usuarios JSON, limites por dispositivo, admin ilimitado y funciones de gestion.

- Estado persistente principal: CSV en filesystem.
- Estado runtime webUI: diccionario global `RUN_STATE` en `web_server.py`.
- Estado por fuente: `Data/source_status.json`, leido por `web_server.py` para mostrar tarjetas de estado, exit code, filas y duraciones por fuente. MapLibre protegido lo sirve desde rutas protegidas de datos; si se publican visores legacy con `publish_to_www=true`, tambien se copia a sus directorios `data/`.
- Estado de logs: `/share/rainmapper/last_run.log` se reescribe por ejecucion.
- Estado de estaciones desactivadas: comentarios en `stations.txt` con marcadores `rainmapper-disabled`.
- Estado de estaciones ignoradas en mapas nuevos: `ignore_stations_tomap.txt`.
- Estado UI de visores: JavaScript en cliente mantiene periodo, capa y vista actual.

## Routing o navegacion
WebUI HA (`web_server.py`):

- `GET /`: pagina principal.
- `GET /settings`: pagina intermedia con enlaces a configuracion de la app HA; usa Supervisor self-info y rutas fallback.
- `GET /file/<html>`: sirve mapas HTML locales.
- `POST`: acciones run/update/maps/all y enable/disable de grupos de estaciones.
- La portada muestra `RAINMAPPER_APP_VERSION` en el panel de estado. El enlace operativo principal a MapLibre usa `/protected/maplibre/index.html?v=<RAINMAPPER_APP_VERSION>`; los enlaces `/local/...` solo aplican a salidas legacy cuando `publish_to_www=true`. Los `index.html` de Leaflet/MapLibre tambien deben mantener sus referencias internas `style.css`, `config.js` y `app.js` con el mismo cache-buster de version; `scripts/smoke-test.sh` lo valida desde `0.2.65`.

Home Assistant sirve:

- `/protected/maplibre/index.html`: visor operativo recomendado, servido por `web_server.py`.
- `/protected/maplibre/data/*`: GeoJSON y estado para MapLibre protegido.
- `/local/Plots/...`: Bokeh HTML solo si `publish_to_www=true`.
- `/local/rainmapper-leaflet/index.html`: Leaflet legacy solo si `publish_to_www=true`.
- `http://<HA_IP>:8099/protected/maplibre/index.html`: entrada protegida MapLibre servida por `web_server.py`; Cloudflared debe apuntar el hostname externo al servicio `http://<HA_IP>:8099`.
- OpenTopoMap y Esri: tiles raster usados por Leaflet y MapLibre.
- Terrarium/Mapzen DEM externo: fuente `raster-dem` opcional para terrain 3D en MapLibre. No se empaqueta dentro de Docker ni se publica desde `/config/www`.

No incluir secretos en codigo ni documentacion.

## Configuracion
- `requirements.txt`: dependencias Python raiz.
- `rainmapper-local/Dockerfile`: Docker local.
- `rainmapper-local/docker-compose.yml`: Docker local con volumenes. La raiz mantiene `docker-compose.yml` como include de compatibilidad.
- `rainmapper-app/Dockerfile`: Docker HA app; se debe construir con la raiz del repo como contexto.
- `rainmapper-app/config.yaml`: metadata y schema HA.
- Meteocat/Socrata: timeout y reintentos configurables mediante `meteocat_request_timeout` y `meteocat_max_attempts` en HA, o `RAINMAPPER_METEOCAT_REQUEST_TIMEOUT`/`RAINMAPPER_METEOCAT_MAX_ATTEMPTS` en Docker local.
- `repository.yaml`: metadata repositorio HA.
- `.gitignore`: excluye datos, caches, venv, tests locales y scripts antiguos.
- `.dockerignore`: excluye datos locales, caches y material no necesario para imagenes Docker.
- `rainmapper_core/config/const.py`: defaults compartidos. Calcula rutas runtime desde la raiz del entorno.

No detectado: `package.json`, `pyproject.toml`, Makefile, ESLint, Prettier, pytest config.

## Testing
Hay un smoke test versionado en `scripts/smoke-test.sh`, tests funcionales offline con `unittest` en `tests/` y una prueba Docker offline versionada en `scripts/docker-offline-functional-test.sh`.

Validaciones existentes/recomendadas:

```bash
./scripts/smoke-test.sh
./scripts/docker-offline-functional-test.sh
.venv/bin/python -m unittest discover -s tests
python -m unittest tests.test_web_server_auth
python -m py_compile rainmapper_core/rainmapper.py rainmapper_core/bokeh_maps.py rainmapper_core/geojson.py rainmapper-app/app/web_server.py rainmapper-app/app/mushroom_catalogs_ui.py rainmapper-app/app/mushroom_profiles_ui.py rainmapper-app/app/mushroom_gis_mappings_ui.py
node --check rainmapper_core/viewers/leaflet-viewer/app.js
node --check rainmapper_core/viewers/maplibre-viewer/app.js
docker compose build rainmapper
docker compose run --rm -e MODE=help rainmapper
docker build -f rainmapper-app/Dockerfile -t rainmapperha-ha:test .
git diff --check
```

Cobertura: el smoke test valida sintaxis Python/JS/shell, ejecuta `unittest`, conversion GeoJSON minima con `ignore_stations_tomap.txt`, reconstruccion con poco historico para columnas `Last*_rains`, versionado HA, empaquetado HA sin copias de core y whitespace de Git. Los tests en `tests/` cubren fixtures funcionales de conversion Tomap -> GeoJSON, estaciones ignoradas, coordenadas invalidas, columnas obligatorias, `rainmapper_core.tomap`, un pipeline offline integrado `upsert -> Tomap -> GeoJSON`. `scripts/docker-offline-functional-test.sh` anade una validacion mas pesada con Docker real, pero sigue sin red y sin tocar `docker-data`: construye la imagen local, monta datos temporales y valida `Tomap`/GeoJSON generados dentro del contenedor. `rainmapper-app/Dockerfile` copia el core directamente desde la raiz del repositorio; ya no hay copia fisica de `rainmapper_core/` en `rainmapper-app/app`. `scripts/check-history.py` valida historicos CSV de forma basica. Las pruebas funcionales completas de HA/movil siguen siendo principalmente manuales.

## Build y despliegue
Docker local:

```bash
docker compose build rainmapper
docker compose run --rm rainmapper
```

`MODE=maps` y `MODE=all` generan GeoJSON local en `docker-data/PublicData`; Bokeh y visores publicos legacy se generan/publican solo si `publish_to_www=true`.

Home Assistant:

- El repo se anadio como repositorio de apps/add-ons en HA cuando era publico. Desde el 2026-06-22 se decidio mantener el repo GitHub `cginebrosa/RainmapperHA` privado para no exponer codigo ni logica de descarga, abriendolo solo en ventanas operativas para que HA detecte updates. Tras validar `0.2.137` en HA, auditoria final del 2026-06-25: repo privado (`private=true`, `visibility=private`, rama `inicial`).
- HA detecta `repository.yaml` y `rainmapper-app/config.yaml`.
- Desde `0.2.57`, `rainmapper-app/config.yaml` define `image: ghcr.io/cginebrosa/rainmapperha`, por lo que HA debe descargar la imagen versionada en vez de construirla localmente.
- Desde `0.2.60`, el flujo normal publica la imagen multi-arch `amd64`/`arm64` desde el Mac con `scripts/build-push-ha-image.sh`. Flujo operativo actual: validar, hacer bump, commit/push, publicar/verificar imagen y avisar al usuario en cuanto HA pueda probarla.
- `scripts/build-push-ha-image.sh` publica dos tags: `<version>` y `latest`. Home Assistant instala la etiqueta versionada que corresponde a `config.yaml`; `latest` queda solo como conveniencia operativa.
- El script limpia etiquetas locales antiguas de `ghcr.io/cginebrosa/rainmapperha` despues de un push correcto y conserva por defecto las dos ultimas versiones locales mas `latest`.
- El paquete remoto GHCR debe seguir accesible para Home Assistant si no se configura autenticacion de registry en HA. Estado vigente de continuidad: `0.2.193/latest` esta publicada/verificada con digest multi-arch `sha256:2f563f601ed4b8902f679e2be43b689ae6b255a28a5207a4dade2555e255c98a`.
- Procedimiento estandar tras publicar y validar una nueva version HA: limpiar tambien las versiones remotas antiguas del paquete GHCR, conservando la ultima version validada, `latest`, el rollback inmediato y las entradas auxiliares sin tag asociadas a los pushes multi-arch/attestations que se conserven. Esto evita acumular basura en GitHub Packages sin romper pulls de HA. No borrar la version que declare `rainmapper-app/config.yaml` ni sus entradas auxiliares multi-arch mientras HA pueda necesitar instalarla o reinstalarla.
- `.github/workflows/build-rainmapper-app.yml` queda como fallback manual (`workflow_dispatch`), no como publicacion automatica en cada push.
- Los updates se distribuyen con commit de version en GitHub e imagen GHCR publicada/verificada. Si HA necesita detectar metadata desde el repo privado, abrir el repo temporalmente, usar `Check for updates`/`Update` en HA y volver a privado tras validar.

## Convenciones de codigo
- Scripts Python monoliticos con constantes globales y funciones procedurales.
- Configuracion por variables de entorno y argumentos CLI.
- Persistencia por CSV y directorios fijos.
- WebUI construida con HTML generado en Python.
- JS de visores sin bundler ni framework.
- Logs operativos principales y webUI HA en ingles; README/DOCS de la app HA siguen en espanol por decision operativa actual.
- Scripts de mantenimiento/desarrollo (`.py`, `.sh` u otros) deben incluir documentacion interna en ingles: cabecera de proposito y comentarios breves antes de bloques o funciones no obvias. No hace falta comentar cada linea, pero el flujo debe poder entenderse sin depender del historial del chat.
- Errores Wunderground se clasifican por patrones en logs.
- Cambios de core deben hacerse en `rainmapper_core/`; no reintroducir copias fisicas en `rainmapper-app/app`.

## Riesgos arquitectonicos
- Persisten entrypoints/wrappers shell de compatibilidad en raiz, pero la duplicidad fisica de core entre raiz y app HA fue retirada; no reintroducirla.
- Acoplamiento fuerte a nombres/rutas CSV.
- Scraper Wunderground fragil ante cambios HTML o estaciones desaparecidas.
- Proteccion automatica de historicos limitada: existen `scripts/check-history.py`, `scripts/backup-data.sh` y smoke checks, pero no una suite funcional completa de regresion historica.
- `web_server.py` concentra demasiadas responsabilidades.
- Gestion de version dispersa entre `config.yaml`, `CHANGELOG.md`, assets y Dockerfile.
- API keys de mapas cliente son visibles en navegador si se usan tiles externos con token.
- MapLibre protegido es el visor principal recomendado. Bokeh, Leaflet publico y visores publicos antiguos quedan como legacy opcional bajo `publish_to_www`; no asumir que existen en `/config/www` ni en `/local`.
- La configuracion Cloudflare real no esta versionada. Estado operativo conocido desde 2026-06-22: HTTP redirige a HTTPS, HSTS esta activo con `includeSubDomains`, `rainmap.nomentero.com` sirve la ruta protegida y los subdominios fallback externos `leaflet.nomentero.com`/`maplibre.nomentero.com` quedan protegidos con Cloudflare Access.
