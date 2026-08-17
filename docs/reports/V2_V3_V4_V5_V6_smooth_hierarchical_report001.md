# Informe 001 — V6 retardos suaves y pooling parcial

Fecha: 2026-08-16. Estado: **experimental, no operativo**.

## Respuesta corta

V6 gana 4 y pierde 30 de 34 comparaciones estrictas contra el mejor miembro individual V2/V3/V4/V5 sobre las mismas filas. No se usa Brier medio entre especies. El mejor estimador V6 por contexto se reparte así: {'smooth_species_logistic_v1': 19, 'smooth_partial_pooling_logistic_v1': 11, 'smooth_shared_logistic_v1': 4}.

El pooling parcial vence al modelo suave por especie 15 veces y pierde 19; frente al modelo completamente compartido gana 44 y pierde 8. Por tanto, compartir información ayuda en algunos casos, pero no es la explicación dominante: el modelo independiente sigue siendo el mejor V6 más frecuente.

La sensibilidad por campañas completas mejora simultáneamente al mejor V5 de campaña y al baseline fenológico en ambos contratos para: `amanita_caesarea`, `boletus_aereus`, `cantharellus_cibarius_sl`, `hygrophorus_latitabundus`. Las especies que el modelo conjunto puede predecir sin comparador individual previo se conservan como diagnóstico y no cuentan como victoria: {'boletus_edulis': ['fixed-groups7', 'lag-groups7'], 'cantharellus_lutescens': ['fixed-groups7', 'fixed-groups14', 'lag-groups7', 'lag-groups14'], 'lactarius_sanguifluus': ['fixed-groups7', 'fixed-groups14', 'lag-groups7', 'lag-groups14'], 'russula_virescens': ['fixed-groups7', 'fixed-groups14', 'lag-groups7', 'lag-groups14'], 'tricholoma_terreum': ['fixed-groups7', 'fixed-groups14', 'lag-groups7', 'lag-groups14']}.

## Resultado por especie

| Especie | Gana | Empata | Pierde |
|---|---:|---:|---:|
| `amanita_caesarea` | 1 | 0 | 3 |
| `boletus_aereus` | 0 | 0 | 4 |
| `boletus_edulis` | 0 | 0 | 2 |
| `boletus_pinophilus` | 0 | 0 | 4 |
| `cantharellus_cibarius_sl` | 1 | 0 | 3 |
| `hygrophorus_latitabundus` | 2 | 0 | 2 |
| `hygrophorus_marzuolus` | 0 | 0 | 4 |
| `lactarius_deliciosus` | 0 | 0 | 4 |
| `morchella_elata_complex` | 0 | 0 | 4 |

[`v6-brier-delta-by-species.svg`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/graphs/v6-brier-delta-by-species.svg)

Las únicas victorias estrictas son:

| Especie | Comparación | Mejora Brier | Mejor V6 |
|---|---|---:|---|
| `hygrophorus_latitabundus` | `fixed-groups7` | +0.0642 | `smooth_partial_pooling_logistic_v1` |
| `hygrophorus_latitabundus` | `fixed-groups14` | +0.0402 | `smooth_partial_pooling_logistic_v1` |
| `amanita_caesarea` | `lag-groups7` | +0.0070 | `smooth_species_logistic_v1` |
| `cantharellus_cibarius_sl` | `lag-groups7` | +0.0063 | `smooth_species_logistic_v1` |

## Interpretación

El modelo suave por especie comprueba si reducir 365 días a 50 exposiciones evita la selección difusa de V5. El compartido fuerza una única respuesta meteorológica entre especies. El pooling parcial conserva esa respuesta común y permite desviaciones específicas más pequeñas.

Que el pooling parcial gane al modelo completamente compartido no basta: para justificar jerarquía debe vencer también al modelo suave por especie y al mejor contrato anterior, y mantenerlo al bloquear campañas. Los errores compartidos deduplicados por fase son {'between_positive_visits': 9, 'pre_fruiting_observed': 10, 'unknown_phase': 34, 'post_fruiting_observed': 3, 'singleton': 6}.

## Decisión

La promoción queda prohibida. V6 pierde 30/34, así que **no justifica desarrollar ahora un jerárquico probabilístico general ni cambiar el Predictor**. La señal más concreta es `hygrophorus_latitabundus`: pooling parcial mejora en sus dos comparaciones fixed, pero el test solo contiene cuatro observaciones y debe tratarse como hipótesis frágil. Las mejoras de `amanita_caesarea` y `cantharellus_cibarius_sl` son pequeñas y proceden del modelo suave por especie, no de la jerarquía.

El experimento sí responde a la pregunta metodológica: suavizar los retardos reduce drásticamente la dimensionalidad y permite evaluar especies de soporte mínimo mediante pooling, pero no recupera una mejora general. El siguiente paso con mayor valor no es añadir otra familia; es incorporar nuevas campañas/visitas y repetir este V6 congelado. V2/V3/V4/V5 permanecen vivas y no se propone ensemble.

Artefactos: [`analysis-summary.json`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/analysis-summary.json), [`heldout-predictions.jsonl`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/heldout-predictions.jsonl) y [`shared-errors.json`](../../docker-data/audits/mushroom-ml-v6-smooth-hierarchical-20260816/shared-errors.json).
