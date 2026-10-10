# Release HA 0.2.335 — 10/10/2026

El usuario autorizó «publicamos HA» después de la validación local del cambio de
referencia para selección y comparación. La instalación y prueba en HA real
quedan a su cargo.

## Alcance

- Selección A/B/C/D y comparación Iₖ, incluida la habitual, con la última
  preparación compatible, también en modo histórico y «Comprobar predicción».
- Fecha y coordenadas consultadas conservadas para meteorología e IFF. El visor
  muestra la fecha de referencia usada para la selección con modelos actuales.
- Acumulados históricos conservados; ningún clic prepara ni entrena modelos.
  No cambia la huella científica ni hace falta repetir una preparación compatible.
- Contrato de mapa `map_competing_selection_v3`. El worker local ya contiene el
  código compatible; esta publicación es de HA. Se conservan los coordinadores.

Ver [validación funcional local](competing-current-reference-local-2026-10-10.md):
87 pruebas dirigidas, navegador de escritorio/móvil y consulta real de Olvan
del 17/09/2019. Mantiene IFF habitual 54/100 y muestra las cinco notas actuales
sobre 90 visitas, referencia 10/10/2026.

## Verificación de release

- HA local y worker reconstruidos y recreados antes de la autorización.
  Comprobación previa al bump: 251 archivos de HA y 150 del worker coinciden
  con el worktree, sin diferencias ni rutas sin resolver.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: exit 0;
  2.106 pruebas en 99,234 s, 55 omitidas por disponibilidad del entorno,
  sin fallos. Sintaxis, empaquetado y fixtures correctos.
- Después del smoke sólo cambian versión, cache-busters, changelog y
  documentación. Comprobadas las tres versiones y los seis cache-busters
  en 0.2.335; `git diff --check` correcto.
- Archivos privados de observaciones excluidos del commit y conservados por
  huella. Los archivos ejecutables candidatos no cambiaron durante el build.
- No se ejecutan entrenamientos, selección/comparación ni precálculos.

## Publicación GHCR

Una única ejecución de `scripts/build-push-ha-image.sh`, terminada con exit 0.
Comprobación remota con `docker buildx imagetools inspect`: los tags
`ghcr.io/cginebrosa/rainmapperha:0.2.335` y `latest` comparten digest:

`sha256:addc77eecbaa971cdf6da1976cb363ebd857136044991a97cf640a9e5212641d`

Ambos contienen manifests `linux/amd64` y `linux/arm64`, además de attestations.
El script aplica la retención local de imágenes y caché acordada; no elimina
fuentes, observaciones ni volúmenes operativos.

Recibos privados: `tmp/jobs/release-ha-0.2.335-20261010/` contiene `smoke.log`,
`build-push.log`, `local-parity.json`, `ghcr-verification.json` y las huellas
de conservación. Código, pruebas, metadatos y documentación se incluyen en un
único commit de release posterior a verificar GHCR.

Pendiente: instalación y prueba de HA real por el usuario.
