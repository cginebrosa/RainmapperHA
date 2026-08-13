# Active Context

Ventana operativa de RainmapperHA. Contiene solo lo necesario para continuar.
El histórico está en `docs/decisions.md`, `docs/project-archive.md` y los
documentos temáticos enlazados.

## Estado operativo actual — 2026-08-13

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- HA `0.2.254` está instalada, arrancada y validada en la RPi4. `0.2.254` y
  `latest` comparten digest multiarch verificado. El worker M1 desplegado es
  `1.0.8`, healthy/idle y conserva identidad y caché GIS.
- La imagen HA `0.2.255` está publicada y verificada, pero **no está instalada**:
  el usuario ha decidido no actualizar HA hasta cerrar Biology V3. No confundir
  una imagen preparada con el estado de la instancia.
- El worker `1.0.9` está construido y validado solo como imagen local. El worker
  activo continúa siendo `1.0.8`; no reiniciarlo ni sustituirlo antes del cierre
  y la actualización coordinada posterior.
- Con `0.2.254` se ejecutó `Reconstruir y reentrenar todo` en M1:
  reconstrucción completa (~1 min 29 s), entrenamiento completo (~31 s) y
  promoción conjunta correctas. La generación viva contiene los dos contratos
  altitude V2 y el runtime sincronizó 20.758.092 bytes sin discrepancias.
- Predictor M1 y fallback HA producen resultados equivalentes y no vacíos. HA
  tarda ~98 s y alcanzó ~577 MiB sin OOM; M1 sigue siendo el ejecutor normal.
- Altitude V2 está cerrado. La causa, corrección y validaciones de las versiones
  anteriores quedan archivadas en `docs/decisions.md` y en la genealogía ML;
  no reabrirlas durante Biology V3.

## Próximos pasos, en orden

1. Considerar cerrado el bloque de implementación y evaluación de benchmark
   Biology V3. No instalar todavía HA `0.2.255` ni el worker `1.0.9`.
2. Acumular observaciones y repetir la comparación V3/V2 sobre las mismas filas
   elegibles antes de plantear un candidato operativo. No entrenar ni promover
   V3 con la evidencia actual.

## Biology V3 — benchmark implementado; promoción operativa bloqueada

- Altitude V2 queda congelado y operativo; V3 se implementa en módulos nuevos.
- `rainmapper_core/mushroom_weather_idw.py` define
  `daily_rain_idw_radius15km_power2_v1`: IDW diario en la microárea, radio 15
  km, potencia 2 y piso 0,1 km. El cero observado cuenta; ausencia, anomalía,
  repetición positiva suprimida y estación retirada no participan.
- `rainmapper_core/mushroom_ml_biology_v3.py` implementa el resolver
  `outing_value_area_v1`, canonicalización especie/microárea/fecha, evidencia
  de episodio de área, materialización IDW por microárea y el contrato cerrado
  `area_daily_mean_microarea_idw_v1`: media diaria de los IDW disponibles de
  todas las microáreas configuradas; sin contribuyentes queda ausente.
- El benchmark ya separa estrictamente `predictive_features`, `quality` y
  `metadata`; `build_biology_v3_X` solo acepta variables predictivas registradas
  y las pruebas impiden que calidad o área entren en `X`.
- `fixed_gap_7d_biology_v3` y `lag_event_biology_v3` están implementados con
  gates y motivos legibles. Conservan cada observación como muestra y añaden
  grupos diagnósticos por especie+área con máximos de 7 y 14 días.
- Smoke real sobre copias locales de los Parquet de HA:
  IDW diario acumulado `46,003 mm` frente a `46,059 mm` calculado sobre Tomap
  redondeado para `42.01333, 1.97155`, `2026-08-06…12`.
- Reproducción preliminar sobre los 399 registros locales: 348 unidades
  microárea/fecha y 278 episodios de área, con 2 conflictos de microárea y 9
  episodios mixtos. La discrepancia antigua queda reconciliada: 278 menos 3
  desconocidos son los 275 entrenables; los 11 mixtos pre-canónicos eran 9
  conflictos entre microáreas más los 2 conflictos internos.
- Auditoría del agregador: 7.262 días-área, diferencia mediana contra el IDW del
  centroide 0,001 mm, p95 0,62 mm, p99 1,89 mm y máximo 7,89 mm. La dispersión
  máxima entre microáreas fue 43,94 mm: se descarta el centroide calculado. El
  Predictor aceptará la media IDW como lluvia canónica sin reservas por fuente,
  interpolación o dispersión. La procedencia queda solo para reproducción.
- Elevación transfronteriza cerrada: el DEM Catalunya sigue siendo principal y
  el MDE oficial de Andorra 5 m es fallback. El derivado operativo tiene CRS
  EPSG:27563 embebido, metros, `NoData=-9999`, 30 MB y se transporta/cachea como
  parte del dataset GIS del worker. Ordino queda en 2063,2 m; la observación GPS
  de 2080 m contrasta con 2073,5 m del DEM.
- `mushroom-GIS-HA` era una copia local histórica de preparación de 5,9 GB. No
  aparecía en ninguna ruta de ejecución, estaba ignorada y sus diez ficheros de
  datos eran idénticos byte a byte a `mushroom-GIS`; se eliminó de forma
  autorizada. También se retiró su regla de `.gitignore`. No recrearla ni usarla
  como staging; local usa `mushroom-GIS/` y HA `/media/rainmapper/mushroom-GIS/`.
- Benchmark local reproducible sobre 399 observaciones: `fixed_gap` conserva
  399 muestras y deja 204 elegibles; `lag_event` conserva 1.596 muestras para
  horizontes 1/2/3/7 y deja 816 elegibles, 204 por horizonte. Se materializan
  264 grupos de 7 días y 244 de 14 días sin agregar sus filas. No se entrenó
  ningún modelo.
- `rainmapper_core/mushroom_ml_biology_v3_evaluation.py` ejecuta una comparación
  no operativa con corte cronológico 70/30 por especie y grupos completos de
  florada. Catorce días es la referencia principal por cubrir floradas largas;
  siete días es la comprobación de sensibilidad. Ningún grupo cruza train/test
  y ninguna observación se elimina.
- La comparación mantiene `active_full`, `without_rain`,
  `without_temperature_humidity` y `weather_only`. En `fixed_gap`/14 días,
  quitar lluvia empeoró Brier de 0,1923 a 0,2643 y quitar temperatura/humedad a
  0,2560: con estos datos la lluvia no añade ruido y las tres familias ayudan.
  `weather_only` obtuvo 0,1713, señal de que mes/altitud requieren seguimiento,
  no autorización para borrarlos ni para escoger retrospectivamente variables.
- Frente a altitude V2, V3 mejora Brier y balanced accuracy en tres de cuatro
  vistas y queda prácticamente igual en Brier para `lag_event`/7 días. La
  comparación aún usa conjuntos elegibles distintos y V3 empeora log loss por
  probabilidades extremas. Por ello no supera un gate honesto de promoción.
  No se escribió un artefacto reutilizable (`model_artifact_written=false`).
- La altitud de microárea queda cacheada al crear o cambiar su geometría en las
  dos rutas locales de mantenimiento; un guardado sin cambio geométrico la
  reutiliza. La cadena Catalunya→Andorra→IGN MTN50 hoja 592 resolvió las 58/58
  microáreas en una copia temporal: 396 muestras del DEM Catalunya, 9 de
  Andorra y 15 del IGN. Puertomingalvo queda cubierto por el IGN, con medias de
  1.329,6 m (`pm_arriba`) y 1.279,9 m (`mas_del_sapo`). El fichero autoritativo
  microáreas en una copia temporal y después se materializó el mismo resultado
  en el `known_sites` vivo de HA, con backup previo y validación 58/58. Los tres
  DEM están bajo `/media/rainmapper/mushroom-GIS/`; no se empaquetan en Git ni
  en la imagen.

## Riesgos y restricciones activas

- No promover candidatos antiguos ni mezclar artefactos y modelos de
  generaciones distintas; la generación activa actual sí es coherente.
- Biology V3 parte de una muestra pequeña y sesgada por visitas; los scores
  brutos no son probabilidades calibradas.
- Mantener la RPi4 para coordinación y trabajo incremental acotado. Rebuild y
  entrenamiento permanecen en M1. El Predictor HA está validado solo como
  fallback administrativo lento (~98 s y ~577 MiB en la prueba semanal).
- El histórico meteorológico fuente/año, CSV vivos acotados, colas intradía,
  Tomap/MapLibre y Predictor histórico ya están migrados en HA; no rehacer el
  cutover durante esta corrección.
- Preservar el worktree. No limpiar, resetear ni sobrescribir cambios locales.
- El MDE de Andorra y demás binarios GIS siguen fuera de Git. Las copias de HA
  se verificaron por hash; preservarlas en `/media` y no incluirlas en releases.

## Archivos relevantes

- `rainmapper-app/app/web_server.py`: chaining, preparación de identidad viva y
  estilo del modal.
- `rainmapper_core/mushroom_worker_results.py`: rebase canónico y promoción
  conjunta con rollback.
- `rainmapper-app/app/mushroom_workers_ui.py`: acción completa y estado de jobs.
- `rainmapper_core/mushroom_predictor_runtime.py`: validación estricta de la
  identidad de features/modelos.
- `rainmapper_core/mushroom_ml_experiments.py` y
  `rainmapper_core/mushroom_ml_experiment_trainer.py`: contratos altitude V2.
- `scripts/run-mushroom-ml-train-job.py` y
  `rainmapper_core/mushroom_worker_results.py`: manifiesto y barrera de
  compatibilidad V2.
- `rainmapper_core/mushroom_weather_idw.py`: contrato espacial de lluvia V3.
- `rainmapper_core/mushroom_ml_biology_v3.py`: target, canonicalización y
  contratos completos de benchmark V3.
- `scripts/build-biology-v3-benchmark.py`: benchmark local sin entrenamiento.
- `rainmapper_core/mushroom_ml_biology_v3_evaluation.py` y
  `scripts/evaluate-biology-v3-benchmark.py`: comparación temporal local sin
  persistir modelos.
- `scripts/materialize-micro-area-dem-altitudes.py`: relleno DEM seguro que
  exige una salida distinta del fichero fuente.
- `mushroom-GIS/dem-andorra/README.md`: formato, procedencia, hashes y control
  GPS del fallback DEM transfronterizo.
- `scripts/audit-biology-v3-idw.py`: smoke IDW acotado y de solo lectura.
- `scripts/audit-biology-v3-area-idw.py`: comparación reproducible de media de
  microáreas frente al centroide del área.
- `docs/mushrooms/mushroom-ml-contract-versions-es.md`: genealogía canónica de
  V0, V1, altitude V2 y Biology V3.
- `tests/test_mushroom_worker_results.py` y `tests/test_web_server_auth.py`:
  regresiones de identidad y wrapping.
- `docs/mushrooms/mushroom-ml-v3-data-audit-es.md` y
  `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`: siguiente bloque.
- `docker-data/audits/mushroom-weather-backfill-20260811/PROGRESS.md`: evidencia
  del backfill/migración, no contexto de arranque.

## Reglas operativas

- Una tarea explícita autoriza ediciones, consultas, pruebas, empaquetado y
  demás acciones no destructivas de su alcance. No pedir confirmaciones
  redundantes. El MCP Codebase es consulta de solo lectura y no requiere pedir
  permiso. Preguntar ante destrucción, escritura en HA no autorizada o una
  ampliación material del alcance.
- No promover artefactos/modelos, escribir datos en HA, cambiar red/Tailscale ni
  ejecutar trabajos pesados sin petición explícita.
- Antes de publicar HA, seguir `docs/release-flow.md`; durante el build informar
  al menos una vez por minuto y verificar tags, digest y plataformas.

## Validación habitual

```bash
PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
.venv/bin/python -m unittest discover -s tests
git diff --check
```
