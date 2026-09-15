# Propuesta de rangos provisionales de pH por especie

**Preparada y aplicada a las 21 fichas locales el 13/09/2026. Rangos provisionales revisables.**

Decisión posterior del usuario: aplicar todos los rangos propuestos, incluidos los
diez amplios, y revisarlos comparando con setales conocidos. Los 21 pares
`ecology.ph_min/ph_max` de `docker-data/mushroom-data/mushroom_profiles.json`
ya están informados. Esta decisión sustituye la recomendación inicial de dejar
diez rangos solo como contexto. Se conservan copia previa y procedencia por ficha.

**Fuente aplicada posteriormente:** OpenLandMap local y filtro por su media,
con SoilGrids conservado para comparar. Véase §12: sustituye la política histórica
de comparación por intervalos de §6; las 21 ventanas numéricas no cambian.
La prueba posterior de §15 admite una excepción configurable para aereus:
sustrato silíceo y solapamiento de incertidumbre, con el pH original conservado.
Revisión posterior de todas las unidades ICGC y contraste de las 21 fichas:
[sustrato y pH](prediction-map-substrate-species-review-es.md). La excepción de
aereus queda bloqueada ante mezclas con carbonatos o yeso; los rangos no cambian.

## 1. Qué significan los números

Son **ventanas operativas provisionales**, no límites de supervivencia ni rangos
universales demostrados de fructificación. Para la mayoría de especies, la evidencia
local es cualitativa. La traducción a números siguiente es una **aproximación explícita
propuesta ahora**, no un dato que ya estuviera en los artículos o aprobado anteriormente.

Todos los rangos se usan para **filtrado provisional**, manteniendo abstención
ante datos ausentes. Los diez rangos AMPLIO también filtran por
acuerdo del usuario; su menor confianza sigue registrada. Se revisarán con setales
conocidos, sin convertir un desacuerdo en prueba de ausencia de una especie.

La confianza indicada evalúa los **extremos numéricos propuestos**, no si el hongo
está bien identificado o la certeza de que fructifique en un lugar.

## 2. Método reproducible

Se contrastaron perfiles, catálogo local, revisión de cada especie y fuentes
externas concretas de suelo/cultivo. No se ha tomado la semilla del repositorio.
Para las aproximaciones se reutilizan únicamente las clases químicas explícitas
actuales del catálogo: ácido 3,5–6,5, ligeramente ácido 5,5–6,8, neutro 6,5–7,5
y básico 7,2–8,8. Los límites siguen siendo convenciones locales.

| Clase de propuesta | Ventana | Construcción |
|---|---:|---|
| A | 3,5–6,8 | Unión ácido + ligeramente ácido. |
| AN | 3,5–7,5 | Unión ácido + ligeramente ácido + neutro. |
| NB | 6,5–8,8 | Neutro + básico; margen neutro añadido deliberadamente a la preferencia por bases. |
| AMPLIO | 3,5–8,8 | Cobertura de las cuatro clases; filtro amplio provisional aceptado por el usuario. |
| TRUFA | 7,1–8,9 | Extremos de truferas naturales recogidos por CTFC, con el máximo redondeado hacia fuera. |

**No se traduce automáticamente «silíceo», «calizo», «arenoso» o «humus» a pH.**
La clase se elige por la descripción química y el contexto de las fuentes, con
las excepciones y discrepancias que se detallan por especie. No se transforman
óptimos de crecimiento micelial en agar en límites del suelo donde aparecen setas.

## 3. Tabla completa

| Especie / ficha conservada | pH mínimo | pH máximo | Clase | Confianza numérica | Uso aplicado |
|---|---:|---:|---|---|---|
| *Amanita caesarea* | 3,5 | 7,5 | AN | baja | Filtrado provisional |
| *Boletus aereus* | 3,5 | 6,8 | A | baja | Filtrado provisional |
| *Boletus edulis* | 3,5 | 7,5 | AN | baja | Filtrado provisional |
| *Boletus pinophilus* | 3,5 | 6,8 | A | baja | Filtrado provisional |
| *Calocybe gambosa* | 6,5 | 8,8 | NB | baja | Filtrado provisional |
| *Cantharellus cibarius* | 3,5 | 7,5 | AN | muy baja | Filtrado provisional |
| *Cantharellus lutescens* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Craterellus cornucopioides* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Hygrophorus latitabundus* | 6,5 | 8,8 | NB | baja | Filtrado provisional |
| *Hygrophorus marzuolus* | 3,5 | 6,8 | A | baja | Filtrado provisional |
| *Lactarius deliciosus* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Lactarius salmonicolor / quieticolor* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Lactarius sanguifluus* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Lactarius vinosus* | 3,5 | 7,5 | AN | baja | Filtrado provisional |
| *Lepista nuda* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Macrolepiota procera* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Marasmius oreades* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Morchella elata complex* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Russula virescens* | 3,5 | 6,8 | A | baja | Filtrado provisional |
| *Tricholoma terreum* | 3,5 | 8,8 | AMPLIO | muy baja | Filtrado provisional |
| *Tuber melanosporum* | 7,1 | 8,9 | TRUFA | media | Filtrado provisional |

La tabla incluye **21 filtros provisionales**, diez de ellos con ventana AMPLIO.
Sus extremos y niveles de confianza no cambian respecto a la propuesta inicial;
cambia la decisión de aplicarlos todos para poder contrastarlos en uso.
La amplitud del grupo salmonicolor/quieticolor conserva la decisión de una sola ficha.

## 4. Justificación por especie

- **Amanita caesarea** (`amanita_caesarea`): Preferencias ácida y neutra en ficha local; envolvente de ambas. No usar pH 6–7 de cultivo micelial como límite de campo. [Revisión local](literature/prediction/amanita_caesarea_revision_bibliografica_rainmapper.md).
- **Boletus aereus** (`boletus_aereus`): Preferencia ácida local. Máximo 6,8 aproximado por clase; no copiar límites de edulis. [Revisión local](literature/prediction/boletus_aereus_revision_bibliografica_rainmapper.md).
- **Boletus edulis** (`boletus_edulis`): Síntesis local: ácido a neutro. Estudios de jarales/castañares confirman contextos ácidos, no extremos de tolerancia. No reducir al intervalo de las parcelas. [Revisión local](literature/prediction/boletus_edulis_revision_bibliografica_rainmapper.md). [Mediavilla et al. (2019), Effect of forest fire prevention treatments on bacterial communities associated with productive Boletus edulis sites](https://doi.org/10.1111/1751-7915.13395) [Artificial intelligence unveils key interactions between soil properties and climate factors on Boletus edulis and B. reticulatus mycelium in chestnut orchards of different ages (2023)](https://www.frontiersin.org/journals/soil-science/articles/10.3389/fsoil.2023.1159793/full)
- **Boletus pinophilus** (`boletus_pinophilus`): Preferencia ácida. Caliza acidificada no implica pH superficial básico. No convertir el pH de una comunidad de pinar en nicho de la especie. [Revisión local](literature/prediction/boletus_pinophilus_revision_bibliografica_rainmapper.md).
- **Calocybe gambosa** (`calocybe_gambosa`): Preferencia por bases; añadir margen neutro es una decisión operativa. El pH alterado por el corro no es requisito previo. [Revisión local](literature/prediction/calocybe_gambosa_revision_bibliografica_rainmapper.md). [Natural History Museum, University of Oslo: Calocybe gambosa](https://www.nhm2.uio.no/botanisk/bot-mus/sopp/fakta/fakt-4.htm)
- **Cantharellus cibarius** (`cantharellus_cibarius_sl`): Tendencia ácida; ampliación hasta neutro por alcance s.l. e incertidumbre taxonómica. Es una decisión provisional, no tolerancia demostrada de todo el complejo. [Revisión local](literature/prediction/cantharellus_cibarius_sensu_lato_revision_bibliografica_rainmapper.md).
- **Cantharellus lutescens** (`cantharellus_lutescens`): Fuentes con contextos ácidos y pinares calcáreos. Ventana amplia provisional; humedad/musgo y hospedadores aportan contexto adicional. [Revisión local](literature/prediction/cantharellus_lutescens_revision_bibliografica_rainmapper.md).
- **Craterellus cornucopioides** (`craterellus_cornucopioides`): Fuentes divergentes ácido/neutro y básico. Ventana amplia provisional. [Revisión local](literature/prediction/craterellus_cornucopioides_revision_bibliografica_rainmapper.md).
- **Hygrophorus latitabundus** (`hygrophorus_latitabundus`): Preferencia por bases. Tramo 6,5–7,2 añadido como margen operativo, no como evidencia de producción. [Revisión local](literature/prediction/hygrophorus_latitabundus_revision_bibliografica_rainmapper.md).
- **Hygrophorus marzuolus** (`hygrophorus_marzuolus`): Preferencia ácida y suelos descarbonatados. Extremos de clases, no de experimentos de fructificación. [Revisión local](literature/prediction/hygrophorus_marzuolus_revision_bibliografica_rainmapper.md).
- **Lactarius deliciosus** (`lactarius_deliciosus`): Conflicto entre preferencias ácidas y poco ácidas/calizas; la fuente técnica de cultivo describe amplitud. No transferir modelos de Lactarius agregado. [Revisión local](literature/prediction/lactarius_deliciosus_revision_bibliografica_rainmapper.md). [Viveros ROBIN, Un huerto de setas de éxito](https://www.robinpepinieres.com/es/page/49-un-huerto-de-setas-de-exito)
- **Lactarius salmonicolor / quieticolor** (`lactarius_salmonicolor_quieticolor_group`): Unión del componente ácido de quieticolor y neutro/básico de salmonicolor de R12. Conservar una ficha y sus observaciones. [Revisión local](literature/prediction/lactarius_salmonicolor_quieticolor_revision_bibliografica_rainmapper.md).
- **Lactarius sanguifluus** (`lactarius_sanguifluus`): Marc/local favorecen bases; la fuente técnica de cultivo incluye ácido a básico. Ventana amplia por discrepancia; conservar preferencia caliza como información. [Revisión local](literature/prediction/lactarius_sanguifluus_revision_bibliografica_rainmapper.md). [Viveros ROBIN, Un huerto de setas de éxito](https://www.robinpepinieres.com/es/page/49-un-huerto-de-setas-de-exito)
- **Lactarius vinosus** (`lactarius_vinosus`): Preferencia ácida con margen neutro; tabla de Castaño registra producción a pH 6,5–7,0. No copiar la afinidad negativa contradictoria de soil_acidic. [Revisión local](literature/prediction/lactarius_vinosus_revision_bibliografica_rainmapper.md). [Castaño et al. (2016), Soil drying procedure affects the DNA quantification of Lactarius vinosus but does not change the fungal community composition](https://doi.org/10.1007/s00572-016-0714-3)
- **Lepista nuda** (`lepista_nuda`): Prioridad local: materia orgánica y humedad. Ventana amplia provisional, sin extremos biológicos demostrados. [Revisión local](literature/prediction/lepista_nuda_revision_bibliografica_rainmapper.md).
- **Macrolepiota procera** (`macrolepiota_procera`): Sin extremos comparables de campo. Cobertura; no trasladar sustratos de cultivo al suelo del punto. [Revisión local](literature/prediction/macrolepiota_procera_revision_bibliografica_rainmapper.md).
- **Marasmius oreades** (`marasmius_oreades`): El corro modifica el suelo; no deducir requisitos previos a partir de ese efecto. Ventana amplia provisional. [Revisión local](literature/prediction/marasmius_oreades_revision_bibliografica_rainmapper.md).
- **Morchella elata complex** (`morchella_elata_complex`): Complejo heterogéneo. No importar límites de esculenta o de otra especie cultivada. Ventana amplia provisional. [Revisión local](literature/prediction/morchella_elata_complex_revision_bibliografica_rainmapper.md).
- **Russula virescens** (`russula_virescens`): Preferencia ácida de la ficha europea. Números aproximados de clase, sin transferir resultados de taxones asiáticos. [Revisión local](literature/prediction/russula_virescens_revision_bibliografica_rainmapper.md).
- **Tricholoma terreum** (`tricholoma_terreum`): Preferencia caliza con presencia sobre silíceos; la roca no determina pH. Sin extremos comparables; ventana amplia provisional por decisión del usuario. [Revisión local](literature/prediction/tricholoma_terreum_revision_bibliografica_rainmapper.md).
- **Tuber melanosporum** (`tuber_melanosporum`): CTFC: 7,1–8,85 en truferas naturales; propuesta 7,1–8,9. Separado de 7,5–8,5 recomendado para cultivo. No sustituye carbonatos ni horizonte adecuado. [Revisión local](literature/prediction/tuber_melanosporum_revision_bibliografica_rainmapper.md). [Fischer, Oliach, Bonet y Colinas (2017), Best Practices for Cultivation of Truffles, CTFC](https://trumap.ctfc.cat/wp-content/uploads/2016/03/TRUMAP_Truffles_Handbook_ENG.pdf)

## 5. Evidencia numérica y sus límites

- **Edulis:** un jaral productivo de Zamora se describe con pH 5,0–5,5; eso
  respalda contexto ácido, no los extremos completos de tolerancia. [Mediavilla
  et al., 2019, métodos](https://doi.org/10.1111/1751-7915.13395).
  Otro estudio de castañares presenta pH 4,7–5,0 y estudia micelio: no equivale
  a definir cuándo fructifica. [Estudio de castañares,
  resultados](https://www.frontiersin.org/journals/soil-science/articles/10.3389/fsoil.2023.1159793/full).
  Los 3,5–7,5 propuestos son la envolvente cualitativa local, no cifras tomadas
  de esos experimentos. No se copian a pinophilus.
- **Vinosus:** la tabla 1 del estudio de Castaño contiene doce parcelas con
  pH 6,5–7,0 y producción media positiva en 2008–2014. Se conserva el margen
  neutro y no se adopta la afinidad negativa contradictoria de la ficha local.
  No se ha establecido el método de pH de esa tabla en el texto consultado.
  [Artículo](https://doi.org/10.1007/s00572-016-0714-3),
  [texto aportado por sus autores, tabla 1](https://www.researchgate.net/publication/304070496_Soil_drying_procedure_affects_the_DNA_quantification_of_Lactarius_vinosus_but_does_not_change_the_fungal_community_composition).
- **Trufa negra:** el manual CTFC diferencia el intervalo de cultivo recomendado
  7,5–8,5 del observado en truferas naturales 7,1–8,85. Se elige este último,
  ampliando el máximo por redondeo a 8,9. El propio manual indica que calcio y
  carbonatos aportan información adicional; pH adecuado no acredita producción.
  [CTFC, página impresa 15](https://trumap.ctfc.cat/wp-content/uploads/2016/03/TRUMAP_Truffles_Handbook_ENG.pdf).
- **Sanguifluus/deliciosus:** la guía de ROBIN contiene tanto preferencias
  particulares como una descripción conjunta de amplitud ácido–básico.
  Por esa discrepancia con las fuentes locales no se endurece un corte por pH.
  Es orientación técnica del productor, no una curva experimental de tolerancia.
  [Guía de cultivo](https://www.robinpepinieres.com/es/page/49-un-huerto-de-setas-de-exito).

Las fuentes externas complementan la revisión local; no sustituyen automáticamente
las fichas. No se ha realizado una nueva revisión exhaustiva de toda la bibliografía.

## 6. Comparación con SoilGrids y caso de Merlès

Regla histórica del filtro SoilGrids, sustituida en la preview por §12:

1. Intervalo cartografiado contenido en la ventana: compatible **en pH**, todavía
   sujeto a hospedadores, altitud, época y demás evidencia.
2. Intervalos disjuntos: fuera de la ventana provisional; no prueba de ausencia biológica.
3. Solapamiento parcial: desconocido, sin asignar una probabilidad inventada.
4. Dato ausente o no comparable: desconocido. No sustituir por cero.

La capa 0–5 cm es la convención actual de consulta del mapa. No equivale al
horizonte de raíces o fructificación de todas las especies, especialmente trufa.
Las fuentes sin profundidad/método comparable conservan esa limitación. No hay
una conversión fija entre pH en agua y pH en KCl/CaCl₂. No combinar profundidades
promediándolas sin una decisión posterior.

En Santa Maria de Merlès (`42.01347,1.97050`), la consulta reproducida devuelve
mediana 7,6 e intervalo 5,0–8,3 a 0–5 cm:

| Especie | Ventana propuesta | Comparación con 5,0–8,3 | Comportamiento del filtro actual |
|---|---|---|---|
| Edulis | 3,5–7,5 | Solapamiento parcial | `unknown / ph_overlap`; fuera de la lista de compatibles. |
| Pinophilus | 3,5–6,8 | Solapamiento parcial | `unknown / ph_overlap`; fuera de la lista de compatibles. |

Ese resultado se comprobó primero en copia temporal y, tras la aplicación, se
reprodujo con las fichas operativas actualizadas y la instantánea geográfica ya
capturada. No se repitió la descarga ni una auditoría GIS. Ambos quedan fuera de
la lista de compatibles por incertidumbre; no demuestra ausencia física.
El problema separado de Quercus demasiado genérico y los 600 m sigue pendiente;
no se ajustaron los rangos de pH solo para hacer desaparecer este ejemplo.

## 7. Aplicación, validación y revisión con setales

- [Registro de aplicación local](../reports/prediction-map-species-ph-application-2026-09-13.json):
  los 21 cambios antes/después, huellas, backup y reproducción de Merlès.
- [JSON de propuesta original](../reports/prediction-map-species-ph-proposal-2026-09-13.json):
  snapshot previo, conservado sin reescribir sus recomendaciones originales.
  Su estado `proposal_not_applied` describe aquel momento; la decisión vigente
  y la aplicación están en el registro posterior. No es importable como perfiles.
- Copia previa: `docker-data/mushroom-data/backups/mushroom_profiles.20260913T170720493827Z.keep.json`.
- Los datos operativos solo cambian en pH y metadatos de procedencia.
  Catálogo, mappings y observaciones conservaron sus huellas al aplicar; hospedadores, altitudes,
  meses y parámetros del motor conservan sus valores.
- Validación del conjunto local: cero errores; los mismos 89 avisos previos.
  `EcologyReader` carga las 21 fichas y reproduce Merlès con ambos boletos en
  `unknown / ph_overlap`. Se conserva la abstención existente.
- 33 pruebas dirigidas de ecología y validación de datos: correctas. Consulta
  nueva a la API de la preview: ambos boletos `unknown / ph_overlap`, sin reinicio.
- Después se detectaron ediciones concurrentes de mayúsculas en nombres comunes
  de dos hospedadores del catálogo; se conservaron y se registraron separadamente.
- No runners, entrenamiento, precálculo, publicación HA ni nuevas descargas.
  Las cifras permanecen editables en las fichas, sin listas por especie en Python.

Para revisar un setal, anotar punto, especie y presencia conocida, fecha cuando
esté disponible, pH cartografiado y motivo del filtro. Antes de ajustar un rango,
comprobar si la discrepancia procede del pH, del hospedador, de la altitud o de la
época. Registrar cada ajuste en la ficha y su procedencia; no modificar observaciones
para hacer encajar el resultado. No hace falta resolver toda esa validación antes
de continuar con Rovelló y el motor compartido.

## 8. Primer contraste con setal conocido: Merlès

El usuario comunica presencia abundante de **aereus** y presencia de **caesarea**.
Consulta nueva en `42.01347,1.97098`: 620,8 m; SoilGrids superficial mediana 7,6,
intervalo **5,1–8,3**. Las dos especies pasan hospedadores, altitud y fecha, pero
quedan `unknown / ph_overlap`; la UI solo lista compatibles y las oculta.
Eso hace que la incertidumbre se perciba como una exclusión. El resultado anterior
que ocultaba edulis/pinophilus no validaba por sí solo la calidad ecológica del filtro.

La captura de Sporas muestra 7,1 y 605 m, sin coordenadas exactas, fuente ni
profundidad de pH comprobables. El 7,1 está dentro de nuestro intervalo; no demuestra
que una cartografía sea más precisa. Tampoco basta sustituir 7,6 por 7,1: el máximo
provisional de aereus es 6,8. Aereus/pinophilus comparten ventana y caesarea/edulis
también: el pH por sí solo no puede separar estas parejas con las fichas actuales.

ISRIC describe estimaciones a 250 m, mediana e intervalo de predicción del 90 %.
El lector divide los enteros por diez, conforme a las unidades documentadas.
No se ha demostrado un error de escala; tampoco se ha medido el suelo del setal.
[Documentación oficial de SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).

**Siguiente ajuste propuesto, todavía sin implementar:** conservar los 21 rangos
editables y la abstención, hacer visible el intervalo de pH y mostrar por separado
las especies pendientes únicamente por incertidumbre de pH, sin presentarlas como
compatibilidad confirmada ni saltarse hospedadores, altitud o época. No retocar los
rangos para resolver solo este ejemplo. La presencia aportada queda documentada
como contraste, sin crear ni modificar registros de observaciones.

[Diagnóstico reproducido](../reports/prediction-map-merles-ph-reliability-2026-09-13.json).

### Contraste adicional: Olvan y lectura directa del raster

El usuario señala que 5,1–8,3 es demasiado amplio y confirma aereus y ou de reig
también en Olvan. Se comprobaron tres celdas distintas del GeoTIFF local, incluida
la coincidencia entre coordenadas transformadas, geotransform del archivo y offsets
del índice: Merlès 7,6 [5,1–8,3], Olvan (`42.06220,1.93614`) 7,6 [5,3–8,3],
La Pera (`42.0641,1.9387`, coordenadas visibles en Sporas) 7,7 [5,3–8,4].
Los valores coinciden con las consultas nuevas de preview. En estos tres puntos
no se detecta valor fijo, caché cruzada ni desplazamiento entre índice y GeoTIFF.
Esto verifica la lectura local, no la exactitud del modelo frente al suelo real.

El intervalo amplio no respalda una exclusión precisa a escala del setal. Exigir
su contención completa dentro de una ventana provisional y ocultar después el
estado desconocido produce omisiones de especies que el usuario conoce presentes.
Queda pendiente corregir ese uso de la incertidumbre; no se han ampliado rangos
ni sustituido el dato local por el de Sporas. El pH completo de la nueva captura
de Sporas queda recortado: no se inventa su decimal ni su fuente.

## 9. Alternativas de pH: prioridad España peninsular

El usuario precisa el alcance: **España, priorizando la Península**. Las islas
son menos importantes y no deben bloquear una mejora; no limitarla a Cataluña.

SoilGrids ofrece mediana, media y cuantiles 5/95 por profundidad. El 7,6 mostrado
es la mediana; 5,1–8,3 expresa incertidumbre. La media es otra estimación puntual,
no una medición más precisa garantizada. [Documentación ISRIC](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).

Se localizaron los COG públicos de **OpenLandMap-soildb** y se consultaron tres
píxeles por HTTP, sin descargar mapas completos. Producto 2020–2022, pH en agua,
**0–30 cm**, media a 30 m; cuantiles 16/84 a 120 m. El catálogo describe método
suelo:agua 1:1. [Proyecto](https://github.com/openlandmap/soildb),
[catálogo de archivos](https://github.com/openlandmap/soildb/blob/main/tables/OpenLandMap_soildb_COGS.csv).

| Punto | SoilGrids mediana 0–5 cm | OpenLandMap media 0–30 cm | OpenLandMap intervalo 68 %, a 120 m |
|---|---:|---:|---:|
| Merlès 42.01347, 1.97098 | 7,6 | 6,7 | 5,6–7,9 |
| Olvan 42.06220, 1.93614 | 7,6 | 6,6 | 5,7–7,6 |
| La Pera 42.0641, 1.9387 | 7,7 | 6,4 | 5,5–7,6 |

Las estimaciones centrales son más ácidas y encajan mejor con el contexto que
el usuario comunica. No equivalen a validación mediante pH medido. Mayor detalle
espacial no garantiza mayor exactitud; las profundidades son distintas y no se
puede comparar directamente un intervalo del 68 % con otro del 90 %. Sigue
habiendo incertidumbre y, con la regla actual, estos intervalos también dejarían
las especies indicadas como desconocidas. Sustituir la fuente por sí solo no
resuelve que la UI las oculte.

**ESDAC/LUCAS** ofrece otra cartografía europea de pH H2O/CaCl2 a **500 m**,
a partir de muestras 2009/2012. Puede servir de contraste, pero no mejora la
resolución espacial. Su portal exige solicitud/registro; no se ha enviado ninguna.
[Producto oficial](https://esdac.jrc.ec.europa.eu/content/chemical-properties-european-scale-based-lucas-topsoil-data).

En esta fase histórica OpenLandMap quedó como candidata. **Descarga e integración
completadas posteriormente**, según §12.
Pendiente comprobar cobertura peninsular efectiva, comparar horizontes/estadísticos
adecuados y contrastar más puntos. Las pruebas de tres setales no acreditan
superioridad nacional ni identifican la fuente que utiliza Sporas.
[Lecturas y metadatos verificables](../reports/prediction-map-ph-alternatives-spain-2026-09-13.json).

### Valores de Sporas comunicados posteriormente por el usuario

El usuario concreta **Olvan 6,6 y Merlès 7,1**. OpenLandMap coincide con el
valor comunicado de Olvan (diferencia 0,0 frente a 1,0 con SoilGrids). En Merlès,
la diferencia baja de 0,5 a 0,4. La mejora de concordancia es especialmente clara
en Olvan; conservar esa distinción al valorar ambos casos. Son valores comunicados
por el usuario, sin consulta independiente a la API de Sporas ni comprobación de
que sus coordenadas exactas coincidan con las nuestras. La coincidencia no acredita
que Sporas utilice OpenLandMap ni sustituye una medición del suelo.

## 10. ¿Puede OpenLandMap sustituir todo lo leído de SoilGrids?

El usuario prefiere reducir el número de fuentes. Se compara el catálogo publicado
con las lecturas actuales, sin autorizar ni ejecutar una migración general.

El producto **OpenLandMap-soildb a 30 m** no contiene solo pH: publica fracciones
de arena/limo/arcilla, densidad aparente, contenido/densidad de carbono orgánico y
clasificaciones de suelo. El CSV inspeccionado incluye ocho propiedades y **no
incluye retención de agua**. [Catálogo](https://github.com/openlandmap/soildb/blob/main/tables/OpenLandMap_soildb_COGS.csv).

Nuestras lecturas de SoilGrids comprenden pH en tres horizontes y retención a
**10, 33 y 1500 kPa**, seis horizontes hasta 200 cm y tres cuantiles: nueve capas
pH y 54 de retención. Fuentes actuales: `mushroom_map_terrain.py:17` y
`mushroom_soilgrids.py:49`. No confundir textura o carbono disponibles en un
catálogo con variables que el lector actual ya esté consumiendo.

OpenLandMap también documenta un producto anterior de agua a **33/1500 kPa y
250 m**, para profundidades puntuales 0/10/30/60/100/200 cm. No se ha encontrado
en esa lista el equivalente a 10 kPa ni comprobado un contrato igual de cuantiles.
Profundidades puntuales no equivalen directamente a nuestros intervalos.
[Documentación del producto anterior](https://docs.openlandmap.org/016-project.html#openlandmap-long-term-soil-water-content).

Conclusión: permite evaluar el reemplazo del pH, pero **no es sustituto completo
directo** del conjunto leído. Unificar el proveedor con la colección antigua aún
mezclaría productos/resoluciones. Propuesta práctica: mantener la retención local
existente y evaluar únicamente el pH nuevo. Unificación total exigiría revisar
por separado entradas, incertidumbre y cálculo hídrico. No se ha cambiado la
fuente operativa, derivado retención con fórmulas nuevas ni repetido descargas.

## 11. Estimación de almacenamiento local del pH peninsular

Cabeceras GeoTIFF comprobadas: una banda Byte (un byte por píxel), media nominal
30 m y dos cuantiles nominales 120 m. Periodo 2020–2022, horizonte 0–30 cm.
Rectángulo conservador `[-9.6,35.9,3.4,43.9]`: incluye Portugal y mar; no es una
máscara exacta del territorio español. No se han descargado los rasters completos.

| Capas | Tamaño de píxeles sin compresión, GB decimales |
|---|---:|
| pH medio a 30 m | 1,664 |
| Dos límites de incertidumbre a 120 m | 0,208 |
| Total | **1,872** |

Con pirámides de visualización sucesivas a mitad de resolución, la estimación
sube aproximadamente a **2,50 GB** antes de compresión. **Reservar unos 3 GB**
es una previsión de trabajo prudente para este conjunto; no es el tamaño medido
de una descarga. El tamaño comprimido final no se ha medido. No se necesita
almacenar el archivo mundial, cuya media de pH a 30 m pesa 60,58 GB según HEAD.
Esta cifra local corresponde solo al pH superficial y su incertidumbre, no a
todas las variables ni periodos de OpenLandMap.
[Cabeceras y cálculo](../reports/prediction-map-openlandmap-ph-sizing-2026-09-13.json).

### Ampliación del cálculo a toda España

Para Península, Baleares, Canarias, Ceuta, Melilla y territorios españoles del
norte de África se estiman tres recortes rectangulares separados, evitando el
gran rectángulo único que incluiría todo el mar hasta Canarias. Con las mismas
rejillas verificadas: **2,251 GB sin compresión**, aproximadamente **3,001 GB**
con pirámides; reserva de planificación **4 GB**. Incluye márgenes, zonas de mar
y territorio vecino; no es una máscara exacta. El tamaño comprimido final sigue
sin medirse. Mismo alcance: pH 0–30 cm, un periodo y dos límites de incertidumbre.

## 12. Aplicación local OpenLandMap y comparación visible (13/09/2026)

El usuario autoriza descarga, comparación con SoilGrids y selección por la media
OpenLandMap. Nueve GeoTIFF completados: **376.526.984 bytes (368 MiB)** en
`mushroom-map-GIS/openlandmap-ph/spain-v20250204/`, con manifiesto y adquisición
verificable. Incluyen recortes de península/Baleares, Canarias y territorios
norteafricanos; los rectángulos tienen margen y no son máscaras de frontera.

La preview usa **media 0–30 cm a 30 m** para compararla con los límites inclusivos
de cada ficha. El Q16–Q84 (68 %) a 120 m es informativo y no amplía ni veta esa
comparación. Media ausente implica desconocido. No se usa SoilGrids automáticamente
cuando falta OpenLandMap; SoilGrids se conserva para comparación y retención hídrica.

Si falta la media en el punto, se busca el píxel válido más cercano hasta **1 km**,
configurable mediante `nearest_max_distance_m` en el manifiesto. Se muestra su
distancia; los límites se consultan en esa misma ubicación, sin búsquedas independientes.
Si no hay píxel dentro del radio, se mantiene dato ausente. No se ha demostrado
cobertura completa de píxeles válidos: se comprobaron nueve ubicaciones españolas.

La cabecera muestra «pH estimado», sin profundidad. Terreno muestra media y dos
límites OpenLandMap, mediana y límites SoilGrids, profundidades y significado de
incertidumbre. Los límites no son extremos medidos en el suelo del setal.

| Punto verificado en API local | OpenLandMap estimado | Inferior | Superior | SoilGrids 0–5 cm mediana |
|---|---:|---:|---:|---:|
| Merlès 42.01347, 1.97098 | 6,7 | 5,6 | 7,9 | 7,6 |
| Olvan 42.06220, 1.93614 | 6,6 | 5,7 | 7,6 | 7,6 |

Aereus y caesarea vuelven a ser compatibles en ambos puntos. Edulis y pinophilus
también pasan con las fichas actuales; su hospedador Quercus genérico y mínimo
altitudinal siguen siendo una revisión independiente pendiente. No se han cambiado
rangos para ajustar estos resultados. Coincidir con Sporas no demuestra exactitud.

39 pruebas de ecología/consultas/contrato, 21 de lectores GDAL y comprobación de
navegador correctas; API de preview verificada. Sin runners ni despliegue HA.
[Registro de implementación y huellas](../reports/prediction-map-openlandmap-ph-implementation-2026-09-13.json).

Comprobación de la captura posterior: Olvan `42.06246,1.93612` devuelve **6,7**
OpenLandMap y **7,6** SoilGrids. No es exactamente el punto 6,6 de la tabla.
La API usa la media OpenLandMap y el JS servido coincide con el actualizado,
con `Cache-Control: no-store`. Una pestaña abierta conserva su JS cargado hasta
recargar la página; si aún muestra «pH · 0–5 cm», corresponde a la cabecera anterior.

El usuario confirma después de recargar que ya funciona: cabecera y desplegable
actualizados. No fue necesario modificar datos ni reglas por esta incidencia.

## 13. Contraste en setales de La Selva del Camp: aereus, 13/09/2026

Dos puntos con presencia abundante comunicada por el usuario, 41.22694/1.09095
y 41.23675/1.13555, quedan excluidos solo por media OpenLandMap 7,2 y 7,5 frente
al máximo provisional 6,8. Hosts, altitud y septiembre encajan. El usuario
rechaza ampliar ese máximo globalmente a 7,5; el límite se conserva.

En ambos puntos, la cartografía ICGC identifica la misma unidad `mc_Capg`,
pizarras, traducida por mapping revisado a sustrato silíceo. Es preferencia
primaria de la ficha y produce `soil_preference_match`; la regla actual no
permite que esa preferencia supere la exclusión por pH. Los intervalos
OpenLandMap 6,7–7,8 y 6,6–8,1 sí solapan el extremo de la ventana de la ficha.

Es una discrepancia para revisar la combinación de evidencias, no una medición
de suelo ácido ni una justificación de elevar el límite general. El pH depende
de varios factores, además del material parental ([USDA NRCS](https://www.nrcs.usda.gov/sites/default/files/2022-10/Soil%20PH.pdf)).
Propuesta todavía no implementada: valorar compatibilidad condicionada cuando
encajen hospedadores, sustrato y solapamiento de incertidumbre, conservando el
pH original. Ninguna regla «silíceo siempre anula pH» ha sido aprobada.
[Registro de comprobaciones](../reports/prediction-map-selva-aereus-substrate-2026-09-13.json).

## 14. Propuesta de filtro conjunto de sustrato y pH

Petición del usuario, 13/09/2026: estudiar la conversión del GIS a categorías
ácido, silíceo, calizo, básico y neutro para combinarlas con el pH. **Propuesta de
diseño; no aplicada al código ni a las fichas.** Su fiabilidad deberá contrastarse
con setales conocidos; combinar capas no garantiza por sí solo una mejora.

Comprobación de los archivos locales actuales:

- `mushroom_reference_catalogs.json`, `catalogs.soil_types`, ya contiene las cinco
  categorías, además de otras de textura, humedad y drenaje. Incluye rangos
  orientativos incluso para `soil_siliceous` (4,0–6,8) y `soil_calcareous`
  (7,2–8,8). No deben interpretarse como mediciones ni límites universales.
- `mushroom_gis_mappings.json` conserva equivalencias generales por texto y
  mappings exactos revisados. No confundirlos: para `mc_Capg`, el mapping exacto
  aceptado identifica pizarra y `soil_siliceous`, con confianza media; no acredita
  por sí mismo `soil_acidic`.
- `mushroom_profiles.json` atribuye a aereus preferencias primarias silícea y
  ácida. El filtro actual registra coincidencias de suelo, pero no excluye por
  su ausencia ni permite que anulen `ph_outside`.
- La [revisión bibliográfica de aereus](literature/prediction/boletus_aereus_revision_bibliografica_rainmapper.md),
  §4.5, recomienda aptitud flexible y calibrable, sin reglas universales de pH o
  litología. El [informe local de Sporas](literature/sporas_especies_informe_rainmapper.md),
  §3.7, recoge «Ácido o silíceo». El máximo 6,8 de esta propuesta procede de una
  aproximación por clase, no de un límite experimental de la especie.

Diseño propuesto:

1. Conservar todas las etiquetas dentro de **Terreno**, distinguiendo internamente
   composición del sustrato (silíceo, calizo, mixto u otros) y reacción química
   (ácido, neutro, básico). Esta última procede del pH o de una descripción
   edafológica explícita; una tendencia deducida de roca conserva ese carácter.
   No contar la etiqueta química derivada del pH como una segunda evidencia.
2. Reutilizar los mappings exactos revisados por fuente, edición y código. Las
   mezclas conservan todos sus componentes respaldados y su procedencia; una
   unidad mixta no confirma qué componente ocupa exactamente el setal. No forzar
   arenas, depósitos aluviales o materiales desconocidos a una de las cinco clases.
3. Expresar en cada ficha qué categorías acepta, cuáles son solo preferencias y
   cuáles constituyen incompatibilidad revisada. No convertir automáticamente las
   afinidades existentes en listas exhaustivas ni en prohibiciones.
4. Evaluar conjuntamente: coincidencia de sustrato y pH refuerza compatibilidad;
   incompatibilidad explícita y respaldada puede filtrar aunque el pH encaje;
   sustrato favorable con pH estimado discrepante requiere una regla de conflicto
   por ficha. Para aereus se propone estudiar admisión condicionada por sustrato,
   conservando el pH original, sin ampliar globalmente a 7,5. El papel exacto de
   los límites de incertidumbre sigue pendiente de concretar.
5. Falta de mapping no equivale a suelo incompatible. Conservar abstención donde
   falte evidencia requerida, y mantener hospedadores, altitud y época. Registrar
   el motivo de admisión, exclusión o conflicto, sin inventar probabilidades.

Catálogo para categorías y semántica; mappings para equivalencias del GIS; fichas
para requisitos y política de combinación. Todo editable en los JSON locales,
sin excepciones por especie o coordenada escritas en Python. Antes de activar el
filtro, revisar las reglas generales que equiparan silíceo con ácido o calizo con
básico y el uso de los rangos orientativos del catálogo, preservando backups.
Validación dirigida prevista: los dos setales de La Selva, un caso con sustrato
explícitamente incompatible, una mezcla y un punto sin mapping. No requiere
descargas, entrenamiento ni precálculo.

## 15. Prueba local del filtro combinado

Activada tras «pues lo probamos», documentada el 14/09/2026. Sustituye el estado
pendiente de §13–14 para este ensayo. Motor genérico compartido en
`rainmapper_core/mushroom_map_ecology.py`, inicialmente `broad_species_windows_v3`;
revisión vigente `broad_species_windows_v4` con la cautela de mezclas descrita debajo.
Solo **aereus** tiene activada la nueva configuración local:

```json
"soil_filter": {
  "accepted_soil_ids": ["soil_siliceous"],
  "ph_override_blocked_soil_ids": ["soil_calcareous", "soil_gypsiferous"],
  "excluded_soil_ids": [],
  "ph_conflict": "estimated_interval_overlap",
  "review_ref": "docs/mushrooms/prediction-map-species-ph-proposal-es.md#15-prueba-local-del-filtro-combinado"
}
```

Este bloque opcional vive en `ecology` de la ficha local. IDs validados contra
el catálogo; referencia de revisión obligatoria. No hay especies ni coordenadas
especiales en Python. Sin bloque, el comportamiento anterior se conserva.

- `accepted_soil_ids`: suelos que pueden respaldar la admisión frente a un pH
  estimado discrepante. No es una lista exhaustiva de suelos donde puede vivir.
- `ph_override_blocked_soil_ids`: componentes que impiden esa excepción cuando
  el pH queda fuera. En aereus son carbonatos y yeso, para no seleccionar solo
  la fracción silícea de una mezcla. No excluyen cuando la media sí encaja.
- `excluded_soil_ids`: exclusiones expresas. Solo una coincidencia con un ID
  excluido produce descarte; una mezcla de aceptados y excluidos produce
  desconocido. **La lista está vacía en aereus:** no se ha convertido su
  preferencia contra caliza en una prohibición universal.
- `ph_conflict`: `strict` mantiene el filtro anterior; `estimated_interval_overlap`
  permite aereus cuando hay suelo aceptado en un mapping exacto revisado, ningún
  suelo excluido ni bloqueador de la excepción, media válida de OpenLandMap y un intervalo válido que contiene
  esa media y solapa la ventana de la ficha. No se aplica a SoilGrids, a valores
  ausentes, intervalos inválidos o completamente disjuntos. El pH no se sustituye.
- Mapping ausente o suelo no listado no equivale a incompatible: continúa el
  control normal de pH. Los controles de hospedadores, altitud y época siguen
  siendo obligatorios; el soporte del sustrato no los compensa.

La UI muestra «Admitida por sustrato compatible; pH estimado discrepante» en la
especie admitida así. El detalle conserva pH medio, límites, fuentes y materiales.
El ensayo inicial no cambió mappings. La revisión posterior ICGC amplía las
equivalencias de materiales, sin inferir acidez ni modificar rangos de pH.
Las otras 20 fichas conservan sus filtros; ampliar esta política a
ellas o añadir exclusiones requiere revisar sus requisitos respectivos.

Validación para fecha seleccionada **13/09/2026**, con las fuentes locales y el
motor ya existente, sin entrenamiento ni precálculo:

| Punto | Media e intervalo OpenLandMap | Aereus antes → ahora | Probabilidad del motor, primer día |
|---|---|---|---:|
| 41.22694, 1.09095 | 7,2; 6,7–7,8 | Incompatible → compatible por sustrato | 48,8947 % |
| 41.23675, 1.13555 | 7,5; 6,6–8,1 | Incompatible → compatible por sustrato | 44,8780 % |

Comprobadas las respuestas de la API de la preview y sus contratos. Chrome
confirma en el segundo punto aereus con porcentaje, aviso y pH 7,5 conservado.
Pruebas dirigidas: 26 de ecología (incluyen exclusión configurable, mezcla,
ausencia de mapping, intervalo disjunto, requisitos restantes y recarga inválida),
12 de contrato, 7 de predicción compartida y 14 del validador de datos.
Las exclusiones se prueban con fichas sintéticas; no se han añadido vetos a las
especies reales. Comparación contra backup: solo cambia aereus, y ninguna otra
fila ecológica cambia en los dos puntos.

Backup preservado:
`docker-data/mushroom-data/backups/mushroom_profiles.20260913T201813685161Z.soil-filter.keep.json`.
Para desactivar únicamente el ensayo se puede quitar `ecology.soil_filter` de
aereus o poner `ph_conflict: "strict"`; no restaurar toda la copia si después
hay otras ediciones del usuario.
[Evidencia y huellas](../reports/prediction-map-soil-filter-trial-2026-09-14.json).

### Contraste adicional: unidad Ggd en L'Aleixar

En 41.22071, 1.07009 hay pino carrasco, encina y quejigo; pH 6,9 con intervalo
6,0–7,7. Aereus seguía fuera porque `Ggd` no tenía equivalencia exacta revisada.
Completada en `gis-mapping-reviews/icgc-ggd-2026-09-14.json`: «Granodiorites i
granits alcalins» se representa con la categoría amplia existente de sustrato
silíceo y tendencia `soil_siliceous`. Es una clasificación operativa del material,
no una medición de acidez. Referencia mineralógica: [clasificación USGS](https://apps.usgs.gov/thesaurus/thesaurus-full.php?thcode=4).
Se conserva la descripción original de ambos componentes y el informe previo.

Tras recarga automática del JSON local, API de preview confirma aereus compatible
por sustrato y probabilidad 47,2049 % para 14/09/2026. En el punto anterior
41.22012, 1.06989 sigue faltando identificación de hospedadores y se mantiene
abstención. No se ha implementado préstamo de árboles vecinos.
[Comprobación de ambos puntos y backup](../reports/prediction-map-ggd-mapping-2026-09-14.json).
