# Inventario preliminar de HA local — 03/10/2026

Tras confirmar el usuario la descarga a local, se consultaron archivos, metadatos
e índice de entrenamiento en lectura. Este inventario inicia la comprobación de
viabilidad. **No se ejecutaron predicciones, reconstrucciones, entrenamientos,
precálculos ni cambios operativos.** Tampoco se consultó HA real.

## Fuente y alcance

`docker inspect --format '{{json .Mounts}}' rainmapper-local-rainmapper-ha-ui-1`
confirmó los montajes de `docker-data/` en `/share/rainmapper` y
`docker-media/rainmapper/` en `/media/rainmapper`.

Se usaron `docker-data/mushroom-data/mushroom_observations.json` (544 observaciones)
y `mushroom_known_sites.json` (72 áreas y 113 microáreas/setales). No se mezclaron
con las copias antiguas de observaciones de la raíz ni de `mushroom-data/`.
La procedencia desde HA real está confirmada por el usuario; no se verificó paridad
remota ni cobertura meteorológica específica de cada observación.

## Observaciones de las dos especies

Se aplicó el catálogo local `mushroom_reference_catalogs.json`: `scarce` y categorías
superiores son favorables; `very_scarce` y `absent`, desfavorables. Ninguna fila de
estas dos especies tiene abundancia pendiente.

| Medida | Boletus aereus | Amanita caesarea |
| --- | ---: | ---: |
| Observaciones | 86 | 98 |
| Favorables según el catálogo | 53 | 63 |
| Desfavorables según el catálogo | 33 | 35 |
| De ellas, ausencia (`absent`) | 28 | 32 |
| De ellas, muy escasas (`very_scarce`) | 5 | 3 |
| Setales distintos | 22 | 36 |
| Áreas distintas | 10 | 27 |
| Grupos técnicos de 14 días | 40 | 57 |
| Grupos con alguna observación desfavorable | 20 | 21 |
| Grupos con alguna observación favorable | 28 | 40 |
| Grupos con ambos resultados | 8 | 4 |
| Máximo de filas en un grupo | 8 | 8 |
| Rango de fechas observadas | 04/10/2016–26/09/2026 | 12/09/2015–03/10/2026 |

Se utilizó `observation_validation_groups` de
[mushroom_ml_biology_v3.py](../../../rainmapper_core/mushroom_ml_biology_v3.py),
desde la línea 1578, con `max_duration_days=14` y el mapa microárea–área local.
Agrupa por especie y área, con duración máxima desde la primera observación.
**Son grupos técnicos, no una acreditación de independencia estadística.** Los
grupos mixtos están en ambos recuentos; no sumarlos dos veces. También puede haber
dependencia entre especies de una misma salida.

Las 184 observaciones figuran como `validation_status=valid` y
`calibration_use=include`; todas tienen un setal resoluble. No hay IDs duplicados
en las 544 observaciones ni coincidencias especie–setal–fecha en estas 184 filas.
Estas comprobaciones estructurales no validan por sí solas la calidad de las etiquetas.

**Criterio confirmado por el usuario el 03/10/2026:** las 16 observaciones de
caesarea procedentes de GBIF y etiquetadas `normal` son favorables con el mismo
criterio que cualquier otra observación `normal`. Se mantienen incluidas en los
63 favorables, sin exclusión, penalización ni validación adicional por su origen
GBIF. Este punto queda resuelto. Aereus no tiene observaciones de origen GBIF.

## Solapamiento con entrenamiento local

El registro local enlaza las cinco versiones instaladas al lote
`operational_20260928T005344Z`. Su índice `training-observations.sqlite` contiene
792 claves de modelos, 226 conjuntos completos y 491 IDs distintos de observación.
Su tamaño y SHA-256 coinciden con la referencia del manifiesto del lote.

SQLite se abrió con `mode=ro`. Se cruzaron los IDs actuales con la unión de los
conjuntos de modelos de cada especie y los compartidos (`all_species`).

| Cruce por ID | Aereus | Caesarea |
| --- | ---: | ---: |
| Presente en al menos un modelo pertinente | 85 | 97 |
| Ausente de todos los modelos pertinentes | 1 | 1 |

La fila ausente de aereus está fechada el 02/10/2023 y etiquetada `very_abundant`;
la de caesarea, el 03/10/2026 y `scarce`. **Ambas son favorables.** Ausencia del
índice no demuestra independencia del catálogo, del diseño o de otras observaciones
relacionadas. Presencia significa uso del ID en algún modelo, no en todos, ni
identidad del contenido después de posibles ediciones. El cruce corresponde al lote
local; no certifica qué artefactos usa ahora HA real.

Esta reserva de IDs ausentes no permite evaluar el comportamiento ante salidas
realmente desfavorables. El histórico contiene ambos resultados y permite estudiar
la viabilidad de nuevos ajustes, sujeto a calidad y separación del procedimiento.

## Meteorología y artefactos derivados

`docker-data/Data/weather-history/CURRENT.json` apunta a la generación
`20261003T150452920192Z-06045b1c3b6e`. Se verificó el SHA-256 de su manifiesto:
`d7c9a5d422d6b3b986878e09ea5d70ad17857ce9e39be80d18dd5160dbdeec43`.
Declara 46 particiones y 5.564.636 filas. Todas las particiones y el catálogo
referidos existen y sus tamaños coinciden; no se recalcularon todos sus hashes.

| Fuente | Fecha mínima declarada | Fecha máxima declarada |
| --- | --- | --- |
| AEMET | 19/06/2012 | 03/10/2026 |
| Meteocat | 19/06/2012 | 03/10/2026 |
| Meteoclimatic | 28/09/2023 | 03/10/2026 |
| Wunderground | 24/10/2015 | 03/10/2026 |

Esta cobertura temporal global no garantiza estaciones adecuadas, continuidad o
variables suficientes por setal y ventana. No se ha comprobado disponibilidad de
previsiones meteorológicas archivadas a fecha de emisión.

En `docker-media/rainmapper/results/artifacts/`, los archivos
`mushroom_observations_weather_features.json` y `mushroom_observation_features_v0.json`
declaran generación el 28/09/2026 y contienen 542 filas cada uno. Ninguno contiene
los dos IDs ausentes del entrenamiento. El usuario confirma que el último
entrenamiento se realizó el 28/09/2026: **la fecha de estos artefactos es la
esperada y no constituye una incidencia ni un bloqueo**. Se distingue el conjunto
de aquel entrenamiento de las entradas descargadas después. No hace falta repetir
el entrenamiento por esa diferencia de fechas; cualquier preparación experimental
se decidirá según las particiones y datos que requiera el estudio. No se reconstruyeron.

## Huellas de las entradas observadas

SHA-256 de archivos bajo `docker-data/mushroom-data/`; las huellas de observaciones
y setales permanecieron iguales al terminar las consultas:

| Archivo | SHA-256 |
| --- | --- |
| `mushroom_observations.json` | `2a7d9a08b79387c11935835ae0b8b9e5694b185b07673b04ca114c85227bc5be` |
| `mushroom_known_sites.json` | `f33673a28452d452105df8f9d7c65115d2719abae035bcbcca357c3479c31162` |
| `mushroom_reference_catalogs.json` | `470df4bad9174974f7c69c96023aeed484b5ba1f65a30a70656e9e0b3fc0b9fe` |
| `mushroom_ml_version_registry.json` | `8a1bf9136163791aa97d0bc44bbcc2fbb0bc74d7c5dcd7a3ac515c248d82b28e` |

## Dictamen preliminar y siguiente paso

Hay material histórico para diseñar una comparación retrospectiva acotada; todavía
no se ha demostrado su suficiencia para una conclusión operativa. Las dos filas
ausentes del entrenamiento, ambas favorables, no constituyen una prueba final
adecuada del equilibrio de errores que interesa al usuario.

Antes de calcular predicciones: comprobar cobertura meteorológica por caso,
revisar la separación de episodios y fijar particiones y presupuesto. La clasificación
de los GBIF `normal` y la fecha del último entrenamiento están aclaradas; no quedan
como pendientes. Después se podrá concretar qué ajustes experimentales hacen falta.
Se conservan los modelos activos, los datos privados y el destino del worker.
