# Observaciones: optimización de la interfaz antes de decidir SQLite

El usuario autorizó corregir las lecturas repetidas y el render innecesario,
medir el resultado y decidir más adelante si migrar la base de datos.
Se mantiene JSON y no se modifican observaciones, especies ni setales privados.

## Cambio implementado

- La sección comparte una lectura de setales durante su render. El contexto
  se libera incluso si falla: otra petición vuelve a leer el archivo y puede
  ver los cambios. No hay caché global con datos retenidos entre usuarios.
- El listado conserva los enlaces de edición y pequeños contenedores; cada
  formulario se solicita al abrirlo. Se reutiliza el mismo generador y el POST
  existente, con sus filtros, paginación, multimedia y controles GIS/DEM.
- La petición del editor es de lectura, utiliza el listener de mantenimiento
  y respeta el prefijo ingress. Si falla muestra un error con reintento; puede
  cerrarse durante la carga. Una respuesta tardía no reabre un editor cerrado.
- Cerrar y reabrir conserva el borrador de campos en esa página. Se evita una
  recarga al quitar el ancla. Los adjuntos mantienen el comportamiento previo:
  cerrar el formulario puede vaciar el selector de archivo.
- El encabezado del formulario permite ver el cierre en una pantalla de 390 px.

Código: `rainmapper-app/app/mushroom_profiles_ui.py` (`with_known_sites_snapshot`,
`render_observation_editor_placeholders`, `render_observations_section`) y
`rainmapper-app/app/web_server.py` (`loadObservationEditor`,
`serve_mushroom_observation_detail`, ruta `/api/mushrooms/observation-editor`).

## Medición reproducida

Cinco parejas alternadas, en el mismo proceso del Mac y con los mismos datos:
561 observaciones, 21 perfiles, 75 áreas, 116 microáreas; página de 25 filas.
El código anterior procede de una copia tomada antes del cambio.

| Preparación de la sección | Antes | Después |
| --- | ---: | ---: |
| Mediana del render | 708 ms | 45 ms |
| Lecturas de setales por render | 30 | 1 |
| HTML de la sección | 2.449.879 B | 975.955 B |
| Elementos HTML | 27.866 | 6.366 |
| Editores completos antes de abrir ninguno | 25 | 0 |

El render requiere unas 15,7 veces menos tiempo y produce un 60,2 % menos de
HTML. Una serie anterior dio 655→42 ms. Las huellas de los datos permanecieron
iguales durante las mediciones. Evidencia local en
`tmp/jobs/observation-ui-speed-20261010/`: `baseline.json`, `paired.json`,
`measurements.json`, scripts y logs.

Son tiempos de preparación de la sección, con caché del sistema operativo
caliente. No son latencias HTTP completas ni mediciones de una Raspberry Pi 4.
El primer clic en Editar añade una petición pequeña. El detalle al seleccionar
una fila, la validación general de la página y los mapas/visores precargados
siguen siendo recorridos distintos: no atribuirles esta misma aceleración.

## Validación y activación

31 pruebas dirigidas distintas correctas: 27 de observaciones/navegación ya
existentes y cuatro nuevas sobre aislamiento del contexto, actualización entre
peticiones, editor con filtros/errores y frontera del listener. Tras ajustar la
ruta ingress se repitieron las cuatro nuevas.

Prueba Chrome aislada correcta: carga diferida, error/reintento, conservación
del borrador, filtros, controles multipart/GIS/mapa, respuesta tardía, móvil,
ancla directa y ruta ingress con/sin barra final. También pasó la prueba
existente GIS/EXIF con datos sintéticos. Los guardados se prueban con fixtures,
no guardando ni modificando observaciones del usuario.

La imagen HA local se reconstruyó y sus tres archivos afectados se contrastaron
por SHA-256 desde un contenedor aislado sin red ni volúmenes. Inicialmente se
esperó el aviso del usuario de que terminó el trabajo del worker.

Tras recibir ese aviso el 10/10 se recrearon HA local y el worker, activando
también los cambios anteriores de Iₖ. Se verificó la paridad del código efectivo
y la conservación exacta de ambos coordinadores y de la configuración.
La prueba Chrome `observation_gis_browser_check.mjs --local-read-only` contra HA
local abrió el editor bajo demanda y recibió su vista previa GIS/DEM; no guardó
observaciones. Evidencia: `tmp/jobs/local-activation-20261010/`.
No se publica release ni se lanzan trabajos operativos. Quedan la prueba de
selección/comparación que lanza el usuario, la mejora percibida en mantenimiento
y la decisión posterior sobre SQLite.

El usuario confirmó después que funciona y autorizó la publicación. La prueba
operativa de selección/comparación también se auditó correctamente antes de
publicar [HA 0.2.334](release-ha-0.2.334-2026-10-10.md). Quedan su instalación
y evaluación en HA real y la decisión posterior sobre SQLite.
