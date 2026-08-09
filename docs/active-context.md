# Active Context

Ventana operativa de RainmapperHA. Este documento contiene únicamente el estado
necesario para continuar; el histórico vive en `docs/decisions.md`,
`docs/project-archive.md` y los documentos de diseño enlazados.

## Estado a 2026-08-09

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Último commit publicado antes de este cierre: `c5a01f0`.
- HA `0.2.239` está publicada en GHCR y GitHub, pero el usuario todavía no ha
  confirmado su instalación/validación en la RPi4.
- Tags `0.2.239` y `latest`: digest multi-arquitectura
  `sha256:10d52bbb18d2c39a48cc8088d0c269e01b4d826d4b836ce287732c2df70f55f3`,
  con manifests `linux/amd64` y `linux/arm64` verificados.
- Worker M1 actualizado y en ejecución con `rainmapper-worker:1.0.2`, conectado
  al coordinador real, healthy/idle y con cachés persistentes GIS/DEM y
  Predictor válidas. Su identidad es `worker_1a9a232c20fe2ee2` / `M1 Personal`.
- Al reiniciar, el M1 reclamó un entrenamiento ML que ya estaba encolado; acabó
  correctamente en unos 30 s y verificó cuatro especies. No quedó ocupado.
- Smoke de release: 531 tests, validadores y `git diff --check`, todo correcto.

## Resultado principal de la sesión

El Predictor puede ejecutarse en HA o en un worker `predictor_v1`. HA conserva
la UI, selección, autoridad de jobs, resultados y Diagnostics; el worker es una
calculadora sin UI ni acceso directo desde el navegador.

La validación de HA `0.2.237`/worker anterior mostró que el ejecutor sí se
conservaba entre vistas, pero cada callback granular del Predictor hacía dos
peticiones HTTP síncronas al coordinador (control + progreso). Una semana de 56
área/día generaba 112 viajes y convertía un cálculo M1 de 2,617 s en 117–134 s.

La pareja HA `0.2.239` + worker `1.0.2` elimina ese cuello de botella:

- el worker publica solo transiciones duraderas de inicio y final;
- no retransmite progreso interno por área, fecha o especie;
- el modal muestra una espera/ETA calculada únicamente en el navegador a partir
  de medidas anteriores; no afirma ser progreso real;
- cuando llega el resultado, el modal se cierra y se sustituye la vista;
- el resultado conserva `backend_seconds`, cold/warm, fingerprint, estado de
  cachés, bytes sincronizados, versión/job/ejecutor y HA sigue midiendo duración,
  memoria y temperatura en su caja negra;
- si algún día se necesita detalle de fases del worker, se acumulará localmente
  y se adjuntará una sola vez al resultado final.

También siguen vigentes las optimizaciones publicadas previamente:

- ejecutor fijado durante toda la sesión del Predictor; solo se vuelve a elegir
  si el usuario pulsa Cambiar ejecutor o el seleccionado deja de estar apto;
- cachés LRU acotadas por fingerprint para resultados y respuestas completas;
- inferencia vectorizada para ranking, semana e historial;
- runtime inmutable sincronizado por fingerprint y caché persistente del worker.

## Referencia de rendimiento real

Prueba del usuario en HA/RPi4 inmediatamente antes de instalar `0.2.239`:

- apertura fría del Predictor: aproximadamente 30–40 s;
- navegación normal posterior entre días/especies/vistas: prácticamente
  instantánea;
- consulta de una fecha de hace unos dos años: aproximadamente 10 s, coherente
  con cargar bajo demanda otro contexto meteorológico del Parquet.

Medición directa dentro del M1:

- semana de 56 filas: 2,617 s inicial;
- misma respuesta cacheada: 0,001 s;
- el tiempo de 117–134 s observado antes de `1.0.2` era transporte de progreso,
  no cálculo ML.

No asumir todavía que el M1 extremo a extremo ya consigue esos 2–6 s: falta la
prueba real conjunta de HA `0.2.239` y worker `1.0.2`.

## Próximo paso inmediato

1. Instalar HA `0.2.239` en la RPi4. No hace falta ejecutar el runner.
2. Confirmar en `Workers y trabajos` que M1 aparece conectado, idle y versión
   `1.0.2`.
3. Abrir el Predictor seleccionando M1 y medir de forma aproximada:
   - primera entrada/recommender;
   - cambio a mañana y varios días;
   - Por especie;
   - Consultar fecha actual y una fecha histórica;
   - Historial;
   - repetición de alguna operación para observar caché caliente.
4. Verificar que todas las vistas conservan M1 sin volver a preguntar ni caer a
   HA mientras siga disponible.
5. Revisar Diagnostics: ejecutor, `backend_seconds`, cold/warm y cachés deben
   quedar registrados aunque el modal ya no muestre progreso granular.
6. Comparar con la referencia HA anterior. El objetivo de la prueba no es solo
   “ganar” a HA, sino confirmar que el worker responde en segundos y no consume
   recursos de la RPi4.

Si sigue tardando mucho, separar inmediatamente:

- `backend_seconds` del worker;
- tiempo total observado por HA;
- sincronización de runtime/bytes;
- estado de caché de respuesta y runtime;
- posible espera de cola o worker ocupado.

## Política de ejecución vigente y evolución pública

En el panel privado actual, las dos capacidades internas de política están
fijadas a `True`: permitir selección manual y permitir HA. No son opciones del
add-on ni campos de usuario; esa entrada por Ingress no tiene identidad
Rainmapper y todavía no aplica autorización por rol.

Para una futura integración autenticada dentro de MapLibre:

- usuarios normales: Auto, exclusivamente workers compatibles;
- sin worker disponible: mensaje de indisponibilidad o cola acotada; nunca
  fallback silencioso a HA/RPi4;
- sin selección manual para usuarios normales;
- administradores: la política futura podrá permitir selección y/o HA;
- el navegador siempre llama al gateway de HA; nunca se conecta directamente a
  un worker;
- antes de exponerlo a varios usuarios harán falta límites de concurrencia,
  rate limiting y caché compartida de respuestas.

La fuente futura de esas capacidades (rol hardcoded, campo de usuario o perfil)
queda deliberadamente sin decidir. No abrir ese trabajo durante la validación de
`0.2.239`.

## Diagnósticos y RPi4

- La pestaña Diagnostics es la autoridad de observabilidad: historial, A/B,
  evolución, promedios por versión, Gantt de las cuatro fuentes y recuperación
  de memoria.
- Runner y Predictor se agrupan por cargas comparables; no comparar tipos de
  operación distintos.
- `Operational duration` es trabajo real; `Diagnostic window` puede incluir las
  muestras posteriores de recuperación a 60/600 s.
- Los runners `all` producen una operación `Runner update` y otra `Runner`: la
  primera mide descarga/proceso meteorológico y la segunda el flujo completo.
- El P0 de memoria de la RPi4 está cerrado para el escenario monousuario probado:
  runner y Predictor no simultáneos, cero OOM y recuperación correcta. Seguir
  vigilando picos cercanos a 1,5 GiB de cgroup.
- Especificación y procedimiento: `docs/runtime-diagnostics.md`.

## Workers y almacenamiento

- HA y worker tienen secuencias de versión independientes; la compatibilidad se
  negocia por capacidades (`predictor_v1`, `weather_parquet_v1`,
  `terminal_job_cleanup_v1`, etc.), no por igualdad de versiones.
- `./mushroom_worker_start.sh` construye/arranca la versión declarada en
  `rainmapper-worker/Dockerfile` y conserva identidad, token y cachés del volumen.
- El snapshot prefiere `weather_daily.parquet`; conserva CSV como fallback para
  workers antiguos. Los CSV siguen siendo fuente meteorológica de ingestión.
- Antes de cada trabajo externo, HA reconcilia restos y muestra si limpió algo.
  Conserva 50 tombstones con scroll de unas 10 filas, dos backups y candidatos
  pendientes; bundles terminales/promocionados se eliminan. GIS/DEM permanece
  como caché compartida.
- Sigue pendiente una URL de coordinador anunciada y agnóstica de LAN/VPN/proxy.
  El M1 real conserva por ahora su coordinador Tailscale configurado; no cambiar
  puertos/IP ni aislar el lab en esta prueba.

## Datos y seguridad operativa

- Fuente autoritativa de setas en HA: `/share/rainmapper/mushroom-data/`.
- Copia local de pruebas: `docker-data/mushroom-data/`; no sobrescribir HA desde
  ella sin una sincronización explícita y verificada.
- GIS/DEM pesado en HA: `/media/rainmapper/mushroom-GIS/`, no `/share`.
- Media de observaciones en
  `/share/rainmapper/mushroom-data/media/observation-photos/`.
- No borrar `docker-data/`, `tmp/`, `mushroom-GIS/`, backups, históricos ni
  artefactos locales sin autorización explícita.
- No tocar CSV reales sin `docs/history-safety.md`.
- No inventar features, umbrales, pesos ni ventanas del modelo.
- Los textos visibles de setas deben existir en `mushroom_labels.json` para
  inglés, español y catalán.

## Riesgos y dudas activas

- La ETA del modal es deliberadamente aproximada; no debe interpretarse como
  porcentaje del backend.
- Al eliminar callbacks, la cancelación interactiva no se consulta dentro de
  cada fila del cálculo. El job sigue teniendo transiciones duraderas y los
  cálculos deberían durar segundos; revisar cancelación si alguna carga vuelve
  a ser larga.
- El worker M5 no se ha actualizado a `1.0.2` ni se ha preparado todavía el TAR
  de esta versión.
- La futura exposición pública no puede reutilizar la política privada actual
  con fallback HA: debe ser worker-only y limitar carga.
- `web_server.py` continúa siendo un hotspot grande; evitar ampliar su lógica de
  dominio si puede residir en `rainmapper_core` o módulos UI específicos.

## Archivos relevantes para continuar

- `rainmapper-app/app/web_server.py`: gateway, modal/ETA, selección y jobs.
- `rainmapper_core/mushroom_worker_service.py`: ejecución silenciosa y respuesta.
- `rainmapper_core/mushroom_worker_jobs.py`: estados duraderos de jobs.
- `rainmapper_core/mushroom_predictor_service.py`: cálculo, cachés y contrato.
- `rainmapper_core/mushroom_predictor_runtime.py`: runtime/fingerprint.
- `rainmapper-app/app/mushroom_workers_ui.py`: UI de workers y trabajos.
- `rainmapper-worker/Dockerfile`: worker `1.0.2`.
- `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y
  `rainmapper-app/CHANGELOG.md`: HA `0.2.239`.
- `docs/mushrooms/mushroom-remote-predictor-design-es.md`: diseño vinculante.
- `docs/runtime-diagnostics.md`: caja negra y procedimiento RPi4.
- `docs/release-flow.md`: publicación HA.

## Validación habitual

```bash
PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Antes de cualquier release HA, leer y seguir `docs/release-flow.md`. No publicar
ni hacer bump sin petición explícita del usuario.
