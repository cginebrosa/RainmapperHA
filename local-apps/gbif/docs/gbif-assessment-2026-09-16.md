# GBIF: volumen inicial y plan de evaluación para Rainmapper

Consulta: 16/09/2026, 19:54–19:58 UTC. Investigación de solo lectura;
sin descarga de ocurrencias, importación, entrenamiento ni cambios de producción.
Se han consultado las **tres especies solicitadas por el usuario**, no la lista
ampliada del handoff. Las cifras son registros indexados, no salidas independientes.

## Resultado y recomendación

**Merece un piloto acotado, sobre todo con Lactarius deliciosus; no hay evidencia
todavía de que mejore los modelos.** Catalunya aporta 482 registros brutos en
la ventana solicitada. Hay 129 con incertidumbre declarada de hasta 1 km, 47
con incertidumbre mayor y 306 sin ese dato. Estos últimos no se consideran
automáticamente ni precisos ni inválidos.

| Especie | Catalunya desde 19/06/2012 | Catalunya, cualquier fecha o sin fecha | España desde 19/06/2012 | Observaciones locales actuales de esa especie |
| --- | ---: | ---: | ---: | ---: |
| Boletus edulis | 84 | 225 | 752 | 61 |
| Amanita caesarea — ous de reig | 68 | 227 | 319 | 77 |
| Lactarius deliciosus | 330 | 735 | 1.130 | 58 |
| Total | 482 | 1.187 | 2.201 | 196 |

La última columna procede de `docker-data/mushroom-data/mushroom_observations.json`,
que contiene 477 registros en total. Es una comparación de volúmenes brutos;
no presupone igual calidad, elegibilidad, fechas ni independencia. El fichero
`mushroom-data/mushroom_observations.json` del worktree contiene 441, con 51/74/50
para estas especies. **No se ha contado ni sincronizado el fichero de HA real.**

## Cómo se han contado

Evidencia con respuestas agregadas, parámetros y URLs exactas:
[gbif-counts-2026-09-16.json](../data/gbif-counts-2026-09-16.json).
Todas las búsquedas de ocurrencias llevan `limit=0`; `results` está vacío.

- Región verificada: [GADM ESP.6_1 = Cataluña](https://api.gbif.org/v1/geocode/gadm/ESP.6_1).
- Intervalo cerrado `eventDate=2012-06-19,2026-09-16`, evitando fechas futuras.
- El rango abierto del handoff devuelve las mismas cifras.
- Sin filtro de dataset, licencia, tipo de registro o precisión en el recuento bruto.
- Species Match v2 devuelve los tres nombres como `SPECIES`, `ACCEPTED`, coincidencia
  `EXACT`, sin sinonimia: edulis `5954958`, caesarea `5240269`, deliciosus `5248629`.
- Las búsquedas por `scientificName` y por `taxonKey` coinciden: 84/68/330.
  `taxonKey` incluye sinónimos y taxones descendientes; no se han contado solo
  identificaciones cuyo texto original sea exactamente el binomio.

Consultas brutas:

- [Edulis, Catalunya y ventana temporal](https://api.gbif.org/v1/occurrence/search?taxonKey=5954958&gadmGid=ESP.6_1&eventDate=2012-06-19%2C2026-09-16&limit=0).
- [Caesarea, Catalunya y ventana temporal](https://api.gbif.org/v1/occurrence/search?taxonKey=5240269&gadmGid=ESP.6_1&eventDate=2012-06-19%2C2026-09-16&limit=0).
- [Deliciosus, Catalunya y ventana temporal](https://api.gbif.org/v1/occurrence/search?taxonKey=5248629&gadmGid=ESP.6_1&eventDate=2012-06-19%2C2026-09-16&limit=0).

**Límite geográfico:** GBIF asigna GADM a partir de coordenadas. Este recuento
no incluye automáticamente citas solo textuales de Catalunya sin georreferenciar.
Como control adicional, España + `stateProvince` repetido para Cataluña/Catalunya/
Catalonia/Barcelona/Girona/Lleida/Tarragona devuelve 88/73/335; todos con coordenadas.
No son conjuntos idénticos a GADM: no se deben sumar ni atribuir su diferencia a
una causa concreta sin examinar los registros. La discrepancia es pequeña y queda
pendiente de auditoría, no resuelta por preferir el número mayor.
Fuente: [procesamiento geográfico GBIF](https://techdocs.gbif.org/en/data-processing/).

## Procedencia: no se ha filtrado por FungaCAT

| Dataset | Edulis | Caesarea | Deliciosus | Total |
| --- | ---: | ---: | ---: | ---: |
| Observation.org | 41 | 32 | 232 | 305 |
| iNaturalist Research-grade Observations | 27 | 34 | 86 | 147 |
| SIM — registros de Joan Montón | 16 | 2 | 11 | 29 |
| FungaCAT | 0 | 0 | 1 | 1 |

Sin restricción temporal, FungaCAT aporta 103/148/278 en la región GADM.
No se han inspeccionado sus registros para separar fechas antiguas de fechas
ausentes o incompletas. La descripción del dataset indica compilación bibliográfica;
no es un registro exhaustivo de salidas de recolección.

Las licencias de las ocurrencias contadas son 416 CC BY-NC, 65 CC BY y 1 CC0.
No se ha excluido CC BY-NC. La importación futura debe conservar la licencia de
cada ocurrencia, la atribución y el dataset; no basta copiar la licencia general
del catálogo del publicador.

Fuentes: [Observation.org](https://api.gbif.org/v1/dataset/8a863029-f435-446a-821e-275f4f641165),
[iNaturalist](https://api.gbif.org/v1/dataset/50c9509d-22c7-4a22-a47d-8c48425ef4a7),
[SIM](https://api.gbif.org/v1/dataset/bf4ab07a-4d9b-4ee9-af03-d22651385dbc),
[FungaCAT](https://api.gbif.org/v1/dataset/8583f4f6-f762-11e1-a439-00145eb45e9a).

## Calidad disponible mediante conteos, no admisión automática

Los 482 conservan el recuento al exigir `hasCoordinate=true`,
`hasGeospatialIssue=false`, `occurrenceStatus=PRESENT`, `month=1,12`, `day=1,31`.
Esto acredita campos interpretados por GBIF, no una revisión del dato original,
la identificación ni que cada fecha corresponda inequívocamente a un único día.

| Especie | Filtros básicos | Incertidumbre ≤100 m | ≤500 m | ≤1.000 m | Incertidumbre no informada |
| --- | ---: | ---: | ---: | ---: | ---: |
| B. edulis | 84 | 9 | 18 | 34 | 43 |
| A. caesarea | 68 | 10 | 20 | 26 | 34 |
| L. deliciosus | 330 | 32 | 45 | 69 | 229 |
| Total | 482 | 51 | 83 | 129 | 306 |

Las columnas de umbral son acumulativas, no se suman. Son escenarios de sensibilidad,
no una regla científica de aceptación. Las cifras salen de la faceta completa de
incertidumbre; el umbral de 1.000 m se ha contrastado además mediante tres consultas
directas con `coordinateUncertaintyInMeters=0,1000`.
Los 129 siguen siendo candidatos: falta deduplicación, alcance espacial de los
modelos, revisión de fecha/origen y cobertura meteorológica por punto.

La faceta de tipo informa 477 `HUMAN_OBSERVATION`, 4 `PRESERVED_SPECIMEN` y 1
`OCCURRENCE`. No se han excluido ejemplares conservados. Todos los registros
figuran como `PRESENT`; el conjunto contado no aporta ausencias explícitas.

## Meteorología y contrato actual de Rainmapper

El `CURRENT.json` local apunta a la generación
`20260916T102940341741Z-f7077c0bfabb`. Su manifiesto declara datos de AEMET y
Meteocat desde **19/06/2012**, hasta 16/09/2026. Verificado leyendo metadatos,
sin reconstruir históricos. Esto no prueba cobertura completa de lluvia,
temperatura y humedad para cada punto y fecha de GBIF.

El lector `observation_weather_read_scope` utiliza ventanas previas de 120 días
(`rainmapper_core/mushroom_observation_context.py:31`, `:1533`). La fecha inicial
del histórico no convierte automáticamente las observaciones de ese mismo día
en entrenables: hay que verificar la ventana previa requerida por cada modelo,
las estaciones cercanas y las variables disponibles.

**Diferencia de objetivo:** el esquema exige `flush_abundance` y el objetivo operativo
se deriva del catálogo mediante `prediction_target` (`mushroom_observation_context.py:905`).
Una observación con pocos ejemplares puede ser presencia real y florada desfavorable.
GBIF `PRESENT` no informa por sí solo si una salida merece la pena. Tampoco
`individualCount`, cuando exista, implica abundancia comparable sin área/esfuerzo.

El catálogo local contiene `pending` con `prediction_favorable=0`, y el cargador
incorpora sus entradas (`mushroom_observation_context.py:868`). Por tanto, una
importación no debe usar `pending` como supuesto objetivo desconocido sin comprobar
la exclusión efectiva del entrenamiento. No asignar `normal`, `scarce` o `absent`
por conveniencia para superar la validación.

GBIF diferencia modelos de presencia, presencia/fondo y presencia/ausencia:
[documentación de métodos](https://docs.gbif.org/course-data-use/en/commonly-used-algorithms.html).
La ausencia de una cita no demuestra ausencia de setas ni una salida sin resultados.

## Plan propuesto, todavía sin implementar

1. **Auditoría pequeña de los registros candidatos.** Empezar por deliciosus y
   una muestra estratificada de las otras dos especies y de los principales datasets.
   Revisar fechas originales, coordenadas ocultadas/generalizadas, incertidumbre
   ausente, taxonomía, fotos o evidencia accesible, campos de abundancia/esfuerzo,
   duplicados y posibles discrepancias GADM/provincia. No resolver los 306 casos
   sin precisión mediante un valor inventado.
2. **Medir utilidad real antes de integrar.** Obtener el número de eventos
   independientes por especie, año, zona y proveedor; comprobar intersección con
   las áreas y el histórico meteorológico de Rainmapper, sin entrenar. Separar
   los criterios de precisión necesarios para meteorología de los de microhábitat.
3. **Importación trazable y reversible, cuando se acuerde.** Primero un fichero
   de candidatos separado; después integración en `mushroom_observations.json`
   preservando los datos del usuario. El esquema ya ofrece
   `source.type=imported_dataset`, `source.label`, `source.url` y `location.precision_m`.
   Proponer un bloque de procedencia estructurado para proveedor GBIF, `gbifID`,
   `occurrenceID`, dataset, licencia/atribución, nombres original y aceptado,
   incertidumbre, flags y lote/fecha de importación. Su persistencia en UI,
   exportación, reconstrucción y worker debe probarse; no se afirma que exista hoy.
   Deduplicar por identificadores y revisar duplicados entre datasets y frente a
   observaciones propias. No usar solo coordenada+especie como identidad única.
4. **Definir el objetivo antes de los tres entrenamientos.** Para comparar el
   IFF actual hace falta información compatible con favorabilidad. Si GBIF solo
   aporta presencia, no es válido convertir todo a favorable ni entrenar el
   clasificador binario actual con una sola clase. Las alternativas a decidir son:
   aprovechar únicamente registros con abundancia interpretable, usar GBIF como
   evidencia auxiliar o diseñar un experimento distinto de presencia/fondo.
   En este último, el fondo no son ausencias verificadas y el resultado no debe
   presentarse como mejora directa del IFF operativo.
5. **Comparación controlada, una vez compatible el objetivo.** Tres conjuntos
   propios / GBIF / combinación, con el mismo tratamiento de variables y presupuesto
   de ajuste. Separación de entrenamiento y evaluación por evento/duplicado y bloques
   de espacio y tiempo antes de ajustar modelos. Reservar el mismo conjunto de
   observaciones propias para evaluar los tres, fuera de todos los entrenamientos;
   acompañarlo con evaluación externa GBIF adecuada a su tipo de etiqueta. Comparar
   por especie, calibración y capacidad predictiva con incertidumbre; usar Brier/
   log-loss/PR-AUC solo cuando haya etiquetas binarias y ambas clases suficientes.
   Medir también el efecto del tamaño y del proveedor, evitando que la mejora sea
   solo repetición de una misma salida. Sin promoción automática a HA real.

No se fija ahora un mínimo universal de muestras ni se promete una mejora por
añadir datos. Mi recomendación es autorizar primero el piloto de calidad y
compatibilidad de etiquetas; 482 registros justifican explorarlo, no una
integración completa a ciegas.

## Observaciones sobre el handoff

La estrategia de usar Species Match, GADM y `limit=0` es válida y se ha contrastado
con la API actual. El control de España de edulis reproduce exactamente 752.
El texto dice «siete especies», pero una lista contiene nueve; esta investigación
se limita a las tres de la petición vigente. No se ha investigado ni mezclado
vinosus/sanguifluus. El documento original y el trabajo GBIF previo se conservan.

No se ha accedido a HA real ni modificado HA local, destinos del worker, datos
operativos, modelos o GIS. Estos dos archivos nuevos son investigación local
sin publicar; la revisión GIS continúa aplazada.
