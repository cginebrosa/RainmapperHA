# Resultado de la primera investigación local

**Conclusión: no hay evidencia suficiente para activar el umbral conservador
ensayado.** En aereus evita algunas recomendaciones favorables erróneas, pero
retira bastantes aciertos y no mejora la proporción de recomendaciones acertadas.
En caesarea, la regla de desarrollo mantiene el umbral original en los tres cortes:
la variante coincide con la referencia. Esto no acredita que el sistema actual
sea óptimo; tampoco valida directamente los modelos instalados el 28/09.

Estudio completado según [goal.md](goal.md) y el
[protocolo cerrado](protocolo-ejecucion-2026-10-03.md). Se comparan selección y
consejo actuales con modelos experimentales propios de cada corte (A), frente
al mismo procedimiento con un umbral favorable elegido sólo en desarrollo (B).
No se han instalado estos modelos ni modificado el mapa, HA real o el worker.

Las letras A/B son propias de este estudio. Aquí B cambia el umbral; en el
[informe de selección](../prediction-model-selection/resultados-2026-10-04.md)
B cambia la evidencia del ranking. Para caesarea, A y B de umbrales coinciden;
la mejora de B comentada en el otro informe corresponde a otro procedimiento.

Las [tablas completas](tablas-2026-10-03.md) incluyen matrices por año y horizonte,
curvas de desarrollo, ganadores e intervalos. Código, comandos y evidencias privadas
se describen en [reproducibilidad.md](reproducibilidad.md).

## Datos utilizados y significado de los años

Se utilizaron 499 observaciones elegibles del ámbito compartido de diez especies.
De las dos especies objetivo hay 184: 86 aereus y 98 caesarea. Los `normal`, incluidos
GBIF, se mantienen favorables conforme a la definición acordada.

**Los anteriores a 2024 sí se procesaron:** 31 aereus y 37 caesarea, con registros
desde 2016 y 2015, respectivamente. Preparan los modelos y las reglas del primer
corte. No son observaciones descartadas.

| Prueba externa | Ajuste inicial | Ranking | Elección B | Reajuste antes del externo |
|---|---|---|---|---|
| 2024 | Hasta 2021 | 2022 | 2023 | Datos permitidos hasta 2023 |
| 2025 | Hasta 2022 | 2023 | 2024 | Datos permitidos hasta 2024 |
| 2026 | Hasta 2023 | 2024 | 2025 | Datos permitidos hasta 2025 |

El reajuste conserva configuración, ranking y umbral cerrados. Cada externo queda
fuera de sus ajustes y decisiones. Un externo de un año puede convertirse en
desarrollo del siguiente; no se vuelve a contar como prueba externa distinta.
No se emplea el modelo productivo, que ya vio casi todo este histórico.

| Especie | Externos positivos / negativos | Observaciones | Grupos técnicos | Áreas |
|---|---:|---:|---:|---:|
| Aereus | 36 / 19 | 55 | 20 | 8 |
| Caesarea | 35 / 26 | 61 | 31 | 19 |

Son **116 observaciones externas y 812 emisiones**, siete por observación. Los
grupos se comparten entre especies: hay 32 grupos únicos en conjunto, no 51
independientes. Se unen visitas próximas de una misma área, incluso entre especies.
No es una prueba de setales completamente nuevos ni de independencia biológica.

Todos los contratos retienen las 86 observaciones de aereus; V3 físico retiene
94/98 de caesarea y los demás 98. Sus cuatro exclusiones son favorables. Se conservan
los filtros propios del contrato y todos los casos externos en la evaluación del
mapa, incluyendo abstenciones: no se limita la prueba a puntos que dieron consejo.

## Qué ocurrió al aumentar el umbral

| Especie | Umbral B para 2024 | Para 2025 | Para 2026 |
|---|---:|---:|---:|
| Aereus | 0,60 | 0,75 | 0,60 |
| Caesarea | 0,60 | 0,60 | 0,60 |

En 2024 faltaba soporte de desarrollo para cambiarlo. En los demás casos sin
cambio no hubo mejora estricta admisible. Los mínimos de utilidad se fijaron antes
de calcular; no son una equivalencia de costes atribuida al usuario. Retirar un
favorable lo convierte en abstención, nunca en una afirmación desfavorable.

Promedio de los siete horizontes, con peso total 1 por observación. Cada celda
muestra **cantidad / total correspondiente → porcentaje**. Los decimales proceden
del promedio y los porcentajes se calculan antes de redondear. «Perfecto» es una
referencia ideal, no un resultado obtenido.

| Especie | Método | TP: favorables detectados / favorables reales | FP: falsos favorables / desfavorables reales | Precisión: aciertos / consejos favorables | Cobertura: consejos / observaciones | Oportunidades perdidas / favorables reales |
|---|---|---:|---:|---:|---:|---:|
| Aereus | A | 11,29 / 36 → 31,3% | 3,43 / 19 → 18,0% | 11,29 / 14,71 → 76,7% | 20 / 55 → 36,4% | 24,71 / 36 → 68,7% |
| Aereus | B | 7,29 / 36 → 20,2% | 2,29 / 19 → 12,0% | 7,29 / 9,57 → 76,1% | 14,86 / 55 → 27,0% | 28,71 / 36 → 79,8% |
| Aereus | **Perfecto (ideal)** | 36 / 36 → 100,0% | 0 / 19 → 0,0% | 36 / 36 → 100,0% | 55 / 55 → 100,0% | 0 / 36 → 0,0% |
| Caesarea | A y B | 13,43 / 35 → 38,4% | 2,57 / 26 → 9,9% | 13,43 / 16 → 83,9% | 20,57 / 61 → 33,7% | 21,57 / 35 → 61,6% |
| Caesarea | **Perfecto (ideal)** | 35 / 35 → 100,0% | 0 / 26 → 0,0% | 35 / 35 → 100,0% | 61 / 61 → 100,0% | 0 / 35 → 0,0% |

La cobertura restante es abstención; **no equivale a acertar un desfavorable**.
Los porcentajes describen esta cohorte retrospectiva, no una garantía de acierto
en futuras salidas ni la calibración del IFF instalado.

### Cómo leer las columnas

- **TP: favorables detectados / favorables reales.** El sistema dijo favorable y
  la observación fue favorable. El denominador incluye todas las observaciones
  realmente favorables. Su porcentaje es la detección de positivos: más es mejor.
- **FP: falsos favorables / desfavorables reales.** El sistema dijo favorable,
  pero la observación fue desfavorable. Se divide entre todas las observaciones
  realmente desfavorables. Es el error que el usuario quiere penalizar más:
  menos es mejor.
- **Precisión: aciertos / consejos favorables.** De todos los consejos favorables
  emitidos, cuántos acertaron. El denominador es TP + FP. Mide la fiabilidad de
  recomendar favorable: más es mejor. Sin consejos favorables es no estimable
  (`0 / 0 → NE`), no un 100% de acierto.
- **Cobertura: consejos / observaciones.** En cuántas observaciones se emitió
  consejo favorable o desfavorable, sea acertado o erróneo. El resto es abstención.
  Una cobertura mayor sólo es útil si acompaña a una calidad suficiente.
- **Oportunidades perdidas / favorables reales.** Observaciones realmente favorables
  en las que se aconsejó desfavorable o se abstuvo. Su denominador es el mismo
  que el de TP; ambos porcentajes suman 100%. Menos oportunidades perdidas es mejor.

La **precisión** mide cuánto acertamos cuando recomendamos favorable; la
**detección** mide qué parte de las oportunidades existentes encontramos. Se
puede tener mucha precisión y detectar muy pocas oportunidades por recomendar
muy pocas veces. Abstenerse no cuenta como acertar un desfavorable.

Los recuentos se promedian entre siete antelaciones. Una observación favorable
que recibe consejo favorable en cuatro de ellas aporta `4 / 7 = 0,57` TP; si
lo recibe en las siete, aporta 1 TP. Por eso aparecen decimales. El máximo TP
es 36 para aereus y 35 para caesarea, sus observaciones realmente favorables.
La fila **Perfecto (ideal)** detecta todos esos favorables, aconseja correctamente
desfavorable en los demás casos y no se abstiene, en ninguno de los horizontes.

### Interpretación del cambio en aereus

El cambio real se concentra en **aereus 2025**: sus 23 observaciones externas
contienen 15 favorables y ocho desfavorables. Los falsos favorables pasan de
**3 / 8 → 37,5%** a **1,86 / 8 → 23,2%**; los favorables detectados, de
**9,43 / 15 → 62,9%** a **5,43 / 15 → 36,2%**. Son promedios entre horizontes. En emisiones brutas,
se retiran ocho falsos favorables y 28 verdaderos favorables; no son 36 salidas
independientes. La variante conserva sólo el 57,6 % de los aciertos favorables
de A en ese corte, aunque en desarrollo exigíamos conservar al menos el 80 %.

El intercambio observado equivale a perder 3,5 recomendaciones acertadas por
cada falsa favorable evitada. Sin una relación de costes acordada no puede
declararse que cualquier reducción de falsos favorables compense esa pérdida.
Además, la precisión favorable baja ligeramente, 75,9 % → 74,5 % en ese corte.
**No recomiendo promover B con estos datos.** El experimento no ha contrastado
otras reglas de ranking, selección diaria o conjuntos de modelos.

## Incertidumbre y cobertura

Se realizaron 2.000 remuestreos de grupos completos, estratificados por corte y
pareados entre A/B. Los modelos, ranking y umbrales permanecen fijos en ellos;
no incorporan incertidumbre de volver a entrenarlos y seleccionarlos.

- Aereus A: falsos entre consejos favorables, 23,3 %, intervalo 95 % **2,6–39,4 %**.
  B: 23,9 %, intervalo **3,2–53,8 %**. Diferencia B−A: **−5,7 a +15,3 puntos**.
- La detección de favorables de aereus baja 11,1 puntos con B; intervalo de la
  diferencia **−19,9 a −4,5 puntos**. La reducción agregada de falsos favorables
  equivalentes es 1,14, con intervalo de diferencia **−2,57 a 0,00**.
- Caesarea A/B: falsos entre consejos favorables, 16,1 %, intervalo **2,8–41,0 %**.
  La igualdad A/B es consecuencia de haber elegido el mismo umbral; no prueba que
  umbrales alternativos sean equivalentes o que el riesgo sea nulo.

Estas tasas agregadas tienen denominador válido en las 2.000 réplicas. Los
resultados por corte/horizonte guardan su número de réplicas válidas en el JSON;
una precisión sin recomendaciones es indefinida, nunca 100 %. Las tablas incluyen
también un límite exploratorio por grupo, cuya unidad es «algún falso favorable
en un episodio recomendado», distinta de la precisión por emisión.

Hay una limitación operativa relevante: **A se abstiene en todos los casos de
aereus 2024 y caesarea 2025**. Sus ceros de falsos favorables no indican éxito.
El soporte de ranking de esos cortes era de sólo seis y cuatro observaciones,
respectivamente. Sus catálogos califican toda la evidencia como insuficiente:
el filtro exige al menos ocho para reconocer una mejora sobre la prevalencia.
En 98 emisiones de aereus y 175 de caesarea se llegó a inferir el target, pero
todos sus candidatos fueron vetados por esa evidencia insuficiente, aunque sus
Brier numéricos fueran mejores que la referencia. El código del veto
`brier_not_better_than_prevalence` engloba aquí **falta de soporte**, no prueba de
un Brier peor. Las otras 21 emisiones de aereus se abstienen por temporada (14)
o hospedadores desconocidos (7); las otras siete de caesarea por hospedadores
desconocidos. No se observaron fallos de carga ni incompatibilidad de modelos.
Esta explicación técnica no valida biológicamente el filtro GIS ni acredita ese
comportamiento en el modelo instalado. Fuentes:
[catálogo de calidad](../../../rainmapper_core/mushroom_ml_quality_catalog.py#L282)
y [filtros del comparador](../../../rainmapper_core/mushroom_ml_multiversion_comparison.py#L530).
No se relajaron filtros a posteriori para obtener una comparación más vistosa.

En 2026 sólo hay cuatro grupos de aereus y cinco de caesarea. El muestreo de visitas,
la proximidad entre áreas y el histórico ya conocido al diseñar el sistema limitan
la generalización. Más horizontes o más remuestreos no crean nuevas visitas.

## ¿Siempre gana el mismo modelo?

Las familias ganadoras **sí cambian entre puntos y cortes** en esta reconstrucción.
Por ejemplo, entre emisiones con probabilidad de ganador disponible:

- Aereus 2025: V5 de 30 días gana 121/161 (75,2 %); también aparecen V2, V3 y V6.
  En 2026 aparecen dos perfiles V4: balance climático 41/69 → 59,4% y meteorología ampliada
  28/69 → 40,6%. No hay ganador con probabilidad disponible en el externo 2024.
- Caesarea 2024: V3 core/logística gana 83/119 (69,7 %), junto con V2 y V6.
  En 2026 domina V2/random forest, 81/98 (82,7 %), frente a V3/SVM 17/98 → 17,3%.

Estos denominadores pueden incluir un veredicto incierto: disponer de probabilidad
no equivale a recomendar una salida. Las tablas separan el consejo final.

La repetición de una familia es compatible con un ranking por especie/horizonte
que permanece estable entre entrenamientos, condicionado después por elegibilidad
y cobertura semanal del punto. **No demuestra por sí sola que sea el mejor criterio.**
Este estudio no ha comparado un ranking contextual alternativo; cambiar más veces
de modelo tampoco es un objetivo de calidad por sí mismo.

Como diagnóstico descriptivo adicional, el Brier entre emisiones con probabilidad
del ganador disponible es 0,221 para aereus (230 emisiones) y 0,173 para caesarea
(217). Se calcula después de seleccionar al ganador y excluye casos sin probabilidad:
no es calibración del mapa completo ni una comparación limpia entre especies.
Los cinco intervalos descriptivos de probabilidad se guardan en el análisis privado;
no se usaron para elegir o corregir B.

## Límites de reproducción y conservación

- Se ejecutaron 1.512 ajustes, 168 en cada una de las nueve fases, y se resolvieron
  semanas completas para todas las emisiones de desarrollo y externas. Ningún
  fallo imprevisto de contrato se contabilizó como abstención científica.
- A/B comparten el diseño de cuatro ventanas; **no replican el tamaño del 70/30
  operativo**. El catálogo de ranking utiliza sólo su ventana bajo el contrato
  de 14 días, sin mezclar el split adicional productivo de siete días.
- El histórico meteorológico respeta el corte de cada emisión, pero sus revisiones
  y el contexto geográfico actual impiden afirmar qué habría publicado HA entonces.
  Se conservan las limitaciones internas de tuning/preprocesamiento V6 y calibración
  SVM, detalladas en el protocolo; los externos quedan excluidos de ellas.
- El primer lote alcanzó el límite inicial de 4 GiB. Tras la autorización de 8 GiB,
  el máximo RSS observado fue 2.743.468.032 bytes (2,55 GiB). Los lotes sumaron unos
  **19,7 minutos de ejecución supervisada**, incluidos intentos fallidos; esto no
  es la duración total de la conversación. Salidas privadas: aproximadamente 1,23 GB.
- El primer lector creó/retiró metadatos de lease, sin alterar los valores del
  histórico. El adaptador corregido evita esos leases y verifica hashes. No se
  afirma ausencia absoluta de escrituras de metadatos durante la preparación inicial.
- Los hashes de predicciones de 2024/2025 se registraron al analizar; en 2026
  también al cerrar cada evaluación. La geografía no figuraba en el sello inicial
  de evaluación de 2024. Estas limitaciones no se ocultan con un sello retroactivo.
- La fuente inicial de `train_fold.py` se reconstruyó posteriormente y su SHA-256
  coincide exactamente con el sellado al ejecutarse. Se conserva junto con las
  versiones anteriores del evaluador. La diferencia sólo añade validaciones y
  sellos de dependencias, sin cambiar ajustes, particiones o ranking.

Once pruebas dirigidas verifican separación, proyección de variables, regla B y
contabilidad. Entradas congeladas y fuentes se contrastaron al cerrar el análisis.
Se conservan datos originales, modelos activos y todos los resultados privados.
No hubo trabajos operativos, despliegues, limpiezas ni cambios del coordinador.

## Siguiente paso propuesto, fuera de este goal

Mantener la operación actual y **no activar B**. La siguiente investigación debería
examinar la estabilidad del ranking y la cobertura perdida con poca evidencia,
usando validación temporal interna más amplia y controles de utilidad antes de
elegir una alternativa. Los cortes vistos aquí ya han informado esa hipótesis:
no presentarlos después como una confirmación nueva e intacta.

En paralelo, proponer una validación prospectiva con predicciones fechadas antes
de cada salida, versión y política identificadas, resultados favorables y
desfavorables explícitos, y condición de cierre acordada por adelantado. Conservar
abstenciones y no convertir salidas no realizadas en negativos. Harán falta más
episodios y soporte espacial para una conclusión operativa firme; este estudio
no justifica fijar ahora un número mágico de observaciones ni un nuevo umbral.
La ejecución de ese seguimiento o una segunda comparación requiere otro encargo.

Actualización de presentación del 04/10/2026: denominadores y porcentajes añadidos
sin repetir el experimento ni cambiar resultados, reglas o conclusiones. Versiones
anteriores y registro de la edición en
`tmp/prediction-model-selection/documentation-amendments/2026-10-04-threshold-denominators/`.

Ampliación explicativa del 04/10/2026: guía de lectura de columnas en ambos informes
y justificación por campaña de caesarea B en el estudio de selección. Se conservan
resultados y criterios del experimento; versiones anteriores y hashes en
`tmp/prediction-model-selection/documentation-amendments/2026-10-04-reading-guide-and-caesarea-b/`.
