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

## Cambio de direccion 2026-07-01: predictor inicial mas simple

El trabajo hecho no se deshace: observaciones, GIS mappings, catalogos, DEM y
reconstructor siguen siendo piezas utiles. El cambio acordado es usar menos
parametros en la v0 del predictor y hacer que esos parametros reflejen mejor la
literatura fiable realmente disponible. El laboratorio no debe intentar arrancar
con una taxonomia geologica fina ni con un predictor complejo. La direccion es
construir primero un predictor explicable basado en las mismas senales amplias
que suelen aparecer en fichas micologicas y guias de campo:

- vegetacion o bosque asociado;
- arboles huesped o arboles acompanantes cuando sean relevantes;
- tipo de suelo amplio: acido/siliceo, calcario/basico, arenoso, humedo,
  yesifero o variable;
- altitud aproximada;
- temporada;
- rasgos simples de habitat, por ejemplo ribera, bosque montano, sotobosque
  humedo o zonas abiertas.

Las capas GIS siguen siendo necesarias, pero su papel cambia: deben clasificar
cada punto del mapa en esas caracteristicas internas simples. La geologia,
vegetacion, sustrato y DEM son traductores de contexto; no son por si mismos el
modelo predictivo. Por ejemplo, una descripcion GIS de pizarra puede servir como
evidencia de tendencia `soil_siliceous`/`soil_acidic`, pero el predictor inicial
no deberia requerir que una especie "prefiera pizarra" salvo que una fuente
fiable lo diga explicitamente.

La meteorologia de los incrementales de Rainmapper se combina despues con esa
aptitud estatica del punto. El flujo conceptual queda:

```text
punto del mapa
  -> DEM/GIS: altitud, vegetacion, host probable, suelo amplio, habitat
  -> perfiles/literatura: especies compatibles con ese contexto
  -> incrementales meteorologicos: lluvia, temperatura, humedad, viento previos
  -> observaciones reales: calibracion local y candidatos revisables
```

La primera carga de conocimiento por especie puede venir de fichas escaneadas o
libros revisados por el usuario, pero debe convertirse a datos normalizados y
revisables. No debe copiar texto largo de las fuentes ni fijar umbrales
meteorologicos por intuicion. El output inicial recomendado es un JSON
experimental de seed literario, separado de perfiles productivos, con campos de
suelo, vegetacion, habitat, altitud/temporada aproximadas y estado
`needs_review`.

Despues, las observaciones reales deben servir para inferir parametros nuevos o
refinar parametros existentes, pero no para modificar el modelo a ciegas. El
ciclo correcto es:

```text
observaciones + contexto GIS/DEM + meteorologia historica
  -> hipotesis o candidato de parametro
  -> test reproducible en laboratorio
  -> revision humana de si encaja con datos y literatura disponible
  -> promocion manual al modelo si aporta valor
```

Ejemplos de candidatos aceptables como hipotesis: una ventana de lluvia que
aparece repetidamente antes de positivos, un rango altitudinal local mas
estrecho que el descrito en la ficha, o una asociacion fuerte con un tipo de
bosque en las observaciones propias. Hasta que se validen, esos candidatos deben
vivir en outputs experimentales y reportes, no en el scoring productivo.

Esta decision no elimina la UI de `GIS mappings` ni los catalogos existentes; la
reorienta hacia mappings mas mantenibles. `geology_50000.Codi` debe priorizar
salidas de tendencia edafica amplia mediante reglas declarativas, y conservar la
litologia fina como trazabilidad, auditoria o futuro enriquecimiento cuando la
evidencia lo justifique. Las categorias finas pueden permanecer en el dataset,
pero no deben ser obligatorias ni dominar el scoring inicial.

El camino anterior, basado en intentar completar muchos parametros finos por
especie desde el inicio, queda aparcado como fase futura de enriquecimiento
avanzado. No es criterio de exito de la v0 rellenar todo `mushroom_profiles.json`
ni convertir cada detalle GIS en un parametro predictivo. Para v0, el dato
minimo util es una ficha normalizada que permita comparar un punto del mapa
contra habitat, vegetacion/host, suelo amplio, altitud, temporada y meteorologia
reconstruida. Si algun dia las observaciones locales permiten justificar mas
detalle, ese detalle debe entrar como candidato probado, no como obligacion del
schema inicial.

Fuera de alcance de v0:

- completar todos los pesos y subparametros actuales por especie;
- fijar ventanas de lluvia, temperatura, humedad o viento por intuicion;
- usar litologias exactas como `lith_slate` o `lith_basaltic` para scoring salvo
  evidencia documental o local verificable;
- promocionar automaticamente hipotesis inferidas desde pocas observaciones;
- tratar el catalogo fino como una lista de campos obligatorios.

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

## Fase 0: mini-fase GIS acotada

Objetivo:

Antes de implementar el `observation_context_builder`, identificar que capas
oficiales son realmente utilizables para Catalunya y que equivalentes
peninsulares quedan como fallback.

Alcance:

- usar `docs/mushrooms/gis-layer-inventory-es.md` como inventario vivo;
- construir la v0 GIS solo para Catalunya;
- mantener la Peninsula Iberica espanola como fase 2 del predictor siguiendo la
  misma metodologia documental y tecnica;
- en fase 2 solo deberian faltar fuentes equivalentes no catalanas para DEM,
  coberturas, suelos y litologia; la reconstruccion meteorologica se basara en
  el mismo `observation_context_builder` y los historicos Rainmapper ya
  disponibles;
- dejar fuera de alcance Canarias, Baleares, Ceuta y Melilla;
- no versionar capas grandes; las copias locales bajo `mushroom-GIS/` deben
  seguir ignoradas por Git y fuera de la imagen HA;
- no crear mappings nuevos por intuicion sin inspeccionar atributos reales.

Duracion maxima:

- 2 dias de trabajo efectivo.

Salida esperada:

- lista corta de capas v0;
- decision raster/vector por capa;
- fuente, licencia, formato, CRS y resolucion documentados;
- primeros codigos/campos externos candidatos para `mushroom_gis_mappings.json`;
- gaps conocidos antes de disenar el builder.

Capas Catalunya v0 seleccionadas:

- MVC50 para vegetacion, hosts, habitat y substrato preferente.
- ICGC Geologia territorial 1:50.000
  `geologia-territorial-50000-geologic-v3r0-202412` para litologia/geologia.
- ICGC Model d'elevacions del terreny topografic Catalunya 5 m
  `model-elevacions-terreny-topografic-catalunya-5m-2009-2018` para altitud,
  pendiente y orientacion.

Capas Catalunya aparcadas:

- ICGC/MCSC `cobertes-sol-v1r0-2024`, candidata futura para cobertura
  estructural general. No se usara para hosts y no bloquea la v0.
- ICGC Mapa de suelos 1:25.000 `sols-25000-v1r1-202512`, descartada para v0:
  cobertura parcial, poca utilidad predictiva frente a `MVC50.LLVA_Subst` y
  mapping poco directo contra los IDs internos de suelo de especies.

Plan inmediato tras cerrar la mini-fase GIS:

1. Documentar el estado final de capas v0 y dejarlo referenciado en
   continuidad.
2. Probar consultas por coordenada sobre 2-3 observaciones reales o
   anonimizadas, sin publicar coordenadas.
3. Disenar la salida experimental `observations_gis_features` con campos,
   fuentes, codigos crudos y gaps.
4. Implementar el `observation_context_builder` meteorologico local desde
   `docker-data/Data/`.
5. Integrar DEM/GIS en el laboratorio, ya sea como fase del mismo builder o como
   builder GIS separado.
6. Crear mappings solo desde codigos reales observados y mantener sin mapping
   cualquier clase no revisada.

Auditoria batch reutilizable:

```bash
./mushroom_gis_mappings_rebuild.sh
```

Este comando recorre los valores unicos de los campos GIS mapeables configurados
en `rainmapper_core.mushroom_gis_lab`, no usa coordenadas de observaciones y
escribe el payload local que consume `/mushrooms/gis-mappings`:

```text
docker-data/mushroom-lab/working/features/gis_observation_reconstruction.json
```

Por defecto lee `docker-data/mushroom-data/` si existe para respetar la copia
mutable del laboratorio local; si no, usa `mushroom-data/`. El script no escribe
`mushroom_gis_mappings.json`: solo genera candidatos de revision. Las
sugerencias derivadas de texto litologico oficial son preselecciones
revisables, no mappings `accepted` computables. La salida de consola y el JSON
incluyen metricas por capa/campo (`unique`, `existing`, `candidates`,
`suggested`) y tiempos de ejecucion por campo mas tiempo total.

La ruta de salida no requiere configuracion manual en el lanzamiento normal. El
core usa, por orden:

1. `RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH`, si se quiere forzar un JSON
   concreto.
2. `RAINMAPPER_MUSHROOM_LAB_DIR`, si se quiere forzar el directorio base del
   laboratorio.
3. `/share/rainmapper/mushroom-lab/` dentro de Home Assistant.
4. `docker-data/mushroom-lab/` en el laboratorio local del repo.
5. `tmp/mushroom-lab/` solo como fallback local si no existe `docker-data/`.

El payload batch es una cache reconstruible, no fuente de verdad. La fuente de
verdad son las capas GIS, `mushroom_reference_catalogs.json`,
`mushroom_gis_mappings.json` y las reglas declarativas. Para preparar promocion
futura a HA sin rehacer el motor, el core acepta:

```bash
RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH=/share/rainmapper/mushroom-lab/working/features/gis_observation_reconstruction.json
```

Tambien acepta un directorio base persistente, mas comodo para HA:

```bash
RAINMAPPER_MUSHROOM_LAB_DIR=/share/rainmapper/mushroom-lab
```

o el parametro puntual del wrapper:

```bash
./mushroom_gis_mappings_rebuild.sh --output /share/rainmapper/mushroom-lab/working/features/gis_observation_reconstruction.json
```

En HA real, el default ya apunta a `/share/rainmapper/mushroom-lab/` si existe
`/share/rainmapper`; no hace falta pasar la variable en el arranque normal.

Si se quiere auditar contra los defaults versionados en vez de la copia mutable
local:

```bash
./mushroom_gis_mappings_rebuild.sh --mushroom-data-root mushroom-data
```

### Promocion controlada de reglas batch a la copia mutable

Mientras las reglas batch se estan probando, la copia versionada:

```text
mushroom-data/mushroom_reference_catalogs.json
mushroom-data/mushroom_gis_mappings.json
```

puede ir por delante de la copia mutable local:

```text
docker-data/mushroom-data/mushroom_reference_catalogs.json
docker-data/mushroom-data/mushroom_gis_mappings.json
```

La copia mutable local representa el futuro `/share/rainmapper/mushroom-data/`
de HA. Cuando la UI `/mushrooms/gis-mappings` muestre que las reglas nuevas son
razonables, una sesion posterior puede promover esas reglas a la copia mutable.

Reglas de promocion:

1. No promocionar observaciones, historicos, perfiles ni backups. Esta promocion
   se limita a `mushroom_reference_catalogs.json` y
   `mushroom_gis_mappings.json`.
2. Hacer backup previo de los dos JSON destino bajo
   `docker-data/mushroom-data/backups/`, con timestamp y sufijo claro de
   promocion GIS.
3. Comparar versionado contra mutable antes de escribir. No asumir que
   `docker-data/mushroom-data/` es identico a `mushroom-data/`.
4. Fusionar los cambios nuevos del laboratorio GIS:
   - nuevos IDs de `soil_types` y `lithology_types`;
   - aliases y reglas nuevas de `lithology_mappings` y
     `vegetation_mappings`;
   - seccion `batch_suggestion_rules`;
   - cualquier ajuste relacionado requerido para que el validador cruce IDs.
5. Preservar cambios vivos no relacionados si existen. Esto significa no perder
   textos, labels o descripciones que esten en la copia mutable y no formen
   parte del cambio GIS que se esta promoviendo. Si una sesion Codex anterior
   escribio labels adicionales en `docker-data/mushroom-data/`, revisarlos y
   mantenerlos salvo que sean claramente obsoletos.
6. Validar despues de escribir:

```bash
python3 scripts/validate-mushroom-data.py
```

7. Reconstruir el payload batch usando ya la copia mutable normal:

```bash
./mushroom_gis_mappings_rebuild.sh
```

8. Abrir `/mushrooms/gis-mappings` en el Docker local y confirmar que los
   candidatos y sugerencias coinciden con lo revisado.

Solo despues de estar satisfechos en Docker local se debe repetir la promocion
equivalente en HA real sobre:

```text
/share/rainmapper/mushroom-data/mushroom_reference_catalogs.json
/share/rainmapper/mushroom-data/mushroom_gis_mappings.json
```

En HA real aplicar el mismo criterio defensivo: backup previo, comparacion,
fusion controlada, validacion y reconstruccion del payload bajo
`/share/rainmapper/mushroom-lab/`. No copiar a ciegas desde el repo si la copia
viva de HA contiene cambios posteriores hechos desde la UI.

Decision de suelo v0:

- No usar capa edafologica externa en v0. El sustrato predictivo sale de
  `MVC50.LLVA_Subst`; el suelo real detallado queda fuera hasta que exista una
  fuente continua y claramente mapeable.

## Fase 1: `observation_context_builder` meteorologico local

Objetivo:

Reconstruir condiciones meteorologicas previas por observacion desde los incrementales de Rainmapper, dejando preparada la estructura para DEM/GIS.

Alcance inicial:

- leer observaciones activas y utiles para analisis;
- normalizar fecha, especie, abundancia real (`flush_abundance`), resultado derivado para analisis, coordenadas, altitud, validacion, calidad de fuente y uso de calibracion;
- conservar hosts observados manualmente (`site_context.observed_host_ids`) como evidencia de campo, separada de cualquier inferencia GIS futura;
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
analysis_result
flush_abundance
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
observed_host_ids
```

`analysis_result` no existe en el JSON real de observaciones. Es un campo derivado del extractor:

```text
analysis_result = absent   si flush_abundance == absent
analysis_result = present  si flush_abundance != absent
```

El extractor debe conservar siempre el valor original `flush_abundance` para no perder la intensidad observada de la florada. Los nombres exactos pueden ajustarse al implementar, pero la salida debe conservar trazabilidad suficiente para revisar cada fila.

`observed_host_ids` procede de la observacion base y debe tratarse como evidencia manual de campo. No debe confundirse con hosts o tipos de bosque inferidos por GIS, que se generaran mas adelante en `observations_gis_features`.

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
- El contenedor `rainmapper-ha-ui` queda parado tras ejecutar `./mushroom_lab_stop.sh`; auditoria Docker del 2026-07-02 no muestra servicios activos y `docker-data/` queda preservado.
- La mini-fase GIS acotada ya produjo UI `GIS mappings`, rebuild batch reutilizable y reglas declarativas de tendencia edafica amplia. El siguiente trabajo tecnico sera definir el schema minimo del seed literario v0 y despues implementar la Fase 1 como `observation_context_builder` local experimental.
- Este documento sera la guia que se ira adaptando segun decisiones sobre metodo meteorologico, DEM/GIS y generacion de candidatos.
