# Worker multicoordinador

Estado: **diseño acordado, pendiente de implementación y validación**

Fecha: 2026-08-17

Este documento define la evolución del worker externo para que una misma
instalación física pueda permanecer emparejada simultáneamente con varios
coordinadores Rainmapper. El primer caso de uso es el worker M1 atendiendo al HA
real de la RPi4 y al HA local de laboratorio sin cambiar su URL persistida, sin
reemparejarlo en cada prueba y sin crear un worker o volumen temporal.

El runtime actual sigue siendo monocoordinador: conserva una sola
`rainmapper_url` y un solo token. Nada de lo descrito aquí debe interpretarse
como disponible en worker `1.0.10` ni como autorización para modificar el
worker normal, HA real o sus credenciales.

## 1. Decisiones vinculantes

1. Una instalación conserva un único `worker_id`, un único volumen persistente
   y una única caché de datasets, aunque atienda a varios coordinadores.
2. Cada coordinador tiene URL, token, estado y referencia de secreto propios.
   Un token nunca se comparte entre coordinadores.
3. El worker inicia todas las conexiones y mantiene heartbeat y consulta de
   jobs independientes con cada coordinador activo. No se abre una UI ni un
   puerto de administración en el worker.
4. Solo puede existir **un job activo global** en la instalación. Los
   coordinadores no pueden hacer que el M1 ejecute dos reconstrucciones o
   entrenamientos pesados a la vez.
5. Cuando queda libre, el worker consulta coordinadores aptos con una política
   justa y determinista, inicialmente round-robin. La indisponibilidad de uno
   no bloquea a los demás.
6. Todo job queda ligado a su coordinador de origen. Snapshot, progreso,
   control, resultado, receipt y limpieza solo se intercambian con ese origen.
7. La actualización completa mantiene tres jobs enlazados —reconstrucción, ML
   v0 y V2–V6— y una única promoción de la generación completa en el
   coordinador de origen.
8. Emparejar un coordinador nuevo **añade** una entrada; no sustituye ni
   modifica las existentes. La migración desde el formato actual debe conservar
   exactamente la URL y el token ya instalados, sin exigir pairing nuevo.

## 2. Límite configurable

El límite no se codificará de forma rígida en el servicio. La configuración
persistente del worker tendrá el parámetro local `max_coordinators`, con valor
predeterminado **4**. El arranque/CLI permitirá establecerlo explícitamente y
validará que sea un entero positivo dentro de un rango operativo documentado.
El nombre exacto de una posible variable de entorno se cerrará durante la
implementación para no declarar ahora una interfaz inexistente.

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

El schema monocoordinador se migrará atómicamente a una colección semejante a:

```text
worker_id
max_coordinators: 4
coordinators:
  - coordinator_id
    label
    rainmapper_url
    state
    token_ref
    last_success_at
    last_error
```

Este bloque es un modelo conceptual, no el formato JSON final. Los tokens
seguirán en ficheros de secretos separados con permisos restrictivos; no
aparecerán en el JSON de metadatos, argumentos, health, logs o Git.
`coordinator_id` será una identidad local estable y no dependerá del hostname,
la etiqueta humana ni la posición en una lista.

La migración debe ser idempotente y reversible mediante backup del fichero de
configuración anterior. Un fallo de validación no puede sobrescribir la
configuración monocoordinador válida. En especial, la URL actual del HA real no
se normalizará hacia otra dirección ni se reemplazará por la del laboratorio.

## 4. Planificación y aislamiento de jobs

- El supervisor mantiene heartbeats de todos los coordinadores activos incluso
  mientras hay un job en ejecución.
- Solo intenta claims cuando el slot global está libre. Si dos coordinadores
  ofrecen trabajo, el turno round-robin evita prioridad permanente por orden de
  configuración o latencia.
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
2. En el siguiente heartbeat o consulta autenticada, ese HA responde con un
   rechazo inequívoco de credencial, inicialmente HTTP `401`.
3. El worker elimina atómicamente **solo** el token y la asociación de ese
   `coordinator_id`, deja de consultarlo y conserva intactos los demás.

Un timeout, error DNS, desconexión, HTTP `5xx` u otro fallo transitorio nunca
autoriza a borrar credenciales. Si cambia el contrato de errores, el protocolo
deberá mantener una señal autenticada y no ambigua de revocación; no se inferirá
por ausencia de heartbeat.

Para no dejar un resultado sin destino, el coordinador rechazará con `409` una
revocación mientras ese worker tenga un job suyo activo, salvo que antes se
cancele o finalice siguiendo el protocolo normal. La revocación no puede
promocionar, descartar ni redirigir resultados implícitamente.

### Olvido local de un coordinador inaccesible

Como el worker no tiene UI, el script/CLI de gestión ofrecerá una operación
local explícita para listar asociaciones sin secretos y olvidar una por
`coordinator_id`. El nombre exacto del comando se definirá al implementarlo.
Esta operación borra solo la credencial local y advertirá que el coordinador
remoto puede conservar su hash hasta que se revoque también desde su propia UI.

## 6. Emparejamiento y administración

El flujo normal continúa empezando en `Workers y trabajos` del coordinador:
genera un código de un uso y el usuario lo introduce en el arranque/CLI del
worker junto con la URL de ese HA. La diferencia es que una validación correcta
añade el coordinador a la colección en vez de sustituir el anterior.

Cada HA solo ve y administra su propia relación con el worker. No recibe la
lista de otros coordinadores, sus URLs, labels ni estados. Desde la UI de HA se
puede revocar la credencial de ese HA; desde el CLI local se resuelven la
recuperación y el olvido cuando dicho HA ya no es accesible.

## 7. Compatibilidad y despliegue

- Un worker migrado con una sola entrada debe comportarse igual que el runtime
  actual.
- Un HA anterior que use el protocolo vigente debe poder seguir siendo uno de
  los coordinadores; la evolución no depende de que conozca a los demás.
- La migración y el supervisor multicoordinador requieren una nueva versión del
  worker. Los cambios de HA se limitarán a las señales de revocación y a las
  protecciones de job activo que resulten necesarias tras revisar el protocolo
  existente.
- La entrega se probará primero con dos coordinadores locales aislados y datos
  sintéticos. No se cambiará la asociación del M1 real para validar la
  migración.

## 8. Criterios de aceptación

- Migración sin reemparejar y sin modificar los bytes de URL/token existentes.
- Alta de un segundo coordinador y reinicio conservando ambos.
- Heartbeat visible en dos HAs con un único `worker_id`.
- Un solo job global, arbitraje justo y ausencia de doble claim.
- Enrutado de progreso, control, resultado y receipt al origen correcto.
- Aislamiento ante caída de uno de los HAs.
- Colisión deliberada de `job_id` entre coordinadores sin mezclar temporales.
- Revocación por `401` que elimina solo esa asociación en el siguiente ciclo.
- Timeout, DNS y `5xx` que conservan credenciales.
- Rechazo `409` de revocación con job activo.
- Límite `max_coordinators` configurable, persistente y validado, incluido el
  rechazo no destructivo de un alta que lo exceda.
- Reducción del límite por debajo del recuento actual rechazada sin modificar
  el límite previo ni ninguna asociación.
- Los tres jobs completos se encadenan y solo el coordinador de origen realiza
  una promoción final.
- Ningún secreto ni dato de otro coordinador aparece en UI, logs o respuestas.

## 9. Fuera de alcance de esta fase

- Ejecutar varios jobs pesados en paralelo.
- Añadir una interfaz web o puerto entrante al worker.
- Compartir snapshots, modelos candidatos o datos vivos entre coordinadores.
- Descubrimiento automático de coordinadores o fallback silencioso.
- Cambiar URLs persistidas, usar Tailscale desde Codex o modificar producción.
- Preparar o publicar una release sin autorización explícita posterior.
