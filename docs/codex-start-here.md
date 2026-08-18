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

## Estado general al cierre de 2026-08-17

- Rama activa: `inicial`; el worktree grande y mixto es deliberado. Preservar
  todos los cambios y ficheros no rastreados.
- El usuario mostró HA `0.2.256` y worker M1 `1.0.10` instalados y emparejados.
  La regeneración real completó reconstrucción y ML v0, pero V2–V6 falló porque
  dependía de un JSON del laboratorio ausente en HA.
- La corrección local deriva V2–V6 del snapshot fresco de cada job, conserva una
  identidad de entrenamiento verificable y avisa en el Predictor cuando los
  modelos no incorporan las entradas actuales.
- El worker temporal `Validación local` fue retirado. El worker M1 normal sigue
  emparejado con el HA real y no se cambia de coordinador para probar en local.
  El HA local canónico usa `8101` y dispone de un ejecutor opt-in dentro de su
  propio contenedor: encadena reconstrucción, ML v0 y V2–V6 y promociona una
  sola vez al final. La prueba larga terminó en 18m45s y el smoke final pasó
  863 pruebas.
- Los dos diagnósticos P0 quedaron cerrados localmente: la fila fija procedía
  del comparador legado de estación única, no del V2 del batch, y MapLibre
  descartaba indebidamente ceros al contar soporte IDW. La tarjeta V2 resuelve
  ahora el batch común IDW; V5/V6 v2 consumen IDW, ET0, balance y SMI con paridad
  de inferencia. Preparar releases exige una nueva autorización explícita; no
  tocar HA/worker reales mientras tanto.
- V2–V6 tienen el mismo estatus experimental. V2 aparece primero solo por
  cronología. V5 pierde 32/34 y V6 30/34 frente al mejor miembro anterior; no se
  añade otra familia ni ensemble durante este gate.
- El snapshot `mushroom-ml-snapshot-20260816` sigue siendo evidencia científica
  inmutable, pero ya no es una dependencia de una regeneración operativa.
- El repositorio GitHub sigue público. Las imágenes no incluyen observaciones,
  aunque el fichero semilla rastreado debe revisarse por privacidad aparte.

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
- Auditoría ML v3: `docs/mushrooms/mushroom-ml-v3-data-audit-es.md`
- Especificación ML v3: `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`
- Especificación Biology V4, en implementación local por fases:
  `docs/mushrooms/mushroom-ml-biology-v4-implementation-spec-es.md`
- Contrato técnico de caché SoilGrids y persistencia por microárea para V4:
  `docs/mushrooms/biology-v4-soilgrids-cache-contract-es.md`
- Progreso por puntos de Biology V4:
  `docs/mushrooms/mushroom-ml-biology-v4-progress-es.md`. Los puntos 1
  (contexto SoilGrids), 2 (balance climático diario), 3 (depósito experimental
  por microárea) y 4 (registro y benchmarks por bloques) están implementados
  en local. Las evaluaciones emparejadas de 7/14 días y la comparación genérica
  V2/V3/V4 sobre filas idénticas ya están cerradas e interpretadas por especie;
  continuidad `fixed_gap` y `lag_event` ya tienen secuencias reales
  `core`/balance/suelo. El balance reduce parpadeo global; el depósito no mejora
  y queda no seleccionado. No hay soporte para aprender aún una capa de estado;
  la paridad local train/inferencia pasa sin diferencias y solo falta validar
  el empaquetado/runtime cuando se autorice integrar. HA y M1 no ejecutan este
  código todavía; la única excepción de datos es el `known_sites` derivado que
  se instaló en HA de forma autorizada y respaldada.
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
