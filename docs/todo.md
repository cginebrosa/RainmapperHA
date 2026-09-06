# TODO

Prioridades vivas al cierre del 6 de septiembre de 2026. El estado operativo
breve está en `docs/active-context.md`; las decisiones duraderas, en
`docs/decisions.md`.

## P0 — Materializar y comprobar el KNN suavizado en local

- [x] Auditar los extremos KNN con los mismos grupos hold-out y todas las
  especies/versiones seleccionadas disponibles.
- [x] Comparar calibración Platt, isotónica y suavizado `(7p + 1) / 9`. Adoptar
  el suavizado porque mejora Brier, ECE y log-loss sin cambiar ROC-AUC.
- [x] Implementar un único KNN activo
  `knn_distance_beta_smoothed_v2`, conservando el anterior solo para historia.
- [x] Aplicar la misma salida a entrenamiento, hold-out e inferencia; migrar las
  definiciones empaquetadas V2--V4 y mantener generaciones persistentes.
- [x] Evitar certezas visuales: mostrar `>99 %` y `<1 %` en predicciones sin
  modificar probabilidades ni porcentajes empíricos de acierto.
- [x] Validar el worktree: 1.283 pruebas de la suite completa, prueba adicional
  de migración del registro, compilación, JSON y `git diff --check` correctos.
- [x] Reconstruir y recrear HA local. Verificar dentro del contenedor el nuevo
  ID y la migración del registro. No usar worker.
- [x] Ejecutar entrenamiento operativo local normal con `docker-data`; comprobar
  observaciones elegibles, perfiles, ajustes, métricas, catálogo y que la nueva
  generación no contiene `knn_distance_v1`.
- [x] Ejecutar después el precálculo local; verificar `quick_check`, cobertura,
  tamaño, miembros/payloads y las tres vistas del Predictor.
- [x] Revisar en UI extremos, fallback, advertencias de lluvia y `MOD_0001`.

## P0 — Próxima release HA

- [x] HA `0.2.292` fue publicada antes del cambio KNN.
- [x] No instalar `0.2.292` como release del KNN suavizado. Elegir una versión
  HA posterior y seguir `docs/release-flow.md` cuando el usuario autorice
  bump/build/push.
- [x] Instalar esa nueva HA en el equipo real; confirmar versión desde
  Diagnostics y ejecutar en orden entrenamiento → precálculo.
- [x] Medir en la RPi4 recepción, validación y activación del SQLite deduplicado.
  Confirmar que no reaparece el timeout al 95 % observado con el artefacto de
  465 MB.
- [x] Reconstruir/versionar el worker porque se utilizó para entrenamiento y
  precálculo remoto. La versión comprobada es `1.0.41`.

## P1 — Auditoría científica pendiente

- [x] Auditoría hídrica multiespecie/multiversión para Rovelló, Edulis,
  Pinícola, Aereus y Ou de reig, con ablaciones de lluvia, temperatura,
  humedad, altitud, balance/SMI y retardos.
- [x] No crear V7: la interacción lluvia × suelo añadida no mejora de manera
  estable sobre los ganadores actuales.
- [x] Mantener `MOD_0001`: ecología y ventanas son diagnóstico, nunca veto o
  corrección de la predicción.
- [x] Mantener por ahora la definición actual de racha seca; `<1 mm = seco` no
  mostró mejora estable. Conservar siempre esas cantidades en variables
  continuas y balance hídrico.
- [ ] Repetir la comparación contador actual / `<1 mm` / sin contador cuando
  existan nuevos grupos independientes suficientes.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando sus hold-outs
  externos contengan ambas clases; repetir por área solo con soporte adecuado.
- [ ] Definir, si se continúa, «señal hídrica antecedente» con periodo, fuente,
  acumulado, cobertura e incertidumbre. No copiar «lluvia de activación» ni
  probabilidades de Sporas.io.
- [ ] Decidir si se implementa una **tendencia predictiva** de siete días para
  sustituir el antiguo texto de ventana. No usar los ceros placeholder de
  Rovelló ni presentar la tendencia como regla biológica.
- [x] Auditar de forma no destructiva el cambio de contexto de área a microárea
  para las ocho especies y los 11 perfiles operativos. No desplegarlo: mejora
  global de Brier de solo `0,225 %`, separación correcta de episodios mixtos en
  `52,8 %` de evaluaciones y coste incompatible con la RPi4 usando los JSON
  expandidos actuales.
- [ ] Repetir la auditoría de microáreas solo cuando existan más episodios
  simultáneos positivos/negativos en varias áreas y campañas. No crear modelos
  por identificador de microárea ni reglas altitudinales fijas.

## P1 — Predictor y datos

- [ ] Crear el catálogo explícito de especies posibles por área.
- [ ] Sustituir Historial en HA por el evaluador persistido del catálogo
  hold-out; el precálculo semanal no contiene `history`.
- [ ] Mejorar los mensajes de incompatibilidad: diferenciar reentrenamiento,
  precálculo, cobertura y corrupción.
- [x] Comprobar y retirar la antigua carpeta local de precálculo: contenía un
  SQLite de cero bytes y un staging vacío; el estado activo está bajo
  `docker-media/rainmapper/predictor_precompute/`.

## P2 — Rendimiento y observabilidad

- [x] Medir el nuevo entrenamiento y precálculo local de forma comparable al
  lote anterior: duración, ajustes, lecturas, inferencias, tamaño, miembros y
  payloads.
- [ ] Instrumentar por separado cálculo, transferencia, validación/publicación
  en HA y renderizado.
- [ ] Continuar la optimización por perfil medido según
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`.

## Completado en la sesión cerrada

- [x] Auditoría P0 científica, hídrica, aplicabilidad de lluvia, racha seca y
  probabilidades extremas documentada con runners reproducibles.
- [x] Revalidación de las observaciones nuevas del 5 de septiembre dentro del
  hold-out agrupado y explicación de por qué su tamaño siguió siendo 16.
- [x] Diagnóstico de la falsa ventana de Rovelló: `fruiting_timing=unknown` y
  límites cero de relleno, no pérdida del payload.
- [x] Implementación y validación del KNN suavizado y del formato honesto de
  probabilidades extremas.
