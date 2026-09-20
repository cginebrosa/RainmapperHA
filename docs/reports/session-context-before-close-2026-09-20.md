# Archivo anterior al cierre del 20/09/2026

Snapshot histórico de continuidad, no estado operativo vigente. Contiene
afirmaciones de fechas distintas que fueron sustituidas en el cierre. Los enlaces
relativos de los bloques copiados conservan su base original `docs/`.

## active-context.md antes de compactar

# Contexto activo — 19/09/2026

## Último desarrollo local: adopción del SMI · 20/09/2026

Referencia aceptada por el usuario: extracción regulada + Penman–Monteith +
una capa de 0–30 cm, compartida por entrenamiento/precálculo/mapa. El simple
queda como comparación visual. [SMI-07: decisión, código, consumidores y pruebas](mushrooms/SMI/adoption-2026-09-20/README.md).
Contratos nuevos invalidan datos/pesos físicos antiguos y precálculos anteriores;
requiere reconstruir entradas, reentrenar y precalcular antes de desplegar.

**0.2.315 publicada en GHCR; pendiente de instalación por el usuario en HA real.**
Tags versión/latest verificados con digest común
`sha256:8d064cef61c9e24fe283796b71aa37ad4d3eea2924141f4be554de1cc1a1f885`,
manifests AMD64/ARM64. [Informe de release](reports/ha-release-0.2.315.json).
El usuario autorizó preparar la release y reconstruir los servicios existentes.
HA local y el worker existente se reconstruyeron; sus dos coordinadores se
conservaron sin cambios. Primer circuito: reconstrucción y entrenamiento base
completos; multiversión rechazó el catálogo de ajustes por el cambio de contrato.
Se ha añadido una migración acotada del catálogo anterior: conserva únicamente
hiperparámetros/procedencia, nunca pesos ni métricas antiguas. Prueba con catálogo
persistido local: 714 decisiones, 403258 bytes, sin abrir modelos.

También se añade el modelo seleccionado por fecha antes del IFF en el mapa,
con nombres compartidos con Predictor y referencias compactas por especie.
Su tooltip separado (ratón/táctil/teclado), ES/CA/EN, explica algoritmo, SMI,
balance como entrada directa, otras entradas y ventana. Se inspeccionan las
columnas del artefacto ya cargado: no inferir estas propiedades por versión.

Segundo circuito local completado: reconstrucción/base promovidos y multiversión
verificada, 714 ajustes previstos/714 correctos/0 fallidos, lote
`operational_20260920T020702Z`. Después se reconstruyeron/recrearon HA local y
el mismo worker con los últimos tooltips; 211/114 archivos idénticos al checkout,
coordinadores intactos. Smoke final: 1690 tests, 48 omitidos, OK; navegador
ES/CA/EN y 1280/375/320 px, OK. Una predicción real local de Bellver confirmó
ese lote y `Smooth Shared–V6w`, SMI sí/balance directo no, ventana 30 días.

**Última instrucción del usuario: el precálculo lo lanzará él. NO lanzarlo desde
Codex.** Su primer intento falló antes de encolar: `desired.json` conservaba
revisión 68/esquema 1.6 y faltaba admitir esa versión al avanzar a 1.7.
Corregido en `_desired_revision_for_advance`, sin aceptar resultados antiguos.
418 pruebas dirigidas y smoke 1690/48 omitidas OK. Ambos contenedores existentes
reconstruidos/recreados; paridad 211/114 archivos OK, coordinadores intactos y
ambas colas libres. Comprobado dentro de HA que la revisión 68 puede avanzar;
el fichero real permaneció intacto hasta el reintento del usuario.
El reintento `worker_job_7YWJHNU9LAaR` terminó correctamente a las 02:55:34 UTC;
recibido y activado esquema 1.7/revisión 69, lote nuevo, 749 respuestas y
28.004.352 bytes. Recibo, identidad deseada y SHA del archivo coinciden;
SQLite íntegro. El usuario solicitó publicar tras finalizar: aceptación local
completada. HA real no se ha actualizado. Tras instalar, el usuario lanzará
la reconstrucción/entrenamiento y el precálculo de HA real, sin reutilizar los
artefactos físicos anteriores. Evidencia en `tmp/release-0.2.315` y el informe SMI-07; no repetir
entrenamientos completos para probar sólo presentación.

[Continuación de auditorías](mushrooms/SMI/continuation.md).

## Alcance y fuentes de verdad

Este contexto se ha contrastado con el checkout `81a6b0b` (HA 0.2.312) y sus
cambios documentales locales. La sección de setales recoge además el desarrollo
posterior pendiente de publicación. [Auditoría y fuentes](reports/documentation-audit-2026-09-18.md).
Código disponible, prueba anterior e instalación comunicada son evidencias
distintas: no se ha accedido a HA real ni inspeccionado contenedores para esta
revisión documental. El código no prueba el estado de un servicio en ejecución.
La release 0.2.313 y su validación local posterior se recogen debajo.

**No acceder por SSH a la RPi4 sin petición expresa, tampoco para lectura.**
La autorización del 18/09 cubrió únicamente la migración y verificación ya
terminadas. Parar, instalar y arrancar Rainmapper en HA real corresponde al
usuario. No cambiar destinos del worker, copiar semillas sobre datos privados,
limpiar archivos o iniciar entrenamiento/precálculo por mantener documentación.

## Versiones y validación

- HA del repositorio: **0.2.314**, coincidente en `rainmapper-app/config.yaml`,
  Dockerfile (LABEL/ENV) y cache-busters de ambos visores.
- Worker: **1.1.3** como valor por defecto en su Dockerfile y Compose. Versionado
  independiente de HA; una etiqueta no demuestra la imagen efectiva en ejecución.
- La publicación 0.2.312 se verificó en esta sesión: tags de versión y `latest`,
  mismo digest, AMD64/ARM64; commit `81a6b0b` enviado a `origin/inicial`.
  [Informe](reports/ha-release-0.2.312.json). No confundir ese resultado con un
  nuevo inventario remoto realizado durante esta auditoría.
- Validación de la candidata: HA local y worker reconstruidos, 202/108 archivos
  sin diferencias, smoke de 1.639 tests (48 omitidos), búsqueda real y UI móvil
  ES/CA/EN. Después solo se modificaron versión/cache-busters y documentación.
- **Usuario confirma que funciona bien en iPhone y Safari del Mac tras la
  publicación 0.2.312.** Incidencia de zoom del buscador cerrada por esa validación.
  No se ha inspeccionado remotamente la versión instalada.

## Suspensiones de modelos — publicado en 0.2.314

Nueva sección en Workers y trabajos para suspender/reactivar modelos por especie
o globalmente, con motivo persistido. Afecta a la selección de predicciones;
no elimina artefactos ni impide entrenarlos. Registro transportado al worker,
identidad de runtime/precálculo renovada y caché filtrada antes de servir IFF.
[Funcionamiento y validación](mushrooms/model-suspensions-es.md).

HA local y el único worker reconstruidos: paridad efectiva 206/109 archivos;
smoke de 1.649 tests, 48 omitidos (validación anterior; no se modificó código
ejecutable al ampliar las reglas). Siete suspensiones para rovelló solo en HA
local: HGB/KNN/SVM-V2 y HGB de ambos perfiles V3/V4. Las cuatro últimas se
guardaron mediante el formulario tras autorización. Precálculo con las tres
reglas V2 terminado/activado y mapa local/worker coincidentes en dos puntos.
La nueva cadena lanzada por el usuario terminó: lote `operational_20260919T014018Z`
instalado, 714 artefactos, siete reglas conservadas. Los 14 artefactos de los siete
modelos suspendidos existen y pasan hash. 56 combinaciones suspendidas bloqueadas;
35 selecciones en cinco puntos respetan la política (Smooth Partial V6-30).
Paridad mapa local/worker correcta en Pradell y Capolat. Precálculo
`worker_job_O7yzs0AqVMK6` completo y activado, revisión 68, SHA verificado y
ningún ganador suspendido en los resultados persistidos.

Publicación autorizada: GHCR `0.2.314` y `latest` verificados con el mismo digest
`sha256:bc4324b83141fb8719f1d18b770c5dc0db816966e5b2ce344f1a8c375c9d12bc`,
AMD64 y ARM64. [Informe de release](reports/ha-release-0.2.314.json).
Pendiente instalación por el usuario y aplicación de las siete reglas en HA real:
son configuración privada y no viajan dentro de la imagen. El único worker ya
está reconstruido con soporte, conservando coordinadores; no se publicó otro worker.
[Auditoría ampliada y límites](reports/rovello-model-sensitivity-expanded-2026-09-19.md).

## Mantenimiento de setales — publicado en 0.2.313

Implementado en `mushroom_known_sites_ui.py`, `known-sites.js` y `known-sites.css`,
con rutas privadas de workspace/detalle/observaciones en `web_server.py`.
Mapa MapLibre persistente, árbol y selección bidireccionales, ficha lateral,
altas con dibujo inmediato, buscador Photon con POI y controles de mapa.
Archivo/restauración/borrado conservan las restricciones del backend y piden
confirmación; los borradores ofrecen guardar, descartar o seguir editando.

La recuperación GIS/DEM/SoilGrids sigue disponible: modal de trabajo durante
las peticiones, propuesta GIS seleccionable antes de aplicar/guardar y errores
sin perder el borrador. No se consulta el raster por navegar entre fichas.
Las observaciones se cargan bajo demanda, con páginas de 50; el workspace omite
los informes derivados y comparte una sola colección de geometrías.

Validación local del 18/09: 349 tests dirigidos correctos; recorrido real de
navegador con alta de área/microárea, Polygon/MultiPolygon, error de guardado,
GIS aplicado y persistido, cancelación, archivo/restauración/borrado protegido,
buscador y anchura móvil. Datos originales y anillo de backups restaurados;
observaciones sin cambios. Script reproducible: `tests/known_sites_browser_check.mjs`
(requiere `--allow-local-writes`, solo HA local).

Respuesta HTML medida: 7.342.163 → aproximadamente 424.000 bytes; respuesta del servidor local
~1,51 s → ~0,025 s. No representa el tiempo de descargar/renderizar cartografía
ni una medición en RPi4. El usuario confirmó la edición de un área y una microárea y autorizó publicar.
HA local y worker reconstruidos para la release: 204/108 archivos sin diferencias,
URLs y hashes de configuración del worker conservados. Smoke de 1.641 tests
(48 omitidos) correcto. GHCR verificado para 0.2.313/latest con el mismo digest
y manifests AMD64/ARM64; [informe](reports/ha-release-0.2.313.json). Worker sigue
1.1.3 sin nueva publicación; no se repitió entrenamiento/precálculo por este cambio
de UI. Instalación/parada/arranque de HA real a cargo del usuario, pendiente de
confirmación. UI local: `http://127.0.0.1:8101/mushrooms/known-sites`.

## Mapa meteorológico y mapa de predicciones

Entradas protegidas `/protected/maplibre/index.html` y
`/protected/prediction-map/index.html`. Comparten los assets de
`rainmapper_core/viewers/maplibre-viewer`; la extensión de predicción vive en
`rainmapper_core/viewers/prediction-map` y se sirve mediante
`rainmapper-app/app/mushroom_prediction_map_ui.py`.

- Lupa entre Ajustes y 3D. Photon público consultado directamente desde el
  navegador al enviar Buscar/Intro; no hay autocomplete. Hasta 8 resultados,
  timeout 20 s, separación mínima 1 s, caché en memoria de 50 consultas.
  La posición del mapa orienta la búsqueda sin limitarla a Catalunya.
- Selección centra el mapa y crea un POI con nombre. Una nueva búsqueda válida
  retira el marcador anterior. Navegar no lanza inferencia. Campo de 16 px,
  ayuda de búsqueda y créditos Photon/OSM/OpenTopoMap/OpenFreeMap/OpenMapTiles.
- Predicción con ejecutor local o worker. La preferencia inicial es worker.
  Si el envío al worker recibe 503 `executor_unavailable` o `worker_busy`, el
  cliente intenta **una vez** en local sin cambiar la preferencia guardada.
  No es recuperación general de fallos de una consulta ya aceptada.
- «Servidor local» es el servidor que sirve ese mapa, no necesariamente el Mac.
  Inicialización fallida y excepciones de consultas locales se registran en log;
  el broker no incorpora un reintento automático de inicialización. El reinicio
  del usuario recuperó la incidencia anterior, sin diagnóstico causal concluyente.
- Ecología territorial (suelo/pH, hosts/hábitat, altitud) separada de fenología
  diaria. Compatibles en temporada aparecen en la lista; el complemento aparece
  en descartes/información insuficiente, incluidos los descartes por temporada.
- IFF expresa favorabilidad relativa, no probabilidad de encontrar setas.
  Cero, modelo ausente e inaplicabilidad son distintos. Cada ficha de Rovelló
  conserva su ID/modelo; no fusionar observaciones ni prestar modelos.
- Ausencia de suelo identificado muestra «Suelo no determinado». Exigirlo sigue
  siendo decisión de cada ficha; no introducir un veto global ni derivarlo del pH.

[Especificación central](mushrooms/prediction-map-specification-es.md) y
[arquitectura](architecture.md). La validación funcional no acredita precisión
micológica ni cobertura GIS nacional completa.

## Fichas y vigencia de modelos

El mapa consume perfiles privados actuales a través de `MapPublication` y el
lector ecológico. El aviso `pending_model_species_ids` y
`mushroom_model_state` se relaciona con cambios de observaciones;
`save_profile_form` no marca pendientes de reconstrucción. El vector rápido
`REVISION_VECTOR_KEYS` no incluye revisión de perfiles. Confirmado en código,
no una promesa de que cualquier edición requiera reentrenar. La distinción entre
filtros consultados en vivo y entradas del entrenamiento necesita mantenerse.

## Almacenamiento y migración completada

`mushroom_paths.py` resuelve rutas nuevas cuando `media_layout.organized()` valida
`/media/rainmapper/.media-layout-v1.json`. Sin marcador conserva rutas antiguas;
con journal incompleto rechaza continuar. La migración es una operación CLI
explícita, no una acción automática de instalación o arranque.

| Contenido tras migración | Ruta bajo `/media/rainmapper` |
| --- | --- |
| Fuentes geográficas canónicas y manifiestos | `geography/` |
| Modelos | `results/models/` |
| Artefactos de reconstrucción | `results/artifacts/` |
| Archivo de versiones | `results/model-archive/` |
| Precálculo activo y recibos | `results/predictor-precompute/` |
| Transferencias del worker | `transfers/worker/` |
| TAR de runtime | `cache/predictor-runtime-archives/` |

HA real: operación del 18/09 con 0.2.310, seis movimientos, 1.550 archivos
conservados y 4.942 duplicados GIS retirados solo tras hashes íntegros
(21.358.531.147 bytes lógicos, no medida de espacio físico). Datos privados,
identidad del runtime y SQLite verificados. El usuario confirmó después el mapa
con ejecutores local y worker. No repetir la operación por este documento.
[Informe](reports/ha-media-migration-2026-09-18.json) ·
[Procedimiento](mushrooms/ha-media-organization-proposal-es.md).

## Herramientas locales de investigación

**Wunderground:** `local-apps/wunderground/code/station_research.py` y `local-apps/wunderground/code/web/`,
no incluidos por el Dockerfile HA. Consultas por clic, preliminares y candidatas,
revisión Pendiente/Dudosa/Aceptada/Rechazada guardada en SQLite, filtros combinables
por fuente, relieve/norte, fondos y búsqueda de lugares. Días con lluvia válida
X/30 incluye 0 mm: mide disponibilidad, no calidad. Deduplicación por ID frente
a la red de referencia; aceptar una candidata no la añade al IDW ni hace backfill.
La base de referencia inicial es local, no el estado en vivo de HA real.
[Uso y persistencia](station-research-es.md). No asumir que el servidor esté arrancado.

Los recuentos iniciales (143 nuevas/12 priorizadas) son históricos del análisis;
las revisiones del usuario pueden cambiar. No afirmar que actualmente ninguna
esté aceptada sin consultar su SQLite. Conservar
`local-apps/wunderground/data/` y su `research.sqlite3`.

**GBIF:** visor y herramientas en `local-apps/gbif/code/`; datos en `local-apps/gbif/data/`. Snapshot, fotografías y
revisiones excluidos de Git e imagen. Cuatro estados; clave interna `approved`
para Aceptada, diferente de `accepted` en WU. Persistencia de revisión en navegador
más guardado en archivo opcional; no se ha simulado un crash físico de Chrome.
El usuario dejó pendiente revisar **observaciones GBIF**, no estaciones.
No importar ni entrenar automáticamente. [Guía](../local-apps/gbif/docs/guide.md).

## Pendientes y límites conservados

- Revisión GIS **aplazada expresamente**: tanda histórica de 488, 145 aceptados y
  343 pendientes (331 sin investigación suficiente y 12 con limitación documentada,
  no declarados irresolubles). Los 567 códigos previamente aceptados no cuentan
  como nueva revisión. Revalidar archivos antes de retomar; no se reauditan ahora.
- Conservar `tmp/soil-review-after-0.2.307/` completo, sus fuentes y auditorías.
  [Método](mushrooms/gis-soil-review-method-es.md) · [Informe](gis-review-2026-09-16.md).
  Copias GIS comparadas históricamente no prueban su consumo actual en HA/worker.
- Calidad/backfill de candidatas WU solo tras revisión y lote aprobado.
- Árboles vecinos, cobertura GEODE/MFE fuera de Catalunya y validación científica
  en puntos nuevos siguen pendientes. SoilGrids puntual no completa integración
  general por áreas ni implica geología/ecología disponible fuera de Catalunya.
- El resto de pendientes de producto/ciencia se conserva en [todo.md](todo.md).
- `docs/ui/rainmapper-geocoding-options-review.md` es un encargo/propuesta sin
  seguimiento Git al auditar; no se ha ejecutado ni convertido en decisión técnica.

## Worktree y continuidad

Al iniciar esta auditoría, HEAD y `origin/inicial` eran `81a6b0b`. Había cambios
locales documentales de confirmación Safari y el archivo personal
`mushroom-data/mushroom_observations.json`, que se preserva sin editar ni incluir
por arrastre. No había cambios ejecutables versionados pendientes.
Esta revisión añade solo documentación, sin build, publicación ni acceso remoto.

El [archivo previo a esta auditoría](reports/session-context-before-doc-audit-2026-09-18.md)
conserva el detalle de las sesiones, huellas y decisiones; es histórico, no una
fuente de estado actual. Las decisiones científicas y operativas siguen en
[decisions.md](decisions.md) y especificaciones temáticas. No inferir cambios de
código o datos a partir de los pendientes.

## todo.md antes de compactar

# TODO — actualizado 19/09/2026

Arranque suficiente: [codex-start-here](codex-start-here.md) y
[active-context](active-context.md). Esta lista no autoriza trabajos ni publicaciones.
El historial y los checklists anteriores se conservan en
[archivo documental](reports/session-context-before-close-2026-09-16.md).

## Suspensiones de modelos — 19/09/2026

- [x] Preparar para la próxima versión HA el panel de suspensiones cerrado por
  defecto: retirado `open` del elemento `details`. Publicado en 0.2.315.
- [x] Incluir ese ajuste visual en la release 0.2.315.
- [x] Preparar JSON independiente de suspensiones y exportación/importación en
  Workers. HA local reconstruido: ocho archivos ejecutables cotejados por SHA,
  formulario probado en Chrome con las mismas siete reglas y sin modificar el
  registro de generaciones. Smoke inicial: 1.660 tests, 48 omitidos. Publicado en 0.2.315.
- [x] Reconstruir HA local y worker y validar la cadena integrada antes de
  publicar 0.2.315: 714 entrenamientos correctos y precálculo activado.
  Smoke final 1690 tests, 48 omitidos; ver informe de release.
- [x] Implementar suspensión/reactivación por especie o global desde Workers y
  trabajos; persistencia y transporte al worker, filtro anterior a la caché.
  [Contrato y estado local](mushrooms/model-suspensions-es.md).
- [x] Validar precálculo y mapa local/worker con HGB/KNN/SVM-V2 suspendidos.
- [x] Ampliar a HGB de ambos perfiles V3/V4 para rovelló: siete reglas en HA local,
  guardadas mediante el formulario tras autorización.
- [x] Verificar la cadena de entrenamiento lanzada por el usuario: lote nuevo
  instalado, siete reglas conservadas, 14 artefactos suspendidos entrenados y
  verificados por SHA; 56 combinaciones excluidas y 35 selecciones válidas en
  cinco puntos. Paridad mapa local/worker correcta en dos puntos.
- [x] Verificar resultado y activación del precálculo `worker_job_O7yzs0AqVMK6`: recibo,
  SHA, siete reglas y ausencia de ganadores suspendidos.
- [x] Publicar HA 0.2.314: GHCR versión/latest, mismo digest, AMD64 y ARM64
  verificados. [Informe](reports/ha-release-0.2.314.json).
- [x] Configurar las siete suspensiones en HA real 0.2.314 mediante su formulario;
  comprobadas de nuevo por SMB el 19/09. Generaciones conservadas al aplicarlas.
- [ ] Usuario avisará tras entrenamiento/precálculo en HA real para verificar sus
  resultados; no lanzar ni repetir esos trabajos automáticamente.
- [x] Verificar las siete reglas en el snapshot de entrada del entrenamiento,
  tanto en HA local como dentro del worker. Pendiente su resultado, no confundir
  transporte correcto con validación completa de la cadena.
- [ ] Revisar científicamente los modelos cuestionados antes de reactivarlos:
  estabilidad ante trazas de lluvia, independencia de vecinos de KNN,
  calibración y respuesta temporal. Suavidad por sí sola no prueba precisión.
- [ ] Corregir y versionar de forma coherente el criterio de día lluvioso/racha
  seca en entrenamiento e inferencia; evaluar umbrales con evidencia, sin cambiar
  la semántica de artefactos existentes. KNN: comprobar independencia por ID de
  observación, no solo igualdad de atributos. [Resultados y límites](reports/rovello-model-sensitivity-expanded-2026-09-19.md).

## Pendiente del usuario — observaciones GBIF (17/09/2026)

- [ ] El usuario revisará las observaciones descargadas de GBIF en el visor local
  y les asignará Pendiente, Dudosa, Aceptada o Rechazada. [Visor y guardado](../local-apps/gbif/docs/guide.md).
- [ ] Esperar su indicación tras esa revisión para preparar la incorporación de
  las aceptadas y decidir las pruebas comparativas o zonas candidatas. Conservar
  el JSON de revisión; no importar, entrenar, generar setales ni aprobar citas
  automáticamente. No se afirma que la revisión ya esté terminada.

## Aplazado por el usuario — revisión GIS

- [ ] Retomar los **343 pendientes** de la tanda de 488: **331 sin investigación
  específica suficiente** y **12 con limitación específicamente documentada**.
  No dar los 12 por irresolubles. **No continuar ahora.**
  [Método breve](mushrooms/gis-soil-review-method-es.md) ·
  [recuento, evidencias y validación](gis-review-2026-09-16.md).
- [ ] Al retomar, revalidar hashes, cola, fuentes y ámbito por código; aceptar solo
  lo justificado, conservar registros ajenos y comprobar ambos lectores.
  Los 567 suelos aceptados anteriores no cuentan como nuevamente investigados.

## Seguimiento 18/09/2026

- [x] Corregir tamaño del campo de búsqueda a 16 px y añadir su uso a la ayuda
  ES/CA/EN. HA local reconstruido; Chrome móvil, traducciones y huellas correctos.
- [x] Revisar créditos del mapa: Photon/komoot, OSM, OpenTopoMap y OpenFreeMap/
  OpenMapTiles; panel desplazable y comprobado en HA local móvil ES/CA/EN.
- [x] Publicar 0.2.312 con corrección, ayuda y créditos: autorizada y verificada
  en GHCR, ambos tags/digest y arquitecturas. [Informe](reports/ha-release-0.2.312.json).
- [x] Usuario confirma el 18/09 que el buscador funciona bien en iPhone y Safari
  del Mac después de publicar 0.2.312. Incidencia de zoom cerrada por su
  validación en dispositivos reales.


- [x] Implementar diagnóstico de errores del ejecutor local del mapa y lectores:
  componente, traceback y stderr visible. Cinco pruebas nuevas y suite dirigida
  correcta (161 casos, 48 omitidos). Cambio en worktree posterior a 0.2.310.
- [x] Instalar/validar ese cambio en HA local y worker: ambos reconstruidos,
  paridad 202/108 archivos y dos puntos coincidentes. Suite de 1.639 tests,
  48 omitidos. 0.2.311 aceptada, publicada y verificada en GHCR.
  Reintento controlado solo propuesto.
  El reinicio de HA real por el usuario recuperó el servicio; causa inicial no
  recuperable a partir de los logs antiguos.
- [x] Visor local de investigación WU: 3D/norte, disponibilidad X/30, cuatro
  estados con guardado SQLite, búsqueda por clic con modal, promoción a candidata
  y limpieza persistente de preliminares/puntos consultados. [Uso](station-research-es.md). Sin altas operativas.
- [ ] Revisar calidad de candidatas WU del primer análisis de cobertura de Catalunya.
  Análisis inicial: 143 nuevas identificadas y 12 priorizadas por geometría.
  Son recuentos históricos; comprobar el SQLite antes de afirmar estados actuales.
  [Informe local](../local-apps/wunderground/data/README.md). Preparar
  históricos/backfill solo después de acordar el lote y aprobar estaciones.

## Próximo bloque operativo, cuando se solicite

- [x] Trasladar los visores WU y GBIF a `local-apps/{wunderground,gbif}/{code,data}`.
  SQLite WU íntegro (179 registros, 506 entradas de caché, 19 eventos); snapshots
  GBIF verificados por SHA al mover 4.359 archivos. Se conserva la URL WU y
  enlaces de compatibilidad GBIF sin duplicar fotografías. Datos excluidos de
  Git y ambas aplicaciones excluidas de las imágenes Docker.

- [x] Retirar el entorno aislado de reconstrucción de julio por autorización
  del usuario: eliminados `docker-compose.rebuild-test.yml` y
  `options.rebuild-test.json`; documentación actualizada. No había contenedor
  ni imagen etiquetada de ese entorno. HA local y worker sin cambios.
- [ ] Continuar la revisión selectiva del espacio del workspace. Los duplicados
  GIS autorizados el 19/09 ya se retiraron (véase el registro siguiente).
  [Inventario del 18/09](reports/repository-disk-audit-2026-09-18.md): 62,4 GB,
  con 15,6 GB de posibles copias GIS identificadas por ruta/tamaño y 4,5 GB
  de auditorías. No sumar estas cifras como ahorro ni borrar automáticamente.
  Antes de retirar archivos, revalidar inventario, comparar contenidos mediante
  hashes, revisar consumidores y comprobar HA local/laboratorio. Conservar
  fuentes únicas, observaciones, fotos GBIF, revisiones WU y trabajo GIS aplazado;
  separar informes y entradas únicas de derivados reproducibles. La limpieza
  restante queda pendiente de autorización expresa.
- [x] Comparar por SHA-256 las parejas de la raíz y `docker-media/rainmapper/geography`
  el 19/09: 1.432 archivos idénticos en `mushroom-GIS` (6.820.316.846 bytes) y
  2.149 en `mushroom-map-GIS` (8.801.926.945 bytes). No son hardlinks. La raíz
  también contiene 101 y 5.707 archivos, respectivamente, sin pareja en media.
  No equivale a ahorro físico garantizado en APFS. Inventario previo al borrado.
- [x] Retirar los duplicados GIS autorizados: 1.422 archivos de `mushroom-GIS`
  y 2.079 de `mushroom-map-GIS`, tras repetir SHA-256 inmediatamente antes de
  borrar cada copia raíz. Total: 15.620.730.911 bytes lógicos; aumento neto
  observado de espacio libre: 498.569.216 bytes, con otros servicios activos.
  Conservados archivos únicos, scripts, documentación y metadatos. Las copias
  canónicas en `docker-media` no se modificaron.
  Tras el borrado, lector geográfico de HA local preparado y consulta de Capolat
  correcta: municipio, terreno, árboles, vegetación, geología y ecología disponibles.
  Sin reiniciar servicios.
  [Registro](reports/local-gis-duplicate-cleanup-2026-09-19.json).
- [x] Comprobar dentro de HA local que GIS y mapa utilizan `/media/rainmapper/geography`,
  montado desde `docker-media/rainmapper/geography`. Revisar antes de consolidar
  las referencias de adquisición/auditoría que todavía usan las carpetas raíz.
- [ ] Revisar crecimiento de caché de builds: variables de versión preceden a
  instalación de dependencias en ambos Dockerfiles. La limpieza autorizada de
  caché no usada en 24 h devolvió 0 B; no se borraron imágenes ni volúmenes.
  Establecer una retención acotada y evitar reinstalar dependencias por cambios
  de versión, con validación del empaquetado antes de aplicar ajustes.
- [x] Reorganizar media en HA local y real: HA real 0.2.310, seis movimientos,
  1.550 archivos conservados; 4.942 duplicados verificados y retirados (21,36 GB
  lógicos). Datos privados y runtime intactos, SQLite correcto y lectores
  preparados tras retirada. [Informe](reports/ha-media-migration-2026-09-18.json).
- [x] Usuario confirma que el mapa de HA real funciona en local y worker después
  de la migración. Comprobaciones offline de datos, lectores y SQLite correctas.
- [x] Usuario comunica que utiliza 0.2.311 en iPhone: buscador con POI y diagnóstico de errores.
  No parar, instalar ni arrancar HA real por su cuenta.
- [x] Confirmar versión efectiva de HA real: 0.2.309 por SSH LAN el 17/09.
- [ ] Comprobar sin trabajos costosos el consumo efectivo en HA real/worker de
  los JSON GIS subidos. El mapping almacenado **coincidía byte a byte** con
  HA local en la comparación del 17/09; no volver a copiarlo por rutina. La comparación
  no acredita el runtime ni revalida el JSON de auditoría.

## Completado el 17/09/2026

- [x] Publicar HA 0.2.309 y enviar commit `0ce6de3` a `origin/inicial`.
  [Informe](reports/ha-release-0.2.309.json): HA local/worker reconstruidos,
  paridad 200/107 archivos, smoke 1.615 tests con 48 omitidos y Chrome correcto.
- [x] Incluir aplicabilidad IFF por magnitud, tooltip, suelo no determinado,
  error comprensible de referencia suelo/pH y descartes completos por fecha.
  Conservar control por especie; no exigir suelo identificado globalmente.
- [x] Comparar mapping almacenado en HA real/local, SHA y contenido idénticos.
  [Evidencia](reports/gis-mapping-ha-parity-2026-09-17.json).
- [x] GBIF: cuatro estados, autoguardado y herramientas versionadas; datos, fotos
  y revisiones personales excluidos de Git e imagen. Revisión manual pendiente.
- [x] `IFF:` del Predictor publicado en 0.2.308, instalación de esa versión
  terminada según el usuario; conservado en 0.2.309.

## Completado anteriormente (16/09/2026)

- [x] Publicar HA 0.2.307; usuario confirma instalación.
  [Evidencia de release](reports/ha-release-0.2.307.json).
- [x] Presentación IFF, traducciones, colores, fechas, compactación y ayuda del
  mapa incluidas en el trabajo de release; no confundir pruebas funcionales con
  validación científica ni emulación con iPhone físico.
- [x] Justificar y aceptar 145 códigos nuevos (95 silíceos, 32 mixtos, 18 calcáreos)
  e incorporarlos a HA local. Últimos mappings comprobados en ambos lectores del
  contenedor para los 1.055 códigos; inventario total 1.336 preservado.
- [x] Usuario comunica subida de los dos JSON a HA real; consumo remoto aún no
  verificado. No requiere entrenamiento/precálculo para el mapa puntual.
- [x] Corregir dos puntos de IFF en el Predictor local, conservando tooltip.
- [x] Limpiar GHCR/entregas obsoletas/copias locales/caché Docker autorizadas,
  conservar datos activos y Python 3.11. Medidas y límites en el informe GIS.
- [x] Documentar método, distinguir investigación insuficiente de limitación
  investigada y dejar el resto aplazado por instrucción del usuario.
- [x] Renovar documentación de continuidad y archivar contexto histórico.

## Pendientes de producto y ciencia — no reabrir automáticamente

- [ ] Recuperación de arbolado vecino: concretar criterio/radio, distancia y
  procedencia; el vecino de pH no la sustituye.
- [ ] Revisar vinosus y demás fichas con evidencia específica, sin restaurar
  rangos antiguos ni crear vetos globales; conservar ediciones del usuario.
- [ ] Contrastar compatibilidad y valores IFF con setales conocidos; auditar
  incertidumbre espacial de GIS/IDW y transferencia a puntos nuevos.
- [ ] Ampliar regresión de estilos/gestos y convivencia de modos en Safari/iPhone.
  El zoom del buscador ya está validado por el usuario en 0.2.312; eso no cubre
  toda la regresión móvil. No abrir administración local a la Wi-Fi.
- [ ] Corregir la tarjeta del worker que muestra **«En espera» durante un
  entrenamiento activo**. Diagnóstico confirmado el 18/09/2026 mediante
  `GET http://127.0.0.1:8110/health`: estado general `idle`,
  `lanes.foreground.status=idle` y `lanes.background.status=busy`, con un
  `active_job_id` en segundo plano. Es evidencia de ese instante, no del estado
  futuro del trabajo. En `rainmapper_core/mushroom_worker_service.py`, tanto
  la respuesta de salud como el heartbeat toman el estado general únicamente
  de `foreground`; `_worker_card` en `rainmapper-app/app/mushroom_workers_ui.py`
  representa `payload.status` sin considerar `lanes`.
  Mostrar «Ocupado» si cualquiera de los dos carriles está ocupado y distinguir
  la disponibilidad para consultas del mapa de la actividad de entrenamiento/
  precálculo. Revisar también la actualización automática de la tarjeta y
  preservar los estados de desconexión y dataset no disponible. No cambiar la
  planificación ni bloquear consultas por corregir el indicador. Añadir pruebas
  dirigidas para ambos libres, solo segundo plano ocupado, solo primer plano
  ocupado y ambos ocupados. **Aplazado por el usuario**; no se ha cambiado código
  ni interrumpido el entrenamiento durante el diagnóstico.
- [ ] Medir cola/transporte/render, RAM e IO en destino con límites RPi4; no
  extrapolar mediciones del Mac ni repetir trabajos caros para diagnosticar.
- [ ] Completar integración nacional GEODE/MFE, esquemas regionales e índices
  usando descargas existentes. Catalunya no acredita cobertura española completa.
- [ ] Al ampliar consumidores GIS, comprobar compatibilidad de grupos de reglas;
  los dos lectores de los mappings actuales sí se han verificado.
- [ ] Completar aceptación geográfica en máquina independiente/AMD64 antes de
  retirar originales que aún se necesiten. Revalidar estado previo, sin rehacer
  la consolidación ya acreditada por los informes del 15/09.
- [ ] Ampliación separada: superficie coloreada por zona visible; no precalcular
  todos los puntos del territorio por inferencia del informe puntual.

## SoilGrids y enriquecimiento general

- [ ] Completar lector común/agregación por áreas, deltas y pruebas de recursos
  al retomar integración general; medir y deduplicar antes de transportar.
- [ ] Separar mostrar pH/profundidad/incertidumbre, migrar almacenamiento y cambiar
  variables de modelos. Preservar anotaciones y comprobar contratos antes de migrar.
- [ ] Revisar rangos provisionales ante nueva evidencia; no generalizar aereus
  a 7,5 ni inventar pH del suelo desde litología.
- [ ] Francia: ecología/geología y normalización forestal pendientes;
  DEM/SoilGrids puntuales no acreditan cobertura ecológica.

## Predictor y operación — pendientes conservados

- [ ] Aplicabilidad multiespecie (Rovelló / Els Ports / 07/09/2026), sin tolerancia
  global inventada; distinguir modelo ausente de modelo vetado.
- [ ] Catálogo de especies posibles por área y evaluador persistido hold-out que
  sustituya Historial; mensajes separados de entrenamiento/precálculo/corrupción.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando los hold-outs externos
  contengan ambas clases; no reabrir contador de días secos sin evidencia nueva.
- [ ] CLI worker por asociación; medir transferencia/hash/escritura/promoción
  antes de cualquier diseño de streaming.
- [ ] Runner externo/AWS/servidor doméstico y Python 3.14: futuros, no migrar ahora.
- [ ] Revalidar incidencia meteorológica Barcelona/Erinya y controles del runner
  antes de actuar: [informe histórico](reports/weather-coordinate-conflict-2026-09-13.json).
- [ ] Microáreas francesas y Meteo-France frente a Wunderground: bloque separado.

No relanzar reconstrucción, entrenamiento o precálculo para un cierre documental.
No borrar auditorías ni el directorio de trabajo de la revisión aplazada.
