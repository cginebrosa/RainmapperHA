# TODO — revisión 03/10/2026

Arranque: [codex-start-here](codex-start-here.md) y [active-context](active-context.md).
Esta lista no autoriza trabajos ni publicaciones. Etapas superadas conservadas en
[archivo del cierre](reports/session-context-before-close-2026-09-22.md).

## UI · Círculos de setales (03/10)

- [x] Traducciones ES/CA/EN, edición por centro/radio y corrección de coordenadas
  GBIF de 16 decimales. Pruebas locales completas y confirmación del usuario.
  Publicado en **HA 0.2.331**, con los ajustes geográficos locales ya validados.
  [Release, alcance y comprobaciones](reports/release-ha-0.2.331-2026-10-03.md).
- [ ] Instalación de 0.2.331 y comprobación en HA real, a cargo del usuario.

## P2 · Geografía preparada y expansión territorial

- [ ] **EN CURSO · Organización local de geografía operativa y fuentes**
  (28/09): **local y worker validados; código publicado en 0.2.331**.
  Pruebas funcionales restantes a cargo del usuario: asignación de
  observaciones, recuperación geográfica en setales e importación GBIF.
  Edición circular local confirmada el 03/10. Conservar `-todelete`
  hasta completarlas y acordar su retirada.
  `geography-sources/` preparada; 5.891 archivos antiguos conservados en
  `mushroom-GIS-todelete/` y `mushroom-map-GIS-todelete/`. Imágenes locales
  reconstruidas, lecturas antes/después idénticas, smoke 1.859/55 y 51 pruebas
  dirigidas correctos. Sin cambios en HA real ni borrados. Quedan decisión sobre
  HA real y retirada expresa de `-todelete` tras aceptación y revisión final.
  Precálculo automático posterior confirmado también directamente en HA real:
  revisión 277, activación HA/worker y cierre reconocido, 11 min 40 s;
  987/987 combinaciones especie–área–día, sin faltantes/extras; limpieza completa.
  [Plan, pasos, incidencias y retirada](mushrooms/geography-local-organization-plan-es.md).
  [Auditoría posterior HA real](reports/ha-geography-files-audit-2026-09-28.md):
  ya usa la raíz correcta; 16,11 GB lógicos, sin gran copia sobrante identificada
  que pueda retirarse directamente. Históricos candidatos: 4,02 MB. No borrar
  ni archivar antes de hablarlo con el usuario; sin necesidad de release por ello.
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
- [ ] Crecimiento de disco y caché Buildx: medir físicamente y conservar datos,
  fuentes y backups. Limpieza adicional requiere alcance explícito; no borrar
  imágenes/manifests mientras se está instalando HA real.
  El 28/09 el usuario aplaza esta investigación hasta cerrar la revisión del
  precálculo. Pendiente conciliar caída de 145–150 a 115,44 GB disponibles;
  [mediciones parciales y límites](mushrooms/geography-local-organization-plan-es.md).
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
