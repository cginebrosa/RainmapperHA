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

## Estado general al cierre de 2026-08-27

- Rama activa `inicial`, entrega principal `4b6422d`; preservar siempre el
  worktree y cualquier fichero no rastreado. HA real continúa en `0.2.266`; la imagen `0.2.267` está publicada
  pero no instalada. El worker normal es `1.0.18` y conserva la identidad emparejada
  `worker_1a9a232c20fe2ee2`. Revalidar el runtime al comenzar una sesión nueva.
- La separación entre mantenimiento operativo y benchmark científico está
  desplegada. El mantenimiento completo verifica y autopromociona
  conjuntamente una generación por cada versión instalada seleccionada; el
  benchmark conserva evidencia e historial pero no prepara, activa ni revierte
  versiones.
- El selector de mantenimiento se deriva del registro activo, no de una lista
  hardcoded. Admite cualquier subconjunto instalado de V2/V3/V4/V5w/V6w y
  conserva la selección durante rebuild, ML v0, entrenamiento multiversión y
  promoción. `preferred_version_id` sigue siendo independiente.
- El reentreno local y el real terminaron con las cinco versiones. En HA real,
  el batch `operational_20260825T221049Z` produjo 636/636 ajustes, cero fallos y
  fue promocionado. Solo queda registrar la comprobación visual final de las
  cinco opciones y la desaparición del aviso de identidad desconocida.
- La retención ML está activa en HA real por decisión del usuario. El log
  observado fue `mode=apply removed=74 errors=0`; Predictor y reentreno
  funcionaron después. La caché TAR vive bajo `/media`, fuera de `/share` y de
  los backups. No cambiar la opción ni hacer borrados manuales.
- El siguiente bloque prioritario es rendimiento: la cadena remota real tardó
  ~37 minutos aunque los fits ocuparon ~2–3. Están confirmados uploads por
  fichero, `fsync` repetidos, reescritura de una cola de 5,39 MB en cada tick,
  rehashes redundantes y preparación sin telemetría suficiente. En laboratorio,
  telemetría, tuning operativo congelado y workspace meteorológico compartido
  redujeron el flujo completo a 8 min 55 s frío y 7 min 54 s caliente, con
  714/714 fits, cero fallos, equivalencia y promoción verificada.
- El objetivo local de <=10 minutos ya se cumple sin C ni paralelismo. Antes de
  compactar cola o agrupar transporte, medir el mismo código por el camino
  remoto HA↔worker después de una entrega autorizada; tocar esas capas solo si
  la medición lo justifica. El detalle está en `docs/todo.md` y en el informe
  `docs/reports/operational-rebuild-10m-lab-2026-08-26.md`.
- La vigencia futura se comprobará mediante revisiones pequeñas y avisos, no
  releyendo todo el histórico durante promociones o consultas. Worker y
  coordinador deben reutilizar objetos meteorológicos inmutables por digest y
  evitar copias/rehashes redundantes.
- V5/V6 operativas son las variantes windowed 30/60/90. Los 365 días se usan
  como calentamiento físico de balance/SMI, no como ventana predictiva. Las
  definiciones no-windowed legacy siguen como `reference` y queda pendiente su
  retirada definitiva tras auditar referencias.
- El selector operativo elige por separado ventana fija y retardo/evento. Solo
  entran candidatos aplicables, con Brier estrictamente mejor que prevalencia y
  ROC-AUC >= 0,55; después prioriza mayor mejora Brier, menor Brier y mayor
  ROC-AUC. La fiabilidad del ganador y el consenso entre familias metodológicas
  se muestran como ejes diferentes.
- La aplicabilidad vigente sigue usando una heurística no calibrada: rango
  mínimo/máximo aprendido por variable, `outside_feature_ratio >= 0,05` o una
  variable fuera de rango a `>= 3 sigma`. Esos dos umbrales están fijados por el
  código, no aprendidos. Deben auditarse antes de modificarlos.
- La validación debe ser proporcional: pruebas dirigidas por bloque y un smoke
  completo antes de una entrega relevante, no smoke repetido tras cada cambio
  documental, commit o bump.
- No preparar bump, build, publicación, instalación ni release sin autorización
  explícita nueva.
- El smoke transversal previo a las releases pasó 1.006 pruebas. `0.2.264` no
  migraba el registro persistente 1.0 y fue detenida; `0.2.265` añadió la
  migración validada con copia exacta previa; `0.2.266` añadió el selector
  dinámico de versiones y es la instalada actual confirmada por el usuario.
- El histórico meteorológico oficial de HA fue reparado y rebasado a una raíz
  autosuficiente; el runner manual posterior terminó correctamente. La próxima
  sesión debe tratar esta migración como cerrada y mantener como deuda la
  compactación del escritor y el coste del post-drain, no repetir el backfill.

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
- Plataforma de workers: `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
- Evolución pendiente del worker para conservar varios coordinadores:
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`
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
- Todo texto visible nuevo de setas debe existir en
  `mushroom-data/mushroom_labels.json` en inglés, español y catalán.
- Evitar ampliar `web_server.py` con dominio nuevo: preferir `rainmapper_core`
  y módulos UI especializados.
- Usar `.venv/bin/python` (Python 3.11) para desarrollo y validación local.
- Preservar el contexto de navegación y no crear versiones divergentes de un
  modal según su origen.
- No limpiar GHCR sin confirmar versión activa y rollback y sin conservar los
  manifests/attestations multi-arquitectura necesarios.

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
