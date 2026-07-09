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
- Ultimo commit/release HA publicado: `50714ed Release Home Assistant 0.2.193`.
- Version HA del repo: `0.2.193`.
- Imagen HA publicada/verificada: `ghcr.io/cginebrosa/rainmapperha:0.2.193`
  y `latest`, digest multi-arch
  `sha256:9cbf3327a732103577fed0273dc6e6824ebc3a8c191fc35715f5248c1b7b23d9`.
- El servicio local HA UI se prueba con `rainmapper-local/docker-compose.yml`,
  puerto `127.0.0.1:8101`, montando `docker-data/` como `/share/rainmapper`.

## Foco activo

El foco activo vuelve a estar principalmente en el modulo de setas. La medicion
de rendimiento de `run_all` queda como seguimiento puntual:

- Observaciones reales con hosts, bosque, suelo, habitat y orientacion
  observados.
- Reconstruccion v0 desde observaciones: GIS/DEM, meteorologia, features y
  modelo aprendido.
- Comparacion visual en `Parametros`: perfil, evidencia v0 y valores emergentes.
- Separacion clara de origenes: perfil/literatura, Campo, GIS/DEM.
- Estado de modelo desactualizado y reconstruccion manual desde UI.
- Diagnostico de tiempos reales por proceso/fase tras detectar `run_all` en
  torno a 12 minutos en RPi; tras `0.2.190`, el ultimo dato HA comunicado es
  `08:55`, sin mejora visible atribuible a quitar Bokeh/Leaflet publico.

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
Tomap completo a `10.2s` (`last-rains=6.7s`). En HA, el `run_all` posterior con
3 threads bajo a unos 10 minutos: Wunderground sigue dominando y Bokeh anadia
casi 1 minuto en la fase de mapas.

La generacion/publicacion legacy en `/config/www` queda controlada por
`publish_to_www`. Con `publish_to_www: false` se omiten Bokeh/Google Maps,
`/local/Plots`, Leaflet publico y el heatmap/MapLibre publico antiguo; Tomap,
GeoJSON en `PublicData` y MapLibre protegido se siguen generando. Si hiciera
falta reactivar ese legado, cambiar esa opcion a `true`. `0.2.190` publica este
contrato y deja `publish_to_www: false` por defecto.

El usuario valida que `0.2.190` funciona en HA. El ultimo `run_all` comunicado
queda en `08:55`. El `source_status.json` de ese run (`2026-07-08T17:07:58`)
muestra:

- Meteoclimatic: `121.1s`; mayores costes `fetch_seconds=30.5s`,
  `write_incremental_seconds=17.7s`, `read_observations_seconds=13.0s` y
  `upsert_incremental_seconds=12.9s`.
- Meteocat: `119.1s`; domina escritura/upsert CSV:
  `write_incremental_seconds=49.4s` y `upsert_incremental_seconds=32.7s`.
- AEMET: `125.8s`; domina `write_outputs_seconds=46.5s` y
  `build_daily_seconds=26.1s`.
- Wunderground: `345.8s`; domina `scrape_seconds=338.1s`.

La actualizacion queda en unos `7:45` desde el primer `started_at` al
`generated_at`; frente al `run_all` total de `08:55`, mapas/otros procesos
quedan alrededor de `1:10`. No se observa una mejora significativa por retirar
la publicacion legacy publica porque el tiempo restante esta en Wunderground,
escrituras/upserts de CSV grandes y Tomap/GeoJSON protegido. Salvo que se quiera
reducir cobertura o cambiar la estrategia de Wunderground, el frente de
rendimiento queda practicamente agotado para optimizaciones de bajo riesgo.

`0.2.189` corrige el guardado parcial desde `Parametros` v0 de especies: los
campos no renderizados/ausentes en el formulario se preservan y ya no se
sobrescriben con `null`, evitando errores de validacion al cambiar solo
topografia como `altitude_max_m`.

`0.2.191` publica el trabajo de observaciones micologicas con imagenes:
almacenamiento de fotos reducidas en `mushroom-data/media/observation-photos/`,
preview EXIF con foto, fecha/hora, coordenadas, altitud y mapa antes de aplicar
al formulario, aplicacion diferida hasta `Guardar observacion`, miniaturas en
detalle/mapa y modales internos de imagen/EXIF. Tambien incluye compactacion de
tablas de evidencia meteorologica y restauracion de posicion/navegacion al
cerrar modales.

`0.2.192` publica refinamientos posteriores de UI setas: filas de observacion
mas compactas, tarjeta de metadatos de especies dentro de `General`, selector
visible de origen de ubicacion, separacion estricta entre tipo de origen,
origen de ubicacion y origen de altitud, y restauracion del scroll interno de
la lista de Observaciones. En local se reconstruyo
`docker-data/mushroom-data/mushroom_observations.json` comparando fotos
guardadas bajo `mushroom-data/media/` con EXIF: 47 observaciones quedan como
foto/EXIF coincidente y 2 Morchella sin foto quedan manuales. Ese JSON y
`media/` son datos operativos ignorados por git; copiarlos a HA si se quiere
replicar el estado local.

`0.2.193` corrige el `DtypeWarning` de pandas al leer
`Meteoclimatic_observations_incremental.csv`: el historico crudo de
observaciones Meteoclimatic ahora se lee con dtypes explicitos para metadatos
de estacion, ubicacion y altitud, evitando inferencia por chunks sin cambiar el
schema operativo.

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

- Tabs internos v0: `Ecologia`, `Suelos`, `Topografia` y `Fenologia`.
- Ecologia/Suelos/Topografia/Fenologia tienen patron de tres columnas:
  1. perfil configurado;
  2. evidencia v0;
  3. valores emergentes.
- Chips de evidencia muestran soporte y origenes cuando existen: `Campo`,
  `GIS/DEM`, `Marc`.
- `Campo` puede calcularse desde observaciones guardadas; `GIS/DEM` y agregados
  del modelo requieren reconstruccion.
- No existe tab interno `Meteorologia` en modo v0; la meteorologia reconstruida
  se revisa desde `Evidencia > Meteorologia` y desde el modelo aprendido.

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
- `Parametros > Fenologia` debe mostrar evidencia observada igual que el resto
  de tabs de Parametros; no debe decir que falta modelo aprendido si otras tabs
  ya muestran evidencia para la especie.
- El modelo v0 puede quedar desactualizado tras editar observaciones hasta que
  el usuario pulse reconstruccion.
- Pocas observaciones por especie: no presentar emergentes como verdad fuerte.
- La UI debe seguir preservando datos no visibles al guardar formularios con
  tabs.
- `mushroom-GIS/` contiene capas pesadas ignoradas por Git y no debe
  versionarse; en HA la copia operativa debe estar bajo `/media/rainmapper/`
  para no inflar backups de `/share`.
- `0.2.190` funciona en HA con `publish_to_www: false`; el rendimiento queda en
  torno a `08:55` para el ultimo `run_all` comunicado. `0.2.191` queda
  pendiente de validacion HA.

## Proximos pasos recomendados

1. Validar visualmente con modelo reconstruido la pantalla `Parametros`,
   especialmente origenes Campo/GIS/DEM/Marc.
2. Redisenar `Evidencia` para separar Campo, GIS/DEM y coincidencias con perfil.
3. Diseñar promocion manual de candidatos a perfil, sin escritura automatica.
4. Solo retomar rendimiento si se decide actuar sobre Wunderground, cobertura
   de estaciones o politicas de actualizacion.

## Validaciones recientes conocidas

Ultimo release validado localmente:

- `./scripts/smoke-test.sh` OK, 208 tests, antes de publicar `0.2.193`.
- `docker buildx imagetools inspect ghcr.io/cginebrosa/rainmapperha:0.2.193`
  OK tras publicar.
- Commit `50714ed` pusheado.

Repetir validaciones relevantes antes de commit.

## Dudas o contradicciones detectadas

- Algunos documentos largos conservan salidas antiguas bajo
  `docker-data/mushroom-lab/working`. La decision vigente es `mushroom-data`.
- `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md` todavia dice
  en una seccion que fenologia/clima no se comparan todavia y puede mencionar
  `Meteorologia` como tab pendiente. Leerlo como historia de rediseño, no como
  estado completo: en v0 las tabs reales de Parametros son Ecologia, Suelos,
  Topografia y Fenologia.
- `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`
  mantiene "Conectar observaciones al extractor meteorologico local" como
  pendiente; el flujo v0 ya tiene context/features/modelo. Esa frase queda
  historica o parcialmente obsoleta.
- `docs/decisions.md` y `docs/todo.md` son cronologicos; entradas antiguas de
  versiones 0.2.150-0.2.192 no deben desplazar el estado activo 0.2.193.
