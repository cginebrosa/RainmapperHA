# Memoria de HA real tras entrenamiento y precálculo

Inspección de solo lectura por SMB el 22/09/2026. Sin SSH, entrenamiento,
precálculo, construcción de runtime ni reinicios. Copia privada de evidencia en
`tmp/ha-memory-20260922/`. Las capturas del usuario corresponden a HA 0.2.317;
en la primera inspección, el código de validación no tenía diferencias frente al commit
`d4a468a` (release 0.2.317).

## Hechos medidos en HA real

Fuentes: `/Volumes/share/rainmapper/diagnostics/runtime_metrics.jsonl`,
`runtime_summary.jsonl`, `mushroom-data/mushroom_worker_jobs.json` y recibo de
`/Volumes/media/rainmapper/results/predictor-precompute/active.sqlite3`.
Horas siguientes en Europe/Madrid (UTC+2):

- Precálculo `worker_job_gXoBg-kce0FE`, revisión 213: recibido a las 02:01:30,
  activado en HA a las 02:03:40. Verificación/publicación HA: 129,518696 s.
- Archivo: 46.759.936 bytes. Copiado al Mac y verificado contra SHA/tamaño del
  recibo (`6bc242a3d5184ccf18d0d8ad4c789076879f14858679d97751e3fcf5c358c915`).
- 02:00:35: proceso principal 428,629 MiB RSS, contenedor 676,879 MiB.
- 02:02:57, dentro de la activación: proceso 924,094 MiB RSS; contenedor
  1.132,734 MiB. Es una muestra, no una garantía de pico máximo del trabajo.
- 02:07:58, al detenerse: proceso 485,684 MiB RSS; contenedor 689,051 MiB.
- 02:08:38, nuevo arranque: proceso 243,984 MiB RSS; contenedor 293,691 MiB.
- Las capturas de Info muestran 18,1% y 11,6%. No equiparar exactamente
  ese indicador con RSS o cgroup: tienen diferente alcance y momento.

También hubo actualizaciones meteorológicas durante ese arranque. No atribuir
cada crecimiento de memoria a entrenamientos. Las consultas previas al último
precálculo registraban diez instancias Predictor cacheadas; eso no demuestra
que sean responsables del exceso. Son de carga perezosa.

## Causa concreta del pico, reproducida localmente

`mushroom_predictor_precompute._validate_published_rows` acumula todas las
respuestas validadas y descomprimidas en `response_payloads`, además de coberturas
y claves. El archivo inspeccionado contiene 208 respuestas distintas, 208
coberturas, 847 celdas y 756 miembros operativos. La recepción en web_server
materializa primero el cuerpo HTTP completo y lo entrega como BytesIO.

Se ejecutó **únicamente validate_artifact(full=True)** sobre la copia existente,
en proceso Python del Mac. No se generaron predicciones ni nuevos artefactos.
Instrumentación por fases y perfil de retorno para contar objetos retenidos:

| Momento | RSS MiB |
|---|---:|
| Antes de validar, después de importar módulos | 188,36 |
| Antes de validar las filas publicadas | 197,64 |
| Al retornar el validador, con sus 208 respuestas aún referenciadas | 677,05 |
| Tras liberar las variables locales del validador | 289,38 |
| Tras terminar toda la validación | 289,17 |
| Tras gc.collect diagnóstico en ese proceso del Mac | 250,17 |

Pico registrado en ese proceso: 786,36 MiB. La instrumentación altera tiempos;
58 s en el Mac no se presenta como benchmark. Las magnitudes no son una medida
intercambiable con la Raspberry. Sí prueban un pico grande por validar un archivo
existente relativamente pequeño y una recuperación parcial tras liberar objetos.
No se demuestra una fuga acumulativa ni se explica con esto toda la diferencia
242 MiB RSS entre antes del reinicio real y el nuevo arranque.

## Limpieza existente y dirección propuesta

La promoción completa llama a `release_predictor_cache()`: suelta instancias,
servicio y meteorología compartida y llama a gc.collect. No es correcto afirmar
que la promoción no limpia nada. La activación del precálculo cierra SQLite,
pero la validación ocurre dentro del servidor persistente y acumula respuestas.

Prioridad propuesta en la primera inspección:

1. Validar respuestas secuencialmente y conservar solo índices/metadatos mínimos
   para comprobar relaciones. Mantener todas las comprobaciones semánticas.
2. Recibir el archivo por bloques directamente a temporal, sin conservar todo
   el cuerpo HTTP. Mantener límites, SHA, autorización y publicación atómica.
3. Medir antes/después/recuperación de recepción, promoción y activación, separando
   RSS, memoria del contenedor y caché de archivos. No usar gc.collect o subir
   límites como sustitutos de corregir el diseño.
4. Revisar aparte el consumo al arrancar y las cachés de consulta: 244 MiB RSS
   iniciales observados. No prometer un objetivo de RAM sin medirlo.

La corrección se validará primero con la misma copia en el Mac/HA local; no se
necesita reentrenar ni lanzar otro precálculo para reproducir este problema.

## Corrección implementada y desplegada localmente

`_validate_published_rows` conserva claves y solicitudes normalizadas, procesa cada
respuesta compartida una sola vez y comprueba sus alias antes de liberarla. Ya no
retiene las respuestas completas ni los payloads de miembros operativos. Mantiene
la validación de identidades, cobertura, runtime, solicitudes y retargeting.

El endpoint `precompute-artifact` evita `read_request_body`: autentica y autoriza
antes de consumir un iterador de bloques de hasta 1 MiB, con decodificación tanto
de Content-Length como de chunked. El publicador escribe directamente al temporal,
verifica tamaño/SHA y conserva la publicación atómica y la comprobación del deseo
vigente. Los errores eliminan el temporal y preservan el activo y su recibo. El
worker ya enviaba por bloques; recibe la mejora del validador compartido. No se
suben límites ni se cambia el formato del artefacto ni se añade GC forzado.

Comparación sin perfilado sobre la misma copia de 46.759.936 bytes, en procesos
independientes del Mac (`before-benchmark.json`, `after-benchmark.json`):

| Medida | Antes | Después |
|---|---:|---:|
| Tiempo de validación completa | 16,00 s | 15,66 s |
| Pico del proceso | 825,14 MiB | 304,09 MiB |

Segunda comprobación de retención (`before-retention.json`, `after-retention.json`):
el incremento RSS final respecto al proceso después de importar módulos pasa de
109,16 a 62,69 MiB. Tras GC diagnóstico: +66,16 frente a +50,70 MiB. Esta segunda
medición carga una copia del módulo anterior para compararlo; el RSS inicial
difiere y por eso se expresan incrementos. No prueba el consumo total del servidor
HA ni resuelve todavía la memoria de arranque/cachés de consultas.

En un proceso aislado dentro de la imagen Linux de HA local, la validación de la
misma copia terminó en 14,80 s con pico de 259,01 MiB y el mismo SHA. No se activó
esa copia, no se generaron predicciones y no se midió aún en la Raspberry.

Validación: 1.724 tests con 52 skips y smoke completo correctos. La primera pasada
en sandbox tuvo seis errores exclusivamente por denegación de bind HTTP local;
la pasada autorizada terminó correctamente. Las nuevas pruebas cubren liberación
entre respuestas, referencias inexistentes, truncado, exceso de tamaño, fallo de
transporte, conservación del activo, autorización previa y recepción/publicación
HTTP tanto fija como chunked.

Se reconstruyeron HA local y el worker y se verificaron 217/117 archivos efectivos,
sin diferencias. El primer arranque del worker detectó que su Dockerfile no incluía
el módulo pendiente de consenso; se añadió `mushroom_recommendation_policy.py` y una
importación real del servicio durante el build. El build corregido y arranque
posterior fueron correctos. Configuración y credenciales del worker conservan sus
SHA; destinos real `http://100.111.77.48:8100` y local `http://rainmapper-ha-ui:8100`
sin cambios. La etiqueta local sigue siendo `1.1.4`; la huella de imagen sí cambió.

Evidencia de paridad: `tmp/ha-memory-20260922/parity.json`. HA local:
`sha256:cb3312b3650dcbf9d5830e95d4d4630b2556da6c55805831a24ee4367d4dde9c`;
worker: `sha256:1ed4e19f34de913839ce17245beb4bdc43765522abc73d05c5fec99d8960371a`.

**Pendiente de release:** el usuario eligió expresamente lanzar él mismo el circuito
completo en HA local. No se ha lanzado entrenamiento ni precálculo. Auditar sus
resultados/recepción/activación y pedir aceptación del resultado local antes de
publicar. No se ha actualizado la imagen HA real ni publicado una release.


## Circuito local lanzado por el usuario y comparación de tiempos

Auditoría 22/09/2026 de `docker-data/mushroom-data/mushroom_worker_jobs.json`,
registro equivalente de `/Volumes/share/rainmapper/`, logs del worker y archivos
activos dentro de los contenedores. No se lanzaron trabajos desde esta auditoría.

- Reconstrucción `worker_job_nUoV4TXWa0U59aFx`, base
  `worker_job_yJWXlX7xGk8VPjJa` y multiversión
  `worker_job_25OJr56p3RhQpdJc`: completos. Multiversión: 792/792 ajustes, cero
  fallos, generación `operational_20260922T011105Z`.
- Primer precálculo `worker_job_bF6AU7jpJ50-`: creado 01:20:33 UTC con la
  generación del 20/09 mientras se entrenaba. Promoción 01:22:46; inicio del
  precálculo 01:22:49 y fallo 01:22:52 en runtime_sync, HTTP 409. Esperó 136 s;
  ejecutó unos 3,55 s, sin iniciar cálculo. La asignación antigua y la nueva
  huella no coinciden; el endpoint rechaza esa discrepancia. El cuerpo concreto
  del 409 no quedó guardado, solo el error genérico.
- Segundo precálculo `worker_job_TSqdxNLr7YfS`, revisión 73: completo,
  recibido y activado en HA y worker, limpieza completa. Archivo 48.459.776 bytes;
  SHA de ambos activos comprobado directamente:
  `431e73ef52a2f5f2692f0b822cc3057ed87b5ae2b575b6333d22b4ff2dbda38e`,
  coincide con el recibo de HA.

| Medida | Local anterior 20/09 | HA real último | Local nuevo |
|---|---:|---:|---:|
| Miembros operativos | 574 | 756 | 756 |
| Recuento áreas de identidad | 108 | 121 | 121 |
| Cálculo precálculo | 383,58 s | 493,29 s | 481,81 s |
| Verificación/publicación HA | 12,58 s | 129,52 s | 15,95 s |
| Activación worker | 12,78 s | 18,75 s | 17,57 s |
| Ejecución total precálculo | 411 s | 651 s | 518 s |
| Multiversión (792 ajustes) | no comparable disponible | 763 s | 698 s |

Los modelos/datos/fecha/política difieren y HA real publica en una Raspberry;
esta tabla no es un A/B controlado ni demuestra una aceleración por el parche.
Sí muestra más trabajo respecto al local antiguo y ausencia de ralentización
observada frente al último cálculo del worker para HA real de iguales recuentos.
El ETA intermedio tampoco es la duración final.

Muestras posteriores a la activación: proceso principal HA local entre 357 y
361 MiB RSS, máximo acumulado del arranque 486,66 MiB. El muestreo empezó después
de publicar, por lo que no permite aislar su pico. Existen otros tres procesos
hijos Python; no equiparar ese RSS al total del contenedor ni dar por resuelto
el consumo inicial/cachés. No se ha medido el parche en la Raspberry.

Pendiente aceptación del usuario antes de publicar; ninguna release publicada.
