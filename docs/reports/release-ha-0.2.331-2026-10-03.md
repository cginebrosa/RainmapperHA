# Release Home Assistant 0.2.331 — 03/10/2026

Publicación autorizada tras confirmación del usuario de la edición circular local.
La instalación, parada y arranque en HA real siguen a cargo del usuario.

## Cambios incluidos

- Círculos: controles ES/CA/EN según dispositivo; mover centro y cambiar radio
  con dos controles, manteniendo GeoJSON y las coordenadas originales en no-op.
- GBIF: aceptar coordenadas de hasta 16 decimales y reconocer círculos WGS84,
  además de los anillos Mercator dibujados por TerraDraw. Corregido el rechazo
  al abrir Riudarenes. Polígonos alterados no se fuerzan a círculo.
- Organización geográfica: rutas canónicas locales, herramientas WU/GBIF,
  exclusiones de fuentes y antiguos en Docker/Git, y documentación de transición.
  Conserva precedencia de configuración explícita y compatibilidad HA.
- Notas de geografía versionadas trasladadas a `geography-sources/`.
  No incluye datos GIS, observaciones privadas ni carpetas `-todelete`.

## Validación

- HA local previamente reconstruida/recreada con el código definitivo y aceptada
  por el usuario. Prueba en Riudarenes: apertura, cambio de radio, no-op exacto y
  descarte con archivo persistido idéntico byte a byte. Navegador aislado:
  ampliar/reducir/mover, guardar/reabrir, añadir/sustituir/descartar y tres idiomas.
- Geografía: reconstrucción/lecturas y paridad HA/worker registradas en el
  [plan local](../mushrooms/geography-local-organization-plan-es.md).
- Paridad revalidada en esta release: nueve archivos afectados HA y cuatro del
  worker coinciden con el worktree. No se repiten reconstrucciones/pruebas
  funcionales sin cambios desde la validación aceptada.
- Smoke final: `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`, correcto;
  **1.859 tests, 55 omitidos**, 88,583 s de suite Python; regresión JS independiente
  de círculos GDAL correcta. Versiones/cache-busters y diff comprobados tras bump.
- Sin cambios funcionales después del smoke. Sin entrenamiento, precálculo,
  reinicio del worker ni cambio de coordinadores. No se accede a HA real.

## Publicación comprobada

`./scripts/build-push-ha-image.sh` terminó con código 0 en una única ejecución.
Consultados ambos tags mediante `docker buildx imagetools inspect`:

- `ghcr.io/cginebrosa/rainmapperha:0.2.331`
- `ghcr.io/cginebrosa/rainmapperha:latest`
- Digest común: `sha256:be84ceaedf2289f73157b39661b7d4480c69c23de276d4d61a47dc5685dde90b`.
- amd64: `sha256:623642f056772901e3b2f712c0c992fad5b702eb870466e8af5e5d460390815a`.
- arm64: `sha256:6b2c43076a0a156a29bad1c61ebb3f6caf48002b7a5c551578bcdc406db49ad5`.

Evidencia local: `tmp/release-0.2.331/` (`smoke.log`, `parity.json`,
`candidate-hashes.json`, `build-push.log`, `ghcr-latest.txt`). Navegador y
regresión GBIF: `tmp/sites-circle-edit-20261002/verification.json`.

## Pendientes y límites

El usuario instala 0.2.331 y verifica la edición de setales en HA real.
Última instalación real confirmada: 0.2.330. No hace falta migrar media para
esta release. Conservados todos los antiguos; su borrado requiere revisión y
confirmación propias. Observaciones privadas fuera del commit y de la imagen.
