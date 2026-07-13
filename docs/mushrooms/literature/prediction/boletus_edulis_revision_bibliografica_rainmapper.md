# Predicción de floradas de *Boletus edulis*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Boletus edulis* Bull.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Boletus edulis* y aporta evidencia útil para explicar o predecir su fructificación.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

*Boletus edulis* es una de las especies de hongos silvestres comestibles mejor estudiadas desde el punto de vista de productividad, fenología y gestión forestal. Aun así, la literatura no permite formular una regla universal basada en una cantidad concreta de lluvia, una temperatura óptima única o un número fijo de días entre un episodio meteorológico y la aparición de cuerpos fructíferos.

Los estudios específicos revisados permiten sostener las siguientes conclusiones:

1. **La precipitación durante la estación de fructificación es un factor importante.** En un pinar de *Pinus sylvestris* de Soria, la precipitación otoñal se correlacionó positivamente con la producción de *B. edulis*. En esa misma investigación no se detectó un efecto significativo de la temperatura media sobre la producción.

2. **La importancia de cada variable cambia entre lugares y escalas temporales.** Otros estudios de series largas encontraron que la producción de *B. edulis* se explica mejor combinando precipitación, temperatura mínima, humedad del suelo y productividad primaria del bosque. Esto impide trasladar directamente una relación obtenida en un bosque a todos los demás.

3. **La humedad del suelo es una variable relevante, pero no puede afirmarse que sea siempre superior a la precipitación.** En algunos modelos específicos de *B. edulis* aparece entre las variables más informativas; en otros, la precipitación estacional explica mejor la producción. Rainmapper debería conservar ambas y permitir que la calibración determine su importancia regional.

4. **El estado fisiológico del bosque influye en la producción.** Una serie de más de veinte años mostró que la productividad primaria del año anterior, estimada mediante NDVI, contribuyó a explicar las cosechas de *B. edulis*. La meteorología inmediatamente anterior no es, por tanto, la única fuente de variabilidad.

5. **La estructura del rodal es un predictor demostrado.** Un modelo específico en pinares de *Pinus sylvestris* identificó el área basimétrica como un factor fuerte de la producción. Esto demuestra que el bosque no debe tratarse solo como una máscara binaria de presencia del hospedador.

6. **Las cortas forestales intensas pueden reducir fuertemente el micelio del suelo y la producción.** En cambio, la recolección intensiva de carpóforos no mostró un efecto significativo sobre la biomasa micelial en el estudio revisado.

7. **La sequía puede modificar tanto la productividad como la fenología.** Una serie prolongada en pinares españoles relacionó cambios en *B. edulis* con la disminución de la precipitación entre julio y septiembre.

8. **Los extremos térmicos pueden interactuar con la gestión forestal.** En un estudio italiano, incrementos bruscos de temperatura máxima parecieron inhibir la producción en parcelas sin aclarar o moderadamente aclaradas, mientras que la respuesta fue distinta en parcelas con aclareo intenso. No debe interpretarse este resultado como una temperatura crítica universal.

9. **La presencia del micelio no garantiza una florada.** La cantidad de micelio en otoño se correlacionó con la producción de carpóforos en un estudio, pero la relación varió entre años y condiciones.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hospedador y tipo de bosque | Filtro ecológico | Alta |
| Precipitación de la estación de fructificación | Señal hídrica principal | Alta |
| Humedad del suelo | Estado hídrico complementario | Media-alta |
| Temperatura, especialmente extremos y mínimas | Modulador climático | Media-alta |
| Día del año y fenología regional | Modulador temporal | Alta |
| Estructura del rodal | Modulador de productividad | Alta |
| Estado previo de la vegetación | Potencial de campaña | Media-alta |
| Gestión y perturbaciones recientes | Corrección de aptitud | Alta |
| Historial local de observaciones | Calibración principal | Muy alta |

**Conclusión práctica:** Rainmapper puede construir para *B. edulis* un modelo mejor fundamentado que para muchas otras especies. Debe combinar hábitat, estructura forestal, precipitación, humedad del suelo, temperatura y estado previo de la vegetación. Los umbrales y retardos numéricos deben calibrarse regionalmente y no copiarse de un único estudio.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Boletus edulis*?

Se revisó literatura más amplia que la finalmente citada. Se descartaron:

- estudios de productividad total de hongos sin resultados separados para *B. edulis*;
- trabajos sobre el complejo *B. edulis* cuando no podía saberse qué especie se había medido;
- publicaciones de composición química, contaminación o valor nutricional;
- referencias secundarias sin acceso a resultados verificables;
- afirmaciones divulgativas sobre cantidades de lluvia, fases lunares o días hasta fructificación;
- modelos generales cuya especie objetivo no era *B. edulis*.

Se seleccionaron **ocho trabajos principales**, todos con resultados específicos para *B. edulis* o con una variable de respuesta expresamente separada para esta especie.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Precipitación otoñal y producción

Parladé et al. siguieron entre 2011 y 2015 la producción de carpóforos y la biomasa de micelio extrarradical de *B. edulis* en un pinar de *Pinus sylvestris* de Soria.

El resultado meteorológico más claro fue:

- la precipitación media de otoño, de septiembre a noviembre, se correlacionó positivamente con la producción de carpóforos;
- no se detectaron efectos significativos de la precipitación media del verano, primavera o invierno anteriores;
- no se detectó un efecto significativo de la temperatura media sobre la fructificación en ese estudio.

Esta evidencia es fuerte dentro del área y periodo analizados, pero no debe interpretarse como demostración de que solo la lluvia otoñal importa en todos los hábitats.

**Conclusión útil:** Rainmapper debe incluir la precipitación durante la estación efectiva de fructificación. Las ventanas deberán adaptarse a la región y no definirse únicamente por estaciones calendáricas.

## 2.2. Humedad del suelo, precipitación y productividad primaria

Olano et al. utilizaron dos de las series de producción fúngica más largas disponibles en pinares mediterráneos, de 22 y 24 años. Modelaron por separado la producción de *B. edulis* en el bosque húmedo.

Los modelos más informativos para la especie incluyeron variables climáticas y de teledetección:

- precipitación;
- temperatura mínima;
- humedad del suelo;
- diferencia estacional del NDVI del año anterior.

El resultado más relevante no es que una única variable dominara siempre, sino que la producción respondió a una combinación del clima del año de fructificación y de la productividad primaria previa del bosque.

El estudio documentó además una elevada variabilidad interanual. Esto confirma que campañas meteorológicamente parecidas pueden producir resultados diferentes.

**Conclusión útil:** Rainmapper debería separar dos componentes:

- condiciones recientes que permiten la fructificación;
- potencial de producción acumulado por el bosque durante meses anteriores.

## 2.3. Sequía y cambios fenológicos

Büntgen et al. analizaron series prolongadas de producción en España. Para *B. edulis* y *Lactarius* spp., los cambios en fenología y productividad se asociaron con una disminución de la precipitación entre julio y septiembre.

El artículo estudia tendencias temporales, no una regla para predecir cada episodio de fructificación. Su valor principal es demostrar que la sequía estival y de comienzos de otoño puede alterar tanto la cantidad producida como el calendario.

**Conclusión útil:** no basta con medir lluvia inmediatamente antes de una observación. El déficit hídrico acumulado durante el verano puede modificar el potencial y el momento de la campaña.

## 2.4. Variabilidad climática local y regional

García-Bustamante et al. estudiaron específicamente *B. edulis* en pinares de *Pinus sylvestris* de Soria y analizaron la relación entre productividad y variabilidad climática local y regional.

El trabajo demuestra que la señal climática relevante puede depender de la escala espacial y que los patrones atmosféricos regionales condicionan las variables locales que finalmente experimenta el bosque.

Para Rainmapper, esta conclusión implica que una estación meteorológica aislada puede no representar correctamente:

- altitud;
- exposición;
- gradientes de precipitación;
- inversión térmica;
- microclima del rodal.

**Conclusión útil:** el modelo debe usar datos espacializados y, cuando sea posible, corregidos por topografía y cobertura.

## 2.5. Estructura del rodal

Martínez-Peña et al. desarrollaron un modelo específico de producción para *B. edulis* en bosques de *Pinus sylvestris*. El área basimétrica del rodal fue un factor fuerte de la producción.

Este resultado es importante porque demuestra que “hay pinos” no es una descripción suficiente del hábitat. La densidad y estructura del bosque modifican:

- disponibilidad de raíces hospedadoras;
- competencia entre árboles;
- entrada de luz;
- temperatura y humedad del suelo;
- producción de carbono;
- acumulación de hojarasca.

El valor óptimo calculado en aquel estudio pertenece a ese sistema forestal concreto y no debe utilizarse como umbral universal.

**Conclusión útil:** Rainmapper debería incorporar estructura forestal cuando existan datos fiables, pero calibrar su función por tipo de bosque y región.

## 2.6. Micelio, carpóforos y gestión forestal

Parladé et al. cuantificaron el micelio de *B. edulis* mediante PCR en tiempo real y compararon parcelas con corta total, corta parcial y sin intervención.

Los resultados principales fueron:

- la corta de árboles redujo fuertemente la biomasa de micelio del suelo;
- la biomasa de micelio en otoño se correlacionó con la producción de carpóforos;
- la recolección intensiva de setas no produjo un efecto significativo sobre la biomasa micelial.

Estos resultados tienen aplicación directa para Rainmapper:

- una masa forestal recién cortada no debe conservar automáticamente la misma aptitud anterior;
- la intensidad y fecha de la perturbación importan;
- la detección o estimación del micelio podría mejorar la predicción, aunque no suele estar disponible a escala cartográfica.

**Conclusión útil:** la continuidad del hospedador vivo y de su sistema radicular debe tratarse como una condición ecológica importante.

## 2.7. Extremos térmicos y aclareo

Salerni, Paoli y Perini analizaron la producción de *B. edulis* bajo distintos niveles de gestión forestal y episodios climáticos extremos.

Encontraron que aumentos bruscos de temperatura máxima parecían inhibir la productividad en parcelas no aclaradas o con aclareo moderado. En las parcelas con aclareo intenso, la respuesta posterior fue diferente y la productividad pareció favorecerse a partir de aproximadamente veinte días después del evento.

Este resultado es específico del diseño, bosque y periodo estudiados. No justifica afirmar que el calor sea beneficioso tras un número fijo de días. Sí demuestra una interacción entre:

- extremo térmico;
- apertura del dosel;
- microclima;
- respuesta posterior de la fructificación.

**Conclusión útil:** la temperatura debe interactuar con cobertura y gestión, no entrar únicamente como variable independiente.

## 2.8. Microbiota y dinámica del micelio en castañares

Santolamazza-Carbone et al. estudiaron el micelio de *B. edulis* mediante qPCR en castañares de distintas edades y durante diferentes meses y años.

La frecuencia y concentración de micelio cambiaron notablemente entre años. La edad de las plantaciones no explicó por sí sola todas las diferencias, y se encontraron asociaciones entre la microbiota del suelo y la concentración del micelio.

Este trabajo se refiere a micelio, no a producción de carpóforos. No permite convertir la microbiota en una variable operativa sencilla para Rainmapper, pero demuestra que parte de la variabilidad queda fuera de la meteorología y de la estructura visible del bosque.

**Conclusión útil:** incluso un modelo con buen clima y hábitat seguirá teniendo incertidumbre biológica no observada.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y formación forestal

La literatura específica revisada incluye *B. edulis* en:

- pinares de *Pinus sylvestris*;
- castañares;
- bosques húmedos de coníferas;
- otros sistemas ectomicorrícicos compatibles.

La especie tiene una amplitud de hospedadores considerable. Por ello, Rainmapper no debería utilizar una única especie arbórea como requisito exclusivo.

El modelo debe distinguir entre:

- hospedador potencial;
- hábitat local con producción demostrada;
- tipo y estructura del rodal;
- continuidad temporal del bosque.

## 3.2. Precipitación

La precipitación durante la estación de fructificación es uno de los factores mejor respaldados, especialmente en los estudios de Soria.

Debe calcularse mediante ventanas móviles y periodos fenológicos regionales. La literatura revisada no permite afirmar que exista una cantidad mínima universal.

## 3.3. Humedad del suelo

La humedad del suelo aparece en modelos específicos y representa una medida más próxima a la disponibilidad hídrica que la lluvia bruta.

Sin embargo, no todos los estudios muestran que sustituya o supere a la precipitación. Por tanto, Rainmapper debería conservar ambas variables y evitar una conclusión categórica sobre cuál será mejor en todas las regiones.

## 3.4. Temperatura

La evidencia es menos uniforme que para la precipitación:

- en Parladé et al. no se detectó un efecto significativo de la temperatura media;
- en Olano et al., la temperatura mínima formó parte de modelos informativos;
- en Salerni et al., los incrementos bruscos de temperatura máxima interactuaron con el nivel de aclareo.

La conclusión defendible es que la temperatura importa, pero:

- puede importar como mínima, máxima, anomalía o extremo;
- su efecto puede depender de la humedad y la cobertura;
- la temperatura media aislada puede no ser informativa.

## 3.5. Estado previo de la vegetación

El NDVI del año anterior contribuyó a explicar la producción en la serie larga de Olano et al.

Esta variable puede interpretarse como indicador del estado productivo del hospedador, pero no como medida directa del carbono disponible para el hongo.

Rainmapper puede utilizar NDVI o EVI como modulador del potencial de campaña, manteniendo explícita esta limitación interpretativa.

## 3.6. Estructura y gestión forestal

El área basimétrica y las cortas forestales cuentan con evidencia específica.

Deben considerarse:

- área basimétrica o un sustituto;
- cobertura de copa;
- densidad;
- corta total o parcial;
- años desde la intervención;
- supervivencia del hospedador.

No se debe copiar un supuesto óptimo estructural entre regiones o especies forestales.

## 3.7. Fenología y sequía antecedente

La producción se concentra generalmente en la estación húmeda y fresca de cada región, pero la fecha y duración varían.

Variables defendibles:

- día del año;
- precipitación acumulada desde verano;
- duración del periodo seco;
- anomalía respecto a la climatología;
- comienzo observado de la campaña local.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

Los estudios muestran relaciones entre precipitación y producción, pero no un umbral transferible a cualquier territorio.

## 4.2. Retardo fijo después de la lluvia

No se ha encontrado un número universal de días entre precipitación y fructificación.

## 4.3. Temperatura óptima única

Los resultados dependen del indicador térmico, el bosque y la gestión.

## 4.4. Superioridad universal de la humedad del suelo

Es una variable relevante, pero la literatura específica no demuestra que siempre prediga mejor que la precipitación.

## 4.5. Viento, humedad relativa, radiación y VPD

Son variables físicamente plausibles para representar secado y microclima, pero los trabajos seleccionados no proporcionan funciones específicas robustas para la producción de *B. edulis*.

## 4.6. pH o litología universalmente óptimos

La especie aparece en sistemas edáficos diferentes. Los valores locales no deben convertirse en reglas globales.

## 4.7. Efecto positivo general del aclareo

La gestión puede modificar producción y microclima, pero la dirección del efecto depende de intensidad, tiempo transcurrido y condiciones locales. No debe asumirse que aclarar siempre mejora la producción.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- hospedador compatible;
- tipo de bosque;
- continuidad del arbolado;
- estructura del rodal;
- perturbaciones recientes;
- historial de presencia.

## 5.2. Componente hídrico

Incluir por separado:

- precipitación reciente;
- precipitación acumulada durante la estación;
- duración de sequía antecedente;
- humedad del suelo;
- anomalía respecto a la climatología local.

No imponer inicialmente un único índice compuesto que oculte qué señal funciona mejor.

## 5.3. Componente térmico

Incluir:

- temperatura mínima;
- temperatura máxima;
- temperatura media;
- cambios bruscos;
- anomalías térmicas;
- interacción con cobertura y humedad.

La calibración debe determinar qué variable resulta relevante por región.

## 5.4. Potencial de campaña

Incluir, cuando esté disponible:

- NDVI/EVI del año anterior;
- vigor actual del bosque;
- balance hídrico estacional;
- historial de productividad local.

## 5.5. Estructura y gestión

Representar:

- cobertura;
- área basimétrica o sustituto;
- densidad;
- cortas recientes;
- severidad de perturbaciones;
- tiempo desde la intervención.

## 5.6. Evidencia observacional

Cada observación debería registrar:

- identificación fiable;
- fecha y coordenadas;
- abundancia o biomasa aproximada;
- esfuerzo de búsqueda;
- hospedador;
- estructura del bosque;
- perturbaciones;
- meteorología previa;
- ausencia documentada cuando exista muestreo real.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- hospedador y tipo de bosque;
- precipitación de la estación de fructificación;
- precipitación reciente;
- temperatura mínima y máxima;
- día del año;
- altitud;
- historial local de observaciones;
- perturbaciones forestales intensas.

## Recomendables

- humedad del suelo;
- duración de la sequía antecedente;
- cobertura de copa;
- área basimétrica o indicador estructural;
- NDVI/EVI;
- anomalías climáticas;
- orientación y pendiente.

## Experimentales

- viento;
- humedad relativa;
- radiación;
- evapotranspiración;
- déficit de presión de vapor;
- microbiota del suelo;
- estimación indirecta de biomasa micelial.

“Experimental” significa que la literatura seleccionada no permite asignarles un efecto específico generalizable para la fructificación de *B. edulis*.

---

# 7. Conclusiones

1. *Boletus edulis* dispone de literatura específica suficiente para construir un modelo probabilístico científicamente informado.

2. La precipitación durante la estación de fructificación es uno de los factores más consistentemente respaldados.

3. La humedad del suelo es útil, pero no debe declararse universalmente superior a la precipitación.

4. La temperatura presenta efectos dependientes del indicador y del contexto. La temperatura media puede no resultar significativa mientras que las mínimas, máximas o extremos sí lo hacen.

5. El estado productivo del bosque durante el año anterior puede contribuir a explicar la cosecha posterior.

6. La estructura del rodal, especialmente el área basimétrica en pinares de *Pinus sylvestris*, tiene capacidad predictiva demostrada.

7. Las cortas intensas pueden reducir claramente el micelio y la producción.

8. La recolección intensiva de carpóforos no redujo la biomasa micelial en el estudio específico revisado, aunque este resultado no debe generalizarse a cualquier práctica de recolección o hábitat.

9. La sequía estival puede modificar productividad y fenología.

10. No existe base científica para fijar una lluvia mínima, una temperatura óptima o un retardo universal después de la precipitación.

Rainmapper debería combinar señales climáticas, estado hídrico, estructura forestal y productividad previa del hospedador. Los parámetros numéricos deben aprenderse regionalmente a partir de observaciones y mantenerse separados de las conclusiones generales de la literatura.

---

# 8. Bibliografía seleccionada

## 1. Parladé, J. et al. (2017)

**Título:** Effects of forest management and climatic variables on the mycelium dynamics and sporocarp production of the ectomycorrhizal fungus *Boletus edulis*.  
**Revista:** Forest Ecology and Management, 390, 73–79.  
**DOI / página editorial:** https://www.sciencedirect.com/science/article/pii/S0378112717301317  
**Copia institucional:** https://digital.csic.es/bitstream/10261/413365/4/boletus_edulis_fungus_Parlade.pdf

**Aportación:** seguimiento específico de micelio y carpóforos en *Pinus sylvestris*. Demuestra correlación positiva con precipitación otoñal, reducción del micelio tras cortas y relación entre biomasa micelial otoñal y producción.

**Confianza:** alta dentro del sistema forestal estudiado.

## 2. Olano, J. M. et al. (2020)

**Título:** Primary productivity and climate control mushroom yields in Mediterranean pine forests.  
**Revista:** Agricultural and Forest Meteorology, 288–289, 107994.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0168192320301179  
**Texto institucional:** https://uvadoc.uva.es/bitstream/handle/10324/73839/Primary-productivity-and-climate-control-mushroom-_2020_Agricultural-and-For.pdf?sequence=1

**Aportación:** series de 22 y 24 años; modelo específico de *B. edulis* con precipitación, temperatura mínima, humedad del suelo y NDVI previo.

**Confianza:** alta para variabilidad interanual y combinación de clima con productividad primaria.

## 3. Martínez-Peña, F. et al. (2012)

**Título:** Yield models for ectomycorrhizal mushrooms in *Pinus sylvestris* forests with special focus on *Boletus edulis* and *Lactarius* group *deliciosus*.  
**Revista:** Forest Ecology and Management, 282, 63–69.  
**DOI:** https://doi.org/10.1016/j.foreco.2012.06.034  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0378112712003635  
**Texto:** https://cris.ctfc.cat/docs/upload/27_310_Yield%20models.pdf

**Aportación:** primer modelo de rendimiento declarado específicamente para *B. edulis*; identifica el área basimétrica como un factor fuerte.

**Confianza:** alta para el papel de la estructura en los pinares estudiados; los valores concretos son locales.

## 4. Büntgen, U. et al. (2015)

**Título:** Drought-induced changes in the phenology, productivity and diversity of Spanish fungi.  
**Revista:** Fungal Ecology, 16, 6–18.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S1754504815000331

**Aportación:** relaciona tendencias de fenología y productividad de *B. edulis* con la disminución de la precipitación de julio a septiembre.

**Confianza:** alta para tendencias de largo plazo; no define una regla de episodio individual.

## 5. García-Bustamante, E. et al. (2021)

**Título:** Impact of local and regional climate variability on fungi productivity in *Pinus sylvestris* forests: the case of *Boletus edulis*.  
**Revista:** International Journal of Climatology.  
**DOI / página editorial:** https://rmets.onlinelibrary.wiley.com/doi/10.1002/joc.7144

**Aportación:** estudia específicamente la relación de *B. edulis* con variabilidad climática local y regional en Soria.

**Confianza:** alta para la necesidad de contextualización espacial del clima.

## 6. Salerni, E., Paoli, L. y Perini, C. (2023)

**Título:** Combined impact of forest management and climate change on *Boletus edulis* productivity: may mycosilviculture mitigate the effects of climate extremes?  
**Revista:** Italian Journal of Mycology, 52(1), 76–88.  
**DOI:** https://doi.org/10.6092/issn.2531-7342/16464  
**Texto:** https://italianmycology.unibo.it/article/view/16464

**Aportación:** analiza conjuntamente extremos de temperatura máxima y diferentes intensidades de aclareo.

**Confianza:** media-alta; la interacción observada es específica del sistema y no debe transformarse en un umbral universal.

## 7. Santolamazza-Carbone, S. et al. (2023)

**Título:** Soil microbiota impact on *Boletus edulis* mycelium in chestnut orchards of different ages.  
**Revista:** Applied Soil Ecology, 181, 104790.  
**DOI / texto:** https://www.sciencedirect.com/science/article/pii/S0929139322004061

**Aportación:** demuestra variación anual de frecuencia y concentración de micelio y asociaciones con la microbiota del suelo.

**Confianza:** alta para dinámica micelial; no mide directamente producción de carpóforos.

## 8. Salerni, E. y Perini, C. (2004)

**Título:** Experimental study for increasing productivity of *Boletus edulis* s.l. in Italy.  
**Revista:** Forest Ecology and Management, 201, 161–170.  
**DOI:** https://doi.org/10.1016/j.foreco.2004.06.027  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S0378112704005213

**Aportación:** experimento de gestión orientado a productividad de *B. edulis* sensu lato. Se conserva por su relevancia histórica y experimental, pero sus resultados deben interpretarse con cautela por el uso de “sensu lato”.

**Confianza:** media para gestión; menor que la de los estudios que identifican estrictamente *B. edulis*.

---

## Nota final sobre la evidencia

Se revisaron también trabajos generales sobre productividad de hongos mediterráneos, humedad del suelo, cambio climático y gestión forestal. Solo se incorporaron al texto cuando presentaban resultados separados para *B. edulis*.

No se utilizaron como evidencia principal:

- estudios que agrupaban todos los hongos ectomicorrícicos;
- modelos de producción total sin desglose de especie;
- afirmaciones divulgativas sobre humedad relativa, luna o días exactos de aparición;
- parámetros obtenidos en un único bosque como si fueran universales.

La evidencia disponible es notablemente mejor que para *B. aereus* o *B. pinophilus*, pero sigue describiendo relaciones probabilísticas y dependientes del lugar.
