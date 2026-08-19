# TODO

Prioridades vigentes. El estado inmediato está en `docs/active-context.md`;
este fichero distingue trabajo cerrado de próximas entregas.

## P0 — Separar entrenamiento operativo y benchmark científico

- [x] Documentar la propuesta, UI objetivo, promoción y entrega por fases en
  `docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`.
- [x] Acordar que la separación no cambia el V2 operativo: seguirá activo hasta
  que el usuario promocione explícitamente una generación compatible.
- [x] Acordar dos acciones principales: `Reconstruir y reentrenar operativo` y
  `Ejecutar benchmark científico`; `Ver comparación` será contextual al job.
- [x] Mapear con Codebase Memory la cadena externa y
  `mushroom_local_full_update`, incluidos planificación, transporte,
  instalación, promoción, rollback y UI.
- [x] Introducir identidades separadas para job operativo y benchmark.
- [x] Resolver el plan operativo desde la generación activa; inicialmente debe
  producir todo V2 fixed/lag requerido por el Predictor.
- [x] Retirar V3–V6 de la reconstrucción habitual sin borrar sus contratos,
  generaciones ni capacidad de reproducción.
- [x] Mantener el job V2–V6 actual como benchmark manual independiente, sin
  promoción automática.
- [x] Añadir tests que demuestren continuidad del V2 instalado, completitud,
  frescura, fallo/rollback y paridad entre worker y ejecutor HA local.
- [x] Adaptar UI y labels `en/es/ca` solo después de cerrar el backend.
- [x] Ejecutar pruebas dirigidas, smoke completo y `git diff --check`.
- [x] Detenerse antes de release y pedir autorización explícita.

## P1 — Informe persistente y benchmark seleccionable

- [x] Persistir selección, snapshot, plan, métricas, predicciones hold-out y
  artefactos de cada benchmark.
- [x] Medir duración por fit, versión, perfil y estimador. Falta ejecutar un
  benchmark nuevo para atribuir los 40 minutos observados con esta telemetría.
- [x] Añadir `Ver comparación` e historial de benchmarks.
- [x] Mostrar por especie/contrato/horizonte/estimador Brier, prevalencia,
  delta emparejado, ROC-AUC, calibración, soporte, fallos y duración.
- [x] No crear Brier medio entre especies ni declarar un ganador universal.
- [x] Permitir seleccionar versiones/perfiles compatibles sin que el benchmark
  modifique el Predictor.
- [x] No preseleccionar perfiles, conservar la selección lanzada y evitar que un
  benchmark V3 prepare o evalúe V4–V6.
- [x] Añadir cancelación cooperativa del benchmark HA local.
- [x] Conservar en la fila terminada los perfiles exactos y contadores del
  informe; usar `Ver informe` para uno, `Ver comparación` para varios y
  refrescar el historial al terminar.

## P1 — V3 physical / V3+

- [x] Registrar un perfil/feature set nuevo; no modificar los bundles V3 core.
- [x] Mantener idénticas filas, targets, splits, contratos y estimadores de V3.
- [x] Añadir únicamente balance hídrico y SMI derivados causalmente del mismo
  IDW, con paridad entrenamiento/inferencia.
- [x] Ejecutar en HA local la comparación real V3 core frente a V3+ físico
  sobre soporte emparejado: 216/216 fits correctos y 0 fallos.
- [ ] Solo si el bloque físico mejora repetidamente, comparar después
  `+balance`, `+SMI` y `+balance+SMI`.

## P1 — Promoción genérica desde benchmark

- [x] Documentar el contrato genérico de perfil, candidata, generación completa,
  gates y rollback en
  `docs/mushrooms/mushroom-ml-generic-profile-promotion-plan-es.md`.
- [x] Materializar en código qué artefactos constituyen una generación
  operacional completa para cualquier perfil elegible.
- [x] Exigir `operational_eligible`, integridad, compatibilidad, paridad y
  entradas vivas coincidentes.
- [x] Añadir promoción humana explícita, transaccional y con rollback desde el
  informe; nunca promocionar una celda aislada elegida retrospectivamente.
- [x] Implementar el primer objetivo como versión completa `biology_v3`, con
  V3 core y V3+ físico instalados y visibles conjuntamente en Predictor.
- [x] Reconstruir HA local con autorización y validar que el informe V3/V3+
  ofrece `Preparar candidata completa`.
- [ ] Ejecutar candidata, promoción, cuatro salidas fixed/lag y rollback desde
  la UI.
- [x] Hacer que el entrenamiento habitual resuelva dinámicamente todos los
  perfiles de la versión promovida.
- [ ] Para V4–V6, declarar qué conjunto completo de perfiles es técnicamente
  operativo antes de habilitarlo. V3 y V3+ ya son elegibles conjuntamente;
  V4–V6 todavía no.

## P2 — Ventanas y coste científico

- [ ] Conservar V5/V6-365 como controles reproducibles.
- [ ] Separar el spin-up necesario para SMI de la ventana predictiva.
- [ ] Si la comparación física aporta señal, evaluar V5-30/60/90 sobre las
  mismas filas y splits; estudiar V6 después sobre ventanas justificadas.
- [ ] Mantener estos experimentos fuera de la reconstrucción habitual.
- [ ] No ensayar ensemble salvo que se materialice y supere al mejor miembro
  individual por especie y contrato.

## P2 — Worker multicoordinador

- [x] Documentar el diseño en
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- [ ] Implementar migración atómica de asociaciones, máximo configurable,
  heartbeats independientes, slot global, arbitraje justo y aislamiento por
  coordinador/job.
- [ ] Probar primero con dos HAs locales aislados. No modificar el worker M1 ni
  HA reales sin autorización.

## P2 — Datos y meteorología

- [ ] Incorporar las cuatro salidas negativas recientes cuando la plataforma
  esté alineada y crear un snapshot nuevo; no sobrescribir
  `mushroom-ml-snapshot-20260816`.
- [ ] Validar en producción la autocuración meteorológica en una entrega
  independiente.
- [ ] Revisar el umbral especial de soporte IDW de lluvia.
- [ ] Corregir el matching geológico por subcadena (`gres`/`negres`) antes
  de usar esos proxies.

## P3 — Integridad y privacidad

- [ ] Revisar por separado la privacidad de
  `mushroom-data/mushroom_observations.json`, rastreado en el repositorio.
- [ ] Añadir sanity checks confirmables para temporada, altitud y primera
  observación especie-área/microárea.
- [ ] Auditar identificaciones automáticas antiguas potencialmente
  contaminantes.

## Trabajo cerrado que condiciona el P0

- [x] V2 usa meteorología IDW común; el comparador legado de estación única ya
  no suplanta su tarjeta.
- [x] MapLibre cuenta ceros finitos en el soporte IDW y excluye N/A.
- [x] V5/V6 v2 consumen IDW, ET0, balance y SMI con paridad de inferencia.
- [x] El worker reutiliza por SHA-256 los modelos que acaba de entrenar y evita
  volver a descargar el runtime completo.
- [x] `lag_event` operativo vuelve a cubrir h1..h7 sin multiplicar fits.
- [x] HA `0.2.261` fue publicada y worker privado local `1.0.14` construido.
- [x] El batch revalidado `local_v2_v6_20260818T162939Z` contiene 432
  artefactos de 436 fits planificados y cuatro fallos V5.

## Riesgos

- No basta con eliminar V2–V6 de la cadena actual: debe seguir construyéndose
  el conjunto completo que necesita el V2 operativo.
- Un benchmark antiguo sigue siendo auditable, pero no promocionable si sus
  entradas ya no coinciden con las vivas.
- El soporte por especie/campaña es pequeño; los rankings son diagnósticos.
- Preservar todos los cambios, datos, cachés y ficheros no rastreados.
- No usar Tailscale, tocar HA real/worker normal ni publicar releases sin
  autorización explícita.
