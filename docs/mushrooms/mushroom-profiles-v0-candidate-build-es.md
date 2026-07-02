# Build y promocion de perfiles v0

Fecha: 2026-07-02.

Este documento describe el flujo usado para convertir la fuente normalizada de
Marc Estevez en perfiles operativos v0 dentro de la estructura rica existente de
`mushroom-data/mushroom_profiles.json`.

## Principio

La v0 no reemplaza el schema rico. Usa la misma estructura completa de perfiles,
pero solo considera activos estos bloques:

- ecologia amplia: hosts, tipo de bosque, suelo amplio y rasgos de habitat;
- fenologia: meses principales/secundarios y patrones de temporada;
- topografia amplia: altitud minima/maxima y orientaciones si existen;
- estado de revision/calibracion.

Quedan aparcados para v0:

- `weather_model`;
- `scoring_weights`;
- `ecology.lithology_affinities`;
- `phenology.fruiting_delay_after_rain_days`;
- `topography.altitude_optimal_*`;
- umbrales meteorologicos y minimos de observaciones.

## Script

Comando:

```bash
python3 scripts/build-mushroom-profile-v0-candidate.py
```

Salidas por defecto:

- `tmp/mushroom-lab/working/profiles/mushroom_profiles_v0_candidate.json`
- `tmp/mushroom-lab/working/profiles/mushroom_reference_catalogs_v0_overlay_proposal.json`
- `tmp/mushroom-lab/working/profiles/mushroom_reference_catalogs_v0_promoted_candidate.json`
- `tmp/mushroom-lab/output/reports/mushroom_profile_v0_candidate_build.md`

El script sigue escribiendo primero en `tmp/` para permitir auditoria. La
promocion productiva se hizo generando perfiles y catalogos en el mismo cambio:

```bash
python3 scripts/build-mushroom-profile-v0-candidate.py \
  --include-catalog-gaps \
  --output-profiles mushroom-data/mushroom_profiles.json \
  --output-catalogs mushroom-data/mushroom_reference_catalogs.json
```

## Resultado actual

Estado tras la promocion actual:

- perfiles productivos actuales: 21;
- especies normalizadas en fuente v0: 21;
- perfiles productivos cubiertos por la fuente: 21;
- especies pendientes de promover desde la fuente: 0;
- gaps de catalogo v0 promovidos y referenciados: 12 IDs nuevos, 32
  referencias desde perfiles.

Las especies incorporadas en esta promocion fueron:

- `cantharellus_lutescens`
- `craterellus_cornucopioides`
- `lactarius_deliciosus`
- `lactarius_salmonicolor_quieticolor_group`
- `lepista_nuda`
- `macrolepiota_procera`
- `marasmius_oreades`
- `russula_virescens`
- `tricholoma_terreum`
- `tuber_melanosporum`

## Placeholders

El schema rico actual exige campo numerico `affinity` en cada afinidad. Para
relaciones nuevas que vienen de la fuente normalizada, el candidato usa:

```json
{
  "relationship": "source",
  "affinity": 0.0,
  "v0_placeholder": true
}
```

Esto no es un peso ni un parametro del predictor v0. La proyeccion v0 definida
en `rainmapper_core/mushroom_profile_v0.py` ignora los valores numericos y solo
usa `id` + `relationship`.

Las afinidades enriquecidas antiguas que no proceden de la fuente v0 se
conservan en el perfil rico con `v0_active: false`. La proyeccion v0 las ignora,
pero la UI avanzada y el historico del perfil no pierden ese trabajo.

Cuando se actualiza la altitud amplia desde fuente, el script normaliza
`topography.altitude_optimal_*` solo para mantener el schema rico ordenado y
validable. Esos campos siguen aparcados para v0.

## Catalogos

Los gaps de catalogo v0 ya estan promovidos a
`mushroom-data/mushroom_reference_catalogs.json` y referenciados desde los
perfiles que los solicitaron mediante `catalog_gap_candidates`.

Entradas promovidas:

- `habitat_features`: `feature_blueberry_understory`,
  `feature_calcicolous_shrubland`, `feature_disturbed_soil`,
  `feature_heath_rockrose_understory`, `feature_mature_forest`,
  `feature_mediterranean_shrubland`, `feature_moist_forest`,
  `feature_organic_debris`, `feature_shaded_slope`;
- `host_taxa`: `host_corylus_avellana`, `host_quercus_coccifera`,
  `host_quercus_faginea`.

La regla para gaps futuros sigue siendo la misma: no anadir IDs nuevos al
catalogo productivo si no quedan referenciados por perfiles productivos o GIS
mappings en el mismo cambio.

## Validacion

Pruebas que cubren este flujo:

```bash
python3 -m unittest tests.test_mushroom_profile_v0_candidate_builder
```

El test comprueba que el candidato:

- contiene 21 especies;
- no deja especies de la fuente pendientes de promover;
- no separa `lactarius_salmonicolor` y `lactarius_quieticolor`;
- valida sin errores estructurales contra los catalogos actuales;
- comprueba que los gaps de catalogo promovidos existen y estan referenciados
  por perfiles.
