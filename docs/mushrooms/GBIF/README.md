# Investigación GBIF — copia local del 16/09/2026

Descarga terminada y verificada el 16/09/2026 a las 20:43 UTC:
**1.928 registros únicos y 2.291 fotografías**, unos **1,9 GB** en total.
Catálogo fuente: `docker-data/mushroom-data/mushroom_profiles.json`, 21 perfiles
resueltos mediante 22 taxones. Ámbito: Catalunya (`ESP.6_1`), 19/06/2012–16/09/2026.
Sin filtros por proveedor, licencia, calidad ni incertidumbre.

## Abrir en local

- [Visor MapLibre de observaciones](snapshot-catalunya-20120619-20260916-full/index.html).
- [Galería sin conexión](snapshot-catalunya-20120619-20260916-full/gallery.html).
- [Descripción, estructura y tabla por especie](snapshot-catalunya-20120619-20260916-full/README.md).
- [Tabla CSV de revisión](snapshot-catalunya-20120619-20260916-full/review.csv).
- [Validación de la descarga](snapshot-catalunya-20120619-20260916-full/validation.json).
- [Inventario final y huellas](snapshot-catalunya-20120619-20260916-full/offline-manifest.json).

Estas rutas apuntan a archivos locales **excluidos de Git y Docker**. Los enlaces
no estarán disponibles en un clon sin esa copia de investigación. También se
excluyen las muestras y respuestas JSON de las consultas preliminares.
El código y la documentación del visor se versionan junto con HA 0.2.309.
Los registros descargados, fotografías y revisiones personales no se publican.

El visor permite elegir un perfil o todos, filtrar por incertidumbre (≤1 km,
>1 km, desconocida, **≤1 km y desconocidas**, o todas), buscar y abrir detalles/fotos
al pulsar una cita. El nuevo filtro combinado incluye 1.774 observaciones del conjunto completo.
La cabecera es compacta y el mapa ocupa todo el ancho y la altura restante de la
ventana, con la leyenda dentro de la pantalla. Se retiró el navegador lateral;
al pulsar una cita aparece una ficha superpuesta con cierre y desplazamiento propio.
Las fotos aparecen al principio de la ficha, completas y sin recorte; si hay varias,
se recorren horizontalmente. Los datos principales quedan a continuación y los
campos secundarios se conservan en «Más datos y procedencia», cerrado inicialmente.
Los filtros restaurados por el navegador se sincronizan con los puntos y el recuento.
`Mostrar incertidumbre`, activado inicialmente, dibuja círculos azul claro
semitransparentes con radio igual a los metros publicados, aplicando los mismos
filtros que a los puntos. Son 747 radios conocidos en la copia inicial. Por
petición del usuario, las 1.181 incertidumbres desconocidas se representan en
rojo semitransparente con **500 m de radio exclusivamente visual**; su valor
original continúa siendo desconocido y no se usa 500 m para entrenar ni filtrar.
La leyenda y la ficha distinguen esa convención. No se crean zonas ni se modifican coordenadas.

Debajo de las coordenadas se muestran **altitud del DEM local y municipio obtenido
de los polígonos municipales IGN locales**. La extracción cubre 1.928 altitudes
(DEM ICGC de 5 m) y 1.926 municipios; dos puntos carecen de cobertura municipal
en el fichero utilizado y se muestran como no disponibles. Se leyeron 1.151
coordenadas distintas, reutilizando los resultados para citas coincidentes.
[Resultados y fuentes](snapshot-catalunya-20120619-20260916-full/metadata/geography.json).
Son datos del punto publicado, no una caracterización de toda su zona de incertidumbre.

Los números de los grupos cuentan **registros**, no ejemplares ni ubicaciones únicas.
En el caso revisado de *Boletus aereus* hay dos pares con la misma fecha, observador
y coordenadas, pero distintos IDs de Observation.org: GBIF `4459994467`/`4460004405`
en 41.229605, 1.097946 y `4460000578`/`4462113128` en 41.225215, 1.108761.
Se conservan como candidatos a revisar por posible duplicidad. Al pulsar un grupo
coincidente pequeño, el visor permite escoger cada registro por su identificador.

Bajo el zoom, el botón **2D/3D** activa relieve con las mismas teselas Terrarium
(Mapzen) del mapa de predicción, sin exageración (1×), e inclina la vista a 55°.
Al volver a 2D desactiva el relieve y la inclinación. **↑N** orienta al norte
conservando centro, zoom e inclinación. El relieve se conserva al cambiar de fondo
y requiere Internet; no usa ni modifica el DEM local de las fichas.

Los fondos **Satélite+, Híbrido, Topográfico y Liberty** reutilizan las cuatro
configuraciones actuales del visor compartido del mapa de predicción. Requieren
Internet; el usuario descartó un fondo local esquemático. MapLibre, las
observaciones y todas las fotos se leen localmente. GBIF solo se abre si se pulsa
expresamente el enlace de procedencia. La galería sigue siendo utilizable sin red.

Se han conservado los registros interpretados, los 1.928 originales `verbatim`
con sus extensiones, metadatos completos de los cinco proveedores, correspondencias
taxonómicas, URLs de consulta, tiempos, recuentos antes/después y SHA-256.
Las fotografías enlazadas se guardan sin transformar, con autoría y licencia
vinculadas a cada observación. Verificados 2.283 JPEG y 8 PNG; ningún error de descarga.
Es una captura de la API viva, no una descarga transaccional con DOI.

| Incertidumbre declarada | Registros |
| --- | ---: |
| Hasta 1.000 m, inclusive | 593 |
| Superior a 1.000 m | 154 |
| Desconocida | 1.181 |

El complejo operativo `Morchella elata` y `Cantharellus cibarius` sensu lato se
consultan por sus taxones nominales; no se afirma cobertura exhaustiva de todos
sus miembros. `Lactarius salmonicolor / quieticolor` se ha consultado como dos
especies. GBIF distingue `L. vinosus` de `L. sanguifluus` en esta captura.

Las observaciones operativas, setales y catálogo locales conservaron sus SHA-256
durante la descarga y validación. No se han importado registros, asignado abundancias,
creado setales, cambiado destinos del worker ni ejecutado entrenamiento/precálculo.
Todos los registros descargados declaran presencia; las ausencias del experimento
de entrenamiento siguen siendo una decisión pendiente.

## Revisión manual de observaciones

Cada cita empieza como **Pendiente**. En su ficha puede cambiarse a **Dudosa**,
**Aceptada** o **Rechazada**, y volver a Pendiente. El filtro «Revisión» se combina con especie,
incertidumbre y búsqueda; el recuento desglosa los estados de los resultados.
Los cambios se guardan automáticamente en el navegador. Para activar además el
**guardado automático en disco**, pulsar «Activar guardado en archivo» y elegir
una carpeta en Chrome. Se crea o recupera `gbif-revision-autoguardado.json` en ella;
si ya existe, se valida y combina con las decisiones más recientes del navegador
antes de escribir. Seleccionar la carpeta no vacía el archivo existente.
La interfaz anuncia «Guardado en archivo» solo después de cerrar correctamente la
escritura. Si falla, conserva el archivo anterior, mantiene el cambio en el
navegador y muestra el error. «Reanudar guardado» permite reintentar.

El visor recuerda el archivo mediante IndexedDB. Al reabrirlo recupera y combina
la revisión; si Chrome necesita permiso otra vez, muestra «Reanudar guardado».
El navegador debe autorizar expresamente ese acceso desde el botón. Si se pierden
sus datos, elegir de nuevo la misma carpeta recupera el JSON. Las exportaciones
quedan como copias voluntarias al terminar la sesión, no son necesarias tras cada
cambio cuando el guardado en archivo está activo. Antes de cerrar, esperar a que
aparezca «Guardado en archivo»; una escritura todavía pendiente no se garantiza
frente a un cierre abrupto.

Las decisiones siguen separadas por la huella SHA-256 de `occurrences.json`.
El archivo se valida antes de cada escritura, se conserva la decisión más reciente
y se serializa la escritura entre pestañas del mismo visor. El navegador no
compatible muestra que solo están disponibles almacenamiento interno/exportación.
La prueba automatizada usa handles reales del navegador (OPFS en localhost de
pruebas), escrituras/abortos y recuperación desde IndexedDB; sustituye el selector
nativo de carpeta, cuya interacción con el usuario no se automatiza.
Referencia de la API: [documentación de Chrome](https://developer.chrome.com/docs/capabilities/web-apis/file-system-access).

**Exportar revisión** descarga un JSON con los 1.928 IDs GBIF, estado y fecha de
la decisión (`reviewed_at`; nula si nunca se revisó), versión de esquema y huella
de la copia. No modifica un JSON exportado anteriormente. **Importar revisión**
valida el conjunto completo antes de guardar y combina por fecha de decisión:
conserva la más reciente, incluyendo el regreso explícito a Pendiente. Rechaza
archivos de otra copia, IDs duplicados/desconocidos, estados inválidos y decisiones
contradictorias con la misma fecha. Los errores de almacenamiento se muestran y
no se anuncian como cambios guardados.

Sin activar el guardado en archivo, puede importarse el último JSON al empezar
y exportarse al terminar. Conservar ese nuevo archivo para la próxima sesión y para
la futura incorporación de las aceptadas. El CSV original no incorpora estos
estados. Los JSON `gbif-revision-*.json` están excluidos de Git en esta carpeta.
No se alteran datos originales, abundancias ni incertidumbre; aprobar aquí no
inserta automáticamente la cita en las observaciones operativas.

## Continuidad

**17/09/2026: revisión manual pendiente por parte del usuario.** Revisará las
observaciones descargadas de GBIF en el visor y asignará Pendiente, Dudosa o
Aceptada o Rechazada, comprobando duplicados, fechas, identificación, precisión y utilidad.
No se considera completada ni se presupone el número de citas ya revisadas.
Conservar sus decisiones guardadas y esperar su indicación antes de incorporar
observaciones, crear zonas/setales o iniciar pruebas comparativas de entrenamiento.
No revisar ni aprobar automáticamente en su nombre. El umbral ≤1 km no sustituye esos controles. Mantener las dos
vías descritas en [el plan](gbif-observations-and-sites-plan.md), sin importar ni
entrenar automáticamente.

Los documentos `gbif-assessment-2026-09-16.md` y sus consultas son el análisis
inicial de tres especies; no confundir sus recuentos con esta ampliación.
El documento de handoff se conserva como entrada histórica del usuario.

Scripts locales: `download_gbif_snapshot.py`, `download_gbif_media.py` y
`finalize_gbif_snapshot.py`. Las descargas ya están terminadas: **no volver a
ejecutarlas por rutina**. `finalize_gbif_snapshot.py` valida en local sin red;
requiere Pillow y compara también las huellas de los datos operativos originales.

Actualización 17/09/2026: cuatro estados Pendiente/Dudosa/Aceptada/Rechazada.
«Aceptada» conserva la clave interna `approved`, por lo que las revisiones
antiguas de «Aprobada» siguen siendo válidas; «Rechazada» usa `rejected`.
Ambos participan en filtros, recuentos, exportación/importación y autoguardado.
No se migran ni sobrescriben las decisiones existentes.
