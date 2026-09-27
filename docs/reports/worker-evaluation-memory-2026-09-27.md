# Reutilización de entradas V2–V6 — 27/09/2026

## Incidente y alcance

El worker del usuario terminó a las 22:58:59 del 26/09 (20:58:59 UTC).
`docker inspect rainmapper-worker`: `OOMKilled=true`, salida 137. El trabajo
`worker_job_XpH0Q6p3EQaUxiyF` quedó persistido en HA como `running`, 46 %.
No se conoce el pico de memoria completo del trabajo ni su asignación exacta
en el instante de la terminación. No atribuir toda la caída a un único JSON.

Archivo verificado en su volumen: `multiversion_inputs/v5/biology-v5-lag.json`,
528.821.763 bytes, 3.493 muestras según el manifiesto. El contrato conserva
365 días de variables meteorológicas, físicas y de estado del suelo. No se
recorta este historial ni se modifica la construcción del SMI.

## Cambio local

- El preparador ejecuta los evaluadores con `runpy`, en el mismo proceso.
  Antes V2–V5 cargaba ambos contratos (`fixed`, `lag`) juntos y V6 volvía a
  cargar cada uno para cada perfil seleccionado.
- Ahora carga un contrato temporal, evalúa V2–V5, pasa **el mismo objeto V5**
  a todos los perfiles V6 y libera las entradas antes del siguiente contrato.
  Las entradas V3/V4 se liberan antes de V6. Sólo se conservan resultados.
- V5 comparte la normalización entre perfiles de un mismo objeto de entrada.
  V6 normaliza una vez por contrato. Los estimadores y el preprocesamiento
  ajustado a las muestras de entrenamiento siguen siendo independientes.
- V6 autónomo también carga cada contrato una sola vez. Al recibir resultados
  del preparador, finaliza sus artefactos sin leer ni evaluar de nuevo.
- Se conserva el orden anterior de predicciones e informes V6 (perfil,
  contrato, partición), y se sella el manifiesto después del manifiesto V5.
- No hay caché global ni persistente de objetos Python. El entrenamiento final
  sigue siendo otro proceso, con su propia lectura de entradas. No se afirma
  una única lectura física en todo el pipeline: validadores/hash y la etapa
  final siguen leyendo ficheros. La reutilización se aplica a los consumidores
  de las entradas durante la evaluación V2–V6.

Código: `scripts/prepare-mushroom-ml-multiversion-inputs.py`,
`scripts/evaluate-biology-v5-raw-benchmark.py`,
`scripts/evaluate-biology-v6-smooth-hierarchical.py`.

## Verificación

25 pruebas dirigidas correctas: 7 de ciclo de vida/integración/paridad nuevas,
6 de preparación multiversión, 8 del preprocesador V6 y 4 de hold-out.
Las nuevas comparan ajustes pequeños sintéticos independientes frente a la
entrada compartida: igualdad exacta de probabilidades e informes para ventanas
30/60/90 y el contrato completo de 365 días; entrada original sin modificación.
Comprueban también una lectura por archivo, identidad compartida V5/V6,
liberación de objetos antes de cargar el siguiente contrato, liberación tras
excepción y ausencia de recarga en la finalización V6.

Medición adicional con archivos **reales** del trabajo detenido, volumen
montado en solo lectura, imagen existente `rainmapper-worker:1.1.6`, sin red,
contenedor de diagnóstico limitado a 4 GiB. No ejecuta el servicio del worker.
Se sustituye `evaluate_split` por un resultado vacío: **no ajusta modelos**.
Se ejecutan las mismas cargas, normalizaciones y particiones de V6 autónomo.

| Medida | Anterior | Corregido |
| --- | ---: | ---: |
| Lecturas por archivo fixed/lag | 3 | 1 |
| Normalizaciones | 6 | 2 |
| Pico RSS (KiB, `resource.getrusage`) | 4.180.276 | 1.789.896 |
| Pico RSS (GiB) | 3,99 | 1,71 |

Reducción aproximada del 57 %. Es evidencia del coste de carga y reutilización,
**no** del pico total, tiempo de entrenamiento ni garantía de ausencia de OOM
en el trabajo completo. Artefactos y script de medición en
`docker-data/diagnostics/v6-memory-20260927/`; `loading-measurement.json` contiene
huellas del código medido. No se duplicaron los JSON grandes.

## Despliegue autorizado

El usuario solicita reconstruir el worker y se reserva entrenamiento/precálculo
desde HA real. Reconstruido `rainmapper-worker:1.1.6`, imagen
`sha256:79440107723a685b3e8eb32b2161a2ec0f9224f02cc7a09339101a4553eaa747`.
Paridad de 122 archivos Python de la imagen con el worktree, sin diferencias;
25 pruebas dirigidas correctas también dentro de la imagen reconstruida.
Recreado el servicio con los mismos dos archivos Compose y el mismo volumen.

Estado comprobado: contenedor `running/healthy`, `/health` devuelve `idle`,
ambas vías sin trabajo activo y caché GIS válida. Hashes de
`config/coordinator.json`, `config/additional-coordinators.json` e
`identity/worker.json` idénticos antes/después. URL primaria conservada:
`http://100.111.77.48:8100`. `check-all` confirma acceso a ambos coordinadores.
Las huellas de los tres scripts leídos del contenedor activo coinciden con los
archivos corregidos. No se publicó HA ni se lanzaron trabajos operativos.
La corrección futura del estado huérfano queda en `docs/todo.md`.

La comprobación de disponibilidad anterior corresponde al arranque del 27/09;
no acredita que siga libre después de que el usuario lance trabajos. La
validación operativa posterior se documenta a continuación. El estado huérfano `running`
de HA y la duración del precálculo son pendientes separados en
[TODO](../todo.md); esta corrección no los resuelve.

## Validación operativa posterior — 27/09/2026

El usuario lanzó el ciclo desde HA real y avisó de su finalización. Comprobación
posterior de `mushroom_worker_jobs.json`, registro ML de HA, recibos y SQLite
activos de HA/worker, `docker inspect`, logs y cgroup del contenedor reconstruido.
Sin lanzar trabajos, reiniciar servicios ni escribir datos en HA.

| Etapa | Trabajo | Ejecución (inicio → fin persistidos) | Resultado |
| --- | --- | ---: | --- |
| Reconstrucción | `worker_job_t_wE49eGFlNjpxmZ` | 2 min 5 s | Completa y promovida |
| V0 | `worker_job_fMVi22qIIes8iO_u` | 27 s | 10 especies, verificado y promovido |
| Multiversión | `worker_job_IUys0YwNNx8-S_L6` | 10 min 4 s | 792/792 ajustes, 0 fallos, verificado |
| Precálculo | `worker_job_uiqmMIjaU7Cs` | 9 min 39 s | Completo y activo en HA y worker |

Las cinco versiones operativas del registro apuntan al lote nuevo
`operational_20260926T223720Z`. Precálculo revisión **261**, cobertura
27/09–03/10/2026, `publication_state=complete`: 868 filas de cobertura y base,
777 miembros operativos, 1.015 respuestas; recuentos reales coinciden con sus
metadatos. Las 124 áreas del contrato son pares especie/área, no necesariamente
124 áreas geográficas distintas. SHA leído de ambos SQLite, coincidente con
el recibo activo de HA y el resultado del trabajo:
`2575c66a54617bb1c035e96903018587b5f42353bb6bd52ed938067ac05cb753`.
Tamaño 43.884.544 bytes. Limpieza terminal de los cuatro trabajos: `complete`.

Desglose persistido del precálculo: sincronización runtime 1,81 s; cálculo
441,58 s; ida/vuelta de subida 105,64 s, de ellos publicación HA 100,91 s y
transferencia estimada 4,74 s; activación worker 15,26 s. Estas medidas no son
fases exhaustivas ni una comparación A/B con ejecuciones anteriores. El total
observado es menor que los 11 minutos reportados antes, sin demostrar la causa.

Contenedor original del rebuild aún `running/healthy`, `RestartCount=0`,
`OOMKilled=false`; cgroup `oom=0`, `oom_kill=0`. Ambos carriles `idle` al consultar.
`memory.peak=7368622080` bytes (**6,86 GiB**) desde su creación, incluye el ciclo
completo y cachés; no permite atribuir el pico a una fase ni compararlo directamente
con el RSS del ensayo de carga aislada. `memory.current=2899759104` bytes en una
muestra posterior; tampoco equivale al RSS de Python ni demuestra fuga.

Los logs registran timeouts de heartbeat/claim seguidos de `heartbeat_restored`.
Los trabajos se verificaron y liberaron con confirmación de finalización. Por
tanto, ciclo completado sin OOM, pero no afirmar ausencia absoluta de incidencias
de comunicación. El diagnóstico de duración y estado huérfano sigue aplazado.
