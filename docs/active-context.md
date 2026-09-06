# Active Context

Ventana operativa de RainmapperHA al cierre del 6 de septiembre de 2026. No es
un histórico. Revalidar siempre `pwd`, rama, HEAD, worktree, fuentes y runtimes
antes de asumir que este estado continúa vigente.

## Estado comprobado

- Repositorio: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`;
  el commit de release HA `0.2.293` debe ser el HEAD al retomar.
- El fichero `mushroom-data/mushroom_observations.json` queda modificado fuera
  del commit de release porque pertenece al usuario. No limpiarlo, editarlo,
  restaurarlo ni incluirlo ciegamente en otro commit.
- Fuente de datos local viva para entrenamiento y pruebas:
  `docker-data/mushroom-data/`. `mushroom-data/` contiene defaults para una
  instalación nueva; no sustituye los datos vivos descargados de HA.
- Versiones declaradas en fuente: HA `0.2.293` en
  `rainmapper-app/config.yaml` y worker `1.0.39` en
  `rainmapper-worker/Dockerfile`.
- HA `0.2.293` está publicada en GHCR. Los tags `0.2.293` y `latest` comparten
  el digest `sha256:3dce0e5cecec99645f89313925d93cf6ff594711a383fa413d13ba276bc57e03`
  y contienen manifests `linux/amd64` y `linux/arm64`.
- El contenedor local `rainmapper-local-rainmapper-ha-ui-1` se comprobó activo
  con la imagen `sha256:08a111d121f66c6554926c399e8352b5441a39b2a75e281edc3ebd1bcc81db92`.
  Dentro del contenedor, `EXPERIMENT_ESTIMATOR_IDS` contiene
  `knn_distance_beta_smoothed_v2` y no el KNN antiguo.
- El worker local se comprobó activo y healthy con
  `rainmapper-worker:1.0.39`, imagen
  `sha256:55849222b054c6cc66d29541d3f5a678001c86e1c86134f3f59fb2f1e9316ef0`.
  Conserva el volumen, la identidad `worker_1a9a232c20fe2ee2`, el emparejamiento
  y las cachés; empaqueta el nuevo módulo de calibración y anuncia el KNN
  suavizado como único KNN activo.

## Cambio KNN implementado y materializado en local

- El único KNN activo para entrenamientos nuevos en el código fuente es
  `knn_distance_beta_smoothed_v2`. Aplica `(7p + 1) / 9` a la probabilidad
  cruda: elimina ceros y unos exactos, conserva el orden de los casos y lleva
  un `p=1` crudo a `8/9`.
- `knn_distance_v1` permanece soportado únicamente para cargar, mostrar y
  auditar generaciones históricas. No compiten dos KNN en entrenamientos
  nuevos.
- La misma clase se usa en entrenamiento, hold-out e inferencia para evitar
  diferencias entre evaluación y producción.
- El registro empaquetado asigna el nuevo KNN a los perfiles V2, V3 y V4. El
  mecanismo `ensure_seeded` refresca esas definiciones en el registro
  persistente conservando generaciones y estados instalados.
- La UI muestra `>99 %` y `<1 %` para probabilidades predictivas que de otro
  modo se redondearían a certeza. No altera la probabilidad interna ni los
  porcentajes empíricos de acierto como `100 % (13/13)`.
- Validación final de release: smoke completo superado con 1.288 pruebas,
  compilación Python, parseo JavaScript y shell, fixtures y
  `git diff --check`.

## Artefactos operativos locales comprobados

- El registro persistente instala V2, V3, V4, V5w y V6w desde el lote
  `local_operational_20260905T231844Z`: 406 observaciones elegibles, 8 especies,
  11 perfiles y 636/636 artefactos correctos, sin fallos.
- El catálogo de ajustes pertenece al mismo lote: 636 decisiones, 80 del KNN
  suavizado. Se cargaron y verificaron los 636 modelos instalados; los 80 KNN
  serializan `BetaSmoothedKNeighborsClassifier` con 7 vecinos, pesos por
  distancia, tamaño efectivo 7 y prior beta `alpha=1`.
- El hold-out contiene 27.536 filas físicas únicas y 2.880 métricas completas,
  sin valores no finitos. Los 10.640 valores KNN quedan entre `1/9` y `8/9`,
  sin ceros ni unos exactos. La generación nueva no contiene ninguna aparición
  de `knn_distance_v1`.
- El precálculo activo es la revisión 40, artefacto
  `sha256:2cf9112367c3565abe76c4984c248f753e87208f22712b43eb28f7181dafb447`,
  cobertura 2026-09-06--2026-09-12 y 29.917.184 bytes. Su fichero coincide con
  el recibo (`sha256:c21f6f3bd237f6003f9583fe90976a0824fe628f071a892c6de7be216624300d`).
- El SQLite devuelve `quick_check=ok`, cero violaciones de claves externas y
  cero páginas libres. Materializa 504 coberturas y predicciones base, 420
  miembros, 623 respuestas lógicas y 143 payloads deduplicados; las vistas se
  reparten en 560 `query`, 56 `week` y 7 `recommender`. Todo el JSON, incluido
  el contenido comprimido, tiene cero apariciones del KNN antiguo y ningún
  valor no finito.
- La carpeta obsoleta `docker-data/mushroom-data/predictor_precompute` se eliminó
  tras comprobar que solo contenía un SQLite de cero bytes y `staging` vacío.
  El estado activo reside en `docker-media/rainmapper/predictor_precompute/`.

## Auditoría científica cerrada

- La auditoría P0 cubrió Rovelló, Edulis, Pinícola, Aereus y Ou de reig, todas
  sus versiones/ganadores auditables y los mismos grupos hold-out de 14 y 7
  días. No se encontró un fallo general que justifique V7.
- La señal útil de lluvia se concentra principalmente entre 15 y 30 días; la
  temperatura alta es el freno más fuerte. Balance hídrico/estado del suelo y
  lluvia antecedente aportan señal, pero una interacción lluvia × suelo añadida
  explícitamente no mejora de forma estable.
- La calibración genérica Platt/isotónica empeoró KNN. El suavizado elegido
  mejoró Brier `0,1618 → 0,1554`, ECE `0,1310 → 0,0821` y log-loss
  `2,1054 → 0,4863`, manteniendo ROC-AUC. Al repetir el selector cambió solo
  5 de 301 decisiones especie--área--día.
- Para racha seca no se adopta todavía `<1 mm = seco`: la prueba no fue estable.
  La lluvia continua, acumulados y balance hídrico conservan siempre las
  cantidades inferiores a 1 mm. La hipótesis futura preferida es comparar el
  contador actual, el umbral de 1 mm y la ausencia del contador.
- Llanega negra, Marçot y Múrgola negra se aplazan hasta que sus hold-outs
  externos contengan ambas clases.
- Sporas.io es solo fuente de preguntas. «Lluvia de activación» no es ground
  truth ni una variable ad hoc que deba copiarse.

## MOD_0001 y ventana de fructificación

- `MOD_0001` sigue vigente: ecología, lluvia y ventanas externas pueden
  mostrarse como diagnóstico, pero no modifican probabilidad, ranking,
  aplicabilidad, color ni recomendación.
- La política de aplicabilidad conserva una desviación exclusivamente de lluvia
  como advertencia, no como veto por sí sola. Otros motivos fuera de dominio sí
  pueden producir fallback o abstención.
- En Rovelló, `fruiting_timing` es `unknown`: los límites de retardo a cero del
  perfil eran placeholders, no una ventana biológica válida. La UI actual hace
  bien en ocultar ese texto. No rellenar con cifras de Sporas.io.
- Una futura indicación «activa/terminando» solo debería volver como tendencia
  predictiva derivada de la secuencia aprendida de siete días y requerirá una
  decisión semántica explícita. No está implementada.

## Próxima secuencia autorizable

1. Instalar HA `0.2.293` en el equipo real solo con autorización explícita.
2. Verificar versión, arranque, almacenamiento persistente y migración del
   registro sin borrar generaciones fuera de la política de retención.
3. Ejecutar allí entrenamiento y después precálculo, auditando las mismas
   identidades, conteos y ausencia del KNN antiguo que en local.
4. Medir especialmente la activación del SQLite de unos 29 MB en la RPi4.

## Riesgos y dudas activas

- La generación y el precálculo auditados son locales; todavía falta comprobar
  el ciclo equivalente en HA real después de instalar `0.2.293`.
- La RPi4 sufrió anteriormente una publicación/validación síncrona muy lenta
  con un SQLite grande. El artefacto deduplicado local es de unos 29 MB, pero
  falta medir allí el ciclo real completo.
- El commit de release excluye expresamente las observaciones del usuario; ese
  fichero seguirá apareciendo como modificación local después del cierre.

## Archivos relevantes

- Decisión y evidencia científica:
  `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.
- Diseño de racha seca:
  `docs/mushrooms/literature/prediction/rainmapper_dry_spell_variable_review.md`.
- Suavizado KNN:
  `rainmapper_core/mushroom_ml_probability_calibration.py` y
  `rainmapper_core/mushroom_ml_experiment_trainer.py`.
- Registro: `mushroom-data/mushroom_ml_version_registry.json` y
  `rainmapper_core/mushroom_ml_version_registry.py`.
- UI: `rainmapper-app/app/mushroom_predictor_ui.py`.
- Auditoría reproducible: `scripts/audit-mushroom-probability-extremes.py`.
- Datos vivos: `docker-data/mushroom-data/`.
- Modelos y precálculo actuales:
  `docker-media/rainmapper/mushroom-derived/ml_models/` y
  `docker-media/rainmapper/predictor_precompute/`.
