# Consolidación de cartografía compartida — revisión del 15/09/2026

**Estado: implementación, aceptación y limpieza locales terminadas.**
Dos entradas de HA real copiadas y verificadas desde Mac; originales conservados.
La adopción está activa solo en HA local. No se ha instalado ni publicado una
release en HA real. [Informe final](../reports/shared-geography-acceptance-2026-09-15.json).

## Implementación actual

- `mushroom_geography_store.py`: objetos por SHA, recibos indexados en SQLite y
  vistas de enlaces duros. No usa mtime como identidad del contenido.
- `mushroom_geography_import.py` y `scripts/manage-shared-geography.py`: adopción
  offline, verificación una vez o entrada ya verificada; activación explícita.
  Un paquete incremental puede omitir los objetos presentes en el almacén.
- `mushroom_worker_dataset_cache.py` y `mushroom_map_geography_runtime.py`:
  consultan el mismo almacén antes de transportar. Mantienen sus contratos y
  selecciones por coordinador. El dataset científico conserva sus 13 archivos.
- Lectores de terreno, bosque, geología, cubiertas y OpenLandMap: validan identidad
  física nativa separada del mtime lógico original. No cambian índices ni contextos.
- `mushroom_rebuild_snapshot.py`: manifiesto GIS sellado y validación de metadatos;
  no abre rásteres para construir el inventario del siguiente trabajo.

Estructura efectiva (no confundir con la propuesta inicial más abajo):

```text
/media/rainmapper/geography/
  objects/<sha256>
  receipts.sqlite
  generations/<revision>/                # mapa: manifest.json + geography-sources.json
  datasets/mushroom_gis_v0/versions/<fp>/  # GIS + auxiliares; contrato de 13 archivos
  datasets/mushroom_gis_v0/current
  CURRENT.json                           # publicación del mapa
  imports/                               # entradas verificadas, luego retirables
```

En el worker, `geography/objects` y `receipts.sqlite` son comunes. Sus vistas de
mapa permanecen bajo `geography/coordinators/<id>/versions`; las científicas
conservan `datasets/mushroom_gis_v0/versions` para no romper referencias de jobs.
Estas rutas son enlaces al mismo contenido, no otras copias físicas.

**Los recibos nativos se crean dentro de HA o del worker.** Los inodos/dispositivos
que ve Mac/SMB no son trasladables a Linux. Mac verifica los bytes copiados;
la adopción explícita dentro de HA registra los metadatos de su filesystem.
No activar una copia de `geography-sources.json` generada en otra máquina.

Validación nueva: smoke 1.594/48, cuatro puntos GIS con igualdad total de valores
y contextos, seis consultas autenticadas HA/worker con igualdad de resultados.
El worker reutilizó 3.510 archivos con 0 bytes de payload transferidos/rehasheados.
El importador incremental tiene seis tests dirigidos tras su último ajuste.
Circuito científico completo: reconstrucción/base promocionadas, 714/714 ajustes
multiversión correctos y precálculo recibido/activado. Tras recrear las imágenes
finales y limpiar, seis consultas nuevas conservan paridad exacta; todos los
recibos son válidos. Reinicio del worker: 0 bytes de transporte/hash de geografía.

## Limpieza local aplicada

- Worker persistente `rainmapper-worker-data`: cinco archivos de una versión
  científica antigua pasan a enlaces del almacén común; se retira `map-geography`.
  Liberados **5.457.006.592 bytes asignados** (5,46 GB / 5,08 GiB). Las versiones
  científicas y su puntero activo se conservan.
- HA local: retiradas las carpetas provisionales `prediction-map` y
  `geography-import-verified` bajo `docker-media/rainmapper`. Liberados 4.009.984
  bytes; los payloads grandes ya compartían inodo con el almacén consolidado.
- Limpieza con servicios parados, trabajos terminados, referencias verificadas
  antes y recibos actualizados después. Datos privados, backups, fuentes del
  repositorio, configuraciones y URLs de coordinador conservados.
- **HA real: ningún borrado ni movimiento.** El usuario retirará originales solo
  después de probar la adopción nativa. Las cifras de enlaces lógicos no se deben
  sumar como si fueran ocupación física.

## Próximo paso en HA real: adopción nativa, todavía NO ejecutada

Los datos ya están copiados. No volver a subirlos. Las entradas son:

1. `/media/rainmapper/geography/imports/local-20260914`: mapa completo y manifiesto.
2. `/media/rainmapper/geography/imports/legacy-gis-20260915`: `dataset.json`,
   `auxiliary.json` y solo 1.084.029.490 bytes que faltaban en la primera entrada.
   Los 5.736.287.356 bytes compartidos se reutilizan por SHA.

Después de instalar la versión aceptada que incluya estos comandos, ejecutar
**dentro del contenedor HA**, en este orden. `--sealed-source` corresponde a las
copias verificadas el 15/09: no usarlo si se han modificado desde esa verificación.
Crea recibos Linux y enlaces sin rehashear/copiar los GiB en la RPi4.

```sh
python /app/scripts/manage-shared-geography.py import-map \
  --root /media/rainmapper/geography \
  --source /media/rainmapper/geography/imports/local-20260914 \
  --generation local-20260914 --sealed-source

python /app/scripts/manage-shared-geography.py import-dataset \
  --root /media/rainmapper/geography \
  --source /media/rainmapper/geography/imports/legacy-gis-20260915 \
  --manifest /media/rainmapper/geography/imports/legacy-gis-20260915/dataset.json \
  --auxiliary-manifest /media/rainmapper/geography/imports/legacy-gis-20260915/auxiliary.json \
  --sealed-source
```

La importación no cambia la publicación activa. Tras comprobar ambos resultados,
la activación explícita es:

```sh
python /app/scripts/manage-shared-geography.py publish-dataset \
  --root /media/rainmapper/geography \
  --fingerprint sha256:7410f2e2482b77688027440fa047344bba65285fa2f9e812c07c65f769981574

python /app/scripts/manage-prediction-map-volume.py publish \
  --publication-root /media/rainmapper/geography --generation local-20260914
```

La configuración del mapa debe apuntar `geography_publication_root` a
`/media/rainmapper/geography`, preservando los demás campos. GIS/SoilGrids usan
la vista publicada común salvo una ruta explícita configurada; revisar esa ruta
antes de dar por migrado cada consumidor. Heartbeat anuncia el manifiesto actual;
el worker prepara su vista fuera del clic y reutiliza los objetos conocidos.
No transportar los archivos auxiliares de SoilGrids en cada trabajo científico.

Comprobar mapa, snapshot de 13 archivos, caché disponible y recibos nativos antes
de retirar entradas/originales. La eliminación de enlaces cambia ctime: debe
refrescar los recibos del almacén en una operación controlada. No copiar recibos
SQLite o `geography-sources.json` del Mac ni borrar carpetas manualmente mientras
los servicios están usando la caché. Para HA real aún no se ha aplicado limpieza.

## Revisión inicial histórica (antes de implementar)

## Resultado medido

Sí existe duplicación entre el dataset GIS de reconstrucción y la publicación
geográfica del mapa. La caché nueva reutiliza archivos entre sus propias versiones,
pero no consulta la caché GIS anterior. Deben compartir almacenamiento.

[Informe de evidencia](../reports/gis-consolidation-review-2026-09-15.json).
Se han leído metadatos mediante el volumen SMB ya montado y manifiestos existentes;
no se han leído/rehasheado los GiB de rásteres o vectores.

| Ubicación en HA real, bajo `/media/rainmapper/` | Archivos | Bytes lógicos |
| --- | ---: | ---: |
| `mushroom-GIS` | 1.432 | 6.820.316.846 |
| `prediction-map/generations/local-20260914/mushroom-GIS` | 3 | 5.241.749.525 |
| `prediction-map/generations/local-20260914/mushroom-map-GIS` | 3.507 | 9.296.464.776 |
| Total de estas tres carpetas, sin manifiesto raíz | 4.942 | 21.358.531.147 |

Los tamaños son sumas de archivos, no una medición de bloques físicos ocupados.
Las dos subcarpetas de la generación nueva **no son dos copias completas entre sí**:
la primera contiene tres DEM regionales; la segunda contiene el resto de fuentes
y los índices preparados. El solapamiento principal es con la carpeta antigua.

| Contenido compartido | Bytes de una copia | Evidencia |
| --- | ---: | --- |
| DEM Cataluña 5 m | 5.127.260.482 | Hash persistido igual entre ambos circuitos del worker; inodos distintos |
| Geología ICGC 1:50.000 | 293.679.104 | Igual; cambia la ruta de la fuente |
| DEM Francia 5 m | 83.072.534 | Igual |
| DEM Andorra 5 m | 31.416.509 | Igual |
| DEM IGN hoja 592 | 3.736.503 | Igual; cambia también el nombre del archivo |
| Codificación `.cpg` | 5 | Igual; no implica que las capas completas sean equivalentes |
| SoilGrids normalizado, 1.355 teselas | 197.122.219 | Hashes iguales en ambos manifiestos de HA y tamaños actuales coincidentes |

**Worker:** seis coincidencias con hash persistido igual e inodos diferentes,
5.539.165.137 bytes. La comparación es entre `datasets/mushroom_gis_v0` y
`map-geography`; dentro de cada circuito ya hay enlaces duros que no deben
contabilizarse como copias adicionales. No se ha auditado aquí toda la retención
histórica del volumen ni calculado un ahorro total del worker.

**HA:** los cinco archivos grandes anteriores existen en la carpeta antigua con
el tamaño esperado y en la generación nueva con el hash del manifiesto preparado.
No se ha recalculado el hash del contenido antiguo en HA. Los hashes de SoilGrids
sí están declarados en ambos manifiestos actuales. Son candidatos a consolidación;
antes de retirar una copia se debe validar su identidad nativa y la vigencia del
recibo correspondiente. Una igualdad de nombre/tamaño no basta para borrar.

El ahorro potencial identificado en HA es **5.736.287.356 bytes (5,74 GB / 5,34 GiB)**.
Estas tres carpetas pasarían de unos 21,36 a 15,62 GB lógicos, más metadatos, si se
confirman los candidatos. No es una promesa de espacio físico liberado ni incluye
otras copias/backups de HA.

## Contenido que no debe confundirse con duplicación

- MVC50mil antiguo ocupa 885 MB y MFE del mapa unos 1,64 GB incluyendo auxiliares.
  Son capas diferentes, con contratos y campos distintos; no sustituir una por otra.
- SoilGrids antiguo conserva 197 MB de descargas WCS originales y 197 MB de teselas
  normalizadas. Las 1.355 normalizadas aparecen en el mapa bajo
  `source/existing-retention/normalized/`. Los originales por bloques y las teselas
  no son archivos idénticos; conservar procedencia y decidir su retención aparte.
- El nuevo conjunto incluye IGN MDT25, municipios, cubiertas ICGC, OpenLandMap e
  índices que no están en el dataset GIS de 13 archivos de reconstrucción.
- Un índice espacial, una geometría subdividida y su fuente tienen usos distintos.
  Consolidar almacenamiento no autoriza a eliminarlos ni a regenerarlos.
- El relieve visual del visor MapLibre usa teselas Terrarium remotas:
  `rainmapper_core/viewers/maplibre-viewer/app.js:41`. No consume directamente estos
  TIFF para dibujar el relieve. El GIS local sirve a los lectores y procesos que
  lo solicitan; no hay que forzar que cada mapa o job descargue todas las capas.

## Por qué ocurre y qué código cambia

Referencias al código revisado en este worktree; los nombres de la estructura
propuesta más abajo todavía no existen como contrato implementado.

| Componente actual | Comportamiento comprobado | Cambio necesario |
| --- | --- | --- |
| `mushroom_gis_lab.py:58`, `:109` | Resuelve `/media/rainmapper/mushroom-GIS`; rutas del dataset anterior | Resolver una vista del catálogo común, conservando los contratos de capas |
| `mushroom_rebuild_snapshot.py:147`, `:205` | Dataset de reconstrucción; caché de hashes por identidad física y rutas | Tomar hashes de una publicación verificada y fijar sus dependencias por job |
| `mushroom_worker_transport.py:374` | Sirve archivos por ruta declarada en el manifiesto inmutable del trabajo | Resolver esa referencia contra el almacén común sin ampliar el acceso autorizado |
| `mushroom_worker_dataset_cache.py:156`, `:328` | Reutiliza archivos de su propia versión anterior y misma ruta | Buscar por hash en el almacén público compartido antes de descargar |
| `mushroom_map_volume.py:40`, `:116` | Empaqueta dependencias en una generación que conserva las rutas locales | Exportar/adoptar objetos únicos y manifiestos por consumidor |
| `mushroom_map_geography_runtime.py:304` | Identifica objetos por SHA **más mtime** | Identidad de contenido por SHA; sello físico separado de metadatos de origen |
| `mushroom_map_geography_runtime.py:428` | Limpieza limitada a sus propias versiones/objetos | Retención común que conozca referencias y trabajos de todos los consumidores |
| `mushroom_map_terrain.py:74`, `mushroom_map_forest.py:119`, `mushroom_map_land_parts.py:17` | Lectores comprueban rutas y timestamps de fuentes preparadas | Resolver fuentes selladas sin exigir que un mismo objeto tenga distintos mtimes |

No basta con cambiar una ruta o crear symlinks hacia fuera: los resolutores
comprueban que las fuentes permanezcan dentro de la raíz autorizada. Además,
`soil_water_context` (`mushroom_map_terrain.py:203`) incorpora ruta y mtime de origen
a su identidad. Hay que conservar esa procedencia lógica durante la migración;
cambiar de ubicación física no debe cambiar valores ni invalidar innecesariamente
contextos/modelos. Modificar el contrato científico requeriría otra validación.

## Estructura propuesta: una raíz de cartografía por máquina

En HA, **`/media/rainmapper/geography/`**, y en el volumen persistente del worker,
**`/var/lib/rainmapper-worker/geography/`**. No dentro de las imágenes.

```text
geography/
  objects/<sha256>                 # contenido inmutable, una copia
  manifests/<revision>.json        # capa, edición, licencia y dependencias
  views/<consumer>/<revision>/     # rutas compatibles, enlaces duros
  receipts/                       # identidad física verificada localmente
  staging/                        # transferencias incompletas y reanudables
```

Los punteros activos en el worker deben seguir separados por coordinador y
consumidor. Se comparte contenido público idéntico, no permisos ni selección de
versiones. Los datos privados —fichas, mappings, observaciones, modelos y meteo—
mantienen su autoridad y aislamiento actuales; no se mezclan con este catálogo.

Las vistas contienen enlaces duros o referencias resueltas por el lector, no una
copia física por mapa/job. Los sidecars de shapefile permanecen agrupados con sus
nombres lógicos. Si el sistema de archivos no permite enlaces duros, no hacer una
copia silenciosa de varios GiB: usar el resolutor o declarar la limitación.

Cada consumidor declara **solo sus dependencias**. La reconstrucción puede seguir
usando su dataset actual, el mapa sus capas puntuales, y entrenamiento/precálculo
los contextos/artefactos que ya reciben. Compartir el almacén no exige enviar toda
la cartografía a cada entrenamiento ni sustituir sus entradas científicas.

## Hashes, actualizaciones y transporte

1. Preparar y sellar archivos nuevos en el Mac o en el productor: SHA una sola vez
   por contenido. La revisión pequeña del manifiesto identifica el conjunto.
2. HA adopta la publicación y guarda un recibo nativo de sus archivos. Reutiliza
   hashes ya verificados, sin recorrer/rehashear el árbol en cada clic o heartbeat.
   Copiar un archivo y un hash declarado no demuestra por sí solo su integridad:
   el recibo debe proceder de una verificación fiable de esa copia.
3. Las actualizaciones son publicaciones explícitas y atómicas. HA observa el
   puntero pequeño y anuncia su revisión; no intenta detectar cambios arbitrarios
   en miles de archivos. Una edición manual exige republicar; una discrepancia
   detectada provoca abstención/error y revisión, nunca un rehash masivo implícito.
4. El heartbeat anuncia referencias y disponibilidad. La transferencia ocurre
   aparte, asincrónica, por el mecanismo de preparación existente y con el canal
   background; no transporta los GiB dentro del heartbeat. Respeta los trabajos
   científicos y libera recursos entre bloques.
5. El worker obtiene el manifiesto solo cuando cambia; busca cada SHA en el almacén
   común y pide únicamente objetos ausentes. Descarga reanudable, verificación del
   contenido al recibir y recibo persistido; reinicio caliente sin rehash completo.
6. El clic online referencia una versión ya preparada. Cada consulta/job fija esa
   versión hasta terminar. El cambio de fecha o de fichas no invalida la cartografía
   si esta no ha cambiado. La preparación y la cola online conservan sus límites.

El hash de contenido no puede incluir el nombre o el mtime. Estos son metadatos de
procedencia o de validación local, no una razón para descargar otra vez los mismos
bytes. Los lectores deben distinguir ambos conceptos antes de compartir inodos:
un enlace duro no puede tener un timestamp diferente del objeto al que enlaza.

## Migración propuesta sin volver a subir todo

### Preparación: copia autorizada, sin mover originales

**Instrucción posterior del usuario:** Codex debe hacer primero **copias**, no
movimientos, y el usuario retirará las carpetas sobrantes cuando todo funcione.
Esto sustituye el traslado manual indicado inicialmente abajo. Se conservarán
intactos tanto `mushroom-GIS` antiguo como la generación bajo `prediction-map`.
Autorizada la copia de esta última a `geography/imports/local-20260914` mediante
el volumen SMB ya montado. Espacio previo comprobado: 59.258.310.656 bytes libres;
necesarios con manifiesto: 14.539.022.086 bytes. Verificación de SHA durante la
copia y mediante lectura posterior del destino desde el Mac; sin hash recurrente
en HA. No activar publicación ni instalar código remoto durante esta operación.

La creación temporal de esta copia adicional es petición expresa del usuario;
el objetivo del almacén definitivo sigue siendo evitar duplicación operativa.
La limpieza queda a cargo del usuario tras aceptar el funcionamiento.

#### Instrucciones iniciales, sustituidas por la copia anterior

El usuario pide primero instrucciones de colocación; después comprobar la copia
y modificar cachés/transportes. Comprobación SMB del 15/09: existe la generación
`prediction-map/generations/local-20260914` y su manifiesto de 3.510 archivos;
`prediction-map/CURRENT.json` y la raíz `geography` no existen en HA real.
La generación nueva no está publicada mediante ese puntero.

Preparación indicada: crear `/media/rainmapper/geography/imports/` y **mover la
carpeta completa** `prediction-map/generations/local-20260914` a
`geography/imports/local-20260914`, con `manifest.json` y ambas subcarpetas dentro.
No mover archivos individualmente ni fusionar sus contenidos. `imports` es una
entrada temporal de adopción, no una nueva copia ni el diseño definitivo del almacén.
Desde el Mac estas rutas llevan el prefijo `/Volumes/media` en lugar de `/media`.

Conservar `/media/rainmapper/mushroom-GIS` en su ubicación: el código anterior la
resuelve directamente y aún puede necesitarla. No borrar duplicados, metadatos ni
backups. El traslado del paquete conserva rutas internas y manifiesto, pero deja
obsoleta su ruta de publicación anterior: no ejecutar la guía antigua de importación
durante esta transición. Después del aviso del usuario, verificar la entrada y
continuar la implementación/local acceptance autorizadas. No consta traslado
efectuado por Codex ni cambio de cachés en esta fase.

1. Crear un plan en seco con manifiestos existentes, identidad nativa, permisos,
   dispositivo y espacio. Separar coincidencias verificadas de candidatos por
   tamaño/nombre. Los archivos sin recibo fiable se verifican una vez de manera
   controlada, preferiblemente desde Mac/worker; no dar por válido un hash ajeno.
2. Adoptar archivos ya presentes mediante enlaces o movimientos dentro del mismo
   filesystem; **no crear una tercera copia**. No alterar las publicaciones selladas
   existentes mientras puedan estar en uso ni destruir backups. Las fuentes que
   todavía se escriben deben pasar a publicación atómica/copia al modificar antes
   de compartir inodos: nunca editar un objeto común en el sitio.
3. Preparar adaptadores/vistas para ambos consumidores y versiones nuevas solo de
   los metadatos o índices afectados. Reutilizar geometrías y valores preparados;
   no repetir descargas, entrenamiento o generación de rásteres por cambiar rutas.
4. Importar las cachés del worker al mismo almacén; preservar sus coordinadores,
   las referencias de trabajos y sus recibos. Cambiar un inode/ctime durante la
   adopción no debe disparar el hash del DEM de 5 GB en HA: registrar explícitamente
   la nueva identidad comprobada. No falsificar la caché anterior.
5. Probar localmente y cambiar punteros de forma atómica. Conservar vuelta atrás
   mediante manifiestos/vistas, que no requieren otra copia de los objetos.
6. Solo después de aceptación, retirar copias independientes confirmadas mediante
   un plan explícito de limpieza. Esta revisión **no autoriza ni ejecuta borrados**.

La limpieza debe considerar todas las vistas, coordinadores, versiones retenidas,
trabajos activos y transferencias. No basta con que la caché del mapa considere un
objeto antiguo: reconstrucción o un job en curso pueden seguir necesitándolo.
Retención acotada de parciales; archivos de procedencia y backups con política
separada. No eliminar datos simplemente porque no los use el mapa actual.

## Aceptación pendiente

- Pruebas de mismo hash con nombres y timestamps distintos, archivo diferente con
  igual tamaño, sidecars, inmutabilidad y acceso fuera de raíces autorizadas.
- Importación local reutilizando las dos cachés: comprobar inodos compartidos,
  cero transferencias de objetos presentes y cero hash de GiB en HA al reiniciar,
  consultar o enviar heartbeats. Medir también escrituras/serialización.
- Paridad de valores e identidades lógicas de contextos y predicciones; mapas,
  reconstrucción y procesos que consumen SoilGrids conservan sus entradas.
- Concurrencia de online/background, dos coordinadores, versión fijada por job,
  actualización de una capa, reanudación y limpieza sin borrar referencias vivas.
- Si se implementa antes de publicar HA, reconstruir HA y worker locales y ejecutar
  la aceptación proporcional al cambio transversal, siguiendo `release-flow.md`
  y AGENTS. La validación de la candidata anterior no valida este diseño futuro.

**Recomendación:** consolidar antes de cerrar la nueva release HA para evitar
perpetuar los dos circuitos. Lo que el usuario ya subió sigue sirviendo como origen
de la migración; esta revisión no requiere volver a transferir los 14,54 GB.
