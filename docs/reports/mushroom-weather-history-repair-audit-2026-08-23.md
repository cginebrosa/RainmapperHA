# Auditoría de reparación del histórico meteorológico — 2026-08-23

## Resultado

La pérdida de muestras de entrenamiento no procedía de que el preparador
ignorase el IDW. Las muestras excluidas conservaban el contrato
`daily_weather_idw_radius15km_power2_temp_altitude_v1`, pero el histórico activo
de HA contenía particiones oficiales antiguas incompletas.

La descarga directa de HA apuntaba a la generación
`20260822T215331118702Z-d31546032805`. El lote ML local activo
`local_operational_20260822T115556Z` había congelado exactamente los mismos
hashes incompletos en su snapshot de entrenamiento.

Descomposición observada de las 417 observaciones:

- 43 no tienen target operativo de entrenamiento (`calibration_use=review`):
  13 están en borrador y 30 son válidas pero siguen en revisión;
- quedan 374 observaciones con target utilizable;
- con el histórico incompleto, V3 aceptaba 324 y V4
  `extended_weather`/`climatic_balance` aceptaba 308;
- con el histórico reparado, V3 y esos dos bloques V4 aceptan las 374.

Por tanto, las 50 exclusiones V3 y las 16 exclusiones adicionales V4 eran
consecuencia de cobertura meteorológica histórica insuficiente. No eran una
carencia intrínseca de observaciones ni un bypass del IDW.

## Evidencia de la causa

En la generación descargada de HA, AEMET no tenía ningún valor de humedad entre
2012 y 2025. En 2026 la humedad comienza el 23 de junio y faltaba en el 73,3 %
de las filas anuales acumuladas. Ejemplo: AEMET 2023 contenía 301.958 filas y
cero valores de humedad.

Meteocat 2012–2016 estaba prácticamente completo gracias al backfill histórico
inicial. El tramo local posterior era el defectuoso: por ejemplo, Meteocat 2020
tenía 14.733 filas en HA frente a 68.051 después de la reparación.

El IDW sí se calculaba en las muestras rechazadas. No podía producir humedad
cuando ninguna estación dentro del radio contractual de 15 km tenía un valor
para el día. Las 50 muestras V3 perdidas fallaban el mínimo de 19/21 días de
humedad; parte de ellas también fallaba lluvia o temperatura.

## Construcción aislada

La descarga original se preservó en:

`docker-data/audits/ha-weather-history-check-20260823/incoming/weather-history`

La reparación se construyó sin escribir en HA ni en el histórico Docker activo.
Partió de esa generación y reutilizó los payloads oficiales cacheados y ya
auditados:

- AEMET: 4.177.019 filas pendientes, años 2012–2026;
- Meteocat: 658.893 filas pendientes, años 2016–2026.

La generación lógica reparada resultante fue
`20260822T232738692904Z-04c84f3821c4`.

Las puertas de no pérdida dieron:

- AEMET: cero claves antiguas perdidas; días-hueco internos
  202.117 → 121.467;
- Meteocat: cero claves antiguas perdidas; días-hueco internos
  326.531 → 1.664;
- Wunderground y Meteoclimatic: las 16 particiones activas conservaron
  exactamente sus hashes y conteos de HA.

Informes primarios:

- `docker-data/audits/ha-weather-history-check-20260823/reports/build-candidate.json`;
- `docker-data/audits/ha-weather-history-check-20260823/reports/audit-final-aemet.json`;
- `docker-data/audits/ha-weather-history-check-20260823/reports/audit-final-meteocat.json`.

## Compactación física

La reconstrucción masiva expuso un defecto físico del camino de merge: al
intercalar millones de actualizaciones de una fila, `_BoundedTableWriter`
vaciaba al alcanzar 128 fragmentos, aunque el objetivo de grupo fuese 8.192
filas. Las 30 particiones oficiales quedaron con 37.828 grupos Parquet y
349.959.233 bytes de objetos activos.

Se realizó una compactación sin pérdida a grupos de 8.192 filas, coherente con
la granularidad anterior. Cada partición reescrita fue releída y comparada
íntegramente con su tabla de origen: mismo esquema, orden, filas y valores. El
resultado tiene 651 grupos oficiales y 49.590.594 bytes de objetos activos.

La primera generación compactada para entrega fue
`20260822T233809281377Z-24ed6ad33848`, en:

`docker-data/audits/ha-weather-history-check-20260823/ready-to-upload-final/weather-history`

Contenía solo `CURRENT.json`, el manifiesto y catálogo activos y las 46
particiones referenciadas. La resolución con verificación de hashes aceptó las
46 particiones, 5.480.224 filas y el total declarado.

Una copia temporal de la entrega superó además una actualización incremental
real del escritor: añadió una fila de prueba, creó la generación hija
`20260822T234518796591Z-e014f4bed33b`, enlazó
`previous_generation_id` con la generación compactada y resolvió 5.480.225
filas con verificación completa de hashes. La copia entregable no fue modificada
por esta prueba.

La primera salida compactada, `ready-to-upload-compact`, fue rechazada por el
propio lector porque el total del manifiesto omitía el tamaño del catálogo. No
debe utilizarse. Se conservó como evidencia del fallo; la carpeta con sufijo
`final` corrige el manifiesto y es la única entregable.

## Corrección de raíz tras el primer runner real

Después de instalar la salida compactada en HA, el runner del
2026-08-23 02:30 CEST se detuvo en `archive pending before update`, antes de
actualizar ninguna fuente. `prune_weather_generations` rechazó correctamente la
limpieza porque el manifiesto activo retenía como predecesora la generación
`20260822T232738692904Z-04c84f3821c4`, cuyo manifiesto no formaba parte de la
entrega compacta.

No se restauraron los objetos de la generación anterior: 26 de sus 47 objetos
ya no estaban en HA y habrían reintroducido 342.385.868 bytes declarados. Se
creó en su lugar una nueva generación raíz que referencia exactamente los
mismos objetos compactados y declara `previous_generation_id: null`:

`20260823T003617919308Z-58903f62a763`

La carpeta `ready-to-upload-final/weather-history` apunta ahora a esa raíz. La
corrección mínima que debe copiarse sobre una instalación que ya contiene los
objetos está en:

`docker-data/audits/ha-weather-history-check-20260823/ready-to-upload-root-fix/weather-history`

Solo contiene el nuevo manifiesto y `CURRENT.json`. Ambas copias locales
resolvieron con verificación completa de hashes: 46 particiones, 5.480.224 filas
y 49.590.594 bytes activos. Una copia temporal superó el mismo comando que
había fallado en HA: conservó la nueva raíz, retiró solo el manifiesto compacto
anterior (15.448 bytes) y no eliminó ni duplicó ningún objeto.

## Comprobación ML

El preparador multiversión consumió directamente la carpeta final compactada:

- V3 ventana fija: 374/417 elegibles;
- V3 retardo/evento: 2.618/2.919 elegibles;
- V4 ventana fija, bloques `core`, `extended_weather` y `climatic_balance`:
  374/417 elegibles;
- V4 retardo/evento, los mismos bloques: 2.618/2.919 elegibles.

La compactación no cambió esos resultados respecto a la generación reparada no
compactada.

## Operación pendiente

HA recibió con Rainmapper detenido los dos ficheros de
`ready-to-upload-root-fix`. La lectura posterior de `/share` verificó el hash
del manifiesto, las 46 particiones, 5.480.224 filas, 49.590.594 bytes activos y
`previous_generation_id: null`.

El runner manual posterior superó `archive pending before update` y publicó la
hija `20260823T004654212246Z-59a50ee60e80`, con la raíz corregida como
predecesora inmediata. Incorporó cuatro lotes frescos —AEMET, Meteocat,
Meteoclimatic y Wunderground— y dejó 46 particiones, 5.481.652 filas y
50.297.632 bytes activos. La resolución posterior con verificación completa de
hashes fue correcta. AEMET, Meteocat, Meteoclimatic y Wunderground completaron;
Wunderground resolvió mediante scraper cuatro respuestas API HTTP 204 y terminó
98/98 estaciones, sin fallos. Mapas y siete GeoJSON se publicaron correctamente.
El proceso acabó con código 0 en 5 min 50 s: pre-drain 3 s, actualización 2 min
24 s, post-drain 2 min 14 s y mapas 43 s, además de publicación. La reparación
y su validación operativa quedan cerradas.

Antes de repetir una reconstrucción masiva conviene corregir el límite de
fragmentos del escritor o añadir una fase de compactación transaccional. Este
defecto no invalida el contenido final ya compactado, pero sí hace ineficiente
la salida física directa del reparador.
