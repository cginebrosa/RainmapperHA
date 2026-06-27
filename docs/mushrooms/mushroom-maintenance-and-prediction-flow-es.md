# Flujo de mantenimiento y uso del modelo de predicción de floradas

Versión del documento: borrador 0.1
Ficheros relacionados:

- `mushroom_profiles.json`
- `mushroom_reference_catalogs.json`
- `mushroom_gis_mappings.json`

Este documento describe cómo deben mantenerse los tres JSON y cómo deberían usarse en la futura aplicación de predicción de floradas sobre mapa.

## 1. Objetivo funcional

La funcionalidad pretende estimar, para una especie y una zona geográfica, la idoneidad o probabilidad relativa de florada usando:

- hábitat;
- vegetación/árboles;
- suelo/litología;
- altitud, orientación y pendiente;
- época del año;
- lluvia acumulada;
- temperatura;
- humedad;
- viento;
- observaciones locales futuras.

La salida debería ser explicable, por ejemplo:

```text
Boletus pinophilus — idoneidad alta
Motivos: pinar montano compatible, altitud adecuada, lluvia favorable en 15 días y viento seco bajo.
Confianza del modelo: media.
```

## 2. Separación de responsabilidades

### `mushroom_reference_catalogs.json`

Define qué valores existen. Es el vocabulario maestro.

### `mushroom_profiles.json`

Define qué necesita cada especie usando IDs del catálogo.

### `mushroom_gis_mappings.json`

Define cómo traducir datos GIS externos a IDs internos.

Esta separación es crítica para evitar texto libre y para que el motor sea mantenible.

## 2.1 Datos versionados y datos editables en HA

La arquitectura de mantenimiento debe separar los JSON empaquetados con la app de la copia viva editable en Home Assistant:

```text
mushroom-data/
  mushroom_profiles.json
  mushroom_reference_catalogs.json
  mushroom_gis_mappings.json

/share/rainmapper/mushroom-data/
  mushroom_profiles.json
  mushroom_reference_catalogs.json
  mushroom_gis_mappings.json
```

Los ficheros bajo `mushroom-data/` son defaults versionados y sirven para instalación inicial, tests y recuperación. En HA, la UI de administración debe editar la copia persistente bajo `/share/rainmapper/mushroom-data/`. En primer arranque o primera activación del módulo, si la copia persistente no existe, debe precargarse desde los defaults de la imagen. Si ya existe, no debe sobrescribirse durante actualizaciones de la app.

El futuro motor de predicción debe leer primero la copia persistente; si falta, puede usar los defaults versionados como fallback.

## 2.2 Importación, exportación y plantillas JSON

Las pantallas de mantenimiento de perfiles y catálogos deben prever acciones administrativas para:

- importar un JSON completo compatible con el modelo correspondiente;
- exportar el JSON actualmente persistido;
- exportar los defaults empaquetados con la app;
- exportar un JSON vacío/plantilla con la estructura mínima del modelo de datos.

Estas acciones no tienen por qué ser pestañas propias en la primera versión; pueden vivir como acciones de cabecera o menú avanzado dentro de `Mantenimiento de especies` y `Catálogo maestro`.

Reglas obligatorias:

1. Importar no debe modificar nada hasta pasar validación sintáctica, estructural y cruzada.
2. Antes de reemplazar un fichero persistente debe crearse backup con timestamp.
3. La escritura debe ser atómica: escribir temporal, validar, reemplazar.
4. La importación debe mostrar resumen de cambios antes de confirmar: especies/IDs añadidos, modificados, eliminados, errores y warnings.
5. La exportación de plantilla vacía debe preservar `schema_version`, `model_purpose`, `important_note`, estructura raíz y `metadata` mínima, pero dejar arrays principales vacíos.
6. La plantilla de `mushroom_profiles.json` debe incluir `species_profiles: []`.
7. La plantilla de `mushroom_reference_catalogs.json` debe incluir todos los grupos de `catalogs` existentes con arrays vacíos.
8. No sustituir IDs de catálogo por texto libre durante importación.
9. No aplicar cambios automáticos en perfiles al importar catálogos, ni cambios automáticos en catálogos al importar perfiles, salvo confirmación explícita en una fase futura.

## 2.3 Alcance de la primera fase

La primera fase de mantenimiento debe centrarse en:

- `mushroom_profiles.json`: edición de perfiles de especies, validación y exportación/importación.
- `mushroom_reference_catalogs.json`: edición del vocabulario maestro, validación y exportación/importación.

`mushroom_gis_mappings.json` debe mantenerse como fichero de datos versionado y validable, pero no requiere una UI completa de mantenimiento en esta fase. Las pantallas de perfiles y catálogos pueden usarlo para mostrar impacto, referencias existentes o errores cruzados, pero la edición de reglas GIS queda para una fase posterior.

## 3. Flujo para añadir una nueva especie

1. Crear `species_id` estable.
2. Revisar si todos los hosts, suelos, litologías, bosques y rasgos existen en `mushroom_reference_catalogs.json`.
3. Añadir al catálogo lo que falte.
4. Crear perfil en `mushroom_profiles.json`.
5. Usar afinidades, no listas planas de texto.
6. Definir fenología y topografía de forma conservadora.
7. Definir umbrales meteorológicos iniciales con `weather_threshold_confidence: low` salvo que estén muy contrastados.
8. Definir `scoring_weights` sumando aproximadamente 1.0.
9. Definir `prediction_confidence` y `metadata`.
10. Ejecutar validación cruzada.

## 4. Flujo para añadir un nuevo host/suelo/litología

1. Buscar si ya existe un ID equivalente.
2. Si existe, reutilizarlo.
3. Si no existe, crear entrada en el catálogo correcto.
4. Añadir nombres comunes y jerarquía si aplica.
5. Actualizar perfiles o mapeos que lo necesiten.
6. Ejecutar validación cruzada.

Nunca crear un ID dentro del perfil sin declararlo antes en el catálogo.

## 5. Flujo para añadir una capa GIS real

Este flujo describe el objetivo final. En la primera fase no se implementa una UI completa para editar `mushroom_gis_mappings.json`; estas reglas se mantienen por fichero y se validan para asegurar que apuntan a IDs internos existentes.

1. Identificar la fuente: WMS, WFS, GeoJSON, raster, PostGIS, etc.
2. Identificar campos disponibles: código, descripción, clase, especie dominante, litología, etc.
3. Crear o actualizar `mapping_sources`.
4. Crear reglas específicas en `vegetation_mappings`, `corine_land_cover_mappings` o `lithology_mappings`.
5. Usar códigos reales de la fuente si existen.
6. Mantener patrones de texto como fallback.
7. Asignar `confidence` a cada mapeo.
8. Ejecutar validación de IDs.
9. Probar con celdas reales del mapa.

## 6. Flujo de cálculo de predicción

Para cada celda y especie:

1. Obtener datos geográficos:
   - lat/lon;
   - altitud DEM;
   - orientación;
   - pendiente;
   - vegetación;
   - cobertura;
   - litología;
   - suelo si existe.
2. Obtener meteo agregada:
   - lluvia 3, 7, 15, 30 días;
   - temperatura mínima/media/máxima;
   - humedad mínima/máxima;
   - viento medio y rachas;
   - índice de viento seco.
3. Mapear GIS a IDs internos.
4. Cargar perfil de especie.
5. Calcular scores parciales.
6. Aplicar pesos.
7. Aplicar penalizaciones.
8. Ajustar con observaciones locales si existen.
9. Devolver score, nivel, confianza y explicación.

## 7. Scores parciales recomendados

### Habitat score

Combina:

- host score;
- forest type score;
- soil score;
- lithology score;
- habitat feature score.

### Season score

Compara fecha actual con:

- `main_months`;
- `secondary_months`;
- `season_pattern_ids`.

### Altitude score

Compara DEM con rangos óptimos.

### Rainfall score

Compara lluvia acumulada con umbrales de especie.

### Temperature score

Compara mínimas y máximas recientes con rangos óptimos.

### Humidity score

Usa humedad mínima y máxima recientes.

### Wind penalty

Penaliza viento seco fuerte después de lluvia. El viento no debe ser sólo una variable aislada; debe afectar a la conservación de humedad.

## 8. Índice de viento seco

Recomendación inicial:

```text
dry_wind_index = viento × sequedad × temperatura × persistencia
```

Factores:

- viento medio 3 días;
- racha máxima 3 días;
- humedad mínima;
- temperatura máxima;
- días consecutivos con viento/sequedad;
- proximidad temporal a una lluvia significativa.

Ejemplo de interpretación:

```text
Lluvia 15d buena + viento seco fuerte 3 días posteriores = penalización alta.
```

## 9. Salida recomendada para la UI

Ejemplo:

```json
{
  "species_id": "boletus_pinophilus",
  "cell_id": "grid_00123",
  "date": "2026-06-27",
  "score": 74,
  "suitability_level": "high",
  "model_confidence": "medium",
  "components": {
    "habitat": 0.86,
    "season": 0.75,
    "altitude": 0.92,
    "rainfall": 0.70,
    "temperature": 0.68,
    "humidity": 0.60,
    "wind_penalty": -0.08
  },
  "explanation": [
    "Hábitat compatible: pinar montano y suelo silíceo.",
    "Altitud dentro del rango óptimo.",
    "Lluvia reciente favorable.",
    "Penalización leve por viento seco."
  ]
}
```

## 10. Mantenimiento de observaciones locales

Para calibrar, la app debería registrar observaciones reales:

```text
fecha
species_id
zone_id/cell_id
found true/false
quantity_level
freshness
worm_damage_level
habitat_confirmed
tree_species_observed
soil_moisture_observed
notes
```

Las observaciones negativas son tan importantes como las positivas. Sin “fui y no encontré”, el modelo se sesga.

## 11. Calibración

Antes de calibrar una especie, respetar mínimos definidos en `prediction_confidence`:

- `minimum_observations_for_calibration`;
- `minimum_positive_observations`;
- `minimum_negative_observations`.

La calibración debería ajustar primero:

1. ventanas lluvia → florada;
2. pesos de lluvia/viento/humedad;
3. altitud óptima local;
4. afinidades de hábitat locales;
5. penalizaciones de calor y viento.

## 12. UI de mantenimiento recomendada

Pantallas sugeridas:

1. Resumen de especies.
2. Mantenimiento de perfil de especie.
3. Catálogos maestros.
4. Afinidades ecológicas.
5. Parámetros meteorológicos.
6. Mapeos GIS.
7. Validación y errores.
8. Observaciones locales.
9. Calibración.

## 13. Validación antes de usar en producción

Validar siempre:

- JSON correcto;
- campos obligatorios;
- IDs existentes;
- pesos coherentes;
- valores controlados;
- meses 1–12;
- rangos numéricos coherentes;
- ausencia de texto libre computable;
- mapeos GIS apuntando a IDs válidos.

## 14. Reglas para sesiones de Codex

Codex debe:

- leer los documentos antes de modificar;
- no cambiar estructura sin permiso;
- tratar JSON como datos, no como lógica hardcoded;
- preservar IDs estables;
- reportar inconsistencias antes de corregirlas automáticamente;
- añadir tests o validadores cuando sea posible;
- actualizar documentación si cambia el modelo.
