# Limpieza GHCR · 11/10/2026

El usuario autorizó limpiar GHCR mientras ejecutaba su cálculo local.
Alcance exclusivo: paquete `cginebrosa/rainmapperha`, siguiendo la retención
documentada en `docs/decisions.md` (sección GHCR) y `docs/release-flow.md`.

Inventario autenticado de GitHub Packages: 155 entradas. Se conservaron la
versión de `rainmapper-app/config.yaml` (`0.2.336`), `latest`, el rollback
inmediato (`0.2.335`) y todos los manifests referenciados por ambos índices.
No había proceso local de publicación de imágenes en curso en la comprobación.

Se eliminaron 145 entradas correspondientes a 29 versiones antiguas:
`0.2.305` y `0.2.307`–`0.2.334`. Cada borrado quedó registrado con su ID,
digest, tags y respuesta HTTP 204. Ningún borrado falló.

El inventario posterior contiene exactamente las diez entradas protegidas:
dos índices, cuatro imágenes de arquitectura y cuatro manifests de attestation.

| Tags conservados | Digest del índice |
| --- | --- |
| `0.2.336`, `latest` | `sha256:8af3d7f701b785ea1b3e7b48a42d71c984365e79d94eb61104cca966fc94ce4b` |
| `0.2.335` | `sha256:addc77eecbaa971cdf6da1976cb363ebd857136044991a97cf640a9e5212641d` |

Verificación posterior por API de registry: los diez manifests siguen accesibles
y sus SHA-256 coinciden byte a byte con los anteriores. Verificación adicional
con `docker buildx imagetools inspect` para los tres tags: índices correctos,
`linux/amd64` y `linux/arm64` presentes en ambas versiones.

No se modificaron imágenes locales, contenedores, coordinadores, archivos de
datos ni el trabajo de cálculo del usuario. No hubo build, publicación o deploy.

Evidencia privada: `tmp/jobs/ghcr-cleanup-20261011/`, con `plan.json`
(inventario y árbol protegido), `deleted.jsonl` (145 recibos), `after.json`,
`verification.json` y `after-*.txt` (verificación Docker).
API utilizada: `GET/DELETE https://api.github.com/users/cginebrosa/packages/container/rainmapperha/versions`.
La autorización se tomó de `GH_TOKEN`, sin guardarla en los recibos.
