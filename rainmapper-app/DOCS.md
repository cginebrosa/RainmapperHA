# Rainmapper Home Assistant App

Rainmapper descarga datos de lluvia de estaciones meteorologicas y genera los CSV que despues se usan para crear mapas HTML.

Esta app no es una web que quede ejecutandose continuamente. Esta pensada para arrancar, trabajar durante unos minutos y terminar. Por eso consume pocos recursos en una Raspberry Pi y encaja bien con una automatizacion diaria de Home Assistant.

## Como funciona

La app ejecuta los mismos scripts de Rainmapper dentro de un contenedor Docker controlado por Home Assistant.

Flujo habitual:

1. Home Assistant arranca la app manualmente o mediante una automatizacion.
2. Rainmapper descarga o actualiza datos meteorologicos.
3. Se generan los CSV de salida en `Tomap`.
4. La app termina y el contenedor se apaga.

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

Arranca un servidor web pequeno para ver los mapas HTML generados en `Plots` desde Home Assistant. Este modo no descarga datos y no genera mapas nuevos; solo muestra los HTML que ya existan en `/share/rainmapper/Plots`.

Para usar la barra lateral de Home Assistant, la app debe estar arrancada en este modo.

## Configuracion recomendada

Para uso diario:

```yaml
mode: update
timezone: Europe/Madrid
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

La app tiene `startup: once`. Esto significa que no esta pensada para quedarse viva todo el dia.

Lo recomendable es crear una automatizacion de Home Assistant que la arranque cada dia, por ejemplo a las 23:50. La app correra, terminara y el contenedor se apagara.

Ejemplo conceptual:

```yaml
trigger:
  - platform: time
    at: "23:50:00"
action:
  - service: hassio.addon_start
    data:
      addon: rainmapper
```

El identificador exacto del servicio puede depender de como Home Assistant exponga la app instalada. Conviene seleccionarlo desde el editor visual de automatizaciones si esta disponible.

## Sidebar

La app soporta `ingress`, asi que Home Assistant puede mostrarla en la barra lateral.

Para probarlo:

1. Configura `mode: serve`.
2. Arranca la app.
3. Activa `Show on sidebar` si Home Assistant muestra esa opcion.
4. Abre `Rainmapper` desde la barra lateral.

La pagina mostrara una lista de los HTML que haya en:

```text
/share/rainmapper/Plots
```

Importante: `serve` mantiene la app viva para poder servir la pagina. Si usas `mode: update`, `maps` o `all`, la app hara su trabajo y terminara, asi que la barra lateral no tendra un servidor vivo al que conectarse.

## Primer arranque recomendado

Despues de instalar:

1. Configura `mode: help`.
2. Arranca la app manualmente.
3. Revisa los logs.
4. Si la ayuda aparece correctamente, cambia a `mode: update`.
5. Copia tus datos historicos a `/share/rainmapper` si quieres conservarlos.
6. Ejecuta una prueba manual.
7. Crea la automatizacion diaria.

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

### La barra lateral no carga Rainmapper

Comprueba que la app esta arrancada con `mode: serve`. Si la app esta parada, Home Assistant no tiene ningun servidor interno al que conectar.

### Quiero cambiar estaciones Wunderground

Edita `/share/rainmapper/stations.txt` y vuelve a ejecutar la app. No hace falta reconstruir la imagen.
