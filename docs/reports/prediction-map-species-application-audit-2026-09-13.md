# Comprobación de aplicación de las fichas locales

Verificación del 13/09/2026, solicitada por el usuario tras revisar el punto de
Santa Maria de Merlès. Solo lectura de datos; no se repite ninguna migración.

Se compararon el backup previo `.keep.json`, los 143 campos registrados en el
informe de aplicación y el archivo actual `docker-data/mushroom-data/mushroom_profiles.json`.
No hay discrepancias respecto a los valores finales registrados. La huella
actual coincide con la del informe de aplicación y con la leída mediante
`docker exec` dentro de `rainmapper-local-rainmapper-ha-ui-1`.

| Dimensión | Cambio comprobado respecto al backup |
|---|---|
| Altitud mínima/máxima | Modificada en 13 fichas. |
| Óptimos de altitud | Nueve parejas 0–0 se dejaron desconocidas. |
| Meses | Meses secundarios ampliados en 8 fichas; principales conservados. |
| Hospedadores | 25 asociaciones añadidas en 11 fichas. |
| Tipos de bosque | 12 asociaciones añadidas en 6 fichas. |
| Afinidades de suelo de las especies | Sin cambios en las 21 fichas. |
| Afinidades de litología de las especies | Sin cambios en las 21 fichas. |
| Rasgos de hábitat | Sin cambios en las 21 fichas. |
| pH de las especies | Dos campos añadidos por ficha, ambos `null` en las 21. |

La actualización de mappings GIS de suelo/litología fue otra operación y no
equivale a modificar las afinidades de suelo/litología de cada especie.

## Ejemplo que explica el resultado de Merlès

- Edulis: intervalo altitudinal anterior 1.000–2.100 m; actual 600–2.200 m.
  Se añadieron cinco hospedadores alternativos, entre ellos `host_quercus_spp`.
- Pinophilus: anterior 1.000–2.300 m; actual 600–2.300 m.
  Se añadieron cinco hospedadores alternativos, también `host_quercus_spp`.
- El punto de 623,2 m supera ahora ambos mínimos. Roble pubescente y encina
  coinciden con el género Quercus. El resultado procede de esas ampliaciones
  aplicadas, no de que el visor esté leyendo fichas anteriores.

## Qué quedó pendiente respecto al pH

Sí hubo propuestas y revisión por especie. El informe de revisión registra
`proposed_ph_numeric_bounds: null` y exclusión por pH desactivada para las 21.
La decisión posterior autorizó ventanas amplias utilizables, pero la aplicación
solo añadió campos vacíos. En la conversación anterior se comunicó el
13/09 a las 11:09:17 UTC: «He añadido los campos y su guardado, pero todavía
falta completar los valores de pH».

La ausencia de valores guardados no demuestra por sí sola que nunca se hicieran
propuestas. No se ha encontrado una tabla de límites numéricos por especie en
los documentos y mensajes revisados. No deben presentarse las fichas como una
revisión ecológica completamente trasladada a datos: suelo/litología siguen
con sus relaciones anteriores, y los valores pH continúan pendientes.

Evidencia detallada, huellas y diferencias por especie:
[registro JSON](prediction-map-species-application-audit-2026-09-13.json).
