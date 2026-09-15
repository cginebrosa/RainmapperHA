# SoilGrids: cobertura comprobada y condición de uso en RPi4

**Evidencia de la [especificación central del Mapa de predicción](prediction-map-specification-es.md).**
La auditoría está terminada y los huecos aceptados. Este informe conserva sus
resultados; no sustituye el diseño vigente ni ordena repetir la auditoría.

Auditoría de solo lectura del 11/09/2026. No se ha migrado el Predictor ni
modificado su caché, modelos, áreas o microáreas.

## Resultado y decisión

La cobertura es suficiente para continuar: el usuario acepta los huecos y
**no se intentará rellenarlos**. El diseño de lectura ya está documentado en el
[anexo del lector](mushroom-prediction-map-soilgrids-reader-design-es.md);
implementación y validación de la migración local siguen pendientes, con el
presupuesto de la RPi4 como condición de aceptación.

Se han revisado las 63 combinaciones en la cuadrícula nativa de 250 m, recortando
el recuento con las 19 regiones españolas NUTS2 de GISCO 2024, escala 1:1.000.000.
Ningún polígono regional queda fuera de las teselas descargadas. El cálculo usa
centros de píxel; no es una delimitación catastral ni una medición sobre el terreno.

| Comprobación | Resultado |
|---|---:|
| Celdas de 250 m analizadas dentro de España | 8.105.272 |
| Con valores positivos y en rango en las 63 capas | 7.908.114 (97,5675 %) |
| Celdas con cero en las 63 capas | 197.122 |
| Celdas con algunas capas utilizables y otras no | 36 |
| Catalunya: cobertura con las 63 capas utilizables | 95,4419 % |
| Inversiones inferior/mediana/superior entre cuantiles utilizables | 0 |

«Utilizable» significa `0 < valor <= 1000` para retención (regla del lector
actual) y `0 < valor <= 140` para pH almacenado por diez. No demuestra precisión
científica del valor ni presencia de setas. Los porcentajes se refieren al
territorio administrativo, incluyendo zonas urbanas y superficies sin suelo
modelado; no son porcentajes de bosque.

## Ceros y datos ausentes

- Los 191.739 píxeles españoles marcados NoData en la máscara de referencia
  ISRIC tienen cero en todas las capas WCS. No se deben tratar como suelo con
  pH cero ni como retención medida igual a cero.
- Hay otros 5.383 píxeles con todas las capas a cero y 36 parciales en zonas
  donde esa máscara contiene una clase. La máscara no sustituye al control
  individual de cada capa.
- Se contrastaron cinco puntos con tres pequeños archivos originales de pH
  publicados por ISRIC, leídos a través de su VRT: tres ceros WCS corresponden
  a NoData `-32768`; los otros dos valores coinciden (78 y 68, es decir pH 7,8
  y 6,8). Son controles de la semántica, no una comparación nacional entre servicios.
- Las 36 celdas parciales (35 en Canarias y una en Catalunya) tienen pH
  utilizable y alguna capa de retención no utilizable bajo la regla vigente.
  **No se concluye que cualquier cero aislado de retención sea NoData** por
  extrapolar los controles de pH. Se conserva la distinción y no se rellena.
- La documentación general de ISRIC describe exclusiones de suelo, pero su
  máscara descargada contiene clases de superficie desnuda con valores de
  suelo disponibles. No se impondrá un veto nuevo por esos códigos sin una
  justificación específica; se conserva el dato y su procedencia.

Fuentes: [capas y máscara de SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html)
y [distribución oficial de la máscara](https://files.isric.org/soilgrids/latest/data/landmask/).

## Conservación de áreas y microáreas actuales

Se usa el catálogo local real `docker-data/mushroom-data/mushroom_known_sites.json`,
con 34 áreas y 66 microáreas. El fichero homónimo de `mushroom-data/` está vacío;
no se ha confundido con el catálogo activo local. No se ha auditado HA real.

- Las **66 microáreas** tienen valores utilizables en todas las celdas tocadas
  por sus polígonos y conservan su contexto persistido completo.
- Los hashes de geometría y referencias de archivos de los 66 contextos
  coinciden con el catálogo conservado: ninguna referencia perdida o distinta.
- Se han vuelto a comprobar los **1.355 archivos normalizados** en ambas raíces:
  originales y copias coinciden exactamente con sus SHA-256 esperados.
- 33 áreas tienen cobertura completa en las celdas tocadas. Selva del Camp
  tiene 325 de 326 celdas utilizables; la restante está sin datos en la máscara
  oficial. Ninguna de las microáreas actuales pierde cobertura.

Los recuentos por sitio usan todas las celdas que tocan el polígono, no pesos
por fracción de superficie. No sustituyen el agregado ponderado del Predictor.
La identidad de los archivos prueba conservación de valores, pero no es una
prueba de un lector nuevo ni de una migración todavía no realizada.

## RPi4: cuánto hay que leer realmente

Se han inspeccionado las cabeceras de los 1.948 rásteres de suelo de la descarga:

| Medida | Resultado |
|---|---:|
| Total de rásteres | 795.522.040 bytes |
| Mayor archivo individual | 4.140.163 bytes (4,14 MB) |
| Organización interna de todos los TIFF | Bloques de 256 × 256 píxeles |
| Un bloque Int16 descomprimido | 128 KiB |
| Un bloque de cada una de las nueve capas de pH | 1,125 MiB |
| Un bloque de cada una de las 63 capas | 7,875 MiB |

Las dos últimas cifras son aritmética de bloques para un píxel por capa, **no
mediciones del consumo total de RAM ni del tráfico real de disco**: faltan
cabeceras, índices, cachés GDAL y procesos. Consultas de polígonos, interpolación
y concurrencia pueden necesitar más bloques. No se ha medido latencia en RPi4.

El volumen nacional no obliga a leerlo entero para consultar un punto. El
problema que debemos evitar es repetir validaciones completas o abrir un proceso
por capa en cada petición. En el código actual:

- `rainmapper_core/mushroom_soilgrids.py:802`, `_registered_tile_is_valid`,
  lee archivos completos para comprobar SHA-256, incluidos los originales.
- `aggregate_geometry`, en `:1254`, llama a esa comprobación y después lee
  ventanas mediante `_read_xyz_window` (`:1199`), que ejecuta `gdal_translate`.
- Ese camino prepara contextos de microárea; el Predictor consume contextos
  ya persistidos. No implica que cada predicción actual lea todos esos archivos.

### Condiciones para la futura integración

1. Índice local por tesela/capa que resuelva archivos sin recorrer directorios
   ni cargar un manifiesto nacional grande por cada clic.
2. Lectura por ventana, solo de las propiedades necesarias; no abrir las 63
   capas si la pantalla solo necesita describir el pH.
3. Validación completa al incorporar/actualizar una edición. En consulta, usar
   la edición ya validada y su identidad; no recalcular SHA-256 por cada punto.
4. Caché acotada y reutilización de resultados por celda/edición. No almacenar
   copias del país por especie, fecha, consulta o worker job.
5. Agrupar lecturas para evitar decenas de procesos externos por clic. Elegir
   la implementación compatible con HA antes de desplegar; el uso de bindings
   GDAL del Mac en esta auditoría no añade esa dependencia a HA.
6. Medir antes de migrar: consultas nuevas y repetidas, pico de memoria,
   latencia, lecturas de disco y concurrencia limitada. Fijar el presupuesto
   de aceptación sobre el entorno de ejecución disponible, sin extrapolar los
   tiempos del Mac a la RPi4 ni usar HA real como primera integración.

La auditoría nacional y sus máscaras auxiliares se quedan como evidencia de
preparación en el Mac. No se incorpora esta revisión completa a las consultas
de la aplicación ni se envía su salida extensa en los trabajos del worker.

## Evidencia y reproducción

- [Informe resumido](../reports/mushroom-prediction-map-soilgrids-coverage-2026-09-11.json).
- `mushroom-map-GIS/soilgrids-shared/coverage-audit/coverage.json`: recuentos por
  capa, región y sitio, controles y ejemplos diagnósticos.
- `audit.py` en esa carpeta: recorrido reproducible con GDAL/NumPy locales;
  `coverage-tiles/` conserva categorías espaciales de la auditoría.
- `asset-preservation-check.json`, `geometry-context-check.json` y
  `territorial-envelope-check.json`: conservación y ámbito.
- `source-comparison.json`: comparación puntual de WCS y originales pH;
  `rpi4-io-review.json`: tamaños y estructura de lectura.
- [README de las fuentes auxiliares](../../mushroom-map-GIS/soilgrids-shared/coverage-audit/source/README.md).
