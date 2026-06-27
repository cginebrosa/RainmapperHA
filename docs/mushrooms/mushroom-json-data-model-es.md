# Modelo de datos JSON para predicción de floradas de setas

Versión del documento: borrador 0.1
Ficheros relacionados:

- `mushroom_profiles.json`
- `mushroom_reference_catalogs.json`
- `mushroom_gis_mappings.json`

Este documento explica el propósito de los tres ficheros JSON usados por el módulo de predicción de floradas de setas, cómo se relacionan entre ellos y cómo deben mantenerse durante el desarrollo.

El dataset actual es un modelo inicial asistido por investigación. Es útil para desarrollar la aplicación, pantallas de mantenimiento, validadores, prototipos de integración GIS y prototipos del motor de predicción. Todavía no debe considerarse un modelo científico calibrado localmente.

## 1. Objetivo general

Rainmapper ya dispone de datos meteorológicos diarios, acumulados por periodo, mapa y DEM. Estos tres JSON añaden la capa ecológica y semántica necesaria para estimar la idoneidad o probabilidad de florada por especie y zona geográfica.

El motor de predicción debería combinar:

1. Perfiles ecológicos de setas desde `mushroom_profiles.json`.
2. Valores de referencia controlados desde `mushroom_reference_catalogs.json`.
3. Reglas de traducción GIS desde `mushroom_gis_mappings.json`.
4. Datos existentes de la aplicación: lluvia, temperatura, humedad, viento, altitud DEM, orientación, pendiente y celda geográfica.
5. Observaciones locales futuras: encontrada/no encontrada, cantidad, frescura, agusanamiento y confirmación de hábitat.

Principio clave: los perfiles de setas no deben usar texto libre para valores ecológicos computables. Deben usar IDs controlados de catálogo. Las capas GIS también deben traducirse a esos mismos IDs. Esto hace que el motor sea determinista, mantenible y testeable.

Los valores controlados que no son vocabulario ecológico reutilizable, por ejemplo estados de revisión, niveles de confianza o prioridades de calibración, forman parte del contrato del modelo y del validador. No deben añadirse como un campo `controlled_values` dentro de `mushroom_profiles.json`: la UI debe obtenerlos desde backend, constantes compartidas o un futuro endpoint de metadatos del modelo.

## 2. Arquitectura de tres ficheros

```text
mushroom_reference_catalogs.json
    Define el vocabulario controlado: modos tróficos, taxones hospedadores,
    tipos de bosque, suelos, litologías, orientaciones, patrones de temporada
    y rasgos de hábitat.

mushroom_profiles.json
    Define cada perfil de seta usando IDs del catálogo maestro.
    Además guarda fenología, altitud, umbrales meteorológicos, pesos de scoring,
    confianza y metadatos de calibración.

mushroom_gis_mappings.json
    Define reglas iniciales para traducir etiquetas o patrones de capas GIS
    externas a IDs internos. Es el puente entre WMS/WFS/CORINE/geología/
    vegetación y los perfiles de setas.
```

La dependencia debe ir en esta dirección:

```text
mushroom_reference_catalogs.json
        ↑
        │ referenciado por IDs
        │
mushroom_profiles.json       mushroom_gis_mappings.json
        │                              │
        └──────────────┬───────────────┘
                       ↓
              motor de predicción
```

`mushroom_reference_catalogs.json` es el vocabulario maestro. Los otros dos ficheros sólo deben referenciar IDs que existan en él.

## 3. Especies incluidas actualmente

El fichero `mushroom_profiles.json` contiene 11 perfiles operativos:

- `boletus_pinophilus` — *Boletus pinophilus*
- `boletus_edulis` — *Boletus edulis*
- `boletus_aereus` — *Boletus aereus*
- `amanita_caesarea` — *Amanita caesarea*
- `lactarius_sanguifluus` — *Lactarius sanguifluus*
- `lactarius_vinosus` — *Lactarius vinosus*
- `hygrophorus_marzuolus` — *Hygrophorus marzuolus*
- `morchella_elata_complex` — complejo *Morchella elata*
- `calocybe_gambosa` — *Calocybe gambosa*
- `hygrophorus_latitabundus` — *Hygrophorus latitabundus*
- `cantharellus_cibarius_sl` — *Cantharellus cibarius sensu lato*

## 4. Cobertura actual de catálogos

`mushroom_reference_catalogs.json` contiene estos grupos de catálogo:

- `trophic_modes`: 4 entradas
- `host_taxa`: 26 entradas
- `forest_types`: 18 entradas
- `soil_types`: 17 entradas
- `lithology_types`: 13 entradas
- `aspects`: 10 entradas
- `season_patterns`: 17 entradas
- `habitat_features`: 9 entradas

## 5. Cómo trabajan juntos en una predicción

Para una celda del mapa y una especie seleccionada:

1. La aplicación carga el perfil de especie desde `mushroom_profiles.json`.
2. La aplicación obtiene valores ambientales de la celda:
   - clase de vegetación o árbol dominante;
   - tipo de bosque/hábitat;
   - litología/geología;
   - tendencia del suelo, si está disponible o se puede derivar;
   - altitud DEM;
   - orientación y pendiente;
   - lluvia, temperatura, humedad y viento recientes.
3. La aplicación usa `mushroom_gis_mappings.json` para convertir clases GIS crudas en IDs internos.
4. La aplicación resuelve esos IDs contra `mushroom_reference_catalogs.json`.
5. El motor compara los IDs de la celda con las afinidades de la especie en `mushroom_profiles.json`.
6. El motor calcula puntuaciones parciales:
   - hábitat;
   - hospedador/árbol;
   - tipo de bosque;
   - suelo;
   - litología;
   - rasgos de hábitat;
   - temporada;
   - altitud;
   - meteorología;
   - penalización por viento seco;
   - ajuste opcional por observaciones locales.
7. El motor combina esas puntuaciones usando `scoring_weights`.
8. La aplicación muestra un nivel de idoneidad/probabilidad junto con la confianza del modelo.

No debe presentarse el resultado como una garantía absoluta. Formulación recomendada:

```text
Idoneidad de florada: alta
Confianza del modelo: media
Motivo: hábitat compatible, altitud adecuada, lluvia reciente y sin penalización fuerte por viento seco.
```

## 6. Diferencia entre score y confianza

El score y la confianza son conceptos distintos.

- **Score**: idoneidad o probabilidad calculada para una especie en una celda y fecha concretas.
- **Confianza**: fiabilidad del perfil y de sus umbrales antes de calibración local.

Una celda puede tener score alto pero confianza baja si la especie es difícil de modelar, si se trata de un complejo taxonómico o si faltan observaciones locales.

Ejemplo:

```json
{
  "species_id": "morchella_elata_complex",
  "score": 78,
  "suitability_level": "high",
  "model_confidence": "low"
}
```

Esto significa que la zona encaja con las condiciones conocidas, pero el resultado debe mostrarse con cautela.

## 7. Ubicación recomendada en el repositorio

```text
mushroom-data/mushroom_profiles.json
mushroom-data/mushroom_reference_catalogs.json
mushroom-data/mushroom_gis_mappings.json

docs/mushrooms/mushroom-json-data-model-es.md
docs/mushrooms/mushroom-profiles-reference-es.md
docs/mushrooms/mushroom-reference-catalogs-reference-es.md
docs/mushrooms/mushroom-gis-mappings-reference-es.md
docs/mushrooms/mushroom-maintenance-and-prediction-flow-es.md
docs/mushrooms/codex-prompts-mushroom-es.md
```

En Home Assistant, estos ficheros deben tratarse como defaults empaquetados. La UI de administración debe mantener una copia persistente editable:

```text
/share/rainmapper/mushroom-data/mushroom_profiles.json
/share/rainmapper/mushroom-data/mushroom_reference_catalogs.json
/share/rainmapper/mushroom-data/mushroom_gis_mappings.json
```

Regla operativa:

- si la copia persistente no existe, se precarga desde `mushroom-data/`;
- si ya existe, una actualización de la app no debe sobrescribirla;
- el motor de predicción debe leer primero la copia persistente y usar los defaults versionados sólo como fallback;
- las pantallas de mantenimiento deben editar la copia persistente.

Las pantallas de mantenimiento de perfiles y catálogos deben ofrecer importación/exportación JSON y exportación de plantilla vacía del modelo. Estas acciones deben validar antes de guardar, crear backup del fichero persistente actual y escribir de forma atómica.

En la primera fase, la UI de mantenimiento cubre perfiles y catálogos. `mushroom_gis_mappings.json` sigue siendo necesario para validación cruzada, impacto y futuro motor de predicción, pero su mantenimiento visual completo queda pospuesto.

## 8. Regla de desarrollo para sesiones de Codex

Cuando se modifiquen estos ficheros, Codex debe seguir este orden:

1. Añadir o actualizar primero IDs en `mushroom_reference_catalogs.json`.
2. Actualizar perfiles de especies en `mushroom_profiles.json` usando sólo IDs de catálogo.
3. Actualizar mapeos GIS en `mushroom_gis_mappings.json` para traducir etiquetas/códigos de capas externas a IDs internos.
4. Ejecutar validación cruzada.
5. Actualizar documentación si cambia la estructura.

No introducir texto libre ecológico directamente en perfiles salvo notas humanas. Cualquier valor ecológico que use el motor debe ser un ID de catálogo.

## 9. Reglas de validación cruzada

Un validador debería comprobar como mínimo:

- `ecology.trophic_mode_id` existe en `catalogs.trophic_modes`.
- `host_affinities[].id` existe en `catalogs.host_taxa`.
- `forest_type_affinities[].id` existe en `catalogs.forest_types`.
- `soil_affinities[].id` existe en `catalogs.soil_types`.
- `lithology_affinities[].id` existe en `catalogs.lithology_types`.
- `habitat_feature_affinities[].id` existe en `catalogs.habitat_features`.
- `phenology.season_pattern_ids[]` existe en `catalogs.season_patterns`.
- `topography.preferred_aspect_ids[]` existe en `catalogs.aspects`.
- Todo ID emitido por `mushroom_gis_mappings.json` existe en `mushroom_reference_catalogs.json`.
- `scoring_weights` debe sumar aproximadamente 1.0, salvo pesos especiales documentados.
- Cada afinidad debe ser numérica, normalmente entre -1.0 y 1.0.
- Relaciones de evitación deben usar afinidades negativas.
- Relaciones preferidas/secundarias deben usar afinidades positivas.

## 10. Versionado

Usar versiones de esquema de forma conservadora:

- Actualización de datos: cambian valores, no cambia estructura.
- Actualización menor: se añaden campos opcionales. Ejemplo: `schema_version` 0.2 → 0.3.
- Cambio mayor: se rompe estructura. Ejemplo: 0.x → 1.0 cuando sea estable.

Cada especie tiene `metadata.profile_version`. El fichero también tiene `schema_version` a nivel raíz.

## 11. Filosofía de mantenimiento

Los ficheros deben ser conservadores, explicables y no sobreajustados. Los umbrales meteorológicos son parámetros iniciales de modelado y deben calibrarse con observaciones locales.

Evolución recomendada:

1. Esquema estable.
2. Buena normalización de catálogos.
3. Mapeos GIS fiables.
4. Scoring simple y explicable.
5. Captura de observaciones.
6. Calibración local.
7. Modelos más avanzados sólo cuando haya datos suficientes.
