# Contexto activo — cierre del 07/11/2026

Leer con [codex-start-here.md](codex-start-here.md); [todo.md](todo.md) sólo para
ampliar pendientes. La corrección meteorológica está entregada. No hay una nueva
release ni un trabajo operativo encargado para la siguiente sesión.

## Estado operativo y evidencia

- **HA 0.2.341 instalada y funcionando**, confirmado por el usuario el 07/11:
  «ya esta instalada y ha funcionado». No se inspeccionó remotamente HA real
  ni se recibió su log completo; los tiempos y recuentos siguientes son locales.
- Release `49c4c025`; confirmación documentada en `bcd6f126`. Ambos estaban
  publicados en `origin/inicial` antes de este cierre documental. La rama
  principal es **`inicial`**, no `main`; `origin` es el remoto.
- Publicación comprobada: `0.2.341` y `latest`, amd64/arm64, digest
  `sha256:5097c0c05cb5a330d99065d10ad5efef64b67378e71a3bf7a0b77edf64536898`.
  [Informe y recibo de release](reports/release-ha-0.2.341-2026-11-07.md).
- HA local: `rainmapper-local-rainmapper-ha-ui-1`,
  [panel](http://127.0.0.1:8101/) y
  [mapa](http://127.0.0.1:8101/protected/maplibre/index.html).
  `docker ps` confirma el contenedor en ejecución al cerrar; `docker inspect`
  confirma la imagen `ed414fec20d49dc90f80ba2707ef7a922e7808119d3a6d282ab37be1fafe8a3b`.
  La etiqueta visible `local-ha-ui` no representa una versión HA distinta.
- Configuración local guardada: `max_threads: 1`, agenda desactivada
  (`rainmapper-local/options.local-ha-ui.json`). HA real usa 1 según el usuario;
  el **default para nuevas instalaciones** de `rainmapper-app/config.yaml` sigue
  siendo 3. No cambiar ni confundir esos tres ámbitos.
- Worker `rainmapper-worker:1.1.6` y MCP separado `rainmapper-mcp:local` figuran
  ejecutándose y saludables en `docker ps`; no se reiniciaron ni modificaron.
  HA local usa el compose base, sin extensión MCP. Antes de cualquier operación
  futura del worker, leer y conservar sus coordinadores persistidos.

## Qué está resuelto

- Protección común de ubicaciones para las cuatro fuentes: un salto **>1 km**
  conserva la referencia y abre excepción sin abortar descarga/archivo. Sólo
  metadata original que regrese al margen permite autocuración; un CSV cacheado
  o pendiente corregido no acredita recuperación. Un traslado estable exige
  aceptación administrativa, aplicada al comienzo del siguiente runner.
- Revisión desde MapLibre: borde ámbar, buscador/lista por fuente, ambas posiciones
  con marcadores precisos y aceptación con revisión de propuesta. Botón junto
  al título sin otra fila; botón/lista ocultos hasta 640 px. Resumen agrupado
  al final del log. [Contrato](weather-coordinate-protection-es.md).
- AEMET conserva ubicación y otros sensores aunque falte lluvia horaria. Una
  consulta conjunta al inventario **oficial OpenData**, sólo cuando faltan
  ubicaciones, completa el catálogo persistido. No repite esas completaciones
  si siguen válidas. El mensaje «22 locations completed; 0 unresolved» describía
  fichas completadas, no 22 estaciones necesariamente nuevas ni llamadas Google.
- Continúa el refresco AEMET de los últimos 30 días en cada runner: diarios
  oficiales publicados sustituyen valores provisionales horarios, incluso días
  completos y correcciones a la baja. Se actualiza el histórico Parquet. No hay
  scraper AEMET ni una espera artificial de seis horas.
- Corregidas regresiones observadas: tipos geográficos mezclados en Parquet,
  comparación texto/número y redondeo de coordenadas Meteoclimatic que repetían
  enriquecimientos Google; concatenación Wunderground y fecha ausente GeoJSON.
  Las pruebas recorren agregación, catálogo, captura, archivo y segunda pasada.

## Validación que cierra este trabajo

Smoke del código funcional final: **2.194 tests, 55 omitidos, exit 0**. Runner
local del usuario **22:48:34–22:51:25**, **2 min 51 s**, exit 0, cuatro fuentes
`OK`, siete GeoJSON y sin avisos de Pandas. AEMET: 12,767 s, ninguna consulta
necesaria al inventario, 891 fichas de catálogo; las 17 ubicaciones investigadas
coincidían en CSV, Parquet activo y mapa, sin excepciones AEMET.
Tras el bump mecánico, imagen local reconstruida/recreada y 15 archivos efectivos
comprobados. No se cambió código después de publicar; este cierre es documental.
[Mediciones, regresiones y límites](reports/weather-coordinates-local-2026-11-04.md).

## Próximos pasos y riesgos

1. **Si se retoma Wunderground:** contrastar lecturas y fallos con datos actuales
   antes de cambiar código. El último runner local conservaba 106 respuestas
   antiguas, 102 recuperaciones por otra compresión y fallos de `IBAG57`,
   `IFUENT4` e `IMONTF44`. `OK` global no significa actualidad de cada estación.
   La muestra directa anterior confirmó retraso/ausencia en la propia API;
   no prueba su causa ni una incidencia global. [Evidencia](reports/wunderground-api-check-2026-11-07.md).
2. **Roda de Ter** (`ESCAT0800000008510E`): última excepción local comprobada;
   aceptada 41.99/2.32, recibida 49.99/2.32 (889,561 km). Conservar la aceptada
   hasta recuperación original o decisión del usuario. No aceptar el traslado
   por persistencia, ni trasladar este estado local a HA real sin comprobarlo.
3. Meteocat/XEMA: el usuario prefirió esperar ante el retraso observado. Si se
   retoma, consultar API y ventanas efectivas; no se acredita aquí una incidencia
   actual de Socrata ni se amplía configuración automáticamente.
4. **LLM local aparcado** en `feature/local-llm` (`c20d3c6d`), base HA 0.2.338,
   conservado localmente, sin push. No fusionarlo para obtener los arreglos
   meteorológicos. Reconciliar y validar sólo cuando se retome expresamente.
5. Otros bloques aplazados están en TODO: evidencia de utilidad de predicciones,
   trabajo huérfano al perder worker, pruebas GIS/GBIF y auditoría de disco.
   Selección/comparación A/B/C/D, K configurable y especies configurables ya
   están implementadas: no reiniciar el diseño antiguo del 04/10.

## Rutas y precauciones para continuar

- Un único checkout: `/Users/carlosginebrosa/Developer/RainmapperHA` en `inicial`.
  No recrear worktrees permanentes ni mezclar LLM. [Mapa](repository-branches.md).
- Los dos snapshots de observaciones están **autorizados y versionados**:
  `mushroom-data/mushroom_observations.json` (441) y
  `mushroom_observations.json` (520). No fusionarlos ni tratarlos como basura.
  Modelos, credenciales, runtime y datos ignorados se conservan.
- Meteorología local: `docker-data/Data/`. Resolver el histórico mediante
  `weather_history_dataset.resolve_weather_generation` y
  `Data/weather-history/CURRENT.json`. El catálogo raíz legacy
  `Data/weather_stations_catalog.parquet` puede estar desfasado. CSV vivo,
  histórico particionado y GeoJSON publicado son capas distintas; el visor
  consume GeoJSON, no el CSV. No deducir cobertura histórica del contador vivo.
- Código relevante: `weather_coordinates.py`, `weather_history_capture.py`,
  `weather_history_writer.py`, `weather_history_archive.py`, `create_aemet.py`,
  `aemet_station_inventory.py`, `rainmapper.py`, `geojson.py` bajo
  `rainmapper_core/`; UI en `viewers/maplibre-viewer/`, servidor en
  `rainmapper-app/app/web_server.py`. Contratos: `rainmapper-app/DOCS.md` y
  [histórico particionado](weather-history-partitioned-implementation-spec-es.md).
- No SSH ni cambios HA real sin encargo específico. El usuario lanza runners,
  entrenamiento y precálculo. No alterar destino del worker. Pruebas pagadas
  Google acotadas a pocas estaciones, nunca un enriquecimiento masivo diagnóstico.
- Borrar sólo temporales propios identificados al acabar; no barrer `tmp/` ni
  datos/evidencia preservados. No ejecutar la antigua reparación
  `tmp/meteocat-repair-20260926/deploy_csv_decimal_fix.py` sobre datos nuevos.

El contexto acumulado y el TODO anteriores quedan en el
[archivo de este cierre](reports/session-context-before-close-2026-11-07.md).
Son evidencia histórica, no instrucciones vigentes. Sólo abrir anexos según
la siguiente tarea; leer este relevo no autoriza ejecutar los pendientes.
