# Worker multicoordinador

Estado: **runtime multicoordinador implementado y probado; administración CLI
incompleta y pendiente de versionado/despliegue**

Fecha: 2026-08-17
Actualizado: 2026-09-06

Este documento define la evolución del worker externo para que una misma
instalación física pueda permanecer emparejada simultáneamente con varios
coordinadores Rainmapper. El primer caso de uso es el worker M1 atendiendo al HA
real de la RPi4 y al HA local de laboratorio sin cambiar su URL persistida, sin
reemparejarlo en cada prueba y sin crear un worker o volumen temporal.

El worker publicado `1.0.41` sigue siendo monocoordinador. La implementación
multicoordinador está en prueba local con la imagen separada
`rainmapper-worker:multicoordinator-test`; todavía no es una release. Nada de lo
descrito aquí autoriza a modificar las URLs o credenciales de un worker ni a
desplegarlo en HA real.

## 0. Relación con los demás documentos

Este es el documento principal de arquitectura, operación, emparejamiento y
validación del **worker multicoordinador**. No debe confundirse con
`mushroom-ml-multiversion-runtime-spec-es.md`, que define la convivencia de las
versiones científicas V2--V6 dentro del Predictor. El transporte y el contrato
histórico del worker externo se describen en
`mushroom-v0-external-worker-design-es.md`.

Por tanto son dos dimensiones independientes:

- **multicoordinador**: un mismo proceso worker atiende a varios HAs;
- **multiversión**: un mismo runtime Predictor contiene y compara varias
  versiones científicas.

El worker multicoordinador ejecuta trabajos multiversión, pero el número de
coordinadores no cambia los perfiles, modelos ni reglas científicas.

## 1. Decisiones vinculantes

1. Una instalación conserva un único `worker_id`, un único volumen persistente
   y una única caché de datasets, aunque atienda a varios coordinadores.
2. Cada coordinador tiene URL, token, estado y referencia de secreto propios.
   Un token nunca se comparte entre coordinadores.
3. El worker inicia todas las conexiones y mantiene heartbeat y consulta de
   jobs independientes con cada coordinador activo. No se abre una UI ni un
   puerto de administración en el worker.
4. Se conservan los dos carriles actuales como recursos globales del worker:
   un único job `foreground` y un único job `background`. Reconstrucción,
   entrenamiento y predicción interactiva comparten `foreground`; el
   precálculo utiliza `background`. Por tanto pueden coincidir un entrenamiento
   y un precálculo, pero nunca dos entrenamientos ni dos precálculos aunque
   procedan de coordinadores distintos.
5. Cuando un carril queda libre, el worker consulta coordinadores aptos con una
   política justa y determinista, inicialmente round-robin por carril. La
   indisponibilidad de uno no bloquea a los demás.
6. Todo job queda ligado a su coordinador de origen. Snapshot, progreso,
   control, resultado, receipt y limpieza solo se intercambian con ese origen.
7. La actualización completa mantiene tres jobs enlazados —reconstrucción, ML
   v0 y V2–V6— y una única promoción de la generación completa en el
   coordinador de origen.
8. Emparejar un coordinador nuevo **añade** una entrada; no sustituye ni
   modifica las existentes. La migración desde el formato actual debe conservar
   exactamente la URL y el token ya instalados, sin exigir pairing nuevo.

## 2. Límite configurable

El límite no está ligado a dos coordinadores. La configuración
persistente del worker tendrá el parámetro local `max_coordinators`, con valor
predeterminado **4** y rango permitido de **1 a 16**. Se cambia explícitamente
con `config set-limit --max-coordinators N` o al arrancar mediante
`--max-coordinators N`.

El límite cuenta coordinadores activos o temporalmente inaccesibles que aún
conserven credencial. Las entradas revocadas y eliminadas no cuentan. Intentar
añadir otra cuando se alcance el límite falla antes de persistir cambios y
explica que hay que revocar u olvidar una asociación existente, o ampliar de
forma explícita `max_coordinators`.

Reducir `max_coordinators` por debajo del número de asociaciones que aún
conservan credencial también se rechaza de forma atómica. El worker mantiene el
valor anterior y no elige, elimina ni desactiva coordinadores por su cuenta; el
mensaje indica el recuento actual y cuántas asociaciones deben revocarse u
olvidarse antes de repetir el cambio.

Con dos coordinadores el coste de heartbeat y polling es despreciable frente al
cálculo. El límite sigue siendo útil para acotar credenciales, tráfico,
diagnóstico y errores de configuración; no es un límite de rendimiento ni de
jobs concurrentes.

## 3. Configuración y secretos

Para reducir el riesgo sobre el coordinador real ya instalado, su configuración
actual no se migra ni se reescribe. Continúa en `config/coordinator.json` y su
credencial en `secrets/coordinator-token`. Los coordinadores adicionales se
guardan en `config/additional-coordinators.json`:

```text
max_coordinators: 4
coordinators:
  - coordinator_id
    label
    rainmapper_url
    # el token no aparece aquí
```

Cada token adicional se guarda por separado en
`secrets/coordinators/<coordinator_id>.token`, con permisos restrictivos; no
aparecerán en el JSON de metadatos, argumentos, health, logs o Git.
`coordinator_id` será una identidad local estable y no dependerá del hostname,
la etiqueta humana ni la posición en una lista.

Las escrituras de la colección adicional deben ser atómicas. Un fallo de
validación no puede modificar los ficheros monocoordinador válidos ni dejar una
entrada adicional parcialmente utilizable. No se crean copias de seguridad ni
directorios de recuperación. En especial, la URL actual del HA real no se
normaliza hacia otra dirección ni se reemplaza por la del laboratorio.

## 4. Planificación y aislamiento de jobs

- El supervisor mantiene heartbeats de todos los coordinadores activos incluso
  mientras hay jobs en ejecución.
- Solo intenta claims cuando el carril correspondiente está libre. Si varios
  coordinadores ofrecen trabajo para ese carril, el turno round-robin evita
  prioridad permanente por orden de configuración o latencia.
- Tras completar una fase enlazada de una actualización completa, el siguiente
  claim `foreground` prioriza ese coordinador. Cada job conserva en todo caso
  su coordinador de origen y el otro carril sigue disponible para precálculo.
- El estado privado y los temporales se nombran por
  `(coordinator_id, job_id)`. Dos HAs pueden generar el mismo `job_id` sin
  colisión.
- El lease y el token de claim pertenecen exclusivamente al coordinador de
  origen. Nunca se reenvían a otro.
- Un error de red de un coordinador queda aislado. No cancela un job de otro ni
  invalida sus credenciales.
- La caché GIS/DEM puede compartirse únicamente por manifests y hashes
  verificados. Snapshots vivos, resultados y candidatos no se comparten entre
  coordinadores.

## 5. Revocación y olvido

### Revocación iniciada en un coordinador

1. HA elimina su credencial server-side y deja de considerar disponible al
   worker en ese coordinador.
2. En el siguiente heartbeat o consulta autenticada, ese HA rechaza esa
   credencial y únicamente esa conexión queda no disponible.
3. El worker no borra ni sustituye automáticamente ninguna asociación por una
   respuesta de red. El olvido local es una acción explícita con
   `config forget --coordinator-id ID`; la asociación primaria está protegida
   frente a ese comando.

Un `401`, timeout, error DNS, desconexión, HTTP `5xx` u otro fallo nunca
autoriza a borrar credenciales automáticamente.

Para no dejar un resultado sin destino, el coordinador rechazará con `409` una
revocación mientras ese worker tenga un job suyo activo, salvo que antes se
cancele o finalice siguiendo el protocolo normal. La revocación no puede
promocionar, descartar ni redirigir resultados implícitamente.

### Olvido local de un coordinador inaccesible

Como el worker no tiene UI, el CLI permite `config list` para listar
asociaciones sin secretos y `config forget --coordinator-id ID` para olvidar
una asociación adicional.
Esta operación borra solo la credencial local y advertirá que el coordinador
remoto puede conservar su hash hasta que se revoque también desde su propia UI.

## 6. Emparejamiento y administración

El flujo normal continúa empezando en `Workers y trabajos` del coordinador:
genera un código de un uso y el usuario lo introduce en el arranque/CLI del
worker junto con la URL de ese HA. `config add`, o el arranque con
`--add-coordinator URL` y `--pairing-code-stdin`, añade el coordinador a la
colección en vez de sustituir el anterior. El arranque usa `config check-all`:
un coordinador caído no impide iniciar si al menos otro responde.

Cada HA solo ve y administra su propia relación con el worker. No recibe la
lista de otros coordinadores, sus URLs, labels ni estados. Desde la UI de HA se
puede revocar la credencial de ese HA; desde el CLI local se resuelven la
recuperación y el olvido cuando dicho HA ya no es accesible.

### 6.1 Estado actual del CLI

El worker no tiene UI. Existen dos capas de CLI:

1. `mushroom_worker_start.sh`, que construye, configura y arranca el contenedor;
2. `manage-mushroom-worker-config.py`, disponible dentro de la imagen como
   subcomando `config`, que administra el volumen persistente.

La capa interna ya ofrece `list`, `check-all`, `pair`, `add`, `forget` y
`set-limit`. Sin embargo, el script público de arranque solo expone bien el alta
de secundarios y el límite:

- `--rainmapper-url`, `--token-stdin`, `--token-file`, `--clear-token` y el
  pairing sin `--add-coordinator` actúan sobre la asociación primaria;
- `--add-coordinator URL` con `--pairing-code-stdin` añade o renueva por URL una
  asociación secundaria;
- `--coordinator-label` solo etiqueta ese alta;
- no hay todavía opciones públicas para listar, seleccionar, reemparejar,
  cambiar de URL, limpiar el token u olvidar un coordinador concreto.

Esto significa que el runtime es multicoordinador, pero la administración
pública aún no es completa ni suficientemente explícita. Hasta corregirla, no
se debe presentar `mushroom_worker_start.sh` como gestor integral de
coordinadores.

### 6.2 Interfaz administrativa que falta

La interfaz pública debe expresar la acción y el destino sin depender de un
principal implícito:

```text
--list-coordinators
--check-coordinators
--pair-primary URL
--add-coordinator URL
--repair-coordinator ID
--replace-coordinator ID URL
--clear-coordinator-token ID
--forget-coordinator ID
```

Las operaciones sobre una asociación existente deben exigir su
`coordinator_id`. Cambiar una URL o una credencial no puede alterar otra
asociación, y una operación fallida debe conservar intacta la configuración
anterior. El principal seguirá protegido frente a un olvido accidental: su
sustitución deberá ser una acción distinta y explícita.

Después de modificar asociaciones hay que reiniciar el servicio cuando no haya
jobs activos, porque la lista se carga al iniciar el proceso. La comprobación
posterior debe verificar la lista sin secretos, la conectividad independiente y
que las URLs no afectadas conservan exactamente sus valores previos.

## 7. Compatibilidad y despliegue

- Un worker migrado con una sola entrada debe comportarse igual que el runtime
  actual.
- Un HA anterior que use el protocolo vigente debe poder seguir siendo uno de
  los coordinadores; la evolución no depende de que conozca a los demás.
- La migración y el supervisor multicoordinador requieren una nueva versión del
  worker. Los cambios de HA se limitarán a las señales de revocación y a las
  protecciones de job activo que resulten necesarias tras revisar el protocolo
  existente.
- La entrega se prueba con coordinadores locales aislados y datos sintéticos.
  No se cambia la asociación del M1 real para validar la migración.

## 8. Criterios de aceptación

- Migración sin reemparejar y sin modificar los bytes de URL/token existentes.
- Alta de un segundo coordinador y reinicio conservando ambos.
- Heartbeat visible en dos HAs con un único `worker_id`.
- Un solo job global por carril, arbitraje justo y ausencia de doble claim en
  cada carril.
- Entrenamiento `foreground` y precálculo `background` simultáneos, incluso si
  proceden de coordinadores diferentes.
- Enrutado de progreso, control, resultado y receipt al origen correcto.
- Aislamiento ante caída de uno de los HAs.
- Colisión deliberada de `job_id` entre coordinadores sin mezclar temporales.
- Un rechazo, timeout, DNS y `5xx` dejan aislada esa conexión y conservan las
  credenciales hasta una acción local explícita.
- Rechazo `409` de revocación con job activo.
- Límite `max_coordinators` configurable, persistente y validado, incluido el
  rechazo no destructivo de un alta que lo exceda.
- Reducción del límite por debajo del recuento actual rechazada sin modificar
  el límite previo ni ninguna asociación.
- Los tres jobs completos se encadenan y solo el coordinador de origen realiza
  una promoción final.
- Ningún secreto ni dato de otro coordinador aparece en UI, logs o respuestas.

## 9. Implementación y validación local del 6 de septiembre de 2026

- La asociación primaria conserva sin cambios
  `config/coordinator.json` y `secrets/coordinator-token`; las adicionales son
  aditivas y usan secretos separados.
- El planificador acepta cualquier cardinalidad dentro del límite configurado,
  mantiene un slot global por carril y aplica round-robin por carril.
- Los temporales mutables de coordinadores adicionales se aíslan bajo
  `coordinators/<coordinator_id>/`; las cachés inmutables verificadas continúan
  deduplicadas y compartidas.
- El estado de caché y runtime, que implica acceso a disco, se calcula una sola
  vez por ciclo de heartbeat y se reutiliza para todos los coordinadores. No se
  multiplica ese trabajo por el número de HAs.
- Una prueba funcional levantó tres coordinadores aislados, dejó uno no
  disponible y ejecutó a la vez un job `foreground` de uno y un job
  `background` de otro. Verificó tokens separados, respuesta al origen,
  ocultación del `job_id` ajeno y conservación byte a byte de la configuración
  primaria.
- La suite completa terminó con **1305 pruebas correctas**. Además se construyó
  una imagen local separada `rainmapper-worker:multicoordinator-test`, cuyo
  manifest fue
  `sha256:8604bcd4178be495fdf0bcb8d7039d579e8a6184f7c85e26b901ee9ea92e8258`,
  y se comprobó dentro de ella el límite configurable.
- Después se recreó el contenedor de prueba con esa imagen y, conservando la
  asociación primaria, se añadió HA local como segundo coordinador. Ambos HAs
  mostraron el mismo `worker_id` y el entrenamiento solicitado desde HA local
  completó correctamente sus tres jobs encadenados.
- El contenedor de prueba seguía saludable y declaraba dos coordinadores al
  comenzar la reproducción del precálculo. El tag `1.0.41` continuaba siendo la
  release anterior, no el código que ejecutaba el contenedor de prueba.

## 10. Reproducción del fallo de precálculo de HA real

El 6 de septiembre de 2026, HA local encoló el job
`worker_job_MR1tD64I514P` contra el mismo worker multicoordinador usado por HA
real. El job utilizó la generación entrenada
`operational_20260906T210610Z`, ocho especies, 72 pares especie/área, siete días,
cinco versiones y 420 ganadores esperados.

El worker reclamó el job a las `21:33:19Z`, sincronizó el runtime en 0,439 s y
calculó durante aproximadamente 6 min 30 s. Falló antes del upload con el mismo
síntoma observado en HA real:

```text
Artifact coverage counters do not match identity:
{'species': 8, 'areas': 72, 'days': 7, 'versions': 5, 'members': 0}
!=
{'species': 8, 'areas': 72, 'days': 7, 'versions': 5, 'members': 420}
```

Una ejecución diagnóstica mínima sobre el runtime exacto reprodujo la causa en
una sola especie y área: las siete fechas devolvieron
`multiversion_runtime_error` con `UnicodeDecodeError` al encontrar los bytes
`0x1f 0x8b`, cabecera de gzip. El catálogo de calidad de la generación está
comprimido, pero `_load_quality_catalog()` en
`mushroom_ml_multiversion_comparison.py` verifica sus bytes y los pasa
directamente a `json.loads()` sin descomprimirlos. La ruta usada para resolver
el plan operativo sí admite `.gz`; la ruta que ejecuta las comparaciones no.

La excepción queda convertida en una comparación no disponible, por lo que las
respuestas no contienen miembros. El escritor SQLite solo detecta la pérdida al
validar al final los cero miembros materializados frente a los 420 declarados.
El porcentaje cercano al 65 % es, por tanto, el punto visible donde termina el
cálculo y aflora la incoherencia; no es por sí mismo la causa.

Esta reproducción demuestra dos cosas distintas:

1. el enrutado multicoordinador lleva el trabajo local al mismo circuito del
   worker que usa HA real;
2. el fallo pertenece al lector del catálogo comprimido del precálculo, no al
   emparejamiento ni a una diferencia entre HA local y HA real.

La corrección pendiente debe enseñar a ese lector a validar y descomprimir
`.gz`, añadir una prueba con un catálogo realmente comprimido y ejecutar un
precálculo completo local antes de preparar una release. No se debe ocultar el
problema aceptando `members: 0` ni rebajando el contrato de cobertura.

## 11. Fuera de alcance de esta fase

- Ejecutar más de un job por carril o más de dos jobs totales en paralelo.
- Añadir una interfaz web o puerto entrante al worker.
- Compartir snapshots, modelos candidatos o datos vivos entre coordinadores.
- Descubrimiento automático de coordinadores o fallback silencioso.
- Cambiar URLs persistidas, usar Tailscale desde Codex o modificar producción.
- Preparar o publicar una release sin autorización explícita posterior.
