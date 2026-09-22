# HA 0.2.318 — 22/09/2026

El usuario aceptó la prueba visual local y pidió «vale, publicamos version HA».
Publicación de imagen confirmada; instalación en HA real a cargo del usuario.

## Alcance

- Recepción HTTP por bloques y verificación secuencial del precálculo, manteniendo
  límites, integridad y activación atómica.
- Política reversible de consenso (desactivada / solo comparar / aplicar), dos
  alternativas semanales para Ou, Edulis y Pinícola cuando corresponde. Conserva
  el IFF; faltas de datos y abstenciones se explican por separado.
- Conclusión verde/roja bajo temporada y un único Detalle con modelos, IFF y
  perfiles técnicos. Sin cambiar IDW ni reentrenar para el cambio visual.
- Worker local 1.1.5 incluye memoria y política compartidas, importación del
  servicio comprobada durante el build. No se publica imagen remota del worker.
- Observaciones privadas modificadas por el usuario excluidas del commit.

## Validación

Smoke definitivo: 1.724 pruebas, 52 skips, correcto (80,201 s de suite Python).
Registro: `/private/tmp/rainmapper-release-0.2.318-smoke.log`.
Pruebas visuales: 41 consultas, acuerdo/desacuerdo, desplegable único, perfiles
visibles, pantallas 1280/320 px. Tras el smoke solo metadatos de versión,
cache-busters y documentación; valores mecánicos comprobados.

Circuito local lanzado por el usuario: reconstrucción
`worker_job_nUoV4TXWa0U59aFx`, base `worker_job_yJWXlX7xGk8VPjJa`, multiversión
`worker_job_25OJr56p3RhQpdJc` (792/792 ajustes) y precálculo
`worker_job_TSqdxNLr7YfS` completos, verificados y limpieza terminal completa.
Recepción y activación HA/worker: revisión 73, 48.459.776 bytes y SHA común
`431e73ef52a2f5f2692f0b822cc3057ed87b5ae2b575b6333d22b4ff2dbda38e`.
Detalle de tiempos y límites: [informe de memoria](ha-memory-precompute-2026-09-22.md).

HA y worker reconstruidos/recreados con versiones finales; paridad efectiva
217/117 archivos sin diferencias, HTTP HA 200 y worker 1.1.5 con ambos carriles
idle. Configuración y credenciales verificadas por SHA antes/después, idénticas.
Coordinadores conservados: `http://100.111.77.48:8100` y
`http://rainmapper-ha-ui:8100`.

Imágenes locales finales:
- HA: `sha256:344b04b2615a902c98510c1099b0f55bd466f6530d8babf87f0640681ae37503`.
- Worker: `sha256:f4478b37b994ba48b99637326ce9ba538617d9c5c10b780b2df18807c1d14e5a`.

## Publicación verificada

`build-push-ha-image.sh` terminó con código 0. Una única ejecución, supervisada.
Registro: `/private/tmp/rainmapper-release-0.2.318-publish.log`.
Consultados ambos tags con `docker buildx imagetools inspect`:

- `ghcr.io/cginebrosa/rainmapperha:0.2.318` y `latest`:
  `sha256:b3b240a18edca0337692a570e6b8a78aab5441e15ca09d7c956e68943749e79e`.
- linux/amd64: `sha256:3d525c9dd4305030c41d095cc1cc2dd7897de82bffcfa6d2c273e829c9b3386e`.
- linux/arm64: `sha256:180c4d69d21bfa897703187ffef0a27f50a2248b1385bd02285298d07a902da4`.

No se ha instalado ni medido esta versión en la Raspberry. Sin configuración
explícita, la política mantiene modo desactivado; publicar no activa el filtro
ni lanza entrenamiento/precálculo en HA real. El consumo inicial/cachés sigue
siendo investigación separada de la reducción del pico de validación.
