# Meteoclimatic: coordenadas fijas por estación

Esta función permite corregir temporalmente una ubicación errónea del proveedor
sin cambiar el código ni desactivar la estación. Sólo afecta a los códigos de
Meteoclimatic que el operador incluya expresamente en el archivo.

## Ubicación e instalación

| Uso | Ruta |
| --- | --- |
| Archivo activo en HA | `/share/rainmapper/meteoclimatic-fixed-coordinates.txt` |
| Archivo activo en HA local | `docker-data/meteoclimatic-fixed-coordinates.txt` |
| Plantilla distribuida en el repositorio | `meteoclimatic-fixed-coordinates.example.txt` |

El archivo activo va en la raíz de `/share/rainmapper`, junto a `stations.txt`
y `status.txt`, **no dentro de `Data/` ni en la raíz del repositorio**.
Git y la construcción de la imagen excluyen el archivo activo. La imagen incluye
únicamente la plantilla, con el ejemplo comentado: no activa excepciones para
otras instalaciones.

Al arrancar una versión compatible, Rainmapper copia la plantilla sólo si falta
el archivo activo. Las actualizaciones no sobrescriben un archivo existente.
Subirlo a una instalación anterior no incorpora por sí solo esta funcionalidad:
también hay que instalar el parche que lo lee.

## Formato y uso

Texto UTF-8, una estación por línea, con código, latitud y longitud en grados
decimales separados por espacios o tabuladores. Ejemplo de excepción activa:

```text
# Coordenadas históricas de Roda de Ter
ESCAT0800000008510E 41.99 2.32
```

Se admiten líneas vacías, espacios iniciales y comentarios al final de la línea.
Cuando el proveedor corrija la ubicación, basta con quitar la línea o poner `#`
delante:

```text
# ESCAT0800000008510E 41.99 2.32
```

La siguiente operación vuelve a leer el archivo; no hace falta reconstruir la
imagen ni reiniciar para editar las excepciones. Sin archivo o sin entradas
activas se mantiene el comportamiento habitual. La estación continúa descargando
sus mediciones: no es una lista de estaciones desactivadas.

Un código activo duplicado, una línea incompleta o coordenadas inválidas causan
un error que identifica archivo y línea; no se ignoran silenciosamente. El límite
es 64 KiB y 512 estaciones. Si se comenta una excepción mientras el proveedor
sigue enviando una ubicación errónea, la protección habitual puede volver a
bloquear el archivado.

## Efecto sobre descargas y pendientes

- En nuevas descargas se sustituyen las coordenadas antes del enriquecimiento
  geográfico, para consultar municipio y altitud en el punto corregido.
- En lotes ya pendientes se aplican al incorporarlos al histórico y al CSV
  incremental. Los archivos pendientes se conservan hasta su confirmación normal.
- Lluvia, temperatura y las demás mediciones no se modifican. No se realiza una
  reparación general del histórico ni se alteran estaciones ajenas a la lista.
- Los metadatos geográficos del pendiente sólo se reutilizan si corresponden a
  las coordenadas fijadas. Puede recuperarse la altitud del catálogo anterior;
  municipio, provincia y comarca sin referencia fiable quedan vacíos hasta el
  enriquecimiento normal, en lugar de conservar una localidad errónea.

No basta con editar `Data/estacions_meteoclimatic.csv`: la siguiente descarga
puede volver a traer el error y el lote que bloqueó el runner ya está persistido.
El paso de archivado recupera ese lote; los CSV de la última descarga y el registro
se actualizan por el circuito normal de la siguiente descarga. La excepción no
reescribe inmediatamente todos esos archivos al subir el TXT.

Si hay una interrupción después de publicar el histórico pero antes de confirmar
el CSV, la recuperación usa las mismas coordenadas que se aplicaron al lote.
Editar el TXT entre ambos pasos no cambia esa recuperación pendiente. Esta
información queda en el manifiesto existente, sin crear un historial adicional.

## Registro y diagnóstico

Cuando se sustituye una ubicación se escribe en el log el código de estación,
las coordenadas recibidas, las usadas y el nombre del archivo. El mensaje se
emite una vez por estación en cada proceso que aplica la corrección, no por
observación; puede aparecer en distintas etapas del runner. No se genera un
archivo de auditoría independiente.

La primera incidencia que motivó la función fue el salto de 889.561 km de
`ESCAT0800000008510E`: Roda de Ter en el catálogo anterior, frente a una latitud
49.99 publicada por el proveedor. El [informe de la incidencia](reports/weather-coordinate-conflict-2026-10-14.md)
conserva las fuentes, huellas y límites del diagnóstico. El estado de validación,
publicación e instalación se mantiene en [active-context.md](active-context.md).
