# Verificación de implementación · 20/09/2026

En el checkout local, sin Docker ni conexión a HA real/worker activo:

```sh
.venv/bin/python -m unittest \
  tests.test_mushroom_water_unification \
  tests.test_mushroom_climatic_water_balance \
  tests.test_mushroom_worker_packaging \
  tests.test_mushroom_ml_weather_workspace \
  tests.test_mushroom_ml_runtime_trainer \
  tests.test_mushroom_ml_runtime_inference \
  tests.test_mushroom_ml_runtime_features \
  tests.test_mushroom_ml_biology_v3 \
  tests.test_mushroom_ml_biology_v4 \
  tests.test_mushroom_ml_area_weather_runtime \
  tests.test_mushroom_soil_water_state \
  tests.test_mushroom_map_hydrology \
  tests.test_mushroom_map_weather \
  tests.test_mushroom_observation_context \
  tests.test_mushroom_ml_multiversion_input_preparation \
  tests.test_mushroom_ml_raw_weather \
  tests.test_mushroom_predictor_runtime \
  tests.test_mushroom_predictor_precompute \
  tests.test_mushroom_ml_multiversion_comparison \
  tests.test_mushroom_ml_version_registry \
  tests.test_mushroom_ml_training_freshness
```

322 pruebas, OK. Tras el último cambio de código (365 días también para el
perfil físico sin catálogo):

```sh
.venv/bin/python -m unittest tests.test_mushroom_ml_multiversion_comparison tests.test_mushroom_water_unification
```

42 pruebas, OK. Paridad con el mapa archivado de las 22 estaciones:

```sh
.venv/bin/python docs/mushrooms/SMI/adoption-2026-09-20/verify.py
```

22 estaciones / 1.320 fechas, coincidencia exacta; hashes y detalles en
`parity.json`. Los datos originales siguen en su snapshot, sin duplicarlos.

Interfaz (servidor temporal y navegador de pruebas; requiere poder escuchar en
localhost, no usa la sesión personal de Safari):

```sh
node tests/prediction_map_browser_check.mjs local-apps/wunderground/code/vendor/maplibre-gl.js local-apps/wunderground/code/vendor/maplibre-gl.css
git diff --check
```

Navegador `ok: true`, diff sin incidencias. Los cambios posteriores fueron de
Python/documentación, sin cambio posterior en los artefactos de interfaz.

Estos resultados prueban el código local en ese momento. **No prueban una
imagen desplegada ni sustituyen el circuito HA local + worker reconstruidos**
exigido por `AGENTS.md` antes de publicar. Quedan pendientes reconstrucción de
entradas y reentrenamiento operativo, promoción y precálculo/activación con el
nuevo contrato. No alterar el coordinador persistido del worker.

## Preparación de release 0.2.315 (en curso)

Primer circuito local HA+worker reconstruidos: reconstrucción y entrenamiento
base completos; multiversión falló antes de ejecutarse al validar el catálogo de
ajustes con el contrato anterior. Evidencia: `tmp/release-0.2.315/chain-jobs.json`.
No se ha publicado esta candidata ni instalado código en HA real.

Migración explícita del catálogo pre-SMI: valida primero identidad, contenido y
huella exacta del contrato anterior; conserva hiperparámetros y procedencia,
regenera la identidad bajo el contrato nuevo. No migra pesos, entradas ni métricas.
Otras revisiones o contenido alterado siguen rechazándose. Catálogo local probado:
714 decisiones, 403258 bytes; no fue necesario abrir sus artefactos de modelos.
La nueva ejecución debe reconstruir entradas, entrenar y evaluar de nuevo.

El mapa ahora transmite etiquetas deduplicadas por especie y referencias por día.
Nombre compartido con Predictor. Sólo se identifica una selección operativa;
una abstención no presenta como ganador el candidato inicialmente preferido.
Puede existir nombre sin IFF si la selección se conserva; con `no_model` o
`model_unavailable` no se muestra. Respuestas antiguas sin nombres siguen siendo
compatibles. El límite total de respuesta sigue vigente.

69 pruebas dirigidas de catálogo/migración/circuito/registro/mapa pasaron.
El smoke completo y la segunda reconstrucción/paridad están pendientes de registrar.

Segunda candidata reconstruida: smoke completo 1686 tests, 48 omitidos, OK;
prueba de navegador con nombres y estados en 1280/375/320 px, OK. Revisión visual:
se reserva 40 % de la fila a la especie; en móvil el nombre de modelo y el estado
pueden ocupar dos líneas a la derecha. Etiquetas para 32 especies: 2112 bytes con
una etiqueta por especie; cota de 6528 bytes con siete etiquetas largas por especie.

Paridad efectiva después de reconstruir/recrear ambos servicios existentes:
211 archivos HA y 114 worker sin diferencias. Huellas completas en
`tmp/release-0.2.315/parity.json`. Ambos archivos de configuración de coordinadores
conservan sus SHA-256 originales (`worker-config-before.json`).
Segundo circuito iniciado y registrado aparte en `tmp/release-0.2.315/attempt-2`;
conserva el fallo del primero como evidencia, sin borrar historial.

Incidencia observada durante la revisión: una predicción interactiva local
(`worker_job_j-umSqtfTNqI`, distinta del entrenamiento fallido) fue cancelada y
abandonada desde el coordinador. El worker registró la liberación del hilo a los
135.354415 s desde su inicio, con HTTP 409 al consultar el control del trabajo
ya terminal. Posteriormente /health mostró ambas colas idle, el endpoint de
estado de HA local devolvió «En espera» y el usuario confirmó ambos HA en espera.
No se ha reproducido ni corregido aún la latencia concreta de la tarjeta; no
atribuirla sin más al entrenamiento ni confundir duración total con tiempo desde
cancelación. La tarjeta aún toma foreground como estado general; véase TODO.


## Cierre de entrenamiento local y tooltips ES/CA/EN

Segundo circuito: reconstrucción `worker_job_8Yn24z2sc4pyo2eE` y base
`worker_job_HlrvnJPPGT03pmxC` completos/promovidos. Multiversión
`worker_job_uP3vYPNrLDpiijV-`, lote `operational_20260920T020702Z`, terminó
2026-09-20 02:16:29 UTC con verificación correcta: 714 ajustes previstos,
714 correctos, 0 fallidos. Fuente: registro persistido local, extracto en
`tmp/release-0.2.315/attempt-2/chain-jobs.json`.

Última instrucción del usuario: **él lanzará el precálculo**. No se ha lanzado
el de este circuito. No afirmar aceptación completa ni publicar/instalar HA real:
quedan precálculo, recepción/activación y aceptación del resultado local.

Tooltip de modelo (entrada al lado del IFF):

- Metadatos proceden de `feature_cols` del artefacto ya cargado por
  `compare_prepared`, mediante observador opcional usado sólo por el mapa.
  No se vuelven a cargar modelos ni se agregan columnas completas al payload.
  El entrenamiento/las probabilidades no cambian por este observador.
- SMI y balance directo se identifican independientemente. V4 de balance no
  usa SMI; V6w puede usar escalares SMI sin serie de balance/ET₀ como entrada
  directa. En ese caso la ayuda aclara que lluvia/ET sí intervienen al calcular SMI.
- `model_details` se deduplica junto a la etiqueta y se referencia por día;
  dos perfiles con igual etiqueta y distinta ventana no se confunden.
  Metadatos ausentes no se inventan. Se conserva el nombre sin IFF cuando
  existe selección y se oculta para `no_model`/`model_unavailable`.
- ES/CA/EN en `mushroom_labels.json`. Describe entradas, no importancia de
  coeficientes ni probabilidad de encontrar setas. Ayuda independiente del IFF,
  accesible por ratón, toque, foco y Escape.

Validación final tras estos cambios:

- 55 pruebas dirigidas, OK (contratos reales V4/V6, observador, protocolo).
- Smoke 1690 tests, 48 omitidos, OK en
  `/private/tmp/release-final-tooltip-smoke-authorized.log`. Primer intento tuvo
  seis errores de apertura de puertos por sandbox; se repitió autorizado.
- Navegador con fixtures: ES/CA/EN, fecha, estados vacíos, separación de ayudas,
  1280/375/320 px sin desbordamiento. Log `/private/tmp/model-tooltip-browser.log`;
  capturas `prediction-map-browser-ZPfaMT` en el directorio temporal del sistema.
- Imágenes locales existentes reconstruidas/recreadas; paridad 211 archivos HA
  y 114 worker, sin diferencias. Hash agregado HA
  `e04c6f988fbd7ab54f223049c5562520cc6eb3930faa8ed495df2aa60a453616`, worker
  `9ce5d9998cd93a596acc7e611526b7041c89fe061806ea9798eddf96f788c39f`.
  Archivos de coordinadores conservan exactamente las huellas previas.
- Config.js servido por HA local: HTTP 200 y nuevas claves traducidas presentes.
- Predicción puntual real dentro del contenedor HA local, Bellver
  42.31110/1.79167, fecha 20/09: usa el lote nuevo; siete selecciones
  `Smooth Shared–V6w`, ventana 30 días, entradas SMI/lluvia/temperatura/humedad/
  época del año, sin balance directo. Descriptor completo, sin nulls; respuesta
  19786 bytes. Evidencia `check-model-tooltip.py` y `model-tooltip-local.json`
  en `tmp/release-0.2.315`. Esta comprobación no reproduce la predicción del
  18/09 ni demuestra por sí sola que los falsos positivos estén corregidos.

Los últimos cambios son de metadatos/presentación; no se repitieron los 714
entrenamientos tras añadir el observador. Se verificó inferencia con los pesos
recién entrenados y el código final, además de la suite completa.

### Corrección del arranque del precálculo tras migrar a esquema 1.7

El usuario intentó lanzarlo desde HA local y recibió `Unsupported Predictor
precompute schema`. Fuente: `docker-media/rainmapper/results/predictor-precompute/desired.json`,
revisión 68, identidad 1.6. `_desired_revision_for_advance` sólo admitía
identidades antiguas hasta 1.5: se añade 1.6 para conservar el contador al crear
una solicitud nueva. La carga/activación de artefactos sigue exigiendo 1.7;
no se reutilizan resultados anteriores ni se cambia el cálculo científico.

- Prueba de regresión del control: el lector estricto rechaza 1.6 y el avance
  crea una identidad actual. Prueba HTTP/control con fichero temporal de
  revisión 68: solicitud aceptada (202), revisión 69, identidad nueva; conserva
  las comprobaciones de reutilización de trabajo y sustitución forzada.
- 418 pruebas dirigidas OK (`/private/tmp/precompute-schema-tests.log`).
- Smoke completo: 1690 pruebas, 48 omitidas, OK en 77.132 s
  (`/private/tmp/release-precompute-schema-smoke.log`).
- Reconstruidas y recreadas las dos imágenes/servicios existentes. Paridad
  efectiva 211 archivos HA y 114 worker, sin diferencias. Hash agregado HA
  `06af1a59ce298986a89074ae6330431862f86f32435a5eb86b3dcd12892e1910`, worker
  `2a3eb7c9f914bb7a6612429973dd77b5f9ffd06de850491dfa083cf0f72fbc8e`.
- Configuración de los dos coordinadores idéntica antes/después; ambas colas
  idle. HTTP del mapa local 200. Dentro de HA, el control acepta la revisión
  persistida 68 para avanzar y se comprueba que el fichero no ha cambiado.

No se lanzó el precálculo desde Codex ni se modificó HA real. Pendiente el
reintento del usuario y comprobar recepción/activación antes de publicar.

### Precálculo local aceptado para la release 0.2.315

El reintento del usuario completó `worker_job_7YWJHNU9LAaR` entre
2026-09-20 02:50:31 y 02:55:34 UTC, sin error. Se verificaron directamente
`active-receipt.json`, `desired.json` y `active.sqlite3` en
`docker-media/rainmapper/results/predictor-precompute`:

- Revisión deseada y activada: 69. Identidad de artefacto:
  `sha256:5e5c2ff1fc3a0ffc81834f29ce67a53ccafc67e2f9a6e4b8686c69a989b81f39`.
- Esquema 1.7, `publication_state=complete`, cobertura 20–26/09/2026;
  generaciones del lote `operational_20260920T020702Z`.
- 88 áreas, 9 especies, 7 días; 616 filas de cobertura, 525 miembros
  operativos y 749 respuestas persistidas.
- Archivo de 28.004.352 bytes, SHA-256
  `e6d3b2321a4641d2489bbff7f329b7190cb2d5a7cb452ddd056f325d0ac10515`,
  idéntico al recibo. SQLite `quick_check=ok`.
- Paridad repetida antes de publicar: 211/114 archivos, sin diferencias;
  mismas huellas del bloque anterior. No cambió código ejecutable desde el
  smoke de 1690 pruebas: no se repitieron entrenamiento ni smoke.

El usuario solicitó publicar y confirmó que había finalizado el precálculo.
Circuito local completo; publicación autorizada. Instalación y trabajos de HA
real siguen a cargo del usuario.

Publicación completada: `0.2.315` y `latest` en GHCR, digest común
`sha256:8d064cef61c9e24fe283796b71aa37ad4d3eea2924141f4be554de1cc1a1f885`,
AMD64 y ARM64 verificados mediante `docker buildx imagetools inspect`.
Script de publicación terminado con código 0. [Informe](../../../reports/ha-release-0.2.315.json).
