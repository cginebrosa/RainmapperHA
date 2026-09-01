# Auditoría de almacenamiento local — 2026-09-01

Auditoría de solo lectura del workspace
`/Users/carlosginebrosa/Developer/RainmapperHA`. No se borró ningún fichero.
Las cifras proceden de `du -sk`, del registro local vigente y del informe de
reconciliación generado por la propia aplicación.

## Resumen

- Tamaño total: `19.184.004 KiB`, aproximadamente `18,30 GiB` (unos `19 GB`
  decimales).
- `mushroom-GIS`: `7.943.576 KiB` (`7,58 GiB`). Son fuentes GIS y derivados de
  reconstrucción; no se consideran basura en esta auditoría.
- `docker-data`: `7.683.364 KiB` (`7,33 GiB`). De ellos, `6.837.384 KiB`
  (`6,52 GiB`) son auditorías históricas.
- `docker-media`: `2.551.068 KiB` (`2,43 GiB`). Contiene los modelos derivados
  vigentes y el precálculo activo.
- `.venv`: `534.212 KiB` (`0,51 GiB`), entorno de desarrollo reconstruible.
- `tmp`: `292.300 KiB` (`0,28 GiB`), laboratorios y cargas antiguas que deben
  revisarse antes de retirarlos porque el compose local monta `tmp` en
  `/app/tmp`.

## Espacio recuperable confirmado por la aplicación

`docker-data/mushroom-data/diagnostics/storage_reconciliation.json`, generado
el `2026-09-01T19:04:08Z`, declara:

- cero trabajos activos y cero errores;
- un único lote protegido:
  `local_operational_20260901T123855Z`, instalado por V2, V3, V4, V5w y V6w;
- nueve lotes operativos anteriores eliminables;
- ocho resultados ML huérfanos y dos bundles huérfanos;
- `1.857.696.686 bytes` (`1,73 GiB`) recuperables.

Este grupo debe retirarse mediante el reconciliador en modo `apply`, no con un
borrado manual, para que su inventario y su informe queden coherentes.

## Temporal de precálculo abandonado

`docker-data/mushroom-data/predictor_precompute/staging` ocupa `262.236 KiB`
(unos `256 MiB`). Contiene un SQLite temporal de `244 MiB` y su journal,
creados a las 16:13. El artefacto activo se publicó después, a las 16:27, en
`docker-media/rainmapper/predictor_precompute/active.sqlite3` y ocupa `442 MiB`.

El directorio `staging` aún se usa para construir precálculos locales, pero
esos dos ficheros concretos son residuos de una ejecución interrumpida. El
código elimina el nombre final del staging al terminar, pero no todos los
temporales auxiliares creados durante una escritura incompleta. Se puede
recuperar este espacio sin tocar el artefacto activo; queda además pendiente
cerrar esa limpieza automática y ubicar el staging reconstruible en `/media`.

## Auditorías históricas

`docker-data/audits` ocupa `6.837.384 KiB` (`6,52 GiB`):

- `mushroom-weather-backfill-20260811`: `4.227.104 KiB`;
- `ha-weather-history-check-20260823`: `1.094.624 KiB`;
- `official-weather-gap-repair-20260815`: `634.620 KiB`;
- `mushroom-ml-snapshot-20260816`: `484.320 KiB`;
- `mushroom-ml-v5-raw-discovery-20260816`: `384.880 KiB`;
- `mushroom-ml-v6-smooth-hierarchical-20260816`: `11.820 KiB`.

La arquitectura las clasifica expresamente como evidencia de laboratorio y no
como dependencias runtime. Borrarlas no impide ejecutar Rainmapper, pero varios
informes científicos enlazan sus manifiestos, predicciones, gráficas y datos de
reparación. Por tanto no se clasifican como basura automática: eliminarlas es
una decisión consciente de renunciar a esa evidencia o de archivarla fuera del
workspace.

## Propuesta de limpieza

1. Aplicar el plan del reconciliador: recuperación segura de `1,73 GiB`.
2. Retirar el temporal abandonado del precálculo: unos `256 MiB`.
3. Decidir si las auditorías históricas deben conservarse, archivarse fuera del
   workspace o eliminarse: hasta `6,52 GiB` adicionales.
4. Revisar separadamente `tmp` (`0,28 GiB`) y los backups JSON repetidos
   (`31 MiB`).
5. No tocar en esta limpieza `mushroom-GIS`, el lote operativo protegido, el
   precálculo activo, meteorología, observaciones ni medios de usuario.

Sin sacrificar evidencia histórica se pueden recuperar aproximadamente
`1,98 GiB`. Si se retiran también las auditorías, la recuperación asciende a
unos `8,50 GiB`; la revisión posterior de `tmp` podría elevarla a unos
`8,78 GiB`.
