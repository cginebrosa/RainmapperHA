# Active Context

Ventana operativa de RainmapperHA. Este documento contiene únicamente el estado
necesario para continuar; el histórico vive en `docs/decisions.md`,
`docs/project-archive.md` y los documentos de diseño enlazados.

## Estado a 2026-08-10

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Último release preparado: HA `0.2.242` y worker `1.0.4`.
- HA `0.2.239` está instalada y validada en la RPi4 real; `0.2.242` está
  publicada y pendiente de instalación/validación por el usuario.
- Tags `0.2.242` y `latest`: digest multi-arquitectura
  `sha256:3abd516d7aeac7bd4f8bfeacc2d96be2823f339a6c5d31cdc62caaf64ebc562b`,
  con manifests `linux/amd64` y `linux/arm64` verificados.
- Worker M1 actualizado y en ejecución con `rainmapper-worker:1.0.4`, conectado
  al coordinador real, healthy/idle y con cachés persistentes GIS/DEM y
  Predictor válidas. Su identidad es `worker_1a9a232c20fe2ee2` / `M1 Personal`.
- El paquete privado arm64 del M5 está preparado en
  `~/Desktop/RainmapperWorker`: TAR `1.0.4`, Compose, scripts e instrucciones
  actualizados y validados. El TAR `1.0.1` se conserva como rollback.
- La pareja publicada acelera
  reconstrucción, promoción y entrenamiento: reconstrucción y entrenamiento
  coalescen control/progreso remoto a una actualización cada 2 s y conservan
  solo el evento más reciente; la promoción reutiliza la caché segura de hashes
  GIS y solo vuelve a calcular por completo los archivos cuya identidad de
  sistema haya cambiado. Cancelación y estados terminales siguen siendo
  explícitos.
- Al reiniciar, el M1 reclamó un entrenamiento ML que ya estaba encolado; acabó
  correctamente en unos 30 s y verificó cuatro especies. No quedó ocupado.
- Validación local posterior: smoke completo con 543 tests, validadores y
  `git diff --check`, todo correcto.

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

La prueba conjunta de HA `0.2.239` y worker `1.0.2` confirmó dos perfiles
distintos. La primera entrada M1 tardó unos 18,1 s extremo a extremo, con
`backend_seconds` de 4,861 s y runtime sincronizado; repeticiones calientes
reales tardaron aproximadamente 5,6–7,3 s aunque el backend cacheado necesitó
solo 0,001–0,002 s. En HA, la primera entrada tardó 34,45 s, una repetición
caliente 0,77 s, un cambio de día 1,12 s y una fecha histórica 11,96 s.

Por tanto no existe un único ejecutor «más rápido»: M1 es mejor para abrir y
obtener una recomendación aislada; HA es mejor para una sesión con mucha
navegación caliente.

## Próximo paso inmediato

0. Instalar HA `0.2.242`. Después, reconstruir todos los artefactos y reentrenar
   en el M1 desde la UI de HA. La reconstrucción es necesaria porque el cambio
   autoritativo `scarce=1` se materializa en el artefacto de features.
1. Validar que el entrenamiento completa con la política nueva: holdout
   cronológico solo cuando ambos tramos contienen las dos clases, CV
   estratificada sobre todos los episodios y ajuste productivo con todos ellos.
   El objetivo operativo es salida mínimamente interesante: `scarce=1`,
   `very_scarce=0`, `absent=0`; no equivale a mera presencia/ausencia.
2. Validar la barrera fenológica general del Predictor: meses principales y
   secundarios ejecutan ML; fuera de temporada devuelve `out_of_season` sin
   cargar modelo ni meteorología. `mushroom_profiles.json` forma parte del
   runtime remoto, por lo que HA y worker aplican la misma regla.
3. El siguiente trabajo es revisar Diagnostics para separar explícitamente
   `backend_seconds`, cola,
   sincronización, cachés y tiempo total.
4. No ejecutar el runner, no publicar otra versión y no cambiar red/Tailscale
   durante este trabajo.

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
- El worker M5 todavía no ha instalado `1.0.4`; el paquete privado ya está
  preparado en el Escritorio.
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
- `rainmapper-worker/Dockerfile`: worker `1.0.4`.
- `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y
  `rainmapper-app/CHANGELOG.md`: HA `0.2.242`.
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
