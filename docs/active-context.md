# Active Context

Ventana operativa de RainmapperHA. Contiene solo lo necesario para continuar.
El histórico está en `docs/decisions.md`, `docs/project-archive.md` y los
documentos temáticos enlazados.

## Estado operativo actual — 2026-08-13

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- HA `0.2.253` está instalada y validada en la RPi4; es la generación instalada
  anterior a la release pendiente.
- HA `0.2.254` está publicada y pendiente de instalación. `0.2.254` y `latest`
  comparten `sha256:bcc72af6fe60bffd0a75246c5ca6726ef42a9a1852c7fa8fabdcef81b9b8b362`
  y contienen `linux/amd64` y `linux/arm64`.
- El worker M1 desplegado es `1.0.8`, healthy/idle, con la misma identidad y
  caché GIS de 6.306.367.027 bytes. Incorpora rebuild y training altitude V2.
- Worker `1.0.7` queda reemplazado: reconstruía features sin
  `weather_station_altitude_m` y entrenaba contratos V1.
- Tras instalar `0.2.253` se repitió `Reconstruir y reentrenar todo`: reconstrucción
  completa (1 min 29 s), entrenamiento completo (31 s), promoción conjunta y
  primera consulta fría del Predictor completadas correctamente.
- El runtime sincronizó la nueva generación sin discrepancia de hash. El
  artefacto vivo contiene 31 filas Edulis y ninguna microárea de Olvan; la
  relación contaminada ya no aparece en la UI.

## Qué corrige HA 0.2.253

- En el flujo encadenado, el entrenamiento ya recibe el `features.json`
  candidato serializado con las rutas que tendrá tras la promoción. Así, el
  hash grabado en los modelos coincide exactamente con el artefacto vivo.
- La misma función canónica de rebase se usa al preparar el entrenamiento y al
  promover, evitando dos implementaciones que puedan divergir.
- Los mensajes largos del Predictor conservan el diagnóstico completo, pero
  ahora rompen rutas y hashes dentro del ancho del modal.
- Validación local: suite completa con 672 tests, smoke test y comprobaciones de
  versión/sintaxis superados. La imagen multiarch se construyó una sola vez.

## Incidencia altitude V2 y validación local

- HA `0.2.253` solicita `fixed_gap_7d_altitude_v2` y
  `lag_event_altitude_v2`; la generación producida por worker `1.0.7` contiene
  `fixed_gap_7d_v1` y `lag_event_v1`. Ese desacople explica que el Predictor HA
  muestre todas las predicciones vacías mientras el Predictor M1 anterior sí
  responde.
- Snapshot estable posterior al runner creado solo en `/private/tmp`; no se
  modificó `share` ni HA. Rebuild completo: 350 observaciones GIS, 399 filas de
  features, 436.776 registros meteorológicos leídos, 78,8 s.
- El artefacto V2 tiene altitud de estación en 313/399 filas y altitud GIS en
  347/399. El training produjo 8 modelos operativos y 9 modelos sombra V2.
- Prueba centinela Edulis/La Masella y Salteguet: `lag_event_altitude_v2`
  disponible, con correcciones térmicas auditables (+0,08 °C y −2,19 °C).
- 85 pruebas focalizadas y smoke global de 673 tests superados.

## Próximos pasos, en orden

1. Instalar HA `0.2.254` y verificar que arranca y ve worker `1.0.8`.
2. Desde HA ejecutar una única `Reconstruir y reentrenar todo`, comprobar que
   ambos jobs producen altitude V2 y activar la generación completa.
3. Validar Predictor semanal y consulta centinela; HA y M1 deben coincidir.
4. Solo después retomar Biology V3.

## Riesgos y restricciones activas

- No promover candidatos antiguos ni mezclar artefactos y modelos de
  generaciones distintas; la generación activa actual sí es coherente.
- La generación activa es coherente internamente pero es V1; no satisface el
  Predictor altitude V2 de HA. No intentar arreglarla copiando modelos sueltos.
- Biology V3 parte de una muestra pequeña y sesgada por visitas; los scores
  brutos no son probabilidades calibradas.
- Mantener la RPi4 para coordinación y trabajo incremental acotado. Rebuild,
  entrenamiento y Predictor pesado permanecen en el M1.
- El histórico meteorológico fuente/año, CSV vivos acotados, colas intradía,
  Tomap/MapLibre y Predictor histórico ya están migrados en HA; no rehacer el
  cutover durante esta corrección.
- Preservar el worktree. No limpiar, resetear ni sobrescribir cambios locales.

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
  redundantes. Preguntar ante destrucción, escritura en HA no autorizada o una
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
