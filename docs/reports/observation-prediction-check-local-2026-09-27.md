# Comprobar predicción desde observaciones — validación local

27/09/2026. Aceptado por el usuario y publicado en HA 0.2.329.
Instalación real pendiente; véase [release](release-ha-0.2.329-2026-09-27.md).

Botón bajo Cómo llegar en el visor de observaciones. Se envían coordenadas,
ID estable de especie y fecha de la observación mediante el contrato existente
`prediction_map_point_v1`, siete días e histórico visual de 60 días. El motor
conserva las ventanas que necesita cada modelo. Se reutiliza la ficha completa:
IFF/modelo, explicación, meteorología, SMI y terreno. Añade abundancia registrada
y vuelta a la observación. La nota inicial fue retirada en la simplificación final.

La fecha del mapa no cambia. No se activa el clic predictivo si estaba apagado.
El acceso a observaciones no concede permiso de predicción. Cargas diferidas
respetan cambios de sesión/cierre de ficha. Cancelación y errores conservan el
retorno a la observación. El API de detalle añade sólo `species_id`.

## Comprobaciones ejecutadas

- `python -m unittest tests.test_mushroom_map_observations tests.test_mushroom_prediction_map`:
  34 pruebas correctas.
- `python -m unittest tests.test_mushroom_map_model_runtime tests.test_mushroom_map_prediction`:
  27 pruebas correctas; motor no modificado.
- `node tests/prediction_map_browser_check.mjs` con MapLibre local: correcto.
  Comprueba fecha/coordenadas/especie/horizonte, IFF y modelo, meteorología/SMI,
  ausencia de carga de estaciones históricas, fecha global conservada, retorno,
  cancelación sin reapertura tardía, error de consulta y ocultación sin permiso.
  También conserva la batería anterior del mapa y móvil.
  Log: `docker-data/observation-prediction-browser.log`.
- Captura `observation-prediction-check.png` inspeccionada visualmente en
  `prediction-map-browser-DaOXZX` del directorio temporal de navegador.
- HA local reconstruida y recreada con Compose, sin reconstruir worker.
  SHA-256 idéntico para los siete archivos funcionales cambiados (API de
  observaciones, tres JS, dos CSS y etiquetas); JS servido por HTTP 200.
- Consulta HTTP real en HA local con sesión temporal eliminada al terminar:
  observación del 01/08/2025, Amanita caesarea. Resultado en 2,02 segundos,
  siete días, modelo Sparse Group–V5w, meteorología disponible con corte
  31/07/2025 e histórico `estimated_water_balance`. Respuesta de 35.681 bytes
  al serializarla para la comprobación. Esto verifica integración, no exactitud
  científica del IFF ni paridad con los modelos instalados en HA real.

No se modifican observaciones ni se lanzan entrenamiento, precálculo o runner.
HA real no se modifica. Los JSON privados del worktree quedan fuera del cambio.

## Ampliación: trazabilidad de entrenamiento y ficha

Comprobado posteriormente el 27/09/2026, todavía sin publicar HA:

- `mushroom_training_observations.py` escribe `training-observations.sqlite`
  en staging del lote final. Asocia artefacto exacto con conjunto de IDs de las
  filas elegibles ya filtradas del ajuste. Reutiliza el conjunto por matriz;
  una observación en varios horizontes no duplica su pertenencia. No incluye
  vectores de variables ni copia el contenido de las observaciones.
- Índice con claves primarias, conexión de lectura inmutable y caché SQLite
  acotada a 256 KiB. Presupuesto de producción: dos millones de filas de entrada
  acumuladas por conjuntos y 128 MiB de archivo; rechazo antes de insertar el
  conjunto que exceda cardinalidad y límite de páginas durante escritura.
- Referencia de tamaño/digest en manifiesto, transferencia e instalación
  verificadas; incluido también en el runtime enviado al worker. Modelos antiguos
  siguen siendo válidos. Fuente incompleta o fichero ausente no equivale a «No».
- Cada consulta devuelve siete estados como máximo para la especie solicitada,
  sin listas de IDs. Resuelve el artefacto compartido `all_species` cuando procede.
  Permisos de observaciones comprobados en envío y recogida del resultado.
- 101 pruebas dirigidas correctas en `docker-data/training-trace-tests.log`:
  índice, entrenador, catálogo, recepción/instalación, runtime, contrato HTTP,
  broker y empaquetado de runtime. Incluye ausencia, duplicados, conjunto
  compartido, entrada incompleta y plan SQL `SEARCH ... USING PRIMARY KEY`.
- Medición sintética local, 100.000 IDs / diez estimadores con la misma matriz:
  2.183.168 bytes, escritura 0,167 s; 200 consultas, mediana 0,133 ms y máximo
  0,524 ms. Resultado: cien IDs presentes y cien ausentes. Archivo temporal bajo
  docker-data eliminado al terminar. Son medidas del Mac, no de HA real.
- Worker reconstruido/recreado con el módulo incluido explícitamente en su
  Dockerfile. Dos pruebas de ajuste mínimo ejecutadas dentro del contenedor
  correcto: entrenamiento con IDs y reutilización de matriz, 0,062 s. No se
  entrenan ni promocionan modelos operativos. Coordinadores antes/después:
  `http://100.111.77.48:8100` y `http://rainmapper-ha-ui:8100`, sin cambios.
- SHA-256 del código efectivo: nueve ficheros de worker y diecisiete de HA
  coincidentes con worktree antes de la posterior adición de altitud (requiere
  nueva paridad de HA, no reconstrucción del worker).
- Consulta HTTP local del mismo caso anterior con `observation_id`:
  1,01 s, 35.783 bytes; probabilidades idénticas y siete estados `legacy`.
  Sesión de comprobación eliminada en finally. No se escanean observaciones
  para deducir su uso ni se retrorellena un índice de modelos antiguos.
- Navegador: estados Sí/No/antiguo/no verificable al cambiar de día; consulta
  exacta con ID, misma meteorología/SMI y retorno. Punta blanca visible, separación
  del marcador; captura `observation-compact-footer.png` inspeccionada.
  Resultado en `docker-data/training-trace-browser.log`.

Adición solicitada después: altitud guardada bajo Fecha y antes de Área,
aprovechando las tres filas junto a la luna. Sin consulta DEM adicional.
37 pruebas dirigidas de API/observaciones correctas y navegador completo correcto
(77 consultas, 25 de histórico; carpeta `prediction-map-browser-zhN5OZ`). Captura
de ficha con altitud y bocadillo inspeccionada. Imagen HA reconstruida y recreada
por indicación del usuario a las 18:48 UTC, sin reiniciar el worker. Los 17
archivos efectivos de HA coinciden por SHA-256 con el worktree, incluida la
adición de altitud. HTTP local devuelve 200. El entrenamiento del usuario sigue
registrado en ejecución tras la recreación.

Simplificación posterior solicitada: se retira la explicación de reconstrucción
y los párrafos de trazabilidad del panel. Se conserva especie, fecha, abundancia,
retorno y «Usada para entrenar: SÍ» verde / «NO» rojo. Los estados desconocidos
no se convierten en NO: aparecen como SIN DATOS o SIN MODELO. Navegador completo
correcto (77 consultas y 25 de histórico), captura inspeccionada en
`prediction-map-browser-btAkeK/observation-prediction-check.png`.

## Cierre de release

Entrenamiento local del usuario completado y resultado verificado:
`operational_20260927T184246Z`, 792/792 ajustes y cinco versiones instaladas.
Índice presente con 573.440 bytes y 792 modelos; SHA/tamaño declarados coinciden,
los 226 conjuntos están completos y `PRAGMA quick_check` devuelve `ok`.
No se repite entrenamiento ni precálculo para publicar. El método de entrenamiento
se conserva por decisión del usuario; no se implementó el interruptor discutido.

Smoke completo correcto: 1.838 pruebas, 52 omitidas, 86,989 s. Primer intento
limitado por el sandbox al abrir sockets localhost; repetido fuera del sandbox
sin cambios de código. Tras el bump mecánico, HA local reconstruida/recreada:
etiqueta 0.2.329, HTTP 200 y SHA idéntico de 19 archivos HA y nueve worker.
Detalles y huellas remotas en el informe de release.
