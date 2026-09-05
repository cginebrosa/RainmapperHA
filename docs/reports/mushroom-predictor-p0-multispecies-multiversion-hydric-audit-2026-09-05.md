# Auditoría P0 del Predictor: señal hídrica multiespecie y multiversión

Fecha de ejecución: 5 de septiembre de 2026.

Estado: concluida para Rovelló/Riu y ampliada a los ganadores operativos de
Rovelló, Edulis, Pinícola, Aereus y Ou de reig. Esta auditoría no instala ni
promueve modelos, no modifica V2--V6, no publica un V7 y no altera
observaciones. Los modelos de las ablaciones son copias aisladas de laboratorio.
Llanega negra, Marçot y Múrgola negra quedan aplazadas porque sus conjuntos
externos actuales contienen una sola clase.

## Conclusión

La predicción de Riu de Cerdanya no alcanza el 99,9478 % por una regla ad hoc de
«lluvia de activación». El umbral de lluvia significativa de 5 mm, la fecha del
episodio y los días transcurridos aparecen en el diagnóstico, pero no forman
parte de las 27 columnas que consume este modelo.

El modelo sí aprende una señal hídrica antecedente mediante acumulados de
lluvia, balance lluvia menos evapotranspiración y un balance simplificado de
agua en el suelo. Para Riu, la señal útil se parece más a «agua hace dos o tres
semanas seguida de secado» que a «ha llovido ahora». Al retirar toda la lluvia
directa, la predicción solo cambia de 99,9478 % a 99,9253 %. Al retirar a la vez
el balance climático y el estado del suelo baja a 77,5802 %; si se elimina todo
el bloque hídrico baja a 67,4263 %.

Eso no demuestra todavía que el SMI actual sea una buena representación del
estado hídrico. De hecho, retirar solo sus siete columnas mejora claramente el
resultado conjunto de los 112 casos reservados. Hay información duplicada y
señales correlacionadas entre lluvia, balance, humedad y suelo; el modelo puede
repartir pesos inestables entre ellas. El bloque hídrico es importante para el
horizonte de un día, pero la contribución independiente del SMI no está
validada.

Además, el estimador ganador es una regresión logística. Puede sumar por
separado lluvia y SMI, pero no puede aprender por sí solo una interacción del
tipo «esta misma lluvia vale más cuando el suelo ya estaba hidratado». Para
comprobarlo se añadió explícitamente esa combinación en copias aisladas de V5 y
V6. No produjo una mejora estable: perjudicó a Aereus y Pinícola, cambió de
signo según el corte en Ou de reig y Rovelló-V6, y la ampliación `31--59` días
empeoró Rovelló-V5. La prueba queda cerrada sin promover un V7.

## Qué se reprodujo

Se usó el lote operativo
`local_operational_20260903T231056Z` y su candidato:

- especie: `lactarius_deliciosus`;
- versión: `biology_v3`;
- perfil: `common_idw_plus_physical_state`;
- contrato temporal: `lag_event_biology_v3`;
- estimador: `logistic_regression_reduced_v1`;
- horizonte auditado: un día;
- selección: fallback global de especie.

La reconstrucción usa 210 filas para ajustar y las mismas 112 filas externas
del lote para evaluar los siete horizontes. Reproduce las 112 probabilidades
archivadas con una diferencia máxima de `5e-11`. Al reajustar con las 322 filas
disponibles, reproduce la predicción operativa de Riu con una diferencia de
`2,33e-8`.

Los cortes `fruiting_groups_7d` y `fruiting_groups_14d` tienen identificadores
de grupo distintos, pero en Rovelló dejaron exactamente las mismas 112 filas
fuera. Por tanto, sus resultados idénticos no cuentan como dos confirmaciones
independientes.

## Qué significa el 100 %

Para el horizonte de un día quedaron 16 observaciones reservadas: 13
favorables y 3 desfavorables. El candidato clasificó correctamente las 16. Esas
16 filas representan 10 floradas o grupos temporales independientes, porque
varias observaciones comparten lugar y fecha.

El dato es real para ese conjunto pequeño, pero no equivale a una certeza del
100 % en una salida nueva. El Brier de 0,0355 mejora mucho el 0,1553 de predecir
solo con la frecuencia del entrenamiento, mientras que el error de calibración
por intervalos es 0,118. En términos sencillos: ordena y separa muy bien esos
casos, pero sus porcentajes todavía pueden ser aproximadamente 12 puntos más
extremos o más tímidos de lo que corresponde. En los 112 casos de todos los
horizontes, la pendiente de calibración es 0,673, también compatible con
probabilidades demasiado extremas.

El test de un día no contiene ninguna observación de Riu de Cerdanya. Sin
embargo, el ajuste completo sí contiene cinco observaciones históricas
favorables de Riu. Por tanto, no es una transferencia totalmente ciega a un
área nunca vista, aunque el 100 % externo no haya sido comprobado allí. Esas
cinco observaciones, todas positivas, no bastan para elegir un ganador local y
por eso se aplica el ganador de la especie.

## Variables realmente consumidas

Las 27 columnas son:

- horizonte: 1;
- lluvia directa: cuatro acumulados, `0--3`, `4--7`, `8--14` y `15--21` días;
- sequía reciente: un contador de días secos;
- temperatura: máxima y mínima de 7 días, corregidas por altitud;
- humedad relativa: máxima y mínima en cuatro ventanas hasta 21 días;
- balance climático: cuatro ventanas `0--7`, `8--14`, `15--21` y `22--30` días;
- estado del suelo: nivel medio, mínimo, cambios a 7 y 14 días, recarga,
  déficit y secado a 7 días.

No hay una columna directa de altitud. La altitud actúa indirectamente al
corregir las temperaturas antes de que lleguen al modelo. Por eso la ablación
«sin altitud directa» es un control nulo y da exactamente el mismo resultado.
Separar la corrección altitudinal de la temperatura exige regenerar una segunda
meteorología sin dicha corrección; quitar temperatura no aísla altitud.

El balance de suelo no usa siempre 365 días. El código prueba calentamientos de
90, 180 y 365 días y elige el más corto que haya olvidado el estado inicial. El
precálculo no conserva cuál de los tres fue elegido para esta fila de Riu, de
modo que no puede afirmarse que aquí se usaran exactamente 365 días.

La aplicabilidad registrada para Riu es
`within_observed_range`: ninguna de las 27 variables está fuera del rango visto
al entrenar. Esto reduce el riesgo de extrapolación climática, pero no sustituye
una prueba externa local.

## Por qué Riu queda tan alto

La siguiente descomposición pertenece al modelo lineal reajustado con las 322
filas y reproduce el artefacto operativo. Las cifras son aportaciones a la
decisión interna del modelo respecto de la media de entrenamiento; no son
efectos causales.

| Bloque | Empuje interno |
|---|---:|
| Punto de partida del modelo | +4,447 |
| Estado y dinámica del suelo | +3,519 |
| Humedad relativa | +3,057 |
| Lluvia directa | +0,684 |
| Balance climático | +0,530 |
| Horizonte | +0,044 |
| Contador de sequía | -0,045 |
| Temperatura | **-4,678** |

La temperatura máxima de 27,196 °C es por sí sola el freno más fuerte
(`-4,493`). Confirma que el calor alto empuja la predicción hacia abajo.

El suelo actual también se interpreta como seco: nivel medio 0, mínimo 0 y
déficit 1 restan conjuntamente cerca de un punto. Sin embargo, el secado a 7
días y los cambios negativos a 7 y 14 días suman aproximadamente 3,82 puntos y
dominan ese freno. El modelo parece reconocer una fase posterior a una recarga,
ya en descenso, pero con estos datos no puede distinguirse una relación
biológica real de una correlación propia de cuándo se registraron las floradas.

La lluvia de `15--21` días suma; la lluvia de `0--3` días es casi nula en Riu y,
por estar por debajo de la media, también termina sumando en este ajuste. Esto
no se comporta como un umbral simple de activación reciente.

## Ablaciones controladas

En cada fila se retiró el bloque indicado, se reajustó el mismo estimador y se
mantuvieron intactos los casos reservados. Brier menor es mejor. «Errores H1»
cuenta fallos entre los 16 casos del horizonte de un día. La última columna es
la proyección de Riu tras reajustar cada variante con las 322 filas disponibles.

| Variante | Brier 112 | AUC 112 | Brier H1 | Errores H1 | Riu |
|---|---:|---:|---:|---:|---:|
| Completo | 0,0939 | 0,8875 | 0,0355 | 0 | 99,9478 % |
| Sin lluvia directa ni contador seco | 0,0993 | 0,9267 | 0,0372 | 0 | 99,9253 % |
| Sin balance climático | 0,1094 | 0,8749 | 0,0462 | 0 | 99,2729 % |
| Sin estado del suelo | **0,0545** | **0,9649** | **0,0307** | 0 | 98,9908 % |
| Sin balance ni estado del suelo | 0,0875 | 0,9152 | 0,1210 | 3 | 77,5802 % |
| Sin ningún bloque hídrico | 0,1018 | 0,8833 | 0,1388 | 3 | 67,4263 % |
| Sin temperatura | 0,1344 | 0,8802 | 0,0681 | 1 | 99,6697 % |
| Sin humedad relativa | 0,0987 | 0,9304 | 0,0185 | 0 | 99,5872 % |
| Sin altitud directa | 0,0939 | 0,8875 | 0,0355 | 0 | 99,9478 % |

Resultados por retardos:

- retirar lluvia `0--3` mejora el Brier conjunto en 0,0058;
- retirar lluvia `4--7` lo mejora en 0,0018;
- retirar lluvia `8--14` lo empeora en 0,0014;
- retirar lluvia `15--21` lo empeora en 0,0093 y cambia cinco decisiones;
- en el balance climático, la ventana que más empeora el Brier al retirarla es
  `15--21` (+0,0215); `22--30` también aporta (+0,0094);
- retirar la dinámica del suelo mejora el Brier conjunto de 0,0939 a 0,0718;
  retirar el estado actual lo mejora a 0,0832.

La señal temporal aprendida está, por tanto, más en `15--30` días que en la
lluvia inmediata. Es compatible con la pregunta planteada por «lluvia de
activación», pero no demuestra causalidad ni justifica copiar el valor de
Sporas.io.

## Decisión técnica

No se debe modificar ni sustituir V2--V6 a partir de esta prueba. Tampoco hay
base para publicar ahora un V7.

Las ablaciones y la prueba adicional de interacción ya comparan las
representaciones hídricas actuales sobre los mismos grupos externos. Ninguna
alternativa mejora Brier y calibración de forma estable entre especies y entre
los cortes de 7 y 14 días. Por eso se conservan las versiones actuales y se
repetirá la evaluación hold-out cuando existan nuevas observaciones; no hace
falta guardar cada precálculo diario. `MOD_0001` se mantiene: los cálculos
ecológicos siguen siendo diagnósticos y no vetan ni alteran la probabilidad del
modelo.

## Comprobación ciega del 5 de septiembre

El precálculo activo se escribió a las 00:02:30 CEST. Después, sin reentrenar ni
recalcular, se añadieron en HA local seis observaciones correspondientes al 5
de septiembre: tres en Salteguet y tres en La Masella. El fichero local se
guardó a las 20:07:21 CEST. Las seis están validadas e incluidas para
calibración; `scarce` es favorable y `absent` es desfavorable.

| Área | Especie | Predicción archivada | Clasificación | Resultado observado | Brier individual |
|---|---|---:|---|---|---:|
| Salteguet | Edulis | 65,9818 % | Favorable | Favorable | 0,115724 |
| Salteguet | Rovelló | 96,5041 % | Favorable | Favorable | 0,001222 |
| Salteguet | Pinícola | — | Abstención | Desfavorable | — |
| La Masella | Edulis | 65,7802 % | Favorable | Favorable | 0,117099 |
| La Masella | Rovelló | 95,7768 % | Favorable | Favorable | 0,001784 |
| La Masella | Pinícola | 82,5228 % | Favorable | Desfavorable | 0,681001 |

Las probabilidades exactas proceden de
`docker-media/rainmapper/predictor_precompute/active.sqlite3`, artefacto
`sha256:04eac3b1d83224ddf7730771de038020af4c1a52ba5ab06faeaf954410e4223d`.
Su fecha objetivo es el 5 de septiembre, su fecha de emisión es el 4 y emplean
el lote `local_operational_20260903T231056Z`, entrenado antes de crear las seis
observaciones. En consecuencia, esta comparación no contiene fuga de la
respuesta observada hacia el modelo.

Las cuatro recomendaciones favorables de Edulis y Rovelló acertaron el signo.
Pinícola aporta el contraste que faltaba: en La Masella el 82,5228 % fue una
falsa recomendación favorable, mientras que en Salteguet el sistema se abstuvo
y la observación fue desfavorable. La abstención no se contabiliza como un
acierto ni recibe Brier. Entre las cinco predicciones emitidas hubo cuatro
aciertos de clase y un error, pero estos casos comparten fecha y condiciones y
no forman una muestra suficiente para estimar un «80 % de acierto» general ni
para validar la calibración.

La comprobación sí demuestra que el contraste archivado puede conservar tanto
confirmaciones como una falsa alarma real, sin seleccionar únicamente casos
favorables. Se incorporarán como grupos cronológicos externos en la siguiente
batería controlada siempre que su reconstrucción meteorológica resulte
elegible.

### Incorporación a la batería controlada

La reconstrucción posterior confirmó que las dos observaciones de Salteguet son
elegibles y quedan en el hold-out recalculado tanto con `fruiting_groups_7d`
como con `fruiting_groups_14d`. No se añadieron al entrenamiento de las copias
evaluadas. Las tres observaciones posteriores de La Masella aún no se han
reconstruido ni usado en ninguna prueba. En el benchmark de retardos cada
observación produce siete filas —una por horizonte—, pero continúa siendo un
solo caso y un solo grupo, no siete confirmaciones independientes.

Los porcentajes de esas copias no deben compararse como si fueran una
reproducción de los modelos operativos completos. Las seis salidas de la tabla
son la comprobación ciega real; las copias de laboratorio se reajustan sin los
grupos externos para medir únicamente la diferencia entre D0, D1 y D2.

Las trazas de lluvia inferiores a 1 mm hacen que la racha actual y la propuesta
sean materialmente distintas. En las dos observaciones, según el horizonte, la
racha actual toma valores de 8 a 2 días y la variante de 1 mm de 11 a 5: añade
exactamente tres días secos.

Se ejecutaron D0 —definición actual—, D1 —menos de 1 mm cuenta como seco— y D2
—sin contador— en seis configuraciones V2--V4, cinco especies y ambos cortes
agrupados. Sobre las 30 combinaciones de cada corte:

| Corte | D1 mejora / empeora / empata | Delta Brier medio D1 | D2 mejora / empeora / empata | Delta Brier medio D2 |
|---|---:|---:|---:|---:|
| 7 días | 18 / 11 / 1 | -0,0029 | 19 / 8 / 3 | -0,0036 |
| 14 días | 13 / 17 / 0 | +0,0017 | 19 / 8 / 3 | -0,0037 |

D1 no es estable y no debe adoptarse. D2 es más favorable en conjunto, pero no
gana en todas las especies y algoritmos, por lo que tampoco justifica aún
retirar globalmente la columna. En cambio, quitar todo el bloque hídrico
empeora 21 de 30 comparaciones con grupos de 14 días y 20 de 30 con grupos de
7 días. La información hídrica sí aporta; lo que no demuestra valor incremental
estable es este contador explícito.

El resultado completo y reproducible se guarda en
`docker-data/audits/mushroom-dry-spell-ablation-20260905/results/controlled-dry-spell-ablation.json`.
No se ejecutó la búsqueda secundaria de eventos de recarga de tres días porque
el criterio previo no se cumplió.

## Precálculo y presencia de V6

El precálculo activo contiene 420 selecciones: V6 180 (42,9 %), V3 137
(32,6 %), V2 53 (12,6 %), V5 35 (8,3 %) y V4 15 (3,6 %). El 6 de septiembre
hay 36 V6 de 60 selecciones. En Rovelló las 17 áreas de ese día usan V6 porque
comparten el ganador de especie y horizonte; Edulis sigue concentrado en V3.

El lote entrenado continúa siendo el mismo del 3 de septiembre. El artefacto
SQLite anterior fue sustituido y no existe una copia local, por lo que no es
posible afirmar fila por fila qué selección cambió respecto del precálculo
anterior.

## Ampliación multiespecie

### Qué significaba «SMI problemático»

No significa que el estado hídrico del suelo sea una mala idea ecológica ni que
deba retirarse del Predictor. Significa algo mucho más limitado: en la prueba de
Rovelló, al quitar las siete columnas concretas con las que V3 resume el suelo,
el error reservado conjunto bajó. Al quitar a la vez suelo y balance, en cambio,
el horizonte de un día empeoró mucho. Por tanto, los datos respaldan que existe
señal hídrica, pero no demuestran que su representación actual mediante esas
siete columnas sea la mejor.

Las causas compatibles con el resultado, todavía no distinguidas, son
redundancia con lluvia y balance, pocos episodios independientes o que la forma
actual del resumen de suelo permita aprender coincidencias propias de las
observaciones disponibles. Ninguna de ellas autoriza un cambio operativo.

### Qué significa que V3 sea lineal

El estimador de Rovelló-H1 calcula una suma: una aportación de la lluvia, otra de
la temperatura, otra de la humedad, otra del balance y otra del suelo. Puede
aprender que el calor resta o que cierto estado del suelo suma. No puede aprender
directamente una regla combinada como «la misma lluvia ayuda si el suelo venía
húmedo, pero casi no ayuda si venía seco» salvo que se le entregue expresamente
esa combinación o se utilice un estimador capaz de aprender interacciones.

### Evidencia externa disponible

En la partición oficial `fruiting_groups_14d`, para V3 lag y el horizonte de un
día, existen:

| Especie | Observaciones reservadas | Grupos independientes | Favorables / desfavorables |
|---|---:|---:|---:|
| Rovelló | 16 | 10 | 13 / 3 |
| Edulis | 21 | 10 | 8 / 13 |
| Pinícola | 31 | 12 | 12 / 19 |
| Aereus | 32 | 11 | 19 / 13 |
| Ou de reig | 30 | 11 | 11 / 19 |

Esto permite comparar especies. No permite aún declarar ganadores fiables en
todas las zonas. Muchas zonas solo aportan uno o dos grupos. Las excepciones con
algo más de base son sobre todo Olvan para Aereus y Ou de reig; aun allí debe
informarse la incertidumbre. En el resto puede medirse cuánto cambia una
predicción al retirar variables, pero no llamarlo mejora de acierto zonal.

### Primera comparación común de variables

Se ha repetido la ablación con el mismo V3 logístico y los mismos grupos
reservados para las cinco especies. Esta comparación mantiene fijo el método y
permite preguntar si una familia de variables aporta señal de forma estable. No
representa todavía al ganador operativo de todas las especies.

La conclusión es firme: **no existe un efecto hídrico universal y estable en las
cinco especies con la representación V3 actual**. Retirar suelo, balance o lluvia
mejora unas especies y empeora otras, y algunos signos cambian entre agrupaciones
de 7 y 14 días. En cambio:

- la lluvia inmediata no emerge como señal dominante común;
- en Rovelló, la información de `15--30` días es claramente más útil que la de
  `0--7` días;
- en las demás especies, la ventana hídrica útil no se repite con suficiente
  estabilidad como para fijarla todavía;
- que la temperatura sea el freno más fuerte está comprobado para la predicción
  actual Rovelló/Riu, no para todas las especies;
- retirar bloques completos puede cambiar el uso de los restantes al reajustar
  el modelo; por eso no deben interpretarse las diferencias como causalidad.

La lectura acumulativa responde explícitamente a «qué ocurre al añadir» cada
bloque. La tabla usa el horizonte de un día y la partición oficial de 14 días;
Brier menor es mejor:

| Especie | Sin bloque hídrico | Solo lluvia | Lluvia + balance | Lluvia + suelo | Completo |
|---|---:|---:|---:|---:|---:|
| Rovelló | 0,1388 | 0,1210 | **0,0307** | 0,0462 | 0,0355 |
| Edulis | **0,3421** | 0,3534 | 0,3909 | 0,3625 | 0,4179 |
| Pinícola | **0,3674** | 0,4119 | 0,3997 | 0,3814 | 0,3758 |
| Aereus | 0,2432 | 0,2342 | 0,2441 | **0,1798** | 0,1950 |
| Ou de reig | **0,2261** | 0,2629 | 0,2417 | 0,2651 | 0,2698 |

En Rovelló, añadir balance a la lluvia produce la mejora grande y añadir las
siete columnas de suelo después empeora ligeramente el mejor resultado. En
Aereus ocurre otra cosa: el suelo aporta mucho y el balance añadido después
empeora. En Edulis y Ou de reig, esta representación V3 lineal no aprovecha bien
los bloques hídricos. Pinícola queda cerca del modelo sin bloque hídrico, pero
ninguna variante V3 de esta tabla es su ganador operativo.

### Por qué V6 cambia el alcance

El catálogo operativo selecciona por especie y día:

| Especie | Ganadores de los días 1--7 |
|---|---|
| Edulis | V3 los siete días |
| Aereus | V6 los siete días |
| Pinícola | V6 seis días; V2 un día |
| Ou de reig | combinación de V6, V4 y V3 |
| Rovelló | combinación de V3, V6, V2 y V5 |

El V3 `core` ganador de Edulis consume lluvia, temperatura y humedad, pero no
balance ni estado del suelo. V6 consume lluvia, temperatura y humedad diarias
suavizadas en ventanas de 30, 60 o 90 días, más siete resúmenes del estado del
suelo calentado con historia previa. No consume directamente la serie diaria de
balance climático ni la serie diaria de SMI.

Por eso la prueba multiespecie V3 es necesaria pero no suficiente para auditar el
Predictor que se ve en pantalla. La siguiente fase debe repetir retiradas
controladas dentro de cada familia realmente seleccionada: V3 para Edulis, V6
compartido para Aereus, V6 parcialmente compartido para Pinícola y la mezcla
V3/V4/V6 para Ou de reig. Comparar solo los resultados históricos de versiones
distintas no aislaría las variables, porque también cambia el algoritmo.

El efecto práctico de elegir otra familia ya puede cuantificarse sin atribuirlo
a una variable concreta:

| Especie | V3 lineal físico, Brier H1 | Ganador operativo H1 | Brier ganador |
|---|---:|---|---:|
| Rovelló | 0,0355 | V3 lineal físico | 0,0355 |
| Edulis | 0,4179 | V3 `core` HGB | 0,2441 |
| Pinícola | 0,3758 | V6 parcial 30 días | 0,2482 |
| Aereus | 0,1950 | V6 compartido 90 días | 0,1593 |
| Ou de reig | 0,2698 | V6 parcial 90 días | 0,1855 |

Así, V6 sí mejora claramente el error reservado de Pinícola, Aereus y Ou de
reig frente a este V3 lineal. Para no confundir esa ventaja con el efecto de una
variable, la siguiente sección repite las retiradas dentro de los modelos
realmente ganadores.

### Ablación de los ganadores reales V2--V6

La auditoría no se ha limitado a V6. Se reprodujeron y perturbaron copias de las
familias que el catálogo elige de verdad:

- Edulis: V3 `core` HGB;
- Aereus: V6 compartido, ventanas de 30, 60 y 90 días;
- Pinícola: V6 parcialmente compartido y V2 RF;
- Ou de reig: V6 parcialmente compartido, V4 LR/KNN y V3;
- Rovelló: V3, V6 parcialmente compartido, V2 LR/RF y V5 elastic-net.

En las tablas siguientes, un delta Brier positivo significa que retirar esa
información empeora el resultado; por tanto, el bloque aportaba señal útil. Se
mantiene siempre la partición externa oficial de 14 días.

#### V6 seleccionado

| Especie y tramo operativo | Brier base | Sin toda señal hídrica | Sin temperatura | Sin lluvia 15--21 d |
|---|---:|---:|---:|---:|
| Aereus, días 1--2, 90 d | 0,1591--0,1643 | +0,0520--+0,0543 | +0,0131--+0,0274 | +0,0337--+0,0415 |
| Aereus, días 3--5, 30 d | 0,1793--0,2112 | +0,0116--+0,0304 | de -0,0378 a -0,0147 | +0,0155--+0,0413 |
| Aereus, días 6--7, fijo 60 d | 0,1797 | +0,0341 | -0,0011 | +0,0056 |
| Pinícola, días 1--4, fijo 30 d | 0,2482 | +0,0042 | +0,0454 | +0,0164 |
| Pinícola, días 5--6, 60 d | 0,1903--0,1959 | +0,0211--+0,0298 | +0,0475--+0,0513 | +0,0248--+0,0301 |
| Ou de reig, día 1, 90 d | 0,1855 | +0,0152 | +0,0593 | +0,0420 |
| Ou de reig, días 4--5, 30 d | 0,1516--0,1694 | +0,0293--+0,0353 | +0,0387--+0,0464 | +0,0060--+0,0267 |
| Rovelló, días 2--3, 30 d | 0,0719--0,0748 | +0,0211--+0,0285 | +0,0448--+0,0584 | +0,0044--+0,0091 |

El resultado importante es consistente: **retirar conjuntamente lluvia y estado
del suelo empeora los ocho tramos V6 seleccionados**. No ocurre lo mismo al
retirar únicamente el resumen del suelo: aporta claramente en algunos tramos y
es redundante o perjudicial en otros. Por eso «el bloque hídrico sirve» y «este
SMI aislado es siempre bueno» no son la misma afirmación.

La lluvia de `15--21` días aporta en los ocho tramos. La de `0--3` días tiene
efecto pequeño y de signo mixto. Esto es exactamente el patrón que se buscaba:
la activación aparece aprendida como memoria meteorológica desplazada, no como
un umbral manual de 2 o 5 mm. La temperatura suele ser uno de los bloques más
fuertes, aunque no lo es en todos los tramos de Aereus.

La reproducción V6 no es bit a bit porque el snapshot histórico completo de
meteorología que produjo el lote ya no está disponible. Reconstruido con la
historia local actual, el error medio absoluto frente a las probabilidades
archivadas es `0,000045` y el máximo `0,0093`, concentrado en las observaciones
más recientes. Es una reproducción muy próxima y suficiente para esta
sensibilidad controlada, pero se conserva esta limitación.

La partición alternativa de 7 días confirma casi todo el patrón: retirar el
bloque hídrico empeora 13 de los 14 horizontes V6 seleccionados y retirar lluvia
`15--21` empeora también 13 de 14. Las dos excepciones son cambios minúsculos:
Ou-H1 sin bloque hídrico mejora `0,0003` y Rovelló-H2 sin lluvia `15--21` mejora
`0,0002`. No se ocultan, pero no contradicen el efecto principal observado en
la partición oficial de 14 días.

#### Edulis V3 `core`

El ganador de Edulis consume 15 variables de lluvia, temperatura y humedad. No
consume balance climático ni estado de suelo, de modo que retirarlos sería un
control nulo. La reproducción de las probabilidades archivadas es exacta a
`5e-11`.

| Variante, H1 | Brier | Cambio |
|---|---:|---:|
| Completo | 0,2441 | — |
| Sin lluvia | 0,2499 | +0,0058 |
| Sin temperatura | 0,2498 | +0,0058 |
| Sin humedad | 0,5322 | **+0,2881** |

En este ganador la humedad es la señal decisiva. La lluvia ayuda, pero poco; la
ventana inmediata `0--3` aporta (+0,0104 al retirarla), mientras `15--21` no es
utilizada por los árboles en este ajuste. Por tanto, el patrón `15--21` de V6 no
debe generalizarse a todos los algoritmos y especies. Con grupos de 7 días se
mantienen el aporte de lluvia y el dominio de la humedad; el signo de la
temperatura cambia, por lo que su pequeña contribución en Edulis no es estable.

#### Ganadores V2, V4 y V5

| Ganador real | Brier base | Sin lluvia | Sin temperatura | Lectura temporal principal |
|---|---:|---:|---:|---|
| Rovelló V2 LR, día 4 | 0,0727 | +0,2146 | +0,0342 | lluvia `15--21`: +0,1674 |
| Rovelló V2 RF, día 6 | 0,0982 | +0,0478 | -0,0385 | lluvia `15--21`: +0,0195 |
| Pinícola V2 RF, día 7 | 0,2354 | +0,0073 | +0,0545 | `8--21` aporta poco; `0--7` es redundante |
| Rovelló V5, día 5 | 0,0185 | +0,1055 | +0,1692 | lluvia `31--59`: +0,1056 |
| Rovelló V5, día 7 | 0,0649 | +0,0634 | +0,1284 | lluvia `31--59`: +0,0541 |

V2 y V5 se reproducen prácticamente bit a bit; la excepción es Pinícola-V2,
con diferencia máxima de probabilidad `0,0011`. V5 muestra una matización
importante: cuando el horizonte de predicción se alarga, la memoria útil puede
desplazarse hasta `31--59` días. «La información se concentra entre 15 y 30
días» es una buena descripción de Rovelló-H1 y de los V6 examinados, pero no una
ley universal para todos los horizontes. Los efectos principales de V2 y V5
mantienen signo con las particiones de 7 y 14 días; en Rovelló ambas particiones
dejan exactamente los mismos casos externos.

En Ou de reig, V4 también apunta en la misma dirección: quitar lluvia, balance,
temperatura o humedad empeora el Brier seleccionado, y la temperatura es el
bloque dominante. Sin embargo, la reproducción completa de sus probabilidades
no es suficientemente próxima —aunque el Brier del horizonte elegido sí
coincide—, por lo que ese resultado se clasifica como provisional y no se usa
para la conclusión fuerte.

#### Zonas

Hacer la prueba en todas las zonas no es una locura, pero muchas no permiten
medir acierto de forma fiable: suelen tener solo uno o dos episodios
independientes. Se calcularon resultados zonales cuando había ambas clases. Los
dos casos con una base mínimamente interpretable fueron:

- Aereus en Olvan, H1: quitar toda la señal hídrica empeora el Brier en
  `+0,0839`;
- Ou de reig en Olvan, H1: quitarla empeora en `+0,0337`.

En ambos, temperatura, lluvia y suelo aportan. Los resultados de Pinícola por
zona y de otras zonas de Ou/Rovelló/Edulis se conservan como sensibilidad, pero
con solo dos grupos no se presentan como evidencia de mejora. La auditoría real
por zona crecerá automáticamente en credibilidad al incorporar nuevos episodios
independientes; repetir filas del mismo episodio no resolvería el problema.

### Conclusión multiversión

1. El Predictor sí aprende una forma de «lluvia de activación»: usa lluvia
   antecedente y estado hídrico, sin copiar una cifra de Sporas.io ni aplicar un
   veto ecológico.
2. La lluvia inmediata no es el disparador general. En V6, `15--21` días es la
   ventana más estable; en V5 a horizontes largos aparece `31--59` días.
3. En la partición oficial de 14 días, la señal hídrica combinada mejora todos
   los tramos V6 realmente elegidos, además de los ganadores V2/V5 de Rovelló.
   El resumen de suelo aislado no mejora siempre: su utilidad depende de
   especie, horizonte y redundancia con lluvia/humedad.
4. La temperatura es normalmente un freno o predictor muy fuerte, pero Edulis
   depende sobre todo de humedad y hay excepciones en Aereus y Rovelló-V2 RF.
5. La interacción explícita «lluvia antecedente × estado previo del suelo» ya
   se probó y no mejora de manera estable. No hay evidencia para machacar
   V2--V6 ni para promover un V7.

### Prueba adicional ejecutada: lluvia × suelo antecedente

Se añadieron, sin umbrales manuales, productos entre la lluvia acumulada de
`15--21` y `22--30` días y el estado del suelo justo antes de cada intervalo.
En ventanas largas se probó además `31--59` días con el suelo del día 60. La
prueba conserva el mismo algoritmo, ajuste congelado y grupos externos; solo
añade columnas aprendibles. Brier positivo en la tabla significa empeorar.

| Familia y tramos realmente elegidos | Cambio Brier, grupos 14 d | Comprobación 7 d |
|---|---:|---:|
| Tramos V6 seleccionados de Aereus | de +0,0129 a +0,0421 | todos empeoran |
| Tramos V6 seleccionados de Pinícola | de +0,0162 a +0,0400 | todos empeoran |
| Ou de reig V6, H1/H4/H5 | +0,0025 / -0,0057 / -0,0001 | los tres empeoran |
| Rovelló V6, H2/H3 | +0,0018 / +0,0072 | ambos mejoran |
| Rovelló V5, interacción `15--30`, todos los horizontes | -0,0006 | mismo resultado |
| Rovelló V5, añade `31--59`, todos los horizontes | **+0,0379** | mismo resultado |

Los cortes de 7 y 14 días de Rovelló-V5 contienen exactamente las mismas filas,
por lo que su coincidencia no es una segunda confirmación. En V6, Aereus y
Pinícola dan un rechazo estable; Ou de reig y Rovelló cambian de signo según la
agrupación. En Rovelló-V5, la mejora de `15--30` es diminuta y añadir la
interacción larga empeora claramente, aunque la lluvia `31--59` por sí sola sí
aportaba en la ablación. Una variable útil por separado no implica que su
producto con el suelo sea útil.

Edulis no tiene una intervención directa equivalente: su ganador operativo V3
`core` no consume estado del suelo. En las configuraciones V6 exploratorias, la
interacción queda prácticamente neutra en promedio y tampoco ofrece una mejora
estable que justifique cambiar de familia.

La calibración tampoco mejora de forma consistente. En conjunto, la prueba
responde la pregunta científica pero no descubre un candidato superior. Elegir
ahora una variante por el mejor caso aislado reutilizaría el hold-out para
seleccionar modelo. La comparación se repetirá cuando entren nuevas
observaciones independientes; no requiere conservar cada precálculo diario.

`MOD_0001` continuó intacto: la ecología se puede mostrar como diagnóstico, pero
nunca veta ni corrige la salida aprendida.

## Auditoría del veto de aplicabilidad por lluvia

Se reconstruyó el soporte de entrenamiento después de retirar exactamente los
grupos externos y se aplicó el control de rango a los 25 candidatos distintos
elegidos por especie para Rovelló, Edulis, Pinícola, Aereus y Ou de reig. No se
reentrenó ningún modelo. La unidad es una predicción candidato--observación;
los 599 casos del corte oficial proceden de 54 grupos independientes.

| Regla | Cobertura 14 d | Brier aceptados | Casos recuperados | Comprobación 7 d |
|---|---:|---:|---:|---:|
| Actual: mínimo/máximo y desviación en mm | 82,8 % | 0,1708 | — | 81,4 % |
| Cola de lluvia transformada con `log1p` | 84,8 % | 0,1735 | 12 | 82,4 % |
| La lluvia avisa, pero no veta por sí sola | **92,0 %** | 0,1721 | **55** | **91,6 %** |

La regla actual rechazó 103 casos, pero su Brier fue `0,1572`, mejor que el
`0,1708` de los casos que dejó pasar. Por tanto, en este hold-out el veto no
está separando predicciones estadísticamente peores. También descartó 45 casos
positivos y 58 negativos: no actúa simplemente como protección ante falsas
alarmas.

La transformación logarítmica no queda validada: solo recupera 12 casos y su
Brier en esos casos es `0,2843` en el corte oficial, aunque en el corte de 7
días baja a `0,1522`. Ese cambio de comportamiento entre particiones impide
recomendarla.

La alternativa más clara es tratar cualquier lluvia fuera del rango observado
como **advertencia de extrapolación**, no como motivo suficiente de abstención.
Recupera 55 casos en 14 días —30 positivos y 25 negativos— con Brier `0,1839`,
y 48 en 7 días con Brier `0,1745`. La pérdida media frente a los casos ya
aceptados es pequeña y estable, mientras la cobertura sube unos nueve o diez
puntos. Las desviaciones de temperatura, humedad, suelo u otras variables
conservarían la regla actual y podrían seguir causando abstención.

Esta política quedó implementada y validada en el Predictor el 5 de septiembre.
La lluvia sigue visible en el diagnóstico, pero ya no veta por sí sola. Las 40
pruebas dirigidas del runtime, selector y runners de auditoría pasaron; también
pasó la suite completa de 1.279 pruebas. En la reproducción directa de
Rovelló/La Masella del 8 de septiembre, los `32,143784` mm de
`rain_mm__lag_028` quedaron como advertencia y el candidato V5w fue aceptado con
`99,8511 %`. La pequeña desviación simultánea de `soil_water_change_14d`
(`2,521` desviaciones estándar) no alcanzó por sí misma el umbral de veto.

## Auditoría de probabilidades extremas

Se expandieron las probabilidades archivadas de cada estimador y se cruzaron
con el catálogo sellado de selección. Para reflejar la pantalla real también se
reconstruyeron los contextos especie--área--día; un modelo de ventana fija que
gana en varios días se cuenta una vez por cada contexto operativo, por lo que
los recuentos no deben confundirse con observaciones independientes.

| Contextos operativos | Corte oficial 14 d | Corte de estabilidad 7 d |
|---|---:|---:|
| Predicciones / grupos | 910 / 54 | 728 / 59 |
| Probabilidad `>= 99 %` | 58; acierto 94,8 % | 40; acierto 100 % |
| Probabilidad exactamente `100 %` | 14; acierto 85,7 % | 6; acierto 100 % |
| Probabilidad exactamente `0 %` | 3; acierto 100 % | 6; acierto 100 % |
| Brier global | 0,1700 | 0,1699 |

El `100 %` exacto no puede interpretarse como certeza: en el corte oficial hay
dos negativos entre 14 salidas exactas de `1,0`. Ambos errores pertenecen al
KNN de V4 para Ou de reig, día 3, en Breda y Llambilles. El tercero de los tres
errores por encima de `99 %` es la regresión logística V4 en Olvan (`99,65 %`).
Los ceros exactos acertaron, pero solo hay tres casos oficiales y seis en la
partición alternativa: son demasiado pocos para validar certeza negativa.

El problema no afecta igual a todas las familias. V5 produjo 16 casos por
encima de `99 %` y todos fueron positivos en ambos cortes, sin emitir ceros o
unos exactos. V6 no emitió ningún valor `>= 99 %` ni un extremo exacto en estos
hold-outs operativos. Los extremos exactos proceden del KNN de siete vecinos
ponderados por distancia, que puede devolver `0` o `1` cuando todos los vecinos
efectivos pertenecen a la misma clase.

Excluir KNN sin más tampoco queda justificado. Al retirarlo y repetir el mismo
selector, el ganador global de Ou de reig para el día 3 pasa a V6 compartido,
pero empeora el Brier de `0,1628` a `0,1836` y reduce el acierto de las
recomendaciones favorables de `10/14` a `8/12`. La calibración mejora muy poco
(`0,1688` a `0,1624`). La conclusión cerrada es más concreta:

1. V2--V6 no presentan un problema general de saturación.
2. Los `100 %` exactos del KNN no son probabilidades calibradas y no deben
   leerse como certeza, aunque el KNN conserve utilidad para ordenar casos.
3. No se debe eliminar KNN ni recortar todas las probabilidades de forma
   cosmética. La siguiente comparación, si se autoriza un cambio de modelo,
   debe calibrar fuera de muestra la salida de KNN y enfrentarla al KNN actual
   y al sustituto V6 con los mismos grupos.

Ninguna de estas pruebas utilizó Sporas.io como etiqueta ni permitió que la
ecología vetara o corrigiera la predicción; `MOD_0001` sigue intacto.

## Artefactos reproducibles

- runner: `scripts/audit-mushroom-hydric-ablation.py`;
- funciones auditables: `rainmapper_core/mushroom_ml_hydric_ablation.py`;
- prueba dirigida: `tests/test_mushroom_ml_hydric_ablation.py`;
- resultado completo no operativo:
  `docker-data/audits/mushroom-hydric-ablation-20260905/results/lactarius-v3-lag-logistic.json`;
- resultados equivalentes de la primera comparación común:
  `edulis-v3-lag-logistic.json`, `pinicola-v3-lag-logistic.json`,
  `aereus-v3-lag-logistic.json` y `ou-de-reig-v3-lag-logistic.json`, en el mismo
  directorio de auditoría;
- ablación V6 de ventanas 30/60/90 y perfiles compartido/parcial:
  `v6-controlled-ablation-all.json`;
- Edulis V3 `core`: `edulis-v3-core-hgb-fixed-ablation.json`;
- ganadores restantes: `v2-selected-winners-ablation.json`,
  `rovello-v5-raw60-ablation.json` y
  `ou-de-reig-v4-climatic-balance-ablation.json`;
- prueba adicional: `v6-hydric-interaction-challenger.json` y
  `rovello-v5-hydric-interaction-challenger.json`;
- aplicabilidad de lluvia: `scripts/audit-mushroom-rain-applicability.py` y
  `docker-data/audits/mushroom-rain-applicability-20260905/results/rain-applicability-gates.json`;
- extremos y calibración: `scripts/audit-mushroom-probability-extremes.py` y
  `docker-data/audits/mushroom-probability-extremes-20260905/results/extreme-probability-calibration.json`;
- especies aplazadas: `deferred-species-evidence.json`;
- inventario de pruebas pendientes y runners:
  `docs/reports/mushroom-predictor-p0-pending-tests-and-python-audit-battery-2026-09-05.md`;
- fuente de preguntas sobre Sporas:
  `docs/mushrooms/literature/sporas_especies_informe_rainmapper.md`, en especial
  su apartado 8.1. No se utilizó como verdad de entrenamiento ni evaluación.
