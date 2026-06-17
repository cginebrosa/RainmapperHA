# RainmapperHA

## Descripcion
RainmapperHA empaqueta Rainmapper como app de Home Assistant.

La app descarga datos meteorologicos de estaciones Meteocat, Meteoclimatic y Wunderground, conserva historicos en CSV, genera ficheros `Tomap`, crea mapas HTML clasicos y publica visores web Leaflet/MapLibre pensados para consultar lluvia acumulada desde Home Assistant o movil.

Objetivo a largo plazo: evolucionar Rainmapper hacia una plataforma de datos y mapas meteorologicos automatizada, con visores moviles y una futura app iOS/Android con autenticacion y control de acceso.

## Requisitos
Confirmado en el repositorio:

- Python 3.11.
- Docker y Docker Compose para ejecucion local.
- Home Assistant con soporte de apps/add-ons para instalar `rainmapper-app`.
- Google Maps API key si se usan funciones/mapas que dependen de Google Maps.
- Jawg Maps access token opcional para capas Jawg en Leaflet/MapLibre.
- MapLibre con capas raster/vectoriales, incluyendo una capa Satellite+ sin clave adicional.

Versiones exactas de Docker/Home Assistant necesarias: pendiente de confirmar.

## Instalacion
Dependencias Python:

```bash
pip install -r requirements.txt
```

Preparar datos persistentes para Docker local:

```bash
mkdir -p docker-data/Data docker-data/Tomap docker-data/Plots docker-data/PublicData
cp stations.example.txt docker-data/stations.txt
```

Instalacion en Home Assistant:

1. Anadir este repositorio como repositorio de apps/add-ons en Home Assistant.
2. Instalar la app `Rainmapper`.
3. Configurar `gmap_api_key` y, opcionalmente, `jawgmaps_api_key`.
4. Usar preferiblemente `mode: serve`.

## Configuracion
Variables/opciones principales:

- `GMAP_API_KEY`: Google Maps API key para ejecucion local Docker.
- `JAWGMAPS_API_KEY`: Jawg Maps token opcional para visores locales.
- `gmap_api_key`: opcion HA equivalente para Google Maps.
- `jawgmaps_api_key`: opcion HA equivalente para Jawg Maps.
- `mode`: `help`, `update`, `maps`, `all` o `serve`.
- `schedule_enabled`: activa schedule interno en HA.
- `schedule_time`: una o varias horas, por ejemplo `06:00, 12:00, 18:00, 23:50`.
- `schedule_days`: `all` o dias configurados. Sintaxis exacta aceptada: ver `rainmapper-app/DOCS.md`.
- `scheduled_action`: `update`, `maps` o `all`.
- `meteoclimatic_pattern`: patron o patrones RSS Meteoclimatic.
- `max_threads`: threads Wunderground; por defecto `1`.
- `max_attempts`: reintentos Wunderground.
- `wunderground_full_log`: log detallado por estacion.
- `publish_to_www`: publica mapas y visores en `/config/www`.

No guardar secretos reales en Git.

## Ejecucion en desarrollo
Build Docker local:

```bash
docker compose build rainmapper
```

Ejecutar una vez con configuracion por defecto:

```bash
docker compose run --rm rainmapper
```

Ver ayuda:

```bash
docker compose run --rm -e MODE=help rainmapper
```

Ejecutar update:

```bash
docker compose run --rm -e MODE=update rainmapper
```

Generar mapas:

```bash
docker compose run --rm -e MODE=maps rainmapper
```

Ejecutar update + maps:

```bash
docker compose run --rm -e MODE=all rainmapper
```

## Tests
Smoke test rapido:

```bash
./scripts/smoke-test.sh
```

El smoke test valida sintaxis Python, sintaxis JavaScript, wrappers shell, conversion GeoJSON minima, reconstruccion con poco historico, metadata de version de Home Assistant, sincronizacion entre raiz y `rainmapper-app/app`, y whitespace del diff de Git.

Para sincronizar las copias empaquetadas en la app de Home Assistant despues de cambios en scripts raiz o visores:

```bash
./scripts/sync-app-files.sh
```

Validaciones manuales/sintacticas recomendadas:

```bash
./scripts/smoke-test.sh
python -m py_compile Rainmapper.py Rainmapper_Client.py tomap_to_geojson.py rainmapper-app/app/web_server.py
node --check leaflet-viewer/app.js
node --check maplibre-viewer/app.js
git diff --check
```

## Seguridad de historicos
Antes de tocar codigo que escriba historicos CSV, crea backup o trabaja sobre una copia:

```bash
./scripts/backup-data.sh docker-data
./scripts/check-history.py docker-data/Data
```

Ver [docs/history-safety.md](docs/history-safety.md).

## Build
Build Docker local:

```bash
docker compose build rainmapper
```

Build de Home Assistant: Home Assistant construye la app desde `rainmapper-app/Dockerfile` al instalar o actualizar. Comando CLI especifico: pendiente de confirmar.

## Despliegue
Despliegue Home Assistant confirmado por flujo manual:

1. Hacer commit y push a GitHub.
2. En Home Assistant, ejecutar `Check for updates` del repositorio/app.
3. Actualizar la app desde la UI de Home Assistant.
4. Reiniciar/arrancar la app si HA no lo hace automaticamente.

No hay pipeline CI/CD detectado.

## Uso en Home Assistant
Modo recomendado:

```yaml
mode: serve
schedule_enabled: true
schedule_time: "06:00, 12:00, 18:00, 23:50"
schedule_days: "all"
scheduled_action: all
publish_to_www: true
```

Con `mode: serve`, Rainmapper queda abierto como servicio ligero, aparece en la barra lateral de Home Assistant y permite:

- lanzar `update`, `maps` o `all` manualmente;
- ver estado, duracion y log de la ultima ejecucion;
- abrir mapas generados;
- usar schedule interno;
- publicar mapas en `/local/Plots`, `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre`.

## Datos persistentes
En Home Assistant:

```text
/share/rainmapper/Data
/share/rainmapper/Tomap
/share/rainmapper/Plots
/share/rainmapper/stations.txt
/share/rainmapper/ignore_stations_tomap.txt
```

En Docker local:

```text
docker-data/Data
docker-data/Tomap
docker-data/Plots
docker-data/PublicData
docker-data/stations.txt
docker-data/ignore_stations_tomap.txt
```

`ignore_stations_tomap.txt` excluye estaciones solo de los GeoJSON usados por Leaflet/MapLibre. No borra historicos.

## Visores de mapas
- Bokeh clasico: `/local/Plots/rain_21d.html` y equivalentes para 1, 7, 14, 30, 60 y 90 dias.
- Leaflet: `/local/rainmapper-leaflet/index.html`.
- MapLibre: `/local/rainmapper-maplibre/index.html`.

## Documentacion de continuidad
- [docs/codex-handoff.md](docs/codex-handoff.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/todo.md](docs/todo.md)
- [docs/decisions.md](docs/decisions.md)

## Documentacion adicional
- [README_DOCKER.md](README_DOCKER.md)
- [rainmapper-app/README.md](rainmapper-app/README.md)
- [rainmapper-app/DOCS.md](rainmapper-app/DOCS.md)
- [rainmapper-app/CHANGELOG.md](rainmapper-app/CHANGELOG.md)
