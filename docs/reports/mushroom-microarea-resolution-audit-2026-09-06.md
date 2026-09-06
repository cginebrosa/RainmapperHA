# Auditoría no destructiva de resolución por microárea — 6 de septiembre de 2026

## Conclusión ejecutiva

No se recomienda cambiar todavía el entrenamiento ni el precálculo operativo de área a microárea.

La resolución por microárea conserva una señal real que hoy se diluye, pero con los datos actuales la mejora global fuera de muestra es de solo `0,000566` de Brier (`0,225 %` relativo). De 99 comparaciones de perfil, partición y estimador, 55 mejoran y 44 empeoran. En los episodios históricos donde microáreas de una misma área discrepan, la microárea positiva recibe una probabilidad media mayor que la negativa solo en el `52,8 %` de las evaluaciones. No es una separación suficientemente fiable para cambiar una recomendación operativa.

La regla de presentación `máximo de las microáreas` es la única que mejora el resumen de área, pero lo hace de forma marginal sobre todos los episodios: Brier `0,261906 → 0,261649` (`0,098 %`). La media y la mediana empeoran. El máximo mejora más en los casos mixtos porque el objetivo de área actual equivale a «hay al menos una microárea favorable», pero puede ocultar las microáreas negativas y no soluciona que el modelo todavía no las distingue de manera estable.

La decisión P0 de esta auditoría es, por tanto:

1. conservar por ahora la predicción operativa a nivel de área;
2. conservar las etiquetas originales por microárea, como ya hace el benchmark multiversión;
3. no añadir restricciones ecológicas ni reglas altitudinales inventadas;
4. no desplegar un precálculo ingenuo por todas las microáreas;
5. volver a evaluar cuando aumenten los episodios simultáneos y la separación sea consistente por especie.

## Alcance y garantías

La auditoría fue local, aislada y no destructiva. No lanzó entrenamiento operativo, precálculo operativo, publicación, promoción ni escritura en HA real. No usó ni modificó el worker. Los modelos de validación se ajustaron únicamente en memoria y no se escribió ningún artefacto de modelo.

Se respetó `MOD_0001`: los diagnósticos ecológicos no participaron en probabilidad, aplicabilidad, ranking, selección ni recomendación. La variante solo cambió la resolución espacial de altura, meteorología, balance hídrico y estado del suelo.

Se evaluaron los 11 perfiles operativos instalados:

- Altitude V2: `common_idw`;
- Biology V3: `core` y `common_idw_plus_physical_state`;
- Biology V4: `extended_weather` y `climatic_balance`;
- Biology V5 windowed: 30, 60 y 90 días;
- Biology V6 windowed smooth hierarchical: 30, 60 y 90 días.

La comparación cubre todos los estimadores declarados por esos perfiles, incluido `knn_distance_beta_smoothed_v2`.

## Fuentes congeladas

| Fuente | Identidad comprobada |
|---|---|
| Repositorio | rama `inicial`, HEAD `666ff08b299f75285a01c611fae1a89c216a75db` |
| Observaciones local y HA real | ambos `13081f3d8ff8ed4f629ce69a7eb625b270222f0a2011047313dbc8b256e03c38` |
| Sitios conocidos de HA real | `39e315d06d513d37968ab5eb2c69abfe31af6f3b861d6733d44f5f53a1d253be` |
| Estaciones activas de HA real | `76df09ec7ecbe5f686759a25280ab281a905c2b897bf866b164e9eab8d239c6f` |
| Registro multiversión de HA real | `20a84c8f4ed67d4a1ce9ba7e5e0cd32b552b5ecc46e90ec090821dfcf7705e35` |
| Meteorología | generación `20260906T090356917682Z-e918eb2b7bc4`, manifiesto `b6309a877e5d3df1aa616e6dcf4d2c3b322ca49363679172eede484e2a7e49ad` |

El worktree tenía previamente modificado `mushroom-data/mushroom_observations.json`. No se leyó como fuente de esta auditoría, no se modificó y no se incluyó en ningún cambio.

## Qué hace realmente el código actual

Hay dos rutas distintas que conviene no confundir:

- El entrenador V0 heredado agrupa por especie, área y fecha y declara favorable el episodio si **cualquier** microárea fue favorable (`rainmapper_core/mushroom_ml_trainer.py:155-201`). En esa ruta una negativa simultánea queda absorbida por el positivo de área.
- El benchmark multiversión conserva cada observación original como una fila independiente (`rainmapper_core/mushroom_ml_biology_v3.py:1484-1557` y su prueba en `tests/test_mushroom_ml_biology_v3.py:439-457`). Sin embargo, las filas de una misma área y fecha reciben el mismo contexto espacial agregado de área.

La meteorología operativa ya se calcula primero para cada microárea y después se promedia, junto con ETo, balance y suelo (`rainmapper_core/mushroom_ml_area_weather_runtime.py:59-182`). Por eso el problema no es que falten datos microespaciales, sino que se descartan al construir la entrada final del modelo.

Los grupos de validación se mantuvieron a nivel de especie y área durante 7 y 14 días (`rainmapper_core/mushroom_ml_biology_v3.py:1560-1603`). Ninguna variante pudo entrenar con una microárea y examinarse con otra perteneciente al mismo episodio.

## Método

Se construyeron dos juegos con las mismas observaciones, objetivos, horizontes, perfiles, estimadores y particiones temporales:

- **Baseline área:** altura representativa y series IDW/ETo/balance/suelo promediadas entre las microáreas del área, tal como funciona hoy.
- **Candidato microárea:** cada fila recibió la altura, serie IDW, ETo, balance y suelo de su microárea. No se introdujo el identificador de microárea como variable aprendible y el modelo siguió siendo global por especie o compartido, según el perfil.

Para reutilizar los constructores actuales sin alterar código operativo, cada microárea se presentó temporalmente como un área de un solo miembro. Después se restauraron el área original y los grupos originales antes de evaluar. Se comprobaron `27.312` filas de predicción fuera de muestra con identidad exacta entre baseline y candidato. Al contar cada estimador disponible se obtuvieron `106.832` pares probabilidad–objetivo.

No se usó un catálogo de ajuste congelado porque no existe uno persistido junto a las fuentes consultadas. Ambos lados utilizaron exactamente el mismo procedimiento científico de selección interna de los evaluadores actuales. Por ello esta prueba mide el efecto causal de la resolución espacial, pero no es una reproducción binaria de la generación instalada.

## Observaciones disponibles

El snapshot contiene 447 observaciones totales. Para las ocho especies operativas hay 400, de las que 377 son `valid + include`.

| Especie | Elegibles | Episodios área/día | Episodios microárea/día | Casos mixtos área/día |
|---|---:|---:|---:|---:|
| `amanita_caesarea` | 71 | 54 | 71 | 1 |
| `boletus_aereus` | 74 | 55 | 74 | 3 |
| `boletus_edulis` | 53 | 47 | 53 | 0 |
| `boletus_pinophilus` | 78 | 56 | 76 | 3 |
| `hygrophorus_latitabundus` | 11 | 10 | 11 | 0 |
| `hygrophorus_marzuolus` | 25 | 20 | 24 | 1 |
| `lactarius_deliciosus` | 48 | 42 | 47 | 0 |
| `morchella_elata_complex` | 17 | 17 | 17 | 0 |

La aparente diferencia entre 78 observaciones de `boletus_pinophilus` y 76 episodios microárea/día procede de observaciones compatibles repetidas; no hay objetivos opuestos dentro de una misma microárea y fecha.

Después de la corrección del usuario hay **cero** contradicciones de objetivo en la misma especie, microárea y día. Permanecen ocho discrepancias legítimas entre microáreas de la misma área y día:

| Especie | Área y fecha | Amplitud altitudinal |
|---|---|---:|
| `amanita_caesarea` | Olvan, 2022-10-18 | 148,3 m |
| `boletus_aereus` | Olvan, 2024-05-29 | 23,9 m |
| `boletus_aereus` | Olvan, 2024-09-21 | 122,8 m |
| `boletus_aereus` | Olvan, 2025-09-04 | 49,4 m |
| `boletus_pinophilus` | Guils, 2025-06-18 | 135,0 m |
| `boletus_pinophilus` | Guils, 2026-07-03 | 469,5 m |
| `boletus_pinophilus` | Guils, 2026-07-10 | 469,5 m |
| `hygrophorus_marzuolus` | Sant Joan, 2025-04-01 | 317,1 m |

Olvan confirma que no debe aplicarse una regla genérica de «cotas altas»: tres de sus discrepancias ocurren con menos de 50 m o alrededor de 120 m de diferencia. En Sant Joan, además, las observaciones positivas de marzuolus están en las microáreas cercanas a 1.400 m y las negativas alrededor de 1.700 m en esa fecha concreta. La relación depende de especie, momento, agua, temperatura y suelo; no es una restricción fija.

## Resultado predictivo global

| Versión / perfil | Cambio Brier al usar microárea | Cambio relativo | Comparaciones mejor / peor |
|---|---:|---:|---:|
| V2 `common_idw` | -0,003468 | 1,287 % peor | 3 / 9 |
| V3 `core` | +0,001944 | 0,765 % mejor | 8 / 4 |
| V3 `common_idw_plus_physical_state` | -0,002530 | 1,001 % peor | 4 / 8 |
| V4 `extended_weather` | +0,004785 | 1,833 % mejor | 10 / 2 |
| V4 `climatic_balance` | +0,004516 | 1,740 % mejor | 10 / 2 |
| V5 ventana 30 d | -0,005980 | 2,568 % peor | 0 / 4 |
| V5 ventana 60 d | -0,004376 | 1,815 % peor | 1 / 3 |
| V5 ventana 90 d | +0,014087 | 5,505 % mejor | 2 / 2 |
| V6 ventana 30 d | +0,001330 | 0,586 % mejor | 6 / 3 |
| V6 ventana 60 d | -0,000553 | 0,233 % peor | 5 / 4 |
| V6 ventana 90 d | -0,002663 | 1,081 % peor | 6 / 3 |

Un cambio Brier positivo significa menor error con microárea. La mejora no es coherente entre ventanas del mismo modelo: V5 mejora a 90 días pero empeora a 30 y 60; V6 mejora a 30 días pero empeora a 60 y 90. Eso impide interpretar el resultado como una ganancia estructural robusta.

Por estimador, `knn_distance_beta_smoothed_v2` empeora `0,004347` de Brier (`1,607 %`) y gana 3 de sus 10 comparaciones. Los mejores cambios agregados aparecen en la regresión logística reducida (`1,922 %` mejor), Elastic Net (`3,182 %` mejor) y SVM calibrada (`1,371 %` mejor), mientras Sparse Group (`2,381 %` peor) y el V6 específico por especie (`2,111 %` peor) retroceden.

## Resultado por especie

| Especie | Cambio relativo Brier | Interpretación |
|---|---:|---|
| `amanita_caesarea` | 0,460 % mejor | cambio pequeño e inestable |
| `boletus_aereus` | 1,143 % peor | no apoya el cambio |
| `boletus_edulis` | 1,037 % peor | no apoya el cambio |
| `boletus_pinophilus` | 1,856 % peor | empeora pese a los casos altitudinales de Guils |
| `hygrophorus_latitabundus` | 6,447 % mejor | solo 11 observaciones; alta incertidumbre |
| `hygrophorus_marzuolus` | 10,241 % mejor | 25 observaciones; el caso mixto de Sant Joan se ordena mal en la mayoría de pruebas |
| `lactarius_deliciosus` | 1,138 % peor | no apoya el cambio |
| `morchella_elata_complex` | 17,717 % mejor | solo 17 observaciones y ningún caso mixto; no demuestra resolución microespacial |

Las mejoras grandes se concentran precisamente en las especies con menos datos y sin suficientes episodios mixtos. No deben interpretarse como evidencia de producción.

## Los ocho episodios mixtos

Seis de los ocho episodios aparecen en alguna partición de prueba; los otros dos quedan en entrenamiento por orden cronológico. Al repetirlos entre perfiles, estimadores, contratos y horizontes se obtienen 2.592 evaluaciones:

- la probabilidad media de las microáreas positivas supera a la de las negativas en 1.369 (`52,8 %`);
- todas las positivas superan a todas las negativas en 1.225 (`47,3 %`);
- Guils 2026-07-03 muestra señal útil para `boletus_pinophilus` (margen medio positivo en el `62,4 %` de las evaluaciones);
- Guils 2026-07-10 es inconsistente (`46,6 %`);
- Sant Joan 2025-04-01 ordena mayoritariamente al revés las microáreas de `hygrophorus_marzuolus` (`2,8 %` con margen correcto).

Es decir: la resolución existe en los datos de entrada, pero el tamaño y la diversidad de la muestra todavía no permiten aprenderla de forma fiable.

## Cómo podría presentarse un área

Se compararon tres reglas calculadas a partir de las mismas probabilidades microárea:

| Regla de resumen | Brier de evento de área, sin sensibilidad de campaña |
|---|---:|
| Predicción de área actual | 0,261906 |
| Media de microáreas | 0,262760 |
| Mediana de microáreas | 0,263074 |
| Máximo de microáreas | 0,261649 |

La media y la mediana diluyen la existencia de una microárea favorable. El máximo encaja con la semántica actual «es favorable si existe alguna microárea favorable», pero su mejora global es demasiado pequeña. En los episodios mixtos el máximo mejora de `0,322165` a `0,268550`, aunque ese resultado es en parte consecuencia directa de que el objetivo de área también usa un `cualquiera favorable`.

Si en el futuro se adopta esta resolución, la interfaz no debería ocultarla en una cifra única. Debería mostrar:

- resumen de área con una regla documentada;
- estado «variable dentro del área» cuando la dispersión sea material;
- intervalo de probabilidades;
- microáreas concretas favorables y desfavorables.

No debería generar frases causales como «favorable en cotas altas» a partir de una sola predicción.

## Coste y restricciones de Raspberry Pi 4

El número de filas de entrenamiento no crece: se mantuvo en 400 para ventana fija y 2.800 para los siete retardos. Sí aumenta el número de contextos espaciales distintos que deben materializarse:

- ventana fija: 179 contextos área/fecha frente a 232 microárea/fecha (`+29,6 %`);
- retardos: 1.110 frente a 1.496 (`+34,8 %`).

El laboratorio completo generó temporalmente 898.352.328 bytes para el baseline y 1.018.312.927 bytes para el candidato (`+13,4 %`). Sumando ambos lados ocupó 1.880.196 KiB en disco. El proceso científico expandido alcanzó un pico de 7.473.086.464 bytes (`6,96 GiB`) de RSS en macOS. Ese patrón no es aceptable para producción en una Raspberry Pi 4.

Esos tamaños corresponden a JSON de benchmark, predicciones repetidas y errores compartidos; no son una propuesta de formato operativo. Los ficheros voluminosos se eliminaron al cerrar la auditoría, conservando solo los resúmenes compactos.

Una implementación futura tendría que cumplir estas condiciones antes de probarse en HA:

1. calcular cada serie meteorológica de microárea una sola vez y reutilizarla;
2. procesar entrenamiento y evaluación en flujo o por bloques, sin JSON de cientos de MiB;
3. no transportar ni reconstruir cadenas completas que sean puro almacenamiento;
4. en precálculo, guardar solo la ganadora por microárea y el resumen de área;
5. medir pico de memoria, tiempo, disco y tamaño final en la Raspberry Pi 4 antes de autorizar despliegue.

## Limitaciones

- Solo existen ocho episodios área/día con etiquetas opuestas entre microáreas; son insuficientes para demostrar generalización espacial.
- Las observaciones no cubren todas las microáreas con la misma frecuencia. Parte de la señal puede confundirse con año, campaña o especie.
- La auditoría compara capacidad predictiva fuera de muestra; no creó una generación operativa candidata ni ejecutó la semana actual. Hacerlo habría requerido promover o emular un catálogo completo pese a que la primera condición de aceptación ya falló.
- La ausencia de un catálogo de ajuste persistido impide reproducir bit a bit la generación instalada, aunque no sesga la comparación porque ambos lados usaron el mismo procedimiento.
- Las métricas por especie de baja muestra tienen una incertidumbre alta y no autorizan decisiones aisladas.

## Criterio para reabrir la propuesta

Conviene repetir esta auditoría cuando haya, por especie relevante, varios episodios simultáneos positivos/negativos en más de un área y campaña. Como mínimo, el candidato debería:

- mejorar Brier de forma consistente en ambos contratos y en la mayoría de perfiles operativos;
- ordenar correctamente positivas sobre negativas muy por encima del 50 %;
- no degradar las especies con más observaciones;
- conservar la identidad de filas y el aislamiento de grupos;
- demostrar un precálculo compacto y un pico de memoria compatible con la Raspberry Pi 4.

## Evidencia compacta

Los resultados de máquina quedan en `docker-data/audits/mushroom-microarea-resolution-20260906/`:

- `provenance.json`;
- `structural-summary.json`;
- `comparison-summary.json`;
- `decision-summary.json`;
- `run-stats.json`;
- `COMPACT-MANIFEST.json`.
