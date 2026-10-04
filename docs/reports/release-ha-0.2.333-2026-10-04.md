# Release HA 0.2.333 · 04/10/2026

Publicada por petición expresa del usuario («publicamos version de HA»), después
de entregar la validación local de la medición por recorridos y su convivencia
con las consultas. Pendiente instalación y prueba del usuario en HA real.

## Cambios publicados

- Regla después de reorientar al norte y antes de Créditos, sin permiso específico.
- Recorridos A→B→C… en 2D y 3D, con línea provisional desde el último punto,
  vértices arrastrables, Deshacer y Nueva. Pulsar el último punto termina;
  volver a pulsarlo permite continuar.
- Distancia horizontal y aproximada sobre el relieve, desnivel neto y ascenso/
  descenso acumulados. Muestreo Mapzen/Terrarium acotado en navegador, independiente
  de la exageración visual; conserva la distancia horizontal si falta elevación.
- Panel compacto ES/CA/EN, con ayuda desplegable y acciones en una fila en móvil.
- Recorrido terminado visible mientras funcionan predicciones, fichas de estaciones
  e información del terreno. Captura los clics sólo al trazar o arrastrar.

[Especificación](../mushrooms/prediction-map-specification-es.md).
No cambia modelos, SMI, meteorología observada ni contratos del worker. No ejecuta
entrenamientos, precálculos ni operaciones sobre el coordinador o el worker.

## Validación y aceptación local

- HA local reconstruida/recreada desde el código candidato antes de la petición
  de publicación. Ocho archivos de ejecución y etiquetas revalidados frente al
  worktree y a la evidencia aceptada: SHA-256 coincidentes.
- Prueba matemática/DEM: recorridos de ida/vuelta, vértices, pendientes, cumbre,
  antimeridiano, límites globales, interpolación bilineal, caché, cancelación y
  elevación ausente correctos; módulo de cálculo sin cambios posteriores.
- Navegador completo correcto sobre el código definitivo: trazado, cierre/
  reanudación, arrastre 3D, consultas con recorrido terminado, cambio de estilo,
  ausencia de permisos específicos y panel móvil. 78 consultas predictivas y
  25 históricas simuladas por la regresión; ningún trabajo operativo real.
- Panel móvil comprobado en 320×568, 360×640 y 390×844, ES/CA/EN, sin desbordamiento.
- Smoke obligatorio: `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`,
  **1.911 pruebas, 55 omitidas; correcto**, con permisos para servidores localhost.
  Incluye pruebas locales previas ajenas al cambio, conservadas fuera del commit.
- Después del smoke sólo se modificaron versiones, cache-busters, changelog y
  documentación. Tres referencias de versión y seis cache-busters alineados;
  sin segundo smoke tras el bump mecánico.

## Publicación y verificación remota

Una sola ejecución de `./scripts/build-push-ha-image.sh`, supervisada hasta salida
0. `docker buildx imagetools inspect` confirma ambos tags y arquitecturas:

| Tag | Digest del índice |
|---|---|
| `ghcr.io/cginebrosa/rainmapperha:0.2.333` | `sha256:3980114db78a60a0d44a720d51773af7f311607567e20f43ad9455fb18630832` |
| `ghcr.io/cginebrosa/rainmapperha:latest` | `sha256:3980114db78a60a0d44a720d51773af7f311607567e20f43ad9455fb18630832` |

- `linux/amd64`: `sha256:38092387a9e6510f169c556acc1be1fbf9c8db69663778fa4359db558d11c653`.
- `linux/arm64`: `sha256:5392ed0fa59daac8473d0a1abf318e247e4046d2ed66a13a3579f423b581c4d0`.

Limpiezas automáticas de Docker mantenidas conforme a la autorización previa del
usuario: retirada de la etiqueta local 0.2.332 y caché Buildx acotada a 8 GiB;
salida de prune: **5,796 GB** recuperados. No es una medición de espacio libre total
del Mac. No se borraron tags remotos, fuentes, archivos privados ni volúmenes.

Evidencia privada en `tmp/release-0.2.333/`: paridad aceptada/actual/runtime, smoke,
build-push, consultas GHCR y huellas de observaciones antes/después. Validación
funcional y capturas: `tmp/measurement-queries-20261004/` y
`tmp/measurement-compact-20261004/`.

Código, pruebas, metadatos y documentación se incluyen en un único commit después
de verificar GHCR. Cambios locales previos ajenos y observaciones privadas quedan
fuera. El usuario instala y prueba en HA real; última instalación confirmada:
0.2.332. No repetir publicación ni lanzar trabajos operativos al continuar.
