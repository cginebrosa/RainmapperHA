# Registro canónico de versiones de contratos ML

Este documento es el registro permanente de por qué existen las versiones del
modelo micológico. No confundirlas con la versión del add-on HA (`0.2.x`) ni con
la imagen del worker (`1.0.x`): esas versiones indican software desplegado; los
identificadores siguientes describen el significado de los datos y modelos.

## Resumen

| Contrato | Estado | Cambio principal |
| --- | --- | --- |
| `mushroom_ml_v0` | REFERENCIA | Primer clasificador operativo, sin corte meteorológico causal estricto. |
| `fixed_gap_7d_v1`, `lag_event_v1` | REEMPLAZADO por altitude V2 | Cortes meteorológicos reproducibles y sin fuga temporal. |
| `fixed_gap_7d_altitude_v2`, `lag_event_altitude_v2` | VIGENTE | Meteorología diaria IDW multifuente común y temperatura trasladada a la altitud representativa del área. |
| `fixed_gap_7d_biology_v3`, `lag_event_biology_v3` | BENCHMARK LOCAL, NO OPERATIVO | Observaciones preservadas, targets, IDW de área, separación de calidad y grupos de florada 7/14. |
| `fixed_gap_7d_biology_v4`, `lag_event_biology_v4` | PROPUESTO, BENCHMARK LOCAL | Memoria de lluvia hasta 30 días, distribución de lluvia, balance climático, estado hídrico del suelo y continuidad auditable. |
| `fixed_gap_7d_biology_v5_raw365_v1`, `lag_event_biology_v5_raw365_v1` | HISTÓRICO NO CONFORME | Primera ejecución: cinco canales IDW; ET0/balance solo como ablación y SMI ausente. |
| `fixed_gap_7d_biology_v5_raw365_v2`, `lag_event_biology_v5_raw365_v2` | PROPUESTO, CORRECCIÓN LOCAL | Ocho canales causales IDW/físicos, incluido estado hídrico, para selección regularizada. |
| `fixed_gap_7d_biology_v6_smooth_hierarchical_v1`, `lag_event_biology_v6_smooth_hierarchical_v1` | HISTÓRICO NO CONFORME | Suavizó solo los cinco canales primarios de V5 v1. |
| `fixed_gap_7d_biology_v6_smooth_hierarchical_v2`, `lag_event_biology_v6_smooth_hierarchical_v2` | PROPUESTO, CORRECCIÓN LOCAL | Bases suaves sobre los ocho canales diarios V5 v2, estados físicos escalares y pooling parcial. |

## Tubería meteorológica común V2–V6

La única secuencia válida, tanto para construir el dataset como para predecir,
es:

`estaciones habilitadas → IDW diario por microárea → [ET0/balance/SMI si el perfil los declara] → agregación de área → variables del modelo`.

Los valores de estación son entradas crudas para la interpolación, nunca
variables consumidas directamente por V2–V6. Un cero observado participa en el
IDW con su peso; un valor ausente/N/A se excluye y nunca se convierte en cero.
ET0 usa Tmin/Tmax IDW corregidas a la altitud de la microárea; el balance es
`lluvia IDW - ET0` en esa misma microárea; el depósito SMI usa esa lluvia IDW,
esa ET0 y el contexto SoilGrids. Solo después se agregan las microáreas. La
paridad incluye fórmulas, orden de columnas, fechas de corte, tratamiento de
ausencias y perfiles; un artefacto entrenado con otra tubería no es compatible.
Los V2/V3 actuales no declaran estado físico y usan 90 días; omitir esos
derivados en inferencia evita calcular columnas descartadas. La capacidad no se
retira: una futura comparación V2/V3 `IDW + balance/SMI` debe tener perfil o
contrato propio, entrenarse y medirse contra el perfil original. V4 usa 90 días
y deriva físicos solo en sus perfiles correspondientes. Los 365 días son una
constante del contrato V5/V6 (`mushroom_ml_raw_weather.LOOKBACK_DAYS`), no un
parámetro interactivo; modificarla exige nuevas columnas y reentrenamiento.

## V0 — modelo inicial

- Introdujo artefactos por observación, entrenamiento por especie y Predictor.
- Se conserva para trazabilidad y diagnóstico, no como contrato recomendado.
- Parte de sus variables podían usar meteorología demasiado próxima o posterior
  a la fecha de emisión; por eso no sirve de referencia causal definitiva.

## V1 — contratos temporales

- `fixed_gap_7d_v1`: ventana ciega fija de siete días.
- `lag_event_v1`: corte meteorológico según fecha de emisión y eventos de lluvia.
- Ambos hacen explícitos cobertura, ausencias, lluvia suprimida, estación
  elegida, horizonte y fecha de corte. Los huecos no se convierten en lluvia
  cero salvo las reglas explícitas del contrato meteorológico.
- Fueron la primera base reproducible para comparar familias de estimadores.
- Quedan congelados como referencia. No deben promocionarse bajo un runtime que
  solicite altitude V2.

## Altitude V2 — corrección térmica por altitud

Es un cambio aislado sobre V1, no Biology V3.

- Contratos vigentes: `fixed_gap_7d_altitude_v2` y
  `lag_event_altitude_v2`.
- Existe una sola base meteorológica válida para ambos contratos: el IDW
  multifuente común de área, con radio 15 km, potencia 2 y las mismas reglas de
  cero, ausencia, estación retirada y duplicado positivo que Biology V3. Esta
  base es obligatoria tanto en entrenamiento como en inferencia.
- Un bundle construido con `nearest_station_single_source_daily` pertenece a
  V1 legado aunque incluya corrección térmica. No puede publicarse, cargarse ni
  mostrarse como `altitude_v2`. La tarjeta operativa y la comparación deben
  resolver el mismo artefacto V2 instalado; no se permiten dos cálculos V2 con
  contratos espaciales distintos.
- Antes de construir variables térmicas se aplica:

  `T_area = T_station + (z_station - z_area) / 100 * 0,65 °C`

- `z_station` procede del catálogo meteorológico y debe materializarse en
  `weather_station_altitude_m` durante la reconstrucción.
- `z_area` es la media de las altitudes DEM medias de todas las microáreas
  materializadas del área. No depende solo de las observaciones del episodio.
- Si falta una de las altitudes, no se usa silenciosamente la temperatura cruda.
- Se sustituyen umbrales térmicos globales hardcoded por variables continuas
  corregidas. La respuesta conserva estación, ambas altitudes, gradiente y
  corrección aplicada para auditoría.
- Rebuild y training deben ejecutarse con software V2. Entrenar V2 sobre un
  `features.json` antiguo sin `weather_station_altitude_m` no es válido.
- La promoción debe exigir exactamente ambos identificadores V2 en el
  manifiesto de entrenamiento.

### Compatibilidad operativa

- HA `0.2.254` está instalada y añade la barrera de promoción que rechaza
  manifiestos V1 incompatibles.
- Worker `1.0.7` es anterior: reconstruye features sin altitud de estación y
  entrena V1; no es compatible de extremo a extremo.
- Worker `1.0.8` desplegado incorpora reconstrucción, entrenamiento y metadatos
  altitude V2. La generación V2 completa fue promovida y validada en M1 y en el
  fallback HA el 2026-08-13.

## Biology V3 — benchmark local implementado

No es una tercera corrección técnica incremental de altitud. Es un rediseño más
amplio que debe comparar sus resultados contra altitude V2 congelado:

- cada observación original como muestra; las vistas microárea/fecha y
  área/fecha solo auditan conflictos y no reducen filas;
- targets favorable, desfavorable y desconocido sin inventar negativos;
- censura y sesgo de visitas explícitos;
- exclusión de metadata/quality de las variables predictivas cuando corresponda;
- grupos de validación por especie+área de 7/14 días sin segmentar el modelo por
  área, más calibración y Brier antes de
  cualquier propuesta de promoción.

La implementación local del 2026-08-13 añade contratos nuevos sin cambiar
V2: `outing_value_area_v1`, `area_microarea_evidence_v1`,
`observed_weather_quality_v1` y, tras corregir el tratamiento ya acordado de
duplicados, `daily_rain_idw_radius15km_power2_duplicate_zero_v2`. La lluvia V3 es una serie IDW diaria en
el punto representativo de cada microárea, radio 15 km y potencia 2. Ausencias,
errores y estaciones retiradas no se convierten en cero. Solo un `N/A`
identificado como repetición positiva del día anterior aporta `0 mm`; se cuenta
por separado como imputación trazable. El contrato
`area_daily_mean_microarea_idw_duplicate_zero_v2` agrega cada día mediante
la media de los IDW disponibles de todas las microáreas configuradas; descarta
el centroide calculado del área. El modelo acepta esta media como lluvia
canónica sin penalización ni advertencia por la procedencia de las estaciones.
Los dos feature sets construyen `predictive_features`, `quality` y `metadata`
por separado. Solo variables predictivas registradas pueden entrar en `X`; el
área y los contadores de cobertura no entran. La lluvia siempre usa la media
diaria de IDW de las microáreas configuradas. Temperatura y humedad relativa
del aire conservan el selector V2 sensible al corte; la corrección por altitud
se aplica a temperatura.

La reproducción local conserva 399 observaciones en `fixed_gap` y genera 1.596
muestras en `lag_event` para horizontes 1/2/3/7. Con altitudes DEM
materializadas en una copia de known sites resultan 204 y 816 muestras
elegibles, respectivamente. Los grupos de florada contienen 264 grupos a 7
días y 244 a 14 días, sin fusionar observaciones. Los cuatro horizontes no se
interpretan como cuatro observaciones independientes. No se persistió ningún
modelo.

La comparación equivalente reconstruye V2 por observación y encuentra 167
filas semanales comunes. La evaluación vigente no selecciona por un Brier
combinado entre especies: compara por separado contrato temporal, estimador y
especie. Dentro de cada contrato, LR, RF, ET, HGB, KNN y SVM RBF reciben la
misma `X`. Mes y altitud directa permanecen inactivos; la altitud sigue
corrigiendo la temperatura.

Las variables activas no contienen medias meteorológicas: lluvia IDW acumulada,
racha seca, extremos de temperatura y extremos de humedad relativa. Las medias
se conservan inactivas. El análisis fila a fila de las 15 parejas muestra que
RF+ET es la pareja más coincidente de forma sistemática, sobre todo en
`lag_event`, pero no existe un estimador ganador universal y el soporte por
especie sigue siendo pequeño. No autoriza promoción operativa.

La altitud de cada microárea se calcula y cachea al crear o cambiar su geometría;
no se consulta el DEM durante cada benchmark o predicción. La cadena local
Catalunya→Andorra→IGN MDT25 hoja 592 cubre las 58 microáreas actuales. Si una
microárea futura queda fuera de las tres coberturas, conserva `no_data`.

La especificación vive en
`docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`; hasta que pase sus
gates permanece como candidato de benchmark y no sustituye altitude V2.

## Biology V4 — agua disponible y continuidad, benchmark local implementado

V4 continúa en estado declarativo `proposed` y no es operativo. Ya tiene
implementados localmente el contexto SoilGrids, el balance climático, el
depósito edáfico experimental y los dos benchmarks por bloques. Hereda sin cambios el target,
la unidad de observación, los grupos especie+área, la lluvia IDW y la separación
`predictive_features`/`quality`/`metadata` de V3.

El cambio propuesto añade:

- ventana de lluvia 22–30 días y número de días lluviosos por ventanas;
- balance climático entre lluvia y demanda evaporativa;
- estado hídrico estimado primero por microárea y después resumido al área,
  únicamente donde retención, profundidad y drenaje tengan soporte trazable;
- extremos de temperatura y humedad relativa, manteniendo las medias directas
  fuera de `X`;
- métricas de continuidad y una posible capa de estado por especie+área, solo
  si reduce parpadeo sin empeorar Brier o calibración.

La falta de suelo no elimina observaciones del benchmark general. Cada bloque
se compara sobre filas emparejadas y los seis estimadores reciben la misma `X`
por especie y contrato. La especificación canónica está en
`docs/mushrooms/mushroom-ml-biology-v4-implementation-spec-es.md`.

El primer derivado congelado es
`microarea_climatic_water_balance_v1`, cuya demanda evaporativa usa
`hargreaves_samani_fao56_temperature_v1`: lluvia del contrato IDW de área,
Tmin/Tmax corregidas, latitud y fecha. Un hueco no equivale a cero; calidad,
constantes, series fuente y temperatura media auxiliar quedan fuera de `X`.
Humedad relativa mínima/máxima continúa como predictor independiente. Este
contrato está declarado mediante `derived_feature_contract_ids` en el registro
de versiones, no mediante una condición hardcoded por nombre V4.

El segundo derivado local es `microarea_soil_water_state_v1`. Calcula primero
un depósito acotado por microárea y después resume al área; conserva como
variantes los perfiles 0–30/0–60/0–100 cm y capacidad a 10/33 kPa. Su estado es
`uncalibrated_physical_index`: el contexto actual no incluye corrección `cfvo`
por fragmentos gruesos ni parámetros forestales calibrados. Las variantes se
persisten y validan, pero permanecen experimentales hasta la comparación
emparejada; ninguna se elige por hardcode o intuición.

La entrada térmica diaria conserva como primera opción el selector V2 sensible
al corte. Si Tmin/Tmax falta en un día, V4 puede usar otra estación real a menos
de 15 km, elegible en ese mismo corte y corregida a la altitud del área. No
interpola ni usa el futuro. Esta cobertura elevó las filas con suelo 0–30 cm de
166 a 191 en `fixed_gap` y de 667 a 765 en `lag_event`, sin borrar las filas que
siguen incompletas.

La evaluación local emparejada usa los seis estimadores y grupos temporales de
7 y 14 días. Compara Brier por especie, contrato, algoritmo y bloque; no publica un
Brier medio entre especies. El balance tiene señal especialmente favorable en
`lag_event` (30 mejoras frente a 14 empeoramientos en 48 pares
estimador-especie). El suelo produce resultados mixtos y conserva las seis
variantes como experimentales. No se escribió ningún modelo.

## Biology V5 raw weather discovery — contrato en corrección local

V5 no reemplaza ni promociona V2/V3/V4. Su perfil completo materializa 365 días
causales de lluvia, Tmin, Tmax, RHmin y RHmax con el mismo IDW común, además de
ET0, balance climático y estado hídrico/SMI derivados causalmente. Conserva
también los resúmenes físicos de corte registrados. Las magnitudes observadas y
calculadas entran juntas para que Elastic Net y sparse-group logistic puedan
seleccionarlas dentro de train; los contadores de calidad y procedencia quedan
fuera de `X`. Los perfiles que omiten calendario, derivados físicos o SMI son
ablaciones, no el perfil canónico de runtime. En `lag_event` hay un único ajuste
por especie+contrato+estimador+split. El Predictor admite 1..7; los cortes
1/2/3/7 siguen siendo un resumen diagnóstico que filtra las mismas
probabilidades hold-out, no una limitación de disponibilidad del modelo.

El benchmark histórico del 2026-08-16 conserva 8.490 predicciones fila a fila. En 34
contextos evaluables, el mejor V5 vence dos veces y pierde 32 frente al mejor
miembro individual V2/V3/V4; las dos victorias corresponden a
`boletus_edulis`, que solo es evaluable en grupos de 14 días. Esa ejecución
trató ET0/balance como ablación, excluyó SMI y terminó instalando el perfil
`raw_primary_no_calendar`; por tanto no satisface el contrato completo fijado
ahora y debe repetirse antes de comparar o instalar V5. La ablación sin
calendario y 25 remuestreos agrupados confirman una selección demasiado densa
para afirmar ventanas meteorológicas. V5 permanece `proposed`, sin generación,
modelo ni Predictor operativo. Especificación e informe:
`docs/mushrooms/mushroom-ml-biology-v5-raw-weather-discovery-spec-es.md` y
`docs/reports/V2_V3_V4_V5_raw_weather_report001.md`.

## Biology V6 — retardos suaves y pooling parcial, contrato en corrección local

V6 reutiliza la matriz completa de V5. Reduce cada canal diario —primario o
físico— a diez bases B-spline sobre un eje logarítmico de retardo y conserva
sin suavizar los estados/resúmenes físicos escalares. Compara logística suave por
especie, coeficientes completamente compartidos y pooling parcial con
desviaciones específicas más penalizadas.

La ejecución histórica del 2026-08-16 suavizó únicamente los cinco canales
primarios y no satisface este contrato completo; debe repetirse después de V5.
En sus 34 comparaciones estrictas contra el mejor miembro V2/V3/V4/V5, V6 gana 4
y pierde 30. El pooling parcial supera al modelo totalmente compartido con
frecuencia, pero pierde 19/34 frente al suave por especie. La señal más clara
es `hygrophorus_latitabundus` en dos comparaciones fixed, con solo cuatro
observaciones de test. V6 permanece `proposed`, sin generación ni capacidad
operativa. Especificación e informe:
`docs/mushrooms/mushroom-ml-biology-v6-smooth-hierarchical-spec-es.md` y
`docs/reports/V2_V3_V4_V5_V6_smooth_hierarchical_report001.md`.

## Biology V5 windowed raw weather — sucesora de V5 raw365, en corrección local

Creada el 2026-08-19 tras observar que el perfil `raw_primary_plus_physical_state`
de V5 (365 columnas diarias crudas por canal, ~2.557 columnas totales) no
converge (`sparse-group logistic did not converge within 1000 iterations`)
para 4 de 9 especies en el benchmark real, por dimensionalidad excesiva frente
al soporte disponible. `biology_v5_raw_weather_discovery` pasa a
`status: reference` (nunca se borra; sus benchmarks archivados siguen siendo
válidos para lectura histórica) y se retira del selector de benchmark
(`benchmark_available: false`, `operational_eligible: false` en sus
perfiles).

`biology_v5_windowed_raw_weather` reutiliza los mismos `temporal_contract_id`
(`fixed_gap_7d_biology_v5_raw365_v2`, `lag_event_biology_v5_raw365_v2`) y el
mismo `derived_feature_contract_id` que V5 raw365 — describen la misma forma
de entrada preparada (serie de área de 365 días); solo cambia qué columnas
selecciona cada perfil, como ya ocurría con las seis variantes de perfil que
convivían bajo el mismo contrato en V5. Declara tres perfiles que compiten
entre sí, idénticos salvo la ventana de columnas crudas de lluvia/temperatura/
humedad expuesta al modelo: `raw_window_30d_plus_physical_state`,
`raw_window_60d_plus_physical_state`, `raw_window_90d_plus_physical_state`.
Balance hídrico y SMI se mantienen comunes a las tres ventanas: siguen
calculándose con calentamiento de 365 días y se exponen únicamente como los
siete escalares `PHYSICAL_STATE_SCALARS`, nunca como series diarias completas.
Pendiente de investigar (no implementado): recalcular balance/SMI de forma
independiente por ventana en vez de compartirlo.

Sin benchmark real ejecutado todavía sobre esta versión al escribir esta
entrada. Especificación:
`docs/mushrooms/mushroom-ml-biology-v5-raw-weather-discovery-spec-es.md`
(pendiente de ampliar con la variante windowed). Detalle completo de la
decisión en `docs/decisions.md` (2026-08-19, "Perfiles de ventana predictiva
30/60/90 días en V5/V6...").

## Biology V6 windowed smooth hierarchical — sucesora de V6 smooth-365, en corrección local

Creada el mismo día y por el mismo motivo que la anterior.
`biology_v6_smooth_hierarchical` pasa también a `status: reference` con
`benchmark_available: false`. A diferencia de V5, el perfil original de V6 no
mostró fallos de convergencia (la compresión a diez bases B-spline por canal
ya reduce mucho la dimensionalidad); se retira igualmente para mantener el
mismo diseño de comparación por ventana que V5 y evitar mezclar un control de
365 días con las nuevas ventanas.

`biology_v6_windowed_smooth_hierarchical` reutiliza los mismos
`temporal_contract_id` del V6 retirado y declara tres perfiles
(`smooth_window_30d_plus_physical_state`, `_60d_`, `_90d_`) que aplican la
misma proyección B-spline de diez bases, pero solo sobre los cinco canales
meteorológicos primarios truncados a la ventana correspondiente — no sobre
las series diarias de balance/SMI/ETO, que se mantienen compartidas como los
mismos siete escalares `PHYSICAL_STATE_SCALARS` de siempre.

Sin benchmark real ejecutado todavía sobre esta versión al escribir esta
entrada. Especificación:
`docs/mushrooms/mushroom-ml-biology-v6-smooth-hierarchical-spec-es.md`
(pendiente de ampliar con la variante windowed).

## Regla de continuidad

Cada contrato nuevo debe añadir aquí su motivación, entradas, cambio semántico,
compatibilidad de software, estado y contrato reemplazado. La compactación de
`active-context.md` nunca debe eliminar esta genealogía.

El estado y las generaciones ya no se deducen de este texto ni se codifican por
nombre de versión. El registro canónico legible por máquina es
`mushroom-data/mushroom_ml_version_registry.json`; el procedimiento de
comparación, retención permanente, promoción y rollback está en
`docs/mushrooms/mushroom-ml-version-lifecycle-es.md`. V2 deberá seguir
persistiendo y siendo reejecutable aunque V3, V4 o una versión futura llegue a
ser operativa.
