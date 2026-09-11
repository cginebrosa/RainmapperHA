# TODO

Prioridades vivas al cierre del 11 de septiembre de 2026. El estado operativo
y la evidencia exacta están en `docs/active-context.md`; las decisiones
duraderas, en `docs/decisions.md`.

## P0 — Corregir la semántica temporal de la selección semanal

- [x] Implementar selección opcional de una familia común por especie/área,
  priorizando cobertura semanal de aplicabilidad y después evidencia agregada.
- [x] Mantener la familia ganadora ante un veto diario y abstenerse sin cambiar
  a otra candidata.
- [x] Reconstruir HA local y worker desde el mismo código y validar con un nuevo
  precálculo que la identidad de familia permanece estable.
- [x] Aislar el caso `boletus_aereus/olvan`: una familia semanal `fixed h7`
  corta cada fecha siete días antes y hace que el 13/09 ignore lluvia conocida
  del 09/09 que el 16/09 sí puede usar.
- [x] Limitar las anclas del modo semanal a contratos `lag_event`, conservando
  versión/perfil/estimador y variando horizonte h1--h7.
- [x] Mantener la decisión existente de `daily_fallback` auditado cuando no
  existe familia común; no introducir abstención semanal completa.
- [x] Al restringir el agregado a `lag_event`, conservar ese fallback y dejar
  explícito que no garantiza continuidad ni corte común. `fixed h7` solo puede
  reaparecer mediante la selección diaria identificada como tal.
- [x] Añadir regresiones para corte meteorológico común, cobertura primero,
  abstención sin cambio y ausencia de familia de retardo.
- [x] Reconstruir HA local y worker preservando exactamente ambos coordinadores;
  comprobar código efectivo y las regresiones temporales en ambos contenedores.
- [x] El usuario lanzó el precálculo local; revisión 54 completa y activa.
  Codex no lanzó trabajos. Revisión persistida final: 61 parejas con una
  familia semanal constante, seis fallback diarios y doce fuera de temporada.
  No entrenar.
- Especificación:
  `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`.

## P0 — Integrar el worktree después de la corrección

- [ ] Validar visualmente `Total rows` y `Updated rows` en el panel y confirmar
  que no se recorren otra vez los CSV.
- [ ] Confirmar en un runner local proporcional que el modo mensual
  Wunderground pide día 1--hoy y, en días 1--7, incluye el mes anterior; no
  repetirlo si la misma revisión ya queda cubierta por la prueba final.
- [x] Publicar HA `0.2.302` con smoke completo (1.384 tests), tags GHCR
  verificados y cierre mediante un único commit/push selectivo.
- [ ] El usuario debe instalar `0.2.302` en HA y confirmar el resultado.
- [x] Excluir expresamente del commit
  `mushroom-data/mushroom_observations.json`.

## P0 — Revisar abstenciones por aplicabilidad

- [ ] Auditar una muestra multiespecie separando tolerancia absoluta,
  desviación normalizada, tipo de variable y dirección de extrapolación.
- [ ] Empezar por Rovelló / Els Ports / 2026-09-07: LR-V3 calculó `0,0016 %`,
  pero se abstuvo por humedad máxima `88,062 %` frente al mínimo aprendido
  `89,001 %` y temperatura máxima `33,151 °C` frente al máximo `30,933 °C`.
- [ ] Determinar por especie y variable si una diferencia absoluta pequeña
  puede bloquear por sí sola. No aplicar una tolerancia global.
- [ ] Diseñar la presentación de una probabilidad vetada como diagnóstico, sin
  color operativo, recomendación ni ranking.
- [ ] Separar en UI `modelo no disponible` de `modelo disponible pero vetado`.

## P1 — Francia: terminar integración operativa

- [x] Integrar RGE ALTI Francia 5 m como cuarto DEM y transportarlo mediante la
  caché GIS incremental del worker.
- [x] Comprobar altitud, pendiente y orientación en microáreas de Font-Romeu y
  Quérigut desde HA local.
- [x] Descartar Infoclimat como fuente nueva inicial por cobertura útil
  insuficiente y documentar Meteo-France como alternativa futura.
- [ ] Reaplicar y revisar GIS/DEM de todas las microáreas francesas desde la UI
  de HA real `0.2.301`, que ya contiene el soporte francés.
- [ ] Decidir si el desfase operativo de Meteo-France aporta valor suficiente
  frente a las estaciones Wunderground ya disponibles antes de implementarlo.

## P1 — Worker, almacenamiento y observabilidad

- [x] Limpiar 10,43 GiB de jobs antiguos y una generación GIS inactiva tras
  auditoría por hash, preservando runtimes, cachés y asociaciones.
- [x] Conservar en `Trabajos recientes` los precálculos automáticos terminales
  dentro del límite ligero global de 50 entradas.
- [ ] Completar el CLI por `coordinator_id` sin alterar otros coordinadores.
- [ ] Medir en la Raspberry Pi 4 lectura de red, hash/escritura, `fsync`,
  validación y promoción antes de implementar streaming incremental.
- Especificación de transporte:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.

## P1 — Predictor y ciencia aplazada

- [ ] Crear el catálogo explícito de especies posibles por área.
- [ ] Sustituir `Historial` en HA por el evaluador persistido del catálogo
  hold-out; el precálculo semanal no contiene `history`.
- [ ] Mejorar mensajes de incompatibilidad para diferenciar reentrenamiento,
  precálculo, cobertura y corrupción.
- [ ] Repetir la comparación de racha seca actual, `<1 mm` y sin contador sólo
  cuando existan nuevos grupos independientes suficientes.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando sus hold-outs
  externos contengan ambas clases.

## Completado en esta sesión

- [x] Publicar e instalar HA `0.2.298`, `0.2.300` y finalmente `0.2.301`; esta
  última es la release vigente en HA real.
- [x] Corregir el alta de especies nuevas en tuning y confirmar que el
  entrenamiento real con `cantharellus_cibarius_sl` supera el fallo original.
- [x] Añadir defensa por timestamp frente a variantes CDN Wunderground
  obsoletas, orden configurable de encodings y modos semanal/mensual
  mutuamente excluyentes.
- [x] Incorporar el DEM francés, conservar las capas SoilGrids ya incluidas en
  el dataset GIS y validar la caché resultante de 13 ficheros en el worker.
- [x] Añadir las bases de selección semanal coherente, contadores total/nuevo
  del estado de fuentes y retención de precálculos automáticos recientes.
- [x] Documentar la limitación `fixed h7` y la propuesta `lag_event h1--h7`
  para que la siguiente sesión pueda continuar sin repetir diagnóstico.
