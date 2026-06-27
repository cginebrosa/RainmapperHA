# Especificación UI — Mantenimiento de `mushroom_reference_catalogs.json`

## Propuesta

Esta especificación desarrolla el mantenimiento de un **Hub operativo del catálogo maestro** para Rainmapper.

El objetivo no es crear un CRUD aislado de IDs, sino una pantalla de mantenimiento del vocabulario maestro que sirva realmente al futuro motor de predicción de floradas.

El catálogo maestro debe permitir:

- mantener los IDs controlados de `mushroom_reference_catalogs.json`;
- ver su uso real en `mushroom_profiles.json`;
- ver su uso real en `mushroom_gis_mappings.json`;
- detectar inconsistencias, IDs huérfanos, IDs sin uso y referencias rotas;
- entender qué utilidad tiene cada ID dentro del motor de predicción;
- ayudar al flujo de desarrollo y validación del predictor.

## Referencias visuales

Debes utilizar las siguientes imagenes como referencias visuales para el desarrollo

docs/mushrooms/ui/reference-catalogs/reference-catalog-hub.png
docs/mushrooms/ui/reference-catalogs/reference-catalog-detail-form.png
docs/mushrooms/ui/reference-catalogs/reference-catalog-domain-impact-reference.png

Uso previsto de cada imagen:

```text
reference-catalog-hub.png
    Referencia principal de la propuesta.
    Muestra el hub operativo: cards superiores, filtros por grupo, tabla global,
    panel lateral de detalle, uso/impacto y validación cruzada.

reference-catalog-detail-form.png
    Referencia visual para formularios de edición en drawer lateral.
    Útil para ver cómo renderizar campos heterogéneos según el grupo de catálogo.

reference-catalog-domain-impact-reference.png
    Referencia complementaria para entender cómo mostrar relación con el motor,
    dominios ecológicos, impacto predictivo y uso cruzado.
```

Estas imágenes son referencias visuales, no contratos funcionales exactos. El código real debe respetar siempre el modelo de datos de los JSON existentes.

---

# 1. Contexto del modelo

El módulo de predicción de floradas usa tres ficheros relacionados:

```text
mushroom_reference_catalogs.json
mushroom_profiles.json
mushroom_gis_mappings.json
```

Responsabilidades:

```text
mushroom_reference_catalogs.json
    Vocabulario maestro. Define todos los IDs válidos.

mushroom_profiles.json
    Perfiles de especies. Deben referenciar IDs existentes en el catálogo.

mushroom_gis_mappings.json
    Reglas para traducir datos GIS externos a IDs internos del catálogo.
```

La dependencia conceptual es:

```text
mushroom_reference_catalogs.json
        ↑
        │ IDs controlados
        │
mushroom_profiles.json       mushroom_gis_mappings.json
        │                              │
        └──────────────┬───────────────┘
                       ↓
              motor de predicción
```

El mantenimiento del catálogo debe reforzar esta arquitectura.

## Regla clave

No crear valores ecológicos directamente en perfiles o mapeos GIS si no existen primero en `mushroom_reference_catalogs.json`.

El catálogo maestro es la fuente de verdad para los IDs computables.

---

# 2. Modelo de datos a mantener

## Estructura raíz esperada

```json
{
  "schema_version": "0.1",
  "model_purpose": "reference_catalogs_for_mushroom_fruiting_probability_scoring",
  "important_note": "...",
  "catalogs": {},
  "metadata": {}
}
```

## Grupos actuales del catálogo

El bloque `catalogs` contiene actualmente estos grupos:

```text
trophic_modes
host_taxa
forest_types
soil_types
lithology_types
aspects
season_patterns
habitat_features
```

Cobertura actual documentada:

```text
trophic_modes: 4 entradas
host_taxa: 26 entradas
forest_types: 18 entradas
soil_types: 17 entradas
lithology_types: 13 entradas
aspects: 10 entradas
season_patterns: 17 entradas
habitat_features: 9 entradas
```

La UI no debe hardcodear estos números. Debe calcularlos desde el JSON real.

---

# 3. Objetivo funcional de la pantalla

La pantalla se llamará:

```text
Catálogo maestro de referencia
```

Subtítulo recomendado:

```text
Hub operativo del vocabulario del motor de predicción
```

Debe permitir:

1. Ver el estado global del catálogo.
2. Filtrar entradas por grupo.
3. Buscar por ID, etiqueta, nombre científico o texto relevante.
4. Editar entradas según la estructura real de cada grupo.
5. Ver relaciones de uso con perfiles.
6. Ver relaciones de uso con GIS mappings.
7. Ver qué dominio del motor usa cada ID.
8. Mostrar validación cruzada.
9. Gestionar entradas nuevas, duplicadas o eliminadas con seguridad.
10. Mantener el estilo visual dark mode de Rainmapper.

---

# 4. Layout general

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar Rainmapper                                           │
├──────────────────────────────────────────────────────────────┤
│ Header                                                       │
│ Catálogo maestro de referencia                               │
│ Hub operativo del vocabulario del motor de predicción         │
│ [Volver] [Actualizar] [Buscar ID, grupo o uso...]             │
│                                      [Nueva entrada]          │
├──────────────────────────────────────────────────────────────┤
│ Cards superiores de salud y uso                              │
├──────────────────────────────────────────────────────────────┤
│ Filtros por grupo                                            │
│ Todos | trophic_modes | host_taxa | forest_types | ...       │
├──────────────────────────────────────────────────────────────┤
│ Tabla global de entradas              │ Drawer detalle        │
│                                       │ - campos editables    │
│                                       │ - uso e impacto       │
│                                       │ - validación cruzada  │
├──────────────────────────────────────────────────────────────┤
│ Panel inferior de validación cruzada / alertas               │
└──────────────────────────────────────────────────────────────┘
```

---

# 5. Header

Debe contener:

```text
Catálogo maestro de referencia
Hub operativo del vocabulario del motor de predicción
```

Acciones:

```text
Volver
Actualizar
Nueva entrada
```

Buscador:

```text
Buscar ID, grupo, etiqueta, nombre científico o uso...
```

Indicadores de estado:

```text
8 grupos · 114 IDs
Flujo validado / Con alertas / Con errores
```

El indicador de “flujo validado” es derivado. No debe persistirse en el JSON salvo que ya exista soporte real.

---

# 6. Cards superiores

Mostrar cards compactas con métricas derivadas.

Cards recomendadas:

```text
Total grupos
Total IDs
Usados en perfiles
Usados en GIS
IDs huérfanos
Sin uso
Con jerarquía
Pendientes revisión
```

## Definiciones

### Total grupos

Número de claves dentro de `catalogs`.

### Total IDs

Suma de entradas en todos los grupos.

### Usados en perfiles

Número de IDs del catálogo encontrados al analizar `mushroom_profiles.json`.

### Usados en GIS

Número de IDs del catálogo emitidos o referenciados por `mushroom_gis_mappings.json`.

### IDs huérfanos

IDs referenciados desde perfiles o GIS mappings que no existen en `mushroom_reference_catalogs.json`.

### Sin uso

IDs definidos en el catálogo que no aparecen en perfiles ni en GIS mappings.

### Con jerarquía

IDs que tienen relación jerárquica, normalmente `parent_id` o equivalentes.

### Pendientes revisión

Entradas que el validador marque como dudosas, incompletas o inconsistentes.

Si el modelo actual no tiene un campo explícito de revisión por entrada, esta métrica debe ser derivada de validaciones, no inventada como campo persistente.

---

# 7. Filtros principales

## Filtros por grupo

Tabs o chips:

```text
Todos
trophic_modes
host_taxa
forest_types
soil_types
lithology_types
aspects
season_patterns
habitat_features
```

Cada chip puede mostrar contador:

```text
host_taxa 26
soil_types 17
```

## Filtros adicionales

```text
Estado de uso:
- Todos
- Usado
- Sin uso
- Huérfano
- Con referencias GIS
- Con referencias en perfiles

Dominio del motor:
- Trófico
- Huésped
- Hábitat
- Edáfico
- Geológico
- Topográfico
- Fenológico
```

Estos estados/dominios son derivados para UI. No deben modificar el schema del JSON.

---

# 8. Tabla global de entradas

La tabla central debe ser la herramienta principal de navegación.

Columnas recomendadas:

```text
Grupo
ID
Label / scientific_name
Parent ID
Uso en perfiles
Uso en GIS
Dominio del motor
Estado
Acciones
```

## Grupo

Nombre del catálogo al que pertenece la entrada:

```text
host_taxa
soil_types
lithology_types
...
```

## ID

ID estable de la entrada.

Ejemplos:

```text
host_pinus_sylvestris
soil_calcareous
lith_limestone
aspect_NE
season_autumn_main
feature_snowmelt
```

## Label / scientific_name

Debe mostrar el mejor texto humano disponible según el grupo.

Reglas sugeridas:

```text
host_taxa:
    scientific_name si existe.
    Si no, label.es o id.

soil_types / lithology_types / forest_types / aspects / season_patterns / habitat_features:
    label.es si existe.
    Si no, label.en.
    Si no, id.

trophic_modes:
    label.es o id.
```

## Parent ID

Mostrar `parent_id` si existe.

Si no existe:

```text
—
```

## Uso en perfiles

Número de referencias detectadas en `mushroom_profiles.json`.

## Uso en GIS

Número de referencias detectadas en `mushroom_gis_mappings.json`.

## Dominio del motor

Campo derivado por grupo:

```text
trophic_modes       → trófico
host_taxa           → huésped / simbiosis
forest_types        → hábitat
soil_types          → edáfico
lithology_types     → geológico
aspects             → topográfico
season_patterns     → fenológico
habitat_features    → microhábitat
```

## Estado

Estado visual derivado:

```text
Activo
Sin uso
Huérfano
Revisar
Inconsistente
```

No debe persistirse automáticamente como campo nuevo salvo que el JSON ya tenga un campo equivalente.

---

# 9. Drawer lateral de detalle

Al seleccionar una entrada de la tabla, abrir un drawer lateral derecho.

El drawer debe incluir:

```text
Detalle del término
Uso e impacto
Referencias de uso
Validación cruzada
Alertas y avisos
Acciones
```

## 9.1 Detalle del término

Debe renderizar un formulario dinámico según el grupo y según los campos reales de la entrada.

No inventar campos nuevos.

No asumir que todos los grupos comparten los mismos campos.

Campos comunes posibles:

```text
id
label
label.es
label.ca
label.en
parent_id
notes
```

Campos específicos posibles documentados:

### host_taxa

```text
id
rank
scientific_name
genus
family
common_names.es[]
common_names.ca[]
common_names.en[]
parent_id
```

### soil_types

```text
id
label.es
label.ca
label.en
ph_min
ph_max
texture
organic_matter
drainage
notes
```

### lithology_types

```text
id
label.es
general_reaction
parent_soil_tendency_ids[]
```

### aspects

```text
id
label
```

### season_patterns

```text
id
label
```

### habitat_features

```text
id
label
```

### forest_types

```text
id
label
parent_id
```

### trophic_modes

```text
id
label
```

Codex debe inspeccionar el JSON real y renderizar sólo los campos existentes o estructuralmente soportados.

## 9.2 Uso e impacto

Bloque obligatorio en el drawer.

Debe responder:

```text
¿Dónde se usa este ID?
¿Qué parte del predictor alimenta?
¿Qué pasaría si se modifica?
```

Mostrar:

```text
Usado en mushroom_profiles
Usado en mushroom_gis_mappings
Dominios del motor
Referencias de uso
```

Ejemplo:

```text
Usado en mushroom_profiles: 18 perfiles
Usado en mushroom_gis_mappings: 12 mapeos GIS
Dominio del motor: huésped primario
```

## 9.3 Referencias de uso

Mostrar ejemplos concretos.

Ejemplo para `host_pinus_sylvestris`:

```text
Perfil: Boletus pinophilus
Campo: ecology.host_affinities

Perfil: Lactarius sanguifluus
Campo: ecology.host_affinities

Mapping GIS: Catalunya vegetation layer
Campo: mapped_host_ids
```

Si hay muchas referencias:

```text
Ver todas las referencias
```

## 9.4 Validación cruzada

Mostrar validaciones asociadas a la entrada seleccionada:

```text
ID válido
Parent existente
Referenciado correctamente en perfiles
Referenciado correctamente en GIS
No hay duplicados
No hay referencias rotas
```

Estados visuales:

```text
OK
Warning
Error
```

## 9.5 Alertas y avisos

Ejemplos:

```text
Este ID está definido pero no se usa en perfiles ni mapeos GIS.
Este ID tiene parent_id inexistente.
Este ID está usado en GIS pero no en perfiles.
Este ID está usado en perfiles pero no existe en catálogo.
No cambies el ID si ya está referenciado en producción.
```

---

# 10. Formularios por grupo

## Regla general

El mantenimiento debe ser **schema-aware** y **group-aware**.

Codex debe evitar un formulario único rígido.

La UI debe renderizar campos en función de:

1. grupo seleccionado;
2. campos existentes en la entrada;
3. convenciones documentadas del catálogo.

## host_taxa

Formulario recomendado:

```text
ID
Rank
Scientific name
Genus
Family
Common names ES
Common names CA
Common names EN
Parent ID
```

`common_names` debe editarse como chips/tags por idioma.

## soil_types

Formulario recomendado:

```text
ID
Label ES
Label CA
Label EN
pH min
pH max
Texture
Organic matter
Drainage
Notes
```

Validaciones:

```text
ph_min <= ph_max
id único
```

## lithology_types

Formulario recomendado:

```text
ID
Label ES
General reaction
Parent soil tendency IDs[]
Notes
```

`parent_soil_tendency_ids[]` debe seleccionar IDs existentes de `soil_types`.

## aspects

Formulario recomendado:

```text
ID
Label ES / CA / EN si existe
```

## season_patterns

Formulario recomendado:

```text
ID
Label ES / CA / EN si existe
Description / notes si existe
```

## habitat_features

Formulario recomendado:

```text
ID
Label ES / CA / EN si existe
Description / notes si existe
```

## forest_types

Formulario recomendado:

```text
ID
Label ES / CA / EN si existe
Parent ID si existe
Notes si existe
```

## trophic_modes

Formulario recomendado:

```text
ID
Label ES / CA / EN si existe
Description / notes si existe
```

---

# 11. Panel inferior de validación cruzada

En la parte inferior de la pantalla, mostrar un resumen de consistencia.

Bloques:

```text
IDs válidos en perfiles
IDs válidos en GIS
Faltantes
Huérfanos
Inconsistencias
```

## IDs válidos en perfiles

IDs usados por `mushroom_profiles.json` que existen en el catálogo.

## IDs válidos en GIS

IDs emitidos/referenciados por `mushroom_gis_mappings.json` que existen en el catálogo.

## Faltantes

IDs referenciados en perfiles o GIS que no existen en el catálogo.

## Huérfanos

IDs definidos en catálogo pero no usados en perfiles ni GIS.

## Inconsistencias

Problemas como:

```text
parent_id inexistente
duplicados
tipos incompatibles
campos requeridos ausentes
referencia a grupo incorrecto
```

---

# 12. Relación con perfiles

La pantalla debe analizar `mushroom_profiles.json` para detectar referencias a IDs del catálogo.

Referencias mínimas a detectar:

```text
ecology.trophic_mode_id
ecology.host_affinities[].id
ecology.forest_type_affinities[].id
ecology.soil_affinities[].id
ecology.lithology_affinities[].id
ecology.habitat_feature_affinities[].id
phenology.season_pattern_ids[]
topography.preferred_aspect_ids[]
```

Codex debe adaptar estos paths al JSON real.

Si el JSON real todavía no está completamente normalizado y usa nombres o listas distintas, Codex debe reportarlo y no inventar migraciones sin confirmación.

---

# 13. Relación con GIS mappings

La pantalla debe analizar `mushroom_gis_mappings.json` para detectar IDs emitidos por reglas GIS.

En la primera fase esta relación es de sólo lectura: se usa para impacto, warnings y validación cruzada. La edición completa de `mushroom_gis_mappings.json` queda fuera de esta pantalla y se diseñará en una fase posterior.

Referencias mínimas a detectar:

```text
vegetation_mappings[].mapped_host_ids[]
vegetation_mappings[].mapped_forest_type_ids[]
vegetation_mappings[].mapped_habitat_feature_ids[]
corine_land_cover_mappings[].mapped_forest_type_ids[]
corine_land_cover_mappings[].mapped_habitat_feature_ids[]
lithology_mappings[].mapped_lithology_ids[]
lithology_mappings[].mapped_soil_tendency_ids[]
derived_rules[].outputs[]
```

Codex debe inspeccionar el JSON real y adaptar los paths a la estructura existente.

---

# 14. Utilidad real dentro del motor de predicción

El mantenimiento debe explicar y visualizar cómo cada grupo alimenta el predictor.

## Mapeo de grupos a componentes del motor

```text
trophic_modes
    Define estrategia ecológica base de la especie.
    Impacta en interpretación de hábitat y tipo de perfil.

host_taxa
    Alimenta afinidad con hospedadores.
    Muy importante para especies ectomicorrícicas.

forest_types
    Alimenta el score de hábitat.

soil_types
    Alimenta compatibilidad edáfica y preferencias/evitaciones.

lithology_types
    Alimenta sustrato geológico y puede derivar tendencia de suelo.

aspects
    Alimenta score topográfico junto con DEM/orientación.

season_patterns
    Complementa main_months y secondary_months en el score de temporada.

habitat_features
    Alimenta microhábitat: musgo, hojarasca, ribera, nieve, prados, quemados, etc.
```

La UI debe mostrar este contexto en:

- drawer lateral;
- tooltip informativo;
- panel de “Uso e impacto”;
- validación cruzada.

---

# 15. Acciones

## Acciones globales

```text
Actualizar
Nueva entrada
Guardar cambios
Ver informe completo de integridad
Importar JSON
Exportar JSON
Exportar plantilla vacía
```

## Acciones por entrada

```text
Editar
Duplicar
Eliminar
Ver referencias
```

## Restricciones

- `Eliminar` debe pedir confirmación.
- No permitir eliminar sin advertir si el ID está usado en perfiles o GIS.
- No permitir cambiar `id` sin advertencia fuerte si está usado.
- Duplicar debe generar un nuevo ID.
- Guardar debe ejecutar validación local antes de persistir.

## Importación/exportación JSON

Estas acciones trabajan sobre `mushroom_reference_catalogs.json`.

### Exportar JSON

Debe exportar el catálogo persistente actual usado por HA. Si también se permite exportar los defaults empaquetados con la app, debe aparecer como acción separada:

```text
Exportar JSON actual
Exportar defaults empaquetados
```

### Exportar plantilla vacía

Debe generar un JSON válido con la estructura raíz del catálogo y todos los grupos actuales vacíos:

```json
{
  "schema_version": "0.1",
  "model_purpose": "reference_catalogs_for_mushroom_fruiting_probability_scoring",
  "important_note": "...",
  "catalogs": {
    "trophic_modes": [],
    "host_taxa": [],
    "forest_types": [],
    "soil_types": [],
    "lithology_types": [],
    "aspects": [],
    "season_patterns": [],
    "habitat_features": []
  },
  "metadata": {}
}
```

La plantilla vacía debe preservar los grupos de catálogo existentes para que un importador posterior pueda validar estructura sin inferir grupos.

### Importar JSON

Flujo obligatorio:

1. Seleccionar fichero JSON.
2. Validar sintaxis.
3. Validar estructura raíz y grupos de catálogo.
4. Validar IDs únicos por grupo.
5. Validar referencias internas como `parent_id`, `dominant_host_ids`, `soil_bias_ids` y `parent_soil_tendency_ids`.
6. Validar referencias cruzadas desde `mushroom_profiles.json` y `mushroom_gis_mappings.json` contra el catálogo importado.
7. Mostrar resumen de diferencias: IDs añadidos, modificados, eliminados, errores y warnings.
8. Pedir confirmación fuerte si se eliminan IDs usados por perfiles o GIS.
9. Crear backup del catálogo persistente actual.
10. Guardar con escritura atómica.
11. Ejecutar validación final.

No debe modificar `mushroom_profiles.json` ni `mushroom_gis_mappings.json` automáticamente. Si una importación deja referencias rotas, debe bloquearse o requerir un flujo explícito de migración.

---

# 16. Validaciones

## Validaciones de catálogo

```text
id obligatorio
id único dentro de su grupo
id en minúsculas
id con guiones bajos
id no dependiente del idioma
parent_id existe si se informa
label/nombre humano disponible si el grupo lo requiere
```

## Validaciones de campos específicos

### host_taxa

```text
scientific_name recomendado si rank = species
genus recomendado
family recomendado
parent_id debe existir si se informa
```

Estado de implementacion pendiente:

```text
La WebUI actual permite editar host_taxa.parent_id, pero debe anadirse feedback de
validacion cruzada visible en pantalla para confirmar que el parent_id existe en
catalogs.host_taxa antes/despues de guardar.
```

### soil_types

```text
ph_min <= ph_max
```

### lithology_types

```text
parent_soil_tendency_ids[] debe referenciar soil_types existentes
```

### cross-file

```text
Todo ID usado en mushroom_profiles existe en reference_catalogs.
Todo ID emitido por mushroom_gis_mappings existe en reference_catalogs.
No hay IDs duplicados.
No hay parent_id rotos.
```

Pendiente de UI:

```text
Mostrar validaciones de cross references por campo, especialmente:
- host_taxa.parent_id -> catalogs.host_taxa
- forest_types.dominant_host_ids[] -> catalogs.host_taxa
- forest_types.soil_bias_ids[] -> catalogs.soil_types
- lithology_types.parent_soil_tendency_ids[] -> catalogs.soil_types
```

---

# 17. Estados visuales derivados

Los estados visuales no son necesariamente campos persistentes.

Estados recomendados:

```text
Activo
Usado
Sin uso
Huérfano
Faltante
Revisar
Inconsistente
```

Colores:

```text
Activo / usado: verde
Sin uso: gris
Huérfano / faltante: ámbar
Inconsistente / error: rojo
Revisión: violeta o ámbar
```

---

# 18. Comportamiento esperado

## Carga inicial

1. Cargar `mushroom_reference_catalogs.json`.
2. Cargar `mushroom_profiles.json` si está disponible.
3. Cargar `mushroom_gis_mappings.json` si está disponible.
4. Calcular métricas derivadas.
5. Mostrar tabla global con todas las entradas.
6. Seleccionar la primera entrada o mantener la última seleccionada.

## Edición

- Los cambios se mantienen en estado local.
- Mostrar indicador de cambios pendientes.
- Confirmar antes de cambiar de entrada si hay cambios sin guardar.
- Actualizar el panel de validación al modificar campos relevantes.

## Guardado

- Guardar sólo debe persistir cambios en `mushroom_reference_catalogs.json`.
- No modificar automáticamente `mushroom_profiles.json`.
- No modificar automáticamente `mushroom_gis_mappings.json`.
- Si un cambio requiere actualizar perfiles o GIS mappings, mostrar aviso o propuesta, pero no aplicarlo sin confirmación explícita.

---

# 19. Componentes sugeridos

```text
ReferenceCatalogPage
├── ReferenceCatalogHeader
├── ReferenceCatalogSummaryCards
├── ReferenceCatalogGroupFilters
├── ReferenceCatalogTable
├── ReferenceCatalogDetailDrawer
│   ├── CatalogEntryForm
│   ├── EntryUsageImpactPanel
│   ├── EntryReferencesPanel
│   ├── EntryValidationPanel
│   └── EntryAlertsPanel
├── CrossValidationSummary
├── CrossValidationAlerts
├── ConfirmDialog
├── UnsavedChangesDialog
└── CatalogBadge
```

## Componentes de formulario por grupo

```text
CatalogEntryForm
├── TrophicModeForm
├── HostTaxonForm
├── ForestTypeForm
├── SoilTypeForm
├── LithologyTypeForm
├── AspectForm
├── SeasonPatternForm
└── HabitatFeatureForm
```

Si el repo ya tiene componentes genéricos de forms/cards/tables/drawers, Codex debe reutilizarlos antes de crear nuevos.

---

# 20. Criterios de aceptación

La implementación se considera correcta si:

- Se puede visualizar todo el catálogo maestro.
- Se puede filtrar por grupo.
- Se puede buscar por ID o etiqueta.
- Se puede seleccionar una entrada y ver su detalle.
- Los formularios respetan los campos reales del JSON.
- Se visualiza uso en perfiles.
- Se visualiza uso en GIS mappings.
- Se visualiza utilidad en el motor de predicción.
- Se muestra validación cruzada.
- Se detectan IDs faltantes, huérfanos e inconsistentes.
- No se inventan campos persistentes nuevos.
- No se modifica `mushroom_profiles.json` ni `mushroom_gis_mappings.json` sin confirmación explícita.
- El diseño sigue el estilo visual dark mode de Rainmapper.
- La UI es consistente con las pantallas ya diseñadas para `mushroom_profiles`.
- Codex puede usar las imágenes de referencia sin interpretarlas como datos reales.

---

# 21. Proceso obligatorio para Codex

Antes de implementar, Codex debe inspeccionar el repo y responder:

1. Dónde están ubicados los JSON reales.
2. Dónde encaja mejor esta pantalla en la navegación de Rainmapper.
3. Qué componentes UI existentes se pueden reutilizar.
4. Qué estructura real tienen las entradas de cada grupo de catálogo.
5. Qué paths reales de `mushroom_profiles.json` referencian IDs del catálogo.
6. Qué paths reales de `mushroom_gis_mappings.json` emiten IDs del catálogo.
7. Qué validaciones cruzadas se pueden implementar ya.
8. Qué partes deben quedar como derivadas o mock si falta backend.
9. Riesgos antes de tocar código.

No implementar cambios hasta recibir confirmación.

---

# Prompt corto para Codex

Lee estos documentos y datos:

```text
docs/mushrooms/ui/reference-catalogs/reference-catalog-maintenance-proposal.md
docs/mushrooms/ui/reference-catalogs/reference-catalog-hub.png
docs/mushrooms/ui/reference-catalogs/reference-catalog-detail-form.png
docs/mushrooms/ui/reference-catalogs/reference-catalog-domain-impact-reference.png

mushroom_reference_catalogs.json
mushroom_profiles.json
mushroom_gis_mappings.json
```

Quiero desarrollar el mantenimiento del catálogo maestro `mushroom_reference_catalogs.json` como un **hub operativo del motor de predicción**, no como un CRUD aislado.

Objetivo:

- mantener los IDs controlados del catálogo;
- visualizar su uso real en `mushroom_profiles.json`;
- visualizar su uso real en `mushroom_gis_mappings.json`;
- mostrar control de calidad y validación cruzada;
- mostrar la utilidad de cada ID dentro del motor de predicción;
- mantener el estilo visual dark mode de Rainmapper, coherente con las pantallas de `mushroom_profiles`.

No inventes campos persistentes nuevos. No cambies el schema sin permiso. No modifiques perfiles ni GIS mappings automáticamente.

Antes de implementar, inspecciona el repo y dime:

1. Archivos implicados.
2. Estructura real de `mushroom_reference_catalogs.json`.
3. Campos reales por grupo de catálogo.
4. Paths reales de referencias en `mushroom_profiles.json`.
5. Paths reales de referencias en `mushroom_gis_mappings.json`.
6. Componentes UI existentes que puedes reutilizar.
7. Plan de implementación.
8. Validaciones cruzadas que implementarás.
9. Riesgos o dudas.

Espera mi confirmación antes de aplicar cambios.
