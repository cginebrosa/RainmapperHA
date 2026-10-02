# Geografía de HA real: archivos operativos e históricos

Revisión de sólo lectura del 28/09/2026, solicitada por el usuario. No se borra,
mueve ni escribe nada en HA; no se ejecutan trabajos, builds o reinicios.

## Resultado

No se identifica una gran copia geográfica sobrante que pueda retirarse sin
cambiar contratos o lectores. Hay aproximadamente **4,02 MB de metadatos
históricos candidatos a archivar** y otros **3,57 MB de recibos/inventarios y
documentación técnica** cuya conservación resulta útil. No hay autorización
para retirar ninguno.

La raíz `/media/rainmapper/geography` contiene **3.603 archivos regulares**,
**16.112.419.316 bytes lógicos (16,11 GB)**, sin enlaces simbólicos ni errores de
inventario. Es tamaño de archivos leído por SMB, no una medición de bloques
físicos recuperables en el disco de HA. No se ha auditado aquí el resto de media,
backups, resultados ni el disco del Mac.

## Qué ocupa espacio y debe conservarse

| Grupo | Tamaño lógico | Interpretación |
|---|---:|---|
| Referencias físicas de publicación activa + dataset científico | 15.018,00 MB | 3.512 rutas, todas presentes; forman parte de los contratos activos. |
| MVC50 original, carpeta completa | 885,43 MB | El mantenimiento de mapeos sigue leyendo el shapefile original. |
| SoilGrids `raw-wcs` | 197,17 MB | 55 originales, todos referenciados por el manifiesto SoilGrids. |

Las filas no son una partición estrictamente aditiva: un archivo de 5 bytes del
MVC50 original también aparece entre las referencias activas del mapa.

Los mayores grupos de la geografía son el DEM de Cataluña (5,127 GB), DEM IGN
MDT25 (4,588 GB), Cobertes 2024 (1,717 GB) y MFE25 (1,638 GB). Estos tamaños no
demuestran redundancia ni autorizan recortar cobertura.

El mapa usa el índice MVC50 preparado de 479.780.864 bytes, pero el original
sigue teniendo consumidores: `mushroom_gis_lab.py:124` define la capa original y
`:574` la utiliza al construir candidatos de mapeo. Un índice preparado no
sustituye automáticamente todas las funciones del original. El índice MFE25
también abre su shapefile (`mushroom_map_forest.py:143` y `:152`).

SoilGrids mantiene 1.410 rutas únicas de originales/normalizados en su
manifiesto, todas presentes. `_registered_tile_is_valid` comprueba ambos
archivos (`mushroom_soilgrids.py:809`), y `aggregate_geometry` utiliza esa
validación (`:1276`). Eliminar los originales haría fallar ese lector. La mera
ausencia de esos archivos en el manifiesto del mapa no acredita desuso.

## Duplicación ya evitada y duplicados pequeños

La publicación activa `local-mvc50-20260928` tiene **1.358 alias** que resuelven
a archivos compartidos, con 494.537.831 bytes lógicos asociados. Las antiguas
rutas alternativas no existen como archivos físicos en el inventario. Incluyen
la geología y SoilGrids `existing-retention`: esos nombres en los manifiestos no
representan una segunda copia física. La resolución se implementa en
`mushroom_map_geography_runtime.py:188` y `mushroom_geography_store.py`.

Los catálogos de mapa y auxiliares identifican diez grupos de TIFF pequeños
con contenido repetido. Se ha comprobado su SHA-256 leyendo sólo **265.577 bytes
en 175 archivos**, sin discrepancias: redundancia de contenido de **254.156 bytes**.
Sus rutas forman parte de los contratos; no basta con borrar las copias. No se
propone cambiar su almacenamiento para recuperar aproximadamente 0,25 MB.

## Históricos que se podrían archivar tras acordarlo

| Archivos | Tamaño lógico |
|---|---:|
| `imports/` completo: metadatos y directorios vacíos | 1.990.554 bytes |
| `generations/local-20260914/manifest.json` | 807.785 bytes |
| `map-sources-local-20260914.json` | 1.223.062 bytes |
| **Total histórico candidato** | **4.021.401 bytes** |

`CURRENT.json` apunta a la generación del 28/09, no a la del 14/09. Tres copias
del manifiesto del 14/09 son idénticas mediante SHA-256 completo: una en
`generations/`, otra en `imports/local-20260914/` y otra en
`imports/retired-legacy-metadata/prediction-map/generations/`. Las carpetas de
importación no contienen otra copia de los grandes rasters o vectores.

Además, `retirement-20260918.json` (3.000.631 bytes), `SHA256SUMS` (533.484 bytes)
y los tres XML de capacidades SoilGrids (37.743 bytes) son evidencia/documentación.
No se propone borrarlos: su utilidad y pequeño tamaño favorecen conservarlos.
Las declaraciones activas `geography-sources.json`, `geography-dataset.json`,
`map-config.json`, `territorial-context.json`, `CURRENT.json` y el manifiesto
vigente deben permanecer. No se trata el catálogo auxiliar como basura:
también tiene consumidores de mantenimiento/importación.

## Método y límites

- Origen comprobado con `mount`: `/Volumes/media-1` es el volumen `media` de
  `100.111.77.48`, montado previamente por el usuario. No se montó ni usó SSH.
- Inventario por metadatos, sin recorrer contenido de GIS pesado. SMB comunica
  inodos distintos y `nlink=1`; no se extrapola ahorro físico a partir de ello.
- Se cruzan `CURRENT.json`, manifiesto activo, alias físicos, dataset científico,
  catálogo auxiliar y manifiesto SoilGrids. No se vuelven a hashear los grandes
  archivos: los hashes de sus catálogos son evidencia sellada previa, no una
  verificación íntegra nueva. Los pequeños duplicados sí se verifican de nuevo.
- Dependencias revisadas en el código actual. Los cambios locales de esta tarea
  añaden resolución para el host y no eliminan estos consumidores de HA.
- Evidencia detallada local: `tmp/ha-geography-audit-20260928/inventory.json`,
  `active-comparison.json` y `catalogue-analysis.json`.

Recomendación: **mantener HA como está**. Archivar cuatro MB de históricos sería
una decisión de orden, con impacto despreciable en capacidad. Reducir realmente
los GIS requeriría otra tarea de diseño y validación de lectores/cobertura.
