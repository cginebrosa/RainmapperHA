# TODO — actualizado 18/09/2026

Arranque suficiente: [codex-start-here](codex-start-here.md) y
[active-context](active-context.md). Esta lista no autoriza trabajos ni publicaciones.
El historial y los checklists anteriores se conservan en
[archivo documental](reports/session-context-before-close-2026-09-16.md).

## Pendiente del usuario — observaciones GBIF (17/09/2026)

- [ ] El usuario revisará las observaciones descargadas de GBIF en el visor local
  y les asignará Pendiente, Dudosa, Aceptada o Rechazada. [Visor y guardado](mushrooms/GBIF/README.md).
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
- [ ] Usuario instala 0.2.312 y comprueba el foco/zoom en Safari de iPhone.
  La emulación móvil de Chrome no acredita el teclado/zoom de Safari físico.


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
  143 nuevas identificadas; 12 priorizadas por geometría, ninguna aprobada ni añadida.
  [Informe local](../tmp/station-coverage-catalunya-20260918/README.md). Preparar
  históricos/backfill solo después de acordar el lote y aprobar estaciones.

## Próximo bloque operativo, cuando se solicite

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
  los JSON GIS subidos. El mapping almacenado **ya coincide byte a byte** con
  HA local, comprobado el 17/09; no volver a copiarlo por rutina. La comparación
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
- [ ] Ampliar regresión Safari/iPhone físico, estilos/gestos y convivencia de
  modos meteorológico/predicción; no abrir administración local a la Wi-Fi.
- [ ] Revalidar si la tarjeta del worker muestra ambos carriles de actividad.
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
