# Predicción de floradas de *Macrolepiota procera*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Macrolepiota procera* (Scop.) Singer  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Macrolepiota procera* y aporta información útil sobre fructificación, clima, hábitat, suelo, estructura de la vegetación o distribución.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Macrolepiota procera* es limitada, pero existe al menos un modelo climático específico desarrollado en bosques mediterráneos y varios trabajos de largo plazo en los que la especie aparece identificada dentro de series de productividad fúngica.

Las conclusiones mejor respaldadas son:

1. **Es una especie saprótrofa.** No depende de un hospedador ectomicorrícico concreto. Su presencia se relaciona con materia orgánica del suelo, restos vegetales y ambientes herbosos o forestales abiertos.

2. **Puede fructificar en pastizales, claros, bordes de bosque, caminos, parques y bosques poco densos.** La estructura abierta o semia­bierta del hábitat aparece repetidamente en la literatura ecológica.

3. **Existe evidencia específica de que la precipitación de final de verano y otoño influye en su aparición y rendimiento.** En un modelo mediterráneo, la probabilidad de presencia se relacionó con la precipitación de septiembre y octubre y con la temperatura de noviembre.

4. **La precipitación de agosto favoreció la producción temprana de septiembre en el modelo citado.** Este resultado es específico del área y periodo estudiados y no debe convertirse en un umbral universal.

5. **La relación con la lluvia de octubre no fue lineal.** El modelo mostró una respuesta creciente y posteriormente decreciente, lo que indica que más precipitación no implica necesariamente más producción en cualquier circunstancia.

6. **La temperatura de noviembre formó parte del modelo de ocurrencia.** La literatura disponible no permite fijar una temperatura óptima universal ni interpretar el signo del efecto fuera del modelo concreto.

7. **La especie aparece en modelos mediterráneos de cambio climático y productividad.** Un estudio reciente de Cataluña utilizó más de cien parcelas permanentes y series superiores a veinte años para proyectar la productividad futura de cinco especies, incluida *M. procera*.

8. **La altitud y la región bioclimática modifican la productividad potencial.** Los modelos de cambio climático prevén desplazamientos espaciales de las zonas favorables, pero no una respuesta idéntica en todo el territorio.

9. **La estructura del hábitat importa, aunque faltan modelos exclusivos de la especie.** Estudios generales de pinares mediterráneos muestran efectos de área basimétrica, densidad, precipitación y temperatura sobre la productividad total; *M. procera* aparece en los inventarios, pero los coeficientes agregados no deben atribuirse directamente a ella.

10. **La composición y propiedades del suelo influyen en el ambiente donde fructifica.** Se ha documentado relación entre parámetros abióticos del suelo y composición mineral de los carpóforos, pero estos trabajos no proporcionan un modelo de aparición.

11. **No existe evidencia suficiente para fijar una cantidad mínima de lluvia, una humedad crítica, una temperatura óptima o un número fijo de días entre lluvia y fructificación.**

12. **El historial local y la disponibilidad de hábitats abiertos con materia orgánica deben tener un peso elevado.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hábitat abierto o semia­bierto | Filtro ecológico principal | Alta |
| Materia orgánica y sustrato herboso | Filtro de aptitud | Alta |
| Precipitación de agosto–octubre | Señal hídrica principal | Alta |
| Temperatura de otoño | Modulador fenológico | Media-alta |
| Día del año | Ventana fenológica | Alta |
| Altitud y región bioclimática | Moduladores espaciales | Media-alta |
| Cobertura y densidad de vegetación | Moduladores de microhábitat | Media |
| Humedad del suelo | Variable a calibrar | Media |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Alteración del suelo | Penalización de aptitud | Media |

**Conclusión práctica:** Rainmapper debería modelar *M. procera* mediante un filtro de hábitats abiertos o de bosque claro con materia orgánica, una señal de precipitación entre final de verano y otoño, temperatura otoñal, altitud e historial local. La literatura permite seleccionar estas variables, pero no justificar umbrales meteorológicos universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Macrolepiota procera*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- trabajos centrados exclusivamente en composición química, metales o valor nutricional;
- estudios de cultivo sin utilidad directa para fructificación de campo, salvo para confirmar respuestas fisiológicas;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos generales de productividad fúngica sin presencia documentada de la especie;
- estudios de otras *Macrolepiota* sin resultados específicos;
- registros florísticos sin información ecológica o temporal;
- afirmaciones tradicionales sobre lluvia o “buen tiempo” sin soporte científico.

Se seleccionaron **siete referencias principales**, priorizando modelos climáticos, estudios de cambio climático, series de productividad, ecología de hábitat y fisiología de cultivo.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Estrategia saprótrofa

*Macrolepiota procera* es una especie saprótrofa.

Esto significa que obtiene nutrientes de materia orgánica muerta y no necesita una simbiosis obligatoria con raíces de árboles.

La literatura la sitúa en:

- praderas;
- pastizales;
- claros forestales;
- bordes de caminos;
- parques;
- márgenes de bosque;
- bosques abiertos de frondosas y coníferas;
- suelos con restos vegetales y humus.

**Conclusión útil:** Rainmapper debe utilizar una máscara de sustrato y estructura del hábitat, no una máscara de hospedador.

## 2.2. Modelo climático mediterráneo específico

Karavani et al. desarrollaron modelos climáticos para hongos comercializados en bosques mediterráneos.

Para *M. procera*, el modelo de probabilidad de ocurrencia mostró dependencia de:

- precipitación de septiembre;
- precipitación de octubre;
- temperatura de noviembre.

El modelo de rendimiento incorporó además:

- precipitación de agosto;
- efecto no lineal de la precipitación de octubre.

La precipitación de agosto tuvo un efecto positivo sobre la producción temprana de septiembre.

**Conclusión útil:** las ventanas de final de verano y otoño están respaldadas específicamente y deben calcularse por separado.

## 2.3. Respuesta no lineal a la precipitación de octubre

El mismo estudio encontró una respuesta creciente y después decreciente del rendimiento respecto a la precipitación de octubre.

Esto puede significar que:

- una cantidad insuficiente de agua limita la producción;
- a partir de cierto nivel, el beneficio adicional disminuye;
- condiciones muy húmedas pueden coincidir con temperaturas, saturación o procesos no favorables;
- la relación no puede representarse mediante una suma lineal simple.

El artículo no justifica trasladar el punto de inflexión a otra región.

**Conclusión útil:** utilizar funciones no lineales o clases de adecuación, no asumir “más lluvia = más setas”.

## 2.4. Precipitación de agosto y producción temprana

La relación positiva entre precipitación de agosto y producción de septiembre sugiere una fase de preparación previa a la aparición visible.

No demuestra:

- un tiempo fijo de respuesta;
- una cantidad mínima;
- que agosto sea siempre relevante en regiones más frías;
- que el efecto se mantenga en primavera.

**Conclusión útil:** Rainmapper debe adaptar las ventanas al calendario regional, pero conservar una señal hídrica previa a la campaña.

## 2.5. Temperatura de noviembre

La temperatura de noviembre formó parte del modelo de probabilidad de ocurrencia.

El resumen accesible no permite reconstruir de manera segura:

- el coeficiente exacto;
- la forma completa de la respuesta;
- un intervalo óptimo;
- la interacción con precipitación.

Por tanto, no se debe afirmar que una temperatura concreta favorece o inhibe la florada fuera del modelo original.

**Conclusión útil:** incluir temperatura otoñal como variable de calibración, sin umbral previo.

## 2.6. Cambio climático y distribución futura

Morera et al. modelaron los efectos del cambio climático sobre la productividad y distribución de cinco especies de interés socioeconómico en Cataluña, incluida *M. procera*.

El estudio utilizó:

- más de cien parcelas permanentes;
- más de veinte años de muestreo;
- modelos de aprendizaje automático;
- gradientes bioclimáticos mediterráneos;
- escenarios climáticos futuros;
- resolución espacial de paisaje.

Los resultados generales mostraron que las áreas óptimas de productividad pueden desplazarse altitudinalmente y cambiar entre regiones bioclimáticas.

Para *M. procera*, la revisión global posterior indicó que los modelos no proyectaban cambios significativos de productividad total en todos los escenarios, pero sí cambios espaciales.

**Conclusión útil:** la estabilidad regional agregada no significa estabilidad local. Rainmapper debe modelar desplazamientos espaciales.

## 2.7. Altitud y gradientes mediterráneos

Alday et al. estudiaron biomasa y diversidad de hongos a lo largo de gradientes altitudinales mediterráneos.

*M. procera* figuró entre las especies saprótrofas registradas.

El estudio mostró que:

- biomasa y diversidad responden a escalas espaciales y temporales diferentes;
- altitud, clima y estructura del bosque afectan a las comunidades;
- las especies saprótrofas no siguen necesariamente los mismos patrones que las ectomicorrícicas.

No se publicó una función individual para *M. procera*.

**Conclusión útil:** altitud y región climática deben entrar como moduladores, pero sin copiar coeficientes comunitarios.

## 2.8. Estructura de pinares mediterráneos

Herrero et al. modelaron productividad fúngica de largo plazo en *Pinus pinaster*.

El modelo agregado incluyó:

- relación entre área basimétrica y densidad;
- precipitación;
- temperaturas medias de septiembre y noviembre.

*M. procera* aparece explícitamente en el inventario de especies.

Sin embargo, el modelo se refiere a productividad total y no a *M. procera* por separado.

**Conclusión útil:** estructura del rodal y clima son variables razonables, pero la evidencia específica de la especie sigue siendo indirecta.

## 2.9. Hábitats abiertos y bordes

La literatura ecológica europea describe de forma consistente la especie en:

- praderas;
- pastos;
- bordes de bosque;
- márgenes de caminos;
- claros;
- parques;
- bosques luminosos.

Este patrón es coherente con su estrategia saprótrofa y con la disponibilidad de materia orgánica herbácea.

No existe un porcentaje universal de cobertura arbórea que defina el hábitat óptimo.

**Conclusión útil:** la cobertura debe modelarse de forma continua y probablemente no lineal.

## 2.10. Suelo

Mleczek et al. estudiaron 230 carpóforos y sus suelos o sustratos asociados.

El trabajo mostró que parámetros abióticos del suelo y proximidad al tráfico influyen en:

- composición mineral;
- acumulación de elementos;
- valor nutritivo;
- contaminación.

Este estudio no modela la aparición, pero demuestra que los carpóforos responden al ambiente edáfico local.

La literatura ecológica suele asociar la especie con suelos:

- bien drenados;
- frescos o mesófilos;
- ricos en materia orgánica;
- de praderas o bosques abiertos.

**Conclusión útil:** textura, drenaje y materia orgánica son variables útiles, pero sin umbrales específicos.

## 2.11. Crecimiento micelial en cultivo

Pekşen et al. estudiaron el efecto de:

- pH;
- temperatura;
- fuentes de carbono;
- fuentes de nitrógeno;

sobre el crecimiento micelial de *M. procera*.

Estos trabajos confirman que:

- el micelio responde a temperatura y pH;
- existen condiciones de cultivo más favorables que otras;
- la fisiología no es indiferente al ambiente.

No deben transformarse en:

- temperatura óptima de fructificación natural;
- pH óptimo del suelo;
- umbral meteorológico;
- calendario de campaña.

**Conclusión útil:** estos datos solo respaldan la inclusión de temperatura y suelo como variables, no sus valores de campo.

## 2.12. Fenología

En Europa, la fructificación se concentra principalmente:

- desde verano tardío;
- durante otoño;
- hasta noviembre en regiones templadas;
- ocasionalmente en primavera en algunos territorios.

La campaña depende de:

- lluvia;
- temperatura;
- región;
- altitud;
- tipo de hábitat.

No existe una ventana universal idéntica para toda Europa.

**Conclusión útil:** usar día del año y climatología regional de forma flexible.

## 2.13. Distribución agregada y corros

La especie puede aparecer:

- solitaria;
- en grupos;
- en arcos;
- en corros.

Esto indica una distribución espacial del micelio no uniforme y una posible recurrencia local.

No se ha localizado una tasa universal de expansión de los corros.

**Conclusión útil:** el historial local y la geometría de observaciones repetidas deben tener mucho peso.

---

# 3. Factores predictivos defendibles

## 3.1. Hábitat abierto o semia­bierto

Variables recomendadas:

- pastizal;
- pradera;
- claro;
- borde forestal;
- parque;
- margen de camino;
- cobertura arbórea;
- cobertura herbácea.

## 3.2. Materia orgánica

Incluir:

- humus;
- restos vegetales;
- hojarasca;
- materia orgánica del suelo;
- compost o residuos de siega;
- continuidad del sustrato.

## 3.3. Precipitación

Las ventanas con mejor respaldo específico son:

- agosto;
- septiembre;
- octubre.

Rainmapper debe adaptar esos meses al calendario regional y probar ventanas móviles equivalentes.

No existe una cantidad mínima universal.

## 3.4. Temperatura

Incluir:

- temperatura media;
- mínimas;
- máximas;
- anomalía;
- temperatura de otoño;
- interacción con humedad.

No existe un óptimo universal.

## 3.5. Humedad del suelo

Debe calcularse mediante:

- precipitación;
- evapotranspiración;
- textura;
- drenaje;
- cobertura;
- humedad antecedente.

La literatura específica directa es menor que para precipitación, pero la variable es coherente con el hábitat y el modelo climático.

## 3.6. Altitud y región bioclimática

Incluir:

- altitud;
- zona climática;
- orientación;
- exposición;
- desplazamiento de aptitud bajo cambio climático.

## 3.7. Cobertura y estructura

La especie aparece tanto en praderas como en bosques claros.

El modelo debe evitar dos extremos no demostrados:

- asumir que solo aparece en espacios completamente abiertos;
- asumir que cualquier bosque es adecuado.

## 3.8. Historial local

Debe incluir:

- presencia confirmada;
- frecuencia;
- abundancia;
- geometría del corro;
- fecha;
- tipo de hábitat;
- alteraciones recientes.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral transferible.

## 4.2. Número fijo de días post-lluvia

No se ha demostrado un retardo universal.

## 4.3. Temperatura óptima de campo

Los valores de cultivo no equivalen a fructificación natural.

## 4.4. pH óptimo

No existe un intervalo de suelo universalmente validado.

## 4.5. Cobertura arbórea óptima

No se ha publicado un porcentaje generalizable.

## 4.6. Efecto lineal de la lluvia

La precipitación de octubre mostró una respuesta no lineal en el modelo específico.

## 4.7. Viento, radiación y humedad relativa

No existen funciones específicas generalizables.

## 4.8. Tasa anual de expansión de corros

No se ha localizado una tasa universal.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- pradera o pastizal;
- claro o borde;
- bosque poco denso;
- materia orgánica;
- historial local;
- ausencia de alteración severa.

## 5.2. Componente hídrico

Incluir:

- precipitación de final de verano;
- precipitación de septiembre y octubre;
- humedad del suelo;
- balance hídrico;
- días secos;
- distribución temporal de la lluvia.

## 5.3. Componente térmico

Incluir:

- temperatura otoñal;
- mínimas;
- máximas;
- anomalías;
- interacción con agua disponible.

## 5.4. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica local;
- inicio observado de campaña.

## 5.5. Estructura del hábitat

Incluir:

- cobertura arbórea;
- cobertura herbácea;
- borde;
- distancia a caminos;
- densidad;
- manejo del pastizal;
- retirada de materia orgánica.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- identificación fiable;
- tipo de hábitat;
- cobertura;
- materia orgánica;
- suelo;
- meteorología previa;
- geometría del grupo o corro;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- tipo de hábitat;
- materia orgánica;
- historial local;
- precipitación de final de verano–otoño;
- día del año;
- temperatura;
- altitud;
- cobertura.

## Recomendables

- humedad del suelo;
- textura;
- drenaje;
- orientación;
- cobertura herbácea;
- borde forestal;
- anomalías climáticas;
- distribución temporal de la lluvia.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- temperatura del suelo;
- índices de vegetación;
- expansión de corros;
- modelos de cambio climático de alta resolución.

“Experimental” significa que la variable puede ser útil, pero la literatura específica no permite asignarle una relación universal sobre la fructificación de *M. procera*.

---

# 7. Conclusiones

1. *Macrolepiota procera* es una especie saprótrofa.

2. No depende de un hospedador ectomicorrícico concreto.

3. Aparece principalmente en praderas, pastizales, claros, bordes y bosques abiertos.

4. La materia orgánica del suelo es un componente ecológico central.

5. Existe un modelo mediterráneo específico que relaciona ocurrencia con precipitación de septiembre y octubre y temperatura de noviembre.

6. La precipitación de agosto favoreció la producción temprana de septiembre en ese modelo.

7. La respuesta a la precipitación de octubre fue no lineal.

8. Los coeficientes del modelo son locales y no deben trasladarse como umbrales universales.

9. Los modelos de cambio climático prevén desplazamientos espaciales de las áreas productivas.

10. Altitud, región bioclimática y estructura del hábitat deben formar parte del modelo.

11. No existe una lluvia mínima, una temperatura óptima o un número fijo de días post-lluvia universal.

12. Rainmapper debería combinar hábitat abierto, materia orgánica, lluvia de final de verano–otoño, temperatura, altitud e historial local.

---

# 8. Bibliografía seleccionada

## 1. Karavani, A. et al. (2016)

**Título:** Effect of climatic and micro-climatic conditions on mushroom productivity in Mediterranean forests.  
**Documento:** informe o trabajo técnico del proyecto MEDFOREX / investigación asociada.  
**Texto completo:** https://www.medfor.eu/sites/default/files/editor/karavani_et_al_final.pdf

**Aportación:** principal fuente climática específica. Relaciona la ocurrencia de *M. procera* con precipitación de septiembre y octubre y temperatura de noviembre; incorpora precipitación de agosto y una respuesta no lineal de octubre en el modelo de rendimiento.

**Confianza:** alta para el área y datos estudiados; los parámetros no son universales.

## 2. Morera, A. et al. (2024)

**Título:** Analysis of climate change impacts on the biogeographical patterns of forest fungi.  
**Revista:** Ecological Indicators.  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S1574954124000992

**Aportación:** modela productividad y distribución futura de cinco especies, incluida *M. procera*, con más de cien parcelas permanentes y series superiores a veinte años.

**Confianza:** alta para desplazamientos espaciales y escenarios regionales; no predice episodios diarios.

## 3. Herrero, C. et al. (2019)

**Título:** Predicting Mushroom Productivity from Long-Term Field-Data Series in Mediterranean *Pinus pinaster* Forests in the Context of Climate Change.  
**Revista:** Forests, 10, 206.  
**DOI / texto:** https://doi.org/10.3390/f10030206  
**Página:** https://www.mdpi.com/1999-4907/10/3/206

**Aportación:** incluye explícitamente *M. procera* en una serie de largo plazo y relaciona productividad total con estructura, precipitación y temperaturas de septiembre y noviembre.

**Confianza:** media para la especie individual, porque el modelo es agregado.

## 4. Alday, J. G. et al. (2017)

**Título:** Mushroom biomass and diversity are driven by different spatio-temporal scales along Mediterranean elevation gradients.  
**Revista:** Scientific Reports, 7, 45824.  
**Texto completo:** https://www.nature.com/articles/srep45824

**Aportación:** registra *M. procera* como saprótrofa en gradientes altitudinales mediterráneos y demuestra que biomasa y diversidad responden a escalas distintas.

**Confianza:** media para la especie concreta; alta para contexto espacial.

## 5. Pekşen, A. et al. (2020)

**Título:** Determination of optimum culture conditions for mycelial growth of *Macrolepiota procera*.  
**Revista:** Acta Scientiarum Polonorum Hortorum Cultus.  
**Página editorial:** https://czasopisma.up.lublin.pl/asphc/article/view/1389

**Aportación:** demuestra experimentalmente la respuesta del micelio a temperatura, pH y nutrientes.

**Confianza:** alta para cultivo; baja para trasladar valores a fructificación natural.

## 6. Mleczek, M. et al. (2022)

**Título:** Road traffic and abiotic parameters of underlying soils determine the mineral composition and nutritive value of the mushroom *Macrolepiota procera*.  
**Revista:** Chemosphere.  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S0045653522017064

**Aportación:** analiza 230 carpóforos y sustratos, demostrando la influencia del ambiente edáfico local.

**Confianza:** alta para composición y suelo; no modela aparición.

## 7. Kewessa, G. et al. (2022)

**Título:** Forest type and site conditions influence the diversity and productivity of wild edible mushrooms.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC9605516/

**Aportación:** incluye *M. procera* como especie saprótrofa y relaciona comunidades de hongos comestibles con tipo forestal y condiciones del sitio.

**Confianza:** media para hábitat; no ofrece un modelo individual de la especie.

---

## Nota final sobre la evidencia

La literatura específica de *M. procera* ofrece una base razonable para seleccionar:

- precipitación de final de verano y otoño;
- temperatura otoñal;
- altitud;
- estructura abierta del hábitat;
- materia orgánica;
- historial local.

No permite definir:

- precipitación mínima;
- temperatura óptima de campo;
- número de días post-lluvia;
- humedad crítica;
- pH universal;
- cobertura óptima.

La estructura más defendible para Rainmapper es: hábitat abierto o semia­bierto + materia orgánica + precipitación de agosto–octubre + temperatura otoñal + altitud + historial local.
