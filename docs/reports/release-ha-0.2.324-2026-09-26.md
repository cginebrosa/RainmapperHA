# Release HA 0.2.324 — 26/09/2026

Publicación autorizada tras aceptación expresa de la candidata local. Instalación
HA real pendiente y a cargo del usuario. No se ha operado por SSH.

## Contenido

- Exportación del visor GBIF a ZIP con filtros, fotos y resolución de duplicados;
  importación con revisión por registro, mantener/reemplazar, restauración de
  archivadas, progreso, abundancia Normal, procedencia e incertidumbre conservadas.
- Recuperación GIS/DEM y asignación de microárea; creación opcional de setales por
  lote, reutilización, radios 500/495 m, ampliación con margen de 5 m y origen.
  SoilGrids desde cobertura local; no descarga territorios durante la importación.
- Navegación desde observación a setales, búsqueda por coordenadas y círculos
  nuevos o sobre geometrías existentes. Nombres editables con IDs estables.
- Nombres comunes de hosts GIS en detalle; calendario y escritura manual de
  fechas compatibles, sin perder la selección ni enviar antes de terminar.
- Al mover una observación desde el mapa, descartar GIS del punto anterior y
  conservar evidencia de campo. Asignar microárea sigue siendo una acción explícita.

## Validación y protección

- Smoke completo: **1.815 pruebas, 52 skips, OK**, 86,337 s; script código 0.
  `/private/tmp/rainmapper-0.2.324-smoke-final.log`.
- Chrome: seleccionar/cambiar/limpiar fechas, escritura con separadores, Enter,
  cambio de foco, fechas inválidas y carga inicial sin reenvío. Sin excepciones JS.
  `/private/tmp/observation-dates-browser.log`.
- Once pruebas dirigidas GIS; resolución de nombres comunes comprobada en es/ca/en.
- HA local reconstruida/recreada y página de observaciones comprobada. Paridad
  revalidada al aceptar: **228 archivos, cero diferencias**, SHA agregado
  `81b71636c39b2c64d3db6fc11f2090fbe5093a9b6276df56dffe03eb68407801`.
  Después sólo bump, cache-busters, changelog y documentación; sin cambios funcionales.
- Worker sin reconstrucción ni reinicio; identidad, arranque, imagen y huellas de
  coordinadores/credenciales conservados. Observaciones privadas repo/local y
  política/suspensiones conservadas; JSON privado excluido de imagen y commit.
- HA real: diagnóstico previo únicamente por lectura del volumen share. No se
  modificaron datos. No se lanzaron entrenamientos ni precálculos operativos.
- Pruebas previas de funcionalidades: [GBIF](gbif-import-local-2026-09-25.md) y
  [navegación/setales](known-sites-navigation-local-2026-09-25.md), con su alcance
  y fecha específicos. La candidata final tiene el smoke/paridad de este informe.

## Publicación verificada

`./scripts/build-push-ha-image.sh` terminó con código 0; una sola instancia,
seguida mediante la misma sesión durante build, push y limpieza local de caché.
Log: `/private/tmp/rainmapper-0.2.324-build-push.log`.

`docker buildx imagetools inspect` para ambos tags confirma:

- `0.2.324` y `latest`: `sha256:edc07e41ee0075b6af0f53a3d6ed2369d79786d7a43300c3c0edd6dcaf1a712b`.
- amd64: `sha256:5d7ab2ba1fbae23ecd83e9b325be5b99deb46cbad1054bdc0126712e9a5655ba`.
- arm64: `sha256:6062b6114909b6550620ab5562b28580412cc1bfe662dfd8a636a81d622fd96c`.

Código, pruebas, documentación, changelog y bump se cierran en un único commit
`Release Home Assistant 0.2.324`, posterior a la verificación GHCR.
