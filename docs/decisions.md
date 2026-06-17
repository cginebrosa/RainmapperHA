# Decisions

## 2026-06-17 - Ejecutar Home Assistant en modo serve (fecha aproximada)

### Decision
La app de Home Assistant debe arrancar normalmente en `mode: serve`.

### Motivo
Permite tener la app viva en sidebar, webUI por ingress, schedule interno y botones manuales sin depender de arrancar contenedores puntuales.

### Alternativas consideradas
Ejecutar contenedores de un solo uso con `update` o `all` desde automatizaciones externas.

### Consecuencias
El contenedor queda abierto, pero consume pocos recursos. La webUI pasa a ser el punto operativo principal.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`

### Estado
Confirmada.

## 2026-06-17 - Persistir datos fuera del contenedor (fecha aproximada)

### Decision
Los datos viven en `/share/rainmapper` en Home Assistant y en `docker-data` en Docker local.

### Motivo
Evitar perder historicos y configuraciones al actualizar/reinstalar la app.

### Alternativas consideradas
Guardar datos dentro de la imagen/contenedor.

### Consecuencias
Los updates no deben machacar `stations.txt`, `ignore_stations_tomap.txt` ni historicos CSV. Hay que tener cuidado con permisos y symlinks.

### Ficheros afectados
- `rainmapper-app/run.sh`
- `docker-compose.yml`
- `.gitignore`

### Estado
Confirmada.

## 2026-06-17 - Mantener Docker local para pruebas en Mac (fecha aproximada)

### Decision
Conservar un Docker local separado del paquete HA.

### Motivo
Permite probar cambios de core y mapas antes de llevarlos a Home Assistant/RPi.

### Alternativas consideradas
Desarrollar directamente sobre la app HA.

### Consecuencias
Hay duplicidad de scripts entre raiz y app HA. Se gana seguridad operativa a costa de sincronizacion manual.

### Ficheros afectados
- `Dockerfile`
- `docker-compose.yml`
- `run.sh`
- `rainmapper-app/app/`

### Estado
Confirmada, revisable.

## 2026-06-17 - Publicar mapas en /config/www (fecha aproximada)

### Decision
Cuando `publish_to_www` esta activo, la app copia mapas y visores a `/config/www` para servirlos como `/local/...`.

### Motivo
Permite abrir mapas desde HA, movil y enlaces externos via dominio/Cloudflare.

### Alternativas consideradas
Servir solo desde la webUI/ingress de la app.

### Consecuencias
Los mapas pueden quedar accesibles por URL publica si HA esta publicado. La autorizacion granular no esta implementada todavia.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`

### Estado
Confirmada.

## 2026-06-17 - Mantener Bokeh, Leaflet y MapLibre durante transicion (fecha aproximada)

### Decision
No retirar Bokeh todavia; publicar tambien Leaflet y MapLibre. MapLibre queda como visor principal recomendado y Leaflet como fallback.

### Motivo
Bokeh es la referencia historica. Leaflet funciona bien en movil. MapLibre permite mapas vectoriales mas nitidos y desde `0.2.47` tambien puede cubrir las capas raster Hybrid y Topographic que antes estaban solo en Leaflet. Desde `0.2.48`, MapLibre tambien prueba Satellite+, combinando imagen Esri con orientacion vectorial OpenFreeMap.

### Alternativas consideradas
Eliminar Bokeh inmediatamente o sustituir Leaflet por MapLibre de golpe.

### Consecuencias
Hay mas mantenimiento, pero se puede comparar comportamiento y calidad antes de migrar. MapLibre ya esta validado como funcional en movil. Modificado en `0.2.47`: MapLibre incorpora Hybrid raster por defecto y Topographic raster, manteniendo los estilos vectoriales. Modificado en `0.2.48`: se descarta Tracestrack por ahora porque requiere app key de pago para vector maps y se prueba Satellite+ con OpenFreeMap sobre imagen Esri. Modificado en `0.2.53`: MapLibre queda como visor principal recomendado tras validacion en HA/iPhone; Leaflet sigue publicado como fallback.

### Ficheros afectados
- `Rainmapper_Client.py`
- `tomap_to_geojson.py`
- `leaflet-viewer/`
- `maplibre-viewer/`
- `rainmapper-app/app/web_server.py`

### Estado
Confirmada, revisable. Modificada el 2026-06-17 para reflejar que MapLibre ya funciona bien en movil, que se mantienen publicados Leaflet y MapLibre, y que MapLibre `0.2.53` pasa a ser el visor principal recomendado. Leaflet queda como fallback.

## 2026-06-17 - Retirar ruta legacy rainmapper-mobile

### Decision
Dejar de publicar `/local/rainmapper-mobile` desde la app de Home Assistant.

### Motivo
La ruta legacy ya no se utiliza. Cloudflare tiene redirecciones hacia `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre`.

### Alternativas consideradas
Mantener `/local/rainmapper-mobile` indefinidamente como alias de compatibilidad.

### Consecuencias
Se reduce una ruta duplicada y se simplifica la publicacion. En la siguiente generacion de mapas se elimina cualquier carpeta antigua `/config/www/rainmapper-mobile` que quedara publicada.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `README.md`
- `rainmapper-app/README.md`
- `rainmapper-app/DOCS.md`

### Estado
Confirmada.

## 2026-06-17 - App settings con enlaces fallback

### Decision
La pagina `/settings` de la webUI muestra el enlace recomendado a la configuracion de la app y rutas fallback en vez de redirigir automaticamente a una unica URL.

### Motivo
La ruta de configuracion de Home Assistant puede variar por version o por formato de slug. Una redireccion automatica a una sola URL podia funcionar en una instalacion y fallar en otra sin dejar alternativas visibles.

### Alternativas consideradas
Mantener la redireccion automatica a `/config/app/<slug>/config`.

### Consecuencias
Abrir la configuracion requiere un clic adicional, pero la pagina es mas portable y da opciones visibles si cambia la ruta o el slug. Modificado en `0.2.44`: solo se muestra el enlace recomendado por defecto; los fallbacks quedan en una seccion avanzada porque en la instalacion actual solo funciona el recomendado.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`

### Estado
Confirmada, modificada en `0.2.44`.

## 2026-06-17 - Ingles para webUI HA y changelog

### Decision
Usar ingles para los textos visibles de la webUI de Home Assistant, metadata de la app HA y `rainmapper-app/CHANGELOG.md`.

### Motivo
Home Assistant y el changelog son superficies de usuario/soporte donde conviene mantener un idioma consistente y portable.

### Alternativas consideradas
Mantener mezcla de ingles/espanol o traducir tambien todos los logs internos en el mismo cambio.

### Consecuencias
La version `0.2.45` corrige los textos visibles detectados y traduce entradas antiguas del changelog. Modificado en `0.2.46`: los logs operativos principales del core tambien pasan a ingles, incluyendo progreso y resumen Wunderground. README/DOCS de la app HA se mantienen en espanol de momento porque la app es principalmente de uso propio y no una distribucion publica para terceros.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Confirmada.

## 2026-06-17 - Usar GeoJSON como capa comun para visores nuevos (fecha aproximada)

### Decision
Leaflet y MapLibre consumen GeoJSON generado desde `Tomap`.

### Motivo
Separar datos de visualizacion, reutilizar los mismos datos para varios visores y preparar una futura app movil.

### Alternativas consideradas
Parsear directamente CSV `Tomap` en navegador o seguir solo con HTML Bokeh.

### Consecuencias
`tomap_to_geojson.py` se vuelve pieza clave. Cambios en `Tomap` requieren revisar el conversor.

### Ficheros afectados
- `tomap_to_geojson.py`
- `leaflet-viewer/app.js`
- `maplibre-viewer/app.js`

### Estado
Confirmada.

## 2026-06-17 - Crear smoke test versionado

### Decision
Mantener un comando unico `./scripts/smoke-test.sh` para validaciones rapidas del repositorio.

### Motivo
El proyecto no tiene framework de tests completo y hay riesgo recurrente de errores de sintaxis, metadata HA desalineada o copias raiz/app HA desincronizadas.

### Alternativas consideradas
Seguir ejecutando comandos manuales sueltos en cada sesion.

### Consecuencias
El smoke test no sustituye pruebas funcionales en Docker/HA ni validacion movil, pero deja una red basica repetible para cambios pequenos y medianos.

### Ficheros afectados
- `scripts/smoke-test.sh`
- `README.md`
- `docs/architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Confirmada.

## 2026-06-17 - Sincronizacion operativa raiz/app HA sin refactor

### Decision
Mantener la duplicidad actual entre raiz y `rainmapper-app/app`, pero anadir `scripts/sync-app-files.sh` como comando explicito para copiar scripts raiz y visores a la app HA.

### Motivo
La duplicidad todavia existe y una refactorizacion estructural del core seria mas amplia. Un comando versionado reduce errores manuales mientras se mantiene el flujo actual.

### Alternativas consideradas
Refactorizar ya el core en un paquete Python unico o seguir copiando ficheros manualmente.

### Consecuencias
`scripts/sync-app-files.sh` sincroniza raiz -> app HA y `scripts/smoke-test.sh` verifica que las copias quedan identicas. No elimina la deuda arquitectonica; solo la mitiga operativamente.

### Ficheros afectados
- `scripts/sync-app-files.sh`
- `scripts/smoke-test.sh`
- `README.md`
- `docs/codex-handoff.md`
- `docs/architecture.md`
- `docs/todo.md`

### Estado
Confirmada.

## 2026-06-17 - Proteger historicos antes de cambios de escritura CSV

### Decision
Antes de cambios que puedan escribir o reestructurar historicos CSV, se debe trabajar con backup o copia temporal y validar la salida con `scripts/check-history.py`.

### Motivo
Los CSV historicos son el activo central del proyecto y pueden corromperse si hay errores en pandas, merges, deduplicado, fechas o escritura de columnas.

### Alternativas consideradas
Confiar solo en validacion manual despues de ejecutar contra datos reales.

### Consecuencias
Los cambios de core de datos llevan un paso operativo adicional, pero reducen el riesgo de perdida o corrupcion de historicos.

### Ficheros afectados
- `scripts/backup-data.sh`
- `scripts/check-history.py`
- `docs/history-safety.md`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Confirmada.

## 2026-06-17 - Ignorar estaciones anomalas con fichero manual (fecha aproximada)

### Decision
Crear `ignore_stations_tomap.txt` y aplicarlo solo al generar GeoJSON.

### Motivo
Permite ocultar estaciones con outliers sin borrar ni alterar historicos. Si el outlier caduca del periodo, la estacion puede volver quitandola del fichero.

### Alternativas consideradas
Borrar datos historicos, filtrar automaticamente outliers o desactivar descarga de la estacion.

### Consecuencias
El control es manual. Afecta solo Leaflet/MapLibre, no Bokeh ni historicos.

### Ficheros afectados
- `tomap_to_geojson.py`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `README.md`
- `rainmapper-app/DOCS.md`

### Estado
Confirmada.

## 2026-06-17 - Mantener stations.txt fuera de la imagen (fecha aproximada)

### Decision
`stations.txt` se crea/preserva en `/share/rainmapper` o `docker-data`, no dentro de la imagen como unica fuente editable.

### Motivo
Permite anadir/quitar estaciones Wunderground sin reconstruir imagen.

### Alternativas consideradas
Incluir `stations.txt` fijo en Docker.

### Consecuencias
La primera instalacion debe crear una plantilla si falta. Los updates no deben sobrescribir el fichero del usuario.

### Ficheros afectados
- `rainmapper-app/run.sh`
- `docker-compose.yml`
- `stations.example.txt`

### Estado
Confirmada.

## 2026-06-17 - Usar Wunderground con un thread por defecto en RPi (fecha aproximada)

### Decision
Mantener `max_threads: 1` por defecto.

### Motivo
La RPi no debe cargarse excesivamente. El scraper es el cuello de botella, pero estabilidad y baja carga pesan mas que paralelizar agresivamente.

### Alternativas consideradas
Subir threads para acelerar scraping.

### Consecuencias
La ejecucion completa tarda mas, pero la carga es estable. Se anaden metricas para entender donde optimizar. El rendimiento actual es aceptable: update completo + generacion de mapas tarda unos 7 minutos, asi que cambios de timeout/observabilidad quedan en baja prioridad hasta acumular mas datos.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `docker-compose.yml`
- `Rainmapper.py`

### Estado
Confirmada, revisable. Modificada el 2026-06-17 para bajar timeout/observabilidad de Wunderground a baja prioridad mientras el tiempo global siga siendo aceptable.

## 2026-06-17 - Guardar metricas de Wunderground en CSV (fecha aproximada)

### Decision
Guardar tiempos por estacion en `Data/metricas_wunderground.csv`.

### Motivo
Permite analizar estaciones lentas sin depender solo del log y prepara posible explotacion futura en Grafana/InfluxDB.

### Alternativas consideradas
Solo log, InfluxDB inmediato.

### Consecuencias
Se acumula otro CSV operativo. InfluxDB queda como mejora futura.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`

### Estado
Confirmada.

## 2026-06-17 - Soportar multiples patrones Meteoclimatic (fecha aproximada)

### Decision
`meteoclimatic_pattern` acepta varios patrones separados por coma, punto y coma o ` - `.

### Motivo
Permite recuperar varias zonas RSS sin cambiar codigo.

### Alternativas consideradas
Un solo patron fijo en `const.py`.

### Consecuencias
Hay un pequeno delay entre peticiones para no golpear el feed. Algunos prefijos pueden no estar soportados por Meteoclimatic aunque el codigo los acepte.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/config.yaml`

### Estado
Confirmada.

## 2026-06-17 - API keys solo por entorno/configuracion (fecha aproximada)

### Decision
No guardar API keys reales en Git. Google y Jawg se configuran por variables/opciones.

### Motivo
Evitar exposicion de credenciales. Ya hubo una alerta historica por una Google API key antigua.

### Alternativas consideradas
Hardcodear claves en scripts o HTML.

### Consecuencias
Cada instalacion debe configurar sus propias claves. En mapas cliente, tokens de tiles pueden ser visibles en navegador y deben restringirse por dominio si el proveedor lo permite.

### Ficheros afectados
- `const.py`
- `rainmapper-app/config.yaml`
- `leaflet-viewer/config.js`
- `maplibre-viewer/config.js`

### Estado
Confirmada.

## 2026-06-17 - Exponer visor por dominio/Cloudflare sin auth propia por ahora (fecha aproximada)

### Decision
Usar dominio/Cloudflare para acceder a HA/visor, pero no implementar aun autenticacion propia de Rainmapper.

### Motivo
Permite compartir y probar el visor rapidamente.

### Alternativas consideradas
Construir backend/app con auth antes de publicar visores.

### Consecuencias
Es valido para pruebas privadas, pero no para producto publico con permisos por usuario/mapa. Hay que resolverlo antes de una app iOS/Android publica.

### Ficheros afectados
- No hay configuracion Cloudflare versionada en el repo.
- `rainmapper-app/app/web_server.py` publica contenido en `/config/www`.

### Estado
Confirmada para pruebas, revisable antes de publicacion.

## 2026-06-17 - Futura app movil con API propia antes de producto publico

### Decision
Para una futura app iOS/Android publica o bajo suscripcion, no depender directamente de Home Assistant como backend publico. Mantener HA como motor privado de generacion y disenar una API/backend intermedio para autenticacion, permisos, filtros y serving controlado de datos.

### Motivo
Los visores actuales y GeoJSON estaticos funcionan bien para uso privado, pero no dan control granular por usuario, mapa o zona. Una app comercial necesita autorizacion en servidor, revocacion de acceso y una forma segura de aplicar favoritos y filtros.

### Alternativas consideradas
Consumir directamente los GeoJSON publicados en `/local/...` desde la app movil, convertir HA en backend publico, o migrar inmediatamente todos los datos a una base de datos nueva.

### Consecuencias
La primera fase de app movil deberia definir API, auth y permisos antes de producto publico. La migracion a base de datos queda como fase posterior si GeoJSON/CSV dejan de ser suficientes.

### Ficheros afectados
- `docs/mobile-app-architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Propuesta inicial confirmada a nivel de diseno; pendiente de implementacion.

## 2026-06-17 - Cloudflare y app cross-platform como direccion de prototipo movil

### Decision
Para explorar la futura app iOS/Android, tomar como direccion preferente de prototipo una arquitectura con Cloudflare R2 para artefactos GeoJSON, Cloudflare Worker como API ligera y React Native + MapLibre React Native como app cross-platform.

### Motivo
Cloudflare ya forma parte del acceso externo actual y encaja con artefactos GeoJSON estaticos/cacheables. Workers evita operar un VPS en la primera fase. React Native permite una base comun iOS/Android y MapLibre alinea la app con el visor principal recomendado del proyecto.

### Alternativas consideradas
App nativa separada Swift/Kotlin, PWA, FastAPI en VPS, Supabase/Firebase como backend principal o consumo directo de GeoJSON publicados por Home Assistant.

### Consecuencias
La app futura deberia consumir una API controlada, no rutas `/local/...` de Home Assistant. Hay que definir estructura R2, manifiesto `latest.json`, endpoints minimos y una estrategia de auth/permisos antes de producto publico. La implementacion no es inmediata y puede revisarse si el prototipo muestra limitaciones.

### Ficheros afectados
- `docs/mobile-app-architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Confirmada como direccion de diseno/prototipo; pendiente de implementacion.

## 2026-06-17 - Usar imagen preconstruida GHCR para la app HA

### Decision
Configurar la app de Home Assistant para usar la imagen preconstruida `ghcr.io/cginebrosa/rainmapperha:<version>` y publicar imagen multi-arch `amd64`/`arm64` con GitHub Actions.

### Motivo
Home Assistant estaba construyendo la imagen en la Raspberry Pi en cada update, con tiempos observados cercanos a 3 minutos incluso para cambios pequenos. La documentacion oficial de Home Assistant recomienda contenedores preconstruidos como metodo preferido porque el usuario solo descarga la imagen final y evita builds locales lentos.

### Alternativas consideradas
Mantener build local en HA, construir manualmente en Mac y subir imagen a mano, o posponer la preconstruccion hasta una fase mas estable.

### Consecuencias
Los updates de HA pasan a depender de que GitHub Actions haya publicado la imagen de la version correspondiente antes de actualizar en HA. El paquete GHCR debe ser accesible para Home Assistant; si queda privado, habra que hacerlo publico o configurar autenticacion. Se gana velocidad de instalacion/update en RPi si el tiempo de GitHub Actions, idealmente con cache Buildx/GHA, resulta aceptable. Si no compensa para pruebas rapidas, queda abierta la alternativa de build/push manual desde Mac.

### Ficheros afectados
- `.github/workflows/build-rainmapper-app.yml`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Implementada y validada en `0.2.57`: Home Assistant descargo `ghcr.io/cginebrosa/rainmapperha:0.2.57` sin build local. Modificada en `0.2.58` para anadir cache Buildx/GHA en futuras Actions. Reemplazada como flujo normal en `0.2.60` por build/push local con Buildx antes del commit de version, dejando GitHub Actions como fallback manual.

## 2026-06-17 - Publicar imagen HA con Buildx local antes del commit de version

### Decision
Usar `scripts/build-push-ha-image.sh` como flujo normal para publicar desde el Mac la imagen multi-arch `ghcr.io/cginebrosa/rainmapperha:<version>` antes de hacer commit/push del cambio de version visible para Home Assistant. GitHub Actions queda disponible solo como workflow manual de fallback.

### Motivo
GitHub Actions con cache siguio tardando alrededor de 7 minutos y Home Assistant detecta el update en cuanto ve `config.yaml`, aunque la imagen todavia no este publicada. Publicar localmente primero elimina esa ventana y aprovecha que el Mac construye mas rapido que la Raspberry Pi.

### Alternativas consideradas
Mantener GitHub Actions automatico y esperar a que termine, construir en Home Assistant, o subir imagen manual sin script versionado.

### Consecuencias
El flujo de release exige login Docker contra GHCR en el Mac y disciplina de publicar imagen antes de subir el commit de version. A cambio, HA no deberia ofrecer un update cuyo tag de imagen aun no exista. GitHub Actions deja de ejecutarse automaticamente en cada push de `rainmapper-app`.

### Ficheros afectados
- `scripts/build-push-ha-image.sh`
- `.github/workflows/build-rainmapper-app.yml`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/decisions.md`

### Estado
Implementado en `0.2.60`; pendiente validar instalacion en Home Assistant usando imagen publicada localmente.

## 2026-06-17 - Exponer fuente de estacion en GeoJSON y filtros del visor

### Decision
Anadir propiedad `Source` a los GeoJSON generados e incorporar en MapLibre Settings un filtro por fuentes Meteocat, Meteoclimatic y Wunderground, junto al filtro existente de lluvia minima.

### Motivo
La futura app iOS/Android necesitara filtros de estaciones sin depender de logica duplicada en cada cliente. Los CSV `Tomap` actuales no traen una columna de origen, pero los codigos reales permiten una inferencia razonablemente conservadora sin tocar historicos: Meteoclimatic empieza por `ES` y tiene longitud larga, aproximada como minimo 15 caracteres; Wunderground empieza por `I`; Meteocat se limita a codigos de longitud 2. Cualquier otro codigo queda como `Unknown` y se avisa en stdout al convertir GeoJSON.

### Alternativas consideradas
Filtrar solo en el cliente por patrones de codigo, o modificar el pipeline principal `Rainmapper.py` para anadir origen a los historicos.

### Consecuencias
Los visores pueden usar `Source` directamente y el cliente futuro tendra un contrato de datos mas claro. La inferencia sigue acoplada al formato actual de codigos; si una fuente cambia su nomenclatura, habra que ajustar `tomap_to_geojson.py` y sus tests. No se modifica el historico CSV. `Unknown` se mantiene visible como filtro separado en MapLibre para no ocultar datos inesperados.

### Ficheros afectados
- `tomap_to_geojson.py`
- `maplibre-viewer/`
- `rainmapper-app/app/tomap_to_geojson.py`
- `rainmapper-app/app/maplibre-viewer/`
- `tests/test_tomap_to_geojson.py`

### Estado
Implementada en `0.2.58`; modificada en `0.2.59` para clasificar Meteocat solo con codigos de longitud 2 y avisar por `Unknown`. Pendiente validacion en Home Assistant/iPhone.
