# Predicción de floradas de *Lactarius sanguifluus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Lactarius sanguifluus* (Paulet) Fr.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Lactarius sanguifluus* y aporta información útil sobre fructificación, hábitat, hospedador, suelo, clima, estructura forestal o distribución.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Lactarius sanguifluus* es limitada. Existen estudios taxonómicos, trabajos sobre comunidades ectomicorrícicas, caracterización de rodales productores y publicaciones de productividad forestal en las que la especie aparece identificada. Sin embargo, no se ha localizado un modelo meteorológico validado y exclusivo de la especie que permita fijar una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre un episodio de precipitación y la aparición de carpóforos.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica ligada principalmente a pinos.** La asociación con *Pinus* es el rasgo ecológico más consistente en Europa y el Mediterráneo.

2. **Se encuentra especialmente en pinares mediterráneos y submediterráneos.** En la Comunidad Valenciana se ha documentado en rodales dominados principalmente por *Pinus halepensis*, *P. nigra* y *P. pinaster*.

3. **La especie también forma ectomicorrizas abundantes en otros pinos mediterráneos o montanos.** En raíces finas de *Pinus heldreichii* fue una de las especies ectomicorrícicas más frecuentes identificadas molecularmente.

4. **Existe una asociación recurrente con suelos calizos o ricos en bases.** Esta preferencia aparece en revisiones taxonómicas, trabajos de hábitat y estudios de comunidades. No existe, sin embargo, un intervalo universal de pH o carbonatos validado para la fructificación.

5. **Es una especie predominantemente mediterránea y termófila.** La literatura de cultivo ectomicorrícico la describe como adaptada a ambientes mediterráneos y horizontes de suelo calcáreos o cálcicos.

6. **La fenología europea es principalmente otoñal.** Los registros se concentran normalmente entre septiembre y noviembre, con prolongación posible hasta diciembre en las regiones más meridionales. Esta ventana no debe tratarse como un calendario rígido.

7. **La producción se integra a menudo en el grupo comercial de los níscalos.** Muchos estudios forestales agrupan *L. sanguifluus* con *L. deliciosus*, *L. semisanguifluus*, *L. vinosus* u otras especies próximas. Los coeficientes calculados para ese grupo no pueden atribuirse automáticamente a *L. sanguifluus*.

8. **La estructura y gestión del pinar probablemente influyen, pero faltan modelos separados para la especie.** Los estudios regionales de productividad y gestión incluyen la especie, aunque normalmente no publican una función meteorológica individual.

9. **La recurrencia del fuego puede modificar las comunidades ectomicorrícicas de los pinares mediterráneos.** *L. sanguifluus* aparece en estudios sobre perturbación y gestión, pero no existe una curva específica de recuperación postincendio para la especie.

10. **No existe evidencia suficiente para asignar efectos universales e independientes al viento, humedad relativa, radiación o evapotranspiración.** Pueden ayudar a estimar la conservación de humedad, pero no deben presentarse como predictores demostrados de *L. sanguifluus*.

11. **La distinción respecto a *Lactarius vinosus* es imprescindible.** Los análisis moleculares y morfológicos confirman que son especies diferentes, por lo que las observaciones mal identificadas pueden distorsionar el modelo.

12. **El historial local y el hospedador deben tener más peso que cualquier regla meteorológica genérica.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Pinus* compatible | Filtro ecológico principal | Muy alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Suelo calizo o rico en bases | Modulador de aptitud | Alta |
| Día del año | Ventana fenológica otoñal | Alta |
| Precipitación reciente y acumulada | Variable a calibrar | Media |
| Humedad del suelo | Estado hídrico | Media |
| Temperatura reciente | Modulador mediterráneo | Media |
| Especie de pino y estructura del rodal | Moduladores ecológicos | Media-alta |
| Altitud y orientación | Moduladores microclimáticos | Media |
| Fuego y gestión reciente | Penalización o corrección temporal | Media |

**Conclusión práctica:** Rainmapper debería modelar *L. sanguifluus* mediante un filtro fuerte de pinares mediterráneos o submediterráneos, preferencia flexible por suelos calcáreos, una ventana otoñal y un peso elevado del historial local. Las variables meteorológicas deben incorporarse para calibración, pero la bibliografía específica no permite fijar umbrales ni retardos universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Lactarius sanguifluus*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de *Lactarius deliciosus* sin desglose de especie;
- trabajos del grupo de níscalos que no permitían distinguir *L. sanguifluus*;
- artículos de composición química, nutrición o contaminantes;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos generales de productividad fúngica sin resultados identificables para la especie;
- registros antiguos cuya identidad con *L. vinosus* o *L. semisanguifluus* era dudosa;
- referencias no accesibles que solo repetían preferencias ecológicas sin aportar datos originales.

Se seleccionaron **ocho referencias principales**, priorizando taxonomía, caracterización de rodales, estudios de ectomicorrizas, gestión forestal y trabajos de distribución mediterránea.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Identidad taxonómica

Nuytinck y Verbeken analizaron molecular y morfológicamente *L. sanguifluus* y *L. vinosus*.

El estudio confirmó que:

- son especies diferenciadas;
- existen caracteres morfológicos útiles;
- el color y viraje del látex son importantes;
- la identificación visual puede ser problemática;
- las observaciones deben conservar información taxonómica detallada.

Esta cuestión afecta directamente a Rainmapper porque ambos taxones aparecen en la aplicación y pueden compartir pinares y campañas.

**Conclusión útil:** las observaciones de *L. sanguifluus* deben registrar látex, coloración, viraje, fotografías y hospedador.

## 2.2. Asociación con pinos

La relación con *Pinus* aparece de forma consistente en la literatura europea y mediterránea.

Los contextos documentados incluyen:

- *Pinus halepensis*;
- *Pinus nigra*;
- *Pinus pinaster*;
- *Pinus heldreichii*;
- otros pinos según región.

En el estudio valenciano de rodales productores, las formaciones con mayor representación fueron:

1. *Pinus halepensis*;
2. *Pinus nigra*;
3. *Pinus pinaster*.

El trabajo también registró mosaicos con encinar, coscojar, romeral y matorral, pero la presencia del pino seguía siendo el componente central.

**Conclusión útil:** el motor debe utilizar especie de pino y estructura del pinar, no solo una categoría forestal genérica.

## 2.3. *Pinus heldreichii* y presencia subterránea

Iotti et al. estudiaron hongos asociados a raíces finas de *Pinus heldreichii* en el sur de Italia.

El diseño incluyó:

- 70 árboles;
- análisis químicos del suelo;
- tipificación de raíces ectomicorrícicas;
- secuenciación ITS;
- 147 especies fúngicas identificadas.

*L. sanguifluus* representó aproximadamente el 5,1 % de las secuencias ectomicorrícicas y fue una de las especies más comunes.

Este resultado demuestra:

- asociación real con raíces;
- presencia importante en el sistema subterráneo;
- compatibilidad con *P. heldreichii*;
- posible persistencia incluso cuando no se observan carpóforos.

**Conclusión útil:** la ausencia de setas visibles no equivale a ausencia del hongo.

## 2.4. *Pinus halepensis* y perturbación mediterránea

El Karkouri et al. estudiaron la diversidad ectomicorrícica en una plantación perturbada de *Pinus halepensis* en la región mediterránea.

El trabajo incluye *L. sanguifluus* dentro de la comunidad ectomicorrícica del pinar.

Su aportación principal es confirmar que:

- la especie puede formar parte de comunidades de *P. halepensis*;
- el contexto mediterráneo perturbado mantiene diversidad ectomicorrícica;
- la composición depende de suelo, hospedador y estado del rodal.

No ofrece una función separada de fructificación.

**Conclusión útil:** *P. halepensis* debe recibir un peso alto, pero la perturbación y la historia del rodal deben registrarse.

## 2.5. Suelos calizos

La asociación con suelos calcáreos es una de las características más repetidas.

La literatura especializada describe *L. sanguifluus* como:

- adaptado a horizontes calizos o cálcicos;
- presente en pinares sobre sustratos carbonatados;
- frecuente en ambientes mediterráneos ricos en bases;
- capaz de aparecer en dunas calizas con pinos.

La revisión sobre cultivo sostenible de hongos ectomicorrícicos comestibles la define como una especie termófila, predominantemente mediterránea y adaptada a suelos calizos o cálcicos.

No se ha localizado una función cuantitativa específica de:

- pH;
- porcentaje de carbonatos;
- textura;
- profundidad del suelo;
- capacidad de retención.

**Conclusión útil:** usar litología, pH estimado y carbonatos como moduladores de alta relevancia, no como umbrales absolutos.

## 2.6. Carácter mediterráneo y termófilo

La distribución europea se concentra especialmente en el sur y en regiones mediterráneas.

La especie también se ha registrado más al norte en enclaves cálidos, soleados, protegidos y calizos.

Esto respalda la caracterización termófila, pero no permite concluir que:

- temperaturas más altas sean siempre favorables;
- exista un mínimo o máximo universal;
- el calor sustituya a la humedad.

En clima mediterráneo, el calor puede aumentar simultáneamente la evaporación y el déficit hídrico.

**Conclusión útil:** modelar la temperatura en interacción con disponibilidad de agua y exposición.

## 2.7. Fenología

Los registros europeos sitúan la fructificación principalmente:

- septiembre;
- octubre;
- noviembre;
- ocasionalmente diciembre en regiones meridionales.

La fecha puede desplazarse según:

- altitud;
- latitud;
- especie de pino;
- lluvia efectiva;
- temperatura otoñal;
- reserva hídrica antecedente.

No se ha localizado una serie fenológica larga exclusiva de la especie que permita estimar un retardo post-lluvia.

**Conclusión útil:** usar una ventana otoñal flexible y aprendida regionalmente.

## 2.8. Caracterización de rodales valencianos

Domínguez-Núñez et al. localizaron mediante cartografía digital rodales productores de *L. deliciosus* y *L. sanguifluus* en la Comunidad Valenciana.

El estudio relacionó las zonas productoras con:

- pinares;
- especies de pino;
- formaciones mixtas;
- matorrales mediterráneos;
- estructura del paisaje forestal.

La limitación principal es que parte del análisis trata conjuntamente ambas especies.

**Conclusión útil:** la cartografía de vegetación es útil para delimitar aptitud, pero no permite separar completamente la ecología de *L. sanguifluus*.

## 2.9. Productividad y gestión a escala regional

Los modelos regionales de Cataluña y otros territorios incluyen *L. sanguifluus* entre las especies comerciales de pinares.

Estos trabajos demuestran que la productividad micológica a escala de paisaje responde a:

- especie forestal;
- área basimétrica;
- clima;
- intensidad de gestión;
- edad y estructura del rodal.

Sin embargo, los resultados suelen estar agregados por grupo de especies o productividad total.

**Conclusión útil:** estructura y gestión deben entrar como variables candidatas, sin copiar coeficientes de modelos agregados.

## 2.10. Aclareos y grupo de níscalos

El estudio de Bonet et al. sobre aclareos define el grupo comercial “*Lactarius deliciosus*” incluyendo expresamente:

- *L. sanguifluus*;
- *L. semisanguifluus*;
- *L. salmonicolor*;
- *L. vinosus*;
- otras especies próximas.

El trabajo encontró respuestas del grupo a tratamientos selvícolas, pero no permite saber qué proporción correspondía a *L. sanguifluus*.

**Conclusión útil:** la gestión puede influir, pero la evidencia no es específica de esta especie y debe etiquetarse como indirecta.

## 2.11. Fuego y recurrencia de incendios

Estudios recientes en *Pinus pinaster* y *Pinus halepensis* muestran que una alta recurrencia de incendios reduce la diversidad ectomicorrícica local y regional.

*L. sanguifluus* aparece en inventarios y tesis relacionados con comunidades postincendio.

No se ha localizado una curva específica que indique:

- años necesarios para recuperación;
- severidad crítica;
- respuesta del micelio;
- respuesta de los carpóforos.

**Conclusión útil:** penalizar incendios severos y recurrentes como factor de hábitat, pero sin asignar un periodo fijo de recuperación.

## 2.12. Registros fuera de pinos europeos

Se han publicado estudios de asociación de *L. sanguifluus* con vegetación conífera y caducifolia en Asia.

Algunos de estos registros incluyen *Juglans*, *Populus* o *Quercus*, pero su interpretación debe ser prudente por:

- diferencias biogeográficas;
- posible uso amplio del nombre europeo;
- necesidad de confirmación molecular;
- coexistencia de pinos no descritos en el resumen.

**Conclusión útil:** para Rainmapper europeo, la evidencia principal debe seguir centrada en *Pinus*.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador

El filtro principal debe ser la presencia de pinos.

Prioridad sugerida, sin pesos numéricos universales:

- *Pinus halepensis*;
- *Pinus nigra*;
- *Pinus pinaster*;
- *Pinus heldreichii*;
- otros pinos con observaciones regionales.

La ausencia de pino debería reducir claramente la aptitud.

## 3.2. Suelo

Variables recomendadas:

- litología calcárea;
- pH estimado;
- carbonatos;
- textura;
- profundidad;
- drenaje;
- capacidad de retención.

La preferencia calcícola está bien respaldada, pero no define una exclusión absoluta.

## 3.3. Temperatura

La caracterización termófila justifica incluir:

- temperatura media;
- máximas;
- mínimas;
- anomalías;
- persistencia del calor otoñal;
- interacción con humedad.

No existe un óptimo publicado y transferible.

## 3.4. Agua disponible

Aunque no existe un modelo climático exclusivo, la fructificación requiere un estado hídrico favorable.

Rainmapper debería calcular:

- precipitación reciente;
- precipitación acumulada;
- humedad del suelo;
- balance hídrico;
- días secos consecutivos;
- evapotranspiración como componente del balance.

Estas variables deben calibrarse con observaciones propias.

## 3.5. Fenología

Variables:

- día del año;
- fecha histórica local;
- altitud;
- región climática;
- primera lluvia otoñal efectiva;
- persistencia de temperaturas suaves.

No debe fijarse la campaña únicamente entre septiembre y noviembre.

## 3.6. Estructura del pinar

Incluir:

- área basimétrica;
- cobertura;
- densidad;
- edad;
- altura;
- especie dominante;
- gestión reciente.

La literatura específica no define una estructura óptima para *L. sanguifluus*.

## 3.7. Historial local

Es esencial:

- presencia confirmada;
- calidad taxonómica;
- abundancia;
- recurrencia;
- especie de pino;
- suelo;
- fechas;
- perturbaciones.

## 3.8. Fuego y perturbación

Registrar:

- severidad;
- recurrencia;
- tiempo desde incendio;
- regeneración del pinar;
- pérdida de suelo;
- tratamientos postincendio.

No existe una función específica validada.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral validado y exclusivo de la especie.

## 4.2. Número fijo de días después de la lluvia

No se ha localizado un retardo universal.

## 4.3. Temperatura óptima

El carácter termófilo no equivale a una temperatura óptima conocida.

## 4.4. pH óptimo exacto

La preferencia por suelos calizos está bien documentada, pero no existe un intervalo universal.

## 4.5. Efecto positivo general de los aclareos

Los estudios suelen agrupar varias especies de níscalos.

## 4.6. Recuperación exacta tras incendio

No existe una curva específica publicada.

## 4.7. Viento, radiación y humedad relativa

No se han localizado funciones específicas generalizables.

## 4.8. Asociación regular con frondosas

Los registros asiáticos atípicos no justifican modificar el perfil europeo centrado en pinos.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- presencia de *Pinus*;
- especie de pino;
- suelo calcáreo o rico en bases;
- continuidad del pinar;
- historial local;
- ausencia de perturbación severa reciente.

## 5.2. Componente hídrico

Incluir:

- precipitación reciente;
- precipitación acumulada;
- humedad del suelo;
- balance hídrico;
- duración del periodo seco;
- evapotranspiración.

## 5.3. Componente térmico

Incluir:

- temperatura media;
- mínimas;
- máximas;
- anomalía;
- interacción con agua disponible.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- primera aparición observada.

## 5.5. Estructura forestal

Incluir:

- área basimétrica;
- cobertura;
- densidad;
- edad;
- especie dominante;
- gestión reciente.

## 5.6. Perturbación

Incluir:

- incendios;
- recurrencia;
- severidad;
- tala;
- compactación;
- erosión;
- regeneración del hospedador.

## 5.7. Control taxonómico

Cada observación debería registrar:

- látex;
- viraje;
- color;
- zonación del sombrero;
- fotografías;
- especie de pino;
- nivel de certeza;
- análisis molecular cuando exista.

## 5.8. Evidencia observacional

Registrar:

- fecha y coordenadas;
- abundancia;
- hospedador;
- litología;
- pH estimado;
- estructura del rodal;
- meteorología previa;
- perturbación;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- identificación fiable;
- especie de *Pinus*;
- tipo de pinar;
- historial local;
- litología o pH;
- día del año;
- precipitación;
- humedad del suelo;
- temperatura;
- altitud.

## Recomendables

- carbonatos;
- textura;
- cobertura;
- densidad;
- área basimétrica;
- orientación;
- pendiente;
- gestión;
- incendios previos.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- déficit de presión de vapor;
- temperatura del suelo;
- índices de vigor del pinar;
- modelos separados por especie de pino;
- detección molecular de micelio.

“Experimental” significa que la literatura específica no permite asignarles todavía una relación universal sobre la fructificación de *L. sanguifluus*.

---

# 7. Conclusiones

1. *Lactarius sanguifluus* es una especie ectomicorrícica ligada principalmente a pinos.

2. *Pinus halepensis*, *P. nigra*, *P. pinaster* y *P. heldreichii* cuentan con evidencia específica.

3. La especie es predominantemente mediterránea y termófila.

4. Los suelos calizos o ricos en bases constituyen una preferencia ecológica consistente.

5. La fenología es principalmente otoñal, con prolongación posible hasta diciembre en regiones meridionales.

6. Existe evidencia subterránea directa de su ectomicorriza en raíces de pino.

7. La ausencia de carpóforos no implica ausencia del hongo.

8. Muchos modelos forestales agrupan la especie con otros níscalos y no permiten extraer coeficientes específicos.

9. La estructura forestal y la gestión son variables relevantes, pero todavía insuficientemente cuantificadas para la especie individual.

10. La recurrencia de incendios puede reducir la diversidad ectomicorrícica, pero no existe una curva específica de recuperación.

11. No existe una cantidad mínima de lluvia, una temperatura óptima o un número fijo de días post-lluvia universal.

12. Rainmapper debería combinar pino, suelo calcáreo, agua disponible, temperatura, fenología, estructura forestal e historial local.

---

# 8. Bibliografía seleccionada

## 1. Nuytinck, J. y Verbeken, A. (2003)

**Título:** *Lactarius sanguifluus* versus *Lactarius vinosus* — molecular and morphological analyses.  
**Revista:** Mycological Progress, 2, 227–234.  
**DOI:** https://doi.org/10.1007/s11557-006-0060-5  
**Página editorial:** https://link.springer.com/article/10.1007/s11557-006-0060-5

**Aportación:** referencia taxonómica principal para separar *L. sanguifluus* de *L. vinosus*.

**Confianza:** muy alta para identidad taxonómica; no aporta un modelo meteorológico.

## 2. Domínguez-Núñez, J. A. et al. (2008)

**Título:** Caracterización de rodales productores de *Lactarius deliciosus* y *Lactarius sanguifluus* en la Comunidad Valenciana.  
**Publicación:** Boletín de la Sociedad Micológica Valenciana, 13, 2–18.  
**Consulta:** https://www.researchgate.net/publication/261876207_Characterization_of_Forest_Stands_Producers_of_Lactarius_deliciosus_and_Lactarius_sanguifluus_in_Valencian_County_Spain

**Aportación:** identifica mediante cartografía los rodales productores y relaciona la presencia con *Pinus halepensis*, *P. nigra* y *P. pinaster*.

**Confianza:** alta para hábitat regional; parte del análisis agrupa ambas especies.

## 3. Iotti, M. et al. (2018)

**Título:** Fungi inhabiting fine roots of *Pinus heldreichii* in the southernmost European forest of this relict pine species.  
**Revista:** Symbiosis.  
**Página editorial:** https://link.springer.com/article/10.1007/s13199-017-0504-5  
**Registro institucional:** https://publications.slu.se/?file=publ%2Fshow&id=94010

**Aportación:** identifica molecularmente *L. sanguifluus* como una de las especies ectomicorrícicas más frecuentes en raíces de *P. heldreichii*.

**Confianza:** alta para hospedador y presencia subterránea.

## 4. El Karkouri, K. et al. (2004)

**Título:** Diversity of ectomycorrhizal symbionts in a disturbed *Pinus halepensis* plantation in the Mediterranean region.  
**Revista:** Annals of Forest Science.  
**Texto completo:** https://hal.science/hal-00883806/document

**Aportación:** registra *L. sanguifluus* en la comunidad ectomicorrícica de una plantación mediterránea de *P. halepensis*.

**Confianza:** alta para asociación con *P. halepensis*; no aporta predicción de carpóforos.

## 5. Guerin-Laguette, A. et al. (2022)

**Título:** Successes and challenges in the sustainable cultivation of edible ectomycorrhizal mushrooms.  
**Revista:** Frontiers in Forests and Global Change / revisión disponible en PMC.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9157773/

**Aportación:** caracteriza *L. sanguifluus* como especie termófila, predominantemente mediterránea y adaptada a horizontes calizos o cálcicos.

**Confianza:** alta como revisión de síntesis; no aporta umbrales de fructificación.

## 6. Bonet, J. A. et al. (2012)

**Título:** Immediate effect of thinning on the yield of *Lactarius* group *deliciosus* in *Pinus pinaster* forests.  
**Revista:** Forest Ecology and Management.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0378112711006621

**Aportación:** incluye expresamente *L. sanguifluus* dentro del grupo comercial de níscalos y analiza respuesta a aclareos.

**Confianza:** media para *L. sanguifluus* individual, porque los resultados están agregados.

## 7. de-Miguel, S. et al. (2014)

**Título:** Impact of forest management intensity on landscape-level mushroom productivity: a regional model-based scenario analysis.  
**Revista:** Forest Ecology and Management, 330, 218–227.  
**Texto completo:** https://cris.ctfc.cat/docs/upload/27_431_De-Miguel%20et%20al-%202014.pdf

**Aportación:** incluye *L. sanguifluus* entre las especies comerciales de pinares catalanes y relaciona productividad regional con estructura y gestión forestal.

**Confianza:** media para la especie concreta; los modelos son regionales y agregados.

## 8. Pérez-Izquierdo, L. et al. (2020)

**Título:** Ectomycorrhizal fungal diversity decreases in Mediterranean pine forests subjected to high fire recurrence.  
**Texto completo:** https://www.uv.es/verducam/Ecto_Pinus_Fire.pdf

**Aportación:** demuestra el efecto de la recurrencia de incendios sobre comunidades ectomicorrícicas de *Pinus pinaster* y *P. halepensis*, contexto en el que aparece *L. sanguifluus*.

**Confianza:** alta para efecto comunitario del fuego; no proporciona una respuesta separada de la especie.

---

## Nota final sobre la evidencia

La literatura específica de *L. sanguifluus* permite definir con bastante confianza:

- asociación con *Pinus*;
- preferencia por ambientes mediterráneos;
- afinidad por suelos calcáreos;
- fenología principalmente otoñal;
- importancia de la correcta separación respecto a *L. vinosus*.

No permite definir:

- precipitación mínima;
- temperatura óptima;
- humedad crítica;
- número de días post-lluvia;
- área basimétrica óptima;
- periodo universal de recuperación tras incendios.

Rainmapper debería mantener una clara separación entre evidencia específica de la especie y resultados agregados del grupo comercial de los níscalos.
