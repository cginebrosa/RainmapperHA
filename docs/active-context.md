# Active Context

Contexto operativo actual para continuar RainmapperHA sin cargar toda la
historia antigua. Si una tarea necesita mas detalle, seguir las referencias
indicadas.

## Regla de mantenimiento

Este documento debe ser una ventana operativa, no un historico acumulativo.
Cuando entre informacion nueva, debe salir, resumirse o archivarse informacion
que ya no guie el trabajo inmediato. Las tareas cerradas, descartadas o antiguas
no deben quedarse indefinidamente en `docs/todo.md`; mover su memoria util a
`docs/project-archive.md`, `docs/decisions.md` o al documento largo que
corresponda.

## Estado real del repo

- Ruta activa: `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Ultimo release funcional pusheado: `11a04e6 Release Home Assistant 0.2.187`.
- Version HA: `0.2.187`.
- Imagen HA publicada/verificada: `ghcr.io/cginebrosa/rainmapperha:0.2.187`,
  digest multi-arch
  `sha256:1fc5a0eb46659b8ca9496935bb3c3491a424e9dac277eec7823ddd12983f19be`.
- `latest` apunta al mismo digest que `0.2.187`.
- El servicio local HA UI se prueba con `rainmapper-local/docker-compose.yml`,
  puerto `127.0.0.1:8101`, montando `docker-data/` como `/share/rainmapper`.

## Foco activo

El foco activo combina el modulo de setas y la medicion de rendimiento del
backend `run_all`:

- Observaciones reales con hosts, bosque, suelo, habitat y orientacion
  observados.
- Reconstruccion v0 desde observaciones: GIS/DEM, meteorologia, features y
  modelo aprendido.
- Comparacion visual en `Parametros`: perfil, evidencia v0 y valores emergentes.
- Separacion clara de origenes: perfil/literatura, Campo, GIS/DEM.
- Estado de modelo desactualizado y reconstruccion manual desde UI.
- Diagnostico de tiempos reales por proceso/fase tras detectar `run_all` en
  torno a 12 minutos en RPi.

El resto de visores esta estable salvo que una tarea lo toque explicitamente.

## Rendimiento backend

`0.2.184` corrigio los contadores `start_count/end_count` para que sean
thread-local y no mezclen tiempos entre fuentes paralelas. Tambien publica en
`source_status.json` un desglose AEMET por fases:

- `fetch_seconds`
- `normalize_seconds`
- `read_hourly_seconds`
- `merge_hourly_seconds`
- `read_stations_seconds`
- `station_catalog_seconds`
- `station_enrichment_seconds`
- `build_daily_seconds`
- `read_daily_seconds`
- `merge_daily_seconds`
- `write_outputs_seconds`
- `total_seconds`

El panel HA muestra ese desglose en la tarjeta AEMET. El `run_all` de HA
`0.2.184` mostro que AEMET tardaba `5m38s` y que el coste dominante era
`build_daily_seconds` con `4m32s`. `0.2.185` reemplaza ese bucle Python por
agregacion vectorizada con pandas; en local, 125k filas horarias se agregaron en
`1.23s`.

`0.2.186` publica en HA los desgloses de fase para Meteocat, Meteoclimatic y
Wunderground. Con 4 threads en RPi, el `run_all` de `0.2.186` mostro:

- Wunderground `scrape_seconds=419.6s`: cuello de red/servicio remoto.
- Meteoclimatic `build_daily_seconds=67.9s`: bucle Python por estacion/dia.
- Tomap `last-rains duration=49.0s`: agregacion Python por grupo.
- Meteocat y AEMET ya quedan muy condicionados por escritura CSV grande.

`0.2.187` vectoriza el rebuild diario de Meteoclimatic y la agregacion Tomap
last-rains. En local, Meteoclimatic diario con datos reales paso a `0.066s` y
Tomap completo a `10.2s` (`last-rains=6.7s`). En el siguiente `run_all` en RPi
hay que confirmar la mejora real; lo esperable es que siga dominando
Wunderground salvo que se cambie la estrategia/concurrencia del scrape.

## Fuente de verdad operativa

Para setas, en local:

```text
docker-data/mushroom-data/
```

En HA:

```text
/share/rainmapper/mushroom-data/
```

Las capas GIS/DEM pesadas para reconstruccion de contexto no deben vivir bajo
`/share` porque entrarian en backups completos de Home Assistant. En HA deben
colocarse en:

```text
/media/rainmapper/mushroom-GIS/
```

`rainmapper_core/mushroom_paths.py` centraliza rutas. Los artefactos v0
operativos deben vivir en `mushroom-data`, no en `mushroom-lab/working`.

Archivos operativos principales:

- `mushroom_profiles.json`
- `mushroom_observations.json`
- `mushroom_reference_catalogs.json`
- `mushroom_gis_mappings.json`
- `mushroom_labels.json`
- `mushroom_gis_observation_reconstruction.json`
- `mushroom_observations_weather_features.json`
- `mushroom_observation_features_v0.json`
- `mushroom_model_v0.json`
- `mushroom_model_v0_state.json`
- `reports/`

`tmp/mushroom-lab/` queda para pruebas locales explicitas, QGIS, fotos y
artefactos exploratorios.

## Modulos relevantes ahora

UI y rutas:

- `rainmapper-app/app/web_server.py`: rutas, POST, jobs, orquestacion.
- `rainmapper-app/app/mushroom_profiles_ui.py`: pantallas grandes de especies,
  observaciones, evidencia y parametros.
- `rainmapper-app/app/mushroom_catalogs_ui.py`: catalogos.
- `rainmapper-app/app/mushroom_gis_mappings_ui.py`: mappings GIS.

Core setas:

- `rainmapper_core/mushroom_paths.py`: rutas canonicas.
- `rainmapper_core/mushroom_observations.py`: helpers comunes de guardado y
  campos derivados de observaciones.
- `rainmapper_core/mushroom_model_state.py`: especies pendientes de reconstruir.
- `rainmapper_core/mushroom_observation_context.py`: contexto GIS/DEM/meteo por
  observacion.
- `rainmapper_core/mushroom_observation_features.py`: features v0 unificadas.
- `rainmapper_core/mushroom_learned_model.py`: modelo v0 descriptivo.
- `rainmapper_core/mushroom_gis_lab.py`: laboratorio/mappings GIS y QGIS.
- `rainmapper_core/mushroom_profile_v0.py`: proyeccion v0 de perfiles ricos.
- `rainmapper_core/mushroom_validation.py`: validacion de datos.

Scripts:

- `mushroom_observation_context_rebuild.sh`
- `mushroom_observation_features_v0_build.sh`
- `mushroom_learned_model_v0_build.sh`
- `mushroom_gis_mappings_rebuild.sh`
- `scripts/apply-mushroom-literature-source.py`
- `scripts/update-mushroom-observation-derived-fields.py`
- `scripts/validate-mushroom-data.py`

## Decisiones vigentes

- `mushroom-data` es la ubicacion operativa estable de setas.
- `mushroom-lab/working` queda historico para el modelo operativo; no mantener
  fallbacks nuevos hacia esa ruta.
- El modelo v0 aprendido no es predictor productivo ni ML final.
- El modelo v0 no modifica `mushroom_profiles.json`.
- Las decisiones en `Evidencia` son estado interno reversible; no aplican
  cambios automaticos.
- Campo y GIS/DEM deben distinguirse en UI y datos.
- Marc Estevez es fuente literaria fiable para afinidades ecologicas. Si una
  afinidad esta normalizada desde Marc, se marca como origen `Marc` y relacion
  principal en perfiles, sin inventar pesos.
- No reintroducir `v0_catalog_gap_promoted` como origen visible.
- No usar litologia fina ni viento como scoring productivo v0 sin evidencia
  suficiente.
- El despliegue futuro a HA debe reemplazar datos micologicos con la copia local
  validada; no mezclar con datos de setas existentes en HA.

## Estado UI setas

### Observaciones

- Captura observaciones positivas/negativas, EXIF, coordenadas, altitud, origen,
  validacion, uso en calibracion y notas.
- Captura opcionalmente:
  - arboles/hosts observados;
  - bosque observado;
  - suelo observado;
  - habitat observado;
  - orientacion observada.
- Calcula campos derivados de fecha como mes/temporada al guardar o importar.
- Alta, edicion, importacion EXIF, archivado/restauracion y cambios relevantes
  marcan especies pendientes en `mushroom_model_v0_state.json`.
- La reconstruccion del modelo v0 se ejecuta en background y muestra progreso,
  porcentaje, tiempo transcurrido y ETA.

Referencia: `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`.

### Parametros

- Tabs internos: `Ecologia`, `Suelos`, `Topografia`, `Fenologia` y
  `Meteorologia`.
- Ecologia/Suelos/Topografia/Fenologia tienen patron de tres columnas:
  1. perfil configurado;
  2. evidencia v0;
  3. valores emergentes.
- Chips de evidencia muestran soporte y origenes cuando existen: `Campo`,
  `GIS/DEM`, `Marc`.
- `Campo` puede calcularse desde observaciones guardadas; `GIS/DEM` y agregados
  del modelo requieren reconstruccion.
- Pendiente: cerrar `Meteorologia` con el mismo patron de comparacion.

Referencia: `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`.

### Evidencia

- Tiene subpestanas Hosts/bosques, Suelos/habitat, Meteorologia y Modelo
  aprendido.
- Hosts/bosques y Suelos/habitat deben contar evidencia local unificada cuando
  exista: Campo + GIS/DEM, preservando origenes visibles por item.
- Sigue pendiente redisenar la vista para separar mas explicitamente:
  - declarado/observado por campo;
  - reconstruido por GIS/DEM;
  - coincidencias con perfil;
  - decisiones internas.

## Modelo v0 aprendido

Flujo reproducible completo:

```bash
./mushroom_observation_context_rebuild.sh
./mushroom_observation_features_v0_build.sh
./mushroom_learned_model_v0_build.sh
```

La UI puede reconstruir desde el boton de modelo desactualizado. El rebuild
puede limitarse a especies pendientes cuando sea posible, pero no es
incremental fila a fila: regenera los artefactos necesarios para esas especies.

El modelo resume:

- observaciones usadas, positivas y negativas;
- soporte categorico por hosts, bosques, suelos y habitat;
- procedencia de valores (`field`/Campo, `gis`/GIS);
- rangos numericos de altitud y meteorologia;
- gaps de datos.

No resume todavia todos los parametros productivos ni fija umbrales.

## Literatura y origenes

Marc Estevez:

- Resumen humano: `docs/mushrooms/literature/marc-estevez-species-conclusions-es.md`.
- Fuente normalizada: `docs/mushrooms/literature/marc-estevez-v0-source-normalized.json`.
- Aplicador: `scripts/apply-mushroom-literature-source.py`.
- Documento operativo: `docs/mushrooms/mushroom-literature-source-apply-es.md`.

Origenes que deben entenderse en UI:

- `Marc`: fuente literaria aplicada al perfil.
- `Campo`: valor declarado por el observador en observaciones.
- `GIS/DEM`: valor reconstruido desde capas geograficas o DEM.
- `Original` puede existir como contexto historico de perfiles base, pero no
  debe confundirse con evidencia fuerte si no esta respaldado por Marc, Campo o
  GIS/DEM.

## Bugs, riesgos y limitaciones abiertas

- `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md` y
  `docs/mushrooms/mushroom-predictor-design-es.md` todavia contienen muchas
  rutas antiguas `docker-data/mushroom-lab/working`; tienen nota de vigencia,
  pero no deben leerse como contrato operativo actual.
- `docs/todo.md` contiene backlog largo con tareas antiguas. Usarlo como
  referencia, no como lista estricta de arranque.
- `Evidencia` necesita rediseño semantico: aunque los titulos visibles ya no
  dicen GIS, la vista todavia debe separar mejor Campo, GIS/DEM, coincidencias
  con perfil y decisiones.
- `Parametros > Meteorologia` no esta cerrado en el patron de tres columnas.
- El modelo v0 puede quedar desactualizado tras editar observaciones hasta que
  el usuario pulse reconstruccion.
- Pocas observaciones por especie: no presentar emergentes como verdad fuerte.
- La UI debe seguir preservando datos no visibles al guardar formularios con
  tabs.
- `mushroom-GIS/` contiene capas pesadas ignoradas por Git y no debe
  versionarse; en HA la copia operativa debe estar bajo `/media/rainmapper/`
  para no inflar backups de `/share`.

## Proximos pasos recomendados

1. Validar visualmente con modelo reconstruido la pantalla `Parametros`,
   especialmente origenes Campo/GIS/DEM/Marc.
2. Cerrar `Parametros > Meteorologia` con el mismo patron de tres columnas.
3. Redisenar `Evidencia` para separar Campo, GIS/DEM y coincidencias con perfil.
4. Validar en HA `0.2.183`: el modal de reconstruccion v0 debe refrescar
   correctamente bajo ingress y el boton rojo debe contar solo especies
   pendientes que sigan teniendo observaciones elegibles actuales.
5. Diseñar promocion manual de candidatos a perfil, sin escritura automatica.
6. Mantener o mejorar documentacion corta si se detectan nuevas contradicciones
   entre documentos largos y codigo.

## Validaciones recientes conocidas

Ultimo cierre conocido:

- `python3 scripts/validate-mushroom-data.py` OK, 0 errores, 6 warnings
  conocidos.
- `python3.11 -m py_compile` de UI/core v0 OK.
- `python3.11 -m unittest` de rutas, estado, observaciones, GIS, contexto,
  features, modelo, Marc, validator y web auth OK, 114 tests.
- `git diff --check` OK.

Repetir validaciones relevantes antes de commit.

## Dudas o contradicciones detectadas

- Algunos documentos largos conservan salidas antiguas bajo
  `docker-data/mushroom-lab/working`. La decision vigente es `mushroom-data`.
- `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md` todavia dice
  en una seccion que fenologia/clima no se comparan todavia; el codigo y el
  contexto reciente ya avanzaron hacia tres columnas en Fenologia y pendiente en
  Meteorologia. Leerlo como historia de rediseño, no como estado completo.
- `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`
  mantiene "Conectar observaciones al extractor meteorologico local" como
  pendiente; el flujo v0 ya tiene context/features/modelo. Esa frase queda
  historica o parcialmente obsoleta.
- `docs/decisions.md` y `docs/todo.md` son cronologicos; entradas antiguas de
  versiones 0.2.150-0.2.179 no deben desplazar el estado activo 0.2.180.
