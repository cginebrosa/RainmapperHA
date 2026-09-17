# Contexto histórico anterior al cierre del 16/09/2026

Archivo documental: contiene estados reemplazados y contradicciones históricas.
No usar como estado operativo ni como autorización. El relevo vigente está en
[active-context](../active-context.md) y [start-here](../codex-start-here.md).

## Documento archivado: codex-start-here.md

# Codex Start Here

Punto de entrada estable para RainmapperHA. Leer completo este documento y
`active-context.md`; `todo.md` solo amplía prioridades.

Incremento actual: geografía portable, con archivos ordinarios compartidos en
`/media/rainmapper/geography`. **Sin comandos ni enlaces en el primer arranque.**
Validación local terminada: smoke 1600/48, código efectivo HA/worker comprobado,
cuatro puntos GIS idénticos, seis consultas con paridad y primer acceso con media
read-only. Copias en sus rutas definitivas de HA real y referencias verificadas; originales
preservados. [Informe](reports/shared-geography-portable-2026-09-15.json).
[Guía vigente](mushrooms/shared-geography-consolidation-es.md).
HA 0.2.304 publicada el 16/09/2026: tags y plataformas GHCR verificados.
Worker existente 1.1.2 validado. HA real no instalada; el usuario instalará.
[Release](reports/ha-release-0.2.304.json). Continuar según `active-context.md`; no repetir la
adopción nativa ni los uploads históricos.

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

## Estado general del trabajo local al 15/09/2026

- Base local del mapa consolidada en imágenes HA/worker reconstruidas y recreadas,
  con huellas efectivas verificadas, smoke y paridad del día 15. Incluye los ajustes
  de UI/idiomas/afinidades y canal online anteriores; ya no depende de copias
  puntuales al contenedor. Copia recuperable en `backups/local-base-20260915/`.
  [Informe](reports/prediction-map-local-images-2026-09-15.json). Sin release HA real.
- Zona horaria visible en Parámetros → Predicción, ES/CA/EN y por dispositivo.
  Fecha inicial y corte meteorológico usan esa zona (inicial Europe/Madrid) tanto
  en HA como en worker; corregido el null general al pasar medianoche con worker
  UTC. [Funcionamiento](mushrooms/prediction-map-local-worker-setup-es.md#calendario-visible-de-la-predicción--15092026).

- **Implementado:** separación territorial/temporal (`territorial_and_seasonal_windows_v6`).
  El lugar selecciona por suelo+pH, hospedadores/hábitat y altitud; el predictor
  conserva fenología y evalúa fecha/meteorología. Decisión posterior: fuera de
  temporada no aparece ni invoca modelo; visibles con etiqueta principal/secundaria.
  Estado territorial separado de la fase diaria. Descartadas sin modelo; salida
  temprana sin candidatas; compatibles sin cálculo al final con null distinto de cero.
  Cuatro reglas locales conjuntas aplicadas: aereus, edulis, pinophilus y cibarius.
  Suelo/pH se conserva por decisión final del usuario; no reabrir la restricción
  por litología. UI: suelo antes de árboles y descartes con motivos separados.
  Volumen/configuración de lectores actuales y paridad HA local–worker ya probados;
  usar el worker existente, destinos intactos. Revisión visual y árboles vecinos
  aplazados al TODO. La caché privada y la publicación geográfica ya están integradas y probadas.
  Pendiente: GEODE/MFE nacional y despliegue de la candidata, sin
  repetir descargas. RPi4 calculará mediante worker en principio, sin fallback local.
  Contraste científico y resto de fichas siguen pendientes.
- Prioridad: **Mapa de predicción**, complementario al Predictor. Preview nueva
  reutiliza MapLibre y muestra terreno/meteorología reales y candidatas ecológicas
  del punto y **probabilidades del motor Python existente**. Compatibles por
  probabilidad descendente; sin cálculo al final. Predicción experimental.
- Fichas/catálogo locales revisados: 21 fichas con ventanas amplias, 115 hosts;
  21 pares pH min/max provisionales aplicados y revisables. Datos de trabajo en `docker-data/mushroom-data/`,
  no en las semillas del repo. Promoción posterior explícita.
- Revisadas las 1.055 unidades geológicas ICGC: 1.046 códigos con equivalencias
  de materiales en 192 reglas compartidas; nueve sin equivalencia segura.
  Composición del suelo puede seguir indeterminada aunque se identifique un
  depósito. Catálogo local ampliado y mezclas conservadas; GEODE siguiente fase.
  No equivalencias fijas en Python. Terreno agrupa árboles/hábitats; las fichas
  de prado/ribera pueden encajar sin árboles. Hosts específicos siguen exigidos.
- Ayuda de las reglas de suelo/pH: [guía de los controles](mushrooms/soil-ph-rule-help-es.md),
  también en Ecología → Suelos mediante «Ayuda», completa en ES/CA/EN.
- Reglas suelo/pH en cuatro fichas locales, sin cambiar rangos ni afinidades:
  silíceo como apoyo no exhaustivo; caliza+pH admitido, condicionado sin presumir
  descalcificación; composición sin resolver, desconocido. Solo aereus conserva
  el ensayo de intervalo solapado, bloqueo de mezcla con carbonatos/yeso y máximo
  6,8. Las otras 17 fichas conservadas; sin vetos geológicos universales. Detalle en
  [sustrato y especies](mushrooms/prediction-map-substrate-species-review-es.md#reglas-locales-conjuntas-v5).
- Rovelló por especie: cuatro IDs/fichas conservados, sin grupo derivado ni
  préstamo de modelos. Motor conectado en preview y ejecutor Python común.
  Paridad/datos de worker y comparación de ejecutores después del bloque de
  compatibilidad descrito arriba; no inferencia en navegador.
- Corregida lectura MFE de candidatos con anillos inválidos: reparación acotada
  en memoria, conservando área y originales. Recuperadas encinas/hayas/castaños
  en los puntos de Fogars y Arbúcies; no faltaban esas capas.
- OpenLandMap pH descargado e integrado en preview: nueve GeoTIFF, 368 MiB en
  `mushroom-map-GIS/openlandmap-ph/spain-v20250204/`. Selección con media, detalle
  con límites e incertidumbre y comparación SoilGrids; profundidad solo en Terreno.
  Si falta dato, píxel válido más cercano hasta 1 km y distancia visible. No repetir
  descarga. Registro: `docs/reports/prediction-map-openlandmap-ph-implementation-2026-09-13.json`.
- SoilGrids descargado/auditado, huecos aceptados; no repetir descargas ni auditoría.
  Lectores candidatos puntuales existen; migración general áreas/microáreas y
  exportación portable de volumen siguen pendientes detrás del mapa.
- `mushroom-map-GIS/` queda fuera de Git/Docker; clone/imagen no transportan mapas.
  Catálogos, perfiles, observaciones y URLs deben preservarse. `mushroom-data/`
  contiene un cambio previo de observaciones del usuario: no incluirlo ciegamente.
- El filtro y motor nuevos están activos en preview y en HA local/worker existente,
  con datos actuales montados en solo lectura y paridad comprobada en ARM64.
  Conjunto geográfico compartido de 15,62 GB mediante referencias portables; aún no incluye integración
  de GEODE/MFE fuera de Catalunya. Alcance objetivo nacional conservado.
  HA real `0.2.303`
  funciona según confirmación del usuario, sin publicación del nuevo mapa.
- Worktree con cambios/archivos nuevos sin commit. `active-context.md` identifica
  código, estado comprobado, pruebas, riesgos y siguiente acción suficiente.

No hace falta leer un tercer relevo para retomar. Los anexos del mapa documental
se consultan solo al profundizar en el componente, sin reabrir decisiones cerradas.

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

- Mapa de predicción, pasos completados y pendientes:
  `docs/mushrooms/mushroom-prediction-map-progress-es.md`
- Mapa de predicción: nuevo informe por coordenadas, complementario al Predictor;
  análisis sin implementación:
  `docs/mushrooms/mushroom-map-point-prediction-feasibility-es.md`
- Fuentes descargadas para ese módulo, separadas en `mushroom-map-GIS/` con
  README junto a los archivos: `docs/mushrooms/mushroom-map-gis-downloads-es.md`
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
- Fuentes y GIS para la expansión Font-Romeu--Quérigut:
  `docs/mushrooms/france-sources/`
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


## Documento archivado: active-context.md

# Active Context

## Release 0.2.307 — 16/09/2026

Imagen verificada en GHCR: `0.2.307` y `latest` comparten digest
`sha256:d8c0c1b110b9d700e980e5409888374b61d1dcd35f0203260f0145c15af8ca46`,
con manifests amd64 y arm64. Publicación autorizada expresamente tras revisión local.
[Informe y evidencia de release](reports/ha-release-0.2.307.json).

Incluye IFF en tres idiomas, colores por favorabilidad, ayuda desplazable,
fechas con día de semana, filas compactas de especies e inventario GIS completo.
HA local y el único worker existente (1.1.3) reconstruidos; 200/107 archivos
efectivos coinciden con el código candidato. Destinos del worker conservados.
Smoke final: 1613 tests, 48 omitidos; navegador correcto y sin desbordamiento móvil.
La cadena local completó reconstrucción, entrenamiento base, 714 ajustes
multiversión y precálculo activado. El cambio posterior de datos KMga4 se validó
con ambos lectores y consulta local del punto; no se repitió esa cadena por él.

Entrega congelada: `tmp/release-0.2.307/ha-data/mushroom-data/`, siete JSON para
`/share/rainmapper/mushroom-data/`. El usuario indica haber copiado sin backup;
no se ha comprobado el destino ni instalado/reiniciado HA real desde el agente.
**Revisión científica adicional en pausa por petición del usuario.** No modificar
la entrega congelada. Hay 471 códigos geológicos aceptados solo por litología,
sin tendencia de suelo, además de 17 pendientes. No está cerrada la investigación
de suelos de todas las formaciones. El cambio IFF es presentación; las revisiones
GIS no reescriben modelos ni precálculos existentes.
Observaciones privadas y documentación GBIF ajenas quedan fuera del commit.

## Antecedente: release 0.2.305

Estado del 16/09/2026. **HA 0.2.305 publicada y verificada en GHCR**: versión y
`latest` tienen el mismo digest y manifests amd64/arm64. Actualización aceptada
por el usuario tras revisar HA local; instalación de HA real pendiente del usuario.
[Informe de release](reports/ha-release-0.2.305.json).

Incluye encuadre móvil tras login/recarga, cabecera de predicción compacta,
fila Zona/Fecha alineada (selector 98×24 px), Cancelar compacto y etiqueta «Local».
Worker es el valor inicial sin preferencia guardada; un rechazo inicial 503 por
indisponibilidad/ocupación se reintenta una vez en Local sin modificar el setting.
No se reintentan trabajos ya aceptados ni errores genéricos o cancelaciones.
[Informe móvil y pruebas](reports/map-mobile-login-2026-09-16.md).

Puerta local completada desde la candidata: HA y worker reconstruidos y recreados,
198/106 archivos efectivos idénticos al worktree, coordinadores persistidos sin
cambios. Smoke 1.600 tests/48 omitidos correcto; navegador 29 peticiones correcto.
Safari local: consulta real Worker 2,14 s total / 1,42 s cálculo; fallback controlado
Worker → Local conserva el setting. Worker permanece en 1.1.2, sin release nueva.
No hay cambios científicos ni GIS: no regenerar mapas, entrenar, recalcular ni
volver a subir datos para instalar 0.2.305. Recargar el visor tras actualizar.
Pendiente confirmar en iPhone físico el comportamiento tras login y recarga.

HA 0.2.304 fue probada por el usuario en real, incluyendo ejecución por worker.
La disponibilidad requirió habilitar `primary` en el override de mapa del M1;
[diagnóstico anterior](reports/map-worker-real-ha-2026-09-16.md).
Conservar los originales de media hasta validar el funcionamiento en HA real.
No repetir uploads de GiB ni ejecutar comandos de preparación al primer arranque.
Ediciones ajenas de `mushroom-data/mushroom_observations.json` y documentación GBIF
quedan fuera de esta release; datos privados locales y reales preservados.

## Geografía portable: evidencia de la release 0.2.304

La nueva versión lee archivos ordinarios desde `/media/rainmapper/geography`.
No hay comandos de primer arranque, symlinks ni recibos dependientes del equipo
para instalar los datos en HA. GIS y SoilGrids usan `mushroom-GIS`; mapa resuelve
sus referencias al mismo archivo compartido mediante un manifiesto portable.
Configuración de reserva en `geography/map-config.json` si no hay una explícita.

- Smoke actual: 1.600 tests, 48 omitidos, OK. Ambos contenedores reconstruidos y
  recreados, 198/106 archivos efectivos sin diferencias. Versiones 0.2.304/1.1.2.
- Cuatro lecturas GIS/contextos iguales a la estructura anterior y seis consultas
  autenticadas con igualdad local/worker, incluso concurrentes; permisos básicos,
  401 sin sesión y cancelación correctos. El usuario confirmó que vuelve a
  funcionar el ejecutor local tras arrancar los contenedores.
- Primer acceso sin red, sistema y media de solo lectura: configuración detectada,
  ejecutor local listo, inventario GIS de 13 archivos. Ninguna preparación al arrancar.
- Worker reutiliza 3.510 archivos con 0 bytes de transferencia, metadatos y hash.
  URLs de ambos coordinadores conservadas. No se han lanzado nuevos entrenamientos
  o precálculos: el contrato GIS y contenido son idénticos al circuito completo ya
  validado. Este cambio de rutas tiene pruebas dirigidas y paridad reales.
- Limpieza local aplicada: retirados objetos/recibos/vistas HA antiguos; 3.581
  archivos ordinarios compartidos, 15.622.243.791 bytes lógicos más metadatos.
  Conservados originales del repositorio, datos privados, backups y caché worker.
- HA real: 3.581 archivos colocados en sus rutas definitivas y referencias finales
  verificadas (3.510 mapa / 1.432 GIS). Archivos ordinarios, sin enlaces creados ni
  recibos nativos. `SHA256SUMS` junto a siete manifiestos/configuraciones. Los tres
  directorios originales intactos. No se ha instalado/reiniciado/ejecutado HA real.

[Guía vigente](mushrooms/shared-geography-consolidation-es.md) e
[informe final](reports/shared-geography-portable-2026-09-15.json). Fuentes y hashes
recuperables en `backups/ha-portable-ready-20260915/`. Candidata publicada como HA 0.2.304;
la instalación y prueba RPi4/iPhone las hará el usuario. No repetir cargas de GiB,
adopción antigua ni circuito local por cambios únicamente documentales.
Las imágenes arm64 y paquetes guardados en `ha-map-candidate-20260915` son previos
a esta corrección: no confundirlos con las imágenes locales actuales comprobadas.

El estado anterior queda en
[contexto previo](reports/context-before-portable-close-2026-09-15.md).
Los apartados siguientes conservan el alcance y las validaciones históricas de
la candidata; las rutas/instalación vigentes son las descritas arriba.

## Candidata local aceptada técnicamente — 15/09

**Trabajo autónomo local completado. No publicado en GHCR ni instalado en HA real.**
El usuario hará la instalación; no tocar la RPi4 ni publicar como continuación
implícita. [Informe final](reports/prediction-map-geography-2026-09-15.json).

HA **0.2.304** / worker **1.1.2** reconstruidos y recreados desde fuentes; verificados
194 archivos HA y 103 worker dentro de imágenes y contenedores, sin diferencias.
Smoke final: **1581 tests, 48 omitidos, OK**. Seis consultas reales con usuario básico,
paridad exacta HA local/worker, repetición, concurrencia y cancelación correctas.
La prueba usa el batch operativo nuevo y produce probabilidades. Estos tiempos
son del M1 local, no una medición de rendimiento de la RPi4.

Circuito local mediante worker completado y auditado:
- `worker_job_uS0z1vBVTD7vB6m-`: reconstrucción verificada y promovida.
- `worker_job_JcDC_qjKhmWtnGSa`: entrenamiento base, nueve especies, promovido.
- `worker_job_d0_gpX_RtsLf0K9Q`: 714/714 ajustes; cinco generaciones instaladas
  del batch `operational_20260915T013504Z`.
- `worker_job_0BvFFmJkAIaj`: precálculo recibido y activo, revisión 61,
  artefacto `sha256:6f60d84e9bc6c5fc87b31ffe0e10817278eb00cb025289d533e21585c4480fc5`.
No repetir estos trabajos: no quedan directorios terminales en el worker.

Correcciones detectadas durante aceptación: caché preparada y online ocupado se
tratan por separado para aceptar la cola acotada; notas de auditoría `installation`
no invalidan modelos idénticos. La comparación sigue exigiendo igualdad de
`installed_generation_id`, generaciones y contratos de artefactos. Cambios finales
solo en módulos del mapa, reconstruidos y probados después; el código científico
no cambió respecto al circuito ejecutado (huellas en el informe).

Cartografía con autoridad en `/media/rainmapper/prediction-map`: HA vigila el pequeño
`CURRENT.json`, sin rehashear los GiB. Transferencia fría real al volumen del worker:
3510 archivos, 14.538.214.301 bytes. Reinicio: cero bytes transferidos/rehasheados.
Sin `/maps` compartido en ambos contenedores. Tras promoción, caché privada:
790 archivos reutilizados y solo 31.538 bytes descargados del registro cambiado;
cartografía intacta. Una vista geográfica, dos privadas y ninguna descarga parcial.
Coordinadores, fichas, catálogos, mappings, setales, observaciones y credenciales
preservados. Los cambios de datos son los derivados esperables del circuito local.

Paquete recuperable en `backups/ha-map-candidate-20260915/`: cartografía comprimida
(12.127.781.210 bytes) con hashes, imágenes locales arm64, fuentes, configuración de
ejemplo y backup previo a pruebas. [Guía de importación](mushrooms/prediction-map-ha-media-install-es.md).
No es una release multiarch publicada. Siguientes pasos: aceptación del usuario,
publicación según `release-flow.md`, importación de datos y prueba iPhone en HA real.
GEODE/cobertura ecológica nacional y revisión a fondo de suelo/pH siguen en TODO.

## Cadena operativa en background — 15/09/2026

Autorizado por el usuario después de confirmar que su trabajo había acabado.
Cambio de código: reconstrucción, ML base y ML multiversión (incluido benchmark)
comparten background con el precálculo. El mapa/Predictor interactivo conserva
online. La preferencia por el coordinador de la cadena sigue el carril recibido;
promoción y verificaciones permanecen en HA. Sin migración ni transporte extra.
41 pruebas de cola, 41 de servicio y 343 de API correctas; smoke 1565/48.
HA local y worker existente reconstruidos y recreados, 193/101 archivos iguales
a fuentes en imágenes y contenedores. Coordinadores conservados, canales libres
antes de recrear. Esa aceptación inicial no ejecutó trabajos científicos reales; el circuito completo
local se completó después, como se indica arriba.
[Informe](reports/worker-background-chain-2026-09-15.json).
[Funcionamiento y compatibilidad con HA antiguo](mushrooms/mushroom-worker-multicoordinator-design-es.md#reparto-de-canales--incremento-del-15092026).
La prohibición de instalar HA real sigue vigente. No duplicar la cadena local ya completada.

## Mapa unificado y permiso individual — 15/09/2026 (aplicado y validado localmente)

**Incremento completado:** datos privados conectados al almacén de objetos del worker,
sin montajes privados del Mac. HA reutiliza hashes sellados de modelos/meteorología;
hash inicial de entradas pequeñas: 482.575 bytes. Worker reutilizó 787 archivos y
descargó cuatro (475.540 bytes), más manifiesto de 269.782 bytes, antes del clic.
Imágenes/contenedores verificados: 193 archivos HA y 101 worker; seis consultas reales
con paridad exacta local/worker, repetición y cancelación correctas. Smoke 1561/48,
10 pruebas de caché y 14 de rutas. [Informe](reports/prediction-map-private-cache-2026-09-15.json).
El precálculo que el usuario protegió entonces ya terminó. No publicado HA real.
[Diseño, explicación y límites](mushrooms/prediction-map-private-cache-es.md).
Conservar la posición del interruptor de predicción por petición del usuario.

Decisión del usuario: en HA real el visor habitual incorporará la capa de
predicción. `/protected/maplibre/index.html` y el alias anterior
`/protected/prediction-map/index.html` sirven la misma composición del visor;
se conservan estaciones, meteorología y recursos compartidos.

`can_use_prediction_map` se guarda en la ficha de usuario, junto a Heatmap,
Métricas e IDW. Es explícito para **todos los roles**, incluidos administradores;
si falta, queda desactivado. La UI Usuarios permite activarlo o retirarlo.
La API exige la sesión existente y ese permiso en cada consulta: ningún bypass
por rol. El visor retira los controles cuando se refresca una sesión revocada.

No hay otro login ni otra persistencia: se reutilizan `/auth/*` y los ajustes
por dispositivo. Ejecutor, idioma y zona horaria siguen en esos ajustes;
retirar el permiso no los borra. La preview permanece aislada, sin auth real.

Validación: 13 pruebas de contrato/rutas, 343 de autenticación, navegador con
usuario básico autorizado, admin revocado, URL habitual, meteorología y
persistencia. Smoke completo: 1552 tests, 48 omitidos. Ambas imágenes reconstruidas
y contenedores recreados: 192 archivos HA y 100 worker coinciden con las fuentes.
Consulta real con usuario básico temporal: seis consultas local/worker, tres
especies con cálculo, paridad exacta, repetición/concurrencia/cancelación correctas.
Usuario y dispositivo temporales retirados; registros previos de usuarios iguales.
Coordinadores y volúmenes conservados. No publicado en HA real.
Informe: `docs/reports/prediction-map-user-permissions-2026-09-15.json`.

Prueba manual local: `http://127.0.0.1:8101/users` → usuario → **Prediction access**
→ **Save user**. Abrir/recargar `http://127.0.0.1:8101/protected/maplibre/index.html`
con la sesión habitual. No se ha activado automáticamente para usuarios existentes.

El puerto local sigue enlazado a `127.0.0.1:8101`; no es accesible directamente
desde iPhone. No exponer todo ese servidor a LAN: incluye administración local.
Si se habilita una prueba móvil local, limitarla al visor y API autenticadas.
La caché privada por asociación ya está conectada y probada sin montajes privados
compartidos. Sigue pendiente su despliegue en HA real y la aceptación de release.

## Incremento anterior y prioridades históricas (ver actualización de caché arriba)

**Base local incorporada a imágenes, 15/09:** HA local y el worker existente se
han reconstruido desde el mismo worktree y recreado sin copiar código de aplicación
después. Verificados 192 archivos en HA y 100 en worker contra fuentes, tanto en
imágenes como dentro de contenedores; sin diferencias. Incluye todos los ajustes
anteriores de mapa, idiomas, ayuda, canal online y editor de afinidades. El botón
«Añadir fila» también se inicializa al cambiar de especie por AJAX, no solo al
cargar la página. Los wrappers de arranque incorporan los overlays del mapa cuando
ya existe su configuración; recrear con ellos conserva sus montajes.

**Calendario visible:** Parámetros → Predicción → Zona horaria de la predicción,
con ayuda ES/CA/EN y guardado por dispositivo. Valor inicial `Europe/Madrid`.
La fecha inicial ya usa esa zona, no la del navegador. Cada consulta lleva
`calendar_timezone` validada hasta los lectores de HA/worker y el resultado debe
devolver la misma; visible bajo la fecha. Conserva el ajuste al guardar desde
el mapa meteorológico. Informes abiertos mantienen su zona original.
Corregido el fallo de medianoche: el worker UTC consideraba el 14/09 todavía
«hoy» cuando en Madrid ya era 15/09, rechazaba el corte meteorológico del 14 y
mostraba todas las especies sin cálculo. No cambia modelos ni inventa datos;
se mantiene la protección contra cortes futuros y la abstención por datos/modelos.
[Semántica y configuración](mushrooms/prediction-map-local-worker-setup-es.md#calendario-visible-de-la-predicción--15092026).

Validación final: smoke **1.551 tests, 48 omitidos, OK**; Chrome con 20 consultas
fixture, zona del navegador Honolulu/mapa Kiritimati, persistencia, escritorio/móvil
y ruta meteorológica. API HA local–worker para el 15/09: paridad exacta, repetición,
concurrencia y cancelación; tres especies calculadas en La Vansa/Montclar.
Sagàs (41.98996, 1.90109): aereus y caesarea vuelven a tener siete probabilidades.
Perfiles, datos y backups del usuario preservados; URLs del worker idénticas por
SHA256 antes/después. Se esperó a que finalizaran los trabajos que lanzó el usuario.

Evidencia e identidades finales: [informe de base local](reports/prediction-map-local-images-2026-09-15.json).
Copia recuperable local en `backups/local-base-20260915/`: source completo con
archivos nuevos, hashes, configuración y JSON privados actuales/anteriores.
Los modelos, meteorología y GIS permanecen en sus volúmenes; no se duplicaron GB.
Etiquetas locales conservadas: `rainmapperha:local-base-20260915` y
`rainmapper-worker:local-base-20260915`. **No hay publicación ni actualización de
HA real, ni commit/push del worktree.** Seguimos con dos mapas; el meteorológico
actual y la preview sin autenticación real se conservan.

Siguiente: integrar la caché privada por asociación con el mapa y completar GIS
nacional. Antes de HA real sigue pendiente el circuito local de entrenamiento,
promoción y precálculo aplicable y la aceptación expresa, según `release-flow.md`.
No lanzarlo automáticamente: esta tarea solo autorizó builds/recreaciones locales.
La revisión científica de suelo/pH y la revisión visual a fondo/árboles vecinos
siguen aparcadas en TODO. No reabrirlas por este arreglo.

## Historial de los incrementos incorporados a la base local

Las referencias siguientes a copias puntuales o imágenes pendientes describen
el momento original de cada ajuste: quedan superadas por la reconstrucción del
15/09 documentada arriba.

**Edición de afinidades corregida, 14/09:** el decodificador HTTP omite valores
vacíos; el parser anterior terminaba al primer índice ausente y perdía las filas
posteriores a un ID puesto en «-». Ahora recorre los índices enviados, conserva
metadatos de identidades sin cambiar y mantiene las afinidades ocultas de V0.
Marcador de grupo permite vaciar una lista completa. «Añadir fila» en V0 y
Enriched, con opciones del catálogo, prevención de duplicados y ayuda ES/CA/EN.
Se aplica a hosts, bosques, suelos, litología y rasgos de hábitat.
Seis pruebas dirigidas pasan, incluidas primera/intermedia/última fila vacía,
índices separados, cero, metadatos, datos ocultos y validación de duplicados.
Navegador sobre HA local: añadir dos filas por grupo, seleccionar catálogo,
vaciar la primera sin alterar las restantes, V0/Enriched y anchos 1600/390.
Código y etiquetas copiados a HA local, reiniciado y SHA-256 comparados con
fuentes; no se reconstruyeron imágenes ni se modificó el worker.

Recuperación limitada a `tricholoma_terreum.ecology.host_affinities`: restaurados
`host_pinus_nigra` y `host_pinus_sylvestris` con sus metadatos del backup
`mushroom_profiles.20260914T194237Z.json`. El backup mostrado en la captura
(`194342Z`) ya contenía el borrado. Abeto blanco sigue eliminado; todos los demás
campos y perfiles actuales, incluidos cambios posteriores de suelo, se conservan.
Validación: 0 errores, 104 avisos. Copia previa a la recuperación conservada en
`docker-data/mushroom-data/backups/mushroom_profiles.20260914T195548693692Z.affinity-recovery.keep.json`.
Incorporar estos cambios en la próxima imagen autorizada.


**Hover inmediato por fecha, 14/09:** eliminado `<title>` de puntos de la gráfica
semanal, que dependía de la demora nativa del navegador. Tooltip propio sin espera
al mover el puntero por una columna de fecha; muestra juntas todas las especies
calculadas ese día y sus colores, sin acertar en puntos próximos/solapados.
Posición horizontal acotada a la gráfica, sin capturar clics; salir/Escape oculta.
Foco de teclado en punto muestra el mismo desglose. Sin valores se indica sin
probabilidad calculada, sin inventar cero. No consulta ni recalcula; preserva
selector/clic de fecha. Prueba de navegador final pasa (20 consultas fixture),
incluida aparición síncrona lejos de curvas, las tres especies, borde derecho,
teclado y día sin valores. Captura inspeccionada. JS/CSS copiados a HA local y
huellas servidas por HTTP verificadas. Sin reinicios ni cambios del worker/datos;
incorporar en la próxima imagen autorizada.

**Colores de curvas, 14/09:** corregida asignación que consumía posiciones para
todas las especies del catálogo y dejaba curvas visibles con verdes muy próximos.
Solo consumen color las especies compatibles con alguna probabilidad finita en
temporada durante la semana (0 incluido, null no). Paleta contrastada inicial de
ocho colores sin repetición; extensión por tonos para más series. Identidad
ordenada y conjunto semanal mantienen colores al cambiar fecha/ranking/idioma;
curva y marcador de lista comparten color. Los colores pueden cambiar entre
puntos con conjuntos calculados distintos. Prueba de navegador correcta (19
consultas fixture), incluida regresión de 21 especies con solo tres curvas
próximas: Edulis azul, Pinícola naranja y Rovelló morado. Captura inspeccionada.
JS copiado a HA local y verificado por HTTP; sin reinicios, cambios de cálculo,
worker o datos. Incorporar en próxima imagen autorizada.

**Mapa por canal online/foreground, 14/09:** decisión expresa del usuario:
background puede ejecutar precálculo mientras online atiende el mapa. Corregido
el bloqueo global que impedía sondear consultas si había cualquier trabajo activo.
El mapa conserva su contrato efímero por coordenadas, pero comparte una reserva
global de foreground con los trabajos online existentes; no añade un tercer
cálculo concurrente ni un canal por coordinador. Reserva no bloqueante antes de
reclamar, retenida hasta finalizar y liberada también con errores; background
conserva su carril independiente. Cuando online está ocupado, acción autenticada
`busy` mantiene presencia sin reclamar; broker devuelve `worker_busy`, distinto
de desconectado, con texto ES/CA/EN. El visor usa la capacidad de predicción para
el aviso inicial; ya no inventa modo simulado mientras espera el primer resultado.
23 pruebas dirigidas pasan (incluido servicio con dos coordinadores y concurrencia
de carriles); navegador correcto con aviso de ocupado (18 consultas fixture).
Aplicado en HA local/worker por copia, sin imágenes nuevas. Worker reiniciado solo
con ambos carriles libres y configuraciones de coordinador idénticas por hash.
No se lanzó ni canceló entrenamiento/precálculo real durante este arreglo.
Comprobación final HA local→worker tras el cambio: `worker_ready=true`,
`data_mode=prediction`, 7 especies, cálculo 1277,742 ms; sesión temporal eliminada.

Diagnóstico que originó el cambio: `worker_job_UbGvg0cuhtud` era precálculo de
`primary` (HA real), no de la cola local mostrada. Log confirmó fin/liberación a
19:04:10 UTC (21:04:10 local). La tarjeta «En espera» mira solo foreground y puede
ocultar actividad de background; queda pendiente mejorar el resumen de la tarjeta.
El predictor remoto `worker_predictor_v1` se asigna a foreground cuando se crea
ese trabajo; no significa que toda consulta del predictor vaya al worker, porque
puede servirse del precálculo existente.

**Ayuda de suelo/pH, 14/09:** disponible en Ecología → Suelos, V0 y Enriched,
como desplegable explícito «Ayuda: cómo funcionan el suelo y el pH». Explica los
ocho controles, pH, excepción, afinidades, duplicidad aparente de Silíceo,
Calizo condicionado/bloqueador, ejemplo aereus/ou de reig y guardado. Texto
completo ES/CA/EN, 14 secciones; [guía fácil de consultar](mushrooms/soil-ph-rule-help-es.md).
Dos pruebas dirigidas pasan; navegador en HA local verifica apertura sin cambios
en campos y sin desbordamiento a 1600/390 px. Render de tres idiomas comprobado
en contenedor sin etiquetas ausentes. UI y etiquetas copiadas a HA local y
reiniciado solo ese contenedor; hashes coinciden. Sin editar fichas ni reglas,
sin worker/build/publicación. Incorporar cambios en próxima imagen autorizada.

**Hospedadores ES/CA/EN, 14/09:** corregido el lector forestal y el mapa para
usar `common_names` del catálogo local según el idioma seleccionado. Los 115
hospedadores ya tenían los tres idiomas: no se editó el catálogo. `labels`
transporta tres nombres acotados; `label` conserva compatibilidad anterior.
Sin traducción se muestra el nombre científico; alias ambiguos siguen sin
asignarse. Cambiar idioma no repite consultas y editar nombres conserva la caché
geográfica. Trece pruebas GDAL pasan en directorio temporal del worker y prueba
de navegador ES→EN→CA→ES pasa, incluidos fallback y payload antiguo.
Punto 41.98967, 1.90060 comprobado en lector del worker: Alzina/Holm oak,
Roure martinenc/Downy oak, Arboç/Strawberry tree. Cambios copiados a HA local y
worker, reiniciados tras comprobar worker idle; hashes de archivos y de ambas
configuraciones de coordinador verificados. JavaScript servido por HTTP coincide.
Sin builds/publicación: incorporar estos archivos en la próxima imagen autorizada.

**Inglés para demostración, 14/09:** el usuario pide enseñarlo a su jefe como
ejemplo para posibles predicciones en alquileres de M3. Verificados los 117 textos
del mapa con traducción EN y prueba de navegador ES→EN→ES con resultado abierto:
cabecera, máximo semanal, temporada, sin cálculo y gráfica; fecha conservada y
sin nuevas consultas. Activado `settings.language=en` en el único Safari local
habilitado de `carlos` que usa worker; demás ajustes/dispositivos intactos.
Es la preferencia compartida del visor por dispositivo. Recargar para aplicarla.
El pendiente de nombres forestales detectado entonces queda resuelto en el
incremento anterior. Los nombres de especies siguen los definidos en ficha;
no afirmar que todos los datos descriptivos están traducidos. La activación
inicial de idioma no modificó código ejecutable.

**Editor de reglas suelo/pH, 14/09:** el usuario detectó que la regla de exclusión
por falta de suelo solo estaba en JSON. Ahora Ecología → Suelos, en V0/Enriched,
expone los siete campos de `ecology.soil_filter`: exigencia de contexto, suelos
de apoyo/condicionados/excluidos, suelos que bloquean excepción de pH, modo de
excepción y referencia. Activación explícita; sin regla no se crea al guardar.
Metadatos expone además `map_display_name`, otro campo usado por el mapa que
faltaba en el formulario. Las afinidades antiguas y «Evitar» no se presentan como
vetos. Validación compartida de reglas y catálogo local antes de guardar.
Cuatro pruebas dirigidas pasan, incluidos rechazo de IDs/conflictos/referencia
vacía y conservación de otras fichas/campos; pruebas en copias temporales locales.
Controles comprobados por HTTP/navegador en HA local, escritorio/móvil sin guardar.
Perfiles, catálogo, mappings y observaciones reales mantienen sus hashes previos:
no se ha desactivado `require_soil_context` de aereus ni cambiado ninguna regla.
Dos módulos de UI y etiquetas copiados/reiniciados solo en HA local; imagen
pendiente de reconstruir en la siguiente construcción autorizada. [Detalles](mushrooms/prediction-map-local-worker-setup-es.md#edición-de-las-reglas-de-suelo-y-ph).

**Diagnóstico Merlès solicitado, 14/09:** punto 42.01392, 1.96982, fecha
2026-09-14 consultado con el lector geográfico del worker y sus datos montados.
Aereus pasa hospedadores, altitud, pH y temporada principal, pero queda `unknown`
por `soil_unresolved`: unidad ICGC `Q`, depósitos de fondo de valle/rambla/piedemonte,
sin tendencia edáfica resuelta en el mapping. Ou de reig queda compatible porque
su ficha no exige ese contexto conjunto; asimetría de criterios entre fichas,
no evidencia de ausencia de aereus. No se modifican reglas ni mappings:
suelo/pH sigue aparcado. [Respuesta del lector](reports/prediction-map-merles-soil-unresolved-2026-09-14.json).

**Gráfica semanal en cabecera, 14/09:** añadida al final de la cabecera fija,
después de la fecha. Usa exclusivamente las siete probabilidades recibidas del
ejecutor para las especies visibles. Color por identidad, estable al cambiar
fecha/orden, compartido por curva y marcador de la fila. Cada fila calculada
muestra máximo semanal y primera fecha del pico; `null` interrumpe la curva,
0 permanece válido, sin modelo no tiene curva ni máximo inventado. Respeta
temporadas por día. Pulsar la gráfica cambia fecha sin consultar al worker.
Prueba de navegador escritorio/móvil correcta, incluyendo huecos, cero, ausencia
de modelo, colores, temporadas y cabecera fija. Recursos visuales y traducciones
copiados a HA local; reiniciado solo HA local para cargar etiquetas. HTTP coincide
con fuentes y API vuelve a anunciar `worker_ready: true`. Sin build ni cambio de
datos/modelos/worker/HA real; incorporar cambios en próxima imagen local autorizada.

**Cabecera fija del popup, 14/09:** por petición del usuario, título/cierre,
ubicación, terreno, tiempos y selector de fecha permanecen fuera del scroll.
Solo especies, avisos y desplegables se desplazan en `.pm-result-body`.
En mapas estrechos se ajusta el encuadre si falta altura para cabecera y contenido,
manteniendo el punto y la flecha. Prueba de navegador escritorio/móvil pasa,
incluidos fecha visible al desplazar, cambio de fecha, bordes y visor meteorológico.
Tres recursos visuales actualizados en HA local y verificados contra HTTP:
`prediction-mode.js`, `prediction-mode.css`, `prediction-bootstrap.js`.
Siguen pendientes de incorporar a la imagen en una construcción local posterior;
no se reconstruyó/reinició ni se cambió worker, datos o HA real.

**Ajuste visual posterior, 14/09:** el usuario probó el mapa mediante worker en
HA local y detectó popups demasiado bajos cerca del borde superior. El popup
lateral ahora desplaza su cuerpo dentro del mapa y compensa la flecha hacia el
punto; en escritorio (ancho de mapa ≥900 px) aprovecha la altura disponible sin
el tope de 650 px. Foco del cierre sin desplazar el contenido; ajuste al cambiar
altura/contenido o mover el mapa. Navegador escritorio/móvil y cuatro posiciones
de borde pasan. Solo el JS visual se ha actualizado en el contenedor HA local,
verificado por SHA256 de la respuesta HTTP; la imagen aún contiene el JS anterior.
No hubo build, reinicio ni cambio en worker/HA real o autenticación de preview.
La revisión visual general aplazada sigue en TODO.

**Último incremento: volumen y paridad HA local–worker, 14/09.** El usuario aplaza
revisión visual a fondo/Safari y árboles vecinos (siguen en TODO), y autoriza
preparar datos/configuración y comparar ejecutores. Se usa el worker existente,
no uno adicional. Ambos contenedores reconstruidos, montajes de mapa en solo lectura
y canal de la asociación HA local activados. URLs/credenciales persistidas intactas.
La preview ficticia se conserva. [Instalación, comandos y límites](mushrooms/prediction-map-local-worker-setup-es.md).

Generación pública local: 3.510 archivos / 14.538.214.301 bytes lógicos,
reutilizados por enlaces duros (cero copia adicional); segunda instalación sin
transferencia ni rehash. Contiene dependencias de lectores actuales; **no completa
España**: GEODE y MFE fuera de Catalunya siguen sin integrar. El usuario confirma
alcance nacional, no recortar territorio. Preparar estas integraciones sin repetir
descargas/auditorías. La portabilidad nacional y la aceptación en otra máquina
quedan abiertas; la paridad del cálculo actual sí está probada en Linux ARM64.

La Vansa/Montclar: resultados idénticos, repetición/concurrencia, cancelación,
401/400 y worker desconectado→503 sin fallback correctos. Once archivos compartidos
con hashes idénticos al source en ambos contenedores. [Informe](reports/prediction-map-local-worker-integration-2026-09-14.json).
**RPi4: cálculo mediante worker en principio.** HA local se usa como referencia
de paridad; no extrapolar estos tiempos al Raspberry ni trasladarle configuración
de cálculo local automáticamente. No hubo entrenamiento, precálculo o release.
La prueba comparte datos privados de HA local por montajes de solo lectura.
Antes de HA real falta integrar el mapa con las generaciones privadas de esa
asociación en el worker; nunca sustituirlas por `docker-data` del Mac. Cartografía
pública reutilizable, perfiles/modelos/meteorología separados por coordinador.

**Última precisión del usuario: minimizar transporte durante la predicción.**
Reutilizar meteorología del precálculo y fichas existentes si coinciden con las
versiones aprobadas por HA. El runtime actual ya reutiliza recibos/objetos y
transfiere solo archivos cambiados (cuatro pruebas dirigidas pasan); **el mapa
todavía no está conectado a esa caché**. Su integración debe usar referencias
compactas, evitar manifiestos completos/hashes/TARs por clic y sincronizar solo
lo ausente, con versiones coherentes y permisos por asociación. No confundir
la prueba con montajes locales con una prueba de ese transporte. [Contrato y
aceptación pendiente](mushrooms/prediction-map-local-worker-setup-es.md#sincronización-privada-y-caché-requisito-acordado-integración-pendiente).

**Implementado localmente: `territorial_and_seasonal_windows_v6`.**

1. **Especies posibles en el lugar:** suelo+pH conjuntamente, hospedadores o
   hábitat y altitud. `status` territorial no cambia por mes ni meteorología.
   `daily_statuses` es una proyección idéntica, validada por contrato/navegador.
2. **Lista visible y cálculo en una fecha:** decisión posterior del usuario:
   **fuera de temporada no debe aparecer**. Solo se muestran fases principal o
   secundaria, con esa etiqueta junto a la especie. La clasificación procede de
   los meses originales y de la función compartida con el Predictor en
   `mushroom_phenology.py`; humedad/temperatura siguen en el motor existente.
   `daily_season_phases` está separado del estado territorial. La lista visible
   sí puede cambiar con la fecha; no hay descuentos arbitrarios del porcentaje.

`territorial_candidates` conserva el primer nivel; `prediction_candidates` añade
la temporada entre lector, ejecutor y runtime. Se filtra antes del contexto hídrico
para modelos y de inferir; las fechas fuera de temporada no invocan modelos. Se respeta la
selección de especies solicitada. Sin candidatas no se llama al proceso del
motor; el runtime también retorna antes de abrir modelos/meteorología. Si ninguna
candidata tiene evidencia de modelo, no prepara meteorología del modelo.
El desplegable meteorológico permanece independiente. Compatibles sin modelo o
con abstención permanecen al final con «Sin probabilidad calculada»: `null`, no 0.

**Cuatro fichas locales revisadas:** aereus, edulis, pinophilus y cibarius s.l.
Cambios limitados a `ecology.soil_filter`; pH, hosts, fenología, altitudes y ediciones
restantes preservados por comparación estructural. Silíceo es apoyo no exhaustivo;
caliza+pH admitido produce admisión condicionada, nunca descalcificación confirmada.
Otros tipos conocidos no preferidos pueden entrar condicionados. Sin composición
resuelta, abstención por falta de información; sin nuevo veto litológico.
Solo aereus conserva la excepción de intervalo solapado y el máximo 6,8.
[Reglas completas y procedencia](mushrooms/prediction-map-substrate-species-review-es.md#reglas-locales-conjuntas-v5).
UI con avisos de admisión condicionada y desplegable de descartadas/desconocidas.
Descartadas: nombre en línea propia, cada motivo debajo y filas separadas;
corregida la concatenación visual de nombres/motivos.
Cabecera «Terreno»: tipos de suelo primero, después árboles/hábitats. Etiquetas
del catálogo recibido en `mapped_context.soil_tendencies`, mezclas conservadas;
suelo en color tierra, sin inferir categorías nuevas desde pH ni cambiar filtros.

**Siguiente:** integrar el mapa con la caché privada existente según el requisito
anterior y completar integración nacional (GEODE y MFE fuera de Catalunya)
y su paquete operativo; no reducir el alcance a Catalunya. Revisión visual a fondo
y recuperación forestal vecina aplazadas por el usuario al TODO.
El usuario ha aparcado suelo/pH: conservar reglas; la revisión de otras fichas y
vinosus sigue pendiente, sin reabrirla automáticamente ni cambiar datos en silencio.
La aceptación del cálculo actual en HA local–worker está realizada arriba; no
confundirla con validación científica, cobertura nacional o permiso de release.
No repetir el incremento ni las comprobaciones ya terminadas si no cambia código.

Balance y orden de los pendientes actualizados en
[el seguimiento del mapa](mushrooms/mushroom-prediction-map-progress-es.md#balance-y-próximos-pasos--14092026).

## Contraste posterior solicitado: presentación temporal y suelo condicionado

Diagnóstico del segundo punto del usuario: **42.29077, 1.53842**, distinto del
primer punto de La Vansa. API actual: 1.784 m, pino rojo, unidad `Tk` (margas y
calizas margosas), OpenLandMap 6,4 [5,4–7,3]. V5 admite condicionados edulis y
pinophilus; reproduce 61 % y 28 % redondeados para 14/09. Ambos incluyen septiembre
en sus fichas. No hay evidencia de carbonatos superficiales/descalcificación medida.
**Decisión posterior cerrada del usuario:** conservar las reglas actuales de
suelo/pH. Rechaza exigir tipo de suelo y confirmación por pH porque descartaría
setales conocidos de aereus. No implementar esa restricción ni cambiar admisiones
condicionadas. La revisión puntual también confirmó componente calcáreo en las
unidades de Olvan/Merlès; geología y pH no describen exhaustivamente el suelo del
setal. Esta decisión no revierte el filtro estacional ni sus etiquetas.
[Diagnóstico exacto](reports/prediction-map-vansa-second-diagnosis-2026-09-14.json).

En el primer punto de la captura (42.17076, 1.84548), marçot figura territorialmente
posible y devuelve abstención; su ficha excluye septiembre. Fredolic incluye
septiembre secundario y devuelve falta de modelo. La decisión posterior ya está aplicada: marçot se oculta y no llega al modelo;
fredolic aparece con «Temporada secundaria» y sin modelo. No se cambiaron meses
ni reglas de suelo. 106 pruebas y Chrome; respuesta actual de este mismo punto
verificada en el [informe v6](reports/prediction-map-season-visibility-2026-09-14.json).

**Descalcificación en las capas reales:** OpenLandMap instalado solo aporta pH e
incertidumbre. En atributos ICGC no aparecieron descalcificación/descarbonatación;
Orst/Orst1/mc_Orst mencionan nódulos disueltos en roca/protolito. **GEODE sí contiene
el concepto en unidades cartografiadas**: unidad 247, Z1000, «Fm. Oviedo: calizas,
a veces descalcificadas, y margas», confirmada en servicio oficial y bloque local
`layer-8/0016000.json.gz` (OBJECTID 16027/16028). «A veces» no localiza ni mide el
horizonte superficial en cada punto. GEODE aún no es el lector integrado de estos
puntos catalanes. [Evidencia acotada](reports/prediction-map-gis-decalcification-2026-09-14.json).
No confundir la categoría del catálogo con datos asignados a una coordenada.

Setal adicional comunicado por el usuario: **Montclar, 42.02466, 1.77189**,
aereus presente según su testimonio. No denunciaba exclusión actual: ilustra que
un veto por componente calcáreo perdería un setal conocido. Consulta actual:
763,8 m, pH estimado 6,6 [6,1–7,9], encina/roble pubescente, unidad `POmlg`,
tendencias calcárea/arenosa. Aereus admitida condicionada y temporada principal.
Reglas conservadas, sin excepción por coordenadas ni alta en observaciones.
[Registro del contraste](reports/prediction-map-montclar-aereus-2026-09-14.json).

## Suelo y pH: conclusiones y límites vigentes

- La revisión bibliográfica respalda cruzar suelo y hospedador, no una jerarquía
  universal «suelo manda siempre». Hospedador necesario no se sustituye por suelo.
- Composición de roca y reacción del suelo son dimensiones diferentes. Silíceo
  no equivale automáticamente a ácido; calcáreo no demuestra pH básico superficial.
- El agua infiltrada puede lavar carbonatos: roca caliza con horizonte superficial
  descalcificado/ácido es posible. Un pH **estimado** bajo no confirma ese proceso;
  tampoco las lluvias recientes permiten inferirlo. No convertir todas las calizas
  en terreno favorable ni excluir edulis universalmente por la roca madre.
- Edulis local ya incluye `lith_decalcified_soil` entre sus preferencias. No hay
  medición de descalcificación en La Vansa. Que allí fructifique poco o mucho no
  se deduce de las fuentes revisadas. Presencia comunicada tampoco mide el pH.
- No duplicar evidencia contando «ácido» derivado de pH además del mismo pH.
  Mantener mezclas, procedencia y desconocidos. No rellenar faltantes como neutro.
- El usuario rechaza ampliar globalmente aereus a pH máximo 7,5. Sigue en 6,8.
  No hay decisión aprobada de veto calcáreo universal para las otras especies.

[Fuentes primarias y propuesta](mushrooms/prediction-map-ecological-factors-literature-es.md)
y [matriz de 21 fichas](mushrooms/prediction-map-substrate-species-review-es.md).
Son anexos para profundizar; el alcance y decisiones necesarios están arriba.

## Qué está implementado y qué no

El mapa calcula probabilidades del **motor Python existente en preview local**,
con modelos instalados, evidencia por especie y entradas del punto. No calcula
ML en navegador ni toma prestada la evidencia del área que contiene el punto.
**Predictor por área; mapa por especie**, incluso en Olvan. La diferencia de
porcentajes ya se investigó después del precálculo del usuario; no intentar
igualarlos ni repetir esa investigación. [Informe](reports/prediction-map-olvan-after-precompute-2026-09-13.json).

Rovelló tiene cuatro filas por IDs existentes: deliciosus, sanguifluus, vinosus y
salmonicolor/quieticolor. Esto **reemplaza el grupo derivado**. Solo deliciosus
tiene modelo en las comprobaciones realizadas; no prestar su modelo a las demás.
Nombres en `metadata.map_display_name`, sin fusionar observaciones ni dividir
la ficha conjunta salmonicolor/quieticolor. Probabilidades descendentes del día;
sin cálculo al final. Cálculo disponible no significa validación científica:
`scientifically_validated=false`, `point_validation=not_established`.

**Reglas de suelo v5 conservadas en el filtro v6:** `ecology.soil_filter` de las cuatro fichas define apoyo
silíceo, lista de exclusiones vacía, caliza condicionada y requisito de composición
resuelta. Son reglas provisionales, no límites biológicos absolutos. El máximo de
aereus no se amplía: solo su ensayo previo permite una media fuera de rango con
intervalo OpenLandMap solapado y silíceo, sin componente carbonatado/yesífero que
bloquee esa excepción. Edulis/pinophilus/cibarius comparan estrictamente la media.
Las otras 17 fichas conservan sus políticas de suelo; ninguna usa meses para la
selección territorial. Preferencias y valores de afinidad no activan nuevos vetos.

Revisión ICGC aplicada: 1.055 códigos revisados, 1.046 con materiales en 192 reglas
compartidas; 14 materiales añadidos al catálogo. Nueve sin equivalencia segura:
CK, Dlva, Fd, Glpm, Org, Pze, bf, ff, mr_EÇOr. Identificar un depósito no resuelve
su composición: 392 unidades indeterminadas para silíceo/calizo/yesífero. Mezclas
sin proporciones inventadas; cuatro códigos de cubierta y cinco filas MVC
previas preservados. **GEODE siguiente fase**, no revisar/descargar otra vez ICGC.
[Revisión y hashes](reports/prediction-map-icgc-substrates-2026-09-14.json).

Catálogo y mappings locales conservan los SHA256 `applied_files_sha256` del
informe ICGC, revalidados. El hash de perfiles cambió después de v5 por edición
desde la UI a las 02:42:58 del 14/09: salmonicolor/quieticolor conserva solo
`host_abies_spp`, con metadatos actualizados. Edición preservada; comparación
estructural con backup `mushroom_profiles.20260914T004258Z.json`, que coincide
con el hash v5. No restaurar cinco afinidades anteriores. El [informe v5](reports/prediction-map-two-levels-2026-09-14.json),
con reglas antes/después y prueba de preservación de los demás campos.
Backups con sufijo `20260913T224213651843Z.icgc-substrates.keep.json` y revisión
`docker-data/mushroom-data/gis-mapping-reviews/icgc-substrates-2026-09-14.json`
conservados. No repetir la auditoría ICGC ni las descargas.

## Casos útiles para pruebas dirigidas

Los valores de la tabla son contexto histórico, no mediciones. En este incremento
se reconsultaron nueve puntos con los lectores reales para enero y septiembre:
listas territoriales idénticas, sin inferir modelos en esa comprobación geográfica.
Vallcebre mantiene latitabundus; La Selva/L’Aleixar, aereus condicionada; La Vansa,
las tres fichas condicionadas; Fogars conserva edulis; Ggd sin hosts se abstiene.
Olvan/Merlès conservan aereus y caesarea. Resultados actuales en el informe v5.

| Punto | Evidencia y resultado que interesa |
|---|---|
| Vallcebre 42.22549, 1.81417 | Latitabundus: pino rojo, 1.050 m, pH 6,9; excluida el 13/09 solo por mes (principal 10–12, secundario 1). Debe seguir posible territorialmente tras separar niveles. |
| La Selva 41.22694, 1.09095 | Pizarras `mc_Capg`, silíceo, pH 7,2 [6,7–7,8], encina/roble, 415,4 m. Aereus admitida por ensayo v4; presencia abundante comunicada. |
| La Selva 41.23675, 1.13555 | Misma unidad silícea, pH 7,5 [6,6–8,1], encina/quejigo, 357,9 m; aereus admitida con aviso. No ampliar máximo global. |
| L’Aleixar 41.22071, 1.07009 | `Ggd`, granito+granodiorita → silíceo; pH 6,9 [6,0–7,7], hosts identificados. Aereus compatible por ensayo. |
| 41.22012, 1.06989 | `Ggd` ya mapeado, pero polígono MFE «No arbolado», códigos cero. Vecino con pino/encina/quejigo a 52,09 m. Sigue absteniendo por terreno; no fallo geométrico. |
| La Vansa 42.27588, 1.52460 | `PPcm`, lutitas+caliza, pino rojo, 1.663,7 m, media 6,3 [5,2–7,3], SoilGrids superficial 6,1. Edulis, pinophilus y cibarius: admisión condicionada desde v5. Caliza cartografiada no confirma carbonatos superficiales/descalcificación. |
| Fogars 41.77528, 2.46480 | Haya recuperada tras arreglo geométrico MFE, edulis compatible. Regresión para no volver a perder árboles. |
| Olvan 42.06282, 1.93765 y Merlès 42.01347, 1.97098 | Setales de aereus/caesarea comunicados. Mantener selección por especie y OpenLandMap; no ajustar modelos para igualar el Predictor de áreas. |

Informes específicos en `docs/reports/prediction-map-{vallcebre-latitabundus,
ggd-missing-hosts,ggd-mapping,vansa-calcareous,...}-2026-09-*.json`.
La reparación MFE acotada en memoria recuperó árboles en Fogars y Arbúcies;
fuentes/índices intactos. **Árboles vecinos aún no implementado**: usuario lo ha
solicitado; concretar criterio/radio antes de trasladar información y mostrar
procedencia/distancia. No confundirlo con vecino de pH, que sí existe hasta 1 km.

## Datos, archivos y ejecución

- Autoridad: `docker-data/mushroom-data/mushroom_profiles.json`,
  `mushroom_reference_catalogs.json`, `mushroom_gis_mappings.json`. Son los datos
  de trabajo, **no las semillas** `mushroom-data/`. 21 fichas/21 rangos de pH,
  115 hosts. Preservar ediciones del usuario: edulis mínimo **900 m**,
  pinophilus **1.100 m**, no restaurar 600 m.
- UI única **Terreno**. Ectomicorrícicas exigen hospedador específico compatible;
  jerarquía de género admite descendientes, no equivalencia entre hermanos.
  No ectomicorrícicas pueden entrar por hábitat revisado (prado, ribera, bosque).
  Falta de árboles/hábitat significa desconocido, nunca ausencia física demostrada.
- OpenLandMap media 0–30 cm para filtro, límites Q16–Q84 informativos; nueve TIFF
  (368 MiB) en `mushroom-map-GIS/openlandmap-ph/spain-v20250204/manifest.json`.
  Profundidad solo en desplegable Terreno; SoilGrids conservado para comparación
  y retención hídrica. Sin media, vecino hasta 1 km y distancia; sin vecino,
  desconocido. No fallback silencioso a SoilGrids ni nuevas descargas.
- Preview recargada con los mismos argumentos y puerto; API v6 comprobada:
  `http://127.0.0.1:65517/protected/prediction-map/index.html`.
  No asumir que sobreviva ni reutilizar PID antiguo. Sesión ficticia, sin autenticación real.
  Entrada: `tests/prediction_map_browser_check.mjs --preview`, lectores en
  `tests/prediction_map_preview_reader.mjs`. Configuración de esta ejecución en
  `/private/tmp/rainmapper-map-point-executor-config.json` (temporal, no autoridad).
- GDAL usa `/opt/homebrew/bin/python3`; motor/meteorología `.venv/bin/python`
  **sin resolver el symlink**. Datos observados `docker-data/Data`,
  `docker-data/stations.txt`, `PublicData`. Modelos en
  `docker-media/rainmapper/mushroom-derived/ml_models`; registro local
  `docker-data/mushroom-data/mushroom_ml_version_registry.json`.
- GIS: `mushroom-map-GIS/terrain-index/point-inputs-2026-09-12.sqlite`, índice MFE
  `mushroom-map-GIS/mfe25/prepared/catalunya-point-index-v2-2026-09-13.sqlite`,
  geología ICGC `mushroom-map-GIS/icgc-geologia-50000/source/geologia-territorial-50000-geologic-v3r0-202412.gpkg`,
  cubiertas `mushroom-map-GIS/icgc-cobertes-2024/source/cobertes-sol-v1r0-2024.gpkg`,
  municipios `mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg`,
  SoilGrids `mushroom-map-GIS/soilgrids-shared`, DEM nacional
  `mushroom-map-GIS/ign-mdt25`, regional `mushroom-GIS`. Ya preparados; no reconstruir.
- Código del incremento: `rainmapper_core/mushroom_map_ecology.py`,
  `mushroom_map_model_runtime.py`, `mushroom_prediction_map.py`,
  `viewers/prediction-map/` y textos ES/CA/EN en `mushroom-data/mushroom_labels.json`.
  Ejecutores: `mushroom_map_execution.py`, `mushroom_map_prediction.py`;
  script de modelo `scripts/prediction-map-local-model.py`.
- Pruebas: `tests/test_mushroom_map_ecology.py`,
  `test_mushroom_map_model_runtime.py`, `test_mushroom_prediction_map.py`,
  `test_mushroom_map_prediction.py`; datos locales opt-in en
  `test_mushroom_map_local_mappings.py`. Cubren invariancia por fecha, fenología
  preservada, cero llamadas para incompatibles y orden filtro→entradas del modelo.

## Validación, riesgos y siguientes fases

Último ajuste de UI: prueba Chrome escritorio/móvil correcta con suelo antes de
árboles, motivos de descarte en líneas propias y sin desbordamiento horizontal.
Comando: `node tests/prediction_map_browser_check.mjs /private/tmp/rainmapper-maplibre-4.7.1.js /private/tmp/rainmapper-maplibre-4.7.1.css`.
Capturas de esa ejecución: directorio temporal `prediction-map-browser-gI2mPH`,
incluida `exclusions-mobile.png`, inspeccionada visualmente. La preview sirvió JS/CSS
idénticos a los archivos actuales, sin reinicio ni cambios de filtros.
Este cierre documental no repite pruebas ejecutables: revisión y `git diff --check`.
Las pruebas siguientes son evidencia de sus respectivos incrementos, no una nueva
ejecución ni aceptación de Safari/iPhone, HA–worker o precisión científica.

V6 actual: **106 pruebas correctas**, incluyendo regresión del Predictor, datos
locales, salida temprana estacional y semana que cruza el mes sin inferir en días
fuera de temporada. Chrome: ocultación diaria, etiquetas principal/secundaria,
cero/null, móvil y ruta meteorológica correctos. Preview recargada en 65517 con
los mismos argumentos; API Cercs verifica marçot fuera/sin modelo invocado,
fredolic secundario sin modelo y edulis principal. Perfiles, catálogo y mappings
mantienen hashes v5. [Informe](reports/prediction-map-season-visibility-2026-09-14.json).

Validación histórica del código v5: **67 pruebas dirigidas correctas**, incluidas nueve
contra JSON locales; otras **369 pruebas de regresión, 12 omitidas**, resultado OK.
Chrome escritorio/móvil: fecha, orden, cero/null, motivos, ruta meteorológica y
permisos simulados correctos. Nueve puntos × dos fechas mediante lectores GIS
actuales. API real de preview en La Vansa: edulis/pinophilus calculadas y cibarius
con abstención/null. Ninguna de estas comprobaciones acredita precisión científica.
Comandos, resultados, tamaños de payload y huellas del código en
[el informe v5](reports/prediction-map-two-levels-2026-09-14.json).

La integración está ahora en preview y HA local/worker existente, con el alcance
de la aceptación registrado arriba. HA real no ha recibido este bloque. Pendientes:
completar GIS nacional, destino físico independiente/AMD64, medición IO físico y
rendimiento representativo, revisión visual/Safari aplazada y superficie coloreada.
Mantenedores legacy de mappings agrupados y 37 cubiertas pendientes. Vinosus
mantiene contradicciones documentadas; no corregirlo silenciosamente.

No runners, entrenamiento, precálculo, publicación HA real, Tailscale,
autenticación real de preview, cambios de coordinador ni borrado de datos/backups.
Preservar URLs antes/después de cualquier operación futura autorizada del worker.
Los builds/recreaciones locales de este incremento sí fueron autorizados.
No repetir descargas, auditorías o migraciones terminadas. RPi4 compartida:
límites acotados, sin fuerza bruta ni artefactos grandes por punto/día/modelo.
Continuar informando brevemente al menos cada minuto. Antes de implementar,
resumir al usuario lo entendido y el incremento concreto; no pedir confirmaciones
rutinarias sobre trabajo ya autorizado.

Worktree ampliamente modificado, con archivos nuevos sin seguimiento y cambios
previos en `mushroom-data/mushroom_observations.json`. No atribuir todo el diff a
esta sesión ni incluirlo ciegamente en commit. Cierre sin commit/push ni despliegue.
Incidencia Barcelona corregida anteriormente en catálogos local/HA real, Erinya
pendiente de la fuente; reglas de coordenadas documentadas, sin runner nuevo.
[Registro](reports/weather-coordinate-conflict-2026-09-13.json).


## Documento archivado: todo.md

# TODO

Prioridades al cierre del **15/09/2026**. Arranque suficiente:
`codex-start-here.md` + `active-context.md`. Esta lista amplía tareas;
[especificación central](mushrooms/prediction-map-specification-es.md) = diseño.

## Pendiente aplazado — revisión de suelos GIS (16/09/2026)

- [ ] Retomar la justificación de los **343 códigos pendientes** de
  `geology_50000`: **331 sin investigación específica suficiente** y **12 con
  investigación específica y limitación documentada**, aún no necesariamente
  irresolubles. Hay **145 aceptados** de la tanda de 488, incorporados a HA
  local; el usuario comunica que ha subido los dos JSON a HA real. Seguir la
  [guía breve de revisión](mushrooms/gis-soil-review-method-es.md) y revalidar el
  [estado y las evidencias](gis-review-2026-09-16.md) antes de continuar.
  Aceptar solo lo justificado; no contar una comprobación genérica como revisión
  final ni modificar las 567 clasificaciones anteriores sin investigación.
  **Aplazado expresamente por el usuario; no continuar ahora.**

## P0 — Mapa de predicción: cerrar aceptación local y concretar integración

### Consolidación geográfica solicitada — revisión del 15/09

- [x] Inventariar las tres carpetas de HA y cruzar manifiestos/cachés del worker
  sin rehashear GiB. Duplicación worker 5,54 GB; ahorro potencial HA 5,74 GB, con
  límites de evidencia explícitos. [Diseño](mushrooms/shared-geography-consolidation-es.md).
- [x] Implementar almacén geográfico público común por SHA y vistas por consumidor;
  reutilizar el dataset GIS de reconstrucción y la publicación del mapa. Adaptar
  hashes/recibos, lectores sensibles a rutas/mtime y transporte incremental fuera
  del clic. Mantener autoridad HA, permisos por coordinador y contextos científicos.
- [x] Adopción y limpieza local: paridad GIS/mapa, circuito científico completo,
  imágenes finales verificadas y reinicio sin transporte/hash. Worker libera
  5,46 GB; versiones/punteros preservados.
  [Informe](reports/shared-geography-acceptance-2026-09-15.json).
- [x] Copiar y verificar en HA real el mapa y solo el delta GIS faltante, sin
  mover/borrar originales ni activar código. Entradas bajo `geography/imports`.
- [x] Sustituir la adopción al primer arranque por archivos ordinarios y manifiestos
  portables preparados previamente. Validado localmente sin red y media read-only.
- [x] Colocar y verificar las copias en las rutas definitivas de HA real.
  Originales conservados; sin comandos ni enlaces al instalar.
  [Informe portable](reports/shared-geography-portable-2026-09-15.json).
- [ ] Tras actualizar HA real, probar el circuito con sus datos y comprobarlo antes
  de que el usuario retire originales. [Guía](mushrooms/shared-geography-consolidation-es.md).

### Candidata local validada — 15/09

- [x] Aplicado a imágenes y contenedores locales: reconstrucción/entrenamientos
  en background junto al precálculo. Smoke 1565/48; paridad de código 193/101
  archivos HA/worker. HA real antiguo conserva su reparto hasta actualizarlo.
  [Informe y límites](reports/worker-background-chain-2026-09-15.json).

- [x] Aplicar/verificar localmente mapa unificado en URL habitual y permiso
  `can_use_prediction_map` por usuario para cualquier rol; autenticación y
  ajustes del visor compartidos. Reconstruido en ambas imágenes, verificado en
  contenedores y consultas reales con usuario básico; smoke 1552/48 y navegador OK.
- [x] Conectar datos privados del mapa a caché sincronizada del worker y probar
  sin montajes privados compartidos. Validado en imágenes locales, seis consultas
  con paridad exacta. [Evidencia y límites](mushrooms/prediction-map-private-cache-es.md).
- [x] GIS/DEM/OpenLandMap preparados con autoridad en `/media` de HA, publicación
  geográfica versionada y caché incremental del worker sin `/maps`. Transferencia
  real de 14,54 GB; reinicio sin transferencia/rehasheado. Cambios, reanudación y
  limpieza probados. Circuito operativo local completo y seis consultas idénticas;
  smoke 1581/48. [Informe](reports/prediction-map-geography-2026-09-15.json).
- [x] Preparar candidata HA 0.2.304 / worker 1.1.2 y paquete GIS con hashes;
  imágenes locales arm64 y fuentes recuperables en `backups/ha-map-candidate-20260915/`.
- [x] Aceptación del usuario y publicación multiarch HA 0.2.304: tags de versión
  y latest con mismo digest, amd64/arm64 verificados el 16/09/2026.
  [Release](reports/ha-release-0.2.304.json).
- [ ] Instalación y aceptación en HA real por el usuario: usar geografía ya
  preparada, probar permisos de predicción, worker y Safari/iPhone; preservar
  datos privados y originales hasta validar. [Guía vigente](mushrooms/shared-geography-consolidation-es.md).
- [ ] Prueba iPhone: acceso local restringido al visor, o tras aceptación y
  publicación explícita de HA real; no abrir administración local a la Wi‑Fi.

### Completado; no rehacer

- [x] Edición de afinidades: «-» elimina solo su fila; añadir filas en V0/Enriched,
  preservando metadatos y filas ocultas. Pruebas dirigidas y navegador local
  correctos. Recuperados los dos pinos de Fredolic desde backup, sin reponer
  el abeto blanco ni cambiar otros campos. Aplicado a HA local.

- [x] Tooltip inmediato por fecha en gráfica semanal, con todas las especies y
  colores del día, evitando acertar en curvas solapadas. Ratón/teclado y ausencia
  de valores probados; sin nuevas consultas. Aplicado en HA local.
- [x] Colores contrastados asignados solo a especies con curvas calculadas,
  estables durante la semana y compartidos con la lista. Regresión de tres curvas
  próximas entre 21 especies comprobada en navegador; aplicada en HA local.
- [x] Consultas del mapa comparten canal online/foreground con trabajos online;
  background independiente, máximo dos cálculos globales. Ocupado y desconectado
  diferenciados y aviso inicial experimental corregido. Validado/aplicado local.
- [x] Ayuda de suelo/pH en Ecología → Suelos, ES/CA/EN, con explicación de
  afinidades frente a apoyo, admisión condicionada y bloqueo de excepciones.
  [Guía](mushrooms/soil-ph-rule-help-es.md); aplicada y comprobada en HA local.
- [x] Especificación central, dos rutas del mismo MapLibre y extensión opcional.
- [x] Botón diana/dardo bajo IDW, modal cancelable y popup anclado; clic/hover
  sobre estación conserva meteorología. Terreno detallado desplegable.
- [x] Preview local sin autenticación real; ajustes temporales aislados. Grupo
  Predicción local/worker; persistencia con los demás ajustes diseñada/probada.
- [x] Municipio IGN nacional opcional, DEM/pH por ventanas, cubiertas/geología
  ICGC, arbolado MFE Catalunya y nombres/alias del catálogo local conectados.
- [x] Geometrías grandes resueltas mediante auxiliares preparados, sin elevar
  límites ni modificar originales. No reconstruir auxiliares por consulta.
- [x] Meteorología observada hasta 60 días en popup; viento opcional identificado
  de estación. Lecturas residentes y huecos explícitos.
- [x] Ampliación/revisión local de hosts y alias, conservando entradas del usuario;
  115 hosts tras añadir Eucalyptus. Promoción pendiente.
- [x] Revisión de literatura de 21 fichas y segunda pasada. Ventanas amplias
  aplicadas localmente: meses/hosts/hábitats/altitud, manteniendo procedencia.
- [x] `ecology.ph_min/ph_max` en mantenimiento, JSON, importación/guardado y
  validación; 21 rangos provisionales aplicados y revisables.
- [x] Filtro residente de hosts/meses/altitud y pH opcional conectado a preview.
  Padre de género ↔ especie admitido, hermanos específicos no equivalentes.
  Sin hosts, las fichas no ectomicorrícicas pueden entrar por hábitat revisado.
- [x] `PointExecutor`, broker efímero/canal remoto y adaptador semanal
  `resolve_species_week` preparados y probados aisladamente, sin activación remota.
- [x] Adaptadores de retención puntual y preparación hídrica/meteorológica 90/365
  usando rutinas existentes, ya conectados al motor del visor.
- [x] Último filtro v4: 67 pruebas dirigidas, API y Chrome según informe ICGC.
  Validación de esa revisión, no reejecutada durante el cierre documental;
  no equivale a Safari/iPhone ni a paridad de contenedores/release.

### Continuación inmediata, en este orden

- [ ] Tarjeta de worker: mostrar actividad de ambos carriles, para que «En espera»
  del primer plano no oculte precálculo de background en otro coordinador.

Decisión posterior del usuario: revisión visual a fondo/Safari y árboles vecinos
quedan aplazados en este TODO. Incremento autorizado ahora: volumen/configuración
portables y comparación del cálculo en HA local y el worker existente, conservando
sus coordinadores. Sin publicación HA real. La autorización autónoma posterior permitió el circuito
local de entrenamiento/precálculo, ya completado: no repetirlo.

- [x] Inventario y clasificación de materiales ICGC — registro histórico:
  1.055 códigos inventariados, 1.046 con materiales en
  192 reglas compartidas, 14 materiales nuevos; nueve sin equivalencia segura.
  Catálogo/mappings/perfiles locales respaldados. Mezclas preservadas; reconocer
  un depósito no demuestra su composición. GEODE aplazado. Informe
  `prediction-map-icgc-substrates-2026-09-14.json`. Esto no acredita una revisión
  completa de los tipos de suelo; sus pendientes están en la tarea del 16/09.
- [x] OpenLandMap pH España local: nueve TIFF, 368 MiB; media para selección,
  límites informativos y comparación SoilGrids, profundidad solo en Terreno.
  Vecino de pH hasta 1 km con distancia. No repetir descarga.
- [x] Matriz de suelo/pH de 21 fichas; ensayo configurable solo en aereus, máximo
  6,8. Silíceo+solapamiento puede admitir media superior, salvo mezcla con
  carbonatos/yeso; sin nuevos vetos universales ni cambios en otras 20 fichas.
- [x] Bibliografía contrastada: hospedador/suelo, roca vs horizonte superficial,
  lavado/descalcificación y separación entre presencia y fructificación.
  `prediction-map-ecological-factors-literature-es.md` contiene fuentes y propuesta.
- [x] Dos niveles y descarte antes de inferencia implementados; v6 añade temporada
  a la selección de cálculo/visibilidad, conservando el estado territorial separado.
- [x] Hábitats no ectomicorrícicos sin árboles, admitidos por el usuario; hosts
  específicos conservados. Coherencia de instantáneas forestal/ecológica,
  74 pruebas Python y Chrome. UI única Terreno y suelos posibles sin vetos.
- [x] Decisión posterior Rovelló: cuatro filas por ID existente, nombres distintos,
  probabilidades propias y sin grupo derivado. Observaciones intactas; sin modelos
  prestados entre especies. Salmonicolor/quieticolor sigue unido.
- [x] Conectados modelos/evidencia sellada y entradas puntuales al motor Python
  compartido: `PointExecutor` y preview. Sin inferencia en navegador.
- [x] Contrato/UI/broker en modo real, sin IDs demo; lista por probabilidad
  descendente del día, null al final y cero preservado.
- [x] Continuidad semanal, corte común, vetos y fallback probados; materialización
  perezosa equivalente al modo completo. Pruebas dirigidas y Chrome correctos.
- [x] Corregido MFE con geometría candidata inválida: recuperación en memoria
  conservando área, originales y límites; 12 pruebas y tres puntos reales.
- [x] Decisión cerrada tras comparar Olvan: Predictor por área; mapa por especie
  con entradas del punto, incluso dentro de áreas conocidas. No añadir selección
  territorial al mapa ni igualar porcentajes. Implementación actual conservada.
- [x] Retirar meses del filtro de especies posibles (v5 local). Conservar
  fenología en las fichas para el predictor; ajustar contrato/consumidores y textos
  «compatibles para esta fecha». Estado territorial independiente de fecha.
- [x] Decisión posterior v6: fuera de temporada no aparece ni invoca modelos.
  Las visibles muestran principal/secundaria según la ficha. 106 pruebas y Chrome.
- [x] Cabecera Terreno: suelos antes de árboles/hábitats, con etiquetas de mappings.
  Descartadas con nombre y motivos en líneas separadas; Chrome escritorio/móvil.
- [x] Decisión final de suelo/pH: conservar reglas actuales. Rechazada restricción
  adicional por litología; Montclar documentado como contraejemplo, sin editar datos.
- [x] Selección antes del modelo/contexto hídrico y salida temprana sin candidatas.
  Prueba de **cero llamadas al modelo para descartadas**, no solo ocultación UI.
  Compatibles sin modelo al final, null distinto de cero; abstención conservada.
- [x] Primer bloque de reglas explícitas suelo+pH por ficha: aereus,
  edulis, pinophilus y cibarius. Distinguir preferencias/requisitos/tolerancias,
  caliza cartografiada/descalcificación e incertidumbre. No veto universal por
  caliza ni pH inventado desde roca. Cada ajuste con motivo y caso esperado.
- [x] Pruebas funcionales de Vallcebre (fecha), La Selva/L'Aleixar (aereus y silíceo), La Vansa
  (caliza+pH ácido estimado), Olvan/Merlès y regresión forestal de Fogars.
  Motivos de exclusión/admisión condicionada visibles sin alterar porcentajes.
  Nueve puntos con lectores reales × enero/septiembre y API La Vansa; ver informe v5.
- [ ] Concretar recuperación forestal vecina solicitada, con criterio/radio y
  distancia/procedencia. **Aún no implementada**; el vecino de pH no la sustituye.
- [ ] Revisar contradicciones de vinosus y completar reglas del resto de fichas
  después de validar el primer bloque; conservar la ficha conjunta de Rovelló.
  Revisión pendiente, no autorización para reabrir ahora suelo/pH ni endurecer vetos.
- [ ] Validar porcentajes y compatibilidad frente a setales conocidos con las
  fichas actuales. No confundir validación funcional con transferencia científica.
- [x] Comparación del cálculo completo en HA local y worker existente: resultados,
  generaciones, primera consulta/repetición, concurrencia, tiempos totales/cálculo
  y memoria cgroup registrados. No extrapolar tiempos del Mac a RPi4.
- [ ] Ampliar mediciones representativas de cola/transporte/render, RAM incremental
  e IO físico en destino. No usar tiempos del lector como benchmark de predicción.

Incidencia anterior del runner: Barcelona corregida en catálogo local/HA real,
con backups y mediciones conservados. Regla de saltos con destino en España
aproximada (incluidas islas) implementada, sin desplegar código ni relanzar runner.
Erinya espera corrección de la fuente por decisión del usuario.
Ver `reports/weather-coordinate-conflict-2026-09-13.json`.


## P1 — Integración operativa del mapa, posterior al cálculo local

- [x] Consolidar cambios puntuales en imágenes reproducibles HA local/worker,
  recrear y verificar código efectivo, preservar datos/coordinadores y respaldar
  source/configuración. Completado 15/09; 1.551 tests (48 omitidos), navegador y
  paridad real. No equivale a release HA real ni a validación científica.
- [x] Corregir el desfase de medianoche y exponer zona horaria en Parámetros →
  Predicción, con ayuda ES/CA/EN, persistencia por dispositivo y transporte
  explícito HA–worker. Fecha inicial independiente del navegador; zona en cabecera.

- [x] Nombres forestales por idioma en el mapa: `ForestReader` entrega ES/CA/EN
  desde el catálogo local (115 hospedadores completos). Selector comprobado en
  navegador sin nuevas consultas; trece pruebas GDAL correctas. Aplicado en HA
  local/worker, coordinadores conservados; incorporado a ambas imágenes el 15/09.
  Los nombres de especies siguen las ediciones de sus fichas.
- [x] Exponer los siete campos de la regla conjunta suelo/pH en Ecología → Suelos
  (V0/Enriched) y nombre específico del mapa en Metadatos. Validación de guardado
  con catálogos locales, sin modificar los valores actuales. Pruebas dirigidas y
  controles de HA local comprobados en navegador escritorio/móvil, 14/09.
- [x] Volumen portable de lectores actuales, configuración y canal remoto activados
  en HA local y worker existente. Paridad de dos puntos, repetición/concurrencia,
  cancelación y worker desconectado sin fallback; URLs conservadas por hash.
  [Informe](reports/prediction-map-local-worker-integration-2026-09-14.json).
- [ ] Completar paquete **nacional**: integrar GEODE y MFE fuera de Catalunya,
  usando las descargas existentes. 14,54 GB actuales no son España completa;
  no recortar territorio. Índices/normalización y mappings aún necesarios.
- [x] Autenticación real y preferencias con los demás ajustes de dispositivo;
  retirar adaptación de preview al integrarla. Permisos UI/API y revocación.
- [x] Conectar mapa del worker a las generaciones privadas de su asociación,
  reutilizando sincronización y caché existentes. Probado con HA local sin
  montajes privados; despliegue RPi4 pendiente. No sustituir sus datos por el Mac.
- [x] Minimizar transporte del mapa: referencias compactas y cero descarga de
  objetos/manifiesto completo en clic con versiones ya verificadas; reutilizar
  meteorología del precálculo y fichas sin cambios. Sincronizar solo archivos o
  particiones ausentes/modificados, incluir catálogos/mappings necesarios y no
  invalidar datos iguales por editar una ficha. Fijar versiones por consulta,
  deduplicar preparación concurrente y preservar autorización por asociación.
  Validar cambio de ficha, meteorología incremental, reinicio y caché caliente;
  medidos bytes de control y objetos aparte. [Contrato y pruebas](mushrooms/prediction-map-private-cache-es.md).
- [ ] Ampliar regresión de estilos/gestos, Safari/iPhone y convivencia con mapa
  meteorológico. No cambiar comportamiento de la ruta meteorológica actual.
- [ ] Antes de integración GIS general, adaptar mantenimiento/consumidores legacy
  al bloque `exact_value_mapping_groups`; el mapa y validador ya lo leen.
- [ ] Promover explícitamente catálogo/fichas/mappings locales al repo y HA cuando
  estén aceptados. Preservar datos originales y ediciones concurrentes.
- [ ] Preparar volumen portable con GIS/DEM/SoilGrids/municipios e índices:
  imagen de arquitectura compatible + datos/manifiesto/instalador, destino limpio,
  reinicios/actualizaciones y coordinador intacto. No reconstruir desde HA real.
  Base actual instalada por enlaces, copia/reanudación probadas con fixtures;
  falta cierre nacional, máquina independiente y AMD64. ARM64 local comprobado.
- [ ] Ampliar normalización MFE25 a otros esquemas/regiones e índice GEODE cuando
  se amplíe ámbito; no bloquear Catalunya por completar todo el país.
- [ ] Auditar escala/incertidumbre útil de estaciones/IDW y transferencia del
  modelo a ubicaciones nuevas, sin prometer precisión meteorológica a metros.
- [x] Decisión RPi4: cálculo del mapa en worker en principio; HA coordina/entrega.
  Sin fallback local. La comparación con HA local comprueba paridad, no decide
  dónde calcular en producción ni extrapola rendimiento a la Raspberry.
- [ ] Solo si se solicita release: reconstrucción HA local/worker del mismo
  código, circuito local aplicable y aceptación expresa antes de HA real.
- [ ] Superficie coloreada por zona visible: ampliación separada a concretar;
  el clic/informe puntual no implica precálculo de todos los puntos de España.

## P2 — SoilGrids y enriquecimiento general, sin desplazar el mapa

- [x] Descargas/auditoría terminadas: 54 retenciones + nueve pH, 7.119 pares
  tesela/capa; huecos aceptados. No repetir sin motivo nuevo.
- [x] Diseño compartido RPi4: índice, ventanas, caché y concurrencia acotadas,
  sin hashes completos/proceso por capa en cada consulta; reparto HA/worker.
- [x] Lectores candidatos puntuales DEM/pH/retención y controles locales;
  esto no completa la migración de agregados/consumidores antiguos.
- [ ] Migración compatible para altas/cambios de áreas/microáreas y consumidores:
  CRS/NoData, ediciones, referencias antiguas y deltas sin perder ediciones.
  No interpretar todo cero de retención como NoData.
- [ ] Preparación remota previa al snapshot, réplicas de datos y aceptación de
  deltas en HA; medir RAM/IO/latencia y agregado de polígonos en RPi4.
- [ ] Concretar enriquecimiento en Setales/observaciones: pH geográfico,
  profundidad/incertidumbre/procedencia y agregación, preservando anotaciones.
  Separar mostrar datos, migrar almacenamiento y cambiar variables de modelos.
- [ ] Cambiar referencias solo tras validación. Caché antigua y backups se
  conservan; 30 días fue propuesta, no permiso de borrado automático.
- [x] 21 rangos de pH provisionales ya aplicados por decisión del usuario.
- [ ] Revisar esos rangos/ventanas ante evidencia nueva sin restaurar versiones
  antiguas ni ampliar globalmente aereus a 7,5, opción rechazada por el usuario.
- [ ] Francia: vegetación/ecología y geología aplazadas; municipios opcionales.
  DEM/SoilGrids comprobados puntualmente no acreditan ecología disponible.
- Referencias: diseño del lector y reparto en `mushrooms/`; detalles/inventarios
  históricos en [snapshot archivado](reports/session-context-before-close-2026-09-13.md).

## Pendientes conservados — Predictor y ciencia, no prioritarios frente al mapa

- [ ] Aplicabilidad multiespecie, caso Rovelló / Els Ports / 2026-09-07:
  diferencia absoluta/normalizada/dirección, sin tolerancia global inventada.
- [ ] Probabilidad vetada solo diagnóstica; distinguir sin modelo de modelo vetado.
- [ ] Catálogo explícito de especies posibles por área.
- [ ] Sustituir Historial por evaluador persistido hold-out; precálculo no incluye history.
- [ ] Mensajes distintos para reentrenamiento, precálculo, cobertura y corrupción.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando hold-outs externos
  tengan ambas clases. Auditoría de días secos cerrada: no cambiar contador/modelos.

## Pendientes conservados — Operación

- [ ] CLI del worker por `coordinator_id`, manteniendo otros destinos.
- [ ] Medir transferencia/hash/escritura/fsync/promoción antes de streaming RPi4.
- [ ] Runner meteorológico externo y AWS/servidor doméstico: futuro, no migrar ahora.
- [ ] GIS/DEM de microáreas francesas desde UI al retomar ese trabajo y Meteo-France
  frente a Wunderground; revalidar versión HA entonces.
- [ ] Confirmar si faltan controles visuales de contadores y runner mensual
  Wunderground; no repetir lo ya acreditado para la misma revisión.
- [x] HA real `0.2.303` confirmado instalado/funcionando por el usuario.
- [x] Selección semanal `lag_event` h1–h7 y fallback diario existentes conservados;
  meteorología observada del Predictor y aviso final del worker corregidos anteriormente.

No se autoriza ningún trabajo, borrado, cambio de coordinador ni publicación
por figurar en esta lista. El próximo bloque autorizado es la implementación local.
