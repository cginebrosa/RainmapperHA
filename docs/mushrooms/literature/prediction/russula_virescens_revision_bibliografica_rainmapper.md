# Predicción de floradas de *Russula virescens*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Russula virescens* (Schaeff.) Fr.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Russula virescens* o revisa de forma directa su delimitación taxonómica, ecología, hospedadores, fenología o distribución.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Russula virescens* es muy escasa. Existen revisiones taxonómicas, estudios filogenéticos, inventarios de Russulaceae, trabajos sobre ectomicorrizas y publicaciones de distribución, pero no se ha localizado un modelo meteorológico validado y exclusivo de la especie que permita fijar una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre un episodio meteorológico y la aparición de carpóforos.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica.** Su presencia depende de árboles hospedadores vivos y de la continuidad del bosque.

2. **En Europa se asocia principalmente a frondosas.** La literatura la sitúa sobre todo con *Quercus* y *Fagus*, y también en algunos bosques mixtos con otras frondosas.

3. **La identidad taxonómica fuera de Europa es problemática.** Numerosos registros asiáticos y norteamericanos atribuidos históricamente a *R. virescens* corresponden a especies distintas. En 2025 se describió *Russula orientalovirescens* para gran parte del material del sudeste asiático anteriormente identificado como *R. virescens*.

4. **No deben utilizarse sin revisión los datos tropicales o norteamericanos.** El perfil de Rainmapper debe basarse prioritariamente en material europeo confirmado.

5. **La fenología europea es principalmente estival y de comienzos de otoño.** Los inventarios y monografías la sitúan normalmente entre verano y principio de otoño, con variación regional y altitudinal.

6. **La especie aparece en bosques caducifolios y mixtos, especialmente robledales y hayedos.** Los estudios de Russulaceae en Europa central y meridional la registran en comunidades con *Fagus*, *Quercus* y, en ocasiones, *Carpinus*.

7. **La distribución espacial parece ser localizada e irregular.** Puede reaparecer en los mismos lugares durante años, pero no es necesariamente abundante en todo bosque compatible.

8. **La meteorología debe considerarse un modulador, no el filtro principal.** La literatura específica no permite establecer qué ventana de precipitación o temperatura es óptima para la especie.

9. **La humedad del suelo es una variable ecológicamente plausible, pero no existe evidencia específica suficiente para declarar un umbral ni una superioridad universal frente a la precipitación.**

10. **La estructura y el estado del bosque probablemente influyen a través del hospedador y el microclima.** No existe, sin embargo, una función cuantitativa exclusiva de *R. virescens* para cobertura, área basimétrica o edad del rodal.

11. **La identificación visual puede fallar.** Las especies verdes y areoladas próximas requieren atención morfológica y, en algunos territorios, confirmación molecular.

12. **El historial local y la calidad taxonómica de las observaciones deben tener un peso muy alto.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Quercus* o *Fagus* | Filtro ecológico principal | Alta |
| Bosque caducifolio o mixto compatible | Filtro de aptitud | Alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Día del año | Ventana fenológica estival–otoñal | Media-alta |
| Humedad del suelo | Variable a calibrar | Media |
| Precipitación reciente y acumulada | Variable a calibrar | Media |
| Temperatura reciente | Modulador fenológico | Media |
| Cobertura y estructura del bosque | Modulador de microclima | Media |
| Altitud y orientación | Moduladores espaciales | Media |
| Calidad de identificación | Control imprescindible | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *R. virescens* mediante un filtro de frondosas —especialmente robles y hayas—, una ventana de verano–principio de otoño, variables hídricas y térmicas como señales a calibrar y un peso muy elevado del historial local. La literatura no permite fijar umbrales meteorológicos universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Russula virescens*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de otras especies verdes de *Russula* sin resultados específicos;
- publicaciones de composición química, nutrición o actividad farmacológica;
- registros asiáticos o americanos no revisados molecularmente;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos generales de hongos ectomicorrícicos sin resultados separados;
- inventarios donde la especie aparecía únicamente en una lista sin contexto ecológico;
- afirmaciones de hospedador basadas en registros taxonómicamente dudosos.

Se seleccionaron **siete referencias principales**, priorizando revisiones taxonómicas, filogenia, estudios de Russulaceae europeas y trabajos de ectomicorrizas.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Identidad taxonómica europea

*Russula virescens* fue descrita en Europa y constituye la referencia nominal del grupo de rúsulas verdes con el sombrero areolado.

La revisión de la subsección Amoeninae confirmó que:

- las especies europeas, asiáticas y norteamericanas forman linajes distintos;
- materiales parecidos visualmente pueden no ser *R. virescens*;
- la identificación requiere combinar morfología y secuencias;
- el nombre se utilizó históricamente de forma demasiado amplia.

**Conclusión útil:** Rainmapper debe considerar válidos con mayor confianza los registros europeos bien documentados.

## 2.2. Registros asiáticos mal atribuidos

Wisitrassameewong et al. describieron en 2025 *Russula orientalovirescens* para colecciones verdes y areoladas del sudeste asiático que durante años se habían tratado como *R. virescens*.

El estudio utilizó:

- ITS;
- `rpb2`;
- `tef1`;
- morfología detallada;
- comparación con material europeo.

Los resultados demostraron que la mayor parte de esas colecciones asiáticas representaban una especie diferente.

**Conclusión útil:** los estudios tropicales históricos bajo el nombre *R. virescens* no deben utilizarse para definir clima, hospedadores o fenología europeos sin revisión taxonómica.

## 2.3. Problema norteamericano

La literatura norteamericana ha reconocido varias especies del complejo *virescens–crustosa*, entre ellas *Russula parvovirescens*.

Los trabajos taxonómicos indican que:

- el grupo es mucho más diverso de lo supuesto;
- muchos registros históricos de “*R. virescens*” en Norteamérica no corresponden a la especie europea;
- las asociaciones con pinos y robles norteamericanos pertenecen a menudo a taxones diferentes.

**Conclusión útil:** no trasladar a Rainmapper datos norteamericanos salvo confirmación explícita de identidad.

## 2.4. Estrategia ectomicorrícica

*Russula* es un género ectomicorrícico y *R. virescens* se integra en esa estrategia.

La especie intercambia nutrientes y agua con raíces de árboles y recibe carbono del hospedador.

Esto implica que la fructificación depende potencialmente de:

- presencia de hospedador;
- vigor del árbol;
- continuidad del bosque;
- humedad del suelo;
- estado de la red micelial;
- historia del rodal.

**Conclusión útil:** la meteorología favorable fuera de un bosque compatible no debería producir una probabilidad alta.

## 2.5. Asociación con robles

La asociación con *Quercus* es una de las más repetidas para la especie europea.

Beenken estudió sistemática y ecología de *Russula* y documentó expresamente la combinación *R. virescens* + *Quercus robur*.

Otros inventarios europeos la sitúan en robledales y bosques mixtos con robles.

No existe evidencia suficiente para afirmar que todos los *Quercus* tengan la misma aptitud.

**Conclusión útil:** la presencia de roble debe recibir un peso alto, con calibración por especie y región.

## 2.6. Asociación con haya

Los inventarios de Russulaceae y estudios micológicos de hayedos europeos incluyen *R. virescens* en comunidades de *Fagus sylvatica*.

La especie aparece en:

- hayedos;
- hayedos con *Carpinus*;
- bosques mixtos con *Quercus*;
- mosaicos caducifolios.

El número de registros suele ser bajo, lo que impide deducir una productividad media estable.

**Conclusión útil:** *Fagus sylvatica* debe incluirse como hospedador compatible de alta confianza.

## 2.7. Bosques mixtos de frondosas

Los estudios de Russulaceae en Europa central muestran que *R. virescens* puede aparecer en bosques con:

- haya;
- roble;
- carpe;
- mezclas de frondosas.

Esto no significa que la especie sea indiferente al hospedador. Puede existir una asociación principal no identificable cuando varias raíces coexisten.

**Conclusión útil:** en bosque mixto, Rainmapper debe conservar la probabilidad si existen frondosas ectomicorrícicas compatibles.

## 2.8. Fenología europea

Las monografías e inventarios europeos sitúan la fructificación principalmente:

- durante verano;
- desde julio o agosto en muchas regiones;
- hasta comienzos de otoño;
- con prolongación variable según altitud y clima.

No se ha localizado una serie meteorológica exclusiva y prolongada de *R. virescens* que permita estimar:

- fecha media de inicio;
- retardo tras lluvia;
- temperatura de activación;
- duración de la campaña.

**Conclusión útil:** utilizar una ventana flexible de verano–principio de otoño, aprendida regionalmente.

## 2.9. Irregularidad y baja frecuencia

En varios inventarios europeos, *R. virescens* aparece con pocos registros.

Esto puede reflejar:

- rareza local;
- fenología breve;
- baja detectabilidad;
- identificación difícil;
- distribución en colonias pequeñas;
- condiciones ambientales poco frecuentes.

La revisión de genética poblacional de *Russula* indica que los genets del género suelen ser relativamente pequeños y que la recombinación local es frecuente.

Este resultado es general del género, no específico de *R. virescens*, pero ayuda a interpretar una distribución espacial fragmentada.

**Conclusión útil:** no asumir grandes colonias continuas; las observaciones históricas deben conservarse con resolución espacial fina.

## 2.10. Suelo

La literatura específica accesible no ofrece un modelo robusto de preferencias edáficas cuantitativas.

Se ha descrito en suelos de bosques caducifolios y mixtos con características diversas.

No existe soporte suficiente para imponer:

- pH óptimo;
- litología obligatoria;
- textura universal;
- profundidad mínima;
- contenido concreto de materia orgánica.

**Conclusión útil:** suelo y litología deben tratarse como variables exploratorias o calibrables.

## 2.11. Humedad y precipitación

No se ha localizado un estudio que relacione de forma específica la producción de *R. virescens* con:

- precipitación acumulada;
- humedad del suelo;
- evapotranspiración;
- sequía antecedente;
- número de días desde lluvia.

La necesidad de agua es fisiológicamente razonable, pero no debe convertirse en una afirmación cuantitativa específica.

**Conclusión útil:** incluir lluvia y humedad para aprendizaje, etiquetándolas como variables no calibradas bibliográficamente.

## 2.12. Temperatura

La fenología estival sugiere tolerancia a condiciones relativamente cálidas dentro del ciclo europeo, pero no existe evidencia suficiente para caracterizarla como estrictamente termófila ni para definir:

- óptimo térmico;
- máxima crítica;
- mínima de activación;
- efecto de amplitud diaria.

**Conclusión útil:** temperatura reciente y anomalía térmica deben entrar como moduladores, no como reglas.

## 2.13. Estado del hospedador

La condición ectomicorrícica hace plausible que el vigor del árbol influya en la fructificación.

Sin embargo, no se ha localizado un trabajo específico de *R. virescens* que relacione producción con:

- NDVI;
- crecimiento anual;
- estrés hídrico del árbol;
- defoliación;
- edad del rodal.

**Conclusión útil:** estas variables pueden considerarse experimentales, no demostradas para la especie.

## 2.14. Persistencia local

Las fuentes ecológicas describen la reaparición en los mismos lugares.

No existe una serie específica que cuantifique:

- tasa de recurrencia;
- longevidad de colonias;
- tamaño de los genets;
- distancia de expansión.

**Conclusión útil:** el historial local debe tener mucho peso, sin asumir una geometría o velocidad de expansión universal.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedadores

Priorizar:

- *Quercus*;
- *Fagus sylvatica*;
- bosques mixtos con frondosas ectomicorrícicas;
- *Carpinus* como contexto secundario documentado.

No existe una jerarquía cuantitativa universal.

## 3.2. Tipo de bosque

Variables recomendadas:

- robledal;
- hayedo;
- bosque mixto caducifolio;
- continuidad del dosel;
- edad y conservación del bosque;
- presencia de frondosas compatibles.

## 3.3. Historial local

Debe registrar:

- observaciones confirmadas;
- calidad taxonómica;
- recurrencia;
- abundancia;
- fecha;
- hospedadores;
- cambios del bosque.

## 3.4. Fenología

Incluir:

- día del año;
- fecha histórica local;
- altitud;
- región climática;
- anomalía térmica;
- comienzo observado de campaña.

## 3.5. Humedad

Variables candidatas:

- precipitación reciente;
- acumulados de varias semanas;
- humedad del suelo;
- duración de sequía;
- balance hídrico.

Deben calibrarse con datos propios.

## 3.6. Temperatura

Variables candidatas:

- temperatura media;
- mínimas;
- máximas;
- anomalía;
- temperatura del suelo.

No existe una forma de respuesta específica publicada.

## 3.7. Estructura forestal

Incluir cuando exista:

- cobertura;
- área basimétrica;
- densidad;
- altura;
- edad;
- perturbaciones.

El efecto exacto debe aprenderse regionalmente.

## 3.8. Calidad taxonómica

Cada observación debería registrar:

- fotografías del sombrero;
- patrón areolado;
- color;
- esporada;
- microscopía cuando exista;
- secuencia ITS;
- nivel de certeza;
- región biogeográfica.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral específico validado.

## 4.2. Número fijo de días después de la lluvia

No se ha localizado un retardo universal.

## 4.3. Temperatura óptima

No existe una temperatura de fructificación demostrada para la especie.

## 4.4. pH o litología óptimos

No existe soporte específico suficiente.

## 4.5. Hospedador exclusivo

Robles y hayas cuentan con la evidencia más sólida, pero no se ha demostrado exclusividad absoluta.

## 4.6. Fenología idéntica en toda Europa

La fecha cambia regionalmente y no existe una serie común.

## 4.7. Viento, radiación y humedad relativa

No existen funciones específicas generalizables.

## 4.8. Datos asiáticos o norteamericanos como equivalentes

La taxonomía moderna contradice esa equivalencia.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- *Quercus*;
- *Fagus*;
- bosque caducifolio o mixto;
- continuidad forestal;
- historial local;
- calidad de identificación.

## 5.2. Componente hídrico

Incluir:

- precipitación reciente;
- precipitación acumulada;
- humedad del suelo;
- balance hídrico;
- días secos.

Mantener inicialmente las variables separadas.

## 5.3. Componente térmico

Incluir:

- temperatura media;
- mínimas;
- máximas;
- anomalías;
- interacción con humedad.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- fecha histórica local;
- región climática;
- comienzo observado de campaña.

## 5.5. Estructura del bosque

Incluir:

- cobertura;
- área basimétrica;
- densidad;
- edad;
- composición;
- perturbaciones recientes.

## 5.6. Control taxonómico

Clasificar observaciones como:

- confirmada;
- probable;
- dudosa;
- secuenciada;
- fuera de Europa;
- complejo *virescens–crustosa*.

## 5.7. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- fotografías;
- hospedadores próximos;
- tipo de bosque;
- altitud;
- suelo;
- meteorología previa;
- esfuerzo de búsqueda;
- nivel de certeza.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- calidad de identificación;
- presencia de *Quercus* o *Fagus*;
- tipo de bosque;
- historial local;
- día del año;
- altitud;
- precipitación;
- humedad del suelo;
- temperatura.

## Recomendables

- cobertura;
- área basimétrica;
- orientación;
- pendiente;
- sequía antecedente;
- composición de frondosas;
- anomalías climáticas;
- perturbaciones.

## Experimentales

- NDVI del hospedador;
- temperatura del suelo;
- evapotranspiración;
- viento;
- radiación;
- humedad relativa;
- pH;
- litología;
- modelos separados por hospedador.

“Experimental” significa que la variable puede resultar útil, pero la literatura específica no permite asignarle todavía una relación universal sobre la fructificación de *R. virescens*.

---

# 7. Conclusiones

1. *Russula virescens* es una especie ectomicorrícica europea.

2. La asociación mejor respaldada es con frondosas, especialmente *Quercus* y *Fagus*.

3. Los registros asiáticos y norteamericanos históricos deben revisarse porque muchos corresponden a otras especies.

4. *Russula orientalovirescens* demuestra que las colecciones asiáticas verdes y areoladas no son necesariamente *R. virescens*.

5. La fenología europea es principalmente estival y de comienzos de otoño.

6. La especie puede aparecer de forma localizada e irregular incluso en bosques compatibles.

7. No existe un modelo meteorológico específico validado para su fructificación.

8. No existe una cantidad mínima de lluvia, temperatura óptima ni retardo post-lluvia universal.

9. La humedad, temperatura y estructura forestal deben utilizarse como variables de calibración.

10. El historial local y la calidad taxonómica deben tener un peso muy alto.

11. Rainmapper debería excluir o rebajar la confianza de registros extraeuropeos no confirmados molecularmente.

12. El modelo inicial debe combinar frondosas compatibles, fenología estival, estado hídrico, temperatura e historial local.

---

# 8. Bibliografía seleccionada

## 1. Wisitrassameewong, K. et al. (2020)

**Título:** Taxonomic revision of *Russula* subsection Amoeninae from Asia.  
**Revista:** MycoKeys, 69, 111–190.  
**DOI / texto completo:** https://doi.org/10.3897/mycokeys.69.53673  
**Enlace:** https://mycokeys.pensoft.net/article/53673/

**Aportación:** revisión filogenética de especies asiáticas, europeas y norteamericanas próximas; demuestra la separación geográfica y taxonómica de los linajes.

**Confianza:** muy alta para delimitación taxonómica.

## 2. Wisitrassameewong, K. et al. (2025)

**Título:** *Russula orientalovirescens* sp. nov., a common Southeast Asian green-cracking Russula previously identified as *R. virescens*.  
**Revista:** PLOS ONE.  
**DOI / texto completo:** https://doi.org/10.1371/journal.pone.0322545  
**Enlace:** https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0322545

**Aportación:** demuestra que gran parte del material del sudeste asiático atribuido a *R. virescens* representa una especie diferente.

**Confianza:** muy alta para control biogeográfico y taxonómico.

## 3. Buyck, B. et al. (2006)

**Título:** *Russula parvovirescens* sp. nov., a common but ignored species in the eastern United States.  
**Revista:** Mycologia.  
**Texto accesible:** https://www.researchgate.net/profile/Bart-Buyck/publication/6658811_Russula_parvovirescens_sp_nov_a_common_but_ignored_species_in_the_eastern_United_States/links/56dc190308aebe4638c029a9/Russula-parvovirescens-sp-nov-a-common-but-ignored-species-in-the-eastern-United-States.pdf

**Aportación:** demuestra la complejidad del grupo *virescens–crustosa* en Norteamérica y la poca fiabilidad de registros históricos bajo el nombre europeo.

**Confianza:** muy alta para diferenciación norteamericana.

## 4. Beenken, L. (2004)

**Título:** Die Gattung *Russula*: Untersuchungen zu ihrer Systematik anhand von Ektomykorrhizen.  
**Tesis doctoral, Ludwig-Maximilians-Universität München.**  
**Texto completo:** https://edoc.ub.uni-muenchen.de/3175/1/Beenken_Ludwig.pdf

**Aportación:** estudia sistemática y ectomicorrizas e incluye expresamente la asociación *R. virescens* + *Quercus robur*.

**Confianza:** alta para asociación con roble y estrategia ectomicorrícica.

## 5. Adamčík, S. et al. (2006)

**Título:** Diversity of Russulaceae in the Vihorlatské vrchy Mountains, Slovakia.  
**Revista:** Czech Mycology, 58, 43–66.  
**Texto completo:** https://czechmycology.org/_cm/CM58103.pdf

**Aportación:** inventario europeo de Russulaceae en hayedos, robledales y bosques mixtos, con registro explícito de *R. virescens*.

**Confianza:** alta para hábitat regional; no aporta modelo climático.

## 6. Zotti, M. et al. (2002)

**Título:** Mycological researches in beech woods in Western Ligurian Apennines.  
**Revista:** Cryptogamie, Mycologie, 23(2).  
**Texto completo:** https://sciencepress.mnhn.fr/sites/default/files/articles/pdf/cryptogamie-mycologie2002v23f2a4.pdf

**Aportación:** documenta la especie en el contexto de hayedos europeos y aporta información de comunidad forestal.

**Confianza:** media-alta para asociación con haya; no ofrece predicción individual.

## 7. Wang, P. et al. (2015)

**Título:** Recent advances in population genetics of ectomycorrhizal mushrooms *Russula* spp.  
**Revista:** Mycology, 6, 110–120.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC6106078/

**Aportación:** sintetiza que los genets de *Russula* suelen ser pequeños, la recombinación local frecuente y la dispersión efectiva a larga distancia limitada.

**Confianza:** alta para el género; evidencia indirecta para la estructura espacial de *R. virescens*.

---

## Nota final sobre la evidencia

La literatura de *R. virescens* es mucho más sólida para taxonomía y hospedadores que para meteorología.

La evidencia permite definir con bastante confianza:

- carácter ectomicorrícico;
- asociación europea con robles y hayas;
- fenología principalmente estival;
- distribución localizada;
- necesidad de revisar registros no europeos.

No permite definir:

- precipitación mínima;
- humedad óptima;
- temperatura de fructificación;
- días post-lluvia;
- pH o litología universal;
- estructura forestal óptima.

La estructura más defendible para Rainmapper es: identificación europea fiable + *Quercus/Fagus* + bosque caducifolio o mixto + ventana estival–otoñal + variables hídricas y térmicas a calibrar + historial local.
