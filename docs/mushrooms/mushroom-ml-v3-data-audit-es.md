# Auditoría de datos previa al siguiente contrato ML

Estado: **CERRADA PARA DISEÑO** el 2026-08-11. Esta auditoría ejecuta los pasos
1–3 de la revisión conceptual: fija qué se intenta predecir, mide la muestra
real disponible y separa señal biológica de control de calidad. No entrena ni
promociona modelos y no modifica HA.

La especificación de código derivada de estos resultados está en
`mushroom-ml-v3-implementation-spec-es.md`.

## Reconciliación posterior a la canonicalización — 2026-08-13

La implementación del contrato `area_microarea_evidence_v1` sobre las mismas
399 observaciones produce 348 unidades canónicas
`(especie, microárea, fecha)` y 278 episodios `(especie, área, fecha)`:

- 188 favorables, 87 desfavorables y 3 desconocidos;
- al excluir los 3 targets desconocidos del entrenamiento quedan exactamente
  los 275 episodios entrenables citados en esta auditoría;
- la tabla histórica contó 11 grupos mixtos porque agrupó filas originales
  directamente a área. Dos eran en realidad conflictos duplicados dentro de
  una única microárea (`amanita_caesarea/llambilles_arriba/2024-11-20` y
  `boletus_aereus/llambilles_medio/2024-11-20`);
- después de canonicalizar primero cada microárea, esos dos permanecen como
  `target_conflict=true`, pero no aparentan ser dos microáreas distintas. Quedan
  9 episodios realmente mixtos entre microáreas.

Por tanto, 275/11 y 278/9 no describen datasets distintos ni pérdida de datos:
el primer par era una vista pre-canónica entrenable y el segundo es la vista
auditable completa. Los recuentos nuevos reemplazan los anteriores para
Biology V3, manteniéndolos aquí para explicar la transición.

## Fuentes auditadas

Se comparó en modo lectura la fuente de producción de HA con la copia de juego
ya existente en `docker-data/mushroom-data`. Observaciones, catálogos, sitios y
reconstrucción GIS eran idénticos, por lo que no se creó otra copia ni se
sobrescribió el artefacto local de features, que era más reciente que el de HA.

| Fuente local | SHA-256 |
|---|---|
| `mushroom_observations.json` | `82e8995757354c74d5d3e5583da2b9157956c49fe92c4957b03caa0228aade2c` |
| `mushroom_reference_catalogs.json` | `849a32954345f5cc76074602922a3bc98d7333961ba12d5c4cec248457adca86` |
| `mushroom_known_sites.json` | `ef9363a1ae3c37cdb8ed72109e925ddd7f2e508cb06e4ac35563b9ac530d2ac7` |
| `mushroom_gis_observation_reconstruction.json` | `efc8597996e4f688cb2121f66787710b9980f35573dcd4d703159dbae10e9a5a` |
| `mushroom_observation_features_v0.json` local reconstruido | `e5f24d8c5acfe5da013e39b7e7eae4a3c590d310537eedc14a8f661fadab05f3` |

El corpus contiene 399 observaciones. De ellas, 350 tienen
`calibration_use=include`; las 44 `pending` están en revisión, al igual que
cinco observaciones adicionales. Tras aplicar validez, uso para calibración,
target conocido, microárea y agregación a área/fecha quedan 275 episodios.

## Qué significa el target

La pregunta operativa no es «¿apareció al menos una seta?», sino:

```text
¿Las condiciones de especie y área justificaban realizar una salida en T?
```

El target individual queda fijado así:

| Abundancia observada | Target de salida |
|---|---|
| `exceptional`, `very_abundant`, `abundant`, `normal`, `scarce` | favorable |
| `very_scarce`, `absent` | desfavorable |
| `pending`, ausente, no reconocida o `calibration_use != include` | desconocido |

`very_scarce` significa que hubo presencia, pero no una salida suficientemente
interesante. Es por tanto un negativo **operativo**, no una afirmación de
ausencia biológica. Un día no visitado y una especie no buscada continúan siendo
desconocidos; no se fabrican negativos.

La muestra está condicionada por la decisión previa del observador: normalmente
se sale cuando ya parece que puede haber setas. Por tanto, incluso un modelo
correcto estima utilidad **entre salidas seleccionadas**, no la probabilidad
incondicional de cualquier especie, área y día de Catalunya.

El catálogo actual todavía asigna `prediction_favorable=0` a `pending`. No ha
contaminado la muestra auditada porque las 44 observaciones pendientes tienen
`calibration_use=review`, pero es una dependencia frágil: el siguiente contrato
debe forzar `pending` a desconocido antes de comprobar la clase.

El mapping de abundancia usado por v2 tiene hash
`9ee2f5f2df388236d879cf0ba937f50e9b0f33ef9999978c2e6680cc774911eb`.
Los bundles v2 se congelan con esa referencia; el sucesor declarará otro
`target_contract_id`.

## Unidad de observación y agregación actual

La fila autoritativa identifica especie, microárea y fecha. El benchmark actual
la reduce a `(species_id, area_id, observed_at)` y considera favorable el área
si **cualquier** microárea fue favorable. Para las variables toma la fila con
menos `weather_gaps`.

La semántica «algún lugar del área justificó la salida» es compatible con el
target operativo, pero la implementación pierde información:

- confunde número de filas con número de microáreas comprobadas;
- no resuelve duplicados de una misma microárea y fecha;
- no conserva cuántas microáreas fueron favorables o desfavorables;
- una salida mixta se convierte en un positivo limpio;
- la meteorología del episodio depende de qué fila tenga menos avisos.

La vista pre-canónica detectó 11 grupos área/fecha mixtos; tras la reconciliación
anterior, Biology V3 conserva 9 mixtos reales entre microáreas y 2 conflictos
internos de microárea:

| Especie | Grupos mixtos |
|---|---:|
| Ou de reig (`amanita_caesarea`) | 2 |
| Aereus (`boletus_aereus`) | 4 |
| Pinícola (`boletus_pinophilus`) | 3 |
| Rebozuelo (`cantharellus_cibarius_sl`) | 1 |
| Marçot (`hygrophorus_marzuolus`) | 1 |

Ejemplos relevantes son Pinícola/Guils el 2025-06-18, 2026-07-03 y
2026-07-10: una microárea favorable coexistió con dos o más microáreas
desfavorables. El target de área puede seguir siendo favorable, pero el episodio
debe llevar `mixed_target=true` y conservar el recuento real; no debe aparentar
que toda el área respondió igual.

## Tamaño y equilibrio de la muestra

`Episodios` son los grupos área/fecha actuales. `Clústeres 7d` agrupa fechas
consecutivas de la misma especie y área separadas por siete días o menos; sirve
para mostrar que varias filas pueden pertenecer a una misma florada, no para
crear todavía otra partición. `Meteo utilizable` es el proxy reproducido en
esta auditoría: exige 19/21 y 81/90 días de lluvia, altitud y variables
meteorológicas candidatas completas. El artefacto se reconstruyó con el selector
vigente, que además exige 19/21 días de temperatura y humedad; v3 deberá
materializar esos dos recuentos para verificarlos directamente. Es un recuento
conservador sobre la estación ya materializada, no el máximo recuperable tras
volver a ejecutar el fallback para el corte de cada contrato.

| Especie | Episodios F/D | Clústeres 7d | Meteo utilizable F/D |
|---|---:|---:|---:|
| Ou de reig | 49 — 26/23 | 35 | 28 — 14/14 |
| Aereus | 50 — 33/17 | 35 | 30 — 21/9 |
| Edulis | 26 — 21/5 | 23 | 6 — 2/4 |
| Pinícola | 37 — 24/13 | 31 | 15 — 8/7 |
| Rebozuelo | 9 — 4/5 | 9 | 5 — 2/3 |
| Camagroc | 3 — 3/0 | 3 | 1 — 1/0 |
| Trompeta negra | 1 — 1/0 | 1 | 1 — 1/0 |
| Llanega negra | 10 — 7/3 | 7 | 3 — 2/1 |
| Marçot | 20 — 18/2 | 15 | 8 — 8/0 |
| Rovelló | 40 — 34/6 | 34 | 11 — 8/3 |
| Lactarius salmonicolor/quieticolor | 0 | 0 | 0 |
| Lactarius sanguifluus | 3 — 3/0 | 2 | 0 |
| Lactarius vinosus | 1 — 1/0 | 1 | 1 — 1/0 |
| Macrolepiota procera | 1 — 1/0 | 1 | 0 |
| Múrgola negra | 17 — 4/13 | 12 | 12 — 2/10 |
| Russula virescens | 4 — 4/0 | 4 | 0 |
| Tricholoma terreum | 4 — 4/0 | 4 | 1 — 1/0 |

Conclusiones de suficiencia:

- Ou de reig, Aereus y Pinícola son las únicas especies con al menos diez
  ejemplos por clase antes del filtro meteorológico. Después del filtro,
  Pinícola queda en 8/7 y Aereus en 21/9.
- Edulis no tiene 26 ejemplos meteorológicos: tiene seis utilizables, solo dos
  favorables. Un 100% consecutivo no puede interpretarse como evidencia fuerte.
- Rovelló, Marçot, Llanega, Rebozuelo y Múrgola solo permiten exploración o
  modelos compartidos; no justifican un modelo independiente complejo.
- Las especies de una sola clase no permiten clasificación supervisada por
  especie. Deben abstenerse o utilizar en el futuro un modelo compartido con
  efectos de especie, nunca una clase sintética.
- Las particiones 70/30 no crean independencia biológica. Las floradas
  observadas en días próximos deben poder agruparse en validación para medir la
  sensibilidad a episodios repetidos.

Estas categorías son diagnósticas, no un umbral biológico hardcoded. El bundle
debe publicar sus recuentos y el Predictor debe distinguir «sin datos»,
«exploratorio» y «validación independiente posible».

## Cobertura meteorológica

En `fixed_gap_7d_altitude_v2`, 127 de 275 episodios (46,2%) carecen de cada
banda de lluvia y 128 (46,5%) carecen de las temperaturas corregidas. La
imputación por mediana permite ajustar esos episodios como si contuvieran una
meteorología típica; con esta tasa de ausencia, la imputación deja de ser una
excepción y puede dominar el modelo.

La caída no significa que el fallback a otra estación estuviera desactivado:

- los 127 episodios sin estación son exactamente todos los episodios de
  2012–2022; todos tienen alguna estación catalogada dentro de 15 km, pero
  ninguna alcanza 81 de los 90 días de lluvia anteriores a la fecha histórica;
- el Parquet completo empieza en 2016, pero eso no implica que las estaciones
  cercanas a cada área tengan una serie local continua. En los episodios
  antiguos las mejores candidatas próximas siguen teniendo históricos
  fragmentarios, por lo que el selector agota el fallback sin encontrar una
  estación elegible;
- los 148 episodios de 2023–2026 sí tienen estación y series materializadas de
  120 días.

La auditoría detecta además una desalineación recuperable. El selector vigente
califica la estación en `T` y cuenta lluvia bruta no nula, mientras que
`fixed_gap_7d` consume el corte `T-7` después de suprimir lecturas sospechosas.
Con el snapshot auditado, 25 de los 148 episodios recientes dejan de superar el
gate al aplicar el contrato real en `T-7`; 18 de ellos sí disponen de otra
estación elegible dentro de 15 km si el fallback se vuelve a ejecutar en ese
corte y sobre lluvia ya depurada. Los siete restantes no tienen alternativa
utilizable. Un episodio adicional, Pinícola/Ordino de 2026-06-13, pierde las
temperaturas corregidas porque falta la altitud representativa del área, no por
falta de estación meteorológica.

Con ese proxy y el conjunto completo de candidatas quedan 122/275 episodios
para el corte fijo. En `lag_event_altitude_v2` quedan entre 122 y 125 según
horizonte. Es la reproducción del artefacto actual, no el resultado objetivo
del selector corregido: el fallback sensible al corte debe recuperar 18
episodios del corte fijo y elevar el recuento al menos a 140 con estos mismos
datos, sin inventar meteorología para los 127 históricos. El sucesor no debe
ocultar ninguna de las dos cifras: entrenar con 275 filas y medianas no equivale
a tener 275 episodios meteorológicos.

### Ausencia local frente a histórico recuperable

Los 127 episodios históricos no demuestran que la meteorología original no
exista. Demuestran únicamente que **no está materializada con cobertura
utilizable en el Parquet auditado**. El contenido local por fuente es:

| Fuente | Intervalo presente en el Parquet auditado | Observación |
|---|---|---|
| Meteocat | 2016-12-20 — 2026-08-10 | Es la única fuente local que retrocede antes de 2023, pero no aporta series próximas continuas suficientes para los episodios 2012–2022. |
| Meteoclimatic | 2023-09-28 — 2026-08-11 | No cubre los años históricos afectados. |
| Wunderground | 2023-08-01 — 2026-08-11 | No se ha ejecutado un backfill histórico completo y una PWS solo puede aportar fechas en las que ya existía y publicaba. |
| AEMET | 2026-05-25 — 2026-08-11 | La integración local es reciente; el Parquet no representa el archivo climatológico histórico de AEMET. |

Meteocat publica datos diarios históricos y medidas XEMA anteriores al inicio
del Parquet local; AEMET OpenData expone climatología diaria por rango de fechas
y estación; la API PWS de Weather Company permite consultar historia diaria por
estación y rango. Por tanto, una parte posiblemente importante de 2012–2022 es
**potencialmente recuperable**, pero no se debe contar como recuperada hasta
verificar estación, variable y día. Los límites previsibles son estaciones que
aún no existían, cambios de emplazamiento, ausencia de humedad u otra variable
exigida y falta de una alternativa dentro de 15 km.

El siguiente diagnóstico meteorológico debe trabajar solo en `docker-data` y:

1. enumerar para cada episodio la ventana histórica exacta requerida por cada
   contrato y conservar esas ventanas para la auditoría;
2. complementar hacia atrás cada fuente: desde 150 días antes de la primera
   observación elegible hasta el día anterior al inicio de su histórico local,
   para todas las estaciones conocidas disponibles en Meteocat, AEMET y en la
   lista PWS Wunderground, sin limitar la adquisición al radio de 15 km ni volver
   a pedir el tramo ya materializado;
3. normalizar las descargas en un Parquet provisional y unirlas con una copia
   del histórico actual sin eliminar ni sustituir filas, conservando fuente,
   estación, fecha, variables originales y flags de calidad;
4. volver a ejecutar entonces el selector sensible al corte, eligiendo la
   estación utilizable más cercana y aplicando fallback hasta 15 km, y publicar
   cuántos episodios se recuperan por fuente, especie, área, año y clase;
5. no mezclar nada en producción hasta validar duplicados, unidades, cobertura
   y coherencia frente a la serie ya existente.

El inventario ejecutable de los 127 episodios, sus ventanas `T-150…T`, los
rangos de backfill anteriores al histórico local de cada fuente, las 7 ventanas
mínimas, las 40 ventanas por área y las estaciones candidatas a 15 km para la
selección posterior queda descrito en
`docs/mushrooms/mushroom-weather-historical-backfill-handoff-es.md`. Los CSV y
el resumen reproducible viven únicamente en
`docker-data/audits/mushroom-weather-backfill-20260811/`.

Referencias oficiales: [Meteocat — Dades obertes](https://www.meteo.cat/wpweb/serveis/dades-obertes/),
[AEMET OpenData](https://opendata.aemet.es/dist/) y
[Weather Company — PWS Historical](https://developer.weather.com/docs/openapi/pws-historical-2-0).

### Ordino y la altitud representativa

El episodio Pinícola/Ordino de 2026-06-13 sí tiene estación meteorológica y
altitud de estación, pero no altitud representativa del área. No es un fallo del
centroide ni del selector meteorológico. El raster utilizado es el modelo de
elevaciones de Catalunya de 5 m; su rectángulo geográfico engloba la coordenada
de Ordino, pero las celdas situadas fuera de Catalunya están enmascaradas como
`NoData`. La reconstrucción GIS confirma `dem_5m: no_value` tanto para el área
como para su microárea.

No se debe deducir una cota del nombre `ordino_cota_2100` ni introducirla como
constante. El contrato corregido debe declarar `area_altitude_missing` y excluir
esa muestra de las temperaturas corregidas hasta disponer de una fuente DEM
trazable que cubra Andorra. La solución general es un DEM secundario de
cobertura transfronteriza, con procedencia y resolución registradas, no una
excepción manual para Ordino.

## Auditoría de variables v2

### Candidatas biológicas o contextuales

- calendario circular de la fecha objetivo;
- altitud representativa del área;
- lluvia en bandas disjuntas 0–3, 4–7, 8–14 y 15–21;
- edad de lluvia mayor de 2 mm y de lluvia significativa;
- duración de sequía observada;
- temperatura y humedad posteriores al episodio significativo;
- temperatura máxima media y temperatura media corregidas de siete días;
- `horizon_days` únicamente en el contrato de retardos.

Que sean candidatas no significa que deban entrar juntas. La muestra utilizable
muestra correlaciones muy altas:

| Variables | Correlación de Pearson aproximada |
|---|---:|
| temperatura máxima media 7d / temperatura media 7d | 0,971 |
| temperatura media 7d / temperatura media posterior a lluvia | 0,963 |
| edad lluvia >2 mm / edad lluvia significativa | 0,961 |
| edad lluvia >2 mm / sequía observada | 0,850 |

Estas relaciones explican la inestabilidad y los extremos de LR. La comparación
debe activar y desactivar familias completas de variables, no añadir todas las
derivadas por comodidad.

### Calidad y censura: metadatos, no predictores

Los siguientes campos describen si se pudo medir la meteorología. Deben salir
de `feature_cols` y permanecer en `sample.quality` y en la auditoría:

- `rain_observed_days_21`, `rain_missing_days_21`,
  `rain_suppressed_days_21`;
- `rain_observed_days_90`, `rain_missing_days_90`,
  `rain_suppressed_days_90`;
- `dry_spell_is_censored`;
- `temp_observed_days_after_significant_rain`;
- `humidity_observed_days_after_significant_rain`.

No son independientes: observados, ausentes y suprimidos suman la ventana; los
dos recuentos posteriores a lluvia son idénticos en la muestra completa y
correlacionan 1,000 con la edad del episodio por construcción. Dejarlos como
features permite que el estimador aprenda la historia del pipeline, la época
con mejor cobertura o la estación seleccionada en lugar de la florada.

### Campos que requieren redefinición o comparación controlada

- `significant_rain_found_90d` duplica en gran parte una edad ya limitada a
  `90` días. Debe permanecer como metadato de interpretación o demostrar valor
  en una comparación controlada antes de volver a ser predictor.
- temperatura/humedad «después de lluvia» actualmente significan media de 90
  días cuando no se encuentra un episodio. Esa doble semántica debe dividirse
  o eliminarse del conjunto mínimo.
- temperatura máxima media y temperatura media de siete días, así como los dos
  relojes de lluvia, no deben convivir automáticamente en un modelo lineal sin
  regularización y diagnóstico de colinealidad.
- `horizon_days` es parte del contrato temporal, no evidencia ecológica. Puede
  entrar en el modelo `lag_event` solo si se valida que un único estimador
  compartido representa correctamente los horizontes 1–7.

## Resultado del benchmark Biology V3

1. El target queda definido como utilidad de la salida, con `very_scarce`
   desfavorable y `pending/no visitado/no buscado` desconocido.
2. La muestra real y su sesgo quedan cuantificados; no se puede tratar todas
   las especies como problemas independientes igualmente entrenables.
3. El benchmark separa `predictive_features`, `quality` y `metadata`; ningún
   contador de cobertura vota en el modelo y las pruebas bloquean su entrada en
   `X`.
4. `fixed_gap` conserva 399 observaciones y deja 204 elegibles. `lag_event`
   conserva 1.596 filas de horizonte y deja 816 elegibles. Los grupos de
   florada de 7/14 días solo controlan el corte temporal; no reducen filas.
5. La evaluación vigente ejecuta los seis estimadores exactos sobre las mismas
   columnas de cada contrato. LR/RF se etiquetan activos y ET/HGB/KNN/SVM RBF
   experimentales, pero la etiqueta no filtra el análisis.
6. El Brier se informa por especie frente a su propia prevalencia. Los valores
   combinados entre especies quedan marcados como diagnósticos y no seleccionan
   estimadores.
7. El conjunto activo no contiene medias meteorológicas: usa acumulados IDW de
   lluvia, racha seca, temperatura máxima/mínima y humedad relativa
   máxima/mínima. Las medias se siguen materializando y validando, pero no
   entran en `X`.
8. No hay un ganador universal. En `fixed_gap`/14 días los mejores Brier por
   especie evaluable son LR (Amanita, Lactarius y Morchella), HGB (B. aereus),
   ET (B. edulis) y SVM RBF (B. pinophilus). La misma asignación se mantiene al
   repetir con grupos de 7 días.
9. En `lag_event`, también estable entre grupos 7/14, ganan LR (Amanita), KNN
   (B. aereus y Morchella), RF (B. edulis y B. pinophilus) y HGB (Lactarius).
   Las filas de horizonte no cuentan como observaciones independientes.
10. RF+ET es la pareja con mayor coincidencia sistemática, especialmente en
    `lag_event`. No se confunde coincidencia con calidad: para considerarla útil
    ambos deben mejorar el Brier de prevalencia de la especie.

No se ha elegido un sucesor operativo. La comparación ya usa las mismas filas y
separa contrato, estimador y especie, pero el soporte por especie continúa
siendo pequeño. Hay que acumular observaciones antes de un candidato operativo;
este bloque no persiste ni promociona modelos.
