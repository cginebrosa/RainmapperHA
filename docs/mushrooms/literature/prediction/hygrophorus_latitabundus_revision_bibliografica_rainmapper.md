# Predicción de floradas de *Hygrophorus latitabundus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Hygrophorus latitabundus* Britzelm.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia o menciona explícitamente *Hygrophorus latitabundus* y aporta información útil sobre fructificación, hábitat, hospedador, clima, estructura forestal o productividad.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Hygrophorus latitabundus* es limitada, pero existe al menos un estudio español que modeló su producción de carpóforos por separado y relacionó el rendimiento con variables climáticas y de estructura forestal.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica ligada principalmente a pinos.** La revisión taxonómica clásica de Arnolds encontró que prácticamente todas las colecciones estudiadas procedían de bosques naturales o plantados de *Pinus*. La literatura posterior mantiene esta asociación como el rasgo ecológico más sólido.

2. **La asociación con *Pinus* es mucho más consistente que con otras coníferas.** Existen algunas referencias antiguas próximas a *Picea*, pero el conjunto de la evidencia sitúa a la especie principalmente en pinares.

3. **La especie aparece en varios pinares mediterráneos y submediterráneos.** Está documentada en masas de *Pinus nigra*, *P. sylvestris*, *P. halepensis* y *P. pinaster* dentro de estudios forestales ibéricos.

4. **Existe una ecuación predictiva específica publicada para pinares prepirenaicos.** En ese modelo, la producción aumentó con la temperatura mínima del suelo de septiembre y con el excedente hídrico de septiembre, y disminuyó con el área basimétrica del rodal.

5. **Ese modelo no debe trasladarse literalmente a toda el área de distribución.** Procede de parcelas concretas del Solsonès y de un periodo de estudio limitado. Sus coeficientes son locales y no constituyen umbrales universales.

6. **La combinación de agua disponible y temperatura al comienzo del otoño es la evidencia meteorológica específica más útil.** La precipitación bruta no fue la única variable relevante; el modelo utilizó excedente hídrico, que integra precipitación y demanda evaporativa.

7. **La estructura del bosque también importa.** El área basimétrica tuvo un efecto negativo en el modelo específico, lo que sugiere que masas excesivamente densas pueden reducir la producción en ese sistema. No se ha demostrado una densidad óptima universal.

8. **La fenología es principalmente otoñal.** Los registros europeos la sitúan desde final de verano hasta noviembre o comienzos del invierno, según región y altitud.

9. **Los suelos calizos o ricos en bases aparecen asociados de forma frecuente.** Esta preferencia está bien descrita, pero no existe un intervalo universal de pH demostrado para la fructificación.

10. **No existe evidencia específica suficiente para fijar efectos independientes del viento, humedad relativa, radiación o déficit de presión de vapor.** Pueden contribuir al balance hídrico, pero no deben presentarse como predictores demostrados por separado.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Pinus* | Filtro ecológico principal | Muy alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Excedente hídrico o balance hídrico de comienzo de otoño | Señal climática principal | Alta |
| Temperatura mínima de comienzo de otoño | Modulador térmico | Alta |
| Área basimétrica o densidad del rodal | Modulador estructural | Media-alta |
| Suelo calizo o rico en bases | Modulador de aptitud | Media-alta |
| Día del año | Ventana fenológica | Alta |
| Altitud y orientación | Moduladores microclimáticos | Media |
| Precipitación y humedad del suelo | Componentes del estado hídrico | Media-alta |
| Gestión forestal reciente | Variable a calibrar | Media |

**Conclusión práctica:** Rainmapper debería modelar *H. latitabundus* mediante un filtro fuerte de pinares, una ventana otoñal, un componente hídrico que represente excedente de agua y una componente térmica basada especialmente en las mínimas de comienzo de otoño. La estructura del rodal debe incorporarse, pero los coeficientes publicados para el Solsonès no deben considerarse universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Hygrophorus latitabundus*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de otras especies de *Hygrophorus* sin resultados para *H. latitabundus*;
- trabajos químicos, nutricionales o de contaminación;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos de productividad total de hongos sin desglose por especie;
- datos antiguos bajo *Hygrophorus limacinus* cuya identidad no podía confirmarse;
- inventarios donde la especie aparecía solo en una lista sin información ecológica útil;
- referencias secundarias que repetían preferencias de hábitat sin aportar resultados originales.

Se seleccionaron **siete referencias principales**, priorizando trabajos taxonómicos, ecológicos y forestales que aportan información directa sobre hospedador, productividad o variables ambientales.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Asociación con pinos

Arnolds revisó el grupo de especies próximas a *Hygrophorus olivaceoalbus* y estudió once colecciones de *H. latitabundus*.

El resumen ecológico fue claro:

- todas las referencias bibliográficas principales procedían de bosques naturales o plantados de *Pinus*;
- ocho de las once colecciones estudiadas se asociaban a *Pinus sylvestris*;
- dos colecciones belgas se habían atribuido a proximidad de *Picea*;
- una colección carecía de información de hábitat.

La evidencia acumulada favorece claramente a *Pinus*.

**Conclusión útil:** la presencia de pino debe actuar como filtro ecológico principal. Las referencias con *Picea* son minoritarias y antiguas, por lo que no justifican tratar todos los bosques de coníferas como igualmente aptos.

## 2.2. Problemas de identificación histórica

La literatura antigua utilizó con frecuencia nombres como:

- *Hygrophorus limacinus* sensu auct.;
- *Hygrophorus olivaceoalbus* var. *obesus*;
- materiales confundidos con *H. olivaceoalbus* o *H. persoonii*.

Arnolds mostró diferencias morfológicas, microscópicas y ecológicas entre estos taxones.

Bellanger et al. confirmaron posteriormente, mediante filogenia molecular, la delimitación de *H. latitabundus* dentro de la sección Olivaceoumbrini.

**Conclusión útil:** las observaciones históricas deben validarse antes de incorporarlas a Rainmapper. Las confusiones con especies de *Picea* o frondosas pueden distorsionar el perfil ecológico.

## 2.3. Modelo predictivo específico del prepirineo

Martínez de Aragón et al. estudiaron la productividad de hongos ectomicorrícicos y saprótrofos comestibles en pinares del prepirineo español.

Las parcelas se situaron en masas de:

- *Pinus nigra*;
- *Pinus sylvestris*;
- *Pinus halepensis*.

Para *H. latitabundus* publicaron una ecuación específica en la que la producción se relacionó con:

- temperatura mínima media del suelo en septiembre;
- excedente hídrico de septiembre;
- área basimétrica.

El signo de las relaciones fue:

- positivo para temperatura mínima de septiembre;
- positivo para excedente hídrico de septiembre;
- negativo para área basimétrica.

El modelo alcanzó una capacidad explicativa moderada, no total.

**Conclusión útil:** existe respaldo directo para incluir temperatura mínima, balance hídrico de septiembre y estructura del rodal.

## 2.4. Qué significa el excedente hídrico

El excedente hídrico utilizado en el estudio no equivale simplemente a precipitación.

Representa la parte del agua disponible una vez considerada la demanda atmosférica y el balance entre:

- precipitación;
- evapotranspiración potencial;
- déficit o superávit de agua.

Esto es importante porque dos episodios con la misma lluvia pueden producir estados hídricos diferentes según temperatura y evaporación.

**Conclusión útil:** Rainmapper debería preferir un índice de balance hídrico a la lluvia aislada cuando disponga de datos suficientes.

## 2.5. Temperatura mínima de septiembre

La temperatura mínima media del suelo en septiembre apareció con efecto positivo en el modelo específico.

Este resultado puede interpretarse como evidencia de que:

- un comienzo de otoño demasiado frío puede limitar o retrasar la actividad;
- la especie responde a condiciones térmicas del suelo;
- las mínimas pueden aportar más información que la temperatura media.

No debe concluirse que exista una temperatura mínima óptima universal. El estudio produjo un coeficiente local para un conjunto concreto de pinares.

**Conclusión útil:** incluir temperatura mínima del suelo o una estimación de temperatura mínima cercana al suelo durante el comienzo de la campaña.

## 2.6. Área basimétrica

El área basimétrica mostró un efecto negativo en la ecuación específica.

El área basimétrica resume parcialmente:

- densidad;
- tamaño de los árboles;
- competencia;
- cierre del dosel;
- cantidad de raíces hospedadoras;
- microclima.

La relación negativa puede indicar que rodales muy densos fueron menos productivos en ese sistema. No demuestra que un bosque abierto sea siempre mejor, ni que exista un valor óptimo universal.

**Conclusión útil:** incorporar estructura forestal como variable continua y calibrarla por región y especie de pino.

## 2.7. Presencia en *Pinus pinaster*

Estudios posteriores de productividad de hongos en masas mediterráneas de *Pinus pinaster* incluyen expresamente *H. latitabundus* entre las especies comestibles y comercializables registradas.

Estos trabajos modelan generalmente la productividad total o grupos de especies, no la respuesta individual de *H. latitabundus*.

**Conclusión útil:** *P. pinaster* debe considerarse hospedador o hábitat compatible, pero no se deben atribuir a la especie los coeficientes de modelos agregados.

## 2.8. Presencia en *Pinus nigra*

La especie aparece explícitamente en:

- estudios de pinares prepirenaicos de *Pinus nigra*;
- inventarios de *Pinus nigra* en Croacia;
- registros griegos bajo *Pinus nigra* mezclado con otras especies.

La evidencia de *P. nigra* es consistente, especialmente en regiones mediterráneas y submediterráneas.

**Conclusión útil:** *Pinus nigra* debe recibir un peso alto en el perfil ecológico.

## 2.9. Fenología

Los registros europeos y mediterráneos sitúan la fructificación principalmente:

- desde final de verano;
- durante otoño;
- en algunos lugares hasta noviembre o diciembre.

El estudio griego registra recolecciones a finales de noviembre y comienzos del invierno.

**Conclusión útil:** la ventana fenológica debe centrarse en otoño, pero permitir desplazamientos por altitud y clima regional.

## 2.10. Suelos calizos

La especie se asocia con frecuencia a:

- suelos calizos;
- terrenos ricos en bases;
- pinares sobre sustratos carbonatados.

La literatura taxonómica y ecológica repite esta preferencia.

Sin embargo, no se ha localizado un estudio específico que defina:

- pH mínimo;
- pH óptimo;
- concentración de carbonatos;
- exclusión de sustratos silíceos.

**Conclusión útil:** usar litología calcárea y pH estimado como moduladores, no como filtros absolutos.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador

El factor más sólido es la presencia de *Pinus*.

Rainmapper debería distinguir:

- *Pinus nigra*;
- *Pinus sylvestris*;
- *Pinus halepensis*;
- *Pinus pinaster*;
- otros pinos con observaciones regionales;
- coníferas no pino, con aptitud mucho más incierta.

## 3.2. Balance hídrico de comienzo de otoño

El excedente hídrico de septiembre cuenta con evidencia específica.

Variables operativas:

- precipitación;
- evapotranspiración potencial;
- humedad antecedente;
- balance hídrico;
- déficit acumulado;
- excedente mensual o móvil.

La ventana exacta debe ajustarse regionalmente. En zonas más altas o más frías, el periodo equivalente puede desplazarse.

## 3.3. Temperatura mínima

La temperatura mínima del suelo de septiembre fue informativa en el modelo prepirenaico.

Si Rainmapper no dispone de temperatura del suelo, puede estimarla mediante:

- temperatura mínima del aire;
- cobertura;
- radiación;
- humedad;
- altitud;
- tipo de suelo.

Esa estimación debe mantenerse separada de una medición real.

## 3.4. Estructura forestal

El área basimétrica debe incorporarse cuando existan datos.

Posibles sustitutos:

- cobertura de copa;
- densidad de pies;
- altura dominante;
- biomasa;
- edad del rodal;
- datos LiDAR.

No debe asumirse una relación lineal universal.

## 3.5. Fenología

Variables recomendadas:

- día del año;
- fecha histórica local;
- altitud;
- especie de pino;
- anomalía térmica;
- llegada del excedente hídrico otoñal.

## 3.6. Suelo

Factores útiles:

- litología;
- pH estimado;
- carbonatos;
- textura;
- capacidad de retención;
- profundidad;
- drenaje.

La preferencia calcícola es suficientemente consistente para modular la aptitud, pero no para excluir todo suelo no calcáreo.

## 3.7. Historial local

La especie puede ser rara a escala regional y abundante en rodales concretos.

El historial debería incluir:

- observaciones confirmadas;
- frecuencia;
- abundancia;
- años productivos;
- especie de pino;
- suelo;
- estructura;
- gestión reciente.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Temperatura mínima exacta

El modelo español publicó una relación cuantitativa, pero su coeficiente no debe utilizarse como umbral universal.

## 4.2. Excedente hídrico exacto

La relación es específica del sistema prepirenaico y del periodo de estudio.

## 4.3. Densidad óptima del bosque

El efecto negativo del área basimétrica no demuestra que cuanto más abierto, mejor.

## 4.4. Exclusividad absoluta de *Pinus*

La evidencia favorece fuertemente a los pinos, pero existen algunas referencias antiguas próximas a *Picea*. No existe base suficiente para afirmar una exclusividad absoluta en toda Europa.

## 4.5. pH óptimo universal

No se ha localizado un intervalo cuantitativo validado.

## 4.6. Viento, radiación y humedad relativa

No existen funciones específicas generalizables para la fructificación de la especie.

## 4.7. Número fijo de días después de la lluvia

No se ha identificado un retardo universal.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- presencia de *Pinus*;
- especie de pino;
- suelo calizo o rico en bases;
- continuidad forestal;
- historial local;
- ausencia de perturbación severa.

## 5.2. Componente hídrico

Incluir:

- precipitación reciente;
- evapotranspiración;
- balance hídrico;
- excedente hídrico;
- humedad del suelo;
- déficit antecedente.

## 5.3. Componente térmico

Incluir:

- temperatura mínima;
- temperatura mínima cercana al suelo;
- temperatura media;
- anomalía térmica;
- primeras heladas.

## 5.4. Estructura del rodal

Incluir:

- área basimétrica;
- cobertura;
- densidad;
- altura;
- edad;
- intervenciones recientes.

## 5.5. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- desplazamiento de la campaña.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- identificación fiable;
- abundancia;
- especie de pino;
- litología;
- pH estimado;
- estructura forestal;
- meteorología previa;
- esfuerzo de búsqueda;
- perturbaciones.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- especie de *Pinus*;
- tipo de pinar;
- historial local;
- balance hídrico de comienzo de otoño;
- temperatura mínima;
- día del año;
- altitud;
- área basimétrica o sustituto estructural.

## Recomendables

- precipitación;
- evapotranspiración;
- humedad del suelo;
- litología calcárea;
- pH estimado;
- cobertura;
- densidad;
- orientación;
- pendiente.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- déficit de presión de vapor;
- temperatura del suelo estimada;
- índices de vigor del arbolado;
- tiempo desde gestión forestal;
- modelos regionales separados por especie de pino.

“Experimental” significa que la literatura específica no permite asignarles todavía un efecto universal sobre la fructificación de *H. latitabundus*.

---

# 7. Conclusiones

1. *Hygrophorus latitabundus* está ligado principalmente a pinares.

2. *Pinus sylvestris* y *Pinus nigra* cuentan con evidencia especialmente sólida.

3. *Pinus halepensis* y *Pinus pinaster* también aparecen en estudios ibéricos donde la especie fue registrada.

4. Existe un modelo predictivo específico publicado para pinares prepirenaicos.

5. Ese modelo relacionó positivamente la producción con temperatura mínima del suelo y excedente hídrico de septiembre.

6. El área basimétrica mostró un efecto negativo en el mismo modelo.

7. Los coeficientes del modelo son locales y no deben trasladarse como reglas universales.

8. La especie fructifica principalmente en otoño.

9. Los suelos calizos o ricos en bases constituyen una preferencia ecológica consistente, pero no un requisito absoluto demostrado.

10. No existe evidencia suficiente para fijar un número de días post-lluvia, una temperatura óptima universal o un umbral hídrico general.

11. La estructura forestal y el balance hídrico deben formar parte del modelo.

12. Rainmapper debería combinar hospedador, balance hídrico, mínimas térmicas, fenología, suelo e historial local.

---

# 8. Bibliografía seleccionada

## 1. Arnolds, E. (1979)

**Título:** Notes on *Hygrophorus* — III. The group of *Hygrophorus olivaceoalbus*.  
**Revista:** Persoonia, 10, 357–382.  
**Texto completo:** https://repository.naturalis.nl/pub/532005/PERS1979010003005.pdf

**Aportación:** revisión taxonómica y ecológica fundamental. Documenta la asociación dominante de *H. latitabundus* con bosques naturales o plantados de *Pinus*.

**Confianza:** muy alta para identidad y hospedador.

## 2. Martínez de Aragón, J., Bonet, J. A., Fischer, C. R. y Colinas, C. (2007)

**Título:** Productivity of ectomycorrhizal and selected edible saprotrophic fungi in pine forests of the pre-Pyrenees mountains, Spain: predictive equations for forest management of mycological resources.  
**Revista:** Forest Ecology and Management, 252, 239–256.  
**Consulta:** https://www.academia.edu/30016998/Productivity_of_ectomycorrhizal_and_selected_edible_saprotrophic_fungi_in_pine_forests_of_the_pre_Pyrenees_mountains_Spain_Predictive_equations_for_forest_management_of_mycological_resources  
**Tesis relacionada con tablas y ecuaciones:** https://www.researchgate.net/profile/Martinez-De-Aragon-Juan/publication/200017819_Produccion_de_esporocarpos_de_hongos_ectomicorricicos_y_valoracion_socioeconomica_Respuesta_de_estas_comunidades_a_incendios_forestales/links/58b6e7bca6fdcc2d14d6e7ac/Produccion-de-esporocarpos-de-hongos-ectomicorricicos-y-valoracion-socioeconomica-Respuesta-de-estas-comunidades-a-incendios-forestales.pdf

**Aportación:** fuente predictiva principal. Publica una ecuación específica para *H. latitabundus* basada en temperatura mínima de septiembre, excedente hídrico de septiembre y área basimétrica.

**Confianza:** alta para los pinares y periodo estudiados; no transferible directamente a otras regiones.

## 3. Bellanger, J.-M. et al. (2021)

**Título:** *Hygrophorus* sect. Olivaceoumbrini: new boundaries, extended phylogenetic diversity and key to European taxa.  
**Revista:** Persoonia, 46, 272–312.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9311391/

**Aportación:** confirma molecularmente la delimitación de *H. latitabundus* y ayuda a separar registros válidos de especies próximas.

**Confianza:** muy alta para taxonomía; no aporta un modelo meteorológico.

## 4. Herrero, C. et al. (2019)

**Título:** Predicting mushroom productivity from long-term field-data series in Mediterranean *Pinus pinaster* forests in the context of climate change.  
**Revista:** Forests, 10, 206.  
**Texto completo:** https://www.mdpi.com/1999-4907/10/3/206

**Aportación:** incluye expresamente *H. latitabundus* entre las especies comestibles de pinares de *P. pinaster* y aporta contexto de productividad forestal y cambio climático.

**Confianza:** media para la especie concreta; los modelos principales son agregados.

## 5. de-Miguel, S. et al. (2014)

**Título:** Impact of forest management intensity on landscape-level mushroom productivity: a regional model-based scenario analysis.  
**Revista:** Forest Ecology and Management.  
**Texto completo:** https://cris.ctfc.cat/docs/upload/27_431_De-Miguel%20et%20al-%202014.pdf

**Aportación:** incluye *H. latitabundus* entre las especies consideradas en análisis regionales de producción y gestión de pinares.

**Confianza:** media para gestión; no desglosa una función meteorológica exclusiva de la especie.

## 6. Dimou, D. M. et al. (2008)

**Título:** Mycodiversity studies in selected ecosystems of Greece: IV. Macrofungi from *Abies cephalonica* forests and other intermixed tree species.  
**Revista:** Mycotaxon, 104.  
**Texto completo:** https://www.mycotaxon.com/resources/checklists/dimou-v104-checklist.pdf

**Aportación:** registra *H. latitabundus* a finales de noviembre bajo *Pinus nigra* mezclado con otras especies y confirma su fenología tardía.

**Confianza:** media-alta para hábitat y fecha local; no aporta predicción cuantitativa.

## 7. de Román, M. y Boa, E. (2004)

**Título:** Collection, marketing and cultivation of edible fungi in Spain.  
**Revista:** Micología Aplicada Internacional, 16, 25–33.  
**Texto completo:** https://www.redalyc.org/pdf/685/68516201.pdf

**Aportación:** documenta la importancia comercial de *H. latitabundus* en España y su asociación con pinares.

**Confianza:** media para contexto de aprovechamiento y distribución; no es un estudio predictivo.

---

## Nota final sobre la evidencia

La literatura específica de *H. latitabundus* es más reducida que la de *Boletus edulis*, pero contiene un elemento especialmente valioso: una ecuación de productividad desarrollada expresamente para la especie.

Ese modelo constituye la mejor evidencia disponible para seleccionar variables, pero no para fijar valores universales. Rainmapper debería conservar la dirección de las relaciones como hipótesis iniciales bien documentadas:

- mayor temperatura mínima al inicio del otoño;
- mayor excedente hídrico;
- menor área basimétrica dentro del rango observado.

Los coeficientes, umbrales y forma exacta de esas relaciones deben recalibrarse con datos propios y por región.
