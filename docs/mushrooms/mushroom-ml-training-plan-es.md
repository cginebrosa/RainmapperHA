# Plan de reconstruccion y entrenamiento ML de setas

Este documento define la direccion acordada para construir un modelo de machine
learning basado en observaciones reales. El `mushroom_model_v0.json` actual es
descriptivo: resume soporte, rangos y gaps, pero no entrena un estimador ni
produce probabilidades. El modelo ML sera un artefacto separado.

El diagnóstico real del primer entrenamiento productivo y el plan vigente para
pulir o sustituir sus estimadores se mantienen en
`mushroom-ml-model-hardening-plan-es.md`. Ese documento prevalece para la fase
de comparación con el dataset actual: tratamiento de huecos, reducción de
variables, abstención, validación y calificación de modelos.

Fuente bibliografica inicial por especie:

- `docs/mushrooms/literature/prediction/boletus_aereus_revision_bibliografica_rainmapper.md`

La bibliografia selecciona familias de variables candidatas y ayuda a interpretar
resultados. No fija filtros, pesos ni umbrales si las publicaciones no los
cuantifican especificamente.

## Alcance inicial

Dataset al 2026-08-02 (tras importacion masiva de fotos de campo):

- 772 observaciones totales: 126 `include` + 646 `review` pendientes de
  revision manual de especie y evidencia.
- Corte 2018+: Meteocat (XEMA, datos desde 2016-12-20) es la unica fuente
  weather con historico util para el periodo 2017-2022. Las observaciones
  anteriores a 2018 son escasas (≤19 por especie) y no justifican el coste
  de revision para el modelo v1.
- 8 especies alcanzan el umbral minimo de ≥20 observaciones desde 2018:

  | Especie                     | Observaciones desde 2018 |
  |-----------------------------|--------------------------|
  | Boletus edulis               | 152                      |
  | Boletus aereus               | 151                      |
  | Boletus pinophilus           | 100                      |
  | Lactarius deliciosus         |  93                      |
  | Amanita caesarea             |  77                      |
  | Hygrophorus marzuolus        |  66                      |
  | Cantharellus cibarius s.l.   |  28                      |
  | Morchella elata complex      |  22                      |

- Las 9 especies restantes tienen entre 2 y 7 observaciones y no entran en
  el modelo v1; podran incorporarse cuando el dataset crezca.
- Umbral empirico: 22 observaciones (Morchella elata complex) es el limite
  con incertidumbre alta; 66+ es comodo; ≥20 se usa como criterio de entrada
  al primer modelo.

### Estado tras revision (2026-08-03)

Tras la primera pasada de revision manual de las 646 observaciones importadas:

- **587 observaciones** en el store (reduccion respecto a 772 por archivado/fusiones).
- **423 validas** (`validation_status=valid`): la observacion de especie, fecha y
  lugar esta confirmada.
- **191 validas con `calibration_use=review`**: validacion de especie confirmada pero
  florada pendiente de rellenar por el usuario (`flush_abundance=pending`).
  Estas observaciones proceden de la identificacion automatica desde fotografias;
  el usuario todavia no ha registrado cuantos ejemplares encontro. **No cuentan
  como ausencias**: quedan excluidas del entrenamiento automaticamente por
  `calibration_use != include`, no por su `flush_abundance`.
- **232 validas con `calibration_use=include`**: especie y florada confirmadas,
  aptas para entrenamiento si tienen `micro_area_id` asignada.
- **158 draft**: observaciones pendientes de revision completa; no entran en ningun
  calculo.

Bloqueos activos para ampliar el dataset de entrenamiento:

1. **Rellenar florada en las 191 obs con `calibration_use=review`**: son visitas reales
   con especie confirmada; en cuanto el usuario registre la florada observada y pase
   `calibration_use` a `include`, entraran al entrenamiento.
2. **Asignar `micro_area_id` a 65 obs validas** que aun no tienen setal asignado.
3. **Revisar las 158 obs en draft**: confirmar especie y florada para que pasen a valid.

Primer objetivo: clasificacion binaria de utilidad operativa de la florada para
una salida de recoleccion: `unfavorable=0`, `favorable=1`. No es una
clasificacion de mera presencia: encontrar uno o dos ejemplares puede conservar
`analysis_result=present` y, a la vez, ser `prediction_target=unfavorable` si la
florada se registra como `very_scarce`.
Evolucion posterior: abundancia ordinal desde `absent` hasta `exceptional`.

Las primeras salidas seran experimentales y no se presentaran como predictor
fiable mientras la validacion y el numero de negativos sean insuficientes.

Las visitas negativas reales son especialmente importantes: no deben
fabricarse ausencias desde fechas o lugares que no se visitaron. Con el
dataset actual predominan las observaciones positivas; hay que priorizar el
registro de no detecciones con esfuerzo conocido.

El objetivo no es predecir presencia biologica, micelio ni cualquier carpoforo
aislado. Predice si las condiciones se parecen a episodios con una florada
minimamente interesante. Una visita sin carpoforos visibles es una no deteccion
condicionada por el esfuerzo de busqueda, no una demostracion de ausencia de la
especie; una visita `very_scarce` confirma presencia visible, pero sigue siendo
desfavorable para recomendar la salida.

## Unidad de entrenamiento

La unidad no debe ser cada registro aislado, sino un episodio independiente:

```text
especie + micro_area_id + fecha
```

Varias observaciones de la misma florada no deben aparecer como ejemplos
independientes, tengan o no fotografia asociada.
El dataset generara un `episode_id` interno y reproducible desde esos campos. No
es necesario pedir al usuario un identificador de salida.

**Implementado (2026-08-02):** `mushroom_learned_model.py` consolida las filas de
entrenamiento en episodios antes de construir el modelo V0, mediante
`consolidate_to_episodes`. La clave de episodio es `(species_id, micro_area_id, date)`.
Politica de consolidacion:
- `prediction_target`: favorable si alguna observacion del episodio es favorable.
- Variables categoricas (hosts, bosques, suelos, habitat, aspecto): union de todos los
  valores del episodio con trazabilidad de fuente (`field`/`gis`).
- Variables numericas meteorologicas: se toma la observacion de mejor `source_quality`,
  pues todas comparten meteorologia del mismo dia.
- `episode_observation_ids`: lista de IDs de observacion originales, para trazabilidad.

Observaciones sin `micro_area_id` quedan excluidas del entrenamiento: sin area
no hay clave de episodio. El campo `excluded_no_area` del artefacto registra cuantas.
`micro_area_id` ahora fluye desde la observacion hasta el artefacto de features v0
a traves de `mushroom_observation_context.py` y `mushroom_observation_features.py`.

Una no deteccion debe conservar, cuando sea posible, zona o recorrido, duracion o
nivel de esfuerzo, habitat inspeccionado y calidad del observador. Las no
detecciones casuales o sin esfuerzo conocido no deben tener el mismo valor de
entrenamiento que una busqueda dirigida en habitat compatible.

## Elegibilidad para entrenamiento

Una observacion (fila de features v0) entra al entrenamiento si cumple las cuatro
condiciones de `is_training_row` en `mushroom_learned_model.py`:

```python
validation_status == "valid"
and calibration_use == "include"
and prediction_target in {"favorable", "unfavorable"}
and micro_area_id is not None   # requerido para clave de episodio
```

### prediction_target y la politica del catalogo

`prediction_target` no se guarda directamente en la observacion: se deriva en el
momento de construir el artefacto de features, a partir de `flush_abundance` y
del campo `prediction_favorable` del catalogo `observation_flush_abundance`.

El codigo que materializa esta derivacion es `prediction_target()` en
`mushroom_observation_context.py`. Cada artefacto generado conserva el mapping
exacto y su SHA-256 para que un cambio futuro del catalogo no altere
silenciosamente la interpretacion de un modelo ya generado.

Mapeo vigente del catalogo (campo `prediction_favorable`):

| flush_abundance | prediction_favorable | prediction_target |
|-----------------|----------------------|-------------------|
| exceptional     | 1                    | favorable         |
| very_abundant   | 1                    | favorable         |
| abundant        | 1                    | favorable         |
| normal          | 1                    | favorable         |
| scarce          | 1                    | favorable         |
| very_scarce     | 0                    | unfavorable       |
| absent          | 0                    | unfavorable       |
| pending         | 0 (en catalogo)      | **excluida via calibration_use** |

La frontera operativa se fija entre `very_scarce` y `scarce`: `very_scarce`
describe hallazgos testimoniales (por ejemplo, uno o dos ejemplares) que no
justifican recomendar el desplazamiento; `scarce` ya representa una florada
pequena pero minimamente interesante. Esta decision no convierte
`unfavorable` en sinonimo de ausencia: `analysis_result` conserva por separado
si hubo carpoforos visibles.

**Sobre `pending`:** aunque el catalogo define `pending.prediction_favorable=0`,
estas observaciones nunca llegan al filtro de `prediction_target` porque el
flujo de trabajo las mantiene en `calibration_use=review`. `pending` significa
"el usuario no ha registrado todavia cuantos ejemplares encontro", no "ausencia
confirmada". En cuanto el usuario rellena la florada, `calibration_use` pasa a
`include` y la observacion entra al entrenamiento con el target correcto.

### Estado del dataset de entrenamiento (2026-08-03)

Episodios disponibles por especie tras aplicar los cuatro criterios:

| Especie                     | Ep. favorable | Ep. desfavorable | Total ep. |
|-----------------------------|---------------|------------------|-----------|
| Boletus aereus              | 31            | 21               | **52**    |
| Amanita caesarea            | 23            | 24               | **47**    |
| Boletus pinophilus          | 15            | 24               | **39**    |
| Lactarius deliciosus        | 15            |  5               | **20**    |
| Hygrophorus marzuolus       | 15            |  2               | **17**    |
| Morchella elata complex     |  4            | 13               | **17**    |
| Boletus edulis              |  5            |  9               | **14**    |
| Cantharellus cibarius s.l.  |  3            |  5               |  **8**    |
| Hygrophorus latitabundus    |  4            |  1               |  **5**    |
| Resto de especies           |  —            |  —               |  ≤2 c/u   |

Interpretacion:

- **≥20 episodios con ambas clases representadas:** B. aereus, A. caesarea,
  B. pinophilus. Son las unicas especies para las que tiene sentido intentar un
  baseline binario ahora.
- **10-19 episodios:** L. deliciosus, H. marzuolus, M. elata complex, B. edulis.
  Soporte minimo; los resultados seran ruidosos pero el pipeline puede ejecutarse
  para validar el proceso.
- **<10 episodios:** no entrenar todavia; incorporar cuando crezca el dataset.
- **Desequilibrio de clases:** H. marzuolus (15 fav / 2 desf) y L. deliciosus
  (15 fav / 5 desf) tienen muy pocos negativos; un baseline mayoritario ya da
  precision alta sin aprender nada.

Este estado se actualiza manualmente al revisar el dataset. Para regenerarlo
ejecutar el analisis de elegibilidad descrito arriba con los cuatro criterios.

## Zonas y setales conocidos

La proximidad geografica no garantiza que dos puntos pertenezcan al mismo setal
ni que fructifiquen de la misma forma. Dentro de una zona amplia, como Olvan,
puede haber varias subzonas conocidas con respuestas distintas aunque compartan
meteorologia regional y parezcan ecologicamente similares.

El modelo debe distinguir al menos tres niveles conceptuales:

```text
area general -> setal conocido -> observacion/episodio por fecha
```

Los nombres definitivos se decidiran al implementar, pero el contrato necesitara
identificadores estables equivalentes a:

- `area_id`: area geografica amplia y reconocible;
- `micro_area_id`: setal o subzona conocida con comportamiento propio;
- `episode_id`: agrupacion interna derivada de especie, setal y fecha.

La asignacion inicial de `micro_area_id` debe ser manual y revisable. No se debe
suponer que un radio fijo alrededor de unas coordenadas identifica correctamente
un setal: relieve, bosque, suelo, orientacion y discontinuidades locales pueden
separar subzonas muy proximas. En el futuro la UI podra representar una subzona
como punto, poligono o geometria privada, pero el identificador no debe depender
de que esa geometria este definida desde el primer dia.

Una misma salida al campo puede recorrer varios setales y obtener resultados
distintos. Por ejemplo, `La Pera` y `Serra de Ramons` pueden pertenecer a
`area_id=olvan` pero tener `micro_area_id` diferentes por altitud, orientacion o
microclima. Aunque se visiten el mismo dia, sus observaciones no se agrupan entre
si. La nocion humana de "salida" puede conservarse en el futuro como metadata
operativa, pero no define la unidad predictiva de la primera version.

Las coordenadas y limites de setales son datos sensibles y permanecen en los
datos locales no versionados. Los documentos y artefactos versionables solo
deben contener el contrato, nunca ubicaciones reales.

### Dos problemas predictivos diferentes

Primera fase, fructificacion en setales conocidos:

```text
area_id + micro_area_id + fecha + meteorologia diaria + contexto local
  -> probabilidad de fructificacion visible en ese setal
```

En esta fase, `area_id` y `micro_area_id` pueden aportar senales jerarquicas:
el area resume comportamiento regional y la microarea factores persistentes
locales que todavia no medimos. El objetivo es aprender cuando
responde cada setal conocido, comparando visitas positivas y no detecciones con
esfuerzo conocido.

Segunda fase, descubrimiento de nuevos setales:

```text
variables ambientales aprendidas en setales conocidos
  -> afinidad de una localizacion no conocida
```

Para esta fase no se puede depender de la identidad de `micro_area_id`. Habra que evaluar si
host, bosque, suelo, altitud, orientacion, microclima y meteorologia explican las
diferencias entre setales. Solo debe intentarse cuando el modelo de setales
conocidos tenga una validacion razonable y haya suficientes setales distintos,
no solo muchas observaciones del mismo lugar.

### Validacion espacial

Las metricas deben indicar que pregunta se esta validando:

- prediccion temporal conocida: dejar fuera episodios/fechas completas, pero
  permitir que el setal exista en entrenamiento;
- generalizacion espacial: dejar fuera `micro_area_id` completas para comprobar
  si el modelo funciona en una subzona no vista;
- descubrimiento: evaluar localizaciones nuevas confirmadas posteriormente, sin
  usar su identidad ni sus observaciones durante el entrenamiento.

Una buena precision temporal en setales conocidos no demuestra capacidad para
descubrir setales nuevos. Ambos resultados deben publicarse por separado.

## Ciclo operativo

1. Guardar o editar una observacion marca el dataset/modelo como desactualizado.
2. Una accion explicita de reconstruccion selecciona observaciones validas y
   las agrupa por especie, `micro_area_id` y fecha; `area_id` se resuelve desde
   `mushroom_known_sites.json`.
3. Para cada episodio reconstruye meteorologia diaria previa y contexto GIS/DEM.
4. Guarda la serie diaria auditable y genera las variables derivadas.
5. Construye un dataset versionado, entrena y valida el estimador.
6. Guarda modelo, contrato de features, metricas y observaciones utilizadas.
7. La prediccion no reentrena: genera las mismas features para punto/fecha y
   aplica el modelo guardado.

```text
observaciones -> reconstruccion -> dataset -> entrenamiento -> modelo
punto/fecha actual -> mismas features -> modelo guardado -> prediccion
```

### Computo externo y separacion de jobs

Home Assistant sigue siendo la fuente de verdad de observaciones, setales,
catalogos, historicos y modelos operativos aceptados. Los calculos pesados
se ejecutan en un worker Docker privado, inicialmente en el Mac M1, mediante la
plataforma descrita en `mushroom-v0-external-worker-design-es.md`.

**Implementacion actual (2026-08-03):**

- `rebuild_v0` (tipo de job `worker_candidate_rebuild`): genera el artefacto de
  features `mushroom_observation_features_v0.json` ejecutando las cuatro fases
  (GIS/DEM, meteorologia, features, modelo V0 descriptivo). Existia antes del
  entrenamiento ML.
- `ml_train_v0` (tipo de job `worker_ml_train_v0`): toma el artefacto de features
  generado por un rebuild, entrena un estimador LR+RF por especie y devuelve
  los `.joblib` y `ml_train_report.json` como un único paquete verificable. HA
  comprueba schema, rutas, tamaños, hashes y coherencia de especies; la promoción
  actualiza modelos e informe y limpia la caché del Predictor. El operador los
  promociona manualmente.
  Script: `scripts/run-mushroom-ml-train-job.py`.
  Imagen worker: instala `numpy==2.4.6 pandas==2.2.2 scikit-learn==1.9.0`.

**Separacion de jobs (diseno):** varios entrenamientos sobre el mismo artefacto de
features no repiten GIS/DEM ni meteorologia. El campo `triggered_by_job_id` esta
reservado para chaining automatico futuro (rebuild → train); de momento el trigger
es siempre manual. El `work_key` `"ml_train:v0:{features_digest}"` impide duplicar
un job activo sobre el mismo artefacto.

**Jobs futuros no implementados todavia:**

- `build_ml_dataset`: generara un `dataset_id` inmutable con particiones declaradas,
  separando la preparacion del dataset del entrenamiento.
- `evaluate_ml_model`: backtesting y comparacion de candidatos sin modificar el
  modelo activo.

El worker solo sube paquetes de resultados; no escribe directamente en `/share`.
HA valida hashes y schemas antes de aceptar el paquete. Ningun entrenamiento
promociona un modelo automaticamente.

Si los datos vivos cambian durante un entrenamiento, el run puede conservarse
como experimento reproducible ligado al snapshot y dataset originales, marcado
como no vigente. Activar un modelo requerira una accion humana explicita,
reversible y compatible con el contrato de features del runtime.

La reconstruccion V0 conservara siempre ejecucion local en HA. El entrenamiento
ML experimental no necesita fallback en la Raspberry: si el M1 no esta
disponible, puede permanecer en cola sin afectar a la aplicacion ni al modelo
activo.

## Variables consideradas

La lista de esta seccion es un catalogo de variables candidatas, no el conjunto
que debe entrar completo en el primer modelo. Hay que separar:

```text
serie reconstruida completa -> variables candidatas -> subconjunto de entrenamiento
```

La reconstruccion conserva detalle porque volver a consultar historicos puede
ser costoso y porque permite probar hipotesis posteriores. El entrenamiento
inicial debe usar pocas variables para reducir sobreajuste, especialmente con la
muestra actual.

Primer subconjunto orientativo, limitado a unas 8-10 variables:

- compatibilidad de bosque o formacion forestal;
- compatibilidad de hospedador;
- lluvia acumulada 7 y 21 dias;
- una medida de concentracion/distribucion de la lluvia;
- temperatura media en 7 dias;
- variabilidad termica en 7 dias;
- altitud;
- mes circular, representado por seno y coseno.

**Sobre hosts y variables categoricas en el modelo V0 actual:** el modelo V0 no
tiene limite de hosts ni aplica seleccion de variables. Para cada host calcula
`positive_support`, `negative_support` y `ratio_delta` de forma independiente.
Cuantos mas hosts distintos, mas filas en la tabla descriptiva, pero no hay
penalizacion ni problema de dimensionalidad porque el V0 no es un estimador
estadistico. El unico riesgo es interpretativo: un host con soporte 1/0 tiene
`ratio_delta=+1.0` que no significa nada — hay que mirar siempre el soporte.

Para el modelo ML real (segunda fase) si habra que tomar decisiones: agrupar hosts
raros en una categoria "other", usar codificacion one-hot o embeddings, y aplicar
seleccion de features para evitar sobreajuste con muestras pequeñas. Con el dataset
actual esto es prematuro; conviene esperar a tener el conjunto confirmado tras
revisar las 646 observaciones en estado `review`.

La cobertura/calidad meteorologica se conserva para aceptar, rechazar o ponderar
episodios y para interpretar resultados. No tiene que entrar como predictor del
fenomeno biologico en el primer modelo.

Este subconjunto tampoco queda aprobado de forma automatica. Cada variable se
mantendra solo si puede calcularse con cobertura suficiente y aporta mejora en
validacion sobre episodios no vistos. Las variables nuevas se incorporaran de
forma incremental y se compararan contra el baseline anterior. Con muestras
pequenas no se hara seleccion masiva entre decenas de features usando el mismo
test final, porque produciria resultados optimistas por sobreajuste.

### Serie meteorologica diaria

**Ventana acordada (2026-08-03): 30 dias de datos diarios.** El ciclo completo
de inicio-maximo-fin de una florada dura aproximadamente 2 semanas; datos de
hace 60-90 dias pertenecen a un ciclo distinto y anaden ruido. Los acumulados
largos (60/90 d) quedan fuera del artefacto de entrenamiento ML.

Datos diarios almacenados (30 dias previos a cada episodio):
- lluvia diaria (mm);
- temperatura minima, maxima y media diaria (grados C);
- humedad minima, maxima y media diaria (%).

Acumulados comprimidos conservados (ventanas cortas utiles como features directas):
- acumulados 7/14/21/30 dias de lluvia, temperatura y humedad.

Los acumulados de 60/90 dias del artefacto v0 actual se eliminan del contrato
de features v1 ML.

**Features derivadas acordadas (2026-08-03)** — calculadas durante el rebuild
a partir de la serie diaria antes de descartar el detalle diario:

De lluvia:
- `dry_spell_days`: dias consecutivos sin lluvia inmediatamente antes del episodio;
- `days_since_significant_rain`: dias desde el ultimo evento mayor o igual a 5 mm;
- `rainy_days_14d`: numero de dias con lluvia mayor a 2 mm en los ultimos 14 dias
  (captura si la lluvia fue distribuida o concentrada en un aguacero puntual).

De temperatura:
- `thermal_amplitude_mean_7d`: media de (temp_max menos temp_min) por dia en los
  ultimos 7 dias;
- `thermal_amplitude_mean_14d`: idem para 14 dias;
- `thermal_trend`: temp_mean_7d menos media de temp_mean de los dias 8-30
  (negativo = enfriando, positivo = calentando);
- `heat_stress_days`: dias consecutivos con temperatura maxima mayor a 28 grados C
  inmediatamente antes del episodio.

De humedad:
- `high_humidity_days_14d`: dias con humedad media mayor a 80% en los ultimos 14 dias.

**Razon de estas features:** el modelo puede aprender patrones que las sumas
acumuladas no expresan directamente, como la presencia de sequia reciente, si
esta enfriando, o si la lluvia fue en un dia o repartida. El umbral exacto
(28 grados, 5 mm, 2 mm, 80%) no debe tratarse como verdad calibrada: son
puntos de partida razonables que el modelo puede confirmar o ignorar.

**El modelo no sabe de antemano que ventana meteorologica importa para cada
especie.** Por eso se le proporcionan ventanas multiples (7/14/21/30 dias) y
features derivadas: el modelo descubrira cuales tienen poder predictivo real
para cada especie sin que se pre-impongan hipotesis sobre los tiempos de
respuesta del micelio.

No se fijaran umbrales por intuicion. Si se usan variables basadas en umbral,
el valor debe aprenderse dentro del entrenamiento o declararse como umbral
experimental y validarse sin fuga de datos.

### Contexto espacial y ecologico

- altitud y orientacion;
- host, bosque, tendencia de suelo y habitat;
- procedencia separada `field` y `gis`;
- compatibilidad de cada senal con el perfil v0 aceptado de la especie;
- gaps de GIS y mappings no aceptados.

Las asociaciones bibliograficas con encinares, fagaceas, castano u otros
ambientes mediterraneos respaldan estas variables como senales prioritarias, no
como filtros universales. Un habitat no documentado no se convierte
automaticamente en incompatible y los pesos deben aprenderse con datos locales.

La termofilia ecologica y la temperatura meteorologica reciente se modelan como
conceptos distintos:

- aptitud termica general del lugar, apoyada por habitat, altitud y exposicion;
- secuencia de temperaturas antes del episodio, cuyo efecto temporal es una
  hipotesis que debe aprender el estimador.

### Tiempo y fenologia

- mes y dia del ano con codificacion circular seno/coseno;
- ano;
- pertenencia a mes principal o secundario del perfil;
- patron estacional aceptado.

La literatura permite fructificacion estival de `boletus_aereus`, incluidos
julio y agosto en un seguimiento iberico, pero no impone una ventana fija. La
codificacion circular permite que la fenologia regional se aprenda desde las
observaciones sin restringir el modelo al otono.

## Registro de evidencia por variable

El contrato de features debe mantener, para cada variable o familia:

- justificacion bibliografica o tecnica;
- estado `priority`, `candidate` o `experimental`;
- fuente de datos y cobertura;
- efecto esperado solo como hipotesis, sin peso impuesto;
- evidencia local y resultado de validacion;
- version en la que entro o salio del subconjunto entrenado.

## Dataset y artefactos previstos

Los nombres definitivos se fijaran al implementar, pero deben separar claramente
serie reconstruida, matriz de entrenamiento y modelo:

```text
mushroom_ml_daily_context_v0.json
mushroom_ml_training_dataset_v0.json
mushroom_ml_model_v0.json
mushroom_ml_evaluation_v0.json
```

Los artefactos operativos locales viven bajo
`docker-data/mushroom-data/`; en HA equivaldran a
`/share/rainmapper/mushroom-data/`. No se versionan observaciones, coordenadas,
historicos ni modelos entrenados con datos reales.

Cada build debe registrar:

- version del contrato de features;
- especie y objetivo;
- areas, setales conocidos, episodios y observaciones utilizados;
- fecha de generacion;
- cobertura y gaps;
- algoritmo e hiperparametros;
- particiones de entrenamiento/validacion;
- metricas y baseline comparado.

## Entrenamiento y validacion

**Eleccion de algoritmo (2026-08-03):** el objetivo no es solo clasificar sino
descubrir que features y que ventanas temporales importan para cada especie.
Por eso se usan dos modelos complementarios:

1. **Regresion logistica regularizada (L1/L2):** baseline interpretable.
   Los coeficientes muestran directamente que variables empuja hacia favorable
   o desfavorable. Util para detectar si el modelo aprende algo con sentido.
2. **Random forest o gradient boosting:** captura relaciones no lineales
   (por ejemplo, "necesita lluvia Y temperatura baja, no solo una de las dos")
   y produce importancia de features que revela que ventanas y derivadas usa
   el modelo. Preferible cuando el numero de features supera ~20.

Con ~50 features (30 dias diarios + acumulados + derivadas) y 50-60 episodios
por especie, ambos modelos necesitan regularizacion agresiva. No usar redes
neuronales ni modelos temporales complejos con la muestra actual.

La separacion de validacion se hara por `episode_id`, fecha o `micro_area_id`,
nunca por observacion aleatoria. Observaciones correlacionadas del mismo setal y
fecha no pueden quedar a ambos lados de la particion.

**Politica implementada de ajuste y evaluacion (2026-08-10):** el corte
cronologico 70/30 se conserva como una evaluacion adicional: los episodios mas
antiguos entrenan un modelo temporal efimero y los mas recientes lo validan. Si
cualquiera de los dos tramos contiene una sola clase, esa evaluacion se marca
explicitamente como no disponible y no aborta el entrenamiento.

La validacion cruzada estratificada usa todos los episodios elegibles, sin
separar observaciones del mismo episodio, y reduce automaticamente el numero de
folds al tamano de la clase minoritaria. Tras calcular las metricas, los modelos
productivos LR y RF se ajustan de nuevo con todos los episodios elegibles. De
esta forma las observaciones recientes, incluidas las no detecciones que antes
no se registraban, participan en el modelo operativo sin presentar una
comprobacion retrospectiva como si fuera validacion hacia delante.

El primer modelo se validara para setales conocidos. La evaluacion por setal
completo se incorporara cuando haya suficientes `micro_area_id` diferentes para
que la prueba tenga sentido.

Metricas minimas:

- distribucion de clases;
- calidad y esfuerzo de las no detecciones;
- baseline mayoritario;
- precision, recall y matriz de confusion;
- ROC-AUC o PR-AUC solo cuando ambas clases y el tamano de muestra lo permitan;
- coeficientes/importancia de variables;
- resultados por particion y advertencias de muestra insuficiente.

La evaluacion debe rechazar o etiquetar claramente como no fiable un modelo sin
negativos suficientes, sin particion valida o con cobertura meteorologica pobre.

El entrenamiento del 2026-08-10 confirmó que este requisito todavía no se
cumple en el Predictor operativo. Para Aereus, LR y RF obtuvieron ROC-AUC
temporal de `0,3818` y `0,4545`; aun así se combinaron al 50% y se mostraron
como probabilidad normal. El análisis reproducible, las causas y los criterios
de sustitución están en `mushroom-ml-model-hardening-plan-es.md`.

Desde la fase experimental posterior, el mismo job entrena además bundles
**shadow** para `fixed_gap_7d_v1` y `lag_event_v1`. Se guardan junto al modelo
operativo y su informe queda anidado en `shadow_experiments`, pero no alteran la
recomendación oficial. Su contrato temporal, métricas comunes y uso en el
laboratorio del Predictor se definen en
`mushroom-ml-experiment-contract-es.md`.

## Criterio del primer hito

El primer hito no es publicar un mapa predictivo. Es conseguir, empezando
por las especies con mas observaciones (B. edulis / B. aereus, 152/151 obs),
un proceso reproducible que:

1. permita asignar manualmente cada observacion a un setal conocido;
2. agrupe observaciones por especie, setal y fecha;
3. reconstruya y conserve meteorologia diaria desde Meteocat (corte 2018+);
4. genere siempre el mismo contrato de features para entrenamiento y prediccion;
5. entrene un baseline binario sin fuga entre episodios;
6. publique metricas honestas y explique por que el resultado es o no usable.

Una vez validado el proceso con una especie, el mismo pipeline se aplica al
resto de las 8 especies viables sin cambiar el contrato de features.

## Store de areas conocidas

La jerarquia privada se mantiene en `mushroom_known_sites.json`. Las
observaciones guardan solo `micro_area_id`; el `area_id` padre se resuelve desde
el store para evitar duplicacion e inconsistencias.

El contrato reserva desde el inicio campos opcionales para nombres/aliases,
ubicacion administrativa, coordenada representativa, geometria GeoJSON,
precision, altitud, topografia, ecologia, acceso, procedencia, notas, archivado y
metadata. No son obligatorios para crear una microarea y podran completarse
progresivamente o mediante reconstruccion GIS.
