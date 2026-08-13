# Registro canónico de versiones de contratos ML

Este documento es el registro permanente de por qué existen las versiones del
modelo micológico. No confundirlas con la versión del add-on HA (`0.2.x`) ni con
la imagen del worker (`1.0.x`): esas versiones indican software desplegado; los
identificadores siguientes describen el significado de los datos y modelos.

## Resumen

| Contrato | Estado | Cambio principal |
| --- | --- | --- |
| `mushroom_ml_v0` | REFERENCIA | Primer clasificador operativo, sin corte meteorológico causal estricto. |
| `fixed_gap_7d_v1`, `lag_event_v1` | REEMPLAZADO por altitude V2 | Cortes meteorológicos reproducibles y sin fuga temporal. |
| `fixed_gap_7d_altitude_v2`, `lag_event_altitude_v2` | VIGENTE | Temperatura trasladada de la altitud de estación a la altitud representativa del área. |
| `fixed_gap_7d_biology_v3`, `lag_event_biology_v3` | BENCHMARK LOCAL, NO OPERATIVO | Observaciones preservadas, targets, IDW de área, separación de calidad y grupos de florada 7/14. |

## V0 — modelo inicial

- Introdujo artefactos por observación, entrenamiento por especie y Predictor.
- Se conserva para trazabilidad y diagnóstico, no como contrato recomendado.
- Parte de sus variables podían usar meteorología demasiado próxima o posterior
  a la fecha de emisión; por eso no sirve de referencia causal definitiva.

## V1 — contratos temporales

- `fixed_gap_7d_v1`: ventana ciega fija de siete días.
- `lag_event_v1`: corte meteorológico según fecha de emisión y eventos de lluvia.
- Ambos hacen explícitos cobertura, ausencias, lluvia suprimida, estación
  elegida, horizonte y fecha de corte. Los huecos no se convierten en lluvia
  cero salvo las reglas explícitas del contrato meteorológico.
- Fueron la primera base reproducible para comparar familias de estimadores.
- Quedan congelados como referencia. No deben promocionarse bajo un runtime que
  solicite altitude V2.

## Altitude V2 — corrección térmica por altitud

Es un cambio aislado sobre V1, no Biology V3.

- Contratos vigentes: `fixed_gap_7d_altitude_v2` y
  `lag_event_altitude_v2`.
- Antes de construir variables térmicas se aplica:

  `T_area = T_station + (z_station - z_area) / 100 * 0,65 °C`

- `z_station` procede del catálogo meteorológico y debe materializarse en
  `weather_station_altitude_m` durante la reconstrucción.
- `z_area` es la media de las altitudes DEM medias de todas las microáreas
  materializadas del área. No depende solo de las observaciones del episodio.
- Si falta una de las altitudes, no se usa silenciosamente la temperatura cruda.
- Se sustituyen umbrales térmicos globales hardcoded por variables continuas
  corregidas. La respuesta conserva estación, ambas altitudes, gradiente y
  corrección aplicada para auditoría.
- Rebuild y training deben ejecutarse con software V2. Entrenar V2 sobre un
  `features.json` antiguo sin `weather_station_altitude_m` no es válido.
- La promoción debe exigir exactamente ambos identificadores V2 en el
  manifiesto de entrenamiento.

### Compatibilidad operativa

- HA `0.2.254` está instalada y añade la barrera de promoción que rechaza
  manifiestos V1 incompatibles.
- Worker `1.0.7` es anterior: reconstruye features sin altitud de estación y
  entrena V1; no es compatible de extremo a extremo.
- Worker `1.0.8` desplegado incorpora reconstrucción, entrenamiento y metadatos
  altitude V2. La generación V2 completa fue promovida y validada en M1 y en el
  fallback HA el 2026-08-13.

## Biology V3 — benchmark local implementado

No es una tercera corrección técnica incremental de altitud. Es un rediseño más
amplio que debe comparar sus resultados contra altitude V2 congelado:

- cada observación original como muestra; las vistas microárea/fecha y
  área/fecha solo auditan conflictos y no reducen filas;
- targets favorable, desfavorable y desconocido sin inventar negativos;
- censura y sesgo de visitas explícitos;
- exclusión de metadata/quality de las variables predictivas cuando corresponda;
- grupos de validación por especie+área de 7/14 días sin segmentar el modelo por
  área, más calibración y Brier antes de
  cualquier propuesta de promoción.

La implementación local del 2026-08-13 añade contratos nuevos sin cambiar
V2: `outing_value_area_v1`, `area_microarea_evidence_v1`,
`observed_weather_quality_v1` y
`daily_rain_idw_radius15km_power2_v1`. La lluvia V3 es una serie IDW diaria en
el punto representativo de cada microárea, radio 15 km y potencia 2. Ausencias,
errores, repeticiones suprimidas y estaciones retiradas no se convierten en
cero. El contrato `area_daily_mean_microarea_idw_v1` agrega cada día mediante
la media de los IDW disponibles de todas las microáreas configuradas; descarta
el centroide calculado del área. El modelo acepta esta media como lluvia
canónica sin penalización ni advertencia por la procedencia de las estaciones.
Los dos feature sets construyen `predictive_features`, `quality` y `metadata`
por separado. Solo variables predictivas registradas pueden entrar en `X`; el
área y los contadores de cobertura no entran. La lluvia siempre usa la media
diaria de IDW de las microáreas configuradas. Temperatura y humedad relativa
del aire conservan el selector V2 sensible al corte; la corrección por altitud
se aplica a temperatura.

La reproducción local conserva 399 observaciones en `fixed_gap` y genera 1.596
muestras en `lag_event` para horizontes 1/2/3/7. Con altitudes DEM
materializadas en una copia de known sites resultan 204 y 816 muestras
elegibles, respectivamente. Los grupos de florada contienen 264 grupos a 7
días y 244 a 14 días, sin fusionar observaciones. Los cuatro horizontes no se
interpretan como cuatro observaciones independientes. No se persistió ningún
modelo.

La comparación equivalente reconstruye V2 por observación y encuentra 167
filas semanales comunes. La evaluación vigente no selecciona por un Brier
combinado entre especies: compara por separado contrato temporal, estimador y
especie. Dentro de cada contrato, LR, RF, ET, HGB, KNN y SVM RBF reciben la
misma `X`. Mes y altitud directa permanecen inactivos; la altitud sigue
corrigiendo la temperatura.

Las variables activas no contienen medias meteorológicas: lluvia IDW acumulada,
racha seca, extremos de temperatura y extremos de humedad relativa. Las medias
se conservan inactivas. El análisis fila a fila de las 15 parejas muestra que
RF+ET es la pareja más coincidente de forma sistemática, sobre todo en
`lag_event`, pero no existe un estimador ganador universal y el soporte por
especie sigue siendo pequeño. No autoriza promoción operativa.

La altitud de cada microárea se calcula y cachea al crear o cambiar su geometría;
no se consulta el DEM durante cada benchmark o predicción. La cadena local
Catalunya→Andorra→IGN MDT25 hoja 592 cubre las 58 microáreas actuales. Si una
microárea futura queda fuera de las tres coberturas, conserva `no_data`.

La especificación vive en
`docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`; hasta que pase sus
gates permanece en diseño y no sustituye altitude V2.

## Regla de continuidad

Cada contrato nuevo debe añadir aquí su motivación, entradas, cambio semántico,
compatibilidad de software, estado y contrato reemplazado. La compactación de
`active-context.md` nunca debe eliminar esta genealogía.
