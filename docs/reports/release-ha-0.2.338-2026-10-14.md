# Release Home Assistant 0.2.338 — 14/10/2026

## Autorización y alcance

El usuario aceptó el resultado local y pidió publicar: «pues publicamos version
de HA». La release añade excepciones de coordenadas Meteoclimatic administradas
con `/share/rainmapper/meteoclimatic-fixed-coordinates.txt`, junto a `stations.txt`.
Incluye nuevas descargas, archivado de pendientes y recuperación del CSV después
de una interrupción. No modifica mediciones meteorológicas. `#` desactiva una
entrada; la instalación conserva el archivo del operador.

Preparación aislada desde `8f3998e9` (0.2.337), rama
`fix/meteoclimatic-fixed-coordinates`. Excluye el trabajo MCP/Gemma pendiente y
los datos privados. El checkout principal conserva esos cambios para continuar
cuando el usuario lo indique; Gemma sigue pausado.

## Validación previa aceptada

- 38 pruebas dirigidas correctas y smoke completo: 2146 pruebas, 55 omitidas.
- Imagen candidata reconstruida; nueve huellas de código/plantilla verificadas
  en el contenedor de aceptación y en HA local habitual.
- Copia aislada: error de 889.561 km reproducido; cuatro lotes cerrados en
  19,953 s, 16.497 filas verificadas y observaciones ajenas preservadas.
- Runner completo lanzado por el usuario en HA local: exit 0, 1m36s; registros
  de hoy en las cuatro fuentes, CSV y Parquet coincidentes, cero pendientes.
- Roda de Ter conserva 41.99, 2.32 y altitud 465 m en su lectura nueva.
- Wunderground fue parcial: cinco fallos de estación y ocho respuestas antiguas.
  Esto se comunicó antes de que el usuario autorizara la publicación.

[Detalle y evidencia local](meteoclimatic-fixed-coordinates-local-2026-10-14.md).
No cambió código ejecutable tras la validación; no se repitió el smoke por
actualizar documentación. Worker y MCP no se reconstruyeron ni reiniciaron.

## Publicación

Publicación completada con exit code 0. Una sola ejecución de
`scripts/build-push-ha-image.sh`, desde el candidato aislado. Verificación remota
posterior de ambos tags mediante `docker buildx imagetools inspect`, con tiempo
máximo por consulta de 45 segundos:

| Tag | Digest | Plataformas de ejecución |
| --- | --- | --- |
| `ghcr.io/cginebrosa/rainmapperha:0.2.338` | `sha256:a33f3eab7376c4f675e17f6987507a70af95459e7ec56bc204bfbba5696a578b` | `linux/amd64`, `linux/arm64` |
| `ghcr.io/cginebrosa/rainmapperha:latest` | Mismo digest | `linux/amd64`, `linux/arm64` |

Los otros dos manifests son attestations. Limpiezas automáticas desactivadas
mediante `LOCAL_IMAGE_CLEANUP=0` y `LOCAL_BUILD_CACHE_CLEANUP=0`; sin limpieza GHCR.
No se necesitó cancelar ni duplicar el build.

Log, consultas remotas y recibo JSON conservados en
`local/evidence/meteoclimatic-fixed-coordinates-20261014/`:
`ha-0.2.338-build-push.log`, `ghcr-0.2.338.txt`, `ghcr-latest.txt`,
`ghcr-verification.json`. Código, tests, versión, changelog y documentación se
agrupan en un único commit `Release Home Assistant 0.2.338`, destinado a
`origin/inicial` después de verificar GHCR.

## Instalación y retirada pendiente

El usuario ya confirmó haber subido el TXT a HA real. **No confirma que 0.2.338
esté instalada ni que su runner haya terminado**. Instalación y prueba real a su
cargo; Codex no accede a HA real ni inicia trabajos operativos.

El contenedor `rainmapper-ha-coordinate-patch-acceptance` está parado. El usuario
autorizó borrarlo cuando local y HA real estén comprobados; esperar su confirmación
real. Los recibos de validación se conservan en `local/evidence/`.
