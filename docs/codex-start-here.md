# Codex Start Here

Punto de entrada estable para una nueva sesión en RainmapperHA.

## Qué es el proyecto

RainmapperHA es una aplicación Python empaquetada como add-on de Home Assistant.
Ingiere históricos meteorológicos, genera mapas protegidos MapLibre y mantiene
el dominio micológico: observaciones y media, setales, GIS/DEM, reconstrucción de
artefactos, entrenamiento ML y Predictor de Floradas.

El cálculo pesado puede ejecutarse en HA o en workers externos emparejados. HA
conserva autoridad sobre usuarios, UI, jobs, datasets, promoción de artefactos,
resultados y Diagnostics; los workers son calculadoras sin UI pública.

## Arranque obligatorio

Trabajar únicamente en:

```text
/Users/carlosginebrosa/Developer/RainmapperHA
```

Antes de actuar:

```bash
pwd
git status --short
```

Leer siempre, en este orden:

1. `docs/codex-start-here.md`
2. `docs/active-context.md`
3. `docs/todo.md` solo si hacen falta prioridades más largas

`docs/active-context.md` es una ventana operativa, no un diario. El histórico
está en `docs/decisions.md`, `docs/project-archive.md` y los diseños temáticos.

## Estado general al 2026-09-09

- Rama `inicial`; la fuente declara HA `0.2.298`. GHCR `0.2.298` y `latest`
  comparten el índice multi-arquitectura
  `sha256:0c0bb47d532146c9cfed16f02de277c27c917207a5765c032c44b9933e0f2785`,
  con manifests `linux/amd64` y `linux/arm64`. HA local y el worker se
  reconstruyeron desde el código funcional definitivo y completaron el circuito
  de entrenamiento y precálculo antes del bump mecánico. HA real no se ha
  actualizado todavía a `0.2.298`.
- HA usa el último precálculo autocontenido durante una actualización, aunque
  esté marcado como desactualizado. Las tres vistas del Predictor leen una
  respuesta SQLite sellada e indexada y no reconstruyen ni revalidan cientos de
  componentes en cada consulta.
- El worker privado está healthy con la imagen local `rainmapper-worker:1.1.1`;
  no se distribuye mediante GHCR. Mantiene la URL principal
  autorizada `http://100.111.77.48:8100` y HA local como asociación adicional.
  No cambiar ninguna sin autorización expresa para ese destino.
- La candidata GIS francesa incorpora RGE ALTI 5 m para Font-Romeu y Quérigut.
  El TIFF operativo local tiene SHA-256
  `3e86d6c2ee4e3677dd895de369045b8f49c02a23902771692177b7a60256860f`;
  la copia montada en `/Volumes/media` se verificó con el mismo hash, tamaño,
  checksum y CRS EPSG:2154.
- La separación de cachés de runtime por coordinador está implementada,
  probada y ejercitada en el circuito local completo, con objetos físicos
  compartidos por SHA-256.
- También permanece modificado
  `mushroom-data/mushroom_observations.json`. Es del usuario: no editarlo,
  restaurarlo, borrarlo ni incluirlo ciegamente. Los datos vivos locales para
  pruebas están en `docker-data/mushroom-data/`.
- Se adoptó `knn_distance_beta_smoothed_v2` como único KNN de nuevos
  entrenamientos. El KNN anterior solo se conserva para leer generaciones
  históricas. `MOD_0001` sigue vigente: ecología y ventanas son diagnóstico y
  no modifican la predicción.
- El gate por especie para modelos con predicciones hold-out constantes está
  entrenado y aplicado: ninguna de las 280 selecciones selladas ni de los 420
  miembros del precálculo eligió una candidata constante.
- Las especies que entran por primera vez en el entrenamiento reciben
  decisiones V2--V4/V6 declaradas y seleccionan V5 únicamente con la partición
  de entrenamiento. El catálogo resultante se transporta, verifica, instala y
  reutiliza; los huecos parciales siguen fallando de forma cerrada.
- El worker ofrece un Explorador de modelos de solo lectura en `/models`
  (`http://127.0.0.1:8110/models` en local). Navegar selectores no abre bundles;
  el modelo elegido solo se carga al pedir la inspección y después de verificar
  su SHA-256. Todavía no existe enlace desde HA.
- Queda abierta una revisión de aplicabilidad a partir de Rovelló / Els Ports /
  2026-09-07: el modelo calculó `0,0016 %`, pero se abstuvo por humedad menos de
  un punto fuera del mínimo aprendido y temperatura máxima superior al rango.
  Solo está documentado; no se cambiaron reglas ni UI.
- No borrar datos o artefactos, crear copias o mecanismos de reversión ad hoc,
  cambiar retención, lanzar trabajos, hacer build/publicación ni tocar HA real
  sin autorización explícita.

El estado exacto, la prueba siguiente y los riesgos están en
`docs/active-context.md`.

## Mapa documental

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
- Auditoría y propuesta todavía no implementada para reducir copias, buffers y
  rehashes durante transferencias HA--worker sin debilitar integridad:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`
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
- Observaciones/schema: `docs/mushrooms/mushroom-observations-schema-es.md`
- GIS: `docs/mushrooms/gis-layer-inventory-es.md`
- Labels: `docs/mushrooms/mushroom-labels-reference-es.md`
- UI de parámetros: `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`
- UI de observaciones: `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`

## Reglas operativas críticas

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
  HA local y, si interviene cálculo remoto, el worker desde el mismo source. La
  prueba debe recorrer el circuito funcional afectado; compilar por sí solo no
  constituye validación. Solo después de la aceptación se publica o instala HA
  real.
- Durante un build/push HA, vigilar la misma sesión cada 20–30 s e informar al
  usuario al menos cada minuto; no duplicar builds. Verificar tags, digest y
  manifests antes de cancelar un cliente que tarde en cerrar.
- HA y worker tienen versiones independientes. Compatibilidad significa
  capacidades y contratos, no números iguales.
- No borrar `docker-data/`, `tmp/`, `mushroom-GIS/`, backups, históricos,
  artefactos o imágenes sin autorización explícita.
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
- GIS/DEM pesado en HA: `/media/rainmapper/mushroom-GIS/`; no moverlo a `/share`
  porque inflaría backups.
- Media de observaciones:
  `/share/rainmapper/mushroom-data/media/observation-photos/`.
- Resolver canónico: `rainmapper_core/mushroom_paths.py`.
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
