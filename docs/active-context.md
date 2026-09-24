# Contexto activo — HA 0.2.321 publicada, instalación pendiente (24/09/2026)

Leer primero [codex-start-here.md](codex-start-here.md). Este archivo basta para
retomar; [todo.md](todo.md) amplía las prioridades. No arrancar leyendo informes
ni el [archivo histórico](reports/session-context-before-close-2026-09-22.md).

## Estado actual: release HA 0.2.321

- Usuario acepta la UI local y autoriza publicar. **GHCR 0.2.321/latest
  verificados**, mismo digest
  `sha256:4ec6de37a3d926d1b555c6065152dd94a28ce90b68bc1be008ac008fa73a025d`,
  manifests `linux/amd64` y `linux/arm64`. Script terminó con código 0.
- Incluye capa de observaciones, permisos y opción móvil por defecto desactivados,
  spiderfy con fechas y cierre al repetir pulsación, ficha GIS/nombres comunes/luna;
  también avisos históricos diferenciados y calendario activo que vuelve a hoy.
- **Regla general aclarada por el usuario:** entrenamiento/precálculo sólo si el
  cambio afecta a esos procesos, entradas, contratos operativos o artefactos.
  UI, permisos y mensajes se validan proporcionalmente, sin exigir ese circuito.
  Actualizados `AGENTS.md`, `release-flow.md` y `codex-start-here.md`; no es una
  excepción por versión. Los trabajos necesarios los sigue lanzando el usuario.
- Smoke **1.751 pruebas, 52 skips, OK**; navegador final OK. HA local y worker
  reconstruidos/recreados desde el mismo código, paridad efectiva **224/125** sin
  diferencias. Worker libre antes de reiniciar, coordinadores/credenciales e
  identidad preservados. Observaciones repo/local y suspensiones con hashes intactos.
  Después sólo bump, cache-busters, changelog y documentación; metadatos locales
  de aceptación HA 0.2.320/worker 1.1.6. Ningún entrenamiento ni precálculo lanzado.
- Código, pruebas, versión y cierre documental reunidos en el commit único
  `Release Home Assistant 0.2.321`; consultar Git para hash/estado del push.
  Observaciones privadas excluidas. [Informe](reports/release-ha-0.2.321-2026-09-24.md).
- **Instalación real pendiente del usuario.** Última versión confirmada en HA real:
  0.2.320. No afirmar 0.2.321 instalada sin revalidar. Los bloques inferiores son
  evidencia histórica de preparación; sus pendientes de publicación quedan
  resueltos por esta entrega.

## Evidencia local de la capa de observaciones (23–24/09)

- Usuario autoriza implementación: ojos bajo histórico, selector superior
  izquierdo con especies/recuentos, setas y ficha con especie, fecha, área/microárea,
  abundancia, hosts, bosque y observador. Añadido ID para distinguir registros.
  Compatible con predicción/histórico: todas las fechas, sin recálculos ni worker.
- Contador para coincidencias; despliegue radial con líneas a coordenadas reales
  y fechas pequeñas DD/MM/AAAA. Conserva todos los registros. Grupos grandes con
  ocho iconos por página; mover el mapa o pulsar fuera repliega.
- Permiso `can_use_observations_map`, false por defecto incluso admin, en Usuarios
  → Observation map access. No se ha activado a nadie automáticamente.
- Usuario elige ajuste **general** móvil además del permiso individual:
  `maplibre_observations_mobile_enabled: false`, en `rainmapper-app/config.yaml`
  options/schema y `rainmapper-local/options.local-ha-ui.json`. En configuración
  del complemento: Allow observation map on mobile. Reiniciar HA tras cambiarlo;
  no el worker. Heurística: ancho ≤767 px o táctil con altura ≤600 px.
- HA local reconstruido/recreado y HTTP 200, 223 archivos efectivos sin diferencias.
  Config.js confirma móvil false. Backend: 515 observaciones/17 especies;
  listado 1.573 bytes, página máxima 4.982 bytes, puntos totales 30.530 bytes.
- Validación final: **smoke 1.744 pruebas, 52 skips, OK**, 76,990 s; navegador OK,
  incluidos permisos, revocación, spiderfy/fechas, fichas, predicción activa,
  histórico y móvil desactivado/habilitado sin perder fecha histórica.
  Logs `/private/tmp/rainmapper-observations-{smoke-final,browser}.log`.
- Worker sin reiniciar; observaciones privadas y suspensiones con hashes intactos.
  Sin entrenamientos/precálculos, bump, commit ni release nueva. Pendiente de
  aceptación del usuario en local. HA real sigue 0.2.320; no incorpora estos cambios
  ni los ajustes históricos de abajo. Antes de publicar sigue siendo obligatoria
  la validación conjunta HA/worker correspondiente.
  [Especificación](mushrooms/prediction-map-specification-es.md) ·
  [Evidencia local](reports/observations-map-local-2026-09-23.md).
- Corrección posterior a la prueba del usuario: la ficha omitía hosts/bosque GIS
  aceptados porque sólo leía `observed_*`. Ahora combina valores de campo y
  `site_context.gis_recovery.values`, validando coordenadas con `valid_recovery`;
  marca aportes GIS como «GIS aceptado» y no consulta GIS ni modifica registros.
  Pruebas dirigidas posteriores: 27 OK, incluidas fusión, procedencia y rechazo de
  recuperación desfasada/no válida. El smoke de 1.744 corresponde al estado previo
  a esta corrección; no se presume validación de una nueva release. Navegador
  repetido OK con marcas GIS en hosts/bosque. HA local reconstruido/recreado:
  223 archivos efectivos sin diferencias y registro del usuario comprobado dentro
  del contenedor; hosts/bosque aceptados presentes. Registros y suspensiones intactos.
- Ajuste de nombres pedido después: hosts y bosque se muestran con nombres
  comunes/etiquetas del idioma del mapa; científico sólo si falta traducción del
  host. Probado ca/es/en y fallback, 7 pruebas del módulo OK. HA local reconstruido
  y recreado, HTTP 200, 223 archivos efectivos sin diferencias y nombres catalanes
  comprobados dentro del contenedor. No cambió el frontend ni se repitió el smoke.
- Fase lunar solicitada después (24/09): imagen SVG con iluminación calculada
  junto a Fecha/Área y cuatro textos traducidos. Función compartida
  `rainmapper_core.lunar_phase.lunar_phase`: fase continua, fracción iluminada,
  creciente/menguante, categoría y versión; fecha sin hora a mediodía UTC.
  Sólo se calcula al abrir la ficha, según fecha de observación. Preparada para
  otros consumidores; no se integra todavía en entrenamiento.
  12 pruebas dirigidas OK, incluidas referencias USNO y convenciones temporales;
  navegador OK con las cuatro imágenes, encaje sin overflow e histórico activo.
  HA local reconstruido/recreado, HTTP 200 y 224 archivos efectivos sin diferencias.
  Observación `obs_20250904_0026` comprobada dentro del contenedor: 04/09/2025,
  creciente, fracción ≈0,8751. Worker conserva ID/arranque/imagen; huellas de
  observaciones repo/local y suspensiones intactas. Sin nueva release.
- Interacción posterior (24/09): repetir pulsación de una seta cierra su ficha,
  también mientras carga; otra observación abre su ficha. Repetir pulsación del
  contador abierto repliega el spiderfy y cierra su ficha. Comprobado en navegador
  para setas individuales/desplegadas, cambio de registro, cierre sin petición,
  carga pendiente y reapertura del grupo. HA local reconstruido/recreado, HTTP 200
  y paridad efectiva 224 archivos sin diferencias; no se opera el worker.

## Diagnóstico actual: histórico durante el runner (23/09)

- HA real 0.2.320 instalada, revalidada por `diagnostics/runtime_state.json`
  mediante SMB LAN. Worker 1.1.6 responde. Captura del usuario anterior al
  precálculo: no atribuirla al background ocupado observado después.
- Runner 11:00:17–11:06:51; `CURRENT.json` cambió a las 11:04:03 y la copia
  para el worker se publicó a las 11:06:51. Worker sincronizó mapa 11:07:04 y
  tomó precálculo 11:07:07. Durante el desfase, el código rechaza la copia
  desactualizada y el histórico muestra el texto genérico «worker no disponible».
  Mecanismo reproducido con prueba dirigida, 1 test OK; falta el error concreto
  de aquella consulta para atribuirle causalidad absoluta. Timeouts de conexión
  observados son otra evidencia, sin causa aislada.
- Tras «pues lo hacemos», corregidos en local los avisos del histórico: separan
  actualización, sincronización, ocupación, incompatibilidad, timeout y errores.
  Conservan fallback local y controles de coherencia. Fecha del progreso DD/MM/AAAA.
  HA local reconstruido/recreado, HTTP 200 y 220 archivos efectivos sin diferencias.
  Pruebas dirigidas: 52 OK; navegador OK, incluidos avisos traducidos y fallback.
  Worker existente sin reiniciar: mismo contenedor/arranque/imagen. Coordinadores,
  tokens, suspensiones y observaciones privadas conservan sus huellas.
  Cambios pendientes de commit; ninguna release nueva ni trabajos lanzados por
  Codex. HA real sigue con 0.2.320 y aún no incorpora esta corrección. Esto no
  constituye la validación del par HA/worker requerida para una futura release.
  [Evidencia y límites](reports/historical-worker-runner-2026-09-23.md).
- Ajuste posterior solicitado: calendario derecho con histórico activo vuelve
  directamente a hoy; el indicador superior mantiene el selector de fecha.
  Tooltips ajustados a cada acción. HA local reconstruido/recreado otra vez,
  HTTP 200 y 220 archivos efectivos sin diferencias. Navegador OK: selector
  desde indicador, regreso directo sin modal, datos actuales y botón desmarcado;
  log `/private/tmp/rainmapper-history-toggle-browser.log`. Pendiente de publicar
  junto con los avisos anteriores; usuario confirma HA real 0.2.320 funcionando.
- SMB LAN actual: `192.168.0.121` en `/Volumes/share` y `/Volumes/media`.
  Revalidar montajes; sus nombres no identifican por sí solos la ruta de red.

## Publicación HA 0.2.320 y validación del 22/09

- Usuario acepta el calendario («funciona mucho mejor») y pide publicar HA.
  Lanzó el circuito en HA local tras preparar la candidata y confirma que
  terminaron el entrenamiento y precálculo. Resultados auditados antes de publicar.
- Candidata **HA 0.2.320 / worker local 1.1.6**, ambos construidos del worktree
  de aquella publicación y recreados. HA arrancó `2026-09-22T20:18:43Z`, worker `20:19:53Z`.
  Imágenes `sha256:ee142a887d10b26ca9a588704ddf177fa27539004faeec0e5cff14a5b3146095`
  y `sha256:ece494abb1a4669e51ff1bf68c6c5d8978c611a9e0bc19a961679df0be0856a8`.
  Etiqueta HA 0.2.320; `/health` worker 1.1.6, idle en ambos carriles al comprobar.
  El entorno HA local sigue declarando `local-ha-ui` como versión de ejecución.
- Paridad efectiva **220/125 archivos sin diferencias**. Coordinadores/tokens,
  suspensiones y observaciones privadas comparados antes/después, intactos.
  Evidencia local: `tmp/release-0.2.320/{before,after}.json` y
  `tmp/historical-map-20260922/parity.json`.
- Smoke final **1.734 pruebas, 52 skips, OK**, 80,957 s. Se actualizaron las
  expectativas de versión del worker que fallaron en la primera pasada; ningún
  cambio funcional adicional. Log `/private/tmp/rainmapper-0.2.320-smoke-final.log`.
- **Reconstrucción/base/multiversión nuevos completados y auditados**. Usuario
  lanzó `worker_job_xlB0PxODkcHOogIr` a las 20:22:35 UTC; encadenó base
  `worker_job_nS7GPTKDbODxZxub` y multiversión `worker_job_I58iOv160Z309ez5`.
  Terminó a las 20:36:04 UTC: **792/792 ajustes correctos, cero fallos**.
  Tres resultados verificados y limpieza terminal completa; reconstrucción/base
  promovidos. Registro instala las cinco versiones del lote
  `operational_20260922T202508Z`, puertas de promoción passed y revisiones de
  entrada coincidentes. Auditoría: `tmp/release-0.2.320/training-audit.json`.
  Política/suspensiones y observaciones privadas comparadas, intactas.
- **Precálculo local revisión 74 completo, recibido y activo**, trabajo
  `worker_job_7Xbqi9U1m2X2` de 20:40:59–20:49:04 UTC. Recibo, archivo SQLite
  (48.414.720 bytes/SHA), identidad, cinco generaciones nuevas y recuentos
  comprobados. 994 respuestas / 208 payloads compartidos; limpieza terminal completa.
  Auditoría: `tmp/release-0.2.320/precompute-audit.json`. Se validó el circuito
  nuevo completo; no se reutiliza la excepción de 0.2.319.
  No lanzar trabajos desde Codex ni reiniciar el worker mientras esté ocupado.
- **GHCR 0.2.320/latest verificados**, mismo digest
  `sha256:6200c13ef2a09dc096dd821e78efecd791cad94af4f927658b053ea0a64132c5`,
  manifests linux/amd64 y linux/arm64; script terminado con código 0.
  Código, pruebas, bump y cierre documental se reúnen en el único commit
  `Release Home Assistant 0.2.320`; consultar Git para hash/estado del push.
  Observaciones privadas excluidas y conservadas. [Informe y circuito](reports/release-ha-0.2.320-2026-09-22.md).
- Instalación de 0.2.320 en HA real confirmada después por SMB (23/09).
  Histórico utilizado por el usuario según captura; no copiar usuarios ni modelos desde local.

## Modo histórico aceptado en local: alcance y evidencia previa al bump

- Calendario debajo de predicción, fecha común del mapa y modelos actuales;
  meteorología hasta D−1. Permiso `can_use_historical_map` independiente y false
  por defecto incluso admin. Ningún usuario habilitado automáticamente.
- Ajuste local/worker compartido con predicción, fallback y modal. Sólo encuadre
  + margen de las capas; ayuda para acercarse antes. Caché por fecha/período/
  generación: zoom dentro de cobertura no consulta; ampliar pide sólo zonas
  nuevas. GeoJSON en memoria, sin temporales en disco.
- HA local y worker existentes reconstruidos/recreados, worker idle comprobado
  antes. Paridad efectiva **220/125 archivos**, sin diferencias. Imágenes HA
  `sha256:0ebdcaecc8cb5de6325fb6de7a79933bdb6036d2aafdca3aca19636ffa3ca440`
  y worker `sha256:72639e326a726f403f443503fab82c5de51f39cfab1668e163a52a17b0e91e0b`.
  Sin bump/publicación; HA real no se ha actualizado.
- Smoke **1.734 pruebas, 52 skips, OK**; navegador comprueba permiso, fecha,
  fallback, ficha, zoom y regreso a zonas cargadas sin recálculo. Lectura real
  en contenedores: 80 estaciones ≈0,7–0,8 s frío / 0,15–0,17 s caliente; extensión
  28 estaciones ≈0,1 s. Mac, sin espera HTTP/interfaz; no son medidas RPi.
- Usuario activó el permiso de Carlos y confirmó carga con captura: 20/09/2026,
  64 estaciones, 6,1 s. Corrigidos contraste/progreso del modal, fecha de cabecera
  y etiqueta sin solapamiento. Estación AEMET con coordenadas diarias ausentes:
  usa ubicación comprobada del catálogo, con procedencia explícita. Fichas sin
  modal general, detalle bajo demanda y caché de ocho estaciones en la pestaña.
  Ajuste posterior solicitado: fecha de la etiqueta histórica en DD/MM/AAAA,
  como la cabecera. HA local reconstruido; comprobación del texto y paridad OK.
  Selector rediseñado después: calendario propio claro, estilo del buscador,
  mes/año directos, días táctiles, atajos Ayer/Hace un año y teclado. Fechas futuras
  bloqueadas; navegar no calcula hasta Aplicar. Navegador y capturas móvil/escritorio
  verificados; HA local actualizado con paridad 220/125, worker sin reiniciar.
- Prueba final HTTP/navegador real OK: 141 estaciones de 2025, ambos destinos,
  ficha/caché/zoom/vuelta a hoy sin errores. Espera total 0,641 s local / 48,268 s
  worker, aunque lector 374/328 ms: falta desglosar espera fuera del cálculo.
  No se modificaron asociaciones ni planificación del worker para esta función.
- Coordinadores/tokens, política y observaciones privadas conservados. Usuarios
  sólo con cambios del usuario; cuentas temporales de prueba retiradas al terminar.
  Sin SSH ni lanzar entrenamiento/precálculo. Se observó un precálculo del
  coordinador principal en el log del worker durante la sesión; no lo lanzó Codex.
- [Diseño](mushrooms/prediction-map-specification-es.md#modo-histórico-del-mapa-22092026)
  y [evidencia/límites](reports/historical-map-local-2026-09-22.md).
  Interfaz aceptada y circuito completo/publicación en el bloque actual.
  Excepción 0.2.319 no extensible.
- Cierre documental anterior revisado e incluido con esta release.
  No incluir observaciones privadas en commits.

## Snapshot anterior: cierre y revalidación SMB

- **HA 0.2.319 publicada**, commit `dda52e8`, enviado a `origin/inicial`.
  GHCR versión/latest verificados con el mismo digest
  `sha256:fcdf067a7ffc41a89d3715b6dc367348f57ce9711879c56bd0b28bf3b770e65e`,
  manifests linux/amd64 y linux/arm64. Script de publicación terminó con código 0.
- **HA real 0.2.319 instalada**, confirmada por el usuario y revalidada por SMB
  LAN (`192.168.0.121`, `/Volumes/share-1`). `diagnostics/runtime_state.json`
  declara versión 0.2.319 y arranque `2026-09-22T03:26:45.197Z`; el registro
  coincide. **Detalle completo todavía no validado en real:** las páginas del mapa
  no se persisten y SMB no permite comprobarlas. Se ha consultado al usuario sobre
  completar la prueba mediante HTTP LAN. [Evidencia y límites](reports/ha-0.2.319-smb-2026-09-22.md).
- **HA local** `rainmapper-local-rainmapper-ha-ui-1` running; imagen
  `sha256:6c52d5e2bf5c9bba161239dcfb506937ecc56d6c8cfb36b08683b0641b845992`.
  Contiene el cambio aceptado, construido antes del bump mecánico: no afirmar que
  sus metadatos sean 0.2.319. Puerto 8101.
- **Worker** `rainmapper-worker`, 1.1.5, running/healthy; `/health` reconsultado al
  cierre: foreground y background idle, sin trabajos activos, cachés válidas.
  Imagen `sha256:571041c90d6d587b124024cf69cec004b74f172d8db9d97300f9a14f5d44bc18`.
  Worker compartido con HA real y HA local; puerto 8110. Revalidar antes de operarlo.
- Coordinadores preservados en el despliegue y comprobados por hashes:
  principal `http://100.111.77.48:8100`, adicional `http://rainmapper-ha-ui:8100`.
  La presencia de URL Tailscale persistida no autoriza usar Tailscale/SSH.
- Política **local** reconsultada en
  `docker-data/mushroom-data/mushroom_ml_prediction_policy.json`: `shadow`,
  `consensus_v1`, siete suspensiones; conservarlas. En SMB real se comprueban siete
  suspensiones y ausencia de `recommendation_policy` en el archivo separado;
  el código de 0.2.319 usa `legacy` por defecto. No se ha consultado el modo de
  un runtime ya cargado. Publicar no activa el filtro automáticamente.
- Git antes del cierre documental: sólo `mushroom-data/mushroom_observations.json`
  modificado, privado/preexistente. No editar, revertir ni incluir en commits.
  Este cierre modifica documentación; no asumir commit/push del cierre sin mirar Git.
  Revisión SMB posterior: HEAD sigue en `dda52e8`; documentación pendiente de commit.
  Corregidos 32 enlaces relativos del archivo histórico trasladado a `reports/`.

## Qué se acaba de entregar

**0.2.319: detalle completo de variables fuera de rango.** El servidor normal
transportaba sólo tres ejemplos aunque contara 33; no bastaba añadir scroll.
Ahora una consulta opcional `applicability_page` de una especie/día carga páginas
compactas de 32 filas al abrir el aviso; lista con scroll, contador y Cargar más.
Comprueba fecha, zona horaria y procedencia antes de incorporar detalle. Errores
visibles y posibilidad de reintento. Normalización, IFF y payload normal intactos.
El detalle vuelve a resolver la semana de esa especie y consulta un modelo/día:
puede añadir latencia al abrir, no entrena ni precalcula. Máximo sintético <8 KiB
por página. No equivale a una corrección de sensibilidad ni de fiabilidad del IFF.

Validación: 97 pruebas dirigidas también en imagen HA; navegador con 47 consultas,
33 filas, scroll, paginación, fallos y cambio de datos. HA local/worker reconstruidos
antes de la prueba, paridad efectiva 217/117 archivos. Usuario confirma «funciona».
Smoke final 1.725 pruebas, 52 skips, correcto. Después sólo bump/cache-busters y
textos documentales. [Informe](reports/release-ha-0.2.319-2026-09-22.md).

**Excepción sólo para 0.2.319:** usuario autorizó expresamente publicar con esa
validación sin repetir entrenamiento/precálculo. El circuito local anterior
(reconstrucción/base/multiversión y precálculo completo revisión 73, 792 ajustes)
no se presenta como validación de este contrato nuevo. No generalizar la excepción.
Los entrenamientos y precálculos los lanza el usuario («Los lanzo yo en HA local»).

## Decisiones vigentes que afectan al siguiente paso

**Consenso de recomendaciones (incluido desde 0.2.318):** Workers y trabajos →
Modelos de predicción → Desactivado / Solo comparar / Aplicar
(`legacy` / `shadow` / `prudent`). En Ou de reig, Edulis y Pinícola, cuando hay
recomendación favorable e IFF ≥60, consulta exactamente dos familias alternativas
fijas de la semana, posteriores al ganador en el ranking sellado. Aplicar exige
las dos disponibles y ≥60; si discrepan o faltan, se abstiene. Conserva ganador e
IFF, no suaviza diferencias espaciales. Aereus/deliciosus quedan fuera de este veto.
Ausencia de alternativas no es desacuerdo. Descartes por datos cuentan sólo
familias evaluadas; no las que el mapa no ejecutó. Conclusión verde/roja, ámbar si
faltan alternativas, debajo de temporada; un Detalle con perfiles visibles.

El usuario exige evitar más errores que aciertos perdidos. Rechazó la regla
global que evitaba 130 errores pero perdía 156 aciertos. La retrospectiva selectiva
39/10 motivó esta dirección, **no acredita ese balance futuro ni el selector
completo por área**: ámbito elegido tras ver datos, observaciones reutilizadas por
plazo y familias correlacionadas. Mantener modo reversible y medir con nuevas
observaciones/GBIF revisado antes de ampliar especies o activar por rutina.

**Querigut/rovelló:** el informe del lote real de septiembre reprodujo 99→90,
no encontró consenso general sobre esos IFF y detectó exclusiones por huecos de
lluvia/estado hídrico e imputación en V5/V6. Suelo/hosts GIS ausentes y estado
hídrico son problemas distintos; las microáreas inspeccionadas tenían retención
SoilGrids. No atribuirlo todo a Francia, ni tratar 99 como 99% de acierto.
El filtro de consenso no cubre deliciosus. Informe opcional:
`docs/reports/querigut-predictor-2026-09-21.md`; conclusiones de ese snapshot,
no prueba de los modelos actuales después de otros entrenamientos.

**Memoria (corregida desde 0.2.318):** verificación secuencial de respuestas y
recepción de artefacto por bloques, conservando SHA, límites y activación atómica.
Benchmark histórico con la misma copia en Mac: pico 825→304 MiB, 16,00→15,66 s;
no es medida del servidor RPi. Falta medir en real y explicar consumo inicial y
retención/cachés. No está demostrada una fuga. La percepción de lentitud tampoco
se aisló en un A/B con mismos datos/modelos. Ver informe de memoria si se retoma.

**Datos de lluvia:** copiar `Data/` no actualiza el GeoJSON de `PublicData/`.
La ficha de estación puede seguir mostrando el mapa generado antes; la predicción
puntual lee su histórico meteorológico por otro camino. Comprobar generación,
configuración y modelos antes de afirmar paridad entre HA real y local.

**Ciencia conservada:** SMI común regulado + PM + una capa 0–30 cm con IDW;
modelo simple sólo visual. Host/suelo GIS filtran compatibilidad en el mapa;
no inferir entradas entrenadas por el nombre del modelo: mirar sus columnas.
No cambiar IDW, suspensiones ni modelo operativo por intuición o por acuerdo visual.

## Próximos pasos, por orden

1. Resolver diagnóstico del aviso genérico de worker en histórico durante el
   runner, sin mezclar generaciones. Completar la prueba del detalle de
   variables en HA real, para Servidor local y worker cuando estén disponibles;
   requiere consulta viva del mapa, pues las respuestas no se persisten.
2. Medir memoria de HA real con registros persistidos: arranque, reposo, consultas
   y recepción/activación tras trabajos que lance el usuario. Separar RSS/cgroup/
   caché de archivos y tiempos por fase. No generar artefactos para diagnosticar.
   Copia diagnóstica en `tmp/ha-0.2.319-smb-20260922/`: RSS y cgroup disponibles,
   sin desglose de cachés. No interpretar cgroup menos RSS como caché medida.
3. Revisar resultados reales del modo de consenso elegido y cobertura de las dos
   alternativas. Cambiar modo sólo si el usuario lo pide; registrar calidad y
   recomendaciones perdidas, no prometer que resuelve hipersensibilidad.
4. GBIF sigue pendiente de revisión manual del usuario. GIS general, WU, indicador
   de worker y limpieza no se reabren automáticamente; pendientes en `todo.md`.

## Archivos útiles y accesos

- Detalle: `rainmapper_core/{mushroom_prediction_map,mushroom_map_model_runtime,
  mushroom_ml_multiversion_comparison,mushroom_ml_runtime_inference}.py`,
  `rainmapper_core/viewers/prediction-map/prediction-mode.{js,css}`,
  `mushroom-data/mushroom_labels.json`.
- Consenso: `rainmapper_core/mushroom_recommendation_policy.py`, política separada
  `mushroom_ml_prediction_policy.json`, UI `rainmapper-app/app/mushroom_model_settings_ui.py`.
- Memoria: `rainmapper_core/mushroom_predictor_precompute.py`, recepción en
  `rainmapper-app/app/web_server.py`; informe `docs/reports/ha-memory-precompute-2026-09-22.md`.
- Pruebas del detalle: `tests/test_mushroom_map_model_runtime.py`,
  `tests/test_mushroom_ml_runtime_inference.py`, `tests/prediction_map_browser_check.mjs`.
- Local: `http://127.0.0.1:8101/protected/prediction-map/index.html`;
  Workers `/mushrooms/workers`. Datos `docker-data/mushroom-data/`; geografía y
  derivados `docker-media/rainmapper/`. HA real usa sus propios `/share` y `/media`.
- Logs de release: `/private/tmp/rainmapper-0.2.319-{smoke-final,publish}.log`.
  Los temporales pueden desaparecer; el informe de release conserva resultados.

## Límites de actuación

Release 0.2.321 autorizada y publicada; no deducir autorización para otra publicación.
Instalar/parar/arrancar HA real corresponde al usuario. No SSH sin petición
expresa, no Tailscale ni montar SMB por Tailscale. SMB LAN `/Volumes/share-1`
revalidado; `/Volumes/share` y `/Volumes/media` apuntaban a Tailscale y no se usaron.
Conservar coordinadores y volúmenes; revisar ambos carriles antes de tocar worker.
No inferir permiso para entrenar/precalcular de una solicitud de diagnóstico o
release. Recursos RPi4 4 GB estrictamente limitados. La excepción de 0.2.319 no
sustituye `AGENTS.md` ni `docs/release-flow.md` para una futura release.
