# Investigación del umbral de recomendación favorable

**Primera comparación local completada el 03/10/2026.**
[Resultado y conclusión](resultados-2026-10-03.md): no se respalda activar el
umbral conservador ensayado. [Tablas](tablas-2026-10-03.md) y
[reproducción](reproducibilidad.md). El encargo y sus límites están en
[goal.md](goal.md); su cierre en [estado.md](estado.md). No se han promovido modelos
ni realizado trabajos operativos.

Esta carpeta se llamaba `docs/agents/prediction/`. El 03/10/2026 se renombró a
`prediction-thresholds/` para identificar el contraste realmente ejecutado:
umbral conservador frente al mismo selector. El método general conserva preguntas
más amplias del planteamiento original; no significa que se hayan probado todas.
La selección del ganador tiene ahora su [propio encargo](../prediction-model-selection/README.md).

Los scripts y resultados privados mantienen `scripts/prediction_research/` y
`tmp/prediction-research/`. El recibo de cierre conserva las rutas y hashes del
momento del estudio; la documentación previa al cambio de nombre se preservó en
`tmp/prediction-research/documentation-before-rename-20261003/`, con su mapa de
reubicación. El cambio documental no repite ni altera los resultados científicos.

## Objetivo

Determinar qué procedimiento de selección de modelos y emisión de recomendaciones
ofrece resultados más útiles para **Boletus aereus** y **Amanita caesarea** en el
mapa de predicciones. Para comparar procedimientos se podrán entrenar modelos
experimentales desde cero con partes del histórico, evaluándolos sobre episodios
excluidos tanto de su ajuste como de la elección de modelos, ranking y umbrales.
La investigación no queda limitada a las observaciones nuevas desde el último
entrenamiento productivo; su suficiencia deberá determinarse en el inventario.

La preferencia del usuario es explícita: **penalizar más una recomendación
favorable que termina en una salida desfavorable que el error contrario**, sin
acabar recomendando siempre desfavorable. Buscaremos un equilibrio medible entre
fiabilidad de las recomendaciones favorables y oportunidades favorables detectadas.
El usuario no ha fijado una proporción numérica entre ambos costes. El
[protocolo de ejecución](protocolo-ejecucion-2026-10-03.md) fija mínimos de utilidad
como supuestos técnicos explícitos, antes de examinar la prueba externa.

El resultado puede ser mantener el sistema actual, proponer un cambio acotado o
concluir que faltan datos. No se presupone que alternar más de modelo mejore las
predicciones ni que un selector contextual sea necesario.

## Qué significa independencia en este estudio

El código revisado distingue evaluación y ajuste productivo: el entrenamiento base
evalúa con un corte temporal 70/30 y después ajusta modelos nuevos con todos los
episodios elegibles. La ruta multiversión también ajusta los artefactos operativos
con todas las muestras elegibles de su ámbito. Las fuentes están en la tabla técnica.
Ese ajuste no garantiza por sí mismo una mejora ni borra la evaluación anterior;
**el antiguo 30 % deja de ser independiente del modelo productivo final**.

- **Evaluar el modelo instalado:** requiere casos que no hayan intervenido en su
  ajuste ni en su selección. El inventario encontró un ID por especie ausente de
  todos los modelos pertinentes del lote local, ambos favorables; todavía no se
  acredita su independencia respecto a selección y diseño.
- **Comparar procedimientos experimentales:** permite reutilizar el histórico con
  nuevos ajustes y particiones temporales por episodios. Cada prueba debe quedar
  fuera de toda decisión de ajuste y selección del procedimiento evaluado.

La independencia se exige respecto al experimento evaluado. Haber usado un caso
en producción no lo inutiliza para esa comparación retrospectiva, pero reutilizar
un modelo o ranking que ya lo conoce contaminaría la prueba. El conocimiento previo
del histórico también puede sesgar el diseño del estudio: debe declararse y
contrastarse con futuras salidas. **Repetir particiones no crea más episodios
independientes.** Con poco soporte, el resultado podrá ser una candidata provisional
pendiente de confirmación o evidencia insuficiente, sin conclusión operativa fiable.

## Documentos y orden de lectura

1. Este documento: alcance, referencia de partida y preguntas.
2. [Método](metodo.md): etiquetas, independencia, experimentos y criterios de evaluación.
3. [Plan de trabajo](plan-de-trabajo.md): fases, entregables, límites del futuro agente
   y condiciones para terminar o detener la investigación.
4. [Inventario preliminar del 03/10/2026](inventario-inicial-2026-10-03.md): recuentos,
   solapamiento con entrenamiento local y límites de la evidencia disponible.
5. [Goal y reglas autorizadas](goal.md) y [estado de ejecución](estado.md).
6. [Protocolo cerrado de ejecución](protocolo-ejecucion-2026-10-03.md): cortes,
   reproducción semanal, selección del umbral y soporte mínimo antes de calcular.
7. [Resultados](resultados-2026-10-03.md), [tablas completas](tablas-2026-10-03.md)
   y [reproducibilidad](reproducibilidad.md).
8. [Ejemplo de lanzamiento](ejemplo-lanzamiento.md): mensaje con el encargo y las
   instrucciones del agente, conservado como referencia del estudio completado.

Esta carpeta es el protocolo de la investigación. No sustituye la
[especificación del mapa](../../mushrooms/prediction-map-specification-es.md) ni
modifica las decisiones operativas del proyecto.

## Alcance y límites

- El usuario confirmó la descarga a local de observaciones, setales y meteorología.
  Se verificaron los archivos montados por HA local; no se consultó HA real para
  comprobar paridad. La suficiencia y sus límites se valoran en el informe final.
- El estudio se hará en el entorno local, con originales conservados y artefactos
  experimentales separados de los activos. Se reutilizarán datos geográficos
  compatibles existentes, sin duplicarlos indiscriminadamente.
- Se evaluarán por separado ambas especies y los horizontes de predicción. No
  se mezclarán poblaciones para declarar un ganador común.
- El goal autoriza los ajustes experimentales aislados de su primera comparación.
  No acceder a HA real, cambiar coordinadores del worker, relanzar entrenamientos
  operativos o precálculos, desplegar, limpiar ni promover modelos. Los trabajos
  operativos siguen a cargo del usuario.
- Observaciones, ubicaciones precisas, identificadores privados y predicciones
  por caso permanecerán en almacenamiento local privado. El repositorio sólo
  recibirá protocolo, código autorizado y resultados agregados revisados.

## Referencia técnica inspeccionada

La lectura corresponde al código local el **03/10/2026**, con HEAD
`c28a514bfee42f70e0bd262baf162e5a5f566849`. Es una referencia para diseñar el estudio,
no una verificación de los contenedores o artefactos que ejecute HA al iniciarlo.
Las líneas siguientes son orientativas para esa revisión; revalidar los símbolos
y sus contratos cuando comience la investigación.

| Hallazgo en el código | Fuente local |
| --- | --- |
| El entrenamiento base fija un 70 % temporal para entrenamiento de evaluación y hace después un ajuste productivo nuevo con todos los episodios elegibles. | [mushroom_ml_trainer.py](../../../rainmapper_core/mushroom_ml_trainer.py), `TRAIN_RATIO`, línea 85; `_temporal_split`, desde 226; `train_species`, ajuste final desde 402. |
| El entrenamiento multiversión prepara todas las muestras elegibles del ámbito para ajustar el artefacto operativo. La partición agrupada de evaluación usa por defecto el 70 % de grupos, no necesariamente el 70 % exacto de filas. | [mushroom_ml_runtime_trainer.py](../../../rainmapper_core/mushroom_ml_runtime_trainer.py), `fit_artifact`, desde 411, y `_prepare_fit_inputs`, desde 484; [mushroom_ml_biology_v3_evaluation.py](../../../rainmapper_core/mushroom_ml_biology_v3_evaluation.py), `chronological_group_split`, desde 85. |
| El catálogo produce cadenas históricas de candidatos por especie y horizonte; el runtime del mapa carga las selecciones de especie. | [mushroom_ml_reliability_audit.py](../../../rainmapper_core/mushroom_ml_reliability_audit.py), `build_selection_catalog`, líneas 844–890; [mushroom_map_model_runtime.py](../../../rainmapper_core/mushroom_map_model_runtime.py), `_refresh`, desde 203. |
| Para la semana se ordenan familias comunes por evidencia agregada. Primero pesa el límite inferior de Wilson de la precisión favorable, después precisión, número de favorables, recall y otros desempates. | [mushroom_predictor_precompute.py](../../../rainmapper_core/mushroom_predictor_precompute.py), `_weekly_family_aggregate`, `_weekly_family_rank`, `weekly_aggregate_resolution_index`, desde 577. |
| En el punto se calculan entradas e inferencias propias. La ruta del mapa usa evaluación diferida: recorre familias en ese orden y puede parar cuando una cubre los siete días. No calcula necesariamente todos los modelos para elegir el de mayor probabilidad. | [mushroom_map_model_runtime.py](../../../rainmapper_core/mushroom_map_model_runtime.py), `predict`, líneas 250–300; [mushroom_map_prediction.py](../../../rainmapper_core/mushroom_map_prediction.py), `resolve_species_week`, líneas 62–86. |
| La priorización semanal considera primero cobertura operativa y después posición histórica; existen fallback diario y abstención. Los filtros incluyen disponibilidad, suspensión, aplicabilidad y evidencia mínima. | [mushroom_ml_multiversion_comparison.py](../../../rainmapper_core/mushroom_ml_multiversion_comparison.py), `_operational_gate_failures`, desde 504; `prioritize_weekly_resolutions_by_applicability`, desde 606. |
| La política de recomendación puede contrastar alternativas y modificar la recomendación conservando el ganador y su IFF. Selección de modelo y consejo mostrado son decisiones distintas. | [mushroom_map_prediction.py](../../../rainmapper_core/mushroom_map_prediction.py), líneas 91–107; [mushroom_recommendation_policy.py](../../../rainmapper_core/mushroom_recommendation_policy.py), `apply`, desde 86. |

**Interpretación que se someterá a prueba:** ese diseño puede explicar que se
repita la misma familia para una especie cuando sigue siendo aplicable. Todavía
no se ha medido su frecuencia con los datos del estudio, ni demostrado que esa
repetición sea un defecto. Tampoco el ranking histórico demuestra por sí solo
que el candidato sea el más acertado en cada ubicación.

## Preguntas que deberá responder el estudio

1. ¿Qué familias se eligen realmente por especie, punto y semana, y qué motivos
   explican los cambios, descartes y abstenciones?
2. ¿Cuántas recomendaciones favorables fracasan y cuántas salidas favorables se
   pierden, contando también incertidumbre, abstenciones y falta de cobertura?
3. ¿Basta ajustar el umbral o la política de recomendación, conservando el modelo?
4. ¿Mejora algo cambiar el ranking o la prioridad de cobertura semanal frente a
   calidad, manteniendo los filtros de validez?
5. ¿Hay evidencia suficiente para seleccionar por contexto o por día, en lugar de
   mantener una familia semanal? ¿Se sostiene la mejora fuera de los casos usados
   para desarrollar la regla?

## Condición de éxito

Obtener una comparación reproducible del procedimiento completo, con recuentos,
incertidumbre y trazabilidad, que respete la preferencia del usuario y conserve
utilidad práctica. Una propuesta sólo será candidata a implementación si supera
los criterios fijados antes de la prueba final y la evidencia admite esa conclusión.
Una comparación exploratoria sólo permite proponer una candidata provisional,
pendiente de confirmación. **Documentar insuficiencia de evidencia también es un
cierre válido; desplegar cambios no forma parte de este estudio.**
