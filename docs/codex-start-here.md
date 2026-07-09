# Codex Start Here

Este es el punto de entrada para una nueva sesion Codex en RainmapperHA.

## Objetivo del proyecto

RainmapperHA es una aplicacion Python empaquetada como add-on de Home
Assistant. Descarga historicos meteorologicos, genera mapas de lluvia y mantiene
un modulo de setas para registrar observaciones, revisar perfiles de especies y
construir un modelo v0 descriptivo/auditable.

El trabajo activo actual esta centrado en el modulo de setas, en diagnosticar
el rendimiento del backend `run_all` y en mantener solo el visor protegido como
salida operativa principal.

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
- Ultimo release HA publicado: `fb2d2c7 Release Home Assistant 0.2.190`.
- Version HA del repo: `0.2.190` en `rainmapper-app/config.yaml` y
  `rainmapper-app/Dockerfile`.
- No hacer bump de version ni publicar imagen HA salvo peticion explicita.
- Imagen publicada/verificada: `ghcr.io/cginebrosa/rainmapperha:0.2.190` y
  `latest`, digest multi-arch
  `sha256:b0e81a8f1db09c2cef3da7af5dfa6ae25a97814c8a7ee7fffd81bc0e423f8d2b`.

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
  `mushroom_gis_mappings_ui.py`.
- Usar patrones existentes y evitar refactors grandes si no son necesarios.

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
python3 scripts/validate-mushroom-data.py
python3.11 -m py_compile rainmapper-app/app/web_server.py rainmapper-app/app/mushroom_profiles_ui.py rainmapper_core/mushroom_paths.py
python3.11 -m unittest tests.test_mushroom_paths tests.test_mushroom_model_state tests.test_mushroom_observations tests.test_mushroom_gis_lab tests.test_mushroom_observation_context tests.test_mushroom_observation_features tests.test_mushroom_learned_model tests.test_mushroom_literature_source_apply tests.test_mushroom_data_validator tests.test_web_server_auth
git diff --check
```

Para release HA: revisar diff, ejecutar validacion local relevante, hacer bump
de version/cache-busters, commit/push, publicar y verificar la imagen GHCR, y
avisar al usuario en cuanto HA pueda probarla. No retrasar una prueba en HA por
documentacion de cierre o hashes documentales.
