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
