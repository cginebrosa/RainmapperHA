# Evidencia de campo pendiente de identificar · 20/09/2026

El usuario comunica que un compañero visitó ayer tres ubicaciones para las que
se mostraba un IFF ≥80 para Lactarius deliciosus y no encontró ninguna seta de
ninguna especie en las tres. La fecha inferida por «ayer» sería 19/09/2026,
pendiente de confirmación. No se conocen aún coordenadas/setales, fecha de la
consulta del IFF, entorno, modelo ganador ni detalle del esfuerzo de búsqueda.

Es evidencia adversa relevante sobre la utilidad práctica de esas predicciones.
No atribuirla al SMI, al modelo HGB ni al cambio actual sin recuperar los datos.
Tampoco interpretar el IFF como probabilidad calibrada de encontrar setas.
No afirmar que la unificación del SMI vaya a resolver estos casos: algunas
versiones no consumen estado hídrico y otras pueden fallar por otras razones.

Se han pedido al usuario las tres ubicaciones, fecha de visita y fecha/entorno
de la predicción. Conservar, si están disponibles, las predicciones originales
y sus modelos/datos; una predicción recalculada posteriormente no demuestra qué
se mostró antes de la visita. Registrar las observaciones negativas cuando se
identifiquen, evitando duplicados. Si se incorporan al entrenamiento, dejar de
considerarlas validación independiente del modelo reentrenado.

## Capturas aportadas posteriormente

Lectura directa de las capturas del 18/09/2026 (fecha seleccionada 18/09,
gráfica hasta 24/09, ejecutor mostrado «Worker»):

| Punto | Coordenadas | Altitud mostrada | IFF Lactarius deliciosus |
|---|---|---|---|
| Vallcebre A | 42.20292, 1.84242 | 1274,5 m | 86/100, plano toda la semana |
| Vallcebre B | 42.18669, 1.82177 | 1316,2 m | 84/100, plano toda la semana |
| Bellver de Cerdanya / Riu | 42.31110, 1.79167 | 1564,3 m | 100/100, plano toda la semana |

La cuarta imagen repite la tercera: son tres puntos, no cuatro. Las imágenes
no muestran ID de modelo, generación ni versión de la aplicación. Las curvas
planas coinciden con el síntoma histórico investigado, pero no prueban que el
estimador fuera HGB. Los IFF del día 19 se leen de las mismas curvas planas;
el número destacado corresponde al día 18 seleccionado.

Se conservarán como comparación externa del entrenamiento nuevo. No se ha
insertado una observación en los datos de entrenamiento a partir de estas
capturas. Esta nota no contiene un diagnóstico causal ni una evaluación
cuantitativa de rendimiento.
