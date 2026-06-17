# TODO

## Proximo paso recomendado
Avanzar en la siguiente prioridad operativa: mantener sincronizadas raiz/app HA durante cada cambio funcional y homogeneizar idioma de logs/UI o validar portabilidad del enlace App settings.

## Prioridad alta
- [x] Corregir inconsistencia de version en la app HA
  - Contexto: `rainmapper-app/config.yaml` indica `0.2.42`; `rainmapper-app/Dockerfile` conserva ahora labels/env `0.2.42`.
  - Ficheros relacionados: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: version alineada en metadata HA, labels Docker y changelog.
  - Estado: resuelto.

- [x] Validar MapLibre en movil tras los ultimos ajustes
  - Contexto: MapLibre funciona bien en movil; se mantiene publicado junto a Leaflet de momento.
  - Ficheros relacionados: `maplibre-viewer/`, `rainmapper-app/app/maplibre-viewer/`.
  - Criterio de aceptacion: cambio de capa mantiene estaciones, cambio de periodo conserva vista, popup es usable y no desplaza/molesta.
  - Estado: validado por el usuario en movil.

- [ ] Mantener sincronizadas raiz y app HA
  - Contexto: hay copias de scripts y visores en raiz y dentro de `rainmapper-app/app`.
  - Ficheros relacionados: `Rainmapper.py`, `Rainmapper_Client.py`, `tomap_to_geojson.py`, `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/app/`.
  - Criterio de aceptacion: despues de cada cambio funcional, raiz y app contienen la misma version necesaria.
  - Riesgo si no se hace: Docker local funciona pero HA no, o al reves.

- [x] Proteger el historico CSV antes de cambios de pandas
  - Contexto: `Data/*_incremental.csv` es el valor principal del proyecto.
  - Ficheros relacionados: `Rainmapper.py`, `Data/`, `/share/rainmapper/Data`, `scripts/backup-data.sh`, `scripts/check-history.py`, `docs/history-safety.md`.
  - Criterio de aceptacion: backup o prueba en directorio temporal antes de cambios que escriban historicos.
  - Estado: resuelto como practica operativa versionada. Antes de cambios que escriban CSV, usar backup/copia temporal y validar con `scripts/check-history.py`.

## Prioridad media
- [x] Decidir visor principal
  - Contexto: conviven Bokeh, Leaflet y MapLibre; MapLibre ya funciona bien en movil.
  - Ficheros relacionados: `Rainmapper_Client.py`, `leaflet-viewer/`, `maplibre-viewer/`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: definir si Bokeh queda como legacy, si Leaflet sigue activo y si MapLibre pasa a principal.
  - Estado: decision temporal tomada; Leaflet y MapLibre se mantienen publicados de momento. Bokeh sigue como referencia/compatibilidad.
  - Riesgo aceptado: complejidad y mantenimiento de varios visores hasta nueva revision.

- [x] Retirar `/local/rainmapper-mobile`
  - Contexto: la ruta legacy ya no se usa porque Cloudflare redirige a `rainmapper-leaflet` y `rainmapper-maplibre`.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper-app/DOCS.md`, `README.md`, `rainmapper-app/README.md`.
  - Criterio de aceptacion: dejar de publicar `/local/rainmapper-mobile` y limpiar la carpeta antigua al publicar mapas.
  - Estado: resuelto en version `0.2.42`.

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
- [x] Crear smoke tests automatizados
  - Contexto: no hay framework de tests completo, pero existe `scripts/smoke-test.sh`.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `README.md`, `docs/architecture.md`, `docs/codex-handoff.md`.
  - Criterio de aceptacion: comando unico que valide sintaxis Python, JS, conversion GeoJSON minima y wrappers shell.
  - Estado: resuelto con smoke test de sintaxis Python/JS/shell, conversion GeoJSON minima, version HA, sincronizacion raiz/app HA y whitespace Git.

- [ ] Separar core en paquete Python reutilizable
  - Contexto: scripts grandes y duplicados.
  - Ficheros relacionados: `Rainmapper.py`, `rainmapper-app/app/Rainmapper.py`.
  - Criterio de aceptacion: una unica fuente de verdad para core compartida por Docker local y HA.
  - Riesgo si no se hace: mantenimiento manual permanente.

- [ ] Mejorar observabilidad de Wunderground
  - Contexto: Wunderground es el cuello de botella, pero todavia no hay suficientes observaciones de tiempos y el rendimiento actual es aceptable.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos.
  - Ficheros relacionados: `Rainmapper.py`, `Data/metricas_wunderground.csv`.
  - Criterio de aceptacion: metricas revisables y comparables por ejecucion; posible export futuro a InfluxDB/Grafana.
  - Riesgo si no se hace: optimizacion a ciegas del scraper si el rendimiento empeora en el futuro.

- [ ] Revisar timeout del scraper Wunderground
  - Contexto: algunas estaciones pueden tardar o fallar, pero el tiempo global actual es aceptable y conviene acumular mas observaciones antes de cambiarlo.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos.
  - Ficheros relacionados: `Rainmapper.py`, `util/`.
  - Criterio de aceptacion: timeout configurable y errores registrados sin bloquear toda la ejecucion.
  - Riesgo si no se hace: estaciones lentas podrian penalizar todo el run si el rendimiento empeora.

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
- [ ] No hay tests funcionales formales
  - Sintoma: no existe framework de test completo ni fixtures para validar conversion GeoJSON o runs funcionales.
  - Causa probable: proyecto evolucionado por validacion manual.
  - Ficheros relacionados: `scripts/smoke-test.sh`, futuro set de fixtures.
  - Como reproducir: ejecutar `./scripts/smoke-test.sh`; cubre smoke checks, pero no prueba datos reales ni ejecuciones Docker/HA.
  - Criterio de solucion: definir fixtures minimos y pruebas funcionales versionadas.

## Validaciones pendientes
- [ ] `docker compose build rainmapper` tras cambios de Docker local.
- [ ] `docker compose run --rm -e MODE=help rainmapper`.
- [ ] `docker compose run --rm -e MODE=all rainmapper` en datos de prueba antes de tocar historicos reales.
- [ ] Actualizacion HA desde GitHub tras bump de version.
- [ ] `Run all` desde webUI HA.
- [ ] Schedule con varias horas y dias.
- [ ] Leaflet en iPhone: cambio periodo conserva posicion, popups, leyenda, Jawg opcional.
- [x] MapLibre en movil: estilos, marcadores tras cambio de capa, popup, bounds.
- [ ] `ignore_stations_tomap.txt`: estacion ignorada desaparece de Leaflet/MapLibre pero sigue en historico.
- [ ] Reconstruccion desde cero con poco historico.

## Preguntas pendientes para el usuario
- [x] Confirmar si MapLibre debe sustituir a Leaflet como visor principal o si ambos se mantienen.
- [x] Confirmar cuando retirar la ruta legacy `/local/rainmapper-mobile`.
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
