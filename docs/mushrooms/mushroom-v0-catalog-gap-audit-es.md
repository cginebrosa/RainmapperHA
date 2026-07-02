# Auditoria de gaps de catalogos para perfiles v0

Fecha: 2026-07-02.

Objetivo: comprobar si `mushroom_reference_catalogs.json` ya permite expresar
la v0 operativa sin tirar catalogos ni perfiles existentes.

Conclusion corta: los catalogos iniciales cubrian la mayor parte de la v0. No
hizo falta rehacerlos. Los gaps amplios detectados en esta auditoria se
promovieron despues a `mushroom_reference_catalogs.json` junto con referencias
desde los perfiles v0, para evitar IDs de catalogo sin uso.

## Ya cubierto

### Hosts y vegetacion

El catalogo `host_taxa` ya cubre bien:

- pinos principales: `Pinus sylvestris`, `P. uncinata`, `P. halepensis`,
  `P. nigra`, `P. pinea`, `P. pinaster`;
- abeto blanco: `Abies alba`;
- haya: `Fagus sylvatica`;
- encina y alcornoque: `Quercus ilex`, `Quercus suber`;
- robles genericos: `Quercus spp.`;
- castano: `Castanea sativa`;
- abedules: `Betula spp.`;
- ribera generica: `Populus spp.`, `Fraxinus spp.`, `Ulmus spp.`;
- vegetacion herbacea de prados: `host_grassland_vegetation`.

Para v0 esto permite evitar una explosion de especies acompanantes. Cuando la
fuente menciona robles mediterraneos concretos, `host_quercus_spp` y los tipos
de bosque mediterraneo pueden ser suficientes salvo que observaciones locales
justifiquen separar mas.

### Bosques y habitats amplios

`forest_types` ya cubre:

- pinares montanos, subalpinos, mediterraneos y calcarios;
- abetales, hayedos, frondosas caducifolias;
- encinar, alcornocal, castañar y bosque mixto;
- ribera;
- prados/pastos;
- borde de bosque;
- bosque quemado o perturbado.

### Suelo amplio

`soil_types` ya cubre la v0 casi completa:

- acido, ligeramente acido, neutro, basico;
- calcario, fuertemente calcario, siliceo;
- arenoso, franco, franco-arenoso;
- humifero/rico en materia organica;
- humedo, bien drenado, encharcado, muy seco;
- yesifero.

Gap menor: no existe `soil_variable` como forma explicita de decir "sin filtro
edafico". Puede no ser necesario si el perfil omite afinidades de suelo, pero
seria util para UI/explicacion.

### Temporada

`season_patterns` cubre primavera, verano, otono, final de otono, invierno suave,
deshielo y post-perturbacion. Puede bastar para v0.

## Gaps candidatos

Estos IDs no deben anadirse automaticamente sin revisar labels y uso, pero son
los candidatos mas claros para cargar perfiles v0 desde la fuente estructurada.

### `soil_types`

- `soil_variable`: indiferente o variable, para especies donde la fuente dice
  que el pH/sustrato no debe filtrar.

### `habitat_features`

- `feature_mature_forest`: bosque maduro. Aparece en boletos/rossinyol como
  rasgo ecologico relevante, aunque GIS v0 no lo mida bien todavia.
- `feature_moist_forest`: bosque humedo. Es mas general que ribera o musgo y
  aparece en trompeta, russula, camagroc y otros.
- `feature_shaded_slope`: obaga/umbria. Muy repetido para especies tardias,
  montanas o sensibles al calor.
- `feature_warm_lowland`: tierra baja calida/solana litoral. Util para especies
  mediterraneas termofilas.
- `feature_mediterranean_shrubland`: matorral mediterraneo acompanante.
- `feature_calcicolous_shrubland`: matorral calcicola acompanante.
- `feature_heath_rockrose_understory`: brezos/jaras/brecina como senal de
  sotobosque acido/siliceo.
- `feature_blueberry_understory`: arandano como senal de alta montana humeda y
  acida.
- `feature_organic_debris`: hojarasca, restos vegetales, pinochas o materia
  organica visible para saprofitas.
- `feature_disturbed_soil`: terreno removido/alterado. `habitat_disturbed_forest`
  existe como tipo amplio, pero Morchella necesita el rasgo de suelo removido
  incluso fuera de bosque.

### `host_taxa`

No bloquear v0 por estas ausencias. Posibles candidatos futuros:

- `host_corylus_avellana`: avellano, relevante sobre todo para `Tuber melanosporum`.
- `host_quercus_faginea`, `host_quercus_pubescens_or_humilis`,
  `host_quercus_coccifera`: si se decide separar robles mediterraneos en vez de
  usar `host_quercus_spp`.
- `host_arbutus_unedo`, `host_juniperus_spp`, `host_buxus_spp`: mejor tratarlos
  inicialmente como acompanantes/habitat, no como host principal de v0.

## Estado tras promocion

Promovidos a catalogo productivo y referenciados desde perfiles:

- `host_corylus_avellana`
- `host_quercus_faginea`
- `host_quercus_coccifera`
- `feature_mature_forest`
- `feature_moist_forest`
- `feature_shaded_slope`
- `feature_mediterranean_shrubland`
- `feature_calcicolous_shrubland`
- `feature_heath_rockrose_understory`
- `feature_blueberry_understory`
- `feature_organic_debris`
- `feature_disturbed_soil`

## Recomendacion historica

1. No modificar catalogos aun de forma masiva.
2. Anadir primero solo `soil_variable` y los `habitat_features` que se usen en
   perfiles v0 reales.
3. Mantener los hosts acompanantes como notas o rasgos de habitat hasta que haya
   necesidad clara de IDs.
4. Revisar `mushroom_gis_mappings.json` para que MVC50 y geologia emitan
   `mapped_soil_tendency_ids`, `mapped_host_ids`, `mapped_forest_type_ids` y
   `mapped_habitat_feature_ids` compatibles con estos campos.
