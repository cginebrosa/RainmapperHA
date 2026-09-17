# TODO — cierre 16/09/2026

Arranque suficiente: [codex-start-here](codex-start-here.md) y
[active-context](active-context.md). Esta lista no autoriza trabajos ni publicaciones.
El historial y los checklists anteriores se conservan en
[archivo documental](reports/session-context-before-close-2026-09-16.md).

## Pendiente del usuario — observaciones GBIF (17/09/2026)

- [ ] El usuario revisará las observaciones descargadas de GBIF en el visor local
  y les asignará Pendiente, Dudosa o Aprobada. [Visor y guardado](mushrooms/GBIF/README.md).
- [ ] Esperar su indicación tras esa revisión para preparar la incorporación de
  las aprobadas y decidir las pruebas comparativas o zonas candidatas. Conservar
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

## Próximo bloque operativo, cuando se solicite

- [ ] Comprobar sin trabajos costosos que HA real/worker consumen los dos JSON
  que el usuario ha subido. No sobrescribirlos con copias antiguas.
- [ ] Incorporar `IFF:` del Predictor a una futura versión, tras validación local
  proporcional y aceptación; ya está en HA local, no publicado después de 0.2.307.
- [ ] Separar y revisar el diff documental/código antes de un eventual commit;
  preservar observaciones y `docs/mushrooms/GBIF/` del usuario.

## Completado en esta sesión

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
