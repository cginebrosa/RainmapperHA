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

## CLAUDE.md

Existe `CLAUDE.md` en la raiz del repositorio. Claude Code lo carga automaticamente
al arrancar cada sesion. Contiene las reglas operativas criticas, estructura del
proyecto, comandos de validacion y flujo de release. No es necesario leerlo
manualmente; esta disponible como referencia rapida durante el trabajo.

## Lectura minima al arrancar

Leer siempre:

1. `docs/codex-start-here.md`
2. `docs/active-context.md`

Leer despues segun tarea:

- Release HA (bump, CHANGELOG, build, push): `docs/release-flow.md`
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
- Plan de entrenamiento ML y estado actual del dataset (elegibilidad, episodios
  por especie, bloqueos activos, politica prediction_target):
  `docs/mushrooms/mushroom-ml-training-plan-es.md`
  — leer cuando se pregunte por estado del dataset, numero de episodios,
  cuantas especies son entrenables, o criterios de is_training_row.
- Modelo v0/laboratorio: `docs/mushrooms/mushroom-parameter-reconstruction-lab-plan-es.md`
- Predictor: `docs/mushrooms/mushroom-predictor-design-es.md`
- Plataforma privada de computo externo para reconstruccion/ML (imagen, cache
  GIS, UI multi-worker, ciclo inocuo autenticado por pairing con
  cancelacion/reasignacion/exclusion de duplicados, configuracion portable y
  entrega autenticada de JobSpec/snapshot vivo, ejecucion candidata, progreso y
  retorno/validacion de ResultManifest probados localmente; descarga GIS real a
  volumen vacio, reutilizacion con cero bytes, cancelacion, corte de red,
  freshness y promocion manual atomica probados en el laboratorio local. El
  selector operativo esta habilitado solo en el Compose local para todas las
  especies, pendientes y una especie; HA real/Tailscale siguen pendientes y
  requieren primero una version HA normal con el coordinador. No existe ni se
  debe crear una imagen HA de desarrollo como atajo):
  `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
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
- Ultimo release HA publicado: `0.2.225` (2026-08-06). Pendiente de instalar en HA real
  (instalada actualmente: `0.2.221`).
- **P0 Predictor/RPi4:** 0.2.221 y 0.2.225 siguen materializando 622k filas
  meteorologicas y pueden provocar un pico cercano a 1 GB. No abrir Predictor
  remotamente hasta implementar y validar chunks de 120 dias filtrados por las
  estaciones necesarias, manteniendo las features en 30 dias. Diseno completo
  en `docs/mushrooms/mushroom-predictor-design-es.md`, seccion 0.
- Version HA del repo: `0.2.225` en `rainmapper-app/config.yaml` y
  `rainmapper-app/Dockerfile`.
- No hacer bump de version ni publicar imagen HA salvo peticion explicita.
- Imagen publicada: `ghcr.io/cginebrosa/rainmapperha:0.2.225` y `latest`.
- `0.2.211` se valido en HA real con M1 emparejado por LAN: reposo estable,
  asignacion, transporte de entradas y reconstruccion candidata completa
  privada completados. Un candidato quedo verificado al 100 % en 55 s sin
  promocion automatica; despues un job operacional completo termino en 49 s y
  fue promocionado manualmente con exito al modelo vivo. `0.2.212` incorpora la
  promocion en segundo plano con progreso visible y bloqueo de clics duplicados,
  ya validada en HA real. `0.2.213` incorpora el descarte con confirmacion de
  candidatos terminales no promocionados y la limpieza de sus copias privadas
  tanto en HA como en el worker. Esa revision
  tambien compacta la pantalla HA + dos workers, ordena todas las columnas con
  fechas normalizadas y retira de Observaciones el panel GIS heredado que no
  correspondia a un job identificable. `0.2.214`, publicada y pendiente de
  instalar, corrige la busqueda de cualquier campo de Observaciones sobre el
  conjunto completo antes de paginar; Enter y el debounce envian el filtro y
  reinician la lista en pagina 1.
- `0.2.207` fue ejecutada realmente en HA el 2026-07-18: `Reconstruir todas`
  completo las cuatro fases en 4 min 44 s. En local ya se verificaron 126
  features (66 favorables/60 desfavorables), sin discrepancias con
  `prediction_favorable`, y 125 filas entrenables (65/60) porque una observacion
  favorable sigue en borrador. Queda, si se considera necesario, comprobarlo
  tambien visual/operativamente en HA.
- `0.2.199` fue validada en HA por el usuario el 2026-07-11: MapLibre protegido
  funciona y el popup largo muestra `Pluja` en `Valores IDW`.
- `0.2.204` fue validada en HA el 2026-07-16: el flujo completo de subida,
  preview, asociacion y guardado de un video de 30,4 MB funciona; la conversion
  tarda unos 5-10 segundos y el resto es casi instantaneo.
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
  `mushroom_gis_mappings_ui.py`; setales en `mushroom_known_sites_ui.py` y la
  plataforma de computo en `mushroom_workers_ui.py`.
- Usar patrones existentes y evitar refactors grandes si no son necesarios.
- En desarrollo local usar siempre `.venv/bin/python` (Python 3.11), igual que
  el contenedor y HA. No usar el Python del sistema. La migracion a Python 3.14
  se tratara como tarea separada.
- La navegacion de la WebUI debe conservar el contexto de llamada: al cerrar o
  volver, restaurar formulario/borrador o lista con seleccion, filtros, orden y
  scroll. No crear versiones divergentes del mismo modal segun el origen.
- La release instalada `0.2.211` contiene el coordinador externo y mantiene
  ambos interruptores seguros por defecto y la reconstruccion HA como fallback.
  No crear una imagen de desarrollo/sideload.

## Fuente de verdad de setas

Para las observaciones, la fuente operativa actual es HA real y la revisión se
realiza allí:

```text
/share/rainmapper/mushroom-data/
```

La ruta local es una copia fresca del estado de HA para pruebas y comprobaciones;
no tratarla como una fuente autoritativa independiente ni sobrescribir HA desde
ella sin una operación de sincronización explícita y verificada:

```text
docker-data/mushroom-data/
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

Para release HA: seguir `docs/release-flow.md` paso a paso. Incluye bump de
version en tres sitios, actualizacion de CHANGELOG.md, cache-busters, build
multi-arch, commit y aviso al usuario. No retrasar una prueba en HA por
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
