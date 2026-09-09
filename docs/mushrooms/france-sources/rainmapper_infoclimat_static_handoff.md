# Rainmapper — evaluación descartada de Infoclimat / StatIC

## Handoff verificado para Quérigut–Font-Romeu

**Revisión:** 9 de septiembre de 2026

**Estado:** fuente contrastada y descartada para el corredor inicial

**Alcance:** pruebas no destructivas y documentación; no se prevé implementación

## 1. Conclusión

Infoclimat/StatIC es técnicamente utilizable, pero **no se integrará** en el
alcance Quérigut–Font-Romeu. La cobertura obtenida no justifica crear un quinto
proveedor meteorológico, añadir otro secreto y mantener reglas específicas de
licencia, intervalos y lluvia.

Las pruebas reales dejan dos estaciones utilizables:

```text
000EN — Osséja — 1350 m
000BR — Mérens-les-Vals — 1070 m
```

Osséja era la única candidata útil para la Cerdanya francesa. Mérens-les-Vals
queda fuera del corredor piloto. Las estaciones prioritarias ya están cubiertas
por el proveedor Wunderground que Rainmapper utiliza:

```text
IFORMI6 — Formiguères
IFONTR8 — Font-Romeu-Odeillo-Via
```

En la generación canónica local del 8 de septiembre de 2026, `IFORMI6` contiene
292 días entre 2025-09-01 y 2026-09-08, e `IFONTR8` contiene 1.286 días entre
2022-11-04 y 2026-09-08. Ambas estaciones respondieron también a la API de
Wunderground el 9 de septiembre de 2026.

La API de Infoclimat quedó validada sólo como resultado técnico de la
investigación. No se crearán cliente, agregador, cola diaria ni configuración HA
para esta fuente.

Las estaciones Météo-France propuestas no están disponibles mediante esta API
con los identificadores probados. Deben obtenerse directamente de Météo-France.

## 2. API comprobada

Endpoint:

```text
https://www.infoclimat.fr/opendata/
```

Petición:

```text
version=2
method=get
format=json
stations[]=<ID>
start=YYYY-MM-DD
end=YYYY-MM-DD
token=<secreto>
```

La clave se leyó de `INFOCLIMAT_API_KEY`. No se imprimió ni se guardó en el
repositorio. Las respuestas de prueba quedaron sólo en `/private/tmp`.

La página oficial indica un máximo de siete días consecutivos, salvo para el
propietario de la estación:

https://www.infoclimat.fr/opendata/

### Intervalo inclusivo

La petición de Osséja entre `2026-09-01` y `2026-09-07` devolvió:

```text
status: OK
errors: []
primera fila: 2026-09-01 00:00:00 UTC
última fila:  2026-09-07 23:50:00 UTC
filas: 1008
```

`end` es inclusivo en la respuesta comprobada. Siete fechas completas producen
`7 × 24 × 6 = 1008` observaciones. Los backfills deben dividirse en bloques de
como máximo siete fechas inclusivas, sin solapamientos accidentales.

### Datos del día actual

La consulta de Osséja para el 8 de septiembre, realizada antes de terminar el
día, devolvió 132 filas hasta las 21:50 UTC. La consulta de Mérens-les-Vals
devolvió 133 filas hasta las 22:00 UTC.

La API sirve para mostrar el estado del día en MapLibre. Esas filas forman un día
parcial: no deben entrar como día cerrado en entrenamiento ni predicción.

## 3. Forma de la respuesta

Estructura comprobada:

```json
{
  "status": "OK",
  "errors": [],
  "data": [],
  "stations": [],
  "metadata": {},
  "hourly": {
    "000EN": []
  }
}
```

Los datos están en:

```python
response["hourly"][station_id]
```

No están en `response["data"]`. El parser debe validar `status`, inspeccionar
siempre `errors` y tolerar una estación autorizada sin observaciones.

Un HTTP correcto tampoco garantiza éxito. Por ejemplo, las estaciones no
autorizadas devolvieron JSON válido con:

```text
status: warning
errors:
  - Station '<ID>' not allowed here.
  - No valid stations were requested.
```

## 4. Resultado de todas las estaciones solicitadas

Se consultó el 8 de septiembre de 2026 para las estaciones actuales. Para
`000RX`, que está inactiva, se consultaron además el inicio oficial de su archivo
y el 25–26 de mayo de 2026.

| Prioridad | ID probado | Estación | Resultado real | Decisión |
|---|---|---|---|---|
| alta | `000EN` | Osséja, 1350 m | `OK`; 132 filas actuales; CC BY-NC | API válida; integración descartada |
| alta | `STATIC0478` | Font-Romeu, 1952 m | `warning`; `not allowed here` | desactivada |
| media | `000BR` | Mérens-les-Vals, 1070 m | `OK`; 133 filas actuales; CC BY-NC | API válida; integración descartada y fuera del piloto |
| media | `000RX` | Font-Romeu anterior, 1788 m | `OK`; archivo accesible desde 17/06/2020 y datos hasta 26/05/2026; CC BY | histórico localizado; integración descartada |
| alta | `07737` | Formiguères | `warning`; `not allowed here` | usar Météo-France directa |
| alta | `MF66082004` | Formiguères | `warning`; `not allowed here` | usar Météo-France directa |
| media | `MF66004401` | Les Angles | `warning`; `not allowed here` | usar Météo-France directa |
| media | `MF09239005` | Quérigut | `warning`; `not allowed here` | sin fuente Infoclimat |

No se ha probado otra variante de ID para Les Angles o Quérigut porque no existe
evidencia actual de una variante Infoclimat válida. No se inventará una.

### Font-Romeu: dos identidades distintas

El catálogo ampliado contiene:

```text
STATIC0478 — 1952 m — Etalab Open License — actividad reciente
000RX      — 1788 m — CC BY              — archivo 2020-06-17 a 2026-05-26
```

No son intercambiables. `STATIC0478` aparece en el catálogo pero la API no la
autoriza con la clave probada. `000RX` sí está autorizada, pero no aporta tiempo
actual. Nunca deben fusionarse por compartir municipio o nombre.

La API devolvió 53 filas de `000RX` el 17 de junio de 2020, desde las 10:45 hasta
las 23:45 UTC, y 138 filas entre el 25 de mayo de 2026 a las 00:00 y el 26 de
mayo a las 12:00 UTC. La página de metadatos confirma apertura el 17 de junio de
2020 y último reporte el 26 de mayo de 2026.

## 5. `version=2`

Se comparó la misma estación y fecha con y sin `version=2`.

La respuesta básica incluye:

```text
temperature
pression
humidite
point_de_rosee
vent_moyen
vent_rafales
vent_direction
pluie_1h
pluie_3h
```

La versión 2 añade, entre otros:

```text
vent_rafales_10min
temperature_min
temperature_max
pluie_6h
pluie_12h
pluie_24h
pluie_cumul_0h
pluie_intensite
pluie_intensite_max_1h
source
uv
```

Para Osséja, un día ocupó aproximadamente 66 kB en la versión básica y 168 kB
en versión 2. Una semana completa en versión 2 ocupó aproximadamente 1,26 MB.

Decisión:

- usar `version=2`, porque aporta el cierre `pluie_24h` necesario para reproducir
  el episodio validado;
- extraer sólo los campos necesarios;
- procesar y agregar por estación/bloque;
- no conservar grandes respuestas JSON en HA.

## 6. Precipitación: corrección crítica

La propuesta original de reproducir 18,4 mm sumando `pluie_1h` por fecha UTC no
funciona.

En la descarga de Osséja del 23 al 25 de agosto:

- hubo 432 observaciones de diez minutos;
- `pluie_1h` apareció una vez por hora, con 72 valores no nulos;
- la suma del 24 de agosto UTC fue 18,2 mm;
- la suma del 25 de agosto UTC fue 0,2 mm;
- `pluie_24h` apareció a las 06:00 UTC;
- `2026-08-25 06:00:00` contenía `pluie_24h = 18.4`.

La climatología de Infoclimat publica 18,4 mm para el 24 de agosto:

https://www.infoclimat.fr/climatologie/annee/2026/osseja/valeurs/000EN.html

La coincidencia se obtiene con el acumulado de 24 horas entregado a las 06:00
UTC del día siguiente. Por tanto, no se debe validar contra una suma por
calendario UTC ni asumir que la lluvia usa la misma medianoche que temperatura y
humedad.

### Regla inicial para días cerrados

Para `000EN`, sólo si alguna vez se reabre la decisión, habría que repetir la
prueba en más episodios:

1. usar `pluie_24h` de las 06:00 UTC como total cerrado;
2. asignarlo a la fecha climatológica anterior;
3. conservar hora de cierre y cobertura en el informe de ingestión;
4. no sustituirlo silenciosamente por la suma de `pluie_1h`;
5. no generalizar la regla a todas las estaciones hasta validarla.

`pluie_1h` es útil para el estado intradía y para auditar cobertura. Los `null`
no son ceros y no deben sumarse seis veces por hora.

## 7. UTC, día local y estado intradía

La API usa `dh_utc`. Para temperatura, humedad y viento:

1. interpretar el texto como UTC;
2. convertirlo a `Europe/Paris`;
3. conservar UTC y fecha local en el staging acotado;
4. agrupar con una convención explícita y probada también durante cambios DST.

Una implementación futura tendría que separar:

```text
estado intradía para MapLibre
    datos parciales del día, con hora y antigüedad

histórico diario para entrenamiento/predicción
    sólo días cerrados y sustituibles por correcciones posteriores
```

Rainmapper ya limita la predicción al día anterior. Los datos del día actual no
deben cambiar esa regla.

## 8. Mapeo al contrato actual de Rainmapper

El diseño original proponía medias y punto de rocío que no existen en el contrato
diario actual. No se ampliará el esquema sin un consumidor concreto.

El contrato de `rainmapper_core/weather_history_contract.py` contiene:

```text
rain_mm
max_temp_celsius
min_temp_celsius
max_humidity_percent
min_humidity_percent
wind_avg_kmh
wind_min_kmh
wind_max_kmh
wind_gust_kmh
wind_direction_deg
wind_gust_direction_deg
wind_observation_count
wind_source_height_m
```

Mapeo propuesto:

| Infoclimat | Rainmapper | Regla |
|---|---|---|
| `pluie_24h` | `rain_mm` | cierre 06:00 UTC, fecha anterior; aún por validar en más episodios |
| `temperature` | mínimo/máximo de temperatura | extremos de muestras válidas |
| `humidite` | mínimo/máximo de humedad | extremos de muestras válidas |
| `vent_moyen` | media/mínimo/máximo de viento | ya viene en km/h |
| `vent_rafales_10min` | `wind_gust_kmh` | máximo; `vent_rafales` como respaldo documentado |
| `vent_direction` | `wind_direction_deg` | media circular |

`point_de_rosee`, presión, radiación y medias pueden quedar en diagnósticos de
evaluación, pero no en cada fila canónica.

## 9. Cobertura y calidad

Para una fecha completa de diez minutos se esperan 144 muestras. Para
`pluie_1h`, 24 valores horarios no nulos. Son medidas de cobertura, no una prueba
automática de calidad.

Registrar por variable y bloque:

```text
available_samples
expected_samples
coverage_ratio
first_timestamp_utc
last_timestamp_utc
daily_close_present
api_status
api_errors
```

Reglas mínimas:

- `null` permanece ausente;
- no rellenar temperatura, humedad o viento con cero;
- no declarar lluvia cerrada sin el cierre elegido;
- no ocultar estaciones fallidas tras un éxito parcial;
- permitir que una corrección posterior sustituya la fila canónica.

Los umbrales exactos de aceptación de un día incompleto aún no están definidos
para una serie StatIC de diez minutos. Deben decidirse con más muestras.

## 10. Catálogo de estaciones

Catálogo activo comprobado:

```text
https://www.infoclimat.fr/opendata/stations_xhr.php?format=geojson
```

El 8 de septiembre de 2026 devolvió 1222 estaciones y aproximadamente 953 kB.
Incluía para Osséja ID, coordenadas, altitud, licencia, departamento y
`last_activity`.

Catálogo ampliado para auditoría:

```text
https://www.infoclimat.fr/opendata/stations_xhr.php?format=geojson&display_closed=1
```

Que una estación aparezca en el catálogo no prueba que la API la autorice ni que
entregue datos recientes. La selección debe seguir este orden:

```text
catálogo
    -> radio del área
    -> actividad reciente
    -> licencia compatible
    -> petición autenticada real
    -> comparación con Météo-France
    -> alta explícita
```

## 11. Coste de integración evitado

Rainmapper no tiene una clase base de proveedores meteorológicos. No se creará
una clase `InfoclimatProvider` aislada.

Estado actual verificado:

- `KNOWN_SOURCES` sólo admite AEMET, Meteocat, Meteoclimatic y Wunderground;
- `LIVE_CSV_FILES` y `DAILY_INCREMENTAL_FILES` sólo incluyen esas cuatro;
- el contrato IDW declara esas cuatro fuentes;
- el lector Parquet de Tomap también las filtra explícitamente;
- `config.yaml` sólo ofrece secretos para Google Maps y AEMET;
- el viento canónico ya usa km/h, igual que Infoclimat.

Una integración habría exigido, como mínimo:

```text
rainmapper_core/create_infoclimat.py             cliente, parser y agregación
rainmapper_core/weather_history_contract.py      source=infoclimat
rainmapper_core/weather_live_csv.py              cola diaria
rainmapper_core/mushroom_observation_context.py  contexto multiespecie
rainmapper_core/mushroom_weather_idw.py           fuente IDW
rainmapper_core/tomap.py                          filtro Parquet
rainmapper-local/docker-compose.yml               secreto local
rainmapper-app/config.yaml y run.sh               secreto HA
tests dirigidos                                   contrato y casos reales fijados
```

Cola propuesta:

```text
Infoclimat_incremental.csv
source = infoclimat
clave = (infoclimat, station_code, local_date)
```

## 12. Secreto usado durante la evaluación

Variable disponible para pruebas en el Mac:

```text
INFOCLIMAT_API_KEY
```

No se añadirá `RAINMAPPER_INFOCLIMAT_API_KEY` ni una opción
`infoclimat_api_key` a HA. La variable usada para las pruebas puede eliminarse
del entorno cuando ya no sea necesaria.

Nunca debe aparecer en URLs registradas, logs, excepciones, diagnósticos o
fixtures.

## 13. Política que habría sido necesaria

Esta sección se conserva únicamente para que la evaluación sea reproducible si
en el futuro cambia de forma sustancial la cobertura disponible:

1. Consultar una ventana reciente solapada de hasta siete fechas.
2. Procesar una estación y bloque cada vez.
3. Separar el día actual de los días cerrados.
4. Generar filas compatibles con el contrato existente.
5. Aplicar upsert por `(source, station_code, local_date)`.
6. Permitir correcciones posteriores.
7. Registrar errores por estación y el carácter parcial del resultado.

No se repetirá todo el histórico en cada ejecución. Un backfill inicial avanzará
en bloques de siete fechas y podrá reanudarse desde el último bloque confirmado.

## 14. Pruebas que serían necesarias si se reabre la decisión

### Parser/API

- `status == OK` y `errors == []`;
- `status == warning` es fallo funcional;
- estación autorizada sin filas no es error de transporte;
- `hourly[station_id]` puede faltar;
- strings numéricos y `null` se normalizan correctamente;
- campos extra de versión 2 no rompen el parser;
- el secreto nunca aparece en mensajes.

### Intervalos/tiempo

- `start` y `end` inclusivos;
- bloques de una a siete fechas sin huecos;
- conversión UTC a `Europe/Paris`, incluido DST;
- el día actual permanece parcial;
- el histórico no incorpora el día en curso.

### Lluvia

- `pluie_1h` no se suma seis veces por hora;
- `null` no se convierte en cero;
- `2026-08-25 06:00 UTC -> pluie_24h=18.4` produce el cierre del 24 de agosto;
- ausencia de cierre se informa, no se disfraza como 0 mm;
- episodios adicionales confirman o invalidan la regla antes de generalizarla.

### Integración

- fila canónica con `source=infoclimat`;
- deduplicación y reemplazo por clave canónica;
- cola viva acotada;
- inclusión en histórico particionado, contexto multiespecie, IDW y Tomap;
- licencia y atribución deduplicadas en el catálogo, no repetidas en cada fila.

## 15. Decisión de implementación

No hay implementación prevista. Para el corredor inicial se reutilizarán
`IFORMI6` e `IFONTR8` y se añadirá el histórico oficial de Météo-France. Esta
decisión sólo se reabrirá si aparece una cobertura Infoclimat claramente mejor
que no esté disponible mediante esas dos fuentes.

## 16. Fuentes

- OpenData: https://www.infoclimat.fr/opendata/
- catálogo activo: https://www.infoclimat.fr/opendata/stations_xhr.php?format=geojson
- metadatos de Osséja: https://www.infoclimat.fr/stations/metadonnees.php?id=000EN
- tiempo real de Osséja: https://www.infoclimat.fr/observations-meteo/temps-reel/osseja/000EN.html
- climatología 2026: https://www.infoclimat.fr/climatologie/annee/2026/osseja/valeurs/000EN.html
- catálogo data.gouv.fr: https://www.data.gouv.fr/fr/datasets/liste-des-stations-en-open-data-du-reseau-meteorologique-infoclimat-static-et-meteo-france-synop/

## 17. Decisión final

Infoclimat queda descartado para el corredor inicial. No se implementará ni se
solicitará ninguna credencial adicional para HA. El resultado de Osséja y la
diferencia entre `pluie_24h` y la suma por calendario UTC se conservan como
evidencia técnica, no como trabajo pendiente.
