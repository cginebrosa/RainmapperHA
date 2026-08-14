# Contrato SoilGrids para Biology V4

Estado: **DISEÑO TÉCNICO Y AUDITORÍA PARCIAL; NO IMPLEMENTADO EN HA**.

Este documento define cómo obtener, cachear, validar y persistir el contexto
hidráulico estático de SoilGrids para las microáreas. Complementa la
especificación científica
[`mushroom-ml-biology-v4-implementation-spec-es.md`](mushroom-ml-biology-v4-implementation-spec-es.md).

No autoriza una instalación en HA, una actualización del worker, un modelo V4,
una promoción ni una release.

## 1. Decisión vigente

El SMI inicial usa directamente propiedades hidráulicas numéricas de
SoilGrids. No convierte geología o cobertura vegetal en milímetros y no exige
cambios en:

- `mushroom_reference_catalogs.json`;
- `mushroom_gis_mappings.json`.

Geología y MVC50 continúan siendo información útil para hábitat, hosts,
auditoría y futuras comparaciones, pero no alimentan el depósito hídrico V4
inicial.

Los raster SoilGrids se guardan una sola vez en una caché GIS compartida. Cada
microárea conserva en `known_sites` únicamente el resultado ponderado de
intersectar su polígono con esos raster.

## 2. Qué es estático y qué se calcula diariamente

SoilGrids no proporciona la humedad actual. Proporciona propiedades estáticas
estimadas del suelo:

| Capa | Significado |
| --- | --- |
| `wv0010` | Agua volumétrica retenida a 10 kPa. |
| `wv0033` | Agua volumétrica retenida a 33 kPa. |
| `wv1500` | Agua volumétrica retenida a 1500 kPa, aproximación al punto de marchitez. |

Estas capas existen para seis profundidades:

```text
0-5 cm
5-15 cm
15-30 cm
30-60 cm
60-100 cm
100-200 cm
```

Y para los cuantiles Q0.05, Q0.50 y Q0.95. El producto almacena agua en
unidades equivalentes a `1 mm/m` por unidad raster.

El alta o edición de una microárea calcula y guarda este contexto estático. El
runtime diario combina después esos valores con lluvia IDW, demanda evaporativa
y estado del día anterior. Nunca vuelve a consultar SoilGrids durante una
predicción.

## 3. Auditoría ya realizada

El 2026-08-14 se probó Q0.50 del horizonte 0–5 cm para `wv0010`, `wv0033` y
`wv1500` sobre las 58 microáreas de la copia local de `known_sites`.

Entrada:

```text
known_sites sha256:
ef9363a1ae3c37cdb8ed72109e925ddd7f2e508cb06e4ac35563b9ac530d2ac7

CRS SoilGrids:
+proj=igh +datum=WGS84 +no_defs

resolución:
250 x 250 m

recorte de prueba:
X = 756000 .. 1080500
Y = 4482000 .. 4737000
```

Resultado:

| Medida | Resultado |
| --- | ---: |
| Microáreas auditadas | 58 |
| Cobertura completa en las tres capas | 58 |
| Parcial / sin cobertura | 0 / 0 |
| Agua disponible 33–1500 kPa, solo 0–5 cm | 5,710–9,733 mm |
| Agua disponible 10–1500 kPa, solo 0–5 cm | 9,823–13,388 mm |

La intersección usa toda la superficie de cada polígono y pondera el área de
cada píxel. No usa el centroide. Evidencias:

- `biology-v4-soilgrids-topsoil-audit-2026-08-14.json` contiene valores y
  hashes por microárea;
- `scripts/audit-biology-v4-soilgrids.py` reproduce el cálculo con recortes
  alineados;
- los tres GeoTIFF de prueba permanecieron en `/private/tmp`; no se copiaron a
  HA, M1, Git ni la imagen.

Esta prueba demuestra cobertura espacial del primer horizonte y cuantíl. No
valida todavía las otras profundidades, incertidumbre, balance diario ni SMI.

## 4. Alcance geográfico de la caché

La caché no sigue fronteras administrativas:

- no se crea una copia por microárea;
- no se crea una copia por área;
- no se limita a Catalunya, porque excluiría Puertomingalvo;
- no se define como España, porque Ordino está en Andorra;
- no se descarga el producto global ni España completa sin necesidad.

La unidad de cobertura es una cuadrícula de bloques alineados con el raster
nativo. Propuesta a congelar como `soilgrids_tile_512px_v1`:

```text
pixel:       250 x 250 m
bloque:      512 x 512 píxeles
lado:        128 km
clave:       <tile_x>_<tile_y>
origen:      cuadrícula nativa SoilGrids/Interrupted Goode Homolosine
```

Un bloque se comparte entre todas las microáreas que lo intersectan. Una
geometría nueva descarga solo los bloques ausentes. El tamaño de 512 píxeles es
una decisión de almacenamiento y puede ajustarse antes de implementar; una vez
publicado el `contract_id` no cambia sin migración.

La primera extensión rectangular contenía 1.323.960 píxeles por capa. Los
GeoTIFF comprimidos medían 0,63–0,71 MB cada uno; por eso las 54 capas básicas
de retención para la cobertura actual se estiman en 35–40 MB. Esa cifra no
representa toda España.

## 5. Rutas

Desarrollo local, ignorado por Git:

```text
mushroom-GIS/soilgrids/
```

HA, fuera de `/share` y de los backups ordinarios:

```text
/media/rainmapper/mushroom-GIS/soilgrids/
```

Estructura candidata:

```text
soilgrids/
  manifest.json
  raw-wcs/
    <source_version>/<coverage_id>/<tile_id>.tif
  normalized/
    <source_version>/<coverage_id>/<tile_id>.tif
  staging/
  reports/
```

`raw-wcs` conserva opcionalmente la respuesta exacta para auditoría. Los
ficheros `normalized` incorporan CRS, geotransformación y compresión validados;
son los únicos que consulta el mantenimiento de microáreas. `staging` nunca es
fuente de producción.

Los raster no se empaquetan en la imagen HA, no entran en Git y no se envían al
worker.

## 6. Manifiesto de caché

`manifest.json` es la autoridad de qué bloques son utilizables:

```json
{
  "schema_version": "1.0",
  "contract_id": "soilgrids_tile_512px_v1",
  "source": {
    "source_id": "soilgrids_2_water_retention",
    "source_version": "...",
    "license": "CC-BY-4.0",
    "native_crs_proj4": "+proj=igh +datum=WGS84 +no_defs",
    "pixel_size_m": 250,
    "tile_pixels": 512,
    "service": "WCS",
    "downloaded_at": "..."
  },
  "coverages": {
    "wv0033_0-5cm_Q0.5": {
      "tiles": {
        "<tile_id>": {
          "bbox_native": [0, 0, 0, 0],
          "raw_sha256": "sha256:...",
          "normalized_sha256": "sha256:...",
          "width": 512,
          "height": 512,
          "status": "valid",
          "validated_at": "..."
        }
      }
    }
  }
}
```

No basta con que exista un fichero: solo se usa si aparece como `valid` y su
hash coincide. La actualización del manifiesto y la promoción de ficheros son
atómicas.

## 7. Descarga y ampliación segura

Para una geometría nueva o modificada:

1. transformar el polígono WGS84 al CRS nativo SoilGrids;
2. calcular bloques intersectados, incluyendo el borde exacto;
3. comprobar en el manifiesto las 54 coberturas mínimas;
4. reutilizar todos los bloques válidos existentes;
5. descargar a `staging` únicamente los bloques ausentes;
6. validar cada respuesta antes de normalizarla;
7. promover ficheros completos y actualizar el manifiesto atómicamente;
8. calcular el agregado de la microárea;
9. actualizar `known_sites` mediante copia candidata, validación y backup.

Una ampliación concurrente usa lock y deduplicación por
`source_version + coverage_id + tile_id`. Dos altas cercanas no pueden descargar
el mismo bloque dos veces ni escribir simultáneamente el manifiesto.

La descarga WCS debe verificar:

- código HTTP y tipo de contenido;
- que la respuesta sea GeoTIFF y no XML/HTML de error;
- dimensiones y geotransformación esperadas;
- alineación exacta a la cuadrícula nativa;
- rango y tipo de dato;
- ausencia de truncado;
- SHA-256;
- cobertura válida del bloque solicitado.

El WCS probado devuelve GeoTIFF con geotransformación pero sin CRS embebido. La
normalización debe asignar únicamente el CRS nativo conocido después de validar
la consulta y el grid; nunca inferir otro CRS desde las coordenadas.

Un fallo no reemplaza un bloque anterior válido ni deja un manifiesto parcial.

## 8. Alta y edición en la UI

El guardado de una microárea coordina tres contextos independientes:

```text
geometría válida
  ├── altitud DEM
  ├── SoilGrids estático
  └── resto de metadatos de la microárea
```

Secuencia:

1. validar y normalizar la geometría candidata;
2. calcular `geometry_hash`;
3. resolver altitud con el contrato DEM vigente;
4. asegurar bloques SoilGrids y calcular agregados;
5. validar ambos bloques derivados por separado;
6. escribir una copia candidata de `known_sites`;
7. releer y validar 58/58 o el nuevo total;
8. crear backup y hacer sustitución atómica.

Si la caché local cubre la geometría, no hay red. Si faltan bloques y SoilGrids
no responde, la UI puede guardar la geometría con
`soilgrids_water_context.status=pending` y mostrar el motivo, pero:

- no inventa ceros;
- no conserva como vigente el contexto de la geometría anterior;
- no habilita features SMI para esa microárea;
- programa o permite reintentar la resolución;
- un fallo SoilGrids no borra una altitud válida.

Cambiar nombre, descripción, aliases u observaciones no recalcula SoilGrids.
Cambiar el polígono sí lo invalida.

## 9. Bloque persistido en `known_sites`

Cada microárea guarda:

```json
{
  "derived_context": {
    "soilgrids_water": {
      "contract_id": "microarea_soilgrids_water_context_v1",
      "geometry_hash": "sha256:...",
      "generated_at": "...",
      "status": "complete|partial|pending|stale|no_coverage|error",
      "source": {
        "source_id": "soilgrids_2_water_retention",
        "source_version": "...",
        "cache_contract_id": "soilgrids_tile_512px_v1",
        "manifest_hash": "sha256:...",
        "tile_ids": [],
        "asset_hashes": []
      },
      "coverage_fraction": 1.0,
      "depths": [
        {
          "top_cm": 0,
          "bottom_cm": 5,
          "valid_pixel_count": 13,
          "area_weighted": {
            "Q0.05": {
              "wv0010_mm_per_m": 0,
              "wv0033_mm_per_m": 0,
              "wv1500_mm_per_m": 0
            },
            "Q0.50": {
              "wv0010_mm_per_m": 0,
              "wv0033_mm_per_m": 0,
              "wv1500_mm_per_m": 0
            },
            "Q0.95": {
              "wv0010_mm_per_m": 0,
              "wv0033_mm_per_m": 0,
              "wv1500_mm_per_m": 0
            }
          }
        }
      ],
      "quality": {
        "spatial_min": {},
        "spatial_max": {},
        "exclusion_reasons": []
      }
    }
  }
}
```

Se persisten los valores originales por tensión, profundidad y cuantíl. No se
guarda solamente una resta ya interpretada. Esto permite modificar el cálculo
del SMI sin repetir el cruce GIS.

La diferencia de cuantiles marginales no es automáticamente un cuantíl de la
diferencia. Cualquier propagación de incertidumbre tendrá contrato propio.

## 10. Invalidación

El bloque se recalcula cuando cambia cualquiera de:

- `geometry_hash`;
- `microarea_soilgrids_water_context_v1`;
- versión SoilGrids;
- contrato de caché o manifiesto relevante;
- hash de un bloque usado;
- método de agregación espacial.

No se repite el cruce al cambiar:

- nombre o descripción;
- aliases;
- perfiles o especies;
- observaciones;
- contrato del balance diario.

Si cambia únicamente la fórmula SMI, se recalcula la serie diaria desde los
valores SoilGrids ya persistidos. No se redescargan raster ni se reabre el GIS.

## 11. Worker y reconstrucciones

HA mantiene la caché GIS y `known_sites`. El worker recibe en el bundle:

- `known_sites` con el bloque SoilGrids agregado;
- contrato de balance hídrico;
- meteorología necesaria;
- hashes de entrada.

El worker no monta `/media`, no descarga SoilGrids y no interpreta geología.
Debe rechazar una tarea si el manifiesto declara features SMI pero la microárea
carece de contexto completo o tiene un `geometry_hash` distinto.

La reconstrucción registra en su manifiesto:

```text
soilgrids_source_version
soilgrids_context_contract_id
soilgrids_context_hash
water_balance_contract_id
microareas_complete/partial/missing
```

## 12. Cálculo hídrico posterior

El contexto SoilGrids no decide por sí solo el algoritmo diario. Antes de
implementar el SMI deben congelarse por comparación:

- capacidad de campo basada en 10 o 33 kPa;
- espesores 0–30, 0–60 y 0–100 cm como candidatos iniciales;
- tratamiento de fragmentos gruesos si se incorpora `cfvo`;
- infiltración, desbordamiento y drenaje;
- evapotranspiración real según fracción de agua disponible;
- calentamiento 90/180/365 días;
- propagación de Q0.05/Q0.50/Q0.95.

No hace falta elegir una profundidad desde la geología o vegetación. V4 puede
materializar varios espesores físicos sobre las mismas muestras y dejar que el
benchmark determine cuál aporta señal, manteniendo cada variante identificada.

## 13. Pruebas obligatorias

### Caché y red

- una microárea dentro de caché no realiza llamadas WCS;
- dos microáreas cercanas reutilizan bloques;
- una microárea exterior descarga solo bloques ausentes;
- una descarga repetida es idempotente;
- HTML/XML de error no se acepta como GeoTIFF;
- un fallo deja intactos bloques y manifiesto anteriores;
- locks impiden descargas/promociones duplicadas;
- hashes incorrectos invalidan el bloque.

### Geometría y raster

- se usa el polígono completo, no centroide;
- CRS y ejes se transforman explícitamente;
- los píxeles de borde se ponderan por superficie intersectada;
- `NoData` no se convierte en cero;
- una geometría modificada invalida el contexto anterior;
- nombre o descripción modificados no lo invalidan;
- 58/58 microáreas reproducen la cobertura del snapshot 0–5 cm Q0.50.

### Persistencia

- el bloque candidato valida antes de sustituir `known_sites`;
- existe backup recuperable;
- `geometry_hash`, tile IDs y hashes pertenecen a la misma generación;
- `pending/error` no se interpreta como suelo seco;
- altitud válida sobrevive a un fallo SoilGrids y viceversa.

### ML

- fuente, cobertura, cuantiles, hashes, pixel count y estado quedan en
  `quality`/`metadata`, nunca en `X`;
- solo features hídricas derivadas y explícitamente activadas entran en `X`;
- cambiar filas elegibles invalida una comparación emparejada;
- ningún modelo operativo se entrena o promociona durante esta implementación.

## 14. Orden de implementación local

1. Completar la auditoría de cinco profundidades restantes y Q0.05/Q0.95.
2. Congelar identificadores WCS, unidades, origen del grid y contrato de tiles.
3. Implementar downloader a staging, normalización, validación y manifiesto.
4. Descargar la caché mínima para las microáreas actuales y verificar hashes.
5. Implementar agregador por polígono y schema `known_sites`.
6. Materializar los 58 contextos en una copia local candidata y validar.
7. Integrar alta/edición de microárea y estados/reintentos en la UI local.
8. Incluir el bloque agregado en snapshot/bundle del worker.
9. Implementar balance climático y variantes SMI con cierre de masa.
10. Ejecutar benchmarks V4 emparejados; no entrenar candidato operativo.

Solo después de cerrar y validar estos pasos podrá prepararse una actualización
coordinada HA/worker, y únicamente con autorización explícita.

## 15. Trabajo explícitamente no realizado

- no se ha modificado `known_sites` real ni local;
- no se ha creado la caché operativa bajo `/media`;
- no se ha cambiado la UI;
- no se ha cambiado el worker;
- no se ha modificado reference catalog ni GIS mappings;
- no se ha implementado el SMI diario;
- no se ha entrenado o promovido V4;
- no se ha construido ni publicado una release.
