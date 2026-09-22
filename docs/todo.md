# TODO — cierre 22/09/2026

Arranque: [codex-start-here](codex-start-here.md) y [active-context](active-context.md).
Esta lista no autoriza trabajos ni publicaciones. Etapas superadas conservadas en
[archivo del cierre](reports/session-context-before-close-2026-09-22.md).

## Publicado · Modo histórico HA 0.2.320

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
- [ ] Usuario instala 0.2.320 en HA real y habilita el permiso histórico desde Usuarios.
  [Release y circuito completo](reports/release-ha-0.2.320-2026-09-22.md).
  [Evidencia y tiempos](reports/historical-map-local-2026-09-22.md).

## P0 · Terminar aceptación de HA 0.2.319 en real

- [x] Corregir lista parcial de variables con detalle paginado, scroll y contador.
- [x] Reconstruir HA local y worker; comprobar paridad 217/117 y conservar destinos.
- [x] Usuario prueba local y confirma que funciona. Smoke 1.725 pruebas/52 skips OK.
- [x] Publicar 0.2.319/latest, mismo digest y amd64/arm64; push `dda52e8`.
  [Informe y excepción autorizada](reports/release-ha-0.2.319-2026-09-22.md).
- [x] Instalación confirmada por el usuario y versión 0.2.319 comprobada por SMB
  LAN en estado/registro de arranque. [Evidencia](reports/ha-0.2.319-smb-2026-09-22.md).
- [ ] Probar en real el detalle completo en ambos ejecutores: no se persiste y
  SMB no basta; pendiente consulta viva del mapa. No reconstruir worker por rutina.
- [ ] Ante fallo, consultar logs/códigos y procedencia de datos. No repetir
  entrenamiento ni precálculo como diagnóstico.

## P1 · Memoria y tiempos en Raspberry Pi 4 (4 GB)

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
- [ ] Confirmar modo de HA real antes de interpretar avisos. Local está shadow;
  no activar ni ampliar a deliciosus/aereus sin decisión explícita.
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
- [ ] Validación geográfica independiente/AMD64 antes de retirar originales.
- [ ] Revalidar incidente Barcelona/Erinya antes de actuar:
  [informe histórico](reports/weather-coordinate-conflict-2026-09-13.json).
- [ ] Runner externo/AWS/servidor doméstico y Python 3.14 quedan como futuros.
- [x] Releases anteriores GIS/DEM/SMI/suspensiones y visores WU/GBIF separados:
  historial en archivo, no quedan instalaciones antiguas como tareas actuales.

## Pendientes del usuario y aplazamientos explícitos

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
