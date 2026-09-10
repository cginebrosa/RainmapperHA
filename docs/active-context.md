# Active Context

Ventana operativa de RainmapperHA al 10 de septiembre de 2026. No es
un histórico. Revalidar siempre repositorio, contenedores, datos y servicios
antes de asumir que este estado sigue vigente.

## Estado comprobado del repositorio

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- La release HA `0.2.301` está publicada en GHCR. Sustituye a `0.2.300` y añade
  configuración del orden de variantes de caché Wunderground y retención del
  historial ligero de precálculos automáticos.
- La fuente declara HA `0.2.301` y worker `1.1.1`; sus secuencias de versión son
  independientes.
- La base previa a esta release se revalidó en
  `3b9155e6014973763a04daf00ae16803fd227998`. Tras el commit de release debe
  revalidarse el HEAD publicado; debe permanecer fuera del commit
  `mushroom-data/mushroom_observations.json`:
  es dato del usuario y no debe editarse, restaurarse, borrarse ni incluirse en
  el commit. Los datos vivos del laboratorio están en `docker-data/`.

## HA 0.2.301 publicada

- GHCR `0.2.301` y `latest` se revalidaron al cierre y comparten el índice
  `sha256:bd89eb8635827e1f0403505bc06a6d9ce02e5797348e7ab44a9b88e73badc8ba`.
  Contienen manifests `linux/amd64`
  `sha256:3e7593f7c2ef89533d32f1c8875c94708a6761c50a2b8d2844c74858fcc3d80c`
  y `linux/arm64`
  `sha256:927fdf03033a597df995f1f3d6628ad80021c596ec852764b7c01599994b5048`.
- HA local se reconstruyó desde el worktree actual con la etiqueta de
  desarrollo `rainmapperha:local-ha-ui`; su imagen efectiva es
  `sha256:aeffc10beb32bb11f8260b5cec18ff568e4f833abf2fcd068ade69cfbb9d5f50`.
  Las huellas SHA-256 de `daily_api.py`, `rainmapper.py`, `web_server.py` y
  `run.sh` coinciden exactamente entre workspace y contenedor; la UI responde
  HTTP 200.
- El usuario confirmó anteriormente la instalación de `0.2.300` en HA real. El
  primer runner posterior completó la descarga Wunderground con la nueva
  instrumentación de caché activa: 101 estaciones, dos respuestas antiguas tras probar
  `identity`, `gzip` y `deflate`, y cinco fallbacks HTTP 204 al scraper.

## Worker operativo

- `rainmapper-worker` está activo y healthy con la imagen local privada
  `rainmapper-worker:1.1.1`; el worker no se publica en GHCR.
- Imagen efectiva:
  `sha256:3a2631dd3b9138f4821ef3901e0d11f057778b9e539350054d1923db17ccdb70`.
  Etiqueta, entorno y `/health` declaran `1.1.1`.
- Identidad: `worker_1a9a232c20fe2ee2`, nombre `M1 Personal`. Ambos carriles
  están idle; caché GIS/dataset y caché Predictor figuran válidas.
- Asociaciones persistidas revalidadas sin exponer credenciales:
  - principal: `http://100.111.77.48:8100`;
  - adicional `coordinator_fde2e9b1c6c1f5b2`:
    `http://rainmapper-ha-ui:8100`;
  - límite local: cuatro coordinadores.
- Está prohibido cambiar esas URLs sin autorización expresa para el destino
  concreto. Reconstruir, recrear, reiniciar o probar el worker no autoriza a
  modificar asociaciones.
- El runtime lógico está aislado por coordinador y reutiliza objetos físicos
  comunes por SHA-256. El CLI por `coordinator_id` continúa incompleto.
- La caché GIS activa ya contiene 13 ficheros y 6.424.592.573 bytes, incluido
  el DEM francés. Su fingerprint vigente es
  `sha256:7410f2e2482b77688027440fa047344bba65285fa2f9e812c07c65f769981574`.
- Antes de la limpieza, el volumen persistente del worker ocupaba 18.084.029
  KiB según `du`. Una auditoría por SHA-256 e inodo encontró 9.413.367.857
  bytes de copias físicas repetidas:
  6.306.367.027 en una versión GIS inactiva y 3.107.000.830 en snapshots y
  directorios de trabajos históricos. Tras confirmar el 2026-09-09 que las
  colas de ambos coordinadores no tenían trabajos activos, se eliminaron 19
  espacios de trabajo antiguos bajo `jobs/`, 58 espacios de trabajo legacy y
  la versión GIS inactiva
  `sha256:4aa3777e0f1c4d05c7788e464d87f4bcb952eaa40160701e49fda336445475f9`.
  El volumen pasó de 18.084.029 KiB a 7.144.228 KiB: 10,43 GiB liberados.
  Se conservó y validó en profundidad la versión GIS activa
  `sha256:5b537ffebbb9c17ce380ee21257204465eb1e310a159a05a224d74b65c7fe729`,
  además de los runtimes, precálculos y cachés operativas vigentes.

## Trabajo funcional cerrado

### Caché Wunderground

- Weather.com se comprobó sirviendo variantes divergentes según
  `Accept-Encoding`: la variante `gzip` conservaba IOLVAN3 a las 01:44 con
  0 mm, mientras `identity` y `deflate` devolvían lecturas de las 21:54/22:09
  con 63,5 mm. `Vary: Accept-Encoding` confirmó que es caché del CDN, no una
  caché local de Rainmapper.
- Para intervalos que incluyen hoy, el cliente usa por defecto el orden
  `gzip,identity,deflate`, configurable desde HA mediante una lista cerrada de
  las seis permutaciones válidas. Si el último `epoch`/`obsTimeUtc` supera cuatro
  horas de antigüedad prueba también las restantes variantes, conserva
  exclusivamente la respuesta con timestamp más reciente y registra reintentos,
  recuperaciones o persistencia de datos antiguos. En históricos no añade
  peticiones.
- El modo mensual permanece predeterminado y el semanal queda disponible como
  alternativa mutuamente excluyente. HA valida al guardar el orden de encodings;
  el arranque vuelve a validar tanto ese orden como la exclusión mutua de los
  modos mensual y semanal. Un runner local dirigido a IOLVAN3 acabó
  1/1, sin fallback ni errores, y persistió 63,5 mm para 2026-09-09 tanto en
  `Wunderground_incremental.csv` como en `weather_daily.parquet`.

### GIS francés Font-Romeu–Quérigut

- El DEM IGN RGE ALTI francés de 5 m está integrado como cuarto fallback, con
  `source_id = dem_france_rge_alti_5m`, y forma parte condicional del inventario
  del snapshot.
- El TIFF definitivo local tiene 6579 × 8368 píxeles, CRS EPSG:2154 reconocido
  formalmente por GDAL, 100 % de cobertura válida, checksum de banda 63498 y
  SHA-256
  `3e86d6c2ee4e3677dd895de369045b8f49c02a23902771692177b7a60256860f`.
- HA local obtiene ocho muestras válidas procedentes del DEM francés en cada
  una de las tres microáreas. La validación fue de solo lectura: la interfaz
  debe revisar y aplicar el contexto GIS/DEM persistido.
- La copia de `/Volumes/media` se sustituyó y verificó: tiene el mismo tamaño,
  SHA-256, checksum de banda y CRS EPSG:2154 que el TIFF local definitivo.

### Alta automática de especies en el catálogo de tuning

- Una especie que entra por primera vez recibe decisiones V2--V4 y V6
  declaradas. Sus 12 combinaciones V5 seleccionan configuración usando solo la
  partición de entrenamiento; si no hay evidencia suficiente queda registrado
  el fallback conservador ya definido.
- El catálogo emitido por el entrenamiento se incluye en el resultado del
  worker, se valida por identidad y SHA-256, se instala con el batch y se
  reutiliza en entrenamientos posteriores. Un hueco parcial en una especie ya
  representada o una forma nueva de modelo/versión/perfil sigue fallando de
  forma cerrada.
- La generación validada contiene 714 decisiones, 78 para
  `cantharellus_cibarius_sl`, incluidas 12 V5 con selección interna disponible,
  y ningún marcador provisional pendiente.

### Modelos constantes

- El entrenamiento calcula degeneración por `split_id`, especie y candidata
  exacta. Con al menos dos resultados y rango de probabilidades
  `<= 0,000001`, marca `constant_prediction=true`.
- La selección sellada excluye esa candidata para toda la especie con
  `constant_species_prediction`; el selector compartido vuelve a comprobar el
  veto, por lo que el precálculo lo hereda sin añadir coste a una consulta.
- No se rechaza un algoritmo por no tener coeficientes. Random Forest, KNN u
  otros siguen siendo aptos si sus predicciones hold-out no son constantes.
- En la generación promovida se comprobaron 2.880 entradas primarias y 3.456
  alternas, con 181 candidatas constantes en cada catálogo. Ninguna de las 280
  selecciones selladas ni de los 420 miembros del precálculo eligió una
  candidata constante.

### Explorador de modelos

- `rainmapper_core/mushroom_model_explorer.py` aporta una aplicación de solo
  lectura montada en `/models` por el servidor HTTP del worker. La instancia
  local responde en `http://127.0.0.1:8110/models`.
- Leer los selectores solo abre catálogo y manifiestos. El artefacto elegido se
  deserializa únicamente al pulsar `Inspeccionar este modelo`, mediante el
  loader que verifica SHA-256 y sin incorporarlo a la caché compartida.
- Muestra estructura real, variables, coeficientes o importancias cuando el
  estimador los expone, rangos de entrenamiento y configuración. Los signos y
  pesos no se presentan como causalidad. Algoritmos sin peso global fijo se
  explican como tales.
- Sigue siendo una aplicación aislable y no existe todavía enlace desde HA.

### Entrenamiento y precálculo validados en HA local

- Reconstrucción: `worker_job_RobUm1YQrDSrbSow`, resultado verificado como
  distinto. Entrenamiento base: `worker_job_Sh0LrML9gLOVTctP`, nueve especies,
  resultado verificado. Multiversión: `worker_job_HQ8eMiiJ0qe0PE66`, batch
  `operational_20260909T211842Z`, resultado verificado y promovido.
- El primer precálculo iniciado después del entrenamiento,
  `worker_job_oac7R5t9YSn9`, fue cancelado correctamente al quedar superado. Su
  reemplazo `worker_job_w1SZanQRBW0H` terminó, se publicó y se activó: 551,698 s
  de cálculo y 631,132 s totales en el worker.
- Los runners programados posteriores solicitaron nuevos precálculos al
  publicar su runtime y avanzaron la cobertura. El log del worker registra
  ejecuciones iniciadas aproximadamente a las 00:17, 01:51, 05:07 y 08:07
  CEST. Desde 0.2.301, activar un reemplazo ya no elimina del historial los
  precálculos terminales anteriores: permanecen en `Trabajos recientes` dentro
  del límite global de 50 trabajos. La retención de artefactos pesados sigue
  siendo independiente.
- El artefacto activo comprobado tras
  `worker_job_fJQB65AUngtj` es
  `sha256:c0b06a02d43948eb3810bfd08708dce2e1bc77f7cf9cebd911b7f9ad47b72ded`,
  con runtime fingerprint
  `sha256:2c73d71fd8d9c485a6f05c0e160e11ec13c79b40875c3bedffbbdfb6dee065d3`.
  Su publicación está completa y cubre del 10 al 16 de septiembre: nueve
  especies, cinco versiones, 79 parejas especie--área, 469 miembros y 158
  grupos ejecutados. Tiene 553 predicciones base y ocupa 31.211.520 bytes.
- El aumento de 157 a 158 grupos refleja una nueva pareja especie--área:
  `boletus_edulis` pasó de 15 a 16 áreas. `cantharellus_cibarius_sl` mantiene
  seis áreas; su alta previa explicaba el salto de 143 a 157 mediante ocho
  grupos generales y seis grupos de área.
- El smoke final de la candidata 0.2.301 pasó 1.350 pruebas en `59,050 s`,
  además de sintaxis, fixtures y comprobaciones de histórico. No se repitieron
  entrenamiento ni precálculo: el cambio funcional está limitado al cliente
  Wunderground y al historial ligero del coordinador y tiene pruebas dirigidas.

## Próximos pasos, por prioridad

1. Instalar HA 0.2.301 en HA real y comprobar el siguiente runner, sin repetir
   entrenamiento ni precálculo.
2. Revisar y aplicar desde la interfaz el GIS/DEM de las microáreas francesas
   que aún no lo tengan. No sobrescribir silenciosamente el contexto persistido.
3. Auditar de forma multiespecie las abstenciones por aplicabilidad. Separar
   tolerancia absoluta, desviación normalizada, tipo de variable y dirección de
   extrapolación. Caso inicial: Rovelló / Els Ports / 2026-09-07.
4. Diseñar cómo mostrar una probabilidad calculada pero vetada como dato
   diagnóstico, sin color de recomendación, ranking ni mensaje favorable.
5. Medir en la Raspberry Pi 4 la publicación HA--worker por fases antes de
   implementar streaming incremental o cambiar la política de `fsync`.
6. Completar administración CLI por `coordinator_id` sin alterar otros
   coordinadores.

## Riesgos y dudas activas

- HA real sigue en `0.2.300` según la última confirmación del usuario; no asumir
  `0.2.301` instalada hasta verificarla después de la actualización.
- La aplicabilidad actual puede vetar por una desviación normalizada alta aunque
  la diferencia absoluta sea pequeña. No ampliar umbrales globalmente sin la
  auditoría multiespecie.
- Una probabilidad vetada puede mejorar la transparencia, pero debe quedar
  inequívocamente separada de una recomendación.
- La optimización de streaming está documentada, no implementada. SHA-256 no
  sustituye la validación semántica, la autorización ni la promoción atómica.
- `mushroom_observations.json` sigue modificado y protegido fuera de Git.

## Archivos relevantes

- Entrada de continuidad: `docs/codex-start-here.md`.
- Prioridades: `docs/todo.md`.
- Decisiones: `docs/decisions.md`.
- Arquitectura: `docs/architecture.md`.
- Explorador: `rainmapper_core/mushroom_model_explorer.py` y
  `tests/test_mushroom_model_explorer.py`.
- Gate de constantes: `rainmapper_core/mushroom_ml_quality_catalog.py`,
  `rainmapper_core/mushroom_ml_reliability_audit.py` y
  `rainmapper_core/mushroom_ml_runtime_inference.py`.
- Worker y runtime multicoordinador:
  `rainmapper_core/mushroom_worker_service.py`,
  `rainmapper_core/mushroom_predictor_runtime.py` y
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- Rendimiento e integridad HA--worker:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`.
- Selección/aplicabilidad:
  `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`.
