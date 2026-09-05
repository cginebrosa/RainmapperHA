# Active Context

Ventana operativa de RainmapperHA al cierre del 4 de septiembre de 2026. No es
un histórico. Revalidar siempre rama, HEAD, worktree y runtimes antes de afirmar
que este estado continúa vigente.

## Estado comprobado en este cierre

- Repositorio: rama `inicial`, HEAD
  `e5476dac9f40b81d612210b258696e176aa3785d`, con un worktree muy modificado.
  Hay cambios de código, pruebas, documentación y datos del usuario; en
  particular, preservar `mushroom-data/mushroom_observations.json`. No limpiar,
  descartar ni hacer commit global sin revisar el alcance.
- Versiones declaradas en fuentes: HA `0.2.292` y worker `1.0.38`. La imagen HA
  `0.2.292` ya fue construida y publicada en GHCR para `linux/amd64` y
  `linux/arm64`; el tag de versión y `latest` comparten el digest
  `sha256:9f1e111f292037f6d0d6a2dafe9d458d6d35dd9549182986ef5edd5a0230f6d1`.
  La publicación Git de esta release queda incluida en el cierre; aún no se ha
  instalado en HA real, que sigue declarando `0.2.291` en su
  `diagnostics/runtime_state.json` montado.
- El worker local fue reconstruido y recreado con `rainmapper-worker:1.0.38` sin
  publicar una imagen remota. Su health endpoint confirmó versión `1.0.38`,
  estado `idle`, caché GIS válida y caché Predictor válida; la imagen local
  resuelta es
  `sha256:29febd4b5f1ddf24781c55905354a13df5ca22369c03fb6486deadbf682ba8b1`.
- Laboratorio local: `rainmapper-local-rainmapper-ha-ui-1` estaba levantado con
  la imagen local actual y la portada y Predictor respondían HTTP 200 en el
  puerto 8101. El endpoint `/health` de esa UI responde 404; eso no demuestra un
  fallo del contenedor.
- Entrenamiento operativo activo: generación
  `local_operational_20260905T194632Z` para las cinco versiones instaladas
  `V2`, `V3`, `V4`, `V5w` y `V6w`. Usó 406 observaciones elegibles y terminó
  con 636/636 ajustes y cero fallos; el catálogo de selección usa contrato
  `1.2`.
- Precálculo local activo: revisión deseada `39`, estado `complete`, contrato
  de artefacto `1.6`, cobertura 2026-09-05–2026-09-11 y
  `PRAGMA quick_check = ok`. Ocupa 29.233.152 bytes, no tiene páginas libres y
  contiene 504 predicciones base, 420 miembros operativos, 143 payloads físicos
  y 623 respuestas lógicas. La ejecución final duró 8m34s. Existe además un
  SQLite de cero bytes en el directorio raíz de
  precálculo; no se ha determinado si es un placeholder transitorio. No borrarlo
  sin resolver su propietario.

## Predictor vigente en el worktree

- Todas las versiones operativas instaladas participan automáticamente. Ya no
  existen casillas de inclusión ni una versión «preferida» que influya en la
  predicción.
- El selector compara candidato de área y candidato global de especie mediante
  el mismo límite inferior de Wilson al 95 %. Gana el mayor; el empate conserva
  el candidato de área. El resultado conserva la identidad completa del modelo
  elegido y separa probabilidad, acierto observado, límite conservador,
  observaciones y floradas.
- Las tres vistas operativas (`Esta semana`, `Por especie` y `Consultar fecha`)
  comparten selector. El SQLite semanal conserva miembros reutilizables y el
  lector compone respuestas sin repetir inferencia.
- El ciclo cancelar→relanzar del precálculo fue corregido: un intento terminal o
  todavía parando no bloquea indefinidamente un lanzamiento manual posterior.
- La tarjeta resumen fue simplificada, incluye tooltips y coloca primero la
  evidencia que decide. Los veredictos categóricos usan badges de color.
- El código incorpora una cadena sellada de candidatos fiables: si el primero
  queda fuera de dominio para las features de un área/fecha, usa el siguiente
  aplicable en el orden fijado por el entrenamiento y muestra el fallback. El
  catálogo activo conserva la cadena completa para auditoría; el precálculo
  activo ya resuelve esa cadena y materializa únicamente el candidato final, su
  posición y los motivos de descarte anteriores.

## MOD_0001: ecología diagnóstica, no veto

- Las reglas externas de ventana tras lluvia, temperatura y compatibilidad
  ecológica están retiradas temporalmente de la decisión operativa. No cambian
  la probabilidad aprendida, el color ni el dictamen final.
- Los cálculos y su trazabilidad se conservan deliberadamente para poder
  auditarlos o reintroducirlos. El código y las pruebas están marcados con
  `MOD_0001` en `rainmapper_core/mushroom_prediction_interpretation.py`,
  `rainmapper-app/app/mushroom_predictor_ui.py`,
  `tests/test_mushroom_prediction_interpretation.py` y
  `tests/test_web_server_auth.py`.
- Cuando existe, el episodio de lluvia conserva fecha, cantidad IDW del área,
  días hasta la fecha objetivo y umbral. La propagación fue corregida de forma
  transversal para V2–V6 y adaptadores, no solo para un caso concreto.
- La ventana orientativa vuelve a mostrarse como diagnóstico: compara esos días
  con los intervalos tras lluvia configurados para la especie. No es aprendida
  ni afecta a la salida operativa.
- Motivo: actualmente solo se predicen combinaciones especie/área donde la
  especie está confirmada. Las ventanas y condiciones meteorológicas deberían
  aprenderse de observaciones si realmente aportan señal; no hay evidencia
  suficiente para justificar un veto causal externo.

## Investigación abierta: señal hídrica y probabilidades extremas

- No está comprobado qué variables de lluvia, temperatura, humedad, altitud o
  retardos usa efectivamente cada familia ganadora ni cuánto contribuye cada
  grupo a la predicción. Hay que auditar el pipeline real, no inferirlo por el
  nombre de los modelos.
- Caso de control prioritario: Rovelló/Riu de Cerdanya dio 100 % en Rainmapper
  con fallback global de especie y sin evidencia de área, mientras Sporas.io
  mostraba 9,5 %. La divergencia no demuestra por sí sola cuál es correcto, pero
  obliga a revisar saturación, calibración, extrapolación y fallback territorial.
- En Ous de Reig/Olvan las cifras visibles fueron cercanas (aprox. 69 % frente a
  63,4 %), pero la lluvia mostrada por Sporas.io no pudo reconstruirse con sus
  estaciones visibles. No usar coincidencias puntuales como validación.
- En Sporas.io, «lluvia de activación» parece ser una señal de precipitación
  antecedente desplazada según la especie, pero su manual no hace auditables las
  fechas, duración, umbral, fuentes, pesos ni transformación exacta. Sus alturas
  y agregados también resultaron opacos en las comprobaciones visuales. Debe
  tratarse como inspiración de conceptos, no como verdad de referencia.
- Término provisional para Rainmapper: **señal hídrica antecedente**. No llamarla
  «lluvia de activación» ni atribuir causalidad hasta validar el concepto.

La revisión y ejemplos están en
`docs/mushrooms/literature/sporas_especies_informe_rainmapper.md` y el plan
científico en
`docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`.

La auditoría P0 ya ejecutada está en
`docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.
Concluye que la señal hídrica antecedente sí está aprendida en los ganadores
actuales, pero que añadir explícitamente lluvia × suelo previo no mejora de
forma estable y no justifica V7. Las tres especies aún no auditables y todos los
runners preparados están inventariados en
`docs/reports/mushroom-predictor-p0-pending-tests-and-python-audit-battery-2026-09-05.md`.
El mismo informe conserva además el contraste ciego, realizado antes del
reentrenamiento, de las seis observaciones locales del 5 de septiembre: Edulis
y Rovelló fueron favorables en Salteguet y La Masella como predecía el
precálculo anterior; Pinícola fue ausente, con una falsa recomendación favorable
en La Masella y abstención en Salteguet. Las seis observaciones ya forman parte
de las 406 elegibles del entrenamiento activo; por ello las predicciones
posteriores no deben presentarse como una segunda comprobación ciega.

## Próximos pasos recomendados

1. La política de aplicabilidad de lluvia ya está implementada: una desviación
   de precipitación se conserva como advertencia pero no causa por sí sola una
   abstención. Pasaron las pruebas dirigidas y la suite completa de 1.280 casos.
   Rovelló/La Masella del 8 de septiembre deja de abstenerse: los `32,14` mm se
   trazan como aviso y V5w devuelve `99,8511 %`.
2. Si se decide modificar KNN, probar calibración estrictamente fuera de muestra
   contra KNN actual y su sustituto V6. La auditoría ya cerrada encontró dos
   errores entre 14 unos exactos en el corte oficial, ambos de Ou de reig V4
   KNN; excluir KNN sin más empeora Brier y acierto favorable global.
3. Repetir la auditoría para Llanega negra, Marçot y Múrgola negra cuando sus
   hold-outs contengan ambas clases. Repetir también por zona solo donde haya
   ambas clases y varios episodios independientes.
4. Repetir la evaluación hold-out al incorporar observaciones nuevas. No es
   necesario archivar cada precálculo diario ni condicionar las salidas al campo
   a la predicción.
5. Si se muestra una futura señal hídrica antecedente, definir periodo exacto,
   fuente/procedencia, acumulado, cobertura, incertidumbre y diferencia
   contrafactual al retirar el episodio.
6. Solo después decidir si se publica HA `0.2.292` y se instala worker `1.0.38`.
   Si cambia código ejecutable, reajustar versiones y repetir validación antes de
   seguir `docs/release-flow.md`.

## Riesgos y límites

- Incidente HA real del 5 de septiembre, job
  `worker_job_P97f12hT1WfL`: el cálculo terminó en 747,14 s y HA recibió los
  465.711.104 bytes, pero su validación/publicación síncrona tardó 729,24 s. El
  worker `1.0.37` agotó su timeout HTTP de 300 s y registró `timed out` al 95 %.
  La telemetría `ha_activation_finished_at` solo se escribe después del
  reemplazo atómico y del recibo, por lo que HA sí activó el artefacto; el
  worker no pudo recibir ese recibo ni activar su copia. Los heartbeats fallaron
  durante la publicación y se restauraron al terminar. No se relanzó el job.
  El SQLite local final ocupa 29.233.152 bytes frente a 465.711.104 bytes en HA
  real. La regresión intermedia llegó a 477.696.000 bytes y 21.182 miembros al
  replicar cadenas de fallback; quedó corregida conservando 420 miembros y
  compactando la base de staging antes de publicarla. El transporte y la
  activación en la RPi4 siguen requiriendo una prueba real tras la release.
- El 100 % es una salida del modelo seleccionado, no certeza biológica. El caso
  territorial citado carece de evidencia propia de área y hereda evidencia
  global de especie.
- El límite Wilson evalúa acierto al recomendar salir; no es la probabilidad de
  florada ni corrige por sí solo una probabilidad mal calibrada.
- El precálculo actual es coherente e íntegro, pero puede reproducir cualquier
  problema científico del runtime/modelo activo con mucha eficiencia.
- El worktree mezcla muchas modificaciones todavía no publicadas y datos del
  usuario. Antes de release hay que revisar el diff ejecutable completo y no
  asumir que una prueba histórica sigue vigente.
- El estado HA real se revalidó el 5 de septiembre leyendo `/Volumes/share` y
  el worker local M1: HA declaró `0.2.291` y el contenedor worker sano declaró
  `1.0.37`. Los cambios del worktree siguen sin publicarse.

## Archivos relevantes

- Continuidad: `docs/codex-start-here.md`, `docs/todo.md`, `docs/decisions.md`.
- Selector y auditoría científica:
  `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`.
- Auditoría P0 multiespecie y multiversión de señal hídrica, lluvia antecedente
  y ganadores operativos V2--V6:
  `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.
- Comparación exploratoria con Sporas.io:
  `docs/mushrooms/literature/sporas_especies_informe_rainmapper.md`.
- Interpretación: `rainmapper_core/mushroom_prediction_interpretation.py`.
- UI: `rainmapper-app/app/mushroom_predictor_ui.py`.
- Selector/catálogos: `rainmapper_core/mushroom_ml_quality_catalog.py` y
  `rainmapper_core/mushroom_ml_reliability_audit.py`.
- Precálculo: `rainmapper_core/mushroom_predictor_precompute.py` y
  `rainmapper_core/mushroom_predictor_precompute_control.py`.
- Inputs operativos: `docker-media/rainmapper/mushroom-derived/ml_models/` y
  `docker-media/rainmapper/predictor_precompute/`.
