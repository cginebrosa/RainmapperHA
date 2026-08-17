# TODO

Prioridades vigentes. El estado inmediato está en `docs/active-context.md`; el
detalle histórico vive en `docs/decisions.md`, `docs/project-archive.md` y los
informes temáticos.

## P0 — Cerrar análisis multiversión antes de integrar

- [x] Reparar localmente los históricos oficiales AEMET/Meteocat y conservar
  una generación inmutable. Todo lo recuperable quedó materializado; Meteocat
  mantiene solo tres días que la API devuelve vacíos.
- [x] Aplicar meteorología IDW común a V2/V3/V4: lluvia, Tmin/Tmax corregidas a
  altitud DEM y RHmin/RHmax, usando las cuatro fuentes y mínimo una estación.
- [x] Separar `predictive_features`, `quality` y `metadata`; impedir por pruebas
  que calidad, área o identidad entren en `X`.
- [x] Completar V3 fixed/lag y V4 core/meteo/balance/suelo, con gates, motivos
  legibles, paridad train/inferencia y continuidad 7/14.
- [x] Crear snapshot canónico `mushroom-ml-snapshot-20260816`: 395
  observaciones, 352 fixed elegibles y 1.408 tareas lag elegibles. Instalar solo
  el `known_sites` derivado y respaldado en HA.
- [x] Comparar V2/V3/V4 sobre filas idénticas, seis algoritmos, especies,
  contratos y grupos 7/14, sin Brier medio.
- [x] Corregir `lag_event` para ajustar una vez y filtrar por horizonte sin
  reentrenar. Reducir `lag/groups7` de 650,68 s a unos 157 s y superar 801 tests.
- [x] Publicar el análisis canónico en
  `docs/reports/V2_V3_V4_consensus_report002.md`; marcar report001 y el JSON lag
  pre-corrección como históricos.
- [ ] Añadir salida de evaluación apta para analizar errores fila a fila, sin
  escribir modelos operativos ni filtrar observaciones.
- [ ] Analizar falsos positivos/negativos compartidos por especie, horizonte,
  fase de florada y meteorología. Proponer otra familia de modelos solo si
  responde a un patrón de error concreto.
- [ ] Si se ensaya un ensemble, exigir que supere al mejor miembro individual
  por especie/contrato; acuerdo entre modelos no es un gate suficiente.

## P1A — Nuevas observaciones y decisión de contrato

- [ ] Después de alinear la plataforma, incorporar las cuatro salidas negativas
  recientes del usuario, correspondientes a cuatro microáreas y cuatro
  especies. Preservar el snapshot actual y crear otro.
- [ ] Repetir exactamente fixed/lag, grupos 7/14, seis algoritmos y V2/V3/V4.
  Medir cuánto cambian ganadores, calibración, Brier y consenso de calidad.
- [ ] Mantener V2/V3/V4 persistidas aunque no estén operativas. Estados y
  selección proceden del registro genérico, nunca de `if` por versión.
- [ ] Decidir por especie y contrato si alguna versión merece candidatura. V4
  queda hoy `proposed` y no supera el gate; no entrenar candidato todavía.

## P1B — Integración coordinada futura, requiere autorización

- [ ] Rebasar el histórico local reparado sobre un snapshot fresco de HA para
  no perder avances de scheduled runners.
- [x] Empaquetar y validar localmente registro multiversión, V3/V4, autocuración
  meteorológica y datos GIS/SoilGrids requeridos por alta/edición de microáreas.
- [x] Publicar HA `0.2.256` multi-arch y preparar el paquete privado arm64 del
  worker `1.0.10`; no instalar HA `0.2.255` ni worker `1.0.9`.
- [ ] Con autorización explícita, entrenar una generación candidata concreta
  desde observaciones, known sites e histórico del mismo snapshot.
- [ ] Instalar primero worker `1.0.10` y después HA `0.2.256`; validar ambos sin
  lanzar todavía reconstrucción ni entrenamiento.
- [ ] Después de validar la pareja, reconstruir y promover una sola
  generación; validar Predictor M1/HA, huellas, paridad y rollback.
- [ ] Confirmar que V2/V3/V4 permanecen archivadas y reevaluables después de
  elegir la versión operativa.

## P2 — Biology V4 y GIS experimental

- [x] Traducir la literatura de fructificación a la especificación V4.
- [x] Implementar caché SoilGrids por extensión dinámica y materialización por
  microárea; 59/59 microáreas actuales tienen agregados completos.
- [x] Implementar memoria de lluvia, días lluviosos, balance climático, estado
  hídrico y continuidad, conservando extremos sin medias como predictores.
- [x] Verificar que V4 core reproduce V3 y que balance/suelo conservan paridad
  train/inferencia.
- [x] Concluir que balance no mejora Brier consistentemente y SoilGrids suele
  empeorar predicción/continuidad. Conservarlos experimentales y desactivados.
- [ ] Deuda no bloqueante: completar propiedades/quantiles SoilGrids solo si un
  experimento futuro los necesita; no ampliar descargas por anticipación.
- [ ] Corregir el matching geológico por subcadena (`gres`/`negres`) antes de
  usar esos proxies. El SMI actual no los consume.
- [ ] No crear suavizado o estado de florada hasta disponer de más etiquetas
  semanales; hoy hay unas 50 útiles y no se inventan estados intermedios.

## P2 — Autocuración meteorológica

- [x] Implementar localmente detector, cola durable, backoff, reparación por
  bloques y cierre automático para huecos oficiales fuera del solape diario.
- [x] Mantener contratos diferentes: Meteocat en bloques máximos de 15 días;
  AEMET una petición de climatología por runner para evitar `429`.
- [x] Reparar primero histórico particionado y después CSV vivo de 180 días.
- [ ] Desplegar solo dentro de una release coordinada autorizada y validar su
  aviso batch en Diagnostics/Errors.
- [ ] Futuro no prioritario: bootstrap autónomo de histórico en una instalación
  virgen, derivando alcance desde la observación más antigua y el lookback.
- [ ] Evaluar más adelante una skill dedicada a backfills meteorológicos; los
  pasos deterministas deben permanecer en scripts probados.

## P3 — Integridad de observaciones y UX

- [ ] Añadir sanity checks confirmables al alta/edición/importación: temporada,
  altitud y primera observación especie-área/microárea.
- [ ] Mostrar advertencias y permitir continuar; nunca corregir, descartar ni
  reclasificar automáticamente una excepción real.
- [ ] Auditar identificaciones automáticas antiguas que pudieran contaminar
  artefactos previos.

## Baseline completado que no debe reabrirse

- [x] Histórico meteorológico transaccional particionado por fuente/año,
  `CURRENT.json` atómico, CSV vivos de 180 días y consumidores acotados.
- [x] Altitude V2 operativa de extremo a extremo en HA `0.2.254` y worker
  `1.0.8`, con promoción conjunta y fallback HA validado.
- [x] Ciclo de vida ML genérico: versiones persistentes, generaciones
  inmutables, huella semántica por área y gates de promoción.
- [x] DEM Catalunya con fallback oficial Andorra; eliminación autorizada de la
  copia local redundante `mushroom-GIS-HA`.

## Riesgos y dudas

- Predictor actual desalineado por cambio de `known_sites`; resolver con rebuild
  coordinado, nunca relajando hashes o parcheando bundles.
- Soporte bajo y sensible: dos observaciones ya cambiaron ganadores; Edulis no
  tiene dos clases en la partición de grupos 7.
- Los horizontes lag no son observaciones independientes.
- V4 no supera hoy a V3 de forma consistente y no es candidata operativa.
- El histórico reparado/autocuración y gran parte de V3/V4 existen solo en el
  worktree local; revisar alcance cuidadosamente antes de commit o release.
