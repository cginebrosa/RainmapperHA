# Referencia de `mushroom_gis_mappings.json`

Versión del documento: borrador 0.1
Fichero descrito: `mushroom_gis_mappings.json`

Este fichero define reglas para traducir información externa de capas GIS a IDs internos del modelo de setas.

## 1. Responsabilidad del fichero

`mushroom_gis_mappings.json` responde a la pregunta:

```text
¿Cómo convierto una clase externa de vegetación, cobertura, hábitat o geología en IDs internos que entienda el motor de predicción?
```

Ejemplo conceptual:

```text
Clase GIS: "Pinedes de pi negre"
↓
IDs internos:
host_pinus_uncinata
forest_subalpine_pine
```

El motor no debe depender directamente de textos externos de WMS/WFS/CORINE. Debe depender de IDs internos controlados.

## 2. Estructura raíz

```json
{
  "schema_version": "0.1",
  "model_purpose": "initial_semantic_mappings_from_external_gis_layers_to_mushroom_reference_catalogs",
  "important_note": "...",
  "mapping_sources": [],
  "exact_value_mappings": [],
  "vegetation_mappings": [],
  "corine_land_cover_mappings": [],
  "lithology_mappings": [],
  "derived_rules": [],
  "metadata": {}
}
```

## 3. Estado actual

El fichero actual es una base operativa inicial y conservadora. Contiene:

- `mapping_sources`: 4 fuentes conceptuales.
- `exact_value_mappings`: mappings exactos revisables para capas locales activas.
- `vegetation_mappings`: 19 reglas.
- `corine_land_cover_mappings`: 6 reglas.
- `lithology_mappings`: 10 reglas.
- `derived_rules`: 5 reglas.

Todavía no contiene códigos exactos finales de las capas WMS/WFS reales que se usarán en producción. Debe evolucionar cuando se elijan las fuentes GIS concretas.

## 4. `mapping_sources`

Describe fuentes GIS previstas.

Ejemplos conceptuales:

- mapa de hábitats de Cataluña;
- Mapa Forestal de España;
- CORINE Land Cover / Copernicus;
- geología/litología ICGC.

Cada fuente debería tener:

- `id`: identificador interno de fuente;
- `name`: nombre humano;
- `type`: vegetación, cobertura, litología, etc.;
- `notes`: comentarios.

## 5. `exact_value_mappings`

Traduce valores exactos de una capa GIS local a IDs internos del catalogo. Es el
contrato preferente para capas activas del laboratorio porque evita depender de
textos libres o coincidencias aproximadas.

Cada entrada se identifica por:

- `source_id`: fuente GIS interna, por ejemplo `mvc50` o `geology_50000`;
- `field`: atributo de la capa, por ejemplo `LLFISCAT_t`, `LLVA_Subst` o
  `Codi`;
- `raw_value`: valor bruto exacto encontrado en la capa.

Ejemplo:

```json
{
  "source_id": "mvc50",
  "field": "LLVA_Subst",
  "raw_value": "Silici",
  "mapped_soil_tendency_ids": ["soil_siliceous"],
  "confidence": "high",
  "review_status": "accepted",
  "notes": "Exact MVC50 substrate value."
}
```

Los destinos solo pueden ser listas de IDs existentes en
`mushroom_reference_catalogs.json`:

- `mapped_host_ids` contra `host_taxa`;
- `mapped_forest_type_ids` contra `forest_types`;
- `mapped_habitat_feature_ids` contra `habitat_features`;
- `mapped_lithology_ids` contra `lithology_types`;
- `mapped_soil_tendency_ids` contra `soil_types`.

### Estados de revision

`review_status` tiene un contrato operativo cerrado:

- `accepted`: valor revisado y usable. Puede emitir IDs internos.
- `pending_review`: valor persistido para no perderlo, pero todavia pendiente
  de decision. Puede guardarse sin IDs internos o con IDs propuestos, pero no
  emite salida computable hasta pasar a `accepted`.
- `ignored`: valor revisado y descartado. No emite IDs internos, pero queda
  persistido para que no vuelva a aparecer como candidato pendiente.

El reconstructor GIS no modifica este fichero. Solo lee los mappings existentes,
aplica IDs validos de entradas `accepted` y genera candidatos temporales para los
valores sin mapping. Las entradas `pending_review` e `ignored` quedan como
valores conocidos sin salida computable. La pantalla `GIS mappings` es la que
persiste entradas nuevas o actualiza entradas existentes.

## 6. `vegetation_mappings`

Traduce clases de vegetación, bosque o hábitat a:

- `mapped_host_ids`;
- `mapped_forest_type_ids`;
- `mapped_habitat_feature_ids`.

Ejemplo conceptual:

```json
{
  "source_patterns": ["pi negre", "Pinus uncinata", "pino negro"],
  "mapped_host_ids": ["host_pinus_uncinata"],
  "mapped_forest_type_ids": ["forest_subalpine_pine"],
  "confidence": "high"
}
```

### `source_patterns`

Lista de textos o patrones que pueden aparecer en atributos GIS. En el futuro conviene sustituir o complementar estos patrones con códigos exactos de capa.

### `confidence`

Indica fiabilidad del mapeo:

- `high`: mapeo directo y claro.
- `medium`: mapeo razonable, pero puede depender del contexto.
- `low`: mapeo tentativo.

## 7. `corine_land_cover_mappings`

Traduce clases generales de cobertura del suelo.

CORINE es útil para contexto amplio, pero suele ser demasiado general para identificar especies arbóreas concretas.

Ejemplo:

```text
CORINE: coniferous forest
↓
forest_mixed_conifer
```

No debería tener el mismo peso que una capa de vegetación detallada.

## 8. `lithology_mappings`

Traduce clases litológicas o geológicas a:

- `mapped_lithology_ids`;
- `mapped_soil_tendency_ids` como tendencia edáfica derivada.

Ejemplo:

```json
{
  "source_patterns": ["limestone", "caliza", "calcària"],
  "mapped_lithology_ids": ["lith_limestone"],
  "mapped_soil_tendency_ids": ["soil_calcareous", "soil_basic"],
  "confidence": "high"
}
```

La relación litología → suelo es una aproximación. Debe tratarse como tendencia, no como certeza.

En el laboratorio GIS, estas reglas pueden usarse para generar sugerencias de
revision desde descripciones oficiales de geologia. Una sugerencia no equivale a
un mapping `accepted`: debe conservar el `Codi` y la `Descripcio` oficiales,
mostrar los IDs propuestos y requerir revision humana antes de emitir salida
computable. Las reglas de geologia deben usar conceptos reutilizables
internacionalmente (`lith_basaltic`, `lith_volcanic`, `lith_fine_clastic`,
etc.), con aliases multilingues solo como ayuda para reconocer textos de capas
externas.

## 8.1 `batch_suggestion_rules`

`batch_suggestion_rules` define como el laboratorio batch debe generar
preselecciones revisables para valores GIS nuevos. Es una capa declarativa: el
codigo Python no contiene equivalencias de dominio como `Pi roig ->
host_pinus_sylvestris`; solo lee reglas, valida IDs contra
`mushroom_reference_catalogs.json` y escribe sugerencias temporales.

Ejemplo conceptual:

```json
{
  "rule_id": "geology_50000_lithology_text_patterns",
  "source_id": "geology_50000",
  "field": "Codi",
  "match_fields": ["Descripcio", "Descripcio_protolit"],
  "source_section": "lithology_mappings",
  "auto_accept_confidences": ["high"]
}
```

Reglas:

- el catalogo maestro no debe copiar clases de cada capa GIS;
- el catalogo maestro solo debe contener conceptos internos estables;
- las reglas batch traducen valores de capas hacia esos conceptos;
- `auto_accept_confidences` declara que niveles de confianza pueden tratarse
  como `accepted` en la reconstruccion batch; coincidencias fuera de esa lista
  quedan como `pending_review`;
- si una capa revela un concepto interno util que falta, se anade una vez al
  catalogo con labels y aliases;
- si una clase externa no encaja en conceptos utiles, debe quedar sin sugerencia
  o como `ignored`, no forzarse.

Esto evita el bucle de mantenimiento de copiar miles de codigos externos al
catalogo: los codigos externos viven en `exact_value_mappings` cuando se revisan,
y el catalogo conserva solo vocabulario del modelo.

## 9. `derived_rules`

Reglas que combinan varias señales para inferir IDs internos.

Ejemplos conceptuales:

```text
Si litología = caliza → suelo probable = calcareous/basic
Si litología = granito/esquisto → suelo probable = siliceous/acidic
Si vegetación = ribera → feature_riparian
Si hay nieve/deshielo → feature_snowmelt
```

Las reglas derivadas deben tener prioridad menor que datos directos de una capa especializada.

## 10. Uso en el flujo de predicción

Para cada celda:

1. Leer atributos GIS crudos.
2. Ejecutar reglas de mapeo por fuente.
3. Obtener IDs internos candidatos.
4. Resolver conflictos y duplicados.
5. Asignar confianza a cada ID mapeado.
6. Comparar esos IDs con afinidades de la especie.
7. Calcular el componente de hábitat.

Ejemplo:

```text
Entrada celda:
- vegetación: "Pineda de pi roig"
- litología: "granito"
- altitud: 1450 m

Mapeo:
- host_pinus_sylvestris
- forest_montane_pine
- lith_granite
- soil_acidic / soil_siliceous como inferencia

Perfil Boletus pinophilus:
- host_pinus_sylvestris affinity 1.0
- forest_montane_pine affinity alta
- lith_granite affinity positiva

Resultado:
- hábitat favorable
```

## 10. Resolución de conflictos

Una celda puede recibir señales contradictorias:

```text
vegetación: pinar
litología: caliza
perfil especie: pinar ácido/silíceo
```

El motor debe:

1. Mantener ambas señales.
2. Aplicar afinidades positivas/negativas.
3. Considerar la confianza del mapeo.
4. No sobrescribir datos directos con inferencias débiles.

## 11. Relación con catálogos

Todos los IDs emitidos por este fichero deben existir en `mushroom_reference_catalogs.json`.

Validaciones necesarias:

- `mapped_host_ids[]` existe en `catalogs.host_taxa`.
- `mapped_forest_type_ids[]` existe en `catalogs.forest_types`.
- `mapped_soil_tendency_ids[]` existe en `catalogs.soil_types`.
- `mapped_lithology_ids[]` existe en `catalogs.lithology_types`.
- `mapped_habitat_feature_ids[]` existe en `catalogs.habitat_features`.
- `derived_rules[].outputs[]` existe en alguno de los catálogos internos cuando el valor es un ID de catálogo.

## 12. Evolución hacia producción

Cuando se elijan capas reales:

1. Identificar nombre de fuente y URL/servicio.
2. Ver qué campo contiene código o descripción de clase.
3. Añadir `source_code` o `source_class_id` si existe.
4. Mantener `source_patterns` como fallback.
5. Añadir tests con ejemplos reales de atributos GIS.
6. Marcar confianza de cada mapeo.

## 13. Reglas para Codex

Codex no debe asumir que los patrones actuales son definitivos. Debe tratarlos como base inicial. Si se integra una capa concreta, debe añadir mapeos exactos sin romper los IDs internos existentes.
