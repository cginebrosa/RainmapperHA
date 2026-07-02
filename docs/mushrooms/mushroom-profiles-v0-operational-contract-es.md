# Contrato operativo v0 de perfiles de setas

Este documento fija la direccion acordada para no tirar el trabajo existente de
perfiles, catalogos, mappings GIS y UI de mantenimiento.

La v0 no crea un modelo paralelo definitivo. La v0 es una vista operativa minima
encima de `mushroom_profiles.json`: usa solo los campos que el primer predictor
puede defender con fuente revisada, GIS amplio y observaciones locales futuras.
Los campos ricos existentes quedan aparcados, no borrados.

## Principio

```text
mushroom_profiles.json rico
  -> proyeccion v0 operativa
  -> motor v0 y futura UI v0
```

La proyeccion vive en codigo en:

```text
rainmapper_core/mushroom_profile_v0.py
```

No modifica el JSON productivo. Lee perfiles ricos y devuelve un payload v0 con
campos activos y campos aparcados declarados explicitamente.

La fuente normalizada inicial y su auditor viven en:

```text
docs/mushrooms/literature/marc-estevez-v0-source-normalized.json
scripts/audit-mushroom-profile-v0-source.py
```

El auditor escribe reportes locales bajo `tmp/mushroom-lab/` y comprueba que los
21 perfiles productivos actuales de `mushroom_profiles.json` estan cubiertos por
la fuente normalizada.

## Campos activos v0

La v0 usa:

- identidad de especie: `species_id`, `scientific_name`, `common_names`,
  `taxonomy_status`, `edibility`;
- modo trofico: `ecology.trophic_mode_id`;
- vegetacion/host: `ecology.host_affinities`, pero sin usar pesos numericos;
- tipo de bosque/habitat: `ecology.forest_type_affinities`, sin pesos
  numericos;
- suelo amplio: `ecology.soil_affinities`, tratado como tendencia edafica;
- rasgos simples de habitat: `ecology.habitat_feature_affinities`;
- temporada: `phenology.main_months`, `phenology.secondary_months`,
  `phenology.season_pattern_ids`;
- altitud aproximada: `topography.altitude_min_m` y
  `topography.altitude_max_m`;
- orientacion como rasgo blando: `topography.preferred_aspect_ids` y
  `topography.aspect_notes`;
- estado de revision y calibracion:
  `metadata.review_status`,
  `metadata.requires_human_validation`,
  `prediction_confidence.local_calibration_status`.

Los registros de afinidad v0 conservan solo:

```json
{"id": "host_pinus_sylvestris", "relationship": "primary"}
```

La clave `affinity` numerica del perfil rico no se promociona a v0 porque no
esta calibrada.

## Campos aparcados para v0

Estos campos siguen en `mushroom_profiles.json`, pero no son parametros activos
del motor v0:

- `ecology.lithology_affinities`;
- `phenology.fruiting_delay_after_rain_days`;
- `topography.altitude_optimal_min_m`;
- `topography.altitude_optimal_max_m`;
- `weather_model`;
- `scoring_weights`;
- umbrales/confianza meteorologica fina;
- minimos de observaciones para calibracion.

Esto no significa que sobren. Significa que pertenecen a una fase posterior,
cuando exista soporte verificable por fuente u observaciones locales suficientes.

## Catalogos

`mushroom_reference_catalogs.json` se mantiene como vocabulario comun. La v0
debe reutilizarlo antes de crear campos nuevos.

Catalogos reutilizables directamente:

- `trophic_modes`;
- `host_taxa`;
- `forest_types`;
- `soil_types`;
- `season_patterns`;
- `aspects`;
- `habitat_features`;
- catalogos de observaciones.

Si faltan claves amplias necesarias para v0, se anaden aqui con labels en
`en`, `es` y `ca`, y se validan igual que el resto.

La primera auditoria de gaps vive en:

```text
docs/mushrooms/mushroom-v0-catalog-gap-audit-es.md
```

## GIS mappings

`mushroom_gis_mappings.json` tambien se conserva. Su papel v0 es traducir capas
externas hacia senales amplias:

- `mapped_host_ids`;
- `mapped_forest_type_ids`;
- `mapped_soil_tendency_ids`;
- `mapped_habitat_feature_ids`.

La litologia fina puede seguir como trazabilidad o enriquecimiento futuro, pero
el output principal de v0 debe ser la tendencia edafica amplia cuando sea
defendible. Las entradas `accepted` son las unicas computables; `pending_review`
e `ignored` no alimentan el motor.

## UI de mantenimiento

La UI actual no se descarta. Se aparca como vista rica/avanzada.

Direccion para la futura UI v0:

- usar la misma pantalla base de mantenimiento de especies;
- mantener store, backups, validacion, labels, catalogos, archivado y raw JSON;
- mostrar primero solo campos activos v0;
- ocultar `weather_model`, `scoring_weights` y litologia fina del flujo normal;
- dejar la vista rica como avanzada/futura, sin borrarla;
- mostrar claramente que la especie esta `not_calibrated` hasta que las
  observaciones locales lo justifiquen.

Las observaciones no cambian de contrato por esta decision. Siguen siendo la
evidencia local que servira para contrastar y calibrar la v0.

## Regla de promocion

Un dato no pasa a parametro activo v0 por estar presente en el perfil rico. Solo
entra en la proyeccion v0 si esta en la lista de campos activos y no depende de
pesos, umbrales o litologia fina no calibrada.

El flujo correcto es:

```text
perfil rico existente
  -> proyeccion v0 sin pesos numericos
  -> motor v0 explicable
  -> observaciones + meteorologia + GIS
  -> candidatos revisables
  -> promocion manual si aporta valor
```
