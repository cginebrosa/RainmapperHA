# Release HA 0.2.327 — 27/09/2026

Usuario: «publicamos». Imagen publicada y verificada; instalación pendiente a
cargo del usuario.

## Contenido

- Casillas del importador GBIF fijadas a 16 × 16 px, también cuando los selectores
  Mantener/Reemplazar ensanchan la columna de un lote mixto.
- Notas de pendiente DEM al crear microáreas GBIF, con media y rango igual que
  en mantenimiento. Conserva cero; no inventa valores con DEM ausente/incompleto.
  No migra microáreas existentes ni cambia geometrías o incertidumbre.

## Validación

- HA local reconstruida/recreada y código efectivo idéntico al worktree:
  `mushroom_gbif_sites.py` SHA-256
  `0f9142ae1ae9e7677ae45bc1191c89a03f77ffcc4e6e60c14f07904e3f5ac456`;
  `mushroom_gbif_ui.py`
  `7968eea69f9d2ed97ccb464c3fb7b56d2445918baf7499619b26278638fc820d`.
- Observaciones HTTP 200. Navegador con estilos completos, lote mixto y medidas
  de casillas correctas; captura inspeccionada. 42 pruebas dirigidas del
  importador, incluidas persistencia de notas, cero y ausencia de DEM.
- Smoke completo: **1.831 pruebas, 52 omitidas, 89,756 s, OK**, código 0.
  Registro `docker-data/release-0.2.327-smoke.log`.
- Después del smoke sólo bump mecánico, cache-busters, changelog y documentación.
  Versiones y cache-busters alineados en 0.2.327.

## Publicación

Una instancia de `build-push-ha-image.sh`, supervisada hasta código 0. Registro
`docker-data/release-0.2.327-build.log`. Verificado con `imagetools inspect`:

- Tags `0.2.327` y `latest`, mismo digest:
  `sha256:5cc973b4b1c3eedeafcbd61279a90c1a55d8002ef2669f763c1c01103d9c2d3e`.
- AMD64: `sha256:f6ee8d6d1d00fd95df0491c1b368c566e584ae6f1df741aed779d6738dce583c`.
- ARM64: `sha256:385c4b01bf6941b6a8951b0daf7185c81be58272a63f4ea615b01f42919844fc`.

Código, pruebas, bump y documentación en un único commit posterior a verificar
GHCR. Observaciones privadas excluidas. Worker, coordinadores, suspensiones y
datos reales intactos; sin SSH, entrenamientos, precálculos ni runners.
