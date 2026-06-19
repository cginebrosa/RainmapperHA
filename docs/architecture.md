# Architecture

## Resumen tecnico
RainmapperHA es una aplicacion Python empaquetada en Docker y Home Assistant. El core descarga y normaliza datos meteorologicos en CSV. Una segunda capa genera mapas HTML clasicos con Bokeh y GeoJSON para visores estaticos modernos. La app de Home Assistant anade webUI, schedule interno, publicacion a `/config/www` e integracion con ingress/sidebar.

La arquitectura actual no separa completamente dominio, infraestructura y UI: hay scripts grandes y duplicados entre raiz y `rainmapper-app/app`. Aun asi, el flujo esta estabilizado y funciona como pipeline de ficheros.

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
- Librerias HTTP/API: `requests`, `sodapy_local`, `googlemaps`.
- Librerias de testing: `unittest` de la libreria estandar en `tests/`; no se ha detectado `pytest`.
- Base de datos: no hay base de datos detectada; persistencia por CSV.
- Despliegue: GitHub como repositorio de app HA y GHCR como registry de imagenes preconstruidas; Home Assistant descarga `ghcr.io/cginebrosa/rainmapperha:<version>` cuando existe la imagen publicada.

## Estructura de carpetas
- `rainmapper-app/`: paquete de Home Assistant.
- `rainmapper-app/app/`: codigo que entra en la imagen HA.
- `leaflet-viewer/`: fuente del visor Leaflet en raiz.
- `maplibre-viewer/`: fuente del visor MapLibre en raiz.
- `scripts/`: utilidades versionadas de desarrollo; contiene `smoke-test.sh`, `sync-app-files.sh`, `backup-data.sh` y `check-history.py`.
- `local_update.sh`: runner local solo update, util para refrescar descargas actuales e incrementales sin reconstruir `Tomap` ni publicar visores.
- `meteoclimatic_local/`: cliente local Meteoclimatic.
- `sodapy_local/`: copia local/adaptada de Socrata client.
- `util/`: parser/scraper Wunderground.
- `Data/`: CSV historicos locales, ignorados por Git.
- `Tomap/`: CSV intermedios para mapas, ignorados por Git.
- `Plots/`: HTML Bokeh generados, ignorados por Git.
- `docker-data/`: volumenes locales Docker, ignorados por Git.
- `docs/`: documentacion de continuidad.

## Punto de entrada de la aplicacion
Hay varios entry points segun entorno:

- Docker local: `Dockerfile` ejecuta `/app/run.sh`.
- Home Assistant: `rainmapper-app/Dockerfile` ejecuta `/run.sh`.
- Core de datos: `Rainmapper.py`.
- Reconstruccion Tomap sin descarga: `tomap_builder.py`.
- Mapas Bokeh: `Rainmapper_Client.py`.
- GeoJSON: `tomap_to_geojson.py`.
- WebUI HA: `rainmapper-app/app/web_server.py`.
- Leaflet: `leaflet-viewer/index.html` y `leaflet-viewer/app.js`.
- MapLibre: `maplibre-viewer/index.html` y `maplibre-viewer/app.js`.

## Flujo principal
1. Se arrancan Docker local o app HA.
2. El wrapper prepara rutas y variables de entorno.
3. En HA, `serve` arranca `web_server.py`.
4. El usuario pulsa `Run update`, `Generate maps` o `Run all`, o el schedule dispara una accion.
5. `Rainmapper.py` descarga datos y actualiza CSV historicos/incrementales.
6. `tomap_builder.py` reconstruye CSV `Tomap` para los periodos acumulados desde historicos incrementales sin descargar datos nuevos.
7. En `MODE=maps`, `MODE=all` y `Generate maps`, `tomap_builder.py` reconstruye `Tomap` antes de generar salidas publicables.
8. `Rainmapper_Client.py` genera HTML Bokeh en `Plots`.
9. `tomap_to_geojson.py` genera GeoJSON desde `Tomap`.
10. `web_server.py` publica HTML, GeoJSON y visores estaticos en `/config/www`.
11. Home Assistant sirve los mapas por `/local/...`.

## Componentes, modulos o capas principales

### Core de descarga y datos
- Ruta: `Rainmapper.py` y `rainmapper-app/app/Rainmapper.py`.
- Responsabilidad: descarga Meteocat, Meteoclimatic y Wunderground; actualiza historicos; escribe estado por fuente; metricas Wunderground.
- Dependencias: pandas, requests, BeautifulSoup, googlemaps, `meteoclimatic_local`, `sodapy_local`, `util`.
- Relacion: alimenta `Rainmapper_Client.py` y `tomap_to_geojson.py`. Desde `0.2.71`, registra en `Data/source_status.json` el resultado de cada fuente y puede continuar con incrementales previos si una fuente falla completamente. El estado por fuente incluye duraciones reales medidas con temporizadores locales; no usar los logs `start_count/end_count` como metrica fiable cuando hay paralelismo porque comparten un temporizador global.

### Generador Bokeh
- Ruta: `Rainmapper_Client.py` y copia en app.
- Responsabilidad: leer `Tomap` y generar HTML Bokeh en `Plots`.
- Dependencias: Bokeh, pandas, Google Maps key.
- Relacion: salida publicada por `web_server.py` a `/config/www/Plots`.

### Reconstructor Tomap
- Ruta: `tomap_builder.py` y copia en app.
- Responsabilidad: leer historicos `Data/*_incremental.csv` y reconstruir `Tomap/*.csv` y `LastXX_rains.csv` sin ejecutar descargas.
- Dependencias: pandas, pathlib, constantes locales.
- Relacion: `run.sh`, `rainmapper-app/run.sh` y `Generate maps` de la webUI lo ejecutan antes de `Rainmapper_Client.py` y `tomap_to_geojson.py`. Es la ruta activa de generacion `Tomap`; el bloque ejecutable inline de `Rainmapper.py` fue retirado de forma transicional, dejando helpers legacy marcados para limpieza posterior.

### Conversor GeoJSON
- Ruta: `tomap_to_geojson.py` y copia en app.
- Responsabilidad: convertir CSV `Tomap` a GeoJSON por periodo.
- Dependencias: pandas, json, pathlib.
- Relacion: produce datos para Leaflet/MapLibre.

### WebUI HA
- Ruta: `rainmapper-app/app/web_server.py`.
- Responsabilidad: servidor HTTP, webUI, acciones, schedule, publicacion, logs, status, enable/disable estaciones.
- Dependencias: stdlib HTTP, subprocess, threading, json, pathlib.
- Relacion: orquesta scripts Python y publica visores.

### Wrapper HA
- Ruta: `rainmapper-app/run.sh`.
- Responsabilidad: leer opciones HA, crear persistencia, symlinks, exportar variables, arrancar modo.
- Dependencias: shell, Python para leer JSON de opciones.
- Relacion: entrypoint del contenedor HA.

### Wrapper Docker local
- Ruta: `run.sh`.
- Responsabilidad: ejecutar Rainmapper localmente en Docker y mapear variables cortas/largas.
- Dependencias: shell, Python para calculo schedule.
- Relacion: entorno seguro de pruebas en Mac. En `maps/all`, ejecuta `Rainmapper_Client.py` y `tomap_to_geojson.py`, dejando GeoJSON actualizado en `docker-data/PublicData` para los visores locales.

### Runner local completo
- Ruta: `local_all.sh`.
- Responsabilidad: automatizar la secuencia de prueba local: `docker compose build rainmapper`, `docker compose run --rm -e MODE=all rainmapper` y servidor HTTP local para abrir visores.
- Dependencias: Docker Compose y `python3`.
- Relacion: acceso rapido a `http://127.0.0.1:8080/maplibre-viewer/` y `http://127.0.0.1:8080/leaflet-viewer/` tras regenerar datos locales.

### Runner local solo mapas
- Ruta: `local_maps.sh`.
- Responsabilidad: automatizar la secuencia de prueba local sin descargar datos nuevos: `docker compose build rainmapper`, `docker compose run --rm -e MODE=maps rainmapper` y servidor HTTP local para abrir visores.
- Dependencias: Docker Compose y `python3`.
- Relacion: permite iterar rapido cambios de Leaflet/MapLibre. Desde la extraccion conservadora de `tomap_builder.py`, `MODE=maps` reconstruye `Tomap` desde `docker-data/Data` antes de generar Bokeh/GeoJSON; si no hay lecturas para el dia actual, el periodo de 1 dia puede quedar vacio aunque existan `Tomap` anteriores.

### Comparador Tomap
- Ruta: `scripts/compare-tomap-builder.sh`.
- Responsabilidad: reconstruir `Tomap` en un directorio temporal con `tomap_builder.py` y compararlo con `docker-data/Tomap`.
- Relacion: sirve para validar que el builder reproduce los `Tomap` actuales sin sobrescribirlos; despues de retirar el bloque inline de `Rainmapper.py`, ya no compara contra una generacion legacy nueva.

### Leaflet viewer
- Ruta: `leaflet-viewer/` y `rainmapper-app/app/leaflet-viewer/`.
- Responsabilidad: visor web movil basado en Leaflet y GeoJSON.
- Dependencias: Leaflet CDN, tiles raster.
- Relacion: publicado a `/local/rainmapper-leaflet`.

### MapLibre viewer
- Ruta: `maplibre-viewer/` y `rainmapper-app/app/maplibre-viewer/`.
- Responsabilidad: visor web principal con mapas vectoriales/raster, filtros cliente de estaciones y terreno 3D opcional.
- Dependencias: MapLibre GL JS CDN, Esri raster Hybrid/Satellite, OpenTopoMap raster, OpenFreeMap y DEM externo Terrarium/Mapzen para terreno 3D.
- Relacion: publicado a `/local/rainmapper-maplibre`. Satellite+ es la capa inicial recomendada; combina imagen Esri con orientacion vectorial OpenFreeMap. Desde `0.2.58`, Settings permite elegir mapa base, filtrar por lluvia minima y filtrar por fuente de estacion. Desde `0.2.71`, el filtro `Source` muestra badges de estado por fuente si existe `data/source_status.json`; en escritorio, desde zoom 9, la ficha de estacion tambien aparece por hover sin cambiar el comportamiento tactil de movil. El visor incluye un boton de orientacion norte que solo resetea el `bearing`. El terreno 3D se activa desde Settings, esta apagado por defecto y se reaplica al cambiar de estilo porque `setStyle` reemplaza las fuentes del mapa. Una pulsacion larga sobre el mapa consulta altitud DEM leyendo directamente el tile Terrarium externo y decodificando el pixel RGB, no mediante `queryTerrainElevation`; el disparador usa eventos MapLibre y `contextmenu` para funcionar tanto en local como servido desde HA.

## Modelo de datos
Persistencia por CSV:

- Historicos incrementales en `Data/*_incremental.csv`.
- Listados/metadata de estaciones en `Data/estacions_*.csv`.
- CSV preparados para mapas en `Tomap/01_Tomap_Last_day.csv`, `02_Tomap_Last_week.csv`, etc.
- Ultimos registros en `Tomap/LastXX_rains.csv`; por defecto `Last30_rains.csv`, configurable con `RAINMAPPER_LAST_RAINS_HISTORY` o la opcion HA `last_rains_history`.
- Metricas Wunderground en `Data/metricas_wunderground.csv`.
- Estado de fuentes en `Data/source_status.json`, con entradas para Meteoclimatic, Meteocat y Wunderground. Estados actuales: `OK`, `DISABLED`, `STALE`, `NOK` y `PENDING`. `STALE` indica que la fuente fallo pero se reutilizo incremental previo. El payload puede incluir `duration_seconds`, `started_at`, `finished_at` y `timings`; los subtiempos actuales se usan especialmente para Meteocat.
- GeoJSON publicados en `PublicData/*.geojson` y `/config/www/rainmapper-data`.

Campos relevantes detectados o usados:

- `Codi Estació` / codigo de estacion.
- `Source` en GeoJSON, inferido por `tomap_to_geojson.py` desde el codigo de estacion: `ES...` con longitud minima 15 para Meteoclimatic, `I...` para Wunderground, codigos de longitud 2 para Meteocat, resto `Unknown` con aviso en stdout.
- `Latitud`, `Longitud`.
- lluvia acumulada por periodo.
- municipio/provincia/altitud.
- historico de ultimas lluvias y temperaturas max/min para popup (`Data_Pluja_XX`, `Pluja_Diaria_XX`, `Temp_Max_XX`, `Temp_Min_XX`). La configuracion por defecto genera hasta 30 registros, `last_rains_history` permite cambiarlo en HA, y los visores detectan dinamicamente cuantos hay en el GeoJSON.

Schemas completos: pendiente de confirmar en detalle leyendo todos los CSV y funciones pandas.

## Gestion de estado
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
- OpenTopoMap y Esri: tiles raster usados por Leaflet y MapLibre.
- Terrarium/Mapzen DEM externo: fuente `raster-dem` opcional para terrain 3D en MapLibre. No se empaqueta dentro de Docker ni se publica desde `/config/www`.

No incluir secretos en codigo ni documentacion.

## Configuracion
- `requirements.txt`: dependencias Python raiz.
- `rainmapper-app/app/requirements.txt`: dependencias Python app.
- `Dockerfile`: Docker local.
- `docker-compose.yml`: Docker local con volumenes.
- `rainmapper-app/Dockerfile`: Docker HA app.
- `rainmapper-app/config.yaml`: metadata y schema HA.
- Meteocat/Socrata: timeout y reintentos configurables mediante `meteocat_request_timeout` y `meteocat_max_attempts` en HA, o `RAINMAPPER_METEOCAT_REQUEST_TIMEOUT`/`RAINMAPPER_METEOCAT_MAX_ATTEMPTS` en Docker local.
- `repository.yaml`: metadata repositorio HA.
- `.gitignore`: excluye datos, caches, venv, tests locales y scripts antiguos.
- `.dockerignore`: excluye datos locales, repo HA y material no necesario para imagen local.
- `const.py`: defaults locales.
- `rainmapper-app/app/const.py`: defaults dentro de app.

No detectado: `package.json`, `pyproject.toml`, Makefile, ESLint, Prettier, pytest config.

## Testing
Hay un smoke test versionado en `scripts/smoke-test.sh` y un primer bloque de tests funcionales con `unittest` en `tests/`.

Validaciones existentes/recomendadas:

```bash
./scripts/smoke-test.sh
.venv/bin/python -m unittest discover -s tests
./scripts/sync-app-files.sh
python -m py_compile Rainmapper.py Rainmapper_Client.py tomap_to_geojson.py rainmapper-app/app/web_server.py
node --check leaflet-viewer/app.js
node --check maplibre-viewer/app.js
docker compose build rainmapper
docker compose run --rm -e MODE=help rainmapper
git diff --check
```

Cobertura: el smoke test valida sintaxis Python/JS/shell, ejecuta `unittest`, conversion GeoJSON minima con `ignore_stations_tomap.txt`, reconstruccion con poco historico para columnas `Last*_rains`, versionado HA, sincronizacion de copias raiz/app HA y whitespace de Git. Los tests en `tests/test_tomap_to_geojson.py` cubren fixtures funcionales de conversion Tomap -> GeoJSON, estaciones ignoradas, coordenadas invalidas y columnas obligatorias. `scripts/sync-app-files.sh` copia scripts raiz y visores a `rainmapper-app/app` como practica operativa, sin resolver aun la duplicidad arquitectonica. `scripts/check-history.py` valida historicos CSV de forma basica. Las pruebas funcionales completas de Docker/HA/movil siguen siendo principalmente manuales.

## Build y despliegue
Docker local:

```bash
docker compose build rainmapper
docker compose run --rm rainmapper
```

`MODE=maps` y `MODE=all` generan tanto mapas Bokeh como GeoJSON local en `docker-data/PublicData`.

Home Assistant:

- El repo se anade como repositorio de apps/add-ons en HA.
- HA detecta `repository.yaml` y `rainmapper-app/config.yaml`.
- Desde `0.2.57`, `rainmapper-app/config.yaml` define `image: ghcr.io/cginebrosa/rainmapperha`, por lo que HA debe descargar la imagen versionada en vez de construirla localmente.
- Desde `0.2.60`, el flujo normal publica la imagen multi-arch `amd64`/`arm64` desde el Mac con `scripts/build-push-ha-image.sh` antes de subir el commit de version. Esto evita que HA vea un update antes de que exista la imagen en GHCR.
- `scripts/build-push-ha-image.sh` publica dos tags: `<version>` y `latest`. Home Assistant instala la etiqueta versionada que corresponde a `config.yaml`; `latest` queda solo como conveniencia operativa.
- El script limpia etiquetas locales antiguas de `ghcr.io/cginebrosa/rainmapperha` despues de un push correcto y conserva por defecto las dos ultimas versiones locales mas `latest`.
- `.github/workflows/build-rainmapper-app.yml` queda como fallback manual (`workflow_dispatch`), no como publicacion automatica en cada push.
- Los updates se distribuyen publicando primero la imagen localmente, subiendo despues el commit a GitHub, y usando `Check for updates`/`Update` en HA.

## Convenciones de codigo
- Scripts Python monoliticos con constantes globales y funciones procedurales.
- Configuracion por variables de entorno y argumentos CLI.
- Persistencia por CSV y directorios fijos.
- WebUI construida con HTML generado en Python.
- JS de visores sin bundler ni framework.
- Logs operativos principales y webUI HA en ingles; README/DOCS de la app HA siguen en espanol por decision operativa actual.
- Scripts de mantenimiento/desarrollo (`.py`, `.sh` u otros) deben incluir documentacion interna en ingles: cabecera de proposito y comentarios breves antes de bloques o funciones no obvias. No hace falta comentar cada linea, pero el flujo debe poder entenderse sin depender del historial del chat.
- Errores Wunderground se clasifican por patrones en logs.
- Cambios de core deben duplicarse en raiz y `rainmapper-app/app`.

## Riesgos arquitectonicos
- Duplicidad de codigo entre raiz y app HA.
- Acoplamiento fuerte a nombres/rutas CSV.
- Scraper Wunderground fragil ante cambios HTML o estaciones desaparecidas.
- Proteccion automatica de historicos limitada: existen `scripts/check-history.py`, `scripts/backup-data.sh` y smoke checks, pero no una suite funcional completa de regresion historica.
- `web_server.py` concentra demasiadas responsabilidades.
- Gestion de version dispersa entre `config.yaml`, `CHANGELOG.md`, assets y Dockerfile.
- API keys de mapas cliente son visibles en navegador si se usan tiles externos con token.
- Bokeh, Leaflet y MapLibre conviven; MapLibre es el visor principal recomendado, Leaflet queda como fallback publicado y Bokeh como referencia/compatibilidad.
