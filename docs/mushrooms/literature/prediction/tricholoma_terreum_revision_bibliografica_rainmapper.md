# Predicción de floradas de *Tricholoma terreum*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Tricholoma terreum* (Schaeff.) P. Kumm.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Tricholoma terreum* y aporta información útil sobre fructificación, fenología, hospedador, suelo, estructura forestal, clima o identificación taxonómica.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Tricholoma terreum* es limitada. Existen trabajos taxonómicos sólidos, estudios de ectomicorrización con pinos, experimentos de fructificación controlada, inventarios forestales y publicaciones sobre fenología europea, pero no se ha localizado un modelo meteorológico validado y exclusivo de la especie que permita fijar una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre un episodio meteorológico y la aparición de carpóforos.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica asociada principalmente a pinos.** La asociación con *Pinus sylvestris* es especialmente sólida en Europa. También se ha documentado fructificación controlada con *Pinus densiflora*.

2. **Las referencias bajo *Picea* deben interpretarse con cautela.** La revisión molecular de *Tricholoma* del norte de Europa indica que *T. terreum* está asociado principalmente a *Pinus* y solo posiblemente a *Picea*. Parte de los registros históricos bajo pícea corresponde a especies próximas mal diferenciadas.

3. **Los suelos calizos o ricos en bases aparecen de forma recurrente.** La taxonomía moderna la sitúa principalmente en pinares sobre terrenos calcáreos. No existe, sin embargo, un intervalo universal de pH validado para la fructificación.

4. **La fenología europea es principalmente otoñal y tardía.** Los registros se concentran desde final de verano hasta finales de otoño, y pueden prolongarse hasta diciembre en regiones templadas o mediterráneas.

5. **La especie puede producir carpóforos en grupos densos o corros.** El historial local debe tener un peso alto porque la fructificación puede repetirse en zonas concretas dentro de un pinar adecuado.

6. **La estructura y edad del pinar influyen sobre la comunidad fúngica, pero faltan coeficientes exclusivos de la especie.** En los Pirineos se ha estudiado la producción ectomicorrícica en *Pinus sylvestris* según edad y orientación; las observaciones locales indicaban mayor presencia de *T. terreum* en laderas orientadas al norte, pero los autores señalaron que no existían datos suficientes para cuantificar ese efecto por especie.

7. **La asociación funcional con el pino está demostrada experimentalmente.** Estudios de genes de hidrofobinas mostraron expresión específica durante la formación de ectomicorrizas con *Pinus sylvestris*.

8. **La fructificación controlada es posible, pero difícil.** En cultivo abierto con plántulas de *Pinus densiflora*, *T. terreum* produjo un único carpóforo tras más de dos años. Esto confirma la dependencia del hospedador y la complejidad del proceso reproductivo.

9. **La meteorología debe tratarse como modulador y no como regla aislada.** La literatura general de fenología fúngica europea demuestra cambios asociados a temperatura y precipitación, pero no existe una función específica suficientemente robusta para *T. terreum*.

10. **No existe evidencia suficiente para asignar umbrales universales a precipitación, humedad del suelo, temperatura, viento, radiación o evapotranspiración.**

11. **La identificación taxonómica es importante.** *T. terreum* se ha confundido históricamente con *T. myomyces*, *T. gausapatum*, *T. triste* y otros tricolomas grises.

12. **Rainmapper debería priorizar el filtro de pinar, suelo calcáreo, fenología otoñal e historial local, y aprender las relaciones meteorológicas a partir de observaciones propias.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Pinus* compatible | Filtro ecológico principal | Muy alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Suelo calizo o rico en bases | Modulador de aptitud | Alta |
| Día del año | Ventana fenológica otoñal | Alta |
| Precipitación reciente y acumulada | Variable a calibrar | Media |
| Humedad del suelo | Estado hídrico a calibrar | Media |
| Temperatura reciente | Modulador fenológico | Media |
| Orientación y altitud | Moduladores microclimáticos | Media |
| Edad y estructura del pinar | Moduladores ecológicos | Media |
| Calidad de identificación | Control imprescindible | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *T. terreum* mediante un filtro fuerte de pinares —especialmente de *Pinus sylvestris*—, una preferencia flexible por suelos calcáreos, una ventana otoñal y un peso elevado del historial local. Las variables meteorológicas deben incorporarse para calibración, pero la bibliografía específica no permite fijar umbrales ni retardos universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Tricholoma terreum*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de otras especies de *Tricholoma* sin resultados específicos;
- trabajos centrados en composición química, contaminación o toxicología;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos de productividad total de hongos sin resultados separables para la especie;
- registros históricos bajo *T. myomyces* cuya identidad no podía comprobarse;
- observaciones bajo *Picea* que podían corresponder a otros tricolomas grises;
- afirmaciones locales sobre orientación o suelo sin metodología publicada suficiente.

Se seleccionaron **ocho referencias principales**, priorizando taxonomía molecular, ectomicorrización experimental, fructificación controlada, inventarios de pinares y estudios fenológicos europeos.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Delimitación taxonómica

Heilmann-Clausen et al. revisaron las especies de *Tricholoma* del norte de Europa mediante caracteres morfológicos y secuencias ITS.

Para *T. terreum*, el trabajo concluyó que:

- forma un linaje reconocible;
- *T. myomyces* no dispone de apoyo suficiente como especie separada en el material europeo analizado;
- existe confusión histórica con otros tricolomas grises;
- la ecología y el hospedador son importantes para interpretar los registros.

**Conclusión útil:** Rainmapper debería considerar *T. myomyces* como sinónimo documental sujeto a revisión y evitar incorporar automáticamente todos los registros antiguos.

## 2.2. Confusión con especies de pícea

Holec y colaboradores señalaron que ciertos tricolomas semejantes a *T. terreum* encontrados bajo *Picea* pueden corresponder a *Tricholoma borgsjoeënse* u otros taxones próximos.

Esto es relevante porque:

- los registros bajo pícea pueden inflar artificialmente la amplitud de hospedadores;
- la asociación con pino es mucho más consistente;
- el hospedador puede ayudar a corregir identificaciones dudosas.

**Conclusión útil:** los registros bajo *Picea* deben tener menor confianza salvo confirmación molecular o revisión especializada.

## 2.3. Asociación principal con *Pinus sylvestris*

La literatura taxonómica y experimental coincide en una asociación estrecha con *Pinus sylvestris*.

Mankel et al. describieron que:

- *T. terreum* se asocia normalmente con pino silvestre;
- la asociación con pícea es mucho menos clara;
- la formación de ectomicorriza desencadena cambios de expresión génica;
- determinadas hidrofobinas participan en el establecimiento de la simbiosis.

**Conclusión útil:** *Pinus sylvestris* debe recibir el peso máximo en el filtro europeo.

## 2.4. Ectomicorrización experimental

Los estudios de hidrofobinas y micorrización demostraron que *T. terreum* no es simplemente un hongo que aparece casualmente bajo pinos.

La especie:

- coloniza raíces;
- forma estructuras ectomicorrícicas;
- expresa genes específicos durante la simbiosis;
- depende funcionalmente de la relación con el árbol.

**Conclusión útil:** la presencia de hospedadores vivos y la continuidad del sistema radicular son condiciones ecológicas necesarias.

## 2.5. Fructificación controlada con *Pinus densiflora*

Yamada et al. mantuvieron cultivos ectomicorrícicos de varias especies de *Tricholoma* con plántulas de *Pinus densiflora* durante tres años.

Para *T. terreum*:

- se formaron ectomicorrizas;
- aparecieron primordios;
- solo uno llegó a desarrollar un carpóforo maduro;
- la fructificación se produjo aproximadamente veintiséis meses después del trasplante;
- los cuerpos fructíferos aparecieron cerca de las plántulas o del margen del sustrato.

El bajo éxito demuestra que la presencia de micelio y hospedador no garantiza fácilmente la fructificación.

**Conclusión útil:** el modelo debe predecir probabilidad de carpóforo visible, no mera presencia del hongo.

## 2.6. Suelo calcáreo

La revisión de Heilmann-Clausen et al. caracteriza la especie como asociada principalmente a pinares sobre terreno calcáreo.

Otras fuentes europeas coinciden en describirla en:

- suelos calcáreos;
- suelos neutros o ricos en bases;
- terrenos bien drenados;
- pinares de sustratos minerales.

No existe un estudio específico que establezca:

- pH mínimo;
- pH óptimo;
- porcentaje necesario de carbonatos;
- textura obligatoria.

**Conclusión útil:** litología calcárea y pH estimado deben modular la aptitud, sin convertirse en filtros absolutos.

## 2.7. Edad del bosque y orientación

Bonet, Fischer y Colinas estudiaron la relación entre edad forestal, orientación y producción de hongos ectomicorrícicos en pinares de *Pinus sylvestris* del Pirineo central.

El artículo recoge que los propietarios forestales observaban:

- mayor producción de *T. terreum* en orientaciones norte;
- mayor presencia de *Lactarius deliciosus* en orientaciones secas de suroeste.

Los propios autores advirtieron que no existían datos suficientes para cuantificar diferencias de rendimiento por especie y orientación.

El estudio sí demuestra a nivel comunitario que:

- edad;
- orientación;
- microclima;
- estructura del rodal;

afectan a la producción fúngica.

**Conclusión útil:** orientación norte es una hipótesis regional documentada, no una regla demostrada para toda la especie.

## 2.8. Presencia en pinares sometidos a condiciones ambientales diferentes

Rudawska et al. estudiaron comunidades ectomicorrícicas en plántulas y rodales de *Pinus sylvestris* bajo condiciones ambientales contrastadas.

*T. terreum* apareció en uno de los emplazamientos y no en otros.

El resultado muestra que:

- la presencia del pino no es suficiente;
- suelo, contaminación, vegetación y contexto local pueden filtrar la especie;
- las comunidades ectomicorrícicas cambian entre lugares.

El estudio no permite aislar cuál de esas variables determinó la presencia de *T. terreum*.

**Conclusión útil:** conservar múltiples variables edáficas y ambientales para aprendizaje, sin atribuir causalidad no demostrada.

## 2.9. Fenología otoñal

Los inventarios del norte y centro de Europa sitúan *T. terreum* principalmente entre:

- agosto o septiembre;
- octubre;
- noviembre;
- en algunas regiones, diciembre.

La revisión taxonómica nórdica aporta registros principalmente otoñales.

No existe una serie larga y exclusiva de la especie que permita calcular un calendario universal.

**Conclusión útil:** usar una ventana amplia de final de verano–otoño tardío, ajustada por región y altitud.

## 2.10. Fenología y cambio climático

Kauserud et al. analizaron registros históricos de fructificación de numerosos hongos noruegos y europeos y demostraron cambios importantes en la fecha y duración de las temporadas.

Aunque estos trabajos no proporcionan una función meteorológica diaria exclusiva para *T. terreum*, justifican que:

- las fechas históricas no son constantes;
- temperatura y precipitación regional modifican la fenología;
- la temporada de especies tardías puede prolongarse en años cálidos.

**Conclusión útil:** el día del año debe combinarse con anomalías térmicas y climáticas.

## 2.11. Transferencia de carbono desde pinos

Rapaport et al. rastrearon carbono fijado por árboles y lo detectaron en carpóforos de *T. terreum* y *Suillus collinitus* situados a distintas distancias de los pinos marcados.

El estudio confirma de forma directa que:

- el carbono fotosintético del árbol llega rápidamente al hongo;
- la fructificación está conectada al estado fisiológico del hospedador;
- la distancia al árbol y la red subterránea son relevantes.

No proporciona un modelo de productividad ni demuestra una relación directa con NDVI.

**Conclusión útil:** el vigor del pino puede ser una variable experimental razonable, pero no una relación cuantificada para Rainmapper.

## 2.12. Producción agrupada y recurrencia

La especie suele fructificar:

- en grupos numerosos;
- en líneas;
- en arcos o corros;
- en puntos repetidos del pinar.

No se ha localizado una tasa universal de expansión ni una serie que cuantifique la recurrencia anual de colonias individuales.

**Conclusión útil:** registrar geometría y localizaciones históricas con resolución fina.

## 2.13. Meteorología

No se ha localizado un estudio que modele exclusivamente para *T. terreum*:

- precipitación acumulada;
- humedad del suelo;
- temperatura máxima o mínima;
- evapotranspiración;
- días desde lluvia;
- déficit de presión de vapor.

Los estudios de productividad total en pinares muestran efectos generales de precipitación y temperatura, pero no permiten asignar coeficientes a esta especie.

**Conclusión útil:** las variables meteorológicas son candidatas necesarias para calibración, no relaciones ya establecidas.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador

Priorizar:

- *Pinus sylvestris*;
- otros *Pinus* con observaciones regionales confirmadas;
- pinares naturales o plantados;
- continuidad del sistema radicular.

Los registros bajo *Picea* deben recibir menor confianza.

## 3.2. Suelo

Variables recomendadas:

- litología calcárea;
- pH estimado;
- carbonatos;
- textura;
- drenaje;
- profundidad;
- materia orgánica.

No existe un umbral universal.

## 3.3. Historial local

Debe registrar:

- presencia confirmada;
- frecuencia;
- abundancia;
- geometría de grupos o corros;
- fecha;
- hospedador;
- suelo;
- perturbaciones.

## 3.4. Fenología

Incluir:

- día del año;
- fecha histórica local;
- altitud;
- región climática;
- anomalía térmica;
- primeras heladas;
- duración del otoño.

## 3.5. Componente hídrico

Variables candidatas:

- precipitación reciente;
- precipitación acumulada;
- humedad del suelo;
- balance hídrico;
- duración del periodo seco.

No existe una ventana específica publicada.

## 3.6. Temperatura

Variables candidatas:

- temperatura media;
- mínimas;
- máximas;
- anomalía;
- temperatura del suelo.

No existe una temperatura óptima demostrada.

## 3.7. Estructura forestal

Incluir cuando esté disponible:

- edad;
- área basimétrica;
- cobertura;
- densidad;
- altura;
- gestión reciente;
- orientación.

## 3.8. Estado del hospedador

Variables experimentales:

- NDVI/EVI;
- estrés hídrico;
- defoliación;
- crecimiento anual;
- mortalidad;
- densidad de raíces.

La transferencia de carbono está demostrada, pero no su relación cuantitativa con la cosecha.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral específico validado.

## 4.2. Número fijo de días post-lluvia

No se ha localizado un retardo universal.

## 4.3. Temperatura óptima

No existe una temperatura de fructificación transferible.

## 4.4. Orientación norte obligatoria

La observación está documentada en el Pirineo, pero no fue cuantificada por especie.

## 4.5. pH óptimo exacto

La preferencia calcícola está respaldada, pero no existe un intervalo universal.

## 4.6. Asociación regular con pícea

La taxonomía moderna obliga a revisar muchos registros bajo *Picea*.

## 4.7. Efecto universal de edad o aclareo

No existe un modelo individual de la especie.

## 4.8. Viento, radiación y humedad relativa

No se han localizado funciones específicas generalizables.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- presencia de *Pinus*;
- prioridad de *P. sylvestris*;
- suelo calcáreo o rico en bases;
- continuidad forestal;
- historial local;
- calidad taxonómica.

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
- heladas;
- temperatura del suelo.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica;
- duración del otoño.

## 5.5. Estructura del pinar

Incluir:

- edad;
- densidad;
- área basimétrica;
- cobertura;
- orientación;
- gestión.

## 5.6. Control taxonómico

Clasificar observaciones como:

- confirmada;
- probable;
- posible *T. myomyces*;
- posible especie gris próxima;
- secuenciada;
- hospedador dudoso.

## 5.7. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- fotografías;
- especie de pino;
- suelo;
- orientación;
- estructura forestal;
- meteorología previa;
- esfuerzo de búsqueda;
- nivel de certeza.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- calidad de identificación;
- especie de *Pinus*;
- tipo de pinar;
- historial local;
- litología o pH;
- día del año;
- altitud;
- precipitación;
- humedad del suelo;
- temperatura.

## Recomendables

- orientación;
- área basimétrica;
- edad;
- cobertura;
- densidad;
- carbonatos;
- textura;
- anomalías climáticas;
- gestión reciente.

## Experimentales

- NDVI del pino;
- temperatura del suelo;
- evapotranspiración;
- viento;
- radiación;
- humedad relativa;
- transferencia de carbono;
- modelos separados por especie de pino.

“Experimental” significa que la variable puede resultar útil, pero la literatura específica no permite asignarle todavía una relación universal sobre la fructificación de *T. terreum*.

---

# 7. Conclusiones

1. *Tricholoma terreum* es una especie ectomicorrícica ligada principalmente a pinos.

2. *Pinus sylvestris* cuenta con la evidencia ecológica y experimental más sólida.

3. La asociación con *Picea* debe revisarse porque puede ocultar errores taxonómicos.

4. Los suelos calcáreos o ricos en bases constituyen una preferencia ecológica consistente.

5. La fenología es principalmente otoñal y tardía.

6. La formación de ectomicorriza con pino está demostrada molecular y experimentalmente.

7. La fructificación controlada es posible, pero difícil y poco frecuente.

8. La edad, orientación y estructura del pinar pueden influir, pero no existe una función exclusiva validada.

9. La orientación norte es una observación regional, no una regla universal.

10. No existe una cantidad mínima de lluvia, temperatura óptima ni retardo post-lluvia universal.

11. La calidad taxonómica y el historial local deben tener un peso muy alto.

12. Rainmapper debería combinar pino, suelo calcáreo, fenología otoñal, agua disponible, temperatura y estructura forestal.

---

# 8. Bibliografía seleccionada

## 1. Heilmann-Clausen, J. et al. (2017)

**Título:** Taxonomy of *Tricholoma* in northern Europe based on ITS sequence data and morphological characters.  
**Revista:** Persoonia, 38, 38–57.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5645187/  
**PDF:** https://macroecointern.dk/pdf-reprints/Heilmann-Clausen_Persoonia_2017.pdf

**Aportación:** referencia taxonómica principal. Delimita *T. terreum*, revisa la sinonimia con *T. myomyces* y documenta asociación principal con *Pinus* sobre suelos calcáreos.

**Confianza:** muy alta para taxonomía, hospedador y suelo.

## 2. Mankel, A. et al. (2002)

**Título:** Identification of a hydrophobin gene that is developmentally regulated in the ectomycorrhizal fungus *Tricholoma terreum*.  
**Revista:** Applied and Environmental Microbiology, 68, 1408–1413.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC123729/

**Aportación:** demuestra la asociación funcional con *Pinus sylvestris* y la regulación genética durante la formación de ectomicorriza.

**Confianza:** muy alta para simbiosis; no aporta meteorología de fructificación.

## 3. Yamada, A. et al. (2007)

**Título:** Sustainable fruit-body formation of edible mycorrhizal *Tricholoma* species for 3 years in open pot culture with pine seedling hosts.  
**Revista:** Mycoscience.  
**Consulta:** https://www.researchgate.net/publication/226583503_Sustainable_fruit-body_formation_of_edible_mycorrhizal_Tricholoma_species_for_3_years_in_open_pot_culture_with_pine_seedling_hosts

**Aportación:** primera fructificación controlada documentada de *T. terreum* con *Pinus densiflora*; muestra la dificultad de completar el desarrollo del carpóforo.

**Confianza:** alta para dependencia del hospedador y cultivo; no transferible directamente a campo.

## 4. Bonet, J. A., Fischer, C. R. y Colinas, C. (2004)

**Título:** The relationship between forest age and aspect on the production of sporocarps of ectomycorrhizal fungi in *Pinus sylvestris* forests of the central Pyrenees.  
**Revista:** Forest Ecology and Management, 203, 157–175.  
**DOI / página editorial:** https://doi.org/10.1016/j.foreco.2004.07.063  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0378112704006358

**Aportación:** analiza edad y orientación en pinares y recoge la observación local de mayor producción de *T. terreum* en laderas norte, señalando que faltan datos específicos para cuantificarla.

**Confianza:** alta para contexto forestal; baja-media para la orientación concreta de la especie.

## 5. Rudawska, M. et al. (2011)

**Título:** Species and functional diversity of ectomycorrhizal fungal communities on Scots pine seedlings in contrasting forest nurseries.  
**Revista:** Annals of Forest Science, 68, 5–15.  
**Página editorial:** https://link.springer.com/article/10.1007/s13595-010-0002-x

**Aportación:** registra *T. terreum* de forma específica en uno de los emplazamientos y demuestra que las comunidades asociadas a *Pinus sylvestris* cambian entre condiciones ambientales.

**Confianza:** media-alta para presencia y filtro ambiental; no identifica el factor causal exacto.

## 6. Holec, J. et al. (2012)

**Título:** *Tricholoma borgsjoeënse* found in the Czech Republic and notes on grey *Tricholoma* species under *Picea*.  
**Revista:** Czech Mycology, 64, 177–188.  
**Texto completo:** https://czechmycology.org/_cmo/CM64210.pdf

**Aportación:** demuestra que materiales semejantes a *T. terreum* bajo pícea pueden corresponder a otros taxones.

**Confianza:** alta para control taxonómico y revisión de hospedadores.

## 7. Kauserud, H. et al. (2008)

**Título:** Mushroom fruiting and climate change.  
**Revista:** Proceedings of the National Academy of Sciences, 105, 3811–3814.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC2268836/

**Aportación:** demuestra cambios históricos en la fenología de hongos otoñales europeos en relación con clima.

**Confianza:** alta para contexto fenológico general; no ofrece una ecuación exclusiva de *T. terreum*.

## 8. Rapaport, A. et al. (2025)

**Título:** Rapid and chemically diverse carbon transfer from trees to ectomycorrhizal fungal sporocarps.  
**Revista:** Functional Ecology.  
**Página editorial:** https://besjournals.onlinelibrary.wiley.com/doi/10.1111/1365-2435.14541

**Aportación:** detecta carbono fijado por pinos en carpóforos de *T. terreum*, confirmando la conexión funcional entre árbol y fructificación.

**Confianza:** alta para transferencia de carbono; no aporta un modelo de productividad.

---

## Nota final sobre la evidencia

La literatura de *T. terreum* es sólida para:

- taxonomía;
- asociación con pinos;
- preferencia por suelos calcáreos;
- naturaleza ectomicorrícica;
- fenología otoñal;
- complejidad de la fructificación.

Es insuficiente para definir:

- precipitación mínima;
- humedad óptima;
- temperatura de fructificación;
- días post-lluvia;
- orientación óptima universal;
- estructura forestal óptima.

La estructura más defendible para Rainmapper es: identificación fiable + *Pinus* —especialmente *P. sylvestris*— + suelo calcáreo + ventana otoñal + variables hídricas y térmicas a calibrar + historial local.
