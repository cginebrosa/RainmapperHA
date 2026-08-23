# Active Context

Ventana operativa para continuar RainmapperHA. Revalidar código, datos, runtime
y worktree antes de afirmar estado presente. Las decisiones duraderas están en
`docs/decisions.md`; las prioridades completas, en `docs/todo.md`.

## Estado al cierre — 2026-08-23

- Workspace `/Users/carlosginebrosa/Developer/RainmapperHA`, rama `inicial`.
- El worktree está deliberadamente muy sucio: contiene cambios de código,
  pruebas, documentación, datos, módulos nuevos no rastreados y eliminaciones.
  Preservarlo íntegramente; no restaurar, limpiar ni sobrescribir nada local.
- Las versiones declaradas y publicadas son HA `0.2.264` y worker `1.0.17`.
  La imagen HA multiarch `0.2.264` y `latest` comparte el digest
  `sha256:3835fa0fe59889873386661f31e1823a77a0b174ef89d8e6772ae14efa195dc5`
  con manifests `linux/amd64` y `linux/arm64`; todavía no está instalada en HA.
- El worker normal fue reconstruido como `1.0.17` sobre el mismo volumen
  `rainmapper-worker-data` y conservó `worker_id: worker_1a9a232c20fe2ee2`;
  su health quedó `idle` y el usuario confirmó que HA vuelve a verlo. Se retiró
  únicamente la imagen local `1.0.16`, no el volumen ni su identidad.
- El paquete privado arm64 está en
  `/Users/carlosginebrosa/Desktop/RainmapperWorker-1.0.17`; el TAR tiene SHA-256
  `90e4ce8abd2ddbdda7df0e820d3e2710c76cebe2c43485badf88134fe02e0df8`.
  El commit de release `ea75d95` está publicado en `inicial`.
- No se usó Tailscale, no se instaló ni modificó el add-on de HA real y
  `ml_storage_reconciliation_apply` continúa deshabilitado. El usuario sí había
  instalado antes la corrección meteorológica mínima y ejecutado su runner.

## Histórico meteorológico reparado

- La copia fresca de HA confirmó que el histórico activo no incorporaba el
  backfill oficial auditado: AEMET carecía de humedad en 2012–2025 y Meteocat
  conservaba particiones dispersas después de 2016. IDW sí estaba conectado y
  consumía esos datos incompletos; no era un fallo de selección de fuente.
- El histórico reparado recupera 374/417 observaciones con target operativo
  para ventana fija y 2.618/2.919 muestras de retardo. Las otras 43 no tienen
  target operativo (`review`), incluidas 13 en borrador.
- La generación compacta original omitía un manifiesto predecesor y el primer
  runner real se detuvo de forma segura. Se añadió
  `python -m rainmapper_core.weather_history_rebase`, que convierte de forma
  verificada e idempotente la generación activa en raíz sin copiar objetos.
- El usuario instaló con Rainmapper detenido el parche mínimo
  `ready-to-upload-root-fix`. La raíz
  `20260823T003617919308Z-58903f62a763` quedó verificada y el runner manual
  posterior terminó con código 0, creando la hija
  `20260823T004654212246Z-59a50ee60e80`: 46 particiones, 5.481.652 filas y
  50.297.632 bytes activos, con hashes verificados.
- El runner tardó 5 min 50 s; el post-drain meteorológico consumió 2 min 14 s.
  Queda pendiente optimizarlo. Antes de otro backfill masivo también hay que
  corregir `_BoundedTableWriter`: generó grupos Parquet de 128 filas y fue
  necesario compactarlos a la granularidad contractual de 8.192.
- Evidencia reproducible:
  `docs/reports/mushroom-weather-history-repair-audit-2026-08-23.md`.

## Predictor multiversión local

- El registro local usa una `installed_generation_id` independiente para cada
  V2/V3/V4/V5w/V6w y `preferred_version_id: biology_v4`. La preferida es el
  valor por defecto; no desinstala ni degrada las demás.
- `Consultar fecha` hace competir las versiones marcadas y elige por separado
  ventana fija y retardo/evento. Un candidato solo es elegible si tiene
  probabilidad válida, aplicabilidad `within_observed_range` o `caution`, Brier
  estrictamente mejor que prevalencia y ROC-AUC >= 0,55. El ranking prioriza
  mayor mejora Brier, menor Brier, mayor ROC-AUC e identidad estable.
- La UI expone abstenciones y motivos, probabilidad sin redondeo ambiguo cerca
  del umbral de 60 %, fiabilidad estadística del ganador y consenso entre
  familias metodológicas como veredictos separados, con criterio en la ayuda y
  evidencia por escenario. Smooth Species/Shared/Partial son variantes de una
  familia logística, no evidencia independiente.
- Tras una predicción solo quedan desplegadas las versiones que contienen un
  algoritmo elegido; las demás siguen auditables pero plegadas.
- La revalidación visual de espaciado/tamaños, ayudas, veredictos y plegado se
  completó con confirmación del usuario. Se alinearon también los controles de
  Especies, Área, Fecha y Preferida mediante altura común y anclaje superior.
- La selección entre vistas quedó trazada y cubierta: `Consultar fecha` usa las
  versiones marcadas tanto en resumen como en detalle y franja semanal; Esta
  semana/recommender, Por especie e Historial usan solo la preferida. Ambos
  caminos delegan la elección independiente por escenario en
  `build_selected_operational_comparison`, también a través del contrato
  preparado del worker.

## Retención ML/worker implementada solo en local

- Especificación vinculante:
  `docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`.
- La caché TAR regenerable se resuelve fuera de `/share`, en
  `/media/rainmapper/runtime-cache/predictor-runtime-archives`; el laboratorio
  monta el equivalente bajo `docker-media/rainmapper`.
- `rainmapper_core/mushroom_storage_reconciler.py` y
  `rainmapper_core/mushroom_ml_storage_reconciler.py` generan un plan para
  bundles, resultados, staging, payloads Predictor, batches, generaciones,
  candidatos legacy, promotion-history y benchmarks. `dry-run` es el modo
  seguro; `ml_storage_reconciliation_apply` vale `false` por defecto.
- El mantenimiento operativo es un único flujo completo: rebuild, ML v0 y
  entrenamiento multiversión se verifican y autopromocionan conjuntamente. Se
  retiraron las rutas públicas de reconstrucción parcial, entrenamiento o
  promoción aislada y preparar/activar/rollback desde benchmark.
- Los benchmarks nuevos se compactan inmediatamente a `evidence_only` y solo
  conservan informe, hold-out, catálogo de calidad, identidad y manifiesto de
  evidencia. Historial, Ver informe y Borrar permanecen.
- Solo se protegen permanentemente batches referenciados por una generación
  instalada. Se conserva rollback transaccional durante la instalación y el
  backup más reciente del rebuild completo. Resultados operativos terminales
  pesados: 24 h; payloads Predictor: últimos 10 o 24 h, lo que proteja más.
- Validación definitiva previa al bump: smoke completo correcto con 1.003
  pruebas en 48,411 s, además de compilación Python, sintaxis JS/shell,
  fixtures y `git diff --check`. El ajuste CSS pasó 2 pruebas dirigidas y la
  coherencia del Predictor otras 9. El perfil aislado del recommender cargó 8
  predictores, hizo 58 comparaciones y 1.392 inferencias; una petición fría
  tardó 27,78 s, una caliente con fecha distinta 23,09 s y un hit exacto de
  caché tuvo una mediana de 24,6 ms. `dry-run` local con 59 entradas y
  190.107.758 bytes recuperables, cero errores y cero eliminaciones.
  `git diff --check` correcto.
- No está instalado ni probado en HA real. Antes de habilitar `apply`: smoke,
  revisión final, instalación autorizada, `dry-run` real revisado con el usuario
  y autorización destructiva separada.

## Riesgos y dudas activos

1. **Aplicabilidad no calibrada:** `outside_feature_ratio >= 0,05` y una salida
   a `>= 3 sigma` son constantes nuestras, no límites aprendidos ni reglas
   ecológicas. Auditar con hold-out qué variables disparan la regla y cómo se
   degradan Brier, discriminación y calibración antes de cambiar valores.
2. **Rendimiento:** el perfil aislado sitúa el coste en las 58 comparaciones:
   inferencia de modelos ~12 s, contexto meteorológico ~6 s y construcción de
   variables ~2,7 s en una petición caliente con fecha distinta. Las métricas
   existentes no aparecen como hotspot y no se añadió instrumentación
   persistente. Un experimento externo con bosques en serie redujo la inferencia
   a ~6,1 s y el total de 25,78 s a 20,66 s sin diferencias funcionales en la
   respuesta; las 465 diferencias observadas fueron solo tiempos internos. Es
   un candidato, no un cambio aplicado, y requiere implementación acotada,
   pruebas de paridad y nueva medición antes de adoptarlo.
3. **Retención destructiva:** nunca activar `ml_storage_reconciliation_apply`
   ni borrar restos reales basándose solo en el `dry-run` local.
4. **Código legacy:** las V5/V6 no-windowed siguen como `reference`; no
   retirarlas sin demostrar que ninguna referencia viva las necesita. La
   auditoría general de deuda está separada en `docs/todo.md`.

## Próximos pasos, en orden

1. Detenerse antes de instalar `0.2.264` en HA. Si el usuario lo autoriza,
   instalar y ejecutar primero el `dry-run` real de retención; revisar juntos su
   informe y pedir autorización independiente antes de cualquier `apply`.
2. Evaluar de forma acotada la inferencia serie para bosques de una sola muestra,
   con pruebas de paridad y benchmark repetible; no añadir métricas permanentes.
3. Auditar la regla 5 %/3 sigma con datos fuera de muestra, documentar evidencia
   y detenerse antes de proponer nuevos umbrales.
4. Después de cerrar la retención, realizar la auditoría separada de deuda y
   código obsoleto.

## Archivos relevantes

- Selector/UI: `rainmapper_core/mushroom_ml_multiversion_comparison.py`,
  `rainmapper_core/mushroom_predictor_service.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py`,
  `rainmapper-app/app/web_server.py`.
- Registro/mantenimiento: `rainmapper_core/mushroom_ml_version_registry.py`,
  `rainmapper_core/mushroom_ml_multiversion_transport.py`,
  `rainmapper_core/mushroom_local_full_update.py`,
  `scripts/run-mushroom-ml-multiversion-job.py`.
- Retención: `rainmapper_core/mushroom_paths.py`,
  `rainmapper_core/mushroom_storage_reconciler.py`,
  `rainmapper_core/mushroom_ml_storage_reconciler.py`,
  `rainmapper_core/mushroom_worker_results.py`.
- Histórico: `rainmapper_core/weather_history_writer.py`,
  `rainmapper_core/weather_history_rebase.py` y el informe citado arriba.
- Pruebas: `tests/test_mushroom_ml_multiversion_comparison.py`,
  `tests/test_mushroom_ml_multiversion_transport.py`,
  `tests/test_mushroom_ml_storage_reconciler.py`,
  `tests/test_mushroom_storage_reconciler.py`,
  `tests/test_mushroom_worker_results.py`, `tests/test_web_server_auth.py`.

## Reglas para continuar

- Leer `docs/codex-start-here.md` y este documento; consultar `docs/todo.md`
  solo para prioridades completas.
- Usar Codebase Memory MCP antes de descubrir o cambiar código y reindexarlo si
  sigue mostrando símbolos retirados.
- No usar Tailscale, no tocar HA real ni volver a modificar el worker normal y
  no hacer otro bump, build, publicación ni release sin autorización explícita
  nueva.
- Añadir pruebas proporcionadas al riesgo. El bloque transversal tiene smoke
  completo correcto; repetirlo solo si cambia código ejecutable de riesgo
  suficiente para invalidarlo.
