# Referencia de `mushroom_reference_catalogs.json`

Versión del documento: borrador 0.1
Fichero descrito: `mushroom_reference_catalogs.json`

Este fichero es el vocabulario maestro del módulo de predicción de floradas. Define todos los IDs que pueden utilizar `mushroom_profiles.json` y `mushroom_gis_mappings.json`.

## 1. Responsabilidad del fichero

`mushroom_reference_catalogs.json` responde a la pregunta:

```text
¿Qué valores ecológicos, taxonómicos, geográficos y semánticos son válidos en el sistema?
```

Debe evitar que la aplicación acabe usando variantes de texto como:

```text
acidic / acid / ácido / acid_soil / siliceous acidic
```

En su lugar, se usa un ID estable:

```text
soil_acidic
```

## 2. Estructura raíz

```json
{
  "schema_version": "0.1",
  "model_purpose": "reference_catalogs_for_mushroom_fruiting_probability_scoring",
  "important_note": "...",
  "catalogs": {},
  "metadata": {}
}
```

## 3. Grupos de catálogo actuales

El bloque `catalogs` contiene:

- `trophic_modes`
- `host_taxa`
- `forest_types`
- `soil_types`
- `lithology_types`
- `aspects`
- `season_patterns`
- `habitat_features`

Cobertura actual:

- `trophic_modes`: 4 entradas
- `host_taxa`: 26 entradas
- `forest_types`: 18 entradas
- `soil_types`: 17 entradas
- `lithology_types`: 13 entradas
- `aspects`: 10 entradas
- `season_patterns`: 17 entradas
- `habitat_features`: 9 entradas

## 4. Convención de IDs

Los IDs deben ser:

- estables;
- en minúsculas;
- con guiones bajos;
- legibles;
- únicos dentro de su catálogo;
- no dependientes del idioma de visualización.

Ejemplos:

```text
trophic_ectomycorrhizal
host_pinus_sylvestris
forest_montane_pine
soil_calcareous
lith_limestone
aspect_NE
season_autumn_main
feature_snowmelt
```

No cambiar IDs existentes sin migración.

## 5. Catálogo `trophic_modes`

Define el modo trófico o estrategia ecológica de la seta.

Ejemplos:

- `trophic_ectomycorrhizal`
- `trophic_saprotrophic`
- `trophic_saprotrophic_or_facultative_complex`
- `trophic_saprotrophic_or_plant_associated_grassland`

Uso principal:

```json
"ecology": {
  "trophic_mode_id": "trophic_ectomycorrhizal"
}
```

## 6. Catálogo `host_taxa`

Define árboles, géneros, familias o grupos hospedadores.

Campos habituales:

```json
{
  "id": "host_pinus_sylvestris",
  "rank": "species",
  "scientific_name": "Pinus sylvestris",
  "genus": "Pinus",
  "family": "Pinaceae",
  "common_names": {
    "es": ["pino silvestre"],
    "ca": ["pi roig"],
    "en": ["Scots pine"]
  },
  "parent_id": "host_pinus_spp"
}
```

### Jerarquía

`parent_id` permite relacionar especies con géneros o grupos:

```text
host_pinus_sylvestris → host_pinus_spp
host_pinus_uncinata   → host_pinus_spp
host_quercus_ilex     → host_quercus_spp
```

Esto permite que una capa GIS que sólo diga “Pinus spp.” pueda seguir siendo útil.

## 7. Catálogo `forest_types`

Define tipos de bosque o hábitat vegetal.

Ejemplos:

- `forest_montane_pine`
- `forest_subalpine_pine`
- `forest_mediterranean_pine`
- `forest_calcareous_pine`
- `forest_mediterranean_oak`
- `forest_chestnut`
- `forest_riparian`
- `habitat_grassland_meadow`

Uso:

```json
"forest_type_affinities": [
  {
    "id": "forest_montane_pine",
    "relationship": "preferred",
    "affinity": 0.95
  }
]
```

## 8. Catálogo `soil_types`

Define tipos/tendencias de suelo.

Ejemplos:

- `soil_acidic`
- `soil_neutral`
- `soil_basic`
- `soil_calcareous`
- `soil_siliceous`
- `soil_sandy`
- `soil_humus_rich`
- `soil_waterlogged`
- `soil_well_drained`

Campos posibles:

- `label`: nombres por idioma;
- `ph_min` / `ph_max` si aplica;
- `texture`;
- `organic_matter`;
- `drainage`.

El suelo puede venir de una capa edafológica real o inferirse parcialmente desde litología.

## 9. Catálogo `lithology_types`

Define litología o sustrato geológico.

Ejemplos:

- `lith_granite`
- `lith_schist`
- `lith_sandstone`
- `lith_limestone`
- `lith_dolomite`
- `lith_calcareous_marl`
- `lith_alluvial`
- `lith_variable`

Campos útiles:

```json
{
  "id": "lith_limestone",
  "label": { "es": "Caliza" },
  "general_reaction": "basic",
  "parent_soil_tendency": ["soil_calcareous", "soil_basic"]
}
```

La litología no equivale exactamente al suelo, pero permite derivar tendencias.

## 10. Catálogo `aspects`

Define orientaciones topográficas.

Ejemplos:

- `aspect_N`
- `aspect_NE`
- `aspect_E`
- `aspect_SE`
- `aspect_S`
- `aspect_SW`
- `aspect_W`
- `aspect_NW`
- `aspect_flat`
- `aspect_riparian`

Se usa con el DEM para puntuar orientación.

## 11. Catálogo `season_patterns`

Define etiquetas fenológicas.

Ejemplos:

- `season_spring`
- `season_late_winter`
- `season_summer`
- `season_autumn_main`
- `season_late_autumn`
- `season_snowmelt_associated`
- `season_summer_after_storms`
- `season_early_winter_mild_areas`

Estas etiquetas complementan `main_months` y `secondary_months`.

## 12. Catálogo `habitat_features`

Define rasgos de microhábitat o contexto.

Ejemplos:

- `feature_mossy`
- `feature_humus_rich_litter`
- `feature_riparian`
- `feature_forest_edge`
- `feature_burned_forest`
- `feature_disturbed_soil`
- `feature_snowmelt`
- `feature_grassland_fairy_ring`
- `feature_open_woodland`

Estos rasgos pueden venir de GIS, observaciones o reglas derivadas.

## 13. Relación con los otros ficheros

`mushroom_profiles.json` referencia IDs de todos estos catálogos.

`mushroom_gis_mappings.json` emite IDs de estos catálogos cuando encuentra clases GIS externas.

Por tanto, cualquier ID usado en perfiles o mapeos debe existir aquí.

## 14. Flujo para añadir nuevos valores

Cuando una especie necesita un nuevo host, suelo, litología o rasgo:

1. Comprobar si ya existe un ID equivalente.
2. Si no existe, añadirlo al catálogo correcto.
3. Usar un ID estable y claro.
4. Añadir nombres comunes si aplica.
5. Añadir `parent_id` si es taxonómico.
6. Actualizar perfiles o mapeos para usar el nuevo ID.
7. Ejecutar validación cruzada.

## 15. Reglas para Codex

Codex no debe crear valores nuevos directamente en `mushroom_profiles.json`. Primero debe actualizar este catálogo. Si detecta un texto libre o ID inexistente, debe reportarlo o proponer el alta en catálogo.
