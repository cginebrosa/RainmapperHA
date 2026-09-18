# Archivo histórico — contexto previo a la auditoría documental del 18/09/2026

Este snapshot conserva decisiones y evidencias; contiene estados de distintas fechas
que no deben usarse como estado actual. Consultar [contexto vigente](../active-context.md).

# Contexto activo — 18/09/2026, HA 0.2.312 publicada; media real migrado

**Restricción expresa del usuario: no acceder por SSH a la RPi4 sin petición
explícita, tampoco para consultas. El 18/09 autorizó SSH para la migración de
media, su verificación y la retirada de duplicados GIS comprobados. Esta excepción
no autoriza otras operaciones. Parar, instalar y arrancar Rainmapper en HA real
sigue a cargo del usuario.**

## Release 0.2.312 — buscador en iPhone, ayuda y créditos

El usuario comunica zoom de página persistente al enfocar el buscador en iPhone.
El campo heredaba 13 px; se fija a 16 px, igual que la corrección de acceso de
0.2.305 (`c188f3f`). No se cambia el viewport ni se desactiva el zoom manual.
La ayuda del propio mapa incluye ahora búsqueda por lupa, resultados, marcador,
sustitución al iniciar otra búsqueda y servicio online Photon, en ES/CA/EN.

**0.2.312 publicada, autorizada por el usuario («publicamos») y verificada en GHCR.**
Los tags `0.2.312` y `latest` comparten
`sha256:a3fb966651370713d2c620c49c1b97d98bed6c859859488909db22f11cd754f5`,
con manifests `linux/amd64` y `linux/arm64`. Script terminado con código 0;
las dos fases de subida de capas registraron 41,9 s y 3,3 s.
HA local y worker reconstruidos/recreados desde la candidata; 202/108 archivos
comprobados sin diferencias y destinos del worker conservados. Smoke correcto:
1.639 tests, 48 omitidos. El bump posterior solo cambia versión/cache-busters.
Sin entrenamiento ni precálculo. [Informe de release](../reports/ha-release-0.2.312.json).

Chrome móvil (360×780): fuente efectiva 16 px, sin exceso de ancho, búsqueda real
Saldes y POI correctos; ayuda y créditos en ES/CA/EN, cero excepciones JS.
Evidencia en `tmp/iphone-place-search-20260918/credits-browser.log`.
La emulación no acredita el teclado/zoom de Safari físico. **Validación final
confirmada por el usuario el 18/09/2026 tras publicar 0.2.312:** «ya funciona bien
en el iphone y en safari del mac». Se cierra la incidencia de zoom del buscador
y su comprobación pendiente en Safari. Fuente: confirmación del usuario en esta
sesión; no es una inspección remota de la versión instalada.
La instalación y el arranque en HA real siguen exclusivamente a su cargo.

Créditos: Photon (komoot), datos OSM, OpenTopoMap y OpenFreeMap/OpenMapTiles,
ya usados por los fondos. Referencias: https://github.com/komoot/photon y
https://openfreemap.org/quick_start/. Panel con altura limitada y desplazamiento
vertical; comprobados enlaces, traducciones y límites del viewport móvil.


## Estado verificado y siguiente paso — 18/09/2026

**Publicación histórica de HA 0.2.311 verificada en GHCR**: en aquella publicación
`0.2.311` y `latest` compartían
`sha256:37d6745665923919079f8b51b98a6565ae378a2d76c0e72be266adf604702b79`,
con manifests `linux/amd64` y `linux/arm64`. Script terminado con código 0;
capas subidas en 38,6 s. [Informe](../reports/ha-release-0.2.311.json).
Incluye buscador con POI en el visor compartido y logs de errores de predicción.
Usuario aceptó explícitamente la validación local antes de publicar. HA local y
worker reconstruidos; 202/108 archivos comprobados, dos puntos con resultados
idénticos entre ejecutores y smoke de 1.639 tests (48 omitidos). El bump posterior
solo cambia versión/cache-busters. No se relanzaron entrenamientos ni precálculos.
La herramienta de investigación WU se versiona como herramienta local, sin sus
datos ni revisiones y sin incluirla en la imagen HA. Última versión comprobada
directamente en HA real: 0.2.310; posteriormente el usuario comunica el uso de
0.2.311 en su iPhone y reporta el problema de zoom del buscador.

La release anterior [0.2.310](../reports/ha-release-0.2.310.json) se publicó en
`6624660`; su push había tardado 1.580,2 s. No atribuir aquella lentitud
exclusivamente a Docker ni a Orange: causa de red exacta no determinada.

El usuario confirmó **0.2.310 instalada y Rainmapper detenido**; estado revalidado
con HA CLI. Autorizó SSH para verificar hashes en la Raspberry. **HA real migrado:
seis movimientos y 1.550 archivos conservados; 4.942 duplicados GIS retirados
tras verificar íntegramente origen y copia canónica** (21.358.531.147 bytes lógicos).
Cuatro metadatos adicionales conservados en `geography/imports/retired-legacy-metadata`.
Diez archivos privados mantienen su SHA, identidad del runtime conservada,
ninguna fuente publicada ausente y SQLite activo `quick_check=ok`.
Tras retirar originales, geografía/meteorología/modelos siguen preparados usando
la imagen instalada 0.2.310. Se indicó al usuario que puede arrancar Rainmapper;
Codex no lo paró ni arrancó. **El usuario confirma después que el mapa de
HA real funciona con ejecutor local y worker.**
[Informe](../reports/ha-media-migration-2026-09-18.json) y
[organización](../mushrooms/ha-media-organization-proposal-es.md).
HA local tenía ocho movimientos y 1.547 archivos conservados. Instalar una imagen
no mueve ni borra carpetas. La revisión científica GIS sigue aplazada.

El usuario cerró/reabrió Docker durante la subida. Después autorizó arrancar
worker y HA local: ambos arrancados el 18/09, worker healthy, HA local HTTP 200;
los dos archivos de coordinadores conservan exactamente sus SHA anteriores.
No se cambió ningún destino del único worker.

### Buscador de lugares en mapa de predicciones — 18/09

Incorporado al visor compartido MapLibre: lupa después de ajustes y antes de
3D; panel blanco en español/catalán/inglés. Consulta Photon directamente desde
el navegador, por Enter/Buscar, sin claves ni dependencia del servidor de
investigación del Mac. Preferencia suave por la zona visible, hasta ocho
resultados y caché limitada a 50 consultas durante la sesión de la página.
Seleccionar un lugar centra el mapa en un segundo y crea un POI con nombre;
iniciar otra búsqueda lo elimina, también si no hay resultados. Navegación
separada del cálculo: no consulta predicciones ni cambia filtros o revisiones.

Pruebas dirigidas: traducciones (2 tests) y circuito Chrome del visor compartido,
incluyendo lupa/orden, resultados, coordenadas, texto escapado, POI, limpieza,
panel móvil y ausencia de consultas de predicción por navegación. Evidencia de
trabajo en `tmp/prediction-place-search-20260918/`. HA local reconstruido y
recreado; los SHA256 de app.js/index.html/style.css/translations.json dentro
del contenedor coinciden con los probados. Búsqueda real «Saldes» desde el
visor servido en `127.0.0.1:8101/protected/prediction-map/index.html` verificada
en Chrome con POI, sin errores JS ni consultas de predicción. Esa prueba de
navegación no autentica ni comprueba datos privados; el circuito de predicción
se validó con el fixture aislado y después mediante el coordinador local y el
worker reales: dos puntos, cuatro consultas, resultados científicos coincidentes.
HA local y worker reconstruidos/recreados; paridad de 202/108 archivos sin diferencias.
Suite completa: 1.639 tests, 48 omitidos, correcta. Usuario acepta expresamente
publicar 0.2.311 al terminar la migración; publicada y verificada. El bump posterior
solo cambia versión/cache-busters; no se repite el smoke por esos metadatos.

### Incidencia del ejecutor local de HA real

El 18/09 el usuario autorizó **solo el diagnóstico por SSH de lectura** para
esta incidencia; esa excepción no autoriza futuros accesos ni cambios. HA real
revalidado en `0.2.309`. El worker vuelve a responder según el usuario, pero
«Servidor local» sigue mostrando ejecutor no disponible. En ese mapa local
significa HA real, no el Mac.

Comprobación independiente dentro del contenedor real, sin iniciar un broker,
predicciones, trabajos ni escrituras: todas las rutas de la configuración
`/media/rainmapper/geography/map-config.json` existen; geografía preparada en
2,416 s, meteorología en 0,440 s y modelos en 4,227 s. Evidencia:
`tmp/ha-local-executor-20260918/readiness.json` y script de diagnóstico junto a ella.
En código, `QueryBroker._local_loop` comprueba `ready()` una sola vez y silencia
la excepción; `ResidentReader` descarta stderr. Un fallo transitorio inicial
puede dejar el ejecutor indisponible, pero **la causa histórica concreta no se
ha recuperado**. El usuario confirma que reiniciar Rainmapper recuperó el ejecutor local.
Solicita registrar los errores. Cambio posterior a la release **implementado
en HA local y worker reconstruidos, publicado en 0.2.311**: stderr de los lectores llega al log
de HA/worker; inicialización, lectura de protocolo y consultas registran el
componente y traceback. Se conserva el contrato JSON y el comportamiento de
ejecución/fallback. Cinco pruebas nuevas, suite dirigida de 161 casos con 48
omitidos, sin fallos (`tmp/ha-local-executor-20260918/logging-tests.log`).
HA local y worker ya ejecutan este cambio; HA real conserva 0.2.310.
Reintento controlado solo propuesto. **Ninguno incluido en 0.2.310**.

### Exploración de cobertura Catalunya / Wunderground

Usuario acepta usar base **local del 17/09 a las 11:31**, sin afirmar paridad
con HA real. Primera exploración terminada: 735 estaciones con algún dato de
lluvia en siete días en Catalunya, cuatro fuentes, ceros incluidos y exclusiones
respetadas. Malla territorial de 2 km: 8.031 puntos, 175 a más de 10 km de la
estación disponible más cercana. Estaciones vecinas incluidas en distancias.

20 consultas WU near, 200 entradas, 178 IDs únicos: 143 nuevas dentro de Catalunya,
8 conocidas, 1 excluida y 26 fuera de Catalunya. Nuevas: 75 QC=1, 65 QC desconocido,
3 QC fallido. Lista inicial de 12 para revisar: reduciría hipotéticamente los
175 puntos a 110; no demuestra calidad ni mejora del IDW. **Ninguna incorporada ni backfill operativo lanzado.** Hay candidatas de QC desconocido interesantes
que no deben descartarse solo por ese campo.

[Informe local](../../tmp/station-coverage-catalunya-20260918/README.md),
[mapa MapLibre](../../tmp/station-coverage-catalunya-20260918/viewer/index.html),
[CSV completo](../../tmp/station-coverage-catalunya-20260918/candidates.csv).
Respuestas originales, scripts y resultados conservados junto al informe;
mapa probado en Chrome: 12 prioritarias, filtro de 143 nuevas y estaciones visibles.
Tras un bloqueo 403 de OSM mostrado por el usuario, el visor usa los mismos
cuatro fondos de predicciones/GBIF, con Satélite+ por defecto y conservación
de filtros/capas al cambiar. Las consultas WU y el análisis no se repitieron.
Siguiente fase propuesta: revisión de calidad y continuidad de un lote pequeño;
aprobar individualmente antes de preparar un backfill. No volver a consultar
la API para analizar estos mismos resultados ya descargados.

El usuario autoriza convertir el mapa en herramienta de investigación local:
implementación en `scripts/station_research.py`, interfaz en
`scripts/station-research/`, lanzador `scripts/station-research.command`.
[Uso y límites](../station-research-es.md). Guarda revisiones/candidatas/preliminares
con SQLite fuera de Git, en el mismo directorio de investigación. Controles
3D/norte, filtro de cuatro estados, disponibilidad X/30, búsqueda WU por clic
con modal de progreso, promoción a candidata y eliminación solo de preliminares.
No incorpora estaciones operativas. Consultas nuevas autorizadas expresamente
para esta herramienta; no se ha lanzado backfill operativo. IOLIOL3 verificada
online: 30/30 días (19/08–17/09), altitud publicada 425,8 m. La base de estaciones
actuales sigue siendo el snapshot local; no se afirma paridad con HA real.
Se retira el filtro ambiguo «Nuevas para la red»: en la descarga inicial
seleccionaba las nuevas de Catalunya, pero las nuevas búsquedas no aplicaban
ese límite. Quedan «Prioritarias iniciales» y «Todas las candidatas», sin
distinción geográfica implícita y con filtro de revisión independiente.
Cabecera reorganizada: selección/revisión y acciones en primera fila;
controles de visibilidad/fuentes y recuento en segunda. Selector de fondo
tras un botón de capas a la izquierda, inmediatamente antes del botón 3D.
Al abrirlo muestra directamente las cuatro opciones con el fondo activo
marcado, sin un segundo desplegable.
Buscador de municipios/topónimos en la cabecera: Enter/Buscar consulta Photon,
lista blanca de hasta ocho resultados y selección para centrar el mapa con
un POI rotulado. El POI se retira al iniciar la siguiente búsqueda, incluso
si no hay resultados; no dispara investigación al pulsarlo. Global,
con preferencia suave por la zona visible; caché SQLite persistente y una
petición/segundo, sin autocompletado ni clave WU. No modifica estaciones,
filtros o revisiones ni activa consultas WU al elegir lugar. Verificado con
Molló y Pedraforca; trece tests dirigidos y Chrome: centrado en Molló incluso
con investigación activa, sin llamadas WU ni cambios de datos. Captura
`tmp/station-coverage-catalunya-20260918/place-search-verified.png`.
Servidor del visor recargado; cambio solo local, sin publicar ni tocar HA/worker.
Título general «Cobertura meteorológica», sin limitar la investigación a
Catalunya; la búsqueda admite coordenadas de cualquier lugar. La red de
referencia y los huecos conservan el ámbito del análisis inicial.
«Fuentes actuales» permite cualquier combinación de Meteocat, AEMET,
Meteoclimatic y Wunderground mediante casillas independientes en un desplegable,
con recuento de actuales según selección. Marcadores actuales ampliados de
4 a 7 px de radio, borde blanco de 2 px. Es un filtro visual: conserva la
capa de huecos calculada con todas las fuentes.
El visor omite por ID las estaciones WU ya incorporadas en la base local,
tanto en nuevas búsquedas como en candidatas iniciales. Conserva en disco y
exportación sus registros/revisiones; las estaciones distintas con coordenadas
iguales no se fusionan.
Validación del visor: once tests dirigidos y Chrome con servidor de pruebas
aislado (persistencia tras recarga, estados, 3D/norte, búsqueda, promoción,
modal, limpieza de preliminares/puntos consultados y cambio de fondo). Evidencia visual en
`tmp/station-coverage-catalunya-20260918/research-verified.png`. Búsqueda real
por coordenadas comprobada; consultas y revisiones personales fuera de Git.
La herramienta de investigación sigue siendo local; no modifica HA real.
La migración de media es una operación distinta, terminada y documentada arriba.

La revisión general GIS y la revisión/importación de GBIF siguen aplazadas.

Consulta paralela sobre avisos al editar fichas: confirmado en código que el
aviso de mantenimiento de especies usa `pending_model_species_ids`, marcado
por cambios de observaciones; `save_profile_form` no marca pendientes. El mapa
incorpora las fichas privadas actuales en `MapPublication`, independientemente
del snapshot de modelos y meteorología. La comprobación rápida ML tampoco
incluye una revisión de fichas en `REVISION_VECTOR_KEYS`. No se ha cambiado
esta lógica ni se ha demostrado que editar un filtro de mapa requiera entrenar.
La discrepancia local en `published-runtime.json` afecta a la ficha publicada,
no demuestra por sí sola que el modelo entrenado de HA real esté desactualizado.

La release 0.2.309 incluyó los cambios de IFF descritos debajo, aviso de suelo no
determinado, mensaje comprensible para la referencia obligatoria de suelo/pH y
listado de descartes completo: temporada, pH, altitud, hospedadores, suelo y
datos insuficientes. La lista se recalcula para la fecha seleccionada y conserva
motivos simultáneos. Caso diagnosticado en Vallcebre (42.22524, 1.81535):
llanega negra compatible territorialmente pero fuera de temporada en septiembre;
marçot fuera de temporada y pH 6,9 superior al máximo configurado 6,8.
No se alteran las fichas ni se fuerza exigir suelo a especies que no lo requieren.
Smoke definitivo: 1.615 tests, 48 omitidos; Chrome correcto; 200/107 archivos
efectivos en HA local/worker coincidentes. Ambos reconstruidos y recreados desde
la candidata, worker privado 1.1.3 con destinos intactos. Evidencia
`tmp/release-0.2.309/`. Datos GBIF/fotos/revisiones y observaciones del usuario
no se incluyen en la release; el código del visor GBIF sí queda versionado.

## Tooltip del mapa — incluido en 0.2.309 (17/09/2026)

Corregido en `rainmapper_core/viewers/prediction-map/prediction-mode.css` el
layout del tooltip semanal: el nombre y su IFF/banda van en dos líneas, con ancho
intrínseco limitado al gráfico. Antes, la columna automática del IFF podía
comprimir «Aereus» hasta una letra por línea. Reproducción con CSS anterior y
comprobación del nuevo en Chrome, CA/ES/EN y anchos 430/292/252 px: nueve casos
correctos, sin desbordamiento. Evidencias `tmp/prediction-tooltip-20260917/`.
Instalado después en HA local el 17/09, junto con el cambio de aplicabilidad.
Incluido en la release 0.2.309 validada posteriormente con ambos contenedores.
HA real ejecuta 0.2.309; Chrome no acredita Safari físico.

## Estado operativo y grado de comprobación

### IFF por punto — incluido en 0.2.309 (17/09/2026)

Por petición del usuario, auditados dos puntos cercanos de Aereus: bloqueo al
pasar de 6/160 a 8/160 columnas fuera de rango. La política publicada
`magnitude_v2` elimina el veto por porcentaje y conserva el veto por magnitud
≥3 desviaciones en una entrada ya fuera del rango; lluvia sigue solo como aviso
y las salidas de variables constantes se bloquean. El mapa explica ausencia de
modelo, rechazo por dominio y extrapolación con aviso y detalles desplegables.
Puede cambiar la familia elegida: en estos puntos Aereus pasa a V6/90 días e
IFF 21/19. No se ha demostrado mejora predictiva ni calibrado el umbral.
121 tests dirigidos y navegador Chrome. **Instalado en HA local y worker el
17/09 por petición del usuario**, reconstruidos desde el mismo worktree: 200/107
archivos coincidentes, destinos persistidos del worker intactos. Dos puntos
consultados por API en ambos modos dan igualdad completa salvo tiempos/ID.
Aereus: 0,205671 y 0,191804, ambos con aviso. Observaciones, setales y registro
ML conservan SHA. Evidencia `tmp/iff-local-install-20260917/`. HA real no se ha
actualizado automáticamente; cambios publicados en 0.2.309. No entrenar
ni precalcular por rutina.
[Decisión, cifras y límites](../reports/iff-applicability-2026-09-17.md).

### Suelo no determinado y control por especie

Investigación puntual autorizada de Tordera (41.72905, 2.74775) y Soriguera
(42.37001, 1.06978): HA local devuelve Qt1 y Qve con geología disponible,
pero `mapped_soil_tendency_ids=[]`. Contraste espacial del ICGC y consulta
IGME: entorno granítico próximo en Tordera; varias unidades de composición
distinta junto al depósito de Soriguera. No basta para asignar composición al
depósito ni reclasificar globalmente esos códigos. Por autorización posterior,
implementada la regla general «Suelo no determinado» en cabecera y Terreno si
faltan tendencias, en ES/CA/EN; los suelos conocidos mantienen sus etiquetas.
El despliegue local inicial se verificó por HTTP y conservó las huellas de datos.
Después quedó incluido en la candidata definitiva 0.2.309: HA local y worker
reconstruidos/recreados y verificados juntos, como acredita el informe de release.
Comprobación completa del visor en Chrome aislado correcta, incluidas las
etiquetas en los tres idiomas y el caso con suelo conocido.
Sin cambios de mapping ni de HA real, y revisión GIS general aplazada. Evidencias
`tmp/tordera-soil-20260917/`, `tmp/two-soils-20260917/` y
[investigación de los dos puntos](../reports/two-soils-2026-09-17.md).

Consulta posterior del usuario: en 42.35521, 1.07764 (Soriguera, Qll),
`soil_tendencies=[]` y Ou de reig se admite como `compatible/standard` por
`hosts_match`, `altitude_match`, `ph_match`. La ficha efectiva de
`amanita_caesarea` no contiene `soil_filter`: pH permitido 3,5–7,5 y altitud
0–1000 m; el punto tiene roble pubescente, pH 6,8 y altitud 664,9 m.
La ausencia de suelo no bloquea esa ficha. El usuario rechazó exigir suelo
identificado globalmente: considera suficiente el control de cada ficha.
Se conserva esta política; no añadir un veto general por suelo desconocido.
Evidencia y verificación de instalación: `tmp/soil-label-local-20260917/`.

### GBIF: copia local y revisión pendiente del usuario

Actualización 17/09/2026: el visor instalado permite
**Pendiente/Dudosa/Aceptada/Rechazada**. `approved` conserva la clave de Aceptada
para compatibilidad con revisiones previas; `rejected` es el nuevo estado.
Incluido en filtro, recuentos, importación/exportación y autoguardado.
Prueba Chrome aislada correcta: persistencia en archivo y recarga, 1.928 registros
conservados y ninguna revisión real modificada por la prueba.

**Pendiente del usuario — 17/09/2026:** revisar manualmente las observaciones
**descargadas de GBIF** en el visor local, clasificándolas como Pendiente, Dudosa,
Aceptada o Rechazada. El usuario confirma que esta revisión queda a su cargo; no se da por
completada ni se presupone cuántas citas ha revisado. Conservar su archivo de
revisión y esperar su indicación antes de incorporar citas, generar zonas/setales
o iniciar comparaciones de entrenamiento. No revisar ni aprobar por él automáticamente.

Por petición del usuario, descarga local terminada y verificada el 16/09/2026,
20:43 UTC: **1.928 registros y 2.291 fotos** de Catalunya, 19/06/2012–16/09/2026.
Sin filtro de proveedor FUNGCAT: se consultaron todos los proveedores disponibles
para los 21 perfiles del catálogo local (22 taxones consultados; límites de los
complejos documentados). Conserva todos los campos interpretados y originales
disponibles en los endpoints consultados, metadatos y archivos de imagen.
Hay 593 registros con incertidumbre declarada ≤1 km, 154 superiores y 1.181
desconocidos; la copia conserva todos. [Entrada y evidencia](../mushrooms/GBIF/README.md).

Datos y fotos excluidos de Git y Docker, unos 1,9 GB locales. Verificadas imágenes,
enlaces offline y huellas de observaciones, setales y catálogo, sin modificaciones
operativas. La descarga GBIF no importó datos operativos ni inició entrenamiento o precálculo.
Sus herramientas se versionaron después en el commit de 0.2.309. Próximo paso:
revisión manual de esta copia por parte del usuario. Las dos vías posteriores
(observaciones y puntos candidatos) quedan a la espera. No redescargar por rutina. Esta investigación no revalida los contenedores ni HA real descritos debajo.

Objetivo posterior: incorporar citas conservando procedencia GBIF e incertidumbre
original; usar ≤1 km como criterio inicial y tratar la desconocida por separado.
El usuario propone abundancia «Normal» si no hay abundancia publicada, pendiente
de resolver al integrar. Comparar modelos con observaciones propias, solo GBIF
y ambas combinadas; ninguna de esas pruebas se ha iniciado. La otra vía es
identificar zonas de fructificación por especie, separadas de los setales propios.

Visor de investigación separado en `index.html`: MapLibre 4.7.1 con los cuatro
fondos online del mapa compartido (Satélite+, Híbrido, Topográfico, Liberty),
selector de especie/todas, filtros de incertidumbre y fichas con fotos locales.
`Mostrar incertidumbre` activa los círculos: azul con radio publicado; rojo de
500 m como convención visual para desconocidos, sin cambiar su valor original
ni su elegibilidad. El usuario descartó un fondo cartográfico local esquemático.
Observaciones/fotos no se vuelven a consultar a GBIF. La galería anterior se
conserva en `gallery.html`. La futura integración como zonas por especie en el
mapa de predicción quedó propuesta para más adelante; todavía no implementada.

El filtro combinado `≤1 km y desconocidas` incluye 1.774 registros. Las fichas
muestran bajo las coordenadas la altitud del DEM local (1.928 disponibles) y el
municipio de los polígonos IGN locales (1.926 disponibles; dos sin cobertura).
La extracción local consultó 1.151 coordenadas únicas y conserva resultados y
fuentes en `metadata/geography.json` de la copia, sin alterar los originales GBIF.
Los 500 m de desconocidos continúan siendo solo visuales.
Cabecera/filtros compactos y mapa a todo el ancho, ajustado verticalmente a la
ventana. Se eliminó la lista lateral: ficha superpuesta al pulsar, con cierre y
scroll propio. Los números de grupos cuentan registros; comprobados dos pares
coincidentes de Boletus aereus en La Selva del Camp, conservados sin deduplicación.
El visor permite abrir cada registro coincidente. Verificación en navegador de
desktop/móvil, límites de pantalla, filtros, fichas, recuentos y ausencia de llamadas
a GBIF en `viewer/browser-validation.json` dentro de la copia local.
La ficha muestra primero las fotografías completas, con desplazamiento horizontal
si hay varias; los campos secundarios quedan en «Más datos y procedencia».
Se verifica específicamente la foto de GBIF `4978365738` visible al abrir, sin
scroll inicial, en escritorio, portátil y móvil.

Revisión manual del visor: Pendiente (inicial), Dudosa, Aceptada y Rechazada, con
selector en la ficha, filtro combinado y recuentos. Guardado automático en el
navegador (`localStorage`, huella de la copia); Exportar/Importar revisión permite
conservar y recuperar un JSON con ID GBIF, estado y fecha. Importar fusiona por
fecha más reciente; no sobrescribe decisiones recientes con exportaciones viejas.
Guardado automático en archivo añadido: «Activar guardado en archivo» elige
una carpeta en Chrome y crea/combina `gbif-revision-autoguardado.json`, que se
actualiza tras cada cambio. Recuerda el handle en IndexedDB; al reabrir recupera
el archivo o pide «Reanudar guardado» si Chrome exige permiso. Confirma guardado
solo tras cerrar la escritura; errores preservan el archivo anterior y los cambios
en el navegador. Exportar queda como copia voluntaria; las exportaciones no se
actualizan solas. Prueba con FileSystemFileHandle real en OPFS/localhost de pruebas
(el selector nativo se sustituye), escrituras, fallo antes de cerrar, reintento y
recuperación desde archivo. No se ha forzado un crash real de Chrome.
Bajo zoom: 2D/3D con relieve Terrarium online del mapa de predicción (1×), pitch
55° al activar y 0° al desactivar; ↑N conserva centro/zoom/pitch. La activación
se conserva al cambiar de fondo; no cambia los DEM locales ni las observaciones.
No se ha importado nada en observaciones operativas. Prueba dirigida de navegador
verifica recarga, estados/filtros, exportación/importación, rechazos atómicos,
fallos de escritura y conservación de decisiones recientes; fotos siguen visibles.

| Componente | Estado al cierre | Evidencia / límite |
| --- | --- | --- |
| HA real | Última instalación terminada comunicada: 0.2.308; usuario anuncia instalación de 0.2.309 | Finalización y versión efectiva de 0.2.309 no confirmadas |
| Datos GIS en HA real | Mapping almacenado idéntico byte a byte al local, verificado el 17/09 vía SMB LAN | Consumo efectivo de HA real/worker y JSON de auditoría no revalidados; [evidencia](../reports/gis-mapping-ha-parity-2026-09-17.json) |
| HA local | Contenedor `rainmapper-local-rainmapper-ha-ui-1`, reconstruido y recreado con candidata 0.2.309 | 200 archivos coincidentes, etiqueta local `local-ha-ui` |
| Worker | Un único `rainmapper-worker`, imagen `rainmapper-worker:1.1.3`, reconstruido y recreado, healthy | 107 archivos coincidentes; ambos archivos de destinos conservan sus SHA; sin nueva publicación del worker |
| Predictor local | Presentación `IFF:88/100`, tooltip conservado | Renderizado comprobado en ES/CA/EN dentro del contenedor; publicado en 0.2.308 |
| Release disponible | HA `0.2.309` y `latest` en GHCR | Mismo digest y manifests amd64/arm64 verificados; [informe](../reports/ha-release-0.2.309.json) |

Mapa local: <http://127.0.0.1:8101/protected/maplibre/index.html>.
El worker conserva `http://100.111.77.48:8100` y la asociación
`http://rainmapper-ha-ui:8100`, comprobadas en
`/var/lib/rainmapper-worker/config/{coordinator,additional-coordinators}.json`.
No modificar sus destinos ni crear un segundo worker por conveniencia de pruebas.
Codex no debe usar Tailscale/SMB por Tailscale; esa restricción no autoriza cambiar
la URL persistida del worker.

## Revisión GIS: resultado real y límite

Tanda de **488 códigos**: **145 aceptados**, **343 pendientes**. De los pendientes,
**12** tienen investigación específica con una limitación documentada y **331**
no tienen investigación específica suficiente. Los 12 no están declarados
irresolubles ni se considera agotada su bibliografía.

El inventario mantiene **1.055 códigos geológicos**, **277 MVC** y **4 de cubiertas**:
1.336 identidades, representadas mediante 477 reglas físicas, dentro del límite
existente de 512. Hay 712 códigos geológicos con suelo aceptado: 567 anteriores
más los 145 de esta tanda. **Los 567 anteriores no se han vuelto a justificar en
esta tanda**. Inventariar/materiales aceptados no equivale a suelo revisado.

Los 145 nuevos son 95 silíceos, 32 mixtos y 18 calcáreos. No se han renombrado
fuentes ni cambiado los mappings MVC. La evidencia se refiere a componentes del
sustrato cartografiado, no a textura/pH medidos en cada suelo superficial.

### Archivos activos y entrega comunicada

Bajo `docker-data/mushroom-data/` en local y
`/share/rainmapper/mushroom-data/` en HA real:

- `mushroom_gis_mappings.json` — 256.816 bytes; SHA-256
  `054a92665b10e4d7d54801eced3657998eeab731fc31cb17b2d7d67fbc9c7f20`.
- `gis-mapping-reviews/unresolved-substrates-2026-09-16.json` — 985.024 bytes;
  SHA-256 `26196b1f191fd1e9d52906ff4058bdd5c50eb48b50b7bef2de724043819e70d1`.

Son los dos archivos de la última subida comunicada por el usuario. El 17/09 se
releyó el mapping local y `/Volumes/share/rainmapper/mushroom-data/mushroom_gis_mappings.json`
en HA real por SMB LAN: **idénticos byte a byte**, 256.816 bytes y SHA indicado.
No hace falta volver a copiar el mapping. Esta comparación no acredita el consumo
en runtime ni revalida el segundo JSON de auditoría. [Comparación](../reports/gis-mapping-ha-parity-2026-09-17.json).
El catálogo no cambió en aquella tanda. `gis-mapping-reviews` contiene justificaciones JSON,
**no copias de seguridad**: conservar las auditorías referenciadas.

En la validación GIS del 16/09 se comprobó la coincidencia de ambos
lectores efectivos para los 1.055 códigos geológicos / 1.336 identidades. Esto
valida carga e interpretación, no presencia real de setas. Detalles:
[informe](../gis-review-2026-09-16.md) y
[método breve para retomar](../mushrooms/gis-soil-review-method-es.md).

Cambiar estos mappings no requiere entrenar ni precalcular para las consultas
puntuales del mapa: `EcologyReader._refresh` en
`rainmapper_core/mushroom_map_ecology.py` refresca las entradas, y
`rainmapper_core/mushroom_map_runtime.py` sincroniza versiones privadas en
background reutilizando modelos/meteorología. No significa que los artefactos
ya entrenados o precalculados del Predictor se reescriban. El consumo de la
última subida en HA real/worker queda por comprobar, sin relanzar trabajos costosos.

## Material necesario para retomar

`tmp/soil-review-after-0.2.307/` contiene `baseline/`, `candidate/`,
`build_review.py`, `verify_review.py`, `install_local.py`, `research-queue.json`,
`research-depth-count.json`, `geographic-scope.json`, `validation.json` y `sources/`.
Las fuentes ocupan aproximadamente 90 MiB. Mantener este trabajo y sus referencias:
no es una carpeta de entrega prescindible. Parte está fuera del seguimiento de Git;
no asumir que otra máquina o un clon nuevo lo tendrá.

Investigar por unidad/formación/facies y ámbito, con fuentes ICGC/IGME y estudios
primarios; registrar URL/localizador/huella y alcance. No aceptar por palabras
clave, por apariencia del bosque ni por falta de evidencia en contra. Silíceo y
calcáreo pueden coexistir cuando estén justificados; las exclusiones de la ficha
siguen siendo explícitas. No inventar pH, textura o descalcificación desde roca.

## UI, release y disco

IFF es favorabilidad relativa 0–100, no probabilidad. Se conserva el acrónimo en
ES/CA/EN, tooltip también sin cálculo, escala de colores y presentación compacta.
El cambio publicado en `0.2.308` está en `rainmapper-app/app/mushroom_predictor_ui.py`:
dos puntos tras IFF en tarjetas/detalle. Huella host/contenedor comprobada:
`7c5cf97a63d6cb63a88a1d2cdcaafe9ae543bd846e7bc47874344a455d53690b`.
El usuario comunicó después que la instalación de 0.2.308 terminó. Datos
históricos de esa release: 1.613 tests, 48 omitidos, correcto;
metadatos y cache-busters 0.2.308 alineados. No se ha repetido el circuito costoso
para este cambio exclusivamente de presentación.

Limpieza ejecutada anteriormente en la sesión según
`tmp/disk-cleanup-20260916.json`: retiradas entregas/copias obsoletas, backups
25,75 GiB → 10,6 MiB, 4,32 GiB de copias antiguas y 1,917 GB de caché Docker.
Espacio libre observado entonces: aproximadamente 91 → 122 GiB; no es una medida
nueva al cierre. GHCR: informe `tmp/release-0.2.307/cleanup/ghcr-result.json`
registra 80 versiones eliminadas y conservación de 0.2.307/latest y 0.2.305 con
sus manifests; 0.2.306 retirada. No se ha repetido inventario remoto al cierre.
Python 3.11-slim se conserva por decisión del usuario; 3.14 es trabajo futuro.
No hacer más limpieza ni recrear paquetes de rollback no solicitados.

## Worktree y riesgos de continuidad

- HA `0.2.309` publicada y commit `0ce6de3` enviado a `origin/inicial`.
  Antes de este cierre documental solo estaba modificado el archivo de
  observaciones del usuario; ahora se añaden los cambios documentales locales.
  No hay otro cambio ejecutable pendiente verificado en el worktree.
  La revisión GIS no se ha reanudado.
- `mushroom-data/mushroom_observations.json` modificado es dato del usuario:
  preservado fuera del commit. Scripts y documentación GBIF revisados se
  versionan; snapshots, media y revisiones permanecen ignorados.
- No hay revisión científica completa: faltan los 343 casos y los 567 previos
  no son una nueva auditoría. Una etiqueta ausente requiere diagnóstico específico.
- No sobrescribir datos de HA real con semillas del repo ni asumir paridad con
  `docker-data/`. Tampoco extrapolar rendimiento del M1 a la RPi4.
- Publicación futura: seguir `release-flow.md`, paridad local y validación
  proporcional del código definitivo; no repetir entrenamiento/precálculo solo
  por cerrar documentación o por cambiar etiquetas del mapa.

La arquitectura no ha cambiado en este cierre documental. Para contexto histórico
opcional: [archivo anterior](../reports/session-context-before-close-2026-09-16.md).
Las decisiones vigentes de esta sesión encabezan [decisions.md](../decisions.md).
Durante cualquier trabajo, informar brevemente al usuario aproximadamente cada minuto.
No relanzar builds, entrenamiento, precálculo ni revisión GIS para compactar documentación.
