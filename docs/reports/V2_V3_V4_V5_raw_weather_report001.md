# Informe 001 — V5 raw weather frente a V2/V3/V4

Fecha: 2026-08-16. Estado: **experimental, no operativo**.

## Respuesta corta

V5 raw no justifica todavía publicar una nueva versión de HA ni elegirlo como Predictor. En los 34 contextos evaluables especie+contrato+partición, el mejor V5 gana 2 y pierde 32 frente al mejor miembro individual V2/V3/V4 sobre las mismas filas. El resultado varía por especie y no se ha calculado Brier medio entre especies.

La sensibilidad por campañas completas supera simultáneamente prevalencia y fenología en ambos contratos solo para: `amanita_caesarea`, `boletus_pinophilus`, `cantharellus_cibarius_sl`. Esto impide interpretar la selección de retardos como una mejora generalizable.

Los 25 remuestreos agrupados exigidos se completaron en los 32 contextos evaluables del perfil raw sin calendario. Aun así, las selecciones son densas: 3330 celdas especie+contrato+estimador+variable pasan el umbral. Que aparezcan miles de días estables indica que la regularización no ha aislado ventanas interpretables, no que todos esos días sean biológicamente importantes.

La ablación es informativa: el mejor V5 usa `raw_primary_no_calendar` en 17/34 contextos y alguna variante sin calendario en 24/34. El calendario no explica por sí solo el resultado, pero quitarlo tampoco hace que V5 venza a los contratos actuales.

Los resultados **no justifican GAM/DLNM, estado temporal ni jerárquico como sucesor del Predictor**. Si se ensaya una sola familia diagnóstica, la jerárquica es la mejor priorizada por el soporte muy desigual entre especies; el modelo de estado queda condicionado a confirmar errores alternantes dentro de floradas. V5 debe permanecer solo experimental.

## Comparación por especie

Cada fila cuenta cuatro comparaciones (`fixed`/`lag_event` × grupos 7/14). «Gana» significa menor Brier que el mejor algoritmo individual de V2/V3/V4; no se comparó contra un ensemble.

| Especie | Gana | Empata | Pierde |
|---|---:|---:|---:|
| `amanita_caesarea` | 0 | 0 | 4 |
| `boletus_aereus` | 0 | 0 | 4 |
| `boletus_edulis` | 2 | 0 | 0 |
| `boletus_pinophilus` | 0 | 0 | 4 |
| `cantharellus_cibarius_sl` | 0 | 0 | 4 |
| `hygrophorus_latitabundus` | 0 | 0 | 4 |
| `hygrophorus_marzuolus` | 0 | 0 | 4 |
| `lactarius_deliciosus` | 0 | 0 | 4 |
| `morchella_elata_complex` | 0 | 0 | 4 |

Detalle auditable: [`analysis-summary.json`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/analysis-summary.json) y [`brier-delta-by-species.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/brier-delta-by-species.svg).

## Sensibilidad por campaña

La celda muestra `Brier del mejor V5 / supera baseline fenológico`. Las campañas `area_id+año` no cruzan train/test.

| Especie | fixed | lag_event |
|---|---|---|
| `amanita_caesarea` | 0.2505 / sí | 0.2508 / sí |
| `boletus_aereus` | 0.2486 / sí | 0.2497 / sí |
| `boletus_edulis` | n/e | n/e |
| `boletus_pinophilus` | 0.2541 / sí | 0.3010 / sí |
| `cantharellus_cibarius_sl` | 0.2500 / sí | 0.2500 / sí |
| `hygrophorus_latitabundus` | 0.1837 / sí | 0.1837 / sí |
| `hygrophorus_marzuolus` | 0.1240 / sí | 0.1240 / sí |
| `lactarius_deliciosus` | 0.1763 / sí | 0.1763 / sí |
| `morchella_elata_complex` | 0.1111 / no | 0.0741 / no |

Superar el baseline en campaña no basta para promoción: también se exige vencer al mejor miembro actual, estabilidad y calibración razonable.

## Variables, retardos y dos escalas

Se encontraron 3330 celdas especie+contrato+estimador+variable con frecuencia ≥0,70 y signo concordante ≥0,80 en 25 remuestreos por grupos completos del perfil raw sin calendario. Es un resultado excesivamente denso. Por canal: {'rain_mm': 476, 'temp_min_c': 586, 'temp_max_c': 592, 'humidity_min_pct': 657, 'humidity_max_pct': 1019}. Por banda: {'0-7': 77, '8-30': 205, '31-90': 541, '91-180': 715, '181-364': 1792}. Al normalizar por la anchura de cada banda, la densidad por día es {'0-7': 9.625, '8-30': 8.913, '31-90': 9.017, '91-180': 7.944, '181-364': 9.739}: prácticamente uniforme, no dos picos temporales.

Esta lectura es diagnóstica. La lluvia, humedad y temperatura están correlacionadas; que el regularizador escoja una no vuelve irrelevantes causalmente a las demás. Hay retardos estables recientes y largos, pero su densidad casi uniforme y el mal rendimiento hold-out **no respaldan dos ventanas diferenciadas** de activación y preparación micelial/hospedador.

- [`stable-features-by-channel.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-features-by-channel.svg)
- [`stable-features-by-lag-band.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-features-by-lag-band.svg)
- [`selection-frequency-by-lag.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/selection-frequency-by-lag.svg)
- [`stable-lag-heatmap-by-species.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-lag-heatmap-by-species.svg)
- [`stable-coefficient-intervals.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-coefficient-intervals.svg)
- [`stable-coefficient-signs.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/stable-coefficient-signs.svg)

## Falsos positivos y negativos compartidos

Con umbral 0,5 hay 3518 filas-contexto `shared_all`: {'false_positive': 3149, 'false_negative': 369}. Al deduplicar especie+observación+tipo quedan 90 errores observacionales: {'between_positive_visits': 9, 'unknown_phase': 42, 'post_fruiting_observed': 5, 'pre_fruiting_observed': 11, 'singleton': 10, 'onset_observed': 5, 'decline_observed': 6, 'active_observed': 2}. Los listados completos conservan especie, contrato, horizonte, fase, campaña y resúmenes meteorológicos en [`shared-errors.json`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/shared-errors.json).

- [`shared-errors-by-phase.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/shared-errors-by-phase.svg)
- [`shared-errors-by-species.svg`](../../docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/graphs/shared-errors-by-species.svg)

`unknown_phase` domina tras deduplicar; `between_positive_visits`, onset y decline no dominan. Por eso los errores no justifican todavía un modelo de estado. La inestabilidad entre especies con n pequeño hace que una estructura jerárquica sea la siguiente hipótesis más razonable, pero no un candidato operativo. No se reetiquetaron observaciones ni se trataron días no visitados como negativos.

## Método y salvaguardas

- Snapshot canónico inmutable: `docker-data/audits/mushroom-ml-snapshot-20260816`.
- 395 observaciones `fixed`, 1.580 tareas `lag`; 352 y 1.408 elegibles respectivamente.
- V5 entrega 365 días causales de cinco canales IDW comunes; la ablación añade ET0 y balance.
- Elastic Net y sparse-group logistic se ajustan solo con train y seleccionan por Brier interno.
- `lag_event` realiza un ajuste por especie+contrato+estimador+split; 1/2/3/7 filtran las mismas probabilidades hold-out.
- 12,280 filas hold-out y 12,280 claves únicas; no se escribieron modelos ni se entrenó candidato operativo.
- No se modificaron HA, worker, GHCR, releases ni modelos operativos.

## Limitaciones que impiden promoción

1. El tamaño por especie sigue siendo pequeño y algunas particiones tienen una sola clase.
2. Incluso sin calendario, 2.938 variables-día pasan el umbral de estabilidad: no emerge una ventana parsimoniosa interpretable.
3. La parrilla nocturna se redujo a seis configuraciones Elastic Net y nueve sparse-group para mantener el coste acotado; quedó registrada en código.
4. Los errores compartidos cuentan contextos repetidos y horizontes como diagnósticos, no como observaciones independientes.

## Decisión

Mantener V2/V3/V4 vivas y V5 como `proposed` no operativa. No desbloquear Rainmapper mediante una publicación HA basada en este ensayo. Si se continúa la investigación, ensayar una familia jerárquica por especie como diagnóstico, comparándola en las mismas filas contra el mejor miembro individual. Un modelo de estado queda descartado por ahora salvo que más observaciones confirmen errores alternantes dentro de floradas; un GAM/DLNM queda aplazado hasta que aparezcan bandas estables. No se propone ensemble.
