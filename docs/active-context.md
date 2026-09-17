# Contexto activo — 17/09/2026, release 0.2.309

## Alcance y siguiente paso

La revisión restante de suelos está **aplazada expresamente por el usuario**.
No seguir investigando ni aceptar códigos ahora. Se ha dejado una tarea enlazada
con el método en [TODO](todo.md). La próxima sesión debe partir de este estado,
revalidarlo de forma proporcional y atender el nuevo bloque que indique el usuario.
HA `0.2.309` publicada por petición expresa del usuario: tags de versión/latest
con mismo digest y manifests AMD64/ARM64 verificados. Instalación de 0.2.309 en
HA real pendiente del usuario; comunicó que la instalación anterior de 0.2.308
había terminado. No se ha relanzado entrenamiento ni precálculo.
[Informe de release](reports/ha-release-0.2.309.json).

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
HA real no actualizado; no constituye aceptación de release ni prueba en Safari.

## Estado operativo y grado de comprobación

### IFF por punto — incluido en 0.2.309 (17/09/2026)

Por petición del usuario, auditados dos puntos cercanos de Aereus: bloqueo al
pasar de 6/160 a 8/160 columnas fuera de rango. La política candidata
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

### Investigación GBIF posterior al cierre de HA

Actualización 17/09/2026: el visor instalado de la copia local permite
Pendiente/Dudosa/Aceptada/Rechazada. `approved` se conserva como clave de Aceptada
para compatibilidad con todas las revisiones previas; `rejected` es el nuevo
estado. Incluido en filtro, recuentos, importación/exportación y autoguardado.
Prueba Chrome aislada correcta (incluyendo persistencia en archivo y recarga),
1928 registros conservados; ninguna revisión real modificada por la prueba.

Investigación puntual autorizada de Tordera (41.72905, 2.74775) y Soriguera
(42.37001, 1.06978): HA local devuelve Qt1 y Qve con geología disponible,
pero `mapped_soil_tendency_ids=[]`. Contraste espacial del ICGC y consulta
IGME: entorno granítico próximo en Tordera; varias unidades de composición
distinta junto al depósito de Soriguera. No basta para asignar composición al
depósito ni reclasificar globalmente esos códigos. Por autorización posterior,
implementada la regla general «Suelo no determinado» en cabecera y Terreno si
faltan tendencias, en ES/CA/EN; los suelos conocidos mantienen sus etiquetas.
Instalado después en HA local el 17/09, reconstruyendo y recreando solo su
contenedor. Verificado por HTTP JS/CSS idénticos al worktree y traducciones
ES/CA/EN presentes; observaciones, mappings y registro ML conservan SHA.
Worker sin recrear; no constituye aceptación de release ni actualización de HA real.
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
La ausencia de suelo no bloquea esa ficha; no se cambió esta política.
Evidencia y verificación de instalación: `tmp/soil-label-local-20260917/`.

**Pendiente del usuario — 17/09/2026:** revisar manualmente las observaciones
**descargadas de GBIF** en el visor local, clasificándolas como Pendiente, Dudosa
o Aprobada. El usuario confirma que esta revisión queda a su cargo; no se da por
completada ni se presupone cuántas citas ha revisado. Conservar su archivo de
revisión y esperar su indicación antes de incorporar citas, generar zonas/setales
o iniciar comparaciones de entrenamiento. No revisar ni aprobar por él automáticamente.

Por petición del usuario, descarga local terminada y verificada el 16/09/2026,
20:43 UTC: **1.928 registros y 2.291 fotos** de Catalunya, 19/06/2012–16/09/2026,
para los 21 perfiles del catálogo local (22 taxones consultados; límites de los
complejos documentados). Conserva todos los campos interpretados y originales
disponibles en los endpoints consultados, metadatos y archivos de imagen.
Hay 593 registros con incertidumbre declarada ≤1 km, 154 superiores y 1.181
desconocidos; la copia conserva todos. [Entrada y evidencia](mushrooms/GBIF/README.md).

Datos y fotos excluidos de Git y Docker, unos 1,9 GB locales. Verificadas imágenes,
enlaces offline y huellas de observaciones, setales y catálogo, sin modificaciones
operativas. No hubo importación, entrenamiento, precálculo, publicación ni cambios
del worker. Próximo paso: revisión manual de esta copia por parte del usuario;
las dos vías posteriores (observaciones y puntos candidatos) quedan a la espera. No redescargar por
rutina. Esta investigación no revalida los contenedores ni HA real descritos debajo.

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

Revisión manual añadida al visor: Pendiente (inicial), Dudosa y Aprobada, con
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
| HA real | Última instalación comunicada por el usuario: 0.2.308; 0.2.309 pendiente | No se ha instalado ni verificado remotamente 0.2.309 |
| Datos GIS en HA real | Usuario confirma subida de los dos JSON actualizados | No se ha comprobado remotamente su SHA ni su consumo efectivo |
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

Son los dos archivos de la última subida que comunica el usuario. El catálogo
no cambió en esta tanda. `gis-mapping-reviews` contiene justificaciones JSON,
**no copias de seguridad**: conservar las auditorías referenciadas.

Al cierre se comprobó el SHA de mappings en HA local y la coincidencia de ambos
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

- HA `0.2.309` publicada; código, test, metadatos e informe de release se cierran
  en un único commit tras verificar GHCR. La documentación previa pendiente se
  conserva en el worktree; la revisión GIS no se ha reanudado.
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
