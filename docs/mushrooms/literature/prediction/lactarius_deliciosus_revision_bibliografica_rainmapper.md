# Predicción de floradas de *Lactarius deliciosus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Lactarius deliciosus* (L.) Gray  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que estudia explícitamente *Lactarius deliciosus* o, cuando así se indica, el grupo *Lactarius deliciosus*, y aporta información útil sobre fructificación, clima, humedad del suelo, estructura forestal, micelio, gestión o productividad.  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal.

---

# Resumen ejecutivo

*Lactarius deliciosus* es una de las especies de hongos silvestres comestibles mejor estudiadas en pinares mediterráneos y submediterráneos. Existen series largas de producción, modelos de rendimiento, estudios sobre micelio extrarradical, teledetección, estructura forestal y respuesta a tratamientos selvícolas.

Aun así, la literatura no permite formular una regla universal del tipo “una determinada cantidad de lluvia produce una florada después de un número fijo de días”. Los modelos publicados son dependientes del bosque, la región, el periodo de observación y, en algunos casos, del uso del término “grupo *deliciosus*” en lugar de una identificación estrictamente separada de *L. deliciosus*.

Las conclusiones mejor respaldadas son:

1. **La presencia de pinos es el filtro ecológico principal.** La especie es ectomicorrícica y está estrechamente ligada a *Pinus*. En España se ha estudiado especialmente en *Pinus pinaster* y *Pinus sylvestris*.

2. **La precipitación de final de verano y otoño es uno de los factores climáticos más consistentes.** Una serie de diecisiete años en *Pinus pinaster* encontró que la precipitación de final del verano y comienzo del otoño favorecía tanto la aparición como la producción.

3. **La humedad del suelo aporta información comparable a la precipitación.** En series de 22–24 años, la humedad del suelo estimada por teledetección igualó o se aproximó al poder predictivo de la precipitación.

4. **La temperatura también influye, pero su efecto no es simple.** Un estudio específico del micelio y los carpóforos encontró relaciones positivas con precipitación y humedad relativa, y negativas con temperaturas máximas y mínimas. Otros modelos muestran que temperatura y precipitación actúan conjuntamente.

5. **La productividad del bosque del año anterior puede condicionar la campaña siguiente.** El NDVI del año anterior fue un predictor importante en modelos de largo plazo. Esto sugiere que la campaña depende tanto de la meteorología reciente como del estado previo del hospedador.

6. **La estructura del rodal es importante.** Altura dominante, área basimétrica, edad, volumen de vegetación y cobertura aparecen repetidamente en modelos específicos o de grupo.

7. **La producción puede responder a aclareos forestales.** En un estudio, los aclareos más intensos aumentaron tanto la cantidad de micelio extrarradical como la producción de carpóforos en el otoño inmediatamente posterior.

8. **La biomasa de micelio puede anticipar la producción.** En el estudio de Liu et al., la cantidad de micelio en el suelo se correlacionó con la producción del mismo año y del año siguiente.

9. **Los suelos ácidos favorecieron el rendimiento de *Lactarius* en una serie larga de *Pinus pinaster*.** Este resultado es regional y no debe convertirse en un umbral universal de pH.

10. **La fenología productiva en los pinares estudiados es principalmente otoñal.** En el norte de España, una campaña comercial intensa se concentró durante cuatro a seis semanas entre mediados de octubre y mediados de noviembre.

11. **No existe evidencia suficiente para fijar un umbral universal de lluvia, temperatura, humedad relativa, radiación o viento.** Incluso cuando un estudio publica una cifra concreta, esa cifra debe interpretarse como local.

12. **La incertidumbre taxonómica debe controlarse.** Algunos trabajos modelan *Lactarius group deliciosus*, que puede incluir otros níscalos próximos. Rainmapper debería distinguir entre evidencia estricta de *L. deliciosus* y evidencia de grupo.

## Factores que deberían entrar en una primera versión del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Pinus* compatible | Filtro ecológico principal | Muy alta |
| Precipitación de final de verano y otoño | Señal hídrica principal | Alta |
| Humedad del suelo | Estado hídrico | Alta |
| Temperatura de la estación de fructificación | Modulador climático | Media-alta |
| Día del año | Ventana fenológica | Alta |
| NDVI o productividad previa del bosque | Potencial de campaña | Media-alta |
| Área basimétrica, altura y cobertura | Moduladores estructurales | Alta |
| Micelio extrarradical, si existe | Indicador avanzado | Alta |
| Gestión y aclareos recientes | Modulador de productividad | Media-alta |
| Historial local de observaciones | Calibración principal | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *L. deliciosus* mediante un filtro fuerte de pinares, una señal hídrica de final de verano–otoño, temperatura, estructura forestal, productividad previa del hospedador e historial local. La literatura permite seleccionar estas variables con bastante confianza, pero no justifica copiar umbrales numéricos universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores cuentan con respaldo científico específico suficiente para incorporarlos a un modelo de predicción de fructificaciones de *Lactarius deliciosus*?

Se revisó más bibliografía de la finalmente citada. Se descartaron:

- estudios de otras especies de *Lactarius* sin resultados separados;
- publicaciones de composición química, nutrición o contaminantes;
- páginas divulgativas con cifras meteorológicas no verificables;
- modelos de producción total de hongos sin desglose útil;
- estudios del grupo *deliciosus* cuando no podía saberse si sus conclusiones eran aplicables a *L. deliciosus*, salvo que se indicara expresamente esta limitación;
- referencias económicas sin información ecológica o fenológica;
- trabajos de cultivo in vitro cuando sus resultados no podían trasladarse a fructificación de campo.

Se seleccionaron **ocho referencias principales**, priorizando series largas, modelos específicos, estudios de micelio y trabajos de estructura forestal o teledetección.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Asociación con pinos

*Lactarius deliciosus* es ectomicorrícico y depende de raíces vivas de *Pinus*.

La literatura seleccionada lo estudia principalmente en:

- *Pinus pinaster*;
- *Pinus sylvestris*;
- plantaciones de pinos introducidos;
- pinares mediterráneos y continentales.

El trabajo sobre comercialización en el norte de España documenta que la especie comenzó a aparecer en el área después de sustituir robles nativos por pinos.

Esto no demuestra que cualquier pinar sea igualmente apto. Importan también:

- edad;
- estructura;
- suelo;
- clima;
- continuidad del rodal;
- estado fisiológico del arbolado.

**Conclusión útil:** la presencia de *Pinus* debe actuar como filtro necesario, pero no suficiente.

## 2.2. Precipitación de final de verano y otoño

Taye et al. analizaron diecisiete años de datos en bosques de *Pinus pinaster* del centro de España.

Los resultados principales fueron:

- la precipitación de final de verano y comienzo de otoño favoreció la emergencia;
- esa misma precipitación favoreció la producción;
- los modelos separaron probabilidad de aparición y cantidad producida;
- el clima no fue el único factor, porque también influyeron suelo y estructura del rodal.

Esta es una de las evidencias más sólidas y directamente aplicables a Rainmapper.

**Conclusión útil:** calcular precipitación en ventanas que cubran final de verano y comienzo de otoño, pero adaptar las fechas a la región y altitud.

## 2.3. Humedad del suelo

Olano et al. utilizaron series de 22 y 24 años en pinares de *Pinus pinaster* y *Pinus sylvestris*.

Para el sistema seco, donde *L. deliciosus* era la especie comercial principal:

- la humedad del suelo obtenida por teledetección mostró una capacidad predictiva similar a la precipitación;
- la combinación de humedad, clima y NDVI mejoró los modelos;
- ninguna variable explicó por sí sola toda la variación.

La humedad del suelo responde a:

- lluvia;
- evapotranspiración;
- textura;
- drenaje;
- cobertura;
- humedad antecedente.

**Conclusión útil:** Rainmapper debe conservar precipitación y humedad del suelo como variables distintas, no asumir que una sustituye siempre a la otra.

## 2.4. Temperatura, humedad relativa y radiación

Águeda et al. siguieron la dinámica estacional del micelio y la producción de carpóforos en pinares del centro de España.

Para *L. deliciosus* encontraron:

- biomasa micelial positivamente relacionada con humedad relativa;
- biomasa micelial negativamente relacionada con temperatura media y radiación;
- producción de carpóforos positivamente relacionada con precipitación y humedad relativa;
- producción negativamente relacionada con temperaturas máxima y mínima.

Estos resultados proceden de parcelas y periodos concretos.

No demuestran que:

- temperaturas más bajas sean siempre mejores;
- exista una temperatura crítica;
- la radiación tenga siempre el mismo efecto;
- la humedad relativa pueda sustituir a la humedad del suelo.

**Conclusión útil:** incluir temperatura máxima, mínima, humedad relativa y radiación como variables de calibración, manteniendo interacciones con el estado hídrico.

## 2.5. Dinámica estacional del micelio

En el mismo estudio, la biomasa de micelio de *L. deliciosus* mostró una dinámica estacional clara:

- diferencias significativas entre parcelas;
- diferencias significativas a lo largo del año;
- máximo en diciembre;
- mínimo en febrero;
- segundo máximo menos pronunciado en marzo.

Sin embargo, en ese estudio no se observó una correlación significativa entre biomasa micelial y productividad de las parcelas.

Esto contrasta con el estudio posterior de Liu et al., donde la cantidad de micelio sí se correlacionó con producción actual y futura.

La diferencia puede deberse a:

- diseño;
- momento del muestreo;
- intensidad de muestreo;
- variación espacial;
- tratamientos forestales;
- años concretos.

**Conclusión útil:** el micelio es prometedor, pero su relación con carpóforos no es idéntica en todos los estudios.

## 2.6. Micelio como predictor de cosecha

Liu et al. cuantificaron micelio extrarradical de *L. deliciosus* y lo relacionaron con la producción.

Encontraron:

- alta correlación entre micelio del suelo y producción de carpóforos en el mismo año;
- correlación también con la producción del año siguiente;
- incremento de micelio y carpóforos tras aclareos más intensos;
- posibilidad de utilizar el micelio como herramienta de previsión.

Este resultado es especialmente relevante para Rainmapper, aunque medir micelio requiere muestreo molecular y no es viable como capa general de gran escala.

**Conclusión útil:** cuando existan datos de parcelas experimentales o muestreos de suelo, el micelio puede actuar como indicador avanzado de potencial productivo.

## 2.7. Efecto del aclareo

El estudio de Liu et al. encontró que los tratamientos de aclareo más intensos incrementaron:

- micelio extrarradical;
- producción de carpóforos;
- respuesta en el otoño inmediatamente posterior.

Los posibles mecanismos incluyen cambios en:

- vigor de los árboles restantes;
- disponibilidad de carbono por árbol;
- luz;
- humedad;
- temperatura del suelo;
- competencia radicular.

El estudio no demuestra que cualquier aclareo intenso sea beneficioso en cualquier bosque o a largo plazo.

**Conclusión útil:** registrar intensidad, fecha y tipo de intervención, y calibrar efectos locales.

## 2.8. Estructura forestal

Martínez-Peña et al. desarrollaron modelos de rendimiento del grupo *Lactarius deliciosus* en pinares de *Pinus sylvestris* con quince años de datos.

La producción del grupo estuvo influida por:

- altura dominante;
- área basimétrica;
- lluvia;
- temperatura.

El uso del término “grupo *deliciosus*” limita la atribución estricta a *L. deliciosus*, pero los resultados son útiles en pinares donde esta especie constituye una parte importante del grupo comercial.

Martínez-Rodrigo et al. incorporaron:

- volumen de vegetación;
- cobertura;
- NDVI;
- precipitación otoñal;
- estructura derivada de LiDAR terrestre y Landsat.

**Conclusión útil:** la estructura del bosque debe entrar en el modelo como conjunto de variables continuas, no como una simple clasificación de presencia de pinos.

## 2.9. Productividad primaria previa

Olano et al. encontraron que el NDVI del año anterior se correlacionaba con la cosecha posterior.

Los autores propusieron un proceso en dos etapas:

1. la productividad primaria del hospedador favorece la acumulación de recursos;
2. el clima de la estación de fructificación determina si esos recursos se convierten en carpóforos.

Esta interpretación es una hipótesis mecanística razonable derivada del modelo, no una medición directa del flujo de carbono hacia *L. deliciosus*.

**Conclusión útil:** usar NDVI o EVI del año anterior como modulador del potencial de campaña, no como desencadenante inmediato.

## 2.10. Suelo

Taye et al. encontraron:

- efecto positivo de la acidez del suelo sobre el rendimiento de *Lactarius*;
- efecto negativo de suelos arenosos sobre la producción total;
- efecto negativo de la edad del rodal sobre parte de la producción modelada.

Debe distinguirse entre:

- resultado de *Lactarius* a nivel de género o grupo;
- resultado exclusivo de *L. deliciosus*;
- condiciones particulares de los Arenosoles y Regosoles de Soria.

**Conclusión útil:** incluir pH, textura y capacidad de retención como moduladores, sin convertirlos en filtros absolutos.

## 2.11. Fenología y duración de campaña

El estudio etnoeconómico del norte de España documentó:

- recolección comercial intensa;
- cuatro a seis semanas de campaña;
- concentración entre mediados de octubre y mediados de noviembre.

Esta fenología corresponde a un territorio y periodo concretos.

En otras regiones:

- puede comenzar antes;
- puede prolongarse después;
- cambia con altitud;
- depende de las primeras lluvias efectivas y del régimen térmico.

**Conclusión útil:** la fecha histórica local es útil, pero debe adaptarse con variables climáticas.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador

El filtro ecológico principal debe ser *Pinus*.

Rainmapper debería distinguir:

- *Pinus pinaster*;
- *Pinus sylvestris*;
- otros pinos con observaciones confirmadas;
- plantaciones jóvenes;
- pinares maduros;
- masas mixtas.

## 3.2. Precipitación

Variables recomendadas:

- precipitación de final de verano;
- precipitación de comienzo de otoño;
- acumulado otoñal;
- número de días lluviosos;
- duración de periodos secos;
- anomalía respecto a climatología.

No existe una cantidad universal mínima.

## 3.3. Humedad del suelo

Debe estimarse mediante:

- teledetección;
- balance hídrico;
- precipitación;
- textura;
- evapotranspiración;
- cobertura.

Puede tener un poder predictivo similar al de la precipitación, pero no siempre la reemplaza.

## 3.4. Temperatura

Incluir:

- temperatura mínima;
- temperatura máxima;
- temperatura media;
- anomalías;
- interacción con humedad;
- temperatura del suelo cuando exista.

No existe un óptimo universal.

## 3.5. Humedad relativa y radiación

Cuentan con evidencia específica en el estudio de dinámica micelial y carpóforos.

Deben tratarse como:

- variables auxiliares;
- indicadores de secado;
- posibles predictores dependientes del lugar.

No se debe fijar un umbral general.

## 3.6. Productividad del hospedador

Variables útiles:

- NDVI/EVI del año anterior;
- vigor actual;
- estrés estival;
- pérdida de copa;
- crecimiento del rodal.

Su función principal sería modular la intensidad potencial, no el inicio exacto.

## 3.7. Estructura forestal

Incluir:

- área basimétrica;
- altura dominante;
- cobertura;
- volumen de vegetación;
- edad;
- densidad;
- tratamientos recientes.

No existe una estructura óptima universal.

## 3.8. Micelio

Cuando exista muestreo:

- concentración de micelio;
- fecha de muestreo;
- distribución espacial;
- respuesta a gestión.

Debe considerarse una variable de alta calidad, pero costosa y local.

## 3.9. Fenología

Combinar:

- día del año;
- altitud;
- región;
- fecha histórica local;
- lluvia efectiva;
- temperatura;
- humedad del suelo.

---

# 4. Factores que no están demostrados de forma universal

## 4.1. Umbral de precipitación

Aunque algunos estudios locales publican cifras concretas, no existe una cantidad universal transferible.

## 4.2. Número fijo de días después de la lluvia

No se ha demostrado un retardo general.

## 4.3. Temperatura óptima

Los efectos cambian según estudio, bosque y escala temporal.

## 4.4. Efecto siempre positivo del aclareo

El resultado de Liu et al. fue positivo en el contexto estudiado, pero no debe universalizarse.

## 4.5. Relación universal entre micelio y carpóforos

Un estudio encontró correlación fuerte y otro no encontró relación significativa.

## 4.6. pH óptimo universal

La acidez favoreció el rendimiento en una serie concreta, pero no define un intervalo global.

## 4.7. Viento

No se localizaron funciones específicas robustas y generalizables.

## 4.8. Radiación y humedad relativa como reglas independientes

Existe evidencia específica, pero no suficiente para fijar umbrales universales.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro ecológico

Combinar:

- presencia de *Pinus*;
- especie de pino;
- continuidad del rodal;
- historial local;
- suelo compatible;
- ausencia de perturbación severa.

## 5.2. Componente hídrico

Incluir por separado:

- precipitación de final de verano;
- precipitación otoñal;
- humedad del suelo;
- duración del periodo seco;
- balance hídrico;
- humedad relativa.

## 5.3. Componente térmico

Incluir:

- temperatura máxima;
- mínima;
- media;
- anomalías;
- temperatura del suelo;
- interacción con humedad.

## 5.4. Componente de productividad previa

Incluir:

- NDVI/EVI del año anterior;
- vigor del dosel;
- estrés de la vegetación;
- crecimiento del bosque.

## 5.5. Estructura forestal

Incluir:

- área basimétrica;
- altura dominante;
- cobertura;
- volumen;
- edad;
- densidad;
- aclareos recientes.

## 5.6. Micelio

Cuando exista:

- concentración;
- fecha;
- localización;
- tendencia;
- respuesta a tratamientos.

## 5.7. Fenología regional

Usar:

- día del año;
- altitud;
- fecha histórica;
- región climática;
- comienzo observado de campaña.

## 5.8. Evidencia observacional

Cada registro debería incluir:

- identificación fiable;
- fecha y coordenadas;
- abundancia o biomasa;
- especie de pino;
- estructura del rodal;
- suelo;
- meteorología previa;
- gestión reciente;
- esfuerzo de búsqueda;
- presión recolectora.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- especie de *Pinus*;
- tipo de pinar;
- historial local;
- precipitación de final de verano y otoño;
- humedad del suelo;
- temperatura mínima y máxima;
- día del año;
- altitud;
- área basimétrica o indicador estructural.

## Recomendables

- NDVI/EVI del año anterior;
- humedad relativa;
- radiación;
- altura dominante;
- cobertura;
- edad;
- textura;
- pH;
- tratamientos selvícolas recientes.

## Experimentales

- viento;
- déficit de presión de vapor;
- temperatura del suelo estimada;
- concentración de micelio;
- crecimiento anual del arbolado;
- modelos de teledetección de estructura;
- predicción separada de presencia y cantidad.

“Experimental” significa que la variable es prometedora o cuenta con evidencia local, pero no dispone de una relación universal validada para *L. deliciosus*.

---

# 7. Conclusiones

1. *Lactarius deliciosus* es una especie ectomicorrícica estrechamente ligada a pinos.

2. La precipitación de final de verano y comienzo de otoño es uno de los factores climáticos mejor respaldados.

3. La humedad del suelo tiene una capacidad predictiva comparable a la precipitación en series largas.

4. Temperatura, humedad relativa y radiación pueden influir en micelio y carpóforos, pero sus efectos son dependientes del contexto.

5. El NDVI del año anterior aporta información sobre el potencial de la campaña siguiente.

6. La estructura forestal —área basimétrica, altura, cobertura y volumen— afecta a la productividad.

7. El micelio extrarradical puede anticipar la producción, aunque los estudios no son completamente consistentes.

8. Los aclareos intensos aumentaron micelio y carpóforos en un estudio específico, pero no deben considerarse universalmente beneficiosos.

9. La acidez del suelo favoreció el rendimiento de *Lactarius* en una serie de *Pinus pinaster*, sin justificar un pH óptimo universal.

10. La campaña es principalmente otoñal, pero las fechas varían regionalmente.

11. No existe una lluvia mínima, una temperatura óptima ni un número fijo de días post-lluvia universal.

12. Rainmapper debería combinar hospedador, agua, temperatura, estructura forestal, productividad previa e historial local.

---

# 8. Bibliografía seleccionada

## 1. Taye, Z. M. et al. (2016)

**Título:** Meteorological conditions and site characteristics driving edible mushroom production in *Pinus pinaster* forests of Central Spain.  
**Revista:** Fungal Ecology, 23, 30–41.  
**DOI / página editorial:** https://doi.org/10.1016/j.funeco.2016.05.008  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S1754504816300514

**Aportación:** serie de diecisiete años. Demuestra el efecto positivo de la precipitación de final de verano y comienzo de otoño sobre aparición y producción, y analiza suelo y estructura del rodal.

**Confianza:** alta para los pinares y periodo estudiados.

## 2. Olano, J. M. et al. (2020)

**Título:** Primary productivity and climate control mushroom yields in Mediterranean pine forests.  
**Revista:** Agricultural and Forest Meteorology, 288–289, 108015.  
**DOI:** https://doi.org/10.1016/j.agrformet.2020.108015  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0168192320301179

**Aportación:** series de 22 y 24 años. Modela específicamente *L. deliciosus* en el bosque seco con precipitación, temperatura, humedad del suelo y NDVI.

**Confianza:** alta para variabilidad interanual y combinación de clima con productividad previa.

## 3. Águeda, B. et al. (2013)

**Título:** Seasonal dynamics of *Boletus edulis* and *Lactarius deliciosus* extraradical mycelium in pine forests of central Spain.  
**Revista:** Mycorrhiza, 23, 391–402.  
**Consulta:** https://www.researchgate.net/publication/235422511_Seasonal_dynamics_of_Boletus_edulis_and_Lactarius_deliciosus_extraradical_mycelium_in_pine_forests_of_central_Spain

**Aportación:** cuantifica micelio y relaciona su dinámica y la producción de carpóforos con precipitación, humedad relativa, temperaturas y radiación.

**Confianza:** alta para dinámica estacional local; relación micelio–producción no significativa en ese estudio.

## 4. Liu, B. et al. (2016)

**Título:** *Lactarius deliciosus* Fr. soil extraradical mycelium correlates with stand fruitbody productivity and is increased by forest thinning.  
**Revista:** Forest Ecology and Management, 380, 196–201.  
**DOI:** https://doi.org/10.1016/j.foreco.2016.08.053  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0378112716304911

**Aportación:** relaciona micelio con producción actual y del año siguiente y demuestra un incremento tras aclareos intensos.

**Confianza:** alta para el sistema estudiado; no universaliza la respuesta al aclareo.

## 5. Martínez-Peña, F. et al. (2012)

**Título:** Yield models for ectomycorrhizal mushrooms in *Pinus sylvestris* forests with special focus on *Boletus edulis* and *Lactarius* group *deliciosus*.  
**Revista:** Forest Ecology and Management, 282, 63–69.  
**DOI:** https://doi.org/10.1016/j.foreco.2012.06.034  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0378112712003635

**Aportación:** serie de quince años. Relaciona la producción del grupo *deliciosus* con lluvia, temperatura, altura dominante y área basimétrica.

**Confianza:** alta para el grupo en *Pinus sylvestris*; cautela taxonómica para atribución exclusiva a *L. deliciosus*.

## 6. Martínez-Rodrigo, R. et al. (2022)

**Título:** Stand Structural Characteristics Derived from Combined TLS and Landsat Data Support Predictions of Mushroom Yields in Mediterranean Forest.  
**Revista:** Remote Sensing, 14, 5025.  
**DOI:** https://doi.org/10.3390/rs14195025  
**Texto completo:** https://www.mdpi.com/2072-4292/14/19/5025

**Aportación:** integra precipitación otoñal, volumen de vegetación, cobertura y NDVI para modelar la producción de *L. deliciosus*.

**Confianza:** alta para utilidad de teledetección y estructura en el área estudiada; las cifras concretas son locales.

## 7. de Román, M. y Boa, E. (2006)

**Título:** The marketing of *Lactarius deliciosus* in Northern Spain.  
**Revista:** Economic Botany, 60, 284–290.  
**DOI / página editorial:** https://link.springer.com/article/10.1663/0013-0001%282006%2960%5B284%3ATMOLDI%5D2.0.CO%3B2

**Aportación:** documenta fenología comercial de cuatro a seis semanas entre mediados de octubre y mediados de noviembre y la aparición asociada a la introducción de pinos.

**Confianza:** media-alta para fenología y contexto local; no es un modelo climático.

## 8. Herrero, C. et al. (2019)

**Título:** Predicting Mushroom Productivity from Long-Term Field-Data Series in Mediterranean *Pinus pinaster* Forests in the Context of Climate Change.  
**Revista:** Forests, 10, 206.  
**DOI:** https://doi.org/10.3390/f10030206  
**Texto completo:** https://www.mdpi.com/1999-4907/10/3/206

**Aportación:** aporta contexto de largo plazo sobre producción, estructura forestal y cambio climático en pinares donde *L. deliciosus* es una especie económica principal.

**Confianza:** media para la especie concreta; parte de los modelos son agregados.

---

## Nota final sobre la evidencia

La literatura de *L. deliciosus* es relativamente abundante, pero debe separarse cuidadosamente entre:

- estudios de la especie;
- estudios del grupo *deliciosus*;
- modelos de *Lactarius* a nivel de género;
- modelos de producción total de hongos.

La evidencia permite afirmar con confianza que el agua disponible, la temperatura, la estructura del pinar, la productividad previa del hospedador y la biomasa micelial son relevantes.

No permite afirmar un umbral meteorológico universal ni una receta fija de aparición. Los parámetros numéricos deben calibrarse por región, tipo de pinar y calidad taxonómica de las observaciones.
