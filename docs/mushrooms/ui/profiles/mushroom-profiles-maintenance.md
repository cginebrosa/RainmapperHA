# Diseño del mantenimiento de especies para el predictor de floradas

## Objetivo

Desarrollar una nueva pantalla de mantenimiento para `mushroom_profiles.json`, que será la base del futuro predictor de floradas de setas de Rainmapper.

El mantenimiento debe permitir consultar, editar, validar y preparar para calibración los perfiles de especies definidos en el JSON.

El diseño visual debe ser coherente con el resto de interfaces rediseñadas en Rainmapper:

- Dark mode.
- Estilo SaaS/admin moderno.
- Sidebar izquierda.
- Header superior compacto.
- Cards con bordes sutiles.
- Acento azul/cyan.
- Chips de estado.
- Layout denso pero legible.
- Tablas compactas.
- Formularios agrupados por dominio funcional.
- Evitar pantallas muy largas sin estructura.

El fichero de datos base es:

mushroom-data/mushroom_profiles.json

Imágenes/prototipos de referencia sugeridos:

docs/mushrooms/ui/profiles/mushroom-profiles-summary.png
docs/mushrooms/ui/profiles/mushroom-profiles-species.png
docs/mushrooms/ui/profiles/mushroom-profiles-observations.png
docs/mushrooms/ui/profiles/mushroom-profiles-parameters.png
docs/mushrooms/ui/profiles/mushroom-profiles-calibration.png

El modelo actual contiene:

- `schema_version`
- `model_purpose`
- `important_note`
- `requires_catalog_file`
- `species_profiles[]`
- `metadata`

Cada `species_profile` contiene:

- `species_id`
- `scientific_name`
- `common_names`
- `taxonomy_status`
- `edibility`
- `ecology`
- `phenology`
- `topography`
- `weather_model`
- `scoring_weights`
- `prediction_confidence`
- `metadata`

Debes considerar a mushroom-data/mushroom_profiles.json como el modelo de datos actualmente valido, y que pueden haber habido modificaciones al modelo de datos desde que se escribió esta especificacion. Si encuentras diferencias, adapta lo que dice esta especificacion a la realidad actual del modelo de atos.

Este modelo de datos fue definido y la UI debe respetarlo. No debes inventar campos nuevos como obligatorios salvo que se definan claramente como UI-only o futuros.

---

## Estructura general de la pantalla

La sección se llamará:

```text
Mantenimiento de especies
```

Subtítulo:

```text
Gestiona perfiles de especies para el predictor de floradas
```

### Layout global

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar Rainmapper                                           │
├──────────────────────────────────────────────────────────────┤
│ Header                                                       │
│ Mantenimiento de especies                                    │
│ Buscar especie o campo...       [Actualizar] [Nueva especie] │
├──────────────────────────────────────────────────────────────┤
│ Tabs                                                         │
│ Resumen | Especies | Observaciones | Parámetros | Calibración│
├──────────────────────────────────────────────────────────────┤
│ Contenido de la pestaña activa                               │
└──────────────────────────────────────────────────────────────┘
```

### Navegación lateral

Debe seguir el estilo visual de Rainmapper.

Items sugeridos:

```text
Panel
Mapas
Datos
Estaciones
Alertas
Tareas
Meteocat
AEMET
Wunderground
Logs
Usuarios
Especies
Ajustes
```

La opción activa será:

```text
Especies
```

---

## Tabs necesarias

La pantalla tendrá estas pestañas:

1. `Resumen`
2. `Especies`
3. `Observaciones`
4. `Parámetros`
5. `Calibración`

No incluir por ahora como pestañas propias:

- Ajustes.

La importación/exportación sí debe preverse como acción administrativa avanzada en la cabecera o en un menú de herramientas. No debe ocupar una pestaña propia en la primera versión.

---

# 1. Pantalla Resumen

## Objetivo

Dar una visión rápida del estado global del modelo de especies.

Debe mostrar indicadores agregados calculados a partir de `species_profiles`.

## Métricas principales

Cards superiores:

```text
Total especies
Taxones aceptados
Taxones operativos / complejos
Sin calibrar
Borrador
Alta / muy alta prioridad
Validación humana requerida
```

Ejemplo con el JSON actual:

```text
Total especies: 11
Taxones aceptados: 8
Taxones operativos / complejos: 3
Sin calibrar: 11
Borrador: 11
Alta / muy alta prioridad: 9
Validación humana requerida: 11
```

## Chips resumen

Debajo de las cards, mostrar chips agregados:

```text
Confianza global:
- medium: 9
- low: 2

Estado calibración:
- not_calibrated: 11

review_status:
- draft: 11

requires_human_validation:
- true: 11

Prioridad calibración:
- high: 7
- medium: 2
- very_high: 2
```

## Secciones principales

### 1. Estado de calibración

Mostrar gráfico donut o card visual:

```text
not_calibrated: 11
partially_calibrated: 0
locally_calibrated: 0
needs_review: 0
```

Debe usar valores controlados del contrato del modelo. En la fase actual estos valores no viven en un campo `controlled_values` dentro del JSON; deben exponerse desde backend/validador o constantes de modelo compartidas:

```text
not_calibrated
partially_calibrated
locally_calibrated
needs_review
```

### 2. Prioridad de calibración

Mostrar barras por prioridad:

```text
very_high
high
medium
low
```

Debe usar:

```text
prediction_confidence.calibration_priority
```

### 3. Especies que requieren atención inmediata

Tabla compacta con especies prioritarias.

Criterio recomendado:

- `calibration_priority = very_high`
- o `overall_confidence = low`
- o `taxonomy_status` distinto de `accepted`
- o `requires_human_validation = true`

Columnas:

```text
Especie | Nombre común | Prioridad | Confianza | Motivo
```

Ejemplo:

```text
Lactarius vinosus | Níscalo vinoso | very_high | low | Taxonomía incierta
Morchella elata complex | Colmenilla alta | very_high | low | Complejo operativo
Lactarius sanguifluus | Níscalo sangrante | high | medium | Calibración pendiente
```

### 4. Revisión taxonómica especial

Mostrar especies con:

```text
taxonomy_status != accepted
```

Columnas:

```text
Taxón | taxonomy_status | Motivo
```

### 5. Últimas especies actualizadas

Tabla compacta:

```text
Especie | updated_at | created_by | review_status
```

### 6. Próximas acciones

Card lateral o inferior con acciones recomendadas:

```text
Cargar observaciones reales
Calibrar taxones prioritarios
Revisar perfiles draft
Validar con expertos
```

Estas acciones pueden ser botones o enlaces internos a las tabs correspondientes.

---

# 2. Pantalla Especies

## Objetivo

Permitir seleccionar una especie y mantener su perfil completo.

Esta pantalla es el mantenimiento principal de `species_profiles[]`.

Debe mostrar:

- Lista lateral de especies.
- Panel principal de edición.
- Subtabs internas por dominio del perfil.

## Layout

```text
┌───────────────────────┬──────────────────────────────────────┐
│ Lista de especies     │ Detalle de especie                   │
│ Buscar especie...     │ Header especie + subtabs             │
│                       │                                      │
│ Boletus pinophilus    │ General | Ecología | Fenología       │
│ Boletus edulis        │ Modelo meteorológico | Scoring       │
│ ...                   │ Confianza | Metadata                 │
└───────────────────────┴──────────────────────────────────────┘
```

## Lista lateral de especies

Cada fila debe mostrar:

```text
Icono seta
scientific_name
primer common_name
overall_confidence
calibration_priority
review_status
```

Ejemplo:

```text
Boletus pinophilus
Boleto de pino
[medium] [high] [draft]
```

Debe permitir:

- Buscar por `scientific_name`.
- Buscar por `species_id`.
- Buscar por `common_names`.
- Filtrar por:
  - `taxonomy_status`
  - `edibility`
  - `overall_confidence`
  - `calibration_priority`
  - `review_status`
  - `local_calibration_status`

## Header de especie

Al seleccionar una especie, mostrar:

```text
Boletus pinophilus
Boleto de pino
species_id: boletus_pinophilus

Taxonomía: accepted
Comestibilidad: excellent
Confianza global: medium
Calibración local: not_calibrated
Revisión: draft
```

## Subtabs internas de especie

Dentro de la pantalla `Especies`, usar subtabs:

1. `General`
2. `Ecología`
3. `Fenología`
4. `Modelo meteorológico`
5. `Scoring`
6. `Confianza`
7. `Metadata`

---

## 2.1 Subtab General

Campos:

```text
species_id
scientific_name
common_names[]
taxonomy_status
edibility
```

### species_id

- Campo texto.
- Debe ser único.
- Recomendado bloquear edición si ya existen observaciones asociadas en el futuro.

### scientific_name

- Campo texto.

### common_names

- Editor tipo chips.
- Permitir añadir/eliminar nombres comunes.

### taxonomy_status

Select.

Valores actuales detectados en JSON:

```text
accepted
species_complex_operational
uncertain_operational_taxon
```

Debe aceptar nuevos valores si el JSON futuro los incluye o si se añaden a controlled values.

### edibility

Select.

Valores actuales detectados:

```text
excellent
good
edible_when_thoroughly_cooked
```

---

## 2.2 Subtab Ecología

Debe editar:

```text
ecology
```

Campos:

```text
ecology.trophic_mode_id
ecology.host_affinities[]
ecology.forest_type_affinities[]
ecology.soil_affinities[]
ecology.lithology_affinities[]
ecology.habitat_feature_affinities[]
```

Diseño recomendado con cards:

```text
1. Relación ecológica
- trophic_mode_id

2. Hospedadores
- host_affinities

3. Tipos de bosque / hábitat
- forest_type_affinities

4. Suelos
- soil_affinities

5. Litología
- lithology_affinities

6. Rasgos de hábitat
- habitat_feature_affinities
```

Los arrays de afinidades deben editarse como filas o chips enriquecidos con `id`, `relationship` y `affinity`.

Ejemplo:

```text
host_affinities:
[Pinus sylvestris · primary · 1.00] [Pinus uncinata · primary · 0.95] [+]
```

---

## 2.3 Subtab Fenología

Debe editar:

```text
phenology
```

Campos:

```text
main_months[]
secondary_months[]
season_pattern_ids[]
fruiting_delay_after_rain_days.min
fruiting_delay_after_rain_days.optimal_min
fruiting_delay_after_rain_days.optimal_max
fruiting_delay_after_rain_days.max
```

Diseño:

### Meses principales

Selector de meses tipo chips:

```text
Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic
```

Los meses activos de `main_months` deben resaltarse en azul.

### Meses secundarios

Mismo selector, pero con color secundario o menos intenso.

### Patrón de temporada

Editor de chips:

```text
late_spring_possible
summer
autumn
```

### Delay tras lluvia

Card compacta:

```text
Mínimo | Óptimo min | Óptimo max | Máximo
```

Ejemplo:

```text
5 | 7 | 15 | 21 días
```

---

## 2.4 Subtab Modelo meteorológico

Debe editar:

```text
weather_model
```

Esta pantalla debe mostrar todos los parámetros climáticos de la especie seleccionada.

Es imprescindible que se vea claramente la especie seleccionada.

Header obligatorio:

```text
Especie seleccionada: Boletus pinophilus
species_id: boletus_pinophilus
```

Bloques:

### Lluvia

Campos:

```text
weather_model.rainfall.rain_7d_min_mm
weather_model.rainfall.rain_15d_min_mm
weather_model.rainfall.rain_15d_optimal_min_mm
weather_model.rainfall.rain_15d_optimal_max_mm
weather_model.rainfall.rain_30d_saturation_penalty_mm
weather_model.rainfall.snowmelt_bonus
```

Notas:

- `snowmelt_bonus` sólo aparece en algunas especies.
- La UI debe soportar campos opcionales.
- Si no existe, no mostrarlo o mostrarlo como opcional desactivado.

### Temperatura

Campos:

```text
weather_model.temperature.temp_min_7d_optimal_min_c
weather_model.temperature.temp_min_7d_optimal_max_c
weather_model.temperature.temp_max_7d_optimal_min_c
weather_model.temperature.temp_max_7d_optimal_max_c
weather_model.temperature.heat_penalty_temp_max_c
weather_model.temperature.frost_penalty_temp_min_c
```

### Humedad

Campos:

```text
weather_model.humidity.humidity_min_7d_preferred_min_pct
weather_model.humidity.humidity_max_7d_preferred_min_pct
```

### Viento

Campos:

```text
weather_model.wind.wind_avg_3d_penalty_kmh
weather_model.wind.wind_gust_3d_penalty_kmh
weather_model.wind.dry_wind_sensitive
```

Diseño recomendado:

```text
┌─────────────────────┐ ┌─────────────────────┐
│ Lluvia              │ │ Temperatura         │
├─────────────────────┤ ├─────────────────────┤
│ rain_7d_min_mm      │ │ temp_min_7d...      │
│ rain_15d_min_mm     │ │ temp_max_7d...      │
│ ...                 │ │ heat_penalty...     │
└─────────────────────┘ └─────────────────────┘

┌─────────────────────┐ ┌─────────────────────┐
│ Humedad             │ │ Viento              │
└─────────────────────┘ └─────────────────────┘
```

---

## 2.5 Subtab Scoring

Debe editar:

```text
scoring_weights
```

Campos actuales:

```text
habitat
season
altitude
rainfall
temperature
humidity
wind_penalty
snowmelt_or_soil_moisture
```

Notas:

- `snowmelt_or_soil_moisture` sólo aparece en algunas especies.
- La UI debe soportar pesos opcionales.
- No asumir que todas las especies tienen exactamente las mismas claves.

Diseño:

- Barras horizontales con input numérico.
- Mostrar suma total de pesos.
- Avisar si la suma no es aproximadamente 1.00.

Ejemplo:

```text
Habitat       [======      ] 0.30
Season        [===         ] 0.15
Altitude      [===         ] 0.15
Rainfall      [====        ] 0.20
Temperature   [==          ] 0.10
Humidity      [=           ] 0.05
Wind penalty  [=           ] 0.05

Total: 1.00 OK
```

Acciones:

```text
Normalizar pesos
Restablecer
Guardar cambios
```

---

## 2.6 Subtab Confianza

Debe editar:

```text
prediction_confidence
```

Campos:

```text
overall_confidence
habitat_confidence
topography_confidence
phenology_confidence
weather_threshold_confidence
taxonomy_confidence
local_calibration_status
calibration_priority
minimum_observations_for_calibration
minimum_positive_observations
minimum_negative_observations
notes
```

Valores controlados:

```text
confidence_values:
- low
- medium
- high

local_calibration_status:
- not_calibrated
- partially_calibrated
- locally_calibrated
- needs_review

calibration_priority:
- low
- medium
- high
- very_high
```

Diseño recomendado:

```text
1. Perfil de confianza
- overall_confidence
- habitat_confidence
- topography_confidence
- phenology_confidence
- weather_threshold_confidence
- taxonomy_confidence

2. Requisitos de calibración
- local_calibration_status
- calibration_priority
- minimum_observations_for_calibration
- minimum_positive_observations
- minimum_negative_observations

3. Notas
- notes
```

---

## 2.7 Subtab Metadata

Debe editar:

```text
metadata
```

Campos:

```text
profile_version
created_at
updated_at
created_by
review_status
reviewed_by
source_quality
requires_human_validation
```

Valores controlados:

```text
review_status:
- draft
- needs_review
- reviewed
- validated
- deprecated
```

Diseño:

```text
Version
Created at
Updated at
Created by
Review status
Reviewed by
Source quality
Requires human validation
```

Notas:

- `created_at` y `created_by` pueden ser read-only.
- `updated_at` puede actualizarse automáticamente al guardar.
- `review_status` debe ser editable.
- `requires_human_validation` debe ser boolean/switch.

---

## Acciones globales de la pantalla Especies

Botones inferiores o header:

```text
Guardar cambios
Duplicar especie
Validar perfil
Eliminar
Importar JSON
Exportar JSON
Exportar plantilla vacía
```

Requisitos:

- `Eliminar` debe pedir confirmación.
- `Duplicar especie` debe generar nuevo `species_id`.
- `Validar perfil` debe comprobar mínimos:
  - species_id no vacío
  - scientific_name no vacío
  - scoring_weights suma razonable
  - confidence/calibration válidos
  - weather_model completo según la especie
  - metadata.review_status coherente

## Importación/exportación JSON

Estas acciones trabajan sobre `mushroom_profiles.json`.

### Exportar JSON

Debe exportar el fichero persistente actual usado por HA, no necesariamente los defaults empaquetados. Si se ofrece exportar defaults, debe aparecer como acción separada:

```text
Exportar JSON actual
Exportar defaults empaquetados
```

### Exportar plantilla vacía

Debe generar un JSON válido con la estructura raíz del modelo, sin especies:

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

La plantilla debe mantener los campos raíz reales del modelo, pero no debe incluir perfiles de ejemplo salvo que se añada una opción explícita de "exportar ejemplo".

### Importar JSON

Flujo obligatorio:

1. Seleccionar fichero JSON.
2. Validar sintaxis.
3. Validar estructura raíz y perfiles.
4. Validar referencias contra `mushroom_reference_catalogs.json`.
5. Mostrar resumen de diferencias: especies añadidas, modificadas, eliminadas, errores y warnings.
6. Pedir confirmación fuerte si se eliminan especies o cambian `species_id`.
7. Crear backup del JSON persistente actual.
8. Guardar con escritura atómica.
9. Ejecutar validación final.

No debe modificar `mushroom_reference_catalogs.json` automáticamente. Si el JSON importado referencia IDs inexistentes, mostrar errores y proponer crear primero esos IDs desde el catálogo maestro.

---

# 3. Pantalla Observaciones

## Objetivo

Gestionar observaciones reales o negativas que se usarán para calibrar el predictor.

Estas observaciones no están aún dentro de `mushroom_profiles.json`, pero serán necesarias para el futuro calibrador.

La UI debe diseñarse como módulo futuro sin mezclarlo con el JSON de perfiles.

## Layout

```text
Header:
Predicción de floradas
Gestiona observaciones de campo utilizadas para calibrar y mejorar predicciones.

[Nueva observación]
```

## Métricas superiores

Cards:

```text
Total observaciones
Positivas / Presente
Negativas / No presente
Pendientes de validación
```

## Filtros

```text
Rango de fechas
Especie
Resultado
Observador
Fuente
Validación
Buscar observaciones
```

## Tabla de observaciones

Columnas:

```text
Fecha
Especie
Nombre común
Localidad
Provincia
Altitud
Hábitat
Resultado
Cantidad
Observador
Fuente
Validación
Acciones
```

## Resultado

Valores sugeridos:

```text
present
not_present
unknown
```

Visual:

- `present`: verde.
- `not_present`: rojo.
- `unknown`: gris/ámbar.

## Panel de detalle lateral

Al seleccionar una observación, mostrar panel derecho:

```text
ID observación
Especie
Nombre común
Fecha
Hora
Localidad
Provincia
Coordenadas
Altitud
Hábitat
Resultado
Cantidad estimada
Observador
Fuente
Notas del observador
Validación
```

## Uso para calibración

Mostrar card:

```text
Utilización para calibración
Esta observación se puede usar para calibración
Confianza automática: alta / media / baja
Score de calidad
```

## Acciones

```text
Nueva observación
Editar observación
Eliminar observación
Validar observación
Marcar como no válida
Importar observaciones
```

Nota:

La importación/exportación general no se implementa como tab propia, pero puede existir una acción puntual dentro de Observaciones en el futuro.

---

# 4. Pantalla Parámetros

## Objetivo

Editar los parámetros completos de una especie seleccionada, agrupando:

- Modelo climático.
- Modelo de hábitat.
- Fenología.
- Topografía.
- Scoring.

Esta pantalla debe ser una vista más directa y operativa que los subtabs de Especies.

Es importante que se visualice siempre la especie seleccionada.

## Header obligatorio

```text
Especie seleccionada: Boletus pinophilus
species_id: boletus_pinophilus
taxonomy_status: accepted
review_status: draft
```

## Selector de especie

Debe poder cambiar la especie activa.

Opciones:

- Select en header.
- O usar la especie seleccionada en la tab Especies.

## Layout

Dos columnas principales:

```text
┌──────────────────────────────┬──────────────────────────────┐
│ Modelo climático             │ Modelo de hábitat            │
│ - Lluvia                     │ - Ecología y hábitat         │
│ - Temperatura                │ - Suelos y litología         │
│ - Humedad                    │ - Topografía                 │
│ - Viento                     │ - Fenología                  │
│                              │ - Scoring                    │
└──────────────────────────────┴──────────────────────────────┘
```

## Modelo climático

Debe mostrar todos los campos de:

```text
weather_model.rainfall
weather_model.temperature
weather_model.humidity
weather_model.wind
```

No debe limitarse sólo a lluvia.

### Card Lluvia

```text
rain_7d_min_mm
rain_15d_min_mm
rain_15d_optimal_min_mm
rain_15d_optimal_max_mm
rain_30d_saturation_penalty_mm
snowmelt_bonus si existe
```

### Card Temperatura

```text
temp_min_7d_optimal_min_c
temp_min_7d_optimal_max_c
temp_max_7d_optimal_min_c
temp_max_7d_optimal_max_c
heat_penalty_temp_max_c
frost_penalty_temp_min_c
```

### Card Humedad

```text
humidity_min_7d_preferred_min_pct
humidity_max_7d_preferred_min_pct
```

### Card Viento

```text
wind_avg_3d_penalty_kmh
wind_gust_3d_penalty_kmh
dry_wind_sensitive
```

## Modelo de hábitat

Debe mostrar todos los campos de:

```text
ecology
topography
phenology
scoring_weights
```

### Card Ecología y hábitat

```text
ecology.trophic_mode_id
ecology.host_affinities[]
ecology.forest_type_affinities[]
ecology.habitat_feature_affinities[]
```

### Card Suelos y litología

```text
ecology.soil_affinities[]
ecology.lithology_affinities[]
```

### Card Topografía

```text
altitude_min_m
altitude_optimal_min_m
altitude_optimal_max_m
altitude_max_m
preferred_aspect_ids[]
aspect_notes
```

### Card Fenología

```text
main_months[]
secondary_months[]
season_pattern_ids[]
fruiting_delay_after_rain_days.min
fruiting_delay_after_rain_days.optimal_min
fruiting_delay_after_rain_days.optimal_max
fruiting_delay_after_rain_days.max
```

### Card Scoring

```text
scoring_weights.*
```

Mostrar todos los pesos existentes de la especie seleccionada.

No hardcodear únicamente los pesos estándar, porque algunas especies pueden tener:

```text
snowmelt_or_soil_moisture
```

## Acciones

```text
Restablecer
Aplicar sólo a esta especie
Guardar cambios
```

No implementar todavía “aplicar a todas las especies” salvo que se defina claramente, porque podría ser peligroso.

---

# 5. Pantalla Calibración

## Objetivo

Gestionar el estado de calibración de cada especie y preparar el modelo para usar observaciones reales.

Debe estar basada principalmente en:

```text
prediction_confidence
metadata.requires_human_validation
metadata.review_status
```

Y en el futuro, en observaciones reales.

## Header obligatorio

Mostrar especie seleccionada:

```text
Especie seleccionada: Boletus pinophilus
Confianza global: medium
Estado calibración local: not_calibrated
Prioridad calibración: high
Estado revisión: draft
```

## Cards superiores

```text
Estado calibración
Prioridad
Confianza global
Observaciones mínimas
Positivas mínimas
Negativas mínimas
```

Ejemplo:

```text
Estado calibración: no calibrada
Prioridad: alta
Confianza global: media
Observaciones mínimas: 20
Positivas mínimas: 8
Negativas mínimas: 12
```

## Sección 1: Perfil de confianza

Campos editables:

```text
overall_confidence
habitat_confidence
topography_confidence
phenology_confidence
weather_threshold_confidence
taxonomy_confidence
```

Cada campo debe ser un select con valores:

```text
low
medium
high
```

## Sección 2: Requisitos de calibración

Campos:

```text
local_calibration_status
calibration_priority
minimum_observations_for_calibration
minimum_positive_observations
minimum_negative_observations
requires_human_validation
```

## Sección 3: Cobertura de observaciones

Aunque las observaciones aún no estén en el JSON, diseñar el bloque para el futuro.

Mostrar:

```text
Total observaciones utilizadas
Positivas
Negativas
Datos faltantes clave
```

Debe visualizar progreso contra mínimos requeridos.

Ejemplo:

```text
28 / 120
10 / 60 positivas
8 / 50 negativas
5 / 20 datos faltantes clave
```

Estos datos pueden venir en el futuro de otro endpoint o fichero.

## Sección 4: Notas de calibración

Debe mostrar y editar:

```text
prediction_confidence.notes
```

Además puede tener un campo UI-only futuro:

```text
internal_calibration_notes
```

Si se implementa, dejar claro que no pertenece al JSON actual salvo que se decida ampliar el schema.

## Sección 5: Acciones y recomendaciones

Acciones:

```text
Añadir observaciones locales
Revisar umbrales meteorológicos
Iniciar validación humana
Marcar revisado
Recalcular scoring
Guardar calibración
```

Notas:

- `Añadir observaciones locales` debe llevar a la tab Observaciones.
- `Revisar umbrales meteorológicos` debe llevar a Parámetros.
- `Guardar calibración` actualiza `prediction_confidence` y metadata relacionada.
- `Marcar revisado` puede actualizar `metadata.review_status`.

---

# Validaciones generales

## Validación de identidad

- `species_id` obligatorio.
- `species_id` único.
- `scientific_name` obligatorio.
- `common_names` puede estar vacío, pero mostrar warning si no hay nombres comunes.

## Validación de arrays

Los siguientes campos deben ser arrays editables:

```text
common_names
host_affinities
forest_type_affinities
soil_affinities
lithology_affinities
habitat_feature_affinities
main_months
secondary_months
season_pattern_ids
preferred_aspect_ids
```

## Validación de fenología

- `main_months` debe contener valores 1-12.
- `secondary_months` debe contener valores 1-12.
- `fruiting_delay_after_rain_days.min <= optimal_min <= optimal_max <= max`.

## Validación de topografía

- `altitude_min_m <= altitude_optimal_min_m <= altitude_optimal_max_m <= altitude_max_m`.

## Validación meteorológica

- Los rangos min/max deben ser coherentes.
- Temperatura mínima óptima min <= temperatura mínima óptima max.
- Temperatura máxima óptima min <= temperatura máxima óptima max.
- Rain 15d optimal min <= Rain 15d optimal max.
- Si `snowmelt_bonus` no existe, no forzar su creación.

## Validación de scoring

- Suma de `scoring_weights` recomendada: 1.00.
- Mostrar warning si la suma está fuera de rango razonable.
- Permitir normalizar pesos.

## Validación de confianza/calibración

- `overall_confidence` debe estar en los valores controlados del contrato del modelo (`low`, `medium`, `high`).
- Las demás confidence también deben usar `low`, `medium`, `high`.
- `local_calibration_status` debe estar en valores controlados.
- `calibration_priority` debe estar en valores controlados.
- Mínimos de observaciones deben ser enteros positivos.

## Validación metadata

- `review_status` debe estar en valores controlados: `draft`, `needs_review`, `reviewed`, `validated`, `deprecated`.
- `requires_human_validation` debe ser boolean.
- `created_at` y `updated_at` deben ser fechas válidas.

---

# Comportamiento esperado

## Carga inicial

- Cargar `mushroom_profiles.json`.
- Mostrar Resumen por defecto.
- Seleccionar por defecto la primera especie o la última editada.
- Mostrar contador de especies.

## Edición

- Los cambios se mantienen en estado local hasta guardar.
- Mostrar indicador de cambios pendientes.
- Permitir descartar cambios.
- Confirmar antes de cambiar de especie si hay cambios sin guardar.

## Guardado

- Guardar debe actualizar el perfil de especie correspondiente.
- Actualizar `metadata.updated_at`.
- No modificar `created_at`.
- No modificar `created_by` salvo que se defina explícitamente.

## Duplicar especie

- Clonar perfil actual.
- Generar nuevo `species_id`.
- Poner `metadata.review_status = draft`.
- Poner `metadata.requires_human_validation = true`.
- Cambiar `scientific_name` o pedirlo en modal.

## Eliminar especie

- Pedir confirmación.
- No permitir eliminar si hay observaciones asociadas en el futuro, salvo confirmación especial.

## Validar perfil

Debe ejecutar validaciones del schema lógico y mostrar:

```text
Errores
Warnings
Recomendaciones
```

---

# Componentes sugeridos

```text
MushroomProfilesPage
├── MushroomSidebar
├── MushroomHeader
├── MushroomTabs
├── SummaryTab
│   ├── SummaryMetricCards
│   ├── CalibrationStatusChart
│   ├── CalibrationPriorityChart
│   ├── AttentionSpeciesTable
│   ├── TaxonomyReviewCard
│   └── NextActionsCard
├── SpeciesTab
│   ├── SpeciesListPanel
│   ├── SpeciesDetailHeader
│   ├── SpeciesSubTabs
│   ├── GeneralSubTab
│   ├── EcologySubTab
│   ├── PhenologySubTab
│   ├── WeatherModelSubTab
│   ├── ScoringSubTab
│   ├── ConfidenceSubTab
│   └── MetadataSubTab
├── ObservationsTab
│   ├── ObservationMetricCards
│   ├── ObservationFilters
│   ├── ObservationsTable
│   └── ObservationDetailPanel
├── ParametersTab
│   ├── SelectedSpeciesHeader
│   ├── ClimateModelPanel
│   ├── HabitatModelPanel
│   └── ScoringWeightsPanel
├── CalibrationTab
│   ├── CalibrationHeader
│   ├── CalibrationMetricCards
│   ├── ConfidenceProfileCard
│   ├── CalibrationRequirementsCard
│   ├── ObservationCoverageCard
│   ├── CalibrationNotesCard
│   └── CalibrationActionsCard
├── TagEditor
├── MonthSelector
├── AspectSelector
├── ConfidenceBadge
├── CalibrationBadge
├── ReviewStatusBadge
├── NumericFieldWithUnit
├── ConfirmDialog
└── UnsavedChangesDialog
```

No es obligatorio crear todos estos componentes si el código actual del repo tiene una estructura más simple, pero sí se recomienda evitar un único componente gigante.

---

# Estilo visual

## Colores

- Fondo principal: dark navy / charcoal.
- Cards: dark blue-gray ligeramente más claro.
- Bordes: gris azulado sutil.
- Primary: azul/cyan.
- Success: verde.
- Warning: ámbar.
- Danger: rojo.
- Purple: estados de calibración o taxones complejos.

## Chips

Usar chips para:

```text
taxonomy_status
edibility
overall_confidence
local_calibration_status
calibration_priority
review_status
requires_human_validation
```

## Tablas

- Filas compactas.
- Hover suave.
- Fila seleccionada con borde/acento azul.
- Acciones al final.

## Formularios

- Inputs compactos.
- Labels claros.
- Unidades visibles:
  - mm
  - ºC
  - %
  - km/h
  - m
  - días

## Responsive

- Desktop: layout de 2 columnas cuando tenga sentido.
- Pantallas medianas: cards en 2 columnas.
- Pantallas pequeñas: 1 columna y scroll vertical.
- Tablas con scroll horizontal.

---

# Implementación recomendada para Codex

## Enfoque

Codex tiene acceso al repo real, por tanto debe inspeccionar primero el código existente antes de implementar.

No debe reconstruir la aplicación desde cero.

Debe:

1. Localizar dónde encaja mejor esta nueva pantalla en la app.
2. Reutilizar estilos, componentes y patrones existentes de Rainmapper.
3. Reutilizar la sidebar, botones, cards, tabs y badges existentes si los hay.
4. Cargar `mushroom_profiles.json` desde la ubicación adecuada del repo.
5. Mantener el modelo de datos fiel al JSON.
6. Implementar primero una versión funcional con edición local y guardado según la arquitectura real.
7. Dejar Observaciones como módulo futuro si todavía no hay backend/dataset real.

## Restricciones

- No inventar backend nuevo sin aprobación.
- No cambiar el schema de `mushroom_profiles.json` sin aprobación.
- No mezclar observaciones reales dentro de `mushroom_profiles.json` salvo que se decida explícitamente.
- No añadir pestañas de Importación/Exportación ni Ajustes en esta fase; la importación/exportación debe ser acción administrativa avanzada.
- No hardcodear que todas las especies tengan exactamente los mismos campos opcionales.
- No forzar campos opcionales como `snowmelt_bonus` o `snowmelt_or_soil_moisture` si no existen en una especie.

---

# Prompt corto para Codex

Lee `docs/ui/mushroom-profiles-maintenance.md` y el fichero real `mushroom_profiles.json`.

Quiero desarrollar un mantenimiento de especies para el futuro predictor de floradas de Rainmapper, con el estilo visual dark mode usado en el resto de pantallas rediseñadas.

No inventes un modelo de datos nuevo. Usa el modelo real de `mushroom_profiles.json`.

Implementa o prepara la implementación de estas pantallas:

1. Resumen.
2. Especies.
3. Observaciones.
4. Parámetros.
5. Calibración.

No implementes por ahora pestañas de Importación/Exportación ni Ajustes. Sí debes prever acciones administrativas para importar/exportar JSON y exportar una plantilla vacía del modelo.

Requisitos clave:

- La pantalla `Especies` debe permitir mantener todo el contenido de `species_profiles[]`.
- La pantalla `Parámetros` debe mostrar siempre la especie seleccionada.
- La pantalla `Parámetros` debe incluir todos los parámetros climáticos: lluvia, temperatura, humedad y viento.
- La pantalla `Parámetros` también debe incluir el modelo de hábitat: ecología, suelos, litología, topografía, fenología y scoring.
- La pantalla `Calibración` debe trabajar con `prediction_confidence` y `metadata`.
- La pantalla `Observaciones` debe diseñarse como módulo futuro para calibración, sin mezclar observaciones dentro de `mushroom_profiles.json` salvo que ya exista soporte real.
- Respeta los controlled values definidos en el JSON.
- Mantén el diseño compacto, moderno y consistente con Rainmapper.

Antes de implementar, inspecciona el repo y dime:

1. Dónde encaja mejor esta nueva pantalla en la aplicación.
2. Qué componentes existentes se pueden reutilizar.
3. Cómo cargarías y guardarías `mushroom_profiles.json`.
4. Qué estructura de componentes propones.
5. Qué validaciones implementarías primero.
6. Qué partes dejarías como mock/futuras, especialmente Observaciones y Calibración basada en observaciones reales.
7. Riesgos o dudas antes de tocar código.

Espera mi confirmación antes de aplicar cambios.
