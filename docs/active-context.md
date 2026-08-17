# Active Context

Ventana operativa para continuar RainmapperHA. No reconstruir el estado actual
desde conversaciones, memorias ni informes históricos: revalidar siempre código,
datos y runtime. Las razones duraderas viven en `docs/decisions.md` y las
especificaciones temáticas enlazadas.

## Estado al cierre — 2026-08-17

- Workspace verificado:
  `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- El worktree es grande y deliberadamente mixto. Contiene la implementación
  V2–V6, meteorología, UI, worker, pruebas y documentación, además de cinco PDF
  científicos no rastreados. No limpiar, resetear, sustituir ni borrar nada.
- Estado de producción observado durante esta sesión en la UI y terminal del
  usuario: HA `0.2.256` y worker M1 `1.0.10` están instalados; M1 conserva
  identidad, emparejamiento y caché. Codex no lo ha revalidado directamente
  contra los hosts al cierre.
- El worker real usa la dirección Tailscale de HA porque está fuera de la LAN.
  La prohibición operativa es que Codex no use Tailscale ni exponga SMB; no
  significa retirar o cambiar esa URL persistente del worker.
- La instalación real `0.2.256`/`1.0.10` sigue pendiente de la corrección; no
  repetir allí la regeneración hasta publicar e instalar una release autorizada.
- Ninguna V2–V6 está validada como preferida o ganadora. V2 alimenta la tarjeta
  histórica únicamente por orden cronológico. Todas siguen experimentales y
  deben mostrarse con calidad hold-out, aplicabilidad y cautelas propias.

## Corrección implementada localmente

- La regeneración ya no depende de JSON del laboratorio. Cada ejecución congela
  un snapshot fresco de observaciones, catálogos, mapeos GIS, histórico
  meteorológico y entradas auxiliares; el worker deriva de él V2–V6.
- La acción única `Reconstruir y reentrenar todo` mantiene tres pasos:
  reconstrucción común, entrenamiento ML v0 y lote comparativo V2–V6. No se ha
  añadido una acción parcial para el tercer paso.
- `lag_event` conserva un solo ajuste por especie + contrato + estimador; los
  horizontes 1/2/3/7 filtran las probabilidades del mismo hold-out y nunca
  reentrenan.
- Cada batch nuevo guarda `training-input-manifest.json`, con hashes e identidad
  de entrada pero sin datos brutos ni rutas privadas. El Predictor compara esa
  identidad con las entradas vivas y avisa si la generación está
  `stale`, `unknown` o `invalid`; solo omite el aviso cuando está `current`.
- La copia temporal recibida desde el worker se elimina solo después de una
  instalación íntegra y verificada. Si la instalación falla, queda retenida
  para diagnóstico.
- Las imágenes públicas se han reducido a código, dependencias y defaults. HA
  incluye una plantilla de observaciones vacía; no contiene observaciones,
  snapshots, hold-outs, benchmarks ni modelos entrenados. El worker tampoco
  incorpora esos datos.
- Especificación vinculante:
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`.

## Runtime local restaurado y ejecutor HA local

- El montaje temporal que introducía el worker ficticio `Validación local`, HA
  en `8103` y worker en `8111` fue retirado. También se eliminó su volumen
  temporal; el worker normal y su volumen persistente no se modificaron.
- El HA local ordinario vuelve a ser `http://127.0.0.1:8101/`. Muestra el mismo
  registro de workers que el HA real, pero `M1 Personal` aparece desconectado
  porque el proceso normal del worker mantiene una única conexión saliente con
  el HA real de la RPi4. No se reempareja ni se cambia esa URL para usar el HA
  local.
- Se reintroduce una capacidad distinta y explícita para el laboratorio:
  `RAINMAPPER_LOCAL_HA_COMPUTE_ENABLED=true`. Solo
  `rainmapper-local/docker-compose.yml` la activa. El default de la imagen HA y
  el HA real permanece desactivado y coordinador-only.
- Cuando está activa, la UI ofrece `Home Assistant local`. El cálculo se ejecuta
  dentro del contenedor HA local sobre la CPU del M1, sin crear ni emparejar un
  worker. Encadena tres identidades de trabajo —reconstrucción, ML v0 y V2–V6—
  desde snapshots inmutables y realiza una única promoción del conjunto al
  final. Un fallo conserva la generación anterior y limpia el staging local.
- El camino ordinario de producción no cambia: el HA de la RPi4 coordina y el
  worker M1 ejecuta los mismos tres contratos. La UI y el backend no permiten
  promocionar la generación completa hasta que el V2–V6 enlazado haya terminado.
- La regeneración real por el ejecutor HA local terminó correctamente en
  18m45s. Encadenó las tres fases y activó una sola generación completa; el
  batch V2–V6 instalado es `local_v2_v6_20260817T171541Z`. La promoción local
  es automática al final de la cadena, no existe un botón posterior.
- Después de esa prueba se añadió progreso real dentro del tramo V2–V6 usando
  los contadores por fit que ya emite el trainer. El 58–90% muestra fits
  completados/planificados, versión, especie, éxitos y fallos; no simula tiempo.
- La preparación dinámica ya emitía ocho hitos y el worker remoto los publicaba,
  pero el ejecutor `Home Assistant local` los descartaba al lanzar el preparador
  sin `--progress-jsonl`. El camino local queda conectado al mismo JSONL: el
  50–58% informa paso y fase de V3/V4/V5/V6. Además reenvía los eventos internos
  ya disponibles: microáreas, cortes de área, comparación/dataset y split V6,
  aunque varios de esos eventos compartan porcentaje global. Los porcentajes
  representan fases y unidades terminadas, no una estimación de tiempo
  transcurrido o restante.
- La primera reconstrucción posterior al cambio V5/V6 v2 falló a los 23m12s y
  86%: el registro persistente del laboratorio aún declaraba V5/V6 v1 mientras
  el runtime solo materializaba v2. No hubo promoción y el descriptor anterior
  `local_v2_v6_20260817T171541Z` permaneció intacto. En este laboratorio de una
  sola instalación se alineó `docker-data` con los contratos v2. El runtime
  valida ahora la cobertura completa del plan antes de ajustar modelos y el
  ejecutor HA local hace esa prevalidación antes de iniciar la reconstrucción.
  En arranques posteriores, `ensure_seeded()` actualiza las definiciones de
  contrato desde la imagen conservando estados, historial y generaciones; una
  futura revisión contractual no requiere copiar el registro persistente a mano.
- La repetición posterior terminó y promocionó correctamente el batch
  `local_v2_v6_20260817T213901Z`, snapshot
  `sha256:c7e7b4f5e538604737bc4119c2acc7a4a7644c8f87b333d02caaee6bd8c369e3`.
  El manifiesto instalado valida contra el registro v2, contiene 487 artefactos
  de 868 fits planificados y conserva 381 fits fallidos: 378 por especies con
  una sola clase entrenable y tres por no convergencia sparse-group. Edulis
  dispone de ambos contratos en V2–V6; V5 usa
  `raw_primary_plus_physical_state` y V6 `smooth_weather_physical_state`.
  `runtime-batch.json`, catálogo de calidad y manifiesto de entradas quedaron
  instalados; `.local-full-update` quedó vacío.
- El desglose posterior corrigió una interpretación inicial: nueve especies
  aportan artefactos por especie, no tres. Siete especies con solo 1–4 filas
  elegibles, todas favorables, entraron indebidamente porque V2–V6 usaba la
  selección general de la UI en vez de `trained_species`; sus 54 fits por
  especie explican los 378 rechazos. La planificación queda corregida para usar
  solo especies con al menos diez filas y ambas clases. Las tres no
  convergencias restantes son únicamente V5 lag sparse-group de Amanita
  caesarea, Boletus aereus y Lactarius deliciosus; sus demás artefactos existen.
- El Predictor resume antes del detalle cuatro niveles: utilizables en dominio
  que mejoran prevalencia, evidencia débil, extrapolaciones/no utilizables y
  abstenciones meteorológicas. Para la consulta Edulis/Salteguet/2026-08-20 se
  verificaron 11/7/55/72 miembros respectivamente. Los 72 no son fallos de
  modelos: h1–h3 requieren cortes meteorológicos 17–19 de agosto aún incompletos
  en la copia local; h7 dispone de 21/21 días. El texto técnico
  `runtime_feature_gates_failed` ya no se muestra y el detalle queda plegado.
- La imagen local final está reconstruida y el contenedor canónico está mapeado
  en `8101`. El smoke final pasó 863 pruebas; compilación Python/JS/shell,
  fixtures y `git diff --check` pasaron. La auditoría confirmó cero modelos
  entrenados y cero datasets generados en las imágenes; HA solo lleva una
  plantilla de observaciones vacía. No se publicó ni versionó nada.
- El batch `local_v2_v6_20260817T171541Z` está `current/inputs_match`; su
  manifiesto coincide con el SHA-256 registrado
  `53cdbf1dda9ea2d9e56ed155737c79f6047ff38ede36a2f5ab44de580d92de8f`,
  declara `operational_candidate_trained=false`, no referencia el snapshot
  antiguo y dejó vacío `docker-data/.local-full-update`.
- Sus 244 artefactos `lag_event` tienen horizontes `[1,2,3,7]`, sin claves
  duplicadas por versión, especie, contrato, perfil y estimador.

## P0 cerrado localmente — detenerse antes de release

1. La fila «Ventana ciega fija de 7 días» pertenecía al comparador legado
   `MushroomModelComparator`, alimentado por
   `nearest_station_single_source_daily`; no era el miembro V2 `common_idw` del
   batch. Sus 18 episodios frente a 20 procedían de dos huecos de la estación
   única; el IDW común recupera ambos. La tarjeta resuelve ahora exclusivamente
   los artefactos V2 instalados del batch y no degrada al comparador legado.
2. MapLibre contaba soporte de lluvia por valor truthy y descartaba `0.0`; N/A
   sí debe excluirse. La corrección cuenta ceros finitos con su peso IDW y
   mantiene N/A fuera. La prueba de regresión está en `tests/test_maplibre_idw.py`.
3. V5/V6 anteriores no cumplían la intención de «todas las variables». Los
   contratos v2 materializan por microárea estaciones habilitadas → IDW → ET0,
   balance y SMI → agregado de área. V5 usa ocho canales diarios y estados
   escalares; V6 suaviza los ocho y conserva los escalares. El Predictor usa la
   misma ruta y el runtime remoto empaqueta `stations.txt` para conservar las
   fuentes habilitadas.
4. Validación: 54 pruebas dirigidas, suite completa 871/871, smoke completo y
   `git diff --check` verdes. Una construcción real desechable materializó V5
   v2 para 593 área/corte (395 muestras fixed y 1.580 lag); se detuvo la
   reevaluación exhaustiva posterior para no gastar CPU/tokens innecesarios.
5. Próximo paso: detenerse e informar. Preparar o publicar una release requiere
   autorización explícita nueva.

La secuencia de entrega acordada separa riesgos:

1. Primera entrega urgente HA+worker: corrección V2–V6, manifiesto, promoción
   completa, limpieza, resumen del Predictor y progreso del ejecutor local.
2. Release posterior solo del worker: multicoordinador completo, probado antes
   con dos HAs locales aislados.
3. Release HA posterior únicamente si hace falta añadir la protección `409`
   durante una revocación con job activo. El resto del worker multicoordinador
   debe conservar compatibilidad con el HA publicado en el primer paso.

## Evolución acordada, todavía no implementada

- El worker externo evolucionará de una única URL/token a varias asociaciones
  de coordinador independientes. Esto permitirá que el mismo M1 permanezca
  emparejado con el HA real y el HA local sin sustituir la URL existente ni
  crear un worker temporal.
- Seguirá existiendo un único `worker_id`, volumen, caché y slot global de
  ejecución. Los heartbeats serán independientes y los claims se arbitrarán de
  forma justa; cada job y sus resultados permanecerán ligados al coordinador
  de origen.
- El máximo se persistirá como parámetro configurable `max_coordinators`, con
  default 4; no será una constante rígida. Revocar desde un HA eliminará su
  credencial server-side y el worker purgará solo esa asociación al recibir un
  `401` inequívoco en el ciclo siguiente. Fallos de red o `5xx` no borrarán
  credenciales.
- El diseño completo y sus pruebas de aceptación están en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`. No está
  implementado en worker `1.0.10` y no autoriza cambios en el M1 o HA reales.

## Investigación ML ya cerrada para este gate

- V5 conserva 12.280 predicciones hold-out fila a fila y el análisis de falsos
  positivos/negativos compartidos. Gana 2 y pierde 32 de 34 comparaciones contra
  el mejor miembro V2/V3/V4. No respalda dos ventanas meteorológicas estables ni
  un estado temporal; queda experimental.
- V6 probó curvas suaves por especie, una curva compartida y pooling parcial.
  Gana 4 y pierde 30 de 34 contra el mejor V2/V3/V4/V5. No justifica ahora un
  jerárquico general ni cambiar el Predictor.
- No añadir otra familia ni un ensemble en este gate. Un ensemble futuro debe
  superar al mejor miembro individual por especie y contrato. Nunca usar Brier
  medio entre especies.
- Informes vigentes:
  - `docs/reports/V2_V3_V4_V5_raw_weather_report001.md`;
  - `docs/reports/V2_V3_V4_V5_V6_smooth_hierarchical_report001.md`;
  - `docs/reports/V2_V3_V4_consensus_report002.md`.

## Riesgos y dudas activos

- El Predictor local dejó de repetir la validación del manifiesto de 487
  artefactos y la carga de bundles dentro de una misma petición. La consulta de
  referencia medida bajó de 116,011 s en caliente a 13,185 s; el cambio al día
  siguiente dentro del mismo proceso tardó 12,435 s. El smoke completo pasó
  881 pruebas y `git diff --check` quedó limpio. La imagen HA local se
  reconstruyó después sin tocar HA real ni el worker normal: el endpoint en
  `127.0.0.1:8101` devolvió `200`, con 22,992 s para 2026-08-18 y 16,184 s para
  2026-08-19 ya en caliente; los logs no mostraron errores de aplicación.
- La pestaña «Por especie» reveló primero un `UnboundLocalError`: `_render_week`
  conservaba una referencia copiada a la variable `area`, inexistente en esa
  vista. Tras retirarla, la cuadrícula aún tardaba unos siete minutos porque
  reconstruía 14 ventanas solapadas por área. El runtime prepara ahora una sola
  serie IDW de 96 días por área y corta de ella las 8 fechas de corte únicas de
  la semana. En el HA local reconstruido, Edulis devolvió tabla HTTP `200` de
  349.019 bytes en 26,013 s, sin la excepción. El smoke posterior pasó 883
  pruebas y `git diff --check` quedó limpio.
- La ventana runtime queda ligada al contrato: V2/V3 actuales 90 días IDW sin
  estado físico; V4 90 días y físicos solo en perfiles que los declaran; V5/V6
  mantienen 365 días mediante la constante canónica
  `mushroom_ml_raw_weather.LOOKBACK_DAYS`. No se ha retirado balance/SMI de
  V2/V3 como posibilidad: queda preservada y probada la activación por un futuro
  perfil explícito `IDW + estado físico`, que deberá entrenarse y compararse
  separadamente.
- Los resultados actuales no autorizan concluir que 365 días «no sirven».
  V5/V6-365 queda intacto como control reproducible; queda pendiente un nuevo
  V5/V6-90 emparejado sobre las mismas filas y splits para medir específicamente
  la aportación de los días 91–365.

- [CERRADA] El falso vacío MapLibre descartaba ceros finitos al contar soporte;
  N/A se excluye y no propaga `NaN`.
- [CERRADA] `model_not_trained` pertenecía al bundle legado de estación única,
  con 18 episodios elegibles; el batch V2 común IDW es otro artefacto.
- La instalación real sigue sin la corrección V2–V6. No afirmar que su Predictor
  incorpora toda la información disponible.
- Los batches anteriores no tienen identidad de entrenamiento; su vigencia debe
  mostrarse como no verificable, no asumirse actual.
- La prueba larga puede rondar 20 minutos y el coste crecerá mientras V2–V6
  sigan activas. Reducir versiones en el futuro reducirá el coste.
- El soporte por especie/campaña sigue siendo pequeño. V5/V6 y cualquier ranking
  son diagnósticos, no promoción ni causalidad.
- El worktree mezcla muchos bloques. Revisar el alcance antes de commit/release
  y preservar los PDF científicos no rastreados.
- La imagen ya no copia observaciones, pero el repositorio público sigue
  rastreando `mushroom-data/mushroom_observations.json` con datos semilla. No se
  modificó en esta sesión. Revisar privacidad por separado antes de asumir que
  el repositorio completo carece de observaciones.
- La autocuración meteorológica y la reparación histórica amplia siguen sin una
  validación de producción independiente de esta corrección multiversión.

## Archivos relevantes

- Continuidad: `docs/codex-start-here.md`, este documento y `docs/todo.md`.
- Decisiones y arquitectura: `docs/decisions.md`, `docs/architecture.md`.
- Runtime: `rainmapper-app/app/web_server.py`,
  `rainmapper_core/mushroom_worker_jobs.py`,
  `rainmapper_core/mushroom_worker_service.py` y
  `rainmapper_core/mushroom_worker_transport.py`.
- Snapshot/training: `rainmapper_core/mushroom_rebuild_snapshot.py`,
  `scripts/prepare-mushroom-ml-multiversion-inputs.py` y
  `scripts/run-mushroom-ml-multiversion-job.py`.
- Instalación/validación del batch:
  `rainmapper_core/mushroom_ml_model_catalog.py` y
  `rainmapper_core/mushroom_ml_multiversion_transport.py`.
- Vigencia/UI: `rainmapper_core/mushroom_ml_training_freshness.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py`,
  `mushroom-data/mushroom_labels.json`.
- Diagnóstico IDW: `rainmapper_core/viewers/maplibre-viewer/app.js`, funciones
  `estimatedFieldUsableFeatures`, `estimateFieldCellValue`,
  `estimatedFieldPointMetricValue` y `buildIdwPointValues`.
- Empaquetado: `rainmapper-app/Dockerfile`, `rainmapper-worker/Dockerfile` y
  `rainmapper-app/defaults/mushroom_observations.json`.
- Pruebas principales: `tests/test_mushroom_ml_training_freshness.py`,
  `tests/test_mushroom_ml_multiversion_transport.py`,
  `tests/test_mushroom_worker_jobs.py`,
  `tests/test_mushroom_worker_transport.py` y
  `tests/test_mushroom_worker_packaging.py`.

## Reglas para continuar

- Leer primero `docs/codex-start-here.md` y este documento; `docs/todo.md` solo
  si hacen falta prioridades completas.
- Comprobar `pwd`, rama y `git status`; preservar todos los cambios y no usar
  comandos destructivos.
- Consultar Codebase Memory MCP antes de descubrir o cambiar código.
- Responder siempre a los mensajes del usuario mientras se trabaja.
- Codex no usa Tailscale. No cambiar la URL Tailscale persistida del worker real
  sin orden explícita.
- No tocar HA real, worker normal, GHCR ni releases durante la prueba local.
- Tras superar el gate local, detenerse e informar. Preparar o publicar releases
  exige una nueva autorización explícita del usuario y seguir
  `docs/release-flow.md`.
