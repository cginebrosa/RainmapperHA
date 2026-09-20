# Suspensión manual de modelos de predicción

Suspensiones disponibles en HA 0.2.314. La separación en JSON independiente y
su exportación/importación se publican en 0.2.315, validada en HA local.

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

- En HA 0.2.314, reglas en `prediction_model_suspensions` del registro privado
  `mushroom_ml_version_registry.json`; no en las semillas del repositorio.
- Desde 0.2.315, archivo hermano `mushroom_ml_prediction_policy.json`,
  con `schema_version`, `kind` y `suspensions`. El registro guarda únicamente
  `prediction_policy_file` como referencia. La migración escribe primero las
  reglas y después la referencia; un archivo referenciado ausente o inválido
  produce error, sin reactivar silenciosamente los modelos.
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

### Exportación/importación desde 0.2.315

El panel aparece cerrado inicialmente. **Exportar** descarga solo las reglas;
**Importar** permite seleccionar un JSON o pegarlo y exige confirmar el reemplazo
de todas las reglas actuales (una lista vacía las retira). Se validan modelos,
especies y revisión antes de guardar. No se copian generaciones ni rutas de
artefactos. No importar este formato como registro completo en HA 0.2.314.

Los snapshots sellados del worker conservan las reglas efectivas dentro del
contrato, sin referencias al archivo vivo del coordinador. El mapa incorpora la
política actual a su identidad y caché sin republicar los modelos pesados.
Una política distinta invalida la reutilización del precálculo publicado.

Comprobación del 19/09: smoke de 1.660 tests, 48 omitidos; HA local reconstruido
y ocho archivos modificados cotejados con el contenedor por SHA-256. Chrome:
panel cerrado, selección de archivo, vista previa de siete reglas, confirmación,
POST real y exportación posterior coincidente; registro de generaciones idéntico
antes/después. Posteriormente, el 20/09, se reconstruyeron ambos contenedores
y se completó reconstrucción, entrenamiento base/multiversión y precálculo
recibido/activado. [Validación integrada de 0.2.315](SMI/adoption-2026-09-20/validation.md).

Fuentes: `rainmapper_core/mushroom_ml_prediction_policy.py`,
`mushroom_ml_policy_store.py`,
`mushroom_ml_version_registry.py`, `mushroom_ml_multiversion_comparison.py`,
`mushroom_map_runtime.py`, `rainmapper-app/app/mushroom_model_settings_ui.py`
y el handler `set_prediction_model_policy` de `web_server.py`.

## Validación de 0.2.314 y aplicación en HA real

HA local y el único worker reconstruidos con el mismo código candidato.
Paridad efectiva de 206 archivos HA y 109 worker, sin diferencias, revalidada
antes del bump mecánico a 0.2.314. Smoke: 1.649 tests, 48 omitidos.
Configuración de coordinadores del worker conservada.

Siete reglas guardadas mediante el formulario en HA local para
`lactarius_deliciosus`: HGB/KNN/SVM-V2, HGB-V3 core y físico, HGB-V4
meteorología extendida y balance climático. El usuario confirmó el comportamiento
del mapa local y autorizó publicar. Estas reglas son datos privados de cada
instalación: la imagen no las copia a HA real. El 19/09 se aplicaron las siete
reglas mediante el formulario de HA real 0.2.314, conservando sus generaciones;
se revalidó su presencia por SMB. No requiere reentrenar. El mapa las aplica
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
