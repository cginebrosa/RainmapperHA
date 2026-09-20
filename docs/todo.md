# TODO — actualizado 19/09/2026

Arranque suficiente: [codex-start-here](codex-start-here.md) y
[active-context](active-context.md). Esta lista no autoriza trabajos ni publicaciones.
El historial y los checklists anteriores se conservan en
[archivo documental](reports/session-context-before-close-2026-09-16.md).

## Suspensiones de modelos — 19/09/2026

- [x] Preparar para la próxima versión HA el panel de suspensiones cerrado por
  defecto: retirado `open` del elemento `details`. Publicado en 0.2.315.
- [x] Incluir ese ajuste visual en la release 0.2.315.
- [x] Preparar JSON independiente de suspensiones y exportación/importación en
  Workers. HA local reconstruido: ocho archivos ejecutables cotejados por SHA,
  formulario probado en Chrome con las mismas siete reglas y sin modificar el
  registro de generaciones. Smoke inicial: 1.660 tests, 48 omitidos. Publicado en 0.2.315.
- [x] Reconstruir HA local y worker y validar la cadena integrada antes de
  publicar 0.2.315: 714 entrenamientos correctos y precálculo activado.
  Smoke final 1690 tests, 48 omitidos; ver informe de release.
- [x] Implementar suspensión/reactivación por especie o global desde Workers y
  trabajos; persistencia y transporte al worker, filtro anterior a la caché.
  [Contrato y estado local](mushrooms/model-suspensions-es.md).
- [x] Validar precálculo y mapa local/worker con HGB/KNN/SVM-V2 suspendidos.
- [x] Ampliar a HGB de ambos perfiles V3/V4 para rovelló: siete reglas en HA local,
  guardadas mediante el formulario tras autorización.
- [x] Verificar la cadena de entrenamiento lanzada por el usuario: lote nuevo
  instalado, siete reglas conservadas, 14 artefactos suspendidos entrenados y
  verificados por SHA; 56 combinaciones excluidas y 35 selecciones válidas en
  cinco puntos. Paridad mapa local/worker correcta en dos puntos.
- [x] Verificar resultado y activación del precálculo `worker_job_O7yzs0AqVMK6`: recibo,
  SHA, siete reglas y ausencia de ganadores suspendidos.
- [x] Publicar HA 0.2.314: GHCR versión/latest, mismo digest, AMD64 y ARM64
  verificados. [Informe](reports/ha-release-0.2.314.json).
- [x] Configurar las siete suspensiones en HA real 0.2.314 mediante su formulario;
  comprobadas de nuevo por SMB el 19/09. Generaciones conservadas al aplicarlas.
- [ ] Usuario avisará tras entrenamiento/precálculo en HA real para verificar sus
  resultados; no lanzar ni repetir esos trabajos automáticamente.
- [x] Verificar las siete reglas en el snapshot de entrada del entrenamiento,
  tanto en HA local como dentro del worker. Pendiente su resultado, no confundir
  transporte correcto con validación completa de la cadena.
- [ ] Revisar científicamente los modelos cuestionados antes de reactivarlos:
  estabilidad ante trazas de lluvia, independencia de vecinos de KNN,
  calibración y respuesta temporal. Suavidad por sí sola no prueba precisión.
- [ ] Corregir y versionar de forma coherente el criterio de día lluvioso/racha
  seca en entrenamiento e inferencia; evaluar umbrales con evidencia, sin cambiar
  la semántica de artefactos existentes. KNN: comprobar independencia por ID de
  observación, no solo igualdad de atributos. [Resultados y límites](reports/rovello-model-sensitivity-expanded-2026-09-19.md).

## Pendiente del usuario — observaciones GBIF (17/09/2026)

- [ ] El usuario revisará las observaciones descargadas de GBIF en el visor local
  y les asignará Pendiente, Dudosa, Aceptada o Rechazada. [Visor y guardado](../local-apps/gbif/docs/guide.md).
- [ ] Esperar su indicación tras esa revisión para preparar la incorporación de
  las aceptadas y decidir las pruebas comparativas o zonas candidatas. Conservar
  el JSON de revisión; no importar, entrenar, generar setales ni aprobar citas
  automáticamente. No se afirma que la revisión ya esté terminada.

## Aplazado por el usuario — revisión GIS

- [ ] Retomar los **343 pendientes** de la tanda de 488: **331 sin investigación
  específica suficiente** y **12 con limitación específicamente documentada**.
  No dar los 12 por irresolubles. **No continuar ahora.**
  [Método breve](mushrooms/gis-soil-review-method-es.md) ·
  [recuento, evidencias y validación](gis-review-2026-09-16.md).
- [ ] Al retomar, revalidar hashes, cola, fuentes y ámbito por código; aceptar solo
  lo justificado, conservar registros ajenos y comprobar ambos lectores.
  Los 567 suelos aceptados anteriores no cuentan como nuevamente investigados.

## Seguimiento 18/09/2026

- [x] Corregir tamaño del campo de búsqueda a 16 px y añadir su uso a la ayuda
  ES/CA/EN. HA local reconstruido; Chrome móvil, traducciones y huellas correctos.
- [x] Revisar créditos del mapa: Photon/komoot, OSM, OpenTopoMap y OpenFreeMap/
  OpenMapTiles; panel desplazable y comprobado en HA local móvil ES/CA/EN.
- [x] Publicar 0.2.312 con corrección, ayuda y créditos: autorizada y verificada
  en GHCR, ambos tags/digest y arquitecturas. [Informe](reports/ha-release-0.2.312.json).
- [x] Usuario confirma el 18/09 que el buscador funciona bien en iPhone y Safari
  del Mac después de publicar 0.2.312. Incidencia de zoom cerrada por su
  validación en dispositivos reales.


- [x] Implementar diagnóstico de errores del ejecutor local del mapa y lectores:
  componente, traceback y stderr visible. Cinco pruebas nuevas y suite dirigida
  correcta (161 casos, 48 omitidos). Cambio en worktree posterior a 0.2.310.
- [x] Instalar/validar ese cambio en HA local y worker: ambos reconstruidos,
  paridad 202/108 archivos y dos puntos coincidentes. Suite de 1.639 tests,
  48 omitidos. 0.2.311 aceptada, publicada y verificada en GHCR.
  Reintento controlado solo propuesto.
  El reinicio de HA real por el usuario recuperó el servicio; causa inicial no
  recuperable a partir de los logs antiguos.
- [x] Visor local de investigación WU: 3D/norte, disponibilidad X/30, cuatro
  estados con guardado SQLite, búsqueda por clic con modal, promoción a candidata
  y limpieza persistente de preliminares/puntos consultados. [Uso](station-research-es.md). Sin altas operativas.
- [ ] Revisar calidad de candidatas WU del primer análisis de cobertura de Catalunya.
  Análisis inicial: 143 nuevas identificadas y 12 priorizadas por geometría.
  Son recuentos históricos; comprobar el SQLite antes de afirmar estados actuales.
  [Informe local](../local-apps/wunderground/data/README.md). Preparar
  históricos/backfill solo después de acordar el lote y aprobar estaciones.

## Próximo bloque operativo, cuando se solicite

- [x] Trasladar los visores WU y GBIF a `local-apps/{wunderground,gbif}/{code,data}`.
  SQLite WU íntegro (179 registros, 506 entradas de caché, 19 eventos); snapshots
  GBIF verificados por SHA al mover 4.359 archivos. Se conserva la URL WU y
  enlaces de compatibilidad GBIF sin duplicar fotografías. Datos excluidos de
  Git y ambas aplicaciones excluidas de las imágenes Docker.

- [x] Retirar el entorno aislado de reconstrucción de julio por autorización
  del usuario: eliminados `docker-compose.rebuild-test.yml` y
  `options.rebuild-test.json`; documentación actualizada. No había contenedor
  ni imagen etiquetada de ese entorno. HA local y worker sin cambios.
- [ ] Continuar la revisión selectiva del espacio del workspace. Los duplicados
  GIS autorizados el 19/09 ya se retiraron (véase el registro siguiente).
  [Inventario del 18/09](reports/repository-disk-audit-2026-09-18.md): 62,4 GB,
  con 15,6 GB de posibles copias GIS identificadas por ruta/tamaño y 4,5 GB
  de auditorías. No sumar estas cifras como ahorro ni borrar automáticamente.
  Antes de retirar archivos, revalidar inventario, comparar contenidos mediante
  hashes, revisar consumidores y comprobar HA local/laboratorio. Conservar
  fuentes únicas, observaciones, fotos GBIF, revisiones WU y trabajo GIS aplazado;
  separar informes y entradas únicas de derivados reproducibles. La limpieza
  restante queda pendiente de autorización expresa.
- [x] Comparar por SHA-256 las parejas de la raíz y `docker-media/rainmapper/geography`
  el 19/09: 1.432 archivos idénticos en `mushroom-GIS` (6.820.316.846 bytes) y
  2.149 en `mushroom-map-GIS` (8.801.926.945 bytes). No son hardlinks. La raíz
  también contiene 101 y 5.707 archivos, respectivamente, sin pareja en media.
  No equivale a ahorro físico garantizado en APFS. Inventario previo al borrado.
- [x] Retirar los duplicados GIS autorizados: 1.422 archivos de `mushroom-GIS`
  y 2.079 de `mushroom-map-GIS`, tras repetir SHA-256 inmediatamente antes de
  borrar cada copia raíz. Total: 15.620.730.911 bytes lógicos; aumento neto
  observado de espacio libre: 498.569.216 bytes, con otros servicios activos.
  Conservados archivos únicos, scripts, documentación y metadatos. Las copias
  canónicas en `docker-media` no se modificaron.
  Tras el borrado, lector geográfico de HA local preparado y consulta de Capolat
  correcta: municipio, terreno, árboles, vegetación, geología y ecología disponibles.
  Sin reiniciar servicios.
  [Registro](reports/local-gis-duplicate-cleanup-2026-09-19.json).
- [x] Comprobar dentro de HA local que GIS y mapa utilizan `/media/rainmapper/geography`,
  montado desde `docker-media/rainmapper/geography`. Revisar antes de consolidar
  las referencias de adquisición/auditoría que todavía usan las carpetas raíz.
- [ ] Revisar crecimiento de caché de builds: variables de versión preceden a
  instalación de dependencias en ambos Dockerfiles. La limpieza autorizada de
  caché no usada en 24 h devolvió 0 B; no se borraron imágenes ni volúmenes.
  Establecer una retención acotada y evitar reinstalar dependencias por cambios
  de versión, con validación del empaquetado antes de aplicar ajustes.
- [x] Reorganizar media en HA local y real: HA real 0.2.310, seis movimientos,
  1.550 archivos conservados; 4.942 duplicados verificados y retirados (21,36 GB
  lógicos). Datos privados y runtime intactos, SQLite correcto y lectores
  preparados tras retirada. [Informe](reports/ha-media-migration-2026-09-18.json).
- [x] Usuario confirma que el mapa de HA real funciona en local y worker después
  de la migración. Comprobaciones offline de datos, lectores y SQLite correctas.
- [x] Usuario comunica que utiliza 0.2.311 en iPhone: buscador con POI y diagnóstico de errores.
  No parar, instalar ni arrancar HA real por su cuenta.
- [x] Confirmar versión efectiva de HA real: 0.2.309 por SSH LAN el 17/09.
- [ ] Comprobar sin trabajos costosos el consumo efectivo en HA real/worker de
  los JSON GIS subidos. El mapping almacenado **coincidía byte a byte** con
  HA local en la comparación del 17/09; no volver a copiarlo por rutina. La comparación
  no acredita el runtime ni revalida el JSON de auditoría.

## Completado el 17/09/2026

- [x] Publicar HA 0.2.309 y enviar commit `0ce6de3` a `origin/inicial`.
  [Informe](reports/ha-release-0.2.309.json): HA local/worker reconstruidos,
  paridad 200/107 archivos, smoke 1.615 tests con 48 omitidos y Chrome correcto.
- [x] Incluir aplicabilidad IFF por magnitud, tooltip, suelo no determinado,
  error comprensible de referencia suelo/pH y descartes completos por fecha.
  Conservar control por especie; no exigir suelo identificado globalmente.
- [x] Comparar mapping almacenado en HA real/local, SHA y contenido idénticos.
  [Evidencia](reports/gis-mapping-ha-parity-2026-09-17.json).
- [x] GBIF: cuatro estados, autoguardado y herramientas versionadas; datos, fotos
  y revisiones personales excluidos de Git e imagen. Revisión manual pendiente.
- [x] `IFF:` del Predictor publicado en 0.2.308, instalación de esa versión
  terminada según el usuario; conservado en 0.2.309.

## Completado anteriormente (16/09/2026)

- [x] Publicar HA 0.2.307; usuario confirma instalación.
  [Evidencia de release](reports/ha-release-0.2.307.json).
- [x] Presentación IFF, traducciones, colores, fechas, compactación y ayuda del
  mapa incluidas en el trabajo de release; no confundir pruebas funcionales con
  validación científica ni emulación con iPhone físico.
- [x] Justificar y aceptar 145 códigos nuevos (95 silíceos, 32 mixtos, 18 calcáreos)
  e incorporarlos a HA local. Últimos mappings comprobados en ambos lectores del
  contenedor para los 1.055 códigos; inventario total 1.336 preservado.
- [x] Usuario comunica subida de los dos JSON a HA real; consumo remoto aún no
  verificado. No requiere entrenamiento/precálculo para el mapa puntual.
- [x] Corregir dos puntos de IFF en el Predictor local, conservando tooltip.
- [x] Limpiar GHCR/entregas obsoletas/copias locales/caché Docker autorizadas,
  conservar datos activos y Python 3.11. Medidas y límites en el informe GIS.
- [x] Documentar método, distinguir investigación insuficiente de limitación
  investigada y dejar el resto aplazado por instrucción del usuario.
- [x] Renovar documentación de continuidad y archivar contexto histórico.

## Pendientes de producto y ciencia — no reabrir automáticamente

- [ ] Recuperación de arbolado vecino: concretar criterio/radio, distancia y
  procedencia; el vecino de pH no la sustituye.
- [ ] Revisar vinosus y demás fichas con evidencia específica, sin restaurar
  rangos antiguos ni crear vetos globales; conservar ediciones del usuario.
- [ ] Contrastar compatibilidad y valores IFF con setales conocidos; auditar
  incertidumbre espacial de GIS/IDW y transferencia a puntos nuevos.
- [ ] Ampliar regresión de estilos/gestos y convivencia de modos en Safari/iPhone.
  El zoom del buscador ya está validado por el usuario en 0.2.312; eso no cubre
  toda la regresión móvil. No abrir administración local a la Wi-Fi.
- [ ] Corregir la tarjeta del worker que muestra **«En espera» durante un
  entrenamiento activo**. Diagnóstico confirmado el 18/09/2026 mediante
  `GET http://127.0.0.1:8110/health`: estado general `idle`,
  `lanes.foreground.status=idle` y `lanes.background.status=busy`, con un
  `active_job_id` en segundo plano. Es evidencia de ese instante, no del estado
  futuro del trabajo. En `rainmapper_core/mushroom_worker_service.py`, tanto
  la respuesta de salud como el heartbeat toman el estado general únicamente
  de `foreground`; `_worker_card` en `rainmapper-app/app/mushroom_workers_ui.py`
  representa `payload.status` sin considerar `lanes`.
  Mostrar «Ocupado» si cualquiera de los dos carriles está ocupado y distinguir
  la disponibilidad para consultas del mapa de la actividad de entrenamiento/
  precálculo. Revisar también la actualización automática de la tarjeta y
  preservar los estados de desconexión y dataset no disponible. No cambiar la
  planificación ni bloquear consultas por corregir el indicador. Añadir pruebas
  dirigidas para ambos libres, solo segundo plano ocupado, solo primer plano
  ocupado y ambos ocupados. **Aplazado por el usuario**; no se ha cambiado código
  ni interrumpido el entrenamiento durante el diagnóstico.
- [ ] Medir cola/transporte/render, RAM e IO en destino con límites RPi4; no
  extrapolar mediciones del Mac ni repetir trabajos caros para diagnosticar.
- [ ] Completar integración nacional GEODE/MFE, esquemas regionales e índices
  usando descargas existentes. Catalunya no acredita cobertura española completa.
- [ ] Al ampliar consumidores GIS, comprobar compatibilidad de grupos de reglas;
  los dos lectores de los mappings actuales sí se han verificado.
- [ ] Completar aceptación geográfica en máquina independiente/AMD64 antes de
  retirar originales que aún se necesiten. Revalidar estado previo, sin rehacer
  la consolidación ya acreditada por los informes del 15/09.
- [ ] Ampliación separada: superficie coloreada por zona visible; no precalcular
  todos los puntos del territorio por inferencia del informe puntual.

## SoilGrids y enriquecimiento general

- [ ] Completar lector común/agregación por áreas, deltas y pruebas de recursos
  al retomar integración general; medir y deduplicar antes de transportar.
- [ ] Separar mostrar pH/profundidad/incertidumbre, migrar almacenamiento y cambiar
  variables de modelos. Preservar anotaciones y comprobar contratos antes de migrar.
- [ ] Revisar rangos provisionales ante nueva evidencia; no generalizar aereus
  a 7,5 ni inventar pH del suelo desde litología.
- [ ] Francia: ecología/geología y normalización forestal pendientes;
  DEM/SoilGrids puntuales no acreditan cobertura ecológica.

## Predictor y operación — pendientes conservados

- [ ] Aplicabilidad multiespecie (Rovelló / Els Ports / 07/09/2026), sin tolerancia
  global inventada; distinguir modelo ausente de modelo vetado.
- [ ] Catálogo de especies posibles por área y evaluador persistido hold-out que
  sustituya Historial; mensajes separados de entrenamiento/precálculo/corrupción.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando los hold-outs externos
  contengan ambas clases; no reabrir contador de días secos sin evidencia nueva.
- [ ] CLI worker por asociación; medir transferencia/hash/escritura/promoción
  antes de cualquier diseño de streaming.
- [ ] Runner externo/AWS/servidor doméstico y Python 3.14: futuros, no migrar ahora.
- [ ] Revalidar incidencia meteorológica Barcelona/Erinya y controles del runner
  antes de actuar: [informe histórico](reports/weather-coordinate-conflict-2026-09-13.json).
- [ ] Microáreas francesas y Meteo-France frente a Wunderground: bloque separado.

No relanzar reconstrucción, entrenamiento o precálculo para un cierre documental.
No borrar auditorías ni el directorio de trabajo de la revisión aplazada.
