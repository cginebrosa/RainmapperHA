# Aplicacion de fuentes literarias a perfiles de setas

## Objetivo

`scripts/apply-mushroom-literature-source.py` aplica una fuente literaria
normalizada a las afinidades ecologicas de `mushroom_profiles.json`.

La herramienta existe para limpiar y reforzar la ficha de especies sin convertir
observaciones, GIS/DEM o modelos aprendidos en cambios automaticos de perfil.

Por defecto actua sobre la copia viva que usa la aplicacion:

- en desarrollo local: `docker-data/mushroom-data/mushroom_profiles.json`;
- en Home Assistant: `/share/rainmapper/mushroom-data/mushroom_profiles.json`.

Los defaults versionados de `mushroom-data/` son semilla/packaging. Solo se
tocan explicitamente con `--versioned-defaults` o pasando `--profiles`.

## Contrato de entrada

La fuente debe ser un JSON normalizado con:

- `source_id`;
- `species[]`;
- `species[].species_id`;
- listas opcionales:
  - `host_ids`;
  - `forest_type_ids`;
  - `soil_tendency_ids`;
  - `habitat_feature_ids`;
  - `catalog_gap_candidates`.

La primera fuente aplicada es:

`docs/mushrooms/literature/marc-estevez-v0-source-normalized.json`

## Regla aplicada para Marc Estevez

Marc Estevez se trata como fuente documental fiable. Si la fuente normalizada
lista una afinidad para una especie, el script la escribe como:

```json
{
  "relationship": "primary",
  "source_ids": ["literature_marc_estevez"]
}
```

Si la afinidad ya existia, se conserva su fila, se activa para v0 si estaba
aparcada y se actualiza `relationship` a `primary`. Si la afinidad no existia,
se anade con `affinity: 0.0` y `v0_placeholder: true` para mantener el schema
rico sin inventar pesos numericos.

## Lo que no hace

- No lee observaciones.
- No lee GIS/DEM.
- No reconstruye modelo aprendido.
- No cambia pesos numericos como evidencia productiva.
- No promociona automaticamente evidencia local a perfiles.
- No crea nuevos catalogos; los IDs deben existir ya en
  `mushroom_reference_catalogs.json`.

## Reutilizacion con otra fuente

Para aplicar otra fuente literaria:

1. Crear un JSON normalizado con el mismo contrato de entrada.
2. Anadir un alias legible en `SOURCE_ID_ALIASES` si se quiere mostrar un badge
   corto en UI.
3. Ejecutar primero en seco:

```bash
python3 scripts/apply-mushroom-literature-source.py --source ruta/fuente.json
```

4. Revisar el reporte generado en:

`tmp/mushroom-lab/output/reports/mushroom_literature_source_apply.md`

5. Aplicar solo si el diff es defendible:

```bash
python3 scripts/apply-mushroom-literature-source.py --source ruta/fuente.json --apply
```

Para preparar tambien los defaults versionados de la imagen, ejecutar el mismo
flujo de forma explicita:

```bash
python3 scripts/apply-mushroom-literature-source.py --versioned-defaults --source ruta/fuente.json --apply
```

6. Validar:

```bash
python3 scripts/validate-mushroom-data.py --data-dir docker-data/mushroom-data
python3 scripts/validate-mushroom-data.py
python3.11 -m unittest tests.test_mushroom_literature_source_apply tests.test_mushroom_profile_v0_candidate_builder
```

## Politica de conflicto

La herramienta actual es deliberadamente simple: una fuente literaria listada
marca afinidad `primary`. Si en el futuro una fuente trae fuerza explicita por
ID, debe ampliarse el normalizador de fuente antes de aplicar relaciones mas
finas. No se deben deducir relaciones debiles a partir de texto libre sin
haberlas normalizado previamente.
