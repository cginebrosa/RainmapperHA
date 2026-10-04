# Release HA 0.2.332 · 04/10/2026

Publicada tras la aceptación expresa de HA local por el usuario y su instrucción
«pues publicamos version de HA». La instalación y prueba en HA real quedan a
cargo del usuario; no se ha instalado ni reiniciado HA real desde esta sesión.

## Cambio publicado

- Capa de áreas y microáreas conocidas en el mapa de predicciones, con botón de
  polígonos debajo de Observaciones, colores diferenciados y etiquetas al acercarse.
- Compatible con las demás capas, consultas del mapa y cambios de mapa base;
  disponible en escritorio y móvil. Controles y leyenda en ES/CA/EN.
- Mismo permiso `can_use_observations_map` en interfaz y API. La lectura privada
  no devuelve notas, fotos ni fichas completas, y no crea trabajos ni modifica datos.
  Carga al activar, cancela al desactivar y retira la capa al revocar el permiso.
- Respuesta acotada y almacenada en caché por revisión del fichero de origen.
  Datos locales medidos: 72 áreas + 113 microáreas, 10.371 vértices, 411.808 bytes.

[Especificación](../mushrooms/prediction-map-specification-es.md).
No cambia SMI, meteorología, modelos, entrenamientos, precálculos ni contratos del worker.

## Validación

- HA local reconstruida/recreada antes de la aceptación del usuario. Antes de
  publicar se revalidaron las seis huellas de código/etiquetas contra el contenedor
  y contra la evidencia de la versión probada: todas coinciden.
- Pruebas dirigidas: 28 correctas. Navegador compartido correcto, con convivencia
  de capas, autorización, texto seguro, cambio de estilo, cancelación, errores,
  reintento, leyendas y capturas de escritorio/móvil.
- Smoke definitivo: `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`,
  **1.911 pruebas, 55 omitidas; resultado correcto**. Incluye las pruebas locales
  preexistentes del worktree, que permanecen fuera de este commit si no pertenecen
  a la capa. No se repitieron investigaciones ni trabajos operativos.
- El primer intento dentro del sandbox terminó con seis errores al abrir
  servidores de prueba en localhost (`PermissionError`). Se conservó ese log y
  se repitió fuera del sandbox con éxito, sin cambios de código.
- Después del smoke sólo se modificaron las tres referencias de versión,
  cache-busters de ambos visores, changelog y documentación. Versiones alineadas
  y `git diff --check` correcto; sin segundo smoke tras el bump mecánico.

## Publicación y comprobación remota

Una sola ejecución de `./scripts/build-push-ha-image.sh`, supervisada hasta su
salida 0. Verificación posterior con `docker buildx imagetools inspect` para ambos
tags:

| Tag | Digest del índice |
|---|---|
| `ghcr.io/cginebrosa/rainmapperha:0.2.332` | `sha256:6e48babc0868d84a76509bb95cd0418ff778d8926f59df8f7e74b623703717b2` |
| `ghcr.io/cginebrosa/rainmapperha:latest` | `sha256:6e48babc0868d84a76509bb95cd0418ff778d8926f59df8f7e74b623703717b2` |

Manifests presentes en ambos tags:

- `linux/amd64`: `sha256:f638be8965788b9e56e84ebdecd13ab5e6cb0680969c713fd49a80e00ce4491a`.
- `linux/arm64`: `sha256:65e085679fb287503eb443b6a025a1eb8708ce605dfe79533cff64e3429cae32`.

El usuario autorizó expresamente mantener activadas las limpiezas de Docker del
script para reducir ocupación local. Se retiró la etiqueta local 0.2.331 y
`docker buildx prune --max-used-space 8589934592` informó **6,486 GB** recuperados;
no se interpreta como una medición del espacio libre total del Mac. No se han
retirado fuentes, archivos privados, volúmenes ni carpetas históricas.

Evidencia local privada conservada en `tmp/release-0.2.332/`: `parity.json`,
`smoke.log`, `smoke-authorized.log`, `build-push.log`, `ghcr-version.txt`,
`ghcr-latest.txt` y huellas de los dos archivos privados de observaciones.
Validación funcional previa: `tmp/known-sites-map-20261004/validation.json`.

## Continuidad

Código, pruebas de la capa, versión, changelog y documentación de release se
publican en un único commit tras comprobar GHCR. Los cambios locales previos
ajenos a esta release y las observaciones privadas se conservan sin incorporarlos.
No se ha cambiado el coordinador ni reiniciado/reconstruido el worker.

El usuario puede instalar 0.2.332 en HA y comprobar el botón y su permiso. La
discusión sobre utilidad de aereus/caesarea sigue pendiente; esta release no
aprueba k=2, 3, 4 ni inicia experimentos.
