# Diseño del predictor de floradas de setas

Versión del documento: borrador 0.1

Ficheros relacionados:

- `mushroom_profiles.json`
- `mushroom_reference_catalogs.json`
- `mushroom_gis_mappings.json`
- `mushroom_observations.json`
- `docs/mushrooms/mushroom-local-observation-lab-es.md`
- `docs/mushrooms/mushroom-ml-training-plan-es.md`

Direccion ML acordada 2026-07-11: el modelo aprendido v0 actual sigue siendo
descriptivo y no debe confundirse con machine learning. El plan concreto de
dataset, variables meteorologicas diarias, entrenamiento y validacion empieza
con `boletus_aereus` y se define en
`docs/mushrooms/mushroom-ml-training-plan-es.md`.

Este documento propone una primera arquitectura funcional para el predictor de floradas de setas de Rainmapper. No define todavía un algoritmo cerrado ni un contrato definitivo de schema. Su objetivo es ordenar las decisiones antes de modificar el modelo de datos o implementar el motor predictivo.

La propuesta se ha contrastado con literatura científica identificada sobre productividad micológica, fructificación, fenología y modelos de distribución de hongos, pero no todos los artículos están disponibles como texto completo local. Por tanto, este documento distingue entre evidencia documental verificable, deducción prudente de diseño y trabajo pendiente. El dataset actual debe seguir considerándose un modelo inicial mantenible y explicable, no un modelo científico calibrado localmente.

Nota de vigencia 2026-07-05: las referencias antiguas a
`docker-data/mushroom-lab/working/` describen fases historicas. El modelo v0
operativo, sus features y su estado viven ahora en `mushroom-data/`
(`docker-data/mushroom-data/` en local, `/share/rainmapper/mushroom-data/` en
HA). `tmp/mushroom-lab/` queda para pruebas explicitas/QGIS.

Regla crítica:

```text
No fijar umbrales, pesos ni parámetros específicos del motor predictivo por intuición.
Cada valor debe estar soportado por fuente documental verificable o por observaciones locales trazables.
Si sólo existe una deducción general, debe documentarse como tal y no convertirse en número.
No asumir que una fuente contiene un dato si no se ha podido leer el contenido real.
No presentar como hecho una hipótesis que no se pueda demostrar con documentación, código fuente o datos locales.
```

## 1. Conclusión de diseño

El predictor no debería ser un único cálculo meteorológico del tipo "ha llovido X en 7 o 15 días". Las fuentes revisadas apuntan a un modelo híbrido con tres capas:

1. Aptitud estática del sitio.
2. Disparo meteorológico y fenológico.
3. Calibración local mediante observaciones reales.

La primera capa responde a:

```text
¿Puede esta especie fructificar razonablemente en esta celda?
```

La segunda capa responde a:

```text
¿Hay condiciones recientes para que fructifique ahora?
```

La tercera capa responde a:

```text
¿Qué nos dicen las observaciones locales sobre cómo corregir el modelo base?
```

Esta separación es importante porque un sitio ecológicamente perfecto puede no estar en momento de florada, y una semana meteorológicamente favorable no debería producir predicción alta si la especie no encaja con el hábitat, el árbol huésped, el suelo, la altitud o la orientación.

### 1.1 Dirección v0 acordada: señales amplias, no modelo hiperparametrizado

La v0 operativa debe empezar con un predictor más simple y explicable que el
modelo completo descrito en este documento. La literatura práctica y las guías
de campo suelen describir las especies con categorías amplias:

- bosques o árboles asociados;
- suelos ácidos/silíceos, calcáreos/básicos, arenosos, húmedos, yesíferos o
  variables;
- altitud o piso aproximado;
- temporada;
- hábitats sencillos como ribera, bosque montano, encinar, robledal, pinar,
  hayedo o prados/bordes.

Por tanto, las capas GIS deben ayudar a clasificar cada punto del mapa en esas
características internas. DEM aporta altitud/topografía; MVC50 aporta
vegetación, hábitat y sustrato; geología puede aportar una tendencia edáfica
cuando no hay una capa de suelo mejor. La geología detallada no debe convertirse
en el eje del predictor inicial: una roca como pizarra puede traducirse a
tendencia silícea/ácida, pero no debe crear una preferencia específica de especie
por `lith_slate` salvo fuente verificable.

La meteorología histórica de los incrementales de Rainmapper se aplicará después
como capa dinámica sobre esa aptitud estática del punto. Con pocas observaciones,
el resultado correcto puede ser todavía "apto por hábitat, meteorología
insuficientemente calibrada" o "datos insuficientes", no una puntuación
aparentemente precisa.

El modelo rico descrito en versiones previas de este documento queda como una
arquitectura futura de enriquecimiento avanzado, no como objetivo de cierre de
la v0. La v0 no debe intentar rellenar todos los campos actuales de
`mushroom_profiles.json`, ni usar pesos, ventanas meteorológicas o litologías
finas por especie como si fueran verdad productiva. Esos campos pueden
mantenerse por compatibilidad de datos, UI y exploración. Los valores efectivos
de la v0 deben salir de una proyección mínima y trazable del perfil mantenido,
documentada en `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`
y en `rainmapper_core/mushroom_profile_v0.py`, enriquecida después con la fuente
estructurada revisada y observaciones locales contrastadas cuando existan
suficientes datos.

Esta decisión evita reiniciar el mantenimiento desde cero: `mushroom_profiles.json`,
`mushroom_reference_catalogs.json`, `mushroom_gis_mappings.json` y la UI rica
actual se conservan. La futura UI v0 debe usar la misma base de mantenimiento,
pero mostrar solo los campos activos de v0 y aparcar los bloques ricos como vista
avanzada/futura.

### 1.2 Modelo aprendido v0 desde observaciones locales

El primer `mushroom_model_v0.json` generado por
`mushroom_learned_model_v0_build.sh` no es todavia el predictor operativo. Es
una capa descriptiva y auditable que resume que dicen las observaciones locales
ya reconstruidas sobre cada especie.

Entrada actual:

- `docker-data/mushroom-lab/working/features/observation_features_v0.json`;
- observaciones incluidas para calibracion local y con estado valido;
- contexto de campo declarado por el observador, cuando exista, empezando por
  hosts observados;
- contexto GIS v0 por observacion: hosts, bosques, suelos, habitat y altitud;
- meteorologia reconstruida por observacion: lluvia 1/7/14/21/30/60/90,
  temperatura 7/14/21/30 y humedad 7/14/21/30;
- gaps meteorologicos, GIS o de feature conservados como datos de calidad;
- procedencia por valor en las features categoricas cuando sea posible:
  `field` para evidencia declarada por el observador y `gis` para evidencia
  reconstruida desde GIS/DEM.

Salida actual:

- un bloque por especie;
- numero de observaciones usadas;
- separacion entre observaciones favorables y desfavorables segun el objetivo
  operativo derivado de la florada;
- soporte de variables categoricas: cuantas favorables/desfavorables contienen cada
  host, bosque, suelo o rasgo de habitat;
- ratios favorable/desfavorable cuando hay datos suficientes;
- rangos numericos observados en favorables y desfavorables: minimo, maximo y media
  para altitud, lluvia, temperatura y humedad;
- gaps agregados por especie.

El objetivo se materializa en los artefactos como `prediction_target`, pero la
fuente de verdad continua siendo `flush_abundance`. La correspondencia se lee
del entero `prediction_favorable` de
`catalogs.observation_flush_abundance`; no esta codificada en el modelo. Cada
reconstruccion conserva el mapping exacto y su huella para que un cambio futuro
del catalogo no altere silenciosamente la interpretacion de un modelo ya
generado.

Lo que hace:

- permite auditar si los valores declarados en `mushroom_profiles.json` estan
  apoyados por observaciones locales;
- permite diferenciar si el soporte de un valor viene de campo, de GIS/DEM o de
  ambos, sin mezclarlo como si tuviera la misma naturaleza;
- muestra candidatos o contradicciones potenciales, por ejemplo un host
  observado que no esta declarado o un suelo declarado que no aparece en ninguna
  observacion;
- permite comparar favorables contra desfavorables cuando existan suficientes
  observaciones de florada escasa, muy escasa o inexistente;
- sirve como base para generar candidatos revisables por especie.

Lo que no hace todavia:

- no predice floradas por celda ni por fecha;
- no calcula un score operativo;
- no modifica `mushroom_profiles.json`;
- no promociona automaticamente hosts, suelos, habitats, altitudes, meses ni
  rangos meteorologicos;
- no fija pesos, umbrales ni ventanas meteorologicas por especie;
- no debe interpretarse como evidencia fuerte si solo hay pocas observaciones o
  si solo hay favorables y ninguna desfavorable.

La pantalla `Evidencia > Modelo aprendido` es por tanto un detalle tecnico de
auditoria. Para que sea realmente util en mantenimiento, esa informacion debe
aparecer junto al dato que se esta revisando:

- en `Parametros`, al lado de hosts, bosques, suelos, habitat, altitud,
  fenologia y metricas meteorologicas v0;
- en `Especies > General`, como resumen compacto de observaciones usadas,
  gaps, contradicciones principales y estado de aprendizaje;
- en `Especies > Ecologia`, junto a cada host/bosque/suelo/habitat declarado o
  candidato;
- en `Especies > Fenologia y Topografia`, comparando meses y rango altitudinal
  declarados con lo observado;
- en meteorologia, como rangos observados y alertas de calidad de datos, no
  como parametros productivos aprobados automaticamente.

El flujo correcto sigue siendo no destructivo:

```text
observacion aprobada
  -> GIS/DEM y meteorologia reconstruidos
  -> features v0 reconstruidas con procedencia Campo/GIS
  -> modelo aprendido descriptivo
  -> evidencia v0 y valores emergentes visibles junto al parametro
  -> decision humana o candidato revisable
  -> promocion manual y trazable si procede
```

Esta capa puede evolucionar hacia un modelo estadistico o ML sencillo, pero debe
mantener explicabilidad y trazabilidad. El primer uso no debe ser "aprobar pesos
a mano", sino ayudar a detectar relaciones observadas y discrepancias entre el
perfil base y los datos reales.

Variantes futuras posibles, sin implementarlas todavia:

- estadistica descriptiva actual: soportes, ratios, rangos y gaps por especie;
- scoring explicable semi-automatico: convertir candidatos revisados en pesos o
  reglas simples, manteniendo trazabilidad;
- modelos clasicos ligeros cuando haya mas datos: regresion logistica, arboles
  pequenos o random forest limitado para comparar variables, siempre mostrando
  importancia/soporte y evitando una caja negra;
- evaluacion por especie con pocos datos: entrenar desde pocas observaciones es
  posible como experimento, pero la UI debe mostrar incertidumbre y no venderlo
  como verdad productiva.

No se recomienda deep learning ni modelos complejos en esta fase. El valor
inmediato esta en comparar el perfil base con lo que se observa localmente, y en
hacer visibles los calculos junto a cada parametro revisable.

## 2. Fuentes fiables usadas como referencia

Se han priorizado papers científicos y fuentes primarias. Las aplicaciones comerciales o páginas de pronóstico sin metodología pública no se consideran base suficiente para el diseño.

La biblioteca operativa de fuentes vive en `docs/mushrooms/literature/README.md`. Ese manifiesto indica qué artículos tienen acceso abierto detectable, cuáles están bloqueados para descarga automática desde terminal y cuáles quedan como `DOI-only`.

### 2.1 Modelos de rendimiento forestal y productividad micológica

Fuentes principales:

- Martínez-Peña et al. 2012, *Yield models for ectomycorrhizal mushrooms in Pinus sylvestris forests with special focus on Boletus edulis and Lactarius group deliciosus*: https://doi.org/10.1016/j.foreco.2012.06.034
- Taye et al. 2016, *Meteorological conditions and site characteristics driving edible mushroom production in Pinus pinaster forests of Central Spain*: https://doi.org/10.1016/j.funeco.2016.05.008
- Bonet et al. 2008, *Empirical models for predicting the production of wild mushrooms in Scots pine forests in the Central Pyrenees*: https://doi.org/10.1051/forest:2007089

Qué aportan al diseño:

- La productividad micológica depende de características del sitio y de la masa forestal, no sólo del tiempo reciente.
- Las variables de bosque, hospedante, altitud, orientación, edad/estructura forestal y clima aparecen como predictores relevantes.
- Justifican que Rainmapper mantenga una capa ecológica por especie y no sólo umbrales de lluvia/temperatura.

### 2.2 Modelos de fructificación, fenología y clima

Fuentes principales:

- Kauserud et al. 2012, *Warming-induced shift in European mushroom fruiting phenology*: https://doi.org/10.1073/pnas.1200789109
- Andrew et al. 2018, *Explaining European fungal fruiting phenology with climate variability*: https://doi.org/10.1002/ecy.2237
- Büntgen et al. 2015, *Drought-induced changes in the phenology, productivity and diversity of Spanish fungi*: https://doi.org/10.1016/j.funeco.2015.03.008
- Krebs et al. 2008, *Mushroom crops in relation to weather in the southwestern Yukon*: https://doi.org/10.1139/b08-094

Qué aportan al diseño:

- La fenología cambia con temperatura, precipitación, altitud y variabilidad climática.
- La sequía y el estrés hídrico afectan productividad, diversidad y calendario de fructificación.
- La lluvia útil puede operar en ventanas más largas que 7 o 15 días.
- En algunos contextos se observan efectos de memoria o condiciones acumuladas que no encajan en una ventana corta única.

### 2.3 Modelos de distribución y aptitud de hábitat

Fuente principal:

- Nepote Valentin et al. 2023, *Modeling geographic distribution of arbuscular mycorrhizal fungi from molecular evidence in soils using a maximum entropy approach*: https://doi.org/10.7717/peerj.14651

Qué aporta al diseño:

- Los modelos de distribución de especies usan ocurrencias y variables ambientales como clima, suelo, vegetación, elevación y uso/cobertura del suelo.
- Esto justifica una capa GIS traducida a un vocabulario interno estable.
- La predicción espacial necesita separar datos GIS crudos de conceptos ecológicos usados por el motor.

## 3. Papel de `mushroom_gis_mappings.json`

`mushroom_gis_mappings.json` sí tiene sentido si Rainmapper quiere predecir por celda/mapa.

No es estrictamente necesario para:

- editar especies;
- registrar observaciones;
- calcular un score manual de una observación concreta con coordenadas ya conocidas;
- desarrollar pantallas de mantenimiento.

Sí es necesario para:

- convertir capas externas de vegetación, bosque, suelo o geología a IDs internos;
- comparar una celda GIS con las afinidades de `mushroom_profiles.json`;
- mantener el predictor independiente de nombres crudos de capas externas;
- validar impacto cuando cambian catálogos o perfiles;
- explicar por qué una celda sube o baja de aptitud para una especie.

La regla conceptual debería ser:

```text
Las capas GIS describen el territorio con códigos externos.
Los perfiles de especie describen ecología con IDs internos.
mushroom_gis_mappings.json traduce entre ambos mundos.
```

Por tanto, no conviene eliminarlo. Lo prudente es mantenerlo como fichero versionado y validable, pero no invertir todavía en una UI compleja hasta elegir fuentes GIS definitivas.

### 3.1 Uso durante la predicción

Durante la predicción, `mushroom_gis_mappings.json` no debería actuar como una lista decorativa. Su función será transformar atributos externos de capas GIS en señales internas que el motor pueda comparar contra los perfiles de especie.

Ejemplo conceptual:

```text
coordenada -> capa externa de vegetación -> código externo -> mapping -> host_taxa/forest_types/habitat_features -> score de hábitat
coordenada -> capa geológica -> código externo -> mapping -> lithology_types/soil_types -> score de suelo/litología
coordenada -> DEM -> altitud/orientación/pendiente -> topography_score
```

Reglas de diseño:

- El predictor no debe depender de textos crudos de una capa externa.
- Cada mapping debe indicar de qué fuente/capa/campo procede.
- Si una capa cambia códigos, se debe arreglar el mapping sin tocar perfiles de especie.
- Si un código externo no tiene mapping, el motor debe reportarlo como gap de GIS, no inventar una afinidad.
- La UI de catalogos debe poder enseñar impacto y referencias, pero la edición completa de mappings puede esperar hasta elegir fuentes definitivas.

### 3.2 Relación con fuentes GIS candidatas

Las fuentes candidatas para Catalunya y España son oficiales, pero todavía deben verificarse capa por capa antes de convertirlas en contrato del motor:

- ICGC/ICC:
  - DEM/elevaciones;
  - cubiertas del suelo;
  - vegetación/hábitats;
  - geología/litología;
  - suelos si hay atributos útiles.
- IGN/CNIG:
  - MDT/DEM;
  - SIOSE u ocupación/cobertura del suelo;
  - servicios y descargas nacionales útiles para zonas fuera de Catalunya.

Preferencia:

- DEM: raster local o WCS/descarga reproducible.
- Vegetación, hábitat, litología y suelo: vector local, WFS o descarga con atributos.
- WMS: válido para inspección visual, no como fuente primaria del cálculo porque devuelve imagen.

Antes de implementar un extractor hay que documentar URL/servicio, licencia, cobertura, resolución, sistema de referencia, campos usados y mapping interno.

## 4. Modelo funcional propuesto

### 4.1 Entradas estáticas de celda

Estas variables describen el lugar:

- altitud DEM;
- orientación;
- pendiente, si está disponible;
- posición topográfica o proxy de humedad, si puede derivarse;
- vegetación dominante;
- árboles o grupos de árboles;
- tipo de bosque;
- litología/geología;
- suelo o tendencia de suelo;
- rasgos de microhábitat inferibles, si la fuente GIS lo permite.

Estas entradas deberían convertirse a IDs internos mediante `mushroom_gis_mappings.json` cuando procedan de capas externas.

### 4.2 Entradas dinámicas meteorológicas

Estas variables describen el momento:

- lluvia acumulada ya disponible en Rainmapper, actualmente 1, 7, 14, 21, 30, 60 y 90 días;
- lluvia diaria desde incrementales cuando haga falta reconstruir ventanas o episodios;
- días desde lluvia significativa;
- intensidad del último episodio de lluvia;
- días secos consecutivos;
- temperatura mínima y máxima reciente;
- temperatura media o grados-día, si se decide usar suma térmica;
- heladas recientes;
- calor extremo reciente;
- humedad relativa;
- VPD o estrés evaporativo, si se puede calcular;
- viento medio y rachas;
- proxy de humedad de suelo;
- nieve/deshielo para especies de montaña o primavera.

No todas estas variables tienen que estar en `mushroom_profiles.json`. En particular, las ventanas de lluvia largas ya existen en Rainmapper o pueden derivarse desde incrementales diarios. El trabajo pendiente no es "crear más datos meteorológicos", sino seleccionar qué variables usa el motor, cómo las transforma y cómo las explica.

Principio de diseño:

```text
Los datos meteorológicos base viven en Rainmapper.
El motor calcula features predictivas a partir de esos datos.
Los perfiles de especie sólo guardan parámetros humanos si hay fuente fiable o calibración local.
```

### 4.3 Entradas de especie

Estas variables ya pertenecen al perfil de especie:

- modo trófico;
- afinidades de hospedador;
- afinidades de bosque;
- afinidades de suelo;
- afinidades de litología;
- rasgos de hábitat;
- meses principales y secundarios;
- patrones de temporada;
- retraso tras lluvia;
- rango altitudinal;
- orientaciones preferidas;
- umbrales meteorológicos;
- pesos de scoring;
- confianza y prioridad de calibración.

### 4.4 Entradas de observación

Las observaciones deben servir para calibrar, no sólo para guardar histórico. Deben aportar:

- especie;
- fecha;
- coordenadas;
- altitud observada o recuperada;
- abundancia/florada;
- ausencia explícita si se registra;
- calidad de origen;
- validación;
- uso para calibración;
- observador/origen;
- notas de hábitat y hospedador.

La observación debe poder ponderarse por calidad, estado de validación y uso de calibración.

## 5. Scoring conceptual

El motor debería producir varias puntuaciones parciales antes de una puntuación final:

```text
habitat_static_score
host_score
soil_lithology_score
topography_score
phenology_score
moisture_trigger_score
temperature_score
desiccation_penalty
calibration_adjustment
```

La puntuación final no debería presentarse inicialmente como probabilidad estadística estricta si no hay calibración suficiente. Es más honesto tratarla como:

```text
índice de aptitud de florada
```

o:

```text
score relativo explicable
```

Cuando haya suficientes observaciones, se podrá calibrar hacia probabilidad o clases de confianza.

## 6. Comparación contra el schema actual

| Familia de variables | Estado actual | Evaluación | Acción recomendada |
| --- | --- | --- | --- |
| Especie e identidad | Cubierto en `mushroom_profiles.json` | Correcto | Mantener |
| Modo trófico | Cubierto por catálogo | Correcto | Mantener |
| Hospedadores | Cubierto por afinidades y catálogo | Importante para ectomicorrícicas | Mantener |
| Bosque/hábitat | Cubierto por afinidades | Correcto | Mantener |
| Suelos | Cubierto por catálogo | Útil, pero dependerá de calidad de fuente GIS | Mantener |
| Litología | Cubierto por catálogo | Útil como proxy, no sustituye mapa de suelo | Mantener |
| Rasgos de hábitat | Cubierto | Útil pero difícil de inferir por GIS | Mantener como afinidad manual |
| Altitud | Cubierto | Muy relevante | Mantener |
| Orientación | Cubierto | Relevante para humedad/insolación | Mantener |
| Pendiente | Mencionada en docs, no perfilada por especie | Puede ayudar a drenaje/humedad | Derivar desde DEM antes de añadir parámetros por especie |
| Meses principales/secundarios | Cubierto | Correcto | Mantener |
| Patrones de temporada | Cubierto por catálogo | Correcto | Mantener |
| Retraso tras lluvia | Cubierto | Muy útil | Mantener |
| Lluvia 1/7/14/21/30/60/90 días | Disponible en Rainmapper GeoJSON | Base suficiente para explorar ventanas largas | Seleccionar ventanas predictivas en el motor, no duplicarlas en perfiles |
| Incrementales diarios de lluvia | Disponible en Rainmapper | Permite reconstruir episodios y rachas secas | Usar para features derivadas |
| Días desde lluvia significativa | Derivable desde incrementales | Muy relevante operacionalmente | Calcular en el motor, con umbral global inicialmente |
| Periodo seco acumulado | Derivable desde incrementales | Relevante para sequía | Calcular en el motor, sin umbral por especie inicialmente |
| Humedad relativa | Cubierto 7 días | Útil pero limitado | Mantener y evaluar VPD |
| VPD / estrés evaporativo | No cubierto | Puede ser mejor que humedad aislada | Derivar si hay datos suficientes |
| Temperatura reciente | Cubierto 7 días | Correcto | Mantener |
| Suma térmica / grados-día | No cubierto | Puede ayudar en primavera/deshielo | Evaluar más adelante |
| Helada/calor | Cubierto como penalización | Correcto | Mantener |
| Viento seco | Cubierto | Correcto para desecación | Mantener |
| Nieve/deshielo | Cubierto como caso especial | Tiene sentido para especies concretas | Mantener como modificador, no como regla general |
| Edad/estructura forestal | No cubierto | Aparece en literatura | Futuro, sólo si hay GIS fiable |
| Observaciones | Cubierto como base inicial | Clave para calibración | Diseñar calibración real |

## 7. Lluvia más allá de 14/15 días

La pregunta no debería ser sólo si añadimos un campo `rain_30d_min_mm` al perfil. Además, Rainmapper ya tiene acumulados de lluvia a 1, 7, 14, 21, 30, 60 y 90 días, y también dispone de detalle diario en incrementales. Por tanto, el problema no es la falta de datos base.

Hay dos fenómenos distintos:

1. Lluvia detonante reciente.
2. Humedad antecedente o estrés hídrico acumulado.

El primer fenómeno encaja bien con 7/15 días y retraso tras lluvia.

El segundo puede evaluarse con ventanas largas o índices derivados:

- lluvia acumulada 21/30/60/90 días ya existente;
- días secos consecutivos;
- días desde lluvia significativa;
- balance simple lluvia-evapotranspiración;
- proxy de humedad de suelo.

Recomendación:

```text
No añadir de entrada muchos umbrales manuales por especie.
Primero seleccionar features a partir de acumulados/incrementales ya disponibles.
Registrar esas features en explicaciones/debug.
Después, con fuentes específicas u observaciones, decidir qué especies necesitan sensibilidad propia.
```

Esto mantiene el perfil de especie mantenible y evita convertirlo en una tabla de parámetros difícil de calibrar manualmente.

## 8. ¿Sobran datos en el perfil de especie?

No parece que sobren datos para un modelo explicable. La mayoría de campos actuales corresponden a variables que aparecen en la literatura o son necesarias para explicar decisiones al usuario.

El riesgo no es tener demasiadas familias de datos, sino:

- intentar calibrarlas manualmente sin observaciones;
- confundir proxies débiles con datos directos;
- añadir más umbrales meteorológicos por especie antes de tener motor y validación;
- mezclar valores calculados automáticamente con parámetros mantenidos por humanos.

La estrategia recomendada es:

```text
Mantener los perfiles como conocimiento experto editable.
Calcular variables meteorológicas y GIS derivadas en el motor.
Usar observaciones para ajustar pesos y umbrales.
```

## 9. Deducciones aplicables desde la literatura

Esta sección no pretende fijar valores exactos para cada especie. Resume qué se puede deducir razonablemente de las fuentes identificadas y qué uso práctico tiene para Rainmapper. Donde no haya texto completo local o una fuente específica de especie, las conclusiones deben tratarse como hipótesis de diseño pendientes de validación, no como parámetros calibrados.

Regla de seguridad:

```text
No se deben inventar pesos o umbrales por especie.
Un parámetro específico de especie necesita fuente documental verificable o calibración local.
La revisión humana puede aprobar una hipótesis, pero debe quedar marcada como no calibrada si no hay evidencia.
```

### 9.1 Ectomicorrícicas de pinar y planifolios

Especies actuales afectadas:

- `boletus_pinophilus`
- `boletus_edulis`
- `boletus_aereus`
- `lactarius_sanguifluus`
- `lactarius_vinosus`
- `hygrophorus_marzuolus`
- `hygrophorus_latitabundus`
- `cantharellus_cibarius_sl`

Deducciones con soporte:

- El árbol huésped y el tipo de bosque importan mucho en la aptitud estática.
- La edad/estructura de la masa forestal aparece en modelos publicados, pero Rainmapper no debería pedirla como parámetro manual hasta tener una fuente GIS fiable.
- Altitud y orientación aparecen como variables relevantes en estudios forestales y de fenología.
- Temperatura, precipitación y sequía afectan productividad y calendario.
- La lluvia reciente no basta: la humedad antecedente y el estrés hídrico acumulado deben poder entrar en el motor.

Aplicación a nuestro schema:

- Mantener afinidades de hospedador, bosque, suelo, litología, altitud y orientación.
- Usar `mushroom_gis_mappings.json` para traducir bosque/vegetación/suelo/geología a IDs internos.
- No añadir todavía pesos por especie para cada ventana de lluvia.
- Calcular y mostrar variables de 21/30/60/90 días como contexto del score.

Fuentes especialmente relevantes:

- Martínez-Peña et al. 2012: modelos para *Boletus edulis* y grupo *Lactarius deliciosus* en `Pinus sylvestris`.
- Bonet et al. 2004/2008/2010: producción de esporocarpos, edad/orientación y modelos en pinares del Pirineo central.
- Taye et al. 2016: meteorología y características de sitio en `Pinus pinaster` del centro de España.

### 9.2 Boletus y Lactarius

Deducciones con soporte más directo:

- Hay literatura específica para *Boletus edulis* y grupo *Lactarius deliciosus*.
- Las fuentes relacionan producción con masas de pino, variables de sitio y meteorología.
- Para `lactarius_sanguifluus` y `lactarius_vinosus`, la extrapolación desde grupo *Lactarius deliciosus* debe tratarse como aproximación, no como valor calibrado.
- Para `boletus_pinophilus` y `boletus_aereus`, la extrapolación desde *Boletus edulis* debe tratarse como familiar/ecológica, no específica.

Uso recomendado:

- Revisar primero perfiles de Boletus/Lactarius con esta literatura.
- Documentar en cada especie qué parámetros son específicos y cuáles son extrapolados.
- Priorizar observaciones reales para separar especies próximas.

### 9.3 Cantharellus

Deducciones con soporte parcial:

- *Cantharellus cibarius* es ectomicorrícica y su productividad depende de hábitat/árboles y condiciones ambientales.
- Hay fuentes monográficas y estudios de productividad/ecología, pero no se ha localizado todavía una tabla simple de umbrales meteorológicos transferibles a Cataluña.

Uso recomendado:

- Mantenerlo como `sensu lato` operativo.
- No afinar umbrales meteorológicos específicos sin fuente adicional o observaciones.
- Priorizar observaciones locales para diferenciar comportamiento real en encinares, hayedos, pinares u otros bosques.

Fuente candidata:

- CABI Compendium, *Cantharellus cibarius (golden chanterelle)*: https://doi.org/10.1079/cabicompendium.33373661

### 9.4 Morchella, Hygrophorus marzuolus y especies de primavera/deshielo

Deducciones prudentes:

- El deshielo y la dinámica térmica de primavera pueden ser relevantes para especies de montaña o primavera.
- `snowmelt_bonus` debe seguir siendo un modificador específico, no una regla general.
- No hay que interpretar nieve/deshielo como equivalente directo a lluvia.

Uso recomendado:

- Mantener `snowmelt_bonus` sólo en especies donde tenga sentido ecológico.
- Calcular variables de temperatura/deshielo como features del motor si hay datos disponibles.
- No añadir más parámetros manuales hasta tener fuentes específicas o observaciones locales.

### 9.5 Especies faltantes frecuentes en Cataluña

La lista actual cubre especies habituales de recolección, pero no es completa. Candidatas futuras:

- seta de cardo, *Pleurotus eryngii*;
- níscalos adicionales o complejos locales si se decide separarlos;
- otras especies locales de interés operativo.

Para introducir nuevas especies, el flujo recomendado es:

1. Buscar fuente específica de ecología/fructificación.
2. Añadir vocabulario necesario al catálogo si falta.
3. Crear perfil conservador con campos mínimos.
4. Marcar confianza/calibración como baja o pendiente.
5. Calibrar con observaciones reales antes de afinar umbrales.

## 10. Biblioteca de fuentes a conservar

Estas fuentes deben tratarse como material de referencia para revisar especies existentes o introducir especies nuevas.

El manifiesto local vive en `docs/mushrooms/literature/README.md`. En esta fase no hay PDFs locales validados porque las fuentes open access detectadas devuelven bloqueos anti-bot/403 desde terminal o repositorios con challenge, y las demás fuentes aparecen como no open access en OpenAlex. No se han guardado páginas de bloqueo ni HTML de landing como si fueran papers.

| Fuente | Utilidad para Rainmapper |
| --- | --- |
| Martínez-Peña et al. 2012, `10.1016/j.foreco.2012.06.034` | Base para Boletus/Lactarius, pinares, rendimiento y variables forestales |
| Bonet et al. 2004, `10.1016/j.foreco.2004.07.063` | Relación entre edad/orientación y producción en `Pinus sylvestris` |
| Bonet et al. 2008, `10.1051/forest:2007089` | Modelos empíricos de producción en pinares del Pirineo central |
| Bonet et al. 2010, `10.1139/X09-198` | Producción y riqueza de setas en pinares del Pirineo central |
| Taye et al. 2016, `10.1016/j.funeco.2016.05.008` | Meteorología y características de sitio en `Pinus pinaster` |
| Büntgen et al. 2015, `10.1016/j.funeco.2015.03.008` | Sequía, fenología y productividad de hongos en España |
| Kauserud et al. 2012, `10.1073/pnas.1200789109` | Cambio fenológico europeo y relación con clima |
| Andrew et al. 2018, `10.1002/ecy.2237` | Fenología fúngica explicada con variabilidad climática |
| Krebs et al. 2008, `10.1139/b08-094` | Ejemplo fuerte de memoria hídrica/lluvia en ventanas largas |
| Nepote Valentin et al. 2023, `10.7717/peerj.14651` | Justificación de modelos GIS/SDM con clima, suelo, vegetación y elevación |
| CABI, *Cantharellus cibarius*, `10.1079/cabicompendium.33373661` | Ficha monográfica para revisar Cantharellus sensu lato |

Queda pendiente crear una bibliografía más operativa por especie. Esa bibliografía debería vivir en documentación o en un futuro campo de metadatos de especie, no mezclada con los parámetros predictivos.

## 11. Cambios candidatos futuros

Estos cambios no deberían aplicarse automáticamente. Requieren diseño y validación:

1. Seleccionar features meteorológicas calculadas a partir de datos ya disponibles:
   - `rain_21d_total_mm`
   - `rain_30d_total_mm`
   - `rain_60d_total_mm`
   - `rain_90d_total_mm`
   - `days_since_significant_rain`
   - `dry_spell_days`
   - `soil_moisture_proxy`
   - `vpd_proxy`

2. Revisar `weather_model.rainfall`:
   - mantener 7/15 días como disparo reciente;
   - redefinir `rain_30d_saturation_penalty_mm` como penalización de exceso, no como sustituto de humedad antecedente;
   - no añadir `rain_30d_min_mm` por especie salvo fuente fiable o calibración local.

3. Revisar topografía:
   - tratar pendiente inicialmente como feature de celda, no como preferencia manual por especie;
   - evaluar un índice topográfico de humedad si el DEM lo permite.

4. Revisar nieve/deshielo:
   - mantenerlo como modificador específico para especies de primavera/montaña;
   - evitar que contamine especies donde no aplica.

5. Diseñar calibración:
   - definir cómo pesan abundancia, validación, calidad de origen y uso de calibración;
   - separar observaciones positivas, negativas y dudosas;
   - decidir si se ajustan pesos globales, umbrales por especie o correcciones por zona.

## 11.1 Engine experimental desde observaciones reales

El siguiente motor a construir no debe sobrescribir fichas. Debe reconstruir condiciones observadas y generar candidatos revisables.

Entradas:

- observaciones reales desde `mushroom_observations.json`;
- incrementales meteorológicos de Rainmapper;
- perfiles actuales;
- catálogos;
- mappings GIS;
- capas DEM/GIS locales cuando existan.

Salidas:

- features meteorológicas por observación;
- features GIS/topográficas por observación;
- resumen por especie;
- diferencias entre positivas y negativas;
- candidatos experimentales con trazabilidad;
- reporte humano.

Un candidato sólo puede pasar a ficha real mediante revisión manual. El motor debe indicar:

- observaciones usadas;
- calidad y estado de validación;
- si hay observaciones negativas comparables;
- valor actual;
- rango observado;
- candidato, si procede;
- confianza;
- campos sin datos suficientes.

Con pocas observaciones, el resultado correcto puede ser simplemente "datos insuficientes" más una tabla de condiciones reales observadas.

## 11.2 Estado UI que habilita el laboratorio

La UI actual de observaciones ya permite capturar datos reales de forma mucho más rápida que un flujo batch manual:

- alta y edición de observaciones;
- filtros por especie, fecha, resultado, estado y texto;
- selector de todas las especies;
- ordenación por cabeceras;
- selección de fila completa para ver detalle;
- archivado/restauración/borrado defensivo;
- importación de fotos EXIF con plantilla común;
- importación de una foto, varias fotos o carpeta;
- duplicado como plantilla sin guardar;
- duplicado con recuperación EXIF antes del guardado;
- preservación de filtros y panel de archivadas tras acciones.

Esta UI puede usarse en local contra `docker-data/` para capturar observaciones sin tocar HA. Cuando se decida publicar el flujo en HA, hay que recordar que los datos productivos de observaciones se guardan en `/share/rainmapper/mushroom-data/mushroom_observations.json`.

## 11.3 Subida futura desde MapLibre por colaboradores

Funcionalidad futura de prioridad media: permitir que los colaboradores actuales, no necesariamente los usuarios comerciales futuros, puedan subir fotos de observaciones desde el visor protegido MapLibre.

La forma preferida encaja con el patron de permisos/toggles de MapLibre ya existente para metricas, IDW y Heatmap: un permiso por usuario, por ejemplo `can_upload_mushroom_observations`, controla si el visor muestra o no la accion de subida de observaciones.

Objetivo:

- aumentar rapidamente el volumen de observaciones reales;
- aprovechar EXIF de fotos tomadas en campo;
- registrar automaticamente usuario/origen desde la sesion Rainmapper;
- dejar todo como pendiente de revision por el propietario antes de usarlo en calibracion.

Alcance propuesto:

- toggle/permiso en gestion de usuarios para activar subida de observaciones;
- boton o panel en MapLibre protegido para `Subir observacion`;
- seleccion de una o varias imagenes;
- validacion de que la imagen contiene EXIF util antes de crear observacion;
- extraccion EXIF de fecha, coordenadas y altitud con la misma logica que la WebUI de observaciones;
- `observer` y usuario tecnico derivados de la sesion autenticada;
- `source.type = photo_exif`;
- `source.label = nombre del fichero`;
- `validation_status = draft` o estado equivalente pendiente de revision;
- `calibration_use = review` o equivalente;
- la observacion no debe entrar automaticamente en calibracion hasta revision manual.

Compatibilidad y conversion de imagen:

- JPEG con EXIF debe ser el camino base para iPhone y Android.
- HEIC/HEIF no debe considerarse garantizado hasta validarlo en el contenedor real.
- Si se decide aceptar HEIC/HEIF, valorar una conversion server-side a JPEG durante la subida, preservando EXIF util antes de extraer fecha/GPS/altitud o almacenar metadata.
- La conversion no debe borrar ni alterar la informacion EXIF necesaria para la observacion.
- Si la imagen no tiene EXIF util, debe rechazarse o quedar como pendiente incompleta, nunca crear coordenadas por defecto.

Riesgos y decisiones pendientes:

- definir si los colaboradores pueden indicar especie/abundancia o si solo suben foto y comentario;
- evitar exponer coordenadas privadas a otros usuarios;
- limitar tamano, numero y tipo de ficheros;
- definir si se guardan imagenes originales, JPEG convertido o solo EXIF/metadata. Por privacidad y almacenamiento, la opcion preferida inicialmente es no persistir la imagen completa salvo decision explicita;
- validar compatibilidad Android/iPhone en HA real.

Regla importante: estas observaciones externas deben quedar separadas conceptualmente de observaciones validadas. Sirven para acelerar captura, no para modificar parametros sin revision humana.

## 12. Decisiones pendientes

- Elegir fuentes GIS reales y su granularidad.
- Decidir si `mushroom_gis_mappings.json` seguirá siendo sólo fichero o tendrá mantenimiento visual.
- Definir el primer algoritmo de scoring explicable.
- Definir qué features meteorológicas de los acumulados/incrementales actuales usa el predictor.
- Definir cómo se guardarán resultados/debug de predicción para poder auditar el modelo.
- Definir el mínimo de observaciones necesario antes de llamar a un resultado "calibrado". Base empírica disponible (2026-08-02): 22 observaciones (Morchella elata complex) es el límite con incertidumbre alta; 66+ (Hygrophorus marzuolus) es un punto de partida cómodo. Se recomienda ≥20 como criterio de entrada al modelo v1.
- Decidir si el output será una clase ordinal, un score 0-1 o una probabilidad calibrada.

## 13. Recomendación inmediata

El siguiente paso recomendado no es cambiar todavía el schema de perfiles, sino construir primero un laboratorio local de observaciones reales. El diseño operativo vive en `docs/mushrooms/mushroom-local-observation-lab-es.md`.

Flujo recomendado:

1. Copiar historicos meteorologicos de HA a `tmp/mushroom-lab/input/ha-data/`.
2. Importar observaciones positivas y negativas desde fotos geolocalizadas o CSV manual.
3. Reconstruir condiciones meteorologicas previas a cada observacion desde incrementales.
4. Cruzar cada coordenada con DEM, cubierta/vegetacion y litologia/suelo.
5. Generar condiciones observadas por especie.
6. Proponer parametros candidatos marcados como experimentales.
7. Promocionar manualmente a fichas reales solo cuando haya evidencia suficiente.

Cuando exista ese laboratorio, diseñar el primer motor explicable:

1. Definir features estáticas de celda.
2. Seleccionar features meteorológicas desde acumulados e incrementales existentes.
3. Definir puntuaciones parciales.
4. Definir salida y explicación.
5. Ejecutar el motor contra especies actuales sin calibración.
6. Comparar predicciones con observaciones reales.
7. Sólo entonces decidir nuevos campos estructurales en `mushroom_profiles.json`.

Esto permite avanzar sin sobrecargar el mantenimiento manual de especies y evita que el schema crezca antes de saber qué variables aportan señal real en nuestro territorio.
