# HA 0.2.323 — publicada el 25/09/2026

Publicación y commit/push autorizados por el usuario. Instalación en HA real a su
cargo; no realizada por el agente.

## Cambios

- Wunderground: admitir `.station-header` y `dashboard-header-view`, altitud con
  unidades explícitas m/ft, hemisferios e identidad de estación verificados.
- Conservar el uso de metadatos ya guardados. Reintentar contenido incompleto con
  HTTP 200, errores HTTP y transporte; tres intentos por fase, timeout y variantes
  de codificación existentes. Sin navegador como dependencia del runner.
- Filtrar fechas antes de escribir CSV; rechazar respuestas sin observaciones del
  intervalo. Si todas las estaciones fallan, fallar la fuente y recurrir al
  histórico existente, evitando declarar éxito por una descarga vacía.
- SoilGrids: mostrar área, microárea, estado y cobertura con enlace a mantenimiento;
  retirar la promesa inexacta de reintento automático de contextos parciales actuales.

El bloqueo previo de offsets mensuales positivos queda pendiente. Esta release
no cambia modelos ni intenta suavizar la predicción de Aereus en Olvan. Diagnóstico
en [informe del 24/09](aereus-olvan-soilgrids-2026-09-24.md).

## Validación

- HA local reconstruido/recreado antes de publicar; 224 archivos efectivos sin
  diferencias, huella
  `b7dbeb59e4766da81283e4dcbddf8543761f3d201fb31ff1ccc6163f04f5b706`.
- 32 pruebas WU: ambos formatos, unidades, coordenadas, identidad, recuperación,
  agotamiento acotado, fechas ajenas y CSV vacío. Metadatos reales de IALCAL258,
  IALLEP1 e ILAIGL7 leídos correctamente sin escribir meteorología en HA real.
- Fixtures de ambos formatos y rechazo de año incorrecto ejecutados dentro del
  contenedor HA local; HTTP 200 del servidor.
- Aviso SoilGrids: tres pruebas dirigidas y comprobación de presentación con Chrome.
- Smoke completo: **1.770 pruebas, 52 omitidas, OK**, 81,567 s.
  Log `/private/tmp/rainmapper-0.2.323-smoke.log`.
- Tras el smoke sólo bump, cache-busters, changelog y documentación; metadatos
  de versión verificados sin repetir la suite.

## Publicación y conservación

- GHCR `0.2.323` y `latest`, digest común
  `sha256:7a68ff2a0594d6a219f0dff54603fb0c891463898a590c94f2df983f4a3989f4`.
- Manifests `linux/amd64` y `linux/arm64` verificados. Script finalizado, código 0.
- Log `/private/tmp/rainmapper-0.2.323-publish.log`; evidencia no versionada en
  `tmp/release-0.2.323/` (inspecciones GHCR, paridad y snapshots de conservación).
- Worker sin build, publicación ni reinicio: no ejecuta el extractor WU ni la UI
  modificada. Mismo contenedor, imagen, arranque, destinos, credenciales e identidad.
- Hashes de observaciones privadas repo/local y política de predicción conservados
  durante esta release. Observaciones privadas excluidas del commit y de la imagen.
- No se han lanzado entrenamientos, precálculos ni runners operativos.
