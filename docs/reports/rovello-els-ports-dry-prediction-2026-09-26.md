# Rovelló en Els Ports: resultado favorable con sequía

Investigación del 26/09/2026, HA real, lectura de artefactos persistidos por SMB.
Sin entrenamiento, precálculo, consultas nuevas de predicción ni cambios de
modelos, políticas, suspensiones o datos privados.

## Resultado comprobado

La captura anterior muestra IFF 81 y 2,2 mm disponibles en el resumen de 30 días.
La captura del mapa muestra IFF 81 y una estimación de agua disponible del 3,8 %
(1,3 L/m²), en 40.81383, 0.31152. Esos valores proceden de las capturas del usuario;
no se ha recuperado el payload anterior para descomponer exactamente su 81.

Durante la investigación terminó el precálculo que había lanzado el usuario.
Su revisión **258**, trabajo `worker_job_OMd73fnVlgtN`, terminó a las 20:34:59 UTC.
El SQLite activo de HA consultado entonces contenía para **Els Ports, Lactarius deliciosus, 26/09**
un resultado de **0,782894**, equivalente a IFF 78 redondeado. Es una comprobación
del Predictor por área; no se ha recalculado el punto del mapa.

El modelo elegido en esa revisión era `biology_v4 / lag_event_biology_v4 /
climatic_balance / logistic_regression_reduced_v1`, horizonte 1. Generación
`biology_v4_operational_20260924T130123Z`, anterior a la reparación Meteocat.

Entradas persistidas de ese modelo en la revisión 258:

- Lluvia en las cinco ventanas de 30 días: 0; 0; 4,711; 0,192; 0,001646 mm
  (suma 4,904646 mm, distinta del resumen de la captura anterior).
- Balances climáticos de las cuatro ventanas: −21,865; −17,026; −28,849;
  −32,531 mm.
- Diagnóstico de última lluvia significativa: 22/08, 9,139 mm; 35 días antes.
  Este diagnóstico no forma parte de las 33 columnas predictivas del artefacto.
- Cero variables ausentes; aplicabilidad `within_observed_range`, cero columnas
  fuera de los rangos individuales observados durante entrenamiento.
- Ninguna de las 33 columnas es el agua almacenada/disponible del suelo.

## Mecanismo reproducido

Se copió únicamente el modelo de 6.225 bytes a un directorio temporal local,
verificando su SHA contra el manifest instalado:
`126bc8b0474ea70af2fe8e6f5a7d6c91700ccb21ec8e3471e8f73190cd476bd9`.
Se descompuso algebraicamente la regresión logística usando sus coeficientes,
medias y escalas guardadas, y las entradas del precálculo. No se ejecutó el
runtime de predicción. Resultado **0,7828942008235266**, coincidente con el valor
persistido a sus seis decimales.

Contribuciones seleccionadas respecto a las medias de entrenamiento, en unidades
del predictor lineal (no puntos de IFF):

| Variable del caso | Contribución |
| --- | ---: |
| Humedad mínima 15–21 días: 13,387 % | +2,6008 |
| Cero días de lluvia en la última semana | +1,5055 |
| Humedad mínima 22–30 días: 15,2155 % | +1,3883 |
| Racha seca observada: 8 días | +0,6771 |
| Temperatura máxima última semana: 28,4 °C | −2,4906 |
| Balance climático 15–21 días: −28,8493 mm | −1,2096 |
| Lluvia 15–21 días: 0,192 mm | −1,0309 |

El intercepto es +2,63419 y la suma final +1,28261. Existen penalizaciones por
sequía, pero otras asociaciones aprendidas las compensan. Los signos son una
propiedad comprobada de este ajuste multivariable; no demuestran relaciones
causales ni significan que la sequía favorezca biológicamente la fructificación.

La aplicabilidad examinada comprobaba rangos por columna; este caso los superaba sin
avisos. Ese control no valida la combinación hídrica/ecológica completa.
La selección usa evidencia global de especie, sin evidencia específica de área:
5 recomendaciones favorables acertadas de 5, entre 19 observaciones evaluadas
(9 positivas, 10 negativas), con límite inferior Wilson 95 % de 0,5655.
Los 16 grupos de validación no equivalen a 16 observaciones positivas.

## Fuentes y límites

- HA `/media/rainmapper/results/predictor-precompute/active.sqlite3`, revisión 258,
  artefacto `sha256:f50746de6c23e7aa894e033cf63d7bcc06289808fb030ca9db33d7a92943dab4`.
- Manifest y modelo bajo `results/models/batches/operational_20260924T130123Z/`.
- `mushroom_ml_version_registry.json` de HA: generación instalada y revisión de
  meteorología de entrenamiento del 24/09.
- Evidencia local: `tmp/els-ports-20260926/active258-response-0.json`,
  `model.joblib`, `lr-contributions.json`.
- Código: `rainmapper_core/mushroom_ml_biology_v4.py:206`, composición de bloques;
  `rainmapper_core/mushroom_ml_runtime_inference.py:248`, comprobación de rangos.

La reparación Meteocat no reentrena los coeficientes existentes. Es razonable
revisar este mismo caso después del reentrenamiento que lance el usuario, pero
no hay evidencia de que éste vaya a resolverlo por sí solo. Queda pendiente
evaluar estabilidad de las asociaciones, casos secos de contraste y tratamiento
del estado hídrico en la selección/validación. No se introduce un umbral de agua
arbitrario, ni se suspende automáticamente esta familia durante el diagnóstico.

## Seguimiento tras reentrenamiento — 27/09/2026

El usuario termina reconstrucción/entrenamiento/precálculo. Lote instalado
`operational_20260926T223720Z`, precálculo 261, 27/09–03/10. SHA del SQLite
comprobado idéntico en HA y worker: ver
[validación operativa](worker-evaluation-memory-2026-09-27.md).
Consulta de `operational_members` en el SQLite del worker, sin generar predicciones.

Els Ports/rovelló cambia a **RF–V3**, perfil `common_idw_plus_physical_state`,
contrato `lag_event_biology_v3`, estimador `random_forest_restricted_v1`.
Probabilidad guardada 0,366163 en los siete días: IFF **37**. Esto confirma el
cambio observado, pero no aísla causalmente reparación de lluvia, nuevas muestras,
reentrenamiento, selección y cambio de fecha. La captura anterior era del 26/09.

La captura nueva del usuario corresponde a un punto de Vallcebre y muestra
rovelló RF–V3 76; Edulis LR–V3 32→45. No confundir RF con LR. En el precálculo
**por área** de Vallcebre, RF–V3 de rovelló da 0,764091 los tres primeros días,
0,762412 los dos siguientes, 0,761260 y 0,759631. Todos redondean a IFF 76.
No se ha consultado de nuevo ni recuperado el payload puntual de la captura.

Inspección del artefacto instalado, 297.906 bytes, sin ajuste de modelos ni
invocación del runtime de predicción:
`models/batches/operational_20260926T223720Z/generations/biology_v3_operational_20260926T223720Z/biology_v3/lag_event_biology_v3/common_idw_plus_physical_state/random_forest_restricted_v1/lactarius_deliciosus.joblib`.

- Pipeline con imputador y Random Forest de 200 árboles; 27 columnas reales.
- En estas semanas sólo cambia `horizon_days` (1→7) entre sus columnas.
  `days_since_significant_rain_at_target` sí cambia en el diagnóstico, pero
  **no está en las columnas consumidas por este modelo**.
- Las variables de lluvia, balance y agua del suelo son las observadas al corte
  26/09; no se proyecta un agotamiento del suelo día a día en estas entradas.
- Importancia interna de impureza del horizonte: 0,0015659 (0,1566 %), sólo 12
  nodos del bosque dividen por él. No interpretar como importancia causal.
- Recorrido de las reglas persistidas con las entradas guardadas: en Els Ports
  los siete días llegan a las mismas hojas en los 200 árboles; en Vallcebre
  cambian de hoja cuatro árboles durante la semana (0/0/0/1/1/2/4 frente al día 1).

La repetición se explica en el modelo y sus entradas; no es una copia del valor
por la UI ni sólo redondeo en Els Ports. Es escasa sensibilidad temporal en este
ajuste. LR–V3 no es universalmente constante; la captura de Edulis lo contradice.
Una semana plana no prueba por sí sola mala exactitud, pero tampoco respalda una
capacidad de anticipar evolución diaria. No forzar una bajada ni cambiar el
selector por estética: estudiar validación temporal con episodios independientes
y, si se propone estado hídrico proyectado, definir hipótesis y contrato para
entrenamiento e inferencia. Sin cambios de modelo, políticas o suspensiones.
