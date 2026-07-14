# Codex Start Here

Este es el punto de entrada para una nueva sesion Codex en RainmapperHA.

## Objetivo del proyecto

RainmapperHA es una aplicacion Python empaquetada como add-on de Home
Assistant. Descarga historicos meteorologicos, genera mapas de lluvia y mantiene
un modulo de setas para registrar observaciones, revisar perfiles de especies y
construir un modelo v0 descriptivo/auditable.

El release HA estable y MapLibre meteorologico estan validados. El trabajo
activo se concentra en el modulo de setas: observaciones, media EXIF, setales
jerarquicos con geometria/GIS/DEM y preparacion de un pipeline ML real. El
modelo v0 actual sigue siendo descriptivo y auditable, no un estimador ML.

## Ruta obligatoria

Trabajar solo en:

```text
/Users/carlosginebrosa/Developer/RainmapperHA
```

No usar la copia antigua de iCloud/Mobile Documents.

Antes de editar, comprobar:

```bash
pwd
git status --short
```

## Lectura minima al arrancar

Leer siempre:

1. `docs/codex-start-here.md`
2. `docs/active-context.md`

Leer despues segun tarea:

- Arquitectura/rutas/entrypoints: `docs/architecture.md`
- Pendientes y prioridades largas: `docs/todo.md`
- Decisiones cronologicas: `docs/decisions.md`
- Historia no activa: `docs/project-archive.md`
- Seguridad de historicos CSV: `docs/history-safety.md`
- App movil futura: `docs/mobile-app-architecture.md`
- Refactor/core: `docs/core-refactor.md` solo si se toca estructura/core/refactor

Para tareas de setas:

- Parametros UI: `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`
- Observaciones UI: `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`
- Schema de observaciones: `docs/mushrooms/mushroom-observations-schema-es.md`
- Plan de entrenamiento ML: `docs/mushrooms/mushroom-ml-training-plan-es.md`
- Modelo v0/laboratorio: `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`
- Predictor: `docs/mushrooms/mushroom-predictor-design-es.md`
- Contrato perfiles v0: `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`
- Fuente Marc Estevez: `docs/mushrooms/mushroom-literature-source-apply-es.md`
- GIS: `docs/mushrooms/gis-layer-inventory-es.md`
- Labels: `docs/mushrooms/mushroom-labels-reference-es.md`

## Mantenimiento de contexto

- Este documento debe ser breve y estable. Actualizarlo solo si cambia la
  estructura general del proyecto, las reglas de trabajo o el mapa de
  documentacion.
- `docs/active-context.md` es la ventana operativa actual, no un historico
  acumulativo. Una nueva sesion debe poder arrancar leyendo solo estos dos
  documentos y consultar el resto bajo demanda.
- Las decisiones importantes van a `docs/decisions.md` con estado claro:
  vigente, reemplazada, obsoleta o pendiente de confirmar.
- La historia util que ya no sea contexto activo va a
  `docs/project-archive.md` o al documento historico correspondiente.

## Estado general verificado

- Rama activa: `inicial`.
- Ultimo release HA publicado: `0.2.202`.
- Version HA del repo: `0.2.202` en `rainmapper-app/config.yaml` y
  `rainmapper-app/Dockerfile`.
- No hacer bump de version ni publicar imagen HA salvo peticion explicita.
- Imagen publicada/verificada: `ghcr.io/cginebrosa/rainmapperha:0.2.202` y
  `latest`, digest multi-arch
  `sha256:3ee510ee50793e252bbe5a6c05f722567da758f374d865ebd96a272c259ee7ed`.
- Commit release: `7ba31e8 Release Home Assistant 0.2.202`.
- `0.2.199` fue validada en HA por el usuario el 2026-07-11: MapLibre protegido
  funciona y el popup largo muestra `Pluja` en `Valores IDW`.
- Repo GitHub sigue publico por decision explicita del usuario; no cerrarlo.
- No limpiar GHCR sin confirmar version activa/rollback y sin conservar
  manifests/attestations auxiliares multi-arch.
- `rainmapper-local/options.local-ha-ui.json` es el perfil versionado de la HA
  UI local. Puede modificarse temporalmente durante pruebas de backfill, pero no
  debe contener claves reales.

## Reglas de trabajo

- No borrar `docker-data/`, `tmp/`, `mushroom-GIS/`, `backups/`, historicos ni
  artefactos locales.
- No tocar datos reales de historicos CSV sin seguir `docs/history-safety.md`.
- No inventar umbrales, pesos, ventanas meteorologicas ni parametros de setas.
- El modelo v0 aprendido es descriptivo/auditable; no escribe perfiles.
- Cualquier promocion de evidencia a perfil debe ser manual, visible y
  reversible.
- Todo texto visible nuevo del dominio setas debe ir en
  `mushroom-data/mushroom_labels.json` con `en`, `es` y `ca`.
- Mantener `web_server.py` en rutas/POST/orquestacion; pantallas grandes en
  `mushroom_profiles_ui.py`, `mushroom_catalogs_ui.py` o
  `mushroom_gis_mappings_ui.py`; setales en `mushroom_known_sites_ui.py`.
- Usar patrones existentes y evitar refactors grandes si no son necesarios.
- En desarrollo local usar siempre `.venv/bin/python` (Python 3.11), igual que
  el contenedor y HA. No usar el Python del sistema. La migracion a Python 3.14
  se tratara como tarea separada.
- La navegacion de la WebUI debe conservar el contexto de llamada: al cerrar o
  volver, restaurar formulario/borrador o lista con seleccion, filtros, orden y
  scroll. No crear versiones divergentes del mismo modal segun el origen.

## Fuente de verdad de setas

En la fase local actual, la fuente operativa de setas es:

```text
docker-data/mushroom-data/
```

En HA equivale a:

```text
/share/rainmapper/mushroom-data/
```

Las capas GIS/DEM pesadas necesarias para reconstruir contexto de setas en HA
viven en:

```text
/media/rainmapper/mushroom-GIS/
```

No moverlas a `/share` salvo decision explicita: inflan backups completos de
Home Assistant.

`rainmapper_core/mushroom_paths.py` es el resolver canonico. No reintroducir
lecturas legacy del modelo en `mushroom-lab/working`.

`tmp/mushroom-lab/` queda para pruebas explicitas, QGIS, fotos e intermedios
exploratorios. No es la ruta estable del modelo v0.

Cuando se decida subir este trabajo a HA, los datos micologicos locales
validados deben reemplazar los de HA para especies, observaciones, catalogos,
mappings, labels y artefactos v0. No mezclar con datos micologicos antiguos de
HA. No tocar usuarios, dispositivos ni historicos meteorologicos en esa
operacion.

## Validaciones habituales

Para cambios en setas:

```bash
.venv/bin/python scripts/validate-mushroom-data.py
.venv/bin/python -m py_compile rainmapper-app/app/web_server.py rainmapper-app/app/mushroom_profiles_ui.py rainmapper-app/app/mushroom_known_sites_ui.py rainmapper_core/mushroom_paths.py rainmapper_core/mushroom_known_sites.py
PYTHONPATH=rainmapper-app/app .venv/bin/python -m unittest tests.test_mushroom_paths tests.test_mushroom_model_state tests.test_mushroom_observations tests.test_mushroom_gis_lab tests.test_mushroom_known_sites tests.test_mushroom_observation_context tests.test_mushroom_observation_features tests.test_mushroom_learned_model tests.test_mushroom_literature_source_apply tests.test_mushroom_data_validator tests.test_web_server_auth
git diff --check
```

Para release HA: revisar diff, ejecutar validacion local relevante, hacer bump
de version/cache-busters, commit/push, publicar y verificar la imagen GHCR, y
avisar al usuario en cuanto HA pueda probarla. No retrasar una prueba en HA por
documentacion de cierre o hashes documentales.

Para MapLibre protegido: no fiarse solo de que `app.js` contenga un cambio. El
HTML servido debe cargar assets con el cache-buster de la version runtime; desde
`0.2.199`, `web_server.py` sirve el index protegido con `no-store` y reescribe
los query strings de assets a `RAINMAPPER_APP_VERSION`.

Para limpieza GHCR: conservar siempre la version activa, `latest`, rollback
inmediato y manifests/attestations auxiliares sin tag asociados. No limpiar
durante una instalacion HA en curso. En esta maquina no asumir que `gh` esta
instalado; usar `curl` con `GH_TOKEN` como documenta `docs/decisions.md` en la
seccion GHCR.
