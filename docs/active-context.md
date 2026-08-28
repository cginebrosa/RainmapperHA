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

## Corrección Predictor pendiente de entrega — 2026-08-27

Tras instalar HA `0.2.268` y worker `1.0.19`, una consulta abierta desde una
fila del Recommender terminaba en el worker pero HA mostraba `No disponible`.
La causa confirmada era una divergencia del contrato `compare`: la UI lo activa
por defecto y el job remoto lo desactivaba salvo `compare=1`. Localmente se ha
unificado la semántica y se conserva `compare=0` como desactivación explícita.

Un Recommender caliente posterior tardó 44 s porque la clave LRU incluía la
especie residual de navegación aunque la vista calcula las ocho especies. La
clave ahora canoniza ese campo y reutiliza el resultado global. La evidencia,
los tamaños reales y la validación inicial de 273 pruebas están en
`docs/reports/predictor-remote-navigation-cache-2026-08-27.md`. Estos cambios
afectan a HA y worker y aún no se han versionado, construido ni instalado.

La revisión posterior confirmó otra divergencia: el worker ejecutaba
`PredictorService`, pero HA calculaba directamente desde el módulo UI. La ruta
interna local ya construye el mismo contrato y usa una instancia persistente
del mismo servicio; update/rebuild/reentreno la liberan mediante el mecanismo
de caché existente. En el contenedor HA local, Recommender frío/caliente midió
35,115/0,209 s, una repetición 0,208 s, el detalle Edulis/Vallter 7,832 s y la
vuelta al Recommender 0,218 s, todos con HTTP 200 y contenido real. Las suites
dirigidas suman ahora 274 pruebas sin fallos y la suite transversal final pasó
1.042 pruebas en 51,422 s. `git diff --check` también pasó. No hay bump, build ni
publicación autorizados.

Una revisión adicional confirmó que el Recommender no ejecuta todas las
versiones: usa solo la preferida, pero antes calculaba primero un ranking con el
modelo base sobre exactamente las mismas áreas observadas. Ese ranking se
retiró sin ampliar a áreas sin observaciones. El frío local bajó de 35,115 a
31,647 s (−3,467 s; ~9,9 %), el hit caliente midió 0,201 s y el diff de mejor
apuesta y filas finales fue vacío. El coste frío dominante restante son las
comparaciones preferidas por especie/área.

La optimización siguiente queda especificada en
`docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`. Antes de
otra refactorización se agregarán los tiempos ya emitidos por
`compare_selection` para atribuir los 31,647 s restantes entre meteorología,
artefactos, variables, inferencia y selección. Después se priorizará una caché
semántica persistente y acotada que permita reutilizar en el detalle cada
comparación hecha por el Recommender; workspace meteorológico común e
inferencia por lotes quedan condicionados a la evidencia. Los objetivos son
Recommender frío <=10 s y detalle reutilizado <=1 s sin alterar áreas,
probabilidades, modelos, abstenciones ni gates científicos.

## Autocura SoilGrids en implementación local — 2026-08-27

La revisión de la nueva área Espinavell en el `known_sites` real encontró 63
microáreas: 59 SoilGrids completas y cuatro pendientes, entre ellas Ritort. La
causa estructural era que `resolve_geometry_context` agregaba antes de
inicializar la caché; si faltaba `manifest.json`, capturaba la excepción y no
llegaba a crear ni descargar teselas.

Localmente se ha corregido ese orden y se ha añadido una reconciliación global
best-effort antes del snapshot operativo. El job nace en estado persistente
`preparing`, muestra la fase localizada «Reconciliando GIS y SoilGrids», no es
reclamable todavía y admite cancelación segura. Solo se recalculan contextos no
vigentes; los fallos se registran por microárea y no detienen el reentreno. La
promoción de `known_sites` usa el escritor atómico existente y se cancela si el
fichero cambió concurrentemente.

Una prueba sin escritura leyó el fichero montado de HA real y usó la caché
local: 59 contextos se reutilizaron por identidad, 4/4 se repararon, no hubo
peticiones ni descargas y los 63 terminaron completos en 52,259 s. Predictor y
Setales muestran aviso global y marca por microárea si todavía queda algún
contexto pendiente. La validación final pasa la suite completa de 1.056 pruebas,
compilación de los módulos modificados, validación JSON de etiquetas y
`git diff --check`. La validación operativa completa con la copia fresca se
describe en la sección siguiente.

El diseño, contadores, degradación y riesgos están en
`docs/mushrooms/mushroom-soilgrids-autocure-spec-es.md`.

## Validación fresca y optimización adicional — 2026-08-28

Con la copia fresca de 439 observaciones (396 elegibles), el primer proceso
completo anterior a esta optimización terminó correctamente en 706,517 s
(11 min 46,5 s), con promoción atómica y cero fits fallidos. La reconstrucción
consumió 107,399 s; el hold-out V2--V5, 218,108 s; y los fits finales V2--V6,
aproximadamente 156 s. La telemetría contabilizó 1.365.432.305 bytes leídos,
2.473 hashes, 826 copias y 97 fsync. Los hashes y la promoción no explican el
coste dominante: juntos representan una fracción pequeña frente al cálculo de
hold-out y entrenamiento.

Se rechazaron dos atajos medidos: paralelizar cuatro datasets empeoró el
hold-out de 125,09 a 170,21 s por sobresuscripción, y limitar globalmente loky a
un núcleo alteró 62 probabilidades KNN (diferencia máxima 0,1427). En cambio,
limitar solo RandomForest y ExtraTrees a un hilo durante el fit redujo en el
contenedor el hold-out V2--V5 de 192,307 a 166,260 s (−26,047 s; −13,5 %) con
salida completa y SHA del hold-out idénticos. Los artefactos restauran
`n_jobs=-1` después del fit para conservar el contrato de inferencia.

El entrenamiento final prepara ahora una única matriz por combinación de
versión, contrato temporal, perfil y especie, y la reutiliza entre algoritmos.
El manifiesto persiste entradas, aciertos y bytes de esa caché para medir su
efecto y dimensionar memoria; no crea matrices cuyo ancho dependa del número de
observaciones. La reconciliación SoilGrids se ejecuta también en el camino
local antes del snapshot, como quinta fase visible y cancelable, con degradación
por microárea.

Pasan 35 pruebas dirigidas del núcleo, cuatro pruebas dirigidas web y la suite
completa de 1.056 pruebas en 47,266 s. `git diff --check` está limpio. Se
reconstruyó únicamente `rainmapperha:local-ha-ui` (digest local de la lista de
manifiestos `sha256:259f272b8e566b89a7673c5c09885bbcc6f6e661ae19238c61d369ecd503d8d3`)
y `/mushrooms/workers` responde 200 dentro del contenedor. No se tocó HA real ni
el worker normal.

El proceso completo lanzado por el usuario terminó en 548,095 s de telemetría
monotónica (9 min 8,1 s; la UI redondea el trabajo a 9 min 8 s), frente a
706,503 s con los mismos datos frescos: ahorro de 158,408 s (22,4 %) y objetivo
de 600 s cumplido con 51,905 s de margen. El hold-out V2--V5 bajó de 218,108 a
138,767 s y los fits finales de 156,013 a 101,073 s. La caché preparó 204
matrices, obtuvo 510 reutilizaciones y ocupó 72.139.352 bytes (68,8 MiB).

La autocura tardó 14,539 s: revisó las 63 microáreas, reparó las cuatro
pendientes y dejó 63/63 completas, sin peticiones, descargas ni avisos. El
resultado produjo 714/714 fits, cero fallos, 29.208 predicciones hold-out y
3.528 métricas. Las cinco versiones seleccionadas quedaron enlazadas en el
registro a `local_operational_20260827T225123Z`; la UI muestra «Complete
generation active». Instalación y promoción tardaron 3,270 s. La evidencia
persistente es `diagnostics/operational-performance/6uCH9V-0EoMEf0SC.json`,
`diagnostics/soilgrids-reconciliation-latest.json` y el manifiesto del batch.

## Release preparada — 2026-08-28

El smoke definitivo de release pasó 1.056 pruebas y todos los validadores. HA
`0.2.269` quedó publicada en GHCR con digest multi-arquitectura
`sha256:4c81d607949d7746f773de9e651e0ef5f7a65fad19de9a4cf368d9e2bbb8f8f3`;
los tags `0.2.269` y `latest` coinciden y contienen `linux/amd64` y
`linux/arm64`. El cliente Buildx quedó bloqueado después de completar la subida
y se canceló solo tras verificar remotamente ambos tags, digest y plataformas.

El worker privado `1.0.20` se construyó para arm64 con imagen local
`sha256:5ab52bb6d886b93fda98131cf3ba26b12974fcdd0f7e3caae5399dbc3eab52c7`.
El worker normal fue recreado conservando `rainmapper-worker-data`; responde
healthy, `idle`, con versión 1.0.20, caché GIS válida y caché Predictor válida.
No se lanzó ningún trabajo ni se modificaron datos de HA real. Queda que el
usuario instale HA 0.2.269 y ejecute las pruebas reales.

## Evidencia real y trabajo local posterior — 2026-08-28

En HA real 0.2.269 con worker 1.0.20, una recomendación cuyo resultado científico
ya estaba cacheado empleó unos 25 s aunque el backend informó 0,023 s. El runtime
tenía 713 ficheros y 253.657.749 bytes. El worker volvía a verificar su contenido
en cada sincronización aun cuando el fingerprint coincidía. La corrección añade
publicación persistente en HA y un recibo sellado en el worker: una reutilización
válida hace cero hashes y cero transferencias. La vía ordinaria calcula hashes al
publicar cambios; una mutación externa se detecta por ruta, tamaño y mtime y solo
rehasea los ficheros alterados para autocurar el manifiesto.

La primera reconstrucción real posterior produjo esta cadena: reconstrucción
7 min 21 s, ML v0 2 min 28 s y un tercer trabajo multiversión que falló tras
4 min 17 s. El fallo exacto fue `Operational preparation requires a tuning
catalog`: el bundle remoto operativo omitía el catálogo congelado que sí usa el
camino local. La corrección local lo sella en el snapshot y lo pasa explícitamente
al preparador; no relaja la validación científica.

La misma ejecución mostró materialización y verificación redundantes entre los
tres trabajos. El diseño de entrega local sellada, fallback canónico a HA,
telemetría y criterios de aceptación está en
`docs/mushrooms/mushroom-worker-chained-job-local-handoff-spec-es.md`.
La primera entrega local ya incorpora objetos inmutables por SHA-256 con recibo
atómico para entradas generales y meteorológicas, reutilización por enlace y
fases distintas para caché local y descarga. ML v0 declara hashes y tamaños para
que V2--V6 reutilice exactamente sus entradas. La caché tiene presupuesto blando
de 1 GiB y nunca poda objetos protegidos por la operación actual.

La validación local posterior pasa 1.066 pruebas en 44,479 s, compilación de los
módulos modificados y `git diff --check`. El smoke completo previo al bump pasó
1.066 pruebas en 48,378 s. HA 0.2.270 quedó publicada y verificada en GHCR: los
tags `0.2.270` y `latest` comparten el digest multi-arquitectura
`sha256:7692f3805bc90cd4172de1700993962a571cc80da5b3c09382b87760c3282cca`
y contienen `linux/amd64` y `linux/arm64`. El worker privado 1.0.21 se construyó
localmente para arm64 como
`sha256:da0c16bbb0b5f4b8e1a1cc7eca708cb7e4c267d0e6fcce733d8d61285e34d1a9`;
no se instaló ni se reinició el worker normal. Falta instalar ambas versiones y
medir en HA real Predictor frío/caliente y la cadena remota completa.

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
- Autocura SoilGrids: `rainmapper_core/mushroom_soilgrids.py`,
  `rainmapper_core/mushroom_soilgrids_reconciler.py`,
  `docs/mushrooms/mushroom-soilgrids-autocure-spec-es.md`.
- Retención: `rainmapper_core/mushroom_storage_reconciler.py`,
  `rainmapper_core/mushroom_ml_storage_reconciler.py`,
  `docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`.
- Entrega local entre trabajos encadenados:
  `docs/mushrooms/mushroom-worker-chained-job-local-handoff-spec-es.md`.

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
