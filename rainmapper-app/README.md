# Rainmapper

Rainmapper es una app de Home Assistant para actualizar datos de lluvia de estaciones meteorologicas, generar mapas HTML y consultarlos desde la barra lateral de Home Assistant.

La app se queda abierta como un servicio ligero. Desde su webUI puedes lanzar `update`, `maps` o `all`, ver el estado de la ultima ejecucion, consultar logs recientes y abrir los mapas generados.

Cuando `publish_to_www` esta activado, cada generacion de mapas publica los visores y datos en `/config/www`, accesibles desde Home Assistant como `/local/...`.

Visores publicados:

- MapLibre recomendado: `/local/rainmapper-maplibre/index.html`.
- Leaflet fallback: `/local/rainmapper-leaflet/index.html`.
- Bokeh / HTML clasico como referencia: `/local/Plots/rain_21d.html` y equivalentes.

MapLibre es el visor principal recomendado. Incluye capas raster Hybrid/Topographic, capas vectoriales y una capa Satellite+ con imagen Esri y orientacion vectorial OpenFreeMap. Leaflet se mantiene publicado como fallback.

La programacion interna puede ejecutar Rainmapper una o varias veces al dia usando `schedule_time`, por ejemplo `06:00, 12:00, 18:00, 23:50`, y se puede limitar por dias con `schedule_days`.

Datos persistentes:

- `/share/rainmapper/Data`
- `/share/rainmapper/Tomap`
- `/share/rainmapper/Plots`
- `/share/rainmapper/stations.txt`
- `/share/rainmapper/ignore_stations_tomap.txt`

`ignore_stations_tomap.txt` se crea automaticamente si no existe y no se sobrescribe en updates. Pon un codigo de estacion por linea para ocultarla de los visores Leaflet/MapLibre sin borrar ni alterar sus datos historicos.

El modo recomendado para Home Assistant es `serve`.

Puedes activar el schedule interno para ejecutar `all` cada dia a una hora concreta, por ejemplo a las `23:50`.

`meteoclimatic_pattern` acepta uno o varios patrones de Meteoclimatic. Puedes separarlos con coma, punto y coma o ` - `, por ejemplo:

```yaml
meteoclimatic_pattern: "ESCAT;ESARA;ESCLM"
```

Las claves `gmap_api_key` y `jawgmaps_api_key` no deben guardarse en Git. `gmap_api_key` se usa para los mapas clasicos Bokeh/Google Maps y para completar metadata de estaciones durante `update` cuando hace falta consultar altitud, municipio/localidad o provincia. `jawgmaps_api_key` es opcional; si esta vacia, las capas Jawg no aparecen en Leaflet/MapLibre.

`last_rains_history` controla cuantos registros recientes de lluvia se guardan en los CSV `Tomap` y, por tanto, cuantos puede mostrar el popup de una estacion en Leaflet/MapLibre. El valor por defecto es `30`. Este dato se aplica cuando Rainmapper reconstruye `Tomap`, es decir, durante `update` o `all`. El modo `maps` no recalcula `Tomap`; solo convierte los `Tomap` ya existentes en HTML/GeoJSON.

`meteocat_request_timeout` y `meteocat_max_attempts` controlan el timeout y los reintentos de las consultas Meteocat/Socrata. Los valores por defecto son `30` segundos y `3` intentos para evitar que un timeout transitorio de `analisi.transparenciacatalunya.cat` haga fallar un `Run all` a la primera.
