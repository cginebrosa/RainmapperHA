# TODO

Lista operativa priorizada. El histórico completado se resume en
`docs/decisions.md` y `docs/project-archive.md`.

## P0 — Validación inmediata

- [ ] Instalar HA `0.2.239` en la RPi4.
- [ ] Confirmar que `M1 Personal` aparece conectado, idle, con worker `1.0.2`,
  capacidad `predictor_v1` y cachés válidas.
- [ ] Probar el Predictor completo usando M1: entrada, varios días, Por especie,
  fecha actual, fecha histórica e Historial.
- [ ] Confirmar que todas las interacciones mantienen M1 sin nuevo selector ni
  fallback a HA mientras siga disponible.
- [ ] Medir aproximadamente primera operación y repeticiones calientes; revisar
  en Diagnostics `backend_seconds`, cold/warm, ejecutor, cachés y bytes.
- [ ] Si alguna petición tarda mucho, separar cálculo del worker, cola,
  sincronización de runtime y tiempo total observado por HA antes de cambiar
  código.

## P1 — Después de validar 0.2.239

- [ ] Documentar las medidas reales M1 extremo a extremo y compararlas con HA:
  apertura fría 30–40 s, navegación caliente casi instantánea y fecha histórica
  alrededor de 10 s como referencia previa.
- [ ] Preparar/exportar la imagen worker `1.0.2` para M5 solo si el usuario quiere
  actualizarlo. M5 no es necesario para validar el M1.
- [ ] Diseñar la exposición autenticada del Predictor desde MapLibre:
  - usuarios normales en Auto y exclusivamente sobre workers;
  - sin fallback silencioso a HA/RPi4;
  - cola y límites de concurrencia;
  - rate limiting y caché compartida;
  - gateway en HA, nunca navegador → worker;
  - política administrativa de selección pendiente de decidir.
- [ ] Diseñar una URL de coordinador anunciada y agnóstica de LAN, VPN o proxy;
  no cambiar la configuración Tailscale que funciona durante la validación.

## P2 — Mejoras condicionadas por evidencia

- [ ] Si hacen falta fases detalladas del Predictor remoto, acumularlas dentro
  del worker y enviarlas una sola vez con el resultado final.
- [ ] Añadir checkpoints locales de cancelación únicamente si aparecen cálculos
  interactivos suficientemente largos para necesitarlos; no restaurar llamadas
  HTTP por fila.
- [ ] Afinar la apertura fría de HA/RPi4 solo después de validar la vía worker y
  disponer de una medida descompuesta fiable.
- [ ] Seguir reduciendo responsabilidades de `web_server.py` cuando los cambios
  puedan residir en `rainmapper_core` o módulos de UI específicos.

## Completado en el ciclo actual

- [x] Predictor ejecutable en HA o worker `predictor_v1`, con HA como autoridad
  de UI, jobs, resultados y Diagnostics.
- [x] Selección de ejecutor fijada durante toda la sesión; solo cambia por orden
  explícita o indisponibilidad real.
- [x] Diagnóstico del retraso remoto: 112 viajes síncronos al coordinador para
  una semana de 56 filas convertían 2,617 s de cálculo en 117–134 s.
- [x] Eliminados callbacks granulares; worker `1.0.2` publica solo inicio/final y
  el modal usa una ETA visual no autoritativa.
- [x] Cachés LRU por fingerprint, inferencia vectorizada y runtime inmutable
  persistente en worker.
- [x] HA `0.2.239` publicada multi-arquitectura y worker M1 `1.0.2` healthy/idle.
- [x] Caja negra persistente con comparativas, evolución, promedios por versión,
  Gantt de fuentes y recuperación de memoria.
- [x] P0 de memoria RPi4 cerrado para uso monousuario sin runner y Predictor
  simultáneos; cero OOM en las pruebas realizadas.
- [x] Parquet meteorológico filtrable, catálogo de estaciones, paridad
  train/predict y selección por cobertura.
- [x] Retención/limpieza de bundles terminales de workers y reconciliación antes
  de lanzar trabajos.
- [x] Limpieza de fotos huérfanas y corrección del borrado de media compartida.

## Riesgos y dudas abiertas

- La ETA del modal es una estimación del cliente, no porcentaje real.
- El M5 sigue en una versión anterior del worker.
- La fuente futura de permisos del Predictor público —rol fijo, campo de usuario
  o perfil— está sin decidir.
- Escalar el Predictor sin límites podría trasladar la saturación de la RPi4 a
  los workers; la publicación pública no debe hacerse antes de resolverlo.
- HA y worker se versionan de forma independiente; nunca inferir compatibilidad
  por igualdad de números, sino por capacidades y contratos.
