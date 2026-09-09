# Rainmapper — GIS, DEM y suelo para el corredor Quérigut–Font-Romeu

**Estado:** diseño adaptado al repositorio actual

**Revisado:** 9 de septiembre de 2026

**Ámbito inicial:** corredor Quérigut–Formiguères–Les Angles–Font-Romeu, entre Ariège (D09) y Pyrénées-Orientales (D66).

## 1. Decisión

La ampliación francesa debe reutilizar el modelo existente de áreas, microáreas y contexto GIS. No se creará un subsistema francés paralelo.

La primera entrega utilizará:

1. **IGN RGE ALTI a 5 m** como DEM de trabajo.
2. **SoilGrids**, mediante la caché global que Rainmapper ya materializa por geometría.
3. **BD Forêt V2 de Ariège (D09) y Pyrénées-Orientales (D66)** como primera capa vectorial francesa.

Quedan para una segunda decisión:

- OCSID D66, porque el contrato operativo actual no tiene un campo `landcover_type`.
- BD Charm-50, porque la litología existe en los catálogos, pero está aparcada en el perfil V0.
- MNT LiDAR HD de 50 cm, como posible mejora local y no como requisito inicial.

## 2. Encaje con el Rainmapper actual

### 2.1 Áreas y microáreas

`rainmapper_core/mushroom_known_sites.py` ya permite:

- `administrative_location.country` en las áreas;
- geometrías GeoJSON `Polygon` o `MultiPolygon`;
- ubicación representativa, altitud, topografía y contexto ecológico en las microáreas.

Por tanto, añadir Francia requiere datos y cobertura GIS/meteorológica, no un cambio del esquema territorial.

Las áreas `font_romeu` y `querigut` ya existen en el catálogo local, con
geometrías de 1896,6961 ha y 1465,8247 ha respectivamente. La copia local del
9 de septiembre de 2026 contiene una microárea en Font-Romeu
(`font_romeu_font_romeu_medio`) y dos en Quérigut
(`querigut_querigut_medio` y `querigut_querigut_bajo`). Los campos
administrativos, incluido `country`, siguen vacíos. Esto no bloquea el DEM,
pero debe completarse `country = France` antes de considerar cerrada el alta
territorial.

La misma copia contiene dos observaciones válidas e incluidas de
`boletus_edulis`, ambas del 3 de septiembre de 2026 y asociadas a las dos
microáreas de Quérigut. Font-Romeu todavía no tiene observaciones.

La frontera no debe modificar el predictor. Los identificadores de área y microárea seguirán siendo identificadores internos estables; el país se registrará como metadato administrativo.

### 2.2 DEM actual

`rainmapper_core/mushroom_gis_lab.py` tiene una cadena fija:

```text
DEM Catalunya 5 m
→ DEM Andorra 5 m
→ IGN España MDT25 MTN50-592
→ IGN Francia RGE ALTI 5 m
```

El muestreo usa `gdallocationinfo -wgs84`, por lo que un raster puede conservar su CRS nativo si está correctamente georreferenciado. La reconstrucción de una microárea toma una rejilla 5 × 5 dentro del polígono y deriva altitud, pendiente y orientación.

La integración francesa debe añadir el DEM francés a esa cadena o crear un mosaico de trabajo coherente. No debe cambiarse el CRS general de Rainmapper.

### 2.3 Capas vectoriales actuales

Las consultas vectoriales transforman cada punto desde WGS84 a **EPSG:25831** antes de ejecutar `ogrinfo -spat`. Las capas francesas deben:

- preprocessarse a EPSG:25831; o
- declarar su CRS y hacer una transformación por capa.

Para la primera entrega se prefiere preprocesarlas a EPSG:25831: es más sencillo y conserva el comportamiento actual.

Los únicos resultados ecológicos operativos son:

```text
host_ids
forest_type_ids
soil_tendency_ids
habitat_feature_ids
```

No se añadirá `landcover_type` ni se activará litología sólo porque exista una fuente francesa.

### 2.4 SoilGrids actual

`rainmapper_core/mushroom_soilgrids.py` ya implementa una caché mundial basada en geometría:

```text
geometría WGS84 de microárea
→ transformación al CRS nativo de SoilGrids
→ cálculo de teselas necesarias
→ descarga WCS y validación
→ contexto estático agregado
```

El runtime de predicción no consulta SoilGrids. La descarga ocurre al crear o cambiar una microárea, o mediante una materialización explícita. Francia no necesita otro dataset ni otra arquitectura de suelo.

### 2.5 Transporte al worker

`rainmapper_core/mushroom_rebuild_snapshot.py::gis_dataset_files()` enumera de
forma explícita el Shapefile MVC50, el GeoPackage geológico y los DEM, incluido
el nuevo RGE ALTI francés cuando existe. No incluye automáticamente una tercera
capa de `vector_layers()`.

Al añadir BD Forêt habrá que ampliar nuevamente este inventario:

- incluir todos los sidecars necesarios del Shapefile francés;
- comprobar tamaño y hash antes de crear el snapshot;
- probar la descarga transaccional del worker;
- verificar dentro del worker que los ficheros efectivos coinciden con el snapshot.

El recorte de BD Forêt al ámbito piloto debe hacerse antes del transporte para no cargar HA ni el worker con ambos departamentos completos sin necesidad.

## 3. Fuentes y prioridad

| Necesidad | Fuente | Uso en Rainmapper | Fase |
|---|---|---|---|
| Altitud, pendiente y orientación | IGN RGE ALTI 5 m | Nuevo fallback o mosaico DEM francés | 1 |
| Retención de agua del suelo | SoilGrids 2.0, 250 m | Caché existente por microárea | 1 |
| Bosque y especie/formación dominante | BD Forêt V2 D09 + D66 | Mapping a hosts, forest types y hábitats actuales | 1 |
| Cobertura/uso general | OCSID D66 2021 | Sólo si se define un mapping útil al contrato actual | 2 |
| Litología | BRGM BD Charm-50 D66 | Sólo tras decidir activar litología en el modelo | 2 |
| Relieve de muy alta resolución | IGN MNT LiDAR HD | Mejora puntual donde haya teselas disponibles | Opcional |

## 4. DEM: RGE ALTI 5 m

Fuente oficial:

https://www.data.gouv.fr/datasets/rge-alti-r

RGE ALTI es la opción inicial porque ofrece una resolución de 5 m compatible con el DEM principal actual. Evita descargar y reducir teselas LiDAR de 50 cm sin una necesidad demostrada.

La descarga se ha verificado contra el WMS-R público de la Géoplateforme, sin
cuenta ni clave API:

```text
endpoint: https://data.geopf.fr/wms-r/wms
layer: RGEALTI-MNT_PYR-ZIP_FXX_LAMB93_WMS
version: WMS 1.3.0
format: image/geotiff
crs: EPSG:2154
```

El servicio entrega valores de elevación `Float32`, no una imagen coloreada.

### Preparación

1. Tomar la envolvente conjunta de las áreas `font_romeu` y `querigut`.
2. Ampliarla 10 km y alinearla a la cuadrícula de 5 m.
3. Descargar cuatro recortes por el límite de dimensiones del WMS.
4. Conservar esos recortes en `source/`, fuera del contrato operativo mínimo.
5. Generar un GeoTIFF único, teselado y comprimido, con nodata explícito.
6. Validar CRS, resolución, extensión, nodata, continuidad y elevaciones.
7. Usar la ruta estable:

```text
mushroom-GIS/dem-france-rge-alti-5m/extracted/rainmapper-dem-france-rge-alti-5m.tif
```

El raster construido el 9 de septiembre de 2026 tiene 6579 × 8368 píxeles,
ocupa 83.072.534 bytes (79,2 MiB), presenta cobertura válida completa y tiene
SHA-256
`3e86d6c2ee4e3677dd895de369045b8f49c02a23902771692177b7a60256860f`.
La definición de coordenadas entregada por el WMS se normalizó a la definición
oficial EPSG:2154. El checksum GDAL de la banda permaneció en 63498 antes y
después de esa corrección de metadatos.
La procedencia y los hashes de las cuatro piezas están en el README del dataset.

### Integración

Añadir un `source_id` inequívoco, por ejemplo:

```text
dem_france_rge_alti_5m
```

La reconstrucción conserva ese `source_id` en la procedencia de la altitud. El
DEM francés se añade después de Catalunya, Andorra y MTN50-592, de modo que
rellena Francia sin cambiar la fuente seleccionada en las zonas ya cubiertas.

### Validación

Resultados reales del raster y del código operativo:

| Área | Centroide | Rejilla interior | Altitud de la rejilla |
|---|---:|---:|---:|
| `font_romeu` | 1986,80 m | 8 muestras | 1871,7–2131,9 m; media 2032,2 m |
| `querigut` | 1764,26 m | 5 muestras | 1522,6–1865,7 m; media 1653,3 m |

Todas estas lecturas conservan `source_id = dem_france_rge_alti_5m`. El
polígono irregular de Quérigut no forma en la rejilla de área una cruz completa
de vecinos y por eso el informe de área no deriva pendiente. Esto no se corrige
inventando muestras: se comprobará pendiente y orientación sobre las geometrías
reales de sus microáreas.

La ejecución dentro de HA local sobre las tres microáreas reales produjo:

| Microárea | Muestras | Altitud mínima | Altitud máxima | Altitud media |
|---|---:|---:|---:|---:|
| `querigut_querigut_medio` | 8 | 1642,3 m | 1780,7 m | 1708,7 m |
| `querigut_querigut_bajo` | 8 | 1550,5 m | 1689,0 m | 1629,2 m |
| `font_romeu_font_romeu_medio` | 8 | 2007,3 m | 2119,2 m | 2077,2 m |

Las 24 muestras utilizaron el DEM francés. Estos valores se calcularon en modo
lectura: el contexto persistido debe actualizarse mediante la revisión GIS/DEM
de la interfaz, no sobrescribirse silenciosamente.

- varios puntos conocidos deben devolver altitud;
- los puntos fuera de Francia deben conservar su fuente anterior;
- nodata no puede interpretarse como elevación válida;
- la rejilla 5 × 5 debe producir altitud mínima, máxima y media;
- pendiente y orientación deben resultar plausibles en una microárea montañosa;
- debe comprobarse la diferencia entre altitud declarada y DEM, sin sobrescribirla silenciosamente.

## 5. SoilGrids

Fuentes oficiales:

- https://docs.isric.org/globaldata/soilgrids/
- https://docs.isric.org/globaldata/soilgrids/wcs.html

Rainmapper usa el servicio WCS de SoilGrids 2.0, resolución de 250 m, licencia CC BY 4.0 y las propiedades de retención de agua `wv0010`, `wv0033` y `wv1500` en seis profundidades y tres cuantiles.

### Estado comprobado

No hay que descargar “un SoilGrids francés”. La caché local actual ya cubre las
dos áreas y la agregación con el código operativo termina correctamente:

| Área | Teselas | Estado | Profundidades | Exclusiones |
|---|---|---|---:|---|
| `font_romeu` | `x163_y84`, `x163_y85` | `complete` | 6 | ninguna |
| `querigut` | `x163_y85` | `complete` | 6 | ninguna |

Cuando existan microáreas se materializará su geometría definitiva. Lo normal
es que reutilicen estas teselas, pero la cobertura se comprobará para cada
geometría real.

## 6. Bosque: BD Forêt V2 D09 y D66

Fuentes:

- https://www.data.gouv.fr/datasets/bd-foret-v2-ariege-2019
- https://www.data.gouv.fr/datasets/bdforet-v2-pyrenees-orientales-2019

Son las primeras capas vectoriales francesas que deben integrarse porque su información puede proyectarse sobre los IDs ecológicos que Rainmapper ya utiliza. D09 es obligatorio para Quérigut; D66 cubre Formiguères, Les Angles y Font-Romeu.

### Preparación

1. Descargar los Shapefiles oficiales de D09 y D66 y conservar los originales.
2. Inspeccionar el CRS y todos los nombres y valores reales de atributos.
3. Recortar al ámbito de trabajo, manteniendo un margen alrededor de las microáreas.
4. Reproyectar el producto de trabajo a EPSG:25831.
5. Registrar versión, fecha, licencia, fuente, hash y transformación aplicada.

### Integración

Añadir una entrada a `vector_layers()` y sus campos relevantes a `MAPPABLE_LAYER_FIELDS`. El mapping debe seguir el mecanismo exacto de `gis_mappings`; no se aceptarán equivalencias inventadas a partir de traducciones del nombre.

Cada valor francés debe quedar en uno de estos estados:

```text
mapped
pending_review
ignored
unmapped
```

Las salidas permitidas en la fase 1 son:

```text
mapped_host_ids
mapped_forest_type_ids
mapped_habitat_feature_ids
mapped_soil_tendency_ids
```

`mapped_lithology_ids` puede conservarse como evidencia de laboratorio, pero no se proyecta al contexto V0 actual.

## 7. Fuentes aplazadas

### OCSID D66 2021

https://www.data.gouv.fr/datasets/ocsid-occupation-du-sol-interdepartementale-pyrenees-orientales66

OCSID puede distinguir bosque, matorral, pastizal, agricultura, suelo desnudo, urbano y agua. Sin embargo, Rainmapper no consume hoy un campo general de ocupación del suelo.

Además, este producto D66 no cubre el extremo de Quérigut en D09. No puede presentarse como una capa continua de todo el corredor.

Antes de integrarlo hay que decidir si una parte pequeña y revisada de sus clases mejora `habitat_feature_ids` o `forest_type_ids`. Si no existe ese mapping concreto, se aplaza; no se ampliará el contrato del predictor sólo para almacenar la capa.

### BRGM BD Charm-50

https://infoterre.brgm.fr/formulaire/telechargement-cartes-geologiques-departementales-150-000-bd-charm-50

El producto geológico existe y su descarga departamental puede requerir formulario. No se automatizará el formulario ni un CAPTCHA. La licencia y las condiciones efectivas se registrarán en el momento de la descarga.

La litología está aparcada en `rainmapper_core/mushroom_profile_v0.py`. BD Charm-50 se incorporará sólo después de una decisión explícita sobre el contrato del modelo y el mapping litológico. Si se activa para este corredor, serán necesarios D09 y D66.

### MNT LiDAR HD

https://www.data.gouv.fr/datasets/mnt-lidar-hd

El producto ofrece GeoTIFF de 50 cm en teselas de 1 km y Licence Ouverte 2.0. No se afirma aquí que todas las teselas de la zona piloto estén ya disponibles: debe comprobarse en el selector oficial antes de planificar una descarga.

Su uso sólo se justifica si RGE ALTI 5 m demuestra una limitación relevante para las microáreas. En ese caso se descargarán exclusivamente las teselas afectadas y se derivará un raster de trabajo compatible.

## 8. Ámbito piloto

El ámbito se definirá mediante las geometrías reales, no mediante una descarga genérica de ambos departamentos. Como referencia funcional debe cubrir inicialmente:

```text
Quérigut
Mijanes
Formiguères
Les Angles
Targasonne
Font-Romeu-Odeillo-Via
```

El recorte debe seguir el corredor y las geometrías reales de las microáreas, con margen suficiente para el muestreo; no todo D09 ni todo D66.

## 9. Orden de implementación

1. Mantener las dos áreas francesas ya creadas y completar sus metadatos administrativos.
2. Descargar, unir y validar RGE ALTI 5 m con el margen conjunto de 10 km. Hecho localmente.
3. Integrar el DEM francés en `sample_dem` y en los informes de procedencia.
4. Incluir el GeoTIFF operativo en el inventario del snapshot.
5. Crear dos o tres microáreas con geometrías reales. Hecho en la copia local.
6. Materializar y auditar su SoilGrids, reutilizando la caché existente. Hecho;
   las tres microáreas tienen estado `complete` y cobertura 1,0.
7. Descargar e inspeccionar BD Forêt V2 D09 y D66.
8. Proponer los mappings a los catálogos Rainmapper y revisarlos antes de activarlos.
9. Integrar la capa vectorial francesa y reconstruir el contexto de las microáreas piloto.
10. Evaluar después, con una necesidad concreta, OCSID, BRGM o LiDAR HD.

## 10. Despliegue en HA real y worker

El DEM no se empaqueta dentro de la imagen de HA. Antes de usar las áreas
francesas en HA real hay que copiar únicamente este fichero:

```text
/media/rainmapper/mushroom-GIS/dem-france-rge-alti-5m/extracted/
rainmapper-dem-france-rge-alti-5m.tif
```

También puede copiarse el README de procedencia. Los cuatro ficheros de
`source/` no son necesarios en HA real. Tras la copia deben comprobarse el
tamaño y el SHA-256 anteriores. El coordinador incorpora el GeoTIFF operativo
al snapshot y el worker lo recibe mediante el transporte transaccional
existente; no hace falta subirlo manualmente al worker.

Hay que distinguir copia a HA y transporte al worker. En el estado verificado
el 9 de septiembre de 2026, el inventario local pasa de 12 ficheros y
6.341.520.039 bytes a 13 ficheros y 6.424.592.573 bytes. Se ha corregido
`sync_from_fetcher` para comparar cada registro con la versión activa mediante
ruta, tamaño y SHA-256 del manifiesto. Los ficheros sin cambios se enlazan al
staging transaccional y sólo se descargan los nuevos o modificados. Si el
sistema de ficheros no permite el enlace, se conserva como alternativa la
descarga normal después de volver a comprobar el espacio disponible.

Para esta ampliación, el comportamiento esperado con el worker `1.1.1` es
reutilizar localmente los 12 ficheros existentes y transferir únicamente los
83.072.534 bytes del nuevo GeoTIFF. La versión anterior permanece disponible
durante la activación; los ficheros enlazados no duplican sus bloques físicos.
Los resultados del transporte exponen por separado ficheros y bytes
transferidos y reutilizados. El worker instalado en HA real no adquiere este
comportamiento hasta que se publique e instale la versión que contiene el
cambio; no se debe lanzar antes un entrenamiento o un precálculo para probarlo.

La copia definitiva en `/Volumes/media/rainmapper/mushroom-GIS` se verificó el
9 de septiembre: tiene 83.072.534 bytes, SHA-256
`3e86d6c2ee4e3677dd895de369045b8f49c02a23902771692177b7a60256860f`,
CRS EPSG:2154, checksum de banda 63498, nodata -99999 y cobertura válida del
100 %. El README y el sidecar de estadísticas también están presentes.

### Auditoría de duplicación existente

La auditoría por tamaño, SHA-256 e inodo del 9 de septiembre no encontró
ficheros duplicados dentro de `mushroom-GIS` en `/Volumes/media`. La copia de HA
es el origen operativo del coordinador y no contiene los archivos `source/` del
repositorio.

El volumen persistente local del worker ocupa 18.084.029.423 bytes y sí conserva
restos históricos materiales:

- la versión GIS inactiva `sha256:4aa377...` duplica físicamente 10 ficheros de
  la versión activa: 6.306.367.027 bytes; la versión activa `sha256:5b537...`
  pasó verificación profunda de sus 12 ficheros y 6.341.520.039 bytes;
- 19 snapshots de reconstrucción de los días 19 y 20 de julio ocupan
  2.130.820.047 bytes, de los que 2.002.188.888 son contenido duplicado;
- 58 directorios de trabajo heredados ocupan 2.520.244.099 bytes, con
  1.045.845.814 bytes duplicados internamente.

En total se identificaron 9.413.367.857 bytes de copias físicas repetidas en el
worker: 6.306.367.027 en la versión GIS inactiva y 3.107.000.830 fuera de las
versiones GIS. No se ha eliminado nada. La limpieza debe reconciliar antes los
trabajos con ambos coordinadores y conservar la versión GIS activa, las cachés
por contenido y los artefactos promovidos.

En el `mushroom-GIS` del repositorio se encontraron 448.748.886 bytes
duplicados, concentrados casi por completo en
`sols-25000-v1r1-202512/source`: un ZIP repetido y una carpeta `copia` cuyos
archivos principales son idénticos a los de `extracted`. Son archivos fuente
locales y no forman parte del inventario operativo del worker.

## 11. Criterios de aceptación

- [ ] El esquema existente guarda un área con `country = France` y sus microáreas sin migración paralela.
- [x] Cada microárea piloto tiene geometría y ubicación representativa válidas.
- [x] SoilGrids cubre ambas áreas mediante la caché existente.
- [x] El DEM francés devuelve elevaciones y conserva un `source_id` trazable.
- [ ] Las áreas españolas mantienen exactamente su cadena y resultados anteriores.
- [x] El cálculo local obtiene altitud mínima, máxima y media, pendiente y orientación para las microáreas piloto.
- [ ] BD Forêt se consulta en EPSG:25831 mediante el pipeline actual.
- [ ] Todos los valores BD Forêt están mapeados, ignorados o pendientes de revisión de forma explícita.
- [ ] Los IDs aceptados existen en los catálogos Rainmapper.
- [x] El inventario del snapshot incluye el DEM francés cuando el fichero existe.
- [ ] El snapshot incluye todos los componentes necesarios de BD Forêt, con tamaño y hash validados.
- [ ] El worker recibe esos artefactos transaccionalmente y consulta los mismos datos que HA local.
- [ ] No se añade litología ni ocupación del suelo al modelo sin una decisión de contrato separada.
- [ ] No se realizan consultas GIS o SoilGrids remotas durante una predicción.

## 12. Fuera de alcance de la primera entrega

```text
CarHab
MNH / altura de dosel
bosque histórico
ortofoto
índices topográficos avanzados
WMS en tiempo de predicción
descarga nacional francesa
nuevas variables de modelo para litología o landcover
```

La primera entrega termina con **áreas francesas + SoilGrids existente + RGE ALTI 5 m + BD Forêt D09/D66**, completamente trazables y compatibles con el contexto operativo actual.
