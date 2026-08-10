# Diagnóstico y plan de endurecimiento de los modelos ML de setas

Estado: diagnóstico reproducido con HA `0.2.242`, worker `1.0.4` y los
artefactos reconstruidos y reentrenados el 2026-08-10.

Este documento es la referencia de trabajo para la siguiente fase del
Predictor: pulir los modelos actuales y comparar alternativas que puedan
gestionarse y explicarse mejor con el dataset disponible.

La restricción operativa es explícita: de momento no hay más observaciones de
salidas ni más cobertura meteorológica histórica. El trabajo debe mejorar la
honestidad y utilidad del Predictor usando los datos actuales. Nuevas
observaciones permitirán recalibrarlo en el futuro, pero no son un requisito
para empezar esta fase.

El muestreo tampoco es aleatorio. Las salidas se realizan principalmente
cuando el observador experto ya considera probable encontrar setas; los días
que parecen claramente desfavorables normalmente no se visitan. En
consecuencia, la prevalencia aprendida describe el porcentaje favorable entre
salidas previamente seleccionadas, no la frecuencia real entre todos los
días-área posibles. El baseline incorpora parte del criterio previo del
observador y puede ser difícil de superar con pocos fallos documentados.

No se crearán negativas sintéticas a partir de días no visitados. Una ausencia
solo puede considerarse negativa si consta que la especie se buscó con esfuerzo
suficiente. Encontrar otra especie en una salida tampoco demuestra por sí solo
la ausencia de la especie objetivo. Hasta disponer de un contrato de visita o
checklist de especies buscadas, los días y especies no comprobados son
desconocidos. Los scores deben interpretarse como señal condicionada al
muestreo de salidas, no como probabilidad incondicional de cualquier día.

Documentos relacionados:

- `mushroom-ml-training-plan-es.md`: contrato general de entrenamiento.
- `mushroom-ml-experiment-contract-es.md`: contrato temporal y benchmark
  versionado para comparar nuevas variables y estimadores.
- `mushroom-predictor-design-es.md`: comportamiento funcional del Predictor.
- `mushroom-observations-schema-es.md`: semántica de las observaciones y del
  objetivo operativo.

## Caso centinela: Aereus en Coll de la Batalla

Consulta reproducida:

```text
especie: Boletus aereus
área: Coll de la Batalla
fecha: 2026-08-14
estación: ILALEI9, a 2,08 km
resultado: 71,1% favorable
LR: 98,2%
RF: 44,0%
```

El ensemble actual es la media aritmética sin ponderar de los modelos
disponibles:

```text
(98,2% + 44,0%) / 2 = 71,1%
```

La consulta se conservará como caso centinela de regresión. Con cero lluvia
reciente y calor intenso, el sistema no debe presentar una recomendación
favorable de alta confianza por interpretar como meteorología real los días
posteriores al último dato observado.

## Meteorología que recibió el modelo

La interfaz mostraba `0,0 mm` en 7 y 14 días. La estación sí tenía una serie
diaria completa hasta el 2026-08-10; la consulta terminaba el 2026-08-14 y las
ausencias eran cuatro días futuros, no huecos del Parquet:

| Ventana | Días con dato | Valor construido |
|---|---:|---:|
| 1 día | 0/1 | ausente; imputado posteriormente a 0 |
| 7 días | 3/7 | 0,0 mm |
| 14 días | 10/14 | 0,0 mm |
| 21 días | 16/21 | 3,05 mm |
| 30 días | 24/30 | 6,10 mm |

También se detectaron dos fechas de lluvia consecutiva sospechosamente
repetidas, 2026-07-21 y 2026-07-28.

Las derivadas agravaron la interpretación. Al avanzar más allá del último día
observado, el primer día futuro ausente hizo que algunas rachas quedaran en
cero en lugar de desconocidas:

- `days_since_significant_rain` no pudo calcularse y el `SimpleImputer` lo
  sustituyó por la mediana de entrenamiento: 6 días;
- `rain_1d_mm` ausente se imputó a 0;
- `dry_spell_days` pasó de 12 días el 10/08 a 0 a partir del 12/08;
- `heat_stress_days` pasó de 30 días el 10/08 a 0 al atravesar un día futuro
  sin dato;
- los avisos de cobertura se muestran al usuario, pero no reducen la
  probabilidad ni provocan abstención del modelo.

El salto 20% -> 71% quedó dominado por esas dos derivadas: en LR, solamente
`heat_stress_days` aportó aproximadamente +33,34 puntos de log-odds al cambiar
artificialmente de 30 a 0, y `dry_spell_days` otros +3,33. Por tanto, el 71% no
es una respuesta del modelo a la sequedad real, sino una violación del corte
temporal en la construcción de variables futuras.

Debe distinguirse siempre:

```text
0 mm observados con cobertura completa != día futuro desconocido
```

## Qué aprendió la regresión logística

Las contribuciones principales al logit de la predicción fueron:

| Variable | Valor | Contribución al logit |
|---|---:|---:|
| `temp_min_7d_c` | 20,94 °C | +2,037 |
| `temp_max_14d_c` | 36,33 °C | -1,693 |
| `humidity_max_14d_pct` | 94% | +1,450 |
| `humidity_max_7d_pct` | 91% | +1,410 |
| `rain_14d_mm` | 0 mm | +1,298 |
| `rainy_days_14d` | 0 | +1,224 |
| `temp_mean_14d_c` | 27,24 °C | -1,034 |

La ausencia de lluvia en 14 días y la ausencia de días lluviosos empujan la
probabilidad hacia favorable. No es una relación micológica defendible; es una
correlación aprendida de una muestra pequeña, incompleta y confundida por otras
variables.

El propio dataset ayuda a explicar el signo invertido:

| Target Aereus | Episodios con lluvia 14d | Mediana lluvia 14d |
|---|---:|---:|
| Favorable | 23 | 56,89 mm |
| Desfavorable | 16 | 69,70 mm |

En esta muestra llovió más, en mediana, antes de episodios desfavorables. La
lluvia es necesaria pero no suficiente; el modelo lineal ha convertido esa
confusión en la conclusión errónea «menos lluvia favorece».

Coll de la Batalla aporta nueve episodios de Aereus. Seis episodios favorables
antiguos no tienen ninguna variable meteorológica y se entrenan con valores
imputados; solo dos desfavorables y un favorable tienen meteorología. Esto
reduce aún más la capacidad de aprender la relación local real.

## Fenología insuficientemente condicionada

El perfil de Aereus declara septiembre y octubre como meses principales, y
junio, julio, agosto y noviembre como secundarios. También describe las salidas
estivales como posteriores a lluvia y un retraso de fructificación de 5 a 21
días.

La implementación actual solo usa la fenología como barrera binaria:

- fuera de meses principales/secundarios: no ejecuta ML;
- dentro de un mes permitido: ejecuta el mismo modelo sin exigir el evento de
  lluvia asociado a una temporada secundaria.

En el caso centinela, la contribución de `month=8` al logit fue `+0,001`,
prácticamente nula. Agosto permite entrar al modelo, pero ni penaliza la
temporada secundaria ni exige una tormenta estival compatible.

## Tamaño, dimensionalidad y validación

El modelo productivo de Aereus se ajustó con:

- 51 episodios: 34 favorables y 17 desfavorables;
- 39 variables;
- entre un 23,5% y un 39,2% de ausencias en muchas variables meteorológicas;
- 35 episodios en el tramo temporal antiguo y 16 en el reciente para la
  evaluación cronológica adicional.

Hay casi tantas variables como episodios y varias ventanas contienen medidas
muy correlacionadas. El ajuste productivo con todos los episodios puede separar
muy bien su propia muestra, pero eso no demuestra capacidad predictiva.

Resultados del holdout temporal:

| Modelo | ROC-AUC | Accuracy | Recall favorable | F1 |
|---|---:|---:|---:|---:|
| Regresión logística | 0,3818 | 0,2500 | 0,0909 | 0,1429 |
| Random forest | 0,4545 | 0,3750 | 0,0909 | 0,1667 |
| Ensemble actual | — | 0,1875 | — | — |

Un ROC-AUC inferior a 0,5 indica que, en ese tramo reciente, la ordenación fue
peor que el azar. Aun así, ambos modelos reciben el mismo peso y el Predictor
muestra el promedio como un porcentaje favorable normal.

La CV estratificada (`0,6722` para LR y `0,7182` para RF) sirve como diagnóstico
adicional, pero no invalida el mal resultado temporal. Con datos correlacionados
por fecha, zona y condiciones meteorológicas puede ser optimista.

## Diagnóstico consolidado

El 71% no significa que el modelo haya encontrado condiciones adecuadas de
fructificación. Es el resultado conjunto de:

1. cobertura de lluvia incompleta tratada en parte como cero real;
2. variables derivadas imposibles de calcular sustituidas por medianas que
   describen una situación distinta;
3. demasiadas variables correlacionadas para 51 episodios;
4. episodios favorables históricos sin meteorología;
5. relaciones aprendidas con signo físicamente dudoso;
6. fenología secundaria que permite agosto sin exigir lluvia previa;
7. probabilidades no calibradas presentadas como porcentajes;
8. media 50/50 de dos modelos que no superan el azar en el holdout temporal.

Hasta resolverlo, las probabilidades actuales son resultados experimentales.
No deben interpretarse como frecuencia real ni como confianza calibrada.

## Casos pendientes de revisión del laboratorio operativo

### Racha térmica fuera del dominio: Olvan, 2026-08-15

En Ou de reig, `fixed_gap_7d_v1` dio LR `0%` y `lag_event_v1` LR
`100%`. Ambos recibieron la misma estación y meteorología coherente, pero
`heat_stress_observed_at_cutoff` tomó valores de 58 y 59 días consecutivos por
encima de 28 °C. En el benchmark de Ou de reig y Aereus esta variable nunca
superó 8 días. La LR la recibió a 36-47 desviaciones estándar del entrenamiento
y dos coeficientes inestables de signo contrario saturaron el resultado en los
dos extremos.

Con el laboratorio ampliado, KNN apenas cambia durante la semana porque
mantiene los mismos siete vecinos y sus distancias relativas varían muy poco.
La SVM queda exactamente plana (Ou de reig 50,04%/53,92%; Aereus
66,03%/66,65%): la distancia estandarizada extrema hace que el kernel RBF tenga
similitud casi nula con todos los ejemplos y la calibración devuelva su nivel
base. Esos valores constantes son diagnóstico de extrapolación, no evidencia
meteorológica estable.

Pendiente:

- extender la política fuera de dominio a los modelos sombra y distinguir
  score visible de score interpretable;
- comparar racha acotada, `log1p` y recuentos de días cálidos en ventanas
  fijas de 7/14/21 días;
- conservar este caso como prueba centinela.

### Florada observada: Santa Maria de Merlès, 2025-09-30

El usuario confirma una salida muy favorable de Aereus y Ou de reig. Ou de
reig produce una señal incierta pero operativamente plausible; Aereus se
abstiene aunque sus scores brutos son altos. Debe revisarse la presencia y
partición del episodio en el benchmark y separar claramente dos mensajes:
score favorable del ajuste y falta de validación global del estimador. Este
caso se conserva como segundo centinela de falsos negativos o abstenciones
excesivamente globales.

La revisión confirma que el episodio está presente y etiquetado `favorable`
para ambas especies. En la partición estratificada 70/30 quedó en `train`; en
el diagnóstico cronológico quedó en `test`. El modelo de consulta se reajustó
después con todos los episodios, por lo que sus scores sobre esa fecha ya han
visto la propia salida y no constituyen un backtest independiente. Para
consultas históricas con observación conocida debe mostrarse una predicción
out-of-fold o leave-one-episode-out, o advertirse explícitamente la inclusión
del episodio en el ajuste.

En Aereus, el bloqueo por prevalencia es global para los bundles actuales, no
específico de Santa Maria de Merlès: fixed-gap obtiene Brier `0,26` (LR) y
`0,28` (RF) frente al baseline `0,22`; lag/event obtiene `0,30` y `0,29` frente
a `0,22`. Mientras ningún estimador mejore ese suelo fuera de muestra, todas
las consultas de Aereus se abstienen aunque el ajuste completo produzca scores
altos. Pendiente revisar si el filtro debe seguir siendo global por especie o
si se puede estimar fiabilidad por régimen sin fragmentar todavía más una
muestra pequeña.

### Prueba prospectiva: Pinícola en Guils y Salteguet, 2026-08-15

El usuario prevé visitar ambas áreas por lluvia reciente, época y conocimiento
de campo. Se registra antes de conocer el resultado para evitar sesgo
retrospectivo.

| Área | Fixed: HGB* | Lag/event: SVM* | Dictamen operativo previo |
|---|---:|---:|---|
| Guils | 98% | 71% | Incierto, referencia RF 52–58% |
| Salteguet | 88% | 62% | Incierto, referencia RF 50–52% |

HGB es el mejor Brier de Pinícola/fixed (`0,1013`) y SVM el mejor de
Pinícola/lag-event (`0,1449`), ambos frente a prevalencia `0,2317`. Los scores
no son probabilidades calibradas, pero la dirección de ambos contratos es
favorable y Guils queda por encima de Salteguet. Después de la salida se debe
registrar resultado, abundancia, áreas realmente prospectadas y posibles
microáreas no visitadas.

## Objetivo de la siguiente fase

Conservar el máximo de información útil del dataset actual, pero reducir la
capacidad del pipeline para producir seguridad falsa. El resultado buscado no
es necesariamente un modelo más complejo: puede ser un sistema híbrido más
sencillo, explicable y capaz de responder «datos insuficientes».

La comparación debe contestar estas preguntas:

1. ¿Qué parte de la señal supera a un baseline trivial por especie?
2. ¿Qué variables mantienen un efecto estable entre particiones?
3. ¿Qué modelo generaliza mejor a fechas posteriores?
4. ¿Cuándo debe abstenerse por cobertura meteorológica insuficiente?
5. ¿Cómo combinar fenología, requisitos ecológicos y señal estadística sin
   ocultar qué componente decide?

El objetivo de producto no es imitar el porcentaje favorable de las salidas
ya filtradas por el observador, sino superponer una vigilancia sistemática que
una persona no puede realizar diariamente para todas las especies, áreas,
estaciones y horizontes. Por ello, prevalencia y Brier siguen siendo controles
de calibración, pero no deben silenciar una señal útil para ranking. El
Predictor distinguirá señal no validada de recomendación validada y medirá
también recuperación de floradas, ordenación de candidatos, precisión en el
top-k y acierto prospectivo de recomendaciones congeladas antes de la salida.

## Plan de trabajo con los datos actuales

### 1. Congelar un benchmark reproducible

- Usar el snapshot reconstruido del 2026-08-10 como primer benchmark.
- Guardar para cada especie episodios, clases, cobertura, particiones y semillas.
- Incorporar el caso Aereus/Coll/2026-08-14 como prueba centinela.
- Comparar todos los candidatos sobre exactamente las mismas particiones.
- Añadir baseline mayoritario y prevalencia por especie; ningún estimador se
  considera útil si no los mejora fuera de muestra.

### 2. Corregir semántica de huecos antes de cambiar de algoritmo

- No convertir cobertura parcial en cero observado sin conservar esa diferencia.
- Calcular `dry_spell_days` y `days_since_significant_rain` solo cuando exista
  continuidad suficiente.
- Separar imputación necesaria para sklearn de la validez operativa de una
  predicción.
- Definir estados de abstención o confianza reducida para features críticas.
- Evaluar si los episodios históricos sin meteorología deben excluirse del
  estimador meteorológico o alimentar solo componentes espaciales/fenológicos.

### 3. Reducir variables y colinealidad

- Partir de un subconjunto pequeño, aproximadamente 6-10 variables justificadas.
- Evitar introducir simultáneamente todas las ventanas 7/14/21/30 de la misma
  magnitud sin demostrar mejora fuera de muestra.
- Representar calendario de forma circular si permanece como predictor.
- Hacer ablation tests: meteorología sola, fenología sola, contexto estático y
  combinaciones incrementales.
- Revisar estabilidad de signos y efectos, no solo importancia global.

### 4. Comparar candidatos gestionables

| Candidato | Función en la comparación |
|---|---|
| Prevalencia/baseline constante | Suelo mínimo que todo modelo debe superar |
| LR regularizada con pocas variables | Baseline interpretable principal |
| RF muy restringido y hojas grandes | Capturar interacciones sin memorizar episodios |
| Extra Trees restringido | Contrastar la estabilidad de particiones aleatorias más decorrelacionadas |
| Boosting poco profundo | Capturar interacciones graduales; candidato solo si mejora de forma estable |
| KNN por distancia | Contrastar con episodios meteorológicos locales parecidos |
| SVM RBF calibrada | Probar fronteras no lineales; se omite si una clase tiene menos de dos ejemplos en train |
| Reglas ecológicas + modelo estadístico | Evitar recomendaciones incompatibles y permitir abstención |

No se priorizan redes neuronales, modelos temporales profundos ni nuevas
dependencias pesadas. Con la muestra actual aumentarían complejidad y riesgo de
sobreajuste sin resolver los huecos de origen.

### 5. Endurecer validación y selección

- Mantener holdout temporal y añadir varios cortes temporales cuando las clases
  lo permitan.
- Agrupar por fecha/salida cuando varias áreas compartan la misma situación
  meteorológica, para reducir fuga entre folds.
- Publicar intervalos de incertidumbre mediante bootstrap cuando sea viable.
- Medir balanced accuracy, precision, recall, PR-AUC, ROC-AUC, Brier score y
  log loss; no seleccionar solo por accuracy.
- Ejecutar pruebas de etiquetas permutadas y sensibilidad a imputación como
  controles contra señal espuria.
- No promocionar automáticamente el candidato que gane una única métrica.

### 6. Separar elegibilidad, score y confianza

El Predictor debería distinguir tres conceptos:

```text
elegibilidad ecológica/estacional
    + score estadístico fuera de muestra
    + confianza según cobertura y calidad
```

Una fecha puede estar dentro de temporada y aun así no cumplir las condiciones
de activación de una temporada secundaria. Un score alto con lluvia incompleta
puede terminar en «datos insuficientes», no en favorable.

Los umbrales ecológicos no deben inventarse silenciosamente. Los ya presentes
en el perfil —por ejemplo lluvia significativa y retraso de fructificación— se
tratarán como hipótesis explícitas y se probarán contra el mismo benchmark.

La interfaz y el payload de interpretación separan desde la iteración local
`1.1` tres respuestas que antes quedaban mezcladas:

1. **Compatibilidad ecológica**: `compatible`, `incompatible`, `unknown` o
   `out_of_season`. La barrera de lluvia puede emitir un veto aunque la capa
   estadística se abstenga.
2. **Soporte estadístico**: `unavailable`, `limited`, `moderate` o `strong`.
   Solo cuenta familias de estimadores operativos que mejoran el Brier de la
   prevalencia y no están excluidas por dominio.
3. **Dictamen práctico**: favorable, incierto, poco probable, fuera de
   temporada o sin recomendación fiable.

El consenso solo existe si quedan al menos dos familias validadas e
independientes. Dos cortes que escogen el mismo RF aportan un rango entre
fechas de corte, pero no constituyen dos votos: se muestra «soporte limitado»
y no «consenso bajo». La calidad ecológica describe la fiabilidad del evento,
la estación y la cobertura; nunca debe llamarse simplemente «confianza» porque
podría confundirse con confianza estadística.

Matriz de decisión vigente para la prueba local:

| Compatibilidad ecológica | Soporte estadístico | Salida práctica |
|---|---|---|
| Incompatible | Cualquiera | Poco probable por veto ecológico |
| Desconocida por datos insuficientes | Cualquiera | Sin recomendación fiable |
| Compatible | No validado | Condiciones compatibles, sin confirmación estadística |
| Compatible | Limitado o discrepante | Incierto; prospección razonable |
| Compatible | Consenso favorable | Favorable |
| Compatible | Consenso desfavorable | Poco probable |

La cabecera solo muestra un rango cuando procede de estimadores admitidos. Los
scores brutos descartados y todos los modelos sombra permanecen en el bloque
técnico, pero no aparecen como una supuesta probabilidad principal ni sirven
para ordenar las vistas compactas. Debajo se conserva una explicación rica en
lenguaje natural: evento y momento biológico, cambio de estación, estimadores
fuera de dominio, soporte frente a prevalencia y condición histórica. El texto
es determinista, traducido y construido con códigos de motivo; no lo genera un
modelo de lenguaje.

Los modelos sombra tampoco deben quedar reducidos a una tabla que requiera
interpretación manual. Para cualquier especie, área y fecha, cada contrato
selecciona como **señal experimental** el shadow disponible con menor Brier
entre los que mejoran la prevalencia. La pareja resultante se resume como
favorable, desfavorable, incierta o contradictoria, mostrando estimador(es) y
rango bruto. Continúa sin votar ni alterar el dictamen operativo. Si alguna
variable está severamente fuera de dominio, la señal se acompaña de cautela
explícita porque KNN puede copiar vecinos lejanos y una SVM RBF puede aplanarse
hacia el nivel base de su calibración.

Cuando la ecología es compatible pero LR/RF no ofrecen soporte autorizado, el
título deja de destacar una señal bruta operativa favorable o desfavorable y
pasa a «Incierto — condiciones compatibles». La cabecera distingue entonces
«soporte estadístico operativo» de «señal experimental», de modo que una SVM,
HGB, ET o KNN validada pueda aportar evidencia visible sin ser promocionada de
forma implícita. Esta regla es genérica; no contiene excepciones por especie,
zona, fecha ni estimador.

### 7. Calificación del modelo y presentación

- Un modelo con ROC-AUC temporal igual o inferior a 0,5 no puede aportar el mismo
  peso que uno validado.
- No promediar modelos por defecto al 50/50; seleccionar, ponderar o excluir con
  una regla reproducible basada en validación.
- No mostrar porcentajes como probabilidades reales mientras no exista
  calibración fuera de muestra suficiente.
- Mostrar score experimental, rango o estado de confianza cuando sea más honesto.
- Conservar explicación por modelo, features utilizadas, imputaciones y gaps.

La presentación debe ser autoexplicativa sin convertir la vista principal en
un manual permanente. La cabecera separa explícitamente «Compatibilidad
ecológica», «Fiabilidad de la compatibilidad ecológica», «Fiabilidad
estadística del modelo operativo», consenso y señal experimental. Cada término
y cada campo de auditoría incorpora ayuda localizada al pasar el cursor o
recibir foco de teclado. Las ayudas cubren también Brier y su base de
prevalencia, ROC-AUC, origen de scores, corte meteorológico, horizonte,
coberturas, salto de estación, variables fuera de dominio, estimadores y media
sin ponderar.

Los nombres de contrato tampoco se presuponen conocidos: `fixed_gap_7d_v1` se
explica como una predicción que solo ve datos hasta siete días antes de la fecha
objetivo; `lag_event_v1` usa el último corte completo disponible al emitir la
consulta y representa explícitamente el retardo hasta la fecha objetivo. El
ancho útil de escritorio puede crecer para mantener legible esta cabecera, pero
la disposición conserva el salto de línea y el desplazamiento de tablas en
pantallas pequeñas.

## Criterio de salida de la fase

La fase se considerará completada cuando exista una comparación reproducible
por especie que:

1. use el dataset actual sin fabricar observaciones ni ausencias;
2. trate cero, dato ausente y cobertura parcial como estados diferentes;
3. reduzca sustancialmente la dimensionalidad del baseline;
4. compare al menos baseline, LR reducida, árbol restringido y opción híbrida;
5. descarte modelos que no superen el baseline temporal;
6. pueda abstenerse ante meteorología insuficiente;
7. explique por qué una recomendación es favorable, desfavorable o incierta;
8. no convierta un score no calibrado en una certeza porcentual.

Más observaciones seguirán siendo valiosas y se incorporarán conforme se
generen. La mejora inmediata, sin embargo, depende sobre todo de usar mejor las
que ya existen, reducir grados de libertad y hacer que validación, confianza y
presentación sean coherentes.

## Estado de implementación del laboratorio (2026-08-10)

Ya están implementadas las primeras piezas del plan, todavía sin sustituir el
modelo operativo:

- series meteorológicas diarias conservadas en el artefacto JSON;
- benchmark 70/30 estratificado y agrupado por fecha, con semilla reproducible;
- diagnóstico cronológico 70/30 secundario y agrupado por fecha;
- `fixed_gap_7d_v1`, con ceguera fija de siete días;
- `lag_event_v1`, con corte en ayer o el último día completo y horizontes 1..7;
- prevalencia, LR reducida y RF restringido sobre las mismas particiones;
- bundles shadow que viajan en el runtime del worker;
- comparación opt-in en «Consultar fecha», con fecha de corte visible.

La primera ejecución no ha encontrado aún un ganador: los cuatro candidatos
de Aereus empeoran el Brier de la prevalencia, aunque dos ordenan mejor que azar
en ese único holdout. El siguiente análisis debe ampliar cortes temporales,
ablation, cobertura y casos centinela antes de calibrar o promocionar nada.

La primera prueba integral del caso centinela tampoco quedó resuelta solo con el corte:
`fixed_gap_7d_v1` produjo 72,51% con 6/15 variables ausentes y
`lag_event_v1` 65,91% con 11/16 ausentes. Los cortes fueron correctos, pero la
imputación permitió emitir score sin evidencia meteorológica suficiente. Esa
ejecución queda como diagnóstico histórico del problema, no como resultado del
contrato actual.

La corrección acordada elimina la invalidez de ventanas por un hueco aislado:
lluvias ausentes o descartadas aportan cero efectivo, pero conservan contadores
de cobertura y supresión. Los eventos se buscan hasta 90 días y saturan su edad
en 90; el artefacto conserva 120 días. La estación deja de ser simplemente la
de mejor cobertura entre cinco: desde el centroide se usa la estación elegible
más cercana dentro de 15 km y se salta a la siguiente cuando no supera los
mínimos 19/21 y 81/90 de lluvia y 19/21 de temperatura y humedad. Sin ninguna
candidata válida, el Predictor se abstiene.

La segunda reconstrucción local elimina las ausencias del caso centinela y
cambia `fixed_gap_7d_v1` a 24,48%, pero `lag_event_v1` sube a 76,96%. Ambos ven
la misma sequía reciente y 71 días desde lluvia significativa; la diferencia
procede del modelo, especialmente de una LR extrema y sensible al horizonte,
no de datos meteorológicos ocultos. Ninguno supera aún la prevalencia temporal
en Brier. El próximo análisis debe estudiar ablation del horizonte, estabilidad
de coeficientes y calibración antes de cualquier promoción.

La paridad de ejecución es vinculante: benchmark y Predictor deben invocar los
mismos constructores versionados y la misma política de estación/cobertura. La
respuesta comparativa conserva todas las variables usadas para que esta
equivalencia pueda verificarse caso por caso.

Edulis aporta 26 episodios, 21 favorables y 5 desfavorables. En el snapshot del
2026-08-10, el 70% cronológico agrupado deja train con 16 favorables y ningún
desfavorable; no existe un holdout temporal limpio con ambas clases a los dos
lados sin partir una misma fecha. La evaluación principal pasa a ser
estratificada por clase y agrupada por fecha: aproximadamente 15 favorables + 3
desfavorables en train y 6 + 2 en test. El diagnóstico cronológico se conserva
como «no disponible», sin impedir el ajuste final sobre los 26 episodios.

Esta separación responde a dos preguntas distintas. La partición estratificada
mide si el modelo discrimina dentro de la distribución histórica disponible;
la cronológica comprueba si esa señal se mantiene frente a observaciones más
modernas. Ninguna fecha ni sus áreas pueden aparecer a ambos lados, y ambas
particiones quedan congeladas en el benchmark.
