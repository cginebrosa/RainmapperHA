# Active Context

Ventana operativa de RainmapperHA. Este documento contiene únicamente el estado
necesario para continuar; el histórico vive en `docs/decisions.md`,
`docs/project-archive.md` y los documentos de diseño enlazados.

## Estado a 2026-08-11

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Release actual: HA `0.2.246` publicada y worker M1 `1.0.6` actualizado.
- HA `0.2.244` está instalada en la RPi4 real. El usuario reconstruyó todos los
  artefactos, entrenó los modelos y promovió el candidato con M1 `1.0.5`.
- HA `0.2.246` está pendiente de instalar por el usuario y sustituye a
  `0.2.245`, que no llegó a instalarse. Sus tags `0.2.246` y
  `latest` comparten el digest multi-arquitectura
  `sha256:ec443dca611007a2efd8e510e2d9c907ec0e9374267d3974a8ffbb431731f93e`,
  con manifests `linux/amd64` y `linux/arm64` verificados.
- Worker M1 actualizado y en ejecución con `rainmapper-worker:1.0.6`, conectado
  al coordinador real, healthy/idle y con cachés persistentes GIS/DEM y
  Predictor válidas. Su identidad es `worker_1a9a232c20fe2ee2` / `M1 Personal`.
- El paquete privado arm64 del M5 está preparado en
  `~/Desktop/RainmapperWorker`: TAR `1.0.5`, Compose, scripts e instrucciones
  actualizados y validados. SHA-256 del TAR:
  `d1c4237cc7fff52430d355deae2ba7022f83347f6b054ac833ec08ce151940ac`.
  El TAR `1.0.1` se conserva como rollback y `1.0.4` se retiró para no acumular
  copias.
- La pareja publicada acelera
  reconstrucción, promoción y entrenamiento: reconstrucción y entrenamiento
  coalescen control/progreso remoto a una actualización cada 2 s y conservan
  solo el evento más reciente; la promoción reutiliza la caché segura de hashes
  GIS y solo vuelve a calcular por completo los archivos cuya identidad de
  sistema haya cambiado. Cancelación y estados terminales siguen siendo
  explícitos.
- Al reiniciar, el M1 reclamó un entrenamiento ML que ya estaba encolado; acabó
  correctamente en unos 30 s y verificó cuatro especies. No quedó ocupado.
- Validación de release: smoke completo con 573 tests, validadores y
  `git diff --check`, todo correcto.
- HA `0.2.244` incorpora la mejora de presentación del Predictor: el
  Predictor amplía su ancho útil de escritorio, renombra los dos indicadores
  ambiguos como fiabilidad ecológica y estadística operativa, y añade ayudas
  localizadas a la cabecera, los contratos meteorológicos y todos los campos
  técnicos. El usuario completó la validación visual local antes de publicar.

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

HA `0.2.246` y worker `1.0.6` reúnen los tres ajustes encontrados durante la
validación real y la aclaración visual validada posteriormente en local:

- el recomendador remoto se mostraba vacío porque `recommender` no incluía
  `areas`; ahora las transporta y el adaptador también las deriva de `rankings`;
- el modal no permitía cancelar una predicción en curso; ahora solicita
  cancelación cooperativa, detiene su polling y el worker consulta control una
  vez antes de publicar;
- tres consultas Pinícola acabaron en `409`. No fue el límite de tamaño: las
  respuestas medidas fueron 793/819/862 KiB. El worker ahora conserva el cuerpo
  exacto del error para identificar la causa en la siguiente reproducción. Aun
  así, el contrato se amplía de 1 a 8 MiB, más 64 KiB de envoltorio HTTP, y queda
  documentada la obligación de compactar antes de aproximarse al guardarraíl.
  Los resultados pesados se externalizan además de la cola caliente a ficheros
  por job verificados por tamaño/SHA-256. Así, el polling deja de releer hasta
  50 respuestas de ~0,8 MiB; esta acumulación es una explicación plausible del
  aumento de CPU observado en la RPi, aunque no explica por sí sola el `409`.

El smoke de release pasa completo con 579 tests. M1 `1.0.6` está healthy/idle y
conserva identidad, coordinador y cachés. HA `0.2.246` aclara además que la señal
experimental reúne el modelo sombra con menor Brier de cada contrato, y que
fiabilidad `limitada` no significa que el estimador ganador falle la validación.
Falta que el usuario instale HA `0.2.246` y repita en este orden: resumen
inicial, cancelación y Pinícola. Si el
`409` reaparece, el nuevo detalle del worker permitirá identificar su contrato
exacto sin conjeturas.

La posible incorporación de un LLM pequeño en M1/M5 queda acotada en
`docs/mushrooms/mushroom-worker-local-llm-narrator-design-es.md`. Sería una
capacidad opcional de narración local que recibiría el dictamen estructurado ya
cerrado, sin autoridad para cambiarlo ni inventar datos, con validación estricta
y fallback al texto determinista. No se descarga ni se incluye ningún modelo en
la release actual.

1. Validar localmente y después en HA real las correcciones de transporte del
   Predictor, conservando M1 durante la sesión. La reconstrucción, promoción y
   entrenamiento con HA `0.2.244`/M1 `1.0.5` ya están completados. La sustitución
   de la recomendación v0 por la pareja
   `fixed_gap_7d_v1` + `lag_event_v1`. El motor determinista ya selecciona por
   especie el estimador con mejor Brier que la prevalencia. La interpretación
   `1.1` separa compatibilidad/evidencia ecológica, soporte/consenso estadístico
   y dictamen práctico; una sola familia validada ya no se presenta como
   consenso, y un veto ecológico oculta de la cabecera los scores brutos que no
   pueden intervenir. La explicación rica se conserva en dos bloques lógicos y
   la auditoría técnica sigue completa. Si ningún estimador supera el baseline,
   conserva una señal bruta explícitamente descartada solo en el detalle. Los
   shadows ya aportan además una señal experimental genérica: por contrato se
   elige el que tenga mejor Brier por debajo de prevalencia y se resume como
   favorable, desfavorable, incierto o contradictorio, con rango, modelos y
   cautela fuera de dominio. Sigue sin cambiar el dictamen ni rankings. Aereus
   en Olvan el 2026-08-16 queda como ejemplo: ecología compatible, LR/RF sin
   soporte operativo y SVM experimental favorable 66–67%, pero con cautela por
   racha térmica fuera de dominio.
   Los bundles locales `1.2` guardan soporte de variables y predicciones holdout:
   la LR se excluye ante extrapolaciones severas e Historial distingue scores
   fuera de muestra de episodios incluidos en el ajuste final. La UI local
   retira la tarjeta y los factores meteorológicos v0 y conserva el detalle
   técnico de ambos contratos. El laboratorio añade ET, HGB, KNN y SVM como
   modelos sombra; la SVM se omite si train no permite calibrarla (actualmente
   Marçot/fixed-gap). La primera evaluación local encuentra una señal nueva
   relevante: SVM mejora la prevalencia de Aereus en fixed (`0,1858` frente a
   `0,2222`) y lag/event (`0,1778`), mientras LR y RF no lo hacían. Sigue sin
   autoridad operativa hasta validar episodios, horizontes y salidas futuras.
   Queda registrada una prueba prospectiva para el 2026-08-15: Pinícola en
   Guils y Salteguet. El usuario planea visitar ambas; antes del resultado, los
   mejores shadows dan HGB fixed 98%/88% y SVM lag 71%/62%, respectivamente,
   mientras el dictamen RF conserva 52–58% y 50–52%.
   La prueba visual/funcional local está completada y estos cambios ya forman
   parte de HA `0.2.243` y worker `1.0.5`; falta la validación final en HA real.
2. Pulir los modelos de aprendizaje actuales y comparar alternativas más
   manejables con el mismo dataset. No hay por ahora más observaciones de campo
   ni meteorología histórica: la fase debe mejorar tratamiento de gaps,
   dimensionalidad, validación, abstención y presentación usando los datos
   disponibles.
3. Usar como referencia vinculante
   `docs/mushrooms/mushroom-ml-model-hardening-plan-es.md`. El caso centinela es
   Aereus en Coll de la Batalla el 2026-08-14: 71% final por media de LR 98% y
   RF 44% pese a sequía; cuatro días meteorológicos futuros desconocidos se
   trataron como valores favorables y la validación temporal fue peor que azar.
   El contrato reproducible para esta fase está en
   `docs/mushrooms/mushroom-ml-experiment-contract-es.md`: benchmark congelado,
   fecha de corte explícita, `fixed_gap_7d_v1` y `lag_event_v1`. Ambos se
   entrenan con LR reducida y RF restringido. Desde esta iteración local forman
   la pareja operativa: `mushroom_ml_v0` queda como baseline interno y la UI
   decide mediante estimadores que superan la prevalencia en Brier. Los scores
   siguen sin ser probabilidades calibradas.
   El contrato meteorológico revisado ya está implementado localmente para los
   shadows: 120 días, eventos hasta 90, lluvia ausente/suprimida como cero
   efectivo con cobertura, temperatura/humedad sobre días disponibles, corte
   de `lag_event` en ayer y salto a la siguiente estación elegible hasta 15 km.
   Entrenamiento y Predictor comparten los constructores de variables y el
   selector; la iteración está publicada en HA `0.2.243` y worker `1.0.5`, pero
   HA todavía no la tiene instalada.
   En el caso centinela ya no falta ninguna variable: `fixed_gap_7d_v1` baja a
   24,48%, mientras `lag_event_v1` sube a 76,96%. Ambos ven 0 mm recientes y
   71 días desde lluvia significativa; la discrepancia está ahora en la LR y
   el horizonte del modelo, no en `null` meteorológicos imputados. Ninguno
   supera todavía la prevalencia en Brier.
   La UI local en `http://127.0.0.1:8101/mushrooms/predictor` ya usa una copia
   fresca de HA reconstruida en `docker-data` (400 observaciones, Parquet de
   630.449 filas y 1.948 estaciones), con 6 modelos operativos y 12 shadows.
   El laboratorio muestra estación, distancia, salto, coberturas, bandas,
   eventos, horizonte y validación temporal. La evaluación principal es ahora
   70/30 estratificada por clase, agrupada por fecha y reproducible con semilla
   42; el 70/30 cronológico queda como diagnóstico secundario.
   En Aereus/Coll/2026-08-14 la prueba local produce 16% operativo, 24%
   `fixed_gap` y 27% `lag_event`. En Edulis los shadows ya están disponibles,
   pero muestran que la validación cronológica no existe porque el tramo
   antiguo sólo contiene favorables.
4. Después se revisará Diagnostics para separar explícitamente
   `backend_seconds`, cola, sincronización, cachés y tiempo total.
5. No ejecutar el runner, no publicar otra versión y no cambiar red/Tailscale
   durante este trabajo salvo instrucción posterior explícita.

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

- Las probabilidades ML actuales son experimentales. En Aereus, el holdout
  temporal dio ROC-AUC `0,3818` para LR y `0,4545` para RF; el ensemble al 50%
  no tiene en cuenta esa falta de calidad.
- Cobertura parcial de lluvia puede aparecer como acumulado cero; además,
  variables críticas ausentes se imputan sin que el Predictor reduzca confianza
  o se abstenga. Esto puede invertir el efecto aprendido de la lluvia.
- El baseline usa 39 variables para solo 51 episodios de Aereus, con ausencias
  meteorológicas relevantes. La siguiente fase debe empezar por benchmark,
  huecos y reducción de variables antes de añadir complejidad.
- La ETA del modal es deliberadamente aproximada; no debe interpretarse como
  porcentaje del backend.
- Al eliminar callbacks, la cancelación interactiva no se consulta dentro de
  cada fila. La UI ya puede solicitarla y abandonar la espera, pero el worker la
  confirma al terminar la unidad indivisible mediante una única consulta de
  control; no es una interrupción inmediata del cálculo Python.
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
- `docs/mushrooms/mushroom-ml-model-hardening-plan-es.md`: diagnóstico real del
  primer entrenamiento y plan inmediato de comparación/endurecimiento ML.
- `docs/runtime-diagnostics.md`: caja negra y procedimiento RPi4.
- `docs/release-flow.md`: publicación HA.

## Validación habitual

Regla de autorización confirmada por el usuario: una tarea explícita incluye
permiso para sus ediciones, consultas, pruebas y demás acciones no destructivas.
No solicitar confirmaciones redundantes. Preguntar solo ante destrucción,
escritura en HA fuera de lo autorizado o ampliación material de alcance.

```bash
PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Antes de cualquier release HA, leer y seguir `docs/release-flow.md`. No publicar
ni hacer bump sin petición explícita del usuario.
