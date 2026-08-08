# Mantenimiento de fotos de observaciones

## Contrato de imagen

La carga normal de Rainmapper aplica el mismo contrato implementado por
`save_observation_image_media()`:

- JPEG con calidad 86 y optimización;
- lado máximo de 1600 píxeles, conservando proporción;
- orientación EXIF aplicada antes del redimensionado;
- metadatos EXIF conservados cuando Pillow puede leerlos;
- filtro Lanczos.

El script `scripts/resize-mushroom-observation-photos.py` permite preparar el
lote en una máquina externa, aplicarlo mediante reemplazos atómicos y verificar
hashes, referencias y metadatos. Nunca debe ejecutarse a la vez que el runner ni
mientras se editan observaciones.

## Pasada real del 2026-08-08

Fuente autoritativa:
`/share/rainmapper/mushroom-data/media/observation-photos`, montada en el M1 como
`/Volumes/share/rainmapper/mushroom-data/media/observation-photos` mediante SMB y
Tailscale.

Inventario inicial:

- 422 JPEG y 986.224.750 bytes reales;
- 368 rutas distintas en observaciones activas y 54 adicionales únicamente en
  observaciones archivadas;
- las 422 estaban referenciadas y no faltaba ninguna;
- 210 candidatas: 209 superaban 1600 píxeles y una adicional superaba 1 MiB;
- lote candidato: 894.558.314 bytes.

La conversión se hizo íntegramente en el M1. Las 210 salidas ocuparon
107.831.378 bytes, mantuvieron EXIF, se pudieron decodificar y quedaron con un
lado máximo de 1600 píxeles. La sustitución actualizó 276 enlaces de media porque
algunas fotografías están compartidas por varias observaciones.

Resultado verificado:

- 422 archivos y 422 rutas referenciadas entre activas y archivadas;
- cero rutas ausentes, archivos sin referencia o temporales;
- 210 hashes remotos iguales a las salidas validadas;
- 199.497.814 bytes finales;
- ahorro: 786.726.936 bytes, 750,3 MiB o 87,95 % del lote convertido.

La herramienta quedó cubierta por cuatro pruebas específicas y el smoke
completo del repositorio pasó con 494 tests el mismo día.

## Copia de recuperación e informes

Mientras no se valide visualmente una muestra desde HA, conservar:

- `~/Desktop/Fotos Bolets/originales a reducir/`: los 210 originales, con su
  estructura anual;
- `~/Desktop/Fotos Bolets/reducidas para HA/`: las 210 salidas aplicadas;
- `~/Desktop/Fotos Bolets/informe reduccion 2026-08-08/manifest.json`: hashes,
  dimensiones, EXIF y tamaños antes/después;
- `apply-report.json` y `verification-report.json`: resultado de aplicación y
  auditoría final;
- `json originales/`: copias exactas de las observaciones activas y archivadas
  antes de actualizar `size_bytes`, `resized`, `content_type` y
  `exif_preserved`.

Para una restauración total se deben copiar los originales sobre
`media/observation-photos/` conservando los años y restaurar después los dos JSON
de `json originales/`. La aplicación y la restauración no deben coincidir con un
runner ni con ediciones desde la UI.

## Secuencia reutilizable

1. Auditar dimensiones, referencias activas y archivadas sin modificar datos.
2. Copiar solo las candidatas a almacenamiento local y conservar hashes.
3. Ejecutar `stage` hacia una carpeta vacía.
4. Revisar el manifiesto y el ahorro antes de escribir en HA.
5. Ejecutar `apply`; primero valida todos los hashes originales, guarda los JSON
   y luego reemplaza cada imagen mediante un temporal verificado.
6. Ejecutar `verify` y exigir `ok: true` antes de considerar terminada la pasada.

La selección inicial por tamaño es una ayuda para detectar importaciones que no
pasaron por la UI, no un requisito permanente: una foto ya normalizada puede
superar ligeramente 1 MiB si contiene mucho detalle. La conformidad final se
determina por formato, dimensiones y por el hash del resultado producido con el
contrato anterior.
