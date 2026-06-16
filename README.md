# RainmapperHA

RainmapperHA empaqueta Rainmapper como app de Home Assistant.

La app descarga datos de lluvia de estaciones meteorologicas, genera ficheros intermedios para mapas y crea mapas HTML consultables desde Home Assistant.

## Home Assistant

La app se instala como repositorio de apps/add-ons de Home Assistant desde este repositorio de GitHub.

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
- ver el estado de la ultima ejecucion;
- consultar el log completo del ultimo trabajo;
- abrir los mapas HTML generados;
- ejecutar una o varias programaciones diarias;
- publicar una copia de los mapas en `/local/Plots`.

Documentacion completa de la app:

- [README de la app](rainmapper-app/README.md)
- [Documentacion detallada](rainmapper-app/DOCS.md)
- [Changelog](rainmapper-app/CHANGELOG.md)

## Datos persistentes

La app guarda los datos fuera del contenedor:

```text
/share/rainmapper/Data
/share/rainmapper/Tomap
/share/rainmapper/Plots
/share/rainmapper/stations.txt
/share/rainmapper/ignore_stations_tomap.txt
```

`ignore_stations_tomap.txt` permite excluir estaciones concretas solo de los GeoJSON usados por Leaflet/MapLibre. Las descargas y los CSV historicos no se modifican.

Si `publish_to_www` esta activado, los mapas tambien se publican en:

```text
/config/www/Plots
```

y Home Assistant los sirve como:

```text
/local/Plots/rain_01d.html
/local/Plots/rain_07d.html
/local/Plots/rain_14d.html
/local/Plots/rain_21d.html
/local/Plots/rain_30d.html
/local/Plots/rain_60d.html
/local/Plots/rain_90d.html
```

## Visores de mapas

RainmapperHA publica tres visores:

- Bokeh / HTML clasico: `/local/Plots/rain_21d.html` y equivalentes para 1, 7, 14, 30, 60 y 90 dias.
- Leaflet: `/local/rainmapper-leaflet/index.html` (`/local/rainmapper-mobile/index.html` se mantiene como ruta compatible antigua).
- MapLibre: `/local/rainmapper-maplibre/index.html`.

Leaflet y MapLibre usan GeoJSON generados desde `Tomap`. El fichero `ignore_stations_tomap.txt` solo afecta a estos visores nuevos.

## Google Maps API key

Cada instalacion debe usar su propia Google Maps API key.

La clave no debe guardarse en GitHub ni dentro de la imagen Docker. En Home Assistant se configura como opcion `gmap_api_key`; en Docker local se lee desde la variable de entorno `GMAP_API_KEY`.

## Docker local

El repositorio tambien conserva un Docker local para probar Rainmapper en Mac antes de copiar cambios a la app de Home Assistant.

Documentacion del Docker local:

- [README_DOCKER.md](README_DOCKER.md)

## Estructura del repositorio

```text
.
├── Rainmapper.py              # Script principal
├── Rainmapper_Client.py       # Generacion de mapas HTML
├── Dockerfile                 # Docker local para Mac/desarrollo
├── docker-compose.yml         # Runner Docker local
├── README_DOCKER.md           # Documentacion Docker local
├── repository.yaml            # Metadata del repositorio para Home Assistant
└── rainmapper-app/            # App de Home Assistant
```

## Desarrollo

Flujo recomendado:

1. Probar cambios en el Docker local del Mac.
2. Copiar los cambios necesarios a `rainmapper-app/app`.
3. Probar la imagen de la app.
4. Subir a GitHub.
5. Actualizar la app desde Home Assistant.
