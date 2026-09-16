# Active Context

## Release 0.2.307 — 16/09/2026

Imagen verificada en GHCR: `0.2.307` y `latest` comparten digest
`sha256:d8c0c1b110b9d700e980e5409888374b61d1dcd35f0203260f0145c15af8ca46`,
con manifests amd64 y arm64. Publicación autorizada expresamente tras revisión local.
[Informe y evidencia de release](reports/ha-release-0.2.307.json).

Incluye IFF en tres idiomas, colores por favorabilidad, ayuda desplazable,
fechas con día de semana, filas compactas de especies e inventario GIS completo.
HA local y el único worker existente (1.1.3) reconstruidos; 200/107 archivos
efectivos coinciden con el código candidato. Destinos del worker conservados.
Smoke final: 1613 tests, 48 omitidos; navegador correcto y sin desbordamiento móvil.
La cadena local completó reconstrucción, entrenamiento base, 714 ajustes
multiversión y precálculo activado. El cambio posterior de datos KMga4 se validó
con ambos lectores y consulta local del punto; no se repitió esa cadena por él.

Entrega congelada: `tmp/release-0.2.307/ha-data/mushroom-data/`, siete JSON para
`/share/rainmapper/mushroom-data/`. El usuario indica haber copiado sin backup;
no se ha comprobado el destino ni instalado/reiniciado HA real desde el agente.
**Revisión científica adicional en pausa por petición del usuario.** No modificar
la entrega congelada. Hay 471 códigos geológicos aceptados solo por litología,
sin tendencia de suelo, además de 17 pendientes. No está cerrada la investigación
de suelos de todas las formaciones. El cambio IFF es presentación; las revisiones
GIS no reescriben modelos ni precálculos existentes.
Observaciones privadas y documentación GBIF ajenas quedan fuera del commit.

## Antecedente: release 0.2.305

Estado del 16/09/2026. **HA 0.2.305 publicada y verificada en GHCR**: versión y
`latest` tienen el mismo digest y manifests amd64/arm64. Actualización aceptada
por el usuario tras revisar HA local; instalación de HA real pendiente del usuario.
[Informe de release](reports/ha-release-0.2.305.json).

Incluye encuadre móvil tras login/recarga, cabecera de predicción compacta,
fila Zona/Fecha alineada (selector 98×24 px), Cancelar compacto y etiqueta «Local».
Worker es el valor inicial sin preferencia guardada; un rechazo inicial 503 por
indisponibilidad/ocupación se reintenta una vez en Local sin modificar el setting.
No se reintentan trabajos ya aceptados ni errores genéricos o cancelaciones.
[Informe móvil y pruebas](reports/map-mobile-login-2026-09-16.md).

Puerta local completada desde la candidata: HA y worker reconstruidos y recreados,
198/106 archivos efectivos idénticos al worktree, coordinadores persistidos sin
cambios. Smoke 1.600 tests/48 omitidos correcto; navegador 29 peticiones correcto.
Safari local: consulta real Worker 2,14 s total / 1,42 s cálculo; fallback controlado
Worker → Local conserva el setting. Worker permanece en 1.1.2, sin release nueva.
No hay cambios científicos ni GIS: no regenerar mapas, entrenar, recalcular ni
volver a subir datos para instalar 0.2.305. Recargar el visor tras actualizar.
Pendiente confirmar en iPhone físico el comportamiento tras login y recarga.

HA 0.2.304 fue probada por el usuario en real, incluyendo ejecución por worker.
La disponibilidad requirió habilitar `primary` en el override de mapa del M1;
[diagnóstico anterior](reports/map-worker-real-ha-2026-09-16.md).
Conservar los originales de media hasta validar el funcionamiento en HA real.
No repetir uploads de GiB ni ejecutar comandos de preparación al primer arranque.
Ediciones ajenas de `mushroom-data/mushroom_observations.json` y documentación GBIF
quedan fuera de esta release; datos privados locales y reales preservados.

## Geografía portable: evidencia de la release 0.2.304

La nueva versión lee archivos ordinarios desde `/media/rainmapper/geography`.
No hay comandos de primer arranque, symlinks ni recibos dependientes del equipo
para instalar los datos en HA. GIS y SoilGrids usan `mushroom-GIS`; mapa resuelve
sus referencias al mismo archivo compartido mediante un manifiesto portable.
Configuración de reserva en `geography/map-config.json` si no hay una explícita.

- Smoke actual: 1.600 tests, 48 omitidos, OK. Ambos contenedores reconstruidos y
  recreados, 198/106 archivos efectivos sin diferencias. Versiones 0.2.304/1.1.2.
- Cuatro lecturas GIS/contextos iguales a la estructura anterior y seis consultas
  autenticadas con igualdad local/worker, incluso concurrentes; permisos básicos,
  401 sin sesión y cancelación correctos. El usuario confirmó que vuelve a
  funcionar el ejecutor local tras arrancar los contenedores.
- Primer acceso sin red, sistema y media de solo lectura: configuración detectada,
  ejecutor local listo, inventario GIS de 13 archivos. Ninguna preparación al arrancar.
- Worker reutiliza 3.510 archivos con 0 bytes de transferencia, metadatos y hash.
  URLs de ambos coordinadores conservadas. No se han lanzado nuevos entrenamientos
  o precálculos: el contrato GIS y contenido son idénticos al circuito completo ya
  validado. Este cambio de rutas tiene pruebas dirigidas y paridad reales.
- Limpieza local aplicada: retirados objetos/recibos/vistas HA antiguos; 3.581
  archivos ordinarios compartidos, 15.622.243.791 bytes lógicos más metadatos.
  Conservados originales del repositorio, datos privados, backups y caché worker.
- HA real: 3.581 archivos colocados en sus rutas definitivas y referencias finales
  verificadas (3.510 mapa / 1.432 GIS). Archivos ordinarios, sin enlaces creados ni
  recibos nativos. `SHA256SUMS` junto a siete manifiestos/configuraciones. Los tres
  directorios originales intactos. No se ha instalado/reiniciado/ejecutado HA real.

[Guía vigente](mushrooms/shared-geography-consolidation-es.md) e
[informe final](reports/shared-geography-portable-2026-09-15.json). Fuentes y hashes
recuperables en `backups/ha-portable-ready-20260915/`. Candidata publicada como HA 0.2.304;
la instalación y prueba RPi4/iPhone las hará el usuario. No repetir cargas de GiB,
adopción antigua ni circuito local por cambios únicamente documentales.
Las imágenes arm64 y paquetes guardados en `ha-map-candidate-20260915` son previos
a esta corrección: no confundirlos con las imágenes locales actuales comprobadas.

El estado anterior queda en
[contexto previo](reports/context-before-portable-close-2026-09-15.md).
Los apartados siguientes conservan el alcance y las validaciones históricas de
la candidata; las rutas/instalación vigentes son las descritas arriba.

## Candidata local aceptada técnicamente — 15/09

**Trabajo autónomo local completado. No publicado en GHCR ni instalado en HA real.**
El usuario hará la instalación; no tocar la RPi4 ni publicar como continuación
implícita. [Informe final](reports/prediction-map-geography-2026-09-15.json).

HA **0.2.304** / worker **1.1.2** reconstruidos y recreados desde fuentes; verificados
194 archivos HA y 103 worker dentro de imágenes y contenedores, sin diferencias.
Smoke final: **1581 tests, 48 omitidos, OK**. Seis consultas reales con usuario básico,
paridad exacta HA local/worker, repetición, concurrencia y cancelación correctas.
La prueba usa el batch operativo nuevo y produce probabilidades. Estos tiempos
son del M1 local, no una medición de rendimiento de la RPi4.

Circuito local mediante worker completado y auditado:
- `worker_job_uS0z1vBVTD7vB6m-`: reconstrucción verificada y promovida.
- `worker_job_JcDC_qjKhmWtnGSa`: entrenamiento base, nueve especies, promovido.
- `worker_job_d0_gpX_RtsLf0K9Q`: 714/714 ajustes; cinco generaciones instaladas
  del batch `operational_20260915T013504Z`.
- `worker_job_0BvFFmJkAIaj`: precálculo recibido y activo, revisión 61,
  artefacto `sha256:6f60d84e9bc6c5fc87b31ffe0e10817278eb00cb025289d533e21585c4480fc5`.
No repetir estos trabajos: no quedan directorios terminales en el worker.

Correcciones detectadas durante aceptación: caché preparada y online ocupado se
tratan por separado para aceptar la cola acotada; notas de auditoría `installation`
no invalidan modelos idénticos. La comparación sigue exigiendo igualdad de
`installed_generation_id`, generaciones y contratos de artefactos. Cambios finales
solo en módulos del mapa, reconstruidos y probados después; el código científico
no cambió respecto al circuito ejecutado (huellas en el informe).

Cartografía con autoridad en `/media/rainmapper/prediction-map`: HA vigila el pequeño
`CURRENT.json`, sin rehashear los GiB. Transferencia fría real al volumen del worker:
3510 archivos, 14.538.214.301 bytes. Reinicio: cero bytes transferidos/rehasheados.
Sin `/maps` compartido en ambos contenedores. Tras promoción, caché privada:
790 archivos reutilizados y solo 31.538 bytes descargados del registro cambiado;
cartografía intacta. Una vista geográfica, dos privadas y ninguna descarga parcial.
Coordinadores, fichas, catálogos, mappings, setales, observaciones y credenciales
preservados. Los cambios de datos son los derivados esperables del circuito local.

Paquete recuperable en `backups/ha-map-candidate-20260915/`: cartografía comprimida
(12.127.781.210 bytes) con hashes, imágenes locales arm64, fuentes, configuración de
ejemplo y backup previo a pruebas. [Guía de importación](mushrooms/prediction-map-ha-media-install-es.md).
No es una release multiarch publicada. Siguientes pasos: aceptación del usuario,
publicación según `release-flow.md`, importación de datos y prueba iPhone en HA real.
GEODE/cobertura ecológica nacional y revisión a fondo de suelo/pH siguen en TODO.

## Cadena operativa en background — 15/09/2026

Autorizado por el usuario después de confirmar que su trabajo había acabado.
Cambio de código: reconstrucción, ML base y ML multiversión (incluido benchmark)
comparten background con el precálculo. El mapa/Predictor interactivo conserva
online. La preferencia por el coordinador de la cadena sigue el carril recibido;
promoción y verificaciones permanecen en HA. Sin migración ni transporte extra.
41 pruebas de cola, 41 de servicio y 343 de API correctas; smoke 1565/48.
HA local y worker existente reconstruidos y recreados, 193/101 archivos iguales
a fuentes en imágenes y contenedores. Coordinadores conservados, canales libres
antes de recrear. Esa aceptación inicial no ejecutó trabajos científicos reales; el circuito completo
local se completó después, como se indica arriba.
[Informe](reports/worker-background-chain-2026-09-15.json).
[Funcionamiento y compatibilidad con HA antiguo](mushrooms/mushroom-worker-multicoordinator-design-es.md#reparto-de-canales--incremento-del-15092026).
La prohibición de instalar HA real sigue vigente. No duplicar la cadena local ya completada.

## Mapa unificado y permiso individual — 15/09/2026 (aplicado y validado localmente)

**Incremento completado:** datos privados conectados al almacén de objetos del worker,
sin montajes privados del Mac. HA reutiliza hashes sellados de modelos/meteorología;
hash inicial de entradas pequeñas: 482.575 bytes. Worker reutilizó 787 archivos y
descargó cuatro (475.540 bytes), más manifiesto de 269.782 bytes, antes del clic.
Imágenes/contenedores verificados: 193 archivos HA y 101 worker; seis consultas reales
con paridad exacta local/worker, repetición y cancelación correctas. Smoke 1561/48,
10 pruebas de caché y 14 de rutas. [Informe](reports/prediction-map-private-cache-2026-09-15.json).
El precálculo que el usuario protegió entonces ya terminó. No publicado HA real.
[Diseño, explicación y límites](mushrooms/prediction-map-private-cache-es.md).
Conservar la posición del interruptor de predicción por petición del usuario.

Decisión del usuario: en HA real el visor habitual incorporará la capa de
predicción. `/protected/maplibre/index.html` y el alias anterior
`/protected/prediction-map/index.html` sirven la misma composición del visor;
se conservan estaciones, meteorología y recursos compartidos.

`can_use_prediction_map` se guarda en la ficha de usuario, junto a Heatmap,
Métricas e IDW. Es explícito para **todos los roles**, incluidos administradores;
si falta, queda desactivado. La UI Usuarios permite activarlo o retirarlo.
La API exige la sesión existente y ese permiso en cada consulta: ningún bypass
por rol. El visor retira los controles cuando se refresca una sesión revocada.

No hay otro login ni otra persistencia: se reutilizan `/auth/*` y los ajustes
por dispositivo. Ejecutor, idioma y zona horaria siguen en esos ajustes;
retirar el permiso no los borra. La preview permanece aislada, sin auth real.

Validación: 13 pruebas de contrato/rutas, 343 de autenticación, navegador con
usuario básico autorizado, admin revocado, URL habitual, meteorología y
persistencia. Smoke completo: 1552 tests, 48 omitidos. Ambas imágenes reconstruidas
y contenedores recreados: 192 archivos HA y 100 worker coinciden con las fuentes.
Consulta real con usuario básico temporal: seis consultas local/worker, tres
especies con cálculo, paridad exacta, repetición/concurrencia/cancelación correctas.
Usuario y dispositivo temporales retirados; registros previos de usuarios iguales.
Coordinadores y volúmenes conservados. No publicado en HA real.
Informe: `docs/reports/prediction-map-user-permissions-2026-09-15.json`.

Prueba manual local: `http://127.0.0.1:8101/users` → usuario → **Prediction access**
→ **Save user**. Abrir/recargar `http://127.0.0.1:8101/protected/maplibre/index.html`
con la sesión habitual. No se ha activado automáticamente para usuarios existentes.

El puerto local sigue enlazado a `127.0.0.1:8101`; no es accesible directamente
desde iPhone. No exponer todo ese servidor a LAN: incluye administración local.
Si se habilita una prueba móvil local, limitarla al visor y API autenticadas.
La caché privada por asociación ya está conectada y probada sin montajes privados
compartidos. Sigue pendiente su despliegue en HA real y la aceptación de release.

## Incremento anterior y prioridades históricas (ver actualización de caché arriba)

**Base local incorporada a imágenes, 15/09:** HA local y el worker existente se
han reconstruido desde el mismo worktree y recreado sin copiar código de aplicación
después. Verificados 192 archivos en HA y 100 en worker contra fuentes, tanto en
imágenes como dentro de contenedores; sin diferencias. Incluye todos los ajustes
anteriores de mapa, idiomas, ayuda, canal online y editor de afinidades. El botón
«Añadir fila» también se inicializa al cambiar de especie por AJAX, no solo al
cargar la página. Los wrappers de arranque incorporan los overlays del mapa cuando
ya existe su configuración; recrear con ellos conserva sus montajes.

**Calendario visible:** Parámetros → Predicción → Zona horaria de la predicción,
con ayuda ES/CA/EN y guardado por dispositivo. Valor inicial `Europe/Madrid`.
La fecha inicial ya usa esa zona, no la del navegador. Cada consulta lleva
`calendar_timezone` validada hasta los lectores de HA/worker y el resultado debe
devolver la misma; visible bajo la fecha. Conserva el ajuste al guardar desde
el mapa meteorológico. Informes abiertos mantienen su zona original.
Corregido el fallo de medianoche: el worker UTC consideraba el 14/09 todavía
«hoy» cuando en Madrid ya era 15/09, rechazaba el corte meteorológico del 14 y
mostraba todas las especies sin cálculo. No cambia modelos ni inventa datos;
se mantiene la protección contra cortes futuros y la abstención por datos/modelos.
[Semántica y configuración](mushrooms/prediction-map-local-worker-setup-es.md#calendario-visible-de-la-predicción--15092026).

Validación final: smoke **1.551 tests, 48 omitidos, OK**; Chrome con 20 consultas
fixture, zona del navegador Honolulu/mapa Kiritimati, persistencia, escritorio/móvil
y ruta meteorológica. API HA local–worker para el 15/09: paridad exacta, repetición,
concurrencia y cancelación; tres especies calculadas en La Vansa/Montclar.
Sagàs (41.98996, 1.90109): aereus y caesarea vuelven a tener siete probabilidades.
Perfiles, datos y backups del usuario preservados; URLs del worker idénticas por
SHA256 antes/después. Se esperó a que finalizaran los trabajos que lanzó el usuario.

Evidencia e identidades finales: [informe de base local](reports/prediction-map-local-images-2026-09-15.json).
Copia recuperable local en `backups/local-base-20260915/`: source completo con
archivos nuevos, hashes, configuración y JSON privados actuales/anteriores.
Los modelos, meteorología y GIS permanecen en sus volúmenes; no se duplicaron GB.
Etiquetas locales conservadas: `rainmapperha:local-base-20260915` y
`rainmapper-worker:local-base-20260915`. **No hay publicación ni actualización de
HA real, ni commit/push del worktree.** Seguimos con dos mapas; el meteorológico
actual y la preview sin autenticación real se conservan.

Siguiente: integrar la caché privada por asociación con el mapa y completar GIS
nacional. Antes de HA real sigue pendiente el circuito local de entrenamiento,
promoción y precálculo aplicable y la aceptación expresa, según `release-flow.md`.
No lanzarlo automáticamente: esta tarea solo autorizó builds/recreaciones locales.
La revisión científica de suelo/pH y la revisión visual a fondo/árboles vecinos
siguen aparcadas en TODO. No reabrirlas por este arreglo.

## Historial de los incrementos incorporados a la base local

Las referencias siguientes a copias puntuales o imágenes pendientes describen
el momento original de cada ajuste: quedan superadas por la reconstrucción del
15/09 documentada arriba.

**Edición de afinidades corregida, 14/09:** el decodificador HTTP omite valores
vacíos; el parser anterior terminaba al primer índice ausente y perdía las filas
posteriores a un ID puesto en «-». Ahora recorre los índices enviados, conserva
metadatos de identidades sin cambiar y mantiene las afinidades ocultas de V0.
Marcador de grupo permite vaciar una lista completa. «Añadir fila» en V0 y
Enriched, con opciones del catálogo, prevención de duplicados y ayuda ES/CA/EN.
Se aplica a hosts, bosques, suelos, litología y rasgos de hábitat.
Seis pruebas dirigidas pasan, incluidas primera/intermedia/última fila vacía,
índices separados, cero, metadatos, datos ocultos y validación de duplicados.
Navegador sobre HA local: añadir dos filas por grupo, seleccionar catálogo,
vaciar la primera sin alterar las restantes, V0/Enriched y anchos 1600/390.
Código y etiquetas copiados a HA local, reiniciado y SHA-256 comparados con
fuentes; no se reconstruyeron imágenes ni se modificó el worker.

Recuperación limitada a `tricholoma_terreum.ecology.host_affinities`: restaurados
`host_pinus_nigra` y `host_pinus_sylvestris` con sus metadatos del backup
`mushroom_profiles.20260914T194237Z.json`. El backup mostrado en la captura
(`194342Z`) ya contenía el borrado. Abeto blanco sigue eliminado; todos los demás
campos y perfiles actuales, incluidos cambios posteriores de suelo, se conservan.
Validación: 0 errores, 104 avisos. Copia previa a la recuperación conservada en
`docker-data/mushroom-data/backups/mushroom_profiles.20260914T195548693692Z.affinity-recovery.keep.json`.
Incorporar estos cambios en la próxima imagen autorizada.


**Hover inmediato por fecha, 14/09:** eliminado `<title>` de puntos de la gráfica
semanal, que dependía de la demora nativa del navegador. Tooltip propio sin espera
al mover el puntero por una columna de fecha; muestra juntas todas las especies
calculadas ese día y sus colores, sin acertar en puntos próximos/solapados.
Posición horizontal acotada a la gráfica, sin capturar clics; salir/Escape oculta.
Foco de teclado en punto muestra el mismo desglose. Sin valores se indica sin
probabilidad calculada, sin inventar cero. No consulta ni recalcula; preserva
selector/clic de fecha. Prueba de navegador final pasa (20 consultas fixture),
incluida aparición síncrona lejos de curvas, las tres especies, borde derecho,
teclado y día sin valores. Captura inspeccionada. JS/CSS copiados a HA local y
huellas servidas por HTTP verificadas. Sin reinicios ni cambios del worker/datos;
incorporar en la próxima imagen autorizada.

**Colores de curvas, 14/09:** corregida asignación que consumía posiciones para
todas las especies del catálogo y dejaba curvas visibles con verdes muy próximos.
Solo consumen color las especies compatibles con alguna probabilidad finita en
temporada durante la semana (0 incluido, null no). Paleta contrastada inicial de
ocho colores sin repetición; extensión por tonos para más series. Identidad
ordenada y conjunto semanal mantienen colores al cambiar fecha/ranking/idioma;
curva y marcador de lista comparten color. Los colores pueden cambiar entre
puntos con conjuntos calculados distintos. Prueba de navegador correcta (19
consultas fixture), incluida regresión de 21 especies con solo tres curvas
próximas: Edulis azul, Pinícola naranja y Rovelló morado. Captura inspeccionada.
JS copiado a HA local y verificado por HTTP; sin reinicios, cambios de cálculo,
worker o datos. Incorporar en próxima imagen autorizada.

**Mapa por canal online/foreground, 14/09:** decisión expresa del usuario:
background puede ejecutar precálculo mientras online atiende el mapa. Corregido
el bloqueo global que impedía sondear consultas si había cualquier trabajo activo.
El mapa conserva su contrato efímero por coordenadas, pero comparte una reserva
global de foreground con los trabajos online existentes; no añade un tercer
cálculo concurrente ni un canal por coordinador. Reserva no bloqueante antes de
reclamar, retenida hasta finalizar y liberada también con errores; background
conserva su carril independiente. Cuando online está ocupado, acción autenticada
`busy` mantiene presencia sin reclamar; broker devuelve `worker_busy`, distinto
de desconectado, con texto ES/CA/EN. El visor usa la capacidad de predicción para
el aviso inicial; ya no inventa modo simulado mientras espera el primer resultado.
23 pruebas dirigidas pasan (incluido servicio con dos coordinadores y concurrencia
de carriles); navegador correcto con aviso de ocupado (18 consultas fixture).
Aplicado en HA local/worker por copia, sin imágenes nuevas. Worker reiniciado solo
con ambos carriles libres y configuraciones de coordinador idénticas por hash.
No se lanzó ni canceló entrenamiento/precálculo real durante este arreglo.
Comprobación final HA local→worker tras el cambio: `worker_ready=true`,
`data_mode=prediction`, 7 especies, cálculo 1277,742 ms; sesión temporal eliminada.

Diagnóstico que originó el cambio: `worker_job_UbGvg0cuhtud` era precálculo de
`primary` (HA real), no de la cola local mostrada. Log confirmó fin/liberación a
19:04:10 UTC (21:04:10 local). La tarjeta «En espera» mira solo foreground y puede
ocultar actividad de background; queda pendiente mejorar el resumen de la tarjeta.
El predictor remoto `worker_predictor_v1` se asigna a foreground cuando se crea
ese trabajo; no significa que toda consulta del predictor vaya al worker, porque
puede servirse del precálculo existente.

**Ayuda de suelo/pH, 14/09:** disponible en Ecología → Suelos, V0 y Enriched,
como desplegable explícito «Ayuda: cómo funcionan el suelo y el pH». Explica los
ocho controles, pH, excepción, afinidades, duplicidad aparente de Silíceo,
Calizo condicionado/bloqueador, ejemplo aereus/ou de reig y guardado. Texto
completo ES/CA/EN, 14 secciones; [guía fácil de consultar](mushrooms/soil-ph-rule-help-es.md).
Dos pruebas dirigidas pasan; navegador en HA local verifica apertura sin cambios
en campos y sin desbordamiento a 1600/390 px. Render de tres idiomas comprobado
en contenedor sin etiquetas ausentes. UI y etiquetas copiadas a HA local y
reiniciado solo ese contenedor; hashes coinciden. Sin editar fichas ni reglas,
sin worker/build/publicación. Incorporar cambios en próxima imagen autorizada.

**Hospedadores ES/CA/EN, 14/09:** corregido el lector forestal y el mapa para
usar `common_names` del catálogo local según el idioma seleccionado. Los 115
hospedadores ya tenían los tres idiomas: no se editó el catálogo. `labels`
transporta tres nombres acotados; `label` conserva compatibilidad anterior.
Sin traducción se muestra el nombre científico; alias ambiguos siguen sin
asignarse. Cambiar idioma no repite consultas y editar nombres conserva la caché
geográfica. Trece pruebas GDAL pasan en directorio temporal del worker y prueba
de navegador ES→EN→CA→ES pasa, incluidos fallback y payload antiguo.
Punto 41.98967, 1.90060 comprobado en lector del worker: Alzina/Holm oak,
Roure martinenc/Downy oak, Arboç/Strawberry tree. Cambios copiados a HA local y
worker, reiniciados tras comprobar worker idle; hashes de archivos y de ambas
configuraciones de coordinador verificados. JavaScript servido por HTTP coincide.
Sin builds/publicación: incorporar estos archivos en la próxima imagen autorizada.

**Inglés para demostración, 14/09:** el usuario pide enseñarlo a su jefe como
ejemplo para posibles predicciones en alquileres de M3. Verificados los 117 textos
del mapa con traducción EN y prueba de navegador ES→EN→ES con resultado abierto:
cabecera, máximo semanal, temporada, sin cálculo y gráfica; fecha conservada y
sin nuevas consultas. Activado `settings.language=en` en el único Safari local
habilitado de `carlos` que usa worker; demás ajustes/dispositivos intactos.
Es la preferencia compartida del visor por dispositivo. Recargar para aplicarla.
El pendiente de nombres forestales detectado entonces queda resuelto en el
incremento anterior. Los nombres de especies siguen los definidos en ficha;
no afirmar que todos los datos descriptivos están traducidos. La activación
inicial de idioma no modificó código ejecutable.

**Editor de reglas suelo/pH, 14/09:** el usuario detectó que la regla de exclusión
por falta de suelo solo estaba en JSON. Ahora Ecología → Suelos, en V0/Enriched,
expone los siete campos de `ecology.soil_filter`: exigencia de contexto, suelos
de apoyo/condicionados/excluidos, suelos que bloquean excepción de pH, modo de
excepción y referencia. Activación explícita; sin regla no se crea al guardar.
Metadatos expone además `map_display_name`, otro campo usado por el mapa que
faltaba en el formulario. Las afinidades antiguas y «Evitar» no se presentan como
vetos. Validación compartida de reglas y catálogo local antes de guardar.
Cuatro pruebas dirigidas pasan, incluidos rechazo de IDs/conflictos/referencia
vacía y conservación de otras fichas/campos; pruebas en copias temporales locales.
Controles comprobados por HTTP/navegador en HA local, escritorio/móvil sin guardar.
Perfiles, catálogo, mappings y observaciones reales mantienen sus hashes previos:
no se ha desactivado `require_soil_context` de aereus ni cambiado ninguna regla.
Dos módulos de UI y etiquetas copiados/reiniciados solo en HA local; imagen
pendiente de reconstruir en la siguiente construcción autorizada. [Detalles](mushrooms/prediction-map-local-worker-setup-es.md#edición-de-las-reglas-de-suelo-y-ph).

**Diagnóstico Merlès solicitado, 14/09:** punto 42.01392, 1.96982, fecha
2026-09-14 consultado con el lector geográfico del worker y sus datos montados.
Aereus pasa hospedadores, altitud, pH y temporada principal, pero queda `unknown`
por `soil_unresolved`: unidad ICGC `Q`, depósitos de fondo de valle/rambla/piedemonte,
sin tendencia edáfica resuelta en el mapping. Ou de reig queda compatible porque
su ficha no exige ese contexto conjunto; asimetría de criterios entre fichas,
no evidencia de ausencia de aereus. No se modifican reglas ni mappings:
suelo/pH sigue aparcado. [Respuesta del lector](reports/prediction-map-merles-soil-unresolved-2026-09-14.json).

**Gráfica semanal en cabecera, 14/09:** añadida al final de la cabecera fija,
después de la fecha. Usa exclusivamente las siete probabilidades recibidas del
ejecutor para las especies visibles. Color por identidad, estable al cambiar
fecha/orden, compartido por curva y marcador de la fila. Cada fila calculada
muestra máximo semanal y primera fecha del pico; `null` interrumpe la curva,
0 permanece válido, sin modelo no tiene curva ni máximo inventado. Respeta
temporadas por día. Pulsar la gráfica cambia fecha sin consultar al worker.
Prueba de navegador escritorio/móvil correcta, incluyendo huecos, cero, ausencia
de modelo, colores, temporadas y cabecera fija. Recursos visuales y traducciones
copiados a HA local; reiniciado solo HA local para cargar etiquetas. HTTP coincide
con fuentes y API vuelve a anunciar `worker_ready: true`. Sin build ni cambio de
datos/modelos/worker/HA real; incorporar cambios en próxima imagen local autorizada.

**Cabecera fija del popup, 14/09:** por petición del usuario, título/cierre,
ubicación, terreno, tiempos y selector de fecha permanecen fuera del scroll.
Solo especies, avisos y desplegables se desplazan en `.pm-result-body`.
En mapas estrechos se ajusta el encuadre si falta altura para cabecera y contenido,
manteniendo el punto y la flecha. Prueba de navegador escritorio/móvil pasa,
incluidos fecha visible al desplazar, cambio de fecha, bordes y visor meteorológico.
Tres recursos visuales actualizados en HA local y verificados contra HTTP:
`prediction-mode.js`, `prediction-mode.css`, `prediction-bootstrap.js`.
Siguen pendientes de incorporar a la imagen en una construcción local posterior;
no se reconstruyó/reinició ni se cambió worker, datos o HA real.

**Ajuste visual posterior, 14/09:** el usuario probó el mapa mediante worker en
HA local y detectó popups demasiado bajos cerca del borde superior. El popup
lateral ahora desplaza su cuerpo dentro del mapa y compensa la flecha hacia el
punto; en escritorio (ancho de mapa ≥900 px) aprovecha la altura disponible sin
el tope de 650 px. Foco del cierre sin desplazar el contenido; ajuste al cambiar
altura/contenido o mover el mapa. Navegador escritorio/móvil y cuatro posiciones
de borde pasan. Solo el JS visual se ha actualizado en el contenedor HA local,
verificado por SHA256 de la respuesta HTTP; la imagen aún contiene el JS anterior.
No hubo build, reinicio ni cambio en worker/HA real o autenticación de preview.
La revisión visual general aplazada sigue en TODO.

**Último incremento: volumen y paridad HA local–worker, 14/09.** El usuario aplaza
revisión visual a fondo/Safari y árboles vecinos (siguen en TODO), y autoriza
preparar datos/configuración y comparar ejecutores. Se usa el worker existente,
no uno adicional. Ambos contenedores reconstruidos, montajes de mapa en solo lectura
y canal de la asociación HA local activados. URLs/credenciales persistidas intactas.
La preview ficticia se conserva. [Instalación, comandos y límites](mushrooms/prediction-map-local-worker-setup-es.md).

Generación pública local: 3.510 archivos / 14.538.214.301 bytes lógicos,
reutilizados por enlaces duros (cero copia adicional); segunda instalación sin
transferencia ni rehash. Contiene dependencias de lectores actuales; **no completa
España**: GEODE y MFE fuera de Catalunya siguen sin integrar. El usuario confirma
alcance nacional, no recortar territorio. Preparar estas integraciones sin repetir
descargas/auditorías. La portabilidad nacional y la aceptación en otra máquina
quedan abiertas; la paridad del cálculo actual sí está probada en Linux ARM64.

La Vansa/Montclar: resultados idénticos, repetición/concurrencia, cancelación,
401/400 y worker desconectado→503 sin fallback correctos. Once archivos compartidos
con hashes idénticos al source en ambos contenedores. [Informe](reports/prediction-map-local-worker-integration-2026-09-14.json).
**RPi4: cálculo mediante worker en principio.** HA local se usa como referencia
de paridad; no extrapolar estos tiempos al Raspberry ni trasladarle configuración
de cálculo local automáticamente. No hubo entrenamiento, precálculo o release.
La prueba comparte datos privados de HA local por montajes de solo lectura.
Antes de HA real falta integrar el mapa con las generaciones privadas de esa
asociación en el worker; nunca sustituirlas por `docker-data` del Mac. Cartografía
pública reutilizable, perfiles/modelos/meteorología separados por coordinador.

**Última precisión del usuario: minimizar transporte durante la predicción.**
Reutilizar meteorología del precálculo y fichas existentes si coinciden con las
versiones aprobadas por HA. El runtime actual ya reutiliza recibos/objetos y
transfiere solo archivos cambiados (cuatro pruebas dirigidas pasan); **el mapa
todavía no está conectado a esa caché**. Su integración debe usar referencias
compactas, evitar manifiestos completos/hashes/TARs por clic y sincronizar solo
lo ausente, con versiones coherentes y permisos por asociación. No confundir
la prueba con montajes locales con una prueba de ese transporte. [Contrato y
aceptación pendiente](mushrooms/prediction-map-local-worker-setup-es.md#sincronización-privada-y-caché-requisito-acordado-integración-pendiente).

**Implementado localmente: `territorial_and_seasonal_windows_v6`.**

1. **Especies posibles en el lugar:** suelo+pH conjuntamente, hospedadores o
   hábitat y altitud. `status` territorial no cambia por mes ni meteorología.
   `daily_statuses` es una proyección idéntica, validada por contrato/navegador.
2. **Lista visible y cálculo en una fecha:** decisión posterior del usuario:
   **fuera de temporada no debe aparecer**. Solo se muestran fases principal o
   secundaria, con esa etiqueta junto a la especie. La clasificación procede de
   los meses originales y de la función compartida con el Predictor en
   `mushroom_phenology.py`; humedad/temperatura siguen en el motor existente.
   `daily_season_phases` está separado del estado territorial. La lista visible
   sí puede cambiar con la fecha; no hay descuentos arbitrarios del porcentaje.

`territorial_candidates` conserva el primer nivel; `prediction_candidates` añade
la temporada entre lector, ejecutor y runtime. Se filtra antes del contexto hídrico
para modelos y de inferir; las fechas fuera de temporada no invocan modelos. Se respeta la
selección de especies solicitada. Sin candidatas no se llama al proceso del
motor; el runtime también retorna antes de abrir modelos/meteorología. Si ninguna
candidata tiene evidencia de modelo, no prepara meteorología del modelo.
El desplegable meteorológico permanece independiente. Compatibles sin modelo o
con abstención permanecen al final con «Sin probabilidad calculada»: `null`, no 0.

**Cuatro fichas locales revisadas:** aereus, edulis, pinophilus y cibarius s.l.
Cambios limitados a `ecology.soil_filter`; pH, hosts, fenología, altitudes y ediciones
restantes preservados por comparación estructural. Silíceo es apoyo no exhaustivo;
caliza+pH admitido produce admisión condicionada, nunca descalcificación confirmada.
Otros tipos conocidos no preferidos pueden entrar condicionados. Sin composición
resuelta, abstención por falta de información; sin nuevo veto litológico.
Solo aereus conserva la excepción de intervalo solapado y el máximo 6,8.
[Reglas completas y procedencia](mushrooms/prediction-map-substrate-species-review-es.md#reglas-locales-conjuntas-v5).
UI con avisos de admisión condicionada y desplegable de descartadas/desconocidas.
Descartadas: nombre en línea propia, cada motivo debajo y filas separadas;
corregida la concatenación visual de nombres/motivos.
Cabecera «Terreno»: tipos de suelo primero, después árboles/hábitats. Etiquetas
del catálogo recibido en `mapped_context.soil_tendencies`, mezclas conservadas;
suelo en color tierra, sin inferir categorías nuevas desde pH ni cambiar filtros.

**Siguiente:** integrar el mapa con la caché privada existente según el requisito
anterior y completar integración nacional (GEODE y MFE fuera de Catalunya)
y su paquete operativo; no reducir el alcance a Catalunya. Revisión visual a fondo
y recuperación forestal vecina aplazadas por el usuario al TODO.
El usuario ha aparcado suelo/pH: conservar reglas; la revisión de otras fichas y
vinosus sigue pendiente, sin reabrirla automáticamente ni cambiar datos en silencio.
La aceptación del cálculo actual en HA local–worker está realizada arriba; no
confundirla con validación científica, cobertura nacional o permiso de release.
No repetir el incremento ni las comprobaciones ya terminadas si no cambia código.

Balance y orden de los pendientes actualizados en
[el seguimiento del mapa](mushrooms/mushroom-prediction-map-progress-es.md#balance-y-próximos-pasos--14092026).

## Contraste posterior solicitado: presentación temporal y suelo condicionado

Diagnóstico del segundo punto del usuario: **42.29077, 1.53842**, distinto del
primer punto de La Vansa. API actual: 1.784 m, pino rojo, unidad `Tk` (margas y
calizas margosas), OpenLandMap 6,4 [5,4–7,3]. V5 admite condicionados edulis y
pinophilus; reproduce 61 % y 28 % redondeados para 14/09. Ambos incluyen septiembre
en sus fichas. No hay evidencia de carbonatos superficiales/descalcificación medida.
**Decisión posterior cerrada del usuario:** conservar las reglas actuales de
suelo/pH. Rechaza exigir tipo de suelo y confirmación por pH porque descartaría
setales conocidos de aereus. No implementar esa restricción ni cambiar admisiones
condicionadas. La revisión puntual también confirmó componente calcáreo en las
unidades de Olvan/Merlès; geología y pH no describen exhaustivamente el suelo del
setal. Esta decisión no revierte el filtro estacional ni sus etiquetas.
[Diagnóstico exacto](reports/prediction-map-vansa-second-diagnosis-2026-09-14.json).

En el primer punto de la captura (42.17076, 1.84548), marçot figura territorialmente
posible y devuelve abstención; su ficha excluye septiembre. Fredolic incluye
septiembre secundario y devuelve falta de modelo. La decisión posterior ya está aplicada: marçot se oculta y no llega al modelo;
fredolic aparece con «Temporada secundaria» y sin modelo. No se cambiaron meses
ni reglas de suelo. 106 pruebas y Chrome; respuesta actual de este mismo punto
verificada en el [informe v6](reports/prediction-map-season-visibility-2026-09-14.json).

**Descalcificación en las capas reales:** OpenLandMap instalado solo aporta pH e
incertidumbre. En atributos ICGC no aparecieron descalcificación/descarbonatación;
Orst/Orst1/mc_Orst mencionan nódulos disueltos en roca/protolito. **GEODE sí contiene
el concepto en unidades cartografiadas**: unidad 247, Z1000, «Fm. Oviedo: calizas,
a veces descalcificadas, y margas», confirmada en servicio oficial y bloque local
`layer-8/0016000.json.gz` (OBJECTID 16027/16028). «A veces» no localiza ni mide el
horizonte superficial en cada punto. GEODE aún no es el lector integrado de estos
puntos catalanes. [Evidencia acotada](reports/prediction-map-gis-decalcification-2026-09-14.json).
No confundir la categoría del catálogo con datos asignados a una coordenada.

Setal adicional comunicado por el usuario: **Montclar, 42.02466, 1.77189**,
aereus presente según su testimonio. No denunciaba exclusión actual: ilustra que
un veto por componente calcáreo perdería un setal conocido. Consulta actual:
763,8 m, pH estimado 6,6 [6,1–7,9], encina/roble pubescente, unidad `POmlg`,
tendencias calcárea/arenosa. Aereus admitida condicionada y temporada principal.
Reglas conservadas, sin excepción por coordenadas ni alta en observaciones.
[Registro del contraste](reports/prediction-map-montclar-aereus-2026-09-14.json).

## Suelo y pH: conclusiones y límites vigentes

- La revisión bibliográfica respalda cruzar suelo y hospedador, no una jerarquía
  universal «suelo manda siempre». Hospedador necesario no se sustituye por suelo.
- Composición de roca y reacción del suelo son dimensiones diferentes. Silíceo
  no equivale automáticamente a ácido; calcáreo no demuestra pH básico superficial.
- El agua infiltrada puede lavar carbonatos: roca caliza con horizonte superficial
  descalcificado/ácido es posible. Un pH **estimado** bajo no confirma ese proceso;
  tampoco las lluvias recientes permiten inferirlo. No convertir todas las calizas
  en terreno favorable ni excluir edulis universalmente por la roca madre.
- Edulis local ya incluye `lith_decalcified_soil` entre sus preferencias. No hay
  medición de descalcificación en La Vansa. Que allí fructifique poco o mucho no
  se deduce de las fuentes revisadas. Presencia comunicada tampoco mide el pH.
- No duplicar evidencia contando «ácido» derivado de pH además del mismo pH.
  Mantener mezclas, procedencia y desconocidos. No rellenar faltantes como neutro.
- El usuario rechaza ampliar globalmente aereus a pH máximo 7,5. Sigue en 6,8.
  No hay decisión aprobada de veto calcáreo universal para las otras especies.

[Fuentes primarias y propuesta](mushrooms/prediction-map-ecological-factors-literature-es.md)
y [matriz de 21 fichas](mushrooms/prediction-map-substrate-species-review-es.md).
Son anexos para profundizar; el alcance y decisiones necesarios están arriba.

## Qué está implementado y qué no

El mapa calcula probabilidades del **motor Python existente en preview local**,
con modelos instalados, evidencia por especie y entradas del punto. No calcula
ML en navegador ni toma prestada la evidencia del área que contiene el punto.
**Predictor por área; mapa por especie**, incluso en Olvan. La diferencia de
porcentajes ya se investigó después del precálculo del usuario; no intentar
igualarlos ni repetir esa investigación. [Informe](reports/prediction-map-olvan-after-precompute-2026-09-13.json).

Rovelló tiene cuatro filas por IDs existentes: deliciosus, sanguifluus, vinosus y
salmonicolor/quieticolor. Esto **reemplaza el grupo derivado**. Solo deliciosus
tiene modelo en las comprobaciones realizadas; no prestar su modelo a las demás.
Nombres en `metadata.map_display_name`, sin fusionar observaciones ni dividir
la ficha conjunta salmonicolor/quieticolor. Probabilidades descendentes del día;
sin cálculo al final. Cálculo disponible no significa validación científica:
`scientifically_validated=false`, `point_validation=not_established`.

**Reglas de suelo v5 conservadas en el filtro v6:** `ecology.soil_filter` de las cuatro fichas define apoyo
silíceo, lista de exclusiones vacía, caliza condicionada y requisito de composición
resuelta. Son reglas provisionales, no límites biológicos absolutos. El máximo de
aereus no se amplía: solo su ensayo previo permite una media fuera de rango con
intervalo OpenLandMap solapado y silíceo, sin componente carbonatado/yesífero que
bloquee esa excepción. Edulis/pinophilus/cibarius comparan estrictamente la media.
Las otras 17 fichas conservan sus políticas de suelo; ninguna usa meses para la
selección territorial. Preferencias y valores de afinidad no activan nuevos vetos.

Revisión ICGC aplicada: 1.055 códigos revisados, 1.046 con materiales en 192 reglas
compartidas; 14 materiales añadidos al catálogo. Nueve sin equivalencia segura:
CK, Dlva, Fd, Glpm, Org, Pze, bf, ff, mr_EÇOr. Identificar un depósito no resuelve
su composición: 392 unidades indeterminadas para silíceo/calizo/yesífero. Mezclas
sin proporciones inventadas; cuatro códigos de cubierta y cinco filas MVC
previas preservados. **GEODE siguiente fase**, no revisar/descargar otra vez ICGC.
[Revisión y hashes](reports/prediction-map-icgc-substrates-2026-09-14.json).

Catálogo y mappings locales conservan los SHA256 `applied_files_sha256` del
informe ICGC, revalidados. El hash de perfiles cambió después de v5 por edición
desde la UI a las 02:42:58 del 14/09: salmonicolor/quieticolor conserva solo
`host_abies_spp`, con metadatos actualizados. Edición preservada; comparación
estructural con backup `mushroom_profiles.20260914T004258Z.json`, que coincide
con el hash v5. No restaurar cinco afinidades anteriores. El [informe v5](reports/prediction-map-two-levels-2026-09-14.json),
con reglas antes/después y prueba de preservación de los demás campos.
Backups con sufijo `20260913T224213651843Z.icgc-substrates.keep.json` y revisión
`docker-data/mushroom-data/gis-mapping-reviews/icgc-substrates-2026-09-14.json`
conservados. No repetir la auditoría ICGC ni las descargas.

## Casos útiles para pruebas dirigidas

Los valores de la tabla son contexto histórico, no mediciones. En este incremento
se reconsultaron nueve puntos con los lectores reales para enero y septiembre:
listas territoriales idénticas, sin inferir modelos en esa comprobación geográfica.
Vallcebre mantiene latitabundus; La Selva/L’Aleixar, aereus condicionada; La Vansa,
las tres fichas condicionadas; Fogars conserva edulis; Ggd sin hosts se abstiene.
Olvan/Merlès conservan aereus y caesarea. Resultados actuales en el informe v5.

| Punto | Evidencia y resultado que interesa |
|---|---|
| Vallcebre 42.22549, 1.81417 | Latitabundus: pino rojo, 1.050 m, pH 6,9; excluida el 13/09 solo por mes (principal 10–12, secundario 1). Debe seguir posible territorialmente tras separar niveles. |
| La Selva 41.22694, 1.09095 | Pizarras `mc_Capg`, silíceo, pH 7,2 [6,7–7,8], encina/roble, 415,4 m. Aereus admitida por ensayo v4; presencia abundante comunicada. |
| La Selva 41.23675, 1.13555 | Misma unidad silícea, pH 7,5 [6,6–8,1], encina/quejigo, 357,9 m; aereus admitida con aviso. No ampliar máximo global. |
| L’Aleixar 41.22071, 1.07009 | `Ggd`, granito+granodiorita → silíceo; pH 6,9 [6,0–7,7], hosts identificados. Aereus compatible por ensayo. |
| 41.22012, 1.06989 | `Ggd` ya mapeado, pero polígono MFE «No arbolado», códigos cero. Vecino con pino/encina/quejigo a 52,09 m. Sigue absteniendo por terreno; no fallo geométrico. |
| La Vansa 42.27588, 1.52460 | `PPcm`, lutitas+caliza, pino rojo, 1.663,7 m, media 6,3 [5,2–7,3], SoilGrids superficial 6,1. Edulis, pinophilus y cibarius: admisión condicionada desde v5. Caliza cartografiada no confirma carbonatos superficiales/descalcificación. |
| Fogars 41.77528, 2.46480 | Haya recuperada tras arreglo geométrico MFE, edulis compatible. Regresión para no volver a perder árboles. |
| Olvan 42.06282, 1.93765 y Merlès 42.01347, 1.97098 | Setales de aereus/caesarea comunicados. Mantener selección por especie y OpenLandMap; no ajustar modelos para igualar el Predictor de áreas. |

Informes específicos en `docs/reports/prediction-map-{vallcebre-latitabundus,
ggd-missing-hosts,ggd-mapping,vansa-calcareous,...}-2026-09-*.json`.
La reparación MFE acotada en memoria recuperó árboles en Fogars y Arbúcies;
fuentes/índices intactos. **Árboles vecinos aún no implementado**: usuario lo ha
solicitado; concretar criterio/radio antes de trasladar información y mostrar
procedencia/distancia. No confundirlo con vecino de pH, que sí existe hasta 1 km.

## Datos, archivos y ejecución

- Autoridad: `docker-data/mushroom-data/mushroom_profiles.json`,
  `mushroom_reference_catalogs.json`, `mushroom_gis_mappings.json`. Son los datos
  de trabajo, **no las semillas** `mushroom-data/`. 21 fichas/21 rangos de pH,
  115 hosts. Preservar ediciones del usuario: edulis mínimo **900 m**,
  pinophilus **1.100 m**, no restaurar 600 m.
- UI única **Terreno**. Ectomicorrícicas exigen hospedador específico compatible;
  jerarquía de género admite descendientes, no equivalencia entre hermanos.
  No ectomicorrícicas pueden entrar por hábitat revisado (prado, ribera, bosque).
  Falta de árboles/hábitat significa desconocido, nunca ausencia física demostrada.
- OpenLandMap media 0–30 cm para filtro, límites Q16–Q84 informativos; nueve TIFF
  (368 MiB) en `mushroom-map-GIS/openlandmap-ph/spain-v20250204/manifest.json`.
  Profundidad solo en desplegable Terreno; SoilGrids conservado para comparación
  y retención hídrica. Sin media, vecino hasta 1 km y distancia; sin vecino,
  desconocido. No fallback silencioso a SoilGrids ni nuevas descargas.
- Preview recargada con los mismos argumentos y puerto; API v6 comprobada:
  `http://127.0.0.1:65517/protected/prediction-map/index.html`.
  No asumir que sobreviva ni reutilizar PID antiguo. Sesión ficticia, sin autenticación real.
  Entrada: `tests/prediction_map_browser_check.mjs --preview`, lectores en
  `tests/prediction_map_preview_reader.mjs`. Configuración de esta ejecución en
  `/private/tmp/rainmapper-map-point-executor-config.json` (temporal, no autoridad).
- GDAL usa `/opt/homebrew/bin/python3`; motor/meteorología `.venv/bin/python`
  **sin resolver el symlink**. Datos observados `docker-data/Data`,
  `docker-data/stations.txt`, `PublicData`. Modelos en
  `docker-media/rainmapper/mushroom-derived/ml_models`; registro local
  `docker-data/mushroom-data/mushroom_ml_version_registry.json`.
- GIS: `mushroom-map-GIS/terrain-index/point-inputs-2026-09-12.sqlite`, índice MFE
  `mushroom-map-GIS/mfe25/prepared/catalunya-point-index-v2-2026-09-13.sqlite`,
  geología ICGC `mushroom-map-GIS/icgc-geologia-50000/source/geologia-territorial-50000-geologic-v3r0-202412.gpkg`,
  cubiertas `mushroom-map-GIS/icgc-cobertes-2024/source/cobertes-sol-v1r0-2024.gpkg`,
  municipios `mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg`,
  SoilGrids `mushroom-map-GIS/soilgrids-shared`, DEM nacional
  `mushroom-map-GIS/ign-mdt25`, regional `mushroom-GIS`. Ya preparados; no reconstruir.
- Código del incremento: `rainmapper_core/mushroom_map_ecology.py`,
  `mushroom_map_model_runtime.py`, `mushroom_prediction_map.py`,
  `viewers/prediction-map/` y textos ES/CA/EN en `mushroom-data/mushroom_labels.json`.
  Ejecutores: `mushroom_map_execution.py`, `mushroom_map_prediction.py`;
  script de modelo `scripts/prediction-map-local-model.py`.
- Pruebas: `tests/test_mushroom_map_ecology.py`,
  `test_mushroom_map_model_runtime.py`, `test_mushroom_prediction_map.py`,
  `test_mushroom_map_prediction.py`; datos locales opt-in en
  `test_mushroom_map_local_mappings.py`. Cubren invariancia por fecha, fenología
  preservada, cero llamadas para incompatibles y orden filtro→entradas del modelo.

## Validación, riesgos y siguientes fases

Último ajuste de UI: prueba Chrome escritorio/móvil correcta con suelo antes de
árboles, motivos de descarte en líneas propias y sin desbordamiento horizontal.
Comando: `node tests/prediction_map_browser_check.mjs /private/tmp/rainmapper-maplibre-4.7.1.js /private/tmp/rainmapper-maplibre-4.7.1.css`.
Capturas de esa ejecución: directorio temporal `prediction-map-browser-gI2mPH`,
incluida `exclusions-mobile.png`, inspeccionada visualmente. La preview sirvió JS/CSS
idénticos a los archivos actuales, sin reinicio ni cambios de filtros.
Este cierre documental no repite pruebas ejecutables: revisión y `git diff --check`.
Las pruebas siguientes son evidencia de sus respectivos incrementos, no una nueva
ejecución ni aceptación de Safari/iPhone, HA–worker o precisión científica.

V6 actual: **106 pruebas correctas**, incluyendo regresión del Predictor, datos
locales, salida temprana estacional y semana que cruza el mes sin inferir en días
fuera de temporada. Chrome: ocultación diaria, etiquetas principal/secundaria,
cero/null, móvil y ruta meteorológica correctos. Preview recargada en 65517 con
los mismos argumentos; API Cercs verifica marçot fuera/sin modelo invocado,
fredolic secundario sin modelo y edulis principal. Perfiles, catálogo y mappings
mantienen hashes v5. [Informe](reports/prediction-map-season-visibility-2026-09-14.json).

Validación histórica del código v5: **67 pruebas dirigidas correctas**, incluidas nueve
contra JSON locales; otras **369 pruebas de regresión, 12 omitidas**, resultado OK.
Chrome escritorio/móvil: fecha, orden, cero/null, motivos, ruta meteorológica y
permisos simulados correctos. Nueve puntos × dos fechas mediante lectores GIS
actuales. API real de preview en La Vansa: edulis/pinophilus calculadas y cibarius
con abstención/null. Ninguna de estas comprobaciones acredita precisión científica.
Comandos, resultados, tamaños de payload y huellas del código en
[el informe v5](reports/prediction-map-two-levels-2026-09-14.json).

La integración está ahora en preview y HA local/worker existente, con el alcance
de la aceptación registrado arriba. HA real no ha recibido este bloque. Pendientes:
completar GIS nacional, destino físico independiente/AMD64, medición IO físico y
rendimiento representativo, revisión visual/Safari aplazada y superficie coloreada.
Mantenedores legacy de mappings agrupados y 37 cubiertas pendientes. Vinosus
mantiene contradicciones documentadas; no corregirlo silenciosamente.

No runners, entrenamiento, precálculo, publicación HA real, Tailscale,
autenticación real de preview, cambios de coordinador ni borrado de datos/backups.
Preservar URLs antes/después de cualquier operación futura autorizada del worker.
Los builds/recreaciones locales de este incremento sí fueron autorizados.
No repetir descargas, auditorías o migraciones terminadas. RPi4 compartida:
límites acotados, sin fuerza bruta ni artefactos grandes por punto/día/modelo.
Continuar informando brevemente al menos cada minuto. Antes de implementar,
resumir al usuario lo entendido y el incremento concreto; no pedir confirmaciones
rutinarias sobre trabajo ya autorizado.

Worktree ampliamente modificado, con archivos nuevos sin seguimiento y cambios
previos en `mushroom-data/mushroom_observations.json`. No atribuir todo el diff a
esta sesión ni incluirlo ciegamente en commit. Cierre sin commit/push ni despliegue.
Incidencia Barcelona corregida anteriormente en catálogos local/HA real, Erinya
pendiente de la fuente; reglas de coordenadas documentadas, sin runner nuevo.
[Registro](reports/weather-coordinate-conflict-2026-09-13.json).
