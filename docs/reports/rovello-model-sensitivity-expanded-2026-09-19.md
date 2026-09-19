# Rovelló: ampliación de sensibilidad V2–V4 — 19/09/2026

## Alcance y límites

Auditoría de inferencia local, sin reentrenamiento, publicación ni modificación
de las suspensiones. Se reutilizó el lote aislado `audit_fresh_20260919`, ya
entrenado con las copias actualizadas. No representa una lectura nueva de HA real.
Meteorología fijada a `20260918T215356489746Z-e8b02c29756f`; emisión 19/09,
corte observado 18/09. Modelos verificados por hash antes de cargar; identidad
de modelo/meteorología comprobada también al terminar.

Cinco puntos: Pradell, Capolat, Vallcebre, Gósol y Urús; siete horizontes.
Quince combinaciones de HGB/KNN/SVM: V2, V3 core, V3 con estado físico, V4
meteorología extendida y V4 balance climático. Partial-30 se utiliza como
control, sin que ello acredite su precisión micológica.

25 escenarios por punto: basal, 12 perturbaciones grandes de lluvia/temperatura/
humedad y 12 trazas (+0,001/+0,01/+0,1 mm a edades 0/7/16/30 días). Total:
**125 casos y 14.000 resultados**, incluidos los rechazados. Cambios posteriores
al IDW, anteriores a reconstruir atributos. No prueban toda la respuesta espacial,
otras especies ni otras fechas. Contenedor sin red, entradas de solo lectura,
2 CPU y 3 GiB máximos; no se alteró el servicio del worker ni su coordinador.

## HGB: el defecto también existe en V3 y V4

Ejemplos de salida bruta al añadir **0,01 mm a 16 días**:

| Modelo | Punto | IFF antes → después | Salto |
| --- | --- | --- | --- |
| HGB-V2 | Vallcebre | 58,7469 → 99,5327 | +40,7858 |
| HGB-V3 core | Vallcebre | 15,5729 → 96,7319 | +81,1590 |
| HGB-V3 con estado físico | Pradell | 12,8001 → 88,7021 | +75,9020 |
| HGB-V4 meteorología extendida | Urús | 54,7293 → 96,3059 | +41,5766 |
| HGB-V4 balance climático | Urús | 50,6148 → 93,5265 | +42,9117 |

Los cinco artefactos tienen divisiones aprendidas en el acumulado de 15–21 días
con umbrales de 0,002 mm; los de V3/V4 también incluyen algunos de 0 o 0,001.
Restaurar únicamente ese acumulado al valor basal devuelve exactamente el IFF
basal en los cinco ejemplos. El cambio de contador de días lluviosos no explica
esos saltos de HGB-V4.

**Salida bruta no equivale a predicción operativa.** HGB-V3/V4 no estaban en la
cadena semanal de candidatos de especie del lote auditado. Además, HGB-V3 core
falla controles Brier/ROC; otros fallos dependen del horizonte. Algunos miembros
HGB-V3+/V4 pasan los controles individuales, pero eso no los incorpora por sí solo
a la cadena sellada. Esta protección actual no corrige el artefacto ni garantiza
que otro entrenamiento no vuelva a admitirlo.

## SVM: versiones diferentes, comportamiento diferente

- SVM-V2 conserva la saturación ya diagnosticada; suspensión anterior intacta.
- SVM-V3: máximo cambio admitido con +0,01 mm de aproximadamente **0,0127 IFF**
  entre ambos perfiles. Las curvas varían; no se reprodujeron los grandes saltos
  de HGB. No es una validación de calibración o precisión de campo.
- SVM-V4: +0,001 mm ya causa cambios de **1,6455** (extendido) y **1,2314**
  (balance); +0,01 mm produce **1,6466** y **1,2326**, respectivamente.
  Son casos admitidos y ambas variantes están en la cadena de candidatos.

Intervención diagnóstica en Vallcebre, horizonte 6: SVM-V4 extendido pasa de
83,5909 a 85,2375. Restaurando solo `rainy_days_cutoff_15_21d` de 1 a 0,
queda en **83,5922**. Para balance: 84,7089 → 85,9415; restaurando el contador:
**84,7102**. El incremento casi entero procede de contar una traza como un día
de lluvia. Las intervenciones sobre atributos son diagnósticos, no nuevos
escenarios meteorológicos físicamente coherentes.

Código causal: `mushroom_ml_biology_v4.py:612` cuenta valores `> 0.0`.
`mushroom_ml_biology_v3.py:821` también corta la racha seca con `> 0`.
Corregir esta semántica requeriría coherencia entre entrenamiento e inferencia;
no se ha cambiado ningún umbral en esta auditoría.

## KNN: tampoco basta con que la curva deje de ser plana

- V2 repite 88,8889 en los 35 resultados basales.
- V3/V4 alternan mesetas y escalones. Ejemplo bruto V3 con estado físico en
  Pradell: **78,61 → 88,89 → 78,22 → 78,05 → 78,08 → 78,25 → 78,47**.
  En Urús ambos KNN-V3 repiten 88,8889 toda la semana. No todas estas celdas
  pasan los filtros individuales, y ningún KNN-V3/V4 figura en la cadena semanal
  auditada. No se han contado aquí observaciones únicas detrás de sus vecinos.
- KNN-V4: +0,001 mm puede producir unos **−11,32 IFF brutos**. Los máximos
  aparecen en Capolat y están rechazados por aplicabilidad/calidad. Con +0,01 mm,
  restaurar solo el contador de días lluviosos reduce la diferencia a menos de
  0,001 IFF. El salto no debe presentarse como una predicción operativa aceptada.
- En los pares que sí pasan los controles individuales, el máximo cambio de
  KNN-V4 extendido con +0,01 mm es **0,0069 IFF**. KNN-V4 balance no tiene pares
  admitidos; eso no equivale a respuesta nula ni a estabilidad acreditada.

## Decisión que permite la evidencia

Recomendar extender la suspensión de HGB a ambos perfiles V3 y V4 para rovelló.
Revisar KNN-V3/V4 por estabilidad temporal y vecinos, y SVM-V4 por la semántica
de día lluvioso. No extrapolar el fallo de SVM-V2 a SVM-V3 sin evidencia.
La auditoría no amplía automáticamente las suspensiones: siguen siendo las
tres decisiones previas de HA local. Una corrección de atributos necesita
reentrenamiento; suspender un modelo ya entrenado solo requiere renovar las
predicciones y el precálculo.

Evidencia reproducible local: `tmp/rovello-response-audit-20260919/expanded.py`,
`summarize_expanded.py`, `isolate_expanded.py`, `expanded-results.jsonl.gz`
(790.660 bytes), `expanded-summary.json` y `expanded-causal.json`. Se retiró
la salida temporal sin comprimir tras verificar su hash; no se duplicaron
modelos ni históricos.

## Aplicación autorizada y revisión posterior

Tras autorización del usuario se guardaron mediante el POST del formulario local
las cuatro reglas HGB-V3/V4 recomendadas. Lectura posterior del registro: siete
suspensiones para rovelló, incluidas las tres V2 anteriores. Ninguna regla nueva
para SVM-V3/V4 o KNN-V3/V4; HA real no fue modificado.

Revisión adicional de KNN sobre los cinco artefactos lag del lote auditado,
hash verificado y solo lectura: cada uno tiene 406 filas entrenadas. Excluyendo
solo el horizonte, hay 357 patrones distintos en V2 y 323 en V3/V4. Entre los
siete vecinos de las consultas basales se observan 7 patrones en V2, 6–7 en
V3 core, 7 en V3 físico, 4–7 en V4 extendido y 6–7 en V4 balance. Esto NO cuenta
observaciones independientes: una misma observación puede generar varios
atributos temporales distintos. Los bundles no contienen IDs de observación y
los intermedios de preparación fueron eliminados tras la auditoría anterior.
No se reconstruyeron esos datos ni se entrenó otra vez para recuperarlos.
Evidencia compacta: `knn_pattern_audit.py` y `knn-patterns.json` en el directorio
de auditoría. La independencia debe comprobarse con los IDs de las filas del
siguiente entrenamiento; la inspección de patrones no la demuestra.

La causa del salto por día lluvioso está localizada, pero no se ha fijado un
umbral nuevo arbitrario. Una corrección debe definir el criterio común para
contar días y cortar rachas secas, versionar el contrato de atributos, mantener
compatibilidad con los modelos existentes y comparar el resultado de nuevos
entrenamientos. No basta con modificar solo la inferencia, redondear lluvia o
suavizar la curva mostrada. La verificación del entrenamiento local iniciado por
el usuario sigue pendiente; las suspensiones no deben impedir entrenar modelos.
