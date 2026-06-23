# TODO

Nota operativa: ejecutar tareas, tests y commits solo desde `/Users/carlosginebrosa/Developer/RainmapperHA`. No usar la copia antigua de iCloud/Mobile Documents.

## Proximo paso recomendado
`0.2.101` queda validada manualmente en HA: la WebUI `Users` refresca y busca correctamente sin refrescar el navegador. `0.2.104` corrigio la publicacion experimental AEMET tras el fallo de merge Tomap. `0.2.105` queda publicada en GHCR con bounds dinamicos en MapLibre, contador `Invalid: N` y temperatura/humedad AEMET agregada a max/min diarios (`sha256:02240d108c7c4c7b166091ea8f4342c7af4fe017fd4d32575efdecc6bcd0ad9c`); el usuario reporto que en HA ya aparecen todas o casi todas las estaciones AEMET en la ruta experimental. `0.2.106` queda publicada en GHCR con atribuciones visibles por fuente en MapLibre (`sha256:47213a34f1ff8d0a9fa7440ee24ed6e2ec694bc62fef86d115865465cecdf29b`). `0.2.107` queda publicada en GHCR con ajuste visual del prefijo AEMET y creditos AEMET/Meteoclimatic (`sha256:be6272220c393a3f36fe885218c590e87d9cd09c0be54bd77275e9388d8edaf2`). `0.2.108` queda publicada y validada/dada por buena en HA con vista inicial MapLibre por dispositivo, fix de duplicados diarios AEMET por tipos mixtos en `local_date`, y `stations` en `source_status.json` (`sha256:2a39a36f5b5098e16eb73d7ae08f6897f91a0973053544a485c396e7c329d62a`). `0.2.109` queda publicada en GHCR con AEMET integrado en el Tomap/GeoJSON estandar del visor protegido y la ruta experimental `/local/rainmapper-maplibre-aemet` desactivada como rollback temporal (`sha256:90daf3d1fb8006ca33b0102b1a098ddd7399116700b77926109579ab5e5476a9`). `0.2.110` queda publicada en GHCR con redaccion de atribuciones AEMET/Meteocat mas clara: datos elaborados por Rainmapper (`sha256:217c1c1c47484f1725ce842a8a40fc9da24548dee98c4e0e3e2af817716f54e1`). `0.2.111` queda publicada y validada/dada por buena en HA con Meteoclimatic/Wunderground alineados al criterio de informacion elaborada por Rainmapper (`sha256:f962cb744e41200badbe65786b8182f6c2ac6fe567e4e9e3415708ce4a250112`). `0.2.112` queda publicada en GHCR con ayuda `?` de MapLibre y documentacion HA actualizada (`sha256:37f841c9004ab879227d2cc67ee6f836d1e8c4adc14ae609ba9b7cf41b3637f7`), pendiente de validacion real en HA. El 2026-06-24 se limpio GHCR remoto tras validar `0.2.111`; no limpiar `0.2.111` hasta confirmar que `0.2.112` arranca correctamente. Siguiente paso recomendado: subir el commit de `0.2.112`, hacer el repo publico temporalmente para que HA detecte la version, validar en HA y volver a privado.

## Prioridad alta
- [x] Corregir upsert de historicos incrementales por estacion/dia
  - Contexto: los incrementales no son append puro; las fuentes pueden reenviar una estacion/dia con valores corregidos o campos complementarios incompletos. El patron anterior `update` + `merge` por todas las columnas podia dejar duplicados logicos si la fila nueva traia `NaN`.
  - Ficheros relacionados: `rainmapper_core/incremental_upsert.py`, `rainmapper_core/rainmapper.py`, `tests/test_incremental_upsert.py`.
  - Criterio de aceptacion: una sola fila por `Codi Estació` + `Data Local`; valores nuevos no nulos mandan; `NaN` nuevo conserva valor antiguo no nulo.
  - Estado: resuelto y validado localmente con datos copiados de HA. Meteocat paso de 28 filas duplicadas a 0; Meteoclimatic y Wunderground se mantuvieron sin duplicados. `local_update.sh`, `MODE=maps`, unit tests y smoke test pasaron. Validado tambien en HA `0.2.77`: `Run update` termino con exit code 0, Meteocat quedo en 316685 filas y `Generate maps` publico correctamente `v=0.2.77`.

- [x] Corregir inconsistencia de version en la app HA
  - Contexto: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile` y `rainmapper-app/CHANGELOG.md` deben avanzar juntos en cada bump de version.
  - Ficheros relacionados: `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: version alineada en metadata HA, labels Docker y changelog.
  - Estado: resuelto.

- [x] Validar MapLibre en movil tras los ultimos ajustes
  - Contexto: MapLibre funciona bien en movil segun validacion manual/reportada por el usuario; se mantiene publicado junto a Leaflet de momento. La `0.2.47` anade capas raster Hybrid/Topographic y requiere validacion visual especifica.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`.
  - Criterio de aceptacion: cambio de capa mantiene estaciones, cambio de periodo conserva vista, popup es usable y no desplaza/molesta.
  - Estado: validado manualmente por el usuario en movil; pendiente de confirmacion automatizada.

- [x] Validar MapLibre raster y Leaflet fallback en HA/iPhone
  - Contexto: MapLibre `0.2.53` incorpora Satellite+ como base por defecto, Hybrid raster, Topographic raster y estilos vectoriales; Leaflet se mantiene como fallback con Topographic/Hybrid.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper_core/viewers/leaflet-viewer/`.
  - Criterio de aceptacion: Hybrid, Topographic y Satellite+ cargan correctamente, el cambio entre capas conserva marcadores, periodo, vista y popup en movil.
  - Estado: validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada. Leaflet queda como fallback publicado.
  - Riesgo si no se hace: decidir retirada de Leaflet sin confirmar que MapLibre cubre bien las capas raster que interesan.

- [x] Mantener sincronizadas raiz y app HA
  - Contexto: antes habia copias de scripts y visores en raiz y dentro de `rainmapper-app/app`.
  - Ficheros relacionados: `rainmapper_core/`, `rainmapper-app/Dockerfile`, `rainmapper-app/app/web_server.py`, `scripts/smoke-test.sh`, `scripts/build-push-ha-image.sh`.
  - Criterio de aceptacion: una unica fuente de verdad para core y visores compartidos; `rainmapper-app/app` solo contiene codigo especifico de HA.
  - Estado: resuelto por refactor core/app/local. HA se construye desde la raiz del repositorio y `scripts/smoke-test.sh` valida que `rainmapper-app/app` no vuelva a contener copias de core.
  - Riesgo residual: el build HA ya no soporta usar `rainmapper-app` como contexto Docker aislado; debe usarse la raiz del repo.

- [x] Proteger el historico CSV antes de cambios de pandas
  - Contexto: `Data/*_incremental.csv` es el valor principal del proyecto.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `Data/`, `/share/rainmapper/Data`, `scripts/backup-data.sh`, `scripts/check-history.py`, `docs/history-safety.md`.
  - Criterio de aceptacion: backup o prueba en directorio temporal antes de cambios que escriban historicos.
  - Estado: resuelto como practica operativa versionada. Antes de cambios que escriban CSV, usar backup/copia temporal y validar con `scripts/check-history.py`.

## Prioridad media

- [x] Incorporar AEMET OpenData como fuente horaria reciente
  - Contexto: el 2026-06-23 se probo con `AEMET_API_KEY` el endpoint oficial `/opendata/api/observacion/convencional/todas`. La llamada global devuelve observaciones horarias recientes de las ultimas 12 horas para todas las estaciones recibidas, con `idema`, `lat`, `lon`, `alt`, `ubi`, `fint` y `prec`. Segun metadatos AEMET, `prec` es la precipitacion acumulada durante los 60 minutos anteriores a `fint`, en mm; `fint` viene en UTC. En pruebas reales se obtuvo un dataset de unas 10k filas, 798 estaciones para la fecha filtrada y lluvia no nula en 23 estaciones. AEMET puede devolver `429 Too Many Requests` si se llama repetidamente durante pruebas.
  - Ficheros relacionados: `rainmapper_core/create_aemet.py`, `rainmapper_core/rainmapper.py`, `rainmapper_core/geocoding.py`, `rainmapper_core/tomap.py`, `rainmapper_core/geojson.py`, `rainmapper-app/config.yaml`, `rainmapper-app/run.sh`, `rainmapper-local/run.sh`, `rainmapper_core/viewers/maplibre-viewer/`, `tests/test_create_aemet.py`, `tests/test_tomap_builder.py`, `tests/test_tomap_to_geojson.py`.
  - Plan original ya ejecutado:
    1. Configuracion: anadir opcion/env para `AEMET_API_KEY` y flag de fuente `aemet` sin hardcodear secretos ni imprimir la clave.
    2. Cliente: hacer una sola llamada por ejecucion a `/observacion/convencional/todas`, leer la URL temporal `datos`, parsear tolerando caracteres no UTF-8 en `ubi`, y no llamar nunca estacion por estacion.
    3. Normalizacion: convertir cada registro horario con `prec` numerica a schema Rainmapper usando codigo estable `AEMET:{idema}` o equivalente que no colisione con fuentes existentes; preservar `fint` UTC como instante de fin de periodo horario.
    4. Historico: guardar filas horarias AEMET en un historico propio o adaptar el modelo incremental con identidad `source + idema + fint`; no forzar `Data Local` diaria sin decidir antes como se acumulan horas UTC frente a dias locales.
    5. Acumulados: construir acumulados de 1/7/14/21/30/60/90 dias desde las horas guardadas, dejando explicita la zona horaria. Recomendacion inicial: almacenar todo en UTC y definir el corte de periodos con una conversion controlada a la zona operativa solo en el agregador, no durante descarga.
    6. Degradacion: si AEMET devuelve `429`, timeout o error temporal, marcar fuente como `STALE`/`NOK` segun haya historico previo y continuar `Run all` con el resto de fuentes.
    7. Backfill opcional: estudiar despues `/valores/climatologicos/diarios/.../todasestaciones` para completar dias cerrados. Ese endpoint trae `prec` diario como texto con coma decimal, puede publicarse con retraso, no trae coordenadas y requiere unir con `inventarioestaciones/todasestaciones`.
    8. Creditos legales: cuando una estacion venga de AEMET, mostrar en su ficha `Fuente: AEMET` e indicar que Rainmapper elabora la informacion a partir de datos de la Agencia Estatal de Meteorologia. En el panel de informacion/creditos de MapLibre, anadir una referencia agregada a AEMET cuando haya datos AEMET cargados. Si el dato original trae fecha de actualizacion, mostrarla o conservarla en metadatos. Desde la revision de atribuciones del 2026-06-23, MapLibre muestra tambien atribucion por fuente para Meteocat, Meteoclimatic y Wunderground, y ya no muestra la fila generica `Source:` en las fichas.
  - Seguridad de historicos: antes de implementar escritura real, seguir `docs/history-safety.md`: backup o copia temporal, prueba offline con fixtures, `scripts/check-history.py` antes/despues y no ejecutar contra `/share/rainmapper/Data` sin validacion.
  - Criterio de aceptacion: con una sola llamada global AEMET por `Run all`, se anaden o actualizan observaciones horarias deduplicadas; las estaciones AEMET aparecen en `Tomap`/GeoJSON con `Source=AEMET`; los acumulados no mezclan mal UTC/dia local; `429` no rompe el pipeline; MapLibre muestra atribucion AEMET en fichas de estacion y creditos generales cuando aplica; tests cubren parseo, deduplicado, acumulacion y fallo degradado.
  - Estado: implementado, publicado y validado/dado por bueno en HA hasta `0.2.111` para el alcance actual. Existe `rainmapper_core/create_aemet.py`, ejecutable como `python -m rainmapper_core.create_aemet`, que genera `Aemet.csv`, `Aemet_current_daily.csv`, `Aemet_hourly_incremental.csv`, `estacions_aemet.csv` y `Aemet_incremental.csv`. El historico horario AEMET guarda `prec` como `rain_mm` y, desde `0.2.105`, tambien `ta` como `temp_celsius` y `hr` como `humidity_percent` cuando AEMET los entrega; el diario calcula `max_temp_celsius`, `min_temp_celsius`, `max_humidity_percent` y `min_humidity_percent` desde las horas disponibles. El catalogo `estacions_aemet.csv` se rellena con identificador, nombre, altitud y coordenadas de AEMET, y preserva `Comarca`, `Municipi` y `Provincia` cuando las coordenadas no cambian. El reverse geocoding se ha extraido a `rainmapper_core/geocoding.py` y ahora lo comparten las fuentes existentes y AEMET: cuando una estacion AEMET es nueva, le faltan `Municipi`/`Provincia` o cambian sus coordenadas, se consulta Google Maps usando la misma `GMAP_API_KEY` que el resto de fuentes. `Comarca` no se usa como condicion para reintentar porque Google no la devuelve de forma fiable; si llega, se conserva, pero no debe forzarse. El CLI de AEMET permite `--skip-station-enrichment` solo para pruebas temporales. `create_aemet` y `aemet_api_key` estan anadidos a la configuracion HA/local, con `create_aemet=false` por defecto. `rainmapper_core.rainmapper` puede ejecutar AEMET como cuarta fuente opcional y degradar por el mecanismo general de `source_status.json`. Tras validar `0.2.108` en HA, `0.2.109` integra AEMET en el Tomap/GeoJSON estandar de HA mediante `--include-aemet true`, por lo que `/protected/maplibre/index.html`, Leaflet y Bokeh usan los mismos datos de produccion con AEMET cuando exista `Aemet_incremental.csv`. El publicador experimental `/local/rainmapper-maplibre-aemet/index.html` queda desactivado por flag en codigo y debe retirarse definitivamente cuando la ruta estandar quede estable durante uso real. GeoJSON infiere `AEMET:` como `Source=AEMET`. MapLibre incluye AEMET en el selector de fuentes y atribucion en ficha/panel de creditos. Prueba real de flujo completo en `tmp/aemet-flow-test/` genero 9120 filas horarias, 802 estaciones en `estacions_aemet.csv`, 802 filas diarias, Tomap completo y 7 GeoJSON con `Source=AEMET`, sin tocar historicos reales. Prueba real con reverse geocoding en `tmp/aemet-geocode-test-v2/` genero 802 estaciones enriquecidas: 802/802 con `Municipi`, 800/802 con `Provincia` y 7/802 con `Comarca`; casos revisados: `REUS AEROPUERTO -> Reus`, `BARCELONA AEROPUERTO -> El Prat de Llobregat`. El usuario copio ese `estacions_aemet.csv` enriquecido a `/share/rainmapper/Data` en HA. En `0.2.103`, HA ya ejecuto AEMET cuando `create_aemet=true`, pero fallo la ruta experimental al generar Tomap porque `merge_dataframes()` hacia un `pd.merge` por todas las columnas y pandas rechazo mezclar tipos `object`/`float64` en `max_temp_celsius`; `0.2.104` cambia esa union a `pd.concat(...).drop_duplicates()` y anade test de regresion. Tras probar `0.2.104`, el visor experimental mostraba solo estaciones AEMET dentro del antiguo `DISPLAY_BOUNDS` Catalunya/este; `0.2.105` elimina el recorte regional en MapLibre: el visor solo descarta coordenadas no numericas o fuera del rango geografico valido, encuadra el mapa usando las features cargadas y muestra `Invalid: N` en la cabecera cuando alguna feature queda descartada por coordenadas invalidas. El usuario reporto que con este cambio ya aparecen todas o casi todas las estaciones AEMET en HA. `0.2.106` anade atribuciones visibles por fuente en popups y creditos, y elimina la fila generica `Source:` del popup. En HA `0.2.107`, un `Run all` solo AEMET mostro que `Aemet_current_daily.csv` queda con una fila por estacion, pero `Aemet_incremental.csv` duplicaba estacion/dia al mezclar historico horario leido de CSV con filas nuevas: pandas leia `local_date` como entero desde disco y las filas actuales lo traian como texto. `0.2.108` corrige ese duplicado y queda validada/dada por buena por el usuario. `0.2.109` queda publicada en GHCR; `0.2.110` queda publicada en GHCR con atribuciones AEMET/Meteocat ajustadas a datos elaborados por Rainmapper. `0.2.111` queda publicada y validada/dada por buena en HA con atribuciones Meteoclimatic/Wunderground alineadas al mismo criterio. Pendiente dejar correr unos dias y despues eliminar el publicador experimental.

- [ ] Eliminar definitivamente la ruta/proceso experimental AEMET `/local/rainmapper-maplibre-aemet`
  - Contexto: al pasar AEMET a produccion, el codigo conserva `publish_aemet_experimental_maplibre()` desactivado mediante `PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE = False` como rollback temporal. Esa via fue util durante la implantacion de AEMET como nueva fuente, pero ya no debe quedar como camino paralelo si la ruta estandar sigue estable.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper_core/geojson.py`, documentacion de continuidad.
  - Criterio de aceptacion: tras validar varios ciclos reales con AEMET en `/protected/maplibre/index.html`, retirar el flag, la funcion experimental, rutas temporales `rainmapper-maplibre-aemet`, referencias de WebUI/documentacion y cualquier instruccion operativa que sugiera usar el visor experimental. Mantener solo el pipeline AEMET de produccion (`create_aemet`, Tomap/GeoJSON estandar y fuente `AEMET` en MapLibre).
  - Estado: pendiente deliberado; no quitar todavia para poder reactivar el modo test AEMET si la ruta estandar fallase.

- [ ] Normalizar codigos internos de todas las fuentes con prefijo de origen
  - Contexto: AEMET se normaliza internamente como `AEMET:{idema}` para evitar colisiones y permitir trazabilidad, aunque MapLibre lo muestra sin el prefijo. Las fuentes historicas todavia dependen de inferencias por forma del codigo (`ES...` largo para Meteoclimatic, `I...` para Wunderground, longitud 2 para Meteocat).
  - Ficheros relacionados: historicos `*_incremental.csv`, catalogos `estacions_*.csv`, `rainmapper_core/geojson.py`, `rainmapper_core/tomap.py`, `rainmapper_core/rainmapper.py`, visores y tests.
  - Criterio de aceptacion: definir prefijos estables por fuente, migrar historicos/catalogos con backup y pruebas segun `docs/history-safety.md`, mantener compatibilidad o migracion controlada de `ignore_stations_tomap.txt` y publicar GeoJSON con `Source` sin inferencias fragiles.
  - Estado: mejora futura. No mezclar con la validacion AEMET actual; requiere plan especifico de migracion de historicos.

- [ ] Validar MapLibre protegido en HA/Cloudflare
  - Contexto: la ruta protegida MapLibre ya fue validada manualmente en HA `0.2.82`: `/protected/maplibre/index.html` pide login, `admin` funciona desde Mac+iPhone y un usuario normal queda limitado a un dispositivo. La version `0.2.83` amplia el backend a `users.json` con `username`, `name`, `email`, roles `free/basic/pro/admin` y `max_devices`. El usuario valido en HA que el primer login crea `users.json`; despues se decide retirar por completo el formato antiguo.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper_core/viewers/maplibre-viewer/`, `users.example.json`, `tests/test_web_server_auth.py`, `rainmapper-app/DOCS.md`.
  - Criterio de aceptacion: publicar nueva version HA con `users.json` como unico formato, validar login por `username`, admin ilimitado, usuario `free` limitado por `max_devices`, reutilizacion de dispositivo registrado, gestion WebUI de usuarios/dispositivos desde Ingress/Home Assistant y GeoJSON inaccesible sin sesion. Cloudflared debe apuntar a `http://<HA_IP>:8099` para `rainmap.nomentero.com` y no depender de `/local/rainmapper-maplibre/index.html`. Tras uso real, decidir si se retira el fallback local de MapLibre o si se mantiene como emergencia protegida externamente por Cloudflare Access.
  - Estado: protegido basico validado manualmente en HA `0.2.82`; ampliacion `users.json`/`max_devices` publicada como imagen `ghcr.io/cginebrosa/rainmapperha:0.2.83`; retirada del formato antiguo y WebUI de gestion publicadas en `0.2.84`; correccion del auto-refresh publicada en `0.2.85`; gestion de contrasenas `Set password`/`Reset password` publicada como imagen `0.2.86`. El 2026-06-22 se comprobo la exposicion externa: `rainmap.nomentero.com/protected/maplibre/data/01d.geojson` devuelve `401` sin sesion, HTTP redirige a HTTPS, HSTS esta activo con `includeSubDomains`, y los subdominios fallback `leaflet.nomentero.com`/`maplibre.nomentero.com` quedan detras de Cloudflare Access tambien para GeoJSON. Pendiente de uso real con companeros usando login Rainmapper y de decidir si se retira el fallback local.

- [ ] Observar prueba externa con usuarios reales
  - Contexto: desde el 2026-06-22 hay dos companeros probando la ruta protegida con login Rainmapper. Se han creado cuatro usuarios: usuario propio con rol `admin` y limite configurado de 2 dispositivos; `Diegomovil`, `Diegopc` y `Ramonmovil` con rol `free` y 1 dispositivo cada uno. No se ha avisado a los companeros del limite de dispositivo para observar si comparten credenciales.
  - Ficheros relacionados: `/share/rainmapper/users.json`, `/share/rainmapper/devices.json`, WebUI `Users`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: los usuarios pueden entrar desde su dispositivo previsto; si comparten acceso o cambian de dispositivo/navegador, el bloqueo por `max_devices` queda visible y gestionable desde WebUI Users; no aparecen errores de sesion inesperados ni exposicion de GeoJSON sin login.
  - Estado: prueba en curso. HA ejecuta `Run all` con schedule `01:45 - 05:00 - 08:00 - 11:00 - 14:00 - 17:00 - 20:00 - 23:55`. `0.2.101` quedo validada manualmente para WebUI `Users`; `0.2.111` queda validada/dada por buena en HA con AEMET ya integrado en el visor protegido estandar. Pendiente observar varios ciclos reales y comportamiento de los usuarios externos.

- [x] Cerrar exposicion publica de repo, fallbacks y paquetes antiguos
  - Contexto: antes de compartir el visor con companeros, se reviso la seguridad externa. El repo publico exponia codigo y logica de descarga, y `maplibre.nomentero.com/local/rainmapper-maplibre/data/01d.geojson` llego a responder `200` con GeoJSON sin login antes de proteger el subdominio.
  - Ficheros relacionados: `docs/codex-handoff.md`, `docs/architecture.md`, `docs/decisions.md`; configuracion real en GitHub/GHCR/Cloudflare fuera del repo.
  - Criterio de aceptacion: repo GitHub privado; `rainmap.nomentero.com` fuerza HTTPS y mantiene datos protegidos por login Rainmapper; fallbacks `leaflet` y `maplibre` exigen Cloudflare Access; GHCR conserva solo la imagen actual necesaria para HA.
  - Estado: completado el 2026-06-22 para repo/fallbacks/HTTPS. Repo `cginebrosa/RainmapperHA` privado; HTTP->HTTPS activo; HSTS activo con `max-age=2592000; includeSubDomains`; `x-content-type-options: nosniff` presente; `router`, `leaflet` y `maplibre` redirigen a Cloudflare Access; ruta protegida de datos en `rainmap` devuelve `401` sin sesion. En aquel momento GHCR se limpio borrando 179 versiones/entradas antiguas y conservando `0.2.100`, `latest` y cuatro entradas auxiliares multi-arch. El 2026-06-24 se limpio de nuevo tras validar `0.2.111`; `0.2.112` queda publicada en GHCR pero pendiente de validar, asi que no limpiar `0.2.111` todavia.

- [x] Validar identidad de usuario en cabecera MapLibre
  - Contexto: el visor MapLibre protegido ya recibe `username`, `name`, `email` y `role` en login y en `/auth/session`.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA, tras login y tras recargar una sesion guardada, la cabecera muestra fecha generada y `username (role)` en dos lineas compactas sin romper el layout movil.
  - Estado: implementado y validado manualmente en HA durante las validaciones posteriores hasta `0.2.111`; las capturas de uso muestran `username (role)` en la cabecera protegida. Pendiente solo de cobertura automatizada si se quiere fijar layout por test.

- [x] Ajustar umbral de hover MapLibre
  - Contexto: `0.2.87` muestra temporalmente el nivel de zoom en la cabecera de MapLibre, debajo de `Generated`, para decidir a partir de que zoom conviene activar el hover de estaciones.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: tras probar en HA, confirmar el valor de `HOVER_POPUP_MIN_ZOOM` y retirar el indicador temporal de zoom si ya no hace falta.
  - Estado: publicado en `0.2.95` con umbral `7`; pendiente de validar en HA/movil y retirar el indicador temporal si ya no hace falta.

- [ ] Validar estacion con lluvia mas cercana en popup de terreno MapLibre
  - Contexto: el popup de terreno por pulsacion larga muestra altitud DEM y coordenadas del punto. Para aportar contexto sin reverse geocoding, se anade un bloque `Nearest rainy station` calculado en cliente desde las estaciones cargadas en el mapa para el periodo actual.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA/movil, una pulsacion larga muestra altitud, coordenadas, estacion con lluvia mas cercana, lluvia acumulada del periodo seleccionado, distancia, municipio/provincia de esa estacion y altitud de estacion; si no hay estaciones con lluvia en el mapa, muestra un mensaje explicito.
  - Estado: publicado en `0.2.96`; pendiente de validar en HA.

- [x] Validar settings MapLibre por dispositivo
  - Contexto: el visor MapLibre protegido guarda preferencias por `device_id` dentro de `/share/rainmapper/devices.json`, no en `users.json`, para que cada navegador/dispositivo conserve su configuracion independiente.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`, `tests/test_web_server_auth.py`.
  - Criterio de aceptacion: en HA, cambiar Settings y cerrar el panel guarda `period`, `min_rain_mm`, `map_style`, `language`, `last_rains_history`, `station_sources`, `terrain_enabled`, `terrain_exaggeration` y, solo bajo accion explicita, `map_view`; cambiar periodo desde la barra inferior, mover el mapa normalmente, usar el boton rapido de capas o usar el boton compacto `2D`/`3D` no debe escribir `devices.json`. Al recargar o volver a entrar desde el mismo dispositivo se restauran esos valores desde `devices.json`. Borrar el dispositivo desde la WebUI debe borrar tambien sus preferencias.
  - Estado: validado manualmente por el usuario en HA hasta `0.2.111`. Incluye persistencia por dispositivo en `devices.json`, boton rapido de seleccion de mapa entre `2D`/`3D` y la brujula sin persistir `map_style`, separacion equivalente entre periodo visible de la barra inferior y periodo preferido guardado desde Settings, selector de idioma ES/EN/CA y boton de Settings para guardar la vista actual como predeterminada (`map_view`) sin escribir continuamente al mover el mapa. Cubierto por tests backend de saneado/almacenamiento.

- [x] Validar i18n ES/EN/CA en MapLibre
  - Contexto: se decide no tocar de momento la WebUI HA y aplicar multiidioma solo al visor MapLibre, usando lenguaje de usuario no tecnico: lluvia/mapa/estacion/fuente/relieve.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/translations.json`, `rainmapper-app/app/web_server.py`, `tests/test_web_server_auth.py`, `tests/test_maplibre_translations.py`.
  - Criterio de aceptacion: en HA, cambiar idioma desde Settings actualiza textos visibles de MapLibre en ES/EN/CA, guarda `language` en `devices.json` al cerrar Settings y lo recupera al volver desde el mismo dispositivo. Los cambios rapidos de mapa/periodo/2D-3D fuera de Settings deben mantener el criterio actual de no persistir preferencias.
  - Estado: validado manualmente por el usuario en HA `0.2.99`: el selector de idioma funciona bien, `translations.json` se carga y el idioma queda como setting por dispositivo. Imagen publicada `ghcr.io/cginebrosa/rainmapperha:0.2.99` con digest `sha256:2ebebc6f0da239e22f23e7bb3e1eddddedf61fd1f172a11dcf76d7bdbb8a82b5`.

- [ ] Estudiar visita guiada MapLibre con globos contextuales
  - Contexto: `0.2.112` anade el boton final `?` con ayuda del mapa en ES/EN/CA. Una mejora mas guiada seria mostrar globos breves en el primer login de un dispositivo para explicar controles clave, o permitir lanzar la misma visita a voluntad desde la ayuda.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`, `rainmapper_core/viewers/maplibre-viewer/translations.json`, `rainmapper-app/app/web_server.py`, `tests/test_maplibre_translations.py`.
  - Criterio de aceptacion: definir si la visita aparece automaticamente solo una vez por dispositivo, si se activa manualmente desde el panel `?`, o ambas cosas. Si se persiste el estado, guardarlo por dispositivo en `devices.json` sin bloquear el mapa ni escribir continuamente. Los globos deben ser cerrables, no tapar controles criticos en movil, tener textos ES/EN/CA y quedar documentados en la ayuda del mapa.
  - Estado: idea futura. Priorizar una UX ligera: no convertir la ayuda en un tutorial obligatorio ni molesto para usuarios recurrentes.

- [x] Validar controles compactos MapLibre en movil
  - Contexto: en iPhone, la columna derecha de botones flotantes ocupaba demasiada altura y la leyenda podia acercarse mas al borde izquierdo.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA/movil, los botones de la derecha quedan compactos sin perder facilidad de pulsacion, con separacion visual minima de 1px, margen derecho reducido y paneles laterales de Settings/mapas/creditos correctamente alineados. La leyenda queda mas pegada a la izquierda sin cortarse.
  - Estado: validado manualmente por el usuario en HA `0.2.100`. Incluye botones moviles de 34px, separacion de 1px, margen derecho de 6px, leyenda a 4px del margen izquierdo y etiquetas compactas `1d`/`7d`/... en la barra inferior. Imagen publicada `ghcr.io/cginebrosa/rainmapperha:0.2.100` con digest `sha256:03b2d0cc42a08069bddbb7f6a4e7cee05aae5345dd29a40438a79e4d1b8f5134`.

- [ ] Validar zoom visible temporal MapLibre
  - Contexto: se ha anadido localmente un indicador `Zoom X.XX` en la cabecera compacta de MapLibre para confirmar el umbral real de hover.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/style.css`.
  - Criterio de aceptacion: en HA/movil el zoom visible cambia al hacer zoom y permite confirmar que `HOVER_POPUP_MIN_ZOOM=7` es adecuado.
  - Estado: publicado en `0.2.95` con umbral `7`. Retirar el indicador al fijar el umbral definitivo.

- [x] Crear gestion WebUI de usuarios y dispositivos
  - Contexto: el backend ya soporta roles `free`, `basic`, `pro`, `admin`, `username`, `name`, `email` y `max_devices` opcional en `users.json`; la WebUI local anade una pagina `Users`.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper-app/DOCS.md`, `/share/rainmapper/users.json`, `/share/rainmapper/devices.json`.
  - Criterio de aceptacion: desde la webUI HA se pueden listar usuarios, crear/desactivar/borrar usuarios, cambiar rol, cambiar `max_devices`, establecer una nueva contrasena, forzar cambio de contrasena y gestionar dispositivos asociados. Borrar un usuario debe borrar tambien todos sus dispositivos asociados.
  - Requisito especifico: para cada usuario debe poder borrarse un dispositivo concreto o borrar todos sus dispositivos.
  - Estado: implementado y validado manualmente en HA hasta `0.2.101`. La pagina `Users` permite crear usuarios, editar nombre/email/rol/status/max_devices, establecer nuevas contrasenas, forzar cambio de contrasena mediante `must_change_password`, borrar dispositivos individuales o todos los de un usuario y borrar el usuario junto con sus dispositivos. En `0.2.101` se publica y valida una mejora de `Users` con cabecera fija, boton manual `Refresh` sin refrescar navegador, busqueda tipo texto libre sobre usuarios/dispositivos y preservacion de posicion de scroll al refrescar. Cubierto por `tests/test_web_server_auth.py`.

- [x] Decidir visor principal
  - Contexto: conviven Bokeh, Leaflet y MapLibre; MapLibre ya funciona bien en movil segun validacion manual/reportada por el usuario y desde `0.2.47` tambien soporta Hybrid/Topographic raster.
  - Ficheros relacionados: `rainmapper_core/bokeh_maps.py`, `rainmapper_core/viewers/`, `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: definir si Bokeh queda como legacy, si Leaflet sigue activo y si MapLibre pasa a principal.
  - Estado: MapLibre queda como visor principal recomendado tras validar `0.2.53`; Leaflet se mantiene publicado como fallback. Bokeh sigue como referencia/compatibilidad.
  - Riesgo aceptado: complejidad y mantenimiento de varios visores hasta nueva revision.

- [x] Retirar `/local/rainmapper-mobile`
  - Contexto: la ruta legacy ya no se usa porque Cloudflare redirige a `rainmapper-leaflet` y `rainmapper-maplibre` segun reporte del usuario; pendiente de confirmar fuera del repositorio.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`, `rainmapper-app/DOCS.md`, `README.md`, `rainmapper-app/README.md`.
  - Criterio de aceptacion: dejar de publicar `/local/rainmapper-mobile` y limpiar la carpeta antigua al publicar mapas.
  - Estado: resuelto en version `0.2.42`.

- [x] Homogeneizar idioma de logs y UI
  - Contexto: la webUI visible de HA, metadata HA, changelog y logs operativos principales del core quedan en ingles desde `0.2.46`.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper-app/app/web_server.py`, `rainmapper-app/README.md`, `rainmapper-app/DOCS.md`.
  - Criterio de aceptacion: idioma definido para superficies de usuario final y logs operativos.
  - Estado: resuelto para webUI/changelog/logs operativos. README/DOCS de la app HA quedan en espanol de momento por ser documentacion de uso propio, no distribucion publica.
  - Riesgo residual: si la app se distribuye publicamente, convendra traducir README/DOCS a ingles.

- [x] Validar portabilidad del enlace App settings
  - Contexto: funciona en la instalacion actual, pero dependia de slug/fallback y de una unica ruta.
  - Ficheros relacionados: `rainmapper-app/app/web_server.py`.
  - Criterio de aceptacion: probado en otra instalacion HA o documentado como limitacion.
  - Estado: mejorado en `0.2.44`; la pagina App settings muestra el enlace recomendado calculado con Supervisor self-info y deja las rutas alternativas en una seccion avanzada. Queda validar en otra instalacion si aparece la ocasion.

- [x] Revisar documentacion/enlaces tras elegir MapLibre como visor principal
  - Contexto: MapLibre queda como visor principal recomendado; Leaflet se mantiene publicado como fallback y Bokeh como referencia/compatibilidad.
  - Ficheros relacionados: `README.md`, `rainmapper-app/README.md`, `rainmapper-app/DOCS.md`, `docs/codex-handoff.md`, `docs/todo.md`.
  - Criterio de aceptacion: la documentacion de uso presenta MapLibre primero y no induce a pensar que los tres visores tienen el mismo rol operativo.
  - Estado: resuelto.

- [x] Validar filtro de lluvia minima en MapLibre
  - Contexto: se ha anadido un panel `Settings` al visor MapLibre con slider `Min rain` para validar la UX antes de llevar el concepto a la futura app cross-platform.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: en HA/iPhone el slider filtra estaciones del periodo actual, conserva cambio de periodo/capa y no bloquea popups ni lectura del mapa.
  - Estado: validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada. El slider filtra sin romper cambio de periodo/capa ni popups segun esa validacion.

- [x] Validar vuelta a Satellite+ en MapLibre
  - Contexto: en `0.2.55`, despues de cambiar desde Satellite+ a otra capa, volver a Satellite+ no refrescaba la capa y quedaba la anterior.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/index.html`.
  - Criterio de aceptacion: en HA/iPhone, Satellite+ vuelve a cargar correctamente tras alternar con Hybrid, Topographic y Liberty.
  - Estado: corregido en `0.2.56` y validado manualmente por el usuario en HA/iPhone; pendiente de confirmacion automatizada.

- [x] Validar parada limpia SIGTERM en Home Assistant
  - Contexto: Supervisor aviso que Rainmapper `0.2.54` no manejaba SIGTERM durante update y termino con codigo 143.
  - Ficheros relacionados: `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper-app/config.yaml`, `rainmapper-app/Dockerfile`, `rainmapper-app/CHANGELOG.md`.
  - Criterio de aceptacion: al actualizar/reiniciar la app HA, Supervisor no muestra warning de SIGTERM y el proceso sale con codigo 0; si hay un job activo, la app intenta esperar a que termine antes de cerrar.
  - Estado: corregido en `0.2.55` y validado manualmente por el usuario; pendiente de confirmacion automatizada. Ya no aparece el warning de SIGTERM del Supervisor segun esa validacion.

## Prioridad baja
- [x] Estabilizar MapLibre 3D terrain
  - Contexto: MapLibre puede inclinar/rotar el mapa, pero el relieve real requiere una fuente DEM. Se ha anadido un toggle `3D terrain` y slider `Exaggeration` en Settings usando DEM externo Terrarium/Mapzen.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`.
  - Criterio de aceptacion: confirmar en local/HA/iPhone que activar 3D terrain funciona sobre Satellite+, Hybrid, Topographic y Liberty sin romper filtros, cambio de periodo, cambio de capa ni popups.
  - Estado: completado por decision del usuario el 2026-06-18; validado manualmente en local, HA, Mac e iPhone y queda como funcionalidad definitiva. En `0.2.77` se anade boton compacto `2D`/`3D` bajo `Generated`, atajo `t`, cola para el popup de altitud y cierre correcto sin bloquear hover. Riesgo aceptado: sigue dependiendo del DEM externo Terrarium/Mapzen hasta que se decida si hace falta DEM propio.

- [x] Revisar ergonomia del panel Settings de MapLibre en movil
  - Contexto: al anadir badges de estado por fuente, el panel Settings necesita mas ancho. El ajuste actual evita solapes y funciona en iPhone, pero puede sentirse algo ancho.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/style.css`, `rainmapper_core/viewers/maplibre-viewer/app.js`, `rainmapper_core/viewers/maplibre-viewer/index.html`.
  - Criterio de aceptacion: tras usarlo en movil, decidir si se mantiene el ancho actual, se compactan los badges o se cambia Settings a un panel tipo drawer/bottom sheet.
  - Estado: resuelto en `0.2.81` a nivel visual/operativo y validado manualmente en HA en versiones posteriores hasta `0.2.111`. El visor MapLibre pasa a una UI mas moderna con cabecera clara, controles flotantes, panel Settings claro y compacto en dos columnas, selector inferior de periodo, leyenda vertical dinamica, creditos en boton de informacion y popups claros.

- [x] Crear smoke tests automatizados
  - Contexto: no hay framework de tests completo, pero existe `scripts/smoke-test.sh`.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `README.md`, `docs/architecture.md`, `docs/codex-handoff.md`.
  - Criterio de aceptacion: comando unico que valide sintaxis Python, JS, conversion GeoJSON minima y wrappers shell.
  - Estado: resuelto con smoke test de sintaxis Python/JS/shell, conversion GeoJSON minima, version HA, sincronizacion raiz/app HA y whitespace Git.

- [x] Crear fixtures funcionales iniciales para GeoJSON
  - Contexto: Leaflet y MapLibre dependen de GeoJSON generado desde `Tomap`.
  - Ficheros relacionados: `tests/fixtures/`, `tests/test_tomap_to_geojson.py`, `rainmapper_core/geojson.py`, `scripts/smoke-test.sh`.
  - Criterio de aceptacion: tests versionados cubren estaciones ignoradas, coordenadas invalidas, columnas obligatorias y nombres de salida por periodo.
  - Estado: resuelto como primera cobertura formal con `unittest`, integrada en `./scripts/smoke-test.sh`.

- [x] Separar core en paquete Python reutilizable
  - Contexto: scripts grandes y duplicados.
  - Ficheros relacionados: `rainmapper_core/`, `rainmapper-app/Dockerfile`, `rainmapper-app/app/web_server.py`, `docs/core-refactor.md`.
  - Criterio de aceptacion: una unica fuente de verdad para core compartida por Docker local y HA.
  - Estado: resuelto en alcance conservador. `incremental_upsert` vive en `rainmapper_core/incremental_upsert.py`, `rainmapper_core.tomap` y `rainmapper_core.geojson` son entrypoints canonicos; los wrappers raiz/HA de Tomap y GeoJSON fueron retirados, la configuracion Python compartida vive en `rainmapper_core/config/`, Bokeh vive en `rainmapper_core/bokeh_maps.py`, los visores compartidos viven en `rainmapper_core/viewers/`, el runner principal vive en `rainmapper_core/rainmapper.py`, Bokeh vive en `rainmapper_core/bokeh_maps.py`, los wrappers Python raiz fueron retirados, y las librerias internas de fuente viven en `rainmapper_core/sources/`. El runtime Docker local vive en `rainmapper-local/`, con wrappers/rutas compatibles en raiz. HA se construye desde la raiz del repo y `rainmapper-app/app` queda solo para `web_server.py`. Validado con unit tests, smoke test, Docker offline functional test, `./local_update.sh` real con exit code 0, HA 0.2.79 antes de retirar las ultimas copias y HA 0.2.80 con `Run all` manual correcto tras cerrar la refactorizacion core/app/local.
  - Riesgo si no se hace: mantenimiento manual permanente.

- [x] Extraer generacion de CSV `Tomap` de `Rainmapper.py`
  - Contexto: hasta ahora `Generate maps`/`MODE=maps` solo consumia los `Tomap` existentes para generar Bokeh y GeoJSON. Si cambiaba una columna derivada de `Tomap`, como el numero de ultimos registros de lluvia por estacion, hacia falta `Run all`/`MODE=all` para reconstruirlos.
  - Nota: desde `0.2.67`, el numero de registros recientes se configura con `last_rains_history`; con `rainmapper_core.tomap`, `Generate maps` deberia poder reconstruir ese historico sin `Run all`, pendiente de validacion local/HA.
  - Ficheros relacionados: `rainmapper_core/tomap.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper_core/bokeh_maps.py`, `rainmapper_core/geojson.py`.
  - Estado: resuelto. `python -m rainmapper_core.tomap` reconstruye `Tomap` y `LastXX_rains.csv`; `MODE=maps`, `MODE=all` y `Generate maps` lo invocan antes de Bokeh/GeoJSON. En `Rainmapper.py` se han retirado el bloque ejecutable inline de generacion `Tomap` y los helpers legacy `create_grouped` y `create_last_rains`.
  - Validacion: tras ejecutar `local_update.sh`, `scripts/compare-tomap-builder.sh` confirma que `rainmapper_core.tomap` reconstruye los mismos CSV `Tomap` que el flujo antiguo de `Rainmapper.py` para los datos locales actuales. `local_maps.sh` reconstruye `Tomap`, genera GeoJSON y arranca el servidor local correctamente. `Generate maps` en HA `0.2.74` fue validado manualmente por el usuario. Tras retirar el bloque inline, `local_all.sh` completo termina con `rainmapper_core.rainmapper` exit code 0, reconstruye Tomap con `rainmapper_core.tomap` y genera GeoJSON. Tras limpiar helpers legacy, `MAX_THREADS=3 ./local_update.sh` termina con exit code 0 y las descargas actuales quedan contenidas en sus incrementales.
  - Riesgo residual: si cambia el schema de historicos incrementales, hay que actualizar `rainmapper_core.tomap` y sus tests.

- [ ] Mejorar observabilidad de Wunderground
  - Contexto: Wunderground es el cuello de botella, pero todavia no hay suficientes observaciones de tiempos y el rendimiento actual es aceptable.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos segun reporte del usuario; pendiente de confirmar automaticamente.
  - Observacion local 2026-06-19: despues de permitir que `docker-compose.yml` propague `MAX_THREADS`, `local_update.sh` paso de `385.69s` con `MAX_THREADS=1` a `196.82s` con `MAX_THREADS=2` y `81.20s` con `MAX_THREADS=3`; Wunderground paso de `0:06:02` a `0:03:03` y despues a `0:01:19`.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `Data/metricas_wunderground.csv`.
  - Criterio de aceptacion: metricas revisables y comparables por ejecucion; validar en HA/RPi si `max_threads=2` o `3` reduce tiempos sin generar timeouts, carga excesiva ni fallos de fuentes; posible export futuro a InfluxDB/Grafana.
  - Estado: parcialmente mejorado. `source_status.json` guarda duraciones reales por fuente y la webUI las muestra; Meteocat guarda subtiempos de metadata, condiciones, precipitacion, merge y guardado. Tras observacion nocturna de schedules en HA sin problemas reportados por el usuario, `max_threads=3` queda como valor operativo recomendado; queda pendiente decidir si exportar metricas historicas a InfluxDB/Grafana.
  - Riesgo si no se hace: optimizacion a ciegas del scraper si el rendimiento empeora en el futuro.

- [ ] Definir estrategia legal/comercial para Wunderground antes de una app publica
  - Contexto: el scraping HTML actual funciona para uso propio, pero las condiciones de TWC/Wunderground consultadas el 2026-06-18 no lo hacen apto como base de una app comercial sin permiso escrito. La API/PWS Data Feed oficial tambien limita el uso a personal/no comercial salvo acuerdo separado, y el pricing publico de Weather Data APIs parte de un plan Standard de 500 USD/mes orientado a clientes empresariales.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/sources/wunderground/`, futura API/app movil, documentacion de producto.
  - Criterio de aceptacion: antes de comercializar mapas o app, decidir entre retirar Wunderground, reemplazarlo por fuentes con licencia compatible, limitarlo a uso privado o negociar derechos con The Weather Company.
  - Riesgo si no se hace: dependencia de una fuente con coste/licencia incompatible con una app comercial.

- [ ] Revisar timeout del scraper Wunderground
  - Contexto: algunas estaciones pueden tardar o fallar, pero el tiempo global actual es aceptable y conviene acumular mas observaciones antes de cambiarlo.
  - Dato operativo actual: update completo + generacion de mapas tarda unos 7 minutos segun reporte del usuario; pendiente de confirmar automaticamente.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/sources/wunderground/`.
  - Criterio de aceptacion: timeout configurable y errores registrados sin bloquear toda la ejecucion.
  - Riesgo si no se hace: estaciones lentas podrian penalizar todo el run si el rendimiento empeora.

- [x] Hacer Meteocat/Socrata mas tolerante a timeouts transitorios
  - Contexto: en HA `0.2.67`, un `Run all` fallo despues de Wunderground porque una consulta Meteocat XEMA a `analisi.transparenciacatalunya.cat` supero el timeout por defecto de 10s del cliente Socrata.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper_core/config/const.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, `rainmapper-app/config.yaml`.
  - Criterio de aceptacion: las llamadas Meteocat/Socrata usan timeout configurable y reintentos antes de fallar el run.
  - Estado: corregido en `0.2.68` con `meteocat_request_timeout` y `meteocat_max_attempts`; pendiente de validacion manual en HA.

- [x] Validar ejecucion degradada por fuente y exit code global
  - Contexto: `rainmapper_core.rainmapper` ejecuta Meteoclimatic, Meteocat, Wunderground y AEMET opcional en futuros paralelos. Wunderground controla errores por estacion y muestra resumen; Meteoclimatic tolera fallos de patrones individuales si algun patron devuelve datos, pero aborta si no recupera ninguno; Meteocat reintenta desde `0.2.68`; AEMET debe degradar si hay error temporal/429.
  - Objetivo: si una fuente falla completamente, el proceso general deberia poder continuar con las fuentes que si funcionen, reutilizar o marcar claramente datos antiguos cuando proceda, y dejar trazabilidad visible.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, `rainmapper-app/app/web_server.py`, `run.sh`, `rainmapper-app/run.sh`, `rainmapper_core/geojson.py`, `rainmapper_core/viewers/maplibre-viewer/`, documentacion HA.
  - Estado parcial: desde `0.2.71`, la webUI muestra estado/exit code separado para Meteoclimatic, Meteocat y Wunderground; desde la integracion AEMET tambien muestra AEMET. `rainmapper_core.rainmapper` escribe `Data/source_status.json`; si una fuente falla completamente intenta reutilizar su incremental previo y marca la fuente como `STALE`; si no hay incremental utilizable la marca como `NOK`. El fichero se copia como `data/source_status.json` en Leaflet/MapLibre publicados, y MapLibre muestra badges junto al filtro `Source`. Desde `0.2.73`, el exit code global distingue `0` exito completo, `2` exito degradado con al menos una fuente usable y `1` fallo total/no recuperable; `Run all` debe continuar a `maps` cuando `update` devuelve `2`.
  - Validacion: `0.2.73` fue validada manualmente en HA con `Run all` completo, `Exit code 0` y mapas generados correctamente.
  - Validacion adicional: el caso degradado `Exit code 2` se da por validado de facto en local por decision del usuario, tras el fallo accidental de lectura/escritura provocado por iCloud que permitio comprobar continuidad del proceso y trazabilidad por fuente.
  - Estado: resuelto operativamente; una validacion HA con fallo simulado queda como comprobacion opcional, no como bloqueo.

- [x] Retirar Jawg Maps de Leaflet/MapLibre y de la configuracion
  - Contexto: Jawg Street/Terrain eran capas opcionales activadas con `jawgmaps_api_key`, pero MapLibre ya cubre las necesidades actuales con Satellite+, Hybrid, Topographic, Liberty y 3D terrain. Jawg anade gestion de API key, posible restriccion por dominio, dudas de uso no comercial y complejidad de documentacion/soporte.
  - Ficheros relacionados: `rainmapper_core/viewers/leaflet-viewer/`, `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper-app/config.yaml`, `rainmapper-app/run.sh`, `rainmapper-app/app/web_server.py`, README/DOCS y docs de contexto.
  - Criterio de aceptacion: no aparece `jawgmaps_api_key` en opciones HA ni docs principales; `JAWGMAPS_API_KEY` deja de usarse en visores; Leaflet/MapLibre no muestran capas Jawg; quedan actualizadas las decisiones/documentacion indicando que se descarta Jawg por bajo valor frente a complejidad/licencia/API key.
  - Estado: resuelto en `0.2.69`.
  - Riesgo si no se hace: mantener una dependencia externa y una clave cliente visible que ya no aporta valor suficiente al flujo actual.

- [ ] Evaluar InfluxDB/Grafana para metricas
  - Contexto: el usuario ya tiene interes en analitica de tiempos de estaciones.
  - Ficheros relacionados: `rainmapper_core/rainmapper.py`, futuro exporter.
  - Criterio de aceptacion: decision tecnica documentada.
  - Riesgo si no se hace: se acumulan CSV sin explotacion.

- [x] Validar imagen Docker HA preconstruida
  - Contexto: antes de usar GHCR, Home Assistant construia la app en la RPi durante installs/updates, y la barra de progreso de HA podia quedarse en 0% hasta terminar. El Mac construye mucho mas rapido que la RPi segun validacion manual/reportada por el usuario.
  - Ficheros relacionados: `.github/workflows/build-rainmapper-app.yml`, `rainmapper-app/Dockerfile`, `rainmapper-app/config.yaml`, GitHub Container Registry.
  - Criterio de aceptacion: publicar imagen multi-arch `amd64`/`arm64` en GHCR antes de hacer visible el update en HA; HA descarga `ghcr.io/cginebrosa/rainmapperha:<version>` sin build local.
  - Estado: el repo soporta imagen GHCR y Buildx local con limpieza de etiquetas antiguas. Validaciones en `0.2.57`, `0.2.60`, `0.2.61`/`0.2.62`/`0.2.63`/`0.2.65` fueron manuales/reportadas por el usuario; pendientes de confirmar automaticamente. El flujo normal pasa a Buildx local con `scripts/build-push-ha-image.sh`, dejando Actions como fallback manual. Procedimiento de validacion: ejecutar `./scripts/smoke-test.sh` una sola vez antes del build/push; no repetirlo tras publicar si solo se actualiza documentacion con el digest. Repetirlo solo si despues del primer smoke se toca codigo runtime, configuracion HA, assets de visor, scripts o ficheros incluidos en la imagen.
  - Riesgo residual: requiere login Docker en GHCR desde el Mac y disciplina de publicar imagen antes del commit de version.

- [x] Validar filtros de visor para futura app movil
  - Contexto: antes de construir la app iOS/Android se quieren probar funciones utiles en el visor web actual.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/`, `rainmapper_core/geojson.py`, `tests/test_tomap_to_geojson.py`.
  - Criterio de aceptacion: MapLibre permite filtrar por lluvia minima y por fuente de estacion; el GeoJSON incluye `Source` para no repetir inferencias en clientes futuros.
  - Estado: filtro de lluvia minima en `0.2.54`; filtro Meteocat/Meteoclimatic/Wunderground y `Source` en GeoJSON en `0.2.58`; ajuste defensivo `Unknown` y Meteocat longitud 2 en `0.2.59`. Cubierto parcialmente por `tests/test_tomap_to_geojson.py` para inferencia `Source`; validacion visual del visor pendiente de automatizar.

- [x] Disenar futura app iOS/Android
  - Contexto: objetivo a largo plazo incluye app movil con autenticacion y permisos.
  - Ficheros relacionados: `docs/mobile-app-architecture.md`.
  - Criterio de aceptacion: arquitectura propuesta para API, auth, permisos y serving de mapas.
  - Ideas funcionales iniciales:
    - Lista de estaciones favoritas para mostrar en el mapa solo esas estaciones.
    - Filtro por cantidad minima de lluvia en el periodo seleccionado para mostrar solo estaciones que superen ese umbral.
  - Estado: resuelto a nivel de diseno inicial; no implementado.
  - Riesgo si no se hace: el visor publico actual no controla quien accede a que.

- [x] Documentar direccion Cloudflare + app cross-platform
  - Contexto: se quiere explorar futura app iOS/Android sin depender de Home Assistant como backend publico.
  - Ficheros relacionados: `docs/mobile-app-architecture.md`, `docs/decisions.md`, `docs/codex-handoff.md`.
  - Criterio de aceptacion: documentar Cloudflare R2, Worker API, React Native/MapLibre, pruebas sin stores y primer MVP recomendado.
  - Estado: resuelto a nivel de arquitectura; pendiente de implementacion.

## Bugs abiertos
- [x] Docker local dejaba GeoJSON obsoletos en `MODE=maps/all`
  - Sintoma: tras ejecutar Docker local en `MODE=all`, `docker-data/Tomap` se actualizaba pero `docker-data/PublicData/*.geojson` mantenia fechas antiguas, por lo que MapLibre local no mostraba lecturas recientes.
  - Causa historica: `run.sh` local solo ejecutaba el generador Bokeh; la generacion GeoJSON estaba en `web_server.py` de HA pero no en el wrapper local. Actualmente el generador Bokeh se ejecuta como `python -m rainmapper_core.bokeh_maps`.
  - Ficheros relacionados: `run.sh`, `rainmapper-app/run.sh`, `Dockerfile`.
  - Estado: corregido; `maps/all` ejecuta tambien `rainmapper_core.geojson`.

- [ ] Tests funcionales formales incompletos
  - Sintoma: ya existen fixtures `unittest` offline para `rainmapper_core.geojson`, `rainmapper_core.tomap`, un pipeline integrado `upsert -> Tomap -> GeoJSON`; tambien existe `scripts/docker-offline-functional-test.sh` para validar el pipeline dentro de Docker con datos temporales. No hay cobertura funcional formal para HA real, publicacion webUI o generacion completa Bokeh/visores servida desde HA.
  - Causa probable: proyecto evolucionado por validacion manual.
  - Ficheros relacionados: `scripts/smoke-test.sh`, `scripts/docker-offline-functional-test.sh`, `tests/`, futuro set de fixtures HA/webUI.
  - Como reproducir: ejecutar `./scripts/smoke-test.sh` para checks rapidos y `./scripts/docker-offline-functional-test.sh` para validacion Docker offline; ninguna de las dos prueba HA real.
  - Criterio de solucion: ampliar pruebas funcionales para publicacion, webUI y/o ejecuciones controladas de HA sin depender de red.

- [x] Cache-buster obsoleto en assets del visor MapLibre
  - Sintoma: la pulsacion larga de altitud funcionaba en local pero no en mapas servidos desde HA.
  - Causa: se detecto un problema real de cache-buster (`rainmapper_core/viewers/maplibre-viewer/index.html` seguia referenciando `app.js?v=0.2.62` aunque la app HA estaba en `0.2.63`), pero Chrome limpio tambien fallo tras generar mapas, asi que la causa funcional final era el disparador `pointerdown` directo sobre canvas en HA.
  - Ficheros relacionados: `rainmapper_core/viewers/maplibre-viewer/index.html`, `rainmapper_core/viewers/leaflet-viewer/index.html`, `scripts/smoke-test.sh`.
  - Estado: corregido en `0.2.65`; el smoke test valida que los cache-busters internos de los visores coinciden con la version HA y MapLibre usa eventos propios del mapa mas `contextmenu` para la pulsacion larga. Validado manualmente por el usuario en HA tanto en iPhone como en Safari para Mac; pendiente de confirmacion automatizada.

## Validaciones pendientes
Nota: las validaciones marcadas como resueltas en esta seccion son, salvo que se indique un script concreto, validaciones manuales/reportadas por el usuario y no pruebas automatizadas reproducibles solo desde el repositorio.

- [x] `docker compose build rainmapper` tras cambios de Docker local.
- [x] `docker compose run --rm -e MODE=help rainmapper`.
- [x] `docker compose run --rm -e MODE=all rainmapper` en datos de prueba antes de tocar historicos reales.
- [x] Actualizacion HA desde GitHub tras bump de version.
- [x] `Run all` desde webUI HA.
- [x] `Run all` HA `0.2.73` con semantica nueva: caso normal validado con `Exit code 0` y mapas generados correctamente.
- [x] Schedule con varias horas y dias.
- [x] Leaflet en iPhone: cambio periodo conserva posicion, popups y leyenda.
- [x] MapLibre en movil: estilos, marcadores tras cambio de capa, popup, bounds.
- [x] `ignore_stations_tomap.txt`: estacion ignorada desaparece de Leaflet/MapLibre pero sigue en historico.
- [x] Reconstruccion desde cero con poco historico.
- [x] `./local_all.sh`: build local, `MODE=all`, servidor HTTP local y MapLibre con datos actuales; validado manualmente por el usuario el 2026-06-18 a las 00:37 con 432 estaciones en el periodo de 1 dia, pendiente de confirmacion automatizada.

## Preguntas pendientes para el usuario
- [x] Confirmar si MapLibre debe sustituir a Leaflet como visor principal o si ambos se mantienen.
- [x] Confirmar cuando retirar la ruta legacy `/local/rainmapper-mobile`.
- [x] Confirmar si el repo debe quedar privado o publico para distribucion futura.
  - Estado: confirmado el 2026-06-22; repo privado. Para la instalacion HA actual se mantiene GHCR accesible.
- [x] Confirmar si Jawg permite restringir token por dominio y si se usara en publico.
  - Estado: se decide retirar Jawg de momento; no hace falta investigar restricciones de token mientras no se use.
- [x] Confirmar idioma final de UI visible HA/changelog: ingles.
- [x] Confirmar si los logs internos del core deben quedar tambien en ingles.

## Ideas futuras
- App iOS/Android con login y autorizacion por mapa/zona.
- Prototipo cross-platform con React Native + MapLibre consumiendo Cloudflare Worker API.
- Publicacion de GeoJSON a Cloudflare R2 con manifiesto `latest.json`.
- Favoritos de estaciones y filtro por lluvia minima en la futura app movil.
- Revisar modelo de limites por plan para `Last rains history`, separando registros publicados en GeoJSON de registros visibles por usuario o suscripcion.
- API propia entre backend y app movil.
- Capa de permisos por usuario.
- Cache/CDN de GeoJSON publicados.
- Panel de calidad de estaciones basado en metricas Wunderground.
- Auto-deteccion de outliers de lluvia antes de publicar mapas.
- Migracion de historicos CSV a formato mas eficiente si crecen mucho, por ejemplo Parquet, pendiente de evaluar.
