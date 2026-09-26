# Setales desde observaciones: navegación y círculos (25/09/2026)

**Cierre posterior:** incluido en [HA 0.2.324 publicada el 26/09](release-ha-0.2.324-2026-09-26.md). El resto acredita las comprobaciones locales en las fechas indicadas.

Implementación y comprobación en HA local, sin publicación ni actualización real.

- El enlace «Gestionar zonas conocidas» abre otra pestaña para conservar el
  formulario original. Transmite el ID de la observación, las coordenadas actuales
  del formulario y el ID de la microárea seleccionada; conserva el regreso con filtros.
- Setales abre la ficha de la microárea y centra el mapa en la observación. El punto
  permite consultar especie, fecha, florada, observador, incertidumbre y microárea,
  además de acceder al detalle. Las coordenadas modificadas se identifican como
  posición del formulario; el resto de la ficha corresponde al registro guardado.
  Sin observación guardada se muestra sólo la posición. Se transporta una ficha,
  no todas las observaciones. Coordenadas inválidas/no finitas no llegan al mapa.
- Botón para volver a centrar la observación. Su marcador permanece al buscar
  otro lugar o cambiar de setal. En ventana estrecha, centrar oculta los paneles
  para dejar visible el punto, sin descartar cambios.
- El buscador admite `42.15, 1.44`, `42.15 1.44` y `42,15; 1,44`, siempre
  latitud y longitud. Valida rangos y resuelve coordenadas sin petición Photon;
  mantiene Photon para topónimos.
- En edición de geometría de áreas y microáreas: «Dibujar círculo», clic en el
  centro y segundo clic en el borde. Se guarda un Polygon GeoJSON; permite editar
  sus vértices posteriormente. Mantiene el guardado explícito y el circuito
  existente de geometría/GIS/DEM/SoilGrids. No cambia contratos de modelos.

## Verificación

- 4 pruebas de contexto de observación, 4 de setales y 2 de perfiles: correctas.
  Casos de coordenadas no finitas/fuera de rango, posición del borrador, ausencia
  de referencia y exclusión de observaciones ajenas al contexto.
- `tests/known_sites_navigation_browser_check.mjs --local-preview`: Chrome real
  con MapLibre/TerraDraw; enlace con latitud recién editada, selección y centrado,
  popup, búsquedas directas y Photon simulado, círculo dibujado con clics reales,
  guardado de área y reapertura de vértices, círculo de microárea y descarte,
  vista estrecha y consulta de mapa/popup en HA local. Sin errores JavaScript.
- Las escrituras de la prueba usan `known_sites_navigation_fixture.py` y un
  almacén temporal; HA local persistente sólo se consulta. No se importaron ni
  modificaron observaciones privadas ni setales del usuario.
- HA local reconstruida/recreada. Paridad: **228 archivos, cero diferencias**,
  SHA agregado `dc724f23facf5ce6be995838c38ab51964ac55be3cb914e37c4ab03a944f026d`.
  Worker sin cambiar contenedor, imagen, arranque, coordinadores ni credenciales;
  observaciones y política/suspensiones con las mismas huellas antes/después.
- Evidencia: `tmp/sites-navigation-20260925/{before,after,parity}.json`;
  log `/private/tmp/sites-navigation-browser-final.log`; capturas en
  `/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/sites-navigation-Hk3mFL/`.
  Compilación Python, sintaxis JavaScript y `git diff --check` correctos.

No se lanzó entrenamiento/precálculo, no se operó el worker ni HA real, y no se
hizo commit/push. La mejora del esquema del plan de importación GBIF sigue
aplazada en TODO; este cambio corresponde al mantenimiento de setales.

## Corrección del 26/09: microárea existente y clic sobre marcador

El caso añadido reproduce un centro interceptado por el marcador DOM: el segundo
clic iniciaba otro círculo con radio mínimo, todavía sin terminar. La prueba
anterior sólo comprobaba la presencia de suficientes vértices, por lo que no
acreditaba el centro/radio ni que hubiera terminado. Se amplió para comprobarlos.

Ahora se ignoran marcadores/popups durante el dibujo; sólo IDs de geometrías
terminadas se sincronizan al formulario. La elección en un setal existente permite
sustituir su contorno o añadir otro círculo. Sustituir sólo retira la geometría
anterior al terminar el nuevo círculo. Modo resaltado, radio/instrucciones y
ocultación del contorno persistido durante la edición, manteniendo el borrador.

Prueba ampliada: microárea existente, clics reales sobre el punto de observación,
radio ≈412 m y centro comprobados; sustitución guardada en almacén temporal,
añadir/descartar, círculo incompleto preservando original, polígonos nuevos,
reapertura, móvil y consulta de HA local. Sin excepciones JavaScript. Ocho pruebas
Python dirigidas correctas. Captura:
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/sites-navigation-wAMJGn/existing-circle-active.png`.

HA local reconstruida/recreada; 228 archivos iguales al worktree, SHA agregado
`347ab1e7cd6f0d15ed6a9272c4318aa56fdcb616390f24e97e96205fcb6a5738`.
Auditoría `tmp/sites-circle-20260926/`: worker y datos privados intactos.
Log `/private/tmp/sites-circle-browser-final.log`. No release ni trabajos operativos.
