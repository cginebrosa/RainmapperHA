# Plataforma privada de computo externo para reconstruccion y ML

Estado: **reconstruccion externa completa y parcial con promocion manual validadas en el laboratorio local; HA real/Tailscale pendientes**

Fecha inicial: 2026-07-18

Revision: 2026-07-20

Este documento define una plataforma privada para ejecutar fuera de Home
Assistant los calculos pesados del dominio de setas. El primer caso de uso sera
la reconstruccion completa V0 en un Mac M1 con Docker. La misma infraestructura
de snapshots, jobs, progreso, validacion y resultados debera admitir despues la
preparacion de datasets, el entrenamiento ML y la evaluacion de modelos.

La ruta del fichero conserva el nombre historico `mushroom-v0-external-worker`
para no romper referencias, pero el alcance vigente ya no se limita al V0 ni a
un Mac concreto.

La extraccion del pipeline, el CLI/snapshot, los contratos, el adaptador HA
opt-in, la imagen worker, la cache GIS versionada, el launcher portable y la
pantalla multi-worker ya existen y se han validado solo entre los dos
contenedores locales del M1. El protocolo incluye pairing, jobs candidatos,
inputs/resultados, sincronizacion GIS autenticada y transaccional y promocion
manual atomica. La ruta operativa solo esta habilitada en el Compose local y
admite reconstruccion completa, pendientes y una especie. Todavia no existe Tailscale ni se ha
habilitado el worker en HA real. Antes de continuar hay que releer este
documento y comprobar el estado del worktree, porque no se ha publicado este
prototipo en HA ni en ningun registry.

## Resumen para revision rapida

- Primera topologia: Home Assistant + M1. M5 y AWS quedan para mas adelante.
- HA conserva datos vivos, jobs y artefactos operativos aceptados; el worker es
  computo reemplazable con cache descartable.
- La imagen no contiene GIS/DEM ni otros datasets pesados semiestaticos. El
  worker los sincroniza desde HA a un volumen persistente versionado la primera
  vez y solo vuelve a descargarlos cuando cambia su manifest.
- La sincronizacion por HTTP autenticado ya esta implementada: ausencia,
  reutilizacion, cambio, fallo y espacio insuficiente se cubren con datasets
  sinteticos; una prueba real descargo los 6,3 GB a un volumen nuevo, los
  verifico profundamente y un segundo job los reutilizo con cero bytes.
- La reconstruccion HA sigue siendo fallback permanente.
- La UI local ya centraliza estado y controles en `Workers y trabajos`: detecta
  por heartbeat saliente los servicios de una red Docker privada, permite
  reconstruir en HA, ejecutar candidatos privados y, solo en el laboratorio,
  lanzar una reconstruccion externa completa o parcial y promocionarla manualmente. HA
  sigue disponible como fallback.
- Los accesos de reconstruccion desde el aviso de modelo desactualizado,
  Observaciones y modelo aprendido navegan a esta pagina con el alcance
  preseleccionado. Un ejecutor predeterminado persistente puede ser HA o un
  worker exacto; si no esta disponible o no soporta el alcance, se informa y se
  exige elegir otro destino, sin failover silencioso.
- Cancelacion cooperativa/forzada, limpieza de parciales, corte/reconexion de
  red, reintentos idempotentes, corrupcion, freshness y promocion con rollback
  estan cubiertos localmente. No sustituyen la prueba HA/Tailscale.
- La plataforma separa reconstruccion V0, dataset ML, entrenamiento y
  evaluacion para reutilizar datasets sin repetir calculos previos.
- HA y worker llaman a los mismos pipelines de `rainmapper_core`, con entradas
  y salidas explicitas.
- El worker inicia toda comunicacion, recibe snapshots inmutables y nunca
  escribe directamente en las rutas vivas de HA.
- Se evaluara Tailscale en el host frente a Tailscale dentro de Docker; la
  segunda opcion favorece portabilidad, pero debe probarse y respetar las
  politicas del equipo anfitrion.
- Una reconstruccion obsoleta se rechaza; un experimento ML puede conservarse
  como candidato historico, pero nunca se activa automaticamente.
- El orden sigue siendo medir HA/M1, extraer pipeline, demostrar equivalencia
  por CLI y solo despues abordar Docker, API, Tailscale y UI.

## 1. Motivo y alcance inicial

La reconstruccion completa ya funciona en Home Assistant, pero la Raspberry Pi
es sensiblemente mas lenta que un Mac:

- MacBook Pro M1 Pro: aproximadamente 40 segundos.
- Home Assistant/Raspberry Pi: 4 minutos y 44 segundos.
- El usuario estima que la fase GIS/DEM en HA consume por si sola alrededor de
  dos minutos. Esta ultima cifra aun debe medirse con los tiempos de fase del
  job, no tratarse como un dato confirmado.
- El M5 no forma parte de la primera implementacion y todavia no esta conectado
  a Tailscale por tratarse de un equipo de trabajo.

La primera topologia sera solo Home Assistant + MacBook Pro M1 Pro. El diseno
no debe impedir anadir mas adelante el M5, otro ordenador o una VM privada en
AWS, pero no se implementaran ni probaran esos destinos en la primera fase.

La finalidad es aprovechar computo externo cuando este disponible, sin eliminar
la reconstruccion local de HA ni crear implementaciones que puedan divergir.
Aunque el primer baseline ML sera ligero, la reconstruccion GIS/DEM y
meteorologica, la generacion de datasets, las validaciones cruzadas y futuras
busquedas de hiperparametros pueden justificar la misma estrategia.

## 2. Decisiones ya acordadas

1. Home Assistant seguira siendo la fuente de verdad de los datos vivos, del
   registro de jobs y de los artefactos operativos aceptados.
2. La reconstruccion local de HA se conservara siempre como alternativa.
3. El primer worker sera el M1. Ejecutara las cuatro fases completas, incluida
   GIS/DEM:
   1. reconstruccion GIS/DEM;
   2. contexto meteorologico;
   3. union de features V0;
   4. modelo aprendido V0.
4. HA y el worker usaran el mismo codigo Python del pipeline. No habra una
   copia del reconstructor dentro de `rainmapper-worker/`.
5. El worker tendra una imagen Docker propia y ligera, sin los 5,9 GB de
   GIS/DEM ni otros datasets pesados semiestaticos. Esos datos se sincronizaran
   desde HA y se conservaran en un volumen persistente versionado del worker.
6. Esa imagen no se publicara en GHCR ni en otro registro de Internet. Se
   construira y transferira de forma privada con `docker save`/`docker load`;
   el volumen de datos no forma parte de ese TAR y se sincroniza por separado.
7. El worker utilizara una direccion estable de Tailscale de HA, tambien cuando
   este en la misma LAN. Tailscale podra ejecutarse en el host o dentro del
   despliegue Docker del worker; ambas opciones se evaluaran antes de cerrar la
   topologia.
8. HA no localizara el Mac por IP ni abrira una conexion entrante hacia el.
   Sera el worker quien se registre, envie heartbeats y pregunte a HA si tiene
   trabajo.
9. La primera UI permitira elegir HA o M1 para la reconstruccion. Los trabajos
   ML podran dirigirse al M1 cuando anuncie la capacidad correspondiente. El
   equipo desde el que se abre el navegador no determina donde corre el job.
10. Observaciones, perfiles y catalogos forman parte de los datos vivos que el
    worker debe recibir. No basta con enviar solo los incrementales
    meteorologicos.
11. La plataforma separara al menos reconstruccion V0, construccion de dataset
    ML, entrenamiento y evaluacion. Entrenar de nuevo sobre un dataset ya
    congelado no debe repetir GIS/DEM ni meteorologia.
12. Un resultado externo nunca se escribe directamente en las rutas vivas de
    HA. El worker sube un paquete y HA decide si lo rechaza, lo conserva como
    candidato o lo promociona explicitamente.

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
                                  │ crea JobSpec + snapshot inmutable
                                  │
                         API privada de workers
                                  ▲
                                  │ polling/heartbeat saliente
                                  │ descarga inputs / sube progreso y resultado
                                  │
                     Docker rainmapper-worker
                     M1 en la primera implementacion
                                  │
                     runner comun de tipos de job
                                  │
                 volumen persistente de datasets versionados
                                  │
                  pipelines compartidos de rainmapper_core
                    │             │              │
              rebuild V0     dataset ML     train/evaluate
```

El navegador solo ordena el trabajo y consulta su estado. Cerrar la pestana o
abrir Rainmapper desde otro ordenador no debe interrumpir el job.

### 4.1 Destinos y tipos de ejecucion

**Home Assistant**

- El job actual se ejecuta en un thread/background job del add-on.
- Lee los datos persistentes de HA y escribe los artefactos V0 en HA.
- No depende de que ningun Mac ni Tailscale esten disponibles.
- Es el fallback permanente para la reconstruccion V0 operativa.
- No es obligatorio ejecutar en HA entrenamientos ML experimentales: pueden
  quedar en cola hasta que exista un worker compatible sin afectar al modelo
  activo.

**Worker externo M1**

- HA crea el job y congela un manifest de entrada.
- El worker elegido reclama el job por polling.
- Descarga los datos vivos necesarios y sincroniza desde HA cualquier dataset
  pesado requerido que no exista con el mismo manifest en su volumen.
- Ejecuta el pipeline comun correspondiente al tipo de job.
- Sube un paquete de resultados y sus checksums.
- HA valida el paquete y aplica la politica de aceptacion del tipo de job.

**Destinos futuros**

- El M5, otro Mac o una VM en AWS podran usar el mismo protocolo si anuncian
  versiones y capacidades compatibles.
- No se presupone que todos los workers tengan GIS/DEM ni todas las
  dependencias ML.
- La identidad logica y las capacidades del worker importan mas que la maquina,
  su IP o donde se ejecute Tailscale.

### 4.2 Flujo de datos y autoridad

```text
datos vivos HA -> snapshot_id -> contexto/dataset inmutable -> training runs
                                      │                         │
                                      └──── hashes/versiones ───┘

resultado worker -> validacion HA -> rechazado | candidato | promocionado
```

La cache del worker es descartable. Un modelo activo y su contrato de features
no pueden depender de que el M1 siga encendido ni de que conserve temporales.

## 5. Pipelines comunes con entradas y salidas explicitas

La coordinacion operativa usada por HA sigue dentro de
`start_mushroom_model_rebuild_job()` en
`rainmapper-app/app/web_server.py`. Los calculos viven en modulos comunes:

- `rainmapper_core/mushroom_gis_lab.py`;
- `rainmapper_core/mushroom_observation_context.py`;
- `rainmapper_core/mushroom_observation_features.py`;
- `rainmapper_core/mushroom_learned_model.py`.

El primer prototipo local del 2026-07-19 ya extrae la misma secuencia a:

```text
rainmapper_core/mushroom_rebuild_pipeline.py
```

Ese modulo expone una operacion del estilo:

```text
run_rebuild(inputs, outputs, scope, progress_callback, cancel_event)
```

Su firma local cubre ya:

- alcance: una especie, pendientes o todas;
- rutas de entrada y directorio temporal de salida;
- callbacks de fase, porcentaje, mensaje y tiempos;
- cancelacion cooperativa;
- resultado estructurado con contadores y tiempos;
- ausencia de dependencias HTTP, HTML o de la UI;
- ausencia de lecturas o escrituras implicitas en el store vivo de HA: todas las
  rutas de entrada y salida deben proceder del contrato del job.

Existen ya `InputManifest 0.1`, `JobSpec 0.1` y `ResultManifest 0.1`. Fijan
snapshot, hashes de inputs, fingerprint GIS, alcance, lista exacta de salidas y
hashes/tamanos del resultado. Los contadores declarados se contrastan con los
cuatro JSON principales antes de aceptar el paquete.

El prototipo incorpora tambien
`scripts/run-mushroom-rebuild-pipeline.py`. El CLI exige `--output-dir`, rechaza
solapamientos con inputs o `mushroom-data` vivo, no sobrescribe resultados
previos y tiene `--dry-run`. La primera ejecucion real leyo inputs locales y
escribio exclusivamente en un directorio temporal. `web_server.py` ya puede
usar este modulo mediante el flag local opt-in
`RAINMAPPER_MUSHROOM_REBUILD_PIPELINE=shared`; `legacy` sigue siendo el default
y ningun release HA se ha modificado.

### 5.1 Evidencia del primer run local aislado (2026-07-19)

Entorno: MacBook Pro M1, Python 3.11 del proyecto, GIS local `mushroom-GIS` de
7,1 GB, historicos `docker-data/Data` de 769 MB y datos vivos locales leidos en
modo de entrada. La salida temporal ocupo 1,9 MB.

| Fase | Tiempo |
|---|---:|
| GIS/DEM, 125 observaciones | 97,857 s |
| Meteorologia, 126 observaciones | 14,342 s |
| Features V0, 126 observaciones | 0,022 s |
| Modelo V0, 14 especies | 0,021 s |
| Total | 112,244 s |

Los hashes antes/despues confirmaron que los artefactos V0 vivos no cambiaron.
Los dos CSV fueron identicos byte a byte a la reconstruccion viva. Los tres
informes solo cambiaron en `Generated at`. Weather, features y modelo JSON solo
cambiaron en fechas y rutas de procedencia/salida. En GIS cambiaron tambien las
rutas de las capas y un unico muestreo DEM sin elevacion se represento como
`no_value` + cadena vacia en el artefacto vivo y `no_data` + `-9999` en el M1;
esta diferencia no se propago a CSV, features ni modelo.

Esto valida el encadenamiento y el aislamiento, pero no cierra aun la
integracion HA: hay que ejecutar despues HA mediante este mismo modulo.

### 5.2 Snapshot manifestado y comparacion automatica (2026-07-19)

Se incorporaron:

- `mushroom_rebuild_snapshot.py`, con `InputManifest 0.1`, copia atomica de
  inputs vivos/meteo, SHA-256 y verificacion antes/despues;
- `scripts/prepare-mushroom-rebuild-snapshot.py`, para crear/verificar snapshots
  privados fuera del repositorio;
- `mushroom_rebuild_comparison.py` y
  `scripts/compare-mushroom-rebuild-artifacts.py`, que comparan cuatro JSON,
  dos CSV y tres informes.

El snapshot real ocupo 106 MB: tres JSON y los cuatro incrementales
meteorologicos que consume V0. GIS/DEM no se duplico; diez archivos realmente
usados quedaron fijados mediante el fingerprint
`sha256:4aa3777e0f1c4d05c7788e464d87f4bcb952eaa40160701e49fda336445475f9`.
El snapshot completo recibio el ID
`sha256:3c3f9e27bae0e108a8b4bf4ac10cb5a7a8934025f0d1de2d6bf237cdff210e26`.

La reconstruccion desde ese snapshot produjo 125 resultados GIS, 126 filas de
weather/features y 14 modelos de especie:

| Fase | Tiempo |
|---|---:|
| GIS/DEM | 102,407 s |
| Meteorologia | 14,286 s |
| Features V0 | 0,021 s |
| Modelo V0 | 0,013 s |
| Total | 116,728 s |

El manifest siguio valido despues del run. Los nueve artefactos fueron
equivalentes tanto a los artefactos HA `0.2.207` como al primer run M1. La
normalizacion se limita a metadatos de fecha/ruta y al nodata que GDAL expresa
como `no_value` + vacio en HA o `no_data` + `-9999` en el Mac; sólo se aplica
cuando el estado declara expresamente que no existe elevacion. CSV y cualquier
valor de dominio se comparan estrictamente. Las pruebas del comparador confirman
que un cambio de dominio hace fallar la comparacion.

### 5.3 Integracion en una imagen HA local aislada (2026-07-19)

`web_server.py` puede despachar ahora al modulo comun cuando
`RAINMAPPER_MUSHROOM_REBUILD_PIPELINE=shared`. El valor por defecto es
`legacy`: no existe fallback automatico despues de un fallo parcial, porque
mezclar dos coordinadores en el mismo job seria inseguro; la reversibilidad se
hace seleccionando explicitamente el coordinador antes de arrancar.

El arnes local incorpora:

- `rainmapper-local/docker-compose.rebuild-test.yml`, con servicio e imagen
  propios, puerto `127.0.0.1:8102` y variable obligatoria
  `RAINMAPPER_REBUILD_TEST_RUNTIME`;
- `rainmapper-local/options.rebuild-test.json`, sin schedule, backfill ni
  descargas meteorologicas;
- materializacion atomica del snapshot a `share`, `tmp` y `config-www` privados.

El Compose resuelto no contenia ninguna ruta a `docker-data`. Monto el runtime
en `/share/rainmapper`, `mushroom-GIS` como read-only y QGIS bajo el `tmp`
aislado. La imagen se construyo desde el mismo Dockerfile HA y arranco como
Python 3.11.15/aarch64; la WebUI devolvio HTTP 200.

La llamada real a `start_mushroom_model_rebuild_job()` produjo:

| Fase | Tiempo |
|---|---:|
| GIS/DEM | 26,309 s |
| Meteorologia | 15,308 s |
| Features V0 | 0,022 s |
| Modelo V0 | 0,015 s |
| Suma de fases | 41,654 s |

El job termino como `complete`, marco `pipeline=shared` y devolvio 125
resultados GIS, 126 weather/features y 14 modelos. Los nueve artefactos fueron
equivalentes tanto a HA `0.2.207` como al run CLI desde snapshot. El manifest
siguio valido, QGIS se escribio solo en el runtime temporal y el contenedor/red
se retiraron sin `-v`. La imagen local no es aun una imagen de worker.

#### Publicacion transaccional, fallos y cancelacion

El adaptador `shared` no escribe los resultados de una fase directamente sobre
los artefactos aceptados. Cada job usa
`mushroom-data/.rebuild-staging/<job_id>` para generar los nueve artefactos de
GIS, meteorologia, features y modelo. En rebuilds parciales se copia primero al
staging el modelo vigente para conservar las especies no incluidas.

Solo despues de completar las cuatro fases se valida que existan las nueve
salidas y se promocionan. Antes de sustituirlas se guarda un rollback corto; si
falla cualquier sustitucion, se restauran todas las ya promocionadas. El estado
de especies pendientes se limpia unicamente despues de una promocion completa.
QGIS sigue siendo una salida auxiliar del runtime aislado, no uno de los nueve
artefactos operativos comparados.

Las pruebas unitarias del 2026-07-19 cubren:

- fallo en cada una de las cuatro fases sin promocion ni limpieza del estado
  pendiente;
- fallo inyectado en la tercera sustitucion y restauracion de todos los
  artefactos aceptados;
- rebuild parcial que parte del modelo vigente;
- cancelacion cooperativa, sin promocion y con limpieza del staging.

Se repitieron ademas dos casos dentro de la imagen HA local aislada:

| Caso | Punto alcanzado | Estado final | Artefactos aceptados |
|---|---|---|---|
| Fallo controlado | GIS/DEM completo; fallo al entrar en Meteorologia | `failed` | 9/9 equivalentes |
| Cancelacion | GIS/DEM al 1 % | `cancelled` (solicitud 202) | 9/9 equivalentes |

En ambos casos `.rebuild-staging` quedo sin ficheros de job. La cancelacion se
ofrece solo para `shared`; un job `legacy` devuelve 409 porque el coordinador
antiguo no tiene puntos de parada cooperativos seguros. La transicion a
promocion se marca bajo el mismo lock que la solicitud de cancelacion: una vez
iniciada deja de anunciarse como cancelable y una peticion tardia devuelve 409.
`legacy` continua como valor por defecto y no se ha cambiado ni publicado
ninguna version HA. La suite completa termino con 264 tests correctos.

Quedaran dos adaptadores finos:

- `web_server.py`: crea el job HA, muestra progreso y llama al pipeline comun;
- `rainmapper-worker/`: transporte, cache, autenticacion y llamada al mismo
  pipeline comun.

No se aceptara copiar las cuatro llamadas actuales al worker. Si cambia una
fase, HA y Mac deben recibir el cambio al actualizar el mismo paquete de codigo.

La plataforma general tendra ademas un runner que seleccione el pipeline por un
tipo de job versionado, conceptualmente:

```text
run_job(job_spec, input_dir, output_dir, progress_callback, cancel_event)
```

Ese runner solo despacha. Las reglas de dominio siguen en `rainmapper_core`, no
en el transporte ni en la API de workers.

### 5.4 JobSpec y ResultManifest reales (2026-07-19)

Se incorporaron:

- `rainmapper_core/mushroom_rebuild_contracts.py`;
- `scripts/run-mushroom-rebuild-job.py`, con `create-spec`, `verify-spec`,
  `run` y `verify-result`;
- pruebas de contrato, integridad, salidas incompletas y contadores
  incoherentes.

`JobSpec 0.1` no contiene rutas absolutas del host. Declara `job_id`,
`job_spec_id`, tipo/pipeline, `snapshot_id`, requisitos de dataset por
fingerprint, alcance con IDs exactos y las nueve rutas de artefacto permitidas.
El CLI recibe por separado donde esta materializado el snapshot y permite
sobrescribir la raiz GIS, igual que necesitara el futuro worker.

`ResultManifest 0.1` liga el resultado al `job_id`, `job_spec_id` y
`snapshot_id`; registra SHA-256, tamano y tipo de los nueve artefactos, tiempos
por fase y resumen. La validacion vuelve a derivar desde los JSON los recuentos
GIS, weather, features y especies, por lo que no confia solo en el resumen que
declara el proceso.

El run real desde el snapshot ya congelado produjo:

| Fase | Tiempo |
|---|---:|
| GIS/DEM | 100,495 s |
| Meteorologia | 14,141 s |
| Features V0 | 0,020 s |
| Modelo V0 | 0,013 s |
| Total | 114,671 s |

El resultado contenia 125 reconstrucciones GIS, 126 weather/features y 14
especies. El manifiesto verifico 9/9 artefactos y el comparador confirmo su
equivalencia con el run anterior desde snapshot. Dos copias manipuladas se
rechazaron expresamente: cambiar el `snapshot_id` genero mismatch tanto del
hash del `JobSpec` como del input; anadir un byte a `mushroom_model_v0.json`
dejo 8/9 artefactos validos y denuncio el tamano incorrecto. Los originales
permanecieron intactos bajo `/private/tmp`. La suite completa suma 269 tests.

### 5.5 Tipos de job previstos

**`rebuild_v0`**

- ejecuta GIS/DEM, meteorologia, features V0 y modelo descriptivo V0;
- puede correr en HA o en M1;
- su resultado representa el estado operativo vigente.

**`build_ml_dataset`**

- agrupa episodios por especie, `micro_area_id` y fecha;
- conserva contexto diario, cobertura y procedencia;
- genera un dataset inmutable con `dataset_id`, contrato de features y hashes;
- evita repetir esta fase para cada experimento de entrenamiento.

**`train_ml_model`**

- recibe un `dataset_id` ya construido y una especificacion cerrada de
  algoritmo, variables, particiones, hiperparametros y semilla;
- produce modelo candidato, metricas y manifest reproducible;
- no reconstruye GIS ni meteorologia.

**`evaluate_ml_model`**

- compara candidatos o ejecuta backtesting sobre datasets declarados;
- nunca sustituye por si solo el modelo activo.

Los nombres y versiones definitivos se fijaran al implementar. El contrato debe
permitir anadir tipos de job sin cambiar el protocolo de transporte.

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
- sincronizar y versionar en volumen los datasets pesados requeridos;
- preparar directorios temporales y cache local;
- validar que anuncia la capacidad requerida por el `job_type`;
- llamar al runner comun y al pipeline de `rainmapper_core` correspondiente;
- enviar progreso, logs acotados y estado de cancelacion;
- empaquetar, firmar mediante checksums y subir resultados;
- borrar temporales de forma segura al terminar.

No debe contener reglas de abundancia, calculos GIS, logica meteorologica,
seleccion de features ni logica de entrenamiento.

Cada worker anunciara al menos:

- `worker_id` y nombre visible;
- arquitectura, RAM y espacio disponible;
- version del agente, core y schemas soportados;
- manifests de datasets pesados presentes en el volumen, incluido GIS/DEM;
- tipos y versiones de job que puede ejecutar;
- runtime ML disponible cuando corresponda.

## 7. Imagen ligera y datasets pesados persistentes

### 7.1 Dataset actual inspeccionado

HA mantiene la copia autoritativa bajo `/media/rainmapper/mushroom-GIS/`. El
repositorio de trabajo contiene `mushroom-GIS-HA`, con un tamano aproximado de
5,9 GB:

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
RAINMAPPER_MUSHROOM_GIS_ROOT=/var/lib/rainmapper-worker/datasets/mushroom_gis_v0/current
```

HA generara un manifest versionado cuando se importe o sustituya un dataset
pesado. No se recalcularan hashes de los 5,9 GB en cada job. El manifest
incluira como minimo tipo y version de dataset, rutas relativas, tamanos,
SHA-256, tamano total, procedencia y metadata de licencia.

### 7.2 Contenido de la imagen

La imagen del worker no incluira GIS/DEM ni otros datasets pesados
semiestaticos. Contendra solamente:

- agente y runner del worker;
- `rainmapper_core` y codigo de pipelines;
- Python y dependencias de aplicacion;
- GDAL, Rasterio y otras librerias nativas;
- dependencias ML correspondientes a las capacidades anunciadas.

De este modo actualizar codigo o librerias no obliga a mover de nuevo los 5,9
GB. La imagen seguira teniendo un tamano relevante por sus dependencias nativas,
pero sera varios GB menor y comun para cualquier host de la misma arquitectura.

Los nombres del despliegue seran deliberadamente genericos y no codificaran la
maquina anfitriona:

- imagen: `rainmapper-worker:<version>`;
- servicio y contenedor: `rainmapper-worker`;
- volumen persistente: `rainmapper-worker-data`.

No se usaran nombres como `rainmapper-worker-m1` o `rainmapper-worker-m5`. La
misma imagen y el mismo Compose deben funcionar sin modificaciones en cualquier
host compatible; si alguna vez conviven dos instancias en un solo Docker se
distinguiran mediante el nombre del proyecto Compose, no creando variantes de
la imagen.

#### Primera imagen local validada (2026-07-19)

Se crearon `rainmapper-worker/Dockerfile`,
`rainmapper-worker/entrypoint.sh` y el arnes
`rainmapper-local/docker-compose.worker-test.yml`. La imagen resultante,
`rainmapper-worker:local-contract-test`, tiene estas propiedades comprobadas:

- `arm64/linux`, Python 3.11.15 y GDAL 3.10.3;
- 151.477.088 bytes, frente a 478.283.433 bytes de la imagen HA local;
- solo entrypoint, runner contractual y los diez modulos `rainmapper_core`
  requeridos por reconstruccion/snapshot/contratos;
- sin GIS/DEM, datos de setas, WebUI, servidor HA, FFmpeg, ExifTool ni el
  conjunto de dependencias Python de la app completa;
- proceso Python bajo UID/GID dedicado 10001:10001;
- snapshot, `JobSpec` y GIS montados read-only, unica escritura en
  `rainmapper-worker-data`;
- runtime con `network_mode: none` y `pull_policy: never`.

El mismo `JobSpec 0.1` real completo las cuatro fases dentro de la imagen:

| Fase | Tiempo |
|---|---:|
| GIS/DEM | 26,071 s |
| Meteorologia | 16,023 s |
| Features V0 | 0,020 s |
| Modelo V0 | 0,013 s |
| Total | 42,130 s |

Produjo 125 resultados GIS, 126 weather/features y 14 especies. El
`ResultManifest` verifico 9/9 artefactos y el comparador confirmo equivalencia
con el run anterior desde snapshot. El volumen ocupo 2,0 MB. Se elimino solo el
primer contenedor, se creo un segundo contenedor efimero con la misma imagen y
el mismo volumen y este volvio a verificar 9/9; por tanto, reemplazar el
contenedor no pierde resultados. La imagen y `rainmapper-worker-data` se
conservan localmente, sin contenedores worker activos.

Esa primera prueba aun montaba GIS desde el host en read-only. La seccion
siguiente documenta la prueba posterior que ya elimina ese montaje durante el
calculo.

### 7.3 Volumen persistente de datasets

Cada instalacion montara un volumen Docker privado, separado de la imagen:

```text
/var/lib/rainmapper-worker/datasets/
  mushroom_gis_v0/
    staging/
      <fingerprint>.<uuid>/
    versions/
      <fingerprint-1>/
      <fingerprint-2>/
    current -> versions/<fingerprint-2>
```

Reglas:

- en el primer arranque el worker puede registrarse sin GIS, pero no reclama o
  ejecuta un job que lo requiera hasta completar la sincronizacion inicial;
- compara el manifest requerido por HA con los datasets locales;
- si coincide, reutiliza el volumen sin descargar;
- si cambia, descarga a `staging` solo ficheros o bloques ausentes cuando sea
  posible, verifica tamanos/hashes y activa la nueva version atomicamente;
- nunca sobrescribe en sitio un dataset que pueda estar usando otro job;
- conserva la version anterior hasta que no existan jobs fijados a ella y se
  cumpla una politica de limpieza segura;
- un fallo, corte de red o falta de espacio mantiene intacta la version activa.

El volumen sobrevive a reinicios y reemplazos normales del contenedor. Antes de
sincronizar hay que reservar espacio para dataset activo, staging, version
anterior temporal, outputs y caches; la cifra inicial de 12-15 GB debe medirse
de nuevo con este esquema.

Los procedimientos de instalacion y actualizacion no usaran `docker compose
down -v`, `docker volume rm` ni limpiezas con `--volumes` sobre este despliegue.
Perder el volumen no pierde la fuente de verdad, pero obliga a descargar y
verificar de nuevo todos los datasets pesados.

#### Cache local implementada y validada (2026-07-19)

Se incorporaron `rainmapper_core/mushroom_worker_dataset_cache.py` y
`scripts/manage-mushroom-worker-datasets.py`. El entrypoint de la imagen admite
ahora `dataset sync-local`, `dataset verify [--deep]` y `dataset resolve`. La
implementacion:

- valida el `InputManifest 0.1`, su fingerprint y rutas relativas seguras;
- copia cada fichero a un staging unico calculando SHA-256 durante la escritura
  y comprueba que la fuente no cambia entre el `stat` anterior y posterior;
- escribe un manifest de cache, mueve staging a
  `versions/<fingerprint>` y solo entonces reemplaza `current` atomicamente;
- nunca sobrescribe una version existente; una coincidencia valida devuelve
  `reused` y solo reactiva el symlink;
- en uso normal valida manifest, fingerprint, existencia y tamanos; la opcion
  profunda recalcula todos los hashes cuando se necesita una auditoria;
- ante cualquier fallo elimina exclusivamente su staging y conserva intactos
  `current` y las versiones anteriores.

La primera sincronizacion local monto la fuente GIS del M1 en solo lectura y
copio al volumen los 10 ficheros declarados, 6.306.367.027 bytes, con fingerprint
`sha256:4aa3777e0f1c4d05c7788e464d87f4bcb952eaa40160701e49fda336445475f9`.
Una validacion profunda posterior fue valida. Repetir el mismo comando devolvio
`reused` inmediatamente y no volvio a copiar ni a calcular los 6,3 GB de
hashes.

Las pruebas con datasets pequenos cubren primera carga, reutilizacion sin
copia, activacion de una version nueva conservando la anterior, rechazo de
rutas inseguras y fallo inyectado durante una segunda copia. En el ultimo caso
`current` siguio apuntando a la version valida y staging quedo vacio.

El ejecutor contractual acepta `--worker-data-dir`: comprueba superficialmente
la cache activa, exige que su fingerprint sea el requerido por el `JobSpec` y
mantiene la verificacion profunda de los ficheros vivos del snapshot. Asi no
rehash los 6,3 GB GIS en cada job. Sin esa opcion conserva el comportamiento
anterior y verifica GIS profundamente.

Con la imagen `rainmapper-worker:local-dataset-cache-test`, conservada al cerrar
la prueba bajo la etiqueta estable `rainmapper-worker:local`, se lanzo despues
un contenedor nuevo con `network none`, snapshot y JobSpec read-only y el
volumen persistente, pero **sin montar la fuente GIS del host**. El resultado
fue:

| Fase | Tiempo |
|---|---:|
| GIS/DEM | 25,703 s |
| Meteorologia | 16,296 s |
| Features V0 | 0,019 s |
| Modelo V0 | 0,013 s |
| Total | 42,033 s |

Produjo 125 resultados GIS, 126 weather/features y 14 especies. El
`ResultManifest` valido 9/9 artefactos y el comparador confirmo 9/9 equivalentes
con la referencia. La imagen inspeccionada ocupa 151.492.749 bytes y el volumen
6.310.438.770 bytes, incluidos dataset, manifests y outputs. No quedan
contenedores worker activos. La suite completa del repositorio termino con 278
tests correctos.

Al cerrar el ensayo se consolido el estado local: la imagen vigente quedo como
`rainmapper-worker:local` y se retiraron las etiquetas worker temporales, el
arnes HA rebuild y las copias locales de imagenes GHCR. Docker conserva solo
`rainmapper-worker:local` y `rainmapperha:local-ha-ui`. La limpieza no afecto a
GHCR remoto ni al volumen; una validacion superficial posterior confirmo de
nuevo los 10 ficheros y 6.306.367.027 bytes de `mushroom_gis_v0`.

#### Encendido y apagado manual del servicio local (2026-07-19)

La misma imagen puede permanecer levantada como servicio headless mediante:

```bash
./mushroom_worker_start.sh
./mushroom_worker_stop.sh
```

El arranque usa `rainmapper-local/docker-compose.worker-local.yml`, crea o
reutiliza explicitamente `rainmapper-worker-data`, construye
`rainmapper-worker:local`, publica solo `127.0.0.1:8110` y espera a que
`/health` confirme que el servicio responde. Si el volumen aun no contiene el
dataset, el estado `needs_dataset` permite completar el arranque: el primer job
compatible lo descargara y persistira antes de calcular. El Compose tiene un
nombre de proyecto propio, por lo que no mezcla ni considera huerfano al
contenedor de la UI local.

El apagado ejecuta `docker compose stop`, nunca `down -v`: imagen, dataset,
manifests y resultados permanecen. El servicio atiende `SIGTERM` y la prueba
real termino como `Exited (0)`. Se comprobo ademas que el proceso Python corre
como UID 10001 y que Docker continua mostrando solo las dos imagenes esperadas:
`rainmapperha:local-ha-ui` y `rainmapper-worker:local`.

`http://127.0.0.1:8110/health` devuelve unicamente JSON de diagnostico con
version, estado `idle`/`busy`/`needs_dataset`, capacidades y resumen de cache.
El worker no tiene UI propia. Anuncia `job_api: candidate_rebuild_v0`: acepta
el ciclo inocuo, la entrega de inputs y reconstrucciones candidatas privadas,
pero no promociona reconstrucciones operativas.

La interfaz humana ya vive en la UI local de Rainmapper, no en el worker. Ambos
servicios comparten la red Docker externa `rainmapper-local-compute`; el worker
se registra de forma saliente en la UI, mientras el puerto `127.0.0.1:8110`
queda como diagnostico local. La pagina
`/mushrooms/workers` muestra HA y worker, version, capacidades, cache, ultima
comprobacion, alcance de reconstruccion y jobs recientes. La opcion HA reutiliza
el launcher existente; la opcion externa permanece visible y deshabilitada
hasta que exista el transporte real. Se probaron tanto `En espera` como
`Desconectado` con HTTP 200, sin ejecutar una reconstruccion ni modificar
artefactos vivos. Docker conserva exactamente las dos imagenes previstas.
El primer formulario heredaba el ancho global de los `input` y sus radios se
solapaban; se reemplazo por tarjetas seleccionables independientes para destino
y alcance. Pendientes queda deshabilitado si el contador es cero y el selector
de especie solo aparece al elegir ese alcance. La suite completa termino con
289 tests correctos.

La deteccion directa de un unico `/health` se sustituyo despues por el primer
protocolo outbound real, todavia local. El worker genera un `worker_id` opaco,
persiste identidad y nombre visible bajo `rainmapper-worker-data` y recibe desde
el script anfitrion el nombre de la maquina fisica. El arranque admite
`--name "Nombre visible"`; si no se indica, usa como propuesta el ComputerName
del Mac. Imagen y recreacion del contenedor conservan la identidad del volumen.

Cada dos segundos el worker envia a
`/api/mushrooms/workers/heartbeat` su ID, nombre visible, maquina fisica,
arquitectura, version, capacidades, estado y cache. La UI registra metadatos
estaticos solo cuando cambian y mantiene los heartbeats en memoria, evitando
escribir a disco en cada pulso. La pantalla renderiza una coleccion y admite
cero, uno o varios workers; un heartbeat obsoleto lo muestra desconectado.

La prueba real registro el nombre fisico detectado del M1, `aarch64`, cache
valida y estado `En espera`. Tras detener y recrear el contenedor con los
scripts normales reaparecio con el mismo ID opaco y nombre; esos valores reales
no se documentan ni versionan. La API esta deshabilitada por defecto y solo la habilita el Compose
local. El worker llama al contenedor `rainmapper-ha-ui` por
`rainmapper-local-compute`: esto no accede al HA real y funciona sin Tailscale.
Para HA real, que solo es accesible mediante el tailnet, seguira siendo
obligatorio Tailscale en el host o en el despliegue Docker. La UI se probo
ademas con dos identidades simultaneas y genero una tarjeta y un destino
independiente para cada una. Suite completa: 296 tests.

La primera cola persistente local se anadio despues como prueba vertical del
transporte. Cada tarjeta conectada ofrece `Probar asignacion`; HA guarda un
`worker_claim_probe` dirigido al `worker_id` exacto y el worker consulta
`/api/mushrooms/workers/jobs/claim` despues de cada heartbeat. El claim se
serializa bajo el mismo lock de HA: otro worker obtiene cola vacia y el mismo
job no puede reclamarse dos veces. La pagina muestra de forma persistente
`En cola` y `Reclamado`, tipo y worker de destino. Estos jobs no contienen
snapshot, no ejecutan el pipeline y no escriben ni promocionan artefactos del
modelo.

El recorrido entre los dos contenedores se valido realmente. Con el worker
encendido el job paso a `claimed`; apagado quedo `queued` en
`mushroom_worker_jobs.json`, y tras recrear el contenedor el mismo worker
conservo su identidad y lo reclamo automaticamente. En esa iteracion la API
seguia habilitada solo por el Compose local y no tenia aun autenticacion. El destino externo de
reconstruccion continua deshabilitado. Suite completa: 301 tests.

El destino del worker dejo despues de estar fijado en el Compose. El arranque
portable admite:

```bash
./mushroom_worker_start.sh --help
./mushroom_worker_start.sh \
  --name "Worker M1" \
  --rainmapper-url http://rainmapper-ha-ui:8100
```

La URL validada se guarda bajo
`rainmapper-worker-data/config/coordinator.json`; el token, si existe, se
guarda separado bajo `secrets/coordinator-token` y nunca aparece en el JSON ni
en la salida de diagnostico. Puede entregarse por stdin o fichero privado, no
como argumento visible. Los parametros presentes sustituyen su valor guardado;
los omitidos se recuperan del volumen.

Antes de arrancar, un contenedor efimero consulta
`/api/mushrooms/workers/ping` y comprueba que la URL responde como coordinador
Rainmapper compatible. Una URL nueva que no responda no se persiste ni
interrumpe un worker ya activo. Con terminal interactivo, el script explica el
problema y permite reintentar, cambiar URL/token o cancelar; sin terminal,
`--non-interactive` o una ejecucion automatizada fallan con instrucciones en
lugar de quedar bloqueados esperando entrada.

La prueba real guardo la URL del laboratorio, arranco y despues volvio a
arrancar sin pasar URL, recuperandola y validandola desde el volumen. Un destino
DNS inexistente se rechazo y la configuracion valida anterior permanecio. El
heartbeat y el claim inocuo siguieron funcionando despues de retirar
`RAINMAPPER_HA_URL` del Compose. `mushroom_lab_start.sh` muestra ahora por
separado la URL humana `http://127.0.0.1:8101/...` y la URL interna para el
worker `http://rainmapper-ha-ui:8100`, indicando que no son intercambiables.
Suite completa: 306 tests.

La primera UI calculaba conectado/desconectado solo al renderizar la pagina.
Aunque el servidor marcaba correctamente `disconnected` al superar el timeout,
una pestana ya abierta podia seguir mostrando `En espera` hasta pulsar
`Actualizar`. Se corrigio con un endpoint ligero
`/api/mushrooms/workers/status`: la pagina consulta cada dos segundos y
sustituye solo tarjetas, destinos e historial, sin recargar el formulario ni
perder alcance/especie seleccionados. Al volver a una pestana oculta fuerza una
comprobacion inmediata.

El margen original era 20 s sobre heartbeat de 5 s: toleraba aproximadamente
cuatro pulsos perdidos y evitaba falsos offline por jitter, pero resultaba lento
para el control manual local. La configuracion actual envia heartbeat cada 2 s
y caduca a los 5 s. No se usa heartbeat=timeout porque un unico retraso haria
parpadear el estado. Con uno o pocos workers la carga es despreciable y los
heartbeats sin cambios no escriben metadatos en disco; si algun dia hay muchos
workers se podra introducir long polling/backoff sin cambiar el contrato.

La prueba real arranco y detuvo el contenedor: el endpoint paso de `En espera`
a `Desconectado` 3,25 s despues de terminar la parada, segun la posicion del
ultimo heartbeat. El navegador puede sumar hasta los 2 s del siguiente poll.
El boton de asignacion desaparece al desconectar. Suite completa: 308 tests.

La cola inocua se amplio despues a un ciclo persistente con `lease`, token de
claim, confirmacion de inicio, control, finalizacion, cancelacion y reasignacion.
Una reasignacion solo es valida antes de `started_at` y revoca el token anterior;
una vez iniciado, hay que cancelar y crear un nuevo intento. Cada trabajo lleva
ademas un `work_key` independiente del worker. HA rechaza otro trabajo activo
con la misma clave, aunque apunte a otro worker; trabajos con alcance o snapshot
distintos tendran claves distintas y si podran ejecutarse en paralelo.

La cancelacion tiene dos niveles en `Workers y trabajos`: cooperativa y
forzada. El worker mantiene el supervisor y los heartbeats separados del
subproceso de calculo. La cooperativa termina en un punto seguro; la forzada
ordena al supervisor matar el subproceso si no responde. Si el contenedor
completo o su red estan caidos, HA no puede matar fisicamente un proceso en otra
maquina con este protocolo exclusivamente outbound: conserva la autoridad para
rechazar cualquier resultado tardio y debe mostrar el worker desconectado hasta
reconciliar. No se anadira acceso remoto a Docker como atajo implicito.

El recorrido real entre los dos contenedores comprobo `idle -> busy -> idle`,
finalizacion normal, cancelacion cooperativa y cancelacion forzada. Mientras el
primer probe estaba `running`, un segundo con el mismo `work_key` no se creo.
Las tres pruebas solo ejecutaron un temporizador en un subproceso: no tocaron el
pipeline, observaciones, GIS ni artefactos del modelo. Suite completa: 317 tests.

Estas pruebas demuestran cache, persistencia, coordinacion outbound y ejecucion
supervisada desacoplada de las rutas GIS del host. La entrega autenticada de
inputs reales se valido despues como se describe a continuacion.
`network_mode: none` pertenece solo al arnes aislado; el worker final tendra red
saliente hacia HA, directamente por el Tailscale del host o mediante el sidecar
que se evaluara mas adelante.

#### Entrega local autenticada de JobSpec y snapshot (2026-07-19)

La tarjeta de cada worker compatible ofrece ahora dos pruebas distintas:
`Probar asignacion` conserva el temporizador inocuo anterior y `Probar envio de
entradas` crea un `worker_snapshot_transport_probe`. La segunda congela en el
coordinador una copia privada e inmutable de los tres JSON vivos y los cuatro
incrementales meteorologicos, crea el `JobSpec 0.1` y encola un contrato que
solo contiene IDs, hashes, recuento, tamano y un endpoint relativo. No monta
`docker-data` en el worker ni entrega rutas absolutas del host.

El worker reclama el job por su canal outbound, confirma inicio y descarga
`job_spec.json`, `input_manifest.json` y solo los paths declarados en el
manifest. Cada GET exige tres pruebas simultaneas: Bearer permanente del
worker, `worker_id` y token de claim del job. El servidor vuelve a comprobar
asignacion/estado y limita cada path al bundle inmutable; el worker aplica
limites de tamano, copia a staging, calcula SHA-256 durante la descarga y solo
renombra al directorio persistente final despues de verificar el `JobSpec`, el
snapshot y la version GIS requerida. Un fallo elimina solo su staging
incompleto y no activa inputs ni resultados.

La prueba real entre `rainmapper-ha-ui` y `rainmapper-worker`, sin HA real,
Tailscale, Internet ni nueva version, transfirio y verifico 7 ficheros vivos
por 111.031.244 bytes. El worker reutilizo la cache GIS persistente exacta de
10 ficheros/6.306.367.027 bytes, termino `Input bundle verified` y dejo bajo su
volumen solo `job_spec.json`, manifest y entradas. No genero
`mushroom_model_v0.json`, no ejecuto ninguna fase y no modifico ni promociono
el modelo vivo. La UI mostro el progreso/resultado persistente. Suite completa:
329 tests.

Este paso demuestra el stream autenticado de los datos vivos, no todavia la
sincronizacion por red de una version GIS ausente o nueva. Si el fingerprint
requerido no esta en cache, el worker falla de forma segura. Sigue pendiente
anadir la descarga/activacion transaccional del dataset pesado desde el mismo
coordinador; cuando exista, solo se transferira al faltar o cambiar la version.

#### Reconstruccion candidata local end-to-end (2026-07-20)

La tarjeta del worker ofrece ahora `Probar reconstruccion candidata`. Esta
accion crea un `worker_candidate_rebuild` con `work_key` global por snapshot y
alcance, reutiliza exactamente el transporte autenticado anterior y mantiene
deshabilitado el destino externo del formulario de reconstruccion operativo.
Por tanto, la prueba no puede sustituir accidentalmente al fallback HA.

Tras verificar los inputs y la huella GIS, el supervisor lanza
`run-mushroom-rebuild-job.py` como subproceso. Las cuatro fases usan el pipeline
unico de `rainmapper_core`, escriben solo bajo `jobs/<job_id>/candidate` en el
volumen y publican progreso persistente. El uso de subproceso conserva la
cancelacion cooperativa/forzada ya definida para la cola: el servicio y los
heartbeats permanecen vivos mientras el calculo corre.

El worker valida localmente el `ResultManifest` y despues sube primero ese
manifest y a continuacion las nueve rutas exactas. Cada POST exige Bearer
permanente, `worker_id` y claim vigente. Rainmapper no confia en el resumen que
devuelve el worker: vuelve a validar identidad del job/snapshot, contrato de
artefactos, rutas, limites, tamanos y SHA-256; finaliza staging de forma atomica
y deriva el resultado de su propia copia verificada. No existe codigo de
promocion en este flujo. El paquete queda bajo
`.worker-candidate-results/<job_id>` para auditoria y comparacion.

La primera prueba real local transfirio/reutilizo 7 inputs por 111.031.244 bytes
y la cache exacta de 10 ficheros GIS/6.306.367.027 bytes. Completo las cuatro
fases, subio `ResultManifest` mas nueve artefactos y termino
`Candidate result verified`, con 9/9 validos y comparacion semantica
`equivalent`. El candidato ocupa aproximadamente 2,0 MB. Se calcularon las
huellas de los nueve artefactos vivos antes y despues: todas permanecieron
identicas. La tabla persistente muestra fecha/hora local de creacion y duracion
real calculada para cada trabajo. La pagina usa una presentacion compacta para
que pairing, tarjetas, controles y diez columnas de historial aprovechen mejor
el ancho y reduzcan el scroll vertical. Suite completa: 335 tests; validador: 0
errores y 11 warnings conocidos. UI y worker quedan encendidos.

Quedan fuera de esta evidencia la promocion operativa/freshness, los fallos
reales de red/corrupcion y la conexion Tailscale. Ninguno debe habilitarse
implicitamente por haber cerrado el roundtrip candidato local.

#### Sincronizacion GIS autenticada y condicional (2026-07-20)

El bundle inmutable declara ahora `dataset_id`, fingerprint, recuento y tamano
total. Si esa version no esta activa, el worker solicita cada path declarado a
`/api/mushrooms/workers/jobs/dataset`; cada GET vuelve a exigir Bearer,
`worker_id` y claim vigente. Rainmapper rechaza otro dataset, otra huella o un
path no incluido en el manifest autoritativo y nunca expone una ruta absoluta.

El stream se escribe directamente en el staging del volumen para no necesitar
otra copia temporal de 6,3 GB. Antes de pedir el primer byte se reserva el
tamano declarado mas 256 MiB de margen. Cada fichero queda limitado a 8 GiB y
el dataset a 16 GiB, se valida contra tamano y SHA-256 y solo despues se mueve a
`versions/<fingerprint>` y se activa `current` atomicamente. Un fallo limpia
solo su staging; la version previa sigue activa. Si la huella ya existe y es
valida, no se llama al endpoint y el resultado informa `reused` y cero bytes.

Las pruebas sinteticas cubren una cache vacia descargada por el canal
autenticado, reutilizacion sin ninguna peticion, cambio de version, fallo de red
sin alterar `current`, limpieza de staging y rechazo por espacio insuficiente
antes de descargar. El launcher espera a `/health`, por lo que un primer
arranque sin dataset queda correctamente en `needs_dataset` y puede recibir el
primer job en lugar de bloquearse esperando `/ready`.

La prueba real del M1 reutilizo la cache vigente de 10 ficheros y
6.306.367.027 bytes, fingerprint
`sha256:4aa3777e0f1c4d05c7788e464d87f4bcb952eaa40160701e49fda336445475f9`.
El trabajo termino `Input bundle verified` con
`dataset_cache_status: reused` y `dataset_transferred_size_bytes: 0`. No se
duplico el dataset ni se toco el modelo vivo. Suite completa: 340 tests;
validador de datos: 0 errores y 11 warnings conocidos.

No se ha hecho deliberadamente una descarga real completa de 6,3 GB a un
volumen Docker nuevo ni se ha cortado una transferencia real de ese tamano. La
semantica queda cubierta con datasets sinteticos, pero esas dos pruebas siguen
siendo necesarias antes de considerar portable el alta en otro host.

### 7.4 Primera sincronizacion y actualizaciones

El worker anuncia en heartbeat los `dataset_id` y hashes que conserva. Cada
`JobSpec` declara los datasets pesados requeridos.

```text
worker sin dataset -> sync completa -> verificacion -> activacion -> job
worker actualizado -> manifests iguales ---------------------------> job
worker desfasado   -> sync delta/full -> verificacion -> activacion -> job
```

La primera implementacion transfiere por separado los paths del manifest y
evita todos los GET si el fingerprint ya esta activo. Todavia no hace delta por
bloques dentro de un fichero monolitico: una version nueva vuelve a descargar
ese fichero completo. Ese refinamiento solo se incorporara si las mediciones de
actualizacion lo justifican. HA sigue siendo la fuente de verdad; el volumen es
una replica persistente y reconstruible.

### 7.5 Construccion y transferencia privadas de la imagen

Flujo base previsto; el roundtrip local ya se valido como se detalla abajo,
pero siguen pendientes el instalador y la importacion en otro host:

```bash
docker build -f rainmapper-worker/Dockerfile \
  -t rainmapper-worker:<version> .

docker save rainmapper-worker:<version> \
  -o rainmapper-worker-<version>.tar

# Copiar el TAR por un medio privado al host autorizado.

docker load -i rainmapper-worker-<version>.tar
```

El TAR no se anade a Git. Tampoco se publica en GHCR. Puede guardarse en un
disco local, NAS privado o transferencia directa entre equipos. `docker save`
y `docker load` transportan la imagen, no el volumen de datasets. Al instalar
el worker en otro host, ese host sincronizara desde HA o recibira una exportacion
privada del volumen gestionada por separado y validada contra el manifest.

Portabilidad significa que la imagen no se reconstruye, parchea ni configura
para M1, M5 o AWS. El paquete de instalacion usara un Compose generico y el alta
normal sera `docker load` seguido de `docker compose up -d`. En el primer
arranque el despliegue creara automaticamente `rainmapper-worker-data`, generara
una identidad nueva si no existe y descargara desde HA los datasets requeridos.

Copiar literalmente solo los bytes de la imagen no puede autorizar por si mismo
el acceso a HA: la nueva instalacion debe recibir como bootstrap la URL de HA y
un codigo temporal de pairing. Si se adopta Tailscale dentro del
despliegue, tambien necesitara su alta inicial. Esos secretos y el estado de
identidad nunca se incluyen en la imagen exportable. Son la unica configuracion
especifica de la instalacion; codigo, Compose, nombres, rutas internas y flujo
de arranque seran iguales en todos los hosts.

El usuario no tiene que editar `.env` en el flujo local actual. La base
del instalador vive en `mushroom_worker_start.sh`: ofrece `--help`, acepta URL,
nombre y codigo de pairing por stdin, valida antes de guardar, reutiliza la configuracion del
volumen y guia o cancela si falta o no es accesible. El paquete transferible a
otro host generalizara ese mismo comportamiento, sin cambiar el contrato, y:

1. comprueba Docker y que la imagen compatible esta cargada;
2. pregunta la URL de HA;
3. solicita un codigo temporal mostrado en `Workers y trabajos`, sin dejarlo en
   el historial del shell;
4. valida conectividad y credenciales antes de arrancar;
5. genera la configuracion local con permisos restrictivos;
6. crea o reutiliza `rainmapper-worker-data` y ejecuta
   `docker compose up -d`;
7. muestra identidad, estado y un diagnostico breve verificable desde HA.

No es necesario conocer el formato de un `.env` para arrancar el worker. La
automatizacion usa parametros y `--non-interactive`; reejecutar el arranque
conserva identidad, configuracion y volumen. Una URL nueva solo sustituye la
anterior despues de responder como coordinador compatible.

#### Pairing local autenticado (2026-07-19)

El Compose local activa `RAINMAPPER_WORKER_AUTH_REQUIRED=true`. La pantalla
central crea un codigo humano `XXXX-XXXX`, valido 10 minutos y utilizable una
sola vez; solo puede haber uno activo y generar otro invalida el anterior. El
worker envia ese codigo junto con su identidad opaca a
`/api/mushrooms/workers/pair`. HA responde una sola vez con un token aleatorio
exclusivo. El worker guarda el token bajo
`rainmapper-worker-data/secrets/coordinator-token`; HA guarda solo SHA-256 en
`mushroom_worker_credentials.json`. Ningun token aparece en health, JSON de
configuracion, argumentos, logs o Git.

Heartbeat, claim, start, control y finish exigen `Authorization: Bearer` y el
`worker_id` debe corresponder a la credencial. La UI indica
`Emparejado`/`No emparejado`, permite generar el codigo y revocar el token. Una
revocacion elimina el heartbeat y el registro visible, retira el worker de
tarjetas/selectores, restablece HA si era el predeterminado y obliga a repetir
pairing. El historial conserva el destino ya copiado en cada job. El flujo real
comprobo 401 sin token, pairing, ciclo inocuo autenticado completo y recreacion
sin volver a introducir codigo. Suite completa: 325 tests.

Si finalmente se integra Tailscale dentro del despliegue Docker, el mismo
instalador gestionara tambien ese alta sin exigir editar `.env`: preguntara si
se desea activar, usara un flujo de autorizacion interactivo o solicitara una
clave de alta de un solo uso sin eco, esperara a que la identidad quede activa
y comprobara que la API privada de HA sea alcanzable antes de dar la instalacion
por terminada. El estado de Tailscale vivira en un volumen privado persistente,
separado de la imagen, para que reinicios y actualizaciones no obliguen a
autenticar de nuevo.

#### Roundtrip local save/load (2026-07-19)

La imagen se etiqueto temporalmente como
`rainmapper-worker:local-portability-test` y se exporto a
`/private/tmp/rainmapper-worker-local-portability-test.tar`:

- tamano TAR: 151.497.216 bytes;
- SHA-256 TAR:
  `69a266478efdcdb45cb4e19afa928c5a10e917bb81a6745e9806bea4545829c2`;
- image ID antes de exportar:
  `sha256:d5fa400e1fc90c366a9efcbd3593d1560daa5404a74caceec51255e5741c64c1`.

Se retiro unicamente la etiqueta temporal, manteniendo intactas la etiqueta
`local-contract-test`, la imagen y `rainmapper-worker-data`. `docker load`
restauro la etiqueta desde el TAR con el mismo image ID, arquitectura arm64 y
tamano de imagen 151.477.088 bytes. La etiqueta restaurada arranco con
`--pull never` y `network none`, monto el volumen existente y verifico 9/9
artefactos sin reconstruir la imagen ni repetir el calculo.

Docker muestra dos medidas distintas para la misma imagen: `docker image
inspect` informa 151.477.088 bytes y el TAR transportable ocupa 151.497.216,
mientras `docker images` muestra 616 MB de almacenamiento local/desempaquetado.
La comparacion de portabilidad debe usar el TAR; la planificacion de disco del
host debe considerar la cifra local mayor.

Esta es una prueba de roundtrip/formato y arranque local. No demuestra aun una
importacion en daemon limpio o en otra maquina, porque la etiqueta original
conservo las capas locales. Esa comprobacion se hara al disponer de otro host o
mediante una prueba destructiva expresamente autorizada y recuperable desde el
TAR. El TAR permanece privado bajo `/private/tmp` y no se versiona ni publica.
La suite completa del repositorio termino con 272 tests correctos.

### 7.6 Arquitecturas de CPU

El M1 es `arm64`. Un futuro M5 tambien lo seria, pero una VM de AWS podria ser
`arm64` o `amd64`. Para soportar otra arquitectura habra que construir y
exportar una imagen especifica o un archivo OCI multiarquitectura. Esta
portabilidad no debe suponerse sin probar Rasterio/GDAL, librerias ML y el resto
de dependencias nativas en cada arquitectura.

### 7.7 Licencias y procedencia

Antes de sincronizar GIS/DEM a workers hay que revisar las condiciones de uso,
redistribucion y atribucion de cada fuente. Los datasets no se incluyen en la
imagen ni se publican. HA solo los entrega a workers privados autorizados; un
futuro host cloud debe cumplir las mismas condiciones.

## 8. Datos que viajan desde HA

El worker debe recibir un snapshot autocontenido de los datos vivos necesarios
y referencias inmutables a los manifests de datasets pesados requeridos. Los
datos vivos viajan con el job; los datasets pesados se sincronizan y persisten
por separado.

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
- los 5,9 GB GIS/DEM dentro del snapshot vivo de cada job; se sincronizan por el
  canal de datasets pesados solo cuando falta o cambia su manifest;
- archivos de log generales;
- otros datos privados sin relacion con el job.

### 8.3 Sincronizacion incremental de datos vivos

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

### 8.4 Snapshots, datasets y caches

- Cada conjunto de inputs congelado tendra un `snapshot_id` derivado de su
  manifest y hashes.
- El snapshot fijara tambien los `dataset_id` y hashes de los datasets pesados
  usados, aunque sus bytes residan en el volumen persistente del worker.
- Un dataset ML tendra un `dataset_id` propio y referenciara el `snapshot_id`,
  el contrato de features y el pipeline que lo genero.
- Distintos entrenamientos podran reutilizar el mismo `dataset_id` sin volver a
  descargar datos vivos ni ejecutar GIS/DEM y meteorologia.
- La cache por hash del worker es una optimizacion, nunca la unica copia de un
  dataset o modelo aceptado.
- HA conservara como minimo manifests, metricas, contrato de features y modelos
  candidatos/activos necesarios para auditoria. Antes de guardar historiales ML
  grandes bajo `/share` se evaluara su impacto en backups; los artefactos
  voluminosos podrian usar una ruta privada bajo `/media` o almacenamiento
  privado adicional, manteniendo en HA el indice y los hashes.

## 9. Protocolo de jobs

### 9.1 Identidad del worker

Cada instalacion tendra configuracion local no versionada:

- `worker_id` opaco y estable, generado en el primer arranque y persistido en
  `rainmapper-worker-data`;
- nombre visible;
- URL Tailscale fija de HA;
- token dedicado, revocable y distinto de cualquier token de usuario;
- capacidades: arquitectura, RAM, espacio libre, versiones del worker/core,
  tipos de job y runtime ML;
- manifests de datasets pesados presentes en su volumen, incluido GIS/DEM.

El `worker_id`, no su IP, nombre de contenedor ni modelo de Mac, identifica el
destino. Cambiar de Wi-Fi no crea un worker nuevo. El nombre visible puede ser
humano, por ejemplo `Mac M1`, pero no altera la imagen ni el Compose.

### 9.2 Secuencia

1. El worker hace `heartbeat` saliente a HA.
2. HA muestra el worker como disponible si el heartbeat es reciente y las
   versiones son compatibles; indica aparte si necesita sincronizar datasets.
3. El usuario elige tipo de job, alcance y destino compatible.
4. HA calcula un `work_key` desde tipo, alcance y huella del snapshot. Si ya hay
   trabajo activo equivalente, no crea otro; despues crea el `job_id`, fija
   alcance y construye el manifest de entrada.
5. El worker elegido consulta jobs y reclama el suyo mediante una operacion
   atomica con lease y token de claim.
6. Compara los datasets pesados requeridos con su volumen. Si falta alguno o su
   manifest no coincide, comprueba espacio, lo sincroniza, valida y activa.
7. Descarga el snapshot de datos vivos, valida hashes y confirma que puede
   empezar.
8. Confirma el inicio, ejecuta las fases declaradas en un subproceso supervisado
   y publica progreso.
9. Consulta entre unidades de trabajo si HA ha solicitado cancelar.
10. Empaqueta solo los artefactos permitidos y sube resultados/checksums.
11. HA valida compatibilidad y que el snapshot fuente siga vigente.
12. HA rechaza el paquete, lo registra como candidato o promociona
    atomicamente sus artefactos segun la politica del tipo de job.
13. El worker limpia temporales; HA conserva un resumen acotado del job.

### 9.3 Estados minimos

```text
queued
claimed
syncing_static_inputs
syncing_job_inputs
running
uploading_results
validating
candidate
complete
rejected_stale
cancel_requested
cancelled
failed
worker_disconnected
```

`worker_disconnected` no significa automaticamente que el proceso haya
fallado. Debe existir un timeout claro y una reconciliacion si el worker vuelve
a conectarse.

`cancel_requested` incluye `cancel_mode: cooperative|force`. El modo forzado
mata el subproceso de calculo si el supervisor sigue accesible. Si se pierde el
worker completo, HA puede cercar el job e impedir aceptar resultados, pero no
puede matar remotamente el contenedor sin un canal de administracion adicional.

### 9.4 Progreso

Se reutilizaran los callbacks incrementales que ya existen en las cuatro fases.
El worker enviara como minimo:

- tipo de job, fase e indice de fase;
- porcentaje de fase y total;
- unidad actual/total cuando exista;
- bytes/archivos transferidos durante sincronizacion de datasets y del job;
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

Los artefactos ML previstos incluyen dataset diario, matriz de entrenamiento,
modelo candidato y evaluacion, tal como define
`mushroom-ml-training-plan-es.md`.

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
- para entrenamiento: `dataset_id`, especie/objetivo, contrato de features,
  algoritmo, hiperparametros, semilla, particiones, distribucion de clases,
  baseline y metricas.

La frescura se trata de forma distinta segun el resultado:

- `rebuild_v0`: si cambia cualquier input relevante, HA rechaza la promocion
  porque el artefacto pretende representar el estado operativo actual;
- `build_ml_dataset`: el dataset sigue siendo reproducible respecto a su
  snapshot, pero se marca si ya no corresponde al estado vivo;
- `train_ml_model` y `evaluate_ml_model`: el experimento puede conservarse como
  candidato historico ligado a su `dataset_id`, aunque hayan cambiado los datos
  vivos; nunca se activa automaticamente.

La promocion sera atomica: guardar paquete, validar, hacer backup corto de los
artefactos vigentes y sustituirlos como una unidad. Un fallo no puede dejar una
mezcla de fases nuevas y antiguas.

El adaptador HA local `shared` ya aplica esta regla a los nueve artefactos V0:
staging por job, comprobacion de salidas, backup corto, sustitucion y rollback
si una operacion falla. La futura recepcion de resultados externos debera
reutilizar esta semantica, ampliandola con `ResultManifest`, hashes y las
validaciones de compatibilidad anteriores.

Para V0 se esperan artefactos normalizados equivalentes entre HA y M1. Para ML
no se exigira igualdad binaria entre maquinas o versiones de librerias si la
serializacion no es determinista; se exigiran entorno versionado, semillas,
predicciones y metricas reproducibles dentro de tolerancias documentadas.

## 11. Integracion en la UI

La primera iteracion local ya esta implementada como una pantalla central
`Workers y trabajos`, accesible desde el resto de pantallas de setas y el panel
principal. No se ha anadido UI al contenedor headless. La pantalla detecta el
worker real por `/health`, conserva HA como destino funcional y muestra el
destino externo deshabilitado con una explicacion honesta cuando no es
compatible. La misma pagina permite ejecutar pruebas candidatas privadas en
workers compatibles y, solo en el laboratorio, promoverlas manualmente. Los
accesos contextuales ya no lanzan jobs: abren esta pantalla con `todas`,
`pendientes` o `una especie` preseleccionado, de modo que existe una unica
entrada visible y no una segunda implementacion de reconstruccion.

El ejecutor predeterminado se persiste en el registro privado como
`home_assistant` o `worker:<worker_id>`. Solo determina la preseleccion. Si el
worker esta desconectado, no emparejado, no anuncia una API operacional o no
admite el alcance, no se selecciona HA automaticamente: la pagina muestra el
problema, deshabilita el envio y exige una eleccion manual. Actualmente HA y el
worker externo operacional del laboratorio admiten `todas`, `pendientes` y
`una especie`.

Cuando el transporte este listo, el selector existente pasara a permitir:

```text
Ejecutar en:
  Home Assistant
  MacBook M1       disponible · worker/core X · GIS Y
```

Reglas:

- HA siempre aparece como opcion.
- La primera version solo muestra HA y M1. Otros destinos se incorporaran
  cuando existan realmente y superen las mismas comprobaciones.
- Un worker incompatible, sin heartbeat reciente o sin espacio suficiente se
  muestra deshabilitado y explica el motivo.
- Un worker compatible que necesita sincronizar GIS/DEM puede seleccionarse,
  pero la UI muestra version requerida, descarga pendiente y tamano estimado.
- No se cambia automaticamente de worker sin informar al usuario.
- Si el destino desaparece antes de reclamar el job, se puede cancelar, esperar
  o elegir HA; no se debe ejecutar dos veces sin saberlo.
- Solo un worker reclama cada job.
- Un `work_key` activo solo puede tener un job, con independencia del worker de
  destino. Alcances o snapshots diferentes generan claves distintas.
- Antes de empezar puede reasignarse y se revoca el claim anterior. Despues de
  empezar, la alternativa segura es cancelar y crear un nuevo intento.
- La UI de progreso debe mostrar tipo de job, destino, sincronizacion, fases de
  calculo, subida y validacion.
- Los resultados ML se muestran primero como runs/candidatos con dataset,
  metricas y advertencias; activar un modelo es otra accion explicita,
  confirmada y reversible.
- Mas adelante se puede anadir seleccion automatica del worker mas rapido, pero
  no es necesaria en la primera version.

## 12. Tailscale

### 12.1 Direccion unica de HA

La configuracion persistente del worker usara una URL estable de Tailscale para
HA, por ejemplo conceptualmente:

```text
https://homeassistant.<tailnet>.ts.net:8100
```

El listener del add-on es `8100/tcp`; Home Assistant permite asignarle otro
puerto host si fuera necesario. La URL elegida debe ser estable dentro y fuera
de casa. No se intentara detectar si conviene una IP LAN distinta.

Esto se refiere a la comunicacion worker-HA. El usuario puede abrir la UI de HA
por la ruta que use habitualmente; el navegador no transporta el job.

### 12.2 Servicio accesible

El add-on incorpora una API de worker autenticada en un listener dedicado
`8100`, separado de web/Ingress `8099`. `8100/tcp` no se publica por defecto:
hay que asignarlo expresamente en HA y restringirlo mediante ACL de Tailscale.
El listener solo acepta las rutas exactas del protocolo y exige Bearer salvo el
ping de descubrimiento/pairing. El navegador no usa este puerto.

### 12.3 Dos modos de despliegue

**Tailscale en el host**

- el contenedor usa el tailnet ya conectado del Mac;
- es sencillo para el M1 si Docker Desktop enruta correctamente MagicDNS/IP de
  Tailscale;
- liga la disponibilidad del worker a la configuracion del host.

**Tailscale dentro del despliegue Docker**

- un sidecar o proceso de red aporta una identidad Tailscale propia al worker;
- la identidad, configuracion y despliegue viajan juntos y dependen menos del
  ordenador anfitrion;
- facilita mover el worker a otro Mac o a una VM en AWS;
- requiere probar red compartida entre contenedores, persistencia del estado de
  Tailscale, renovacion/revocacion y los permisos de red que admita Docker
  Desktop;
- el token de enrolamiento solo se usa para el alta y nunca se incluye en la
  imagen ni en el TAR;
- el instalador interactivo realiza el alta, persiste el estado en un volumen y
  valida la conexion a HA; `.env` queda solo como alternativa avanzada.

Tailscale dentro de Docker es la opcion preferente a evaluar para portabilidad,
no una decision tecnica cerrada. No se elegira hasta realizar un spike minimo
despues de demostrar el pipeline por CLI. En un Mac de trabajo tambien se debe
confirmar que la politica del equipo permite Docker y ese uso de red: no se
asume que ejecutar Tailscale dentro de un contenedor evita las restricciones de
la organizacion.

### 12.4 Identidad portable

- La identidad Tailscale pertenece a la instalacion del worker, no al modelo
  fisico del Mac.
- Su estado persistente vive en un volumen privado y no dentro de la imagen.
- Clonar una imagen o TAR no debe clonar automaticamente la identidad ni el
  token del M1.
- Mover la imagen a otro host crea una nueva identidad Tailscale durante el
  instalador; no se copia silenciosamente la identidad de la maquina anterior.
- El primer arranque genera el `worker_id`; cada despliegue futuro, incluido M5
  o AWS, tendra credenciales y permisos revocables propios.

### 12.5 Futuro worker en AWS

Una VM en AWS podria ejecutar el mismo protocolo y una imagen compatible. No
forma parte de la primera implementacion. Si se incorpora:

- se conectara de forma saliente al tailnet y no expondra una API publica;
- no se abriran puertos entrantes generales en el security group;
- datos, caches, snapshots y discos seguiran siendo privados y cifrados;
- se mediran costes de computo, almacenamiento y transferencia antes de dejarla
  persistente;
- la instancia se identificara por capacidades/versiones, no por una IP fija.

### 12.6 Disponibilidad

- Para ejecutar externamente, HA y el despliegue del worker deben estar
  conectados al tailnet, ya sea desde el host o desde Docker.
- Si Tailscale o el Mac no estan disponibles, el worker aparece offline.
- La reconstruccion local en HA sigue funcionando sin Tailscale.
- No se abre ningun puerto entrante en el Mac: todas las conexiones parten del
  worker hacia HA.

## 13. Seguridad y privacidad

- Token exclusivo por worker, revocable individualmente.
- La API queda apagada por defecto; la autenticacion queda requerida por
  defecto y el modo operacional solo puede activarse si ambas condiciones son
  efectivas. Los tres flags solo estan activos en el Compose del laboratorio.
- Token fuera de Git, fuera de la imagen y cargado mediante secreto/variable
  local de Docker.
- Credenciales y estado de Tailscale fuera de la imagen exportable.
- ACL Tailscale limitada al servicio y puerto de workers.
- TLS de Tailscale/MagicDNS cuando se configure el endpoint definitivo.
- No aceptar nombres de archivo absolutos, no normalizados ni `..` en paquetes;
  snapshots y ficheros GIS se resuelven dentro de su raiz y se vuelve a
  comprobar la huella completa del manifest.
- Limite de tamano independiente para JSON del protocolo (64 KiB), snapshots,
  datasets y resultados.
- Lista cerrada de artefactos que HA permite instalar.
- Antes de promocionar, HA elimina referencias auxiliares del worker y rebasa
  metadatos de rutas hacia las rutas autoritativas del coordinador para no
  persistir paths privados del host externo.
- Logs sin tokens, coordenadas completas innecesarias ni contenido de datos
  privados.
- Temporales y caches del Mac con permisos locales y politica de limpieza.
- Nunca incluir datos vivos en la imagen Docker exportable.
- Nunca incluir datasets pesados privados ni sus credenciales de sincronizacion
  en la imagen Docker exportable.
- Un worker solo puede reclamar tipos de job y alcances que HA le haya
  autorizado y que haya anunciado como capacidad.
- Ningun resultado ML se convierte en modelo activo por el mero hecho de haber
  terminado correctamente.
- Un futuro host cloud debe cumplir las mismas restricciones y no convierte los
  snapshots privados en datos publicables.

## 14. Fallos y recuperacion

| Situacion | Comportamiento esperado |
| --- | --- |
| Worker offline antes de empezar | El job permanece en cola o el usuario elige HA/otro worker. |
| Se pierde Tailscale durante el calculo | El worker sigue localmente y reintenta; HA marca desconectado tras timeout. |
| Se cancela el job | El worker detecta `cancel_requested`, detiene entre unidades seguras y no sube resultados parciales. |
| El calculo se cuelga pero el supervisor responde | La cancelacion forzada mata el subproceso de calculo y el worker confirma `cancelled`. |
| Se cuelga o desconecta el contenedor completo | HA cerca el job y rechaza resultados tardios; sin canal de administracion remoto no puede matar fisicamente el proceso del otro host. |
| Falla la sincronizacion de un dataset pesado | No se activa el staging ni empieza el calculo; el volumen conserva la version anterior. |
| No hay espacio para dataset + staging | El worker rechaza el claim/inicio con diagnostico y HA mantiene disponible el fallback local cuando aplique. |
| Cambian inputs durante `rebuild_v0` | HA rechaza la promocion por snapshot obsoleto. |
| Cambian inputs durante un experimento ML | HA puede conservarlo como candidato historico ligado a su snapshot, pero no activarlo automaticamente. |
| Falla una fase | No se promociona ningun artefacto del paquete. |
| Falla la subida | Se reintenta de forma idempotente con el mismo `job_id`. |
| Resultado corrupto/incompatible | HA lo conserva solo para diagnostico acotado o lo elimina; mantiene el V0 anterior. |
| Dos workers consultan a la vez | Solo el worker asignado puede reclamar atomicamente el job; el token/lease anterior queda invalidado al reasignar. |
| Se solicita dos veces trabajo equivalente | El `work_key` global impide el segundo job mientras el primero siga activo. |
| Worker vuelve tras timeout | Reconcilia por `job_id`; no crea una segunda ejecucion automatica. |

## 15. Fases de implementacion

### Fase 0. Medir y cerrar requisitos

- Medir por separado las cuatro fases en HA y M1.
- Medir tamano real de inputs meteorologicos y outputs.
- Medir por separado coste de construir dataset y de entrenar el baseline.
- Confirmar arquitectura Docker y espacio disponible en el M1.
- Medir transferencia inicial de GIS/DEM, estructura de archivos y viabilidad
  de sincronizacion por fichero/bloque.
- Revisar licencias/atribucion de los tres datasets GIS/DEM.
- Inventariar las rutas implicitas que hoy usan las cuatro fases.

El M5 y AWS quedan fuera de estas medidas iniciales.

### Fase 1. Extraer el pipeline comun

- Mover la orquestacion de cuatro fases a `rainmapper_core`.
- Mantener el job HA actual usando ese modulo.
- Hacer explicitas todas las rutas de entrada y salida.
- Anadir cancelacion y resultado estructurado independiente de la UI.
- Probar que el output HA antes/despues es equivalente.

Esta fase debe poder publicarse por si sola sin que exista aun ningun worker.

Estado 2026-07-19: prototipo local creado con rutas explicitas, progreso,
cancelacion y resultado estructurado. El adaptador HA local ya lo usa mediante
flag opt-in y dio 9/9 artefactos equivalentes; `legacy` sigue siendo el default.
Fallos de las cuatro fases, rollback de promocion y cancelacion quedaron
cubiertos; los casos reales de fallo tras GIS y cancelacion durante GIS
conservaron 9/9 artefactos y limpiaron staging. Esta fase queda completada en
local. Sigue pendiente decidir expresamente cualquier cambio de default antes
de un release.

### Fase 2. Contratos y CLI local

- Definir `JobSpec`, `InputManifest` y `ResultManifest` versionados.
- Crear un CLI/runner local sin red.
- Ejecutar un snapshot local con rutas explicitas.
- Comparar artefactos y checksums semanticamente con la ejecucion HA/local.
- Verificar errores, cancelacion y limpieza de temporales.

Estado 2026-07-19: CLI local, aislamiento, cancelacion, `InputManifest 0.1`,
snapshot inmutable y comparador normalizado completados. Un run repetido desde
snapshot dio 9/9 artefactos equivalentes a HA `0.2.207`; el adaptador HA local
ya invoca el mismo pipeline y sus temporales se verificaron en exito, fallo y
cancelacion. `JobSpec 0.1` y `ResultManifest 0.1` se probaron despues con otro
run real 9/9 valido y con manipulaciones rechazadas. Esta fase queda completada
en local.

### Fase 3. Imagen ligera y volumen de datasets

- Construir imagen arm64 sin GIS/DEM ni datasets pesados.
- Probar `docker save`/`docker load` y ejecucion reproducible en el M1.
- Crear el volumen persistente versionado y el resolver de `current`.
- Implementar sincronizacion completa desde HA, staging, hashes y activacion
  atomica; despues optimizar deltas si la medicion lo justifica.
- Validar GDAL/Rasterio contra las rutas del volumen.
- Probar que reemplazar la imagen conserva el volumen y que un host nuevo puede
  reconstruirlo desde HA.
- Medir tamano de imagen/TAR, volumen, descarga inicial, actualizacion y
  reconstruccion completa.

Estado 2026-07-19: imagen arm64 minima construida y validada sin red, 151,5 MB,
job real 42,130 s y 9/9 equivalente. Un segundo contenedor verifico el mismo
resultado desde `rainmapper-worker-data`, por lo que la persistencia basica esta
demostrada. El roundtrip local `docker save/load` restauro el mismo image ID y
reutilizo el volumen 9/9; queda pendiente repetirlo en daemon limpio/otro host.
La cache GIS versionada ya sincronizo y valido profundamente los 10 ficheros y
6.306.367.027 bytes, reutilizo la misma huella sin recopia y ejecuto otro job
sin montar GIS del host en 42,033 s con equivalencia 9/9. La sincronizacion
desde el coordinador ya esta implementada y los tests cubren primera carga,
reutilizacion sin GET, sustitucion, espacio y fallo seguro. Una prueba real
posterior partio del volumen aislado vacio
`rainmapper-worker-data-fresh-validation-20260720`, transfirio realmente los 10
ficheros/6.306.367.027 bytes, supero verificacion profunda y los reutilizo en
un segundo job con cero bytes. El contenedor temporal quedo detenido y ambos
volumenes se conservaron. Siguen pendientes una actualizacion real a otra
version y repetir el ensayo en otro host/daemon.

### Fase 4. API de workers y transporte Tailscale

- Implementar registro, heartbeat, claim, snapshot y subida de resultados.
- Crear tokens por worker y ACL.
- Probar siempre contra la URL Tailscale fija de HA.
- Anadir hashes, limites, compatibilidad y promocion atomica.
- Comparar Tailscale en el host con sidecar dentro de Docker y elegir el modo
  inicial con evidencia de red, permisos y portabilidad.

Estado 2026-07-20: identidad, registro multi-worker y ciclo outbound persistente
estan completados entre los dos contenedores locales.
Incluye claim con lease/token, inicio, estado `busy`, control, finalizacion,
cancelacion cooperativa/forzada, reasignacion solo antes de empezar y exclusion
global por `work_key`. Tanto el calculo inocuo como el candidato real corren en
subproceso supervisado. `worker_snapshot_transport_probe` entrega por HTTP
autenticado el `JobSpec` y los 7 inputs vivos; `worker_candidate_rebuild`
ejecuta las cuatro fases, publica progreso y devuelve `ResultManifest` mas nueve
artefactos por uploads autorizados. La prueba real termino 9/9 `equivalent` sin
modificar las nueve huellas vivas. El pairing local ya emite credenciales
exclusivas, guarda solo hashes en HA y protege heartbeat/claim/ciclo de jobs; el
endpoint continua desactivado por defecto fuera del arnes. Despues se probaron
dos cancelaciones reales durante GIS/DEM, una cooperativa y otra forzada, sin
alterar el modelo y sin dejar candidato/progreso/logs parciales. Otro candidato
sobrevivio a un corte y reconexion de la red Docker y termino verificado 9/9;
las llamadas idempotentes reintentan fallos transitorios dentro de una ventana
acotada. Tests aislados rechazan resultado corrupto e inputs
modificados/freshness. Tailscale sigue pospuesto hasta llevar este mismo
contrato a la red real.

Consolidacion posterior del 2026-07-20: autenticacion fail-closed, modo
operacional condicionado a API+auth, rutas de snapshot/GIS confinadas, huella
del manifest revalidada, JSON del protocolo limitado a 64 KiB y metadatos de
promocion rebasados a paths autoritativos. Despues se separaron web/Ingress
`8099` y protocolo privado `8100`, se incorporaron dos interruptores HA seguros
por defecto y los controles humanos quedaron limitados al Ingress autenticado.
Una sonda desde el contenedor worker comprobo que alcanza `8100`, que el host no
lo publica y que ambos listeners rechazan rutas ajenas. El proceso antiguo no
se reinicio para conservar sus jobs y mantiene `:8099` en memoria hasta que el
launcher ejecute la migracion preparada. Suite completa: 369 tests; validador:
0 errores/11 warnings conocidos. Sigue abierta para P1 la publicacion privada
real de HA y sus ACL/TLS antes de cualquier release.

### Fase 5. UI y progreso persistente

- Mostrar workers y compatibilidad.
- Permitir elegir HA/M1 en reconstrucciones y solo destinos compatibles en los
  demas tipos de job.
- Ampliar progreso con sincronizacion, ejecucion, subida y validacion.
- Hacer que estado/cancelacion sobrevivan a recargar la pagina.

Estado 2026-07-20: iteracion local candidata completada. Existe la pagina
central, deteccion conectado/desconectado, tarjetas de HA/worker, controles de
alcance e historial persistente. Los probes muestran cola, claim, ejecucion,
cancelacion y finalizacion; permiten cancelar, forzar cancelacion y reasignar
solo antes de empezar. La misma pantalla genera codigos de pairing, muestra el
estado autenticado y permite revocar una credencial. La prueba candidata muestra
progreso de inputs, cuatro fases, upload y validacion persistente. La seleccion
externa operativa esta habilitada solo en `rainmapper-local/docker-compose.yml`
mediante `RAINMAPPER_WORKER_OPERATIONAL_ENABLED=true`; default y HA real siguen
deshabilitados. El primer flujo externo se valido con
`Todas las especies elegibles` y despues se habilitaron `Pendientes` y
`Una especie`. El job operativo local completo tardo 49 s,
fue 9/9 equivalente y mantuvo las huellas vivas intactas hasta pulsar la
promocion manual. Esta revalido contrato/freshness, sustituyo las nueve rutas de
forma atomica, conservo la copia anterior bajo `.worker-promotion-backups`,
persistio un recibo y limpio pendientes despues del exito. Las copias de
promocion no crecen indefinidamente: se conservan como maximo las dos mas
recientes, unos 2 MB cada una, y las anteriores solo se podan despues de una
promocion completada. No contienen GIS/DEM.

La promocion parcial no instala directamente el candidato reducido. Rainmapper
vuelve a cargar los nueve artefactos vivos, reemplaza solo las filas de
GIS/meteorologia/features cuyos `observation_id` declara el JobSpec y solo los
modelos cuyos `species_id` pertenecen al alcance. Regenera CSV e informes en
staging y promociona el conjunto completo mediante el mismo rollback atomico.
Un candidato parcial requiere por tanto que exista previamente un modelo
completo. Las claves de exclusividad impiden que convivan dos alcances con
especies comunes o uno completo con cualquier parcial del mismo snapshot;
siguen permitiendo especies disjuntas en workers diferentes. Las promociones
se serializan para que la segunda mezcla parta siempre de la primera ya
aceptada y no sobrescriba un cambio disjunto.

Prueba local real del 2026-07-20: `Una especie` y `Pendientes` procesaron y
promocionaron `cantharellus_lutescens` (una observacion seleccionada). Los hashes
de los modelos de las otras 13 especies permanecieron identicos. Un segundo job
`Pendientes` se cancelo cooperativamente en Meteorologia al 55 % y no se
promociono. La promocion pendiente limpio el estado solo despues del exito y
la retencion mantuvo el maximo de dos copias. Suite completa: 359 tests;
validador: 0 errores y 11 warnings conocidos.

### Fase 6. Dataset y baseline ML

- Incorporar `build_ml_dataset` sobre snapshots y episodios versionados.
- Incorporar `train_ml_model` y `evaluate_ml_model` para el baseline acordado.
- Reutilizar un mismo `dataset_id` en varios runs sin repetir reconstruccion.
- Guardar candidatos y metricas sin promocion automatica.

Cuando se incorporen varios algoritmos predictivos, sus resultados no deben
gestionarse mediante las dos copias de emergencia de la promocion V0. Se
creara un registro versionado de modelos independiente. Cada entrada debe
identificar algoritmo y parametros, version de codigo y contratos, snapshot y
`dataset_id`, particiones/semillas, artefactos, metricas globales y por especie
y estado de ciclo de vida (`candidate`, `active`, `archived` o `rejected`).

La comparacion se hara sobre el mismo conjunto de validacion, con separacion
espacial y temporal cuando corresponda. La UI podra resumir el resultado, pero
no reducira la decision a un score unico opaco: mostrara capacidad predictiva,
calibracion, cobertura/estabilidad y coste de calculo. Promocionar equivaldra a
seleccionar humanamente una version como activa; volver a una version conocida
sera otra seleccion trazable y no una restauracion manual de backups. Este
registro queda diferido hasta la fase ML y no modifica el cierre actual del
worker V0.

### Fase 7. Prueba integral

- Ejecutar la misma reconstruccion en HA y M1 con un snapshot congelado.
- Comparar resultados normalizados.
- Probar worker offline, corte Tailscale, cancelacion, inputs modificados y
  resultado corrupto.
- Probar que un experimento ML obsoleto queda auditable pero no activo.
- Documentar instalacion privada del worker en el M1.

M5, otra maquina o AWS se incorporaran en una fase posterior repitiendo las
pruebas de arquitectura, red, seguridad, rendimiento y costes. No bloquean el
primer worker.

Estado local 2026-07-20: completada dentro del M1 sin HA real/Tailscale. Se
probaron equivalencia, cache vacia/reutilizada, worker desconectado, cancelacion
cooperativa/forzada, corte/reconexion de red, corrupcion, freshness, promocion
manual y conservacion del fallback. La suite completa queda en 348 tests y el
validador de datos en 0 errores/11 warnings conocidos. La fase integral no se
considera cerrada para produccion hasta repetir el recorrido contra HA real por
la red privada elegida.

Primer corte contra HA real por LAN, 2026-07-20: `0.2.211` mantuvo estable el
reposo, completo asignacion y transporte de entradas y retiro correctamente los
avisos transitorios. Un candidato completo privado termino en 55 s. Tras activar
el modo operacional, otro candidato completo termino verificado en 49 s y su
promocion manual quedo registrada como `Promoted to live model`, sustituyendo
atomicamente el modelo vivo y conservando la copia anterior. Como la promocion
revalida freshness de forma sincrona, incluidos los hashes GIS, el navegador
parecia inmovil hasta terminar. `0.2.212` la ejecuta en segundo plano, persiste
fase/porcentaje, muestra una barra mediante polling y bloquea reintentos mientras
`promotion_status=promoting`; ya quedo instalada y probada en HA real.

Validacion posterior: `0.2.212` se instalo y la barra de promocion funciono en
HA real. Despues se completo un candidato parcial de `Amanita caesarea`. La
mejora local siguiente incorpora `Descartar` con modal para candidatos
terminales no promocionados: elimina en HA el snapshot y resultado privados,
mantiene un tombstone persistente y ordena al worker por heartbeat autenticado
e idempotente borrar su directorio de job; la fila desaparece al recibir el
acuse. El dataset GIS/DEM compartido, el modelo vivo y los backups de promocion
no entran en el borrado. Una promocion activa no puede descartarse. Si Rainmapper
se reinicio durante ella, se permite solo cuando no existe hilo activo ni
recibo, backup o staging de recuperacion; ante cualquier duda se conserva todo y
se exige recuperacion manual. La misma revision compacta la pantalla para que HA
y dos workers ocupen una fila, pliega pruebas y gestion, elimina textos y el
ancla superior redundantes, muestra los jobs internos como `HA local` y permite
ordenar por todas las columnas. La ordenacion inicial convierte los offsets de
HA y workers a un instante comun. Tambien se retira de Observaciones el panel
GIS heredado, porque no estaba asociado a un job concreto y podia quedar vacio.
Esta mejora tiene 386 tests y esta publicada e instalada en `0.2.213`; permanece
pendiente probar integralmente el descarte con HA/worker. La `0.2.214` corrige
la busqueda de Observaciones sobre el conjunto completo antes de paginar:
busca todos los campos persistidos y los nombres visibles resueltos, envia con
Enter o debounce y vuelve a la pagina 1. El usuario la valido localmente; la
imagen HA esta publicada y pendiente de instalar.

## 16. Criterios de aceptacion

- HA y worker llaman al mismo pipeline de `rainmapper_core`.
- Las cuatro fases V0 se ejecutan en HA o M1 y muestran progreso persistente.
- El M1 es materialmente mas rapido que HA con el mismo snapshot.
- Los resultados equivalentes producen la misma estructura y valores; si hay
  diferencias no deterministas, estan normalizadas y justificadas.
- Ningun dato vivo ni imagen del worker se publica en Internet.
- La imagen privada no contiene GIS/DEM, se puede transferir y ejecutar
  reproduciblemente en el M1.
- La primera ejecucion que necesita GIS/DEM lo sincroniza desde HA a un volumen
  persistente; los jobs posteriores lo reutilizan mientras coincida el manifest.
- Actualizar o reemplazar la imagen conserva el volumen y no fuerza una nueva
  descarga de datasets sin cambios.
- Una actualizacion de datos semiestaticos se verifica en staging y se activa
  atomicamente sin romper la version anterior.
- Un dataset congelado puede alimentar varios entrenamientos sin repetir GIS ni
  meteorologia.
- Cambiar datos en HA durante un job no instala artefactos operativos obsoletos.
- Los runs ML registran dataset, contrato, algoritmo, particiones, semillas,
  metricas y advertencias.
- Ningun candidato ML se activa sin una promocion humana explicita y reversible.
- Un fallo o cancelacion conserva intactos los artefactos V0 anteriores.
- Si no hay worker, la reconstruccion HA continua disponible.
- Si no hay worker, un entrenamiento ML puede esperar sin afectar a la app ni al
  modelo activo.
- La UI informa con claridad de tipo, destino, version, fase y estado del job.

## 17. Preguntas abiertas

1. Cuales son los tiempos por fase en HA y como varian los 97,857 s GIS/DEM,
   14,342 s meteo, 0,022 s features y 0,021 s modelo medidos en el primer run
   M1 al usar exactamente el mismo snapshot/dataset.
2. Que URL/puerto host estable y mecanismo de TLS/ACL expondran el listener
   interno `8100` del add-on al tailnet.
3. Si el primer despliegue usara Tailscale del host o sidecar Docker y que
   permisos necesita cada opcion.
4. Cuanto ocupan el snapshot vivo inicial y los deltas habituales.
5. Que historicos meteorologicos minimos necesita cada alcance de
   reconstruccion.
6. Tiempo de sincronizacion por Tailscale/LAN real, tamano de deltas y espacio
   real de una actualizacion con staging/rollback. El tamano contractual actual
   ya es 10 ficheros/6.306.367.027 bytes y la carga local a volumen vacio esta
   comprobada.
7. Condiciones exactas de redistribucion/atribucion de DEM, MVC50 y geologia.
8. Si la primera version necesita reanudar jobs o basta con reintento completo.
9. Durante cuanto tiempo conservar historial, logs y paquetes fallidos en HA.
10. Como versionar conjuntamente worker, core, schema y manifests de datasets
    pesados sin acoplarlos al numero de version del add-on mas de lo necesario.
11. Que artefactos ML completos se guardan en `/share`, cuales bajo `/media` y
    que debe entrar en backups.
12. Si una futura VM en AWS compensa coste, transferencia y mantenimiento, y
    que arquitectura usaria.
13. Cuando exista acceso al M5, si la politica del equipo permite Docker,
    Tailscale en contenedor y tratamiento local de estos datos privados.

## 18. Siguiente paso

Los seis bloques locales previos a la red real estan completados. El orden
recomendado desde este punto es:

1. instalar `0.2.214` y validar en HA real la busqueda global, el descarte
   seguro y la pantalla compacta/ordenable;
2. reiniciar el launcher del worker para incorporar el acuse de limpieza y
   probar descarte, desconexion/reconexion, cache y freshness contra el M1;
3. comprobar de nuevo la reconstruccion HA de fallback;
4. decidir el endurecimiento Tailscale/TLS/ACL del listener privado `8100` sin
   publicarlo en el router;
5. medir entonces las fases HA de manera compatible con los tiempos obtenidos
   en M1, usando exactamente el mismo snapshot y dataset;
6. repetir `docker load`/bootstrap en un daemon limpio u otro host y probar una
   actualizacion real del dataset semiestatico;
7. anadir `build_ml_dataset`, entrenamiento y evaluacion sobre la
   infraestructura ya probada.

La `0.2.213` esta instalada; la primera reconstruccion completa operacional y
su promocion manual M1 ↔ HA real ya terminaron correctamente, igual que una
reconstruccion parcial y una cancelacion. `0.2.214` esta publicada y pendiente
de instalar/probar en HA.

No hace falta reabrir la extraccion del pipeline ni duplicar el reconstructor:
el riesgo principal siguiente esta en la topologia y seguridad de red real, no
en la equivalencia local ya demostrada.
