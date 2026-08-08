# Active Context

Ventana operativa para continuar RainmapperHA sin depender de conversaciones
anteriores. Este documento describe el estado actual, no el historial completo.

## TL;DR — Estado del proyecto (leer esto primero)

**Release HA:**
- Publicada, instalada y validada en HA real: `0.2.232`. Conserva los cambios
  de `0.2.230`/`0.2.231` y refuerza la caja negra del runner con heartbeat
  persistente cada 10 s, fases AEMET, timeout total de 90 s, boot ID/uptime y
  archivado del log de una ejecución interrumpida. Digest multiarquitectura:
  `sha256:bb819e5407f1c685eb75b05955841b3e35554d3467140a3ff56a2708eec721da`.
- Runner manual real de `0.2.232` completado en 6:15, código 0, pico cgroup
  1.445,4 MiB, mínimo `MemAvailable` 822,6 MiB, máximo 54,5 °C y cero OOM.
  Heartbeats, fases AEMET y recuperación 60/600 s validados; detalle y hash del
  ZIP en `docs/runtime-diagnostics.md`.
- Cambio local no publicado: los timestamps UTC de la caja negra se convierten
  al ISO local con offset usado por Summary. Por decisión del usuario no se
  sube versión HA solo por este ajuste; se incluirá en una futura release.
- La imagen anterior `0.2.226` conservaba el Parquet monolítico; queda sustituida
  operativamente por `0.2.227`.
- No hay versión de desarrollo/sideload.
- `0.2.227` genera row groups filtrables, hace
  bootstrap seguro del catálogo, impide la lectura interactiva del Parquet
  monolítico, acota la caché por filtro e incluye diagnóstico automático.
  El runner ya regeneró 625.529 filas en 1.222 row groups y creó el catálogo.
- `0.2.228` añade el transporte, verificación y promoción atómica de
  `ml_train_report.json`, coherencia de especies e invalidación de caché.
- Ensayo B del Predictor completado sin OOM: la subfase meteorológica tardó
  8,667 s y retuvo 337,8 MiB RSS a los 600 s de forma estable. El usuario observó
  al menos unos 30 s desde el clic hasta la pantalla; falta instrumentar esa
  latencia extremo a extremo.
- Ensayo C completado: aviso correcto durante el runner, 4 instancias liberadas
  antes del hijo, pico cgroup 1.477,2 MiB, mínimo `MemAvailable` 780,2 MiB,
  recuperación a 600 s y cero OOM. P0 de memoria cerrado para el escenario
  monousuario probado.
- Rebuild de features, entrenamiento con el worker `0.2.228` y promoción de los
  modelos y `ml_train_report.json` completados y confirmados por el usuario el
  2026-08-08.
- `0.2.229` publicó la caja negra v2 y la optimización temporal del Predictor:
  las vistas actuales comparten una única ventana sustituible de 96 días;
  fechas históricas se cargan bajo demanda e Historial carga una sola vez el
  rango de sus episodios. Prueba real completada en RPi4: petición fría servidor
  36,622 s, 7.728 registros meteorológicos, pico de proceso 420,1 MiB RSS, pico
  de cgroup 576,3 MiB y cero OOM. El detalle está en
  `docs/runtime-diagnostics.md`.
- Mantenimiento real de fotos completado el 2026-08-08 sobre el share de HA:
  210 JPEG normalizados a lado máximo 1600/calidad 86 con EXIF, 786.726.936
  bytes liberados; 422/422 ficheros referenciados, cero faltantes o huérfanos.
  Originales e informes conservados en `~/Desktop/Fotos Bolets/`. Procedimiento
  en `docs/mushrooms/observation-photo-maintenance-es.md`.

**Worker M1 / M5 ↔ HA real — qué está hecho y qué queda:**
- Hecho: emparejamiento LAN, reconstrucción completa candidata, promoción manual al modelo vivo, avisos transitorios, descarte con modal, M1 y M5 probados y funcionales. M5 ~1.5x más rápido que M1 en red local.
- Pendiente en HA real: prueba de descarte con candidato terminal no promocionado, corte/reconexión sin revocar credencial, freshness/cache.
- Decisión pendiente: incluir Tailscale dentro de la imagen del worker (M5 no tiene Tailscale por ser el del trabajo).
- Portabilidad en daemon limpio: pendiente, no bloquea work actual.

**Observaciones / ML (estado 2026-08-06):**
- La revisión se realiza en **HA real**. Docker local es una copia fresca del estado de
  revisión de HA y se usa para pruebas y comprobaciones, no como entorno autoritativo
  independiente.
- Estado comprobado en la copia local fresca: **530 observaciones** = 276
  `calibration_use=include` + **254 `review` pendientes**.
- De las 254 pendientes: 120 `draft`, 131 `valid` y 3 `doubtful`; 233 conservan
  `flush_abundance=pending` y 40 de las válidas no tienen `micro_area_id`.
- `mushroom_reference_catalogs.json` subido a HA (`/share/rainmapper/mushroom-data/`) — necesario para que el valor `pending` de flush_abundance se muestre correctamente.
- Fases 1–4 del predictor ML completadas (features, trainer, predictor engine, UI Predictor con estadísticas de fiabilidad).
- Modelos entrenados a nivel **área** (no micro_area): B. aereus (37 ep, 42% holdout), A. caesarea (35 ep, 27% holdout), B. pinophilus (22 ep, 71% holdout). L. deliciosus no llega al mínimo de 20 episodios.
- Worker job `ml_train_v0` implementado (ver sección "Worker ml_train_v0" más abajo).
- Bloqueos actuales de revisión: 120 obs en draft, 233 con florada pendiente y
  40 válidas sin `micro_area_id`.

**Prioridad inmediata:**
1. **P0 Predictor / memoria RPi4 cerrado en el alcance probado:** A–C completos
   sin OOM. Runner aislado: 7:02 y pico cgroup 1.347,8 MiB. Predictor: subfase
   meteorológica 8,667 s y retención estable. Runner posterior: 6:43, pico cgroup
   1.477,2 MiB, 780,2 MiB disponibles y recuperación correcta. Apertura manual
   ≥30 s pendiente como rendimiento. Detalle en `docs/runtime-diagnostics.md`.
2. **Revisar observaciones `review` en HA real** — 254 pendientes. Es el paso más
   impactante para mejorar los modelos ML. La evidencia observada NO se revisará manualmente:
   se implementará herencia desde micro_area (ver sección "atributos ecológicos" al final).
3. **Rebuild/training completado:** features reconstruidas, modelos reentrenados
   con el worker actualizado y modelos/informe promovidos en HA real; confirmado
   por el usuario el 2026-08-08.
4. **Planificación pendiente:** verificación/comparación de modelos candidatos antes de promoción (ver sección al final).
5. **Caja negra 2.1 validada en HA real:** runner manual 0.2.232, heartbeats,
   fases AEMET, cierre y recuperación 60/600 s correctos. Queda pendiente solo
   afinar la latencia total de apertura del Predictor y enriquecer, si se desea,
   la visualización en vivo del último heartbeat.
6. Worker: probar descarte con candidato terminal en HA real.
7. Decidir si meter Tailscale dentro de la imagen del worker.

El contrato de instrumentación automática, descarga y ensayo controlado en
RPi4 está en `docs/runtime-diagnostics.md`. La implementación local ya registra
JSONL acotado, picos del proceso y del cgroup, recuperación a 60/600 s, carga fría
del Predictor, libera sus cachés antes del runner, impide solapamientos y añade
un ZIP descargable desde el panel. Los ensayos A–C reales pasaron y cierran el
P0 de memoria; queda pendiente instrumentar la latencia total del Predictor.
Validación local de la release `0.2.232`: `smoke-test.sh`, 490 tests, PASS el
2026-08-08. La release ya está instalada y el runner manual quedó validado en
HA real; el ajuste visual posterior deliberadamente sin publicar pasa el smoke
completo con 495 tests.

**Flujo de datos actual:** las observaciones se revisan y guardan en HA real. La copia de
`docker-data/mushroom-data/` se refresca desde HA para pruebas y comprobaciones; no planificar
una subida de `mushroom_observations.json` local sobre HA como paso de cierre. Los `.joblib`
se generan desde el worker después del release.

## ML Predictor — estado (2026-08-06, fases 1-4 completadas)

### Incidente P0 de memoria en RPi4 — diseño de arreglo acordado (2026-08-06)

**Síntoma:** al abrir el Predictor en HA, se materializan 622k objetos
`DailyWeatherRecord` Python (~358 MiB estimado), colapsando la RPi4.

**Diagnóstico:** `_get_shared_weather_stations()` carga el parquet completo
(1.948 estaciones × todos los días históricos) y lo convierte entero en objetos
Python. Solo se necesitan las estaciones cercanas a las micro-áreas del modelo.

**Mediciones reales (docker-data, 2026-08-06):**
- Parquet completo: 625.434 filas, 1.932 estaciones, ~358 MiB estimado
- Con filtro top-5 estaciones a ≤15 km por micro-área: 100 estaciones únicas,
  70.490 filas (11% del total), ~40 MiB estimado — reducción del 89%
- 46 micro-áreas: todas tienen entre 4 y 5 estaciones dentro del radio de 15 km
- Radio máximo al fallback más lejano: 15 km

**Plan de implementación acordado — 4 cambios:**

**1. `rainmapper_core/rainmapper.py`** — al final del runner, después de generar
`weather_daily.parquet`, generar también `weather_stations_catalog.parquet`:
solo columnas `(station_code, lat, lon, altitud, source)`, una fila por estación
(sin duplicados). ~100 KB, generado en el mismo paso.

**2. `rainmapper_core/mushroom_observation_context.py`** — nueva función
`load_stations_catalog(data_dir)` que lee `weather_stations_catalog.parquet`.
Nueva función `nearest_station_codes(catalog, lat, lon, max_km=15, top_n=5)`
que devuelve los códigos de las N estaciones más cercanas dentro del radio.
La función existente `load_daily_weather_parquet()` acepta un parámetro
opcional `station_filter: set[tuple[str, str]] | None` — si se pasa, usa filtros
DNF por `(source, station_code)` antes de materializar el DataFrame. Un filtro
vacío o la ausencia del Parquet fallan de forma acotada, sin cargar todos los CSV.

**3. `rainmapper_core/mushroom_ml_predictor.py`** — dos cachés módulo-nivel
con invalidación por mtime (igual que ya funciona para el parquet completo):
- `_shared_stations_catalog` — catálogo ligero de coordenadas, siempre en memoria
- `_shared_weather_stations` — ya existe, ahora carga solo las estaciones
  relevantes calculadas desde el catálogo y las coordenadas del modelo activo

Al inicializar `MushroomMLPredictor`, calcular las estaciones necesarias
(top-5 a ≤15 km de cada micro-área del modelo) y pasarlas como filtro a
`load_daily_weather_parquet()`.

**4. `mushroom_observation_context.py` — fallback en `select_station()`**
Entre las cinco estaciones más cercanas, seleccionar la que tenga mejor cobertura
en la ventana de features ya existente de 30 días; la distancia desempata. Así se
evita inventar un umbral nuevo y no se conserva una estación casi vacía solo por
ser unos metros más próxima.

**Lo que NO cambia:**
- La caché `_shared_weather_stations` con invalidación por mtime sigue existiendo
  (ya implementada hoy) — ahora simplemente guarda 100 estaciones en lugar de 1.932
- El contrato del worker de entrenamiento no cambia. El próximo rebuild de
  features y retrain debe usar la selección compartida por mejor cobertura para
  consolidar la misma política en entrenamiento y serving.
- `weather_daily.parquet` sigue siendo la fuente canónica

**Corrección incluida en 0.2.227 (publicada el 2026-08-07):** se confirmó
que `pd.read_parquet(..., filters=...)` no basta con el artefacto actual porque
sus 625.434 filas están en un único row group. El generador ahora ordena por
fuente/estación/fecha y escribe row groups de 512 filas de forma atómica. La ruta
interactiva rechaza un Parquet monolítico antes de leerlo y la UI solicita ejecutar
una actualización meteorológica. El catálogo se genera en streaming si falta o
está obsoleto. La caché incluye el filtro de estaciones y las cargas frías están
serializadas con lock single-flight.
Suite integral local de la release: **462 tests OK**.

### Fases completadas

**Fase 1 (pipeline features) — DONE:**
- `mushroom_observation_context.py`: ventana 30d, 8 features derivadas, series diarias en JSON.
- `mushroom_observation_features.py`: eliminados rain_60d/rain_90d, añadidas 8 derivadas.
- Rebuild completo: 587 rows, 554 con estación, 8 features derivadas correctamente calculadas.

**Control de calidad de lluvia — DONE (2026-08-03):**
- `mushroom_observation_context.py`: nueva función `_consecutive_duplicate_rain_dates()`.
- Detecta días con exactamente el mismo valor de lluvia > 0 en días calendario consecutivos.
  Patrón conocido de estaciones Wunderground cuando el sensor deja de reportar y el sistema
  copia el último valor conocido. Puede afectar cadenas de cualquier longitud (2, 3, N días).
- Comportamiento: mantiene el primer día de la cadena, nullifica los siguientes.
  Se reportan como gap `rain_suspect_consecutive_YYYYMMDD` en `data_gaps`.
- Aplicado en los tres sitios de uso de lluvia: acumulados de ventana (`build_weather_values`),
  features derivadas (`build_derived_features`: dry_spell, days_since_significant_rain,
  rainy_days_14d) y serie diaria raw (`build_daily_series`).
- Un único punto de cálculo: `dup_dates` se computa una vez antes de llamar a las tres funciones.
  Al estar en `mushroom_observation_context.py`, aplica automáticamente tanto al rebuild de
  features de entrenamiento como al predictor en tiempo real — sin inconsistencia modelo/predicción.
- Solo lluvia (> 0). Temperatura y humedad no se filtran — pueden repetir legítimamente.
- Tests: `test_build_weather_features_nullifies_consecutive_duplicate_rain` añadido. Suite: **392 tests OK**.

**Control de calidad de lluvia en MapLibre / Tomap — DONE (2026-08-03):**
- Los mismos dos filtros aplicados también en `rainmapper_core/tomap.py` — el pipeline que
  genera los CSV Tomap que consume el visor MapLibre.
- Nueva función `_apply_rain_quality_filters(df)` en `tomap.py`: mismo comportamiento que
  en el pipeline ML (outlier > 300mm + duplicados consecutivos), aplicado sobre DataFrame pandas.
- Llamada en dos puntos: `create_grouped()` (totales de período 1d/7d/30d/90d) y
  `create_last_rains()` (historial diario en popups de estación), ambos antes de agregar.
- Constante `DAILY_RAIN_SANITY_LIMIT_MM = 300.0` definida en `tomap.py` (igual que en
  `mushroom_observation_context.py` — si se cambia, actualizar los dos sitios).
- Los datos brutos de los CSV incrementales no se modifican — el filtro se aplica solo en memoria.

**Fase 2 (trainer) — DONE:**
- `rainmapper_core/mushroom_ml_trainer.py` — entrena LR + RF por especie, guarda joblib + JSON report.
- scikit-learn 1.9.0 instalado en `.venv` (via `.venv/bin/python3.11 -m pip install scikit-learn`).
- Modelos entrenados y guardados en `docker-data/mushroom-data/ml_models/` (gitignored).
- Reporte en `docker-data/mushroom-data/mushroom_ml_v0_report.json`.
- **Unidad de episodio: `(species, area, date)`** — no micro_area. Las estaciones meteorológicas
  sirven áreas enteras; entrenar a nivel micro_area con features compartidas generaba ruido puro
  (mismas X, etiquetas contradictorias el mismo día dentro de la misma área).
- 3 especies entrenadas: B. aereus (37 ep), A. caesarea (35 ep), B. pinophilus (22 ep).
  L. deliciosus skipped: solo 16 episodios (mínimo=20).
- Agregación: episodio favorable si ALGUNA micro_area del área tuvo obs favorable ese día.
  altitude del episodio = media de altitudes de las micro_areas observadas.

Resultados trainer B. aereus (37 area episodes: 24+/13-, split 25 train / 12 test):
- LR CV-AUC: 0.367, holdout: 0.778
- RF CV-AUC: 0.500, holdout: 0.815
- RF top features: humidity_min_7d_pct (6.5%), thermal_amplitude_mean_7d (5.2%), temp_mean_14d (4.9%)

Resultados trainer B. pinophilus (22 area episodes: 11+/11-, split 15 train / 7 test):
- LR CV-AUC: 1.0, holdout: 0.4  ← señal de overfitting por dataset pequeño
- RF CV-AUC: 1.0, holdout: 0.5
- Diagnóstico: insuficientes datos para generalizar. Necesita más observaciones revisadas.

**Fase 3 (predictor engine) — DONE:**
- `rainmapper_core/mushroom_ml_predictor.py` — predictor completo con 4 modos de consulta.
- Usa mismas funciones de features que el training (`mushroom_observation_context`).
- Restricción ecológica: `rank_areas(only_observed=True)` por defecto — solo áreas donde
  la especie tiene observaciones válidas+include, evitando predicciones ecológicamente
  imposibles (ej: B. aereus a 2200m en Salteguet/La Feixa).
- Modos CLI: `predict(area, date)`, `rank_areas(date)`, `week_window(area, start)`, `backtest()`.

Backtest B. aereus (37 episodios a nivel área):
- **59% accuracy (22/37)**. Distribución: 14 falsos negativos, 1 falso positivo.
  El modelo es conservador — cuando duda, dice "desfavorable".
- Mejor área: **Olvan 68% (13/19 episodios)**. Tiene más observaciones de entrenamiento.
- Áreas con mal rendimiento: selva_del_camp, coll_de_la_batalla, espunyola — todas con 1-2
  episodios de entrenamiento; el modelo no aprendió su patrón específico.

Backtest B. pinophilus (22 episodios a nivel área):
- **36% accuracy (8/22)**. Overfitting claro: CV-AUC 1.0 vs holdout 0.4-0.5.
- Mejora vs. versión anterior a micro_area (24% → 36%): scarce=0 eliminó falsos positivos
  de Guils (micro_areas con florada mínima que contaminaban el entrenamiento).
- No fiable todavía — necesita más observaciones revisadas.

**Decisiones de diseño consolidadas:**
- `scarce.prediction_favorable = 0` — solo floradas de consistencia real predicen favorable
  (normal/abundant/very_abundant/exceptional). 4-5 setas no justifican salida al monte.
- Nivel de agregación: **área** (no micro_area). Razón: las estaciones meteorológicas sirven
  áreas enteras; micro_area generaba ruido por construcción.
- No forecast necesario: el modelo aprende el lag entre condiciones y florada; los 30 días
  anteriores a cualquier fecha futura próxima ya están en los históricos.
- 39 features numéricas: rain 5 ventanas + temp 12 + humidity 12 + 8 derivadas + altitude + month.
- LR + RF ensemble (media de probabilidades). RF generaliza mejor en todos los casos.
- Thresholds de label (no producción): ≥0.60 favorable, ≤0.40 unfavorable, resto uncertain.

**Rutas en mushroom_paths.py:**
- `mushroom_known_sites_path()` — `mushroom_known_sites.json`
- `mushroom_ml_models_dir()` — `mushroom-data/ml_models/` (gitignored, binarios joblib)
- `mushroom_ml_report_json_path()` — `mushroom-data/mushroom_ml_v0_report.json`

**Fase 4 (UI Predictor) — DONE:**
- `mushroom_predictor_ui.py` nuevo: pantalla "Predictor" con 4 vistas.
- "Esta semana": ranking semanal de condiciones por área (tabla con badge favorable/unfavorable/uncertain).
- "Por especie": semana de detalle para especie+área seleccionadas.
- "Consultar fecha": predicción puntual fecha+área.
- "Historial": backtesting visual con tarjetas de estadísticas clicables (filtran por correct/FN/FP).
- Caché lazy por especie en `web_server.py`. Modelos joblib cargados bajo demanda.
- **Estadísticas de fiabilidad (0.2.225):** strip con holdout accuracy por especie, badges de
  episodios por área (🟩 ≥10 / 🟨 4–9 / 🟥 1–3) en "Por especie" y "Consultar fecha".
  Dos leyendas: predicción (círculos 🟢🟡🔴) y fiabilidad (cuadrados 🟩🟨🟥).
- **Backtest durante entrenamiento (0.2.225):** `mushroom_ml_trainer.py` calcula holdout
  accuracy (split temporal 70/30) y stats por área al entrenar, guardadas en
  `mushroom_ml_v0_report.json`. La UI lee el reporte; no hay cómputo live en cada petición.
- **Fix caché parquet (0.2.225):** `_get_shared_weather_stations()` invalida la caché
  automáticamente si el mtime del parquet ha cambiado — evita datos obsoletos si el runner
  regenera el fichero sin reiniciar el add-on.

## Importación masiva de observaciones + fixes de datos (2026-08-01/02, cerrada)

### Estado histórico de la importación (2026-08-02)

Importación completada y saneada originalmente en Docker local. Las cifras de esta
sección describen el lote importado y se conservan como trazabilidad; no son el recuento
operativo actual. La revisión posterior pasó a realizarse en HA real.

- `review_table.json` en `/Users/carlosginebrosa/Desktop/Fotos Bolets/candidates/`
- 818 archivos de entrada → **772 observaciones totales** en `docker-data/mushroom-data/mushroom_observations.json`
  (126 existentes `include` + 646 nuevas `review`)
  Nota: se eliminaron 33 duplicados y 167 MOV observations respecto al merged inicial.
- Media procesada: 757 ficheros referenciados (fotos + vídeos) en `docker-data/mushroom-data/media/`
- Docker local queda como copia de HA para pruebas y comprobaciones
  (`http://127.0.0.1:8101` cuando está arrancado).

### Desglose de las 818 entradas originales
- 646 observaciones importadas con `calibration_use: "review"`
- 154 MOVs Live Photo companion detectados y omitidos automáticamente (mismo stem que un HEIC)
- 44 omitidas sin perfil en Rainmapper (18 especies sin definir)
- 3 omitidas no identificadas
- 33 eliminadas por ser duplicados de observaciones `include` existentes

### Fixes aplicados en esta sesión (2026-08-01/02)

**flush_abundance "pending" (nuevo valor de catálogo)**
- Las 646 obs importadas tenían `flush_abundance: null`, bloqueando TODOS los saves con 646 errores de validación.
- Solución: añadido `"pending"` al catálogo `observation_flush_abundance` (`calibration_score: 0.0`, `prediction_favorable: 0`, `sort_order: 0`).
- Las 646 obs parcheadas con `flush_abundance: "pending"`.
- Añadido campo `calibration_score` al formulario de edición del catálogo (era editable solo via JSON raw).
- Validación cruzada nueva: `flush_abundance: "pending"` + `calibration_use: "include"` → ERROR bloqueante.
- Ficheros modificados: `mushroom_reference_catalogs.json`, `mushroom_catalogs_ui.py`, `web_server.py` (handler + template), `validate-mushroom-data.py`.

**Conversión de JPEGs falsos**
- 421 de 645 ficheros `.jpg` contenían bytes HEIC raw (PIL falló durante el import, se guardó raw y se renombró).
- Convertidos a JPEG real con `sips` (macOS nativo). 0 fallos.
- Ningún fichero HEIC queda ni por extensión ni por contenido.

**Borrado de media al eliminar observación**
- `delete_archived_observation` no eliminaba los ficheros de media huérfanos.
- La primera corrección hacía reference counting entre activas + resto de
  archivadas y borraba los ficheros con `reference_count == 0`, pero el borrado
  físico seguía ocurriendo después del JSON sin reintento persistente.
- Reforzado el 2026-08-08: `delete_archived_observation` y
  `delete_observation_media` registran primero una intención en
  `maintenance/observation_media_cleanup_queue.json`. Tras guardar el JSON se
  vuelve a contar referencias y solo entonces se borra. Los fallos quedan en la
  cola y se reintentan al arrancar o al entrar en mantenimiento de perfiles.
- Todas las mutaciones de perfiles/observaciones están serializadas dentro del
  proceso web para impedir carreras entre la cola y los JSON.
- Archivar conserva siempre la media. Archivar escribe primero la copia
  archivada y después retira la activa; restaurar hace la operación inversa. En
  errores controlados se aplica rollback, priorizando siempre duplicación
  recuperable frente a pérdida del registro.
- Tests físicos: conservar al archivar/restaurar, no borrar si otra observación
  referencia el fichero, borrar al retirar la última referencia, persistir y
  reintentar fallos de `unlink`, y rollback si falla cualquiera de los stores.

**Bug de cambio de especie (causa raíz identificada)**
- El usuario no podía cambiar la especie de una observación importada: el `store.replace` fallaba por los 646 errores de `flush_abundance`. Resuelto al parchear el catálogo.
- UX pendiente de verificar: `observations_return_url` usa `return_selected_species_id` (especie antigua) con prioridad sobre la nueva, lo que puede hacer parecer que el cambio no se guardó aunque sí lo hiciera.

### Scripts en `scripts/observations-mass-import/`
- `README.md` — proceso completo documentado (pasos 1-11)
- `01_assign_areas.py` — point-in-polygon área/micro-área ✓
- `02_assign_evidence.py` — evidencia desde obs más cercana ✓
- `03_map_species.py` — mapeo species→species_id con aliases y reglas contextuales ✓
- `04_generate_observations.py` — genera + media + fusiona con obs existentes ✓
  (detecta y omite MOVs Live Photo companion automáticamente)
- `media_utils.py` — procesado PIL/ffmpeg de imágenes y vídeos, extraído de web_server.py ✓

### Reglas de mapeo de especies (en 03_map_species.py)
- USER_NAME_ALIASES: Tricholoma sp.→terreum, Morchella sp.→elata_complex, Russula sp.→virescens
- CONTEXT_RULES: Boletus sp. + Amanita caesarea→aereus, + Lactarius→edulis, + Tricholoma terreum→edulis
- Boletus sp. standalone: <1000m→aereus, ≥1000m otoño→edulis, ≥1000m otra época→pinophilus

### Decisiones tomadas
- calibration_use: "review" para todas las importadas
- validation_status: del campo confidence (valid/draft/doubtful)
- Especies sin perfil (18 especies): ignorar, no importar
- Fotos con micro_area_id "pending" (5): importar con micro_area_id null
- Fotos sin área conocida (188): importar con micro_area_id null y site_context vacío
- MOVs Live Photo companion: omitir siempre, conservar solo el HEIC
- source.label conserva el nombre original (.HEIC) como dato de trazabilidad, no es una ruta

### Estado operativo posterior (2026-08-06)

- Revisión en curso en HA real: **254 observaciones `review` pendientes**.
- Confirmar especie y pasar a `calibration_use: "include"` las válidas desde la UI de HA.
- Completar las evidencias de campo necesarias en HA.
- Refrescar Docker local desde HA cuando se necesite una copia para pruebas o
  comprobaciones; no usar el espejo local como origen de una sobrescritura de HA.

## Dataset ML — último snapshot entrenado (2026-08-03)

Episodios a nivel **área** (valid + include + micro_area_id asignada, agregados por `(species, area, date)`).
Tabla completa con criterios y política en `docs/mushrooms/mushroom-ml-training-plan-es.md`.

| Especie                    | Ep. fav | Ep. desf | Total (área) | Entrenado |
|----------------------------|---------|----------|--------------|-----------|
| Boletus aereus             | 24      | 13       | 37           | ✅ 59% backtest |
| Amanita caesarea           | 17      | 18       | 35           | ✅ (backtest pendiente) |
| Boletus pinophilus         | 11      | 11       | 22           | ✅ 36% backtest (overfitting) |
| Lactarius deliciosus       | —       | —        | 16           | ❌ < 20 ep mínimo |

Nota: los conteos a nivel área son menores que a nivel micro_area porque micro_areas del mismo
área en la misma fecha se fusionan en un único episodio.

Los episodios de la tabla corresponden al último entrenamiento y no incorporan
automáticamente el avance posterior de la revisión. Estado operativo comprobado en la
copia fresca de HA: 254 `review` (120 `draft`, 131 `valid`, 3 `doubtful`), 233 con
`flush_abundance=pending` y 40 válidas sin `micro_area_id`.

## Worker ml_train_v0 — implementación (2026-08-03)

Nuevo tipo de job `"worker_ml_train_v0"` para el worker externo. Paralelo a `rebuild_v0`
(que genera el artefacto de features), pensado para chaining futuro vía `triggered_by_job_id`.

### Diseño del job

- **Separación de responsabilidades**: `rebuild_v0` reconstruye features, `ml_train_v0` entrena
  modelos. Dos jobs independientes; en el futuro el coordinador puede encadenarlos automáticamente.
- **`triggered_by_job_id`**: campo vacío = trigger manual desde la UI. No vacío = disparado
  automáticamente por un rebuild (hook para chaining futuro, aún no implementado en coordinador).
- **work_key**: `"ml_train:v0:{features_digest}"` — deduplicación por artefacto de features.
  Dos requests sobre el mismo features.json no crean dos jobs concurrentes.
- **promotion_eligible**: siempre `True`. La promoción es manual (botón "Promote models" en UI).

### Bundle de inputs

3 ficheros planos escritos por el coordinador en `input_bundles/{job_id}/`:
- `job_spec.json` — job_id, species_ids, min_rows=10, cv_folds=3
- `features.json` — copia de `mushroom_observation_features_v0.json` en vivo
- `known_sites.json` — copia de `mushroom_known_sites.json`

Sin estructura de snapshot GIS ni validación de fingerprints (no aplica para training).

### Resultados del worker

Staging en `worker_data/{job_id}/ml_candidate/`:
- `ml_train_result.json` — manifest con schema_version "0.2", kind "mushroom_ml_v0_result",
  trained_species, artifacts (path/size_bytes/sha256)
- `ml_train_report.json` — métricas/backtest correspondiente exactamente a los
  modelos del candidato
- `ml_models/{species_id}.joblib` — un fichero por especie entrenada

Endpoints separados de los de rebuild (evitan confusión):
- `POST /api/mushrooms/workers/jobs/ml-result-file` — sube manifest o artefacto
- `POST /api/mushrooms/workers/jobs/ml-result-complete` — finaliza y verifica

### Promoción

Sin freshness check (no aplica: no hay snapshot de inputs). Revalida hashes y
copia atómicamente por fichero los `.joblib` a
`mushroom_paths.mushroom_ml_models_dir()` y el informe a
`mushroom_ml_v0_report.json`; el informe se promociona después de los modelos.
Invalida las instancias cacheadas del Predictor y escribe `promotion_receipt.json`.
No actualiza `mushroom_model_v0_state.json` (tarea de rebuild, no de training).

### Subprocess del worker

Script `scripts/run-mushroom-ml-train-job.py` lanzado como subprocess dentro del container:
- Lee `job_spec.json`, `features.json`, `known_sites.json` del dir de inputs
- Llama a `mushroom_ml_trainer.run()` con progress callback
- Construye manifest con sha256 del informe y de cada `.joblib`
- Escribe `ml_candidate/ml_train_result.json`
- Stdout final: `{"status": "ml_train_complete", "trained_species_count": N, ...}`

### Imagen worker

`rainmapper-worker/Dockerfile` ahora instala:
```
numpy==2.4.6 pandas==2.2.2 scikit-learn==1.9.0
```
Y copia `rainmapper_core/mushroom_ml_trainer.py` + `scripts/run-mushroom-ml-train-job.py`.

### Ficheros modificados

| Fichero | Cambios |
|---------|---------|
| `rainmapper_core/mushroom_worker_jobs.py` | `JOB_TYPE_ML_TRAIN`, `create_ml_train_job()`, `authorize_ml_train_result_upload()`, ext. `begin_candidate_promotion()` + `_normalized_result()` |
| `rainmapper_core/mushroom_worker_results.py` | `receive_ml_train_result_file()`, `finalize_ml_train_result()`, `promote_ml_train_candidate()`, `upload_ml_train_result()` |
| `rainmapper_core/mushroom_worker_transport.py` | `download_ml_train_inputs()` |
| `rainmapper_core/mushroom_worker_service.py` | Rama ml_train en `run_claimed_job()` |
| `rainmapper-app/app/web_server.py` | `create_mushroom_ml_train_job()`, `receive_mushroom_ml_train_result_file()`, `complete_mushroom_ml_train_result()`, `promote_mushroom_ml_train_candidate_job()`, endpoints POST |
| `rainmapper-app/app/mushroom_workers_ui.py` | `_render_ml_train_panel()`, botón promote ml_train |
| `mushroom-data/mushroom_labels.json` | 9 labels nuevos `ui.worker_ml_train*` (en/es/ca) |
| `rainmapper-worker/Dockerfile` | numpy + pandas + scikit-learn; copia ml_trainer + run script |
| `scripts/run-mushroom-ml-train-job.py` | CLI nuevo (subprocess del worker) |

### Pendiente

- Instalar la app HA `0.2.232`; no requiere reconstruir la imagen worker ni
  reentrenar porque no cambia el contrato ni las features de entrenamiento.
- Repetir cuando sea necesario el job ml_train_v0 end-to-end ya validado: crear
  job desde UI, worker lo recoge, entrena, sube y promover en HA.
- Implementar chaining automático rebuild → ml_train en el coordinador (campo `triggered_by_job_id`).

### Cobertura meteorológica por fuente
| Fuente | Rango disponible |
|---|---|
| Meteocat | dic 2016 → hoy (fuente principal histórica) |
| Wunderground | ago 2023 → hoy |
| Meteoclimatic | sep 2023 → hoy |
| AEMET | jun 2026 → hoy (solo reciente) |

Observaciones sin cobertura meteo: 19 (años 2012–2013). Decisión: mantenerlas como referencia de campo, no invertir en backfill histórico para 19 obs.

## Setales conocidos (2026-08-03)

22 áreas, 46 micro_areas en `docker-data/mushroom-data/mushroom_known_sites.json`.

| Área (`area_id`)              | Micro_areas                                                                   |
|-------------------------------|-------------------------------------------------------------------------------|
| bacanella                     | bacanella                                                                     |
| breda                         | arriba                                                                        |
| coll_de_la_batalla            | principal                                                                     |
| el_perello                    | lo_burgar                                                                     |
| els_ports                     | la_mola                                                                       |
| ermita_ascensio               | obaga_de_la_castellana                                                        |
| espunyola                     | muntanya                                                                      |
| guils                         | el_comu · estacio · la_feixa · la_socarrada · plantacion_pinitos              |
| la_gavarra                    | paradell                                                                      |
| la_masella                    | estacion · km11 · km9                                                         |
| llambilles                    | abajo · arriba · medio                                                        |
| olvan                         | bosquecillo · cercado_vacas · la_pera · mas_ballaro · romeros · serra_ramons  |
| ordino                        | cota_2100                                                                     |
| prats_de_llucanes             | bosc_davant_prats_llucanes                                                    |
| rectoria_de_la_selva          | rectoria                                                                      |
| rubio                         | plantacion                                                                    |
| salteguet                     | entrada · salteguet_fondo                                                     |
| sant_jaume_de_boixadera       | pla_de_boixadera                                                              |
| sant_joan                     | baga_de_sant_andreu · coll_de_leix · cota_1400 · obaga_de_la_culla · recta_1700 · serrat_de_la_carbassa |
| santa_maria_de_merles         | la_tor_nova · casa_escrigues · la_coromina                                    |
| selva_del_camp                | casa_perros · mas_de_sant_josep · mas_de_la_cabrera                           |
| vallcebre                     | agustinet · petitons                                                          |

## CLAUDE.md creado (2026-08-01)

Se creo `CLAUDE.md` en la raiz del repositorio. Claude Code lo carga automaticamente
en cada sesion. Contiene estructura del proyecto, entrypoints, comandos de validacion,
flujo de release, reglas operativas y referencia del modulo de setas. Mantenerlo
actualizado al introducir cambios estructurales relevantes.

## Repositorio y release estable

- Workspace unico:
  `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Release HA publicada en GHCR y version del repositorio: `0.2.232` (2026-08-08),
  digest `sha256:bb819e5407f1c685eb75b05955841b3e35554d3467140a3ff56a2708eec721da`.
  En HA real está instalada y validada `0.2.232`.
  Workers (M1 y M5) probados y funcionales.

### Histórico: última release validada antes de ML (0.2.214)
- Release instalada y validada en ese momento: `0.2.214` (`524bf2c`).
  Búsqueda global de Observaciones validada en HA real.
- Imagen: `ghcr.io/cginebrosa/rainmapperha:0.2.214`, digest
  `sha256:a13a4bb1a1de0bc901fe198ee01ea25a6fe7fb594b1721321de7df0173cb698a`.
- Manifests verificados: `linux/amd64`
  `sha256:cb03ce65b1d926f96063f2ab2754e4cd299e8c76c5bb365a2d463bcf55b469bc`
  y `linux/arm64`
  `sha256:bf465baef107f537d110463664871ce8e57e6a2bea22f5dbe5601413844180dc`.
- El repositorio GitHub sigue publico por decision explicita del usuario.
- El usuario autorizo expresamente el 2026-07-20 el bump, publicacion y
  commit/push de `0.2.214` tras validar localmente la busqueda corregida.

El codigo de release esta versionado. Antes de continuar, ejecutar
`git status --short`; no limpiar, revertir ni sobrescribir cualquier cambio
local nuevo que aparezca.

## Correccion clave: no existe una imagen HA de desarrollo

No hay, ni se quiere crear, una imagen de desarrollo/sideload de Home Assistant.
Introducirla complicaria innecesariamente el despliegue y la continuidad.

No se creo ni se debe crear una imagen HA de desarrollo. `0.2.208` introdujo el
coordinador normal, `0.2.209` corrigio su refresco bajo Ingress y `0.2.210`
controla la interaccion de Workers y la preparacion costosa de entradas sin
cambiar los flags seguros ni el fallback HA. `0.2.211` integra los avisos de
actividad en el polling: los mensajes de preparacion, cola y conflicto se
retiran al finalizar el trabajo, mientras los errores reales permanecen.

La `0.2.208` arranco con ambos interruptores apagados. Despues se publico
`8100` solo en la LAN, se activo `Enable external worker connections`, se
emparejo M1 y la prueba inocua de asignacion termino correctamente en 13 s.
En `0.2.209` se comprobo que Rainmapper, el worker y la pagina en reposo son
estables, al igual que una asignacion. Una sola prueba de envio de entradas
consume aproximadamente un nucleo mientras calcula los hashes de 5,87 GiB,
termina correctamente y devuelve la CPU a la normalidad. Los clics repetidos
antes de ver respuesta iniciaban varias preparaciones sincronas concurrentes,
agotaban la CPU de HA y provocaban timeouts de watchdog y salidas 137 de otros
add-ons. `0.2.210` prepara el bundle en segundo plano, impide duplicados con un
lock no bloqueante, desactiva inmediatamente el boton y reutiliza una cache
privada de hashes GIS validada por metadatos del fichero.

`0.2.211` ya se instalo y se valido con el worker M1 por LAN. El reposo, la
asignacion, el envio de entradas y la retirada automatica de avisos quedaron
estables. Una reconstruccion candidata privada de todas las especies elegibles
termino verificada al 100 % en 55 s (`Candidate result verified`) sin tocar el
modelo vivo. Despues se activo `Allow external rebuilds and promotion`: un job
operacional completo termino en 49 s y su promocion manual instalo correctamente
el candidato como modelo vivo, retiro la accion y conservo la copia anterior.

Siguiente orden:

1. Publicar solo con autorizacion expresa las mejoras locales: descarte con
   modal de candidatos terminales no promocionados, limpieza segura en HA y
   worker, y pantalla compacta HA + dos workers con trabajos ordenables.
2. Validar el descarte con un candidato terminal no promocionado; despues
   probar corte/reconexion sin revocar la credencial. La reconstruccion parcial
   y la cancelacion de `Amanita caesarea` ya se probaron en HA real.
3. Completar pruebas de freshness/cache y seguridad del endpoint.
4. Verificar otra vez el fallback HA y medir las fases en HA y M1 sobre el mismo
   snapshot/dataset.

La conexion actual usa HTTP en la LAN privada. No publicar `8100` en el router;
Tailscale/TLS/ACL queda como endurecimiento posterior.

## Estado del worker externo local

El prototipo funciona enteramente en el laboratorio Docker local y no depende
de HA real:

- UI Rainmapper local: `http://127.0.0.1:8101`.
- Coordinador local, solo en la red Docker: `http://rainmapper-ha-ui:8100`.
- Health local del worker: `http://127.0.0.1:8110/health`.
- Inicio/parada: `./mushroom_worker_start.sh` y
  `./mushroom_worker_stop.sh`.
- Imagen generica privada: `rainmapper-worker`; servicio/contenedor
  `rainmapper-worker`; volumen persistente `rainmapper-worker-data`.
- El launcher admite `--help`, nombre, URL del coordinador, pairing y modo no
  interactivo; recupera la configuracion no secreta y la identidad desde el
  volumen. El token permanente se guarda separado bajo `secrets/`.
- El worker es headless: la interfaz humana y la autoridad permanecen en
  Rainmapper.
- La comunicacion es outbound desde el worker. Rainmapper conserva la fuente de
  verdad de datos vivos, jobs y artefactos aceptados.
- Pairing temporal de un solo uso, Bearer permanente por worker, registro
  multi-worker, heartbeat, deteccion desconectado, revocacion y ejecutor
  predeterminado estan implementados localmente.
- La cola persistente implementa lease/claim, inicio, progreso, finalizacion,
  cancelacion cooperativa y forzada, y reasignacion solo antes del inicio.
- Un `work_key` impide ejecuciones activas solapadas. Especies disjuntas pueden
  ejecutarse en paralelo; los alcances completos o con especies comunes se
  bloquean.
- La pagina `Workers y trabajos` centraliza los lanzamientos y conserva HA como
  fallback. No existe fallback silencioso si el ejecutor predeterminado esta
  desconectado o no es compatible.
- Alcances externos locales operativos: todas las especies elegibles,
  pendientes y una especie.
- El aviso `Modelo V0 desactualizado` y las antiguas acciones de Observaciones
  navegan a `Workers y trabajos` con el alcance preseleccionado; ya no lanzan un
  rebuild directamente.

### Pipeline, datasets y promocion

- HA y worker usan el pipeline unico
  `rainmapper_core/mushroom_rebuild_pipeline.py`; la ruta HA estable continua
  en `legacy` salvo flag opt-in.
- Contratos versionados locales: `InputManifest 0.1`, `JobSpec 0.1` y
  `ResultManifest 0.1`.
- El snapshot vivo se congela en Rainmapper. El worker descarga solo paths
  declarados, valida tamaños/SHA-256 y nunca monta directamente `docker-data`.
- La imagen no contiene GIS/DEM. El dataset semiestatico se sincroniza desde
  Rainmapper a staging solo si falta o cambia el fingerprint, se valida y se
  activa atomicamente en el volumen persistente.
- Cache actual probada: `mushroom_gis_v0`, 10 ficheros,
  6.306.367.027 bytes. Primera carga a volumen vacio y reutilizacion posterior
  con cero bytes transferidos verificadas.
- El worker genera nueve artefactos candidatos privados, sube manifest y bytes,
  y Rainmapper vuelve a validar contrato, hashes, tamaños y contadores.
- La promocion siempre es explicita. Una promocion completa o parcial instala
  atomica y conjuntamente los nueve artefactos; la parcial mezcla solo las
  observaciones/especies declaradas con el ultimo modelo vivo.
- Antes de instalar los artefactos, HA elimina referencias auxiliares del
  worker y rebasa las rutas de metadatos a las rutas autoritativas del
  coordinador. Los datos privados existentes no se reescribieron durante la
  auditoria.
- Las promociones se serializan para que trabajos disjuntos no pierdan cambios.
- Se conservan como maximo dos copias recuperables de los nueve artefactos
  derivados anteriores (aproximadamente 2 MB por copia, sin GIS/DEM). La poda
  ocurre solo tras una promocion correcta.
- Estas copias son rollback operativo, no un catalogo historico de modelos.
  Para la futura fase ML queda documentado un registro versionado independiente
  con algoritmo, parametros, snapshot/dataset, metricas comparables y seleccion
  explicita del modelo activo.
- La opcion de conexiones externas esta activa en la instalacion real para M1;
  la opcion operacional de reconstruccion y promocion sigue desactivada hasta
  el siguiente ensayo controlado.

## Consolidacion por episodio en el modelo V0 (2026-08-02)

Implementada la politica de consolidacion de observaciones en episodios dentro
de `mushroom_learned_model.py`:

- Clave de episodio: `(species_id, micro_area_id, date)`.
- `prediction_target`: favorable si alguna obs del episodio es favorable.
- Variables categoricas (hosts, bosques, suelos, habitat, aspecto): union de valores
  con trazabilidad de fuente; no hay limite de hosts, el modelo V0 es descriptivo.
- Variables numericas: observacion de mejor `source_quality` del episodio.
- `episode_observation_ids`: lista de IDs para trazabilidad.
- Obs sin `micro_area_id`: excluidas del entrenamiento (`excluded_no_area` en summary).

`micro_area_id` ahora fluye desde la observacion hasta el artefacto de features v0:
añadido a `CSV_FIELDS` y `build_observation_weather_row` en
`mushroom_observation_context.py`, y a `CSV_FIELDS` y `build_joined_row` en
`mushroom_observation_features.py`.

4 tests nuevos en `test_mushroom_learned_model.py`. Suite completa: **391 tests OK**.

## Validacion local de cierre

Resultados comprobados el 2026-07-20 tras consolidar el diff y sus correcciones
posteriores:

- `.venv/bin/python -m unittest discover -s tests`: **386 tests OK** (391 tras consolidacion episodios 2026-08-02).
- `.venv/bin/python scripts/validate-mushroom-data.py`: **0 errores y 11
  warnings conocidos**.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: **OK**, incluidos los
  386 tests, sintaxis Python/JavaScript/shell, versiones y fixtures.
- Las imagenes locales HA/worker se inspeccionaron sin montar volumenes: no
  contienen `docker-data`, GIS/DEM, credenciales ni configuracion persistente
  del worker. HA contiene solo los assets `mushroom-data` ya versionados.
- Reconstruccion externa completa local, transferencia GIS a volumen vacio,
  reutilizacion de cache, corte/reconexion, cancelacion, corrupcion/freshness,
  retorno de 9/9 artefactos y promocion manual atomica: verificadas.
- Alcance `una especie` para `cantharellus_lutescens`: completado y
  promocionado.
- Alcance `pendientes` para la misma unica observacion: completado y
  promocionado.
- Los hashes de las otras 13 especies permanecieron exactamente iguales.
- Segundo job `pendientes`: cancelado cooperativamente en Meteorologia al 55 %,
  sin promocion.
- La retencion elimino la tercera copia y mantuvo las dos mas recientes.
- La web y el protocolo quedaron separados: `8099` rechaza las rutas del
  worker, `8100` solo acepta el protocolo cerrado y exige Bearer. Una sonda
  manual desde el contenedor worker existente alcanzo `8100` dentro de la red
  Docker; ese puerto no se publico en el Mac.
- El proceso worker que llevaba horas activo no se reinicio para no reclamar ni
  alterar jobs conservados. Sigue usando en memoria la URL antigua `:8099` y
  registra 404; el proximo arranque mediante `mushroom_worker_start.sh` migrara
  la URL local persistida a `:8100` antes de conectarse.
- No quedan rebuilds candidatos activos. La cola local conserva tres probes de
  transporte antiguos en `claimed`; no son reconstrucciones ni modifican el
  modelo. No borrarlos sin revisar/autorizar.

Los contenedores locales se reconstruyeron con el codigo actual y quedaron
encendidos al cerrar, pero la proxima sesion debe comprobar su estado real en
vez de asumirlo.

### Objetivo `prediction_favorable`

La derivacion se verifico explicitamente en los datos locales actuales:

- features: 126 filas = 66 favorables + 60 desfavorables;
- 0 discrepancias respecto a `prediction_favorable` del catalogo;
- 0 valores sin politica conocida;
- modelo entrenable: 125 filas = 65 favorables + 60 desfavorables.

La diferencia es `obs_20241109_0005` (`cantharellus_lutescens`): es favorable
pero sigue en borrador y se excluye del entrenamiento. Sigue pendiente, si se
considera necesario, comprobar visual/operativamente estos recuentos en HA; no
confundirlo con la validacion local ya cerrada.

## Prioridades siguientes

### P0 — Consolidar el prototipo antes de publicar nada

Estado: consolidacion completada, publicada en `0.2.208`, instalada y probada
contra M1 real; el refresco se publico en `0.2.209` y el control de interaccion
y preparacion pesada en `0.2.210`. La sincronizacion de avisos con el estado
terminal de los trabajos se publica en `0.2.211`.

1. La API permanece apagada por defecto, la autenticacion es fail-closed y el
   modo operacional exige simultaneamente API y autenticacion. HA expone dos
   opciones separadas: `Enable external worker connections` y
   `Allow external rebuilds and promotion`, ambas desactivadas por defecto.
2. Se confinan los paths de snapshots/GIS, se verifica la huella del manifest,
   se acota el JSON del protocolo y se evita conservar paths privados del
   worker tras una promocion.
3. El empaquetado fuente excluye `docker-data` y `mushroom-GIS`; la imagen HA
   incluye el coordinador pero no lo habilita. La comprobacion final de la
   imagen construida corresponde a P1, antes de publicar.
4. Preparar un checkpoint/commit solo cuando el usuario lo pida. No mezclar un
   release apresurado con el cierre documental.

### P1 — Preparar una version HA normal para la prueba real

1. Topologia interna definida: web/Ingress permanece en `8099`; el protocolo
   del worker usa un listener dedicado `8100`, no publicado por defecto en HA,
   con rutas cerradas y autenticacion obligatoria. Los controles humanos del
   worker en `8099` solo aceptan Ingress autenticado de HA.
2. Elegir y validar como primera exposicion privada el puerto host de `8100`
   mediante LAN/Tailscale y su ACL/TLS. Comparar Tailscale del host frente a
   sidecar Docker. El sidecar favorece
   portabilidad, pero no elude politicas del Mac ni debe ser requisito para la
   primera prueba si LAN/Tailscale del host basta.
3. Imagen HA local construida con el Dockerfile normal e inspeccionada sin
   volumenes: incluye coordinador/UI/core, no contiene datos privados ni
   GIS/DEM y la reconstruccion local HA sigue disponible en `legacy` por
   defecto.
4. Bump y GHCR de `0.2.214` completados con autorizacion expresa. `0.2.214` y
   `latest` comparten el digest multi-arch verificado
   `sha256:a13a4bb1a1de0bc901fe198ee01ea25a6fe7fb594b1721321de7df0173cb698a`;
   import check arm64: `image_import_ok 0.2.214 False False True True`. Instalada
   en HA real y búsqueda global de Observaciones validada (2026-08-02).

### P2 — Prueba M1 ↔ HA real

- M1 ya esta emparejado por LAN con HA real y la prueba de asignacion termino
  correctamente en 13 s.
- `0.2.211` esta instalada; reposo, asignacion, preparacion de entradas y
  retirada automatica de avisos quedaron comprobados.
- La reconstruccion completa operacional en M1 termino en 49 s, fue verificada
  y se promociono manualmente al modelo vivo con exito. Falta probar pendientes
  y una especie contra HA real.
- Probar cancelacion cooperativa/forzada, worker apagado, corte/reconexion,
  duplicados/solapes, stale result y cache presente/ausente.
- `0.2.212` ejecuta la promocion en segundo plano con fases, porcentaje y barra
  mediante el polling existente; ya se valido en HA real.
- `0.2.213`: `Descartar` aparece solo en candidatos terminales no
  promocionados y abre un modal. HA elimina resultado y snapshot privados; una
  orden/acuse idempotente por heartbeat elimina el directorio del job en el
  worker. Una promocion activa bloquea el descarte; una interrumpida solo se
  puede borrar si no hay recibo, backup ni staging de recuperacion. El modelo
  vivo, sus dos rollback y la cache GIS/DEM quedan fuera del borrado. Para la
  prueba integral hay que instalar HA y reiniciar el launcher del worker, que
  reconstruye su imagen.
- La misma version compacta `Workers y trabajos`: HA y dos workers caben
  en tres columnas, las pruebas/gestion quedan plegadas, el encabezado pierde
  textos redundantes y el acceso azul que solo hacia scroll. La tabla permite
  ordenar por cualquier columna, muestra los jobs HA como `HA local` y compara
  fechas de HA/worker por instante UTC para evitar ordenes falsos por offset.
- Observaciones deja de mostrar el desplegable heredado de ultima reconstruccion
  GIS: no estaba ligado a un job concreto y podia prometer una revision vacia o
  distinta del trabajo reciente. La ejecucion y el historial quedan en Workers.
- `0.2.214` corrige la busqueda de Observaciones bajo paginacion: Enter envia
  inmediatamente, la escritura se envia con debounce, se vuelve a pagina 1 y
  se buscan todos los campos persistidos y los nombres visibles resueltos de
  especie, area, microarea y catalogos antes de paginar. Instalada en HA real
  y búsqueda global validada (2026-08-02). M1 y M5 probados y funcionales;
  M5 aproximadamente 1.5x más rápido que M1 en red local.
- Verificar que HA reconstruye localmente aunque no haya worker.
- Medir tiempos por fase HA/M1 con el mismo snapshot y dataset.

### P3 — Portabilidad y ML posteriores

- Repetir `docker load` y bootstrap en otro daemon/host sin reutilizar capas ni
  volumen; probar tambien una actualizacion real del dataset semiestatico.
- Solo despues incorporar jobs separados `build_ml_dataset`, `train_ml_model`
  y `evaluate_ml_model`, sin promocion automatica.
- M5 y AWS quedan diferidos.

## Riesgos y dudas abiertas

- El prototipo grande ya esta versionado en `e2f117d`; los datos persistentes y
  GIS/DEM siguen fuera de Git y no deben limpiarse.
- La equivalencia local no sustituye una prueba en HA/Raspberry ni una prueba
  de red real.
- Falta elegir y validar en HA real la publicacion privada de `8100`, su
  ACL/TLS y la topologia Tailscale inicial; el protocolo ya no comparte el
  listener web `8099`.
- No se ha demostrado aun portabilidad en un daemon/host realmente limpio.
- La auditoria local no encontro secretos ni datos GIS/vivos incorporados al
  contexto de imagen. Antes de publicar sigue siendo obligatorio inspeccionar
  la imagen HA construida y su configuracion efectiva.
- `docker save/load` mueve la imagen, no el volumen persistente; un host nuevo
  debe reconstruir cache/configuracion mediante bootstrap y sincronizacion.
- Los datasets GIS/DEM requieren revisar licencias/atribucion antes de cualquier
  redistribucion fuera del entorno privado.
- El modelo V0 sigue siendo descriptivo/auditable, no un modelo ML predictivo.

## Archivos relevantes

Diseno y continuidad:

- `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
- `docs/mushrooms/mushroom-ml-training-plan-es.md`
- `docs/decisions.md`
- `docs/todo.md`

UI/coordinador:

- `rainmapper-app/app/web_server.py`
- `rainmapper-app/app/mushroom_workers_ui.py`
- `rainmapper-app/app/mushroom_profiles_ui.py`
- `rainmapper-app/app/mushroom_known_sites_ui.py`

Worker y despliegue local:

- `rainmapper-worker/`
- `mushroom_worker_start.sh`
- `mushroom_worker_stop.sh`
- `mushroom_lab_start.sh`
- `rainmapper-local/docker-compose.yml`
- `rainmapper-local/docker-compose.worker-local.yml`

Core compartido:

- `rainmapper_core/mushroom_rebuild_pipeline.py`
- `rainmapper_core/mushroom_rebuild_contracts.py`
- `rainmapper_core/mushroom_rebuild_snapshot.py`
- `rainmapper_core/mushroom_rebuild_comparison.py`
- `rainmapper_core/mushroom_worker_*.py`

Pruebas:

- `tests/test_mushroom_rebuild_*.py`
- `tests/test_mushroom_worker_*.py`
- `tests/test_web_server_auth.py`

## Reglas innegociables de continuidad

- Trabajar exclusivamente en el workspace indicado.
- Usar siempre `.venv/bin/python` (Python 3.11), nunca el Python del sistema.
- No revertir ni sobrescribir cambios locales existentes.
- No borrar, sustituir ni versionar datos privados de
  `docker-data/mushroom-data` ni GIS/DEM.
- No hacer bump, release, limpieza GHCR ni cambios destructivos sin peticion
  expresa.
- No crear una imagen HA de desarrollo como atajo.
- Mantener siempre la reconstruccion local de HA como fallback.
- Todo texto visible nuevo de setas debe existir en
  `mushroom-data/mushroom_labels.json` para `en`, `es` y `ca`.

## Planificació: verificació i comparació de models candidats (pendent)

### Context
Ara mateix la promoció d'un model candidat és un acte de fe: no hi ha manera de
comparar el candidat amb el model viu abans de decidir. El botó "Promote" existeix
però no mostra res que justifiqui la decisió.

### Objectiu
Quan el worker acaba un `ml_train_v0` i el resultat és terminal (llestos per promocionar),
la UI hauria de permetre:
1. **Verificar** el candidat: veure les mètriques del nou model (accuracy, AUC, backtest)
   sense haver de promocionar-lo.
2. **Comparar** el candidat amb el model viu actual: quines espècies milloren, quines
   empitjoren, diferència de backtest per espècie.
3. **Decidir** amb informació: promocionar tot, promocionar algunes espècies, o descartar.

### Peces necessàries
- `ml_train_result.json` (ja existeix al staging del worker) porta `trained_species`
  i sha256/mida dels `.joblib`. No porta mètriques de backtest.
- `mushroom_ml_v0_report.json` (generat pel trainer, ja existeix) porta accuracy,
  AUC i backtest per espècie. Caldria incloure'l com a artefacte al bundle de resultats.
- El model viu té el seu propi report si ha estat entrenat des del worker (staging anterior).
  Si no, no hi ha report del model viu i la comparació seria parcial.

### Decisions de disseny a prendre
- Incloure `mushroom_ml_v0_report.json` al bundle de resultats del worker (al costat dels `.joblib`).
- Afegir endpoint GET per llegir el report del candidat (sense promocionar).
- Afegir endpoint GET per llegir el report del model viu (si existeix).
- UI "Workers y trabajos": quan un job `ml_train_v0` és terminal i no promocionat,
  mostrar botó "Veure mètriques" que obri un panel de comparació.
- Promoció parcial per espècie (opcional, més complexa): permet promocionar
  B. aereus (que millora) però no B. pinophilus (que empitjora). Valorar si val la pena.

### Prioritat
Pendent. No bloqueja res actual. Fer-ho abans del proper cicle de re-entrenament
quan hi hagi prou observacions revisades per justificar una nova versió del model.

## Planificación: atributos ecológicos en micro_area + herencia en observaciones (pendiente)

### Análisis realizado (2026-08-04)

Se analizaron las 232 observaciones `calibration_use=include` con `micro_area_id` asignada.
Los atributos categóricos (`observed_host_ids`, `observed_forest_type_ids`,
`observed_soil_tendency_ids`, `observed_habitat_feature_ids`, `observed_aspect_ids`)
están bien rellenos: 226/232 tienen hosts, 211-216 tienen el resto.

**Hallazgo clave:** en la mayoría de micro_areas los valores son idénticos en todas las
observaciones — por ejemplo `olvan_la_pera` tiene `host_quercus_ilex` en 25/25 obs y
`forest_holm_oak` en 25/25. Es decir, ya son de facto atributos del lugar, no de la visita.
Excepción: `la_masella_km11` (4 obs sin ningún dato — importación masiva sin evidencia).

### Diseño acordado

Patrón **"defaults from reference + override per observation"**:

1. **`mushroom_known_sites.json`** añade atributos ecológicos por micro_area:
   `default_host_ids`, `default_forest_type_ids`, `default_soil_tendency_ids`,
   `default_habitat_feature_ids`, `default_aspect_ids`.
   Se derivan de las observaciones existentes: valor presente en >50% de obs `include`.

2. **Al crear una observación o asignar micro_area**, los atributos se copian automáticamente
   desde la micro_area como valores por defecto. El usuario puede sobrescribirlos si ese día
   observó algo diferente.

3. **Flag de sobreescritura**: cuando el usuario edita manualmente un atributo, queda marcado
   (`site_context_overridden: true` o a nivel de campo) para distinguir "heredado de micro_area"
   de "observado específicamente ese día".

4. **Para el modelo ML**: el trainer puede elegir qué usar:
   - Atributos de la micro_area (más estables, menos ruido por varianza inter-observación)
   - Atributos de la observación (más específicos, capturan variaciones del día)
   Esta decisión se toma cuando se implemente el uso de variables categóricas en el modelo.

### Pasos de implementación (en orden)

1. **Paso 0 (ya hecho):** análisis confirma que los datos son derivables de obs existentes.
2. **Paso 1:** añadir campos `default_*` a `mushroom_known_sites.json` derivándolos del
   conjunto `include` final tras la revisión (script de derivación automática).
3. **Paso 2:** UI: al asignar micro_area a una observación, pre-rellenar los atributos
   desde `mushroom_known_sites.json` si están vacíos en la observación.
4. **Paso 3:** flag de sobreescritura en la observación.
5. **Paso 4 (futuro):** usar variables categóricas en el modelo ML, decidiendo fuente.

### Prerequisito
Terminar de revisar en HA las 254 observaciones `review` pendientes antes de derivar los defaults,
para que la base de derivación sea completa y representativa.
