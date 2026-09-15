# Geografía compartida: estructura portable

Estado del 15/09/2026: lectura directa validada en HA local y worker. Copias colocadas y referencias finales verificadas
en HA real. [Informe](../reports/shared-geography-portable-2026-09-15.json). HA 0.2.304 publicada el 16/09/2026; worker existente 1.1.2 validado.
Instalación por el usuario pendiente. [Release](../reports/ha-release-0.2.304.json).

## Instalación: archivos preparados antes de actualizar

La versión nueva encuentra los archivos directamente. **No hay que ejecutar
comandos, registrar datos, crear enlaces ni reorganizar carpetas al arrancar HA.**
El método anterior de adopción nativa está sustituido por esta estructura de
archivos ordinarios. [Diseño anterior, solo histórico](../reports/shared-geography-before-portable-2026-09-15.md).

```text
/media/rainmapper/geography/
  mushroom-GIS/                            # GIS científico completo y fuentes compartidas
    geography-dataset.json                # contrato científico de 13 archivos
    geography-auxiliary.json               # inventario de los 1.432 archivos conservados
    geography-sources.json                # identidad portable de los archivos
    ...                                   # DEM, geología, SoilGrids, capas y auxiliares
  mushroom-map-GIS/                        # fuentes e índices exclusivos del mapa
    ...                                   # MFE, IGN, OpenLandMap, municipios, cubiertas…
  generations/local-20260914/manifest.json  # contrato lógico del mapa, sin duplicar fuentes
  map-sources-local-20260914.json          # ruta lógica → archivo ordinario compartido
  map-config.json                         # configuración preparada para HA
  CURRENT.json                            # versión de geografía que debe usar el mapa
```

El conjunto contiene **3.581 archivos de datos, 15.622.243.791 bytes** (15,62 GB;
14,55 GiB), más manifiestos pequeños. El mapa conserva sus 3.510 referencias
lógicas y el GIS científico sus 1.432 entradas, con 1.361 referencias compartidas.
No sumar estas referencias como si fueran copias físicas distintas.

Los archivos comunes, como los DEM regionales, geología y teselas SoilGrids
normalizadas, viven en `mushroom-GIS`. El manifiesto del mapa declara su ruta real;
los lectores y el servidor de transporte la resuelven sin enlaces del filesystem.
Las fuentes diferentes y los originales de descarga se conservan: MFE no
sustituye MVC50mil; las teselas normalizadas no sustituyen los originales WCS.

## Cómo los encuentra la aplicación

- GIS y SoilGrids prefieren `geography/mushroom-GIS` si contiene su manifiesto
  preparado. Las rutas configuradas explícitamente mantienen prioridad.
- El mapa respeta primero su configuración explícita o privada. Si no existe,
  lee `geography/map-config.json`. La raíz `.` significa el directorio que contiene
  ese archivo, no un path del Mac.
- El archivo preparado conserva las rutas estándar de datos privados de HA;
  no copia usuarios, fichas, observaciones, modelos ni meteorología del Mac.
- La publicación lee `CURRENT.json`, el manifiesto de la versión y su tabla de
  rutas. No crea directorios, SQLite, recibos nativos ni enlaces en HA.

## Hashes, cambios y transporte

Los SHA se calcularon/verificaron al preparar y copiar los archivos desde el Mac.
Los manifiestos guardan esos SHA, los tamaños y las identidades lógicas que esperan
los índices existentes. La tabla portable registra tamaño y mtime a milisegundos,
para tolerar la precisión de SMB; no depende de inodo, dispositivo o ctime.
Cada fuente accedida se comprueba con stat. Esto no es un nuevo hash de contenido:
una modificación deliberada que conserve tamaño y mtime requiere nueva verificación.

Al cambiar datos se prepara de nuevo el manifiesto de la versión, fuera del clic,
y se entrega junto con los archivos cambiados. No se deben editar datos publicados
silenciosamente ni fabricar SHA a partir de nombres/tamaños. La huella geográfica
actual no cambia por reorganizar físicamente archivos con el mismo contenido.

HA consulta el pequeño puntero de versión; el heartbeat anuncia esa huella al
worker. El worker prepara su caché fuera del clic y solo solicita contenidos que
no tiene. Verifica los hashes mientras descarga. Las consultas online transportan
referencias y el punto solicitado, no la cartografía completa.

En el volumen persistente del worker, `geography/objects/<sha256>` es un almacén
común para mapa y dataset científico. Sus vistas internas usan enlaces duros como
optimización de caché, gestionados por el propio worker. El usuario no tiene que
crearlos. No hay GIS en la imagen ni copias completas por trabajo/coordinador.

## Validación y conservación

- Smoke: 1.600 tests, 48 omitidos, OK.
- Ambos contenedores reconstruidos; código efectivo comprobado: 198 archivos HA
  y 106 worker, sin diferencias respecto a sus fuentes.
- Cuatro puntos: geografía y contextos idénticos antes/después de cambiar rutas.
- Seis consultas autenticadas: resultados local/worker idénticos, concurrencia,
  cancelación, usuario básico y rechazo sin autorización comprobados.
- Primer acceso en contenedor sin red, filesystem y media en solo lectura:
  autodetección de configuración, cálculo local listo y contrato GIS de 13 archivos.
- Worker tras recreación: 3.510 archivos reutilizados, 0 bytes transferidos,
  0 bytes rehasheados y 0 bytes de manifiestos descargados.
- El circuito científico completo anterior conserva sus contratos y artefactos;
  no se ha vuelto a entrenar para un cambio de rutas. El inventario de 13 archivos
  es idéntico. Evidencia anterior en el informe de consolidación.

**Conservar en HA real**, hasta que el usuario pruebe la nueva versión y decida
retirarlos, los tres directorios originales:

1. `/media/rainmapper/mushroom-GIS`
2. `/media/rainmapper/prediction-map/generations/local-20260914/mushroom-GIS`
3. `/media/rainmapper/prediction-map/generations/local-20260914/mushroom-map-GIS`

La colocación final reorganiza exclusivamente las copias nuevas que se crearon
bajo `geography/imports`. No copia otra vez los GiB ni modifica esos originales.
La versión antigua de HA continúa usando sus rutas anteriores hasta actualizarla.

GEODE/MFE nacional pendiente conserva su alcance en el TODO. Esta consolidación
no amplía cobertura ni cambia reglas ecológicas.

## Por qué todavía aparecen carpetas repetidas en media

Revisión de solo lectura del 15/09/2026, solicitada tras ver las carpetas en Finder:
[inventario y evidencia](../reports/shared-geography-duplicates-2026-09-15.json).

**Sí quedan copias físicas antiguas fuera de `geography`.** Se conservaron por
la instrucción de copiar primero y retirar los originales después de probar la
nueva versión. Consolidar la estructura nueva no eliminó esos originales.
Sus inventarios suman 21.358.531.147 bytes (21,36 GB); se comprobó que siguen
presentes y coinciden los tamaños de los archivos mayores de nueve familias.
No se ha repetido el hash completo ni un inventario exhaustivo de los originales.
La retirada posterior se limita a los tres directorios enumerados arriba, una vez
comprobado que la versión instalada y sus configuraciones usan las rutas nuevas.

Dentro de `geography`, los dos nombres SoilGrids no son dos copias completas:

| Carpeta relativa a `geography` | Contenido comprobado |
| --- | --- |
| `mushroom-GIS/soilgrids` | 1.414 archivos, 395.714.887 bytes: originales WCS, 1.355 teselas normalizadas y metadatos. Los originales y las teselas son representaciones diferentes conservadas con su procedencia. |
| `mushroom-map-GIS/soilgrids-shared` | 601 archivos, 401.256.253 bytes: bloques adicionales de la adquisición española y documentación. |

No hay SHA de contenido compartido entre esas dos carpetas físicas según sus
manifiestos. Las 1.355 referencias lógicas del mapa a las teselas ya existentes
se resuelven en `mushroom-GIS/soilgrids`, sin mantener allí una segunda copia.
Sí quedan diez grupos de TIFF pequeños idénticos entre distintas rutas del propio
`soilgrids-shared`: 254.156 bytes redundantes en total; el mayor archivo repetido
mide 2.830 bytes. Por tanto, no describir el árbol como absolutamente libre de
duplicados. Esta revisión no cambia rutas ni elimina archivos referenciados.

`geography/generations/local-20260914` contiene únicamente el manifiesto de
807.785 bytes. `geography/imports` conserva tres manifiestos, 1.182.315 bytes,
y directorios vacíos. Ninguno contiene otra copia de los GiB de cartografía.
La revisión usa listados y tamaños actuales y SHA ya verificados de los
manifiestos, sin releer los rásteres grandes ni modificar nada en HA real.

## Resultado final de la preparación en HA real

Colocados los 3.581 archivos en 578 s mediante rename de nuestras copias verificadas
sobre el mismo volumen SMB, sin retransmitir los GiB. Comprobación posterior de
las 3.510 referencias del mapa y 1.432 GIS correcta; todos los archivos de datos
son ordinarios con un enlace físico. Los siete manifiestos/configuraciones tienen
SHA de metadatos comprobado y `SHA256SUMS` reúne los hashes de datos y metadatos.
Los hashes de los datos se reutilizan de la copia ya verificada, no se rehashearon.

`geography/imports` conserva los manifiestos pequeños de preparación y directorios
vacíos; no se utiliza en runtime. Los tres directorios originales siguen intactos.
No se ha instalado, reiniciado ni ejecutado código en HA real. La comprobación
remota se hizo mediante el volumen montado; la ejecución con media read-only se
probó en el contenedor local. La prueba nativa RPi4/iPhone será tras instalar.

HA 0.2.304 publicada; worker existente 1.1.2 validado. Fuentes actuales y
sus hashes en `backups/ha-portable-ready-20260915/`; esta copia no es un paquete
para sobrescribir datos privados ni una instalación por sideload. Las imágenes
Docker locales conservan la versión probada. Publicación multiarch verificada
según `docs/release-flow.md`; queda la instalación y prueba por el usuario.
