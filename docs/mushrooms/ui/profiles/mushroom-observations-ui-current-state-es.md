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

## Acciones de fila

Acciones activas:

- `Editar`;
- `Duplicar`;
- `Archivar`.

Regla de interaccion:

- pulsar en la fila selecciona la observacion;
- pulsar en un boton ejecuta esa accion y no debe disparar tambien la seleccion de fila.

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

## Pendientes

- Decidir si la importacion EXIF multiple desde edicion debe tener una confirmacion explicita antes de crear varias observaciones.
- Construir importacion CSV/JSON si sigue siendo necesaria despues del flujo EXIF.
- Conectar las observaciones al extractor meteorologico local.
- Mostrar en el futuro candidatos de parametros por especie, sin sobrescribir perfiles automaticamente.
- Revisar si las observaciones archivadas deben poder filtrarse y ordenarse con las mismas cabeceras que las activas cuando crezcan mucho.
