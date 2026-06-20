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
Cuando `rainmapper_core/` este estabilizado:
- Mantener `scripts/sync-app-files.sh`, pero reducir progresivamente la lista de scripts duplicados.
- Evaluar si `rainmapper-app/Dockerfile` puede copiar el paquete compartido de una forma menos duplicada.

### Fase 4: refactor de `Rainmapper.py`
Solo despues de tener cobertura suficiente y varias validaciones:
- Extraer funciones puras y sin efectos secundarios.
- Evitar cambiar descarga, escritura de historicos y estado por fuente en el mismo paso.
- Mantener posibilidad de comparar outputs antes/despues.
