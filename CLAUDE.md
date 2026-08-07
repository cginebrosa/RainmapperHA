# RainmapperHA — Guía para Claude Code

## Documentos referenciados son obligatorios

**REGLA ESTRICTA:** Cuando el CLAUDE.md o cualquier instrucción activa diga "ver `fichero.md`", "seguir `fichero.md`", "leer `fichero.md`" o similar, leer ese fichero **antes de actuar**. No asumir que recuerdas el contenido de sesiones anteriores. No saltarte la lectura porque el paso parece obvio. Si no has leído el fichero referenciado, no has seguido la instrucción. Saltarse esta regla equivale a ignorar directamente el CLAUDE.md y puede tener consecuencias irreversibles (releases incorrectos, datos corruptos, pasos omitidos). Esta regla no tiene excepciones.

## Preguntas vs. órdenes

**REGLA ESTRICTA:** Cuando el usuario hace una pregunta, responde SOLO con texto. NO ejecutes ninguna herramienta, NO toques ningún fichero, NO ejecutes ningún comando. Espera la confirmación explícita del usuario antes de hacer cualquier acción. Esta regla no tiene excepciones.

## Coordenadas

Las coordenadas de observaciones y fotos van siempre en **decimal WGS84** (ej: `42.063325`, `1.9375444`). Nunca en formato DMS (grados°minutos'segundos").

## Workspace y rama

- Ruta válida: `/Users/carlosginebrosa/Developer/RainmapperHA`
- Rama activa: `inicial`
- No usar la copia antigua de iCloud/Mobile Documents.
- Antes de editar: `pwd && git status --short`

## Lectura obligatoria al arrancar sesión

**REGLA ESTRICTA:** Lee `docs/active-context.md` al inicio de CADA sesión, ANTES de responder a cualquier pregunta o ejecutar cualquier acción. Este fichero contiene el estado real del proyecto: versión HA instalada, pruebas completadas, prioridad inmediata y bloqueos activos. Sin leerlo, cualquier respuesta sobre el estado del proyecto será incorrecta. Esta regla no tiene excepciones.

1. `docs/active-context.md` — **leer primero, siempre** — estado actual, versión instalada, prioridades
2. `docs/codex-start-here.md` — reglas operativas y mapa de documentación

Consultar después según tarea:
- Arquitectura/entrypoints: `docs/architecture.md`
- Pendientes y prioridades: `docs/todo.md`
- Decisiones cronológicas: `docs/decisions.md`
- Seguridad de históricos CSV: `docs/history-safety.md`
- Módulo de setas (si aplica): `docs/mushrooms/` — ver índice abajo

## Estructura del proyecto

```
rainmapper_core/            # lógica Python compartida
  rainmapper.py             # runner principal: descarga + normaliza todas las fuentes
  tomap.py                  # reconstruye CSVs Tomap desde históricos
  geojson.py                # convierte Tomap → GeoJSON para visores web
  bokeh_maps.py             # genera mapas HTML legacy Bokeh/Google Maps
  incremental_upsert.py     # upsert de históricos CSV (clave: Codi Estació + Data Local)
  create_aemet.py           # fuente AEMET (opcional, aislada del runner principal)
  wind.py                   # helpers de viento (conversiones, media circular)
  geocoding.py              # geocodificación Google Maps para metadata de estaciones
  meteoclimatic_history.py  # histórico y deduplicación Meteoclimatic
  mushroom_paths.py         # resolver canónico de rutas del módulo de setas ← usar siempre
  mushroom_store.py         # persistencia JSON de datos de setas
  mushroom_*.py             # módulos del módulo de setas (ver sección específica)
  config/                   # const.py, config.py, config_wunderground.py
  sources/                  # forks locales embebidos (NO son paquetes externos instalados)
    wunderground/           # API diaria + scraper HTML Wunderground
    meteoclimatic_local/    # fork local de la lib Meteoclimatic
    sodapy_local/           # fork local de sodapy para Meteocat/Socrata
  viewers/
    leaflet-viewer/         # visor Leaflet estático (fuente canónica)
    maplibre-viewer/        # visor MapLibre estático (fuente canónica, visor principal)

rainmapper-app/
  config.yaml               # manifiesto del add-on HA (versión, opciones, puertos, imagen)
  Dockerfile                # imagen HA: python:3.11-slim + gdal-bin + ffmpeg + exiftool + core + app
  run.sh                    # entrypoint HA: lee /data/options.json, arranca modo elegido
  DOCS.md                   # documentación de usuario completa
  CHANGELOG.md              # historial de versiones
  app/                      # código específico HA (server-rendered)
    web_server.py           # servidor HTTP principal (puerto 8099 web + 8100 worker)
    mushroom_profiles_ui.py # pantallas de especies, observaciones, evidencia, parámetros
    mushroom_catalogs_ui.py # pantallas de catálogos de referencia
    mushroom_gis_mappings_ui.py  # pantalla de revisión de mappings GIS
    mushroom_known_sites_ui.py   # pantalla de áreas privadas y micro-áreas
    mushroom_workers_ui.py  # pantalla Workers y trabajos

rainmapper-local/           # Docker local Mac
  docker-compose.yml        # servicios: rainmapper (runner) + rainmapper-ha-ui (WebUI local)
  docker-compose.worker-local.yml  # servicio rainmapper-worker (worker externo local)
  docker-compose.worker-test.yml   # test del worker
  docker-compose.rebuild-test.yml  # test de rebuild
  Dockerfile                # imagen local del runner
  options.local-ha-ui.json  # perfil versionado de opciones para la WebUI local

rainmapper-worker/          # imagen Docker headless del worker externo
  Dockerfile                # python:3.11-slim + gdal-bin + gosu; corre como UID 10001 (no-root)
                            # solo copia los mushroom_*.py necesarios, NO todo rainmapper_core
  entrypoint.sh             # arranque del servicio worker

mushroom-data/              # datos de setas VERSIONADOS en el repo (a diferencia de Data/)
  mushroom_profiles.json    # 21 perfiles productivos de especies
  mushroom_reference_catalogs.json  # catálogos de referencia (host_taxa, forest_types, etc.)
  mushroom_observations.json        # observaciones de campo (store editable)
  mushroom_labels.json      # labels multiidioma (en/es/ca) ← añadir aquí todo texto nuevo
  mushroom_known_sites.json # áreas privadas y micro-áreas
  mushroom_gis_mappings.json # mappings entre capas GIS externas e IDs internos de catálogo
  mushroom_evidence_decisions.json  # estado de decisiones de revisión GIS por especie
  mushroom_gis_observation_reconstruction.json  # artefacto GIS por observación (generado)
  mushroom_model_v0.json            # modelo aprendido v0 (artefacto generado)
  mushroom_model_v0_state.json      # especies con rebuild pendiente
  mushroom_observation_features_v0.{json,csv}   # features v0 unificadas (artefacto generado)
  mushroom_observations_weather_features.{json,csv}  # features weather (artefacto generado)
  reports/                  # informes .md de build generados (versionados, no regenerar a mano)

mushroom-GIS/               # placeholder vacío en el repo — el contenido GIS/DEM NO se versiona
                            # en local: capas ICGC (MVC50, DEM 5m, geología 50k)
                            # en HA: /media/rainmapper/mushroom-GIS/

scripts/                    # utilidades operativas
  smoke-test.sh             # validación completa antes de cualquier release
                            # incluye: sintaxis Python/JS/shell, versiones alineadas,
                            # empaquetado HA, fixtures GeoJSON, todos los tests unittest
  build-push-ha-image.sh    # publica imagen multi-arch a GHCR
  backup-data.sh            # backup .tar.gz de Data/ o docker-data/
  check-history.py          # valida integridad de históricos CSV antes/después
  validate-mushroom-data.py # valida semánticamente todos los JSON de setas
  run-mushroom-rebuild-job.py       # CLI del worker para ejecutar un rebuild
  run-mushroom-worker-service.py    # CLI del worker para arrancar el servicio
  manage-mushroom-worker-config.py  # CLI del worker para gestionar configuración
  manage-mushroom-worker-datasets.py # CLI del worker para gestionar datasets GIS
  aemet-backfill-30-days.py # backfill manual AEMET fuera de HA

docker-data/                # datos persistentes Docker local — NO versionar, NO borrar
Data/, Tomap/, Plots/       # salidas generadas — NO versionar (en .gitignore)
backups/                    # backups .tar.gz — NO versionar (en .gitignore)
tmp/                        # artefactos temporales/laboratorio — NO versionar
docs/                       # documentación del proyecto
tests/                      # 387 tests en 38 ficheros unittest
```

## Python

Usar siempre `.venv/bin/python` (Python 3.11). Nunca el Python del sistema.

## Entrypoints

```bash
python -m rainmapper_core.rainmapper   # descarga + normaliza fuentes meteo
python -m rainmapper_core.tomap        # reconstruye CSVs Tomap
python -m rainmapper_core.geojson      # genera GeoJSON para visores
python -m rainmapper_core.bokeh_maps   # genera mapas HTML Bokeh (legacy)
python -m rainmapper_core.create_aemet # fuente AEMET (uso independiente)
```

## Dependencias clave

Python (pip, `requirements.txt`): `pandas`, `numpy`, `requests`, `beautifulsoup4`, `lxml`,
`bokeh==3.2.2`, `googlemaps`, `pytz`, `Pillow==12.2.0` (EXIF), `Requests`.

Sistema (instaladas en el Dockerfile HA): `gdal-bin` (GIS), `ffmpeg` (conversión vídeo observaciones),
`libimage-exiftool-perl` (metadatos EXIF). El worker solo lleva `gdal-bin` y `gosu`.

`web_server.py` usa exclusivamente stdlib de Python (`http.server`, `threading`, `json`, etc.).
No hay framework web externo (no Flask, no FastAPI).

## Validaciones

```bash
# Smoke test completo (obligatorio antes de cualquier release)
PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh

# Suite completa
.venv/bin/python -m unittest discover -s tests

# Validador de datos de setas
.venv/bin/python scripts/validate-mushroom-data.py

# Sintaxis rápida
.venv/bin/python -m py_compile rainmapper_core/rainmapper.py rainmapper_core/geojson.py \
  rainmapper-app/app/web_server.py
node --check rainmapper_core/viewers/maplibre-viewer/app.js
node --check rainmapper_core/viewers/leaflet-viewer/app.js
git diff --check
```

Para cambios en setas (incluye el fichero de test más grande: 166 tests):
```bash
PYTHONPATH=rainmapper-app/app .venv/bin/python -m unittest \
  tests.test_web_server_auth \
  tests.test_mushroom_paths tests.test_mushroom_model_state \
  tests.test_mushroom_observations tests.test_mushroom_gis_lab \
  tests.test_mushroom_known_sites tests.test_mushroom_observation_context \
  tests.test_mushroom_observation_features tests.test_mushroom_learned_model \
  tests.test_mushroom_literature_source_apply tests.test_mushroom_data_validator
```

`test_web_server_auth.py` (166 tests) es el fichero más crítico: cubre toda la webUI de HA,
autenticación, gestión de usuarios y el protocolo completo del worker externo. Ejecutarlo
siempre que se toque `web_server.py` o cualquier módulo `*_ui.py`.

## Flujo de release HA

**Solo con autorización explícita del usuario. Ver pasos completos en `docs/release-flow.md`.**

Resumen: smoke test → bump versión (3 sitios) → actualizar `CHANGELOG.md` →
cache-busters → smoke test → `build-push-ha-image.sh` → commit/push → avisar usuario.

Durante `build-push-ha-image.sh`, seguir obligatoriamente la supervisión descrita
en `docs/release-flow.md`: consultar la misma sesión cada 20-30 segundos, informar
al usuario al menos una vez por minuto, no duplicar builds y no cancelar un cliente
local atascado hasta verificar en GHCR ambos tags, su digest y las plataformas.

No retrasar la prueba en HA por documentación de cierre o hashes documentales.
La documentación de continuidad se actualiza después del release o al cerrar sesión.

## Docker local — comandos

```bash
# WebUI local (equivalente a HA, monta docker-data/)
./mushroom_lab_start.sh          # UI en http://127.0.0.1:8101
./mushroom_lab_stop.sh

# Worker externo local
./mushroom_worker_start.sh       # health en http://127.0.0.1:8110/health
./mushroom_worker_stop.sh
# Opciones útiles del worker:
#   --name "Nombre"              nombre visible
#   --rainmapper-url URL         URL del coordinador (8100, no 8101)
#   --pairing-code-stdin         leer código de pairing desde stdin
#   --clear-token                borrar credencial sin necesitar que el coordinador responda

# Runner meteo local
./local_all.sh                   # MODE=all + servidor HTTP en http://127.0.0.1:8080/rainmapper_core/viewers/maplibre-viewer/
                                 # puerto configurable: PORT=8081 ./local_all.sh
./local_update.sh                # solo descarga datos
./local_maps.sh                  # solo genera mapas
```

**URLs importantes:**
- WebUI lab (browser): `http://127.0.0.1:8101`
- Coordinador worker (solo containers en la red Docker): `http://rainmapper-ha-ui:8100`
- Health worker: `http://127.0.0.1:8110/health`
- NO usar `127.0.0.1:8101` como URL del coordinador para el worker.

## Puertos — separación crítica

| Puerto | Qué es | Quién lo usa |
|--------|---------|--------------|
| `8099` | Web / Ingress HA | Navegador, Ingress HA, controles humanos |
| `8100` | Coordinador privado del worker | Solo workers externos autenticados |

Confundir estos puertos rompe la seguridad. El puerto `8100` NO se expone públicamente en HA por defecto.

## GHCR

- Usar `GH_TOKEN` con `curl` para listar/borrar versiones remotas. No usar `gh` ni osxkeychain.
- Conservar siempre: versión activa, `latest`, rollback inmediato y manifests auxiliares multi-arch.
- No limpiar durante una instalación HA en curso.
- Ver procedimiento exacto en `docs/decisions.md` (sección GHCR).

## Módulo de setas — fuente de verdad operativa

```
Local:   docker-data/mushroom-data/          ← fuente de verdad durante desarrollo
HA:      /share/rainmapper/mushroom-data/
GIS/DEM: mushroom-GIS/                       ← placeholder vacío en repo, contenido local
HA GIS:  /media/rainmapper/mushroom-GIS/     ← NO mover a /share (infla backups HA)
```

Resolver canónico de rutas: `rainmapper_core/mushroom_paths.py`. No reintroducir heurísticas de rutas en otros módulos.

**`mushroom-data/` está versionado** (a diferencia de `Data/` que está en .gitignore). Los cambios en los JSON de perfiles, catálogos, observaciones, labels y mappings son parte del workflow normal de mantenimiento y se commitean.

**Al subir datos a HA:** reemplazar en HA los ficheros de `mushroom-data/` por la copia local validada. No mezclar con datos antiguos de HA ni tocar `users.json`, `devices.json` ni históricos meteorológicos.

## Módulo de setas — módulos Python clave

| Módulo | Propósito |
|--------|-----------|
| `mushroom_paths.py` | Resolver canónico de rutas — usar siempre este |
| `mushroom_store.py` | Persistencia JSON: seeding, validación, replace atómico + backup |
| `mushroom_observations.py` | Helpers shared para payloads de observaciones |
| `mushroom_profile_v0.py` | Proyección v0 del schema rico — no promueve campos ML numéricos |
| `mushroom_gis_lab.py` | Reconstrucción GIS por observación usando capas locales |
| `mushroom_observation_context.py` | Contexto meteorológico por observación desde históricos Rainmapper |
| `mushroom_observation_features.py` | Join features GIS + weather → features v0 |
| `mushroom_learned_model.py` | Modelo v0 descriptivo/auditable — no escribe perfiles, no fija umbrales |
| `mushroom_model_state.py` | Estado pendiente de rebuild por especie |
| `mushroom_rebuild_pipeline.py` | Pipeline compartido HA+worker — sin deps HTTP/HA/Docker |
| `mushroom_rebuild_snapshot.py` | Snapshots versionados de inputs reproducibles |
| `mushroom_rebuild_contracts.py` | Contratos JobSpec 0.1 / ResultManifest 0.1 |
| `mushroom_rebuild_comparison.py` | Comparación semántica de artefactos de rebuild |
| `mushroom_worker_*.py` | Infraestructura del worker: auth, config, registry, jobs, results, transport, dataset cache, service |

## Módulo de setas — documentación

| Fichero | Qué cubre |
|---------|-----------|
| `docs/mushrooms/mushroom-v0-external-worker-design-es.md` | Diseño completo de la plataforma de cómputo externo |
| `docs/mushrooms/mushroom-ml-training-plan-es.md` | Plan ML: dataset, entrenamiento, evaluación |
| `docs/mushrooms/mushroom-predictor-design-es.md` | Diseño del predictor de floradas (borrador) |
| `docs/mushrooms/mushroom-observations-schema-es.md` | Schema operativo de observaciones |
| `docs/mushrooms/mushroom-labels-reference-es.md` | Contrato de `mushroom_labels.json` |
| `docs/mushrooms/gis-layer-inventory-es.md` | Inventario capas GIS (MVC50, DEM, geología) |
| `docs/mushrooms/mushroom-gis-mappings-reference-es.md` | Schema de `mushroom_gis_mappings.json` |
| `docs/mushrooms/mushroom-profiles-reference-es.md` | Schema de `mushroom_profiles.json` |
| `docs/mushrooms/mushroom-reference-catalogs-reference-es.md` | Schema de `mushroom_reference_catalogs.json` |
| `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md` | Contrato v0: qué campos son activos, qué es legado |
| `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md` | Guía para reconstrucción de parámetros desde observaciones |
| `docs/mushrooms/literature/marc-estevez-v0-source-normalized.json` | Única fuente literaria normalizada versionada (21 especies) |
| `docs/mushrooms/literature/README.md` | Índice de la biblioteca de literatura del predictor |

## Datos persistentes HA

```
/share/rainmapper/Data/             # históricos meteorológicos CSV
/share/rainmapper/Tomap/
/share/rainmapper/Plots/
/share/rainmapper/stations.txt
/share/rainmapper/ignore_stations_tomap.txt
/share/rainmapper/users.json        # gestión de usuarios MapLibre
/share/rainmapper/devices.json
/share/rainmapper/mushroom-data/    # datos de setas
/media/rainmapper/mushroom-GIS/     # capas GIS/DEM pesadas — NO mover a /share
```

## Reglas operativas — NO hacer sin autorización explícita

- Bump de versión, publicar imagen, limpiar GHCR, commit/push
- Borrar `docker-data/`, `tmp/`, `mushroom-GIS/`, `backups/` ni históricos CSV
- Tocar históricos CSV sin seguir `docs/history-safety.md` (backup previo obligatorio)
- Crear una imagen HA de desarrollo/sideload
- Inventar umbrales, pesos, ventanas meteorológicas ni parámetros del motor de setas
- Ejecutar `docker compose down -v` (borra volúmenes con datos)

## Reglas operativas — siempre hacer

- Usar `.venv/bin/python` (Python 3.11), nunca el Python del sistema
- Leer `docs/codex-start-here.md` + `docs/active-context.md` al arrancar sesión
- Ejecutar smoke test antes de cualquier release
- Mantener la reconstrucción local de HA como fallback permanente
- Todo texto visible nuevo del dominio setas → `mushroom-data/mushroom_labels.json` con `en`, `es` y `ca`
- Al publicar: ir directamente con permisos elevados (no intentar flujo normal primero, falla por sandbox)
- Actualizar `docs/active-context.md` y documentación relevante al cerrar sesión con cambios
- Al modificar `web_server.py` o cualquier `*_ui.py`: ejecutar `test_web_server_auth.py` (166 tests)

## Opciones HA relevantes para desarrollo

Las opciones más relevantes al desarrollar (lista completa en `rainmapper-app/config.yaml` y `rainmapper-app/DOCS.md`):

| Opción | Default | Nota |
|--------|---------|------|
| `mode` | serve | `serve` es el modo HA normal |
| `ui_language` | en | Soporta `en`, `es`, `ca` |
| `schedule_enabled` | false | Schedule interno de HA |
| `create_aemet` | false | AEMET es opcional, requiere `aemet_api_key` |
| `publish_to_www` | false | Publica Bokeh/Leaflet en `/config/www` |
| `external_worker_connections_enabled` | false | Arranca listener 8100 |
| `external_worker_rebuilds_enabled` | false | Autoriza rebuilds externos |
| `wunderground_daily_api` | true | API diaria con fallback scraper HTML |
| `max_threads` | 3 | Threads Wunderground — usar 1 si hay timeouts |

## Worker externo — reglas

- No existe ni se creará imagen HA de desarrollo para pruebas del worker.
- El selector operacional externo (`external_worker_rebuilds_enabled`) está desactivado por defecto en HA.
- El protocolo de pairing usa código temporal de 10 min / uso único desde la UI "Workers y trabajos".
- `8100` no se expone en el router. LAN privada primero; Tailscale/TLS/ACL como endurecimiento posterior.
- Al borrar token del worker: `./mushroom_worker_start.sh --clear-token` (no requiere que el coordinador responda).
- No reiniciar el proceso worker para preservar jobs en cola activos; el próximo arranque migrará la URL.
