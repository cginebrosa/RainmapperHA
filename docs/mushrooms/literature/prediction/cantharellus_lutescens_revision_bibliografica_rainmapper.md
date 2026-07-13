# Predicción de floradas de *Cantharellus lutescens*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Cantharellus lutescens* (Pers.) Fr.  
**Nombre actualmente aceptado en buena parte de la literatura taxonómica:** *Craterellus lutescens* (Fr.) Fr.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que menciona y estudia explícitamente *Cantharellus lutescens* o *Craterellus lutescens* y aporta información útil sobre fructificación, fenología, hábitat, clima, gestión forestal o perturbación.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las fructificaciones de *Cantharellus lutescens* —actualmente tratado con frecuencia como *Craterellus lutescens*— es limitada. Existe un trabajo clásico dedicado expresamente a relacionar la descarga de esporas y el desarrollo de los cuerpos fructíferos con factores climáticos, y varios estudios posteriores sobre productividad, gestión forestal, perturbación física y distribución en pinares. Sin embargo, no se ha localizado un modelo moderno, validado y transferible que permita fijar una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre la precipitación y la aparición de carpóforos.

Las conclusiones más sólidas son:

1. **Es una especie ectomicorrícica ligada principalmente a coníferas.** La literatura europea y mediterránea la registra de forma recurrente en pinares, incluidos pinares de *Pinus nigra*, y también en otros bosques de coníferas.

2. **El microhábitat húmedo y musgoso aparece de forma consistente.** La especie se encuentra con frecuencia en suelos forestales con cobertura de musgo y elevada retención de humedad. Esta asociación es ecológicamente importante, pero no equivale a un umbral cuantitativo de humedad.

3. **La fructificación se concentra principalmente entre final de verano, otoño e inicio del invierno, según región.** La fenología varía con latitud, altitud y condiciones anuales.

4. **Existe evidencia específica de relación con factores climáticos, pero la literatura accesible no permite convertirla en reglas numéricas universales.** El trabajo clásico de Kälin y Ayer estudió expresamente el desarrollo de los carpóforos y la descarga de esporas en relación con el clima. La relevancia del estudio es alta, pero sus resultados deben interpretarse dentro del bosque y periodo investigados.

5. **La estructura y gestión del bosque afectan a la producción.** Estudios de aclareo citados en la literatura especializada muestran que la reducción de la producción tras tratamientos forestales puede ser temporal y que las diferencias entre intensidades de aclareo pueden desaparecer en menos de seis años.

6. **El pisoteo reduce la fructificación visible.** Experimentos suizos de larga duración encontraron menor número y tamaño de carpóforos en áreas sometidas a pisoteo, aunque el micelio parecía persistir.

7. **Cortar o arrancar los cuerpos fructíferos no mostró una reducción de las cosechas futuras en experimentos prolongados.** Debe distinguirse la recolección del daño físico al suelo.

8. **La presencia en pinares productivos no implica producción estable.** La biomasa puede variar mucho entre años, incluso en hábitats adecuados.

9. **No existe evidencia suficiente para asignar de forma independiente efectos universales al viento, humedad relativa, radiación o evapotranspiración.** Pueden ayudar a describir el secado del suelo, pero no están demostrados como predictores específicos de la especie.

10. **El historial local debe tener un peso muy alto.** La especie suele formar colonias extensas y persistentes; una localización confirmada constituye una señal más fiable que muchas variables generales.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Pinar o bosque de coníferas compatible | Filtro ecológico principal | Alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Humedad del suelo | Estado hídrico | Media-alta |
| Precipitación reciente y acumulada | Señal de recarga | Media-alta |
| Cobertura de musgo | Indicador de microhábitat | Media-alta |
| Temperatura reciente | Modulador fenológico | Media |
| Día del año | Ventana fenológica regional | Alta |
| Cobertura y estructura del bosque | Modulador de productividad | Media-alta |
| Aclareos, caminos y pisoteo | Penalización temporal o local | Alta |
| Altitud y orientación | Moduladores microclimáticos | Media |

**Conclusión práctica:** Rainmapper debería modelar *C. lutescens* mediante un filtro de pinares o coníferas compatibles, una señal de humedad persistente, una fenología regional de final de verano–invierno y una penalización por alteración del suelo o gestión reciente. No deben incorporarse umbrales meteorológicos exactos sin calibración local.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Cantharellus lutescens*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios centrados exclusivamente en *Cantharellus cibarius*;
- trabajos sobre *Craterellus tubaeformis* sin resultados separados para *C. lutescens*;
- publicaciones de química, nutrición o actividad farmacológica;
- guías micológicas y páginas divulgativas sin metodología científica;
- cifras meteorológicas sin una fuente identificable;
- modelos generales de productividad fúngica que no incluían la especie o no permitían separarla;
- estudios norteamericanos sobre “chanterelles” de identidad taxonómica distinta.

Se seleccionaron **siete referencias principales**, priorizando trabajos donde la especie aparece explícitamente y que aportan información útil sobre clima, hábitat, gestión, perturbación o productividad.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Identidad taxonómica

El nombre *Cantharellus lutescens* aparece de forma habitual en la literatura forestal y micológica del siglo XX. En la clasificación moderna, la especie se sitúa generalmente en el género *Craterellus* como *Craterellus lutescens*.

Esta cuestión no es meramente nomenclatural. Las búsquedas bibliográficas deben incluir:

- *Cantharellus lutescens*;
- *Craterellus lutescens*;
- en trabajos más antiguos, combinaciones o nombres cercanos como *Cantharellus xanthopus* o *Cantharellus aurora*, cuando los autores los trataron como sinónimos.

No todos esos nombres se han utilizado siempre con el mismo criterio. Rainmapper debería conservar un identificador taxonómico estable y registrar los sinónimos documentales por separado.

**Conclusión útil:** la búsqueda y trazabilidad bibliográfica deben contemplar ambos géneros, pero no mezclar automáticamente especies próximas.

## 2.2. Relación específica con factores climáticos

Kälin y Ayer publicaron un estudio expresamente dedicado a la descarga de esporas y el desarrollo de los cuerpos fructíferos de *Cantharellus lutescens* en relación con factores climáticos.

Es la referencia más directamente orientada a la pregunta predictiva. El trabajo confirma que:

- el desarrollo del carpóforo puede seguirse en relación con el clima;
- la maduración y la liberación de esporas responden a las condiciones ambientales;
- la fructificación no es un evento instantáneo, sino un proceso de desarrollo.

La publicación es antigua y no se ha localizado una versión digital completa de acceso abierto que permita extraer con seguridad todos sus resultados cuantitativos. Por esta razón, esta revisión no reproduce cifras ni umbrales.

**Conclusión útil:** existe evidencia específica de dependencia climática, pero no se deben inventar valores numéricos a partir de referencias secundarias.

## 2.3. Fenología

Los inventarios europeos sitúan la fructificación principalmente en:

- final del verano;
- otoño;
- en regiones suaves, también comienzo del invierno.

La duración de la campaña depende de:

- altitud;
- latitud;
- llegada de las primeras heladas;
- persistencia de humedad;
- régimen térmico del bosque.

La literatura específica revisada no permite establecer una fecha fija de inicio o final aplicable a toda Europa.

**Conclusión útil:** Rainmapper debe utilizar una ventana fenológica amplia y regional, ajustada por observaciones y anomalías climáticas.

## 2.4. Pinares y asociación con coníferas

La especie aparece repetidamente en pinares europeos y mediterráneos.

En Istria, Croacia, un estudio preliminar sobre hongos ectomicorrícicos comestibles en rodales de *Pinus nigra* registró *C. lutescens* como la especie más abundante del inventario.

Los trabajos españoles sobre productividad y gestión de hongos forestales también la incluyen entre las especies comerciales de pinares.

Esta evidencia permite afirmar que:

- los pinares son un hábitat prioritario;
- *Pinus nigra* es un hospedador o contexto forestal claramente documentado;
- otros bosques de coníferas pueden ser compatibles;
- la presencia del árbol no garantiza por sí sola una florada.

**Conclusión útil:** el tipo de conífera y el historial local deben formar parte del filtro de hábitat.

## 2.5. Musgo y humedad superficial

La especie se registra de forma característica en suelos musgosos de bosques de coníferas. La cobertura de musgo puede:

- conservar humedad;
- moderar temperatura;
- reducir evaporación directa;
- proteger primordios;
- indicar menor alteración del suelo.

La literatura revisada utiliza esta asociación de forma recurrente, pero no proporciona un porcentaje universal de cobertura de musgo ni demuestra que el musgo sea obligatorio en todos los hábitats.

**Conclusión útil:** la cobertura de musgo es un indicador de microhábitat relevante, no un requisito binario.

## 2.6. Aclareo forestal

Pilz, Molina y Mayo estudiaron el efecto de diferentes intensidades de aclareo sobre la producción de rebozuelos en bosques jóvenes.

La literatura posterior cita que el efecto de los distintos tratamientos sobre la producción de *C. lutescens* persistió menos de seis años. Esto sugiere:

- una reducción o modificación temporal de la fructificación tras la intervención;
- capacidad de recuperación a medio plazo;
- importancia del tiempo transcurrido desde el tratamiento;
- interacción entre estructura del bosque y microclima.

Debe señalarse una limitación: el artículo de Pilz et al. se desarrolló en el noroeste de Estados Unidos y la nomenclatura de los rebozuelos en esa región ha sido históricamente compleja. La atribución directa a *C. lutescens* procede de cómo la literatura posterior resumió el estudio, por lo que su aplicación taxonómica europea debe ser prudente.

**Conclusión útil:** Rainmapper puede penalizar temporalmente masas recién aclaradas, pero no asumir un efecto permanente ni universal.

## 2.7. Pisoteo y compactación

Los experimentos suizos de larga duración sobre recolección incluyeron una colonia de *Cantharellus lutescens* sometida a pisoteo.

Los resultados indicaron:

- reducción del número de carpóforos;
- reducción de su tamaño;
- persistencia aparente del micelio;
- recuperación potencial cuando cesa la perturbación.

Los autores propusieron que el pisoteo podría destruir primordios próximos a la superficie sin eliminar necesariamente el micelio.

**Conclusión útil:** caminos, zonas recreativas, alta presión de recolectores y compactación deben reducir la probabilidad de fructificación visible.

## 2.8. Recolección

Egli et al. compararon durante décadas la recolección mediante corte, arranque y ausencia de recolección.

No observaron una reducción de la producción futura atribuible al método de recogida. Esta conclusión se refiere a la extracción del carpóforo y debe separarse del pisoteo asociado al acceso.

**Conclusión útil:** Rainmapper no debería penalizar automáticamente una zona por el hecho de que se recolecten setas, salvo que exista alteración física del suelo.

## 2.9. Variabilidad interanual

Los inventarios prolongados de hongos forestales muestran grandes diferencias entre años en abundancia y fenología. *C. lutescens* forma parte de esa dinámica.

La variabilidad puede proceder de:

- clima;
- humedad antecedente;
- temperatura;
- estructura del bosque;
- producción del hospedador;
- estado del micelio;
- perturbaciones;
- procesos biológicos no medidos.

**Conclusión útil:** el modelo debe producir probabilidades y reconocer incertidumbre incluso en colonias conocidas.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y formación forestal

El factor ecológico principal es la presencia de coníferas compatibles.

Rainmapper debería distinguir:

- *Pinus nigra*;
- otros *Pinus*;
- abetales y otros bosques de coníferas documentados;
- bosques mixtos con coníferas;
- ausencia de hospedador compatible.

No existe una jerarquía universal cuantificada entre especies arbóreas.

## 3.2. Historial local

Las colonias pueden producir repetidamente en zonas concretas.

Variables recomendadas:

- presencia histórica;
- frecuencia de observaciones;
- extensión de la colonia;
- años sin fructificación;
- abundancia máxima observada;
- perturbaciones desde la última campaña.

El historial local debería tener un peso superior al de una aptitud ambiental puramente teórica.

## 3.3. Humedad del suelo

La asociación con zonas húmedas y musgosas respalda la importancia de la humedad superficial.

El modelo puede utilizar:

- humedad del suelo;
- precipitación reciente;
- precipitación acumulada;
- días secos consecutivos;
- retención edáfica;
- orientación y cobertura.

No existe un valor mínimo específico validado.

## 3.4. Temperatura

La temperatura influye en desarrollo, maduración y duración de la temporada, pero la literatura seleccionada no permite fijar un óptimo universal.

Variables defendibles:

- temperatura media reciente;
- temperatura mínima;
- primeras heladas;
- anomalía térmica;
- temperatura del suelo cuando exista.

## 3.5. Fenología

El día del año debe interactuar con:

- altitud;
- región climática;
- anomalía térmica;
- llegada de lluvias;
- historial local de primera aparición.

No debe actuar como un calendario rígido.

## 3.6. Musgo y microhábitat

La cobertura de musgo puede funcionar como indicador de:

- humedad persistente;
- baja perturbación;
- microclima estable;
- suelo adecuado.

Debe tratarse como variable continua o de clase, no como requisito absoluto.

## 3.7. Gestión y perturbación

Variables relevantes:

- intensidad del aclareo;
- años desde el tratamiento;
- caminos;
- compactación;
- pisoteo;
- eliminación de musgo;
- movimiento de suelo.

La respuesta puede ser temporal y no debe interpretarse como pérdida permanente de aptitud.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No se ha localizado un umbral validado y transferible.

## 4.2. Número fijo de días después de la lluvia

La literatura específica confirma relación climática, pero no un retardo universal.

## 4.3. Temperatura óptima

No existe un valor universal respaldado por los estudios seleccionados.

## 4.4. Necesidad absoluta de musgo

La asociación es fuerte, pero no se ha demostrado que la especie no pueda fructificar sin cobertura musgosa.

## 4.5. Densidad forestal óptima

Los efectos de gestión dependen del bosque, clima y tiempo desde la intervención.

## 4.6. Viento, radiación y humedad relativa

No se localizaron funciones específicas generalizables para la especie.

## 4.7. Efecto negativo de cortar o arrancar

Los experimentos de larga duración no respaldan esa afirmación.

## 4.8. Recuperación exacta tras aclareo

La referencia de menos de seis años procede de un sistema concreto y no constituye una regla universal.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- conífera compatible;
- tipo de pinar;
- continuidad forestal;
- cobertura;
- musgo;
- historial local;
- ausencia de alteración severa.

## 5.2. Componente hídrico

Incluir:

- precipitación reciente;
- acumulados de varias semanas;
- humedad del suelo;
- duración del periodo seco;
- retención edáfica;
- orientación.

## 5.3. Componente térmico

Incluir:

- temperatura media;
- mínimas;
- primeras heladas;
- temperatura del suelo;
- anomalías.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- desplazamiento anual de la campaña.

## 5.5. Perturbación

Penalizar según:

- intensidad del aclareo;
- años desde la intervención;
- pisoteo;
- proximidad a caminos;
- compactación;
- pérdida de musgo.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- identificación fiable;
- especie arbórea dominante;
- cobertura de musgo;
- humedad aparente;
- orientación;
- altitud;
- perturbación;
- meteorología previa;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- conífera dominante;
- tipo de bosque;
- historial local;
- precipitación reciente;
- humedad del suelo;
- día del año;
- temperatura;
- altitud;
- perturbaciones recientes.

## Recomendables

- cobertura de musgo;
- orientación;
- pendiente;
- temperatura del suelo;
- precipitación acumulada;
- días secos consecutivos;
- cobertura forestal;
- años desde aclareo;
- proximidad a caminos.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- déficit de presión de vapor;
- índices de vigor del hospedador;
- clasificación automática de musgos;
- estimación espacial de colonias.

“Experimental” significa que la literatura específica no permite asignarles un efecto universal sobre la fructificación de *C. lutescens*.

---

# 7. Conclusiones

1. *Cantharellus lutescens* se trata actualmente con frecuencia como *Craterellus lutescens*.

2. La especie está ligada principalmente a bosques de coníferas, especialmente pinares.

3. *Pinus nigra* aparece documentado como hábitat productivo en estudios mediterráneos.

4. El microhábitat húmedo y musgoso es una asociación ecológica consistente.

5. Existe un estudio clásico específico que relaciona desarrollo del carpóforo y descarga de esporas con factores climáticos.

6. La literatura accesible no permite extraer de forma fiable umbrales meteorológicos universales.

7. La fenología se concentra principalmente entre final de verano, otoño e inicio del invierno, con variación regional.

8. La gestión forestal puede reducir temporalmente la productividad.

9. El pisoteo disminuye el número y tamaño de carpóforos, aunque el micelio puede persistir.

10. Cortar o arrancar no mostró una reducción de las futuras cosechas en los experimentos prolongados revisados.

11. La presencia histórica de colonias debe ser uno de los predictores más fuertes.

12. Rainmapper debería combinar bosque compatible, humedad persistente, temperatura, fenología y perturbación, sin imponer cifras no demostradas.

---

# 8. Bibliografía seleccionada

## 1. Kälin, I. y Ayer, F. (1983/1984)

**Título:** Sporenabwurf und Fruchtkörperentwicklung des Goldstieligen Pfifferlings (*Cantharellus lutescens*) im Zusammenhang mit Klimafaktoren.  
**Revista:** Mycologia Helvetica, 1, 67–88.  
**Referencia bibliográfica accesible en:** https://research.fs.usda.gov/download/treesearch/5298.pdf

**Aportación:** estudio específico sobre descarga de esporas, desarrollo de carpóforos y factores climáticos.

**Confianza:** alta por especificidad; limitada para esta revisión porque no se localizó el texto completo abierto y no se reproducen cifras secundarias.

## 2. Egli, S. et al. (2006)

**Título:** Mushroom picking does not impair future harvests – results of a long-term study in Switzerland.  
**Revista:** Biological Conservation, 129, 271–276.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S0006320705004726

**Aportación:** experimento prolongado sobre corte, arranque y pisoteo. Incluye referencias específicas a una colonia de *C. lutescens* afectada por pisoteo.

**Confianza:** alta para recolección y perturbación física en el sistema estudiado.

## 3. Pilz, D., Molina, R. y Mayo, J. (2006)

**Título:** Effects of thinning young forests on chanterelle mushroom production.  
**Revista:** Journal of Forestry, 104, 9–14.  
**Referencia:** https://www.researchgate.net/publication/233710180_Effects_of_Thinning_Young_Forests_on_Chanterelle_Mushroom_Production

**Aportación:** analiza el efecto de distintas intensidades de aclareo sobre la producción de rebozuelos. La literatura posterior cita una recuperación de las diferencias en menos de seis años.

**Confianza:** media para *C. lutescens* europeo debido a la complejidad taxonómica de los rebozuelos norteamericanos.

## 4. Straatsma, G., Ayer, F. y Egli, S. (2001)

**Título:** Species richness, abundance, and phenology of fungal fruit bodies over 21 years in a Swiss forest plot.  
**Revista:** Mycological Research, 105, 515–523.  
**DOI:** https://doi.org/10.1017/S0953756201004154  
**Texto:** https://www.fungifun.org/docs/mushrooms/Species%20richness%20abundance%20and%20phenology%20of%20fungal%20fruit%20bodies%20over%2021%20years%20in%20a%20Swiss%20forest%20plot.pdf

**Aportación:** serie semanal de 21 años que documenta la enorme variabilidad interanual y fenológica de hongos forestales, con referencia explícita a *C. lutescens* y al trabajo climático de Kälin y Ayer.

**Confianza:** alta para contexto fenológico y variabilidad; no ofrece un modelo exclusivo moderno de la especie.

## 5. Diminić, D. et al.

**Título:** Productivity of edible mycorrhizal fungi in Austrian pine (*Pinus nigra*) stands in Istria, Croatia – preliminary results.  
**Referencia:** https://www.researchgate.net/publication/260293725_Productivity_of_edible_mycorrhizal_fungi_in_Austrian_pine_Pinus_nigra_stands_in_Istria_Croatia_-_preliminary_results

**Aportación:** registra *C. lutescens* como la especie más abundante en los rodales de *Pinus nigra* estudiados.

**Confianza:** media-alta para asociación con pino laricio y productividad local; estudio preliminar.

## 6. Alday, J. G. et al. (2017)

**Título:** Mushroom biomass and diversity are driven by different spatio-temporal scales along Mediterranean elevation gradients.  
**Revista:** Scientific Reports, 7, 45824.  
**Texto completo:** https://www.nature.com/articles/srep45824

**Aportación:** incluye explícitamente *Craterellus lutescens* entre las especies de los pinares mediterráneos analizados y demuestra que biomasa y diversidad responden a escalas espaciales y temporales diferentes.

**Confianza:** media para la especie concreta; alta para contextualizar la necesidad de modelos espaciales y temporales.

## 7. Olah, B. et al. (2020)

**Título:** Assessing the potential of forest stands for mushroom production.  
**Revista:** Forests, 11, 282.  
**Texto completo:** https://www.mdpi.com/1999-4907/11/3/282

**Aportación:** incluye *Cantharellus lutescens* en un sistema de evaluación de aptitud de rodales y utiliza variables de cobertura forestal derivadas de literatura especializada.

**Confianza:** media para aptitud estructural; no es un modelo de inicio de florada.

---

## Nota final sobre la evidencia

La literatura específica sobre *C. lutescens* es más reducida y menos accesible que la disponible para *Boletus edulis*. El trabajo climático más directamente relevante es antiguo y no se ha localizado en acceso abierto completo, por lo que no se han reproducido valores cuantitativos derivados de citas secundarias.

También se revisaron estudios de *Craterellus tubaeformis*, rebozuelos norteamericanos y productividad general de hongos. No se utilizaron para fijar parámetros específicos cuando la identidad taxonómica o la variable de respuesta no permitían separar *C. lutescens*.

La conclusión defendible es sencilla: bosque de coníferas, microhábitat húmedo y musgoso, fenología de final de verano–invierno, sensibilidad a perturbación física y gestión, y una respuesta climática real pero todavía insuficientemente cuantificada para establecer umbrales universales.
