# Rainmapper Home Assistant App

Rainmapper descarga datos meteorologicos de estaciones Meteoclimatic, Meteocat, Wunderground y AEMET opcional. Conserva historicos CSV, reconstruye CSV `Tomap` y publica GeoJSON para el visor MapLibre protegido. Los visores publicos legacy se generan solo si `publish_to_www` esta activado.

La app se queda abierta como un servicio ligero. Sirve una webUI para Home Assistant, permite lanzar ejecuciones manuales, muestra los mapas generados y puede ejecutar un schedule interno.

## Como funciona

La app ejecuta los mismos scripts de Rainmapper dentro de un contenedor Docker controlado por Home Assistant.

Flujo habitual:

1. Home Assistant arranca la app como servicio.
2. La webUI queda disponible mediante ingress y sidebar.
3. Desde la webUI puedes lanzar `update`, `maps` o `all`.
4. Si el schedule interno esta activado, la app ejecuta la accion configurada cada dia.
5. Los datos y mapas se guardan en `/share/rainmapper`.
6. Si `publish_to_www` esta activado, los mapas Bokeh y el visor Leaflet legacy se publican en `/config/www`.

## Carpetas persistentes

La app guarda los datos fuera del contenedor, en la carpeta compartida de Home Assistant:

```text
/share/rainmapper
```

Dentro se usan estas rutas:

```text
/share/rainmapper/Data
/share/rainmapper/Tomap
/share/rainmapper/Plots
/share/rainmapper/stations.txt
/share/rainmapper/ignore_stations_tomap.txt
/share/rainmapper/users.json
/share/rainmapper/devices.json
```

Contenido esperado:

- `Data`: CSV historicos e incrementales de Meteocat, Meteoclimatic, Wunderground y AEMET cuando esta habilitado.
- `Tomap`: CSV preparados para pintar mapas.
- `Plots`: HTML generados por `python -m rainmapper_core.bokeh_maps`.
- `stations.txt`: lista de estaciones Wunderground que quieres descargar.
- `ignore_stations_tomap.txt`: lista opcional de estaciones que no deben aparecer en los GeoJSON usados por Leaflet/MapLibre.
- `Data/source_status.json`: ultimo estado de actualizacion por fuente.
- `users.json`: usuarios manuales para el visor MapLibre protegido. Si no existe, la app lo crea copiando `/app/users.example.json`.
- `devices.json`: dispositivos autorizados. Si no existe, la app lo crea como JSON vacio.

Si `stations.txt` no existe, la app lo crea automaticamente copiando una plantilla. Despues puedes editarlo desde la carpeta compartida.

Si `ignore_stations_tomap.txt` no existe, la app lo crea automaticamente con una linea de comentario. Si ya existe, no se sobrescribe durante los updates.

## Mapas legacy publicados en /local/Plots

Si `publish_to_www` esta activado, cada vez que `maps` termina correctamente la app genera mapas Bokeh/Google Maps y copia una version publica a:

```text
/config/www/Plots
```

Home Assistant sirve esa carpeta como:

```text
/local/Plots
```

Por ejemplo:

```text
/local/Plots/rain_01d.html
/local/Plots/rain_07d.html
/local/Plots/rain_14d.html
/local/Plots/rain_21d.html
/local/Plots/rain_30d.html
/local/Plots/rain_60d.html
/local/Plots/rain_90d.html
```

La carpeta interna `/share/rainmapper/Plots` sigue siendo la salida legacy de Bokeh cuando `publish_to_www` esta activo. La carpeta `/config/www/Plots` es solo una copia publicada para acceder a esos mapas desde Home Assistant.

Al publicar, la app recrea `/config/www/Plots` completa. Asi evita dejar HTML antiguos que ya no correspondan a la ultima generacion.

## Visores de mapas

Rainmapper mantiene tres formas de consultar los mapas. MapLibre protegido es el visor principal recomendado desde la validacion de `0.2.53`. Leaflet publico y Bokeh quedan como visores legacy desactivados por defecto.

### MapLibre viewer

Ruta recomendada:

```text
/protected/maplibre/index.html
```

El visor MapLibre carga sus datos desde `/protected/maplibre/data/*`, por lo que la ruta protegida requiere login. No depende de `/config/www`.

Permite usar mapas raster Hybrid/Topographic, una capa Satellite+ con imagen Esri y orientacion vectorial OpenFreeMap, y mapas vectoriales como OpenFreeMap.

Es el visor recomendado para movil y para uso normal porque combina mejor rendimiento movil, capas raster utiles y renderizado vectorial nitido para etiquetas/orientacion.

En Settings, el filtro `Source` permite filtrar Meteocat, Meteoclimatic, Wunderground y AEMET, y muestra tambien el ultimo estado conocido de cada fuente cuando existe `source_status.json`. Esto permite ver si una fuente esta `OK`, `STALE` o `NOK` mientras se consulta el mapa.

La barra derecha incluye un boton `?` al final. Abre la ayuda del mapa, con resumen de periodos, estaciones, filtros, controles, relieve, altitud, estado de fuentes y notas de autenticacion. La ayuda usa el idioma seleccionado en Settings.

### Leaflet viewer legacy

Ruta publica legacy, solo si `publish_to_www` esta activo:

```text
/local/rainmapper-leaflet/index.html
```

El visor Leaflet usa los GeoJSON publicados dentro de `/config/www/rainmapper-leaflet/data`. Se mantiene disponible como procedimiento legacy, pero no se publica por defecto.

### Bokeh / HTML clasico legacy

Ruta publica legacy, solo si `publish_to_www` esta activo:

```text
/local/Plots
```

Ejemplos:

```text
/local/Plots/rain_01d.html
/local/Plots/rain_07d.html
/local/Plots/rain_14d.html
/local/Plots/rain_21d.html
/local/Plots/rain_30d.html
/local/Plots/rain_60d.html
/local/Plots/rain_90d.html
```

Este visor usa los HTML generados por `python -m rainmapper_core.bokeh_maps`. Es el visor original y sigue siendo util como referencia, pero en movil es menos comodo y no se genera por defecto.

### Que se regenera en cada caso

Cuando ejecutas `maps` o `all`:

- se reconstruyen los CSV `Tomap` desde los historicos incrementales de `/share/rainmapper/Data`;
- si `publish_to_www` esta activo, se regeneran los HTML clasicos en `/share/rainmapper/Plots` y se publican en `/config/www/Plots`;
- se regeneran los GeoJSON desde `Tomap`;
- se publican los datos para MapLibre protegido;
- si `publish_to_www` esta activo, se publica tambien Leaflet legacy en `/config/www/rainmapper-leaflet`.

Si editas `ignore_stations_tomap.txt`, ejecuta `maps` o `all` para que Leaflet y MapLibre reflejen el cambio.


## Usuarios del visor MapLibre protegido

MapLibre puede protegerse con una autenticacion ligera pensada para pruebas privadas. No es todavia una gestion completa de usuarios ni de suscripciones.

En una instalacion nueva, la app crea automaticamente un fichero de ejemplo:

```text
/share/rainmapper/users.json
```

Formato:

```json
{
  "users": [
    {
      "username": "usuario",
      "name": "Nombre Usuario",
      "email": "usuario@example.com",
      "password": "clave_temporal",
      "role": "free",
      "enabled": true,
      "max_devices": 1,
      "must_change_password": false,
      "can_use_heatmap": false,
      "can_use_layer_metrics": false
    },
    {
      "username": "admin",
      "name": "Administrador",
      "email": "admin@example.com",
      "password": "clave_temporal",
      "role": "admin",
      "enabled": true,
      "max_devices": 0,
      "must_change_password": false,
      "can_use_heatmap": true,
      "can_use_layer_metrics": true
    }
  ]
}
```

Importante: cambia las contrasenas y usuarios de ejemplo antes de exponer el visor protegido fuera de tu red. Si `users.json` ya existe, la app no lo sobrescribe durante updates.

Reglas actuales:

- `username` es el identificador usado para el login.
- `name` es el nombre de la persona.
- `email` queda como dato de contacto para futuras funciones.
- Roles soportados: `free`, `basic`, `pro` y `admin`.
- `max_devices` es opcional. Si falta, se usa el valor por defecto del rol: `free=1`, `basic=2`, `pro=3`, `admin=0`.
- `max_devices=0` significa dispositivos ilimitados.
- `enabled` debe ser `true` para permitir acceso.
- `must_change_password` es opcional. Si es `true`, el usuario debe iniciar sesion con su contrasena actual y elegir una contrasena distinta antes de acceder al mapa.
- `can_use_heatmap` controla el boton `Heatmap` y la pestana/seccion `Heatmap` en Settings del visor MapLibre protegido.
- `can_use_layer_metrics` controla el boton rapido de selector de metrica/capa y el selector `Layer metric` en Settings del visor MapLibre protegido.
- Si esos permisos faltan en un usuario existente, la app aplica defaults compatibles: `admin=true` y resto de roles `false`. Al crear un usuario `admin` desde la WebUI, ambos permisos quedan activados por defecto.
- Si la contrasena esta en claro, la app la convierte automaticamente a hash PBKDF2 despues del primer login correcto.
- `users.json` es el unico formato de usuarios soportado.

La app crea automaticamente, si no existe:

```text
/share/rainmapper/devices.json
```

Ese fichero guarda el `device_id`, usuario, rol, user-agent, ultimo acceso y hash del token de sesion. Si un usuario normal borra los datos del navegador, se generara un nuevo `device_id` y quedara bloqueado hasta que limpies o borres su dispositivo anterior.

La WebUI de Home Assistant incluye una pagina `Users` para crear usuarios, borrar usuarios, activar/desactivar acceso, cambiar rol, cambiar `max_devices`, activar/desactivar permisos MapLibre de `Heatmap` y `Layer metric`, establecer una nueva contrasena y borrar dispositivos asociados a un usuario, uno a uno o todos a la vez. `Delete user` borra tambien todos sus dispositivos asociados. `Set password` guarda una contrasena definida por el administrador y borra automaticamente los dispositivos del usuario. `Reset password` no muestra ni cambia directamente la contrasena: marca el usuario para que tenga que elegir una contrasena distinta en el proximo inicio de sesion y tambien borra sus dispositivos.

Si usas Cloudflare Tunnel con el add-on Cloudflared de Home Assistant, apunta el hostname externo al servidor Rainmapper publicado por la app:

```text
service: http://<HA_IP>:8099
```

Despues abre el visor en:

```text
https://rainmap.nomentero.com/protected/maplibre/index.html
```

No pongas `/protected/maplibre/index.html` en el campo `service` de Cloudflared: el `service` debe ser solo host y puerto. La ruta `/local/rainmapper-maplibre/index.html` queda temporalmente como fallback mientras se valida Cloudflared, pero no debe ser la ruta externa definitiva. Si existe una regla externa de Cloudflare que redirige `/` a `/local/rainmapper-maplibre/index.html`, conviene desactivarla o sustituirla por la ruta protegida cuando la validacion termine.

La app publica el puerto web `8099/tcp` para que Cloudflared pueda acceder al servidor Rainmapper. Esto no abre ningun puerto del router por si solo, pero hace que el servidor sea accesible desde la red local donde corre Home Assistant. El protocolo del worker no se sirve en ese puerto.

La API de workers usa un listener distinto, `8100/tcp`, y queda sin publicar por defecto. Para conectar un worker externo hay que asignar expresamente un puerto host a `8100/tcp` en la seccion `Network` de la app y limitarlo a la red privada/LAN o Tailscale correspondiente. No debe apuntarse Cloudflared ni un navegador a ese puerto.

La autenticacion ligera se aplica al servidor HA (`web_server.py`). El visor local usado por `local_maps.sh` o `local_all.sh` sigue siendo estatico para pruebas en el Mac y lee datos desde `docker-data/PublicData`.

## Modos de ejecucion

`mode` controla que hace la app al arrancar.

```text
help
```

Muestra la ayuda de `python -m rainmapper_core.rainmapper`. Es util para una primera prueba despues de instalar.

```text
update
```

Descarga datos y actualiza historicos incrementales. No publica visores por si solo.

```text
maps
```

Reconstruye `Tomap` desde los historicos incrementales, genera GeoJSON para MapLibre protegido y, si `publish_to_www` esta activo, genera/publica los visores legacy. No descarga datos nuevos.

```text
all
```

Ejecuta primero `update` y despues `maps`. Es el modo habitual para schedule cuando quieres descargar datos nuevos y publicar visores actualizados en la misma ejecucion. Si `update` termina con exito degradado (`exit code 2`), `all` continua con `maps` y conserva `2` como resultado final.

```text
serve
```

Arranca la app como servicio web. Muestra una portada de Rainmapper con botones para ejecutar `update`, `maps` y `all`, estado de la ultima ejecucion, logs recientes y enlaces a los mapas HTML generados en `Plots`.

Para usar la barra lateral de Home Assistant, la app debe estar arrancada en este modo. Este es el modo recomendado para uso normal en HA.

## Configuracion recomendada

Para uso diario:

```yaml
mode: serve
timezone: Europe/Madrid
schedule_enabled: true
external_worker_connections_enabled: false
external_worker_rebuilds_enabled: false
ml_storage_reconciliation_apply: false
schedule_time: "23:50"
schedule_days: all
scheduled_action: all
days_init: -7
days_end: 0
backfill_months_enabled: false
months_init: -48
months_end: 0
months_interval: 3
backfill_pause_seconds: 5
backfill_station_filter: ""
create_meteoclimatic: true
create_meteocat: true
create_wunderground: true
create_aemet: false
meteoclimatic_pattern: "ESCAT;ESARA;ESCLM"
nomaps: false
nototals: false
days_bucket: 10
meteocat_request_timeout: 30
meteocat_max_attempts: 3
last_rains_history: 30
maplibre_hover_zoom: 6.0
maplibre_heatmap_weight_curve: soft
maplibre_heatmap_opacity: 80
maplibre_heatmap_radius: 90
maplibre_heatmap_intensity: 70
maplibre_estimated_field_enabled: false
maplibre_estimated_field_opacity: 90
maplibre_estimated_field_radius: medium
maplibre_estimated_field_quality: medium
maplibre_estimated_field_smoothing: balanced
maplibre_estimated_field_altitude_correction: false
maplibre_estimated_field_dem_zoom: 9
maplibre_estimated_field_radius_small_km: 10
maplibre_estimated_field_radius_medium_km: 15
maplibre_estimated_field_radius_large_km: 25
maplibre_estimated_field_max_radius_km: 50
maplibre_estimated_field_grid_low_cell_km: 2
maplibre_estimated_field_grid_medium_cell_km: 1
maplibre_estimated_field_grid_high_cell_km: 0.5
maplibre_estimated_field_smoothing_smooth_power: 1
maplibre_estimated_field_smoothing_balanced_power: 2
maplibre_estimated_field_smoothing_local_power: 3
maplibre_estimated_field_temperature_lapse_rate_c_per_100m: 0.65
max_threads: 3
max_attempts: 3
wunderground_daily_api: true
wunderground_full_log: false
publish_to_www: false
gmap_api_key: ""
aemet_api_key: ""
```

Notas rapidas:

- `mode: serve` es el modo normal para usar webUI, sidebar y schedule interno.
- `scheduled_action: all` ejecuta descarga de datos y generacion/publicacion de mapas.
- `backfill_months_enabled: false` debe quedar desactivado en uso diario. Al activarlo, Rainmapper hace una reconstruccion administrativa por ventanas mensuales, crea antes un backup de los CSV incrementales y espera `backfill_pause_seconds` entre ventanas. En Wunderground, las ventanas de backfill se pasan tambien como fechas locales exactas para evitar que la conversion UTC desplace el inicio al mes anterior.
- `backfill_station_filter: ""` permite limitar una reconstruccion administrativa a estaciones concretas. El formato es `fuente::id1,id2`, por ejemplo `wunderground::IORDIN1,IMERAN22`. Usa `;` para varias fuentes, por ejemplo `wunderground::IORDIN1;aemet::1234X`. Las comillas son opcionales para IDs con espacios. Si queda vacio no filtra nada.
- `meteocat_request_timeout: 30` y `meteocat_max_attempts: 3` hacen que las consultas Meteocat/Socrata reintenten ante timeouts transitorios antes de fallar el run.
- `max_threads: 3` es el valor operativo recomendado tras validacion real en Home Assistant/Raspberry Pi sin carga relevante observada. Si aparecen timeouts, errores de Wunderground o carga excesiva, bajar temporalmente a `1`.
- `create_aemet: false` deja AEMET desactivado por defecto. Para usar AEMET, activa esta opcion y configura `aemet_api_key`.
- `last_rains_history: 30` define cuantos registros recientes de lluvia se guardan en los CSV `Tomap` para el popup de estaciones en Leaflet/MapLibre. El valor se aplica cuando Rainmapper reconstruye `Tomap`; en Home Assistant, `maps` y `all` reconstruyen `Tomap` antes de generar HTML/GeoJSON.
- `publish_to_www: false` deja apagada la generacion/publicacion legacy de Bokeh/Google Maps y Leaflet publico. Tomap, GeoJSON y MapLibre protegido se siguen generando normalmente.
- `maplibre_hover_zoom: 6.0` define desde que nivel de zoom se activan los popups por hover sobre estaciones en MapLibre de escritorio. Admite decimales, por ejemplo `6.5`.
- `maplibre_heatmap_weight_curve: soft`, `maplibre_heatmap_opacity: 80`, `maplibre_heatmap_radius: 90` y `maplibre_heatmap_intensity: 70` definen los valores iniciales del heatmap para dispositivos sin settings guardados. El boton `Reset heatmap defaults` del visor restaura estos valores y los guarda para el dispositivo al cerrar Settings.
- `maplibre_estimated_field_*` define los defaults y parametros tecnicos de la capa experimental `IDW`. La capa se calcula en el navegador solo para el viewport visible. Los settings por dispositivo exponen activacion, opacidad, radio fisico (`small|medium|large`), calidad (`low|medium|high`), suavizado (`smooth|balanced|local`), zoom DEM (`8|9|10`) y correccion DEM opcional solo para temperatura. Cuando esa correccion se usa, el visor muestra `IDW DEM`; si esta activada pero el DEM externo no se puede usar, vuelve al IDW normal y muestra `IDW sin DEM`. Los radios en km, tamano fisico de celda en km, potencia IDW, radio fisico maximo, zoom DEM por defecto y gradiente termico se ajustan en `config.yaml` para probar sin publicar nueva imagen.
- `gmap_api_key` se usa para los mapas Bokeh/Google Maps y para completar metadata de estaciones con servicios de Google.
- `aemet_api_key` se usa solo si `create_aemet` esta activado.
- `wunderground_full_log: true` aumenta mucho el detalle del log de Wunderground y normalmente solo conviene para diagnostico.

## Home Assistant options

Estas son las opciones declaradas en `rainmapper-app/config.yaml`:

- `mode`: `help`, `update`, `maps`, `all` o `serve`.
- `timezone`: zona horaria usada por schedule y marcas de tiempo, por defecto `Europe/Madrid`.
- `schedule_enabled`: activa o desactiva el schedule interno.
- `external_worker_connections_enabled`: `Enable external worker connections`.
  Arranca la API privada autenticada en `8100`; no publica por si sola el
  puerto en el host.
- `external_worker_rebuilds_enabled`: `Allow external rebuilds and promotion`.
  Permite que los workers emparejados ejecuten el mantenimiento operativo
  completo y que HA autopromocione conjuntamente sus salidas verificadas.
  Mantenerla desactivada si solo se quiere diagnosticar la conectividad.
- `ml_storage_reconciliation_apply`: aplica la política auditada de retención
  al arrancar Rainmapper y en los puntos terminales del ciclo de vida. Su valor
  predeterminado es `false`: genera el informe `dry-run`, pero no elimina nada.
  Solo debe activarse después de revisar ese informe y autorizar expresamente
  la primera limpieza real.
- `schedule_time`: una o varias horas `HH:MM`.
- `schedule_days`: `all` o lista de dias.
- `scheduled_action`: `update`, `maps` o `all`.
- `days_init` / `days_end`: rango relativo de dias usado por las descargas.
- `backfill_months_enabled`, `months_init`, `months_end`, `months_interval`, `backfill_pause_seconds`: modo administrativo para reconstrucciones por ventanas de meses. Cuando esta activado, el update calcula ventanas mensuales, las convierte a `days_init`/`days_end`, ejecuta un update por ventana, hace backup previo de los CSV incrementales y muestra la pausa entre ventanas en `Current step`. Para Wunderground, ademas de `days_init`/`days_end`, se pasan fechas locales exactas de inicio y fin de ventana. Esto es deliberado: el uso diario mantiene la relectura legacy del mes anterior cuando `days_init` cruza un cambio de mes, pero el backfill mensual no debe duplicar meses por el desfase UTC/local.
- `backfill_station_filter`: filtro administrativo de estaciones por fuente. Actualmente se aplica a Wunderground y queda preparado para extenderlo a otras fuentes. Formato: `fuente::id1,id2`; separa fuentes con `;`. Dejalo vacio en uso diario para que no limite updates normales.
- `create_meteoclimatic`, `create_meteocat`, `create_wunderground`, `create_aemet`: activan o desactivan fuentes.
- `meteoclimatic_pattern`: patron o patrones del RSS Meteoclimatic.
- `nomaps`, `nototals`, `days_bucket`: opciones legacy del core de Rainmapper conservadas por compatibilidad.
- `meteocat_request_timeout`, `meteocat_max_attempts`: timeout y reintentos para Meteocat/Socrata.
- `last_rains_history`: numero de registros recientes preparados para popups.
- `maplibre_hover_zoom`: nivel minimo de zoom para activar popups por hover sobre estaciones en MapLibre de escritorio. Admite valores decimales como `6.5`.
- `maplibre_heatmap_weight_curve`, `maplibre_heatmap_opacity`, `maplibre_heatmap_radius`, `maplibre_heatmap_intensity`: valores iniciales del heatmap MapLibre para dispositivos sin preferencias guardadas. Opacidad, radio e intensidad se expresan como porcentaje. El visor incluye una accion para restaurar esos defaults desde Settings > Heatmap.
- `maplibre_estimated_field_enabled`, `maplibre_estimated_field_opacity`, `maplibre_estimated_field_radius`, `maplibre_estimated_field_quality`, `maplibre_estimated_field_smoothing`, `maplibre_estimated_field_altitude_correction`, `maplibre_estimated_field_dem_zoom`: valores iniciales de la capa experimental `IDW` para dispositivos sin preferencias guardadas. La correccion de altitud usa DEM externo Terrarium/Mapzen por celda y solo afecta a temperatura; no se aplica a lluvia, humedad ni viento.
- `maplibre_estimated_field_radius_*_km`, `maplibre_estimated_field_max_radius_km`, `maplibre_estimated_field_grid_*_cell_km`, `maplibre_estimated_field_smoothing_*_power`, `maplibre_estimated_field_temperature_lapse_rate_c_per_100m`: parametros tecnicos de la interpolacion IDW. Se sirven en `/protected/maplibre/config.js` y se actualizan al reiniciar la app.
- `max_threads`, `max_attempts`, `wunderground_daily_api`, `wunderground_full_log`: concurrencia, reintentos, fuente diaria primaria y logging de Wunderground.
- `publish_to_www`: activa la generacion/publicacion legacy en `/config/www` de Bokeh/Google Maps y Leaflet publico. Por defecto esta desactivado.
- `gmap_api_key`: clave Google Maps.
- `aemet_api_key`: clave AEMET OpenData.

## Google Maps API key

`gmap_api_key` debe configurarlo cada usuario con su propia clave de Google Maps. La app la usa en dos sitios:

- En los mapas HTML clasicos generados por Bokeh/Google Maps.
- Durante `update`, cuando Rainmapper necesita completar o refrescar metadata de estaciones: altitud, municipio/localidad y provincia. Esto ocurre sobre todo cuando aparece una estacion nueva, cuando cambian sus coordenadas o cuando la metadata guardada esta incompleta.

No debe guardarse en GitHub ni dentro de la imagen Docker. Home Assistant la almacena como una opcion de tipo `password`.

Si solo ejecutas `update`, la clave puede no usarse en todas las ejecuciones, porque las estaciones ya conocidas conservan su metadata local. Aun asi, puede ser necesaria si hay estaciones nuevas, coordenadas cambiadas o datos de altitud/municipio/provincia pendientes de completar.

La clave debe tener habilitados los servicios de Google necesarios para el uso que hagas: mapas para Bokeh/Google Maps y consultas de elevacion/geocodificacion inversa para completar metadata de estaciones.

## Meteoclimatic pattern

`meteoclimatic_pattern` filtra las estaciones leidas desde el feed RSS de Meteoclimatic.

Puedes indicar un patron unico:

```yaml
meteoclimatic_pattern: ESCAT
```

`ESCAT` selecciona estaciones de Cataluna.

Tambien puedes indicar varios patrones. Se aceptan separadores con coma, punto y coma o ` - `:

```yaml
meteoclimatic_pattern: "ESCAT;ESARA;ESCLM"
```

Ejemplos equivalentes:

```yaml
meteoclimatic_pattern: "ESCAT,ESARA,ESCLM"
meteoclimatic_pattern: "ESCAT - ESARA - ESCLM"
```

La app leera las estaciones que coincidan con cualquiera de los patrones indicados. Si el valor esta mal escrito o no coincide con estaciones del feed, esa fuente puede devolver menos estaciones de las esperadas.

## Rango de dias

`days_init` y `days_end` controlan el rango de fechas usado en la descarga de datos.

Configuracion habitual:

```yaml
days_init: -7
days_end: 0
```

Esto descarga desde 7 dias atras hasta hoy. Normalmente no hace falta cambiarlo salvo para reconstrucciones o pruebas concretas.

Para reconstrucciones largas puede activarse el modo mensual:

```yaml
backfill_months_enabled: true
months_init: -48
months_end: 0
months_interval: 3
backfill_pause_seconds: 5
backfill_station_filter: ""
```

Con esa configuracion, Rainmapper ejecuta updates por ventanas de 3 meses
naturales desde 48 meses atras hasta el mes actual, convirtiendo cada ventana a
`days_init`/`days_end`. Para Wunderground tambien envia los limites locales
`YYYY-MM-DD` de cada ventana, evitando releer el mes anterior por conversion UTC
en reconstrucciones administrativas. Antes de la primera ventana copia los CSV
`*_incremental.csv` a `Data/backups/backfill_incrementals_<timestamp>/`.
Entre ventanas espera la pausa configurada y la muestra en el `Current step` de
la pantalla Summary.

Para reconstruir solo algunas estaciones de una fuente, informa
`backfill_station_filter`:

```yaml
backfill_station_filter: "wunderground::IORDIN1,IMERAN22"
```

El separador entre fuente y estaciones es `::`; las estaciones se separan con
coma. Si hubiera un ID con espacios, puede escribirse entre comillas. Deja el
valor vacio al terminar la reconstruccion para volver a procesar todas las
estaciones.

## Historico reciente en popups

`last_rains_history` controla cuantos registros recientes de lluvia prepara Rainmapper para los popups de estaciones de Leaflet y MapLibre:

```yaml
last_rains_history: 30
```

Este valor afecta a la generacion de los CSV `Tomap` y a las columnas `Data_Pluja_XX`, `Pluja_Diaria_XX`, `Temp_Max_XX` y `Temp_Min_XX` que despues llegan al GeoJSON. Se aplica cuando Rainmapper reconstruye `Tomap`; en Home Assistant, `maps` y `all` reconstruyen `Tomap` antes de generar HTML/GeoJSON.

Los visores detectan dinamicamente cuantos registros trae cada GeoJSON. MapLibre ademas muestra un control `Last rains history` en Settings para limitar cuantos de esos registros ya generados se ven en pantalla. Ese control del visor no crea mas historico; solo filtra lo que ya esta publicado.

## Fuentes de datos

Estas opciones permiten activar o desactivar fuentes:

```yaml
create_meteoclimatic: true
create_meteocat: true
create_wunderground: true
create_aemet: false
```

Si desactivas una fuente, no se descargan datos nuevos de esa fuente en `update` o `all`.

### AEMET OpenData

AEMET es una fuente opcional, desactivada por defecto:

```yaml
create_aemet: false
aemet_api_key: ""
```

Para activarla necesitas una clave de AEMET OpenData. Rainmapper usa el endpoint horario global de observacion convencional, guarda historico horario AEMET, agrega lluvia diaria y, cuando AEMET entrega esos campos, conserva tambien temperatura y humedad para max/min diarios. En Home Assistant, `create_aemet` controla la descarga/refresco de datos AEMET. Los mapas se generan con `--include-aemet true`, por lo que AEMET aparece en el visor protegido estandar siempre que exista un `Aemet_incremental.csv` utilizable.

Para cargar manualmente un historico reciente de dias cerrados, el repositorio incluye `scripts/aemet-backfill-30-days.py`. Ese helper se ejecuta fuera de HA, descarga el endpoint diario de climatologia AEMET, une el inventario de estaciones y genera `Aemet_incremental.csv` en una carpeta temporal local. Si se le pasa un `estacions_aemet.csv` existente con `--station-catalog`, conserva los metadatos enriquecidos de municipio/provincia/comarca. No escribe en `Data/` por defecto; tras revisar la salida, puedes subir manualmente `Aemet_incremental.csv` a la carpeta `Data` de Rainmapper en HA.

La ruta experimental `/local/rainmapper-maplibre-aemet/index.html` queda desactivada por flag como rollback temporal; AEMET ya no depende de un visor separado.

## Meteocat / Socrata

Las lecturas de Meteocat se descargan desde `analisi.transparenciacatalunya.cat` mediante Socrata. Si el servidor tarda demasiado, la app reintenta antes de abortar:

```yaml
meteocat_request_timeout: 30
meteocat_max_attempts: 3
```

`meteocat_request_timeout` es el timeout por intento, en segundos. `meteocat_max_attempts` es el numero maximo de intentos por consulta. Si todos los intentos fallan, el `update` falla para evitar publicar mapas incompletos como si fueran correctos.

## Wunderground

`max_threads` controla el paralelismo al leer estaciones Wunderground. En la instalacion real de Home Assistant/Raspberry Pi se ha validado `3` como valor operativo recomendado:

```yaml
max_threads: 3
```

Si aparecen timeouts, errores de Wunderground o carga excesiva, usar `max_threads: 1` como modo conservador de diagnostico.

`max_attempts` define cuantos reintentos se hacen por estacion:

```yaml
max_attempts: 3
```

`wunderground_daily_api` usa la API diaria de Wunderground como fuente primaria para tablas mensuales. Si la API falla, Rainmapper escribe un log de fallback, usa el scraper HTML existente y muestra el contador `API fallback errors` en el resumen de Wunderground:

```yaml
wunderground_daily_api: true
```

`wunderground_full_log` activa log detallado por estacion:

```yaml
wunderground_full_log: false
```

Usa `true` solo para diagnostico porque el log puede crecer mucho.

## Claves de mapas

`gmap_api_key` es la clave de Google Maps. Se usa para los mapas HTML clasicos Bokeh/Google Maps y tambien para completar metadata de estaciones durante `update` mediante consultas de altitud y geocodificacion inversa. No debe guardarse en Git.

## Wunderground stations.txt

La lista de estaciones Wunderground no esta dentro de la imagen de la app. Esta fuera, en:

```text
/share/rainmapper/stations.txt
```

Esto permite anadir o quitar estaciones sin reconstruir la app.

## Ignorar estaciones en los visores Leaflet/MapLibre

Para ocultar estaciones con datos anomalos en los visores nuevos sin borrar historico, edita:

```text
/share/rainmapper/ignore_stations_tomap.txt
```

Formato:

```text
# Stations ignored when generating GeoJSON / new maps
IOLVAN2
IGUARD34
```

Reglas:

- Una estacion por linea.
- Las lineas vacias se ignoran.
- Puedes usar comentarios con `#`.
- El filtro no afecta a `Data`, `Tomap` ni a la descarga diaria.
- Solo afecta a los GeoJSON publicados para Leaflet y MapLibre.

Para recuperar una estacion, borra su linea y vuelve a ejecutar `maps` o `all`.

## Automatizacion diaria

La app puede programar ejecuciones por si misma mientras esta arrancada en `mode: serve`.

Configuracion recomendada:

```yaml
schedule_enabled: true
schedule_time: "23:50"
schedule_days: all
scheduled_action: all
```

Con esto, Rainmapper se queda vivo como servicio y ejecuta `all` cada dia a las 23:50.

Tambien puedes dejar `schedule_enabled: false` y lanzar ejecuciones manuales desde la webUI.

`schedule_time` tambien acepta varias horas en el mismo campo. Puedes separarlas con comas, punto y coma, espacios o guiones:

```yaml
schedule_time: "06:00, 12:00, 18:00, 23:50"
```

o:

```yaml
schedule_time: "06:00-12:00-18:00-23:50"
```

`schedule_days` permite limitar los dias de ejecucion. Usa `all` para todos los dias, o una lista separada por comas:

```yaml
schedule_days: "mon,tue,wed,thu,fri"
```

Tambien acepta nombres en espanol:

```yaml
schedule_days: "lunes,martes,miercoles,jueves,viernes"
```

## Sidebar

La app soporta `ingress`, asi que Home Assistant puede mostrarla en la barra lateral.

Para probarlo:

1. Configura `mode: serve`.
2. Arranca la app.
3. Activa `Show on sidebar` si Home Assistant muestra esa opcion.
4. Abre `Rainmapper` desde la barra lateral.

La pagina mostrara:

- botones para ejecutar `update`, `maps` y `all`;
- estado de la ultima ejecucion;
- estado separado de Meteoclimatic, Meteocat, Wunderground y AEMET;
- duracion de la ultima ejecucion;
- proxima ejecucion programada;
- informacion de la ultima publicacion en `/local/Plots`;
- enlaces a MapLibre, Leaflet y Bokeh publicados;
- log completo de la ultima ejecucion;
- enlaces a los HTML que haya en:

```text
/share/rainmapper/Plots
```

Importante: `serve` mantiene la app viva para poder servir la pagina. Si usas `mode: update`, `maps` o `all`, la app hara su trabajo y terminara, asi que la barra lateral no tendra un servidor vivo al que conectarse.

### Estado por fuente

La webUI muestra una tarjeta para cada fuente:

- `OK`: la fuente se ha actualizado correctamente.
- `DISABLED`: la fuente esta desactivada en la configuracion y se usan los datos incrementales ya existentes.
- `STALE`: la fuente ha fallado, pero Rainmapper ha podido continuar usando su incremental previo.
- `NOK`: la fuente ha fallado y no habia incremental utilizable para esa fuente.
- `PENDING`: estado temporal mientras se esta ejecutando.

Si una fuente queda como `STALE`, los mapas pueden mezclar datos nuevos de otras fuentes con datos anteriores de esa fuente. Si queda como `NOK`, revisa el log completo de la ejecucion antes de dar por buena la publicacion.

## Primer arranque recomendado

Despues de instalar:

1. Configura `mode: help`.
2. Arranca la app manualmente.
3. Revisa los logs.
4. Si la ayuda aparece correctamente, cambia a `mode: serve`.
5. Copia tus datos historicos a `/share/rainmapper` si quieres conservarlos.
6. Ejecuta una prueba manual desde la webUI.
7. Activa `schedule_enabled` si quieres programacion diaria.

## Copiar datos desde el Mac

Si vienes del Docker local del Mac, el contenido equivalente esta en `docker-data`.

Copia:

```text
docker-data/Data        -> /share/rainmapper/Data
docker-data/Tomap       -> /share/rainmapper/Tomap
docker-data/Plots       -> /share/rainmapper/Plots
docker-data/stations.txt -> /share/rainmapper/stations.txt
```

## Modulo de setas

### Datos persistentes

El modulo de setas guarda sus datos fuera de la imagen, en:

```text
/share/rainmapper/mushroom-data/
```

Ficheros que debes copiar al instalar o actualizar (no se generan automaticamente):

```text
mushroom_profiles.json
mushroom_reference_catalogs.json
mushroom_observations.json
mushroom_labels.json
mushroom_known_sites.json
mushroom_gis_mappings.json
ml_models/                   <- directorio con los .joblib entrenados
```

Las capas GIS/DEM deben ir en `/media/rainmapper/mushroom-GIS/` (no en `/share`;
ese directorio puede ser grande y inflaria los backups de HA).

### Pantalla Predictor

La pantalla `Predictor` muestra predicciones de fructificacion basadas en los
modelos ML entrenados (`ml_models/*.joblib`). Tiene cuatro vistas:

- **Esta semana**: ranking semanal de condiciones por area para cada especie con
  modelo entrenado. Badge favorable/unfavorable/uncertain por dia.
- **Por especie**: detalle de la semana para especie+area seleccionadas.
- **Consultar fecha**: prediccion puntual para una especie, area y fecha concretas.
- **Historial**: backtesting: predicciones pasadas comparadas con observaciones
  reales. Las tarjetas de estadisticas (aciertos/falsos negativos/falsos positivos)
  son clicables y filtran el historial.

Los modelos se cargan bajo demanda; si no hay `.joblib` para una especie, esa
especie no aparece en el selector.

### Mantenimiento ML con worker externo

La pantalla `Workers y trabajos` ofrece un único mantenimiento operativo:

1. Activar `Enable external worker connections` y `Allow external rebuilds and
   promotion` en las opciones de la app.
2. Conectar y emparejar un worker.
3. Ejecutar `Rebuild and retrain operational models`.
4. El worker encadena reconstrucción completa, ML v0 y entrenamiento
   multiversión de las versiones instaladas.
5. HA verifica frescura, integridad y completitud y autopromociona las tres
   salidas como una sola generación. Si la autopromoción se interrumpe, la UI
   puede reanudar únicamente esa promoción conjunta.

`Run scientific benchmark` es independiente: genera informe, predicciones
hold-out, calidad e identidad en estado `evidence_only`. La UI permite consultar
el historial o borrarlo, pero un benchmark no prepara ni activa modelos.

## Desarrollo

En este repositorio hay dos zonas de trabajo:

```text
Raiz del repo           -> Docker local del Mac y contexto de build HA
rainmapper_core/        -> core compartido, generadores y visores
rainmapper-app/app      -> codigo especifico de Home Assistant
```

La imagen de Home Assistant se construye desde la raiz del repositorio y copia `rainmapper_core/` directamente. `rainmapper-app/app` debe quedar reservado a codigo especifico de HA; actualmente contiene `web_server.py`.

Flujo recomendado:

1. Cambia y prueba el codigo en el Docker local del Mac.
2. Ejecuta las validaciones necesarias, como `./scripts/smoke-test.sh`.
3. Publica la imagen HA desde la raiz con `./scripts/build-push-ha-image.sh` solo cuando haya una version nueva.
4. Sube los cambios a GitHub y actualiza o reinstala la app en Home Assistant.

## Problemas habituales

### La instalacion tarda mucho

Es normal en Raspberry Pi. La imagen instala dependencias Python pesadas como `pandas`, `numpy`, `bokeh` y `lxml`.

### No aparecen datos nuevos

Revisa los logs de la app y confirma que el modo es `update` o `all`.

### No aparecen mapas HTML

Ejecuta `mode: maps` o `mode: all` y comprueba `/share/rainmapper/Plots`.

### No aparecen mapas en /local/Plots

Comprueba que `publish_to_www` esta en `true` y ejecuta `maps` o `all`. La publicacion legacy solo ocurre cuando la generacion de mapas termina correctamente.

### El log parece corto o antiguo

La webUI muestra el contenido completo de `/share/rainmapper/last_run.log`, pero ese archivo solo guarda la ultima ejecucion. Cada nuevo `update`, `maps` o `all` sobrescribe el log anterior.

### La barra lateral no carga Rainmapper

Comprueba que la app esta arrancada con `mode: serve`. Si la app esta parada, Home Assistant no tiene ningun servidor interno al que conectar.

### El schedule no se ejecuta

Comprueba que la app esta arrancada en `mode: serve`, que `schedule_enabled` esta en `true`, y que `schedule_time` contiene horas validas en formato `HH:MM`. Si usas `schedule_days`, confirma que incluye el dia actual o usa `all`.

### Quiero cambiar estaciones Wunderground

Edita `/share/rainmapper/stations.txt` y vuelve a ejecutar la app. No hace falta reconstruir la imagen.
