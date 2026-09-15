# Revisión conjunta de sustrato y pH

Revisión local del 14/09/2026. Alcance autorizado: las **1.055 unidades ICGC**
descargadas y el contraste con las **21 fichas locales**. GEODE queda para la
siguiente fase. No se han revisado polígonos nuevos ni descargado cartografía.

## Cómo se combinan

**Estado vigente 14/09: niveles separados y reglas locales v5 aplicadas.** El
apartado «Reglas locales conjuntas v5» sustituye el estado operativo v4 descrito
en los apartados históricos de esta revisión.

Contraste bibliográfico posterior: [suelo, hospedadores, pH, clima y
descalcificación](prediction-map-ecological-factors-literature-es.md).
Contiene una propuesta pendiente de aplicar; no establece un veto universal por
caliza ni identifica descalcificación únicamente mediante un pH estimado bajo.

Se mantienen dos datos distintos: **composición del terreno** y **pH del suelo**.
La geología identifica materiales y posibles tendencias; OpenLandMap aporta la
estimación de pH. La ficha indica preferencias y, cuando estén justificadas,
restricciones. Además siguen siendo necesarios hospedadores o hábitat y altitud
compatibles. La época corresponde al predictor, no a esta selección territorial.
Ningún sustrato sustituye esos requisitos.

El vocabulario del [ICGC](https://app.icgc.cat/web/es/mapageol_atles_vocabllegenda_v2.php)
permite distinguir granodiorita, mármol y otros materiales. «Alcalino» en un
granito no significa pH básico del suelo. Los nombres de formaciones tampoco
son materiales: «Margues de la Guixa» no acredita yeso. La reacción del suelo
también depende de su evolución y del ambiente, según la [ficha de pH del
NRCS](https://www.nrcs.usda.gov/sites/default/files/2022-10/Soil%20PH.pdf).

No se convierten automáticamente silíceo/calizo en ácido/básico, ni desconocido
en neutro. Las etiquetas químicas derivadas del pH no cuentan como una segunda
evidencia independiente. Los antiguos intervalos orientativos del vocabulario
`soil_types` no se propagan desde la roca al pH del punto.

## Resultado de la revisión ICGC

Se comprobó que los pares actuales `Codi/Descripcio` coinciden con los 1.055 de
la revisión previa mediante una consulta DISTINCT de la tabla de atributos;
no se repitió la auditoría de geometrías. Se revisaron tanto las equivalencias
aceptadas como las que habían quedado sin resolver.

| Clasificación de los componentes reconocidos | Unidades |
|---|---:|
| Componente silíceo, sin carbonato/yeso identificado | 150 |
| Componente carbonatado, sin silíceo/yeso identificado | 364 |
| Componente yesífero, sin silíceo/carbonato identificado | 14 |
| Mezcla de las categorías anteriores | 58 |
| Otros materiales identificados | 77 |
| Composición indeterminada para esas categorías | 392 |
| **Total revisado** | **1.055** |

Estos números no son superficies ni clases de suelos medidas. Una unidad con
componente silíceo puede contener también detritos o roca máfica; no se presume
que sea homogénea ni que se conozcan las proporciones. «Sin identificado» tampoco
demuestra ausencia. Se conservan todos los materiales reconocidos y la descripción.

Hay equivalencias de materiales para **1.046 códigos**, agrupadas en **192 reglas
geológicas compartidas**. Las nueve unidades restantes tienen una decisión de
revisión explícita sin equivalencia suficientemente segura: `CK`, `Dlva`, `Fd`,
`Glpm`, `Org`, `Pze`, `bf`, `ff` y `mr_EÇOr`. Muchos depósitos reconocidos como
aluviales o detríticos siguen teniendo composición indeterminada: reconocer
gravas no permite decidir de qué roca proceden.

Se añaden **14 tipos de material** al catálogo local, con etiquetas ES/CA/EN y
sin pH inferido: granodiorita, mármol, gneis, filita, sedimentario silíceo, arcosa,
máfico, ígneo intermedio, calcosilicatado, corneana, depósito orgánico, depósito
salino, sedimento no consolidado y componente carbonatado.

Ejemplos revisados:

| Código | Resultado | Límite de interpretación |
|---|---|---|
| `Ggd` | Granodiorita + granito; tendencia silícea | No asigna pH ácido. Conserva el resultado de la corrección previa. |
| `mc_Dcm` | Mármol; tendencia carbonatada | No copia el pH de caliza ni acredita carbonato activo superficial. |
| `mc_Capl` | Pizarra + caliza; mezcla silícea/carbonatada | No hereda la composición de `Capl` por semejanza del código. |
| `Cacnl` | Caliza + radiolarita; mezcla | No elige solo el componente favorable a la seta. |
| `Qes` | Sauló; tendencia silícea/arenosa | No acredita el pH actual. |
| `Bo`, `Ggdq` | Basalto / roca ígnea intermedia | No se convierten en suelo básico por terminología petrológica. |
| `Orst` | Material con nódulos carbonatados disueltos | No atribuye carbonatos residuales ni acidez actual. |
| `Qt1` | Depósito aluvial detrítico | No acredita humedad actual, humus ni ribera. |
| `bf`, `ff` | Deformación/falla, composición indeterminada | No se inventa roca original. |

La autoridad editable permanece en `docker-data/mushroom-data/`:

- `mushroom_reference_catalogs.json`: vocabulario.
- `mushroom_gis_mappings.json`: equivalencias exactas por fuente, edición y código.
- `gis-mapping-reviews/icgc-substrates-2026-09-14.json`: 1.055 decisiones con
  descripción original, componentes, límites, procedencia y cambios.
- `mushroom_profiles.json`: preferencias, rangos y política por especie.

La clasificación no usa expresiones regulares ni IDs de especies en el motor.
Las ayudas de preparación son externas al runtime; el resultado revisado son
los JSON exactos. Se conservan las revisiones anteriores y backups de los tres
JSON locales antes de aplicar este incremento. Las semillas del repo no se usan.

## Contraste de las 21 fichas

La tabla combina la lectura actual de `mushroom_profiles.json` con los apartados
4.1–4.21 de la [revisión bibliográfica local](prediction-map-species-literature-review-es.md)
y las justificaciones individuales de la [propuesta de pH, §4](prediction-map-species-ph-proposal-es.md#4-justificación-por-especie).
Los rangos son los ya aplicados, **no nuevos extremos biológicos demostrados**.

| Ficha | Terreno a considerar según la revisión | pH local | Tratamiento de la geología |
|---|---|---:|---|
| Amanita caesarea | Preferencia silícea/ácida; tolerancia neutra en ficha | 3,5–7,5 | Preferencia, sin veto a toda roca carbonatada. |
| Boletus aereus | Preferencia silícea/ácida | 3,5–6,8 | Ensayo combinado descrito debajo. |
| Boletus edulis | Preferencia ácida; posibles suelos acidificados sobre caliza | 3,5–7,5 | La roca caliza por sí sola no lo excluye. |
| Boletus pinophilus | Preferencia silícea/ácida; caliza acidificada contemplada | 3,5–6,8 | No convertir preferencia en litología obligatoria. |
| Calocybe gambosa | Preferencia caliza/rica en bases; prados | 6,5–8,8 | Preferencia; el pH del corro puede ser efecto del hongo. |
| Cantharellus cibarius s.l. | Preferencia silícea/ácida, con diversidad del grupo | 3,5–7,5 | No extrapolar exclusividad a todo el complejo. |
| Cantharellus lutescens | Contextos silíceos y calcáreos; humedad/musgo | 3,5–8,8 | Admitir ambas tendencias; falta afinidad litológica explícita en ficha. |
| Craterellus cornucopioides | Ambos contextos, énfasis distintos entre fuentes | 3,5–8,8 | Preferencia no resuelta; no escoger una sola roca. |
| Hygrophorus latitabundus | Preferencia caliza/rica en bases | 6,5–8,8 | La revisión no acredita exclusividad universal; mantener pinos y época. |
| Hygrophorus marzuolus | Tendencia silícea/ácida; suelo descarbonatado posible | 3,5–6,8 | No deducir pH superficial de la roca. |
| Lactarius deliciosus | Contextos ácidos y calizos en fuentes | 3,5–8,8 | No limitar por roca; pinos siguen necesarios. |
| L. salmonicolor / quieticolor | Grupo con tendencias edáficas diferentes | 3,5–8,8 | Mantener amplitud y una sola ficha, sin dividir observaciones. |
| Lactarius sanguifluus | Preferencia caliza, tolerancia más amplia en fuente técnica | 3,5–8,8 | Silíceo desfavorable no equivale a exclusión calibrada. |
| Lactarius vinosus | Tendencia silícea; ficha internamente contradictoria | 3,5–7,5 | No derivar vetos ni sumar afinidades contradictorias. |
| Lepista nuda | Ambos sustratos; relevancia de materia orgánica | 3,5–8,8 | No exigir roca concreta. |
| Macrolepiota procera | Ambos sustratos; materia orgánica/hábitat | 3,5–8,8 | No exigir roca ni árboles concretos. |
| Marasmius oreades | Prados y microhábitat, sin exclusividad mineralógica acreditada | 3,5–8,8 | No añadir una roca obligatoria. |
| Morchella elata complex | Complejo heterogéneo; contextos aluviales/humíferos en ficha | 3,5–8,8 | No copiar calcicolía de M. esculenta. |
| Russula virescens | Preferencia silícea/ácida | 3,5–6,8 | No convertirla en ausencia sobre toda geología carbonatada. |
| Tricholoma terreum | Preferencia caliza, también silíceos descritos | 3,5–8,8 | Admitir ambos contextos. |
| Tuber melanosporum | Suelo carbonatado y aireado con respaldo ecológico | 7,1–8,9 | pH adecuado no acredita carbonato activo; falta medirlo. |

**Estado operativo:** esta revisión no convierte las afinidades en nuevos vetos
de suelo para las 21 especies. Sus rangos de pH, árboles, altitudes, fechas y
afinidades se conservan. Las otras veinte fichas mantienen comparación por la
media de pH, sin excepción litológica nueva. La revisión no queda confundida
con una activación masiva de filtros aún no justificados.

En vinosus siguen señaladas dos contradicciones concretas: `soil_acidic` aparece
como primario con afinidad negativa y las rocas carbonatadas figuran preferidas
junto a la tendencia silícea. No se inventa un peso para resolverlas. En trufa
negra, exigir roca caliza no sustituiría el requisito de un suelo carbonatado:
son variables distintas. Ambos puntos quedan identificados para la próxima
revisión de fichas, sin bloquear las equivalencias ICGC.

## Cautela añadida al ensayo de aereus

Política `broad_species_windows_v4`. La ficha conserva `ph_max=6.8`, su suelo
aceptado `soil_siliceous` y la excepción `estimated_interval_overlap`. Añade:

```json
"ph_override_blocked_soil_ids": ["soil_calcareous", "soil_gypsiferous"]
```

Este campo impide que una mezcla con carbonatos o yeso rescate una media fuera
de rango. **No es una exclusión general de esos suelos**: `excluded_soil_ids`
sigue vacío. Si la media entra en el rango, se mantienen los demás filtros.

| Caso, con hospedadores, altitud y época compatibles | Resultado del filtro |
|---|---|
| Silíceo, media 7,5, intervalo 6,6–8,1 | Admisión condicionada y aviso; conserva el 7,5. |
| Silíceo + calizo, misma media e intervalo | Fuera por pH; no aplicar excepción. |
| Silíceo + calizo, media 6,7 | Compatible con estos filtros; no hay veto geológico universal. |
| Geología desconocida, media 7,5 | Fuera por pH; no inventar sustrato favorable. |
| Silíceo pero falta pH o hospedador | Desconocido; el sustrato no completa ese dato. |

El intervalo expresa incertidumbre de la estimación; no demuestra que el pH real
esté dentro del rango de la especie. La excepción es un ensayo revisable frente
a setales, no una medición ni una probabilidad adicional. La caliza acidificada
puede explicar algunos casos, pero no se presupone en un punto sin evidencia.

La validación de este incremento y los hashes aplicados se registran en
[el informe](../reports/prediction-map-icgc-substrates-2026-09-14.json).
No incluye entrenamiento, precálculo, publicación HA ni integración GEODE.

## Caso de contraste: La Vansa i Fórnols

Comprobado tras la captura del usuario: **42.27588, 1.52460**, fecha 14/09/2026.
La unidad `PPcm` describe lutitas rojas con intercalaciones de calizas micríticas.
El lector identifica `lith_fine_clastic`, `lith_limestone` y `soil_calcareous`.
Por tanto, sí hay componente calcáreo identificado en la consulta.

Edulis, pinophilus y cibarius se admiten con motivos `hosts_match`,
`altitude_match` y `ph_match`: pino rojo, 1.663,7 m y OpenLandMap 6,3
[5,2–7,3], dentro de sus ventanas actuales en septiembre. SoilGrids superficial
estima 6,1. Sus tres fichas carecen de `soil_filter`; las preferencias silíceas
y la afinidad desfavorable a caliza de pinophilus/cibarius no se aplican como veto.

El usuario considera incompatible ese lugar con esas especies por ser calcáreo.
Se registra como contraste de terreno para decidir el filtro conjunto. No prueba
un pH medido ni permite establecer imposibilidad biológica solo con la unidad
geológica. Esta comprobación no modifica las fichas ni activa exclusiones.
[Respuesta y reglas verificadas](../reports/prediction-map-vansa-calcareous-2026-09-14.json).

## Reglas locales conjuntas v5

Aplicadas el 14/09/2026 únicamente en `ecology.soil_filter` de cuatro fichas de
`docker-data/mushroom-data/mushroom_profiles.json`. No se cambian pH, altitudes,
afinidades, hospedadores, fenología, metadatos del usuario ni las otras 17 fichas.
Catálogo y mappings locales se leen tal como quedaron revisados; semillas intactas.
Procedencia: las revisiones por especie y de pH enlazadas en la matriz de 21 fichas,
el contraste bibliográfico suelo/hospedador y los setales documentados arriba.
Son reglas operativas provisionales, no límites biológicos demostrados.

| Ficha | Rango conservado | Apoyo y admisión condicionada | Fuera de rango |
|---|---|---|---|
| aereus | 3,5–6,8 | Silíceo + pH admitido apoya la selección. Componente calcáreo + pH admitido: condicionado, sin confirmar descalcificación. | Conserva el ensayo previo: solo OpenLandMap con intervalo válido solapado y componente silíceo, sin carbonatos/yeso identificados, puede admitir con aviso una media fuera de rango. |
| edulis | 3,5–7,5 | Preferencia silícea; caliza cartografiada + pH admitido: condicionado. La preferencia existente por suelo descalcificado se conserva, sin atribuirla al punto a partir del pH. | Comparación estricta con la media; no hereda la excepción de aereus. |
| pinophilus | 3,5–6,8 | Preferencia silícea; caliza cartografiada + pH admitido: condicionado. Altitud mínima editada de 1.100 m conservada. | Comparación estricta con la media. |
| cibarius s.l. | 3,5–7,5 | Preferencia silícea; componente calcáreo + pH admitido: condicionado, sin declarar exclusividad litológica para todo el complejo. | Comparación estricta con la media. |

Campos de las cuatro fichas:

- `accepted_soil_ids=[soil_siliceous]` indica apoyo, **no una lista exhaustiva**.
- `excluded_soil_ids=[]`: ningún veto litológico nuevo. Una afinidad negativa
  o `avoid` no se transforma en prohibición.
- `conditional_soil_ids=[soil_calcareous]`: con pH dentro del rango añade
  `soil_ph_conditional`; también cuando la unidad mezcla silíceo y calcáreo.
  La roca no localiza carbonatos activos ni mide el horizonte superficial.
- Otros tipos identificados fuera de las preferencias no se excluyen:
  `soil_not_listed`, admisión condicionada si pasan los demás requisitos.
- `require_soil_context=true`: sin tendencia edáfica resuelta por mappings
  aceptados, `unknown/soil_unresolved`. Es abstención por falta de composición,
  no una prohibición biológica ni una exigencia de roca silícea. Identificar solo
  un depósito de composición indeterminada no completa ese dato.
- Sin pH válido, hospedador/hábitat o altitud necesaria: desconocido. Una
  incompatibilidad explícita de pH o altitud sigue descartando. El sustrato no
  rellena esos huecos ni se usa para generar un pH.
- `review_ref` enlaza este apartado. Los motivos y `admission=conditional`
  distinguen incertidumbre de admisión ordinaria. No descuentan porcentajes.

La Selva y L’Aleixar conservan la admisión condicionada de aereus por el ensayo
de incertidumbre. La Vansa deja de aparecer como admisión ordinaria para edulis,
pinophilus y cibarius: pasa a **condicionada**, sin afirmar descalcificación ni
imposibilidad. Con pH fuera de rango, la caliza no rescata estas tres fichas.
El punto Ggd sin hosts sigue absteniendo. Vallcebre conserva latitabundus en el
nivel territorial incluso fuera de los meses de su ficha.

El motor genérico aplica datos locales; no contiene IDs de estas especies,
coordenadas, equivalencias geológicas ni descuentos específicos. La extensión
al resto de fichas y las contradicciones de vinosus quedan pendientes, sin
activación masiva. Evidencia del incremento en
[el informe v5](../reports/prediction-map-two-levels-2026-09-14.json).

## Decisión posterior: conservar las reglas conjuntas

El usuario comprobó la alternativa «restricción por tipo de suelo y confirmación
por pH» y la descartó por excluir sitios de aereus. **Se conservan las reglas
anteriores**, sin nuevo requisito litológico excluyente ni cambios de pH.
Las admisiones condicionadas no pasan a veto/abstención automática. Esta decisión
se refiere al suelo; el filtro estacional v6 y las etiquetas de fase siguen activos.
