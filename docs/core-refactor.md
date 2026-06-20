# Core Refactor Notes

## Objetivo
Reducir gradualmente la duplicidad entre los scripts de raiz y las copias dentro de `rainmapper-app/app`, sin romper Docker local ni la app de Home Assistant.

La estrategia es conservadora: mantener solo los entrypoints publicos que siguen aportando compatibilidad real (`run.sh`, `local_*.sh` y `rainmapper-app/run.sh`) y mover implementaciones compartidas a `rainmapper_core/`. Los wrappers Python del raiz ya fueron retirados; se usan directamente `python -m rainmapper_core.rainmapper`, `python -m rainmapper_core.bokeh_maps`, `python -m rainmapper_core.tomap` y `python -m rainmapper_core.geojson`.

## Principios
- No mover `Rainmapper.py` entero al inicio.
- No cambiar simultaneamente imports, Dockerfiles, webUI y logica de datos.
- Mantener wrappers compatibles solo mientras aporten compatibilidad real. Desde Fase 5I ya no quedan wrappers Python raiz para core, configuracion ni upsert incremental.
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
- Mantener temporalmente `incremental_upsert.py` en raiz como wrapper compatible. Sustituido en Fase 5H: el wrapper raiz fue retirado.
- Mantener `rainmapper-app/app/incremental_upsert.py` como wrapper compatible cuando se sincronice la app HA.
- Ajustar `scripts/sync-app-files.sh` para copiar `rainmapper_core/` a `rainmapper-app/app/rainmapper_core/`.
- Ajustar `scripts/smoke-test.sh` para comprobar que `rainmapper_core/` y su copia HA estan sincronizados.

Estado actual de esta fase:
- `rainmapper_core/__init__.py` creado.
- `rainmapper_core/incremental_upsert.py` creado con la implementacion real.
- `incremental_upsert.py` de raiz convertido temporalmente en wrapper compatible. Sustituido en Fase 5H: el wrapper raiz fue retirado.
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
- Restaurar el contenido anterior de `incremental_upsert.py` desde Git si se vuelve a ese punto historico.
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
- El smoke test ahora cubre tambien wrappers que antes podian quedar fuera de la comparacion explicita, como `tomap_builder.py`.

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
Estado: iniciada. Fases 5A, 5B, 5C, 5D y 5E implementadas en alcance conservador.

Objetivo:
- Pasar de la estructura hibrida actual a una separacion mas clara por responsabilidades, sin convertirlo en una secuencia indefinida de micro-refactors.

Estructura objetivo:
- `rainmapper_core/`: todo lo compartido por Docker local y Home Assistant.
  - Scripts Python reutilizables y modulos de dominio.
  - `rainmapper_core/sources/` con clientes/helpers de cada fuente.
  - Configuracion comun cuando realmente sea compartida (`rainmapper_core/config/const.py`, `rainmapper_core/config/config.py`, `rainmapper_core/config/config_wunderground.py` o equivalentes).
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
- Ajustar `scripts/sync-manifest.sh` para sincronizar tambien `rainmapper_core/config/config.py` y `rainmapper_core/config/config_wunderground.py`.

Decision conservadora:
- Decision sustituida en Fase 5H: los wrappers raiz de configuracion se retiraron y los usos manuales deben importar desde `rainmapper_core.config`.
- No mover todavia `Rainmapper.py` ni partir la logica de fuentes.
- No tocar el Dockerfile de Home Assistant.

Detalle importante:
- `rainmapper_core/config/const.py` calcula `_script_path` como la raiz del runtime a partir de `rainmapper_core/config`. En Docker esas rutas son internas del contenedor (`/app/Data`, `/app/Tomap`, `/app/Plots`) y se montan desde `docker-data/...` en el Mac; en ejecuciones locales sin contenedor apuntan a la raiz del repo.
- Ya no hay wrapper raiz de `const.py`; el import canonico es `rainmapper_core.config.const`.

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
- Retirar las copias compatibles `rainmapper-app/app/leaflet-viewer` y `rainmapper-app/app/maplibre-viewer`.
- `scripts/sync-manifest.sh` sincroniza `rainmapper_core/`; los visores HA entran en la imagen como parte de `rainmapper_core/viewers/`.

Decision conservadora:
- No cambiar las URLs publicas `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre`.
- `./local_maps.sh`, `./local_all.sh`, el servidor HTTP local y las validaciones usan directamente las rutas canonicas del core.

Validaciones esperadas:
- `node --check rainmapper_core/viewers/leaflet-viewer/app.js` y `node --check rainmapper_core/viewers/maplibre-viewer/app.js` usando las rutas canonicas.
- `node --check rainmapper_core/viewers/.../app.js` usando las rutas canonicas.
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`


#### Fase 5E: mover Rainmapper.py al core
Estado: implementada y validada en HA 0.2.79 antes de retirar wrappers raiz.

Cambios implementados:
- Copiar la implementacion real de `Rainmapper.py` a `rainmapper_core/rainmapper.py`.
- Convertir `Rainmapper.py` de raiz en wrapper compatible que ejecuta `rainmapper_core.rainmapper` con `runpy`.
- Convertir `rainmapper-app/app/Rainmapper.py` en el mismo wrapper compatible mediante `scripts/sync-app-files.sh`.
- Ajustar la ruta runtime usada por el modulo movido para que `requirements.txt`, `stations.txt`, `Data/`, `Tomap/` y `Plots/` sigan resolviendo desde la raiz del entorno (`/app` en Docker/HA).
- Cambiar el import de upsert para usar directamente `rainmapper_core.incremental_upsert`.

Decision conservadora:
- No partir todavia la logica interna de `Rainmapper.py`; el objetivo de esta fase es una sola fuente de verdad compartida, no reescribir el runner.
- Decision sustituida en Fase 5I: el comando historico `python Rainmapper.py` se retira y se usa `python -m rainmapper_core.rainmapper`.

Validaciones realizadas:
- `.venv/bin/python Rainmapper.py --help`
- `.venv/bin/python -m py_compile Rainmapper.py rainmapper_core/rainmapper.py rainmapper-app/app/Rainmapper.py rainmapper-app/app/rainmapper_core/rainmapper.py`
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
- `./local_update.sh` con Docker local y descarga real: Meteoclimatic, Meteocat y Wunderground completaron con exit code 0.

Siguiente paso recomendado:
- Si HA sigue estable en `0.2.79`, publicar una version dedicada con este movimiento y probar `Run update` o `Run all` en HA.
- Despues de validar HA, cerrar la fase de estructura core/app/local y decidir si merece la pena partir internamente `rainmapper_core/rainmapper.py` por responsabilidades.


#### Fase 5F: retirar wrappers Tomap/GeoJSON de raiz y HA
Estado: implementada en alcance conservador; pendiente de version dedicada y validacion HA junto con la fase 5E.

Cambios implementados:
- Retirar `tomap_builder.py` y `tomap_to_geojson.py` de la raiz del repo.
- Retirar `rainmapper-app/app/tomap_builder.py` y `rainmapper-app/app/tomap_to_geojson.py`.
- Usar `python -m rainmapper_core.tomap` y `python -m rainmapper_core.geojson` en Docker local, HA, webUI, smoke test, comparador Tomap y prueba Docker offline.
- Anadir bloques `if __name__ == '__main__'` a los modulos core para que sean ejecutables directamente con `python -m`.

Decision conservadora:
- Decision sustituida por Fase 5I: los wrappers `Rainmapper.py` y `Rainmapper_Client.py` fueron retirados tras validar el core.
- No cambiar todavia nombres publicos de comandos de usuario como `local_maps.sh` o `local_all.sh`.

Validaciones minimas:
- `python -m rainmapper_core.tomap --help`
- `python -m rainmapper_core.geojson --help`
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`


#### Fase 5G: construir HA desde la raiz y retirar copias fisicas de app
Estado: implementada; pendiente de version HA posterior y validacion manual en Home Assistant.

Cambios implementados:
- `rainmapper-app/Dockerfile` se construye con la raiz del repositorio como contexto.
- La imagen HA copia `rainmapper_core/`, wrappers raiz, configuracion compartida, `stations.example.txt` y `rainmapper-app/app/web_server.py` directamente desde la raiz.
- `rainmapper-app/app` queda reservado para codigo especifico de HA; actualmente solo contiene `web_server.py`.
- Se retiran `scripts/sync-app-files.sh` y `scripts/sync-manifest.sh` porque ya no hay copia fisica de core que sincronizar.
- `scripts/smoke-test.sh` valida que `rainmapper-app/app` no vuelva a contener copias de core.
- `.github/workflows/build-rainmapper-app.yml` y `scripts/build-push-ha-image.sh` usan la raiz del repo como contexto Docker.

Decision conservadora:
- Decision sustituida por Fase 5I: los wrappers Python de raiz fueron retirados porque ya no evitaban roturas relevantes y generaban confusion.
- No partir internamente `rainmapper_core/rainmapper.py` en esta fase; eso queda para una refactorizacion funcional posterior si aporta valor.

Validaciones realizadas:
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`

Riesgo residual:
- La app HA ya no debe construirse con `rainmapper-app` como contexto Docker aislado. El flujo soportado es construir desde la raiz del repo, como hacen `scripts/build-push-ha-image.sh` y el workflow manual de GitHub Actions.


#### Fase 5H: retirar wrappers raiz de configuracion e incremental upsert
Estado: implementada; pendiente de version HA posterior y validacion manual en Home Assistant.

Cambios implementados:
- Retirar `const.py`, `config.py`, `config_wunderground.py` e `incremental_upsert.py` de la raiz.
- Actualizar tests para importar `rainmapper_core.incremental_upsert` directamente.
- Actualizar `rainmapper-app/Dockerfile` para no copiar esos wrappers a `/app`.

Decision conservadora:
- Decision sustituida en Fase 5I: se mantienen solo wrappers shell (`run.sh`, `local_*.sh`), no wrappers Python del core.
- Mantener `rainmapper_core/config/` como unica fuente de verdad de configuracion Python.

Validaciones esperadas:
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
- `docker build -f rainmapper-app/Dockerfile -t rainmapperha-ha:test .`


#### Fase 5I: retirar wrappers raiz Rainmapper/Rainmapper_Client
Estado: implementada y validada manualmente en HA `0.2.80` con `Run all` correcto tras validacion local completa.

Cambios implementados:
- Retirar `Rainmapper.py` y `Rainmapper_Client.py` de la raiz.
- Cambiar Docker local, Home Assistant y la webUI para ejecutar directamente:
  - `python -m rainmapper_core.rainmapper`
  - `python -m rainmapper_core.bokeh_maps`
- Actualizar `rainmapper-app/Dockerfile` para no copiar wrappers Python a `/app`.
- Actualizar `scripts/smoke-test.sh` para compilar el paquete core en vez de wrappers retirados.

Decision conservadora:
- Mantener wrappers shell de usuario (`run.sh`, `local_all.sh`, `local_maps.sh`, `local_update.sh`) porque siguen siendo utiles como interfaz operativa.
- No partir internamente `rainmapper_core/rainmapper.py` en esta fase; solo se limpian entrypoints redundantes.

Validaciones esperadas:
- `python -m rainmapper_core.rainmapper --help`
- Import de `rainmapper_core.bokeh_maps.main`
- `.venv/bin/python -m unittest discover -s tests`
- `./scripts/smoke-test.sh`
- `./scripts/docker-offline-functional-test.sh`
- `docker build -f rainmapper-app/Dockerfile -t rainmapperha-ha:test .`
