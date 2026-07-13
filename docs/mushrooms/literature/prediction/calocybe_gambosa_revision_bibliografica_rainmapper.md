# Predicción de floradas de *Calocybe gambosa*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Calocybe gambosa* (Fr.) Donk  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Calocybe gambosa* y aporta información útil sobre fenología, hábitat, suelo o fructificación.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La bibliografía científica dedicada específicamente a predecir las floradas de *Calocybe gambosa* es escasa. No se ha localizado un modelo validado para la especie que permita establecer una cantidad mínima de lluvia, una temperatura óptima de fructificación o un número fijo de días entre un episodio meteorológico y la aparición de carpóforos.

La evidencia específica disponible permite sostener con razonable confianza las siguientes conclusiones:

1. **Es una especie de fructificación primaveral muy marcada.** Las series fenológicas británicas muestran que su primera aparición se ha adelantado a lo largo de las últimas décadas.

2. **La temperatura previa a la fructificación afecta claramente a la fecha de aparición.** En el estudio fenológico más directamente relevante, los años con marzo más cálido presentaron una primera fructificación más temprana.

3. **No se detectó una relación con la precipitación mensual acumulada en los tres primeros meses del año.** Los autores advirtieron que este resultado no demuestra que el agua sea irrelevante; probablemente indica que una escala mensual es demasiado gruesa para detectar la respuesta a humedad.

4. **La fecha exacta de fructificación no puede explicarse únicamente mediante temperatura.** El mismo estudio propone que la precipitación o humedad a escalas de pocos días probablemente interviene, pero no pudo determinar esa relación.

5. **El hábitat principal son praderas, pastizales, bordes de bosque y claros herbosos.** La especie forma anillos o arcos de brujas mediante expansión radial del micelio en el suelo.

6. **No debe modelarse como una especie ectomicorrícica.** La evidencia reciente la caracteriza como descomponedora del suelo y demuestra interacciones directas con las plantas herbáceas de sus anillos.

7. **El micelio modifica de forma intensa el suelo.** En el frente activo se han observado acumulación de nutrientes, descenso del pH, aumento de la hidrofobicidad y reducción de la diversidad fúngica local.

8. **La hidrofobicidad generada por el propio micelio puede reducir la humedad del suelo en el frente activo.** Esto introduce una retroalimentación importante: la presencia de un anillo establecido puede modificar localmente la disponibilidad de agua y no limitarse a responder pasivamente a la meteorología.

9. **La especie muestra fidelidad espacial mediante anillos persistentes.** Para Rainmapper, el historial de localizaciones conocidas será probablemente más informativo que muchas variables ambientales generales.

10. **No existe evidencia suficiente para asignar un efecto específico al viento, radiación, humedad relativa o evapotranspiración sobre la fructificación.** Pueden utilizarse como variables auxiliares para estimar el microclima, pero no como factores demostrados para la especie.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Localización histórica del anillo o corro | Filtro espacial principal | Muy alta |
| Día del año | Modulador fenológico | Muy alta |
| Temperatura de final de invierno y comienzo de primavera | Predictor de adelanto o retraso | Alta |
| Temperatura reciente | Modulador fenológico | Alta |
| Precipitación o humedad reciente a escala corta | Variable a calibrar | Media |
| Pradera, pastizal o borde herboso | Filtro ecológico | Alta |
| Estructura y continuidad del tapiz vegetal | Modulador de aptitud | Media |
| Propiedades locales del suelo | Modulador ecológico | Media |
| Historial local de observaciones | Calibración principal | Muy alta |

**Conclusión práctica:** Rainmapper debería tratar *C. gambosa* como una especie primaveral y espacialmente muy persistente. El modelo mínimo debe combinar lugares conocidos o hábitats herbosos compatibles, temperatura de las semanas y meses previos, día del año y una señal de humedad reciente. La literatura no permite fijar umbrales numéricos universales de lluvia o temperatura.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Calocybe gambosa*?

Se revisó literatura más amplia que la finalmente citada. Se descartaron:

- estudios de otros hongos formadores de anillos sin resultados para *C. gambosa*;
- artículos sobre *Calocybe indica* u otras especies del género;
- trabajos de composición química, nutrición o actividad farmacológica;
- páginas divulgativas con umbrales meteorológicos no documentados;
- afirmaciones tradicionales sobre lluvia o fechas sin análisis científico;
- estudios generales de hongos primaverales que no separaban la especie.

Se seleccionaron **cinco trabajos principales** porque son los que aportan información directamente útil sobre fenología, hábitat, suelo y biología de *C. gambosa*. La escasez de publicaciones predictivas específicas es una conclusión de la revisión y no debe compensarse añadiendo estudios genéricos.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Adelanto de la fructificación primaveral

Mattock, Gange y Gange analizaron registros británicos de hongos primaverales desde mediados del siglo XX. *Calocybe gambosa* fue una de las especies objetivo.

El estudio encontró una tendencia significativa hacia una aparición más temprana. En la serie del sur de Wiltshire, la fecha media de primera fructificación pasó de una aparición tradicional alrededor del 23 de abril a fechas progresivamente anteriores. En la década de 2000, la media se situaba aproximadamente alrededor del 22 de abril, aunque la variación anual seguía siendo considerable.

La importancia del trabajo no reside en esa fecha concreta, que corresponde al sur de Inglaterra, sino en demostrar que:

- la primera fructificación responde a las condiciones climáticas del año;
- la fenología no es fija;
- el calendario tradicional puede desplazarse;
- el calentamiento primaveral puede adelantar la campaña.

**Conclusión útil:** Rainmapper debe usar el día del año como variable flexible y corregida por temperatura, no como una fecha fija.

## 2.2. Relación con la temperatura de marzo

El mismo estudio encontró una relación altamente significativa entre la fecha de primera fructificación de *C. gambosa* y la temperatura media de marzo.

El patrón fue claro:

- marzo más cálido → primera aparición más temprana;
- marzo más frío → primera aparición más tardía.

Esta es la evidencia meteorológica específica más sólida localizada para la especie.

Los autores interpretaron que temperaturas más altas pueden favorecer el crecimiento previo del micelio y permitir que el hongo acumule los recursos necesarios para fructificar antes. Esa explicación fue propuesta como mecanismo plausible, no demostrada experimentalmente.

**Conclusión útil:** la temperatura previa a la estación de fructificación debe entrar en el modelo. No debe utilizarse una temperatura óptima universal, sino una relación regional entre anomalía térmica y adelanto o retraso.

## 2.3. Ausencia de relación con lluvia mensual

Mattock et al. no encontraron relación entre la primera fecha de fructificación y los totales mensuales de precipitación de los primeros meses del año.

Este resultado debe interpretarse con precisión:

- no demuestra que la humedad no importe;
- demuestra que los acumulados mensuales utilizados no explicaron la fecha de primera aparición;
- los propios autores señalaron que la escala mensual podía ser demasiado gruesa;
- sugirieron que la respuesta a humedad podría ocurrir a escala de pocos días.

No existe en ese trabajo una cuantificación del periodo exacto ni de la cantidad de lluvia necesaria.

**Conclusión útil:** Rainmapper debe probar precipitación y humedad en ventanas cortas, pero no puede considerar demostrada ninguna ventana concreta.

## 2.4. Hábitat de praderas y bordes herbosos

La literatura específica describe *C. gambosa* como un hongo que forma anillos en:

- praderas;
- pastizales;
- céspedes y jardines;
- claros herbosos;
- bordes de bosque;
- sistemas de colinas con vegetación herbácea.

El trabajo de Zotti et al. se desarrolló en una pradera arbolada de un jardín botánico a 837 m de altitud, manejada mediante siega e irrigación ocasional. El estudio de Graziosi et al. analizó igualmente anillos asociados a comunidades herbáceas.

Estos datos no justifican afirmar que la especie necesita un manejo concreto ni una altitud determinada. Sí permiten establecer que el sustrato herboso y el suelo con materia orgánica constituyen su hábitat principal.

**Conclusión útil:** la máscara ecológica debe priorizar praderas y bordes herbosos persistentes, no bosques cerrados ni filtros de hospedador arbóreo.

## 2.5. Formación y persistencia de anillos

*Calocybe gambosa* forma anillos de brujas producidos por la expansión radial del micelio.

Zotti et al. estudiaron tres anillos y diferenciaron:

- zona exterior no colonizada;
- frente fúngico activo;
- zona interior ya atravesada por el micelio.

La existencia de un frente radial implica que la probabilidad espacial no es homogénea dentro del área ocupada. La fructificación se vincula al anillo activo, no necesariamente al centro histórico.

**Conclusión útil:** cuando Rainmapper disponga de geometrías o fotografías históricas, debería representar el corro como una estructura espacial expansiva y no como un punto estático.

La literatura seleccionada no proporciona una velocidad anual universal de expansión para *C. gambosa*.

## 2.6. Modificación del suelo por el micelio

Zotti et al. observaron cambios significativos en 13 de las 24 propiedades físico-químicas analizadas en el frente activo.

Entre los resultados se encontraban:

- aumento de amonio;
- aumento de nitrato;
- aumento de fósforo disponible;
- aumento de potasio;
- acumulación de otros nutrientes;
- disminución del pH;
- aumento de la hidrofobicidad;
- reducción de la diversidad fúngica del suelo;
- cambios marcados en la comunidad bacteriana.

El estudio demuestra que el hongo modifica activamente el ambiente edáfico durante la expansión.

**Conclusión útil:** el suelo no es simplemente una variable externa que condiciona al hongo. Un anillo establecido genera su propio patrón local de nutrientes y disponibilidad de agua.

## 2.7. Hidrofobicidad y condiciones de sequedad local

El incremento de la hidrofobicidad en el frente activo reduce la capacidad del suelo para retener o infiltrar agua. Los autores relacionaron esta condición con la instauración de condiciones locales de sequedad.

Este resultado no permite concluir que la sequía meteorológica favorezca la fructificación. Al contrario, describe una modificación causada por el propio micelio.

Su relevancia para predicción es que:

- la humedad medida a escala de estación puede no representar el frente del anillo;
- la respuesta a lluvia puede variar entre la zona exterior, el frente y el interior;
- los anillos maduros pueden presentar una dinámica hídrica propia.

**Conclusión útil:** las observaciones locales y el conocimiento de la posición del frente pueden ser más útiles que una capa de humedad de resolución gruesa.

## 2.8. Interacción con la vegetación herbácea

Graziosi et al. estudiaron de forma específica las interacciones entre *C. gambosa* y las plantas en sus anillos.

Los resultados mostraron:

- cambios en la composición vegetal entre zonas del anillo;
- disminución de la diversidad en el frente activo;
- transición relativa de dicotiledóneas hacia monocotiledóneas;
- colonización endofítica de plantas herbáceas por el micelio;
- comportamiento perjudicial sobre raíces en determinados ensayos;
- efectos estimulantes de compuestos volátiles sobre el crecimiento aéreo en otras condiciones.

Estos resultados muestran una interacción compleja y no reducible a una simple asociación positiva o negativa.

**Conclusión útil:** la composición y el estado de la vegetación pueden aportar señales sobre la ubicación del frente, pero no existe todavía una variable vegetal sencilla y validada para predecir la fructificación.

---

# 3. Factores predictivos defendibles

## 3.1. Historial espacial de anillos conocidos

Es probablemente el factor más fuerte para uso práctico.

La expansión radial y la persistencia de los anillos implican que:

- una localización confirmada mantiene valor predictivo en años posteriores;
- el lugar exacto de fructificación puede desplazarse hacia el exterior;
- una observación puntual debería conservar información sobre el contorno del corro;
- el centro geométrico no representa necesariamente la zona activa.

Rainmapper debería registrar, cuando sea posible:

- geometría del anillo;
- radio aproximado;
- orientación de los arcos visibles;
- fecha de cada observación;
- desplazamiento entre campañas.

## 3.2. Día del año y temperatura previa

La fenología primaveral y la relación con la temperatura de marzo cuentan con evidencia específica.

Variables recomendadas:

- día del año;
- temperatura media de final de invierno;
- temperatura media de marzo o periodo regional equivalente;
- anomalía térmica respecto a la climatología;
- acumulación térmica como variable experimental.

La mención de acumulación térmica es una propuesta de modelización. No se ha localizado un umbral específico de grados-día para la especie.

## 3.3. Humedad reciente

La ausencia de correlación con lluvia mensual no elimina la posible influencia del agua.

Rainmapper debería conservar:

- precipitación de pocos días;
- número de días desde la última lluvia;
- humedad superficial del suelo;
- duración del periodo seco;
- anomalía de humedad.

Estas variables deben considerarse candidatas a calibración, no factores ya demostrados.

## 3.4. Hábitat herboso

El filtro de aptitud debería priorizar:

- praderas permanentes;
- pastizales;
- bordes herbosos;
- claros;
- parques y jardines con césped;
- áreas con continuidad del suelo y baja alteración física.

No existe evidencia suficiente para definir una única comunidad vegetal obligatoria.

## 3.5. Suelo

La actividad del anillo está vinculada a cambios en:

- nutrientes;
- pH;
- hidrofobicidad;
- microbiota;
- materia orgánica.

Sin embargo, los estudios revisados describen principalmente los cambios causados por el hongo, no valores iniciales que permitan predecir dónde se instalará.

Por tanto, Rainmapper no debe convertir los valores observados dentro del frente en requisitos previos de hábitat.

## 3.6. Altitud y región climática

La primera fecha de fructificación cambia con el régimen térmico. La altitud puede utilizarse como modulador climático, pero no se ha identificado una relación específica universal entre altitud y presencia.

El modelo debe aprender calendarios regionales y altitudinales a partir de observaciones.

---

# 4. Factores que no están demostrados específicamente

## 4.1. Cantidad mínima de lluvia

No existe una cifra validada para desencadenar la fructificación de *C. gambosa*.

## 4.2. Número de días después de la lluvia

La hipótesis de una respuesta a escala de pocos días procede de la interpretación de Mattock et al., pero el estudio no determinó el retardo.

## 4.3. Temperatura óptima de fructificación

La temperatura de marzo explica parte de la variación de la fecha de primera aparición en el sur de Inglaterra, pero no define un óptimo fisiológico ni un umbral universal.

## 4.4. Necesidad de suelo calcáreo

La especie se registra con frecuencia en praderas calcáreas, pero los trabajos predictivos seleccionados no justifican tratar el sustrato calcáreo como requisito universal.

## 4.5. Asociación obligatoria con arbustos o árboles concretos

No se ha encontrado evidencia científica suficiente para considerar espinos, endrinos u otros arbustos como hospedadores obligatorios. La especie no debe modelarse mediante una relación ectomicorrícica con ellos.

## 4.6. Viento, radiación, humedad relativa y evapotranspiración

No se localizaron funciones específicas que relacionen estas variables con la fructificación de *C. gambosa*.

## 4.7. Velocidad universal de expansión del anillo

Los anillos se expanden radialmente, pero no se ha identificado en la bibliografía seleccionada una tasa generalizable para Rainmapper.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Componente espacial

Priorizar:

- observaciones históricas;
- geometría conocida del anillo;
- distancia al frente observado en campañas anteriores;
- continuidad del terreno herboso;
- ausencia de transformación reciente del suelo.

## 5.2. Componente fenológico

Incluir:

- día del año;
- temperatura de final de invierno;
- temperatura media de marzo o periodo equivalente;
- anomalía térmica;
- fecha media histórica local.

## 5.3. Componente hídrico

Probar por separado:

- precipitación reciente;
- humedad del suelo;
- días desde lluvia;
- duración del periodo seco.

No imponer inicialmente una relación fija.

## 5.4. Hábitat

Usar como filtro:

- pradera;
- pastizal;
- borde herboso;
- claro;
- parque o jardín con suelo no removido;
- historial de anillos.

## 5.5. Evidencia observacional

Cada registro debería incluir:

- fecha;
- coordenadas;
- identificación fiable;
- abundancia;
- disposición en arco o círculo;
- radio estimado;
- posición respecto a observaciones anteriores;
- tipo de vegetación;
- siega, pastoreo o alteración;
- meteorología previa;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- historial local de presencia;
- día del año;
- temperatura de final de invierno y primavera;
- hábitat herboso;
- altitud;
- observación de anillo o arco;
- continuidad del suelo.

## Recomendables

- precipitación reciente;
- humedad superficial;
- días desde lluvia;
- anomalía térmica;
- tipo de manejo;
- cobertura y composición del tapiz herbáceo;
- geometría y radio del anillo.

## Experimentales

- grados-día;
- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- índices de vegetación;
- pH y nutrientes como predictores previos;
- estimación automática del avance radial.

“Experimental” significa que su inclusión puede ser útil para calibración, pero la literatura específica no permite asignarles todavía una relación general con la fructificación.

---

# 7. Conclusiones

1. *Calocybe gambosa* presenta una fenología primaveral muy marcada.

2. La temperatura de marzo mostró una relación específica y significativa con la fecha de primera fructificación en una serie británica prolongada.

3. Los años más cálidos adelantaron la aparición.

4. La lluvia mensual de los primeros meses del año no explicó la fecha de fructificación en ese estudio.

5. Ese resultado no demuestra que la humedad sea irrelevante; la respuesta puede producirse a escalas temporales más cortas.

6. No existe una cantidad mínima de lluvia ni un retardo post-lluvia validado para la especie.

7. La especie está vinculada principalmente a praderas, pastizales, bordes herbosos y claros.

8. Forma anillos persistentes y espacialmente estructurados; el historial local debe ser uno de los predictores principales.

9. El frente activo modifica nutrientes, pH, hidrofobicidad, microbiota y vegetación.

10. Las propiedades observadas dentro del frente no deben confundirse con requisitos iniciales del hábitat.

11. No existe evidencia suficiente para modelarla como ectomicorrícica ni para imponer un hospedador leñoso.

12. Rainmapper debería usar un modelo sencillo basado en ubicación histórica, fenología térmica, hábitat herboso y humedad reciente a calibrar.

---

# 8. Bibliografía seleccionada

## 1. Mattock, G., Gange, A. C. y Gange, E. C. (2007)

**Título:** Spring fungi are fruiting earlier.  
**Revista:** British Wildlife, 18(4), 267–272.  
**Texto accesible:** https://www.researchgate.net/publication/291045031_Spring_fungi_are_fruiting_earlier  
**Copia PDF:** https://www.researchgate.net/profile/Alan_Gange/publication/291045031_Spring_fungi_are_fruiting_earlier/links/5ece33a7299bf1c67d204913/Spring-fungi-are-fruiting-earlier.pdf

**Aportación:** es la fuente meteorológica específica más relevante. Analiza la primera fecha de fructificación de *C. gambosa*, su adelanto histórico y su relación con la temperatura media de marzo. No encontró relación con la lluvia mensual analizada.

**Confianza:** alta para fenología y efecto regional de temperatura; limitada para precipitación a escala corta y para extrapolación fuera del sur de Inglaterra.

## 2. Zotti, M. et al. (2021)

**Título:** Riding the wave: Response of bacterial and fungal microbiota associated with the spread of the fairy ring fungus *Calocybe gambosa*.  
**Revista:** Applied Soil Ecology, 163, 103963.  
**DOI:** https://doi.org/10.1016/j.apsoil.2021.103963  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S0929139321000846

**Aportación:** estudio específico de tres anillos. Documenta cambios en nutrientes, pH, hidrofobicidad y comunidades microbianas en el frente activo.

**Confianza:** alta para procesos edáficos locales; no estudia desencadenantes meteorológicos de fructificación.

## 3. Graziosi, S. et al. (2025)

**Título:** Analysis of Plant–Fungus Interactions in *Calocybe gambosa* Fairy Rings.  
**Revista:** Plants, 14(18), 2884.  
**DOI:** https://doi.org/10.3390/plants14182884  
**Texto completo:** https://www.mdpi.com/2223-7747/14/18/2884

**Aportación:** analiza cambios en la comunidad vegetal, colonización de raíces y efectos directos e indirectos del hongo sobre plantas herbáceas.

**Confianza:** alta para interacciones en el anillo estudiado; no ofrece un modelo meteorológico.

## 4. Zotti, M. et al. (2020)

**Título:** Fungal fairy rings as ecosystem engineer structures in grasslands.  
**Referencia y contexto:** citada en los trabajos específicos posteriores sobre *C. gambosa* y anillos de brujas.

**Aportación:** proporciona el marco ecológico para interpretar los anillos como estructuras que modifican suelo, vegetación y biodiversidad.

**Confianza:** media para aplicación directa a *C. gambosa*; se utiliza únicamente como apoyo conceptual y no para fijar parámetros.

## 5. Wollan, A. K. et al. (2008)

**Título:** Modelling and predicting fungal distribution patterns using herbarium data.  
**Revista:** Journal of Biogeography.  
**Consulta:** https://www.researchgate.net/publication/227549137_Modelling_and_predicting_fungal_distribution_patterns_using_herbarium_data

**Aportación:** incluye *C. gambosa* entre especies utilizadas para estudiar la capacidad de variables climáticas y de distribución para modelar presencia fúngica.

**Confianza:** media-baja para floradas; útil para distribución potencial, no para fecha de fructificación.

---

## Nota final sobre la evidencia

Se localizaron numerosas fichas micológicas y fuentes de recolección que atribuyen a *C. gambosa* intervalos concretos de lluvia, temperatura o días de espera. No se incorporaron porque no aportaban una metodología científica verificable.

También se revisaron estudios generales sobre hongos primaverales y anillos de brujas. Solo se utilizaron cuando aportaban resultados separados para *C. gambosa* o ayudaban a interpretar procesos observados directamente en la especie.

La conclusión principal es deliberadamente prudente: la temperatura previa explica parte del calendario, el hábitat y la persistencia espacial están bien documentados, pero la señal hídrica exacta y los umbrales de fructificación siguen sin estar establecidos.
