# Predictor remoto de floradas

Estado: implementación funcional y validada en el laboratorio local el
2026-08-09; pendiente de empaquetar y validar en HA real.

## Objetivo

Mantener Home Assistant como interfaz, coordinador y archivo diagnóstico, pero
permitir que el cálculo del Predictor se ejecute en un worker compatible. El
motor existente `rainmapper_core.mushroom_ml_predictor.MushroomMLPredictor`
continúa siendo la única implementación de inferencia; no se duplica código
entre HA y el worker.

## Límites de responsabilidad

- HA autentica al usuario, descubre ejecutores, presenta Auto/Manual, crea la
  operación diagnóstica, conserva progreso/resultados y renderiza la UI.
- `rainmapper_core` contiene el motor y una fachada sin HTML que ejecuta una
  petición `predictor_v1` completa.
- El worker es una calculadora: sincroniza un runtime inmutable, ejecuta la
  fachada común y devuelve progreso, resultado y telemetría.
- El navegador nunca recibe el token del worker ni conecta directamente con
  él. La comunicación continúa siendo saliente desde el worker hacia HA.

## Selección de ejecutor

Al abrir el Predictor se presenta una pantalla con `Auto` recomendado y una
opción manual por cada ejecutor disponible: HA y workers conectados, libres,
compatibles y con capacidad `predictor_v1`.

Auto ordena candidatos por tiempo esperado comparable. HA conserva, por
ejecutor y contexto compatible, la última y la mediana de las muestras frías y
calientes, el tiempo total observado por el navegador, el número de muestras,
la versión del worker y el fingerprint del runtime. Una única muestra anómala
no gobierna la selección. Un worker sin historial participa inicialmente tras
el worker predeterminado y queda marcado como `Sin mediciones`.

## Contratos

`PredictorRequest v1` declara `operation_id`, vista, especie, área, fecha,
filtro, ejecutor y fingerprint esperado. `PredictorResponse v1` contiene datos
estructurados suficientes para que HA reproduzca la UI existente, ejecutor,
runtime usado, estado frío/caliente, métricas y errores tipificados.

Los eventos `PredictorProgress v1` incluyen fase, mensaje, porcentaje y, cuando
exista, unidades completadas/totales. No se inventa un porcentaje dentro de una
operación indivisible: la UI muestra fase indeterminada hasta el siguiente hito.

La compatibilidad no compara los números de versión de HA y worker. Se negocia
mediante `predictor_v1`, versión del contrato, esquema de features y formato de
modelo. Un cambio incompatible crea `predictor_v2`.

## Runtime inmutable

HA es autoritativo y manifiesta, con tamaño y SHA-256:

- `weather_daily.parquet`;
- `weather_stations_catalog.parquet`;
- modelos `mushroom_ml_v0_*.joblib`;
- `mushroom_known_sites.json`;
- `mushroom_observation_features_v0.json`;
- metadatos necesarios para validar el modelo.

El worker descarga a staging, verifica y activa atómicamente por fingerprint.
Los ficheros sin cambios se reutilizan. Nunca se mezcla un modelo con features
o meteorología de otro runtime. El runtime anterior permanece operativo hasta
que el nuevo queda completamente validado.

## Cola interactiva y progreso

La petición es un trabajo interactivo pequeño sin promoción de artefactos. El
worker la reclama por el canal autenticado existente y envía progreso frecuente.
La espera de reclamación debe desacoplarse del heartbeat de estado o mantenerse
en un intervalo interactivo corto. HA muestra inmediatamente la pantalla de
espera, el ejecutor, la fase y una barra de progreso.

## Entrada modal desde el panel de control

El botón Predictor del panel mantiene un `href` funcional como fallback, pero
con JavaScript abre un modal compacto que reúne selección y progreso:

1. muestra Auto y los ejecutores compatibles con nombre legible, tiempo típico,
   muestras y estado de caché;
2. al confirmar, el mismo modal pasa a estado de espera y bloquea su cierre para
   no perder la referencia al trabajo interactivo;
3. para un worker, sigue el redirect del job y consulta su HTML de estado cada
   600 ms, leyendo fase, mensaje y porcentaje de atributos estables;
4. para HA local mantiene una barra indeterminada mientras termina la petición;
5. al recibir el Predictor completo sustituye el documento sin recalcular el
   resultado.

El modal está fuera del fragmento del panel que se refresca cada cinco segundos,
por lo que una actualización de estado no interrumpe la operación. La ruta
directa conserva la pantalla completa de selección/espera para navegadores sin
JavaScript y para recuperación manual.

## Diagnóstico

HA crea un único `operation_id` y conserva la operación `predictor_request` en
la caja negra. Las fases del worker son hijas de esa operación. Se distinguen
las métricas de RPi/HA, worker, transporte y navegador. El navegador envía el
tiempo hasta contenido visible; el worker puede enviar muestras de recuperación
a 60 y 600 segundos. Los logs locales del worker son auxiliares y rotatorios,
no el historial autoritativo.

## Fallos y concurrencia v1

- Solo se ofrece un worker conectado, libre y compatible.
- Si falla antes de empezar, HA permite cambiar al siguiente candidato.
- Si falla durante el cálculo, HA conserva ambos intentos y explica el fallback.
- La primera versión mantiene el bloqueo existente durante un runner y no
  solapa Predictor con reconstrucción o entrenamiento en el mismo worker.
- La ejecución local HA sigue disponible como fallback deliberado.

## Criterios de aceptación

- Paridad HA/worker con el mismo runtime.
- Menos de 8 s en carga fría del M1 y 2-3 s en caliente como objetivos iniciales.
- La RPi no carga modelos ni Parquet cuando calcula un worker.
- Sin transferencias redundantes ni activaciones parciales.
- Selección Auto explicable y selección Manual respetada.
- Progreso y diagnóstico completos en HA.

## Implementación realizada

- `mushroom_predictor_service.py` define y valida `PredictorRequest/Response
  1.0`, expande las cuatro vistas y adapta la respuesta al renderer existente.
- `mushroom_predictor_runtime.py` crea el manifiesto content-addressed,
  autoriza cada descarga y activa el runtime verificado de forma atómica. El
  worker enlaza o copia desde el runtime anterior los archivos cuyo SHA-256 no
  cambió.
- La cola incorpora `worker_predictor_v1`; el worker anuncia `predictor_v1`,
  mantiene en memoria los predictores del fingerprint activo y publica fases y
  porcentaje mediante el canal de trabajos autenticado.
- La entrada del Predictor presenta Auto y Manual. Solo enumera workers vivos,
  libres y compatibles; HA siempre permanece como alternativa local. Las
  selecciones se conservan al navegar por pestañas, filtros, especies y fechas.
- HA conserva hasta 40 muestras por ejecutor y muestra última, mediana, fría,
  caliente y número de muestras. Auto utiliza la mediana; los ejecutores aún no
  medidos quedan detrás de los medidos y siguen disponibles manualmente.
- La operación remota conserva un único monitor `predictor_request` desde la
  cola hasta el HTML final. El resultado pesado se guarda en HA; la respuesta
  de confirmación al worker se reduce para no superar el límite del protocolo.

## Matriz de validación antes de publicar

1. Completado en lab: construir el worker y confirmar `predictor_v1` y caché.
2. Completado en lab: Manual frío/caliente sin retransmisión redundante.
3. Completado en HA real: ejecutar el Predictor tanto en HA como en M1 y
   conservar mediciones comparables para ambos ejecutores.
4. Completado en HA real: Auto recomienda el M1 a partir de esas mediciones;
   el bloqueo del Predictor mientras corre un runner ya se había validado por
   separado.
5. Pendiente: descargar la caja negra tras la prueba y verificar tiempos de HA, worker y
   cliente. La telemetría de recursos propia del host worker y las muestras de
   recuperación a 60/600 s quedan como ampliación posterior; el tiempo de
   backend, caché, transporte, fases y resultado sí quedan registrados ahora.

## Resultado del laboratorio local (2026-08-09)

Validación extremo a extremo con HA `local-ha-ui` y `M1 Personal` worker 1.0.0:

- capacidad anunciada: `predictor_v1`;
- selección Manual: correcta;
- primer trabajo: completado, runtime `synchronized`, 15.808.259 bytes
  transferidos y 2,5944 s de backend;
- segundo trabajo idéntico: completado, runtime `reused`, 0 bytes transferidos
  y 0,2505 s de backend;
- ambos resultados se conservaron en HA y fueron renderizados mediante la UI
  existente, sin ejecutar de nuevo el modelo en HA;
- las muestras fría/caliente y el fingerprint quedaron guardados en el archivo
  de estadísticas del coordinador.

Esta prueba valida el protocolo y la caché dentro del M1. Sigue siendo necesaria
una medición posterior desde el navegador y la validación final con las imágenes
que se vayan a publicar.

La entrada modal también se validó manualmente en el mismo laboratorio: abre
desde el panel, recomienda `M1 Personal` por su nombre público, transforma la
selección en progreso y entrega la UI completa al terminar. La suite asociada
queda en 517 tests.

## Validación en HA real (2026-08-09)

HA `0.2.234` quedó instalada en la RPi4 y el mismo acceso modal ejecutó
correctamente el Predictor tanto en Home Assistant como en `M1 Personal`. La
estadística autoritativa de HA muestra, tras las primeras muestras comparables:

- Home Assistant: 40,2 s habituales, 1 muestra y caché local;
- M1 Personal: 3,6 s habituales, 2 muestras y caché válida;
- Auto recomienda correctamente `M1 Personal` y conserva HA como alternativa
  manual.

La muestra es todavía pequeña y no constituye un benchmark definitivo, pero
valida la selección, ejecución, retorno del resultado y persistencia de tiempos
en el despliegue real.

## Pendiente diferido: endpoint de coordinador portable

No se modifica el despliegue que ya funciona. En una evolución posterior se
deberá desacoplar la dirección anunciada a los workers de una IP o tecnología de
red concreta. El diseño deberá servir indistintamente para LAN, Tailscale,
WireGuard, otra VPN o un proxy HTTPS:

- HA tendrá una URL de coordinador anunciada explícitamente, distinta del
  listener interno y de su mapeo de puerto en Supervisor;
- el emparejamiento entregará esa URL lógica al worker y este la persistirá en
  su volumen, no en la imagen ni en Compose;
- la UI mostrará la URL anunciada y advertirá si un worker declara otra;
- el laboratorio usará un perfil separado o un override temporal que nunca
  sobrescriba el coordinador de producción;
- se preferirá un nombre DNS estable; el descubrimiento local podrá ayudar,
  pero no se asumirá que una VPN transporta mDNS;
- cambiar el puerto publicado requerirá actualizar o reiniciar los workers,
  salvo que exista previamente un punto estable de descubrimiento.

Hasta abordar esta deuda, `8100` se considera parte estable de la topología
privada y no debe cambiarse sin reconfigurar los workers emparejados.

## Evolución futura: Predictor autorizado desde MapLibre

La separación HA/coordinador/worker permite ofrecer la predicción a los usuarios
remotos que ya acceden al mapa sin exponer el worker a Internet. La arquitectura
objetivo mantiene este límite:

```text
Usuario remoto -> MapLibre/Predictor -> HA -> selector -> worker o HA fallback
```

- HA seguirá autenticando, autorizando por usuario o rol, creando jobs,
  limitando concurrencia/frecuencia y conservando diagnóstico.
- El worker seguirá siendo una calculadora privada con conexión saliente; el
  navegador no conocerá su URL ni sus credenciales.
- La primera entrega reutilizará la UI del Predictor en un panel lateral o modal
  abierto desde MapLibre, pasando zona, especie o fecha como contexto.
- Integraciones posteriores podrán colorear microáreas, consultar una zona al
  pulsarla o añadir capas por especie/fecha, sin crear un segundo motor de
  predicción.
- La autorización del mapa y la de la feature Predictor serán independientes:
  poder ver lluvia no concederá automáticamente permiso para predecir.
- Nunca se expondrán coordenadas exactas de setales o microáreas privadas. La
  respuesta pública deberá trabajar con identificadores y geometrías que el
  usuario ya tenga autorizados.
- Antes de habilitar varios usuarios se incorporarán caché de consultas
  equivalentes, límites de capacidad y una respuesta explícita cuando todos los
  ejecutores estén ocupados.

Esta evolución no forma parte de la primera release del Predictor remoto. El
modal actual y el contrato `predictor_v1` son la base reutilizable; la futura
integración necesitará su propio modelo de permisos y pruebas de exposición.
