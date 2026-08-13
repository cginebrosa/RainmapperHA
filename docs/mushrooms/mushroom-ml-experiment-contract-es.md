# Contrato de experimentación ML para floradas

Estado: `fixed_gap_7d_altitude_v2` y `lag_event_altitude_v2` son la pareja local
actual, pero quedan congelados como `reference_only` para la siguiente fase: no
se corregirán cambiando sus columnas o semántica. Conservan los cortes
temporales de v1, corrigen la temperatura por diferencia de altitud y eliminan
la racha térmica global de 28 °C. `fixed_gap_7d_v1` y `lag_event_v1` se
conservan también como referencia reproducible; `mushroom_ml_v0` queda como
baseline histórico.

La auditoría que fija el target, cuantifica la muestra real y separa variables
biológicas de calidad está en `mushroom-ml-v3-data-audit-es.md`. El sucesor
`fixed_gap_7d_biology_v3` / `lag_event_biology_v3` está únicamente especificado
en `mushroom-ml-v3-implementation-spec-es.md`: todavía no está implementado, no
entrena modelos y no modifica el Predictor.

Este documento define cómo construir y comparar modelos del Predictor usando
siempre los mismos datos, particiones y reglas temporales. La finalidad es que
añadir un algoritmo nuevo no permita cambiar accidentalmente el problema que
se está evaluando.

## Pregunta predictiva

Para una fecha objetivo `T` y un horizonte `h`, todo candidato debe estimar:

```text
P(florada útil en T | meteorología observada hasta T-h)
```

`T-h` es la fecha de corte o fecha de emisión. No se utilizan predicciones
meteorológicas. Un día posterior al corte es desconocido: nunca equivale a
lluvia cero, cero sequía o cero estrés térmico.

La fecha objetivo sí es conocida y puede aportar calendario o fenología. La
edad que tendrá en `T` un episodio de lluvia ya observado también puede
calcularse sin conocer el tiempo futuro.

## Contrato térmico corregido por altitud

Los contratos v2 no suponen que la temperatura medida en la estación sea la
temperatura físicamente representativa del área. Antes de construir variables
térmicas aplican:

```text
T_area = T_estacion + (altitud_estacion - altitud_area) / 100 * 0,65 °C
```

Por tanto, una estación 500 m por debajo del área aporta una corrección de
`-3,25 °C`; una estación más alta aporta una corrección positiva. El gradiente
`0,65 °C/100 m` es parte explícita y versionada del contrato físico v2. Coincide
con el valor empleado actualmente en MapLibre, pero no se lee de una preferencia
de la UI ni se ajusta durante el entrenamiento.

Las fuentes de altitud son auditables:

- la estación usa `altitude` del catálogo meteorológico Parquet;
- el área usa la media de `derived_context.gis_dem.altitude_mean_m` de **todas**
  sus microáreas materializadas en `known_sites`;
- no se usa la cota DEM del centroide de coordenadas;
- no se consulta el DEM en vivo durante una predicción;
- la media del área se deriva al cargar el JSON, de modo que no depende de qué
  microáreas tengan observaciones en una fecha concreta.

Las lecturas originales de estación no se modifican. El benchmark y el
Predictor construyen una serie corregida en memoria y guardan en metadatos la
altitud de estación, la altitud representativa del área, el gradiente y el
offset aplicado. Si falta cualquiera de las dos altitudes, las variables
térmicas corregidas quedan ausentes; nunca se sustituyen silenciosamente por la
temperatura cruda.

Los contratos v2 sustituyen:

- `heat_stress_observed_at_cutoff`;
- `heat_stress_is_censored`;

por variables continuas corregidas:

- `temp_max_mean_cutoff_7d_c`;
- `temp_mean_cutoff_7d_c`.

También corrigen `temp_mean_after_significant_rain_c`. No existe ya un umbral
global de 28 °C ni un umbral térmico hardcoded por especie: cada estimador
aprende de las temperaturas continuas corregidas y de las observaciones de su
propia especie. El comportamiento de v1 permanece disponible únicamente para
comparar la migración.

La paridad es vinculante: reconstrucción, entrenamiento, consulta local y
worker remoto deben invocar los mismos constructores v2. Una mezcla de bundle
v2 con variables v1 debe rechazarse por `feature_set_id`, no degradarse.

## Dos capas independientes

```text
artefacto de observaciones y meteorología diaria
                    |
                    v
benchmark congelado: muestras + cortes + particiones
                    |
          +---------+----------+
          |         |          |
       baseline     LR       árbol/otro
          |         |          |
          +---------+----------+
                    |
           informe comparable
```

La primera capa decide qué información puede ver un modelo. La segunda decide
cómo aprender de ella. Para comparar algoritmos se debe conservar intacta la
primera capa.

## Artefacto diario reutilizable

`mushroom_observation_features_v0.json` conserva ahora, además de los escalares
operativos, estas series ordenadas desde el día más antiguo hasta `T`:

- `daily_rain_mm`;
- `daily_temp_min_c`, `daily_temp_max_c`, `daily_temp_mean_c`;
- `daily_humidity_min_pct`, `daily_humidity_max_pct`,
  `daily_humidity_mean_pct`.

Las series permanecen fuera del CSV y del estimador operativo v0. Su función es
permitir reconstruir experimentos desde un artefacto inmutable, sin volver a
leer históricos meteorológicos que podrían cambiar.

## Benchmark versionado

El módulo `rainmapper_core.mushroom_ml_experiments` construye un JSON de tipo
`mushroom_ml_benchmark`. No entrena, instala ni promociona ningún modelo.

Cada muestra contiene:

- `episode_id`: especie, área y fecha objetivo;
- `sample_id`: episodio más horizonte;
- `target_date` y `cutoff_date`;
- `horizon_days`;
- target favorable/desfavorable;
- partición `train` o `test`;
- variables y metadatos de cobertura.

Los horizontes iniciales son `1..7`. Todos los horizontes derivados de un mismo
episodio quedan obligatoriamente en la misma partición. Además, fechas objetivo
iguales no se reparten entre entrenamiento y prueba.

La evaluación principal usa un 70/30 estratificado por clase y agrupado por
fecha objetivo. Aproxima por separado el 30% de favorables y desfavorables en
test, sin dividir una misma fecha/salida. La selección de fechas es
determinista con semilla `42` y queda materializada en el benchmark; los
modelos no pueden recalcularla a conveniencia.

El benchmark conserva en paralelo una partición cronológica 70/30, también
agrupada por fecha. Es un diagnóstico secundario de deriva hacia observaciones
más modernas. Si alguno de sus tramos contiene una sola clase, se declara no
disponible; no impide entrenar ni invalida la evaluación estratificada.

El ejecutable explícito acepta los dos contratos iniciales:

```bash
.venv/bin/python -m rainmapper_core.mushroom_ml_experiments \
  --features <mushroom_observation_features_v0.json> \
  --known-sites <mushroom_known_sites.json> \
  --feature-set fixed_gap_7d_v1 \
  --output <mushroom_ml_benchmark.json>
```

El benchmark registra SHA-256 de ambos inputs. Regenerarlo con otros datos crea
otro benchmark, aunque conserve el mismo catálogo de experimentos.

## Contrato `fixed_gap_7d_v1`

Es la hipótesis sencilla propuesta para hacer idéntica la información temporal
de entrenamiento y Predictor. Para cada observación en `T` genera una sola
muestra y fija el último día meteorológico visible en `T-7`. Los siete días
`T-6..T` quedan ocultos; no se rellenan con cero ni con predicción
meteorológica.

Las variables se calculan respecto a ese corte: bandas de lluvia, edad de la
última lluvia conocida, sequía y calor observados, calendario de `T` y altitud.
Para una consulta futura entre hoy y seis días vista, el corte queda entre ocho
días atrás y ayer y toda la información necesaria ya existe. Para una consulta
histórica se reproduce la misma ceguera de siete días del entrenamiento.

Este contrato responde a «qué se podía decir siete días antes de la florada».
Su ventaja es la coherencia y su coste es renunciar deliberadamente a
información reciente que sí puede ser útil para horizontes cortos.

## Contrato meteorológico revisado y selección de estación

Los dos feature sets comparten estas reglas. Son parte del contrato y deben ser
idénticas en reconstrucción, entrenamiento, HA y workers:

- conservar 120 días diarios en el artefacto JSON;
- buscar eventos de lluvia en los 90 días anteriores al corte;
- expresar una edad no encontrada como `90`, es decir, «90 días o más»;
- convertir a `0 mm efectivos` tanto una lluvia explícitamente descartada como
  una fecha sin lectura de lluvia, conservando por separado días observados,
  ausentes y suprimidos;
- no invalidar una suma completa por uno o varios huecos de lluvia;
- calcular temperatura y humedad con los días disponibles y conservar su
  cobertura; una ausencia nunca equivale a `0 °C` o `0%`;
- para `lag_event_v1`, usar como corte deseado el día anterior a la emisión y,
  si no está completo, retroceder al último día meteorológico completo;
- entrenar `lag_event_v1` con horizontes meteorológicos 1..7, coherentes con
  esa latencia de un día.

La estación se resuelve desde el centroide del área. Se prueban por distancia
las estaciones situadas como máximo a 15 km y se escoge la primera que cumpla
la calidad mínima versionada. Una estación no es elegible si no alcanza:

- 19/21 lecturas de lluvia recientes;
- 81/90 lecturas de lluvia en la búsqueda larga;
- 19/21 días con temperatura mínima y máxima;
- 19/21 días con humedad mínima y máxima.

Los valores de lluvia descartados cuentan como suprimidos, no como ausencias.
Si ninguna estación cumple, el Predictor debe abstenerse; no amplía el radio ni
utiliza silenciosamente una serie pobre. Entre dos estaciones elegibles se
prefiere la más cercana que tenga completo el día de corte requerido. Si la más
cercana supera la cobertura global pero todavía no ha publicado ese día, se
salta temporalmente a la siguiente elegible dentro de 15 km; solo si ninguna lo
tiene se permite retroceder al último día completo de la más cercana. Los
umbrales, el radio y el salto se registran en metadatos para poder revisarlos.

## Primer conjunto de variables: `lag_event_v1`

Es una hipótesis versionada, no una afirmación biológica definitiva. Mantiene
una dimensionalidad pequeña y utiliza únicamente meteorología observada hasta
el corte:

- horizonte y calendario circular de `T`;
- altitud;
- lluvia en bandas disjuntas de 0–3, 4–7, 8–14 y 15–21 días antes del corte;
- edad en `T` del último episodio conocido de más de 2 mm;
- edad en `T` de la última lluvia significativa conocida de al menos 5 mm;
- sequía y estrés térmico observados hasta el corte;
- indicador de que esas duraciones están truncadas por el límite del histórico;
- temperatura y humedad observadas después de la última lluvia significativa.

En este contrato legado, los umbrales de 2 mm, 5 mm y 28 °C no son nuevos: se
heredan de las derivadas v0 y quedan escritos en el benchmark. El umbral térmico
no existe en los contratos `*_altitude_v2`. Las bandas temporales son la primera
hipótesis que deberá someterse a ablation y sensibilidad; cualquier variante
recibirá otro `feature_set_id`.

Las sumas de lluvia usan la serie efectiva: un día ausente o descartado aporta
`0 mm`, sin invalidar la ventana, y su naturaleza queda conservada en los
contadores de días observados, ausentes y suprimidos. Temperatura y humedad no
se convierten en cero: se calculan con los días disponibles y exponen cuántos
días han contribuido. Las rachas inmediatas conservan además un indicador de
censura cuando su límite antiguo no es observable.

## Cómo añadir comparaciones futuras

Un experimento deberá declarar como mínimo:

```text
experiment_id
benchmark_sha256
feature_set_id
estimator_id y versión
hiperparámetros completos
semilla
política de imputación
política de calibración
métricas globales, por especie y por horizonte
```

Para comparar dos estimadores deben coincidir `benchmark_sha256`, muestras y
particiones. Para comparar dos conjuntos de variables deben derivarse de los
mismos episodios, horizontes y particiones, y el informe debe mostrar sus
distintos `feature_set_id`.

Los candidatos del laboratorio son:

1. prevalencia aprendida únicamente en train;
2. regresión logística regularizada y reducida;
3. random forest restringido;
4. Extra Trees restringido;
5. HistGradientBoosting poco profundo;
6. KNN escalado y ponderado por distancia;
7. SVM RBF calibrada, solo cuando train contiene al menos dos ejemplos de cada
   clase.

No se elegirá un ganador por una única métrica. El informe común deberá incluir
como mínimo ROC-AUC cuando sea calculable, PR-AUC, balanced accuracy, Brier,
log loss, matriz de confusión y número de muestras. También mostrará resultados
por horizonte y cobertura; una métrica ausente por clase única debe quedar como
ausente, no convertirse en cero.

Si el dataset completo de una especie contiene ambas clases pero el diagnóstico
cronológico agrupado deja una sola clase en train o test, el bundle se evalúa
con el 70/30 estratificado y se reajusta después con todos los episodios. Su
`temporal_validation.available` queda en `false`; no se parte una misma fecha
para fabricar una métrica cronológica. Una futura promoción deberá considerar
por separado la evaluación estratificada y esta limitación temporal.

## Entrenamiento shadow implementado

`rainmapper_core.mushroom_ml_experiment_trainer` construye, para ambos feature
sets, exactamente las mismas seis familias gestionables:

- `logistic_regression_reduced_v1`;
- `random_forest_restricted_v1`;
- `extra_trees_restricted_v1`;
- `hist_gradient_boosting_restricted_v1`;
- `knn_distance_v1`;
- `rbf_svm_calibrated_v1`.

LR y RF siguen siendo los únicos estimadores que pueden alimentar el dictamen
durante esta fase. ET, HGB, KNN y SVM son modelos sombra: aparecen con sus
scores y métricas, pero no votan ni modifican el rango operativo. La SVM se
omite por contrato cuando su calibración en dos folds no puede conservar dos
ejemplos de cada clase. Esto sucede actualmente solo para Marçot en
`fixed_gap_7d_v1`; no se mueven episodios ni se crean muestras sintéticas para
forzar su entrenamiento.

### Primera lectura local con seis estimadores (2026-08-10)

La primera ejecución sobre el benchmark congelado confirma que ampliar el
laboratorio aporta información y que no existe un ganador universal. Brier más
bajo es mejor; entre paréntesis figura el baseline de prevalencia:

| Especie | Contrato | Mejor estimador | Brier |
|---|---|---|---:|
| Ou de reig | fixed | LR | 0,1702 (0,2489) |
| Ou de reig | lag/event | LR | 0,1675 (0,2489) |
| Aereus | fixed | SVM* | 0,1858 (0,2222) |
| Aereus | lag/event | SVM* | 0,1778 (0,2222) |
| Edulis | fixed | LR | 0,1110 (0,1944) |
| Edulis | lag/event | SVM* | 0,1560 (0,1944) |
| Pinícola | fixed | HGB* | 0,1013 (0,2317) |
| Pinícola | lag/event | SVM* | 0,1449 (0,2317) |
| Marçot | fixed | ET* | 0,1223 (0,1480) |
| Marçot | lag/event | prevalencia | 0,1480 |
| Rovelló | fixed | LR | 0,0672 (0,1392) |
| Rovelló | lag/event | ET* | 0,0942 (0,1392) |

La SVM abre una vía especialmente relevante para Aereus, donde LR y RF no
superaban la prevalencia en ninguno de los dos contratos. Este resultado no la
promueve: debe comprobarse por episodio, horizonte y observaciones futuras. La
misma SVM es mala para Pinícola/fixed y Ou de reig, lo que confirma que la
selección futura tendrá que ser por especie y contrato, nunca una votación o un
modelo global elegido por una sola tabla.

También calcula una prevalencia aprendida solo en train. La evaluación usa el
corte estratificado y agrupado congelado; el diagnóstico cronológico se
conserva aparte. Los modelos de consulta se reajustan después con todas las
muestras. Los ficheros se denominan
`mushroom_ml_experiment_<feature_set>_<species>.joblib`; nunca pisan
`mushroom_ml_v0_<species>.joblib`.

El job normal de entrenamiento genera esos bundles después del operativo,
incluye su informe dentro de `shadow_experiments` y los promociona como
artefactos auxiliares. Reconstruir primero es obligatorio: un artefacto antiguo
sin series diarias no puede alimentar estos contratos.

## Pareja operativa e interpretación en el Predictor

El Predictor no debe presentar `mushroom_ml_v0` como recomendación futura. Sus
variables terminan en `T` y, para cualquier fecha posterior al último día
meteorológico completo, mezclan observaciones reales con días futuros
desconocidos. Sus ficheros se conservan temporalmente como baseline técnico y
para reproducir la transición, pero no alimentan rankings, colores, resumen
semanal, Historial ni dictamen.

La decisión operativa conserva dos contratos complementarios:

| Fila | Información visible |
|---|---|
| `fixed_gap_7d_v1` | meteorología hasta `T-7`, siempre |
| `lag_event_v1` | meteorología hasta ayer —o último día completo anterior—; horizonte `1..7` |

Cada fila técnica muestra corte meteorológico, LR, RF, ET, HGB, KNN, SVM y
media simple sin ponderar. Los estimadores sombra se identifican con `*`.
Esos scores no son probabilidades operativas calibradas. La media se conserva
para auditoría, pero no decide el resultado.

Cada bundle incluye la evaluación 70/30 fuera de muestra, el Brier de la
prevalencia y las métricas de LR y RF. Para cada combinación especie/feature
set, el motor de interpretación:

1. excluye cualquier estimador cuyo Brier no mejore la prevalencia;
2. entre los restantes usa como referencia el de menor Brier;
3. forma un rango con las referencias de `fixed_gap` y `lag_event`;
4. marca consenso bajo cuando LR y RF difieren al menos 20 puntos;
5. no muestra una recomendación si ningún estimador supera el baseline;
6. añade temporada, evento de lluvia, retraso de fructificación, cobertura y
   disponibilidad de ambos contratos como contexto explícito.

Desde el esquema de bundle `1.2` también conserva el soporte observado de cada
variable, la pertenencia train/test de cada episodio y las probabilidades del
holdout, además de la disponibilidad y motivo de exclusión de cada estimador.
Una variable que queda fuera del mínimo/máximo de entrenamiento y a
seis o más desviaciones estándar de su media se considera extrapolación
severa. La LR se excluye del dictamen porque puede saturarse linealmente en 0 o
1; el score bruto continúa visible para auditoría. Si dos referencias validadas
quedan separadas 50 puntos o más, el sistema se abstiene en lugar de presentar
ese rango como información utilizable.

Cuando ningún estimador supera el Brier de prevalencia, el Predictor ya no
silencia necesariamente el resultado. Resume por separado los ensembles
brutos aplicables como «señal favorable no validada», «señal desfavorable no
validada» o «señal estadística no interpretable». El rango se marca
explícitamente como bruto y no validado, participa en rankings como pista y no
se convierte en recomendación ni probabilidad calibrada.

Si los dos cortes seleccionan estaciones distintas, el contrato conserva los
códigos de ambas estaciones y añade un aviso al dictamen. La selección sigue
siendo independiente y correcta para cada corte, pero se explicita que una
parte de la diferencia entre scores puede proceder del cambio de estación y no
solo del contrato de variables.

La estadística no puede anular una incompatibilidad ecológica explícita del
perfil. Para cualquier especie con retraso de fructificación definido, si no se
encuentra lluvia significativa en 90 días o su edad supera el máximo declarado,
el dictamen es poco favorable y el rango estadístico deja de ser aplicable. La
regla es general, no una excepción por especie o área; los scores brutos siguen
visibles para diagnosticar correlaciones espurias.

El resultado es un contrato estructurado y determinista: `verdict`,
`reference_range`, `statistical_consensus`, `confidence`, `weather_signal`,
`fruiting_timing`, estimadores de referencia y `reason_codes`. El backend no
genera prosa libre. La UI traduce los códigos mediante plantillas de labels, de
forma idéntica en ejecución HA o worker.

El rango no es un intervalo de confianza ni una probabilidad calibrada. Es el
rango de scores de los estimadores que sí superan la prevalencia fuera de
muestra. Los estados posibles son favorable, incierto, poco favorable, fuera
de temporada y abstención.

### Presentación

- «Consultar fecha» muestra arriba el dictamen compacto, después la semana
  calculada con la pareja operativa y, de forma desplegable, todos los datos
  técnicos de ambos contratos. El bloque antiguo «Factores meteorológicos» se
  elimina porque duplicaba información y procedía de ventanas v0 inválidas para
  el futuro.
- «Esta semana» y «Por especie» muestran color, dictamen y rango compacto; cada
  celda enlaza al análisis completo.
- «Historial» recalcula el dictamen de ambos contratos para cada episodio y lo
  contrasta con lo observado. Si el episodio pertenece al 30% reservado,
  utiliza las probabilidades guardadas del modelo que no lo vio; si perteneció
  a train, muestra el ajuste final y avisa de que no es una comprobación
  independiente.
- Los datos técnicos conservan corte, horizonte, estación, salto de estación,
  cobertura, bandas de lluvia, edad de eventos, LR/RF, media sin ponderar y
  Brier frente a prevalencia.

El runtime remoto transporta perfiles y bundles con sus métricas embebidas. HA
y worker ejecutan el mismo módulo `mushroom_prediction_interpretation`; HA
mantiene UI, autoridad de jobs, caché de respuestas e Historial.

### Despliegue cuando la validación local sea definitiva

Este cambio afecta a ambos lados del contrato remoto:

1. HA necesita la UI, el servicio de expansión de vistas, el intérprete y el
   contrato actualizado de respuesta.
2. M1 y M5 necesitan el comparador, el intérprete y el entrenador que incrusta
   la evaluación dentro de cada bundle.
3. Después de actualizar imágenes debe repetirse **solo el entrenamiento ML**
   para regenerar los 12 bundles con métricas embebidas. No hace falta
   reconstruir los artefactos de observaciones si sus hashes y series diarias
   siguen correspondiendo al snapshot vigente.
4. El nuevo fingerprint del runtime sincroniza automáticamente modelos y
   perfiles al worker elegido. No se copian modelos manualmente entre HA y
   workers.
5. Se actualizan M1 y el paquete arm64 privado del M5. La configuración del
   coordinador, red y Tailscale no cambia.

Durante una actualización escalonada, un bundle antiguo sin evaluación produce
abstención, nunca una recomendación basada otra vez en la media v0. Por tanto el
orden seguro es actualizar worker, actualizar HA, reentrenar y validar el
runtime sincronizado.

`fixed_gap_7d_v1` debe dar una respuesta estable para `T` con independencia del
día de consulta. `lag_event_v1` puede cambiar cada día porque incorpora lo
observado hasta el último día meteorológico completo y declara el horizonte
restante.

Que un resultado «tenga sentido» en un caso conocido sirve para detectar y
descartar fallos graves, pero no demuestra precisión. La evidencia se
acumulará en tres niveles: métricas temporales congeladas, casos centinela
plausibles y predicciones guardadas antes de la salida que luego se contrasten
sobre el terreno. Nunca se escogerá un modelo mirando solo la salida que más
se parezca a la intuición del día.

## Primera ejecución local, solo diagnóstica e histórica

Con el snapshot local disponible el 2026-08-10, Aereus aportó 47 episodios al
benchmark diario. Esta ejecución utilizó todavía el holdout cronológico luego
reemplazado por la evaluación dual; se conserva para explicar la evolución:

| Contrato | Estimador | ROC-AUC | Brier |
|---|---|---:|---:|
| `fixed_gap_7d_v1` | LR reducida | 0,7500 | 0,3437 |
| `fixed_gap_7d_v1` | RF restringido | 0,5000 | 0,2826 |
| `lag_event_v1` | LR reducida | 0,4309 | 0,4215 |
| `lag_event_v1` | RF restringido | 0,6888 | 0,2787 |
| ambos | prevalencia de train | — | 0,2150 |

El resultado es deliberadamente inconcluso: `fixed_gap` mejora la ordenación de
LR y `lag_event` la de RF, pero todos los estimadores empeoran el Brier de la
prevalencia. Con una sola partición y tan pocos episodios no se promociona ni se
calibra ninguno. La tabla del Predictor existe precisamente para estudiar su
comportamiento sin ocultar esta limitación.

La ejecución integral inicial del caso Aereus/Coll/2026-08-14 confirmó además
que corregir únicamente el corte temporal no bastaba:

| Contrato | LR | RF | Media | Variables ausentes |
|---|---:|---:|---:|---:|
| `operational_v0` | 99,42% | 43,00% | 71,21% | gaps v0 |
| `fixed_gap_7d_v1` | 76,21% | 68,81% | 72,51% | 6/15 |
| `lag_event_v1`, h=4 | 81,97% | 49,85% | 65,91% | 11/16 |

Los dos shadows respetan sus cortes (`2026-08-07` y `2026-08-10`), pero siguen
dando scores altos sin eventos de lluvia utilizables porque el pipeline imputa
las variables ausentes. Por eso el laboratorio muestra el número de ausencias
y no acompaña los scores shadow de un semáforo favorable/desfavorable. El
resultado motivó el contrato revisado de lluvia efectiva, cobertura y selección
de estación descrito arriba.

## Segunda ejecución local con el contrato meteorológico revisado

La copia local reconstruida el 2026-08-10 seleccionó estación para 210 de 427
filas; 41 cambiaron de estación respecto al artefacto anterior y 139 dejaron de
usar una estación que no alcanzaba la calidad mínima dentro de 15 km. No se ha
modificado HA ni se han promovido modelos.

En Aereus quedaron 50 episodios. Estos resultados preceden también a la
partición estratificada actual y corresponden al antiguo holdout cronológico:

| Contrato | Estimador | ROC-AUC | Brier |
|---|---|---:|---:|
| `fixed_gap_7d_v1` | prevalencia de train | 0,5000 | **0,2165** |
| `fixed_gap_7d_v1` | LR reducida | 0,5091 | 0,4550 |
| `fixed_gap_7d_v1` | RF restringido | 0,6182 | 0,2358 |
| `lag_event_v1` | prevalencia de train | 0,5000 | **0,2165** |
| `lag_event_v1` | LR reducida | 0,7651 | 0,2537 |
| `lag_event_v1` | RF restringido | 0,6805 | 0,2311 |

Ningún estimador supera todavía a la prevalencia en Brier. `lag_event` ordena
mejor los casos, sobre todo con LR, pero sus scores siguen sin estar calibrados.

El caso centinela usa ILALEI9 a 2,08 km, con 90/90 días de cobertura de lluvia
bruta para la selección. Tras descartar tres repeticiones sospechosas, el
contrato conserva 87 días observados y 3 suprimidos; no queda ninguna variable
ausente:

| Contrato | Corte | LR | RF | Media | Ausentes |
|---|---|---:|---:|---:|---:|
| `operational_v0` | `T` | 99,42% | 43,00% | 71,21% | gaps v0 |
| `fixed_gap_7d_v1` | 2026-08-07 | 0,00% | 48,96% | 24,48% | 0/24 |
| `lag_event_v1`, h=5 | 2026-08-09 | 99,99% | 53,93% | 76,96% | 0/25 |

Ambos shadows ven las mismas magnitudes esenciales: 0 mm en las dos bandas
recientes, 3,05 mm en cada una de las bandas 8–14 y 15–21, y 71 días desde la
última lluvia significativa. Por tanto, el problema de `null` más imputación ha
desaparecido, pero la enorme divergencia de LR demuestra que el modelo sigue
inestable y que el horizonte replicado de `lag_event` introduce una asociación
que debe analizarse. El contrato cambia por completo `fixed_gap`, pero no
autoriza a escogerlo por resultar más plausible en un único caso.

Entrenamiento y Predictor llaman a los mismos constructores
`build_fixed_gap_7d_features` y `build_lag_event_features`, y comparten la
selección de estación, la serie diaria efectiva y los umbrales de cobertura.
El Predictor conserva en la respuesta estación, distancia, corte, horizonte,
coberturas y variables usadas; esta simetría es obligatoria para cualquier
feature set futuro.

## Tercera ejecución local: evaluación estratificada y UI ampliada

Se copió en modo lectura el snapshot HA del 2026-08-10 a `docker-data`: 400
observaciones activas, 630.449 filas meteorológicas y 1.948 estaciones. Se
regeneraron contexto meteorológico y features, y se entrenaron localmente los
seis modelos operativos y los doce bundles shadow. No se modificó HA.

La evaluación estratificada de Aereus usa 24 favorables + 12 desfavorables en
train y 10 + 5 en test. Ningún candidato supera la prevalencia en Brier:

| Contrato | Estimador | ROC-AUC | Brier |
|---|---|---:|---:|
| `fixed_gap_7d_v1` | prevalencia | 0,5000 | **0,2222** |
| `fixed_gap_7d_v1` | LR | 0,5600 | 0,2569 |
| `fixed_gap_7d_v1` | RF | 0,4800 | 0,2754 |
| `lag_event_v1` | prevalencia | 0,5000 | **0,2222** |
| `lag_event_v1` | LR | 0,5457 | 0,3009 |
| `lag_event_v1` | RF | 0,5159 | 0,2852 |

Con esos modelos, el caso Aereus/Coll/2026-08-14 produce 16% operativo, 24%
`fixed_gap` y 27% `lag_event`. Los dos shadows ven 0 mm en las dos bandas
recientes y 71 días desde lluvia significativa. El cambio respecto a la
segunda ejecución demuestra que la partición de evaluación y las observaciones
frescas alteran mucho modelos tan pequeños; no convierte esos scores en
probabilidades calibradas.

Edulis usa 15 favorables + 3 desfavorables en train y 6 + 2 en test. La LR de
`fixed_gap` obtiene ROC-AUC 0,9167 y Brier 0,1110 frente a 0,1944 de prevalencia,
pero sólo hay ocho episodios de test. El diagnóstico cronológico continúa no
disponible porque su train contiene 16 favorables y ningún desfavorable. La UI
lo muestra expresamente y evita interpretar la cifra estratificada como prueba
de generalización futura.

El «Laboratorio de modelos» muestra ahora, además de LR/RF/resultado: estación,
distancia, horizonte, calidad 21/90, salto de estación, bandas de lluvia, días
desde eventos, cobertura observada/ausente/suprimida, cobertura posterior al
evento y estado de validación temporal.

## Promoción al Predictor

Construir un benchmark o ganar una comparación no cambia el modelo de HA. La
promoción requiere una decisión separada y estas comprobaciones:

- superar la prevalencia fuera de muestra;
- comportamiento coherente en varios cortes temporales;
- estabilidad por horizonte y especie;
- tratamiento explícito de cobertura insuficiente;
- caso centinela Aereus/Coll de la Batalla sin salto favorable causado por días
  futuros desconocidos;
- compatibilidad del mismo `feature_set_id` entre entrenamiento y Predictor;
- modelo, informe, features y contrato temporal versionados conjuntamente.

Hasta entonces, `mushroom_ml_v0` continúa siendo el modelo operativo y este
pipeline es únicamente laboratorio reproducible.
