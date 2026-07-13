# Predicción de floradas de *Lepista nuda*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Lepista nuda* (Bull.) Cooke  
**Nombre actualmente aceptado en parte de la literatura reciente:** *Collybia nuda* (Bull.) Z.M. He & Zhu L. Yang  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 12 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Lepista nuda* o *Collybia nuda* y aporta información útil sobre fenología, hábitat, suelo, clima, producción o distribución.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Lepista nuda* es limitada. Existen estudios fenológicos, inventarios forestales, trabajos de cultivo, análisis de suelos y publicaciones sobre distribución y ecología, pero no se ha localizado un modelo meteorológico de campo validado y generalizable que permita establecer una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre un episodio meteorológico y la aparición de carpóforos.

Las conclusiones mejor respaldadas son:

1. **Es una especie saprótrofa de hojarasca y materia orgánica.** No depende de un hospedador ectomicorrícico concreto, aunque aparece con frecuencia en bosques de coníferas, bosques caducifolios, bordes forestales, jardines y otros lugares con abundante materia orgánica.

2. **La fenología es principalmente otoñal y tardía.** En estudios mediterráneos y europeos figura entre las especies típicas del otoño, y puede prolongar la fructificación hasta comienzos del invierno.

3. **La fecha de primera aparición ha cambiado con el clima.** Un estudio mediterráneo de largo plazo encontró que *L. nuda* actualmente comienza a fructificar antes que en el periodo histórico analizado.

4. **La temperatura es un modulador fenológico claro, pero no existe un óptimo de campo universal.** Los estudios de cultivo muestran que el crecimiento micelial y la inducción de fructificación responden a la temperatura, pero esos resultados no deben transferirse directamente al bosque.

5. **La disponibilidad de materia orgánica es un factor ecológico central.** La especie aparece en hojarasca, compost, restos vegetales, suelos ricos en humus y zonas con acumulación de residuos orgánicos.

6. **La humedad del suelo es relevante, pero no hay un umbral específico validado.** Estudios de suelos de hábitats naturales han encontrado valores elevados de humedad y materia orgánica, aunque proceden de pocas localidades y no definen requisitos universales.

7. **La especie puede aparecer bajo coníferas y frondosas.** Un estudio irlandés de producción registró la mayor parte de la biomasa en plantaciones de *Picea sitchensis*, con producciones menores en *Pinus sylvestris* y *Abies*.

8. **La productividad es muy irregular y espacialmente agregada.** Puede formar corros o grupos densos, pero estar ausente de parcelas aparentemente similares.

9. **El historial local y la presencia de hojarasca o compost deben tener un peso alto.** Para una especie saprótrofa, la disponibilidad del sustrato es más relevante que la presencia de una especie arbórea concreta.

10. **No existe evidencia suficiente para asignar efectos universales independientes al viento, radiación, humedad relativa o evapotranspiración.** Pueden influir en el secado, pero no están demostrados como predictores específicos de la especie.

11. **La identidad taxonómica debe vigilarse.** La especie ha sido trasladada recientemente al género *Collybia*, y además existe un complejo de taxones morfológicamente próximos, como *Lepista sordida*, *L. glaucocana* y otros.

12. **Rainmapper debe modelarla como una especie de sustrato orgánico y fenología fría, no como una especie ligada a un árbol hospedador.**

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hojarasca, compost o materia orgánica | Filtro ecológico principal | Muy alta |
| Historial local de fructificación | Predictor espacial principal | Muy alta |
| Día del año | Ventana fenológica otoñal–invernal | Alta |
| Temperatura reciente | Modulador fenológico | Media-alta |
| Descenso térmico estacional | Señal candidata de activación | Media |
| Humedad del suelo o del sustrato | Estado hídrico | Media |
| Precipitación reciente | Entrada del balance hídrico | Media |
| Cobertura forestal o sombreado | Modulador de microclima | Media |
| Tipo de sustrato y profundidad de hojarasca | Modulador de aptitud | Alta |
| Alteración reciente del suelo | Penalización de aptitud | Media |

**Conclusión práctica:** Rainmapper debería modelar *L. nuda* mediante un filtro de materia orgánica disponible, una ventana de otoño tardío–invierno, temperatura y humedad del sustrato, y un peso elevado del historial local. La literatura no permite fijar umbrales meteorológicos exactos.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Lepista nuda*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- trabajos centrados exclusivamente en composición química, valor nutricional o contaminantes;
- estudios de *Lepista sordida* u otras especies próximas sin resultados para *L. nuda*;
- páginas divulgativas con cifras meteorológicas no verificables;
- manuales de cultivo comerciales sin metodología científica;
- inventarios en los que la especie aparecía solo como una línea en una lista;
- datos de campo sin identificación taxonómica suficientemente clara;
- conclusiones sobre otros hongos saprótrofos trasladadas sin evidencia específica.

Se seleccionaron **siete referencias principales**, priorizando fenología, productividad en bosques, hábitat, suelo y taxonomía.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Situación taxonómica actual

El nombre *Lepista nuda* se ha utilizado durante décadas en micología europea.

Un estudio filogenómico reciente sobre Clitocybaceae trasladó la especie al género *Collybia*, como *Collybia nuda*. La propuesta se basa en:

- filogenia molecular;
- filogenómica;
- revisión de caracteres morfológicos;
- reorganización de los géneros *Clitocybe*, *Lepista* y *Collybia*.

La nomenclatura todavía no se ha estabilizado en todas las bases de datos y publicaciones.

**Conclusión útil:** Rainmapper debería conservar *Lepista nuda* como nombre visible si es el usado por la aplicación, pero registrar *Collybia nuda* como nombre aceptado o sinónimo taxonómico reciente.

## 2.2. Posible complejo de especies

La identificación puede confundirse con:

- *Lepista sordida*;
- *Lepista glaucocana*;
- *Lepista personata*;
- taxones próximos del complejo violeta;
- algunos *Cortinarius* violetas.

La similitud morfológica puede afectar a observaciones ciudadanas y datos históricos.

**Conclusión útil:** las observaciones de calibración deberían incluir fotografías, color de esporada, hábitat, tamaño y nivel de certeza.

## 2.3. Estrategia saprótrofa

La especie se considera saprótrofa de hojarasca y materia orgánica.

Aparece en:

- hojarasca de bosques caducifolios;
- acículas de coníferas;
- compost;
- restos vegetales;
- márgenes de bosque;
- jardines;
- suelos ricos en humus;
- zonas con acumulación de residuos orgánicos.

No forma una asociación ectomicorrícica obligatoria con un árbol concreto.

**Conclusión útil:** Rainmapper no debe usar una máscara de hospedador, sino una máscara de disponibilidad de sustrato orgánico.

## 2.4. Fenología otoñal

Fernández-Ruiz et al. analizaron comunidades macrofúngicas en un paisaje forestal mediterráneo y clasificaron *L. nuda* entre las especies típicas de fructificación otoñal.

El estudio muestra que:

- aparece dentro del conjunto característico del otoño;
- la composición semanal cambia de forma ordenada durante la campaña;
- la fenología depende del clima anual y del contexto forestal.

No proporciona una función meteorológica separada para *L. nuda*.

**Conclusión útil:** el día del año debe ser una variable importante, pero no un calendario rígido.

## 2.5. Adelanto de la primera fructificación

Vogt-Schilb et al. analizaron cambios fenológicos de largo plazo en hongos mediterráneos.

Para *L. nuda* encontraron que:

- actualmente comienza a fructificar antes que en el periodo histórico analizado;
- la fecha de primera fructificación ha cambiado con el clima;
- la fenología no puede considerarse estable.

El estudio no implica que toda la campaña se haya adelantado por igual ni proporciona una regla diaria simple.

**Conclusión útil:** Rainmapper debe utilizar anomalías climáticas y fecha histórica local, no fechas fijas.

## 2.6. Producción en bosques de Irlanda

Harrington et al. evaluaron la producción de hongos silvestres comestibles en parcelas forestales irlandesas.

Para *L. nuda* registraron producción en:

- *Picea sitchensis*;
- *Pinus sylvestris*;
- *Abies*;
- con mayor biomasa total en parcelas de *Picea sitchensis*.

El informe muestra que la especie puede fructificar bajo distintos tipos de arbolado.

Sin embargo, el resultado no demuestra preferencia fisiológica por *Picea*. La diferencia puede depender de:

- cantidad de hojarasca;
- humedad;
- edad de la plantación;
- estructura;
- número de parcelas;
- condiciones locales.

**Conclusión útil:** el tipo de bosque debe utilizarse como indicador del sustrato y microclima, no como hospedador obligatorio.

## 2.7. Hábitat en castañares y bosques mediterráneos

Baptista et al. registraron *L. nuda* en castañares del nordeste de Portugal durante un seguimiento de cuatro años.

La comunidad fue analizada en relación con:

- temperatura;
- precipitación;
- patrón estacional;
- tipo de bosque.

El trabajo confirma presencia en bosques de frondosas y fenología ligada a la campaña húmeda, pero no publica un modelo individual para *L. nuda*.

**Conclusión útil:** la especie puede aparecer en castañares y otros bosques con hojarasca abundante.

## 2.8. Suelo y materia orgánica

Un estudio coreano de suelos de hábitats de *L. nuda* analizó siete localidades.

Encontró:

- humedad del suelo elevada en promedio;
- contenido alto de materia orgánica;
- pH ácido en la mayoría de muestras;
- contenido apreciable de nitrógeno.

Los valores exactos proceden de pocas localidades y no deben tratarse como umbrales universales.

El hecho de que el pH fuera ácido en esas muestras no demuestra que la especie requiera exclusivamente suelos ácidos.

**Conclusión útil:** materia orgánica, humedad y nitrógeno son variables relevantes; el pH debe utilizarse como modulador y no como filtro absoluto.

## 2.9. Crecimiento y fructificación en cultivo

Los estudios de cultivo de *L. nuda* muestran que:

- el crecimiento micelial responde a temperatura;
- la fructificación requiere condiciones diferentes de las óptimas para crecimiento vegetativo;
- el descenso térmico se utiliza para inducir la formación de carpóforos;
- el sustrato y la cobertura condicionan la producción.

Estos resultados proceden de cultivos controlados, no de bosques.

No deben transformarse directamente en:

- temperatura de campo óptima;
- umbral de frío;
- número de días de enfriamiento;
- fecha de aparición.

**Conclusión útil:** el descenso térmico estacional es una variable candidata razonable, pero su función debe calibrarse con datos naturales.

## 2.10. Corros y distribución agregada

La especie puede formar corros o grupos extensos sobre sustratos orgánicos.

Esto indica:

- expansión radial del micelio;
- persistencia espacial;
- distribución no uniforme;
- recurrencia en lugares concretos.

No se ha localizado una tasa universal de expansión anual.

**Conclusión útil:** el historial local y la geometría de colonias conocidas deben tener un peso alto.

## 2.11. Hojarasca y descomposición

La especie participa activamente en la descomposición de hojarasca.

Estudios experimentales comparativos muestran alta capacidad enzimática y extracción de nutrientes de materiales vegetales.

Esto respalda el papel central del sustrato, pero no permite inferir qué especie arbórea produce la hojarasca óptima.

**Conclusión útil:** Rainmapper debería representar cantidad y continuidad de materia orgánica más que especie de árbol concreta.

## 2.12. Temperatura y precipitación en estudios de comunidad

Los estudios de comunidades donde aparece *L. nuda* muestran relación general entre:

- fructificación;
- temperatura;
- lluvia;
- fase de la temporada.

Pero no ofrecen coeficientes separados para la especie.

**Conclusión útil:** temperatura y precipitación deben incorporarse como variables de calibración, no como relaciones específicas ya demostradas.

---

# 3. Factores predictivos defendibles

## 3.1. Sustrato orgánico

Es el factor ecológico principal.

Variables recomendadas:

- profundidad de hojarasca;
- acumulación de acículas;
- compost;
- restos de poda;
- humus;
- materia orgánica del suelo;
- nitrógeno;
- continuidad del sustrato.

## 3.2. Historial local

Debe incluir:

- presencia confirmada;
- frecuencia;
- abundancia;
- geometría del corro;
- tipo de sustrato;
- fecha;
- alteraciones desde la última observación.

## 3.3. Fenología

Variables:

- día del año;
- fecha histórica local;
- anomalía térmica;
- duración del otoño;
- primeras heladas;
- comienzo del periodo húmedo.

## 3.4. Temperatura

Debe incorporarse mediante:

- temperatura media;
- mínimas;
- descenso térmico respecto a semanas anteriores;
- anomalía;
- heladas;
- temperatura del suelo si existe.

No existe un valor óptimo universal.

## 3.5. Humedad del sustrato

Variables:

- humedad del suelo;
- precipitación reciente;
- balance hídrico;
- días secos consecutivos;
- humedad de hojarasca;
- cobertura.

No existe un umbral específico validado.

## 3.6. Tipo de bosque

El tipo de bosque puede utilizarse como indicador de:

- cantidad de hojarasca;
- sombra;
- humedad;
- microclima;
- composición del sustrato.

No debe actuar como hospedador obligatorio.

## 3.7. Alteración del suelo

Deben penalizarse:

- retirada de hojarasca;
- laboreo;
- compactación;
- movimientos de tierra;
- eliminación de compost;
- desbroces intensos.

La literatura específica no cuantifica el tiempo de recuperación.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Temperatura óptima de campo

Los valores de cultivo no deben trasladarse directamente al bosque.

## 4.2. Umbral de frío

No existe un descenso térmico universal validado para inducción natural.

## 4.3. Cantidad mínima de lluvia

No se ha localizado un umbral específico y transferible.

## 4.4. Número fijo de días después de la lluvia

No existe un retardo universal publicado.

## 4.5. pH óptimo

Los suelos analizados en algunas localidades fueron ácidos, pero no se ha demostrado exclusividad.

## 4.6. Preferencia obligatoria por coníferas o frondosas

La especie aparece bajo ambos tipos de bosque.

## 4.7. Viento, radiación, humedad relativa y evapotranspiración

No existen funciones específicas generalizables para la fructificación.

## 4.8. Tasa anual de expansión del corro

No se ha localizado una tasa universal.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro de sustrato

Combinar:

- hojarasca;
- humus;
- compost;
- residuos vegetales;
- continuidad del sustrato;
- historial local.

## 5.2. Componente térmico

Incluir:

- temperatura media;
- mínimas;
- descenso térmico;
- anomalía;
- primeras heladas;
- temperatura del suelo.

## 5.3. Componente hídrico

Incluir:

- precipitación;
- humedad del suelo;
- humedad de hojarasca;
- balance hídrico;
- días secos.

## 5.4. Fenología regional

Usar:

- día del año;
- fecha histórica;
- región climática;
- altitud;
- duración del otoño;
- comienzo del periodo frío.

## 5.5. Estructura del hábitat

Incluir:

- bosque caducifolio o de coníferas;
- cobertura;
- profundidad de hojarasca;
- manejo;
- bordes;
- jardines y zonas compostadas.

## 5.6. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- fotografías;
- identificación fiable;
- tipo de sustrato;
- profundidad de hojarasca;
- bosque o jardín;
- humedad aparente;
- meteorología previa;
- alteración del suelo;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- sustrato orgánico;
- historial local;
- día del año;
- temperatura reciente;
- humedad del suelo o sustrato;
- precipitación;
- tipo de hábitat.

## Recomendables

- profundidad de hojarasca;
- materia orgánica;
- nitrógeno;
- cobertura;
- temperatura mínima;
- descenso térmico;
- pH;
- manejo reciente.

## Experimentales

- grados-día fríos;
- temperatura del suelo;
- humedad de hojarasca estimada;
- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- geometría y expansión del corro.

“Experimental” significa que la variable puede ser útil, pero la literatura específica no permite asignarle una relación universal sobre la fructificación de *L. nuda*.

---

# 7. Conclusiones

1. *Lepista nuda* es una especie saprótrofa de hojarasca y materia orgánica.

2. No depende de un hospedador ectomicorrícico concreto.

3. Aparece tanto bajo coníferas como bajo frondosas, y también en jardines, compost y bordes forestales.

4. La fenología es principalmente otoñal y puede prolongarse hasta el invierno.

5. La primera fructificación se ha adelantado en series mediterráneas de largo plazo.

6. La temperatura actúa como modulador fenológico, pero no existe un óptimo de campo universal.

7. La humedad y la materia orgánica del sustrato son factores ecológicos importantes.

8. Los valores de humedad, pH o temperatura obtenidos en cultivo o en pocas localidades no deben usarse como umbrales universales.

9. La especie puede formar corros persistentes y espacialmente agregados.

10. El historial local y la disponibilidad de hojarasca deben tener mucho peso.

11. No existe una lluvia mínima, un número fijo de días post-lluvia o un umbral de frío validado.

12. Rainmapper debería combinar sustrato orgánico, humedad, temperatura, fenología e historial local.

---

# 8. Bibliografía seleccionada

## 1. Vogt-Schilb, H. et al. (2022)

**Título:** Climate-induced long-term changes in the phenology of Mediterranean fungi.  
**Revista:** Fungal Ecology, 60, 101183.  
**Texto completo:** https://hal.science/hal-03869086v1/file/S1754504822000277.pdf

**Aportación:** demuestra que *L. nuda* comienza actualmente a fructificar antes que en el periodo histórico analizado.

**Confianza:** alta para tendencia fenológica; no aporta una función diaria exclusiva.

## 2. Fernández-Ruiz, A. et al. (2023)

**Título:** A Statistical Approach to Macrofungal Diversity in a Mediterranean Forest Ecosystem.  
**Revista:** Forests, 14, 1662.  
**DOI / texto:** https://doi.org/10.3390/f14081662  
**Página:** https://www.mdpi.com/1999-4907/14/8/1662

**Aportación:** clasifica *L. nuda* entre las especies típicas de fructificación otoñal en un seguimiento de comunidades mediterráneas.

**Confianza:** alta para fenología comunitaria; no es un modelo individual.

## 3. Harrington, T. et al. (2019)

**Título:** Assessment of production of wild edible fungi in Irish forests.  
**Informe:** COFORD.  
**Texto completo:** https://www.coford.ie/media/coford/content/FORESTFUNGIFinalReport3251019.pdf

**Aportación:** cuantifica producción de *L. nuda* en parcelas de *Picea sitchensis*, *Pinus sylvestris* y *Abies*.

**Confianza:** alta para producción local y amplitud de hábitat; no demuestra preferencia fisiológica universal.

## 4. Baptista, P. et al. (2010)

**Título:** Diversity and fruiting pattern of macrofungi associated with chestnut (*Castanea sativa*) in the Trás-os-Montes region, Northeast Portugal.  
**Revista:** Fungal Ecology, 3, 9–19.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S175450480900066X

**Aportación:** registra *L. nuda* en castañares y analiza la comunidad en relación con temperatura y precipitación.

**Confianza:** media-alta para hábitat y fenología regional; no ofrece un modelo separado de la especie.

## 5. Kim, J. H. et al. (2012)

**Título:** Soil properties of *Lepista nuda* habitats.  
**Consulta del resumen:** https://www.researchgate.net/publication/264078274_Study_on_characteristic_of_mycelial_culture_in_ear_mushroom

**Aportación:** analiza humedad, pH, materia orgánica y nitrógeno en siete hábitats naturales de *L. nuda*.

**Confianza:** media; número limitado de localidades y acceso bibliográfico incompleto.

## 6. He, Z.-M. et al. (2023)

**Título:** Systematic arrangement within the family Clitocybaceae (Tricholomatineae, Agaricales): phylogenetic and phylogenomic evidence, morphological data and muscarine-producing innovation.  
**Revista:** Fungal Diversity.  
**Página editorial:** https://link.springer.com/article/10.1007/s13225-023-00527-2

**Aportación:** reorganiza la familia y transfiere *Lepista nuda* al género *Collybia*.

**Confianza:** muy alta para taxonomía; no aporta predicción ecológica.

## 7. Hjelm, O. et al. (1999)

**Título:** Production of organically bound halogens by the litter-degrading fungus *Lepista nuda*.  
**Registro:** https://www.diva-portal.org/smash/record.jsf?pid=diva2%3A253043

**Aportación:** demuestra actividad saprótrofa y transformación química de hojarasca en laboratorio y campo.

**Confianza:** alta para función saprótrofa; no aporta un modelo de fructificación.

---

## Nota final sobre la evidencia

La literatura específica de *L. nuda* permite definir con bastante confianza:

- estrategia saprótrofa;
- dependencia de materia orgánica;
- fenología otoñal y tardía;
- cambio histórico de la fecha de primera aparición;
- amplitud de hábitats forestales;
- importancia probable de humedad y temperatura.

No permite definir:

- temperatura óptima de campo;
- umbral de enfriamiento;
- precipitación mínima;
- número de días post-lluvia;
- pH universal;
- tipo de bosque obligatorio.

La estructura más defendible para Rainmapper es: sustrato orgánico + humedad + temperatura + ventana otoñal–invernal + historial local.
