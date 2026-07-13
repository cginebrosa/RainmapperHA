# Predicción de floradas de *Boletus aereus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Boletus aereus* Bull.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que menciona y estudia explícitamente *Boletus aereus*  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal

---

# Resumen ejecutivo

La literatura científica dedicada específicamente a predecir la fructificación de *Boletus aereus* es escasa. No se ha localizado un modelo validado que permita afirmar que la especie aparece después de una cantidad concreta de lluvia, dentro de un número fijo de días o en un intervalo térmico universal. Por tanto, no es científicamente defendible asignar a Rainmapper umbrales numéricos precisos basándose únicamente en publicaciones.

Aun así, los estudios que registran expresamente *B. aereus* permiten extraer varias conclusiones suficientemente consistentes:

1. **Es una especie termófila.** Aparece asociada a los sectores más cálidos de bosques mediterráneos de frondosas y se separa ecológicamente de especies más mesófilas. La temperatura es, por tanto, una variable relevante, pero la literatura específica no permite fijar un óptimo numérico.

2. **La disponibilidad de agua es necesaria, pero no basta con medir lluvia bruta.** La fructificación mediterránea presenta una gran variabilidad entre años. La lluvia debe interpretarse junto con la capacidad del suelo para conservar agua y con las condiciones posteriores que favorecen o aceleran el secado.

3. **El hábitat compatible es un requisito previo.** La evidencia específica sitúa a *B. aereus* principalmente en bosques termófilos de frondosas, especialmente encinares y otros sistemas dominados por *Quercus*. También se ha documentado en castañares y sistemas mixtos de robles y *Cistus*.

4. **Puede fructificar en verano.** Un seguimiento semanal de más de cuatro años en un encinar del oeste de la península ibérica registró *B. aereus* entre las especies presentes en julio y agosto. Esto refuerza la idea de que no debe modelarse exclusivamente como una especie otoñal.

5. **La respuesta es irregular y local.** En inventarios prolongados puede aparecer con baja frecuencia y gran variación interanual. La ausencia de fructificaciones visibles no significa necesariamente ausencia de micelio.

6. **No hay base específica suficiente para considerar viento, humedad relativa, radiación o evapotranspiración como predictores demostrados de la especie.** Son variables físicamente razonables para estimar la conservación de humedad, pero deben tratarse como variables auxiliares o experimentales, no como factores científicamente confirmados para *B. aereus*.

## Factores que deberían entrar en una primera versión sencilla del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Hábitat y hospedador compatible | Filtro previo imprescindible | Alta |
| Temperatura reciente | Indicador de adecuación termófila | Alta |
| Precipitación reciente | Señal de recarga hídrica | Media |
| Humedad o balance hídrico del suelo | Mejor representación del agua disponible | Media |
| Época del año | Ventana fenológica flexible, incluido verano | Media-alta |
| Cobertura, orientación y exposición | Moduladores del microclima | Media |
| Historial local de observaciones | Principal fuente futura de calibración | Muy alta |

**Conclusión práctica:** Rainmapper debería empezar con un modelo probabilístico prudente formado por un filtro de hábitat, una señal térmica cálida, una señal de recarga hídrica y una ventana fenológica flexible. Los pesos y retardos deben aprenderse con observaciones reales. La literatura específica no permite convertir estas relaciones en reglas rígidas.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores pueden incorporarse con una confianza razonable a un modelo de predicción de floradas de *Boletus aereus*, utilizando únicamente trabajos científicos que mencionen y estudien explícitamente esta especie?

Se descartaron como base principal:

- trabajos centrados exclusivamente en *Boletus edulis*;
- estudios de “boletos” sin desglose por especie;
- modelos generales de hongos ectomicorrícicos;
- páginas divulgativas y fichas de recolección;
- afirmaciones con cifras concretas sin metodología científica publicada;
- estudios de composición química o gastronomía sin utilidad ecológica.

Se conservaron trabajos donde *B. aereus* aparece identificado de forma explícita y que aportan información sobre al menos uno de estos aspectos:

- fenología;
- temperatura o exposición;
- hábitat;
- hospedadores;
- estructura forestal;
- frecuencia y regularidad de fructificación;
- presencia del micelio o de cuerpos fructíferos.

La revisión final utiliza **siete publicaciones principales**. No todas modelan la meteorología de la especie; precisamente esa ausencia es una conclusión relevante.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Seguimientos de fructificación

Los estudios más útiles son inventarios plurianuales con parcelas permanentes y muestreos repetidos. Estos trabajos permiten saber cuándo y en qué condiciones ecológicas aparece la especie, pero normalmente no reúnen suficientes observaciones de *B. aereus* para construir una ecuación meteorológica exclusiva.

Fernández-Ruiz et al. realizaron muestreos semanales desde febrero de 2009 hasta junio de 2013 en un encinar mediterráneo del centro-oeste de la península ibérica. *B. aereus* figura expresamente entre las especies micorrícicas recogidas durante julio y agosto. El resultado es importante porque demuestra, en un seguimiento sistemático, que la fenología de la especie puede incluir plenamente el verano.

Sin embargo, el propio estudio destaca una fuerte variación interanual de la fructificación y la influencia de las condiciones meteorológicas de cada año. No proporciona una relación cuantitativa específica entre la presencia de *B. aereus* y la lluvia o temperatura.

**Conclusión útil:** la época del año importa, pero la ventana fenológica debe ser flexible y regional. No debe limitarse la predicción al otoño.

## 2.2. Carácter termófilo

Zotti y Pautasso estudiaron 246 especies en 15 parcelas permanentes de encinares de Liguria durante cuatro años. Su análisis de ordenación relacionó uno de los principales gradientes ecológicos con exposición y temperatura. *Boletus aereus* apareció dentro del grupo de especies más termófilas.

Richard et al., en un encinar mediterráneo maduro de Córcega, también clasificaron *B. aereus* entre las especies vinculadas a bosques termófilos de angiospermas. Además, su producción de cuerpos fructíferos fue baja e irregular dentro del inventario.

Estas dos fuentes, independientes y basadas en ambientes mediterráneos, constituyen la evidencia más sólida para considerar la adecuación térmica como un factor importante.

**Conclusión útil:** el modelo debe favorecer situaciones térmicas cálidas compatibles con el carácter termófilo de la especie, pero no existe evidencia específica suficiente para fijar una temperatura óptima universal.

## 2.3. Hospedadores y ambiente forestal

Los trabajos revisados sitúan la especie en:

- encinares de *Quercus ilex*;
- otros bosques termófilos de frondosas;
- sistemas mixtos de *Quercus* y *Cistus*;
- castañares;
- otros ambientes dominados por fagáceas.

Peintner et al. estudiaron comunidades fúngicas del suelo y cuerpos fructíferos en un bosque de *Castanea sativa*, incluyendo expresamente *B. aereus*. El trabajo confirma que la especie puede estar integrada en comunidades ectomicorrícicas de castañar y que la detección bajo tierra no coincide necesariamente con los cuerpos fructíferos visibles.

Sanz-Benito et al. registraron *B. aereus* en un estudio de cinco años sobre sistemas mixtos de *Quercus pyrenaica* y *Cistus ladanifer*. Aunque los análisis se centran en la comunidad completa, el trabajo demuestra que la especie forma parte de estos mosaicos mediterráneos y que los tratamientos sobre la estructura de la vegetación modifican la producción y composición de esporocarpos.

**Conclusión útil:** el hospedador y la estructura del bosque deben actuar como filtros de aptitud. Una meteorología favorable fuera de un hábitat compatible no debería generar una probabilidad alta.

## 2.4. Irregularidad de la fructificación

En el inventario de Richard et al., *B. aereus* fue una especie rara, de baja frecuencia y baja regularidad de producción de cuerpos fructíferos. Este dato no debe interpretarse como rareza universal, porque corresponde a una localidad concreta, pero sí muestra que la presencia del hongo no garantiza una fructificación frecuente o abundante.

La comparación entre comunidades subterráneas y cuerpos fructíferos en otros estudios refuerza la misma cautela: observar o no observar setas en superficie es una medida imperfecta de la presencia y actividad real del hongo.

**Conclusión útil:** el modelo debe predecir probabilidad de fructificación visible, no presencia biológica del hongo. También debe aceptar un nivel elevado de incertidumbre y falsos negativos aparentes.

---

# 3. Factores predictivos defendibles

## 3.1. Hábitat y hospedador compatible

Es el factor de mayor confianza.

La evidencia específica asocia repetidamente *B. aereus* con bosques mediterráneos cálidos de frondosas. Los encinares aparecen en varias publicaciones, junto con otros robles, castaño y sistemas de *Quercus* con *Cistus*.

En Rainmapper, este factor debería implementarse como un filtro previo:

- presencia probable de hospedadores compatibles;
- tipo de cubierta forestal;
- continuidad y madurez del bosque;
- estructura del sotobosque;
- historial de observaciones confirmadas.

No parece razonable asignar el mismo peso a todos los hospedadores ni descartar automáticamente otros posibles. La literatura revisada confirma asociaciones, pero no establece una jerarquía universal y cuantificada.

## 3.2. Temperatura

La termofilia de *B. aereus* es una de las conclusiones más consistentes.

La temperatura puede tener dos funciones:

1. determinar si el lugar y la época ofrecen un ambiente compatible;
2. modificar la velocidad de pérdida de agua después de una lluvia.

El modelo debería usar temperatura reciente y, cuando sea posible, estimaciones microclimáticas corregidas por:

- altitud;
- orientación;
- cobertura de copa;
- exposición;
- proximidad al suelo.

Lo que no debe hacerse es definir una temperatura exacta como “óptima” o un umbral rígido de bloqueo. Los estudios específicos revisados no lo justifican.

## 3.3. Precipitación y agua disponible

La literatura específica de *B. aereus* no aporta un umbral fiable de precipitación. Aun así, la aparición de cuerpos fructíferos requiere agua y los propios estudios de campo subrayan la influencia de la variabilidad meteorológica en la fenología.

Para Rainmapper conviene diferenciar:

- lluvia registrada;
- lluvia efectiva que infiltra;
- agua que permanece en el suelo;
- velocidad de secado posterior.

La lluvia debe utilizarse como señal de recarga, no como predictor aislado. En una primera versión sencilla pueden calcularse acumulados en varias ventanas temporales, pero sin atribuir a ninguna de ellas el carácter de “ventana demostrada para *B. aereus*”.

La humedad del suelo o un índice de balance hídrico resulta conceptualmente preferible, aunque su superioridad específica para esta especie todavía debe validarse.

## 3.4. Fenología

La evidencia confirma que *B. aereus* puede fructificar durante julio y agosto en encinares ibéricos. También está reconocido como taxón mediterráneo y termófilo.

Por tanto:

- no debe restringirse al otoño;
- la estación favorable puede variar con región y altitud;
- la ventana debe desplazarse según el clima del año;
- el día del año debe funcionar como modulador, no como regla excluyente.

Una opción prudente consiste en aprender la fenología a partir de observaciones regionales y usar la literatura solo para permitir una ventana cálida amplia.

## 3.5. Exposición, cobertura y estructura forestal

El estudio de Zotti y Pautasso relaciona la distribución de especies, incluido *B. aereus*, con gradientes de exposición y temperatura. Los estudios en sistemas de *Quercus* y *Cistus* muestran que la gestión y estructura de la vegetación modifican la comunidad y la producción de cuerpos fructíferos.

Estas variables son relevantes porque cambian el microclima:

- insolación;
- temperatura del suelo;
- conservación de humedad;
- escorrentía;
- evaporación;
- densidad de raíces hospedadoras.

En Rainmapper deben tratarse como modificadores de la señal meteorológica, no como desencadenantes independientes.

---

# 4. Factores que no están demostrados específicamente

## 4.1. Viento

No se ha encontrado, dentro de la literatura seleccionada, un análisis específico que relacione velocidad de viento y fructificación de *B. aereus*.

Puede utilizarse para mejorar una estimación de secado o evapotranspiración, pero su peso debe considerarse experimental.

## 4.2. Humedad relativa

Es físicamente razonable que influya en la conservación de humedad y en el desarrollo de carpóforos. Sin embargo, no se ha localizado una función específica para esta especie.

Debe usarse como variable auxiliar, no como criterio demostrado.

## 4.3. Radiación solar

La radiación afecta a temperatura y evaporación, pero los artículos específicos no cuantifican su efecto sobre *B. aereus*. Su inclusión es razonable dentro del balance hídrico o de un modelo microclimático.

## 4.4. Evapotranspiración y déficit de presión de vapor

Son variables potencialmente útiles para representar pérdida de agua. No obstante, su relevancia específica deberá comprobarse con datos de Rainmapper.

## 4.5. Litología y pH

Los estudios ecológicos permiten identificar ambientes y gradientes, pero no justifican una regla universal de litología o pH aplicable a toda la distribución de la especie.

Estas capas deben utilizarse como información de aptitud flexible y calibrable.

---

# 5. Modelo mínimo recomendado para Rainmapper

Se recomienda una arquitectura sencilla y explicable.

## 5.1. Filtro de hábitat

La celda debe presentar:

- bosque de frondosas compatible;
- hospedador probable;
- condiciones ecológicas coherentes con la distribución regional;
- ausencia de incompatibilidades evidentes.

## 5.2. Adecuación térmica

Usar temperatura reciente para representar el carácter termófilo, mediante una función suave y calibrable.

No establecer valores exactos procedentes de esta revisión.

## 5.3. Estado hídrico

Combinar:

- precipitación reciente;
- humedad antecedente;
- retención estimada del suelo;
- pérdidas posteriores.

El resultado debe ser un índice relativo de disponibilidad de agua.

## 5.4. Fenología regional

Usar el día del año y la altitud como moduladores. Permitir fructificación estival y otoñal allí donde las observaciones locales lo confirmen.

## 5.5. Evidencia observacional

Las observaciones reales deben tener prioridad progresiva sobre los supuestos bibliográficos.

El modelo debe registrar:

- presencia confirmada;
- ausencia con esfuerzo de búsqueda conocido;
- abundancia aproximada;
- fecha;
- hábitat;
- hospedador;
- meteorología previa;
- calidad de identificación.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- máscara de hábitat compatible;
- hospedador o formación forestal;
- temperatura reciente;
- precipitación reciente;
- índice de humedad o balance hídrico;
- día del año;
- altitud;
- historial local de observaciones.

## Recomendables

- orientación;
- pendiente;
- cobertura de copa;
- estructura de sotobosque;
- retención estimada del suelo;
- anomalía térmica respecto a la climatología local.

## Experimentales

- viento;
- humedad relativa;
- radiación;
- evapotranspiración;
- déficit de presión de vapor;
- índices de vegetación;
- indicadores de estrés del hospedador.

La clasificación “experimental” no significa que estas variables sean irrelevantes. Significa que la literatura específica revisada no permite afirmar que sean predictores demostrados de *B. aereus*.

---

# 7. Conclusiones

1. No existe evidencia específica suficiente para construir una regla numérica universal de fructificación de *Boletus aereus*.

2. Los factores más defendibles son:
   - hábitat y hospedador;
   - carácter termófilo;
   - disponibilidad de agua;
   - fenología cálida y flexible;
   - exposición y estructura forestal.

3. La temperatura es importante, pero no se conoce un óptimo universal publicado para la especie.

4. La lluvia es necesaria como fuente de agua, pero no se ha demostrado una cantidad mínima ni un retardo fijo específico.

5. La presencia en julio y agosto está respaldada por un seguimiento semanal plurianual en un encinar ibérico.

6. La especie puede presentar baja frecuencia y fuerte irregularidad interanual incluso en hábitats adecuados.

7. Rainmapper debería modelar probabilidades, no certezas.

8. Los umbrales y pesos deben proceder de las observaciones futuras del proyecto, no de cifras extrapoladas de otras especies.

La literatura permite construir una primera estructura sensata, pero no elimina la incertidumbre. En términos sencillos: el modelo puede identificar cuándo y dónde las condiciones parecen razonables para *B. aereus*, pero seguirá sin poder garantizar que la seta decida fructificar.

---

# 8. Bibliografía seleccionada

## 1. Fernández-Ruiz, A. et al. (2022)

**Título:** Considerations on Field Methodology for Macrofungi Studies in Fragmented Forests of Mediterranean Agricultural Landscapes.  
**Revista:** Agronomy, 12, 528.  
**Enlace:** https://doi.org/10.3390/agronomy12020528  
**Acceso:** https://www.mdpi.com/2073-4395/12/2/528

**Aportación:** seguimiento semanal de febrero de 2009 a junio de 2013 en encinar mediterráneo. Registra expresamente *B. aereus* entre las especies recogidas en julio y agosto. Demuestra además una elevada variación interanual de la fructificación.

**Confianza para esta revisión:** alta para fenología local; baja para umbrales meteorológicos, porque no modela la especie por separado.

## 2. Zotti, M. y Pautasso, M. (2013)

**Título:** Macrofungi in Mediterranean *Quercus ilex* woodlands.  
**Revista:** Czech Mycology, 65(2), 193–218.  
**Enlace:** https://czechmycology.org/_cmo/CM65205.pdf

**Aportación:** inventario de cuatro años en 15 parcelas permanentes. Sitúa *B. aereus* dentro de un grupo de especies termófilas asociado a un gradiente de exposición y temperatura.

**Confianza:** alta para termofilia y hábitat; insuficiente para parámetros meteorológicos numéricos.

## 3. Richard, F. et al. (2004)

**Título:** Diversity and fruiting patterns of ectomycorrhizal and saprobic fungi in an old-growth Mediterranean forest dominated by *Quercus ilex* L.  
**Revista:** Canadian Journal of Botany, 82, 1711–1729.  
**Enlace de consulta:** https://www.researchgate.net/publication/238562609_Diversity_and_fruiting_patterns_of_ectomycorrhizal_and_saprobic_fungi_in_an_old-growth_Mediterranean_forest_dominated_by_Quercus_ilex_L

**Aportación:** clasifica *B. aereus* como especie de bosques termófilos de angiospermas y muestra una frecuencia y producción reducidas en el área estudiada.

**Confianza:** alta para asociación ecológica; local para frecuencia e irregularidad.

## 4. Peintner, U. et al. (2007)

**Título:** Soil fungal communities in a *Castanea sativa* forest: matching molecular data and fruiting bodies.  
**Revista:** Mycological Research, 111, 317–328.  
**PubMed:** https://pubmed.ncbi.nlm.nih.gov/17359260/  
**DOI:** https://doi.org/10.1016/j.mycres.2007.01.004

**Aportación:** incluye expresamente *B. aereus* en el estudio de comunidades fúngicas de un castañar y compara presencia subterránea con cuerpos fructíferos.

**Confianza:** alta para asociación con castaño y para la cautela al interpretar ausencia de esporocarpos.

## 5. Sanz-Benito, I. et al. (2022)

**Título:** Effects of fuel reduction treatments on the sporocarp production and richness of a *Quercus/Cistus* mixed system.  
**Revista:** Forest Ecology and Management, 505, 119798.  
**DOI:** https://doi.org/10.1016/j.foreco.2021.119798  
**Acceso:** https://www.sciencedirect.com/science/article/pii/S0378112721008896

**Aportación:** estudio de cinco años en sistemas de *Quercus pyrenaica* y *Cistus ladanifer* que incluye *B. aereus* en el inventario. Evidencia que la estructura y los tratamientos de la vegetación pueden modificar la producción y composición de la comunidad fúngica.

**Confianza:** media para el papel de la estructura forestal; no permite aislar la respuesta de *B. aereus*.

## 6. Loizides, M. et al. (2019)

**Título:** Phylogenetic and distributional data on boletoid fungi in Cyprus and description of a new sampling methodology.  
**Revista:** Data in Brief, 25, 104219.  
**DOI:** https://doi.org/10.1016/j.dib.2019.104219  
**Acceso:** https://www.sciencedirect.com/science/article/pii/S235234091930469X

**Aportación:** aporta registros ecológicos, fenológicos y de distribución mediterránea de boletoides identificados molecularmente, incluyendo *B. aereus*.

**Confianza:** media-alta para distribución y contexto mediterráneo; limitada para predicción meteorológica.

## 7. Martins, A. et al.

**Título:** Management of chestnut plantations for a multifunctional land use under Mediterranean conditions: effects on productivity and sustainability.  
**Acceso al documento:** https://repositorio.utad.pt/server/api/core/bitstreams/c073f37f-4052-48f1-bb32-1ae1eb732cc6/content

**Aportación:** incluye *B. aereus* entre las especies comestibles asociadas a plantaciones de castaño y aporta contexto sobre manejo y productividad fúngica en sistemas mediterráneos.

**Confianza:** media para hábitat y manejo; no ofrece un modelo meteorológico exclusivo de la especie.

---

## Nota final sobre la evidencia

Se localizaron numerosos artículos que mencionan *B. aereus* únicamente como parte del complejo *B. edulis*, en listas florísticas o en estudios químicos. No se utilizaron para inferir umbrales de fructificación. También se descartaron modelos de *B. edulis* y de comunidades ectomicorrícicas generales, aunque pudieran sugerir variables plausibles, porque el criterio de esta revisión era conservar únicamente evidencia donde *B. aereus* apareciera de manera explícita.
