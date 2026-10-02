# DEM de Andorra — contrato local de formato y procedencia

Este directorio contiene la copia local del Model Digital d'Elevacions de
Andorra. Los binarios permanecen ignorados por Git; este documento sí forma
parte del repositorio para que el formato y las decisiones de interpretación
no dependan del código ni de la memoria de una sesión.

## Procedencia

- Nombre oficial: `Model Digital d'Elevacions`.
- Página oficial:
  <https://www.iea.ad/model-digital-d-elevacions>
- Fuente digital declarada: Departament de Medi Ambient del Govern d'Andorra.
- Elaboración: CREAF, Universitat Autònoma de Barcelona.
- Base: mapa topográfico de Andorra de 1995, elaborado por el área de
  cartografía y topografía del Govern d'Andorra.
- Descarga utilizada: versión ArcGIS/TIFF comprimida como `mde_ArcGis.rar`.
- La página consultada no muestra una licencia explícita de redistribución. El
  raster se conserva como dataset GIS local y no debe incorporarse a imágenes,
  releases ni repositorios hasta aclarar sus condiciones de uso.

## Distribución local

```text
dem-andorra/
├── README.md
├── source/
│   └── mde_ArcGis.rar
└── extracted/
    ├── MDE.tif
    ├── MDE.TFW
    ├── MDE.tif.aux.xml
    └── MDE.tif.ovr
```

El RAR y los ficheros extraídos son binarios locales ignorados por Git. No se
debe eliminar ni modificar el original de `source/` durante el procesamiento.

## Formato confirmado

- Modelo: raster continuo de elevación.
- Fichero principal: GeoTIFF `MDE.tif`.
- Dimensiones: `7040 × 5540` celdas.
- Resolución: `5 × 5 m` por celda.
- Tipo de píxel: entero sin signo de 16 bits (`UInt16`).
- Unidad almacenada: **decímetros**.
- Conversión canónica a Rainmapper: `elevation_m = pixel_value / 10.0`.
- Georreferenciación: `MDE.TFW`, con origen `(521402.5, 40097.5)` y tamaño de
  píxel `(5, -5)`.

El TIFF no contiene una declaración CRS embebida. La ficha oficial declara
«Cònica Conforme de Lambert per a la zona III de França i Andorra amb Datum
NTF». Rainmapper la interpreta como `EPSG:27563`, `NTF (Paris) / Lambert Sud
France`. Esta correspondencia también queda validada geométricamente: al
aplicarla, Ordino cae dentro del raster y las cotas resultantes concuerdan con
una medida GPS independiente.

No debe consultarse el TIFF con `-wgs84` sin asignarle antes este CRS mediante
un VRT o un derivado que conserve intacto el fichero original.

## Integridad

Hashes SHA-256 obtenidos el 13 de agosto de 2026:

```text
fb10122c22e3c289a88c3e9c6ccfa54583fd7e780ee93266cfacbfb9025456e9  source/mde_ArcGis.rar
d3c9bca2c4e9f6bab71c596af0656c01887b2badc8d1678304e9888522d16a9b  extracted/MDE.tif
```

## Validación independiente en Ordino

Observación Rainmapper `obs_20260613_0001`:

- coordenadas EXIF: `42.55009167, 1.57271667`;
- altitud GPS del iPhone: `2080 m`;
- valor raster: `20735 dm` = `2073.5 m`;
- diferencia DEM menos GPS: `-6.5 m`.

Otras comprobaciones:

- centro representativo del área Ordino: `20632 dm` = `2063.2 m`;
- centro de la microárea `ordino_cota_2100`: `20642 dm` = `2064.2 m`.

La concordancia de 6,5 m con el GPS y la continuidad de los valores cercanos
son compatibles con un DEM de 5 m. Este control valida la interpretación del
CRS y de los decímetros; no convierte la lectura GPS puntual en la altitud
representativa de toda el área.

## Uso previsto en Rainmapper

Este DEM es la fuente secundaria trazable para puntos de Andorra donde el DEM
ICGC de Catalunya devuelve `NoData`. La altitud utilizada por los contratos ML
debe guardar como mínimo la fuente, el CRS efectivo, la unidad original y el
valor convertido a metros. El fallback no debe deducir cotas del nombre de una
microárea ni introducir excepciones manuales por área.

## Derivado operativo

El fichero que se manifiesta y transporta al worker es:

```text
extracted/rainmapper-dem-andorra-5m-elevation-m-epsg27563.tif
```

Se genera localmente a partir del original sin modificarlo. Incorpora el CRS
`EPSG:27563`, convierte decímetros a metros `Float32`, transforma el fondo
original `32768` en `NoData=-9999`, usa compresión DEFLATE sin pérdida y añade
pirámides internas. Ocupa aproximadamente 30 MB.

SHA-256 del derivado operativo:

```text
10e9a27d97c7e3fb05b9411e8604cdd3674df128d61fbabf6a491a64ed5bbb22
```

El derivado no se incluye en Git ni en la imagen. El coordinador lo declara en
el dataset GIS inmutable y el worker lo descarga una sola vez por hash a su
caché compartida. Catalunya mantiene prioridad; este raster solo se consulta
cuando el DEM catalán no devuelve una cota válida.
