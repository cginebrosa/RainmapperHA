# Rainmapper

Rainmapper es una app de Home Assistant para actualizar datos de lluvia de estaciones meteorologicas y generar los ficheros que usa Rainmapper para sus mapas.

La app esta pensada para ejecutarse bajo demanda o mediante una automatizacion diaria. Arranca, procesa los datos, escribe los resultados en `/share/rainmapper` y termina.

Datos persistentes:

- `/share/rainmapper/Data`
- `/share/rainmapper/Tomap`
- `/share/rainmapper/Plots`
- `/share/rainmapper/stations.txt`

El modo recomendado para uso diario en Home Assistant es `update`.

Para ver los mapas desde la barra lateral de Home Assistant, usa `mode: serve` y arranca la app. Esto sirve los HTML generados en `/share/rainmapper/Plots`.
