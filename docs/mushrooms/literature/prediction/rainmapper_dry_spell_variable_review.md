# Rainmapper — revisión técnica y diseño experimental de la racha seca

Fecha de revisión: 5 de septiembre de 2026

Estado: diseño documentado y primera batería ejecutada en copias aisladas; sin
cambios en modelos operativos ni precálculo.

## 1. Objetivo y alcance

Este documento revisa cómo representa Rainmapper una racha de días secos y define la batería de pruebas necesaria para decidir si esa variable ayuda realmente a predecir fructificaciones.

No es una revisión de literatura científica ni convierte los criterios de Sporas.io en *ground truth*. Es una revisión técnica basada en el código y los artefactos actuales. Las hipótesis ecológicas que aparecen aquí deben tratarse como preguntas que el modelo ha de contrastar con las observaciones de Rainmapper.

Este diseño respeta `MOD_0001`: los cálculos ecológicos continúan disponibles como diagnóstico, pero no vetan ni modifican probabilidades.

## 2. Conclusión ejecutiva

La variable actual `dry_spell_observed_at_cutoff` tiene un problema de definición: cualquier cantidad positiva de lluvia, incluso 0,1 mm, pone la racha seca a cero. Eso confunde una traza de precipitación con la ruptura efectiva de un periodo seco.

La recomendación es:

1. No eliminar ni modificar silenciosamente la variable de los modelos ya entrenados.
2. Probar como alternativa principal una racha seca en la que un día con menos de 1 mm siga contando como seco y un día con 1 mm o más rompa la racha.
3. Mantener por separado el concepto de lluvia significativa de 5 mm o más. No es la definición de día seco y no debe sustituirla.
4. Conservar la precipitación real, incluidos valores inferiores a 1 mm, en sumas, series diarias, balance hídrico y SMI. El umbral de 1 mm solo afecta al contador binario de racha seca.
5. Comparar la alternativa con la definición actual y con la ausencia completa de esa variable, usando exactamente los mismos grupos de entrenamiento y prueba.

La batería ejecutada el 5 de septiembre no respalda adoptar el umbral de 1 mm
como feature operativa: mejora unas combinaciones y empeora otras. Quitar por
completo el contador resulta algo más favorable y estable, pero tampoco es
universal. Por tanto, no se recomienda hoy ningún cambio operativo.

### Decisión en lenguaje directo

- **Ahora no se cambia qué significa racha seca en V2--V4.** Aunque parece más
  sensato llamar seco a un día con 0,1 mm, la prueba no demuestra que usar
  `< 1 mm` mejore las predicciones de forma consistente.
- **Tampoco se borra la información de lluvia.** Las cantidades diarias, sus
  acumulados y el estado hídrico sí aportan señal. Lo dudoso es únicamente el
  contador que resume todo eso como «N días secos».
- **La siguiente hipótesis preferida para un contrato futuro es prescindir de
  ese contador**, dejando que el modelo aprenda la sequedad desde la lluvia
  continua y, cuando estén presentes, SMI/balance/estado del suelo. En la
  batería actual esta opción fue más estable que cambiar el corte a 1 mm.
- **El corte de 1 mm queda como comparación, no como decisión tomada.** Cuando
  entren nuevos episodios independientes se repetirán las tres variantes:
  actual, `< 1 mm` y sin contador. Solo entonces se decidirá si una sustituye a
  la actual.

Por tanto, «considerar seco `< 1 mm`» no significa eliminar esos milímetros de
la meteorología: seguirían entrando con su valor real en todas las variables
continuas. Solo cambiaría el contador de días consecutivos, si algún día esa
variante demuestra ser mejor y se publica en un contrato nuevo.

## 3. Comportamiento actual verificado

### 3.1 V3

En `rainmapper_core/mushroom_ml_biology_v3.py`:

- `dry_spell_observed_at_cutoff` está marcada como predictiva y activa (línea 179).
- Los relojes de lluvia superior a 2 mm y de lluvia significativa están conservados pero inactivos (líneas 177-178).
- `_dry_spell()` recorre la lluvia hacia atrás y termina en cuanto encuentra `value > 0` (líneas 816-824).
- Un dato ausente no se convierte en cero: interrumpe el cálculo y marca la racha como censurada.

Por tanto:

```text
25 días con 0 mm
último día con 0,1 mm
resultado actual: 0 días secos
```

La racha se calcula en el corte meteorológico, no en la fecha objetivo. En una predicción a siete días no se añaden artificialmente esos siete días a la racha observada.

### 3.2 V4

V4 hereda como núcleo las variables predictivas activas de V3 (`rainmapper_core/mushroom_ml_biology_v4.py`, líneas 37-41). También cuenta como «día lluvioso» cualquier valor superior a cero en sus variables ampliadas (líneas 608-614). Por ello, tanto la racha heredada como esos contadores son sensibles a trazas de lluvia.

### 3.3 V2

V2 incluye como entradas predictivas:

- la racha seca explícita;
- los días desde lluvia superior a 2 mm;
- los días desde lluvia significativa superior a 5 mm.

Esto se comprueba en `rainmapper_core/mushroom_ml_experiments.py` (columnas de entrada en las líneas 62-71). En V2, los umbrales de 2 y 5 mm no son solo texto de interfaz: pueden influir en la predicción.

### 3.4 V5 y V6

V5/V6 no usan un contador explícito de racha seca. Reciben perfiles de lluvia diaria o por ventanas y, según el perfil, variables de estado físico/hídrico. La sequedad puede ser aprendida de forma indirecta, pero no existe una entrada equivalente que pueda sustituirse sin definir un contrato experimental nuevo.

### 3.5 Caso comprobado de *Boletus edulis*

El artefacto HGB-V3 `core` seleccionado y revisado para *B. edulis* recibe `dry_spell_observed_at_cutoff`, pero no la utiliza en ninguna de sus divisiones internas: 0 de 710 *splits*.

Esto significa únicamente que esa variable no cambia las decisiones de ese modelo concreto. No demuestra que:

- las rachas secas carezcan de valor para otras especies o algoritmos;
- la definición alternativa de 1 mm vaya a ser inútil;
- SMI o balance hídrico la estén sustituyendo.

En particular, ese HGB-V3 `core` no recibe SMI ni balance hídrico. Su posible redundancia sería con las ventanas de lluvia, humedad y temperatura que sí consume. Contar *splits* es un diagnóstico útil, no una medida suficiente de calidad predictiva.

## 4. Cuatro conceptos que no deben mezclarse

| Concepto | Definición propuesta | Uso |
|---|---|---|
| Precipitación continua | Milímetros reales observados o interpolados | Series, acumulados, balance hídrico y SMI; nunca se pone a cero por ser menor de 1 mm |
| Día seco efectivo | Precipitación diaria menor de 1 mm | Construcción experimental de la racha seca |
| Lluvia que rompe la racha | Precipitación diaria igual o superior a 1 mm | Pone a cero la racha seca experimental |
| Lluvia significativa | Precipitación diaria igual o superior a 5 mm | Referencia diagnóstica independiente; no define por sí sola la racha seca |

El reloj histórico de lluvia superior a 2 mm es un quinto concepto heredado. Sigue siendo una entrada de V2 y está inactivo en V3. No debe presentarse como sinónimo de día seco ni de lluvia significativa.

Una cantidad como 0,1 mm puede proceder de la resolución de una estación, de ruido o de la interpolación IDW del área. No se ha demostrado cuál de estas causas explica cada caso; el problema verificable es que el contador actual es demasiado sensible a cualquiera de ellas.

## 5. Definiciones que deben compararse

### D0 — definición actual

```text
dry_spell_any_positive
día seco: P = 0 mm
rompe la racha: P > 0 mm
```

Es el control que reproduce el comportamiento existente.

### D1 — definición recomendada para la prueba principal

```text
effective_dry_spell_p1
día seco: 0 <= P < 1 mm
rompe la racha: P >= 1 mm
```

Los valores ausentes continúan siendo desconocidos: censuran la racha y nunca se convierten en cero.

### D2 — sin contador de racha seca

Se retira únicamente esa entrada, manteniendo las demás variables. Esta ablación permite saber si cualquier versión de la racha aporta algo frente a no usarla.

### D3 — eventos de recarga en ventana, prueba secundaria

Como experimento posterior se pueden construir relojes como:

```text
days_since_recharge_5mm_3d
days_since_recharge_10mm_3d
```

Miden días desde una ventana de tres días que acumuló al menos 5 o 10 mm. No deben llamarse «racha seca»: responden a otra pregunta, la existencia de un posible evento de recarga repartido en varios días.

No se recomienda empezar probando muchos umbrales diarios —1, 3, 5 y 10 mm— contra la misma prueba externa. Eso facilitaría escoger por azar el que mejor encaje en una muestra pequeña. El umbral de 1 mm queda fijado de antemano como hipótesis principal; cualquier búsqueda adicional debe resolverse solo dentro de los datos de entrenamiento.

## 6. Batería de pruebas y secuencia

La secuencia está diseñada para que cada fase responda a una pregunta distinta y para evitar atribuir a la racha seca efectos que pertenecen a la lluvia acumulada o al estado hídrico.

### Fase 0 — inventario y reproducción del punto de partida

Estado: ejecutada para la primera batería del 5 de septiembre.

1. Congelar en un manifiesto experimental las revisiones de observaciones, meteorología, GIS y contratos de features.
2. Inventariar, por especie y versión, qué modelos candidatos y ganadores reciben realmente:
   - racha seca;
   - relojes de 2 y 5 mm;
   - ventanas o series de lluvia;
   - SMI, balance o estado hídrico.
3. Reproducir sin cambios las métricas actuales con los mismos grupos `fruiting_groups_14d`.
4. Comprobar también `fruiting_groups_7d` como análisis de estabilidad, no como un conjunto alternativo del que elegir el mejor resultado.

Si el punto de partida no se reproduce, la batería se detiene y se explica primero la diferencia. No se comparan variantes construidas sobre bases distintas.

### Fase 1 — prueba aislada de la definición de racha seca

Estado: ejecutada para seis configuraciones V2--V4, cinco especies y los cortes
agrupados de 7 y 14 días.

Para cada combinación auditable de especie, versión, perfil y algoritmo se comparan, sin cambiar nada más:

| Variante | Racha usada | Pregunta |
|---|---|---|
| R0 | D0: cualquier lluvia positiva rompe la racha | Control actual |
| R1 | D1: menos de 1 mm continúa siendo seco | ¿Mejora una definición menos sensible a trazas? |
| R2 | D2: sin racha seca | ¿Aporta algo el contador explícito? |

Se mantienen idénticos:

- observaciones;
- grupos externos;
- resto de variables;
- algoritmo e hiperparámetros;
- semilla;
- calibrador;
- reglas de aplicabilidad y selección.

Esta es la comparación principal y debe ejecutarse antes que cualquier prueba de ventanas de recarga.

### Fase 2 — atribución de la señal hídrica

Estado: ejecutada dentro de las mismas copias aisladas para los bloques
aplicables a cada contrato.

Después de conocer R0/R1/R2, se hacen ablaciones de bloques para saber qué información hídrica sostiene el resultado:

| Variante | Cambio respecto al contrato completo | Pregunta |
|---|---|---|
| H0 | Ninguno | Referencia |
| H1 | Quitar solo la racha seca | Valor incremental de la racha |
| H2 | Sustituirla solo por D1 | Valor de la definición de 1 mm |
| H3 | Quitar ventanas/acumulados de lluvia | Dependencia de la cantidad y distribución temporal de lluvia |
| H4 | Quitar SMI/balance/estado hídrico, cuando existan | Dependencia del estado hídrico del suelo |
| H5 | Quitar racha y ventanas de lluvia, conservando estado hídrico | ¿Basta el estado hídrico? |
| H6 | Quitar estado hídrico y conservar lluvia más D1 | ¿Basta la meteorología reciente? |

Una casilla se marca «no aplicable» si la versión no tiene ese bloque. Por ejemplo, no se atribuirá a SMI la falta de uso de la racha en un V3 `core` que no recibe SMI.

Las ablaciones no cambian temperatura, humedad, altitud ni retardos no hídricos. Esos bloques se analizan por separado en la auditoría P0 multivariable para no mezclar preguntas.

### Fase 3 — eventos de recarga, solo si las fases 1 y 2 lo justifican

Estado: no ejecutada. D1 no mejoró de forma estable y D2 fue más favorable en
el agregado, por lo que no se cumple el criterio previo para abrir una búsqueda
de nuevos relojes o umbrales.

Se comparan como máximo dos definiciones fijadas antes de mirar la prueba externa:

- `days_since_recharge_5mm_3d`;
- `days_since_recharge_10mm_3d`.

Primero se decide cualquier umbral o combinación mediante particiones agrupadas internas del entrenamiento. Después se evalúa una sola elección en el *hold-out* externo. Si no mejora de forma consistente a D1 y a la ausencia de contador, se descarta esta ampliación.

### Fase 4 — réplica multiespecie y multiversión

La prueba no debe quedarse en Rovelló/Riu ni en V6.

Alcance inicial:

- Rovelló;
- Edulis;
- Pinícola;
- Aereus;
- Ou de reig.

Se incluyen los candidatos V2, V3 y V4 que realmente reciben la variable y los modelos operativos seleccionados de cada especie. V5/V6 sirven como comparación estructural —aprendizaje desde lluvia cruda/estado hídrico sin contador explícito—, pero no se les añade D1 de forma encubierta.

Los resultados se presentan:

1. por especie;
2. agregados entre especies sin ocultar heterogeneidad;
3. por área solo cuando haya suficientes positivos y negativos para que la métrica sea interpretable.

No se crearán modelos independientes por área si el contrato actual no los entrena así. «Todas las zonas» significa comprobar el comportamiento y los errores en las áreas representadas, no inventar un entrenamiento distinto.

Las tres especies operativas restantes se incorporarán cuando sus *hold-outs* tengan ambas clases y evidencia suficiente. Hasta entonces deben figurar como pendientes, no como resultados negativos.

### Fase 5 — selección justa y confirmación

1. Toda elección de definición, umbral o hiperparámetro se hace dentro del entrenamiento con particiones internas agrupadas.
2. `fruiting_groups_14d` permanece como evaluación externa principal.
3. `fruiting_groups_7d` se usa para comprobar estabilidad.
4. El resultado externo se informa completo, incluidos casos donde no puede calcularse una métrica por faltar una clase.
5. Como el *hold-out* actual ya se ha consultado durante varias auditorías, una mejora en él permite formular un candidato, pero no justificar por sí sola su promoción operativa.
6. Las nuevas observaciones que se incorporen normalmente a Rainmapper aportarán confirmación independiente en futuros reentrenamientos; no se requiere guardar todos los precálculos diarios ni organizar salidas de campo específicas.

## 7. Métricas y lecturas obligatorias

La métrica principal es Brier porque mide la calidad de la probabilidad, no solo si se supera un umbral. Se informarán además:

- calibración: curva, pendiente/intercepto y ECE cuando la muestra lo permita;
- ROC-AUC y PR-AUC cuando existan ambas clases;
- acierto al recomendar salir y su límite conservador;
- cobertura y abstenciones;
- cambios de decisión respecto al control;
- estabilidad al retirar grupos completos;
- distribución del efecto por especie y por área auditable.

Como diagnósticos, no como criterio único:

- número de *splits* de la variable;
- importancia por permutación calculada sin usar la prueba externa para seleccionar;
- relación con ventanas de lluvia y variables hídricas;
- ejemplos individuales donde R0, R1 y R2 divergen.

SHAP es opcional. No se necesita para decidir si una ablación mejora o empeora la predicción.

## 8. Criterio de decisión

No se adoptará una variante porque produzca el porcentaje más alto en unos pocos casos. D1 será candidata solo si:

- mejora Brier o calibración de forma repetida, no en un único grupo;
- no deteriora materialmente discriminación, cobertura ni estabilidad;
- el efecto aparece en más de una especie o existe una razón reproducible para limitarlo a una especie/versión;
- la mejora se mantiene en `fruiting_groups_14d` y es compatible con la comprobación de 7 días;
- su efecto puede explicarse mediante las entradas realmente consumidas.

Interpretación de resultados:

| Resultado | Conclusión |
|---|---|
| D1 supera de forma estable a D0 y D2 | La definición de 1 mm es candidata a un contrato nuevo |
| D0 y D1 son equivalentes, ambas superan D2 | La racha aporta señal, pero el umbral no está resuelto |
| D2 iguala o supera a D0 y D1 | El contador explícito no aporta valor demostrable en ese ámbito |
| El efecto cambia mucho por especie o versión | No debe imponerse una definición global sin una regla justificada |
| Solo mejora una métrica o un grupo pequeño | Resultado insuficiente; no se promociona |

Cambiar la semántica de una feature obliga a crear un artefacto y contrato versionados y a reentrenar. Nunca se debe reinterpretar una columna existente dentro de modelos ya entrenados ni machacar las versiones actuales. Esta auditoría no reserva por sí sola el nombre V7 ni autoriza un cambio operativo.

## 9. Resultado de la batería del 5 de septiembre

### 9.1 Entradas y alcance

Se reconstruyeron benchmarks nuevos desde la copia activa de HA local:

- 445 observaciones totales en la fuente;
- 329 observaciones de las cinco especies auditadas;
- 322 observaciones elegibles en ventana fija;
- 2.254 filas elegibles en retardos, porque cada observación puede aparecer en
  siete horizontes;
- meteorología activa con identidad
  `20260905T150355498130Z-c3bb48b2165e`.

Las seis configuraciones controladas cubren:

- V2 común: regresión logística y random forest;
- V3 `core`: HGB con ventana fija;
- V3 con estado físico: regresión logística;
- V4 con balance climático: regresión logística y KNN.

Se probaron Rovelló, Edulis, Pinícola, Aereus y Ou de reig. V5/V6 no se
alteraron porque no contienen el contador explícito. Sirven como comparación
estructural, no como receptores encubiertos de D1.

### 9.2 Las dos observaciones nuevas

Las observaciones positivas de Edulis y Rovelló del 5 de septiembre en
Salteguet son elegibles y quedan en el conjunto externo tanto con grupos de 7
como de 14 días. Cada una es un solo caso observado, aunque el benchmark de
retardos lo evalúe en siete horizontes.

Esta evaluación y la comprobación prospectiva responden a preguntas distintas.
Los porcentajes 65,9818 % y 96,5041 % pertenecen a los modelos operativos que
existían antes de registrar las observaciones. Las ablaciones reajustan copias
usando solo la partición de entrenamiento y reservan los grupos externos; sus
probabilidades individuales pueden ser diferentes y no sustituyen aquellos
dos porcentajes archivados.

En ambas, el valor de la racha cambia así:

| Horizonte | D0 actual | D1 con umbral de 1 mm |
|---:|---:|---:|
| 1 día | 8 | 11 |
| 2 días | 7 | 10 |
| 3 días | 6 | 9 |
| 4 días | 5 | 8 |
| 5 días | 4 | 7 |
| 6 días | 3 | 6 |
| 7 días | 2 | 5 |

La diferencia de tres días procede de trazas inferiores a 1 mm. Por tanto, el
caso demuestra que D0 y D1 no son etiquetas equivalentes en los datos reales.

### 9.3 Resultado conjunto D0/D1/D2

Un delta Brier negativo significa mejora respecto de D0. Las cifras siguientes
son medias simples entre las 30 combinaciones configuración/especie de cada
corte; no son 30 experimentos independientes ni una estimación causal.

| Corte | Variante | Mejora | Empeora | Empata | Delta Brier medio |
|---|---|---:|---:|---:|---:|
| 7 días | D1, racha con 1 mm | 18 | 11 | 1 | -0,0029 |
| 7 días | D2, sin racha | 19 | 8 | 3 | -0,0036 |
| 14 días | D1, racha con 1 mm | 13 | 17 | 0 | +0,0017 |
| 14 días | D2, sin racha | 19 | 8 | 3 | -0,0037 |

La lectura principal es:

- D1 no es estable: el signo cambia entre especies, algoritmos y cortes;
- D2 es más favorable en Brier, pero todavía empeora ocho de treinta
  combinaciones en cada corte;
- en calibración por cinco intervalos D1 suele mejorar, pero esa mejora no va
  acompañada de una mejora estable del Brier;
- no hay base para imponer D1 globalmente ni para borrar la variable de todos
  los contratos actuales.

En los candidatos operativamente relevantes se observa la misma mezcla:

| Candidato, corte de 14 días | Delta Brier D1 | Delta Brier D2 |
|---|---:|---:|
| Rovelló V2 logística | -0,0170 | -0,0237 |
| Rovelló V2 random forest | +0,0030 | -0,0134 |
| Edulis V3 `core` HGB | -0,0004 | 0,0000 |
| Pinícola V2 random forest | +0,0073 | -0,0133 |
| Ou de reig V4 logística | -0,0048 | -0,0001 |
| Ou de reig V4 KNN | +0,0156 | +0,0131 |

En Edulis V3 `core`, quitar la racha vuelve a producir esencialmente el mismo
modelo y el mismo Brier. Cambiarla por D1 puede hacer que el árbol empiece a
usarla, pero no aporta una mejora relevante.

### 9.4 Resultado de las ablaciones hídricas

La falta de utilidad estable del contador no significa que la información
hídrica sea inútil:

- quitar todo el bloque hídrico empeora 21 de 30 comparaciones en el corte de
  14 días y 20 de 30 en el de 7;
- quitar cantidades y ventanas de lluvia empeora 17 de 30 comparaciones en 14
  días y 16 de 30 en 7;
- retirar balance/estado hídrico empeora la media de los contratos que los
  contienen, aunque el efecto sigue variando por especie y algoritmo.

La conclusión compatible con ambas auditorías es sencilla: lluvia y estado
hídrico contienen señal, pero el contador explícito de racha seca no demuestra
una aportación adicional estable.

### 9.5 Decisión tras la prueba

1. No adoptar D1 como nueva semántica operativa.
2. No modificar ni eliminar todavía la columna de modelos ya entrenados.
3. Considerar D2 —contratos futuros sin contador explícito— como hipótesis más
   prometedora que añadir nuevos umbrales.
4. No ejecutar por ahora D3 ni buscar el mejor umbral en el hold-out externo.
5. Repetir D0/D1/D2 cuando haya nuevos grupos independientes, especialmente
   negativos, antes de decidir un contrato futuro.

El resultado reproducible está en
`docker-data/audits/mushroom-dry-spell-ablation-20260905/results/controlled-dry-spell-ablation.json`.
El runner aislado está junto al resultado y declara expresamente que no escribe
modelos ni precálculos.

## 10. Consecuencias para la interfaz

La interfaz debe distinguir:

- «racha de días secos», con su umbral explícito;
- «última lluvia significativa ≥ 5 mm»;
- «días desde lluvia > 2 mm» cuando proceda de un V2;
- acumulados de lluvia que el modelo consume.

El rótulo «lluvia significativa usada» no debe sugerir que el evento de 5 mm decidió una predicción si el modelo seleccionado no consume ese reloj. Puede mostrarse como referencia diagnóstica, indicando claramente que no es una feature activa de ese resultado.

## 11. Relación con las auditorías existentes

Este diseño complementa, no sustituye:

- `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`, que compara la señal hídrica en varias especies y versiones;
- `docs/reports/mushroom-predictor-p0-pending-tests-and-python-audit-battery-2026-09-05.md`, que registra las pruebas pendientes y los *scripts* preparados.

La ejecución deberá documentar para cada resultado las revisiones de entrada, el contrato, los grupos, el modelo, las métricas y cualquier caso no evaluable.

## 12. Conclusiones

1. Rainmapper sí tiene una variable explícita de días secos en V2-V4; no existe como contador en V5/V6.
2. Su definición actual es frágil ante lluvias testimoniales porque cualquier valor superior a cero rompe la racha.
3. Una lluvia inferior a 1 mm debe seguir conservándose como cantidad meteorológica, pero se propone tratar ese día como seco únicamente para la variante experimental D1.
4. La lluvia significativa de 5 mm es un diagnóstico diferente y razonable; no debe confundirse con el límite de día seco.
5. El caso Edulis HGB-V3 muestra que la feature actual puede estar presente sin influir, pero no permite generalizar a las demás especies o modelos.
6. La comparación D0/D1/D2 ya se ha ejecutado manteniendo idénticos los grupos
   dentro de cada combinación. D1 no mejora de forma estable y D2 obtiene el
   resultado agregado más favorable.
7. Las ablaciones confirman que la señal hídrica conjunta sí aporta, aunque el
   contador no demuestre utilidad incremental estable.
8. No se justifica abrir ahora la búsqueda de eventos de recarga en tres días.
9. Ningún resultado de esta batería modifica directamente una predicción ni un
   artefacto operativo: cualquier adopción posterior requerirá autorización,
   contrato nuevo, entrenamiento y validación independiente.
