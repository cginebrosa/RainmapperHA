# Runtime multiversión V2–V6 para Predictor, HA y worker

Estado: **CONTRATO IMPLEMENTADO EN EL LABORATORIO LOCAL; PENDIENTE DE
REVALIDACIÓN FINAL Y DE CUALQUIER DESPLIEGUE REAL**.

La reserva inicial de esta integración fue HA `0.2.256` y worker `1.0.10`; es
un dato histórico, no la versión actual. Las versiones declaradas vigentes se
consultan en `docs/codex-start-here.md` y el runtime real se revalida en cada
sesión. Ninguna numeración autoriza build, publicación, instalación ni
promoción de modelos.

Desde el 2026-08-23, «promoción» en este contrato significa exclusivamente la
instalación automática y conjunta del mantenimiento completo. Los benchmarks
son evidencia `evidence_only` y no ofrecen preparación, activación ni rollback
manual por versión.

## Objetivo

HA y worker deben conservar V2, V3, V4, V5 y V6 como modelos reales y
seleccionables cuando exista una generación entrenada compatible. El modo
normal usa exclusivamente la generación preferida. El modo Comparar ejecuta
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
  mismo perfil se ajusta con varios estimadores a la vez. En operación solo
  compiten los aplicables, con Brier mejor que prevalencia y ROC-AUC >= 0,55;
  el ranking se define más abajo.
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
diseño ya implementado en el laboratorio local de varias versiones instaladas
a la vez. Su despliegue en HA real sigue siendo una operación independiente.

## Cuatro disponibilidades distintas

- `catalog_visible`: el contrato aparece en el catálogo explicativo.
- `benchmark_runnable`: se puede reconstruir y evaluar localmente.
- `comparison_eligible`: existe un artefacto exacto, compatible y evaluado que
  puede ejecutarse en Comparar.
- `operational_eligible`: además cumple integridad y contrato y puede instalarse
  como generación operativa de su versión; ser preferida es un puntero aparte.

Que V3–V6 sean visibles no implica que finjan una predicción. Cuando una versión
no tenga un batch multiversión compatible, su estado será «sin generación
instalada».

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
| V2 `altitude_v2` | `common_idw` | LR, RF, ET, HGB, KNN, SVM | sí si está instalada |
| V3 `biology_v3` | `core` | LR, RF, ET, HGB, KNN, SVM | sí si está instalada |
| V4 `biology_v4` | `extended_weather`, `climatic_balance` | LR, RF, ET, HGB, KNN, SVM | sí si está instalada |
| V5 `biology_v5_windowed_raw_weather` | `raw_window_30d/60d/90d_plus_physical_state` | Elastic Net, sparse-group | sí si está instalada |
| V6 `biology_v6_windowed_smooth_hierarchical` | `smooth_window_30d/60d/90d_plus_physical_state` | suave por especie, compartido, pooling parcial | sí si está instalada |

V4 `core`, las variantes SoilGrids y las ablaciones V5 quedan reconstruibles en
el laboratorio, pero no multiplican el catálogo ordinario: V4 core duplica V3
y las restantes no superaron los benchmarks actuales.

Las definiciones anteriores `biology_v5_raw_weather_discovery` y
`biology_v6_smooth_hierarchical`, que sí usaban 365 días como ventana
predictiva completa, permanecen por ahora con `status: reference` únicamente
por compatibilidad y reproducibilidad histórica. No son versiones operativas
promocionables. Su retirada definitiva del registro, adaptadores, ramas de
compatibilidad y pruebas legacy queda pendiente; antes deberá comprobarse que
ninguna generación instalada, puntero, manifiesto o ruta de runtime las
referencia. Retirar esos contratos no implica borrar los informes de benchmark
ya archivados, cuya conservación o migración se decidirá explícitamente.

## Paridad meteorológica del Predictor

El Predictor no lee una estación concreta para ninguna V2–V6. Para cada fecha
de corte materializa el IDW multifuente diario de cada microárea usando las
fuentes habilitadas. ET0, balance hídrico y SMI se calculan después desde ese
IDW solo cuando el perfil exacto instalado declara variables físicas: omitir
trabajo que el bundle no consume no elimina esa capacidad. V2/V3 actuales usan
90 días IDW sin estado físico; V4 usa 90 días y activa físicos únicamente en
sus perfiles correspondientes. Las V5/V6 operativas son las variantes
`windowed`: cada una ofrece perfiles predictivos de 30, 60 y 90 días. V5
introduce únicamente los retardos de meteorología cruda incluidos en la ventana
elegida; V6 construye sus bases suaves sobre esa misma ventana. Ambas añaden
los escalares de estado físico compartidos, pero no introducen como variables
predictivas los 365 canales diarios completos.

`weather_lookback_days=365` y `predictive_window_days=30|60|90` representan
dos necesidades distintas. Los 365 días son el histórico causal de
calentamiento usado por los perfiles que declaran estado físico para derivar
ET0, balance hídrico, fracción de agua del suelo/SMI y sus resúmenes. La ventana
30/60/90 determina qué retardos meteorológicos puede consumir el modelo. Por
tanto, el histórico físico de 365 días puede prepararse o cachearse una vez y
compartirse entre perfiles, mientras que cada contrato predictivo debe recibir
solo sus columnas exactas. Los perfiles que no incluyen estado físico no deben
solicitar esos 365 días por defecto.

El registro, el entrenador y el adaptador de inferencia deben resolver el mismo
perfil y el mismo orden exacto de columnas.
Si el runtime no puede reproducir ese contrato, debe abstenerse: no puede
sustituir ausencias por cero ni degradar a meteorología de una sola estación.
El bundle remoto incluye además `stations.txt`; así el worker aplica la misma
lista de estaciones Wunderground habilitadas/deshabilitadas que HA. Omitir ese
fichero cambia las fuentes del IDW y rompe la paridad aunque los Parquet sean
idénticos.

La reducción predictiva V5/V6 a 30/60/90 ya está implementada y evaluada. La
optimización pendiente es evitar releer o transportar repetidamente el mismo
histórico físico de 365 días: podrá resolverse mediante caché incremental o
materialización de los escalares, manteniendo identidad, causalidad y paridad
entre entrenamiento e inferencia. Runtime y entrenamiento deben seguir
reproduciendo exactamente tanto la ventana predictiva como el calentamiento
físico declarados por cada generación.

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
entonces se instala atómicamente. El batch anterior permanece como rollback
transaccional solo hasta confirmar la instalación y después se elimina; no se
mantiene un historial operativo de generaciones.
Una activación parcial que mezcle snapshots está prohibida. Tras una instalación
verificada, la copia temporal recibida desde el worker se elimina; si falla la
verificación, se conserva para diagnóstico.

El batch conserva además `training-input-manifest.json`, una identidad pequeña
y verificable de las entradas usadas. Contiene hashes, tamaños, identidad del
histórico meteorológico y del dataset GIS, pero no incorpora observaciones,
parquets, predicciones hold-out, modelos ni rutas privadas del host. Su SHA-256
queda referenciado por el manifiesto del batch.

El manifiesto incorpora además un vector de revisiones para comparar la
vigencia sin releer los datasets completos:

```text
observations_revision
weather_generation_id
weather_manifest_sha256
sites_revision
stations_revision
catalogs_revision
gis_revision
training_contract_version
```

Cada revisión se publica al crear o validar su entrada. Comparar este vector es
una operación de metadatos. Los hashes completos siguen formando parte de la
integridad de los manifiestos, pero no se recalculan durante una promoción, una
consulta del Predictor o un reentrenamiento rutinario.
Todo escritor autorizado debe publicar la nueva revisión atómicamente con el
cambio. Las modificaciones externas que eludan esos escritores quedan fuera de
la comprobación rápida y se detectan mediante una auditoría profunda explícita.

## Reconstrucción y entrenamiento

La reconstrucción común materializa una sola vez:

1. snapshot inmutable de observaciones, known sites, perfiles e histórico;
2. catálogo y serie meteorológica IDW común por microárea;
3. agregados por área y cortes diarios de hasta 365 días;
4. datasets V2–V6 derivados de esa caché.

El entrenamiento multiversión consume esos datasets. El job ordinario ajusta
las versiones instaladas seleccionadas —una, varias o todas— y genera en la
misma pasada sus artefactos y evidencia hold-out sincronizada. El benchmark
científico completo añade particiones 7/14, campañas, remuestreos y reportes y
se ejecuta aparte. Así no se recalcula IDW cinco veces ni se convierte cada
regeneración de datos en un benchmark largo.

La reconstrucción común se ejecuta cuando cambian sus fuentes y publica nuevas
revisiones inmutables. Reentrenar una selección consume directamente esas
generaciones actuales sin ejecutar antes una segunda comprobación profunda. Los
constructores de cada versión preparan solo las filas y variables requeridas y
ajustan todos los estimadores declarados por sus perfiles. Las versiones no
seleccionadas conservan su generación instalada y muestran un aviso de vigencia
si sus revisiones ya no coinciden.

Cuando el worker termina, HA verifica la integridad, completitud y contrato de
cada generación producida y puede instalarla atómicamente en el slot de su
versión. Una diferencia entre el vector usado para entrenar y las revisiones
vivas se conserva como aviso trazable, pero no invalida artefactos correctos ni
provoca otro trabajo pesado. La promoción no recorre ni vuelve a descargar las
particiones meteorológicas. Cambiar la versión preferida solo mueve un puntero.

El benchmark científico queda reservado para incorporar una versión nueva,
modificar perfiles, features, estimadores o contratos, o realizar una
comparación científica manual. No forma parte del mantenimiento operativo
ordinario de las versiones ya instaladas.

## Predictor y explicaciones

El modo normal conserva ranking, semana, consulta e histórico con una única
versión preferida. Comparar añade selector de versión, temporal, perfil y
estimador, muestra disponibilidad real y ejecuta referencias exactas.

Cada resultado conserva dos capas:

- explicación ecológica común: corte, horizonte, fase de florada, lluvia,
  temperatura, humedad, balance y cobertura usados por el contrato;
- explicación estadística específica: probabilidad, soporte hold-out por
  especie/contrato, Brier frente a prevalencia y fenología, dominio de variables
  y motivo de exclusión.

### Selector operativo por escenario

Ventana fija y retardo/evento se resuelven independientemente. Un miembro solo
entra en el ranking cuando está disponible, devuelve una probabilidad finita,
su aplicabilidad es `within_observed_range` o `caution`, su Brier es
estrictamente menor que el Brier de prevalencia y su ROC-AUC es al menos 0,55.
La ausencia de cualquier gate produce una abstención explícita con los motivos;
no se elige el candidato menos malo.

Entre los elegibles el orden vigente es: mayor mejora absoluta de Brier frente
a prevalencia, menor Brier, mayor ROC-AUC e identidad estable como desempate
final. ROC-AUC >= 0,55 es por tanto un suelo de entrada; no sustituye la
prioridad principal de calibración/Brier.

### Fiabilidad estadística y consenso

Son ejes diferentes. La fiabilidad califica la evidencia fuera de muestra del
ganador de cada escenario. El veredicto global adopta el peor escenario:

- alta: ROC-AUC >= 0,80, mejora relativa Brier >= 20 %, al menos 50 muestras
  test, al menos 10 ejemplos de cada clase y aplicabilidad dentro del rango;
- moderada: ROC-AUC >= 0,70, mejora relativa Brier >= 10 %, al menos 30 muestras
  test, al menos 5 ejemplos de cada clase y aplicabilidad dentro del rango o
  con cautela;
- limitada: el ganador supera los gates operativos, pero no todos los requisitos
  de los niveles anteriores;
- no disponible: falta ganador evaluable en algún escenario requerido.

El consenso compara probabilidades entre familias metodológicas elegibles, no
entre nombres de estimadores que implementan el mismo supuesto. LR, Elastic Net,
Sparse Group y Smooth Species/Shared/Partial pertenecen a la familia logística;
RF/ET a árboles agregados; HGB a boosting; KNN a distancia; SVM a kernel. Las
variantes de una misma familia aportan acuerdo interno, pero no evidencia
independiente. Entre familias, separación máxima <= 10 puntos es consenso alto,
entre 10 y 20 moderado y >= 20 bajo. Con una sola familia se informa `sin
contraste`; el resumen global adopta el peor escenario medible y declara cuántos
escenarios pudieron contrastarse.

### Aplicabilidad vigente y deuda de calibración

Cada artefacto guarda por columna el mínimo, máximo, media y desviación estándar
de sus muestras elegibles. En inferencia se compara el valor crudo actual con
ese soporte marginal. El estado vigente es:

- `within_observed_range`: ninguna columna fuera de su mínimo/máximo;
- `caution`: existe alguna columna fuera, pero representa menos del 5 % y
  ninguna de esas columnas alcanza 3 desviaciones respecto a la media;
- `outside_domain`: al menos el 5 % de las columnas queda fuera o una columna
  ya fuera del rango alcanza 3 desviaciones.

El 5 % es una proporción de columnas, no una superación física del 5 %. Un
episodio de lluvia superior al máximo no se considera ecológicamente malo por
esta regla: solo se marca que el modelo dispone de menos soporte para esa
entrada. Los límites mínimo/máximo/media/desviación se calculan desde los datos;
los umbrales 5 % y 3 sigma están hardcoded y no son propiedades del estimador ni
constan calibrados empíricamente para Rainmapper.

La revisión acordada separará compatibilidad ecológica de aplicabilidad
estadística y probará, sin cambiar todavía el selector: distribuciones robustas
por variable, frecuencia de vecinos comparables, combinaciones multivariantes y
degradación de Brier/ROC-AUC/calibración en hold-out conforme aumenta la novedad.
Solo después de esa auditoría se discutirán nuevos límites. Si no hay extremos
fuera de muestra suficientes, el resultado correcto será evidencia insuficiente,
no un umbral nuevo presentado como validado.

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

Antes de renderizar el Predictor, HA compara el vector de revisiones del batch
instalado con los metadatos actuales. Si cambian, muestra un aviso de que las
predicciones no incorporan todavía toda la información y pide reentrenar las
versiones afectadas. Esta comprobación no abre ni calcula hashes de los
datasets. Los lotes antiguos que no guardan identidad se muestran como
«vigencia no verificable», nunca como actuales por suposición. El chequeo no
confunde meteorología futura de una
consulta con datos históricos de entrenamiento.

## Compatibilidad HA/worker

HA coordina catálogo, snapshot, jobs, manifests, instalación transaccional,
selección preferida y UI. El worker declara capacidades explícitas para
entrenamiento e inferencia
multiversión. HA solo le asigna un job si entiende su versión de contrato. Si
no hay worker compatible, el fallback local debe ejecutar el mismo contrato y
manifest, no otra implementación.

El worker conserva una caché meteorológica persistente direccionada por digest.
Un job descarga únicamente objetos ausentes o modificados y publica cuántos
bytes transfirió y reutilizó. La validación profunda de un objeto se realiza al
ingresarlo o durante una auditoría explícita; no se repite para todos los
objetos en cada promoción. HA tampoco reconstruye ni copia un snapshot completo
si puede referenciar la misma generación inmutable.

## Gates antes de release

- catálogo y `model_ref` validados sin listas V2–V6 hardcodeadas en la UI;
- adaptadores train/inferencia con paridad por perfil;
- un único ajuste lag y proyección operativa 1..7 comprobados por tests;
- batch atómico, hash, incompatibilidad y rollback transaccional probados;
- Comparar mantiene explicaciones y no promedia versiones;
- worker anuncia capacidades reales y HA las exige;
- pruebas dirigidas proporcionales durante cada bloque y una suite completa con
  smoke local antes de release;
- ningún modelo operativo, HA real, GHCR o release se modifica durante esta
  implementación local.

## Regla de empaquetado

Las imágenes HA y worker contienen código, dependencias y defaults públicos.
HA incluye una plantilla de observaciones vacía para instalaciones nuevas; no
contiene registros de observación, snapshots canónicos, benchmarks, hold-outs
ni modelos entrenados. Las entradas reales se congelan en HA al lanzar el
trabajo y se transfieren al worker mediante el contrato autenticado. Los
bundles temporales del job se descartan al terminar, pero los objetos
meteorológicos inmutables pueden permanecer en la caché persistente del worker,
acotada y verificable por digest. Reducir la imagen elimina herramientas de
compilación o cachés
innecesarios; no elimina información del dataset, porque esa información nunca
debe formar parte de la imagen pública.
