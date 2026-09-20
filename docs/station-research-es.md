# Investigación local de estaciones Wunderground

Herramienta separada de HA, del worker y de los catálogos operativos. Se abre en
[127.0.0.1:8123](http://127.0.0.1:8123/). Para arrancarla tras cerrar el servidor:

```sh
./local-apps/wunderground/start.command
```

El lanzador usa `.venv`, la clave configurada de Wunderground y el conjunto local
`local-apps/wunderground/data/`. La clave se utiliza exclusivamente en
el servidor, nunca se entrega al navegador. El servidor escucha solo en loopback.
Los fondos y el relieve requieren Internet; las decisiones se guardan en el Mac.
El código está en `local-apps/wunderground/code/station_research.py` y `local-apps/wunderground/code/web/`.

## Uso

Cabecera en dos filas: selección/revisión y acciones arriba; fuentes y capas
visibles debajo. El botón de capas a la izquierda, antes de 3D, permite elegir
Satélite+, Híbrido, Topográfico o Liberty en una lista directa con el activo marcado.

El buscador **Municipio o topónimo** de la cabecera se activa con Enter o
**Buscar**. Muestra hasta ocho resultados con comarca/región/país; al elegir uno,
el mapa se centra allí y coloca un POI con su nombre. Ese POI desaparece al
iniciar la siguiente búsqueda, incluso si no devuelve resultados. Admite lugares de cualquier país y prioriza suavemente
la zona visible, sin restringirse a Catalunya. Añade provincia o país cuando
el nombre sea ambiguo. Escape o un clic fuera cierra los resultados.

Utiliza el servicio público [Photon](https://github.com/komoot/photon), basado
en OpenStreetMap. Las búsquedas se envían solo al pulsar Buscar/Enter, sin
consultas por cada tecla; máximo una petición por segundo y caché persistente
en el Mac por texto y zona aproximada. La primera consulta requiere Internet;
la disponibilidad y los topónimos dependen del proveedor. No utiliza la clave
WU. Navegar a un lugar no consulta estaciones, ni altera filtros o revisiones,
aunque esté activado el modo investigación.

El selector muestra «Prioritarias iniciales» o «Todas las candidatas», sin filtro
geográfico implícito. La clasificación histórica «nueva» de la primera descarga
excluía las de fuera de Catalunya; ya no se usa como filtro del visor.

- **Fuentes actuales** permite marcar cualquier combinación de Meteocat,
  AEMET, Meteoclimatic y Wunderground con casillas independientes (también ninguna). El recuento refleja la selección;
  candidatas y preliminares mantienen sus filtros. Los huecos siguen calculados
  con todas las fuentes de la base de referencia.
- **2D/3D** activa el terreno, con el mismo proveedor del visor GBIF. **↑N** orienta
  al norte conservando el modo de relieve.
- **⌖** activa investigación. Pulsa un punto libre del mapa: consulta estaciones
  cercanas y comprueba su disponibilidad de lluvia. Omite por ID las estaciones
  ya incorporadas a la red local de referencia, para no duplicar sus marcadores. El modal muestra el avance.
  Pulsar una estación abre su ficha sin lanzar otra búsqueda geográfica.
- **Preliminares**, violetas, son resultados online aún no promovidos. Desde la
  ficha puedes **Promover a candidata**. Las ya incorporadas que quedaron en
  la descarga inicial también se ocultan de candidatas y preliminares; se conservan
  los registros originales y sus revisiones en disco y en la exportación. Las estaciones ya conocidas o excluidas
  según la base local no se incorporan por esa vía.
- **Pendiente / Dudosa / Aceptada / Rechazada** se guarda inmediatamente en disco
  y se puede filtrar. Aceptada no modifica la red de estaciones ni el IDW.
- **Eliminar preliminares** limpia únicamente esa etapa; conserva candidatas,
  revisiones y la caché de consultas. Puede volver a descubrir una preliminar
  eliminada al buscar de nuevo en la zona.
- **Limpiar puntos consultados** elimina los círculos de búsquedas, incluidos
  los iniciales. No reaparecen al recargar y no borra estaciones ni revisiones.
- **Exportar revisión** descarga registros y estados para consulta o copia; el
  guardado normal es automático, no requiere exportar ni importar cada sesión.

Los datos viven en `research.sqlite3` (y sus archivos SQLite `-wal`/`-shm` mientras
está abierto), dentro del directorio de investigación ignorado por Git. No se debe
copiar solo el archivo principal con el servidor abierto para hacer una copia
integral: cerrar primero el servidor o usar la API de backup de SQLite. La
exportación JSON copia los registros y decisiones, no toda la caché meteorológica.

## Qué significa X/30

En las candidatas y preliminares se consultan los últimos **30 días completos**
según Europe/Madrid: desde ayer menos 29 días hasta ayer, inclusivos. Se cuenta un
día si tiene precipitación numérica finita y no negativa; **0 mm cuenta**. No se
suman duplicados de una fecha, ni se convierten errores de API en cero días.
Se conserva el histórico recibido. La lectura actual aporta altitud publicada y
última observación cuando Wunderground las entrega. Un fallo de lectura actual
no invalida un histórico obtenido correctamente.

En las estaciones actuales se utilizan los datos de la **base local del
17/09/2026 a las 11:31**: su ventana termina el 16/09, evitando contar como completo
el día de generación. Solo se reutilizan los GeoJSON si coinciden con las huellas
del análisis original. Esto refleja disponibilidad en nuestra base, no demuestra
que el proveedor carezca de los días ausentes. No es una lectura del HA real.

**Disponibilidad no demuestra calidad:** ni un 30/30 ni QC=1 de Wunderground
certifican un pluviómetro correcto o una mejora del IDW. El catálogo WU tiene una
fecha de actualización separada de la última lectura meteorológica.

## Consultas limitadas y caché

El endpoint [Location Service Near](https://developer.weather.com/docs/openapi/location-service-near-3-0)
devuelve hasta diez estaciones cercanas. Una búsqueda no descarga todas las
estaciones de un territorio. Se deduplican por ID y se conservan las revisiones.
Cada estación requiere su propia consulta de
[histórico diario](https://developer.weather.com/docs/openapi/pws-historical-2-0)
y de lectura actual. Las consultas se realizan secuencialmente, con separación
mínima de 0,4 s. El histórico se reutiliza para la misma ventana, las lecturas
actuales durante la misma hora UTC y la búsqueda por coordenadas durante el día.
Abrir el visor no consulta de golpe el histórico de todas las candidatas; el
recuento cambia con la promoción y revisión guardada en SQLite.

Quedan para una fase posterior la evaluación comparativa de calidad, la aprobación
operativa y el backfill de las estaciones seleccionadas. No se modifica HA real,
HA local, el destino del worker, entrenamientos ni precálculos desde este visor.
