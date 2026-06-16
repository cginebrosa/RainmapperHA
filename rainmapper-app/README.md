# Rainmapper

Rainmapper es una app de Home Assistant para actualizar datos de lluvia de estaciones meteorologicas, generar mapas HTML y consultarlos desde la barra lateral de Home Assistant.

La app se queda abierta como un servicio ligero. Desde su webUI puedes lanzar `update`, `maps` o `all`, ver el estado de la ultima ejecucion, consultar logs recientes y abrir los mapas generados.

Cuando `publish_to_www` esta activado, cada generacion de mapas publica una copia en `/config/www/Plots`, accesible desde Home Assistant como `/local/Plots`.

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
