# Mapa de HA real: asociación del worker

El usuario notificó cálculo local correcto (6,76 s) y worker no disponible,
aunque Workers y trabajos mostraba M1 Personal en espera.

Causa comprobada en `/point-config/worker.json` del contenedor: el override
local solo seleccionaba `coordinator_fde2e9b1c6c1f5b2` (HA local). La función
`mushroom_map_worker.start` crea ejecutores únicamente para las asociaciones
seleccionadas. El heartbeat general seguía funcionando para HA real.

Corrección de configuración, sin cambiar código ni imagen:

- Copia previa en `backups/map-worker-real-ha-20260916/worker-before.json`.
- Añadida asociación `primary` a `docker-data/prediction-map/worker.json`,
  conservando la asociación local y sus mismas opciones de caché privada/geográfica.
- Reiniciado únicamente `rainmapper-worker`, tras comprobar `foreground` y
  `background` en `idle`, sin trabajos activos, en `/health` (puerto interno 8098).
- URLs y archivos de configuración de coordinadores intactos antes/después:
  primary `http://100.111.77.48:8100` y local `http://rainmapper-ha-ui:8100`.
  SHA256 de coordinator.json:
  `5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10`;
  additional-coordinators.json:
  `22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0`.

Verificación efectiva mediante los informes `last-sync.json` del worker:

- Geografía primary: 3510 archivos reutilizados, 0 archivos descargados,
  0 bytes de datos transferidos, 0 bytes hasheados; manifiesto 807785 bytes.
- Snapshot privado primary: 790 archivos reutilizados, 1 descargado,
  31509 bytes de datos transferidos, 269784 bytes de metadatos.
  La verificación inicial en el worker registra 791 archivos hasheados.
- Intercambio autenticado `action=busy` con
  `/api/mushrooms/workers/map-queries` de HA real: HTTP 200; las huellas
  privadas y geográficas listas coinciden con las exigidas por HA.
  Esta comprobación no reclama trabajos ni calcula predicciones.

Confirmación posterior del usuario mediante captura: consulta en HA real por
Worker, 1,88 s totales y 0,85 s de cálculo, con probabilidades y gráfica semanal.
No se ha instalado, reiniciado ni modificado código en HA real.
