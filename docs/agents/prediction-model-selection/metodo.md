# Método propuesto para estudiar la selección del ganador

**Método ejecutado: [protocolo cerrado](protocolo-ejecucion-2026-10-04.md) y
[resultados del 04/10/2026](resultados-2026-10-04.md).** Las
hipótesis proceden del [estudio de umbrales](../prediction-thresholds/resultados-2026-10-03.md).
Este documento conserva el planteamiento previo; las decisiones numéricas y
correcciones técnicas selladas se encuentran en los protocolos enlazados desde el README.

## 1. Reconstruir la decisión y sus límites

Revalidar en código y configuración el recorrido: evidencia de evaluación →
catálogo/ranking por especie y horizonte → candidatos del punto → filtros →
resolución semanal → recomendación. Separar ganador del catálogo, ganador del
punto e interpretación final. Registrar cuándo cambia una familia y por qué.

Comprobar por separado casos sin suficiente evidencia, probabilidades poco útiles,
dominio no aceptable, geografía/temporada y errores técnicos. En el estudio anterior
`brier_not_better_than_prevalence` también cubría evidencia insuficiente: no llamar
mal rendimiento numérico a todos los vetos que llevan ese código.

La auditoría debe identificar si domina una familia por su evidencia histórica,
por su disponibilidad/cobertura o por descarte de alternativas. No inferir una
preselección incondicional de la frecuencia del ganador.

## 2. Revalidar datos y clasificar qué pueden demostrar

Comprobar hashes antes de reutilizar cohorte, meteorología, geografía, contratos
y política. No volver a generar las entradas del primer estudio por rutina.
Los originales y su carpeta privada quedan conservados.

Clasificar las observaciones en histórico ya utilizado para diseñar este estudio,
registros posteriores si realmente existen y evidencia prospectiva aún no recogida.
No asumir que las últimas descargas contienen casos nuevos independientes. Para
el modelo instalado, comprobar pertenencia a todos los ajustes y decisiones que
se pretendan evaluar; el antiguo 30 % no es una reserva frente al ajuste final.

Las particiones externas 2024–2026 ya vistas sólo permiten exploración para estas
nuevas hipótesis. Un nuevo remuestreo o una frontera diferente no crea confirmación.
Informar también si los setales son conocidos: una separación temporal no demuestra
transferencia espacial a lugares nuevos.

## 3. Comparación pequeña con cambios identificables

**A:** procedimiento actual completo revalidado, reconstruido con modelos y
ranking propios del corte. No usar el catálogo productivo para elegir en casos
que ya intervinieron en su construcción.

**B:** conservar fórmula del ranking, filtros, política y resolución semanal de A.
Cambiar la obtención de evidencia: reunir predicciones de varias ventanas pasadas,
cada una emitida por modelos entrenados exclusivamente con datos anteriores y
separados por episodios. Todas esas ventanas deben preceder la evaluación del
corte. No reutilizar predicciones de ajuste como si fueran validación.

Cada observación/horizonte/modelo aporta a ese ranking una sola predicción válida;
evitar contabilizar repetidamente una visita al acumular ventanas. El soporte
se cuenta en observaciones y episodios reales, no en siete filas por visita.
No bajar el mínimo de soporte ni mezclar horizontes para superarlo artificialmente.
Mostrar también el envejecimiento de esa evidencia y las diferencias de soporte
entre familias; no elegir sólo el subconjunto donde cada candidato acierta más.

**C:** mismos modelos, evidencia, ranking, filtros y umbral que B; resolver la
familia para cada día. B−A mide el procedimiento de construcción de evidencia;
C−B mide la decisión diaria. Presentar además C−A con la advertencia de que cambia
dos componentes. La elección diaria puede aumentar cobertura y también variación
y errores; no presuponer que mejora.

Mantener el umbral favorable de la referencia, sin una nueva búsqueda de umbrales.
El contexto del punto se usa para validez y diagnósticos predefinidos; entrenar un
selector contextual o un ensemble ampliaría este alcance y exigiría justificarlo
con soporte suficiente. No se incorpora a esta primera matriz.

## 4. Cerrar temporalidad y ajustes antes de comparar

El inventario decidirá las fechas exactas y la viabilidad de hasta tres cortes;
no copiar automáticamente los del primer estudio. Justificar purgas, agrupación
de visitas entre especies y separación de horizontes. Establecer el número máximo
de ventanas internas según soporte y coste antes de ver qué variante gana.

Dentro de cada corte, mantener preprocesamiento, soporte, tuning y calibración
fuera de los casos con que se mide el ranking. Reconstruir las predicciones
temporales de B cuando los artefactos existentes no cumplen esa exclusión. El
modelo final para evaluar A/B/C podrá reajustarse con todos los datos de desarrollo
permitidos, conservando reglas y ranking cerrados; el externo permanece fuera.

Compartir los modelos finales entre variantes cuando sus entradas y ajustes son
idénticos. Si la comparación exige distinto entrenamiento, declararlo: sería una
diferencia adicional y no un efecto puro de selección. Mantener todos los cortes
viables, no escoger después sólo los años que favorecen una alternativa.

Para cada emisión histórica, reproducir el corte meteorológico del contrato sin
información futura. Distinguir histórico revisado de datos realmente disponibles
entonces. Para B semanal, materializar los siete días completos; siete horizontes
de una observación no forman una semana.

## 5. Reutilizar sin sesgar el universo de candidatos

Las trazas del estudio de umbrales son **perezosas**: contienen los candidatos que
su resolución necesitó materializar. No forman una tabla exhaustiva de todas las
familias ni bastan para simular cualquier selector nuevo. La ausencia de un modelo
en esa traza no significa que fallara ni que estuviera suspendido.

La revisión del código identificó además que desactivar `lazy_families` no suprime
por sí solo la agregación semanal. Una variante diaria requiere verificar esa
semántica en el arnés, no sólo cambiar un booleano. Referencia de la revisión:
[mushroom_map_prediction.py](../../../rainmapper_core/mushroom_map_prediction.py#L62).

Definir el universo de candidatos desde los contratos y particiones, antes de
conocer el resultado del punto. Inventariar los huecos del panel requerido para
A/B/C y calcular sólo los necesarios, conservando también fallos y abstenciones.
No ejecutar todos los modelos sobre toda la geografía. Medir cardinalidad y coste
del panel acotado antes de materializarlo.

Una reutilización exige iguales entradas, corte meteorológico, contexto del punto,
contrato, especie, horizonte, preprocesamiento, artefacto y política pertinente.
Referenciar cachés por identidad y hash; no compartirlas entre cortes por coincidir
el nombre de la familia. Separar inferencia de recomendación cuando el cambio de
selector permita reutilizar sólo una de ellas.

## 6. Métricas, estabilidad y decisión

Por especie, corte y horizonte: matriz observado favorable/desfavorable frente a
consejo favorable/desfavorable/abstención; falsos favorables, verdaderos favorables,
oportunidades perdidas, precisión favorable, cobertura y soporte. Denominador cero
es no estimable. Cada observación pesa en total 1 al resumir sus siete horizontes.

Comparaciones pareadas B−A y C−B, con remuestreo de episodios completos y
estratificación temporal. No interpretar un intervalo condicionado a modelos ya
ajustados como toda la incertidumbre de aprender y seleccionar. Informar réplicas
con denominador válido y el soporte de los grupos; cero errores no significa
riesgo cero. El protocolo fijará semillas y repeticiones antes del cálculo.

Medir concentración de familias ganadoras, cambios entre días y campañas,
dependencia del ranking de unos pocos episodios y causas de exclusión. La
estabilidad debe evaluarse sin escoger reglas por su rendimiento en la prueba.
Calibración/Brier se presentan como diagnósticos del ámbito donde exista salida,
no como sustitutos de utilidad o cobertura del mapa completo.

Antes de comparar, fijar mínimos de oportunidades detectadas, soporte, cobertura
y mejora práctica. Presentar el intercambio entre falsos favorables evitados y
aciertos retirados; no inventar un coste numérico del usuario. Controles de
siempre abstenerse o siempre desfavorable impiden premiar la inutilidad.

Si una variante parece mejor sólo en el histórico reutilizado, clasificarla como
**candidata exploratoria**. Proponer confirmación con predicciones fechadas antes
de futuras salidas, reglas identificadas, negativos explícitos y condición de
cierre previamente fijada. No activar modelos ni registrar automatizaciones
prospectivas como efecto secundario de redactar esta propuesta.
