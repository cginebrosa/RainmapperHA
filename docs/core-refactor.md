# Core Refactor Notes

## Objetivo
Reducir gradualmente la duplicidad entre los scripts de raiz y las copias dentro de `rainmapper-app/app`, sin romper Docker local ni la app de Home Assistant.

La estrategia es conservadora: mantener los entrypoints actuales (`Rainmapper.py`, `tomap_builder.py`, `tomap_to_geojson.py`, `Rainmapper_Client.py`, `run.sh` y `rainmapper-app/run.sh`) y mover primero solo implementaciones pequenas y estables a un paquete compartido.

## Principios
- No mover `Rainmapper.py` entero al inicio.
- No cambiar simultaneamente imports, Dockerfiles, webUI y logica de datos.
- Mantener wrappers compatibles mientras se valida cada paso.
- No tocar historicos reales (`Data`, `docker-data`, `/share/rainmapper`) durante la refactorizacion.
- Validar cada fase con:
  - `./scripts/smoke-test.sh`
  - `./scripts/docker-offline-functional-test.sh`
  - tests unitarios con `.venv/bin/python -m unittest discover -s tests`
- Actualizar `docs/codex-handoff.md`, `docs/architecture.md`, `docs/todo.md` y este documento cuando cambie el estado de la refactorizacion.

## Fase 1: paquete compartido minimo
Estado: implementada y validada.

Cambios previstos:
- Crear paquete `rainmapper_core/`.
- Mover la implementacion de `incremental_upsert.py` a `rainmapper_core/incremental_upsert.py`.
- Mantener `incremental_upsert.py` en raiz como wrapper compatible.
- Mantener `rainmapper-app/app/incremental_upsert.py` como wrapper compatible cuando se sincronice la app HA.
- Ajustar `scripts/sync-app-files.sh` para copiar `rainmapper_core/` a `rainmapper-app/app/rainmapper_core/`.
- Ajustar `scripts/smoke-test.sh` para comprobar que `rainmapper_core/` y su copia HA estan sincronizados.

Estado actual de esta fase:
- `rainmapper_core/__init__.py` creado.
- `rainmapper_core/incremental_upsert.py` creado con la implementacion real.
- `incremental_upsert.py` de raiz convertido en wrapper compatible.
- `rainmapper-app/app/incremental_upsert.py` convertido en wrapper compatible via `scripts/sync-app-files.sh`.
- `rainmapper-app/app/rainmapper_core/` creado como copia operativa del paquete compartido para la imagen HA.
- `scripts/sync-app-files.sh` modificado para sincronizar `rainmapper_core/`.
- `scripts/smoke-test.sh` modificado para compilar y comparar `rainmapper_core/`.
- Validado con `.venv/bin/python -m unittest discover -s tests`.
- Validado con `./scripts/smoke-test.sh`.
- Validado con `./scripts/docker-offline-functional-test.sh`.

Nota operativa: el primer intento de `./scripts/sync-app-files.sh` fallo por permisos del sandbox al copiar sobre `rainmapper-app/app/Rainmapper.py`; se repitio con permisos adecuados y termino correctamente.

## Rollback de Fase 1
Si falla algo:
- Restaurar el contenido anterior de `incremental_upsert.py` desde Git.
- Eliminar `rainmapper_core/`.
- Quitar `sync_dir rainmapper_core` de `scripts/sync-app-files.sh`.
- Quitar las referencias a `rainmapper_core` de `scripts/smoke-test.sh`.
- Volver a ejecutar `./scripts/smoke-test.sh`.

## Fase 2: usar paquete compartido en mas helpers pequenos
Estado: implementada y validada para GeoJSON y Tomap builder.

Cambios implementados:
- Crear `rainmapper_core/geojson.py` con la implementacion compartida de conversion `Tomap` -> GeoJSON.
- Mantener `tomap_to_geojson.py` en raiz como wrapper compatible hacia `rainmapper_core.geojson`.
- Mantener `rainmapper-app/app/tomap_to_geojson.py` como wrapper compatible cuando se sincronice la app HA.
- Crear `rainmapper_core/tomap.py` con la implementacion compartida de reconstruccion `Data/*_incremental.csv` -> `Tomap/*.csv`.
- Mantener `tomap_builder.py` en raiz como wrapper compatible hacia `rainmapper_core.tomap`.
- Mantener `rainmapper-app/app/tomap_builder.py` como wrapper compatible cuando se sincronice la app HA.
- Mantener sin cambios los entrypoints de Docker local y Home Assistant: siguen ejecutando `tomap_to_geojson.py`.
- Mantener sin cambios los entrypoints de Docker local y Home Assistant: siguen ejecutando `tomap_builder.py`.
- Ajustar `scripts/smoke-test.sh` para compilar tambien `rainmapper_core/geojson.py`, `rainmapper_core/tomap.py` y sus copias HA.

Validaciones realizadas para este paso:
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`

Resultado:
- `tomap_to_geojson.py` y `tomap_builder.py` quedan como entrypoints estables.
- La logica compartida vive en `rainmapper_core/geojson.py` y `rainmapper_core/tomap.py`.
- Los tests existentes siguen importando `tomap_builder` sin cambios gracias al wrapper.

No mover todavia:
- `Rainmapper.py` completo.
- `Rainmapper_Client.py` completo.
- `web_server.py`.

## Rollback de Fase 2
Si falla algo:
- Restaurar el contenido anterior de `tomap_to_geojson.py` desde Git.
- Restaurar el contenido anterior de `tomap_builder.py` desde Git.
- Eliminar `rainmapper_core/geojson.py`.
- Eliminar `rainmapper_core/tomap.py`.
- Quitar las referencias a `rainmapper_core/geojson.py` de `scripts/smoke-test.sh`.
- Quitar las referencias a `rainmapper_core/tomap.py` de `scripts/smoke-test.sh`.
- Ejecutar `./scripts/sync-app-files.sh` para volver a alinear la app HA.
- Volver a ejecutar `./scripts/smoke-test.sh`.

## Fases futuras

### Fase 3: reducir duplicidad operativa
Estado: implementada en alcance conservador inicial.

Cambios implementados:
- Crear `scripts/sync-manifest.sh` como fuente unica de ficheros y directorios que se copian desde raiz hacia `rainmapper-app/app`.
- Hacer que `scripts/sync-app-files.sh` use ese manifiesto para copiar ficheros/directorios.
- Hacer que `scripts/smoke-test.sh` use el mismo manifiesto para validar que la copia HA esta alineada.
- El smoke test ahora cubre tambien wrappers que antes podian quedar fuera de la comparacion explicita, como `incremental_upsert.py` y `tomap_builder.py`.

Decision conservadora:
- No cambiar todavia `rainmapper-app/Dockerfile`. El build de HA y el fallback de GitHub Actions usan `rainmapper-app` como contexto Docker, asi que copiar directamente codigo desde la raiz requeriria cambiar el flujo de build y podria afectar Home Assistant.

Validaciones realizadas para este paso:
- `./scripts/sync-app-files.sh`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`

Pendiente dentro de Fase 3:
- Si se quiere reducir mas la copia fisica dentro de `rainmapper-app/app`, hacerlo en una fase posterior cambiando explicitamente el flujo de build y validando HA/GHCR.
- La reorganizacion global de carpetas queda aplazada hasta que `Rainmapper.py` este mas modularizado.

### Fase 4: agrupar librerias internas por fuente
Estado: implementada.

Cambios implementados:
- Mover `sodapy_local/` a `rainmapper_core/sources/sodapy_local/`.
- Mover `meteoclimatic_local/` a `rainmapper_core/sources/meteoclimatic_local/`.
- Mover `util/` a `rainmapper_core/sources/wunderground/`.
- Actualizar imports en `Rainmapper.py`, `rainmapper-app/app/Rainmapper.py` y dentro de las librerias movidas.
- Eliminar del paquete HA las copias antiguas top-level `sodapy_local/`, `meteoclimatic_local/` y `util/`; ahora entran en HA como parte de `rainmapper_core/`.
- Ampliar `scripts/smoke-test.sh` para compilar dinamicamente todos los `.py` bajo `rainmapper_core/` y su copia HA.

Decision conservadora:
- No partir todavia la logica de descarga de `Rainmapper.py`; solo se actualizan imports hacia las nuevas rutas de fuente.
- No mover constantes ni helpers sueltos uno por uno.

Validaciones realizadas para este paso:
- imports locales de `rainmapper_core.sources.sodapy_local`, `rainmapper_core.sources.meteoclimatic_local` y `rainmapper_core.sources.wunderground`.
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
- import de fuentes dentro del contenedor Docker local.

### Fase 5: estructura objetivo `core/app/local`
Estado: iniciada. Fases 5A, 5B, 5C y 5D implementadas en alcance conservador.

Objetivo:
- Pasar de la estructura hibrida actual a una separacion mas clara por responsabilidades, sin convertirlo en una secuencia indefinida de micro-refactors.

Estructura objetivo:
- `rainmapper_core/`: todo lo compartido por Docker local y Home Assistant.
  - Scripts Python reutilizables y modulos de dominio.
  - `rainmapper_core/sources/` con clientes/helpers de cada fuente.
  - Configuracion comun cuando realmente sea compartida (`const.py`, `config.py`, `config_wunderground.py` o equivalentes).
  - Generacion `Tomap`, GeoJSON, upsert incremental y mapas compartidos.
  - Visores compartidos Leaflet/MapLibre si siguen siendo identicos para local y HA.
  - Dependencias Python comunes si local y HA siguen usando el mismo set.
- `rainmapper-app/`: solo lo especifico de Home Assistant.
  - `config.yaml`, `Dockerfile`, `run.sh` de HA.
  - `web_server.py`, ingress/sidebar, schedule HA, publicacion a `/config/www` y lectura de `/data/options.json`.
  - Documentacion propia de la app HA.
- `rainmapper-local/`: solo lo especifico del entorno local.
  - Dockerfile/Compose local si dejan de vivir en raiz.
  - Scripts de conveniencia locales como `local_all.sh`, `local_maps.sh`, `local_update.sh`.
  - Wrappers locales que solo existan para desarrollo en Mac.

Alcance recomendado:
1. Definir y documentar el mapa final de ficheros antes de mover nada.
2. Mover directorios grandes y coherentes, no constantes o helpers uno a uno.
3. Mantener wrappers compatibles temporalmente para no romper comandos conocidos.
4. Cambiar Docker local y Docker HA en pasos separados, con validacion entre ambos.
5. No mezclar esta reestructura con cambios funcionales de descarga, historicos o visores.

Validaciones minimas:
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
- `./local_all.sh` al menos una vez antes de publicar nueva version HA.
- Si se toca `rainmapper-app/Dockerfile` o `rainmapper-app/run.sh`, validar build/push GHCR e instalacion HA en una version dedicada.

Relacion con "partir `Rainmapper.py`":
- No significa dividir el fichero por estetica.
- Significa separar responsabilidades grandes que hoy conviven en `Rainmapper.py`: CLI/configuracion, orquestacion, fuentes, upsert, estado por fuente, metricas y escritura de ficheros.
- Esta separacion funcional puede hacerse despues o en paralelo controlado con la reestructura de carpetas, pero no debe bloquear la fase 5 si la fase 5 se limita a ordenar ubicaciones y empaquetado.

#### Fase 5A: mover runtime local
Estado: implementada y subida a Git.

Cambios implementados:
- Crear `rainmapper-local/`.
- Mover ahi los ficheros especificos del Docker local:
  - `rainmapper-local/Dockerfile`
  - `rainmapper-local/docker-compose.yml`
  - `rainmapper-local/run.sh`
  - `rainmapper-local/local_all.sh`
  - `rainmapper-local/local_maps.sh`
  - `rainmapper-local/local_update.sh`
- Mantener wrappers compatibles en la raiz:
  - `docker-compose.yml`: incluye `rainmapper-local/docker-compose.yml` para que `docker compose ...` siga funcionando desde la raiz.
  - `run.sh`, `local_all.sh`, `local_maps.sh`, `local_update.sh`: wrappers que delegan en `rainmapper-local/`.
  - No se mantiene `Dockerfile` en raiz para evitar que `docker build .` genere una imagen distinta o incompleta por error.

Decision conservadora:
- No tocar todavia la imagen de Home Assistant ni `rainmapper-app/Dockerfile`.
- No mover `Rainmapper.py` ni cambiar logica de datos.
- Mantener los comandos habituales de raiz mientras se valida la nueva ubicacion local.

Validaciones realizadas:
- `docker compose -f rainmapper-local/docker-compose.yml config`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
- `./local_all.sh` o `./rainmapper-local/local_all.sh` cuando se quiera una validacion completa con descarga real.

#### Fase 5B: mover configuracion Python compartida al core
Estado: implementada en alcance conservador.

Cambios implementados:
- Crear `rainmapper_core/config/`.
- Mover la implementacion real de:
  - `const.py` -> `rainmapper_core/config/const.py`
  - `config.py` -> `rainmapper_core/config/config.py`
  - `config_wunderground.py` -> `rainmapper_core/config/config_wunderground.py`
- Mantener wrappers compatibles en raiz y en `rainmapper-app/app/`.
- Actualizar imports internos de `Rainmapper.py`, `Rainmapper_Client.py`, `tomap_builder.py` y `rainmapper_core/sources/wunderground/` para usar `rainmapper_core.config`.
- Ajustar `scripts/sync-manifest.sh` para sincronizar tambien `config.py` y `config_wunderground.py`.

Decision conservadora:
- Los wrappers se mantienen aunque el codigo interno ya no dependa de imports top-level antiguos. Esto evita romper usos manuales o scripts externos que sigan haciendo `from const import _DATA_PATH`.
- No mover todavia `Rainmapper.py` ni partir la logica de fuentes.
- No tocar el Dockerfile de Home Assistant.

Detalle importante:
- `rainmapper_core/config/const.py` calcula `_script_path` como la raiz del runtime a partir de `rainmapper_core/config`. En Docker esas rutas son internas del contenedor (`/app/Data`, `/app/Tomap`, `/app/Plots`) y se montan desde `docker-data/...` en el Mac; en ejecuciones locales sin contenedor apuntan a la raiz del repo.
- El wrapper `const.py` reexporta explicitamente nombres con guion bajo porque `import *` no exporta constantes privadas por defecto.

Validaciones realizadas:
- Importar `rainmapper_core.config.const` y `const` legacy y confirmar que `_DATA_PATH`, `_MAPS_PATH` y `_PLOT_PATH` apuntan al runtime root.
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`, que confirmo dentro del contenedor Docker las rutas internas `/app/Data` y `/app/Tomap`.

#### Fase 5C: mover Bokeh maps al core
Estado: implementada en alcance conservador.

Cambios implementados:
- Mover la implementacion real de `Rainmapper_Client.py` a `rainmapper_core/bokeh_maps.py`.
- Mantener `Rainmapper_Client.py` en raiz y en `rainmapper-app/app` como entrypoint compatible.
- Convertir el bloque ejecutable antiguo en `main()` para que importar `rainmapper_core.bokeh_maps` no genere mapas como efecto secundario.

Decision conservadora:
- Mantener el nombre `Rainmapper_Client.py` como comando operativo, porque `run.sh`, `rainmapper-app/run.sh` y `web_server.py` todavia lo invocan directamente.
- No cambiar todavia la publicacion `/local/Plots`.

Validaciones esperadas:
- `python -m py_compile Rainmapper_Client.py rainmapper_core/bokeh_maps.py`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`

#### Fase 5D: mover visores compartidos al core
Estado: implementada en alcance conservador. Ajuste posterior completado: `web_server.py` publica directamente desde `rainmapper_core/viewers`.

Cambios implementados:
- Mover los visores compartidos a:
  - `rainmapper_core/viewers/leaflet-viewer/`
  - `rainmapper_core/viewers/maplibre-viewer/`
- Mantener rutas compatibles en raiz:
  - `leaflet-viewer` -> `rainmapper_core/viewers/leaflet-viewer`
  - `maplibre-viewer` -> `rainmapper_core/viewers/maplibre-viewer`
- Retirar las copias compatibles `rainmapper-app/app/leaflet-viewer` y `rainmapper-app/app/maplibre-viewer`.
- `scripts/sync-manifest.sh` sincroniza `rainmapper_core/`; los visores HA entran en la imagen como parte de `rainmapper_core/viewers/`.

Decision conservadora:
- No cambiar las URLs publicas `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre`.
- Los enlaces de raiz mantienen funcionando `./local_maps.sh`, `./local_all.sh`, el servidor HTTP local y las validaciones existentes.

Validaciones esperadas:
- `node --check leaflet-viewer/app.js` y `node --check maplibre-viewer/app.js` usando las rutas compatibles.
- `node --check rainmapper_core/viewers/.../app.js` usando las rutas canonicas.
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
