# Schema de observaciones de setas

Este documento define el primer schema operativo de observaciones de setas para calibrar y confirmar los parametros de los perfiles de especies.

El schema es deliberadamente exhaustivo, pero no obliga a informar todos los campos. Una persona debe poder crear una observacion util con especie, fecha, ubicacion, abundancia de florada, calidad del origen y estado de validacion. El resto de campos enriquecen la calibracion cuando esten disponibles.

## Objetivos

- Capturar observaciones reales positivas y negativas para calibrar perfiles de especies.
- Permitir alta rapida desde reportes habituales, especialmente enlaces copiados de Google Maps.
- Conservar procedencia y fiabilidad para ponderar observaciones durante la calibracion.
- No mezclar observaciones dentro de `mushroom_profiles.json` ni `mushroom_reference_catalogs.json`.
- Mantener etiquetas traducibles desde `mushroom-data/mushroom_labels.json`.
- Mantener valores seleccionables en `mushroom-data/mushroom_reference_catalogs.json` para poder evolucionarlos sin cambios de codigo.

## Almacenamiento

Fichero futuro recomendado:

```text
mushroom-data/mushroom_observations.json
```

La copia persistente en HA deberia seguir el patron actual de datos de setas:

```text
/share/rainmapper/mushroom-data/mushroom_observations.json
```

Los valores controlados usados por este schema viven bajo `catalogs` en `mushroom_reference_catalogs.json`:

- `observation_flush_abundance`
- `observation_validation_statuses`
- `observation_calibration_uses`
- `observation_exclusion_reasons`
- `observation_source_types`
- `observer_expertise_levels`
- `observation_location_sources`
- `observation_altitude_sources`

Las pantallas UI deben leer etiquetas, orden y metadata de calibracion desde estos catalogos en vez de hardcodear valores.

## Observacion minima valida

```json
{
  "observation_id": "obs_20260629_0001",
  "species_id": "boletus_pinophilus",
  "observed_at": "2026-06-29",
  "location": {
    "lat": 42.35406,
    "lon": 1.85317
  },
  "flush_abundance": "abundant",
  "source_quality": 0.8,
  "validation_status": "draft",
  "calibration_use": "review"
}
```

Campos obligatorios:

- `observation_id`
- `species_id`
- `observed_at`
- `location.lat`
- `location.lon`
- `flush_abundance`
- `source_quality`
- `validation_status`
- `calibration_use`

## Observacion completa

```json
{
  "observation_id": "obs_20260629_0001",
  "species_id": "boletus_pinophilus",
  "observed_at": "2026-06-29",
  "location": {
    "input": "https://maps.google.com/...",
    "lat": 42.35406,
    "lon": 1.85317,
    "source": "google_maps_url",
    "precision_m": null
  },
  "altitude": {
    "meters": 1259,
    "source": "google_maps",
    "resolved_at": "2026-06-29T10:30:00Z"
  },
  "flush_abundance": "abundant",
  "observer": {
    "name": "Carlos",
    "expertise": "experienced"
  },
  "source": {
    "type": "personal_observation",
    "label": "",
    "url": "",
    "notes": ""
  },
  "source_quality": 0.9,
  "validation_status": "valid",
  "calibration_use": "include",
  "calibration_exclusion_reason": "",
  "derived": {
    "month": 6,
    "season": "summer"
  },
  "site_context": {
    "observed_host_ids": [
      "host_pinus_sylvestris",
      "host_quercus_ilex"
    ],
    "observed_forest_type_ids": [
      "forest_montane_pine"
    ],
    "observed_soil_tendency_ids": [
      "soil_siliceous"
    ],
    "observed_habitat_feature_ids": [
      "feature_mature_forest"
    ],
    "observed_aspect_ids": [
      "aspect_N"
    ],
    "habitat_notes": "",
    "host_notes": "",
    "soil_notes": "",
    "aspect_notes": ""
  },
  "metadata": {
    "created_at": "2026-06-29T10:30:00Z",
    "updated_at": "2026-06-29T10:30:00Z",
    "created_by": "webui",
    "reviewed_by": "",
    "reviewed_at": ""
  }
}
```

## Definicion de campos

### Identidad

`observation_id` es un ID unico y estable. Formato sugerido para altas desde UI: `obs_YYYYMMDD_NNNN`. Los imports pueden usar un prefijo determinista por origen.

`species_id` debe referenciar una especie activa de `mushroom_profiles.json`. Las especies archivadas deberian exigir revision explicita antes de usar la observacion para calibrar.

`observed_at` es la fecha de observacion en formato ISO, `YYYY-MM-DD`. La hora queda opcional porque la mayoria de reportes de setas son a nivel de dia.

`derived.month` y `derived.season` son campos persistidos baratos calculados
desde `observed_at` al guardar. No son entrada manual ni sustituyen a la
fenologia de la especie. Sirven para evitar recomputo durante reconstrucciones
del modelo v0. Si faltan en observaciones antiguas, los builders pueden
recalcularlos desde `observed_at`.

Estaciones simples:

- `winter`: diciembre, enero, febrero.
- `spring`: marzo, abril, mayo.
- `summer`: junio, julio, agosto.
- `autumn`: septiembre, octubre, noviembre.

### Ubicacion

`location.input` guarda el valor original pegado por el usuario. Puede ser un enlace de Google Maps, coordenadas decimales u otro texto de ubicacion.

`location.lat` y `location.lon` usan coordenadas decimales WGS84. Este es el formato canonico.

`location.source` registra como se obtuvieron las coordenadas:

- `manual_decimal`
- `google_maps_url`
- `device_gps`
- `imported_csv`
- `inferred`

`location.precision_m` es opcional. Debe usarse si el origen informa incertidumbre, si se difumina la ubicacion de forma intencionada o si un import es aproximado.

La UI debe poder parsear URLs habituales de Google Maps y cadenas de coordenadas. Si el parseo falla, la observacion debe quedar en draft hasta corregir coordenadas.

### Altitud

`altitude.meters` es opcional pero importante para calibracion. Si falta, la UI deberia ofrecer una accion `Recover altitude` a partir de coordenadas.

`altitude.source` registra el origen de la altitud:

- `manual`
- `google_maps`
- `dem`
- `imported`

`altitude.resolved_at` registra cuando se recupero automaticamente la altitud.

### Tamano de la florada

`flush_abundance` es el resultado observado. Es categorico, ordenado y obligatorio.

Los valores permitidos se mantienen en `catalogs.observation_flush_abundance`:

- `exceptional`
- `very_abundant`
- `abundant`
- `normal`
- `scarce`
- `very_scarce`
- `absent`

El catalogo tambien guarda el `calibration_score` numerico usado por la calibracion:

| Valor | Score |
| --- | ---: |
| `exceptional` | 1.00 |
| `very_abundant` | 0.85 |
| `abundant` | 0.70 |
| `normal` | 0.50 |
| `scarce` | 0.30 |
| `very_scarce` | 0.15 |
| `absent` | 0.00 |

Las observaciones negativas (`absent`) son muy valiosas si fecha, especie, ubicacion y calidad del origen son creibles.

### Contexto observado de campo

`site_context.observed_host_ids` recoge arboles declarados por el observador en
el punto. La UI limita este campo a pocos hosts para evitar convertirlo en una
lista exhaustiva poco fiable.

Los campos `site_context.observed_forest_type_ids`,
`site_context.observed_soil_tendency_ids`,
`site_context.observed_habitat_feature_ids` y
`site_context.observed_aspect_ids` permiten declarar, de forma opcional,
bosque, suelo, rasgos de habitat y orientacion observados. Deben usar IDs de
`forest_types`, `soil_types`, `habitat_features` y `aspects`.

Estos valores representan evidencia de campo. No sustituyen automaticamente a
GIS/DEM ni a los parametros de especie; el modelo v0 aprendido debe conservar
su procedencia como fuente `field`.

### Origen y fiabilidad

`observer.name` es opcional.

`observer.expertise` es opcional. Los valores se mantienen en `catalogs.observer_expertise_levels`:

- `unknown`
- `beginner`
- `experienced`
- `expert`

`source.type` es opcional pero recomendable. Los valores se mantienen en `catalogs.observation_source_types`:

- `personal_observation`
- `trusted_observer`
- `whatsapp`
- `telegram`
- `social_media`
- `forum`
- `imported_dataset`
- `other`

`source_quality` es obligatorio. Es un numero entre `0.0` y `1.0` que representa la fiabilidad del origen antes de aplicar el estado de validacion.

Ejemplos sugeridos:

- `0.95`: observacion propia con coordenadas exactas.
- `0.90`: observador experto de confianza.
- `0.70`: reporte verbal fiable.
- `0.40`: reporte generico de red social o grupo.
- `0.20`: rumor o reporte poco atribuible.

### Validacion

`validation_status` es obligatorio. Los valores se mantienen en `catalogs.observation_validation_statuses`:

- `draft`
- `valid`
- `doubtful`
- `invalid`

El catalogo tambien guarda el `calibration_multiplier` usado por la calibracion:

| Estado | Multiplicador |
| --- | ---: |
| `valid` | 1.00 |
| `draft` | 0.50 |
| `doubtful` | 0.25 |
| `invalid` | 0.00 |

`source_quality` y `validation_status` se separan de forma intencionada. La calidad del origen mide la fiabilidad de quien informa; el estado de validacion mide cuanto acepta Rainmapper esa observacion.

### Uso en calibracion

`calibration_use` es obligatorio y controla si una observacion entra en la calibracion.

Los valores permitidos se mantienen en `catalogs.observation_calibration_uses`:

- `include`: usar para calibracion.
- `exclude`: no usar para calibracion.
- `review`: pendiente de decidir.

No es lo mismo que `validation_status`. Un registro puede ser valido pero excluirse porque la ubicacion es imprecisa, es duplicado, queda fuera del area modelada o no es una observacion silvestre.

`calibration_exclusion_reason` es opcional. Los valores se mantienen en `catalogs.observation_exclusion_reasons`:

- `location_too_imprecise`
- `species_uncertain`
- `cultivated_or_market`
- `duplicate`
- `outside_model_area`
- `invalid_date`
- `other`

### Contexto del sitio

`site_context` es opcional. La primera informacion estructurada de sitio es:

- `observed_host_ids`: hasta 3 arboles/hosts observados en campo, como IDs de `catalogs.host_taxa`.

Este campo describe lo observado por la persona en el punto, no lo inferido por GIS. Sirve para comparar observaciones reales contra `host_affinities` de la especie y, mas adelante, contra hosts o tipos forestales inferidos desde capas oficiales.

El resto queda como notas libres:

- `habitat_notes`
- `host_notes`
- `soil_notes`
- `aspect_notes`

Estas notas no sustituyen las afinidades catalogadas de especie. Describen lo observado en un sitio concreto.

### Imagen o video asociado

Cada observacion admite como maximo un archivo multimedia asociado. `media[]`
usa `kind: photo` para imagenes y `kind: video` para videos. Las imagenes se
guardan bajo `media/observation-photos/`.

Los videos se normalizan al importarlos: MP4 con video H.264, audio AAC,
resolucion maxima 854x480 y los primeros 30 segundos. El original no se
conserva. Fecha/hora, GPS y altitud util se guardan en `capture_metadata` y se
copian tambien al contenedor MP4 cuando estan disponibles. Una altitud
QuickTime igual a cero se considera ausente porque el iPhone la usa como
marcador cuando no dispone de altitud. En ese caso, si hay coordenadas, la
vista previa propone la elevacion consultada en el DEM y la identifica como
`Origen DEM`; al aplicarla se persiste con `altitude.source: dem`. Para que la
lista y la vista previa no dependan del soporte de miniaturas del navegador,
se genera un poster JPEG a partir de un fotograma del video.

El endpoint privado de media admite peticiones `HEAD` y rangos HTTP de un solo
intervalo (`206 Partial Content`, `Content-Range` y `Accept-Ranges: bytes`) para
que Safari pueda reproducir el MP4 dentro del ingress de Home Assistant.

El limite es 100 MB por archivo y 500 MB por importacion multiple. Los tres
modos de la UI son comunes para imagen y video: asociar solo el archivo,
actualizar solo los datos de captura o realizar ambas operaciones.

### Metadata

`metadata.created_at`, `metadata.updated_at`, `metadata.created_by`, `metadata.reviewed_by` y `metadata.reviewed_at` sirven para auditoria y mantenimiento.

## Peso de calibracion

La primera version de calibracion puede calcular un peso efectivo:

```text
effective_weight = source_quality * validation_multiplier
```

Despues `calibration_use` decide si la observacion ponderada se incluye, se excluye o queda pendiente de revision.

## Requisitos de UI

- Crear observaciones rapido con los campos obligatorios minimos.
- Aceptar URLs de Google Maps o coordenadas decimales en un solo input.
- Guardar la ubicacion original pegada en `location.input`.
- Parsear a coordenadas decimales WGS84.
- Ofrecer `Recover altitude` desde coordenadas.
- Mostrar tamano de florada como selector ordenado, no como numero libre.
- Mostrar `source_quality` como porcentaje o control 0-1.
- Mantener campos avanzados opcionales y plegables.
- Marcar para revision registros sin coordenadas, especie, fecha o decision de calibracion.
# Extension de areas conocidas (2026-07-11)

Cada observacion puede incluir opcionalmente:

```json
"micro_area_id": "olvan_la_pera"
```

El ID referencia una microarea activa o historica de
`mushroom_known_sites.json`. El `area_id` padre no se duplica en la observacion;
se resuelve desde ese store. Las observaciones antiguas sin `micro_area_id`
siguen siendo validas.
