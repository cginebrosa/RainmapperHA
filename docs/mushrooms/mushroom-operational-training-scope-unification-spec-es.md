# Unificación del alcance del entrenamiento operativo

Estado: implementación local en validación; sin despliegue ni reconstrucción real
Fecha: 2026-08-28

## Estado de implementación local

El contrato canónico vive en
`rainmapper_core/mushroom_operational_training_scope.py`. Calcula la elegibilidad
después de `filter_eligible()` y `aggregate_to_area_episodes()`, conserva los
recuentos y motivos estructurados, y sella el resultado con `scope_id`. El mismo
componente construye el plan independiente del transporte, con el alcance
completo, versiones, perfiles, fits y `tuning_catalog_id`, y lo identifica con
`plan_id`.

La ruta local, HA y el worker transportan y validan esas identidades. ML v0
recalcula el alcance solo como comprobación de integridad contra los inputs
recibidos y debe obtener exactamente el documento sellado; no puede redefinirlo.
La preparación V2–V6 hace la misma comprobación antes del trabajo pesado, exige
cobertura completa del catálogo y filtra todos los builders y hold-outs por las
especies del plan. El entrenamiento y la entrega operativa rechazan diferencias
de especies, fits, alcance, plan o catálogo antes de la promoción.

La política implementada para una especie admitida sin tuning congelado es
fallar en el preflight con las claves ausentes. No se sintetiza ni se copia una
decisión. El modelo vivo permanece protegido por la promoción posterior a la
verificación y por el rollback existente.

Validación local del 2026-08-28, sin reconstruir, entrenar, instalar ni
promocionar modelos:

- mismos `mushroom_observation_features_v0.json`, `mushroom_known_sites.json`,
  registro y catálogo para las dos serializaciones de entrada;
- igualdad exacta de scope y plan;
- `scope_id`
  `sha256:45f5aad288480362ccbb9baf5fb6bdebddce944fdfea0184d5a763fe2b88a865`;
- `plan_id`
  `sha256:be5d22b4e0897f0940d39a1203fc1be4c695b3c1102d8a8344a56fab7810e13f`;
- `tuning_catalog_id`
  `sha256:804179cf51e229b04537e43de5a528794e1e7584ff0c5834d623df3110ee570e`;
- ocho especies admitidas, cinco versiones, once perfiles y 636 fits
  planificados;
- Cantharellus: diez filas elegibles, nueve episodios y exclusión
  `insufficient_area_episodes`;
- preparación completa de `v2_v5_heldout`, V3/V4/V5 fixed y lag, y
  `v6_heldout`, todos con las ocho especies y las identidades anteriores;
- 84 pruebas dirigidas de scope, preparación, transporte y worker, y 301 de HA,
  ruta local, runtime, plan y catálogo, correctas sobre el estado documentado;
- smoke local completo: 1.078 pruebas, compilación Python, parseo JavaScript y
  shell, fixtures auxiliares y control de whitespace, correcto.

Siguen pendientes la igualdad de fits ejecutados, métricas y artefactos entre
ejecutores, la telemetría/UI y una medición integral. No debe
repetirse la reconstrucción real sin autorización.

## Objetivo

Eliminar la divergencia entre la reconstrucción local y la cadena HA→worker.
Con el mismo snapshot, catálogo de modelos y selección de versiones, ambas rutas
deben calcular una sola vez el mismo alcance de especies, sellarlo y consumirlo
sin volver a descubrir especies en pasos posteriores.

La corrección no consiste en añadir una decisión para una especie concreta. Debe
eliminar la duplicación de criterios que permitió que local y remoto tomaran
decisiones diferentes con las mismas observaciones.

## Evidencia del fallo real

La reconstrucción iniciada el 2026-08-28 a las 04:41:46 CEST produjo esta cadena:

| Trabajo | Creado | Inicio worker | Fin | Resultado |
| --- | --- | --- | --- | --- |
| Reconstrucción completa | 04:41:46 | 04:45:41 | 04:52:08 | completado |
| ML v0 | 04:52:15 | 04:52:18 | 04:54:19 | completado |
| ML operativo V2–V6 | 04:55:46 | 04:56:04 | 05:02:05 | fallido |

El tiempo real hasta el fallo fue 20 min 19 s. La UI mostró únicamente los
intervalos `started_at`→`finished_at`, ocultando 3 min 55 s antes del primer
claim y 1 min 27 s entre ML v0 y la creación del tercer trabajo.

El tercer trabajo falló durante la preparación de inputs con:

```text
KeyError: altitude_v2|fixed_gap_7d_altitude_v2|common_idw|
logistic_regression_reduced_v1|cantharellus_cibarius_sl
```

Fuentes primarias consultadas:

- `/share/rainmapper/mushroom-data/mushroom_worker_jobs.json`;
- logs del contenedor `rainmapper-worker:1.0.21`;
- lote real instalado `operational_20260825T221049Z`;
- lote local instalado `local_operational_20260827T225123Z`;
- informes candidatos de reconstrucción y ML v0 conservados en
  `.worker-candidate-results`.

No había diferencia de observaciones: local y HA real contenían las mismas 15
observaciones de Cantharellus y 10 filas inicialmente elegibles. La divergencia
era de orquestación y estado instalado:

- `eligible_training_species()` seleccionó Cantharellus por tener 10 filas;
- `mushroom_ml_trainer.run()` agregó las filas en episodios área/fecha, obtuvo 9
  episodios y la omitió del resultado ML v0;
- `linked_ml_trained_species_ids()` selló ocho especies para el trabajo remoto;
- la evaluación V2–V6 recorrió de nuevo el snapshot completo y solicitó una
  decisión para Cantharellus, ignorando el alcance sellado;
- el lote real anterior contenía ocho especies y 636 fits, sin Cantharellus;
- el lote local posterior contenía nueve especies y 714 fits, incluida la clave
  que faltaba, por lo que el defecto quedó enmascarado en local.

## Problema de arquitectura

Compartir repositorio e imagen no garantiza equivalencia: actualmente existen
dos implementaciones de la orquestación dentro del mismo source.

- La ruta local parte de `mushroom_local_full_update.eligible_training_species`.
- La ruta remota usa el resultado efectivo de ML v0 mediante
  `linked_ml_trained_species_ids`.
- Los scripts de preparación/evaluación vuelven a descubrir especies desde los
  datasets y pueden salirse de ambas listas.

El alcance científico no puede depender del punto de entrada, del entorno ni de
qué lote previo haya quedado instalado.

## Diseño obligatorio

### 1. Alcance canónico único

Crear un único componente compartido que produzca un
`OperationalTrainingScope` a partir del snapshot inmutable y del contrato de
entrenamiento. Como mínimo debe contener:

- identidad/fingerprint del snapshot;
- especies candidatas y recuento de filas;
- episodios después de la agregación canónica;
- presencia de ambas clases requeridas;
- especies admitidas;
- especies omitidas con motivo estructurado;
- revisión del contrato de elegibilidad.

La elegibilidad debe decidirse después de aplicar la misma agregación y las
mismas comprobaciones que usa el entrenamiento real. No se admite seleccionar
por filas y descartar posteriormente con un criterio distinto.

### 2. Cálculo único y sellado

El alcance se calcula una vez por reconstrucción y se incorpora a los manifests
de los tres trabajos. Debe viajar con SHA-256 y formar parte de sus identidades.
ML v0 puede certificar el resultado, pero no redefinir silenciosamente el
alcance. Cualquier discrepancia entre alcance solicitado y entrenamiento
efectivo debe convertirse en un diagnóstico explícito antes de V2–V6.

### 3. Consumo estricto

Todos los pasos deben aceptar y respetar explícitamente `species_ids`:

- reconstrucción de features;
- ML v0;
- construcción de V2/V3/V4/V5/V6;
- hold-out y comparaciones;
- generación del catálogo de calidad;
- entrenamiento de artefactos;
- verificación y promoción.

Ningún paso posterior puede redescubrir especies recorriendo el snapshot
completo. Las filas de especies no incluidas pueden permanecer en el snapshot,
pero deben quedar fuera de cálculo, métricas y búsqueda de tuning.

### 4. Cobertura del catálogo de tuning

Antes del trabajo pesado debe validarse que el catálogo congelado cubre el
producto exacto de especie, versión, perfil, contrato temporal y estimador del
alcance sellado.

No se sintetizarán decisiones de tuning ni se copiarán desde otra especie sin un
contrato científico explícito. Si una especie recién elegible no tiene cobertura:

- se conserva intacto el modelo operativo vigente;
- se registra el hueco exacto y se muestra en UI;
- el sistema no inicia minutos de preparación destinados a terminar en
  `KeyError`;
- el resultado no puede presentarse como promoción completa.

La política científica para incorporar por primera vez una especie sin tuning
(benchmark previo o configuración base explícita) debe quedar codificada y
probada, no inferida durante el entrenamiento.

### 5. Una sola orquestación

Local y remoto deben construir el mismo plan serializable y ejecutar el mismo
estado de fases. El transporte puede cambiar —llamada local o job HTTP—, pero no
puede cambiar:

- alcance;
- orden lógico;
- inputs;
- catálogo congelado;
- validaciones;
- artefactos finales.

La ruta local debe poder generar el mismo manifiesto que recibiría el worker y
usarlo como prueba contractual, evitando una segunda implementación funcional.

### 6. Tiempo total y fases visibles

La UI debe separar:

- duración total desde `created_at` hasta fin, incluyendo preparación HA;
- duración de la fase actual;
- tiempo en reconciliación SoilGrids;
- materialización/verificación del catálogo;
- preparación y sellado del bundle;
- espera de claim;
- ejecución worker;
- recepción, verificación, promoción y transición al siguiente trabajo.

El objetivo de ≤10 minutos se mide desde la pulsación hasta la promoción final,
no sumando únicamente tiempos `started_at`→`finished_at`.

## Integridad operativa

La unificación debe conservar:

- snapshots inmutables y hashes verificables;
- cancelación y retry idempotentes;
- rollback y conservación del modelo vivo ante cualquier fallo;
- promoción atómica únicamente tras verificar toda la entrega;
- handoff local sellado entre trabajos del mismo worker;
- retención vigente, sin ampliarla ni borrar datos;
- visibilidad de especies omitidas y causas, sin omisiones silenciosas.

## Pruebas de aceptación

1. Diez filas de una especie que se agregan en nueve episodios producen la misma
   exclusión y el mismo motivo en local y remoto.
2. Una especie presente en el snapshot pero fuera del alcance sellado no llega a
   hold-out, tuning, fits ni métricas.
3. Local y remoto producen el mismo `OperationalTrainingScope` y fingerprint con
   iguales inputs.
4. Local y remoto producen el mismo plan de perfiles, especies y fits.
5. Un hueco de tuning se detecta antes de preparar/evaluar V2–V6 y preserva el
   modelo vivo.
6. Un catálogo que sí cubre el alcance permite completar los mismos artefactos y
   métricas en ambos ejecutores.
7. Cancelación en preparación, entrenamiento, upload y promoción conserva el
   comportamiento actual.
8. Retry reutiliza inputs sellados únicamente si coinciden snapshot, alcance y
   catálogo.
9. La UI muestra duración total y duración de fase sin reinicios.
10. La prueba real completa debe terminar en ≤10 minutos; si no, la telemetría
    debe atribuir todos los segundos a fases concretas.

## Evidencia de integración HA→worker del 2026-08-28

La primera ejecución real con HA `0.2.273` y worker `1.0.22` detectó una
asimetría de representación que las pruebas iniciales no cubrían. ML v0 sellaba
el scope con el JSON de features normalizado para las rutas finales, mientras
V2–V6 recibía el JSON original del candidato de reconstrucción. Las filas y las
ocho especies eran las mismas, pero `source_identity.features_sha256` no podía
coincidir; la preparación abortó antes de entrenar o promocionar V2–V6.

El contrato queda precisado así:

- el handoff enlazado transporta los bytes exactos de `features.json` y
  `known_sites.json` usados para calcular el scope de ML v0;
- sus SHA-256 se validan contra el bundle de ML v0 antes de limpiar ese bundle;
- esos mismos bytes se incorporan al snapshot V2–V6, sin volver a leer el
  candidato original ni el `known-sites` vivo para decidir el alcance;
- V2–V6 recalcula el scope solo como validación de integridad y exige igualdad
  completa con el scope sellado; no redefine especies ni decisiones.

Las pruebas centinela verifican la captura previa al handoff asíncrono, los
digests y la igualdad byte a byte de ambas entradas dentro del bundle V2–V6.
La validación local posterior completó 271 pruebas del servidor, 49 pruebas
transversales dirigidas y el smoke completo de 1.082 pruebas. La corrección se
publicó en HA `0.2.274`; su índice OCI es
`sha256:899d45f797952218ea865e40d3293247ab14d8d6f3e6e53ea7f807595f0fd001`
y contiene manifests `linux/amd64` y `linux/arm64`. La equivalencia real queda
pendiente de una nueva ejecución iniciada por el usuario.

## Orden de implementación propuesto

1. Extraer el cálculo canónico y sus pruebas de agregación/elegibilidad.
2. Generar el plan/manifiesto único y usarlo en la ruta local.
3. Transportar y validar el mismo plan en la ruta HA→worker.
4. Aplicar el filtro obligatorio en todos los builders y evaluadores.
5. Añadir la prevalidación completa del catálogo de tuning.
6. Corregir duración total/fase y telemetría de transiciones.
7. Ejecutar pruebas dirigidas, smoke local completo y una única medición fría y
   caliente antes de cualquier release.
