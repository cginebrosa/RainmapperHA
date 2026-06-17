# Codex Handoff

## Objetivo de la app
RainmapperHA empaqueta Rainmapper como app de Home Assistant. La app descarga datos meteorologicos de varias fuentes, preserva historico en CSV, genera ficheros intermedios `Tomap`, crea mapas HTML clasicos y publica visores web modernos basados en GeoJSON para consultar lluvia acumulada por estacion.

Objetivo a largo plazo: convertir Rainmapper en una plataforma estable para recopilar, preservar, analizar y visualizar datos meteorologicos de multiples fuentes, automatizada desde Home Assistant, con visores web moviles y, mas adelante, una app iOS/Android con autenticacion, permisos de acceso y posible control comercial por mapas o zonas.

## Estado actual del proyecto
El proyecto tiene dos empaquetados principales:

- Docker local para Mac/desarrollo en la raiz del repositorio.
- App de Home Assistant en `rainmapper-app/`.

La app de Home Assistant esta funcionando como servicio `serve`, con webUI por ingress/sidebar, schedule interno, ejecuciones manuales `update`, `maps` y `all`, publicacion en `/config/www`, visores Bokeh, Leaflet y MapLibre, metricas basicas de Wunderground y fichero manual para ignorar estaciones anomalas en los GeoJSON.

El desarrollo actual esta en fase de operacion y mejora incremental de visores: Leaflet y MapLibre funcionan bien en iPhone y, de momento, se mantienen publicados ambos. Bokeh se mantiene como referencia y compatibilidad. Hay deuda tecnica por duplicidad entre scripts de raiz y scripts copiados dentro de `rainmapper-app/app`.

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
- Testing formal: existe `scripts/smoke-test.sh` para validaciones rapidas; no se ha detectado `pytest`, `package.json`, Makefile ni framework de test completo.
- Lint/format formal: pendiente de confirmar. No se ha detectado configuracion dedicada.

## Documentos de referencia
- [architecture.md](architecture.md)
- [todo.md](todo.md)
- [decisions.md](decisions.md)
- [history-safety.md](history-safety.md)
- [mobile-app-architecture.md](mobile-app-architecture.md)

Tambien existen documentos de uso:

- [../README.md](../README.md)
- [../README_DOCKER.md](../README_DOCKER.md)
- [../rainmapper-app/README.md](../rainmapper-app/README.md)
- [../rainmapper-app/DOCS.md](../rainmapper-app/DOCS.md)
- [../rainmapper-app/CHANGELOG.md](../rainmapper-app/CHANGELOG.md)

## Estructura relevante del proyecto
- `Rainmapper.py`: script principal de descarga, normalizacion, historico y generacion de CSV `Tomap`.
- `Rainmapper_Client.py`: generador de mapas HTML clasicos con Bokeh.
- `tomap_to_geojson.py`: conversor de CSV `Tomap` a GeoJSON para Leaflet/MapLibre.
- `const.py`: constantes y defaults de ejecucion local.
- `run.sh`: wrapper Docker local.
- `Dockerfile`: imagen Docker local.
- `docker-compose.yml`: runner Docker local con volumenes persistentes.
- `leaflet-viewer/`: visor Leaflet fuente para pruebas locales/publicacion.
- `maplibre-viewer/`: visor MapLibre fuente para pruebas locales/publicacion.
- `scripts/smoke-test.sh`: smoke test versionado para validar sintaxis, GeoJSON minimo con `ignore_stations_tomap.txt`, reconstruccion con poco historico, versiones y sincronizacion raiz/app HA.
- `scripts/sync-app-files.sh`: sincroniza scripts raiz y visores hacia `rainmapper-app/app` como practica operativa mientras exista duplicidad.
- `scripts/backup-data.sh`: crea backups `.tar.gz` de `Data` o de una raiz de datos Rainmapper.
- `scripts/check-history.py`: valida CSV historicos y permite comparar una copia antes/despues.
- `docs/mobile-app-architecture.md`: arquitectura inicial propuesta para futura app iOS/Android con API, auth, permisos, favoritos y filtro de lluvia minima.
- `rainmapper-app/`: app de Home Assistant.
- `rainmapper-app/app/`: copia operativa de scripts Python y visores que entran en la imagen de HA.
- `rainmapper-app/app/web_server.py`: webUI, schedule, publicacion a `/config/www`, controles de estaciones y ejecucion de jobs.
- `Data/`, `Tomap/`, `Plots/`: datos generados locales. Estan ignorados por Git.
- `docker-data/`: datos persistentes del Docker local. Esta ignorado por Git.

## Ficheros clave

### `Rainmapper.py`
- Proposito: descarga datos de Meteocat, Meteoclimatic y Wunderground; actualiza historicos; genera CSV `Tomap`; guarda metricas de Wunderground.
- Estado actual: funcional, con argumentos CLI para fuentes, fechas, threads, intentos, log completo Wunderground y patrones Meteoclimatic multiples. El fichero de estaciones ignoradas para mapas nuevos se aplica en `tomap_to_geojson.py`, no directamente aqui.
- Riesgos: contiene mucha logica acoplada, pandas sobre CSV historicos y scraping de Wunderground. No tocar sin preservar historicos y probar con Docker local.

### `rainmapper-app/app/Rainmapper.py`
- Proposito: copia del script principal dentro de la app HA.
- Estado actual: debe mantenerse alineado con `Rainmapper.py` cuando se prueben cambios en local y se quieran llevar a HA.
- Riesgos: duplicidad manual. Es facil corregir raiz y olvidar la copia de la app.

### `Rainmapper_Client.py`
- Proposito: genera mapas HTML clasicos Bokeh desde `Tomap`.
- Estado actual: sigue funcionando y se publica en `/local/Plots`.
- Riesgos: depende de Google Maps API key y Bokeh. A medio plazo puede quedar como compatibilidad si Leaflet/MapLibre sustituyen su uso.

### `tomap_to_geojson.py`
- Proposito: convierte los siete CSV `Tomap` a GeoJSON para visores nuevos.
- Estado actual: soporta 1, 7, 14, 21, 30, 60 y 90 dias; incluye metadata de generacion; permite ignorar estaciones desde `ignore_stations_tomap.txt`.
- Riesgos: si cambia el schema de `Tomap`, hay que actualizar este conversor y validar ambos visores.

### `rainmapper-app/app/web_server.py`
- Proposito: webUI HA, endpoints de ejecucion, schedule, publicacion de mapas, estado, logs, controles de errores Wunderground.
- Estado actual: pieza central de la app HA. Sirve modo `serve` en puerto 8099 e ingress.
- Riesgos: mucha responsabilidad en un unico fichero. Cambios aqui pueden afectar schedule, webUI, publicacion y acciones manuales.

### `run.sh`
- Proposito: wrapper Docker local. Traduce variables de entorno a argumentos de `Rainmapper.py` y `Rainmapper_Client.py`.
- Estado actual: soporta modos `once/update`, `maps`, `all`, `help`, `schedule`.
- Riesgos: el modo `schedule` local es distinto del modo `serve` de HA; no confundir.

### `rainmapper-app/run.sh`
- Proposito: entrypoint de HA. Lee `/data/options.json`, prepara `/share/rainmapper`, crea symlinks, exporta variables y arranca el modo elegido.
- Estado actual: crea `stations.txt` e `ignore_stations_tomap.txt` si no existen y respeta los ficheros existentes.
- Riesgos: tocarlo puede romper persistencia de datos o reinstalaciones de HA.

### `rainmapper-app/config.yaml`
- Proposito: metadata, opciones y schema de Home Assistant.
- Estado actual: version `0.2.53`, ingress, sidebar, opciones de schedule, API keys, mapas, fuentes y publish. La `0.2.46` fue validada en Home Assistant con `Run all`; el log interno sale en ingles y el schedule esta funcionando. La webUI muestra la version runtime en el panel de estado, agrupa las tarjetas de status en filas explicitas y los enlaces de visores incluyen cache-buster de version para evitar cargas obsoletas en HA.
- Riesgos: cualquier cambio de schema puede afectar updates de HA. Revisar compatibilidad de opciones existentes.

### `rainmapper-app/Dockerfile`
- Proposito: construye imagen de la app HA.
- Estado actual: usa Python 3.11 slim. Version alineada con `rainmapper-app/config.yaml` en `0.2.53`.
- Riesgos: puede confundir updates o diagnostico de version si labels/env no se actualizan junto con `config.yaml` en futuros bumps.

### `leaflet-viewer/` y `rainmapper-app/app/leaflet-viewer/`
- Proposito: visor Leaflet estatico.
- Estado actual: funcional, con capas Topographic/Hybrid y Jawg opcional solo si hay API key no vacia, leyenda, selector de periodo, popups moviles y preservacion de vista al cambiar periodo.
- Riesgos: se publica solo en `/local/rainmapper-leaflet`; la ruta legacy `/local/rainmapper-mobile` fue retirada porque Cloudflare ya redirige a los visores actuales.

### `maplibre-viewer/` y `rainmapper-app/app/maplibre-viewer/`
- Proposito: visor experimental MapLibre con mapas vectoriales y raster.
- Estado actual: funcional, con Satellite+ raster/vectorial por defecto, Hybrid raster, Topographic raster, OpenFreeMap Liberty y Jawg Street/Terrain opcional.
- Riesgos: la base MapLibre ya cubre las capas clave de Leaflet, pero la version `0.2.53` queda pendiente de validacion visual en HA/iPhone antes de decidir si MapLibre pasa a visor principal unico. Satellite+ mezcla tiles Esri con orientacion vectorial OpenFreeMap y puede requerir ajustes visuales tras probar en movil.

### `docker-compose.yml`
- Proposito: ejecucion Docker local con volumenes en `docker-data`.
- Estado actual: build local `rainmapperha:test`, modo por defecto `once`, variables de entorno y volumenes persistentes.
- Riesgos: no incluye datos en Git; requiere `docker-data/stations.txt` y API keys locales segun uso.

## Funcionalidades ya implementadas
- Docker local reproducible para Mac/desarrollo: `Dockerfile`, `docker-compose.yml`, `run.sh`.
- App Home Assistant instalable desde repo GitHub: `repository.yaml`, `rainmapper-app/config.yaml`.
- Modo `serve` con webUI e ingress/sidebar: `rainmapper-app/app/web_server.py`.
- Ejecuciones manuales `update`, `maps`, `all`: `web_server.py`, `run.sh`.
- Schedule interno con multiples horas y dias de semana: `web_server.py`, `config.yaml`.
- Persistencia en `/share/rainmapper`: `rainmapper-app/run.sh`.
- Publicacion de mapas a `/config/www`: `web_server.py`.
- Mapas Bokeh publicados en `/local/Plots`: `Rainmapper_Client.py`, `web_server.py`.
- Leaflet viewer publicado en `/local/rainmapper-leaflet/index.html`: `leaflet-viewer/`, `web_server.py`.
- MapLibre viewer publicado en `/local/rainmapper-maplibre/index.html`: `maplibre-viewer/`, `web_server.py`.
- GeoJSON para 1/7/14/21/30/60/90 dias: `tomap_to_geojson.py`.
- Ignorar estaciones anomalas en GeoJSON sin borrar historico: `ignore_stations_tomap.txt`, `tomap_to_geojson.py`.
- Wunderground full log configurable y resumen de errores: `Rainmapper.py`, `config.yaml`.
- Control webUI para desactivar/reactivar estaciones Wunderground por 404 o parse error: `web_server.py`.
- Metricas de tiempos por estacion Wunderground en `Data/metricas_wunderground.csv`: `Rainmapper.py`.
- Meteoclimatic con multiples patrones separados por coma, punto y coma o ` - `: `Rainmapper.py`.
- Google Maps API key por variable/opcion, sin hardcode confirmado en ficheros inspeccionados.
- Jawg Maps opcional en visores si existe `JAWGMAPS_API_KEY`/`jawgmaps_api_key`.
- Satellite+ en MapLibre combina Esri World Imagery con carreteras, limites y etiquetas vectoriales de OpenFreeMap.

## Funcionalidades parcialmente implementadas
- Leaflet y MapLibre: funcionales y validados en iPhone; se mantienen publicados ambos de momento. MapLibre `0.2.48` anade Satellite+ sobre las capas Hybrid/Topographic raster de `0.2.47` y puede reducir la necesidad futura de Leaflet si se valida bien.
- Sustitucion futura de Bokeh: Leaflet/MapLibre ya existen, pero Bokeh sigue publicado y documentado.
- Ruta legacy `/local/rainmapper-mobile`: retirada; Cloudflare redirige a `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre`.
- App settings link: usa Supervisor self-info; muestra el enlace recomendado por defecto y deja rutas alternativas en una seccion avanzada.
- Versionado HA: `config.yaml`, labels Docker y banner runtime estan alineados en `0.2.53`.
- Internacionalizacion: la webUI visible de HA, metadata HA, changelog y logs operativos principales del core estan en ingles. README/DOCS de la app HA siguen en espanol porque de momento la app es de uso propio; no hay sistema i18n.

## Funcionalidades pendientes
- Validar MapLibre/Leaflet `0.2.53` en HA/iPhone; si funciona bien, reevaluar si MapLibre puede pasar a visor principal unico y Leaflet queda como fallback.
- Mantener Leaflet y MapLibre publicados de momento.
- Decidir retirada de Bokeh o mantenerlo como referencia.
- Crear tests automaticos mas completos; existe smoke test versionado para checks rapidos, incluyendo `ignore_stations_tomap.txt` y reconstruccion con poco historico.
- Mejorar separacion entre core de datos, webUI y visores.
- Preconstruir imagen Docker HA multi-arch mas adelante, cuando la app este mas estable, para acelerar updates en RPi y evitar builds locales lentos.
- Analitica historica de metricas Wunderground, posiblemente con InfluxDB/Grafana.
- Autenticacion/autorizacion real para una futura app publica iOS/Android.
- Definir modelo de producto/acceso si se venden mapas o zonas.
- Ideas para futura app iOS/Android: favoritos de estaciones y filtro por lluvia minima en el periodo seleccionado.
- Arquitectura inicial de app movil documentada en [mobile-app-architecture.md](mobile-app-architecture.md).

## Bugs abiertos o problemas conocidos
- Duplicidad de scripts entre raiz y `rainmapper-app/app`; mitigada operativamente con `scripts/sync-app-files.sh` y smoke test, sin refactor estructural todavia.
- No hay tests formales detectados.
- Wunderground es el cuello de botella principal; se ejecuta con `max_threads=1` en RPi para no cargarla. Aun asi, el rendimiento actual es aceptable: update completo + generacion de mapas tarda unos 7 minutos. Observabilidad/timeout queda en baja prioridad hasta acumular mas observaciones.
- Jawg Maps en navegador implica que el token de tiles puede ser visible al cliente; debe restringirse por dominio si el proveedor lo permite.
- Los historicos CSV son el valor central del proyecto; no deben borrarse ni reescribirse sin backup. Ver [history-safety.md](history-safety.md).
- Algunas carpetas generadas (`Data`, `Tomap`, `Plots`, `docker-data`, `docker-empty-test`) existen localmente pero estan ignoradas por Git.

## Variables de entorno y configuracion
- `GMAP_API_KEY`: clave Google Maps; usada por `const.py`, `Rainmapper.py` y mapas Bokeh. Obligatoria si se usan funciones que requieren Google Maps; no debe ir en Git.
- `JAWGMAPS_API_KEY`: token Jawg Maps; usado para activar capas Jawg en Leaflet/MapLibre. Opcional.
- `SODAPY_APPTOKEN`: token Socrata/Meteocat mencionado solo en codigo comentado; actualmente no se usa porque `socrata_token` se fija a `None`. Pendiente de confirmar si debe reactivarse en el futuro.
- `SUPERVISOR_TOKEN`: token inyectado por Home Assistant; usado por `web_server.py` para consultar self-info del addon. Lo proporciona HA.
- `RAINMAPPER_MODE` / `MODE`: modo Docker local (`once`, `update`, `maps`, `all`, `schedule`, `help`).
- `RAINMAPPER_SCHEDULE_TIME` / `SCHEDULE_TIME`: hora o horas de schedule local/HA segun wrapper.
- `RAINMAPPER_TIMEZONE` / `TIMEZONE`: zona horaria, por defecto `Europe/Madrid`.
- `RAINMAPPER_DAYS_INIT` / `DAYS_INIT`: inicio de rango relativo de dias.
- `RAINMAPPER_DAYS_END` / `DAYS_END`: fin de rango relativo de dias.
- `RAINMAPPER_CREATE_WUNDERGROUND` / `CREATE_WUNDERGROUND`: activa Wunderground.
- `RAINMAPPER_CREATE_METEOCLIMATIC` / `CREATE_METEOCLIMATIC`: activa Meteoclimatic.
- `RAINMAPPER_CREATE_METEOCAT` / `CREATE_METEOCAT`: activa Meteocat.
- `RAINMAPPER_METEOCLIMATIC_PATTERN` / `METEOCLIMATIC_PATTERN`: patron o patrones RSS Meteoclimatic.
- `RAINMAPPER_MAX_THREADS` / `MAX_THREADS`: threads Wunderground.
- `RAINMAPPER_MAX_ATTEMPTS` / `MAX_ATTEMPTS`: reintentos Wunderground.
- `RAINMAPPER_WUNDERGROUND_FULL_LOG` / `WUNDERGROUND_FULL_LOG`: log detallado por estacion.
- `RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE`: fichero de estaciones ignoradas al generar GeoJSON.

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

Sincronizar copias raiz -> app HA:

```bash
./scripts/sync-app-files.sh
```

Validaciones sintacticas usadas/recomendadas:

```bash
./scripts/smoke-test.sh
python -m py_compile Rainmapper.py Rainmapper_Client.py tomap_to_geojson.py rainmapper-app/app/web_server.py
node --check leaflet-viewer/app.js
node --check maplibre-viewer/app.js
git diff --check
```

Lint/format:

```text
pendiente de confirmar
```

Despliegue Home Assistant:

```text
Subir cambios a GitHub, hacer Check for updates en Home Assistant y actualizar la app desde la UI de HA. No hay comando CLI de despliegue confirmado.
```

## Flujo de ejecucion de la app
1. Home Assistant arranca `rainmapper-app/run.sh`.
2. `run.sh` lee `/data/options.json`, crea `/share/rainmapper` y sus subcarpetas, crea `stations.txt` e `ignore_stations_tomap.txt` si faltan y no sobrescribe los existentes.
3. `run.sh` crea symlinks hacia `/app/Data`, `/app/Tomap`, `/app/Plots`, `/app/PublicData` y exporta variables.
4. En modo recomendado `serve`, arranca `web_server.py` en `0.0.0.0:8099`.
5. La webUI permite lanzar `update`, `maps` o `all`.
6. `update` ejecuta `Rainmapper.py` y actualiza CSV historicos y `Tomap`.
7. `maps` ejecuta `Rainmapper_Client.py`, genera Bokeh HTML y despues `tomap_to_geojson.py` para los visores nuevos.
8. Si `publish_to_www` esta activo, la app copia HTML y visores a `/config/www`.
9. HA sirve los resultados como `/local/Plots`, `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre`.

## Integraciones externas
- Meteocat / Socrata: usado desde `Rainmapper.py` y `sodapy_local`. Endpoint exacto/datasets: pendiente de confirmar en detalle.
- Meteoclimatic RSS: usado desde `meteoclimatic_local`; `meteoclimatic_pattern` filtra estaciones.
- Wunderground: scraping via `requests`, `BeautifulSoup` y parser local en `util/`.
- Google Maps: `googlemaps` Python client y Bokeh `gmap`; clave en `GMAP_API_KEY`/`gmap_api_key`.
- Home Assistant Supervisor API: `web_server.py` usa `SUPERVISOR_TOKEN` para resolver informacion del addon.
- OpenTopoMap / Esri / OpenFreeMap / Jawg Maps: proveedores de tiles/estilos para visores.
- Cloudflare/domain externo: usado operacionalmente para exponer HA/visor, pero no hay configuracion de Cloudflare versionada en el repo.

## Decisiones importantes ya tomadas
Resumen:

- Home Assistant se ejecuta en modo `serve` para mantener sidebar y webUI.
- Los datos historicos viven fuera del contenedor.
- Docker local en Mac se conserva como entorno de pruebas.
- Bokeh, Leaflet y MapLibre conviven; Leaflet y MapLibre se mantienen publicados de momento.
- Los visores nuevos usan GeoJSON generado desde `Tomap`.
- Las estaciones anomalas se ignoran en GeoJSON mediante fichero manual, sin borrar historico.
- Wunderground usa un thread por defecto en RPi.

Detalle en [decisions.md](decisions.md).

## Riesgos antes de continuar
- No borrar ni limpiar `Data`, `Tomap`, `Plots`, `/share/rainmapper` ni `docker-data` sin backup explicito.
- No modificar `rainmapper-app/run.sh` sin revisar persistencia y symlinks.
- No modificar `Rainmapper.py` sin revisar impacto en historicos incrementales.
- Mantener sincronizadas raiz y `rainmapper-app/app` si se cambia core Python o visores; usar `./scripts/sync-app-files.sh` y validar con `./scripts/smoke-test.sh`.
- No introducir API keys reales en Git.
- Validar cambios de visores en movil real, especialmente iPhone.
- Ejecutar `./scripts/smoke-test.sh` antes de cerrar cambios relevantes.
- Antes de tocar pandas o escritura CSV, usar `./scripts/backup-data.sh` y `./scripts/check-history.py` sobre una copia.

## Proximo paso recomendado
Continuar con mejoras de bajo riesgo o decidir si se aborda la separacion estructural del core duplicado.

## Prompt recomendado para nueva sesion de Codex
"Lee primero docs/codex-handoff.md. Después consulta docs/architecture.md, docs/todo.md y docs/decisions.md. No modifiques código todavía. Primero resume el objetivo de la app, el estado actual, los ficheros clave, lo que funciona, lo que falta y el siguiente paso recomendado."
