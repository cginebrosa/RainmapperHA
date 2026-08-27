# Predictor remoto: navegación y caché — 2026-08-27

## Alcance

Diagnóstico y corrección local de tres incidencias observadas tras instalar HA
`0.2.268` y worker `1.0.19`:

1. al abrir una recomendación, la consulta remota terminaba pero HA mostraba
   `No disponible`;
2. volver al Recommender después de visitar Edulis recalculaba las ocho especies
   y tardaba unos 44 segundos aunque el runtime ya estaba caliente;
3. HA y el worker usaban motores de ejecución distintos: el worker llamaba a
   `PredictorService`, mientras HA calculaba directamente desde la UI y no podía
   aprovechar la misma normalización ni la caché de respuestas.

No se modificó el share real. La cola
`/Volumes/share/rainmapper/mushroom-data/mushroom_worker_jobs.json` se consultó
exclusivamente con `jq` en modo de lectura y limitando la salida a los cuatro
trabajos afectados.

## Evidencia real

| Trabajo | Vista | Cálculo observado | Runtime | Resultado |
| --- | --- | ---: | --- | ---: |
| `worker_job_qY5iodslKa_M` | Recommender | 112 s entre inicio y fin | frío, sincronizado | 1.928.531 bytes |
| `worker_job_PFsDQ3xB5W9T` | Edulis/La Masella | 18 s | reutilizado | 590.273 bytes |
| `worker_job_99uNueWdRJw1` | Recommender | 44 s | reutilizado | 1.928.540 bytes |
| `worker_job_etOvQodVXAzl` | Edulis/La Masella | 12 s | reutilizado | 589.598 bytes |

Los cuatro trabajos terminaron como `complete`. Ningún resultado se acercó al
límite vigente de 64 MiB; tampoco alcanzaron el límite antiguo de 8 MiB.

### Consulta que terminaba vacía

La solicitud remota contenía simultáneamente:

- `compare_models: false`;
- 24 selecciones multiversión de Biology V4.

La UI interpreta la ausencia de `compare` como comparación activada, mientras
que `create_remote_predictor_job` solo la activaba si recibía literalmente
`compare=1`. El worker, por tanto, no preparaba los bloques multiversión que la
UI esperaba al renderizar la respuesta terminal. En ejecución local esos
bloques se calculaban bajo demanda y el defecto quedaba oculto.

La corrección hace que el contrato remoto use la misma semántica que la UI:
comparación activada salvo `compare=0` explícito.

### Recommender caliente que recalculaba

El primer Recommender llevaba `species_id=amanita_caesarea`; después de navegar
a Edulis, el segundo llevaba `species_id=boletus_edulis`. La vista Recommender
ignora esa selección y evalúa siempre todas las especies entrenadas, pero la
clave LRU incluía `species_id`. Dos solicitudes semánticamente idénticas se
consideraban distintas y la segunda repetía todo el cálculo.

La corrección usa una identidad canónica de «todas las especies entrenadas» en
la clave del Recommender. En un hit, la respuesta sigue reflejando la solicitud
actual para no falsear su auditoría. La caché continúa acotada a 32 entradas y
sigue separada por vista, fecha, filtros, issue date, conjunto entrenado y
selecciones relevantes.

### Un único motor en HA y worker

`build_predictor_request` es ahora la única traducción del formulario al
contrato Predictor. La usan tanto la creación del job remoto como el ejecutor
interno de HA. En ambos casos el cálculo termina en
`PredictorService.execute`; la UI se limita a renderizar su respuesta
verificada.

HA conserva una instancia del servicio asociada al fingerprint del runtime. La
primera petición construye y verifica ese runtime; las siguientes reutilizan
modelos, objetos meteorológicos y la LRU de respuestas. Los puntos existentes
que liberan la caché antes de update, rebuild o reentreno liberan también esta
instancia, de modo que un cambio operativo no puede conservar modelos antiguos.
No se añadió ningún proceso ni worker nuevo.

Las funciones directas antiguas permanecen por ahora dentro del módulo UI como
soporte de render y pruebas unitarias, pero la ruta productiva interna de HA ya
no las usa para calcular. Su retirada completa debe tratarse como una limpieza
posterior y separada, con análisis de llamadas y equivalencia, no mezclarse con
esta corrección funcional.

### Ranking base redundante del Recommender

La revisión del camino frío confirmó que el Recommender no calcula todas las
versiones instaladas: para cada área resuelve únicamente todos los perfiles de
la versión preferida. Sí hacía antes un trabajo redundante: `rank_areas()`
ejecutaba el modelo base para todas las áreas observadas y las ordenaba; después
el Recommender descartaba esas probabilidades y volvía a evaluar exactamente
las mismas áreas con la versión preferida.

`rank_areas(only_observed=True)` no añadía ningún filtro: tomaba literalmente
`areas_with_species_observations()`, ejecutaba `predict_many()` y ordenaba el
resultado. Ahora el servicio conserva la lista explícita de áreas observadas y
calcula directamente la comparación preferida para cada una. Las áreas sin
observaciones elegibles continúan excluidas igual que antes; ampliar a áreas no
observadas sería una decisión distinta de extrapolación, no una optimización.

## Validación local

- Seis pruebas dirigidas iniciales: `OK`.
- Suites completas `tests.test_mushroom_predictor_service` y
  `tests.test_web_server_auth`: 274 pruebas, cero fallos.
- Suite transversal final `python -m unittest discover -s tests`: 1.042 pruebas,
  cero fallos, 51,422 s.
- `git diff --check`: correcto.
- La prueba nueva demuestra `miss` para el primer Recommender y `hit` para el
  segundo cuando solo cambia la especie residual; el cálculo por especie no se
  repite.
- La prueba contractual demuestra comparación activada por defecto y conserva
  `compare=0` como desactivación explícita.
- Antes de unificar el motor, dos Recommender internos con especie residual
  Amanita y Edulis tardaron 30,831 s y 29,068 s: HA recalculaba ambos.
- Tras sincronizar reversiblemente los tres módulos en el mismo contenedor HA
  local, la secuencia medida fue:

| Consulta local | HTTP | Tiempo | Respuesta |
| --- | ---: | ---: | ---: |
| Recommender frío, residual Amanita | 200 | 35,115 s | 351.297 bytes |
| Recommender caliente, residual Edulis | 200 | 0,209 s | 351.265 bytes |
| Recommender caliente repetido | 200 | 0,208 s | 351.265 bytes |
| Detalle Edulis/Vallter desde una fila | 200 | 7,832 s | 384.538 bytes |
| Vuelta al Recommender tras el detalle | 200 | 0,218 s | 351.265 bytes |
| Recommender frío sin ranking base | 200 | 31,647 s | 351.275 bytes |
| Recommender caliente sin ranking base | 200 | 0,201 s | 351.265 bytes |

El Recommender caliente fue unas 168 veces más rápido que el frío y unas 139
veces más rápido que el segundo cálculo interno anterior. El HTML caliente no
estaba vacío: mostró Edulis/Vallter como mejor apuesta al 70 % y una lista de
áreas. El detalle mostró Edulis y Vallter y no contenía `No disponible`.

Eliminar el ranking base redujo el frío de 35,115 a 31,647 s: 3,467 s y
aproximadamente un 9,9 %. Un diff dirigido de mejor apuesta y todas las filas
—especie, área, porcentaje y modelo— fue vacío frente a la ejecución anterior.
La prueba unitaria exige además que todas las áreas observadas reciban su
comparación preferida y que `rank_areas()` no se invoque. La mejora es válida,
pero muestra que el coste dominante restante está en las comparaciones de la
versión preferida por especie/área.

Esta última frase identifica el camino multiplicativo restante, no una
atribución cronometrada completa de los 31,647 s. `compare_selection` ya mide
manifiesto, catálogo, resolución, contexto meteorológico y comparación
preparada, pero el benchmark HTTP todavía no ha agregado esas métricas para
todas las áreas. La propuesta vinculada para hacerlo y decidir después entre
caché semántica, workspace meteorológico común e inferencia por lotes está en
`docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`.

La sincronización dejó copias previas en `/tmp` dentro del contenedor local y
reinició solo `rainmapper-local-rainmapper-ha-ui-1`. No se creó ningún worker
local adicional, no se usó el worker normal y no se modificó `/share`.

## Riesgos y siguiente validación

- La corrección contractual y el ejecutor interno cambian HA; la clave de caché
  compartida cambia el worker. Una entrega requiere versiones coordinadas
  nuevas de ambos artefactos.
- No se ha medido todavía el tiempo remoto después del cambio. El hit elimina el
  recálculo de unos 44 segundos observado, pero permanecen cola, polling,
  renderizado y transferencia del resultado de aproximadamente 1,93 MiB.
- El coste frío inicial de HA era 35 s y el detalle nuevo 7,8 s. La mejora
  demostrada de caché elimina recálculos idénticos. Retirar el ranking base lo
  reduce a 31,6 s, pero no elimina el cálculo preferido ni autoriza a omitir la
  verificación del runtime.
- Tras una eventual instalación basta una secuencia corta: Recommender, clic en
  una fila y vuelta al mismo Recommender. Debe aparecer la consulta completa y
  la vuelta debe registrar `response_cache_status=hit`.
