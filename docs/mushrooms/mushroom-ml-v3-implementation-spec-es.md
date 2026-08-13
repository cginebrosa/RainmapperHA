# Especificación de implementación del sucesor de v2

Estado: **ESPECIFICADO, NO IMPLEMENTADO**. Documento de traspaso para ejecutar
con otro agente/modelo después de la auditoría
`mushroom-ml-v3-data-audit-es.md`.

La tarea no consiste en retocar v2 hasta que produzca resultados más
plausibles. Debe crear contratos nuevos, reproducibles y comparables, dejando
v2 como referencia inmutable.

## Alcance

Implementar solamente:

1. congelación reproducible de los contratos v2;
2. target operativo y unidad de episodio explícitos;
3. separación estricta entre variables predictivas y calidad/censura;
4. benchmark sucesor listo para ablaciones posteriores.

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
feature_set_id: fixed_gap_7d_biology_v3
feature_set_id: lag_event_biology_v3
```

Si se cambian estos nombres durante la implementación, el cambio debe quedar en
una ADR/decisión antes de generar el primer benchmark. Nunca se reutiliza un ID
para otra lista de columnas o semántica.

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
permite excluirlo en una ablación de positivos limpios y evita perder evidencia
local. La auditoría actual debe reproducir exactamente 11 grupos mixtos.

Sustituir en `aggregate_to_area_episodes` la selección «fila con menos
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

La primera versión del benchmark conserva como **candidatas para ablación**, no
como conjunto ganador:

```text
target_month_sin
target_month_cos
gis_altitude_m
rain_cutoff_0_3d_mm
rain_cutoff_4_7d_mm
rain_cutoff_8_14d_mm
rain_cutoff_15_21d_mm
days_since_rain_gt_2_at_target
days_since_significant_rain_at_target
dry_spell_observed_at_cutoff
temp_mean_after_significant_rain_c
humidity_mean_after_significant_rain_pct
temp_max_mean_cutoff_7d_c
temp_mean_cutoff_7d_c
horizon_days  # solo lag_event_biology_v3
```

Esta lista deliberadamente permite crear benchmarks de ablación. No autoriza
entrenar un modelo final con todas las columnas. El informe debe resaltar las
familias correlacionadas: temperaturas, relojes de lluvia y variables
posteriores al evento.

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
si una ablación demuestra que distingue de forma estable un evento en el borde
de la ventana de un no-evento.

### Semántica posterior al episodio

No mantener una variable con dos significados. Actualmente, cuando no se
encuentra lluvia significativa, la «media posterior a lluvia» pasa a ser una
media de 90 días. v3 debe elegir de forma explícita una de estas opciones:

1. dejar `temp/humidity_after_event` como no aplicable sin episodio y usar un
   estimador que trate ese estado explícitamente; o
2. crear otra variable con nombre real, por ejemplo `temp_mean_lookback_90d_c`.

No imputar la ausencia de un evento con la mediana de episodios que sí lo
tuvieron. Para el benchmark inicial se recomienda conservar ambos valores en
metadata, pero excluir `*_after_significant_rain` del conjunto mínimo hasta que
la ablación decida su semántica.

### Gate de calidad

El benchmark puede contener todas las muestras para auditoría, pero debe
materializar `training_eligible` y motivos. Mínimo actual:

- estación elegible dentro de 15 km;
- lluvia >=19/21 y >=81/90;
- temperatura y humedad >=19/21;
- series alineadas e histórico suficiente;
- altitud de estación y área disponibles para el contrato corregido;
- variables predictivas requeridas por la ablación disponibles.

Una muestra no elegible no entra en entrenamiento ni se convierte en una fila
de medianas. El informe muestra recuentos antes/después por especie y clase. Con
el snapshot auditado, la reproducción del artefacto vigente debe mostrar 275
episodios totales y 122 meteorológicamente utilizables con el conjunto completo
de candidatas. Tras aplicar el selector sensible al corte y a lluvia depurada,
18 episodios recientes deben recuperarse mediante otra estación dentro de
15 km, de modo que el mismo snapshot alcance al menos 140 utilizables sin
rellenar los episodios históricos sin cobertura.

No fijar 122 ni 140 como constantes de código: son aserciones de reproducción y
aceptación ligadas a los hashes de esta auditoría. El informe debe explicar las
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

### Cobertura de elevación transfronteriza

La altitud representativa del área no puede depender únicamente del DEM 5 m de
Catalunya. El proveedor de elevación debe soportar una cadena de fuentes:

1. DEM principal de Catalunya cuando la celda tenga valor;
2. DEM secundario trazable con cobertura transfronteriza cuando el principal
   devuelva `NoData`;
3. `area_altitude_missing` y muestra no elegible si ninguna fuente responde.

Cada valor materializado guardará fuente, versión o fecha, resolución y método
de agregación sobre el área/microáreas. No inferir altitud desde nombres ni
añadir excepciones hardcoded por área. Ordino/2026-06-13 es el caso de aceptación:
el DEM catalán debe fallar de forma explícita y el secundario, cuando exista,
debe resolver la cota o conservar la abstención explicada.

## Particiones y dependencia entre salidas

Conservar la partición 70/30 por fecha ya existente para comparabilidad, pero
añadir un diagnóstico agrupado por florada:

- mismo `species_id` y `area_id`;
- fechas consecutivas separadas <=7 días pertenecen al mismo grupo;
- ningún grupo cruza train/test;
- repetir como sensibilidad con 14 días, sin elegir el que dé mejor resultado.

La partición principal final se decidirá después de comparar fecha frente a
grupo de florada. El benchmark materializa ambas; el entrenador no las
recalcula.

## Suficiencia por especie

Publicar en benchmark e informe:

```text
n_episodes_total
n_episodes_training_eligible
n_favorable
n_unfavorable
n_fruiting_clusters_7d
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

1. Añadir tipos/IDs y pruebas de congelación v2.
2. Implementar resolver de target y canonicalización de microáreas.
3. Sustituir `aggregate_to_area_episodes` para producir evidencia de área sin
   elegir la fila con menos gaps.
4. Separar el payload del benchmark en `predictive_features`, `quality` y
   `metadata`.
5. Añadir gate y recuentos de suficiencia sin entrenar modelos.
6. Generar el benchmark local y comparar sus conteos contra la auditoría.
7. Solo después implementar ablaciones/entrenamiento en otra tarea.

## Criterio de cierre de esta implementación

La tarea termina cuando el benchmark sucesor es reproducible, auditable y
separa correctamente target, unidad, features y calidad. Que Edulis o Pinícola
produzcan una cifra «más razonable» no es criterio de aceptación. No se publica
ni se promociona ningún modelo como parte de este cambio.
