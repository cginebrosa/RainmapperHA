# Decisions

Nota de auditoria 2026-06-29: este fichero es un log cronologico/historico. Las entradas antiguas se conservan para trazabilidad y pueden describir fases intermedias ya sustituidas por decisiones posteriores. Estado real verificado contra el repo en este cierre: version HA `0.2.175`; `.github/workflows/build-rainmapper-app.yml` solo es fallback manual (`workflow_dispatch`); el build HA soportado usa la raiz del repo como contexto; `rainmapper-app/app` contiene solo codigo especifico HA (`web_server.py`, `mushroom_catalogs_ui.py`, `mushroom_profiles_ui.py`); los entrypoints activos son modulos `rainmapper_core` y wrappers shell actuales; los wrappers raiz `Rainmapper.py`, `Rainmapper_Client.py`, `tomap_builder.py`, `tomap_to_geojson.py` y scripts de sincronizacion `scripts/sync-app-files.sh`/`scripts/sync-manifest.sh` no existen y no deben reintroducirse. `0.2.175` esta publicada/pusheada con imagen `ghcr.io/cginebrosa/rainmapperha:0.2.175/latest`, digest multi-arch `sha256:883695d0d414d871857a219a904ea60effc3af6c64aa320b9bf5447d10389a7e`, commit `b52cd5c`, pendiente de validar en HA. `0.2.172` fue confirmada por el usuario como funcionando correctamente el 2026-06-28; incluye la correccion de la tarjeta `Weather model summary` del tab `General/Summary` de especies. `0.2.175` introduce el store real de observaciones de setas, labels genericas y mantenimiento inicial de observaciones.

## 2026-06-27 - Mantener JSON de setas como defaults versionados y copia editable en HA

Decision:

- Tratar `mushroom-data/mushroom_profiles.json`, `mushroom-data/mushroom_reference_catalogs.json` y `mushroom-data/mushroom_gis_mappings.json` como defaults versionados empaquetados con la app.
- En Home Assistant, mantener la copia viva editable en `/share/rainmapper/mushroom-data/`.
- La UI de administracion de setas debe editar la copia persistente, no los defaults de la imagen.
- En primer arranque o primera activacion del modulo, si faltan ficheros persistentes, copiarlos desde los defaults; si existen, no sobrescribirlos al actualizar.
- El futuro motor de prediccion debe leer primero `/share/rainmapper/mushroom-data/` y usar los defaults versionados solo como fallback.
- Las pantallas de mantenimiento de perfiles y catalogos deben prever importacion/exportacion JSON y exportacion de una plantilla vacia del modelo.
- La primera fase de UI de mantenimiento cubre `mushroom_profiles.json` y `mushroom_reference_catalogs.json`; `mushroom_gis_mappings.json` queda como dato versionado, validable y consultable para impacto, pero sin editor completo hasta una fase posterior.
- Los valores controlados no ecologicos, como `review_status`, confidence y prioridades de calibracion, son contrato del modelo/validador/backend, no un campo `controlled_values` dentro de los JSON de perfiles.
- Estados validos de `metadata.review_status`: `draft`, `needs_review`, `reviewed`, `validated`, `deprecated`.

Motivo:

- Los perfiles y catalogos necesitan mantenimiento desde HA sin perder cambios en actualizaciones.
- Los defaults versionados siguen dando una base reproducible, testeable y recuperable.
- La importacion/exportacion permite mantenimiento externo, backup manual y migraciones controladas.

Consecuencias:

- Cualquier guardado desde UI debe validar antes de persistir, crear backup con timestamp y escribir de forma atomica.
- Importar un JSON debe mostrar resumen de cambios antes de confirmar y bloquear referencias rotas.
- Exportar plantilla vacia debe preservar `schema_version`, `model_purpose`, estructura raiz y grupos/campos principales, pero sin datos de especies o catalogos.
- No modificar automaticamente perfiles al importar catalogos, ni catalogos al importar perfiles, salvo flujo de migracion explicito y confirmado.

Estado de implementacion:

- Commit `54a86d0` introduce los defaults versionados, documentacion, validador y tests.
- La capa backend minima queda en `rainmapper_core/mushroom_store.py`.
- La imagen HA copia `mushroom-data/` y `scripts/validate-mushroom-data.py` a `/app/`.
- Endpoints admin disponibles en `rainmapper-app/app/web_server.py`: `GET/POST /api/mushrooms/validate`, `GET /api/mushrooms/export?file=profiles|catalogs|gis&source=current|persistent|default`, `GET /api/mushrooms/template?file=profiles|catalogs` y `POST /api/mushrooms/import` con `{file, data}`.
- `POST /api/mushrooms/import` solo permite `profiles` y `catalogs`; `gis` queda solo lectura en esta fase.
- Primera UI WebUI de catalogos disponible en `/mushrooms/catalogs`: hub de metricas, filtros por grupo, busqueda, tabla de IDs, creacion de entradas nuevas por grupo con plantilla minima validada, detalle con JSON editable por entrada, panel de validacion cruzada y bloque avanzado de import/export/plantilla JSON del catalogo completo.
- La UI de catalogos usa POST server-side por ingress HA, igual que `Users`; los endpoints JSON quedan como base para futuras pantallas cliente.
- Primera release HA que incluye backend/store y UI de catalogos: `0.2.150`, imagen `ghcr.io/cginebrosa/rainmapperha:0.2.150/latest`, digest multi-arch `sha256:35e42628eeb0937ec800608e9251fa0ef8148d4f6a626aea52a13a341ba71c0f`, commit `ecf2ed8`. Validacion local: `./scripts/smoke-test.sh` OK con 97 tests. Validacion HA: no cerrarla como buena por 404 en HA ingress al pulsar `Mushroom catalogs`; fix local aplicado con rutas relativas, seeding de defaults al arrancar y contador `Reference errors` derivado del validador para evitar falsos positivos GIS.
- La semantica exacta de `Reference errors` debe revisarse cuando esten completos el mantenimiento de perfiles, el mantenimiento GIS y el motor de prediccion; por ahora no debe contar cadenas tecnicas GIS que no sean IDs internos de catalogo.

## 2026-06-28 - Borrado defensivo de especies mediante archivado previo

Decision:

- No permitir borrado irreversible directo de una especie activa desde `mushroom_profiles.json`.
- El flujo soportado es activo -> archivado -> restaurado o borrado permanente desde archivo.
- Las especies archivadas se guardan fuera del JSON activo, en `/share/rainmapper/mushroom-data/archived/mushroom_profiles_archived.json`.
- `Restore species` solo puede restaurar si el `species_id` no existe ya en perfiles activos.
- `Delete permanently` solo aparece para especies archivadas y debe mostrar doble advertencia de navegador, incluyendo que no se puede deshacer.

Motivo:

- `species_id` es clave estable del modelo de prediccion; borrar un perfil activo por error podria romper mantenimiento, calibracion futura u observaciones asociadas.
- Archivado conserva recuperacion y auditoria practica sin contaminar el JSON activo que consume el motor.
- El borrado permanente queda disponible para limpiar pruebas, pero requiere una accion previa defensiva.

Consecuencias:

- La UI debe presentar `Archive species` para perfiles activos, no `Delete species` directo.
- El archivo de especies archivadas no forma parte del modelo predictor activo; se usa solo para mantenimiento.
- Si en el futuro hay observaciones/calibraciones vinculadas, el archivado/restauracion debera validar tambien esas referencias.

Actualizacion 2026-06-28: `0.2.169` no debe cerrarse como buena para este flujo porque en HA los modales de `New species`, `Duplicate species` y `Restore species` quedaban visibles pero no interactivos por una colision de `z-index` del backdrop heredada de los modales antiguos de Users. `0.2.170` corrige esa capa y queda como version a validar para el ciclo de vida defensivo.

Actualizacion 2026-06-28: desde `0.2.171`, `Archive species` no requiere reescribir manualmente el `species_id`. La UI muestra el ID seleccionado en solo lectura y el POST confia en el `species_id` oculto de la accion seleccionada. La confirmacion defensiva queda en el modal y el `confirm()` del navegador; el requisito de escribir el ID se retira porque era redundante y poco ergonomico para mantenimiento HA local.

## 2026-06-29 - Observaciones de setas como store propio y calibracion futura

Decision:

- Guardar observaciones de floradas en `mushroom-data/mushroom_observations.json`, separado de `mushroom_profiles.json` y `mushroom_reference_catalogs.json`.
- Mantener los valores tabulados de observaciones en `mushroom_reference_catalogs.json`, no hardcodeados en UI/backend.
- Usar `mushroom_labels.json` como diccionario general de labels de setas, sustituyendo el antiguo `mushroom_parameter_labels.json`.
- Tratar el alta/edicion de observaciones como mantenimiento HA server-side, con validacion global antes de persistir y backup atomico como perfiles/catalogos.
- Aplicar estrategia defensiva al borrado: una observacion activa solo puede archivarse; el borrado permanente solo existe desde observaciones archivadas y exige doble confirmacion de navegador mas confirmacion backend por `observation_id`.
- Mantener `calibration_use`, `validation_status` y `source_quality` como conceptos separados: uso en calibracion, aceptacion/validacion y fiabilidad del origen no significan lo mismo.

Motivo:

- Las observaciones seran la base para calibrar o confirmar si los parametros de especies son correctos frente a datos reales de campo.
- Separarlas de perfiles evita mezclar modelo teorico con evidencia observada.
- Los catalogos tabulados permiten cambiar opciones de abundancia, origen, validacion o uso sin tocar codigo.

Consecuencias:

- `rainmapper_core/mushroom_store.py` debe sembrar y validar tambien `observations`.
- `scripts/validate-mushroom-data.py` valida especies, coordenadas, fechas, catalogos de observacion y rangos de calidad.
- La UI inicial de `Observations` cubre alta, edicion, archivo, restauracion y borrado permanente; importacion CSV/JSON queda como tarea futura.
- `ui_language` queda disponible en `config.yaml`, pero la seleccion real de idioma para mantenimientos de setas queda pendiente.

Estado:

- Publicado en HA `0.2.175`, imagen/digest documentados en la nota de auditoria superior; pendiente de validacion operativa en Home Assistant.

## 2026-06-27 - Compactar panel expandido de usuarios sin cambiar contratos backend

Decision:

- Ajustar solo el contenido del usuario expandido en Home Assistant `Users`, sin redisenar toda la pantalla.
- Mantener `User details`, `Permissions` y `Audit` dentro del formulario `update_user` para no romper el guardado actual.
- Convertir `Permissions` en un grid de tarjetas con metadata centralizada para que nuevos permisos puedan anadirse sin duplicar markup.
- Mover `Security` a un bloque separado y compacto, preservando los forms/handlers actuales de `Set password`, `Reset password` y `Delete user`.
- Trackear la especificacion y referencia visual en `docs/ui/rainmapper-user_panel_redesign.md` y `docs/ui/rainmapper-user_panel_redesign.png`.

Motivo:

- La version accordion de `Users` funciona, pero el panel expandido seguia ocupando demasiado espacio y dejaba mucho desbalance visual entre detalles, permisos, seguridad, dispositivos y auditoria.
- Los permisos van a crecer si la app evoluciona, por lo que conviene preparar una UI en tarjetas sin cambiar todavia el modelo backend.
- Evitar cambios de endpoints o backend reduce el riesgo en una pantalla sensible de administracion.

Consecuencias:

- Los nombres de campos POST y `admin_action` existentes se conservan: `update_user`, `set_password`, `reset_password`, `delete_user`, `delete_device` y `delete_all_devices`.
- La auditoria sigue siendo informativa y compacta dentro del formulario de guardado.
- La seguridad queda visualmente separada para evitar forms anidados, manteniendo confirmaciones existentes.
- La validacion relevante debe hacerse dentro de HA/ingress por anchura real de pantalla y estilos de Home Assistant.

Estado:

Publicado inicialmente en imagen HA `0.2.148` con digest multi-arch `sha256:a2fcab2222519150bd20a3f9cbb1949736b03384e1c6b79f36ef50d79d28c821` y commit `48629ff`. En HA se detecto que el acordeon aparecia totalmente desplegado porque `.user-panel { display: grid; }` pisaba el atributo `hidden`, y ademas el JS podia abrir/restaurar automaticamente un usuario al cargar. `0.2.149` corrige el comportamiento: todos los usuarios nacen cerrados, pulsar un usuario abierto lo cierra, abrir un usuario cierra todos los demas y el refresh manual deja el listado cerrado. Imagen HA `0.2.149` publicada con digest multi-arch `sha256:3a488f597e34d2caba2c30edc90f5426813eb0c19858e2dcd679b197abda474b` y commit `039e615`. Validacion local: `python3 -m unittest tests.test_web_server_auth` OK y `./scripts/smoke-test.sh` OK. Instalada y validada/dada por buena en HA por el usuario el 2026-06-27.

## 2026-06-27 - Redisenar Control Panel HA como dashboard con tabs internos

Decision:

- Redisenar el Control Panel principal de Rainmapper dentro de Home Assistant como un dashboard compacto con tabs internos: `Summary`, `Data sources`, `Viewers`, `Maps`, `Logs` y `Errors`.
- Mantener la WebUI del Control Panel en ingles, aunque los documentos/mockups de trabajo puedan estar en castellano.
- Usar HTML/CSS/JS server-side generado desde `rainmapper-app/app/web_server.py`, sin dependencias frontend nuevas, para mantener compatibilidad con HA ingress.
- Preservar todos los handlers y acciones existentes: `Run update`, `Generate maps`, `Run all`, `App settings`, `Users`, `Update only` por fuente, abrir visores, abrir mapas, abrir log, `Disable all` y `Enable all`.
- No anadir confirmacion a `Disable all` / `Enable all`, porque son acciones reversibles y el usuario rechazo introducir friccion de seguridad ahi.

Motivo:

- El panel anterior era funcional pero demasiado alto y dificil de escanear conforme crecen fuentes, mapas, logs y errores.
- Home Assistant ya proporciona navegacion lateral; anadir una segunda sidebar dentro de Rainmapper seria mas pesado y menos coherente dentro de ingress.
- Los tabs internos permiten separar resumen, fuentes, visores, mapas, logs y errores sin perder acceso rapido a las acciones operativas principales.
- Mantener contratos POST y endpoints evita riesgo innecesario en una pantalla de control ya usada en produccion.

Consecuencias:

- El codigo de `web_server.py` crece con helpers server-side pequenos para renderizar fragments del dashboard, tablas, tarjetas, listas de mapas y preview de logs.
- La UX se valida en HA/ingress, no solo en HTML local, porque los estilos y anchuras reales dependen del contenedor de Home Assistant.
- Futuras mejoras del panel deben preservar primero los handlers existentes y anadir tests que comprueben enlaces/acciones criticas.

Estado:

Publicado en imagen HA `0.2.147` con digest multi-arch `sha256:368c910b9a31fba587c1e1cbca0201395feeecca3bf9e8884f62ccc08a76feef` y commit `9ffecab`. Validacion local: `./scripts/smoke-test.sh` OK. El usuario reporto el 2026-06-27 que la `0.2.147` parece funcionar bien en HA.

## 2026-06-25 - Mantener permisos funcionales simples por usuario solo como fase actual

Decision:

- Aceptar temporalmente `can_use_heatmap`, `can_use_layer_metrics` y `can_use_estimated_field` como flags directos por usuario en `users.json`.
- No seguir acumulando muchos flags independientes en cada usuario sin revisar antes el modelo de permisos.
- Si crece el numero de funcionalidades protegidas, definir una arquitectura de permisos por perfil/tipo de usuario en un JSON separado, con overrides opcionales por usuario.

Motivo:

- Ahora solo hay pocas funciones con permisos y el cambio por usuario es simple, compatible y facil de operar desde la WebUI.
- Si la app evoluciona hacia mas funcionalidades, mapas, zonas o perfiles comerciales, duplicar permisos en cada usuario seria fragil y dificil de mantener.
- Separar identidad de usuario, perfil base y overrides deja una ruta mas limpia hacia perfiles `free/basic/pro/admin` u otros modelos futuros.

Consecuencias:

- El modelo actual es suficiente para la fase inmediata de heatmap/metrica, pero queda marcado como deuda arquitectonica.
- Antes de anadir mas permisos funcionales, revisar un posible `permission_profiles.json` o equivalente persistido en `/share/rainmapper`.
- Cualquier migracion futura debe mantener compatibilidad con los flags existentes y defaults actuales: admins con permisos activos por defecto y resto de roles sin permisos experimentales salvo override.

## 2026-06-24 - Backfill manual AEMET con climatologia diaria

Decision:

- Se anade `scripts/aemet-backfill-30-days.py` como helper local para generar `Aemet_incremental.csv` de dias cerrados desde el endpoint diario de climatologia AEMET.
- El helper queda fuera del pipeline HA normal: por defecto escribe en `tmp/aemet-backfill-<timestamp>/`, no toca `Data/` y no modifica el historico horario AEMET.
- Para conservar metadatos enriquecidos se debe pasar `--station-catalog` apuntando al `estacions_aemet.csv` actual; para fusionar con un historico ya descargado de HA se puede pasar `--existing-incremental`.
- La subida a HA sigue siendo manual y debe tratarse como operacion sobre historicos: revisar salida y aplicar `docs/history-safety.md` antes de reemplazar CSV reales.

## 2026-06-23 - Promover AEMET al visor estandar protegido

Decision:

- Tras validar/dar por buena `0.2.108` en HA, AEMET pasa a formar parte del Tomap/GeoJSON estandar generado por la app HA.
- Los comandos de mapas de HA ejecutan `rainmapper_core.tomap` con `--include-aemet true`, de modo que `/protected/maplibre/index.html`, Leaflet y Bokeh consumen el mismo dataset de produccion con AEMET cuando exista `Aemet_incremental.csv`.
- Mantener `rainmapper_core.tomap` con AEMET excluido por defecto para pruebas locales/controladas; la promocion a produccion se decide en los comandos HA, no cambiando el default global del modulo.
- Desactivar la ruta experimental publica `/local/rainmapper-maplibre-aemet/index.html` mediante `PUBLISH_AEMET_EXPERIMENTAL_MAPLIBRE = False`, sin borrar todavia el codigo del publicador.
- Dejar documentada como tarea pendiente la retirada definitiva del publicador experimental AEMET cuando la ruta estandar quede validada durante uso real.

Motivo:

- La ruta experimental ya permitio validar integracion AEMET, bounds dinamicos, contador de coordenadas invalidas, atribuciones y duplicados diarios.
- Mantener dos visores con datasets distintos deja de aportar valor operativo y puede confundir las pruebas con usuarios reales.
- Conservar temporalmente el codigo experimental desactivado permite volver rapido al modo test si la promocion a produccion descubre un problema inesperado.

Consecuencias:

- El numero de estaciones del visor protegido aumentara cuando AEMET este habilitado y haya `Aemet_incremental.csv`.
- `Generate maps` y `Run all` en HA regeneran el dataset estandar incluyendo AEMET; si `create_aemet=false` o falta historico AEMET, el resultado sigue funcionando con el resto de fuentes.
- En la siguiente publicacion, la WebUI deberia dejar de mostrar el enlace `AEMET test viewer` porque la carpeta experimental se limpia al publicar.
- Hay que eliminar mas adelante el flag y `publish_aemet_experimental_maplibre()` para no dejar codigo de rollback indefinidamente.

## 2026-06-23 - Guardar la vista inicial MapLibre solo por accion explicita

Decision:

- Anadir en Settings de MapLibre protegido una accion explicita `Set current view as default` / `Usar vista actual por defecto`.
- Guardar en `devices.json` la vista elegida (`lng`, `lat`, `zoom`, `bearing`, `pitch`) como `map_view`, saneada por el backend.
- Al abrir o refrescar el visor protegido, si el dispositivo tiene `map_view`, restaurar esa vista en lugar de hacer `fitBounds()` a todos los datos.
- No guardar automaticamente cada movimiento, zoom o pan del mapa.

Motivo:

- Con AEMET, el dataset cubre mucho mas territorio y el encuadre automatico inicial muestra "demasiado mapa".
- Guardar cada movimiento escribiria con frecuencia en `/share/rainmapper/devices.json` en la Raspberry Pi 4. La preferencia debe ser deliberada y de baja frecuencia, igual que los ajustes persistidos al cerrar Settings.

Consecuencias:

- La vista por defecto se actualiza solo cuando el usuario pulsa el boton en Settings y cierra el panel, no al navegar normalmente por el mapa.
- Si no hay vista guardada, se mantiene el comportamiento anterior de encuadrar los datos cargados.
- La ruta experimental/fallback sin autenticacion no usa settings de dispositivo y por tanto conserva el encuadre automatico.

## 2026-06-23 - Atribuciones visibles por fuente en MapLibre

Decision:

- Mostrar atribucion especifica por fuente en la ficha de cada estacion MapLibre y retirar la fila generica `Source:` del popup.
- Mantener AEMET en castellano: `Fuente: AEMET - Informacion elaborada por Rainmapper a partir de datos de la Agencia Estatal de Meteorologia`.
- Mostrar Meteocat siempre en catalan, con el formato de fuente indicado por la Generalitat y el organismo/dataset XEMA: `Font: Generalitat de Catalunya. Departament de Territori, Habitatge i Transicio Ecologica. METEOCAT. Dades meteorologiques de la XEMA. Dades elaborades per Rainmapper.`
- Mostrar Meteoclimatic de forma conservadora y en castellano como `Fuente: Informacion elaborada por Rainmapper a partir de datos de Meteoclimatic (www.meteoclimatic.net)` hasta localizar un texto legal mas especifico para el RSS usado por Rainmapper.
- Mostrar Wunderground de forma conservadora y en ingles como `Source: Information elaborated by Rainmapper from Weather Underground data` hasta definir un texto contractual/legal concreto; esta atribucion no cambia la decision previa de no basar una app comercial en Wunderground sin acuerdo escrito.
- Incluir las mismas fuentes en el panel de creditos/informacion del visor.

Motivo:

- La Generalitat exige atribuir la reutilizacion de datos abiertos indicando `Generalitat de Catalunya`, el departamento y, si aplica, el organismo o entidad autonoma. Para XEMA, el dataset publico identifica el departamento `Territori, Habitatge i Transicio Ecologica` y `METEOCAT` como organismo/fuente.
- AEMET ya estaba atribuido; al anadir mas fuentes, la fila `Source:` duplicaba informacion y era menos clara que una atribucion visible.
- Meteoclimatic y Wunderground requieren revision adicional de terminos/formato exacto, pero en la fase privada actual es preferible mostrar al menos una fuente visible antes que ocultarla.

Consecuencias:

- Los creditos de MapLibre mezclan textos en distintos idiomas deliberadamente: AEMET y Meteoclimatic en castellano, Meteocat en catalan y Wunderground en ingles.
- Antes de publicar Rainmapper fuera del uso privado actual, revisar de nuevo Meteoclimatic y Wunderground y sustituir las atribuciones conservadoras por el texto legal/acuerdo aplicable.
- El codigo del visor MapLibre es compartido; desde la promocion de AEMET, el protected estandar usa el dataset con AEMET. La ruta experimental queda apagada y solo deberia reactivarse como rollback temporal.

## 2026-06-23 - Usar AEMET OpenData horario como nueva fuente candidata

Decision:

- Usar como candidato principal de AEMET el endpoint global `/opendata/api/observacion/convencional/todas`.
- Llamarlo como maximo una vez por ejecucion de `Run all`/schedule, nunca por estacion.
- Tratar `fint` como timestamp UTC de fin de la hora observada.
- Tratar `prec` como lluvia horaria acumulada durante los 60 minutos anteriores a `fint`.
- Deduplicar por `AEMET + idema + fint`.
- Guardar primero observaciones horarias y construir acumulados de periodo desde nuestro historico, no asumir que la respuesta es un dia completo.
- Si AEMET devuelve `429 Too Many Requests` u otro fallo temporal, la fuente debe degradar sin romper el pipeline completo.
- Dejar el endpoint diario de climatologia como posible backfill futuro de dias cerrados, no como fuente operativa inmediata.
- Si se muestran datos AEMET en visores o exports para terceros, mostrar atribucion visible a AEMET. Para estaciones AEMET en MapLibre, la ficha de estacion debe incluir al menos `Fuente: AEMET`; si el dato se mezcla o transforma dentro de Rainmapper, usar el texto ampliado `Informacion elaborada utilizando, entre otras, la obtenida de la Agencia Estatal de Meteorologia`. El panel de creditos/informacion del visor debe incluir una referencia agregada a AEMET cuando el dataset cargado contenga alguna estacion AEMET.

Motivo:

- El schedule real de HA ejecuta `Run all` unas 8 veces al dia, por lo que una llamada global cada 3 horas encaja con el endpoint horario sin hacer scraping agresivo.
- La respuesta trae en el mismo registro `idema`, coordenadas, nombre de estacion y lluvia horaria, suficiente para integrarla sin llamadas por estacion.
- El endpoint diario puede ser util para completar historicos, pero se publica con retraso, no trae coordenadas en el registro de datos y requiere unir con el inventario de estaciones.
- AEMET aplica limites de uso: durante pruebas manuales varias llamadas seguidas llegaron a `429`.
- La nota legal oficial de AEMET permite reutilizacion comercial y no comercial, pero exige no desnaturalizar la informacion, citar a AEMET como fuente, mencionar fecha de actualizacion cuando conste, conservar metadatos aplicables y no sugerir patrocinio, participacion o apoyo de AEMET.

Consecuencias:

- La implementacion debe ser muy conservadora con llamadas externas: una llamada de indice, una descarga de la URL temporal `datos`, sin bucles por estacion.
- El historico AEMET no debe mezclarse ingenuamente con historicos diarios existentes hasta definir el corte UTC/local. El plan inicial es almacenar UTC y hacer la conversion/control de periodos en el agregador.
- Cualquier escritura de historicos CSV para AEMET debe seguir `docs/history-safety.md`: backup o copia temporal, fixtures, validacion de estructura y deduplicado antes de tocar datos reales.
- Los CSV exploratorios en `tmp/aemet-test/` son solo material temporal de analisis y no forman parte del pipeline.
- La integracion debe preservar en los datos publicados metadatos suficientes para atribucion: `Source=AEMET`, timestamp de observacion `fint` en UTC y, si esta disponible, timestamp de generacion/actualizacion del dataset. `estacions_aemet.csv` actua como catalogo persistente de estaciones y debe preservar campos enriquecidos manualmente, como `Comarca`, `Municipi` y `Provincia`, aunque AEMET no los entregue en el endpoint horario. No usar logo AEMET salvo que venga integrado o se revise expresamente su uso; texto es suficiente para la primera version.
- Durante la validacion inicial, `tomap.py` excluia AEMET por defecto y solo lo incluia con `--include-aemet true`; la WebUI HA publicaba una variante experimental `/local/rainmapper-maplibre-aemet/index.html`. Tras validar `0.2.108`, HA pasa a generar el Tomap estandar con `--include-aemet true` y la ruta experimental queda desactivada por flag como rollback temporal.
- El reverse geocoding vive en `rainmapper_core/geocoding.py` y lo comparten las fuentes existentes y AEMET. AEMET debe seguir el mismo criterio operativo que Meteoclimatic/Wunderground: consultar Google Maps cuando la estacion sea nueva, falten `Municipi`/`Provincia` o cambien sus coordenadas. El enriquecimiento usa `GMAP_API_KEY`/`RAINMAPPER_GMAP_API_KEY`, preserva campos ya rellenados si las coordenadas no cambian y evita resultados tecnicos tipo `plus_code` cuando hay alternativas. `Comarca` no queda disponible de forma fiable desde Google y no se usa como condicion para repetir llamadas; si llega, se conserva. El CLI de AEMET permite `--skip-station-enrichment` solo para pruebas temporales.

Estado:

Diseno aceptado por el usuario como direccion para continuar. Primera implementacion completada de forma opcional y desactivada por defecto: `rainmapper_core/create_aemet.py`, opciones `create_aemet`/`aemet_api_key`, integracion opcional en `rainmapper_core.rainmapper`, consumo bajo flag en `tomap.py`, inferencia `Source=AEMET` en GeoJSON, atribucion AEMET en MapLibre y ruta experimental `/local/rainmapper-maplibre-aemet/index.html`. El 2026-06-23 se ejecuto una prueba real temporal con reverse geocoding en `tmp/aemet-geocode-test-v2/`: 802 estaciones, 802 con `Municipi`, 800 con `Provincia` y 7 con `Comarca`; `REUS AEROPUERTO` quedo como `Reus`, coherente con la localidad esperada. Durante la primera prueba HA, `0.2.103` ejecuto AEMET pero fallo la publicacion experimental al reconstruir Tomap por un `pd.merge` sobre columnas opcionales con tipos distintos (`object`/`float64`). La union de fuentes en Tomap debe tratarse como union de filas, no como join relacional por todas las columnas; desde `0.2.104`, `merge_dataframes()` usa `pd.concat(...).drop_duplicates()` para aceptar fuentes con columnas opcionales heterogeneas. Desde `0.2.105`, AEMET persiste tambien temperatura `ta` y humedad `hr` horarias cuando existen, agregandolas como max/min diarios, y MapLibre deja de recortar estaciones por bounds regionales: solo descarta coordenadas geograficamente invalidas y muestra `Invalid: N`. `0.2.108` queda validada/dada por buena en HA y se decide integrar AEMET en el visor protegido estandar, manteniendo el publicador experimental desactivado solo como rollback temporal.

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
- La imagen HA copia `rainmapper_core/`, wrappers raiz, configuracion compartida y los modulos HA de `rainmapper-app/app/` directamente desde la raiz.
- `rainmapper-app/app` queda reservado a codigo especifico de HA; actualmente contiene `web_server.py`, `mushroom_catalogs_ui.py` y `mushroom_profiles_ui.py`.
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
- `rainmapper_core/viewers/maplibre-viewer/`
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
Para una futura app iOS/Android publica o bajo suscripcion, no depender directamente de Home Assistant como backend publico. Mantener HA como motor privado de generacion y disenar una API/backend externo intermedio para autenticacion, permisos, filtros y serving controlado de datos. Esto no contradice la API interna que ya existe en el add-on HA para el visor MapLibre protegido (`/auth/*`, `/protected/maplibre/*`).

### Motivo
Los visores actuales y GeoJSON protegidos funcionan bien para uso privado, pero no dan el nivel de control comercial por usuario, mapa o zona que requeriria una app publica. Una app comercial necesita autorizacion en un backend externo, revocacion de acceso y una forma segura de aplicar favoritos y filtros sin exponer rutas internas de HA.

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
El flujo de release exige login Docker contra GHCR en el Mac y disciplina de publicar imagen antes de subir el commit de version. A cambio, HA no deberia ofrecer un update cuyo tag de imagen aun no exista. GitHub Actions deja de ejecutarse automaticamente en cada push de `rainmapper-app`. El script publica la etiqueta versionada y `latest`; Home Assistant usa la etiqueta versionada. Desde el ajuste posterior a `0.2.60`, el script limpia etiquetas locales versionadas antiguas del mismo repositorio y conserva por defecto las dos ultimas mas `latest`. El smoke completo debe ejecutarse una vez antes del build/push; no se repite tras publicar si solo se actualiza documentacion con el digest, salvo que se toque codigo runtime, configuracion HA, assets, scripts o ficheros incluidos en la imagen despues de ese smoke.

Actualizacion operativa 2026-06-28, reforzada el 2026-06-29: el criterio de "version disponible para probar en HA" requiere tanto imagen GHCR publicada/verificada como commit de bump pusheado a GitHub. HA detecta la version desde `config.yaml` en GitHub, por lo que dejar el commit solo localmente o retrasar el push para documentar mantiene al usuario bloqueado. En releases de prueba HA, despues de verificar GHCR debe hacerse commit/push inmediato de los artefactos de release y avisar al usuario. Antes de ese aviso queda prohibida cualquier actualizacion de documentacion de continuidad. "Documentacion minima", "solo digest", "rapida" o "para evitar contradicciones" son excepciones falsas y no sustituyen el cierre posterior. No hay excepciones documentales antes de desbloquear HA; despues del aviso hay que completar continuidad real con estado, version, digest, validaciones y pendientes mientras el usuario instala/prueba.

Actualizacion operativa 2026-06-28: por las restricciones del sandbox de Codex, `git commit` puede requerir escritura elevada en `.git` y `git push`/GHCR requieren red. Cuando el usuario pida explicitamente subir a Git o publicar una version HA, primero se revisa estado/diff y se ejecutan las validaciones necesarias; despues se usan directamente permisos elevados para `git commit`, `git push`, build/push GHCR o comandos de red necesarios, evitando intentos previos que ya se sabe que fallaran por sandbox.

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
- `rainmapper_core/geojson.py`
- `rainmapper_core/viewers/maplibre-viewer/`
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
- El 2026-06-22, `ghcr.io/cginebrosa/rainmapperha:0.2.100` seguia resolviendo manifest multi-arch `linux/amd64` y `linux/arm64` despues de la limpieza.
- El 2026-06-24, tras validar `0.2.111`, GHCR se limpio de nuevo: quedaron `0.2.111`, `latest` y cuatro entradas auxiliares sin tag del mismo push multi-arch/attestation. `ghcr.io/cginebrosa/rainmapperha:0.2.111` resolvio como index OCI con `linux/amd64` y `linux/arm64`. El repo remoto se verifico como `private`.
- El 2026-06-24 se publico `ghcr.io/cginebrosa/rainmapperha:0.2.112` y `latest` con digest multi-arch `sha256:37f841c9004ab879227d2cc67ee6f836d1e8c4adc14ae609ba9b7cf41b3637f7`, verificado como index OCI con `linux/amd64` y `linux/arm64`; quedo superado por `0.2.113` antes de validarse en HA.
- El 2026-06-24 se publico `ghcr.io/cginebrosa/rainmapperha:0.2.113` y `latest` con digest multi-arch `sha256:b8bdf0a9b433932c4fc7af012cd7d0876ea6d821aa7131b5e81458031c831627`, verificado como index OCI con `linux/amd64` y `linux/arm64`, y despues quedo validado/dado por bueno en HA.

### GHCR
Se borraron 179 versiones/entradas antiguas del paquete `rainmapperha` en GHCR. En ese momento quedaron `0.2.100`, `latest` y cuatro entradas auxiliares sin tag asociadas al mismo push multi-arch. El 2026-06-24 se repitio la limpieza tras validar `0.2.111`: quedaron `0.2.111`, `latest` y cuatro entradas auxiliares sin tag asociadas al mismo push multi-arch/attestation. Ese mismo dia se publicaron `0.2.112` y `0.2.113`; tras validar `0.2.113` en HA, se limpio GHCR de nuevo y quedaron solo `0.2.113`, `latest` y cuatro entradas auxiliares sin tag del mismo push multi-arch/attestation.

Auditoria real del 2026-06-24 tras publicar `0.2.118`: GHCR conserva `0.2.118,latest` con digest multi-arch `sha256:07ce37c45de5f705aeb1621f4fb680a7b2c9360014ee1ccbb95322e7815d0e96` y `0.2.117` como rollback con digest multi-arch `sha256:e12749d4b16a48c362f731eb4f03dbb850b71988061602396c51293ad0350d65`; cada una conserva cuatro entradas auxiliares sin tag del push multi-arch/attestation. Para futuras releases HA, la limpieza remota de GHCR pasa a ser parte del procedimiento estandar despues de validar la nueva version en HA: conservar solo la ultima version validada, `latest` y las entradas auxiliares del mismo push multi-arch. No borrar la version que declare `rainmapper-app/config.yaml` ni sus entradas auxiliares mientras HA pueda necesitar reinstalarla. Actualizacion 2026-06-25: `0.2.137` queda validada/dada por buena en HA con digest multi-arch `sha256:539c879d2c7f9dfc282d671b71c627a858b48d59778e3195ec2d0254accee928`; GHCR remoto queda limpio tras borrar las versiones/entradas antiguas de `0.2.134`, `0.2.135` y `0.2.136`, y conserva solo `0.2.137`, `latest` y cuatro auxiliares sin tag del mismo push multi-arch.

### Ficheros afectados
- `docs/codex-handoff.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/decisions.md`

### Estado
Completado operacionalmente el 2026-06-22 y revisado de nuevo el 2026-06-24. `0.2.113` quedo validado en HA y limpio en GHCR en su momento. Actualizacion 2026-06-25: `0.2.137` queda validada/dada por buena en HA; despues se puso el repo remoto en privado (`private=true`, `visibility=private`, rama `inicial`) y se limpio GHCR remoto conservando solo `0.2.137`, `latest` y cuatro auxiliares sin tag del mismo push multi-arch.

## 2026-06-26 - Capa MapLibre IDW calculada en cliente

### Decision
Anadir una capa experimental `IDW` en MapLibre para estimar un campo zonal de la metrica activa. La capa se calcula en el navegador solo para el viewport visible, se renderiza como `fill` GeoJSON con opacidad configurable y queda protegida por el permiso de usuario `can_use_estimated_field`.

### Motivo
El heatmap nativo de MapLibre usa densidad ponderada; por tanto, zonas con muchas estaciones pueden verse mas intensas que zonas con valores meteorologicos mayores pero menos estaciones. Para lluvia, temperatura, humedad y velocidad de viento se quiere una lectura aproximada de promedio espacial, no de concentracion de observaciones.

### Consecuencias
La Raspberry Pi no calcula la interpolacion; solo sirve el GeoJSON de estaciones y `config.js`. La carga pasa al dispositivo cliente y se limita al area visible. Los settings por dispositivo controlan activacion, opacidad, radio fisico, calidad, suavizado y correccion por altitud. Los parametros tecnicos de radios en km, radio fisico maximo, tamano fisico de celda en km, potencia IDW y gradiente termico viven en `rainmapper-app/config.yaml` para ajustar pruebas en HA sin publicar una nueva imagen. Las metricas ausentes/no numericas no participan en la interpolacion; las temperaturas negativas son valores validos. El viento se trata inicialmente como escalar, dejando una posible visualizacion vectorial con flechas para una fase posterior.

### Ficheros afectados
- `rainmapper-app/config.yaml`
- `rainmapper-app/run.sh`
- `rainmapper-app/app/web_server.py`
- `rainmapper_core/viewers/maplibre-viewer/`
- `users.example.json`
- `tests/test_web_server_auth.py`

### Estado
Publicado inicialmente en imagen HA `0.2.138` con digest multi-arch `sha256:c16e87c8e86186e09dc04f77759ffe2c1f1cbf0fa97e6b5e015364d38530cd17`. `0.2.139` intento limitar el azul de lluvia cero, pero en HA siguio mostrando un comportamiento demasiado parecido y expuso problemas de sincronizacion entre botones `Heatmap`/`IDW`. `0.2.140` corrigio la incompatibilidad Heatmap/IDW, hizo que los botones rapidos no persistieran, mantuvo persistencia solo desde Settings, paso radio y tamano de celda IDW a km configurables (`maplibre_estimated_field_radius_*_km`, `maplibre_estimated_field_grid_*_cell_km`) y evito que lluvia cero generase area visible por si sola. `0.2.141` y `0.2.142` ajustaron el refresco visual del source/layer IDW. `0.2.143` movio IDW por encima de los circulos de estacion para que la opacidad pueda taparlos. `0.2.144` mostro en Settings los valores efectivos de radio, celda y potencia `p` procedentes de `config.yaml`. `0.2.145` optimizo el refresco IDW con cache por clave de calculo para evitar recalcados duplicados y reconstrucciones innecesarias al alternar capas o refrescar estilo.

La implementacion de `0.2.145` hace que `updateEstimatedFieldLayer()` evite recalcados duplicados con una clave de calculo que incluye periodo, revision de datos, metrica, escala, viewport, canvas, fuentes activas y parametros IDW; si la clave no cambia reutiliza el GeoJSON calculado. Tambien limita a uno los callbacks `idle` pendientes cuando el estilo MapLibre aun no esta listo y evita reconstruir la capa de estaciones al activar IDW. Esta pauta queda documentada en `docs/architecture.md` como patron para futuras capas calculadas en cliente, por ejemplo el predictor de floradas de setas.

## 2026-06-27 - Redisenar WebUI Users como accordion server-side

### Decision
Refactorizar la pagina Home Assistant `Users` a una lista compacta tipo accordion, generada desde helpers Python en `rainmapper-app/app/web_server.py`, sin introducir framework frontend ni build step. Mantener todos los contratos POST existentes y anadir salvaguardas de confirmacion para acciones sensibles.

### Motivo
La tabla original funcionaba, pero ocupaba demasiado espacio por usuario y era dificil de mantener cuando habia varios dispositivos. La WebUI vive dentro de Home Assistant/ingress, por lo que conviene conservar HTML/CSS/JS embebido y dependencias cero. Helpers Python pequenos dan suficiente estructura sin crear una arquitectura frontend separada.

### Consecuencias
Cada usuario se muestra como una fila compacta con resumen, permisos y ultimo dispositivo visto; solo un usuario queda expandido cada vez. La creacion pasa a modal. Las acciones `Save user`, `Set password`, `Reset password`, `Delete user`, `Delete device` y `Delete all devices` requieren confirmacion del navegador. `users.json` incorpora campos de auditoria `created_at`, `updated_at` y `last_change`; los timestamps siguen en formato UTC `...Z`, ahora generados con `datetime.now(UTC)` para evitar `datetime.utcnow()` deprecado. La UI debe validarse dentro de Home Assistant porque el espacio real depende del iframe/ingress.

### Ficheros afectados
- `rainmapper-app/app/web_server.py`
- `tests/test_web_server_auth.py`
- `docs/ui/user-management-redesign.md`
- `docs/ui/user-management-accordion-prototype.png`

### Estado
Publicado en imagen HA `0.2.146` con digest multi-arch `sha256:fefbc22459cd8e388f6660ac533293557f157a33e3a1f8dc1cb781359a6c8ca8` y commit `ab5b2dd`. Validacion local: `./scripts/smoke-test.sh` OK. Validada/dada por buena en HA el 2026-06-27.
