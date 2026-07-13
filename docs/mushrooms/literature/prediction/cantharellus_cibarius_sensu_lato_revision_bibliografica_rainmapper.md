# Predicción de floradas de *Cantharellus cibarius* sensu lato
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie o grupo:** *Cantharellus cibarius* sensu lato  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Cantharellus cibarius* o taxones incluidos históricamente en *C. cibarius* sensu lato y aporta información útil sobre fructificación, fenología, hábitat o productividad.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La bibliografía sobre *Cantharellus cibarius* es más abundante que para muchas otras especies silvestres comestibles, pero presenta una dificultad importante: durante décadas se utilizó el nombre *C. cibarius* para varios taxones diferentes. Actualmente, *C. cibarius* sensu stricto se considera esencialmente europeo, mientras que numerosos estudios norteamericanos se refieren a especies o variedades que hoy se separan taxonómicamente.

Dado que Rainmapper utiliza el perfil **“*Cantharellus cibarius* sensu lato”**, esta revisión conserva algunos estudios de ese complejo cuando aportan información ecológica útil, pero identifica claramente su carácter no estrictamente europeo.

Las conclusiones mejor respaldadas son:

1. **Es un hongo ectomicorrícico y depende de hospedadores leñosos compatibles.** En Europa se asocia con coníferas y frondosas, entre ellas *Picea*, *Pinus*, *Fagus*, *Quercus* y *Castanea*. La composición del bosque debe actuar como filtro ecológico previo.

2. **El agua disponible y la temperatura previa son factores relevantes.** Estudios específicos de productividad en Canadá encontraron relaciones con temperatura del suelo, grados-día, humedad del suelo y precipitación acumulada antes de la primera aparición.

3. **No existe un umbral meteorológico universal.** Los valores obtenidos en Saskatchewan o en pinares canadienses pertenecen a esos sistemas y no deben trasladarse como reglas a Europa o a la península ibérica.

4. **La respuesta puede comenzar semanas antes de la primera fructificación visible.** Algunos modelos relacionaron el rendimiento con condiciones acumuladas entre varias semanas y meses antes de la aparición, lo que respalda el uso de ventanas temporales largas además de las lluvias recientes.

5. **El microhábitat del bosque importa.** En pinares canadienses, la productividad se relacionó con densidad del rodal, musgos, composición del sotobosque, textura del suelo y ausencia en zonas alteradas como caminos.

6. **La fructificación varía entre años y lugares.** La meteorología no explica toda la variabilidad; intervienen hospedador, estructura del bosque, suelo, micelio y perturbaciones.

7. **La fenología europea está cambiando con el clima.** Estudios continentales sobre registros de fructificación muestran desplazamientos y prolongación de la temporada en numerosas especies otoñales, entre ellas *C. cibarius* en las bases de datos analizadas.

8. **La degradación del suelo y los cambios ambientales pueden reducir las poblaciones.** El declive histórico en los Países Bajos se relacionó más con cambios del suelo y contaminación atmosférica que con la recolección.

9. **La recolección de carpóforos no cuenta con evidencia sólida de reducir por sí misma las cosechas futuras.** Estudios prolongados sobre hongos forestales no detectaron una disminución causada por cortar o arrancar, aunque el pisoteo y la alteración del suelo pueden tener efectos.

10. **No existe evidencia suficiente para fijar una velocidad crítica de viento, una humedad relativa mínima o una radiación óptima específica para el grupo.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hospedador y tipo de bosque | Filtro ecológico principal | Alta |
| Humedad del suelo | Estado hídrico | Alta |
| Precipitación previa | Señal de recarga | Alta |
| Temperatura del suelo o del aire | Modulador climático | Alta |
| Fenología regional | Modulador temporal | Alta |
| Estructura y densidad del bosque | Modulador de productividad | Media-alta |
| Musgos y microhábitat superficial | Indicador local | Media |
| Alteración del suelo y caminos | Penalización de aptitud | Media-alta |
| Historial local de observaciones | Calibración principal | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *C. cibarius* sensu lato mediante un filtro de bosque y hospedador compatible, una combinación de humedad del suelo, precipitación y temperatura acumuladas, y una fenología regional flexible. Los valores numéricos deben aprenderse localmente y no copiarse de estudios realizados con otros taxones del complejo.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Cantharellus cibarius* sensu lato?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de composición química, contaminación o propiedades medicinales;
- trabajos de otras especies de *Cantharellus* sin relación histórica con *C. cibarius*;
- modelos generales de producción fúngica sin resultados separados para el grupo;
- páginas divulgativas con cifras meteorológicas no verificables;
- estudios norteamericanos que usaban el nombre *C. cibarius* cuando la identidad taxonómica era incierta, salvo que se incluyeran expresamente como evidencia de *C. cibarius* sensu lato;
- afirmaciones sobre lluvia, temperatura o días hasta aparición que no procedían de análisis publicados.

Se seleccionaron **ocho trabajos principales**, elegidos por su utilidad para fenología, productividad, microhábitat, estructura forestal o conservación.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Problema taxonómico

El nombre *Cantharellus cibarius* se utilizó históricamente de forma muy amplia.

Los estudios moleculares demostraron que muchos rebozuelos amarillos de Norteamérica y Asia no pertenecen a *C. cibarius* sensu stricto. Por ello:

- los resultados europeos son los más directamente aplicables a *C. cibarius* sensu stricto;
- los resultados norteamericanos pueden ser útiles para el perfil sensu lato;
- no deben mezclarse como si describieran una única población biológica;
- los parámetros regionales deben calibrarse por taxón y territorio.

Esta limitación afecta especialmente a estudios canadienses identificados como *C. cibarius* o *C. cibarius* var. *roseocanus*.

**Conclusión útil:** Rainmapper debería conservar “sensu lato” solo si el perfil pretende agrupar varios rebozuelos amarillos difíciles de separar. Cuando existan identificaciones moleculares o morfológicas fiables, convendría distinguir taxones.

## 2.2. Temperatura acumulada, suelo y humedad

Ivanochko et al. estudiaron durante varios años la productividad de rebozuelos en el norte de Saskatchewan. Analizaron datos meteorológicos horarios, compras comerciales, rendimiento de campo, temperatura del suelo, humedad, precipitación y características de los rodales.

Los modelos con mejor ajuste combinaron:

- grados-día de crecimiento;
- temperatura del suelo;
- humedad del suelo o precipitación acumulada.

El estudio relacionó estas condiciones con el rendimiento varias semanas antes de la primera aparición.

Su aportación principal es demostrar que:

- la señal meteorológica se acumula durante un periodo prolongado;
- temperatura y agua actúan conjuntamente;
- la temperatura del suelo puede aportar información adicional;
- la lluvia aislada no describe por sí sola la respuesta.

Los valores numéricos publicados pertenecen a un ecosistema boreal y no deben convertirse en umbrales para Rainmapper.

**Conclusión útil:** utilizar ventanas térmicas e hídricas múltiples, con especial atención a temperatura y humedad del suelo.

## 2.3. Lluvia y temperatura en pinares de *Pinus banksiana*

Rochon et al. estudiaron la ecología y productividad de *Cantharellus cibarius* var. *roseocanus* en dos rodales de *Pinus banksiana* del este de Canadá.

Encontraron correlaciones positivas entre:

- precipitación total durante la semana anterior a la fructificación;
- temperatura del aire aproximadamente dos semanas antes;
- productividad de carpóforos.

También identificaron características de microhábitat asociadas a mayor productividad.

Este trabajo es directamente útil para el grupo sensu lato, pero no debe atribuirse sin matices al *C. cibarius* europeo.

**Conclusión útil:** la respuesta puede incluir una señal hídrica corta y una señal térmica algo anterior. Las ventanas concretas deben validarse regionalmente.

## 2.4. Microhábitat y estructura del bosque

El estudio de Rochon et al. encontró mayor productividad en microhábitats caracterizados por:

- elevada densidad del rodal;
- presencia frecuente de musgos;
- determinada composición del sotobosque;
- propiedades específicas del suelo;
- menor presencia de especies ericáceas en los lugares más productivos.

La ausencia de colonias en algunos caminos o zonas alteradas se interpretó como indicio de condiciones microambientales inadecuadas.

El estudio de Saskatchewan también evaluó edad, densidad y composición de más de cien rodales, lo que refuerza la importancia de la estructura forestal.

**Conclusión útil:** Rainmapper no debería tratar el bosque como una simple máscara de presencia de árboles. Cobertura, densidad, musgos y alteración superficial pueden modular la aptitud.

## 2.5. Hospedadores

La literatura europea caracteriza *C. cibarius* como ectomicorrícico y asociado a varios árboles.

Entre los hospedadores documentados figuran:

- *Picea*;
- *Pinus*;
- *Fagus*;
- *Quercus*;
- *Castanea*;
- *Abies*;
- otros árboles ectomicorrícicos según región.

Baptista et al. registraron *C. cibarius* en castañares del nordeste de Portugal durante un seguimiento de cuatro años, dentro de una comunidad cuya fructificación fue analizada en relación con temperatura y precipitación.

El hecho de que aparezca con distintos hospedadores no significa que todos tengan la misma capacidad productiva.

**Conclusión útil:** el filtro ecológico debe admitir varios tipos de bosque y aprender pesos regionales a partir de observaciones.

## 2.6. Fenología europea y calentamiento

Kauserud et al. analizaron más de 700.000 registros de hongos de Austria, Noruega, Suiza y Reino Unido.

El estudio mostró cambios en la fenología de fructificación de numerosas especies otoñales:

- temporadas más largas;
- cambios en fecha de inicio;
- retrasos o adelantos según especie y región;
- relación con el alargamiento de la estación vegetativa.

*C. cibarius* figura entre las especies incluidas en las grandes bases de datos europeas utilizadas en este tipo de análisis.

Este trabajo no proporciona una función meteorológica simple para Rainmapper, pero demuestra que la fenología histórica no es estable.

**Conclusión útil:** las fechas tradicionales deben sustituirse por ventanas dinámicas ajustadas por clima y región.

## 2.7. Suelo, contaminación y declive poblacional

Jansen y Van Dobben analizaron el declive de *C. cibarius* en los Países Bajos.

Su conclusión fue que los cambios del suelo, posiblemente relacionados con contaminación atmosférica, acidificación y sucesión de la vegetación, explicaban mejor el declive que la recolección excesiva.

Esta evidencia es importante porque muestra que:

- el hábitat puede perder aptitud aunque el hospedador siga presente;
- los cambios químicos del suelo afectan a largo plazo;
- la ausencia de fructificación no siempre responde al tiempo de esa campaña.

**Conclusión útil:** Rainmapper debería separar aptitud estructural de largo plazo y activación meteorológica de corto plazo.

## 2.8. Recolección y alteración física

Egli et al. realizaron un experimento de larga duración en Suiza sobre recolección de hongos forestales.

Los tratamientos de cortar o arrancar no redujeron las cosechas futuras ni la riqueza de especies. Sin embargo, el pisoteo del suelo sí redujo el número de cuerpos fructíferos en parte del experimento.

Aunque el estudio no se limitó exclusivamente a *C. cibarius*, se incluye por su relevancia directa para la interpretación de presión recolectora en hongos forestales, y porque la literatura de conservación de rebozuelos lo utiliza como referencia.

**Conclusión útil:** no penalizar automáticamente una zona por recolección histórica, pero sí considerar compactación, caminos y perturbación física.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y tipo de bosque

Es un requisito fundamental.

El modelo debería distinguir:

- coníferas;
- frondosas;
- castañares;
- bosques mixtos;
- registros locales por taxón de *Cantharellus*.

No existe una jerarquía universal de hospedadores aplicable a toda Europa.

## 3.2. Humedad del suelo

La humedad del suelo aparece directamente en modelos específicos del grupo y representa una variable biológicamente próxima al micelio.

Debe calcularse o estimarse mediante:

- precipitación;
- textura;
- cobertura;
- evapotranspiración;
- pendiente;
- humedad antecedente.

No existe un valor universal de humedad óptima.

## 3.3. Precipitación

La precipitación cuenta con evidencia específica:

- acumulada durante semanas previas;
- a corto plazo antes de la fructificación;
- como alternativa a humedad del suelo en modelos de productividad.

Rainmapper debería mantener varias ventanas temporales y permitir que el modelo elija las relevantes por región.

## 3.4. Temperatura

La literatura específica respalda:

- temperatura del suelo;
- grados-día;
- temperatura del aire antes de la fructificación;
- efecto sobre fenología.

No se justifica una temperatura óptima única.

## 3.5. Fenología regional

La temporada cambia con:

- latitud;
- altitud;
- clima anual;
- hospedador;
- taxón dentro del complejo.

El día del año debe ser una variable flexible y no una regla excluyente.

## 3.6. Estructura forestal

Variables defendibles:

- densidad;
- cobertura;
- edad o desarrollo del rodal;
- presencia de musgo;
- alteración del suelo;
- caminos y compactación.

Los resultados concretos de pinares boreales no deben trasladarse literalmente a hayedos o robledales mediterráneos.

## 3.7. Estado del suelo

La evidencia de declive en Países Bajos demuestra que los cambios edáficos pueden modificar la capacidad de fructificación a largo plazo.

Variables útiles:

- pH;
- nitrógeno;
- materia orgánica;
- compactación;
- textura;
- contaminación o deposición nitrogenada cuando existan datos.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

Los estudios publican valores locales, pero no existe una cifra transferible a todos los taxones y regiones.

## 4.2. Número fijo de días hasta la aparición

Se han encontrado asociaciones con periodos de una o varias semanas, pero no un retardo universal.

## 4.3. Grados-día universales

Los grados-día funcionaron en Saskatchewan, pero no deben utilizarse directamente en la península ibérica sin calibración.

## 4.4. Densidad forestal óptima universal

Los pinares boreales productivos no representan todos los bosques europeos.

## 4.5. Musgo como requisito obligatorio

La presencia de musgo se relacionó con productividad en estudios concretos, pero no constituye una condición universal demostrada.

## 4.6. Viento, radiación y humedad relativa

No se localizaron funciones específicas y generalizables para la fructificación de *C. cibarius* sensu lato.

## 4.7. Efecto negativo de la recolección

La evidencia disponible no permite afirmar que cortar o arrancar carpóforos reduzca las cosechas futuras. La alteración física del suelo es una cuestión distinta.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- hospedador compatible;
- tipo de bosque;
- continuidad forestal;
- historial local;
- taxón probable dentro del complejo;
- alteración del suelo.

## 5.2. Componente hídrico

Incluir por separado:

- precipitación reciente;
- precipitación acumulada de varias semanas;
- humedad del suelo;
- duración del periodo seco;
- anomalía respecto a la climatología.

## 5.3. Componente térmico

Incluir:

- temperatura del aire;
- temperatura del suelo cuando esté disponible;
- acumulación térmica;
- anomalías;
- interacción con humedad.

## 5.4. Fenología

Usar:

- día del año;
- altitud;
- latitud o región climática;
- fecha media histórica;
- desplazamiento observado de la campaña.

## 5.5. Microhábitat

Incorporar cuando existan datos:

- cobertura;
- densidad;
- musgos;
- caminos;
- compactación;
- sotobosque;
- textura superficial.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- identificación y nivel de certeza;
- posibilidad de taxón distinto dentro del complejo;
- abundancia;
- hospedador;
- tipo de bosque;
- musgo;
- cobertura;
- alteración;
- meteorología previa;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- hospedador y tipo de bosque;
- precipitación reciente;
- humedad del suelo;
- temperatura;
- día del año;
- altitud;
- historial local de observaciones.

## Recomendables

- temperatura del suelo;
- precipitación acumulada de varias semanas;
- cobertura y densidad;
- musgo;
- textura;
- pH;
- caminos y compactación;
- anomalías climáticas.

## Experimentales

- grados-día regionales;
- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- deposición de nitrógeno;
- índices de vigor del hospedador;
- clasificación automática de taxones del complejo.

“Experimental” significa que la literatura seleccionada no permite asignarles un efecto generalizable para toda la entidad *C. cibarius* sensu lato.

---

# 7. Conclusiones

1. *Cantharellus cibarius* sensu lato agrupa evidencia procedente de varios taxones y regiones; la identidad taxonómica debe tratarse con cautela.

2. La asociación ectomicorrícica con árboles compatibles es un requisito fundamental.

3. Temperatura, humedad del suelo y precipitación cuentan con respaldo específico.

4. La señal meteorológica puede comenzar varias semanas antes de la primera fructificación.

5. No existe una cantidad mínima universal de lluvia ni un retardo fijo.

6. La temperatura del suelo y los grados-día son variables prometedoras, pero sus valores son regionales.

7. La estructura del bosque y el microhábitat modifican la productividad.

8. Musgos, densidad y menor alteración superficial se asociaron con mayor productividad en determinados pinares canadienses.

9. La fenología europea está cambiando y no debe modelarse mediante fechas rígidas.

10. Los cambios del suelo pueden causar declives prolongados incluso cuando el hospedador sigue presente.

11. La recolección por corte o arranque no cuenta con evidencia sólida de reducir futuras cosechas; el pisoteo y la compactación sí pueden ser relevantes.

12. Rainmapper debería calibrar parámetros por región, hábitat y, cuando sea posible, taxón concreto.

---

# 8. Bibliografía seleccionada

## 1. Ivanochko, G. et al. (2021)

**Título:** Characterization of chanterelle (*Cantharellus cibarius*) and pine mushrooms (*Tricholoma magnivelare*) in northern Saskatchewan.  
**Revista:** Canadian Journal of Plant Science.  
**DOI / página editorial:** https://cdnsciencepub.com/doi/10.1139/cjps-2021-0136  
**Página alternativa:** https://www.sciencedirect.com/org/science/article/abs/pii/S0008422021000579

**Aportación:** relaciona productividad con grados-día, temperatura del suelo y humedad o precipitación acumulada durante varias semanas antes de la primera aparición.

**Confianza:** alta para el sistema boreal estudiado; baja para transferir valores numéricos a Europa.

## 2. Rochon, C. et al. (2011)

**Título:** Ecology and productivity of *Cantharellus cibarius* var. *roseocanus* in two eastern Canadian jack pine stands.  
**Revista:** Botany, 89, 663–675.  
**DOI / página editorial:** https://cdnsciencepub.com/doi/abs/10.1139/b11-058  
**Copia:** https://www.researchgate.net/publication/237155304_Ecology_and_productivity_of_Cantharellus_cibarius_var_roseocanus_in_two_eastern_Canadian_jack_pine_stands

**Aportación:** correlaciona productividad con lluvia de la semana anterior y temperatura de aproximadamente dos semanas antes; analiza musgos, densidad, sotobosque y suelo.

**Confianza:** alta para el taxón y hábitat estudiados; indirecta para *C. cibarius* europeo.

## 3. Kauserud, H. et al. (2012)

**Título:** Warming-induced shift in European mushroom fruiting phenology.  
**Revista:** Proceedings of the National Academy of Sciences, 109, 14488–14493.  
**DOI:** https://doi.org/10.1073/pnas.1200789109  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC3437857/

**Aportación:** demuestra cambios amplios en la fenología de hongos otoñales europeos a partir de cientos de miles de registros.

**Confianza:** alta para tendencia fenológica general; no proporciona una función diaria exclusiva para *C. cibarius*.

## 4. Baptista, P. et al. (2010)

**Título:** Diversity and fruiting pattern of macrofungi associated with chestnut (*Castanea sativa*) in the Trás-os-Montes region, Northeast Portugal.  
**Revista:** Fungal Ecology, 3, 9–19.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S175450480900066X

**Aportación:** registra *C. cibarius* en castañares durante cuatro años y relaciona la dinámica de la comunidad con temperatura y lluvia.

**Confianza:** media-alta para hábitat y fenología regional; no modela exclusivamente la especie.

## 5. Jansen, E. y Van Dobben, H. F. (1987)

**Título:** Is decline of *Cantharellus cibarius* in the Netherlands due to air pollution?  
**Revista:** Ambio, 16, 211–213.  
**Consulta:** https://www.jstor.org/stable/4313357

**Aportación:** atribuye el declive principalmente a cambios del suelo, contaminación y sucesión, no a recolección excesiva.

**Confianza:** alta para el caso histórico estudiado; no es un modelo de floración anual.

## 6. Egli, S. et al. (2006)

**Título:** Mushroom picking does not impair future harvests – results of a long-term study in Switzerland.  
**Revista:** Biological Conservation, 129, 271–276.  
**Consulta:** https://ui.adsabs.harvard.edu/abs/2006BCons.129..271E/abstract  
**Copia:** https://www.researchgate.net/publication/222572829_Mushroom_picking_does_not_impair_future_harvests_-_Results_of_a_long-term_study_in_Switzerland

**Aportación:** demuestra que cortar o arrancar no redujo las futuras cosechas del conjunto estudiado; el pisoteo sí redujo carpóforos.

**Confianza:** alta para el efecto general de recolección en el experimento; no exclusiva de *C. cibarius*.

## 7. Buyck, B., Hofstetter, V. y Olariaga, I. (2016)

**Título:** Setting the record straight on North American *Cantharellus*.  
**Revista:** Cryptogamie, Mycologie.  
**Consulta / monografía relacionada:** https://www.researchgate.net/publication/313853913_Cantharellus_monografia_Europa

**Aportación:** delimita la diversidad europea y norteamericana y demuestra que muchos registros históricos de *C. cibarius* corresponden a especies distintas.

**Confianza:** alta para interpretación taxonómica; no aporta predicción meteorológica.

## 8. Moore, L. M. et al. (1989)

**Título:** Pure culture synthesis of ectomycorrhizas with *Cantharellus cibarius*.  
**Texto completo:** https://natuurtijdschriften.nl/pub/540739/ABN1989038003003.pdf

**Aportación:** aporta evidencia experimental de la naturaleza ectomicorrícica y de asociaciones con hospedadores.

**Confianza:** alta para simbiosis; no aporta parámetros de fructificación.

---

## Nota final sobre la evidencia

Se revisaron numerosos estudios norteamericanos identificados históricamente como *C. cibarius*. Solo se conservaron aquellos útiles para el concepto sensu lato y se señaló expresamente su limitación taxonómica.

No se utilizaron como base:

- cifras meteorológicas divulgativas;
- datos de otros rebozuelos sin relación clara con el complejo;
- estudios químicos o alimentarios;
- modelos de productividad total sin desglose útil;
- parámetros locales presentados como universales.

La evidencia permite construir un modelo razonable basado en hábitat, agua, temperatura y fenología, pero obliga a mantener una separación clara entre el *C. cibarius* europeo y otros taxones históricamente incluidos bajo el mismo nombre.
