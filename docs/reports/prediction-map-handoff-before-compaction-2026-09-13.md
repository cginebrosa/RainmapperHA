# Relevo del Mapa de predicción — 13/09/2026

Solicitado por el usuario antes de compactar. Este relevo resume ejecución y
continuación; la autoridad de diseño sigue siendo la
[especificación central](../mushrooms/prediction-map-specification-es.md).
Sustituye como punto de continuación al relevo del 12/09 y a los «siguientes
pasos» históricos. No reiniciar el trabajo desde descargas o revisión bibliográfica.

## Situación al dejar el relevo

**La vista previa muestra terreno y meteorología reales y candidatas ecológicas,
pero todavía no calcula probabilidades reales de fructificación.** El último
incremento conecta el filtro de hospedadores, meses y altitud a la lista del popup.
Con filtro conectado desaparecen las curvas de ejemplo y aparece «Predicción
pendiente». Sin hospedadores identificados en el punto, la lista queda vacía.

Revalidado al preparar este documento:

- `http://127.0.0.1:65517/protected/prediction-map/index.html`: HTTP 200 mediante
  GET; no se ha ejecutado otra consulta predictiva para documentar.
- Proceso de preview: PID **84535**, `node tests/prediction_map_browser_check.mjs`,
  argumentos transcritos más abajo. Es un identificador temporal: revalidar antes
  de cualquier operación. Sesión de herramienta anterior 92305, no depender de ella.
- `docker ps`: `rainmapper-local-rainmapper-ha-ui-1`, imagen
  `rainmapperha:local-ha-ui`, publicado solo en `127.0.0.1:8101`;
  `rainmapper-worker`, imagen `rainmapper-worker:1.1.1`, healthy, puerto local 8110.
  Esto acredita procesos/etiquetas, no paridad de código ni estado de trabajos.
- Los tres JSON locales del filtro conservan exactamente las huellas del
  [informe de compatibilidad](prediction-map-ecology-2026-09-13.json): perfiles
  177.432 bytes, catálogo 101.239, mappings 27.883; total 306.554 bytes.
- `git status --short`: muchos cambios y archivos nuevos sin seguimiento.
  **No hay que limpiar ni restaurar ese trabajo.** El cambio en
  `mushroom-data/mushroom_observations.json` es previo y pertenece al usuario;
  no incluirlo ciegamente en un commit ni sustituirlo.

HA real: el usuario confirmó `0.2.303` instalado y funcionando. No se ha
inspeccionado ni actualizado HA real en esta entrega. El filtro último está
activado únicamente en la preview; no se han reconstruido HA/worker para él.

## Decisiones vigentes que no deben reabrirse por pérdida de contexto

- Prioridad: completar entradas/compatibilidad → predicción real primero en
  servidor local/HA → comparar ese mismo cálculo con worker. «Local» significa
  servidor, no navegador. Reutilizar el motor Python existente; no duplicarlo.
- Un punto tiene entradas propias, incluso dentro de un área conocida. Misma
  política de selección semanal que el Predictor; no copiar el porcentaje del
  área ni exigir igualdad si las entradas del punto son diferentes.
- Horizonte máximo inicial de siete días. Una selección semanal coherente,
  con reglas de fiabilidad, corte y fallback del Predictor, no escoger un modelo
  distinto libremente para cada día. Hay adaptador preparado, aún sin integrar.
- Visor nuevo/ruta nueva, núcleo MapLibre reutilizado; mantener comportamiento
  del mapa meteorológico. Botón de diana con dardo bajo IDW; clic y hover sobre
  estaciones siguen siendo meteorológicos incluso en modo predicción.
- Modal «Calculando predicción» al consultar, cancelable; resultado en popup
  anclado al punto, no panel lateral. Municipio/coordenadas, altitud y pH en
  cabecera; arbolado en fila completa. Terreno/geología en desplegable.
- Meteorología observada visible hasta 60 días; el motor puede usar más.
  Sin previsión meteorológica en UI por ahora. Viento opcional de una estación
  identificada, no viento interpolado. Lluvia/temperatura/humedad usan su lector
  observado IDW. No confundirlo con el IDW de visualización del navegador.
- Preview con usuario ficticio: no añadir autenticación real todavía ni escribir
  ese usuario en `devices.json`. Sus ajustes de prueba están aislados en archivo
  temporal; mantenerlo sencillo y retirable.
- Catálogo/perfiles de trabajo: **los locales en `docker-data/mushroom-data/`**,
  no los del repo. Su promoción al repo y HA real será posterior y explícita.
- Ventanas amplias por ficha: unión de meses y asociaciones utilizables, extremos
  amplios de altitud y pH. No rellenar valores desconocidos con ceros. Orientación
  no es requisito para ninguna especie; revisar más adelante si hace falta.
- Salmonicolor/quieticolor conserva su ficha conjunta. Rovelló agrupará
  observaciones **en datos derivados**, conservando IDs originales y fichas.
  Una curva del grupo, compatible si una ficha completa encaja; no mezclar el
  hospedador de una ficha con la altitud de otra ni sumar probabilidades.
- Huecos de arbolado y SoilGrids aceptados. No descargar o auditar otra vez sin
  motivo nuevo. Vegetación/ecología francesa pendiente, geología francesa aparte;
  no bloquear el desarrollo por ampliar esa cobertura.
- Mapas pesados en volumen persistente portable del worker; no meterlos todos
  en su imagen ni reconstruirlos desde la RPi4. AWS/otro servidor son ideas futuras.

### Última precisión del usuario: hospedadores

| En la ficha | En cartografía | Coincide |
|---|---|---|
| Pino negro | Pino negro | Sí |
| Pino negro | Pinos, género genérico | Sí |
| Pino negro | Pino rojo/silvestre | No |
| Pinos, género genérico | Cualquier especie de ese género | Sí |
| Pino negro o abeto | Encinas | No |

Mismo criterio para todos los géneros. No equiparar hermanos taxonómicos por
compartir padre ni pinos/abetos por compartir familia. Basta una alternativa
positiva de la ficha. Para afinar a pino negro, no mantener también una relación
genérica con pinos si no se quiere admitirla como alternativa.

Si una especie requiere un hospedador y no se identifica uno compatible, no
incluirla. **Sin ningún hospedador identificado en el punto, abstenerse para
toda la lista en esta fase**, aunque el motivo sea un hueco cartográfico. Esto
no significa ausencia física demostrada, incompatibilidad científica ni 0 %.
No reintroducir especies «por si acaso» usando meteorología favorable.

## Trabajo realizado y archivos importantes

### Fichas, revisión bibliográfica y pH

La [revisión de literatura](../mushrooms/prediction-map-species-literature-review-es.md)
conserva la comparación de las 21 fichas y segunda pasada; sus decisiones
posteriores de ventanas amplias prevalecen sobre propuestas antiguas más estrictas.
La tabla §1.1 refleja la aplicación local, con evidencia en
[prediction-map-species-windows-2026-09-13.json](prediction-map-species-windows-2026-09-13.json).

Aplicado previamente: 25 relaciones de plantas y 12 de bosque añadidas, ocho
fichas con meses cambiados, 13 con extremos de altitud cambiados y nueve parejas
de óptimos 0–0 pasadas a desconocidas. Se conservan relaciones originales,
observaciones, IDs, nombres, pesos y orientaciones. Catálogo: 114 entradas de la
ampliación anterior + `host_eucalyptus_spp` = 115.

`ecology.ph_min/ph_max` implementados en JSON, mantenimiento V0/Enriched,
guardado/importación y validación. **Ambos están `null` en las 21 fichas.**
El usuario vio los controles vacíos: no es un fallo del formulario; no se han
inferido números de categorías de suelo ni de óptimos de cultivo.
Archivos: `rainmapper-app/app/mushroom_profiles_ui.py`, `web_server.py`,
`rainmapper_core/mushroom_validation.py`, `scripts/validate-mushroom-data.py`,
`mushroom-data/mushroom_labels.json`; pruebas de mantenimiento/datos correspondientes.

Ese bloque sí se instaló en HA local, según su informe: 26 + 22 pruebas,
42 editores renderizados y HTTP 200, cuatro huellas efectivas comprobadas.
Es evidencia de aquella entrega, no validación del filtro posterior en Docker.
Backups permanentes registrados (no borrarlos ni volver a aplicar la migración):

- `docker-data/mushroom-data/backups/mushroom_reference_catalogs.20260913T110116616635Z.keep.json`
- `docker-data/mushroom-data/backups/mushroom_profiles.20260913T110116616635Z.keep.json`

### Filtro ecológico y preview — último incremento

| Archivo | Función en la entrega |
|---|---|
| `rainmapper_core/mushroom_map_forest.py` | Además de etiquetas, devuelve `host_id` canónico por científico/alias inequívoco; conserva caché geométrica al editar catálogo. |
| `rainmapper_core/mushroom_map_ecology.py` | `EcologyReader`, reglas residentes `broad_species_windows_v1`, jerarquía y evaluación diaria de las fichas. |
| `scripts/prediction-map-local-geography.py` | Añade `--profiles`, `--ecology-catalogs`, `--gis-mappings`; devuelve `ecology` con fechas y estados. |
| `rainmapper_core/mushroom_map_execution.py` | `PointExecutor` transporta esas rutas y fecha/horizonte al mismo lector, preparado para HA/worker. |
| `rainmapper_core/viewers/prediction-map/prediction-mode.js` | Valida `ecology`, presenta solo candidatas del día, sin gráfico simulado; abstención/fallo dejan lista vacía. |
| `mushroom-data/mushroom_labels.json` | Ocho textos nuevos ES/CA/EN para compatibilidad/predicción pendiente. |
| `tests/prediction_map_browser_check.mjs` | Preview con rutas de datos explícitas; casos de UI para candidatas, día, falta de hosts y lector no disponible. |
| `tests/test_mushroom_map_ecology.py` | 14 pruebas de reglas, jerarquía, fechas, altitud, pH, mapping y recarga. |
| `tests/test_mushroom_map_forest.py` | Comprueba también IDs, alias, cambios de catálogo y ausencia de IDs antiguos tras fallo. |

El lector compila solo los tres JSON pequeños, detecta cambios con stat y hace
huellas al recargarlos, no en cada consulta. Una instantánea por semana solicitada;
32 fichas máximo, 2 MiB por archivo y 512 mappings exactos. Sin bibliografía, red,
escaneos de capas ni procesos por especie/capa. Los IDs sin catálogo no acreditan
un hospedador; ediciones inválidas no reutilizan silenciosamente reglas anteriores.

El filtro actual aplica meses principales/secundarios, altitud inclusiva y hosts.
Para no ectomicorrícicas requiere hábitat reconocido mediante mapping exacto.
Suelo/litología solo aportan preferencias coincidentes, no vetos nuevos. pH opcional:
intervalo 0–5 cm contenido admite esa dimensión; disjunto queda fuera;
solapamiento parcial/incompleto es desconocido. Límites vacíos no vetan.
No se usan orientaciones ni se calculan probabilidades.

**Límite técnico importante:** el contrato sigue siendo el prototipo
`prediction_map_point_v1`, `data_mode=simulation`. `QueryBroker.finish()` exige
que `species` conserve los ejemplos exactos. Se añade `ecology`; el visor, si
está presente, ignora esos ejemplos y muestra candidatas reales como pendientes.
No afirmar que el payload entero sea una predicción real. Al conectar el motor
hay que evolucionar contrato, validadores de broker y UI conjuntamente.

### Evidencia del último incremento

[informe de compatibilidad](prediction-map-ecology-2026-09-13.json):
14 pruebas de filtro + 10 forestales GDAL + 6 de broker + 12 de mapa = 42.
Navegador Chrome real: candidatas por fecha, falta de host/fallo sin ejemplos,
móvil, clic/hover de estaciones, permisos y ruta meteorológica conservados.
No repetirlas por este relevo solo documental; repetir lo proporcional si cambia código.

Puntos consultados con lectores reales, fecha 2026-09-13:

- Avià `42.06511, 1.81822`: `host_data_missing`, cero candidatas. También se
  comprobó por POST de la preview; meteorología disponible.
- Olvan `42.06397, 1.93668`: encina, quejigo, roble pubescente; siete candidatas
  según las fichas locales. Pinophilus puede aparecer aquí porque su ficha local
  ampliada incluye `host_quercus_spp`: no confundirlo con equivalencia roble/pino.
- Ger `42.46291, 1.82695`: pino negro y enebro; cuatro candidatas.

Lecturas M1, no motor completo: primera 582 ms, siguientes 33–73 ms, repetida
2,3 ms; respuesta geográfica de 7,6–9,9 kB. No extrapolar estos tiempos a la RPi4
ni presentarlos como comparación de predicción local/worker. Memoria y tiempos
completos del motor se medirán cuando esté integrado.

## Cómo está ejecutándose la preview

Comando observado; **no lanzarlo si ya hay un proceso en ese puerto**. Antes de
reiniciar, inspeccionar el proceso y preservar sus argumentos. No toca workers.

```bash
node tests/prediction_map_browser_check.mjs \
  /private/tmp/rainmapper-maplibre-4.7.1.js \
  /private/tmp/rainmapper-maplibre-4.7.1.css \
  --preview --port 65517 \
  --municipalities mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg \
  --geography-python /opt/homebrew/bin/python3 \
  --municipalities-edition 2026-08-10 \
  --terrain-index mushroom-map-GIS/terrain-index/preview-2026-09-12.sqlite \
  --soil-root mushroom-map-GIS/soilgrids-shared \
  --dem-root mushroom-map-GIS/ign-mdt25 \
  --regional-root mushroom-GIS \
  --weather-data docker-data/Data \
  --weather-stations docker-data/stations.txt \
  --land-cover mushroom-map-GIS/icgc-cobertes-2024/source/cobertes-sol-v1r0-2024.gpkg \
  --geology mushroom-map-GIS/icgc-geologia-50000/source/geologia-territorial-50000-geologic-v3r0-202412.gpkg \
  --land-cover-parts mushroom-map-GIS/icgc-cobertes-2024/prepared/oversized-parts-2026-09-12.gpkg \
  --forest-index mushroom-map-GIS/mfe25/prepared/catalunya-point-index-v2-2026-09-13.sqlite \
  --forest-catalogs docker-data/mushroom-data/mushroom_reference_catalogs.json \
  --profiles docker-data/mushroom-data/mushroom_profiles.json \
  --ecology-catalogs docker-data/mushroom-data/mushroom_reference_catalogs.json \
  --gis-mappings docker-data/mushroom-data/mushroom_gis_mappings.json
```

El Python Homebrew tiene GDAL; `.venv/bin/python` se usa para los demás tests y
para el lector meteorológico de esta preview. No instalar dependencias de nuevo
por no tener GDAL en `.venv`. Librerías MapLibre/ajustes están en temporales:
si desaparecen, comprobar rutas antes de diagnosticar fallo de la aplicación.

## Pendientes en el orden de continuación

1. **Completar traducciones revisadas de hábitat/suelo/litología de los productos
   nuevos**, sobre los mappings locales. Hay cinco mappings exactos previos;
   no coinciden en fuente/edición con `icgc_cobertes_2024` (`2024`) y
   `icgc_geologia_50000` (`2024-12`). No aplicar un código de MVC50 por igualdad
   textual a otra capa. Preparar correspondencias con leyendas ya locales,
   validar IDs y guardar con backup/procedencia. No deducir hosts concretos de
   cubiertas genéricas ni dar por resuelto hábitat mientras falta el mapping.
2. **Agrupación derivada Rovelló**: deliciosus, sanguifluus, vinosus y
   salmonicolor/quieticolor unidos como objetivo predictivo manteniendo sus
   observaciones originales. Versionar miembros/identidad y asegurar una curva.
   Preparar código/contrato/pruebas; no lanzar entrenamiento automáticamente.
3. **Conectar el motor real compartido**, construyendo entradas propias del punto
   y conservando selección semanal del Predictor. `mushroom_map_prediction.py`
   ya contiene `resolve_species_week`; revisar sus pruebas y §9 de la
   especificación antes de crear algo paralelo. Conectar ecología/elegibilidad,
   entradas hídricas y meteorológicas, artefactos aplicables y abstenciones.
   Cambiar juntos contrato, broker, ejecutor y UI para eliminar los ejemplos.
   No etiquetar score sin calibración como probabilidad garantizada.
4. **Validar primero el cálculo local completo**: mismos inputs/artefactos/política
   deben dar mismo resultado que el Predictor; con terreno propio puede diferir
   del porcentaje del área. Verificar fechas/semana, gaps y casos excluidos.
5. **Después comparar HA/local y worker** con el mismo cálculo y versiones:
   identidad de datos/modelos, transporte, colas, latencia fría/caliente, RAM,
   disco y carga. No comparar solo las lecturas geográficas como sustituto.
6. **Posteriormente integrar/desplegar** autenticación y preferencias reales,
   distribución portable de datos y promoción de catálogo/perfiles locales.
   Hacer paridad local aplicable de HA y worker antes de HA real; no considerar
   esta preview aislada una validación de release. No publicar ni instalar sin
   autorización expresa y flujo de release.

Siguen aplazados: vegetación/ecología y geología de Francia, ampliación de cobertura
forestal, cifras pH ausentes cuando no hay fuente utilizable, revisión futura de
ventanas/orientaciones, lector hídrico SoilGrids/agregación por áreas y microáreas,
migración de caché antigua y etiquetas forestales en el idioma seleccionado.
No son motivo para repetir descargas ni bloquear toda la implementación del visor.

Aspectos a comprobar al ampliar el filtro (no presentarlos como resueltos):
catálogos coherentes entre lector forestal y ecológico al editar durante una
consulta; clasificación de fallos de datos; coincidencias de hábitat para no
ectomicorrícicas; validación del nuevo payload en broker cuando deje el modo demo.

## Restricciones operativas y forma de trabajar

No borrar cachés, backups, datos, observaciones o URLs de coordinador. No lanzar
jobs de meteorología, reconstrucción, entrenamiento o precálculo, ni publicar HA.
No cambiar destino de un worker al reconstruirlo: conservar URL exacta y comprobarla.
No tocar el mapa meteorológico actual ni su autenticación como atajo.

Avisar brevemente del avance al menos cada minuto; responder a preguntas del
usuario y seguir la tarea, sin interpretar la pregunta como cancelación.
Preferir consultas pequeñas y artefactos existentes; HA real es una RPi4 compartida.
MCP Codebase primero, pero su índice actual no contiene los módulos nuevos del
mapa: tras resultado insuficiente se permite lectura directa. No reindexar ni
repetir auditorías por este motivo. No delegar a subagentes sin instrucción explícita.

En esta actualización de relevo solo se documenta; no se han reiniciado procesos,
reconstruido imágenes, modificado datos ni repetido pruebas de ejecución.
