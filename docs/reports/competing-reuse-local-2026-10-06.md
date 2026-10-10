# Selección y comparación: reutilización y panel plegado · 06/10/2026

El usuario canceló el trabajo largo y pidió optimizar la reutilización antes de
volver a lanzarlo. El log confirma la cancelación de
`worker_job_ZFACRJa4VG_0ze9s` a las 19:34:03 UTC y la liberación de su vía de fondo.
Codex no lanzó otro histórico, estudio, entrenamiento operativo ni precálculo.
No se publicó una release ni se modificaron observaciones o fuentes privadas.

## Implementación

El mismo trabajo prepara la selección A/B/C/D y la comparación común con
Habitual. El mapa sólo lee resultados; el botón de Workers usa la K personal o
la heredada del add-on. No se solicita preparación histórica al consultar puntos.

`mushroom_competing_panels.Builder` reutiliza la base meteorológica/ET₀ ya
preparada, recortando por corte histórico y conservando el tratamiento de lluvia
duplicada en el límite. Indexa fechas y huellas de estaciones; mantiene una
ventana por vista, compartiendo las bases en lugar de copiarlas.

La nueva tabla `runtime_inputs` guarda series por área/corte y variables por
especie/perfil/fecha/horizonte. Excluye estimador y pesos de la clave cuando no
alteran esas variables. Las claves incluyen código, contexto y meteorología
consumida. La huella de cada unidad sigue incluyendo sus datos de ajuste/prueba y
las variables de sus semanas completas. Cambiar observaciones invalida unidades
dependientes, conservando las variables que no cambian. La inferencia usa un lote
por visita de hasta 49 filas, conservando los días no disponibles. Cambiar sólo K
reutiliza la generación guardada, sin preparar meteorología ni ajustar modelos.

Se admite explícitamente el productor revisado del trabajo cancelado,
`ce683820f90f3e87cb2e8cdee471ba4ff466acbd6f4bab468d79555965b8cdd5`, únicamente si
coinciden exactamente los datos actuales de ajuste/prueba y la huella actual de
la semana. Se conservan sus claves y paquetes: no se acepta una generación
entera por similitud. Las unidades incompletas o antiguas sin semanas completas
no tienen garantizada la reutilización.

No se elevan límites: hasta 32 MiB comprimidos para las nuevas entradas dentro
de la base de unidades ya limitada a 256 MiB, reservando margen para resultados.
El FIFO sólo elimina entradas reconstruibles de esa tabla, nunca unidades,
semanas, observaciones o archivos fuente. Memo comprimido de hasta 2 MiB e índice
de fechas/huellas de hasta 16 MiB. Se mantienen los 96 MiB de semanas y el
artefacto resumido para HA de máximo 1 MiB.

El progreso total se reparte entre familias y no retrocede por eventos internos.
Conserva contadores de visitas y entradas creadas/reutilizadas; no inventa ETA.
Workers muestra **Selección y comparación** (ES/CA/EN) en un `<details>` cerrado
por defecto, cuyo estado abierto se conserva durante el refresco. El título
también se aplica a la lista y al detalle del trabajo.

## Verificación

- **62 pruebas dirigidas** aprobadas en Mac: selección/comparación, no disparo
  desde mapa, cachés/dependencias/límites, progreso, agua y presentación.
- **37 pruebas** aprobadas en la imagen worker reconstruida, sin red ni datos
  reales. Incluyen constructores reales con datos sintéticos.
- Igualdad exacta de muestras y fingerprints de semanas entre materialización
  directa y compartida para los perfiles V3–V6 y ambos contratos temporales.
  Casos con estaciones lejanas, ausentes y lluvia repetida en el límite. Pruebas
  de reapertura SQLite, cambio de estimador/pesos/visita, invalidación por lluvia
  consumida y conservación ante lluvia posterior al corte.
- Microprueba sintética de una visita y cuatro candidatos: materializaciones
  meteorológicas **104 → 13**, variables **104 → 13**, llamadas de inferencia
  **52 → 4** y fingerprints idénticos. Tiempos **0,4843 → 0,0635 s**. La inferencia
  aquí usa respuesta sintética; no mide ajustes reales ni permite extrapolar esa
  aceleración al trabajo completo.
- Navegador contra HA local a **1600, 375 y 320 px**: inicialmente cerrado,
  teclado, formularios conservados, refresco sin cerrar y cero POST. Captura de
  375 px inspeccionada visualmente.
- HA local y worker reconstruidos/recreados. Se esperó a que terminara el
  precálculo ajeno `worker_job_63sX-HMKUUlY`, iniciado por el coordinador principal
  y completado a las 19:46:37 UTC. Codex no lo lanzó ni canceló. Ambas vías del
  worker libres antes/después de recrearlo.
- Paridad efectiva por SHA-256: **32 archivos HA / 25 worker**, sin diferencias;
  Workers HTTP 200. Revisión idéntica Mac/HA/worker:
  `a36878ced3018d2d38432befcd06105f9947e684de8770c75725bb64fd93a4e1`.
- Coordinadores conservados: principal `http://100.111.77.48:8100`, adicional
  `http://rainmapper-ha-ui:8100`. Hashes de configuración antes/después:
  `5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10` y
  `22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0`.

Recibos locales: `tmp/competing-reuse-20261006/` (`tests.log`, `image-tests.log`,
`measure.json`, `browser.json`, capturas, builds y `parity.json`). Fuentes de
estado: `/health` del worker, logs Docker y endpoint local de Workers.

## Pendiente del usuario

Recargar Workers, abrir Selección y comparación y pulsar Comprobar y actualizar.
Medir duración real, reutilización efectiva, cobertura/ausencias, publicación del
resumen y notas comunes del mapa. Este recorrido completo aún no se ha validado
con sus datos reales. La primera comparación puede necesitar ajustes aislados de
validación para semanas que el selector antiguo no guardaba. No confundir las
pruebas sintéticas con ese trabajo ni anunciar un tiempo máximo.
