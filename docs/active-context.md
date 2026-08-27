# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-27

- Workspace `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  La base era `4b6422d` (`Release Home Assistant 0.2.267 and worker 1.0.18`)
  y la corrección posterior se publica coordinadamente como HA `0.2.268` y
  worker `1.0.19`, en `7fe0974`.
- HA real arrancó en `0.2.268`, confirmado por el usuario. El worker normal se
  actualizó a `1.0.19` preservando el volumen `rainmapper-worker-data`; quedó
  `healthy` e `idle`, con la misma identidad `worker_1a9a232c20fe2ee2`, el
  mismo dataset de 6.341.520.039 bytes y la misma caché Predictor de
  253.631.110 bytes. Tras el reinicio de HA, el worker registró
  `heartbeat_restored` a las 08:43:49 del 2026-08-27.
- El último banner aportado, anterior a `0.2.266`, mostraba Python `3.11.16`;
  confirmar de nuevo el intérprete si una tarea futura depende de su versión
  exacta.
- La entrega de rendimiento, Predictor y release coordinada está contenida en
  `7fe0974`. Preservar cualquier cambio o fichero no rastreado que aparezca en
  una sesión posterior.
- El grafo Codebase Memory tenía 10.647 nodos y 45.213 relaciones y ya no
  devolvía símbolos retirados de `mushroom_ml_version_promotion`; no fue
  necesario reindexarlo.
- Los tags HA `0.2.268` y `latest` comparten el digest multi-arquitectura
  `sha256:cc94b6b272c7256ab4796358fcdbb20f65e731e7707e5349a42dadd52fb27c95`.
  El worker `1.0.19` quedó construido como ARM64 y exportado en un TAR privado
  de 293 MiB con SHA-256
  `8ae143e2973f99536103f0431af5bd0420287258affaff597ceefcf6ab8d6a67`.

## Estado operativo vigente

- HA `0.2.264` reveló que el registro persistente ML 1.0 no podía leerse con el
  schema nuevo. HA `0.2.265` añadió la migración 1.0→2.0 con copia exacta previa
  y arrancó sin errores de reconciliación. HA `0.2.268` es la versión instalada
  actual confirmada por el usuario.
- `0.2.267` obtiene del registro activo las versiones operativas instaladas en
  vez de usar una lista fija. La reconstrucción permite seleccionar cualquier
  subconjunto instalado de V2, V3, V4, V5w y V6w y conserva esa selección a
  través de rebuild, ML v0, entrenamiento multiversión y promoción. La versión
  preferida sigue siendo una elección independiente.
- La prueba local terminó correctamente y el Predictor reconoció las cinco
  versiones. La validación visual local del selector y de la predicción quedó
  confirmada por el usuario.
- Las primeras mediciones optimizadas fueron 534,571 s en frío y 473,654 s en
  caliente, pero ya no son líneas base válidas de aceptación: se comprobó que
  cuatro perfiles completos carecían de probabilidades hold-out por una
  resolución incorrecta del contrato temporal. El ciclo local corregido midió
  591,561 s, con 714/714 ajustes, cero fallos, calidad completa y promoción
  atómica. Una
  predicción semanal dirigida de Edulis/V6/todas las áreas midió 7,623–7,684 s.
  El transporte de resultados del Predictor admite 64 MiB con preflight y
  timeout final de 60 s; el formulario solo calcula mediante `Predecir`, pero
  recalcula en memoria las áreas válidas cuando cambia la especie.
- En HA real se ejecutó la cadena completa con 374 observaciones elegibles,
  ocho especies y las cinco versiones. El batch multiversión
  `operational_20260825T221049Z` terminó con 636/636 ajustes y cero fallos. La
  evidencia de la cola muestra promoción completada y limpieza terminal.
- Queda una comprobación funcional corta, no una reconstrucción nueva:
  confirmar en la UI de HA real que el Predictor ofrece las cinco versiones,
  que desapareció el aviso de identidad de origen desconocida y que una
  predicción real termina y presenta resultados con el nuevo transporte.

## Retención ML y espacio de backups

- La opción real **Apply ML storage retention** fue habilitada por el usuario.
  El arranque registró
  `Mushroom storage reconciliation mode=apply removed=74 errors=0`, seguido de
  servidor y coordinador operativos. Una predicción posterior y el reentreno
  completo funcionaron.
- `ml_storage_reconciliation_apply` conserva `false` como valor por defecto del
  producto, pero la opción del HA real está activa. No cambiarla, no borrar
  manualmente y no repetir limpiezas destructivas fuera del reconciliador.
- La caché TAR regenerable vive fuera de `/share`, bajo
  `/media/rainmapper/runtime-cache/predictor-runtime-archives`, por lo que no
  engorda los backups de HA. El laboratorio usa el equivalente bajo
  `docker-media/rainmapper`.
- Los resultados operativos terminales pesados tienen TTL de 24 horas y la
  limpieza se ejecuta en arranque y checkpoints del ciclo de vida. No depende
  únicamente de apagar y encender la app.
- Aún conviene documentar una lectura final de Diagnostics con tamaños después
  del ciclo real y comprobar el comportamiento de la caché TAR tras reinicio;
  esto no bloquea el trabajo de rendimiento local.

## Hallazgo principal: el entrenamiento remoto tarda demasiado

El objetivo acordado es reducir `Reconstruir y reentrenar operativo` a un máximo
de 10 minutos extremo a extremo en el M1 Pro dentro de Docker, sin relajar
hashes, trazabilidad, cancelación, rollback ni promoción atómica.

Evidencia real del 2026-08-25:

- reconstrucción candidata: ~3 min 30 s;
- ML v0: ~1 min 18 s;
- multiversión: ~30 min 56 s;
- hasta completar multiversión: 35 min 55 s; la promoción enlazada terminó
  aproximadamente 1 min 15 s después;
- el usuario observó que los fits reales consumían solo unos 2–3 minutos.

Cuellos de botella confirmados:

1. El batch produjo 642 POST secuenciales para 173,4 MiB. Los 636 artefactos
   pequeños tardaron ~12 min 43 s; el upload completo, ~14 min 51 s. Cada
   fichero abre `urlopen`, se relee, valida y fuerza un `fsync`; el handler usa
   HTTP/1.0 por defecto.
2. `mushroom_worker_jobs.json` medía 5,39 MB. Unos 4,12 MB de su forma compacta
   eran 43 copias de manifiestos de runtime. Cada señal de control/progreso
   carga y reescribe la cola completa con `fsync` y `replace`; el polling ocurre
   cada dos segundos.
3. `Validating live inputs (n/64)` publica 64 actualizaciones —52 entradas del
   snapshot y 12 ficheros GIS—, reescribiendo la cola en cada callback. También
   se rehashea meteorología con `verify_weather_file_hashes=True`.
4. Los mismos bytes se verifican varias veces al recibir, finalizar e instalar,
   y después se copian. El worker también vuelve a recorrer modelos para
   manifiesto y caché.
5. Los ~15 min 56 s previos al primer upload mezclan descarga, preparación y
   fits; faltan tiempos persistentes por fase. El preparador ejecuta ocho etapas
   en serie y los monitores releen el JSONL de progreso completo cada 0,5 s.
6. Candidate, ML v0, bundles, benchmark y telemetría usan variantes del mismo
   patrón de microllamadas. Deben auditarse de forma transversal.

El detalle y el orden de implementación están en el bloque P2 de
`docs/todo.md`. En laboratorio ya están implementadas la telemetría persistente,
el catálogo de tuning congelado y la primera parte del workspace meteorológico
compartido. La preparación operativa completa del mismo snapshot bajó de
459,101 s a aproximadamente 185,4 s, con igualdad semántica exacta de los ocho
artefactos consumidos e igualdad byte por byte de los hold-out V2--V6. No se ha
repetido todavía el ciclo completo optimizado en HA real; la instalación de HA
`0.2.268` y worker `1.0.19` sí quedó completada y enlazada por heartbeat.

El smoke local extremo a extremo terminó formalmente en 534,571 s en frío y
473,654 s en caliente, con 714/714 fits y cero fallos. La revisión posterior
demostró que la promoción aceptó cuatro perfiles sin probabilidades hold-out;
por tanto, esos dos tiempos describen el rendimiento del flujo, pero no una
ejecución semánticamente completa. La preparación compartida consumió
260,947/236,058 s y los fits operativos 149,765/122,149 s. La telemetría se conserva bajo
`mushroom-data/diagnostics/operational-performance/`. Para validar se sincronizó
el código de forma reversible dentro del contenedor HA local existente, sin
crear ni tocar un worker.

El informe completo de cambios, mediciones, equivalencia, pruebas y riesgos es
`docs/reports/operational-rebuild-10m-lab-2026-08-26.md`.

Durante la misma sesión se corrigió localmente el Predictor, sin build ni
instalación. El resultado máximo pasa de 8 a 64 MiB, el worker lo comprueba
antes de enviar y el `finish` Predictor dispone de 60 s. La navegación ya no
calcula al cambiar desplegables, actualiza las zonas de la especie en memoria,
unifica la selección que calculan worker y UI y reutiliza el resultado semanal
terminado al cambiar de día. Una consulta local Edulis/V6 para todas las zonas
con franja semanal terminó dos veces en 7,623/7,684 s, HTTP 200 y sin errores
visibles. Falta la validación visual completa y un payload grande remoto antes
de proponer entrega.

El 2026-08-27 se corrigió además la regresión estructural del hold-out
operativo. Los benchmarks materializados podían llevar el contrato temporal
solo en `sample_id`; el evaluador no lo resolvía al contrato operativo del
catálogo de tuning y absorbía el fallo por estimador. V2 común, V3 core y los
dos perfiles V4 quedaban con `n_test = 0`, aunque el batch promocionaba. Ahora
el evaluador resuelve el contrato mediante el catálogo congelado y el job
rechaza antes de entrenar cualquier catálogo que deje un perfil seleccionado
sin probabilidades. El recomendador tampoco presenta la primera abstención
como «mejor señal».

La operación local completa `6BAUyBn6P2Exoq2e` terminó en 591,561 s, con
714/714 ajustes, cero fallos, 27.296 filas hold-out y las cinco generaciones
promovidas. La evaluación restaurada consumió 162,672 s para V2--V5 y 26,031 s
para V6. Cumple el máximo de 600 s con 8,439 s de margen; falta una repetición
caliente para medir variabilidad, no para demostrar la corrección funcional.
El informe reproducible es
`docs/reports/operational-holdout-contract-fix-2026-08-27.md`.

## Próximos pasos, en orden

1. Ejecutar una predicción funcional corta desde HA real y comprobar las cinco
   versiones, la presentación del resultado y la ausencia del aviso de identidad
   desconocida; no requiere reconstruir modelos.
2. Cuando se decida medir estabilidad, repetir una única ejecución caliente para
   cuantificar la variabilidad alrededor del límite local de 600 s.
3. Medir una reconstrucción remota fría/caliente
   para separar el cálculo ya reducido del transporte HA↔worker.
4. Solo si la medición remota lo justifica, compactar la cola: deduplicar
   manifiestos inmutables, separar lease/progreso
   volátil del historial durable, espaciar checkpoints y sacar housekeeping del
   tick de telemetría.
5. Agrupar los uploads en un contenedor efímero determinista y reanudable con
   chunks de 8–16 MiB, extracción segura y borrado posterior. Mantener el
   manifiesto lógico y todos los límites de confianza.
6. Sellar staging con un recibo verificable para reutilizar una única
   verificación completa durante instalación; eliminar rehashes y copias que no
   crucen una frontera nueva.
7. Introducir paralelismo acotado o C/Cython/Numba/Rust únicamente si un perfil
   futuro demuestra un núcleo Python puro dominante; el objetivo local ya se
   cumple sin ello.
8. Validar igualdad contractual y numérica, cache fría/caliente, cancelación,
   retry, rollback, ausencia de residuos y capacidad de respuesta de HA y del
   Predictor. Detenerse y presentar resultados antes de otra instalación o
   release.

## Riesgos y dudas activos

1. **Camino remoto aún sin repetir:** el tramo local ya tiene marcas
   persistentes, pero falta medir con el código nuevo cuánto añaden descarga,
   cola y upload en HA↔worker.
2. **Cambiar transporte o persistencia es transversal:** un paquete agrupado o
   una cola compacta no pueden debilitar límites de tamaño/recuento, protección
   contra traversal/enlaces, hashes, cancelación, retry o rollback.
3. **Aplicabilidad no calibrada:** `outside_feature_ratio >= 0,05` y una salida
   a `>= 3 sigma` son heurísticas, no límites aprendidos. Su auditoría sigue
   pendiente, separada de la optimización de transporte.
4. **Validación funcional real pendiente:** HA `0.2.268` y worker `1.0.19` están
   arrancados y coordinados, pero no se ha registrado todavía una predicción
   final ni una captura de las cinco versiones y de la desaparición del aviso
   de identidad desconocida.
5. **Retención real activa:** funcionó con 74 eliminaciones y cero errores; no
   debe deshabilitarse, forzarse ni complementarse con borrados manuales sin una
   decisión nueva del usuario.
6. **Margen local estrecho:** el ciclo corregido cumple los 600 s por 8,439 s;
   una repetición caliente debe cuantificar variabilidad antes de considerar el
   rendimiento estable.

## Archivos relevantes

- Orquestación/jobs: `rainmapper-app/app/web_server.py`,
  `rainmapper_core/mushroom_worker_jobs.py`,
  `rainmapper_core/mushroom_worker_transport.py`.
- Entrenamiento/transporte: `scripts/run-mushroom-ml-multiversion-job.py`,
  `rainmapper_core/mushroom_ml_multiversion_transport.py`,
  `rainmapper_core/mushroom_ml_multiversion_training.py`.
- Verificación/promoción: `rainmapper_core/mushroom_worker_results.py`,
  `rainmapper_core/mushroom_ml_version_registry.py`,
  `rainmapper_core/mushroom_local_full_update.py`.
- Predictor/UI: `rainmapper_core/mushroom_ml_multiversion_comparison.py`,
  `rainmapper_core/mushroom_predictor_service.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py`.
- Retención: `rainmapper_core/mushroom_storage_reconciler.py`,
  `rainmapper_core/mushroom_ml_storage_reconciler.py`,
  `docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo para las prioridades completas.
- Cumplir `AGENTS.md`: usar Codebase Memory MCP antes de descubrir o cambiar
  código y reindexar solo si el grafo contiene símbolos retirados.
- Comprobar `pwd`, rama y `git status`; preservar todos los cambios locales y
  ficheros no rastreados.
- Trabajar primero en el laboratorio local. No usar Tailscale, no tocar HA real
  ni el worker normal, no cambiar la opción de retención y no borrar datos.
- No hacer bump, build, publicación, instalación ni release sin autorización
  explícita nueva. Ejecutar validación proporcional y terminar con
  `git diff --check`.
