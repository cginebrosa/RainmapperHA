# Método del estudio de umbrales y marco original

Estado: primera comparación de umbrales completada; [resultados](resultados-2026-10-03.md).
El marco general original incluía otras variantes que no se ejecutaron aquí.
Cortes y criterios efectivos en el
[protocolo de ejecución](protocolo-ejecucion-2026-10-03.md). Inventario preliminar en
[el informe del 03/10/2026](inventario-inicial-2026-10-03.md).
Alcance y autorización en [README](README.md); secuencia de trabajo en
[plan-de-trabajo](plan-de-trabajo.md).

## 1. Fijar qué significa acertar

Separar tres elementos: resultado observado de la salida, salida numérica del
modelo y recomendación final del mapa. Un IFF no es un porcentaje de acierto.
Cambiar el umbral de recomendación no equivale a cambiar el modelo ganador.

La [definición documentada de observaciones](../../mushrooms/mushroom-observations-schema-es.md),
líneas 244–278 en la revisión inicial, considera favorable desde `scarce` hasta
`exceptional`, y desfavorable `very_scarce` o `absent`. El objetivo es una salida
mínimamente interesante, no presencia de cualquier ejemplar. Antes de evaluar,
comprobar que el catálogo importado y los artefactos aplican esa misma definición.

Revisar especialmente artefactos antiguos: [mushroom_observation_features.py](../../../rainmapper_core/mushroom_observation_features.py),
líneas 223–236, contiene compatibilidad que recurre a `analysis_result` cuando
falta un objetivo conocido. No mezclar silenciosamente objetivos de presencia y
de salida favorable. Cualquier definición alternativa será otro experimento,
identificado antes de mirar sus resultados; no una modificación de los originales.

Una ausencia de registro, una visita no realizada o una especie no mencionada
**no constituyen un negativo**. Usar negativos explícitos y suficientemente
documentados para esa especie, fecha y zona; registrar la incertidumbre del
resultado observado. Una colección con sólo resultados favorables no permite
evaluar el comportamiento ante salidas realmente desfavorables.

**Aclaración del usuario del 03/10/2026:** los registros GBIF etiquetados `normal`
son favorables con el mismo criterio que los demás `normal`. En esta investigación
no se excluyen, penalizan ni someten a una validación adicional por ser GBIF.
Su origen se conserva como metadato de procedencia; esta clasificación está resuelta.

## 2. Inventario y unidad de evaluación

Crear un manifiesto local de los datos aportados, con fecha de extracción,
versiones, huellas, procedencia y disponibilidad temporal. Incluir observaciones,
setales, meteorología, contratos de variables, catálogo de etiquetas, modelos,
catálogos de calidad y configuración de selección y recomendaciones. Conservar
originales; un manifiesto y referencias bastan cuando no hace falta otra copia.

Por especie, contar positivos, negativos, resultados desconocidos, setales,
campañas, visitas y episodios de florada independientes. Detectar duplicados,
visitas próximas correlacionadas, cambios de etiqueta y meteorología incompleta.
Muchas filas del mismo episodio no equivalen a muchas oportunidades independientes.
Separar dos inventarios: histórico reutilizable para nuevos experimentos y casos
no utilizados por el modelo instalado ni por su selección. No descartar todo el
histórico porque participó en producción ni asumir que los pocos casos nuevos
bastan para una evaluación fiable. Medir positivos y negativos independientes
en cada vía; el número de particiones no aumenta ese soporte.

La unidad de contraste será una observación o salida verificable, con su especie,
ubicación, fecha objetivo, fecha de emisión y horizonte. Vincular las filas de
los distintos horizontes a esa misma unidad. Registrar el contexto conocido al
emitir, sin introducir datos observados al terminar la salida como predictores.

Auditar si cada caso participó en entrenamiento, calibración, selección de
variables/modelos, catálogo de calidad o ajuste de reglas. El índice de
[mushroom_training_observations.py](../../../rainmapper_core/mushroom_training_observations.py),
`lookup`, desde la línea 87, puede ayudar, pero `not_used` no demuestra por sí
solo independencia de todo el procedimiento. `legacy` o `unavailable` tampoco
demuestran exclusión. Conservar como desconocido lo que no se pueda reconstruir.

## 3. Dos análisis con conclusiones distintas

**Auditoría descriptiva del sistema instalado.** Reproducir en local su selección
y registrar familias consideradas, posición histórica, descartes, cobertura de
siete días, ganador, salida numérica, recomendación y motivo final. Medir cuántas
veces gana cada familia y en qué contextos. Puede incluir casos de entrenamiento,
pero debe declararlo: sirve para explicar el mecanismo, no para acreditar precisión
fuera de muestra.

**Evaluación predictiva.** Distinguir dos preguntas y registrar cuál responde cada
resultado:

- Para evaluar el artefacto instalado, usar casos ajenos tanto a su ajuste como a
  las decisiones que lo seleccionaron. Tras el ajuste productivo con todos los
  datos elegibles, el antiguo 30 % no constituye una reserva independiente de ese
  artefacto. La evaluación previa describe los modelos utilizados en aquella prueba;
  volver a puntuar el modelo final sobre sus datos es evaluación dentro de muestra.
- Para comparar procedimientos, construir modelos experimentales nuevos con
  particiones del histórico. Entrenar con episodios anteriores y probar con otros
  posteriores, manteniendo los relacionados juntos. Que producción haya utilizado
  esos casos no impide este experimento, siempre que el modelo experimental y todas
  sus decisiones de ajuste y selección excluyan sus casos de prueba. Se estima el
  rendimiento del procedimiento, no el del artefacto productivo exacto.

En la segunda vía, reconstruir también el catálogo/ranking, la calibración y los
umbrales dentro de cada partición de desarrollo. Los catálogos existentes sirven
para describir el sistema instalado; no reutilizarlos como selectores independientes
si se construyeron con resultados reservados para la prueba experimental.

Declarar cuánto influyó ya el histórico en las variables, familias y reglas que
queremos comparar. Volver a partirlo no elimina ese conocimiento previo. Una
evaluación separada de los ajustes puede aportar evidencia retrospectiva, pero no
debe presentarse como confirmación completamente nueva si el diseño ya se adaptó
a esos resultados. En ese caso la candidata será provisional y la confirmación
requerirá datos no utilizados en su diseño, preferentemente seguimiento prospectivo.

## 4. Separación temporal y por episodios

Reservar entrenamiento, desarrollo/validación y, cuando exista soporte y procedencia
adecuados, una prueba final intacta respecto al estudio. No llamar «intacta» a una
partición por haberle asignado un nombre nuevo si sus resultados ya orientaron las
reglas comparadas. Si no se puede reservar esa prueba, limitar la conclusión a
evidencia exploratoria y planificar la confirmación futura. Entrenar
con el pasado y evaluar periodos posteriores, agrupando visitas del mismo episodio
y evitando que ventanas temporales solapadas o floradas relacionadas crucen cortes.
Definir el agrupamiento y la separación necesaria según los contratos y datos,
antes de comparar resultados. Mantener juntos todos los horizontes de un caso y,
cuando compartan entrenamiento o información, especies observadas en la misma salida.

La infraestructura existente contiene particiones por florada de 14 días y
evaluación agrupada: [mushroom_ml_reliability_audit.py](../../../rainmapper_core/mushroom_ml_reliability_audit.py),
constante del split oficial, línea 28; [mushroom_ml_biology_v3_evaluation.py](../../../rainmapper_core/mushroom_ml_biology_v3_evaluation.py),
`chronological_group_split`, desde 85. Se revisará su idoneidad; su existencia no
demuestra que cualquier conjunto nuevo quede libre de dependencia.

Si hay suficientes episodios, utilizar ventanas cronológicas sucesivas con ajuste
interno y evaluación externa. Dentro de cada partición, ajustar exclusivamente
con entrenamiento/desarrollo la imputación, escalado, variables, modelos,
calibración, umbrales, catálogo y selector. Evaluar fuera **todo el procedimiento**,
sin elegir después el mejor candidato de cada caso conociendo su resultado.

El soporte existente en [mushroom_ml_holdout.py](../../../rainmapper_core/mushroom_ml_holdout.py),
`_preprocess`, `_inner_splits` y `evaluate_dataset`, es un punto de partida para
reutilizar tras comprobar los contratos, no una validación ya ejecutada del estudio.

Evaluar aparte el futuro de setales conocidos y la transferencia a setales no
vistos, cuando la muestra permita ambas preguntas. Ninguna de las dos acredita
automáticamente rendimiento en cualquier punto del mapa.

Para cada fecha de emisión, respetar su corte de información. La auditoría del
mapa actual comprobó que las familias lag usan histórico hasta emisión − 1; no
necesitan previsiones meteorológicas archivadas ni valores futuros para reproducir
sus entradas. El histórico descargado puede incluir revisiones posteriores y no
acredita cuándo estuvo disponible cada dato. Etiquetar el ejercicio como
reconstrucción retrospectiva del procedimiento actual; la evaluación prospectiva
deberá contrastar esa limitación. Si otra variante incorpora previsiones, entonces
sí necesitará los archivos emitidos o declarar la sustitución por observados.

## 5. Matriz inicial pequeña y controlada

Comparar sobre los mismos casos, horizontes y entradas; registrar identidad de
los artefactos, semillas y configuración. La referencia A será el procedimiento
actual completo, incluidos sus filtros y recomendaciones, reproducido sin fuga
de información cuando se use como referencia predictiva. En la comparación
retrospectiva, A también tendrá modelos y ranking ajustados dentro de cada
partición; no será el artefacto instalado entrenado con todo el histórico.

| Variante propuesta | Cambio aislado | Pregunta |
| --- | --- | --- |
| A. Referencia | Ninguno | ¿Cuál es el rendimiento y la cobertura de partida? |
| B. Umbral | Umbral de recomendación, conservando selección y filtros | ¿Se reducen fallos favorables sin cambiar de modelo? |
| C. Ranking | Criterio histórico orientado al coste y utilidad acordados | ¿Mejora elegir la familia por otro equilibrio de errores? |
| D. Semana | Prioridad entre cobertura semanal y calidad | ¿Cuánto cuesta preferir cobertura completa? |
| E. Día | Selección diaria frente a una familia semanal | ¿La adaptación diaria aporta una mejora estable? |

Mantener los filtros de validez, suspensiones y límites de aplicabilidad. No
rescatar modelos inválidos para aumentar cobertura. Si una variante implica
abstenerse más, contabilizarlo como parte de su resultado.

Probar primero cambios aislados; combinar después sólo los prometedores en
desarrollo, con un límite de variantes fijado de antemano. Un selector por contexto
o un conjunto de modelos sería una segunda etapa, justificada por evidencia y
muestra suficientes. Más complejidad no es un objetivo del estudio.

Reutilizar inferencias compatibles para comparar reglas baratas. No ejecutar todas
las familias sobre toda la geografía: limitarse a la cohorte y periodos definidos.
Reentrenar sólo cuando sea necesario para la independencia o el experimento y
esté dentro del alcance de ejecución autorizado.

## 6. Métricas y equilibrio de errores

Reportar una tabla de resultado observado (favorable/desfavorable) frente a
decisión (favorable/desfavorable/sin recomendación). Desglosar incertidumbre,
abstención, datos ausentes y fallo técnico; ninguno cuenta como acierto.

Para métricas binarias, fijar antes cómo se traducen las categorías reales de la
interfaz a esas tres decisiones. No reclasificar una recomendación dudosa después
de conocer el resultado. Evaluar tanto salida del modelo como consejo final.

Denotar TP = favorable acertado, FP = favorable fallido, FN = desfavorable cuando
la salida fue favorable, TN = desfavorable acertado, AP/AN = sin recomendación con
resultado observado favorable/desfavorable. N suma las seis celdas; los resultados
observados desconocidos se cuentan aparte y no se convierten en negativos.

| Medida | Cálculo o presentación |
| --- | --- |
| Riesgo de una recomendación favorable | FP / (TP + FP), junto con ambos recuentos. |
| Precisión favorable | TP / (TP + FP). Es el complemento del riesgo anterior. |
| Oportunidades favorables detectadas | TP / (TP + FN + AP); oportunidades perdidas = FN + AP. |
| Cobertura de decisiones | (TP + FP + FN + TN) / N. |
| Frecuencia de recomendaciones favorables | (TP + FP) / N. |
| Soporte | Casos, visitas/episodios independientes, setales y campañas por especie/horizonte. |

Un denominador cero produce una métrica **no estimable**, nunca un 100 % de
precisión o un 0 % de fallos favorable. Presentar también la matriz completa:
una única exactitud global puede ocultar que siempre se recomienda desfavorable.

En desarrollo, mostrar curvas o tablas de riesgo frente a oportunidades detectadas
y cobertura. Comparar costes con penalización FP mayor que FN, sin inventar una
proporción definitiva. Si se optimiza un coste único, fijar también el tratamiento
de la abstención y los mínimos de utilidad para impedir que desaparecer de los
casos difíciles parezca una mejora gratuita.

Antes de abrir la prueba final, acordar el equilibrio y fijar mínimos de
oportunidades detectadas, cobertura y soporte, más una mejora práctica relevante.
Incluir controles de «siempre desfavorable» y «siempre abstenerse», además de una
referencia simple útil elegida en desarrollo. No aceptar una variante que sólo
reduzca fallos porque deja de recomendar.

Evaluar calibración y Brier como medidas secundarias cuando la salida sea una
probabilidad del mismo objetivo binario. Brier no mide sólo calibración. No
interpretar IFF como probabilidad de encontrar setas ni cambiar etiquetas para
que una curva resulte mejor.

Presentar comparación pareada en casos comunes y resultado completo de cada
procedimiento, incluyendo sus exclusiones y fallos de cobertura. La intersección
de casos disponibles no debe ocultar dónde uno deja de funcionar.

## 7. Incertidumbre, selección final y seguimiento

Estimar incertidumbre respetando episodios correlacionados, con intervalos o
remuestreo pareado por grupos cuando el soporte lo permita. No tratar siete
horizontes de una visita como siete pruebas independientes. El promedio de límites
inferiores de Wilson entre horizontes es un criterio de ranking del código actual,
**no un límite de confianza del 95 % para el resultado semanal agregado**.

Mostrar números absolutos y sensibilidad por especie, periodo y setal. Con pocas
salidas negativas o pocos episodios, declarar la incertidumbre y la posible
insuficiencia del estudio. No fijar una cifra universal de observaciones suficientes
sin conocer la frecuencia de eventos y la mejora que se pretende detectar.
Repetir particiones o remuestrear ayuda a describir variabilidad, pero no sustituye
salidas independientes adicionales. Pocos episodios o pocos negativos pueden
impedir una conclusión operativa aunque las métricas puntuales parezcan buenas.

Cerrar reglas y configuración antes de evaluar la prueba final una sola vez.
Si se ajustan tras verla, pasa a ser desarrollo y hará falta otra prueba
independiente. Ante resultados similares, preferir la solución más simple y barata.

Completar con seguimiento prospectivo: guardar predicciones, versión, meteorología
disponible y reglas **antes** de conocer cada salida; registrar también visitas
desfavorables y las realizadas pese a una predicción desfavorable. Los puntos no
visitados carecen de resultado. Las visitas seleccionadas por el propio mapa pueden
sesgar la muestra: declarar esa limitación y no extrapolar a toda la geografía.

## Fundamento metodológico

La separación entre ajuste de umbral y evaluación sigue el ejemplo oficial de
[decisiones con costes asimétricos de scikit-learn](https://scikit-learn.org/stable/auto_examples/model_selection/plot_cost_sensitive_learning.html).
Las particiones temporales y agrupadas se apoyan en su
[documentación de validación cruzada](https://scikit-learn.org/stable/modules/cross_validation.html).
Evaluar también la selección del procedimiento evita el optimismo descrito por
[Cawley y Talbot, 2010](https://www.jmlr.org/papers/v11/cawley10a.html).
Estas fuentes sustentan el método; no acreditan resultados de Rainmapper.
