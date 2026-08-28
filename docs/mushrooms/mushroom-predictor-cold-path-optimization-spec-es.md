# Optimización del camino frío del Predictor

Especificación acordada el 2026-08-27 para reducir el coste inicial del
Recommender y de la navegación hacia sus detalles sin cambiar la semántica
científica, la elegibilidad de áreas ni los gates de calidad.

## Evidencia de partida

En el laboratorio local, ejecutando HA y el worker mediante el mismo
`PredictorService`:

- Recommender frío antes de retirar el ranking base: 35,115 s;
- Recommender frío después: 31,647 s;
- ahorro demostrado: 3,467 s, aproximadamente 9,9 %;
- petición idéntica caliente: 0,201 s;
- detalle Edulis/Vallter después del Recommender: 7,832 s;
- vuelta al mismo Recommender: 0,218 s.

En HA real `0.2.269` con worker `1.0.20`, el 2026-08-28 se midió además el
envoltorio remoto sobre el runtime
`sha256:35e8e0452e8b48986b3857ee0da2fbd6a8fdf8e35469aa58ada248a3c22a3bce`:

- Recommender 2026-09-01, miss de respuesta: backend 25,897 s y total
  51,251 s;
- vuelta al Recommender 2026-08-29, hit de respuesta: backend 0,0227 s y
  total 25,003 s;
- ambos trabajos reutilizaron el runtime y transfirieron 0 bytes;
- el runtime contenía 713 entradas y 253.657.749 bytes: 659 entradas de
  modelos, 49 meteorológicas y 5 de datos auxiliares.

La segunda medida demuestra que aproximadamente 24,98 s no pertenecen al
cálculo científico. En el camino vigente HA reconstruye el manifiesto cuando
crea el job y otra vez cuando autoriza una descarga; el worker, aunque ya tenga
la misma huella, recorre las 713 entradas y recalcula SHA-256. Los hashes de
contenido están actuando como auditoría por lectura en vez de como identidad
persistente establecida al publicar.

El diff dirigido de mejor apuesta y de todas las filas finales fue vacío al
retirar el ranking base. Las cifras demuestran un coste frío importante y una
caché de respuesta completa eficaz. Todavía no atribuyen los 31,647 s
restantes a una fase concreta.

## Camino actual verificado

El Recommender recorre cada especie entrenada en temporada y todas sus áreas
con observaciones elegibles. Para cada pareja especie/área llama a
`compare_operational_reference`, que evalúa únicamente la versión preferida,
pero incluye todos sus perfiles operativos, contratos temporales y estimadores
disponibles necesarios para aplicar calidad, aplicabilidad y abstención.

`compare_selection` ya emite tiempos monotónicos para validación de manifiesto,
catálogo, resolución, contexto meteorológico y comparación preparada. También
acepta cachés de manifiesto, catálogo, meteorología preparada y comparación,
pero estas estructuras se crean actualmente dentro de una ejecución. La LRU
persistente conserva la respuesta completa, no los resultados parciales que
podrían reutilizar otras vistas o fechas.

## Objetivos

- Recommender frío local <= 10 s sobre el dataset de referencia actual.
- Recommender idéntico caliente <= 1 s.
- Abrir el detalle ya calculado por el Recommender <= 1 s.
- Conservar exactamente áreas elegibles, versiones, perfiles, contratos,
  estimadores, porcentajes, abstenciones, diagnósticos y ganadores.
- Mantener límites de memoria explícitos, invalidación determinista,
  cancelación y ausencia de datos obsoletos tras actualizar meteorología,
  reconstruir, reentrenar o promover modelos.
- Escalar por lotes; no construir una matriz densa cuyo ancho crezca con el
  número total de observaciones.
- No calcular ningún hash de contenido al crear o ejecutar una predicción
  caliente. La comparación ordinaria HA--worker debe ser O(1) respecto al
  número y tamaño de los ficheros del runtime.
- Calcular cada hash al crear, recibir o promocionar el fichero correspondiente,
  y reutilizarlo mientras el objeto permanezca inmutable.

## Entregas

### A. Atribución agregada del coste frío

Persistir o exponer en Diagnostics, por petición y de forma agregada:

- número de especies, áreas y comparaciones;
- perfiles, contratos, estimadores y miembros evaluados;
- hits/misses de respuesta, meteorología, modelos y comparación;
- segundos acumulados y máximo por `selection_manifest`,
  `selection_catalog`, `selection_resolution`, `weather_context` y
  `prepared_comparison`;
- bytes leídos y memoria máxima estimada de matrices, cuando proceda.

La primera medición debe separar preparación meteorológica, carga de
artefactos, construcción de variables, inferencia y selección. No se elegirá
la siguiente refactorización por intuición.

### B. Caché semántica persistente y acotada

Conservar dentro de `PredictorService` resultados parciales por una identidad
que incluya como mínimo fingerprint del runtime, generación meteorológica,
especie, área, fecha objetivo, fecha de emisión y selección operativa. El
detalle abierto desde una recomendación debe reutilizar la comparación ya
calculada.

La caché tendrá límites explícitos de entradas y bytes, métricas de expulsión e
invalidación total mediante `release_predictor_cache`. Ningún valor sobrevivirá
a un cambio de modelos, meteorología o fuentes contractuales.

### C. Workspace meteorológico común en memoria

Si `weather_context` domina, preparar una sola vez por área y fecha el máximo
contexto meteorológico requerido por los perfiles seleccionados. Las ventanas
y contratos menores se derivarán de ese workspace inmutable sin volver a leer
ni interpolar los mismos datos.

### D. Inferencia por lotes

Si `prepared_comparison` domina, agrupar las parejas especie/área compatibles
por artefacto, perfil, contrato y horizonte. Construir filas en memoria y
ejecutar `predict_proba` sobre matrices por lotes, reensamblando después el
mismo resultado auditable por área. El tamaño del lote debe ser configurable o
acotado por presupuesto de memoria para soportar datasets mucho mayores.

### E. Validación y criterio de parada

Cada entrega debe comparar antes/después:

- mejor apuesta y todas las filas especie/área/fecha;
- probabilidades y modelos elegidos;
- motivos de abstención, Brier, ROC-AUC y aplicabilidad;
- comportamiento tras invalidación y cambio de fingerprint;
- frío, caliente idéntico y navegación Recommender→detalle→Recommender;
- crecimiento de RAM y coste por lote.

Si la atribución no proyecta una reducción material, se detendrá la ampliación.
No se añadirá C/Cython/Numba/Rust antes de demostrar que un núcleo numérico,
después del batching, sigue siendo dominante.

### F. Manifiesto persistente publicado por HA

HA mantendrá un manifiesto persistente del runtime activo. Su publicación será
parte de las operaciones que cambian las fuentes consumidas por el Predictor:
promoción o rollback de modelos, publicación de una generación meteorológica y
escritura de perfiles, zonas conocidas, características de observaciones o
catálogo de estaciones.

Cada operación calculará únicamente los digests de los objetos nuevos o
modificados y publicará atómicamente el manifiesto y su huella global después de
que todos los objetos estén completos. Crear un job, servir su manifiesto y
resolver una descarga leerán esa publicación; no llamarán al constructor que
recorre y hashea el árbol vivo.

Si el manifiesto falta, está marcado como incompleto o no puede recuperarse
después de una interrupción, HA podrá reconstruirlo una vez y persistirlo antes
de publicar el runtime. Esa recuperación no se repetirá por consulta. La
petición conservará la huella que recibió al crearse: si la publicación activa
cambia mientras el job está en curso, el job terminará con retry explícito y no
mezclará generaciones.

### G. Recibo persistente de runtime verificado en el worker

El worker verificará tamaño y SHA-256 al recibir por primera vez cada objeto.
Tras materializar el runtime completo escribirá atómicamente un recibo que ligue
la huella global con el manifiesto instalado. El directorio versionado se tratará
como inmutable.

En trabajos posteriores, si huella solicitada, directorio versionado,
manifiesto local y recibo coinciden, el worker activará el runtime sin volver a
leer su contenido. Si cambia la huella, comparará los dos manifiestos y
reutilizará por digest los objetos ya verificados; solo descargará y verificará
los objetos ausentes. Si falta el recibo, una instalación quedó incompleta o
aparece una incoherencia estructural, realizará una verificación completa antes
de recrear el recibo.

La auditoría criptográfica completa seguirá disponible fuera del camino de una
predicción: en instalación, recuperación, Diagnostics o mantenimiento
explícito. Nunca se sustituirá una verificación necesaria al cruzar una frontera
de confianza por `mtime`; lo que se elimina es repetirla sin una nueva escritura
ni transferencia.

### H. Criterios de aceptación del transporte caliente

- una petición idéntica con hit de respuesta no debe construir ni hashear el
  manifiesto en HA;
- un runtime ya sellado no debe abrir ni hashear sus 713 objetos en el worker;
- el contador de bytes transferidos debe permanecer en cero;
- corrupción, falta de recibo y cambio de huella deben recuperar o fallar de
  forma segura, sin servir una mezcla;
- cancelación, retry, retención, rollback y promoción atómica mantienen su
  semántica;
- se persistirán tiempos separados de lectura del manifiesto publicado,
  sincronización del runtime, ejecución del backend y transporte del resultado;
- sobre la referencia real medida, la vuelta caliente debe acercarse al coste
  del backend cacheado y quedar como máximo en 2 s extremo a extremo en red
  local normal. Si la red o el polling impiden ese umbral, se documentará por
  separado y no se atribuirá al predictor.

## Riesgos

- Una clave incompleta puede servir meteorología o modelos obsoletos.
- Una caché sin presupuesto puede convertir rendimiento en presión de memoria.
- Agrupar perfiles con requisitos distintos puede omitir variables o ventanas;
  el workspace común debe ser un superconjunto demostrado, no un filtro.
- El batching puede alterar orden o tipos numéricos; la equivalencia debe
  comprobarse antes de cualquier release.
- El tiempo remoto incluye además cola, polling, transferencia y renderizado;
  se medirá por separado del backend científico.
- Un escritor que cambie una fuente sin publicar el nuevo manifiesto podría
  conservar una huella obsoleta. Todos los puntos de escritura deben usar una
  única API de publicación y las pruebas deben enumerarlos.
- Un recibo copiado sin haber completado el `fsync` permitiría aceptar un
  runtime parcial tras un corte. El recibo debe escribirse el último mediante
  temporal, `fsync` y `replace`.
