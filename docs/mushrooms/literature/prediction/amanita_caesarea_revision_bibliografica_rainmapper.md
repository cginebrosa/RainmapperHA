# Predicción de floradas de *Amanita caesarea*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Amanita caesarea* (Scop.) Pers.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que menciona y estudia explícitamente *Amanita caesarea*  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal

---

# Resumen ejecutivo

La literatura científica dedicada específicamente a predecir la fructificación de *Amanita caesarea* es escasa. No se ha localizado un modelo meteorológico validado para la especie que permita establecer una cantidad mínima de lluvia, una temperatura óptima de fructificación o un número fijo de días entre la precipitación y la aparición de cuerpos fructíferos.

Sí existe, en cambio, evidencia específica suficiente para definir con bastante confianza su perfil ecológico básico y seleccionar los factores que deberían formar parte de un modelo prudente:

1. **Es una especie termófila.** Los estudios de comunidades mediterráneas la sitúan repetidamente entre las especies asociadas a bosques cálidos de frondosas. La temperatura es, por tanto, una variable relevante, aunque no existe un óptimo numérico de fructificación validado en campo.

2. **Su hábitat principal son los bosques de *Quercus*.** La especie aparece expresamente documentada en encinares, alcornocales y otros robledales mediterráneos. También puede formar ectomicorrizas con *Castanea sativa*, pero el bosque de frondosas termófilas debe constituir el filtro principal de aptitud.

3. **La fructificación se concentra en la época cálida.** La evidencia de campo y los inventarios mediterráneos respaldan una fenología de verano y otoño temprano o medio, desplazable según región, altitud y clima anual.

4. **La disponibilidad de agua es necesaria, pero la literatura específica no permite reducirla a una cifra de precipitación.** La lluvia debe interpretarse como recarga potencial del suelo y combinarse con temperatura, exposición, cobertura y capacidad de retención.

5. **El crecimiento vegetativo del micelio responde a temperatura y pH en cultivo.** Daza et al. demostraron diferencias entre aislados y crecimiento en un intervalo térmico relativamente cálido y en medios próximos a la neutralidad. Estos resultados son útiles para confirmar la termofilia fisiológica, pero no deben convertirse directamente en umbrales de fructificación en campo.

6. **La estructura del bosque y los claros pueden influir.** En encinares mediterráneos maduros, *A. caesarea* aparece asociada a comunidades termófilas y a ambientes donde exposición, apertura del dosel y microclima son relevantes.

7. **No existe evidencia específica suficiente para asignar pesos independientes al viento, humedad relativa, radiación o evapotranspiración.** Son variables físicamente razonables para representar el secado, pero deben tratarse como auxiliares o experimentales.

## Factores que deberían entrar en una primera versión sencilla del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Quercus* compatible | Filtro ecológico principal | Alta |
| Bosque termófilo de frondosas | Filtro de aptitud | Alta |
| Temperatura reciente | Indicador de adecuación térmica | Alta |
| Precipitación reciente | Señal de recarga hídrica | Media |
| Humedad o balance hídrico del suelo | Representación del agua disponible | Media |
| Época del año | Ventana flexible de verano–otoño | Media-alta |
| Cobertura y exposición | Modificadores del microclima | Media |
| Historial local de observaciones | Fuente principal de calibración | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *Amanita caesarea* mediante un filtro de bosques cálidos de frondosas —especialmente *Quercus*—, combinado con una señal de temperatura favorable, una señal hídrica y una ventana fenológica de verano–otoño. La literatura específica permite seleccionar estos factores, pero no justificar umbrales meteorológicos rígidos.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores pueden incorporarse con una confianza razonable a un modelo de predicción de floradas de *Amanita caesarea*, utilizando únicamente trabajos científicos que mencionen y estudien explícitamente esta especie?

Se descartaron como fundamento principal:

- estudios dedicados a otras especies de *Amanita*;
- trabajos sobre el complejo *Amanita caesarea* de América o Asia cuando la identidad taxonómica no corresponde claramente a la especie europea;
- modelos generales de hongos ectomicorrícicos;
- páginas divulgativas sin metodología científica;
- cifras de lluvia, temperatura o días hasta fructificación sin publicación verificable;
- estudios exclusivamente químicos, toxicológicos o gastronómicos.

Se conservaron publicaciones donde *A. caesarea* aparece identificada expresamente y que aportan información sobre:

- termofilia;
- hospedadores;
- hábitat;
- fenología;
- crecimiento micelial;
- ectomicorrización;
- estructura del bosque;
- distribución en comunidades mediterráneas.

La revisión final utiliza **ocho publicaciones principales**. Ninguna proporciona por sí sola un modelo meteorológico de fructificación de la especie.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Carácter termófilo

Richard et al. estudiaron durante varios años la diversidad y los patrones de fructificación de hongos en un encinar mediterráneo maduro dominado por *Quercus ilex* en Córcega. *Amanita caesarea* fue clasificada expresamente como especie termófila asociada a frondosas.

Zotti y Pautasso, en un estudio de cuatro años sobre 15 parcelas permanentes de encinar mediterráneo, también situaron a las especies termófilas a lo largo de gradientes relacionados con exposición y temperatura. *A. caesarea* formó parte de la comunidad característica de estos ambientes cálidos.

La coincidencia entre estudios independientes permite considerar la termofilia como uno de los rasgos mejor respaldados de la especie.

**Conclusión útil:** la temperatura debe ser una variable prioritaria, pero no existe un intervalo óptimo de fructificación en campo que pueda trasladarse directamente a Rainmapper.

## 2.2. Asociación con *Quercus*

Los estudios mediterráneos revisados registran *A. caesarea* principalmente en:

- encinares de *Quercus ilex*;
- alcornocales de *Quercus suber*;
- robledales mediterráneos;
- bosques mixtos de frondosas termófilas.

El inventario de Richard et al. la sitúa en un encinar maduro. Zotti y Pautasso la incluyen en comunidades de *Q. ilex*. Ambrosio et al. la registran en bosques mediterráneos de robles. El trabajo de Rinaldi et al. documenta ejemplares en formaciones xerófilas mixtas de *Q. ilex* y *Q. suber* en Cerdeña.

**Conclusión útil:** la distribución de *Quercus* debe actuar como filtro ecológico principal. La presencia de un roble compatible no garantiza la fructificación, pero su ausencia debería reducir notablemente la aptitud.

## 2.3. Asociación con castaño

Meotto, Pellegrino y Bounous produjeron ectomicorrizas sintéticas entre *A. caesarea* y plántulas de *Castanea sativa* y siguieron su evolución en condiciones de campo.

El estudio demuestra que el castaño es un hospedador compatible y que la simbiosis puede establecerse experimentalmente. No demuestra, sin embargo, que todos los castañares tengan la misma aptitud ni que la presencia de castaño asegure fructificaciones.

**Conclusión útil:** los castañares deben considerarse hábitats compatibles secundarios, especialmente allí donde existan observaciones regionales.

## 2.4. Crecimiento micelial y temperatura

Daza et al. estudiaron varios aislados de *A. caesarea* en cultivo y analizaron el efecto de fuentes de carbono y nitrógeno, pH y temperatura. El trabajo confirmó que el crecimiento depende del aislado y que la especie presenta crecimiento vegetativo en condiciones térmicas relativamente cálidas.

Este estudio es uno de los pocos que evalúa experimentalmente la temperatura sobre material específico de *A. caesarea*. Su principal utilidad para Rainmapper es confirmar que el micelio tiene una respuesta térmica y que no debe asumirse un comportamiento idéntico para todos los aislados.

No obstante:

- el crecimiento en placa no equivale a fructificación;
- el medio de cultivo no reproduce el suelo;
- el óptimo micelial no tiene por qué coincidir con el óptimo de aparición de carpóforos;
- no debe utilizarse como umbral meteorológico directo.

**Conclusión útil:** confirma la importancia de la temperatura y la variabilidad intraespecífica, pero no proporciona una regla de fructificación.

## 2.5. Fenología cálida

Los inventarios mediterráneos y las descripciones de campo incluidas en los trabajos seleccionados sitúan la fructificación de *A. caesarea* en la época cálida, normalmente entre verano y otoño.

La especie aparece en ambientes mediterráneos donde la fructificación puede seguir a episodios de lluvia durante periodos todavía cálidos. Sin embargo, la literatura científica específica revisada no permite afirmar:

- una fecha universal de inicio;
- un mes óptimo;
- un número fijo de días después de la lluvia;
- una temperatura mínima nocturna concreta.

**Conclusión útil:** la fenología debe modelarse como una ventana amplia y regional, no como un calendario rígido.

## 2.6. Apertura, exposición y microclima forestal

El estudio de Richard et al. se desarrolló en un encinar con dinámica de claros naturales, mientras que Zotti y Pautasso identificaron gradientes ecológicos relacionados con exposición y temperatura.

Estos trabajos no construyen un modelo específico para *A. caesarea*, pero respaldan que la estructura del bosque influye en el microclima y en la composición de la comunidad fúngica.

Una apertura moderada puede modificar:

- radiación;
- calentamiento del suelo;
- evaporación;
- humedad;
- vigor de los árboles;
- distribución de raíces finas.

**Conclusión útil:** cobertura y exposición deben actuar como moduladores, no como desencadenantes independientes.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y formación forestal

Es el factor más sólido.

La evidencia específica apoya especialmente:

- *Quercus ilex*;
- *Quercus suber*;
- otros *Quercus* mediterráneos;
- *Castanea sativa* como hospedador compatible;
- bosques mixtos de frondosas termófilas.

Para Rainmapper se recomienda una jerarquía conceptual:

1. bosques de *Quercus* con observaciones regionales;
2. otros robledales mediterráneos compatibles;
3. castañares con condiciones adecuadas;
4. bosques mixtos de frondosas termófilas;
5. hábitats sin hospedadores documentados, con aptitud baja.

No deben asignarse pesos numéricos a partir de esta revisión.

## 3.2. Temperatura

La termofilia es una conclusión bien respaldada por estudios de campo y por cultivo micelial.

La temperatura debería emplearse para representar:

- adecuación de la estación;
- persistencia de condiciones cálidas;
- desplazamiento altitudinal de la fenología;
- capacidad de secado posterior a la lluvia.

El efecto debe ser no lineal. El hecho de que la especie sea termófila no implica que el calor extremo sea siempre favorable.

## 3.3. Agua disponible

La fructificación requiere agua, pero ningún trabajo específico revisado ofrece un umbral de lluvia reproducible para *A. caesarea*.

Rainmapper debería distinguir:

- precipitación;
- infiltración;
- humedad antecedente;
- capacidad de retención;
- secado posterior;
- cobertura y exposición.

La variable más próxima al proceso biológico sería un índice de humedad del suelo, aunque su superioridad específica para esta especie debe validarse.

## 3.4. Fenología regional

La ventana general de verano–otoño está razonablemente respaldada.

El modelo debería ajustar esta ventana mediante:

- día del año;
- altitud;
- región climática;
- anomalía térmica;
- primeras observaciones locales de la campaña.

La fecha no debe actuar como exclusión absoluta.

## 3.5. Cobertura, exposición y apertura del dosel

Estas variables modifican simultáneamente temperatura y humedad.

Deben considerarse:

- orientación;
- pendiente;
- cobertura de copa;
- densidad del arbolado;
- presencia de claros;
- exposición al sol.

No existe evidencia específica para definir una cobertura óptima universal.

## 3.6. Suelo

Daza et al. analizaron el efecto del pH sobre crecimiento en cultivo, pero esos resultados no pueden traducirse directamente a una preferencia edáfica rígida en campo.

Para Rainmapper, el suelo debería utilizarse como modulador mediante:

- pH estimado;
- textura;
- drenaje;
- capacidad de retención;
- materia orgánica;
- litología.

No se justifica excluir automáticamente todos los suelos fuera de un intervalo concreto.

---

# 4. Factores que no están demostrados específicamente

## 4.1. Cantidad mínima de lluvia

No se ha localizado una cantidad mínima validada para activar una florada de *A. caesarea*.

Cualquier cifra debe proceder de observaciones locales.

## 4.2. Número de días entre lluvia y fructificación

No existe un retardo universal publicado para la especie.

Rainmapper deberá probar distintas ventanas temporales y aprenderlas a partir de datos reales.

## 4.3. Temperatura óptima de fructificación

El estudio de Daza et al. se refiere a crecimiento micelial en cultivo. No debe utilizarse como temperatura óptima de aparición de setas.

## 4.4. Viento

No se ha encontrado un análisis específico del efecto del viento sobre *A. caesarea*.

Puede emplearse para estimar secado, pero su peso debe considerarse experimental.

## 4.5. Humedad relativa y radiación

Ambas afectan al microclima, pero no existen funciones específicas publicadas para la fructificación de la especie.

## 4.6. Evapotranspiración y déficit de presión de vapor

Son variables útiles para representar pérdida de agua. Su relevancia específica debe validarse con observaciones.

## 4.7. Umbral universal de pH

Los resultados de cultivo no justifican un intervalo edáfico rígido para poblaciones naturales.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro de hábitat

Priorizar:

- bosques de *Quercus*;
- encinares y alcornocales;
- otros robledales mediterráneos;
- castañares compatibles;
- continuidad del arbolado;
- historial regional de presencia.

## 5.2. Adecuación térmica

Usar una función flexible basada en:

- temperatura reciente;
- persistencia del calor;
- altitud;
- orientación;
- cobertura forestal;
- región climática.

No utilizar umbrales numéricos procedentes directamente del cultivo micelial.

## 5.3. Estado hídrico

Combinar:

- precipitación reciente;
- humedad antecedente;
- retención del suelo;
- pendiente;
- cobertura;
- pérdidas por secado.

La salida debería ser un índice relativo de agua disponible.

## 5.4. Ventana fenológica

Partir de una ventana amplia de verano–otoño y ajustarla por región y altitud.

## 5.5. Microclima forestal

Incluir:

- cobertura de copa;
- exposición;
- orientación;
- estructura del bosque;
- presencia de claros.

## 5.6. Evidencia observacional

Registrar:

- identificación confirmada;
- fecha y coordenadas;
- abundancia aproximada;
- hospedador dominante;
- cobertura;
- altitud;
- orientación;
- tipo de suelo;
- esfuerzo de búsqueda;
- meteorología previa.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- distribución de *Quercus* por especie;
- tipo de bosque;
- temperatura reciente;
- precipitación reciente;
- humedad o balance hídrico;
- día del año;
- altitud;
- historial local de observaciones.

## Recomendables

- *Castanea sativa*;
- orientación;
- pendiente;
- cobertura de copa;
- estructura del bosque;
- pH estimado;
- textura y retención del suelo;
- anomalías térmicas y pluviométricas.

## Experimentales

- viento;
- humedad relativa;
- radiación;
- evapotranspiración;
- déficit de presión de vapor;
- índices de vigor del arbolado;
- distancia a claros;
- intensidad de gestión forestal.

“Experimental” significa que la literatura específica no permite confirmar su peso independiente para *A. caesarea*.

---

# 7. Conclusiones

1. No existe un modelo meteorológico específico y validado para predecir las floradas de *Amanita caesarea*.

2. La termofilia es uno de los rasgos mejor demostrados.

3. Los bosques de *Quercus*, especialmente encinares y alcornocales, constituyen el hábitat principal más respaldado.

4. *Castanea sativa* es un hospedador compatible demostrado experimentalmente.

5. La fenología general se concentra en verano y otoño, pero cambia según región, altitud y campaña.

6. La lluvia debe utilizarse como señal de recarga hídrica, no como regla aislada.

7. El crecimiento micelial en cultivo confirma la respuesta a temperatura y pH, pero no permite fijar umbrales de fructificación en campo.

8. La cobertura, la exposición y la apertura del bosque son moduladores plausibles del microclima.

9. Viento, humedad relativa, radiación y evapotranspiración deben tratarse como variables auxiliares hasta que existan datos locales suficientes.

10. Los pesos y umbrales del modelo deben aprenderse con observaciones de Rainmapper.

Rainmapper puede estimar cuándo un bosque cálido de frondosas presenta condiciones razonablemente favorables para *A. caesarea*, pero la literatura específica no permite convertir esa estimación en una predicción determinista.

---

# 8. Bibliografía seleccionada

## 1. Daza, A. et al. (2006)

**Título:** Effect of carbon and nitrogen sources, pH and temperature on in vitro culture of several isolates of *Amanita caesarea* (Scop.:Fr.) Pers.  
**Revista:** Mycorrhiza, 16, 133–136.  
**DOI:** https://doi.org/10.1007/s00572-005-0025-6  
**Página editorial:** https://link.springer.com/article/10.1007/s00572-005-0025-6

**Aportación:** estudio experimental específico de varios aislados de *A. caesarea*. Confirma el efecto de temperatura y pH sobre el crecimiento micelial y muestra variabilidad entre aislados.

**Confianza:** alta para fisiología micelial en cultivo; baja para umbrales de fructificación en campo.

## 2. Richard, F. et al. (2004)

**Título:** Diversity and fruiting patterns of ectomycorrhizal and saprobic fungi in an old-growth Mediterranean forest dominated by *Quercus ilex* L.  
**Revista:** Canadian Journal of Botany, 82, 1711–1729.  
**Acceso:** https://www.researchgate.net/publication/238562609_Diversity_and_fruiting_patterns_of_ectomycorrhizal_and_saprobic_fungi_in_an_old-growth_Mediterranean_forest_dominated_by_Quercus_ilex_L

**Aportación:** registra explícitamente *A. caesarea* en encinar mediterráneo maduro y la clasifica como especie termófila asociada a frondosas.

**Confianza:** alta para hábitat y termofilia; local para frecuencia de fructificación.

## 3. Zotti, M. y Pautasso, M. (2013)

**Título:** Macrofungi in Mediterranean *Quercus ilex* woodlands.  
**Revista:** Czech Mycology, 65(2), 193–218.  
**Texto completo:** https://czechmycology.org/_cmo/CM65205.pdf

**Aportación:** inventario de cuatro años en 15 parcelas permanentes de encinar. Sitúa a la comunidad fúngica a lo largo de gradientes relacionados con exposición y temperatura e incluye *A. caesarea*.

**Confianza:** alta para contexto ecológico mediterráneo; insuficiente para parámetros meteorológicos exclusivos.

## 4. Meotto, F., Pellegrino, S. y Bounous, G. (1999)

**Título:** Evolution of *Amanita caesarea* and *Boletus edulis* synthetic ectomycorrhizae on European chestnut (*Castanea sativa*) seedlings under field conditions.  
**Publicación:** Acta Horticulturae, 494, 201–204.  
**DOI:** https://doi.org/10.17660/ActaHortic.1999.494.30  
**Página:** https://www.actahort.org/books/494/494_30.htm

**Aportación:** demuestra experimentalmente la formación y persistencia de ectomicorrizas entre *A. caesarea* y *Castanea sativa*.

**Confianza:** alta para compatibilidad con castaño; no aporta predicción de fructificación.

## 5. Ambrosio, E. et al. (2018)

**Título:** An annotated checklist of macrofungi in broadleaf Mediterranean forests.  
**Documento:** https://pdfs.semanticscholar.org/155f/d83ff557c9c71cdfdde0622a91891f6e6475.pdf

**Aportación:** registra explícitamente *A. caesarea* en bosque mediterráneo de robles y la clasifica como ectomicorrícica.

**Confianza:** media-alta para hábitat; limitada para meteorología y fenología.

## 6. Baptista, P. et al. (2010)

**Título:** Diversity and fruiting pattern of macrofungi associated with chestnut (*Castanea sativa*) in the Trás-os-Montes region, Northeast Portugal.  
**Revista:** Fungal Ecology, 3, 9–19.  
**Página editorial:** https://www.sciencedirect.com/science/article/abs/pii/S175450480900066X  
**Texto accesible:** https://bibliotecadigital.ipb.pt/server/api/core/bitstreams/5c0c2b10-8788-4c4b-a428-0391ea80d194/content

**Aportación:** incluye expresamente *A. caesarea* entre las especies comestibles de interés regional y estudia diversidad y patrones de fructificación en castañares.

**Confianza:** media para contexto ecológico y fenológico; no ofrece un modelo separado de la especie.

## 7. Rinaldi, A. C. et al. (2018)

**Título:** Sardinia: Mycovisions from a Charming Land.  
**Revista:** Current Research in Environmental & Applied Mycology.  
**Texto completo:** https://www.creamjournal.org/pdf/CREAM_8_5_1.pdf

**Aportación:** documenta *A. caesarea* en un bosque xerófilo mixto de *Quercus ilex* y *Quercus suber* en Cerdeña y refuerza su carácter mediterráneo y termófilo.

**Confianza:** media-alta para hábitat; descriptiva para predicción.

## 8. Zotti, M. et al. (2024)

**Título:** Checklist of Macrofungi Associated with Nine Different Woody Plant Species in Mediterranean Environments.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11050982/

**Aportación:** incluye explícitamente *A. caesarea* en inventarios asociados a distintas formaciones leñosas mediterráneas y aporta contexto sobre amplitud de hospedadores y hábitats.

**Confianza:** media para asociaciones ecológicas; no cuantifica respuesta meteorológica.

---

## Nota final sobre la evidencia

Se localizaron numerosos artículos sobre el complejo *Amanita caesarea* de México, Asia y Norteamérica. No se utilizaron para caracterizar directamente la especie europea porque varios taxones antes agrupados bajo ese nombre se consideran hoy especies distintas.

También se descartaron estudios sobre composición química, acumulación de metales, gastronomía y conocimiento tradicional, ya que no aportan evidencia útil para predecir floradas.

La selección mantiene una conclusión prudente: la literatura permite definir con bastante confianza el hábitat, la termofilia y la fenología general, pero no una receta meteorológica cuantitativa.
