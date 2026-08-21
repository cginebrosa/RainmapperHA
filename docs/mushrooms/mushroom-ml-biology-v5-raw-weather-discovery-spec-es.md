# Especificación Biology V5 candidata — descubrimiento de retardos meteorológicos raw

Estado: **IMPLEMENTADA Y TÉCNICAMENTE PROMOCIONABLE POR ELECCIÓN MANUAL**.
Fecha original: 2026-08-16. Corrección de contrato: 2026-08-17.
Nombre de trabajo: `biology_v5_raw_weather_discovery`.

Resultado de la primera ejecución: implementación y benchmark local completos,
pero gate de promoción fallido. V5 gana 2/34 contextos frente al mejor miembro
individual V2/V3/V4 y pierde 32/34. Se ejecutaron la ablación raw sin calendario
y la degradación permitida a 25 remuestreos agrupados; 3.330 celdas de
coeficiente pasan estabilidad y se distribuyen casi uniformemente por retardo,
sin aislar ventanas interpretables. Véase
`docs/reports/V2_V3_V4_V5_raw_weather_report001.md`.

Actualización 2026-08-19 (primera, benchmark real): el resultado científico
desfavorable se conserva, pero ya no actúa como bloqueo técnico. El perfil
canónico completo puede prepararse y activarse manualmente; sus dos
estimadores compiten mediante la misma regla Brier contra prevalencia
aplicada al resto de versiones.

Actualización 2026-08-19 (segunda, retirada a `reference`): al ejecutar el
benchmark real contra datos de producción, `sparse_group_logistic_raw365_v1`
no converge para 4/9 especies por la altísima dimensionalidad de exponer 365
columnas diarias por canal. `biology_v5_raw_weather_discovery` (este
contrato) pasa a `status: reference` — se conserva íntegro para lectura
histórica, pero ya no es lanzable desde el selector de benchmark ni
promocionable como versión completa. Es sucedido por
`biology_v5_windowed_raw_weather`, con tres perfiles que compiten por ventana
predictiva (30/60/90 días de columnas crudas) en vez de exponer los 365 días
completos, manteniendo balance/SMI compartidos con el mismo calentamiento de
365 días. Genealogía y razonamiento completos en
`docs/mushrooms/mushroom-ml-contract-versions-es.md` y `docs/decisions.md`
(2026-08-19). Esta especificación sigue describiendo con exactitud el
contrato retirado; la especificación dedicada de la variante windowed queda
pendiente de redactar como documento propio.

Esta especificación define un experimento reproducible para responder a una
pregunta concreta: si se proporciona al modelo la historia meteorológica diaria
disponible, sin imponer acumulaciones de 1/3/7/21/30 días elegidas de antemano,
¿puede descubrir qué variables y qué retardos aportan predicción fuera de
muestra?

La corrección del 2026-08-17 aclara que «raw» describe la conservación de la
resolución diaria, no la exclusión de variables físicas calculadas. El perfil
canónico entrega simultáneamente observaciones IDW, ET0, balance climático y
estado hídrico/SMI. Los perfiles que omiten esos derivados son ablaciones.

El nombre V5 es provisional. No representa una promoción, un modelo operativo
ni una decisión sobre versiones de HA o del worker. Solo podrá consolidarse
como contrato operativo después de superar los gates definidos aquí.

## 1. Decisión que implementa esta especificación

Biology V5 candidata debe:

1. conservar cada observación y sus etiquetas originales;
2. materializar una historia meteorológica diaria causal de hasta 365 días;
3. entregar al estimador valores diarios, no ventanas meteorológicas escogidas
   manualmente;
4. entregar juntos canales observados y derivados físicos reconstruibles, sin
   preseleccionar cuál debe dominar;
5. usar regularización para que el propio estimador seleccione variables y
   retardos;
6. conservar predicciones hold-out fila a fila;
7. comparar V5 con V2, V3 y V4 sobre las mismas filas;
8. analizar falsos positivos y negativos compartidos;
9. producir únicamente artefactos de benchmark e informes locales;
10. no escribir modelos, no entrenar un candidato operativo y no cambiar el
   Predictor desplegado.

La hipótesis biológica de dos procesos —acumulación lenta de potencial
micelial/hospedador y activación más rápida de la fructificación— se utilizará
para interpretar las curvas aprendidas. No se impondrán fronteras fijas entre
ambos procesos ni estaciones de calendario como «primavera» u «otoño».

## 2. Invariantes no negociables

- Snapshot fuente:
  `docker-data/audits/mushroom-ml-snapshot-20260816`.
- El snapshot fuente es inmutable. Los resultados nuevos se escribirán en un
  directorio hermano, nunca dentro ni encima del snapshot canónico:
  `docker-data/audits/mushroom-ml-v5-raw-discovery-20260816/`.
- Meteorología común: IDW de área ya compartido por V2/V3/V4, radio 15 km,
  potencia 2, mínimo una contribución válida y corrección de temperatura por
  altitud. No se introducirá una base meteorológica distinta para V5.
- Los huecos no se convierten en cero. Un cero de lluvia solo es cero cuando el
  contrato meteorológico lo reconoce como tal, incluida la regla versionada de
  duplicado positivo suprimido.
- Calidad, cobertura, estación, procedencia, identificadores de área y motivos
  de exclusión nunca entran en `X`.
- No se borran ni consolidan observaciones. Las 395 filas `fixed_gap` y las
  1.580 tareas `lag_event` deben permanecer auditables; la elegibilidad fuente
  de 352 y 1.408, respectivamente, no se relajará ni reinterpretará.
- En `lag_event` existe exactamente un ajuste por
  especie+contrato+estimador+partición. Los horizontes 1/2/3/7 filtran las
  probabilidades del mismo hold-out; nunca provocan reentrenamiento.
- No se calcula ni se usa para decidir un Brier medio entre especies.
- Calidad predictiva precede a consenso. No se propone ensemble salvo que se
  materialice su probabilidad y supere al mejor miembro individual en las
  mismas filas.
- V2, V3 y V4 permanecen registradas, reejecutables y comparables. V5 se añade
  mediante el registro genérico como `proposed` o `candidate`, nunca como
  `active`.
- No se modifica ni construye HA, worker, GHCR o release; no se usa Tailscale;
  no se instala HA 0.2.255 ni worker 1.0.9.
- No se escribe `.joblib`, bundle de modelos ni generación `trained_model`.
  Todos los manifiestos deben declarar `model_artifact_written: false` y
  `operational_candidate_trained: false`.

## 3. Preguntas científicas

El benchmark debe responder por especie y contrato temporal:

1. ¿Mejora la historia diaria raw al mejor resultado individual V2/V3/V4?
2. ¿Qué canales meteorológicos reciben peso predictivo estable?
3. ¿Qué retardos o intervalos contiguos aparecen de forma estable?
4. ¿Emergen una escala reciente y otra lenta sin imponer sus límites?
5. ¿La señal lenta se mantiene al separar campañas área-año completas?
6. ¿El modelo aporta información más allá de la prevalencia y de la fenología
   del calendario?
7. ¿Los falsos positivos o negativos compartidos justifican después una curva
   no lineal/GAM, un estado temporal o una jerarquía entre especies?

El resultado identifica asociaciones predictivas, no causas. Cuando lluvia,
humedad, temperatura, ET0 y balance estén correlacionados, la selección de una
de ellas no prueba que las demás carezcan de relevancia biológica.

## 4. Contratos temporales candidatos

Se añadirán dos identificadores sin reemplazar los existentes:

- `fixed_gap_7d_biology_v5_raw365_v2`;
- `lag_event_biology_v5_raw365_v2`.

Los identificadores `...raw365_v1` quedan congelados para la ejecución
histórica incompleta; no se reutilizan porque añadir balance y SMI cambia el
vector predictivo y su semántica.

Ambos heredan de V3/V4:

- unidad de muestra y política de targets;
- identidad de observación;
- fecha objetivo y fecha de corte causal;
- grupos de florada de 7 y 14 días;
- IDW común de área;
- separación `predictive_features` / `quality` / `metadata`;
- reglas de elegibilidad ya fijadas.

La diferencia semántica de V5 es la representación temporal: conserva cada día
de la historia como un posible predictor y no construye acumulaciones
preseleccionadas para `X`.

## 5. Eje diario causal

Para cada muestra se construirá un eje exacto de 365 posiciones:

- `lag_000` es la fecha de corte meteorológico;
- `lag_001` es el día anterior;
- ...;
- `lag_364` es 364 días antes del corte.

Las fechas deben ser consecutivas y estar alineadas entre todos los canales. La
orientación debe probarse expresamente para impedir inversiones accidentales.
Ningún valor posterior a `cutoff_date` puede entrar en la matriz.

El límite de 365 días es una restricción de alcance y varianza, no una ventana
biológica afirmada por la literatura. Permite que una especie otoñal encuentre
señal en meses anteriores y que una especie primaveral alcance el ciclo previo,
sin entregar años irrelevantes al estimador.

Revisión operativa 2026-08-18: este eje permanece congelado únicamente para
reproducir y comparar V5/V6. Su longitud canónica es
`mushroom_ml_raw_weather.LOOKBACK_DAYS`; no es un parámetro de UI y cambiarla
altera el vector de columnas, por lo que exige otro contrato y reentrenamiento.
No se hereda como ventana por defecto de V2/V3/V4 ni del Predictor. La
literatura local revisada concentra los retardos meteorológicos accionables en
semanas y alrededor de un mes; por ello el runtime ordinario limita V2/V3/V4 a
90 días. El informe V5 tampoco encontró ventanas estables e interpretables en
0–364, pero eso no demuestra ausencia de señal en 91–365. V5/V6-365 queda como
control reproducible; cualquier reducción debe compararlo contra un nuevo
V5/V6-90 sobre las mismas filas y splits. Reducir o sustituir el eje de V5/V6
requiere ese experimento versionado, no una mutación de este contrato.

## 6. Canales que recibe el modelo

### 6.1 Perfil de ablación `raw_primary`

Debe contener las cinco magnitudes primarias reconstruibles hoy con el contrato
IDW común:

- `rain_mm`;
- `temp_min_c`;
- `temp_max_c`;
- `humidity_min_pct`;
- `humidity_max_pct`.

Cada canal genera 365 columnas con nombres inequívocos, por ejemplo
`rain_mm__lag_026`. Son 1.825 candidatos meteorológicos antes de añadir los
controles estáticos.

No se incluirán simultáneamente medias diarias deterministas de Tmin/Tmax o
RHmin/RHmax en este perfil, porque duplican información primaria. No se
incluirán agregados de lluvia, rachas, días lluviosos ni extremos de ventanas:
el propósito es que el modelo descubra su estructura temporal.

### 6.2 Perfil canónico `raw_primary_plus_physical_state`

Debe añadir, con paridad completa entre entrenamiento e inferencia:

- ET0 diaria Hargreaves-Samani/FAO56 ya versionada en V4;
- balance climático diario `rain_mm - et0_mm`;
- estado hídrico/SMI diario como fracción de almacenamiento disponible del
  depósito SoilGrids versionado;
- resúmenes físicos de corte: SMI medio y mínimo, cambios 7/14 días, recarga,
  déficit y secado.

Este es el perfil completo que define V5. `raw_primary`, las variantes sin
calendario y una variante intermedia sin SMI se conservan exclusivamente como
ablaciones para medir qué aporta cada bloque. La falta de una microárea con SMI
no convierte su estado en cero ni elimina automáticamente la observación: se
mantiene `None`, se imputa dentro del train y se audita fuera de `X`.

Los canales diarios del perfil completo son, por tanto: `rain_mm`,
`temp_min_c`, `temp_max_c`, `humidity_min_pct`, `humidity_max_pct`, `eto0_mm`,
`climatic_balance_mm` y `soil_water_fraction`. Todos comparten el eje causal de
365 días. Los resúmenes SMI son escalares y no se expanden artificialmente a
365 duplicados.

### 6.3 Inventario auditable

Antes de construir `X`, el script debe generar `raw-channel-inventory.json`
con todos los campos diarios presentes en el histórico local, su cobertura y
la razón de inclusión o exclusión. Viento, radiación, presión u otras magnitudes
solo podrán añadirse a un perfil separado si:

1. existen de forma suficientemente homogénea en las fuentes;
2. tienen un contrato espacial reproducible común;
3. pueden reconstruirse igual en entrenamiento e inferencia;
4. su ausencia no elimina observaciones.

No se inventará un IDW nuevo de viento o radiación durante esta ejecución solo
para poder decir que se usó «todo».

El inventario debe registrar ET0, balance y SMI como incluidos en el perfil
canónico. No puede declarar `soil_water` excluido por no ser meteorología raw.

### 6.4 Controles fenológicos

El benchmark debe distinguir meteorología de simple calendario:

- baseline de prevalencia de entrenamiento;
- baseline fenológico con seno/coseno del día del año de la fecha objetivo;
- V5 raw sin calendario;
- V5 raw con seno/coseno del día del año.

Esto permite comprobar si una supuesta ventana larga solo codifica que una
observación pertenece a la temporada habitual. En `lag_event`, `horizon_days`
se conserva como predictor separado y no penalizado de forma conjunta con un
canal meteorológico.

Área, microárea, año, fecha literal e identificadores nunca entran en `X`.

## 7. Tratamiento de observaciones históricas

Las observaciones actuales constituyen el target, no una serie diaria completa
de presencia/ausencia. Un día no visitado no es un negativo y no puede
codificarse como cero.

Por ello, la primera V5 no introduce lags diarios de observaciones pasadas. El
análisis de errores podrá justificar posteriormente un modelo de estado que
trate explícitamente visitas irregulares, pero no se fabricará continuidad ni
se suavizarán etiquetas en este experimento.

Todas las filas hold-out deben conservar el target original y los campos de
auditoría necesarios para enlazarlas con la observación fuente.

## 8. Datos ausentes y escalado

- La matriz mantiene las filas elegibles aunque falten días de la historia
  ampliada.
- La imputación se ajusta solo con el train exterior. Se usará mediana por
  columna y se conservarán columnas completamente vacías con valor neutral tras
  escalado, sin eliminarlas silenciosamente.
- El escalador se ajusta solo con train. El hold-out no interviene en
  imputación, escalado, selección ni hiperparámetros.
- No se añaden indicadores de ausencia a `X`: podrían convertir cobertura y
  procedencia en predictores. La cobertura diaria se conserva en `quality`.
- Por canal y banda de retardo se informarán días disponibles, imputados y
  completamente ausentes. Ninguna muestra desaparece por exigir 365 días
  completos.
- Columnas sin varianza o sin soporte en train reciben coeficiente cero y se
  documentan; no producen un error global.

## 9. Estimadores V5

### 9.1 `elastic_net_logistic_raw365_v1` — obligatorio

Pipeline reproducible basado únicamente en dependencias existentes:

1. imputación aprendida en train;
2. estandarización aprendida en train;
3. regresión logística Elastic Net con `solver="saga"`, semilla 42 y límite de
   iteraciones suficiente;
4. selección interna por Brier, nunca por accuracy.

Parrilla máxima para mantener acotada la ejecución nocturna:

- `C`: `0.01`, `0.1`, `1.0`, `10.0`;
- `l1_ratio`: `0.1`, `0.5`, `0.9`;
- `class_weight`: `None` y `balanced` solo cuando el soporte del inner CV lo
  permita.

Si hay empates dentro de una tolerancia de `1e-6`, gana la configuración más
regularizada y después el `l1_ratio` más alto. Deben guardarse convergencia,
iteraciones, hiperparámetros, coeficientes estandarizados y no estandarizados.

### 9.2 `sparse_group_logistic_raw365_v1` — obligatorio

Se implementará con NumPy/SciPy, sin instalar una dependencia nueva. Los grupos
son los canales meteorológicos completos; los controles fenológicos y horizonte
forman grupos propios. La función objetivo combina:

- pérdida logística;
- penalización L1 para seleccionar días individuales;
- penalización L2 por grupo para poder descartar un canal completo.

Los grupos no definen ventanas temporales. Después del ajuste, días
seleccionados contiguos se agrupan únicamente para informar intervalos
emergentes.

La implementación debe usar un optimizador proximal determinista con
backtracking, intercepto no penalizado, pesos de grupo normalizados por su
tamaño, tolerancia y máximo de iteraciones explícitos. Las pruebas unitarias
deben cubrir:

- descenso de la función objetivo;
- probabilidades finitas en `[0, 1]`;
- anulación de un grupo irrelevante sintético;
- conservación de un grupo informativo sintético;
- determinismo;
- error legible si no converge.

Parrilla máxima:

- intensidad global: cuatro valores logarítmicos derivados de
  `lambda_max`, entre `lambda_max` y `0.01 * lambda_max`;
- mezcla L1/grupo: `0.25`, `0.5`, `0.75`.

Una falta de convergencia de una configuración la marca como no disponible; no
autoriza a usar el hold-out para escoger otra. Si todas las configuraciones
fallan para una especie, se conserva la fila de disponibilidad y el benchmark
continúa con Elastic Net.

### 9.3 Modelos que no se añaden todavía

Un GAM/DLNM, modelo temporal de estado o jerárquico no forma parte de la
implementación V5 inicial. El análisis de errores y la estabilidad de
coeficientes decidirán cuál merece el siguiente ensayo. Tampoco se añade un
ensemble.

Los seis estimadores vigentes de V2/V3/V4 continúan siendo los comparadores:
LR, RF, ET, HGB, KNN y SVM RBF calibrada.

## 10. Selección interna sin tocar el hold-out

Para cada especie y contrato:

1. se crea una única partición exterior emparejada;
2. dentro del train exterior se construyen hasta tres folds cronológicos
   expansivos por grupos completos de florada;
3. ningún grupo, observación ni campaña bloqueada puede cruzar un fold;
4. los hiperparámetros minimizan el Brier medio entre folds de esa especie,
   nunca entre especies;
5. si solo hay soporte para dos folds, se usan dos y se registra;
6. si no hay dos clases suficientes para selección interna, se usa una
   configuración conservadora predeclarada y se marca
   `inner_selection_unavailable`; no se consulta el hold-out.

Configuraciones conservadoras de fallback:

- Elastic Net: `C=0.1`, `l1_ratio=0.5`, `class_weight=None`;
- sparse group: segundo valor más regularizado y mezcla `0.5`.

## 11. Particiones exteriores

### 11.1 Comparación primaria

Se reutilizan exactamente las particiones cronológicas por especie y grupos de
florada de 7 y 14 días empleadas por el informe 002. V2/V3/V4/V5 deben evaluarse
sobre claves comunes de observación+horizonte y con targets idénticos.

No se desplaza el corte ni se eliminan filas para obtener dos clases. Una
especie no evaluable se informa como tal.

### 11.2 Sensibilidad obligatoria de campaña

Una historia de 365 días cambia sobre todo entre campañas, no entre visitas
próximas. Se añadirá una evaluación secundaria que bloquee
`species_id + area_id + target_year` como unidad indivisible. Debe ser
cronológica y aproximarse al 70/30 sin romper campañas.

Esta sensibilidad no reemplaza el hold-out primario ni se mezcla con él. Sirve
para detectar si V5 aprende una campaña o un área-año compartidos. Si una
especie queda con una sola clase, se informa y no se modifica el corte.

## 12. Predicciones hold-out fila a fila

El evaluador genérico debe conservar, para todos los contratos y estimadores
disponibles, una fila con al menos:

- `sample_id`;
- `observation_id`;
- `species_id`;
- `area_id` y `micro_area_id` solo como metadata;
- `target_date` y `cutoff_date`;
- `temporal_contract_id` y `version_id`;
- `profile_id`;
- `group_days` y `split_id`;
- `validation_group_id`;
- `campaign_block_id` cuando corresponda;
- `horizon_days`;
- `prediction_target` y `y_true`;
- `train_prevalence_probability`;
- una probabilidad por estimador;
- disponibilidad y motivo si el estimador no pudo ajustarse;
- fase de florada observacional;
- resumen meteorológico diagnóstico;
- cobertura por canal y bandas de retardo.

Se escribirán:

- `heldout-predictions.jsonl`, formato canónico sin pérdida;
- `heldout-predictions.csv`, proyección cómoda para inspección;
- `heldout-predictions-manifest.json`, con hashes, recuentos y claves de
  unicidad.

La clave
`split_id + version_id + profile_id + temporal_contract_id + group_days + species_id + sample_id`
debe ser única por fila. Repetir una ejecución con las mismas entradas y semilla
debe conservar particiones, probabilidades dentro de tolerancia y hashes de la
matriz de entrada.

En `lag_event`, una prueba debe contar exactamente un `.fit()` por
especie+contrato+estimador+split. La proyección por horizonte no puede invocar
`fit`.

## 13. Fase de florada sin inventar etiquetas

La fase es un atributo diagnóstico derivado solo de observaciones conocidas,
nunca un target corregido ni una variable predictiva.

Para cada especie+área+grupo de florada:

- `singleton`: una única observación favorable en el grupo;
- `onset_observed`: primera favorable cuando existen al menos dos favorables;
- `active_observed`: favorable interior;
- `decline_observed`: última favorable cuando existen al menos dos favorables;
- `pre_fruiting_observed`: desfavorable anterior a la primera favorable dentro
  del mismo grupo auditable;
- `post_fruiting_observed`: desfavorable posterior a la última favorable;
- `between_positive_visits`: desfavorable entre dos favorables; se conserva
  como etiqueta original y se señala por posible conflicto/visita;
- `unknown_phase`: no existe soporte observacional suficiente.

No se convierte un día no visitado en ausencia y no se altera ningún target.
El informe debe mostrar cuántas filas sostienen cada fase; categorías con menos
de cinco filas se describen, pero no fundamentan una conclusión general.

## 14. Falsos positivos y negativos compartidos

Se usa umbral fijo 0,5 para la clasificación diagnóstica, además de evaluar las
probabilidades con Brier y log-loss.

Por cada fila y conjunto comparable de estimadores:

- falso positivo: `y_true=0` y `p>=0.5`;
- falso negativo: `y_true=1` y `p<0.5`;
- `wrong_count`: estimadores disponibles que fallan;
- `available_count`: estimadores disponibles;
- `shared_all`: fallan todos los disponibles, exigiendo al menos dos;
- `shared_supermajority`: falla al menos `ceil(2*available_count/3)`, exigiendo
  al menos tres;
- `shared_current_six`: fallan los seis comparadores actuales cuando los seis
  están disponibles.

Los recuentos y listados se desglosarán por:

- especie;
- versión, perfil y contrato temporal;
- horizonte;
- grupo de 7/14 días;
- fase de florada;
- área-año/campaña;
- condiciones meteorológicas anteriores.

Para describir condiciones meteorológicas se permiten resúmenes diagnósticos
que no entran en `X`: bandas `0–7`, `8–30`, `31–90`, `91–180` y `181–365`
días, con lluvia total/días observados, Tmin/Tmax, RHmin/RHmax, ET0 y balance
cuando existan. Estas bandas sirven para explicar errores; no son las variables
entregadas a V5.

El informe debe incluir las filas concretas de errores compartidos, no solo
totales, y comparar si V5 corrige o introduce cada error respecto al mejor
miembro V2/V3/V4 de esa especie.

## 15. Estabilidad y lectura de variables seleccionadas

Una selección aislada no se interpreta como descubrimiento. Dentro del train
exterior se calculará estabilidad mediante los folds internos y, cuando sea
posible, 50 remuestreos deterministas por grupos completos.

Por variable y día se conservarán:

- coeficiente y signo;
- frecuencia de selección;
- mediana y rango intercuartílico del coeficiente;
- grupo meteorológico;
- soporte y fracción imputada.

Se considera `stable_selected` cuando la frecuencia es al menos 0,70 y el signo
coincide en al menos 0,80 de las selecciones no nulas. Días estables contiguos
se agrupan en intervalos emergentes, permitiendo huecos máximos de dos días para
visualización. Este agrupamiento es posterior al ajuste y no modifica `X`.

Los gráficos obligatorios, generados localmente, son:

- mapa de calor variable × retardo por especie;
- curva de frecuencia de selección por retardo;
- coeficientes con signo para los intervalos estables;
- comparación Brier/log-loss/calibración contra baselines y mejor miembro;
- distribución temporal de FP/FN compartidos.

Si 50 remuestreos no terminan dentro del presupuesto nocturno, el proceso puede
reducirlos una sola vez a 25, debe registrarlo y nunca omitir la estabilidad por
completo.

## 16. Métricas y comparación

Por especie, contrato, perfil, estimador y split se informarán:

- `n_train`, `n_test` y clases;
- Brier;
- log-loss;
- balanced accuracy a 0,5;
- matriz de confusión;
- ROC AUC y PR AUC cuando el test tenga dos clases;
- calibration intercept/slope cuando haya soporte, o motivo de ausencia;
- delta y skill frente a prevalencia;
- delta frente al baseline fenológico;
- delta frente al mejor miembro individual V2/V3/V4 en filas idénticas.

No se ordenan modelos por consenso ni por un score combinado entre especies.
Las tablas transversales usarán conteos de victorias/empates/derrotas y mostrarán
si cada especie mejora o empeora.

## 17. Gates para interpretar el resultado

### 17.1 Señal favorable a V5

V5 merece un experimento operativo posterior solo si, por especie evaluable:

1. supera prevalencia y baseline fenológico;
2. mejora o empata dentro de tolerancia al mejor miembro individual V2/V3/V4
   en Brier y no degrada materialmente log-loss/calibración;
3. la mejora no desaparece en la sensibilidad por campaña;
4. las variables/retardos seleccionados son estables;
5. reduce errores compartidos sin concentrar errores nuevos graves en una fase;
6. puede reconstruirse con paridad causal en inferencia.

No se fija ahora una tolerancia universal de promoción porque el soporte difiere
por especie. El informe debe presentar deltas y su incertidumbre por bootstrap
de grupos; la decisión final seguirá siendo humana y por especie.

### 17.2 Decidir la siguiente familia

- Probar GAM/DLNM si los errores o coeficientes muestran relaciones suaves/no
  lineales o franjas de retardo anchas pero Elastic Net selecciona días
  inestables vecinos.
- Probar estado temporal si dominan errores alternantes dentro de la misma
  florada, especialmente `between_positive_visits`, onset o decline.
- Probar jerarquía si las especies con poco soporte muestran patrones de
  retardos semejantes pero estimaciones inestables, mientras especies con más
  datos sí sostienen señal.
- No añadir ninguna de esas familias si el problema principal es cobertura,
  etiquetas contradictorias, visitas sesgadas o ausencia de señal fuera de
  campaña.

## 18. Implementación esperada

La implementación debe preferir componentes nuevos y reutilizables, sin
condiciones por nombre V2/V3/V4. Nombres sugeridos:

- `rainmapper_core/mushroom_ml_raw_weather.py`: contrato, ejes y matriz raw;
- `rainmapper_core/mushroom_ml_sparse_group.py`: estimador proximal;
- `rainmapper_core/mushroom_ml_holdout.py`: salida fila a fila genérica;
- `rainmapper_core/mushroom_ml_error_analysis.py`: fases y errores compartidos;
- `scripts/build-biology-v5-raw-benchmark.py`;
- `scripts/evaluate-biology-v5-raw-benchmark.py`;
- `scripts/report-biology-v5-raw-benchmark.py`;
- pruebas homónimas bajo `tests/`.

Puede reutilizarse la caché larga por microárea y corte de
`scripts/build-biology-v4-benchmark.py`, pero V5 debe materializar los 365 días
de los cinco canales y no limitarse a las series de 90 días guardadas dentro de
V3/V4. Debe materializar en esa misma pasada ET0, balance y la serie diaria SMI
por microárea antes de agregar al área. No se debe reconstruir IDW ni el depósito
por cada muestra cuando pueda cachearse una serie larga por microárea.

El evaluador fila a fila debe ser genérico y extensible mediante el registro.
Las mejoras necesarias para guardar predicciones de V2/V3/V4 no se duplicarán
en cuatro scripts.

## 19. Artefactos requeridos

El directorio de resultados nuevo debe contener como mínimo:

- `MANIFEST.json`;
- `raw-channel-inventory.json`;
- `biology-v5-fixed.json`;
- `biology-v5-lag.json`;
- matrices o caches intermedias con hashes si resultan demasiado grandes para
  incrustarlas en JSON;
- comparaciones de grupos 7 y 14 para fixed y lag;
- sensibilidad por campaña;
- `heldout-predictions.jsonl` y `.csv`;
- `selected-features.json`;
- `shared-errors.json`;
- gráficos;
- `docs/reports/V2_V3_V4_V5_raw_weather_report001.md`.

El informe debe comenzar con una respuesta clara y no exagerada:

- si V5 raw mejora o no;
- en qué especies;
- qué variables y retardos son estables;
- si aparece evidencia compatible con dos escalas;
- cuál de GAM/DLNM, estado temporal, jerarquía o ninguna está justificada;
- si se recomienda mantener V5 solo experimental.

Debe registrar tiempos, comandos, versiones de dependencias, semillas, hashes,
recuentos de ajustes y cualquier degradación del plan por falta de soporte.

## 20. Pruebas y criterios de aceptación

La tarea no está terminada hasta verificar:

1. snapshot fuente sin cambios de hash;
2. ninguna modificación en HA, worker, modelos operativos, GHCR o releases;
3. ninguna observación fuente borrada o reetiquetada;
4. matriz daily lag correctamente orientada y sin futuro;
5. separación estricta de predicción/calidad/metadata;
6. imputación, escalado y tuning ajustados solo con train;
7. hold-out fila a fila para los seis algoritmos actuales y los dos V5 cuando
   estén disponibles;
8. un solo ajuste lag por especie+contrato+estimador+split;
9. horizontes proyectados sin refit;
10. comparaciones sobre filas idénticas;
11. ausencia de Brier medio decisorio entre especies;
12. V2/V3/V4 conservadas mediante registro genérico;
13. artefactos con `model_artifact_written=false`;
14. tests nuevos y suite relevante verdes;
15. `git diff --check` correcto;
16. informe enlazado a artefactos y limitaciones reales.
17. perfil canónico con los ocho canales diarios, resúmenes SMI y paridad
    entrenamiento/inferencia;
18. perfiles sin derivados identificados únicamente como ablaciones.

La suite completa se ejecutará si el tiempo lo permite. Si una prueba ajena al
alcance falla por el worktree previo, se aislará y documentará con evidencia;
no se corregirán ni revertirán cambios del usuario fuera del alcance.

## 21. Presupuesto nocturno y degradación segura

El orden obligatorio es:

1. inventario y builder V5;
2. tests de contrato y fuga;
3. Elastic Net completo;
4. hold-out fila a fila de V2/V3/V4;
5. sparse group y sus tests;
6. comparación y errores compartidos;
7. estabilidad y gráficos;
8. informe y documentación viva.

El proceso debe guardar artefactos incrementalmente y poder reanudarse. Un fallo
de una especie o estimador no aborta las demás. No se lanzan dos benchmarks
idénticos simultáneamente.

Si el tiempo obliga a reducir coste, el orden de degradación permitido es:

1. bajar remuestreos de estabilidad de 50 a 25;
2. omitir solo configuraciones de hiperparámetros que ya hayan demostrado no
   converger;
3. dejar especies no evaluables con motivo explícito.

No está permitido reducir 365 a una ventana elegida después de mirar el
hold-out, eliminar observaciones, usar el test para tuning, reentrenar por
horizonte ni sustituir el análisis probabilístico por accuracy.

## 22. Autonomía y límites operativos

La implementación es local, reversible y no destructiva. Leer ficheros, añadir
módulos/scripts/tests, escribir artefactos nuevos, ejecutar pruebas y benchmarks
y actualizar documentación están autorizados por esta tarea y no requieren
confirmación intermedia.

El agente solo debe detenerse y pedir intervención si encuentra una necesidad
real de:

- borrar o sobrescribir datos no regenerables;
- limpiar/resetear el worktree o descartar cambios existentes;
- desplegar, publicar o instalar HA/worker/release/modelo;
- escribir fuera del workspace y del directorio temporal;
- usar Tailscale o acceder a hosts operativos;
- instalar dependencias nuevas o usar credenciales;
- tomar una decisión científica que altere targets o el snapshot canónico.

Ante una ambigüedad local no destructiva debe inspeccionar código,
documentación, tests y artefactos, adoptar la interpretación más conservadora,
registrarla y continuar.

## 23. Referencias del proyecto

- `docs/codex-start-here.md` y `docs/active-context.md`;
- `docs/reports/V2_V3_V4_consensus_report002.md`;
- `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`;
- `docs/mushrooms/mushroom-ml-biology-v4-implementation-spec-es.md`;
- `docs/mushrooms/mushroom-ml-contract-versions-es.md`;
- `docs/mushrooms/mushroom-ml-version-lifecycle-es.md`;
- `docs/mushrooms/literature/fruiting-phenology/README.md`;
- `docs/mushrooms/literature/prediction/lactarius_deliciosus_revision_bibliografica_rainmapper.md`.

Referencias científicas principales para la interpretación de escalas, no para
imponer ventanas al modelo:

- Taye et al. (2016), serie de 17 años y señal de precipitación de final de
  verano/principio de otoño;
- Olano et al. (2020), productividad previa del hospedador y clima de la
  campaña como proceso en dos etapas;
- De la Varga et al. (2013), dinámica estacional de micelio y fructificación;
- Karavani et al. (2018), retardo aproximado de lluvia y coincidencia de humedad
  del suelo con el inicio;
- preprint de *Boletus edulis* conservado en la carpeta de literatura, ventanas
  diarias de varias semanas y respuesta térmica no lineal.
