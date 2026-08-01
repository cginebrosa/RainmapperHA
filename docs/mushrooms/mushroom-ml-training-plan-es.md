# Plan de reconstruccion y entrenamiento ML de setas

Este documento define la direccion acordada para construir un modelo de machine
learning basado en observaciones reales. El `mushroom_model_v0.json` actual es
descriptivo: resume soporte, rangos y gaps, pero no entrena un estimador ni
produce probabilidades. El modelo ML sera un artefacto separado.

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

Primer objetivo: clasificacion binaria de fructificacion visible:
`not_detected_with_known_search=0`, `detected=1`.
Evolucion posterior: abundancia ordinal desde `absent` hasta `exceptional`.

Las primeras salidas seran experimentales y no se presentaran como predictor
fiable mientras la validacion y el numero de negativos sean insuficientes.

Las visitas negativas reales son especialmente importantes: no deben
fabricarse ausencias desde fechas o lugares que no se visitaron. Con el
dataset actual predominan las observaciones positivas; hay que priorizar el
registro de no detecciones con esfuerzo conocido.

El objetivo no es predecir presencia biologica o micelio. Una visita sin
carpoforos visibles es una no deteccion condicionada por el esfuerzo de busqueda,
no una demostracion de ausencia de la especie.

## Unidad de entrenamiento

La unidad no debe ser cada registro aislado, sino un episodio independiente:

```text
especie + micro_area_id + fecha
```

Varias observaciones de la misma florada no deben aparecer como ejemplos
independientes, tengan o no fotografia asociada.
El dataset generara un `episode_id` interno y reproducible desde esos campos. No
es necesario pedir al usuario un identificador de salida.

Una no deteccion debe conservar, cuando sea posible, zona o recorrido, duracion o
nivel de esfuerzo, habitat inspeccionado y calidad del observador. Las no
detecciones casuales o sin esfuerzo conocido no deben tener el mismo valor de
entrenamiento que una busqueda dirigida en habitat compatible.

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

Home Assistant seguira siendo la fuente de verdad de observaciones, setales,
catalogos, historicos y modelos operativos aceptados. Los calculos pesados
podran ejecutarse en un worker Docker privado, inicialmente en el Mac M1,
mediante la plataforma descrita en
`mushroom-v0-external-worker-design-es.md`.

El flujo remoto no sera un unico job monolitico:

1. `build_ml_dataset` genera contexto diario, episodios, features y un
   `dataset_id` inmutable a partir de un `snapshot_id` de HA;
2. `train_ml_model` reutiliza ese dataset con algoritmo, variables,
   particiones, hiperparametros y semilla declarados;
3. `evaluate_ml_model` compara candidatos o ejecuta backtesting sin modificar
   el modelo activo.

De este modo varios entrenamientos no repiten GIS/DEM, meteorologia ni
transferencia de datos vivos. El worker solo sube paquetes de resultados; no
escribe directamente en `/share`. HA valida hashes, schemas y compatibilidad y
registra el resultado como candidato. Ningun entrenamiento promociona un modelo
automaticamente.

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

Conservar la serie diaria original, inicialmente hasta 60-90 dias previos, con
fuente, estacion, distancia, cobertura, gaps y valores sospechosos.

Lluvia:

- lluvia diaria reciente;
- acumulados 3/7/14/21/30/60/90 dias;
- maximo diario y numero de dias con lluvia;
- dias desde la ultima lluvia;
- racha seca reciente y maxima;
- concentracion de lluvia en los 1/3/5 dias mas lluviosos;
- variabilidad diaria y distribucion temporal.

Temperatura:

- minima, maxima y media diaria;
- medias, minimos y maximos en 3/7/14/21/30 dias;
- amplitud termica diaria;
- variabilidad entre dias;
- mayor subida y bajada entre dias consecutivos;
- tendencia reciente.

Humedad, cuando haya cobertura suficiente:

- media, minima y maxima;
- medias y variabilidad en 7/14/21/30 dias;
- secuencias diarias y gaps.

La humedad relativa y un futuro balance hidrico son variables candidatas, no
predictores demostrados especificamente para `boletus_aereus`. Pueden representar
conservacion de agua o secado, pero deben justificar su permanencia mediante
validacion local.

No se fijaran umbrales de lluvia, temperatura o cambio brusco por intuicion. Si
se prueban variables basadas en umbral, el valor debe aprenderse dentro del
entrenamiento o declararse como umbral experimental y validarse sin fuga de
datos.

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

El primer baseline sera una regresion logistica regularizada. Se podra comparar
con un arbol pequeno u otro modelo tabular explicable cuando haya muestra
suficiente. No usar redes neuronales ni modelos temporales complejos con la
muestra actual.

La separacion de validacion se hara por `episode_id`, fecha o `micro_area_id`,
nunca por observacion aleatoria. Observaciones correlacionadas del mismo setal y
fecha no pueden quedar a ambos lados de la particion.

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
