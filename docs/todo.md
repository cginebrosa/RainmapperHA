# TODO

Prioridades vivas al cierre del 8 de septiembre de 2026. El estado operativo y
la evidencia exacta están en `docs/active-context.md`; las decisiones duraderas,
en `docs/decisions.md`.

## P0 — Revisar abstenciones por aplicabilidad

- [ ] Auditar una muestra multiespecie de predicciones bloqueadas para distinguir
  desviaciones absolutas pequeñas, desviaciones normalizadas altas y
  extrapolaciones materialmente peligrosas.
- [ ] Usar como primer caso controlado Rovelló / Els Ports / 2026-09-07: el
  modelo LR-V3 calculó `0,0016 %`, pero se abstuvo por humedad máxima `88,062 %`
  frente a mínimo aprendido `89,001 %` y temperatura máxima `33,151 °C` frente
  a máximo aprendido `30,933 °C`.
- [ ] Revisar si menos de un punto porcentual de humedad puede bloquear por sí
  solo. No aplicar una tolerancia global sin medir su efecto en todas las
  variables y especies.
- [ ] Decidir si la UI debe mostrar la probabilidad calculada de un modelo
  rechazado, acompañada de una abstención visual inequívoca y sin convertirla
  en recomendación, color operativo ni elemento de ranking.
- [ ] Corregir el texto `aplicabilidad · modelo no disponible` para separar
  modelo inexistente de modelo existente cuya predicción fue vetada.

## P0 — Cerrar el worker multicoordinador

- [x] Permitir que una única instalación mantenga dos o más coordinadores con
  credenciales aisladas y un límite configurable.
- [x] Mantener dos carriles globales para poder ejecutar entrenamiento y
  precálculo en paralelo sin aceptar dos trabajos pesados del mismo tipo.
- [x] Reproducir desde HA local el fallo de precálculo de HA real y corregir la
  lectura del `quality-catalog.json.gz` en el worker.
- [x] Implementar caché lógica de runtime por coordinador con objetos físicos
  compartidos por SHA-256; las 58 pruebas dirigidas actuales pasan.
- [x] Ejecutar un circuito final con ambos coordinadores después del cambio de
  caché y comprobar que alternarlos no vuelve a transferir 162,7 MB ni mezcla
  sus punteros `current`.
- [x] Elegir versión definitiva (`1.0.42` o `1.1.0`), sustituir el tag temporal
  `multicoordinator-test`, reconstruir conservando exactamente los dos destinos
  actuales y comprobarlos después.
- [x] Hacer commit selectivo de los cambios de código/pruebas del worker.
  Excluir y preservar `mushroom-data/mushroom_observations.json`.
- [ ] Completar el CLI por `coordinator_id`: listar, seleccionar, cambiar URL,
  reemparejar, limpiar credenciales y olvidar un coordinador concreto sin tocar
  los demás.

## P1 — Rendimiento y observabilidad

- [ ] Medir por separado preparación, sincronización, cálculo, transferencia,
  validación/publicación en HA y renderizado. El último precálculo real registró
  `0,40 s` de sincronización, `467,96 s` de cálculo y `55,71 s` de publicación.
- [ ] Investigar los aproximadamente 56 segundos de publicación en HA sin
  reintroducir validación profunda por consulta ni debilitar la validación única
  antes de activar el SQLite.
- [ ] Continuar la optimización del camino frío solo a partir de perfiles
  medidos y respetando el presupuesto de la Raspberry Pi 4.
- [ ] Instrumentar por fases la recepción HA--worker y aplicar, si las medidas
  lo justifican, el diseño de streaming, recibos fuertes y eliminación de
  rehashes redundantes descrito en
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.
- [ ] Medir en la Raspberry Pi 4 el coste real de los `fsync` por fichero en los
  bundles multiversión antes de modificar su política de durabilidad.

## P1 — Predictor y ciencia aplazada

- [x] Reconstruir el worker desde el worktree con el gate de modelos constantes
  y ejecutar el circuito completo de reentrenamiento, promoción automática y
  precálculo antes de considerarlo operativo.
- [ ] Crear el catálogo explícito de especies posibles por área.
- [ ] Sustituir `Historial` en HA por el evaluador persistido del catálogo
  hold-out; el precálculo semanal no contiene `history`.
- [ ] Mejorar los mensajes de incompatibilidad para diferenciar
  reentrenamiento, precálculo, cobertura y corrupción.
- [ ] Repetir la comparación del contador de racha seca actual, `<1 mm` y sin
  contador cuando existan nuevos grupos independientes suficientes.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando sus hold-outs externos
  contengan ambas clases.
- [ ] Decidir si se implementa una tendencia predictiva de siete días. No usar
  los ceros placeholder de Rovelló ni presentarla como regla biológica.
- [ ] Repetir la auditoría de microáreas solo cuando existan más episodios
  simultáneos positivos/negativos. No crear modelos por identificador de
  microárea ni reglas altitudinales fijas.

## Completado en esta sesión

- [x] Implementar un gate por especie que detecta probabilidades hold-out
  constantes, las excluye de la selección sellada y las vuelve a vetar en el
  selector compartido por el precálculo.
- [x] Publicar HA `0.2.295` con lecturas directas de una respuesta SQLite
  sellada, sin cientos de lecturas ni validaciones redundantes por consulta.
- [x] Publicar HA `0.2.296` para conservar el último precálculo durante la
  sustitución del runtime, resolver consultas fechadas a través de medianoche y
  evitar reencolados de deseos ya publicados.
- [x] Verificar que `0.2.296` y `latest` comparten el digest multi-arquitectura
  `sha256:877f1b369daed6f6cffdcbf1e512ef572d318244077988eb5016e1f4c9d30919`.
- [x] Reconstruir HA local con la misma versión y comprobar en HA real que
  `Esta semana`, `Por especie` y `Consultar fecha` sirven resultados rápidos.
- [x] Completar un precálculo real de 30.253.056 bytes después de la corrección
  de caché, con sincronización de runtime de `0,399661 s`.
- [x] Confirmar que el fallback al SQLite anterior funciona mientras el runner
  meteorológico termina y el precálculo nuevo aún no está publicado.
- [x] Documentar el análisis exacto de la abstención de Rovelló en Els Ports y
  dejar cualquier cambio de reglas o UI para la siguiente sesión.
- [x] Completar el entrenamiento multiversión con 636 artefactos, promover el
  batch `operational_20260908T000329Z` y publicar el precálculo de 420 miembros
  sin seleccionar ningún modelo hold-out constante.
- [x] Reconstruir el worker local como `1.1.0`, comprobar su código efectivo y
  conservar sin cambios sus coordinadores principal y HA local.
- [x] Publicar HA `0.2.297` y `latest` con el mismo índice multi-arquitectura
  `sha256:07d3eb86efcfc2e6ba2ed02193c19d1503efba021a6256c95b858d71e24fcbfe`.
- [x] Auditar el protocolo de integridad y documentar una optimización futura
  de streaming sin debilitar la validación semántica ni la promoción atómica.
