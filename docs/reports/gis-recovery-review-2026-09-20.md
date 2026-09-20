# Recuperación GIS / DEM revisable — 20/09/2026

Registro cronológico de implementación y validación, posterior al cierre de HA 0.2.315. Las menciones a publicación pendiente describen cada iteración. El conjunto se publicó después en HA 0.2.316, el 21/09/2026; instalación real a cargo del usuario. Véase el [informe final de release](ha-release-0.2.316.json). Se han conservado los cambios documentales anteriores y las observaciones privadas; las pruebas usan fixtures o lecturas de archivos existentes.

## Comportamiento

- Microáreas: `Recuperar GIS / DEM` incorpora MFE25, además del contexto MVC50/geológico existente. La revisión permite mantener, fusionar listas o reemplazar cada campo. Altitud y notas admiten mantener/reemplazar. Aplicar devuelve la ficha como borrador; Guardar sigue siendo una acción posterior.
- Observaciones, en el formulario común de creación/edición/duplicación: recuperación explícita de hosts, bosque, tendencia de suelo, hábitat y altitud disponibles en las coordenadas de la ficha. Se presentan valor actual, propuesta y fuentes. Mantener no cambia el campo; fusionar conserva campo y GIS previo; reemplazar sustituye el campo seleccionado. Aplicar no envía el formulario ni cierra la ficha.
- Los datos inferidos se guardan en `site_context.gis_recovery`, separados de `observed_*`. Reemplazar un campo elimina sus valores anteriores de campo por decisión explícita; los nuevos valores siguen siendo GIS. Una nueva ubicación invalida el GIS anterior. La validación comprueba tamaño, coordenadas y referencias al catálogo.
- La reconstrucción consume la selección GIS guardada en la observación congelada; no consulta una publicación MFE mutable desde el worker. El ensamblado conserva la distinción `field`/`gis`. Esto no añade columnas categóricas a los modelos ML actuales ni modifica sus afinidades de especie.

## Agregación MFE25

`ForestReader.lookup_polygon` utiliza el índice espacial y las geometrías preparadas del mismo lector que el mapa puntual. Une los taxones registrados en todas las intersecciones con superficie positiva; respeta los huecos y excluye contactos únicamente por borde. Cada polígono aporta sus especies registradas, sin umbral arbitrario de dominancia.

El área y la fracción de intersección describen el polígono forestal, **no** la abundancia o cobertura de cada árbol. Se conservan nombres científicos sin correspondencia en el catálogo, sin inventar IDs. MFE no se presenta como inventario exhaustivo. Límites: 2.048 vértices consultados, 64 candidatos/partes, 2 MiB por geometría, 8 MiB de geometrías candidatas, resultado forestal de hasta 60.000 bytes. Un límite devuelve estado explícito, no un conjunto parcial presentado como completo.

El suelo recuperado es una tendencia de la cartografía geológica configurada; no mide pH ni equivale a las propiedades hidráulicas de SoilGrids. Este cambio unifica la fuente MFE de hosts. No afirma que todas las capas del mapa puntual y del GIS histórico sean idénticas.

## Evidencia local

- Pruebas dirigidas de lector MFE, recuperación, formularios, validación de datos, ensamblado de características, reconstrucción y empaquetado: correctas.
- Chrome con formulario temporal: mantener, fusionar, reemplazar, cancelar, invalidación por coordenadas, ausencia de guardado y permanencia de la ficha abierta: correctos.
- Caso de referencia: geometría descargada de los sites actuales, geografía local publicada y catálogo vigente leído por SMB. El punto aporta roble pubescente, pino rojo y avellano. La intersección de la microárea incluye los tres y además haya y roble albar; ocho polígonos intersectados. La respuesta de diagnóstico conjunta ocupa 4.987 bytes; el recorrido del adaptador local tardó aproximadamente 2,13 segundos en esta ejecución.
- Descargas en `docker-data`: 497 observaciones; 41 áreas y 78 microáreas. Ambos JSON coinciden byte a byte con los leídos por SMB de HA. Meteorología: generación `20260920T120508029057Z-61d7f47fdb95`, manifiesto/puntero coincidentes con HA, 47 archivos locales, 52.296.533 bytes y 5.536.295 filas declaradas; todos los hashes locales coinciden con el manifiesto. No se han rehasheado las particiones meteorológicas en HA.
- Evidencia detallada local, ignorada por Git: `tmp/gis-recovery-20260920/downloads-verification.json`, `service-probe.json`, `refugi-mfe.json`. Auditoría inicial de HA 0.2.315: `tmp/ha-0.2.315-audit-20260920/verification.json`; es anterior a las últimas observaciones añadidas y a la descarga meteorológica posterior.

## Antes de una release

Falta el circuito obligatorio de aceptación de release con HA y worker del mismo código y, por afectar a la reconstrucción, el circuito aplicable definido en `AGENTS.md`/`docs/release-flow.md`. Se ha reconstruido únicamente la imagen HA local existente para revisar la interfaz. No se han cambiado coordinadores ni se han lanzado entrenamientos o precálculos. La instalación en HA real sigue pendiente. Los datos existentes no se recuperan ni se reescriben automáticamente: el usuario inicia la recuperación y decide qué guardar.

## Verificación posterior en el HA local servido

El usuario indicó que el botón no aparecía. Se confirmó que el contenedor seguía usando la imagen anterior y se corrigió además la omisión de `mushroom_observation_gis_ui.py` y `observation-gis.js` en los COPY explícitos del Dockerfile HA. Se reconstruyó y recreó exclusivamente `rainmapper-local-rainmapper-ha-ui-1`, con su imagen habitual `rainmapperha:local-ha-ui` y los mismos montajes.

- Ocho archivos efectivos del contenedor comparados por SHA-256 con el worktree: coincidentes.
- `node tests/observation_gis_browser_check.mjs --local-read-only`: Chrome abrió una ficha de observación del servidor `127.0.0.1:8101`, pulsó Recuperar GIS / DEM y recibió la revisión con cuatro campos; ficha abierta y ninguna acción de guardado.
- Los siete tests de empaquetado pasaron, incluidas las comprobaciones de los archivos omitidos.
- Huellas de observaciones privadas/locales, sites y puntero meteorológico: conservadas. Las huellas de `coordinator.json` y `additional-coordinators.json` del worker también quedaron idénticas; el worker no se recreó.

Esta comprobación acredita el despliegue y la vista previa de la interfaz local. No acredita el circuito completo HA–worker requerido para publicar otra release.

### Ajuste de interfaz solicitado posteriormente

El botón de observaciones se trasladó al pie de la ficha, inmediatamente después de Mapa. La recuperación usa ahora un diálogo modal independiente, fuera del formulario y de la columna de evidencia de campo. Aplicar, cancelar o Escape cierran únicamente la revisión y mantienen abierta la ficha; Guardar sigue siendo explícito. Cerrar durante la consulta cancela la espera del navegador y una respuesta tardía no vuelve a abrir el diálogo. Los estados MFE se explican en lenguaje legible, incluyendo que un polígono sin árboles registrados no demuestra ausencia real.

HA local reconstruido y recreado con este ajuste; tres archivos de interfaz efectivos coinciden por SHA-256 con el worktree. Chrome verificó posición después de Mapa, columna derecha libre, revisión modal y cierre con Escape conservando la ficha. El fixture verifica además mantener/fusionar/reemplazar/cancelar sin guardar; nueve pruebas dirigidas de recuperación correctas. Huellas de observaciones privadas/locales y sites conservadas. El worker y HA real siguen sin actualizarse en esta revisión de interfaz.

### Corrección de legibilidad e inspector del mapa

La captura del modal vacío correspondía a un fallo de contraste: el diálogo usaba `--text`, variable inexistente en el tema, y heredaba su fallback oscuro sobre `--card` oscuro. Corregido a `--fg` en `mushroom_observation_gis_ui.py`. La consulta del punto de referencia sí devuelve hosts, suelo calizo y 938,25 m; no era ausencia de datos. La prueba Chrome ahora exige contraste mínimo 4,5:1 en encabezados y celdas, además de comprobar contenido y cierre sin guardar.

El mapa individual de una observación incorpora el botón GIS / DEM en dos líneas. Al activarlo consulta las coordenadas del borrador y muestra un panel a la derecha de la foto; los clics posteriores consultan el nuevo punto con marcador propio. Devuelve hosts, bosque, tendencia de suelo, hábitat y altitud disponibles, fuentes y estados explícitos sin datos. La API añade etiquetas legibles únicamente para los IDs devueltos. El inspector no modifica coordenadas, asignación de microárea ni evidencia. Durante la consulta quedan deshabilitados los controles de edición; al salir recuperan su estado anterior. No se activa sobre una edición de geometría/coordenadas en curso. Se mantiene una consulta simultánea por inspector y solo el último punto pendiente; las respuestas antiguas o posteriores al cierre no actualizan la vista.

Comprobaciones de esta iteración:

- 16 tests de recuperación/empaquetado y 2 tests existentes de página/detalle: correctos.
- Fixture Chrome: decisiones del modal, invalidación por coordenadas y permanencia de la ficha; inspector sin guardado, serialización de consultas, descarte de respuesta antigua y restauración de controles: correcto.
- Chrome contra HA local: contraste del modal, datos recibidos, cierre con Escape; inicialización MapLibre con WebGL por software, consulta inicial y cambio de punto, etiquetas legibles, panel sin solapamiento con controles y conservación de coordenadas/sites: correcto. Se revisaron además las capturas guardadas en `tmp/gis-recovery-20260920/`.
- HA local reconstruido/recreado; huellas de los archivos de interfaz/API efectivos coinciden con el worktree. Observaciones privadas/locales y sites conservan sus hashes respecto al inicio de esta corrección (`contrast-before.json`).

No se ha actualizado HA real ni el worker ni se han ejecutado entrenamientos o precálculos. Esta comprobación sigue siendo una validación de interfaz local, no la aceptación completa de una release.

### Selección visible después de aplicar al borrador

El usuario mostró que Reemplazar desmarcaba los hosts/suelos de campo y no resaltaba los GIS aceptados. La revisión guardaba correctamente los nuevos IDs en el JSON del borrador, pero los selectores solo reflejaban `observed_*`. Corregido en `observation-gis.js`: se resaltan los valores GIS en verde con distintivo `✓ GIS`, también al volver a abrir una ficha con GIS guardado. Los valores de campo mantienen su selección independiente. El estado visual GIS utiliza `indeterminate`, sin enviar esos IDs como observaciones de campo; así tampoco les aplica incorrectamente el límite de tres árboles observados. Pulsar un valor GIS lo quita del borrador; cambiar coordenadas elimina las marcas GIS. La leyenda explica los dos orígenes.

El aviso de aplicación se mueve a una fila completa del pie, fuera de la fila de botones que no admite saltos de línea. Se evita así el solapamiento mostrado en la captura.

Validación: nueve tests Python de recuperación/formulario correctos; fixture Chrome verifica mantener/fusionar/reemplazar, marcas GIS, separación de procedencia en FormData, rehidratación, eliminación manual y cambio de coordenadas. En HA local, Chrome aplicó sin guardar la consulta del punto de referencia, reemplazando hosts/suelo y manteniendo altitud: cuatro hosts y Calizo resaltados, ficha abierta, datos GIS separados y aviso bajo los botones. Captura revisada en `tmp/gis-recovery-20260920/applied-gis-selection.png`. Dos archivos efectivos del contenedor coinciden por SHA-256; hashes privados/locales/sites conservados frente a `selection-before.json`. Solo se reconstruyó/recreó HA local.

### Valores por defecto de la revisión GIS / DEM

A petición del usuario, cada campo recuperado propone Reemplazar si difiere del valor actual (campo + GIS) y Mantener si coincide. Las listas se comparan como conjuntos de IDs, sin depender del orden; la altitud se compara numéricamente con el valor recuperado mostrado. Aplicar al borrador tiene estilo principal y recibe el foco al terminar la consulta. Sigue siendo una aplicación al borrador; no guarda la observación.

Fixture Chrome correcto para diferencias, igualdad de listas/altitud y foco principal. HA local reconstruido/recreado; la huella de `observation-gis.js` coincide con el worktree. La prueba de navegador abre la revisión y la cierra con Escape, sin guardar. Durante esta comprobación el JSON local de observaciones cambió de hash respecto a `defaults-before.json`; no se ha revertido ni se atribuye aquí la autoría de ese cambio. El JSON privado del repositorio y los sites conservaron su hash.

### Valores por defecto y anchura de decisión en microáreas

La revisión GIS/DEM de Setales propone ahora Reemplazar cuando el valor recuperado difiere del actual, incluyendo campos vacíos, y Mantener cuando coincide. Las listas se comparan como conjuntos y las altitudes numéricamente. La propuesta de pendiente usa el mismo texto que se aplica al borrador, evitando discrepancias de formato; la altitud cero se muestra como cero.

El selector dispone de anchura suficiente para Reemplazar. En pantallas de hasta 600 px cada campo se presenta como un bloque con valor actual, propuesta y decisión, sin comprimir las etiquetas. Se mantienen las acciones globales y el guardado explícito.

Validación: nueve pruebas dirigidas de recuperación correctas; fixture de valores distintos/iguales/vacíos, listas reordenadas, altitudes equivalentes y pendiente correcta. Chrome sobre la página de HA local, con revisión sintética insertada sin llamadas de escritura, confirma decisiones y selectores completos a 1600 y 375 px; capturas revisadas. HA local reconstruido/recreado y SHA-256 de los dos archivos efectivos coincidentes. Huellas de observaciones privadas/locales y sites conservadas. Evidencia en `tmp/sites-gis-defaults-20260920/` (ignorada por Git).

No se recreó el worker ni se inició entrenamiento/precálculo. La publicación 0.2.316 sigue pendiente de que el usuario termine de incorporar nuevas observaciones; la validación anterior de release precede este cambio de interfaz.
