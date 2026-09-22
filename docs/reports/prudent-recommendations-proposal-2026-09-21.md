# Recomendaciones prudentes y reversibles — propuesta 21/09/2026

**Propuesta inicial descartada por su coste en aciertos.** El usuario exige
evitar más errores que aciertos perdidos. La propuesta vigente es el
[filtro de acuerdo selectivo](recommendation-consensus-proposal-2026-09-21.md).
Este documento conserva la simulación inicial; no implementarla como decisión vigente.

Estado: decisiones de diseño y simulación retrospectiva; **sin implementación ni
activación operativa**. El usuario prefiere abstención frente a recomendaciones
favorables poco fiables, manteniendo utilidad, y exige poder desconectar el filtro
para comprobar su efecto con observaciones futuras.

## Decisiones propuestas para la primera política

1. Conservar las familias semanales actuales de las cinco especies auditadas.
   No sustituirlas por la generación más reciente ni buscar un modelo distinto
   cada día hasta conseguir una recomendación. La abstención se evalúa por plazo
   de predicción: evidencia de h1 no acredita automáticamente h7 ni viceversa.
2. Mantener la condición numérica actual de favorable, p ≥ 0,60, separada de la
   autorización para recomendar. Subir simplemente a 0,70/0,80 no solventa una
   mala calibración. No interpretar un IFF 80 como 80% de certeza de la salida.
3. Autorizar recomendación solo si la evidencia histórica comparable de esa
   familia/especie/plazo cumple conjuntamente:
   - límite inferior Wilson 95% de precisión favorable **mayor que 0,50**;
   - llamadas favorables procedentes de **al menos tres grupos de validación**;
   - al retirar cualquiera de esos grupos, precisión favorable restante
     **al menos 0,60**, con denominador no vacío.
   Esta es una propuesta de tolerancia al riesgo. Los números no son constantes
   biológicas ni umbrales científicamente acreditados por este análisis. Wilson
   se calcula sobre observaciones dependientes; no es una garantía al 95% sobre
   salidas futuras. Soporte por grupos y omisión son comprobaciones adicionales,
   no una corrección formal de esa dependencia.
4. Conservar filtros existentes de datos, dominio, compatibilidad y suspensiones.
   El filtro nuevo solo puede retirar una recomendación, nunca rescatar un fallo,
   forzar una especie incompatible ni convertir abstención en ausencia de setas.
5. Cuando no pase: «Sin recomendación fiable», con motivo comprensible. Se puede
   consultar el IFF experimental en detalle, pero no mantener color, etiqueta
   favorable ni posición de «mejor apuesta» que contradigan la abstención.
   Mostrar «Aciertos: X de Y recomendaciones, en Z grupos de comprobaciones»;
   definir los grupos como agrupación de casos cercanos, no visitas independientes.
6. No imponer cuota mínima de recomendaciones. Evitar abstenerse siempre se
   comprueba midiendo cobertura; no obliga a recomendar Edulis o Pinícola sin
   evidencia. Una especie puede quedar temporalmente sin recomendaciones.

## Resultado medido con los modelos y predicciones existentes

Datos: lote `operational_20260921T134830Z`; hold-out `fruiting_groups_14d` sellado,
SHA verificado contra manifiesto. Familias preferidas fijas, sin entrenamiento,
sin nuevos cálculos meteorológicos ni precálculo. Los 35 bloques especie/plazo
reutilizan 135 observaciones; las 945 decisiones no son casos independientes.

| Regla simulada | Recomendaciones | Aciertos | Errores | Aciertos entre recomendaciones |
|---|---:|---:|---:|---:|
| Actual: p ≥ 0,60, sin filtro nuevo | 408 | 258 | 150 | 63,2% |
| Solo subir p a 0,70 | 292 | 199 | 93 | 68,2% |
| Solo subir p a 0,80 | 211 | 145 | 66 | 68,7% |
| Prudente: p ≥ 0,60 y las tres condiciones | 122 | 102 | 20 | 83,6% |

La propuesta conserva 29,9% de las recomendaciones anteriores y 39,5% de sus
aciertos; evita 86,7% de sus errores. Retira **156 aciertos y 130 errores**.
Recomienda en 12,9% de las 945 decisiones observación/plazo examinadas, antes de
añadir filtros de aplicabilidad/ecología del punto; la cobertura real puede ser
menor. No promete que esos porcentajes se repitan en uso real.

Comparación de exigencias usando p ≥ 0,60 y los mismos requisitos por grupos:
un límite Wilson >0,40 deja 152 recomendaciones (124 aciertos/28 errores);
>0,50 deja 122 (102/20); >0,60 no deja ninguna. Elegimos **proponer >0,50** por la
preferencia expresada de evitar errores, reconociendo el coste de abstención.
No se ha buscado el decimal que maximice el resultado ni una regla distinta para
cada especie. La elección después de ver datos sigue teniendo sesgo de selección.

| Especie | Plazos que pasarían el filtro | Recomendaciones conservadas | Aciertos / errores |
|---|---|---:|---:|
| Ou de reig | h4 | 11 | 9 / 2 |
| Aereus | h1, h2, h3, h4, h6 | 86 | 68 / 18 |
| L. deliciosus | h3, h4, h5, h6, h7 | 25 | 25 / 0 |
| Edulis | Ninguno | 0 | — |
| Pinícola | Ninguno | 0 | — |

Son plazos respecto al corte meteorológico, no días concretos de una semana ni
una afirmación de que Ou fructifique mejor el cuarto día. Los saltos reflejan
evidencia pequeña e irregular; deben explicarse como disponibilidad de evidencia,
no como discontinuidades biológicas. Deliciosus h1/h2 tiene 4/4 aciertos pero
solo dos grupos con llamadas: no pasa el requisito de diversidad.

Ninguna de las alternativas de Edulis/Pinícola incluidas en la auditoría de
sensibilidad supera siquiera el requisito Wilson >0,50 a p ≥ 0,60 en estos
plazos. Cambiar de familia no las rescata bajo esta regla. En Aereus otras ventanas
pasarían ciertos plazos diferentes; no combinarlas después de ver los resultados
para aparentar una cobertura validada que todavía no se ha demostrado.

## Parámetro reversible solicitado por el usuario

Contrato **propuesto**, nombres todavía no existentes en configuración:

`recommendation_policy_mode`: `legacy` / `shadow` / `prudent`.

- **Actual (`legacy`)**: comportamiento de recomendación previo a este filtro.
  Conserva las correcciones técnicas del mapa y todas las suspensiones existentes.
- **Solo comparar (`shadow`)**: muestra el comportamiento actual y registra qué
  habría retenido la política prudente; no influye en lo mostrado al usuario.
- **Prudente (`prudent`)**: aplica abstención y conserva la decisión anterior como
  referencia para comparar. Modo recomendado tras completar aceptación local.

Una opción visible en configuración de predicción, coherente entre mapa,
Predictor, HA y worker. Volver a `legacy` debe desactivar únicamente este filtro,
sin alterar modelos, IDW, geografía o evidencia. No hay que reentrenar para cambiar
el modo. No generar nuevas inferencias para la rama de referencia: reutilizar la
misma probabilidad y evidencia, aplicando las dos decisiones ligeras.

Identificar la regla con una versión (`prudent_v1`, propuesta), sus umbrales,
ámbito de evidencia, lote y horizonte. Configuración persistida por el coordinador
y transmitida de forma explícita; nunca depender de un ajuste oculto del worker.
Los resultados finales y sus cachés deben distinguir modo/versión de política.
Los artefactos base compatibles pueden reutilizarse, pero no se puede etiquetar
una respuesta antigua como prudente sin reevaluar la decisión. La implementación
deberá verificar si la evidencia disponible en cada respuesta permite esa
reevaluación; no se promete reutilización de todos los formatos de precálculo.

No duplicar catálogos o pesos por punto/día/política: referenciar evidencia sellada.
La comparación debe usar un registro diagnóstico acotado fuera del contrato
operativo: referencia de consulta, momento, objetivo temporal, especie, ámbito
espacial necesario, lote/modelo/evidencia, IFF, modo y ambas decisiones/motivos.
Definir retención y medir tamaño antes de implementarlo. No guardar observaciones
privadas en el repositorio ni multiplicar payloads de HA real.

## Cómo comprobar si mejora en la realidad

Registrar ambas decisiones **antes** de conocer la observación futura. Evaluarlas
sobre los mismos casos observados: recomendaciones equivocadas, recomendaciones
acertadas y oportunidades acertadas que se perdieron por abstención. Mostrar
conteos y cobertura junto a porcentajes, por especie y plazo, con agrupación de
observaciones próximas. No contar lugares no visitados como ausencias.

El emparejamiento consulta/observación exige fecha, especie y ámbito espacial
compatibles; no asignar automáticamente una observación al punto más cercano sin
un contrato de correspondencia. Si faltan observaciones representativas, decirlo:
la selección de lugares visitados puede sesgar el balance.

Con nuevas observaciones evaluadas después se revisan los resultados; con un
nuevo entrenamiento se recalcula la evidencia del lote. No rebajar automáticamente
umbrales por falta de recomendaciones ni ajustar el filtro tras cada resultado.
Conservar versión y periodo de cada regla para poder compararlas sin mezclar datos.

Esta simulación usa los mismos datos que ayudaron a elegir los modelos y diseñar
la política: **es una estimación retrospectiva del compromiso, no una validación
independiente de mejora**. La sensibilidad medida sirve para evitar sustituciones
precipitadas; aún no hay márgenes de incertidumbre justificados para convertirla
en un veto automático. Tampoco se ha fijado un umbral ECE arbitrario a partir de
esta muestra pequeña.

## Antes de activarlo

Implementar y probar primero en local: modo persistido, equivalencia exacta de
`legacy`, decisiones espejo sin doble inferencia, abstención por motivos claros,
paridad HA/worker, invalidación correcta de respuestas finales cacheadas y ninguna
promoción involuntaria de modelos suspendidos. Verificar métricas de la evidencia
real por área y alcance del resto de especies; este informe solo simula las cinco
especies y familias preferidas a nivel de especie. La propuesta no acredita el
comportamiento del selector completo del Predictor por área.

Respetar el circuito local proporcional y las restricciones del usuario sobre
entrenamientos, precálculos y workers. No activar ni publicar como validada sin
haber comprobado esos contratos y mostrado el resultado local revisable.

Fuentes: [auditoría ampliada](model-selection-robustness-2026-09-21.md),
`tmp/model-robustness-20260921/recommendation_tradeoff.py` y
`recommendation-tradeoff.json` (privados, ignorados por Git). El script verifica
integridad y reproduce los conteos h1–h7 del catálogo antes de simular.
