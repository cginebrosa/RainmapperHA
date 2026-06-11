# Rainmapper Home Assistant App

Rainmapper descarga datos de lluvia de estaciones meteorologicas y genera los CSV que despues se usan para crear mapas HTML.

La app se queda abierta como un servicio ligero. Sirve una webUI para Home Assistant, permite lanzar ejecuciones manuales, muestra los mapas generados y puede ejecutar un schedule interno.

## Como funciona

La app ejecuta los mismos scripts de Rainmapper dentro de un contenedor Docker controlado por Home Assistant.

Flujo habitual:

1. Home Assistant arranca la app como servicio.
2. La webUI queda disponible mediante ingress y sidebar.
3. Desde la webUI puedes lanzar `update`, `maps` o `all`.
4. Si el schedule interno esta activado, la app ejecuta la accion configurada cada dia.
5. Los datos y mapas se guardan en `/share/rainmapper`.
6. Si `publish_to_www` esta activado, los mapas HTML tambien se copian a `/config/www/Plots`.

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
```

Contenido esperado:

- `Data`: CSV historicos e incrementales de Meteocat, Meteoclimatic y Wunderground.
- `Tomap`: CSV preparados para pintar mapas.
- `Plots`: HTML generados por `Rainmapper_Client.py`.
- `stations.txt`: lista de estaciones Wunderground que quieres descargar.

Si `stations.txt` no existe, la app lo crea automaticamente copiando una plantilla. Despues puedes editarlo desde la carpeta compartida.

## Mapas publicados en /local/Plots

Si `publish_to_www` esta activado, cada vez que `maps` termina correctamente la app copia una version publica de los mapas a:

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

La carpeta interna `/share/rainmapper/Plots` sigue siendo la salida principal de Rainmapper. La carpeta `/config/www/Plots` es solo una copia publicada para acceder a los mapas desde Home Assistant.

Al publicar, la app recrea `/config/www/Plots` completa. Asi evita dejar HTML antiguos que ya no correspondan a la ultima generacion.

## Modos de ejecucion

`mode` controla que hace la app al arrancar.

```text
help
```

Muestra la ayuda de `Rainmapper.py`. Es util para una primera prueba despues de instalar.

```text
update
```

Descarga datos y genera los CSV de `Tomap`. Es el modo recomendado para la ejecucion diaria en Home Assistant.

```text
maps
```

Lee los CSV de `Tomap` y genera los HTML en `Plots`. No descarga datos nuevos.

```text
all
```

Ejecuta primero `update` y despues `maps`. Es comodo para una prueba completa, pero normalmente no hace falta usarlo cada dia si solo quieres actualizar datos.

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
schedule_time: "23:50"
scheduled_action: all
days_init: -7
days_end: 0
create_meteoclimatic: true
create_meteocat: true
create_wunderground: true
meteoclimatic_pattern: ESCAT
nomaps: false
nototals: false
days_bucket: 10
max_threads: 1
max_attempts: 3
publish_to_www: true
```

## Google Maps API key

`gmap_api_key` debe configurarlo cada usuario con su propia clave de Google Maps.

No debe guardarse en GitHub ni dentro de la imagen Docker. Home Assistant la almacena como una opcion de tipo `password`.

Si solo ejecutas `update`, la clave puede no ser necesaria en todas las ejecuciones. Si generas mapas HTML que usan Google Maps, debes configurarla.

## Meteoclimatic pattern

`meteoclimatic_pattern` filtra las estaciones leidas desde el feed RSS de Meteoclimatic.

Ejemplo:

```yaml
meteoclimatic_pattern: ESCAT
```

`ESCAT` selecciona estaciones de Cataluna.

## Wunderground stations.txt

La lista de estaciones Wunderground no esta dentro de la imagen de la app. Esta fuera, en:

```text
/share/rainmapper/stations.txt
```

Esto permite anadir o quitar estaciones sin reconstruir la app.

## Automatizacion diaria

La app puede programar ejecuciones por si misma mientras esta arrancada en `mode: serve`.

Configuracion recomendada:

```yaml
schedule_enabled: true
schedule_time: "23:50"
scheduled_action: all
```

Con esto, Rainmapper se queda vivo como servicio y ejecuta `all` cada dia a las 23:50.

Tambien puedes dejar `schedule_enabled: false` y lanzar ejecuciones manuales desde la webUI.

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
- duracion de la ultima ejecucion;
- proxima ejecucion programada;
- informacion de la ultima publicacion en `/local/Plots`;
- log completo de la ultima ejecucion;
- enlaces a los HTML que haya en:

```text
/share/rainmapper/Plots
```

Importante: `serve` mantiene la app viva para poder servir la pagina. Si usas `mode: update`, `maps` o `all`, la app hara su trabajo y terminara, asi que la barra lateral no tendra un servidor vivo al que conectarse.

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

## Desarrollo

En este repositorio hay dos zonas de trabajo:

```text
Raiz del repo           -> Docker local del Mac
rainmapper-app/app      -> codigo empaquetado para Home Assistant
```

Flujo recomendado:

1. Cambia y prueba el codigo en el Docker local del Mac.
2. Cuando funcione, copia esos cambios a `rainmapper-app/app`.
3. Sube los cambios a GitHub.
4. Actualiza o reinstala la app en Home Assistant.

## Problemas habituales

### La instalacion tarda mucho

Es normal en Raspberry Pi. La imagen instala dependencias Python pesadas como `pandas`, `numpy`, `bokeh` y `lxml`.

### No aparecen datos nuevos

Revisa los logs de la app y confirma que el modo es `update` o `all`.

### No aparecen mapas HTML

Ejecuta `mode: maps` o `mode: all` y comprueba `/share/rainmapper/Plots`.

### No aparecen mapas en /local/Plots

Comprueba que `publish_to_www` esta en `true` y ejecuta `maps` o `all`. La publicacion solo ocurre cuando la generacion de mapas termina correctamente.

### El log parece corto o antiguo

La webUI muestra el contenido completo de `/share/rainmapper/last_run.log`, pero ese archivo solo guarda la ultima ejecucion. Cada nuevo `update`, `maps` o `all` sobrescribe el log anterior.

### La barra lateral no carga Rainmapper

Comprueba que la app esta arrancada con `mode: serve`. Si la app esta parada, Home Assistant no tiene ningun servidor interno al que conectar.

### El schedule no se ejecuta

Comprueba que la app esta arrancada en `mode: serve`, que `schedule_enabled` esta en `true`, y que `schedule_time` usa formato `HH:MM`.

### Quiero cambiar estaciones Wunderground

Edita `/share/rainmapper/stations.txt` y vuelve a ejecutar la app. No hace falta reconstruir la imagen.
