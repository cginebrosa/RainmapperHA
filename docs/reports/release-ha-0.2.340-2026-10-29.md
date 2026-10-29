# Release HA 0.2.340 — 29/10/2026

Publicación autorizada por el usuario después de aceptar el runner local y
el cierre de pruebas. Parte de `99a4b6e1` (0.2.339) en la rama aislada
`fix/wunderground-recovery-20261029`, destinada a `origin/inicial`.

## Contenido y validación

Wunderground obtiene la clave pública una vez por runner, la comparte en memoria
y recupera el respaldo HTML del sitio antiguo. Conserva las ventanas de descarga,
los reintentos `gzip`/`identity`/`deflate` y el histórico particionado. AEMET
conserva el arreglo de 0.2.339. La integración MCP pendiente del checkout principal
no forma parte de esta release; no se modifica el worker.

- Runner completo ejecutado por el usuario en HA local: Wunderground `OK`,
  108/113 estaciones y 2.969 filas en 18,872 s. Clave: 0,457 s.
- Cinco estaciones sin datos para octubre y ocho respuestas antiguas tras los
  tres reintentos; se conservan sus históricos. El estado global 2 del runner
  corresponde a AEMET `PARTIAL` por un bloque diario fallido, de causa no determinada.
- Smoke completo: código 0, 2.168 pruebas, 55 omitidas; suite Python 128,922 s.
  Después sólo cambian versión, referencias de caché y documentación.
- Huellas efectivas del descargador en HA local coincidentes con la candidata.
  Los 578 archivos de código, pruebas y empaquetado registrados antes del build
  mantienen sus huellas después. No se repite el smoke por cambios documentales.

[Evidencia funcional y límites](wunderground-dynamic-key-local-2026-10-29.md).

## Publicación y cierre

Una sola ejecución de `scripts/build-push-ha-image.sh`, terminada con código 0.
`docker buildx imagetools inspect` confirma en GHCR que `0.2.340` y `latest`
comparten el digest:

`sha256:2896355562de6445bf792ba57d872f697de0f9e52cf1a9c3691e0a6095f9a670`

| Arquitectura | Manifest |
|---|---|
| `linux/amd64` | `sha256:6c56c8d3123f923435f53c2295e6c2814cead74d121dab23292126e33ee48e73` |
| `linux/arm64` | `sha256:bc89c5fca514b50569493aa9cee1e5827ee9a6a760f51ec9d43b1bb61ea23202` |

El script retira la etiqueta local 0.2.339 y ejecuta la limpieza acotada de
Buildx, que informa 5,783 GB liberados. No se eliminan versiones remotas.
Se conserva evidencia compacta y se eliminan los logs y el inventario temporales
de esta publicación. Código, bump, pruebas y documentación se incluyen en un
único commit. El checkout principal queda sin sincronizar, conservando su trabajo.

**Instalación y primer runner de 0.2.340 en HA real pendientes del usuario.**

[Recibo estructurado](release-ha-0.2.340-2026-10-29.json).
