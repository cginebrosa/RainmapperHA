# Runtime multiversión V2–V6 para Predictor, HA y worker

Estado: **EN IMPLEMENTACIÓN LOCAL; NO DESPLEGADO**.

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

`fixed_gap` solo admite horizonte 7. `lag_event` admite 1/2/3/7, pero cada
especie+contrato+perfil+estimador tiene un único ajuste: los cuatro horizontes
seleccionan filas o valores de `horizon_days` del mismo modelo y nunca crean
cuatro entrenamientos.

Por ello el manifiesto distingue `artifact_ref` (la misma identidad sin
`horizon_days`) de `model_ref` (una consulta predictiva concreta). Un artefacto
lag declara `supported_horizons=[1,2,3,7]` y aparece una sola vez en disco.

`group_days=7/14` pertenece únicamente a la partición del benchmark. No forma
parte de `model_ref` ni del runtime. El retardo meteorológico raw 0–364 tampoco
es el horizonte de predicción.

## Catálogo inicial

| Versión | Perfil runtime | Estimadores | Modo normal |
|---|---|---|---|
| V2 `altitude_v2` | `common_idw` | LR, RF, ET, HGB, KNN, SVM | sí, mientras sea activa |
| V3 `biology_v3` | `core` | LR, RF, ET, HGB, KNN, SVM | no sin promoción |
| V4 `biology_v4` | `extended_weather`, `climatic_balance` | LR, RF, ET, HGB, KNN, SVM | no sin promoción |
| V5 `biology_v5_raw_weather_discovery` | `raw_primary_no_calendar` | Elastic Net, sparse-group | no sin promoción |
| V6 `biology_v6_smooth_hierarchical` | `smooth_raw` | suave por especie, compartido, pooling parcial | no sin promoción |

V4 `core`, las variantes SoilGrids y las ablaciones V5 quedan reconstruibles en
el laboratorio, pero no multiplican el catálogo ordinario: V4 core duplica V3
y las restantes no superaron los benchmarks actuales.

## Batch y almacenamiento

Un `batch_id` agrupa generaciones producidas desde exactamente el mismo
`snapshot_id=sha256:...`. El manifiesto enumera todos los artefactos y hashes.
La ruta se deriva del `model_ref`, no de nombres legacy:

```text
batches/<batch>/generations/<generation>/<version>/<temporal>/<profile>/<estimator>/<species>.joblib
```

El batch nuevo se escribe en staging, se verifica por hash y contrato y solo
entonces se activa atómicamente. El batch anterior permanece como rollback. Una
activación parcial que mezcle snapshots está prohibida.

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

V5/V6 no fingirán una importancia causal de cada día. Mostrarán resúmenes por
banda y, cuando proceda, coeficientes o curvas estables con la advertencia de
que son diagnósticos de asociación.

## Compatibilidad HA/worker

HA coordina catálogo, snapshot, jobs, manifests, activación, rollback y UI. El
worker declara capacidades explícitas para entrenamiento e inferencia
multiversión. HA solo le asigna un job si entiende su versión de contrato. Si
no hay worker compatible, el fallback local debe ejecutar el mismo contrato y
manifest, no otra implementación.

## Gates antes de release

- catálogo y `model_ref` validados sin listas V2–V6 hardcodeadas en la UI;
- adaptadores train/inferencia con paridad por perfil;
- un único ajuste lag y proyección 1/2/3/7 comprobados por tests;
- batch atómico, hash, incompatibilidad y rollback probados;
- Comparar mantiene explicaciones y no promedia versiones;
- worker anuncia capacidades reales y HA las exige;
- suite completa y smoke test locales;
- ningún modelo operativo, HA real, GHCR o release se modifica durante esta
  implementación local.
