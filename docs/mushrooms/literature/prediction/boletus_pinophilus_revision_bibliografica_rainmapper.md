# Predicción de floradas de *Boletus pinophilus*
## Revisión bibliográfica breve y conclusiones para Rainmapper

**Especie:** *Boletus pinophilus* Pilát & Dermek  
**Proyecto:** Rainmapper  
**Fecha de revisión:** 11 de julio de 2026  
**Alcance:** literatura científica que menciona y estudia explícitamente *Boletus pinophilus*  
**Extensión prevista:** menos de 10 páginas en formato de lectura normal

---

# Resumen ejecutivo

La literatura científica dedicada específicamente a predecir la fructificación de *Boletus pinophilus* es limitada. No se ha localizado un modelo meteorológico validado para esta especie que permita establecer una cantidad mínima de lluvia, una temperatura óptima o un número fijo de días entre un episodio de precipitación y la aparición de cuerpos fructíferos. Por tanto, esos valores no deben incorporarse a Rainmapper como si fueran parámetros demostrados.

Los trabajos que estudian o registran explícitamente *B. pinophilus* permiten, sin embargo, extraer varias conclusiones útiles y razonablemente consistentes:

1. **La asociación con pinos es el factor ecológico más sólido.** Los estudios filogenéticos y ecológicos europeos señalan que, dentro de la sección *Boletus*, *B. pinophilus* presenta una asociación relativamente estrecha con *Pinus*. También puede aparecer con *Picea*, *Abies*, *Castanea* y otras frondosas, pero los pinares deben constituir el hábitat prioritario del modelo.

2. **Es una especie de bosques consolidados, no simplemente de lugares donde hay pinos.** La presencia y producción de cuerpos fructíferos dependen de la continuidad del hospedador, del suelo, de la estructura del bosque y de la conservación de la comunidad ectomicorrícica.

3. **Su fenología incluye verano y otoño.** Los inventarios en pinares de montaña y pinares boreales europeos registran la especie durante el verano tardío y el otoño. La época exacta cambia con latitud, altitud y clima local.

4. **La meteorología reciente influye en las comunidades donde fructifica, pero no se ha aislado una respuesta cuantitativa exclusiva de la especie.** En rodales de *Pinus uncinata*, las condiciones meteorológicas explicaron variaciones en productividad y riqueza fúngica, con mayor productividad ectomicorrícica hacia el final del verano. *B. pinophilus* formó parte del inventario, pero no fue modelado por separado.

5. **La alteración intensa del bosque puede tener efectos prolongados.** Un estudio de sucesión posterior a grandes incendios registró *B. pinophilus* en bosque no quemado y observó que su producción no se había recuperado tras dos décadas en las zonas afectadas. Esto refuerza el papel del hábitat maduro y de la continuidad ecológica.

6. **La presencia del micelio no equivale a fructificación visible.** En castañares se observó una correspondencia limitada entre los cuerpos fructíferos de los porcini y la detección de su micelio bajo el suelo. La fructificación depende de estímulos adicionales que no están completamente identificados.

## Factores que deberían entrar en una primera versión sencilla del modelo

| Factor | Papel recomendado | Confianza |
|---|---|---|
| Presencia de *Pinus* compatible | Filtro ecológico principal | Alta |
| Continuidad y estado del bosque | Filtro de aptitud | Alta |
| Temperatura reciente | Modulador fenológico y altitudinal | Media |
| Precipitación reciente | Señal de recarga hídrica | Media |
| Humedad o balance hídrico del suelo | Representación del agua disponible | Media |
| Época del año | Ventana flexible de verano–otoño | Media-alta |
| Altitud y exposición | Modificadores del microclima | Media |
| Historial local de observaciones | Fuente principal de calibración futura | Muy alta |

**Conclusión práctica:** Rainmapper debería modelar *B. pinophilus* mediante un filtro de pinares adecuados y relativamente estables, combinado con una señal hídrica, una adecuación térmica regional y una ventana fenológica flexible. La literatura específica permite decidir qué grupos de factores utilizar, pero no permite asignar umbrales numéricos universales.

---

# 1. Objetivo y criterio de selección

El objetivo de esta revisión es responder a una pregunta concreta:

> ¿Qué factores pueden incorporarse con una confianza razonable a un modelo de predicción de floradas de *Boletus pinophilus*, utilizando únicamente trabajos científicos que mencionen y estudien explícitamente esta especie?

Se descartaron como fundamento principal:

- trabajos dedicados exclusivamente a *Boletus edulis*;
- modelos del complejo *B. edulis* sin desglose por especie;
- estudios generales de hongos ectomicorrícicos;
- páginas divulgativas sin metodología publicada;
- cifras sobre lluvia, temperatura o días hasta fructificación sin evidencia científica específica;
- trabajos de química, contaminación o composición alimentaria sin utilidad predictiva.

Se conservaron publicaciones donde *B. pinophilus* aparece identificado explícitamente y que aportan información sobre:

- hospedadores;
- hábitat;
- fenología;
- productividad;
- estructura forestal;
- incendios y alteración;
- presencia del micelio;
- relación general con condiciones meteorológicas en comunidades donde está presente.

La revisión final utiliza **ocho publicaciones principales**. La mayoría no ofrece un modelo meteorológico individual de la especie, lo cual constituye una limitación científica que debe reconocerse.

---

# 2. Qué evidencia específica existe realmente

## 2.1. Asociación preferente con *Pinus*

Beugelsdijk et al. estudiaron filogenéticamente la sección *Boletus* en Europa. Además de confirmar la separación de las especies europeas, señalaron que *B. pinophilus* parecía ser la especie de la sección con una asociación más estrecha con *Pinus*, aunque también se encontraba en rodales puros de *Picea* o *Abies*.

Esta es una evidencia importante porque permite diferenciar su perfil ecológico del de otros porcini europeos. No significa que la especie solo pueda existir con pinos, pero sí que la presencia de *Pinus* debe recibir el peso principal en el filtro de hábitat.

**Conclusión útil:** para Rainmapper, los pinares deben constituir el hábitat prioritario. Las asociaciones con otras coníferas o frondosas deben mantenerse como posibilidades secundarias, no excluirse.

## 2.2. Presencia en pinares de montaña

Ponce et al. estudiaron durante varios años la productividad y diversidad de cuerpos fructíferos en rodales de *Pinus uncinata* del límite superior del bosque. *B. pinophilus* apareció explícitamente en la comunidad analizada.

El estudio concluyó que las condiciones meteorológicas influyeron en la productividad y riqueza de la comunidad fúngica. La productividad ectomicorrícica fue mayor hacia el final del verano, en relación con las condiciones meteorológicas del área.

El trabajo no publica una respuesta separada de *B. pinophilus*. Por tanto, no permite afirmar que una variable meteorológica concreta tuviera sobre esta especie el mismo efecto calculado para el conjunto de hongos ectomicorrícicos.

**Conclusión útil:** la meteorología y la posición dentro de la estación son factores relevantes en pinares de montaña donde aparece la especie, pero sus pesos específicos deben aprenderse con observaciones.

## 2.3. Fenología de verano tardío y otoño

Grzesiak et al. estudiaron una comunidad de macrohongos en un pinar liquénico de *Pinus sylvestris* en Polonia. Registraron expresamente *B. pinophilus* bajo pinos durante agosto y septiembre.

Los trabajos en rodales de *Pinus uncinata* también sitúan el máximo de productividad ectomicorrícica hacia el final del verano. En el norte de Europa existen registros de cosecha durante agosto.

Estas observaciones proceden de regiones frías o de montaña. No deben convertirse en una ventana fija para toda la península ibérica, pero respaldan una fenología centrada en verano tardío y otoño, con posible desplazamiento por altitud y latitud.

**Conclusión útil:** el día del año debe utilizarse como modulador regional, no como regla rígida. La predicción debe permitir campañas más tempranas o tardías según clima y altitud.

## 2.4. Asociación con castaño y complejidad subterránea

Peintner et al. analizaron comunidades fúngicas del suelo en un bosque de *Castanea sativa* que producía grandes cantidades de porcini. Tomaron muestras directamente bajo cuerpos fructíferos de *B. edulis*, *B. aestivalis*, *B. aereus* y *B. pinophilus*.

La correspondencia entre los cuerpos fructíferos observados y la detección subterránea de su micelio fue reducida. El resultado indica que la presencia del hongo en el suelo y la producción visible de setas no son procesos equivalentes.

**Conclusión útil:** una zona puede contener el hongo y no producir cuerpos fructíferos durante una campaña concreta. Rainmapper debe predecir fructificación visible, no existencia del micelio.

## 2.5. Sensibilidad a incendios intensos

Turiel-Santos et al. estudiaron la recuperación de comunidades fúngicas después de grandes incendios en pinares. *B. pinophilus* se recolectó en el bosque no quemado y su producción no se había recuperado después de dos décadas en las etapas de sucesión estudiadas.

El artículo no demuestra que la especie necesite una edad concreta del bosque ni permite generalizar el mismo tiempo de recuperación a todas las regiones. Sí muestra que una perturbación intensa puede eliminar durante largos periodos la capacidad de fructificación observable.

**Conclusión útil:** grandes incendios recientes, pérdida del arbolado y fases tempranas de regeneración deben penalizar fuertemente la aptitud.

## 2.6. Efecto diferente del fuego prescrito

Cuberos et al. analizaron el efecto a corto plazo de quemas prescritas en pinares de *Pinus pinaster*. Detectaron especies comestibles, entre ellas *B. pinophilus*, después del tratamiento y no encontraron cambios significativos generales en diversidad o composición fúngica un año después.

El resultado no contradice el efecto negativo de los grandes incendios. Una quema prescrita de baja intensidad y un incendio severo son perturbaciones muy distintas.

**Conclusión útil:** Rainmapper no debería tratar todas las áreas quemadas de la misma forma. La severidad, la pérdida de arbolado y el tiempo transcurrido son esenciales.

## 2.7. Irregularidad y baja frecuencia local

En un estudio de un pinar de *Pinus sylvestris* de cincuenta años en Lituania, *B. pinophilus* figuró entre las especies más raras del inventario, con muy pocos cuerpos fructíferos y presencia en pocas parcelas.

Esto no implica que sea universalmente rara, pero demuestra que incluso un pinar aparentemente compatible puede producirla de forma escasa o irregular.

**Conclusión útil:** la presencia de pinos es necesaria como señal de hábitat, pero no suficiente para asegurar una florada.

---

# 3. Factores predictivos defendibles

## 3.1. Hospedador y tipo de bosque

Es el factor mejor respaldado.

La evidencia europea sitúa a *B. pinophilus* principalmente con:

- *Pinus sylvestris*;
- *Pinus uncinata*;
- otros *Pinus*;
- de forma secundaria, *Picea* y *Abies*;
- también *Castanea sativa* y algunas frondosas en determinadas localidades.

Para Rainmapper se recomienda una jerarquía de aptitud:

1. pinares con observaciones regionales confirmadas;
2. otros pinares ecológicamente compatibles;
3. bosques de otras coníferas documentadas;
4. castañares u otras frondosas con evidencia local;
5. hábitats sin hospedadores conocidos, con aptitud muy baja.

No deben asignarse pesos numéricos desde esta revisión.

## 3.2. Continuidad y estado del bosque

Los efectos prolongados de grandes incendios y la baja frecuencia observada en algunos pinares indican que no basta con detectar cobertura de *Pinus*.

Son relevantes:

- continuidad del arbolado;
- supervivencia de raíces hospedadoras;
- antigüedad desde una alteración severa;
- estructura del suelo;
- mantenimiento de la comunidad ectomicorrícica;
- cobertura y microclima.

La edad exacta óptima del pinar no está demostrada específicamente para la especie.

## 3.3. Agua disponible

Ningún trabajo seleccionado proporciona un umbral de lluvia específico para *B. pinophilus*. Sin embargo, los estudios de productividad en comunidades de pinares muestran que la variabilidad meteorológica influye en la fructificación.

Rainmapper debería diferenciar:

- precipitación registrada;
- infiltración efectiva;
- humedad antecedente;
- conservación del agua;
- secado posterior.

La lluvia bruta es una entrada. El factor biológicamente relevante es el agua que permanece accesible en el suelo.

## 3.4. Temperatura

La temperatura aparece como parte de las condiciones que ordenan la fenología y productividad de las comunidades de pinares donde está presente la especie.

Su papel debe entenderse de forma regional:

- en alta montaña, limita la duración de la campaña;
- a menor altitud, puede acelerar la pérdida de humedad;
- una misma temperatura atmosférica produce microclimas distintos según orientación y cobertura.

No existe evidencia específica suficiente para definir una temperatura óptima o límites universales.

## 3.5. Fenología regional

La evidencia seleccionada respalda fructificación de verano tardío y otoño. Sin embargo, la amplitud geográfica de la especie hace improbable una ventana idéntica para todos los territorios.

El modelo debería incluir:

- día del año;
- altitud;
- latitud o región climática;
- anomalía térmica de la campaña;
- primeras observaciones locales del año.

## 3.6. Altitud, orientación y microclima

La presencia en *Pinus uncinata* de alta montaña y en *Pinus sylvestris* de áreas boreales demuestra que la altitud no debe interpretarse de forma absoluta. Actúa como sustituto parcial del clima.

La orientación y cobertura deberían modular:

- temperatura del suelo;
- radiación;
- velocidad de desecación;
- duración de la nieve;
- inicio de la estación vegetativa.

La literatura específica no ofrece coeficientes para estas relaciones.

---

# 4. Factores que no están demostrados específicamente

## 4.1. Cantidad mínima de lluvia

No se ha localizado una cantidad de precipitación validada para activar una florada de *B. pinophilus*.

Cualquier cifra concreta deberá proceder de observaciones locales, no de esta revisión.

## 4.2. Número de días hasta la aparición

No existe un retardo universal publicado entre lluvia y emergencia de cuerpos fructíferos para la especie.

Deben probarse distintas ventanas temporales durante la calibración.

## 4.3. Viento, humedad relativa y radiación

Son variables físicamente relacionadas con el secado, pero no se han encontrado modelos específicos de *B. pinophilus* que cuantifiquen sus efectos.

Pueden utilizarse dentro de un índice hídrico o microclimático y evaluarse posteriormente.

## 4.4. pH y litología

La especie aparece frecuentemente en suelos forestales de coníferas, pero la literatura seleccionada no justifica un intervalo universal de pH ni una litología obligatoria.

La información edáfica debe actuar como modulador flexible.

## 4.5. Edad óptima del bosque

Los estudios apoyan la importancia de la continuidad y de la ausencia de perturbación severa, pero no permiten asignar una edad óptima específica.

---

# 5. Modelo mínimo recomendado para Rainmapper

## 5.1. Filtro de hábitat

Priorizar:

- *Pinus* compatible;
- masa forestal continua;
- suelo forestal no gravemente alterado;
- ausencia de incendio severo reciente;
- historial regional de presencia.

## 5.2. Estado hídrico

Combinar:

- precipitación reciente;
- humedad antecedente;
- retención del suelo;
- pendiente;
- cobertura;
- pérdidas posteriores.

El resultado debería ser un índice relativo, no una regla basada en milímetros.

## 5.3. Adecuación térmica regional

Usar una función flexible que dependa de:

- temperatura reciente;
- altitud;
- región climática;
- estación;
- cobertura forestal.

Sus parámetros deberán calibrarse con observaciones.

## 5.4. Ventana fenológica

Partir de una ventana amplia de verano–otoño y ajustarla por región, altitud y datos de campo.

No utilizar fechas fijas universales.

## 5.5. Estado y perturbación del bosque

Incluir al menos:

- severidad del último incendio;
- años desde la perturbación;
- continuidad del dosel;
- recuperación del hospedador.

## 5.6. Evidencia observacional

Registrar:

- especie identificada con confianza;
- fecha y coordenadas;
- número o clase de abundancia;
- hospedador dominante;
- altitud y orientación;
- cobertura;
- señales de incendio o gestión;
- esfuerzo de búsqueda;
- meteorología previa.

---

# 6. Variables recomendadas por nivel de prioridad

## Imprescindibles

- distribución de *Pinus* por especie;
- tipo y continuidad del bosque;
- precipitación reciente;
- humedad o balance hídrico;
- temperatura reciente;
- día del año;
- altitud;
- historial local de observaciones;
- incendios severos y tiempo desde la perturbación.

## Recomendables

- orientación;
- pendiente;
- cobertura de copa;
- tipo de suelo;
- retención hídrica estimada;
- especie de pino dominante;
- anomalías térmicas y pluviométricas locales.

## Experimentales

- viento;
- humedad relativa;
- radiación;
- evapotranspiración;
- déficit de presión de vapor;
- índices de vigor del arbolado;
- intensidad de gestión forestal;
- edad estimada del rodal.

“Experimental” significa que la literatura específica revisada no permite confirmar su peso para *B. pinophilus*, no que carezcan de interés.

---

# 7. Conclusiones

1. No existe un modelo meteorológico específico y validado para predecir las floradas de *Boletus pinophilus*.

2. La asociación preferente con *Pinus* es la evidencia ecológica más sólida y debe definir el filtro principal de hábitat.

3. La especie también puede aparecer con *Picea*, *Abies*, *Castanea* y otras frondosas, por lo que el filtro no debe ser absolutamente excluyente.

4. La fenología observada se concentra principalmente entre verano tardío y otoño, con desplazamientos regionales y altitudinales.

5. La meteorología influye en las comunidades fúngicas de los pinares donde aparece, pero no se conocen pesos ni umbrales exclusivos de la especie.

6. Los grandes incendios pueden reducir su capacidad de fructificación durante periodos prolongados.

7. Las quemas prescritas de baja intensidad no deben equipararse automáticamente a incendios severos.

8. La detección del micelio y la aparición de cuerpos fructíferos no guardan una correspondencia simple.

9. La presencia de un pinar adecuado no garantiza una florada frecuente o abundante.

10. Los valores numéricos del modelo deben aprenderse de observaciones de Rainmapper y conservar trazabilidad respecto a su origen.

Rainmapper puede identificar situaciones ecológica y meteorológicamente favorables para *B. pinophilus*, pero la literatura específica no permite transformar esas condiciones en una predicción determinista.

---

# 8. Bibliografía seleccionada

## 1. Beugelsdijk, D. C. M. et al. (2008)

**Título:** A phylogenetic study of *Boletus* section *Boletus* in Europe.  
**Revista:** Persoonia, 20, 1–7.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC2865352/  
**Repositorio:** https://repository.naturalis.nl/document/570055

**Aportación:** confirma el tratamiento de *B. pinophilus* como especie europea diferenciada y señala que presenta una asociación relativamente estrecha con *Pinus*, aunque también aparece en rodales de *Picea* y *Abies*.

**Confianza:** alta para identidad taxonómica y asociación principal con hospedadores.

## 2. Ponce, Á., Alday, J. G., Bonet, J. A. y de Miguel, S. (2023)

**Título:** Fungal sporocarp productivity and diversity shaped by weather conditions in *Pinus uncinata* stands.  
**Revista:** Forest Ecology and Management, 545, 121291.  
**Enlace:** https://www.sciencedirect.com/science/article/pii/S0378112723004905

**Aportación:** incluye explícitamente *B. pinophilus* en rodales de pino negro de montaña y demuestra la importancia de las condiciones meteorológicas en la productividad y diversidad de la comunidad, especialmente hacia el final del verano.

**Confianza:** media para contexto meteorológico y fenológico; insuficiente para parámetros exclusivos de la especie.

## 3. Peintner, U. et al. (2007)

**Título:** Soil fungal communities in a *Castanea sativa* forest producing large quantities of *Boletus edulis* sensu lato: where is the mycelium of porcini?  
**Revista:** Environmental Microbiology, 9(4), 880–889.  
**PubMed:** https://pubmed.ncbi.nlm.nih.gov/17359260/  
**DOI:** https://doi.org/10.1111/j.1462-2920.2006.01208.x

**Aportación:** estudia expresamente muestras tomadas bajo basidiomas de *B. pinophilus* en castañar y muestra la débil correspondencia entre fructificación visible y detección del micelio.

**Confianza:** alta para asociación con castaño y para la complejidad de la relación micelio–fructificación.

## 4. Turiel-Santos, S. et al. (2024)

**Título:** Large wildfires alter the potential capacity of fire-prone ecosystems to provide edible mushroom provisioning ecosystem services.  
**Revista:** Fungal Ecology.  
**Enlace:** https://www.sciencedirect.com/science/article/pii/S2666719324001651

**Aportación:** registra *B. pinophilus* en bosque no quemado y concluye que su producción no se había recuperado tras dos décadas en las etapas postincendio estudiadas.

**Confianza:** alta para sensibilidad local a grandes incendios; no permite fijar un periodo universal de recuperación.

## 5. Cuberos, N. et al. (2024)

**Título:** Impact of prescribed fire on fungal communities in Scots pine forests.  
**Revista:** Fungal Ecology.  
**Enlace:** https://www.sciencedirect.com/science/article/pii/S2666719324002309

**Aportación:** detecta *B. pinophilus* entre las especies comestibles presentes después de quemas prescritas y muestra que una perturbación de baja intensidad no equivale a un gran incendio.

**Confianza:** media para respuesta a fuego prescrito; seguimiento de corto plazo.

## 6. Grzesiak, B. et al. (2024)

**Título:** Macrofungal sporocarp community in the lichen Scots pine forest in Central Poland.  
**Texto completo:** https://pmc.ncbi.nlm.nih.gov/articles/PMC11426384/

**Aportación:** registra *B. pinophilus* bajo pinos durante agosto y septiembre en un pinar liquénico de *Pinus sylvestris*.

**Confianza:** alta para presencia y fenología local; no aporta relación meteorológica cuantitativa.

## 7. Stankevičienė, D. et al. (2008)

**Título:** Investigación de macrohongos en un bosque de *Pinus sylvestris* de cincuenta años.  
**Revista:** Baltic Forestry, 14(1), 7–15.  
**Texto completo:** https://balticforestry.lammc.lt/bf/PDF_Articles/2008-14%5B1%5D/BF%2014%281%29%207_15.pdf

**Aportación:** sitúa *B. pinophilus* entre las especies más raras del inventario, demostrando que un pinar compatible no garantiza una fructificación frecuente.

**Confianza:** media; resultado local y con pocos cuerpos fructíferos.

## 8. Salerni, E. et al. (2004)

**Título:** Experimental study for increasing productivity of *Boletus edulis* s.l. in Italy.  
**Revista:** Forest Ecology and Management, 201, 161–170.  
**Enlace:** https://www.sciencedirect.com/science/article/abs/pii/S0378112704005213

**Aportación:** el estudio se centró en *B. edulis*, pero identificó expresamente casos esporádicos de *B. pinophilus* —seis cuerpos fructíferos en dos años—. Se incluye únicamente como evidencia de irregularidad local y no para transferir los resultados del modelo de *B. edulis*.

**Confianza:** baja-media para *B. pinophilus* debido al reducido número de observaciones.

---

## Nota final sobre la evidencia

Se localizaron numerosos trabajos sobre el complejo *Boletus edulis*, modelos de producción de hongos comerciales y estudios generales de pinares. No se utilizaron para asignar umbrales meteorológicos a *B. pinophilus* cuando la especie no estaba analizada por separado.

También aparecieron referencias norteamericanas antiguas al “spring bolete” identificado como *B. pinophilus*. Parte de ese material corresponde actualmente a especies distintas, como *Boletus rex-veris*, por lo que no se utilizó para caracterizar la fenología europea de *B. pinophilus*.

La selección mantiene deliberadamente una conclusión prudente: existe evidencia suficiente para definir hábitat, fenología aproximada y sensibilidad a la alteración, pero no para inventar una receta meteorológica precisa.
