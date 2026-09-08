# TODO

Prioridades vivas al cierre del 8 de septiembre de 2026. El estado operativo y
la evidencia exacta están en `docs/active-context.md`; las decisiones duraderas,
en `docs/decisions.md`.

## P0 — Instalar y comprobar HA 0.2.297

- [x] Publicar `0.2.297` y `latest` en GHCR con el mismo índice
  multi-arquitectura.
- [x] Reconstruir y recrear HA local desde HEAD; imagen, contenedor y código
  efectivo corresponden a 0.2.297 y la UI responde HTTP 200.
- [ ] Verificar la versión instalada actualmente en HA real.
- [ ] Si sigue en 0.2.296, instalar 0.2.297 y comprobar arranque, versión y uso
  del precálculo ya existente. No repetir entrenamiento ni precálculo salvo que
  aparezca una incompatibilidad real.

## P0 — Revisar abstenciones por aplicabilidad

- [ ] Auditar una muestra multiespecie de predicciones bloqueadas, separando
  tolerancia absoluta, desviación normalizada, tipo de variable y dirección de
  extrapolación.
- [ ] Usar como primer caso Rovelló / Els Ports / 2026-09-07: LR-V3 calculó
  `0,0016 %`, pero se abstuvo por humedad máxima `88,062 %` frente al mínimo
  aprendido `89,001 %` y temperatura máxima `33,151 °C` frente al máximo
  aprendido `30,933 °C`.
- [ ] Determinar por especie y tipo de variable si una diferencia absoluta
  pequeña puede bloquear por sí sola. No aplicar una tolerancia global.
- [ ] Diseñar la presentación de una probabilidad vetada como dato diagnóstico,
  con abstención inequívoca y sin color operativo, recomendación ni ranking.
- [ ] Separar en UI `modelo no disponible` de `modelo disponible pero rechazado
  por aplicabilidad`.

## P1 — Rendimiento e integridad HA--worker

- [ ] Instrumentar por separado lectura de red, hash/escritura temporal,
  `fsync`, validación semántica, promoción atómica y confirmación al worker.
- [ ] Medir esas fases en la Raspberry Pi 4 antes de cambiar el protocolo.
- [ ] Si las medidas lo justifican, hacer incremental la recepción del SQLite y
  reutilizar el digest calculado durante la escritura para evitar buffers y
  rehashes completos.
- [ ] Convertir los bundles multiversión a lectura/escritura acotada y medir el
  coste de los `fsync` por fichero antes de modificar su durabilidad.
- [ ] Mantener autenticación, límites, tamaño, SHA-256 extremo a extremo,
  validación semántica, staging y `os.replace`. No usar caché de hash basada
  solo en tamaño y `mtime`.
- Especificación de continuidad:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.

## P1 — Worker multicoordinador

- [x] Separar credenciales, heartbeats, claims y runtime lógico por coordinador,
  con objetos físicos compartidos por SHA-256.
- [x] Mantener dos carriles globales de trabajo sin multiplicar concurrencia por
  coordinador.
- [x] Cerrar el circuito local completo, versionar el worker como `1.1.0` y
  conservar exactamente los dos destinos actuales.
- [ ] Completar el CLI por `coordinator_id`: listar, seleccionar, cambiar URL,
  reemparejar, limpiar credenciales y olvidar un coordinador sin tocar los demás.

## P1 — Predictor y ciencia aplazada

- [ ] Crear el catálogo explícito de especies posibles por área.
- [ ] Sustituir `Historial` en HA por el evaluador persistido del catálogo
  hold-out; el precálculo semanal no contiene `history`.
- [ ] Mejorar mensajes de incompatibilidad para diferenciar reentrenamiento,
  precálculo, cobertura y corrupción.
- [ ] Repetir la comparación del contador de racha seca actual, `<1 mm` y sin
  contador cuando existan nuevos grupos independientes suficientes.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando sus hold-outs externos
  contengan ambas clases.
- [ ] Decidir si se implementa una tendencia predictiva de siete días. No usar
  ceros placeholder ni presentarla como regla biológica.
- [ ] Repetir la auditoría de microáreas solo con más episodios simultáneos
  positivos/negativos. No crear modelos por identificador de microárea ni reglas
  altitudinales fijas.

## Completado en la sesión cerrada

- [x] Crear el Explorador de modelos como aplicación de solo lectura del worker,
  accesible en `/models` y capaz de mostrar estructura, variables, pesos o
  importancias y rangos sin cargar el artefacto hasta pedir inspección.
- [x] Detectar modelos con probabilidad hold-out constante por especie y
  candidata exacta, excluirlos durante la selección y volver a vetarlos en el
  selector compartido por el precálculo.
- [x] Reentrenar ocho especies, producir 636/636 artefactos, promover el batch
  `operational_20260908T000329Z` y publicar un precálculo de 420 miembros sin
  seleccionar modelos constantes.
- [x] Reconstruir el worker local como `1.1.0`; dejarlo healthy e idle con sus
  dos asociaciones intactas.
- [x] Publicar HA `0.2.297`, reconstruir HA local con esa versión y confirmar
  paridad de cinco ficheros ejecutables centrales.
- [x] Documentar la auditoría del transporte HA--worker y la propuesta de
  streaming futuro sin retirar validación semántica ni promoción atómica.
- [x] Commit y push de la release en
  `6055dabc72a2ac7837a297f27cf905251d8fe2ae`, excluyendo y preservando
  `mushroom-data/mushroom_observations.json`.
