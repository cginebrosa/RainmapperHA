# Plan del laboratorio de reconstruccion de parametros de setas

Este documento es la guia viva para disenar y ejecutar el laboratorio local que reconstruira condiciones observadas de floradas de setas y, mas adelante, propondra parametros candidatos por especie.

No es todavia una especificacion cerrada del predictor productivo. Su funcion es ordenar el trabajo incremental para que cada decision quede trazada, revisable y separada de los datos productivos de Home Assistant.

Nota de vigencia 2026-07-05: las secciones antiguas que mencionan `docker-data/mushroom-lab/working/` o `/share/rainmapper/mushroom-lab/` describen fases historicas del laboratorio. El contrato operativo actual para datos de setas, artefactos v0 reconstruibles y estado del modelo es `mushroom-data/`: en local `docker-data/mushroom-data/`, en HA `/share/rainmapper/mushroom-data/`. `tmp/mushroom-lab/` queda solo para pruebas locales explicitas, QGIS o scripts exploratorios.

Documentos relacionados:

- `docs/mushrooms/mushroom-local-observation-lab-es.md`
- `docs/mushrooms/mushroom-predictor-design-es.md`
- `docs/mushrooms/mushroom-ml-training-plan-es.md`
- `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`
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
meteorologicos por intuicion. El output inicial recomendado no es un modelo
paralelo definitivo, sino una proyeccion v0 operativa de
`mushroom_profiles.json`: campos activos minimos de suelo amplio, vegetacion,
habitat, altitud/temporada aproximadas y estado de revision/calibracion. El
contrato esta documentado en
`docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md` y en
`rainmapper_core/mushroom_profile_v0.py`.

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
- descartar la UI rica actual de perfiles; debe quedar aparcada como vista
  avanzada/futura mientras la UI v0 muestra solo los campos activos.

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

Salida aprendida v0 ya implementada:

```text
docker-data/mushroom-lab/working/models/mushroom_model_v0.json
docker-data/mushroom-lab/output/reports/mushroom_model_v0.md
```

Se genera con:

```bash
./mushroom_observation_context_rebuild.sh
./mushroom_observation_features_v0_build.sh
./mushroom_learned_model_v0_build.sh
```

o desde la WebUI local en `Evidencia > Modelo aprendido`. La UI debe ofrecer
rebuild de la especie seleccionada y rebuild global cuando tenga sentido. El
rebuild encadena la reconstruccion de contexto, el joiner de features v0 y el
builder del modelo aprendido. No modifica `mushroom_profiles.json`.

Diferenciar wrappers:

- `mushroom_gis_mappings_rebuild.sh` reconstruye la cola batch de candidatos de
  mappings GIS para capas/fuentes; no reconstruye observaciones.
- `mushroom_observation_context_rebuild.sh` reconstruye contexto por
  observacion usando observaciones locales, GIS/DEM y meteorologia disponible.
- `mushroom_observation_features_v0_build.sh` normaliza esas reconstrucciones
  como features v0 por observacion.
- `mushroom_learned_model_v0_build.sh` resume esas features por especie.

Semantica actual del modelo aprendido:

- es descriptivo y auditable, no predictivo;
- resume observaciones validas/incluidas por especie;
- separa positivos y negativos;
- para variables categoricas muestra soporte de hosts, bosques, suelos y
  habitat en positivos/negativos;
- para variables numericas muestra rango minimo/maximo y media en positivos y
  negativos;
- conserva gaps de meteorologia/GIS/feature como informacion de calidad;
- no fija umbrales, pesos ni ventanas por especie;
- no aplica decisiones ni escribe perfiles.

La pantalla meteorologica de evidencia debe ser compacta y comparable. El
estado actual trabaja con lluvia 7/14/21/30/60/90 dias, temperatura 7/14/21/30,
humedad 7/14/21/30 y altitud cuando existe en GIS/DEM. Los outliers de
estaciones deben tratarse como problema de calidad de datos. Como trabajo futuro
se propone calcular una segunda evidencia meteorologica mediante IDW en radios
de 10 km y 15 km para comparar contra la estacion mas cercana, no para
sustituirla automaticamente.

Wunderground aporta velocidad de viento historica con el scrape mensual actual,
pero no direccion. Queda como TODO reconstruir 2-3 años si interesa y estudiar
una direccion media equivalente a Meteocat. No usar viento como señal productiva
de v0 hasta tener suficiente calidad y evidencia.

Uso previsto inmediato:

El modelo aprendido aislado sirve para auditar, pero el mantenimiento real debe
mostrar esta evidencia junto al parametro afectado. El siguiente cambio de UI
debe proyectar los calculos del modelo aprendido en:

- `Parametros`, al lado de los campos v0 seleccionados/no seleccionados;
- `Especies > General`, como resumen de aprendizaje, gaps y contradicciones;
- `Especies > Ecologia`, junto a hosts, bosques, suelos y habitat;
- `Especies > Fenologia y Topografia`, junto a meses, altitud y orientaciones
  cuando haya evidencia reconstruida.

La pantalla `Evidencia > Modelo aprendido` queda como detalle tecnico y
explicativo. La aplicacion de cambios al perfil debe seguir siendo manual,
visible y reversible, preferentemente mediante candidatos o diffs por campo
antes de escribir `mushroom_profiles.json`.

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

Por defecto usa el resolver comun `rainmapper_core/mushroom_paths.py`: en HA
lee la copia persistente `/share/rainmapper/mushroom-data/`; en Docker local
`docker-data/` representa ese mismo `/share/rainmapper`; si no existe copia
persistente, usa los defaults versionados de `mushroom-data/` o
`/app/mushroom-data/`. El script no escribe `mushroom_gis_mappings.json`: solo
genera candidatos de revision. Las
sugerencias derivadas de texto litologico oficial son preselecciones
revisables, no mappings `accepted` computables. La salida de consola y el JSON
incluyen metricas por capa/campo (`unique`, `existing`, `candidates`,
`suggested`) y tiempos de ejecucion por campo mas tiempo total.

La ruta de salida no requiere configuracion manual en el lanzamiento normal. El
core usa el resolver comun `rainmapper_core/mushroom_paths.py`, por orden:

1. `RAINMAPPER_MUSHROOM_GIS_RECONSTRUCTION_PATH`, si se quiere forzar un JSON
   concreto.
2. `RAINMAPPER_MUSHROOM_LAB_DIR`, si se quiere forzar el directorio base del
   laboratorio.
3. `RAINMAPPER_SHARE_ROOT/mushroom-lab/`, si se quiere forzar la raiz
   persistente completa.
4. `/share/rainmapper/mushroom-lab/` dentro de Home Assistant, si existe.
5. `docker-data/mushroom-lab/` en el laboratorio local del repo, como copia de
   `/share/rainmapper`.
6. `tmp/rainmapper-share/mushroom-lab/` solo como ultimo fallback local.

El payload batch es una cache reconstruible, no fuente de verdad. La fuente de
verdad son las capas GIS, `mushroom_reference_catalogs.json`,
`mushroom_gis_mappings.json` y las reglas declarativas. Para preparar promocion
futura a HA sin rehacer el motor, el core acepta:

Desde la proyeccion v0 GIS, no hay que lanzar un segundo paso para obtener la
salida operativa por observacion. Las reconstrucciones por observacion que se
ejecutan desde la UI de Observaciones incluyen `gis_context_v0` dentro de cada
resultado, derivado del payload rico y sin volver a leer capas. El wrapper batch
`./mushroom_gis_mappings_rebuild.sh` no reconstruye observaciones ni genera
contextos v0 por punto: sigue siendo solo la herramienta para reconstruir la
cola de candidatos de mappings de capas completas.

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

## Diseno del cache territorial GIS v0

Objetivo:

Construir, en una fase posterior al laboratorio puntual de observaciones, una
cache estatica para Catalunya que permita consultar rapidamente la aptitud
ecologica base de cualquier celda del mapa. Esta cache no sustituye a
`mushroom_gis_mappings.json`: lo consume. Tampoco sustituye a la meteorologia:
solo representa el contexto estatico del territorio.

Flujo conceptual:

```text
capas GIS oficiales + DEM
  -> valores crudos por celda/poligono
  -> mushroom_gis_mappings.json
  -> gis_context_v0 territorial
  -> predictor v0 + meteorologia reciente
```

La UI de Observaciones queda como laboratorio de control: permite comprobar en
puntos reales si las capas y mappings producen un `gis_context_v0` coherente.
El producto final no debe depender de recorrer solo observaciones.

### Responsabilidades separadas

- `mushroom_gis_mappings_rebuild.sh`: reconstruye candidatos de mappings desde
  valores unicos de capas completas. No usa coordenadas ni DEM por punto.
- Reconstruccion GIS desde Observaciones: muestrea puntos reales y adjunta
  `gis_context_v0` por observacion para validacion humana.
- Cache territorial GIS v0 futuro: genera una estructura consultable para todo
  Catalunya, derivada de capas GIS y mappings revisados.

No mezclar estos flujos en un solo script. Si se implementa la cache territorial,
debe tener wrapper y salidas propias.

### Regla de reconstruccion MVC50 para hosts/bosques

La reconstruccion territorial no debe limitarse a mirar un unico campo de MVC50.
En las observaciones locales ya aparecio el caso de puntos completos y sin gaps
donde `LLVA_niv2t`, `LLFISCAT_t`, `LLVA_txt` y otros campos MVC50 juntos
contenian la senal ecologica util para v0, aunque un campo aislado no bastara.
Ejemplos revisados:

- `LLVA_niv2t = Carrascars` y textos de carrascar/roureda en otros campos:
  emitir senales amplias de encinar/carrascar mediterraneo.
- `LLFISCAT_t = Carrasca (Quercus rotundifolia)`: emitir host/bosque de
  carrasca/encinar usando el grupo v0 existente de `Quercus ilex`.
- `LLVA_niv2t = Rouredes i pinedes submediterrànies de pi roig i pinassa`:
  emitir host/bosque mixto de robles y pinos declarados por la propia clase.
- `LLVA_niv2t = Brolles de romaní i matollars mediterranis afins`: emitir
  habitat de matorral mediterraneo/calcicola, pero no inventar host ni bosque
  si MVC50 no declara arbol dominante.

Regla operativa: estas deducciones se convierten en mappings declarativos por
`source_id` + `field` + `raw_value` dentro de `mushroom_gis_mappings.json`.
No se crean reglas dependientes de la especie observada ni del resultado de una
florada concreta. Si una clase territorial solo permite habitat, la salida v0
queda sin host/bosque y se considera informacion incompleta pero valida.

### Contrato minimo por celda

Cada unidad territorial debe poder devolver, como minimo:

```json
{
  "host_ids": [],
  "forest_type_ids": [],
  "soil_tendency_ids": [],
  "habitat_feature_ids": [],
  "altitude_m": null,
  "altitude_band_m": null,
  "evidence": {
    "source_layers": [],
    "mapping_gaps": [],
    "raw_refs": []
  }
}
```

Campos fuera del contrato v0:

- `mapped_lithology_ids` como input de scoring principal;
- textos crudos completos de capas dentro del producto rapido;
- pesos por especie;
- meteorologia historica o reciente;
- candidatos de calibracion.

La litologia fina puede mantenerse como referencia en `evidence.raw_refs` o en
un fichero auxiliar trazable, pero no debe ser la senal principal del predictor
v0.

### Unidad espacial recomendada

No empezar rasterizando Catalunya a maxima resolucion ni elegir una malla
arbitraria como si todas las fuentes tuvieran la misma precision. La fuente que
manda la semantica v0 de vegetacion/host/habitat es MVC50, y MVC50 es vectorial
a escala 1:50.000, no un raster con celda fija. Por tanto, la unidad espacial
debe respetar la escala efectiva de MVC50.

Regla recomendada:

- usar los poligonos/clases de MVC50 como unidad semantica primaria para
  vegetacion, hosts, habitat y substrato;
- cruzar o muestrear geologia y DEM sobre esa unidad o sobre una malla derivada;
- si se usa malla regular por conveniencia del mapa, no hacerla mas fina que la
  precision util de MVC50;
- tratar la resolucion del DEM de 5 m solo como fuente para resumir altitud, no
  como resolucion del predictor;
- documentar en el manifest si la cache se genero por poligono MVC50, por malla
  regular o por una combinacion de ambos.

Motivo:

- MVC50 no justifica una precision operativa de pocos metros para prediccion
  micologica v0;
- una malla mas fina que la fuente dominante solo crea falsa precision;
- la meteorologia Rainmapper se apoya en estaciones y campos interpolados, no en
  microclima de 5 m;
- una malla puede facilitar cachear y consultar desde un mapa diario, pero debe
  ser una salida operativa derivada, no la verdad semantica principal;
- facilita versionar metadatos de generacion sin guardar capas GIS pesadas.

Si se usa celda, debe guardar su centroide o clave espacial, no coordenadas de
observaciones. Las coordenadas reales de observaciones siguen siendo dato local
del laboratorio.

### Formato de cache

Formato inicial recomendado:

```text
docker-data/mushroom-lab/working/features/catalunya_static_context_v0/
```

Con:

```text
manifest.json
cells.geojsonl     # piloto/debug humano, no producto final grande
cells.parquet      # candidato preferido si el toolchain local lo permite
```

Si Parquet complica dependencias, usar GeoJSONL o CSV comprimido para el piloto
y aplazar optimizacion. No meter esta cache en la imagen HA ni versionarla en
Git. Es reconstruible desde capas GIS locales, DEM, catalogos y mappings.

`manifest.json` debe incluir:

- fecha de generacion;
- version del schema;
- CRS de trabajo;
- unidad espacial (`mvc50_polygon`, `regular_grid` o `hybrid`);
- escala/fuente dominante;
- resolucion de celda si aplica;
- extent usado;
- paths/fingerprints de capas GIS locales;
- hash o timestamp de `mushroom_gis_mappings.json`;
- hash o timestamp de `mushroom_reference_catalogs.json`;
- conteo de celdas;
- conteo de gaps por fuente/campo.

### Piloto recomendado

Antes de Catalunya completa:

1. Elegir una zona pequena con observaciones reales y variedad de habitats.
2. Generar un piloto basado en MVC50:
   - opcion A: poligonos MVC50 recortados a la zona piloto;
   - opcion B: malla regular derivada solo si el visor/predictor la necesita.
3. Para cada unidad piloto:
   - leer clase MVC50 principal;
   - cruzar o muestrear geologia;
   - resumir DEM;
   - aplicar mappings aceptados;
   - construir `gis_context_v0`.
4. Comparar visualmente varias celdas con Observaciones y QGIS.
5. Medir tiempo, tamano de salida y gaps.
6. Solo entonces decidir resolucion de Catalunya completa.

### Regeneracion

La cache territorial debe considerarse invalida si cambia:

- MVC50 o su version local;
- geologia territorial ICGC;
- DEM o derivados topograficos;
- `mushroom_gis_mappings.json`;
- `mushroom_reference_catalogs.json`;
- resolucion/extent de la malla;
- schema `gis_context_v0`.

No hace falta regenerarla por cambios meteorologicos diarios. El predictor
diario debe combinar:

```text
cache estatica GIS v0 + meteorologia reciente + perfil de especie v0
```

### Fuera de alcance inmediato

- cache territorial para Peninsula Iberica completa;
- microtopografia a 5 m;
- slope/aspect como scoring numerico si no hay soporte posterior;
- uso de MCSC/CatLC hasta que MVC50 demuestre quedarse corto;
- publicacion en HA real;
- generacion de mapas de probabilidad diarios.

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
prediction_target
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

`analysis_result` se conserva por compatibilidad y para distinguir presencia
biologica de ausencia, pero no es el objetivo binario operativo del modelo V0.
El objetivo se materializa como `prediction_target` usando la politica
versionada `catalog_prediction_favorable_v1`. La fuente de la regla no esta
codificada en Python: es el entero `prediction_favorable` (`0` o `1`) de cada
entrada de `catalogs.observation_flush_abundance`:

```text
prediction_target = favorable    si flush_abundance es normal, abundant,
                                  very_abundant o exceptional
prediction_target = unfavorable  si flush_abundance es scarce, very_scarce
                                  o absent
prediction_target = unknown      si falta el valor o no esta reconocido
```

La correspondencia anterior es la configuracion del catalogo actual, no una
lista fija del extractor. La politica materializada incluye el mapping exacto,
la ruta del catalogo y una huella SHA-256 del mapping. Si falta
`prediction_favorable` o no es un entero 0/1, la reconstruccion se detiene con
error para evitar entrenar silenciosamente con una clasificacion ambigua.

El extractor debe conservar siempre el valor original `flush_abundance` para
no perder la intensidad observada de la florada. El JSON original de
observaciones no guarda `prediction_target` y no necesita migracion. El valor
derivado se guarda por fila en
`mushroom_observations_weather_features.{json,csv}` y
`mushroom_observation_features_v0.{json,csv}`. El modelo aprendido guarda
ademas la definicion y version de la politica para que cada reconstruccion sea
auditable y reproducible.

El catalogo persistente de Home Assistant no se migra automaticamente. El
orden de despliegue es: actualizar el add-on, importar manualmente el catalogo
completo actualizado y, solo despues, reconstruir todas las especies. No se
modifica ningun JSON de observaciones.

`observed_host_ids` procede de la observacion base y debe tratarse como evidencia manual de campo. No debe confundirse con hosts o tipos de bosque inferidos por GIS, que se generaran mas adelante en `observations_gis_features`.

## Metodo meteorologico inicial

Decision inicial prudente:

- usar estacion cercana como primer POC;
- registrar distancia y fuente;
- evitar interpolacion hasta comprobar calidad de datos y cobertura;
- no mezclar varias fuentes sin explicar la decision.

Implementacion local inicial 2026-07-02:

- modulo: `rainmapper_core/mushroom_observation_context.py`;
- wrapper: `./mushroom_observation_context_rebuild.sh`;
- script: `scripts/reconstruct-mushroom-observation-context.py`;
- entradas por defecto:
  - `docker-data/mushroom-data/mushroom_observations.json`;
  - `docker-data/Data/{Aemet,Meteocat,Meteoclimatic,Wunderground}_incremental.csv`;
- salidas por defecto:
  - `docker-data/mushroom-lab/working/features/observations_weather_features.json`;
  - `docker-data/mushroom-lab/working/features/observations_weather_features.csv`;
  - `docker-data/mushroom-lab/output/reports/observations_weather_features.md`;
- metodo: `nearest_station_single_source_daily`;
- seleccion: estacion diaria mas cercana con al menos un dato dentro de la
  ventana previa de 90 dias;
- lluvia: acumulados de 1/7/14/21/30/60/90 dias, incluyendo la fecha de
  observacion como extremo final;
- temperatura, humedad y viento: resumen de 7 dias, indicado por
  `weather_summary_window_days`;
- cobertura incompleta: se calcula con los dias disponibles y se anade un gap
  del tipo `rain_30d_coverage_17/30`;
- no se define distancia maxima aceptable todavia; por tanto no se descartan
  estaciones lejanas por umbral inventado;
- no se mezclan fuentes: si la estacion elegida no tiene viento, el viento queda
  como gap (`wind_no_data_7d`) aunque otra fuente cercana pueda tenerlo.

Resultado de la primera reconstruccion local sobre 45 observaciones: 45 filas
con estacion meteorologica asignada, 43 con algun gap, principalmente por viento
ausente en la estacion cercana elegida o cobertura parcial en ventanas largas.
Este resultado es util para inspeccion y candidatos, pero no debe interpretarse
todavia como calibracion meteorologica productiva.

Nota sobre viento:

Wunderground ya recupera viento en ejecuciones actuales, pero los historicos
locales disponibles para algunas observaciones antiguas pueden no conservarlo.
Se deja como TODO una reconstruccion historica controlada de Wunderground de los
ultimos 2-3 anos, con backups y `check-history`, antes de usar el viento como
evidencia fuerte. La direccion media requeriria calculo circular, similar al
criterio usado con Meteocat/Tomap, porque el scraping historico mensual diario
no entrega directamente una direccion media fiable en el formato actual. Para
la v0 micologica inicial, el viento queda como campo reconstruible/gap trazable,
pero no debe entrar en scoring ni bloquear candidatos salvo decision posterior.

## Fase 1b: features v0 unificadas por observacion

Implementacion local inicial 2026-07-02:

- modulo: `rainmapper_core/mushroom_observation_features.py`;
- wrapper: `./mushroom_observation_features_v0_build.sh`;
- script: `scripts/build-mushroom-observation-features-v0.py`;
- entradas por defecto:
  - `docker-data/mushroom-lab/working/features/observations_weather_features.json`;
  - `docker-data/mushroom-lab/working/features/gis_observation_reconstruction.json`;
- salidas por defecto:
  - `docker-data/mushroom-lab/working/features/observation_features_v0.json`;
  - `docker-data/mushroom-lab/working/features/observation_features_v0.csv`;
  - `docker-data/mushroom-lab/output/reports/observation_features_v0.md`.

Contrato:

El builder une meteorologia y GIS por `observation_id` y genera una tabla plana
de revision con:

- identidad de observacion, especie, fecha y resultado (`present`/`absent`);
- lluvia acumulada 1/7/14/21/30/60/90 dias;
- temperatura/humedad/viento disponibles;
- `host_ids`, `forest_type_ids`, `soil_tendency_ids`, `habitat_feature_ids`;
- altitud GIS/DEM;
- `weather_gaps`, `gis_gaps` y `feature_gaps`.

No genera candidatos de parametros ni modifica perfiles. Sirve como contrato
intermedio reutilizable: cuando se reconstruya Wunderground historico o se cree
la cache territorial GIS de Catalunya, el siguiente paso debe seguir escribiendo
o consumiendo este tipo de features por observacion.

Resultado de la primera union local:

- 45 observaciones;
- 45 con meteorologia;
- 45 con GIS;
- 43 con gaps meteorologicos;
- 0 con gaps GIS/feature.

Lectura operativa: para estas observaciones, GIS v0 ya no es el bloqueo
principal; la calidad meteorologica historica, especialmente viento, es el punto
que necesita decision antes de usar candidatos meteorologicos.

Decisiones pendientes antes o durante la implementacion:

- decidir si el siguiente POC mantiene estacion unica o permite fuente distinta
  para lluvia/temperatura/humedad/viento con trazabilidad separada;
- definir distancia maxima aceptable antes de marcar gap;
- decidir si se calcula `days_since_significant_rain` en la primera version o se deja para una segunda iteracion;
- si se calcula, definir el umbral como global exploratorio y documentarlo como no productivo;
- decidir si se incluyen observaciones `draft` en modo diagnostico o solo observaciones validadas/aceptadas.

## Tratamiento de observaciones

La primera version debe separar claramente:

- observaciones favorables para una salida de recoleccion;
- observaciones desfavorables, incluidas floradas escasas y ausencias;
- observaciones dudosas;
- observaciones archivadas;
- observaciones excluidas de calibracion;
- observaciones validas pero con gaps meteorologicos.

Configuracion actual del catalogo para el objetivo binario V0:

- `normal` o superior se considera `favorable`;
- `scarce`, `very_scarce` y `absent` se consideran `unfavorable`;
- la florada original se conserva siempre y permite reconstruir el objetivo si
  el campo `prediction_favorable` del catalogo cambia en el futuro.

Regla de inclusion recomendada:

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

Revision de evidencia local v0:

- La UI de especies debe exponer una pestanya `Evidencia` separada de
  `Observaciones`, `Parametros` y `Calibracion`.
- La pestanya `Evidencia` puede tener subtabs internas para no mezclar tipos
  de decision. En el estado actual, `GIS` contiene decisiones manuales y
  `Meteorologia` contiene lectura de features observadas.
- La pantalla compara lo declarado en el perfil v0 contra lo reconstruido desde
  observaciones (`gis_context_v0`) para Hosts, Bosques, Suelos y Habitat.
- Debe mostrar los dos sentidos de la discrepancia:
  - observado localmente pero no declarado en el perfil;
  - declarado en el perfil pero no observado localmente.
- Las decisiones humanas (`promover`, `ignorar`, `mantener`, `marcar dudoso`)
  se guardan aparte y son reversibles. No deben modificar automaticamente
  `mushroom_profiles.json`.
- El fichero de decisiones locales es estado de revision, no fuente biologica
  canonica de especie. La promocion real al perfil debe ser un paso posterior,
  explicito y validado.
- La lectura meteorologica consume `observation_features_v0.json` y solo resume
  rangos/gaps por especie. No debe inferir umbrales ni escribir parametros.

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
- La mini-fase GIS acotada ya produjo UI `GIS mappings`, rebuild batch reutilizable, reglas declarativas de tendencia edafica amplia y proyeccion `gis_context_v0` sobre reconstrucciones por observacion. El contrato operativo v0 de perfiles queda iniciado como proyeccion de `mushroom_profiles.json`, no como descarte del modelo ni de la UI rica. El siguiente trabajo tecnico sera implementar la Fase 1 como `observation_context_builder` local experimental.
- Este documento sera la guia que se ira adaptando segun decisiones sobre metodo meteorologico, DEM/GIS y generacion de candidatos.
