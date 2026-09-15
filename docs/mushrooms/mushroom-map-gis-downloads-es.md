# Descargas GIS para el Mapa de predicción

**Inventario y evidencia de la [especificación central del mapa](prediction-map-specification-es.md).**
El diseño y la distribución operativa se definen allí y en sus anexos técnicos;
este informe acredita adquisición, no integración o instalación en workers.

Adquisición autorizada el **11 de septiembre de 2026**. Estos datos complementarán
el análisis del predictor geográfico; **todavía no están integrados** en modelos,
API, mapa o despliegue HA.

## Ubicación y documentación

Por petición del usuario se guardan en **`mushroom-map-GIS/`**, una carpeta
independiente de `mushroom-GIS`. Cada fuente tiene su README junto a los archivos.
Además, cada TIFF IGN tiene un README individual con sus datos y procedencia.

| Fuente | Estado comprobado | Documentación junto a la descarga |
|---|---|---|
| ICGC, cubiertas de Catalunya 2024 | Completo: ZIP de 810.439.129 bytes y GeoPackage extraído de 1.694.642.176 bytes; 1.524.399 elementos y 41 categorías. | [README ICGC](../../mushroom-map-GIS/icgc-cobertes-2024/source/README.md) |
| IGN/CNIG MDT25, primera cobertura | Completo: 1.524 TIFF, 4.591.983.594 bytes; todos abiertos con GDAL y resolución 25 m comprobada. | [README IGN](../../mushroom-map-GIS/ign-mdt25/source/README.md) |
| MFE25, vegetación y árboles | Recibidas y verificadas las 17 comunidades: 1.994.853 polígonos, 153 archivos originales y 18.004.586.141 bytes extraídos. Dos bases complementarias y diccionario descargados. | [README MFE25 e índice regional](../../mushroom-map-GIS/mfe25/source/README.md) |
| IGME GEODE | Descarga completa: 612.170 recintos geológicos y 44.464 registros de Cuaternario (uno sin geometría); 658 bloques, 1.625.044.963 bytes comprimidos. Límite territorial detectado en Catalánides. | [README GEODE](../../mushroom-map-GIS/geology-spain/source/README.md) |
| ICGC, geología de Catalunya | Copia local verificada: 61.437 polígonos con índice espacial; 16 controles catalanes positivos y tres exteriores sin cobertura. Complemento del hueco GEODE. | [README ICGC geología](../../mushroom-map-GIS/icgc-geologia-50000/source/README.md) |

[Inventario verificable de esta adquisición](../reports/mushroom-map-gis-downloads-2026-09-11.json).
Los manifiestos completos por archivo permanecen junto a los datos y conservan
URL, tamaño y SHA-256. Los binarios y los README individuales están fuera de Git;
este documento y el inventario resumido conservan el seguimiento en el proyecto.
La carpeta también queda excluida del contexto Docker.

## Elecciones y límites

**Altitud.** La [segunda cobertura MDT25](https://centrodedescargas.cnig.es/CentroDescargas/mdt25-segunda-cobertura)
declara cobertura incompleta. Se ha descargado la
[primera cobertura nacional](https://centrodedescargas.cnig.es/CentroDescargas/modelo-digital-terreno-mdt25-primera-cobertura)
como base de 25 m. Incluye variantes de huso para algunas hojas: el número de
archivos no representa otras tantas zonas independientes. Se mantiene el DEM
ICGC de 5 m ya existente para Catalunya, sin volver a descargarlo.

La lectura real detectó dos nombres cuyo huso difiere del CRS del TIFF:
`PNOA-MDT25-ETRS89-HU29-0001-LID.TIF` y
`PNOA-MDT25-ETRS89-HU31-0118B-LID.TIF`. Se conservan los originales y se señala
la discrepancia. Una integración debe leer el CRS interior y el NoData
**-32767**; no deducirlos del nombre ni interpretar el NoData como altitud.
Se han leído cabeceras, no todos los píxeles ni toda la máscara territorial.

**Cubiertas.** Se conserva el [GeoPackage ICGC 2024](https://datacloud.icgc.cat/datacloud/cobertes-sol/gpkg/cobertes-sol-v1r0-2024.zip)
y su ZIP original. La tabla de categorías permite entender la clase de cubierta;
`data_font` conserva la fecha de origen. La edición 2024 actualiza cambios mayores
de 2 ha: no supone observación nueva de todos los metros ni detección de todos los
claros pequeños. Véase la [metodología oficial](https://www.icgc.cat/ca/Geoinformacio-i-mapes/Mapes/Mapa-de-cobertes-del-sol-de-Catalunya).
No se descarga otro raster equivalente que duplicaría la clasificación.

**Árboles.** Las [tablas complementarias oficiales MFE25](https://www.miteco.gob.es/es/biodiversidad/servicios/banco-datos-naturaleza/informacion-disponible/mfe25_informacion_disp.html)
contienen otras especies arbóreas y otras superficies, vinculables por `POLIGON`.
Sus ZIP han pasado CRC; todavía no se han auditado todas sus tablas internas.
No son una sustitución de los polígonos forestales. Las 17 páginas regionales y
sus enlaces quedan archivados en `mfe25/catalogue/` y `mfe25/catalogue.json`.
Los intentos de conexión a `gis.miteco.gob.es` terminan en reinicio o timeout TLS
desde este entorno; no se ha determinado el origen exacto del fallo. El usuario
sí descargó `mfe_catalunia.zip` desde su navegador y lo depositó en el proyecto:
381.585.438 bytes, CRC válido, nueve originales extraídos (1.617.431.022 bytes).
GDAL confirma 238.096 polígonos, todos con origen MFE25, de Barcelona (69.656),
Girona (39.467), Lleida (66.223) y Tarragona (62.750), en **EPSG:25830**.
Hay nombres/códigos de tres especies arbóreas, sus porcentajes de ocupación,
cobertura de copas, formación forestal y uso. Las relaciones con las tablas
complementarias siguen sin auditar. Posteriormente el usuario ha proporcionado
las otras 16 comunidades, cuya comprobación se detalla a continuación.

El paquete remite a `MfeMaxDic2021.gdb` y un diccionario de diciembre de 2021;
los metadatos de exportación están fechados el 14/09/2022. No se ha establecido
la fecha de observación de cada bosque: no anunciarlo como cartografía de 2026.
Las huellas de los originales y comprobaciones están en
`mfe25/source/mfe_catalunia/validation.json`. No se han auditado exhaustivamente
geometrías ni huecos territoriales. La foto fija IEPNB de 2018 se identificó como alternativa
histórica, pero no se descargó como si fuera el MFE25 actual.

**MFE: cierre de las 17 comunidades.** El usuario ha aportado 15 carpetas ya
extraídas y los originales comprimidos de Catalunya (ZIP) y Galicia (RAR).
Galicia se ha extraído con `bsdtar` sin errores. Todas las capas se abren con
GDAL, contienen los componentes SHP/SHX/DBF/PRJ, y sus recuentos completos de
atributos por territorio y origen coinciden con los de GDAL: **1.994.853**
polígonos, todos con `ORIGEN=MFE25`. Cada carpeta tiene README, cabecera GDAL,
recuentos y huellas SHA-256 de sus nueve archivos originales. La carpeta
`MFE_42`, identificada por `NUT2_NOM` como Castilla-La Mancha, se ha renombrado
a `mfe_castillalamancha` por petición del usuario; archivos internos intactos.

La evidencia conjunta está en `mfe25/regions-validation.json`, y el inventario
versionado enlaza las 17 validaciones individuales. Para las 15 carpetas sin
ZIP original se verifican los archivos recibidos; no se afirma haber comprobado
la integridad CRC de un archivo comprimido que no se conserva.

Los diccionarios son Dic2021 en 13 comunidades, Dic2022 en Castilla-La Mancha,
Dic2023 en Aragón y Dic2025 en Andalucía y Comunitat Valenciana. La futura
integración debe normalizar diferencias de campos, por ejemplo `n_sp1` frente
a `sp1_`, y respetar el CRS: Canarias declara **WGS 84 / UTM 28N**, mientras los
otros 16 paquetes declaran **ETRS89 / UTM 30N**. No se han fusionado ni
reproyectado los originales. No quedan paquetes pendientes de las 17 comunidades
catalogadas; esto no demuestra cobertura sin huecos, no incluye una auditoría
geométrica exhaustiva y no equivale a disponer de predicción validada para todo
el país. Ceuta y Melilla no forman parte de ese catálogo regional.

**Geología.** Se utiliza el [REST oficial GEODE](https://mapas.igme.es/gis/rest/services/Cartografia_Geologica/IGME_Geode_50/MapServer),
publicado como distribución en
[datos.gob.es](https://datos.gob.es/es/catalogo/ea0010987-geode-cartografia-geologica-digital-continua-a-escala-1-50-0002).
Las [condiciones generales IGME](https://info.igme.es/media/Pdfs/LicUsoIGME_GENERICA_2022.pdf)
se han consultado y guardado. No se ha encargado un producto vectorial de pago
ni contactado con terceros. Se conservan respuestas JSON de ArcGIS comprimidas,
con geometría sin simplificar; no confundirlas con GeoJSON o un GeoPackage ya indexado.
La paginación por desplazamiento empezó a fallar con error 500; se reanudó por
intervalos de identificadores contrastados con la lista publicada, conservando
los bloques válidos y la procedencia real de cada uno.

La revisión de los 656.634 registros encuentra geometría poligonal no vacía en
656.633. El registro de Cuaternario `OBJECTID 22583`, zona `Z2400`, contiene
`rings: []`; se conserva, pero no sirve para muestreo espacial. La capa principal
contiene 27 códigos de zona y **ningún registro Z3000 (Catalánides)**, aunque
esa zona sí aparece en el catálogo de 28 zonas. Esto impide atribuir cobertura
completa de Catalunya al servicio descargado. Mantener la fuente ICGC prevista
y contrastar las zonas antes de integrar. Evidencia en
`geology-spain/source/geometry-presence-validation.json` y `zones.json`.
Una consulta puntual de Barcelona (2,15 E; 41,40 N) devuelve cero recintos
geológicos en este servicio, coherente con el límite detectado. La respuesta
y los parámetros están conservados en el inventario y junto a la descarga.

El complemento ICGC ya se ha preparado en `icgc-geologia-50000/source/`: ZIP
original, GeoPackage, estilo, metadatos, especificaciones y leyenda. El ZIP y
GeoPackage son copias verificadas de los existentes en `mushroom-GIS`, sin
alterarlos ni repetir su descarga. Se han comprobado integridad, índice y
consultas locales en puntos repartidos por Catalunya. Los resultados y límites
están en el [informe del paso 1](../reports/mushroom-prediction-map-geology-icgc-2026-09-11.json).
El uso previsto es **local**, sin dependencia del servidor: ICGC donde tenga
cobertura catalana y GEODE en los demás puntos válidos. Para GEODE aún falta
crear el índice local de consulta a partir de sus bloques; no está integrado.

El [seguimiento por pasos](mushroom-prediction-map-progress-es.md) mantiene lo
completado, lo pendiente y el siguiente paso propuesto.

Antes de anunciar cobertura del nuevo predictor habrá que comprobar datos
válidos por territorio y preparar índices de consulta. Tener un archivo del
terreno no demuestra disponer de meteorología suficiente, un modelo aplicable
o una probabilidad validada en ese lugar.

## SoilGrids nacional: retención y pH

Adquisición autorizada y terminada el 11/09/2026 en
`mushroom-map-GIS/soilgrids-shared/source/`, junto a GIS/DEM. Se conservan las
54 capas de retención actuales y se añaden nueve de pH superficial con
incertidumbre; textura, carbono y materia orgánica quedan fuera.

538 bloques nuevos, 401.229.517 bytes comprimidos, más 1.410 archivos anteriores
copiados verificando huellas; total 795.522.040 bytes de rásteres. Lectura completa
GDAL y SHA-256 por bloque, 7.119 pares tesela/capa para 113 teselas de almacenamiento
y 63 combinaciones. Ámbito conservador español incluyendo islas, Ceuta y Melilla,
preservando zonas anteriores exteriores; no garantiza dato válido en cada píxel.

[Informe de adquisición](../reports/mushroom-prediction-map-soilgrids-acquisition-2026-09-11.json)
y [README de la fuente](../../mushroom-map-GIS/soilgrids-shared/source/README.md).
Los originales WCS no declaran CRS/NoData; se conservan intactos. Quedan
normalización, máscaras, comparación de ediciones y adaptación de lectores antes
de la migración controlada. No se sustituye todavía la caché del Predictor.

## Preservación del sistema actual

No se modifica `mushroom-GIS`, modelos, observaciones, URLs de coordinador ni
configuraciones de HA/worker. No se ejecutan entrenamientos, precálculos o builds.
El SHA-256 de `mushroom-data/mushroom_observations.json` sigue siendo
`f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
