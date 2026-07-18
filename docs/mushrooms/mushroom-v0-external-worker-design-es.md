# Reconstruccion V0 externa en un Mac

Estado: **diseno acordado, pendiente de implementar**

Fecha: 2026-07-18

Este documento conserva la propuesta para ejecutar la reconstruccion completa
del modelo V0 en un Mac con Docker, manteniendo Home Assistant como fuente de
verdad y sin duplicar el codigo del reconstructor.

No describe una funcionalidad que ya exista. Antes de empezar a implementarla
hay que releer este documento, comprobar el estado actual del pipeline y validar
las preguntas abiertas del final.

## 1. Motivo

La reconstruccion completa ya funciona en Home Assistant, pero la Raspberry Pi
es sensiblemente mas lenta que un Mac:

- MacBook Pro M1 Pro: aproximadamente 40 segundos.
- Home Assistant/Raspberry Pi: 4 minutos y 44 segundos.
- El usuario estima que la fase GIS/DEM en HA consume por si sola alrededor de
  dos minutos. Esta ultima cifra aun debe medirse con los tiempos de fase del
  job, no tratarse como un dato confirmado.
- Falta medir el MacBook Pro M5.

La finalidad del worker externo es aprovechar el Mac cuando este disponible,
sin eliminar la reconstruccion local de HA ni crear dos implementaciones que
puedan divergir.

## 2. Decisiones ya acordadas

1. Home Assistant seguira siendo la fuente de verdad de datos y resultados.
2. La reconstruccion local de HA se conservara siempre como alternativa.
3. El Mac ejecutara las cuatro fases completas, incluida GIS/DEM:
   1. reconstruccion GIS/DEM;
   2. contexto meteorologico;
   3. union de features V0;
   4. modelo aprendido V0.
4. HA y el worker usaran el mismo codigo Python del pipeline. No habra una
   copia del reconstructor dentro de `rainmapper-worker/`.
5. El worker tendra una imagen Docker propia. Los 5,9 GB de GIS/DEM se
   incorporaran a esa imagen, en una capa estable, para poder mover exactamente
   la misma imagen entre el M1, el M5 u otro ordenador compatible.
6. Esa imagen no se publicara en GHCR ni en otro registro de Internet. Se
   construira y transferira de forma privada con `docker save`/`docker load`.
7. Si se usa Tailscale, el worker utilizara siempre la direccion estable de
   Tailscale de HA, tambien cuando el Mac este en la misma red local. No se
   alternaran direcciones LAN y Tailscale.
8. HA no localizara el Mac por IP ni abrira una conexion entrante hacia el.
   Sera el worker quien se registre, envie heartbeats y pregunte a HA si tiene
   trabajo.
9. La UI podra permitir elegir explicitamente donde ejecutar el job: HA, M1 o
   M5. El equipo desde el que se abre el navegador no determina donde corre la
   reconstruccion.
10. Observaciones, perfiles y catalogos forman parte de los datos vivos que el
    worker debe recibir. No basta con enviar solo los incrementales
    meteorologicos.

## 3. Lo que no cambia

- Las observaciones continuan guardando la abundancia catalogada, por ejemplo
  `scarce`, `very_scarce`, `normal` o `abundant`.
- El objetivo binario favorable/desfavorable se sigue derivando de
  `prediction_favorable` en el catalogo `observation_flush_abundance`.
- No se migran ni duplican los JSON de observaciones para ejecutar el worker.
- Los datos privados de `docker-data/mushroom-data/` no se incorporan a la
  imagen, no se versionan y no se transfieren a ningun servicio publico.
- El V0 sigue siendo descriptivo y auditable. El worker no debe promocionar
  evidencia a perfiles ni modificar afinidades manuales.
- La seleccion de un worker no autoriza cambios de version, releases HA,
  limpieza de GHCR ni ninguna otra operacion destructiva.

## 4. Arquitectura propuesta

```text
                         Tailscale: URL fija de HA

  UI de Rainmapper ────────> Home Assistant / Rainmapper
                                  │
                                  │ crea job y snapshot inmutable
                                  │
                         API privada de workers
                                  ▲
                                  │ polling/heartbeat saliente
                                  │ descarga inputs / sube progreso y resultado
                                  │
                     Docker rainmapper-worker
                     Mac M1, Mac M5 u otro equipo
                                  │
                    codigo comun de rainmapper_core
                                  │
                  GIS/DEM incluido en la imagen local
```

El navegador solo ordena el trabajo y consulta su estado. Cerrar la pestana o
abrir Rainmapper desde otro ordenador no debe interrumpir el job.

### 4.1 Dos modos de ejecucion

**Home Assistant**

- El job actual se ejecuta en un thread/background job del add-on.
- Lee los datos persistentes de HA y escribe los artefactos V0 en HA.
- No depende de que ningun Mac ni Tailscale esten disponibles.

**Worker externo**

- HA crea el job y congela un manifest de entrada.
- El worker elegido reclama el job por polling.
- Descarga los datos vivos necesarios y usa su GIS/DEM local incluido en la
  imagen.
- Ejecuta exactamente el mismo pipeline comun.
- Sube un paquete de resultados y sus checksums.
- HA valida el paquete y solo entonces sustituye atomicamente los artefactos
  V0 vigentes.

## 5. Un solo codigo de reconstruccion

Actualmente la coordinacion de las cuatro fases esta dentro de
`start_mushroom_model_rebuild_job()` en
`rainmapper-app/app/web_server.py`. Los calculos ya viven en modulos comunes:

- `rainmapper_core/mushroom_gis_lab.py`;
- `rainmapper_core/mushroom_observation_context.py`;
- `rainmapper_core/mushroom_observation_features.py`;
- `rainmapper_core/mushroom_learned_model.py`.

Antes de crear el worker se debe extraer la orquestacion a un modulo comun,
por ejemplo:

```text
rainmapper_core/mushroom_rebuild_pipeline.py
```

Ese modulo deberia exponer una operacion del estilo:

```text
run_rebuild(inputs, outputs, scope, progress_callback, cancel_event)
```

La firma exacta se decidira al implementar, pero el contrato debe cubrir:

- alcance: una especie, pendientes o todas;
- rutas de entrada y directorio temporal de salida;
- callbacks de fase, porcentaje, mensaje y tiempos;
- cancelacion cooperativa;
- resultado estructurado con contadores, manifest y checksums;
- ausencia de dependencias HTTP, HTML o de la UI.

Quedaran dos adaptadores finos:

- `web_server.py`: crea el job HA, muestra progreso y llama al pipeline comun;
- `rainmapper-worker/`: transporte, cache, autenticacion y llamada al mismo
  pipeline comun.

No se aceptara copiar las cuatro llamadas actuales al worker. Si cambia una
fase, HA y Mac deben recibir el cambio al actualizar el mismo paquete de codigo.

## 6. Estructura prevista del worker

La carpeta nueva podria tener esta forma:

```text
rainmapper-worker/
  Dockerfile
  worker.py
  requirements-worker.txt
  docker-compose.example.yml
  README.md
```

Responsabilidades de `worker.py`:

- registrar el worker y enviar heartbeats;
- consultar jobs pendientes;
- descargar y verificar el snapshot de entrada;
- preparar directorios temporales y cache local;
- llamar a `rainmapper_core.mushroom_rebuild_pipeline`;
- enviar progreso, logs acotados y estado de cancelacion;
- empaquetar, firmar mediante checksums y subir resultados;
- borrar temporales de forma segura al terminar.

No debe contener reglas de abundancia, calculos GIS, logica meteorologica ni
logica del modelo.

## 7. Imagen Docker local y GIS/DEM

### 7.1 Dataset actual inspeccionado

El repositorio de trabajo contiene `mushroom-GIS-HA`, con un tamano aproximado
de 5,9 GB:

- DEM ICGC 5 m: 4,8 GB, bajo
  `model-elevacions-terreny-topografic-catalunya-5m-2009-2018/`;
- MVC50: 844 MB, bajo `MVC50mil/`;
- geologia ICGC 1:50.000: 280 MB, bajo
  `geologia-territorial-50000-geologic-v3r0-202412/`.

Estas rutas coinciden con las que resuelve
`rainmapper_core/mushroom_gis_lab.py`. Ese modulo ya admite
`RAINMAPPER_MUSHROOM_GIS_ROOT`, por lo que el contenedor puede fijar, por
ejemplo:

```text
RAINMAPPER_MUSHROOM_GIS_ROOT=/opt/rainmapper/mushroom-GIS
```

### 7.2 La imagen del worker no es la imagen HA

Los 5,9 GB no deben anadirse al add-on de Home Assistant. Se creara una imagen
independiente para el worker. De ese modo:

- las actualizaciones normales de HA siguen siendo pequenas;
- el worker conserva GIS/DEM aunque cambie el codigo;
- Docker puede reutilizar la capa GIS si el Dockerfile se ordena correctamente;
- los Macs pueden cargar la misma imagen sin reconstruir el dataset.

Hay que prever mas espacio que el tamano nominal del dataset. Como referencia
operativa, reservar al menos 12-15 GB por equipo entre imagen, exportacion,
cache y temporales, y medir el uso real antes de darlo por definitivo.

### 7.3 Construccion y transferencia privadas

Flujo previsto, todavia no implementado:

```bash
docker build -f rainmapper-worker/Dockerfile \
  -t rainmapper-worker:<version> .

docker save rainmapper-worker:<version> \
  -o rainmapper-worker-<version>.tar

# Copiar el TAR por un medio privado al otro Mac.

docker load -i rainmapper-worker-<version>.tar
```

El TAR no se anade a Git. Tampoco se publica en GHCR. Puede guardarse en un
disco local, NAS privado o transferencia directa entre equipos.

### 7.4 Arquitecturas de CPU

M1 y M5 son `arm64`, por lo que pueden compartir una imagen arm64. Si se quiere
soportar tambien un PC `amd64`, habra que construir y exportar una imagen para
cada arquitectura o un archivo OCI multiarquitectura. Esta portabilidad no
debe suponerse sin probar Rasterio/GDAL y el resto de dependencias nativas en
ambas arquitecturas.

### 7.5 Licencias y procedencia

Antes de empaquetar GIS/DEM hay que revisar las condiciones de redistribucion
de cada fuente. Aunque la transferencia vaya a ser privada, la imagen no debe
publicarse ni compartirse con terceros hasta confirmar licencias y atribucion.

## 8. Datos que viajan desde HA

El worker debe recibir un snapshot autocontenido de los datos vivos necesarios
para que el resultado sea reproducible.

### 8.1 Incluir

- observaciones activas que correspondan al alcance del job, y las necesarias
  para reconstruir artefactos compartidos;
- perfiles de especies;
- catalogos de referencia, incluido `prediction_favorable`;
- labels o metadatos de catalogo solo si los necesita el calculo, no por la UI;
- mappings GIS;
- areas y microareas/setales conocidos cuando intervengan en features;
- metadatos de estaciones;
- historicos e incrementales meteorologicos necesarios para las ventanas de
  las observaciones;
- version de app/core, schema y configuracion de calculo relevante.

### 8.2 No incluir

- fotos, videos, posters ni EXIF raw de observaciones;
- backups completos;
- claves API, cookies, tokens de fuentes meteorologicas o secretos HA;
- los 5,9 GB GIS/DEM, porque ya estan en la imagen;
- archivos de log generales;
- otros datos privados sin relacion con el job.

### 8.3 Sincronizacion incremental

La primera version puede transferir un snapshot comprimido completo de los
datos vivos si su tamano es razonable. Despues se puede optimizar con un manifest
por archivo:

```text
ruta relativa + tamano + mtime logico + SHA-256
```

El worker conserva una cache local y solo descarga archivos cuyo hash haya
cambiado. La cache nunca es la fuente de verdad: ante una discrepancia se
descarta y se vuelve a descargar desde HA.

Para los historicos meteorologicos conviene medir antes cuantos archivos y
bytes necesita realmente una reconstruccion. No se debe disenar una descarga
incremental compleja sin esa medicion.

## 9. Protocolo de jobs

### 9.1 Identidad del worker

Cada instalacion tendra configuracion local no versionada:

- `worker_id` estable, por ejemplo `macbook-m1` o `macbook-m5`;
- nombre visible;
- URL Tailscale fija de HA;
- token dedicado, revocable y distinto de cualquier token de usuario;
- capacidades: arquitectura, RAM, espacio libre, version del worker, version
  del core y manifest GIS.

El `worker_id`, no su IP, identifica el destino. Cambiar de Wi-Fi no crea un
worker nuevo.

### 9.2 Secuencia

1. El worker hace `heartbeat` saliente a HA.
2. HA muestra el worker como disponible si el heartbeat es reciente y las
   versiones son compatibles.
3. El usuario elige destino y solicita reconstruccion.
4. HA crea un `job_id`, fija alcance y construye el manifest de entrada.
5. El worker elegido consulta jobs y reclama el suyo mediante una operacion
   atomica.
6. Descarga snapshot/archivos, valida hashes y confirma que puede empezar.
7. Ejecuta las cuatro fases y publica progreso periodicamente.
8. Consulta entre unidades de trabajo si HA ha solicitado cancelar.
9. Empaqueta solo los artefactos permitidos y sube resultados/checksums.
10. HA valida compatibilidad y que el snapshot fuente siga vigente.
11. HA promueve los resultados atomicamente o rechaza el paquete completo.
12. El worker limpia temporales; HA conserva un resumen acotado del job.

### 9.3 Estados minimos

```text
queued
claimed
syncing_inputs
running
uploading_results
validating
complete
cancel_requested
cancelled
failed
worker_disconnected
```

`worker_disconnected` no significa automaticamente que el proceso haya
fallado. Debe existir un timeout claro y una reconciliacion si el worker vuelve
a conectarse.

### 9.4 Progreso

Se reutilizaran los callbacks incrementales que ya existen en las cuatro fases.
El worker enviara como minimo:

- fase e indice de fase;
- porcentaje de fase y total;
- unidad actual/total cuando exista;
- mensaje localizado o codigo de mensaje;
- tiempo total y de fase;
- ETA cuando haya una base de calculo suficiente;
- ultimo heartbeat.

El progreso se guarda en HA, no solo en el DOM del navegador. Asi sobrevive a
recargas y permite abrir el estado desde otro equipo.

## 10. Resultados y consistencia

Los artefactos actuales incluyen, entre otros:

- `mushroom_gis_observation_reconstruction.json`;
- `mushroom_observations_weather_features.json` y CSV/informe;
- `mushroom_observation_features_v0.json` y CSV/informe;
- `mushroom_model_v0.json` e informe.

El worker debe escribirlos primero en un directorio temporal. HA solo los
aceptara si el paquete incluye y supera estas comprobaciones:

- version compatible de app/core y schema;
- hash del catalogo y de la politica `prediction_favorable`;
- manifest/version del GIS/DEM;
- hash del snapshot de observaciones, perfiles, catalogos y mappings;
- lista cerrada de rutas de salida permitidas;
- SHA-256 y tamano de cada salida;
- JSON parseable y validaciones de dominio existentes;
- contadores coherentes de observaciones, especies y gaps.

Si las observaciones o cualquier input relevante cambian mientras corre el
job, HA no debe instalar silenciosamente un resultado obsoleto. Debe rechazarlo
con un estado comprensible y ofrecer reconstruir de nuevo.

La promocion sera atomica: guardar paquete, validar, hacer backup corto de los
artefactos vigentes y sustituirlos como una unidad. Un fallo no puede dejar una
mezcla de fases nuevas y antiguas.

## 11. Integracion en la UI

La propuesta inicial es anadir un selector al iniciar una reconstruccion:

```text
Ejecutar en:
  Home Assistant
  MacBook M1       disponible · worker/core X · GIS Y
  MacBook M5       no disponible
```

Reglas:

- HA siempre aparece como opcion.
- Un worker incompatible, sin heartbeat reciente o sin espacio suficiente se
  muestra deshabilitado y explica el motivo.
- No se cambia automaticamente de worker sin informar al usuario.
- Si el destino desaparece antes de reclamar el job, se puede cancelar, esperar
  o elegir HA; no se debe ejecutar dos veces sin saberlo.
- Solo un worker reclama cada job.
- La UI de progreso actual debe mostrar tambien sincronizacion, subida y
  validacion, ademas de las cuatro fases.
- Mas adelante se puede anadir seleccion automatica del worker mas rapido, pero
  no es necesaria en la primera version.

## 12. Tailscale

### 12.1 Direccion unica de HA

La configuracion del worker usara una URL estable de Tailscale para HA, por
ejemplo conceptualmente:

```text
RAINMAPPER_HA_URL=https://homeassistant.<tailnet>.ts.net:<puerto>
```

El nombre/puerto real se decidiran al implementar. Lo importante es que esa URL
sea la misma dentro y fuera de casa. No se intentara detectar si conviene una IP
LAN distinta.

Esto se refiere a la comunicacion worker-HA. El usuario puede abrir la UI de HA
por la ruta que use habitualmente; el navegador no transporta el job.

### 12.2 Servicio accesible

El add-on necesitara una API de worker autenticada y alcanzable desde el
tailnet. No se debe asumir que el ingress normal del navegador sirve para un
proceso headless. Hay que definir un puerto/API acotado, protegido por token y
restringido mediante ACL de Tailscale.

### 12.3 Ruta desde Docker Desktop

Primero se probara que el contenedor puede alcanzar la IP/MagicDNS de HA a
traves del Tailscale del host Mac. Si Docker Desktop no enruta correctamente el
tailnet, la alternativa es un sidecar de Tailscale. No se anadira ese sidecar
hasta confirmar que es necesario.

### 12.4 Disponibilidad

- Para ejecutar en un Mac, Tailscale debe estar activo tanto en HA como en ese
  Mac.
- Si Tailscale o el Mac no estan disponibles, el worker aparece offline.
- La reconstruccion local en HA sigue funcionando sin Tailscale.
- No se abre ningun puerto entrante en el Mac: todas las conexiones parten del
  worker hacia HA.

## 13. Seguridad y privacidad

- Token exclusivo por worker, revocable individualmente.
- Token fuera de Git, fuera de la imagen y cargado mediante secreto/variable
  local de Docker.
- ACL Tailscale limitada al servicio y puerto de workers.
- TLS de Tailscale/MagicDNS cuando se configure el endpoint definitivo.
- No aceptar nombres de archivo absolutos ni `..` en paquetes.
- Limite de tamano para snapshots y resultados.
- Lista cerrada de artefactos que HA permite instalar.
- Logs sin tokens, coordenadas completas innecesarias ni contenido de datos
  privados.
- Temporales y caches del Mac con permisos locales y politica de limpieza.
- Nunca incluir datos vivos en la imagen Docker exportable.

## 14. Fallos y recuperacion

| Situacion | Comportamiento esperado |
| --- | --- |
| Worker offline antes de empezar | El job permanece en cola o el usuario elige HA/otro worker. |
| Se pierde Tailscale durante el calculo | El worker sigue localmente y reintenta; HA marca desconectado tras timeout. |
| Se cancela el job | El worker detecta `cancel_requested`, detiene entre unidades seguras y no sube resultados parciales. |
| Cambian inputs en HA | HA rechaza el resultado por snapshot obsoleto. |
| Falla una fase | No se promociona ningun artefacto del paquete. |
| Falla la subida | Se reintenta de forma idempotente con el mismo `job_id`. |
| Resultado corrupto/incompatible | HA lo conserva solo para diagnostico acotado o lo elimina; mantiene el V0 anterior. |
| Dos workers consultan a la vez | Solo el worker asignado puede reclamar atomicamente el job. |
| Worker vuelve tras timeout | Reconcilia por `job_id`; no crea una segunda ejecucion automatica. |

## 15. Fases de implementacion

### Fase 0. Medir y cerrar requisitos

- Medir por separado las cuatro fases en HA, M1 y M5.
- Medir tamano real de inputs meteorologicos y outputs.
- Confirmar arquitectura Docker y espacio disponible en ambos Macs.
- Revisar licencias/atribucion de los tres datasets GIS/DEM.
- Decidir endpoint/puerto HA y politica Tailscale.

### Fase 1. Extraer el pipeline comun

- Mover la orquestacion de cuatro fases a `rainmapper_core`.
- Mantener el job HA actual usando ese modulo.
- Anadir cancelacion y un resultado/manifest independiente de la UI.
- Probar que el output HA antes/despues es equivalente.

Esta fase debe poder publicarse por si sola sin que exista aun ningun worker.

### Fase 2. Worker local por linea de comandos

- Crear `rainmapper-worker/` sin red.
- Ejecutar un snapshot local con rutas explicitas.
- Comparar artefactos y checksums semanticamente con la ejecucion HA/local.
- Verificar errores, cancelacion y limpieza de temporales.

### Fase 3. Imagen privada con GIS/DEM

- Construir imagen arm64 con capa GIS estable.
- Probar `docker save`/`docker load` entre M1 y M5.
- Validar GDAL/Rasterio y las rutas reales del dataset.
- Medir tamano de imagen/TAR, arranque, cache y reconstruccion completa.

### Fase 4. API de workers y Tailscale

- Implementar registro, heartbeat, claim, snapshot y subida de resultados.
- Crear tokens por worker y ACL.
- Probar siempre contra la URL Tailscale fija de HA.
- Anadir hashes, limites, compatibilidad y promocion atomica.

### Fase 5. UI y progreso persistente

- Mostrar workers y compatibilidad.
- Permitir elegir HA/M1/M5.
- Ampliar progreso con sincronizacion, ejecucion, subida y validacion.
- Hacer que estado/cancelacion sobrevivan a recargar la pagina.

### Fase 6. Prueba integral

- Ejecutar la misma reconstruccion en HA y Mac con un snapshot congelado.
- Comparar resultados normalizados.
- Probar worker offline, corte Tailscale, cancelacion, inputs modificados y
  resultado corrupto.
- Documentar instalacion privada del worker en ambos Macs.

## 16. Criterios de aceptacion

- HA y worker llaman al mismo pipeline de `rainmapper_core`.
- Las cuatro fases se ejecutan en el destino elegido y muestran progreso.
- El worker externo es materialmente mas rapido que HA con el mismo snapshot.
- Los resultados equivalentes producen la misma estructura y valores; si hay
  diferencias no deterministas, estan normalizadas y justificadas.
- Ningun dato vivo ni imagen del worker se publica en Internet.
- La imagen privada se puede transferir y ejecutar al menos en M1 y M5.
- GIS/DEM no se descarga en cada job.
- Cambiar datos en HA durante un job no instala resultados obsoletos.
- Un fallo o cancelacion conserva intactos los artefactos V0 anteriores.
- Si no hay worker, la reconstruccion HA continua disponible.
- La UI informa con claridad del destino, version, fase y estado del job.

## 17. Preguntas abiertas

1. Cual es el tiempo real de cada fase en HA, M1 y M5.
2. Que URL, puerto y mecanismo de exposicion usara la API privada del add-on en
   Tailscale.
3. Si Docker Desktop alcanza el tailnet del host sin sidecar.
4. Cuanto ocupan el snapshot vivo inicial y los deltas habituales.
5. Que historicos meteorologicos minimos necesita cada alcance de
   reconstruccion.
6. Tamano final de la imagen y del TAR tras compresion de capas.
7. Condiciones exactas de redistribucion/atribucion de DEM, MVC50 y geologia.
8. Si la primera version necesita reanudar jobs o basta con reintento completo.
9. Durante cuanto tiempo conservar historial, logs y paquetes fallidos en HA.
10. Como versionar conjuntamente worker, core, schema y manifest GIS sin
    acoplarlo al numero de version del add-on mas de lo necesario.

## 18. Siguiente paso cuando se retome

No empezar por Docker ni por Tailscale. El primer trabajo debe ser:

1. obtener tiempos de fase fiables y probar el M5;
2. extraer el pipeline comun manteniendo intacta la ejecucion HA;
3. demostrar con un snapshot local que HA y un CLI producen resultados
   equivalentes;
4. solo entonces crear la imagen pesada y el protocolo remoto.

Este orden reduce el riesgo principal: acabar manteniendo dos reconstructores
distintos o atribuir a la red/Docker una diferencia que en realidad proceda del
pipeline.
