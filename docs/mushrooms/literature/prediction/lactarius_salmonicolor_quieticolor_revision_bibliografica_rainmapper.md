# Predicción de floradas de *Lactarius salmonicolor* / *Lactarius quieticolor*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especies:** *Lactarius salmonicolor* R. Heim & Leclair / *Lactarius quieticolor* Romagn.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente una o ambas especies y aporta información útil sobre fructificación, hábitat, hospedador, clima, suelo, estructura forestal o distribución.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

Rainmapper agrupa actualmente *Lactarius salmonicolor* y *Lactarius quieticolor* en un único perfil. La literatura científica muestra, sin embargo, que son especies ecológicamente diferentes y que no deberían tratarse como equivalentes.

Las conclusiones mejor respaldadas son:

1. **Ambas especies son ectomicorrícicas, pero difieren claramente en hospedador.**  
   *L. salmonicolor* está estrechamente ligado a *Abies*, especialmente *Abies alba* en Europa.  
   *L. quieticolor* está ligado a *Pinus* y se ha documentado con varios pinos europeos y exóticos.

2. **El hospedador es el factor ecológico más importante y mejor documentado.**  
   Rainmapper debería separar internamente la aptitud de abetales y pinares, aunque mantenga una ficha conjunta en la interfaz.

3. **Existe un modelo espacial específico para *L. salmonicolor*.**  
   En el noroeste de Turquía se desarrollaron modelos logísticos de distribución usando variables topográficas, climáticas y de rodal. El mejor modelo combinado alcanzó una clasificación global aproximada del 73 %.

4. **La topografía tuvo más capacidad predictiva que el clima o el rodal considerados por separado en ese estudio.**  
   Esto indica que altitud, pendiente y orientación pueden resumir diferencias de microclima, suelo y distribución del hospedador.

5. **La especie *L. salmonicolor* aparece en abetales europeos y se ha detectado directamente en ectomicorrizas de *Abies alba*.**  
   Un estudio reciente en Polonia la encontró asociada a *A. alba* y no a la especie introducida *Abies grandis*, lo que refuerza una afinidad estrecha con el abeto nativo.

6. **Los suelos calizos o ricos en bases aparecen frecuentemente asociados a *L. salmonicolor*.**  
   Un estudio de hábitat en Turquía la registró en terrenos moderadamente o ligeramente alcalinos, arcillosos o franco-arcillosos y calizos. Esos valores son locales y no deben convertirse en umbrales universales.

7. **La fenología de *L. salmonicolor* es principalmente otoñal.**  
   En el estudio turco se registró en octubre y noviembre, entre 750 y 1.250 m, en masas con *Pinus nigra* y *Quercus*; esta asociación local no invalida la afinidad general con *Abies*, pero obliga a revisar la identificación y el contexto de cada registro.

8. ***L. quieticolor* está ligado a pinos y a ambientes húmedos o suelos ácidos.**  
   Estudios europeos y sudamericanos lo sitúan con *Pinus sylvestris*, *P. radiata*, *P. taeda* y *P. elliottii*, normalmente sobre suelos ácidos o arenosos y bajo climas húmedos.

9. **La humedad del sitio parece especialmente importante para *L. quieticolor*.**  
   En modelos del grupo *Lactarius deliciosus* en Soria, su presencia en enclaves húmedos se propuso como explicación parcial de la correlación positiva entre el grupo y variables hídricas. Esta evidencia es indirecta para la especie individual.

10. **La identidad taxonómica es crítica.**  
    Ambas especies pertenecen a la sección *Deliciosi*, donde existen frecuentes errores de identificación. El color del sombrero, el viraje del látex y el hospedador deben registrarse, y las observaciones dudosas no deberían utilizarse para calibración.

11. **No existe evidencia suficiente para fijar una cantidad mínima de lluvia, una temperatura óptima, una humedad relativa crítica o un número fijo de días entre lluvia y fructificación para ninguna de las dos especies.**

12. **El historial local y el hospedador deben pesar más que cualquier regla meteorológica genérica.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | *L. salmonicolor* | *L. quieticolor* | Confianza |
|---|---|---|---|
| Hospedador | *Abies*, especialmente *A. alba* | *Pinus* | Muy alta |
| Historial local | Predictor principal | Predictor principal | Muy alta |
| Altitud, pendiente y orientación | Relevantes en modelo espacial | Moduladores probables | Alta / Media |
| Tipo de suelo | Frecuentemente calizo o básico | Frecuentemente ácido o arenoso | Media-alta |
| Humedad del sitio | Relevante | Especialmente relevante | Media |
| Día del año | Fenología otoñal | Final de verano–otoño | Alta |
| Precipitación reciente | Variable a calibrar | Variable a calibrar | Media-baja |
| Estructura del rodal | Incluida en modelos | Relevante por hábitat de pinar | Media |
| Temperatura | Variable a calibrar | Variable a calibrar | Media-baja |

**Conclusión práctica:** Rainmapper no debería calcular una única aptitud común. Debe evaluar dos subperfiles: abetal para *L. salmonicolor* y pinar, preferentemente húmedo y ácido, para *L. quieticolor*. La meteorología debe modular una aptitud ecológica previa, no sustituirla.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Lactarius salmonicolor* y *Lactarius quieticolor*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de *Lactarius deliciosus* sin desglose de especie;
- trabajos del conjunto de níscalos que no permitían distinguir *L. salmonicolor* o *L. quieticolor*;
- artículos de composición química, nutrición o contaminantes;
- páginas divulgativas con umbrales meteorológicos no verificables;
- registros antiguos con identidad taxonómica dudosa;
- modelos de productividad total de hongos sin resultados específicos;
- estudios de especies de la sección *Deliciosi* de Asia o Norteamérica sin correspondencia taxonómica europea clara.

Se seleccionaron **ocho referencias principales**, priorizando modelos espaciales, estudios taxonómicos, trabajos de ectomicorrizas y publicaciones sobre hábitat o suelo.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Diferencia ecológica entre ambas especies

La revisión taxonómica de Nuytinck y Verbeken y los estudios filogenéticos posteriores confirman que *L. salmonicolor* y *L. quieticolor* son especies distintas dentro de la sección *Deliciosi*.

La separación no es solo morfológica:

- *L. salmonicolor* se asocia principalmente con abetos;
- *L. quieticolor* se asocia con pinos;
- difieren en coloración, virajes y ecología;
- pueden confundirse con *L. deliciosus*, *L. deterrimus*, *L. semisanguifluus* y otros níscalos.

**Conclusión útil:** un único perfil de Rainmapper debe contener dos ramas ecológicas diferenciadas.

## 2.2. Hospedador de *Lactarius salmonicolor*

La literatura europea describe *L. salmonicolor* como una especie estrechamente asociada a *Abies*.

Las fuentes más sólidas incluyen:

- descripciones de ectomicorrizas sobre *Abies alba*;
- inventarios de abetales italianos;
- estudios de comunidades ectomicorrícicas de abeto;
- detección molecular en raíces de *A. alba*.

Kujawska et al. encontraron *L. salmonicolor* asociado a *Abies alba* en ensayos de procedencias en Polonia y no lo detectaron en *Abies grandis*. Los autores lo consideraron conocido por su asociación exclusiva con el abeto nativo dentro del sistema estudiado.

**Conclusión útil:** *Abies alba* debe recibir el peso máximo en Europa. Otros *Abies* pueden considerarse compatibles solo cuando exista evidencia regional.

## 2.3. Abetales y estructura forestal

Los inventarios de abetales italianos incluyen *L. salmonicolor* entre las especies características o diferenciales de estos bosques.

Los trabajos sobre operaciones selvícolas en abetales muestran que los tratamientos forestales modifican la comunidad fúngica. Sin embargo, no proporcionan una función separada de respuesta de *L. salmonicolor* a cada tratamiento.

**Conclusión útil:** continuidad del abetal, cobertura y gestión reciente deben registrarse, pero no existe un efecto cuantitativo específico universal.

## 2.4. Modelo espacial de *Lactarius salmonicolor*

Küçüker y Başkent desarrollaron modelos logísticos de distribución de *L. deliciosus* y *L. salmonicolor* en la unidad de planificación de Kızılcasu, Turquía.

Los modelos utilizaron tres grupos de variables:

- topográficas;
- climáticas;
- de estructura del rodal.

Resultados principales:

- el mejor modelo topográfico clasificó correctamente alrededor del 69,3 %;
- el mejor modelo climático alcanzó aproximadamente el 65,4 %;
- el mejor modelo de rodal, alrededor del 65 %;
- el modelo combinado alcanzó aproximadamente el 73 %.

El trabajo demuestra que:

- la distribución espacial puede modelarse;
- ningún grupo de variables explica por sí solo toda la presencia;
- la combinación mejora el resultado;
- la topografía puede ser especialmente informativa.

El artículo modela distribución u ocurrencia, no el día exacto de inicio de una florada.

**Conclusión útil:** altitud, pendiente, orientación, clima y rodal deben combinarse, pero no confundirse con un modelo de fecha de aparición.

## 2.5. Gestión forestal y simulación

Küçüker y Başkent incorporaron posteriormente los modelos de *L. deliciosus* y *L. salmonicolor* a un sistema de apoyo a la decisión forestal.

El sistema simuló:

- producción de madera;
- producción de setas;
- diferentes intensidades de gestión;
- escenarios de uso múltiple.

La utilidad para Rainmapper es metodológica: demuestra que la ocurrencia y productividad pueden integrarse con dinámica forestal.

No aporta una regla meteorológica nueva ni un umbral universal.

**Conclusión útil:** la estructura y evolución del bosque deben tratarse como variables dinámicas, no estáticas.

## 2.6. Suelo y hábitat de *Lactarius salmonicolor*

Gezer y Kaygusuz estudiaron suelos de localidades turcas donde varias especies, entre ellas *L. salmonicolor*, crecían abundantemente.

Para la localidad de *L. salmonicolor* registraron:

- altitud entre 750 y 1.250 m;
- fructificación en octubre y noviembre;
- vegetación con *Pinus nigra* y *Quercus*;
- suelos moderadamente o ligeramente alcalinos;
- textura arcillosa o franco-arcillosa;
- presencia de carbonatos;
- contenido apreciable de materia orgánica.

El estudio agrupó en parte la interpretación de suelos de varias especies. Por ello, sus valores exactos no deben tratarse como requisitos exclusivos de *L. salmonicolor*.

Además, la asociación local con *Pinus nigra* y *Quercus* contrasta con la afinidad europea repetida por *Abies*. Esto puede reflejar:

- una identificación errónea;
- presencia cercana de abetos no destacada;
- una amplitud ecológica local mayor;
- diferencias regionales;
- limitaciones del estudio.

**Conclusión útil:** la evidencia principal sigue favoreciendo *Abies*, y los registros fuera de abetales deben validarse con especial cuidado.

## 2.7. Hospedador de *Lactarius quieticolor*

La literatura taxonómica y molecular sitúa *L. quieticolor* con *Pinus*.

Está documentado con:

- *Pinus sylvestris* en Europa;
- *Pinus radiata* en Chile;
- *Pinus taeda* y *P. elliottii* en Brasil;
- otros pinos introducidos en el hemisferio sur.

Los registros sudamericanos fueron confirmados mediante morfología y secuencias moleculares.

**Conclusión útil:** la presencia de pino es un filtro ecológico de alta confianza.

## 2.8. Suelos y clima de *Lactarius quieticolor*

Silva-Filho et al. documentaron fructificaciones en plantaciones brasileñas de *Pinus taeda* y *P. elliottii*:

- sobre suelos ácidos;
- bajo clima húmedo;
- con veranos de templados a cálidos.

Los autores interpretaron la presencia como una introducción asociada a pinos exóticos.

Este resultado confirma:

- tolerancia a climas diferentes de los europeos;
- asociación con pinos;
- preferencia por suelos ácidos en ese sistema.

No demuestra que la especie necesite veranos cálidos ni que todas sus poblaciones prefieran las mismas condiciones.

**Conclusión útil:** pinar + suelo ácido + humedad es un perfil ecológico razonable, pero sin umbrales universales.

## 2.9. Humedad de sitio en *Lactarius quieticolor*

En los modelos de rendimiento del grupo *Lactarius deliciosus* en pinares de Soria, los autores señalaron que la presencia de *L. quieticolor* en lugares húmedos podía explicar parte de la relación positiva entre el grupo y variables de humedad.

Esta evidencia es indirecta porque:

- el modelo se aplicó al grupo;
- varias especies contribuían a la producción;
- *L. quieticolor* no fue modelado por separado.

Aun así, coincide con descripciones ecológicas de la especie en enclaves húmedos.

**Conclusión útil:** la humedad del sitio debe entrar como variable prioritaria de calibración para *L. quieticolor*, pero sin atribuirle un coeficiente publicado del grupo.

## 2.10. Introducción con pinos y cambio de hospedador

Los estudios de Chile y Brasil muestran que *L. quieticolor* puede establecerse con pinos no europeos.

Esto indica cierta flexibilidad dentro del género *Pinus*, pero no una capacidad de asociarse con cualquier árbol.

**Conclusión útil:** el modelo debe permitir varios pinos, dando mayor peso a combinaciones confirmadas regionalmente.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador

### *Lactarius salmonicolor*

Priorizar:

- *Abies alba*;
- otros *Abies* con evidencia regional;
- abetales puros o mixtos.

### *Lactarius quieticolor*

Priorizar:

- *Pinus sylvestris*;
- otros *Pinus* europeos;
- pinares introducidos con presencia confirmada.

La presencia del hospedador debe actuar como filtro fuerte.

## 3.2. Topografía

Para *L. salmonicolor*, la topografía tuvo alta capacidad predictiva en el estudio turco.

Variables recomendadas:

- altitud;
- pendiente;
- orientación;
- posición topográfica;
- exposición.

Estas variables probablemente integran clima, suelo y distribución del bosque, pero el artículo no demuestra un mecanismo único.

## 3.3. Suelo

### *L. salmonicolor*

Variables plausibles y documentadas:

- carbonatos;
- pH neutro o básico;
- textura fina;
- materia orgánica.

### *L. quieticolor*

Variables documentadas:

- suelo ácido;
- sustratos arenosos o pobres en bases;
- humedad de sitio.

Ninguna debe convertirse en un filtro absoluto sin calibración local.

## 3.4. Humedad

La humedad es especialmente relevante para *L. quieticolor* y probablemente importante para ambas especies.

Rainmapper debería incluir:

- precipitación reciente;
- humedad del suelo;
- balance hídrico;
- duración de periodos secos;
- orientación;
- cobertura forestal.

No existe un umbral específico validado.

## 3.5. Fenología

### *L. salmonicolor*

Principalmente otoñal, con registros de octubre y noviembre.

### *L. quieticolor*

Final de verano y otoño en Europa, con desplazamientos según región.

Variables:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- anomalía térmica.

## 3.6. Estructura del rodal

Debe incluirse:

- especie arbórea;
- cobertura;
- densidad;
- edad;
- volumen;
- gestión reciente.

La literatura no define una estructura óptima universal para ninguna de las dos especies.

## 3.7. Historial local

Es esencial para ambas especies:

- presencia confirmada;
- calidad de identificación;
- hospedador observado;
- tipo de suelo;
- frecuencia;
- abundancia;
- años sin fructificación.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Umbral de lluvia

No existe una cantidad mínima validada para ninguna de las dos especies.

## 4.2. Número fijo de días después de la lluvia

No se ha identificado un retardo universal.

## 4.3. Temperatura óptima

No existe un valor general respaldado por literatura específica.

## 4.4. Exclusividad absoluta de hospedador

La afinidad es muy fuerte:

- *Abies* para *L. salmonicolor*;
- *Pinus* para *L. quieticolor*.

Pero registros atípicos deben validarse antes de descartarse o aceptarse.

## 4.5. pH óptimo universal

Los estudios de suelo son locales y no permiten fijar intervalos globales.

## 4.6. Efecto independiente de viento, radiación o humedad relativa

No existen funciones específicas generalizables.

## 4.7. Modelo común para ambas especies

La literatura contradice la idea de un único perfil ecológico homogéneo.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Separación interna de especies

Aunque la aplicación mantenga una ficha conjunta, el motor debería calcular:

- `salmonicolor_score`;
- `quieticolor_score`.

La salida conjunta podría ser el máximo, la suma ponderada o dos capas diferenciadas.

## 5.2. Submodelo de *Lactarius salmonicolor*

Incluir:

- presencia de *Abies*;
- especialmente *A. alba*;
- altitud;
- pendiente;
- orientación;
- suelo rico en bases;
- estructura del abetal;
- fenología otoñal;
- historial local.

## 5.3. Submodelo de *Lactarius quieticolor*

Incluir:

- presencia de *Pinus*;
- suelo ácido;
- humedad del sitio;
- precipitación y balance hídrico;
- fenología de final de verano–otoño;
- historial local.

## 5.4. Componente climático

Para ambas:

- precipitación;
- humedad del suelo;
- temperatura;
- anomalías;
- duración del periodo seco.

Debe calibrarse por separado.

## 5.5. Control taxonómico

Cada observación debería registrar:

- fotografías;
- color del látex;
- virajes;
- especie arbórea próxima;
- suelo;
- nivel de certeza;
- identificación molecular cuando exista.

## 5.6. Evidencia observacional

Registrar:

- fecha y coordenadas;
- abundancia;
- hospedador;
- tipo de bosque;
- pH o litología;
- humedad;
- altitud;
- orientación;
- meteorología previa;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- identificación de especie;
- hospedador;
- tipo de bosque;
- historial local;
- día del año;
- altitud;
- orientación;
- suelo;
- humedad del sitio.

## Recomendables

- precipitación reciente;
- humedad del suelo;
- pH;
- carbonatos;
- textura;
- cobertura;
- densidad;
- edad del rodal;
- temperatura.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- déficit de presión de vapor;
- modelos separados de probabilidad;
- clasificación automática a partir de imágenes;
- inferencia del hospedador por cartografía forestal de alta resolución.

“Experimental” significa que la literatura específica no permite asignar una relación universal sobre la fructificación.

---

# 7. Conclusiones

1. *Lactarius salmonicolor* y *Lactarius quieticolor* no deberían compartir un único modelo ecológico indiferenciado.

2. *L. salmonicolor* está estrechamente asociado a *Abies*, especialmente *Abies alba*.

3. *L. quieticolor* está estrechamente asociado a *Pinus*.

4. Existe un modelo logístico espacial específico para *L. salmonicolor*.

5. En ese estudio, la topografía fue más informativa que clima o rodal considerados por separado.

6. La combinación de topografía, clima y estructura forestal mejoró la clasificación.

7. *L. salmonicolor* aparece frecuentemente en suelos calizos o ricos en bases.

8. *L. quieticolor* aparece con frecuencia en suelos ácidos y enclaves húmedos.

9. La fenología de ambas es principalmente de final de verano y otoño, con diferencias regionales.

10. No existe una cantidad mínima de lluvia, temperatura óptima o retardo post-lluvia universal.

11. Los registros fuera del hospedador típico deben revisarse taxonómicamente.

12. Rainmapper debería implementar dos submodelos y una salida conjunta solo a nivel de interfaz.

---

# 8. Bibliografía seleccionada

## 1. Küçüker, D. M. y Başkent, E. Z. (2015)

**Título:** Spatial prediction of *Lactarius deliciosus* and *Lactarius salmonicolor* mushroom distribution with logistic regression models in the Kızılcasu Planning Unit, Turkey.  
**Revista:** Mycorrhiza, 25, 1–11.  
**DOI:** https://doi.org/10.1007/s00572-014-0583-6  
**PubMed:** https://pubmed.ncbi.nlm.nih.gov/24821473/

**Aportación:** principal estudio predictivo específico. Compara modelos topográficos, climáticos, de rodal y combinados para distribución espacial.

**Confianza:** alta para el área estudiada; no predice la fecha diaria de fructificación.

## 2. Küçüker, D. M. y Başkent, E. Z. (2017)

**Título:** Impact of forest management intensity on mushroom occurrence and yield with a simulation-based decision support system.  
**Revista:** Forest Ecology and Management.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0378112716312981

**Aportación:** integra los modelos de *L. salmonicolor* en simulaciones de gestión forestal y producción.

**Confianza:** alta para aplicación forestal regional; no aporta umbrales meteorológicos universales.

## 3. Nuytinck, J. y Verbeken, A. (2005)

**Título:** Morphology and taxonomy of the European species in *Lactarius* sect. *Deliciosi*.  
**Revista:** Mycotaxon, 92, 125–168.  
**Consulta:** https://www.researchgate.net/publication/286407520_Morphology_and_taxonomy_of_the_European_species_in_Lactarius_sect_Deliciosi_Russulales

**Aportación:** revisión taxonómica y ecológica fundamental para separar ambas especies y evitar confusiones.

**Confianza:** muy alta para taxonomía y hospedadores.

## 4. Kujawska, M. et al. (2023)

**Título:** Comparable ectomycorrhizal fungal species richness but low species similarity among native *Abies alba* and alien *Abies grandis* from provenance trials in Poland.  
**Revista:** Forest Ecology and Management, 546, 121355.  
**DOI / texto:** https://doi.org/10.1016/j.foreco.2023.121355

**Aportación:** detecta *L. salmonicolor* en raíces de *Abies alba* y no en *A. grandis*, reforzando la afinidad por el hospedador nativo.

**Confianza:** alta para asociación micorrícica en el sistema estudiado.

## 5. Salerni, E. et al. (2010)

**Título:** Macrofungal communities in Italian fir woods.  
**Revista:** Cryptogamie, Mycologie, 31(3).  
**Texto completo:** https://sciencepress.mnhn.fr/sites/default/files/articles/pdf/cryptogamie-mycologie2010v31f3a3.pdf

**Aportación:** sitúa *L. salmonicolor* como especie ectomicorrícica estrechamente asociada a *Abies alba* en abetales italianos.

**Confianza:** alta para hábitat; no es un modelo meteorológico.

## 6. Gezer, K. y Kaygusuz, O. (2015)

**Título:** Soil and habitat characteristics of various species of mushroom growing wild in the Gireniz Valley, Turkey.  
**Revista:** Oxidation Communications, 38, 389–397.  
**Consulta:** https://www.researchgate.net/publication/291697625_Soil_and_habitat_characteristics_of_various_species_of_mushroom_growing_wild_in_the_Gireniz_Valley_Turkey

**Aportación:** documenta fenología, altitud, vegetación y propiedades del suelo en una localidad de *L. salmonicolor*.

**Confianza:** media; valores locales y posible incertidumbre taxonómica por asociación atípica.

## 7. Silva-Filho, A. G. S. et al. (2020)

**Título:** Not every edible orange milkcap is *Lactarius deliciosus*: first record of *Lactarius quieticolor* from Brazil.  
**Revista:** Journal of Applied Botany and Food Quality, 93, 289–299.  
**Página:** https://ojs.openagrar.de/index.php/JABFQ/article/view/15126

**Aportación:** confirma molecularmente *L. quieticolor* con *Pinus taeda* y *P. elliottii* sobre suelos ácidos y clima húmedo.

**Confianza:** alta para identidad, hospedador y contexto ambiental del estudio.

## 8. Chávez, D. et al. (2015)

**Título:** Phylogenetic and mycogeographical aspects of *Lactarius* sect. *Deliciosi* in *Pinus radiata* plantations in central Chile.  
**Revista:** Phytotaxa.  
**Página editorial:** https://www.biotaxa.org/Phytotaxa/article/view/phytotaxa.226.2.7

**Aportación:** identifica molecularmente *L. quieticolor* en plantaciones de *Pinus radiata* y confirma su capacidad de asociación con pinos introducidos.

**Confianza:** alta para taxonomía y hospedador; no aporta modelo de fructificación.

---

## Nota final sobre la evidencia

La principal conclusión documental es que la agrupación de ambas especies es útil para la interfaz, pero débil desde el punto de vista ecológico.

La evidencia disponible permite definir con bastante confianza:

- *Abies* y suelos frecuentemente básicos para *L. salmonicolor*;
- *Pinus*, suelos frecuentemente ácidos y enclaves húmedos para *L. quieticolor*;
- topografía, clima y estructura forestal como variables de distribución;
- fenología principalmente otoñal.

No permite definir:

- lluvia mínima;
- temperatura óptima;
- humedad crítica;
- número de días después de la lluvia;
- coeficientes universales de productividad.

Rainmapper debería conservar trazabilidad taxonómica y aprender parámetros por especie, hospedador y región.
