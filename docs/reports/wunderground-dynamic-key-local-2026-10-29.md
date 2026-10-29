# Wunderground: clave dinámica y respaldo HTML — 29/10/2026

Cambio aplicado en `fix/wunderground-recovery-20261029`, desde la release
`99a4b6e1` (0.2.339), en `local/worktrees/wunderground-recovery`. El checkout
principal conserva sus cambios pendientes. La validación siguiente precede
a la publicación de 0.2.340; el cierre se enlaza al final del informe.

El runner obtiene la clave pública desde la configuración de una página de
estación y la comparte en memoria durante esa ejecución. Si falla una página,
prueba otras dentro del límite existente `max_attempts`. El scraper histórico
usa la cookie oficial del sitio antiguo. Se elimina la clave fija anterior;
el override explícito por entorno sigue disponible. El visor local de
investigación, que comparte el helper, conserva la clave en memoria hasta su
reinicio. [Funcionamiento y límites](../../rainmapper-app/DOCS.md#clave-dinamica-y-respaldo-html).

## Validación local

- 55 pruebas dirigidas pasan: descubrimiento, páginas incompletas, errores HTTP,
  claves de publicidad, concurrencia, nueva clave por ejecución, respaldo HTML,
  fechas, unidades y compatibilidad del visor local. 41 pruebas Wunderground
  pasan también dentro de la imagen reconstruida.
- Imagen reconstruida con `rainmapper-app/Dockerfile`. Las huellas de los tres
  archivos ejecutables modificados en HA coinciden dentro del contenedor con
  el worktree; no se ejecuta el código mediante un montaje del checkout.
- Runner real `web_server.run_action('update', ..., only_source='Wunderground')`,
  compartido por web/scheduler, con tres hilos y cierres de Parquet antes y
  después. Docker local limitado a 2 CPU y 2 GiB; copia aislada de los datos.
  No se reconstruye ni se modifica el worker ni el HA local habitual.

| Ejecución | Estaciones seleccionadas / actualizadas | Filas descargadas | Fuente | Runner completo | Preparación de clave |
|---|---:|---:|---:|---:|---:|
| API dinámica | 113 / 108 | 2.969 | 49,095 s | 53,880 s | 0,678 s |
| Respaldo HTML forzado, IALCAL123 | 1 / 1 | 29 | 4,679 s | 8,620 s | 0,004 s |

La segunda prueba usa una credencial de prueba inválida por entorno para provocar
el fallo de API. El respaldo recupera los 29 días de octubre sin errores de
estación. No se persiste una clave real. El primer runner prepara una sola clave
para las 113 estaciones. Pico RSS de proceso hijo: 478,61 MiB en la primera
ejecución; no representa el RSS total del contenedor ni el consumo de una RPi4.
Estos tiempos son mediciones locales puntuales, no un benchmark de Raspberry Pi.

La descarga y ambos cierres de archivo terminan con código 0 en las dos pruebas.
El runner completo termina con código 2 porque la copia meteorológica carece de
modelos del Predictor: `FileNotFoundError` al publicar su runtime. No se ha
validado ni ejecutado entrenamiento, precálculo o publicación de mapas.

## Cinco estaciones sin datos publicados para octubre

`IBAG57`, `IFUENT4`, `IGUILS1`, `ILAVAN3` e `IMONTF44` devuelven HTTP 204 por API.
Una lectura independiente del sitio antiguo, con fecha 29/10 y vista mensual,
devuelve HTTP 200, cero tablas históricas y **«No data available»** para octubre
en las cinco. Como control, IALCAL123 devuelve dos tablas. No se interpreta la
ausencia de datos como lluvia cero ni se garantiza cuándo volverán a publicarse.
Otras ocho respuestas siguen antiguas después de las variantes CDN; se mantiene
el diagnóstico existente, sin alterar su umbral ni inventar observaciones.

## Integridad de los datos

- Wunderground/2026 pasa de 31.587 a 31.699 claves estación/día en Parquet:
  112 claves nuevas y ninguna previa perdida. Las otras 45 particiones mantienen
  sus hashes; catálogo y todas las particiones activas verifican sus hashes.
- El CSV incremental pasa de 19.286 a 19.291 filas. El cierre existente aplica
  su retención: retira 107 filas del 02/05, anteriores al corte 03/05.
  Se comprueba que **las 107 siguen presentes en Parquet**. No es una pérdida
  de histórico ni un cambio de retención introducido por esta corrección.
- Los 80 archivos originales de entrada mantienen sus hashes.

La primera preparación del contenedor montó erróneamente la copia de
`stations.txt` como solo lectura y se detuvo antes de descargar; se corrigió
el montaje de esa copia. La primera comprobación del CSV exigía conservar todas
sus claves y se ajustó para verificar la retención real y su presencia en
Parquet. Ninguno de esos ajustes modificó código del descargador.

[Evidencia compacta](wunderground-dynamic-key-local-2026-10-29.json). Las copias
de datos, scripts y logs temporales, contenedores y etiqueta de imagen de prueba
se han eliminado. Se conservan código, tests y documentación.

## Activación posterior en el HA local habitual

El 29/10, a petición del usuario, se reconstruye `rainmapperha:local-ha-ui` y se
recrea `rainmapper-local-rainmapper-ha-ui-1`. La imagen activa es
`sha256:c5a6dd96e28a562ebb4bb94504bdf5975685e4445e69a15d4434bc1bbe9745de`.
Se comprueban nueve huellas dentro del contenedor: las correcciones de AEMET y
Wunderground están presentes. `http://127.0.0.1:8101/` responde HTTP 200.

El HA local llevaba una integración MCP propia que no está en la release base.
Para conservarla, el contexto de construcción local incorpora exactamente sus
dos módulos ya ejecutados y los cambios existentes de Dockerfile/web_server.
No se incorpora el resto del trabajo pendiente del checkout principal ni se
añade MCP a la candidata de release. Ese contexto temporal se elimina después
de construir y verificar la imagen.

Se mantienen todos los montajes y valores de Compose; el worker conserva su
contenedor y fecha de arranque. Modo `serve`, scheduler desactivado y ningún
runner lanzado por Codex: queda preparado para que el usuario lo ejecute desde
el panel local. No se publica ni se modifica HA real.

## Runner completo lanzado posteriormente por el usuario

Tras copiar de nuevo los datos de HA real, el usuario ejecuta `all` en el HA
local habitual. Según `docker-data/last_run.log` y
`docker-data/Data/source_status.json`, termina el 29/10 a las 21:39:27 +01:00
en 1 min 6 s. Wunderground queda `OK`, código 0: 113 estaciones solicitadas,
108 actualizadas y 2.969 filas, en 18,872 s; preparar la clave requiere 0,457 s.
Las cinco estaciones sin datos vuelven a agotar el respaldo HTML. Las ocho
respuestas antiguas se registran después de probar `gzip`, `identity` y
`deflate`, sin recuperación de observaciones más recientes.

El cierre Parquet registra 112 claves nuevas y 211 filas existentes modificadas
en Wunderground/2026, de 31.587 a 31.699 filas. La generación activa es
`20261029T203903804097Z-00de807f2c08`. Se generan y publican siete GeoJSON en
el entorno local. El código global 2 corresponde a AEMET `PARTIAL`: la descarga
horaria termina, pero falla un bloque de consulta diaria oficial. Este registro
no permite determinar la causa de ese bloque fallido.

Al preparar la release se vuelven a comparar las huellas de los tres módulos
de Wunderground dentro del contenedor habitual con el worktree y la evidencia
anterior: coinciden. No se modifica el descargador después de estas pruebas.

## Candidata 0.2.340 preparada

El smoke completo termina con código 0: 2.168 pruebas, 55 omitidas, en
128,922 s para la suite Python; también pasan sintaxis, empaquetado y fixtures.
El primer intento tuvo siete `PermissionError` por puertos locales y el socket
del forkserver bloqueados por el sandbox. La repetición con los permisos
necesarios pasa sin modificar código para resolverlos.

Después del smoke se actualizan únicamente metadatos de versión, referencias
de caché de los dos visores, changelog y este informe. Se comprueba su alineación
en 0.2.340 y `git diff --check`. No se repite la suite por el bump mecánico,
según `docs/release-flow.md`. La imagen local del runner validado conserva los
metadatos 0.2.339; las huellas del descargador coinciden con la candidata.
En ese punto la nueva imagen de release todavía no se había construido ni
publicado. Tras la autorización posterior del usuario, se publica 0.2.340:
[cierre y verificación GHCR](release-ha-0.2.340-2026-10-29.md).
