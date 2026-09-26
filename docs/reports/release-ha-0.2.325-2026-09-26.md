# Release HA 0.2.325 — 26/09/2026

El usuario acepta la corrección local de Meteocat y autoriza publicar. Instalación
HA real a cargo del usuario; transferencia de datos reparados todavía pendiente.

## Contenido y validación

- Consultar grupos diarios UTC completos en las cuatro consultas Meteocat. El
  primer fragmento de la ventana deja de sobrescribir un día completo anterior.
- Mantener las fechas solicitadas, verano/invierno y correcciones oficiales a la
  baja; no modificar los intervalos de otras fuentes ni migrar la identidad diaria.
- 12 pruebas dirigidas correctas. Smoke completo: **1.819 pruebas, 52 omitidas,
  OK**, 85,974 s; script código 0. `/private/tmp/meteocat-fix-smoke.log`.
- HA local reconstruida/recreada; paridad 228 archivos, cero diferencias. SHA
  agregado `b21300f7f29f6d70791f5b74010709cbf4eef67dbce149a4cdb722ecb83f715a`.
  Evidencia `tmp/release-0.2.325/parity.json`. Después sólo bump mecánico,
  cache-busters, changelog y documentación; sin cambios funcionales posteriores.
- Worker, coordinadores, suspensiones y observaciones privadas sin tocar.
  Sin SSH, entrenamiento ni precálculo; ningún JSON privado forma parte del commit.

## Reparación separada de datos

Candidata local: 6.700 registros / 24.034 valores de Meteocat reparados, incluidos
1.171 valores de lluvia, con fuente oficial 01/08–25/09. Sólo cambia Meteocat 2026
y su CSV; las otras 45 particiones y CSV de otras fuentes permanecen idénticos.
Original descargado intacto. [Informe y plan de transferencia](meteocat-partial-days-2026-09-26.md).
La actualización de la imagen por sí sola no recupera ese histórico.

## Publicación

`build-push-ha-image.sh` terminó con código 0, una sola instancia supervisada
hasta el cierre. Registro: `/private/tmp/rainmapper-0.2.325-build.log`.
`docker buildx imagetools inspect` verifica ambos tags y plataformas:

- `0.2.325` y `latest`: `sha256:ba76ee742f9cbec12c63b721b8769a2f76e4e621f8173016fc0656214b17b0f0`.
- amd64: `sha256:f49196353125cf7510732c32126bdf1cd96bc7459efbabb9d469eff1458a3ef4`.
- arm64: `sha256:6a3791ae3721d1badeb05de86a71b0bb5979caf81a8ac49a5a952e019ea1eebc`.

Código, pruebas, bump y documentación se cierran en un único commit
`Release Home Assistant 0.2.325`, después de verificar GHCR. Instalación y
transferencia de datos a HA real aún pendientes.
