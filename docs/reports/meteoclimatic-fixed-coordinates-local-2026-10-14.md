# Coordenadas Meteoclimatic: validación local del parche 0.2.338

## Alcance y aislamiento

Candidato preparado desde `8f3998e9` (HA 0.2.337), rama
`fix/meteoclimatic-fixed-coordinates`, worktree
`/private/tmp/rainmapper-ha-coordinate-patch-20261014`. Excluye los cambios MCP/Gemma
pendientes. La misma corrección se incorporó después al checkout principal
conservando MCP para preparar la prueba manual en el HA local habitual.

Durante esta aceptación no se accedió a HA real. La publicación posterior está
en el [informe de release](release-ha-0.2.338-2026-10-14.md). El usuario confirmó que ya
subió el archivo activo; la instalación del parche y su ejecución real siguen
pendientes. [Guía](../meteoclimatic-fixed-coordinates-es.md) y
[diagnóstico original](weather-coordinate-conflict-2026-10-14.md).

## Pruebas terminadas

- **38 pruebas dirigidas correctas**: excepciones, escritor del histórico y CSV
  vivo; repetidas con éxito al incorporar el parche al checkout principal.
- Smoke del candidato: **2146 pruebas, 55 omitidas**, resultado correcto, más
  sintaxis, versiones y fixtures de GeoJSON, históricos y backup. Primera pasada:
  siete errores de permisos de sockets/procesos del sandbox; repetición con
  esos permisos correcta.
- Imagen `rainmapperha:local-coordinate-patch`, contenedor
  `rainmapper-ha-coordinate-patch-acceptance`, HTTP 200, versión efectiva 0.2.338;
  nueve archivos ejecutables/plantilla comprobados por SHA-256 contra el candidato.
- Bloque exacto de `/run.sh`: crea plantilla cuando falta y conserva el archivo
  del operador si existe. Primera auditoría buscó el script en `/app/run.sh`;
  corregida la ruta del comprobador, terminó sin repetir el archivado ni modificar
  el código del producto.

## Pendientes reales sobre copia aislada

Copia en `/private/tmp/rainmapper-coordinate-validation-20261014/share/Data`,
scheduler y coordinador worker desactivados. Sólo se ejecutó
`archive_and_close_pending`; no runner completo, descargas, entrenamiento ni precálculo.

| Comprobación | Resultado |
| --- | --- |
| Sin excepción | Reproducido exactamente el salto de 889.561 km de `ESCAT0800000008510E` |
| Con `ESCAT0800000008510E 41.99 2.32` | Cuatro lotes archivados y cerrados en 19,953 s locales |
| Datos pendientes verificados | 16.497 filas: AEMET 6669, Meteocat 1501, Meteoclimatic 6990, Wunderground 1337 |
| Histórico ajeno a los lotes | 384.344 filas de particiones afectadas conservadas exactamente |
| Otras particiones | 42 descriptores y hashes intactos |
| Catálogo y CSV incremental de Roda de Ter | 41.99, 2.32, altitud 465 m |
| Mediciones de la estación | Lluvia 0 mm, máxima 24,9 °C y mínima 16,7 °C conservadas |
| Metadatos de Amiens | Municipio/provincia vacíos hasta enriquecimiento normal |
| Pendientes después del cierre | Cero en la copia |
| Política persistida de recuperación | 184 bytes |
| Originales en `docker-data/Data` | 69 archivos con huellas conservadas tras la prueba aislada |

La generación resultante pasó verificación de integridad. El TXT activo se
conservó. La retención normal de CSV vivos y generaciones se ejecutó únicamente
en la copia temporal; los datos que salen de la ventana CSV permanecen en el
histórico canónico. No se realizó limpieza manual sobre originales.

Generación anterior: `20261013T150406166470Z-04bc1cba7ac0`.
Generación de aceptación: `20261014T205534935721Z-07fc99a4d94b`.

El enriquecimiento de nuevas descargas se comprobó primero con geocodificador
simulado; la ejecución manual siguiente comprobó además la descarga real.
Los 19,953 s no son una medición en RPi4 ni del runner completo.

## Evidencia y siguientes pasos

Recibos, hashes, scripts de comprobación y logs:
`local/evidence/meteoclimatic-fixed-coordinates-20261014/` (privado, fuera de Git).

- HA local habitual (`127.0.0.1:8101`) **preparado**: imagen reconstruida, servicio
  recreado, HTTP 200, nueve huellas idénticas al candidato y excepción activa.
  Conserva sus cuatro lotes pendientes para la prueba manual, scheduler desactivado
  y configuración/MCP existentes. Worker y MCP conservan ID, imagen e inicio.
  Privados y 69 archivos originales del Data conservados tras la recreación.
  El contenedor temporal de aceptación queda parado hasta retirarlo.
- Runner local ejecutado por el usuario y revisado, según el apartado siguiente.
  Resultado aceptado por el usuario; publicación verificada en el informe de release.
- El usuario instala la release y ejecuta el runner en HA real.
- **Limpieza autorizada por el usuario:** cuando local y HA real estén comprobados,
  borrar `rainmapper-ha-coordinate-patch-acceptance`. Esperar su confirmación de
  HA real; la subida del TXT no basta. Mantener la evidencia de la validación.

Gemma continúa pausado.


## Prueba manual del usuario: actualización completa del 14/10

El usuario lanzó `all (web)` a las 23:00:37 (Europe/Madrid). Terminó a las
23:02:13 con **exit code 0**, duración **1m36s**. Los dos pasos de archivado
terminaron en 21 s cada uno y el log registra la sustitución de coordenadas tanto
antes de actualizar como durante la nueva descarga Meteoclimatic.

Lectura posterior de CSV incrementales y particiones activas de 2026, sin
relanzar tareas: fechas `20261014`, claves de estaciones sin duplicados diarios
y valores coincidentes entre ambos formatos (tolerancia numérica de 1e-12).

| Fuente | Estaciones con registro de hoy | Con precipitación informada | Con alguna temperatura informada |
| --- | ---: | ---: | ---: |
| AEMET | 835 | 835 | 833 |
| Meteocat | 187 | 186 | 183 |
| Meteoclimatic | 846 | 846 | 846 |
| Wunderground | 100 | 99 | 97 |

Las cuatro fuentes terminaron con estado `OK`, pero ese estado no demuestra que
respondan todas sus estaciones. **Wunderground es parcial:** cinco fallos
(`IGUILS1`, `IBAG57`, `IFUENT4`, `IMONTF44`, `ILAVAN3`) y ocho respuestas antiguas
(`IAVI14`, `IBELLV25`, `IISONA6`, `ILASEL14`, `IMERAN22`, `IMOLL6`, `IOSSJA12`,
`ISANTL13`), persistentes después de reintentos. No se hicieron reintentos nuevos
como parte de esta auditoría. Las otras fuentes también contienen estaciones
históricas sin registro de hoy; no se presume que todas sigan activas.

Roda de Ter tiene lectura nueva a las **22:38:58**, coordenadas **41.99, 2.32**,
altitud **465 m**, municipio devuelto **Les Masies de Roda**, provincia Barcelona.
Lluvia 0 mm, máxima 30,4 °C, mínima 14,7 °C. El registro de estaciones y ambos
históricos contrastados conservan el punto corregido.

Generación activa después del runner:
`20261014T210149631230Z-e1096b26291c`; manifiesto y hashes de particiones de 2026
verificados; **cero pendientes**. Las huellas originales del apartado anterior
corresponden al momento previo a esta ejecución autorizada por el usuario.

Fuentes: `docker-data/last_run.log:1`, `:3`, `:102`, `:220`;
`docker-data/Data/source_status.json`; CSV incrementales de las cuatro fuentes;
`docker-data/Data/weather-history/CURRENT.json` y su manifiesto/particiones;
`docker-data/Data/estacions_meteoclimatic.csv`. Recibo privado con conteos,
coincidencias y huellas: `local/evidence/meteoclimatic-fixed-coordinates-20261014/manual-run-weather-check.json`.

La prueba local del parche es satisfactoria. **HA real continúa sin validar**;
la instalación y prueba real corresponden al usuario. El contenedor temporal
está parado y su eliminación sigue condicionada a esa confirmación.
