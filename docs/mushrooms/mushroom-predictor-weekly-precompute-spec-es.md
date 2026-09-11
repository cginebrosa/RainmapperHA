# Precálculo semanal distribuido del Predictor

Estado al 11 de septiembre: corrección temporal semanal implementada en el
worktree y plan aceptado por el usuario. Pasan 521 pruebas de los módulos
afectados. La aceptación funcional con un SQLite nuevo sigue pendiente:
el usuario ha pedido detenerse justo antes de lanzar el precálculo y lo
lanzará personalmente. No publicar ni instalar una release HA.

Nota de evolución: la selección fiable definida posteriormente en
`mushroom-predictor-reliability-selection-spec-es.md` reemplaza, para la ruta
ordinaria, la obligación de calcular todos los miembros y elegir entre ellos
durante la predicción. El SQLite local instalado ya representa el contrato del
selector sellado. Ese selector publica una resolución
por especie/área/día operativo: para el día `N` compara previamente `lag hN`
con `fixed h7`. El precálculo no retargetea candidatos ni repite el ranking;
calcula el miembro exacto y persiste también, para ese mismo candidato, la
evidencia separada del área y de la especie —Wilson, `x/x`, observaciones
hold-out y floradas— para presentarla junto a la probabilidad.
La misma composición sellada se aplica como mínimo en `Esta semana`, `Por
especie` y `Consulta por fecha`.

Desde el contrato de artefacto `1.6`, la cadena completa y ordenada de
candidatos alternativos permanece una sola vez en el catálogo de calidad
inmutable. Durante el cálculo se recorren esos candidatos hasta encontrar el
primero aplicable, pero el SQLite semanal conserva únicamente el miembro que se
usará, su posición en la cadena, el número de candidatos considerados y los
motivos compactos por los que se descartaron los anteriores. Así la RPi4 recibe
la decisión ya resuelta sin tener que repetir la selección ni procesar miles de
copias de la misma evidencia estadística.

La validación local cruza por identidad completa las 504 celdas: 420 ganadores
y 84 abstenciones, sin discrepancias ni miembros sobrantes. La ejecución no se
divide por familia ganadora: una pareja especie/área se procesa una sola vez y
en esa ejecución usa, para cada uno de los siete días, exclusivamente el
candidato sellado correspondiente. Así se conservan las 623 respuestas lógicas
con 143 ejecuciones para la cobertura actual: 72 semanas de área, 56 consultas
de especie/día, 8 vistas semanales y 7 resúmenes globales. Los resultados y el
contexto meteorológico común se reutilizan durante todo el lote.

La revalidación del 5 de septiembre detectó una regresión de materialización,
no una expansión científica necesaria. El primer precálculo posterior al
reentrenamiento escribió los candidatos alternativos completos en cada celda:
21.182 miembros y 477.696.000 bytes. Al conservar solo el candidato resuelto se
redujo a 420 miembros; una segunda revisión eliminó también la repetición de la
cadena y dejó el artefacto en 69.967.872 bytes. El análisis de páginas mostró
que aproximadamente 40 MB eran espacio libre interno dejado por las
sustituciones durante la construcción. El artefacto final construido con
`VACUUM` ocupa 29.233.152 bytes, mantiene `quick_check = ok` y tiene
`freelist_count = 0`; por eso el constructor compacta ahora su base privada de
staging antes de validarla y publicarla atómicamente.

## Objetivo

Eliminar el cálculo interactivo repetido de las consultas ordinarias del
Predictor mediante un artefacto semanal regenerable que cubra todas las
especies, áreas y fechas con el candidato fiable ya elegido. El cálculo pesado se
ejecutará exclusivamente en el worker operativo preferido. Home Assistant
seguirá siendo coordinador y conservará una copia verificada para sus sesiones
locales.

El precálculo es el único origen de resultados ordinarios en HA real. No es una
fuente científica —se regenera desde el runtime—, pero sí la frontera que evita
inferencias interactivas en HA. Si falta, está incompleto, no cubre la petición
o no puede leerse, HA muestra indisponibilidad y solicita actualizarlo; no
ejecuta cálculo científico local ni crea automáticamente un trabajo remoto.

## Evidencia y dimensión actuales

La inspección de solo lectura del runtime montado el 2026-08-29 confirmó:

- ocho especies entrenadas;
- 72 parejas especie/área con observaciones;
- 504 parejas especie/área/día para una ventana de siete días;
- cinco versiones operativas instaladas: V2, V3, V4, V5 y V6;
- V4 como versión preferida en ese momento.

El Predictor conserva además la predicción base V0 que necesitan algunas
vistas. El artefacto deberá incluirla, pero V0 no se contará como una sexta
versión operativa.

Resultados remotos retenidos del 2026-08-21 muestran, como evidencia histórica
y no como benchmark del código futuro:

- dos Recommender fríos de un día y versión preferida: 25,1903 s y 31,0454 s;
- dos consultas semanales frías con selección multiversión completa: 6,6963 s
  y 8,3009 s para una pareja especie/área;
- una repetición exacta cacheada: 0,0059 s de backend;
- aproximadamente 1 MiB para un Recommender de un día con la preferida.

Un único batch podrá compartir transporte, carga de modelos, contexto
meteorológico, matrices de variables e inferencia. La hipótesis inicial es un
tiempo frío de 5--10 minutos en el M1 actual, pero no se considerará confirmada
hasta medir el nuevo trabajo completo.

## Alcance funcional

Cada artefacto cubrirá:

- la fecha de emisión y los siete días consecutivos desde esa fecha;
- todas las especies entrenadas declaradas por el runtime;
- todas las áreas con observaciones de cada especie;
- la predicción base V0 necesaria para las vistas actuales;
- el único candidato sellado para cada especie/área/día, incluida su identidad
  completa, ámbito territorial o fallback y evidencia resumida;
- fenología, aplicabilidad, abstenciones e interpretaciones necesarias para
  reproducir el resultado vigente.

Las especies fuera de temporada conservarán su estado fenológico y cobertura,
pero no obligarán a ejecutar modelos que el motor actual omite.

El artefacto podrá acelerar `Recommender`, `Esta semana`, `Por especie` y
`Consultar fecha` cuando toda la petición esté dentro de su cobertura.
`Historial`, fechas fuera de la ventana y cualquier modalidad futura no
representada quedan indisponibles en HA real hasta disponer de un contrato
precalculado o de una futura acción manual explícita en worker. No se mezclarán
silenciosamente filas precalculadas y filas calculadas en vivo dentro de una
misma respuesta.

La implementación nueva almacena un único miembro ordinario por celda y el
lector no admite que la selección multiversión de la petición cambie el ganador
sellado. Esta composición se aplica por igual a la fecha concreta, la matriz de
siete días de `Por especie` y el recomendador global `Esta semana`. Los
controles comparativos antiguos de la UI se retirarán después de validar
visualmente la migración; mientras existan no modifican el resultado sellado.

«Único miembro» significa el candidato finalmente utilizable en esa
especie/área/día. Si el candidato preferido queda fuera del dominio observado,
el constructor prueba el siguiente de la cadena sellada y materializa ese
fallback. Una abstención no materializa ningún miembro. La cadena completa no
se replica dentro de respuestas, contexto de especie ni filas operativas.

## Formato del artefacto

Se usará un único fichero SQLite inmutable por publicación lógica. Python y las
imágenes actuales de HA y worker ya incluyen `sqlite3`; el 2026-08-29 ambas
informaron SQLite 3.46.1. La implementación no añadirá paquetes Python ni
binarios del sistema por este motivo.

En Home Assistant, el directorio activo será
`/media/rainmapper/predictor_precompute`, fuera de `/share` y de sus backups.
El worker conservará su copia en su almacenamiento persistente propio.

SQLite se usará como contenedor indexado, no como un segundo motor científico.
El esquema mínimo tendrá:

- metadatos e identidad del artefacto;
- cobertura por especie, área y fecha;
- predicciones base serializadas mediante el contrato vigente;
- miembro operativo normalizado por especie, área, fecha e identidad completa
  del candidato seleccionado;
- contadores de cobertura y diagnóstico de construcción.

La clave primaria lógica será, según la tabla, una combinación de especie,
área, fecha y candidato sellado —versión, perfil, contrato, horizonte y
estimador—. Los accesos usarán
consultas parametrizadas. Los payloads estructurados conservarán el contrato
canónico del Predictor; no se creará una interpretación científica alternativa
en SQL.

El fichero se cerrará sin WAL ni archivos laterales antes de calcular su
digest. Se construirá en la misma partición de destino con nombre temporal,
transacción completa, validación de esquema y `PRAGMA quick_check`; después se
hará `fsync` y sustitución atómica. Los lectores que ya tengan abierto el
artefacto anterior podrán terminar sobre su inodo; las sesiones nuevas abrirán
el nuevo.

## Identidad y validez

La identidad canónica incluirá como mínimo:

- versión del esquema de precálculo;
- versión de los contratos Predictor consumidos;
- fingerprint completo del runtime;
- fecha de emisión, inicio y fin de cobertura;
- lista ordenada de especies entrenadas;
- versiones instaladas, generaciones instaladas y perfiles operativos;
- política de selección diaria o semanal agregada;
- contadores esperados de especies, áreas, días, versiones y miembros.

Se distinguirán dos identificadores:

- `artifact_id`, derivado solo de esa identidad científica canónica y, por
  tanto, estable para los mismos inputs;
- `file_sha256`, calculado sobre los bytes concretos y usado para integridad de
  transporte y publicación.

Tiempos, host constructor y demás telemetría volátil no formarán parte de
`artifact_id`. Un recálculo forzado conservará `artifact_id`, pero no se
presupondrá que reproduce el mismo `file_sha256` salvo que la implementación
demuestre serialización determinista. Las copias HA y worker procedentes de una
misma construcción sí deberán tener exactamente el mismo `file_sha256`.

El fingerprint del runtime seguirá siendo la autoridad para meteorología,
modelos, contenido científico del registro de versiones, perfiles, features,
áreas conocidas y catálogo de estaciones. El registro canónico empaquetado
mantiene un default interno estable y no sigue la preferencia de UI. En el
contrato nuevo el SQLite cubre la selección sellada por especie/área/día, no
todas las alternativas instaladas; cambiar el puntero preferido no altera su
identidad.
No se introducirá una regla débil basada únicamente en la hora del runner o el
`mtime` del SQLite.

## Política opcional de continuidad semanal

La opción HA `predictor_weekly_model_selection`, desactivada por defecto,
decide cómo se ordenan los candidatos sellados al construir el precálculo:

- `false` conserva la selección independiente existente para cada día;
- `true` elige por pareja especie--área una familia común a los siete días.
  Primero maximiza cuántos días supera la aplicabilidad operativa y, entre las
  familias con la misma cobertura, usa la evidencia de fiabilidad agregada de
  toda la semana. No cuenta simplemente cuántos días gana cada candidata ni
  favorece el porcentaje de predicción más alto.

La familia incluye versión, contrato temporal, perfil y estimador. El horizonte
no forma parte de la familia: cada fecha conserva el horizonte que le
corresponde. La familia elegida se mantiene toda la semana. La aplicabilidad
sigue siendo una barrera diaria: si esa familia queda fuera de rango en una
fecha, el resultado se abstiene y no cambia a otra familia. Nunca se publica
una probabilidad vetada como recomendación.

Si el catálogo fiable de una pareja especie--área no contiene ninguna familia
común a los siete días, esa pareja vuelve de forma explícita a la selección
diaria sellada y registra `daily_fallback` con el motivo
`no_reliable_family_covering_week`. Esta excepción no invalida ni aborta el
precálculo completo; el resto de parejas conserva la política semanal.

La política forma parte de la identidad inmutable del artefacto. Cambiar la
opción no exige entrenamiento, pero sí un nuevo precálculo. La capacidad
original era `predictor_weekly_model_selection_v1`; la corrección temporal requiere ahora
`predictor_weekly_model_selection_v2` y política `weekly_lag_event_v2` en la
identidad. `weekly_aggregate` identifica el comportamiento anterior: puede
leerse como desactualizado con aviso específico, pero no satisface una petición
de la identidad nueva ni se admite para construir nuevos artefactos. Los
artefactos históricos de política diaria conservan su identidad.

### Incidencia del precálculo anterior: una familia semanal `fixed h7` usa cortes distintos

La prueba local de continuidad semanal confirmó que una misma familia puede
quedar elegida durante los siete días, pero descubrió un efecto temporal no
deseado cuando esa familia pertenece al contrato `fixed_gap_7d`.

Caso reproducido en el SQLite activo local, emitido para el 10--16 de septiembre
de 2026:

- `boletus_aereus / olvan` usa en las siete fechas la familia
  `biology_v6_windowed_smooth_hierarchical`, contrato
  `fixed_gap_7d_biology_v6_smooth_hierarchical_v2`, perfil
  `smooth_window_30d_plus_physical_state` y estimador
  `smooth_shared_logistic_v1`;
- las siete filas tienen `horizon_days = 7`;
- para el 13 de septiembre la interfaz muestra como última lluvia significativa
  el 17 de agosto, porque el corte meteorológico de `fixed h7` es el 6 de
  septiembre y, por tanto, todavía no puede ver los 56,1 mm del 9 de septiembre;
- para el 16 de septiembre el corte es el 9 de septiembre y la misma familia sí
  ve esa lluvia.

No es una pérdida de datos ni un fallo del IDW. Es la semántica vigente de
`operational_selections`: un contrato `fixed_gap_` exige siempre horizonte 7,
mientras que un contrato de retardo usa el horizonte correspondiente al día de
predicción. El resultado es coherente con el entrenamiento de `fixed h7`, pero
es inadecuado como ancla de continuidad semanal: dentro de una misma franja, un
día cercano puede ignorar meteorología ya conocida que otro día posterior sí
utiliza.

### Corrección temporal implementada

Cuando `predictor_weekly_model_selection` esté activo, la familia común semanal
se elige únicamente entre contratos `lag_event`:

1. Mantener constantes durante la semana versión, perfil y estimador, además de
   la familia de contrato `lag_event`.
2. Conservar el horizonte natural de cada fecha, `h1` a `h7`. Con fecha de
   emisión 10 de septiembre, los siete horizontes comparten como último día
   meteorológico completo el 9 de septiembre.
3. Ordenar las familias de retardo primero por cobertura de aplicabilidad de los
   siete días y después por la evidencia fiable agregada, como hace ya el
   selector semanal.
4. Mantener la familia ganadora toda la semana. Si queda vetada en una fecha,
   abstenerse ese día sin cambiar de familia y sin convertir la probabilidad
   vetada en recomendación.
5. Conservar `fixed h7` en el catálogo, en el detalle técnico y en el modo de
   selección diaria. No alimentarlo con un corte más reciente ni presentarlo
   como un `hN`: eso cambiaría el significado con el que fue entrenado.

Los contratos `lag_event` h1--h7 ya están presentes en las generaciones
operativas, por lo que esta corrección no requiere entrenamiento. Sí requiere
generar un nuevo precálculo después de reconstruir HA local y worker desde el
mismo código. El selector ya está corregido; el precálculo lo lanzará el usuario.

Se conserva el `daily_fallback` auditado ya acordado cuando no existe una
familia fiable común: la aclaración del usuario del 11 de septiembre mantiene
esa política y no autoriza sustituirla por abstención semanal completa. Al
restringir el agregado a `lag_event`, la ausencia de una familia de retardo
completa debe derivar a esa selección diaria, con motivo explícito. En ese
caso puede ganar `fixed h7` conforme al contrato diario, pero la pareja no debe
presentarse como una semana con familia y corte comunes. Esta excepción
conserva las limitaciones temporales del modo diario; no debe confundirse con
la corrección de una pareja que sí tiene familias de retardo completas.

Puntos cubiertos por la implementación:

- filtrar las familias candidatas del agregado semanal antes de
  `weekly_aggregate_resolution_index`, sin alterar la selección diaria sellada;
- impedir que `prioritize_weekly_resolutions_by_applicability` vuelva a admitir
  como ancla una familia `fixed_gap_`;
- persistir en la auditoría la política temporal semanal, el corte meteorológico
  común y los horizontes h1--h7;
- añadir una regresión con una lluvia entre los cortes del 13 y el 16 de
  septiembre que demuestre que ambos resultados semanales usan el último corte
  común disponible;
- comprobar también cobertura, abstención sin cambio de familia y el caso sin
  familia `lag_event` común.

La validación proporcional será: pruebas dirigidas del selector y del
precálculo; reconstrucción de HA local y worker preservando sus coordinadores;
un único precálculo local; e inspección de `Aereus/Olvan` y de una pareja con
veto. No hace falta repetir entrenamiento ni la suite completa salvo que el
cambio final amplíe el alcance.

### Revisión del 11 de septiembre y plan aceptado

El problema, en términos de la pantalla: los siete días deben poder usar la
lluvia que ya conocíamos al emitir la semana. Para la semana del 10--16 de
septiembre, la lluvia del día 9 debe tener seis días de antigüedad al predecir
el 15 y siete al predecir el 16. No debe aparecer de golpe solo el día 16.
Esto afecta a los datos que alimentan el modelo, no solo a la frase de la UI.

Evidencia revalidada mediante lecturas locales, sin ejecutar predicciones ni
entrenamiento:

- `docker-media/rainmapper/predictor_precompute/active.sqlite3`, consultado en
  modo de solo lectura, conserva `artifact_id`
  `sha256:99bf7d11fad9bfd14836f09dd81b785730042b1eed2a6f8f323994ffbebccdae`,
  publicación `complete`, política `weekly_aggregate` y ventana 10--16/09/2026.
- Sus siete miembros de `boletus_aereus/olvan` son V6w de 30 días, contrato
  `fixed_gap_7d_biology_v6_smooth_hierarchical_v2`, estimador
  `smooth_shared_logistic_v1` y horizonte 7. El miembro del 15 conserva lluvia
  significativa del 17/08; el del 16 conserva la del 09/09, 56,06639958758446 mm.
- El corte se obtiene del código actual como `target_date - horizon_days`:
  el 15 usa el 08/09 y el 16 usa el 09/09. No hay un campo de corte explícito
  en los metadatos de esos miembros V6w; esas fechas se derivan de la fórmula,
  no de un campo SQLite inexistente.
- El catálogo `quality-catalog.json.gz` del batch
  `operational_20260909T184116Z`, bajo
  `docker-media/rainmapper/mushroom-derived/ml_models/batches/`, coincide con
  el SHA-256 declarado en su manifiesto. Entre las versiones representadas
  por el SQLite tiene tres familias fiables de retardo comunes a los siete
  días para Aereus/Olvan: V6w de 30, 60 y 90 días, todas con
  `smooth_shared_logistic_v1`. Sus tres archivos de modelo existen y el
  manifiesto declara soporte h1--h7. No se ha calculado cuál ganará tras
  aplicar los controles diarios de aplicabilidad.

Revisión del conjunto: se cruzaron las 79 parejas especie/área de `coverage`
del SQLite con las cadenas selladas del catálogo, usando primero la resolución
del área y, si no existe, la de especie, como hace
`operational_reliability_selections_from_catalog`. Se limitaron los candidatos
a las cinco versiones representadas en el SQLite y se exigió hN en cada día N.

| Especie | Parejas con familia de retardo completa | Parejas que necesitarían fallback diario | Parejas ya sin ganador los siete días |
| --- | ---: | ---: | ---: |
| `amanita_caesarea` | 8 | 0 | 0 |
| `boletus_aereus` | 8 | 0 | 0 |
| `boletus_edulis` | 16 | 0 | 0 |
| `boletus_pinophilus` | 12 | 0 | 0 |
| `cantharellus_cibarius_sl` | 0 | 6 | 0 |
| `hygrophorus_latitabundus` | 0 | 0 | 4 |
| `hygrophorus_marzuolus` | 0 | 0 | 4 |
| `lactarius_deliciosus` | 17 | 0 | 0 |
| `morchella_elata_complex` | 0 | 0 | 4 |
| **Total** | **61** | **6** | **12** |

Son conteos de cobertura del catálogo, no resultados de un precálculo nuevo:
la aplicabilidad diaria todavía puede reducir los días publicables. Las seis
parejas de Cantharellus son `la_masella`, `olvan`, `riu_de_cerdanya`,
`salteguet`, `santa_maria_de_merles` y `selva_del_camp`. El SQLite actual
contiene 126 miembros fijos y 343 de retardo; por tanto la revisión no se limita
a Aereus/Olvan. Las doce parejas sin ganador conservan sus abstenciones
existentes; no son una política nueva de abstención semanal. El usuario aclaró
que están fuera de temporada y se revalidó contra
`species_context.season_phase_by_date`: las tres especies tienen
`out_of_season` en las siete fechas del SQLite activo.

El criterio será genérico para todas las especies, áreas, versiones operativas
y futuras fechas de emisión. Cada pareja puede elegir una familia distinta;
lo común es la fecha hasta la que se conoce la meteorología, no la lluvia de
lugares distintos ni un modelo único para todas las especies. Ningún filtro o
excepción debe depender del nombre Aereus, Olvan, V6w ni de septiembre de 2026.

Plan aceptado; implementación y pruebas completadas, precálculo pendiente:

1. **Seleccionar familias completas de retardo.** En
   `weekly_aggregate_resolution_index`, admitir únicamente contratos
   `lag_event` de versiones operativas con el candidato exacto hN en cada día
   N=1..7. Mantener versión, contrato, perfil y estimador constantes. El código
   actual intersecta las cadenas de las filas `winner`; la revisión debe
   exigir los siete días antes de declarar una familia completa, sin ignorar
   silenciosamente un día sin candidato fiable. La falta de familia completa
   conduce al fallback diario acordado, conservando sus abstenciones previas.
2. **Dar a toda la semana el mismo último día de datos.** Con emisión I,
   objetivo I+N-1 y horizonte N, el corte será siempre I-1. Filtrar antes de
   preparar meteorología y ejecutar inferencias; en
   `mushroom_predictor_service.py` validar los horizontes de los candidatos
   sellados del modo semanal antes de cualquier retargeteo. No transformar
   un modelo `fixed h7` en un modelo de retardo. En
   `prioritize_weekly_resolutions_by_applicability`, impedir también que una
   familia fija o incompleta vuelva a entrar como ancla semanal.
3. **Conservar la regla de elección.** Primero elegir la familia que permita
   publicar más días válidos y después desempatar con la evidencia ya sellada.
   Si la ganadora no es aplicable un día, solo ese día se abstiene y la familia
   se mantiene. No elegir por la probabilidad más alta ni cambiar umbrales.
4. **Identificar el resultado y sus excepciones.** Persistir de forma compacta
   la regla temporal, fecha común de corte y horizontes efectivos. Identificar
   el fallback diario y su motivo en las vistas ordinarias con texto sencillo
   en los tres idiomas; en él no declarar un corte común que no existe. Separar
   en la identidad científica y negociación de capacidad del worker la nueva
   semántica semanal de la antigua: un SQLite o worker que aún permita anclas
   fijas no puede satisfacer silenciosamente la política corregida. Conservar
   la identidad y comportamiento del modo diario. Si se permite leer un
   artefacto anterior, mostrar que usa la política anterior y requiere
   actualización. No basta con modificar una etiqueta o forzar un recálculo
   conservando una identidad que confunda ambos comportamientos.
5. **Probar y revisar en local.** Añadir regresiones dirigidas para lluvia del
   día 9 presente en las entradas h1--h7, antigüedades seis/siete para el 15/16,
   exclusión de familias fijas aunque tengan mejor puntuación, horizonte
   incorrecto, familia incompleta, fallback diario intacto y veto de un día
   sin cambio de familia. Cubrir distintas especies, áreas, contratos/versiones
   y emisiones que crucen mes/año; comprobar que la elección de una pareja no
   afecta a otra y conservar las abstenciones ya selladas. Comprobar también
   identidad/capacidad, compactación
   de auditoría y equivalencia de la semana, especie y consulta por fecha.
   Después de aceptar el plan, reconstruir HA local y worker desde el mismo
   código preservando exactamente sus dos asociaciones; verificar las huellas
   dentro de ambos contenedores; ejecutar un único precálculo local y auditar
   todas las parejas y sus siete días: identidad de familia, corte, horizonte,
   abstenciones y excepciones. Revisar además visualmente ejemplos de semana
   completa, veto diario y fallback, incluido Aereus/Olvan. No entrenar.

La probabilidad de cada fecha puede cambiar al elegir otro modelo y darle la
meteorología correspondiente; no se promete un porcentaje ni que suba por haber
llovido. El criterio de aceptación es que use la información temporal correcta
y respete las reglas de selección y aplicabilidad.

La implementación filtra antes del cálculo, valida el horizonte exacto antes
del retargeteo y añade `common_weather_cutoff`/`horizon_days` a la auditoría
semanal y `cutoff_date` a los metadatos V5/V6. La selección diaria permanece
intacta. Los avisos de fallback y de precálculo anterior existen en inglés,
español y catalán; se muestran también en las vistas compactas.

HA local y worker se reconstruyeron y recrearon con las imágenes
`sha256:99377fb336adf959abfea0fd8c8d463528e83eb46c7d837d9269e64fe2df59f0`
y `sha256:2367842bd216ac2aa8b253377f56e346622b53a2f591e2bbe96aaf04571ede2a`.
HA responde HTTP 200 y el worker `1.1.1` está healthy, con ambos carriles idle y
capacidad v2 anunciada. Pasan seis pruebas temporales dentro de cada uno.
Coinciden con el worktree 142 ficheros Python de HA, su arranque y labels, y los
76 ficheros Python empaquetados en el worker. Sus configuraciones persistidas
de coordinador conservaron exactamente los SHA-256
`5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10`
y `22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0`.

Comprobación ejecutada: 521 pruebas en `test_mushroom_weekly_lag_selection`,
`test_mushroom_predictor_precompute`, `test_mushroom_ml_multiversion_comparison`,
`test_mushroom_predictor_service`, `test_mushroom_ml_runtime_features`,
`test_mushroom_worker_service`, `test_mushroom_worker_packaging` y
`test_web_server_auth`. La prueba SQLite sintética cubre lectura en consulta,
semana y recomendador; no ejecuta el precálculo operativo. La auditoría de solo
lectura del catálogo mediante el selector corregido comprobó las 553 celdas y
reprodujo las 61/6/12 parejas anteriores.

El usuario autorizó implementación, pruebas y reconstrucción local, con parada
expresa antes de lanzar el precálculo: lo ejecutará él. Cualquier publicación o
instalación de HA requiere después validación local y autorización expresa de
release. El JSON de observaciones y las URLs de coordinadores siguen protegidos.

Antes de usar un artefacto se comprobarán su identidad, esquema, cobertura y
estado de publicación. El digest SHA-256 completo se verificará al cruzar la
frontera worker→HA y al recuperar una instalación dudosa, no en cada consulta.
Una sesión caliente leerá metadatos y filas indexadas sin rehashear el fichero.

Cambiar meteorología, modelos o generaciones instaladas, perfiles, features o
cualquier otra entrada científica del runtime hace que el artefacto deje de
ser el vigente. Cambiar sólo la versión preferida no. No obstante, una copia
anterior podrá seguir sirviendo temporalmente respuestas completas como
`desactualizadas` si conserva integridad, cobertura y todas las versiones
solicitadas. Aunque la meteorología no cambie, una fecha de emisión distinta
produce otra ventana y otra identidad.

La UI mostrará la fecha/hora de activación local del fichero cuando reutilice
un artefacto desactualizado. Ese `mtime` es información operativa de la copia
activa, no parte de su identidad científica ni prueba de vigencia.

## Ubicación y autoridad

El worker preferido construirá y conservará el fichero dentro de su volumen.
Al terminar lo subirá una sola vez a HA con tamaño, SHA-256, identidad y
contadores. HA lo recibirá en staging, verificará el contrato y lo publicará
atómicamente dentro del árbol resuelto por `mushroom_paths`.

La misma identidad y el mismo SHA-256 deberán quedar activos en ambos lados:

- el coordinador consultará primero su copia para cualquier petición de la UI,
  aunque la sesión tenga seleccionado el worker; un hit no crea ningún job y
  conserva ese ejecutor únicamente para un posible fallback;
- la versión actual no envía automáticamente misses al worker; una posible
  acción manual futura será explícita y separada del acceso ordinario;
- HA nunca ejecutará el trabajo programado de precálculo.

Esta prioridad de lectura respeta la comunicación saliente worker→HA actual y
evita pagar el polling de un job solo para consultar un fichero idéntico. La
copia local del worker sigue siendo necesaria para misses recuperables,
continuidad del ejecutor y validación de equivalencia, pero no será un requisito
para el hit rápido servido por el coordinador.

### Publicación coordinada en dos fases

No existe una sustitución atómica entre dos máquinas. La activación se hará con
un protocolo explícito:

1. el worker construye y valida una copia local en staging, sin cambiar su
   puntero activo;
2. sube exactamente esos bytes y el manifiesto al staging de HA;
3. HA valida identidad, cobertura, tamaño, esquema y SHA-256, publica su copia
   atómicamente y responde con un recibo sellado;
4. solo después de recibir ese recibo el worker publica atómicamente su copia
   local.

Si se pierde la confirmación, el worker consultará el recibo por `artifact_id`
y `file_sha256` antes de reintentar o activar. Un resultado sustituido nunca se
considerará activo.

Solo habrá un artefacto activo y un temporal en construcción por ubicación. El
anterior se conserva únicamente mientras se construye y valida el nuevo y se
sustituye atómicamente al publicarlo. Después no existe rollback de precálculo:
solo queda el último artefacto completo y válido. Si una cancelación, error o
caída brusca deja SQLite temporales o journals en staging, la siguiente
ejecución los elimina antes de construir; la salida normal limpia además todos
los temporales asociados al job. Estos ficheros son caché regenerable, no
forman parte de la retención científica de modelos, benchmarks o históricos.

## Disparo y estado deseado

El coordinador mantendrá un único estado deseado de precálculo para el worker
operativo preferido. Lo persistirá mediante escritura atómica, no solo en
memoria, con revisión monotónica, `artifact_id`, runtime fingerprint, ventana,
worker objetivo, origen del trigger y `force_recompute`. Tras un reinicio podrá
reconciliar ese deseo con la cola y con el recibo del artefacto publicado.

Se solicitará después de:

- completar correctamente un scheduled runner y publicar su runtime;
- promover o revertir modelos;
- publicar cualquier otra entrada científica que cambie el fingerprint del
  Predictor.

Un runner fallido no publicará un deseo nuevo. El scheduled runner solicitará
siempre el trabajo aunque la huella resultante coincida; si el artefacto exacto
ya existe y está validado, el worker podrá completar el job por reutilización
sin recalcular.

### Lanzamiento manual desde el panel de control

El panel de control principal de Rainmapper ofrecerá una acción explícita
`Lanzar precálculo`. Permitirá recuperar un intento fallido, generar el primer
artefacto sin esperar al siguiente runner y ejecutar pruebas controladas en el
entorno real.

La acción mostrará antes de encolar:

- worker operativo preferido al que quedará asignada;
- fingerprint y ventana de siete días que se van a calcular;
- estado e identidad del artefacto activo, si existe;
- job pendiente o en ejecución para esa misma identidad, si existe.

El lanzamiento ordinario respetará reutilización y latest-wins: si ya existe un
artefacto exacto y válido podrá completar por reutilización, y si el mismo job
está activo abrirá su estado en vez de duplicarlo. Cuando el artefacto sea
válido, la UI ofrecerá por separado `Recalcular igualmente`. Esta variante
sellará `force_recompute=true`, ejecutará el batch completo y solo sustituirá el
fichero activo después de verificar que el nuevo resultado tiene la misma
identidad científica.

El lanzamiento manual:

- usará el runtime activo sin modificar meteorología, modelos ni perfiles;
- irá siempre al worker preferido, aunque esté desconectado;
- nunca ofrecerá HA como destino ni hará fallback de cálculo a HA;
- aparecerá en la misma tabla de trabajos y podrá cancelarse o sustituirse;
- conservará el Predictor actual como fallback durante todo el proceso;
- respetará la misma autorización y protección de acciones del panel de
  control; no introducirá un endpoint público nuevo.

Forzar el recálculo no cambia la identidad ni conserva una segunda copia
permanente. Sirve para medir y verificar el batch sobre los mismos inputs; una
construcción fallida no toca el artefacto activo.

El deseo se asignará al worker configurado como preferido, no al ejecutor que
Auto elegiría para una consulta concreta. Si está desconectado, el coordinador
conservará el job en cola. Si no existe todavía un worker preferido compatible,
conservará el deseo pendiente y no hará fallback a HA.

La capacidad se negociará como `predictor_precompute_v1`. Un worker conocido
pero temporalmente desconectado conservará su última capacidad anunciada. Un
worker antiguo o incompatible dejará el deseo visible como pendiente de worker
compatible en vez de ejecutar un contrato que no entiende.

## Sustitución latest-wins

El precálculo no formará una cola histórica. Para cada worker solo interesará
la identidad deseada más reciente:

- un job anterior todavía en cola o reclamado sin empezar pasará a
  `superseded` y será sustituido;
- un job anterior en ejecución recibirá cancelación cooperativa y el nuevo
  quedará en cola inmediatamente;
- el worker comprobará cancelación o sustitución entre bloques acotados de
  especie/área/fecha/versión;
- si el job antiguo termina durante la carrera, HA rechazará su activación si
  su identidad ya no coincide con el estado deseado;
- el artefacto activo anterior solo se reemplazará después de verificar el
  nuevo, nunca al encolar ni al empezar a calcular.

La sustitución no reutilizará a ciegas filas calculadas con otro fingerprint.
Una futura reutilización incremental deberá demostrar identidad exacta de cada
entrada antes de incorporarse.

## Dos carriles en el worker

El worker actual mantiene un único trabajo activo. La implementación deberá
introducir dos carriles lógicos independientes:

1. `foreground`, con capacidad uno para todos los jobs existentes;
2. `background_precompute`, con capacidad uno y reservado al precálculo.

Un precálculo activo no hará que el worker aparezca ocupado para el carril
foreground. El worker deberá poder reclamar, iniciar, cancelar y terminar una
predicción interactiva, reconstrucción, entrenamiento, benchmark o prueba
mientras conserva el job de precálculo.

La reclamación será consciente del carril: el slot foreground ignorará jobs de
precálculo y el slot background solo reclamará ese tipo. Los jobs foreground
tendrán prioridad de reclamación y ejecución. Estado, lease, cancelación y
heartbeat serán independientes por carril; no se reutilizará el actual slot
único como un booleano compartido.

Cada precálculo fijará el manifiesto y fingerprint inmutables al crear el job y
mantendrá una lease sobre ese runtime hasta terminar, cancelar o ser
sustituido. La limpieza no podrá retirar fuentes con lease. El batch usará una
instancia de servicio o un namespace de caché aislado por fingerprint y nunca
leerá a mitad de ejecución el enlace al runtime activo; así, un runner o una
promoción simultáneos no podrán mezclar dos generaciones dentro del SQLite.

La disponibilidad de dos slots no obliga a competir sin límites por CPU y RAM.
El precálculo tendrá prioridad de recursos inferior, paralelismo acotado y
checkpoints frecuentes. Podrá ceder o suspender temporalmente su cálculo cuando
un foreground pesado lo requiera, manteniendo su slot y reanudándolo después.
No podrá retener locks globales del runtime, caché o transporte durante una
unidad larga ni impedir heartbeats, control o cancelación.

El heartbeat y la UI distinguirán ambos carriles. El estado foreground seguirá
gobernando si el worker es elegible para una consulta ordinaria; no se reducirá
a un único booleano `busy`.

## Lectura desde la UI y fallback

Entrar en Predictor no cargará el SQLite completo en memoria. Cada ejecutor
abrirá su copia en modo de solo lectura, validará una vez los metadatos y
consultará únicamente las filas necesarias mediante índices.

Antes de crear un job interactivo, el coordinador intentará resolver la petición
contra su copia verificada. El orden será:

1. artefacto vigente y exacto;
2. artefacto anterior compatible, marcado como desactualizado;
3. cálculo vivo únicamente en un worker elegido explícitamente;
4. respuesta `sin precálculo disponible` si no existe artefacto utilizable ni
   worker explícito.

HA real no ejecutará bajo ningún concepto el cálculo científico local del
Predictor. Esta prohibición se impondrá en el servidor, no solo ocultando una
opción en la UI. MapLibre será exclusivamente de lectura: vigente, anterior
compatible o pendiente de actualización; abrirlo no creará trabajos.

Un hit vigente o desactualizado:

- no crea un trabajo científico nuevo;
- no sincroniza de nuevo el runtime;
- no carga modelos ni Parquet;
- reconstruye la misma respuesta canónica y conserva el mismo renderer;
- registra identidad, filas leídas y tiempo de lookup.

`PRAGMA quick_check` y el hash completo se ejecutarán al construir, recibir o
recuperar un artefacto dudoso, no al entrar en cada página. El camino caliente
solo comprobará el recibo activo, metadatos, esquema y cobertura necesarios
para la petición.

La optimización comparte una ejecución semanal por pareja especie/área aunque
el ganador cambie entre días, porque no retargetea un candidato común: consulta
la resolución sellada independiente de cada fecha y precalienta únicamente
esos siete candidatos. No ejecuta todas las versiones ni prepara ventanas
meteorológicas que ningún ganador necesite. Al escribir el SQLite, cada miembro
se admite únicamente si coincide de forma exacta con la selección sellada de
su especie/área/día; una coincidencia solo en el número total de miembros no
demuestra cobertura científica correcta.

No podrán reutilizarse ni siquiera como desactualizados:

- ausencia de fichero;
- esquema desconocido;
- cobertura parcial o petición ausente;
- fallo de `quick_check` o de lectura;
- versión o selección no representada;
- fecha o vista fuera de alcance.

Una diferencia de fingerprint, generaciones o meteorología será un motivo de
obsolescencia, no por sí sola un miss, siempre que el artefacto anterior supere
los demás gates. La respuesta mostrará, como mínimo:

- `Precálculo del <fecha y hora>`;
- `Necesita actualizarse`;
- motivos conocidos: modelos reentrenados, meteorología actualizada o ambos;
- si ya existe una actualización pendiente o en ejecución.

Diagnostics registrará `fresh`, `stale` o `missing`, la identidad utilizada y
el motivo. No se mezclarán filas de artefactos distintos ni filas vivas dentro
de una respuesta.

## Transporte, seguridad y límites

El artefacto usará el canal autenticado worker→HA y un endpoint específico; no
se incrustará en `mushroom_worker_jobs.json` ni reutilizará el límite del
resultado interactivo. Antes de aceptar bytes, HA impondrá un máximo separado
y comprobado contra la medición del prototipo, además de validar longitud,
SHA-256, job, worker, identidad deseada y esquema.

El primer prototipo medirá tamaño real antes de fijar ese máximo. La release no
podrá dejar un límite ilimitado ni una configuración de usuario arbitraria.

No se aceptarán rutas proporcionadas por el worker. HA elegirá staging y
destino. Un SQLite corrupto, sobredimensionado, incompleto o perteneciente a una
generación sustituida se descartará sin tocar el artefacto activo.

## Observabilidad

La UI de trabajos mostrará `Precálculo semanal del Predictor` y distinguirá:

- esperando al worker preferido;
- reutilizando artefacto exacto;
- preparando runtime;
- calculando, con unidades completadas y totales reales;
- verificando SQLite local;
- subiendo;
- verificando y publicando en HA;
- superseded, cancelado, fallido o completado.

El resultado persistirá al menos:

- duración por fase;
- especies, áreas, días, versiones y miembros;
- filas escritas y leídas;
- hits de workspace, modelos y comparaciones;
- tamaño y SHA-256;
- runtime fingerprint e identidad del artefacto;
- cancelación, sustitución o reutilización;
- hits, misses y motivos de fallback de la UI.

`Uploading` solo se mostrará mientras haya transferencia real. Preparación,
integridad y publicación tendrán fases separadas.

## Compatibilidad y despliegue seguro

El precálculo se añadirá detrás de una capacidad nueva y no modificará la
semántica de `predictor_v1`. HA y worker podrán actualizarse en distinto orden:

- HA nuevo con worker antiguo conserva el deseo pendiente y usa el Predictor
  actual;
- worker nuevo con HA antiguo no recibe jobs de precálculo y usa el Predictor
  actual;
- un artefacto de esquema desconocido nunca se usa;
- desactivar o retirar el nuevo camino deja intacto el cálculo vigente.

No se conectará el trigger del runner hasta validar escritor, lector, identidad,
fallback, sustitución, concurrencia, transporte y publicación atómica de forma
aislada.

## Plan de implementación

1. Definir contratos, identidad y módulo SQLite con pruebas unitarias de
   escritura, lectura, corrupción, cobertura y sustitución atómica.
2. Implementar el batch semanal local sobre `PredictorService`, compartiendo
   workspace meteorológico, modelos e inferencia entre toda la matriz, y
   comparar sus resultados con el camino actual.
3. Añadir job, capacidad, estado deseado y semántica latest-wins sin conectarlo
   todavía al runner.
4. Separar los dos carriles del worker y validar que cualquier job foreground
   puede reclamarse y terminar mientras el precálculo está activo.
5. Implementar transferencia única, validación y publicación en HA, conservando
   copia idéntica en el worker.
6. Integrar lookup coordinador-first, lookup local del worker y fallback
   completo en las vistas cubiertas.
7. Añadir al panel el lanzamiento manual, reutilización, seguimiento y
   `Recalcular igualmente` sin permitir ejecución en HA.
8. Medir tiempo, CPU, RAM, tamaño, disco y equivalencia en laboratorio.
9. Solo después, conectar los triggers de runtime y scheduled runner.

## Criterios de aceptación

- Ausencia, invalidez o corrupción del artefacto producen la misma respuesta
  que el Predictor actual mediante fallback.
- Para el mismo runtime y petición, la respuesta precalculada coincide con la
  respuesta viva después de excluir únicamente métricas de ejecución y caché.
- Todas las probabilidades, ganadores, abstenciones, criterios, diagnósticos y
  ordenaciones mantienen equivalencia.
- Las 504 celdas se cruzan contra el catálogo sellado: cada una de las 420 con
  ganador contiene exactamente su versión, contrato, perfil, estimador y
  horizonte, y ninguna de las 84 abstenciones contiene un miembro operativo.
- Una petición cubierta se sirve sin crear job, cargar modelos o leer Parquet,
  con objetivo de backend <= 1 s en el M1 y HA de referencia.
- Tras reentrenar o actualizar meteorología, el artefacto anterior compatible
  continúa sirviendo con fecha/hora y aviso `Necesita actualizarse` hasta la
  activación atómica del sustituto.
- En HA real, un miss no ejecuta cálculo científico local. Sin artefacto
  utilizable ni worker explícito se muestra indisponibilidad; MapLibre nunca
  provoca cálculo ni crea un job.
- HA y worker aceptan exactamente el mismo SHA-256 para una construcción y
  producen respuestas equivalentes desde sus copias.
- HA publica antes de que el worker active localmente; pérdida de confirmación,
  reinicio o resultado sustituido no pueden dejar dos identidades consideradas
  activas para el mismo estado deseado.
- Un runner nuevo sustituye un precálculo obsoleto y un resultado tardío no
  puede reemplazar el artefacto deseado.
- Un worker desconectado conserva el job en cola sin ejecutar nada en HA.
- El panel puede encolar manualmente el precálculo sin runner, abre el job ya
  activo en vez de duplicarlo y permite forzar una medición completa sobre la
  misma identidad.
- Tras cancelar o fallar el intento que corresponde al estado deseado vigente,
  un nuevo lanzamiento manual crea una revisión y un job nuevos aunque el
  artefacto completo anterior siga siendo reutilizable. También funciona si la
  cancelación cooperativa todavía está alcanzando su punto seguro o si HA se
  reinició y ya no conserva en memoria el job: la revisión deseada solo se
  considera satisfecha cuando coincide con el recibo de publicación.
- Un job foreground puede empezar y terminar mientras existe un precálculo en
  el segundo carril; heartbeat y cancelación continúan respondiendo.
- Reinicios del coordinador o worker recuperan de forma determinista cola,
  estado deseado y artefacto publicado.
- La construcción fallida no altera el artefacto anterior y no deja temporales
  no acotados.
- Diagnostics separa cálculo, transferencia, verificación y publicación.
- La validación incluye `git diff --check`, pruebas dirigidas, suite pertinente,
  smoke y prueba end-to-end de fallback antes de cualquier release.

## Fuera de alcance

- Cambiar fórmulas, features, gates, perfiles o selección científica.
- Entrenar modelos como parte del precálculo.
- Ejecutar automáticamente el precálculo en HA.
- Precalcular historial completo o fechas fuera de los siete días.
- Cambiar la retención de modelos, benchmarks, históricos o datasets.
- Compartir un artefacto entre fingerprints distintos por semejanza parcial.
- Exponer SQLite o credenciales del worker al navegador.
