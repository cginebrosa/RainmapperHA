# Release HA 0.2.337 — 11/10/2026

El usuario finalizó el cálculo local de cinco especies y autorizó publicar.
Instalación y prueba de HA real pendientes, a su cargo.

## Alcance

- Elegir especies de selección/comparación mediante las 21 casillas del catálogo,
  en una cuadrícula adaptable dentro del desplegable de Workers y trabajos.
- Guardar la selección común a la instalación para trabajos manuales y runner,
  conservar el borrador durante refrescos y bloquear cambios de alcance activos.
- Incluir las especies en la identidad de preparación y reutilizar evaluaciones
  compatibles. Mantener reglas A/B/C/D, K y predicción habitual.
- Conservar aereus/caesarea como valores iniciales al actualizar una instalación
  sin selección guardada. La selección local de cinco no se exporta a HA real.

## Validación local aceptada

HA local y worker reconstruidos/recreados antes de las pruebas del usuario.
Paridad efectiva revalidada contra el worktree: siete archivos de HA y cuatro
del worker; procedimiento común
`a8b31f5b7be370026a8d16fd3bf1e5ebf06071cd53c46e89091a52e826e70421`.
Coordinadores, recursos 4 CPU / 8 GiB y fuentes privadas conservados.

Trabajo `worker_job_paDOHshhqxHzSEcM` completo y recibido: 169,34 s de cálculo,
172 s totales incluyendo 2 s de cola. Control `ready`, sin K pendientes ni error.
Cinco especies y K=2/4, diez comparaciones preparadas con Habitual y A/B/C/D.
Evidencia de 567094 bytes; SHA-256 del archivo coincide con el recibo de HA:
`aa1ee08dc8a3fdc3bc435fe1ab6d3eae41e363eb1a7ca0f3ea81e022b93fb87c`.
No se lanzaron nuevos cálculos durante la release.

93 pruebas dirigidas y navegador contra HA local reconstruido: guardado, recarga,
borrador conservado, desplegable cerrado y sin desbordamiento a
1600/768/375/320 px. Ver [informe funcional](competing-species-local-2026-10-11.md).

## Comprobaciones de release

`PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: exit 0; 2134 pruebas
en 99,002 s, 55 omitidas por disponibilidad del entorno, sin fallos. Sintaxis,
versiones, empaquetado, fixtures y diff correctos. El primer intento dentro del
sandbox produjo siete `PermissionError` por restricciones del entorno; el
mismo código pasó al repetirlo con los permisos necesarios.

Después sólo se modificaron versiones, seis cache-busters, changelog y
documentación. Los tres metadatos y los visores están alineados en 0.2.337.
Observaciones privadas excluidas del commit y no incorporadas a la imagen:
el Dockerfile utiliza el fichero vacío de defaults.

## Publicación

Una ejecución de `scripts/build-push-ha-image.sh`, exit 0. Se aplicó la retención
local de imágenes/caché ya autorizada. No se reiniciaron contenedores ni se
cambiaron coordinadores durante la publicación.

`docker buildx imagetools inspect` confirma que `0.2.337` y `latest` tienen
el mismo digest y contienen `linux/amd64` y `linux/arm64`:

`sha256:5b5b93ddcfc8501a96a9f22355090b683d7d6fb1aa43584eb1e10534ce3c7020`

Código, pruebas, versión y documentación se agrupan en un único commit posterior
a verificar GHCR. La limpieza remota anterior de versiones antiguas tiene su
[recibo independiente](ghcr-cleanup-2026-10-11.md); no se repite durante esta release.

Evidencia privada: `tmp/jobs/release-ha-0.2.337/`, con auditoría del trabajo,
logs de smoke/build y consultas de ambos manifests.
