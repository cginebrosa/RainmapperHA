# Predicción de producción de *Tuber melanosporum*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Tuber melanosporum* Vittad.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Tuber melanosporum* y aporta información útil sobre producción de ascocarpos, clima, humedad del suelo, hospedadores, propiedades edáficas, micelio o cambio climático.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

*Tuber melanosporum* es una de las especies de hongos comestibles mejor estudiadas desde el punto de vista productivo. Existen series regionales de varias décadas, estudios de humedad del suelo, modelos climáticos, análisis de propiedades edáficas, trabajos de cuantificación de micelio y revisiones detalladas de su ciclo biológico.

Aun así, la literatura no permite convertir su producción en una regla universal simple. La trufa negra desarrolla sus ascocarpos bajo tierra durante varios meses, y la cosecha final depende de la interacción entre clima, suelo, hospedador, manejo y biología reproductiva.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica y necesita un hospedador compatible.** Los hospedadores más utilizados y mejor documentados incluyen *Quercus ilex*, otros *Quercus* y *Corylus avellana*. La presencia de un árbol micorrizado no garantiza producción.

2. **Los suelos calizos son un requisito ecológico central.** La especie se asocia con suelos bien aireados y ricos en carbonatos, aunque no existe un único valor de pH, textura o carbonato activo que garantice una trufera productiva.

3. **La humedad del suelo es una de las variables predictivas más importantes.** Un estudio ibérico específico mostró relaciones claras entre la humedad modelizada de la zona radicular y la producción regional.

4. **La precipitación estival es especialmente relevante.** Las series españolas de 1970–2017 relacionaron la producción y el crecimiento del hospedador principalmente con la lluvia de verano y con temperaturas de distintos periodos comprendidos entre la brotación del árbol y la maduración de los ascocarpos.

5. **Los veranos cálidos y secos perjudican la producción de cuerpos fructíferos.** Los análisis regionales europeos muestran descensos de rendimiento cuando coinciden temperaturas estivales elevadas y escasez de precipitación.

6. **La respuesta del micelio y la de los ascocarpos no son idénticas.** Estudios recientes sugieren que el micelio puede tolerar o incluso mostrar mayor abundancia bajo condiciones estivales cálidas y secas, mientras que la producción de trufas disminuye. No deben confundirse supervivencia del micelio y cosecha comercial.

7. **La estación de desarrollo es larga.** El ascocarpo pasa por distintas fases desde primavera o verano hasta la cosecha de finales de otoño e invierno. Las variables de varios meses son más relevantes que el tiempo de los días inmediatamente anteriores a la recolección.

8. **La producción invernal depende de las condiciones mediterráneas acumuladas.** Los estudios regionales indican que la precipitación y la temperatura en verano y otoño condicionan la cosecha posterior.

9. **El estado del hospedador también importa.** El crecimiento del árbol y la producción de trufa comparten parte de la señal climática, especialmente la disponibilidad de agua en verano.

10. **Las propiedades convencionales del suelo explican solo una parte de la variabilidad.** En un estudio ibérico, textura, pH, carbonatos, carbono, nitrógeno y cationes explicaron conjuntamente una proporción limitada de la producción.

11. **El carbonato activo parece más relevante que el carbonato total.** Varios trabajos encontraron mayor carbonato activo en suelos productores de *T. melanosporum* y diferencias respecto a suelos productores de otras especies de *Tuber*.

12. **La distribución del micelio responde de forma distinta en plantaciones y bosques naturales.** Un estudio regional de diez sitios encontró diferentes combinaciones de variables climáticas, topográficas y químicas según el sistema productivo.

13. **No existe una cantidad mínima universal de lluvia, una humedad óptima única, una temperatura crítica general ni un rendimiento garantizado por un tipo de suelo.**

14. **Rainmapper debería separar tres predicciones:** aptitud permanente del sitio, potencial anual de producción y estado de desarrollo de la campaña actual.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hospedador compatible y micorrización | Filtro ecológico principal | Muy alta |
| Suelo calizo, aireado y con carbonato activo | Filtro edáfico | Muy alta |
| Humedad del suelo en zona radicular | Variable climática principal | Muy alta |
| Precipitación de primavera–verano–otoño | Entrada hídrica | Alta |
| Temperatura estival | Modulador y factor de estrés | Alta |
| Déficit hídrico estival | Penalización de producción | Muy alta |
| Estado y crecimiento del hospedador | Potencial de campaña | Alta |
| Día del año y fase de desarrollo | Componente fenológico | Muy alta |
| Altitud y clima regional | Moduladores espaciales | Alta |
| Manejo e irrigación | Corrección del estado hídrico | Alta |
| Abundancia de micelio | Indicador biológico, no equivalente a cosecha | Media-alta |
| Historial de producción | Predictor local principal | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *T. melanosporum* mediante un filtro edáfico y de hospedador, seguido de un modelo anual basado en humedad del suelo, lluvia estival, temperatura, déficit hídrico, estado del árbol y manejo. La producción debe estimarse como probabilidad o rendimiento esperado, nunca como una respuesta determinista a una lluvia concreta.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de producción de *Tuber melanosporum*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- trabajos sobre *Tuber aestivum*, *T. indicum* u otras trufas sin resultados separados;
- guías comerciales o divulgativas sin metodología científica;
- estudios exclusivamente aromáticos, gastronómicos o de conservación poscosecha;
- recomendaciones de cultivo sin datos originales verificables;
- valores climáticos locales presentados como límites universales;
- trabajos de micelio que no permitían distinguir entre presencia biológica y producción de ascocarpos;
- estudios de distribución potencial sin aplicación clara a productividad anual.

Se seleccionaron **nueve referencias principales**, priorizando series largas, humedad del suelo, producción regional, suelo, micelio y ciclo biológico.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Ciclo biológico y fases de desarrollo

Le Tacon et al. revisaron las certezas e incertidumbres del ciclo de *T. melanosporum*.

El proceso incluye:

- germinación de esporas;
- micelio haploide;
- colonización ectomicorrícica del hospedador;
- coexistencia de tipos de apareamiento;
- fecundación;
- formación y desarrollo subterráneo del ascocarpo;
- maduración y liberación posterior de esporas.

La formación del cuerpo fructífero se extiende durante meses.

**Conclusión útil:** Rainmapper no debe usar solo meteorología de los días anteriores a la recolección. Debe representar fases estacionales.

## 2.2. Hospedadores

La especie se cultiva y aparece naturalmente con distintos árboles ectomicorrícicos.

Los mejor documentados en Europa incluyen:

- *Quercus ilex*;
- otros robles;
- *Corylus avellana*;
- determinados *Cistus* y otras especies en sistemas naturales.

La productividad cambia según hospedador y sistema. García-Montero et al. encontraron una producción inferior en brûlés asociados a *Cistus laurifolius* respecto a *Corylus avellana* o *Quercus ilex* en el área estudiada.

**Conclusión útil:** Rainmapper debe distinguir especie hospedadora y no tratar todos los árboles micorrizados como equivalentes.

## 2.3. Suelos calizos

La afinidad por suelos calizos es una de las conclusiones más consistentes.

Las características frecuentemente asociadas incluyen:

- reacción neutra o alcalina;
- carbonatos;
- estructura aireada;
- drenaje suficiente;
- capacidad de retener agua sin anegamiento;
- actividad biológica y estructura favorable.

No existe una combinación única que garantice producción.

**Conclusión útil:** el suelo debe funcionar como filtro multidimensional, no como un simple umbral de pH.

## 2.4. Carbonato activo y carbonato total

García-Montero et al. encontraron diferencias entre:

- suelos dentro y fuera de los brûlés;
- zonas productoras de *T. melanosporum*;
- zonas donde fructificaban otras especies de *Tuber*.

El carbonato activo fue frecuentemente mayor en suelos favorables a *T. melanosporum*, mientras que el carbonato total por sí solo resultó menos informativo.

Los autores propusieron que el micelio puede modificar localmente el entorno químico y solubilizar fracciones carbonatadas.

**Conclusión útil:** Rainmapper debería distinguir, cuando existan datos, carbonato activo y carbonato total.

## 2.5. Capacidad explicativa limitada de las propiedades convencionales del suelo

Un estudio de veinte horizontes superficiales en la península ibérica relacionó productividad con:

- textura;
- pH;
- carbonatos;
- carbono orgánico;
- nitrógeno;
- cationes intercambiables.

El análisis conjunto explicó solo una parte limitada de la variabilidad productiva.

Esto demuestra que:

- un suelo aparentemente adecuado puede no producir;
- la biología, el clima y el manejo siguen siendo decisivos;
- no existe una “receta edáfica” suficiente.

**Conclusión útil:** la aptitud del suelo debe combinarse con historial productivo y estado biológico.

## 2.6. Humedad del suelo y producción ibérica

González-Zamora et al. analizaron humedad modelizada de la zona radicular mediante LISFLOOD y producción de trufa negra en la península ibérica.

El estudio comparó:

- humedad del suelo;
- precipitación;
- escalas temporales diarias, semanales y mensuales;
- variabilidad espacial de la relación.

Los resultados confirmaron una relación significativa entre humedad del suelo y producción.

La humedad integra procesos que la lluvia no representa por sí sola:

- evapotranspiración;
- infiltración;
- almacenamiento;
- drenaje;
- humedad antecedente.

**Conclusión útil:** la humedad del suelo debe ser una variable prioritaria y mantenerse separada de la precipitación.

## 2.7. Precipitación y temperatura en la producción española

García-Barreda et al. analizaron la producción española entre 1970 y 2017.

Encontraron que:

- la variación de la producción se vinculaba al clima;
- la lluvia de verano era especialmente relevante;
- varias temperaturas entre la brotación del hospedador y la maduración del ascocarpo contribuían a explicar la señal;
- el crecimiento del hospedador y la producción compartían parte de la respuesta climática;
- la transición desde cosecha silvestre a plantaciones modificó la tendencia y la variabilidad de las estadísticas nacionales.

**Conclusión útil:** Rainmapper debe separar las series de truferas silvestres y plantaciones, y considerar el manejo de riego.

## 2.8. Producción invernal y clima mediterráneo

Büntgen et al. analizaron series regionales de producción y clima.

El estudio mostró que:

- la cosecha invernal está fuertemente condicionada por el clima mediterráneo;
- lluvia y temperatura durante meses previos influyen en el rendimiento;
- el calor y la sequía crecientes amenazan la producción;
- el riego puede amortiguar parte del déficit hídrico, pero no elimina todos los efectos térmicos.

**Conclusión útil:** el modelo debe conectar condiciones estivales y otoñales con producción invernal.

## 2.9. Veranos cálidos y secos

Los resultados de series regionales y proyecciones climáticas coinciden en que la combinación de:

- temperatura elevada;
- déficit de lluvia;
- sequía persistente;

reduce la producción de ascocarpos.

No debe interpretarse como que toda temperatura alta es negativa. La especie es mediterránea y tolera calor; el problema documentado es el estrés combinado y persistente durante fases sensibles.

**Conclusión útil:** modelar interacción temperatura × humedad, no penalizar linealmente todo el calor.

## 2.10. Micelio frente a ascocarpos

Barou et al. modelaron la biomasa del micelio en plantaciones y bosques naturales de diez sitios.

Los modelos explicaron una parte sustancial de la variabilidad, pero las variables importantes diferían entre sistemas.

En plantaciones aparecieron, entre otras:

- altitud;
- materia orgánica;
- fósforo;
- magnesio;
- boro.

En bosques naturales aparecieron:

- longitud geográfica;
- carbonato cálcico;
- sodio;
- zinc.

Un trabajo más reciente sugiere que condiciones cálidas y secas pueden favorecer o no perjudicar el micelio mediterráneo.

Esto contrasta con el efecto negativo de la sequía sobre la producción de ascocarpos.

**Conclusión útil:** Rainmapper debe mantener dos indicadores separados:

- `mycelium_suitability`;
- `fruitbody_production_potential`.

## 2.11. Bosques naturales frente a plantaciones

Las diferencias entre ambos sistemas incluyen:

- manejo;
- riego;
- densidad de árboles;
- preparación del suelo;
- inoculación;
- competencia con otros hongos;
- edad;
- estructura y diversidad.

La respuesta a variables edáficas y climáticas no es idéntica.

**Conclusión útil:** usar submodelos o, al menos, una variable explícita `production_system`.

## 2.12. Producción histórica y factores humanos

Las estadísticas españolas muestran una transición desde recolección silvestre hacia producción agrícola.

Por tanto, una subida de producción nacional puede reflejar:

- mayor superficie plantada;
- entrada en producción de nuevas parcelas;
- irrigación;
- manejo;
- mejores sistemas de recolección;
- cambios de mercado.

No debe interpretarse directamente como una mejora climática.

**Conclusión útil:** no calibrar relaciones climáticas con producción agregada sin corregir por superficie y manejo.

## 2.13. Amplitud climática de cultivo

Thomas analizó plantaciones productivas de seis continentes.

El trabajo mostró que la especie puede fructificar bajo un rango climático más amplio de lo considerado tradicionalmente, incluyendo lugares:

- más fríos;
- más lluviosos;
- fuera de la distribución natural.

Esto demuestra que los límites históricos de presencia natural no equivalen a límites fisiológicos absolutos, especialmente con:

- elección de hospedador;
- irrigación;
- manejo del suelo;
- microclima.

**Conclusión útil:** evitar filtros climáticos rígidos y diferenciar aptitud natural de aptitud bajo cultivo.

## 2.14. Profundidad, tamaño y maduración

García-Barreda et al. estudiaron profundidad, peso y madurez de trufas.

No encontraron vínculos simples entre esas etapas o características.

Esto indica que el desarrollo del ascocarpo no puede resumirse mediante una única variable de tamaño o profundidad.

**Conclusión útil:** el modelo de producción no debe asumir que ascocarpos más profundos, grandes o antiguos maduran siempre de la misma forma.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y sistema productivo

Variables prioritarias:

- especie hospedadora;
- plantación o bosque natural;
- edad del árbol;
- inoculación;
- estado del brûlé;
- densidad;
- historial productivo.

## 3.2. Suelo

Incluir:

- pH;
- carbonato total;
- carbonato activo;
- textura;
- estructura;
- porosidad;
- profundidad;
- materia orgánica;
- drenaje;
- capacidad de retención;
- calcio, magnesio y nutrientes relevantes.

Ninguna variable debe actuar sola.

## 3.3. Humedad del suelo

Debe representarse por:

- humedad de zona radicular;
- humedad en diferentes profundidades;
- déficit;
- duración de sequía;
- recuperación tras lluvia o riego;
- anomalía respecto a climatología.

## 3.4. Precipitación e irrigación

Distinguir:

- lluvia;
- riego;
- distribución temporal;
- intensidad;
- infiltración;
- precipitación estival;
- precipitación otoñal.

La suma anual es menos informativa que la distribución durante fases sensibles.

## 3.5. Temperatura

Incluir:

- temperatura del aire;
- temperatura del suelo;
- máximas estivales;
- mínimas invernales;
- anomalías;
- duración de olas de calor;
- interacción con humedad.

## 3.6. Estado del hospedador

Variables recomendadas:

- crecimiento anual;
- vigor;
- NDVI/EVI;
- estrés hídrico;
- defoliación;
- mortalidad;
- brotación.

La señal del árbol puede modular el carbono disponible para la simbiosis.

## 3.7. Fenología de campaña

Separar:

- crecimiento vegetativo;
- formación inicial de ascocarpos;
- engorde;
- maduración;
- cosecha.

Las fechas exactas deben calibrarse regionalmente.

## 3.8. Historial de producción

Incluir:

- kg por campaña;
- superficie productiva;
- edad de plantación;
- número de árboles productores;
- riego;
- manejo;
- ubicación del brûlé;
- años sin producción.

## 3.9. Micelio y tipos de apareamiento

Cuando existan datos:

- abundancia de ADN;
- distribución espacial;
- tipos de apareamiento;
- distancia al tronco;
- estación de muestreo.

La abundancia de micelio no equivale automáticamente a cosecha.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral común a todas las regiones y sistemas.

## 4.2. Humedad óptima única

La relación depende de profundidad, suelo, estación y fase del ascocarpo.

## 4.3. Temperatura óptima universal

La amplitud climática de plantaciones productivas contradice límites rígidos.

## 4.4. Suelo “perfecto” que garantice producción

Las propiedades convencionales explican solo parte de la variabilidad.

## 4.5. Carbonato total como predictor suficiente

El carbonato activo puede ser más informativo y el hongo modifica su propio entorno.

## 4.6. Mayor micelio igual a mayor producción

Los estudios de micelio y ascocarpos muestran respuestas distintas.

## 4.7. Efecto del clima sin corregir por manejo

Riego, superficie plantada y edad de las truferas alteran las series productivas.

## 4.8. Viento, radiación o humedad relativa como predictores independientes

Pueden contribuir al balance hídrico, pero no existe una función universal específica.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Capa de aptitud permanente

Combinar:

- hospedador;
- micorrización;
- pH;
- carbonatos;
- textura;
- estructura;
- drenaje;
- profundidad;
- altitud;
- clima de fondo.

## 5.2. Potencial anual

Incluir:

- humedad de primavera;
- precipitación estival;
- déficit hídrico;
- temperaturas estivales;
- estado del hospedador;
- riego;
- edad de la plantación;
- historial productivo.

## 5.3. Estado de campaña

Incluir:

- humedad del suelo por fases;
- lluvia y riego recientes;
- temperatura del suelo;
- olas de calor;
- transición otoño–invierno;
- fechas históricas de cosecha.

## 5.4. Separación micelio–ascocarpos

Mantener:

- aptitud del micelio;
- probabilidad de formación;
- potencial de engorde;
- probabilidad de maduración;
- rendimiento esperado.

## 5.5. Diferenciación por sistema

Submodelos recomendados:

- bosque natural;
- plantación sin riego;
- plantación irrigada.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha;
- coordenadas;
- peso;
- profundidad;
- madurez;
- hospedador;
- árbol productor;
- edad;
- suelo;
- riego;
- lluvia;
- humedad;
- temperatura;
- manejo;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- hospedador;
- sistema productivo;
- historial de producción;
- pH y carbonatos;
- textura y drenaje;
- humedad del suelo;
- precipitación estival;
- temperatura estival;
- déficit hídrico;
- día del año;
- edad de la plantación.

## Recomendables

- carbonato activo;
- temperatura del suelo;
- riego;
- materia orgánica;
- profundidad;
- NDVI o crecimiento del hospedador;
- altitud;
- manejo del brûlé;
- nutrientes del suelo.

## Experimentales

- abundancia de micelio;
- tipos de apareamiento;
- microbioma;
- conductividad térmica del suelo;
- potencial matricial;
- radiación;
- viento;
- modelos por fase de desarrollo;
- detección remota del estrés del hospedador.

“Experimental” significa que la variable puede ser relevante y contar con evidencia local, pero no dispone todavía de una relación universal con la producción de ascocarpos.

---

# 7. Conclusiones

1. *Tuber melanosporum* es una especie ectomicorrícica y necesita hospedadores compatibles.

2. Los suelos calizos son un requisito ecológico central, pero no garantizan producción.

3. La humedad del suelo es una de las variables productivas mejor respaldadas.

4. La precipitación estival y el déficit hídrico condicionan la cosecha invernal.

5. Los veranos persistentemente cálidos y secos reducen la producción de ascocarpos.

6. La respuesta del micelio puede diferir de la respuesta de la producción.

7. El estado y crecimiento del hospedador forman parte de la señal productiva.

8. Las propiedades edáficas convencionales explican solo una parte de la variabilidad.

9. El carbonato activo puede ser más informativo que el carbonato total.

10. Plantaciones y bosques naturales responden a combinaciones ambientales diferentes.

11. El manejo y el riego impiden interpretar de forma directa las estadísticas agregadas de producción.

12. No existe una lluvia mínima, humedad óptima, temperatura crítica ni suelo perfecto universal.

13. Rainmapper debería separar aptitud permanente, potencial anual y estado de campaña.

14. El modelo debe predecir rendimiento probabilístico y no una fecha exacta de “florada”, ya que la trufa se desarrolla bajo tierra durante meses.

---

# 8. Bibliografía seleccionada

## 1. García-Barreda, S. et al. (2020)

**Título:** Variability and trends of black truffle production in Spain (1970–2017): Linkages to climate, host growth, and human factors.  
**Revista:** Agricultural and Forest Meteorology, 287, 107951.  
**DOI / página editorial:** https://doi.org/10.1016/j.agrformet.2020.107951  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0168192320300538

**Aportación:** principal serie española de largo plazo. Relaciona producción, lluvia estival, temperaturas, crecimiento del hospedador y transición hacia cultivo.

**Confianza:** muy alta para tendencias nacionales; requiere corregir por cambios de superficie y manejo.

## 2. González-Zamora, Á. et al. (2022)

**Título:** Soil Moisture and Black Truffle Production Variability in the Iberian Peninsula.  
**Revista:** Forests, 13, 819.  
**DOI / texto completo:** https://doi.org/10.3390/f13060819  
**Enlace:** https://www.mdpi.com/1999-4907/13/6/819

**Aportación:** demuestra de forma específica la relación entre humedad modelizada de la zona radicular y producción ibérica.

**Confianza:** muy alta para la utilidad de humedad del suelo a escala regional.

## 3. Büntgen, U. et al. (2019)

**Título:** Black truffle winter production depends on Mediterranean summer precipitation.  
**Revista:** Environmental Research Letters, 14, 074004.  
**Texto completo:** https://cris.ctfc.cat/docs/upload/27_1069_envreslet_a2019v14n7.pdf

**Aportación:** relaciona producción regional de invierno con precipitación y temperatura mediterráneas y analiza riesgos climáticos.

**Confianza:** alta para relación climática regional.

## 4. Le Tacon, F. et al. (2016)

**Título:** Certainties and uncertainties about the life cycle of the Périgord black truffle (*Tuber melanosporum* Vittad.).  
**Revista:** Annals of Forest Science, 73, 105–117.  
**DOI / página:** https://doi.org/10.1007/s13595-015-0461-1  
**Referencia accesible en:** https://pmc.ncbi.nlm.nih.gov/articles/PMC8775154/

**Aportación:** revisión biológica principal del ciclo, reproducción, ectomicorrizas y desarrollo del ascocarpo.

**Confianza:** muy alta para ciclo biológico.

## 5. García-Montero, L. G. et al. (2006)

**Título:** Soil factors that influence the fruiting of *Tuber melanosporum* (black truffle).  
**Revista:** Australian Journal of Soil Research.  
**Consulta:** https://www.academia.edu/57315899/Soil_factors_that_influence_the_fruiting_of_Tuber_melanosporum_black_truffle_

**Aportación:** analiza estadísticamente textura, pH, carbonatos, carbono, nitrógeno y cationes, mostrando que explican una fracción limitada de la producción.

**Confianza:** alta para la limitación predictiva de las propiedades edáficas convencionales.

## 6. García-Montero, L. G. et al. (2009)

**Título:** Calcareous amendments in truffle culture: A soil nutrition hypothesis.  
**Revista:** Soil Biology and Biochemistry.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0038071709000923

**Aportación:** revisa el papel de carbonato activo, carbonato total y modificación del suelo por el brûlé.

**Confianza:** alta para procesos carbonatados; no define un umbral universal.

## 7. Barou, V. et al. (2024)

**Título:** Modelling environmental drivers of *Tuber melanosporum* mycelium in productive plantations and forests.  
**Revista:** Forest Ecology and Management, 563, 121988.  
**DOI / texto completo:** https://doi.org/10.1016/j.foreco.2024.121988  
**Enlace:** https://repositori.irta.cat/bitstream/handle/20.500.12327/3038/Barou_Modeling_2024.pdf?isAllowed=y&sequence=1

**Aportación:** cuantifica micelio mediante qPCR en diez sitios y demuestra que plantaciones y bosques responden a diferentes combinaciones ambientales.

**Confianza:** muy alta para micelio; no equivalente a producción de ascocarpos.

## 8. Thomas, P. W. (2014)

**Título:** An analysis of the climatic parameters needed for *Tuber melanosporum* cultivation incorporating data from six continents.  
**Revista:** Mycosphere, 5, 137–142.  
**Texto completo:** https://www.mycosphere.org/pdf/Mycosphere_5_1_5.pdf

**Aportación:** demuestra una amplitud climática de cultivo mayor de la considerada tradicionalmente.

**Confianza:** alta para límites amplios de aptitud; no identifica condiciones óptimas de rendimiento.

## 9. García-Barreda, S. et al. (2021)

**Título:** Lack of Linkages among Fruiting Depth, Weight, and Maturity in Irrigated Black Truffle Orchards.  
**Revista:** Agronomy, 11, 498.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC7912816/

**Aportación:** demuestra que profundidad, peso y madurez no mantienen relaciones simples y que las etapas del desarrollo deben analizarse por separado.

**Confianza:** alta para características de ascocarpos en plantaciones irrigadas.

---

## Nota final sobre la evidencia

La bibliografía de *T. melanosporum* permite construir un modelo mucho más sólido que para la mayoría de especies de Rainmapper.

La evidencia permite definir con confianza:

- necesidad de hospedador ectomicorrícico;
- importancia de suelos calizos y aireados;
- papel central de humedad del suelo;
- importancia de lluvia estival;
- efecto negativo de calor y sequía persistentes sobre la producción;
- influencia del hospedador;
- diferencias entre micelio y ascocarpos;
- necesidad de separar bosque natural, secano e irrigación.

No permite definir de forma universal:

- lluvia mínima;
- humedad óptima;
- temperatura crítica;
- carbonato o pH perfectos;
- rendimiento garantizado;
- equivalencia entre abundancia de micelio y producción.

La estructura más defendible para Rainmapper es: aptitud edáfica y de hospedador + humedad y clima estacional + manejo + estado del árbol + historial productivo + modelo por fases del ciclo.
