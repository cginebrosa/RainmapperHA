# Resultado de la investigación del ganador — 04/10/2026

**Mantener por ahora la operación, sin descartar las mejoras observadas para
caesarea.** B mejora su resultado conjunto y C recupera más oportunidades, pero
ninguna supera todos los criterios predefinidos y falta confirmación independiente.
Aereus no mejora con las alternativas. No promover ahora B ni C no demuestra
que A sea óptima; los motivos y las limitaciones del propio criterio se explican
por especie y campaña.

La comparación es exploratoria: sus casos ya se habían visto al diseñar las
hipótesis. No constituye confirmación independiente ni evaluación directa de los
modelos instalados en HA. No se ha modificado la operación.

La regla numérica de nominación es un filtro conservador fijado por el agente
antes del cálculo, no una proporción de costes elegida por el usuario. Su
preferencia cualitativa no permite concluir cuánto favorable erróneo adicional
aceptaría a cambio de recuperar oportunidades. No superar esa regla tampoco
demuestra que abstenerse siempre sea la decisión más útil.

La conversación posterior concretó la preferencia del usuario y propuso un
[índice de utilidad por oportunidades reales](#indice-utilidad-oportunidades).
Se documenta como análisis exploratorio añadido el 04/10/2026: la penalización
de cada falso favorable y el mínimo aceptable siguen pendientes de acuerdo.
No sustituye las reglas del experimento ni autoriza una promoción.

## Qué se comparó

- **A:** selector actual completo con ranking del año anterior Y−1, fuera de ajuste.
- **B:** añade al ranking el año Y−2, con predicciones fuera de su ajuste; mismo selector semanal.
- **C:** catálogo B, elección diaria. Si B ya usa fallback diario, C coincide con B.

Los tres comparten modelos finales por corte, filtros, política y umbral favorable
0,60. Se reutilizaron modelos guardados: ningún entrenamiento nuevo. B−A cambia
la evidencia histórica, incluida su edad y el tamaño de los ajustes que la
produjeron. C−B estudia la selección diaria; C−A cambia ambos componentes.

A reproduce el procedimiento en una partición temporal experimental; no el
reparto operativo 70/30. Tampoco es el A del estudio de umbrales, cuyo ranking era
Y−2. No comparar directamente sus porcentajes como si fuese la misma referencia.

Se evaluaron 116 observaciones: 55 aereus (36 favorables/19 desfavorables) y
61 caesarea (35/26), en 2024–2026. Son 812 emisiones por variante. Cada observación
pesa 1/7 por horizonte: **TP y FP son conteos ponderados, no cientos de casos
independientes**. NE indica denominador inexistente.

## Resultado conjunto

Promedio entre los siete horizontes de predicción (1–7 días). Cada celda muestra
**cantidad / total correspondiente → porcentaje**. Los decimales proceden del
promedio; los porcentajes se calculan antes de redondear. Las filas «Perfecto»
son la referencia ideal, no un resultado obtenido.

| Especie | Variante | TP: favorables detectados / favorables reales | FP: falsos favorables / desfavorables reales | Precisión: aciertos / consejos favorables | Cobertura: consejos / observaciones | Oportunidades perdidas / favorables reales |
|---|---|---:|---:|---:|---:|---:|
| Aereus | A | 17,57 / 36 → 48,8% | 7,71 / 19 → 40,6% | 17,57 / 25,29 → 69,5% | 33 / 55 → 60,0% | 18,43 / 36 → 51,2% |
| Aereus | B | 12,86 / 36 → 35,7% | 8,14 / 19 → 42,9% | 12,86 / 21 → 61,2% | 28,71 / 55 → 52,2% | 23,14 / 36 → 64,3% |
| Aereus | C | 16,71 / 36 → 46,4% | 8,86 / 19 → 46,6% | 16,71 / 25,57 → 65,4% | 35,86 / 55 → 65,2% | 19,29 / 36 → 53,6% |
| Aereus | **Perfecto (ideal)** | 36 / 36 → 100,0% | 0 / 19 → 0,0% | 36 / 36 → 100,0% | 55 / 55 → 100,0% | 0 / 36 → 0,0% |
| Caesarea | A | 8,71 / 35 → 24,9% | 6,57 / 26 → 25,3% | 8,71 / 15,29 → 57,0% | 19,57 / 61 → 32,1% | 26,29 / 35 → 75,1% |
| Caesarea | B | 13,14 / 35 → 37,6% | 2,43 / 26 → 9,3% | 13,14 / 15,57 → 84,4% | 20,57 / 61 → 33,7% | 21,86 / 35 → 62,4% |
| Caesarea | C | 20,14 / 35 → 57,6% | 7 / 26 → 26,9% | 20,14 / 27,14 → 74,2% | 40,29 / 61 → 66,0% | 14,86 / 35 → 42,4% |
| Caesarea | **Perfecto (ideal)** | 35 / 35 → 100,0% | 0 / 26 → 0,0% | 35 / 35 → 100,0% | 61 / 61 → 100,0% | 0 / 35 → 0,0% |

El porcentaje de TP es el de **positivos detectados**. En TP y precisión, más es
mejor; en FP y oportunidades perdidas, menos es mejor. Cobertura cuenta consejos
favorables o desfavorables, sean correctos o incorrectos; abstenerse no cuenta
como acierto. Oportunidades perdidas suma positivos aconsejados desfavorables y
positivos sin consejo. Las tablas completas incluyen matrices 2×3, cada año y horizonte.

### Cómo leer las columnas

- **TP: favorables detectados / favorables reales.** El sistema dijo favorable y
  la observación fue favorable. El denominador incluye todas las observaciones
  realmente favorables. Su porcentaje es la detección de positivos: más es mejor.
- **FP: falsos favorables / desfavorables reales.** El sistema dijo favorable,
  pero la observación fue desfavorable. Se divide entre todas las observaciones
  realmente desfavorables. Es el error que el usuario quiere penalizar más:
  menos es mejor.
- **Precisión: aciertos / consejos favorables.** De todos los consejos favorables
  emitidos, cuántos acertaron. El denominador es TP + FP. Mide la fiabilidad de
  recomendar favorable: más es mejor. Sin consejos favorables es no estimable
  (`0 / 0 → NE`), no un 100% de acierto.
- **Cobertura: consejos / observaciones.** En cuántas observaciones se emitió
  consejo favorable o desfavorable, sea acertado o erróneo. El resto es abstención.
  Una cobertura mayor sólo es útil si acompaña a una calidad suficiente.
- **Oportunidades perdidas / favorables reales.** Observaciones realmente favorables
  en las que se aconsejó desfavorable o se abstuvo. Su denominador es el mismo
  que el de TP; ambos porcentajes suman 100%. Menos oportunidades perdidas es mejor.

La **precisión** mide cuánto acertamos cuando recomendamos favorable; la
**detección** mide qué parte de las oportunidades existentes encontramos. Se
puede tener mucha precisión y detectar muy pocas oportunidades por recomendar
muy pocas veces. Abstenerse no cuenta como acertar un desfavorable.

Los recuentos se promedian entre siete antelaciones. Una observación favorable
que recibe consejo favorable en cuatro de ellas aporta `4 / 7 = 0,57` TP; si
lo recibe en las siete, aporta 1 TP. Por eso aparecen decimales. El máximo TP
es 36 para aereus y 35 para caesarea, sus observaciones realmente favorables.
La fila **Perfecto (ideal)** detecta todos esos favorables, aconseja correctamente
desfavorable en los demás casos y no se abstiene, en ninguno de los horizontes.

### Aereus

B pierde 4,71 favorables acertados y añade 0,43 falsos favorables frente a A.
C recupera oportunidades respecto a B, pero frente a A sigue perdiendo 0,86 TP y
añadiendo 1,14 FP. No hay fundamento para preferir estas alternativas con la
prioridad del usuario. B resulta especialmente poco útil en 2024: sólo 0,14 TP;
en 2026 baja de 5,29 TP de A a 2,29.

### Caesarea

**En el conjunto, B mejora a A:** reduce los falsos favorables de 6,57 a 2,43,
aumenta los aciertos favorables de 8,71 a 13,14 y eleva la precisión de 57,0% a
84,4%. También mejora ligeramente la cobertura. Es una señal favorable a B y
coherente con priorizar menos recomendaciones favorables erróneas.

El desglose muestra cómo se compone ese promedio. Se conserva la misma unidad
ponderada entre horizontes y cada fila explicita sus denominadores:

| Corte | Variante | TP / favorables reales | FP / desfavorables reales | Precisión: TP / consejos favorables | Cobertura: consejos / observaciones |
|---|---|---:|---:|---:|---:|
| 2024 | A | 0 / 14 → 0,0% | 0 / 6 → 0,0% | 0 / 0 → NE | 0 / 20 → 0,0% |
| 2024 | B | 11 / 14 → 78,6% | 2 / 6 → 33,3% | 11 / 13 → 84,6% | 14,14 / 20 → 70,7% |
| 2024 | C | 9,57 / 14 → 68,4% | 2 / 6 → 33,3% | 9,57 / 11,57 → 82,7% | 15,29 / 20 → 76,4% |
| 2025 | A | 5 / 13 → 38,5% | 5,57 / 13 → 42,9% | 5 / 10,57 → 47,3% | 11,14 / 26 → 42,9% |
| 2025 | B | 0 / 13 → 0,0% | 0 / 13 → 0,0% | 0 / 0 → NE | 0 / 26 → 0,0% |
| 2025 | C | 9,14 / 13 → 70,3% | 4,86 / 13 → 37,4% | 9,14 / 14 → 65,3% | 15,86 / 26 → 61,0% |
| 2026 | A | 3,71 / 8 → 46,4% | 1 / 7 → 14,3% | 3,71 / 4,71 → 78,8% | 8,43 / 15 → 56,2% |
| 2026 | B | 2,14 / 8 → 26,8% | 0,43 / 7 → 6,1% | 2,14 / 2,57 → 83,3% | 6,43 / 15 → 42,9% |
| 2026 | C | 1,43 / 8 → 17,9% | 0,14 / 7 → 2,0% | 1,43 / 1,57 → 90,9% | 9,14 / 15 → 61,0% |

En **2024**, B recupera 11 aciertos frente a una A que se abstiene siempre, a
cambio de dos falsos favorables. Es un intercambio potencialmente útil. En
**2025**, B se abstiene en las 26 observaciones y pierde todas las oportunidades,
pero A también funciona mal: acierta cinco consejos favorables y falla 5,57.
Preferir la abstención a ese resultado puede ser razonable con la prioridad del
usuario; la abstención por sí sola no demuestra que B sea peor. En **2026**, B
reduce errores a costa de detectar menos favorables que A.

La regla del agente exigía no añadir más de un FP ponderado en ningún corte y
conservar al menos la mitad de los TP cuando A alcanzase dos. B falla la primera
condición en 2024 y la segunda en 2025, aunque supera los requisitos conjuntos.
**Ese veto es una decisión conservadora del protocolo, no una prueba de que A
sea mejor.** Especialmente en 2024 penaliza dos errores adicionales sin compensar
los once aciertos recuperados. No se atribuye al usuario esa relación de costes.
No se cambian las reglas después de ver los resultados; sí se explicitan sus límites.

La cautela para sustituir la operación procede además de la evidencia limitada:
35 observaciones favorables y 26 desfavorables, repartidas en 31 episodios,
y años previamente vistos al diseñar esta hipótesis. Los intervalos exploratorios
B−A incluyen tanto mejora como empeoramiento: −10,29 a +1,43 FP y −4,14 a +14,57
TP. El comportamiento con el reparto experimental tampoco demuestra qué ocurriría
con los modelos y el ranking instalados en HA.

**Recomendación: conservar B para caesarea como una alternativa prometedora que
merece validación adicional antes de sustituir A.** No concluir «B no sirve» ni
«A es mejor». Antes de otra comparación habría que acordar cómo valorar una
campaña sin consejos frente a una campaña con consejos erróneos y qué utilidad
mínima exigir; después contrastarlo con evidencia nueva. Este informe no lanza
ese seguimiento ni modifica la nominación del protocolo cerrado.

La causa de esa abstención en B2025 está identificada. En 175 de las 182 emisiones
de caesarea sólo se materializa la familia semanal V5, ventana raw de 30 días,
contrato lag y regresión logística elastic net. Tiene 24 casos de ranking y sí
mejora ligeramente el Brier de referencia (0,207803 frente a 0,208944), pero su
ROC AUC **0,483193 no alcanza el mínimo 0,55**. Las 175 quedan vetadas por ese
filtro; 27 también por aplicabilidad. Las otras siete corresponden a una
observación con huéspedes desconocidos. No es falta de soporte ni incertidumbre
de una probabilidad elegida. El catálogo contiene otras 29 entradas que superan
Brier y ROC, pero quedan fuera de esa familia semanal; ello no garantiza que
superen todos los filtros de cada punto.

Es un problema concreto del orden de selección y filtrado: la familia semanal
retenida resulta inelegible después, sin recuperar las alternativas diarias en
esa rama. Fuentes: `fold-2025/quality-B.json` y las trazas B de
`fold-2025/evaluation/predictions.jsonl`, bajo `tmp/prediction-model-selection/`;
filtro en [mushroom_ml_multiversion_comparison.py](../../../rainmapper_core/mushroom_ml_multiversion_comparison.py#L504).

**C también ofrece una señal favorable que merece validación.** Frente a A
recupera 11,43 aciertos, de `8,71 / 35 → 24,9%` a `20,14 / 35 → 57,6%`, con
sólo 0,43 falsos favorables adicionales, de `6,57 / 26 → 25,3%` a
`7 / 26 → 26,9%`. La precisión sube de 57,0% a 74,2% y la cobertura de 32,1% a
66,0%. En este conjunto, C aporta muchas más oportunidades con un aumento pequeño
de falsos favorables. Sería incorrecto resumirlo como «no mejora».

El desglose anterior añade matices: en 2024 C recupera 9,57 aciertos frente a
una A que se abstiene, con dos FP; en 2025 C supera a A en aciertos y reduce sus
FP, además de evitar la abstención completa de B. En 2026 C reduce mucho los
errores, pero sólo detecta `1,43 / 8 → 17,9%` de las oportunidades, frente a
`3,71 / 8 → 46,4%` de A. La precisión de C ese año es 90,9%, condicionada a
sus pocos consejos favorables. Es otro intercambio entre fiabilidad y oportunidades,
no evidencia de que A sea necesariamente preferible con los costes del usuario.

C queda fuera de la nominación porque la regla conjunta exige no aumentar FP
cuando la mejora consiste en ganar TP, y porque incumple los límites por campaña
(2024: más de un FP adicional; 2026: menos de la mitad de los TP de A). Es una
regla estricta: no acepta ni siquiera el aumento conjunto de 0,43 FP a cambio de
11,43 TP. Ese intercambio podría ser aceptable para el usuario, pero no se había
acordado numéricamente. No se reescribe la regla cerrada para declarar que C la
superó; se reconoce que su incumplimiento no basta para descartar su utilidad.

La señal exploratoria de más aciertos de C frente a A tiene un intervalo positivo
(+2,57 a +22,86 TP); el cambio de FP abarca −2,14 a +3,57. Esto favorece seguir
investigando C, sin convertirlo en una confirmación independiente o en la promesa
de que los errores adicionales seguirán siendo tan pocos.

**B y C representan dos alternativas prometedoras para caesarea:** B comete menos
falsos favorables y tiene mayor precisión; C detecta más oportunidades y ofrece
más consejos. Frente a B, C gana siete TP pero añade 4,57 FP en el conjunto.
Mi recomendación es contrastar ambos intercambios en una siguiente validación
con criterios de utilidad acordados antes de observar nueva evidencia. Aún no
se justifica recomendar una sustitución operativa confirmada, ni afirmar que
mantener A sea la mejor solución definitiva. Ninguna variante queda promovida.

<a id="indice-utilidad-oportunidades"></a>

## Índice propuesto: precisión y oportunidades reales

### Preferencia del usuario y significado de cobertura

El usuario concretó su prioridad: **prefiere 10 recomendaciones favorables con
9 aciertos a 40 con 30 aciertos**, siempre que el número de recomendaciones sea
razonablemente útil. Evitar salidas aconsejadas favorables que resulten
desfavorables pesa más que recuperar todas las oportunidades. El ejemplo no
establece todavía una precisión mínima obligatoria del 90% ni una frecuencia
mínima de recomendaciones.

Para expresar esa preferencia hay que distinguir tres denominadores:

- **Precisión favorable:** `TP / (TP + FP)`, acierto cuando se dice favorable.
- **Detección de oportunidades:** `TP / P`, donde `P` son todos los casos realmente
  favorables, incluidos los no detectados. Es la proporción de oportunidades
  reales que se aprovecha.
- **Frecuencia de consejos favorables:** `(TP + FP) / N`, donde `N` son todos los
  casos evaluados. Es cuántas veces se recomienda favorable, se acierte o no.

La columna «Cobertura» de la tabla conjunta incluye consejos favorables **y
desfavorables**. No debe confundirse con las dos últimas medidas ni utilizarse
por sí sola como garantía de que se ofrecen suficientes salidas favorables.

### Fórmula y elección del denominador

La propuesta que queda para continuar la discusión es:

```text
I_k = 100 × (TP − k × FP) / P

P = número de observaciones realmente favorables
k = coste de un falso favorable, relativo al beneficio de un acierto favorable
```

Se muestran cálculos con **k = 3, provisional**: un acierto suma 1 y un falso
favorable resta 3. Son **puntos de utilidad por cada 100 oportunidades reales**,
no un porcentaje de acierto ni una probabilidad. TP y FP conservan la ponderación
entre siete horizontes; no se convierten las siete predicciones de una misma
observación en siete casos independientes.

La primera propuesta de la conversación dividía entre todos los casos `N`.
Medía beneficio por caso evaluado, pero su máximo dependía de cuántos favorables
reales hubiera. El usuario señaló que recomendar sólo 10 de cada 100 veces no
permite juzgar la utilidad sin saber cuántas oportunidades había. Por eso esta
propuesta usa `P`. **No se divide entre los consejos favorables del modelo**:
dividir entre `TP + FP` reduciría el índice a una transformación de la precisión
y perdería la proporción de oportunidades detectadas.

Ejemplo hipotético: en ambos escenarios hay 100 casos y se emiten 10 consejos
favorables, con 9 aciertos y 1 error. La precisión es idéntica, pero la utilidad
respecto a las oportunidades disponibles cambia:

| Favorables reales disponibles | Oportunidades detectadas | Precisión favorable | Índice con k = 3 |
|---|---:|---:|---:|
| 10 de 100 casos | 9 / 10 → 90,0% | 9 / 10 → 90,0% | +60,00 |
| 60 de 100 casos | 9 / 60 → 15,0% | 9 / 10 → 90,0% | +10,00 |

### Valores para A, B y C

Calculados desde los agregados sin redondear de
`tmp/prediction-model-selection/analysis/results.json`, ruta
`species.<especie>.strata.pooled.average`. Para caesarea `P = 35` de 61 casos;
para aereus `P = 36` de 55. Son los resultados del estudio de **selección del
ganador**: las letras A/B no se trasladan al estudio de umbrales, que compara
otros procedimientos. Las fracciones se muestran redondeadas, como en la tabla
conjunta; el índice se calcula con toda la precisión guardada.

| Especie | Variante | Oportunidades reales detectadas | Acierto cuando dice favorable | Índice con k = 3 (puntos) |
|---|---|---:|---:|---:|
| Caesarea | A | 8,71 / 35 → 24,9% | 8,71 / 15,29 → 57,0% | −31,43 |
| Caesarea | B | 13,14 / 35 → 37,6% | 13,14 / 15,57 → 84,4% | **+16,73** |
| Caesarea | C | 20,14 / 35 → 57,6% | 20,14 / 27,14 → 74,2% | −2,45 |
| Aereus | A | 17,57 / 36 → 48,8% | 17,57 / 25,29 → 69,5% | **−15,48** |
| Aereus | B | 12,86 / 36 → 35,7% | 12,86 / 21,00 → 61,2% | −32,14 |
| Aereus | C | 16,71 / 36 → 46,4% | 16,71 / 25,57 → 65,4% | −27,38 |

Con esta penalización, **B obtiene el mejor índice de caesarea**: sus pocos
falsos favorables compensan detectar menos oportunidades que C. En **aereus,
A queda por delante**, aunque todas las variantes tienen saldo negativo.
Cambiar `N` por `P` multiplica los índices de una misma especie por una constante
positiva: cambia la escala y su interpretación, pero no reordena A/B/C dentro
de esa especie.

### Cómo interpretar el índice y fijar un mínimo

- **100 puntos es el máximo:** detectar todos los favorables reales sin emitir
  falsos favorables. Este índice no distingue entre acertar un desfavorable y
  abstenerse en él; por eso alcanzar 100 no exige cobertura total de consejos.
- **0 puntos:** los beneficios compensan exactamente los errores. Abstenerse
  siempre también da 0 si hay favorables reales; no implica utilidad suficiente.
- **Un saldo negativo** indica que los errores pesan más que los aciertos con
  el coste elegido. No significa «ningún acierto» ni demuestra por sí solo que
  el modelo carezca de cualquier utilidad. La escala puede bajar de −100.
- Con recomendaciones favorables y `P > 0`, para obtener un saldo positivo la
  precisión debe superar `k / (1 + k)`: **75% cuando k = 3**. Por eso caesarea C,
  con 74,2%, queda ligeramente por debajo de cero. Ese requisito es consecuencia
  del peso provisional, no un mínimo de precisión ya aceptado por el usuario.
- Si `P = 0`, el índice es **NE**, no cero ni 100. Deben conservarse los recuentos
  de falsos favorables y los demás resultados de ese corte.

Se podría exigir **`I_k ≥ I_mínimo > 0`**. Un mínimo suficientemente exigente
descartaría recomendar casi nada cuando hay muchas oportunidades, pero **no fija por sí sola un número
absoluto suficiente de recomendaciones ni demuestra fiabilidad**. Acertar una
única recomendación sin errores da 1 punto si había 100 favorables reales, pero
100 puntos si sólo había uno. En este último caso se habría aprovechado toda la
oportunidad observada; una sola observación seguiría siendo evidencia insuficiente.
Saber únicamente que había 100 casos totales no basta para calcular el nuevo índice.

Por tanto, quedan **pendientes de acuerdo antes de otra evaluación**:

1. El coste `k`, sin escogerlo sólo para favorecer la variante que ya sale mejor.
2. El mínimo aceptable `I_mínimo`; el ejemplo de 5 puntos usado con el denominador
   anterior no queda trasladado ni aprobado para esta escala.
3. Qué frecuencia o cantidad de consejos favorables sería útil por campaña y qué
   soporte de observaciones y episodios independientes exigir para confiar en ella.
4. Cómo evaluar incertidumbre y estabilidad entre campañas. Un promedio favorable
   no elimina, por ejemplo, la campaña completa sin consejos de caesarea B en 2025.

**Estado para retomar:** propuesta matemática exploratoria, añadida después de
ver los resultados; no es un criterio predeclarado ni validado. Estos valores
son estimaciones puntuales, sin intervalos calculados para el nuevo índice.
No se ha seleccionado un `k` definitivo, un mínimo ni una variante operativa.
Normalizar por `P` no elimina los límites del muestreo: comparar procedimientos
sobre los mismos casos y revisar campañas y soporte, sin extrapolar este
resultado a la frecuencia real de recomendaciones del mapa. Una confirmación
posterior necesitará reglas fijadas de antemano y evidencia independiente.
Esta ampliación documental no lanza otro agente ni experimento, y no modifica
el protocolo cerrado, el selector, el umbral favorable 0,60 ni los modelos.

## Incertidumbre de las diferencias

Bootstrap pareado de 2.000 réplicas por episodios, estratificado por año; intervalos
percentiles del 95%, condicionados a los modelos ya ajustados.

| Especie | Contraste | Cambio FP [intervalo] | Cambio TP [intervalo] |
|---|---|---:|---:|
| Aereus | B−A | 0,43 [-2,71; 3,71] | -4,71 [-11,71; 2,00] |
| Aereus | C−B | 0,71 [-0,57; 2,29] | 3,86 [0,00; 9,00] |
| Aereus | C−A | 1,14 [-1,71; 4,29] | -0,86 [-6,00; 4,86] |
| Caesarea | B−A | -4,14 [-10,29; 1,43] | 4,43 [-4,14; 14,57] |
| Caesarea | C−B | 4,57 [0,29; 9,72] | 7,00 [-0,86; 15,71] |
| Caesarea | C−A | 0,43 [-2,14; 3,57] | 11,43 [2,57; 22,86] |

Estos intervalos tienen 2.000 réplicas válidas; otras métricas con denominadores
vacíos se detallan como NE. La mayoría de los intervalos de mejora cruzan cero.
Hay señales condicionales —por ejemplo más TP de C frente a A en caesarea—, pero
no borran el conocimiento previo del histórico ni incluyen toda la incertidumbre
de volver a aprender y seleccionar modelos. No son garantías operativas.

## Qué explica la repetición del ganador

El ranking sellado prioriza el límite inferior Wilson de la precisión favorable;
después desempatan precisión, número de consejos favorables, recall, incertidumbre,
Brier, calibración, AUC y clave estable. El punto conserva el primer candidato
aplicable de esa evidencia; no escoge el que dé mayor probabilidad favorable.
La agregación semanal favorece repetir familia, pero no siempre consigue imponerla.
En aereus B2025 y B2026 ya activa fallback diario; por eso C coincide allí con B.

En caesarea B, V6 compartido/logístico, ventana de 90 días y contrato lag concentra
el 95,3% de los ganadores con probabilidad disponible. C baja la concentración
de su familia dominante al 16,8% y cambia de familia en 1.139 de 2.199 pares de
días con ganador. Es evidencia de que el procedimiento influye en la repetición,
pero **variar más no garantiza equivocarse menos**. Son frecuencias del experimento,
con semanas solapadas; no una inspección del mapa activo.

Acumular historia tampoco garantiza estabilidad: en el ranking B2025, retirar
un episodio deja al mismo ganador sólo el 13,3–33,3% de las veces en aereus y el
5,6–38,9% en caesarea, según horizonte. El catálogo ya calcula esta sensibilidad;
no se usaron los resultados externos para cambiar reglas.

## Límites y siguiente investigación posible

Los 68 casos objetivo anteriores a 2024 intervienen en desarrollo. El antiguo
30% no es una reserva independiente frente al reajuste final. Los externos usados
aquí están fuera de sus ajustes experimentales, pero ya habían orientado las
hipótesis: esta investigación sigue siendo retrospectiva y exploratoria.

Hay sólo 20 episodios externos de aereus y 31 de caesarea; 32 distintos contando
ambas especies conjuntamente. En 2026 quedan cuatro y cinco respectivamente.
Además, 47/55 casos de aereus y 42/61 de caesarea pertenecen a áreas presentes en
algún entrenamiento previo de la cohorte. Área conocida no significa punto exacto
conocido, y esta separación temporal no demuestra transferencia a lugares nuevos.
La meteorología reconstruida no acredita disponibilidad exacta de datos en la
fecha original. La preparación heredada y sus límites constan en el primer estudio.

Una continuación útil sería contrastar que la selección semanal descarte antes
las familias que ya incumplen filtros conocidos del catálogo, o recupere las
alternativas diarias si ninguna familia semanal resulta elegible. Es una hipótesis
nueva que debe mantener los filtros y fijarse antes de otra comparación; no se
añadió una variante D después de observar el fallo de B2025.
El intercambio de C para caesarea también merece una hipótesis separada, con un
coste aceptable de falsos favorables acordado antes de mirar nueva evidencia.
Ninguna de esas propuestas se lanza como efecto secundario de este cierre.

Para confirmar una eventual regla: congelarla y registrar predicciones fechadas
antes de futuras salidas, mantener negativos explícitos, registrar las visitas
con independencia del consejo y fijar previamente muestra, agrupación y cierre.
El tamaño deberá responder a la precisión que se quiera exigir y a la viabilidad
real; no se afirma que unas pocas observaciones nuevas basten.

## Verificación, coste y procedencia

Los tres catálogos antiguos se reprodujeron exactamente. Pasaron las 812 emisiones
de control y 19.514 comparaciones de preparación meteorológica compartida B/C.
Las 35 pruebas dirigidas pasan. Las correcciones del parsing de exclusiones y del
fallback diario conservan sus intentos fallidos y las fuentes exactas ejecutadas.
El corte 2024 conserva su código original: no se le atribuye retroactivamente el nuevo.

Este estudio contabiliza unos 27 minutos de lotes, incluyendo un margen conservador
por el fallo inicial del supervisor; ambos estudios suman unos 47 de los 120 minutos.
El pico RSS muestreado de este estudio fue 786 MB, bajo el límite de 8 GiB.
Sus artefactos suman unos 161 MB; ambos estudios, 1,39 GB de tamaño de archivos,
bajo el techo conjunto de 2 GiB. Estas cifras no son una medición del disco de Finder.
El coste corresponde al arnés pareado con control y reutilización; no permite
comparar latencias de producción entre variantes ni extrapolarlas a HA real.

Fuentes: `tmp/prediction-model-selection/analysis/results.json`, resúmenes y sellos
de cada corte, y ledgers `runs/`. [Tablas completas](tablas-2026-10-04.md),
[protocolo](protocolo-ejecucion-2026-10-04.md), [enmienda técnica](protocolo-correccion-daily-fallback-2026-10-04.md)
y [reproducibilidad](reproducibilidad.md). El cierre técnico queda en
`tmp/prediction-model-selection/closure.json`. Datos originales, estudio anterior,
modelos activos y operación se conservan; no se ejecutó entrenamiento operativo
ni despliegue ni se cambió el worker o su coordinador.

Actualización de presentación del 04/10/2026: se añaden denominadores, porcentajes
y referencias ideales a la tabla conjunta. Los resultados experimentales y el
cierre original se conservan. Versión anterior y registro de esta edición en
`tmp/prediction-model-selection/documentation-amendments/2026-10-04-table-denominators/`.

Ampliación explicativa del 04/10/2026: guía de lectura de columnas en ambos informes
y justificación por campaña de caesarea B en el estudio de selección. Se conservan
resultados y criterios del experimento; versiones anteriores y hashes en
`tmp/prediction-model-selection/documentation-amendments/2026-10-04-reading-guide-and-caesarea-b/`.

Ampliación de caesarea C del 04/10/2026: el desglose anual incluye A/B/C y se
explican los intercambios de C frente a A y B, sin cambiar reglas ni resultados.
Registro: `tmp/prediction-model-selection/documentation-amendments/2026-10-04-caesarea-c-explanation/`.

Ampliación de utilidad del 04/10/2026: preferencia explícita del usuario, propuesta
de índice normalizado por favorables reales, seis valores A/B/C y decisiones
pendientes. Se conserva el cálculo experimental original; versiones previas,
comprobación de las cifras y hashes en
`tmp/prediction-model-selection/documentation-amendments/2026-10-04-opportunity-utility-index/`.
