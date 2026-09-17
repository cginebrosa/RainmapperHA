# Etiqueta de suelo ausente en Tordera

Consulta puntual autorizada por el usuario el 17/09/2026; no reabre la revisión
GIS general aplazada. Punto de la captura: **41.72905, 2.74775**, HA local.

El lector instalado devuelve la unidad `geology_50000 / Codi=Qt1`, edición
2024-12, feature 8649: «Graves, sorres i lutites. Terrassa fluvial 1».
La capa está disponible. Su regla efectiva está en
`/share/rainmapper/mushroom-data/mushroom_gis_mappings.json`:

- `mapped_lithology_ids`: `lith_fine_clastic`, `lith_unconsolidated_sediment`.
- `mapped_soil_tendency_ids`: lista vacía.
- `review_status`: `accepted`, conservado para la litología.
- Nota: «Clasificación de suelo pendiente: falta evidencia suficiente».
- Referencia: `gis-mapping-reviews/unresolved-substrates-2026-09-16.json`.

La ficha de Qt1 en esa auditoría tiene `outcome=soil_unresolved`. Su justificación
indica que la descripción identifica granulometría y transporte, pero no
composición mineralógica de clastos/matriz. Requiere evidencia de procedencia o
análisis local; no asigna suelo arenoso ni componentes silíceo/calcáreo por defecto.
Esto es la justificación previamente registrada, no una nueva revisión científica.

El código `EcologyReader` añade a `mapped_context.soil_tendencies` únicamente
las tendencias declaradas en el mapping; la lista resulta vacía. Por eso la
cabecera del mapa muestra árboles y bosque de ribera, sin etiqueta de suelo.
Que `mapping_states.geology=accepted` no significa que la composición del suelo
esté resuelta: existe un mapping aceptado para las litologías.

No se cambió ningún mapping ni dato GIS. Evidencia directa del lector instalado:
`tmp/tordera-soil-20260917/geography.json` y `mapping.json`, con ruta y SHA del
archivo efectivo. La lectura local concuerda con la auditoría en
`docker-data/mushroom-data/gis-mapping-reviews/unresolved-substrates-2026-09-16.json`
(entrada Qt1, línea 8131 en esta revisión).
