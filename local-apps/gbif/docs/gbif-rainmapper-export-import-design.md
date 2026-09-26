# Exportación GBIF e importación de observaciones en Rainmapper

Diseño e implementación local del 25/09/2026. **Pendiente de prueba y aceptación
por el usuario antes de publicar en HA real.** El usuario confirma HA 0.2.323
instalada; esta tarea no ha inspeccionado ni actualizado HA real.

## Flujo disponible

1. Abrir el visor habitual y aplicar filtros de especie, incertidumbre, revisión
   y búsqueda. **Exportar a Rainmapper** congela todos los registros filtrados,
   también los situados fuera del encuadre, junto con sus revisiones actuales.
2. Elegir la carpeta del snapshot que contiene `occurrences.json` y `media/`.
   Se solicita acceso de lectura y se comprueba que su SHA-256 corresponde al
   visor. El modal muestra la carpeta de esta página como propuesta copiable,
   el nombre de la carpeta elegida y recuerda su handle para el próximo selector.
   Chrome no permite usar una ruta arbitraria como `startIn` antes de autorizarla.
   No se cambia el archivo de revisiones ni el snapshot de datos.
3. Revisar el número de observaciones, fotos, citas sin foto y lotes. **Guardar
   ZIP** pregunta el nombre y la ubicación de destino antes de preparar el
   archivo, proponiendo fecha, especie y lote como nombre editable en el selector.
   El nombre elegido queda visible. Cada lote solicita destino.
   Si el ZIP existe, valida su contrato y muestra duplicados por ID: **Ignorar
   nueva versión / Reemplazar**. Conserva las demás citas y fotos, incluida la
   procedencia del lote original por cita (`source_export`). Si la combinación
   excede las cotas, no escribe y pide elegir otro destino.
   Esta selección de destino requiere `showSaveFilePicker` (Chrome/Edge); si no
   está disponible se muestra una indicación, sin descarga silenciosa.
4. En la lista de observaciones de Rainmapper, pulsar **Importar GBIF**, elegir
   un ZIP y previsualizarlo. Marcar las observaciones nuevas que se quieran
   aceptar; las no marcadas se rechazan para ese lote. También se puede cancelar
   todo. La previsualización no añade observaciones ni instala fotos.
5. Para duplicados inequívocos, elegir **Mantener / Reemplazar** por cita; Mantener
   es el valor inicial. Reemplazar conserva el ID de Rainmapper y la fecha de
   creación, sustituye datos y fotos y vuelve a Borrador / Revisar. Si estaba
   archivada, se restaura, por decisión expresa del usuario. Identidades ambiguas
   y conflictos de proveedor se mantienen bloqueados.
6. Confirmar. Se prepara cada cita seleccionada con **GIS/DEM y microárea**;
   el modal muestra `i / total` y después la fase de guardado. Los botones de
   aceptar, rechazar y cerrar permanecen en el pie; sólo la tabla tiene scroll.
   Las explicaciones largas están plegadas. Cerrar actualiza la lista.

Los lotes pendientes pueden retomarse o cancelarse desde el mismo diálogo. Un
reintento tras un corte no duplica registros ya escritos. No hay descargas de
media remoto, entrenamiento ni precálculo en este flujo. GIS/DEM son consultas
puntuales a las fuentes locales ya configuradas, como en el formulario.

## Contrato de transporte y límites

Un ZIP **sin compresión**, con `manifest.json` y `media/<sha256>`; sin base64.
`schema = rainmapper-gbif-observations`, `version = 1`. El manifiesto contiene
`export` (lote, fecha, hash del snapshot, filtros, versión de normalización),
`records` (citas y referencias de media) y `assets` (tamaño por hash).
Las fotos idénticas se guardan una vez por paquete y una vez en destino.

| Cota | Valor actual |
| --- | ---: |
| ZIP admitido por HA | 128 MiB (134.217.728 bytes) |
| Media por lote generado por el visor | 120 MiB |
| Citas por lote | 100 |
| Fotos/archivos por paquete | 1.000 |
| Fotos por cita | 50 |
| Foto individual | 8 MiB; JPEG, PNG o WEBP; hasta 40 megapíxeles |
| Manifiesto | 4 MiB |
| Archivo operativo de observaciones tras importar | 16 MiB / 10.000 observaciones |
| Subidas pendientes simultáneas | 2 |

El visor divide la selección en lotes; no omite observaciones por exceder el
primer lote. Una foto que exceda la cota impide preparar el lote y requiere
resolver el caso. La recepción escribe en disco y calcula hashes por bloques
de 256 KiB. Se comprueban espacio libre, directorio central antes de cargarlo,
rutas, entradas repetidas, enlaces, cifrado, tamaños, CRC y SHA-256. Los enlaces
de procedencia no son instrucciones de descarga.

El snapshot revalidado contiene 1.928 citas y 2.291 fotos locales referenciadas
(1.860.382.565 bytes); 173 citas carecen de foto local. Por eso la selección
completa requiere varios ZIP. Estos tamaños no equivalen a memoria residente.
La prueba de recursos se describe en el informe de validación enlazado abajo;
no constituye una medida en Raspberry Pi ni del servidor HA completo.

## Correspondencia con observaciones

| Campo | Regla implementada |
| --- | --- |
| `observation_id` | `obs_gbif_<ID>`; identidad externa conservada aparte |
| `species_id` | Perfil único del visor, validado contra catálogo destino |
| `observed_at` | Día ISO completo coincidente con `original.eventDate`; intervalos o fechas incompletas bloqueados |
| `location.lat/lon` | Coordenadas de la cita; no se sustituyen por EXIF |
| `location.source` | `gbif` |
| `observer.name` / `expertise` | `GBIF` / `unknown` |
| `source.type` / `label` / `url` | `gbif` / `GBIF` / enlace a la cita GBIF |
| `flush_abundance` | **`normal` por decisión expresa del usuario**, registrada como asignación |
| `source_quality` | 0,75 provisional, visible en el diálogo y editable; no es un valor publicado por GBIF |
| `validation_status` / `calibration_use` | `draft` / `review`, incluso si la revisión del visor era aceptada |
| `micro_area_id` | Microárea activa única que contiene el punto; no se crea ni se elige por proximidad |
| `site_context.habitat_notes` | Hábitat literal; no se infieren campos estructurados |
| `altitude` | DEM de la recuperación local; si no está disponible, conserva el DEM válido ya presente en el snapshot |
| `media` | Todas las fotos locales de la cita, originales sin recomprimir, con autoría/licencia por referencia |

Las cantidades originales se preservan, pero no alteran la asignación **Normal**
en la importación. No se generan ausencias ni se aceptan registros que declaren
ausencia. La calidad 0,75 es una decisión provisional de implementación, no un
acuerdo científico nuevo. Antes de incluir en calibración hay que revisar la cita.

Los campos opcionales de procedencia no hacen elegibles los borradores para
reconstrucción o entrenamiento. No se ha modificado el código de esos procesos
para utilizar incertidumbre. El mapa existente puede mostrar borradores y
seguir derivando favorable de abundancia; visibilidad no equivale a validación.

## Preparación automática GIS/DEM y microárea

Antes de confirmar se llama secuencialmente al mismo `observation_preview` de
`mushroom_gis_recovery` que usa el formulario. Guarda hosts, bosque, tendencias
de suelo y hábitat disponibles, fuentes y fecha en `site_context.gis_recovery`,
con `recovery_mode = gbif_import`. Los valores no se mezclan con los campos
`observed_*` de evidencia manual. El DEM recuperado actualiza la altitud.

La ausencia o fallo de datos queda identificado y la cita sigue pendiente de
revisión. El resultado informa cuántas citas tienen datos GIS pendientes; no
inventa hábitat ni resuelve automáticamente contradicciones entre capas.

Se busca contención geométrica entre microáreas y áreas activas, respetando los
huecos del polígono. Sin coincidencias deja `micro_area_id` nulo; si hay varias, elige centro más
cercano e ID estable como desempate. Conserva el resultado en
`external_source.site_assignment`. Se vuelve a comprobar
la asignación justo antes del guardado. La proximidad sólo desempata entre microáreas que contienen el punto.

La preparación se persiste por cita en el lote temporal para poder continuar
sin repetir consultas ya terminadas. La API exige preparar las citas antes de
confirmar. Progreso: preparación GIS/DEM y microárea `i / total`, después guardado
atómico del conjunto y copia secuencial de las fotos.

## Incertidumbre y conservación

`location.precision_m` ya existía. Ahora se ofrece **Incertidumbre de posición
(m)** en el formulario y se conserva al guardar, también al añadir fotos.

| Caso | Valor efectivo / `location.precision_origin` |
| --- | --- |
| Existente sin precisión | 0 / `legacy_default_zero`, al mostrar y guardar; sin reescritura masiva del JSON privado |
| GBIF con radio positivo declarado | Valor original / `declared` |
| GBIF con incertidumbre desconocida | 500 / `assumed_unknown_500m` |
| Corrección manual del radio | Valor introducido / `manual` |

El bloque opcional `external_source` conserva `provider`, `gbif_id`,
`coordinate_uncertainty_m` original (incluido `null`), `uncertainty_assumed`,
`original`, `viewer_review`, snapshot/lote, fecha de importación y valores
asignados. La UI indica cuándo los 500 m son asignados. Cambiar manualmente el
radio no borra el original. Cero de compatibilidad no acredita precisión exacta.

Se retienen identificadores/enlaces de proveedor y dataset, autores originales,
identificador taxonómico y nombres, fecha original, cantidades, hábitat/localidad,
flags, restricciones declaradas, licencia y derechos. La geografía ya presente
en el snapshot queda también como procedencia, incluida su elevación. La autoría
y licencia de cada foto se conservan aparte porque pueden diferir de la cita.

Al cambiar coordenadas, el radio heredado se reinicia a 0 y su origen pasa a
compatibilidad; la evidencia GBIF sigue intacta. Una copia manual conserva la
procedencia pero añade `is_copy` y `copied_from_observation_id`, de modo que no
se apropie de la identidad única de importación.

## Identidad, escritura y permisos

Se detectan IDs GBIF activos y archivados, incluso citas anteriores cuyo enlace
`source.url` ya identifica GBIF. `occurrenceID` y enlaces exactos de proveedor
señalan conflictos entre publicaciones. No se fusiona por proximidad o fecha.

La confirmación vuelve a leer las observaciones bajo el mismo bloqueo que las
ediciones manuales. Un hash de la versión previsualizada impide reemplazar una
cita editada entretanto. Valida el candidato antes de instalar media, mantiene
las observaciones no seleccionadas y usa copia de seguridad y sustitución atómica.
La restauración escribe primero el registro activo y después retira el archivado;
un diario permite resolver un corte entre ambos sin perder el original, con
copia del archivo anterior. Las fotos antiguas no se borran al reemplazar. Un
registro del lote permite reintentar y limpiar únicamente fotos propias no
referenciadas si se cancela tras un fallo. Las fotos se almacenan como
`media/observation-photos/gbif/<sha256>.<ext>` bajo el directorio de datos.

La API `/api/mushrooms/gbif-import` utiliza el contexto autorizado de
mantenimiento (ingress/local o administración) y cabecera propia antes de leer
la subida. No habilita importación para usuarios que sólo visualizan el mapa.

## Código y validación

- Exportador: `local-apps/gbif/code/gbif-export.js`; etiquetas es/ca/en generadas
  desde `mushroom-data/mushroom_labels.json`.
- Contrato/paquetes: `rainmapper_core/mushroom_gbif_import.py`.
- Formulario/procedencia: `rainmapper_core/mushroom_observations.py`,
  `rainmapper-app/app/web_server.py` y `mushroom_profiles_ui.py`.
- Interfaz y API: `rainmapper-app/app/mushroom_gbif_ui.py`,
  `rainmapper-app/app/observation-gbif-import.js`.
- Validación del esquema: `scripts/validate-mushroom-data.py`.
- Pruebas: `tests/test_mushroom_gbif_import.py`,
  `tests/gbif_import_browser_check.mjs`, `tests/gbif_import_fixture_server.py`.
- [Informe local y límites de la evidencia](../../../docs/reports/gbif-import-local-2026-09-25.md).

La aceptación del usuario y cualquier publicación posterior quedan pendientes.
Las confirmaciones automatizadas se realizan en almacenes temporales; en la UI
local persistente la prueba automatizada sólo previsualiza y cancela su propio
lote. El usuario está probando importaciones y modificando su almacén local;
no confundir esos cambios con las fixtures del agente.

## Creación automática de setales por lote (implementada en local)

El usuario autorizó la implementación tras cerrar las reglas del diseño. En el
modal de importación, **Crear áreas y microáreas cuando falten** está inicialmente
desmarcado. Sólo participan nuevas seleccionadas y duplicados con Reemplazar.
Antes de guardar se presenta el plan conjunto: esquema geométrico, nombres
editables de zonas nuevas, áreas ampliadas y asignaciones por observación.
Cambiar selección u opción obliga a rehacer el plan. Previsualizar no crea zonas.

Las citas se procesan por ID GBIF numérico, incorporando cada creación/ampliación
antes de evaluar la siguiente; no depende de la ordenación visual de la tabla.
Dividir la misma selección en lotes distintos puede producir agrupaciones distintas.

- Si una microárea activa contiene el punto, se reutiliza. Si varias lo contienen,
  se elige la de centro más cercano; empate resuelto por ID estable. Esta regla
  de solapamientos se aplica también a la asignación sin creación automática.
- Sin microárea contenedora, se busca un área activa que contenga el punto; entre
  varias, centro más cercano e ID como desempate. Se crea una microárea de **495 m
  de radio**. Si tampoco existe área, se crea una de **500 m de radio inicial**.
- El área, incluso si fue dibujada manualmente, se amplía mediante unión con el
  círculo de 500 m centrado en la nueva cita. No se recorta territorio anterior,
  no se fusionan zonas vecinas y no se amplían microáreas preexistentes.
- Se usa proyección métrica azimutal equidistante centrada en la cita, GDAL/GEOS
  local y polígonos circulares. La aproximación exterior es circunscrita para
  garantizar **al menos 5 m de margen** respecto a la microárea. Se comprueba la
  contención completa tras convertir las geometrías a GeoJSON.
- Centro de círculos originales: coordenadas fundadoras mientras la geometría
  conserve su huella; polígonos manuales o editados: centroide métrico. Se respetan
  huecos, áreas/microáreas archivadas y ausencia de polígonos. No se adivina una
  extensión a partir de un punto representativo.
- Los tamaños son radios, no diámetros. El usuario confirma que los 5 m sirven
  para que la microárea quede dentro del área. La incertidumbre de la observación
  sigue conservada aparte; pertenencia significa contención del punto publicado.

El crecimiento por cadena y los solapamientos son posibles con estas reglas.
Se revisa sólo el lote seleccionado; la auditoría general de citas existentes que
«no encajan» queda para una fase posterior.

### Origen, nombres y datos automáticos

`provenance.creation_source` conserva **manual / gbif / futura fuente**; se muestra
como Origen de creación en las fichas. Las antiguas sin ese dato se interpretan
como manuales sin migración masiva. Una ampliación GBIF no cambia el origen manual.
Se conserva la cita fundadora, centro/radio original, huella geométrica, lote,
snapshot y token de importación; última ampliación tiene su propio registro.
El guardado manual conserva esta procedencia aunque cambie el nombre o la fuente
editable. Las zonas mantienen IDs estables independientes del nombre visible.

Nombre de área propuesto: municipio conservado en el snapshot para las mismas
coordenadas, si está disponible, más sufijo GBIF/ID para distinguir zonas. Ese
municipio procede de contención administrativa, no del núcleo urbano más cercano.
Sin municipio verificado: GBIF/ID. La petición de usar el topónimo más cercano
para microáreas necesita una fuente adicional: no se encontró un nomenclátor local
entre los archivos inspeccionados. Por ahora se propone GBIF/ID editable; no se
presenta la localidad libre del registro como topónimo más cercano verificado.

Las zonas nuevas y áreas ampliadas recuperan GIS/DEM usando la rutina de polígonos
existente; no extrapolan a toda la zona los datos puntuales de la cita. Para cada
microárea nueva se guarda también `derived_context.soilgrids_water`, usando el
resolver canónico sobre **cobertura local**, con `ensure_missing=False`. Si faltan
activos queda contexto pendiente y un contador visible; la importación no descarga
nuevos territorios de SoilGrids. Ampliar sólo el área no recalcula microáreas intactas.
La preparación avanza zona a zona y se guarda para reintentar sin repetir trabajo.
No se lanzan entrenamientos ni precálculos.

### Integridad y recursos

Plan sellado con selección y huella del registro de setales; cambios concurrentes
obligan a revisarlo otra vez. Diario con estado anterior y huella posterior:
primero zonas, después observaciones. Si no se llegaron a guardar las observaciones,
reintento/cancelación revierte únicamente las zonas propias intactas y sin nuevas
referencias. Si se guardaron, conserva las zonas. No sobrescribe ediciones ajenas
para reparar un fallo. Copia anterior en backups; las geometrías temporales se
retiran al completar o cancelar. Importar otra vez reutiliza las zonas existentes.

Mantenimiento manual e importación comparten bloqueo de mutaciones. El motor
geométrico corre una vez por plan en el Python GDAL instalado; usa límites de
100 citas, 4 MiB por contrato geométrico y 60.000 vértices procesados. El plan
persistido evita repetir geometrías en la lista de cambios. Los informes de
preparación se guardan por zona, sin reescribir el plan entero en cada paso.

Implementación: `rainmapper_core/mushroom_gbif_sites.py`, integración en
`mushroom_gbif_import.py`, `mushroom_gbif_ui.py` y `observation-gbif-import.js`.
