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
