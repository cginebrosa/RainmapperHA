# Visor de observaciones GBIF

- `code/`: fuentes HTML/JS/CSS, construcción del visor, adquisición y comprobaciones.
- `docs/`: guía de uso, evaluación y planes de integración.
- `data/`: snapshots originales, fotos, metadatos y muestras de investigación.
  Cada snapshot conserva su visor autónomo generado y sus scripts de procedencia
  como parte del artefacto archivado; las fuentes para trabajar están en `code/`.

Abrir con `./local-apps/gbif/start.command`. Utiliza la URL de archivo anterior
mediante un enlace al snapshot trasladado: conserva el acceso por marcadores y
evita cambiar el origen usado por las revisiones del navegador.

Las revisiones que solo existen en el navegador siguen allí. Los archivos de
autoguardado elegidos en otras carpetas no se han movido. Exportar/importar la
revisión o usar el archivo guardado permite cambiar de navegador; una ruta nueva
no garantiza por sí sola acceso al almacenamiento de una URL `file://` anterior.

No ejecutar los descargadores por rutina. Para comprobar el visor usando un
perfil de navegador temporal, desde la raíz del repo:

```sh
node local-apps/gbif/code/check_gbif_viewer.mjs local-apps/gbif/data/snapshot-catalunya-20120619-20260916-full
```

[Guía y procedencia](docs/guide.md).

[Diseño de exportación a Rainmapper e importación pendiente de revisión](docs/gbif-rainmapper-export-import-design.md)
(25/09/2026; implementación local pendiente de aceptación).

Para exportar: aplicar filtros, pulsar **Exportar a Rainmapper**, seleccionar
la carpeta del snapshot como origen y revisar el resumen. **Guardar ZIP** pide
nombre y ubicación de destino (Chrome/Edge); las selecciones grandes se dividen
en lotes. Después, desde la lista de observaciones de HA local, **Importar GBIF**
permite previsualizar el ZIP y aceptar o rechazar las nuevas observaciones.
Las aceptadas quedan como Borrador / Revisar antes de usar, con abundancia Normal.

Actualización de la prueba local: el modal distingue origen/destino y muestra
los nombres elegidos. En ZIP existentes permite ignorar/reemplazar IDs repetidos;
en importación permite mantener/reemplazar, también restaurando citas archivadas.
Al aceptar recupera GIS/DEM, asigna microárea por contención única y muestra
progreso por cita. Los botones permanecen visibles mientras se desplaza la lista.

La opción **Crear áreas y microáreas cuando falten** permite ampliar el registro
de setales durante la importación: plan revisable, radios 500/495 m, ampliaciones
automáticas y reutilización dentro del lote. Recupera GIS/DEM y SoilGrids local por
microárea; conserva el origen de creación. Los nombres nuevos son editables.
