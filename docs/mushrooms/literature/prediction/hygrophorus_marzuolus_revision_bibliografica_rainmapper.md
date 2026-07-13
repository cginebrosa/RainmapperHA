# Predicción de floradas de *Hygrophorus marzuolus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Hygrophorus marzuolus* (Fr.) Bres.  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia o menciona explícitamente *Hygrophorus marzuolus* y aporta información útil sobre fructificación, fenología, hábitat, hospedador, nieve, estructura forestal o productividad.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

La literatura científica específicamente orientada a predecir las floradas de *Hygrophorus marzuolus* es escasa. Existen trabajos de productividad y presión recolectora en *Pinus sylvestris*, estudios ecológicos de hábitat y referencias sobre su carácter nivícola o subnivícola, pero no se ha localizado un modelo meteorológico validado y generalizable que permita fijar una cantidad mínima de lluvia, una temperatura óptima o un número universal de días entre el deshielo y la aparición de carpóforos.

Las conclusiones mejor respaldadas son:

1. **Es una especie ectomicorrícica asociada principalmente a bosques montanos de coníferas.** La literatura europea la sitúa sobre todo con *Abies*, *Pinus* y, en menor medida, *Picea*. En España está bien documentada en pinares de *Pinus sylvestris*.

2. **Su fenología es invernal y primaveral temprana.** En Pinar Grande, Soria, la producción se siguió entre febrero y abril. En otras regiones europeas aparece desde finales del invierno hasta primavera, con desplazamiento por altitud y clima.

3. **La relación con la nieve y el deshielo es uno de sus rasgos ecológicos más característicos.** La especie puede iniciar el desarrollo bajo la nieve o emerger en los bordes de neveros en fusión.

4. **La nieve no debe interpretarse como un simple requisito binario.** Probablemente actúa mediante aislamiento térmico, aporte gradual de agua y sincronización fenológica, pero la literatura seleccionada no proporciona un espesor, duración o fecha de deshielo universal.

5. **La producción puede concentrarse en colonias localizadas y repetitivas.** El estudio de Pinar Grande identificó numerosas colonias dentro de transectos permanentes y mostró que la distribución espacial no era homogénea.

6. **La estructura forestal puede influir en la producción.** En Pinar Grande se comparó la aparición entre clases de edad de *Pinus sylvestris*, pero la evidencia disponible no permite fijar una edad óptima universal del rodal.

7. **La presión recolectora puede ser elevada y eliminar una parte importante de la producción visible.** Para interpretar observaciones de ausencia o baja abundancia, Rainmapper debe considerar el esfuerzo de búsqueda y la recolección previa.

8. **La fecha de fructificación puede quedar desacoplada de la lluvia líquida reciente.** La reserva de agua aportada por la nieve y el suelo húmedo tras el deshielo puede ser más relevante que la precipitación de los últimos días.

9. **No existe evidencia suficiente para asignar umbrales independientes a viento, humedad relativa, radiación o evapotranspiración.** Estas variables pueden modificar el ritmo de fusión y secado, pero no están demostradas como predictores específicos por separado.

10. **La identidad taxonómica debe revisarse fuera de Europa.** Parte del material norteamericano denominado históricamente *H. marzuolus* puede representar linajes o interpretaciones taxonómicas distintas; los datos europeos son los más directamente aplicables a Rainmapper.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Bosque compatible de *Pinus* o *Abies* | Filtro ecológico principal | Alta |
| Historial local de colonias | Predictor espacial principal | Muy alta |
| Presencia y duración de nieve | Modulador fenológico e hídrico | Alta |
| Fecha de deshielo | Señal de activación | Alta |
| Temperatura del suelo o aire cerca del deshielo | Modulador térmico | Media-alta |
| Humedad del suelo tras el deshielo | Estado hídrico | Media-alta |
| Día del año | Ventana fenológica | Alta |
| Altitud | Modulador climático | Alta |
| Estructura y edad del rodal | Modulador de aptitud | Media |
| Presión recolectora | Corrección de observabilidad | Media-alta |

**Conclusión práctica:** Rainmapper debería modelar *H. marzuolus* mediante un filtro de bosques montanos de coníferas, un componente nival centrado en presencia y fecha de deshielo, una señal de humedad del suelo y un peso muy alto del historial local. La literatura no permite fijar umbrales numéricos universales de nieve, temperatura o días desde el deshielo.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Hygrophorus marzuolus*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de otras especies nivícolas sin resultados para *H. marzuolus*;
- páginas divulgativas con cifras de temperatura, nieve o días hasta aparición;
- trabajos químicos, nutricionales o de contaminación;
- modelos generales de productividad fúngica sin desglose de especie;
- registros norteamericanos cuya identidad taxonómica no era clara;
- inventarios donde la especie aparecía solo en una lista sin información útil;
- afirmaciones tradicionales sobre fases lunares o fechas fijas.

Se seleccionaron **seis referencias principales**, priorizando el estudio de Pinar Grande, trabajos ecológicos de hábitat, fuentes taxonómicas y estudios de comunidades de coníferas donde la especie aparece explícitamente.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Asociación con coníferas

La literatura europea sitúa *H. marzuolus* principalmente en bosques montanos de coníferas.

Los hospedadores y contextos más repetidos son:

- *Abies alba* y otros abetos;
- *Pinus sylvestris*;
- otros *Pinus* de montaña;
- en algunas referencias, *Picea*;
- bosques mixtos de coníferas y frondosas.

El estudio de Macedonia lo registra en:

- masas de *Abies borisii-regis*;
- bosques mixtos con *Pinus peuce*;
- formaciones con *Pinus nigra* y *Quercus*.

En Pinar Grande, la especie se estudió en una gran masa de *Pinus sylvestris*.

**Conclusión útil:** Rainmapper debe usar coníferas compatibles como filtro principal, con especial peso de pinos y abetos.

## 2.2. Producción en Pinar Grande

Altelarrea Martínez y Martínez-Peña estudiaron la dinámica de producción de *H. marzuolus* en Pinar Grande, Soria.

El diseño incluyó:

- nueve transectos;
- once inventarios;
- seguimiento desde la semana 5 hasta la 18 del año;
- muestreos entre febrero y abril;
- interrupciones cuando el suelo permaneció cubierto de nieve;
- localización de 122 colonias;
- registro de 326 carpóforos;
- seguimiento de ejemplares para estudiar evolución y destino.

El trabajo analizó:

- producción potencial;
- producción recolectada;
- consumo por fauna;
- producción malograda;
- clases de edad del pinar;
- presión recolectora;
- tamaño de los carpóforos;
- esporulación.

No publicó un modelo meteorológico universal.

**Conclusión útil:** la especie presenta una producción espacialmente concentrada en colonias y una campaña prolongada desde pleno invierno hasta primavera temprana.

## 2.3. Nieve y deshielo

La especie está ampliamente descrita como asociada a neveros y a la fusión de la nieve.

Las fuentes revisadas indican que:

- puede desarrollarse bajo la nieve;
- puede emerger al retirarse el nevero;
- aparece en bordes de nieve en fusión;
- puede permanecer parcialmente cubierta por suelo, musgo o acículas;
- el deshielo marca el acceso visual a carpóforos que pudieron iniciar su desarrollo antes.

Esto obliga a distinguir:

- inicio del desarrollo;
- emergencia;
- detección por el observador.

**Conclusión útil:** la fecha de observación no equivale necesariamente a la fecha de inicio de fructificación.

## 2.4. Qué función puede desempeñar la nieve

La literatura específica permite sostener la asociación, pero no cuantifica completamente el mecanismo.

Las funciones plausibles de la nieve son:

- aislamiento frente a heladas extremas;
- mantenimiento de una temperatura del suelo más estable;
- aporte gradual de agua durante la fusión;
- protección frente a desecación;
- sincronización de la campaña.

Estas funciones son coherentes con la física del manto nival, pero no todas han sido demostradas experimentalmente para *H. marzuolus*.

**Conclusión útil:** Rainmapper puede utilizar nieve y deshielo como variables de estado, pero debe evitar afirmar un mecanismo único no demostrado.

## 2.5. Fenología regional

En Pinar Grande, el seguimiento se extendió de febrero a abril.

En otras regiones europeas:

- puede aparecer en enero en inviernos suaves;
- la campaña suele concentrarse en marzo y abril;
- en cotas altas puede prolongarse hacia mayo;
- la fecha cambia con duración de la nieve y altitud.

La especie recibe nombres comunes relacionados con marzo, pero ese nombre no constituye una regla fenológica.

**Conclusión útil:** el día del año debe interactuar con altitud, nieve y anomalía térmica.

## 2.6. Altitud

La especie se asocia frecuentemente a bosques montanos y subalpinos.

La altitud influye mediante:

- duración de la cubierta nival;
- temperatura del suelo;
- fecha de deshielo;
- composición forestal;
- duración de la estación de crecimiento.

No se ha localizado un intervalo altitudinal universal aplicable a todas las regiones europeas.

**Conclusión útil:** utilizar altitud como modulador climático, no como límite rígido.

## 2.7. Suelo, musgo y cubierta orgánica

Los carpóforos se describen con frecuencia:

- bajo acículas;
- parcialmente enterrados;
- bajo musgo;
- en suelos húmedos del bosque;
- cerca del frente de fusión de nieve.

No se ha localizado evidencia suficiente para fijar:

- pH óptimo;
- litología obligatoria;
- espesor de hojarasca;
- porcentaje de musgo;
- textura universal.

**Conclusión útil:** cobertura orgánica y musgo son indicadores útiles de microhábitat, no requisitos cuantificados.

## 2.8. Estructura y edad del rodal

El estudio de Pinar Grande comparó la producción entre clases de edad de *Pinus sylvestris*.

La existencia de diferencias entre clases sugiere que la estructura forestal puede influir, pero la información disponible no justifica establecer una edad óptima universal.

La edad del rodal puede representar de forma indirecta:

- densidad;
- área basimétrica;
- continuidad del hospedador;
- cobertura;
- acumulación de acículas;
- microclima;
- desarrollo de la red ectomicorrícica.

**Conclusión útil:** Rainmapper debería registrar estructura y edad, pero aprender sus efectos regionalmente.

## 2.9. Presión recolectora y observabilidad

El estudio de Pinar Grande registró visitas de recolectores durante la campaña.

La presión recolectora puede provocar que:

- una colonia productiva parezca vacía cuando se visita tarde;
- se reduzca la abundancia observable;
- los datos oportunistas infravaloren la producción;
- las ausencias sin control de esfuerzo sean poco fiables.

El trabajo también separó:

- producción potencial;
- ejemplares recolectados;
- ejemplares consumidos por fauna;
- ejemplares malogrados.

**Conclusión útil:** Rainmapper debe distinguir producción biológica de observación disponible.

## 2.10. Esporulación y tamaño

Altelarrea Martínez y Martínez-Peña analizaron la relación entre tamaño del sombrero y esporulación.

El objetivo era valorar en qué momento un carpóforo ha contribuido a la dispersión de esporas.

Este resultado es relevante para gestión de recolección, pero no permite predecir el inicio de la florada.

**Conclusión útil:** tamaño y madurez pueden mejorar la interpretación de observaciones, no el desencadenamiento meteorológico.

## 2.11. Hábitats balcánicos

La tipificación ecológica reciente de hábitats en Bijambare y los registros macedonios confirman la presencia en bosques húmedos y montanos con coníferas.

Estos trabajos amplían la evidencia geográfica y muestran que la especie no está limitada a un único tipo de pinar ibérico.

Sin embargo, no proporcionan un modelo meteorológico transferible.

**Conclusión útil:** el filtro de hábitat debe admitir varios bosques montanos de coníferas y ajustarse regionalmente.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y tipo de bosque

Variables prioritarias:

- *Pinus sylvestris*;
- *Abies* spp.;
- otros pinos de montaña;
- *Picea* como asociación menos consistentemente documentada;
- bosques mixtos con coníferas.

La presencia de frondosas no debe excluir automáticamente la especie cuando hay coníferas compatibles.

## 3.2. Nieve acumulada

Rainmapper debería calcular:

- presencia de nieve;
- duración de cubierta;
- fecha de establecimiento;
- fecha de fusión;
- persistencia de neveros;
- anomalía respecto a años anteriores.

No existe un espesor mínimo demostrado.

## 3.3. Fecha y ritmo de deshielo

El deshielo es probablemente una de las señales operativas más útiles.

Variables posibles:

- días desde desaparición de la nieve;
- velocidad de fusión;
- alternancia hielo–deshielo;
- superficie libre de nieve;
- temperatura del suelo durante la fusión.

No existe un retardo universal validado entre deshielo y aparición visible.

## 3.4. Humedad del suelo

Debe distinguirse de la lluvia reciente.

Fuentes de humedad:

- fusión nival;
- precipitación;
- reserva antecedente;
- retención del suelo;
- cubierta de musgo y acículas.

La lluvia líquida puede ser secundaria en campañas dominadas por nieve.

## 3.5. Temperatura

Variables recomendadas:

- temperatura mínima del aire;
- temperatura del suelo;
- número de días de deshielo;
- anomalía térmica;
- heladas posteriores a la fusión.

No existe una temperatura óptima universal.

## 3.6. Fenología y altitud

El modelo debe combinar:

- día del año;
- altitud;
- nieve;
- región climática;
- fecha histórica local;
- exposición.

La ventana no debe fijarse simplemente como “marzo”.

## 3.7. Historial de colonias

Variables útiles:

- coordenadas de colonias;
- recurrencia;
- número de carpóforos;
- extensión;
- fechas de aparición;
- años sin producción;
- cambios en el bosque.

El historial local debería tener uno de los pesos más altos del modelo.

## 3.8. Estructura forestal

Incluir cuando sea posible:

- edad;
- densidad;
- cobertura;
- área basimétrica;
- continuidad del rodal;
- tratamientos selvícolas.

No existe una función universal específica.

## 3.9. Presión recolectora

Debe tratarse como factor de observabilidad:

- accesibilidad;
- proximidad a pistas;
- intensidad histórica;
- momento de muestreo;
- permisos o regulación;
- visitas estimadas.

No debe confundirse con menor capacidad biológica de producción.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Espesor mínimo de nieve

No existe un umbral validado.

## 4.2. Duración mínima de cubierta nival

La asociación es clara, pero no se ha cuantificado una duración universal.

## 4.3. Número fijo de días desde el deshielo

No se ha localizado un retardo transferible.

## 4.4. Temperatura óptima

No existe un valor general respaldado por la literatura seleccionada.

## 4.5. Lluvia mínima

La lluvia líquida no puede separarse del aporte nival mediante una regla simple.

## 4.6. Edad forestal óptima

El estudio de clases de edad no justifica un valor universal.

## 4.7. Viento, radiación y humedad relativa

No existen funciones específicas generalizables.

## 4.8. Asociación exclusiva con una sola conífera

La evidencia apoya varias coníferas, con peso regional diferente.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- bosque montano de coníferas;
- *Pinus sylvestris* o *Abies*;
- continuidad del rodal;
- historial local;
- microhábitat con musgo o acículas;
- ausencia de alteración severa.

## 5.2. Componente nival

Incluir:

- presencia de nieve;
- duración;
- fecha de deshielo;
- ritmo de fusión;
- nieve residual;
- anomalía nival.

## 5.3. Componente hídrico

Incluir:

- humedad del suelo;
- equivalente de agua de la nieve cuando exista;
- precipitación reciente;
- capacidad de retención;
- días secos tras el deshielo.

## 5.4. Componente térmico

Incluir:

- temperatura mínima;
- temperatura del suelo;
- días con fusión;
- heladas posteriores;
- anomalía térmica.

## 5.5. Fenología regional

Usar:

- día del año;
- altitud;
- fecha histórica local;
- latitud o región climática;
- estado del deshielo.

## 5.6. Estructura forestal

Incluir:

- edad;
- densidad;
- cobertura;
- área basimétrica;
- gestión reciente.

## 5.7. Observabilidad

Corregir mediante:

- accesibilidad;
- presión recolectora;
- momento del muestreo;
- consumo por fauna;
- esfuerzo de búsqueda.

## 5.8. Evidencia observacional

Cada registro debería incluir:

- fecha y coordenadas;
- abundancia;
- colonia;
- identificación fiable;
- hospedador dominante;
- altitud;
- cobertura de nieve;
- estado del deshielo;
- humedad del suelo;
- cobertura de musgo y acículas;
- estructura forestal;
- presión recolectora;
- esfuerzo de búsqueda.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- bosque de coníferas;
- especie arbórea dominante;
- historial local;
- presencia y duración de nieve;
- fecha de deshielo;
- humedad del suelo;
- día del año;
- altitud;
- temperatura mínima.

## Recomendables

- temperatura del suelo;
- equivalente de agua de la nieve;
- ritmo de fusión;
- heladas posteriores;
- musgo y acículas;
- cobertura forestal;
- edad o densidad del rodal;
- presión recolectora.

## Experimentales

- viento;
- radiación;
- humedad relativa;
- evapotranspiración;
- índice de estabilidad del manto nival;
- temperatura subnival estimada;
- modelos de observabilidad;
- detección remota de neveros residuales.

“Experimental” significa que la literatura específica no permite asignarles todavía un efecto universal sobre la fructificación de *H. marzuolus*.

---

# 7. Conclusiones

1. *Hygrophorus marzuolus* es una especie ectomicorrícica de bosques montanos de coníferas.

2. *Pinus sylvestris* y *Abies* cuentan con la evidencia ecológica más sólida.

3. La especie presenta una fenología invernal y primaveral temprana.

4. La asociación con nieve y deshielo es uno de sus rasgos más característicos.

5. Puede iniciar su desarrollo bajo la nieve y hacerse visible durante la fusión.

6. La fecha de observación no equivale necesariamente al inicio del desarrollo.

7. El estudio de Pinar Grande documentó colonias y producción entre febrero y abril.

8. La distribución espacial es agregada y el historial de colonias debe tener un peso muy alto.

9. La humedad procedente de la nieve puede ser más relevante que la lluvia líquida reciente.

10. No existe un espesor mínimo de nieve, una temperatura óptima ni un retardo post-deshielo universal.

11. La estructura forestal puede influir, pero no existe una edad óptima general.

12. La presión recolectora altera fuertemente la observabilidad y debe corregirse.

13. Rainmapper debería combinar bosque compatible, nieve, deshielo, humedad, temperatura, altitud e historial local.

---

# 8. Bibliografía seleccionada

## 1. Altelarrea Martínez, J. M. y Martínez-Peña, F. (2007)

**Título:** Dinámica de la producción de carpóforos, presión recolectora y aprovechamiento del hongo ectomicorrícico comestible de fructificación invernal *Hygrophorus marzuolus* en Pinar Grande (Soria).  
**Publicación:** Actas del IV Congreso Forestal Español / Boletín Micológico de FAMCAL.  
**Texto completo:** https://secforestales.org/publicaciones/index.php/congresos_forestales/article/download/16362/16205/16354  
**Referencia alternativa:** https://www.researchgate.net/publication/270393260_Dinamica_de_la_produccion_de_carpoforos_presion_recolectora_y_aprovechamiento_del_hongo_ectomicorricico_comestible_Hygrophorus_marzuolus_en_Pinar_Grande_Soria

**Aportación:** principal estudio específico ibérico. Analiza colonias, producción, clases de edad del pinar, recolección, fauna, esporulación y campaña entre febrero y abril.

**Confianza:** alta para dinámica local en *Pinus sylvestris*; no ofrece un modelo meteorológico universal.

## 2. Beug, M. W. y Bessette, A. E. (2009)

**Título:** Snowbank Fungi Revisited.  
**Publicación:** Fungi Magazine.  
**Texto:** https://www.fungimag.com/spring-09-articles/13_Snow.pdf

**Aportación:** incluye *H. marzuolus* entre los hongos nivícolas asociados a coníferas y resume su relación con la fusión de nieve.

**Confianza:** media-alta para ecología nival; publicación de síntesis, no experimento predictivo.

## 3. Bingham, J. (2023)

**Título:** *Hygrophorus marzuolus* new to Britain.  
**Revista:** Field Mycology, 24(2).  
**Consulta:** https://www.researchgate.net/publication/390957855_Hygrophorus_marzuolus_new_to_Britain

**Aportación:** documenta molecularmente el primer registro británico y resume hábitat, fenología y asociación con deshielo y coníferas.

**Confianza:** alta para el registro británico y taxonomía; descriptiva para predicción.

## 4. Čolić, D. et al. (2024)

**Título:** Phytocoenological and ecological typification of the March Mushroom (*Hygrophorus marzuolus*) habitat in Bijambare, Sarajevo Canton.  
**Texto completo:** https://radovi.sfsa.unsa.ba/ojs/index.php/rsf/article/download/584/541/638

**Aportación:** tipifica el hábitat y la vegetación asociada a la especie en un sistema montano balcánico.

**Confianza:** alta para el hábitat estudiado; no ofrece umbrales meteorológicos.

## 5. Karadelev, M. et al.

**Título:** Registros y evaluación de *Hygrophorus marzuolus* en bosques montanos de Macedonia del Norte.  
**Página de conservación:** https://redlist.moepp.gov.mk/march-mushroom/  
**Actas ecológicas relacionadas:** https://mes.org.mk/wp-content/uploads/2018/03/proceedings-of-the-4th-congress-of-ecologists-of-the-republic-of-macedonia-with-international-participation.pdf

**Aportación:** documenta la especie con *Abies borisii-regis*, *Pinus peuce*, *Pinus nigra* y bosques mixtos.

**Confianza:** media-alta para distribución y hospedadores regionales.

## 6. Mohatt, K. R. et al. (2008)

**Título:** Ectomycorrhizal fungi of whitebark pine and other high-elevation conifers.  
**Texto completo:** https://plantsciences.montana.edu/facultyorstaff/faculty/cripps/MohattRPViewDoc.pdf

**Aportación:** registra *H. marzuolus* en comunidades ectomicorrícicas de coníferas de alta elevación y aporta contexto sobre su asociación montana.

**Confianza:** media para el concepto ecológico amplio; cautela por diferencias biogeográficas y taxonómicas norteamericanas.

---

## Nota final sobre la evidencia

La evidencia específica de *H. marzuolus* es suficiente para definir hábitat, fenología y relevancia de la nieve, pero insuficiente para construir una regla meteorológica cuantitativa.

No se han utilizado como hechos demostrados:

- espesores mínimos de nieve;
- días exactos desde el deshielo;
- temperaturas óptimas;
- cotas altitudinales universales;
- cantidades mínimas de precipitación.

La estructura inicial más defendible para Rainmapper es: conífera compatible + colonia conocida + cubierta nival + deshielo + humedad del suelo + temperatura + altitud + corrección por presión recolectora.
