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
- Librerias de validacion: pendiente de confirmar.
- Librerias HTTP/API: `requests`, `sodapy_local`, `googlemaps`.
- Librerias de testing: no detectadas.
- Base de datos: no hay base de datos detectada; persistencia por CSV.
- Despliegue: GitHub como repositorio de app HA, Home Assistant construye/instala la app.

## Estructura de carpetas
- `rainmapper-app/`: paquete de Home Assistant.
- `rainmapper-app/app/`: codigo que entra en la imagen HA.
- `leaflet-viewer/`: fuente del visor Leaflet en raiz.
- `maplibre-viewer/`: fuente del visor MapLibre en raiz.
- `scripts/`: utilidades versionadas de desarrollo; contiene `smoke-test.sh`, `sync-app-files.sh`, `backup-data.sh` y `check-history.py`.
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
6. `Rainmapper.py` produce CSV `Tomap` para los periodos acumulados.
7. `Rainmapper_Client.py` genera HTML Bokeh en `Plots`.
8. `tomap_to_geojson.py` genera GeoJSON desde `Tomap`.
9. `web_server.py` publica HTML, GeoJSON y visores estaticos en `/config/www`.
10. Home Assistant sirve los mapas por `/local/...`.

## Componentes, modulos o capas principales

### Core de descarga y datos
- Ruta: `Rainmapper.py` y `rainmapper-app/app/Rainmapper.py`.
- Responsabilidad: descarga Meteocat, Meteoclimatic y Wunderground; actualiza historicos; genera `Tomap`; metricas Wunderground.
- Dependencias: pandas, requests, BeautifulSoup, googlemaps, `meteoclimatic_local`, `sodapy_local`, `util`.
- Relacion: alimenta `Rainmapper_Client.py` y `tomap_to_geojson.py`.

### Generador Bokeh
- Ruta: `Rainmapper_Client.py` y copia en app.
- Responsabilidad: leer `Tomap` y generar HTML Bokeh en `Plots`.
- Dependencias: Bokeh, pandas, Google Maps key.
- Relacion: salida publicada por `web_server.py` a `/config/www/Plots`.

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
- Relacion: entorno seguro de pruebas en Mac.

### Leaflet viewer
- Ruta: `leaflet-viewer/` y `rainmapper-app/app/leaflet-viewer/`.
- Responsabilidad: visor web movil basado en Leaflet y GeoJSON.
- Dependencias: Leaflet CDN, tiles raster.
- Relacion: publicado a `/local/rainmapper-leaflet`.

### MapLibre viewer
- Ruta: `maplibre-viewer/` y `rainmapper-app/app/maplibre-viewer/`.
- Responsabilidad: visor web experimental con mapas vectoriales/raster y filtros cliente de estaciones.
- Dependencias: MapLibre GL JS CDN, Esri raster Hybrid/Satellite, OpenTopoMap raster, OpenFreeMap y Jawg opcional.
- Relacion: publicado a `/local/rainmapper-maplibre`. Satellite+ es la capa inicial recomendada; combina imagen Esri con orientacion vectorial OpenFreeMap. Desde `0.2.58`, Settings permite filtrar por lluvia minima y por fuente de estacion.

## Modelo de datos
Persistencia por CSV:

- Historicos incrementales en `Data/*_incremental.csv`.
- Listados/metadata de estaciones en `Data/estacions_*.csv`.
- CSV preparados para mapas en `Tomap/01_Tomap_Last_day.csv`, `02_Tomap_Last_week.csv`, etc.
- Ultimos registros en `Tomap/Last21_rains.csv`.
- Metricas Wunderground en `Data/metricas_wunderground.csv`.
- GeoJSON publicados en `PublicData/*.geojson` y `/config/www/rainmapper-data`.

Campos relevantes detectados o usados:

- `Codi Estació` / codigo de estacion.
- `Source` en GeoJSON, inferido por `tomap_to_geojson.py` desde el codigo de estacion: `ES...` con longitud minima 15 para Meteoclimatic, `I...` para Wunderground, codigos de longitud 2 para Meteocat, resto `Unknown` con aviso en stdout.
- `Latitud`, `Longitud`.
- lluvia acumulada por periodo.
- municipio/provincia/altitud.
- historico de ultimas lluvias y temperaturas max/min para popup.

Schemas completos: pendiente de confirmar en detalle leyendo todos los CSV y funciones pandas.

## Gestion de estado
- Estado persistente principal: CSV en filesystem.
- Estado runtime webUI: diccionario global `RUN_STATE` en `web_server.py`.
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
- La portada muestra `RAINMAPPER_APP_VERSION` en el panel de estado y sus enlaces hacia visores `/local/...` incluyen `?v=<RAINMAPPER_APP_VERSION>` para reducir cache obsoleta en el frontend de Home Assistant.

Home Assistant publica:

- `/local/Plots/...`: Bokeh HTML.
- Jawg Maps: estilos/capas opcionales con token `JAWGMAPS_API_KEY`/`jawgmaps_api_key`.
- OpenTopoMap y Esri: tiles raster usados por Leaflet y MapLibre.

No incluir secretos en codigo ni documentacion.

## Configuracion
- `requirements.txt`: dependencias Python raiz.
- `rainmapper-app/app/requirements.txt`: dependencias Python app.
- `Dockerfile`: Docker local.
- `docker-compose.yml`: Docker local con volumenes.
- `rainmapper-app/Dockerfile`: Docker HA app.
- `rainmapper-app/config.yaml`: metadata y schema HA.
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
- Logs mixtos en ingles/espanol.
- Errores Wunderground se clasifican por patrones en logs.
- Cambios de core deben duplicarse en raiz y `rainmapper-app/app`.

## Riesgos arquitectonicos
- Duplicidad de codigo entre raiz y app HA.
- Acoplamiento fuerte a nombres/rutas CSV.
- Scraper Wunderground fragil ante cambios HTML o estaciones desaparecidas.
- No hay tests automaticos para proteger historicos.
- `web_server.py` concentra demasiadas responsabilidades.
- Gestion de version dispersa entre `config.yaml`, `CHANGELOG.md`, assets y Dockerfile.
- API keys de mapas cliente son visibles en navegador si se usan tiles externos con token.
- Bokeh, Leaflet y MapLibre conviven; MapLibre es el visor principal recomendado, Leaflet queda como fallback publicado y Bokeh como referencia/compatibilidad.
