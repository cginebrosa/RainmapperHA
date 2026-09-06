# Regresión de recursos del entrenamiento y precálculo — 2026-09-06

## Resultado

La regresión tenía dos recorridos independientes que sobrevivieron a la
compactación anterior del SQLite:

1. HA expandía y serializaba 504 resoluciones completas antes de encolar el
   precálculo. El JSON resultante pesaba 49.913.415 bytes y el worker lo
   rechazaba frente al límite correcto de 16 MiB.
2. El entrenamiento trataba catálogos y hold-out de auditoría como ficheros
   operativos: los copiaba al área de envío, HA los descomprimía y escribía, y
   después copiaba de nuevo todo el lote para instalarlo.

La compactación anterior sí funcionaba en su ámbito: el SQLite final elimina
la cadena completa después de resolver aplicabilidad. La regresión estaba antes
de construir ese SQLite y en el transporte del lote entrenado.

## Evidencia medida

Generación real `operational_20260906T001649Z`:

- 636 modelos: 86.212.574 bytes.
- catálogo operativo: 66.897.313 bytes en crudo;
- catálogo de auditoría: 18.743.962 bytes en crudo;
- lote instalado observado por HA: 265.626.390 bytes;
- precálculo fallido `worker_job_SPz3W_MwjOdU`: 8 especies, 72 áreas,
  504 celdas especie--área--día, 420 ganadores y un JSON de selecciones de
  49.913.415 bytes.

Con el nuevo contrato, el mapa de las mismas 72 áreas ocupa 1.117 bytes. El
índice de ganadores generado desde el catálogo real ocupa 4.329 bytes y vuelve
a contar exactamente 420 ganadores sin abrir el catálogo completo en HA.

La escritura gzip implementada sobre los artefactos reales produce:

- catálogo operativo: 2.264.625 bytes;
- catálogo de auditoría: 965.421 bytes.

El hold-out y el informe operativo también quedan comprimidos desde el worker;
HA verifica la huella de esos ficheros comprimidos y no reconstruye su contenido
de auditoría durante la instalación.

## Contrato corregido

- HA planifica mediante el índice pequeño de estados ganador/abstención y
  encola únicamente las áreas cubiertas.
- El worker sincroniza primero el runtime verificado y allí resuelve la cadena
  sellada, incluidos los vetos de aplicabilidad. Los trabajos antiguos ya
  encolados conservan su ruta de compatibilidad, pero los nuevos no publican ni
  descargan `operational_selections_ref`.
- El runtime incluye modelos, catálogo operativo comprimido e identidad de
  entrenamiento. Excluye catálogo de auditoría, informe y hold-out.
- Los artefactos de auditoría se almacenan comprimidos y solo se abrirán cuando
  una auditoría explícita los solicite.
- El lote producido se mueve al área de envío y el lote recibido se mueve al
  almacén de modelos. Ambos pasos exigen el mismo sistema de ficheros; no crean
  copias de respaldo, árboles de rollback ni directorios `.install`.

`MOD_0001` no cambia: esta corrección solo modifica planificación, transporte y
almacenamiento. No altera probabilidad, ranking, aplicabilidad, recomendación ni
los diagnósticos ecológicos.

## Validación

- 502 pruebas dirigidas superadas durante la implementación.
- Prueba funcional con el catálogo real: 504 resoluciones, 420 ganadores,
  contrato nuevo de 1.117 bytes frente a 49.913.415 bytes del anterior.
- Pruebas explícitas de que el worker no descarga selecciones para el contrato
  nuevo, HA no abre el catálogo completo cuando existe el índice, los runtime no
  contienen auditoría y los dos movimientos conservan el inodo sin dejar
  `.install` ni copias.
- Smoke completo superado sobre el código definitivo: 1.292 pruebas, sintaxis
  Python, JavaScript y shell, fixtures funcionales, empaquetado, versiones
  HA 0.2.294/worker 1.0.40 y `git diff --check`.
- Worker 1.0.40 reconstruido y verificado `healthy` con la misma identidad,
  volumen, cachés y URL `http://100.111.77.48:8100`; el registro de HA recibió
  el heartbeat de la versión nueva.

## Despliegue

HA 0.2.294 y worker 1.0.40 deben instalarse juntos para usar el contrato nuevo.
No requieren repetir el entrenamiento actual para desbloquear el precálculo:
la generación instalada conserva el catálogo antiguo y el worker nuevo lo puede
leer desde el runtime. El siguiente entrenamiento ya producirá los artefactos
comprimidos y el índice pequeño.

La imagen multi-arquitectura de HA 0.2.294 quedó publicada y comprobada en
GHCR. Los tags `0.2.294` y `latest` resuelven al mismo índice
`sha256:79610e563f9124cfc55ae28c57402d9cbd4d4ea3d2012a9b0427a0fb5c14cd9b`
y contienen manifests `linux/amd64` y `linux/arm64`. La instalación y la prueba
en HA real siguen pendientes de autorización y ejecución.
