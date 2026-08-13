# TODO

Lista operativa priorizada. El estado inmediato está en
`docs/active-context.md`; el histórico completado vive en `docs/decisions.md`,
`docs/project-archive.md` y el laboratorio meteorológico.

## P0 — Instalar 0.2.253 y regenerar una generación coherente

- [x] Confirmar que HA terminó de instalar `0.2.252` y que el add-on arranca.
- [x] Confirmar que el worker M1 `1.0.7` está healthy/idle y conserva identidad,
  cachés y capacidades.
- [x] Verificar que `Workers y trabajos` presenta una sola acción completa y no
  expone scopes parciales ni entrenamiento independiente.
- [x] Ejecutar una reconstrucción y reentrenamiento completos en el worker y
  comprobar el encadenado y la promoción conjunta.
- [x] Detectar que la promoción de `0.2.252` cambiaba el hash del features vivo
  después del entrenamiento y que el Predictor bloqueaba la mezcla.
- [x] Corregir la identidad previa al entrenamiento, añadir regresiones, superar
  672 tests/smoke y publicar HA `0.2.253` multiarch.
- [x] Instalar HA `0.2.253`; worker M1 permanece en `1.0.7`.
- [x] Repetir `Reconstruir y reentrenar todo` y activar mediante la única
  promoción conjunta. No reutilizar el candidato generado por `0.2.252`.
- [x] Validar una consulta actual del Predictor: caché fría sincronizada, sin
  discrepancia de identidad; Edulis tiene 31 filas y 0 microáreas de Olvan.
- [ ] Repetir un caso centinela histórico del Predictor.

## P1 — Terminar Biology V3

- [ ] Regenerar la auditoría ML con el histórico meteorológico ya definitivo y
  los artefactos completos recién activados.
- [ ] Confirmar la unidad canónica microárea/fecha, conflictos, favorables,
  desfavorables y desconocidos; quality/metadata permanece fuera de X.
- [ ] Terminar `fixed_gap_7d_biology_v3` y `lag_event_biology_v3` según
  `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`.
- [ ] Ejecutar benchmark temporal/estratificado reproducible y comparar contra
  los contratos altitude v2 congelados. No elegir ni promover por capturas.
- [ ] Revisar calibración, Brier, prevalencia, soporte por especie y dominio
  antes de proponer una promoción de modelos.
- [ ] Mantener rebuild, entrenamiento y Predictor pesado en el M1; medir que HA
  solo coordina y sirve UI/resultados.

## P2 — Integridad de observaciones y UX ecológica

- [ ] Añadir sanity checks confirmables al alta, edición e importación masiva:
  fecha fuera de temporada habitual, altitud discordante y primera observación
  especie-área/microárea.
- [ ] Los checks deben mostrarse en un modal evidente y permitir continuar;
  nunca corregir, descartar ni reclasificar automáticamente una excepción real.
- [ ] Cambiar el dictamen rígido `fuera de temporada` por una advertencia
  ecológica prudente cuando el Predictor pueda evaluar condiciones compatibles.
- [ ] Auditar las identificaciones automáticas antiguas restantes para detectar
  observaciones que pudieron contaminar artefactos previos.
- [ ] Investigar la altitud representativa de Ordino y cobertura DEM de Andorra.

## Completado — histórico y almacenamiento meteorológico

- [x] Backfill cacheado/reanudable de Meteocat, Wunderground y AEMET; ausencia,
  error o estación inexistente nunca se convirtió en lluvia cero.
- [x] Merge complementario y deduplicación por fuente/estación/fecha, con
  candidatos, informes y hashes preservados en el laboratorio.
- [x] Migración inicial construida y validada en el M1, no en la RPi4.
- [x] Histórico canónico transaccional particionado por fuente/año instalado y
  validado en HA, con generaciones inmutables, manifiesto y `CURRENT` atómico.
- [x] CSV diarios vivos acotados a 180 fechas; colas intradía AEMET y
  Meteoclimatic a siete días cerrados más el actual.
- [x] Tomap/MapLibre leen ventanas acotadas; Predictor y workers consumen el
  histórico particionado mediante snapshots y cachés por hash.
- [x] Runner ordinario e idempotencia medidos en la RPi4 de 4 GiB; schedules
  reactivados y generación antigua acotada.
- [x] Métricas Wunderground con retención acotada; escrituras críticas atómicas.

## Completado — release 0.2.252

- [x] Eliminados botones y selectores de reconstrucción parcial/especie/
  pendientes y el entrenamiento independiente de la UI operativa.
- [x] Implementado chaining coordinador de reconstrucción completa a training
  completo usando el `features.json` candidato.
- [x] Implementada promoción conjunta con reservas de ambos jobs, limpieza de
  pendientes posterior al éxito y rollback de artefactos/modelos.
- [x] Smoke del paquete aislado: 651 tests. Worktree completo: 669 tests.
- [x] Publicada HA `0.2.252`, commit `8010b89`, multiarch amd64/arm64, digest
  común `sha256:c888fce58ba98dd082f56678ea4c18aa73ce43f7421c2e309437e756d204920d`.
- [x] Confirmado que worker `1.0.7` ya soporta ambos jobs y no necesita `1.0.8`.
- [x] Documentada la autorización para ejecutar sin consultas redundantes las
  acciones no destructivas propias de una tarea explícitamente encargada.

## Completado — publicación 0.2.253

- [x] Unificada la transformación de metadata a rutas vivas entre preparación
  del entrenamiento y promoción.
- [x] Conservado el diagnóstico completo con wrapping de rutas/hashes en el
  modal del Predictor.
- [x] Suite completa: 672 tests; smoke, sintaxis y versiones superados.
- [x] Publicados `0.2.253` y `latest` con digest común
  `sha256:5b1fad84e76ae80a1144e8f96f8dd54abd708bbcef0e27d27566fd4645ce4e89`
  y manifests `linux/amd64` y `linux/arm64`.

## Riesgos y dudas

- Hasta activar una reconstrucción completa, los artefactos/modelos pueden no
  representar el store corregido de observaciones.
- Edulis tiene una muestra pequeña: una observación incorrecta puede alterar
  significativamente soporte, áreas y scores.
- Los cambios locales Biology V3/altitude v2 no forman parte de `0.2.252`; no
  limpiar el worktree ni confundir código local con producción.
- La muestra de salidas está sesgada porque normalmente no se visita cuando se
  espera un resultado negativo; mantener esta censura explícita.
- HA y worker se versionan independientemente; compatibilidad por capacidades y
  contratos, no por igualdad de versión.
