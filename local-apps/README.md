# Aplicaciones locales

Herramientas de investigación independientes de HA y del worker.

| Aplicación | Código | Datos privados | Abrir |
| --- | --- | --- | --- |
| Wunderground | `wunderground/code/` | `wunderground/data/` | `./local-apps/wunderground/start.command`, después http://127.0.0.1:8123/ |
| GBIF | `gbif/code/` | `gbif/data/` | `./local-apps/gbif/start.command` |

Los lanzadores se pueden ejecutar desde cualquier directorio. `data/` está
excluido de Git; `local-apps/` completo está excluido del contexto Docker.
No borrar datos por considerarlos caché: incluyen revisiones manuales y fotografías.

La migración del 19/09/2026 se hizo mediante movimientos dentro del mismo disco,
sin duplicar los snapshots. Los enlaces en la antigua ubicación de GBIF mantienen
sus URL `file://`; no son otra copia de los datos.
