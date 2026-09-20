# SMI-05 · Elección entre las ocho combinaciones

**Decisión aceptada por el usuario el 20/09/2026:** fijar extracción regulada +
ET nueva (Penman–Monteith con las aproximaciones actuales) + una capa de 0–30 cm
como SMI de referencia. Esta aceptación no implica un despliegue ni validación
de los niveles absolutos. [Propuesta para contrastar cantidades](../absolute-water-plan.md).

Ejecutado el 20/09/2026. [Protocolo previo](PROTOCOL.md), [ranking completo](ranking.md).

**Elección práctica: extracción regulada + ET nueva (Penman–Monteith con las
aproximaciones actuales) + una capa 0–30 cm.** Se completan las dos combinaciones
que faltaban en SMI-03/04: extracción simple en dos capas, con ambas ET.
No se han cambiado los cálculos del mapa ni accedido a HA, worker o Docker.

## Resultado para el SMI del perfil 0–30 cm

Se comparan los totales integrados de las ocho combinaciones con ambas sondas,
dando igual peso a 5 y 20 cm por estación. Después se toma la mediana entre
estaciones. Siempre IDW, nunca se selecciona usando solo lluvia medida.

| Extracción | ET | Capas | Concordancia conjunta r |
|---|---|---:|---:|
| Regulada | ET nueva | 1 | **0,667** |
| Regulada | ET nueva | 2 | 0,640 |
| Regulada | Hargreaves | 1 | 0,624 |
| Regulada | Hargreaves | 2 | 0,615 |
| Simple | ET nueva | 2 | 0,468 |
| Simple | Hargreaves | 2 | 0,449 |
| Simple | ET nueva | 1 | 0,376 |
| Simple | Hargreaves | 1 | 0,321 |

Las 22 estaciones están examinadas y conservadas. El ranking pareado utiliza
**18** con r definido en las ocho opciones y ambas profundidades. No se puede
calcular correlación cuando una curva es constante, y Clot no tiene cobertura
suficiente a 5 cm. No se imputan r=0 ni se ocultan las estaciones excluidas del
ranking común; ver cobertura y resultados individuales en `summary.json`/CSV.

La primera también obtiene el mayor resumen de concordancia de cambios diarios
(0,204). En Spearman la regulada de dos capas con ET nueva queda ligeramente por
encima (0,732 frente a 0,727): **no gana una combinación en todas las métricas**.
La elección combina el resultado global, cambios diarios y los fallos físicos
observados en la cascada, además de evitar complejidad sin ventaja consistente.

Al comparar cada profundidad con su capa correspondiente, en vez de comparar
siempre el total, quedan 13 estaciones comunes: la combinación recomendada sigue
primera en Pearson, cambios diarios y Spearman. Las capas inferiores simples
son constantes en nueve estaciones; no confundir una falta de r con validación.

## Qué significa para avanzar

La evidencia favorece claramente regulación frente a extracción simple. Favorece
solo modestamente ET nueva sobre Hargreaves cuando la estructura es la misma:
no justifica decir que Penman–Monteith sea mucho más exacta físicamente.
Pero sí permite **elegir una referencia concreta** y no esperar a ensayar
indefinidamente todos los modelos posibles.

La elección se basa en evolución temporal, no en una validación del porcentaje
absoluto ni los litros. r=0,667 no significa 66,7% de acierto. No hay FC/WP medidas
comparables para convertir las sondas a SMI; la red explorada no valida bosques.
La evaluación conjunta y los pesos son decisiones explícitas posteriores a los
experimentos, no un criterio preregistrado ni una prueba independiente.

## Definición de las dos opciones nuevas

Mismas capacidades y cascada de SMI-04, cambiando únicamente la extracción: se
consume la demanda potencial mientras haya agua en cada capa, sin reducción
progresiva por sequedad. E potencial 50% arriba; T potencial 50% repartida por
capacidad. Sin compensar demanda insatisfecha extrayendo de otra capa.

Esto completa las ocho opciones **de las estructuras concretas ensayadas**;
«dos capas» no es un único modelo universal. No se han ajustado espesores, raíces,
retrasos o transporte para mejorar resultados.

El simple histórico de una capa drena después de ET; la cascada drena antes.
Se añadió un control simple de una capa con drenaje previo: en las 18 estaciones
comunes su r conjunto es 0,303 con Hargreaves y 0,376 con ET nueva. No altera
la recomendación. El control se guarda aparte y no se cuenta como novena opción.

## Reproducción y pruebas

```sh
.venv/bin/python docs/mushrooms/SMI/factorial-2026-09-20/test_simple_layers.py
.venv/bin/python docs/mushrooms/SMI/factorial-2026-09-20/compare.py
```

Cuatro pruebas nuevas pasan: extracción completa hasta agotar agua, cascada y
desbordes, balance/perturbación de 0,01 mm, historia e incertidumbre/huecos.
En las 44 simulaciones nuevas (22 estaciones × dos ET) hay 60 días publicables;
error máximo de masa diario/acumulado ≤5,69×10⁻¹³ mm como cota redondeada.

704 filas de métricas (incluyen total y referencia por profundidad), 1.320 filas
diarias comprimidas, control del orden de drenaje separado, ranking y resumen.
SHA-256 de entradas y scripts en `summary.json`. ET reconstruida y huellas de
evidencias previas comprobadas. Todo offline, sin descargas ni nuevas imágenes.
