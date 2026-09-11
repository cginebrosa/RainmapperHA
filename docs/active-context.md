# Active Context

Ventana operativa de RainmapperHA al 11 de septiembre de 2026. No es un
histórico. Revalidar siempre repositorio, contenedores, datos y servicios antes
de asumir que este estado sigue vigente.

## Release HA 0.2.302 publicada

- El usuario autoriza publicar HA el 11/09/2026 después de decidir mantener el
  contador de días secos. Bump y changelog preparados para `0.2.302`.
- Smoke completo correcto: 1.384 tests, 57,548 s; sintaxis, fixtures y demás
  controles correctos. Primer intento bloqueado por el sandbox en tres pruebas
  con servidor local; repetición fuera del sandbox correcta. Tras el bump se
  comprobaron solo los tres metadatos de versión y los cache-busters.
- HA local y worker reconstruidos/recreados antes del bump mecánico. Comparados
  144 Python efectivos de HA y 76 del worker: todos idénticos al worktree.
  Las huellas de ambas configuraciones de coordinador siguen siendo las de la
  especificación semanal. Worker `1.1.1` healthy, capacidad semanal v2; sin
  release de worker ni cambios de URL. No se inició entrenamiento ni precálculo.
- Revalidación SQLite de solo lectura: publicación completa, 553 celdas,
  469 miembros lag con horizonte correcto y corte 10/09; 61 parejas con una
  misma familia semanal, seis parejas Cantharellus con fallback diario y
  84 celdas sin miembros en las tres especies fuera de temporada.
- `./scripts/build-push-ha-image.sh` terminó con código 0. GHCR verificado:
  `0.2.302` y `latest` comparten el índice
  `sha256:cb6b54e9b32727521567ccaedb18dcdaf509a9be6ed710acb0d43a42da058e4e`,
  con manifests `linux/amd64` y `linux/arm64` y sus attestations.
- Código, pruebas, bump, changelog y documentación se reúnen en el único commit
  `Release Home Assistant 0.2.302`. Se excluye expresamente el JSON de
  observaciones del usuario, con SHA-256
  `f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
- Pendiente de que el usuario instale y confirme HA real. No confundir la
  publicación con una instalación. No repetir smoke, builds ni trabajos por
  cerrar documentación o publicar el commit.

## Estado operativo comprobado

- Workspace: `/Users/carlosginebrosa/Developer/RainmapperHA`; rama `inicial`.
- Base previa de esta release: `46c9215656897b6598dfb72af87388aff7245a61`
  (`0.2.301`). Consultar Git para la identidad del commit final `0.2.302`.
- HA `0.2.302` publicada en GHCR; última instalación real confirmada por el
  usuario: `0.2.301`. La instalación de `0.2.302` sigue pendiente de confirmación.
- `mushroom-data/mushroom_observations.json` también está modificado, pero es
  dato del usuario: no editarlo, restaurarlo, borrarlo ni incluirlo ciegamente
  en ningún commit. Los datos vivos del laboratorio están en `docker-data/`.
- HA local está activo en `127.0.0.1:8101` con imagen
  `rainmapperha:local-ha-ui`, ID
  `sha256:8f29de0a4e8506d501dc4d97be0efa13b532b7bdd80d7e2349f23347cf67fe6a`.
  La UI responde y las huellas de los módulos modificados coinciden con el
  worktree.
- El worker privado está healthy e idle con `rainmapper-worker:1.1.1`, imagen
  `sha256:2367842bd216ac2aa8b253377f56e346622b53a2f591e2bbe96aaf04571ede2a`.
  Sus carriles foreground/background están idle y las huellas de los tres
  módulos del selector coinciden con HA local y el worktree.
- Asociaciones persistidas del worker, revalidadas sin exponer tokens:
  - principal: `http://100.111.77.48:8100`;
  - adicional `coordinator_fde2e9b1c6c1f5b2`:
    `http://rainmapper-ha-ui:8100`;
  - límite: cuatro coordinadores.
  No cambiar ninguna URL sin autorización expresa para ese destino.
- La caché GIS del worker está válida: 13 ficheros, 6.424.592.573 bytes y
  fingerprint
  `sha256:7410f2e2482b77688027440fa047344bba65285fa2f9e812c07c65f769981574`.
  La caché Predictor está válida con fingerprint
  `sha256:ad96514103ee64fc9302419a67ac662f5bc1f2270fa8c1a547178cb9282fd002`.

## Cambios de 0.2.302 validados localmente

### Continuidad semanal del Predictor

- La opción `predictor_weekly_model_selection`, desactivada por defecto y
  activada en HA local, selecciona una familia `lag_event` común por
  especie/área para los siete días, con horizontes h1--h7 y corte común.
- El orden es cobertura de aplicabilidad semanal primero y evidencia fiable
  agregada después. No gana quien dé probabilidades más altas ni quien sea
  primero más días.
- La familia elegida no cambia si una fecha queda fuera de aplicabilidad: ese
  día se abstiene. Una pareja sin familia común conserva actualmente la
  selección diaria y queda auditada como `daily_fallback`.
- El worker anuncia `predictor_weekly_model_selection_v2`; HA no asigna esa
  política a un worker que no declare la capacidad.
- Pasaron 521 pruebas dirigidas de selector, servicio, SQLite, variables,
  worker, empaquetado y web. HA local y worker se reconstruyeron desde el mismo
  código; pasaron además seis regresiones temporales dentro de cada contenedor.
  Se compararon 142 ficheros Python de HA, su `run.sh` y labels, y 76 Python del
  worker con el worktree: ninguna diferencia.
- El SQLite activo local está completo, usa política `weekly_lag_event_v2`, cubre
  2026-09-11--2026-09-17, nueve especies, 79 parejas especie/área, cinco versiones, 469
  miembros y 553 celdas de cobertura. Su `artifact_id` es
  `sha256:457a09931d22c4d16c28a4075fecf739cd39c7eaa84b098d3fb4443ce4958475`.

### Corrección temporal y precálculo lanzado por el usuario

- El selector anterior podía elegir una familia `fixed_gap_7d`. En el SQLite
  anterior, `boletus_aereus/olvan` usaba la misma V6w `fixed h7` del 10 al 16 de
  septiembre, siempre con `horizon_days = 7`.
- Para la predicción del 13 de septiembre el corte meteorológico es el día 6,
  por lo que no ve los 56,1 mm del día 9. Para la del día 16 el corte es el día
  9 y sí los ve. El dato no se ha perdido: es la semántica con la que se entrenó
  `fixed h7`, pero resulta inadecuada como ancla semanal.
- Corrección aceptada e implementada: en modo semanal seleccionar únicamente una familia
  `lag_event`, mantener versión/perfil/estimador y usar su horizonte natural
  h1--h7. Así toda la semana comparte el último día meteorológico completo.
  `fixed h7` permanece disponible en selección diaria y detalle técnico.
- No se debe alimentar `fixed h7` con meteorología más reciente ni fingir que
  es h1--h7: cambiaría el contrato sin reentrenarlo.
- Los modelos `lag_event` h1--h7 ya existen. El usuario lanzó y confirmó el fin
  del nuevo precálculo. El job `worker_job_tcxhsuDyln_L` está `complete`, con
  activación HA/worker confirmada y revisión 54. No entrenar ni lanzar otro
  precálculo desde Codex.
- Se conserva el `daily_fallback` auditado ya acordado cuando no existe una
  familia común. No se reabre como propuesta de abstención semanal completa.
  Ese fallback puede usar `fixed h7`, pero debe distinguirse de la selección
  semanal con corte común; conserva las limitaciones temporales del modo diario.
- La revisión de solo lectura del 11 de septiembre confirmó tres familias
  `lag_event` comunes h1--h7 para Aereus/Olvan: V6w de 30/60/90 días. Sus
  artefactos están presentes. El plan de corrección y su evidencia están en la
  especificación semanal; el plan está aceptado e implementado y los resultados persistidos del
  precálculo se revalidaron antes de la publicación de 0.2.302.
- La revisión global del mismo catálogo y las 79 parejas del SQLite encontró
  61 con familia de retardo completa, seis de Cantharellus que necesitarían
  fallback diario y doce ya sin ganador toda la semana. Son conteos de catálogo,
  previos al control de aplicabilidad del nuevo precálculo. La corrección y su
  auditoría deben abarcar el conjunto, no solo Aereus/Olvan.
- Las doce parejas sin ganador corresponden a especies fuera de temporada:
  `hygrophorus_latitabundus`, `hygrophorus_marzuolus` y
  `morchella_elata_complex`; `species_context.season_phase_by_date` confirma
  `out_of_season` en las siete fechas para las tres.
- Nueva identidad de política `weekly_lag_event_v2`; los SQLite
  `weekly_aggregate` anteriores se sirven como desactualizados con aviso de
  que pueden omitir lluvia conocida. Se verificó ese aviso y el motivo
  `weekly_selection_policy_outdated` leyendo Aereus/Olvan dentro de HA local.
- Antes de la intervención del usuario, la parada se verificó sin trabajos nuevos: cola local con diez `complete`
  y cuatro `failed`, ambos carriles idle. `desired.json` y
  `active-receipt.json` conservaron exactamente sus SHA-256; no se sustituyó el
  artefacto activo. Las dos configuraciones de coordinador conservaron sus
  huellas y URLs y las observaciones protegidas conservaron su SHA-256.

### Meteorología observada en el Predictor

- Cambio de presentación en `mushroom_predictor_weather_ui.py`, invocado por
  la tarjeta existente y empaquetado en el Dockerfile HA. No cambia inferencia,
  worker, contratos, artefactos ni probabilidades; no necesita precálculo nuevo.
- Resumen con título y fechas en una sola línea, suma de lluvia y última lluvia
  disponible de al menos 0,01 mm. Por indicación del usuario, las trazas menores
  se ignoran al elegir esa última fecha, sin modificar los datos del modelo ni
  los acumulados. Caso confirmado en el precálculo local: Edulis/Espinavell,
  objetivo 11/09/2026, contiene 0,0013102441455423875 mm el 10/09 y
  42,73318528702588 mm el 09/09; el resumen debe mostrar el 09/09 y 42,73 mm.
  Corrección validada con 342 pruebas dirigidas de presentación y web.
  Probabilidad y modelo seleccionado comparten también una fila; se adaptan al
  ancho disponible en móvil. Ajuste final validado con los 334 tests web.
  Las leyendas de mínima/máxima conservan sus colores y se centran en la misma
  fila que las fechas inicial/final de temperatura y humedad (siete pruebas
  dirigidas de meteorología tras este ajuste visual).
  Desplegable «Meteorología observada» con barras diarias, curvas de temperatura
  y humedad mínimas/máximas, lectura al tocar/señalar y tablas accesibles.
  `sessionStorage` conserva abierto/cerrado al cambiar de fecha en la pestaña.
- Corrección posterior al probar las tarjetas semanales: su controlador usa
  `document.open/write`, que borra listeners pero conserva propiedades de
  `window`. El guard global impedía volver a registrar controles después del
  primer cambio de día. Se ata el guard al elemento raíz del documento nuevo.
  La prueba anterior de navegación completa no cubría ese recorrido; ahora
  se reprodujo el fallo con `predictor_launch_script()` real y respuestas HTML
  simuladas (sin trabajos), y se verificaron tres clics sucesivos con estados
  abierto/cerrado/abierto y lectura de barras funcional tras cada sustitución.
- Se retiraron, a petición del usuario, la leyenda verde/gris/rayado y la
  instrucción de señalar/tocar. La lectura aparece en un recuadro flotante
  sobre el gráfico, sin añadir altura. Se oculta al salir, tocar fuera o pulsar
  Escape; se conserva la lectura accesible por teclado y se evitan tooltips
  nativos duplicados. Probado con el controlador real de tarjetas semanales,
  comprobando altura invariable, límites de pantalla y cierre con Escape.
  También se retiró el texto explicativo situado encima de la franja semanal.
  La explicación sobre estimaciones diarias, lluvia débil y datos ausentes se
  trasladó al tooltip del título «Meteorología observada», sin párrafo visible.
  La ventana orientativa de fructificación y el desplegable de detalle técnico
  se sitúan después del origen de selección y antes del bloque meteorológico.
  Se retiró también la línea «Última lluvia de al menos 5 mm» del detalle de
  la tarjeta, por petición posterior del usuario. Los datos y cálculos
  subyacentes permanecen intactos.
- Datos exclusivamente del resultado seleccionado persistido. Un valor ausente
  no se convierte en cero; las curvas se interrumpen en los huecos. Versiones
  con acumulados muestran periodos y sus resúmenes de temperatura/humedad,
  sin inventar series diarias ni fecha de última lluvia.
- Auditoría de lectura de los 469 miembros actuales (2.676.234 bytes): 322
  diarios (V5w/V6w) y 147 con acumulados (V2/V3/V4); ninguno guarda viento en
  sus variables. El render anterior a retirar textos midió como máximo 95.905
  bytes de HTML por resultado. No se amplió ningún payload HA--worker.
- Validación: 341 tests de UI/web; Chrome móvil a 390 px, interacción y
  persistencia abierto/cerrado al navegar entre fechas. Sin desbordamiento de
  página. HA local reconstruido; ninguna publicación ni cambio en HA real.
- Duración del precálculo: cálculo anterior 505,173 s y último 245,102 s;
  transferencia/activación similares. Cobertura y activación completas. La
  telemetría no permite atribuir con certeza todo el ahorro a una fase interna.

### Wunderground y estado de fuentes

- HA `0.2.300` añadió detección de respuestas actuales obsoletas según
  `epoch`/`obsTimeUtc`, reintentos entre variantes `Accept-Encoding` y elección
  exclusiva de la respuesta con timestamp más reciente. El scraper HTML sigue
  siendo el fallback final.
- HA `0.2.301` hizo configurable y validado el orden de encodings; el valor
  vigente es `gzip,identity,deflate`. El runner registra recuperación o
  persistencia de caché antigua y los fallbacks al scraper.
- Los modos mensual y semanal son mutuamente excluyentes. El worktree corrige
  el modo mensual para pedir desde el día 1 hasta hoy y, los días 1--7, incluir
  también el mes anterior. El semanal pide hoy y los seis días anteriores,
  incluso al cruzar mes. Un backfill explícito conserva sus fechas exactas.
- El archivador ya publica `total_rows` y `updated_rows` a partir de contadores
  existentes y mantiene `rows` como alias compatible. El panel muestra ambas
  columnas sin volver a recorrer los CSV.
- La activación de un nuevo precálculo conserva los trabajos automáticos
  terminales dentro del historial ligero global de 50 entradas; la retención
  de artefactos pesados sigue siendo independiente.

### GIS francés y almacenamiento del worker

- RGE ALTI Francia 5 m está integrado como cuarto DEM tras Catalunya, Andorra
  e IGN MDT25 de Puertomingalvo. El TIFF definitivo tiene SHA-256
  `3e86d6c2ee4e3677dd895de369045b8f49c02a23902771692177b7a60256860f`,
  CRS EPSG:2154 y cobertura válida de las microáreas francesas probadas.
- HA local recupera altitud, pendiente y orientación para las microáreas de
  Font-Romeu y Quérigut. HA real ya ejecuta `0.2.301`, que contiene el soporte;
  queda volver a revisar y aplicar los campos desde la UI.
- La limpieza auditada del volumen persistente del worker eliminó únicamente
  jobs antiguos y una generación GIS inactiva: pasó de 18.084.029 KiB a
  7.144.228 KiB, liberando 10,43 GiB. Se preservaron runtimes, cachés y la
  generación GIS activa.
- Infoclimat se descartó como fuente nueva para esta zona por su cobertura útil
  insuficiente. Meteo-France queda como diseño futuro; actualmente Font-Romeu y
  Formiguères se cubren con estaciones Wunderground existentes.

## Releases y entrenamiento cerrados durante la sesión

- HA `0.2.298`: alta automática de especies en el catálogo de tuning. El
  entrenamiento real con `cantharellus_cibarius_sl` superó el fallo original;
  no repetirlo sin una causa nueva.
- HA `0.2.300`: DEM francés, sincronización GIS incremental, modos API
  Wunderground y defensa frente a variantes CDN antiguas.
- HA `0.2.301`: orden configurable de encodings y retención de precálculos
  automáticos en trabajos recientes. Es la release instalada en HA real.
- El entrenamiento y los precálculos posteriores terminaron correctamente
  según confirmación del usuario. La nueva ejecución semanal local fue sólo para
  validar el cambio posterior del worktree.

## Próximos pasos, por prioridad

0. El usuario autorizó y se completó la comparación aislada posterior con el
   selector real: [plan y resultados](reports/mushroom-dry-spell-selector-audit-2026-09-11.md).
   V2/V3/V4 con/sin contador, todos sus perfiles y algoritmos vigentes; V5w/V6w
   idénticos entre brazos. Dos exámenes cronológicos con entrenamiento,
   evidencia de selección y examen separados. 990 intentos de ajuste final,
   978 completados. Semanal sin contador: mejora del error 0,43 % en 2025–2026,
   empeoramiento 8,28 % en 2023–2024 sobre casos comunes. En el segundo se
   pierden 49 escenarios de ocho observaciones de Ou de reig/Olvan: cambia el
   ámbito de evidencia, V6w deja de estar en la lista semanal común y los
   candidatos restantes no son aplicables. Diario: empeora 0,59 % / mejora
   3,32 %, respectivamente. El usuario decide conservar el contador el
   11/09/2026; auditoría cerrada, sin cambios de contratos ni activación.
   Evidencia insuficiente para entrenar ciertos modelos por especie con las
   particiones reservadas, incluido Edulis; no declarar validación universal.
   Observaciones, registro, manifiesto y precálculo protegidos conservan sus
   huellas. 31 tests dirigidos correctos; ninguna publicación HA.
   Antecedente: se completó primero una auditoría aislada de racha seca:
   [plan, resultados y límites](reports/mushroom-dry-spell-threshold-audit-2026-09-11.md).
   Se compararon retirada del contador, umbrales diarios 1–5 mm y acumulados
   5/10 mm en 3 días. 1.602 ajustes en memoria; entradas históricas del 05/09.
   Inventario de 17 especies, comparación descriptiva en seis y selección
   interna válida en tres. Sin contador: reducción media de error 1,05 %/1,27 %
   (grupos 14/7 días) en las seis; 0,30 %/0,66 % en las tres con selección interna,
   donde la incertidumbre incluye ausencia de mejora. Ningún umbral muestra
   una ventaja estable. La retirada favorece sobre todo Rovelló, Edulis y
   Pinícola; Aereus empeora en media. No se activaron modelos, no se lanzó
   precálculo ni se publicó HA. Su ventaja descriptiva no se reprodujo de forma
   estable en la comparación ampliada del selector. No sustituir el contador
   ni eliminarlo de los contratos actuales por iniciativa de Codex.
1. El usuario debe instalar HA `0.2.302` y confirmar el resultado. La opción
   semanal sigue desactivada por defecto; requiere activación explícita y un
   worker con capacidad `predictor_weekly_model_selection_v2`.
2. La UI local fue aceptada por el usuario. La lectura final del precálculo
   confirmó 61 familias semanales constantes, seis fallback diarios y doce
   parejas sin miembros fuera de temporada. No repetir entrenamiento ni
   precálculo por iniciativa de Codex.
3. Tras la instalación, comprobar visualmente en HA «Meteorología observada» y
   las columnas `Total rows`/`Updated rows`; el intervalo mensual está cubierto
   por las pruebas incluidas en el smoke de release.
6. Reaplicar y revisar GIS/DEM en las microáreas francesas de HA real desde la
   UI de `0.2.301`.
7. Retomar la auditoría multiespecie de aplicabilidad desde Rovelló / Els Ports /
   2026-09-07 y diseñar la probabilidad vetada sin convertirla en recomendación.
8. Después: medir transporte HA--worker en RPi4 y completar el CLI por
   `coordinator_id`.

## Riesgos y dudas activas

- Investigación de trazas cerrada: el usuario conserva el contador vigente.
  La publicación de 0.2.302 se ha completado.
  Diagnóstico confirmado el 11/09/2026 en código y precálculo local: la racha
  seca de V2/V3/V4 se corta con cualquier valor `> 0` (`_dry_spell` en
  `mushroom_ml_biology_v3.py`; también ocurre en los constructores de variables
  de observaciones y experimentos). Pinophilus/Espinavell para el 11/09 guarda
  `dry_spell_observed_at_cutoff=0`, con 0,0013102441455423875 mm el 10/09.
  V5/V6 no reciben ese contador: usan series meteorológicas y estado hídrico;
  `soil_water_drydown_7d` mide pérdida de agua, no días consecutivos secos.
  La propuesta inicial de 0,01 mm para ese contador queda retirada: omitía la
  revisión y batería existentes del 05/09. Se revalidó el JSON experimental:
  el umbral de 1 mm no mejora de forma consistente y quitar el contador tampoco
  mejora todas las combinaciones. Se mantiene la decisión de no cambiar los
  contratos actuales. La ampliación bibliográfica del 11/09 documenta el umbral
  meteorológico de 1 mm, la intercepción forestal y por qué 10 mm de lluvia no
  equivalen a humedecer 1 cm de suelo; véase sección 13 de
  `docs/mushrooms/literature/prediction/rainmapper_dry_spell_variable_review.md`.
  Las dos auditorías aisladas del 11/09 están ejecutadas y enlazadas arriba.
  La ampliación con selector no justifica una retirada general del contador;
  los intervalos incluyen ausencia de diferencia y aparece pérdida de cobertura.
  No se ha modificado ningún cálculo operativo ni lanzado entrenamiento/precálculo
  operativo.
- Los cambios de `0.2.302` están publicados y validados localmente; no
  atribuirlos a HA real hasta que el usuario confirme la instalación.
- Elegir una identidad de modelo constante no garantiza coherencia temporal si
  el contrato semanal es `fixed h7`.
- El fallback diario acordado resuelve ausencia de familia común, pero puede
  reintroducir saltos entre días y cortes distintos. Debe quedar identificado
  como excepción; no reabrir su política para corregir Aereus/Olvan.
- La aplicabilidad puede vetar por una desviación normalizada alta aunque la
  diferencia absoluta sea pequeña. No ampliar umbrales globalmente sin la
  auditoría multiespecie.
- Una probabilidad vetada sólo puede mostrarse como diagnóstico inequívocamente
  separado de una recomendación, color operativo o ranking.
- Wunderground puede volver a servir variantes CDN desactualizadas. Conservar
  detección por timestamp, trazas de reintento y fallback; no asumir que un
  encoding concreto será siempre el fresco.
- HA real corre en una Raspberry Pi 4 compartida: no repetir entrenamientos,
  precálculos, escaneos completos ni copias grandes para diagnosticar.
- No tocar las URL de coordinador ni el JSON de observaciones protegido.

## Archivos relevantes

- Continuidad semanal y limitación `fixed h7`:
  `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`.
- Selector y materialización:
  `rainmapper_core/mushroom_ml_multiversion_comparison.py`,
  `rainmapper_core/mushroom_predictor_precompute.py` y
  `rainmapper_core/mushroom_predictor_service.py`.
- Pruebas del selector:
  `tests/test_mushroom_ml_multiversion_comparison.py`,
  `tests/test_mushroom_predictor_precompute.py` y
  `tests/test_mushroom_predictor_service.py`.
- Wunderground: `rainmapper_core/sources/wunderground/daily_api.py`,
  `rainmapper_core/rainmapper.py`, `rainmapper-app/run.sh` y
  `rainmapper-app/config.yaml`.
- Contadores de fuente: `rainmapper_core/weather_history_archive.py` y
  `rainmapper-app/app/web_server.py`.
- GIS francés: `rainmapper_core/mushroom_gis_lab.py`,
  `rainmapper_core/mushroom_rebuild_snapshot.py` y
  `docs/mushrooms/france-sources/`.
- Aplicabilidad: `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`.
- Worker multicoordinador:
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`.
- Flujo de release: `docs/release-flow.md`.
