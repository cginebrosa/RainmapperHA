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
| `fixed_gap_7d_biology_v3`, `lag_event_biology_v3` | DISEÑO, NO IMPLEMENTADO | Rediseño posterior de unidad biológica, targets, deduplicación, censura y validación. |

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

- HA `0.2.253` contiene el Predictor altitude V2; HA `0.2.254` añade la barrera
  de promoción que rechaza manifiestos V1 incompatibles.
- Worker `1.0.7` es anterior: reconstruye features sin altitud de estación y
  entrena V1; no es compatible de extremo a extremo.
- Worker `1.0.8` desplegado incorpora reconstrucción, entrenamiento y metadatos
  altitude V2. La barrera de promoción correspondiente se prepara en el
  coordinador para rechazar manifiestos V1.

## Biology V3 — siguiente investigación

No es una tercera corrección técnica incremental de altitud. Es un rediseño más
amplio que debe comparar sus resultados contra altitude V2 congelado:

- unidad canónica microárea/fecha y deduplicación de observaciones;
- targets favorable, desfavorable y desconocido sin inventar negativos;
- censura y sesgo de visitas explícitos;
- exclusión de metadata/quality de las variables predictivas cuando corresponda;
- validación temporal, soporte por especie, calibración y Brier antes de
  cualquier propuesta de promoción.

La especificación vive en
`docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`; hasta que pase sus
gates permanece en diseño y no sustituye altitude V2.

## Regla de continuidad

Cada contrato nuevo debe añadir aquí su motivación, entradas, cambio semántico,
compatibilidad de software, estado y contrato reemplazado. La compactación de
`active-context.md` nunca debe eliminar esta genealogía.
