# Release HA 0.2.330 — 28/09/2026

Estado al cierre del 28/09: **instalada en HA real, geografía activada**.
El usuario confirma entrenamiento y precálculo reales terminados. No se ha
reauditado ese último ciclo; las cifras detalladas más abajo son del ciclo local.
El usuario autorizó la publicación con «pues publica» tras su aceptación local.

La revisión que detectó diferencias en microáreas/reconstrucción ya está
corregida y validada de forma dirigida. Ambas imágenes locales se reconstruyeron
y recrearon en reposo. El nuevo ciclo operativo del usuario terminó y fue
auditado el 28/09/2026 y aceptado para publicar.

## Publicación verificada

- `build-push-ha-image.sh` terminó con código 0; una sola ejecución.
- Tags `ghcr.io/cginebrosa/rainmapperha:0.2.330` y `latest`, mismo digest:
  `sha256:e932c63ad4d207c64f8e2a634264a2ca5efe96ac782a73ba96a2f7b57e98b8fb`.
- Manifiesto `linux/amd64`: `sha256:029925eaa2ffca14d58fc0f5892c274dded1eb30f84078b2a3e4b09144c4f993`.
- Manifiesto `linux/arm64`: `sha256:e61bc6ecc00283cd2a1a14da239d56dc1f050113be3c040136f30f0d665be7c1`.
- Comprobados ambos tags mediante `docker buildx imagetools inspect`.
- Log: `docker-data/territorial-validation/release-0.2.330-build-push.log`.
- La release excluye los archivos personales de observaciones del commit.

## Contenido

- Política territorial compartida por campo para recuperación, microáreas, reconstrucción y mapa.
- Índice MVC50 exacto y acotado, con alternativas por campo y conflictos explícitos.
- Fallos aislados de capas, sin perder las otras fuentes disponibles.
- Comprobar predicción consulta todas las especies y enmarca la observada.

La preparación del código y las pruebas dirigidas están descritas en
[la política territorial](../mushrooms/territorial-source-policy-es.md).

## Copia inicial del índice a HA real (estado anterior a activación)

Autorización del usuario: «puedes subir el archivo MVC50 nuevo a HA real».
Montaje verificado: `//Carlos@100.111.77.48/media` → `/Volumes/media-1`.

Destino dentro de media:
`rainmapper/geography/mushroom-map-GIS/mvc50/prepared/mvc50-2019-11-v1.sqlite`.

- Tamaño: 479.780.864 bytes.
- SHA-256 local y destino:
  `7fd80b927641e1a335b72ca50c40a8ca1187f337ea53d6688fb3419bd96c7eb5`.
- Copia temporal exclusiva, verificación por lectura del destino desde el Mac y
  renombrado tras verificar. No se han sobrescrito originales.
- `CURRENT.json` idéntico antes/después: generación `local-20260914`, huella
  `sha256:8ab40e26cddf9567b878611f11c39d079579eb455105839a40ac67610e3f1336`.
- En ese momento todavía no se había registrado ni activado MVC50 en HA real;
  la activación posterior se documenta más abajo.
- Recibo y comprobantes locales: `docker-data/territorial-validation/ha-upload.json`,
  `ha-CURRENT-before-upload.json`, `package/mvc50-receipt.json`.

## Validación local previa a publicación

- Smoke `coherent-release-smoke.log`: 1.854 pruebas, 55 omitidas; correcto.
- 87 pruebas dirigidas; pruebas de caché impiden volver a descargar assets
  ya presentes y confirman cero bytes en una repetición.
- Dataset local activado: 14 referencias, 1.997 bytes de configuración y
  2.992 bytes de listado. Los 13 assets ya estaban en la caché real del worker.
- Imágenes reconstruidas, recreadas en reposo y paridad 17 archivos HA/12 worker.
  Configuraciones de coordinadores idénticas por SHA antes/después.
- Prueba sin mocks en ambas imágenes: Tordera, Riudarenes y Olvan coinciden entre
  mapa, recuperación y reconstrucción; recuperación de microárea verificada.
- Evidencia en `docker-data/territorial-validation/coherent-*`,
  `coherence-tests.log`, `territorial-dataset-plan.json` y `parity.json`.

## Activación real completada después de instalar

- Registro `local-mvc50-20260928`, huella
  `sha256:e4252f943945412ae4cfc38f81d685778fbdbadb2351f9523620cf9e262ddbea`;
  fuentes `map-sources-local-mvc50-20260928.json`.
- Puntero `/media/rainmapper/geography/CURRENT.json`, junto a `generations/`.
- Dataset científico activado: 14 referencias, huella
  `sha256:64c6115afbc657246dea6b1aa738e1d4eaf9f7ba42a584ac5a606f9f11550649`;
  configuración 1.997 bytes y listado 2.992 bytes. Cero bytes GIS copiados o
  hasheados durante esta activación; copia del índice ya verificada antes.
- Recibos releídos al cierre: `ha-register-mvc50.json` y
  `ha-territorial-activation.json` en `docker-data/territorial-validation/`.
- Originales conservados. Confirmación final del usuario: instalada y
  entrenamiento/precálculo terminados. No pendiente de nueva instalación.

## Circuito operativo local auditado tras finalizar el usuario

Evidencia: `docker-data/territorial-validation/operational-cycle-audit.json`.
Fuentes: registro de trabajos local, reconstrucción GIS promovida, registro de
versiones, manifiesto del lote y SQLite/recibo de precálculo activo.

| Etapa | Trabajo | Duración ejecutada | Resultado |
|---|---|---|---|
| Reconstrucción | `worker_job_W4ZMDhdaNftGjshc` | 1 min 6 s | Verificada y promovida |
| Entrenamiento base | `worker_job_1BuYMPMKMPZAlXGI` | 24 s | 10 especies, promovido |
| Multiversión | `worker_job_E8NUWbdgmgqzl6ke` | 10 min 26 s | 792/792 ajustes, cero fallos |
| Precálculo | `worker_job_NgApKNHyeyjB` | 10 min 47 s | Publicado; worker confirma activo |

- Dataset de 14 referencias con huella `64c6115afbc657246dea6b1aa738e1d4eaf9f7ba42a584ac5a606f9f11550649`, igual al preparado.
- Las 517 reconstrucciones incluyen `territorial_sources_v1`; 465 completas y
  52 con huecos. Estados de capa: 41 sin árboles registrados en MFE25, 11 fuera
  de cobertura MFE25; 9 fuera de MVC50/Cobertes/geología. DEM disponible en 517.
  No aparecen errores de apertura/consulta. Son estados reportados por las capas,
  no una validación independiente de que el terreno esté correctamente cartografiado.
- Tordera `obs_gbif_3113517775`: sustrato silíceo desde MVC50, bosque mediterráneo
  de quercíneas desde MVC50, pino piñonero/alcornoque desde MFE25.
- Lote `operational_20260928T005344Z`: los 792 archivos de modelos existen y las
  cinco versiones instaladas coinciden con las del precálculo activo.
- Precálculo 28/09–04/10: 987 coberturas y 987 predicciones base, 896 miembros,
  1.134 respuestas. 10 especies, 65 áreas distintas (141 pares especie/área).
  SQLite `quick_check=ok`, sin violaciones de claves; recibo activo coincide con
  el del trabajo. Artefacto 46.391.296 bytes.
- Limpieza de los cuatro trabajos completa, worker en reposo y dataset válido.
- Paridad actual repetida: 17 archivos HA y 12 worker iguales al worktree.

No se ha vuelto a entrenar ni precalcular para auditar. La imagen HA se ha
publicado después de esta auditoría. La activación real posterior está documentada arriba.
