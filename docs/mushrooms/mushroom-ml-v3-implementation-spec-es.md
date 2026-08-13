# Especificación de implementación del sucesor de v2

Estado: **BENCHMARK LOCAL IMPLEMENTADO, NO OPERATIVO**. Target, vistas de
auditoría, IDW diario de área, registro de variables, gates y ambos contratos
de benchmark están implementados y probados. Entrenamiento, elección de
variables y promoción siguen pendientes. Altitude V2 permanece como referencia
operativa inmutable.

La tarea no consiste en retocar v2 hasta que produzca resultados más
plausibles. Debe crear contratos nuevos, reproducibles y comparables, dejando
v2 como referencia inmutable.

## Alcance

Implementar solamente:

1. congelación reproducible de los contratos v2;
2. target operativo y unidad de episodio explícitos;
3. separación estricta entre variables predictivas y calidad/censura;
4. benchmark sucesor listo para comparaciones posteriores de variables.

Fuera de alcance en esta tarea:

- promover modelos o cambiar el dictamen del Predictor;
- elegir el estimador ganador;
- añadir negativos sintéticos;
- entrenar especies sin dos clases mediante trucos de partición;
- cambiar HA, workers, red o Tailscale;
- publicar una release.

## Identificadores propuestos

```text
target_contract_id: outing_value_area_v1
episode_contract_id: area_microarea_evidence_v1
quality_contract_id: observed_weather_quality_v1
rainfall_contract_id: daily_rain_idw_radius15km_power2_v1
area_rainfall_contract_id: area_daily_mean_microarea_idw_v1
feature_set_id: fixed_gap_7d_biology_v3
feature_set_id: lag_event_biology_v3
```

Si se cambian estos nombres durante la implementación, el cambio debe quedar en
una ADR/decisión antes de generar el primer benchmark. Nunca se reutiliza un ID
para otra lista de columnas o semántica.

Las compactaciones de documentación pueden enlazar esta especificación, pero no
reemplazarla por un resumen que pierda fórmulas, alternativas descartadas,
resultados de auditoría o condiciones de revisión. El código implementa el
contrato; no es su única documentación.

## 1. Congelar v2

`fixed_gap_7d_altitude_v2` y `lag_event_altitude_v2` pasan a estado
`reference_only`:

- no cambiar sus `feature_cols`, fórmulas, thresholds, particiones ni mapping;
- conservar sus bundles e informes locales únicamente para reproducir las
  comparaciones ya realizadas;
- registrar en cada benchmark el hash de observaciones, catálogos, known sites,
  reconstrucción GIS y artefacto de features;
- añadir una prueba de snapshot que detecte cambios accidentales en la lista de
  columnas y metadatos v2;
- un bundle v2 no puede cargarse como v3 ni viceversa.

Archivos principales:

- `rainmapper_core/mushroom_ml_experiments.py`: declarar estado/versión de los
  contratos sin modificar su contenido;
- `rainmapper_core/mushroom_ml_experiment_trainer.py`: validar
  `feature_set_id`, `target_contract_id`, `episode_contract_id` y
  `quality_contract_id` del benchmark;
- `rainmapper_core/mushroom_ml_comparison.py`: rechazar silencios o mezclas de
  versiones; no usar fallback de columnas.

## 2. Target operativo

### Resolución de una observación

Crear una función de dominio, separada del label visual, con una firma
equivalente a:

```python
resolve_modeling_target(
    *,
    valid: bool,
    calibration_use: str,
    flush_abundance: str | None,
    policy: TargetPolicy,
) -> Literal["favorable", "unfavorable", "unknown"]
```

Reglas en este orden:

1. `valid is not True` -> `unknown`;
2. `calibration_use != "include"` -> `unknown`;
3. `pending`, vacío o no reconocido -> `unknown`;
4. `very_scarce` o `absent` -> `unfavorable`;
5. `scarce`, `normal`, `abundant`, `very_abundant` o `exceptional` ->
   `favorable`.

El catálogo actual puede seguir sirviendo a v2. El nuevo resolver no debe
interpretar `pending=0` como evidencia negativa. El benchmark v3 materializa el
resultado y el hash de la política; el entrenamiento no vuelve a resolverlo.

Cambios previstos:

- `rainmapper_core/mushroom_observation_context.py`: nuevo resolver y metadata
  versionada de política;
- `rainmapper_core/mushroom_observation_features.py`: materializar el target v3
  o conservar suficientes campos para resolverlo al construir el benchmark;
- `rainmapper_core/mushroom_ml_trainer.py::filter_eligible`: consumir el target
  versionado, no inferirlo de cualquier `prediction_target` heredado.

### Canonicalización por microárea

Antes de agregar a área, agrupar por:

```text
(species_id, micro_area_id, observed_at)
```

Para cada grupo conservar:

- número de filas originales;
- abundancias y targets distintos;
- `target_conflict`;
- target canónico para utilidad de salida: favorable si alguna observación
  válida fue favorable; desfavorable si todas las conocidas fueron
  desfavorables; desconocido si ninguna fue conocida;
- abundancia máxima según el orden operativo del catálogo.

No borrar las filas originales ni corregir observaciones durante el benchmark.
La canonicalización es una vista derivada y auditable.

### Episodio de área

Agrupar las microáreas canónicas por:

```text
(species_id, area_id, observed_at)
```

Target:

- favorable si al menos una microárea conocida fue favorable;
- desfavorable si hay microáreas conocidas y todas fueron desfavorables;
- desconocido si ninguna microárea aportó target conocido.

Metadatos obligatorios:

```text
n_source_rows
n_microareas_observed
n_microareas_target_known
n_microareas_favorable
n_microareas_unfavorable
n_microareas_unknown
mixed_target
source_micro_area_ids
```

`mixed_target` no cambia automáticamente el target de «merecía la salida», pero
permite excluirlo en una comparación de positivos limpios y evita perder evidencia
local. Sobre las 399 observaciones actuales se reproducen 348 unidades canónicas
y 278 episodios: 188 favorables, 87 desfavorables y 3 desconocidos. Los 275 con
target conocido coinciden con la auditoría anterior. Hay 9 episodios mixtos
entre microáreas y 2 conflictos internos de microárea que la vista antigua
contaba incorrectamente como grupos de área mixtos.

Estas dos agrupaciones son vistas de auditoría, no unidades de entrenamiento.
El benchmark construye una muestra por cada observación original y usa el área
solo para materializar meteorología y relacionar floradas.

El módulo nuevo `rainmapper_core/mushroom_ml_biology_v3.py` ya implementa el
resolver, la vista canónica de microárea y la evidencia de área sin seleccionar
una fila meteorológica. Sustituir en el camino completo v3 de benchmark la
selección «fila con menos
`weather_gaps`». La meteorología debe construirse una sola vez para el área,
fecha y corte mediante el mismo selector de estación que usa inferencia. Si por
compatibilidad se recibe meteorología ya materializada, todas las filas deben
coincidir en estación, corte y serie o el episodio se marca inválido; no se
elige la versión más conveniente.

El fallback forma parte del contrato de cada muestra, no solo de la
reconstrucción de la observación:

1. calcular primero el corte efectivo (`T-7` en ventana ciega o `T-horizonte`
   en retardos/eventos);
2. ordenar las estaciones por distancia al punto representativo del área y
   limitar a 15 km;
3. calcular la calidad en ese corte después de aplicar las mismas reglas de
   ausencia y supresión de lluvia que consumirá el modelo;
4. escoger la primera estación que cumpla 19/21, 81/90 y las coberturas de
   temperatura/humedad; si la más cercana falla, continuar con las siguientes;
5. utilizar exactamente el mismo procedimiento en entrenamiento e inferencia.

No reutilizar una estación elegida por calidad en `T` para decidir que la serie
es válida en `T-7`, ni contar como observado un valor que después se marca como
suprimido. El benchmark debe guardar estación, distancia, rango, candidatas
descartadas, corte y recuentos de calidad efectivos por muestra. Es correcto que
dos contratos u horizontes elijan estaciones distintas cuando sus cortes
requieren días diferentes; debe quedar visible en metadatos.

### Lluvia espacial canónica

Biology V3 no usa la lluvia de una única estación como aproximación espacial.
La lluvia se materializa una sola vez por microárea y fecha mediante el contrato
`daily_rain_idw_radius15km_power2_v1`:

- punto objetivo: `representative_location` de la microárea; si falta, centroide
  trazable de su geometría guardada;
- todas las estaciones activas con observación diaria utilizable dentro de 15
  km;
- peso `1 / max(distancia_km, 0,1)^2`;
- el cero observado participa como cero; ausencia, error, valor negativo,
  lluvia diaria superior a 300 mm, repetición positiva consecutiva suprimida o
  estación retirada no participan;
- si no queda ninguna estación utilizable, el día es ausente, nunca cero;
- la serie conserva por día valor IDW, número de estaciones contribuyentes,
  distancia más próxima y contadores de calidad fuera de `X`.

La fórmula es la misma del IDW de MapLibre. No se copia al modelo el gate visual
de pintura del mapa, porque depende de la escala de color y no es una regla
meteorológica. La equivalencia se comprobó el 2026-08-13 sobre una copia local
del histórico vivo: para `42.01333, 1.97155` y la ventana cerrada
`2026-08-06…2026-08-12`, el IDW diario sumó `46,003 mm` y el IDW directo de los
acumulados Tomap redondeados `46,059 mm`.

Temperatura y humedad relativa del aire conservan inicialmente el selector
sensible al corte de V2. La corrección térmica por altitud se aplica solo a la
temperatura. Sustituirlas también por un campo espacial
sería otro contrato y exige una comparación separada.

Al agregar varias microáreas a un episodio de área se aplica el contrato
`area_daily_mean_microarea_idw_v1`: para cada día se calcula la media aritmética
de los IDW disponibles de **todas sus microáreas configuradas**. Una microárea
sin dato no participa; el día del área solo es ausente si ninguna aporta valor.
No se usa el IDW del centroide del polígono del área: ese punto ya es una
geometría calculada y no una localización de evidencia.

La decisión quedó comprobada sobre 7.262 días-área de 12 áreas reales con más
de una microárea: diferencia mediana frente al centroide de 0,001 mm, p95 de
0,62 mm, p99 de 1,89 mm y máximo de 7,89 mm. El 79,3 % difirió como máximo 0,1
mm. La dispersión máxima entre microáreas alcanzó 43,94 mm; en Sant Joan el
centroide dio 34,94 mm mientras las microáreas iban de 34,53 a 54,07 mm y su
media fue 42,82 mm. Aunque ambos métodos suelen aproximarse, el centroide puede
ocultar tormentas locales. El modelo acepta la media IDW como lluvia canónica,
sin penalización, intervalo de incertidumbre ni advertencia operativa.

## Decisiones que faltan para cerrar Biology V3

Esta es la lista canónica; las tareas de implementación no se cuentan como
decisiones nuevas:

1. **Agregación espacial de lluvia a área — CERRADA.** Media diaria de los IDW
   disponibles de todas las microáreas configuradas; nunca IDW del centroide
   calculado del área.
2. **Unidad de entrenamiento — CERRADA.** La observación original es la muestra
   de aprendizaje y nunca se elimina por pertenecer a la misma fecha o florada
   que otra. Las vistas `especie + microárea + fecha` y
   `especie + área + fecha` resuelven conflictos y resumen evidencia para
   auditoría, pero no reemplazan las observaciones originales. El área
   materializa la meteorología y delimita floradas; no entra en X ni segmenta
   el modelo común de cada especie.
3. **Corte temporal — CERRADO para evaluación.** `fixed_gap_7d` es la vista
   principal por corresponder a la salida semanal; `lag_event` permanece como
   diagnóstico en horizontes 1, 2, 3 y 7. La partición es cronológica 70/30 por
   especie con grupos completos de 14 días; 7 días es sensibilidad.
4. **Variables posteriores a lluvia — CERRADO para el benchmark inicial.** Se calculan y conservan con
   estado inactivo en la predicción mínima mientras no exista un episodio de
   lluvia. Se activarán si su significado es único y la comparación demuestra
   que ayudan de forma estable; nunca se borran del registro.
5. **Validación principal — CERRADA.** Comparar separación cronológica y
   agrupaciones conservadoras de observaciones relacionadas. Las ventanas de
   7/14 días representan respectivamente floradas cortas y largas como regla
   biológica general. Una florada real es de especie+área y su continuidad
   depende de que se mantengan las condiciones; ninguna observación se fusiona
   o descarta al agrupar la validación.
6. **Gate de promoción — CERRADO y no superado.** Comparar V2/V3 sobre las
   mismas filas y corte predeclarado; exigir mejora repetible de Brier en 7/14
   días, calibración/log loss no peores y ausencia de regresiones graves por
   especie con soporte suficiente. La evaluación emparejada usa 167 muestras
   semanales comunes. Los Brier combinados entre especies quedan como
   diagnóstico y nunca deciden el gate; la decisión es por especie, estimador y
   contrato, frente a la prevalencia de entrenamiento de esa especie. El
   soporte actual no autoriza una promoción operativa.
7. **Elevación transfronteriza — cadena local cerrada para las áreas actuales.**
   El DEM Catalunya conserva prioridad, el MDE oficial de Andorra 5 m actúa
   como segundo origen y el MDT25 del IGN, hoja MTN50 592, como tercero. Una
   prueba masiva resolvió las 58/58 microáreas actuales.

### Procedencia meteorológica — auditoría interna, no incertidumbre operativa

AEMET y Meteocat son redes oficiales; Meteoclimatic y Wunderground contienen
observaciones comunitarias sin una auditoría homogénea. Esto no excluye ni
penaliza las estaciones comunitarias: todas las estaciones válidas participan
con el mismo peso IDW determinado exclusivamente por distancia. Pueden aportar
la mejor evidencia disponible de una tormenta local que no alcanzó una estación
oficial próxima.

El modelo usa el resultado como la lluvia canónica del punto y no muestra un
«sí, pero» en la predicción. Fuentes, estaciones participantes, número de
contribuyentes y distancias se conservan solo como procedencia técnica para
reproducir o investigar el cálculo. No entran en `X`, no alteran el peso por
fuente, no reducen la probabilidad predicha y no generan advertencias en la UI.

### Regla de incertidumbre operativa

Biology V3 expresa la incertidumbre inevitable de una predicción futura en su
probabilidad calibrada y su dictamen. No reabre en cada respuesta las asunciones
de contratos meteorológicos ya aceptados. La UI ordinaria no muestra cautelas
por interpolación, fuente comunitaria, dispersión o corrección térmica. Esos
datos son auditoría interna. Solo se muestra un problema si es accionable o si
falta por completo una entrada obligatoria y el motor debe abstenerse.

## 3. Separar biología, calidad y metadatos

### Forma del benchmark

Cada muestra v3 debe tener tres espacios distintos:

```json
{
  "predictive_features": {},
  "quality": {},
  "metadata": {}
}
```

El entrenador solo acepta columnas declaradas en
`feature_set.predictive_feature_cols`. Una aserción debe fallar si un campo
declarado como quality aparece en `X`.

### Candidatas predictivas

La primera versión del benchmark conserva como **candidatas para comparación**, no
como conjunto ganador:

```text
target_month_sin
target_month_cos
gis_altitude_m
rain_cutoff_0_3d_mm
rain_cutoff_4_7d_mm
rain_cutoff_8_14d_mm
rain_cutoff_15_21d_mm
rain_cutoff_22_30d_mm       # experimental, se conserva para comparar
rain_cutoff_31_60d_mm       # experimental, se conserva para comparar
rain_cutoff_61_90d_mm       # experimental, se conserva para comparar
days_since_rain_gt_2_at_target
days_since_significant_rain_at_target
dry_spell_observed_at_cutoff
temp_mean_after_significant_rain_c
humidity_mean_after_significant_rain_pct
temp_max_cutoff_7d_c
temp_min_cutoff_7d_c
humidity_max_cutoff_0_3d_pct
humidity_min_cutoff_0_3d_pct
humidity_max_cutoff_4_7d_pct
humidity_min_cutoff_4_7d_pct
humidity_max_cutoff_8_14d_pct
humidity_min_cutoff_8_14d_pct
humidity_max_cutoff_15_21d_pct
humidity_min_cutoff_15_21d_pct
temp_max_mean_cutoff_7d_c
temp_min_mean_cutoff_7d_c
temp_mean_cutoff_7d_c
horizon_days  # solo lag_event_biology_v3
```

Esta lista deliberadamente permite crear benchmarks comparativos. No autoriza
entrenar un modelo final con todas las columnas. El informe debe resaltar las
familias correlacionadas: temperaturas, relojes de lluvia y variables
posteriores al evento.

Los acumulados disjuntos permiten aprender cantidad y periodo sin imponer un
mínimo biológico. Las ventanas 22–30, 31–60 y 61–90 se conservan inicialmente
como experimentales. Los relojes heredados de 2 y 5 mm se calculan y comparan,
pero permanecen inactivos en X por defecto: son umbrales humanos heredados, no
gates de fructificación ni cantidades mínimas asumidas.

El registro implementado marca como activas por defecto las ventanas de lluvia
0–3, 4–7, 8–14 y 15–21 días, racha seca observada, extremos de temperatura V2
corregidos en siete días y extremos de humedad relativa en las mismas cuatro
ventanas temporales que la lluvia.
Estacionalidad y altitud directa quedan inactivas tras la comparación emparejada:
la altitud sigue aplicada a la corrección de temperatura. Todas las medias de
temperatura y humedad relativa, las ventanas largas de lluvia y los relojes de
2/5 mm están inactivos. Inactivo significa que el campo se sigue
calculando, validando y documentando, pero no entra en la predicción mínima y
puede reactivarse sin reconstruir su definición.

### Ejes y consenso de la evaluación

La palabra «modelo» no sustituye indistintamente a especie, contrato o
algoritmo. Un modelo ajustado queda definido por una especie, un contrato
temporal y un estimador. Los seis estimadores reciben las mismas columnas en
cada ejecución. Se comparan las 15 parejas por especie sobre las mismas filas
reservadas, publicando diferencia de probabilidad, coincidencia respecto a 0,5
y proporciones de consenso alto/moderado/bajo. Coincidir no basta: ambos
estimadores deben superar el Brier de prevalencia de la especie.

### Quality, nunca X

Mover fuera de `feature_cols`:

```text
rain_observed_days_21
rain_missing_days_21
rain_suppressed_days_21
rain_observed_days_90
rain_missing_days_90
rain_suppressed_days_90
dry_spell_is_censored
temp_observed_days_after_significant_rain
humidity_observed_days_after_significant_rain
daily_series_aligned
enough_history
rain_event_search_complete
significant_rain_search_complete
temperature_altitude_correction_available
station_quality_eligible
```

`significant_rain_found_90d` se guarda inicialmente en metadata/quality, no en
X. La edad capada a 90 ya expresa «90 días o más». Solo volverá a ser predictor
si una comparación demuestra que distingue de forma estable un evento en el borde
de la ventana de un no-evento.

### Variables posteriores al episodio — estado inicial cerrado

No se mantiene una variable con dos significados. Cuando no se encuentra lluvia
significativa, `temp/humidity_after_significant_rain` valen `None`; nunca se
transforman silenciosamente en una media de 90 días. Permanecen calculadas,
validadas y documentadas, pero inactivas por defecto hasta que una comparación
estable justifique reactivarlas. Si se necesita una media general de 90 días se
creará otra variable con ese nombre y significado. No se imputa la ausencia de
un evento con la mediana de episodios que sí lo tuvieron.

### Gate de calidad

El benchmark puede contener todas las muestras para auditoría, pero debe
materializar `training_eligible` y motivos. Mínimo actual:

- estación elegible dentro de 15 km;
- lluvia >=19/21 y >=81/90;
- temperatura y humedad >=19/21;
- series alineadas e histórico suficiente;
- altitud de estación y área disponibles para el contrato corregido;
- variables predictivas activas requeridas disponibles.

Una muestra no elegible no entra en entrenamiento ni se convierte en una fila
de medianas. El informe muestra recuentos antes/después por especie y clase. El
benchmark local preserva 399 muestras y deja 204 elegibles en `fixed_gap`; para
los cuatro horizontes de `lag_event` preserva 1.596 y deja 816 elegibles. Estos
conteos describen el snapshot y sus hashes, no son constantes de código. El
informe explica las
transiciones `sin estación elegible`, `estación inicial descartada`, `fallback
seleccionado`, `sin alternativa` y `altitud ausente`.

### Backfill histórico auditable

La ausencia en `weather_daily.parquet` no equivale a ausencia en los archivos
de la fuente. Antes de descartar definitivamente los episodios 2012–2022 se
implementará una herramienta de auditoría/backfill dirigida por las ventanas
que realmente necesita el benchmark:

- salida y caché únicamente bajo `docker-data` durante el laboratorio;
- backfill continuo de todas las estaciones conocidas de Meteocat y AEMET, más
  todas las PWS de la lista configurada de Wunderground, desde 150 días antes de
  la primera observación elegible hasta el día anterior al comienzo del
  histórico local de cada fuente; se une con lo existente sin reemplazarlo y el
  radio de 15 km se aplica después al selector, no a la adquisición;
- descargas fragmentadas según el límite de cada API, reanudables e
  idempotentes;
- normalización provisional separada del Parquet operativo;
- identidad `(source, station_id, local_date)`, unidades originales y
  normalizadas, procedencia, hora de descarga y flags de calidad conservados;
- informe de cobertura antes/después por episodio, contrato, estación, fuente,
  variable y motivo de rechazo;
- ninguna escritura o promoción a HA sin una fase posterior de validación y
  aceptación explícita.

El helper AEMET actual acepta un número arbitrario de días y fragmenta las
peticiones, pero genera artefactos CSV orientados al backfill reciente; debe
envolverse o ampliarse para ventanas históricas selectivas. Wunderground ya
acepta rangos locales, pero no debe confundirse capacidad de consulta histórica
con existencia real de la PWS en años anteriores. La integración Meteocat usa
actualmente los datasets Socrata públicos, pero el Parquet auditado no contiene
todo el archivo oficial disponible: el laboratorio debe tratar la recuperación
histórica como una operación distinta de la actualización incremental normal.

### Materialización y cobertura de elevación

La altitud representativa del área no puede depender únicamente del DEM 5 m de
Catalunya. El proveedor de elevación debe soportar una cadena de fuentes:

1. DEM principal de Catalunya cuando la celda tenga valor;
2. MDE oficial de Andorra 5 m cuando el principal devuelva `NoData`;
3. MDT25 del IGN, hoja MTN50 592, cuando las dos fuentes anteriores no cubran
   la geometría;
4. `area_altitude_missing` y muestra no elegible si ninguna fuente responde.

La altitud se calcula una sola vez al crear o cambiar la geometría de una
microárea y queda cacheada en `known_sites`; guardar sin cambiar el polígono,
construir benchmarks o predecir no vuelve a consultar el DEM. La prueba masiva
sobre copia resolvió las 58/58 microáreas actuales: 396 muestras Catalunya, 9
Andorra y 15 IGN. Puertomingalvo se resuelve mediante la hoja 592 con medias de
1.329,6 m y 1.279,9 m para sus dos microáreas. Una microárea futura fuera de las
tres coberturas seguirá devolviendo `no_data`, sin valores inventados.

Cada valor materializado guardará fuente, versión o fecha, resolución y método
de agregación sobre el área/microáreas. No inferir altitud desde nombres ni
añadir excepciones hardcoded por área. Ordino/2026-06-13 es el caso de aceptación:
el DEM catalán falla de forma explícita y el secundario resuelve 2063,2 m en el
centro del área. En la observación con GPS independiente devuelve 2073,5 m
frente a 2080 m del iPhone. El formato, procedencia y hashes están en
`mushroom-GIS/dem-andorra/README.md`.

## Particiones y dependencia entre salidas — contrato aclarado

Conservar la partición 70/30 por fecha existente para comparabilidad y añadir
diagnósticos que mantengan juntas observaciones probablemente dependientes:

- mismo `species_id` y `area_id`;
- fechas separadas <=7 días se enlazan en un grupo diagnóstico conservador;
- ningún grupo cruza train/test;
- repetir como sensibilidad con 14 días, sin elegir el que dé mejor resultado;
- cada observación permanece como una muestra y conserva su target y abundancia.

Los grupos de 7 y 14 días representan la duración general de floradas cortas y
largas. La continuidad concreta sigue siendo un estado por especie+área que
depende de la meteorología; una ruptura clara de condiciones puede separar dos
floradas dentro del máximo temporal. La partición principal final se decidirá
tras comparar fecha, ambos tipos de florada y continuidad meteorológica. El
benchmark materializa las relaciones; el entrenador no las recalcula ni agrega
sus observaciones. Este marco 7/14 es común a las especies objetivo; no se crean
duraciones distintas por especie sin evidencia posterior suficiente.

## Suficiencia por especie

Publicar en benchmark e informe:

```text
n_observations_total
n_observations_training_eligible
n_area_date_evidence_views
n_favorable
n_unfavorable
n_validation_groups_7d
n_validation_groups_14d
minority_class_count
data_sufficiency_tier
```

Tiers descriptivos:

- `independent_diagnostic`: dos clases y muestra mínima suficiente para un
  diagnóstico independiente pequeño;
- `exploratory_only`: dos clases, pero alguna es demasiado pequeña;
- `single_class`: imposible clasificar por especie;
- `no_training_data`.

No convertir estos nombres en una afirmación de fiabilidad. Cada informe debe
mostrar los números que justifican el tier.

## Pruebas obligatorias

### Target y episodios

- `pending`, `review`, inválido, vacío y desconocido -> `unknown`;
- `very_scarce` -> desfavorable y `scarce` -> favorable;
- duplicados de microárea no aumentan `n_microareas_observed`;
- conflicto de una microárea conserva detalle y resuelve utilidad de salida;
- episodio mixto conserva recuentos y `mixed_target=true`;
- episodio completamente desfavorable sigue siendo desfavorable;
- los 11 grupos mixtos del snapshot se reproducen.

### Separación de variables

- ninguna columna de quality aparece en `X`;
- cambiar solo un contador de cobertura no cambia la predicción si la muestra
  continúa elegible;
- bajar la cobertura por debajo del gate excluye la muestra con motivo legible;
- una fecha sin estación/altitud no se imputa como meteorología típica;
- train e inferencia generan exactamente las mismas predictive features.

### Versionado

- las listas y metadatos v2 permanecen idénticos;
- cargar un bundle con otro target/episode/quality contract falla;
- hashes de fuentes y particiones quedan en benchmark y bundle;
- la reconstrucción del snapshot produce 399 observaciones, 350 incluibles,
  275 episodios y los recuentos por especie documentados en la auditoría.

## Secuencia de implementación recomendada

1. [Hecho] Mantener V2 congelado y separado por IDs.
2. [Hecho] Implementar resolver de target y canonicalización de microáreas.
3. [Hecho en el módulo v3] Producir evidencia de área sin
   elegir la fila con menos gaps.
4. [Hecho como fundamento meteorológico] Materializar IDW diario por microárea,
   sin ceros inventados y excluyendo estaciones retiradas.
5. [Hecho] Separar el payload del benchmark en `predictive_features`, `quality` y
   `metadata`.
6. [Hecho] Añadir gates y recuentos de suficiencia sin entrenar modelos.
7. [Hecho] Generar el benchmark local y comparar sus conteos contra la auditoría.
8. [Hecho sin modelo persistente] Comparar configuraciones y V2/V3 mediante los
   seis estimadores exactos, por especie y con consenso fila a fila; el informe
   declara `model_artifact_written=false`.

## Criterio de cierre de esta implementación

La tarea termina cuando el benchmark sucesor es reproducible, auditable y
separa correctamente target, unidad, features y calidad. Que Edulis o Pinícola
produzcan una cifra «más razonable» no es criterio de aceptación. No se publica
ni se promociona ningún modelo como parte de este cambio.
