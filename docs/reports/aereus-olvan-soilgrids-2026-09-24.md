# Aereus en Olvan y aviso SoilGrids — 24/09/2026

Diagnóstico de artefactos persistidos de HA real mediante SMB LAN, sin ejecutar
entrenamiento, precálculo ni reconstrucción del runtime. Instalación real a cargo
del usuario. `runtime_state.json` confirma HA 0.2.321; 0.2.322 está publicada.

## Saltos de IFF

El precálculo activo reproduce 89 → 53 → 75 → 75 → 75 → 75 → 75 para
Boletus aereus / Olvan, 24–30/09/2026. Es un único estimador HGB-V2 compartido
entre horizontes, con corte meteorológico fijo 23/09. No hay cambio de familia.

| Transición | Días desde lluvia | Primer umbral divergente | Árboles con trayectoria distinta | IFF sin redondear |
| --- | --- | --- | --- | --- |
| 24 → 25/09 | 15 → 16 | 15,5 días | 26 | 88,7201 → 53,2749 |
| 25 → 26/09 | 16 → 17 | 16,5 días | 21 | 53,2749 → 75,4148 |
| 26 → 27/09 | 17 → 18 | horizonte 3,5 | 1 | 75,4148 → 74,7626 |
| 27 → 30/09 | 18 → 21 | Sin trayectorias distintas | 0 | 74,7626 |

Las variables que cambian son `horizon_days`,
`days_since_rain_gt_2_at_target` y `days_since_significant_rain_at_target`.
La lluvia significativa persistida es del 09/09/2026 (47,1419 mm).
El modelo contiene 150 árboles; el recorrido local de sus nodos reproduce los
valores del precálculo. La selección semanal mantiene la familia, pero no impone
continuidad a la respuesta aprendida de sus árboles. Los siete días figuran
dentro del rango observado de entrenamiento; esto no acredita estabilidad temporal.

No se ha suavizado el resultado, suspendido el modelo ni cambiado entrenamiento.
Una eventual corrección requiere evaluar estabilidad temporal y validación del
modelo; ocultar el salto sólo en el gráfico no resuelve la predicción.

### Fuentes primarias

- `/Volumes/media-1/rainmapper/results/predictor-precompute/active.sqlite3`,
  consultas acotadas a `species_context` y `operational_members` para Olvan/Aereus.
- `active-receipt.json`: revisión 237, artefacto
  `sha256:653dac31bbb3e2cb19e45e62a32c620e590b8d87cc88557abbb84a644ddcb422`.
- Batch `operational_20260924T130123Z`, generación
  `altitude_v2_operational_20260924T130123Z`; modelo
  `altitude_v2/lag_event_altitude_v2/common_idw/hist_gradient_boosting_restricted_v1/boletus_aereus.joblib`.
- SHA-256 del modelo verificado contra el manifiesto:
  `48254534db65d8aa554df63ad0eb5ca15df3e3f3cbfa0fbf97007fa97287559c`.
- Auditoría local no versionada: `tmp/aereus-olvan-20260924/tree-audit.json`,
  `inspect_trees.py`, `olvan-members.json`, `olvan-resolutions.json`.

## Microárea SoilGrids

La única microárea pendiente es **Can Brunet**, área **Dosrius**,
ID `dosrius_can_brunet`. Su contexto tiene estado `partial`, cobertura
`0.944354` (94,44 %). No es Olvan.

Fuentes: `mushroom_known_sites.json` y
`diagnostics/soilgrids-reconciliation-latest.json` bajo
`/Volumes/share-1/rainmapper/mushroom-data/`. La reconciliación de 12:58:35 UTC
declara 91 contextos actuales, 90 completos, 1 parcial y 0 intentos de descarga.
Un contexto parcial actual se conserva; el texto previo que prometía reintento
automático con una reconstrucción no describía este caso.

`mushroom_soilgrids.py` clasifica como completo a partir de 0,999 de cobertura;
`mushroom_soil_water_state.py` exige estado completo. No se han relajado estos
criterios ni alterado geometrías/datos para forzar aceptación.

### Corrección de presentación posterior a 0.2.322

El aviso del Predictor ahora enumera área y microárea, estado y porcentaje
disponible. Cada nombre abre su ficha de mantenimiento. Traducciones ES/CA/EN;
nombres escapados e identificadores codificados en URL. Quitada la promesa de
reintento automático. No se consultan rásteres ni servicios externos para renderizar.

Validación: tres pruebas dirigidas (aviso, cobertura/escape y selección de ficha),
Chrome con HTML real y fixture aislada, sin errores ni desbordamiento.
HA local reconstruido/recreado; worker sin reconstrucción/reinicio por este cambio.
Esta corrección **no está en la imagen 0.2.322 publicada**.
