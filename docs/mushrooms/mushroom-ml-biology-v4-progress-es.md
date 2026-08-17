# Progreso de implementación de Biology V4

Estado global: **CERRADA TÉCNICAMENTE EN LOCAL; NO CANDIDATA OPERATIVA**.

Este registro se actualiza al cerrar cada punto. No sustituye la especificación
científica ni autoriza cambios en HA, M1, entrenamiento, promoción o releases.

## Fase 1 — motor hídrico local

### Punto 1 — contexto estático SoilGrids por microárea

Estado: **COMPLETADO Y VALIDADO EN LOCAL — 2026-08-15**.

Implementado:

- contrato `soilgrids_tile_512px_v1`, cuadrícula nativa de 250 m y teselas de
  512 × 512 píxeles;
- 54 coberturas: `wv0010`, `wv0033` y `wv1500`, seis profundidades y tres
  cuantiles;
- instantáneas y SHA-256 de las capacidades WCS oficiales;
- descarga a `staging`, validación GeoTIFF, normalización con CRS, promoción y
  manifiesto atómicos, lock y reutilización por hash;
- descarga rectangular por lotes y corte local, una petición por cobertura;
- reserva conservadora alrededor de las 58 microáreas actuales;
- intersección exacta por superficie de Polygon/MultiPolygon, incluidos huecos;
- agregado por profundidad y cuantil con calidad, procedencia y hashes separados;
- contexto `pending` legible si faltan activos, sin inventar ceros;
- materialización sobre un fichero candidato distinto, preservando el DEM.
- integración local del alta/edición UI: reutiliza geometrías sin cambios,
  resuelve geometrías nuevas y conserva un estado `pending` legible si falla;
- identidad semántica declarativa: V4 incluye el `context_hash` SoilGrids,
  mientras V2/V3 no cambian por añadir este contexto estático.

Resultado local:

| Comprobación | Resultado |
| --- | ---: |
| Microáreas | 58 |
| Teselas ocupadas | 6 |
| Reserva rectangular con un anillo | 30 |
| Teselas con suelo/costa | 25 |
| Posiciones de mar puro | 5 |
| Coberturas | 54 |
| Entradas del manifiesto | 1.355 |
| Entradas inválidas | 0 |
| Tamaño de caché | 407 MB |
| Contextos completos | 58/58 |
| Cobertura espacial | 58/58 a 1,0 |
| Diferencia frente a auditoría 0–5 cm Q0.50 | 0 |

Evidencias:

- `rainmapper_core/mushroom_soilgrids.py`;
- `scripts/manage-soilgrids-cache.py`;
- `scripts/materialize-micro-area-soilgrids.py`;
- `tests/test_mushroom_soilgrids.py`;
- `biology-v4-soilgrids-full-profile-audit-2026-08-15.json`;
- candidato local en `/private/tmp`, SHA-256
  `79d6d387fb58b5ec391917c1581960dec315f43eaa3646eac883cd5754cf17d1`.

Límites mantenidos:

- no se cambió el `mushroom_known_sites.json` operativo;
- no se tocó HA ni el worker M1;
- no se entrenó, promovió ni publicó ningún modelo o artefacto;
- la integración UI existe solo en el código local y no se ha desplegado;
- falta materializar el candidato en el catálogo operativo cuando llegue la
  fase de integración autorizada.

### Punto 2 — balance climático diario

Estado: **COMPLETADO EN LOCAL (2026-08-15)**.

Implementado en `rainmapper_core/mushroom_climatic_water_balance.py` con el
contrato `microarea_climatic_water_balance_v1` y el método versionado
`hargreaves_samani_fao56_temperature_v1`:

- usa lluvia por `area_daily_mean_microarea_idw_duplicate_zero_v2`, Tmin/Tmax corregidas,
  latitud y fecha;
- convierte radiación extraterrestre FAO-56 de MJ/m²/día a evaporación
  equivalente antes de aplicar Hargreaves-Samani;
- no expone la temperatura media auxiliar como predictor;
- mantiene humedad mínima/máxima como variables V4 independientes;
- no imputa huecos como cero y exige soporte diario completo por ventana;
- separa `predictive_features`, `quality` y `metadata`;
- produce las ventanas heredadas exactas 0–6, 7–13, 14–20 y 21–29 días;
- conserva motivos de ausencia y cierre de balance medible.

Validación:

- 7 pruebas unitarias específicas superadas, incluido ejemplo de escala FAO,
  límites, fechas consecutivas, huecos, ventanas y ausencia de fuga a `X`;
- las 17 pruebas de Biology V3 siguen pasando después de conservar Tmin y los
  extremos de humedad en metadata para V4;
- auditoría real reproducible final en
  `biology-v4-climatic-balance-audit-2026-08-15.json`: 399 filas conservadas,
  362 auditables, 37 exclusiones fuente explícitas, 202 con las cuatro ventanas
  hídricas completas, 0 fallos computacionales y error máximo `4,99e-7 mm`;
- el bloque completo `climatic_balance`, que exige además las demás variables
  acumulativas, queda disponible en 198 filas; el cálculo hídrico no elimina
  ninguna observación del benchmark general.

No se entrenó ni promovió nada y no se modificaron HA, M1 o catálogos vivos.

### Punto 3 — depósito de suelo / SMI

Estado: **MOTOR EXPERIMENTAL COMPLETADO EN LOCAL (2026-08-15)**.

Implementado en `rainmapper_core/mushroom_soil_water_state.py`:

- capacidad SoilGrids de tierra fina `wv0033-wv1500`, con `wv0010-wv1500`
  conservada como variante;
- perfiles comparables 0–30, 0–60 y 0–100 cm, sin seleccionar ganador;
- depósito diario acotado, ET real limitada por agua disponible, drenaje,
  demanda no satisfecha y cierre de masa;
- calentamientos 90/180/365 desde estado seco y saturado;
- huecos explícitos que nunca se convierten en días secos;
- cálculo primero por microárea y resumen posterior por área;
- media, mínimo, cambio 7/14, recarga, déficit y secado como candidatos;
- `predictive_features`, `quality` y `metadata` separados.

Auditoría real:

- snapshot temporal coherente con 58/58 altitudes DEM y 58/58 contextos
  SoilGrids; se detectó que el primer candidato del punto 1 mezclaba SoilGrids
  completo con un snapshot antiguo de solo 2 altitudes, sin tocar HA;
- seis variantes auditadas con 365 días hasta 2026-08-11;
- 45/58 microáreas y 20/28 áreas disponibles; todas convergen con 90 días;
- 13 microáreas quedan fuera por huecos de lluvia/ET0, no por falta de
  convergencia; sus motivos y conteos se conservan;
- capacidad `wv0033` 0–30 cm: 34,81–55,96 mm; 0–100 cm:
  104,11–181,42 mm;
- 8 pruebas unitarias específicas superadas.

Límite abierto: el caché aún no contiene `cfvo`; por tanto el índice describe
tierra fina sin corrección por fragmentos. Tampoco incorpora interceptación,
escorrentía, vegetación o raíces calibradas. Se mantiene como
`uncalibrated_physical_index` y ninguna variante se activa antes del benchmark.

### Punto 4 — calidad, pruebas integradas y candidato de benchmark

Estado: **BENCHMARK Y COMPARACIÓN UNIFICADA V2/V3/V4 COMPLETADOS EN LOCAL
(2026-08-15)**.

`rainmapper_core/mushroom_ml_biology_v4.py` declara cuatro bloques acumulativos
sin condicionales por algoritmo:

```text
core
extended_weather
climatic_balance
soil_water
```

Los contratos temporales son `fixed_gap_7d_biology_v4` y
`lag_event_biology_v4`; este último añade `horizon_days`, el fijo lo conserva
fuera de `X`. Todos los estimadores recibirán las mismas columnas dentro de
cada contrato y bloque.

El registro materializa lluvia 22–30, días lluviosos, extremos adicionales,
balance y los siete resúmenes edáficos. No registra medias meteorológicas,
área, microárea, altitud directa, coberturas o motivos como predictores.
`build_biology_v4_X` rechaza explícitamente calidad, metadata y cualquier campo
no registrado. Cada fila conserva elegibilidad y motivos por bloque, por lo
que una carencia de suelo no elimina la observación de `core` o clima.

Once pruebas específicas verifican acumulación de bloques, extremos sin
medias, diferencia fixed/lag, conservación de filas incompletas, respaldo con
mediciones reales, perfiles meteorológicos declarativos y doble barrera contra
fugas a `X`.

La paridad local train/inferencia quedó auditada campo por campo con el mismo
constructor compartido. En `core`, `climatic_balance` y `wv0033_0_30cm` hay
cero diferencias predictivas y cero diferencias de elegibilidad sobre las 399
muestras fixed y las 1.596 lag. Los seis informes y sus SHA-256 están en el
archivo local; no ajustan ni escriben modelos. Queda pendiente únicamente la
paridad de empaquetado/runtime HA–worker, que pertenece a la futura integración.

La reconstrucción final corrigió además dos contratos de calidad sin inventar
datos meteorológicos:

- un `N/A` de lluvia identificado específicamente como repetición positiva del
  día anterior aporta `0 mm`, según la decisión ya adoptada; cualquier otro
  `N/A` continúa ausente. Esto queda versionado como
  `daily_rain_idw_radius15km_power2_duplicate_zero_v2` y se audita mediante
  contadores separados;
- para Tmin/Tmax se intenta primero la estación elegida por el selector V2. Un
  día ausente puede proceder de otra estación real, dentro de 15 km y elegible
  en el mismo corte, con corrección a la altitud del área. No hay interpolación
  ni consulta futura.

Benchmarks locales finales sobre el mismo snapshot:

| Contrato | Filas totales | `core` | `extended_weather` | `climatic_balance` | Suelo 0–30 cm |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fixed_gap_7d_biology_v4` | 399 | 204 | 199 | 198 | 191 |
| `lag_event_biology_v4` | 1.596 | 816 | 794 | 793 | 765 |

El respaldo térmico recupera 25 de las 32 filas semanales que antes perdían el
bloque superficial y 98 filas del contrato variable (667→765). Las 7 filas
semanales restantes pertenecen solo a tres combinaciones área-fecha: dos cortes
de `rubio` y uno de `sant_joan`; faltan dos días en cada serie de 365 y ninguna
estación alternativa elegible aporta medición. Las observaciones se conservan
y solo se desactiva su bloque edáfico.

Las seis variantes de suelo siguen disponibles y ninguna se elige todavía:

| Variante | Fixed soil | Lag soil |
| --- | ---: | ---: |
| `wv0033_0_30cm` | 191 | 765 |
| `wv0010_0_30cm` | 191 | 765 |
| `wv0033_0_60cm` | 191 | 759 |
| `wv0010_0_60cm` | 187 | 749 |
| `wv0033_0_100cm` | 187 | 743 |
| `wv0010_0_100cm` | 181 | 720 |

Se generaron evaluaciones emparejadas por bloques, especie y cada uno de los
seis estimadores, con grupos temporales tanto de 7 como de 14 días y sin
artefacto de modelo. Con grupos de 14 días, el balance mejora el Brier frente a
`core` en 18 de 44 comparaciones estimador-especie semanales y en 30 de 48 de
ventana variable; empeora 16 y 14, respectivamente, y empata en las restantes.
Con grupos de 7 días mejora 17/44 y 27/48, y empeora 20/44 y 18/48. La señal
favorable es más consistente en `lag_event`, pero debe leerse por especie y
estimador. El suelo no es un ganador universal:
en semanal mejora entre 22 y 25 de 44 comparaciones según variante; en ventana
variable mejora entre 15 y 18 de 48 y empeora entre 22 y 31. No se usa ni se
publica un Brier medio entre especies.

Dirección del balance frente a `core`, acumulando únicamente los seis
estimadores en las dos particiones 7/14 (mejora/empeora/empata; no son ensayos
independientes ni una prueba de significación):

| Especie | Fixed | Lag event |
| --- | ---: | ---: |
| *Amanita caesarea* | 0/12/0 | 6/6/0 |
| *Boletus aereus* | 4/8/0 | 1/11/0 |
| *Boletus edulis* | 2/2/4 | 6/6/0 |
| *Boletus pinophilus* | 8/4/0 | 12/0/0 |
| *Hygrophorus latitabundus* | 2/0/6 | 12/0/0 |
| *Hygrophorus marzuolus* | 6/2/4 | 6/3/3 |
| *Lactarius deliciosus* | 10/1/1 | 12/0/0 |
| *Morchella elata* complex | 3/7/2 | 2/6/4 |

Las demás especies no tienen particiones cronológicas con las dos clases y
soporte suficiente para esta comparación. La dirección del suelo también es
específica: al considerar las seis variantes, muestra señal favorable para
*A. caesarea* en ambos contratos, pero claramente desfavorable en `lag_event`
para *B. pinophilus* y *H. latitabundus*. Repetir una especie en seis variantes
no multiplica la evidencia; solo prueba sensibilidad al perfil/capacidad.

El bloque `extended_weather` se descompone además mediante perfiles
declarativos, siempre sobre las mismas filas que `climatic_balance`: lluvia
acumulada 22–30, número de días lluviosos, extremos térmicos 8–30 y extremos de
humedad 22–30. En `lag_event`, días lluviosos mejora 27/48 pares con grupos 7 y
29/48 con grupos 14; lluvia 22–30 mejora 25/48 y 26/48. La extensión de humedad
22–30 empeora 25/48 y 27/48. Esto no desactiva humedad: `core` ya conserva sus
mínimos/máximos hasta 21 días; solo muestra que prolongarla al mes no está
respaldado por este snapshot. En `fixed_gap` todos los aportes son más mixtos.

Resultados reproducibles locales bajo
`docker-data/mushroom-data/ml_version_archive/biology_v4/local-benchmark-20260815-rain-v2/`,
incluidas las cuatro evaluaciones `groups7`/`groups14`.
No implica entrenamiento operativo, promoción, HA o worker.

La comparación multiversión reconstruye V2 sobre las mismas observaciones y
materializa V3 y cada perfil V4 mediante el mismo evaluador genérico. La
intersección exacta conserva 167 filas en `fixed_gap` y 674 en `lag_event` para
`core`; los perfiles ampliados conservan 162 y 656, respectivamente. Las filas
que quedan fuera de una intersección siguen presentes en sus benchmarks de
origen y conservan el motivo de calidad: no se borran observaciones.

Como control, V4 `core` reproduce exactamente el Brier de V3 en las cuatro
particiones, todas las familias, especies y estimadores. Por tanto las
diferencias de los perfiles V4 proceden de las columnas añadidas y no del
comparador. En `active_full`, V3 `core` supera a V2 en 21/34 y 23/34 pares
semanales con grupos 7/14, y en 21/36 pares `lag_event` con ambos grupos. No es
un resultado universal por especie o algoritmo.

V4 tampoco muestra una mejora general sobre V3 o V2. Acumulando únicamente las
cuatro comparaciones y los seis estimadores, el balance frente a V3 mejora en
10/12 pares de *B. edulis* y 16/24 de *B. pinophilus*, pero solo en 4/24 de
*B. aereus* y 1/23 de *Morchella*. Frente a V2, el balance es favorable en
20/36 pares `lag_event`, pero queda prácticamente equilibrado en semanal
(14/29 y 13/29 mejoras con grupos 7/14). Estas repeticiones miden estabilidad
direccional, no son ensayos independientes ni se agregan en un Brier medio.

Se archivaron los cuatro informes unificados
`fixed_gap_7d-v2-v3-v4-groups{7,14}.json` y
`lag_event-v2-v3-v4-groups{7,14}.json`, con SHA-256 reproducible. No contienen
un modelo reutilizable (`model_artifact_written=false`).

### Punto 5 — continuidad diaria

Estado: **EVALUACIÓN LOCAL DE CONTINUIDAD COMPLETADA; NINGUNA CAPA DE ESTADO
ACTIVADA (2026-08-15)**.

`rainmapper_core/mushroom_ml_biology_v4_continuity.py` implementa el contrato
diagnóstico `species_area_daily_continuity_diagnostic_v1`. Sobre una secuencia
diaria por especie y área calcula días positivos/negativos aislados, variación
total de probabilidad, longitudes de racha y cambios entre etiquetas observadas.
Los huecos de fechas cortan las rachas y no se cuentan como transiciones
diarias. Devuelve `predictive_features` vacío y declara que no modifica
probabilidades ni etiquetas. Tres pruebas sintéticas cubren parpadeo, huecos y
entradas inválidas; dos adicionales cubren el ajuste transitorio causal y el
rechazo de estimadores no registrados. La paridad de columnas y valores entre
el constructor V4 de benchmark y el de inferencia diaria también está probada.

`materialize_daily_inference_row` reutiliza el constructor V4 y elimina
únicamente el gate de target desconocido: lluvia, cobertura, estación, altitud
y variables ausentes siguen bloqueando la fecha con motivo legible. El
evaluador ajusta modelos transitorios solo con train, predice una matriz diaria
y adjunta las etiquetas del hold-out después de predecir. No serializa modelos,
no cambia probabilidades y no consulta observaciones futuras.

El script `evaluate-biology-v4-continuity.py` reconstruyó meteorología real
diaria en ventanas de ±14 días alrededor de cada observación del hold-out
semanal. Usa lluvia IDW de área, selector térmico V2 sensible al corte y el
mismo perfil V4. Con grupos de 14 días produjo 617 filas-área, 596 elegibles y
21 exclusiones de calidad; con grupos de 7, 603/584 y 19 exclusiones. Los
controles `core` y `climatic_balance` usan exactamente las mismas filas y
particiones.

Resultado emparejado sobre 140 secuencias especie–estimador–área evaluables:

| Grupos | Días aislados `core`→balance | Pares baja/sube/empata | Variación baja/sube/empata |
| --- | ---: | ---: | ---: |
| 7 días | 98→77 | 30/17/93 | 77/46/17 |
| 14 días | 105→62 | 33/18/89 | 75/42/23 |

La reducción direccional se repite, especialmente en *A. caesarea*,
*B. pinophilus* y *L. deliciosus*, pero no es universal. *B. edulis* y
*Morchella* no muestran una reducción consistente de parpadeo. Los pares no
son ensayos independientes y esta métrica no sustituye Brier o calibración.
No se ha añadido suavizado ni histéresis.

`lag_event` se reconstruyó por separado para horizontes 1/2/3/7, sin mezclar
sus secuencias. Con grupos de 14 días, los aislados `core`→balance fueron
100→87, 116→85, 118→78 y 123→91; con grupos de 7 fueron 98→90, 99→94,
96→89 y 105→95. La variación total bajó en 92–101 de 144–150 pares por
horizonte con grupos 14 y en 101–106 con grupos 7. En la partición de 7 días,
los horizontes 2/3 tienen casi tantos pares que suben como que bajan sus días
aislados: una curva menos variable no garantiza menos cruces del umbral 0,5.

Los cuatro informes fixed y los dieciséis lag (`core` emparejado y balance,
grupos 7/14) están en el archivo local de V4 con SHA-256 y
`model_artifact_written=false`.

El depósito superficial `wv0033_0_30cm` se reconstruyó después por fecha y
microárea, usando 365 días causales, y se agregó al área solo después de cada
simulación. Siempre se comparó contra balance sobre la intersección exacta del
perfil de suelo. En `fixed_gap`, los aislados balance→suelo fueron 81→84 con
grupos 7 y 67→81 con grupos 14. En `lag_event`, con grupos 7 fueron 70→89,
72→89, 74→92 y 93→112 para horizontes 1/2/3/7; con grupos 14 fueron 68→75,
64→78, 64→73 y 90→89. La variación también aumentó en los cuatro horizontes
lag de ambas particiones. Por tanto el suelo se conserva como variable
experimental materializada, entrenable y validable, pero queda **no
seleccionado** para predicción o continuidad.

El gate para aprender `species_area_flush_continuity_v1` tampoco se supera. En
el hold-out semanal evaluable hay solo 50 etiquetas únicas
especie–área–fecha (28 favorables, 22 desfavorables) dentro de las secuencias.
No bastan para aprender de forma separada inicio, mantenimiento y final sin
introducir reglas manuales o reutilizar la misma evidencia muchas veces. La
capa se mantiene especificada y desactivada para poder reevaluarla cuando haya
más observaciones.

Los informes de suelo y sus controles emparejados se archivaron también con
SHA-256. Toda la evaluación diaria mantiene `model_artifact_written=false`.

## Punto 6 — decisión de candidatura

Estado: **GATE NO SUPERADO; V4 SE CONSERVA COMO `proposed` (2026-08-15)**.

La decisión no usa un Brier medio. En la comparación unificada, balance V4
frente a V3 empeora más pares de los que mejora en ambos `fixed_gap`; en
`lag_event` queda aproximadamente equilibrado y cambia de dirección según
especie. Frente a V2 tampoco existe superioridad estable. El beneficio de
continuidad del balance es real pero no compensa una mejora predictiva ausente.
El depósito SoilGrids no mejora Brier de forma general y empeora continuidad.

Consecuencia:

- `biology_v4` permanece viva, registrada, documentada y reproducible con
  estado `proposed`;
- balance, suelo y capa de continuidad se conservan para reentrenar y revalidar
  en el futuro, pero no se activan en predicción;
- no se entrena una generación candidata, no se promociona nada y no se cambia
  HA, M1, GHCR o `known_sites` operativo;
- reabrir el gate exige más observaciones o evidencia nueva y vuelve a ejecutar
  las mismas comparaciones, sin borrar V2/V3/V4.
