# TODO — revisión 04/10/2026

Arranque: [codex-start-here](codex-start-here.md) y [active-context](active-context.md).
Esta lista no autoriza trabajos ni publicaciones. Etapas superadas conservadas en
[archivo del cierre](reports/session-context-before-close-2026-09-22.md).

## P1 pendiente · Utilidad de las predicciones de aereus y caesarea (04/10)

- [x] Completar las dos comparaciones locales: umbral favorable y selección del
  ganador. Conservar artefactos, reglas y controles; no repetir lotes cerrados ni
  presentar las hipótesis reutilizadas como confirmación independiente.
- [x] Hacer legibles los informes: cantidades / denominadores → porcentajes,
  referencia ideal, explicación de columnas, promedios entre siete horizontes
  y comparación de caesarea A/B/C por campaña. Incluye el anexo de umbrales.
- [x] Documentar la preferencia del usuario y el índice por favorables reales;
  calcular k=2/3/4 desde los resultados guardados y conservar su carácter provisional.
- [x] Cerrar la continuidad: contexto compacto, decisiones etiquetadas y contexto
  sustituido archivado. Lectura inicial limitada a los dos documentos de arranque.

- [ ] **Retomar la revisión conjunta de selección, umbrales y utilidad**, sin
  repetir las investigaciones cerradas. [Informe de selección e índice propuesto](agents/prediction-model-selection/resultados-2026-10-04.md#indice-utilidad-oportunidades)
  e [informe de umbrales](agents/prediction-thresholds/resultados-2026-10-03.md).
  El usuario prefiere 10 consejos favorables con nueve aciertos a 40 con 30,
  siempre que la cantidad de recomendaciones sea útil; 90% no es un mínimo acordado.
- [ ] Acordar el coste `k`, el mínimo del índice y la cantidad/frecuencia útil
  de consejos, distinguiendo precisión, oportunidades detectadas y cobertura
  total de consejos. Fórmula discutida: `I_k = 100 × (TP − k × FP) / P`, donde
  `P` son **todos los favorables reales**, incluidos los no detectados; no los
  casos totales ni sólo los consejos favorables del modelo. Ningún `k` ni mínimo
  queda aprobado. Revisar también si esta fórmula representa bien la preferencia.
- [ ] Contrastar esa preferencia con la penalización: sobre los mismos casos,
  para preferir nueve aciertos/un error a 30 aciertos/diez errores se requiere
  `9 − k > 30 − 10k`, es decir, **`k > 7/3 ≈ 2,33`**. Con `k = 2` se invierte
  aquel ejemplo; `k = 3` y `k = 4` lo respetan, sin fijar por ello el coste definitivo.
- [ ] Definir soporte de observaciones y episodios independientes, incertidumbre
  y estabilidad por campaña antes de una nueva validación. Un índice alto con
  una única oportunidad no demuestra fiabilidad; un promedio positivo tampoco
  elimina una campaña sin consejos, como caesarea B en 2025. Distinguir ajuste
  experimental, evidencia ya utilizada y confirmación futura independiente.

Comparación aritmética guardada para retomar, en **puntos de utilidad, no %**.
Estos A/B/C pertenecen al estudio de selección; no equivalen a las letras del
estudio de umbrales. Fuente: `tmp/prediction-model-selection/analysis/results.json`,
agregados `species.<especie>.strata.pooled.average`, sin redondear antes del cálculo.
Denominadores: caesarea 35 favorables reales; aereus 36.

| Especie | Variante | k = 2 | k = 3 | k = 4 |
|---|---|---:|---:|---:|
| Caesarea | A | −12,65 | −31,43 | −50,20 |
| Caesarea | B | +23,67 | +16,73 | +9,80 |
| Caesarea | C | +17,55 | −2,45 | −22,45 |
| Aereus | A | +5,95 | −15,48 | −36,90 |
| Aereus | B | −9,52 | −32,14 | −54,76 |
| Aereus | C | −2,78 | −27,38 | −51,98 |

**Guardado como pendiente por el usuario, no como orden de ejecución.** No lanzar
otro agente, repetir entrenamientos/precálculos, promover B/C ni cambiar HA o el
worker/coordinador. Conservar resultados, reglas originales y archivos privados.

## Aplazado · Disco del Mac (03/10)

Auditoría detenida por decisión del usuario; conservar lo pendiente sin retomarlo.

- [x] Auditar repo, datos de apps y temporales; primero en lectura y después
  únicamente las limpiezas autorizadas indicadas abajo.
  [Desglose y límites](reports/mac-disk-audit-2026-10-03.md).
- [x] Limpieza autorizada: 247 carpetas de pruebas y 61 archivos de sesiones
  archivadas retirados; aumento observado del espacio libre de unos 20,76 GB.
- [ ] Resolver fallo de `codex delete` de una sesión archivada restante (524 MB);
  archivo e índice conservados. Instaladores pendientes son actualizaciones
  preparadas, con DMG de Docker montados: no eliminados.
- [x] Explicar los 262 GB aparentes de WhatsApp: clones APFS verificados,
  2,443 GB contando cada flujo una vez, cerca de los 2,31 GB indicados por la app.
- [x] Conciliar Finder/contenedor: 305,36 GB usados de System+Data frente a
  ~329,08 GB del contenedor con auxiliares; no era diferencia GB/GiB.
  Disponible 179,82 GB ya incluye 14,5 GB purgables.
- [ ] **Pendiente aplazado:** atribuir ~35,8 GB restantes dentro de los 305,36 GB de
  Finder (~269,6 GB inventariados, orientativos). Downloads, Trash, Fotos,
  MobileSync y otros directorios bloqueados incluso fuera del sandbox. Resolver
  acceso macOS o pedir tamaños; no repetir barridos de clones ya comprobados.
- [ ] Decidir tratamiento de instaladores tras revalidar actualizaciones/montajes.
  No borrar contenido montado ni detener Docker/worker para limpiar sin acuerdo.
- [ ] Lightroom, auditorías antiguas y Buildx sólo si se acuerdan por separado.
  Fuentes, geografía operativa y volumen worker se conservan. No desinstalar
  WhatsApp ni equiparar tamaño aparente a espacio recuperable.

## UI · Círculos de setales (03/10)

- [x] Traducciones ES/CA/EN, edición por centro/radio y corrección de coordenadas
  GBIF de 16 decimales. Pruebas locales completas y confirmación del usuario.
  Publicado en **HA 0.2.331**, con los ajustes geográficos locales ya validados.
  [Release, alcance y comprobaciones](reports/release-ha-0.2.331-2026-10-03.md).
- [x] HA 0.2.331 instalada y funcionando, confirmado por el usuario.

## P2 · Geografía preparada y expansión territorial

- [x] **Retirada `-todelete` completada** (03/10), autorizada por el usuario:
  eliminadas sólo las dos carpetas antiguas del Mac. Espacio libre
  94,44 → 116,27 GB (**+21,83 GB**). Fuentes y geografía operativa intactas.
  Share/media de HA real sin `todelete`; ninguna eliminación remota.
  [Revisión, autorización y mediciones](reports/geography-todelete-review-2026-10-03.md).
- [x] **Organización local de geografía operativa y fuentes**: local/worker
  validados, código publicado en 0.2.331 e instalación real confirmada.
  [Plan, pasos e incidencias](mushrooms/geography-local-organization-plan-es.md).
- [ ] Recorridos funcionales generales restantes del usuario: asignación de
  observaciones, recuperación geográfica en setales e importación GBIF.
  Edición circular local y funcionamiento de HA 0.2.331 confirmados.
- [ ] Otros posibles archivos sobrantes de HA: la auditoría del 28/09 no encontró
  una gran copia retirable; históricos candidatos sumaban 4,02 MB. No borrar ni
  archivar sin revisión y acuerdo específicos.
  [Auditoría HA](reports/ha-geography-files-audit-2026-09-28.md).
- [ ] Medir disco y latencia por capa de `mushroom-map-GIS`: separar originales,
  duplicados, índices y rasters efectivamente consultados. El tamaño en disco no
  equivale al volumen leído por punto.
- [ ] Extender el patrón MVC50 preparado a España/Francia cuando corresponda:
  atributos mínimos, índices espaciales, deduplicación por contenido y paquetes
  incrementales. Para DEM, evaluar teselas/compresión/resolución conservando la
  precisión necesaria de altitud y pendiente. Sin borrar originales antes de
  auditar consumidores y demostrar equivalencia.
- [x] Unificar recuperación de microáreas y reconstrucción con las fuentes
  preparadas del mapa. Prioridad por punto antes de agregar muestras del polígono;
  dataset científico de referencias a archivos existentes, caché compartida.
  Validación dirigida en ambas imágenes y ciclo operativo local completado y
  auditado: 517 reconstrucciones, 792 ajustes y precálculo activo.
- [ ] Antes de retirar originales, adaptar/auditar el inventario de valores GIS
  para mantenimiento de mapeos; la migración operativa no autoriza borrarlos.

## Entregado y cerrado · HA 0.2.330 (28/09)

- [x] Coherencia territorial entre mapa, recuperación, microáreas y reconstrucción;
  ciclo local aceptado y release publicada. [Evidencia](reports/release-ha-0.2.330-preparation-2026-09-28.md).
- [x] Instalación en HA real confirmada por el usuario; incluye las mejoras de
  observaciones/GBIF de 0.2.326–0.2.329. No quedan instalaciones intermedias pendientes.
- [x] Registrar MVC50 y activar metadatos científicos en real: generación
  `local-mvc50-20260928`, 14 referencias; sin nuevas copias ni hashes de GIS
  durante la activación. Originales conservados.
- [x] Usuario confirma entrenamiento y precálculo reales terminados al cierre.
  No se ha reauditado este último ciclo ni se reutilizan sus cifras locales como reales.
- [x] Comprobar predicción para todas las especies, observada enmarcada;
  trazabilidad por ID, altitud, bocadillo, foto y Cómo llegar entregados.
- [x] Campins: dos puntos contrastados contra recuperación HA real; Qv3 queda
  no determinado y POa silíceo según mapping vigente. Usuario acepta conservarlo.
  No hay una corrección pendiente ni se añade clasificación Qv3 por vecinos.
- [x] Discusión de entrenamiento cerrada: conservar evaluación previa y ajuste
  final con filas elegibles; no implementar interruptor ni nuevo reparto.
- [ ] Prueba específica de ficha/enlace en móvil: no hay confirmación explícita
  de ese caso. Sólo retomar si el usuario lo necesita; no bloquea esta release.

## Completado · Memoria del worker, IDW y diagnóstico de curvas

- [x] Reconstruir el worker con reutilización de entradas V2–V6; 122 archivos
  en paridad y 25 pruebas correctas dentro de la imagen. Coordinadores e identidad
  conservados. [Alcance y medición](reports/worker-evaluation-memory-2026-09-27.md).
- [x] Ciclo del usuario verificado el 27/09: multiversión 10:04, 792/792 ajustes;
  precálculo 9:39, revisión 261 activa y SHA idéntico HA/worker. Sin OOM/reinicios,
  pico cgroup 6,86 GiB desde arranque; timeouts recuperados. No confundir esta
  medida con el −57 % del ensayo aislado de carga V6. Optimización general pendiente.
- [x] Reexaminar rovelló/Els Ports: ahora RF–V3/IFF 37. Curva plana explicada
  por entradas al corte y baja sensibilidad al horizonte (0/200 árboles cambian).
  No acredita que la reparación resuelva todas las asociaciones aprendidas.
  [Caso anterior](reports/rovello-els-ports-dry-prediction-2026-09-26.md).
- [x] Piloto local de calidad espacial de lluvia: no acredita mejora global.
  Mantener IDW operativo; ampliaciones sólo si se retoma expresamente.
  [Resultados y límites](../local-apps/rainfall-qc/README.md).

## Publicado · Modo histórico desde HA 0.2.320

- [x] Calendario y fecha común; modelos actuales, meteorología hasta D−1.
- [x] Permiso por usuario false por defecto, también admin.
- [x] Local/worker con fallback y progreso; lectura espacial y cobertura reutilizada.
- [x] Reconstrucción/paridad 220/125; smoke, navegador y medida real acotada.
- [x] Usuario activa permiso y confirma primera carga visual en HA local.
- [x] Fichas sin modal general y arreglo de coordenadas históricas ausentes.
- [x] Circuito HTTP/navegador real con 141 estaciones, worker/local, ficha y caché.
- [ ] Si se prioriza rendimiento remoto: desglosar 48,3 s de espera completa frente
  a 0,33 s del lector en la prueba; no atribuir toda la espera al cálculo de GeoJSON.
- [x] Usuario acepta el calendario y solicita publicar HA 0.2.320.
- [x] Candidata local 0.2.320 y worker 1.1.6 reconstruidos; paridad y smoke final OK.
- [x] Usuario lanza reconstrucción/base/multiversión; 792/792 ajustes, tres
  resultados verificados, lote nuevo instalado y limpieza completa auditados.
- [x] Precálculo local del usuario revisión 74 recibido/activo; identidad, SHA,
  recuentos y limpieza terminal verificados contra la generación nueva.
- [x] Publicación 0.2.320/latest, digest común y AMD64/ARM64 verificados.
- [x] Instalación antigua superada: HA 0.2.330 confirmada por el usuario.
- [ ] Confirmar el permiso histórico del usuario que vaya a probarlo en real;
  instalar una versión no acredita que se haya habilitado desde Usuarios.
  [Release y circuito completo](reports/release-ha-0.2.320-2026-09-22.md).
  [Evidencia y tiempos](reports/historical-map-local-2026-09-22.md).

## Verificación pendiente · Detalle de variables publicado desde HA 0.2.319

- [x] Corregir lista parcial de variables con detalle paginado, scroll y contador.
- [x] Reconstruir HA local y worker; comprobar paridad 217/117 y conservar destinos.
- [x] Usuario prueba local y confirma que funciona. Smoke 1.725 pruebas/52 skips OK.
- [x] Publicar 0.2.319/latest, mismo digest y amd64/arm64; push `dda52e8`.
  [Informe y excepción autorizada](reports/release-ha-0.2.319-2026-09-22.md).
- [x] Instalación confirmada por el usuario y versión 0.2.319 comprobada por SMB
  LAN en estado/registro de arranque. [Evidencia](reports/ha-0.2.319-smb-2026-09-22.md).
- [ ] Probar en la versión vigente de HA real el detalle completo en ambos
  ejecutores: no se persiste y SMB no basta; pendiente consulta viva del mapa.
  No reconstruir worker por rutina.
- [ ] Ante fallo, consultar logs/códigos y procedencia de datos. No repetir
  entrenamiento ni precálculo como diagnóstico.

## P1 · Memoria y tiempos en Raspberry Pi 4 (4 GB)

- [ ] **Trabajo huérfano tras perder el worker** (27/09/2026, aplazado por el
  usuario): HA mantiene `running` y un contador creciente después de caducar
  la comunicación; caso confirmado con OOM del worker al 46 %. Mostrar pérdida
  de comunicación y hora del último progreso, distinguir desconexión transitoria
  de terminación confirmada y resolver el estado sin relanzamientos automáticos
  ni duplicar trabajos. Requiere cambio futuro de HA, separado de la corrección
  local de reutilización de entradas V2–V6.
- [ ] **Duración creciente del precálculo automático** (26/09/2026, aplazado):
  el usuario observa un aumento aproximado de 9 a 11 minutos en las últimas
  ejecuciones. Contrastar registros persistidos por fase (preparación, cálculo,
  transferencia, validación y activación), número de áreas/microáreas, modelos,
  cobertura meteorológica y tamaño del resultado. El crecimiento de setales es
  una hipótesis, no una causa confirmada. Comparar alcance y condiciones antes
  de concluir regresión; no lanzar precálculos ni entrenamientos para investigarlo
  sin autorización del usuario. Retomar más adelante, no durante el trabajo activo.
- [x] Identificar y reproducir acumulación de respuestas al validar precálculo.
- [x] Validación secuencial y recepción HTTP por bloques publicadas en 0.2.318,
  conservando límites/SHA/activación atómica. Mac: pico 825→304 MiB, 16,00→15,66 s
  sobre la misma copia. [Evidencia y límites](reports/ha-memory-precompute-2026-09-22.md).
- [x] Auditar circuito local del usuario: 792 ajustes correctos, revisión 73
  recibida/activa. Intento previo falló por huella obsoleta antes de calcular.
- [ ] Medir mejora en HA real con registros después de trabajos del usuario;
  separar proceso, contenedor, caché de archivos y fases. No está medida en RPi.
- [ ] Investigar consumo inicial/cachés y retención residual sin asumir fuga.
- [ ] Si persiste lentitud, comparar mismo alcance/datos/modelos y fases. Las
  comparaciones históricas disponibles no son un A/B que demuestre regresión.

## P1 · Fiabilidad y recomendaciones comprensibles

- [x] Comparación de cinco especies con modelos del lote real nuevo: Ou, Aereus,
  deliciosus, Edulis y Pinícola. [Auditoría](reports/model-selection-robustness-2026-09-21.md).
- [x] Descartar filtro global 130 errores evitados/156 aciertos perdidos.
- [x] Implementar/publicar política reversible legacy/shadow/prudent; dos familias
  fijas para Ou/Edulis/Pinícola cuando hay recomendación favorable e IFF ≥60.
  IFF intacto, reservas por datos ausentes y perfiles/IFF alternativos visibles.
- [x] Presentación compacta: conclusión coloreada bajo temporada y un único Detalle.
- [x] Revisar Querigut en snapshot real: 99 no respaldado por consenso general;
  exclusiones por lluvia/estado hídrico, imputación y límites de evidencia.
  [Informe](reports/querigut-predictor-2026-09-21.md).
- [ ] Medir el balance real de errores evitados/aciertos perdidos y cobertura de
  alternativas; no extrapolar la retrospectiva selectiva 39/10 al selector por área.
- [ ] Confirmar modo de HA real antes de interpretar avisos. El último estado local
  documentado era shadow; revalidarlo si se utiliza.
  No activar ni ampliar a deliciosus/aereus sin decisión explícita.
- [ ] Incorporar sólo GBIF revisado/aprobado por el usuario antes de nueva evaluación.
- [ ] Auditar tres falsos positivos del 18/09 (Vallcebre ×2, Bellver/Riu), recuperando
  fecha/esfuerzo y modelo/generación. [Puntos](mushrooms/SMI/adoption-2026-09-20/field-feedback.md).
  No atribuir al SMI ni convertir visitas incompletas en negativos automáticos.
- [ ] Antes de reactivar suspendidos, revisar trazas de lluvia, independencia
  por observación, calibración y respuesta temporal. Conservar las siete reglas.
- [ ] Mantener SMI regulado + PM + una capa e IDW; simple sólo visual. Nuevas
  cantidades absolutas o retirada de la curva simple requieren tarea expresa.

## P2 · Operación y recursos, al retomar ese bloque

- [ ] Indicador ocupado: acordar semántica de carriles/coordinadores; usuario
  apunta a background por coordinador. No modificar planificación como arreglo UI.
- [ ] CLI por asociación y otras optimizaciones de transporte/hash/escritura;
  recepción de precálculo por bloques ya está hecha, no repetir ese diseño.
- [ ] Catálogo compacto de calidad específico del mapa si el crecimiento lo
  justifica. El fallo quality_read_limit ya se corrigió sin elevar los 64 MiB.
- [ ] Paridad meteorológica: Data y PublicData son capas diferentes. Comprobar
  generación del GeoJSON y fuente de histórico antes de culpar a IDW/predicción.
- [ ] Caché Buildx: auditoría de disco realizada el 03/10; limpieza separada
  todavía no autorizada. 19,8 GB declarados incluían capas compartidas; 8,39 GB
  privados según la captura. No sumarlos además de Docker.raw ni prometer ese
  ahorro sin revalidar. La bajada histórica de libre no está atribuida con certeza.
  Continuar desde el bloque **P1 activo · Disco del Mac**, no repetir la auditoría.
- [ ] Validación geográfica independiente/AMD64 antes de retirar originales.
- [ ] Revalidar incidente Barcelona/Erinya antes de actuar:
  [informe histórico](reports/weather-coordinate-conflict-2026-09-13.json).
- [ ] Runner externo/AWS/servidor doméstico y Python 3.14 quedan como futuros.
- [x] Releases anteriores GIS/DEM/SMI/suspensiones y visores WU/GBIF separados:
  historial en archivo, no quedan instalaciones antiguas como tareas actuales.

## Pendientes del usuario y aplazamientos explícitos

- [ ] **Setales:** auditar observaciones que no encajen en el área/microárea
  asignada, como siguiente bloque independiente de la importación GBIF.
- [ ] **Nombres GBIF:** resolver municipio/topónimo más cercano con una fuente
  verificada; el nombre actual derivado del snapshot no acredita proximidad.
  Conservar IDs estables y permitir editar nombres sin perder asociaciones.
- [ ] **WU · backfill:** impedir offsets mensuales futuros antes de lanzar el
  trabajo; revalidar el caso y evidencia en `tmp/backfill-future-20260924/`.
  No repetir descargas ni alterar el CSV para investigar este pendiente.

- [ ] **GBIF · previsualización de setales** (aplazado por el usuario, 25/09/2026):
  sustituir el esquema de contornos del plan de importación por un mapa con fondo
  cartográfico, leyenda de áreas/microáreas, zoom y selección de cada zona.
  Debe permitir distinguir los límites y examinar zonas alejadas entre sí sin que
  queden reducidas a puntos al encuadrar todo el lote. Mantener la interfaz actual
  hasta retomar expresamente esta mejora.
- [ ] **GBIF:** revisión manual Pendiente/Dudosa/Aceptada/Rechazada; esperar lote
  aprobado antes de importar, entrenar o generar setales. Conservar revisión
  del navegador/JSON y fotografías. [Guía](../local-apps/gbif/docs/guide.md).
- [ ] **WU:** revisar calidad y aprobar candidatas antes de altas/backfill.
  143 nuevas/12 priorizadas fueron recuentos históricos, no estado actual;
  consultar `local-apps/wunderground/data/research.sqlite3`. [Uso](station-research-es.md).
- [ ] **GIS aplazado:** 343 pendientes de la tanda de 488 (331 sin investigación
  específica suficiente, 12 con limitación documentada, no irresolubles).
  Revalidar cola/hashes/fuentes al retomar; 567 aceptados previos no son revisión
  nueva. Conservar `tmp/soil-review-after-0.2.307/`.
  [Método](mushrooms/gis-soil-review-method-es.md), [informe](gis-review-2026-09-16.md).
- [ ] Consumo efectivo de mappings subidos en HA real/worker: paridad almacenada
  histórica no basta; comprobar sin regenerar modelos ni copiar por rutina.

## Producto y ciencia conservados — no ejecutar automáticamente

- [ ] Arbolado vecino: criterio/radio/distancia/procedencia; el vecino pH no lo sustituye.
- [ ] Vinosus y otras fichas: evidencia específica, sin restaurar rangos ni vetos globales.
- [ ] Regresión Safari/iPhone de gestos, estilos y modos; buscador ya aceptado,
  no equivale a validar toda la UI. No exponer administración local a Wi-Fi.
- [ ] GEODE/MFE nacional, esquemas regionales e índices; Francia ecología/geología
  y normalización forestal. DEM/SoilGrids no acreditan cobertura ecológica.
- [ ] Integración geográfica general SoilGrids por áreas, deltas y recursos,
  diferenciada del cálculo hídrico por microárea ya implementado. Separar cambios
  de presentación, almacenamiento y variables; preservar contratos/anotaciones.
- [ ] Revisar rangos provisionales con evidencia: no generalizar aereus a pH 7,5
  ni derivar pH desde litología. Verificar lectores si se amplían grupos de reglas.
- [ ] Superficie coloreada por zona visible: ampliación separada, no calcular
  todos los puntos del territorio por inferencia de la consulta puntual.
- [ ] Aplicabilidad multiespecie (Rovelló/Els Ports/07-09), sin tolerancia global;
  distinguir modelo ausente de modelo vetado.
- [ ] Catálogo de especies por área y evaluador hold-out persistido para Historial;
  distinguir entrenamiento pendiente, precálculo pendiente y corrupción.
- [ ] Auditar Llanega negra/Marçot/Múrgola negra cuando hold-outs tengan ambas clases.
- [ ] Microáreas francesas y Meteo-France frente a WU: bloque separado.
