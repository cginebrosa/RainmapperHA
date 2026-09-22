# Auditoría de selección y sensibilidad de cinco especies — 21/09/2026

La comparación con el lote nuevo no justifica cambiar todos los modelos a V6 ni
atribuir todos los problemas a humedad. Detecta dos riesgos diferentes: respuesta
excesiva a perturbaciones en algunas alternativas y poca fiabilidad de las llamadas
favorables en algunos ganadores. No se ha cambiado la selección operativa.

## Datos y alcance verificados

- Lote real `operational_20260921T134830Z`, snapshot
  `sha256:49ff67fe57a0c9d0320934870b844fc2e7bb870b00394abceb2460612f8d6df8`.
  Incorpora las entradas nuevas: 518 observaciones, 47 áreas y 84 microáreas.
- Meteorología `20260921T120444009086Z-a2aa23b145df`: 49 objetos verificados por
  SHA contra el manifiesto del entrenamiento antes del barrido. Catálogo y
  hold-out sellados; pesos verificados antes de cargarlos.
- Se reprodujo exactamente el ranking semanal por especie del catálogo,
  conservando las suspensiones. Ganador significa aquí primera familia por
  evidencia de especie, **antes de aplicabilidad y admisión ecológica del punto**.
  No es una afirmación de que todos los lugares deban utilizar ese modelo.
- Sensibilidad: 22 combinaciones especie/familia, 20 artefactos de pesos únicos,
  135 contextos especie/observación, 597 filas completas y 20.298 inferencias.
  Se incluyeron todos los contextos del hold-out oficial de estas cinco especies,
  para una selección de alternativas; no se ensayaron todas las familias instaladas.
- Ejecución offline en el Mac. No se entrenó, precalculó, modificó IDW, promovió
  un candidato ni alteró ninguna suspensión. Ninguna predicción del barrido
  contenía features ausentes.

## Por qué gana una familia

La ordenación semanal prioriza el límite inferior de Wilson de la precisión de
las llamadas favorables. Después desempata por precisión, número de llamadas,
recall, menos indecisiones, Brier, calibración ECE y AUC. Es un orden lexicográfico:
una ventaja pequeña en el primer criterio puede imponerse a una diferencia grande
de calibración. No contiene un criterio explícito de robustez a perturbaciones.

Fuente de implementación: `rainmapper_core/mushroom_predictor_precompute.py:591`
y `rainmapper_core/mushroom_ml_reliability_audit.py:284`. Se reconstruyó el ranking
desde las predicciones hold-out, no se dedujo del nombre o antigüedad del modelo.
La cobertura semanal y las reglas de aplicabilidad siguen siendo filtros propios;
el Predictor puede usar evidencia por área y el mapa evidencia de especie.

## Fiabilidad histórica y estabilidad de la elección

La tabla usa el horizonte 1 para mostrar conteos enteros del hold-out. «Aciertos»
es verdaderos favorables / llamadas favorables con p ≥ 0,60, según la etiqueta
objetivo de entrenamiento; no es una garantía de encontrar setas en una salida.
La estabilidad omite cada grupo de validación y vuelve a ordenar las predicciones
ya guardadas. **No reajusta modelos ni constituye validación independiente.**

| Especie | Familia preferida | Observaciones | Aciertos favorables, h1 | Conserva elección al omitir un grupo | Brier medio semanal |
|---|---|---:|---:|---:|---:|
| Ou de reig | Sparse Group V5w (30d + físico) | 31 | 10/18 | 9/12 | 0.172 |
| Aereus | Shared V6w (90d + físico) | 31 | 16/20 | 11/12 | 0.175 |
| L. deliciosus | ET V3 (IDW común + físico) | 18 | 4/4 | 14/15 | 0.200 |
| Edulis | Partial V6w (90d + físico) | 20 | 6/14 | 10/13 | 0.317 |
| Pinícola | ET V2 (IDW común) | 35 | 5/14 | 12/14 | 0.265 |

Menor Brier indica menor error probabilístico. Es un promedio de siete horizontes
con las mismas observaciones; no multiplica el tamaño muestral por siete.
Los 4/4 de deliciosus tienen muy poco soporte: en h1 solo llama favorables a
4 de las 8 observaciones positivas y deja 12 de 18 casos en la banda intermedia.
Edulis y Pinícola tienen respectivamente 8/14 y 9/14 llamadas favorables falsas
en h1. Ser la mejor opción relativa del ranking no asegura calidad suficiente.
Wilson se calcula sobre observaciones; la dependencia por grupos limita su lectura.

## Sensibilidad de los ganadores

Se desplazaron RH mínima/máxima conjuntamente ±1 y ±2 puntos porcentuales,
lluvia ±5% y ±10%, temperatura mínima/máxima ±0,5 y ±1 °C y estado hídrico
mediante una transformación coherente hacia seco/húmedo de hasta 1 y 2 pp.
El protocolo quedó escrito antes del barrido. Son escalas diagnósticas, **no
incertidumbres medidas ni límites de aceptación**.

La tabla muestra el máximo cambio absoluto de IFF respecto al escenario base,
entre signos y horizontes 1/7, en comparaciones donde ambas predicciones son
elegibles y no están fuera de dominio. Incluye `caution`, que sigue requiriendo
aviso de extrapolación. No compara porcentajes relativos del IFF.

| Especie | RH ±1 pp | Lluvia ±5% | Temperatura ±0,5 °C | SMI hasta 1 pp |
|---|---:|---:|---:|---:|
| Ou de reig | 2.96 | 1.66 | 1.52 | 0.54 |
| Aereus | 0.78 | 2.08 | 1.23 | 0.29 |
| L. deliciosus | 4.18 | 1.73 | 0.90 | 0.25 |
| Edulis | 3.74 | 3.19 | 0.37 | 0.22 |
| Pinícola | 0.58 | 1.32 | 4.53 | 0.00 |

SMI usa `x'=(1-|δ|)x+max(δ,0)` para mantener fracciones en [0,1]; cambios,
recarga y secado se escalan de forma coherente. «Hasta 1 pp» no significa un
desplazamiento constante de 1 pp para todo valor inicial. El cero de Pinícola
ET V2 responde al contrato sin esas variables físicas; no demuestra superioridad.

Las perturbaciones afectan a la historia de entrada completa: simulan un sesgo
coherente, no ruido diario independiente. Al cambiar meteorología se mantiene
SMI fijo; los constructores oficiales recalculan sus otras features derivadas.
No es una simulación hidrológica acoplada. Se conservan los mismos hosts, suelo
y geometría, por lo que esta tabla no mide su contribución.

RH ±1 pp cruza el umbral bruto p=0,60 en 2/31 contextos de Ou, 3/31 de Aereus,
0/18 de deliciosus, 3/20 de Edulis y 0/35 de Pinícola, considerando cualquiera
de ambos horizontes y signos admitidos. Un modelo suave puede cruzarlo con un
cambio pequeño si parte cerca de 60; contar cambios de etiqueta no basta para
medir robustez. No se ha aplicado el redondeo entero de la interfaz.

El resumen privado separa respuestas brutas, admitidas y cruces del dominio.
Algunas alternativas tienen menos contextos admitidos, y Pinícola V2 puede estar
fuera de dominio en un horizonte y admitido en el otro. No convertir el máximo
filtrado en certificado de seguridad de todos los casos.

## Comparación de alternativas

Todos los valores RH/temperatura siguientes son máximos de IFF en comparaciones
admitidas. Brier y ECE son promedios semanales del hold-out; menor es mejor.

| Especie | Puesto histórico | Familia | Brier | ECE | RH ±1 pp | Temperatura ±0,5 °C |
|---|---:|---|---:|---:|---:|---:|
| Ou de reig | 1 | Sparse Group V5w (30d + físico) | 0.172 | 0.195 | 2.96 | 1.52 |
| Ou de reig | 2 | Elastic Net V5w (30d + físico) | 0.189 | 0.212 | 2.13 | 2.33 |
| Ou de reig | 3 | Partial V6w (30d + físico) | 0.206 | 0.256 | 1.92 | 1.61 |
| Ou de reig | 6 | LR V3 (core) | 0.157 | 0.129 | 8.28 | 3.07 |
| Aereus | 1 | Shared V6w (90d + físico) | 0.175 | 0.115 | 0.78 | 1.23 |
| Aereus | 2 | Shared V6w (30d + físico) | 0.175 | 0.122 | 0.44 | 1.01 |
| Aereus | 3 | Shared V6w (60d + físico) | 0.181 | 0.126 | 0.82 | 1.41 |
| L. deliciosus | 1 | ET V3 (IDW común + físico) | 0.200 | 0.285 | 4.18 | 0.90 |
| L. deliciosus | 2 | RF V3 (IDW común + físico) | 0.177 | 0.161 | 14.14 | 13.82 |
| L. deliciosus | 3 | LR V3 (IDW común + físico) | 0.192 | 0.179 | 3.62 | 2.38 |
| L. deliciosus | 10 | Elastic Net V5w (60d + físico) | 0.196 | 0.240 | 6.91 | 6.78 |
| L. deliciosus | 12 | Partial V6w (90d + físico) | 0.238 | 0.288 | 2.53 | 2.06 |
| Edulis | 1 | Partial V6w (90d + físico) | 0.317 | 0.401 | 3.74 | 0.37 |
| Edulis | 2 | Species V6w (90d + físico) | 0.358 | 0.446 | 10.46 | 1.16 |
| Edulis | 3 | Shared V6w (60d + físico) | 0.303 | 0.384 | 0.82 | 1.41 |
| Edulis | 11 | ET V3 (core) | 0.281 | 0.285 | 4.85 | 2.57 |
| Pinícola | 1 | ET V2 (IDW común) | 0.265 | 0.300 | 0.58 | 4.53 |
| Pinícola | 2 | SVM V3 (core) | 0.261 | 0.285 | 10.59 | 4.05 |
| Pinícola | 3 | RF V2 (IDW común) | 0.241 | 0.244 | 5.28 | 25.67 |
| Pinícola | 18 | RF V3 (IDW común + físico) | 0.212 | 0.174 | 30.09 | 9.96 |
| Pinícola | 8 | Sparse Group V5w (30d + físico) | 0.244 | 0.192 | 3.56 | 1.88 |
| Pinícola | 6 | Species V6w (60d + físico) | 0.230 | 0.171 | 2.21 | 3.51 |

## Los dos últimos puntos del usuario

Con pesos nuevos y meteorología del lote, la reconstrucción de los puntos C/D
da Ou 64,25/56,04 y Aereus 32,95/30,71. El ejecutor completo produjo los mismos
resultados dentro de HA local y worker durante la aceptación de 0.2.317.

En el ensayo aislado C→D, sustituir solo las features de humedad relativa de C
por las de D cambia Ou de 64,25 a 57,74; sustituir solo las de estado hídrico lo
deja en 64,40. En Aereus la sustitución de humedad lo mueve de 32,95 a 30,91.
Esto respalda que la respuesta a humedad atmosférica domina esa diferencia de
los modelos examinados; no debe confundirse con el porcentaje de agua del suelo
mostrado arriba del mapa. Son intercambios de features, no porcentajes causales
aditivos ni prueba de que el IDW sea incorrecto. El ensayo aislado reutiliza GIS
congelado; no se presenta como una nueva respuesta en vivo de HA real.

## Decisión que permite tomar y propuesta

1. **No sustituir por versión más reciente ni reentrenar para probar suerte.**
   La familia preferida de Ou no es la más sensible de las alternativas ensayadas.
   LR V3 mejora Brier, pero eleva la sensibilidad RH de 2,96 a 8,28. Elastic Net
   V5 y Partial V6 reducen RH pero tienen otros compromisos de error/lluvia.
   La palabra «hipersensibilidad» no queda demostrada por cercanía entre puntos;
   falta un criterio de aceptación justificado por incertidumbre de entradas.
2. **Aereus: conservar provisionalmente**, sin atribuirle validación espacial.
   El resultado combina sensibilidad RH pequeña y estabilidad 11/12. No hay una
   ganancia demostrada suficiente para cambiar de ventana por esta auditoría.
3. **Deliciosus: no cambiar automáticamente de ET a RF por su mejor Brier.** RF
   mejora calibración histórica, pero llega a 14,14 IFF con RH ±1 pp y 13,82 con
   temperatura ±0,5 °C. La estabilidad 14/15 de ET y sus pocas llamadas favorables
   aconsejan ampliar evidencia independiente, no declarar resuelta la fiabilidad.
4. **Priorizar admisión y calibración de Edulis y Pinícola.** La estabilidad de
   una elección no compensa muchas llamadas favorables falsas. Shared V6 de
   Edulis reduce sensibilidad RH (0,82) pero sigue con fiabilidad limitada;
   Pinícola ET V2 responde poco a RH y aun así falla 9 de 14 llamadas favorables
   en h1. Sus alternativas no ofrecen una solución universal.
5. **Diseñar primero el criterio operativo, sin activarlo todavía.** Acordar el
   coste tolerable de una recomendación favorable falsa frente a una abstención;
   exigir soporte en grupos, calidad respecto al baseline y calibración. Estimar
   incertidumbre de entradas con evidencia meteorológica antes de fijar los
   márgenes de perturbación y tolerancias de IFF. Entre candidatos que superen
   esos requisitos, preferir estabilidad/sencillez cuando la ventaja histórica
   sea incierta. Si ninguno pasa, hacer visible la evidencia insuficiente.
6. **Validar cualquier selector nuevo fuera de los datos usados para diseñarlo.**
   Esta reutilización de hold-out es diagnóstica. No demuestra la mejora de una
   regla elegida después de ver el informe ni sobreajuste de una familia concreta.
   La validación prospectiva con observaciones futuras es una vía; una evaluación
   anidada por grupos requeriría entrenamiento adicional y autorización aparte.

No se ha implementado ninguno de esos cambios. El siguiente entregable debe ser
una propuesta revisable de reglas de admisión/selección y de explicación al usuario
(familia, evidencia, motivo, incertidumbre y abstención), antes de cambiar el código.

## Reproducibilidad y límites

Scripts y evidencia privados, excluidos de Git, en `tmp/model-robustness-20260921/`:
`audit_new.py`, `new-ranking-audit.json`, `expanded_stress.py`,
`expanded-stress-protocol.json`, `expanded-stress-results.jsonl`,
`summarize_expanded.py`, `expanded-stress-summary.json`, `selected-artifacts.json`
y `olvan-new-results.json`. El resumen incluye SHA de sus entradas y verifica
597 filas únicas completas, 17 escenarios y 2 horizontes por fila, sin NaN.

Los pesos operativos pueden haber visto estos contextos. La sensibilidad no es
una prueba fuera de muestra; toda precisión histórica proviene exclusivamente
del hold-out sellado. Hay observaciones dependientes y contextos meteorológicos
repetidos: 20.298 inferencias no equivalen a 20.298 observaciones independientes.
Los percentiles son descriptivos de la muestra, no límites de confianza. Esta
auditoría no permite afirmar robustez global, causalidad ecológica o fiabilidad
espacial. No se reproducen aquí ubicaciones ni observaciones privadas.
