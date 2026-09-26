# Validación local de exportación/importación GBIF — 25/09/2026

**Cierre posterior:** incluido en [HA 0.2.324 publicada el 26/09](release-ha-0.2.324-2026-09-26.md). El resto acredita las comprobaciones locales en las fechas indicadas.

**Disponible en HA local y visor local; pendiente de aceptación del usuario.**
No se ha publicado una release, accedido por SSH ni actualizado HA real. El usuario
confirma HA 0.2.323 instalada; esa instalación no se ha inspeccionado en esta tarea.

## Ampliación posterior: creación de setales y SoilGrids

Petición implementada **sólo en local** tras cerrar el diseño con el usuario.
Plan conjunto por lote seleccionado y orden estable GBIF: reutilizar microárea;
si falta, crear radio 495 m y área inicial 500 m o ampliar área contenedora mediante
unión. También amplía áreas manuales por autorización expresa. Coincidencias:
centro más cercano entre contenedoras, ID estable para empate. No fusiona zonas.

Contención completa y margen de 5 m comprobados en geometría métrica GDAL/GEOS.
Polígono exterior circunscrito para no perder margen entre vértices. La incertidumbre
permanece en cada observación. Plan revisable, nombres nuevos editables, progreso
por zona, GIS/DEM de polígonos y SoilGrids por microárea desde cobertura local.
SoilGrids ausente queda pendiente: no se descargan territorios durante la importación.

Origen manual/GBIF/futura fuente conservado en `provenance.creation_source`, visible
en mantenimiento. Una ampliación mantiene el origen previo. Centro fundador, radio,
huella de geometría, cita/lote/snapshot y token persistidos; el formulario manual
mantiene el bloque. Municipio del snapshot más sufijo GBIF para áreas; microáreas
con nombre provisional editable hasta disponer de fuente de topónimos cercanos.

Diario de dos archivos y respaldo: rollback sólo si no se guardaron observaciones,
las zonas propias siguen intactas y no tienen referencias ajenas. Reintentos tras
escritura de observaciones conservan zonas; previsualizar/cancelar no genera altas.
Geometrías del plan almacenadas una sola vez; preparación GIS/DEM/SoilGrids por zona.

Validación de esta ampliación:

- Smoke **1.810 pruebas, 52 skips, OK**, 84,401 s. La primera pasada fue bloqueada
  por el sandbox en seis servidores HTTP de fixtures; repetida con permisos, OK.
  Log `/private/tmp/gbif-sites-smoke-final.log`.
- Tras deduplicar geometrías e incorporar SoilGrids: **40 pruebas dirigidas, OK**,
  7,490 s, `/private/tmp/gbif-sites-soil-directed.log`. Incluyen crecimiento/reutilización,
  orden estable, solapamientos, huecos, zonas archivadas, cambios concurrentes,
  rollback, caída después de guardar observaciones, nombres y conservación del origen.
- Navegador ampliado: **18 comprobaciones, OK**, evidencia local
  `tmp/gbif-sites-20260925/final-browser-result.json` y capturas. Importación temporal con creación persistente de zonas,
  edición de nombres de área/microárea sin perder la asociación por ID y procedencia; en HA local privado sólo plan y cancelación.
- Integración GIS/DEM real dentro de HA local con almacén temporal y una cita GBIF;
  creación de área/microárea y observación Borrador/Revisar. Evidencia final en
  `tmp/gbif-sites-20260925/container-check.json`: SoilGrids **complete**, DEM
  733,45 m y GIS disponibles; hábitat no disponible, conservado como hueco.
- Imagen reconstruida/recreada: **228 archivos efectivos iguales**, huella
  `380257648bc9c769f1d4cf977bf5c4542d8cefb6eb096e2b6ccb59dcf6f6e5d6`.
- Ensayo geométrico sintético de 100 citas separadas: 100 áreas + 100 microáreas,
  plan 2.306.950 bytes, respuesta UI 2.104.880 bytes, 0,895 s en Mac. No mide GIS/DEM,
  SoilGrids, servidor completo ni RPi. Cotas: 100 citas, 4 MiB de contrato geométrico,
  60.000 vértices procesados; no se elevan límites para compensar duplicación.

Auditoría final frente a la línea base de esta ampliación: worker, configuración
de coordinadores/credenciales, observaciones privadas repo/local y política de
suspensiones conservan sus huellas. Las confirmaciones automatizadas escriben
sólo en almacenes temporales. Sin SSH, publicación ni trabajos de modelos.

Las secciones siguientes conservan la validación de la etapa previa del importador;
no confundir sus huellas o medidas con las de esta ampliación.

## Resultado funcional

El visor exporta selección filtrada completa en ZIP con JSON y fotos. Diferencia
origen y destino, muestra sus nombres y propone la carpeta de la página como
referencia copiable. Recuerda permisos de carpeta concedidos por el usuario. El
selector nativo permite cambiar el nombre propuesto o elegir un ZIP existente.
En éste se revisan duplicados por GBIF ID: Ignorar / Reemplazar; las citas ajenas
al lote y sus fotos se conservan. Se valida antes de abrir la escritura.

La importación permite seleccionar nuevas y Mantener / Reemplazar duplicados.
Reemplazar sustituye datos/fotos, conserva el ID de Rainmapper y vuelve a Borrador /
Revisar antes de usar. También restaura archivadas, según decisión del usuario.
Mantener no cambia la observación; conflictos ambiguos o cambios concurrentes no
se sobrescriben. La restauración dispone de diario para reintentos y respaldo.

Altas y reemplazos GBIF: Normal, Borrador / Revisar antes de usar, observador/origen
GBIF, calidad provisional 0,75. Incertidumbre declarada o 500 m asignados con original
conservado; edición, duplicación y adición de fotos mantienen procedencia. Las
observaciones antiguas sin radio muestran 0 sin reescritura masiva. Incertidumbre
queda alineada en Ubicación. Varias fotos siguen vinculadas a una única cita.

Al aceptar, se recuperan GIS/DEM y la microárea activa que contenga el punto.
Los campos cartográficos permanecen separados de los observados; no se inventan
valores ausentes. Si hay varias microáreas, se conserva la ambigüedad para revisión.
Progreso actual/total por cita, seguido de guardado. Cada preparación se persiste
en un pequeño archivo por cita, sin reescribir el lote completo.

El modal mantiene aceptar/rechazar/cerrar visibles en el pie. Sólo la tabla tiene
desplazamiento; ayuda larga plegada y cabeceras con la misma alineación y espaciado
que los valores. Selección y fotos centradas.

Contrato y límites: [documento GBIF](../../local-apps/gbif/docs/gbif-rainmapper-export-import-design.md).

## Comprobaciones realizadas

- Smoke con duplicados y recuperación GIS/DEM: **1.800 pruebas, 52 skips, OK**,
  73,604 s. Log `/private/tmp/rainmapper-gbif-auto-smoke.log`. Después se ajustaron
  el pie/alineación del modal y la persistencia incremental de preparación.
- Pruebas dirigidas tras persistencia incremental: **40 pruebas, OK**, 1,711 s,
  `/private/tmp/gbif-final-directed.log`. Incluyen importador y recuperación GIS,
  archivo/restauración/reintento, cambios concurrentes, microáreas con huecos,
  solapadas o archivadas, fallo de GIS y conservación de informes.
- Navegador: `node tests/gbif_import_browser_check.mjs --local-preview`, **OK**.
  Evidencia `tmp/gbif-duplicates-20260925/final-browser-result.json` y capturas
  `final-browser-*.png` (locales, no versionadas). ZIP real,
  importación HTTP selectiva, SHA de fotos, borradores, duplicados/reemplazo,
  preparación GIS y progreso, combinación de ZIP y cancelación sin escritura.
  Las confirmaciones escriben exclusivamente en un almacén temporal con GIS fixture.
  En HA local persistente sólo se previsualiza/cancela el lote de prueba; se comprueba
  incertidumbre y pie visible con 40 filas a 1280×720 y 390×844. Las 40 filas del
  ensayo visual se clonan en el DOM; no equivalen a importar 40 registros privados.
- Selector nativo sustituido por handle controlado en automatización. La llamada,
  nombre, cancelación y contenido se verifican; la interacción con el diálogo del
  sistema corresponde a la prueba manual del usuario.
- Imagen `rainmapperha:local-ha-ui` reconstruida y servicio HA recreado con
  `--no-deps`. Paridad final de **227 archivos efectivos sin diferencias**:
  `54f75c1de952c823f7a174d7416ee8f6285fef80241ba960b0cdb42f8e4994b1`.
- Integración dentro de la imagen definitiva: preparación con GIS/DEM local real
  e importación en almacén temporal; geometría de microárea de prueba. Coordenadas
  públicas de GBIF 5901832750: hosts, bosque y suelo disponibles, DEM 733,45 m,
  hábitat no disponible. Conserva ese hueco y estado Borrador/Revisar. Evidencia
  `tmp/gbif-duplicates-20260925/auto-check.json`; no modifica citas privadas.

## Ensayo inicial de transporte y límites de la medida

Se creó un ZIP de **125.875.871 bytes** con 9 citas y 55 fotos reales del snapshot,
próximo a la cota de 128 MiB (134.217.728 bytes). Se recibió, previsualizó y confirmó
mediante el mismo importador en un almacén temporal dentro de la imagen local HA.
Se comprobaron todos los hashes y los estados de las nueve altas.

| Medida del proceso de prueba | Resultado |
| --- | ---: |
| Pico RSS inicial | 27.860 KiB |
| Pico RSS final | 30.352 KiB |
| Aumento del pico | 2.492 KiB |
| Tiempo | 0,871 s |
| JSON de las nueve altas | 104.570 bytes |

Evidencia: `tmp/gbif-local-20260925/container-check.json`. La prueba usa un proceso
Python aislado y catálogo inicial vacío dentro del contenedor; **no mide el
servidor HTTP completo, un catálogo de 10.000 observaciones ni una Raspberry Pi**.
Esta medida es anterior a la incorporación de la preparación GIS/DEM: no acredita
su consumo ni duración. El lote se generó mediante un script; el ZIP del exportador
se comprueba aparte en navegador.

## Protección de estado y pendientes

Auditoría final: mismo ID, imagen, arranque y hashes de configuración/credenciales
del worker; mismos hashes de observaciones repo/local y política/suspensiones que
la línea base de esta revisión (`tmp/gbif-duplicates-20260925/{before,after}.json`).
El usuario realizó sus propias pruebas de importación/borrado durante la sesión;
no confundirlas con las confirmaciones automatizadas, que usan datos temporales.
No hubo entrenamiento, precálculo ni cambio de destino del worker.

Se mantienen fuera de commit las observaciones privadas preexistentes del repo y
el JSON no versionado de la raíz. Documentación de cierre revisada y actualizada;
código y documentación siguen sin commit/push. Falta aceptación manual local antes
de publicar o instalar en HA real. Una cita anterior sólo se enriquecerá si el
usuario la reimporta con Reemplazar o usa la recuperación del formulario.
