# Mapa de predicción: SoilGrids compartido y precisión útil

**Anexo de alcance y antecedentes de la [especificación central del mapa](prediction-map-specification-es.md).**
El diseño general se mantiene allí; este documento conserva el alcance de capas
y el dimensionado previo, complementados por el diseño técnico del lector.

Propuesta concretada el 11/09/2026. Posteriormente el usuario autorizó la descarga
nacional: **adquisición terminada y verificada**, según el
[informe de ejecución](../reports/mushroom-prediction-map-soilgrids-acquisition-2026-09-11.json).
538 bloques nuevos y 1.410 archivos reutilizados suman 795.522.040 bytes de
rásteres. Adaptación de lectores y migración **sin ejecutar**. El dimensionado
de abajo conserva el presupuesto previo, no el tamaño comprimido observado.

El [diseño del lector y su validación](mushroom-prediction-map-soilgrids-reader-design-es.md)
concreta ahora la fase pendiente. Sus decisiones propuestas de lectura solo
local, índice, normalización de metadatos y pruebas desarrollan la migración
descrita abajo. Los pasos de adquisición ya terminados no deben repetirse.
El [reparto HA–worker](mushroom-map-compute-data-placement-es.md) establece copias
locales de los mapas en los workers que preparan datos o sirven el nuevo mapa.
La base común no significa un único disco en HA; no se duplica por trabajo.

## Alcance mínimo

El usuario pide evitar datos sin una utilidad concreta y recuerda que la lluvia
es una estimación IDW a partir de estaciones alejadas del punto consultado.
Se reduce la propuesta inicial: **retención de agua existente + pH**.
Textura (arena, limo y arcilla), carbono y materia orgánica quedan fuera de la
adquisición inicial. No se ha demostrado que mejoren este nuevo producto.
Esto no demuestra que sean irrelevantes biológicamente: se reconsiderarán si una
necesidad concreta o una comparación aislada justifica su incorporación.

- Retención: mantener las 54 combinaciones que exige actualmente el Predictor,
  sin cambiar su contrato científico en esta migración.
- pH: propuesta de tres profundidades superficiales, 0–5, 5–15 y 15–30 cm;
  mediana y límites inferior/superior de SoilGrids, nueve combinaciones. Las
  profundidades describen suelo superficial; no implican que cada especie use
  esas tres capas como variables del modelo.
- No descargar pH profundo, medias adicionales ni todas las propiedades
  disponibles «por si acaso». El pH se plantea primero como información de
  compatibilidad ecológica, no como multiplicador automático de probabilidades.

El pH tampoco explica por sí solo la presencia de setas. Las revisiones locales
de [Aereus](literature/prediction/boletus_aereus_revision_bibliografica_rainmapper.md)
y [Lactarius deliciosus](literature/prediction/lactarius_deliciosus_revision_bibliografica_rainmapper.md)
advierten contra convertir asociaciones regionales de suelo en umbrales
universales. Árboles, hábitat y temporada siguen siendo parte del diseño.

## Punto consultado y escala de la predicción

Propuesta de diseño, todavía sin implementar:

1. Consultar altitud, cubierta, árboles y geología del punto según sus mapas de
   origen; conservar escala, fuente y posibles límites entre polígonos.
2. Describir el pH como estimación de la celda de suelo, no como una medición
   tomada exactamente donde se hace clic. SoilGrids tiene una cuadrícula nominal
   de 250 m; interpolar o mostrar más decimales no añade información medida.
3. Reutilizar meteorología por zonas/celdas cuando resulte equivalente, con
   estaciones, distancias y cobertura temporal trazables. El tamaño de estas
   zonas queda pendiente de auditar la red y comparar estimaciones; no se fija
   todavía un tamaño arbitrario ni se confunde una tesela de almacenamiento
   (128 km en esta caché) con una zona de predicción.
4. Dos puntos próximos pueden compartir meteorología y tener distinto hábitat.
   Mostrar esa diferencia es útil, pero no demuestra que sus probabilidades
   puedan distinguirse con precisión a escala de metros.
5. Separar en el informe descripción del terreno, meteorología estimada y
   predicción evaluada. No afinar el porcentaje solo porque la cartografía
   tenga más detalle. Validar la transferencia a lugares nuevos antes de
   presentar los porcentajes como fiables para cualquier punto.

La hipótesis del usuario de que Sporas emplea teselas grandes **no se ha
confirmado** como funcionamiento interno de ese servicio.

## Dimensionado reproducible

[Informe de cálculo](../reports/mushroom-prediction-map-soilgrids-sizing-2026-09-11.json).
Script local: `mushroom-map-GIS/soilgrids-shared/planning/calculate.py`.

Se usan rectángulos conservadores para Península, Baleares, Canarias, Ceuta y
Melilla, con bordes densificados y proyectados a la cuadrícula nativa. Incluyen
mar y países vecinos; no son una máscara territorial ni una prueba de ausencia
de huecos. Unión: 109 teselas, más cuatro antiguas fuera del ámbito, **113**.
Se conservan las 30 teselas existentes, incluidas las que sirven fuera de España.

| Concepto | Resultado |
|---|---:|
| Combinaciones de retención existentes | 54 |
| Combinaciones nuevas de pH propuestas | 9 |
| Total de combinaciones | 63 |
| Máximo de pares tesela/capa | 7.119 |
| Entradas existentes potencialmente reutilizables | 1.355 |
| Máximo pendiente si las anteriores son compatibles | 5.764 |
| Retención + pH, píxeles Int16 sin comprimir | 3.732.406.272 bytes (3,73 GB) |
| De ese total, pH nuevo | 533.200.896 bytes (0,53 GB) |
| Propuesta anterior de 99 combinaciones | 5.865.209.856 bytes (5,87 GB) |
| Archivos antiguos referenciados, originales y normalizados | 394.292.523 bytes |

El recorte de propiedades reduce ese presupuesto bruto un **36,4 %**. No es una
predicción exacta de tráfico ni disco final: faltan cabeceras, índices, máscaras,
vistas reducidas, originales, staging y copia de rollback. Como presupuesto de
trabajo se propone reservar **12 GiB**, no ocuparlos necesariamente. No hay una
duración nacional medida. Las 63 combinaciones aparecen en los metadatos WCS;
la disponibilidad de un identificador no garantiza datos en cada píxel.

Se descargaron tres muestras pequeñas de una tesela (pH, arena y carbono) antes
de reducir el alcance, no sus capas nacionales. La cabecera del piloto pH no
declara CRS ni NoData: debe normalizarse y validarse contra los metadatos de la
fuente antes de usarse. No se considera un ráster operativo validado.

## Lo que dispara actualmente las consultas SoilGrids

Fuentes de código leídas el 11/09/2026:

- `rainmapper_core/mushroom_soilgrids.py`: `required_coverage_ids` y
  `validate_manifest` exigen las 54 combinaciones de retención. Añadir pH
  directamente a ese manifiesto no es compatible.
- `rainmapper-app/app/web_server.py:11541`: `refresh_micro_area_soilgrids_context`
  reutiliza un contexto vigente si no cambia la geometría. Por defecto permite
  obtener las teselas que falten.
- Llamadas al guardar microáreas en `web_server.py:23429`, al modificar geometría
  desde perfiles en `:24028` y al crear microáreas desde ese flujo en `:24116`.
  La rama de guardar un área (`:23381`) no llama directamente a ese refresco.
- `mushroom_soilgrids.py:1150`: `resolve_geometry_context` intenta usar la caché
  y, si falta y está permitido, materializa las teselas. El runtime de predicción
  consume el contexto preparado; no descarga SoilGrids en cada predicción.
- `scripts/manage-soilgrids-cache.py`: también existe materialización explícita.

Cambiar solo la ruta de la caché no adapta el manifiesto, los montajes ni los
contextos de microárea ya persistidos.

## Migración controlada propuesta

1. Congelar el inventario y edición actuales; comprobar integridad de los
   archivos reutilizables y conservar sus valores. Comparar metadatos de nuevas
   descargas: `latest` no significa una edición inmutable.
2. Preparar la base común en una ubicación separada y descargar solo lo que
   falte (adquisición ya terminada). Un único conjunto físico por máquina
   ejecutora, con una vista compatible de retención para
   el Predictor y catálogo de pH para el Mapa. No enviar la base nacional como
   parte de cada trabajo ni incorporarla completa a la imagen HA.
3. Validar cuadrícula, CRS, unidades, máscaras, cuantiles, integridad y consultas.
   Comparar valores/contextos del catálogo viejo y del nuevo en las microáreas
   existentes. La migración no debe cambiar resultados con entradas idénticas.
4. Adaptar de forma conjunta lectores y todos los flujos de creación/edición de
   microáreas. Probar geometría nueva, geometría modificada, edición sin cambio
   geométrico y lugar fuera de cobertura. Según el diseño nuevo, este último
   explicará que faltan datos; una ampliación de la misma base queda como
   mantenimiento explícito por una necesidad nueva, sin volver a otra caché.
5. Validar en local y cambiar referencias/montajes deliberadamente. Tratar los
   contextos persistidos: no invalidarlos ni recalcularlos masivamente por un
   simple cambio de ubicación. Verificar ambas herramientas antes de retirar
   la referencia antigua.
6. Solo después, retirar la estructura antigua del uso normal y mantenerla
   como backup temporal. **Propuesta de plazo: al menos 30 días**, más un ciclo
   local satisfactorio y prueba de creación/edición de microárea. Registrar fecha
   y condición de retirada; el plazo no autoriza un borrado automático.
7. Rollback preparado de lector, rutas y contextos compatibles. No restaurar un
   fichero completo antiguo de observaciones/microáreas que borre las nuevas
   ediciones del usuario. Retirar definitivamente el backup solo tras revisar
   que ya no se necesita.

Esta fase no ha cambiado datos operativos, lectores, montajes ni modelos.

## Fuentes de datos y condiciones

- [Propiedades, profundidades, unidades e incertidumbre de SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).
- [Acceso WCS/WebDAV y licencia](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html).
- Metadatos y muestras guardados junto a su [README local](../../mushroom-map-GIS/soilgrids-shared/planning/README.md).
