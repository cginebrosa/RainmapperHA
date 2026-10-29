# AEMET: diarios oficiales recientes — validación local, 29/10/2026

El descargador revisa en cada runner los últimos 30 días anteriores a hoy mediante
OpenData, aunque ya existan o tengan cobertura horaria completa. Los campos diarios
oficiales sustituyen a los provisionales, incluidas correcciones a la baja. Los
campos ausentes conservan el valor previo. La precipitación oficial mantiene su
fecha y periodo publicado 07–07 UTC. [Contrato completo](../../rainmapper-app/DOCS.md#provisionales-horarios-y-diarios-oficiales).

Se reutiliza `weather_official_backfill.fetch_aemet_climatology`, que ya existía:
el código anterior sí tenía backfill oficial manual y mantenimiento histórico
batch, pero no este refresco de todos los días recientes dentro del descargador.
La cola histórica conserva su alcance; este cambio no conecta esa cola al runner
web. No se usa la web/XML de AEMET ni una espera de seis horas.

## Entorno y alcance

- Rama aislada `fix/aemet-recovery-20261029`, base `7bbdecb9d3ede8e046f717594e34eac070962f9c` (0.2.338).
- Imagen local reconstruida; huellas de seis archivos efectivos del contenedor
  coinciden con el worktree. La imagen de referencia coincide con la base.
- Copias independientes de los datos de HA, Docker con 2 CPU y 2 GiB. Clave desde
  el entorno; sólo AEMET habilitado y archivo particionado activo.
- Ejecución mediante `web_server.run_action('update', ..., only_source='AEMET')`,
  el flujo compartido por web/scheduler, incluidos los cierres de archivo antes
  y después de la descarga. Sin entrenamiento ni precálculo.
- AEMET y ambos cierres terminan con código 0. El runner global termina con 2
  porque la copia meteorológica no contiene modelos del Predictor y su publicación
  queda diferida (`FileNotFoundError`). No valida las demás fuentes ni publicación
  de mapas. No se ha publicado ni instalado una release en HA real.

## Contraste con una lectura independiente de OpenData

Periodo solicitado: 29/09–28/10/2026. La API entrega 22.291 filas de 844 estaciones,
con fechas hasta el 25/10. De ellas, 22.197 estación/día tienen algún campo útil.

| Campo | Valores comprobados en cada almacén | Diferencias |
|---|---:|---:|
| Precipitación | 21.547 | 0 |
| Temperatura máxima | 21.891 | 0 |
| Temperatura mínima | 21.892 | 0 |
| Humedad máxima | 21.658 | 0 |
| Humedad mínima | 21.659 | 0 |

Los 108.647 valores coinciden tanto en CSV como en Parquet. Se añaden 959 registros
oficiales estación/día ausentes. El CSV pasa de 147.141 a 148.122 filas: esos 959
más 22 aportados por la actualización horaria. Ninguna clave previa desaparece ni
se pierde un metadato existente. No se inventan coordenadas para estaciones que
el catálogo horario desconoce.

Las 45 particiones ajenas a AEMET/2026 conservan sus hashes. En AEMET/2026, las
222.871 filas anteriores al 29/09 conservan su contenido; también las 121.313 filas
del CSV anteriores a esa fecha. Los 63 ficheros originales comprobados permanecen
idénticos. En la repetición, el lote ya aplicado reutiliza la generación Parquet
y no inserta filas ni reescribe particiones.

El 26, 27 y 28/10 siguen provisionales: la API todavía no publica sus diarios.
La corrección repara valores diarios; no recupera muestras horarias que AEMET ya
no ofrece. Campos diarios vacíos o `Acum` tampoco se convierten en lluvia cero.

## Tiempos y recursos medidos

| Ejecución | Runner completo | Descargador AEMET | Refresco diario | Pico RSS de proceso hijo |
|---|---:|---:|---:|---:|
| Referencia 0.2.338, primera | 19,45 s | 5,93 s | — | 435,65 MiB |
| Referencia 0.2.338, repetición | 13,98 s | 5,72 s | — | 435,25 MiB |
| Candidata, primera | 30,74 s | 12,34 s | 4,60 s | 546,50 MiB |
| Candidata, repetición | 20,49 s | 11,51 s | 3,88 s | 557,46 MiB |

En la repetición, el coste añadido observado es 6,51 s y unos 122 MiB de pico RSS.
Son mediciones puntuales en Docker local, no tiempos de Raspberry Pi ni RSS total
del contenedor. El primer cierre tiene más trabajo porque sustituye los diarios.
Cada ejecución consulta dos bloques de hasta 15 días: cuatro peticiones HTTP,
10.879.762 bytes recibidos. El estado oficial ocupa 2.946.691 bytes, con metadatos
deduplicados por estación. La respuesta más grande medida ocupa 6.058.043 bytes,
por debajo del límite de 8 MiB por respuesta.

## Verificaciones y limpieza

Smoke final: 2.158 tests en 128,826 s, 55 omitidos, sin fallos; sintaxis, versiones
y comprobación del diff correctas. Las pruebas dirigidas incluyen correcciones a
la baja, campos ausentes, caché ante fallos, persistencia CSV/Parquet, límite de
payload y estaciones cuya altitud llega como texto. Esta última condición produjo
un fallo en la primera integración; se corrigió y se repitió la prueba desde una
copia original. Los resultados anteriores corresponden a la candidata final.

Se conservan sólo código, tests, documentación y [evidencia compacta](aemet-opendata-daily-refresh-local-2026-10-29.json).
Las copias de datos, respuestas completas de la API, scripts, logs, cachés Python
y los dos contenedores temporales se han eliminado. Comprobación final: cero
contenedores de prueba, carpeta temporal ausente y nueve directorios de caché
Python retirados. Los 63 ficheros originales vuelven a coincidir tras la limpieza.
