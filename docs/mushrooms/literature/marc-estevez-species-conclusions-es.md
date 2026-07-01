# Conclusiones operativas de `Marc_EstevezSpecies.pdf`

Fuente local revisada: `docs/mushrooms/literature/Marc_EstevezSpecies.pdf`.

Fecha de revisión: 2026-07-01.

Método de revisión: el PDF no contiene texto seleccionable; `pdftotext` devolvió
páginas vacías. Se revisaron visualmente las 20 páginas renderizadas como
imágenes. Tesseract quedó instalado, pero la build local no pudo leer las
imágenes generadas por Leptonica, así que estas conclusiones se basan en lectura
visual humana asistida por las páginas renderizadas.

Uso previsto: este documento es una base de trabajo para construir un seed
experimental de especies y para orientar el predictor v0. No es un perfil
productivo ni debe sobrescribir `mushroom_profiles.json`. Las señales se han
traducido a categorías amplias y reutilizables para España: vegetación/host,
suelo amplio, hábitat, altitud, temporada y meteorología cualitativa.

Regla de interpretación: cuando el texto describe una preferencia clara se marca
como `preferente`. Cuando el texto admite variación, tolerancia o excepciones se
marca como `tendencia` o `no usar como filtro duro`.

## Resumen general

El documento confirma que el enfoque más realista para la v0 no debe centrarse
en litología fina ni en miles de códigos GIS. La información útil aparece casi
siempre en estas categorías:

- Bosque o vegetación asociada: pinar, abetal, hayedo, robledal, encinar,
  alcornocal, castañar, bosque de ribera, prados, claros y bordes.
- Host o árbol asociado: `Pinus sylvestris`, `Pinus uncinata`, `Pinus nigra`,
  `Pinus halepensis`, `Pinus pinaster`, `Pinus pinea`, `Abies alba`,
  `Fagus sylvatica`, `Quercus ilex`, `Quercus suber`, robles caducifolios,
  castaño, abedul, avellano y otros según especie.
- Suelo amplio: ácido/silíceo, calcáreo/básico, descarbonatado, arenoso,
  húmedo, rico en materia orgánica, variable o indiferente.
- Altitud aproximada y desplazamiento estacional de la cota.
- Calendario de recolección por ventanas amplias, no umbrales exactos.
- Meteorología cualitativa: lluvias/tormentas, enfriamiento posterior, otoño
  avanzado, tolerancia al frío, sensibilidad al calor, humedad persistente.

La geología sigue siendo útil para clasificar puntos del mapa hacia suelo amplio,
pero no como requisito micológico específico salvo casos muy claros como suelos
calcáreos para especies calcícolas.

## Amanita caesarea

Nombre de ficha: el reig. Nombre científico: `Amanita caesarea`.

Páginas revisadas: PDF página 1.

Conclusión para v0:

- Especie termófila mediterránea y de tierra baja/media.
- Debe modelarse con bosques mediterráneos de frondosas, no con coníferas como
  requisito principal.
- El suelo preferente es silíceo, ácido o neutro; puede aparecer
  esporádicamente sobre calizos descarbonatados.
- La lluvia por sí sola no basta: el texto destaca el contraste entre terreno
  caliente, lluvias fuertes de verano y posterior enfriamiento del suelo.

Señales estructurables:

- Vegetación/host preferente:
  - alcornocales con `Quercus suber`;
  - encinares con `Quercus ilex`;
  - robledales con `Quercus humilis`/robles mediterráneos;
  - castañares con `Castanea sativa`;
  - madroño y matorrales mediterráneos como contexto acompañante.
- Suelo:
  - preferente: `soil_siliceous`, `soil_acidic`, `soil_neutral`;
  - tolerancia puntual: `soil_calcareous` si está descarbonatado.
- Hábitat:
  - bosque mediterráneo claro o no excesivamente frío;
  - sotobosque con jaras, brezos o brecina como señal acompañante.
- Calendario:
  - principal: septiembre y octubre;
  - puede aparecer desde junio en bosques esclerófilos si hay condiciones
    óptimas;
  - hábitats más tardíos cerca del litoral.
- Meteorología cualitativa:
  - lluvias/tormentas de verano tras terreno caliente;
  - enfriamiento posterior favorecedor;
  - requiere humedad y temperatura adecuadas.
- Altitud:
  - habitualmente por debajo de 1.000 m según la ficha.

Recomendación de modelo:

- `soil_siliceous`/`soil_acidic` deben ser preferencia, no requisito absoluto.
- `forest_holm_oak`, `forest_cork_oak`, `forest_chestnut` y robledales
  mediterráneos deberían tener mucho peso de aptitud estática.
- La señal meteorológica inicial debería ser cualitativa: lluvia estival y
  contraste térmico. No fijar aún milímetros ni días.

## Boletus edulis / Boletus pinophilus

Nombre de ficha: el cep. Nombres científicos: `Boletus edulis`,
`Boletus pinophilus`.

Páginas revisadas: PDF página 2.

Conclusión para v0:

- La ficha trata conjuntamente el grupo de cep, pero separa comportamiento de
  `B. edulis` y `B. pinophilus`.
- Es un grupo de montaña y bosques frescos, asociado a coníferas y frondosas
  montanas.
- Suelos preferentemente ácidos/silíceos o calizos acidificados, con árboles
  maduros.

Señales estructurables:

- Vegetación/host principal:
  - `Pinus uncinata`;
  - `Pinus sylvestris`;
  - `Abies alba`;
  - en menor medida `Fagus sylvatica`;
  - `Betula pendula`.
- Suelo:
  - `soil_acidic`;
  - `soil_siliceous`;
  - calizos acidificados como tolerancia, no como calcícola.
- Hábitat:
  - bosques frescos montanos;
  - sotobosque con arándanos, brezos o frambuesas como contexto;
  - árboles maduros como condición cualitativa.
- Calendario:
  - `B. edulis`: segunda quincena de julio en bosques frescos por encima de
    1.600 m; máximos entre final de agosto y comienzo de octubre; puede durar
    hasta noviembre en vertientes protegidas del frío.
  - `B. pinophilus`: más temprano; puede aparecer en junio en cotas más bajas,
    entre 1.000 y 1.500 m, con floradas alrededor de San Juan/San Pedro.
- Altitud:
  - `B. edulis`: alta montaña/fresco, por encima de 1.600 m al inicio.
  - `B. pinophilus`: 1.000-1.500 m para apariciones tempranas.

Recomendación de modelo:

- Conviene separar `boletus_edulis` y `boletus_pinophilus` como taxones
  operativos si el predictor quiere calendario y altitud distintos.
- La preferencia por suelos ácidos/silíceos parece clara.
- La madurez del bosque aparece como variable ecológica útil, pero no tenemos
  GIS fiable aún; dejar como nota o candidato futuro.

## Boletus aereus

Nombre de ficha: el sureny fosc. Nombre científico: `Boletus aereus`.

Páginas revisadas: PDF página 3.

Conclusión para v0:

- Especie termófila de baja/media altitud, vinculada a bosques mediterráneos
  de frondosas.
- Preferencia fuerte por sustratos silíceos, más o menos ácidos.
- No suele encontrarse por encima de 900-1.000 m en Catalunya según la ficha.

Señales estructurables:

- Vegetación/host:
  - `Quercus suber`;
  - `Quercus ilex`;
  - `Castanea sativa`;
  - en menor medida robledales y matorrales de brezos/jaras.
- Suelo:
  - `soil_siliceous`;
  - `soil_acidic`;
  - ejemplos de salou, gneis y pizarra como señales de sustrato silíceo.
- Hábitat:
  - alcornocal, encinar, castañar;
  - bosques poco densos, matorrales de brezo/jara;
  - tierra baja y media.
- Calendario:
  - puede empezar en junio si primavera lluviosa;
  - puede mantenerse en verano si siguen condiciones favorables;
  - época principal: final de verano, aproximadamente entre septiembre y mitad
    de octubre;
  - floradas tardías a veces en cotas inferiores a 400 m.
- Altitud:
  - preferencia por debajo de 900-1.000 m.

Recomendación de modelo:

- Buen candidato para aptitud mediterránea termófila.
- `soil_siliceous` y `soil_acidic` deberían ser señales fuertes.
- Evitar extrapolarlo a pinares montanos aunque pueda compartir espacio con
  otros boletos.

## Cantharellus cibarius

Nombre de ficha: el rossinyol. Nombre científico: `Cantharellus cibarius`.

Páginas revisadas: PDF página 4.

Conclusión para v0:

- Especie muy amplia y cosmopolita, pero con preferencia por terrenos silíceos,
  ácidos y bosques maduros/húmedos.
- Aparece desde cotas bajas hasta Pirineo, con desplazamiento estacional de la
  cota.
- Puede convivir con muchos bosques y hosts; no debe modelarse con un único host.

Señales estructurables:

- Vegetación/host:
  - hayedos;
  - robledales de roble albar/petraea y robles de montaña;
  - castañares;
  - encinares y alcornocales;
  - pinares de `Pinus sylvestris`, `Pinus uncinata`, `Pinus radiata`;
  - también eucaliptos y matorral de brezos/jaras según la ficha.
- Suelo:
  - `soil_siliceous`;
  - `soil_acidic`;
  - tolera grados moderados y notables de acidez.
- Hábitat:
  - bosques maduros, 40-50 años o más;
  - ambientes húmedos;
  - puede aparecer en muchos tipos de bosque.
- Calendario:
  - casi todo el año si se consideran todos los hábitats;
  - desde final de mayo/junio/julio en rouredas, encinares y hayedos;
  - en verano en bosques frescos de coníferas y plantaciones pirenaicas, hasta
    2.300 m;
  - en otoño baja progresivamente hacia alcornocales y zona litoral;
  - puede seguir en invierno en vertientes que miran al levante.
- Meteorología:
  - igual que `Amanita caesarea`, la ficha menciona floradas generosas con
    lluvias sobre terreno caliente y posterior enfriamiento.

Recomendación de modelo:

- Debe tener alta tolerancia de hábitat, pero con preferencia por
  silíceo/ácido/húmedo y bosque maduro.
- La madurez del bosque es importante, pero por ahora debe quedar como nota o
  futuro feature GIS.

## Craterellus cornucopioides

Nombre de ficha: la trompeta. Nombre científico: `Craterellus cornucopioides`.

Páginas revisadas: PDF página 5.

Conclusión para v0:

- Especie tardía, de bosques húmedos y frondosos, sensible al calor alto.
- Prefiere suelos silíceos/ácidos/neutros y calizos descarbonatados, aunque la
  ficha destaca gran adaptación edáfica.
- Aparece en otoño avanzado y puede mantenerse hasta invierno en condiciones
  húmedas.

Señales estructurables:

- Vegetación/host:
  - masas mixtas de haya y abeto;
  - bosques mixtos con hayas, robles, pino silvestre;
  - robledales, hayedos, alcornocales;
  - especialmente encinares de serraladas litoral y prelitoral.
- Suelo:
  - `soil_siliceous`;
  - `soil_acidic`;
  - `soil_neutral`;
  - calizos descarbonatados;
  - tolerancia a ligeramente básicos o carbonatados.
- Hábitat:
  - bosques húmedos y frondosos;
  - ambientes de litoral/prelitoral húmedo;
  - parece favorecer humedad persistente.
- Calendario:
  - en cotas superiores a 1.200 m puede aparecer desde final de agosto;
  - fructificación generalizada desde primera semana de octubre;
  - noviembre y diciembre buenos meses en alcornocales, encinares y robledales
    húmedos de la franja litoral;
  - puede conservarse hasta entrado el invierno.
- Meteorología:
  - tolera bien el frío;
  - no tolera temperaturas demasiado cálidas;
  - la ficha menciona perjuicio cerca de 25 °C.

Recomendación de modelo:

- `feature_moist_forest`, `forest_beech`, `forest_fir`,
  `forest_deciduous_broadleaf`, `forest_holm_oak` y `forest_cork_oak` son
  señales útiles.
- La sensibilidad a calor debería ser un candidato meteorológico documentado,
  pero no convertir aún 25 °C en umbral duro sin contrastar observaciones.

## Hygrophorus latitabundus

Nombre de ficha: la llenega negra. Nombre científico: `Hygrophorus latitabundus`.

Páginas revisadas: PDF página 6.

Conclusión para v0:

- Especie mediterránea, tardía, calcícola estricta según la ficha.
- Asociada a pinares calcáreos de `Pinus sylvestris`, `Pinus nigra` y
  `Pinus halepensis`, con presencia de encinas/robles en masas variadas.
- Rechaza temperaturas elevadas y se favorece con otoño avanzado.

Señales estructurables:

- Vegetación/host:
  - `Pinus sylvestris`;
  - `Pinus nigra`;
  - `Pinus halepensis`;
  - en masas con roures y encinas.
- Suelo:
  - `soil_calcareous`;
  - `soil_basic`;
  - preferencia fuerte, casi requisito.
- Hábitat:
  - pinares calcáreos;
  - vertientes umbrías en octubre por encima de 1.000 m;
  - progresivamente baja a pinares de pino blanco por debajo de 600 m en
    diciembre.
- Calendario:
  - otoño avanzado como época preferente;
  - puede durar hasta Navidad en rincones cálidos;
  - octubre por encima de 1.000 m;
  - noviembre baja de cota;
  - diciembre en pinares bajos de pino blanco.
- Meteorología:
  - intolerante a temperaturas elevadas;
  - una calurosa en plena florada la estropea rápidamente;
  - cuerpos fructíferos invadidos por mohos si la temperatura sube.

Recomendación de modelo:

- Esta especie sí justifica usar suelo calcáreo/básico como condición fuerte.
- Buen caso de desplazamiento altitudinal estacional: de cota alta en octubre a
  pinares bajos en diciembre.

## Russula virescens

Nombre de ficha: la llora verde. Nombre científico: `Russula virescens`.

Páginas revisadas: PDF página 7.

Conclusión para v0:

- Especie de frondosas, zonas húmedas y suelos silíceos más o menos ácidos,
  aunque más fértiles que los de algunas especies mediterráneas.
- En Catalunya no se comporta como especie continua de verano por la sequedad
  mediterránea; la ficha diferencia bien áreas atlánticas del norte peninsular y
  comportamiento local.

Señales estructurables:

- Vegetación/host:
  - castañares;
  - encinares;
  - alcornocales;
  - algunos robledales;
  - hayedos.
- Suelo:
  - `soil_siliceous`;
  - `soil_acidic`;
  - nota de suelos más fértiles;
  - preferencia por zonas herbosas/húmedas.
- Hábitat:
  - árboles de frondosas;
  - lugares húmedos;
  - brecina/brezos como acompañantes.
- Calendario:
  - en zonas atlánticas puede aparecer de junio a noviembre;
  - en Catalunya suele hacer una florada entre 5 de junio y 5 de julio en
    castañares, hayedos y abedulares;
  - se reactiva desde final de agosto por encima de 1.000 m;
  - a final de septiembre baja hacia bosques litorales;
  - en alcornocales es irregular y depende de lluvias húmedas de levante.

Recomendación de modelo:

- `soil_siliceous` y `soil_acidic` con `feature_moist_forest` son señales
  relevantes.
- No usar como especie puramente mediterránea seca.
- El concepto de “suelo fértil” debería quedar como nota o futuro feature, no
  como parámetro v0 si no existe catálogo.

## Hygrophorus marzuolus

Nombre de ficha: el marçot. Nombre científico: `Hygrophorus marzuolus`.

Páginas revisadas: PDF página 8.

Conclusión para v0:

- Especie primaveral, montana/subalpina, asociada a coníferas y suelos silíceos
  ligeramente a moderadamente ácidos.
- La altitud y la fenología son muy importantes.
- Aparece también en invierno en algunos enclaves concretos más bajos, pero la
  ventana operativa principal es primavera de montaña.

Señales estructurables:

- Vegetación/host:
  - `Pinus sylvestris`;
  - `Abies alba`;
  - `Pinus uncinata`;
  - muy raramente junto a roble de hoja grande y haya.
- Suelo:
  - `soil_siliceous`;
  - `soil_acidic`;
  - calizos descarbonatados por encima de 1.400 m;
  - preferencia por gres silíceo en terrenos pizarrosos según la ficha.
- Hábitat:
  - bosques montanos/subalpinos de coníferas;
  - rincones frescos;
  - avetosas con arándano en final de temporada.
- Calendario:
  - enero-marzo en casos concretos entre 600 y 1.100 m;
  - desde primeros de abril en claros junto a pino rojo en Pirineo/Prepirineo;
  - se desplaza a 1.700 m o más desde primera semana de mayo;
  - final de temporada en primera mitad de junio en avetosas frescas.
- Altitud:
  - 600-1.100 m en apariciones invernales locales;
  - 1.400 m o más para sustratos calizos descarbonatados;
  - 1.700 m o más en mayo.

Recomendación de modelo:

- Muy buen candidato para predictor v0: temporada + altitud + conífera montana
  + suelo ácido/silíceo.
- No modelar como especie otoñal.

## Tuber melanosporum

Nombre de ficha: la tòfona negra. Nombre científico: `Tuber melanosporum`.

Páginas revisadas: PDF página 9.

Conclusión para v0:

- Especie hipogea de invierno, calcícola, asociada a encinas, carrascas, robles
  mediterráneos, avellano y matorrales calcícolas.
- No es directamente comparable al predictor de floradas visibles, pero es útil
  para confirmar que suelo calcáreo/básico y vegetación calcícola son señales
  ecológicas fuertes.

Señales estructurables:

- Vegetación/host:
  - carrasca/encina;
  - `Quercus ilex`;
  - `Quercus faginea`;
  - `Quercus humilis`;
  - `Quercus coccifera`;
  - `Corylus avellana`;
  - entorno con rosa silvestre, enebro, boj o aliaga.
- Suelo:
  - `soil_calcareous`;
  - `soil_basic`;
  - pedregosidad/textura idónea mencionada en la ficha.
- Hábitat:
  - matorral o bosque claro calcícola;
  - zonas con plantas acompañantes de entorno calcáreo.
- Calendario:
  - se recolecta desde primera semana de diciembre;
  - enero es el mes con mejores cosechas;
  - puede continuar hasta marzo.
- Meteorología:
  - si el verano precedente fue seco, conviene buscar cerca de matorrales como
    enebro o boj según la ficha.

Recomendación de modelo:

- Mantenerla fuera o separada del predictor de setas epigeas si el objetivo
  inicial es florada visible.
- Si se incluye, necesita tipo de modelo diferente: hipogea, ayuda animal o
  señales indirectas.

## Lactarius deliciosus

Nombre de ficha: el pinetell. Nombre científico: `Lactarius deliciosus`.

Páginas revisadas: PDF página 10.

Conclusión para v0:

- Especie asociada a pinos, muy amplia y poco exigente con el suelo, aunque las
  mayores producciones se indican sobre sustratos silíceos permeables y poco
  compactados.
- No debe tratarse como calcífuga estricta ni calcícola estricta.
- Buen ejemplo de preferencia blanda, no filtro duro.

Señales estructurables:

- Vegetación/host:
  - `Pinus sylvestris`;
  - `Pinus pinaster`;
  - `Pinus pinea`;
  - `Pinus halepensis`;
  - `Pinus radiata`;
  - `Pinus nigra`;
  - `Pinus uncinata`;
  - a veces madroño y enebro como acompañantes.
- Suelo:
  - variable;
  - preferencia productiva por `soil_siliceous`, permeable y poco compactado;
  - puede aparecer en calizos prepirenaicos y en terrenos silíceos litorales.
- Hábitat:
  - pinares de todo tipo;
  - sotobosque desde boj y brecina hasta brezos;
  - muy polivalente.
- Calendario:
  - agosto en áreas localizadas del Pirineo por encima de 1.700 m, cerca de
    pino negro y en umbrías;
  - septiembre baja a 1.400-1.500 m;
  - entre 1 y 15 de octubre ronda 1.200 m;
  - noviembre se acerca a 300 m;
  - después puede abarcar la costa hasta la línea de mar;
  - excepcionalmente en junio a 1.400-1.700 m.

Recomendación de modelo:

- Host pine debe ser la señal principal.
- Suelo silíceo debería ser preferencia de producción, no requisito.
- Necesita lógica de desplazamiento estacional por altitud.

## Lactarius sanguifluus

Nombre de ficha: el rovelló. Nombre científico: `Lactarius sanguifluus`.

Páginas revisadas: PDF página 11.

Conclusión para v0:

- Rovellón calcícola, asociado a varias especies de pinos.
- El texto es mucho más fuerte con el suelo que en `Lactarius deliciosus`: los
  terrenos calcáreos son una señal central y la ausencia en zonas silicícolas se
  menciona claramente.
- Limitado por suelo y temperatura.

Señales estructurables:

- Vegetación/host:
  - `Pinus sylvestris`;
  - `Pinus nigra`;
  - `Pinus halepensis`;
  - preferencia por pinares en áreas calcáreas.
- Suelo:
  - `soil_calcareous`;
  - `soil_basic`;
  - no buscar en suelos silíceos ni en suelos calizos descarbonatados o
    acidificados según la ficha.
- Hábitat:
  - pinares calcáreos;
  - plantas acompañantes calcícolas: boj, brezo de invierno, romero, globularia,
    oreja de oso, lavanda.
- Calendario:
  - septiembre en el Pirineo con pino rojo a 1.400-1.700 m;
  - a partir de 15-20 de septiembre baja a 1.000-1.200 m;
  - durante última semana de octubre se sitúa en torno a 600-700 m;
  - puede aparecer a 300-400 m con pino blanco;
  - en noviembre/diciembre llega a franja litoral.
- Altitud:
  - difícilmente sobrepasa 1.600-1.700 m.

Recomendación de modelo:

- A diferencia de `L. deliciosus`, aquí sí se justifica suelo calcáreo/básico
  como señal fuerte.
- Separar claramente perfiles de `L. deliciosus` y `L. sanguifluus`.

## Lactarius vinosus

Nombre de ficha: el vinader. Nombre científico: `Lactarius vinosus`.

Páginas revisadas: PDF página 12.

Conclusión para v0:

- Especie termófila mediterránea de baja altitud, asociada a pinos de tierra
  baja y sustratos silíceos.
- El autor advierte que no conviene hacer mensajes absolutos, pero la tendencia
  hacia suelos silíceos y pinos mediterráneos es clara.

Señales estructurables:

- Vegetación/host:
  - `Pinus pinea`;
  - `Pinus halepensis`;
  - `Pinus pinaster`;
  - a menudo compartiendo hábitat con alcornoque o encina.
- Suelo:
  - `soil_siliceous`;
  - tendencia acidófila;
  - ejemplos de sauló, licorella y sustratos silíceos;
  - el texto considera extrema la versión calcárea/básica y no la confirma para
    el autor.
- Hábitat:
  - tierra baja mediterránea;
  - claros luminosos;
  - pinares mezclados con frondosas mediterráneas.
- Calendario:
  - segunda semana de octubre en puntos elevados de 500-700 m;
  - baja progresivamente durante noviembre;
  - primera quincena de diciembre entre nivel del mar y 500 m;
  - desde entonces hasta enero por debajo de 200 m en solanas costeras.

Recomendación de modelo:

- Host pine mediterráneo + suelo silíceo + baja altitud son señales principales.
- No tratarlo como calcícola salvo que observaciones locales lo demuestren.

## Lactarius salmonicolor / Lactarius quieticolor

Nombre de ficha: rovellons d'avet i pi negre. Nombres científicos:
`Lactarius salmonicolor`, `Lactarius quieticolor`.

Páginas revisadas: PDF página 13.

Conclusión para v0:

- La ficha agrupa dos rovellones de alta montaña, pero separa host y comportamiento:
  `L. salmonicolor` con abeto blanco y `L. quieticolor` con pino negro.
- La señal principal no es suelo fino, sino host + altitud + bosque húmedo/ácido.

Señales estructurables:

- Vegetación/host:
  - `L. salmonicolor`: `Abies alba`;
  - `L. quieticolor`: `Pinus uncinata`.
- Suelo:
  - suelos silíceos o calizos descalcificados/descarbonatados;
  - en la práctica suelos casi siempre ácidos en áreas notorias de Pirineo y
    Prepirineo;
  - la acidez se asocia a hojarasca de coníferas, escorrentía y alta humedad.
- Hábitat:
  - avetosas y pinares de pino negro;
  - rincones húmedos, cerca de arroyos para rovellón de abeto;
  - versantes umbríos;
  - el rovellón de pino negro prefiere masas menos cerradas, árboles más
    dispersos y entrada de luz/herbáceas.
- Calendario:
  - rovellón de abeto: puede aparecer primera semana de julio; se hace más
    presente desde final de julio; producción general desde 10-15 de agosto;
    se mantiene hasta 5-10 de octubre y luego decae.
  - rovellón de pino negro: desde 10-15 de agosto por encima de 1.900 m; desde
    primera semana de septiembre baja hasta 1.700 m.
- Meteorología:
  - la ficha recomienda estar atento desde junio.

Recomendación de modelo:

- Separar ambos perfiles si se quiere precisión: host y calendario difieren.
- Usar `host_abies_alba`, `host_pinus_uncinata`, `forest_fir`,
  `forest_subalpine_pine`, `soil_acidic` y `soil_siliceous`.

## Calocybe gambosa

Nombre de ficha: el moixernó. Nombre científico: `Calocybe gambosa`.

Páginas revisadas: PDF página 14.

Conclusión para v0:

- Especie primaveral de prados, pastos, claros y bordes de bosque, siempre sobre
  sustratos calcáreos según la ficha.
- No es una especie de bosque cerrado; el hábitat abierto es central.

Señales estructurables:

- Vegetación/hábitat:
  - pastos;
  - prados herbosos;
  - claros de bosques esclerófilos;
  - generalmente pastoreados;
  - presencia de enebro o endrino como señal visual de búsqueda.
- Suelo:
  - `soil_calcareous`;
  - `soil_basic`.
- Calendario:
  - final de marzo en zonas bajas de 500-900 m;
  - avanza con la primavera hasta 1.800-1.900 m alrededor de San Juan o inicio de
    julio;
  - puntualmente en otoños muy lluviosos.
- Altitud:
  - 500-900 m al inicio;
  - hasta 1.800-1.900 m a final de primavera/inicio de verano.

Recomendación de modelo:

- Necesita categorías de hábitat abierto: prado, pasto, claro, borde.
- `soil_calcareous` debe ser señal fuerte.
- No modelarlo por host arbóreo.

## Macrolepiota procera

Nombre de ficha: l'apagallums. Nombre científico: `Macrolepiota procera`.

Páginas revisadas: PDF página 15.

Conclusión para v0:

- Especie saprófita y cosmopolita, ligada a materia orgánica y hábitats muy
  diversos.
- La preferencia parece más por riqueza orgánica que por pH.
- Puede aparecer desde primavera lluviosa hasta otoño, con movimiento de cota.

Señales estructurables:

- Hábitat:
  - cualquier tipo de bosque, de pinares a hayedos;
  - encinares, robledales;
  - márgenes, claros;
  - prados y matorrales;
  - jardines enriquecidos con nitrógeno.
- Suelo:
  - puede aparecer sobre silíceos y calcáreos;
  - prefiere rincones/bosques ricos en materia orgánica;
  - usar `soil_organic_rich` o `soil_humus_rich` si el catálogo lo permite.
- Calendario:
  - si la primavera es lluviosa, floradas tímidas entre mayo y junio en tierra
    baja y montaña media;
  - desde final de agosto en cotas 1.400-1.600 m del Pirineo;
  - baja de altitud y cerca del litoral aparece hacia inicio de octubre.

Recomendación de modelo:

- No usar suelo ácido/calcáreo como filtro.
- Modelar como saprófita de materia orgánica, claros/bordes y hábitats variados.
- Puede ser buena especie de “oportunidad general” tras humedad adecuada.

## Cantharellus lutescens

Nombre de ficha: el camagroc. Nombre científico: `Cantharellus lutescens`.

Páginas revisadas: PDF página 16.

Conclusión para v0:

- Especie tardía, resistente al frío, de ambientes húmedos, coníferas y bosques
  mixtos.
- Muy amplia en sustrato: desde calcáreos de Catalunya Central hasta silíceos
  arenosos costeros.
- La humedad/umbría parece más importante que el pH.

Señales estructurables:

- Vegetación/host:
  - coníferas;
  - bosques mixtos de coníferas y planifolios;
  - `Pinus sylvestris`;
  - `Pinus nigra`;
  - `Pinus halepensis`;
  - `Pinus pinaster`;
  - `Pinus pinea`.
- Suelo:
  - variable;
  - calcáreo a silíceo;
  - no usar pH como filtro duro.
- Hábitat:
  - ambientes muy húmedos;
  - obagas;
  - clarianas de bosque;
  - vertientes secas/soleadas se citan como sitios donde no debe buscarse;
  - pinares montanos y también tierra baja húmeda.
- Calendario:
  - desde septiembre hasta mitad de febrero;
  - a principios de septiembre se ve en cotas 1.300-1.400 m en obagas de mitad
    norte;
  - baja progresivamente, en pinares de pinassa hacia final de octubre;
  - en pinares bajos a partir de noviembre;
  - si se mantiene la humedad en invierno, puede durar hasta febrero.
- Meteorología:
  - resiste frío;
  - depende de ambiente húmedo persistente.

Recomendación de modelo:

- Priorizar humedad, obaga, bosque de coníferas/mixto y estación tardía.
- No sobreponderar litología.

## Marasmius oreades

Nombre de ficha: la carrereta. Nombre científico: `Marasmius oreades`.

Páginas revisadas: PDF página 17.

Conclusión para v0:

- Especie de prados, céspedes y zonas herbosas, formando corros o líneas.
- La humedad del suelo y el vigor/verdor de la hierba son señales visuales
  centrales.
- No depende de bosque ni de árbol host.

Señales estructurables:

- Hábitat:
  - céspedes;
  - prados;
  - jardines;
  - zonas herbosas;
  - líneas, corros o semicírculos;
  - puede compartir hábitat con `Calocybe gambosa` y Lycoperdon/Vascellum.
- Suelo:
  - el texto destaca enriquecimiento por raíces/restos vegetales y humedad;
  - no hay señal clara de pH;
  - `soil_moist`, `soil_organic_rich` o hábitat de prado son mejores que
    litología.
- Calendario:
  - se asocia a primavera, pero también puede aparecer en verano y otoño;
  - los corros se dibujan durante buena parte del año;
  - la hierba muy verde en invierno/primavera o más verde que el entorno en
    verano puede indicar micelio activo.

Recomendación de modelo:

- Necesita clase de hábitat `grassland/meadow/lawn`.
- No usar GIS forestal como requisito.
- Buena candidata para observations-driven calibration porque puede depender
  mucho de microhábitat local.

## Tricholoma terreum

Nombre de ficha: el fredolic. Nombre científico: `Tricholoma terreum`.

Páginas revisadas: PDF página 18.

Conclusión para v0:

- Especie tardía y de frío, ligada a pinares y abetales.
- Aparece sobre suelos calcáreos y silíceos, aunque la ficha indica que los
  calcáreos parecen más favorables.
- Prefiere lugares planos más que pendientes, y claros/bordes musgosos también
  favorecen.

Señales estructurables:

- Vegetación/host:
  - pinares;
  - abetales;
  - pinassa más productiva;
  - pino rojo y pastos asociados a ejemplares más robustos.
- Suelo:
  - `soil_calcareous` como tendencia favorable;
  - también `soil_siliceous`;
  - no filtro duro por pH.
- Hábitat:
  - lugares planos;
  - claros y bordes de caminos;
  - zonas musgosas;
  - bosques protegidos del frío cerca de la costa en invierno.
- Calendario:
  - puede aparecer en mayo en piso montano si abril fue húmedo y fresco;
  - época principal: octubre y enero;
  - en cotas altas por encima de 1.500 m desde inicio de octubre;
  - baja con el avance del otoño;
  - en costa protegida del frío puede fructificar hasta marzo;
  - algunos años frescos puede aparecer en bosques subalpinos en agosto y
    septiembre.

Recomendación de modelo:

- Host/forest de coníferas + frío/otoño avanzado son señales clave.
- Suelo calcáreo puede mejorar aptitud, pero no bloquear silíceo.
- Añadir advertencia de confusión con especies tóxicas solo en UI/información,
  no en predictor.

## Morchella esculenta / Morchella conica

Nombre de ficha: la múrgola. Nombres científicos: `Morchella esculenta`,
`Morchella conica`.

Páginas revisadas: PDF página 19.

Conclusión para v0:

- Especie/grupo primaveral, muy condicionado por alteraciones del suelo,
  sustratos removidos, quemados, márgenes, huertos, obras, carreteras y bosque
  de ribera.
- Indiferencia edáfica total según la ficha: aparece en calizos y silíceos.
- No debe modelarse con pH, sino con estación, perturbación, humedad y tipo de
  hábitat.

Señales estructurables:

- Vegetación/hábitat:
  - bosques de ribera;
  - márgenes;
  - huertos;
  - zonas de obras;
  - cunetas/carreteras/vías;
  - terrenos alterados, removidos o quemados;
  - también bosques maduros de pino rojo, pino negro o abeto;
  - matorrales, pastos y bosque mixto.
- Suelo:
  - indiferente: calizo y silíceo;
  - sustrato alterado/removido/quemado es más importante que pH.
- Calendario:
  - tradicionalmente primavera;
  - en litoral cálido puede aparecer desde finales de febrero/invierno;
  - en cotas elevadas del Pirineo puede llegar a junio o primeras semanas de
    julio;
  - marzo: 300-400 m;
  - abril: sube hasta 1.600-1.700 m;
  - mayo: 1.400-1.800 m;
  - junio: hasta 2.000 m en pino negro.

Recomendación de modelo:

- Necesita `feature_disturbed_soil`, `feature_burned_area`,
  `feature_riparian_moisture`, `habitat_woodland_edge` o similares.
- No usar suelo ácido/calcáreo.
- Es candidata fuerte para observaciones + GIS de incendios/alteraciones si se
  dispone de capas fiables.

## Lepista nuda

Nombre de ficha: la pimpinella morada. Nombre científico: `Lepista nuda`.

Páginas revisadas: PDF página 20.

Conclusión para v0:

- Especie saprófita de restos orgánicos y suelos ricos en humus, muy amplia en
  bosque y borde.
- Puede aparecer en calcáreos ricos en humus y en silíceos.
- La materia orgánica parece más importante que el pH.

Señales estructurables:

- Vegetación/hábitat:
  - bosques de coníferas;
  - pinares de `Pinus sylvestris`, `Pinus nigra`, `Pinus halepensis`;
  - planifolios como robledales y encinares;
  - márgenes de caminos;
  - prados;
  - corros.
- Suelo:
  - `soil_humus_rich`;
  - `soil_organic_rich`;
  - calcáreos ricos en humus;
  - silíceos;
  - todo tipo de suelos si hay materia orgánica suficiente.
- Hábitat:
  - hojarasca;
  - restos vegetales;
  - piñas en descomposición;
  - base del pie con restos adheridos, señal de suelo orgánico.
- Calendario:
  - otoño avanzado;
  - floradas primaverales si ha llovido;
  - por encima de 1.500-1.600 m puede aparecer desde septiembre;
  - en piso montano desde octubre;
  - por debajo de 600-700 m desde noviembre;
  - en tierra baja puede mantenerse hasta invierno.

Recomendación de modelo:

- Modelar como saprófita generalista de materia orgánica, no por host.
- Poner peso a `soil_humus_rich`/`soil_organic_rich` y estación fría-húmeda.
- No usar pH como filtro duro.

## Conclusiones para catálogos y GIS

### Suelos amplios suficientes para v0

El documento justifica mantener como mínimo estas categorías:

- `soil_acidic`
- `soil_siliceous`
- `soil_calcareous`
- `soil_basic`
- `soil_neutral`
- `soil_moist`
- `soil_waterlogged` o humedad persistente, si se usa para ribera/obaga
- `soil_humus_rich`
- `soil_organic_rich`
- `soil_sandy` o textura arenosa/permeable
- `soil_variable` o ausencia de filtro duro, si se decide añadir una categoría
  explícita de indiferencia edáfica

No parece necesario que el predictor v0 use litologías finas como preferencia de
especie, salvo como trazabilidad de cómo se infirió el suelo amplio.

### Vegetación y hosts prioritarios

El GIS debe ayudar a identificar al menos:

- pinares genéricos;
- `Pinus sylvestris`;
- `Pinus uncinata`;
- `Pinus nigra`;
- `Pinus halepensis`;
- `Pinus pinaster`;
- `Pinus pinea`;
- `Abies alba`;
- `Fagus sylvatica`;
- encinares;
- alcornocales;
- robledales;
- castañares;
- abedulares;
- prados/pastos;
- bosques de ribera;
- claros/bordes.

### Rasgos de hábitat prioritarios

Las fichas justifican estos rasgos:

- bosque maduro;
- bosque húmedo;
- obaga/umbría;
- solana costera o tierra baja cálida;
- ribera;
- claro de bosque;
- borde de camino;
- prado/pasto/césped;
- terreno removido;
- zona quemada;
- suelo rico en materia orgánica;
- matorral mediterráneo;
- matorral calcícola;
- sotobosque de brezos/jaras;
- presencia de arándano en alta montaña.

Algunos de estos rasgos no tienen aún una fuente GIS fiable. Deben quedar como
nota o candidato futuro hasta disponer de capa o evidencia local.

### Meteorología y fenología

El documento rara vez da umbrales numéricos robustos. Lo útil para v0 es:

- lluvia o tormentas antes de florada;
- contraste térmico después de lluvia;
- humedad persistente;
- enfriamiento otoñal;
- sensibilidad al calor para especies tardías como trompeta o llenega negra;
- desplazamiento de cota según avanza la temporada;
- primavera húmeda para especies primaverales y algunas saprófitas.

No convertir estos textos en milímetros, días exactos o puntuaciones sin
observaciones locales. Sí se pueden registrar como hipótesis meteorológicas
documentadas para que el `observation_context_builder` las contraste.

## Implicaciones para el seed experimental

El JSON experimental derivado de literatura debería guardar, por especie:

- `source_id`: `marc_estevez_species_pdf`;
- `source_pages`: páginas del PDF revisadas;
- `scientific_name`;
- `common_names`;
- `season_notes`;
- `altitude_notes`;
- `host_tendency_ids`;
- `forest_tendency_ids`;
- `soil_tendency_ids`;
- `habitat_feature_ids`;
- `weather_hypotheses`;
- `confidence`: por ejemplo `literature_visual_review`;
- `review_status`: `needs_review`;
- `model_notes`: texto breve de cómo usarlo sin convertirlo en regla dura.

No debe copiar textos largos de la fuente. Debe conservar solo hechos ecológicos
normalizados y notas propias de revisión.
