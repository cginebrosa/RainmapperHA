# Inventario de espacio del workspace — 18/09/2026

Auditoría de solo lectura de `/Users/carlosginebrosa/Developer/RainmapperHA`.
No se han eliminado archivos, cambiado rutas ni detenido contenedores.
Las cifras siguientes son GB decimales, convertidos desde los bloques medidos
por `du -k`; no son una promesa de espacio físico recuperable en APFS.

## Distribución medida

| Carpeta | GB | Contenido comprobado |
| --- | ---: | --- |
| Workspace completo | 62,40 | Equivale a unos 58,1 GiB |
| `mushroom-map-GIS` | 29,54 | Fuentes y preparación de cartografía |
| `docker-media` | 15,85 | Geografía y resultados del entorno HA local |
| `mushroom-GIS` | 8,44 | Fuentes GIS del laboratorio |
| `docker-data` | 5,34 | Datos locales, observaciones y auditorías |
| `docs` | 2,00 | Incluye 1,92 GB del snapshot GBIF |
| `tmp` | 0,56 | Investigación, pruebas y herramienta de estaciones |
| `.venv` | 0,55 | Entorno Python local |
| `.git` | 0,048 | Base de objetos y metadatos Git |

Las tres carpetas GIS/media suman aproximadamente 53,83 GB, el 86 % del total.
La carpeta `backups` ocupa solo unos 11 MB.

## Qué merece una revisión de limpieza

1. **Posibles copias GIS: 15,63 GB.** Un recorrido de los archivos compara
   `mushroom-GIS` y `mushroom-map-GIS` con las mismas rutas relativas bajo
   `docker-media/rainmapper/geography`. Coinciden tamaño y ruta en 1.432
   archivos del primer árbol (6,82 GB) y 2.149 del segundo (8,81 GB).
   Esta comprobación NO compara contenidos: no son todavía duplicados
   certificados para borrar. Ejemplo: el DEM de Catalunya aparece en ambas
   ubicaciones, con 5.127.260.482 bytes por archivo.
2. **Auditorías y experimentos: 4,49 GB**, dentro de `docker-data/audits`.
   Destacan `mushroom-hydric-ablation-20260905` (1,73 GB) y
   `mushroom-weather-backfill-20260811` (1,43 GB). Hay datos preparados,
   snapshots, CSV y resultados. No se ha certificado que sean prescindibles:
   `scripts/audit-mushroom-dry-spell-selector.py:46` y
   `scripts/audit-mushroom-dry-spell-thresholds.py:32` referencian la primera.
3. **Fuentes nacionales MFE25: 18,79 GB** en `mushroom-map-GIS/mfe25`.
   Son datos forestales de las comunidades autónomas, no caché genérica.
   El manifiesto de adquisición y las carpetas regionales existen; la copia
   publicada bajo `docker-media` contiene el subárbol MFE de Catalunya.
   Archivar fuentes fuera del repo reduciría el tamaño de la carpeta, pero
   moverlas dentro del mismo SSD no liberaría espacio en ese disco.

No sumar estas categorías como ahorro: se solapan y requieren decisiones
sobre conservación, consumidores y reproducción de experimentos.

## Datos que deben preservarse

- Geografía publicada y datos operativos locales. `docker-data/prediction-map/config.json`
  apunta a `/media/rainmapper/geography`, y su `CURRENT.json` selecciona
  `local-20260914` mediante `map-sources-local-20260914.json`.
- Observaciones privadas, imágenes, modelos y registros de revisión.
- Snapshot GBIF y fotografías pendientes de revisión.
- Investigación de suelos y revisiones de estaciones de `tmp`, incluida la
  base SQLite de la herramienta Wunderground; `tmp` no significa desechable.
- Fuentes originales, metadatos y licencias necesarios para reproducir o
  ampliar la geografía, hasta acordar su archivo o consolidación.

`docker inspect` confirma que el contenedor
`rainmapper-local-rainmapper-ha-ui-1` monta `docker-data`, `docker-media/rainmapper`,
`mushroom-GIS` y `tmp` desde este workspace. El worker usa un volumen Docker
externo al árbol del repo. El consumo de ese volumen no está incluido en este
inventario. No se ha accedido a HA real.

## Método y siguiente paso seguro

- `du -k -d 1 .` y desgloses a profundidad 2–4 en las carpetas grandes.
- Recorrido de metadatos: tamaño lógico, bloques asignados y número de enlaces.
- Lectura de configuración, manifiestos y referencias concretas de scripts.
- Inspección de los montajes efectivos de los dos contenedores locales.
- No se encontraron archivos terminados en `.part`, `.partial` o `.download`
  en los dos árboles GIS ni en `docker-data`; esto no demuestra ausencia de
  otras clases de restos temporales.

Antes de retirar copias GIS: comprobar huellas contra los originales y los
manifiestos, identificar y ajustar todos los consumidores, conservar los
archivos únicos y verificar HA local y el laboratorio. Para auditorías:
separar informes pequeños y entradas únicas de los derivados reproducibles.
La limpieza requiere autorización; este informe solo identifica dónde revisar.
