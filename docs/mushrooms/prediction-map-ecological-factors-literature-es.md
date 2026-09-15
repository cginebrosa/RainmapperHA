# Suelo, hospedadores, pH y clima: contraste bibliográfico

14/09/2026. Revisión solicitada tras los setales de La Selva del Camp y el
contraste de La Vansa. **Revisión bibliográfica y propuesta original.** La separación
de niveles y las primeras cuatro reglas se aplicaron después en v5; estado vigente
en [las reglas locales](prediction-map-substrate-species-review-es.md#reglas-locales-conjuntas-v5).
Complementa la [revisión de sustratos y fichas](prediction-map-substrate-species-review-es.md)
y la [revisión local de aereus](literature/prediction/boletus_aereus_revision_bibliografica_rainmapper.md).

## Qué sostiene la literatura

**No hay una jerarquía universal «suelo > árbol > pH».** Van der Linde et al.
(2018) encuentran efectos importantes tanto del hospedador como del ambiente,
incluido el pH, sobre las comunidades ectomicorrícicas europeas. La especificidad
por hospedador sigue siendo relevante. Estudian comunidades subterráneas: sus
resultados no son porcentajes de fructificación de nuestras especies.
[Artículo y DOI](https://www.nature.com/articles/s41586-018-0189-9),
[manuscrito institucional consultado](https://www.nw-fva.de/fileadmin/nwfva/publikationen/pdf/van_der_linde_2018_environment_and_host_as.pdf).

**Un mismo árbol no implica las mismas setas.** Zotti y Pautasso (2013) siguieron
15 parcelas de encinar durante cuatro años. Los gradientes de pH y clima
ayudaron a distinguir comunidades aun compartiendo encina. Aereus aparece entre
las especies termófilas. Es evidencia directamente pertinente para cruzar suelo
y ambiente dentro de hábitats compatibles; no fija un máximo universal de pH.
[Estudio original, métodos y resultados](https://czechmycology.org/_cmo/CM65205.pdf).

**El suelo incluye más que su acidez.** El estudio experimental de micelio de
edulis/reticulatus en castañares gallegos (2023) analizó textura, agregación,
porosidad, carbono, nutrientes y clima. Sus suelos tenían pH 4,7–5,0; ese
intervalo de muestreo no demuestra los límites de tolerancia de edulis. La edad
y el manejo del castañar también acompañaban diferencias edáficas. No permite
equiparar cantidad de micelio con cantidad de setas.
[Estudio original](https://www.frontiersin.org/journals/soil-science/articles/10.3389/fsoil.2023.1159793/full).

**Fructificar depende también del tiempo y del bosque.** Sánchez-González et al.
(2019) modelaron producción anual con 90 parcelas de pinares del norte de
España, incluidas parcelas catalanas. Precipitación y estructura de la masa
resultaron relevantes. Los modelos agrupan hongos: no deben trasladarse como
coeficientes diarios de una especie. Altitud y orientación aportan contexto,
pero no sustituyen las condiciones térmicas e hídricas del lugar.
[Estudio original](https://link.springer.com/article/10.1186/s40663-019-0211-1).

## Caliza, lavado y descalcificación

La explicación del usuario tiene fundamento: el agua que percola puede disolver
y transportar carbonatos. La FAO describe horizontes superficiales parcial o
totalmente descalcificados y la disolución favorecida por agua pobre en calcio
y por el CO₂ del suelo. Puede persistir material calcáreo a mayor profundidad.
[FAO, formación de Calcisoles](https://www.fao.org/4/y1899e/y1899e09.htm).

Importan el agua que **atraviesa** el perfil, su drenaje y la evolución del suelo;
no basta contar lluvia. Los carbonatos amortiguan la acidificación mientras
permanece una reserva efectiva; agotada esta, el pH puede descender más.
No convertir la lluvia reciente del predictor en una descalcificación instantánea.
[FAO, lixiviación y amortiguación](https://www.fao.org/4/W5183E/w5183e05.htm).

Por tanto, «roca caliza + suelo superficial ácido» es una combinación posible.
Un pH **estimado** bajo solo permite plantearla como hipótesis: también puede
haber error del modelo o diferencias de profundidad y escala. No demuestra
descalcificación, ausencia de carbonatos ni una florada pequeña. La abundancia
de edulis sobre esos suelos no queda cuantificada por las fuentes consultadas.

La ficha local de edulis ya incluye `lith_decalcified_soil` como preferido en
`docker-data/mushroom-data/mushroom_profiles.json`. Esto no convierte toda unidad
ICGC calcárea en suelo descalcificado. Tampoco la ausencia de caliza en una lista
de preferencias significa que esa lista sea exhaustiva o una prohibición biológica.

## Propuesta práctica para Rainmapper

Separar **compatibilidad del lugar** de **probabilidad de fructificación en una
fecha**. Estas decisiones son una propuesta operativa derivada del contraste,
no reglas numéricas publicadas por los estudios anteriores.

**Alcance precisado por el usuario:** ahora se revisa únicamente el filtro de
especies posibles en el punto. Humedad y temperatura corresponden al predictor
existente; no añadir otro filtro meteorológico, nuevos pesos ni ajustes del
porcentaje. Conservar las ventanas actuales de altitud. La decisión posterior
separa también la época del filtro territorial: la fecha corresponde al segundo
nivel, sin eliminar la fenología de las fichas que utiliza el predictor. La discusión
bibliográfica del clima explica el contexto, no amplía esta implementación.

| Factor | Papel propuesto |
|---|---|
| Hospedador o hábitat | Requisito cuando la biología de la especie lo exige. Un hueco GIS significa desconocido; un suelo favorable no inventa el hospedador. |
| Suelo y pH | Evaluación conjunta de composición, carbonatos y reacción del horizonte relevante. Conservar la distinción entre roca cartografiada y suelo medido/estimado. |
| Altitud y orientación | Contexto regional y microclimático; revisar ventanas por especie, sin aplicar automáticamente dos penalizaciones por altitud y por temperatura correlacionadas. |
| Época y meteorología | Segundo nivel: usar el motor existente para la fecha sin ocultar una especie territorialmente compatible por el mes seleccionado. |

En las fichas, distinguir **requisito, tolerancia, preferencia, incompatibilidad
documentada y desconocido**. Mantener equivalencias en el catálogo/mappings y
reglas específicas en los perfiles locales, con fuente y carácter provisional;
sin códigos de unidades ni nombres de especies fijados en Python.

| Evidencia del punto | Tratamiento propuesto para una especie de preferencia ácida |
|---|---|
| Material silíceo y pH compatible | Apoyo conjunto; comprobar además hospedador y altitud. |
| Material calcáreo y pH básico incompatible | Exclusión respaldada por el conjunto, si la ficha tiene esa restricción. |
| Material calcáreo y pH estimado ácido | Caso condicionado: posible horizonte descalcificado. No afirmar ni imposibilidad ni descalcificación comprobada. |
| Material silíceo y pH estimado básico | Conflicto a revisar; la roca tampoco debe ganar automáticamente. |
| Suelo medido descalcificado y pH compatible | Puede satisfacer una tolerancia a descalcificados de la ficha; no habilita automáticamente otras especies. |
| Mezcla de materiales o información insuficiente | Conservar componentes y desconocimiento; no transformar la mezcla en un suelo homogéneo. |

Para empezar, devolver un motivo comprensible en los casos condicionados y
mantenerlos separados de una compatibilidad confirmada. No inventar un descuento
del porcentaje ni multiplicar el modelo actual por pesos arbitrarios. Las clases
«ácido/básico» derivadas del pH no son otra evidencia independiente del mismo pH.

La Vansa queda como caso de contraste: `PPcm` identifica componente calcáreo y
OpenLandMap estima 6,3; falta una comprobación del horizonte superficial para
resolver la hipótesis de descalcificación. Los setales conocidos aportan evidencia
de presencia, pero no una medición de acidez. Una visita sin setas tampoco acredita
ausencia de la especie. Comparar lugares con y sin producción reiterada, anotando
fecha y condiciones, permitirá revisar las reglas sin generalizar un único punto
a toda Catalunya.

No se modifican fichas, mappings, probabilidades ni la excepción experimental
actual de aereus en esta revisión. Queda pendiente decidir y aplicar la política
conjunta; no se han ejecutado runners, entrenamiento ni precálculo.

## Orden de implementación y aceptación

Plan concretado tras la petición del usuario de indicar cómo seguir. No aplicado
todavía; la comprobación de código confirma que `EcologyReader._species`, en
`rainmapper_core/mushroom_map_ecology.py`, sigue convirtiendo los estados diarios
en `out_of_season`. `resolve_species_week`, en `mushroom_map_prediction.py`, ya
transmite fase estacional y fenología al comparador del predictor.

1. Separar la elegibilidad territorial del mes. Conservar la fenología de las
   fichas para el predictor y cambiar los textos que dicen «compatibles para esta
   fecha». La lista territorial debe ser idéntica al cambiar de fecha, con iguales
   datos y fichas; pueden cambiar orden y predicciones. La falta de cálculo sigue
   siendo distinta de un cero calculado.
2. Convertir la revisión de las 21 fichas en reglas explícitas, empezando por
   aereus, edulis, pinophilus y cibarius, que tienen casos aportados por el usuario.
   No transformar listas de preferencias en listas exhaustivas automáticamente.
   Distinguir carbonatos presentes en el suelo de roca calcárea cartografiada y
   descalcificación confirmada de hipótesis basada en pH estimado. Cada cambio de
   ficha debe tener un motivo y un resultado esperado antes de aplicarlo.
3. Probar la tabla de decisiones con casos controlados y los datos persistidos
   de Olvan/Merlès, La Selva/L'Aleixar y La Vansa. Vallcebre sirve para comprobar
   que latitabundus no desaparece solo por consultar septiembre si encaja el
   territorio. Comprobar también rechazo real por altitud/suelo, falta de datos,
   mezcla geológica y conservación de especies sin modelo. No fijar como verdad
   científica una ausencia inferida únicamente de la captura o de la geología.
4. Mostrar el motivo de cada admisión condicionada o exclusión para que el
   contraste con setales permita corregir la ficha o el dato que falla. Conservar
   el porcentaje del motor y la abstención; no introducir pesos ecológicos
   arbitrarios. Documentar pruebas dirigidas sin entrenamiento ni precálculo.

**Requisito de rendimiento confirmado por el usuario:** resolver primero el
filtro territorial y calcular probabilidades únicamente para las especies que
lo superen y dispongan de modelo aplicable. Las incompatibles no deben llegar a
la inferencia; tampoco convertir la falta de información en compatibilidad.
Si no hay candidatas, salir sin preparar entradas de predicción. Las compatibles
sin modelo se conservan en la lista con probabilidad nula, nunca cero ficticio.

Comprobación actual: `mushroom_map_model_runtime.py`, método `predict`, selecciona
las candidatas mediante `daily_statuses` antes de `_refresh` y de preparar la
meteorología del modelo; retorna inmediatamente cuando la selección está vacía.
Al separar los dos niveles debe conservarse esa salida temprana y basar la
selección en compatibilidad territorial. Añadir prueba que verifique **cero
invocaciones al modelo para especies descartadas**, no solo su ausencia visual.
La consulta meteorológica del desplegable es independiente de la inferencia.
