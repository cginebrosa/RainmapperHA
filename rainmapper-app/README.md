# Rainmapper

Rainmapper es una app de Home Assistant para actualizar datos meteorologicos de Meteoclimatic, Meteocat, Wunderground y AEMET opcional, generar mapas HTML/GeoJSON y consultarlos desde la barra lateral de Home Assistant.

La app se queda abierta como un servicio ligero. Desde su webUI puedes lanzar `update`, `maps` o `all`, ver el estado de la ultima ejecucion, consultar logs recientes y abrir los mapas generados.

La webUI tambien muestra estado separado para Meteoclimatic, Meteocat, Wunderground y AEMET. Si una fuente falla completamente, Rainmapper intenta continuar con su incremental previo y la marca como `STALE`; si no hay datos reutilizables la marca como `NOK`.

Cuando `publish_to_www` esta activado, cada generacion de mapas publica los visores y datos en `/config/www`, accesibles desde Home Assistant como `/local/...`.

Visores publicados:

- MapLibre recomendado: `/protected/maplibre/index.html` (con login ligero).
- Leaflet fallback: `/local/rainmapper-leaflet/index.html`.
- Bokeh / HTML clasico como referencia: `/local/Plots/rain_21d.html` y equivalentes.

MapLibre es el visor principal recomendado. Incluye capas raster Hybrid/Topographic, capas vectoriales y una capa Satellite+ con imagen Esri y orientacion vectorial OpenFreeMap. Se sirve por la ruta protegida `/protected/maplibre/index.html`; Leaflet se mantiene publicado como fallback.

La programacion interna puede ejecutar Rainmapper una o varias veces al dia usando `schedule_time`, por ejemplo `06:00, 12:00, 18:00, 23:50`, y se puede limitar por dias con `schedule_days`.

Datos persistentes:

- `/share/rainmapper/Data`
- `/share/rainmapper/Tomap`
- `/share/rainmapper/Plots`
- `/share/rainmapper/stations.txt`
- `/share/rainmapper/ignore_stations_tomap.txt`
- `/share/rainmapper/users.json`
- `/share/rainmapper/devices.json`
- `/share/rainmapper/Data/source_status.json`

`ignore_stations_tomap.txt` se crea automaticamente si no existe y no se sobrescribe en updates. Pon un codigo de estacion por linea para ocultarla de los visores Leaflet/MapLibre sin borrar ni alterar sus datos historicos.

El modo recomendado para Home Assistant es `serve`.

Puedes activar el schedule interno para ejecutar `all` cada dia a una hora concreta, por ejemplo a las `23:50`.

`meteoclimatic_pattern` acepta uno o varios patrones de Meteoclimatic. Puedes separarlos con coma, punto y coma o ` - `, por ejemplo:

```yaml
meteoclimatic_pattern: "ESCAT;ESARA;ESCLM"
```

La clave `gmap_api_key` no debe guardarse en Git. Se usa para los mapas clasicos Bokeh/Google Maps y para completar metadata de estaciones durante `update` cuando hace falta consultar altitud, municipio/localidad o provincia.

`last_rains_history` controla cuantos registros recientes de lluvia se guardan en los CSV `Tomap` y, por tanto, cuantos puede mostrar el popup de una estacion en Leaflet/MapLibre. El valor por defecto es `30`. Este dato se aplica cuando Rainmapper reconstruye `Tomap`; en Home Assistant, `maps` y `all` reconstruyen `Tomap` antes de generar HTML/GeoJSON.

`maplibre_hover_zoom` controla desde que nivel de zoom se activan los popups por hover sobre estaciones en MapLibre de escritorio. El valor por defecto es `6.0` y admite decimales como `6.5`.

`maplibre_heatmap_weight_curve`, `maplibre_heatmap_opacity`, `maplibre_heatmap_radius` y `maplibre_heatmap_intensity` controlan los valores iniciales del heatmap para dispositivos sin preferencias guardadas. Los defaults actuales son `soft`, `65`, `90` y `70`; los tres valores numericos son porcentajes. El boton `Reset heatmap defaults` del visor restaura estos valores.

`maplibre_estimated_field_*` controla la capa experimental `IDW` de MapLibre. Los defaults de usuario definen si arranca activa, opacidad, radio fisico, calidad, suavizado y correccion de temperatura por altitud. Los parametros tecnicos de radio en km, radio fisico maximo, tamano fisico de celda en km, potencia IDW y gradiente termico tambien viven en `config.yaml` para poder probarlos en HA tras reiniciar la app.

`meteocat_request_timeout` y `meteocat_max_attempts` controlan el timeout y los reintentos de las consultas Meteocat/Socrata. Los valores por defecto son `30` segundos y `3` intentos para evitar que un timeout transitorio de `analisi.transparenciacatalunya.cat` haga fallar un `Run all` a la primera.

`create_aemet` activa la descarga/refresco de AEMET OpenData. Esta desactivada por defecto y requiere `aemet_api_key`. En Home Assistant, la generacion de mapas incluye AEMET en el Tomap/GeoJSON estandar siempre que exista un `Aemet_incremental.csv` utilizable.
