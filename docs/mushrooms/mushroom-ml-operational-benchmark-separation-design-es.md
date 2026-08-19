# Separación entre entrenamiento operativo y benchmarks científicos

Estado: **FASES 1 Y 2 IMPLEMENTADAS EN EL WORKTREE, PENDIENTES DE RELEASE**.

Validación local: 327 pruebas dirigidas y smoke completo de 915 pruebas,
incluidas compilación Python/JavaScript/shell y comprobación de whitespace. Con
autorización posterior se construyó e instaló únicamente la imagen HA local
`rainmapperha:local-ha-ui`; no se hizo bump, publicación, instalación en HA
real ni cambio del worker normal.

## Cadena comprobada y separación implementada

Antes de esta fase, tanto el coordinador externo como
`mushroom_local_full_update` encadenaban reconstrucción, ML v0 y un único job
V2–V6. El resultado multiversión se instalaba al completar su transporte y la
promoción posterior publicaba reconstrucción+ML v0. Esto hacía que el supuesto
benchmark pudiera escribir `runtime-batch.json` antes de la promoción lógica y
obligaba a preparar y ajustar V3–V6 en cada actualización habitual.

La fase 1 deja dos contratos explícitos:

- `job_purpose=operational`: el registro resuelve exclusivamente la versión
  activa y sus perfiles `operational_eligible`; con el registro actual es
  `altitude_v2`, con fixed y lag. El preparador solo materializa sus dos fuentes
  V3 comunes, el plan exige el conjunto exacto de artefactos y cualquier fit
  fallido invalida el candidato.
- `job_purpose=benchmark`: permite resolver uno o varios perfiles V2–V6 y
  materializa solo sus entradas, evaluación hold-out y dependencias; se ejecuta
  únicamente mediante `Ejecutar benchmark científico`.
  El resultado se archiva bajo `ml_models/benchmarks/<batch_id>` y nunca escribe
  el descriptor runtime ni inicia promoción.

En el worker externo, HA crea el snapshot y la especificación, el worker
prepara/entrena y sube todos los ficheros declarados, y HA vuelve a verificar
identidad, hashes, contadores, alcance de especies y plan. Un resultado
operativo queda en staging; solo la promoción conjunta lo instala, publica
reconstrucción+ML v0, libera la caché y limpia pendientes. Si falla antes de
completar esa generación, se elimina el batch nuevo y se restaura exactamente
el descriptor anterior. Workers antiguos sin `ml_job_purpose_v1` no pueden
recibir ninguno de los dos jobs nuevos.

El ejecutor HA local aplica la misma resolución, preparación, runner,
verificación e instalación. Conserva el descriptor anterior y ejecuta rollback
compensatorio ante fallo. Su benchmark manual crea otro snapshot, archiva el
resultado y termina sin liberar caché ni promover artefactos.

La UI presenta las dos acciones por separado y solo muestra promoción completa
para un job operativo enlazado y terminado. La fase 2 añade selección de
perfiles comparables, informe persistente, historial y `Ver comparación`. No
añade promoción desde benchmark; esa capacidad continúa reservada a la fase 4.

Cada benchmark conserva dentro del batch archivado la selección, el snapshot,
el plan completo, los artefactos, los resultados y tiempos de cada fit,
`benchmark-report.json` y las predicciones filtradas en
`holdout-predictions.jsonl`. El coordinador verifica hashes e identidades antes
de archivar. El informe no depende de la retención de la cola de jobs y mantiene
separadas las métricas por especie, contrato, horizonte y estimador.

## Problema

La acción actual `Reconstruir y reentrenar todo` encadena reconstrucción, ML v0
y el catálogo comparativo V2–V6. La ejecución real observada el 2026-08-18
empleó aproximadamente 2 min 29 s en reconstrucción, 1 min 12 s en ML v0 y
39 min 45 s en V2–V6. El batch verificable
`local_v2_v6_20260818T162939Z` planificó 436 fits, produjo 432 artefactos y
registró cuatro fallos V5. Ejecutar toda la investigación en cada actualización
operativa impide iterar con rapidez y mezcla dos objetivos distintos.

Además, V2–V6 no forman una escalera donde cambie una sola variable. Entre
versiones cambian contratos de muestras/targets, variables, algoritmos,
representación temporal y pooling. Una mejora entre versiones completas no
permite atribuir limpiamente qué cambio la produjo.

## Decisión de diseño

Se separarán dos flujos, manteniendo intacto el V2 operativo hasta que exista
una promoción posterior, explícita y válida.

### 1. Reconstruir y reentrenar operativo

- Reconstruye las entradas actuales y ajusta únicamente la generación que usa
  el Predictor normal.
- Mientras no se promocione otra generación, esa referencia sigue siendo V2,
  con sus contratos fijo y de retardos necesarios.
- Conserva instalación atómica, verificación de entradas, rollback y la
  generación anterior ante cualquier fallo.
- No recalcula automáticamente todo V2–V6.

Separar el flujo no promociona, sustituye ni modifica por sí mismo el V2
instalado. Tampoco autoriza a borrar V3–V6: deben seguir registrados y
reproducibles.

### 2. Ejecutar benchmark científico

- Es una acción independiente y bajo demanda.
- Permite seleccionar perfiles/versiones compatibles y usa para todos ellos el
  mismo snapshot inmutable, filas, targets, contratos temporales y splits que
  declare la comparación.
- No cambia el Predictor ni promociona automáticamente al resultado con mejor
  métrica.
- Persiste artefactos, predicciones hold-out, métricas y tiempos con identidad
  suficiente para reproducir el resultado.
- Un runner meteorológico posterior no invalida el informe histórico, porque
  este sigue ligado a su snapshot; sí impide promocionarlo directamente si las
  entradas vivas ya no coinciden.

La fila del trabajo terminado ofrece `Ver comparación`. El informe debe mostrar
por especie, contrato, horizonte y estimador: Brier y prevalencia de referencia,
delta emparejado, ROC-AUC, calibración, soporte, abstenciones/no convergencias y
duración. No se promedian especies para proclamar un ganador universal.

## Primer experimento controlado: V3 core frente a V3 physical

`Biology V3` no contiene hoy variables biológicas directas de bosque, huésped o
sustrato. Su aportación principal es el contrato de muestras, targets,
observaciones relacionadas y validación por floradas; su `X` activo es
fundamentalmente meteorológico.

La primera comparación nueva mantendrá exactamente iguales filas, targets,
splits, contratos y estimadores:

- `V3 core`: meteorología IDW y columnas activas actuales.
- `V3 physical` (nombre provisional de UI: `V3+`): las mismas columnas más
  balance hídrico y SMI calculados causalmente desde la meteorología IDW.

No se sobrescribe el contrato V3 actual: `V3 physical` debe tener identidad de
perfil/feature set propia. Primero se evalúa el bloque físico completo. Solo si
aporta una mejora repetible se abre una segunda ablación para distinguir
`+balance`, `+SMI` y `+balance+SMI`; así no se multiplican modelos antes de
demostrar que el bloque aporta señal.

## Promoción desde un benchmark

El contrato extensible, la identidad de perfil/generación, los gates y la
transacción de promoción/rollback se detallan en
`docs/mushrooms/mushroom-ml-generic-profile-promotion-plan-es.md`. V3/V3+ es el
primer corte, pero coordinación, transporte y UI no pueden resolverlo mediante
excepciones nominales que impidan aplicar el mismo flujo a otra versión.

El informe puede ofrecer `Preparar candidata completa` para una versión cuyos
perfiles técnicos estén todos presentes. No se
promociona una celda aislada ni se elige un estimador retrospectivamente sin un
contrato predeclarado. La promoción exige:

- perfil declarado `operational_eligible`;
- artefactos completos para especies, contratos y estimadores exigidos;
- paridad de variables entre entrenamiento e inferencia;
- integridad y compatibilidad del runtime;
- snapshot todavía compatible con las entradas vivas;
- confirmación humana explícita.

V3 core y V3+ físico son operacionalmente elegibles como una unidad de versión;
V4–V6 todavía no. El diseño permite habilitar otra versión actual o futura sin
ramas nominales, pero antes habrá que declarar el conjunto completo de perfiles,
inputs, contratos y política de miembros. Una vez promovida, el flujo habitual
reentrenará todos los perfiles de esa versión en lugar de V2.

## UI objetivo

Hay dos acciones principales:

1. `Reconstruir y reentrenar operativo`.
2. `Ejecutar benchmark científico`.

`Ver informe` aparece para un único perfil y `Ver comparación` para varios como
acción contextual de cada benchmark terminado; ninguna inicia otro cálculo.
La fila terminada conserva la selección y resume fits, fallos, métricas y
predicciones hold-out, y el historial se actualiza al cerrar el job. Dentro del
informe puede aparecer `Promocionar`, sujeto a los gates anteriores. Un
historial permite reabrir informes persistidos.

## Entrega por fases

### Fase 1 — separar ejecución sin cambiar el Predictor

- [x] Introducir identidad explícita de job operativo frente a benchmark.
- [x] Resolver desde la generación activa qué contratos necesita el entrenamiento
  habitual; inicialmente debe seguir resolviendo V2.
- [x] Retirar el catálogo V2–V6 completo de la cadena habitual.
- [x] Mantener la acción comparativa existente como trabajo independiente.
- [x] Probar que un fallo conserva el V2 instalado y que no cambia ninguna
  predicción antes de una promoción.

### Fase 2 — benchmark manual e informe persistente

- [x] Generalizar la selección de perfiles sobre el job comparativo existente.
- [x] Empezar sin selección, conservar exactamente los perfiles lanzados y
  limitar preparación/evaluación al alcance seleccionado.
- [x] Permitir cancelar con estado terminal explícito los benchmarks HA locales.
- [x] Guardar métricas y duración por fit/versión/perfil/estimador, no solo
  contadores globales.
- [x] Persistir predicciones hold-out y diagnóstico de abstenciones/fallos.
- [x] Añadir informe/comparación contextual, resumen del resultado e historial
  actualizado al terminar.
- [x] Mantener el Predictor y la promoción fuera del benchmark.

### Fase 3 — V3 physical

- [x] Registrar el perfil sin modificar V3 core.
- [x] Construir balance y SMI desde el mismo IDW en entrenamiento e inferencia.
- [ ] Ejecutar la comparación real V3 core/V3 physical sobre filas y splits
  idénticos; el soporte de planificación y evaluación ya está implementado.

### Fase 4 — promoción genérica

- [x] Declarar elegibilidad técnica de todos los perfiles de una versión.
- [x] Preparar desde el informe una candidata nueva de la versión completa sin
  modificar Predictor.
- [x] Añadir activación humana separada, journal, instalación compensatoria y
  rollback exacto de registro+descriptor.
- [x] Hacer que el entrenamiento habitual resuelva dinámicamente todos los
  perfiles de la versión activa.
- [x] Hacer que Predictor muestre cada perfil y sus contratos fixed/lag.
- [ ] Reconstruir HA local con autorización y validar el recorrido real.

### Fase 5 — experimentos posteriores

- Solo si el bloque físico aporta señal, ejecutar sus ablaciones.
- Sustituir experimentalmente V5-365 por variantes V5-30/60/90, sin borrar el
  control histórico; V6 se estudiará después sobre ventanas justificadas.
- Mantener estos experimentos fuera del entrenamiento habitual.

## Riesgos y gates

- No confundir rapidez con validez: operativo y benchmark deben usar la misma
  tubería causal cuando comparen el mismo perfil.
- No dejar al Predictor sin su conjunto completo de artefactos al separar jobs.
- No permitir promoción de un benchmark obsoleto respecto a entradas vivas.
- No declarar causalidad por una mejora predictiva ni elegir sobre el mismo
  hold-out repetidamente sin nueva evidencia.
- El soporte por especie/campaña sigue siendo pequeño.
- Antes de publicar se mantienen como gates tests de planificación, transporte,
  persistencia, UI, promoción, rollback, concurrencia con runner y paridad
  HA/worker.
