# Diccionario de labels de setas

Este documento define el contrato de `mushroom-data/mushroom_labels.json`.

El fichero existe para evitar que la UI de setas muestre claves raw del modelo como `rain_7d_min_mm`, `observation_source_types` o `not_calibrated`, y para permitir mostrar el dominio `mushrooms` en `en`, `es` y `ca`.

## Fichero

```text
mushroom-data/mushroom_labels.json
```

En Home Assistant, la copia persistente vive en:

```text
/share/rainmapper/mushroom-data/mushroom_labels.json
```

En el laboratorio local, la copia de trabajo vive en:

```text
docker-data/mushroom-data/mushroom_labels.json
```

## Regla principal

La UI del dominio `mushrooms` debe pedir labels a `mushroom_labels.json` y no hardcodear textos visibles si esos textos pertenecen al modelo de setas.

Si falta una label, la UI debe mostrar:

```text
missing label: <clave>
```

No debe haber fallback silencioso a la key raw. Esta regla es deliberada: permite detectar huecos de traduccion y evitar pantallas mezcladas con claves internas.

## Idiomas soportados

Cada entrada debe tener:

```json
{
  "en": "...",
  "es": "...",
  "ca": "..."
}
```

`ui_language` se configura en `rainmapper-app/config.yaml` y el runtime HA lo expone como:

```text
RAINMAPPER_MUSHROOM_UI_LANGUAGE
```

Valores soportados:

- `en`
- `es`
- `ca`

Desde `0.2.177`, `ui_language` aplica al dominio `mushrooms`. Control Board y Users quedan fuera de esta fase.

## Tipos de claves

### Campos y parametros del modelo

Claves directas que coinciden con campos JSON:

```text
rain_7d_min_mm
temp_min_7d_optimal_min_c
humidity_min_7d_preferred_min_pct
dry_wind_sensitive
species_id
observation_id
source_quality
validation_status
calibration_use
```

Uso:

- formularios de especies;
- tab `Parametros`;
- tab `Meteorologia`;
- tab `Puntuacion`;
- tab `Confianza`;
- observaciones.

### UI general

Prefijo:

```text
ui.*
```

Ejemplos:

```text
ui.observations
ui.new_observation
ui.import_exif_images
ui.all_species
ui.date_short
ui.status_short
ui.duplicate
```

Uso:

- botones;
- titulos;
- cabeceras;
- mensajes;
- textos de ayuda;
- etiquetas no pertenecientes a un campo JSON concreto.

### Grupos de catalogo

Prefijo:

```text
catalog_group.*
```

Ejemplos:

```text
catalog_group.trophic_modes
catalog_group.host_taxa
catalog_group.season_patterns
catalog_group.observation_source_types
catalog_group.observer_expertise_levels
```

Uso:

- tarjetas superiores de `/mushrooms/catalogs`;
- filtros y detalle de catalogos;
- textos de dominio.

Los grupos nuevos de `mushroom_reference_catalogs.json` deben tener siempre su `catalog_group.<group_id>`.

### Valores controlados no catalogados

Prefijo:

```text
value.*
```

Ejemplos:

```text
value.medium
value.high
value.not_calibrated
value.draft
value.accepted
value.true
```

Uso:

- estados de confianza;
- prioridad;
- estado de calibracion;
- estado de revision;
- taxonomia/comestibilidad cuando se representen como valores controlados del modelo.

Los valores que ya viven en `mushroom_reference_catalogs.json` deben tomar su label del catalogo, no duplicarse como `value.*` salvo que tambien existan como valor de otro campo no catalogado.

## Relacion con reference catalogs

`mushroom_reference_catalogs.json` contiene labels propias por entrada:

```json
{
  "id": "season_summer",
  "label_en": "Summer",
  "label_es": "Verano",
  "label_ca": "Estiu"
}
```

Eso se usa para valores de catalogo como:

- `season_patterns`;
- `aspects`;
- `host_taxa`;
- `forest_types`;
- `soil_types`;
- `lithology_types`;
- catalogos de observaciones.

`mushroom_labels.json` no debe duplicar cada entrada de catalogo. Debe nombrar el grupo, campos de UI y campos del modelo. Las entradas concretas del catalogo se traducen desde el propio catalogo.

## Relacion con observations

La UI de observaciones usa:

- `mushroom_labels.json` para campos, botones, cabeceras y textos de ayuda;
- `mushroom_reference_catalogs.json` para valores tabulados de abundancia, validacion, uso, origen, experiencia, fuente de coordenadas y fuente de altitud.

Ejemplo:

- label de campo `flush_abundance`: `mushroom_labels.json`;
- opciones `abundant`, `scarce`, `none`: `mushroom_reference_catalogs.json`.

## Relacion con Parameters y Species

La pantalla `Parametros` y las tabs internas de especie deben usar labels humanas para:

- modelo climatico;
- scoring;
- confianza;
- fenologia;
- topografia;
- metadata;
- observaciones;
- botones de mantenimiento.

Los nombres raw del JSON solo deben aparecer en:

- paneles avanzados JSON;
- mensajes tecnicos de validacion;
- situaciones de `missing label`.

## Como añadir una label nueva

1. Decidir si es:
   - campo del modelo;
   - texto UI;
   - grupo de catalogo;
   - valor controlado no catalogado;
   - entrada de catalogo.
2. Si es entrada de catalogo, añadir `label_en`, `label_es`, `label_ca` en `mushroom_reference_catalogs.json`.
3. Si no es entrada de catalogo, añadir clave en `mushroom_labels.json`.
4. Añadir los tres idiomas.
5. Ejecutar validacion/render smoke cuando aplique.
6. Si la UI muestra `missing label`, no ocultarlo con fallback; añadir la clave que falta.

## Que no hacer

- No recrear `mushroom_parameter_labels.json`.
- No mantener dos diccionarios paralelos de labels de setas.
- No hardcodear traducciones en `web_server.py`, `mushroom_profiles_ui.py` o `mushroom_catalogs_ui.py` cuando pertenezcan al dominio `mushrooms`.
- No usar fallback silencioso a la clave raw.
- No copiar todas las entradas de catalogo a `mushroom_labels.json`.
- No usar labels como fuente semantica del motor. El motor usa IDs, no textos traducidos.

## Estado actual

`mushroom_labels.json` centraliza actualmente:

- labels visibles de perfiles;
- parametros climaticos;
- scoring;
- confianza/calibracion;
- metadata;
- observaciones;
- botones y textos de UI del dominio `mushrooms`;
- nombres de grupos de reference catalogs;
- valores controlados no catalogados.

Pendiente futuro:

- construir un mantenimiento visual especifico de labels si el fichero crece demasiado;
- extender el patron de `ui_language` a Control Board y Users, probablemente con otro diccionario o una capa i18n general, no mezclando textos no relacionados dentro de `mushroom_labels.json`;
- añadir validacion automatica de cobertura de labels para pantallas principales.
