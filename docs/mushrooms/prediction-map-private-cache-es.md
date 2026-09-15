# Datos privados del mapa: HA y caché del worker

Estado 15/09/2026: implementado y validado en HA local y worker existente, con
imágenes reconstruidas y sin montajes privados del Mac. No aplicado a HA real.

## Qué significa preparar antes del clic

HA sigue siendo la autoridad para fichas, catálogos, mappings y modelos instalados.
El mapa aprovecha la publicación sellada del Predictor para identificar modelos y
meteorología. No vuelve a construirla ni a leer todos esos archivos para calcular
hashes. Un hilo comprueba unos pocos metadatos de archivos; solo vuelve a leer y
hashear los JSON pequeños que cambian. Mientras nada cambia, no crea snapshots.

En el sondeo online existente, HA anuncia una referencia de 71 caracteres. Cuando
el carril online está libre, el worker puede preparar esa versión antes de que
llegue una consulta. Descarga una vez el manifiesto y pide exclusivamente objetos
que no están en su almacén compartido con el Predictor/precálculo. Dos archivos
con contenido idéntico reutilizan un objeto, aunque tengan nombres diferentes.

Con la versión preparada, el worker anuncia esa referencia como disponible. Al
hacer clic se envían coordenadas, fecha, parámetros y la referencia fijada para
esa consulta. Si sigue residente, no hay transferencia de manifiesto, fichas,
modelos ni meteorología, ni recorrido/hash de esos archivos por la consulta.
Siguen existiendo pequeños mensajes de control y la respuesta con el resultado.

Si cambia una ficha, hay una nueva referencia. Se transporta esa ficha, no los
modelos ni la meteorología que siguen iguales. Durante la preparación puede no
estar disponible el mapa; no se sirve silenciosamente una versión anterior.
Una consulta ya admitida conserva su snapshot. Cambiar la generación de modelos
o meteorología exige que su publicación sellada esté preparada y sea coherente.
No se inicia un runner, entrenamiento o precálculo desde el mapa.

## Recursos, integridad y limpieza

- HA comprueba tamaños/fechas de los archivos de anclaje. Reutiliza hashes ya
  publicados de modelos y meteorología; no hashea esos objetos en este circuito.
- Los modelos del snapshot usan enlaces duros; la meteorología usa referencias
  protegidas por las leases existentes de generaciones. No hay copia completa
  de históricos en RPi4. Los ficheros pequeños se inmovilizan para cada versión.
- Los snapshots anteriores de HA se retienen durante la ventana de consultas
  (120 s más 30 s de margen), hasta un máximo de nueve. Después se liberan.
- El worker conserva versión actual y anterior de cada asociación del mapa.
  Los objetos son compartidos, con enlaces: la limpieza elimina solo los que ya
  no pertenecen a ninguna versión retenida. No toca modelos originales, backups,
  datos de usuario ni el puntero del Predictor.
- Si una sincronización falla después de verificar algunos objetos, esos objetos
  pueden quedar disponibles para reintentar. No se activa la descarga incompleta;
  la siguiente sincronización correcta limpia los objetos ya no referenciados.
- Tras reiniciar, el worker compara metadatos con su recibo local. Si coinciden,
  reutiliza sin hashes completos ni transporte. Si detecta cambios/corrupción,
  verifica y repara los objetos necesarios. Descargas parciales no se activan.
- Límites antes de materializar: manifiesto de 8 MiB, 4096 entradas y 1 MiB por
  archivo pequeño mutable. Objetos descargados se limitan a su tamaño declarado
  y se verifican en el worker. Fallos repetidos espacian reintentos hasta 60 s.
- El transporte usa el token y URL persistidos de cada coordinador. El navegador
  no elige rutas de archivos ni URLs de descarga. HA solo sirve objetos enumerados
  en una referencia vigente, después de autenticar al worker.

## Alcance de esta aceptación

La aceptación inicial de datos privados todavía utilizaba un montaje público.
El incremento geográfico posterior descrito abajo retira también ese montaje.
La aceptación inicial por sí sola no resuelve
la distribución nacional de cartografía ni sustituye la puerta de aceptación
científica requerida antes de una release de HA real.

Código: `mushroom_map_runtime.py`, `mushroom_map_worker.py`,
`mushroom_map_queries.py`, `mushroom_prediction_map_ui.py` y sincronizador existente
`mushroom_predictor_runtime.py`. Pruebas: `test_mushroom_map_runtime.py` y
`test_mushroom_predictor_runtime.py`.

## Siguiente incremento obligatorio: cartografía con HA como autoridad

Nota de cierre 15/09: el diseño histórico de este apartado ya está implementado
y validado localmente; ver la sección final y el informe enlazado.

Decisión del usuario, 15/09/2026: GIS, DEM, OpenLandMap y las demás capas del
mapa también deben residir en `/media` de HA real y tener allí su fuente de verdad.
El worker debe mantener una copia sincronizada; el montaje compartido del Mac no
es el mecanismo de distribución para producción. Diseño implementado después
y validado en la sección final.

Comprobación histórica previa al incremento: HA local montaba `docker-media/rainmapper` en
`/media/rainmapper`. La generación `prediction-map/generations/local-20260914`
se monta además como `/maps` en HA y en el worker. Su manifiesto sellado contiene
3510 archivos, 14.538.214.301 bytes (13,54 GiB), y ocupa 955.309 bytes. Estas cifras
se han leído del manifiesto existente, sin recorrer ni hashear los rasters. No
son un inventario nuevo de la RPi4 ni una confirmación de cobertura ecológica nacional.

La publicación privada actual (`mushroom_map_runtime.PRIVATE_FILES` y
`config_for_runtime`) sincroniza fichas, catálogos, mappings, modelos y meteorología;
las rutas geográficas siguen viniendo de la configuración montada. Que el mapping
GIS esté sincronizado no implica que lo estén sus capas cartográficas.

Diseño que se debe concretar/probar localmente antes de HA real:

1. Catálogo/puntero pequeño de generación geográfica activa bajo
   `/media/rainmapper/prediction-map/`, con referencias a archivos sellados y sus
   hashes ya disponibles. Reutilizar datos existentes de `/media` cuando coincidan;
   preservar originales, backups y lectores del mapa meteorológico.
2. Publicación geográfica independiente de la privada. Una ficha nueva o la
   meteorología diaria no debe republicar ni invalidar gigabytes de cartografía.
   No meter el inventario geográfico completo en cada solicitud ni elevar los
   límites del manifiesto privado para hacer que quepa todo.
3. Reutilizar la mecánica asíncrona del sondeo periódico del worker: HA anuncia
   una referencia de versión pequeña; el worker prepara y después anuncia la
   versión disponible. En el mecanismo privado actual ese anuncio usa el sondeo
   del mapa; no se transportan archivos dentro del heartbeat. Los archivos se
   descargan por peticiones autenticadas separadas solo si faltan o cambiaron.
   Comparar la referencia, no escanear directorios ni rehacer hashes de GIS/DEM/pH
   en cada heartbeat o clic. En el alta/actualización se prepara y verifica el
   manifiesto una sola vez, reutilizando checksums existentes. La RPi4 sirve los
   archivos ya publicados.
4. Worker descarga exclusivamente objetos ausentes o distintos; verifica durante
   la descarga y activa la generación completa de forma atómica. Reutiliza copias
   válidas existentes mediante recibos; no borra datos porque cambie un nombre lógico.
   Transporte autenticado ligado al coordinador persistido, sin URLs arbitrarias.
5. Preparación geográfica fuera del clic, de baja prioridad y acotada, compatible
   con la exclusión de background. No ocupar online con la transferencia inicial
   de gigabytes. Anunciar disponibilidad solo con la generación exigida por HA.
6. Cada consulta fija referencias privada y geográfica coherentes. Retener las
   versiones en uso, acotar anteriores y parciales y limpiar solo objetos sin
   referencias; conservar archivos compartidos con otros consumidores.
7. Aceptación en HA local con worker sin `/maps` compartido: primera sincronización,
   repetición sin transporte/hashes pesados, reinicio, cambio de una sola capa,
   edición de una ficha sin retransmitir GIS, interrupción/reanudación, limpieza,
   generación pendiente y consulta con paridad local/worker. Medir bytes y coste
   de HA. No repetir adquisiciones/auditorías/migraciones ya terminadas.

### Cómo detectará HA una actualización sin releer los GiB

Diseño previsto entonces, implementado después: la publicación
es explícita. El proceso de adquisición/importación/actualización prepara una
nueva generación y su manifiesto sellado, reutiliza los checksums de los archivos
sin cambios y verifica los nuevos una sola vez durante la preparación/recepción.
Al finalizar, sustituye atómicamente un puntero pequeño a esa generación. Se
mantiene intacta la generación activa hasta que la nueva esté completa.

HA conserva la referencia en memoria y solo comprueba el metadato del puntero
pequeño, leyéndolo si cambió. El heartbeat/sondeo anuncia esa referencia, sin leer
el manifiesto grande, sin listar miles de archivos y sin abrir/hash de los rasters.
El worker que ya tenga esa versión no necesita descargar ni verificar de nuevo
sus archivos en cada sondeo. Un cambio de contenido requiere una nueva publicación;
modificar un TIFF activo a mano, sin republicar, no puede detectarse de forma
fiable mediante ese puntero. Por eso los archivos publicados deben ser inmutables
para los consumidores y el flujo de mantenimiento debe publicar sus cambios.

Se reutilizarán el manifiesto y las rutinas del volumen geográfico
`mushroom_map_volume.py` donde sean aplicables; su instalación offline actual no
se invocará por clic. La integración de transporte y activación remota todavía
falta. La distribución de archivos y la cobertura nacional por fuente son
comprobaciones distintas; GEODE y cobertura pendiente siguen en su TODO.

## Evidencia del 15/09/2026

Primera preparación sobre la caché existente: 791 archivos lógicos, 162.500.474
bytes; reutilizados 787, descargados cuatro (475.540 bytes) más un manifiesto
de 269.782 bytes. Sin descargar los objetos meteorológicos/modelos ya presentes.
En HA se hashearon 482.575 bytes pequeños y cero bytes de modelos/meteorología.
La preparación del worker duró 5,42 s, antes de las consultas. Las consultas
posteriores conservaron el mismo registro de sincronización.

Seis consultas reales con usuario básico temporal: paridad exacta local/worker en
La Vansa y Montclar, repetición, concurrencia y cancelación correctas. Tres especies
con cálculo; null y abstención preservados. Primera consulta worker 6,38 s total,
5,38 s de cálculo; repetición 2,87 / 1,86 s. Incluye sondeo y calentamiento de
lectores/modelos: preparar archivos no elimina todo el coste del primer cálculo.
Son medidas en el mismo Mac, no una estimación de rendimiento de RPi4.

El worker solo monta `/var/lib/rainmapper-worker`, `/maps` y `/point-config`.
Ambas imágenes y contenedores cotejados: 193 archivos HA y 101 worker, sin
diferencias. URLs/configuraciones de ambos coordinadores conservan sus hashes.
Usuarios existentes sin cambios; usuario y dispositivo de prueba retirados.

Smoke: 1561 pruebas, 48 omitidas. Después, dos casos adicionales completan
10 pruebas de caché y 14 de rutas; también pasan las 19 del runtime del Predictor.
Los fixtures comprueban edición de una ficha (solo ese archivo), actualización
meteorológica (solo partición y metadatos de generación), reinicio sin hashes ni
descargas, reparación de corrupción, fallo/reintento, versiones acotadas y
preparación en online. No se reinició ni monitorizó el worker/precálculo después
de la instrucción del usuario; el reinicio de caché se prueba con fixtures.

[Informe con métricas e identidades](../reports/prediction-map-private-cache-2026-09-15.json).


## Implementación geográfica validada localmente — 15/09/2026

`mushroom_map_geography_runtime.py` añade una publicación independiente de la
privada. `manage-prediction-map-volume.py publish --publication-root RUTA
--generation NOMBRE` comprueba los metadatos del volumen sellado y publica
`CURRENT.json` atómicamente. Reutiliza los SHA-256 del manifiesto; no relee los
rásteres. HA vigila solamente ese indicador y carga el manifiesto cuando cambia.
Modificar archivos de una generación publicada sin publicar otra no está permitido.

El sondeo del mapa anuncia ambas referencias, también cuando online está ocupado.
El worker prepara cartografía en el mismo carril background que los trabajos
científicos, cediendo el carril entre bloques de hasta 8 MiB. Online sigue reservado
para consultas. La disponibilidad del mapa exige ambas versiones preparadas.
Nunca se inicia una descarga geográfica desde el clic.

HA conserva la fuente en `/media/rainmapper/prediction-map/generations/`.
El worker mantiene objetos públicos en `/var/lib/rainmapper-worker/map-geography/`
y vistas por coordinador en `coordinators/<id>/versions/`. No están en la imagen.
Las descargas son autenticadas, acotadas y reanudables; solo se activa la versión
completa y verificada. Los índices actuales necesitan mtimes exactos, por eso la
clave de objeto incluye contenido y mtime. Fichas/meteorología conservan su caché
privada independiente. La limpieza afecta solo a esta caché pública del worker,
respetando vistas activas y consultas recientes; nunca borra la fuente en HA.

Paquete local publicado: 3510 archivos, 14538214301 bytes. Huella del manifiesto:
`sha256:8ab40e26cddf9567b878611f11c39d079579eb455105839a40ac67610e3f1336`.
Los overlays locales ya no montan `/maps`. Transferencia real completada y
reinicio con cero bytes transferidos/rehasheados. Seis consultas con paridad exacta,
circuito operativo completo, precálculo activo y smoke 1581/48 correctos.
[Informe final](../reports/prediction-map-geography-2026-09-15.json).
No se ha publicado ni instalado nada en HA real.

El registro de modelos conserva su contenido original para transporte. Al
compararlo con la publicación sellada solo se ignoran la preferencia global y
las notas de auditoría de instalación (aprobador/generación anterior). La identidad
de las generaciones instaladas y los contratos de artefactos siguen siendo
obligatorios: una generación distinta bloquea la publicación hasta que sea coherente.
Esto evita que la promoción deje el mapa sin servicio por notas históricas.
