# Retención y compactación del almacenamiento ML y del worker

Estado: **IMPLEMENTADA Y VALIDADA EN LABORATORIO LOCAL EL 2026-08-23; INSTALACIÓN,
`dry-run` Y MIGRACIÓN EN HA REAL PENDIENTES**.

Esta especificación no autoriza por sí sola a borrar datos de HA, ejecutar una
migración, reconstruir modelos, arrancar el runner, construir imágenes ni
publicar una release. La implementación se hará primero en el repositorio y en
el laboratorio local. Cualquier limpieza de `/share/rainmapper` real requerirá
una autorización explícita posterior y una previsualización exacta de los
ficheros afectados.

La implementación local ya existe, pero el interruptor
`ml_storage_reconciliation_apply` permanece desactivado por defecto. En ese
estado cada arranque de Rainmapper y cada punto terminal genera auditoría
`dry-run` y no elimina artefactos administrados. «Primer arranque» significa el
primer arranque del add-on/contenedor Rainmapper que contenga esta
implementación, no el arranque de Home Assistant Core.

La retención de 24 horas ha sido ratificada para los resultados pesados de una
ejecución operativa fallida, cancelada o interrumpida. El mantenimiento correcto
se promociona automáticamente como una sola generación y elimina sus copias
privadas al terminar; no existe ya un candidato operativo pendiente de decisión.

## Objetivo

Mantener `/share/rainmapper` permanentemente pequeño porque forma parte de los
backups de Home Assistant, sin perder:

- observaciones, catálogos, perfiles ni configuraciones autoritativas;
- fotos y vídeos de observaciones;
- el histórico meteorológico activo;
- las generaciones operativas instaladas de V2, V3, V4, V5w y V6w;
- la evidencia científica necesaria para auditar los benchmarks;
- una copia acotada de recuperación del último rebuild completo.

La solución no es una limpieza puntual. Debe asignar un ciclo de vida a cada
artefacto, impedir duplicados permanentes y reconciliar automáticamente el
almacenamiento después de cada trabajo, promoción, descarte y arranque.

## No objetivos

- No trasladar predicciones desde el worker a HA. HA sigue siendo coordinador y
  el worker sigue ejecutando la inferencia.
- No borrar ni reducir el histórico meteorológico, GIS/DEM, observaciones o
  media de usuario.
- No incorporar nuevas versiones ML. El catálogo operativo previsto queda
  limitado por ahora a V2, V3, V4, V5w y V6w.
- No conservar indefinidamente todos los modelos producidos durante un
  benchmark o cada intento fallido.
- No romper manifiestos ni dejar referencias del registro o de la cola apuntando
  a ficheros eliminados.

## Línea base observada en HA

Medición de solo lectura del montaje `/Volumes/share/rainmapper` realizada el
2026-08-23. Es una fotografía del almacenamiento entonces instalado, no una
garantía sobre ejecuciones futuras.

| Bloque | Tamaño observado | Situación |
|---|---:|---|
| `mushroom-data/ml_models` | 412 MiB | mezcla modelos activos, lotes, candidatos, benchmark y caché |
| `.worker-candidate-results` | 143 MiB | 26 directorios huérfanos suman 101,3 MiB; otros 7 siguen referenciados |
| `.worker-input-bundles` | 48 MiB | dos bundles de trabajos terminados con promoción fallida |
| `.worker-predictor-results` | 35 MiB | 39 resultados completos todavía referenciados por la cola |
| `.worker-promotion-backups` | 31 MiB | dos copias, límite vigente en código |
| **Perímetro total** | **aprox. 669 MiB** | modelos y artefactos privados del worker |

Los 50 trabajos conservados en `mushroom_worker_jobs.json` estaban terminados;
no había trabajos activos. Dentro de `ml_models` se observaron:

| Subbloque | Tamaño observado |
|---|---:|
| `.predictor-runtime-archives` | 138 MiB |
| `benchmarks` | 95 MiB |
| `batches` | 99 MiB |
| `candidates` | 69 MiB |
| `promotion-history` | 0,5 MiB |
| modelos y metadatos restantes en la raíz | aprox. 11 MiB |

El benchmark conservaba aproximadamente 80 MiB en `generations` y 15 MiB en
informe, predicciones hold-out, catálogo de calidad, manifiesto e identidad de
entrenamiento.

## Clasificación obligatoria

Cada ruta persistente debe pertenecer a una de estas clases:

1. **Autoritativa**: no se regenera sin perder información del usuario. Se
   conserva y respalda.
2. **Operativa instalada**: necesaria para predecir. Se conserva mientras esté
   referenciada por una generación instalada o por el rollback permitido.
3. **Evidencia científica**: permite explicar y auditar una decisión. Se
   conserva en forma compacta, sin binarios innecesarios.
4. **Diagnóstico terminal**: resultado pesado de una ejecución fallida o
   interrumpida. Se conserva durante 24 horas y después queda solo su resumen.
5. **Caché regenerable**: mejora rendimiento, pero no debe inflar backups.
6. **Staging o transporte**: existe solo durante una operación concreta y se
   elimina al alcanzar un estado terminal.

No se puede decidir que algo es eliminable únicamente por su antigüedad. Antes
de borrar un artefacto operativo hay que resolver sus referencias desde el
registro, los manifiestos, las promociones pendientes y el rollback vigente.

## 1. Caché TAR del runtime remoto

El TAR no es una predicción ejecutada en HA. HA construye un paquete
content-addressed con modelos, registro, perfiles, sitios conocidos,
meteorología y demás runtime; el worker autenticado lo descarga cuando su caché
está fría o cambia el fingerprint y ejecuta allí la inferencia.

La caché deja de residir en:

```text
/share/rainmapper/mushroom-data/ml_models/.predictor-runtime-archives/
```

y pasa a:

```text
/media/rainmapper/runtime-cache/predictor-runtime-archives/
```

Contrato:

- `/media` ya está montado con escritura en el add-on y GIS/DEM vive en
  `/media/rainmapper/mushroom-GIS`.
- La caché del Predictor debe estar separada de `mushroom-GIS`.
- El directorio se crea con modo `0700` y cada TAR con modo `0600`.
- Solo se conserva el TAR correspondiente al fingerprint vigente.
- El worker no monta `/media`: sigue descargando el archivo mediante el
  endpoint autenticado existente.
- La ruta debe poder configurarse mediante una variable interna. En HA se
  prefiere `/media/rainmapper`; en laboratorios sin ese montaje se usa una
  caché temporal explícita. Está prohibido volver silenciosamente a
  `ml_models/.predictor-runtime-archives`.
- Un fallo al crear la caché debe producir diagnóstico visible y un fallback
  temporal seguro, nunca una predicción local silenciosa.
- La migración elimina el TAR antiguo de `/share` solo después de verificar que
  el nuevo directorio puede crear, reutilizar y servir un TAR íntegro.

El TAR seguirá ocupando disco fuera de `/share`, pero dejará de formar parte del
backup que motiva esta especificación.

## 2. Resultados y bundles privados del worker

Debe existir un reconciliador idempotente ejecutado:

- al arrancar HA/Rainmapper;
- antes de encolar trabajo nuevo;
- al terminar, cancelar o fallar un trabajo;
- después de la promoción automática o de cualquier estado terminal.

### `.worker-input-bundles`

- Se conserva un bundle mientras el trabajo esté activo o mientras sea
  imprescindible para completar la promoción automática conjunta.
- Un trabajo cancelado o fallido conserva en la cola el resumen de error, pero
  no su copia completa de entradas.
- Un bundle de trabajo terminado se elimina tras promoción o al cerrar su
  retención diagnóstica.
- Los bundles huérfanos se eliminan después de un margen corto que cubra una
  escritura interrumpida; el informe del reconciliador debe indicar identidad,
  edad y motivo.

### `.worker-candidate-results`

- Un resultado operativo terminal no promocionado se conserva durante 24 horas
  para diagnóstico y después se elimina; la cola conserva su resumen y error.
- Después de promoción o descarte se elimina su resultado privado.
- Después de una promoción fallida se conserva el recibo, hashes y resumen del
  error; los binarios y entradas voluminosas se eliminan al cerrar la decisión.
- Los directorios que ya no aparezcan en la cola son huérfanos y se eliminan
  automáticamente tras el margen de staging.
- La cola acotada a 50 trabajos no puede ser la única fuente del recolector:
  los trabajos expulsados de la cola no deben dejar directorios inmortales.

La operación debe producir primero un plan de limpieza y después aplicarlo. Una
ruta insegura, un symlink, un recibo incongruente o una identidad diferente
bloquean esa entrada sin impedir que el resto del informe se genere.

## 3. Restos legacy de candidatos multiversión

El flujo vigente no archiva candidatos promocionables. El mantenimiento entrena
un batch operativo completo, lo verifica, lo instala y promociona conjuntamente
rebuild, ML v0 y V2–V6. `ml_models/candidates/<candidate_id>` pertenece al flujo
legacy de preparación/activación manual desde benchmarks.

El reconciliador trata esos directorios como migración legacy:

1. valida que el nombre y el manifiesto o resultado interno declaran la misma
   identidad;
2. conserva el batch que esté referenciado por una generación instalada;
3. elimina la copia legacy de `candidates` solo en modo `apply`;
4. rechaza sin borrar cualquier symlink, identidad ausente o incongruente.

La eliminación legacy nunca forma parte del tramo reversible de una instalación
operativa vigente.

## 4. Retención de generaciones y batches

El conjunto estable previsto es V2, V3, V4, V5w y V6w. Por cada versión:

- se conserva exactamente una `installed_generation_id` operativa;
- ninguna generación anterior ni batch sin referencia instalada tiene
  retención permanente por defecto.

El recolector construye primero el conjunto de referencias vivas:

```text
generaciones instaladas del registro
```

Solo puede eliminar `batches/<batch_id>` que no pertenezca a ese conjunto. El
informe debe explicar qué referencia protege cada batch o por qué resulta
eliminable. La actualización del registro y la eliminación física se ordenan de
forma que nunca exista un puntero publicado hacia un fichero ausente.

## 5. Recuperación acotada del rebuild

La política legacy de `.worker-promotion-backups` pasa de dos copias a una.

- Se conserva únicamente el estado inmediatamente anterior necesario para
  revertir la última promoción compatible.
- Al confirmar una promoción posterior se poda la copia más antigua.
- Una copia de rollback nunca se presenta como generación operativa normal.
- Si el usuario renuncia expresamente al rollback durante una migración, debe
  quedar registrado; no se infiere de una limpieza genérica.
- El historial `ml_models/promotion-history` de activación manual por versión es
  legacy y se elimina tras validar sus identidades; no protege batches.
- La instalación conjunta conserva rollback transaccional únicamente mientras
  la operación está en curso. Después solo queda la copia más reciente del
  rebuild completo en `.worker-promotion-backups`.

## 6. Benchmark compacto y evidencia científica

Todo benchmark nuevo pasa inmediatamente a `evidence_only` después de verificar
su resultado. Los benchmarks no instalan ni activan versiones operativas.

Se conservan:

- `benchmark-report.json`;
- `holdout-predictions.jsonl`;
- `quality-catalog.json`;
- identidad y revisiones de las entradas de entrenamiento;
- manifiesto específico de evidencia con hashes de los ficheros conservados;
- versión del contrato, batch y snapshot originales.

Se pueden eliminar los modelos binarios de `generations/`, pero no se debe dejar
el manifiesto instalable original aparentando integridad. La compactación debe
publicar atómicamente un estado y manifiesto de evidencia diferenciados. El
runtime no puede resolverlo como batch instalable. Para cambiar una versión se
modifica su contrato y se ejecuta después el mantenimiento operativo completo.

La UI debe seguir pudiendo mostrar el informe y las métricas históricas sin
cargar modelos binarios. Esta decisión elimina una ruta legacy de promoción y
conserva la trazabilidad científica con ahorro permanente.

## 7. Historial pesado del Predictor

`mushroom_worker_jobs.json` puede conservar el resumen ligero de hasta 50
trabajos. Las respuestas completas externalizadas no tienen la misma retención.

Política implementada localmente:

- conservar el resultado completo de los últimos 10 trabajos o durante 24
  horas, lo que proteja más resultados recientes;
- conservar siempre cualquier resultado perteneciente a un trabajo activo;
- retirar atómicamente `predictor_result_ref` de la cola antes o junto con la
  eliminación del JSON correspondiente;
- mantener en el resumen fecha, duración, estado, executor, versión del worker,
  fingerprint, tamaño, error y métricas de rendimiento;
- una lectura histórica sin payload completo debe mostrar «detalle expirado»,
  no un error de integridad ni un enlace roto.

## 8. Diagnóstico y límites de crecimiento

El mantenimiento debe exponer, como mínimo:

- bytes y número de entradas por categoría;
- activos, pendientes, instalados, rollback, huérfanos y expirados;
- último reconciliado, duración, elementos eliminados y errores;
- batches protegidos y referencia que los protege;
- ubicación y fingerprint del TAR vigente;
- estimación de espacio recuperable antes de aplicar una limpieza manual.

Los contadores deben estar disponibles en Diagnostics y en el resultado de la
acción de mantenimiento. No es aceptable una limpieza silenciosa sin auditoría.

## 9. Migración única del estado existente

La migración se divide obligatoriamente en dos modos: `audit/dry-run` y
`apply`. El primero no escribe y debe ejecutarse y revisarse antes de autorizar
el segundo en HA real.

Orden previsto:

1. detener Rainmapper, el worker normal y el runner;
2. comprobar que existe un backup reciente y que el montaje esperado es el
   correcto;
3. volver a medir tamaños y resolver todos los punteros vigentes;
4. generar un informe firmado por hashes con conservar/eliminar/mover y motivo;
5. preparar y verificar la caché TAR en `/media/rainmapper`;
6. cambiar el runtime para usarla y comprobar una descarga autenticada;
7. eliminar el TAR antiguo de `/share`;
8. reconciliar bundles, resultados y cola del worker;
9. eliminar candidatos e historiales de promoción legacy con identidad válida;
10. podar generaciones y batches no instalados y dejar un único backup del rebuild;
11. compactar todos los benchmarks instalables a `evidence_only`;
12. comprobar registro, manifiestos, hashes y cinco generaciones instaladas;
13. ejecutar predicciones dirigidas con las cinco versiones;
14. revalidar tamaños y guardar el informe final;
15. reactivar Rainmapper y mantener el runner detenido hasta autorización
    explícita para su primera ejecución manual.

Si las cinco generaciones aún no están instaladas en HA, la migración no puede
fingirlas. Debe limpiar primero solo lo inequívocamente regenerable o huérfano,
reconstruir las cinco versiones mediante el flujo normal y aplicar después la
retención estable.

## Invariantes de seguridad

- No borrar observaciones, catálogos, perfiles, sitios conocidos, media,
  credenciales, GIS/DEM ni histórico meteorológico.
- No seguir symlinks ni aceptar rutas que escapen de las raíces autorizadas.
- No borrar un batch cuyo identificador aparezca en el conjunto de referencias
  vivas.
- No borrar el último modelo ejecutable de una versión instalada.
- No publicar un registro con referencias ausentes.
- No borrar primero y corregir la cola o el registro después.
- Toda operación destructiva debe ser idempotente, auditable y reanudable.
- Un error parcial debe conservar el último estado coherente y listar los
  elementos no procesados.
- La implementación y sus pruebas no autorizan por sí mismas a ejecutar la
  migración sobre HA real.

## Pruebas exigidas antes de migrar HA

### Dirigidas

- resolución del directorio de caché `/media` y fallback local;
- permisos `0700`/`0600`, reutilización por fingerprint y poda del TAR anterior;
- reconciliación de huérfanos, terminales, pendientes y staging reciente;
- mantenimiento conjunto que instala el batch y retira sus resultados privados;
- fallo entre registro, instalación, recibo y limpieza sin pérdida de runtime;
- cálculo de referencias vivas y rechazo de batches instalados o protegidos;
- un único backup del rebuild y rollback transaccional durante la instalación;
- compactación inmediata `evidence_only` y carga posterior del informe;
- expiración de resultados del Predictor sin referencias rotas;
- `dry-run` sin escrituras y `apply` idempotente.

### Integración

- reconstrucción e instalación conjunta de V2/V3/V4/V5w/V6w;
- predicción remota fría y caliente usando el TAR en `/media`;
- reinicio de HA conservando y reutilizando la caché;
- reinicio sin caché que la reconstruye sin calcular localmente la predicción;
- Diagnostics y tamaños antes/después coherentes;
- smoke completo y `git diff --check` antes de cualquier build autorizado.

## Criterios de aceptación

La implementación se considera terminada cuando:

1. `/share/rainmapper` no contiene el TAR de runtime ni caches equivalentes;
2. no quedan bundles o resultados privados huérfanos fuera de su TTL;
3. no permanecen candidatos ni historiales de activación manual legacy;
4. todos los batches conservados tienen una referencia viva explicable;
5. solo existe un backup vigente del rebuild completo;
6. los benchmarks compactados conservan evidencia legible y no se pueden
   confundir con lotes instalables;
7. el historial del Predictor expira payloads sin romper la cola;
8. las cinco versiones instaladas siguen resolviendo sus modelos exactos;
9. una predicción fría sincroniza el TAR desde `/media` y se ejecuta en el
   worker;
10. el crecimiento posterior queda acotado por límites explícitos y visible en
    Diagnostics.

## Estimación de ahorro

Sobre la línea base observada:

- ahorro inicial estimado: 500–550 MiB;
- ahorro estable estimado después de reconstruir las cinco versiones: 400–500
  MiB, dependiente del tamaño real de V5w y V6w;
- objetivo orientativo para todo `/share/rainmapper`: 700–800 MiB frente a los
  aproximadamente 1,22 GiB observados.

Estas cifras son orientativas. La aceptación no se basa en alcanzar un número
prefijado, sino en que cada byte persistente tenga una referencia y una política
de retención justificables y en que ningún artefacto transitorio vuelva a crecer
sin límite.

## Orden de implementación propuesto

1. resolver de forma configurable la caché TAR en `/media` y probarla;
2. construir el auditor común y el modo `dry-run` sin borrado;
3. corregir el ciclo de vida de bundles y resultados del worker;
4. expirar de forma coherente los resultados completos del Predictor;
5. eliminar candidatos duplicados después de promoción;
6. implementar el grafo de referencias y la poda segura de batches/rollback;
7. añadir el estado compacto `evidence_only` de benchmarks;
8. integrar Diagnostics, pruebas transversales y documentación operativa;
9. presentar el informe `dry-run` real y detenerse para autorización antes de
   ejecutar `apply` en HA.

## Estado de implementación local y evidencia

Implementado:

- caché TAR content-addressed en
  `/media/rainmapper/runtime-cache/predictor-runtime-archives`, permisos
  privados, poda por fingerprint y fallback temporal fuera de `/share`;
- reconciliador común plan/apply para bundles, resultados, staging, huérfanos,
  payloads del Predictor y almacenamiento de modelos;
- validación del batch instalado antes de eliminar el candidato duplicado;
- referencias vivas limitadas a generaciones y batches instalados; candidatos
  e historiales de activación manual quedan clasificados como legacy;
- benchmark `evidence_only` inmediato con inventario y hashes revalidados al leerlo;
- retención diagnóstica de 24 horas para resultados operativos fallidos,
  cancelados o interrumpidos;
- retención del detalle del Predictor: últimos 10 o últimas 24 horas, lo que
  conserve más, con marcador histórico `expired`;
- informe atómico en Diagnostics y opción HA
  `ml_storage_reconciliation_apply`, desactivada por defecto;
- inventario visible de cualquier TAR legacy que aún permanezca en `/share`;
  su retirada sigue siendo el paso manual posterior a verificar el TAR servido
  desde `/media`, no una eliminación ciega de arranque;
- hooks en arranque, preencolado, finalización, cancelación y promociones.

Evidencia local observada el 2026-08-23:

- 312 pruebas dirigidas de rutas retiradas, mantenimiento completo, transporte,
  compactación, reconciliación y UI: correctas;
- compilación de los módulos modificados: correcta;
- `dry-run` sobre `docker-data`: 59 entradas planificadas, 190.107.758 bytes
  recuperables, cero errores y cero eliminaciones; conserva el batch instalado
  y el rollback de rebuild más reciente.

No validado todavía:

- instalación ni ejecución del `dry-run` en HA real;
- modo `apply`, migración, predicción remota fría/caliente, reinicio o
  reutilización del TAR en HA;
- smoke completo y `git diff --check` finales;
- bump, build, publicación o release.
