# Cómo retomar la revisión de suelos GIS

Revisión aplazada por el usuario el 16/09/2026. De la tanda de 488 códigos:
**145 aceptados, 12 pendientes con investigación específica y una limitación
documentada, y 331 sin investigación específica suficiente**. Los 12 no se
consideran irresolubles ni tienen necesariamente toda la bibliografía agotada.
Las otras 567 clasificaciones anteriores quedan fuera de esta tanda.

## Método

1. Identificar el `Codi`, la descripción y los polígonos reales del ICGC
   `geology_50000`, edición 2024-12. Mantener identificadores, edición y
   mayúsculas; no renombrar fuentes ni confundir unidades próximas.
2. Agrupar la investigación por formación, facies y ámbito geográfico. Consultar
   primero cartografía/memorias ICGC e IGME MAGNA y después estudios petrográficos
   específicos. Reutilizar un documento para los códigos que realmente cubra.
3. Contrastar minerales, clastos, matriz y cemento. No trasladar automáticamente
   la composición de un conglomerado a una lutita, ni del protolito al producto
   metamórfico. Explicitar cuándo la correlación es por formación/facies y no
   por un análisis del polígono concreto.
4. Aceptar solo los componentes justificados. Pueden coexistir
   `soil_siliceous` y `soil_calcareous` en una unidad mixta; no significa que
   ambos estén presentes en cada horizonte. Arenisca no implica suelo arenoso,
   ni silíceo implica un pH ácido medido. No deducir textura, drenaje, humus o
   descalcificación superficial de una denominación geológica.
5. Registrar por código: decisión, fundamento, fuente primaria, URL, página o
   apartado y alcance de la evidencia. Conservar SHA-256 de las fuentes.
   Si falta evidencia, dejar el suelo pendiente y conservar la litología válida.
   Una litología `accepted` con suelo vacío no es un suelo validado. Una nota
   genérica o una búsqueda sin resultado tampoco es una revisión terminada.
6. Validar el candidato antes de activarlo en local: conservar las 1.336
   identidades (1.055 geológicas), catálogos y registros ajenos; comprobar ambos
   lectores para todos los códigos. Agrupar únicamente reglas con metadatos
   idénticos, respetando los contratos existentes y el límite de 512 reglas.
   Instalar con comprobación de huellas y verificar los archivos en el contenedor.

## Material para continuar

- [Informe de estado y validación](../gis-review-2026-09-16.md).
- Directorio de trabajo: `tmp/soil-review-after-0.2.307/`. Incluye
  `research-queue.json`, `research-depth-count.json`, `geographic-scope.json`,
  `sources/`, `baseline/`, `build_review.py`, `verify_review.py` e
  `install_local.py`. Los scripts contienen decisiones explícitas, no un
  clasificador automático por palabras.
- Datos locales activos: `docker-data/mushroom-data/mushroom_gis_mappings.json`
  y `gis-mapping-reviews/unresolved-substrates-2026-09-16.json` bajo ese mismo
  directorio. La auditoría conserva las decisiones y referencias por código.

Revalidar archivos y recuentos al retomar: este documento es una instantánea.
Conservar evidencia y scripts necesarios, evitando copias de entrega o rollback
duplicadas. Para PDFs grandes recuperables se puede conservar texto, URL y
huellas, como en las tesis consultadas. No borrar las auditorías referenciadas.
La siguiente actualización de HA real queda fuera de esta tarea pendiente;
primero revisar y comprobar en local.
