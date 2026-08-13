# Active Context

Ventana operativa de RainmapperHA. Contiene solo lo necesario para continuar.
El histórico está en `docs/decisions.md`, `docs/project-archive.md` y los
documentos temáticos enlazados.

## Estado operativo actual — 2026-08-13

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- HA `0.2.252` continúa instalada en la RPi4. La release correctiva `0.2.253`
  está publicada en GHCR y pendiente de instalación: `0.2.253` y `latest`
  comparten `sha256:5b1fad84e76ae80a1144e8f96f8dd54abd708bbcef0e27d27566fd4645ce4e89`
  y contienen `linux/amd64` y `linux/arm64`.
- El worker M1 sigue en `1.0.7`; no necesita actualización para esta corrección.
- En HA se ejecutó correctamente `Reconstruir y reentrenar todo`: reconstrucción
  completa (1 min 43 s), entrenamiento completo (31 s) y promoción conjunta.
  La UI mostró ambos jobs completados y promovidos.
- La primera consulta posterior del Predictor fue bloqueada correctamente por
  una discrepancia de identidad entre el `features.json` vivo y los modelos
  sombra promovidos. No usar esa generación para validar predicciones.

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

1. Instalar HA `0.2.253` y confirmar que arranca. No hace falta cambiar el
   worker M1 `1.0.7`.
2. Ejecutar otra vez `Reconstruir y reentrenar todo`. La generación promovida
   por `0.2.252` no se repara solo instalando el coordinador nuevo.
3. Cuando ambos jobs terminen, usar exclusivamente la promoción conjunta.
4. Abrir el Predictor y comprobar un caso actual y uno histórico. Confirmar que
   no reaparece el error de identidad y que un error largo cabe en el modal.
5. Revisar `Por especie`: Edulis/Olvan no debe aparecer si la observación
   corregida ya no está en el store vivo. La UI indicó 350 observaciones
   elegibles en la reconstrucción reciente; no conservar el antiguo supuesto
   de 399 sin volver a medirlo.
6. Con este incidente cerrado, retomar Biology V3 desde su auditoría y
   especificación.

## Riesgos y restricciones activas

- Hasta reconstruir y promover de nuevo con `0.2.253`, la generación activa es
  internamente incoherente y el Predictor seguirá rechazándola.
- No promover candidatos antiguos ni mezclar artefactos y modelos de
  generaciones distintas.
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
