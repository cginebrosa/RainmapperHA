# Auditoría comparativa del Predictor con y sin contador de días secos

## Decisión y cierre

El 11/09/2026 el usuario decide mantener el contador actual y cerrar esta
auditoría. No se sustituyen modelos ni se cambian contratos.

Limpieza al cierre: eliminados de `/private/tmp` los dos resúmenes auxiliares
`rainmapper-dry-audit-summary.txt`, `rainmapper-dry-audit-summary-final.txt`
y el script puntual `rainmapper-dry-selector-trace.py`; también el
`recent/empty.jsonl` de la primera construcción fallida del catálogo.
Cuatro archivos, 54.268 bytes; ausencia comprobada después del borrado.
Se conservan informes, scripts reproducibles y resultados en `docker-data/audits/`,
incluidas las trazas ya generadas. Los `replay/empty.jsonl` son entradas vacías
intencionadas del catálogo y se conservan con los resultados del ensayo.

## Plan registrado antes de ejecutar

El usuario autoriza el 11/09/2026 una comparación aislada de V2/V3/V4 con y sin
contador, incluyendo el selector real. Esta autorización permite ajustes
experimentales locales; no sustituir modelos, activar precálculos ni publicar HA.

### Qué se compara

- A: contratos y algoritmos actuales de las versiones instaladas V2/V3/V4.
- B: los mismos modelos sin `dry_spell_observed_at_cutoff` ni
  `dry_spell_is_censored` cuando este último sea una entrada predictiva.
- V5w/V6w participan idénticos en A y B. Se entrenan una sola vez por partición
  con datos permitidos; no reutilizar los binarios operativos, que podrían haber
  visto las observaciones del examen. Las V5/V6 antiguas no instaladas no entran.
- Todos los perfiles y estimadores declarados en las cinco versiones instaladas,
  contratos fixed h7 y lag h1–h7. No limitarse a las seis configuraciones de la
  auditoría anterior. Inventariar intentos y motivos de exclusión.
- Reentrenamiento controlado con el código actual: no se pretende identidad
  numérica con los artefactos instalados, entrenados con más datos.

### Datos y separación temporal

Reutilizar exclusivamente los inputs históricos ya preparados el 05/09 en
`mushroom-hydric-ablation-20260905/prepared/snapshot` y `prepared/v5-current`.
Registrar sus huellas; no reconstruir meteorología ni GIS ni introducir nuevas
etiquetas. Usar las nueve especies del manifiesto operativo local, inventariando
también las restantes presentes en los históricos.

Dos exámenes cronológicos, fijados sin mirar los resultados:

| Examen | Entrenamiento | Evidencia para elegir | Examen final |
|---|---|---|---|
| Principal | Hasta 2022 | 2023–2024 | 2025–2026 disponibles |
| Estabilidad | Hasta 2020 | 2021–2022 | 2023–2024 |

Retirar de entrenamiento/evidencia los últimos 14 días antes del cambio de
bloque. Mantener juntos los grupos de florada de 14 días y todos los horizontes
de una observación; excluir grupos que crucen bloques. Fechas globales para
todas las especies, también en V6 compartida, para evitar que el modelo vea
el futuro a través de otra especie. Exigir al menos ocho observaciones de
entrenamiento y ambas clases para modelos por especie; registrar cualquier
requisito adicional del algoritmo. Las especies sin soporte permanecen en el
inventario y en el recuento de cobertura.

La evidencia del selector se calcula exclusivamente en el bloque intermedio,
con los mínimos y filtros vigentes. No rebajar esos mínimos si hay abstenciones.
V5 usa selección interna de sus parámetros solo dentro del entrenamiento; V6
usa la configuración por defecto del entrenador, idéntica entre alternativas.
No usar tuning instalado que pueda incorporar etiquetas del examen final.

### Recorrido del selector

1. Entrenador e inferencia actuales; recalcular el soporte de aplicabilidad
   usando únicamente las filas de entrenamiento y las columnas de cada brazo.
2. Construir evidencia por especie/área/horizonte desde el bloque intermedio.
   Invocar el catálogo de calidad y las funciones de selección actuales.
3. Comparación diaria h1–h7, con fixed h7 disponible según el contrato vigente.
4. Comparación semanal: situar cada observación en cada uno de los siete días
   de una semana. Compartir el corte correspondiente en toda esa semana;
   actualizar únicamente horizonte y variables de fecha/edad de lluvia conforme
   a sus fórmulas vigentes, conservando los datos meteorológicos al corte.
   Verificar que el día observado reproduce exactamente sus entradas guardadas.
5. Invocar continuidad semanal, prioridad por aplicabilidad y selección final,
   conservando el fallback diario vigente. Puntuar solo el día cuya observación
   conocemos; los otros seis sirven para resolver cobertura, no reciben etiquetas
   inventadas. Para fallback, puntuar ese día con sus entradas diarias exactas.

No transportar matrices ni diagnósticos al contrato operativo. Esta es una
reproducción local del cálculo y del selector, no un precálculo publicado ni
una prueba de la interfaz web.

### Cómo se decidirá

- Error probabilístico por modelo y por selector; en el selector comparar
  primero los mismos casos donde A y B dan predicción y presentar aparte cambios
  de cobertura. No conseguir una mejora aparente excluyendo casos difíciles.
- Recomendaciones favorables con el umbral actual 0,60: aciertos, falsas
  recomendaciones y oportunidades no recomendadas. No usar el 0,50 diagnóstico
  de la auditoría anterior como sustituto del criterio operativo.
- Probabilidades, identidades elegidas, abstenciones y sus razones por especie,
  horizonte y examen; no contar siete horizontes como siete observaciones
  independientes. Intervalo descriptivo mediante remuestreo de grupos completos.
- Separar efecto en modelos V2/V3/V4 y efecto final al competir con V5w/V6w.
- Informar si los datos son insuficientes o el resultado no es estable. Los
  históricos ya se han examinado en otras auditorías: no afirmar validación
  prospectiva ni certeza sobre semanas nuevas.

### Recursos y protección

Un proceso local con un hilo numérico. Materializar perfiles por bloques,
reutilizar matrices entre algoritmos y A/B, inferencia por lotes, salidas
compactas bajo `docker-data/audits/`. Preflight de tamaño y cardinalidad antes
de ajustar; registrar duración y fallos. Los modelos se mantienen en memoria,
sin promoverlos. Conservar SHA256 de las observaciones del repositorio y locales,
registro operativo, manifiesto, SQLite activo y recibo antes/después. No tocar
contenedores ni sus coordinadores.

## Resultados

**Recomendación tras ejecutar: conservar por ahora el contador en los contratos
actuales.** La pequeña ventaja semanal del examen reciente no se mantiene en el
anterior; aparecen pérdidas de cobertura. La decisión de cambiar contratos sigue
perteneciendo al usuario. No se ha aplicado ningún cambio operativo.

### Resumen comprensible

En 2025–2026, quitar el contador reduce un 0,43 % el error del selector semanal
en los mismos casos comparables. En 2023–2024 lo aumenta un 8,28 % y deja sin
predicción 49 escenarios que antes tenían resultado. Son 49 combinaciones de
observación y horizonte, correspondientes a ocho observaciones distintas, no
49 salidas independientes ni 49 días nuevos.

El efecto tampoco es constante en selección diaria: empeora un 0,59 % en el
examen reciente y mejora un 3,32 % en el anterior. Esto desaconseja una retirada
general por la pequeña mejora media de la auditoría inicial.

Esta prueba no demuestra que cada traza de lluvia sea biológicamente importante.
Demuestra que **no podemos retirar este contador dando por supuesto que todo el
Predictor mejorará**. Lluvia, suelo y contador son conceptos diferentes.

### Cobertura y ajustes realmente ejecutados

- Nueve especies instaladas inventariadas; los inputs originales contienen 17.
  Todos los perfiles y los seis algoritmos declarados de V2/V3/V4 se intentan
  cuando hay soporte. V5w/V6w se ajustan una vez y sus resultados se comparten
  exactamente entre los brazos.
- 990 intentos de ajuste final: 702 en el examen reciente, todos completados;
  288 en el anterior, 276 completados. Total: **978 ajustes finales completados**.
  Los ajustes internos para elegir parámetros V5 no se incluyen en ese contador.
- Los 12 fallos del examen anterior fueron diez calibraciones SVM sin dos
  ejemplos de cada clase y dos ajustes sparse-group que no convergieron dentro
  de sus 2.000 iteraciones vigentes. No se ampliaron límites ni se forzó su
  entrada en el selector. Los ajustes completados no registraron advertencias.
- V2/V3/V4 pudieron ajustarse en cinco especies en el examen reciente:
  Ou de reig, Aereus, Pinícola, Marzuolus y Rovelló; en dos en el anterior:
  Ou de reig y Pinícola. Que se pueda entrenar no garantiza evidencia suficiente
  para seleccionar el modelo después.
- Edulis no tiene negativos en los bloques de entrenamiento reservados de estas
  particiones; no se puede entrenar honestamente su clasificador por especie
  con ambas clases. Sí participa mediante V6 compartida, igual en ambos brazos.
  No afirmar que esta ejecución haya resuelto por separado la retirada del
  contador en Edulis. Rovelló solo aporta tres observaciones al examen reciente.
- Examen reciente: 151 observaciones de ocho especies, 1.057 escenarios por
  modo y brazo al situar cada observación en h1–h7.
- Examen anterior: 94 observaciones de nueve especies, 658 escenarios por modo
  y brazo. Los dos exámenes finales no comparten observaciones.
- Los motivos y el inventario por especie/bloque están en `preflight.json`;
  los intentos, exclusiones, configuración efectiva y observaciones de
  entrenamiento por modelo están en `fits.json`.

### Selector: comparar los mismos casos antes de mirar la cobertura

«Cambio de error» es relativo al Brier del brazo actual en los casos donde ambos
dan predicción. No son puntos porcentuales de acierto. Primero se promedian los
horizontes comparables de cada observación y después las observaciones; no se
tratan sus siete horizontes como siete observaciones independientes.

| Examen | Modo | Observaciones comparables | Escenarios comparables | Error actual | Error sin contador | Cambio del error |
|---|---|---:|---:|---:|---:|---:|
| 2025–2026 | Semanal | 101 | 641 | 0,463553 | 0,461560 | Mejora 0,43 % |
| 2023–2024 | Semanal | 33 | 181 | 0,249798 | 0,270471 | Empeora 8,28 % |
| 2025–2026 | Diario | 120 | 778 | 0,406609 | 0,408991 | Empeora 0,59 % |
| 2023–2024 | Diario | 39 | 230 | 0,248857 | 0,240606 | Mejora 3,32 % |

Las observaciones que pierden predicción no se introducen como probabilidad cero
ni se mezclan con el error de los casos comparables. Se presentan aparte:

| Examen | Modo | Predicciones actuales | Sin contador | Gana | Pierde |
|---|---|---:|---:|---:|---:|
| 2025–2026 | Semanal | 641 / 1.057 | 644 / 1.057 | 3 | 0 |
| 2023–2024 | Semanal | 230 / 658 | 181 / 658 | 0 | 49 |
| 2025–2026 | Diario | 778 / 1.057 | 778 / 1.057 | 0 | 0 |
| 2023–2024 | Diario | 232 / 658 | 230 / 658 | 0 | 2 |

En el examen anterior, la cobertura semanal pasa de 34,95 % a 27,51 %.
La cobertura baja de ese examen también refleja el entrenamiento más corto y
la evidencia insuficiente; no representa la cobertura de los modelos hoy
instalados. Hay 84 escenarios fuera de temporada en ambos brazos del examen
anterior, y ninguno en el reciente.

### Recomendaciones favorables

Umbral vigente de 0,60. Conteos de escenarios observación/horizonte; no afirmar
que sean salidas reales independientes. La etiqueta es el resultado favorable
del contrato de observación, no una medición universal de presencia de hongos.

| Examen semanal | Favorables acertados actual → sin contador | Falsos favorables | Favorables reales no recomendados | Acierto entre recomendaciones |
|---|---:|---:|---:|---:|
| 2025–2026 | 206 → 210 | 364 → 360 | 249 → 245 | 36,14 % → 36,84 % |
| 2023–2024 | 160 → 111 | 58 → 56 | 232 → 281 | 73,39 % → 66,47 % |

En el examen anterior hay dos falsas recomendaciones menos, pero también
49 recomendaciones acertadas menos: no sería razonable venderlo como mejora
por mirar solo los falsos positivos. En modo diario los aciertos favorables
pasan de 244 a 239 (reciente) y de 148 a 140 (anterior); los falsos favorables
son 333 → 333 y 62 → 63, respectivamente.

**Estos aciertos históricos no son una estimación del acierto actual de la
aplicación.** Ambos brazos se han entrenado con menos datos que los modelos
instalados para reservar evidencia y examen, y la composición de la muestra
cambia entre épocas. Los errores absolutos son elevados, especialmente en el
examen reciente; su comparación A/B permite evaluar la retirada en este ensayo,
pero no atribuir esos porcentajes a las predicciones actuales de septiembre.

### Por especie, selección semanal

| Especie | Cambio error 2025–2026 | Observaciones comparables | Cambio error 2023–2024 | Observaciones comparables |
|---|---:|---:|---:|---:|
| Ou de reig | Mejora 0,67 % | 27 | Empeora 58,76 % | 6 |
| Aereus | Mejora 5,56 % | 9 | Sin comparación disponible | 0 |
| Edulis | Sin cambio | 21 | Sin comparación disponible | 0 |
| Pinícola | Empeora 0,09 % | 41 | Mejora 0,40 % | 14 |
| Rovelló | Mejora 2,29 % | 3 | Sin cambio | 13 |

Cantharellus, Marzuolus y Morchella no obtienen resultados comparables del
selector en estos exámenes; Latitabundus no tiene observaciones de examen
recientes y tampoco obtiene resultados comparables en el anterior. No se les
asigna una mejora de cero: falta evidencia para calcularla.

El 58,76 % de Ou de reig se calcula sobre solo seis observaciones que conservan
predicción en ambos brazos; no representa a toda la especie. Además de ese
retroceso en casos comunes, hay ocho observaciones con pérdidas de cobertura.
En el examen reciente la dirección también cambia por horizonte: el semanal
mejora en h1, h2, h3 y h5, y empeora en h4, h6 y h7. Todo está desglosado en JSON.

### Qué ocurre en las pérdidas de Ou de reig / Olvan

Se reconstruyeron desde las predicciones guardadas los 49 escenarios perdidos,
sin volver a ajustar modelos. Todos corresponden a ocho observaciones de
Ou de reig/Olvan; 46 escenarios tienen etiqueta favorable y tres desfavorable.

Ejemplo `obs_20240619_0001`, 19/06/2024, h3:

1. Con contador, la evidencia decisiva es de especie en los siete horizontes.
   Quedan 16 familias comunes en la lista semanal. La prioridad por aplicabilidad
   elige V6w Smooth Shared de 30 días, aplicable 7/7; p = 0,990729 ese día.
2. Sin contador, cambian las métricas de V2/V3/V4. La selección pasa a evidencia
   del área en h2–h7 y conserva evidencia de especie en h1. La intersección de
   listas semanales se reduce a seis familias; el V6w anterior queda fuera.
3. Ninguna de esas seis pasa la aplicabilidad esa semana. Se conserva V3+
   Random Forest como familia elegida por evidencia, con cobertura 0/7; el día
   observado se abstiene conforme a la política vigente.

Las probabilidades y evidencia de V6w no cambiaron. Cambió su posibilidad de
participar en la lista común a los siete días. Este efecto del selector explica
por qué una ablación de modelos individuales no basta para decidir la retirada.
No se modificó la política de selección para rescatar esos casos durante la
auditoría; cualquier revisión de esa política es una decisión separada.

Trazas completas: `mushroom-dry-selector-20260911-earlier/lost-week-traces.json`.

#### Motivo preciso de exclusión de V6w y cómo interpretarlo

Comprobación adicional desde las mismas filas de evidencia, sin ajustes nuevos:
`mushroom-dry-selector-20260911-earlier/v6-exclusion-explanation.json`.
Se reconstruyen las auditorías de Ou de reig conservando todas sus áreas para
no alterar la evidencia global de especie al inspeccionar Olvan.

V6w Smooth Shared de 30 días sigue siendo elegible en la evidencia global de
especie en h1–h7, con probabilidades y métricas idénticas en ambos brazos. En
Olvan es elegible solo en h1–h2. En h3–h7 queda excluido por
`not_better_than_prevalence`: no supera la referencia basada en la frecuencia
de resultados favorables del entrenamiento. Por ejemplo, en h3 su Brier local
es 0,161968 frente a 0,160000 de referencia, sobre diez observaciones de cuatro
grupos. En la especie es 0,161940 frente a 0,265000 y sí supera esa referencia.
Esta diferencia entre ámbitos ya existía con contador.

La puntuación conservadora del mejor candidato local se mantiene en
0,5650002944 en ambos brazos. Lo que cambia es la mejor puntuación de especie:
en h2 y h3 pasa de 0,5655175352 a 0,5650002944. El empate favorece al área según
la regla vigente. También pasa a preferirse el área en h4–h7. Por tanto, no
debe explicarse este cambio como una mejora general de los competidores locales:
la caída de la mejor puntuación de especie cambia el ámbito decisivo y, con él,
la lista admitida. El constructor conserva la cadena del ámbito elegido, no la
unión de ambas (`mushroom_ml_reliability_audit.py`, `build_selection_catalog`).

**Que V6w pierda la selección no es malo por sí mismo.** Es correcto que gane
otro modelo si aporta mejor evidencia y resulta aplicable. Tampoco abstenerse
es un error por definición: puede evitar una predicción sin respaldo suficiente.
Los 49 escenarios perdidos describen cobertura, no 49 nuevos errores. En este
examen se pierden recomendaciones que habrían sido acertadas, pero eso no
autoriza a saltarse las reglas usando el resultado del examen. La decisión de
retirar el contador debe valorar conjuntamente el error en casos comparables,
las recomendaciones acertadas y falsas, y la cobertura. Este ensayo no permite
atribuir el efecto a una necesidad biológica del contador en V6w ni concluir que
la política de abstención esté equivocada.

### Modelos individuales, antes del selector

Media con el mismo peso por configuración/especie/contrato que tiene ambos
brazos. No es la frecuencia real de consultas. Se puntúan probabilidades crudas
antes del veto de aplicabilidad, en observaciones reservadas para examen.

| Versión | Configuraciones comparables recientes / anteriores | Cambio de error 2025–2026 | Cambio de error 2023–2024 |
|---|---:|---:|---:|
| V2 | 60 / 23 | Empeora 0,42 % | Empeora 1,46 % |
| V3 | 120 / 46 | Empeora 0,02 % | Empeora 1,42 % |
| V4 | 120 / 46 | Empeora 0,13 % | Empeora 0,74 % |

En el conjunto de esas configuraciones, empeoramiento medio de 0,15 % y 1,14 %,
respectivamente. Hay configuraciones individuales que mejoran: no se afirma
que el contador beneficie a todos los modelos. El CSV permite revisar cada una.

Esta ejecución amplía la anterior: seis algoritmos vigentes por perfil, ambos
contratos y separación en entrenamiento/evidencia/examen. La auditoría anterior
usaba una selección reducida de configuraciones, otro reparto de datos y el KNN
histórico. Su mejora descriptiva aproximada del 1 % no es directamente comparable
con estas cifras ni era una autorización para cambiar el sistema.

### Incertidumbre y límites

Remuestreo de 2.000 conjuntos de grupos de florada completos, primero promediando
los horizontes de cada observación. Para el cambio Brier semanal:

- Reciente: intervalo descriptivo [−0,004958; +0,000040].
- Anterior: [−0,002649; +0,060513].

Ambos incluyen ausencia de diferencia. El efecto medio cambia de dirección y la
pérdida de cobertura del examen anterior es observable: los datos no justifican
una retirada general. Los intervalos son condicionales a estos ajustes; no
capturan toda la incertidumbre del entrenamiento, los históricos ya se han
examinado antes y esto no es una validación prospectiva.

Se emplea una única partición de evidencia cronológica por examen, agrupada a
14 días, tanto para sellar la selección como para el catálogo de calidad del
ensayo. No se reutilizan los catálogos instalados de 7/14 días. V6 utiliza la
configuración por defecto del entrenador; V5 selecciona sus parámetros solo
dentro del entrenamiento. Esto preserva una comparación controlada y sin acceso
al examen, pero no reproduce los pesos ni todo el tuning de la instalación real.

El ensayo ejecuta entrenadores, inferencia, aplicabilidad y selector actuales
sobre features persistidas. La retargetización semanal cambia solo horizonte,
calendario y edades de eventos reconstruidas al mismo corte. No reconstruye
GIS/IDW ni recorre HTTP, worker, transporte, activación o UI. No puede justificar
una release ni reemplaza el circuito local obligatorio para un cambio operativo.

### Comprobaciones y recursos

- 35.200 comprobaciones de identidad de entradas: cada perfil reproduce
  exactamente sus features históricas al retargetizar al mismo horizonte.
  Las demás fechas conservan los datos meteorológicos del corte.
- Separación entrenamiento/evidencia/examen verificada desde IDs persistidos;
  grupos completos y margen de 14 días. Identidades y horizontes del selector
  semanal verificados desde los resultados, sin reentrenar.
- V5w/V6w idénticos entre A/B: 9.912 filas de evidencia y 792 entradas de calidad
  en el examen reciente; 4.936 filas y 472 entradas en el anterior.
- Pruebas existentes dirigidas: seis de continuidad semanal, ocho del catálogo
  de calidad y 17 de auditoría/selección de fiabilidad, todas correctas (31).
- 799.458.352 bytes de inputs reutilizados por examen, cargados por bloques.
  Ninguna reconstrucción meteorológica, copia GIS ni trabajo operativo.
  El contador final de ajustes no incluye las búsquedas internas de V5.
- Primer examen: 87,90 s sumados en ajustes/inferencia por modelo y 33,22 s de
  replay recuperado, aparte de preparación y comprobaciones. Segundo examen:
  57,88 s de recorrido completo medido. Un proceso de auditoría a la vez y un
  hilo numérico; inferencia por lotes.
- Incidencia técnica del runner: el primer catálogo rechazó un identificador
  de snapshot que no tenía formato SHA256. Se corrigió solo esa identidad y
  se continuó mediante `--replay-only` desde las predicciones guardadas.
  No se repitieron los 702 ajustes. El segundo examen completó el recorrido
  directamente. Los JSON conservan huellas de código por fase.
- SHA256 de observaciones del repositorio y locales, registro operativo,
  manifiesto instalado, SQLite y recibo activo: iguales antes/después de ambos
  exámenes y en la comprobación cruzada final. No se tocaron contenedores,
  coordinadores, modelos instalados ni HA real.

### Artefactos y reproducción

Runner: `scripts/audit-mushroom-dry-spell-selector.py`.
Verificador/resumen: `scripts/summarize-mushroom-dry-spell-selector.py`.

Directorios locales bajo `docker-data/audits/`:

- `mushroom-dry-selector-20260911-recent/`.
- `mushroom-dry-selector-20260911-earlier/`.

Cada uno contiene `preflight.json`, `result.json`, `summary.json`,
`model-comparison.csv` y `selector-comparison.csv`. Dentro de `recent/` o
`earlier/`: `fits.json`, `split.json`, evidencia y predicciones por modelo en
JSONL; `replay/` contiene los catálogos y las decisiones finales. El primero
añade `cross-checks.json` y el segundo `lost-week-traces.json`.

Huellas de decisiones finales:

- Reciente: `4e2e175851593e2eb7080a55fc674eedcf999fa5924360fe3305903f82bc9fe9`.
- Anterior: `e83422a8144ca3ae7d533e66fc8d0f0c21c022727c77dc816d95c5ba1ac78734`.

Para reproducir, usar directorios nuevos y conservar las entradas originales:

```bash
.venv/bin/python scripts/audit-mushroom-dry-spell-selector.py --fold recent --output docker-data/audits/<nuevo-reciente>
.venv/bin/python scripts/summarize-mushroom-dry-spell-selector.py docker-data/audits/<nuevo-reciente>
.venv/bin/python scripts/audit-mushroom-dry-spell-selector.py --fold earlier --output docker-data/audits/<nuevo-anterior>
.venv/bin/python scripts/summarize-mushroom-dry-spell-selector.py docker-data/audits/<nuevo-anterior>
```
