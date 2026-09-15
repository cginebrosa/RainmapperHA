<!-- Snapshot histórico anterior al cierre. No usar como estado vivo. -->

# Active Context

Estado operativo del **14/09/2026**, tras revisar sustratos ICGC y su combinación
con pH. Leer `codex-start-here.md` y este documento; `todo.md` amplía prioridades.
La ventana anterior se conserva en
[contexto previo](reports/prediction-map-context-before-engine-2026-09-13.md).

## Objetivo y siguiente acción

El **Mapa de predicción ya calcula probabilidades reales en la preview local**,
con entradas del punto, modelos instalados y el motor Python existente. Mantiene
una lista de compatibles: calculadas de mayor a menor para el día seleccionado;
sin cálculo al final, «Sin probabilidad calculada». Un cero calculado sigue siendo
0 %, nunca sustituye la falta de modelo o una abstención. La respuesta contiene
siete días; la lista cambia con el día elegido. Sigue siendo experimental.

**Puntos 1 y 2 implementados:** Rovelló por especie y conexión del motor compartido.
La última decisión del usuario **reemplaza la agrupación derivada**: cuatro filas
con IDs existentes, `Rovelló · deliciosus`, `· sanguifluus`, `· vinosus` y
`· salmonicolor/quieticolor`. No combinar probabilidades ni observaciones. Solo
usar el modelo de cada ID; tener modelo de deliciosus no habilita los otros.
Nombres en `metadata.map_display_name` de las fichas locales, sin lista en Python.

**Siguiente acción:** separar compatibilidad territorial de condiciones para
fructificar: retirar la época del filtro de especies posibles y dejar la fecha
al predictor. Después concretar y probar reglas conjuntas de suelo/pH por ficha
con los setales de contraste. Preparar posteriormente datos/configuración
portable y aceptación local equivalente HA–worker, preservando coordinadores.
La comparación de resultados y recursos entre ejecutores corresponde cuando
compartan entradas y artefactos. No hay autorización para runners, entrenamiento,
precálculo, construcción/publicación HA ni autenticación real de preview.

Contraste bibliográfico añadido el 14/09:
[suelo, hospedadores, pH, clima y descalcificación](mushrooms/prediction-map-ecological-factors-literature-es.md).
La lluvia infiltrada puede lavar carbonatos; roca calcárea no equivale siempre a
suelo superficial carbonatado. Un pH estimado ácido no demuestra descalcificación.
Propuesta pendiente: cruzar requisitos, tolerancias y preferencias por especie,
con tratamiento explícito de datos contradictorios. Esta revisión es documental;
no cambia perfiles ni convierte preferencias en exclusiones automáticas.
El usuario precisa dos niveles: **especies posibles por el lugar** (suelo/pH,
hospedadores/hábitat y altitud) y **condiciones para fructificar en una fecha**.
La decisión posterior reemplaza conservar la época en el primer nivel. Humedad,
temperatura y evaluación temporal corresponden al predictor; no duplicarlas.
El código aún aplica los meses en `EcologyReader._species`; su retirada está
pendiente. Plan concreto y criterios de aceptación en el anexo bibliográfico.
Rendimiento exigido: filtrar antes de inferir; las especies no factibles no
reciben cálculo. Mantener salida temprana sin candidatas, abstención por falta
de datos y compatibles sin modelo al final. Verificar cero invocaciones al
modelo para descartadas al separar los dos niveles.

## Comparación posterior con el Predictor de Olvan

Diagnóstico del punto 42.06282, 1.93765, incluido en el polígono local Olvan:
mapa usa siempre evidencia por especie. Manteniendo entradas/modelos/generación
idénticos y cambiando solo a la cadena sellada de Olvan en una prueba temporal,
aereus pasa de 33,5248 % (ventana 30d) a 36,3608 % (60d); caesarea mantiene
33,223 % y el mismo modelo. La captura del Predictor precalculado muestra 38 %
y 33 %. Tras el precálculo terminado por el usuario, el artefacto local activo
(revisión deseada 58) mantiene aereus en 38,0899 %. Recalculado el mismo punto:
33,5248 % con especie y 36,3608 % con evidencia Olvan. El modelo de 60d coincide
exactamente con el del área, pero 278 de sus 317 entradas difieren (meteorología
y estado hídrico, entre otras); no se han atribuido contribuciones por variable.
Ou de reig se mantiene alrededor de 33,21 % área y 33,22 % punto. Actualizar el
precálculo no elimina la diferencia; no se cambió la selección operativa.
[Comparación posterior](reports/prediction-map-olvan-after-precompute-2026-09-13.json).
**Decisión final del usuario:** mantener el Predictor por área y el mapa con
selección/evidencia por especie y entradas propias del punto, también dentro de
un área conocida. No incorporar evidencia de área al mapa ni intentar igualar
sus porcentajes. Retirada la propuesta anterior de los pendientes; el código
actual ya cumple esta decisión. La prueba con evidencia de Olvan fue diagnóstica.
[Prueba controlada](reports/prediction-map-olvan-selection-scope-2026-09-13.json).

## Hallazgo forestal y preguntas del usuario

Los tres puntos aportados devolvían `trees.unavailable/invalid_geometry`: un
polígono candidato MFE (FID 237242) tenía un anillo inválido lejos del punto y
abortaba la consulta. **No faltaban los datos de esos lugares.** El lector aplica
`MakeValid` en memoria solo a candidatos acotados, exige geometría válida y área
conservada con la tolerancia ya usada en preparación; caché de ocho reparaciones.
Fuentes e índice originales intactos; no descarga ni reconstrucción.

Revalidado por la API de la preview después de reiniciarla:

| Punto | Árboles recuperados | Edulis el 13/09 |
|---|---|---|
| Fogars 41.75621, 2.40315 | Encina | Fuera por altitud |
| Arbúcies 41.79996, 2.48872 | Haya, castaño | Fuera por altitud |
| Fogars 41.77528, 2.46480 | Haya | Compatible, 33,3862 % |

En el último punto antes fallaba únicamente el requisito de hospedador; altura
y pH encajaban. Macrolepiota y Lepista entraban por hábitat: sus fichas son no
ectomicorrícicas y aceptan bosque caducifolio. No deducir un árbol concreto de
esa etiqueta ni añadirla como sustituto universal de un hospedador.
Los verdaderos huecos siguen siendo desconocidos; no implican ausencia física.

Caso Vallcebre 42.22549, 1.81417: llanega negra no aparece el 13/09 únicamente
por fecha (`outside_season`). Pino rojo, 1.050 m y pH 6,9 sí encajan. Ficha actual:
meses principales 10–12, secundario 1; el mismo punto pasa a compatible el 1/10.
Sin cambios en ficha ni cálculo de probabilidades futuras.
[Diagnóstico](reports/prediction-map-vallcebre-latitabundus-2026-09-13.json).

Caso La Selva del Camp 41.22694, 1.09095: aereus queda fuera únicamente por
`ph_outside`: media OpenLandMap 7,2 frente al máximo provisional 6,8 de la ficha
(3,5–6,8). Encina/roble, 415,4 m y septiembre encajan. El usuario comunica
abundancia real; no se ha determinado si falla la estimación o el límite de la
ficha. Intervalo mostrado 6,7–7,8, informativo según política acordada. Sin cambios
al filtro, a la ficha ni a los datos originales.
[Diagnóstico](reports/prediction-map-selva-aereus-ph-2026-09-13.json).
Segundo caso comunicado por el usuario: 41.23675, 1.13555, también La Selva del
Camp. Aereus excluido solo por pH estimado 7,5 (intervalo 6,6–8,1), frente a
máximo 6,8; encina/quejigo, 357,9 m y septiembre encajan. Son dos discrepancias
confirmadas entre filtro y presencia reportada, no mediciones de pH del setal.
[Segundo punto](reports/prediction-map-selva-aereus-ph-second-point-2026-09-13.json).


El usuario **rechaza ampliar globalmente el máximo de aereus a 7,5**; propuesta
retirada, ficha sigue en 6,8. Señala el sustrato silíceo en ambos setales: ambos
pertenecen a la unidad ICGC `mc_Capg` (pizarras), mapping revisado a `lith_slate`
y `soil_siliceous`. La ficha sí acepta ese suelo y el lector registra
`soil_preference_match`, pero la media de pH sigue vetando. Los intervalos
OpenLandMap 6,7–7,8 y 6,6–8,1 solapan la ventana de la ficha. Pendiente revisar
cómo combinar esa evidencia, sin deducir pH de roca ni aplicar excepciones
universales para sustrato silíceo. Este diagnóstico precede al ensayo descrito debajo.
[Comprobación conjunta](reports/prediction-map-selva-aereus-substrate-2026-09-13.json).

El usuario propone después un filtro conjunto con categorías de suelo del GIS
(ácido/silíceo/calizo/básico/neutro) y pH. Ya existen en el catálogo local; estudiar
su combinación separando composición y reacción química, conservando mezclas y
procedencia. No convertir preferencias en vetos ni ausencia de mapping en suelo
incompatible. Revisión y diseño documentados en
[propuesta de pH, §14](mushrooms/prediction-map-species-ph-proposal-es.md#14-propuesta-de-filtro-conjunto-de-sustrato-y-ph).
**Ensayo inicial autorizado:** `broad_species_windows_v3`, bloque
opcional `ecology.soil_filter`, activado solo en aereus. Sustrato silíceo revisado
y solapamiento del intervalo OpenLandMap permiten admitirla con aviso aunque
la media exceda 6,8; media y límites originales intactos. Hosts, altitud, época,
datos ausentes e intervalos disjuntos siguen controlándose. Admite exclusiones
configurables y abstiene ante mezcla aceptada/excluida, pero no hay exclusiones
activadas en aereus ni nuevas reglas en las otras 20 fichas. No se cambiaron
mappings/catálogos ni se equiparó automáticamente roca con acidez.
API local validada en los dos puntos: 48,8947 % y 44,8780 % para 13/09/2026.
Chrome verifica el segundo punto, aviso y pH 7,5. 59 pruebas dirigidas pasan
(26 ecología, 12 contrato, 7 predicción, 14 validador). Preview reiniciada en el
mismo puerto y con las mismas fuentes; recargar pestaña para el aviso nuevo.
[Configuración, límites y backup, §15](mushrooms/prediction-map-species-ph-proposal-es.md#15-prueba-local-del-filtro-combinado)
y [evidencia](reports/prediction-map-soil-filter-trial-2026-09-14.json).

Nuevo setal 41.22012, 1.06989: usuario comunica caesarea y aereus. Comprobación
directa MFE: polígono 2325877, «No arbolado», tres especies «sin datos» y códigos
cero; no es fallo de lectura ni falta de cobertura. ICGC indica bosque denso
(223). Polígono vecino MFE 2326361 a 52,09 m registra pino carrasco, encina y
quejigo; no se trasladan al punto automáticamente. Aereus abstiene por
`terrain_context_missing`; pH del punto aportado 6,8 [6,0–7,7], dentro de su
ventana. La captura muestra otros valores (7,0/cubierta 221), conservados como
referencia visual, no sustituyen la consulta exacta. `Ggd` está sin mapping exacto
(revisión previa unresolved); pendiente revisar equivalencia de granodioritas y
granitos y cómo resolver la discrepancia de árboles sin inventar hospedadores.
[Diagnóstico](reports/prediction-map-ggd-missing-hosts-2026-09-14.json).
Completada después equivalencia exacta `Ggd` (misma fuente/edición/campo) a
`lith_siliceous_substrate` y `soil_siliceous`, confianza media, sin deducir pH.
Informe original unresolved preservado; nueva revisión local
`gis-mapping-reviews/icgc-ggd-2026-09-14.json` y backup del mapping.
Punto vecino aportado 41.22071, 1.07009: encina/quejigo, pH 6,9 [6,0–7,7];
tras mapping aereus compatible, 47,2049 % para 14/09/2026. Primer punto sigue
absteniendo por hosts. Validado por API de preview y 26 pruebas de ecología.
[Evidencia](reports/prediction-map-ggd-mapping-2026-09-14.json).
El usuario pregunta por recuperar árboles del punto próximo: actualmente solo
está implementado/documentado el píxel próximo para pH. ForestReader exige
contención en polígono; no traslada los árboles vecinos. Pendiente concretar
y añadir esa alternativa si se adopta, indicando distancia y procedencia.

## Revisión completa de unidades ICGC y contraste de especies

Completada la revisión autorizada de las **1.055 unidades ICGC** descargadas.
GEODE queda expresamente como siguiente fase. No se repitieron descargas,
auditorías de geometrías ni migraciones. Comprobados los pares actuales de
código/descripción contra la revisión previa, y revisadas las equivalencias
aceptadas y las pendientes. Resultado local: **1.046 códigos con materiales
identificados en 192 reglas geológicas compartidas**, 14 tipos de material
añadidos al catálogo; nueve decisiones sin equivalencia suficientemente segura.
Identificar un depósito no resuelve necesariamente su composición: 392 unidades
siguen indeterminadas para silíceo/calizo/yesífero. Se conservan mezclas, origen,
descripciones y ausencia de proporciones; no se infiere pH de la roca.

**Vigente en preview: `broad_species_windows_v4`.** En aereus se añade
`ph_override_blocked_soil_ids=[soil_calcareous, soil_gypsiferous]`: si coexisten
esos componentes no rescatan una media fuera de rango por contener también
silíceo. No es un veto geológico cuando el pH sí encaja. Máximo 6,8 conservado;
`excluded_soil_ids` vacío. Las otras veinte fichas, los 21 rangos, hospedadores,
altitudes, fechas y afinidades quedan intactos. Contraste documental de las 21
fichas completado; no confundir preferencias con requisitos nuevos. Vinosus
conserva contradicciones identificadas para revisión; la calcicolía de trufa
negra no se resuelve midiendo solo pH ni sustituyendo suelo por roca madre.

[Revisión y matriz por especie](mushrooms/prediction-map-substrate-species-review-es.md).
Decisiones exactas en el JSON local
`gis-mapping-reviews/icgc-substrates-2026-09-14.json`; backups de catálogo,
mappings y perfiles con sufijo `20260913T224213651843Z.icgc-substrates.keep.json`.
La fecha del nombre de backup es UTC. Informe con hashes y validación:
[evidencia](reports/prediction-map-icgc-substrates-2026-09-14.json).

67 pruebas dirigidas pasan; compiladas y contrastadas las 1.055 decisiones.
Preview reiniciada con mismo puerto y fuentes. API verifica política v4 y fecha
14/09: aereus 47,2049 % en Ggd con hosts, 47,089 % y 43,9118 % en los dos setales
de La Selva; Ggd sin hosts sigue absteniendo. Chrome aislado confirma en Ggd
granito + granodiorita, pH 6,9 [6,0–7,7], comparación SoilGrids y aviso de aereus.
No son una nueva calibración científica ni pruebas de HA/worker desplegados.

Nuevo caso comprobado: La Vansa i Fórnols, 42.27588, 1.52460. ICGC `PPcm`,
lutitas rojas con intercalaciones de caliza micrítica; mapping `soil_calcareous`.
Usuario considera que allí no aparecen edulis, pinophilus ni rossinyol por ser
calcáreo. API del 14/09 los admite por pino rojo, 1.663,7 m, época y media pH 6,3
(OpenLandMap 5,2–7,3; SoilGrids superficial 6,1). Ninguna de esas tres fichas
tiene `soil_filter`; sus preferencias no excluyen. Diagnóstico documentado,
sin activar vetos nuevos ni cambiar pH. No confundir componente calizo en la
cartografía con medición del suelo ni con imposibilidad biológica demostrada.
[Evidencia y reglas vigentes](reports/prediction-map-vansa-calcareous-2026-09-14.json).

## Reglas y datos que se conservan

- Autoridad editable: `docker-data/mushroom-data/`, 21 fichas y catálogo local.
  No sustituirlos por semillas del repo ni promoverlos a HA implícitamente.
- Hospedadores específicos obligatorios para fichas ectomicorrícicas. Jerarquía
  explícita: pino negro acepta pino negro o género pinos; no pino rojo. Género
  pinos admite descendientes; especies hermanas no son equivalentes. Una
  alternativa suficiente. Las otras fichas requieren hábitat revisado compatible.
- UI única **Terreno**; separación interna de árboles/hábitats para aplicar la
  regla adecuada. Sin hábitat ni hosts, `terrain_context_missing`, sin porcentajes.
- Mappings locales: 1.046 códigos geológicos en 192 reglas, cuatro códigos de
  cubierta y cinco filas MVC50 conservados. Nueve unidades geológicas revisadas
  sin equivalencia segura; 37 cubiertas siguen pendientes. Mezclas mantienen
  componentes sin duplicados. No deducir pH de litología ni introducir vetos
  universales a partir de afinidades; usar la política revisada de cada ficha.
- OpenLandMap local: nueve GeoTIFF, 368 MiB en
  `mushroom-map-GIS/openlandmap-ph/spain-v20250204/`; selección con media 0–30 cm.
  Q16–Q84 informativo, comparación SoilGrids visible; profundidad solo en Terreno.
  Si falta media: píxel válido más cercano hasta 1 km editable, distancia visible;
  sin vecino, desconocido. No fallback silencioso a SoilGrids. No repetir descarga.
- 21 rangos de pH provisionales aplicados por decisión del usuario, revisables
  frente a setales. Olvan 6,6 y Merlès 6,7 en las comprobaciones previas, SoilGrids
  7,6; coincidencia con otra web no demuestra precisión del suelo del punto.
- Ediciones concurrentes preservadas: la ficha local actual de edulis tiene mínimo
  **900 m**, pinophilus **1.100 m**. No restaurar los antiguos 600 m. Este incremento
  solo añadió los cuatro `map_display_name`; backup previo:
  `docker-data/mushroom-data/backups/mushroom_profiles.20260913T182117725988Z.keep.json`.
- Catálogo, mappings y perfiles locales tienen hashes y backups de cada revisión;
  no comparar su estado actual solo con el informe histórico de integración.
  Observaciones conservadas. Las del repo tienen cambios anteriores del usuario;
  no incluirlas ciegamente en un commit.
- SoilGrids 54 retenciones + nueve pH ya adquiridos/auditados. Se usa para agua.
  Francia sin vegetación suficiente sigue absteniéndose. No ampliar cobertura
  como condición para continuar ni repetir auditorías/migraciones terminadas.

## Implementación y contrato

- `mushroom_map_model_runtime.PointModelRuntime`: registro/modelos existentes,
  evidencia sellada por especie y entradas meteorológicas/hídricas del punto.
  No adopta el área cercana ni inventa evidencia por área. Mantiene declaración
  `point_validation=not_established`; hace falta validar transferencia a setales.
- `mushroom_map_prediction.resolve_species_week`: misma continuidad
  `weekly_lag_event_v2`, familia `lag_event` h1–h7 y corte común. Veto diario sin
  cambiar familia; fallback diario previo si corresponde. Materialización
  perezosa en orden sellado, con pruebas de equivalencia al modo completo.
- `mushroom_ml_predictor.season_phase_for_months`: regla existente extraída y
  compartida, sin umbrales nuevos. Ventanas meteorológicas de 90/365 días según
  el modelo; el popup sigue mostrando como máximo 60 días observados.
- `mushroom_map_execution.PointExecutor`: mismo ejecutor para HA/worker, tres
  lectores residentes (geografía, modelo, meteorología). Nuevo script
  `scripts/prediction-map-local-model.py`; incluido en los Dockerfiles junto
  con los módulos necesarios. Sin construir imágenes ni activar worker.
- `prediction_map_point_v1` admite explícitamente `data_mode=prediction`;
  contrato/broker/UI validados conjuntamente. IDs reales ligados a `ecology`,
  fechas y punto verificados; cero y null distintos. Sin modelos demo en modo real.
  `scientifically_validated=false` incluso con cálculo disponible.
- El catálogo de calidad original se verifica por hash y se proyecta por lectura
  incremental: conserva resoluciones selladas por especie y entries, descarta
  arrays por área. Límites antes de materializar filas; ninguna evidencia grande
  se transporta al visor. Máximo 32 especies; payload final acotado a 256 KiB.
- No cambiar el núcleo del mapa meteorológico. Clic/hover de estaciones conservan
  popup meteorológico. Mapa nuevo en `/protected/prediction-map/index.html`;
  diana, modal cancelable, resultado anclado y fechas mantienen comportamiento.
- Preview con usuario ficticio y preferencias temporales, sin escribir devices
  reales. Futuro selector local/worker se guarda con los demás ajustes del
  dispositivo. Local significa servidor Python, no navegador.

## Estado operativo y evidencia

Preview en `http://127.0.0.1:65517/protected/prediction-map/index.html`, reiniciada
con la corrección forestal. Revalidar PID antes de operar; sesiones/PID no son
identidad estable. GDAL `/opt/homebrew/bin/python3`; modelo/meteorología
`.venv/bin/python` **sin resolver su symlink**. Datos observados `docker-data/Data`,
`stations.txt` y `PublicData`. Perfil/catálogo/mappings locales explícitos.

Índice activo `mushroom-map-GIS/terrain-index/point-inputs-2026-09-12.sqlite`
(ya existía; no reconstruido). Modelo:
`--models-root docker-media/rainmapper/mushroom-derived/ml_models`
y `--model-registry docker-data/mushroom-data/mushroom_ml_version_registry.json`.
Batch comprobado `operational_20260909T184116Z`; modelos resueltos del registro,
sin codificar las nueve especies de la captura del usuario.

[Informe de integración, puntos, hashes y pruebas](reports/prediction-map-engine-integration-2026-09-13.json).
Pruebas dirigidas de contrato/broker/filtro/continuidad/motor, 82 de regresión
Predictor/comparación/meteorología, 21 GDAL pH/terreno y 12 forestales correctas.
Chrome escritorio/móvil: orden descendente, cero/null, cambio de día, errores,
cancelación y mapa meteorológico conservados. Ejecutor completo probado con Olvan
(21.791 bytes) y Ger (19.522); API de preview tras corrección con los tres puntos
(16.122–16.951 bytes). No es benchmark ni validación científica de porcentajes.

HA local, HA real y worker instalado **no recibieron esta integración**. Las
versiones históricas de contenedores no se han revalidado en este incremento.
La paridad de imágenes/release requiere su circuito local y aceptación; no
extrapolar las pruebas de preview a Raspberry Pi ni al worker remoto.

## Límites y pendientes

1. Validar con setales conocidos y fichas actuales; una especie compatible no
   asegura fructificación. Respetar los cambios del usuario en el mantenimiento.
2. Portabilidad GIS e integración remota/configuración; comparar ejecutores con
   mismos datos/modelos. Cartografía fuera de Git/Docker, no viajará con la imagen.
3. Mappings agrupados los leen mapa y validador; editores/consumidores legacy aún
   pendientes. Promoción de catálogos/fichas/mappings requiere decisión explícita.
4. Cobertura adicional, Safari/iPhone, superficie coloreada y demás fases de la
   especificación siguen pendientes; no confundir la lista semanal calculada
   con haber terminado todas las visualizaciones o la integración operativa.
5. No runners, entrenamiento, precálculo, publicaciones HA, borrado de datos,
   backups u observaciones ni cambios de URL de coordinador. RPi4 compartida:
   evitar copias masivas, reconstrucciones diagnósticas y aumentos de límites.
   Sin Tailscale ni autenticación real en preview. Informar al menos cada minuto.

Incidencia meteorológica anterior: Barcelona `ESCAT0800000008011B` corregida por
petición expresa en catálogos local/HA real, conservando mediciones y backups.
Erinya `ESCAT2500000025515B` pendiente de la fuente por decisión del usuario.
Regla final permite saltos con destino en España aproximada, incluidas islas,
con independencia del origen; código no desplegado aquí ni runner reejecutado.
[Registro y rutas](reports/weather-coordinate-conflict-2026-09-13.json).

Diseño central: [especificación](mushrooms/prediction-map-specification-es.md).
Evidencia previa de pH, mappings y ventanas: informes enlazados desde el contexto
histórico. No repetir esos trabajos al retomar.
