# Active Context

Ventana operativa de RainmapperHA. Contiene solo lo necesario para continuar.
El histórico está en `docs/decisions.md`, `docs/project-archive.md` y los
documentos temáticos enlazados.

## Estado operativo actual — 2026-08-13

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- HA `0.2.253` está instalada y validada en la RPi4. `0.2.253` y `latest`
  comparten `sha256:5b1fad84e76ae80a1144e8f96f8dd54abd708bbcef0e27d27566fd4645ce4e89`
  y contienen `linux/amd64` y `linux/arm64`.
- El worker M1 sigue en `1.0.7`; no necesita actualización para esta corrección.
- Tras instalarla se repitió `Reconstruir y reentrenar todo`: reconstrucción
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

## Próximos pasos, en orden

1. Ejecutar un caso histórico centinela adicional para cerrar también la ruta
   de carga histórica con la nueva generación.
2. Con este incidente cerrado, retomar Biology V3 desde su auditoría y
   especificación.

## Riesgos y restricciones activas

- No promover candidatos antiguos ni mezclar artefactos y modelos de
  generaciones distintas; la generación activa actual sí es coherente.
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
