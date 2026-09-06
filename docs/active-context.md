# Active Context

Ventana operativa de RainmapperHA al cierre del 7 de septiembre de 2026. No es
un histórico. Revalidar siempre `pwd`, rama, HEAD, worktree, fuentes y runtimes
antes de asumir que este estado continúa vigente.

## Estado comprobado

- Repositorio: `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
  HEAD comprobado al cerrar esta auditoría:
  `666ff08b299f75285a01c611fae1a89c216a75db`.
- El fichero `mushroom-data/mushroom_observations.json` queda modificado fuera
  del commit de release porque pertenece al usuario. No limpiarlo, editarlo,
  restaurarlo ni incluirlo ciegamente en otro commit.
- Fuente de datos local viva para entrenamiento y pruebas:
  `docker-data/mushroom-data/`. `mushroom-data/` contiene defaults para una
  instalación nueva; no sustituye los datos vivos descargados de HA.
- Versiones declaradas en fuente: HA `0.2.295` en
  `rainmapper-app/config.yaml` y worker `1.0.41` en
  `rainmapper-worker/Dockerfile`.
- HA `0.2.295` está publicada en GHCR. Los tags `0.2.295` y `latest` comparten
  el digest `sha256:11a9796443555a9ba8d0fb66ae01c6ecf7a1cd5df813013e2b354cd9cc40d217`
  y contienen manifests `linux/amd64` y `linux/arm64`.
- El contenedor local `rainmapper-local-rainmapper-ha-ui-1` se comprobó activo
  con la imagen `rainmapperha:local-ha-ui`.
  Dentro del contenedor, `EXPERIMENT_ESTIMATOR_IDS` contiene
  `knn_distance_beta_smoothed_v2` y no el KNN antiguo.
- El worker local se comprobó activo y healthy con la imagen de prueba
  `rainmapper-worker:multicoordinator-test`. Conserva el volumen, la identidad
  `worker_1a9a232c20fe2ee2`, el emparejamiento, la caché GIS de 6.341.520.039
  bytes y la URL autorizada `http://100.111.77.48:8100`.

## Corrección de recursos publicada y en prueba real

- El fallo real del precálculo fue `Worker precompute selections are too
  large`: HA había expandido 504 resoluciones a 49.913.415 bytes antes de que
  el worker pudiera sincronizar el runtime.
- El contrato nuevo encola solo el mapa de 72 áreas, medido en 1.117 bytes. El
  worker 1.0.41 sincroniza primero su runtime y resuelve allí los 420 ganadores,
  cadenas y vetos de aplicabilidad. El límite de 16 MiB no se eleva.
- Los nuevos lotes operativos guardan catálogo, auditoría, informe y hold-out
  comprimidos. El catálogo real medido baja de 66.897.313 a 2.264.625 bytes y
  la auditoría de 18.743.962 a 965.421 bytes.
- HA planifica con un índice de ganador/abstención de 4.329 bytes; no abre el
  catálogo completo. Auditoría, informe y hold-out no entran en el runtime ni
  en la caché del worker.
- El worker y HA mueven el lote verificado dentro del mismo sistema de ficheros
  en vez de duplicarlo. La instalación normal no conserva otro árbol completo
  del lote operativo.
- La generación real ya instalada es compatible: HA 0.2.294 y worker 1.0.41
  pueden repetir el precálculo sin reentrenar. La compresión y el índice pequeño
  se aplicarán a partir del siguiente entrenamiento.
- Evidencia completa:
  `docs/reports/mushroom-precompute-resource-regression-2026-09-06.md`.

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

## Estado operativo real comprobado después de la release

- El registro real instala V2, V3, V4, V5w y V6w desde el lote
  `operational_20260906T001649Z`. Las cinco generaciones instaladas declaran el
  snapshot `sha256:a6d501ab43ff9aea8fa6539c96125bad3b0a1de4b13aae85ecf17f4d8cd2b30b`
  y observaciones `sha256:24464e4c6414e5dd2cda5752495b7668d13f1e1bffe66df646da6f668e656899`.
- El trabajo multiversión `worker_job_9Ly2myJUDAFsD5bL` terminó a las
  `2026-09-06T03:21:17Z`: 636 ajustes planificados, 636 correctos y cero fallos,
  lote calculado `operational_20260906T030610Z`. El registro real consultado
  sigue señalando como instalada la generación `...T001649Z`; no confundir un
  trabajo terminado con una activación que el registro no refleja.
- El precálculo `worker_job_bNaaBwELXbGW` terminó a las
  `2026-09-06T09:15:24Z`, revisión 59, cobertura 2026-09-06--2026-09-12 y
  30.007.296 bytes. Recibo
  `sha256:8394ede7128ea237a8bc951d05be75ce92fca6579ed66de590012ba1249ec830`.
- Después de esos trabajos se corrigieron las observaciones. La fuente viva
  local y la de HA real son idénticas, contienen 447 observaciones y tienen
  SHA-256 `13081f3d8ff8ed4f629ce69a7eb625b270222f0a2011047313dbc8b256e03c38`.
  Por tanto, la generación instalada y el precálculo terminado son anteriores
  al snapshot corregido; no presentarlos como recalculados con esas correcciones.
- La meteorología vigente es
  `20260906T090356917682Z-e918eb2b7bc4`, manifiesto
  `b6309a877e5d3df1aa616e6dcf4d2c3b322ca49363679172eede484e2a7e49ad`.
- El estado activo local del precálculo reside en
  `docker-media/rainmapper/predictor_precompute/`; la antigua carpeta bajo
  `docker-data/mushroom-data/` ya no existe.

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

## Auditoría de resolución por microárea cerrada

- El snapshot corregido deja 377 observaciones elegibles para las ocho especies
  operativas. No hay objetivos opuestos dentro de una misma especie,
  microárea y día. Sí hay ocho episodios legítimos con resultados distintos
  entre microáreas de una misma área y día.
- Se compararon los 11 perfiles operativos y todos sus estimadores sobre 27.312
  filas fuera de muestra idénticas. La microárea mejora Brier solo un `0,225 %`
  relativo: 55 comparaciones mejoran y 44 empeoran.
- En los episodios mixtos, la microárea positiva queda por encima de la negativa
  solo en el `52,8 %` de las evaluaciones. El candidato no separa todavía la
  señal espacial de forma fiable. `knn_distance_beta_smoothed_v2` empeora
  `1,607 %` en esta variante.
- Para resumir el área, media y mediana empeoran. El máximo mejora apenas
  `0,098 %` global y está favorecido por el objetivo actual «cualquier
  microárea favorable»; no justifica un cambio de producción.
- No bajar entrenamiento ni precálculo a microárea con los datos actuales. Una
  revisión futura debe conservar las etiquetas microespaciales, compartir la
  caché meteorológica, procesar en flujo y guardar únicamente resultados
  finales compactos.
- El laboratorio temporal alcanzó `6,96 GiB` de RSS y 1,8 GiB de disco con los
  JSON expandidos actuales. Es una prueba científica, no un diseño compatible
  con la Raspberry Pi 4. Los temporales se eliminaron; quedan 657.218 bytes de
  resúmenes compactos.
- Evidencia completa:
  `docs/reports/mushroom-microarea-resolution-audit-2026-09-06.md`.

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

## Worker multicoordinador y reproducción del precálculo

- El diseño completo está consolidado en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`. Es distinto
  del runtime científico multiversión V2--V6, documentado en
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.
- La imagen de prueba `rainmapper-worker:multicoordinator-test` atiende al HA
  real y al HA local con el mismo `worker_id`, credenciales separadas y un
  carril global `foreground` más otro `background`.
- El entrenamiento solicitado desde HA local completó el mismo circuito de
  tres jobs que HA real. Después, el precálculo local
  `worker_job_MR1tD64I514P` reprodujo el fallo real: ocho especies, 72 pares
  especie/área, siete días, cinco versiones y cero miembros materializados
  frente a 420 esperados.
- La causa comprobada del fallo al `64 %` era un lector incompleto del catálogo
  de calidad: verificaba el hash del `quality-catalog.json.gz`, pero entregaba
  los bytes todavía comprimidos a `json.loads()`. El lector ya descomprime
  después de verificar el hash y comparte una caché por referencia durante
  toda la comparación. El contrato de 420 miembros no se ha rebajado.
- Las pruebas dirigidas del lector, el servicio y el precálculo suman 114 casos
  correctos. El worker de prueba completó después el precálculo real de 420
  miembros y publicó un SQLite de 30.048.256 bytes; así quedó comprobado el
  mismo circuito que antes fallaba.
- El runtime multicoordinador funciona, pero el CLI público de
  `mushroom_worker_start.sh` no permite aún listar, seleccionar, reemparejar,
  cambiar URL, limpiar token u olvidar cualquier coordinador de forma explícita
  por `coordinator_id`. Esa administración debe completarse antes del
  versionado del worker.

## Vigencia y latencia del precálculo

- La vigencia no depende solo de la fecha. Se conservan la coincidencia exacta
  de la huella del runtime, la revisión y el identificador del artefacto, el
  recibo, el tamaño y las validaciones del SQLite. La condición de fecha deja
  de exigir que `coverage_start` sea hoy: el artefacto es vigente mientras hoy
  esté dentro del intervalo inclusivo `coverage_start..coverage_end`.
- Hay una prueba directa del intervalo y una prueba integrada en los dos
  resúmenes de HA que conserva activo un precálculo iniciado el día anterior.
  Un intervalo vencido o una huella distinta sigue marcado como desactualizado.
- La lentitud interactiva estaba en HA, no en el worker ni principalmente en el
  navegador. Los diagnósticos reales anteriores registraban aciertos del
  precálculo con 282 a 527 lecturas SQLite: unos 8 segundos sin contención y
  hasta 54 segundos cuando coincidían varias peticiones.
- La publicación valida exhaustivamente el SQLite una sola vez antes de hacerlo
  activo. La lectura interactiva confía después en ese artefacto inmutable: no
  vuelve a recorrer celdas, predicciones base ni miembros, no repite la
  validación profunda del JSON y usa el catálogo de modelos incluido en la
  propia respuesta sellada.
- `Esta semana` y `Por especie` leen una única respuesta precomputada. En HA
  local, la búsqueda del recomendador bajó de unos `0,98 s` y 333 filas a
  `0,036 s` y una fila; la petición completa quedó en unos `0,15 s`.
- `Consultar fecha` conservaba otra recomposición redundante cuando la selección
  expandida de la UI no coincidía con la clave sellada. Llegaba a 16 filas y
  `0,91--0,97 s`. Ahora localiza directamente la respuesta sellada por
  especie--área--fecha: una fila, `0,045 s` de búsqueda y `0,167 s` para la
  petición completa en la prueba local real.
- Las rutas directas de la UI muestran el modal y bloquean nuevos clics mientras
  hay una navegación en curso. Las 392 pruebas dirigidas de precálculo y
  servidor pasan. El smoke completo de release supera 1.316 pruebas, además de
  fixtures, sintaxis shell y `git diff --check`. No se ha modificado la ciencia
  ni `MOD_0001`.

## Release HA 0.2.295

- Publicada el 7 de septiembre de 2026 como `0.2.295` y `latest`, ambos con el
  digest multiarquitectura
  `sha256:11a9796443555a9ba8d0fb66ae01c6ecf7a1cd5df813013e2b354cd9cc40d217`.
- Incluye la vigencia correcta del precálculo al cruzar medianoche, las lecturas
  directas de una sola fila sellada para recomendador, especie y consulta por
  fecha, y evita validaciones y recomposiciones redundantes durante la consulta.
- Oculta el detalle vacío de versiones en las vistas agregadas, lo conserva en
  `Consultar fecha` cuando contiene datos, muestra el modal en navegaciones
  directas y bloquea clics repetidos mientras la petición está en curso.
- La validación local previa a publicar fue funcional, no solo de compilación:
  1.316 pruebas completas correctas y mediciones HTTP reales con una sola fila
  SQLite y tiempos de petición de décimas de segundo.
- La imagen del worker no forma parte de esta release y sus asociaciones con
  coordinadores no se han modificado.

## Próxima secuencia

1. No implementar ni desplegar la resolución por microárea a partir de la
   auditoría actual.
2. Instalar HA `0.2.295` en HA real y comprobar que recomendador, especie y
   consulta por fecha reutilizan el precálculo con latencia interactiva baja.
3. Confirmar en los diagnósticos reales una sola fila SQLite por respuesta
   sellada y ausencia de recomposición o validación profunda durante la lectura.
4. Completar la administración multicoordinador del CLI con destino explícito
   por `coordinator_id` y pruebas de no modificación de las demás asociaciones.
5. Construir HA local y worker desde el mismo source y superar un circuito
   completo local después de cualquier cambio ejecutable.

## Riesgos y dudas activas

- HA real continúa en `0.2.294` hasta que el usuario instale `0.2.295`; la
  publicación en GHCR no demuestra todavía el rendimiento en la Raspberry Pi.
- El trabajo multiversión más reciente figura completo, mientras que el registro
  sigue apuntando al lote anterior. Antes de otro ciclo hay que tratar el
  registro como fuente de verdad y comprobar la activación, no inferirla del
  porcentaje del trabajo.
- La resolución por microárea no supera el umbral científico ni el de recursos;
  queda cerrada, no pendiente de implementación.
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
- Auditoría de resolución espacial:
  `docs/reports/mushroom-microarea-resolution-audit-2026-09-06.md`.
- Datos vivos: `docker-data/mushroom-data/`.
- Modelos y precálculo actuales:
  `docker-media/rainmapper/mushroom-derived/ml_models/` y
  `docker-media/rainmapper/predictor_precompute/`.
