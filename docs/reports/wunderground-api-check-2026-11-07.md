# Wunderground: comprobación directa del 07/11/2026

Consulta de sólo lectura a las **17:08, Europe/Madrid**. Sin modificar datos
operativos ni guardar la clave pública, descubierta en memoria con el mecanismo
del descargador. No se cambió código de descarga Wunderground en esta revisión.

Endpoint comprobado: `https://api.weather.com/v2/pws/history/daily`.
Parámetros del tramo de noviembre del runner: `startDate=20261101`,
`endDate=20261107`, `format=json`, `units=e`, `numericPrecision=decimal` y el
`stationId` de cada fila. Se contrastaron `epoch`, `obsTimeUtc` y `obsTimeLocal`.
Se solicitó cada variante de `Accept-Encoding` usada por el descargador.

## Respuestas antiguas confirmadas en la muestra

Última lectura, expresada en hora peninsular española:

| Estación | gzip | identity | deflate |
| --- | --- | --- | --- |
| IALCAL123 | 07/11 01:44:51 | 07/11 06:04:50 | 07/11 11:00:02 |
| IALMOS1 | 07/11 01:44:55 | 07/11 06:04:55 | 07/11 10:59:55 |

Las seis respuestas fueron HTTP 200. El timestamp HTTP era actual; la lectura
meteorológica más reciente llevaba unas 6,13–6,14 horas de retraso. El umbral
existente es 4 horas (`CACHE_STALE_AFTER_HOURS` en `daily_api.py`). El descargador
elige el mayor epoch y avisa si continúa por debajo de ese umbral: en estos dos
casos el aviso coincide con los datos originales de la API, no con un error de
zona horaria ni de interpretación del log.

## Cuatro estaciones sin observaciones

`IBAG57`, `IFUENT4`, `ILAVAN3` e `IMONTF44` devolvieron **HTTP 204 sin
observaciones en las tres variantes** para ese mismo intervalo. El log aportado
por el usuario también registra el fallo posterior del fallback HTML: no encontró
la tabla histórica. En esta comprobación se contrastó directamente la API, no se
volvió a ejecutar el scraper HTML.

## Alcance

El runner local contó 105 respuestas antiguas tras reintentos, cuatro estaciones
fallidas y 109 actualizadas. Se verificó directamente la muestra de dos estaciones
antiguas y las cuatro fallidas, no las 113 estaciones. El usuario comunicó los
mismos avisos en HA real con 0.2.340. Estas respuestas no identifican por sí solas
la causa del retraso ni demuestran una incidencia global de Wunderground.
