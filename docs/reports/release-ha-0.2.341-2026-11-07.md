# Release HA 0.2.341 — 07/11/2026

Publicación autorizada por el usuario tras aceptar el runner local y las pruebas.
Parte de `612f162b2ab22e2ae06ad38375657dde841acc8c` (0.2.340) en `inicial`, con
destino `origin/inicial`. El usuario pidió brevemente esperar antes del cierre;
después autorizó continuarlo para que HA pudiera detectar la nueva versión.

## Contenido

- Protección común de ubicaciones para las cuatro fuentes y los pendientes
  Parquet: conservar la referencia ante saltos superiores a 1 km, registrar
  excepciones sin abortar y retirarlas sólo ante metadata original válida.
- Resumen por fuente y revisión de traslados desde MapLibre, con búsqueda,
  marcas visibles y ubicaciones precisas. Aceptación exclusiva del administrador,
  aplicada en el siguiente runner; cabecera compacta y controles ocultos en móvil.
- AEMET conserva ubicación y otros sensores aunque no haya lluvia horaria;
  completa ubicaciones mediante inventario OpenData y reutiliza el catálogo.
  Los valores omitidos no borran mediciones previas ni fabrican lluvia cero.
- Meteoclimatic conserva precisión y compara coordenadas numéricamente para
  reutilizar metadata. Tipos geográficos coherentes para Parquet, unión segura
  de grupos Wunderground y fechas ausentes como `null` en GeoJSON.

El LLM/MCP queda en `feature/local-llm`; no entra en esta imagen. Worker sin
cambios. Los dos snapshots de observaciones autorizados se incluyen en Git sin
alterarlos; el Dockerfile sigue usando sus defaults de observaciones, no estos
snapshots locales. [Organización del repositorio](../repository-branches.md).

## Validación local

- Smoke completo: **2.194 tests, 55 omitidos, 132,511 s**, exit 0, incluidos los
  checks de sintaxis, fixtures, versiones y whitespace. Después sólo cambian
  metadatos de versión, referencias de caché y documentación.
- Runner completo del usuario: **22:48:34–22:51:25**, **2 min 51 s**, exit 0,
  sin `FutureWarning` ni `DtypeWarning`; cuatro fuentes `OK`, siete GeoJSON.
- AEMET: **12,767 s**, cero consultas necesarias al inventario, catálogo de
  891 fichas completo. Las 17 ubicaciones investigadas coinciden en CSV,
  catálogo Parquet activo y mapa. Roda de Ter sigue protegida en 41,99/2,32.
- Persisten 106 respuestas antiguas de Wunderground y tres estaciones fallidas;
  no se presentan como resueltas por esta release.
- Tras el bump, HA local reconstruido/recreado:
  `sha256:ed414fec20d49dc90f80ba2707ef7a922e7808119d3a6d282ab37be1fafe8a3b`.
  Paridad de **15 archivos efectivos**, configuración/volúmenes conservados,
  interfaz HTTP 200 y prueba de regresión Wunderground correcta dentro de la
  imagen en 0,153 s, sin consultas externas. Mismas versiones comprobadas de
  Pandas, NumPy, PyArrow, Requests y lxml que en la candidata aceptada.
- **564 archivos** de código, pruebas y empaquetado conservan sus hashes durante
  la publicación. No se repitió el runner operativo por el bump mecánico.

[Pruebas, incidencias y límites](weather-coordinates-local-2026-11-04.md).

## Publicación y cierre

Una sola ejecución de `scripts/build-push-ha-image.sh`, terminada con exit 0.
`docker buildx imagetools inspect` verifica que `0.2.341` y `latest` comparten:

`sha256:5097c0c05cb5a330d99065d10ad5efef64b67378e71a3bf7a0b77edf64536898`

| Arquitectura | Manifest |
|---|---|
| `linux/amd64` | `sha256:a4ed3b287b770f26c4b898b21cda517eaa1bfd969edd38495004b67ea88a185d` |
| `linux/arm64` | `sha256:b23b93b65bfe7d97113effed6cb45ba5704afe70948b8d18c5aeb80922941d91` |

El manifest arm64 coincide con el construido y comprobado en HA local. El script
retira sólo la etiqueta local de GHCR 0.2.340 y acota la caché Buildx a 8 GiB;
informa **4,753 GB liberados**. No se eliminan versiones remotas ni datos.
Se conserva un recibo compacto y se elimina el log temporal después de verificar
GHCR. Código, bump, changelog, pruebas, documentación y snapshots autorizados
se incluyen en un único commit de release.

## Confirmación en HA real — 07/11/2026

Después de instalar la versión, el usuario confirmó en esta conversación:
«ya esta instalada y ha funcionado». A petición suya se registra esta evidencia
posterior a la publicación: **0.2.341 instalada y funcionando en HA real según
la prueba del usuario**.

No se ha hecho una inspección remota independiente ni se ha recibido el log
completo de esa ejecución. Los tiempos, recuentos y resultados detallados en
la validación local no se atribuyen a HA real. Esta confirmación tampoco acredita
que se hayan resuelto las limitaciones de datos de Wunderground descritas arriba.
La anotación es documental; no cambia código, imagen ni versión.

[Recibo estructurado](release-ha-0.2.341-2026-11-07.json).
