# Geografía operativa y fuentes — plan local, 28/09/2026

Estado: **LOCAL Y WORKER VALIDADOS; pendiente aceptación del usuario**.
Tarea global en curso hasta decidir HA real y la retirada de los antiguos.
Autorizado por el usuario el 28/09/2026.

## Objetivo y límites

Operativa significa **todo lo que necesite para ser operativo**, incluidos
originales consultados por lectores, mantenimiento de mapeos y herramientas.
HA local conserva `docker-media/rainmapper/geography/`, montada como
`/media/rainmapper/geography/`. El worker conserva `geography/` en su volumen,
su caché por contenido y enlaces duros; no crear otra copia ni cambiar destinos.

Separar material no operativo en `geography-sources/`: originales/descargas,
expansión y preparaciones/ensayos anteriores. Conservar temporalmente las raíces
antiguas como `mushroom-GIS-todelete/` y `mushroom-map-GIS-todelete/`, completas y
sin utilizarlas como fallback. No borrar archivos ni cambiar HA real, publicar
releases, iniciar entrenamiento/precálculo o alterar observaciones/modelos.
El usuario indica una ventana aproximada de dos horas sin runners; comprobar
reposo efectivo antes de recrear contenedores, no suponer que esa ventana se amplía.

## Pasos y aceptación

- [x] Registrar autorización, plan y enlace desde TODO antes de implementar.
- [x] 1. Revalidar inventario y dependencias: lectores, índices, metadatos,
  herramientas locales, scripts, montajes y exclusiones Git/Docker. Registrar
  identidad/coordinadores del worker y estado previo sin exponer credenciales.
- [x] 2. Definir y documentar el mapa de origen/destino. Completar dependencias
  operativas ausentes sin sobrescribir archivos ni cambiar contratos científicos.
  Conservar manifiestos activos y hashes de contenido salvo necesidad demostrada.
- [x] 3. Preparar `geography-sources/` y su inventario de procedencia. Mantener
  carpetas antiguas íntegras, verificar la copia y renombrarlas con `-todelete`.
  Actualizar herramientas y documentación vigente que usaban sus rutas.
- [x] 4. Eliminar el montaje local de la raíz antigua; proteger fuentes y
  `-todelete` de Git y del contexto Docker. Adaptar resolución local canónica
  respetando overrides explícitos y compatibilidad de instalaciones existentes.
- [x] 5. Pruebas dirigidas de rutas y dependencias, reconstrucción de HA local
  y del worker si su código ejecutado cambia; recrear servicios existentes y
  verificar código efectivo, identidad y destinos conservados.
- [x] 6. Comprobar lecturas geográficas reales en HA local y worker, mapeos,
  DEM/SoilGrids, fuentes vinculadas a índices y herramientas locales. Sin jobs
  operativos ni regeneración de modelos. Verificar que las rutas antiguas no
  existen/no se recrean y que `-todelete` no sostiene las pruebas.
- [x] 7. Revisar diff, validación proporcional, resultados e incidencias;
  actualizar TODO/contexto y entregar para aceptación local del usuario.
- [ ] Fase posterior: sólo tras aceptación local, decidir si hay que adaptar
  HA real. No está incluida su modificación ni la eliminación de `-todelete`.
- [ ] **Retirada final de antiguos:** tras comprobar y aceptar el funcionamiento,
  revisar que cada archivo conservable existe en geografía operativa o fuentes,
  que no hay referencias/montajes a los antiguos y que las pruebas se ejecutaron
  sin ellos. Presentar el inventario final y obtener la confirmación de borrado;
  entonces eliminar exclusivamente `mushroom-GIS-todelete/` y
  `mushroom-map-GIS-todelete/`, registrar fecha, alcance y espacio medido después.
  Petición expresa del usuario: mantener esta etapa documentada aunque la
  eliminación se haga en una sesión posterior. No es un borrado automático ahora.

## Evidencia y continuidad

Auditoría previa de esta conversación:
`tmp/geography-audit-20260928/informe.md`, `inventory.json`, `duplicates.json`,
`worker-inventory.json`, `active-reference-audit.json`. Los hashes completos
detectaron 1.316.590.855 bytes redundantes; no confundirlos con el espacio que
liberaría APFS ni sumar enlaces duros como copias independientes. Revalidar stat
de archivos implicados antes de mover/copiar; no repetir hashes de GIS sin causa.

Evidencia de implementación y pruebas: `tmp/geography-organization-20260928/`.
Este plan debe actualizarse al completar cada etapa y ante incidencias.

## Incidencias y resolución

- Inicio: hay cambios documentales anteriores y observaciones privadas ya
  modificadas. Preservarlos; no revertirlos ni incluir datos privados en commits.
- El grafo MCP no contiene los módulos territoriales recientes; consultado
  primero, se amplía el análisis mediante fuentes actuales del repositorio.
- Pendiente de comprobar: herramientas WU/GBIF tienen rutas antiguas; el montaje
  Docker de `mushroom-GIS` debe retirarse antes de renombrar para evitar que Docker
  recree una carpeta vacía y oculte una dependencia.

## Resultados y evidencia final

- Inventario actual: 5.891 archivos / 22.238.484.702 bytes en las dos raíces.
  Copiados a `geography-sources/` con SHA-256 durante escritura y lectura completa
  del destino; original intacto. Tabla exacta en `source-move-plan.json` y
  `copy-verification.jsonl`; copia del catálogo en `geography-sources/inventory.json`.
- Distribución: familias científicas y descargas del mapa en `originals/`;
  MFE nacional, GEODE y municipios franceses en `expansion/`; `prepared/` e
  índices de ensayo en `preparations/`. Cada categoría conserva su árbol relativo.
- No se ha necesitado añadir datos operativos: las dependencias utilizadas por
  mapa/mantenimiento ya están en la raíz canónica. Ningún manifiesto activo cambia.
- Worker en reposo antes de las operaciones. Identidad y hashes de configuración
  registrados en `worker-before.json`: primario `http://100.111.77.48:8100`,
  adicional `http://rainmapper-ha-ui:8100`; conservar ambos literalmente.
- 51 pruebas dirigidas correctas. Referencia funcional anterior: cuatro puntos
  geográficos en HA/worker, ambos lectores listos; inventario de mantenimiento
  con 202/62/13 valores MVC50 y 1.055 códigos geológicos, 54 coberturas SoilGrids.
- Dos herramientas archivadas requieren adaptación de rutas, registrada en
  `source-tool-adjustments.json`; no se ejecutan adquisiciones ni auditorías antiguas.
- Incidencia resuelta: una prueba del adaptador GIS antiguo utilizaba sin querer
  la geografía real instalada en el Mac. Ahora declara su raíz de fixture.
- Incidencia de entorno: smoke inicial con 1.859 tests, seis errores al abrir
  sockets HTTP por el sandbox; resto sin fallos, 55 omitidos. Se repite con permiso
  fuera del sandbox. No es un fallo geográfico ni se da el smoke por aceptado.

### Cierre local

- Renombradas las raíces a `mushroom-GIS-todelete/` y
  `mushroom-map-GIS-todelete/`, sin borrar ningún archivo. Comprobación final:
  mismo inodo/tamaño/mtime de los 5.891 originales que al copiar. Las rutas
  anteriores no existen ni fueron recreadas tras las pruebas.
- Eliminado el bind mount antiguo de HA local. Fuentes y `-todelete` excluidos
  de imágenes y datos pesados excluidos de Git; las cuatro notas/ignore que ya
  se versionaban se conservan en su nueva ubicación.
- HA local y worker reconstruidos/recreados. Comparación del código efectivo:
  147 archivos HA y 106 worker coinciden con el worktree, incluidos los cuatro
  módulos compartidos modificados y adaptadores geográficos presentes.
- Configuración e identidad persistidas del worker conservan sus tres SHA-256.
  URLs primarias/adicionales idénticas; ambos carriles en reposo al comprobarlo.
- Lecturas antes/después **idénticas**, cuatro puntos en HA y cuatro en worker,
  con todos los lectores geográficos listos. La resolución territorial entre HA
  y worker también coincide. `readers-*-before/after.json`, `comparison.json`.
- Inventario de mantenimiento completo (202/62/13 valores MVC50; 1.055 códigos
  geológicos) idéntico; manifiesto SoilGrids con 54 coberturas. Los 3.600 archivos
  del árbol operativo conservan tamaño/mtime/inodo; no se modificaron assets,
  configuración ni contratos activos. No se reentrena por este cambio de ubicación.
- Smoke fuera del sandbox: **1.859 tests, 55 omitidos, correcto**. Después del
  renombrado: **51 pruebas dirigidas, correctas**. No se repite el smoke tras
  cambios exclusivamente documentales/Git-ignore.
- Host Mac: resolutores GIS/SoilGrids y publicación apuntan a `docker-media`.
  GBIF validado con un registro sintético (elevación y municipio disponibles);
  aperturas OGR de municipios de las dos herramientas WU comprobadas en el
  contenedor existente con GDAL, usando su expresión real de resolución.
  No se ejecutaron investigaciones WU completas ni importaciones GBIF.
- Avisos GDAL sobre futura política de excepciones y una geometría con
  autointersección aparecieron antes y después; las respuestas fueron idénticas.
- Las referencias antiguas restantes en código son compatibilidad de versiones
  y rutas relativas internas de los manifiestos; ninguna apunta a `-todelete`.
- `git diff --check` correcto. No se hizo commit/push ni publicación.

Resumen persistente: [informe JSON](../reports/geography-local-organization-2026-09-28.json).
Logs y detalle en `tmp/geography-organization-20260928/`. Los cambios documentales
previos y observaciones privadas se mantienen sin revertirlos ni copiarlos.

### Qué queda pendiente

El usuario realizará mañana, 29/09, estas comprobaciones funcionales:

- [ ] Asignación de observaciones: resolución geográfica y asignación al área/setal.
- [ ] Edición de setales: recuperación de geografía y guardado.
- [ ] Importación GBIF: enriquecimiento geográfico e importación real, más allá
  del registro sintético ya probado.

Mantener ambos `-todelete` hasta completar estos recorridos y acordar su retirada.

1. Aceptación del usuario del funcionamiento local.
2. Revisión de rutas HA real realizada posteriormente en lectura: ya usa la raíz
   correcta, sin necesidad identificada de migración o release por esta tarea
   (detalle al final). No se ha modificado HA real.
3. Retirada expresa de los dos `-todelete` según la casilla anterior. Se mantienen
   completos; esta sesión no ejecuta la eliminación.

No se han lanzado entrenamiento, precálculo, descargas, runners ni cambios del
coordinador. Se conservaron datos, fuentes, modelos y generaciones operativas.

### Comprobación operativa posterior: precálculo automático de HA real

El usuario informa de su finalización; comprobado en el worker el 28/09:
`worker_job_BPJgkkhMwTKo`, coordinador `primary`, iniciado a las 15:07:59 UTC.
El registro `predictor_precompute_complete` recoge la respuesta de publicación:
HA activó a las 15:19:22 UTC y el worker a las 15:19:39 UTC. El registro
`job_thread_released` confirma `finish_acknowledged=true`.

Duración worker 699,879 s (11 min 40 s), cálculo 578,045 s, publicación HA
99,823 s; artefacto de 45.613.056 bytes. Su SQLite activo declara
`publication_state=complete`. No quedan `pending-finish.json` ni archivos en
staging; ambos carriles están en reposo. Es evidencia adicional del worker
actualizado operando con HA real, no un entrenamiento nuevo ni una inspección
del filesystem de HA. No se lanzaron trabajos para comprobarlo.

Los montajes actuales `/Volumes/share` y `/Volumes/media-1` apuntan a
`100.111.77.48` por SMB; no se accedió a ellos por la restricción de Tailscale.
Se observaron avisos de timeout/recuperación de comunicación y pausas de la
asociación de mapa; el cierre de este precálculo sí está confirmado. No se
investigan esos avisos ni se cambia la red en esta tarea.

Resultado incorporado al informe JSON enlazado arriba. La aceptación local del
usuario, la decisión sobre HA real y el borrado de `-todelete` siguen separados.

### Aclaración sobre montajes y comprobación directa de HA

El usuario aclara expresamente que se pueden usar los volúmenes que él haya
montado, aunque sean Tailscale. Codex no debe montarlos por su cuenta. La
restricción anterior se interpretó demasiado ampliamente; queda corregida en
`codex-start-here.md` y `active-context.md`.

Tras la aclaración se leen los archivos existentes en los montajes comprobados:
`/Volumes/media-1/rainmapper/results/predictor-precompute/active-receipt.json`,
`desired.json` y los metadatos del SQLite activo (modo ro/immutable), y el trabajo
concreto en `/Volumes/share/rainmapper/mushroom-data/mushroom_worker_jobs.json`.
Resultado: revisión **277**, trabajo `complete`, error vacío, mismo artifact_id y
recibo de publicación, `worker_activation=active`. El SQLite de HA declara
`publication_state=complete` y el mismo artifact_id que el activo del worker.
No se rehashea ni copia la base completa; se comprueban metadatos y recibos.
No se ha escrito nada en HA real ni iniciado trabajos.

Revisión ampliada del precálculo, retomada a petición del usuario tras aplazar
el análisis de disco: el activo sigue correspondiendo a la revisión 277 y al
recibo del trabajo. Se comparan las claves de `coverage` del SQLite remoto
(lectura ro/immutable) con `area_ids_by_species` del trabajo y los siete días
de `desired.json`: 987 esperadas y 987 presentes, cero faltantes y cero extras.
Son 141 pares especie–área distribuidos entre 10 especies, del 28/09 al 04/10;
no deben interpretarse como 141 áreas distintas para cada especie.

Telemetría persistida: sincronización runtime 0,574451 s; cálculo 578,04502 s;
transferencia estimada 2,276827 s; publicación HA 99,823347 s; activación worker
16,779103 s. El upload de ida/vuelta mide 102,100174 s e incluye la publicación,
por lo que no se suman ambas cifras. El desglose no identifica por separado
validación y activación dentro de HA. Limpieza del trabajo `complete` a las
15:19:44 UTC. Diagnóstico de lote: 1.134 solicitudes, 228 ejecutadas y escritura
SQLite `async_single_writer`. No se deduce de ello la causa de la diferencia
de duración con ejecuciones anteriores ni se comprueba científicamente cada
predicción. No se repiten builds, pruebas ni trabajos operativos.

### Auditoría de espacio posterior (28/09)

El usuario observa 145–150 GB disponibles por la mañana y 115,44 GB ahora.
Su captura de Finder incluye 35,29 GB purgables: quedan unos 80,15 GB libres,
coherentes con los 80,15 GB medidos por APFS. No hay una medición inicial de
espacio purgable ni de bloques asignados a Docker.raw que permita cerrar toda
la diferencia de 30–35 GB.

- La nueva copia `geography-sources` ocupa 22.330.249.216 bytes asignados
  (22,33 GB). Fuera de ella, el repositorio creció sólo 23.625.728 bytes respecto
  al inventario previo. Los dos `-todelete` siguen conservados.
- `docker buildx du --format=json` identifica aproximadamente 3,035 GB de
  registros de caché creados desde el inicio de los builds. No se suman tamaños
  de imágenes y caché como si fueran almacenamiento físico independiente.
- La captura de Docker Desktop muestra 66,4 GB para el volumen del worker.
  El recuento actual de tamaños de todas las rutas suma 71.258.569.248 bytes
  (66,36 GiB), compatible con esa cifra. Deduplicando por dispositivo/inodo,
  los archivos ocupan 17.594.867.712 bytes asignados (17,59 GB).
- El inventario anterior a la reorganización del mismo volumen registra
  17.774.440.448 bytes asignados únicos: ahora hay 179.572.736 bytes menos.
  Por tanto, el volumen no creció 10 GB durante esta reorganización. No existe
  aquí una medición de ayer para contrastar los 56 GB recordados por el usuario.
- Contraste adicional: `du -sk /var/lib/rainmapper-worker` devuelve 17.191.552
  KiB incluyendo directorios; con `du -skl` (repite hardlinks), 69.642.076 KiB.
  Los enlaces comparten datos; el recuento por rutas no mide bloques únicos.

Evidencia detallada en `tmp/geography-organization-20260928/disk-explanation.json`
y `worker-disk-audit.json`, comparada con
`tmp/geography-audit-20260928/worker-inventory.json`.
No se han borrado fuentes, `-todelete`, volúmenes ni cachés para investigar.

Referencia histórica aportada después por el usuario: la sesión anterior
registraba aproximadamente 56 GB aparentes frente a 16 GB reales por efecto de
los hardlinks. No es una medición actual ni disponemos aquí del comando y alcance
exactos de aquella revisión. Si el alcance y las unidades eran iguales, frente
a los 17,59 GB actuales indicaría unos 1,6 GB de crecimiento desde aquella
revisión, no 10 GB. No debe confundirse con la comparación medida antes/después
de esta reorganización (17,77 → 17,59 GB).

### Revisión de necesidad de migración/release HA

Consultados los volúmenes montados por el usuario, verificando su origen:
`/Volumes/media-1/rainmapper/geography` corresponde a
`/media/rainmapper/geography` en HA. `CURRENT.json` mantiene la generación
`local-mvc50-20260928`; su manifiesto de fuentes está en la raíz geográfica.
`map-config.json` usa `geography_publication_root: "."`; el dataset científico
y `territorial-context.json` referencian archivos bajo esa misma raíz. También
existen el manifiesto de `mushroom-GIS` y su carpeta `soilgrids`. En el primer
nivel de `/media/rainmapper` no aparecen las antiguas carpetas GIS separadas.

El diff de código conserva la prioridad existente de las rutas HA y añade
fallbacks para el host Mac y un helper de herramientas locales. La retirada del
bind antiguo afecta exclusivamente a compose local. No se identifica necesidad
de mover carpetas en HA ni publicar una versión para aplicar esta organización.
Una futura release podrá incorporar estos cambios, pero no es requisito para
que HA real use la geografía consolidada. Esto no constituye una auditoría
exhaustiva de duplicados o archivos sobrantes dentro de la geografía remota.

### Auditoría posterior de archivos sobrantes en HA real

Solicitada por el usuario y completada en lectura:
[informe del 28/09](../reports/ha-geography-files-audit-2026-09-28.md).
3.603 archivos / 16,11 GB lógicos. No se identifica otra gran copia GIS que
pueda retirarse directamente: las importaciones son metadatos, y los originales
MVC50/SoilGrids mantienen consumidores. Unos 4,02 MB de históricos son candidatos
a archivar tras acordarlo; no hay borrados ni movimientos autorizados.
Se mantienen todos los archivos de HA y los `-todelete` del Mac.

### Publicación posterior: 0.2.331 (03/10/2026)

- [x] El usuario confirma la edición circular local y autoriza la publicación.
  Release 0.2.331 publicada, incluyendo los cuatro módulos de rutas geográficas,
  ajustes locales y documentación; paridad actual HA/worker y smoke completos
  correctos. [Informe](../reports/release-ha-0.2.331-2026-10-03.md).
- [ ] Instalación de la versión en HA real a cargo del usuario. No se modifican
  sus carpetas: la revisión previa confirmó la raíz operativa correcta.
- [ ] Siguen pendientes los recorridos funcionales restantes y la autorización
  específica para retirar `-todelete`. Publicar código no autoriza ese borrado.
