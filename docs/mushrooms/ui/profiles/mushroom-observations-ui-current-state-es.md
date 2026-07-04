# Estado actual de la UI de observaciones de setas

Este documento resume el estado funcional de la pantalla `Mushroom species > Observaciones` tras la iteracion local posterior a `0.2.180`.

La pantalla existe para acelerar la captura de observaciones reales que despues alimentaran el laboratorio local y el futuro motor de calibracion de especies. No debe entenderse todavia como calibrador productivo.

## Objetivo operativo

La pantalla debe permitir registrar muchas observaciones reales sin convertir el proceso en una carga manual lenta.

Casos principales:

- registrar observaciones positivas desde fotos geolocalizadas;
- registrar observaciones negativas o de baja abundancia;
- duplicar una observacion para anadir otra especie en la misma salida;
- importar varias fotos o carpetas usando una plantilla comun;
- revisar, archivar, restaurar y borrar definitivamente observaciones sin perder filtros;
- trabajar en local contra `docker-data/` sin tocar Home Assistant.

## Regla UI para listas seleccionables

Cuando un campo de la UI de setas represente una lista seleccionable de valores controlados y haya espacio suficiente, debe editarse con pastillas seleccionables en lenguaje humano, siguiendo el patron usado en fenologia, patrones de temporada, orientaciones y arboles observados.

Reglas:

- mostrar labels humanos desde `mushroom_labels.json` o `mushroom_reference_catalogs.json`, no IDs crudos;
- permitir seleccion multiple con checkboxes ocultos y pastillas visibles cuando el campo sea multi-valor;
- usar estados visuales claros para seleccionado/no seleccionado;
- hacer que el bloque use todo el ancho disponible si la lista puede crecer;
- mantener la validacion real en backend/validador, aunque la UI reduzca errores;
- reservar `<select>` para elecciones de un unico valor, listas muy largas o campos donde un control compacto sea claramente mas usable.

## Arboles observados

Las observaciones pueden registrar `site_context.observed_host_ids`.

Uso:

- seleccionar hasta 3 arboles/hosts observados directamente en el punto;
- guardar IDs de `catalogs.host_taxa`, no texto libre;
- mostrar nombres humanos del catalogo en el formulario y en el panel de detalle;
- tratarlo como evidencia de campo, no como inferencia GIS.

La UI debe renderizar este campo como pastillas seleccionables de ancho completo en alta, edicion, duplicado e importacion EXIF. No debe volver a un `<select multiple>` porque en navegadores como Safari puede comportarse de forma poco clara para multi-seleccion y obliga a ocupar altura sin mejorar la captura.

El backend y el validador deben rechazar mas de 3 hosts, IDs duplicados o IDs que no existan en `catalogs.host_taxa`. Las observaciones existentes sin este campo siguen siendo validas.

## Filtros y cabecera

La cabecera de la pantalla de Observaciones debe reflejar el filtro activo de especie:

- si se filtra una especie concreta, muestra esa especie;
- si el filtro es `Todas las especies`, muestra `Todas las especies`;
- no debe quedarse fijada en la especie desde la que se entro originalmente al tab.

Los filtros visibles son:

- fecha desde;
- fecha hasta;
- especie;
- resultado;
- estado de validacion;
- texto libre.

Los filtros de fecha son editables y usan date picker. Al seleccionar fecha, el date picker debe cerrarse y el formulario debe aplicar el filtro.

## Tabla de observaciones

La tabla soporta:

- ordenacion por cabeceras;
- seleccion tocando cualquier punto de la fila;
- detalle lateral de la observacion seleccionada;
- altitud redondeada a entero para ganar espacio;
- cabeceras compactas para fecha y estado;
- acciones visibles en escritorio sin perder los botones por anchura.

Columnas actuales:

- fecha;
- especie;
- coordenadas;
- altitud;
- tamano de la florada;
- observador;
- origen;
- estado;
- uso;
- acciones.

La tabla debe tener altura contenida. No debe crecer indefinidamente hasta desplazar botones inferiores o el panel de archivadas fuera de la zona de trabajo.

Las acciones principales de pantalla (`Nueva observacion`, `Importar imagenes
EXIF`, `Abrir calibracion`) deben estar justo debajo de la lista/detalle de
observaciones activas. No deben quedar debajo de archivadas ni debajo de la
reconstruccion GIS local, porque esa posicion dificulta la captura rapida de
observaciones.

## Acciones de fila

Acciones activas:

- `Editar`;
- `Duplicar`;
- `Archivar`.

Regla de interaccion:

- pulsar en la fila selecciona la observacion;
- pulsar en un boton ejecuta esa accion y no debe disparar tambien la seleccion de fila.
- seleccionar una fila no debe mover la pagina hacia arriba ni hacia el final
  del formulario; la UI debe preservar la posicion de scroll operativa.

## Coordenadas y mapa

Las coordenadas de una observacion son accionables en:

- la columna `Coordenadas` de la tabla;
- el campo `Coordenadas` del detalle lateral;
- el modal de alta/edicion, mediante un boton `Mapa` cuando hay latitud y
  longitud.

La accion abre un modal local de mapa con vista hibrida/Google Maps y boton para
abrir Google Maps externo. El modal sirve para revisar visualmente el punto,
hacer zoom y comparar varias observaciones cuando se abre desde evidencia.

Los datos son locales del usuario. No se debe describir esta pantalla como
anonimizadora ni como ocultacion por privacidad; la UI muestra las coordenadas
porque son necesarias para revisar observaciones.

## Duplicar observacion

`Duplicar` abre una plantilla sin guardar.

No debe:

- crear una observacion inmediatamente;
- reservar un `observation_id`;
- copiar un ID y cambiar solo el correlativo.

Debe:

- rellenar el formulario con los datos de la observacion origen;
- permitir cambiar especie, abundancia, fecha, observador, estado, uso y notas;
- permitir subir una o varias fotos EXIF antes de guardar;
- generar el ID solo al guardar, usando la fecha final.

Motivo: el formato `obs_YYYYMMDD_NNNN` debe corresponder a la fecha real de la observacion guardada. Si se duplica primero y luego se cambia fecha o EXIF, crear el ID antes deja IDs incoherentes.

Si desde una plantilla duplicada se suben varias fotos EXIF, la plantilla actua como valores comunes y se crea una observacion por foto.

## Importacion EXIF

La pantalla incluye `Importar imagenes EXIF`.

La lectura de metadatos depende de `Pillow==12.2.0` en `requirements.txt`. Esta dependencia debe estar instalada en local y en HA para extraer fecha, coordenadas y altitud desde fotos.

Compatibilidad actual esperada:

- JPEG con EXIF estandar de iPhone o Android: soportado si la foto conserva fecha/GPS.
- HEIC/HEIF: no considerarlo garantizado hasta validarlo en el contenedor real.
- Si se acepta HEIC/HEIF, valorar convertir a JPEG durante la subida preservando EXIF antes de procesar la observacion.
- Imagenes sin EXIF o con EXIF eliminado por mensajeria/redes: no deben crear observaciones corruptas.

El formulario pide una plantilla comun:

- observador;
- experiencia del observador;
- calidad del origen;
- tamano de la florada;
- estado de validacion;
- especie;
- uso en calibracion.

Por cada imagen la app intenta extraer:

- fecha;
- latitud;
- longitud;
- altitud;
- nombre de fichero.

Campos derivados:

- `location.source = photo_exif`;
- `altitude.source = photo_exif`, si hay altitud;
- `source.type = photo_exif`;
- `source.label = nombre del fichero`.

Puede seleccionarse una foto, varias fotos o una carpeta desde el selector del navegador.

Si una foto no tiene fecha o coordenadas EXIF, debe saltarse o informar el error sin crear una observacion corrupta.

## Edicion con EXIF

El formulario de edicion tambien admite recuperar datos desde EXIF.

Uso esperado:

- abrir una observacion existente;
- subir una foto EXIF;
- actualizar fecha, coordenadas, altitud y origen;
- conservar el resto de datos editables.

Si se suben varias fotos en edicion, la observacion actual puede actuar como plantilla: la primera foto actualiza el registro abierto y las restantes crean observaciones adicionales. Este comportamiento debe revisarse en futuras iteraciones si se quiere hacerlo mas explicito en UI.

## Archivadas y borrado defensivo

El flujo defensivo es:

1. Una observacion activa se puede archivar.
2. Una observacion archivada se puede restaurar.
3. Solo una observacion archivada se puede borrar definitivamente.

El borrado permanente exige confirmacion defensiva, incluyendo confirmacion backend por `observation_id`.

El panel de observaciones archivadas debe poder quedar abierto. Despues de archivar, restaurar o borrar, la pantalla debe preservar:

- especie seleccionada;
- filtros;
- ordenacion;
- observacion seleccionada si aplica;
- panel de archivadas abierto/cerrado;
- posicion operativa dentro de Observaciones.

Esto evita tener que volver a filtrar y desplegar archivadas al borrar varias observaciones.

## Preservacion de contexto tras acciones

Las acciones de observaciones no deben resetear al estado inicial del tab.

Deben preservar:

- `obs_species`;
- `date_from`;
- `date_to`;
- `result`;
- `validation`;
- `obs_q`;
- `sort`;
- `dir`;
- `obs_id`;
- `archive_open`.

La respuesta no debe forzar scroll al bloque `Status` superior si eso desplaza la pantalla fuera de la zona de trabajo. El ancla recomendada para acciones normales es el workspace de observaciones o el panel afectado.

## Relacion con el laboratorio local

Cuando se usa el servicio local `rainmapper-ha-ui`, los datos se escriben en:

```text
docker-data/mushroom-data/mushroom_observations.json
```

Esto permite cargar observaciones reales en local y despues construir el engine experimental sin contaminar HA.

La UI de observaciones es ahora la via preferida para capturar datos reales antes de construir el extractor meteorologico.

## Reconstruccion GIS local

La seccion `Reconstruccion GIS local` debe permanecer colapsable y cerrada por
defecto. Es una herramienta de revision, no el flujo principal de captura.

Subsecciones actuales:

- `Observaciones a reconstruir`: filtra por la especie seleccionada.
- `Valores GIS pendientes de mapping`: debe filtrar por la especie seleccionada
  cuando los pendientes procedan de observaciones reconstruidas.
- `Observaciones usadas para ultima reconstruccion`: seccion propia colapsable
  con los valores crudos de capa por observacion, cerrada por defecto.

Esta reconstruccion de observaciones no debe confundirse con
`mushroom_gis_mappings_rebuild.sh`, que reconstruye candidatos batch de mappings
para capas GIS y no contexto por observacion.

## Pendientes

- Decidir si la importacion EXIF multiple desde edicion debe tener una confirmacion explicita antes de crear varias observaciones.
- Construir importacion CSV/JSON si sigue siendo necesaria despues del flujo EXIF.
- Conectar las observaciones al extractor meteorologico local.
- Mostrar en el futuro candidatos de parametros por especie, sin sobrescribir perfiles automaticamente.
- Revisar si las observaciones archivadas deben poder filtrarse y ordenarse con las mismas cabeceras que las activas cuando crezcan mucho.
- Seguir puliendo el modal de mapa para listas largas de observaciones sin
  perder legibilidad.
