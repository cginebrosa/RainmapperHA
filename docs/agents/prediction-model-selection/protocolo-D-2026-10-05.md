# D: todo el histórico temporalmente evaluable · protocolo previo

El 05/10/2026 el usuario delegó el diseño y autorizó lanzar un agente y completar
el estudio. Este protocolo se sella antes de calcular D. Es una investigación
local aislada; no cambia modelos activos, HA, worker, coordinadores ni datos.
Los estudios A/B/C anteriores permanecen cerrados y sus resultados se reutilizan.

## Pregunta y comparación

D conserva la selección semanal nativa, umbral favorable 0,60, filtros,
suspensiones, contratos, fórmula de ranking y modelos finales de A/B de cada
corte 2024, 2025 y 2026. Amplía únicamente la evidencia anterior de ranking.
Contraste principal D−B; D−A y D−C son descriptivos secundarios. No hay búsqueda
de ventanas, pesos, umbrales, familias o reglas de elegibilidad alternativas.

Se conserva exactamente el panel B del corte; se añade 2022 desde ranking2024
cuando falte y 2023 desde ranking2025 cuando falte. Para 2015–2021 se producen
predicciones anuales con ajustes nuevos sólo cuando hacen falta. Cada ventana
entrena con todas las filas elegibles anteriores a su año, incluyendo las otras
especies del universo congelado para modelos compartidos. Se excluyen episodios
que crucen el límite y episodios con visitas a ±14 días de los límites del año.
Identidad, etiquetas y episodios provienen de la cohorte sellada de 499 casos.
Ningún caso externo se añade al ranking de su propio corte.

Preprocesado, soporte de variables, ajuste, calibración y tuning de cada año
antiguo usan exclusivamente su entrenamiento anterior. Se conserva el selector
de configuración nativo; V6 tiene la limitación ya documentada de transformar
el conjunto inicial antes de sus subdivisiones internas, siempre fuera del año
evaluado. Los modelos antiguos se usan en memoria y no se guardan duplicados.
No se reutiliza una configuración elegida con datos futuros para puntuar pasado.

Cada observación/contrato/perfil/horizonte tiene como máximo una fila, cada
estimador una probabilidad. No rellenar ausencias. Conservar causas por año,
perfil y candidato: falta de especie previa para prevalencia, ausencia de ambas
clases, soporte de calibración/KNN, inelegibilidad física, purga o fallo técnico.
Los compartidos válidos se aprovechan aunque no sea posible un modelo específico.
Los primeros casos sin predicción válida permanecen como datos de arranque para
años posteriores; no se eliminan observaciones. Fallos inesperados detienen el
lote y no se convierten en abstenciones científicas.

Los paneles históricos representan el procedimiento/familia con su configuración
elegida en cada momento, no una configuración fija: hay diferencias de tuning
entre cortes. D−B cambia edad, soporte y mezcla temporal de evidencia, no sólo n.
Se informará soporte desigual por candidato y efectos de retirar un episodio
del ranking. No convertir validación temporal en prueba de lugares nuevos.

## Utilidad, actividad y evidencia: decisiones delegadas

Primario por especie: `I4 = 100 × (TP − 4 FP) / P`, con todos los positivos reales
en P. k=4 traduce la equivalencia expresada por el usuario entre 9 aciertos/1 fallo
y 17 aciertos/3 fallos sobre las mismas oportunidades. El agente adopta la fórmula
y los mínimos siguientes como decisiones de diseño delegadas, no como frases
literales ni preferencias adicionales del usuario. No se redefine lo que los
estudios anteriores predeclararon.

Cada observación externa pesa uno: sus siete horizontes pesan 1/7. Se mantienen
116 observaciones (55 aereus, 61 caesarea), incluidas abstenciones y oportunidades
perdidas; 812 emisiones por método no son 812 visitas independientes.

Una señal **prácticamente útil** exige en el conjunto de cada especie I4 ≥5 puntos,
al menos 10 recomendaciones favorables ponderadas, detectar ≥25% de positivos
y recomendar en ≥5 episodios distintos. No convierte una recomendación en una
salida real ni estima frecuencia semanal de uso: sólo actividad en esta cohorte.
Para llamarla **estable entre campañas**, además cada corte con ≥5 positivos
debe tener ≥1 recomendación ponderada y detectar ≥10% de sus positivos; I4 debe
ser positivo en al menos dos de los tres cortes. Se mostrarán todos los valores
aunque no se cumplan los mínimos. No hay veto separado a incrementar FP: su coste
ya está incorporado en I4.

Mejora material D frente a B: ΔI4 ≥5 puntos, cumpliendo D los mínimos prácticos;
una estabilidad incumplida obliga a calificarla de señal inestable. Si D no
mejora B no se escoge otra ventana retrospectivamente. A/C se presentan igual.

Soporte mínimo para interpretar una señal: ≥10 positivos, ≥10 negativos,
≥10 episodios externos y ≥5 episodios recomendados. Bootstrap pareado de 2.000
réplicas, semilla20261005, episodios completos estratificados por año; intervalos
percentiles95%, denominadores no estimables y réplicas válidas explícitos.
Se calculan I4, TP, FP, precisión, detección y frecuencia favorable por especie,
año y horizonte. Ningún intervalo fijo de modelos cubre toda la incertidumbre
de entrenamiento. Límite inferior positivo de ΔI4 refuerza la señal exploratoria;
no se exige para mostrarla ni sustituye confirmación independiente.

Los años2024–2026 ya fueron vistos al diseñar hipótesis: todos los resultados
son retrospectivos exploratorios. Ninguno autoriza promoción. Confirmación
requiere reglas congeladas, predicciones fechadas antes de visitas nuevas,
registro también de negativos y visitas independientes de los consejos.

## Recursos y controles antes de calcular

Inventario inicial: siete ventanas2015–2021, 42 observaciones objetivo antiguas
(17 aereus,25 caesarea), 22 benchmarks reutilizados y168claves posibles por año.
Cota inicial:1.176intentos de ajuste (se omiten candidatos sin casos evaluables),
3.696filas antiguas de evidencia antes de exclusiones y812emisiones nuevas D.
No copias de benchmarks, meteorología, geografía ni modelos finales.
Los lotes históricos guardados midieron23–31s por168ajustes y285–583s por corte
con varios selectores. Estimación preliminar conservadora: menos de20min de
cálculo nuevo y150MiB de salidas; no es una medición del nuevo estudio.

Techo nuevo independiente:60min de cálculo supervisado,512MiB de salidas nuevas,
8GiB RSS por proceso, un solo proceso de cálculo y un hilo BLAS/OpenMP. No se
aumentarán límites. Preparar y verificar guardas de escritura, red, cardinalidad,
solapamiento y reutilización antes del lote. Registrar fallos, tiempo y RSS reales.
Si no cabe se informa la viabilidad concreta, sin recortar años por conveniencia.

Evidencia privada nueva: `tmp/prediction-model-selection/D-2026-10-05/`.
Scripts nuevos: `scripts/prediction_model_selection_d/`. Se sellan protocolo,
entradas y código; los originales se verifican al finalizar. El informe público
no incluye identificadores de observaciones ni localizaciones privadas.
