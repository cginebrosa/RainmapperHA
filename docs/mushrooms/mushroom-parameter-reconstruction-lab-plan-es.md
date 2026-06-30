# Plan del laboratorio de reconstruccion de parametros de setas

Este documento es la guia viva para disenar y ejecutar el laboratorio local que reconstruira condiciones observadas de floradas de setas y, mas adelante, propondra parametros candidatos por especie.

No es todavia una especificacion cerrada del predictor productivo. Su funcion es ordenar el trabajo incremental para que cada decision quede trazada, revisable y separada de los datos productivos de Home Assistant.

Documentos relacionados:

- `docs/mushrooms/mushroom-local-observation-lab-es.md`
- `docs/mushrooms/mushroom-predictor-design-es.md`
- `docs/mushrooms/mushroom-observations-schema-es.md`
- `docs/mushrooms/mushroom-gis-mappings-reference-es.md`
- `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`
- `docs/history-safety.md`

## Objetivo

Construir un laboratorio local que use observaciones reales/historicas del usuario, fotos EXIF, historicos meteorologicos de Rainmapper y futuras capas GIS/DEM para reconstruir las condiciones observadas antes de cada salida o recolecta.

El resultado esperado no es "el predictor definitivo", sino una base verificable para responder preguntas como:

- que lluvia acumulada habia 1/7/14/21/30/60/90 dias antes de una observacion;
- que temperatura, humedad y viento estaban disponibles en el historico;
- que datos faltan por fuente, fecha o estacion;
- que diferencias aparecen entre observaciones positivas y negativas;
- que parametros candidatos por especie podrian revisarse manualmente mas adelante.

## Reglas criticas

- No escribir en Home Assistant real.
- No modificar automaticamente `mushroom_profiles.json`.
- No versionar fotos, coordenadas reales, observaciones reales, historicos HA ni capas GIS.
- No inventar umbrales, pesos, ventanas meteorologicas ni parametros de especie.
- Si un dato no existe o no se puede reconstruir, marcarlo como gap.
- Si una deduccion es una hipotesis, mantenerla fuera del motor numerico productivo.
- Si se usa un umbral global exploratorio, debe quedar marcado como `experimental_analysis_threshold`, no como parametro de especie.
- Cualquier cambio que escriba historicos CSV debe seguir `docs/history-safety.md`. La primera fase debe limitarse a lectura de `docker-data/Data` y escritura de salidas experimentales bajo `tmp/mushroom-lab/`.

## Datos de entrada

Entradas locales esperadas:

```text
docker-data/mushroom-data/mushroom_observations.json
docker-data/mushroom-data/mushroom_profiles.json
docker-data/mushroom-data/mushroom_reference_catalogs.json
docker-data/mushroom-data/mushroom_gis_mappings.json
docker-data/mushroom-data/mushroom_labels.json
docker-data/Data/
```

El extractor meteorologico debe usar los incrementales historicos de `docker-data/Data/`, no los GeoJSON actuales, porque muchas observaciones pueden ser de anos anteriores.

Si falta un incremental necesario, la salida correcta es reportar el gap y pedir copia desde HA si hace falta. No se deben rellenar datos a partir de supuestos.

## Salidas experimentales

Salidas iniciales previstas:

```text
tmp/mushroom-lab/working/observations/observations_normalized.json
tmp/mushroom-lab/working/features/observations_weather_features.csv
tmp/mushroom-lab/working/features/observations_weather_features.json
tmp/mushroom-lab/output/reports/observations_weather_features.md
```

Salidas posteriores:

```text
tmp/mushroom-lab/working/features/observations_gis_features.csv
tmp/mushroom-lab/output/parameter-candidates/species_parameter_candidates.json
tmp/mushroom-lab/output/reports/species_observed_conditions.md
```

Estas salidas son locales, ignoradas por Git y revisables manualmente.

## Fase 1: extractor meteorologico local

Objetivo:

Reconstruir condiciones meteorologicas previas por observacion desde los incrementales de Rainmapper.

Alcance inicial:

- leer observaciones activas y utiles para analisis;
- normalizar fecha, especie, resultado, abundancia, coordenadas, altitud, validacion, calidad de fuente y uso de calibracion;
- leer incrementales disponibles en `docker-data/Data/`;
- calcular lluvia acumulada previa en ventanas 1/7/14/21/30/60/90 dias;
- calcular temperatura, humedad y viento disponibles cuando existan;
- reportar estacion/fuente usadas, distancia, cobertura temporal y gaps;
- escribir CSV/JSON y reporte humano;
- no generar todavia candidatos de parametros productivos.

Campos minimos esperados por observacion:

```text
observation_id
species_id
observed_at
result
abundance
validation_status
calibration_use
source_quality
latitude
longitude
altitude_m
weather_method
weather_source
weather_station_code
weather_station_distance_km
rain_1d_mm
rain_7d_mm
rain_14d_mm
rain_21d_mm
rain_30d_mm
rain_60d_mm
rain_90d_mm
temp_min_c
temp_max_c
temp_mean_c
humidity_min_pct
humidity_max_pct
humidity_mean_pct
wind_avg_kmh
wind_gust_kmh
wind_direction_deg
data_gaps
```

Los nombres exactos pueden ajustarse al implementar, pero la salida debe conservar trazabilidad suficiente para revisar cada fila.

## Metodo meteorologico inicial

Decision inicial prudente:

- usar estacion cercana como primer POC;
- registrar distancia y fuente;
- evitar interpolacion hasta comprobar calidad de datos y cobertura;
- no mezclar varias fuentes sin explicar la decision.

Decisiones pendientes antes o durante la implementacion:

- elegir si el primer POC selecciona la estacion mas cercana global, por fuente, o por disponibilidad en la ventana;
- definir distancia maxima aceptable antes de marcar gap;
- decidir si lluvia, temperatura, humedad y viento deben venir de la misma estacion o pueden usar estaciones/fuentes distintas con trazabilidad separada;
- decidir si se calcula `days_since_significant_rain` en la primera version o se deja para una segunda iteracion;
- si se calcula, definir el umbral como global exploratorio y documentarlo como no productivo;
- decidir si se incluyen observaciones `draft` en modo diagnostico o solo observaciones validadas/aceptadas.

## Tratamiento de observaciones

La primera version debe separar claramente:

- observaciones positivas;
- observaciones negativas o ausencias;
- observaciones dudosas;
- observaciones archivadas;
- observaciones excluidas de calibracion;
- observaciones validas pero con gaps meteorologicos.

Regla inicial recomendada:

- incluir en salidas diagnosticas todas las observaciones activas parseables;
- marcar `analysis_included` y `analysis_exclusion_reason`;
- usar para resumen principal solo observaciones con estado y uso compatibles con calibracion, segun el criterio documentado en el script/reporte.

No debe desaparecer una observacion silenciosamente.

## Fase 2: DEM y topografia

Objetivo:

Enriquecer cada observacion con contexto topografico reproducible.

Salidas candidatas:

- altitud DEM;
- diferencia entre altitud EXIF/manual y DEM;
- pendiente;
- orientacion;
- posible proxy topografico de humedad si se documenta y se valida.

Fuentes candidatas:

- ICGC/ICC para Catalunya;
- IGN/CNIG para Espana.

No usar WMS como fuente primaria de atributos. WMS sirve para inspeccion visual, no para calculo reproducible.

## Fase 3: cubiertas, vegetacion, litologia y suelo

Objetivo:

Cruzar cada observacion con capas estaticas de habitat.

Reglas:

- documentar fuente, licencia, cobertura, resolucion, CRS, capa, campo y valores usados;
- usar `mushroom_gis_mappings.json` para traducir codigos externos a IDs internos;
- si falta mapping, reportar gap;
- no inferir equivalencias por texto libre o intuicion.

## Fase 4: candidatos de parametros por especie

Objetivo:

Resumir condiciones observadas por especie y proponer candidatos solo cuando haya soporte suficiente.

Salida conceptual:

```json
{
  "species_id": "boletus_aereus",
  "candidate_id": "weather_model.rainfall.rain_15d_optimal_min_mm",
  "current_value": 35,
  "candidate_value": null,
  "evidence_type": "local_observations",
  "observation_ids": ["obs_20250806_0001"],
  "positive_count": 1,
  "negative_count": 0,
  "confidence": "insufficient_data",
  "status": "experimental",
  "notes": "Not enough local observations to propose a numeric candidate."
}
```

Con pocas observaciones, el resultado correcto puede ser describir condiciones observadas y dejar `candidate_value` vacio.

## Fase 5: promocion manual

Un candidato nunca debe sobrescribir automaticamente una ficha de especie.

Flujo futuro recomendado:

1. Recalcular condiciones observadas y candidatos.
2. Mostrar valor actual, rango observado, candidato, soporte y gaps.
3. Comparar positivas y negativas cuando existan.
4. Permitir aplicar manualmente campos concretos.
5. Guardar con validacion, backup y trazabilidad.

El boton productivo de HA queda fuera del alcance hasta que el laboratorio local este validado.

## Validacion minima de la primera implementacion

Antes de considerar util el primer extractor:

- revisar que no escribe fuera de `tmp/mushroom-lab/`;
- ejecutar tests con fixtures sinteticos sin datos reales;
- ejecutar el extractor contra `docker-data/` en modo lectura;
- revisar conteo de observaciones leidas, incluidas, excluidas y con gaps;
- comprobar manualmente varias observaciones conocidas;
- confirmar que las ventanas 1/7/14/21/30/60/90 respetan la fecha de observacion;
- confirmar que faltas de historico quedan como gaps;
- confirmar que no se modifica `docker-data/mushroom-data/*.json` ni `docker-data/Data/*.csv`.

## Estado actual

Estado al crear este plan:

- HA sigue en `0.2.180`.
- El laboratorio local y la UI de observaciones ya permiten cargar observaciones reales en `docker-data/`.
- El contenedor `rainmapper-ha-ui` estaba parado en el cierre previo.
- El siguiente trabajo tecnico sera implementar la Fase 1 como extractor local experimental.
- Este documento sera la guia que se ira adaptando segun decisiones sobre metodo meteorologico, DEM/GIS y generacion de candidatos.
