# Predicción de floradas de *Marasmius oreades*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Marasmius oreades* (Bolton) Fr.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Marasmius oreades* y aporta información útil sobre fructificación, clima, hábitat, suelo, anillos de brujas, estructura espacial o respuesta ambiental.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica sobre *Marasmius oreades* es relativamente abundante en relación con los anillos de brujas, la estructura espacial del micelio y los efectos sobre el suelo y la vegetación. La evidencia específicamente orientada a predecir la aparición de carpóforos es más limitada, aunque un estudio europeo reciente modeló condiciones meteorológicas asociadas a la fructificación de esta especie.

Las conclusiones mejor respaldadas son:

1. **Es una especie saprótrofa de pastizales, praderas, céspedes, bordes de caminos y otros hábitats herbosos abiertos.** No depende de un hospedador ectomicorrícico.

2. **La persistencia espacial del anillo es uno de los factores más informativos.** Los individuos pueden expandirse radialmente durante muchos años y producir repetidamente en el frente activo.

3. **La meteorología influye en la fructificación, pero no existe una regla universal simple.** El estudio europeo de Andrew (2025) incluyó *M. oreades* entre 127 taxones y modeló condiciones climáticas y meteorológicas óptimas asociadas a sus registros de fructificación.

4. **Las temperaturas extremas afectan a la fructificación.** El estudio citado concluyó que todas las especies analizadas mostraban sensibilidad a extremos térmicos diarios, pero no debe extraerse de ello una temperatura crítica universal específica para *M. oreades*.

5. **La amplitud de nicho meteorológico parece relativamente estrecha para muchos hongos terrestres.** Esto respalda el uso de temperatura y humedad a escala diaria, aunque los parámetros concretos deben calibrarse regionalmente.

6. **Los anillos modifican activamente el suelo.** La literatura clásica y moderna documenta movilización de nitrógeno y fósforo, cambios de humedad, hidrofobicidad y alteraciones de la vegetación.

7. **La interacción con la vegetación puede ser negativa o positiva según la zona del anillo.** El frente puede estimular el crecimiento del césped por liberación de nutrientes, pero también provocar estrés hídrico, daño radicular o muerte de la hierba.

8. **El micelio puede volver el suelo hidrófobo y alterar la relación planta–agua.** Por tanto, la humedad meteorológica general puede no representar bien la humedad real en el frente activo.

9. **El hábitat abierto y el uso ganadero cuentan con evidencia ecológica.** Un estudio etnoecológico polaco encontró una fuerte asociación con praderas y reconoció la importancia de áreas de pastoreo y estiércol para hongos saprótrofos como *M. oreades*.

10. **La especie aparece también en dunas costeras y otros pastizales arenosos.** Un estudio genético en Noruega confirmó grandes individuos clonales en sistemas dunares.

11. **La fenología es amplia, habitualmente de primavera a otoño en climas templados.** No existe una única estación de fructificación válida para toda Europa.

12. **No existe evidencia suficiente para fijar una lluvia mínima, una humedad crítica, una temperatura óptima universal o un número fijo de días después de la lluvia.**

13. **Rainmapper debería modelar primero la presencia y geometría del anillo y después la probabilidad meteorológica de fructificación.** El frente activo es mucho más informativo que una celda de hábitat genérico.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Pastizal, pradera o césped | Filtro ecológico principal | Muy alta |
| Historial local y geometría del anillo | Predictor espacial principal | Muy alta |
| Día del año | Modulador fenológico | Alta |
| Temperatura diaria y extremos | Modulador climático | Alta |
| Humedad del suelo | Estado hídrico | Media-alta |
| Precipitación reciente | Señal de recarga | Media |
| Uso ganadero y materia orgánica | Modulador de aptitud | Media-alta |
| Alteración del suelo e hidrofobicidad | Modulador local | Media |
| Altitud y región climática | Moduladores espaciales | Media |
| Cobertura herbácea | Indicador de microhábitat | Media-alta |

**Conclusión práctica:** Rainmapper debería tratar *M. oreades* como una especie de anillos persistentes en hábitats herbosos abiertos. El modelo mínimo debe combinar localización histórica del anillo, posición del frente activo, temperatura, humedad, precipitación reciente y fenología regional. La literatura no justifica umbrales meteorológicos rígidos.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Marasmius oreades*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de otros hongos formadores de anillos sin resultados para *M. oreades*;
- trabajos centrados exclusivamente en genómica sin utilidad ecológica directa;
- páginas divulgativas con cifras meteorológicas no verificables;
- estudios de control fungicida en césped deportivo sin datos ecológicos útiles;
- afirmaciones históricas sobre toxicidad o parasitismo no confirmadas;
- modelos comunitarios que no incluían resultados identificables para la especie;
- publicaciones sobre composición química o propiedades alimentarias.

Se seleccionaron **ocho referencias principales**, priorizando fructificación climática, estructura espacial, suelo, vegetación, hábitat y fenología.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Estrategia saprótrofa y hábitat

*Marasmius oreades* es un hongo saprótrofo que utiliza materia orgánica del suelo y restos vegetales.

La literatura lo sitúa principalmente en:

- praderas;
- pastizales;
- céspedes;
- bordes de caminos;
- claros;
- parques;
- dunas costeras;
- hábitats abiertos de clima templado.

El estudio etnoecológico de Kotowski et al. mostró una asociación clara entre *M. oreades* y los hábitats abiertos, especialmente campos, praderas y márgenes.

**Conclusión útil:** Rainmapper debe utilizar una máscara de hábitat herboso abierto, no una máscara de hospedador arbóreo.

## 2.2. Importancia del pastoreo y la materia orgánica

Kotowski et al. compararon conocimiento ecológico local con literatura científica y concluyeron que la importancia de:

- áreas de pastoreo;
- estiércol animal;
- uso ganadero;

para hongos saprótrofos como *M. oreades* está respaldada por publicaciones previas.

Esto no significa que el estiércol sea obligatorio ni que cuanto más estiércol, mayor producción.

**Conclusión útil:** el uso ganadero y la fertilidad orgánica pueden actuar como moduladores de aptitud.

## 2.3. Formación de anillos persistentes

La especie forma anillos de brujas mediante expansión radial del micelio.

Hiltunen et al. secuenciaron el genoma de individuos procedentes de varios anillos y demostraron:

- gran longevidad;
- crecimiento vegetativo prolongado;
- estabilidad genética extraordinaria;
- estructura clonal del individuo.

La consecuencia ecológica es directa:

- el anillo puede persistir durante muchos años;
- el frente activo se desplaza;
- el centro histórico deja de ser la zona productiva;
- la geometría de observaciones previas tiene valor predictivo.

**Conclusión útil:** registrar anillos como polígonos o arcos y no como puntos aislados.

## 2.4. Estructura espacial y genética en dunas

Abesha, Caetano-Anollés y Høiland estudiaron la estructura genética de anillos en sistemas dunares noruegos.

El trabajo mostró:

- individuos extensos;
- organización espacial clara;
- correspondencia entre genotipo y sectores del anillo;
- expansión radial dentro de pastizales dunares.

Este estudio demuestra que la especie puede persistir en ambientes arenosos abiertos y no solo en céspedes fértiles.

**Conclusión útil:** textura arenosa no debe excluir la especie cuando existe un pastizal estable.

## 2.5. Fructificación y meteorología

Andrew (2025) modeló condiciones asociadas a registros de fructificación de 127 especies europeas, entre ellas *M. oreades*.

El estudio incluyó:

- condiciones climáticas;
- tiempo meteorológico diario;
- temperatura;
- sensibilidad a extremos;
- amplitud de nicho;
- modo nutricional y sustrato.

Los resultados generales mostraron:

- sensibilidad de todas las especies a extremos diarios de temperatura;
- nichos más estrechos en hongos que fructifican sobre suelo;
- capacidad de modelar condiciones óptimas asociadas a la fructificación.

Para *M. oreades*, los ajustes del modelo fueron altos según los materiales suplementarios citados por el artículo.

La información pública accesible no permite reconstruir con seguridad todos los valores específicos.

**Conclusión útil:** temperatura diaria y condiciones meteorológicas de corto plazo deben incluirse, pero sin copiar umbrales no verificados.

## 2.6. Fenología

La especie puede fructificar durante una parte amplia del año en climas templados.

Los registros europeos la sitúan habitualmente:

- desde primavera;
- durante verano;
- en otoño;
- ocasionalmente más tarde en regiones suaves.

Un estudio fenológico sueco analizó registros entre 1980 y 2006 y mostró variación interanual y cambios temporales.

Los datos no justifican una fecha fija universal.

**Conclusión útil:** el día del año debe interactuar con temperatura y humedad regional.

## 2.7. Cambios altitudinales

Diez et al. incluyeron *M. oreades* entre las especies analizadas en un estudio sobre desplazamientos altitudinales de fructificación en los Alpes.

Los resultados generales mostraron movimientos hacia cotas superiores en numerosas especies.

Esto no aporta una regla diaria de aparición, pero demuestra que:

- el nicho de fructificación cambia;
- la altitud histórica no es estática;
- el calentamiento puede desplazar zonas favorables.

**Conclusión útil:** Rainmapper debe combinar altitud y anomalía térmica.

## 2.8. Movilización de nitrógeno y fósforo

Fisher documentó que *M. oreades* moviliza nitrógeno y fósforo durante el crecimiento del anillo.

El frente puede:

- liberar nutrientes;
- estimular el crecimiento de la vegetación;
- producir un anillo de césped más verde;
- alterar la fertilidad local.

**Conclusión útil:** los índices de vegetación pueden ayudar a detectar anillos, pero no deben interpretarse como causa directa de fructificación.

## 2.9. Hidrofobicidad y estrés hídrico

La literatura sobre anillos de *M. oreades* documenta:

- hidrofobicidad del suelo;
- interferencia con relaciones planta–agua;
- zonas de césped seco o muerto;
- cambios en infiltración;
- estrés radicular.

Estos efectos pueden producir una aparente contradicción:

- el frente libera nutrientes y reverdece el césped;
- al mismo tiempo puede desecar o dañar la vegetación.

No son resultados incompatibles, porque pueden corresponder a zonas distintas del anillo o fases diferentes.

**Conclusión útil:** distinguir exterior, frente activo e interior.

## 2.10. Efectos sobre la vegetación

Revisiones modernas de anillos de brujas clasifican *M. oreades* entre las especies capaces de producir anillos con daño visible a la vegetación.

Los mecanismos propuestos incluyen:

- hidrofobicidad;
- competencia por agua;
- compuestos tóxicos;
- alteración del suelo;
- movilización de nutrientes;
- interacción con raíces.

La contribución relativa de cada mecanismo puede variar entre lugares.

**Conclusión útil:** Rainmapper puede usar anomalías de vegetación como indicador espacial, pero no como prueba única de presencia.

## 2.11. Persistencia y estabilidad genética

El trabajo de Hiltunen et al. sobre integridad genómica mostró una tasa extremadamente baja de acumulación de mutaciones durante el crecimiento vegetativo.

Aunque el objetivo era evolutivo, el resultado respalda la idea de:

- individuos longevos;
- anillos persistentes;
- continuidad espacial;
- valor predictivo de observaciones históricas.

**Conclusión útil:** el historial local debe tener un peso muy elevado.

## 2.12. Variabilidad de los anillos

No todos los anillos muestran el mismo patrón.

Pueden presentar:

- césped verde en el frente;
- banda seca;
- muerte de vegetación;
- fructificación sin efectos visibles;
- arcos incompletos;
- discontinuidades por obstáculos;
- expansión asimétrica.

**Conclusión útil:** no exigir una geometría circular perfecta ni una firma vegetal única.

---

# 3. Factores predictivos defendibles

## 3.1. Historial y geometría del anillo

Variables prioritarias:

- centro histórico;
- radio;
- arcos observados;
- frente activo;
- velocidad de expansión aprendida localmente;
- recurrencia de carpóforos;
- interrupciones por caminos o edificios.

No existe una tasa universal de expansión.

## 3.2. Hábitat herboso

Priorizar:

- praderas;
- pastizales;
- céspedes;
- bordes de caminos;
- parques;
- dunas estabilizadas;
- claros.

## 3.3. Temperatura

Incluir:

- temperatura media diaria;
- mínimas;
- máximas;
- extremos;
- anomalía;
- temperatura del suelo cuando exista.

La literatura respalda sensibilidad, no un óptimo universal.

## 3.4. Humedad del suelo

Debe incluir:

- humedad superficial;
- precipitación reciente;
- infiltración;
- hidrofobicidad;
- duración de periodos secos;
- textura.

La humedad puede variar mucho dentro del propio anillo.

## 3.5. Precipitación

La lluvia debe utilizarse como señal de recarga, pero no existe una cantidad mínima específica validada.

Variables posibles:

- precipitación de pocos días;
- acumulados semanales;
- número de días lluviosos;
- días desde la última lluvia;
- intensidad del episodio.

## 3.6. Fenología

Variables:

- día del año;
- región climática;
- altitud;
- fecha histórica local;
- temperatura;
- humedad.

## 3.7. Vegetación y uso del suelo

Incluir:

- cobertura herbácea;
- vigor del césped;
- pastoreo;
- fertilidad orgánica;
- abandono;
- siega;
- riego;
- compactación.

## 3.8. Suelo

Variables útiles:

- materia orgánica;
- textura;
- drenaje;
- hidrofobicidad;
- nitrógeno;
- fósforo;
- compactación.

Los valores observados dentro del anillo no deben confundirse con requisitos iniciales de presencia.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Cantidad mínima de lluvia

No existe un umbral validado y transferible.

## 4.2. Número fijo de días después de la lluvia

No se ha demostrado un retardo universal.

## 4.3. Temperatura óptima

El estudio climático modela óptimos, pero los valores específicos deben consultarse y calibrarse regionalmente.

## 4.4. Velocidad universal de expansión

Cada anillo puede crecer a ritmo distinto.

## 4.5. Firma vegetal única

Los anillos pueden reverdecer, secar o no mostrar cambios visibles.

## 4.6. Necesidad de estiércol

El pastoreo y la materia orgánica favorecen el hábitat, pero no son requisitos absolutos.

## 4.7. pH óptimo

No se ha localizado un intervalo universal.

## 4.8. Viento, radiación y humedad relativa

No existen funciones específicas generalizables para la fructificación.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Componente espacial

Combinar:

- observaciones históricas;
- geometría del anillo;
- frente activo;
- expansión aprendida;
- continuidad del pastizal;
- obstáculos.

## 5.2. Filtro ecológico

Incluir:

- pradera;
- pastizal;
- césped;
- borde;
- duna estabilizada;
- materia orgánica;
- uso ganadero.

## 5.3. Componente térmico

Incluir:

- temperatura diaria;
- extremos;
- anomalías;
- temperatura del suelo;
- interacción con humedad.

## 5.4. Componente hídrico

Incluir:

- humedad del suelo;
- precipitación;
- días secos;
- infiltración;
- textura;
- posible hidrofobicidad.

## 5.5. Fenología regional

Usar:

- día del año;
- altitud;
- región climática;
- fecha histórica;
- duración de la campaña.

## 5.6. Vegetación

Incluir:

- NDVI o vigor del césped;
- bandas verdes o secas;
- cobertura;
- siega;
- pastoreo;
- riego.

## 5.7. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- disposición en arco o círculo;
- radio estimado;
- posición respecto al anillo histórico;
- estado de la vegetación;
- uso del suelo;
- humedad aparente;
- meteorología previa;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- historial local;
- geometría del anillo;
- hábitat herboso;
- día del año;
- temperatura;
- humedad del suelo;
- precipitación reciente;
- cobertura herbácea.

## Recomendables

- pastoreo;
- materia orgánica;
- textura;
- hidrofobicidad;
- NDVI;
- altitud;
- compactación;
- riego;
- siega.

## Experimentales

- velocidad de expansión estimada;
- clasificación automática de anillos;
- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- detección de bandas verdes o secas por teledetección;
- modelos de frente activo.

“Experimental” significa que la variable puede ser útil, pero la literatura específica no permite asignarle una relación universal sobre la fructificación de *M. oreades*.

---

# 7. Conclusiones

1. *Marasmius oreades* es una especie saprótrofa de hábitats herbosos abiertos.

2. Forma anillos longevos y espacialmente persistentes.

3. El frente activo es más informativo que el centro histórico del anillo.

4. La temperatura diaria y sus extremos influyen en la fructificación.

5. No existe una temperatura óptima universal transferible.

6. La humedad del suelo y la precipitación son relevantes, pero la propia actividad del micelio altera la infiltración y el balance hídrico.

7. Los anillos movilizan nitrógeno y fósforo y modifican la vegetación.

8. Pueden producir bandas verdes, zonas secas o daño a la hierba.

9. El pastoreo y la materia orgánica cuentan con respaldo ecológico como moduladores de hábitat.

10. La especie puede persistir también en dunas arenosas estabilizadas.

11. La fenología es amplia y regionalmente variable.

12. No existe una lluvia mínima, una temperatura óptima, una tasa de expansión o un número fijo de días post-lluvia universal.

13. Rainmapper debería combinar geometría del anillo, hábitat herboso, temperatura, humedad, precipitación e historial local.

---

# 8. Bibliografía seleccionada

## 1. Andrew, C. (2025)

**Título:** Not always optimal: Fungal fruiting triggers indicate climate sensitivity in cooler regions.  
**Revista:** Fungal Ecology, 75, 101416.  
**DOI:** https://doi.org/10.1016/j.funeco.2025.101416  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S1754504825000066

**Aportación:** principal fuente climática moderna. Modela condiciones meteorológicas y climáticas asociadas a la fructificación de 127 especies europeas, incluida *M. oreades*.

**Confianza:** alta para sensibilidad climática; los valores específicos deben consultarse en materiales suplementarios y calibrarse regionalmente.

## 2. Abesha, E., Caetano-Anollés, G. y Høiland, K. (2003)

**Título:** Population genetics and spatial structure of the fairy ring fungus *Marasmius oreades* in a Norwegian sand dune ecosystem.  
**Revista:** Mycologia, 95, 1021–1031.  
**DOI:** https://doi.org/10.1080/15572536.2004.11833018  
**Consulta:** https://www.researchgate.net/publication/49674861_Population_Genetics_and_Spatial_Structure_of_the_Fairy_Ring_Fungus_Marasmius_oreades_in_a_Norwegian_Sand_Dune_Ecosystem

**Aportación:** demuestra la estructura genética y espacial de grandes anillos en dunas noruegas.

**Confianza:** muy alta para persistencia espacial y hábitat dunar.

## 3. Hiltunen, M. et al. (2021)

**Título:** The Assembled and Annotated Genome of the Fairy-Ring Fungus *Marasmius oreades*.  
**Revista:** Genome Biology and Evolution, 13(7), evab126.  
**DOI:** https://doi.org/10.1093/gbe/evab126  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC8290104/

**Aportación:** aporta el genoma de referencia y confirma la utilidad de los anillos como individuos longevos y clonales.

**Confianza:** muy alta para biología del individuo; no es un modelo de fructificación.

## 4. Hiltunen, M. et al. (2019)

**Título:** Maintenance of High Genome Integrity over Vegetative Growth in the Fairy-Ring Mushroom *Marasmius oreades*.  
**Revista:** Current Biology, 29, 2758–2765.  
**Página editorial:** https://www.sciencedirect.com/science/article/pii/S096098221930870X

**Aportación:** demuestra estabilidad genómica extraordinaria durante el crecimiento vegetativo prolongado.

**Confianza:** alta para longevidad y persistencia espacial.

## 5. Kotowski, M. A. et al. (2021)

**Título:** Fungal ethnoecology: observed habitat preferences and the perception of changes in fungal abundance by mushroom collectors in Poland.  
**Revista:** Journal of Ethnobiology and Ethnomedicine, 17, 16.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC8059240/

**Aportación:** identifica una asociación clara de *M. oreades* con praderas, campos y márgenes, y respalda la importancia de pastoreo y estiércol para hongos saprótrofos de pastizal.

**Confianza:** media-alta para hábitat; parte de la evidencia procede de conocimiento local contrastado con literatura.

## 6. Fisher, R. F. (1977)

**Título:** Nitrogen and phosphorus mobilization by the fairy ring fungus, *Marasmius oreades*.  
**Revista:** Soil Biology and Biochemistry.  
**Consulta bibliográfica:** https://www.sciencedirect.com/science/article/abs/pii/S1002016022000492

**Aportación:** demuestra movilización de nitrógeno y fósforo durante el crecimiento del anillo.

**Confianza:** alta para modificación del suelo; no aporta meteorología de fructificación.

## 7. Zotti, M. et al. (2025)

**Título:** Fungal fairy rings: history, ecology, dynamics and engineering effects.  
**Revista:** IMA Fungus.  
**Texto completo:** https://imafungus.pensoft.net/article/138320/

**Aportación:** revisión moderna de dinámica, efectos sobre suelo, vegetación, hidrofobicidad y clasificación de anillos, con referencias específicas a *M. oreades*.

**Confianza:** alta como síntesis ecológica.

## 8. Diez, J. et al. (2020)

**Título:** Altitudinal upwards shifts in fungal fruiting in the Alps.  
**Revista:** Proceedings of the Royal Society B.  
**DOI:** https://doi.org/10.1098/rspb.2019.2348  
**Texto:** https://royalsocietypublishing.org/doi/pdf/10.1098/rspb.2019.2348

**Aportación:** incluye *M. oreades* entre las especies analizadas para detectar desplazamientos altitudinales de fructificación.

**Confianza:** alta para tendencia espacial a largo plazo; no ofrece predicción diaria.

---

## Nota final sobre la evidencia

La literatura específica de *M. oreades* permite definir con bastante confianza:

- hábitat herboso abierto;
- estrategia saprótrofa;
- persistencia y expansión radial;
- importancia de la geometría del anillo;
- sensibilidad a condiciones meteorológicas y extremos térmicos;
- modificación activa del suelo y la vegetación.

No permite definir:

- precipitación mínima;
- temperatura óptima universal;
- humedad crítica;
- número fijo de días después de la lluvia;
- tasa de expansión general;
- firma vegetal única.

La estructura más defendible para Rainmapper es: anillo conocido + frente activo + hábitat herboso + temperatura + humedad + precipitación reciente + fenología regional.
