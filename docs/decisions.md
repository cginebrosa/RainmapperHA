# Decisions

## 2026-06-22 - La ruta activa del repo es `/Users/carlosginebrosa/Developer/RainmapperHA`

Decision:

- Usar `/Users/carlosginebrosa/Developer/RainmapperHA` como unica copia activa para desarrollo, tests, builds, documentacion y commits.
- No usar la copia antigua situada bajo iCloud/Mobile Documents porque quedo desfasada y puede provocar ediciones sobre un arbol incorrecto.

Motivo:

- Durante la sesion se detecto que el entorno podia arrancar en la ruta antigua de iCloud mientras el repositorio actualizado vivia en `~/Developer/RainmapperHA`.
- Documentar la ruta evita repetir el problema en futuras sesiones de Codex.

Consecuencias:

- Antes de cualquier cambio relevante, comprobar `pwd` y `git status` en la ruta real.
- Si una herramienta apunta a la ruta iCloud, corregir el `workdir` antes de leer o escribir ficheros.

## 2026-06-21 - Proteger MapLibre y GeoJSON con autenticacion ligera

Decision:

- MapLibre pasa a abrirse desde `/protected/maplibre/index.html` en la webUI de Home Assistant.
- Los GeoJSON y `source_status.json` de MapLibre se sirven desde `/protected/maplibre/data/*` y requieren sesion valida.
- Leaflet se mantiene publicado en `/local/rainmapper-leaflet` como fallback sin autenticacion.
- Los usuarios se gestionan de forma manual en `/share/rainmapper/users.json`.
- Historial de formato: primero se considero un fichero plano separado por punto y coma. Esa decision queda reemplazada por `users.json` como formato unico.
- `users.json` permite campos extensibles: `username`, `name`, `email`, `password`, `role`, `enabled`, `max_devices` y `must_change_password`. `username` es el identificador de login; `name` es el nombre de la persona; `email` queda como contacto.
- Roles soportados: `free`, `basic`, `pro` y `admin`.
- Limites por defecto: `free=1`, `basic=2`, `pro=3`, `admin=0`; `0` significa dispositivos ilimitados. El campo `max_devices` permite sobrescribir el limite por usuario.
- El primer login de un usuario registra un `device_id` generado por el navegador en `/share/rainmapper/devices.json`; nuevos dispositivos se aceptan hasta el limite del usuario. Los dispositivos ya registrados pueden reutilizarse aunque el usuario haya alcanzado su limite.
- En HA, `run.sh` crea `users.json` desde `users.example.json` y `devices.json` vacio si faltan, sin sobrescribir ficheros existentes.
- La WebUI HA incorpora una pagina `Users`, pensada para acceso por Ingress/Home Assistant, para crear usuarios, borrar usuarios, activar/desactivar acceso, editar rol/max_devices, establecer nuevas contrasenas, forzar cambio de contrasena y borrar dispositivos de forma granular. `Delete user` borra tambien todos sus dispositivos asociados. `Set password` guarda una contrasena definida por el administrador y borra dispositivos; `Reset password` marca `must_change_password=true`, borra dispositivos y obliga al usuario a elegir una contrasena distinta tras autenticarse con la actual.

Motivo:

- Evitar compartir un enlace publico sin control durante pruebas con terceros.
- Mantener una solucion simple y reversible antes de construir una gestion real de usuarios, permisos o suscripciones.
- Proteger los datos en servidor, no solo ocultar controles en JavaScript.

Alternativas descartadas:

- Proteger solo el HTML del visor: insuficiente, porque los GeoJSON seguirian accesibles directamente.
- Implementar ya una base de datos de usuarios completa: excesivo para la fase actual de pruebas privadas.
- Usar cookies de sesion como unico mecanismo: se evita de momento para mantener un flujo simple y portable entre Safari, Chrome, Firefox y Android/iOS usando `localStorage` + cabeceras.

Consecuencias:

- Si un usuario con limite de dispositivos borra datos del navegador, generara un nuevo `device_id` y puede quedar bloqueado hasta que se limpie o desactive un registro anterior en `devices.json`.
- El add-on HA publica `8099/tcp` para que Cloudflared pueda apuntar al servidor Rainmapper con `service: http://<HA_IP>:8099`; las reglas externas de Cloudflare para MapLibre deben apuntar a `/protected/maplibre/index.html`, no a `/local/rainmapper-maplibre/index.html`.
- La limpieza defensiva de `/config/www/rainmapper-maplibre/data` queda preparada en codigo, pero aplazada temporalmente para mantener `/local/rainmapper-maplibre/index.html` como fallback funcional mientras se valida Cloudflared/puerto 8099.
- Las contrasenas en claro de `users.json` se migran automaticamente a hash PBKDF2 al primer login correcto.
- El formato antiguo separado por punto y coma se retira tras validar la migracion en la unica instalacion HA activa. Desde este punto, `users.json` es el unico formato soportado.
- El visor Docker local queda sin autenticacion para mantenerlo como entorno rapido de pruebas.
- Modificado el 2026-06-22: los fallbacks externos `leaflet.nomentero.com` y `maplibre.nomentero.com` quedan detras de Cloudflare Access. El fallback local `/local/rainmapper-maplibre` sigue existiendo en HA, pero ya no debe quedar expuesto externamente sin login de Cloudflare.

Estado:

Implementado en varios pasos. La proteccion basica de MapLibre fue validada manualmente por el usuario en HA `0.2.82`: `admin` pudo entrar desde Mac e iPhone, y un usuario normal quedo limitado a un dispositivo. La ampliacion a `users.json` con `username`, `name`, `email`, roles `free/basic/pro/admin` y `max_devices` esta publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.83` y cubierta por `tests/test_web_server_auth.py`. El usuario valido en HA que el login creaba `users.json` desde el formato anterior; despues se decide retirar completamente el formato anterior para evitar ambiguedades futuras. La WebUI de gestion queda publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.84`; la correccion del auto-refresh de formularios queda publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.85`; la gestion clara de `Set password`/`Reset password` queda publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.86` y pendiente de validacion HA.

## 2026-06-20 - Retirar wrappers raiz `Rainmapper.py` y `Rainmapper_Client.py`

Decision:

- Se eliminan `Rainmapper.py` y `Rainmapper_Client.py` de la raiz.
- Docker local, Home Assistant y la webUI ejecutan directamente `python -m rainmapper_core.rainmapper` y `python -m rainmapper_core.bokeh_maps`.
- La imagen HA deja de copiar wrappers Python de raiz; solo copia `stations.example.txt`, `rainmapper_core/`, `web_server.py` y `run.sh`.

Motivo:

- Los wrappers ya no aportaban compatibilidad operativa suficiente y mantenian la confusion sobre donde vive el codigo real.
- El core ya esta empaquetado como modulo ejecutable y el build HA se hace desde la raiz del repositorio.

Consecuencias:

- Cualquier uso manual antiguo `python Rainmapper.py ...` debe cambiarse por `python -m rainmapper_core.rainmapper ...`.
- Cualquier uso manual antiguo `python Rainmapper_Client.py` debe cambiarse por `python -m rainmapper_core.bokeh_maps`.
- Los wrappers shell (`run.sh`, `local_all.sh`, `local_maps.sh`, `local_update.sh`) se mantienen como interfaz comoda de usuario.

## 2026-06-20 - Retirar wrappers raiz de configuracion e incremental upsert

Decision:

- Se eliminan `const.py`, `config.py`, `config_wunderground.py` e `incremental_upsert.py` de la raiz.
- El codigo y los tests importan directamente desde `rainmapper_core.config` y `rainmapper_core.incremental_upsert`.
- La imagen HA deja de copiar esos wrappers desde la raiz.

Motivo:

- Ya no hay codigo interno que dependa de los imports legacy top-level.
- Mantener esos wrappers en la raiz creaba confusion sobre donde vive la configuracion real.
- La raiz queda reservada a entrypoints shell de usuario que siguen aportando compatibilidad, como `run.sh` y `local_*.sh`; los entrypoints Python se ejecutan con `python -m rainmapper_core...`.

Consecuencias:

- Cualquier uso manual antiguo `from const import ...` o `from incremental_upsert import ...` debe cambiarse a imports desde `rainmapper_core`.
- Este cambio requiere validar Docker local, smoke test y build HA porque afecta al contenido copiado a la imagen.

## 2026-06-20 - Construir HA desde la raiz y retirar copias fisicas de core

Sustituye la decision operativa anterior de sincronizar raiz -> `rainmapper-app/app` con `scripts/sync-app-files.sh`.

Decision:

- `rainmapper-app/Dockerfile` se construye con la raiz del repositorio como contexto.
- La imagen HA copia `rainmapper_core/`, wrappers raiz, configuracion compartida y `rainmapper-app/app/web_server.py` directamente desde la raiz.
- `rainmapper-app/app` queda reservado a codigo especifico de HA; actualmente solo contiene `web_server.py`.
- `scripts/sync-app-files.sh` y `scripts/sync-manifest.sh` se retiran.

Motivo:

- Eliminar la duplicidad fisica que obligaba a sincronizar manualmente o mediante script.
- Evitar que HA y Docker local puedan quedar con versiones distintas del core.
- Hacer que `requirements.txt` tenga una sola fuente de verdad para el build HA.

Alternativas descartadas:

- Mantener copias HA sincronizadas: resuelto temporalmente, pero seguia generando confusion y trabajo recurrente.
- Convertir ya todo en paquete instalable Python: se pospone; el build desde raiz resuelve la duplicidad con menos riesgo.

Consecuencias:

- El build HA ya no soporta usar `rainmapper-app` como contexto Docker aislado; debe usarse la raiz del repo.
- `scripts/build-push-ha-image.sh` y `.github/workflows/build-rainmapper-app.yml` usan ese contexto raiz.
- `scripts/smoke-test.sh` valida que no vuelvan copias de core a `rainmapper-app/app`.

## 2026-06-20 - Retirar wrappers raiz/HA de Tomap y GeoJSON

Se eliminan los wrappers `tomap_builder.py` y `tomap_to_geojson.py` de la raiz y sus copias en `rainmapper-app/app`.

Decision:

- `rainmapper_core.tomap` se ejecuta directamente con `python -m rainmapper_core.tomap`.
- `rainmapper_core.geojson` se ejecuta directamente con `python -m rainmapper_core.geojson`.
- Docker local, Home Assistant, webUI, smoke test y pruebas Docker offline pasan a usar esos modulos core.

Motivo:

- Tomap y GeoJSON ya son piezas del core y no necesitan wrappers historicos en raiz.
- Reducir entrypoints duplicados evita confusion sobre donde vive la implementacion real.

Alternativas descartadas:

- Mantener wrappers por compatibilidad: ya no aportan suficiente valor frente a la confusion que generan.
- Renombrar comandos de usuario locales: se pospone; `local_maps.sh` y `local_all.sh` siguen siendo la interfaz comoda para pruebas.

Consecuencias:

- Cualquier uso manual antiguo `python tomap_builder.py` o `python tomap_to_geojson.py` debe cambiarse por `python -m rainmapper_core.tomap` o `python -m rainmapper_core.geojson`.
- Sustituida por la decision posterior de construir HA desde la raiz: la imagen HA copia `rainmapper_core/` durante el build, pero no se versiona una copia fisica en `rainmapper-app/app`.

## 2026-06-20 - Mover `Rainmapper.py` a `rainmapper_core/rainmapper.py`

Se mueve la implementacion real del runner principal de descarga y actualizacion al paquete compartido `rainmapper_core`.

Decision:

- `rainmapper_core/rainmapper.py` pasa a ser la unica implementacion real de descarga, historicos, estado por fuente y metricas.
- `Rainmapper.py` queda como wrapper compatible que ejecuta `rainmapper_core.rainmapper`; HA lo copia desde la raiz durante el build.
- No se parte todavia la logica interna del runner; esta fase solo elimina la duplicidad real raiz/app HA.

Motivo:

- `Rainmapper.py` era el ultimo bloque grande con implementacion duplicada entre raiz y HA.
- Mantener el nombre historico como wrapper evita romper Docker local, HA, scripts existentes y uso manual.

Alternativas descartadas:

- Renombrarlo a `runner.py`: descartado por preferencia del proyecto y porque `rainmapper.py` describe mejor el modulo principal.
- Partir fuentes/CLI/estado en la misma fase: descartado para no mezclar movimiento estructural con reescritura funcional.

Consecuencias:

- Sustituida por la decision posterior de construir HA desde la raiz: no queda copia versionada de `rainmapper_core/` dentro de `rainmapper-app/app`.
- Validado localmente con smoke, Docker offline y `local_update.sh`; HA 0.2.79 valido el movimiento antes de retirar las ultimas copias.

## 2026-06-20 - Mover Bokeh y visores compartidos a `rainmapper_core`

Se mueve la implementacion compartida de mapas clasicos Bokeh y los visores web estaticos al paquete core.

Decision:

- `Rainmapper_Client.py` queda como entrypoint compatible y la implementacion real pasa a `rainmapper_core/bokeh_maps.py`.
- Los visores pasan a:
  - `rainmapper_core/viewers/leaflet-viewer/`
  - `rainmapper_core/viewers/maplibre-viewer/`
- Se retiran las rutas compatibles `leaflet-viewer/` y `maplibre-viewer/` de la raiz; las pruebas locales usan directamente `rainmapper_core/viewers/...`.
- `web_server.py` publica directamente desde `/app/rainmapper_core/viewers/leaflet-viewer` y `/app/rainmapper_core/viewers/maplibre-viewer`, por lo que se retiran las copias separadas `rainmapper-app/app/leaflet-viewer` y `rainmapper-app/app/maplibre-viewer`.

Motivo:

- Bokeh y visores son compartidos por Docker local y Home Assistant, no especificos de ningun runtime.
- Moverlos como bloques coherentes reduce la estructura hibrida sin tocar todavia `web_server.py`, URLs publicas ni Dockerfile de HA.

Alternativas descartadas:

- Mantener copias separadas en `rainmapper-app/app`: descartado tras validar que `web_server.py` puede publicar directamente desde `rainmapper_core/viewers`.
- Eliminar rutas compatibles de raiz: se descarta temporalmente porque romperia comandos locales, documentacion y pruebas existentes.

## 2026-06-20 - Mover configuracion Python compartida a `rainmapper_core/config`

Se mueve la implementacion real de `rainmapper_core/config/const.py`, `rainmapper_core/config/config.py` y `rainmapper_core/config/config_wunderground.py` a `rainmapper_core/config/`.

Motivo:

- Son configuracion compartida por Docker local y Home Assistant.
- Mantenerlas en raiz perpetua la estructura hibrida que se quiere reducir en la fase 5.
- Moverlas como bloque coherente evita una secuencia indefinida de micro-refactors.

Decision:

- Crear `rainmapper_core/config/`.
- Mantener wrappers compatibles en raiz y en `rainmapper-app/app`.
- Actualizar imports internos para usar `rainmapper_core.config`.
- Mantener los wrappers aunque el codigo interno ya no dependa de ellos, para no romper usos manuales o scripts externos con imports historicos.

Detalle importante:

- `rainmapper_core/config/const.py` mantiene nombres historicos con guion bajo (`_DATA_PATH`, `_max_threads`, etc.). La decision posterior del 2026-06-20 retira el wrapper raiz, por lo que el import canonico es `rainmapper_core.config.const`.
- La implementacion movida calcula `_script_path` como la raiz del runtime, no como `rainmapper_core/config`, para conservar rutas `Data`, `Tomap` y `Plots`.

Alternativas descartadas:

- Eliminar wrappers en la misma fase: mas limpio a largo plazo, pero menos conservador. Se pospone hasta que no haya riesgo de romper usos externos o hasta una fase de limpieza dedicada.
- Mover constantes una a una: descartado porque prolonga la refactorizacion sin aportar seguridad adicional.

## 2026-06-20 - Mover runtime Docker local a `rainmapper-local`

### Decision
Mover los ficheros especificos del Docker local a `rainmapper-local/` y mantener wrappers compatibles en la raiz para no romper comandos habituales.

Quedan en `rainmapper-local/`:

- `Dockerfile`
- `docker-compose.yml`
- `run.sh`
- `local_all.sh`
- `local_maps.sh`
- `local_update.sh`

La raiz conserva `local_all.sh`, `local_maps.sh`, `local_update.sh` y `run.sh` como wrappers, y `docker-compose.yml` como include de compatibilidad. No se conserva `Dockerfile` en raiz para evitar builds directos incorrectos con `docker build .`; la ruta canonica es `rainmapper-local/Dockerfile`.

### Motivo
Avanzar la fase 5 hacia la estructura `core/app/local` sin tocar todavia la imagen de Home Assistant ni la logica de descarga. Esto separa responsabilidades de carpetas sin mezclarlo con cambios funcionales.

### Alternativas consideradas
Mover tambien la app HA en el mismo paso, eliminar wrappers de raiz inmediatamente, o mantener todo el runtime local en raiz hasta una reestructuracion completa.

### Consecuencias
Los comandos antiguos desde raiz siguen funcionando, pero la ubicacion canonica del runtime local pasa a ser `rainmapper-local/`. La fase siguiente puede centrarse en mover mas codigo compartido a `rainmapper_core/` sin arrastrar Docker local en la raiz.

### Ficheros afectados
- `rainmapper-local/`
- `Dockerfile`
- `docker-compose.yml`
- `run.sh`
- `local_all.sh`
- `local_maps.sh`
- `local_update.sh`
- `docs/core-refactor.md`
- `docs/architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Implementada en alcance conservador. Pendiente de validacion final y commit.

## 2026-06-20 - Mantener estructura hibrida, pero mover librerias internas por fuente

### Decision
Mantener de momento la estructura actual del repositorio:

- Scripts/entrypoints locales en la raiz.
- Paquete compartido progresivo en `rainmapper_core/`.
- Paquete de Home Assistant en `rainmapper-app/`.
- Copia operativa empaquetada en `rainmapper-app/app`, sincronizada desde la raiz.

Modificacion posterior de la misma fase: mover las librerias internas acopladas a fuentes dentro de `rainmapper_core/sources/`:

- `sodapy_local/` -> `rainmapper_core/sources/sodapy_local/`
- `meteoclimatic_local/` -> `rainmapper_core/sources/meteoclimatic_local/`
- `util/` -> `rainmapper_core/sources/wunderground/`

### Motivo
La estructura no es la ideal a largo plazo, pero funciona como transicion segura. Cambiar ahora carpetas, imports, Dockerfiles y contexto de build de Home Assistant en el mismo bloque aumentaria el riesgo sin aportar una mejora funcional inmediata.

El build de HA y el fallback de GitHub Actions usan `rainmapper-app` como contexto Docker. Hacer que la imagen copie directamente ficheros desde la raiz requeriria cambiar ese flujo y podria afectar instalacion/publicacion en HA, asi que esa parte se mantiene sin cambios.

Mover las librerias completas por fuente reduce duplicidad y aclara donde viven los clientes/helpers de ingesta sin partir todavia la logica de `Rainmapper.py`. Se evita mover constantes o funciones una por una.

### Alternativas consideradas
Reorganizar ya el repositorio hacia una estructura tipo `src/`, dejar las librerias internas en raiz hasta el refactor completo de `Rainmapper.py`, o cambiar el Dockerfile de HA para construir desde la raiz del repo.

### Consecuencias
La duplicidad fisica raiz/app HA se mantiene por ahora, pero queda controlada operativamente con `scripts/sync-manifest.sh`, `scripts/sync-app-files.sh` y `scripts/smoke-test.sh`.

La reorganizacion global de carpetas queda aplazada hasta que el core este mas separado y haya mas cobertura alrededor de `Rainmapper.py`. Las librerias de fuente ya no deben importarse desde rutas top-level antiguas.

### Ficheros afectados
- `scripts/sync-manifest.sh`
- `scripts/sync-app-files.sh`
- `scripts/smoke-test.sh`
- `rainmapper_core/sources/`
- `Rainmapper.py`
- `docs/core-refactor.md`
- `docs/architecture.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Confirmada como criterio conservador para cerrar Fase 3 inicial.

## 2026-06-19 - Upsert incremental por estacion y dia

### Decision
Actualizar los historicos `Data/*_incremental.csv` con una regla comun en `rainmapper_core/incremental_upsert.py`: la identidad logica de una lectura diaria es `Codi Estació` + `Data Local`.

La fila nueva manda para todos los valores no nulos. Si una descarga nueva trae `NaN` en una columna, se conserva el valor antiguo no nulo de esa misma estacion/dia.

### Motivo
El patron anterior combinaba `csv_old.update(csv)` por `Codi Estació` + `Data Local` con un `merge` posterior por todas las columnas. Eso evitaba duplicados exactos, pero podia dejar duplicados logicos cuando una fila nueva tenia `NaN` en temperatura/humedad y la antigua tenia valores. Se detecto en Meteocat con datos reales copiados de HA: 28 filas duplicadas por clave, algunas recientes de junio de 2026.

### Alternativas consideradas
Mantener `merge` por todas las columnas, hacer append puro, quedarse siempre con la fila mas completa o migrar ya a SQLite/Parquet.

### Consecuencias
El CSV sigue siendo el formato persistente, pero la semantica de actualizacion queda explicita y testeada. Se limpian duplicados existentes cuando el incremental se vuelve a guardar. La migracion a SQLite/Parquet queda pospuesta hasta que haya una razon clara de rendimiento, consulta o integridad.

### Ficheros afectados
- `rainmapper_core/incremental_upsert.py`
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `tests/test_incremental_upsert.py`

### Estado
Implementada y validada localmente con datos copiados de HA. `MAX_THREADS=3 ./local_update.sh` termino con exit code 0; Meteocat quedo en 316685 filas y 0 duplicados por clave; Meteoclimatic y Wunderground quedaron con 0 duplicados. `MODE=maps`, tests unitarios y `./scripts/smoke-test.sh` pasaron correctamente. Validada tambien en HA `0.2.77`: `Run update` termino con exit code 0, Meteocat quedo en 316685 filas y `Generate maps` publico visores con `v=0.2.77`.

## 2026-06-19 - Medir duraciones por fuente con temporizadores locales

### Decision
Guardar duraciones reales por fuente en `Data/source_status.json` usando temporizadores locales por proceso, y mostrarlas en la webUI de Home Assistant. Para Meteocat se guardan ademas subtiempos de metadata, condiciones, precipitacion, merge y guardado.

MapLibre no debe mostrar tiempos de proceso; el visor solo necesita estado operativo por fuente para saber si los datos publicados son frescos, degradados o desconocidos.

### Motivo
Al ejecutar fuentes en paralelo, los logs basados en `start_count()`/`end_count()` no son metricas fiables porque usan un temporizador global compartido. En el log de HA `0.2.75`, Meteocat mostraba subtiempos y un supuesto final incoherentes porque otros hilos podian pisar el temporizador.

### Alternativas consideradas
Seguir interpretando los tiempos del log, rehacer todo el sistema de logging, o mostrar todas las metricas tambien en MapLibre.

### Consecuencias
La webUI pasa a ser el sitio operativo para comparar duraciones por fuente y diagnosticar cuellos de botella. Los logs antiguos siguen siendo utiles como trazas humanas, pero no como base para decisiones de rendimiento cuando hay hilos.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/app/web_server.py`
- `docs/codex-handoff.md`
- `docs/architecture.md`
- `docs/todo.md`

### Estado
Implementada y validada en Docker local con `MAX_THREADS=2 ./local_update.sh`: `source_status.json` incluye duraciones reales para Meteoclimatic, Meteocat y Wunderground, y subtiempos para Meteocat. Pendiente de validar visualmente en HA tras bump/publicacion.

## 2026-06-19 - Extraer Tomap de forma conservadora

### Decision
Crear `tomap_builder.py` como script independiente para reconstruir CSV `Tomap` desde historicos incrementales `Data/`, y usarlo en `MODE=maps`/`Generate maps` antes de generar Bokeh y GeoJSON.

Modificacion del 2026-06-19: tras validar `Generate maps` en HA `0.2.74`, se retira el bloque ejecutable inline de generacion `Tomap` de `Rainmapper.py`. Despues de validar `Run all` y la actualizacion local de incrementales, se eliminan tambien los helpers legacy `create_grouped` y `create_last_rains` de `Rainmapper.py`.

### Motivo
Permite regenerar mapas y GeoJSON tras cambios de formato o de `last_rains_history` sin descargar datos nuevos ni ejecutar un `Run all`. Mantener `Rainmapper.py` intacto reduce el riesgo inicial porque el flujo historico de `Run all` sigue disponible mientras se valida el nuevo builder.

### Alternativas consideradas
Eliminar directamente el bloque `Tomap` de `Rainmapper.py`, importar funciones desde `Rainmapper.py`, o esperar a una separacion completa del core en paquete reutilizable.

### Consecuencias
La ruta activa de generacion `Tomap` pasa a ser `tomap_builder.py`. `Rainmapper.py` queda centrado en descarga, historicos y estado por fuente.

### Ficheros afectados
- `tomap_builder.py`
- `run.sh`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `scripts/sync-app-files.sh`
- `tests/test_tomap_builder.py`

### Estado
Implementada. `Run all` local queda validado con `local_all.sh`, `Generate maps` queda validado en HA, y la limpieza de helpers legacy queda validada con `MAX_THREADS=3 ./local_update.sh`, comprobando que las descargas actuales quedan contenidas en sus incrementales.

## 2026-06-18 - No basar una app comercial en Wunderground sin acuerdo escrito

### Decision
Mantener Wunderground como fuente operativa de uso propio por ahora, pero no considerarlo una fuente valida para una futura app comercial sin permiso/acuerdo escrito de The Weather Company.

### Motivo
La API PWS/Data Feed oficial de The Weather Company requiere API key y el pricing publico de Weather Data APIs muestra un plan Standard de 500 USD/mes, con enfoque enterprise, lo que no encaja con el proyecto actual. Ademas, las condiciones de uso de TWC/Wunderground consultadas el 2026-06-18 limitan el uso general de los servicios y el PWS Data Feed a uso personal/no comercial, prohiben copiar/monitorizar datos mediante scrapers para fines comerciales o no autorizados sin permiso escrito, y exigen acuerdo separado para uso comercial del Data Feed.

### Alternativas consideradas
Usar la API PWS oficial de The Weather Company, usar scraping HTML de Wunderground como fuente comercial, buscar endpoints no oficiales usados por la web, sustituir Wunderground por fuentes con licencia compatible o negociar derechos.

### Consecuencias
La optimizacion de Wunderground puede seguir teniendo sentido para uso privado y para la instalacion actual, pero la arquitectura comercial futura debe prever retirar Wunderground, reemplazarlo por otra fuente o negociar licencia. Cualquier investigacion de endpoints no oficiales queda como opcion tecnica de alto riesgo y no como base comercial.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper_core/sources/wunderground/`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/decisions.md`

### Estado
Confirmada como restriccion de estrategia. No implica cambios de codigo inmediatos.

## 2026-06-18 - Permitir update degradado por fuente con estado explicito

### Decision
Si una fuente completa falla durante `update`, Rainmapper intenta continuar usando su incremental previo y marca la fuente como `STALE` en `Data/source_status.json`. Si no hay incremental utilizable, la marca como `NOK`. La webUI de Home Assistant muestra estado y exit code por fuente.

Modificacion del 2026-06-18: el exit code global debe distinguir tres estados: `0` exito completo, `2` exito degradado con al menos una fuente habilitada usable y `1` fallo total/no recuperable. `Run all` debe continuar a `maps` cuando `update` devuelve `2`, pero conservar `2` como resultado final.

### Motivo
Un fallo temporal de Meteocat, Meteoclimatic o Wunderground no deberia impedir publicar datos actualizados de las otras fuentes. Al mismo tiempo, no se deben publicar mapas parciales o con datos reutilizados sin una senal visible.

### Alternativas consideradas
Mantener el fallo global inmediato ante cualquier excepcion de fuente, o silenciar el fallo y publicar mapas sin trazabilidad.

### Consecuencias
Los mapas pueden combinar datos frescos con incrementales previos si una fuente cae, pero la webUI deja trazabilidad visible. MapLibre muestra badges de estado por fuente cuando `source_status.json` esta publicado. El exit code `2` permite automatizaciones y webUI distinguir exito degradado sin tratarlo como fallo total.

### Ficheros afectados
- `Rainmapper.py`
- `rainmapper-app/app/Rainmapper.py`
- `rainmapper-app/app/web_server.py`
- `rainmapper-app/CHANGELOG.md`

### Estado
Implementada parcialmente en `0.2.71` y ampliada con semantica global `0/2/1` tras la decision del 2026-06-18; pendiente de validacion HA con fallo real o simulado.

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
Bokeh es la referencia historica. Leaflet funciona bien en movil segun validacion manual/reportada por el usuario; pendiente de confirmacion automatizada. MapLibre permite mapas vectoriales mas nitidos y desde `0.2.47` tambien puede cubrir las capas raster Hybrid y Topographic que antes estaban solo en Leaflet. Desde `0.2.48`, MapLibre tambien prueba Satellite+, combinando imagen Esri con orientacion vectorial OpenFreeMap.

### Alternativas consideradas
Eliminar Bokeh inmediatamente o sustituir Leaflet por MapLibre de golpe.

### Consecuencias
Hay mas mantenimiento, pero se puede comparar comportamiento y calidad antes de migrar. MapLibre ya esta validado manualmente como funcional en movil segun reporte del usuario; pendiente de confirmacion automatizada. Modificado en `0.2.47`: MapLibre incorpora Hybrid raster por defecto y Topographic raster, manteniendo los estilos vectoriales. Modificado en `0.2.48`: se descarta Tracestrack por ahora porque requiere app key para vector maps; el coste/condiciones exactas quedan pendientes de confirmar si se retoma. Se prueba Satellite+ con OpenFreeMap sobre imagen Esri. Modificado en `0.2.53`: MapLibre queda como visor principal recomendado tras validacion manual en HA/iPhone; Leaflet sigue publicado como fallback.

### Ficheros afectados
- `Rainmapper_Client.py`
- `tomap_to_geojson.py`
- `leaflet-viewer/`
- `maplibre-viewer/`
- `rainmapper-app/app/web_server.py`

### Estado
Confirmada, revisable. Modificada el 2026-06-17 para reflejar que MapLibre ya funciona bien en movil segun validacion manual/reportada por el usuario, que se mantienen publicados Leaflet y MapLibre, y que MapLibre `0.2.53` pasa a ser el visor principal recomendado. Leaflet queda como fallback.

## 2026-06-17 - Retirar ruta legacy rainmapper-mobile

### Decision
Dejar de publicar `/local/rainmapper-mobile` desde la app de Home Assistant.

### Motivo
La ruta legacy ya no se utiliza. Cloudflare tenia redirecciones hacia `/local/rainmapper-leaflet` y `/local/rainmapper-maplibre` segun reporte del usuario. Modificado por la decision del 2026-06-21: MapLibre debe exponerse mediante `/protected/maplibre/index.html`; Leaflet se mantiene en `/local/rainmapper-leaflet` como fallback.

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
- `rainmapper_core/viewers/leaflet-viewer/app.js`
- `rainmapper_core/viewers/maplibre-viewer/app.js`

### Estado
Confirmada.

## 2026-06-18 - Usar terreno 3D en MapLibre con DEM externo

### Decision
Anadir `3D terrain`, apagado por defecto, en MapLibre usando una fuente externa Terrarium/Mapzen como `raster-dem`. Modificado el 2026-06-18: tras validacion manual en local, HA e iPhone, deja de considerarse prototipo experimental y queda como funcionalidad definitiva.

### Motivo
MapLibre permite inclinar/rotar la camara, pero para relieve real necesita tiles DEM codificados. Los mapas actuales Satellite+, Hybrid, Topographic y Liberty no contienen elevacion usable por si mismos. El fichero local `Iberia_HighResolution.CDEM` no fue reconocido por GDAL y Land no permitio exportarlo correctamente durante una prueba manual fuera del repo; pendiente de confirmar si se retoma esa via.

### Alternativas consideradas
Incluir un DEM dentro de la imagen Docker, convertir primero datos IGN/CNIG/Copernicus, usar el CDEM de Land/TwoNav o no probar 3D.

### Consecuencias
No se aumenta el tamano de la imagen Docker. La opcion queda dependiente de un proveedor externo; si esa dependencia falla, rinde mal o se quiere mas control, se estudiara generar tiles DEM propios y servirlos fuera de la imagen, por ejemplo desde `/config/www` o Cloudflare R2.

### Ficheros afectados
- `maplibre-viewer/`
- `rainmapper-app/app/maplibre-viewer/`
- `docs/codex-handoff.md`
- `docs/architecture.md`
- `docs/todo.md`

### Estado
Funcionalidad definitiva, apagada por defecto. Validacion manual/reportada en local, HA e iPhone; pendiente solo de observacion operativa de rendimiento/dependencia externa.

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

## 2026-06-17 - Usar Wunderground con un thread por defecto en RPi (fecha aproximada; reemplazada el 2026-06-20)

### Decision
Mantener `max_threads: 1` por defecto.

Modificacion 2026-06-20: esta decision queda reemplazada. Tras pruebas locales comparativas y observacion nocturna de schedules en Home Assistant/RPi sin problemas reportados, `max_threads: 3` pasa a ser el valor operativo recomendado. `max_threads: 1` queda como modo conservador de diagnostico si aparecen timeouts, errores de Wunderground o carga excesiva.

### Motivo
La RPi no debe cargarse excesivamente. El scraper es el cuello de botella, pero estabilidad y baja carga pesan mas que paralelizar agresivamente.

### Alternativas consideradas
Subir threads para acelerar scraping.

### Consecuencias
La ejecucion completa tarda mas, pero la carga es estable. Se anaden metricas para entender donde optimizar. El rendimiento actual reportado por el usuario es aceptable: update completo + generacion de mapas tarda unos 7 minutos; pendiente de confirmar automaticamente. Por eso, cambios de timeout/observabilidad quedan en baja prioridad hasta acumular mas datos.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `docker-compose.yml`
- `Rainmapper.py`

### Estado
Reemplazada el 2026-06-20 por `max_threads: 3` como valor operativo recomendado.

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
Un solo patron fijo en `rainmapper_core/config/const.py`.

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
No guardar API keys reales en Git. Google se configura por variables/opciones. Modificada el 2026-06-18: Jawg Maps queda retirado y ya no se configura.

### Motivo
Evitar exposicion de credenciales. Ya hubo una alerta historica por una Google API key antigua.

### Alternativas consideradas
Hardcodear claves en scripts o HTML.

### Consecuencias
Cada instalacion debe configurar sus propias claves. En mapas cliente, tokens de tiles pueden ser visibles en navegador y deben restringirse por dominio si el proveedor lo permite; por esa razon se evita mantener proveedores opcionales con token cliente si no aportan valor claro.

### Ficheros afectados
- `rainmapper_core/config/const.py`
- `rainmapper-app/config.yaml`
- `rainmapper_core/viewers/leaflet-viewer/config.js`
- `rainmapper_core/viewers/maplibre-viewer/config.js`

### Estado
Confirmada, modificada para retirar Jawg.

## 2026-06-18 - Retirar Jawg Maps

### Decision
Eliminar las capas Jawg Street/Terrain de Leaflet y MapLibre, y retirar `jawgmaps_api_key`/`JAWGMAPS_API_KEY` de la configuracion.

### Motivo
MapLibre ya cubre el uso actual con Satellite+, Hybrid, Topographic, Liberty y el prototipo 3D. Jawg anadia una API key visible en cliente, dudas de uso/licencia y complejidad de soporte sin aportar valor suficiente.

### Alternativas consideradas
Mantener Jawg como capa opcional o investigar restricciones de token por dominio antes de decidir.

### Consecuencias
Los selectores de mapas quedan mas simples y no hay token Jawg que gestionar. Si en el futuro se necesita otro proveedor con clave cliente, se documentara como nueva decision y se evaluara licencia, costes y restricciones de dominio.

### Ficheros afectados
- `leaflet-viewer/`
- `maplibre-viewer/`
- `docker-compose.yml`
- `rainmapper-app/config.yaml`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `README.md`
- `rainmapper-app/README.md`
- `rainmapper-app/DOCS.md`

### Estado
Confirmada en `0.2.69`.

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
Cloudflare forma parte del acceso externo actual segun reporte del usuario; pendiente de confirmar fuera del repositorio. Encaja con artefactos GeoJSON estaticos/cacheables. Workers evita operar un VPS en la primera fase. React Native permite una base comun iOS/Android y MapLibre alinea la app con el visor principal recomendado del proyecto.

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
Los updates de HA pasan a depender de que exista en GHCR la imagen de la version correspondiente antes de actualizar en HA. El paquete GHCR debe ser accesible para Home Assistant; si queda privado, habra que hacerlo publico o configurar autenticacion. La mejora de velocidad de instalacion/update en RPi fue validada manualmente por el usuario; pendiente de confirmacion automatizada. GitHub Actions con cache no resulto util segun esa observacion manual, por lo que se reemplazo como flujo normal por build/push local desde Mac.

### Ficheros afectados
- `.github/workflows/build-rainmapper-app.yml`
- `rainmapper-app/config.yaml`
- `rainmapper-app/Dockerfile`
- `rainmapper-app/CHANGELOG.md`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`

### Estado
Implementada en `0.2.57`. La descarga de `ghcr.io/cginebrosa/rainmapperha:0.2.57` sin build local fue validada manualmente por el usuario; pendiente de confirmacion automatizada. Modificada en `0.2.58` para anadir cache Buildx/GHA en futuras Actions. Reemplazada como flujo normal en `0.2.60` por build/push local con Buildx antes del commit de version, dejando GitHub Actions como fallback manual.

## 2026-06-17 - Publicar imagen HA con Buildx local antes del commit de version

### Decision
Usar `scripts/build-push-ha-image.sh` como flujo normal para publicar desde el Mac la imagen multi-arch `ghcr.io/cginebrosa/rainmapperha:<version>` antes de hacer commit/push del cambio de version visible para Home Assistant. GitHub Actions queda disponible solo como workflow manual de fallback.

### Motivo
GitHub Actions con cache siguio tardando alrededor de 7 minutos y Home Assistant detecta el update en cuanto ve `config.yaml`, aunque la imagen todavia no este publicada. Publicar localmente primero elimina esa ventana y aprovecha que el Mac construye mas rapido que la Raspberry Pi.

### Alternativas consideradas
Mantener GitHub Actions automatico y esperar a que termine, construir en Home Assistant, o subir imagen manual sin script versionado.

### Consecuencias
El flujo de release exige login Docker contra GHCR en el Mac y disciplina de publicar imagen antes de subir el commit de version. A cambio, HA no deberia ofrecer un update cuyo tag de imagen aun no exista. GitHub Actions deja de ejecutarse automaticamente en cada push de `rainmapper-app`. El script publica la etiqueta versionada y `latest`; Home Assistant usa la etiqueta versionada. Desde el ajuste posterior a `0.2.60`, el script limpia etiquetas locales versionadas antiguas del mismo repositorio y conserva por defecto las dos ultimas mas `latest`.

### Ficheros afectados
- `scripts/build-push-ha-image.sh`
- `.github/workflows/build-rainmapper-app.yml`
- `README.md`
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/decisions.md`

### Estado
Implementado en `0.2.60`: Home Assistant instalo la imagen publicada localmente desde GHCR sin build local segun validacion manual del usuario; pendiente de confirmacion automatizada. Modificado despues de validar `0.2.60` para anadir limpieza local de etiquetas antiguas al script de publicacion.

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
Implementada en `0.2.58`; modificada en `0.2.59` para clasificar Meteocat solo con codigos de longitud 2 y avisar por `Unknown`. La inferencia esta cubierta por `tests/test_tomap_to_geojson.py`; la validacion visual en Home Assistant/iPhone fue reportada por el usuario y queda pendiente de automatizar.

## 2026-06-22 - Cerrar exposicion publica manteniendo actualizaciones HA

### Decision
Hacer privado el repo GitHub `cginebrosa/RainmapperHA`, mantener accesible el paquete GHCR necesario para Home Assistant, proteger los fallbacks externos con Cloudflare Access y endurecer el dominio con redireccion HTTPS y HSTS.

### Motivo
Antes de compartir el visor con companeros, se reviso el riesgo de exposicion. El repo publico permitia ver codigo, rutas y logica de descarga, incluyendo Wunderground. Ademas, antes de proteger el fallback externo, `https://maplibre.nomentero.com/local/rainmapper-maplibre/data/01d.geojson` devolvia `200` con GeoJSON sin login. Para uso privado y pruebas con terceros, la UI principal debe ir por login Rainmapper y los fallbacks no deben saltarse la autenticacion.

### Alternativas consideradas
Dejar el repo publico, borrar el fallback externo, hacer privado tambien GHCR, o retirar todos los subdominios fallback del tunel Cloudflared. Se descarta hacer privado GHCR por ahora porque Home Assistant descarga `ghcr.io/cginebrosa/rainmapperha:<version>` sin autenticacion de registry. Se descarta retirar los fallbacks porque el usuario quiere conservarlos como emergencia si falla la ruta principal.

### Consecuencias
El codigo deja de estar disponible publicamente y un tercero no puede anadir facilmente el repo como add-on repository en Home Assistant. Home Assistant puede seguir descargando la imagen versionada mientras GHCR siga accesible. Los fallbacks `leaflet.nomentero.com` y `maplibre.nomentero.com` siguen existiendo, pero requieren Cloudflare Access, igual que `router.nomentero.com`. HSTS con `includeSubDomains` obliga a que los subdominios actuales y futuros del dominio sigan funcionando por HTTPS. Si se quiere hacer privado GHCR en el futuro, habra que resolver autenticacion de registry desde HA o aceptar publicar temporalmente cada version.

### Verificaciones
- HTTP redirige a HTTPS para `rainmap.nomentero.com` y subdominios revisados.
- HSTS activo con `strict-transport-security: max-age=2592000; includeSubDomains`.
- `x-content-type-options: nosniff` presente.
- `router.nomentero.com` redirige a Cloudflare Access.
- `leaflet.nomentero.com/local/rainmapper-leaflet/index.html` y `data/01d.geojson` redirigen a Cloudflare Access.
- `maplibre.nomentero.com/local/rainmapper-maplibre/index.html` y `data/01d.geojson` redirigen a Cloudflare Access.
- `rainmap.nomentero.com/protected/maplibre/data/01d.geojson` devuelve `401 Authentication required` sin sesion.
- `ghcr.io/cginebrosa/rainmapperha:0.2.100` sigue resolviendo manifest multi-arch `linux/amd64` y `linux/arm64` despues de la limpieza.

### GHCR
Se borraron 179 versiones/entradas antiguas del paquete `rainmapperha` en GHCR. Quedan `0.2.100`, `latest` y cuatro entradas auxiliares sin tag asociadas al mismo push multi-arch. No borrar la version activa ni sus entradas auxiliares mientras `rainmapper-app/config.yaml` declare `0.2.100`. Para futuras releases HA, la limpieza remota de GHCR pasa a ser parte del procedimiento estandar despues de validar la nueva version en HA: conservar solo la ultima version validada, `latest` y las entradas auxiliares del mismo push multi-arch.

### Ficheros afectados
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/decisions.md`

### Estado
Completado operacionalmente el 2026-06-22. No hubo cambios de codigo ni de version HA.
