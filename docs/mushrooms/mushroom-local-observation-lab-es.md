# Laboratorio local de observaciones de setas

Este documento define el flujo local para construir una primera base experimental de observaciones reales de setas a partir de fotos geolocalizadas, observaciones negativas y datos historicos de Rainmapper.

El objetivo no es modificar Home Assistant ni los JSON productivos. El objetivo es crear una BBDD experimental local para inferir condiciones observadas de fructificacion y, mas adelante, proponer parametros candidatos por especie.

Este laboratorio es la fase crucial que conecta todo el trabajo previo:

- Rainmapper ya conserva historicos meteorologicos.
- La UI de especies ya mantiene perfiles, parametros, catalogos y observaciones.
- Las observaciones reales del usuario aportan evidencia local.
- Las capas DEM/GIS aportan contexto topografico, habitat, vegetacion, litologia y suelo.

La meta es dejar de inventar parametros y empezar a construirlos desde evidencia local reproducible.

Documento relacionado de UI:

- `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`

Documento de plan vivo para seguir/adaptar el diseno del extractor y la reconstruccion de parametros:

- `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`

## Regla critica

Los datos de este laboratorio son sensibles:

- fotos;
- coordenadas de recolectas;
- observaciones positivas y negativas;
- historicos meteorologicos copiados desde HA;
- capas GIS locales.

Por tanto, todo dato real debe vivir en rutas ignoradas por Git:

- `docker-data/`, para la copia local mutable equivalente a `/share/rainmapper` y para usar la WebUI local.
- `tmp/mushroom-lab/`, para fotos, capas GIS, ficheros intermedios, reportes y experimentos.

No subir observaciones reales, fotos, coordenadas, historicos meteorologicos ni capas GIS al repositorio.

## Estructura local creada

```text
tmp/mushroom-lab/
  input/
    ha-data/
      Data/
      Tomap/
      mushroom-data/
    photos/
      positive/
      negative/
    manual/
    gis/
      icgc/
      ign-cnig/
  working/
    observations/
    features/
  output/
    parameter-candidates/
    reports/
```

## WebUI local para introducir observaciones

Para introducir observaciones manualmente, no hace falta editar CSV si se usa la UI real de Rainmapper.

El servicio local `rainmapper-ha-ui` arranca la imagen de Home Assistant en modo `serve`, pero montando `docker-data/` como si fuera `/share/rainmapper`:

```text
docker-data/                 -> /share/rainmapper
docker-data/Data/            -> /share/rainmapper/Data
docker-data/Tomap/           -> /share/rainmapper/Tomap
docker-data/mushroom-data/   -> /share/rainmapper/mushroom-data
```

Esto permite introducir observaciones desde:

```text
http://127.0.0.1:8101/mushrooms/profiles?section=observations
```

Los datos que guardes desde esa UI quedan en:

```text
docker-data/mushroom-data/mushroom_observations.json
```

Si `docker-data/mushroom-data/` no existe, la app lo sembrara desde los defaults versionados al arrancar. Para trabajar con los datos reales actuales de HA, copiar previamente `/share/rainmapper/mushroom-data/` dentro de `docker-data/mushroom-data/`.

Comando recomendado desde la raiz del repo:

```bash
./mushroom_lab_start.sh
```

Parar el servidor:

```bash
./mushroom_lab_stop.sh
```

Este servicio no debe usarse para publicar una version HA ni para escribir en Home Assistant. Es solo una copia local de trabajo.

## Estado local al cierre de la iteracion UI

Estado operativo verificado el 2026-06-30:

- El servicio `rainmapper-ha-ui` fue usado para cargar observaciones reales/historicas en local.
- El usuario probo importacion EXIF de varias fotos, duplicado de observaciones, selector de todas las especies, ordenacion y seleccion de filas.
- El flujo local funciona bien para acelerar la carga.
- El contenedor local quedo parado con:

```bash
./mushroom_lab_stop.sh
```

- Los datos locales no se borraron. Las observaciones cargadas siguen en:

```text
docker-data/mushroom-data/mushroom_observations.json
```

Para continuar, el proximo Codex debe arrancar de nuevo el servicio solo si el usuario quiere seguir introduciendo observaciones desde UI:

```bash
./mushroom_lab_start.sh
```

URL:

```text
http://127.0.0.1:8101/mushrooms/profiles?section=observations
```

No usar `docker compose down -v`, no borrar `docker-data/` y no copiar estos datos a HA salvo peticion explicita.

## Que copiar desde Home Assistant

Si se va a usar la WebUI local, copiar primero los datos HA a `docker-data/` porque ese es el volumen que monta el servicio `rainmapper-ha-ui`.

Si se va a ejecutar un experimento aislado por scripts, se puede copiar a `tmp/mushroom-lab/input/ha-data/`.

La preferencia actual para evitar duplicados es usar `docker-data/` como copia operativa local y `tmp/mushroom-lab/` solo para fotos, GIS, intermedios y salidas.

Copiar desde la instalacion HA a:

```text
tmp/mushroom-lab/input/ha-data/
```

### Obligatorio

Desde HA:

```text
/share/rainmapper/Data/
```

hacia `docker-data/Data/` si se trabaja con la WebUI local, o hacia:

```text
tmp/mushroom-lab/input/ha-data/Data/
```

Copiar, como minimo:

- `Meteocat_incremental.csv`
- `Meteoclimatic_incremental.csv`
- `Wunderground_incremental.csv`
- `Aemet_incremental.csv`, si existe
- todos los catalogos de estaciones disponibles, especialmente `estacions*.csv`
- `variables_xema.csv`, si existe

Si existen estos ficheros, copiarlos tambien porque aportan mejor granularidad o viento:

- `Meteoclimatic_observations_incremental.csv`
- `Aemet_hourly_incremental.csv`
- cualquier otro `*_observations_incremental.csv`
- `source_status.json`, solo como diagnostico

### Recomendado

Desde HA:

```text
/share/rainmapper/Tomap/
```

hacia `docker-data/Tomap/` si se trabaja con la WebUI local, o hacia:

```text
tmp/mushroom-lab/input/ha-data/Tomap/
```

`Tomap` no sustituye a los incrementales para el calculo historico, pero sirve para comparar resultados y validar que el laboratorio ve los mismos acumulados publicados por Rainmapper.

### Recomendado para mantener coherencia con la UI actual

Desde HA:

```text
/share/rainmapper/mushroom-data/
```

hacia `docker-data/mushroom-data/` si se trabaja con la WebUI local, o hacia:

```text
tmp/mushroom-lab/input/ha-data/mushroom-data/
```

Copiar:

- `mushroom_profiles.json`
- `mushroom_reference_catalogs.json`
- `mushroom_gis_mappings.json`
- `mushroom_labels.json`
- `mushroom_observations.json`, si existe

Esta copia local permite comparar observaciones experimentales contra las fichas reales sin tocar los datos vivos de HA.

## Donde poner fotos y observaciones

Fotos de recolectas positivas:

```text
tmp/mushroom-lab/input/photos/positive/
```

Estructura recomendada:

```text
tmp/mushroom-lab/input/photos/positive/boletus_pinophilus/
tmp/mushroom-lab/input/photos/positive/lactarius_sanguifluus/
```

Fotos o notas de salidas negativas:

```text
tmp/mushroom-lab/input/photos/negative/
```

Estructura recomendada:

```text
tmp/mushroom-lab/input/photos/negative/2025-10-12_cerdanya_no_boletus/
tmp/mushroom-lab/input/photos/negative/2026-06-18_pirineu_no_marzuolus/
```

### Importacion rapida desde fotos EXIF

La WebUI local incluye un flujo para acelerar la captura de observaciones reales:

```text
Mushroom species > Observaciones > Importar imagenes EXIF
```

Dependencia tecnica:

```text
requirements.txt -> Pillow==12.2.0
```

`Pillow` se usa para leer metadatos EXIF desde las imagenes subidas por la UI. Es necesario tanto en el contenedor local `rainmapper-ha-ui` como en la imagen HA si el flujo EXIF se publica o se mantiene activo. No retirarlo como limpieza de dependencias mientras existan `Importar imagenes EXIF` o recuperacion EXIF desde editar/duplicar.

Compatibilidad esperada:

- Fotos Android en JPEG con EXIF estandar: deben funcionar si contienen fecha de captura y GPS.
- Fotos iPhone en JPEG con EXIF estandar: deben funcionar si contienen fecha de captura y GPS.
- HEIC/HEIF: no darlas por soportadas universalmente hasta probarlas en el contenedor real.
- Si se quiere aceptar HEIC/HEIF de forma robusta, estudiar convertir a JPEG durante la subida preservando EXIF util antes de procesar o guardar metadata. Esto puede requerir dependencia adicional, por ejemplo soporte HEIF para Pillow, y debe documentarse con su impacto en la imagen HA.
- Fotos reenviadas por WhatsApp u otras apps pueden llegar sin EXIF; en ese caso deben saltarse o informar error, no crear observaciones con coordenadas inventadas.

El formulario pide una plantilla comun que se aplica a todas las fotos seleccionadas:

- observador;
- experiencia del observador;
- calidad del origen;
- tamano de la florada;
- estado de validacion;
- especie;
- uso en calibracion.

Para cada imagen, la app intenta extraer de EXIF:

- `observed_at`;
- `latitude`;
- `longitude`;
- `altitude_m`, si existe;
- `source.type = photo_exif`;
- `source.label = nombre del fichero`;
- `location.source = photo_exif`;
- `altitude.source = photo_exif`, si hay altitud.

Se puede seleccionar una foto, varias fotos o una carpeta desde el selector del navegador. Los ficheros sin fecha o GPS se saltan y se informa en el mensaje de estado.

Este flujo esta pensado para el laboratorio local, pero queda implementado con los mismos patrones de la UI productiva para que sea facil publicarlo en HA cuando se valide. En local siempre escribe en:

```text
docker-data/mushroom-data/mushroom_observations.json
```

### Duplicar observaciones

La lista de observaciones incluye accion de duplicar. Es util cuando una misma salida tiene varias especies en el mismo punto o con el mismo contexto.

La accion de duplicar no persiste una observacion nueva inmediatamente. Abre una plantilla sin guardar con los datos de la observacion origen para que se pueda cambiar especie, abundancia, fecha, origen o recuperar datos desde una foto EXIF antes de guardar.

El `observation_id` se genera solo al guardar. Esto es importante porque el formato operativo `obs_YYYYMMDD_NNNN` debe corresponder a la fecha final de la observacion, no a la fecha de la observacion copiada. Si desde la plantilla duplicada se importan una o varias fotos EXIF, cada observacion creada usa la fecha de su propia foto.

Caso de uso principal:

1. Se importa una observacion real desde una foto geolocalizada.
2. Se duplica esa observacion para registrar otra especie de la misma salida.
3. Se cambia especie y tamano de florada.
4. Opcionalmente se sube otra foto EXIF para actualizar fecha, coordenadas, altitud y origen.
5. Al guardar se crea una nueva observacion con ID coherente con la fecha final.

Si se seleccionan varias fotos EXIF desde una plantilla duplicada, la plantilla actua como valores comunes y se crea una observacion por foto.

### Ordenacion de observaciones

La tabla de observaciones se puede ordenar desde las cabeceras por fecha, especie, coordenadas, altitud, tamano de florada, observador, origen, validacion y uso en calibracion.

Esto evita que una lista larga quede en el orden bruto de introduccion.

La fila completa es seleccionable para ver el detalle. Los botones de accion (`Editar`, `Duplicar`, `Archivar`, `Restaurar`, `Borrar definitivamente`) deben preservar filtros, ordenacion, especie seleccionada y estado abierto/cerrado de observaciones archivadas. Esta regla existe para poder limpiar o revisar muchas observaciones sin perder el contexto despues de cada accion.

Observaciones manuales sin foto o correcciones de foto:

```text
tmp/mushroom-lab/input/manual/manual_observations.csv
```

Columnas recomendadas para el primer POC:

```csv
observation_id,species_id,observed_at,latitude,longitude,flush_abundance,source,source_quality,validation_status,notes
```

Valores iniciales:

- `flush_abundance`: `exceptional`, `very_abundant`, `abundant`, `normal`, `scarce`, `very_scarce`, `absent`
- `source`: `photo_exif`, `manual`, `whatsapp`, `field_note`
- `source_quality`: numero entre `0` y `1`
- `validation_status`: `draft`, `valid`, `doubtful`, `invalid`

Para analisis, la ausencia/presencia se deriva de `flush_abundance`: `absent` equivale a observacion negativa y cualquier otro valor equivale a presencia con intensidad de florada.

## Capas GIS

Primera prioridad para Catalunya:

```text
tmp/mushroom-lab/input/gis/icgc/
```

Buscar aqui capas descargadas de ICGC/ICC:

- DEM/elevaciones;
- cubiertas del suelo o vegetacion;
- geologia/litologia;
- suelos, si se localiza una capa util.

Fallback para Espana:

```text
tmp/mushroom-lab/input/gis/ign-cnig/
```

Buscar aqui capas descargadas de IGN/CNIG:

- MDT;
- SIOSE u ocupacion/cobertura del suelo;
- geologia/litologia si se usa una fuente estatal compatible.

Preferencia tecnica:

- raster local, WCS o descarga para DEM;
- vector local, WFS o descarga para poligonos de habitat/suelo/litologia;
- evitar WMS como fuente primaria del calculo porque normalmente devuelve imagen, no atributos estructurados.

### Fuentes GIS candidatas

Estas fuentes no quedan todavia cerradas como implementacion. Son candidatas que deben verificarse antes de usar en codigo:

- ICGC/ICC para Catalunya:
  - modelos digitales de elevaciones;
  - cubiertas del suelo;
  - vegetacion o habitats;
  - geologia/litologia;
  - suelos, si existe una capa con atributos utiles.
- IGN/CNIG para Espana:
  - MDT/DEM;
  - SIOSE u otras capas de ocupacion/cobertura del suelo;
  - servicios WMS/WFS/WCS o descargas oficiales que cubran fuera de Catalunya.
- ICGC/Cartografia geologica y otras capas oficiales catalanas:
  - litologia y substrato;
  - unidades geologicas;
  - posibles proxies de suelo.

Antes de construir extractores, hay que comprobar para cada capa:

- licencia y acceso;
- cobertura territorial;
- resolucion espacial;
- formato disponible;
- si devuelve atributos estructurados por coordenada;
- sistema de referencia;
- estabilidad del servicio o conveniencia de descarga local;
- correspondencia posible con IDs internos de `mushroom_reference_catalogs.json`.

WMS puede servir para inspeccion visual o debug. Para el engine se prefieren descargas locales, WCS o WFS porque necesitamos atributos reproducibles por coordenada.

## Primer motor local esperado

El POC deberia producir:

```text
tmp/mushroom-lab/working/observations/observations_normalized.json
tmp/mushroom-lab/working/features/observations_weather_features.csv
tmp/mushroom-lab/working/features/observations_gis_features.csv
tmp/mushroom-lab/output/parameter-candidates/species_parameter_candidates.json
tmp/mushroom-lab/output/reports/species_observed_conditions.md
```

El motor debe distinguir:

- condiciones observadas reales;
- parametros candidatos;
- datos insuficientes;
- extrapolaciones no validadas.

Con pocas observaciones, el resultado no sera calibracion estadistica. Sera una reconstruccion de condiciones reales y una propuesta experimental.

## Engine experimental de reconstruccion de parametros

El motor local no debe llamarse todavia "predictor productivo". Su objetivo inicial es reconstruir condiciones observadas y proponer candidatos para revision humana.

Entradas minimas:

- `docker-data/mushroom-data/mushroom_observations.json`;
- `docker-data/mushroom-data/mushroom_profiles.json`;
- `docker-data/mushroom-data/mushroom_reference_catalogs.json`;
- `docker-data/mushroom-data/mushroom_gis_mappings.json`;
- incrementales historicos en `docker-data/Data/`;
- capas GIS locales cuando existan.

Salida esperada:

- una tabla por observacion con features meteorologicas previas;
- una tabla por observacion con features GIS/topograficas;
- resumen por especie separando observaciones positivas, negativas, dudosas y excluidas;
- candidatos de parametros con fuente, soporte y confianza;
- reporte humano que explique por que se propone cada candidato.

Reglas del engine:

- No escribir directamente en `mushroom_profiles.json`.
- No modificar Home Assistant.
- No usar observaciones `draft`, `doubtful`, `invalid` o `exclude` salvo que el reporte indique claramente como se han tratado.
- No proponer umbrales numericos si hay menos observaciones de las necesarias para sostenerlos.
- Separar "valor observado" de "parametro recomendado".
- Documentar cada candidato con trazabilidad: observaciones usadas, rango, percentiles o metodo aplicado.
- Si un dato meteorologico o GIS falta, marcarlo como hueco de datos, no inferirlo silenciosamente.

El primer algoritmo puede ser descriptivo:

- calcular min/max/mediana/percentiles de lluvia acumulada 1/7/14/21/30/60/90 dias en observaciones positivas;
- comparar contra observaciones negativas si existen;
- calcular dias desde lluvia significativa usando umbrales globales documentados como experimentales;
- resumir temperatura, humedad, viento y penalizaciones observadas;
- resumir altitud, orientacion, habitat, vegetacion y litologia observadas;
- producir candidatos solo cuando haya senal suficiente y explicar la debilidad cuando no la haya.

Los umbrales globales usados para analisis exploratorio no son automaticamente parametros de especie. Deben quedar marcados como `experimental_analysis_threshold`, no como dato productivo.

## Runbook para la proxima sesion Codex

Objetivo inmediato:

```text
Construir el primer extractor local que tome observaciones reales/historicas y reconstruya las condiciones meteorologicas previas desde los incrementales de Rainmapper.
```

Antes de tocar codigo:

1. Leer `docs/codex-handoff.md`.
2. Leer este documento completo.
3. Leer `docs/mushrooms/mushroom-predictor-design-es.md`.
4. Leer `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`.
5. Leer `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`.
6. Verificar `pwd` en `/Users/carlosginebrosa/Developer/RainmapperHA`.
7. Revisar `git status --short`.
8. Confirmar que se trabaja sobre `docker-data/` y `tmp/mushroom-lab/`, no contra `/share/rainmapper` real de HA.

Datos locales relevantes:

- Observaciones capturadas en local:

```text
docker-data/mushroom-data/mushroom_observations.json
```

- Perfiles/catalogos/mappings locales:

```text
docker-data/mushroom-data/mushroom_profiles.json
docker-data/mushroom-data/mushroom_reference_catalogs.json
docker-data/mushroom-data/mushroom_gis_mappings.json
docker-data/mushroom-data/mushroom_labels.json
```

- Historicos meteorologicos locales copiados desde HA:

```text
docker-data/Data/
```

Si falta algun incremental, pedir al usuario que lo copie desde HA por Samba antes de inventar datos.

No usar los GeoJSON actuales como fuente principal para observaciones historicas. Una observacion de 2025 necesita reconstruirse desde los incrementales historicos de 2025, no desde el estado actual del mapa.

Primer script/engine recomendado:

- leer `mushroom_observations.json`;
- filtrar observaciones activas, validas o marcadas para calibracion segun el criterio que se documente;
- normalizar coordenadas, fecha, especie, abundancia, validacion, `source_quality` y `calibration_use`;
- leer incrementales disponibles en `docker-data/Data/`;
- calcular features previas por observacion:
  - lluvia acumulada 1/7/14/21/30/60/90 dias;
  - dias desde lluvia significativa;
  - racha seca;
  - temperatura minima/maxima/media reciente si existe;
  - humedad disponible;
  - viento disponible;
  - gaps de fuente/fecha;
- escribir resultados en:

```text
tmp/mushroom-lab/working/features/observations_weather_features.csv
tmp/mushroom-lab/working/features/observations_weather_features.json
tmp/mushroom-lab/output/reports/observations_weather_features.md
```

Reglas:

- No modificar `mushroom_profiles.json` desde el script.
- No escribir en HA.
- No versionar observaciones reales ni coordenadas.
- No inventar datos ausentes.
- Si el historico no cubre una fecha, reportar gap.
- Si no se puede determinar la estacion o fuente mas adecuada para una coordenada, documentar el metodo o dejarlo como pendiente.

Decisiones pendientes para el extractor:

- Elegir si se usa la estacion mas cercana, interpolacion ponderada, Tomap reconstruido o una combinacion.
- Definir si el primer POC usa solo lluvia o tambien temperatura/humedad/viento.
- Definir el umbral exploratorio de "lluvia significativa" como parametro global del analisis, no como parametro de especie.
- Decidir como ponderar observaciones negativas frente a positivas.
- Decidir si se incluyen observaciones `draft` o solo `valid`.

Resultado esperado del primer POC:

- No es todavia un predictor.
- Debe producir una tabla verificable de condiciones reales previas a cada observacion.
- Debe permitir mirar, por ejemplo, que condiciones de lluvia/temperatura/humedad habia antes de las observaciones reales de `boletus_aereus` o `amanita_caesarea`.
- Con pocas observaciones, debe decir "datos insuficientes" antes que proponer umbrales falsamente precisos.

## Fases del laboratorio

### Fase 1: observaciones y meteorologia

Objetivo: validar que podemos reconstruir condiciones meteorologicas reales previas a una recolecta o salida negativa.

Entradas:

- observaciones positivas;
- observaciones negativas;
- incrementales locales copiados desde HA.

Salidas:

- observaciones normalizadas;
- lluvia acumulada previa a 1/7/14/21/30/60/90 dias;
- dias desde lluvia significativa;
- racha seca;
- temperatura y humedad disponibles;
- viento disponible, sabiendo que su historico empieza mas tarde.

En esta fase no se necesitan todavia DEM ni GIS para validar el concepto.

### Fase 2: DEM y topografia

Objetivo: enriquecer cada observacion con contexto topografico.

Entradas:

- DEM local de ICGC/ICC o IGN/CNIG.

Salidas:

- altitud;
- pendiente;
- orientacion;
- posibles proxies derivados de humedad topografica, si se decide y se documenta.

### Fase 3: cubiertas, vegetacion, litologia y suelo

Objetivo: enriquecer cada observacion con habitat estatico.

Entradas:

- cubiertas del suelo;
- vegetacion o tipos de bosque;
- geologia/litologia;
- suelos si hay capa util.

Salidas:

- IDs crudos de las capas;
- etiquetas humanas de la fuente;
- traduccion a IDs internos mediante `mushroom_gis_mappings.json` cuando exista;
- gaps donde falte mapping.

### Fase 4: candidatos de parametros por especie

Objetivo: resumir condiciones observadas por especie.

Salidas:

- rangos observados;
- valores frecuentes;
- diferencias entre positivas y negativas;
- numero de observaciones usadas;
- calidad/confianza;
- parametros candidatos marcados como `experimental`.

Los candidatos no se aplican automaticamente a `mushroom_profiles.json`.

Formato conceptual de candidato:

```json
{
  "species_id": "boletus_aereus",
  "candidate_id": "weather_model.rainfall.rain_15d_optimal_min_mm",
  "current_value": 35,
  "candidate_value": 42,
  "evidence_type": "local_observations",
  "observation_ids": ["obs_20250806_0001", "obs_20250805_0001"],
  "positive_count": 2,
  "negative_count": 0,
  "confidence": "low",
  "status": "experimental",
  "notes": "Insufficient sample; keep as review-only candidate."
}
```

Con pocas observaciones, el campo `candidate_value` puede quedar vacio y el reporte puede limitarse a describir condiciones observadas.

### Fase 5: promocion manual

Objetivo: revisar candidatos y decidir que pasa a la ficha real.

Reglas:

- cada cambio debe indicar fuente: observacion local, literatura o decision manual;
- no sobrescribir bloques completos;
- aplicar campo a campo;
- conservar el perfil como dato mantenido, no como salida automatica opaca.

## Futuro boton en la UI

En una fase posterior puede tener sentido un boton en la ficha de especies, pero no debe llamarse ni comportarse como "regenerar parametros" en sentido destructivo.

Comportamiento recomendado:

```text
Recalcular candidatos desde observaciones
```

Ese boton deberia:

- recalcular condiciones observadas y candidatos;
- mostrar diferencias entre valor actual, rango observado y candidato;
- mostrar numero de observaciones positivas/negativas;
- mostrar confianza y huecos de datos;
- permitir aplicar manualmente campos concretos;
- no sobrescribir automaticamente el perfil completo.

Hasta que el laboratorio local este validado, este flujo debe hacerse por scripts locales controlados, no desde la UI productiva de HA.

## Siguiente paso operativo

1. Copiar los historicos y `mushroom-data` actuales de HA a `docker-data/`.
2. Arrancar `rainmapper-ha-ui` y abrir `/mushrooms/profiles?section=observations`.
3. Introducir dos o tres observaciones positivas y, si existen, una o dos negativas.
4. Construir el extractor meteorologico usando `docker-data/Data`.
5. Probar el POC meteorologico antes de introducir DEM/GIS.
6. Anadir DEM.
7. Anadir cubiertas/litologia.
8. Generar candidatos de parametros por especie.
