# Codex: empezar aquí

**Restricción expresa del usuario: no acceder por SSH a la RPi4 sin petición
explícita, tampoco para consultas. El 18/09 autorizó SSH para la migración de
media, su verificación y la retirada de duplicados GIS comprobados. Esta excepción
no autoriza otras operaciones. Parar, instalar y arrancar Rainmapper en HA real
sigue a cargo del usuario.**

Este documento contiene el mapa estable del proyecto y las reglas de continuidad.
El estado operativo está exclusivamente en [active-context.md](active-context.md).

## Arranque de una sesión

1. Leer este documento y [active-context.md](active-context.md).
2. Consultar [todo.md](todo.md) solo para ampliar los próximos bloques.
3. Revalidar los archivos, contenedores y huellas pertinentes antes de afirmar
   su estado actual. Los informes anteriores acreditan la revisión indicada,
   no el estado de otra imagen o de HA real después de una subida manual.
4. Consultar anexos técnicos únicamente cuando lo requiera la tarea elegida.
   Un pendiente no autoriza ejecutarlo; consultar el estado y alcance vigente
   de GIS y releases en `active-context.md`.

## Qué es el proyecto

Rainmapper combina mapas meteorológicos y predicción de fructificación de setas.
El mapa calcula por coordenadas; el Predictor trabaja con áreas y artefactos
entrenados/precalculados. La presentación IFF no garantiza presencia de setas.
HA coordina datos y trabajos; el worker ejecuta cálculo remoto. Sus versiones
son independientes y sus asociaciones deben conservarse.

Las decisiones científicas y sus límites se registran en
[decisions.md](decisions.md). No inferir suelo medido a partir de litología ni
convertir una clasificación inventariada en una revisión bibliográfica terminada.

## Mapa documental

- **Mapa de predicción — especificación central y punto de entrada al diseño:**
  [prediction-map-specification-es.md](mushrooms/prediction-map-specification-es.md).
  Reúne objetivo, componentes, visor, permisos, datos, HA–worker, integración,
  pruebas y decisiones abiertas. Los siguientes documentos del mapa son anexos
  técnicos, evidencia o seguimiento; no sustituyen esta referencia principal.
- GIS/DEM/SoilGrids, consumidores, copias locales y cálculo HA–worker:
  `docs/mushrooms/mushroom-map-compute-data-placement-es.md`
- SoilGrids, diseño del lector compartido, altas/cambios y pruebas de recursos:
  `docs/mushrooms/mushroom-prediction-map-soilgrids-reader-design-es.md`
- SoilGrids, cobertura aceptada y condiciones de lectura en RPi4:
  `docs/mushrooms/mushroom-prediction-map-soilgrids-coverage-es.md`
- SoilGrids, alcance nacional y migración controlada:
  `docs/mushrooms/mushroom-prediction-map-soilgrids-plan-es.md`
- Estado hídrico compartido, decisión aceptada, consumidores y migración:
  `docs/mushrooms/SMI/adoption-2026-09-20/README.md`.
  Extracción regulada + Penman–Monteith + una capa; historial independiente de
  ventanas. Simple sólo visual. Auditorías en `docs/mushrooms/SMI/README.md`;
  no convertir fuentes externas de contraste en dependencias operativas.
- Suspensiones en JSON independiente y transferencia entre instalaciones:
  `docs/mushrooms/model-suspensions-es.md`.

- Mapa de predicción, pasos completados y pendientes:
  `docs/mushrooms/mushroom-prediction-map-progress-es.md`
- Mapa de predicción: nuevo informe por coordenadas, complementario al Predictor;
  análisis sin implementación:
  `docs/mushrooms/mushroom-map-point-prediction-feasibility-es.md`
- Fuentes descargadas para ese módulo, separadas en `mushroom-map-GIS/` con
  README junto a los archivos: `docs/mushrooms/mushroom-map-gis-downloads-es.md`
- Auditoría documental con referencias al código: `docs/reports/documentation-audit-2026-09-18.md`.
- Investigación local de estaciones WU: `docs/station-research-es.md`.
- Media, compatibilidad de rutas y migración explícita: `docs/mushrooms/ha-media-organization-proposal-es.md`.
- Release HA: `docs/release-flow.md`
- Arquitectura y entrypoints: `docs/architecture.md`
- Decisiones: `docs/decisions.md`
- Seguridad de históricos: `docs/history-safety.md`
- Caja negra y procedimiento RPi4: `docs/runtime-diagnostics.md`
- Diseño Predictor: `docs/mushrooms/mushroom-predictor-design-es.md`
- Predictor remoto/worker: `docs/mushrooms/mushroom-remote-predictor-design-es.md`
- Selección durante entrenamiento del candidato más fiable por
  especie/área/día:
  `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`
- Revisión exploratoria de Sporas.io, límites de sus datos visibles y conceptos
  pendientes para Rainmapper:
  `docs/mushrooms/literature/sporas_especies_informe_rainmapper.md`
- Auditoría P0 hídrica multiespecie y multiversión:
  `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`
- Revisión y diseño experimental de la variable de racha seca:
  `docs/mushrooms/literature/prediction/rainmapper_dry_spell_variable_review.md`
- Pruebas aplazadas y batería Python reproducible:
  `docs/reports/mushroom-predictor-p0-pending-tests-and-python-audit-battery-2026-09-05.md`
- Pantalla futura de auditoría del selector:
  `docs/mushrooms/mushroom-predictor-reliability-screen-spec-es.md`
- Optimización acordada del camino frío del Predictor, caché semántica,
  workspace meteorológico común e inferencia por lotes:
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`
- Precálculo semanal distribuido de todas las especies, áreas y versiones,
  persistido en SQLite en HA y worker con fallback al Predictor vigente:
  `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`
- Entrega local sellada entre trabajos encadenados del worker:
  `docs/mushrooms/mushroom-worker-chained-job-local-handoff-spec-es.md`
- Alcance y plan operativo únicos para local, HA y worker:
  `docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`
- Plataforma de workers: `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
- Diseño vigente del worker multicoordinador y administración CLI pendiente:
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`
- Auditoría y propuestas de transferencias HA--worker:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.
  Recepción de precálculo por bloques y validación secuencial ya implementadas;
  evidencia y límites: `docs/reports/ha-memory-precompute-2026-09-22.md`.
  El resto del alcance de aquel documento no se presume implementado.
- Consenso reversible y reservas por falta de datos: reglas vigentes en
  `docs/decisions.md` (22/09); implementación en
  `rainmapper_core/mushroom_recommendation_policy.py`. Estado del despliegue y
  modo local/real exclusivamente en `docs/active-context.md`.
- Entrenamiento ML/dataset: `docs/mushrooms/mushroom-ml-training-plan-es.md`
- Versiones canónicas de contratos ML:
  `docs/mushrooms/mushroom-ml-contract-versions-es.md`
- Ciclo de vida persistente y comparación de versiones ML:
  `docs/mushrooms/mushroom-ml-version-lifecycle-es.md`
- Runtime HA/worker y Predictor V2–V6:
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`
- Retención permanente, caché TAR fuera de backups y limpieza segura de
  modelos/artefactos del worker:
  `docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`
- Separación propuesta entre entrenamiento operativo, benchmark, informe y
  promoción:
  `docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`
- Contrato genérico para perfiles actuales/futuros, candidatas, promoción y
  rollback:
  `docs/mushrooms/mushroom-ml-generic-profile-promotion-plan-es.md`
- Varias versiones ML instaladas a la vez, selector derivado del registro y
  preferida independiente, desplegado en HA `0.2.266`:
  `docs/mushrooms/mushroom-ml-multi-version-installation-design-es.md`
- Auditoría ML v3: `docs/mushrooms/mushroom-ml-v3-data-audit-es.md`
- Especificación ML v3: `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`
- Especificación Biology V4, en implementación local por fases:
  `docs/mushrooms/mushroom-ml-biology-v4-implementation-spec-es.md`
- Contrato técnico de caché SoilGrids y persistencia por microárea para V4:
  `docs/mushrooms/biology-v4-soilgrids-cache-contract-es.md`
- Autocura SoilGrids, fase persistente previa al snapshot y degradación
  best-effort por microárea:
  `docs/mushrooms/mushroom-soilgrids-autocure-spec-es.md`
- Progreso por puntos de Biology V4:
  `docs/mushrooms/mushroom-ml-biology-v4-progress-es.md`. Es histórico técnico;
  la elegibilidad y el runtime vigentes se consultan en el registro y en
  `docs/active-context.md`, no se infieren de ese informe de progreso.
- Informe interpretativo y revisión meteorológica de V4:
  `docs/reports/V4_report001.md`.
- Informe canónico de comparación y consenso V2/V3/V4:
  `docs/reports/V2_V3_V4_consensus_report002.md`. El informe 001 queda
  histórico y no debe guiar decisiones.
- V5 raw y análisis de errores:
  `docs/reports/V2_V3_V4_V5_raw_weather_report001.md`.
- V6 suave y jerárquica:
  `docs/reports/V2_V3_V4_V5_V6_smooth_hierarchical_report001.md`.
- Auditoría científica P0 de la señal hídrica, multiespecie y multiversión,
  incluidos los ganadores operativos V2--V6 y las ablaciones por retardos:
  `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.
- Backfill histórico y promoción:
  `docs/mushrooms/mushroom-weather-historical-backfill-handoff-es.md`
- Almacenamiento y retención meteorológica:
  `docs/weather-storage-retention-plan-es.md`
- Implementación del histórico meteorológico particionado:
  `docs/weather-history-partitioned-implementation-spec-es.md`
- Auditoría de reparación, compactación y corrección de la generación raíz del
  histórico meteorológico:
  `docs/reports/mushroom-weather-history-repair-audit-2026-08-23.md`
- Narrador LLM local opcional:
  `docs/mushrooms/mushroom-worker-local-llm-narrator-design-es.md`
- Contrato perfiles: `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`
- Investigación GBIF, visor local y revisión manual pendiente del usuario:
  `local-apps/gbif/docs/guide.md`. No importar ni entrenar automáticamente.
- Observaciones/schema: `docs/mushrooms/mushroom-observations-schema-es.md`
- GIS: `docs/mushrooms/gis-layer-inventory-es.md`
- Fuentes y GIS para la expansión Font-Romeu--Quérigut:
  `docs/mushrooms/france-sources/`
- Labels: `docs/mushrooms/mushroom-labels-reference-es.md`
- UI de parámetros: `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`
- UI de observaciones: `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`

## Reglas operativas críticas

- Informar brevemente al usuario aproximadamente cada minuto durante cualquier
  trabajo en curso; esta preferencia también se aplica fuera de los builds.

- Conservar la cuota de tokens del usuario: las actualizaciones de proceso deben
  ser mínimas y limitarse a estado, resultado o bloqueo. No narrar pasos obvios,
  repetir contexto ni volcar salidas extensas de comandos; resumirlas y mostrar
  solo la evidencia necesaria. Ampliar detalles únicamente cuando el usuario
  los pida o sean imprescindibles para decidir o diagnosticar.
- Una tarea explícitamente encargada autoriza sus ediciones, consultas,
  pruebas, empaquetado y demás pasos no destructivos dentro del alcance. No
  pedir confirmación adicional por acciones inocuas, tampoco durante una
  release ya autorizada. Consultar el MCP Codebase es siempre lectura y no
  requiere permiso. Consultar únicamente antes de una acción destructiva, una
  escritura en HA que no esté expresamente autorizada o una ampliación material
  del alcance; ante una duda real sobre cualquiera de esos tres casos, preguntar.
- No hacer bump, build ni publicación HA sin petición explícita. Antes de una
  release, leer y seguir `docs/release-flow.md`.
- Todo cambio ejecutable destinado a HA real debe probarse primero construyendo
  HA local y el worker desde el mismo source antes de una release, según
  `release-flow.md`. La prueba debe recorrer el circuito funcional afectado; compilar por sí solo no
  constituye validación. Solo después de la aceptación se publica o instala HA
  real.
- Entrenamiento y precálculo sólo son obligatorios si el cambio afecta a esos
  procesos o a sus entradas, contratos operativos o artefactos. UI, permisos y
  mensajes se validan con pruebas dirigidas, navegador y smoke, sin imponer
  trabajos operativos ajenos al cambio. Regla general acordada el 24/09/2026;
  ver `release-flow.md`. El usuario sigue lanzando los trabajos necesarios.
- Durante un build/push HA, vigilar la misma sesión cada 20–30 s e informar al
  usuario al menos cada minuto; no duplicar builds. Verificar tags, digest y
  manifests antes de cancelar un cliente que tarde en cerrar.
- HA y worker tienen versiones independientes. Compatibilidad significa
  capacidades y contratos, no números iguales.
- No borrar `docker-data/`, `tmp/`, `mushroom-GIS/`, backups, históricos,
  artefactos o imágenes sin autorización explícita.
- El usuario se reserva el lanzamiento del precálculo. No deducir permiso para
  lanzarlo de una solicitud de release, diagnóstico o cierre. No crear otro
  worker, volumen o imagen auxiliar para pruebas; utilizar servicios existentes
  sólo dentro del alcance autorizado, sin modificar sus coordinadores.
- Codex no debe usar Tailscale ni abrir SMB mediante Tailscale. Esta restricción
  no autoriza a retirar la URL Tailscale persistida que el worker real necesita
  cuando opera fuera de la red local.
- No tocar CSV meteorológicos reales sin `docs/history-safety.md`.
- No inventar features, umbrales, pesos, ventanas o reglas micológicas.
- HA real corre en una Raspberry Pi 4 compartida. No usar fuerza bruta,
  expansiones cartesianas, validaciones repetidas, copias grandes ni aumentos de
  límites como sustituto de un diseño eficiente.
- Todo texto visible nuevo de setas debe existir en
  `mushroom-data/mushroom_labels.json` en inglés, español y catalán.
- Evitar ampliar `web_server.py` con dominio nuevo: preferir `rainmapper_core`
  y módulos UI especializados.
- Usar `.venv/bin/python` (Python 3.11) para desarrollo y validación local.
- Preservar el contexto de navegación y no crear versiones divergentes de un
  modal según su origen.
- No limpiar GHCR sin confirmar la versión activa ni crear copias, imágenes de
  reserva o mecanismos de reversión no solicitados. Conservar únicamente los
  manifests/attestations multi-arquitectura necesarios para las versiones que
  el usuario haya decidido mantener.

## Fuentes de verdad y rutas sensibles

- Setas en HA real: `/share/rainmapper/mushroom-data/`.
- Copia local de pruebas: `docker-data/mushroom-data/`; nunca sobrescribir HA
  desde ella sin una sincronización explícita y verificada.
- GIS/DEM pesado en HA: seguir las rutas/manifiestos de la consolidación geográfica
  descrita en `docs/mushrooms/shared-geography-consolidation-es.md`; no moverlo a `/share`
  porque inflaría backups.
- Media de observaciones:
  `/share/rainmapper/mushroom-data/media/observation-photos/`.
- Resolver canónico: `rainmapper_core/mushroom_paths.py`.
- Geografía local canónica organizada: `docker-media/rainmapper/geography/`.
  Las carpetas GIS raíz conservan descargas/pruebas/fuentes aún no integradas;
  no asumir duplicación por nombre. Ver manifiestos y consumidores antes de mover.
- Visores locales: `local-apps/{wunderground,gbif}/code/`; sus datos/fotos/revisiones
  en `data/`, fuera de Git e imágenes. No volver a alojarlos en docs o tmp.
- `tmp/mushroom-lab/` es laboratorio, no fuente operativa.

## Validación habitual

```bash
PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Para un cambio acotado pueden ejecutarse primero tests dirigidos, pero una
release requiere el flujo y validación completa definidos en
`docs/release-flow.md`.

La validación debe ser proporcional al cambio y no un ritual repetido:

- cambios solo documentales: revisión del diff y `git diff --check`;
- código acotado: pruebas dirigidas de los símbolos y contratos afectados;
- cambios transversales, de empaquetado o de alto riesgo: ampliar a la suite
  pertinente y, cuando corresponda, al smoke completo;
- release: un smoke completo sobre el código definitivo antes del bump; después
  del bump mecánico verificar únicamente versiones y cache-busters, salvo que se
  haya modificado código desde el smoke.

No repetir secuencias `smoke → commit/push → documentación → smoke → commit/push`
si los pasos intermedios no cambian código ni artefactos ejecutables. Documentar
el resultado ya obtenido y ejecutar de nuevo solo las comprobaciones que puedan
haber quedado invalidadas.

## Mantenimiento de continuidad

- Actualizar este documento solo si cambia el mapa general, las reglas o la
  arquitectura de alto nivel.
- Sustituir contexto obsoleto en `active-context.md`; no acumular sesiones.
  Mantener allí toda decisión necesaria para el siguiente paso: no exigir leer
  un tercer relevo para reconstruir instrucciones. Archivos y anexos son detalle opcional.
- Registrar decisiones con `[VIGENTE]`, `[REEMPLAZADA]`, `[OBSOLETA]` o `[DUDA]`.
- Mover historia útil fuera de la ventana activa.
- La compactación de continuidad **no puede resumir hasta perder** una decisión
  operativa o científica. `active-context.md` puede conservar solo el estado y
  el enlace, pero `docs/decisions.md` y la especificación temática deben
  mantener fórmula/semántica, alternativas descartadas, motivo, evidencia,
  cifras de validación y condiciones para revisarla en el futuro.
- La genealogía de contratos ML se preserva en
  `docs/mushrooms/mushroom-ml-contract-versions-es.md`: nunca deducir V1/V2/V3
  únicamente del código ni eliminar versiones anteriores al compactar.
