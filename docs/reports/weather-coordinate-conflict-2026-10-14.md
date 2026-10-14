# Runner: conflicto de coordenadas de Roda de Ter, 14/10/2026

## Alcance

Diagnóstico de lectura sobre `docker-data/Data`, que el usuario identifica como
la última copia de HA real. `docker inspect` confirma que HA local monta
`docker-data` en `/share/rainmapper`. No se ha accedido a HA real, ejecutado el
runner, reparado datos, ampliado límites ni iniciado trabajos de Gemma.

## Evidencia comprobada

Estación: `meteoclimatic / ESCAT0800000008510E`.

| Fuente | Nombre / municipio | Latitud | Longitud | Altitud |
| --- | --- | ---: | ---: | ---: |
| Catálogo activo local | Roda de Ter | 41.99 | 2.32 | 465 |
| Registro de estaciones | Roda de Ter / Amiens-2, Somme | 49.99 | 2.32 | 121 |
| Pendiente, fecha 20261013 | Roda de Ter / Amiens-2, Somme | 49.99 | 2.32 | 121 |
| RSS consultado el 14/10 | Roda de Ter (Barcelona) | 49.99 | 2.32 | No contrastada |

- Registro: `docker-data/Data/estacions_meteoclimatic.csv`, línea 294.
- `CURRENT.json`: generación `20261013T150406166470Z-04bc1cba7ac0`.
- Catálogo: `weather-history/catalogs/stations-a46bdcb56d4de9819d71cf829b241bc44755af8d165904fa4e1c5b6cd75d99b6.parquet`.
  La fila de esta estación tiene `metadata_date=20241117`,
  `first_date=20240919`, `last_date=20241117`.
- Pendiente: `weather-history/pending/source=meteoclimatic/0be8af45e7ea03b22dfe33136132cf4791d8cec2f15ccc8382ec3e5a519f7d12.parquet`.
  Son 6990 filas en el lote; la lectura filtrada devuelve una fila de esta
  estación, del 13/10/2026 a las 19:38:27, con precipitación 0 mm.
- La misma coordenada aparece en `Meteoclimatic.csv:213`,
  `Meteoclimatic_incremental.csv:26038` y
  `Meteoclimatic_observations_incremental.csv:12983`.
- RSS público: https://www.meteoclimatic.net/feed/rss/ESCAT0800000008510E.
  Leído con curl; el visor web no pudo abrirlo. Título
  `Roda de Ter (Barcelona)`, `georss:point=49.99 2.32`,
  `pubDate=Wed, 14 Oct 2026 20:08:57 +0000`.
  Captura: `/private/tmp/rainmapper-meteoclimatic-ESCAT0800000008510E-20261014.xml`.

## Explicación y límites

La función `_haversine_km` del código actual devuelve **889.5606418682632 km**
entre ambos pares: redondea a los 889.561 km del error del usuario.
`inside_coordinate_regions` devuelve `False` para el destino. No existe
override `docker-data/Data/weather_coordinate_policy.json` en la copia examinada.

`weather_history_writer.py:558` comprueba el salto; la excepción territorial
requiere fecha no anterior y destino dentro de la región permitida. La latitud
49.99 queda fuera de la envolvente peninsular (norte 44.0). El error se produce
antes de publicar el nuevo `CURRENT.json` (línea 774). Sí se pueden haber escrito
particiones aún no activadas antes de llegar a esa validación; no se ha hecho
un barrido ni una limpieza de esos objetos.

`weather_history_archive.py:70` llama al archivador antes de aplicar los
pendientes al CSV y confirmarlos. Por tanto, arreglar sólo el registro no corrige
el lote ya pendiente y no desbloquea por sí mismo este paso previo del runner.

`rainmapper.py:1837` consulta municipio, provincia y altitud mediante
`get_googlemaps` cuando cambian las coordenadas. Esto explica la derivación de
Amiens-2/Somme a partir de 49.99, 2.32; no demuestra un traslado de la estación.
La publicación actual del proveedor confirma que el valor 49.99 llega desde la
fuente, no que esa sea la ubicación física correcta.

**Inferencia:** es muy probable un error `49.99` por `41.99` en la latitud del
proveedor, coherente con el nombre Roda de Ter (Barcelona) y el catálogo anterior.
No se ha verificado la ubicación física con el propietario de la estación.

## Corrección acordada después del diagnóstico

El usuario eligió un archivo de excepciones editable:
`/share/rainmapper/meteoclimatic-fixed-coordinates.txt`, junto a `stations.txt`
y `status.txt`. Una línea activa fija código, latitud y longitud; `#` permite
desactivarla. El fichero local para subir está en
`docker-data/meteoclimatic-fixed-coordinates.txt`; en la raíz del repositorio
sólo se distribuye `meteoclimatic-fixed-coordinates.example.txt`, con el ejemplo
comentado. No colocar el archivo activo en la raíz del repositorio ni en `Data/`.

La entrada preparada es `ESCAT0800000008510E 41.99 2.32`. El usuario confirmó
el 14/10 que ya había subido el archivo a HA real; Codex no ha accedido a HA real
para verificarlo. Esto no confirma que esté instalado el parche que lo utiliza.

Implementación aislada de los cambios MCP/Gemma en la rama
`fix/meteoclimatic-fixed-coordinates`, worktree
`/private/tmp/rainmapper-ha-coordinate-patch-20261014`, candidato HA `0.2.338`.
La corrección cubre próximas descargas, pendientes, catálogo y recuperación del
CSV tras interrupciones, conservando mediciones. La copia recibida del usuario
se conserva; la aceptación funcional usa una segunda copia temporal.

[Guía de funcionamiento y operación](../meteoclimatic-fixed-coordinates-es.md).
Estado de aceptación, publicación e instalación en
[active-context.md](../active-context.md). Gemma sigue pausado.

## Integridad de las fuentes examinadas (SHA-256)

- Registro CSV: `32902d6a09f2cbc35e695a36c685def577ae9d15cbe7e7f3b9d71c9c7250cbef`.
- CURRENT: `1fe2b305ec1c96363cf77c607b8aece6f2c87fa95a69b54cdb72352dba74004d`.
- Catálogo: `a46bdcb56d4de9819d71cf829b241bc44755af8d165904fa4e1c5b6cd75d99b6`.
- Pendiente: `d7757c66b4f65ae2620451b054051aba983cd096da1d570b1936482cc4a20631`
  (coincide con el manifiesto del lote).
- RSS: `070f8ffa492d25023d826e6331769df4b722e13ab958d5336b4db2061f24bfa4`.
