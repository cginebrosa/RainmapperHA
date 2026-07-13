# Predicción de floradas del complejo *Morchella elata*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie o grupo:** *Morchella elata* complex  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Morchella elata*, el clado Elata o el grupo de “black morels” históricamente tratado como *M. elata* sensu lato, y que aporta información útil sobre fructificación, fenología, fuego, hábitat, temperatura, humedad o distribución.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La expresión **“*Morchella elata* complex”** designa un conjunto de colmenillas negras morfológicamente parecidas, no una única entidad ecológica simple. Los estudios moleculares modernos han demostrado que numerosos registros históricos de *M. elata* corresponden a especies distintas del clado Elata. Esta incertidumbre taxonómica es el principal límite para construir un único modelo predictivo.

La literatura específica permite sostener las siguientes conclusiones:

1. **El complejo incluye especies ecológicamente diferentes.** Algunas fructifican regularmente en bosques no quemados; otras son claramente pirófilas y producen sobre todo después de incendios.

2. **La primavera es la ventana fenológica principal en Europa y Norteamérica templada.** La fecha exacta depende de altitud, nieve, calentamiento del suelo y región.

3. **El calentamiento progresivo del suelo es una señal relevante.** Los estudios sobre colmenillas muestran que la aparición se relaciona con el aumento primaveral de la temperatura del suelo, pero no existe un umbral universal específico para todo el complejo *M. elata*.

4. **La humedad previa es necesaria, pero no existe una cantidad mínima de lluvia transferible.** En colmenillas de campo se han encontrado relaciones con episodios de lluvia durante las semanas previas, aunque parte de esa evidencia procede de otras especies de *Morchella* y no debe convertirse en regla directa para *M. elata* complex.

5. **El fuego es un factor crítico solo para algunos linajes.** En bosques occidentales de Norteamérica, especies del grupo negro producen cosechas masivas la primavera posterior a un incendio; otras especies del mismo grupo aparecen en bosque sano.

6. **El primer año después del incendio suele ser el más productivo para las especies pirófilas.** La producción disminuye fuertemente en años posteriores, pero la magnitud depende de especie, severidad, bosque y clima.

7. **La severidad del fuego y el tipo de bosque importan.** La literatura postincendio demuestra que no todos los incendios ni todas las masas forestales producen la misma respuesta.

8. **Los bosques de coníferas aparecen con frecuencia en el clado Elata.** Se documentan asociaciones o hábitats con *Pinus*, *Picea*, *Abies*, *Cedrus* y *Juniperus*, además de algunos bosques mixtos y frondosas.

9. **No debe asumirse que todas las colmenillas negras sean ectomicorrícicas.** La ecología trófica de *Morchella* es compleja; existen fases saprótrofas y posibles asociaciones con raíces, pero no hay base para aplicar un filtro de hospedador equivalente al de un boleto.

10. **El cultivo aporta información fisiológica, no umbrales de campo.** En aislados identificados como *M. elata*, el crecimiento micelial respondió a la temperatura, pero esos valores no equivalen a temperaturas óptimas de fructificación silvestre.

11. **La observación local y la identificación molecular tienen un valor excepcional.** Un registro de “*M. elata*” sin secuencia o identificación moderna puede representar distintos taxones con respuestas ecológicas diferentes.

12. **No existe evidencia suficiente para fijar una lluvia mínima, temperatura óptima, humedad crítica o número universal de días desde el deshielo o el incendio.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Identidad dentro del clado Elata | Control taxonómico principal | Muy alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Incendio reciente y años desde el fuego | Variable principal para taxones pirófilos | Alta |
| Tipo y severidad del incendio | Modulador postincendio | Alta |
| Día del año | Ventana fenológica primaveral | Alta |
| Temperatura del suelo | Señal de activación primaveral | Media-alta |
| Humedad del suelo / lluvia previa | Estado hídrico | Media |
| Nieve y fecha de deshielo | Modulador de montaña | Media-alta |
| Tipo de bosque | Filtro ecológico flexible | Media-alta |
| Altitud y orientación | Moduladores microclimáticos | Media |

**Conclusión práctica:** Rainmapper no debería utilizar un único modelo homogéneo para todo el complejo. Debe distinguir al menos entre **colmenillas negras pirófilas** y **colmenillas negras no pirófilas**, y combinar taxonomía, historial local, fuego, calentamiento del suelo, humedad y fenología primaveral. Los umbrales numéricos deben aprenderse regionalmente.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico suficiente para incorporarlos a un modelo de predicción de fructificaciones del complejo *Morchella elata*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de *Morchella esculenta* sin relación explícita con el clado Elata;
- trabajos de cultivo de especies chinas como *M. sextelata* o *M. importuna* cuando no aportaban información transferible segura;
- páginas divulgativas con umbrales meteorológicos no verificables;
- publicaciones sobre composición química o nutrición;
- registros históricos de “*M. elata*” sin contexto taxonómico ni ecológico;
- estudios postincendio que no distinguían suficientemente entre colmenillas negras y amarillas;
- cifras de temperatura o humedad de cultivo presentadas como si fueran condiciones de campo.

Se seleccionaron **ocho referencias principales**, priorizando taxonomía multilocus, ecología postincendio, productividad en bosque sano y quemado, estudios específicos de *M. elata* y revisiones de manejo.

---

# 2. Qué evidencia específica existe realmente

## 2.1. El “complejo *Morchella elata*” no es una sola especie ecológica

Richard et al. revisaron la taxonomía de las colmenillas europeas y norteamericanas mediante varios genes.

El trabajo demostró que:

- la morfología del sombrero es muy plástica;
- especies distintas pueden parecer casi idénticas;
- el nombre *M. elata* se aplicó históricamente a múltiples linajes;
- el clado Elata incluye numerosas especies;
- Europa y Norteamérica no comparten necesariamente las mismas especies.

Petrželová y Sochor propusieron posteriormente criterios más conservadores para reconocer especies dentro de *Morchella*.

**Conclusión útil:** Rainmapper debe almacenar “*M. elata* complex” como categoría operativa, pero conservar la identificación molecular o filogenética cuando exista.

## 2.2. Linajes pirófilos y no pirófilos

Pilz et al. estudiaron colmenillas negras en bosques sanos, clareados y quemados del oeste de Norteamérica.

Identificaron varios tipos o especies operativas:

- algunas fructificaban principalmente en suelos quemados;
- otras aparecían también en bosque no quemado;
- los patrones de productividad diferían entre grupos.

Esto demuestra que el fuego no es una regla universal de todo el complejo.

**Conclusión útil:** separar al menos dos submodelos:

- `elata_fire_associated`;
- `elata_non_fire_associated`.

## 2.3. Producción postincendio

Los estudios de ecología y gestión de colmenillas del oeste norteamericano muestran que determinadas especies negras producen cosechas elevadas en la primera primavera después del fuego.

La revisión de Pilz et al. resume que:

- la respuesta puede ser masiva;
- el primer año postincendio suele ser el más importante;
- la producción puede caer rápidamente después;
- el momento del incendio influye;
- incendios de otoño suelen producir fructificación la primavera siguiente.

No todos los taxones siguen este patrón.

**Conclusión útil:** para taxones pirófilos, `years_since_fire = 1` debe considerarse una señal fuerte, pero no una garantía.

## 2.4. Severidad y heterogeneidad del fuego

Larson et al. analizaron abundancia, estructura espacial y sostenibilidad de cosecha postincendio mediante más de mil parcelas georreferenciadas.

El estudio mostró:

- distribución muy agregada;
- presencia solo en una fracción de las parcelas;
- fuerte heterogeneidad espacial;
- alta abundancia en manchas concretas;
- importancia del contexto del incendio y del rodal.

Los resultados no justifican afirmar que cualquier superficie quemada sea apta.

**Conclusión útil:** Rainmapper debe incorporar severidad, tipo de combustible, composición forestal y posición dentro del perímetro quemado.

## 2.5. Estudios postincendio europeos

Snabl et al. estudiaron colmenillas postincendio en pinares del norte y centro de Italia y secuenciaron materiales del clado Elata.

El trabajo confirma que:

- existen colmenillas negras europeas asociadas a bosques quemados;
- la identificación molecular es necesaria;
- morfotipos similares pueden corresponder a taxones diferentes;
- el contexto postincendio europeo también produce diversidad no resuelta visualmente.

**Conclusión útil:** no trasladar automáticamente especies pirófilas norteamericanas a Europa; usar la evidencia europea para validar el submodelo local.

## 2.6. Bosques sanos frente a quemados

Pilz et al. compararon productividad y diversidad en:

- bosques sanos;
- bosques gestionados;
- áreas quemadas.

Algunas colmenillas negras aparecieron únicamente en zonas quemadas, mientras que otras fructificaron en bosque no quemado.

La producción de bosque sano suele ser más baja y menos espectacular, pero puede ser recurrente.

**Conclusión útil:** historial local tiene especial valor en colonias no pirófilas, mientras que el mapa de fuego es prioritario para las pirófilas.

## 2.7. Fenología primaveral

Las colmenillas del clado Elata fructifican principalmente en primavera en regiones templadas.

La fecha depende de:

- latitud;
- altitud;
- nieve;
- temperatura del suelo;
- exposición;
- fecha del incendio;
- régimen de precipitación.

En áreas de montaña, la campaña se desplaza con el deshielo y puede ascender altitudinalmente a lo largo de la primavera.

**Conclusión útil:** el día del año debe interactuar con altitud y temperatura del suelo.

## 2.8. Temperatura y crecimiento micelial de *M. elata*

Winder estudió cultivos derivados de ascosporas de *M. elata*.

El trabajo encontró:

- diferencias entre aislados;
- respuesta clara del crecimiento a temperatura;
- variación ligada a la madurez de los ascocarpos parentales;
- capacidad de crecimiento en un rango relativamente amplio.

Estos resultados se refieren al crecimiento micelial en cultivo.

No deben interpretarse como:

- temperatura óptima de fructificación;
- temperatura de emergencia;
- umbral de campo;
- condición universal del complejo.

**Conclusión útil:** confirmar que la temperatura es fisiológicamente relevante, sin transferir valores de cultivo.

## 2.9. Temperatura del suelo y aparición

Los estudios detallados de campo sobre colmenillas son escasos. Mihail, trabajando con *M. esculenta*, mostró relaciones entre aparición, calentamiento del suelo y lluvia previa.

Esa publicación no estudia *M. elata*, por lo que no puede usarse como evidencia directa.

Su utilidad es únicamente metodológica:

- medir temperatura del suelo;
- usar ventanas de lluvia;
- separar inicio de campaña y abundancia;
- trabajar con series plurianuales.

**Conclusión útil:** aplicar el diseño de variables, no copiar los coeficientes ni umbrales.

## 2.10. Humedad y lluvia previa

La literatura específica del clado Elata coincide en que la fructificación requiere humedad suficiente, pero no ofrece un umbral universal.

En áreas postincendio, la respuesta depende de:

- precipitación invernal;
- nieve;
- humedad del suelo;
- lluvia primaveral;
- velocidad de secado;
- severidad del fuego.

La cantidad exacta varía entre regiones y especies.

**Conclusión útil:** usar balance hídrico y humedad del suelo, no solo lluvia acumulada.

## 2.11. Nieve y deshielo

En bosques montanos del oeste norteamericano, la campaña de colmenillas sigue a menudo el retroceso de la nieve.

La nieve puede afectar:

- humedad del suelo;
- temperatura;
- inicio de la actividad;
- desplazamiento altitudinal de la campaña.

No existe un número universal de días desde el deshielo.

**Conclusión útil:** en áreas de montaña, incluir fecha de deshielo y nieve residual como variables de alta prioridad.

## 2.12. Bosques y vegetación asociados

Las especies del clado Elata se documentan en:

- *Pinus*;
- *Picea*;
- *Abies*;
- *Cedrus*;
- *Juniperus*;
- bosques mixtos;
- algunos sistemas con *Quercus*;
- áreas alteradas, caminos y suelos removidos para ciertos taxones.

Taşkın et al. describieron nuevas especies del subclado Elata en Turquía bajo múltiples coníferas y algunos robles.

**Conclusión útil:** el tipo de bosque debe actuar como modulador por taxón, no como filtro universal del complejo.

## 2.13. Ecología trófica incierta

Las colmenillas pueden presentar:

- crecimiento saprótrofo;
- formación de esclerocios;
- colonización de materia orgánica;
- asociaciones con raíces;
- respuestas a muerte o estrés de árboles;
- fructificación tras perturbaciones.

La literatura no respalda un único modo trófico simple para todo el clado.

**Conclusión útil:** no modelar *M. elata* complex como ectomicorrícico estricto ni como saprótrofo puro.

## 2.14. Distribución espacial agregada

Los estudios postincendio muestran que la producción aparece en manchas.

La agregación puede responder a:

- severidad;
- humedad;
- micrositio;
- profundidad de ceniza;
- vegetación previa;
- suelo;
- colonias preexistentes.

**Conclusión útil:** utilizar resolución espacial fina y evitar medias por todo el perímetro quemado.

---

# 3. Factores predictivos defendibles

## 3.1. Identidad taxonómica

Cada observación debería registrar:

- identificación morfológica;
- fotografías;
- contexto de fuego;
- hábitat;
- secuencia ITS o multilocus cuando exista;
- nivel de certeza.

## 3.2. Fuego

Para taxones pirófilos:

- año del incendio;
- severidad;
- estación del incendio;
- tipo de bosque;
- recurrencia;
- porcentaje de copa consumida;
- profundidad de suelo afectada.

## 3.3. Años desde el incendio

La variable debe ser categórica o no lineal:

- primer año;
- segundo año;
- posteriores.

No se debe asumir una caída idéntica para todos los taxones.

## 3.4. Temperatura del suelo

Variables recomendadas:

- media;
- mínima;
- máxima;
- tasa de calentamiento;
- anomalía;
- acumulación térmica.

No existe un umbral universal.

## 3.5. Humedad del suelo

Incluir:

- humedad volumétrica;
- precipitación;
- nieve;
- balance hídrico;
- días secos;
- velocidad de secado.

## 3.6. Nieve y deshielo

En montaña:

- duración del manto;
- fecha de deshielo;
- nieve residual;
- ritmo de fusión;
- orientación.

## 3.7. Fenología

Combinar:

- día del año;
- altitud;
- latitud;
- temperatura del suelo;
- deshielo;
- historial local.

## 3.8. Tipo de bosque

Registrar:

- conífera dominante;
- bosque mixto;
- frondosas;
- masa sana o quemada;
- edad;
- cobertura;
- mortalidad.

## 3.9. Historial local

Para colonias no pirófilas:

- recurrencia;
- fecha;
- abundancia;
- perturbaciones;
- cambios de vegetación;
- calidad taxonómica.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral común para todo el complejo.

## 4.2. Temperatura óptima

Los valores de cultivo no equivalen a fructificación silvestre.

## 4.3. Número fijo de días desde el deshielo

No se ha demostrado un retardo universal.

## 4.4. Respuesta obligatoria al fuego

Solo ciertos linajes son claramente pirófilos.

## 4.5. Severidad óptima universal

La respuesta depende de especie, bosque y suelo.

## 4.6. Hospedador obligatorio

El clado presenta amplitud ecológica y modos tróficos complejos.

## 4.7. pH óptimo universal

No existe una preferencia cuantitativa común a todo el complejo.

## 4.8. Viento, radiación y humedad relativa

No existen funciones específicas generalizables para todo el complejo.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Separación de submodelos

Implementar al menos:

- `morchella_elata_fire`;
- `morchella_elata_non_fire`.

## 5.2. Submodelo pirófilo

Incluir:

- incendio;
- años desde el fuego;
- severidad;
- tipo de bosque;
- nieve;
- temperatura del suelo;
- humedad;
- altitud;
- fecha.

## 5.3. Submodelo no pirófilo

Incluir:

- historial local;
- tipo de bosque;
- perturbaciones;
- temperatura del suelo;
- humedad;
- nieve;
- día del año.

## 5.4. Componente térmico

Incluir:

- calentamiento del suelo;
- temperatura media;
- mínimas;
- máximas;
- anomalías.

## 5.5. Componente hídrico

Incluir:

- humedad del suelo;
- precipitación;
- nieve;
- balance hídrico;
- días secos.

## 5.6. Control taxonómico

Cada observación debe indicar:

- `species_level`;
- `elata_complex`;
- `fire_associated`;
- `molecularly_confirmed`;
- `identification_confidence`.

## 5.7. Evidencia observacional

Registrar:

- fecha y coordenadas;
- abundancia;
- incendio y año;
- severidad;
- bosque;
- altitud;
- nieve;
- temperatura y humedad del suelo;
- fotografías;
- secuencia cuando exista;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- identificación taxonómica;
- historial local;
- incendio y años desde el fuego;
- día del año;
- temperatura del suelo;
- humedad del suelo;
- tipo de bosque;
- altitud.

## Recomendables

- severidad del incendio;
- fecha del incendio;
- nieve y deshielo;
- orientación;
- cobertura;
- mortalidad del arbolado;
- precipitación previa;
- balance hídrico.

## Experimentales

- acumulación térmica;
- profundidad de ceniza;
- carbono pirogénico;
- pH postincendio;
- radiación;
- viento;
- humedad relativa;
- modelos moleculares por taxón;
- detección remota de micrositios quemados.

“Experimental” significa que la variable puede ser útil, pero la literatura específica no permite asignarle una relación universal para todo el complejo *M. elata*.

---

# 7. Conclusiones

1. El complejo *Morchella elata* incluye varias especies ecológicamente distintas.

2. La morfología por sí sola no permite identificar con seguridad todos los taxones.

3. Algunas especies son pirófilas y otras fructifican en bosque no quemado.

4. El primer año después del incendio es especialmente importante para las especies pirófilas.

5. La severidad, el tipo de bosque y el clima modulan la respuesta postincendio.

6. La fenología es principalmente primaveral.

7. El calentamiento del suelo, la humedad y el deshielo son variables relevantes.

8. No existe un umbral universal de temperatura, lluvia o días desde el deshielo.

9. Los valores de cultivo no deben trasladarse directamente a campo.

10. La ecología trófica no puede reducirse a ectomicorriza o saprotrofía estricta para todo el complejo.

11. El historial local y la identificación molecular deben tener mucho peso.

12. Rainmapper debería utilizar submodelos separados para taxones pirófilos y no pirófilos.

---

# 8. Bibliografía seleccionada

## 1. Richard, F. et al. (2015)

**Título:** True morels (*Morchella*, Pezizales) of Europe and North America: evolutionary relationships inferred from multilocus data and a unified taxonomy.  
**Revista:** Mycologia, 107(2), 359–382.  
**DOI / página editorial:** https://doi.org/10.3852/14-166  
**Enlace:** https://www.tandfonline.com/doi/full/10.3852/14-166

**Aportación:** referencia taxonómica principal. Demuestra la diversidad oculta del clado Elata y la imposibilidad de tratar todos los registros históricos de *M. elata* como una única especie.

**Confianza:** muy alta para taxonomía.

## 2. Petrželová, I. y Sochor, M. (2019)

**Título:** How useful is the current species recognition concept for the determination of true morels? Insights from the Czech Republic.  
**Revista:** MycoKeys, 52, 17–43.  
**Texto completo:** https://mycokeys.pensoft.net/article/32335/

**Aportación:** analiza límites de especie, fiabilidad de ITS y criterios para reconocer taxones de *Morchella*.

**Confianza:** muy alta para control taxonómico.

## 3. Pilz, D. et al. (2004)

**Título:** Productivity and diversity of morel mushrooms in healthy, burned, and insect-damaged forests of northeastern Oregon.  
**Revista:** Forest Ecology and Management, 198, 367–386.  
**DOI / página editorial:** https://doi.org/10.1016/j.foreco.2004.05.028  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0378112704003494

**Aportación:** distingue tipos de colmenillas negras asociados y no asociados al fuego y compara productividad entre bosques sanos y quemados.

**Confianza:** alta para ecología postincendio del oeste norteamericano.

## 4. Pilz, D. et al. (2007)

**Título:** Ecology and Management of Morels Harvested From the Forests of Western North America.  
**Publicación:** USDA Forest Service, General Technical Report PNW-GTR-710.  
**Texto completo:** https://www.fs.usda.gov/pnw/pubs/pnw_gtr710.pdf

**Aportación:** revisión de referencia sobre ecología, fuego, fenología, hábitat, cosecha y gestión de colmenillas negras.

**Confianza:** alta como síntesis; parte de la nomenclatura es anterior a la revisión molecular moderna.

## 5. Larson, A. J. et al. (2016)

**Título:** Post-fire morel (*Morchella*) mushroom abundance, spatial structure, and harvest sustainability.  
**Revista:** Forest Ecology and Management, 377, 16–25.  
**DOI:** https://doi.org/10.1016/j.foreco.2016.06.038  
**Referencia:** https://forestgeo.si.edu/post-fire-morel-morchella-mushroom-abundance-spatial-structure-and-harvest-sustainability

**Aportación:** cuantifica abundancia y fuerte agregación espacial en más de mil parcelas postincendio.

**Confianza:** alta para estructura espacial y productividad postfuego.

## 6. Snabl, M. et al. (2023)

**Título:** New insights on post-fire morels (*Morchella* spp.) in Italy.  
**Revista:** Phytotaxa, 599(5).  
**Página editorial:** https://www.biotaxa.org/Phytotaxa/article/view/phytotaxa.599.5.2

**Aportación:** documenta y secuencia colmenillas del clado Elata en pinares quemados de Italia.

**Confianza:** alta para evidencia postincendio europea y necesidad de identificación molecular.

## 7. Winder, R. S. (2006)

**Título:** Cultural studies of *Morchella elata*.  
**Revista:** Mycological Research, 110, 612–623.  
**DOI / página editorial:** https://doi.org/10.1016/j.mycres.2006.02.003  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0953756206001134

**Aportación:** estudia crecimiento de aislados derivados de ascosporas y respuesta a temperatura.

**Confianza:** alta para fisiología en cultivo; baja para trasladar valores a fructificación natural.

## 8. Taşkın, H. et al. (2016)

**Título:** Four new morel (*Morchella*) species in the elata subclade from Turkey.  
**Revista:** Mycotaxon.  
**Texto completo:** https://www.fungipedia.org/media/kunena/attachments/5518/Taskinetal.2016MycotaxonMorchellaNewSpecies.pdf

**Aportación:** describe especies del subclado Elata y documenta hábitats con *Pinus*, *Cedrus*, *Juniperus*, *Abies* y *Quercus*.

**Confianza:** alta para diversidad y amplitud ecológica regional.

---

## Nota final sobre la evidencia

La principal dificultad no es la ausencia total de bibliografía, sino que gran parte de la literatura antigua utilizó “*Morchella elata*” para varios taxones.

La evidencia permite definir con confianza:

- fenología primaveral;
- importancia de temperatura del suelo, humedad y nieve;
- respuesta postincendio de determinados linajes;
- agregación espacial;
- necesidad de separar taxones pirófilos y no pirófilos.

No permite definir:

- una lluvia mínima;
- una temperatura óptima universal;
- días fijos desde el deshielo;
- severidad óptima común;
- hospedador obligatorio;
- un único modelo para todo el complejo.

La estructura más defendible para Rainmapper es: identificación taxonómica + submodelo de fuego/no fuego + temperatura del suelo + humedad + nieve + fenología + historial local.
