# Archivo de contexto anterior al cierre del 28/09/2026

Snapshot histórico: contiene estados pendientes ya superados. Para el estado de
continuidad usar [active-context](../active-context.md), no este archivo.

# Contexto activo — HA 0.2.330 publicada; instalación pendiente (28/09/2026)

Leer primero [codex-start-here.md](codex-start-here.md). Este documento basta para
retomar; [todo.md](todo.md) amplía prioridades. No reconstruir sesiones leyendo
informes históricos. Los antecedentes completos se conservaron en el
[archivo del repaso del 27/09](reports/session-context-before-refresh-2026-09-27.md).

## Estado y siguiente paso

- **HA 0.2.330 publicada tras completar y auditar el circuito local.**
  Completada la coherencia entre mapa, recuperación puntual, microáreas por
  muestreo y reconstrucción: MFE25 para árboles; MVC50 para bosque/sustrato;
  alternativas Cobertes/geología por campo. La reconstrucción usa un único
  lector por trabajo y el dataset preparado, conservando evidencia revisada.
  Dataset local activado en `docker-media/rainmapper/geography`: 14 referencias,
  configuración 1.997 bytes. El worker ya tenía los 13 assets en caché; no se
  duplican ni transportan de nuevo. Se reutiliza el transporte existente.
  HA local/worker reconstruidos y recreados tras verificar reposo. Paridad
  SHA 17/12 archivos, ambos coordinadores y hashes intactos. Smoke 1.854 pruebas,
  55 omitidas; 87 dirigidas; tres puntos reales y microárea coherentes en ambas
  imágenes. Evidencia `docker-data/territorial-validation/coherent-*` y `parity.json`.
  **Circuito terminado:** 517 observaciones con política nueva; 792/792 ajustes
  sin fallos y cinco versiones promovidas; precálculo 28/09–04/10 activo en HA
  local y confirmado por worker. SQLite íntegro, recibos coincidentes y limpieza
  completa. Duraciones: reconstrucción 1:06, base 0:24, multiversión 10:26,
  precálculo 10:47. Auditoría `operational-cycle-audit.json` en la misma carpeta.
  Publicación autorizada por «pues publica»; script terminado con código 0 y
  tags `0.2.330`/`latest` verificados con el mismo digest y amd64/arm64.
  Digest `sha256:e932c63ad4d207c64f8e2a634264a2ca5efe96ac782a73ba96a2f7b57e98b8fb`.
  **Siguiente paso:** el usuario instala HA; después activar metadatos en real.
  No repetir el ciclo local.

- **HA real:** sólo índice MVC50 copiado y verificado (479.780.864 bytes).
  Aún no registrado: `/media/rainmapper/geography/CURRENT.json` conserva
  `local-20260914` en la última comprobación. Faltan instalación compatible y
  activación de metadatos. No borrar MVC50 original: queda el inventario de
  mantenimiento de mapeos por auditar/adaptar.
  [Preparación](reports/release-ha-0.2.330-preparation-2026-09-28.md),
  [política y procedimiento](mushrooms/territorial-source-policy-es.md).

- **Cambio incluido en 0.2.330:**
  Comprobar predicción consulta todas las especies y enmarca la observada en azul;
  la trazabilidad sigue vinculada a la especie observada y día seleccionado.
  42 pruebas dirigidas y navegador correctos (77 consultas, 25 de histórico).
  HA local y worker reconstruidos/recreados; paridad SHA de los tres archivos HA
  afectados y contrato del worker, HTTP local 200. Ambos coordinadores conservados.
  Se esperó a que los canales del worker estuvieran libres antes de recrearlo.
  No requiere entrenamiento/precálculo. Logs en
  `docker-data/observation-all-species-{browser,ha-build,worker-build}.log`.

- **HA 0.2.329 publicada, instalación pendiente:** Comprobar predicción desde la
  ficha de observación, debajo de Cómo llegar. Abre la ficha completa del mapa
  para las coordenadas/especie/fecha registradas: siete días, IFF/modelo,
  meteorología, SMI y terreno; añade abundancia observada y vuelta a la ficha.
  Conserva fecha global del mapa. Añade trazabilidad del ID por modelo/día mediante
  SQLite generado al ajustar los modelos V2–V6; modelos anteriores se identifican
  como sin trazabilidad. Bocadillo con punta en todos los anclajes y altitud guardada
  entre Fecha y Área. Worker reconstruido y dos ajustes sintéticos comprobados,
  con ambos coordinadores conservados. El entrenamiento local del usuario terminó:
  lote `operational_20260927T184246Z`, 792/792 ajustes, cero fallos, verificado y
  cinco versiones instaladas. Índice SQLite de 573.440 bytes, 792 modelos y
  226 conjuntos completos; tamaño, SHA y `quick_check` correctos.
  101 pruebas dirigidas de trazabilidad/transporte, navegador y consulta HTTP local
  correctos; adición de altitud comprobada con 37 pruebas y navegador.
  Smoke de release: 1.838 pruebas / 52 omitidas, OK. HA local reconstruida/recreada
  con etiqueta 0.2.329, HTTP 200 y paridad SHA de 19 archivos; nueve archivos del
  worker coinciden, sin reconstruirlo de nuevo ni cambiar coordinadores.
  Ficha simplificada posteriormente por petición del usuario: especie, fecha,
  abundancia y SÍ verde / NO rojo; sin párrafos de explicación. Por acuerdo final
  del usuario se mantiene el entrenamiento actual: evaluación previa y ajuste final
  con todas las filas elegibles. No se implementó interruptor ni reparto nuevo.
  Tags/digest/plataformas GHCR verificados y publicación autorizada por el usuario.
  [Release](reports/release-ha-0.2.329-2026-09-27.md).
  [Evidencia](reports/observation-prediction-check-local-2026-09-27.md).

- **HA 0.2.328 publicada**, validada en local y autorizada por el usuario para
  probar en móvil. Tabla de observaciones aprovecha el panel y ficha del mapa
  compacta con foto y Cómo llegar. Smoke 1.831 pruebas / 52 omitidas OK; tags
  y plataformas verificados. Instalación pendiente a cargo del usuario.
  [Release](reports/release-ha-0.2.328-2026-09-27.md).

- **HA 0.2.327 instalada y funcionando**, confirmado por el usuario. Incluye las
  correcciones locales de casillas GBIF y notas DEM.
  Smoke 1.831 pruebas / 52 omitidas OK; tags y plataformas verificados.
  [Release](reports/release-ha-0.2.327-2026-09-27.md).

- **HA 0.2.326 instalada y funcionando**, confirmado por el usuario el 27/09.
  Añade coordenadas, incertidumbre y foto ampliable
  a las fichas del mapa; incorpora los scripts de memoria ya validados. Tags y
  plataformas verificados; [release](reports/release-ha-0.2.326-2026-09-27.md).

- **Comprobación anterior de HA real 0.2.325**, confirmada entonces por el
  usuario y revalidada en
  `/Volumes/share/rainmapper/diagnostics/runtime_state.json` durante este repaso:
  `app_version=0.2.325`, arranque `2026-09-26T20:11:03.600Z`.
- **Comprobación anterior del worker 1.1.6, previa a la trazabilidad**, reconstruido
  y arrancado el 27/09 por petición del usuario,
  sin nueva release HA. Imagen efectiva
  `sha256:79440107723a685b3e8eb32b2161a2ec0f9224f02cc7a09339101a4553eaa747`.
  122 archivos Python en paridad; 25 pruebas dirigidas correctas dentro de la
  imagen. Al verificar el arranque estaba `running/healthy`, `idle`, sin trabajos.
  Ese estado puntual no permite presumir que continúe libre: **revalidar antes
  de operarlo**, aunque los trabajos comprobados hayan terminado.
- Coordinador primario conservado: `http://100.111.77.48:8100`; adicional:
  `http://rainmapper-ha-ui:8100`. Identidad `worker_1a9a232c20fe2ee2`, M1 Personal.
  Configuración de ambos e identidad idénticas por hash antes/después; acceso
  autenticado a ambos correcto al arrancar. No cambiar destinos ni credenciales.
- **Ciclo del usuario completado y verificado el 27/09:** reconstrucción 2:05,
  V0 0:27, multiversión 10:04 (792/792 ajustes, 0 fallos); cinco versiones
  instaladas del lote `operational_20260926T223720Z`. Precálculo 9:39, revisión
  261 activa en HA/worker para 27/09–03/10, SHA idéntico leído en ambos SQLite.
  Worker sin reinicios/OOM, ambos carriles libres al comprobar. Pico cgroup
  6,86 GiB desde arranque, no RSS aislado ni pico atribuible a una fase.
  Hubo timeouts de comunicación recuperados. Codex no lanzó trabajos.
  [Resultados, tiempos y límites](reports/worker-evaluation-memory-2026-09-27.md).
  Rovelló/Els Ports reexaminado: RF–V3 da IFF 37 toda la semana; ver abajo.
- Pendientes aplazados: estado huérfano de HA tras perder worker; duración del
  precálculo (9 → 11 minutos). Ambos en TODO; no están corregidos por el rebuild.

## Corrección de memoria del worker

El contenedor anterior murió por OOM a las 22:58:59 del 26/09 (20:58:59 UTC),
salida 137. El trabajo `worker_job_XpH0Q6p3EQaUxiyF` llevaba unos ocho minutos,
aunque HA seguía mostrando `running`, 46 %, con lease caducada. Ese era el estado
observado durante el incidente, no el del nuevo contenedor ni una cola vigente.
Reconstrucción y V0 anteriores habían terminado; la caída ocurrió durante V6.

`biology-v5-lag.json`: 528.821.763 bytes, 3.493 muestras. No se recortan los
365 días ni el SMI. V2–V5 y V6 ahora comparten la misma entrada por contrato:
cargar `fixed`, evaluar sus consumidores, liberar; después lo mismo con `lag`.
Se comparte normalización por fuente y se conserva el orden final de resultados.
No hay caché permanente. El entrenamiento final es otro proceso con su propia
lectura; no confundir esta mejora con una única lectura en todo el pipeline.

Medición con archivos reales, **sin ajustar modelos**: pico RSS de carga V6
3,99 → 1,71 GiB (−57 %); lecturas por archivo 3 → 1. Las 25 pruebas incluyen
igualdad exacta de resultados sintéticos para 30/60/90 y 365 días. No demuestra
el pico completo ni garantiza por sí sola que el trabajo entero evite OOM.
[Implementación, medición, rebuild y límites](reports/worker-evaluation-memory-2026-09-27.md).

## Meteocat: reparación ya aplicada; preservar datos nuevos

HA 0.2.325 corrige el recorte del primer día UTC que sobrescribía lluvia y otros
campos con horas parciales. Reparación aplicada en real el 26/09 a las 20:09 UTC,
con add-on parado por el usuario: 6.700 filas / 24.034 celdas de 01/08–25/09/2026,
incluidas 1.171 lluvias; otras fuentes preservadas. YB 09/09=54,8 y 16/09=7,1 mm;
W9=44,7 y 14,5 mm. No se certifica todo el histórico anterior al 01/08.
[Release](reports/release-ha-0.2.325-2026-09-26.md),
[diagnóstico y reparación](reports/meteocat-partial-days-2026-09-26.md).

La reparación introdujo mezcla de coma/punto en el CSV: validación insuficiente.
El runner posterior recuperó 1.498 filas y reescribió todo el CSV con coma; lector
real comprobado, 33.707 filas y cinco columnas float64. La auditoría posterior
conservó las 24.034 celdas reparadas y ninguna clave estación/fecha desapareció.
Total histórico tras runner: 5.550.605 filas. **No ejecutar
`tmp/meteocat-repair-20260926/deploy_csv_decimal_fix.py`**: su candidata es anterior
a esos datos nuevos. Evidencia `after-runner.json` y `runner-history-audit.json`
en ese directorio. Si se necesita confirmar el último runner completo, leer su
registro vigente: aquel NOK describía un intento anterior, no el CSV reescrito.

## Histórico, piloto IDW y rovelló con sequía

- Muestreo: 668 pares cercanos y 10.103 comparaciones mensuales. No aparece un
  déficit general de Meteocat frente a AEMET; 88 jornadas de siete estaciones
  coinciden con el API oficial. Hay datos de origen incompletos: DF 06/07/2025
  publica 0 mm con 28/48 lecturas. No confundirlos con nuestra pérdida corregida.
  La auditoría de agosto detectó diferencias menores desde 09/08 y pérdidas
  ≥5 mm desde 13/08; no asegurar que antes no exista ningún problema.
  [Método y límites](reports/weather-cross-source-sample-2026-09-26.md).
- Usuario autorizó un piloto **local**, con datos y salidas en `docker-data`.
  Última sincronización verificada: generación
  `20260926T204049825478Z-635f090343b7`, 5.550.605 registros; 6,6 MB descargados,
  resto reutilizado. No presumir que coincide con HA después de nuevos runners.
  24 referencias, 23.631 jornadas, 48 verificaciones contra IDW canónico.
  MAE diario 1,091417 → 1,091530 mm con reducción de peso; tampoco mejora el
  descarte. **Mantener IDW operativo actual**: el piloto no acredita una mejora.
  [Reglas, resultados y limitaciones](../local-apps/rainfall-qc/README.md).
- Rovelló/Els Ports: artefacto del precálculo 258, 26/09, IFF 78; modelo LR–V4
  del 24/09, anterior a la reparación. Reproducción algebraica de sus
  coeficientes: asociaciones con baja humedad/pocos días lluviosos compensan
  penalizaciones hídricas. Sus 33 entradas no incluyen agua disponible del suelo.
  Sin evidencia local de área; evidencia global 5/5 recomendaciones acertadas
  entre 19 observaciones (9 positivas), límite inferior Wilson 95 % 56,55 %.
  Seguimiento del 27/09: lote nuevo y revisión 261 seleccionan RF–V3, IFF 37
  constante. Sólo cambia el horizonte entre sus 27 entradas; ninguno de los
  200 árboles cambia de hoja en Els Ports. En Vallcebre cambia cuatro árboles,
  IFF 76,41→75,96, todos redondean a 76. Agua del suelo observada al corte, no
  proyectada diariamente. No confundir RF con LR ni atribuir toda la mejora a
  la reparación meteorológica: también cambian muestras, selección y fecha.
  [Informe y evidencia](reports/rovello-els-ports-dry-prediction-2026-09-26.md).

## GBIF y setales: entregado; decisiones que deben conservarse

Las funciones aceptadas por el usuario se publicaron en HA 0.2.324 y están
incluidas en 0.2.325. No son una implementación pendiente de publicar.
[Contrato y uso](../local-apps/gbif/docs/gbif-rainmapper-export-import-design.md),
[validación](reports/gbif-import-local-2026-09-25.md),
[release 0.2.324](reports/release-ha-0.2.324-2026-09-26.md).

- ZIP con citas que cumplen filtros, también fuera del encuadre, y fotos.
  Selector de carpeta origen y archivo destino, nombre editable y ZIP existente.
  Duplicados GBIF al exportar: Ignorar/Reemplazar; al importar: Mantener/Reemplazar.
- Importadas como Borrador/Revisar antes de usar; observador/origen GBIF,
  abundancia Normal y calidad provisional 0,75. Reemplazar conserva ID Rainmapper,
  sustituye datos/fotos y devuelve a revisión; restaura si estaba archivada.
- Incertidumbre original conservada: declarada o 500 m asignados si desconocida;
  existentes sin precisión muestran 0 por compatibilidad, sin migración masiva.
- GIS/DEM y microárea contenedora recuperados al importar, con progreso por cita;
  varios contenedores: centro más cercano. Cartografía separada de datos de campo.
- Alta automática opcional de setales, desmarcada inicialmente: examina todo el
  lote reutilizando altas previas. Radios área 500 m / microárea 495 m; ampliar
  el área por unión geométrica para mantener margen de 5 m, también si era manual.
  Sin recortar/fusionar ni reactivar zonas archivadas. Empates resueltos por ID.
- Origen `provenance.creation_source` manual/GBIF/futuro. Ampliar área manual
  conserva su origen. Nombres editables no cambian IDs ni asociaciones.
  Nombre del área usa municipio del snapshot si existe, con sufijo GBIF/ID;
  topónimo más cercano sigue pendiente de fuente verificada.
- SoilGrids por microárea, cobertura local (`ensure_missing=False`); si falta,
  queda pendiente. Importar no amplía descargas ni lanza modelos. Plan sellado,
  control de concurrencia y diario de guardado según contrato; no deshacer cambios ajenos.
- Lotes: hasta 100 citas / 120 MiB de fotos; ZIP máximo 128 MiB.
- Setales: búsqueda por coordenadas/Photon, navegación desde observación con
  marcador y detalle; círculos como polígonos editables. Sustituir/Añadir círculo,
  clic centro/borde y guardado explícito. Usuario acepta su funcionamiento.
- Pendientes: mapa cartográfico del plan (aplazado), nombres por topónimo y
  auditoría de observaciones que no encajan en sus zonas. No ejecutar por rutina.

## Decisiones vigentes que afectan al siguiente paso

**Consenso de recomendaciones (incluido desde 0.2.318):** Workers y trabajos →
Modelos de predicción → Desactivado / Solo comparar / Aplicar
(`legacy` / `shadow` / `prudent`). En Ou de reig, Edulis y Pinícola, cuando hay
recomendación favorable e IFF ≥60, consulta exactamente dos familias alternativas
fijas de la semana, posteriores al ganador en el ranking sellado. Aplicar exige
las dos disponibles y ≥60; si discrepan o faltan, se abstiene. Conserva ganador e
IFF, no suaviza diferencias espaciales. Aereus/deliciosus quedan fuera de este veto.
Ausencia de alternativas no es desacuerdo. Descartes por datos cuentan sólo
familias evaluadas; no las que el mapa no ejecutó. Conclusión verde/roja, ámbar si
faltan alternativas, debajo de temporada; un Detalle con perfiles visibles.

El usuario exige evitar más errores que aciertos perdidos. Rechazó la regla
global que evitaba 130 errores pero perdía 156 aciertos. La retrospectiva selectiva
39/10 motivó esta dirección, **no acredita ese balance futuro ni el selector
completo por área**: ámbito elegido tras ver datos, observaciones reutilizadas por
plazo y familias correlacionadas. Mantener modo reversible y medir con nuevas
observaciones/GBIF revisado antes de ampliar especies o activar por rutina.

**Querigut/rovelló:** el informe del lote real de septiembre reprodujo 99→90,
no encontró consenso general sobre esos IFF y detectó exclusiones por huecos de
lluvia/estado hídrico e imputación en V5/V6. Suelo/hosts GIS ausentes y estado
hídrico son problemas distintos; las microáreas inspeccionadas tenían retención
SoilGrids. No atribuirlo todo a Francia, ni tratar 99 como 99% de acierto.
El filtro de consenso no cubre deliciosus. Informe opcional:
`docs/reports/querigut-predictor-2026-09-21.md`; conclusiones de ese snapshot,
no prueba de los modelos actuales después de otros entrenamientos.

**Memoria (corregida desde 0.2.318):** verificación secuencial de respuestas y
recepción de artefacto por bloques, conservando SHA, límites y activación atómica.
Benchmark histórico con la misma copia en Mac: pico 825→304 MiB, 16,00→15,66 s;
no es medida del servidor RPi. Falta medir en real y explicar consumo inicial y
retención/cachés. No está demostrada una fuga. La percepción de lentitud tampoco
se aisló en un A/B con mismos datos/modelos. Ver informe de memoria si se retoma.

**Datos de lluvia:** copiar `Data/` no actualiza el GeoJSON de `PublicData/`.
La ficha de estación puede seguir mostrando el mapa generado antes; la predicción
puntual lee su histórico meteorológico por otro camino. Comprobar generación,
configuración y modelos antes de afirmar paridad entre HA real y local.

**Ciencia conservada:** SMI común regulado + PM + una capa 0–30 cm con IDW;
modelo simple sólo visual. Host/suelo GIS filtran compatibilidad en el mapa;
no inferir entradas entrenadas por el nombre del modelo: mirar sus columnas.
No cambiar IDW, suspensiones ni modelo operativo por intuición o por acuerdo visual.

## Publicado en 0.2.326 · ficha de observaciones del mapa (27/09)

Añadidas coordenadas latitud/longitud (seis decimales) e incertidumbre en metros
al detalle del visor de observaciones. **Petición expresa del usuario: mostrar
0 como «0 m», sin aclaraciones ni tooltip de compatibilidad.** La procedencia
se conserva internamente. Valores no nulos pueden indicar declarada/asignada/manual;
se usa `precision_origin` vigente, sin confundir el origen GBIF con una edición.
Sin migración de datos ni cambio de modelos. Etiquetas es/ca/en.

Etiqueta abreviada a **Incertidumbre / Incertesa / Uncertainty**. Si hay foto local,
la ficha muestra una miniatura de la primera foto asociada; al pulsarla ocupa
la misma ficha con «Volver a la observación». Altura ajustada al espacio del mapa.
Lectura autenticada con permiso de observaciones, por ID y revisión, sin exponer
rutas ni abrir URLs externas. Vistas JPEG en memoria (192/960 px), sin alterar
originales ni crear ficheros; cargas canceladas y URLs temporales liberadas al cerrar.

33 pruebas de API/observaciones correctas, incluida denegación de acceso a fotos,
rutas fuera del directorio, revisión antigua, límites y ausencia de archivo.
Batería `prediction_map_browser_check.mjs` correcta: miniatura, ampliación, vuelta
a datos y caso sin foto. Captura ampliada inspeccionada. HA local reconstruida y
recreada desde este código, hashes de módulo, adaptador, JS, CSS y etiquetas
idénticos al worktree; HTTP 200. Foto real local comprobada en el contenedor:
miniatura 144×192 / 9.940 bytes, ampliación 720×960 / 137.733 bytes.
Worker no reconstruido/reiniciado para esta UI. Usuario validó local y autorizó
publicar: imagen 0.2.326 disponible; instalación real confirmada por el usuario.
Smoke completo
correcto (1.829 pruebas, 52 omitidas). Código y documentación incluidos en el
commit de release; JSON privados de observaciones excluidos.

## Corrección publicada en 0.2.327 · casillas GBIF

Tras instalar 0.2.326, el usuario comunica casillas enormes en lotes con duplicados.
La columna comparte casillas y selectores Mantener/Reemplazar; las casillas
heredaban `width:100%` y `min-height` de los campos generales. Regla acotada a
`#gbif-import-dialog input[type=checkbox]`: ancho/alto mínimo y máximo de 16 px,
sin padding. No cambia selección, duplicados ni importación. Prueba de navegador
con estilos completos de `html_page`, lote mixto y aserciones de dimensiones
correcta; captura inspeccionada. HA local reconstruida/recreada; SHA del módulo
idéntico al worktree y HTTP 200 de observaciones. Worker intacto. Usuario autoriza publicar; incluida en 0.2.327.

## Corrección publicada en 0.2.327 · notas de pendiente DEM en microáreas GBIF

El usuario detecta notas de pendiente vacías en `gbif_micro_4993870809` al
comparar con Recuperar GIS/DEM de setales. Confirmado en código: `apply_plan`
guardaba el informe GIS/DEM y copiaba altitudes, orientaciones y ecología, pero
omitía `topography.slope_notes`. Ahora copia media y rango con el mismo formato
del mantenimiento, sólo con DEM disponible y tres valores numéricos finitos;
conserva cero y no inventa notas si faltan datos. Las microáreas existentes no
se migran ni se modifican automáticamente.

Validación: 42 pruebas del importador correctas, incluidas persistencia, pendiente
cero y DEM ausente. HA local reconstruida/recreada, hashes de importador y UI
idénticos al worktree; observaciones HTTP 200. Worker intacto. Usuario autoriza publicar; incluida en 0.2.327.
No se ha inspeccionado el JSON
real de esa microárea: el fichero de share no estaba accesible y no figura en
la copia local de setales comprobada.

## Trabajo documental/Git y límites de actuación

### Publicado en 0.2.328 · altura de la lista de observaciones

Tras confirmar 0.2.327 instalada, el usuario señala espacio vacío bajo la tabla.
El límite fijo `max-height:500px` dejaba hueco cuando el detalle lateral hacía
más alto el panel. `web_server.py` convierte la tarjeta de tabla en columna flex;
el scroll conserva 500 px de base y crece hasta ocupar el espacio de la tarjeta.
No cambia paginación ni datos. Navegador local a 1728×1200: antes tabla 500 px,
hueco 212,6 px y 12 filas completas; después tabla 703,6 px, margen 9 px y 18
filas completas. A 700×900 conserva 500 px y permite llegar a la última fila.
Captura inspeccionada; comprobación repetida sobre HA local reconstruida/recreada
sin inyectar CSS. SHA `web_server.py` idéntico al worktree:
`a00dbdb5bf0d2531b72d3db8ad1393282a5fa28aec605b93691c1c602468977c`.
Evidencia local en `docker-data/observation-table-layout`. Worker intacto.
Usuario valida en local y autoriza publicar: incluido en 0.2.328.

### Publicado en 0.2.328 · ficha de observaciones del mapa

Etiqueta Bosque/Bosc/Forest, interlineado y separaciones compactos. Miniatura y
enlace en una fila inferior que permanece visible; el texto largo se desplaza
dentro de su zona. Ampliar foto oculta datos/pie y Volver los restaura. Enlace
final acordado: Cómo llegar / Com arribar / Directions a Google Maps
`/maps/dir/?api=1&destination=lat,lon`, sin fijar origen ni medio de transporte.
El usuario elige sólo enlace: no círculo de incertidumbre. Maps URLs no ofrece
parámetros de círculo o texto personalizado del marcador; no simularlos.

Prueba del visor compartido en Chrome aislado correcta, incluida etiqueta,
destino, foto visible/enlace a su derecha, ampliación/retorno y caso sin foto.
HA local reconstruida/recreada, paridad de servidor, JS/CSS y etiquetas;
recursos HTTP y etiquetas efectivas comprobados. Evidencia en
`docker-data/observation-popup-layout`. Worker intacto; sin tareas operativas.
Usuario valida en local y autoriza publicación junto al ajuste de altura de
tabla: incluido en 0.2.328. Prueba real en móvil pendiente del usuario.

- Base de esta release: `d055f08` (HA 0.2.327). Ajustes de interfaz, pruebas,
  bump y continuidad se cierran en un único commit de release 0.2.328.
- Privados preexistentes: `mushroom-data/mushroom_observations.json` modificado y
  `mushroom_observations.json` de la raíz sin seguimiento. **No incluirlos en Git,
  revertirlos ni usarlos para sobrescribir datos de HA.**
- Usar `docker-data` para nuevas copias/experimentos; el usuario tiene copia de
  `share/rainmapper` y rechaza respaldos adicionales en HA real. No limpiar datos,
  volúmenes o históricos ajenos. Conservar coordinadores, identidad y suspensiones.
- Montajes usados en la investigación reciente: `/Volumes/share` y
  `/Volumes/media-1`. Revalidar origen/montaje antes de acceder: los nombres
  históricos `/Volumes/share-1` o `/Volumes/media` no acreditan el destino actual.
- Instalar/parar/arrancar HA corresponde al usuario. Sin SSH salvo petición
  expresa; no usar Tailscale ni montar SMB por Tailscale. Conservar, sin sustituir,
  la URL Tailscale persistida que utiliza el worker.
- No lanzar entrenamiento, precálculo ni runner. No reiniciar un worker ocupado.
  Una revisión documental no autoriza desplegar ni publicar. Mantener updates
  breves cada minuto y responder al usuario sin abandonar la tarea activa.
