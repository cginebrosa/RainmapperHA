# Rainmapper add-on

Este add-on usa la misma logica de Rainmapper, pero adaptada a Home Assistant.

## Donde guarda los datos

El add-on crea y usa estas carpetas:

- `/share/rainmapper/Data`
- `/share/rainmapper/Tomap`
- `/share/rainmapper/Plots`
- `/share/rainmapper/stations.txt`

Si `stations.txt` no existe, lo crea copiando `stations.example.txt`.

## Modos

- `update`: descarga datos y genera los CSV de `Tomap`. Es el modo normal para una automatizacion diaria de Home Assistant.
- `maps`: lee `Tomap` y genera los HTML en `Plots`.
- `all`: hace primero `update` y despues `maps`.
- `help`: muestra la ayuda del script.

## Programacion

En Home Assistant lo recomendable es dejar el add-on con `startup: once` y arrancarlo con una automatizacion a la hora deseada, por ejemplo cada dia a las 23:50. Asi el contenedor trabaja, termina y no queda vivo todo el dia consumiendo recursos.

El modo `schedule` se mantiene solo en el Docker local de desarrollo, no en el add-on.

## Configuracion importante

`meteoclimatic_pattern` permite filtrar estaciones del feed RSS de Meteoclimatic. Por ejemplo, `ESCAT` selecciona estaciones de Cataluna.

`gmap_api_key` debe configurarse si quieres generar mapas que dependan de Google Maps.
