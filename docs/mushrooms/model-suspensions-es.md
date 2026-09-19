# Suspensión manual de modelos de predicción

Implementación local del 19/09/2026, todavía sin publicar en HA real.

En **Workers y trabajos → Modelos de predicción** se puede suspender un
estimador/perfil/versión para una especie o para todas, indicando el motivo.
La lista muestra las suspensiones y permite reactivarlas. Una suspensión global
sigue teniendo efecto aunque se retire la suspensión particular de una especie.
Guardar desde una pestaña desactualizada se rechaza para evitar pisar cambios.

La suspensión impide servir IFF con ese modelo en el Predictor y el mapa,
tanto en HA como en el worker. La selección intenta el siguiente candidato
admisible de su cadena; si no queda ninguno, se abstiene. No se sustituyen
resultados por cero ni se modifica el ranking científico archivado.

**No impide entrenarlo.** Se conservan los modelos y sus métricas para poder
auditarlos y reactivarlos. Un reentrenamiento o una actualización de definiciones
no debe borrar las decisiones manuales. Tras cambiar la política, preparar de
nuevo la semana para disponer de un precálculo acorde con ella.

## Persistencia y transporte

- Reglas en `prediction_model_suspensions` del registro privado
  `mushroom_ml_version_registry.json`; no en las semillas del repositorio.
- Identidad: versión, perfil, estimador y especie (`*` significa todas).
  Motivo, fecha y actor acompañan a cada regla.
- El registro viaja en los contratos existentes del worker. Las reglas forman
  parte de la identidad del runtime y del precálculo, pero no cambian la huella
  del contrato de entrenamiento.
- El mapa publica una nueva identidad al cambiar el registro. El filtro se
  aplica antes de reutilizar inferencia en caché. Con reglas activas se exige
  la capacidad `prediction_model_policy_v1` para delegar ejecución.
- Máximo 512 reglas y registro serializado limitado a 256 KiB al guardar.
  No se incorporan informes de auditoría ni datos GIS a esta configuración.

Fuentes: `rainmapper_core/mushroom_ml_prediction_policy.py`,
`mushroom_ml_version_registry.py`, `mushroom_ml_multiversion_comparison.py`,
`mushroom_map_runtime.py`, `rainmapper-app/app/mushroom_model_settings_ui.py`
y el handler `set_prediction_model_policy` de `web_server.py`.

## Validación local completada

HA local y el único worker reconstruidos con el mismo código candidato.
Paridad efectiva de 206 archivos HA y 109 worker, sin diferencias, revalidada
antes del bump mecánico a 0.2.314. Smoke: 1.649 tests, 48 omitidos.
Configuración de coordinadores del worker conservada.

Siete reglas guardadas mediante el formulario en HA local para
`lactarius_deliciosus`: HGB/KNN/SVM-V2, HGB-V3 core y físico, HGB-V4
meteorología extendida y balance climático. El usuario confirmó el comportamiento
del mapa local y autorizó publicar. Estas reglas son datos privados de cada
instalación: la imagen no las copia a HA real. Tras instalar hay que configurarlas
en Workers y trabajos de HA real; no requiere reentrenar. El mapa las aplica
al sincronizar su runtime, y el Predictor necesita renovar su precálculo.

### Resultado del entrenamiento comprobado

El trabajo `worker_job_JW-q5RQnbRFToGxQ` terminó e instaló el lote
`operational_20260919T014018Z`: 714 artefactos, con las siete reglas conservadas.
Se verificaron por SHA los 14 artefactos de los siete modelos suspendidos
(fixed y lag): la política no los ha eliminado del entrenamiento.
En el runtime sincronizado del worker se comprobaron 56 combinaciones de modelo
suspendido/horizonte, todas con `model_suspended`, también ante caché poblada.
Las 35 selecciones de rovelló en Pradell, Capolat, Vallcebre, Gósol y Urús
respetan la política y eligen Smooth Partial V6 de 30 días. Paridad completa del
mapa HA local/worker comprobada de nuevo en Pradell y Capolat con este lote.
Evidencias: `tmp/model-settings-20260919/training-verification.json`,
`trained-runtime-verification.json` y `api-validation.json`.

El precálculo local `worker_job_O7yzs0AqVMK6` terminó y se activó en la revisión
68 con el lote nuevo y las siete reglas. Recibo y SHA del SQLite verificados;
525 miembros inspeccionados, 14 registros suspendidos correctamente no disponibles,
ningún ganador suspendido en los payloads persistidos (2.229 apariciones de
ganadores, incluyendo repeticiones). Evidencia:
`tmp/release-0.2.314/precompute-verification.json`.
La validación técnica no acredita precisión micológica.
