# Release HA 0.2.320 — 22/09/2026

Estado: publicada en GHCR tras validar el circuito local completo. Instalación
en HA real pendiente del usuario. Código y documentación se cierran juntos en
el commit `Release Home Assistant 0.2.320`; consultar Git para su hash.

## Alcance y aceptación

Modo histórico del mapa con permiso independiente, desactivado por defecto.
Calendario propio claro, DD/MM/AAAA, meses/años directos y acceso por teclado.
Los modelos actuales calculan para la fecha elegida con meteorología hasta D−1.
La reconstrucción meteorológica usa el ejecutor de predicción, con fallback local,
progreso y consultas acotadas al encuadre y margen. Reutiliza cobertura y obtiene
detalles de estación bajo demanda. No escribe GeoJSON temporales en disco.

El usuario acepta el resultado local («funciona mucho mejor»), pide publicar HA
y confirma después que terminaron el entrenamiento y precálculo local. No se reutiliza la
excepción de validación exclusiva de 0.2.319. Diseño y pruebas funcionales:
[informe del modo histórico](historical-map-local-2026-09-22.md).

## Candidata efectiva

Ambas imágenes se construyeron desde el mismo código candidato, incluidos bump
HA 0.2.320, cache-busters y worker local 1.1.6. Se recrearon los contenedores
existentes conservando volúmenes y asociaciones. Ambos carriles estaban idle
inmediatamente antes de recrear el worker.

| Comprobación | HA local | Worker |
| --- | --- | --- |
| Imagen | `sha256:ee142a887d10b26ca9a588704ddf177fa27539004faeec0e5cff14a5b3146095` | `sha256:ece494abb1a4669e51ff1bf68c6c5d8978c611a9e0bc19a961679df0be0856a8` |
| Metadatos | etiqueta 0.2.320; entorno `local-ha-ui` | etiqueta y `/health` 1.1.6 |
| Arranque UTC | 20:18:43 | 20:19:53 |
| Archivos comprobados | 220, sin diferencias | 125, sin diferencias |
| SHA del manifiesto de archivos | `c87ad39e5bba0ae1a0b772bca68fa3dd47f7451502eb594647ea4b3fb64e5b6e` | `088506bf4731f2f0308d52dcbe69c4028520a635a5ce624e6e4f676b12d3419b` |

HA local responde HTTP 200. Coordinadores persistidos y tokens comparados por
SHA antes/después, sin cambios. Política/suspensiones locales y observaciones
privadas conservadas. Sin SSH, cambio de destino ni trabajos lanzados por Codex.
Evidencia operativa local en `tmp/release-0.2.320/{before,after}.json` y
`tmp/historical-map-20260922/parity.json`; no se incluyen datos privados en Git.

## Pruebas

Smoke final: **1.734 pruebas, 52 omitidas, OK**, 80,957 s. Incluye sintaxis,
versiones, cache-busters, fixtures y suite Python. Primera pasada falló en dos
pruebas con expectativas fijas de worker 1.1.5; se actualizaron a 1.1.6 y el
smoke se repitió correctamente. No se cambió código funcional después.

Logs locales:

- `/private/tmp/rainmapper-0.2.320-smoke-final.log`
- `/private/tmp/rainmapper-0.2.320-build-ha-local.log`
- `/private/tmp/rainmapper-0.2.320-build-worker-local.log`

## Circuito operativo

Tras el aviso de candidata lista, el usuario inició la reconstrucción local
`worker_job_xlB0PxODkcHOogIr` a las 20:22:35 UTC, asignada al worker existente.

| Etapa | Trabajo | Final UTC | Resultado persistido |
| --- | --- | --- | --- |
| Reconstrucción | `worker_job_xlB0PxODkcHOogIr` | 20:24:34 | Verificado y promovido |
| Entrenamiento base | `worker_job_nS7GPTKDbODxZxub` | 20:25:08 | Verificado, diez especies y promovido |
| Multiversión | `worker_job_I58iOv160Z309ez5` | 20:36:04 | Verificado, 792/792 ajustes, cero fallos |
| Precálculo | `worker_job_7Xbqi9U1m2X2` | 20:49:04 | Revisión 74 recibida y activa |

Los tres trabajos constan completos, encadenados y con limpieza terminal completa
en `docker-data/mushroom-data/mushroom_worker_jobs.json`. El registro instala las
cinco versiones del lote `operational_20260922T202508Z`, con puerta de promoción
`passed`. Sus revisiones coinciden con `results/models/current-input-revisions.json`.
La referencia efectiva se comprueba en `installed_generation_id` del registro;
el campo `active` del manifiesto original del lote no se usa para deducirla.
Política/suspensiones y observaciones privadas permanecen intactas por SHA.
Auditoría reproducible y resumen en `tmp/release-0.2.320/audit-training.py` y
`training-audit.json`. Son comprobaciones de metadatos, no nuevos entrenamientos.

El usuario lanzó el precálculo a las 20:40:59 UTC. Su recibo coincide exactamente
con `results/predictor-precompute/active-receipt.json`: revisión **74**, archivo
de **48.414.720 bytes**, SHA256
`d16246baaf503c7fc1732a0a719c015e7f4003680db537477386802c057a2dcc`, comprobado
por lectura secuencial del SQLite persistido. Identidad de artefacto
`sha256:7899167a48d3c990400af1cbe02e0c9e116678933aebeb37385ce626a46f8802`.
Metadatos `publication_state=complete`, identidad igual a `desired.json`, cinco
generaciones coincidentes con el entrenamiento nuevo y cobertura 22–28/09/2026.
Recuentos reales iguales a los sellados: 847 coberturas/predicciones base,
756 miembros operativos, 994 respuestas, 208 payloads/coberturas compartidas,
diez contextos de especie y un diagnóstico. Activación worker `active`, limpieza
terminal `complete`. Auditoría: `tmp/release-0.2.320/audit-precompute.py` y
`precompute-audit.json`. No se regeneraron artefactos para comprobarlos.

Antes de publicar se revalidaron los 28 archivos candidatos, las imágenes
efectivas de ambos contenedores y las huellas de coordinadores/tokens y datos
protegidos: sin cambios. Worker 1.1.6 idle en ambos carriles. No se repitió el
smoke ni se reiniciaron contenedores: sólo cambió documentación desde la validación.

## Publicación

`build-push-ha-image.sh` terminó con código 0; una sola instancia supervisada.
GHCR `0.2.320` y `latest` comprobados mediante `docker buildx imagetools inspect`:

- Índice común: `sha256:6200c13ef2a09dc096dd821e78efecd791cad94af4f927658b053ea0a64132c5`.
- AMD64: `sha256:cccaf29ccef5c71c7b9f7c8808c6d43d1c0b7c7447f6866ae60be9366234db28`.
- ARM64: `sha256:bb23d7c7f8b2bf9c9cd9f6accf590801b25a2a7ca563bec3b035aa2d9516b457`.
- Attestations auxiliares presentes. Log `/private/tmp/rainmapper-0.2.320-publish.log`.

El script aplicó su política habitual de caché local y registró 7,205 GB
reclamados; sin limpieza remota de GHCR ni retirada de volúmenes/datos.
El commit incluye el cierre documental anterior y excluye expresamente
`mushroom-data/mushroom_observations.json`, privado y preexistente.
La instalación en HA real corresponde al usuario; el permiso histórico debe
activarse allí desde Usuarios, pues por defecto permanece deshabilitado.
