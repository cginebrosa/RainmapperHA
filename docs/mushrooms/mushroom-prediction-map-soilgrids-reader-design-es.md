# SoilGrids compartido: diseño del lector y validación para RPi4

**Anexo técnico de la [especificación central del Mapa de predicción](prediction-map-specification-es.md).**
Este documento concreta el lector, compatibilidad y recursos compartidos con la
aplicación actual; el diseño completo y sus fases se consultan en la especificación.

Propuesta del 11/09/2026. **Diseño documentado; agregación hídrica y migración
sin implementar.** Ampliación del 12/09: lector candidato de puntos DEM/pH,
índice SQLite y vista previa en §6 de la especificación central; no reemplaza
el contexto hídrico antiguo ni acredita su compatibilidad numérica.
Complementa el [plan de alcance](mushroom-prediction-map-soilgrids-plan-es.md).
No reabre la adquisición ni la auditoría nacional: los huecos están aceptados.

Reparto revisado por indicación del usuario: el
[plan de datos y cálculo HA–worker](mushroom-map-compute-data-placement-es.md)
define copias locales de GIS/DEM/SoilGrids en los workers que las necesitan.
HA atiende ediciones acotadas; la preparación de lotes y el nuevo mapa a demanda
se ejecutan en worker. Este lector es compartido por ambas máquinas, no exclusivo
del coordinador. La implementación operativa compartida sigue pendiente.

## Explicación sencilla

La Raspberry no necesita leer el país para responder por un punto. Necesita una
agenda que indique en qué archivo y en qué pequeña ventana están sus datos.
SQLite será esa agenda. Un lector que permanece cargado abrirá los archivos
necesarios, reutilizará una cantidad limitada de datos recientes y devolverá
solo el resultado. El mapa pedirá nueve capas para pH; el contexto hídrico pedirá
las 54 de retención. No se pedirá siempre el conjunto de 63.

Las microáreas seguirán guardando su resumen de suelo. El Predictor consume ese
resumen: no hay que abrir los mapas de suelo cada vez que predice. Guardar un
nombre debe reutilizarlo; cambiar el polígono requiere otro resumen. La edición
pequeña puede resolverlo en HA; la preparación masiva corresponde al worker con
mapas locales. Si falta suelo, se explicará la ausencia y se conservará el resto
de la información.

La propuesta cambia deliberadamente la obtención automática: guardar o hacer
clic consultará solo datos locales. No descargará para rellenar huecos ni
arrancará una ampliación. Una futura ampliación será mantenimiento explícito de
la misma base y requerirá una necesidad nueva. Durante la transición el lector
antiguo permanece operativo hasta la aceptación de la migración.

## Hechos verificados y alcance de esta revisión

Leídos completos `docs/codex-start-here.md` y `docs/active-context.md`.
Se consultó primero el MCP de arquitectura y símbolos. `list_projects` no está
expuesto entre las herramientas de esta sesión; `get_architecture` confirmó
`RainmapperHA`. Algunas posiciones del grafo están desactualizadas; las líneas
citadas abajo se contrastaron con los archivos actuales mediante `rg` y `sed`.

| Fuente actual | Comportamiento comprobado |
|---|---|
| `rainmapper_core/mushroom_soilgrids.py:141`, `:200`, `:270` | El manifiesto exige exactamente 54 capas; se carga y valida completo. No admite añadir pH sin adaptación. |
| Mismo archivo, `:802`, `:1254` | Cada agregación comprueba SHA completos de originales y normalizados de las teselas necesarias; puede releer un original compartido varias veces. No es una lectura de todos los TIFF nacionales. |
| Mismo archivo, `:1199` | Ya hay lectura por ventanas, pero cada ventana ejecuta `gdal_translate`, serializa XYZ y construye un diccionario de píxeles. Para una tesela y las 54 capas, el bucle programa 54 ejecuciones de lectura; es un recuento del código, no una medición. |
| Mismo archivo, `:429`, `:1254` | La proyección usa `gdaltransform`; las intersecciones de píxel se vuelven a calcular por profundidad y cuantíl. |
| Mismo archivo, `:1134` | Un contexto se considera vigente por contratos, versión, geometría y estado. Esta función no abre rásteres ni verifica el manifiesto o sus hashes. Acepta `complete`, `partial` y `no_coverage`. |
| `rainmapper_core/mushroom_ml_biology_v3.py:446` y `mushroom_ml_area_weather_runtime.py:122` | Se carga `derived_context.soilgrids_water` y se pasa al cálculo hídrico. |
| `rainmapper_core/mushroom_soil_water_state.py:58` | El cálculo físico exige contexto `complete`. Ausencia no significa suelo seco. |
| `rainmapper_core/mushroom_soilgrids_reconciler.py:46`, `:134` | La autocura reutiliza contextos vigentes; intenta resolver los demás con `ensure_missing=True`. Parte de su telemetría de lectura es una estimación desde el manifiesto, no contadores reales de E/S. |
| `rainmapper-app/Dockerfile:1`, `:13` y `requirements.txt` | La receta usa Python 3.11 e instala `gdal-bin`; requirements no declara bindings GDAL. No se ha verificado aquí el entorno efectivo de los contenedores. |

Se leyeron únicamente metadatos locales de adquisición para diseñar el índice:
`acquisition-plan.json` ocupa 3.596.115 bytes y relaciona cada capa/tesela con un
TIFF reutilizado o con una ventana dentro de un bloque nuevo; `validation.json`
ocupa 414.801 bytes y conserva tamaños y huellas. Rutas bajo
`mushroom-map-GIS/soilgrids-shared/`. No se ejecutaron sus scripts ni se releyeron
los rásteres. Los 1.948 archivos y 795.522.040 bytes son la evidencia de la
adquisición ya cerrada, no un inventario repetido en esta revisión.

Lectura JSON del catálogo actual
`docker-data/mushroom-data/mushroom_known_sites.json`: 34 áreas, 66 microáreas y
66 bloques con estado declarado `complete`. Esto no revalida sus píxeles ni su
compatibilidad con un lector que todavía no existe.

## Alta y cambio de áreas y microáreas

| Operación actual | Recorrido verificado | Propuesta tras migrar |
|---|---|---|
| Crear/guardar área en Setales | `web_server.py:23381`: guarda el área sin llamar a SoilGrids. | Mantenerlo; cambiar el área padre no recalcula automáticamente sus microáreas. |
| Crear/editar área desde observaciones/perfiles | `web_server.py:24034`, `:24079`: guarda geometría/contexto geométrico, sin refresco SoilGrids. | Mantenerlo. Un futuro informe de suelo de área será una consulta independiente. |
| Crear/guardar microárea en Setales | `web_server.py:23409`, `:23429`: refresca DEM y SoilGrids antes de guardar. | Mismo resumen y persistencia, con lectura local acotada. |
| Editar geometría de microárea desde observaciones/perfiles | `web_server.py:24028`: refresca SoilGrids tras cambiar el polígono. | Compartir el mismo adaptador; impedir publicar el contexto de la geometría anterior como vigente. |
| Crear microárea desde ese flujo | `web_server.py:24116`: refresca antes de guardar. | Mismo comportamiento local y estados que en Setales. |
| Editar solo metadatos | `web_server.py:11541`: reutiliza el contexto si la geometría no cambia y es vigente. | Cero aperturas de TIFF; no renovar fechas ni hashes del contexto. |
| Quitar geometría | Misma función: retira el bloque SoilGrids si cambió la geometría. | Conservar esa semántica, sin borrar DEM u otros campos por un fallo SoilGrids. |
| Autocura antes de reconstrucción | `mushroom_soilgrids_reconciler.py:134`, llamada desde `web_server.py:14203`. | Trasladar la preparación pesada al worker con copia local; HA valida deltas y conflictos antes del snapshot final. Reutilizar contextos vigentes. No iniciar reconstrucciones por activar el lector. |
| Materialización/gestión CLI | `scripts/materialize-micro-area-soilgrids.py:93`, `scripts/manage-soilgrids-cache.py:59`. | Separar lectura, importación y verificación; no dejar una ruta accidental que amplíe la caché antigua. |

Hoy `resolve_geometry_context` (`mushroom_soilgrids.py:1149`) agrega primero;
si queda `pending` y `ensure_missing=True`, llama a `ensure_geometry_cache` y
agrega otra vez. Esta última puede descargar mediante `ensure_tile`. Un contexto
`partial` o `no_coverage` vigente no provoca por sí solo una nueva descarga.

La futura política de mapas locales debe cambiar conjuntamente el refresco y
la autocura: cambiar solo el valor por defecto del refresco dejaría la autocura
descargando y calculando en HA. Local significa en la máquina ejecutora: HA
para edición pequeña, worker para preparación de lotes y nuevo mapa.
Para errores o límites de recursos se conserva `pending` y un motivo específico;
para ausencia conocida, `no_coverage`; para datos utilizables incompletos,
`partial`. Un archivo esperado ausente/corrupto es un error de almacenamiento,
no evidencia científica de falta de cobertura. Reintento explícito, sin bucle
de trabajos ni descarga silenciosa. Los textos nuevos de UI tendrán las tres
traducciones exigidas por el proyecto.

## Índice local y normalización sin duplicar rásteres

Nombres de tablas, interfaces y límites siguientes son **propuestos**, no código
existente. Base SQLite por generación, solo lectura durante las consultas:

| Tabla propuesta | Contenido mínimo |
|---|---|
| `generations` | Identificador de publicación local, versión del esquema y de políticas; identidad de la vista de retención separada de la de pH. |
| `sources` | Snapshot de adquisición, metadatos/atribución y edición científica si se conoce; no confundir una fecha de descarga con una edición homogénea. |
| `assets` | Una fila por archivo físico: ruta relativa, tamaño, SHA ya registrado, procedencia, dimensiones, tipo, geotransformación y CRS confirmado. |
| `tile_layers` | Clave única `(view_id, coverage_id, tile_x, tile_y)`, referencia al archivo, banda y ventana `(xoff, yoff, width, height)`. Índice B-tree sobre esa clave. |
| `legacy_refs` | Referencia de manifiesto/capa/tesela/hash antiguos a archivo y ventana equivalentes, sin cambiar el hash de un contexto existente. |

La cuadrícula regular permite calcular la tesela directamente; no hace falta
añadir R-tree para puntos. Los polígonos enumeran teselas intersectadas con
límite de trabajo, nunca el país entero. El índice devuelve solo las filas de
las capas pedidas. Las URLs, cabeceras WCS y auditoría detallada permanecen en
evidencia externa al contrato de consulta; el índice guarda referencias pequeñas.

Importador separado y por lotes: leer el plan y los comprobantes existentes una
vez, deduplicar archivos y construir una candidata sin tocar el catálogo activo.
No generar 7.119 TIFF ni un VRT nacional que obligue a descubrirlos al abrirlo.
Los bloques nuevos ya agrupan varias teselas: sumar el desplazamiento de la
tesela al de la ventana consultada, conservando su origen superior izquierdo.
Los normalizados antiguos se referencian directamente.

Para los WCS sin CRS declarado, normalizar **metadatos en el índice** con el CRS
confirmado por solicitud y cuadrícula. El lector transforma al CRS registrado
y lee offsets; no necesita reescribir píxeles. No asignar un NoData global a los
TIFF. Una vista auxiliar pequeña solo se justificaría si una herramienta futura
la necesita; no forma parte de cada clic. Comprobar offsets y cabeceras durante
la importación dirigida, sin estadísticas ni auditoría nacional nueva.

Identidad e integridad se separan del camino de consulta:

- Los SHA existentes identifican contenido; importación/promoción conserva su
  evidencia. Una copia a otro soporte exige verificar la transferencia una vez,
  por archivo físico, no por referencia ni por consulta.
- Generaciones publicadas inmutables; la consulta fija una generación hasta
  terminar. Publicar una candidata mediante sustitución atómica de un puntero
  pequeño; nunca modificar el SQLite que ya tienen abierto otros lectores.
- Registrar al instalar tamaño y metadatos locales del archivo. Comprobar `stat`
  de los archivos tocados antes de servirlos, incluyendo resultados cacheados;
  cambio inesperado invalida la entrada y devuelve error. No rehash automático.
  Tamaño/mtime no prueban integridad de bytes: corrupción silenciosa sin cambios
  detectables requerirá verificación explícita y dirigida por un motivo nuevo.
- No enumerar directorios, cargar JSON nacionales, hacer checksums GDAL ni
  hashes completos de TIFF o manifiestos durante la consulta.

## Lector residente, ventanas y límites

Elección inicial: módulo de `rainmapper_core` con bindings `osgeo.gdal` y OSR,
importados de forma diferida. Instancia residente por máquina ejecutora, atendida
por un único hilo propietario de SQLite, transformaciones y datasets. En HA
atiende ediciones pequeñas; en worker, preparación remota y consultas del mapa
sobre su réplica. No crear lectores por petición, modelo ni coordinador.
Los subprocesos de reconstrucción deben acceder al lector del worker mediante
un servicio local o serializar sus fases con presupuesto único; elegir y probar
ese adaptador antes de integrarlos. Las utilidades CLI comparten el módulo en
pruebas/mantenimiento aislados. El límite no se multiplica por proceso/carril.

Un hilo propietario evita compartir datasets entre hilos. GDAL documenta límites
de concurrencia sobre el mismo dataset; este diseño no depende de capacidades
especiales de versiones recientes. [Documentación GDAL de concurrencia](https://gdal.org/en/stable/user/multithreading.html).

API propuesta: consulta por punto/celda y conjunto explícito de capas; agregación
por geometría con política de retención; respuesta pequeña con valores, estado,
cobertura y referencias. No admitir rutas arbitrarias, URLs remotas, matrices
nacionales ni producto cartesiano punto × especie × día × modelo.

Por punto: proyectar una vez, resolver tesela y celda, consultar índice y leer
ventanas 1×1. El TIFF puede descomprimir un bloque interno completo: una ventana
no equivale a dos bytes de E/S. Por polígono: recorrer bloques de como máximo
256×256, calcular pesos de intersección una vez por bloque y reutilizarlos en
las profundidades/cuantiles. Mantener solo tres propiedades, máscara y pesos
del bloque actual; acumular sumas, superficie, conteos y extremos. Sin XYZ,
diccionarios por píxel ni cubo de 63 capas del polígono entero. La API GDAL permite
leer offsets y dimensiones y reutilizar buffers. [API ráster GDAL](https://gdal.org/en/stable/api/python/raster_api.html).

No remuestrear, interpolar ni sustituir polígonos por centroides. Conservar
cuadrícula, ejes, tratamiento de agujeros y ponderación de bordes; validar que la
transformación OSR reproduce el recorrido actual de `gdaltransform`.

Presupuesto inicial de ingeniería, **no mediciones ni garantía de RAM total**:

| Recurso | Límite candidato |
|---|---:|
| Lecturas activas / pendientes | 1 / 4; rechazar antes de encolar si se supera |
| Petición de suelo / vértices | 256 KiB / 4.096, comprobados antes de copiar o proyectar |
| Celdas candidatas por agregación interactiva | 65.536; presupuesto de operaciones geometría×celdas y plazo comprobados incrementalmente |
| Bloques GDAL | 16 MiB globales en el proceso |
| Datasets abiertos | 64 máximo, con cierre LRU |
| Buffers temporales, pesos y máscaras | 8 MiB en total, contando copias NumPy |
| Páginas SQLite | 4 MiB; sin mmap ilimitado ni resultados nacionales en memoria |
| Caché de resultados | 2 MiB y 256 entradas, el primer límite que se alcance |
| Respuesta individual | 64 KiB; estimar referencias antes de construirla |
| Metadatos y colas propios | 2 MiB; conteos y evidencias detalladas fuera de respuestas |
| Objetivo de memoria adicional máxima del lector | 96 MiB RSS sobre el coordinador sin lector, por medir también en cgroup |

Los 32 MiB de caches/buffers explícitos no incluyen librerías, handles, allocators
ni caché del sistema. `GDAL_CACHEMAX` controla bloques, no todo el proceso; fijar
el presupuesto al inicializar, sin usar el porcentaje automático de RAM.
[Opciones GDAL](https://gdal.org/en/stable/user/configoptions.html).
Evitar otra caché Python de los mismos bloques. Clave de resultados:
generación/vista + celda o hash geométrico + capas + política de agregación;
nunca especie o fecha para suelo estático. Cachear ausencias conocidas; no
convertir errores transitorios en ausencias persistentes. Invalidación por
cambio explícito de generación o archivo, sin sondeo nacional.

Plazo candidato: 1 s de servicio por punto y 5 s por agregación interactiva;
cancelación entre bloques y capas. Son objetivos a medir, no tiempos prometidos.
Una operación nativa ya iniciada puede terminar después del plazo: el hilo no
se mata ni se lanza otro lector; se descarta el resultado cancelado. Deduplicar
peticiones idénticas con límite también de suscriptores. Las consultas grandes
quedan pendientes con motivo, sin simplificar geometría ni lanzar un job.
Contrastar estos topes con el tamaño de las 66 geometrías antes de fijarlos;
si excluyen casos actuales, revisar el algoritmo y el fraccionamiento antes
de elevarlos. No declararlos requisitos micológicos.

Empaquetado pendiente: construir bindings contra la misma libgdal de la imagen,
en una etapa de build; comprobar Python/NumPy/GDAL y ambas arquitecturas. No
suponer que instalar `gdal-bin` hace importable `osgeo` desde `/usr/local` Python.
El worker que prepare contextos o sirva el mapa necesita también estos bindings
y sus mapas locales. Sus consumidores de contextos ya preparados mantienen la
importación diferida y no abren rásteres innecesariamente. Si falla la prueba
de bindings, detener esa fase y revisar el backend; no volver silenciosamente
al CLI por capa. El presupuesto anterior es el candidato SoilGrids de HA;
medir aparte el total del worker con DEM, vectores, meteorología y modelos.

## Compatibilidad de valores, ausencias e identidad

Dos políticas explícitas sobre los mismos datos:

1. **Retención compatible con el Predictor.** Conservar seis profundidades,
   tres cuantiles, mm/m, intersección común de las tres propiedades y exclusión
   de valores `<=0` o `>1000` de `aggregate_geometry`. Conservar conteos,
   extremos, redondeo a seis decimales, mínimo de cobertura y umbral `0.999`
   para `complete`. Son reglas observadas del código, no reglas nuevas.
2. **Descripción del mapa.** pH: tres profundidades, entero dividido por diez,
   cero como sin estimación según la evidencia ya guardada; no inventar pH.
   Retención: mantener valor bruto y motivo de exclusión de la política del
   Predictor. No declarar que todo cero sea NoData científico; el mapa no debe
   reinterpretar como suelo seco una celda excluida ni rellenar huecos.

La migración no cambia fórmulas físicas, contador de días secos, features ni
selección del Predictor. Añadir pH no modifica `required_coverage_ids` ni los
manifiestos v1 que siguen usando herramientas antiguas.

Conservar íntegros los contextos existentes y sus hashes. Para comprobar
equivalencia, el índice tendrá una vista compatible congelada con el manifiesto
de retención original y sus hashes de tesela. Su `manifest_hash` se calcula una
vez al importar con la misma canonicalización, no en cada agregado. Cambiar la
ruta física no altera la identidad. No sustituir el hash lógico de una tesela
antigua por el del bloque grande que pueda contenerla.

Si un contexto conserva el hash de otro manifiesto histórico, localizar esa
evidencia antes de afirmar equivalencia de procedencia; no inventar el
manifiesto ni asignarle el hash del actual. El contexto se conserva intacto
mientras se resuelve la discrepancia.

Las zonas nuevas necesitan procedencia honesta: una vista de retención con
identificador de snapshot registrado que enumere sus fuentes y deje explícito
si combina adquisiciones. Mantener el contrato de valores v1 si se conserva
íntegra su semántica, pero adaptar la validación de identidad para aceptar solo
vistas registradas, además del contexto legado. No reutilizar ciegamente la
constante `SOURCE_VERSION` para llamar homogéneos a datos nuevos. Si el schema
o consumidores no permiten esa extensión sin ambigüedad, introducir un contrato
nuevo en una fase separada, con lector dual; esa decisión bloquea la promoción,
no se resuelve falsificando la versión. Probar específicamente este punto antes
de persistir contextos de zonas nuevas.

El cambio de generación de pH no invalida retención. Contextos ya persistidos
conservan su snapshot; un cambio científico futuro no los actualiza de manera
automática. El hash de un contexto recalculado con otra procedencia puede cambiar
aunque sus números coincidan: registrar la causa y comprobar sus consumidores.
Para entradas y procedencia idénticas se exige igualdad del contexto salvo
`generated_at`, incluido `context_hash`. Diferencias al redondear no se aceptan
como equivalencia: corregir el orden/acumulación o mantener el recorrido
compatible. Las diferencias internas de coma flotante son diagnóstico, no
permiso para cambiar el resultado serializado.

## Implementación por fases y puertas de aceptación

| Fase futura | Trabajo | Evidencia para avanzar |
|---|---|---|
| 1. Índice candidato | Importador de metadatos, referencias antiguas, snapshots, validación de rutas/offsets y publicación atómica. Sin cambiar raíces operativas. | Sin duplicación de rásteres; identidad compatible; pruebas de generación incompleta y rollback. |
| 2. Núcleo de lectura | Bindings, hilo propietario, ventanas, pesos por bloque, límites, métricas y cancelación. | Pruebas sintéticas y lectura local dirigida; cero red/subprocesos/hashes de archivos en las consultas nuevas. |
| 3. Compatibilidad y distribución | Adaptador v1, fuente de zonas nuevas, consumidores físicos, réplica del worker y pruebas diferenciales contra contextos guardados. | Sin cambios numéricos inadvertidos; mapas instalados una vez y contextos vigentes reutilizados sin relectura. |
| 4. Integración local | Adaptar Setales, observaciones/perfiles, preparación remota previa al snapshot y CLI; lectura en la máquina ejecutora. | Altas/cambios aislados, deltas del worker validados en HA, conflictos y errores seguros; sin lote pesado en la RPi4. |
| 5. Medición y aceptación local | Reconstruir HA local y worker de pruebas desde el mismo worktree cuando se autorice esta fase; comprobar código efectivo y recorrer el circuito aplicable. | Compatibilidad y recursos documentados; aceptación expresa antes de cualquier release real. |
| 6. Migración autorizada | Instalar índice/base en almacenamiento GIS fuera de backups ordinarios, verificar transferencia y cambiar lector/ruta deliberadamente. | Contextos preservados, consultas correctas, rollback probado; pruebas de hardware bajo autorización específica. |

El trabajo de esta sesión termina en documentar y explicar el plan. Las fases
son futuras: no se lanzan trabajos, builds o servicios ahora. Si la integración
afecta contratos o artefactos de entrenamiento/predicción, la fase local debe
recorrer mediante el worker asignación, reconstrucción, entrenamiento base y
multiversión, recepción/promoción y precálculo/activación, según las reglas del
proyecto. Un test unitario no sustituye esa aceptación. Preservar y comprobar
la URL persistida antes y después de cualquier operación futura sobre un worker.

## Pruebas de compatibilidad previstas

- Índice: referencias reutilizadas y ventanas de bloques grandes; solapes con
  precedencia explícita de la vista; borde entre teselas; generación incompleta,
  cambio atómico, archivo ausente/modificado y ruta fuera de raíz. Nada de
  fallback a otra edición o a la tesela más cercana.
- Ráster sintético pequeño: valores conocidos por celda, orientación norte/sur,
  offsets, CRS, bordes exactos, Polygon/MultiPolygon, agujeros, cobertura parcial,
  todo ausente, pH cero y retención cero. Las mismas pruebas con archivos
  antiguos y el nuevo índice; sin simular la propia respuesta del lector.
- Catálogo: una pasada dirigida de las 66 geometrías contra los contextos
  persistidos, en memoria o salida candidata separada. Comparar valores,
  conteos, cobertura, extremos, contratos y hashes; si hay divergencia, usar
  el lector antiguo solo en esos casos para distinguir un contexto histórico
  diferente de una regresión. No recalcular el país ni escribir el catálogo vivo.
- UI: alta/cambio en ambos puntos de entrada, cambio de nombre, cambio de área
  padre sin cambiar polígono, retirada de geometría, área sin microáreas y
  consulta fuera del ámbito. DEM, observaciones y campos ajenos intactos.
- Concurrencia: dos ediciones de la misma microárea, resultado tardío tras otra
  geometría, cancelación, cola llena y cambio de generación en vuelo. Publicar
  solo si la identidad de la fila leída sigue siendo la actual; nunca restaurar
  todo el catálogo para resolver un conflicto.
- Consumidores: contexto `complete` con salida física idéntica bajo una serie
  meteorológica fija pequeña; `partial/no_coverage/pending` sin features físicas
  inventadas; carga de contextos nuevos y antiguos en HA/worker; hashes de
  entradas sin invalidaciones por añadir pH o mover archivos.
- Aislamiento: denegar red y creación de subprocesos al lector de pruebas;
  contador de bytes hasheados de ráster/manifiesto igual a cero. Verificar
  escrituras cero durante lecturas, incluso `.aux.xml`, WAL o estadísticas.

Ampliar pruebas existentes, no repetirlas ahora: `tests/test_mushroom_soilgrids.py`
(agregación, manifiesto, geometría y DEM),
`tests/test_mushroom_soilgrids_reconciler.py` (reutilización/fallos/parcial),
`tests/test_web_server_auth.py:6329` (refresco por geometría), `:10975` y `:11104`
(promoción y conflicto), y las pruebas físicas/área pertinentes al integrar.
Los tests actuales no validan por sí solos el lector propuesto.

## Medición de memoria, disco y tiempos

Instrumentar el lector con contadores reales. Sustituir la estimación de
`_aggregation_counters` en el camino nuevo: número de archivos abiertos,
ventanas solicitadas, buffers y caché, aciertos/expulsiones, bytes hasheados,
cola, cancelaciones y tiempo de índice/proyección/lectura/agregación. No llamar
«bytes de disco» a bytes Int16 solicitados ni a ventanas teóricas descomprimidas.

Matriz pequeña y reproducible, primero local, posteriormente en RPi4 equivalente
o HA real solo con permiso para la prueba acotada:

| Caso | Ejecución futura y objetivo |
|---|---|
| Reutilización de contexto vigente | Guardar metadatos y autocura simulada: cero TIFF, red, hashes de archivos y cambios de contexto. |
| Punto pH / retención / ambas | 9 / 54 / 63 capas; primera consulta, misma celda, vecina en mismo bloque y otro bloque. Contabilizar aperturas y descompresión, no suponerla. |
| Geometrías | Pequeña, mayor del catálogo, entre teselas, agujeros, parcial y sin cobertura; registrar vértices y celdas tocadas. |
| Persistencia de carga | Secuencia fija de 200 puntos, incluyendo repeticiones, con 1, 2 y 4 clientes. RSS y handles deben estabilizarse al llenarse las caches. No ampliar a una malla nacional. |
| Límites y errores | Petición demasiado grande, 5 pendientes, cancelación, archivo ausente y lector no disponible: rechazo acotado, sin trabajos ni pérdida de datos. |

Separar arranque frío del lector, primera apertura y caché caliente. Un proceso
nuevo no garantiza disco frío: registrar caché del SO no controlada. No vaciar
cachés del kernel ni reiniciar servicios de una RPi compartida para obtener una
medida. Para p50/p95 usar al menos 100 consultas registradas por grupo; para
geometrías singulares informar tiempos individuales, no percentiles ficticios.

Medir RSS base/pico y, en Linux, PSS cuando esté disponible, cgroup
`memory.current`/pico, fallos de página, CPU usuario/sistema y E/S de proceso y
contenedor antes/después. `tracemalloc` solo diagnostica Python: no contabiliza
por sí solo buffers nativos de GDAL/NumPy. Registrar herramienta, unidades,
intervalo de muestreo y disponibilidad; no sumar RSS de procesos como PSS.

Medir bytes lógicos y asignados por categoría: TIFF existentes, índice, staging,
logs, resultado candidato e imagen. Objetivos iniciales: índice activo ≤16 MiB,
dos generaciones de índice ≤32 MiB más staging medido; cero copia adicional
de TIFF para normalizar metadatos; cero escrituras por clic. El coste de una
eventual transferencia a HA se presupuestará antes, contando el espacio antiguo
que se conserva. Los 12 GiB de la adquisición previa no son un nuevo requisito
de disco del lector. Reportar también incremento de imagen por los bindings.

Objetivos candidatos en el hardware objetivo: p95 de punto caliente ≤250 ms,
p95 de primera consulta en proceso residente ≤1 s y geometrías del catálogo
≤5 s; RSS adicional pico ≤96 MiB, sin crecimiento sostenido ni swap atribuible
al lector. Registrar ocupación de colas y latencia total además del tiempo de
servicio. Si no se cumplen, revisar aperturas, pesos, buffers y empaquetado;
no aumentar límites ni afirmar que el Mac demuestra rendimiento de la RPi4.

El informe guardará commit/diff ejecutable, generación de datos, versiones
efectivas, arquitectura, RAM/almacenamiento, carga coexistente, casos y resultados.
No hay todavía medidas de este lector ni del hardware real. Una prueba funcional
en HA local valida integración; una medición en Mac no certifica recursos RPi4.

## Conservación y reversibilidad

No borrar, mover ni cambiar referencias de la caché antigua durante el diseño.
La conmutación futura conservará contextos vigentes; cualquier actualización
se hará por fila con comprobación de identidad, nunca restaurando observaciones
o catálogos completos. Rollback del lector/ruta mantiene las ediciones nuevas;
contextos de una vista no admitida por el lector antiguo se conservan como datos
y requieren tratamiento explícito, no borrado. Probar este caso antes de migrar.

No crear una tercera copia nacional para rollback. La caché antigua ya conservada
es el material de retorno durante la transición. Los 30 días siguen siendo una
propuesta, no una fecha de borrado: retirar datos requiere decisión posterior
y evidencia de que no existen referencias necesarias. Este documento no autoriza
descargas, reauditoría, entrenamiento, precálculo, cambios de coordinador ni HA.
