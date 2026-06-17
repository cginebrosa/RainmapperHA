# TODO

## Proximo paso recomendado
Validar en movil real el visor MapLibre completo: cambio de capa, cambio de periodo conservando vista, bounds libres, popup scrollable y usabilidad frente a Leaflet. Ajustar solo lo que falle en esa validacion.

## Prioridad alta
- [ ] Corregir inconsistencia de version en la app HA
  - Contexto: `rainmapper-app/config.yaml` indica `0.2.41`, pero `rainmapper-app/Dockerfile` parece conservar labels/env `0.2.4`.
  - Ficheros relacionados: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: version alineada en metadata HA, labels Docker y changelog.
  - Riesgo si no se hace: updates o diagnostico de version confusos en Home Assistant.

- [ ] Validar MapLibre en iPhone tras los ultimos ajustes
  - Contexto: MapLibre es experimental y se esta comparando con Leaflet.
  - Ficheros relacionados: `maplibre-viewer/`, `rainmapper-app/app/maplibre-viewer/`.
  - Criterio de aceptacion: cambio de capa mantiene estaciones, cambio de periodo conserva vista, popup es usable y no desplaza/molesta.
  - Riesgo si no se hace: publicar un visor aparentemente mejor pero peor en movil.

- [ ] Mantener sincronizadas raiz y app HA
  - Contexto: hay copias de scripts y visores en raiz y dentro de `rainmapper-app/app`.
  - Ficheros relacionados: `Rainmapper.py`, `Rainmapper_Client.py`, `tomap_to_geojson.py`, `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/app/`.
  - Criterio de aceptacion: despues de cada cambio funcional, raiz y app contienen la misma version necesaria.
  - Riesgo si no se hace: Docker local funciona pero HA no, o al reves.

- [ ] Proteger el historico CSV antes de cambios de pandas
  - Contexto: `Data/*_incremental.csv` es el valor principal del proyecto.
  - Ficheros relacionados: `Rainmapper.py`, `Data/`, `/share/rainmapper/Data`.
  - Criterio de aceptacion: backup o prueba en directorio temporal antes de cambios que escriban historicos.
  - Riesgo si no se hace: perdida o corrupcion de datos historicos.

## Prioridad media
- [ ] Decidir visor principal
  - Contexto: conviven Bokeh, Leaflet y MapLibre.
  - Ficheros relacionados: `Rainmapper_Client.py`, `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: definir si Bokeh queda como legacy, si Leaflet sigue activo y si MapLibre pasa a principal.
  - Riesgo si no se hace: complejidad creciente y triple mantenimiento.

- [ ] Planificar retirada de `/local/rainmapper-mobile`
  - Contexto: ruta legacy mantenida por compatibilidad tras renombrar Leaflet viewer.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper-app/DOCS.md`, `README.md`.
  - Criterio de aceptacion: fecha/version de retirada o decision de mantener indefinidamente.
  - Riesgo si no se hace: rutas duplicadas y confusion de usuarios.

- [ ] Mejorar observabilidad de Wunderground
  - Contexto: Wunderground es el cuello de botella; ya existe `metricas_wunderground.csv`.
  - Ficheros relacionados: `Rainmapper.py`, `Data/metricas_wunderground.csv`.
  - Criterio de aceptacion: metricas revisables y comparables por ejecucion; posible export futuro a InfluxDB/Grafana.
  - Riesgo si no se hace: optimizacion a ciegas del scraper.

- [ ] Revisar timeout del scraper Wunderground
  - Contexto: algunas estaciones pueden tardar o fallar.
  - Ficheros relacionados: `Rainmapper.py`, `util/`.
  - Criterio de aceptacion: timeout configurable y errores registrados sin bloquear toda la ejecucion.
  - Riesgo si no se hace: estaciones lentas penalizan todo el run.

- [ ] Homogeneizar idioma de logs y UI
  - Contexto: hay mensajes en ingles, espanol y algun comentario mixto.
  - Ficheros relacionados: `Rainmapper.py`, `Rainmapper_Client.py`, `web_server.py`, visores.
  - Criterio de aceptacion: idioma definido para usuario final y logs operativos.
  - Riesgo si no se hace: peor soporte y documentacion menos clara.

- [ ] Validar portabilidad del enlace App settings
  - Contexto: funciona en la instalacion actual, pero depende de slug/fallback.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: probado en otra instalacion HA o documentado como limitacion.
  - Riesgo si no se hace: enlace roto fuera del entorno actual.

## Prioridad baja
- [ ] Crear smoke tests automatizados
  - Contexto: no hay framework de tests detectado.
  - Ficheros relacionados: pendiente de definir.
  - Criterio de aceptacion: comando unico que valide sintaxis Python, JS, conversion GeoJSON minima y wrappers shell.
  - Riesgo si no se hace: regresiones manuales.

- [ ] Separar core en paquete Python reutilizable
  - Contexto: scripts grandes y duplicados.
  - Ficheros relacionados: `Rainmapper.py`, `rainmapper-app/app/Rainmapper.py`.
  - Criterio de aceptacion: una unica fuente de verdad para core compartida por Docker local y HA.
  - Riesgo si no se hace: mantenimiento manual permanente.

- [ ] Evaluar InfluxDB/Grafana para metricas
  - Contexto: el usuario ya tiene interes en analitica de tiempos de estaciones.
  - Ficheros relacionados: `Rainmapper.py`, futuro exporter.
  - Criterio de aceptacion: decision tecnica documentada.
  - Riesgo si no se hace: se acumulan CSV sin explotacion.

- [ ] Disenar futura app iOS/Android
  - Contexto: objetivo a largo plazo incluye app movil con autenticacion y permisos.
  - Ficheros relacionados: pendiente de definir.
  - Criterio de aceptacion: arquitectura propuesta para API, auth, permisos y serving de mapas.
  - Riesgo si no se hace: el visor publico actual no controla quien accede a que.

## Bugs abiertos
- [ ] Comportamiento del popup MapLibre pendiente de validacion final en movil
  - Sintoma: pendiente de confirmar; el codigo ya define popup con `anchor: "left"`, `maxWidth` y scroll interno via CSS.
  - Causa probable: si falla la validacion, sera por diferencias de comportamiento entre MapLibre Popup y Leaflet Popup en Safari/iPhone.
  - Ficheros relacionados: `maplibre-viewer/app.js`, `maplibre-viewer/style.css`, copias en `rainmapper-app/app/maplibre-viewer/`.
  - Como reproducir: abrir MapLibre en iPhone, seleccionar estacion con 21 registros y comprobar que no ocupa toda la pantalla ni desplaza el mapa.
  - Criterio de solucion: comportamiento validado o ajustes documentados si no coincide con Leaflet.

- [ ] Version Dockerfile HA desalineada
  - Sintoma: metadata de app y Dockerfile no parecen indicar la misma version.
  - Causa probable: labels/env no actualizados al subir versiones.
  - Ficheros relacionados: `rainmapper-app/Dockerfile`, `rainmapper-app/config.yaml`.
  - Como reproducir: comparar `version` en `config.yaml` con labels/env Dockerfile.
  - Criterio de solucion: version coherente.

- [ ] No hay tests formales
  - Sintoma: no existe comando de test configurado.
  - Causa probable: proyecto evolucionado por validacion manual.
  - Ficheros relacionados: pendiente de definir.
  - Como reproducir: buscar `pytest`, `package.json`, Makefile; no aparecen.
  - Criterio de solucion: definir minimo smoke test.

## Validaciones pendientes
- [ ] `docker compose build rainmapper` tras cambios de Docker local.
- [ ] `docker compose run --rm -e MODE=help rainmapper`.
- [ ] `docker compose run --rm -e MODE=all rainmapper` en datos de prueba antes de tocar historicos reales.
- [ ] Actualizacion HA desde GitHub tras bump de version.
- [ ] `Run all` desde webUI HA.
- [ ] Schedule con varias horas y dias.
- [ ] Leaflet en iPhone: cambio periodo conserva posicion, popups, leyenda, Jawg opcional.
- [ ] MapLibre en iPhone: estilos, marcadores tras cambio de capa, popup, bounds.
- [ ] `ignore_stations_tomap.txt`: estacion ignorada desaparece de Leaflet/MapLibre pero sigue en historico.
- [ ] Reconstruccion desde cero con poco historico.

## Preguntas pendientes para el usuario
- [ ] Confirmar si MapLibre debe sustituir a Leaflet como visor principal cuando este validado.
- [ ] Confirmar cuando retirar la ruta legacy `/local/rainmapper-mobile`.
- [ ] Confirmar si el repo debe quedar privado o publico para distribucion futura.
- [ ] Confirmar si Jawg permite restringir token por dominio y si se usara en publico.
- [ ] Confirmar idioma final de UI/logs: ingles, espanol o catalan.

## Ideas futuras
- App iOS/Android con login y autorizacion por mapa/zona.
- API propia entre backend y app movil.
- Capa de permisos por usuario.
- Cache/CDN de GeoJSON publicados.
- Panel de calidad de estaciones basado en metricas Wunderground.
- Auto-deteccion de outliers de lluvia antes de publicar mapas.
- Migracion de historicos CSV a formato mas eficiente si crecen mucho, por ejemplo Parquet, pendiente de evaluar.
