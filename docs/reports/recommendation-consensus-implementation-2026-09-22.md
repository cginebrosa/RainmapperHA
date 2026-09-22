# Implementación local de reservas y consenso — 22/09/2026

Estado: código del worktree implementado y probado; sin publicar, activar una
política en HA real ni reconstruir contenedores. Sigue vigente la aceptación
local previa a cualquier release. No se han lanzado entrenamientos ni precálculos
operativos; los SQLite de las pruebas contienen exclusivamente fixtures sintéticos.

## Decisiones visibles

En **Workers y trabajos → Modelos de predicción** hay un selector persistido:

- Desactivado (`legacy`): conserva la decisión anterior y mantiene los avisos.
- Solo comparar (`shadow`): conserva la recomendación y registra qué retiraría.
- Aplicar (`prudent`): requiere acuerdo para mantener una recomendación favorable.

Sin configuración explícita sigue `legacy`; no hay activación automática.
Regla `consensus_v1`, ámbito fijo Amanita caesarea, Boletus edulis y B. pinophilus.
Deliciosus y aereus reciben explicaciones/reservas, sin este veto adicional.
No cambia el IFF ni la familia elegida. Si retira una recomendación, muestra el
motivo y conserva el IFF como referencia. Las retiradas siguen siendo inspeccionables
en el recomendador. Una falta de alternativas válidas figura como comparación no
disponible, no como desacuerdo.

El parámetro vive en el JSON de política separado de los modelos, también en su
exportación/importación. Cambiarlo invalida identidades de servicio/resultados
anteriores; no invalida el contrato de entrenamiento ni lanza trabajos. Una
promoción de modelos conserva la política del usuario. Los workers sin la
capacidad `recommendation_consensus_v1` no pueden ejecutar los modos activos.

## Selección y auditoría

Se conserva el selector operativo: cobertura/aplicabilidad semanal, luego evidencia
histórica. Los comparadores son **las dos familias siguientes a la elegida en el
orden semanal sellado**, distintas y fijas durante toda la semana. No se sustituyen
cada día para buscar acuerdo. Una suspensión o veto operativo invalida su voto.
Si no hay familias semanales fijas, no se acredita consenso y el modo Aplicar
se abstiene cuando la recomendación anterior era favorable.

La retrospectiva 39 errores evitados / 10 aciertos perdidos NO acredita el mismo
resultado en el selector completo por área: allí se compararon las tres primeras
familias históricas. Cuando la cobertura mueve el ganador, sus siguientes alternativas
también cambian. El modo Solo comparar sirve para medir esta diferencia sin retirar
recomendaciones todavía. No se han añadido observaciones GBIF pendientes de revisión.

La resolución conserva modo, versión de regla, decisión actual/filtrada y hasta dos
referencias exactas de modelos con probabilidades/estado. Los modelos materializados
conservan lote y generación en sus referencias. La composición desde SQLite reutiliza
la decisión sellada; no necesita transportar features de las alternativas.

Las reservas cuentan familias efectivamente evaluadas, no horizontes ni familias
que el mapa dejó sin ejecutar. Se muestran descartes por falta de datos y cuántos
estaban por delante de la elegida. Suspensión, dominio y calidad histórica son
causas diferentes y no se contabilizan como datos ausentes. Los motivos pueden
solaparse; no se suman como modelos distintos. Un resultado antiguo sin desglose
lo declara, en lugar de inventar cero descartes.

Comprobación adicional de lectura sobre `tmp/querigut-review-20260921/alternatives.json`:
**21/33** familias con veto por datos, **9** mejor clasificadas que la servida;
21 con cobertura de lluvia insuficiente y 5 con estado hídrico ausente. Es el
snapshot de la revisión previa, no una nueva consulta a HA real. No modifica
el IFF de deliciosus ni lo somete al consenso.

## Validación realizada

- Batería dirigida de 254 pruebas Python: 253 pasaron en sandbox; la prueba de
  transporte HTTP local estaba bloqueada por el puerto del sandbox y pasó al
  repetirla con permiso fuera de él. Añadida después una prueba de cambio de
  identidad/capacidad del mapa: suite de runtime 14/14.
- 35 pruebas dirigidas de consenso/orquestación/runtime del mapa pasaron después
  de ampliar la verificación de reutilización y excluir inferencias adicionales
  fuera de temporada. No se han probado modelos mediante reentrenamiento.
- Revisión final de reutilización entre vistas: 152/152 pruebas del selector,
  servicio, SQLite, consenso y semana del mapa. Se preservan el ranking original,
  los recuentos de descartes y la decisión al pasar del recomendador al detalle;
  una cadena ya reducida al ganador no se vuelve a presentar como auditoría 1/1.
- Prueba real en Chrome con servidor y datos ficticios: avisos de descartes,
  IFF 99 conservado, etiqueta Sin recomendación en Aplicar y recomendación intacta
  en Solo comparar; también regresiones existentes de móvil, fechas, errores,
  permisos y mapa compartido.
- Guardado del selector, formulario obsoleto, importación/exportación, persistencia
  al promover modelos, huellas de servicio vs entrenamiento, rechazo de worker
  antiguo, tres vistas del Predictor, caché de decisiones y composición SQLite.
- En el caso sintético de tres familias: 7 evaluaciones del ganador más 7 llamadas
  con el par de alternativas; **una sola preparación meteorológica/hídrica**.
- Aviso compacto deduplicado de siete días: **426 bytes** en el ejemplo medido.
  Contar las exclusiones ya guardadas no ejecuta modelos. Las dos inferencias
  adicionales del filtro sí tienen coste; no se afirma que sean gratuitas.

Fuentes ejecutables: `rainmapper_core/mushroom_recommendation_policy.py`,
`mushroom_ml_multiversion_comparison.py`, `mushroom_predictor_service.py`,
`mushroom_map_prediction.py`, `mushroom_map_model_runtime.py`; pruebas
`tests/test_mushroom_recommendation_policy.py` y módulos relacionados.

## Pendiente antes de activación/publicación

Medir latencia y memoria completas y cobertura efectiva en HA local + worker con
la versión reconstruida, cumpliendo `docs/release-flow.md` y preservando sus
coordinadores. El worker que esté trabajando no se reconstruye. La prueba de
contrato con fixtures no sustituye este circuito. El usuario ejecuta los
precálculos; no repetir entrenamientos para diagnosticar. Empezar por Solo comparar,
revisar ausencias de alternativas y volumen retenido, y obtener aceptación antes
de activar/publicar en real. No extrapolar el tiempo de una prueba Python al RPi4.

## Aclaración del aviso y detalle de alternativas (22/09)

A petición del usuario se conserva la regla: recomendación favorable e IFF >= 60,
dos familias alternativas fijas. El aviso de acuerdo explica «Comprobación
superada» y que se mantiene la recomendación. Mapa y Predictor permiten desplegar
los nombres/perfiles e IFF de las dos alternativas. No cambia la selección ni
se añaden inferencias. Detalle no disponible se muestra como tal.

El mapa transporta como máximo dos filas compactas (etiqueta acotada a 256
caracteres, probabilidad y estado); las referencias completas/features siguen
fuera del contrato. Resumen de ejemplo con dos alternativas: 442 bytes JSON UTF-8,
sin auditoría de disponibilidad. Continúa la deduplicación por día. Se admiten
avisos anteriores sin detalle; se rechazan cardinalidad y valores inválidos.

Validación: 44 pruebas dirigidas correctas y navegador correcto (41 consultas),
incluido desplegar dos resultados y conservar el IFF original. La primera
comprobación visual falló por apuntar a la leyenda del gráfico en el test;
corregido el selector, pasó. No se han ejecutado entrenamientos ni precálculos.
