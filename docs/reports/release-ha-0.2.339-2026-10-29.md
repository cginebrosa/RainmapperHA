# Release Home Assistant 0.2.339 — 29/10/2026

El usuario aceptó la validación local, revisó el procedimiento de publicación y
autorizó ejecutarlo: «adelante». La release incluye exclusivamente el refresco
AEMET y sus pruebas, documentación y metadatos de versión. Se prepara desde
`7bbdecb9` (0.2.338) en `fix/aemet-recovery-20261029`; el trabajo MCP y demás
cambios pendientes del checkout principal quedan fuera.

## Comportamiento

Cada runner AEMET consulta todos los últimos 30 días anteriores a hoy en la API
OpenData, incluidos días completos. Los valores oficiales no vacíos sustituyen
los provisionales horarios, también a la baja, y se conservan ante fallos
posteriores. El cierre habitual actualiza los Parquet y el CSV incremental.
`aemet_daily_refresh_days` admite 7–30 días y vale 30 por defecto. La precipitación
oficial mantiene su fecha y periodo publicado 07–07 UTC. No hay scraping ni
intervalo adicional de seis horas. [Contrato](../../rainmapper-app/DOCS.md#provisionales-horarios-y-diarios-oficiales).

## Validación aceptada y comprobación de la versión

- Runner real web/scheduler sobre copia aislada de HA: 108.647 campos coinciden
  con una consulta independiente de la API, en CSV y Parquet; 959 registros
  oficiales estación/día añadidos, ninguna clave previa perdida y 45 particiones
  ajenas intactas. El 26–28/10 seguía provisional al no devolver la API sus diarios.
- Smoke final: 2.158 pruebas, 55 omitidas. Tras el bump mecánico se comprobaron
  versiones y referencias de los visores, sin repetir el smoke completo.
- Imagen local reconstruida con 0.2.339; seis huellas de código coinciden con la
  candidata aceptada. Las 34 dependencias Python también coinciden; 47 pruebas
  dirigidas pasan dentro de la imagen versionada. No se cambió código funcional.
- Límite de la integración: AEMET y cierres de archivo terminan con código 0;
  el runner global da 2 por publicación del Predictor diferida al faltar modelos
  en la copia meteorológica. No es una prueba de las otras fuentes ni de mapas.
- Repetición local: 20,49 s frente a 13,98 s de la referencia; unos 122 MiB más
  de pico RSS en un proceso hijo. No son medidas de Raspberry Pi.

[Informe funcional y evidencia](aemet-opendata-daily-refresh-local-2026-10-29.md).
No se reconstruye ni se cambia el destino del worker.

## Publicación verificada

Una ejecución de `scripts/build-push-ha-image.sh`, desde el worktree aislado,
supervisada cada 20–30 segundos, termina con código 0. Verificación independiente
posterior mediante `docker buildx imagetools inspect`, con máximo de 40 segundos
por consulta:

| Tag | Digest | Plataformas de ejecución |
|---|---|---|
| `ghcr.io/cginebrosa/rainmapperha:0.2.339` | `sha256:b912bf2408a78fd87a62118e468f83c1a1b944e028116fdfa1b036d6505f6c3f` | `linux/amd64`, `linux/arm64` |
| `ghcr.io/cginebrosa/rainmapperha:latest` | Mismo digest | `linux/amd64`, `linux/arm64` |

La limpieza local automática del script queda habilitada; Buildx informa
6.907 GB reclamados. No se limpió GHCR. Metadatos, código, tests, changelog y
documentación se agrupan en un único commit `Release Home Assistant 0.2.339`
destinado a `origin/inicial`, después de verificar la imagen remota.
[Recibo compacto](release-ha-0.2.339-2026-10-29.json).

## Continuidad e instalación

El checkout principal conserva intactos sus 478 archivos pendientes comprobados;
queda sin sincronizar con la nueva release para no alterar ese trabajo. La rama
de publicación está en `local/worktrees/aemet-recovery`; al retomar desarrollo,
integrar ambas conscientemente, sin publicar el trabajo MCP por accidente.

El usuario instala la actualización y comprueba el primer runner en HA real.
Codex no ha instalado la release ni lanzado trabajos allí. Los temporales de
pruebas, el log y las consultas temporales de publicación se han eliminado,
conservando este informe, el recibo compacto y la huella del log de construcción.
