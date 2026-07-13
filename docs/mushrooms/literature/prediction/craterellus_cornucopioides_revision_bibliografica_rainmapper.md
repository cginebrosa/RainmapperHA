# Predicción de floradas de *Craterellus cornucopioides*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Craterellus cornucopioides* (L.) Pers.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que menciona o estudia explícitamente *Craterellus cornucopioides* y aporta información útil sobre fructificación, fenología, hábitat, clima, estructura forestal o productividad.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las fructificaciones de *Craterellus cornucopioides* es escasa. Existen estudios de comunidades forestales, inventarios de productividad, series fenológicas amplias y trabajos sobre asociaciones ecológicas, pero no se ha localizado un modelo meteorológico moderno y validado para la especie que permita fijar una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre un episodio meteorológico y la aparición de carpóforos.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica asociada principalmente a bosques de frondosas.** Los estudios europeos la registran especialmente en hayedos, robledales y bosques mixtos de frondosas.

2. **El haya aparece como uno de los contextos forestales más consistentes.** En un estudio irlandés de producción de hongos silvestres comestibles, casi toda la producción registrada de *C. cornucopioides* se concentró en parcelas de haya.

3. **También aparece con robles y carpes.** Estudios de comunidades fúngicas en hayedos y robledales documentan afinidad con *Fagus*, *Quercus* y *Carpinus*, aunque no permiten establecer una jerarquía universal de hospedadores.

4. **La especie se asocia a microhábitats húmedos, umbríos y con hojarasca o musgo.** Esta asociación aparece de forma recurrente, pero no existe un umbral cuantitativo de humedad o cobertura de musgo.

5. **La fructificación se concentra normalmente en verano tardío y otoño, y puede prolongarse hasta noviembre en Europa templada.** La ventana exacta depende de región, altitud y clima anual.

6. **La fenología de los hongos europeos está cambiando con el calentamiento.** Series de herbarios y observaciones prolongadas muestran desplazamientos de fechas de fructificación en muchas especies, incluida *C. cornucopioides* en los conjuntos analizados.

7. **La altitud de fructificación también puede desplazarse.** Estudios alpinos de largo plazo incluyen *C. cornucopioides* entre las especies utilizadas para detectar desplazamientos altitudinales de fructificación.

8. **La productividad es muy irregular.** En inventarios plurianuales, la especie puede aparecer en pocas parcelas y producir poco en unos años, mientras que observaciones locales indican abundancia elevada en campañas favorables.

9. **No existe evidencia suficiente para convertir lluvia, temperatura, humedad relativa, viento o radiación en reglas numéricas específicas.** Estas variables deben tratarse como candidatas a calibración, no como relaciones ya demostradas.

10. **El historial local de presencia debe tener mucho peso.** La especie suele fructificar en puntos o manchas repetitivas dentro de bosques adecuados; una localización confirmada es más informativa que una aptitud ambiental general.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hayedo, robledal o frondosa compatible | Filtro ecológico principal | Alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Humedad del suelo y de la hojarasca | Estado hídrico | Media-alta |
| Precipitación reciente y acumulada | Señal de recarga | Media |
| Sombra y cobertura forestal | Modulador microclimático | Media-alta |
| Hojarasca y musgo | Indicador de microhábitat | Media |
| Día del año | Ventana fenológica | Alta |
| Temperatura reciente | Modulador fenológico | Media |
| Altitud | Modulador climático y fenológico | Media |
| Alteración del suelo y del bosque | Penalización de aptitud | Media-alta |

**Conclusión práctica:** Rainmapper debería modelar *C. cornucopioides* mediante un filtro de bosques de frondosas —especialmente haya y roble—, una señal de humedad persistente en suelo y hojarasca, una fenología regional de verano tardío–otoño y un peso elevado del historial local. No deben incorporarse umbrales meteorológicos exactos sin calibración propia.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Craterellus cornucopioides*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios centrados exclusivamente en composición química, nutrición o propiedades medicinales;
- trabajos de *Craterellus fallax* u otros taxones norteamericanos sin equivalencia taxonómica clara;
- estudios generales de Cantharellaceae sin resultados identificables para la especie;
- páginas divulgativas con umbrales meteorológicos no documentados;
- cifras de lluvia, temperatura o humedad procedentes de libros secundarios sin metodología verificable;
- inventarios en los que la especie aparecía solo en una lista sin información ecológica útil;
- modelos de productividad fúngica total sin desglose de especie.

Se seleccionaron **siete referencias principales**, priorizando trabajos sobre hábitat, productividad, fenología, altitud y comunidades forestales donde la especie aparece explícitamente.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Identidad taxonómica y alcance geográfico

En Europa, *Craterellus cornucopioides* está bien reconocido como la trompeta negra o trompeta de los muertos.

En Norteamérica, parte de los registros históricos bajo ese nombre corresponden a *Craterellus fallax*. Los análisis filogenéticos demostraron que el taxón norteamericano oriental puede separarse de *C. cornucopioides*.

Esta distinción es importante porque:

- los resultados europeos son los más directamente aplicables a Rainmapper;
- no deben mezclarse automáticamente observaciones norteamericanas;
- las búsquedas bibliográficas deben comprobar la identidad taxonómica;
- las reglas ecológicas de *C. fallax* no deben trasladarse sin validación.

**Conclusión útil:** Rainmapper debería usar un identificador taxonómico europeo estable y evitar mezclar registros norteamericanos dudosos.

## 2.2. Asociación con hayedos

El estudio irlandés sobre producción de hongos silvestres comestibles examinó parcelas de varios tipos forestales.

Para *C. cornucopioides*:

- la mayor parte de los carpóforos y biomasa se registró en haya;
- la productividad estimada más alta correspondió a bosque de haya;
- solo se encontraron cantidades testimoniales en abedular;
- no apareció en los demás tipos forestales muestreados durante el periodo.

El propio informe advierte que la producción fue baja y que la especie puede ser subdetectada por su color oscuro y su camuflaje entre la hojarasca.

**Conclusión útil:** el haya debe recibir un peso alto en el filtro de hábitat, pero el resultado no demuestra exclusividad.

## 2.3. Hayedos, robledales y carpes

Sarrionandia et al. estudiaron comunidades de macrohongos en hayedos del norte de la península ibérica.

El trabajo registra *C. cornucopioides* y discute su afinidad con:

- *Fagus*;
- *Carpinus* en referencias previas;
- también robles en determinados territorios.

Los estudios de bosques de *Quercus* incluyen igualmente la especie en comunidades ectomicorrícicas.

**Conclusión útil:** el filtro ecológico debe admitir haya, roble y carpe, con pesos aprendidos regionalmente.

## 2.4. Condición ectomicorrícica

Las revisiones modernas sobre cultivo de hongos ectomicorrícicos incluyen *C. cornucopioides* entre las Cantharellaceae ectomicorrícicas.

Esto implica que la fructificación depende de árboles hospedadores vivos y de la continuidad de la simbiosis.

No debe modelarse como un simple saprótrofo de hojarasca, aunque sus carpóforos aparezcan entre hojas en descomposición.

**Conclusión útil:** la presencia y estado del hospedador son condiciones ecológicas esenciales.

## 2.5. Humedad, sombra y microhábitat

La literatura ecológica sitúa la especie en:

- zonas húmedas;
- depresiones y vaguadas;
- laderas umbrías;
- suelos con hojarasca;
- áreas con musgo;
- bosques cerrados o semisombreados.

Sin embargo, la mayor parte de estas descripciones procede de inventarios y monografías, no de experimentos que cuantifiquen la respuesta a humedad.

No existe evidencia suficiente para fijar:

- porcentaje mínimo de humedad;
- cobertura de musgo obligatoria;
- profundidad de hojarasca óptima;
- drenaje ideal universal.

**Conclusión útil:** humedad y sombra son factores defendibles como clases de aptitud, no como umbrales numéricos.

## 2.6. Productividad baja e irregular

El informe irlandés encontró:

- producción baja;
- presencia en muy pocas parcelas;
- fuerte concentración en un único tipo forestal;
- variabilidad entre visitas y años.

El estudio de comunidades fúngicas de Europa oriental registró también producciones destacables en algunos bosques, mostrando que la especie puede ser abundante localmente.

Estos resultados no son contradictorios. Indican que:

- la aptitud es muy espacial;
- la abundancia cambia mucho entre bosques;
- un bosque compatible puede no producir en un año concreto;
- una colonia estable puede producir muchos carpóforos en una campaña favorable.

**Conclusión útil:** historial local y estructura espacial deben pesar más que una media regional.

## 2.7. Fenología y cambio climático

Kauserud et al. analizaron decenas de miles de registros históricos en Noruega y encontraron retrasos significativos en la fructificación otoñal de muchas especies.

Posteriormente, estudios europeos con cientos de miles de registros demostraron:

- temporadas de fructificación más largas;
- cambios en fecha de inicio y final;
- respuestas distintas según especie y región;
- relación con el alargamiento de la estación vegetativa.

*C. cornucopioides* figura entre los taxones incluidos en los grandes conjuntos fenológicos.

**Conclusión útil:** la fenología debe ser dinámica y corregida por clima anual, no basada en fechas tradicionales fijas.

## 2.8. Cambios altitudinales

Diez et al. analizaron registros de fructificación en los Alpes y documentaron desplazamientos altitudinales hacia cotas superiores en numerosas especies.

*C. cornucopioides* estuvo incluida entre las especies analizadas.

El estudio no ofrece una regla diaria de predicción, pero demuestra que:

- la distribución altitudinal de las fructificaciones cambia;
- la temperatura regional afecta a la posición espacial de la campaña;
- los modelos históricos pueden quedar desactualizados.

**Conclusión útil:** altitud y anomalía térmica deben interactuar en Rainmapper.

## 2.9. Gestión forestal y mosaico de vegetación

Los estudios mediterráneos sobre gestión en mosaico de *Cistus* y *Quercus* incluyen *C. cornucopioides* en la comunidad fúngica.

Los resultados generales muestran que la estructura de la vegetación y la sucesión modifican:

- riqueza;
- composición;
- producción de esporocarpos;
- presencia de especies comestibles.

El trabajo no modela *C. cornucopioides* por separado, por lo que no permite afirmar una respuesta concreta a un tratamiento.

**Conclusión útil:** la fase sucesional y la continuidad del bosque deben considerarse, pero sin asignar un efecto específico no demostrado.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y tipo de bosque

La evidencia específica respalda principalmente:

- *Fagus*;
- *Quercus*;
- *Carpinus*;
- bosques mixtos de frondosas.

La presencia en coníferas puras está mucho menos respaldada en Europa.

Rainmapper debería priorizar:

1. hayedos con observaciones históricas;
2. robledales compatibles;
3. bosques mixtos de frondosas;
4. carpedas y formaciones relacionadas;
5. hábitats sin frondosas ectomicorrícicas, con aptitud baja.

## 3.2. Historial local

La especie tiende a aparecer en manchas o colonias recurrentes.

Variables útiles:

- observaciones confirmadas;
- frecuencia histórica;
- abundancia máxima;
- extensión aproximada de la colonia;
- años sin fructificación;
- cambios de cobertura o uso del suelo.

## 3.3. Humedad del suelo y hojarasca

La asociación con ambientes húmedos es consistente.

Rainmapper puede utilizar:

- humedad del suelo;
- precipitación reciente;
- acumulados de varias semanas;
- días secos consecutivos;
- retención edáfica;
- cobertura de hojarasca;
- posición topográfica.

No existe un valor mínimo demostrado.

## 3.4. Sombra y cobertura

La cobertura del dosel modula:

- evaporación;
- temperatura;
- humedad de hojarasca;
- continuidad del microhábitat.

Debe tratarse como variable continua o por clases, no como requisito absoluto.

## 3.5. Fenología

Variables recomendadas:

- día del año;
- fecha histórica local;
- anomalía térmica;
- altitud;
- latitud o región climática;
- primeras lluvias otoñales;
- primeras heladas.

Las lluvias otoñales son una variable plausible, pero la literatura específica no permite fijar una relación cuantitativa universal.

## 3.6. Altitud y topografía

La altitud debe usarse como modulador climático y no como límite rígido.

También pueden ser relevantes:

- orientación;
- vaguadas;
- concavidad;
- exposición;
- proximidad a cursos de agua.

Estas variables se justifican por su efecto sobre humedad y temperatura, no por un modelo específico ya validado.

## 3.7. Alteración del hábitat

Deben penalizarse:

- tala intensa;
- pérdida del hospedador;
- compactación;
- eliminación de hojarasca;
- caminos;
- drenaje;
- transformación del bosque.

No existe una función cuantificada específica para la especie.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No se ha localizado un umbral validado para desencadenar una florada.

## 4.2. Número fijo de días después de la lluvia

No existe un retardo universal publicado.

## 4.3. Temperatura óptima

No se ha identificado una temperatura óptima de fructificación transferible.

## 4.4. pH o suelo calcáreo obligatorio

La especie se ha descrito con frecuencia en suelos calizos, pero la literatura seleccionada no justifica un requisito universal.

## 4.5. Musgo obligatorio

Es un indicador frecuente de microhábitat, no una condición demostrada para todas las poblaciones.

## 4.6. Viento, radiación, humedad relativa y evapotranspiración

No existen funciones específicas y generalizables para la especie.

## 4.7. Productividad estable en hayedos

El haya es un contexto bien respaldado, pero la producción puede ser baja o nula en años concretos.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- haya, roble o carpe;
- bosque de frondosas;
- continuidad del arbolado;
- cobertura;
- historial local;
- ausencia de alteración severa.

## 5.2. Componente hídrico

Incluir:

- precipitación reciente;
- precipitación acumulada;
- humedad del suelo;
- días secos;
- retención edáfica;
- humedad de hojarasca si puede estimarse.

## 5.3. Componente térmico

Incluir:

- temperatura media;
- mínimas;
- anomalías;
- primeras heladas;
- interacción con altitud.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- desplazamiento anual de la campaña.

## 5.5. Microhábitat

Incorporar cuando existan datos:

- orientación;
- cobertura;
- musgo;
- hojarasca;
- concavidad del terreno;
- proximidad a vaguadas;
- compactación.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- identificación fiable;
- hospedador dominante;
- cobertura;
- hojarasca y musgo;
- altitud;
- orientación;
- perturbación;
- meteorología previa;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- tipo de bosque;
- presencia de haya, roble o carpe;
- historial local;
- precipitación reciente;
- humedad del suelo;
- día del año;
- temperatura;
- altitud.

## Recomendables

- cobertura forestal;
- hojarasca;
- musgo;
- orientación;
- pendiente;
- concavidad;
- precipitación acumulada;
- días secos consecutivos;
- alteración del suelo.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- déficit de presión de vapor;
- índices de vigor del hospedador;
- clasificación automática de microhábitats;
- detección de colonias mediante observaciones repetidas.

“Experimental” significa que la literatura específica no permite asignarles un efecto universal sobre la fructificación de *C. cornucopioides*.

---

# 7. Conclusiones

1. *Craterellus cornucopioides* es una especie ectomicorrícica asociada principalmente a frondosas.

2. Los hayedos constituyen uno de los contextos forestales mejor respaldados.

3. También aparece con robles y carpes.

4. La especie se asocia a zonas húmedas, umbrías, musgosas y con hojarasca, pero sin umbrales cuantitativos demostrados.

5. La productividad puede ser muy baja e irregular incluso en hábitats adecuados.

6. Las colonias locales pueden producir abundantemente en campañas favorables.

7. La fructificación se concentra normalmente en verano tardío y otoño, con prolongación posible hasta noviembre.

8. La fenología está cambiando con el clima y no debe modelarse mediante fechas rígidas.

9. Los desplazamientos altitudinales observados en series europeas justifican combinar altitud y anomalía térmica.

10. No existe una cantidad mínima de lluvia, temperatura óptima ni retardo post-lluvia universal.

11. El historial local debe tener un peso muy alto.

12. Rainmapper debería combinar bosque compatible, humedad persistente, microhábitat, fenología y observaciones previas.

---

# 8. Bibliografía seleccionada

## 1. Harrington, T. et al. (2019)

**Título:** Assessment of production of wild edible fungi in Irish forests.  
**Informe:** COFORD.  
**Texto completo:** https://www.coford.ie/media/coford/content/FORESTFUNGIFinalReport3251019.pdf

**Aportación:** cuantifica la producción de *C. cornucopioides* por tipo forestal y muestra una concentración clara en bosque de haya.

**Confianza:** alta para productividad y hábitat dentro de las parcelas estudiadas.

## 2. Sarrionandia, E. et al. (2009)

**Título:** A study of the macrofungal community in the beech forest of Artikutza.  
**Revista:** Cryptogamie, Mycologie, 30(1).  
**Texto completo:** https://sciencepress.mnhn.fr/sites/default/files/articles/pdf/cryptogamie-mycologie2009v30f1a7.pdf

**Aportación:** registra *C. cornucopioides* en hayedo y discute afinidades con haya, carpe y otras frondosas.

**Confianza:** alta para contexto ecológico; no es un modelo meteorológico.

## 3. Kauserud, H. et al. (2008)

**Título:** Mushroom fruiting and climate change.  
**Revista:** Proceedings of the National Academy of Sciences, 105, 3811–3814.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC2268836/

**Aportación:** demuestra cambios prolongados en fechas de fructificación otoñal mediante registros históricos noruegos.

**Confianza:** alta para tendencia fenológica general; no proporciona una función exclusiva de la especie.

## 4. Kauserud, H. et al. (2012)

**Título:** Warming-induced shift in European mushroom fruiting phenology.  
**Revista:** Proceedings of the National Academy of Sciences, 109, 14488–14493.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC3437857/

**Aportación:** analiza cientos de miles de registros europeos y demuestra cambios en duración e inicio de la temporada fúngica.

**Confianza:** alta para fenología continental; limitada para predicción diaria de *C. cornucopioides*.

## 5. Diez, J. et al. (2020)

**Título:** Altitudinal upwards shifts in fungal fruiting in the Alps.  
**Revista:** Proceedings of the Royal Society B.  
**DOI / texto:** https://royalsocietypublishing.org/doi/10.1098/rspb.2019.2348

**Aportación:** incluye *C. cornucopioides* entre las especies usadas para analizar cambios altitudinales de fructificación.

**Confianza:** alta para tendencia espacial a largo plazo; no define umbrales de campaña.

## 6. Magarzo, A. et al. (2023)

**Título:** Mosaic forest management at landscape scale to enhance fungal diversity and production in a context of forest fire prevention in Mediterranean ecosystems.  
**Revista:** Ecological Indicators.  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S1470160X23004144

**Aportación:** incluye *C. cornucopioides* en comunidades de paisajes mediterráneos de *Cistus* y *Quercus* y demuestra que la estructura del mosaico modifica la comunidad fúngica.

**Confianza:** media para la especie concreta; alta para contexto de gestión y sucesión.

## 7. Yamada, A. et al. (2022)

**Título:** Cultivation studies of edible ectomycorrhizal mushrooms.  
**Revista:** Mycoscience, 63, 273–285.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC10043572/

**Aportación:** incluye *C. cornucopioides* entre los hongos comestibles ectomicorrícicos y aporta el marco biológico de dependencia del hospedador.

**Confianza:** alta para estrategia trófica; no aporta predicción meteorológica.

---

## Nota final sobre la evidencia

Se localizaron numerosos trabajos sobre composición química, actividad antioxidante y valor nutricional de *C. cornucopioides*. No se utilizaron porque no aportan información para predecir fructificaciones.

También se excluyeron publicaciones norteamericanas sobre *Craterellus fallax* y registros históricos de “black trumpet” cuya identidad no estaba resuelta.

La conclusión defendible es sencilla: frondosas compatibles —especialmente haya y roble—, humedad persistente, sombra, hojarasca, fenología otoñal flexible e historial local. La bibliografía no permite convertir estas relaciones en umbrales meteorológicos universales.
