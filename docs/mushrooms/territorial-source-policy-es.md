# Resolución común de fuentes territoriales

Publicado en HA 0.2.330 e instalado en HA real; metadatos activados el 28/09/2026.
El usuario confirma entrenamiento y precálculo reales terminados al cierre.
La activación de metadatos por sí sola no modifica
observaciones guardadas, evidencia de campo ni modelos ya entrenados.

## Política por campo

`mushroom_territorial_context.resolve_context` recibe exclusivamente IDs de
mapeos aceptados. No clasifica por palabras del nombre del bosque.

| Campo | Prioridad | Alternativa |
|---|---|---|
| Árboles | MFE25 con IDs del catálogo vigente | MVC50, LLFISCAT_t |
| Bosque | MVC50, LLVA_niv2t y mapeos aceptados | Cobertes 2024 |
| Sustrato | MVC50, LLVA_Subst | Geología 1:50.000 |
| Litología | Geología 1:50.000 | Ninguna |

La existencia del polígono no basta: un campo vacío, sin correspondencia aceptada
o fuera de cobertura permite pasar a la siguiente fuente. No se deduce una
composición silícea/calcárea de una descripción genérica de sedimentos. Una
unidad geológica mixta no contradice por sí sola un sustrato más específico.
Valores explícitos silíceo/calizo opuestos se conservan juntos y se registran
como conflicto; llegan a la evaluación ecológica, que ya distingue unidades
mixtas. No se cambia el pH de OpenLandMap/SoilGrids.

Las cubiertas artificiales/acuáticas inequívocas de Cobertes que discrepan de un
bosque se registran como conflicto. No borran automáticamente información
histórica: una capa 2024 no demuestra el estado del terreno en 2016. La política
no fecha cambios ni resuelve automáticamente estas contradicciones.

Mapa, recuperación puntual, muestras de microáreas y reconstrucción usan los
mismos lectores preparados y mapeos. La recuperación conserva el resultado como evidencia ligada a las
coordenadas. Una recuperación ya guardada puede seguir reflejando fuentes/reglas
anteriores hasta una nueva revisión explícita. El rebuild utiliza la evidencia
congelada; no consulta una publicación viva durante un trabajo científico.

## MVC50 preparado

`scripts/prepare-mvc50-point-index.py` lee el original una vez fuera de HA y crea
un SQLite con RTree, geometrías sin simplificar y solo `LLFISCAT_t`,
`LLVA_niv2t`, `LLVA_Subst`. Producto fijado a noviembre de 2019. Las reglas MVC
sin edición existentes se vinculan únicamente a esa edición.

El lector mantiene una caché de 64 puntos y 2 MiB de páginas SQLite; comprueba
longitudes antes de cargar geometrías (64 candidatos, 2 MiB por geometría,
8 MiB por consulta). Límites, geometrías inválidas, bordes y solapamientos
producen un estado explícito, nunca un valor inventado.

La versión preparada comprobada conserva 116.468 entidades. Original necesario
`.shp/.shx/.dbf/.prj`: 884.213.441 bytes; índice: 479.780.864 bytes. La medida
incluye geometrías y RTree, sin degradar resolución. No permite retirar todavía
el original del mantenimiento GIS: el inventario de valores para revisar mapeos
aún tiene consumidores del original. El dataset científico preparado ya lo omite. El mapa/worker no necesita transportar el original
para este lector.

## Instalación geográfica

La imagen nueva admite el rol `mvc50_index` en el manifiesto público sellado.
Publicar solamente código no agrega la capa a una geografía existente.

1. Preparar/verificar el índice en el Mac. Conservar recibo con ruta relativa,
   SHA-256, bytes y mtime lógico; acompañarlo con la procedencia del original.
2. Copiar únicamente el archivo preparado al árbol `media/rainmapper/geography`
   bajo la ruta del recibo. No sustituir originales ni manifest existentes a mano.
3. Con HA/worker compatibles, ejecutar explícitamente
   `scripts/register-mvc50-map-index.py --root <geography> --receipt <receipt.json>
   --generation <nueva-generacion>`. Por defecto verifica SHA; `--verified-copy`
   se reserva para una copia ya verificada fuera de HA, evitando releer el índice
   en la Raspberry. El script registra metadatos y activa el nuevo puntero al final.
4. La sincronización pública del worker incorpora el único archivo nuevo; los
   demás assets conservan sus identidades. No cambia el coordinador del worker.

El registro requiere una publicación portátil existente, rechaza colisiones y
comprueba que los archivos previos no han cambiado. No modifica el manifiesto
científico, sus observaciones ni su configuración privada. Conservar el puntero
anterior permite volver a la geografía previa sin reconstruir archivos.

## Validación local

Datos y logs en `docker-data/territorial-validation/`. Auditoría sobre las 17
observaciones del incidente más 65 puntos interiores repartidos por el original:
82 resultados iguales mapa/recuperación y sin discrepancias de atributos respecto
al original en los puntos que el lector pudo resolver. El índice no elimina los
problemas geométricos del original. Los tiempos medidos son de consulta MVC50,
no de predicción completa ni una comparación de velocidad con el lector antiguo.

Pruebas dirigidas incluyen prioridad independiente por campo, falta de datos,
ediciones distintas, mapeos pendientes, conflicto de sustrato, cubierta urbana,
huecos, bordes, solapamientos, límites antes de materializar y caché acotada.

Validación inicial del 28/09/2026, anterior a completar reconstrucción/microáreas:

- 116 pruebas Python dirigidas y 16 pruebas con GDAL correctas; el adaptador
  de recuperación conserva las otras fuentes si una falla al abrir o consultar.
- Navegador: 77 consultas y 25 históricas, incluyendo terreno unificado y móvil.
- Prueba sin mocks de tres puntos en HA local y en la imagen del worker:
  mismos árboles, bosque y sustrato entre recuperación y predicción.
- Contenedores reconstruidos/recreados; paridad SHA de 14 archivos HA y 10 del
  worker; hashes de las dos configuraciones de coordinador intactos.
- Sincronización geográfica local: 1 archivo descargado, 479.780.864 bytes;
  publicación de 3.511 archivos. Datos privados reutilizados sin transferencias.
- Predicción completa en el worker desde su caché del coordinador local:
  Tordera `41.7291191, 2.747922`, 27/09/2026, todas las especies, siete días.
  Sustrato silíceo, bosque mediterráneo de quercíneas, meteorología disponible.
  Contrato validado; resultado 29.691 bytes; ejecución puntual medida 4,51 s,
  incluyendo arranque de lectores. No es una medición de rendimiento sostenido.

El ciclo operativo local posterior ha terminado y está auditado: 517
observaciones reconstruidas, 792 ajustes sin fallos y precálculo activo. Véase
el informe de preparación 0.2.330.
En HA real se registró `local-mvc50-20260928` y se activó el dataset científico
preparado. Recibos: `ha-register-mvc50.json` y `ha-territorial-activation.json`
en la carpeta de evidencia. No se volvieron a copiar ni hashear assets al activar.
Véase el [informe de release](../reports/release-ha-0.2.330-preparation-2026-09-28.md).

La prueba de 82 puntos comparte lectores reales y comprueba la resolución; sus
llamadas a recuperación están sustituidas para aislar esa política. La prueba de
tres puntos (`endtoend.py`) sí ejecuta la recuperación real y el adaptador del mapa
sin sustituir llamadas. Ambas evidencias están bajo
`docker-data/territorial-validation/`.


## Reconstrucción coherente y transporte mínimo

`prepare-territorial-dataset.py --root <geography>` muestra el plan sin activar;
`--activate` registra, en reposo, sólo metadatos. Se ejecuta después del registro
MVC50 y con imágenes compatibles. La raíz científica pasa a `geography`, con
`territorial-context.json` y `geography-dataset.json`. Mantiene los DEM del
conjunto anterior y referencia MFE25, MVC50, Cobertes y geología ya publicados.
No copia ni recalcula hashes de GIS en la Raspberry. No cambia el contrato de
transporte: la caché existente reutiliza contenido por SHA, también entre mapa
 y reconstrucción. Sólo descarga archivos ausentes.

En el paquete local medido: 14 referencias, configuración 1.997 bytes y listado
2.992 bytes. El worker ya tenía los 13 assets, por lo que únicamente faltaba la
configuración. Las pruebas verifican que un segundo uso transfiere cero bytes.
Un worker vacío sí necesita descargar los assets; no se oculta ese coste.

`TerritorialSession` mantiene un lector y catálogo por reconstrucción y los
cierra al finalizar. No se carga una copia por observación. Los catálogos y
mapeos corresponden al mismo trabajo. Las microáreas aplican la prioridad a cada
muestra antes de agregar IDs; no equivale a un censo completo del polígono.
Las observaciones con recuperación revisada conservan esa evidencia guardada.

Validación posterior: 87 pruebas dirigidas; smoke de 1.854 pruebas (55 omitidas),
paridad de 17 archivos HA/12 worker y prueba sin mocks en ambas imágenes:
Tordera, Riudarenes y Olvan coinciden entre mapa, recuperación y reconstrucción;
una microárea pequeña de Tordera coincide también. Logs `coherent-*` en
`docker-data/territorial-validation/`. Circuito operativo local posterior completado, auditado y aceptado antes de publicar.


## Clasificación ausente con cobertura disponible: Campins

Caso aceptado sin modificación de mapeos el 28/09/2026. En 41.72509, 2.47462,
MVC50 indica `Indiferent` y geología Qv3 no permite determinar sustrato; en
41.72471, 2.47513, el mismo MVC50 coincide con geología POa, mapeada a silíceo.
Las dos consultas reales tienen capas disponibles. No deducir que un campo sin
clasificar sea falta de cobertura ni clasificar Qv3 por los polígonos vecinos.
Fuentes y decisión científica en `docs/decisions.md`, entrada del 28/09.
