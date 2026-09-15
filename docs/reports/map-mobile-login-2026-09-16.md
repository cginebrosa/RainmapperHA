# Encuadre del mapa después de iniciar sesión en iPhone

El usuario confirma recorte de cabecera, controles derechos y leyenda después
del login, tanto en Safari como en Chrome del iPhone. Escritorio funciona.
Posteriormente informa de recorte también al refrescar con sesión guardada;
el login por sí solo no explica todo el comportamiento observado.

Hipótesis del síntoma: zoom nativo al enfocar campos pequeños. El navegador
local confirma que los cuatro inputs de acceso/cambio de contraseña heredaban
13 px de la etiqueta. iOS puede ampliar la página al enfocar un campo de texto
([WebKit](https://bugs.webkit.org/show_bug.cgi?id=157771)). No se dispone aquí
de una reproducción del zoom en un dispositivo iOS físico.

Cambios acotados al formulario compartido en `maplibre-viewer`:

- `style.css`: inputs de acceso y cambio de contraseña a 16 px.
- `app.js`: enfoque programático con `preventScroll`; liberar foco del
  formulario antes de ocultarlo al terminar el acceso.
- Segundo fallo reproducido: el mapa restaba una cabecera fija de 82 px en
  móvil, pero los filtros restaurados podían aumentar su altura. A 360×640,
  la prueba midió cabecera de 103,8125 px y mapa hasta 661,8125 px.
- `style.css`: distribución en grid con altura real de cabecera y resto para
  el mapa; altura `100dvh` con fallback previo `100%` y sin scroll del documento.
  Las unidades dinámicas se ajustan a la altura disponible del navegador
  ([WebKit 15.4](https://webkit.org/blog/12445/new-webkit-features-in-safari-15-4/)).
- `app.js`: observar cambios de tamaño del contenedor y llamar `map.resize()`
  cuando cambie la cabecera, aunque no haya evento de resize de ventana.
- Se conserva el viewport y la posibilidad de ampliar manualmente la página.

Prueba local `tests/prediction_map_browser_check.mjs` con MapLibre 4.7.1 local:
falló antes del cambio con `Mobile login input sizes: 13,13,13,13`; pasó después.
Comprueba foco, cierre del formulario y límites de cabecera, controles, leyenda
y selector de días a 390×664 y 390×844, además de la suite existente de mapa,
predicciones, popup, fechas, permisos y persistencia. Salida `ok: true`, 20
consultas de fixture, sin excepciones de navegador; proceso termina con código 0.
`git diff --check` correcto.

La comprobación ampliada recarga la página con sesión guardada a 360×640 y
390×744, restaura un resumen con filtros y verifica el ajuste del mapa y canvas.
Falló antes del segundo cambio con límite inferior 661,8125 > 640; pasó después,
junto con el resto de la suite (20 consultas). No reproduce el zoom nativo iOS.

Captura local inspeccionada:
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-Vxq8Y0/mobile-after-reload.png`.

Limitaciones: la emulación Chrome no reproduce el zoom nativo de iOS ni sus
barras reales. Falta comprobar el dispositivo tras una release aceptada.
No se ha publicado una nueva imagen ni modificado la instalación de HA real.

## Cabecera compacta y aceptación visual local

Cambios móviles en `prediction-mode.js` y `prediction-mode.css`: ocultar el
aviso experimental de la cabecera del popup; reunir coordenadas, altitud y pH;
poner la zona horaria junto a Data/Fecha sin su prefijo; reducir espaciados y
altura del gráfico conservando sus etiquetas. Cancelar mide 32 px de alto.
Tras la revisión del usuario, el selector de fecha pasa a 13 px de texto y
26 px de alto, con Data y la zona horaria alineadas por la línea base.

Suite de navegador repetida sobre estos cambios: `ok: true`, 23 consultas,
código de salida 0. Cabecera con terreno completo en es/ca/en a 360×640,
390×744 y 390×844: lista desplazable con 48,6 %, 56,4 % y 53,0 % del popup.
El test mide explícitamente la misma línea base de fecha/zona horaria, altura
del selector, metadatos en una fila y ausencia de desbordamiento horizontal.
Capturas: `/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-zkhneI/`.

Se reconstruyó y recreó únicamente `rainmapper-ha-ui` mediante el compose de
`rainmapper-local`, conservando los volúmenes. Los cuatro archivos de interfaz
del contenedor coinciden por SHA-256 con el worktree. Esta iteración visual no
reconstruye ni reinicia el worker y no constituye la puerta completa de release.

Safari: pestaña existente `http://127.0.0.1:8101/protected/maplibre/index.html`,
modo adaptable a 375×666. Tras recarga autenticada, cabecera 85 px y canvas
581 px: borde inferior exactamente 666 px. Consulta real local de Olvan
(42.06414, 1.93688) por worker: 2,10 s de consulta, 0,88 s de cálculo antes
del último ajuste de fecha. Lista ocupa 45,2 % con seis etiquetas de terreno;
scroll de 180 px conserva la cabecera y todos los controles quedan dentro.
La vista previa CSS temporal que se había añadido a la pestaña real se retiró;
las comprobaciones posteriores usan los archivos servidos por HA local.

Última comprobación Safari tras reconstruir también el ajuste de fecha:
selector 120×26 px, texto 13 px, línea base de Fecha y zona horaria idéntica
(y=280). Lista desplazable 46,5 % del popup; viewport 375×666 y canvas hasta
y=666. Consulta por worker 2,14 s, cálculo 0,87 s. `git diff --check` correcto.

Revisión posterior de texto: `ui.prediction_map_ecology_calculated` abreviado a
«Especies y temporada compatible», «Espècies i temporada compatible» y
«Compatible species and season». Cambio solo de traducciones, validación JSON
y diff; reconstrucción de HA local para verlo en la pestaña existente.

## Ajustes finales de calendario y ejecutor

Fila móvil: «Zona: Europe/Madrid» a la izquierda y «Fecha: selector» a la
derecha (Zona/Data en catalán y Zone/Date en inglés). Selector nativo con
apariencia compacta, fondo claro, 98×24 px y texto de 11 px. Los dos textos
comparten línea base; se conserva la fecha completa. Cancelar: texto 12 px,
relleno 3×8 px, borde suave y foco visible acotado. La ficha identifica el
cálculo local como «Local» en los tres idiomas.

Worker pasa a ser el valor inicial cuando no hay preferencia guardada. Se
respetan los valores explícitos Local/Worker anteriores, incluidos los del
prototipo. Si el POST inicial de Worker devuelve 503 con `worker_busy` o
`executor_unavailable`, el navegador reintenta una sola vez con ejecución
Local y un nuevo request_id, manteniendo punto, fecha y zona horaria.
No escribe el setting ni lanza ambas consultas a la vez. Un trabajo ya
aceptado sigue su cola normal; no se duplica tras un fallo genérico, una
cancelación o un timeout. El resultado muestra el ejecutor que lo calculó.

Pruebas de navegador: 29 peticiones, salida `ok: true`, exit 0; incluyen
default Worker, fallback por busy/offline, preferencia sin escrituras,
indisponibilidad de ambos, Local explícito y vuelta posterior a Worker.
Se conserva la suite de cancelación, fechas, permisos y geometría móvil.
Capturas finales:
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-r5d68G/`.
HA local reconstruido/recreado; bootstrap, módulo, CSS y labels efectivos
coinciden por SHA-256. No cambia el contrato ni código del worker/coordinador.

Safari con HA local reconstruido: prueba controlada interceptando solo el
rechazo inicial de Worker (503 `executor_unavailable`), sin detenerlo ni cambiar
sus coordinadores. Intentos registrados Worker → Local; HA local respondió
202 y después 200 con `execution.mode=local`. La ficha mostró «Local · Temps
de consulta: 2.03 s · Càlcul: 0.93 s»; selector siguió en Worker y el objeto de
settings permaneció idéntico. `fetch` original restaurado automáticamente.
Botón Cancelar medido en Safari: 72,42×26 px, texto de 12 px.

## Cierre de release 0.2.305

Tras la aceptación del usuario, se reconstruyeron y recrearon HA local y el
worker desde la candidata definitiva. Paridad efectiva: 198 archivos HA y 106
worker, sin diferencias; URLs y huellas de configuración de los coordinadores
conservadas. Smoke: 1.600 tests, 48 omitidos, correcto. Consulta final real en
Safari local por Worker: 2,14 s total y 1,42 s cálculo.

Imagen 0.2.305 y latest publicadas con el mismo digest y manifests amd64/arm64,
verificados mediante `docker buildx imagetools inspect` para ambos tags.
[Metadatos y huellas](ha-release-0.2.305.json). Worker sigue en 1.1.2.
Instalación y prueba en iPhone físico pendientes del usuario; no se ha instalado
esta versión en HA real. No requiere regenerar mapas ni artefactos científicos.
