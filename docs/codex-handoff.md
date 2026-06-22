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

La app de Home Assistant esta configurada para funcionar como servicio `serve`, con webUI por ingress/sidebar, schedule interno, ejecuciones manuales `update`, `maps` y `all`, publicacion en `/config/www`, visores Bokeh, Leaflet y MapLibre, metricas basicas de Wunderground y fichero manual para ignorar estaciones anomalas en los GeoJSON. El funcionamiento en la instalacion real de HA ha sido validado manualmente por el usuario hasta la version `0.2.82`; esa validacion no es reproducible solo desde el repositorio. La version `0.2.91` compacta la cabecera de MapLibre protegido mostrando solo fecha generada y `username (role)`; pendiente de validar en HA.

El desarrollo actual esta en fase de operacion y mejora incremental de visores. Leaflet y MapLibre se mantienen publicados ambos; el usuario ha reportado que funcionan bien en iPhone, pendiente de confirmar con pruebas automatizadas o reproducibles desde el repo. Bokeh se mantiene como referencia y compatibilidad. La duplicidad fisica principal entre raiz y `rainmapper-app/app` fue retirada: la imagen HA se construye desde la raiz del repositorio y `rainmapper-app/app` queda reservado para codigo especifico de HA.

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
- `scripts/build-push-ha-image.sh`: publica desde el Mac la imagen multi-arch de la app HA en GHCR usando Docker Buildx; sube tags `<version>` y `latest`, y limpia etiquetas locales versionadas antiguas conservando por defecto las dos ultimas mas `latest`.
- `scripts/compare-tomap-builder.sh`: reconstruye `Tomap` con `python -m rainmapper_core.tomap` en un directorio temporal y compara el resultado con `docker-data/Tomap`.
- `scripts/docker-offline-functional-test.sh`: prueba funcional Docker sin red; construye la imagen local, monta datos temporales, ejecuta `rainmapper_core.tomap` y `rainmapper_core.geojson` dentro del contenedor y valida salidas sin tocar `docker-data`.
- `tests/`: tests funcionales offline con `unittest`; cubren `rainmapper_core.geojson`, `rainmapper_core.tomap`, `rainmapper_core.incremental_upsert` y un pipeline integrado `upsert -> Tomap -> GeoJSON`.
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
- Proposito: descarga datos de Meteocat, Meteoclimatic y Wunderground; actualiza historicos; guarda metricas de Wunderground; escribe `source_status.json`. Se ejecuta con `python -m rainmapper_core.rainmapper`; el wrapper raiz `Rainmapper.py` fue retirado.
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
- Estado actual: version local `0.2.91`, ingress, sidebar, imagen preconstruida `ghcr.io/cginebrosa/rainmapperha`, opciones de schedule, Google Maps API key, mapas, fuentes y publish. La webUI muestra la version runtime en el panel de estado, agrupa las tarjetas de status en filas explicitas, muestra estado separado por fuente (`Meteoclimatic`, `Meteocat`, `Wunderground`) y los enlaces de visores incluyen cache-buster de version para evitar cargas obsoletas en HA. La validacion de `Run all`, logs en ingles y schedule en la instalacion real de Home Assistant es manual/reportada por el usuario; pendiente de confirmar automaticamente. En `0.2.80`, el usuario ha validado manualmente en HA un `Run all` tras la refactorizacion core/app/local y todo parece correcto. En `0.2.78`, el usuario valido manualmente en HA `Run all` correctamente tras la fase 4 del refactor core. En `0.2.77`, el usuario valido manualmente `Run update` con exit code 0, `Generate maps` con exit code 0 y publicacion de visores con `v=0.2.77`.
- Riesgos: cualquier cambio de schema puede afectar updates de HA. Revisar compatibilidad de opciones existentes.

### `rainmapper-app/Dockerfile`
- Proposito: construye imagen de la app HA.
- Estado actual: usa Python 3.11 slim. Version alineada con `rainmapper-app/config.yaml` en `0.2.91`; tambien copia `users.example.json` para inicializar usuarios si falta configuracion persistente.
- Riesgos: puede confundir updates o diagnostico de version si labels/env no se actualizan junto con `config.yaml` en futuros bumps.

### `rainmapper_core/viewers/leaflet-viewer/` y `leaflet-viewer/`
- Proposito: visor Leaflet estatico.
- Estado actual: funcional, con capas Topographic/Hybrid, leyenda, selector de periodo, popups moviles y preservacion de vista al cambiar periodo.
- Riesgos: se publica solo en `/local/rainmapper-leaflet`; la ruta legacy `/local/rainmapper-mobile` fue retirada. Las redirecciones Cloudflare hacia los visores actuales fueron reportadas por el usuario y quedan pendientes de confirmar fuera del repositorio.

### `rainmapper_core/viewers/maplibre-viewer/` y `maplibre-viewer/`
- Proposito: visor principal MapLibre con mapas vectoriales/raster.
- Estado actual: funcional, con Satellite+ raster/vectorial por defecto, Hybrid raster, Topographic raster, OpenFreeMap Liberty, boton para orientar de nuevo al norte, consulta de altitud DEM por pulsacion larga y panel de settings con selector de mapa, filtros cliente por lluvia minima, fuente de estacion y terreno 3D. En `0.2.81` se moderniza la UI: cabecera clara, controles flotantes, selector inferior de periodo, leyenda vertical dinamica, creditos en boton de informacion y popups claros. En `0.2.82`, el usuario valida en HA que `/protected/maplibre/index.html` funciona con login: `admin` puede entrar desde Mac+iPhone y un usuario de prueba queda limitado a un dispositivo. La version `0.2.83` amplia esa autenticacion a `users.json` con `username`, `name`, `email`, roles `free/basic/pro/admin` y `max_devices`; esta parte esta testeada localmente y publicada en GHCR, pero pendiente de validacion HA.
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
- MapLibre viewer operativo en `/protected/maplibre/index.html`: `rainmapper_core/viewers/maplibre-viewer/`, `web_server.py`. Durante la validacion de Cloudflared/puerto 8099 se mantiene temporalmente `/local/rainmapper-maplibre/index.html` como fallback funcional con GeoJSON publicos; el codigo deja marcada la limpieza para retirarlo cuando la ruta protegida quede validada.
- GeoJSON para 1/7/14/21/30/60/90 dias: `rainmapper_core.geojson`.
- Ignorar estaciones anomalas en GeoJSON sin borrar historico: `ignore_stations_tomap.txt`, `rainmapper_core.geojson`.
- Filtros en MapLibre: settings del visor aplica filtros cliente por lluvia minima y por fuente de estacion sobre el periodo cargado para validar UX de futura app movil.
- Popups de estacion en Leaflet/MapLibre: muestran el resumen de estacion, lluvia acumulada, ultima lluvia del historico disponible (`DD/MM/AAAA · mm`) y un desplegable cerrado por defecto con los ultimos registros disponibles en el GeoJSON. El historico anade `Days ago`, mantiene cabecera sticky al hacer scroll y resalta visualmente las filas con lluvia. El visor detecta dinamicamente columnas `Data_Pluja_XX`; MapLibre incluye en Settings el control `Last rains history` para limitar cuantas filas se muestran. Rainmapper genera por defecto 30 registros recientes por estacion, configurable en HA con `last_rains_history` y en Docker local con `RAINMAPPER_LAST_RAINS_HISTORY`/`LAST_RAINS_HISTORY`.
- Terreno 3D en MapLibre: settings permite activar `3D terrain` y ajustar `Exaggeration` usando un DEM externo Terrarium/Mapzen como fuente `raster-dem`. El visor incluye un control flotante `2D`/`3D`, y en escritorio la tecla `t` alterna el mismo estado. No se incluye ningun DEM en la imagen Docker. Validado manualmente por el usuario en local, HA, Mac e iPhone; queda como funcionalidad definitiva por decision del 2026-06-18, aceptando la dependencia externa hasta que se decida si hace falta DEM propio.
- Consulta de altitud en MapLibre: una pulsacion larga sobre el mapa muestra un popup con cola apuntando al punto consultado y la altitud del DEM leyendo directamente el tile Terrarium externo y decodificando el pixel RGB. Se evita `queryTerrainElevation` para esta lectura porque en una prueba manual en Urus/Cerdanya (`42.35406, 1.85317`) devolvio `-4 m` aunque el tile DEM crudo devolvia unos `1259 m`; esta observacion queda pendiente de confirmar automaticamente. En HA no se disparaba la ventana incluso con Chrome limpio y tras generar mapas, por lo que `0.2.65` cambia el disparador de pulsacion larga a eventos propios de MapLibre y `contextmenu`, y ademas alinea los cache-busters internos de los visores. El cierre del popup de terreno limpia el estado activo igual que los popups de estacion para no bloquear el hover posterior en escritorio. En `0.2.77`, el usuario valida que MapLibre funciona bien en HA, Mac e iPhone tras anadir la cola del popup de terreno y el boton `2D`/`3D`; pendiente de confirmar mediante prueba automatizada o reproducible.
- `Source` en GeoJSON: `rainmapper_core.geojson` anade fuente inferida por codigo de estacion (`ES...` de longitud minima 15 para Meteoclimatic, `I...` para Wunderground, codigos de longitud 2 para Meteocat, resto `Unknown`). Si aparece `Unknown`, el conversor emite un `WARNING` en stdout.
- Autenticacion ligera MapLibre: `web_server.py` protege `/protected/maplibre/data/*.geojson` y `source_status.json`. En `0.2.82`, la ruta protegida fue validada manualmente en HA con `admin` desde Mac+iPhone y un usuario normal limitado a un dispositivo. La version `0.2.83` cambia el formato principal a `/share/rainmapper/users.json` con `username` para login, `name`, `email`, `password`, `role`, `enabled`, `max_devices` y `must_change_password`; el usuario valido en HA que el primer login creaba `users.json` desde la configuracion anterior. Despues se decide retirar completamente el formato anterior: `users.json` queda como unico formato soportado. Roles soportados: `free`, `basic`, `pro`, `admin`. Limites por defecto: `free=1`, `basic=2`, `pro=3`, `admin=0` ilimitado, con posible override por usuario. `run.sh` crea `users.json` desde `users.example.json` si no existe, y crea `devices.json` vacio si falta. La WebUI local incluye una pagina `Users` para usar desde Ingress/Home Assistant, con creacion de usuarios, activacion/desactivacion de acceso, cambios de rol/max_devices, establecimiento de nuevas contrasenas, reset obligatorio de contrasena y borrado de dispositivos individuales o todos los de un usuario. `Set password` guarda una contrasena definida por el administrador y borra dispositivos. `Reset password` marca `must_change_password=true`, borra dispositivos y obliga al usuario a elegir una contrasena distinta tras autenticarse con la actual. Aplica al servidor HA; el visor Docker local sigue siendo estatico para pruebas. Los tests `tests/test_web_server_auth.py` cubren JSON, limites por dispositivo y funciones de gestion. Imagen `0.2.86` publicada en GHCR con digest `sha256:ac210e3aebfcba23a49ccae2cfd9532bd119e943da7f77bbe68182823f8c3adb`; pendiente de validar en HA.
- Estado por fuente: `rainmapper_core.rainmapper` escribe `Data/source_status.json` con el ultimo estado de Meteoclimatic, Meteocat y Wunderground. Si una fuente falla completamente, el update intenta continuar con el incremental previo y marca la fuente como `STALE`; si no hay incremental utilizable la marca como `NOK`. La webUI de HA muestra esas tarjetas de estado desde `0.2.71` y ahora tambien muestra duraciones reales por fuente; Meteocat guarda ademas subtiempos reales de metadata, condiciones, precipitacion, merge y guardado. MapLibre muestra solo badges de estado junto al filtro `Source`; por decision del usuario, los tiempos de proceso no son relevantes para el visor de mapas.
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
- Versionado HA: `config.yaml`, labels Docker, banner runtime y cache-busters de visores estan alineados en `0.2.91`.
- Internacionalizacion: la webUI visible de HA, metadata HA, changelog y logs operativos principales del core estan en ingles. README/DOCS de la app HA siguen en espanol porque de momento la app es de uso propio; no hay sistema i18n.
- MapLibre protegido muestra en la cabecera el usuario autenticado y su rol (`free`, `basic`, `pro` o `admin`) en una segunda linea compacta bajo la fecha generada, usando `username (role)` y el payload existente de login o `/auth/session`.

## Funcionalidades pendientes
- Decidir retirada de Bokeh o mantenerlo como referencia.
- Crear tests automaticos mas completos; existe smoke test versionado, cobertura `unittest` offline para GeoJSON, Tomap, upsert incremental, auth backend y pipeline `upsert -> Tomap -> GeoJSON`, y una prueba Docker offline versionada. Faltan fixtures funcionales de HA/webUI/publicacion real.
- Mejorar separacion entre core de datos, webUI y visores.
- Extraccion de CSV `Tomap`: `python -m rainmapper_core.tomap` reconstruye `Tomap` desde historicos sin descargar datos nuevos, y `MODE=maps`/`Generate maps` lo invocan antes de Bokeh/GeoJSON. Validacion local inicial: tras `local_update.sh`, `scripts/compare-tomap-builder.sh` confirma que el builder genera los mismos `Tomap` que el flujo antiguo; `local_maps.sh` reconstruye `Tomap`, genera GeoJSON y arranca el servidor local correctamente. `Generate maps` en HA `0.2.74` fue validado manualmente por el usuario. El bloque ejecutable inline y los helpers legacy de `Rainmapper.py` ya fueron retirados; `local_all.sh` completo queda validado en local con `rainmapper_core.rainmapper` exit code 0, reconstruccion Tomap por `rainmapper_core.tomap` y GeoJSON generado.
- Imagen Docker HA multi-arch preconstruida en GHCR desde `0.2.57`; el repo confirma `image: ghcr.io/cginebrosa/rainmapperha` y el script `scripts/build-push-ha-image.sh`. La instalacion rapida en HA, el progreso de Supervisor, la poca utilidad del cache de GitHub Actions y la limpieza local observada son validaciones manuales/reportadas por el usuario; pendientes de confirmar automaticamente. Desde `0.2.60`, el flujo normal documentado es publicar la imagen desde el Mac con `scripts/build-push-ha-image.sh` antes de subir el commit de version; GitHub Actions queda como fallback manual.
- Analitica historica de metricas Wunderground, posiblemente con InfluxDB/Grafana.
- Gestion WebUI de usuarios y dispositivos: interfaz HA implementada localmente para crear/desactivar/borrar usuarios, cambiar rol/max_devices, establecer nueva contrasena, forzar cambio de contrasena y borrar uno o todos los dispositivos de un usuario. `Delete user` borra tambien todos sus dispositivos asociados. Pendiente de validar en HA con `0.2.89`.
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
Subir cambios a GitHub, hacer Check for updates en Home Assistant y actualizar la app desde la UI de HA. No hay comando CLI de despliegue confirmado.
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
- Meteocat / Socrata: usado desde `rainmapper_core.rainmapper` y `rainmapper_core/sources/sodapy_local`. Endpoint exacto/datasets: pendiente de confirmar en detalle.
- Meteoclimatic RSS: usado desde `rainmapper_core/sources/meteoclimatic_local`; `meteoclimatic_pattern` filtra estaciones.
- Wunderground: scraping via `requests`, `BeautifulSoup` y parser local en `rainmapper_core/sources/wunderground`.
- Google Maps: `googlemaps` Python client y Bokeh `gmap`; clave en `GMAP_API_KEY`/`gmap_api_key`.
- Home Assistant Supervisor API: `web_server.py` usa `SUPERVISOR_TOKEN` para resolver informacion del addon.
- OpenTopoMap / Esri / OpenFreeMap / Terrarium DEM: proveedores de tiles/estilos/relieve para visores.
- Cloudflare/domain externo: usado operacionalmente para exponer HA/visor, pero no hay configuracion de Cloudflare versionada en el repo. Para MapLibre protegido, Cloudflared debe apuntar a `http://<HA_IP>:8099`; las reglas que redirijan a `/local/rainmapper-maplibre/index.html` deben retirarse o cambiarse a la ruta protegida.

## Decisiones importantes ya tomadas
Resumen:

- Home Assistant se ejecuta en modo `serve` para mantener sidebar y webUI.
- Los datos historicos viven fuera del contenedor.
- Docker local en Mac se conserva como entorno de pruebas.
- Bokeh, Leaflet y MapLibre conviven; Leaflet y MapLibre se mantienen publicados de momento.
- Los visores nuevos usan GeoJSON generado desde `Tomap`.
- Las estaciones anomalas se ignoran en GeoJSON mediante fichero manual, sin borrar historico.
- Wunderground usa `max_threads=3` como valor operativo recomendado en HA/RPi tras validacion manual; `1` queda como modo conservador de diagnostico.

Detalle en [decisions.md](decisions.md).

## Riesgos antes de continuar
- No borrar ni limpiar `Data`, `Tomap`, `Plots`, `/share/rainmapper` ni `docker-data` sin backup explicito.
- No modificar `rainmapper-app/run.sh` sin revisar persistencia y symlinks.
- No modificar `rainmapper_core/rainmapper.py` sin revisar impacto en historicos incrementales; ya no existe wrapper raiz `Rainmapper.py`.
- Validar que `rainmapper-app/app` siga conteniendo solo codigo especifico de HA y que el build HA use la raiz del repo; usar `./scripts/smoke-test.sh`.
- Todo script o modulo nuevo (`.py`, `.sh` u otros) debe incluir documentacion interna en ingles: cabecera de proposito y comentarios/docstrings breves en funciones o bloques no obvios.
- No introducir API keys reales en Git.
- No basar una futura app comercial en datos Wunderground obtenidos por scraping ni por PWS Data Feed sin permiso/acuerdo escrito de The Weather Company.
- Validar cambios de visores en movil real, especialmente iPhone.
- Ejecutar `./scripts/smoke-test.sh` antes de cerrar cambios relevantes.
- Antes de tocar pandas o escritura CSV, usar `./scripts/backup-data.sh` y `./scripts/check-history.py` sobre una copia.

## Proximo paso recomendado
Validar en HA `0.2.91`: la cabecera de MapLibre protegido debe ocupar solo dos lineas en movil, mostrando fecha generada y `username (role)`. En la misma validacion, confirmar el bloque de autenticacion ligera: `users.json` como unico formato de usuarios, WebUI de gestion de usuarios/dispositivos sin auto-refresh, `Set password`, `Reset password` obligatorio, `Delete user`, login con `admin` y usuario `free`, limite de dispositivos, y acceso protegido a GeoJSON. Despues, validar Cloudflared apuntando a `http://<HA_IP>:8099/protected/maplibre/index.html` antes de retirar el fallback publico `/local/rainmapper-maplibre`.

## Prompt recomendado para nueva sesion de Codex
"Lee primero docs/codex-handoff.md. Después consulta docs/architecture.md, docs/todo.md y docs/decisions.md. No modifiques código todavía. Primero resume el objetivo de la app, el estado actual, los ficheros clave, lo que funciona, lo que falta y el siguiente paso recomendado."
