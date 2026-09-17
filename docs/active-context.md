# Contexto activo — 18/09/2026, HA 0.2.310 publicada

**Restricción expresa del usuario (17/09): no acceder por SSH a la RPi4 sin
petición explícita, tampoco para consultas. Parar, instalar y arrancar Rainmapper
en HA real queda a cargo del usuario. Las consultas SSH de esta sesión fueron
de lectura; no se ha modificado HA real.**

## Estado verificado y siguiente paso — 18/09/2026

**HA 0.2.310 publicada y verificada en GHCR**: tags `0.2.310` y `latest`
con digest `sha256:d0f7e78a3d6e9393bc8991ef68751b1e315e5cd0aae0a27e08bc0ed7251958f6`,
manifests `linux/amd64` y `linux/arm64`. Script terminado con código 0; log
`tmp/media-migration-20260917/publish-after-quit-20260918.log`. El último push
invirtió 1.580,2 s en capas. [Informe final](reports/ha-release-0.2.310.json).
Se reutilizó la validación del mismo código: 1.621 tests, 48 omitidos, paridad
202/108 archivos HA/worker revalidada el 18/09. No se relanzaron entrenamientos
ni precálculos. No atribuir la lentitud exclusivamente a Docker ni a Orange:
la prueba directa sin Docker a GHCR también fue lenta, mientras la prueba
Cloudflare fue rápida; causa de red exacta no determinada.

La reorganización de `/media` sigue autorizada en ambos entornos, primero
local. **HA local migrado y validado: ocho movimientos, 1.547 archivos
conservados. HA real no se ha migrado ni modificado.** Instalar 0.2.310 no mueve
ni borra carpetas. El usuario reserva para sí parar, instalar y arrancar HA real.
Retirada de originales GIS pendiente de comprobar SHA completos y operación
offline explícita. [Propuesta](mushrooms/ha-media-organization-proposal-es.md).

El usuario cerró/reabrió Docker durante la subida. Después autorizó arrancar
worker y HA local: ambos arrancados el 18/09, worker healthy, HA local HTTP 200;
los dos archivos de coordinadores conservan exactamente sus SHA anteriores.
No se cambió ningún destino del único worker.

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
Solicita registrar los errores: siguiente cambio autorizado, posterior a la
release. Diagnóstico explícito pendiente de implementar; reintento controlado
solo propuesto. **Ninguno incluido en 0.2.310**.

### Exploración de cobertura Catalunya / Wunderground

Usuario acepta usar base **local del 17/09 a las 11:31**, sin afirmar paridad
con HA real. Primera exploración terminada: 735 estaciones con algún dato de
lluvia en siete días en Catalunya, cuatro fuentes, ceros incluidos y exclusiones
respetadas. Malla territorial de 2 km: 8.031 puntos, 175 a más de 10 km de la
estación disponible más cercana. Estaciones vecinas incluidas en distancias.

20 consultas WU near, 200 entradas, 178 IDs únicos: 143 nuevas dentro de Catalunya,
8 conocidas, 1 excluida y 26 fuera de Catalunya. Nuevas: 75 QC=1, 65 QC desconocido,
3 QC fallido. Lista inicial de 12 para revisar: reduciría hipotéticamente los
175 puntos a 110; no demuestra calidad ni mejora del IDW. **Ninguna incorporada,
ningún histórico/backfill lanzado.** Hay candidatas de QC desconocido interesantes
que no deben descartarse solo por ese campo.

[Informe local](../tmp/station-coverage-catalunya-20260918/README.md),
[mapa MapLibre](../tmp/station-coverage-catalunya-20260918/viewer/index.html),
[CSV completo](../tmp/station-coverage-catalunya-20260918/candidates.csv).
Respuestas originales, scripts y resultados conservados junto al informe;
mapa probado en Chrome: 12 prioritarias, filtro de 143 nuevas y estaciones visibles.
Siguiente fase propuesta: revisión de calidad y continuidad de un lote pequeño;
aprobar individualmente antes de preparar un backfill. No volver a consultar
la API para analizar estos mismos resultados ya descargados.

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

La release incluye los cambios de IFF descritos debajo, aviso de suelo no
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
[Decisión, cifras y límites](reports/iff-applicability-2026-09-17.md).

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
[investigación de los dos puntos](reports/two-soils-2026-09-17.md).

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
desconocidos; la copia conserva todos. [Entrada y evidencia](mushrooms/GBIF/README.md).

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
| Datos GIS en HA real | Mapping almacenado idéntico byte a byte al local, verificado el 17/09 vía SMB LAN | Consumo efectivo de HA real/worker y JSON de auditoría no revalidados; [evidencia](reports/gis-mapping-ha-parity-2026-09-17.json) |
| HA local | Contenedor `rainmapper-local-rainmapper-ha-ui-1`, reconstruido y recreado con candidata 0.2.309 | 200 archivos coincidentes, etiqueta local `local-ha-ui` |
| Worker | Un único `rainmapper-worker`, imagen `rainmapper-worker:1.1.3`, reconstruido y recreado, healthy | 107 archivos coincidentes; ambos archivos de destinos conservan sus SHA; sin nueva publicación del worker |
| Predictor local | Presentación `IFF:88/100`, tooltip conservado | Renderizado comprobado en ES/CA/EN dentro del contenedor; publicado en 0.2.308 |
| Release disponible | HA `0.2.309` y `latest` en GHCR | Mismo digest y manifests amd64/arm64 verificados; [informe](reports/ha-release-0.2.309.json) |

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
en runtime ni revalida el segundo JSON de auditoría. [Comparación](reports/gis-mapping-ha-parity-2026-09-17.json).
El catálogo no cambió en aquella tanda. `gis-mapping-reviews` contiene justificaciones JSON,
**no copias de seguridad**: conservar las auditorías referenciadas.

En la validación GIS del 16/09 se comprobó la coincidencia de ambos
lectores efectivos para los 1.055 códigos geológicos / 1.336 identidades. Esto
valida carga e interpretación, no presencia real de setas. Detalles:
[informe](gis-review-2026-09-16.md) y
[método breve para retomar](mushrooms/gis-soil-review-method-es.md).

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
opcional: [archivo anterior](reports/session-context-before-close-2026-09-16.md).
Las decisiones vigentes de esta sesión encabezan [decisions.md](decisions.md).
Durante cualquier trabajo, informar brevemente al usuario aproximadamente cada minuto.
No relanzar builds, entrenamiento, precálculo ni revisión GIS para compactar documentación.
