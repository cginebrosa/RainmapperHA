# Informe 001 de consenso entre algoritmos — V2, V3 y V4

> Informe histórico. Queda reemplazado para decisiones por
> `V2_V3_V4_consensus_report002.md`, que usa el snapshot canónico de 395
> observaciones y corrige la evaluación `lag_event` para no reentrenar por
> horizonte.

Fecha del análisis: 2026-08-16.

## 1. Pregunta que responde

Este informe estudia qué algoritmos producen predicciones parecidas y cuáles
obtienen mejor Brier para cada especie. Incluye:

- V2 reconstruida sobre la meteorología IDW común;
- V3;
- V4 con meteorología ampliada;
- V4 con meteorología ampliada y balance climático.

V4 core no se repite porque reproduce exactamente V3. No se modifica la V2
desplegada ni se entrena o promociona ningún artefacto operativo.

El objetivo no es elegir todavía un conjunto de modelos, sino comprobar si
existe una agrupación estable que merezca estudiarse como predicción conjunta.

## 2. Qué significa consenso

Dos algoritmos se comparan sobre la misma fila de test y para la misma especie.
Se conservan tres medidas distintas:

1. Diferencia absoluta entre sus probabilidades. El contrato existente llama
   acuerdo alto a una diferencia de hasta 0,10, moderado a una diferencia entre
   0,10 y 0,20 y bajo a una diferencia igual o superior a 0,20.
2. Porcentaje de filas en las que ambos quedan al mismo lado de 0,5.
3. Brier de cada algoritmo frente al resultado observado.

La tercera medida es imprescindible. Dos modelos pueden coincidir porque han
aprendido casi la misma función y, aun así, equivocarse juntos. Por ese motivo
este informe no crea una puntuación mezclando acuerdo y Brier.

El orden de selección futuro será siempre calidad primero y consenso después:

1. identificar por especie y contrato los algoritmos con Brier competitivo y
   mejora estable frente a la prevalencia;
2. estudiar el acuerdo solo dentro de ese grupo;
3. comprobar si una combinación mejora al mejor algoritmo individual;
4. no activar la combinación si solo consolida dos predicciones parecidas pero
   peores.

Tampoco calcula un Brier medio entre especies. Los recuentos indican cuántas
veces ocurre un resultado en cuatro validaciones emparejadas:

- `fixed_gap`, grupos de florada de 7 días;
- `fixed_gap`, grupos de 14 días;
- `lag_event`, grupos de 7 días;
- `lag_event`, grupos de 14 días.

## 3. Soporte real de datos

Solo nueve especies tienen clases y muestras suficientes en entrenamiento y
test para calcular estas métricas. Las demás especies se conservan en el
benchmark, pero no se les inventa una evaluación.

| Especie | Observaciones de entrenamiento | Observaciones de test |
|---|---:|---:|
| `amanita_caesarea` | 41–42 | 24–25 |
| `boletus_aereus` | 41–43 | 26–28 |
| `boletus_edulis` | 20 | 11 |
| `boletus_pinophilus` | 33 | 25 |
| `cantharellus_cibarius_sl` | 6 | 4 |
| `hygrophorus_latitabundus` | 7 | 4 |
| `hygrophorus_marzuolus` | 19 | 6 |
| `lactarius_deliciosus` | 30 | 16 |
| `morchella_elata_complex` | 11–12 | 5–6 |

En `lag_event` cada observación produce cuatro horizontes y, por ello, aparecen
más filas. No son observaciones independientes nuevas. Las conclusiones sobre
`cantharellus_cibarius_sl`, `hygrophorus_latitabundus` y las especies con solo
5–6 observaciones de test deben considerarse especialmente provisionales.

Las observaciones revisadas por el usuario después de construir estos ficheros
todavía no están incluidas. Se incorporarán en la siguiente reconstrucción.

## 4. Resultado global de consenso

Random forest y extra trees son la pareja que más se parece en las cuatro
familias evaluadas:

| Contrato de variables | Veces que RF+ET es la pareja más próxima | Casos evaluados | Diferencia media inferior a 0,20 |
|---|---:|---:|---:|
| V2 con IDW común | 24 | 36 | 36/36 |
| V3 | 20 | 36 | 36/36 |
| V4 meteorología ampliada | 22 | 36 | 36/36 |
| V4 balance climático | 22 | 36 | 36/36 |

Es un resultado coherente: ambos son conjuntos de árboles y pueden aprender
fronteras parecidas. Precisamente por eso su coincidencia aporta menos
independencia de la que aportaría el acuerdo entre algoritmos de familias
distintas.

Además, extra trees casi nunca es el algoritmo con menor Brier: lo es en 4 de
36 casos V2, 1 de 36 V3 y 4 de 36 en cada ampliación V4. RF+ET es, por tanto, el
consenso más estable, pero no puede declararse la mejor combinación operativa.

## 5. Algoritmo con menor Brier

La tabla cuenta cuántas veces cada algoritmo obtiene el menor Brier dentro de
su especie y validación. Un empate puede hacer que una fila sume más de 36.

| Contrato | LR | RF | ET | HGB | KNN | SVM |
|---|---:|---:|---:|---:|---:|---:|
| V2 con IDW común | 1 | 5 | 4 | 8 | 7 | 11 |
| V3 | 9 | 8 | 1 | 2 | 8 | 8 |
| V4 meteorología ampliada | 10 | 8 | 4 | 2 | 3 | 10 |
| V4 balance climático | 10 | 7 | 4 | 0 | 1 | 14 |

Abreviaturas: LR, regresión logística; RF, random forest; ET, extra trees;
HGB, HistGradientBoosting; KNN, vecinos por distancia; SVM, SVM RBF calibrada.

No existe un ganador universal. SVM destaca con V2 y con el balance V4; LR
gana mucha presencia desde V3; HGB es competitivo en V2 pero pocas veces es el
mejor absoluto con las variables posteriores. Esto no contradice que HGB
mejore su propio Brier al pasar de V3 a V4: puede mejorar y seguir por detrás de
otro algoritmo.

## 6. Resultado por especie

Cada celda muestra el algoritmo que obtiene el menor Brier con más frecuencia
y en cuántas de las cuatro validaciones. Los empates se conservan.

| Especie | V2 | V3 | V4 meteo | V4 balance |
|---|---|---|---|---|
| `amanita_caesarea` | ET y RF, 2/4 | LR, 3/4 | RF, 3/4 | ET y RF, 2/4 |
| `boletus_aereus` | SVM, 3/4 | SVM, 4/4 | SVM, 3/4 | SVM, 3/4 |
| `boletus_edulis` | HGB y RF, 2/4 | LR y RF, 2/4 | LR y RF, 2/4 | LR y RF, 2/4 |
| `boletus_pinophilus` | SVM, 4/4 | RF, 4/4 | HGB y RF, 2/4 | ET y SVM, 2/4 |
| `cantharellus_cibarius_sl` | ET y HGB, 2/4 | HGB y RF, 2/4 | ET y LR, 2/4 | LR y RF, 2/4 |
| `hygrophorus_latitabundus` | SVM, 4/4 | KNN y SVM, 2/4 | KNN y SVM, 2/4 | SVM, 4/4 |
| `hygrophorus_marzuolus` | KNN, 4/4 | KNN y SVM, 2/4 | SVM, 4/4 | SVM, 4/4 |
| `lactarius_deliciosus` | HGB, 4/4 | LR, 4/4 | LR, 4/4 | LR, 4/4 |
| `morchella_elata_complex` | KNN, 3/4 | KNN, 4/4 | LR, 2/4 | LR, 2/4 |

Los patrones más estables son:

- `boletus_aereus`: SVM es el mejor en 13 de las 16 combinaciones
  versión+validación.
- `lactarius_deliciosus`: cambia de HGB en V2 a LR, que gana las 12
  validaciones de V3 y las dos variantes V4.
- `hygrophorus_marzuolus`: pasa de KNN en V2 a SVM en las dos variantes V4.
- `boletus_pinophilus`: el ganador cambia mucho con el contrato; no hay un
  consenso de calidad estable entre versiones.

En `boletus_edulis` ningún algoritmo gana más de dos de cuatro validaciones
dentro de una versión. LR y RF son los candidatos más repetidos desde V3, pero
el soporte sigue siendo de solo 20 observaciones de entrenamiento y 11 de test.

## 7. ¿El mejor ML aporta información?

Para evitar celebrar un consenso que solo repite la frecuencia de positivos,
se comprobó si el mejor de los seis algoritmos supera al predictor ingenuo que
usa la prevalencia del conjunto de entrenamiento.

| Especie | V2 | V3 | V4 meteo | V4 balance |
|---|---:|---:|---:|---:|
| `amanita_caesarea` | 4/4 | 4/4 | 4/4 | 4/4 |
| `boletus_aereus` | 4/4 | 3/4 | 3/4 | 2/4 |
| `boletus_edulis` | 4/4 | 4/4 | 4/4 | 4/4 |
| `boletus_pinophilus` | 2/4 | 4/4 | 4/4 | 4/4 |
| `cantharellus_cibarius_sl` | 2/4 | 4/4 | 4/4 | 4/4 |
| `hygrophorus_latitabundus` | 4/4 | 2/4 | 4/4 | 4/4 |
| `hygrophorus_marzuolus` | 4/4 | 2/4 | 4/4 | 4/4 |
| `lactarius_deliciosus` | 4/4 | 4/4 | 4/4 | 4/4 |
| `morchella_elata_complex` | 4/4 | 3/4 | 2/4 | 2/4 |

V4 recupera una señal clara frente a prevalencia en `hygrophorus_latitabundus`
y `hygrophorus_marzuolus`, pero la pierde parcialmente en
`boletus_aereus` y `morchella_elata_complex`. De nuevo, no hay una mejora
general para todas las especies.

## 8. Parejas potencialmente útiles

Con los datos actuales no se debe fijar una pareja universal. Las señales que
sí merecen conservarse para la siguiente reconstrucción son:

- RF+ET: acuerdo muy estable en todas las versiones, pero algoritmos poco
  independientes y ET rara vez es el mejor. Es un control de estabilidad, no
  una elección automática.
- V3 para `boletus_edulis`: RF+ET se mantienen próximos y ambos superan la
  prevalencia en las cuatro validaciones, aunque LR/RF son quienes acumulan más
  primeros puestos.
- V4 meteorología ampliada para `hygrophorus_latitabundus`: KNN y SVM superan
  la prevalencia y se mantienen de acuerdo en las cuatro validaciones; además
  se reparten los cuatro mejores Brier.
- V4 para `lactarius_deliciosus`: varios algoritmos superan la prevalencia y
  coinciden, pero LR obtiene el menor Brier en las ocho validaciones V4. Añadir
  modelos similares podría no aportar nada sobre LR.
- V4 balance para `amanita_caesarea` y `cantharellus_cibarius_sl`: RF+ET
  muestran acuerdo y calidad en las cuatro validaciones, aunque el tamaño de
  test de `cantharellus_cibarius_sl` es demasiado pequeño para decidir.

## 9. Decisión que permiten estos datos

No hay evidencia para activar ahora un consenso operativo fijo de los seis
algoritmos. Tampoco hay evidencia para eliminar ninguno:

- los seis se conservan, entrenan, validan y documentan;
- el algoritmo o conjunto usado para predecir podrá variar por especie y
  contrato, mediante configuración versionada y no por `if` hardcodeado;
- una futura combinación deberá compararse contra el mejor algoritmo individual
  de esa especie, no solo contra la prevalencia;
- las nuevas observaciones revisadas deben incorporarse antes de convertir
  estos patrones en una decisión.

El siguiente informe debe repetir exactamente este análisis tras reconstruir
los datos actualizados. Si los ganadores y las parejas cambian con tres o cuatro
observaciones, eso será evidencia directa de que el soporte todavía es
insuficiente para promover un consenso.

También queda definido un segundo análisis: construir perfiles de error de los
seis modelos —falsos positivos/negativos, calibración, fase de la florada y
condiciones meteorológicas— para decidir si falta otra familia de modelos. Un
nuevo algoritmo solo se incorporará si responde a un error compartido o a una
limitación concreta. Posibles hipótesis a contrastar, no decisiones tomadas:

- curvas aditivas suaves si los umbrales son no lineales pero los árboles
  resultan demasiado discontinuos;
- un modelo temporal de estado/duración si el error común es el parpadeo dentro
  de una florada;
- un modelo jerárquico si compartir información entre especies relacionadas
  mejora las especies con pocas observaciones sin segmentar por área.

No se justifica añadir redes neuronales ni otros modelos de alta capacidad con
el volumen actual solo por ampliar la lista.

## 10. Ficheros de evidencia

- `/private/tmp/biology-v2-v3-v4-fixed-common-idw-groups7.json`
- `/private/tmp/biology-v2-v3-v4-fixed-common-idw-groups14.json`
- `/private/tmp/biology-v2-v3-v4-lag-common-idw-groups7.json`
- `/private/tmp/biology-v2-v3-v4-lag-common-idw-groups14.json`

Son artefactos locales de evaluación. No son modelos ni deben promocionarse.
