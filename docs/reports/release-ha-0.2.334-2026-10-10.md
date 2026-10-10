# Release HA 0.2.334 — 10/10/2026

El usuario confirmó «vale, funciona» tras la activación local y autorizó publicar
la versión de HA para instalarla y probarla allí. La instalación y la prueba en
HA real quedan a su cargo.

## Alcance

- Comparación optativa de la selección habitual y A/B/C/D, con K por dispositivo
  e herencia de los valores del add-on: desactivado y K=4 por defecto.
- Selección y comparación en un trabajo del worker, reutilización de variables,
  unidades de validación y ajustes compatibles, e invalidación por especie.
  Las consultas del mapa no lanzan estas preparaciones.
- Iₖ de comparación sobre observaciones comunes, destacados para los máximos
  elegibles, y acumulados compactos para consultas de fechas históricas.
- Mantenimiento de observaciones con una lectura de setales por render y
  editores bajo demanda, conservación de filtros/borradores y cierre en móvil.
- Conversión de vídeos H.264 con matriz de color inválida, errores de guardado
  asíncrono visibles y cierre de la ventana de progreso sin cancelar el trabajo.

No se migran las bases JSON ni se publica un nuevo artefacto de modelos.
Los estudios cerrados no se repitieron. Los archivos privados de observaciones,
las fuentes, los cachés y las evidencias temporales quedan fuera del commit.
El worker local ya contiene el código compatible; esta publicación es de HA.

## Verificación

- HA local y worker se reconstruyeron/recrearon antes de la aceptación del
  usuario. Verificación de código instalado contra el worktree: 251 archivos
  de HA y 150 del worker coinciden; ninguna diferencia ni ruta sin resolver.
- Coordinadores, configuración e identidad del worker conservados. Se mantiene
  el presupuesto autorizado de cuatro CPU y 8 GiB.
- Última selección/comparación local: `worker_job_WW5hw8Pr9iGqKNiM`, estado
  `complete`, 53,926 s registrados; control `ready` y revisión deseada=activa.
  Procedimiento `02c86d9fa9133c91f8424effeced1e4d3bb1d9f2e20bfe16bfbf02f3e347be0d`.
- Artefacto persistido: 218.148 bytes, SHA-256
  `f8b767c8b6ae3e56172162f4adea045c373bc058c2acaa6b6526eca94cc6063c`,
  igual al recibo de publicación. Validadores de evidencia/comparación correctos;
  contiene K=4 y acumulados históricos para aereus y caesarea. Consultar una
  fecha anterior devuelve sus notas sin reconstruir la evaluación.
- Prueba de navegador contra HA local correcta: editor bajo demanda y vista
  previa GIS/DEM, sin guardar observaciones.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: exit 0;
  2.105 pruebas en 102,224 s, 55 omitidas según disponibilidad del entorno,
  sin fallos. Sintaxis, metadatos, empaquetado y fixtures correctos.
- Después del smoke sólo cambian versión, cache-busters, changelog y
  documentación; metadatos/cache-busters comprobados en 0.2.334, diff sin errores.

## Publicación GHCR

Una única ejecución de `scripts/build-push-ha-image.sh`, terminada con exit 0.
Los tags `ghcr.io/cginebrosa/rainmapperha:0.2.334` y `latest` se comprobaron
remotamente mediante `docker buildx imagetools inspect` y comparten digest:

`sha256:c3f5047c5d6a3372339b954ed1c95048c511179abc6628b84c7ebe42e71e6ff1`

Ambos contienen manifests `linux/amd64` y `linux/arm64`, además de attestations.
El script ejecutó la retención local de imágenes y caché de construcción acordada;
no se borraron fuentes, observaciones ni volúmenes operativos.

Recibos privados: `tmp/jobs/release-ha-0.2.334-20261010/` (`smoke.log`,
`build-push.log`, `local-parity.json`, `operational-check.json`,
`ghcr-verification.json`). Código, pruebas, metadatos y documentación se cierran
en un único commit de release después de comprobar GHCR.

Pendiente: instalación y aceptación en HA real por el usuario. Para preparar allí
la comparación se utiliza Selección y comparación; no se transportan los datos
privados de la prueba local dentro de la imagen.
