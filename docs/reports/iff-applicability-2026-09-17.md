# IFF y aplicabilidad por punto — 17/09/2026

Cambio solicitado por el usuario: explicar las abstenciones, auditar los dos
puntos cercanos y permitir extrapolación moderada con aviso, conservando el
rechazo de extremos. Implementado e instalado después en HA local y worker por petición expresa;
incluido después en la publicación HA 0.2.309. Instalación en HA real pendiente;
véase [informe de release](ha-release-0.2.309.json).

## Diagnóstico y decisión acotada

Los puntos (41.43290, 2.11928) y (41.43460, 2.12029) usaban el mismo batch
`operational_20260916T124724Z`, revisión `96a9ec65ae3d362ace81` e histórico
`20260917T093103193779Z-40277240758d`. En Aereus/30 días el primero tenía
6/160 entradas fuera de rango y el segundo 8/160. El segundo alcanzaba el veto
del 5 %, aunque el resultado bruto pasaba solo de 0,343404 a 0,323437.
Una entrada que cruza el máximo es `temp_min_c__lag_009`: 22,692246 frente a
22,831533 °C, con máximo de entrenamiento 22,734823 °C.

Política candidata `magnitude_v2` en `_prediction_payload`:

- Dentro de mínimos/máximos: `within_observed_range`.
- Fuera de rango sin alcanzar el veto por magnitud: `caution`, con aviso visible.
- Fuera de rango y distancia absoluta a la media ≥3 desviaciones estándar:
  `outside_domain`. Se conserva el umbral existente, sin elevarlo.
- Una salida del rango de una variable constante (desviación cero) se rechaza.
- La excepción existente de lluvia sigue siendo solo advertencia.
- El porcentaje de columnas se conserva como diagnóstico y deja de bloquear.
  Días de una misma serie son entradas separadas; su recuento no mide por sí
  mismo cuánto se aleja cada valor.

No cambian los valores emitidos por cada estimador, la evidencia por especie,
las reglas ecológicas ni los mínimos de calidad Brier/ROC-AUC. Sí puede cambiar
el candidato elegido al dejar de vetar uno mejor situado. La política afecta
a la inferencia compartida, no solo a la presentación del mapa. Artefactos de
precálculo anteriores no se reescriben ni se regeneran en esta tarea.

## Comparación real con modelos existentes

Valores del primer día (17/09/2026), redondeados a IFF:

| Especie | Primer punto antes → después | Segundo punto antes → después |
| --- | --- | --- |
| Aereus | 34 → 21 | Sin IFF → 19 |
| Ou de reig | 4 → 4 | 0 → 3 |
| Lactarius deliciosus | 53 → 43 | Sin IFF → 44 |

Aereus elige ahora V6, 90 días, Shared Logistic en ambos puntos. Su evaluación
persistida tiene 22 casos (11 positivos/11 negativos), Brier 0,14398 frente a
0,26 de prevalencia y ROC-AUC 0,946281. Es evidencia previa del modelo, **no
validación de la extrapolación en estas coordenadas**. No se recalibró el umbral
de 3 desviaciones ni se demostró mejora predictiva con nuevos casos etiquetados.
Los valores mostrados permanecen experimentales y llevan aviso.

## Presentación y comprobaciones

El mapa distingue «Sin modelo disponible», «Fuera de rango» e «IFF con
extrapolación · interpretar con cautela». El detalle desplegable muestra recuento
y hasta tres entradas con valor/rango de entrenamiento. Traducciones ES/CA/EN.
También se advierte en el tooltip del gráfico. Las explicaciones diarias se
deduplican por especie mediante referencias; dos respuestas de prueba con
geografía y predicción: 19.043 y 19.048 bytes, sin serie meteorológica adicional.

- 121 pruebas Python dirigidas: inferencia, selección semanal, contrato del
  mapa, selector multiversión, servicio Predictor y auditoría de fiabilidad.
- Chrome aislado: aviso, detalle, fecha, ausencia de modelo, abstención extrema,
  tooltip y regresiones del visor compartido, incluyendo móvil e idiomas.
- Dos consultas reales con los datos/modelos de HA local, cargando el código
  candidato exclusivamente en un proceso de prueba. No se modificaron los
  procesos del servicio, ni la configuración/destinos del único worker.
- Evidencia local preservada: `tmp/aereus-points-20260917/` (antes) y
  `candidate/` (fuentes ensayadas, después y `validation.json`).

## Instalación local posterior, 17/09/2026

Por petición expresa, reconstruidos y recreados HA local y el único worker
con el mismo worktree, sin cambiar etiquetas de versión ni destinos. Paridad
real dentro de contenedores: 200 archivos HA y 107 worker, ninguna diferencia.
Ambos destinos conservan exactamente las huellas registradas antes de recrear.

Prueba por API de HA local con usuario/dispositivo temporal retirados al acabar:
los dos puntos en ejecución local y worker, igualdad salvo ID/tiempos. Aereus
0,205671 y 0,191804, ambos `caution`. JS/CSS servidos corresponden al código
instalado. Respuestas completas de 23.149–23.159 bytes. Observaciones del usuario,
setales y registro de modelos comprobados sin cambios de SHA. Worker healthy.
Evidencia: `tmp/iff-local-install-20260917/{parity,api-validation,preserved-before,preserved-after}.json`.

Queda instalado para revisión del usuario y pendiente de la próxima release.
HA real no actualizado. No hubo entrenamiento, precálculo ni publicación;
esta validación acotada no sustituye las comprobaciones de una futura release.
