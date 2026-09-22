# Filtro de acuerdo: evitar más errores que aciertos perdidos — 21/09/2026

**Propuesta revisada del 21/09. Implementada en el worktree el 22/09, sin activar ni desplegar.**
Ver [implementación y validaciones](recommendation-consensus-implementation-2026-09-22.md). Sustituye como
recomendación de diseño al [filtro general de fiabilidad](prudent-recommendations-proposal-2026-09-21.md),
cuyo coste de 156 aciertos perdidos por 130 errores evitados rechazó el usuario.
Nuevo criterio explícito: evitar más errores de los que se eliminan aciertos,
sin anular la utilidad de las recomendaciones. Mantener opción para desconectarlo
y comparar con observaciones futuras.

## Decisión propuesta

Conservar el modelo semanal preferido y su IFF. Para **Ou, Edulis y Pinícola**,
recomendar solo cuando el preferido y las dos alternativas siguientes del ranking
semanal sellado devuelvan p ≥0,60 para el mismo caso. Si discrepan, abstenerse con
«Los modelos no coinciden lo suficiente para recomendar». No promediar el IFF,
no elevarlo, no crear recomendaciones donde el ganador no las daba y no cambiar
de alternativas cada día buscando acuerdo.

**Aereus y deliciosus permanecen sin este filtro adicional** en la primera prueba:
en Aereus el filtro evita tantos errores como aciertos elimina; en deliciosus
solo elimina aciertos en esta muestra. Esto no acredita fiabilidad general de esas
especies: evita imponer una medida que no ha mostrado beneficio en ellas.

Es un filtro de una recomendación concreta; no bloquea una especie/plazo entero
por su evidencia global. Mantener los filtros existentes de compatibilidad,
datos, dominio y suspensiones. Nunca utilizar un modelo suspendido como respaldo.
Si falta una alternativa elegible, distinguir «comparación no disponible» de
«desacuerdo»; no contar datos ausentes como votos. Antes de activar habrá que
definir y medir ese caso en los dos ejecutores.

## Resultado retrospectivo observado

Mismo lote real nuevo `operational_20260921T134830Z`, hold-out oficial
`fruiting_groups_14d`, familias semanales fijas. No hubo entrenamientos,
precálculos ni inferencias adicionales: se reutilizaron predicciones guardadas.
Se verificó SHA, población alineada, etiquetas y las tres predicciones por caso.

| Política | Recomendaciones | Aciertos | Errores | Aciertos perdidos | Errores evitados |
|---|---:|---:|---:|---:|---:|
| Actual | 408 | 258 | 150 | — | — |
| Filtro global anterior, descartado | 122 | 102 | 20 | 156 | 130 |
| Acuerdo de tres en las cinco especies | 338 | 235 | 103 | 23 | 47 |
| Acuerdo de tres solo en Ou/Edulis/Pinícola | 359 | 248 | 111 | 10 | 39 |

La propuesta selectiva conserva **88,0% de las recomendaciones** y **96,1% de
sus aciertos**, y evita **26,0% de sus errores**. Entre las recomendaciones
retenidas, los aciertos pasan del 63,2% al 69,1% en esta simulación. Quedan 111
errores: es un compromiso mejor, no una solución completa de calibración.

| Especie | Errores que evitaría el acuerdo de tres | Aciertos que eliminaría | Aplicación propuesta |
|---|---:|---:|---|
| Ou de reig | 3 | 0 | Probar filtro |
| Aereus | 8 | 8 | Conservar actual |
| L. deliciosus | 0 | 5 | Conservar actual |
| Edulis | 12 | 0 | Probar filtro |
| Pinícola | 24 | 10 | Probar filtro |

Los totales cuentan decisiones observación/plazo; **no son 945 observaciones
independientes**. Las 135 observaciones se reutilizan a siete horizontes.
En h1, la propuesta selectiva evita 7 errores y pierde 1 acierto: pasa de
70 recomendaciones (41 aciertos/29 errores) a 62 (40/22). Los cambios de la semana
afectan a 14 observaciones negativas y 5 positivas distintas, en algún horizonte;
no significa que evite o pierda todos los horizontes de cada observación.

Con la regla selectiva fija, al omitir uno de los grupos de cada especie, el
beneficio neto de esa especie (errores evitados menos aciertos perdidos) permanece
positivo: Ou entre 1 y 3; Edulis entre 6 y 12; Pinícola entre 4 y 23. Es una
comprobación descriptiva de dependencia, **sin volver a seleccionar familias ni
ámbito**. No demuestra que una selección hecha sin ese grupo hubiera sido igual.
El balance global por horizonte es positivo en h1–h6 y empatado en h7; no se
adapta la regla a posteriori por día para mejorar la tabla.

## Qué otras opciones se compararon

Las reglas se declararon antes de leer las probabilidades de esta comparación,
pero el trabajo completo es exploratorio y reutiliza datos previamente examinados.

| Regla común para cinco especies | Errores evitados | Aciertos perdidos | Balance neto |
|---|---:|---:|---:|
| Subir a p ≥0,70 | 57 | 59 | -2 |
| Ganador favorable y una de las otras dos también | 8 | 10 | -2 |
| Ganador y las otras dos favorables | 47 | 23 | +24 |
| Ninguna alternativa claramente desfavorable (p ≤0,40) | 4 | 4 | 0 |
| Un respaldo favorable y ninguna oposición clara | 8 | 12 | -4 |
| Ganador favorable y media de tres ≥0,60 | 16 | 12 | +4 |

El criterio del usuario descarta las reglas de balance negativo. La de acuerdo
de tres permite un filtro sencillo y un balance mejor en esta comparación. La
decisión de limitarlo a tres especies se tomó **después de ver el desglose**:
puede sobreestimar su beneficio futuro. No ocultar esa selección ni presentarla
como validación independiente o ajuste óptimo universal.

Las alternativas son las siguientes dos familias admitidas en el ranking
semanal de evidencia de especie de la auditoría, no modelos escogidos caso a caso
por sus aciertos. Están ya incluidas en la comparación de sensibilidad. Pueden
estar fuertemente correlacionadas (por ejemplo, ventanas del mismo estimador);
su acuerdo no equivale a tres pruebas independientes ni a confianza multiplicada.

## Parámetro, comparación y coste operativo

Se conserva la necesidad de un parámetro visible y persistido con tres modos
propuestos: `legacy` (actual), `shadow` (actual + comparación), `prudent` (filtro
activo + comparación). Usar una versión específica de regla, propuesta
`consensus_v1`, y ámbito explícito Ou/Edulis/Pinícola. Estos nombres se han incorporado al código del worktree el 22/09; sin ajuste
explícito se conserva `legacy`. No reutilizar sin distinguirlo un identificador
que significase el filtro global anterior.

Apagar el filtro debe restaurar exactamente la decisión actual conservando
correcciones técnicas, suspensiones y modelos. Registrar las decisiones actual
y filtrada junto con referencias de lote/modelos/evidencia y regla, antes de
conocer el resultado de campo. Evaluar ambas contra las mismas observaciones
compatibles, sin contar sitios no visitados como ausencias.

**Corrección respecto a la propuesta anterior:** el acuerdo necesita dos
predicciones adicionales cuando no estén ya disponibles. No prometer una única
inferencia ni coste cero. Reutilizar meteorología, features compartidas y pesos
cacheados cuando el contrato lo permita; no duplicar reconstrucciones GIS/SMI.
Medir latencia, memoria y cardinalidad tanto en HA local como en worker antes
de decidir activación. Los modelos colectivos pueden compartir artefacto, pero
eso debe comprobarse, no asumirse. No cargar todas las familias para comprobar
tres. Mantener diagnóstico fuera del payload operativo mínimo y por referencias.

Las cachés/respuestas finales deben incluir modo/versión/ámbito; un precálculo
antiguo no acredita acuerdo si no contiene las predicciones necesarias. Verificar
compatibilidad de artefactos y mecanismos de abstención antes de activarlo.
No lanzar precálculos o entrenamientos para suplir estos datos sin autorización.

## Siguiente paso y criterio de aceptación

Preparar implementación local reversible y medir coste/cobertura efectiva de
comparadores elegibles. Ensayar primero en `shadow`: mismo resultado visible
actual, registro comparable de lo que habría retirado el filtro. La activación
en real requiere validación local del contrato común mapa/Predictor/worker y
una publicación autorizada; esta simulación no la sustituye.

La evaluación futura debe informar beneficio neto **y** volumen conservado por
especie, usando observaciones posteriores no usadas para escoger esta regla.
Si no se evitan más errores que aciertos perdidos, no mantener el filtro por
inercia. Con pocos casos informar «aún sin evidencia suficiente»; no mover
umbrales tras cada observación para forzar una mejora. El requisito no garantiza
balance positivo para cualquier muestra futura.

Este análisis no reproduce el selector completo del Predictor por área ni la
aplicabilidad de los tres modelos en cada punto. La cobertura real puede ser
menor. La primera prueba abarca solo las cinco especies auditadas y debe
explicitar qué alcance queda sin evaluar.

Evidencia privada reproducible: `tmp/model-robustness-20260921/consensus_tradeoff.py`
y `consensus-tradeoff.json`. Predicciones históricas y familias:
`new-batch/holdout-predictions.jsonl.gz`, `new-ranking-audit.json`.
