# Plan de perfiles ML promocionables y extensibles

Estado: **FASE 4 IMPLEMENTADA; V3–V6 DECLARADAS TÉCNICAMENTE
PROMOCIONABLES COMO VERSIONES COMPLETAS**.

Este plan define cómo pasar de un benchmark científico a una generación
operativa sin acoplar la promoción a `altitude_v2`, `biology_v3` ni a ninguna
versión futura concreta. El primer caso de uso es la comparación controlada:

- `biology_v3/core`: V3 actual, sin cambios;
- `biology_v3/common_idw_plus_physical_state`: V3+ físico, con el mismo target,
  filas, particiones, contratos temporales y estimadores que V3 core, añadiendo
  balance climático y estado hídrico/SMI calculados causalmente desde el mismo
  IDW.

V3 core y V3+ son técnicamente operables. Registrarlos y compararlos no
autoriza instalar nada ni cambiar Predictor: el benchmark solo aporta evidencia
orientativa y la promoción exige dos acciones humanas separadas.

## Invariantes

1. Se promociona una **versión completa y una generación concreta**, incluyendo
   todos sus perfiles `operational_eligible`; nunca una celda o perfil aislado
   elegido después de observar el hold-out.
2. Benchmark, candidata operativa y generación activa tienen identidades
   distintas e inmutables.
3. Una promoción siempre requiere confirmación humana; no existe promoción
   automática por métrica.
4. El runtime anterior continúa utilizable hasta que candidata, artefactos,
   inputs e inferencia hayan superado todos los gates.
5. Registro, descriptor de runtime y estado de instalación cambian como una
   única transacción lógica y se restauran juntos en rollback.
6. El orquestador trabaja con contratos declarativos. El código específico de
   una familia de variables queda detrás de un adaptador identificado, no en
   ramas de coordinación o UI basadas en nombres `Vx`.
7. Toda candidata transporta el catálogo de calidad del benchmark fuente. El
   catálogo conserva su propio snapshot científico: no se recalculan ni se
   atribuyen sus Brier al reentrenamiento operativo con todas las filas.
8. La interpretación recibe, además de las variables usadas por el modelo, la
   evidencia ecológica necesaria (`significant_rain_found_90d` y completitud de
   búsqueda). Esos campos no entran en la matriz predictiva ni pueden perderse
   al cambiar de versión.
9. No existe una lista fija LR/RF ni una categoría operativa/sombra en la
   selección del score. En cada especie, perfil y contrato puede aportar la
   probabilidad cualquier estimador declarado por esa versión que esté
   disponible, no esté excluido para la entrada actual y tenga Brier de
   validación menor que la prevalencia. Entre ellos se elige el menor Brier;
   los empates se resuelven de forma determinista por `estimator_id`.

## Identidad genérica

El objetivo operativo debe evolucionar desde el actual `active_version_id` a
una referencia completa:

```json
{
  "active_operational_target": {
    "version_id": "biology_v3",
    "generation_id": "biology_v3-..."
  }
}
```

La clave promocionable es por tanto:

```text
version_id / generation_id
```

`version_id` conserva la genealogía científica y agrupa sus perfiles;
`generation_id` fija snapshot, conjunto completo de perfiles, artefactos y
hashes. En V3 la generación contiene `core` y
`common_idw_plus_physical_state`. Predictor muestra fixed y lag para ambos, sin
seleccionar silenciosamente un perfil principal.

## Contrato declarativo de perfil

Cada perfil promocionable debe declarar o resolver de forma verificable:

- contratos temporales;
- estimadores y su alcance `species` o `shared`;
- adaptador de entrenamiento e inferencia;
- conjunto y orden exacto de variables;
- días de histórico necesarios, separando ventana predictiva y calentamiento;
- si necesita balance, SMI u otro estado físico;
- campos de `known_sites` y entradas meteorológicas que forman su identidad;
- política de completitud de especies;
- capacidades mínimas que debe anunciar HA o worker;
- versión de schema de sus artefactos.

El catálogo puede exponer esos datos a planificación, preparación, transporte,
Predictor y UI. Ninguna de esas capas debe deducir requisitos buscando tokens
como `v3`, `v5`, `physical_state` o `climatic_balance` en el nombre.

## Primer perfil: V3+

Identidad inicial:

```text
profile_key: biology_v3/common_idw_plus_physical_state
nombre UI: Biology V3+ physical
ventana predictiva: la de V3 core
histórico físico: hasta 365 días causales para probar convergencia 90/180/365
SMI experimental predeclarado: wv0033_0_30cm
```

El depósito `wv0033_0_30cm` es la variante superficial principal ya documentada
en la evaluación V4; usarla aquí fija la hipótesis antes del nuevo benchmark.
V3+ no incorpora las extensiones meteorológicas V4 de 22--30 días: contiene
exclusivamente las columnas de V3 core más balance climático y los resúmenes de
estado hídrico. La comparación usa la intersección de filas elegibles para que
la distinta cobertura de SMI no cambie el soporte entre V3 y V3+.

La fase científica debe demostrar además paridad exacta entre la fila archivada
de entrenamiento y la fila reconstruida por el adaptador de inferencia. Aunque
esa paridad pase, el perfil sigue sin ser operativo hasta completar la fase de
promoción.

## Gates de candidata operativa

La acción `Preparar candidata completa` toma la versión cubierta por el informe,
revalida que su snapshot siga coincidiendo con los inputs vivos y reutiliza sus
bundles ya ajustados. Solo cambia su identidad de batch/generación y vuelve a
calcular los hashes del empaquetado; no repite la preparación meteorológica, el
ajuste ni el hold-out. Si los inputs han cambiado, la candidata se rechaza y se
exige un benchmark nuevo. Su gate se considera `passed`
solo cuando consten todos estos resultados:

1. **Declaración:** perfil y adaptador existen y son compatibles con el runtime.
2. **Completitud:** existen todos los artefactos planificados para especies,
   contratos y estimadores/miembros requeridos; no hay fits fallidos.
3. **Integridad:** manifests, rutas, tamaños y SHA-256 coinciden.
4. **Paridad:** entrenamiento e inferencia producen las mismas variables, orden,
   unidades y reglas de ausencia.
5. **Inputs vivos:** las identidades semánticas exigidas por el perfil siguen
   coincidiendo con observaciones, `known_sites`, estaciones e histórico.
6. **Dominio:** la cobertura mínima declarada se cumple sin convertir ausencias
   en cero ni degradar silenciosamente la fuente IDW.
7. **Smoke Predictor:** fixed y lag 1..7 pueden resolverse para casos
   representativos con el nuevo batch todavía en staging. Debe comprobar Brier
   y baseline desde el catálogo fuente, y coherencia entre lluvia acumulada,
   días desde lluvia significativa y el veto ecológico.
8. **Aprobación:** el usuario confirma versión, perfiles, generación, snapshot y
   generación anterior que quedará disponible para rollback.

El benchmark sirve como evidencia para la decisión humana, pero ninguna
métrica declara una versión ganadora ni bloquea una elección consciente. Los
bundles del benchmark ya se ajustan con todas las filas elegibles; el hold-out
se evalúa aparte y no reemplaza ese ajuste. Por ello la candidata conserva
exactamente esos modelos verificados y evita un segundo trabajo equivalente.

## Transacción de promoción y rollback

La promoción genérica implementada sigue esta secuencia:

1. verificar otra vez gates y frescura;
2. cargar y verificar todos los bundles de la candidata todavía archivada;
3. escribir un journal con objetivo nuevo y copias exactas del registro y
   descriptor anteriores;
4. instalar el batch nuevo y sustituir atómicamente el descriptor runtime;
5. persistir el nuevo `active_operational_target` y el historial;
7. invalidar cachés únicamente después de completar ambos cambios;
8. marcar el journal como completado.

Ante cualquier fallo se restauran descriptor, objetivo activo y estado de
caché. El batch nuevo puede conservarse para diagnóstico, pero nunca queda
seleccionado parcialmente. El rollback manual aplica la misma transacción en
sentido inverso usando una generación preservada, no reentrenando el pasado.

## Extensión a cualquier versión actual o futura

Añadir un perfil nuevo debe reducirse a:

1. registrarlo con identidad, contratos, estimadores, requisitos y adaptador;
2. implementar el adaptador compartido de `build_training_dataset` y
   `build_inference_features`;
3. demostrar por tests de contrato que ambas salidas tienen paridad;
4. anunciar la capacidad equivalente en HA/worker;
5. ejecutar benchmark y archivar informe;
6. preparar una candidata de versión completa y superar los gates genéricos;
7. promover mediante la misma transacción.

Además, V4–V6 y toda versión futura deben superar una prueba transversal del
predictor antes de considerarse integradas:

- el manifiesto candidato declara `quality_catalog` con SHA-256 y el transporte
  incluye el fichero;
- si una generación antigua carece de esa referencia, el runtime solo admite
  como compatibilidad el catálogo del `source_benchmark_batch_id`, verificando
  el hash archivado;
- la UI muestra Brier, baseline y soporte cuando el catálogo contiene la celda,
  sin inventar métricas cuando no la contiene;
- la lluvia significativa encontrada por el adaptador llega a interpretación y
  no se convierte por ausencia del campo en un falso «no ha llovido»; el
  adaptador común busca este contrato en cualquier nivel anidado de `quality`,
  sin ramas nominales para V3, V4 o una versión futura;
- el texto de la tarjeta describe la versión operativa activa, no contiene un
  nombre V2/V3/V4 fijo;
- una candidata ya activada deja de ofrecer «Activar versión completa» y la
  promoción activa conserva únicamente la acción de rollback.

V2–V6 y perfiles futuros siguen exactamente ese procedimiento. El registro ya
declara las familias propias de V5 (`elastic_net` y `sparse_group`) y V6
(`species`, `shared` y `partial_pooling`) junto a su alcance. No se elige un
único miembro al preparar la candidata: la versión conserva todos los
estimadores declarados y la interpretación selecciona por celda el que cumple
la regla Brier anterior. Esa política es datos del perfil y no una rama nominal
de la promoción.

La habilitación técnica vigente es:

- V4: versión completa con `extended_weather` y `climatic_balance`;
- V5: versión completa con `raw_primary_plus_physical_state`;
- V6: versión completa con `smooth_weather_physical_state` y sus tres alcances.

Que una versión sea promocionable no afirma que sea científicamente superior.
La UI exige benchmark archivado, preparación explícita de candidata y una
segunda confirmación humana para activarla; nunca existe promoción automática.
Los adaptadores V4–V6 deben reenviar el evento de lluvia significativa y su
edad como evidencia exclusiva de interpretación, sin introducirla de forma
accidental en la matriz predictiva.

Una versión que no pueda implementar el contrato queda visible y ejecutable
como benchmark, pero la UI explica por qué todavía no es promocionable.

## Entrega incremental

### A. V3/V3+ científico

- [x] registrar V3+ sin modificar V3 core;
- [x] materializar únicamente core + balance + SMI;
- [x] resolver requisitos de preparación desde el perfil;
- [x] registrar el resultado del benchmark real V3/V3+ emparejado en contexto;
- [x] probar paridad train/inferencia;
- [x] declarar ambos perfiles técnicamente operables sin activarlos.

### B. Infraestructura genérica de candidatas

- [x] introducir `active_operational_target` compatible con registros antiguos;
- [x] generar planes para una versión candidata aunque todavía no sea la activa;
- [x] persistir generations `trained_model` y journal de promoción;
- [x] eliminar de coordinación y transporte la exigencia circular de que la
  candidata ya sea la versión activa.

### C. Promoción y rollback desde el informe

- [x] mostrar la acción solo cuando el informe contiene la versión completa;
- [x] añadir preparación y confirmación explícitas separadas;
- [x] realizar instalación, smoke de bundles, cambio de objetivo y rollback;
- [x] auditar cuándo, desde qué snapshot y qué generación fue sustituida;
- [x] reconstruir HA local y validar que el informe completo ofrece la acción;
- [ ] ejecutar candidata, promoción, cuatro salidas Predictor y rollback reales.

### D. Generalización y limpieza

- migrar requisitos nominales restantes a datos del catálogo/adaptadores;
- parametrizar las pruebas sobre todos los perfiles registrados;
- comprobar paridad HA local/worker sin tocar HA real;
- documentar el procedimiento mínimo para registrar una versión futura.

## Pruebas obligatorias

- V3 core conserva exactamente columnas, selección y número de fits anteriores;
- seleccionar solo V3+ no prepara ni evalúa perfiles no requeridos;
- V3/V3+ comparten filas, targets y splits en la comparación;
- el perfil físico exige balance y SMI completos y conserva ausencia explícita;
- paridad entrenamiento/inferencia campo a campo;
- perfiles desconocidos o sin adaptador no pueden ser candidatos;
- artefacto ausente, hash alterado, fit fallido o input obsoleto bloquean la
  promoción;
- fallo en cada punto de la transacción conserva el Predictor anterior;
- tras promoción, el entrenamiento operativo resuelve todos los perfiles de la
  versión activa y fixed/lag siguen funcionando para cada uno;
- el catálogo Brier del benchmark fuente viaja en la candidata, mantiene su
  identidad científica y queda resoluble tras instalación;
- una lluvia significativa presente no activa el guardrail de ausencia por
  pérdida de metadatos entre `quality`, comparación e interpretación;
- rollback restaura exactamente objetivo y batch anteriores.

## Fuera de alcance del primer corte

- seleccionar automáticamente un ganador;
- promocionar un estimador aislado;
- cambiar V2 operativo durante el benchmark V3/V3+;
- activar V3+ antes de implementar gates y transacción;
- bump, build de release, publicación, HA real o worker normal.

### Contrato ecológico de inferencia

La promoción de una versión no puede limitarse a conservar sus columnas
predictivas y artefactos. Cada adaptador de inferencia debe propagar también,
fuera de `predictive_features`, el contrato ecológico común:
`rain_event_search_complete`, `significant_rain_search_complete`,
`significant_rain_found_90d` y `days_since_significant_rain_at_target`.
Estos campos no entrenan ningún estimador, pero son necesarios para que el
dictamen operativo interprete la misma lluvia que muestra el detalle técnico.
Las pruebas de promoción deben atravesar el adaptador diario real de cada
versión; no basta con probar un mapa de calidad sintético.
