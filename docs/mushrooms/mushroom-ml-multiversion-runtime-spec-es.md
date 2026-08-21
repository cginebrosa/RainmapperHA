# Runtime multiversión V2–V6 para Predictor, HA y worker

Estado: **DESPLEGADO INICIALMENTE EN HA 0.2.256 / WORKER 1.0.10; CORRECCIÓN DE
REGENERACIÓN Y TRAZABILIDAD EN VALIDACIÓN LOCAL**.

Versiones de software reservadas para esta integración: HA `0.2.256` y worker
`1.0.10`. Los artefactos anteriores HA `0.2.255` y worker `1.0.9` se saltan y
no se instalarán. Reservar la numeración no autoriza build, publicación,
instalación ni promoción de modelos.

## Objetivo

La siguiente pareja HA/worker debe conservar V2, V3, V4, V5 y V6 como modelos
reales y seleccionables cuando exista una generación entrenada compatible. El
modo normal usa exclusivamente la generación activa. El modo Comparar ejecuta
las referencias elegidas y muestra sus probabilidades y explicaciones. Una
referencia ausente, incompatible o corrupta se marca como no disponible con su
motivo; nunca se sustituye silenciosamente por V2.

No se calcula consenso medio ni ensemble entre versiones. La comparación
presenta cada miembro individual y su calidad hold-out. Un ensemble futuro solo
podrá añadirse como otro estimador si se ha comparado contra el mejor miembro
individual por especie y contrato.

## Vocabulario (versión, perfil, estimador, modelo, generación, batch)

De mayor a menor nivel:

- **Versión** (`version_id`): el diseño completo, p. ej. `biology_v4` o
  `biology_v5_windowed_raw_weather`. Define qué perfiles tiene, qué
  contratos temporales usa y qué estimadores permite. Es lo que se muestra
  como "Biology V4" en las pantallas.
- **Perfil** (`profile_id`): una variante técnica dentro de una versión.
  `biology_v4` tiene dos perfiles (`extended_weather`, `climatic_balance`);
  `biology_v5_windowed_raw_weather` tiene tres (ventana 30d/60d/90d). Una
  versión "completa" exige tener instalados todos sus perfiles a la vez.
- **Contrato temporal** (`temporal_contract_id`): `fixed_gap_7d` (ventana
  ciega fija de 7 días) o `lag_event` (modelo de retardos/eventos, admite
  horizontes 1..7 con un único ajuste, ver "Identidad canónica" abajo). Cada
  perfil se entrena para ambos.
- **Estimador/algoritmo** (`estimator_id`): la técnica de ML concreta — LR,
  RF, ET, HGB, KNN, SVM, o los propios de V5/V6 (sparse-group, suave...). Un
  mismo perfil se ajusta con varios estimadores a la vez y se elige el de
  menor Brier validado que mejora la prevalencia.
- **Modelo/artefacto**: el objeto entrenado concreto para una combinación
  exacta de versión + perfil + contrato + especie + estimador
  (`artifact_ref`, ver abajo). Una generación contiene cientos de estos —
  todas las especies × todos los estimadores × ambos contratos × cada
  perfil de la versión.
- **Generación** (`generation_id`): el conjunto completo de todos esos
  modelos, entrenados juntos en una misma pasada, para **todos** los
  perfiles de una versión. Es lo que se instala o se retira como unidad.
- **Batch** (`batch_id`): el directorio físico en disco
  (`ml_models/batches/<batch_id>/`) donde viven los ficheros serializados de
  una generación y su manifiesto.

Resumen: **Versión → Perfiles → (Contrato × Especie × Estimador) → Modelos
individuales**; todos los modelos de una versión entrenados juntos forman
**una Generación**, guardada en **un Batch**. Ver también
`docs/mushrooms/mushroom-ml-multi-version-installation-design-es.md` para el
diseño (propuesto, no implementado) de varias versiones instaladas a la vez.

## Cuatro disponibilidades distintas

- `catalog_visible`: el contrato aparece en el catálogo explicativo.
- `benchmark_runnable`: se puede reconstruir y evaluar localmente.
- `comparison_eligible`: existe un artefacto exacto, compatible y evaluado que
  puede ejecutarse en Comparar.
- `operational_eligible`: además ha superado el gate de promoción y puede ser la
  única generación activa del modo normal.

Que V3–V6 sean visibles no implica que finjan una predicción. Hasta que el batch
multiversión se entrene, su estado será «sin generación instalada».

## Identidad canónica

Una predicción queda identificada por un `model_ref` inmutable:

```text
batch_id
generation_id
version_id
temporal_contract_id
profile_id
estimator_id
species_id
horizon_days
```

`fixed_gap` solo admite horizonte 7. `lag_event` admite todos los horizontes
enteros `1..7`, pero cada especie+contrato+perfil+estimador tiene un único
ajuste: los siete horizontes seleccionan filas o valores de `horizon_days` del
mismo modelo y nunca crean siete entrenamientos.

Por ello el manifiesto distingue `artifact_ref` (la misma identidad sin
`horizon_days`) de `model_ref` (una consulta predictiva concreta). Un artefacto
lag declara `supported_horizons=[1,2,3,4,5,6,7]` y aparece una sola vez en disco.
Los cortes `1/2/3/7` pueden conservarse como resumen diagnóstico de calidad,
pero no limitan las fechas que el Predictor puede resolver durante la semana.

`group_days=7/14` pertenece únicamente a la partición del benchmark. No forma
parte de `model_ref` ni del runtime. El retardo meteorológico raw 0–364 tampoco
es el horizonte de predicción.

## Catálogo inicial

| Versión | Perfil runtime | Estimadores | Modo normal |
|---|---|---|---|
| V2 `altitude_v2` | `common_idw` | LR, RF, ET, HGB, KNN, SVM | sí, mientras sea activa |
| V3 `biology_v3` | `core` | LR, RF, ET, HGB, KNN, SVM | no sin promoción |
| V4 `biology_v4` | `extended_weather`, `climatic_balance` | LR, RF, ET, HGB, KNN, SVM | no sin promoción |
| V5 `biology_v5_raw_weather_discovery` | `raw_primary_plus_physical_state` | Elastic Net, sparse-group | no sin promoción |
| V6 `biology_v6_smooth_hierarchical` | `smooth_weather_physical_state` | suave por especie, compartido, pooling parcial | no sin promoción |

V4 `core`, las variantes SoilGrids y las ablaciones V5 quedan reconstruibles en
el laboratorio, pero no multiplican el catálogo ordinario: V4 core duplica V3
y las restantes no superaron los benchmarks actuales.

## Paridad meteorológica del Predictor

El Predictor no lee una estación concreta para ninguna V2–V6. Para cada fecha
de corte materializa el IDW multifuente diario de cada microárea usando las
fuentes habilitadas. ET0, balance hídrico y SMI se calculan después desde ese
IDW solo cuando el perfil exacto instalado declara variables físicas: omitir
trabajo que el bundle no consume no elimina esa capacidad. V2/V3 actuales usan
90 días IDW sin estado físico; V4 usa 90 días y activa físicos únicamente en
sus perfiles correspondientes; V5/V6 conservan su eje experimental de 365
días y consumen estado físico. V5 recibe los ocho canales diarios y los
resúmenes SMI; V6 aplica sus bases suaves sobre esos mismos ocho canales y
conserva los escalares físicos. El registro, el entrenador y el adaptador de
inferencia deben resolver el mismo perfil y el mismo orden exacto de columnas.
Si el runtime no puede reproducir ese contrato, debe abstenerse: no puede
sustituir ausencias por cero ni degradar a meteorología de una sola estación.
El bundle remoto incluye además `stations.txt`; así el worker aplica la misma
lista de estaciones Wunderground habilitadas/deshabilitadas que HA. Omitir ese
fichero cambia las fuentes del IDW y rompe la paridad aunque los Parquet sean
idénticos.

Una variante futura V2/V3 `IDW + balance/SMI` debe registrarse, entrenarse y
evaluarse como perfil o contrato diferente. La implementación física permanece
disponible para ese experimento; está prohibido inyectar nuevas columnas en los
bundles V2/V3 actuales o presentarlas como si hubieran formado parte de su
entrenamiento.

## Batch y almacenamiento

Un `batch_id` agrupa generaciones producidas desde exactamente el mismo
`snapshot_id=sha256:...`. El manifiesto enumera todos los artefactos y hashes.
La ruta se deriva del `model_ref`, no de nombres legacy:

```text
batches/<batch>/generations/<generation>/<version>/<temporal>/<profile>/<estimator>/<species>.joblib
```

El batch nuevo se escribe en staging, se verifica por hash y contrato y solo
entonces se instala atómicamente. El batch anterior permanece como rollback.
Una activación parcial que mezcle snapshots está prohibida. Tras una instalación
verificada, la copia temporal recibida desde el worker se elimina; si falla la
verificación, se conserva para diagnóstico.

El batch conserva además `training-input-manifest.json`, una identidad pequeña
y verificable de las entradas usadas. Contiene hashes, tamaños, identidad del
histórico meteorológico y del dataset GIS, pero no incorpora observaciones,
parquets, predicciones hold-out, modelos ni rutas privadas del host. Su SHA-256
queda referenciado por el manifiesto del batch.

## Reconstrucción y entrenamiento

La reconstrucción común materializa una sola vez:

1. snapshot inmutable de observaciones, known sites, perfiles e histórico;
2. catálogo y serie meteorológica IDW común por microárea;
3. agregados por área y cortes diarios de hasta 365 días;
4. datasets V2–V6 derivados de esa caché.

El entrenamiento multiversión consume esos datasets. El job ordinario ajusta
solo los perfiles del catálogo; el benchmark científico completo añade
particiones 7/14, campañas, remuestreos y reportes y se ejecuta aparte. Así no
se recalcula IDW cinco veces ni se convierte cada regeneración de datos en un
benchmark largo.

En el flujo instalado, «Reconstruir y reentrenar todo» encadena necesariamente
la reconstrucción común, el entrenamiento ML v0 y el lote V2–V6. Los
constructores V3/V4/V5 preparan filas y variables; V2 y V6 también consumen la
misma generación de entradas y todos los estimadores se vuelven a ajustar. No
se ofrece una regeneración parcial de comparación: mientras todas las versiones
sigan habilitadas, la coherencia con la última observación y con el histórico
meteorológico aceptado exige completar la cadena entera.

Cuando el worker externo termina y HA verifica el lote V2–V6 enlazado, el
coordinador inicia automáticamente la promoción de la generación completa. No
existe una espera humana entre cálculo y promoción: esa espera permitía que una
actualización meteorológica programada invalidase un candidato ya terminado.
La automatización reutiliza, sin omitirlos, el chequeo de frescura de todas las
entradas, la instalación atómica, el rollback y la invalidación de caché. Si las
entradas cambian durante el cálculo, la promoción se rechaza y no se relanza
automáticamente el trabajo pesado. Las reconstrucciones parciales y los
experimentos no enlazados conservan su promoción explícita cuando corresponda.

## Predictor y explicaciones

El modo normal conserva ranking, semana, consulta e histórico con una única
generación activa. Comparar añade selector de versión, temporal, perfil y
estimador, muestra disponibilidad real y ejecuta referencias exactas.

Cada resultado conserva dos capas:

- explicación ecológica común: corte, horizonte, fase de florada, lluvia,
  temperatura, humedad, balance y cobertura usados por el contrato;
- explicación estadística específica: probabilidad, soporte hold-out por
  especie/contrato, Brier frente a prevalencia y fenología, dominio de variables
  y motivo de exclusión.

La UI resume antes del detalle cuatro grupos mutuamente excluyentes: miembros
utilizables (en dominio y mejores que prevalencia), disponibles en dominio con
evidencia débil, extrapolaciones/no utilizables y abstenciones por entradas
meteorológicas incompletas. Las tablas por algoritmo quedan como diagnóstico
plegable. Un `runtime_feature_gates_failed` causado por cobertura no se presenta
como avería del modelo: muestra el corte meteorológico observado que todavía
debe completarse. En una consulta futura, h1..h7 son fechas de emisión distintas
del mismo modelo `lag_event`; la UI no supone que exista meteorología observada
posterior a hoy.

V5/V6 no fingirán una importancia causal de cada día. Mostrarán resúmenes por
banda y, cuando proceda, coeficientes o curvas estables con la advertencia de
que son diagnósticos de asociación.

Antes de renderizar el Predictor, HA compara la identidad del batch instalado
con las observaciones y entradas históricas actuales. Si cambian, muestra un
aviso de que las predicciones no incorporan todavía toda la información y pide
una reconstrucción y reentrenamiento completos. Los lotes antiguos que no
guardan identidad se muestran como «vigencia no verificable», nunca como
actuales por suposición. El chequeo no confunde meteorología futura de una
consulta con datos históricos de entrenamiento.

## Compatibilidad HA/worker

HA coordina catálogo, snapshot, jobs, manifests, activación, rollback y UI. El
worker declara capacidades explícitas para entrenamiento e inferencia
multiversión. HA solo le asigna un job si entiende su versión de contrato. Si
no hay worker compatible, el fallback local debe ejecutar el mismo contrato y
manifest, no otra implementación.

## Gates antes de release

- catálogo y `model_ref` validados sin listas V2–V6 hardcodeadas en la UI;
- adaptadores train/inferencia con paridad por perfil;
- un único ajuste lag y proyección operativa 1..7 comprobados por tests;
- batch atómico, hash, incompatibilidad y rollback probados;
- Comparar mantiene explicaciones y no promedia versiones;
- worker anuncia capacidades reales y HA las exige;
- suite completa y smoke test locales;
- ningún modelo operativo, HA real, GHCR o release se modifica durante esta
  implementación local.

## Regla de empaquetado

Las imágenes HA y worker contienen código, dependencias y defaults públicos.
HA incluye una plantilla de observaciones vacía para instalaciones nuevas; no
contiene registros de observación, snapshots canónicos, benchmarks, hold-outs
ni modelos entrenados. Las entradas reales se congelan en HA al lanzar el trabajo,
se transfieren al worker mediante el contrato autenticado y se descartan al
terminar. Reducir la imagen elimina herramientas de compilación o cachés
innecesarios; no elimina información del dataset, porque esa información nunca
debe formar parte de la imagen pública.
