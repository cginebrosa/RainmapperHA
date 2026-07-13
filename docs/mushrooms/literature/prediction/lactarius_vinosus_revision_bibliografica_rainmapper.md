# Predicción de floradas de *Lactarius vinosus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Lactarius vinosus* (Quél.) Bataille  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Lactarius vinosus* y aporta información útil sobre fructificación, micelio, humedad del suelo, temperatura, estructura forestal, gestión o taxonomía.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específica sobre *Lactarius vinosus* es más útil para comprender la dinámica de su micelio en el suelo que para predecir directamente el día de aparición de los carpóforos. Existe un estudio anual muy detallado, basado en miles de muestras de suelo y mediciones continuas de humedad y temperatura, además de trabajos sobre detección de esporas, gestión forestal y productividad del grupo comercial de los níscalos.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica claramente diferenciada de *Lactarius sanguifluus*.** Los análisis morfológicos y moleculares justifican tratarla como especie independiente. La identificación correcta es esencial porque ambas pueden compartir pinares y campañas.

2. **Está asociada principalmente a pinos.** Los estudios ecológicos y forestales españoles la sitúan en pinares mediterráneos, especialmente en masas de *Pinus pinaster*. La bibliografía taxonómica europea también la vincula a *Pinus*.

3. **La humedad y la temperatura del suelo controlan fuertemente la biomasa del micelio extrarradical.** En un seguimiento de doce meses, el micelio mostró máximos en primavera y otoño y reducciones bajo temperaturas bajas o bajo la combinación de temperaturas altas y baja humedad.

4. **Las condiciones cálidas y secas reducen el micelio durante el verano.** El estudio específico concluyó que el aumento de la sequía estival puede limitar el crecimiento de la especie.

5. **Un invierno más cálido puede prolongar la actividad micelial.** Los modelos exploratorios del mismo estudio sugirieron mayor actividad durante invierno–primavera bajo condiciones más templadas, sin que ello implique necesariamente una mayor fructificación.

6. **La dinámica subterránea no es equivalente a la producción de carpóforos.** El micelio puede presentar dos máximos anuales, mientras que la fructificación visible se concentra principalmente en otoño.

7. **La detección de esporas puede anticipar o confirmar la emergencia.** Un estudio combinó trampas de esporas, qPCR y observaciones de campo y encontró una relación fuerte entre concentración de esporas y aparición de carpóforos de *L. vinosus*.

8. **La gestión forestal modifica la producción del grupo comercial de los níscalos.** En pinares de *Pinus pinaster*, los aclareos aumentaron a corto plazo la producción del grupo *Lactarius deliciosus*, que incluía expresamente *L. vinosus*. Sin embargo, esos resultados no permiten atribuir toda la respuesta a esta especie.

9. **Los efectos de los aclareos pueden ser temporales y depender del clima.** Estudios de seguimiento prolongado mostraron cambios de corta duración en la comunidad fúngica y una interacción con la temperatura de septiembre y octubre.

10. **No existe un umbral universal de lluvia, humedad, temperatura o días post-lluvia.** Los resultados específicos describen relaciones continuas y estacionales, no una receta meteorológica simple.

11. **El historial local y la estructura del pinar deben tener un peso alto.** La especie puede mostrar gran abundancia en parcelas concretas y escasa presencia en otras aparentemente similares.

12. **La ausencia de carpóforos no implica ausencia del hongo.** El micelio puede permanecer activo en el suelo fuera de la ventana visible de fructificación.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Pinus* compatible | Filtro ecológico principal | Muy alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Humedad del suelo | Variable climática principal | Muy alta |
| Temperatura del suelo | Modulador climático principal | Muy alta |
| Interacción calor × sequedad | Penalización estival | Alta |
| Día del año | Ventana fenológica otoñal | Alta |
| Estructura y gestión del pinar | Modulador de productividad | Media-alta |
| Precipitación reciente y acumulada | Entrada del balance hídrico | Media-alta |
| Esporas aerotransportadas, si existen | Indicador avanzado de emergencia | Alta |
| Altitud y orientación | Moduladores microclimáticos | Media |

**Conclusión práctica:** Rainmapper debería modelar *L. vinosus* mediante un filtro fuerte de pinares, un componente de humedad y temperatura del suelo, una penalización por calor seco, una fenología otoñal y un peso alto del historial local. La literatura específica permite describir bien la dinámica micelial, pero no proporciona umbrales universales para la aparición de carpóforos.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Lactarius vinosus*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de *Lactarius sanguifluus* sin resultados separados;
- trabajos del grupo comercial de los níscalos cuando no permitían identificar la contribución de *L. vinosus*, salvo que se indicara expresamente esta limitación;
- publicaciones de composición química, gastronomía o contaminantes;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos de producción total de hongos sin desglose de especie;
- registros antiguos cuya identidad taxonómica era dudosa;
- trabajos sobre otras especies de la sección *Deliciosi*.

Se seleccionaron **ocho referencias principales**, priorizando estudios específicos de micelio, humedad, temperatura, detección de esporas, taxonomía y gestión de pinares.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Separación de *Lactarius sanguifluus*

Nuytinck y Verbeken analizaron materiales atribuidos a *L. sanguifluus* y *L. vinosus* mediante:

- caracteres macroscópicos;
- ornamentación esporal;
- secuencias ITS;
- análisis filogenéticos.

El trabajo concluyó que *L. vinosus* debe tratarse como una especie separada.

Las diferencias más relevantes para observaciones de campo incluyen:

- coloración más intensamente vinosa;
- menor presencia de tonos anaranjados;
- diferencias en ornamentación de las esporas;
- virajes y color del látex;
- separación molecular.

**Conclusión útil:** no deben mezclarse observaciones de ambas especies. Los registros sin fotografías, látex o confirmación fiable deben marcarse como dudosos.

## 2.2. Asociación con pinos

Los estudios específicos de ecología y gestión de *L. vinosus* en Cataluña y el nordeste de España se desarrollaron en pinares mediterráneos.

El contexto mejor documentado es:

- *Pinus pinaster*;
- rodales de aproximadamente cincuenta años en algunos estudios;
- masas sometidas a distintos niveles de aclareo;
- clima mediterráneo con sequía estival.

La literatura taxonómica europea sitúa igualmente la especie bajo *Pinus*.

**Conclusión útil:** la presencia de pino debe actuar como filtro ecológico fuerte. Rainmapper debería registrar la especie de pino y no limitarse a la categoría genérica “coníferas”.

## 2.3. Seguimiento anual del micelio

Castaño et al. cuantificaron el micelio extrarradical de *L. vinosus* durante doce meses.

El diseño fue especialmente sólido:

- 28 parcelas;
- 2.688 muestras de suelo;
- muestreo mensual;
- cuantificación mediante qPCR;
- temperatura y humedad del suelo registradas cada dos horas.

La biomasa de micelio varió de forma significativa a lo largo del año.

**Conclusión útil:** la actividad subterránea es altamente estacional y responde a condiciones locales de suelo.

## 2.4. Dos máximos estacionales

El estudio encontró dos máximos principales de biomasa micelial:

- primavera;
- otoño.

Los mínimos aparecieron:

- durante invierno frío;
- durante verano seco;
- con una reducción marcada en determinadas fases del final de otoño.

La existencia de un máximo primaveral no implica una florada primaveral equivalente. La biomasa del micelio y la formación de carpóforos son procesos relacionados, pero distintos.

**Conclusión útil:** Rainmapper no debe interpretar directamente un índice de actividad micelial como probabilidad de carpóforos visibles.

## 2.5. Humedad del suelo

La humedad del suelo se correlacionó significativamente con la biomasa de *L. vinosus*.

Los resultados mostraron:

- mayor biomasa bajo condiciones húmedas;
- reducción de biomasa cuando la humedad era baja;
- interacción con temperatura;
- descenso acusado bajo combinación de calor y sequedad.

Esta es la evidencia ambiental más directa y sólida para la especie.

**Conclusión útil:** la humedad del suelo debe ser una variable prioritaria y separada de la precipitación bruta.

## 2.6. Temperatura del suelo

La temperatura también estuvo significativamente relacionada con la biomasa micelial.

La respuesta no fue lineal:

- temperaturas demasiado bajas redujeron la biomasa;
- temperaturas altas podían ser favorables si existía humedad suficiente;
- temperaturas altas combinadas con baja humedad fueron desfavorables.

**Conclusión útil:** Rainmapper debe representar la interacción temperatura × humedad y evitar una función térmica independiente demasiado simple.

## 2.7. Sequía estival

Los autores concluyeron que condiciones más cálidas y secas reducen el micelio durante el verano.

Los modelos exploratorios sugirieron que:

- la prolongación de la sequía impediría el crecimiento estival;
- el calentamiento sin agua disponible no sería favorable;
- el cambio climático podría alterar el ciclo anual.

No debe inferirse una pérdida directa y proporcional de carpóforos sin datos adicionales.

**Conclusión útil:** utilizar duración e intensidad de sequía estival como penalización del potencial de campaña.

## 2.8. Invierno más templado

Las simulaciones del estudio indicaron que un aumento de temperatura podría ampliar la actividad durante invierno–primavera.

Esto se refiere a biomasa micelial en el suelo, no a aparición de setas.

La consecuencia defendible es que:

- el ciclo anual puede desplazarse;
- el hongo puede mantener actividad durante más tiempo;
- el efecto del calentamiento depende de la estación y de la humedad.

**Conclusión útil:** la anomalía térmica debe interpretarse por estación, no como un efecto anual único.

## 2.9. Alta renovación del micelio

El estudio estimó una renovación media del micelio de aproximadamente siete veces por año.

Este resultado muestra:

- alta actividad biológica;
- producción y desaparición rápida de biomasa;
- sensibilidad a cambios mensuales;
- dificultad de extrapolar una medición puntual a toda la campaña.

**Conclusión útil:** una observación de micelio en un momento concreto necesita contexto temporal.

## 2.10. Detección de emergencia mediante esporas

Castaño et al. desarrollaron un método que combinaba:

- trampas de esporas;
- cuantificación molecular por qPCR;
- observación semanal de carpóforos;
- parcelas con distintos niveles de productividad.

Para *L. vinosus* se detectó una relación fuerte entre concentración de esporas y emergencia de carpóforos.

El estudio demuestra que:

- las esporas atmosféricas pueden servir como indicador de actividad reproductiva;
- la señal molecular puede complementar el muestreo visual;
- la detección puede reducir el efecto de observaciones incompletas.

La utilidad operativa depende de instalar muestreadores, algo difícil a gran escala.

**Conclusión útil:** considerar las esporas como indicador avanzado en parcelas piloto o estaciones de calibración.

## 2.11. Fructificación y micelio no son equivalentes

La literatura específica muestra tres niveles distintos:

1. micelio presente en el suelo;
2. producción de primordios y carpóforos;
3. liberación de esporas.

Cada nivel responde a procesos diferentes.

Una zona puede tener:

- micelio sin carpóforos;
- carpóforos aún no detectados;
- esporas procedentes de parcelas cercanas;
- producción eliminada por recolección antes del muestreo.

**Conclusión útil:** el modelo debe distinguir potencial biológico, fructificación y observación.

## 2.12. Aclareo forestal

Bonet et al. estudiaron el efecto inmediato de aclareos en pinares de *Pinus pinaster*.

El grupo comercial analizado incluía expresamente:

- *L. deliciosus*;
- *L. sanguifluus*;
- *L. semisanguifluus*;
- *L. salmonicolor*;
- *L. vinosus*.

Los rodales aclarados fueron más productivos para el grupo durante los primeros años.

Sin embargo:

- no se publicó la respuesta separada de *L. vinosus*;
- el efecto fue de grupo;
- la contribución de cada especie pudo variar;
- no se demostró un efecto permanente.

**Conclusión útil:** el aclareo debe tratarse como variable candidata, no como regla positiva específica de la especie.

## 2.13. Respuesta a largo plazo de la comunidad

Collado et al. analizaron once años de seguimiento semanal en 28 parcelas con distintas intensidades de aclareo.

Los resultados generales fueron:

- cambios de composición a corto plazo;
- mayor efecto bajo aclareos intensos;
- interacción con temperatura de septiembre y octubre;
- ausencia de pérdida de diversidad total de carpóforos;
- efectos temporales de la gestión.

El estudio identificó respuestas particulares dentro del grupo de los níscalos, pero no publicó una ecuación exclusiva para *L. vinosus*.

**Conclusión útil:** la gestión y el clima interactúan; el efecto de una intervención no debe modelarse sin considerar la meteorología posterior.

## 2.14. Posibles respuestas divergentes sobre y bajo el suelo

Trabajos posteriores en el mismo sistema mediterráneo observaron que:

- la producción de carpóforos;
- la biomasa micelial;
- la composición de la comunidad;

pueden responder de forma diferente a los tratamientos.

Esto impide asumir que un aumento de carpóforos refleje necesariamente un aumento equivalente de micelio.

**Conclusión útil:** Rainmapper debe mantener separados los indicadores de producción visible y actividad subterránea.

## 2.15. Fenología visible

Los estudios mediterráneos sitúan la fructificación principalmente en otoño.

En muestreos semanales de pinares mediterráneos, *L. vinosus* aparece entre las especies más abundantes al inicio o durante la primera parte del periodo otoñal de muestreo.

No existe una fecha universal de inicio.

**Conclusión útil:** usar una ventana otoñal flexible, ajustada por altitud, región y condiciones hídricas.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador

El filtro ecológico principal debe ser *Pinus*.

Variables:

- especie de pino;
- continuidad del pinar;
- cobertura;
- edad;
- estado sanitario;
- gestión reciente.

## 3.2. Humedad del suelo

Es la variable ambiental específica más sólida.

Rainmapper debería incluir:

- humedad volumétrica;
- índice de balance hídrico;
- duración de sequía;
- anomalía de humedad;
- humedad a distintas profundidades si existe.

No debe sustituirse automáticamente por precipitación acumulada.

## 3.3. Temperatura del suelo

Variables recomendadas:

- media;
- mínima;
- máxima;
- anomalía;
- interacción con humedad;
- duración de condiciones cálidas y secas.

## 3.4. Interacción calor × sequedad

La penalización más defendible no es “calor” por sí solo, sino:

- temperatura alta;
- humedad baja;
- persistencia de ambas condiciones.

Esta interacción debería ser explícita.

## 3.5. Sequía antecedente

Variables útiles:

- días secos consecutivos;
- déficit hídrico acumulado;
- anomalía de humedad estival;
- duración de la sequía;
- fecha de recuperación hídrica.

## 3.6. Fenología

Combinar:

- día del año;
- altitud;
- fecha histórica local;
- humedad del suelo;
- temperatura;
- primera recuperación otoñal.

## 3.7. Estructura forestal

Incluir:

- área basimétrica;
- cobertura;
- densidad;
- edad;
- volumen;
- aclareos;
- años desde intervención.

La dirección del efecto debe calibrarse localmente.

## 3.8. Micelio

Cuando exista muestreo molecular:

- biomasa;
- fecha;
- profundidad;
- parcela;
- tendencia mensual;
- relación con humedad y temperatura.

## 3.9. Esporas

En estaciones piloto:

- concentración de esporas;
- fecha;
- viento;
- distancia a colonias;
- correlación con carpóforos.

La señal puede indicar emergencia, pero no necesariamente localizar con precisión la parcela productora.

## 3.10. Historial local

Debe incluir:

- presencia confirmada;
- abundancia;
- calidad taxonómica;
- especie de pino;
- estructura;
- fechas;
- micelio o esporas, si existen;
- tratamientos forestales.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral universal específico de la especie.

## 4.2. Número fijo de días después de la lluvia

No se ha demostrado un retardo general.

## 4.3. Temperatura óptima

La respuesta depende de la humedad y de la estación.

## 4.4. Efecto positivo general del aclareo

Los resultados más claros proceden del grupo comercial de los níscalos.

## 4.5. Relación directa entre micelio y carpóforos

La presencia de micelio no garantiza fructificación visible.

## 4.6. Umbral de humedad del suelo

La relación es clara, pero no existe un valor transferible a todas las regiones.

## 4.7. Viento, radiación y humedad relativa

No existen funciones específicas y universalmente validadas para la producción de carpóforos.

## 4.8. Fenología idéntica en todos los pinares

La fecha depende de altitud, clima, especie de pino y humedad.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- presencia de *Pinus*;
- especie de pino;
- continuidad del rodal;
- historial local;
- estructura forestal;
- ausencia de perturbación severa.

## 5.2. Componente hídrico

Incluir:

- humedad del suelo;
- precipitación;
- déficit acumulado;
- días secos;
- balance hídrico;
- recuperación otoñal.

## 5.3. Componente térmico

Incluir:

- temperatura del suelo;
- temperatura del aire;
- máximas;
- mínimas;
- anomalías;
- interacción con humedad.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- primera recuperación hídrica.

## 5.5. Estructura y gestión

Incluir:

- área basimétrica;
- cobertura;
- densidad;
- edad;
- aclareos;
- años desde intervención.

## 5.6. Componente subterráneo

Cuando exista:

- biomasa micelial;
- tendencia;
- humedad y temperatura asociadas;
- fecha de muestreo.

## 5.7. Componente reproductivo

En estaciones experimentales:

- esporas;
- fecha;
- concentración;
- observación de carpóforos;
- viento y distancia.

## 5.8. Evidencia observacional

Cada registro debería incluir:

- identificación fiable;
- fotografías;
- látex y virajes;
- fecha y coordenadas;
- abundancia;
- especie de pino;
- humedad del suelo;
- estructura;
- meteorología previa;
- gestión;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- identificación fiable;
- especie de *Pinus*;
- tipo de pinar;
- historial local;
- humedad del suelo;
- temperatura del suelo o estimada;
- día del año;
- altitud;
- duración de sequía.

## Recomendables

- precipitación;
- balance hídrico;
- cobertura;
- área basimétrica;
- densidad;
- edad;
- aclareos;
- anomalías térmicas;
- fecha de recuperación otoñal.

## Experimentales

- biomasa micelial;
- concentración de esporas;
- viento;
- radiación;
- humedad relativa;
- déficit de presión de vapor;
- modelos de interacción clima × gestión;
- sensores continuos de suelo.

“Experimental” significa que la variable puede ser muy informativa, pero no dispone todavía de una relación universal validada para la fructificación visible de *L. vinosus*.

---

# 7. Conclusiones

1. *Lactarius vinosus* es una especie independiente de *L. sanguifluus*.

2. Está asociada principalmente a pinares.

3. La humedad y la temperatura del suelo controlan de forma clara la dinámica del micelio.

4. El micelio presenta máximos en primavera y otoño.

5. Las condiciones cálidas y secas reducen la biomasa durante el verano.

6. El calentamiento invernal podría prolongar la actividad micelial, sin implicar necesariamente mayor fructificación.

7. La interacción calor × sequedad es más informativa que la temperatura aislada.

8. La presencia de micelio no garantiza carpóforos.

9. La concentración de esporas puede servir como indicador avanzado de emergencia.

10. Los aclareos aumentaron la producción del grupo comercial de los níscalos a corto plazo, pero ese resultado no es exclusivo de *L. vinosus*.

11. La gestión y la meteorología posterior interactúan.

12. No existe una lluvia mínima, una temperatura óptima, una humedad crítica ni un número fijo de días post-lluvia universal.

13. Rainmapper debería combinar pino, humedad del suelo, temperatura del suelo, sequía antecedente, fenología, estructura forestal e historial local.

---

# 8. Bibliografía seleccionada

## 1. Castaño, C. et al. (2017)

**Título:** Seasonal dynamics of the ectomycorrhizal fungus *Lactarius vinosus* are altered by changes in soil moisture and temperature.  
**Revista:** Soil Biology and Biochemistry, 115, 253–260.  
**DOI:** https://doi.org/10.1016/j.soilbio.2017.08.021  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0038071716305727

**Aportación:** principal estudio ambiental específico. Sigue durante doce meses la biomasa micelial en 2.688 muestras de 28 parcelas y demuestra la influencia conjunta de humedad y temperatura del suelo.

**Confianza:** muy alta para dinámica micelial en el sistema estudiado; no es un modelo directo de carpóforos.

## 2. Castaño, C. et al. (2017)

**Título:** Mushroom emergence detected by combining spore trapping with molecular techniques.  
**Revista:** Applied and Environmental Microbiology.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5478987/  
**Repositorio:** https://repositori.udl.cat/bitstreams/24314e27-2540-48f9-9415-e6eaa54859b4/download

**Aportación:** relaciona concentración de esporas detectada por qPCR con la emergencia de carpóforos de *L. vinosus*.

**Confianza:** alta para detección reproductiva en las parcelas estudiadas.

## 3. Nuytinck, J. y Verbeken, A. (2003)

**Título:** *Lactarius sanguifluus* versus *Lactarius vinosus* — molecular and morphological analyses.  
**Revista:** Mycological Progress, 2, 227–234.  
**DOI:** https://doi.org/10.1007/s11557-006-0060-5  
**Consulta:** https://www.researchgate.net/publication/225882705_Lactarius_sanguifluus_versus_Lactarius_vinosus_-_Molecular_and_morphological_analyses

**Aportación:** demuestra mediante morfología y secuencias ITS que *L. vinosus* debe tratarse como especie separada.

**Confianza:** muy alta para taxonomía.

## 4. Nuytinck, J. y Verbeken, A. (2005)

**Título:** Morphology and taxonomy of the European species in *Lactarius* sect. *Deliciosi*.  
**Revista:** Mycotaxon, 92, 125–168.  
**Consulta:** https://www.researchgate.net/publication/286407520_Morphology_and_taxonomy_of_the_European_species_in_Lactarius_sect_Deliciosi_Russulales

**Aportación:** aporta descripciones, clave de identificación, datos ecológicos y criterios para separar *L. vinosus* de especies próximas.

**Confianza:** muy alta para identificación y ecología general.

## 5. Bonet, J. A. et al. (2012)

**Título:** Immediate effect of thinning on the yield of *Lactarius* group *deliciosus* in *Pinus pinaster* forests in Northeastern Spain.  
**Revista:** Forest Ecology and Management.  
**DOI:** https://doi.org/10.1016/j.foreco.2011.10.039  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0378112711006621  
**Texto:** https://cris.ctfc.cat/docs/upload/27_276_Immediate%20effect%20.pdf

**Aportación:** incluye expresamente *L. vinosus* en el grupo analizado y demuestra un incremento inmediato de rendimiento del grupo tras aclareos.

**Confianza:** media para *L. vinosus* individual, porque los resultados están agregados.

## 6. Collado, E. et al. (2021)

**Título:** Impact of forest thinning on aboveground macrofungal community composition and diversity in Mediterranean pine stands.  
**Revista:** Ecological Indicators, 133, 108340.  
**DOI:** https://doi.org/10.1016/j.ecolind.2021.108340  
**Texto completo:** https://www.sciencedirect.com/science/article/pii/S1470160X21010050

**Aportación:** seguimiento semanal de once años en 28 parcelas; demuestra efectos temporales del aclareo y modulación por temperatura de septiembre y octubre.

**Confianza:** alta para respuesta comunitaria y gestión; no ofrece una función exclusiva de *L. vinosus*.

## 7. Castaño, C. et al. (2018)

**Título:** Lack of thinning effects over inter-annual changes in soil fungal community and diversity in a Mediterranean pine forest.  
**Revista:** Forest Ecology and Management, 424, 420–427.  
**Texto institucional:** https://repositori.irta.cat/bitstream/handle/20.500.12327/400/Casta%C3%B1o_Lack_2018.pdf?isAllowed=y&sequence=5

**Aportación:** analiza cambios interanuales bajo distintas intensidades de aclareo en el mismo sistema forestal donde *L. vinosus* es una especie dominante.

**Confianza:** media-alta para contexto subterráneo y gestión; no es una ecuación individual de fructificación.

## 8. de-Miguel, S. et al. (2014)

**Título:** Impact of forest management intensity on landscape-level mushroom productivity: a regional model-based scenario analysis.  
**Revista:** Forest Ecology and Management, 330, 218–227.  
**Texto completo:** https://cris.ctfc.cat/docs/upload/27_431_De-Miguel%20et%20al-%202014.pdf

**Aportación:** incluye *L. vinosus* entre las especies comerciales de pinares catalanes y relaciona productividad regional con gestión y estructura forestal.

**Confianza:** media para la especie individual; los modelos son regionales y agregados.

---

## Nota final sobre la evidencia

La bibliografía de *L. vinosus* ofrece una base excepcionalmente buena para modelar la dinámica del micelio:

- humedad del suelo;
- temperatura del suelo;
- interacción calor × sequedad;
- estacionalidad;
- renovación de biomasa.

La evidencia es menos completa para predecir directamente los carpóforos.

No permite definir:

- lluvia mínima;
- humedad óptima universal;
- temperatura óptima;
- número de días post-lluvia;
- efecto universal del aclareo;
- relación fija entre micelio y fructificación.

La estructura más defendible para Rainmapper es: pinar compatible + humedad del suelo + temperatura del suelo + sequía antecedente + ventana otoñal + historial local + estructura forestal, manteniendo separados los indicadores de micelio, carpóforos y esporas.
