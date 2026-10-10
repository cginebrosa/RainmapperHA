# Auditoría de disco del Mac y RainmapperHA — 03/10/2026

> **Estado al cierre:** auditoría seguida de limpiezas expresamente autorizadas.
> WhatsApp y Chrome tienen clones APFS, no el consumo físico inicialmente
> sugerido por la suma por archivo. Finder 305,36 GB y contenedor 329,08 GB
> corresponden a ámbitos distintos; quedan ~35,8 GB sin atribuir en un balance
> aproximado. Leer los apartados finales «Limpieza autorizada», «WhatsApp» y
> «Conciliación de Finder» para las conclusiones vigentes. Los apartados
> iniciales conservan las mediciones y autorizaciones de cada momento.

Revisión de tamaños y metadatos autorizada por el usuario. **Sin borrados**, sin
parar servicios, sin abrir mensajes de WhatsApp, fotografías ni contenido de
conversaciones. Evidencia en `tmp/disk-audit-20261003/`.

## Capacidad física y límites de la medición

`diskutil apfs list`: contenedor principal 494,38 GB, 348,88 GB consumidos y
145,51 GB no asignados en esa lectura. Data consume 308,08 GB; System 17,09 GB,
Preboot 17,99 GB, Recovery 2,60 GB y VM 2,15 GB. `df` inicial informa unos
150,15 GB disponibles; son lecturas/contabilidades distintas, no cifras sumables.
`tmutil listlocalsnapshots /` enumera tres snapshots de actualización de macOS;
no se ha medido su tamaño exclusivo ni se propone eliminarlos.

Los tamaños de carpetas provienen de `du -sk` o `stat.st_blocks * 512`.
No equivalen a espacio exclusivo recuperable, especialmente con inodos compartidos
(comprobados en el repo) o posible compartición de bloques APFS. Las cifras
aparentes de todo el árbol superan el uso físico: **no sumarlas** ni prometer que
borrar una carpeta liberaría toda su cifra. La discrepancia es especialmente
importante en WhatsApp y las copias firmadas de Chrome; no se ha determinado su
ocupación física exclusiva.

macOS deniega varias carpetas protegidas incluso fuera del sandbox, entre ellas
Downloads, Trash y datos de aplicaciones Apple. Los resultados con errores son
parciales; errores conservados en JSON. No se ha eludido esa protección.

## Repositorio: 47,83 GB descontando enlaces duros

Ruta: `/Users/carlosginebrosa/Developer/RainmapperHA`.
`du -sk` del árbol completo y un inventario independiente por `(dev, ino)`
coinciden en unos **47,83 GB**. Sumar subcarpetas separadas ronda 57,21 GB porque
cuenta dos veces **9,38 GB enlazados entre docker-data y docker-media**.

| Grupo | GB, asignando los compartidos a docker-media |
|---|---:|
| geography-sources | 22,26 |
| docker-media | 16,37 |
| docker-data, sólo bloques adicionales | 5,66 |
| local-apps | 1,95 |
| tmp | 0,79 |
| .venv | 0,55 |
| Resto | 0,25 |

`docker-data/territorial-validation` aparenta 9,38 GB, mayoritariamente enlaces
con la geografía operativa: borrarlo no recuperaría esos 9,38 GB mientras siga
existiendo el otro enlace. `docker-data/audits` sí contiene 4,49 GB de auditorías:
1,73 GB ablation hídrica, 1,43 GB backfill meteorológico, 0,50 GB snapshot ML,
0,39 GB investigación V5 y otros. Son evidencia histórica, no asumir basura.
`local-apps/gbif` concentra 1,92 GB. Git sólo ocupa unos 64 MB.

Las fuentes son originales preservados y la media es operativa. No están en una
lista de borrado. Los `-todelete` ya se retiraron en la tarea anterior.

## Aplicaciones y carpetas externas

| Ubicación / grupo | Tamaño medido | Observación |
|---|---:|---|
| WhatsApp, Group Containers/.../Message | 262,53 GB aparentes | Mayor anomalía; no equivale a espacio exclusivo recuperable |
| Pictures/Lightroom | 44,66 GB | 33,46 GB Previews y 10,73 GB Smart Previews |
| Docker.raw | 42,67 GB de bloques asignados | Tamaño lógico máximo 494,38 GB; no está ocupando ese máximo |
| X/com.google.Chrome.code_sign_clone | 42,86 GB aparentes | 24 carpetas de copias firmadas; compartición física sin medir |
| ~/.codex | 27,72 GB | Historial y sesiones, no sólo caché |
| /Applications | 38,24 GB | Conjunto de aplicaciones instaladas |
| VS Code: Application Support/Code + ~/.vscode | 7,55 GB | Extensiones, WebStorage y cachés |
| Temporales de usuario T | 7,31 GB | Instaladores/actualizadores dominan |
| Documents | 7,22 GB | No se revisó el contenido |
| ~/.lmstudio | 2,17 GB | 1,68 GB extensiones; carpeta habitual models vacía |
| ~/.claude | 0,007 GB | No es un foco relevante en esa ruta |
| Application Support/Land10 | 3,27 GB | 3,26 GB bajo CompeGPS |
| Application Support/Adobe | 2,92 GB | Datos de aplicación |
| Application Support/com.docker.install | 2,32 GB | Revisar como restos de instalación |

No sumar la tabla: hay tamaños aparentes, rutas de aplicación que pueden
compartir bloques y cifras incluidas en otros totales. No se ha afirmado que
Claude/LM Studio carezcan de datos en cualquier ruta personalizada del Mac;
se han medido sus ubicaciones habituales encontradas.

WhatsApp: 554.790 archivos, 261,49 GB lógicos acumulados y 262,77 GB de bloques
por fichero; ningún enlace duro múltiple. No hay un único archivo gigante:
ninguno supera 500 MB. Se consultaron metadatos, sin abrir mensajes/medios.
Que no haya hardlinks no descarta compartición APFS; no se ha cuantificado.

Codex: 20,75 GB en `archived_sessions` (62 archivos; los dos mayores, 4,68 y
2,98 GB), 2,08 GB en `sessions`, 4,26 GB en `thread_history_1.sqlite` y unos
0,39 GB en `logs_2.sqlite`. No tratar el historial como caché prescindible ni
borrar bases activas sin revisar antes su uso y la pérdida de historial.

VS Code: extensiones 3,21 GB; WebStorage 2,64 GB; CachedExtensionVSIXs 1,09 GB;
agent-host 0,30 GB; CachedData 0,15 GB. No se ha abierto WebStorage para atribuir
su contenido ni se considera automáticamente eliminable.

Docker: `docker system df -v` informa volumen worker **17,58 GB**, imágenes y
caché Buildx **19,8 GB**. `docker buildx du` separa 11,41 GB compartidos y
**8,388 GB privados**. No prometer 19,8 GB libres al limpiar: parte comparte
capas con imágenes. No tocar el volumen del worker, sus coordinadores ni
realizar un prune en esta revisión.

Temporales T: `com.docker.install` 4,63 GB, actualizador VS Code 1,49 GB,
`DockerDesktopUpdates` 0,59 GB y **247 carpetas identificadas de pruebas de
navegador Rainmapper, 0,595 GB**. `/private/tmp` es prácticamente vacío (~1 MB).
Los temporales de navegador de las pruebas del agente sí son un remanente,
pero no explican por sí solos las grandes cifras del disco.

## Priorización para una limpieza posterior, no ejecutada

1. Revisar instaladores/actualizadores abandonados y carpetas de pruebas ya
   terminadas. Confirmar que no hay actualización ni navegador usando esos archivos.
2. Revisar política de conservación del historial Codex (27,72 GB); decidir
   con el usuario qué conversaciones necesita conservar. No borrar SQLite a mano.
3. Revisar previsualizaciones de Lightroom (44,19 GB) desde el flujo de la
   aplicación, manteniendo catálogo y fotografías.
4. Revisar medios de WhatsApp desde la aplicación y aclarar el tamaño físico
   exclusivo; sus 262 GB aparentes no son una previsión de recuperación.
5. Si se desea reducir Rainmapper, revisar los 4,49 GB de auditorías históricas
   y estudiar almacenamiento externo de las fuentes (22,26 GB), conservándolas.
6. Revisar caché privada de Docker (8,39 GB) sólo con un alcance acordado que
   preserve imágenes necesarias y el volumen del worker.

No se propone un borrado global de tmp, Library, fuentes, bases de conversaciones
ni volúmenes. La autorización actual cubre auditoría; cualquier limpieza se
concretará con la lista de rutas y su impacto antes de ejecutarla.

## Revisión previa a limpieza solicitada (03/10)

El usuario pide confirmar si es inocuo eliminar sesiones archivadas, instaladores
y pruebas de navegador **antes de hacerlo**. No se ha eliminado ninguno.

- **Pruebas de navegador:** 247 carpetas, unos 0,595 GB, lista exacta en
  `browser-cleanup-reviewed.json`. Ninguna tiene symlinks en su raíz ni archivos
  abiertos en la captura `lsof -nP -F pn`. Candidatas a eliminar: se pierden perfiles,
  capturas y logs de esas pruebas, no datos operativos. Se conservan los informes
  del repo, aunque las capturas referenciadas en esos directorios dejarían de existir.
- **Sesiones archivadas:** 62 archivos `.jsonl`, 20,747 GB asignados. No aparecen
  abiertos. Borrarlos elimina el historial archivado y la posibilidad de reanudarlo;
  no es una limpieza sin pérdida. La CLI instalada ofrece `codex delete <UUID>`
  y `--force` con UUID; usar el mecanismo del producto, no borrar SQLite o índices
  manualmente. Esperar aceptación expresa de perder esas conversaciones.
  Fuente oficial leída: https://learn.chatgpt.com/docs/developer-commands#codex-delete
- **VS Code:** instalado 1.139.1; el paquete temporal con `Info.plist` completo
  es 1.140.0. Proceso ShipIt presente. Es una actualización preparada, no se puede
  dar por resto obsoleto. No tocar la instalación ni la descarga pendiente ahora.
- **Docker:** instalado 4.78.0 (229452). Hay instaladores 4.92.0 (240144) y
  4.93.0 (240920), además de `Application Support/com.docker.install/in_progress`
  con Docker.app 4.93.0. `hdiutil info -plist` confirma ambos DMG montados bajo
  `T/com.docker.install/DockerDesktop-*`, abiertos por `diskimages-helper`.
  **Corrección del desglose anterior:** los 4,63 GB vistos allí corresponden a
  contenidos de imágenes montadas; no sumarlos como otros 4,63 GB exclusivos del
  disco interno además de sus DMG. No borrar directorios montados ni manipular
  `in_progress`; antes debe aclararse/terminarse/descartarse la actualización y
  desmontarse lo que proceda. No se detuvo Docker ni el worker.

Evidencia adicional: `cleanup-candidates.json`, `candidate-open-files.json`,
`staged-installer-versions.json`, `mounted-images.plist`. Las comprobaciones
son una captura del momento; volver a comprobar uso inmediatamente antes de
cualquier limpieza aprobada. WhatsApp se investigará después, según pide el usuario.

## Limpieza autorizada y ejecutada (03/10)

El usuario confirma que no necesita las sesiones archivadas y autoriza perderlas.

- Retirados **61 de los 62 archivos archivados**, usando `codex delete UUID --force`
  para las entradas registradas y borrado de dos archivos huérfanos sin entrada en
  `state_5.sqlite`. Una entrada desapareció durante las operaciones nativas previas;
  se comprobó su ausencia tanto en archivos como en el índice antes de continuar.
- **Pendiente un archivo de 523.865.594 bytes**: la CLI devuelve repetidamente
  `Error: failed to delete session` para `01a073a6-7e39-77e2-8585-e5ab8cfcc5f0`.
  Se mantiene el archivo y su entrada archivada; no se ha editado SQLite a mano.
  La causa del error no está identificada. Las tres entradas no archivadas
  capturadas antes de reanudar la limpieza siguen presentes al finalizar.
- Eliminadas **247 carpetas de pruebas de navegador** de la lista revisada, tras
  comprobar archivos abiertos, inodos y ausencia de montajes dentro de ellas.
  Medición inmediata: +602.836.992 bytes libres. Se pierden esas capturas, perfiles
  y logs; se conservan los informes del repositorio.
- Espacio libre medido durante el conjunto de operaciones: **144,49 → 165,24 GB**,
  aproximadamente **20,76 GB más**. El intervalo incluye la limpieza de navegador;
  **no sumar otros 0,60 GB**. La actividad concurrente puede influir en la diferencia.
  `du -sk ~/.codex` pasa a 7.345.740 KiB (~7,52 GB); archivadas: 511.588 KiB.
- Instaladores de VS Code/Docker conservados por los motivos anteriores. Ningún
  cambio en HA, worker, geografía, instalaciones de aplicaciones o datos operativos.

Recibos locales: `tmp/disk-audit-20261003/archived-deletion.json` y
`browser-deletion.json`. El primero conserva los intentos fallidos además de
los resultados correctos: su número de resultados no equivale al de archivos borrados.

## WhatsApp: discrepancia resuelta mediante metadatos APFS (03/10)

La captura del usuario indica **2,31 GB** de medios. La suma por archivo no era
consumo físico exclusivo: un nuevo inventario da 263,08 GB asignados sumados, pero
**2,443 GB al contar una vez cada identificador de clon**. Hay 555.323 archivos,
6.772 identificadores de flujo distintos, 704 grupos repetidos y hasta 3.801
archivos con el mismo identificador. 549.260 archivos tienen el indicador de
compartición total. `ATTR_CMNEXT_PRIVATESIZE` suma 2,050 GB; esta última cifra
es espacio privado por archivo, no una medición de cuánto liberaría borrar
la carpeta completa (también desaparecerían referencias compartidas internas).

Se han consultado exclusivamente metadatos mediante `getattrlistbulk`, con
`ATTR_CMNEXT_CLONEID`, `ATTR_CMNEXT_PRIVATESIZE` y `ATTR_CMNEXT_EXT_FLAGS`.
El manual instalado de Apple,
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/share/man/man2/getattrlist.2`,
líneas 1239–1243 y 1294–1299, define el tamaño privado y que clones puros
comparten identificador de flujo. No se han abierto mensajes ni multimedia.
El inventario por extensión daba 219,69 GB lógicos de MP4, pero también repetía
los datos compartidos: **no presentarlo como 219 GB de vídeos físicos**.

La cifra de 2,443 GB es coherente con el orden de magnitud de los 2,31 GB de
la aplicación; no demuestra igualdad exacta de qué incluye cada contador.
WhatsApp estaba activo y los recuentos cambiaron entre capturas. No se ha
determinado por qué la aplicación mantiene tantas referencias. No hace falta
desinstalarla para explicar los 262 GB aparentes, ni se ha autorizado aquí
el borrado de su contenedor.

La misma medición en `X/com.google.Chrome.code_sign_clone` reduce 42,87 GB
sumados a 5,274 GB contando cada clon una vez; 0,750 GB son privados por archivo.
Los clones pueden compartir además con archivos fuera de esa carpeta; no
prometer 5,274 GB de recuperación.

Evidencia local: `whatsapp-structure.json`, `whatsapp-apfs.json`,
`chrome-apfs.json` y herramienta de lectura `apfs_metadata.py` bajo
`tmp/disk-audit-20261003/`. Referencia conceptual de Apple:
https://developer.apple.com/documentation/foundation/about-apple-file-system

## Balance posterior a limpieza y límites restantes

`diskutil apfs list -plist` registra 329,04 GB ocupados y 165,35 GB libres en
el contenedor principal de 494,38 GB. Data ocupa 288,24 GB; los demás volúmenes
(System, Preboot, Recovery, Update y VM) suman 40,64 GB, más metadatos del
contenedor. No confundir GB decimales con GiB: 329,04 GB son unos 306,44 GiB.

Medición dirigida posterior: repo 47,83 GB por `du` deduplicando hardlinks,
Lightroom 44,70 GB, Docker.raw 42,71 GB, aplicaciones 38,19 GB, Codex 7,52 GB,
`/opt` 7,32 GB, `/Library` visible 9,92 GB y `Data/System` visible 7,82 GB.
Hay además datos de aplicaciones en Library del usuario, documentos y otros
archivos del desglose inicial. Docker.raw se cuenta una sola vez: no sumar
sus volúmenes, imágenes o Buildx de nuevo.

El balance orientativo `accounting-approximate.json` suma unos 293,17 GB y deja
unos 35,86 GB sin atribuir respecto al contenedor; **no es una conciliación
física exacta**: mezcla capturas próximas, redondeos y posibles clones entre
categorías. La parte desconocida no puede atribuirse automáticamente a snapshots,
WhatsApp, cachés o basura. El intento autorizado fuera del sandbox sigue dando
`Operation not permitted` para Downloads, Trash, Photos Library, MobileSync,
DocumentRevisions y Spotlight; fseventsd da `Permission denied`. Es necesario
resolver el acceso macOS o aportar los tamaños de esas carpetas para cerrar esa
parte del inventario. Ninguna de ellas se ha modificado.

## Conciliación de Finder con el contenedor APFS

La captura posterior del usuario muestra 305.359.646.720 bytes usados (305,36 GB),
179,82 GB disponibles y 14,5 GB purgables. Se descarta la hipótesis GB/GiB.
Nueva consulta `diskutil apfs list -plist`: System 17.086.083.072 bytes y Data
288.281.067.520 bytes, suma 305.367.150.592 bytes: coincide con Finder salvo
7,5 MB entre instantes de medición. Los aproximadamente 329 GB anteriores
corresponden al contenedor completo, que incluye también Preboot 17,993 GB,
Recovery 2,605 GB, Update 0,806 GB, VM 2,148 GB y metadatos del contenedor.
Por tanto eran ámbitos diferentes, no unidades diferentes ni datos perdidos.

Libre físico del contenedor en esta lectura: 165.306.224.640 bytes. Sumando los
14,5 GB purgables de la captura resulta aproximadamente el disponible de Finder
(179,82 GB). Los purgables están incluidos en ese disponible; no sumarlos otra vez.

Para comparar el inventario orientativo con los 305,36 GB de Finder hay que
retirar también de los 293,17 GB inventariados los aproximadamente 23,55 GB de
volúmenes auxiliares: quedan unos 269,62 GB atribuidos y unos 35,74 GB pendientes.
Se mantienen los límites de acceso, redondeos y clones entre categorías descritos
arriba. La tabla inicial de 221,6 GB era incompleta y además incluía esos volúmenes
auxiliares; no compararla directamente con los 305,36 GB de Finder.
