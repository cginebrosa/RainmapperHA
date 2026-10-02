# Fuentes geográficas locales

Esta carpeta conserva material de procedencia, expansión y preparación. No es
una raíz operativa ni un fallback de HA o del worker. Los datos están excluidos
de Git y del contexto Docker; este documento y las notas de procedencia
científica que ya estaban versionadas se conservan en Git.

La geografía operativa completa de HA local está en
`../docker-media/rainmapper/geography/`. Incluye los originales necesarios para
sus lectores y para mantenimiento de mapeos, además de índices y manifiestos.
El worker conserva su caché `geography/` en su volumen independiente.

## Organización

- `originals/mushroom-GIS/`: descargas y documentos de las capas científicas,
  incluido material investigado y descartado que se conserva por procedencia.
- `originals/mushroom-map-GIS/`: descargas de las familias utilizadas en el mapa,
  documentación, licencias y herramientas históricas de adquisición.
- `expansion/mushroom-map-GIS/`: catálogo MFE nacional (incluida la descarga de
  Cataluña), geología española y municipios franceses; no implica integración.
- `preparations/mushroom-map-GIS/`: índices/ensayos anteriores separados de la
  publicación activa. No sustituir índices operativos con ellos.

Se conserva el árbol relativo de cada familia dentro de su categoría. Los
archivos con igual contenido no se han eliminado: el objetivo de esta fase es
separar los usos con una transición verificable y reversible.

`inventory.json` relaciona cada ruta original con su destino, tamaño y SHA-256
comprobado durante la copia. `tool-adjustments.json` registra las adaptaciones de
ruta posteriores de dos herramientas de adquisición/investigación y del catálogo.
No se han
ejecutado descargas ni esas auditorías históricas. Los nombres de rutas guardados
dentro de informes anteriores son procedencia histórica, no configuración viva.

Las carpetas `../mushroom-GIS-todelete/` y `../mushroom-map-GIS-todelete/`
conservan temporalmente los originales íntegros. No deben usarse para ejecutar
herramientas o resolver dependencias. Su retirada posterior requiere el cierre
de las comprobaciones y confirmación del usuario.

[Plan, estado y retirada final](../docs/mushrooms/geography-local-organization-plan-es.md).
[Catálogo histórico de fuentes científicas](originals/mushroom-GIS/README.md).
