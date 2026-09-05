# Selección precalculada del candidato más fiable del Predictor

Estado: selección por fiabilidad e implementación local completadas. La retirada
operativa de los vetos meteorológicos externos al modelo (`MOD_0001`) está
implementada localmente y conserva sus cálculos como diagnóstico; quedan la
validación con un precálculo nuevo y, con autorización separada, el despliegue
en HA real.

## Objetivo

Simplificar la predicción operativa para que cada combinación de especie, área
y día de la predicción use directamente una única probabilidad precalculada,
producida por el candidato que mejor haya demostrado acertar cuando recomienda
realizar una salida para ese mismo horizonte operativo.

Un candidato queda identificado de forma completa por:

- versión;
- perfil y su ventana meteorológica;
- contrato temporal exacto y su familia;
- horizonte;
- estimador.

La selección se calcula y se sella durante el entrenamiento. El precálculo
semanal no vuelve a evaluar ni ordenar candidatos: carga la selección publicada,
ejecuta el candidato indicado y persiste su resultado. La consulta de usuario
se limita a leer esa probabilidad y su trazabilidad.

El cambio elimina del camino ordinario la comparación de todas las
probabilidades en tiempo de predicción. No pretende crear un modelo nuevo,
mezclar candidatos ni encontrar una combinación distinta para cada ejecución.

La pregunta científica principal es:

```text
Cuando este candidato recomienda salir, ¿con qué fiabilidad demostrada acierta?
```

La métrica observable correspondiente es `Favorables acertados`, es decir,
`true_favorable_count / (true_favorable_count + false_favorable_count)`. La
selección no usa el porcentaje bruto sin contexto: lo corrige de forma
conservadora según el número de recomendaciones de salida independientes sobre
las que se obtuvo.

## Decisiones vinculantes

1. La selección pertenece al entrenamiento, no al precálculo ni a la UI.
2. Una misma publicación de entrenamiento produce siempre la misma selección.
3. Cambiar únicamente la meteorología futura o la fecha de la ventana semanal
   obliga a regenerar el precálculo, pero no a reelegir candidato.
4. Cambiar observaciones, meteorología histórica usada para entrenar, split,
   modelos, perfiles, contratos o cualquier otra entrada científica de la
   evaluación exige un nuevo entrenamiento y una nueva selección.
5. El precálculo consume la selección sellada y falla cerrado si falta, no es
   compatible con su esquema o referencia un candidato no instalado.
6. No se calcula un promedio, consenso o ensemble de probabilidades. El
   resultado ordinario procede de un candidato individual y auditable.
7. La selección científica no reutiliza ni modifica
   `preferred_version_id`. Ese puntero de UI sigue siendo un concepto separado.
8. El split autoritativo de selección es `fruiting_groups_14d`. Los demás
   splits solo pueden auditarse por separado como diagnóstico.
9. No se fijan mínimos manuales de observaciones, recomendaciones de salida ni
   recall. Wilson incorpora de forma continua la incertidumbre debida al número
   de recomendaciones y se reajusta al crecer el corpus.
10. No existe un ganador único reutilizable para los siete días. Para el día
    operativo `N` compiten únicamente los candidatos `lag` de horizonte `N` y
    los candidatos `fixed` de horizonte 7. El entrenamiento sella hasta siete
    resoluciones por especie/área.

## Estado actual verificado

`rainmapper_core/mushroom_ml_quality_catalog.py` construye actualmente un
`quality-catalog.json` de esquema `1.3` a partir de predicciones hold-out ya
calculadas. Cada entrada contiene especie, versión, perfil, familia temporal,
horizonte, estimador, soporte, abstenciones, Brier, baseline de prevalencia,
ROC-AUC, calibración y clasificación operativa. El batch local instalado
`local_operational_20260902T205828Z` aún es `1.2`; activar `1.3` exige un nuevo
entrenamiento y un nuevo precálculo.

El productor queda corregido para incluir el `split_id` real en la clave y en
cada entrada, rechazar filas sin split y permitir lookup explícito. Conserva en
`entries` únicamente el split superior de 7 días para compatibilidad con los
consumidores actuales; los demás quedan separados en
`alternate_split_entries`. Así ningún lector antiguo suma splits distintos y un
lector nuevo puede solicitar otro de forma expresa.

Las filas de origen producidas por `rainmapper_core/mushroom_ml_holdout.py`
incluyen `area_id`. El catálogo compacto conserva las métricas agregadas por
especie y las resoluciones ganadoras por especie/área/día; no conserva todas
las alternativas territoriales porque no las necesita el precálculo.

El SQLite semanal instalado conserva todavía todos los miembros necesarios para
reconstruir selecciones multiversión. El código local ya reemplaza esa parte del
camino ordinario: el producto nuevo conserva solo el miembro seleccionado
durante entrenamiento. Una modalidad comparativa futura, si se mantiene, será
explícita y no condicionará la consulta normal.

## Caso independiente, unidad científica y comparabilidad

La identidad indivisible de un candidato evaluado es:

```text
(snapshot_id, split_id, species_id, version_id, profile_id,
 temporal_contract_id, horizon_days, estimator_id)
```

Para el análisis territorial se añade `area_id` como ámbito de evaluación, no
como parte del modelo:

```text
(snapshot_id, split_id, species_id, area_id, candidate_id)
```

La granularidad territorial de esta selección termina en `area_id`. No se
crean ganadores por `micro_area_id`: las microáreas pueden conservarse como
trazabilidad de las observaciones, pero no dividen el soporte ni la resolución
operativa.

Estas claves identifican el candidato y su ámbito, pero no el número de
observaciones ni de grupos. Para contar evidencia se definirá además un
`evaluation_case_id` canónico que represente la unidad científica reservada por
el split y sea exactamente el mismo para todos los candidatos que evaluaron ese
caso.

El `row_key` actual no puede cumplir esa función sin transformación porque
incluye `version_id` y `profile_id`: una misma muestra científica recibe claves
distintas al evaluarse con candidatos distintos. Tampoco se usarán como casos
independientes las filas derivadas de combinaciones de ventana, familia,
horizonte o estimador.

La auditoría local de Aereus/Olvan demuestra que `validation_group_id` no es un
caso binario: un mismo grupo temporal puede contener varias observaciones e
incluso ambas clases. Por tanto, el caso puntuado será la observación hold-out,
identificada de forma canónica e independiente del candidato; en el batch
auditado, `observation_id` cumple esa función y no se repite dentro de un mismo
candidato. El contrato general deberá validar esa unicidad y rechazar cualquier
duplicado ambiguo.

`validation_group_id` se conserva como grupo de dependencia y de separación
temporal. Sus observaciones no se agregan a una etiqueta inventada ni se tratan
como una sola predicción. Todas cuentan individualmente en aciertos, errores y
soporte. Retirar grupos completos sirve únicamente como diagnóstico adicional
de sensibilidad: no cambia la métrica principal ni sustituye observaciones por
episodios artificiales.

Solo se comparan candidatos que:

- proceden del mismo snapshot y split;
- predicen el mismo objetivo y la misma unidad temporal;
- se evaluaron sobre la misma población hold-out, identificada por el conjunto
  ordenado de `evaluation_case_id` independientes;
- conservan separadas especie y área;
- pertenecen al inventario operativo sellado por el entrenamiento.

`split_id` debe formar parte de cada entrada agregada y de su clave de
agrupación. Se prohíbe acumular filas de `fruiting_groups_7d`,
`fruiting_groups_14d`, `campaign_area_year_70_30` o cualquier otro contrato en
una sola métrica, aunque compartan observaciones. El identificador superior del
catálogo no puede sustituir al `split_id` real de cada fila.

Contrato temporal y horizonte son dimensiones del candidato. La familia se
deriva del contrato exacto, pero no lo sustituye en la identidad. Para cada día
operativo `N` solo son aplicables `lag hN` y `fixed h7`: ambos predicen el mismo
target, pero el segundo conserva siempre su separación ciega de siete días. No
se trasladará la fiabilidad demostrada por `lag h1` a `lag h2` ni a ningún otro
horizonte. Si cambia el significado del target o la población, se crearán
selecciones separadas por objetivo; no se proclamará un ganador universal entre
magnitudes no comparables.

No se suman, promedian ni mezclan matrices de confusión de candidatos o
poblaciones diferentes. `Casos probados` será el número de observaciones únicas
del candidato y nunca la suma de `evaluated_count` de varios modelos; el número
de grupos se mostrará por separado.

## Construcción finita durante entrenamiento

La selección reutiliza exclusivamente las probabilidades hold-out que el
entrenamiento ya ha producido. El proceso será:

1. Validar el inventario cerrado de candidatos del plan de entrenamiento.
2. Leer una sola vez las filas hold-out de ese entrenamiento.
3. Resolver cada fila a su `evaluation_case_id` independiente.
4. Rechazar duplicidades y conservar `validation_group_id` como bloque de
   dependencia.
5. Agregar evidencia separada por candidato y especie.
6. Agregar, sobre los mismos casos, evidencia por candidato, especie y área.
7. Formar grupos comparables mediante el identificador de población hold-out.
8. Para cada día operativo del 1 al 7, conservar únicamente `lag hN` y
   `fixed h7`.
9. Aplicar gates de elegibilidad dentro de esa población aplicable.
10. Ordenar de forma determinista los candidatos elegibles.
11. Publicar ganador, evidencia o abstención para cada
    especie/área/día operativo.

Queda expresamente fuera:

- volver a ajustar modelos;
- cargar o recalcular meteorología para seleccionar;
- ejecutar predicciones adicionales;
- probar combinaciones, ensembles, pesos o permutaciones;
- reevaluar selecciones en cada fecha del precálculo;
- mantener una búsqueda iterativa hasta que una métrica mejore.

El coste adicional queda acotado por las filas hold-out y los candidatos ya
declarados. Su complejidad esperada es lineal en esas filas, más la ordenación
de cada grupo pequeño de candidatos. No se construye el producto cartesiano de
especies, áreas, fechas, perfiles y estimadores.

## Evidencia por área y fallback

Se calcularán por separado el mejor candidato elegible para
`(species_id, area_id, prediction_day)` y el mejor candidato global para
`(species_id, prediction_day)`. Que una fila contenga `area_id` no basta: ambos
deben superar los mismos controles objetivos de validez, comparabilidad y
evidencia frente a prevalencia.

La resolución compara directamente sus límites inferiores de Wilson al 95 %:

1. si solo uno es elegible, se usa ese candidato;
2. si ambos son elegibles, gana el de mayor límite conservador;
3. si empatan exactamente, se conserva el candidato específico del área;
4. si ninguno es elegible, se publica una abstención explícita.

Por tanto, disponer de un ganador territorial ya no basta para bloquear un
candidato global de especie que haya demostrado una fiabilidad conservadora
superior. No se añade ningún mínimo manual ni una bonificación opaca por ser
territorial.

No habrá fallback entre especies ni se inventarán regiones semejantes. Un
fallback de especie se materializa durante el mismo entrenamiento para cada
área operativa y queda marcado como `species_fallback`; el precálculo no decide
el fallback.

### Qué significa —y qué no significa— el fallback de especie

`species_fallback` no significa que la predicción ignore el área ni que se
reutilice una probabilidad nacional o genérica. Significa únicamente que la
evidencia hold-out de esa área no permite demostrar qué candidato es el más
fiable allí y que, en su lugar, se hereda la **identidad del candidato** que sí
ha demostrado mayor fiabilidad para esa especie al agregar sus áreas
comparables:

- versión;
- perfil o ventana;
- contrato temporal exacto;
- horizonte;
- estimador.

Una vez heredada esa identidad, el precálculo ejecutará ese modelo con las
features y la meteorología de la **propia área y fecha**. Por tanto, la
probabilidad continúa siendo específica del área; lo que no es específico del
área es la evidencia empleada para elegir qué candidato debe producirla.

La interpretación correcta será: «este candidato ha demostrado ser el más
fiable para la especie; todavía no se ha podido demostrar cuál es el mejor
específicamente para esta área». No se afirmará que el candidato necesariamente
acierte menos en el área ni que el agregado sea intrínsecamente mejor: la
diferencia es el alcance de lo demostrado por los datos disponibles.

La abstención es distinta. Se produce cuando ni el área ni el agregado de la
misma especie ofrecen un candidato elegible. En ese caso no existe una base
científica suficiente para heredar candidato y no se generará una probabilidad
ordinaria mediante una versión concreta u otro sustituto silencioso.

Con nuevas observaciones, un futuro entrenamiento puede convertir una
abstención en fallback o ganador territorial, y un fallback en ganador
territorial. El cambio nunca se hace durante el precálculo: requiere recalcular
y sellar la selección con la nueva evidencia.

Una nueva área operativa no incluida en la publicación requiere regenerar el
artefacto de entrenamiento antes de entrar en el precálculo ordinario. No se le
asigna silenciosamente un candidato desde la UI.

### Fallback por aplicabilidad del modelo

Es distinto del `species_fallback`. Durante el entrenamiento, cada resolución
publica también `candidate_chain`: la lista de candidatos estadísticamente
elegibles en el mismo orden de fiabilidad que produjo el ganador. En cada área
y fecha operativa:

1. se prueba primero el ganador sellado;
2. si sus features actuales quedan fuera del dominio admitido, se descarta solo
   para esa predicción;
3. se toma el primer candidato posterior de la misma lista que conserve
   aplicabilidad y supere los controles operativos;
4. si se agota la lista, se mantiene la abstención.

La fecha no vuelve a ordenar modelos por su porcentaje ni reabre la evaluación
hold-out. Solo comprueba, en el orden ya sellado, cuál puede aplicarse a la
entrada actual. El resultado conserva `preferred_candidate`, `fallback_rank`,
las razones de rechazo y la evidencia del candidato que finalmente se usó.
Este mecanismo es estadístico y no ecológico: no consulta la ventana de
fructificación y respeta `MOD_0001`.

### Funcionalidad futura: especies posibles por área

La elegibilidad operativa podrá dejar de depender exclusivamente de que ya
existan observaciones de esa especie en el área. Se definirá un catálogo
explícito y revisable de especies posibles por área, separado de las
observaciones. Su ausencia nunca se inferirá como imposibilidad ecológica.

Cuando una pareja declarada posible todavía no tenga observaciones:

- el entrenamiento la incluirá en sus resoluciones especie/área/día;
- la evidencia territorial será `no disponible`;
- solo podrá heredar un candidato elegible de la misma especie y día, marcado
  como `species_fallback`;
- el precálculo ejecutará ese candidato con meteorología, GIS y demás features
  de la propia área, por lo que la probabilidad seguirá siendo local;
- la UI mostrará por separado la ausencia de evidencia del área y la evidencia
  global de especie que justificó el candidato.

La declaración ecológica no bastará para saltarse contratos de datos,
aplicabilidad o extrapolación. Si faltan features obligatorias, el candidato
global no es elegible o la entrada queda fuera de los límites admitidos, el
resultado será abstención. Las observaciones futuras permitirán que nuevos
entrenamientos creen evidencia territorial y eventualmente sustituyan el
fallback por un ganador de área.

## Elegibilidad

Un candidato no puede ganar si incumple cualquiera de estos requisitos:

- catálogo, identidad o población inválidos;
- ausencia de una de las dos clases en el hold-out comparable;
- ninguna recomendación de salida, porque `Favorables acertados` no tendría
  denominador;
- probabilidades o baseline no finitos o fuera del intervalo `[0, 1]`;
- evidencia que no mejora el Brier de prevalencia;
- candidato ausente del inventario operativo publicado.

No existe un mínimo manual de observaciones, recomendaciones de salida o
recall. Tampoco se traslada el gate histórico de ROC-AUC `>= 0,55`: ROC-AUC,
recall, cobertura y calibración se publican como contexto y participan en los
desempates definidos, pero no excluyen mediante una cifra elegida a mano. La
mejora estricta de Brier no es un mínimo de soporte: compara contra la referencia
objetiva de predecir siempre la prevalencia del entrenamiento.

Los candidatos no elegibles permanecen en el catálogo para auditoría, con sus
motivos de exclusión. Un resultado `1/1` no se presenta como 100 % demostrado:
su límite inferior de Wilson es aproximadamente 20,7 %. Puede ser el mejor
candidato disponible si además supera las condiciones objetivas, pero el
artefacto conserva la fracción y su gran incertidumbre. Una sola clase o un
predictor que no mejora la prevalencia no puede ganar.

## Métrica principal y orden determinista de fiabilidad

La finalidad es escoger al candidato que haya demostrado mayor fiabilidad al
recomendar salir. Para cada candidato se calcula:

```text
favorables_acertados = true_favorable_count
                       ─────────────────────────────────────────
                       true_favorable_count + false_favorable_count
```

El denominador es el número de observaciones hold-out en las que ese candidato
recomendó salir, no el total de filas ni la suma de varios candidatos. Cada
observación se compara individualmente con la predicción que recibió. El
porcentaje bruto permanecerá visible y el criterio principal será el límite
inferior de Wilson al 95 %, que penaliza porcentajes altos demostrados sobre
pocos casos.

Por ejemplo, `8/10 = 80 %` tiene aproximadamente un límite inferior del `49 %`,
mientras que `75/100 = 75 %` tiene aproximadamente un límite inferior del
`66 %`. El segundo candidato queda por delante porque ha demostrado una
fiabilidad alta sobre mucha más evidencia.

La auditoría también retirará cada `validation_group_id` completo y repetirá el
ranking para mostrar su sensibilidad. Ese resultado se publica como diagnóstico
de robustez: no altera el numerador, el denominador, los gates ni el ganador
calculado sobre todas las observaciones. Una baja estabilidad producirá una
advertencia visible, no una regla oculta distinta de la acordada.

Después de los gates, el orden será lexicográfico y visible:

1. mayor límite inferior de Wilson al 95 % por observaciones para `Favorables
   acertados`;
2. mayor porcentaje bruto de `Favorables acertados`;
3. mayor número de recomendaciones de salida observadas;
4. mayor capacidad para encontrar favorables;
5. menor abstención y mayor cobertura;
6. menor Brier y mayor mejora frente a prevalencia;
7. menor error de calibración;
8. mayor ROC-AUC;
9. clave canónica del candidato como desempate técnico estable.

La estabilidad por grupos se publica después del ranking para explicar cuánto
depende el resultado de una florada o periodo concretos, pero no lo reordena.

No se sumarán estas métricas en un índice opaco. Cuando dos pasos sean
matemáticamente equivalentes por compartir población y baseline, el artefacto
lo indicará y conservará igualmente ambos valores para explicación.

La capacidad de encontrar favorables ayuda a desempatar candidatos que aciertan
igual al recomendar salir, pero uno casi nunca lo hace. Brier protege la calidad
probabilística mediante la comparación objetiva con prevalencia; ROC-AUC y
calibración quedan como diagnóstico y desempate. Ninguna sustituye el objetivo
principal de acertar de forma demostrada cuando se recomienda una salida.

## Artefactos publicados

La selección operativa se publica dentro del `quality-catalog.json` compacto
de esquema `1.3`,
con las entradas necesarias para el precálculo y como mínimo:

- `selection_policy`: versión, gates y orden lexicográfico;
- `population_catalog`: identificadores y contadores de poblaciones
  comparables;
- `species_selections`: ganador y descartes por especie y día operativo;
- `species_area_selections`: resolución final para cada especie/área y día
  operativo;
- identidad completa del candidato elegido;
- ámbito usado, `area` o `species_fallback`;
- métricas determinantes, soporte y población;
- número de observaciones y grupos de validación, recomendaciones de salida,
  porcentaje bruto de `Favorables acertados` y límite inferior de Wilson;
- para cada ganador de área, dos bloques `evidence_by_scope` que evalúan el
  **mismo candidato elegido**: uno sobre el área y otro sobre el agregado de la
  especie; un ámbito sin evaluación se conserva como `null` y uno descartado
  mantiene sus métricas junto a `eligible=false` y sus motivos;
- diagnóstico de estabilidad por `validation_group_id`;
- estado explícito de abstención cuando no haya ganador.

El mismo recorrido hold-out genera además `quality-audit-catalog.json`, un
artefacto ampliado que el precálculo no carga y que Historial podrá abrir bajo
demanda. Conserva todas las evaluaciones territoriales y por especie, el orden
de cada candidato aplicable en cada día, su elegibilidad y los motivos de
exclusión. Las métricas se deduplican por candidato dentro de cada ámbito para
que los candidatos `fixed h7` no repitan siete veces el mismo bloque numérico.

Ambos ficheros comparten `snapshot_id`, split oficial y `selection_id`; el
manifiesto referencia y verifica por SHA-256 los dos. El validador ampliado
comprueba que su rango 1 coincide con el ganador territorial o de especie del
catálogo compacto. Así aporta detalle de auditoría sin convertirse en otra
fuente editable de selección.

Los dos son derivados regenerables y viven juntos en
`/media/rainmapper/mushroom-derived/ml_models/batches/<batch_id>/`. No se copian
a `/share`. La publicación runtime los transporta desde ese batch conservando
su SHA-256. `/share/rainmapper/mushroom-data/` mantiene únicamente el registro
pequeño que señala las generaciones instaladas y los datos/configuración no
regenerables; no almacena modelos ni catálogos de calidad.

La selección no será un fichero editable de preferencias. Formará parte del
batch, quedará referenciada y verificada por SHA-256 en su manifiesto y se
instalará o revertirá atómicamente con los modelos que referencia. Alterar una
entrada invalida el digest.

La clave lógica de resolución será:

```text
(training_publication_id, species_id, area_id, prediction_day,
 prediction_target_id)
```

El valor contiene el `candidate_id` completo; nunca solo una versión.

## Contrato con el precálculo semanal

Para cada especie/área/fecha el precálculo:

1. carga y valida la publicación runtime y su catálogo de calidad;
2. deriva el día operativo 1–7 respecto a la fecha de emisión y resuelve la
   entrada de `species_area_selections`; para una pareja operativa sin fila
   territorial copia exclusivamente la resolución `species_selections` de la
   misma especie y día y la marca `species_fallback`;
3. comprueba que los candidatos de la cadena pertenecen a los modelos
   instalados;
4. ejecuta la cadena sellada y elige el primero que supera la aplicabilidad y
   los controles operativos actuales;
5. persiste probabilidad, identidad preferida y efectiva, posición del
   fallback, razones de rechazo, política, ámbito y evidencia efectiva;
6. se abstiene si la selección falta, es inválida o ningún candidato resulta
   aplicable.

No vuelve a leer todas las métricas para ordenar ni compara probabilidades. La
fecha determina cuál de las siete resoluciones ya selladas debe consumir y la
aplicabilidad determina el primer miembro utilizable de su cadena, sin alterar
el orden. Dos precálculos con la misma publicación de entrenamiento usan la
misma tabla especie/área/día, aunque puedan usar posiciones distintas de la
cadena al cambiar las features meteorológicas de cada fecha.

La identidad del SQLite semanal incluirá el digest de la selección. Un cambio
de selección invalida el precálculo anterior. Un cambio de fecha o meteorología
futura invalida solo los resultados semanales y no la selección entrenada.

No se conserva el artefacto anterior como rollback: una vez que el nuevo
entrenamiento queda instalado y su precálculo completo ha sido validado, las
generaciones sustituidas dejan de ser válidas. El reconciliador elimina los
batches de entrenamiento no instalados y la publicación atómica del
precálculo deja un único `active.sqlite3`. Los restos incompletos de staging se
limpian al finalizar o, tras una caída abrupta, antes del siguiente precálculo.
La activación de una generación elimina además del historial de coordinación
los trabajos terminales anteriores de reconstrucción/entrenamiento, conservando
solo la cadena que acaba de quedar activa. La publicación de un precálculo hace
lo mismo con los trabajos terminales de precálculo anteriores. Los trabajos aún
activos o de otro tipo nunca se borran mediante esta poda.

La limpieza referenciada de modelos se fuerza después de completar una
promoción válida, incluso si la opción general de reconciliación preventiva se
mantiene en modo auditoría. Esto evita que el laboratorio local acumule batches
sustituidos y garantiza la misma semántica en HA real. Nunca se ejecuta antes
de que el registro apunte a la generación nueva ni convierte un fallo de
limpieza posterior en rollback de la generación ya activa.

El adaptador de entrenamiento dentro de HA local debe retirar también sus
resultados privados al finalizar. En particular, el resultado ML v0 usa el
nombre físico `ml.<job_id>`; omitir ese prefijo deja copias regenerables aunque
el batch ya esté activo. Esta limpieza no afecta al catálogo, los modelos
instalados ni la publicación runtime. El flujo remoto valida y retira el mismo
resultado mediante su recibo de promoción.

## Compatibilidad de despliegue en HA real

Los números de esquema son independientes:

| Artefacto | Esquema nuevo | Uso |
| --- | ---: | --- |
| `quality-catalog.json` | `1.3` | selección compacta y doble evidencia consumidas por el precálculo |
| `quality-audit-catalog.json` | `1.0` | detalle ampliado para Historial |
| sobre `published-runtime.json` | `1.2` | transporte y publicación del runtime |
| manifiesto científico dentro del sobre | `1.0` | identidad de las fuentes publicadas |

La compatibilidad no se deduce de que dos números coincidan, sino de que cada
consumidor valide explícitamente su contrato, SHA-256, `snapshot_id` y
`selection_id`.

Orden obligatorio para llevarlo a HA real:

1. publicar e instalar una imagen HA que contenga productor, validadores,
   transporte, lector de precálculo y UI nuevos;
2. actualizar el worker que vaya a ejecutar el entrenamiento, porque su imagen
   debe incluir `mushroom_ml_reliability_audit.py` y empaquetar el catálogo
   ampliado;
3. entrenar y comprobar que el manifiesto referencia ambos catálogos y que sus
   SHA y `selection_id` coinciden;
4. refrescar la publicación runtime `1.2` y comprobar que contiene ambos;
5. ejecutar un precálculo nuevo y validar las 504 celdas antes de retirar los
   controles comparativos antiguos.

Un HA o worker anterior puede manejar el catálogo operativo histórico, pero no
garantiza transportar ni publicar `quality-audit-catalog.json`; por ello no se
debe entrenar en real con versiones mezcladas. El código fuente queda preparado
para ambas imágenes, pero no se ha construido ni publicado ninguna release ni
se ha tocado el worker normal en esta sesión.

## Comportamiento de la UI

Las vistas ordinarias mostrarán una probabilidad principal por especie/área/día
y su explicación mínima:

- candidato elegido;
- versión, ventana, familia temporal, horizonte y estimador;
- selección específica del área o fallback de especie, indicando qué ámbito
  decidió la selección;
- acierto observado cuando recomienda salir en porcentaje y fracción `x/x`,
  etiquetado expresamente como valor bruto;
- número de observaciones hold-out únicas y número de floradas de 14 días;
- límite conservador al 95 % destacado junto al valor bruto, sin denominarlo
  simplemente «fiabilidad» ni presentarlo como la probabilidad de la fecha;
- Brier, calibración, cobertura y fecha/publicación de entrenamiento;
- aviso claro si no existe candidato elegible.

La tarjeta puntual mostrará primero el ámbito que decidió la selección y luego
el otro como referencia. Ambos corresponden siempre al mismo candidato e
incluyen `Acierto observado`, fracción `x/x`, `Límite conservador (95 %)`,
observaciones y floradas. Un ámbito ausente se muestra como `no disponible`; si
fue evaluado pero no superó los gates se identifica como insuficiente para
decidir. La mejor apuesta, sus filas, la matriz de `Por especie` y la franja de
siete días mostrarán solo la evidencia decisiva de forma compacta; un tooltip
conserva los dos ámbitos completos para evitar convertir cada resultado en un
bloque de varias líneas. Las pastillas superiores de fecha no llevan
fiabilidad porque solo cambian el día consultado y no son predicciones. Un caso
`1/1` se presentará, por ejemplo, como `Acierto observado 100 % · 1/1` y
`Límite conservador (95 %) 21 %`, nunca como fiabilidad plena sin matices.

La tarjeta denomina la cifra principal `Probabilidad estimada` y el ganador
`Modelo seleccionado`; no habla ya de rangos entre versiones incluidas ni de
varios modelos elegidos. La capa ecológica temporal no puede sustituir esta
probabilidad ni convertirla en un resultado desfavorable mediante umbrales
manuales de lluvia, temperatura, humedad o días desde lluvia. Brier, ROC-AUC,
gates, consenso y reglas internas de comparación quedan plegados en el detalle
técnico. Los veredictos cualitativos se representan como badges: verde para
favorable/alta/compatible, naranja para moderada o limitada, rojo para
incompatible/baja y gris para no disponible.

Probabilidad, acierto observado, límite conservador, observaciones de prueba,
floradas, ámbitos de evidencia, origen de selección, modelo y contexto ecológico
tienen ayuda contextual accesible mediante foco y `title`, con textos en los
tres idiomas de la aplicación.

La explicación ecológica identifica además el episodio concreto utilizado:
fecha, precipitación diaria IDW del área, días hasta la fecha predicha y umbral
operativo de lluvia significativa (5 mm). Es trazabilidad de la entrada, no una
nueva variable predictiva, y no representa ni el acumulado de varios días del
mapa ni necesariamente el valor de la estación más cercana. Añadirla no exige
reentrenar; los precálculos anteriores deben regenerarse para transportar el
nuevo detalle.
El contrato se aplica a todas las versiones operativas instaladas y a todos sus
perfiles/adaptadores; que el ganador cambie entre días no puede hacer desaparecer
la trazabilidad del episodio. Fecha, cantidad, umbral y días hasta la fecha
objetivo forman un bloque indivisible: un adaptador no puede sustituir por
`null` un valor válido heredado de la muestra meteorológica común.

## MOD_0001 — Separación entre elegibilidad ecológica y predicción temporal

Decisión de diseño de 2026-09-04, implementada localmente: en el alcance
operativo actual solo se predicen combinaciones especie/área donde la presencia
de la especie está confirmada. La compatibilidad biológica del hábitat se usa
por tanto para determinar la **elegibilidad de la combinación**, no para
corregir diariamente la probabilidad una vez admitida.

La evolución temporal debe quedar en manos del modelo entrenado. Sus entradas
ya incluyen lluvia en varias ventanas, temperatura, humedad y periodo seco; los
perfiles físicos añaden balance hídrico y estado del agua del suelo. Que una
variable esté presente demuestra capacidad para aprenderla, pero no demuestra
por sí solo que la relación aprendida sea estable o causal. Esa conclusión debe
basarse en validación hold-out agrupada, comparación de ablaciones y, cuando
haya nuevos datos, evaluación prospectiva.

En consecuencia:

- los rangos manuales de lluvia, temperatura, humedad y retraso tras lluvia no
  aplican vetos duros a una predicción temporal;
- los valores provisionales, ausentes o con todos sus límites a cero se tratan
  como `desconocido`, nunca como una ventana biológica real de cero días;
- la última lluvia significativa y el resto del contexto meteorológico se
  conservan como explicación auditable, sin modificar el resultado;
- las abstenciones duras se reservan para contratos incompletos, datos
  insuficientes o una extrapolación que el contrato del modelo no permita;
- `days_since_significant_rain_at_target` no se activa directamente como regla.
  Si se quiere incorporar, será una variable predictiva candidata y necesitará
  un entrenamiento comparativo que demuestre mejora fuera de muestra;
- para futuras áreas sin observaciones, una declaración explícita de presencia
  posible podrá abrir la elegibilidad y permitir el fallback de especie, pero
  no convertirá afinidades ecológicas no validadas en una probabilidad.

La retirada debe hacerse en la interpretación común, no parcheando una vista o
una versión concreta. Debe afectar por igual a cálculo en línea, precálculo,
resumen semanal, consulta por especie y consulta por fecha, y a todos los
adaptadores operativos instalados.

### Fuentes asociadas a MOD_0001

El identificador se conserva literalmente en código, pruebas y documentación
para localizar la modificación con `rg "MOD_0001"`.

- `rainmapper_core/mushroom_prediction_interpretation.py`: conserva el cálculo
  de ventana y compatibilidad como diagnóstico, pero retira su capacidad de
  modificar `verdict`, `reference_range` o `confidence`; trata `0/0/0/0` como
  configuración desconocida.
- `rainmapper-app/app/mushroom_predictor_ui.py`: deja de presentar el antiguo
  veto o los badges ecológicos como parte del resultado operativo; mantiene la
  lluvia significativa concreta como trazabilidad.
- `tests/test_mushroom_prediction_interpretation.py`: cubre que una discrepancia
  ecológica calculada no anula el resultado y que los ceros provisionales no
  forman una ventana real.
- `tests/test_mushroom_ml_multiversion_comparison.py`: conserva la comprobación
  transversal de la información ecológica calculada en el payload común.
- `tests/test_web_server_auth.py`: impide que campos de veto heredados vuelvan a
  aparecer como resultado operativo en la UI.

### Validación exigida para retirar los vetos

1. Un perfil con ventana `0/0/0/0` produce contexto ecológico `desconocido` y
   nunca `incompatible`.
2. Una predicción estadística elegible no cambia de resultado por una regla
   externa de antigüedad de lluvia, temperatura o humedad.
3. La explicación sigue mostrando, cuando exista, fecha, milímetros, días y
   umbral del episodio significativo usado como referencia.
4. Cálculo en línea y precálculo producen el mismo resultado y la misma
   trazabilidad para idéntica especie, área, fecha y artefactos.
5. Se ejecutan pruebas de regresión sobre todas las versiones y adaptadores
   instalados; el manifiesto y los contratos solo se versionan si cambia el
   esquema intercambiado, no por el mero cambio de criterio interno.
6. Antes de afirmar que lluvia o temperatura aportan señal generalizable, se
   compara el modelo completo contra ablaciones sin esos grupos de variables y
   se archivan Brier, ROC-AUC, calibración y soporte independiente.

### Revisión pendiente: señal hídrica antecedente y atribución temporal

La retirada operativa de los vetos de `MOD_0001` no cierra la investigación
sobre el papel temporal de la lluvia. Se conserva como trabajo posterior la
separación conceptual entre:

- **lluvia reciente**, acumulada inmediatamente antes de la fecha objetivo;
- **señal hídrica antecedente**, acumulada en una ventana anterior que podría
  contribuir a iniciar el proceso de fructificación;
- **episodio significativo**, evento diario concreto utilizado actualmente
  como referencia temporal en la explicación;
- **estado hídrico persistente**, que incluye reserva, balance y condiciones de
  secado posteriores y no puede reducirse a un único acumulado.

Sporas denomina «lluvia de activación» a la lluvia de un periodo anterior que,
según la especie, pudo disparar la fructificación y que interviene en un filtro
interno. La idea de separar ventanas es una hipótesis útil, pero su visor no
publica las fechas de la ventana, su duración, el umbral, las fuentes y pesos
meteorológicos ni la función que transforma el acumulado en probabilidad. Sus
valores no deben copiarse como reglas ni emplearse como verdad de referencia.

Rainmapper debe resolver esta cuestión mediante aprendizaje y evaluación fuera
de muestra, no mediante un nuevo veto manual. La revisión deberá:

1. inventariar qué variables de lluvia, temperatura, humedad, balance y
   retraso consume realmente cada candidato, no solo cuáles están disponibles;
2. medir ablaciones por grupos de variables y perturbaciones controladas del
   historial meteorológico;
3. comprobar calibración por intervalos, prestando especial atención a
   probabilidades saturadas próximas a 0 % o 100 %;
4. comparar retardos y ventanas mediante los mismos grupos de florada del
   hold-out, sin seleccionar y evaluar sobre los mismos casos;
5. diferenciar validación global de especie y evidencia territorial: un
   `species_fallback` no convierte una probabilidad extrema en evidencia local;
6. realizar evaluación prospectiva archivando la predicción anterior a conocer
   cada observación, en lugar de validar contra otro predictor;
7. conservar procedencia meteorológica completa: fechas, estaciones o celdas,
   distancias, pesos, cobertura, correcciones y agregados entregados al modelo.

Si la atribución puede calcularse de forma reproducible, la UI podrá explicar
la señal sin afirmar causalidad, por ejemplo: ventana antecedente evaluada,
episodio principal y cambio de probabilidad al retirar ese episodio. Hasta
entonces se mantendrá «lluvia significativa usada» como trazabilidad de entrada
y no se mostrará una supuesta «lluvia de activación».

Los contrastes exploratorios observados el 2026-09-04 ilustran el problema, no
constituyen una validación de ninguno de los sistemas:

- *Amanita caesarea*/Olvan: Sporas mostró 63,4 % y Rainmapper 69 %, aunque la
  precipitación de la celda de Sporas no pudo reconstruirse con las estaciones
  oficiales visibles;
- *Lactarius deliciosus*/Riu de Cerdanya: Sporas mostró 9,5 % y Rainmapper
  100 %, pese a acumulados recientes del mismo orden; Rainmapper recurrió al
  fallback global de especie, sin evidencia territorial disponible;
- en el segundo caso, la altitud de 1.073 m mostrada por Sporas permaneció
  constante al pulsar puntos situados aproximadamente sobre cotas de 1.850 y
  2.050 m, y tampoco coincidió exactamente con los 1.031 m de la estación SAIH
  Ebro visible más cercana. No se conoce si representa una celda, un agregado,
  otra fuente o un defecto del visor.

Por tanto, una coincidencia puntual entre porcentajes no demuestra concordancia
y una divergencia tampoco identifica por sí sola cuál es correcto. La unidad de
comparación científica será la observación posterior de florada, acompañada de
las entradas exactas y del artefacto que produjo cada predicción.

`Por especie` no mostrará las antiguas cabeceras de «Fiabilidad cuando
recomienda salir» ni los episodios agregados por especie o área. Pertenecían al
backtest anterior, no a la selección específica de cada día, y podían parecer
una segunda medida comparable. La evidencia aplicable se presenta dentro de
cada celda diaria.

La probabilidad continúa etiquetada como cálculo para el área. Ninguna métrica
global de especie se atribuye al área y ninguna métrica territorial se mezcla
con la global: son dos evaluaciones separadas del mismo candidato.

La UI no ordena candidatos para decidir qué probabilidad enseñar. El futuro
evaluador de calidad puede mostrar todos los candidatos y sus métricas como
auditoría, pero será una lectura pura del catálogo sellado.

La presentación acordada será una pestaña nueva, **Fiabilidad**, separada de
Historial. Su contrato funcional, navegación por siete horizontes, tooltips y
pruebas de aceptación se definen en
`mushroom-predictor-reliability-screen-spec-es.md`. Se implementará únicamente
después de validar y desplegar en HA real la base operativa actual.

Los overrides manuales, si se conservan para herramientas de laboratorio,
serán explícitos, temporales y no modificarán la selección publicada. El
Predictor de producto no expone selección manual ni versión preferida: compara
siempre todas las versiones instaladas con perfiles operativos.

## Invalidación y ciclo de vida

Requieren nuevo entrenamiento y nueva selección:

- cambios en observaciones admitidas;
- cambios en la meteorología histórica consumida por features o evaluación;
- cambios de split o población hold-out;
- cambios en modelos, hiperparámetros, perfiles, ventanas, contratos,
  horizontes o estimadores;
- cambios en especies o áreas del alcance operativo;
- cambios en gates o en la política de ranking.

Requieren únicamente nuevo precálculo:

- nueva fecha de emisión o ventana semanal;
- cambios en meteorología futura/operativa que no alteran el corpus histórico
  de entrenamiento;
- pérdida o corrupción del SQLite regenerable con selección aún válida.

La instalación transaccional cambia conjuntamente modelos, catálogos y
selección. Un rollback interno antes de completar esa instalación también debe
revertirlos juntos; después de activar el batch nuevo no se conserva un batch
anterior como rollback. Nunca se combinan modelos de una generación con la
selección de otra.

## Fallos y degradación

- Catálogo o digest inválido: no predecir con una selección reconstruida.
- Candidato no instalado: probar el siguiente candidato sellado; si la cadena
  se agota, abstenerse y señalar inconsistencia de publicación.
- Área operativa sin fila territorial: usar solo el fallback de especie/día ya
  sellado; si tampoco existe, abstenerse.
- Área desconocida fuera del alcance operativo: requerir nuevo entrenamiento.
- Ningún candidato territorial elegible: usar únicamente el fallback de la
  misma especie sellado durante entrenamiento.
- Especie sin candidato elegible: mostrar indisponibilidad científica; no usar
  otra especie, la versión preferida ni el porcentaje más alto.
- Todos los candidatos fiables fuera de dominio: abstenerse; nunca saltar a un
  modelo no incluido en la cadena sellada.
- Precálculo antiguo con otro digest de selección: tratarlo como incompatible,
  no como resultado desactualizado reutilizable.

## Implementación por fases

### Fase 0 — auditoría acotada

- Separar estrictamente todos los `split_id`; verificar cuál es el contrato
  autoritativo y no comparar métricas acumuladas entre splits.
- Validar `observation_id` como `evaluation_case_id` sin versión, perfil,
  ventana, horizonte ni estimador.
- Detectar cuántas filas y candidatos repiten cada observación.
- Contar observaciones, grupos temporales, recomendaciones de salida, clases,
  cobertura y poblaciones distintas por especie/área.
- Medir sensibilidad retirando grupos completos como diagnóstico separado del
  ranking.
- No ajustar modelos ni lanzar un entrenamiento real para esta auditoría.
- Verificar con esos datos el efecto de no imponer mínimos manuales y conservar
  siempre fracciones, Wilson y diagnósticos para no ocultar evidencia débil.

La herramienta read-only de esta fase es
`scripts/audit-mushroom-ml-reliability.py`. Acepta filtros repetibles de especie,
`area_id` y `split_id`; sin filtros de especie o área recorre todo el split
oficial presente en el hold-out y genera JSON. Su
núcleo puro está en `rainmapper_core/mushroom_ml_reliability_audit.py` para que,
si la política resulta válida, pueda integrarse después en el entrenamiento sin
copiar la lógica. Toda salida queda marcada como provisional y no es consumible
por runtime. La ejecución y sus hallazgos están en
`docs/reports/mushroom-reliability-audit-2026-09-02.md`.

El esquema CLI `0.2-audit` devuelve siete `operational_days` por cada
especie/área. Cada día contiene el candidato exacto —incluido
`temporal_contract_id`—, métricas, población comparable, estabilidad y estado
`winner` o `abstain`. Esta es deliberadamente la misma forma conceptual que el
entrenamiento materializa dentro de los catálogos del batch. El fichero JSON
independiente producido manualmente por la CLI sirve solo para revisión y no se
instala. No debe confundirse con `quality-audit-catalog.json`, que sí es un
artefacto sellado del batch para que Historial lea las métricas sin recalcular.

Por defecto la CLI audita únicamente `fruiting_groups_14d`. `--species` y
`--area` pueden repetirse para cualquier combinación; `--split` permite un
diagnóstico explícito de otro contrato y `--all-splits` los recorre todos sin
mezclarlos. `--include-candidates` incluye también descartes y sus motivos.

### Fase 1 — catálogo y selector puro

- [x] Extender el constructor y validador del catálogo al esquema `1.2`.
- [x] Extenderlos a `1.3` para sellar la evidencia de área y de especie del
  mismo candidato en cada resolución ganadora.
- [x] Implementar agregación territorial, grupos comparables, gates, ranking y
  fallback.
- [x] Sellar selecciones deterministas dentro de `quality-catalog.json` durante
  el benchmark que precede al entrenamiento operativo y comprobar que todo
  ganador referencia un artefacto del plan antes de instalar el batch.

La implementación comparte la única lectura de las filas hold-out con el
constructor del catálogo; no vuelve a abrir el fichero ni ejecuta inferencia.
Sobre el batch local `local_operational_20260902T145853Z` —27.328 filas y 83
MiB—, el catálogo completo tardó 11,43 s, frente a unos 9 s de la agregación
anterior aislada. La selección añade por tanto aproximadamente 2–3 s al proceso
local, no un recorrido combinatorio. Esta medición caracteriza la máquina y el
batch citados; el próximo entrenamiento permitirá medir el incremento dentro
del flujo real.

El prototipo ampliado sobre el hold-out instalado de 27.328 filas contiene
15.354 evaluaciones únicas por especie/área y 2.866 por especie, además de 301
y 56 decisiones diarias respectivamente. Serializado de forma compacta ocupa
18.768.688 bytes y construir conjuntamente ambos catálogos tardó 13,45 s en la
máquina local. Frente al JSON directo de auditoría de 60 MiB, la deduplicación
evita repetir métricas fijas por cada día. Estas cifras caracterizan ese batch,
no son límites contractuales.

### Fase 2 — consumo por el precálculo

- [x] Resolver exclusivamente la selección publicada, sin ranking en línea.
- [x] Calcular y almacenar el único miembro ordinario por especie/área/día.
- [x] Persistir en SQLite la resolución y su evidencia para que `Esta semana`,
  `Por especie` y `Consulta por fecha` compongan el mismo resultado.

El batch verificado materializa filas territoriales para las 43 parejas con
población hold-out; el precálculo operativo cubre 72. Para las 29 restantes no
inventa un ganador ni compara candidatos: copia la decisión especie/día ya
sellada por el entrenamiento y la marca `species_fallback`. Esta expansión
determinista resuelve el alcance, pero no reabre la evaluación científica.
Las cifras `84` ganadores territoriales y `161` fallbacks del catálogo anterior
quedan obsoletas con la comparación directa entre ámbitos. La prevalidación del
mismo hold-out con selección `1.2` produce 22 ganadores territoriales, 223
fallbacks y 56 abstenciones entre las 301 filas entrenadas. El reparto final de
las 504 celdas se comprobará sobre el nuevo precálculo, sin anticiparlo como
resultado validado. `quality-audit-catalog.json` conserva 43 ámbitos territoriales y
ocho ámbitos de especie; para un área sin hold-out, Historial debe explicar que
no existe auditoría territorial y mostrar separadamente la evidencia del
fallback de especie, nunca atribuírsela al área.

### Fase 3 — simplificación de producto

- Presentar una probabilidad principal por especie/área.
- Convertir la comparación completa en auditoría secundaria, si se conserva.
- Mantener fuera del camino ordinario la selección manual de versiones: el
  inventario instalado se resuelve dinámicamente y todos sus perfiles
  operativos participan automáticamente.

## Pruebas y aceptación

### Catálogo y selección

- misma entrada produce bytes o estructura canónica idéntica;
- separación completa de especie, área y candidato;
- separación completa de los siete días operativos: `lag hN` solo compite en
  el día `N`, mientras `fixed h7` puede competir en todos;
- conservación de `temporal_contract_id` exacto y prohibición de retargeting;
- `evaluation_case_id` independiente del candidato;
- prohibición de sumar un caso repetido entre modelos, perfiles u horizontes;
- detección de poblaciones hold-out diferentes;
- fórmulas de Brier, baseline, calibración y clasificación;
- fórmula y límite inferior de Wilson de `Favorables acertados`;
- prohibición de mezclar `split_id` y detección del split real por fila;
- retirada determinista de grupos temporales completos como diagnóstico que no
  altera el ganador principal;
- elegibilidad por clases, recomendación favorable, probabilidades válidas,
  población comparable y mejora de Brier frente a prevalencia;
- ausencia de mínimos manuales de observaciones, recomendaciones o recall;
- desempates lexicográficos estables;
- fallback solo desde área a la misma especie;
- abstención cuando no exista ganador;
- rechazo de referencias ausentes y digest incorrecto;
- ninguna llamada a fit, Predictor, meteorología o worker durante la selección.

### Precálculo

- usa exactamente el candidato sellado para cada especie/área/día;
- dos ventanas semanales conservan la misma tabla de siete resoluciones con la
  misma selección;
- no ordena ni evalúa candidatos;
- no calcula miembros no seleccionados en la ruta ordinaria;
- persiste identidad y evidencia del ganador;
- falla cerrado ante esquema, digest o modelo incompatibles;
- un cambio de selección invalida el SQLite anterior.

### UI y extremo a extremo local

- una probabilidad principal y trazabilidad coherente;
- tarjetas basadas en un candidato, observaciones únicas y grupos explícitos,
  nunca en sumas de varios `evaluated_count`;
- fallback y abstención visibles;
- abrir o navegar no ejecuta evaluación científica;
- override de laboratorio no persiste preferencia;
- equivalencia entre probabilidad del ganador sellado y el mismo candidato en
  la ruta comparativa anterior;
- smoke completo y `git diff --check` sobre el código definitivo.

## Criterios de finalización

La entrega estará completa cuando:

1. cada especie/área/día operativo tenga ganador territorial, candidato global
   de especie o abstención explícita dentro del batch entrenado, después de
   comparar área y especie con la misma métrica conservadora;
2. el precálculo consuma esa resolución sin reevaluarla;
3. la ruta ordinaria calcule y presente una única probabilidad trazable;
4. ninguna consulta interactiva compare candidatos ni ejecute inferencia;
5. cualquier cambio científico relevante obligue a publicar una nueva
   selección mediante entrenamiento;
6. el ganador maximice la fiabilidad conservadora demostrada al recomendar una
   salida, sin sumar evidencia de candidatos distintos;
7. el coste de selección quede demostrado como una agregación finita de los
   hold-outs existentes.

## Decisiones cerradas y comprobaciones pendientes

Quedan cerrados `fruiting_groups_14d` como split autoritativo, Wilson bilateral
al 95 % como criterio principal y la ausencia de mínimos manuales de soporte o
recall. La retirada de grupos queda como diagnóstico separado y no interviene
en el ranking.

La Fase 1 queda implementada localmente con esquema de selección `1.2`: el
productor exige `observation_id` y
`validation_group_id`, mantiene cohortes comparables, materializa el fallback
agregado de la misma especie, valida cobertura diaria y sella el digest de la
selección. La sensibilidad por grupos permanece como dato explicativo y no como
gate.

El batch `local_operational_20260902T183908Z` verificó la Fase 1: catálogo `1.2`,
636/636 fits, cero fallos, selección completa y digest correcto. La Fase 2 y la
presentación mínima de la Fase 3 están implementadas en código y pruebas;
quedan reconstruir explícitamente los componentes locales, ejecutar un
precálculo nuevo y validar visualmente las tres vistas antes de cerrarlas.
