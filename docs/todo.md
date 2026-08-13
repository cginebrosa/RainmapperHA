# TODO

Lista operativa priorizada. El estado inmediato está en
`docs/active-context.md`; el histórico completado vive en `docs/decisions.md`,
`docs/project-archive.md` y el laboratorio meteorológico.

## P0 — Cerrar altitude V2 de extremo a extremo

- [x] Diagnosticar el desacople: HA `0.2.253` solicita altitude V2 y worker
  `1.0.7` produjo features/modelos V1 sin altitud de estación.
- [x] Añadir al manifiesto los contratos sombra y rechazar una promoción que no
  declare exactamente los dos contratos altitude V2.
- [x] Reconstruir en el M1 un snapshot real: 313/399 filas con altitud de
  estación; 347/399 con altitud GIS; 78,8 s.
- [x] Entrenar sobre el artefacto reconstruido: 8 modelos operativos y 9 sombra
  altitude V2; predicción centinela real disponible.
- [x] Superar 85 pruebas focalizadas, smoke global de 673 tests y construir
  `rainmapper-worker:1.0.8`.
- [x] Instalar worker `1.0.8` preservando el volumen persistente y verificar
  health, identidad, caché GIS y contratos anunciados.
- [x] Ejecutar desde HA `Reconstruir y reentrenar todo`, activar conjuntamente
  y comprobar que la generación viva contiene altitude V2.
- [x] Verificar Predictor semanal no vacío en M1 y en HA; HA queda validado como
  fallback (97,608 s, ~577 MiB, sin OOM). Referencia HA exacta guardada.
- [x] Comparar HA/M1 para la referencia del 13/08/2026: mismos siete valores
  puntuados y orden; las diferencias restantes eran solo empates sin score.
- [x] Publicar la barrera V2 del coordinador en HA `0.2.254`, multiarch y con
  digest común verificado.
- [x] Instalar HA `0.2.254` y verificar arranque/worker antes del rebuild.

## Completado — coherencia de generación HA 0.2.253

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
- [x] La consulta centinela previa confirmó la coherencia de hashes V1, aunque
  después se detectó su incompatibilidad semántica con el runtime altitude V2.

## P1 — Terminar Biology V3

- [x] Implementar primero el payload de benchmark V3 separado en
  `predictive_features`, `quality` y `metadata`, con una aserción que impida
  incorporar quality a `X`.
- [x] Implementar el contrato IDW diario por microárea (15 km, potencia 2),
  ceros observados válidos y ausencias/suprimidos/retiradas fuera del promedio;
  15 pruebas fundacionales superadas y paridad numérica Tomap comprobada.
- [x] Implementar la unidad canónica microárea/fecha, conflictos, favorables,
  desfavorables y desconocidos; quality/metadata permanece fuera de X.
- [x] Comprobar y ratificar la agregación espacial: media diaria de
  los IDW disponibles de todas las microáreas configuradas del área. Comparar
  con el IDW del centroide calculado, incluyendo p95/p99, máximos y dispersión
  para no ocultar tormentas locales mediante doble suavizado. Resultado: 7.262
  días-área, mediana 0,001 mm, p95 0,62 mm, máximo 7,89 mm y dispersión máxima
  entre microáreas 43,94 mm.
- [x] Ratificar `especie + área + fecha` como unidad final de entrenamiento:
  278 episodios auditables, 275 con target conocido, 9 mixtos reales entre
  microáreas y 2 conflictos internos preservados por separado.
- [x] Reutilizar inicialmente para temperatura/humedad el selector V2 sensible
  al corte y la corrección por altitud; las variables posteriores a un evento
  siguen registradas pero inactivas mientras no exista semántica única.
- [x] Conservar la procedencia técnica del IDW para reproducción interna:
  fuentes, estaciones participantes, número y distancias. No mostrarla como
  incertidumbre, no penalizar estaciones comunitarias y no llevarla a X ni a
  advertencias de la predicción.
- [x] Fijar como validación principal el corte cronológico 70/30 por especie con
  grupos completos de florada de 14 días; repetir con 7 días como sensibilidad,
  sin eliminar observaciones ni escoger retrospectivamente el mejor resultado.
- [x] Resolver DEM secundario trazable para Ordino/Andorra: MDE oficial 5 m,
  EPSG:27563, metros y fallback tras `NoData` del DEM Catalunya; derivado
  incluido en el dataset GIS cacheado del worker y validado a 6,5 m del GPS.
- [x] Terminar `fixed_gap_7d_biology_v3` y `lag_event_biology_v3` según
  `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`.
- [x] Materializar gates y motivos de exclusión antes de entrenar: lluvia IDW,
  cobertura, alineación, historia, temperatura/humedad y altitud disponibles.
- [x] Regenerar la auditoría/benchmark ML con el snapshot actual y
  contrastar 399 observaciones, 348 unidades canónicas, 278 episodios y 275
  targets conocidos; no codificar estos recuentos como constantes.
- [x] Ejecutar benchmark temporal reproducible y comparar contra
  los contratos altitude v2 congelados. No elegir ni promover por capturas.
- [x] Revisar calibración, Brier, prevalencia, soporte por especie y dominio.
  Resultado: V3 no pasa aún el gate operativo porque V2/V3 no comparan las
  mismas filas y V3 empeora log loss; no entrenar ni promover un candidato.
- [x] Empaquetar benchmark/evaluación V3 en worker `1.0.9` y comprobar dentro de
  la imagen el mismo informe y hash que en local, sin instalarla ni ejecutar un
  job operativo.
- [ ] Repetir V2/V3 cuando haya más observaciones, sobre exactamente las mismas
  filas y corte predeclarado. Exigir mejora de Brier repetible en 7/14 días,
  calibración/log loss no peores y ausencia de regresiones graves por especie
  con soporte suficiente antes de entrenar un candidato operativo.

## Completado — saneamiento GIS local

- [x] Verificar que `mushroom-GIS-HA` no era ruta operativa, no estaba
  versionada ni abierta por procesos.
- [x] Comparar sus diez ficheros de datos con `mushroom-GIS` y confirmar
  identidad byte a byte; los otros dos eran `.DS_Store`.
- [x] Eliminar de forma autorizada la copia redundante de 5,9 GB, conservar
  intacto `mushroom-GIS` y retirar la regla de ignore que podía ocultar su
  reaparición.

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
- [x] Investigar la altitud representativa de Ordino y cobertura DEM de Andorra:
  2063,2 m en el centro del área y 2064,2 m en la microárea configurada.

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
- [x] REEMPLAZADO: `1.0.7` soporta ambos tipos de job, pero no el contrato
  altitude V2 completo; se requiere `1.0.8`.
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
- Altitude V2 requiere coherencia entre reconstrucción, training, modelos y
  runtime. No confundir soporte genérico de jobs con soporte del contrato.
- La muestra de salidas está sesgada porque normalmente no se visita cuando se
  espera un resultado negativo; mantener esta censura explícita.
- HA y worker se versionan independientemente; compatibilidad por capacidades y
  contratos, no por igualdad de versión.
