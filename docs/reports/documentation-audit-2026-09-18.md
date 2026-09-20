# Auditoría documental contra el repositorio — 18/09/2026

## Alcance y evidencia

Revisión solicitada por el usuario: actualizar documentación sin suponer el
estado del proyecto. Base comprobada con `git log -1`, `git rev-parse` y
`git status --short`: HEAD y referencia local `origin/inicial` en `81a6b0b`
(Release Home Assistant 0.2.312). No es una nueva consulta al remoto.
Había documentación de confirmación Safari sin commit, observaciones personales
modificadas y un encargo de análisis de geocodificación no versionado.

El repositorio contiene 182 Markdown versionados. La revisión se centra en los
puntos de entrada, arquitectura, continuidad, release, operación y funcionalidades
recientes; no acredita una revisión línea a línea de todos los anexos científicos.
Se consultó primero Codebase Memory. Las búsquedas de clases recientes del mapa
no devolvieron resultados suficientes; se contrastaron archivos actuales mediante
lectura directa. El índice del grafo no se tomó como prueba de inexistencia.

No se han consultado HA real, SSH, GHCR ni contenedores en esta auditoría. Tampoco
se han realizado builds, pruebas funcionales nuevas, migraciones, investigación
científica o cambios de código. Las verificaciones de publicación de esta sesión
siguen en sus informes; la confirmación Safari es evidencia del usuario.

## Hechos contrastados y correcciones

| Área | Fuente primaria del checkout | Resultado y corrección documental |
| --- | --- | --- |
| Versión HA | [config.yaml](../../rainmapper-app/config.yaml), [Dockerfile](../../rainmapper-app/Dockerfile), index de ambos visores | 0.2.312 alineada en metadata y assets. Retiradas tablas que presentaban 0.2.308/309 como estado vigente. |
| Worker | [Dockerfile](../../rainmapper-worker/Dockerfile), [Compose](../../rainmapper-local/docker-compose.worker.yml) | Default 1.1.3, versión independiente. No deducir versión efectiva del contenedor. |
| Publicación | [build-push-ha-image.sh](../../scripts/build-push-ha-image.sh), [release-flow](../release-flow.md) | Publicar/verificar imagen antes de commit/push. Una versión local más latest; límite de caché 8 GiB. Se corrigió el orden inverso y retención de dos imágenes descritos en arquitectura/README. |
| Empaquetado | [Dockerfile HA](../../rainmapper-app/Dockerfile), [.dockerignore](../../.dockerignore), [semilla](../../rainmapper-app/defaults/mushroom_observations.json) | COPY explícitos, core compartido y observaciones vacías de instalación. WU research y snapshot GBIF no se incorporan a la imagen; no confundir exclusión de la imagen con todos los archivos posibles del contexto Docker. |
| Media | [media_layout.py](../../rainmapper_core/media_layout.py), [mushroom_paths.py](../../rainmapper_core/mushroom_paths.py), [CLI](../../scripts/manage-media-layout.py), [run.sh](../../rainmapper-app/run.sh) | Marcador validado, compatibilidad legacy, overrides y migración offline explícita. Modelo/artefactos/precálculo/transferencias/caché con rutas organizadas; instalar no mueve archivos. |
| Integración mapa | [UI](../../rainmapper-app/app/mushroom_prediction_map_ui.py), [ejecutor](../../rainmapper_core/mushroom_map_execution.py), [broker](../../rainmapper_core/mushroom_map_queries.py), [worker](../../rainmapper_core/mushroom_map_worker.py) | Implementación empaquetada HA/worker, no solo preview. Configuración y publicaciones determinan datos disponibles. |
| Fallback | [prediction-mode.js](../../rainmapper_core/viewers/prediction-map/prediction-mode.js), [bootstrap](../../rainmapper_core/viewers/prediction-map/prediction-bootstrap.js) | Preferencia inicial worker. Solo rechazo 503 por indisponibilidad/ocupación reintenta una vez en local; no modifica preferencia ni reenvía consulta aceptada. |
| Temporada/suelo | [ecología](../../rainmapper_core/mushroom_map_ecology.py), [UI de predicción](../../rainmapper_core/viewers/prediction-map/prediction-mode.js) | Estado territorial independiente de fases diarias; fuera de temporada entre descartes. Suelo no determinado visible y exigencia por ficha. Se sustituyó la afirmación de ocultación total. |
| Buscador | [app.js](../../rainmapper_core/viewers/maplibre-viewer/app.js), [CSS](../../rainmapper_core/viewers/maplibre-viewer/style.css), [HTML](../../rainmapper_core/viewers/maplibre-viewer/index.html), [traducciones](../../rainmapper_core/viewers/maplibre-viewer/translations.json) | Photon directo desde navegador, envío explícito, 8 resultados, 20 s, intervalo 1 s, 50 respuestas en memoria; POI reemplazado por nueva búsqueda válida, 16 px, ayuda/créditos. |
| Diagnóstico | [ResidentReader](../../rainmapper_core/mushroom_map_execution.py), [QueryBroker](../../rainmapper_core/mushroom_map_queries.py) | stderr heredado, errores con contexto/traceback; sin reintento automático de inicialización del broker. Documentado sin atribuir causa al fallo anterior. |
| Fichas/modelos | [web_server.py](../../rainmapper-app/app/web_server.py) (`save_profile_form`, `pending_model_species_ids`), [revision vector](../../rainmapper_core/mushroom_ml_version_registry.py), [runtime](../../rainmapper_core/mushroom_map_runtime.py) | Guardar formulario no marca pendientes de reconstrucción; vector rápido no incluye perfiles. Mapa recibe perfiles privados. No inferir necesidad de entrenar por cada cambio de filtro. |
| Investigación WU | [servidor](../../local-apps/wunderground/code/station_research.py), [visor](../../local-apps/wunderground/code/web/app.js) | SQLite, cuatro estados, filtros combinables, deduplicación por ID, 30 días completos, promoción solo a candidata. Los recuentos iniciales no son estado actual de revisiones. |
| Revisión GBIF | [visor](../../local-apps/gbif/code/gbif-viewer.js), [guía](../../local-apps/gbif/docs/guide.md) | Cuatro estados; `approved` corresponde a Aceptada y no debe confundirse con `accepted` de WU. No importación operativa automática. |
| Meteorología/ejecución | [config HA](../../rainmapper-app/config.yaml), [run.sh](../../rainmapper-app/run.sh), [pending Parquet](../../rainmapper_core/weather_history_pending.py) | Serve/schedule ya implementados; particionado opcional, default false. README Docker aún lo presentaba como futuro: corregido. |

## Documentos actualizados

- README general, README Docker y README/DOCS de la app: alcance, entradas del
  mapa, búsqueda, media, release y operación implementada.
- Arquitectura: rutas, módulos de predicción, fallback, fenología, buscador,
  publicación y estado histórico del registry.
- Contexto activo: resumen vigente, fuentes, límites y pendientes. Se conserva
  íntegramente el contenido anterior en
  [archivo previo](session-context-before-doc-audit-2026-09-18.md), identificado
  como histórico. No se borran decisiones científicas, huellas ni evidencias.
- Entrada de Codex, enlace de inicio del handoff histórico, TODO y seguimiento
  del mapa: distinguen estado vigente y evolución histórica.
- Especificación central: decisiones vigentes de fallback/descartes y estado del
  buscador; los diseños y pruebas anteriores mantienen sus fechas.
- Diagnóstico runtime y guía WU: logs de lectores/broker y recuentos variables.
- Informe 0.2.312: conserva confirmación del usuario en iPhone y Safari del Mac.
- Ejemplo de commit de release: retirado un coautor fijo ajeno a la ejecución;
  no modifica requisitos de validación, aceptación ni publicación.

## Límites y asuntos abiertos

La revisión GIS sigue aplazada. Cifras/huellas de GIS, datos descargados GBIF,
revisión de candidatas WU y rendimiento de HA real no se han recalculado.
El código demuestra capacidades, no calidad de predicción ni cobertura nacional.
Las confirmaciones de instalación/funcionamiento del usuario no se presentan
como una inspección remota realizada ahora.

`docs/ui/rainmapper-geocoding-options-review.md` es un encargo independiente no
versionado, preservado. No se ha ejecutado su comparativa comercial/de proveedores
ni alterado la integración Photon. Las observaciones personales tampoco se editan.

## Validación documental

Revisión del diff, parseo JSON del informe 0.2.312 y comprobación de enlaces
relativos a archivos: 192 enlaces en 16 documentos, sin destinos ausentes
en este workspace (incluye archivos locales ignorados, no garantizados en un clon).
`git diff --check` correcto.
No se repite smoke: solo documentación, sin cambios ejecutables ni de imagen.
