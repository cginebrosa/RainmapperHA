# D: todo el histórico evaluable · resultados del 05/10/2026

**Estudio completado. D no cumple el criterio de utilidad fijado para diseñar
esta evaluación.** Se recuperaron predicciones válidas para 40 de las 42
observaciones objetivo anteriores a 2022; no se han descartado datos antiguos
por conveniencia. Los primeros casos de cada especie permanecen como datos de
arranque para los modelos de años posteriores.

- **Aereus:** D reduce fallos respecto a B, pero también detecta menos oportunidades.
  Su utilidad sigue siendo negativa y no mejora de forma estable entre campañas.
- **Caesarea:** D detecta más oportunidades que B, a costa de demasiados fallos
  con el coste elegido. El buen resultado de 2024 no se mantiene en 2025 ni 2026.
- **No se promueve ninguna alternativa ni se cambia HA.** B de caesarea conserva
  una señal conjunta interesante, pero queda sin consejos favorables en 2025 y
  su incertidumbre sigue siendo amplia. Ninguna opción supera conjuntamente
  utilidad práctica y estabilidad.

La ventana óptima de años sigue sin demostrarse. El resultado describe esta
forma concreta de acumular evidencia para la selección nativa; no justifica
eliminar observaciones antiguas ni escoger retrospectivamente otra ventana.

## Qué se comparó y qué se fijó antes de D

| Opción | Evidencia anterior para ordenar candidatos | Selección |
|---|---|---|
| A | Un año | Semanal nativa |
| B | Dos años | Semanal nativa |
| C | Los mismos dos años de B | Diaria |
| D | Todos los años temporalmente evaluables | Semanal nativa |

La selección semanal nativa puede recurrir a cadenas diarias cuando no encuentra
una familia común. D conserva el umbral favorable 0,60, filtros, fórmula nativa,
contratos temporales y modelos finales de A/B. No se ha modificado el coordinador,
worker, código productivo ni modelos operativos.

A es la referencia experimental con ranking del año anterior. Los modelos de
estos cortes retrospectivos no son una evaluación directa del artefacto instalado
en HA ni del catálogo operativo 70/30.

El usuario delegó el diseño y la ejecución. El [protocolo previo](protocolo-D-2026-10-05.md)
fijó `I4 = 100 × (TP − 4 FP) / P`, donde P incluye todos los favorables reales,
también los no detectados. k=4 traduce la equivalencia expresada entre 9 aciertos
con 1 fallo y 17 aciertos con 3 fallos, sobre las mismas oportunidades.

Los mínimos son **decisiones de diseño delegadas**, no nuevas preferencias
literales atribuidas al usuario: I4 ≥5 puntos, al menos 10 consejos favorables
ponderados, detectar ≥25% de oportunidades y recomendar en ≥5 episodios.
Para estabilidad: ≥1 consejo favorable y detección ≥10% en cada campaña con
≥5 positivos, además de I4 positivo en al menos dos campañas. Se pide ≥10
positivos, ≥10 negativos y ≥10 episodios externos para interpretar una señal.
La mejora material principal D−B requiere ≥5 puntos y que D sea útil; no hay un
veto separado a aumentar FP, pues su coste ya está dentro del índice.

## Resultados comparables

Las cifras corresponden a 116 observaciones distintas: 55 aereus, con 36
favorables reales, y 61 caesarea, con 35. Cada observación pesa uno en total:
sus siete horizontes pesan 1/7 cada uno. Por eso los consejos, aciertos y fallos
pueden ser fraccionarios; 812 emisiones por método no son 812 visitas.

| Especie | Opción | Consejos favorables | Aciertos TP | Fallos FP | Precisión | Oportunidades detectadas | Frecuencia favorable | I4 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Aereus | A | 25,29 | 17,57 | 7,71 | 69,5% | 48,8% | 46,0% | -36,90 |
| Aereus | B | 21,00 | 12,86 | 8,14 | 61,2% | 35,7% | 38,2% | -54,76 |
| Aereus | C | 25,57 | 16,71 | 8,86 | 65,4% | 46,4% | 46,5% | -51,98 |
| Aereus | D | 16,57 | 11,00 | 5,57 | 66,4% | 30,6% | 30,1% | -31,35 |
| Caesarea | A | 15,29 | 8,71 | 6,57 | 57,0% | 24,9% | 25,1% | -50,20 |
| Caesarea | B | 15,57 | 13,14 | 2,43 | 84,4% | 37,6% | 25,5% | 9,80 |
| Caesarea | C | 27,14 | 20,14 | 7,00 | 74,2% | 57,6% | 44,5% | -22,45 |
| Caesarea | D | 23,00 | 16,86 | 6,14 | 73,3% | 48,2% | 37,7% | -22,04 |

La frecuencia favorable es la proporción de estas observaciones con consejo
favorable, promediada entre horizontes. No estima consejos semanales de uso real.
I4 son puntos de utilidad, no porcentaje de acierto. Con este coste, una utilidad
positiva exige precisión superior al 80%; eso por sí solo tampoco garantiza
cantidad suficiente ni evidencia fiable.

D supera los mínimos conjuntos de cantidad y detección en ambas especies, pero
falla el mínimo de utilidad. Aereus D también falla la actividad de 2026: sólo
detecta el 9,5% de sus positivos. Caesarea D no emite ningún consejo favorable en
2026: sus 105 emisiones son 54 desfavorables y 51 abstenciones, no silencio total.

### Campañas de D

| Especie | Campaña | Consejos favorables D | TP | FP | Precisión | Detección | I4 D | I4 B |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Aereus | 2024 | 3,71 | 2,00 | 1,71 | 53,8% | 16,7% | -40,48 | -41,67 |
| Aereus | 2025 | 11,57 | 8,14 | 3,43 | 70,4% | 54,3% | -37,14 | -101,90 |
| Aereus | 2026 | 1,29 | 0,86 | 0,43 | 66,7% | 9,5% | -9,52 | 6,35 |
| Caesarea | 2024 | 12,43 | 11,86 | 0,57 | 95,4% | 84,7% | 68,37 | 21,43 |
| Caesarea | 2025 | 10,57 | 5,00 | 5,57 | 47,3% | 38,5% | -132,97 | 0,00 |
| Caesarea | 2026 | 0,00 | 0,00 | 0,00 | NE | 0,0% | 0,00 | 5,36 |

Caesarea D tiene precisión del 95,4% en 2024, pero cae al 47,3% en 2025. Acumular
los tres años oculta esa diferencia. B de caesarea tiene I4 conjunto +9,80 y cumple
los mínimos prácticos conjuntos, pero en 2025 todas sus emisiones se abstienen;
no satisface la estabilidad. Su intervalo de I4 es [−40,72; +40,62].

### Incertidumbre y contraste principal

| Especie | I4 D, intervalo 95% | ΔI4 D−B | Intervalo 95% de ΔI4 |
|---|---:|---:|---:|
| Aereus | [-100,59; 5,31] | 23,41 | [-17,54; 73,98] |
| Caesarea | [-119,44; 36,36] | -31,84 | [-120,11; 25,98] |

Los intervalos de D−B incluyen cero en ambas especies. Aereus presenta una
mejora puntual relativa, pero D sigue con utilidad negativa. Caesarea presenta
un empeoramiento puntual frente a B; la incertidumbre impide cuantificarlo con
precisión. Los secundarios D−A y D−C, junto con TP, FP, precisión, detección y
frecuencia por horizonte, están completos en el JSON de análisis.

Bootstrap pareado de 2.000 réplicas, semilla 20261005, remuestreando episodios
completos dentro de cada campaña. Hay 20 episodios externos de aereus y 31 de
caesarea; no se suman episodios compartidos como evidencia independiente.
Los intervalos conjuntos tienen 2.000 réplicas válidas; algunas particiones por
año pierden réplicas por denominador cero, con el recuento explícito en el JSON.
Los modelos quedan fijos, por lo que no se recoge toda la incertidumbre del
aprendizaje. La comparación temporal tampoco demuestra generalización a lugares
nuevos. Estos años ya se habían visto al diseñar hipótesis: la evidencia es
retrospectiva exploratoria, no una confirmación independiente.

## Años antiguos realmente aprovechados

Se generaron predicciones anuales usando únicamente entrenamiento anterior al
año evaluado, incluyendo las otras especies admitidas para los modelos
compartidos. Preprocesado, soporte y tuning excluyeron el año evaluado. Se
mantuvieron episodios comunes entre especies y purga de 14 días en fronteras
anuales; se verificó la separación también en los ajustes compartidos.

| Año | Aereus: casos / con alguna predicción válida | Caesarea: casos / con alguna predicción válida |
|---|---:|---:|
| 2015 | 0 / 0 | 1 / 0 |
| 2016 | 1 / 0 | 1 / 1 |
| 2017 | 0 / 0 | 1 / 1 |
| 2018 | 0 / 0 | 1 / 1 |
| 2019 | 2 / 2 | 4 / 4 |
| 2020 | 4 / 4 | 6 / 6 |
| 2021 | 10 / 10 | 11 / 11 |
| **Total** | **17 / 16** | **25 / 24** |

La primera observación de cada especie carecía de historia previa de esa especie
para calcular la prevalencia de referencia exigida por el ranking nativo. Ambas
se conservaron para entrenar años posteriores. Se aprovechó la evidencia de
modelos compartidos aun cuando faltaban ambas clases para un modelo específico.
«Alguna predicción» no significa todos los candidatos: cada uno mantiene sus
faltas de soporte, calibración, KNN, física o convergencia, sin rellenar huecos.
Los GBIF etiquetados `normal` siguen siendo favorables, sin penalización por origen.

De 1.176 combinaciones anuales posibles, el inventario encontró 306 ajustes con
soporte inicial; 294 terminaron válidamente. Se ajustaron sólo modelos históricos
necesarios para producir estas predicciones, en memoria. No se repitieron los
entrenamientos cerrados ni se cambiaron los modelos finales. Un intento temprano
se detuvo ante una no convergencia cuyo mensaje no estaba reconocido; se conservó
su evidencia y se corrigió únicamente la clasificación de esa ausencia individual.
No se aumentaron iteraciones ni se descartaron predicciones de otros estimadores.

| Corte externo | Casos distintos en ranking D: aereus / caesarea | Filas perfil/contrato/horizonte |
|---|---:|---:|
| 2024 | 30 / 36 | 5.800 |
| 2025 | 47 / 56 | 9.032 |
| 2026 | 70 / 82 | 13.344 |

Cada corte conserva exactamente sus paneles B y añade sólo años anteriores no
duplicados. Los recuentos por candidato son menores y desiguales. La configuración
de una familia cambia entre algunos años: se evalúa el procedimiento histórico,
no un artefacto fijo. La comparación cambia soporte, antigüedad y mezcla temporal.
V6 conserva la limitación previa de preprocesar el entrenamiento inicial antes
de sus subdivisiones internas, siempre fuera del año evaluado.

La estabilidad del ranking tampoco es automática: al omitir un episodio, el
ganador de cada horizonte se mantiene en el 68,8% de las omisiones para aereus
2024, 32–48% en 2025 y 62,5–100% en 2026. Para caesarea, los rangos son 28,6–57,1%,
44,8–96,6% y 30–97,5%, respectivamente. Son diagnósticos de selección; no tasas de
acierto ni una garantía de utilidad.

## Dos precisiones metodológicas de la ejecución

**Meteorología común.** El manifest utilizado por los estudios antiguos ya no
estaba disponible; CURRENT había cambiado. También habían cambiado observaciones
y áreas operativas, que no se consumieron: se usaron los snapshots privados y
benchmarks originales. Se selló un [anexo previo](protocolo-D-meteorologia-comun-2026-10-05.md)
y se ejecutó un contraste nuevo A/B/C/D sobre un único snapshot meteorológico
local actual, sin descargas. Las inferencias A/B/C son controles de ese contraste;
los resultados antiguos permanecen intactos y no se mezclan con D nueva.

En los 812 casos/horizonte de cada A/B/C, **ninguna decisión cambió** respecto a
los resultados guardados. En 2026 cambió una probabilidad de A y una de B, sin
cambiar sus consejos; las demás coinciden. El histórico revisado no acredita que
la meteorología estuviera disponible exactamente así al emitir en el pasado.

**Cambio de ruta nativa.** El primer intento de 2025 se detuvo antes de guardar
una emisión completa: B de aereus usaba fallback diario con lotes mixtos de
365 días y física, mientras D encontraba una familia semanal V3/core con 90 días
sin física. El [anexo de alcance causal](protocolo-D-ruta-nativa-2026-10-05.md)
se fijó antes del reintento, conservando el fallo y el corte 2024 ya terminado.
No se cambiaron el índice, mínimos, modelos, filtros ni probabilidades.

El contraste mide el efecto completo de ampliar la historia en el procedimiento
nativo, incluyendo la ruta y preparación que éste produce. No aísla un efecto
puro de más historia manteniendo fijas las matrices meteorológicas de todos los
candidatos. Sólo la rama deducida de los catálogos «B diario por fallback, D
semanal» admite esa diferencia nativa registrada; el resto conserva comprobación
estricta y B/C siempre mantiene paridad. Se afectan 161 emisiones de aereus en
2025 y 98 en 2026, con 346 y 392 peticiones compartidas respectivamente. Caesarea
y 2024 no entran en esa rama. No se forzaron entradas artificiales para ocultarla.

## Evidencia, recursos y cierre

Evidencia privada: `tmp/prediction-model-selection/D-2026-10-05/`.

- `inventory.json`: protocolo y 763 entradas selladas, soporte anual, cambios
  operativos no consumidos y snapshot antiguo ausente.
- `historical-v2/`: probabilidades, ajustes y causas por caso/candidato.
  `historical/` conserva el intento fallido.
- `fold-2024/`, `fold-2025/`, `fold-2026/`: catálogos D y procedencia de cada año.
- `common-weather/`: sello común y emisiones A/B/C/D; 2025 completo está en
  `fold-2025-retry/` y su primer intento fallido permanece en `fold-2025/`.
- `analysis-common/results.json`: análisis final comparable, intervalos, soporte,
  estabilidad, deriva de A/B/C y efectos de ruta. `analysis/results.json` conserva
  la etapa descriptiva anterior, en la que D puntual aún no estaba estimada.
- `runs/`, `source-archive/` y el recibo final: versiones exactas, hashes,
  presupuesto acumulado y verificación de entradas.

Límites conservados: 60 minutos de cálculo nuevo, 512 MiB de salidas, 8 GiB RSS,
un proceso de cálculo y un hilo nativo. El sandbox impedía consultar `ps`; se
implementó supervisión del pico RSS del propio proceso con `getrusage`, latido
cada 0,5 s y bloqueo de subprocesos, red y escrituras externas. El padre vigila
memoria, tiempo y tamaño. Se conservaron las guardas de recursos y no se amplió
el presupuesto.

Consumo medido de todos los lotes, incluidos intentos fallidos y verificación:
1.281,93 segundos (21 min 21,93 s), pico RSS 684.752.896 bytes (653 MiB) y
aproximadamente 144 MiB de salidas. El recibo final conserva el tamaño exacto
antes de escribirse. Se verificaron 763 entradas sin cambios y 2.819 referencias
a fuentes archivadas; también la exclusión temporal y de episodios en los 294
ajustes válidos y las 812 emisiones de cada método.

Ocho pruebas dirigidas y las sondas de aislamiento pasaron. Se conservan los
fallos y fuentes originales. No se lanzaron precálculos, geografía, limpiezas,
releases ni operaciones en HA/worker. No hay una alternativa autorizada para
promoción: la evidencia futura tendría que registrar predicciones antes de las
visitas, incluir negativos y recoger visitas independientemente del consejo.
