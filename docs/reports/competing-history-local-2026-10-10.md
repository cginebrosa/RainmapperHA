# Comparación histórica por fecha · 10/10/2026

## Cambio

El usuario autoriza guardar acumulados para ver el Iₖ de comparación en modo
histórico. `mushroom_competing_comparison.py` suma los resultados del mismo
replay; `mushroom_competing_parallel.py` fusiona diferencias por fecha. No hay
replay por fecha consultada ni un trabajo nuevo desde el mapa.

`mushroom_map_competing.py` busca el acumulado estrictamente anterior a la fecha
de emisión y devuelve sólo las cinco notas. Datos anteriores sin acumulados
mantienen compatibilidad y muestran un mensaje específico, no «K pendiente».
Se mantiene la selección habitual principal y el verde para máximos empatados
de la comparación común, sujeto a su soporte actual.

Se conserva la identidad del productor de variables
`f2031581c6ef56c751fe002d6c614a5c3ea237194a7964fe1c33f9a00a3b05f2`.
La revisión previa `b2e5c0f4bda4c687bc0b5e68a211d869ab2ec732d849b3ad8d309fc720bae581`
se admite para reutilizar unidades de validación únicamente con huellas exactas
de sus entradas. No se han modificado ajustes, inferencia ni reglas de selección.

## Pruebas y medida acotada

- 69 pruebas dirigidas correctas: comparación, particiones, columnas compactas,
  reutilización, runner, backend, entradas, empaquetado y mapa.
- Los prefijos coinciden con una evaluación limitada a cada fecha; se prueban
  exclusiones técnicas, abstención, días repetidos, ausencia de soporte y datos
  corruptos. La consulta no llama al replay ni transporta la serie completa.
- Medida de **contadores sintéticos**, 5.000 visitas en dos especies: código
  previo 0,1153 s; nuevo 0,1283 s; diferencia 0,0129 s. Notas finales exactas.
  Validación del nuevo histórico: 0,0327 s; consulta media 0,0068 ms.
- Histórico adicional: 473.852 bytes/K; respuesta del punto: 1.154 bytes.
  Estas cifras no miden entrenamiento, preparación, inferencia ni un trabajo
  operativo completo. No se repitió el benchmark cerrado de 5.000 visitas.

Evidencia privada de esta tarea: `tmp/jobs/competing-history-20261010/`.
La prueba de navegador terminó correctamente. Las imágenes se construyeron,
pero el usuario pidió no recrear los servicios hasta avisar de que terminó el
trabajo del worker para HA real. No se ha aplicado aún este cambio ni lanzado
el trabajo operativo de selección/comparación.

## Corrección de reutilización tras revisión

La revisión encontró que admitir `b2e5c0…` como productor antiguo buscaba sus
unidades con claves JSON, aunque ya utilizaba huellas binarias y contexto de
ventanas de entrada. Una reproducción en memoria reutilizó 3/3 al repetir el
productor y 0/3 al migrar, con entradas idénticas.

Corregido el 10/10: productores binarios revisados separados del formato antiguo;
comprobación exacta con las huellas correspondientes y alias a la unidad
original. La comparación puede leer los ajustes asociados a esas unidades sólo
si su productor está explícitamente admitido y coinciden Python y las versiones
de las bibliotecas numéricas. Se conservan claves, modelos y resultados; no se
duplican los ajustes ni se amplían los presupuestos.

97 pruebas distintas correctas entre las suites dirigidas. Incluyen migración
del ejecutor completo: **3 unidades reutilizadas, 0 calculadas**, evidencia
numérica idéntica; cambios de entradas/etiquetas/contexto invalidan la unidad,
los productores no revisados se rechazan y los alias sobreviven a la reapertura.
Una prueba de procesos fue bloqueada por el sandbox; los 24 casos de esa suite
pasaron al repetirla con permiso para su socket local.

La identidad del productor de variables sigue siendo `f2031581…`; revisión del
procedimiento corregido: `02c86d9fa9133c91f8424effeced1e4d3bb1d9f2e20bfe16bfbf02f3e347be0d`.
Imágenes HA local y worker reconstruidas desde esta corrección, **sin recrear
contenedores ni activar el código nuevo**. Paridad efectiva y prueba operativa
pendientes del aviso del usuario. No se ha reiniciado el worker, cambiado sus
coordinadores, publicado release ni ejecutado trabajos operativos.

Evidencia de la corrección: `tmp/jobs/competing-cache-fix-20261010/`.

## Activación local posterior al aviso del usuario

El 10/10 el usuario avisó de que el worker había terminado. Se comprobaron sus
dos colas libres y se recrearon HA local y worker. Doce archivos efectivos de HA
y ocho del worker coinciden por SHA-256 con el worktree. Los dos archivos de
coordinadores conservan sus hashes y URLs; la configuración efectiva coincide
con la anterior. Worker sano y libre después del arranque.

Se activó conjuntamente la optimización de la UI de observaciones. Su prueba
de navegador contra HA local pasó sin guardar cambios. El usuario lanza ahora
Selección y comparación: no se ha generado aún el nuevo artefacto operativo ni
verificado el resultado histórico con ese trabajo. Sin release ni actualización
de HA real. Evidencia: `tmp/jobs/local-activation-20261010/`.

## Aceptación posterior y release

El usuario confirmó el funcionamiento y solicitó publicar. Se auditó el trabajo
local posterior `worker_job_WW5hw8Pr9iGqKNiM`: completo, 53,926 s, artefacto
activado con recibo coincidente y acumulados históricos válidos en ambas
especies. Release [HA 0.2.334](release-ha-0.2.334-2026-10-10.md) publicada;
instalación y prueba en HA real a cargo del usuario.
