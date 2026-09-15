# Traspaso antes de compactación — Mapa de predicción

Preparado el 12/09/2026 a petición expresa del usuario. Es contexto operativo,
no una especificación alternativa. Referencia de diseño:
[prediction-map-specification-es.md](../mushrooms/prediction-map-specification-es.md).
Leer completos `docs/codex-start-here.md` y `docs/active-context.md` al retomar.

## Punto exacto para continuar

El usuario acaba de reiterar este orden; no volver a proponer comparar
ejecutores o desplegar el canal remoto como siguiente tarea:

1. **Completar el terreno y las entradas necesarias para predecir.**
2. **Integrar y validar la predicción por especies, inicialmente en local.**
3. **Con ese mismo cálculo funcionando, comparar local y worker**, incluyendo
   transporte y preparación. Medir solo el informe no decide el ejecutor.

Reutilizar el **motor de predicción existente**, un único código Python
compartido entre HA y worker. El trabajo nuevo es adaptar las entradas por
coordenada y la respuesta multiespecie. No duplicar fórmulas, selección ni motor
en otro Python o en JavaScript. No está demostrada todavía la aplicabilidad de
los modelos por área a cualquier coordenada; validarla antes de mostrar cifras
como predicción real. No crear áreas persistentes por cada clic.

Revisión inicial ya realizada: `PredictorService.execute()` en
`rainmapper_core/mushroom_predictor_service.py:708` normaliza una petición que
incluye especie/área/fecha. `execute_interactive_prediction()` en
`rainmapper_core/mushroom_worker_service.py:956` llama a ese mismo servicio.
Próximo trabajo útil: trazar las entradas y restricciones de ese motor, contrastar
qué puede obtenerse para un punto con los lectores disponibles, documentar las
carencias concretas y preparar el adaptador compartido. No sustituir este paso
por inventariar otra vez todos los mapas o por repetir auditorías nacionales.

## Decisiones cerradas de la conversación reciente

- «Local» significa **servidor del mapa**: ahora el proceso de prueba del Mac;
  en HA, su servidor/RPi4. No significa dispositivo del navegador.
- El usuario preguntó por ejecutar predicción en navegador, pero después
  confirmó expresamente **HA o worker, por ahora no navegador**. No tratar
  aquella pregunta como autorización para otra arquitectura.
- El navegador sí calcula el IDW visual y sus valores al tocar el mapa,
  heatmap, filtros y lecturas de relieve de teselas. La explicación previa de
  que solo dibujaba era incompleta. El histórico IDW del popup nuevo se calcula
  en Python desde registros diarios; no usar la capa visual como entrada
  científica sin validar su semántica.
- Conservar MapLibre existente, nueva ruta y extensión opcional. El mapa
  meteorológico debe mantener su comportamiento. Estaciones: clic y hover
  meteorológicos también con Predicción activada. Predicción: clic fuera de
  estaciones, modal de cálculo y popup anclado; horizonte máximo siete días.
- **Sin autenticación real nueva en la vista previa**, por petición explícita.
  Usuario ficticio, sin crear usuarios ni dispositivos en HA. No añadir
  infraestructura temporal al código de producción.
- Guardado de parámetros: seguir el mecanismo de los demás parámetros, por
  dispositivo autenticado del usuario en `devices.json`, no preferencia global
  de cuenta. La elección de Predicción se guarda al cerrar el panel con cambios.
- El usuario confirmó que ya funciona el guardado, incluida la vista por defecto.
- Francia: vegetación/ecología aplazadas; geología y municipio francés siguen
  pendientes. No bloquear todo el visor por el nombre municipal ausente.

## Implementado y límite de lo que demuestra

- Visor de prueba con municipio español opcional, altitud, pH por profundidad
  y meteorología observada reales. Selector de histórico 7/15/30/60 días y
  viento de estación identificada si hay datos. **Especies/curvas simuladas**.
- Grupo Predicción: `Servidor local / Worker`, inicialmente local, sin fallback
  automático; tiempos de consulta/cálculo en el popup.
- `mushroom_map_execution.py`: lectores residentes comunes; `mushroom_map_queries.py`:
  broker efímero limitado; `mushroom_map_worker.py`: canal saliente de informes.
  Contrato y pruebas aisladas existentes. **Worker instalado no activado ni
  validado con este código**; en la vista previa elegir worker da indisponibilidad.
- Integración opcional mediante `RAINMAPPER_PREDICTION_MAP_CONFIG`, todavía
  pendiente en contenedores. Dockerfiles preparados, imágenes sin construir
  para esta entrega. No confundir tests de transporte con aceptación Docker.
- Guardado nuevo: la extensión añade `prediction_execution` al payload de
  `currentDeviceSettings()`; el backend valida local/worker y conserva el campo
  si el visor meteorológico guarda otros ajustes sin enviarlo. El antiguo
  `localStorage` solo se lee si no existe preferencia en servidor.
- Solo el servidor de pruebas (`tests/prediction_map_browser_check.mjs`) simula
  `/auth/device-settings` con un JSON de ajustes en el directorio temporal:
  `rainmapper-prediction-map-preview-settings.json`. No es un registro de
  dispositivos ni el archivo real de HA. Al abandonar la vista previa deja de
  usarse; no necesita migración. No ampliar este mecanismo provisional.

## Entorno y verificación

Vista previa: `http://127.0.0.1:65517/protected/prediction-map/index.html`.
`lsof -nP -iTCP:65517 -sTCP:LISTEN` confirmó al preparar este traspaso un proceso
Node PID 52889. PID/estado son una observación puntual: revalidar antes de actuar.
La última sesión de ejecución de la vista previa es 99892. No necesita reinicio
por compactar o por editar documentación.

Lectores geográficos con `/opt/homebrew/bin/python3` (GDAL), meteorología con
`.venv/bin/python` (PyArrow). Datos locales existentes: índice
`mushroom-map-GIS/terrain-index/preview-2026-09-12.sqlite`, raíces
`mushroom-map-GIS/soilgrids-shared`, `mushroom-map-GIS/ign-mdt25`, `mushroom-GIS`,
municipios `mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg`,
meteorología `docker-data/Data` y `docker-data/stations.txt`.

Última validación del cambio de persistencia: **16 pruebas Python dirigidas
correctas** (cuatro de ajustes/dispositivos y las de `test_mushroom_prediction_map`)
y navegador correcto, incluyendo guardado de la vista, restauración al recargar,
elección de ejecución y conservación al guardar desde el mapa meteorológico.
Capturas de esa ejecución en el directorio temporal
`prediction-map-browser-pCW4rB`. `git diff --check` se ejecuta al cerrar este
traspaso. Son resultados históricos, no una orden de repetirlos sin cambios.

## Conservación y forma de trabajar

- Hay numerosos cambios y archivos sin seguimiento; no se han hecho commits
  de estas entregas. `mushroom-data/mushroom_observations.json` aparece modificado:
  son cambios del usuario; no restaurar, editar ni incluir indiscriminadamente.
- No tocar datos, observaciones, caché antigua ni URLs de coordinadores.
  No repetir descargas/auditorías SoilGrids: terminadas, huecos aceptados.
- No lanzar entrenamiento, precálculo, reconstrucciones, builds ni publicaciones
  por el mero hecho de retomar. HA real permanece fuera de estas pruebas.
- Dar avances breves al menos cada minuto y responder preguntas sin abandonar
  la tarea. Distinguir preguntas de decisiones: el usuario lo ha corregido.
- MCP primero para descubrimiento de código. Su índice ha dado símbolos o
  líneas desactualizados; contrastar con el archivo antes de afirmar estado.

Este traspaso no afirma que la compactación ya se haya producido ni cambia
el alcance autorizado: dejar preparado el contexto y continuar por las entradas
geográficas del motor existente cuando se retome el trabajo.
