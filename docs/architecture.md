# Architecture

## Workspace real

La ruta de trabajo valida es `/Users/carlosginebrosa/Developer/RainmapperHA`. La copia antigua en iCloud/Mobile Documents no debe usarse para desarrollo, validacion ni commits porque puede estar desfasada.

## Resumen tecnico
RainmapperHA es una aplicacion Python empaquetada en Docker y Home Assistant. El core descarga y normaliza datos meteorologicos en CSV. Una segunda capa genera mapas HTML clasicos con Bokeh y GeoJSON para visores estaticos modernos. La app de Home Assistant anade webUI, schedule interno, publicacion a `/config/www` e integracion con ingress/sidebar.

La arquitectura actual no separa completamente dominio, infraestructura y UI: todavia hay scripts grandes, aunque la duplicidad fisica entre raiz y `rainmapper-app/app` ya fue retirada. Aun asi, el flujo esta estabilizado y funciona como pipeline de ficheros.

## Stack tecnologico
- Lenguaje: Python 3.11, JavaScript estatico, HTML, CSS, shell.
- Runtime Python: `python:3.11-slim` en Docker.
- Gestor de paquetes Python: `pip` con `requirements.txt`.
- Sistema de build: Dockerfile y Docker Compose.
- Librerias Python principales: pandas, numpy, requests, BeautifulSoup, lxml, googlemaps, bokeh, pytz.
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
- `rainmapper-app/app/`: codigo especifico de Home Assistant que entra en la imagen HA (`web_server.py`). El core y visores se copian desde las rutas canonicas de raiz durante el build.
- `rainmapper-local/`: runtime Docker local y scripts especificos de pruebas locales.
- `rainmapper_core/viewers/leaflet-viewer/`: fuente canonica del visor Leaflet.
- `rainmapper_core/viewers/maplibre-viewer/`: fuente canonica del visor MapLibre.
- `scripts/`: utilidades versionadas de desarrollo; contiene `smoke-test.sh`, `docker-offline-functional-test.sh`, `backup-data.sh`, `build-push-ha-image.sh` y `check-history.py`.
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
8. `python -m rainmapper_core.bokeh_maps` genera HTML Bokeh en `Plots`.
9. `python -m rainmapper_core.geojson` genera GeoJSON desde `Tomap` delegando en `rainmapper_core/geojson.py`.
10. `web_server.py` publica HTML, GeoJSON y visores estaticos en `/config/www`.
11. Home Assistant sirve Bokeh y Leaflet por `/local/...`; MapLibre operativo recomendado se sirve desde `web_server.py` por `/protected/maplibre/index.html` y datos `/protected/maplibre/data/*`. El fallback local `/local/rainmapper-maplibre/index.html` se mantiene temporalmente, pero el fallback externo `maplibre.nomentero.com` queda protegido por Cloudflare Access.

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
- Relacion: salida publicada por `web_server.py` a `/config/www/Plots`.

### Reconstructor Tomap
- Ruta: `rainmapper_core/tomap.py`, sin wrappers raiz/HA; ejecutable con `python -m rainmapper_core.tomap`.
- Responsabilidad: leer historicos `Data/*_incremental.csv` y reconstruir `Tomap/*.csv` y `LastXX_rains.csv` sin ejecutar descargas.
- Dependencias: pandas, pathlib, constantes locales.
- Relacion: `run.sh`, `rainmapper-app/run.sh` y `Generate maps` de la webUI lo ejecutan antes de `python -m rainmapper_core.bokeh_maps` y `python -m rainmapper_core.geojson`. Es la ruta activa de generacion `Tomap`; el bloque ejecutable inline y los helpers legacy de `Rainmapper.py` ya fueron retirados.

### Conversor GeoJSON
- Ruta: `rainmapper_core/geojson.py`, sin wrappers raiz/HA; ejecutable con `python -m rainmapper_core.geojson`.
- Responsabilidad: convertir CSV `Tomap` a GeoJSON por periodo, inferir `Source`, aplicar `ignore_stations_tomap.txt` y escribir metadata de generacion.
- Dependencias: pandas, json, pathlib.
- Relacion: produce datos para Leaflet/MapLibre.

### WebUI HA
- Ruta: `rainmapper-app/app/web_server.py`.
- Responsabilidad: servidor HTTP, webUI, acciones, schedule, publicacion, logs, status, enable/disable estaciones y rutas protegidas de MapLibre.
- Dependencias: stdlib HTTP, subprocess, threading, json, pathlib.
- Relacion: orquesta scripts Python y publica visores. En HA se mantiene `ingress_port: 8099` para la webUI y tambien se publica `8099/tcp` como puerto de app para que Cloudflared pueda apuntar a `http://<HA_IP>:8099` sin usar `/local`.

### Wrapper HA
- Ruta: `rainmapper-app/run.sh`.
- Responsabilidad: leer opciones HA, crear persistencia, symlinks, exportar variables, arrancar modo.
- Dependencias: shell, Python para leer JSON de opciones.
- Relacion: entrypoint del contenedor HA.

### Wrapper Docker local
- Ruta: `rainmapper-local/run.sh`; `run.sh` en raiz es un wrapper compatible.
- Responsabilidad: ejecutar Rainmapper localmente en Docker y mapear variables cortas/largas.
- Dependencias: shell, Python para calculo schedule.
- Relacion: entorno seguro de pruebas en Mac. En `maps/all`, ejecuta `python -m rainmapper_core.bokeh_maps` y `python -m rainmapper_core.geojson`, dejando GeoJSON actualizado en `docker-data/PublicData` para los visores locales.

### Runner local completo
- Ruta: `rainmapper-local/local_all.sh`; `local_all.sh` en raiz es un wrapper compatible.
- Responsabilidad: automatizar la secuencia de prueba local: `docker compose build rainmapper`, `docker compose run --rm -e MODE=all rainmapper` y servidor HTTP local para abrir visores.
- Dependencias: Docker Compose y `python3`.
- Relacion: acceso rapido a `http://127.0.0.1:8080/rainmapper_core/viewers/maplibre-viewer/` y `http://127.0.0.1:8080/rainmapper_core/viewers/leaflet-viewer/` tras regenerar datos locales.

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
- Responsabilidad: construir la imagen HA desde la raiz del repositorio, copiando `rainmapper_core/`, wrappers raiz, configuracion compartida y `rainmapper-app/app/web_server.py`.
- Relacion: `rainmapper-app/app` queda reservado para codigo especifico de HA; el smoke test falla si vuelven a aparecer copias de core en esa carpeta.

### Leaflet viewer
- Ruta canonica: `rainmapper_core/viewers/leaflet-viewer/`.
- En HA se publica directamente desde `/app/rainmapper_core/viewers/leaflet-viewer`.
- Responsabilidad: visor web movil basado en Leaflet y GeoJSON.
- Dependencias: Leaflet CDN, tiles raster.
- Relacion: publicado a `/local/rainmapper-leaflet`.

### MapLibre viewer
- Ruta canonica: `rainmapper_core/viewers/maplibre-viewer/`.
- En HA se publica directamente desde `/app/rainmapper_core/viewers/maplibre-viewer`.
- Responsabilidad: visor web principal con mapas vectoriales/raster, filtros cliente de estaciones y terreno 3D opcional.
- Dependencias: MapLibre GL JS CDN, Esri raster Hybrid/Satellite, OpenTopoMap raster, OpenFreeMap y DEM externo Terrarium/Mapzen para terreno 3D.
- Relacion: los assets estaticos se siguen publicando en `/local/rainmapper-maplibre`, pero la ruta operativa recomendada en HA es `/protected/maplibre/index.html`; los GeoJSON se sirven por `/protected/maplibre/data/*` con autenticacion ligera. Satellite+ es la capa inicial recomendada; combina imagen Esri con orientacion vectorial OpenFreeMap. Desde `0.2.58`, Settings permite elegir mapa base, filtrar por lluvia minima y filtrar por fuente de estacion. Desde `0.2.71`, el filtro `Source` muestra badges de estado por fuente si existe `data/source_status.json`; en escritorio, desde zoom 9, la ficha de estacion tambien aparece por hover sin cambiar el comportamiento tactil de movil. En `0.2.81` la UI se moderniza con cabecera clara, controles flotantes, selector inferior de periodo, leyenda vertical dinamica y popups claros; el popup de estacion se mantiene/refresca al cambiar de periodo si la estacion sigue visible tras filtros. El visor incluye un boton de orientacion norte que solo resetea el `bearing`. El terreno 3D se activa desde Settings, esta apagado por defecto y se reaplica al cambiar de estilo porque `setStyle` reemplaza las fuentes del mapa. Una pulsacion larga sobre el mapa consulta altitud DEM leyendo directamente el tile Terrarium externo y decodificando el pixel RGB, no mediante `queryTerrainElevation`; el disparador usa eventos MapLibre y `contextmenu` para funcionar tanto en local como servido desde HA.

## Modelo de datos
Persistencia por CSV:

- Historicos incrementales en `Data/*_incremental.csv`.
- Identidad logica de una fila incremental: `Codi Estació` + `Data Local`. Debe existir como maximo una fila por fuente/estacion/dia; `rainmapper_core.incremental_upsert` aplica esta regla.
- Listados/metadata de estaciones en `Data/estacions_*.csv`.
- CSV preparados para mapas en `Tomap/01_Tomap_Last_day.csv`, `02_Tomap_Last_week.csv`, etc.
- Ultimos registros en `Tomap/LastXX_rains.csv`; por defecto `Last30_rains.csv`, configurable con `RAINMAPPER_LAST_RAINS_HISTORY` o la opcion HA `last_rains_history`.
- Metricas Wunderground en `Data/metricas_wunderground.csv`.
- Estado de fuentes en `Data/source_status.json`, con entradas para Meteoclimatic, Meteocat, Wunderground y AEMET. Estados actuales: `OK`, `DISABLED`, `STALE`, `NOK` y `PENDING`. `STALE` indica que la fuente fallo pero se reutilizo incremental previo. El payload puede incluir `duration_seconds`, `started_at`, `finished_at`, `rows`, `stations` y `timings`; los subtiempos actuales se usan especialmente para Meteocat.
- GeoJSON generados en `PublicData/*.geojson`. Leaflet recibe copia publica en `/local/rainmapper-leaflet/data`; MapLibre los consume desde `/protected/maplibre/data/*` para exigir login.

Campos relevantes detectados o usados:

- `Codi Estació` / codigo de estacion.
- `Source` en GeoJSON, inferido por `rainmapper_core.geojson` desde el codigo de estacion: `AEMET:` para AEMET, `ES...` con longitud minima 15 para Meteoclimatic, `I...` para Wunderground, codigos de longitud 2 para Meteocat, resto `Unknown` con aviso en stdout.
- `Latitud`, `Longitud`.
- lluvia acumulada por periodo.
- municipio/provincia/altitud.
- historico de ultimas lluvias y temperaturas max/min para popup (`Data_Pluja_XX`, `Pluja_Diaria_XX`, `Temp_Max_XX`, `Temp_Min_XX`). La configuracion por defecto genera hasta 30 registros, `last_rains_history` permite cambiarlo en HA, y los visores detectan dinamicamente cuantos hay en el GeoJSON.

Schemas completos: pendiente de confirmar en detalle leyendo todos los CSV y funciones pandas.

## Gestion de estado

### Autenticacion ligera MapLibre
- Usuarios manuales en `/share/rainmapper/users.json`, con `username`, `name`, `email`, `password`, `role`, `enabled`, `max_devices` y `must_change_password`. `username` es el identificador de login; `name` es el nombre de la persona; `email` es contacto.
- En HA, `run.sh` crea `users.json` desde `/app/users.example.json` si no existe `users.json`; no sobrescribe usuarios existentes.
- `users.json` es el unico formato de usuarios soportado; no hay formato alternativo ni ruta de migracion.
- Dispositivos y sesiones en `/share/rainmapper/devices.json`, generado por la app como JSON vacio si no existe.
- Cada entrada de `/share/rainmapper/devices.json` puede incluir `settings` del visor MapLibre para ese `device_id`: `period`, `min_rain_mm`, `map_style`, `last_rains_history`, `station_sources`, `terrain_enabled` y `terrain_exaggeration`. El backend solo permite leer/escribir esos settings para el dispositivo autenticado mediante `/auth/device-settings` y sanea los valores antes de persistirlos.
- Roles soportados: `free`, `basic`, `pro` y `admin`.
- Limites por defecto: `free=1`, `basic=2`, `pro=3`, `admin=0`; `0` significa dispositivos ilimitados. `max_devices` puede sobrescribir el limite por usuario.
- El visor guarda `device_id` y token de sesion en `localStorage`, y envia `Authorization: Bearer ...` + `X-Rainmapper-Device` al pedir GeoJSON.
- Si se borran datos del navegador, un usuario con limite de dispositivos puede quedar bloqueado porque se genera un nuevo `device_id`; se resuelve limpiando/deshabilitando un registro anterior en `devices.json`.
- La WebUI HA incluye una pagina `Users`, pensada para acceso por Ingress/Home Assistant, para crear usuarios, borrar usuarios, activar/desactivar acceso, cambiar rol/max_devices, establecer nuevas contrasenas, forzar cambio de contrasena y borrar dispositivos individuales o todos los de un usuario. `Delete user` borra tambien todos sus dispositivos asociados. `Set password` guarda una contrasena definida por el administrador y borra los dispositivos del usuario. `Reset password` marca `must_change_password=true`, borra dispositivos y obliga al usuario a elegir una contrasena distinta tras autenticarse con la actual.
- Esta autenticacion ligera aplica al servidor HA. El visor Docker local sigue siendo estatico para pruebas y lee `docker-data/PublicData`. Los tests de backend viven en `tests/test_web_server_auth.py`; cubren usuarios JSON, limites por dispositivo, admin ilimitado y funciones de gestion.

- Estado persistente principal: CSV en filesystem.
- Estado runtime webUI: diccionario global `RUN_STATE` en `web_server.py`.
- Estado por fuente: `Data/source_status.json`, leido por `web_server.py` para mostrar tarjetas de estado, exit code, filas y duraciones por fuente. Al publicar visores, se copia tambien a `data/source_status.json` dentro de Leaflet/MapLibre; MapLibre lo usa solo para mostrar badges junto al filtro `Source`, no tiempos de proceso.
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
- La portada muestra `RAINMAPPER_APP_VERSION` en el panel de estado y sus enlaces hacia visores `/local/...` incluyen `?v=<RAINMAPPER_APP_VERSION>` para reducir cache obsoleta en el frontend de Home Assistant. Los `index.html` de Leaflet/MapLibre tambien deben mantener sus referencias internas `style.css`, `config.js` y `app.js` con el mismo cache-buster de version; `scripts/smoke-test.sh` lo valida desde `0.2.65`.

Home Assistant publica:

- `/local/Plots/...`: Bokeh HTML.
- `/local/rainmapper-leaflet/index.html`: Leaflet fallback local. En la exposicion externa actual, `leaflet.nomentero.com` queda protegido por Cloudflare Access.
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
python -m py_compile rainmapper_core/rainmapper.py rainmapper_core/bokeh_maps.py rainmapper_core/geojson.py rainmapper-app/app/web_server.py
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

`MODE=maps` y `MODE=all` generan tanto mapas Bokeh como GeoJSON local en `docker-data/PublicData`.

Home Assistant:

- El repo se anadio como repositorio de apps/add-ons en HA cuando era publico. Desde el 2026-06-22 el repo GitHub `cginebrosa/RainmapperHA` es privado para no exponer codigo ni logica de descarga; la instalacion existente de HA sigue usando la imagen GHCR preconstruida.
- HA detecta `repository.yaml` y `rainmapper-app/config.yaml`.
- Desde `0.2.57`, `rainmapper-app/config.yaml` define `image: ghcr.io/cginebrosa/rainmapperha`, por lo que HA debe descargar la imagen versionada en vez de construirla localmente.
- Desde `0.2.60`, el flujo normal publica la imagen multi-arch `amd64`/`arm64` desde el Mac con `scripts/build-push-ha-image.sh` antes de subir el commit de version. Esto evita que HA vea un update antes de que exista la imagen en GHCR.
- `scripts/build-push-ha-image.sh` publica dos tags: `<version>` y `latest`. Home Assistant instala la etiqueta versionada que corresponde a `config.yaml`; `latest` queda solo como conveniencia operativa.
- El script limpia etiquetas locales antiguas de `ghcr.io/cginebrosa/rainmapperha` despues de un push correcto y conserva por defecto las dos ultimas versiones locales mas `latest`.
- El paquete remoto GHCR debe seguir accesible para Home Assistant si no se configura autenticacion de registry en HA. El 2026-06-24 se limpio GHCR tras validar `0.2.111`; despues se publico `0.2.112` con digest `sha256:37f841c9004ab879227d2cc67ee6f836d1e8c4adc14ae609ba9b7cf41b3637f7` y se verifico como index OCI con `linux/amd64` y `linux/arm64`. Conservar `0.2.111` como fallback hasta validar `0.2.112` en HA.
- Procedimiento estandar tras publicar y validar una nueva version HA: limpiar tambien las versiones remotas antiguas del paquete GHCR, conservando solo la ultima version validada, `latest` y las entradas auxiliares sin tag asociadas al mismo push multi-arch. Esto evita acumular basura en GitHub Packages. No hacer esta limpieza antes de confirmar que HA descarga y arranca correctamente la nueva version.
- `.github/workflows/build-rainmapper-app.yml` queda como fallback manual (`workflow_dispatch`), no como publicacion automatica en cada push.
- Los updates se distribuyen publicando primero la imagen localmente, subiendo despues el commit al repo privado de GitHub, y usando `Check for updates`/`Update` en HA.

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
- Bokeh, Leaflet y MapLibre conviven; MapLibre es el visor principal recomendado, Leaflet queda como fallback publicado y Bokeh como referencia/compatibilidad.
- La configuracion Cloudflare real no esta versionada. Estado operativo conocido desde 2026-06-22: HTTP redirige a HTTPS, HSTS esta activo con `includeSubDomains`, `rainmap.nomentero.com` sirve la ruta protegida y los subdominios fallback externos `leaflet.nomentero.com`/`maplibre.nomentero.com` quedan protegidos con Cloudflare Access.
