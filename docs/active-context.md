# Contexto activo — release 0.2.319, 22/09/2026

Leer primero [codex-start-here.md](codex-start-here.md). Este documento contiene
lo necesario para retomar; [todo.md](todo.md) amplía prioridades. El
[contexto anterior](reports/session-context-before-close-2026-09-20.md) es archivo,
no una segunda fuente de estado actual.

## Estado y siguiente paso

### HA 0.2.319 publicada — pendiente instalar en HA real

El usuario confirmó que el detalle completo funciona en local y pidió publicar.
Smoke completo correcto: 1.725 pruebas, 52 skips, 82,406 s; registro
`/private/tmp/rainmapper-0.2.319-smoke-final.log`. Se corrigieron tres referencias
obsoletas a worker 1.1.4 en el test de empaquetado (la versión efectiva es 1.1.5).
Bump HA, cache-busters y changelog 0.2.319, sin cambios adicionales de cálculo.
Imagen publicada con script terminado código 0; tags 0.2.319/latest verificados
con el mismo digest y manifests linux/amd64 y linux/arm64. Instalación a cargo
del usuario. Ver [informe de release](reports/release-ha-0.2.319-2026-09-22.md).

La cola local conserva como últimos entrenamientos/precálculo completos los del
22/09 a las 01:08–01:23 UTC, anteriores a esta ampliación diagnóstica. El usuario
autorizó explícitamente la excepción a repetir ese circuito completo exigido por
AGENTS.md: «Sí, publicar con la validación actual». No presentar el circuito
anterior como validación de este contrato nuevo. No se lanzaron entrenamientos
ni precálculos; el usuario indicó que los lanza él en HA local.

### Detalle completo de variables fuera de rango — desplegado en HA local y worker

El usuario detectó 33 variables fuera de rango y solo tres filas visibles. La
causa está en `mushroom_map_prediction.resolve_species_week`: el contrato normal
solo lleva tres ejemplos (la inferencia conserva cinco extremos). No era un
recorte CSS. Se añadió una consulta opcional `applicability_page` para una sola
especie/día, 32 filas compactas por página, reutilizando la cola/autenticación
del mapa. El desplegable carga al abrir, tiene scroll y contador y permite
cargar las siguientes páginas. Verifica fecha, zona horaria y procedencia antes
de incorporar el detalle; errores y cambios de datos quedan visibles.

La consulta normal, límites de respuesta e IFF no cambian. El detalle vuelve a
resolver la semana de esa especie y consulta el modelo seleccionado para el día;
no entrena ni precalcula ni persiste diagnósticos. Página máxima sintética de 32
nombres de 128 caracteres y valores extremos: <8 KiB. Pruebas dirigidas: 97 OK;
prueba final de navegador OK (47 consultas), con 33 filas/scroll/paginación,
rechazo de datos cambiados y fallo de carga. `git diff --check` correcto.

Tras confirmar el usuario que había terminado, `/health` mostró ambas lanes idle,
comprobado también justo antes de recrear. Reconstruidas ambas imágenes y recreados
HA local y worker, conservando identidad, volúmenes y hashes de configuración y
credenciales. Destinos idénticos: `http://100.111.77.48:8100` y
`http://rainmapper-ha-ui:8100`. Worker healthy e idle tras arrancar, cachés válidas.

Paridad efectiva: 217 archivos HA y 117 worker sin diferencias con el checkout
(`tmp/ha-memory-20260922/parity.json`). Imagen HA
`sha256:6c52d5e2bf5c9bba161239dcfb506937ecc56d6c8cfb36b08683b0641b845992`;
worker `sha256:571041c90d6d587b124024cf69cec004b74f172d8db9d97300f9a14f5d44bc18`.
Las 97 pruebas dirigidas pasan también dentro de la nueva imagen HA (ruta de
tests adaptada al empaquetado mediante symlink en contenedor efímero).
JavaScript servido por HA local: HTTP 200 y SHA256 idéntico al checkout.
Consulta anónima al API: HTTP 401; no se ejecutó una consulta real autenticada.
Prueba interactiva confirmada después por el usuario; publicada en 0.2.319 según
el apartado superior. Esta mejora no estaba en 0.2.318. No se han lanzado
entrenamientos ni precálculos: los lanza el usuario.

### Release 0.2.318 publicada; pendiente instalar en HA real

Usuario aceptó el resultado visual y autorizó publicar. GHCR 0.2.318/latest
verificados con mismo digest y amd64/arm64; script terminado código 0. Smoke
final 1.724 pruebas/52 skips correcto. Worker local reconstruido y activo 1.1.5,
destinos/credenciales intactos; HA local final y worker con paridad 217/117.
Código científico igual al circuito completo ejecutado por el usuario; última
validación visual 41 consultas. No se repitió entrenamiento/precálculo.

Ver [evidencia de release](reports/release-ha-0.2.318-2026-09-22.md).
Instala HA el usuario. No activar política ni lanzar trabajos automáticamente.
Pendiente medir la mejora de memoria en Raspberry; consumo inicial/cachés aún
sin resolver. Observaciones privadas excluidas del commit. Las notas inferiores
son historial y sus pendientes de publicación quedan superados por esta sección.


### Ampliación 22/09: conclusión de consenso compacta, desplegada en HA local

Petición del usuario antes de publicar: conclusión bajo temporada, verde si
acuerdo, roja si desacuerdo y «Detalle/Detall» al final. Implementado como un único
desplegable sin recuadro ni separadores; al abrir muestra modelos/IFF/perfiles
sin desplegables anidados. Modo shadow y explicación del umbral dentro del detalle.
Falta de alternativas usa ámbar. Solo presentación del mapa y traducciones;
no cambios del cálculo, del entrenamiento ni de los artefactos.

Prueba navegador: 41 consultas correctas, colores y posición bajo temporada,
apertura con un clic, perfiles visibles, sin solapamiento a 1280/320 px.
Captura: `prediction-map-browser-1m0erG/consensus-models.png` en temporal.
HA local reconstruido/recreado, imagen
`sha256:66a37fac3cab0dd4814ee8850e75d39ac00e9ddb570b62b1177cf464b5901e3a`.
Paridad efectiva 217 archivos HA / 117 worker sin diferencias; worker no
reiniciado. Su contenido empaquetado no cambia con estos archivos del visor.
Pendiente prueba/aceptación visual del usuario y flujo de release proporcional
sobre el estado final. No publicado ni instalado en HA real.


### Ampliación 22/09: circuito local completado por el usuario

Reconstrucción/base/multiversión completas (792/792 ajustes). Precálculo revisión
73 `worker_job_TSqdxNLr7YfS` completo y activo en HA local y worker; ambos archivos
48.459.776 bytes y mismo SHA comprobado contra recibo. El intento previo falló
409 al arrancar con una huella anterior a la promoción, tras 136 s en cola; no
llegó a calcular. No se lanzaron trabajos ni reiniciaron contenedores.

Usuario percibe lentitud: nuevo cálculo 481,81 s frente a 493,29 s del último
worker para HA real con iguales recuentos; multiversión 698 frente a 763 s,
792 ajustes ambos. Local antiguo sí era más corto (383,58 s) pero tenía 574
miembros frente a 756 y menos combinaciones. No es A/B de mismos datos/modelos.
Publicación HA local 15,95 s, activación worker 17,57 s. Informe de memoria
ampliado con evidencias y límites. Pendiente aceptación para release; no publicar
aún. Consumo inicial y otros procesos/cachés siguen siendo revisión separada.

### Ampliación 22/09: memoria corregida; circuito local a cargo del usuario

Validador secuencial y recepción HTTP por bloques implementados. Misma copia de
precálculo real: pico Mac 825→304 MiB, tiempo 16,00→15,66 s; incremento RSS residual
109→63 MiB en comprobación separada. Dentro de HA local Linux: 14,80 s y pico
259 MiB (proceso diagnóstico aislado, no consumo del servidor). Conserva SHA,
contratos y comprobaciones; no cambia límites ni añade GC forzado. Consumo inicial
y cachés de consultas siguen pendientes de investigación separada.

Smoke completo: 1.724 tests, 52 skips. HA local y worker reconstruidos y recreados;
paridad 217/117 archivos sin diferencias. Se corrigió además COPY del módulo de
consenso ausente en la imagen del worker y se añadió importación de servicio al
build. Worker vuelve a estar idle, con `recommendation_consensus_v1`. Destinos y
credenciales conservan sus huellas. Etiqueta local worker sigue 1.1.4, código nuevo.
Evidencia e imágenes en [informe](reports/ha-memory-precompute-2026-09-22.md).

El usuario respondió **«Los lanzo yo en HA local»** a reconstrucción, entrenamiento
y precálculo. No lanzar esos trabajos. Próximo paso: auditar su circuito y memoria
persistida, obtener aceptación y publicar versión HA; no se ha publicado todavía.
Las notas anteriores de worker sin reconstruir o memoria pendiente son históricas.

### Ampliación 22/09: presentación de alternativas en el mapa

El usuario priorizó ordenar el detalle de modelos antes de implementar la mejora
de memoria. Cada alternativa ocupa una fila con nombre e IFF alineados; el perfil
técnico queda plegado y «Solo comparación» separado dentro del bloque de consenso.
Desplegado solo HA local. Navegador: 41 consultas correctas y comprobación de filas
sin solapamiento a 1280/320 px; sintaxis JS y diff correctos. Paridad de 217 archivos
efectivos sin diferencias y HTTP 200. Worker conserva imagen y arranque de
21/09 17:46:47 UTC; HA real sin actualizar. Evidencia de navegador:
`prediction-map-browser-eTVMPI/consensus-models.png` en el directorio temporal.
La mejora de memoria sigue pendiente.

### Ampliación 22/09: investigación de memoria en HA real

Usuario informa 18,1% de RAM tras trabajos frente a 11,6% tras reinicio, en RPi4
de 4 GB. Inspección SMB y copia verificada de precálculo activo 213: la muestra
de 924 MiB RSS / 1.133 MiB cgroup coincide con su validación/activación (129 s).
Antes del reinicio: 486 MiB RSS; al arrancar: 244 MiB. La validación acumula 208
respuestas descomprimidas. Reproducido solo validar la copia en el Mac: pico
786 MiB, final 289 MiB, 250 tras GC frente a base 188. No demuestra fuga ni explica
toda la retención real. Promoción sí limpia cachés del Predictor. Propuesta de
validación secuencial y recepción por bloques **pendiente de implementar**;
no se han cambiado ejecutables, reiniciado workers ni ejecutado trabajos nuevos.
Ver [informe](reports/ha-memory-precompute-2026-09-22.md).

### Ampliación 22/09: desplegado únicamente HA local para probar

Por petición del usuario se reconstruyó y recreó solo `rainmapper-ha-ui`.
Verificados 217 archivos efectivos, sin discrepancias con el worktree.
Formulario local de Workers y trabajos guardó `recommendation_policy.mode=shadow`
(Solo comparar), conservando las siete suspensiones. Registro, observaciones
privadas y setales locales sin cambios por SHA. Evidencia en
`tmp/consensus-local-20260922/`.

El worker sigue en su imagen anterior: su carril de fondo continúa ocupado por
`worker_job_16An-MA-FiXiJuiC`; no se reconstruyó, recreó ni reinició. El usuario
reiteró expresamente que está entrenando para HA real. Para probar ahora el mapa,
usar **Servidor local** en HA local (`http://127.0.0.1:8101`). Solo comparar
conserva el IFF y muestra la decisión del consenso; no suaviza las diferencias
entre puntos. Quedan pendientes actualización del worker y validación conjunta;
este despliegue no acredita aceptación de release real. No se lanzaron trabajos
de entrenamiento ni precálculos. HA real no se actualizó.

Segunda actualización local: aviso «Comprobación superada» y desplegable con las
dos alternativas e IFF, en mapa y Predictor. Regla >=60 y modo shadow conservados.
44 pruebas dirigidas y navegador (41 consultas) correctos; 217 archivos efectivos
coincidentes tras recrear solo HA local. Worker conserva imagen y fecha de inicio.
Al revisar frente a las huellas del primer despliegue, las observaciones y setales
del volumen local han cambiado; no se restauraron ni se atribuye aquí ese cambio.

### Ampliación 22/09: reservas y consenso implementados en el worktree

El usuario pide contar los descartes por falta de datos y continuar la propuesta
selectiva. Implementado selector persistido en Workers y trabajos → Modelos de
predicción: Desactivado / Solo comparar / Aplicar. Sin ajuste explícito sigue
Desactivado; no se ha activado ni desplegado en HA real. Ou/Edulis/Pinícola tienen
consenso de ganador + dos siguientes familias semanales; deliciosus/aereus solo
avisos. IFF intacto, abstención visible por desacuerdo o comparación no disponible.
Las reservas cuentan solo evaluados; en snapshot Querigut, 21/33 descartes por datos,
9 por delante del elegido. No confundir familias no ejecutadas por el mapa con rechazadas.

Código y pruebas dirigidas preparados. Ver
[informe de implementación](reports/recommendation-consensus-implementation-2026-09-22.md)
para verificaciones, costes acotados, diferencias con la retrospectiva y pendiente de
paridad/latencia completa en HA local y worker antes de publicar. No se han tocado
contenedores, coordinadores, observaciones privadas ni ejecutado trabajos reales.
Los apartados anteriores que indicaban «pendiente de implementar» describen el cierre
previo; este bloque actualiza ese estado, sin dar por validada una release.

### Ampliación 22/09: comparación concreta de Querigut terminada

Revalidado por SMB precálculo activo **212**, copia y SHA/tamaño contra recibo.
Los siete modelos/entradas/IFF y resúmenes meteorológicos de Querigut coinciden
exactamente con la revisión 211. Comparadas 33 familias del lote real, siete
plazos, preparando únicamente meteorología/ETo de sus dos microáreas; sin
recalcular estado hídrico, entrenar, precalcular o construir runtime operativo.
Ver ampliación de [informe Querigut](reports/querigut-predictor-2026-09-21.md).

Resuelta causa concreta en las nueve familias anteriores al servido: lluvia
71/90 días frente a mínimo 81; V3 físico además sin estado hídrico. Hueco 29/06–17/07
deja solo 65 días consecutivos, insuficientes para mínimo hídrico de 90.
V5/V6 aceptan entradas ausentes con imputación y no aplican el mismo mínimo.
Las dos microáreas sí tienen SoilGrids de retención completo: no atribuir la
ausencia hídrica a Francia. Tipo de suelo/hosts GIS vacíos son otra fuente;
ninguna columna de las 33 familias es host, tipo de suelo o pH.

Alternativas admitidas por sus adaptadores: V5 90d IFF 89→47; V6 parcial
30/60/90d aproximadamente 55–61 al inicio, frente a servido 99→90. No hay
consenso sobre 99; esas V6 no superan al servido en Brier/precisión histórica.
Las salidas forzadas de los mejores clasificados son diagnósticas inválidas
para operación, no votos utilizables. No cambiar modelo por intuición ni
activar consenso para deliciosus sin decisión explícita. Trabajo autorizado
de filtro reversible y explicaciones sigue pendiente; no hay cambio ejecutable.

### Autorización de implementación y revisión previa de Querigut

El usuario acepta implementar el filtro de acuerdo reversible, tolerando de
momento el coste, e incluir explicaciones comprensibles de cada recomendación.
Antes pide revisar IFF 99/98 de deliciosus en **Predictor de HA real**; confirma
que HA local no se ha reentrenado ni precalculado. GBIF sigue pendiente de revisión
del usuario: no incorporarlo como evidencia nueva validada.

[Inspección de Querigut](reports/querigut-predictor-2026-09-21.md) terminada con
precálculo activo real **revisión 211**, copiado por SMB y verificado por SHA/tamaño,
no con el de HA local. Mismo lote `operational_20260921T134830Z`. Reproducidos los
siete valores con pesos y features guardadas: 98,7779→90,1498. Elastic Net V5w60d
es el décimo por calidad; se elige por cubrir 7/7 días. Evidencia h1 global de
especie 6/8 llamadas correctas, sin evidencia por área. Siete features de estado
hídrico ausentes, rellenadas con medianas; contribución directa pequeña, no causa
única del 99. V5/V6 marca inferencia elegible y el rango omite valores ausentes.
La ampliación del 22/09 anterior identifica los huecos meteorológicos y las
exclusiones individuales; la inspección inicial de 211 no las había resuelto.

La explicación deberá incluir motivo de selección por cobertura, evidencia real
decisiva, datos rellenados y limitaciones. El 99 no equivale a garantía 99%.
Importante para implementación: simulaciones anteriores fijaban familias
preferidas por evidencia antes de cobertura/aplicabilidad. No prometer balance
39/10 para el selector completo por área sin comprobarlo. Deliciosus sigue fuera
del ámbito inicial de consenso, por lo que ese filtro no arreglará por sí solo
Querigut. Implementación **aún pendiente**, autorizada; no confundir informes
con código desplegado. Mantener restricciones de entrenamientos/precálculos.

### HA 0.2.317 publicada — instalar en HA real y retomar comparación

El usuario autorizó desplegar la corrección y pidió retomar después la auditoría
científica de cinco especies. GHCR `0.2.317` y `latest` verificados con el mismo
digest `sha256:3454cacfe4c3776e2d254c96f8e85bff4035f3e96ec750161da8a0a6dae72e79`,
AMD64 y ARM64. [Informe de release](reports/ha-release-0.2.317.json).
**HA real queda pendiente de instalación por el usuario.** Worker local 1.1.4
reconstruido y recreado estando ambas colas en reposo; coordinadores y sus huellas
exactamente conservados. No se ha accedido por SSH ni repetido entrenamiento o
precálculo. Observaciones privadas y setales preservados por SHA y excluidos del
commit y de la imagen.

La incidencia del mapa era `quality_read_limit`: el lector recorría más de
64 MiB del catálogo nuevo, incluida una cola por áreas que descartaba. La
corrección verifica el SHA del archivo completo y termina al reunir la evidencia
por punto, sin elevar límites. Afectaba al modo «Servidor local» de HA real y al
worker; no al Predictor que estaba sirviendo su precálculo. El lector proyectado
no sustituye la validación completa del productor/promoción. Se conservan las
70 resoluciones por especie y las 3.600 métricas originales.

El mapa ahora muestra un modal ante un fallo técnico, con causa traducida
ES/CA/EN, ejecutor, código acotado y referencia de consulta; el traceback queda en
el log. También reconoce respuestas antiguas `model_status=unavailable` sin
código. No expone excepciones arbitrarias/rutas privadas, ni confunde errores con
la ausencia legítima de modelo o abstenciones. Sigue existiendo un límite si
crece la evidencia necesaria; un catálogo compacto específico del mapa sería
una mejora futura, no implementada ni necesaria para esta corrección.

Aceptación local: HA y worker construidos desde el código candidato, 216/116
archivos efectivos coincidentes antes del bump mecánico de HA; smoke 1.707 tests,
52 omitidos, correcto. Navegador correcto, 39 consultas con ambos ejecutores,
fallos conocidos, respuesta antigua y códigos no admitidos. Consultas completas
con geografía real y el lote nuevo en ambos contenedores devuelven exactamente
los mismos IFF: C Ou 64,2481/Aereus 32,9455; D Ou 56,0425/Aereus 30,7147.
No se ha repetido la cadena de entrenamiento/precálculo: restricción explícita
del usuario y cambio acotado al lector/presentación. Evidencia privada en
`tmp/release-0.2.317/` y `tmp/model-robustness-20260921/map-quality-failure.md`.

Datos del lote real nuevo `operational_20260921T134830Z`: 518 observaciones,
47 áreas, 84 microáreas; entradas locales/real/snapshot coincidentes por SHA en
la comprobación anterior. 792 ajustes correctos, cero fallidos; cinco generaciones
promovidas y siete suspensiones conservadas. El precálculo del usuario
`worker_job_B6SNHSRjJFEP` terminó el 21/09 a las 14:34:03 UTC. En esta sesión se
verificó por SMB que el activo (revisión 210, 45.449.216 bytes) coincide por tamaño
y SHA con su recibo. No implica aún auditoría semántica de todas sus respuestas.
Última consulta de montajes: `/Volumes/media` presente; `/Volumes/share` ausente.

**Auditoría ampliada terminada tras la release:** Ou de reig, Aereus,
Lactarius deliciosus, Edulis y Pinícola (B. pinophilus), usando el lote NUEVO.
[Informe y decisiones propuestas](reports/model-selection-robustness-2026-09-21.md).
Se reprodujo el ranking semanal y se midió estabilidad al omitir grupos sin
reentrenar. El barrido amplía el cribado inicial de cuatro contextos a 135
contextos especie/observación, 22 combinaciones especie/familia (20 artefactos),
17 escenarios y dos horizontes: 597 filas completas, 20.298 inferencias.
RH, lluvia, temperatura y SMI perturbados por separado; 49 objetos meteorológicos
verificados contra el snapshot antes de ejecutar. Protocolo escrito previamente.

Con RH ±1 pp, máximos de IFF admitidos: Ou 2,96; Aereus 0,78; deliciosus 4,18;
Edulis 3,74; Pinícola 0,58. Algunas alternativas con menor Brier son mucho más
sensibles. En hold-out h1, los ganadores de Edulis/Pinícola acertaron 6/14 y 5/14
llamadas favorables. Esto prioriza fiabilidad/calibración además de sensibilidad;
no autoriza reemplazar todas las versiones por V6 ni demuestra sobreajuste.
Los ensayos son diagnósticos, no incertidumbres medidas ni umbrales de admisión.
Los ajustes operativos pueden haber visto esos contextos; precisión histórica
exclusivamente con hold-out sellado. No multiplicar el tamaño muestral por los
horizontes o perturbaciones. No se cambió IDW, selector, suspensiones ni modelos.

**Preferencia nueva del usuario:** priorizar abstenerse frente a recomendar mal,
sin que la aplicación se abstenga siempre. Exige un parámetro para desconectar
el filtro y comparar con observaciones futuras. **El usuario rechazó la propuesta
global inicial por perder 156 aciertos para evitar 130 errores.** Exige evitar
más errores que aciertos perdidos. No implementar la regla Wilson/3 grupos como
si siguiera aceptada.

Propuesta vigente, todavía sin implementación/activación:
[acuerdo selectivo](reports/recommendation-consensus-proposal-2026-09-21.md).
Conservar ganador semanal e IFF; para Ou/Edulis/Pinícola recomendar solo cuando
ganador y siguientes dos alternativas del ranking semanal sellado coincidan
en p ≥0,60. Mantener Aereus/deliciosus sin filtro adicional porque en ellos no
mejora el balance. Simulación: 39 errores evitados y 10 aciertos perdidos;
359/408 recomendaciones conservadas (248 aciertos/111 errores). En h1 evita
7 errores y pierde 1 acierto. Se reutilizan 135 observaciones a siete horizontes;
no presentar los totales como salidas independientes.

Ámbito selectivo elegido después de inspeccionar datos: no es validación
independiente. Reglas uniformes y resultados por especie/plazo documentados,
con omisión de grupos sin reselección. No forzar abstención de especies enteras.
Modos propuestos `legacy` / `shadow` / `prudent` con regla `consensus_v1`, aún
no existentes en configuración. Corrección importante: el consenso necesita
dos inferencias adicionales cuando no estén disponibles; medir coste RPi4 y
elegibilidad antes de activar, reutilizando entradas y sin duplicar payloads.
Siguiente trabajo: implementación local reversible, primero comparación shadow,
paridad de contratos/mapa/Predictor/worker y cachés por política. Falta comprobar
ámbitos por área/resto de especies. No tocar runtime real, IDW o suspensiones,
ni lanzar entrenamientos/precálculos. Evidencia privada añadida:
`consensus_tradeoff.py` y `consensus-tradeoff.json`.
Evidencia privada en `tmp/model-robustness-20260921/`: `new-ranking-audit.json`,
`expanded-stress-protocol.json`, `expanded-stress-results.jsonl`,
`expanded-stress-summary.json`, scripts correspondientes y `olvan-new-results.json`.
El `report.md` privado inicial de cuatro contextos es histórico; prevalece el
informe ampliado enlazado arriba. HA real sigue pendiente de instalación de
0.2.317 por el usuario; no confundir aceptación local con comprobación en real.

### HA 0.2.316 publicada

Publicación autorizada tras la aceptación local. GHCR `0.2.316` y `latest`
verificados con el mismo digest
`sha256:df35341875f9c227276c2a1f3c2094f54ce54ca4cf846050b03cd6c4f590302c`,
AMD64 y ARM64. [Informe de release](reports/ha-release-0.2.316.json).
**Siguiente paso: el usuario instala en HA real cuando termine su entrenamiento
en curso.** No se ha instalado ni reiniciado HA real desde esta publicación;
no tocar el worker activo ni lanzar precálculos. Después, verificar resultados
persistidos y la interfaz real, sin atribuirle automáticamente la evidencia local.

El usuario ha autorizado publicar 0.2.316. La candidata incorpora recuperación
GIS/DEM en observaciones, inspector de puntos y agregación MFE25 en microáreas;
[informe de interfaz](reports/gis-recovery-review-2026-09-20.md).
**Incidencia inicial resuelta:** la primera aceptación local completó reconstrucción
y entrenamiento base, pero el multiversión terminó con cinco ajustes fallidos,
ocultos por `Tuning catalog does not cover the plan: 5 missing, 0 unexpected`.
No hubo promoción de esa cadena. Las siete suspensiones se conservaron.

Se corrigió el diagnóstico para comunicar las causas y ámbitos afectados antes
de validar el catálogo incompleto; no se modificaron criterios de entrenamiento
ni admisión. 24 pruebas dirigidas correctas; smoke posterior: 1704 pruebas,
52 omitidas, correcto. HA local y worker reconstruidos/recreados: 216/116 archivos
efectivos coincidentes y huellas de sus coordinadores sin cambios.

El usuario autorizó **una repetición local del multiversión para identificar los
cinco fallos**, ya terminada: todos corresponden a `rbf_svm_calibrated_v1` de
`lactarius_sanguifluus` en los contratos de ventana fija de V2, ambos perfiles
V3 y ambos perfiles V4. Motivo confirmado: `calibration requires at least two
training examples of each class`. Las entradas V3 fijas contenían diez casos
favorables elegibles y uno desfavorable. La repetición usó el mismo snapshot,
58 archivos y el mismo catálogo de ajustes; terminó fallida y limpia, sin
promoción. Evidencia privada ignorada por Git: `tmp/release-0.2.316/`, incluidos
`diagnostic-results.json`, `diagnostic-progress.json` y
`diagnostic-input-parity.json`.

**Reanudado tras confirmar el usuario que las nuevas observaciones están en HA
local.** Comprobado el archivo actual: 505 observaciones, 19 de sanguifluus;
10 episodios favorables y 5 desfavorables válidos/incluidos. La reconstrucción
nueva conserva esos recuentos en las features y está verificada (nueve
artefactos); el entrenamiento base de diez especies está completo/verificado.
El multiversión ha terminado: **792 ajustes correctos, ninguno fallido**;
lote `operational_20260920T204548Z`. Reconstrucción y base promovidos; las cinco
versiones V2–V6 instaladas desde ese lote, con puerta de promoción superada y
revisiones de entrada coincidentes. Recalculadas las huellas de los 792 modelos
y del catálogo de ajustes: ninguna discrepancia. Observaciones privadas,
observaciones/sites locales y las siete suspensiones conservan sus huellas
anteriores. Evidencia actual en `tmp/release-0.2.316/new-data/`, incluidos
`chain-jobs.json` y `promotion-audit.json`; no confundirla con la cadena fallida
anterior. HA local y worker se han reconstruido y recreado después del ajuste de
microáreas; paridad 216/116 archivos, coordinadores sin cambios, smoke final
1704 pruebas/52 omisiones correcto (`smoke-final-ui.log`).

No se ha cambiado el contrato de disponibilidad por modelo. No lanzar
precálculos: siguen a cargo del usuario, después de verificar la promoción.
El precálculo lanzado por el usuario ha terminado: `worker_job_tvVmB0Np_qaP`,
recibido y activo, revisión 71/esquema 1.7, generación nueva y diez especies.
SHA/tamaño, integridad SQLite, identidad deseada y recuentos comprobados:
903 respuestas, 756 coberturas, 574 miembros operativos, 37.773.312 bytes.
Ningún miembro operativo coincide con las siete reglas de suspensión.
Evidencia: `tmp/release-0.2.316/new-data/precompute-audit.json`.
El usuario aceptó el último ajuste visual y autorizó publicar.
Las observaciones privadas se conservan fuera del commit; la documentación
anterior pendiente se incluye en el cierre de la release.

El ajuste posterior de microáreas (Reemplazar si difiere, Mantener si coincide y
selector completo con disposición móvil) ya está en HA local y comprobado con
fixture en navegador a 1600/375 px. Véase el informe GIS enlazado arriba. El smoke final y la reconstrucción de ambos contenedores indicados arriba ya
incluyen este ajuste.

**Último ajuste visual incluido en la release:** «Reconstruir y reentrenar operativo» y
«Ejecutar benchmark científico» son desplegables cerrados por defecto en
Workers y trabajos. Actualizada únicamente la imagen/contenedor HA local;
el usuario prohíbe reconstruir/reiniciar el worker porque entrena para HA real.
Se conserva su contenedor y arranque, comprobados antes/después. El cambio
afecta solo a HTML/CSS de `mushroom_workers_ui.py`, que no se incluye en el
worker; paridad efectiva actual 216/116 archivos sin diferencias.
Validación proporcional: 16 pruebas existentes de la pantalla y navegador real
en HA local a 1600/375 px, apertura con teclado, selecciones conservadas y sin
POST. Evidencia: `tmp/workers-folds-20260920/`. No se han repetido entrenamientos
ni precálculos por este ajuste. Smoke completo final con estos desplegables:
1704 pruebas, 52 omitidas, correcto en 80,720 s (`smoke-release-final.log`).

### Cierre histórico de HA 0.2.315

**HA 0.2.315 publicada; instalación en HA real confirmada por el usuario con
«Hecho» antes de pedir este cierre.** No se inspeccionó HA real para comprobar
su versión efectiva ni se confirmaron sus nuevos entrenamientos/precálculo.
La siguiente tarea útil es verificar esa cadena cuando el usuario la haya
lanzado, mediante registros y artefactos persistidos; no iniciarla por el cierre.

- Release `6bbd0e8`, enviada a `origin/inicial`; GHCR `0.2.315` y `latest`, mismo
  digest `sha256:8d064cef61c9e24fe283796b71aa37ad4d3eea2924141f4be554de1cc1a1f885`,
  AMD64 y ARM64 verificados. [Informe](reports/ha-release-0.2.315.json).
- HA local: `rainmapper-local-rainmapper-ha-ui-1`, imagen `rainmapperha:local-ha-ui`,
  puerto 8101. Worker existente: `rainmapper-worker`, etiqueta 1.1.3 independiente
  de HA, puerto 8110. Ambos arrancados al cierre; worker healthy y sus dos
  carriles idle según `/health`. Revalidar al comenzar otra operación.
- El worker conserva el coordinador principal `http://100.111.77.48:8100` y
  la asociación local `http://rainmapper-ha-ui:8100`. Huellas de ambos archivos
  de configuración comprobadas sin cambios; no redirigirlo ni crear otro worker.
- HA local/worker reconstruidos desde el código publicado; 211/114 archivos
  efectivos coincidentes. Smoke: 1690 pruebas, 48 omitidas, OK. UI ES/CA/EN
  probada a 1280/375/320 px. Evidencia detallada en
  [validación SMI-07](mushrooms/SMI/adoption-2026-09-20/validation.md).
- Cadena local: reconstrucción y base promovidos; multiversión del lote
  `operational_20260920T020702Z`, 714 ajustes correctos, ninguno fallido.
- Precálculo lanzado por el usuario `worker_job_7YWJHNU9LAaR`: completo,
  recibido y activado. Al cierre siguen activos revisión 69/esquema 1.7,
  cobertura 20–26/09, 749 respuestas, archivo de 28.004.352 bytes.
  `active-receipt.json` y metadatos de `active.sqlite3` reconsultados; SHA e
  integridad se comprobaron al publicar. No trasladar este resultado local a HA real.

## Qué incorpora la versión y decisiones que conservar

**SMI común:** extracción regulada + Penman–Monteith + una capa 0–30 cm,
contrato `regulated_pm_single_layer_v1`, para entrenamiento, precálculo y mapa.
El simple original sigue sólo como comparación visual; no es una segunda
variable operativa. La decisión fue aceptada por el usuario tras contrastes
con 22 estaciones, incluyendo ocho combinaciones; no reabrir la investigación
para evitar tomar una decisión práctica. [Justificación y consumidores](mushrooms/SMI/adoption-2026-09-20/README.md).

- La entrada operativa es IDW; Copernicus/ICGC son referencias de auditoría,
  no dependencias del cálculo. Referencia orientativa, sin validación absoluta
  de litros restantes ni de evapotranspiración real del bosque.
- PM usa temperatura/humedad, altitud y viento admisible; radiación estimada,
  viento de 2 m/s estimado cuando falta y Hargreaves como alternativa explícita
  si PM no se puede calcular. No se ha implementado sombra/orientación/dosel.
- Reserva calentada con hasta 365 días, ≥90 días completos y convergencia entre
  arranque seco/lleno; cambiar la ventana del gráfico no reinicia el suelo.
  Los huecos no son ceros. Capacidad SoilGrids 250 m, diferencia entre capacidad
  de campo y marchitez integrada en 0–30 cm. SMI = disponible/capacidad.
- Balance climático sigue siendo lluvia−ET₀; no equivale a cambio de reserva
  (lluvia−extracción regulada−drenaje).
- V2/V3 core/V4 extended no usan SMI; V3+ físico usa SMI y balance; V4 climatic
  usa balance sin SMI; V5/V6 físicos completos usan ambos; V5w/V6w usan escalares
  SMI sin los canales físicos diarios completos. El perfil y las columnas
  reales determinan las entradas, no el nombre del estimador.
- **Migración:** reconstruir entradas y reentrenar modelos físicos antiguos;
  sólo precalcular no basta. Se preservan hiperparámetros verificados del
  catálogo previo, nunca pesos ni métricas. Solicitudes precálculo 1.6 pueden
  avanzar a 1.7 conservando revisión; artefactos 1.6 no se aceptan como actuales.

**Mapa:** nombre del modelo elegido antes del IFF, por fecha; tooltip propio
ES/CA/EN con algoritmo, SMI, balance directo, otras entradas y ventana. Metadatos
obtenidos del artefacto ya cargado y deduplicados por especie. Mantiene distintos
«Sin IFF calculado», «Sin modelo disponible» y abstención. Cabecera con capacidad
y disponible; SMI antes del balance y Terreno al final de los desplegables.

**Suspensiones:** panel cerrado por defecto, JSON independiente
`mushroom_ml_prediction_policy.json` y exportación/importación en Workers.
La migración conserva reglas y generaciones; la imagen no contiene reglas
privadas. Siete reglas de rovelló se aplicaron a HA real en 0.2.314 según la
verificación anterior; confirmar que siguen efectivas tras instalar/entrenar.
No reactivar por rutina. [Contrato](mushrooms/model-suspensions-es.md).

## Pendientes prioritarios y dudas

1. **HA real:** verificar versión, reconstrucción/base/multiversión, recepción y
   promoción; después precálculo y activación, contratos nuevos y siete reglas.
   No sabemos si el usuario ya inició esa cadena. Revisar primero, no repetir
   cálculos caros ni copiar resultados locales.
2. **Falsos positivos:** tres visitas sin setas frente a IFF 86/84/100 del 18/09.
   Puntos: Vallcebre 42.20292/1.84242, Vallcebre 42.18669/1.82177,
   Bellver/Riu 42.31110/1.79167. Fecha de visita y esfuerzo no confirmados;
   las capturas no identificaban el modelo. No se demuestra que el nuevo SMI
   los haya corregido. No convertir visitas incompletas en negativos de entrenamiento.
3. **Indicador del worker:** usuario observó «ocupado» después de cancelar y
   luego confirmó ambos coordinadores en espera. Hay carriles foreground/background
   y asociaciones por coordinador. Semántica del indicador pendiente: el usuario
   cree que debe contar background por coordinador. No imponer «cualquier carril
   ocupado» ni cambiar planificación como arreglo visual. Revisar sólo si se retoma.
4. GIS aplazado, revisión manual GBIF, candidatas WU y nueva limpieza de disco
   no se reabren automáticamente; prioridades y fuentes en `todo.md`.

## Archivos y accesos para continuar

- Física: `rainmapper_core/mushroom_water_physics.py`, `mushroom_soil_water_state.py`.
- Adaptadores: `mushroom_map_hydrology.py`, `mushroom_ml_weather_workspace.py`,
  `mushroom_ml_area_weather_runtime.py`; `mushroom_map_water_physics.py` sólo reexporta.
- Modelos/tooltip: `mushroom_model_labels.py`, `mushroom_map_model_runtime.py`,
  `viewers/prediction-map/prediction-mode.{js,css}`, `prediction-weather.js`, labels.
- Migraciones: `mushroom_ml_tuning_catalog.py`, `mushroom_ml_policy_store.py`,
  `mushroom_predictor_precompute_control.py` (todos bajo `rainmapper_core/`).
- Local: `http://127.0.0.1:8101/protected/maplibre/index.html` (modo predicción)
  o `/protected/prediction-map/index.html`; Workers `/mushrooms/workers`.
- Estado local: `docker-data/mushroom-data/`; GIS canónico
  `docker-media/rainmapper/geography/`; resultados/precálculo
  `docker-media/rainmapper/results/`. HA real usa sus propios `/share` y `/media`.
- Visores independientes: `local-apps/{wunderground,gbif}/{code,data}`;
  los datos/fotos/revisiones quedan excluidos de Git e imágenes. No duplicarlos
  en `docs/mushrooms/GBIF` ni reimportar observaciones automáticamente.

## Permisos y preservación

El usuario lanza el precálculo; instalar/parar/arrancar HA real le corresponde.
Preferir archivos compartidos/API autorizada; no usar SSH sin petición expresa
ni alterar destinos del worker. No crear imágenes/volúmenes/workers auxiliares.
Respetar recursos RPi4 y el circuito local obligatorio antes de otra release.

Antes del cierre documental, único cambio sin commit:
`mushroom-data/mushroom_observations.json`, privado/preexistente; no editar ni
incluir. Este cierre cambia sólo documentación, sin nueva versión/build,
entrenamiento ni precálculo. No asumir commit/push de este cierre: comprobar Git.
Conservar auditorías SMI, datos de los visores y `tmp/soil-review-after-0.2.307/`.
