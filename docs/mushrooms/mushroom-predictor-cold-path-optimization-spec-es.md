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

## Riesgos

- Una clave incompleta puede servir meteorología o modelos obsoletos.
- Una caché sin presupuesto puede convertir rendimiento en presión de memoria.
- Agrupar perfiles con requisitos distintos puede omitir variables o ventanas;
  el workspace común debe ser un superconjunto demostrado, no un filtro.
- El batching puede alterar orden o tipos numéricos; la equivalencia debe
  comprobarse antes de cualquier release.
- El tiempo remoto incluye además cola, polling, transferencia y renderizado;
  se medirá por separado del backend científico.
