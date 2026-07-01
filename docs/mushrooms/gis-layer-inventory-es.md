# Inventario GIS para laboratorio de setas

Version del documento: borrador 0.1
Fecha: 2026-07-01

Este documento inicia la mini-fase GIS previa al `observation_context_builder`.
El objetivo no es integrar capas todavia, sino decidir que fuentes oficiales pueden
aportar contexto topografico, forestal, litologico y edafologico a las
observaciones reales del laboratorio.

## Alcance territorial

Prioridad operativa:

1. Catalunya.
2. Peninsula Iberica espanola como fallback y ampliacion posterior.

Fuera de alcance por ahora:

- Islas Canarias.
- Islas Baleares.
- Ceuta.
- Melilla.

La razon no es tecnica, sino de control de complejidad: esas zonas pueden tener
capas, CRS, geologia, vegetacion y resoluciones distintas. Se reabriran cuando el
flujo peninsular este estabilizado.

## Principios de uso

- No versionar capas GIS descargadas.
- Guardar capas locales bajo `tmp/mushroom-lab/input/gis/` o fuera del repo.
- Mantener `mushroom_gis_mappings.json` como contrato entre codigos externos e
  IDs internos de `mushroom_reference_catalogs.json`.
- No inferir equivalencias por intuicion. Si una clase externa no tiene mapping,
  reportar gap.
- Usar WMS solo para inspeccion visual. Para calculo reproducible se prefieren:
  descarga local, GeoTIFF/COG, Shapefile/GeoPackage, WFS o WCS.

## Raster vs vectorial

Una capa raster no es necesariamente una imagen inutil. Si es un GeoTIFF
clasificado, cada celda tiene un codigo consultable. Para una observacion:

```text
lat/lon -> celda raster -> codigo externo -> mushroom_gis_mappings.json -> ID interno
```

Ventajas del raster:

- muestreo rapido por punto;
- facil generar grids de probabilidad;
- bueno para DEM, pendiente, orientacion y coberturas clasificadas.

Ventajas del vectorial:

- atributos mas ricos;
- conserva poligonos oficiales;
- util para litologia, suelos y unidades forestales cuando el detalle
  semantico esta en tablas de atributos.

Decision provisional:

- DEM, pendiente y orientacion: raster.
- Cobertura/cubierta clasificada: raster si trae codigos estables; vector si
  necesitamos atributos que el raster no conserva.
- Litologia y suelos: vector como fuente primaria; se puede rasterizar despues
  para acelerar muestreos masivos.

## Candidatos Catalunya

## Cierre v0 Catalunya

Estado acordado para la primera version del laboratorio GIS de setas:

| Necesidad | Fuente v0 | Estado |
| --- | --- | --- |
| Hosts observables/inferibles | MVC50 `Mapa de vegetacio de Catalunya 1:50.000` | Cubierto |
| Vegetacion y habitat | MVC50 | Cubierto |
| Substrato preferente vegetal | MVC50 `LLVA_Subst` | Cubierto |
| Geologia/litologia | ICGC `geologia-territorial-50000-geologic-v3r0-202412` GeoPackage | Cubierto |
| DEM/topografia | ICGC `model-elevacions-terreny-topografic-catalunya-5m-2009-2018` GeoTIFF | Cubierto |
| Suelo real detallado | Ninguna capa v0 | Descartado; se usa `LLVA_Subst` como sustrato predictivo |
| Cobertura estructural complementaria | ICGC/MCSC `cobertes-sol-v1r0-2024` | Candidata futura, no necesaria para v0 |

Decision operativa:

- No buscar mas capas GIS para hosts/vegetacion/geologia/DEM v0 Catalunya.
- No usar `cobertes-sol-v1r0-2024` para hosts; los hosts quedan cubiertos por
  MVC50.
- Descartar `sols-25000-v1r1-202512` para v0: cobertura parcial, poca utilidad
  para el predictor actual y mapping poco directo contra los IDs internos de
  suelo de especies.
- Usar `MVC50.LLVA_Subst` como fuente principal de sustrato predictivo
  (`Carbonatat`, `Silici`, `Indiferent`, etc.).
- Mantener `cobertes-sol-v1r0-2024` como candidata futura si el cruce de
  observaciones muestra que necesitamos cobertura estructural mas reciente o
  detallada que MVC50.
- La siguiente fase es probar consultas por coordenada y disenar salidas
  experimentales con MVC50, DEM, geologia y meteorologia.

### Topografia: ICGC Elevacions

Estado: fuente v0 seleccionada para Catalunya.

Fuente:

- ICGC `Elevacions`: https://www.icgc.cat/ca/Geoinformacio-i-mapes/Dades-i-productes/Elevacions
- Metadatos IDEC:
  https://catalegs.ide.cat/geonetwork/srv/cat/catalog.search#/metadata/model-elevacions-terreny-topografic-catalunya-5m-2009-2018
- Descarga directa inspeccionada:
  https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/tif_unzip/model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif

Datos verificados:

- ICGC lista nubes de puntos lidar y modelos de elevaciones.
- La pagina explicita `Elevacions territorial` con modelos de elevaciones de
  alta precision, orientaciones y pendientes.

Fuente local inspeccionada:

```text
/Users/carlosginebrosa/Developer/GIS/IGCC/model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif
```

Copia local de trabajo dentro del repo, ignorada por Git:

```text
mushroom-GIS/model-elevacions-terreny-topografic-catalunya-5m-2009-2018/extracted/model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif
```

Datos verificados con `gdalinfo`:

- driver: GeoTIFF;
- tamano local: 4,8 GB;
- raster: 56.344 x 55.812 pixeles;
- CRS: EPSG:25831, ETRS89 / UTM zone 31N;
- resolucion: 5 m/pixel;
- origen: `(258102.500000, 4763932.500000)`;
- extent: `(258102.500000, 4484872.500000) - (539822.500000, 4763932.500000)`;
- banda: 1 banda `Float32`, `ColorInterp=Gray`;
- `NoData`: `-9999`;
- compresion: LZW;
- overviews internas presentes;
- metadata `TIFFTAG_ARTIST=ICGC`.

Uso previsto:

- altitud corregida/independiente de EXIF;
- pendiente;
- orientacion/aspect;
- posible rugosidad o indice topografico futuro.

Prueba pendiente:

- probar muestreo puntual de altitud sobre observaciones reales;
- derivar slope/aspect en local con GDAL o calcularlos bajo demanda;
- decidir si se guardan derivados completos o solo recortes/salidas
  experimentales.

### Cobertura/cubiertas: ICGC CatLC / MCSC

Estado: candidata futura, no necesaria para v0 Catalunya.

Fuente:

- ICGC `Conjunt de dades multi-resolucio pel Mapa de cobertes de Catalunya (CatLC)`:
  https://www.icgc.cat/ca/Geoinformacio-i-mapes/Mapes/Conjunt-de-dades-multi-resolucio-pel-Mapa-de-cobertes-de-Catalunya-CatLC
- ICGC `Mapa de Cobertes del Sol de Catalunya (MCSC)`, producto local
  inspeccionado como `cobertes-sol-v1r0-2024`.

Datos verificados:

- CatLC usa imagenes aerotransportadas y satelite de 2018.
- Los datos estan en GeoTIFF georreferenciado en WGS84 UTM31N.
- Incluye variables topograficas: aspect a 5 m, DEM a 5 m, slope a 5 m, CHM y
  DSM.
- Incluye un mapa de cobertes del sol con 41 clases a 1 m.
- Licencia indicada: Creative Commons BY 4.0.
- La descarga directa esta en `ftp.icgc.cat/descarregues/CatLCNet`.
- MCSC `cobertes-sol-v1r0-2024` local trae un GeoPackage de 2,4 GB con capa
  `cobertes_sol`, tabla `cobertes_sol_categories`, 1.524.399 poligonos,
  41 categorias, CRS EPSG:25831 y campo principal `nivell_2`.
- MCSC diferencia cobertura estructural util: bosques densos/claros de
  aciculifolios, caducifolios/planifolios y esclerofilos/laurifolios, matollar,
  prats/herbassars, bosc de ribera, sol nu forestal, zonas quemadas, urbano,
  agricola y agua.

Uso previsto:

- cobertura forestal/no forestal;
- clase de cubierta para habitat;
- posible proxy de estructura vegetal con CHM;
- DEM/slope/aspect si evitamos descargar otro producto.

Riesgos:

- volumen alto de descarga;
- hay que confirmar si el mapa de 41 clases distingue suficientemente coniferas,
  frondosas, matorral, prados, cultivos, urbano y agua;
- no debe usarse para inferir especie de arbol si la clase solo dice bosque
  generico.
- MCSC no aporta hosts con el detalle de MVC50 y no debe bloquear la v0.

Prueba pendiente:

- aparcar hasta que las primeras features por observacion muestren si MVC50 se
  queda corto para cobertura estructural;
- si se reactiva, usar MCSC solo para `forest_type_ids`/`habitat_feature_ids`,
  no para `host_taxa`.

### Vegetacion/hosts/substrato: Mapa de vegetacio de Catalunya 1:50.000

Estado: candidato v0 fuerte para Catalunya.

Fuente oficial:

- Pagina de origen UB: https://www.ub.edu/geoveg/cat/cartovegetacio.php
- Descarga unificada MVC50 en shapefile ETRS89:
  http://atzavara.bio.ub.edu/mapes_descarrega/MVC50mil.zip
- Documento metodologico:
  http://atzavara.bio.ub.edu/geoveg/docs/MapaVegetacioCatalunya_50mil_2018.pdf
- Servidor SEMHAVEG para inspeccion visual:
  http://www.ub.edu/geoveg/cat/semhaveg.php

Referencia recomendada por la fuente:

```text
Carrillo, E.; Ferre, A.; Illa, E.; Mercade, A. (editors) 2018. Mapa de vegetacio de Catalunya, E. 1:50.000. Universitat de Barcelona.
```

Fuente local inspeccionada:

```text
/Users/carlosginebrosa/Developer/GIS/IGCC/MVC50mil/
```

Copia local de trabajo dentro del repo, ignorada por Git:

```text
mushroom-GIS/MVC50mil/source/MVC50mil.zip
mushroom-GIS/MVC50mil/extracted/
```

Ficheros:

- `extracted/MVC50mil_novembre2019.shp`
- `extracted/MVC50mil_novembre2019.dbf`
- `extracted/MVC50mil_novembre2019.prj`
- `extracted/MapaVegetacioCatalunya_50mil_2019.pdf`

Herramientas usadas:

- GDAL `3.13.1`;
- Poppler `pdftotext 26.06.0`.

Datos verificados con `ogrinfo`:

- driver: ESRI Shapefile;
- geometria: Polygon;
- features: 116.468;
- CRS: EPSG:25831, ETRS89 / UTM zone 31N;
- extent: `(260188.983400, 4488765.827400) - (527401.970600, 4747980.932200)`;
- ultima actualizacion DBF: 2022-01-11;
- codificacion indicada por `.cpg`: UTF-8.

Campos utiles para el predictor:

| Campo | Uso probable |
| --- | --- |
| `LLVA`, `LLVA_txt` | vegetacion actual detallada |
| `LLVA_niv1`, `LLVA_niv1t` | vegetacion actual simplificada, nivel 1 |
| `LLVA_niv2`, `LLVA_niv2t` | grupos de vegetacion actual utiles para `forest_type_ids` y habitat |
| `LLVA_niv3`, `LLVA_niv3t` | agrupacion amplia de vegetacion |
| `LLFISCAT`, `LLFISCAT_t` | fisiognomia/sobrecarga forestal con especies arboreas dominantes |
| `LLVA_Subst` | substrato preferente de la unidad de vegetacion |
| `LLVP`, `LLVP_txt` | vegetacion potencial |
| `LLVP_Estge` | estatge altitudinal/bioclimatico |
| `LLVP_RBiog`, `LLVP_PBiog` | region/provincia biogeografica |
| `LLVP_Fisio` | fisiognomia dominante de la vegetacion potencial |

Confirmacion del PDF:

- La serie 1:50.000 se inicio en 1983 con el full 295 `Banyoles`, coordinada
  por el Grup de Geobotanica i Cartografia de la Vegetacio de la Universitat de
  Barcelona.
- La serie completa de hojas se termino en 2016 y se fusiono en 2018 en un
  documento cartografico unico.
- El MVC50 fusiona y homogeneiza toda la serie del Mapa de vegetacio de
  Catalunya 1:50.000.
- La vegetacion actual incluye 362 unidades.
- La vegetacion actual simplificada reduce esa informacion a 150 unidades.
- Los niveles 2 y 3 agrupan por caracterizacion fisiognomica y biogeografica.
- La leyenda fisiognomica supera las 200 unidades y representa sobre todo la
  diversidad de especies arboreas; puede indicar especies unicas, mezclas de dos
  o mezclas de tres.
- La cobertura final es continua y tiene casi 117.000 poligonos con atributos de
  vegetacion actual, vegetacion actual simplificada, vegetacion potencial,
  fisiognomia y otros atributos.
- `LLVA_Subst` representa el substrato preferente de la unidad de vegetacion:
  carbonatado, silici, indiferente, salino, arenoso, yesifero, inundado,
  rocoso, nitrogenado, materiales cuaternarios, heterogeneo o agua.

Agregados observados:

`LLFISCAT_t` contiene hosts directamente utiles:

- `Pi blanc (Pinus halepensis)` - 8.884 poligonos.
- `Pi roig (Pinus sylvestris)` - 3.443.
- `Pinassa (Pinus nigra subsp. salzmannii)` - 2.468.
- `Carrasca (Quercus rotundifolia)` - 2.321.
- `Roure martinenc i híbrids (Quercus pubescens, Q. x cerrioides..)` - 2.144.
- `Alzina (Quercus ilex)` - 2.021.
- `Pi negre (Pinus uncinata)` - 1.834.
- `Roure de fulla petita (Quercus faginea)` - 1.468.
- Tambien aparecen mezclas como `Quercus ilex + Pinus halepensis` o
  `Quercus pubescens + Pinus sylvestris`.

`LLVA_niv2t` contiene clases de habitat/vegetacion utiles:

- `Alzinars i suredes`.
- `Rouredes i pinedes submediterrànies de pi roig i pinassa`.
- `Carrascars`.
- `Boscos de pi negre subalpins`.
- `Boscos boreals de pi roig montans i altimontans`.
- `Fagedes, avetoses i altres boscos humits afins`.
- `Arbredes amb sotabosc no forestal`.
- prados, matollars, vegetacion ruderal, roquedos y otros habitats no forestales.

`LLVA_Subst` contiene 13 valores observados en la capa:

- `Carbonatat` - 50.639 poligonos.
- `Indiferent` - 39.376.
- `Silici` - 16.638.
- `Al·luvial` - 3.127.
- `Rocós carbonatat` - 3.022.
- `Rocós silici` - 1.193.
- `Inundat`, `Guixenc`, `Nitrificat`, `Arenós`, `Salí`, `Rocós salí`,
  `No atribuïble`.

Uso previsto:

- mapping de `LLFISCAT`/`LLFISCAT_t` a `host_taxa`;
- mapping de `LLVA_niv2`/`LLVA_niv2t` a `forest_types` y
  `habitat_features`;
- mapping conservador de `LLVA_Subst` a `soil_types` o `lithology_types`
  solo como substrato preferente de vegetacion, no como mapa geologico duro;
- uso de `LLVP_Estge` como contexto bioclimatico, no como altitud medida.

Riesgos:

- escala 1:50.000: buena para contexto, no para microhabitat;
- `LLFISCAT_t` puede contener mezclas de especies y no debe convertirse en un
  unico host sin conservar todos los hosts detectados;
- `LLVA_Subst` es atributo de preferencia de la unidad de vegetacion, no una
  medicion edafologica puntual;
- no sustituye el DEM ni un mapa de suelos continuo cuando existan.

Decision provisional:

Esta capa pasa por delante de CatLC como fuente v0 de vegetacion/hosts/habitat
en Catalunya, porque ya trae atributos vectoriales semanticos y especies
arboreas. CatLC queda como complemento para coberturas raster, DEM/slope/aspect,
estructura vegetal o validacion cruzada.

Prueba pendiente:

- hacer consulta por coordenada contra 2-3 observaciones anonimizadas;
- decidir parser de `LLFISCAT_t` para especies simples y mixtas;
- crear propuesta de `source_id`, por ejemplo `icgc_mvc50_2019`;
- definir mappings solo tras revisar valores reales y catalogos existentes.

### Suelos: ICGC Mapa de sols 1:25.000

Estado: descartado para v0.

Motivo:

- la pagina oficial matiza que el producto se sirve sobre cobertura disponible
  e indica informacion de detalle de aproximadamente el 25% de la superficie
  agraria de Catalunya;
- QGIS muestra gaps amplios en la copia descargada;
- las primeras consultas reales devuelven `no_coverage_at_point` mientras
  MVC50, geologia y DEM si responden;
- el mapping a los `soil_type_ids` internos no compensa para el predictor v0;
- `MVC50.LLVA_Subst` cubre el sustrato predictivo que necesitamos ahora.

Decision:

- no consultar `sols-25000-v1r1-202512` en el laboratorio v0;
- no crear mappings desde esta capa;
- borrar o mantener los ficheros locales queda como decision operativa local,
  pero no deben versionarse ni entrar en la imagen HA.

### Suelos: ICGC Perfils de sols

Estado: fuente complementaria, no capa principal v0.

Fuente:

- ICGC `Perfils de sols`:
  https://www.icgc.cat/ca/Geoinformacio-i-mapes/Dades-i-productes/Geoinformacio-tematica/Cartografia-de-sols/Perfils-de-sols

Datos verificados:

- CSV con perfiles de suelo descritos en campo.
- Publicacion 2025, version v1.0, 3419 registros.
- Incluye composicion por horizontes y caracterizacion fisico-quimica.
- Precision horizontal indicada: <= 100 m.
- Licencia indicada: CC BY 4.0.

Uso previsto:

- validacion o enriquecimiento local cerca de observaciones;
- no usar como cobertura continua del predictor si no hay interpolacion o
  poligonos asociados.

Prueba pendiente:

- comprobar campos y coordenadas;
- decidir si sirve para explicar suelos observados o solo como referencia.

### Litologia/geologia: ICGC geologia

Estado: candidato v0 fuerte para Catalunya con GeoPackage descargado e
inspeccionado localmente.

Fuente:

- ICGC `Geoinformacio geologica i geofisica`:
  https://www.icgc.cat/ca/Geoinformacio-i-mapes/Dades-i-productes/Geoinformacio-geologica-i-geofisica
- Metadatos IDEC del producto `geologia-territorial-50000-geologic-v3r0-202412`:
  https://catalegs.ide.cat/geonetwork/srv/cat/catalog.search#/metadata/geologia-territorial-50000-geologic-v3r0-202412

Datos verificados:

- ICGC agrupa cartografia geologica a diferentes escalas y modelo geologico 3D.
- En la pagina general de geoservicios aparece WMS Geologia territorial.

Fuente local GeoPackage inspeccionada:

```text
/Users/carlosginebrosa/Developer/GIS/IGCC/geologia-territorial-50000-geologic-v3r0-202412-Geopackage/
```

Copia local de trabajo dentro del repo, ignorada por Git:

```text
mushroom-GIS/geologia-territorial-50000-geologic-v3r0-202412/source/geologia-territorial-50000-geologic-v3r0-202412.zip
mushroom-GIS/geologia-territorial-50000-geologic-v3r0-202412/extracted/
```

Ficheros clave:

- `extracted/geologia-territorial-50000-geologic-v3r0-202412.gpkg`
- `extracted/geologia-territorial-50000-geologic-v3r0-202412.qlr`
- `extracted/geologia-territorial-50000-geologic-v3r0-20250430.pdf`
- `extracted/geologia-territorial-50000-geologic-v3r0-202412.html`

Capas internas inspeccionadas con `ogrinfo`:

- `_02_plecs_50000` - Line String.
- `_01_contactes_50000` - Line String.
- `_04_unitats_geologiques_50000` - Polygon.
- `_03_falles_50000` - Line String.
- `layer_styles` - estilos.

Datos verificados de `_04_unitats_geologiques_50000`:

- driver: GPKG;
- geometria: Polygon;
- features: 61.437;
- codigos geologicos distintos en `Codi`: 1.055;
- CRS: EPSG:25831, ETRS89 / UTM zone 31N;
- extent: `(258139.649600, 4486262.977600) - (527401.970700, 4747980.932300)`.

Campos utiles inspeccionados:

| Campo | Uso probable |
| --- | --- |
| `Codi` | codigo de unidad geologica |
| `Ordre` | orden/simbologia |
| `Descripcio` | descripcion litologica/geologica de la unidad |
| `Eo`, `Era`, `Periode`, `Epoca`, `Edat` | edad geologica |
| `Codi_metamorfisme` | codigo de metamorfismo |
| `Descripcio_metamorfisme` | descripcion de metamorfismo |
| `Eo_metamorfisme`, `Era_metamorfisme`, `Periode_metamorfisme`, `Epoca_metamorfisme`, `Edat_metamorfisme` | edad del metamorfismo |
| `Codi_protolit` | codigo de protolito |
| `Descripcio_protolit` | descripcion de protolito |

Nota operativa:

- Para v0 usar el GeoPackage con atributos, no variantes raster RGB
  renderizadas del mapa geologico.

Uso previsto:

- litologia/geologia por coordenada desde `_04_unitats_geologiques_50000`;
- substrato calcareo/siliceo/arcilloso si `Descripcio`, `Codi_protolit` o
  `Descripcio_protolit` lo soportan claramente;
- geologia como proxy de suelo solo cuando no haya mapa de suelos y marcandolo
  como proxy.

Riesgos:

- WMS no basta para el motor numerico;
- hay 1.055 codigos geologicos distintos; el mapping directo uno a uno puede ser
  demasiado grande y probablemente requiera una capa intermedia de familias
  litologicas candidatas.
- `Descripcio` es texto descriptivo oficial, pero no debe mapearse con reglas
  ad hoc opacas; cualquier clasificacion calcareo/siliceo/arcilloso debe quedar
  trazada en `mushroom_gis_mappings.json` o en una tabla auxiliar revisable.

Prueba pendiente:

- probar consultas por coordenada de observaciones reales/anonomizadas;
- extraer muestra de codigos/descripciones frecuentes en observaciones;
- decidir si el primer mapping usa `Codi` directo o una familia litologica
  intermedia;
- mapear codigos a `lithology_type_ids`, no textos libres.

### Vegetacion ICGC WMS

Estado: util para inspeccion visual, no fuente primaria v0.

Fuente:

- ICGC pagina general de geoinformacion lista `WMS Vegetacio`:
  https://www.icgc.cat/ca/Geoinformacio-i-mapes

Uso previsto:

- revisar visualmente zonas y comparar con CatLC.

Riesgo:

- si es solo WMS, no ofrece atributos robustos para reconstruccion por
  observacion.

## Candidatos Peninsula

### DEM/MDT: IGN/CNIG

Estado: candidato fuerte como fallback fuera de Catalunya.

Fuente:

- Centro de Descargas CNIG:
  https://centrodedescargas.cnig.es/CentroDescargas/index.jsp

Uso previsto:

- altitud, pendiente, orientacion fuera de Catalunya.

Prueba pendiente:

- confirmar producto concreto: MDT05, MDT25 u otro;
- confirmar formato, CRS, resolucion y licencia;
- descargar recorte peninsular pequeno o una hoja de prueba.

### Ocupacion/cubiertas: SIOSE Alta Resolucion

Estado: candidato fuerte para cobertura peninsular general.

Fuente:

- SIOSE:
  https://www.siose.es/
- SIOSE Alta Resolucion:
  https://www.siose.es/web/guest/descripcion-ar

Datos verificados:

- SIOSE genera una base de datos de ocupacion del suelo para toda Espana de
  forma coordinada por administraciones publicas.
- SIOSE AR integra informacion de cubiertas y usos del suelo de distintas
  administraciones, con mayor detalle geometrico, tematico y temporal.
- La pagina incluye descarga via Centro de Descargas CNIG.
- Las fuentes tematicas para entornos naturales incluyen SIGPAC, Foto Fija del
  Mapa Forestal de Espana y datos de observacion como LiDAR.

Uso previsto:

- cobertura general fuera de Catalunya;
- separar forestal, agricola, urbano, agua, roquedo, matorral, prados, etc.;
- no asumir especie arborea si el dato no la contiene.

Prueba pendiente:

- descargar muestra;
- inspeccionar modelo fisico y campos;
- decidir si usar SIOSE AR como capa principal o fallback respecto al Mapa
  Forestal.

### Forestal: MITECO Banco de Datos de la Naturaleza / Mapa Forestal

Estado: candidato fuerte para vegetacion/forestal estatal, pendiente de descarga
concreta.

Fuente:

- MITECO Banco de Datos de la Naturaleza:
  https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza.html

Datos verificados:

- El BDN da acceso a informacion alfanumerica, cartografica, documental y
  multimedia del Inventario Espanol del Patrimonio Natural y de la Biodiversidad.
- La politica de datos se basa en acceso libre, aunque MITECO recomienda
  consultar tambien a las comunidades autonomas cuando los datos proceden de
  ellas.
- La pagina ofrece catalogo de informacion publica, WMS y visores.

Uso previsto:

- tipos de masa forestal;
- posibles especies dominantes si el producto elegido lo aporta;
- fallback o complemento de CatLC/SIOSE.

Prueba pendiente:

- localizar descarga concreta del Mapa Forestal de Espana o Foto Fija;
- confirmar atributos de especies/formaciones;
- evaluar si supera a SIOSE para hosts.

### Litologia/geologia: IGME GEODE

Estado: candidato estatal fuerte, con friccion de acceso vectorial.

Fuente:

- IGME GEODE:
  https://info.igme.es/cartografiadigital/geologica/geode.aspx

Datos verificados:

- GEODE es cartografia geologica digital continua a escala 1:50.000.
- Homogeneiza la serie MAGNA, que integra 1143 mapas.
- El plan GEODE busca continuidad cartografica, leyenda unificada y base
  topografica uniforme.
- La informacion vectorial se facilita en ESRI Shapefile, con leyenda PDF e
  informacion auxiliar, pero la pagina indica solicitud y tarifa para vectorial.

Uso previsto:

- fallback o ampliacion litologica peninsular;
- mapping a litologias internas.

Riesgos:

- acceso vectorial no inmediato;
- puede ser excesivo para v0 si ICGC ya cubre Catalunya.

Prueba pendiente:

- comprobar si hay servicios/descargas alternativas abiertas para las zonas
  peninsulares de interes;
- decidir si usar IGME solo cuando salgamos de Catalunya.

## Hipotesis de arquitectura

Para el futuro `observation_context_builder`:

```json
{
  "observation_id": "obs_...",
  "site_context": {
    "dem": {
      "source_id": "icgc_catlc_dem_2018",
      "altitude_m": 1234,
      "slope_deg": 18.2,
      "aspect_deg": 32.0
    },
    "land_cover": {
      "source_id": "icgc_catlc_land_cover_2018",
      "raw_code": "pending_real_code",
      "mapped_forest_type_ids": [],
      "mapped_habitat_feature_ids": [],
      "mapping_status": "unmapped"
    },
    "soil": {
      "source_id": "icgc_msc25m",
      "raw_code": "pending_real_code",
      "mapped_soil_type_ids": [],
      "mapping_status": "unmapped"
    },
    "lithology": {
      "source_id": "icgc_geology_pending",
      "raw_code": "pending_real_code",
      "mapped_lithology_type_ids": [],
      "mapping_status": "unmapped"
    }
  }
}
```

Esto es un schema de trabajo, no un contrato productivo. Los codigos reales
deben salir de muestras descargadas, no de nombres humanos vistos en visor.

## Plan de prueba de 2 dias maximo

Dia 1:

1. Descargar o localizar una muestra pequena de CatLC.
2. Confirmar si el mapa de 41 clases trae codigos estables y leyenda.
3. Confirmar una fuente DEM ligera: CatLC DEM/aspect/slope o ICGC Elevacions.
4. Documentar tamano real, CRS y estrategia de recorte.

Dia 2:

1. Descargar o localizar el SHP del Mapa de sols 1:25.000.
2. Localizar descarga/vector util de geologia ICGC o dejar GEODE como fallback.
3. Probar una consulta manual sobre 2-3 coordenadas ficticias o anonimizadas.
4. Actualizar este inventario con campos reales, codigos y gaps.

Salida esperada:

- lista corta de capas v0;
- decision raster/vector por capa;
- primer set de `source_id`;
- lista de campos externos candidatos para `mushroom_gis_mappings.json`;
- tareas de descarga/procesamiento sin tocar datos reales ni versionar capas.

## Decision actualizada

Para v0 en Catalunya, el orden mas pragmatico es:

1. MVC50 1:50.000 para vegetacion, hosts, habitat y substrato preferente.
2. ICGC Model d'elevacions del terreny topografic Catalunya 5 m para DEM,
   pendiente y orientacion.
3. ICGC geologia territorial 1:50.000 GeoPackage como apoyo secundario y
   trazabilidad litologica, sin sustituir el substrato directo de MVC50 en v0.
4. ICGC Mapa de sols 1:25.000 descartado para v0 por cobertura parcial,
   foco agrario y mapping poco directo contra los IDs internos que usan las
   especies.
5. SIOSE/MITECO/CNIG como fallback peninsular despues de cerrar el flujo
   catalan.

## GIS mappings revisables

La pantalla futura `GIS mappings` debe mantener el contrato entre valores GIS
crudos y codigos internos del catalogo. No debe editar IDs en campos libres:

- cada valor externo se identifica por `source_id`, `field` y `raw_value`;
- los destinos se eligen con selects cerrados contra
  `mushroom_reference_catalogs.json` (`host_taxa`, `forest_types`,
  `soil_types`, `lithology_types`, `habitat_features`);
- el reconstructor conserva siempre el valor crudo y solo anade IDs internos a
  la salida computable cuando el mapping exacto esta `accepted`;
- si una reconstruccion encuentra un valor no presente en
  `mushroom_gis_mappings.json`, lo lista como candidato pendiente de revision,
  pero no modifica automaticamente el catalogo ni los mappings.

La seccion `exact_value_mappings` de `mushroom_gis_mappings.json` es el formato
preferente para las capas locales activas como MVC50. Los mappings antiguos por
patron de texto quedan como ayuda inicial, no como fuente definitiva para campos
criticos.

Contrato de estados de revision para `exact_value_mappings`:

- `accepted`: valor revisado y usable. Puede emitir IDs internos hacia el
  laboratorio y el futuro motor.
- `pending_review`: valor persistido para no perderlo, pero pendiente de
  decision humana. Puede guardarse sin IDs internos si todavia no hay criterio,
  o con IDs propuestos para revision, pero no alimenta el futuro motor hasta
  pasar a `accepted`.
- `ignored`: valor revisado y descartado. No emite IDs internos, pero queda
  persistido para que futuras reconstrucciones no lo vuelvan a listar como
  pendiente.

El reconstructor no debe sobrescribir `mushroom_gis_mappings.json`. Solo lee los
mappings existentes, aplica a la salida computable los `accepted` con IDs
validos, mantiene los `pending_review` como valores conocidos pendientes y trata
los `ignored` como valores conocidos sin salida computable. El resultado
temporal de la reconstruccion se escribe bajo `tmp/`. La escritura de mappings
solo ocurre desde la pantalla `GIS mappings` cuando el usuario pulsa guardar.

La UI inicial de `GIS mappings` trabaja de forma incremental: muestra los
mappings exactos ya aceptados y los valores nuevos detectados por la ultima
reconstruccion de observaciones. No escanea por defecto todas las combinaciones
posibles de las capas originales completas. Esta decision es intencionada para
el laboratorio: primero se estabilizan los valores que aparecen en observaciones
reales y despues, si hace falta cerrar cobertura antes de generar mapas masivos,
se puede anadir una auditoria batch de valores unicos por capa/campo.
