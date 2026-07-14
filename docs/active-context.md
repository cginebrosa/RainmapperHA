# Active Context

Contexto operativo actual para continuar RainmapperHA sin cargar el historico.
Este documento es una ventana de trabajo: los detalles antiguos viven en
`docs/project-archive.md`, `docs/decisions.md` y los documentos tematicos.

## Estado del repositorio

- Ruta unica de trabajo: `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Ultimo release HA publicado: `0.2.203`.
- Commit release: `18fdc49 Release Home Assistant 0.2.203`.
- Imagen: `ghcr.io/cginebrosa/rainmapperha:0.2.203` y `latest`.
- Digest multi-arch: `sha256:67881adedbc8445c9dc7af03c3bb4fcc2b81f6ee17cb35ed043fe371ddb1fc56`.
- El usuario valido `0.2.199` en HA el 2026-07-11: MapLibre protegido funciona
  y el popup largo muestra `Pluja` en `Valores IDW`.
- GitHub sigue abierto/publico por decision explicita; no cerrarlo.
- `0.2.201` incorporo importacion de imagen/video, normalizacion de video,
  posters JPEG y fallback de altitud DEM. `0.2.202` corrige la entrega parcial
  de MP4 necesaria para Safari dentro del ingress de HA.
- No mezclar datos reales de `docker-data/` en Git.

## Foco inmediato

1. Instalar/probar `0.2.203` en Home Assistant y confirmar que el icono de
   maximizar abre las fotos a pantalla fisica completa y que `Esc` devuelve al
   mismo modal. Probar tambien el visor grande con zoom en una pestana nueva.
2. Confirmar que el MP4 asociado se reproduce, permite desplazamiento temporal
   y mantiene poster/metadata en Safari mediante ingress. Si falla, inspeccionar
   primero `HEAD`/`Range` y las respuestas `200`/`206`; no recomprimir el video.
3. Confirmar en HA que la importacion de imagen/video, el fallback DEM y los
   modales de observaciones siguen funcionando con los datos vivos existentes.
4. Tras esa validacion, retomar el pipeline ML experimental empezando por la
   especie con mas observaciones utiles. El plan vigente esta en
   `docs/mushrooms/mushroom-ml-training-plan-es.md`.

GHCR y backfill dejan de ser el foco inmediato. Siguen pendientes una posible
limpieza conservadora y pruebas mensuales cortas, pero no deben interrumpir la
estabilizacion actual de setales/observaciones salvo peticion del usuario.

## Estado funcional de setales

- Existe un store separado de catalogos:
  `mushroom-data/mushroom_known_sites.json`; en runtime local la copia viva es
  `docker-data/mushroom-data/mushroom_known_sites.json`.
- `rainmapper_core/mushroom_known_sites.py` gestiona areas y microareas,
  geometria, derivados, backups, referencias, archivado, restauracion y borrado.
- La WebUI `/mushrooms/known-sites` vive en
  `rainmapper-app/app/mushroom_known_sites_ui.py`.
- Areas y microareas tienen poligonos propios. MapLibre muestra Satellite+ por
  defecto, Topografico e Hybrid, terreno 3D, selector de capas y brujula.
- La UI permite dibujar/editar poligonos, recuperar propuestas GIS/DEM y
  compararlas antes de aplicarlas al formulario. Aplicar una propuesta no debe
  persistir nada hasta pulsar `Guardar`.
- Hay proteccion de cambios sin guardar al cambiar de setal, actualizar, volver
  o navegar a otra pantalla.
- Areas y microareas archivadas se muestran en el mismo arbol. Se pueden
  restaurar o borrar definitivamente; no se pueden archivar ni borrar si tienen
  observaciones vinculadas. Las areas tampoco pueden eliminarse si contienen
  microareas que impidan la operacion.
- El arbol permite colapsar/desplegar cada area y todas a la vez. Arbol y panel
  de detalle tienen scroll interno para mantener visibles las acciones.
- Los contadores de observaciones abren el modal reutilizable de observaciones,
  conservando la pila de navegacion y el punto exacto de retorno.

## Estado funcional de observaciones

- Cada observacion puede referenciar opcionalmente `micro_area_id`; `area_id` se
  resuelve desde el store y no se duplica en la observacion.
- El mapa de una observacion reutiliza el MapLibre de setales y muestra todas
  las areas/microareas visibles. Permite seleccionar/asignar una microarea,
  crear o editar areas y microareas sobre la marcha y volver al formulario sin
  perder su borrador.
- En modo edicion geometrica se suprimen popups de areas/microareas para no
  interceptar los clics de TerraDraw. Fuera de edicion, un unico popup combina
  observacion, area y microarea segun lo que exista bajo el punto.
- El mapa puede seleccionar nuevas coordenadas. Mantiene el punto actual y el
  candidato diferenciados, consulta altitud DEM, muestra coordenadas/altitud y
  exige confirmacion antes de actualizar la observacion.
- La seleccion manual usa los IDs catalogados existentes para origen de
  ubicacion/altitud; no volver a introducir IDs inventados como `manual_map`.
- El boton `Mapa` del formulario usa las coordenadas actuales del borrador,
  incluso al crear o duplicar una observacion aun no guardada. Al cerrar vuelve
  al mismo formulario; desde una lista vuelve a la seleccion, orden y posicion
  anteriores.
- El buscador generico de observaciones serializa el registro completo y puede
  encontrar cualquier valor presente en el JSON, ademas de labels visibles.
- La altitud acepta enteros. Se conserva precision completa en JSON/enlaces y
  se limita solo la presentacion de coordenadas donde corresponde.
- Contrato actual de media: una sola imagen o video por observacion. La UI permite
  desasociar o desasociar y borrar con confirmacion irreversible; solo ofrece
  borrar si el fichero no esta referenciado por otra observacion.
- Al sustituir una foto, el preview EXIF compara imagen existente y nueva,
  muestra datos y mapa de la seleccion, y exige decidir si se conserva o se
  borra el fichero anterior. La imagen nueva no se aplica mientras este
  seleccionada la antigua.
- El preview EXIF usa MapLibre y muestra areas/microareas visibles. Debe seguir
  devolviendo la microarea elegida al formulario, sin guardar la observacion
  hasta pulsar `Guardar observacion`.
- Los videos MOV/MP4 y formatos habituales se leen con ExifTool y se convierten
  con FFmpeg a MP4/H.264, maximo 480p y 30 segundos. Se conservan fecha/hora,
  GPS y altitud util en el MP4 y en `capture_metadata`; el original no se
  guarda. El preview y el detalle usan un poster JPEG generado desde el video.
  Si el archivo tiene coordenadas pero no altitud util, el preview consulta el
  DEM, muestra `Origen DEM` y aplica `altitude.source: dem`. Limites: 100 MB por
  archivo y 500 MB por lote.
- Tras probar `0.2.201` en HA se detecto que Safari dentro del ingress mostraba
  el MP4 pero no podia reproducirlo. `0.2.202` sirve media con rangos
  HTTP (`206`, `Content-Range`, `Accept-Ranges`), admite `HEAD` y declara un
  `source video/mp4` con poster. Validado localmente y publicado; pendiente de
  prueba real en HA.

## Ultimo cambio publicado

`0.2.203` anade pantalla completa real al visor de fotos, con retorno mediante
`Esc`, y sustituye las nuevas acciones de texto por iconos superpuestos. Incluye
un visor grande en pestana nueva con zoom, tamano real y ajuste a ventana. La
correccion de rangos HTTP/`HEAD` para MP4 de `0.2.202` se mantiene; ambas quedan
pendientes de confirmacion final en HA/Safari mediante ingress.

## Predictor y modelo aprendido

- `mushroom_model_v0.json` sigue siendo una salida descriptiva/auditable; no es
  un estimador ML y no escribe perfiles.
- La propuesta ML se centra primero en una especie con suficientes datos y
  requiere episodios por setal/fecha, series meteorologicas diarias, features
  de acumulacion y variabilidad, baseline sencillo y validacion agrupada sin
  fuga.
- No fabricar negativos ni inventar ventanas, umbrales o pesos. Hacen falta mas
  observaciones, especialmente ausencias reales en setales visitados.
- Areas y microareas son entidades predictivas propias. La primera fase
  predecira solo sobre setales conocidos; descubrir nuevos setales queda para
  una fase posterior.
- La bibliografia por especie vive en
  `docs/mushrooms/literature/prediction/` y debe informar hipotesis, no fijar
  automaticamente parametros numericos sin evidencia.

## Fuente de verdad y runtime

- Datos de setas local: `docker-data/mushroom-data/`.
- Equivalente HA: `/share/rainmapper/mushroom-data/`.
- GIS/DEM pesado en HA: `/media/rainmapper/mushroom-GIS/`.
- Fotos y videos: `mushroom-data/media/observation-photos/` y
  `mushroom-data/media/observation-videos/` dentro del runtime; son datos
  privados persistentes y no se versionan.
- Resolver canonico: `rainmapper_core/mushroom_paths.py`.
- UI local: `http://127.0.0.1:8101`, servicio Compose `rainmapper-ha-ui`.
- Estado al cierre: repo limpio y release remota publicada. La UI local estaba
  disponible durante la validacion; comprobar su estado antes de asumir que el
  contenedor sigue activo en una nueva sesion.
- Usar siempre `.venv/bin/python` (Python 3.11), igual que contenedor y HA. No
  usar el Python local del sistema. La migracion a Python 3.14 es una tarea
  futura separada, no parte de estos cambios.

## Validacion al cierre

- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: 230 tests OK.
- JavaScript embebido extraido del HTML: `node --check` OK.
- Ruta de media local comprobada con `HEAD` y rango `bytes=0-1023`: `200`/`206`,
  longitud y `Content-Range` correctos.
- Validador de datos: 0 errores y 11 warnings conocidos.
- Imagen remota `0.2.203`/`latest` verificada para amd64/arm64; Python 3.11.15,
  FFmpeg 7.1.5, ExifTool 13.25 y version runtime correctos. Tamano comprimido:
  478,2 MB arm64 y 497,3 MB amd64. Pendiente prueba HA real.

## Riesgos y dudas

- Safari/ingress puede imponer comportamiento adicional de proxy o cache no
  reproducible localmente; la prueba real de `0.2.203` es el riesgo inmediato.
- El fullscreen generico de imagen depende de que Safari/ingress permita la API
  Fullscreen; el visor grande en pestana nueva queda como alternativa con zoom.
- La UI es HTML/CSS/JS server-rendered concentrada principalmente en
  `web_server.py`; aunque las pantallas grandes estan separadas, el riesgo de
  regresion entre modales compartidos sigue siendo alto.
- El contrato sigue siendo una sola imagen o video por observacion; no asumir
  soporte de galeria ni varios adjuntos.
- Hay datos vivos y backups bajo `docker-data/mushroom-data/`; no borrarlos ni
  reemplazarlos durante tests.
- No asumir que propuestas GIS/DEM equivalen a observacion de campo: son datos
  propios del area/microarea y deben conservar procedencia.
- No limpiar GHCR sin conservar version activa, `latest`, rollback inmediato y
  manifests/attestations auxiliares multi-arch.

## Archivos relevantes inmediatos

- `rainmapper-app/app/mushroom_profiles_ui.py`: observaciones, EXIF, mapas y
  modal compartido de listas/evidencia.
- `rainmapper-app/app/mushroom_known_sites_ui.py`: mantenimiento de setales.
- `rainmapper-app/app/web_server.py`: estilos, JavaScript, rutas y POST.
- `tests/test_web_server_auth.py`: cobertura de `HEAD`, rangos HTTP y fuente MP4.
- `rainmapper-app/Dockerfile`: FFmpeg y ExifTool son dependencias del sistema;
  no deben trasladarse a `requirements.txt`.
- `rainmapper_core/mushroom_known_sites.py`: dominio/persistencia de setales.
- `rainmapper_core/mushroom_gis_lab.py`: propuestas GIS/DEM.
- `mushroom-data/mushroom_known_sites.json`: plantilla/store versionado.
- `mushroom-data/mushroom_labels.json`: labels ES/EN/CA.
- `tests/test_mushroom_known_sites.py` y `tests/test_web_server_auth.py`.
- `docs/mushrooms/mushroom-ml-training-plan-es.md`.
- `docs/mushrooms/mushroom-observations-schema-es.md`.
