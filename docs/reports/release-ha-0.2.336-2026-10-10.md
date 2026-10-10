# Release HA 0.2.336 — 10/10/2026

El usuario autorizó publicar después de ejecutar y aceptar el precálculo local
completo en 2m47s y probar Selección y comparación con K 4, 3 y 2. La instalación
y medición en HA real quedan a su cargo.

## Alcance

- Reutilizar ventanas meteorológicas idénticas y entradas comunes entre
  estimadores en el precálculo, conservando contratos, predicciones y cobertura.
- Reducir serialización, copias y lecturas repetidas al construir y validar el
  artefacto, manteniendo las comprobaciones completas de integridad.
- Preparar las comparaciones pendientes para la K predeterminada del add-on
  y las K guardadas por dispositivos activos. Mostrar K configuradas,
  preparadas y pendientes. Los clics del mapa no inician trabajos.
- Reutilizar evaluaciones históricas compatibles y mantener el contrato escalar
  anterior durante la actualización de HA. El worker local ya tiene el código
  compatible y conserva sus coordinadores; esta publicación es de HA.

## Validación local aceptada

HA local y worker reconstruidos y recreados antes de las pruebas del usuario.
Paridad revalidada antes de publicar: los 11 archivos relevantes de HA y ocho
del worker coinciden con las huellas de la candidata aceptada y el worktree.

Trabajo local `worker_job_n_bieLDCRx9v`, completo y activado en ambos extremos:

- 167 s totales: 5 s de cola y 162 s de ejecución.
- Cálculo 150,626 s, publicación en HA local 4,009 s y activación worker 4,718 s.
- 10 especies, 65 áreas distintas, 141 pares especie/área y siete días,
  del 10 al 16/10/2026: 987 celdas exactas, sin ausencias ni celdas extra.
- 896 miembros operativos; 1.134 consultas mediante 228 respuestas distintas.
- Validación completa correcta, recibo de revisión 77 y SHA-256 idéntico
  en HA y worker: `0b4f27f447f6b64a04873f9488ecc7860048fa38bac9e8ef0b8704def4b555ee`.

El artefacto anterior de HA real tenía los mismos recuentos. La preparación
multiversión acumulada pasa de 432,031 s a 68,251 s. Los modelos instalados y el
coordinador difieren: esta comparación no acredita aún el tiempo total en RPi4
ni el objetivo exacto de dos minutos. Las pruebas aisladas previas sí verifican
igualdad de respuestas con las mismas entradas y semilla de proceso.

## Verificación de release

- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: exit 0; 2.128 pruebas
  en 99,432 s, 55 omitidas por disponibilidad del entorno, sin fallos.
  Sintaxis, empaquetado y fixtures correctos.
- Después del smoke sólo cambian versión, seis cache-busters, changelog y
  documentación. Tres versiones alineadas en 0.2.336 y `git diff --check`
  correcto. Las fuentes ejecutables no cambian durante el build.
- Observaciones privadas conservadas por huella y excluidas del commit.
  No se relanzan entrenamientos, selección/comparación ni precálculos.

## Publicación

Una ejecución de `scripts/build-push-ha-image.sh`, terminada con exit 0.
`docker buildx imagetools inspect` confirma que los tags
`ghcr.io/cginebrosa/rainmapperha:0.2.336` y `latest` comparten digest:

`sha256:8af3d7f701b785ea1b3e7b48a42d71c984365e79d94eb61104cca966fc94ce4b`

Ambos contienen `linux/amd64` y `linux/arm64`, además de attestations. El script
aplica la retención local acordada de imágenes y caché reconstruible; no borra
fuentes ni volúmenes operativos. Código, pruebas, metadatos y documentación
se incluyen en un único commit posterior a verificar GHCR.

Recibos privados: `tmp/jobs/release-ha-0.2.336/` y auditoría operacional
`tmp/jobs/precompute-performance-20261010/local-complete-audit.json`.

Pendiente: instalar y probar HA real por el usuario.
