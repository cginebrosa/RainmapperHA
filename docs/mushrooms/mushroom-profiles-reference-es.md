# Referencia de `mushroom_profiles.json`

Versión del documento: borrador 0.1
Fichero descrito: `mushroom_profiles.json`

Este fichero define los perfiles ecológicos y predictivos de cada especie o grupo operativo de setas. Es el fichero principal que utilizará el motor de predicción para calcular la idoneidad de florada por especie.

## 1. Responsabilidad del fichero

`mushroom_profiles.json` responde a la pregunta:

```text
¿Qué condiciones necesita cada seta para tener probabilidad de florada?
```

Contiene:

- identificación de la especie;
- modo trófico;
- afinidades con árboles/hospedadores;
- afinidades con tipos de bosque/hábitat;
- preferencias de suelo;
- preferencias de litología;
- rasgos de hábitat;
- época de fructificación;
- altitud y orientación;
- umbrales meteorológicos iniciales;
- pesos de scoring;
- confianza y prioridad de calibración.

No debe contener texto libre para valores ecológicos computables. Debe usar IDs definidos en `mushroom_reference_catalogs.json`.

## 2. Estructura raíz

Campos principales:

```json
{
  "schema_version": "0.3",
  "model_purpose": "mushroom_fruiting_probability_scoring",
  "important_note": "...",
  "requires_catalog_file": "mushroom_reference_catalogs.json",
  "species_profiles": [],
  "metadata": {}
}
```

### `schema_version`

Versión del esquema del fichero. Si sólo cambian valores de especies, no debería cambiar. Si se añaden campos estructurales, incrementar versión.

### `requires_catalog_file`

Indica que este fichero depende de `mushroom_reference_catalogs.json`. El validador debe cargar ambos.

### `species_profiles`

Array de perfiles. Cada entrada representa una especie aceptada, una especie operativa o un complejo taxonómico operativo.

## 3. Identificación de especie

Campos típicos:

```json
{
  "species_id": "boletus_edulis",
  "scientific_name": "Boletus edulis",
  "common_names": ["cep", "porcini", "boleto comestible"],
  "taxonomy_status": "accepted",
  "edibility": "excellent"
}
```

### `species_id`

ID estable interno de la especie. No cambiarlo sin migración porque será usado por observaciones, resultados históricos, UI y capas calculadas.

### `taxonomy_status`

Indica cómo se trata taxonómicamente:

- `accepted`: especie aceptada.
- `uncertain_operational_taxon`: taxón operativo con incertidumbre.
- `species_complex_operational`: complejo de especies tratado como unidad práctica.

Ejemplos:

- `lactarius_vinosus`: taxón operativo incierto.
- `morchella_elata_complex`: complejo operativo.
- `cantharellus_cibarius_sl`: sensu lato.

## 4. Bloque `ecology`

Define relaciones ecológicas usando IDs y afinidades.

```json
"ecology": {
  "trophic_mode_id": "trophic_ectomycorrhizal",
  "host_affinities": [],
  "forest_type_affinities": [],
  "soil_affinities": [],
  "lithology_affinities": [],
  "habitat_feature_affinities": []
}
```

### `trophic_mode_id`

Debe existir en `catalogs.trophic_modes`.

Ejemplos:

- `trophic_ectomycorrhizal`
- `trophic_saprotrophic`
- `trophic_saprotrophic_or_facultative_complex`
- `trophic_saprotrophic_or_plant_associated_grassland`

### Afinidades

Cada array de afinidades usa objetos con este patrón:

```json
{
  "id": "host_pinus_sylvestris",
  "role": "primary",
  "affinity": 1.0
}
```

El significado general de `affinity` es:

- `1.0`: relación muy favorable o casi óptima.
- `0.7`–`0.9`: relación favorable.
- `0.3`–`0.6`: relación secundaria o posible.
- `0.0`: neutral o no informativa.
- valor negativo: penalización o evitación.

### `host_affinities`

IDs de `catalogs.host_taxa`. Representa árboles, géneros o grupos hospedadores.

Para especies ectomicorrícicas este bloque es crítico. Para especies de prado o saprófitas puede estar vacío.

### `forest_type_affinities`

IDs de `catalogs.forest_types`. Representa tipos de bosque o hábitats vegetales.

### `soil_affinities`

IDs de `catalogs.soil_types`. Representa preferencias o evitaciones edáficas.

Ejemplo conceptual:

```json
{
  "id": "soil_calcareous",
  "relationship": "preferred",
  "affinity": 0.95
}
```

### `lithology_affinities`

IDs de `catalogs.lithology_types`. Sirve para cruzar con mapas geológicos/litológicos.

La litología no es exactamente lo mismo que el suelo, pero puede ayudar a inferir tendencia ácida, silícea o caliza.

### `habitat_feature_affinities`

IDs de `catalogs.habitat_features`. Incluye rasgos como:

- musgo;
- hojarasca;
- ribera;
- claro de bosque;
- quemado reciente;
- prado;
- corros de bruja;
- nieve/deshielo.

## 5. Bloque `phenology`

Define época de fructificación.

```json
"phenology": {
  "main_months": [8, 9, 10, 11],
  "secondary_months": [6, 7],
  "season_pattern_ids": ["season_autumn_main"],
  "fruiting_delay_after_rain_days": {
    "min": 6,
    "optimal_min": 8,
    "optimal_max": 16,
    "max": 24
  }
}
```

### `main_months`

Meses principales de fructificación. Deben ser enteros 1–12.

### `secondary_months`

Meses posibles, pero menos frecuentes o dependientes de condiciones locales.

### `season_pattern_ids`

Debe referenciar `catalogs.season_patterns`.

### `fruiting_delay_after_rain_days`

Retraso estimado entre lluvia significativa y aparición visible. Es una aproximación inicial. Debe calibrarse localmente.

## 6. Bloque `topography`

Define altitud y orientación.

```json
"topography": {
  "altitude_min_m": 600,
  "altitude_optimal_min_m": 900,
  "altitude_optimal_max_m": 1800,
  "altitude_max_m": 2200,
  "preferred_aspect_ids": ["aspect_N", "aspect_NE"],
  "aspect_notes": "..."
}
```

### Altitudes

Usar DEM para comparar la altitud de la celda con estos rangos:

- fuera de `altitude_min_m` / `altitude_max_m`: puntuación baja o cero;
- dentro del rango óptimo: puntuación alta;
- entre mínimo y óptimo: transición gradual.

### `preferred_aspect_ids`

IDs de `catalogs.aspects`. Las orientaciones frescas suelen ser importantes para especies sensibles a sequedad.

## 7. Bloque `weather_model`

Define parámetros meteorológicos iniciales.

Contiene subbloques:

- `rainfall`
- `temperature`
- `humidity`
- `wind`

Los valores son umbrales iniciales de modelado, no verdades absolutas. Deben calibrarse con observaciones.

### Lluvia

Campos habituales:

```json
"rainfall": {
  "rain_7d_min_mm": 10,
  "rain_15d_min_mm": 25,
  "rain_15d_optimal_min_mm": 40,
  "rain_15d_optimal_max_mm": 100,
  "rain_30d_saturation_penalty_mm": 170
}
```

### Temperatura

Se utilizan mínimas y máximas medias de 7 días.

```json
"temperature": {
  "temp_min_7d_optimal_min_c": 5,
  "temp_min_7d_optimal_max_c": 14,
  "temp_max_7d_optimal_min_c": 13,
  "temp_max_7d_optimal_max_c": 23,
  "heat_penalty_temp_max_c": 27,
  "frost_penalty_temp_min_c": -1
}
```

### Humedad

La humedad mínima es muy importante porque indica desecación diurna.

### Viento

```json
"wind": {
  "wind_avg_3d_penalty_kmh": 16,
  "wind_gust_3d_penalty_kmh": 38,
  "dry_wind_sensitive": true
}
```

El viento debería usarse sobre todo como penalización de conservación de humedad después de lluvia.

## 8. Bloque `scoring_weights`

Define cómo combinar scores parciales.

Ejemplo:

```json
"scoring_weights": {
  "habitat": 0.28,
  "season": 0.15,
  "altitude": 0.12,
  "rainfall": 0.23,
  "temperature": 0.12,
  "humidity": 0.05,
  "wind_penalty": 0.05
}
```

El validador debe comprobar que la suma sea aproximadamente 1.0, salvo que haya pesos especiales documentados.

## 9. Bloque `prediction_confidence`

No calcula probabilidad. Indica fiabilidad del perfil.

```json
"prediction_confidence": {
  "overall_confidence": "medium",
  "habitat_confidence": "high",
  "topography_confidence": "medium",
  "phenology_confidence": "medium",
  "weather_threshold_confidence": "low",
  "taxonomy_confidence": "high",
  "local_calibration_status": "not_calibrated",
  "calibration_priority": "high",
  "minimum_observations_for_calibration": 20,
  "minimum_positive_observations": 8,
  "minimum_negative_observations": 12,
  "notes": "..."
}
```

Valores controlados:

- confianza: `low`, `medium`, `high`;
- calibración local: `not_calibrated`, `partially_calibrated`, `locally_calibrated`, `needs_review`;
- prioridad: `low`, `medium`, `high`, `very_high`.

## 10. Bloque `metadata`

Metadatos de mantenimiento:

```json
"metadata": {
  "profile_version": "0.2",
  "created_at": "2026-06-24",
  "updated_at": "2026-06-24",
  "created_by": "chatgpt_research_assisted",
  "review_status": "draft",
  "reviewed_by": null,
  "source_quality": "mixed",
  "requires_human_validation": true
}
```

Valores controlados para `review_status`:

- `draft`;
- `needs_review`;
- `reviewed`;
- `validated`;
- `deprecated`.

## 11. Reglas de mantenimiento

Al añadir o modificar una especie:

1. No inventar IDs dentro del perfil.
2. Crear primero los IDs necesarios en `mushroom_reference_catalogs.json`.
3. Usar afinidades en lugar de listas planas de texto.
4. Documentar incertidumbre en `prediction_confidence.notes`.
5. Mantener `species_id` estable.
6. Ejecutar validación cruzada antes de usar en producción.
