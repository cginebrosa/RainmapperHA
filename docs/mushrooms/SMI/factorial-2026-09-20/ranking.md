# SMI-05 · Comparación de las ocho combinaciones

Lluvia IDW en todas. Igual peso a 5 y 20 cm por estación; mediana entre estaciones.
Datos y parámetros fijos. Correlación no es porcentaje de acierto ni validación de litros.

## Comparando cada profundidad con su capa

Comparación pareada: **13 estaciones** con las ocho opciones y ambas sondas definidas.
Las otras estaciones no desaparecen: su cobertura y resultados por profundidad figuran en `summary.json` y `metrics.csv`.

| Combinación | r conjunto | r cambios diarios | Spearman conjunto |
|---|---:|---:|---:|
| Regulada · ET nueva · una capa | 0.694 | 0.236 | 0.770 |
| Regulada · Hargreaves · dos capas | 0.646 | 0.183 | 0.706 |
| Regulada · ET nueva · dos capas | 0.642 | 0.201 | 0.709 |
| Regulada · Hargreaves · una capa | 0.641 | 0.230 | 0.764 |
| Simple · ET nueva · una capa | 0.518 | 0.175 | 0.496 |
| Simple · ET nueva · dos capas | 0.507 | 0.200 | 0.480 |
| Simple · Hargreaves · dos capas | 0.385 | 0.172 | 0.440 |
| Simple · Hargreaves · una capa | 0.382 | 0.171 | 0.431 |

Estaciones comunes: Serra de Costa Ampla, El Boixer, Pessonada, Batlliu de Sort, Coll de Paller, La Cultia d'Àreu, Borda Coll, Llivia, Clarella, Bolvir, Aguilar de Segarra, Torre del Lluvià, Mas dels Frares.

## Comparando siempre el total 0–30 cm con ambas sondas

Comparación pareada: **18 estaciones** con las ocho opciones y ambas sondas definidas.
Las otras estaciones no desaparecen: su cobertura y resultados por profundidad figuran en `summary.json` y `metrics.csv`.

| Combinación | r conjunto | r cambios diarios | Spearman conjunto |
|---|---:|---:|---:|
| Regulada · ET nueva · una capa | 0.667 | 0.204 | 0.727 |
| Regulada · ET nueva · dos capas | 0.640 | 0.191 | 0.732 |
| Regulada · Hargreaves · una capa | 0.624 | 0.188 | 0.718 |
| Regulada · Hargreaves · dos capas | 0.615 | 0.178 | 0.719 |
| Simple · ET nueva · dos capas | 0.468 | 0.147 | 0.441 |
| Simple · Hargreaves · dos capas | 0.449 | 0.155 | 0.424 |
| Simple · ET nueva · una capa | 0.376 | 0.162 | 0.351 |
| Simple · Hargreaves · una capa | 0.321 | 0.145 | 0.354 |

Estaciones comunes: Serra de Costa Ampla, Camí dels Nerets, El Boixer, Los Coscolls, Pessonada, Batlliu de Sort, Coll de Paller, La Cultia d'Àreu, El Miracle, Borda Coll, Llivia, Clarella, Cantallops, Bolvir, Garriguella, Aguilar de Segarra, Torre del Lluvià, Mas dels Frares.
