# Revisión de perfiles de especies para el Mapa de predicción

**Fecha de corte: 13/09/2026. Revisión bibliográfica y segunda pasada completadas.
Decisiones posteriores incorporadas y fichas locales actualizadas; motor conectado en preview.**

Documento vinculado a la [especificación central](prediction-map-specification-es.md).
La referencia operativa de esta revisión son las **21 fichas locales editables**
de `docker-data/mushroom-data/mushroom_profiles.json`, junto al catálogo local
`docker-data/mushroom-data/mushroom_reference_catalogs.json`. No se han tomado
las semillas del repositorio como sustituto de esos datos.

Se comprobó en el contenedor local `rainmapper-local-rainmapper-ha-ui-1` que
`default_store()` utiliza `/share/rainmapper/mushroom-data`, montado desde
`docker-data`, y que el archivo de perfiles tiene la misma huella que el
revisado. El handler de perfiles carga ese almacén para las vistas V0/Enriched;
no se han confundido los valores guardados con posibles valores derivados de
la pantalla. El [anexo de comprobaciones](../reports/prediction-map-species-literature-review-2026-09-13.json)
registra rutas, huellas y localizadores del código consultado.

## 1. Decisiones operativas vigentes del usuario — 13/09/2026

**Estas decisiones sustituyen las propuestas más restrictivas de la revisión.**
La evidencia y las discrepancias de §2–§7 se conservan como soporte y para una
revisión futura; no son bloqueos que obliguen a resolver toda la bibliografía
antes de actualizar las fichas. La segunda pasada de §9 precede a estas decisiones.

1. **Ventanas amplias por ficha.** Para meses de fructificación, hospedadores/
   hábitats, pH y altitud mínima/máxima se utilizará la envolvente más amplia
   disponible entre las fuentes examinadas. Se acepta como configuración
   operativa revisable; no se presenta como tolerancia universal demostrada.
2. **Orientación sin requisito.** Ninguna especie se excluirá por orientación
   en esta fase. Se conservan los datos actuales; su posible uso se revisará
   más adelante si los resultados lo requieren. Esta decisión no cambia por
   sí sola variables o pesos del Predictor ya entrenado.
3. **Salmonicolor/quieticolor permanece unido.** Una única ficha con su ID
   actual, ampliando las ventanas y relaciones para cubrir ambos. No se crean
   subperfiles ni se separan observaciones o modelos en esta fase.
4. **Rovelló: propuesta histórica, reemplazada por filas separadas (§8.2).** Las ventanas se
   amplían en cada ficha existente. El usuario elige agrupar las
   observaciones al preparar el entrenamiento del conjunto «Rovelló», conservando
   sus identificaciones originales. Una predicción conjunta, sin fusionar las
   fichas ni duplicar porcentajes. Decisión y situación comprobada en §8.2;
   implementación y entrenamiento pendientes.

### Cómo aplicar «la ventana más amplia»

| Campo | Regla operativa acordada |
|---|---|
| Meses | Unión de los meses citados como principales, secundarios o posibles. Conservar la distinción principal/secundario; ambos admiten compatibilidad. No rellenar meses intermedios que ninguna fuente menciona. |
| Hospedadores y hábitats | Unión de las asociaciones/contextos descritos, como alternativas. No exigir todos a la vez. Mantener la generalización GIS aceptada y distinguir especies de prado de las que necesitan árboles. |
| Altitud min/max | Menor mínimo y mayor máximo utilizables de las fuentes; incorporar cotas publicadas que amplíen lo anterior. Los ceros provisionales y los `null` no son límites. Si falta un extremo, queda desconocido, sin inventarlo. No recalcular óptimos automáticamente. |
| pH min/max | Crear ambos campos en JSON y en **Especies → Ecología → Suelos**, con guardado, lectura e importación/exportación. Usar los extremos más amplios de información de suelo utilizable para esa ficha; conservar fuente y carácter provisional. Un óptimo de cultivo micelial no se convierte en límite del suelo. Si no hay cifras utilizables, campo vacío y sin veto por pH. |
| Revisión posterior | Anotar la procedencia de la ampliación y que estas ventanas, así como el uso de orientación, podrán revisarse con los resultados del mapa. No exigir cerrar esa revisión futura ahora. |

La amplitud acepta diferencias regionales de las fuentes. No convierte una
cifra de temperatura, una parcela sin la especie o una etiqueta de laboratorio
en un extremo válido de otra variable. Los rangos del catálogo de suelos
siguen siendo referencias del catálogo: derivar un pH de especie a partir de
ellos sería una aproximación adicional que debe identificarse como tal.

La lista principal del mapa utilizará estas ventanas operativas. Los datos
cartográficos ausentes siguen siendo desconocidos; no prueban incompatibilidad.
**Decisión posterior del 13/09:** sin hospedadores identificados en el punto,
la lista queda vacía; con arbolado pero sin una coincidencia admitida para una
especie que lo requiere, no predecir esa especie. Ficha «pino negro» acepta GIS
«pino negro» o «pinos», pero no «pino rojo». Ficha «pinos» acepta cualquier
especie del género. No equiparar hermanos taxonómicos ni géneros por familia.
Esto se aplica igual a todas las fichas y no altera sus observaciones.
El criterio de amplitud no cambia por sí solo retardos de lluvia, puntuaciones
ni coeficientes meteorológicos del motor existente.

### 1.1. Aplicación local de ventanas y campos pH — 13/09/2026

Comprobación posterior solicitada por el usuario: las ventanas se aplicaron,
pero entonces los valores de pH seguían pendientes; las afinidades de suelo y litología
de las fichas conservaron sus valores anteriores. Esto no equivale a haber
trasladado toda la revisión ecológica a los datos. Véase la
[auditoría de aplicación](../reports/prediction-map-species-application-audit-2026-09-13.md).

Aplicadas las ventanas a las **21 fichas locales**, manteniendo sus IDs,
nombres, orientaciones, observaciones, coeficientes meteorológicos y pesos
existentes. Se ampliaron meses en ocho fichas y cambiaron extremos de altitud
en trece, incluyendo extremos desconocidos. Se añadieron **25 relaciones de
plantas y 12 de tipos de bosque**; los rasgos de hábitat existentes ya recogían
los IDs de la normalización de Marc y se conservaron.

El [registro exacto antes/después](../reports/prediction-map-species-windows-2026-09-13.json)
contiene las fuentes por ficha, huellas, validación y rutas de las dos copias
`.keep.json`. Las 114 entradas anteriores del catálogo local se conservaron;
se añadió `host_eucalyptus_spp` para representar el género citado por Sporas
para *C. cibarius* sin asignarlo a una especie concreta de eucalipto. Catálogo
local: 115 entradas. Las semillas de perfiles/catálogos del repo no se sustituyeron.

Las nuevas relaciones son secundarias/alternativas. Sus números de afinidad
se guardan como **0 provisional**, con `v0_placeholder=true`: no representan
un peso medido ni incompatibilidad. Conservan `source_ids` visibles; la
procedencia conjunta y la decisión revisable están en
`metadata.ecological_window_review`. La siguiente integración debe consumir
la relación cualitativa y respetar esa distinción.

**pH implementado:** `ecology.ph_min` y `ecology.ph_max`, opcionales, editables
en **Especies → Ecología → Suelos**, tanto V0 como Enriched. Rango admitido
0–14, mínimo ≤ máximo, vacío → `null`; JSON y formularios rechazan valores
inválidos. Inicialmente quedaron vacíos. La decisión posterior del usuario
aplica ahora los [21 rangos provisionales](prediction-map-species-ph-proposal-es.md)
como filtros revisables con setales conocidos; no son límites biológicos demostrados.

Se limpiaron nueve óptimos de altitud 0–0, dejándolos desconocidos. Los óptimos
numéricos restantes no se recalcularon. Los mínimos/máximos 0 de *Marasmius* y
*Tuber* pasaron a desconocidos, al igual que el mínimo de *Russula virescens*.
El mínimo provisional de *C. cornucopioides* se sustituyó por los 200 m
publicados por Sporas. Se conservaron los ceros que la fuente sí describe como
cota litoral. El validador admite extremos desconocidos y sigue rechazando
un orden invertido entre los valores conocidos.

Ventanas guardadas (meses 1–12; «—» significa desconocido). La tabla de §3
queda como **snapshot anterior**, para poder comparar:

| ID de ficha | Altitud min–max (m) | Meses principales | Meses secundarios |
|---|---:|---|---|
| `amanita_caesarea` | 100–1000 | 9, 10 | 6, 7, 8, 11 |
| `boletus_aereus` | 100–1200 | 9, 10 | 6, 7, 8, 11 |
| `boletus_edulis` | 600–2200 | 8, 9, 10 | 5, 6, 7, 11, 12 |
| `boletus_pinophilus` | 600–2300 | 6, 7, 8, 9 | 4, 5, 10, 11, 12 |
| `calocybe_gambosa` | 400–1900 | 4, 5, 6 | 3, 7 |
| `cantharellus_cibarius_sl` | 50–2300 | 6, 7, 8, 9, 10 | 4, 5, 11, 12 |
| `cantharellus_lutescens` | 0–1800 | 10, 11, 12 | 1, 2, 9 |
| `craterellus_cornucopioides` | 200–1600 | 10, 11, 12 | 1, 6, 7, 8, 9 |
| `hygrophorus_latitabundus` | 100–1600 | 10, 11, 12 | 1 |
| `hygrophorus_marzuolus` | 600–2000 | 4, 5 | 1, 2, 3, 6 |
| `lactarius_deliciosus` | 0–1900 | 9, 10, 11 | 6, 8, 12 |
| `lactarius_salmonicolor_quieticolor_group` | 750–2300 | 8, 9 | 7, 10, 11 |
| `lactarius_sanguifluus` | 0–1700 | 9, 10, 11 | 12 |
| `lactarius_vinosus` | 0–1010 | 10, 11, 12 | 1 |
| `lepista_nuda` | 0–1800 | 10, 11, 12 | 1, 2, 3, 4, 9 |
| `macrolepiota_procera` | 0–1800 | 9, 10 | 5, 6, 7, 8, 11, 12 |
| `marasmius_oreades` | —–— | 4, 5, 6 | 7, 8, 9, 10 |
| `morchella_elata_complex` | 0–2000 | 3, 4, 5 | 2, 6, 7 |
| `russula_virescens` | —–1600 | 6, 7, 9 | 8, 10, 11 |
| `tricholoma_terreum` | 0–1800 | 1, 10, 11, 12 | 2, 3, 5, 8, 9 |
| `tuber_melanosporum` | —–— | 1, 2, 12 | 3 |

Casos de amplitud provisional: 2.200 m de *B. edulis* conserva el extremo de
la normalización de Marc; 2.300 m de *B. pinophilus* conserva el extremo local.
El conjunto salmonicolor/quieticolor admite pinos/abetos, 750–2.300 m y
julio–noviembre: 750 m y noviembre proceden del registro regional recogido
en R12 §2.6, cuya limitación taxonómica sigue documentada. *L. vinosus* se
amplía hasta 1.010 m por producción positiva en esa cota (tabla 3 citada en
§4.14). Son ventanas operativas acordadas, revisables con resultados.

**Comprobaciones:** 26 pruebas dirigidas del mantenimiento y 22 de
validación/proyección/perfiles, sin errores; 42 editores renderizados en el
contenedor local (21 × V0/Enriched), controles de pH presentes en la página
HTTP 200 y cuatro huellas de código coincidentes con el worktree. Validación
del conjunto local: 0 errores y 89 avisos; no se confunde integridad de datos
con validación científica. HA local fue reconstruido/recreado en modo `serve`
con planificación desactivada, preservando sus volúmenes. No se reinició el
worker ni se publicaron imágenes o datos a HA real; no se lanzaron trabajos.

**Siguiente:** compatibilidad a partir de estas fichas, agrupación derivada
Rovelló y motor real compartido. El visor conserva las curvas simuladas.

## 2. Fuentes y fuerza de la evidencia

Se contrastan las fichas locales con:

| Conjunto | Uso en esta revisión | Límite |
|---|---|---|
| [Marc: conclusiones](literature/marc-estevez-species-conclusions-es.md) y [normalización](literature/marc-estevez-v0-source-normalized.json) | Origen de muchos campos y descripción regional por especie | Una normalización no es una segunda fuente independiente. El PDF escaneado permite comprobar la redacción original. |
| [Informe local de Sporas](literature/sporas_especies_informe_rainmapper.md) | Comparación de 15 fichas, tablas mensuales y descripciones | Síntesis divulgativa local; no equivale a validación científica de cada intervalo ni a una inspección nueva de la web. |
| [Revisiones por especie](literature/prediction/) | Las 21 revisiones correspondientes a las fichas; evidencia, limitaciones y bibliografía | Las afirmaciones de una revisión local se identifican como tales cuando el original no se ha contrastado directamente. |
| [Fenología y floradas](literature/fruiting-phenology/README.md) | Ocho notas y cinco PDF científicos locales | Distinguir comunidad/especie, clima/fructificación y resultado mensual/respuesta diaria. |
| Fuentes primarias señaladas al pie | Comprobaciones de los casos con mayor efecto sobre exclusiones, hospedadores y pH | No se certifica la totalidad de referencias externas citadas por los 21 informes. |

**Evidencia directa** significa texto, tabla o resultado primario comprobado.
**Síntesis concordante** significa coincidencia razonada entre documentos
locales; no convierte sus cifras en límites biológicos validados.
**Pendiente** identifica una propuesta que necesita contraste primario o
validación regional antes de activarse. «No se ha acreditado un límite» no
significa «se ha demostrado que no existe».

Las 21 fichas constan como `needs_review`. La nota raíz del JSON indica que
las afinidades numéricas provisionales y los campos meteorológicos/puntuación
aparcados no debían ser parámetros activos de v0. Esta revisión del fichero no
certifica qué campos consume cada modelo desplegado: eso requiere trazar el
consumidor antes de cualquier migración.

## 3. Comparación de altitud y calendario

Valores **del snapshot anterior a la aplicación de §1.1**, transcritos del archivo local. «Principal / secundaria»
son los campos existentes, no una recomendación nueva. Los rangos de Sporas
son los publicados en su informe local, no valores aprobados para sustituirlos.

| Especie / ID local | Altitud min–max (m) | Óptimo (m) | Meses principales / secundarios | Sporas: altitud y época de cabecera |
|---|---:|---:|---|---|
| Amanita caesarea (`amanita_caesarea`) | 100–1.000 | 300–1.000 | sep, oct / jun, jul, ago | 300–1.000; ago–oct |
| Boletus aereus (`boletus_aereus`) | 100–1.000 | 300–1.000 | sep, oct / jun, jul, ago, nov | 100–1.200; ago–oct |
| Boletus edulis (`boletus_edulis`) | 1.000–2.100 | 1.000–1.800 | ago, sep, oct / jul, nov | 600–1.800; sep–nov |
| Boletus pinophilus (`boletus_pinophilus`) | 1.000–2.300 | 1.200–1.700 | jun, jul, ago, sep / oct | 600–2.000; sep–nov y primavera |
| Calocybe gambosa (`calocybe_gambosa`) | 500–1.900 | 800–1.600 | abr, may, jun / mar, jul | 400–1.800; abr–jun |
| Cantharellus cibarius (`cantharellus_cibarius_sl`) | 400–2.300 | 800–1.700 | jun, jul, ago, sep, oct / may, nov, dic | 50–1.500; jun–oct (taxón s.l. no resuelto) |
| Cantharellus lutescens (`cantharellus_lutescens`) | 0–1.600 | 0–0 | oct, nov, dic / ene, feb, sep | 400–1.800; oct–dic |
| Craterellus cornucopioides (`craterellus_cornucopioides`) | 0–1.600 | 0–0 | oct, nov, dic / ene, ago, sep | 200–1.600; sep–nov |
| Hygrophorus latitabundus (`hygrophorus_latitabundus`) | 100–1.600 | 300–1.200 | oct, nov, dic / ene | Sin ficha equivalente en el informe |
| Hygrophorus marzuolus (`hygrophorus_marzuolus`) | 600–1.900 | 1.200–1.900 | abr, may / ene, feb, mar, jun | 900–2.000; feb–abr |
| Lactarius deliciosus (`lactarius_deliciosus`) | 0–1.900 | 0–0 | sep, oct, nov / jun, ago, dic | 100–1.600; sep–dic |
| Lactarius salmonicolor / quieticolor (`lactarius_salmonicolor_quieticolor_group`) | 1.200–2.300 | 1.200–1.200 | ago, sep / jul, oct | Sin ficha equivalente en el informe |
| Lactarius sanguifluus (`lactarius_sanguifluus`) | 0–1.700 | 300–1.200 | sep, oct, nov / dic | Sin ficha equivalente en el informe |
| Lactarius vinosus (`lactarius_vinosus`) | 0–700 | 100–700 | oct, nov, dic / ene | Sin ficha equivalente en el informe |
| Lepista nuda (`lepista_nuda`) | 0–1.800 | 0–0 | oct, nov, dic / ene, feb, mar, abr, sep | Sin ficha equivalente en el informe |
| Macrolepiota procera (`macrolepiota_procera`) | 0–1.800 | 0–0 | sep, oct / may, jun, ago, nov | 50–1.400; sep–nov |
| Marasmius oreades (`marasmius_oreades`) | 0–0 | 0–0 | abr, may, jun / jul, ago, sep, oct | Sin ficha equivalente en el informe |
| Morchella elata complex (`morchella_elata_complex`) | 0–2.000 | 800–1.800 | mar, abr, may / feb, jun, jul | Sin ficha equivalente en el informe |
| Russula virescens (`russula_virescens`) | 0–1.600 | 0–0 | jun, jul, sep / ago, oct, nov | Sin ficha equivalente en el informe |
| Tricholoma terreum (`tricholoma_terreum`) | 0–1.800 | 0–0 | ene, oct, nov, dic / feb, mar, may, ago, sep | Sin ficha equivalente en el informe |
| Tuber melanosporum (`tuber_melanosporum`) | 0–0 | 0–0 | ene, feb, dic / mar | Sin ficha equivalente en el informe |

Decisión vigente: tomar la envolvente amplia como ventana operativa, conservando
los valores y fuentes de esta tabla como referencia anterior a la edición. La
unión no se etiqueta como límite biológico universal. No usar la intersección
restrictiva entre fuentes. La asignación final de extremos se registrará antes
de escribir las fichas locales.

## 4. Propuestas por especie

En todos los apartados se conserva el ID actual. Estos apartados recogen la
revisión bibliográfica previa: sus reservas sobre ampliar intervalos quedan
sustituidas operativamente por §1. No es necesario resolver cada reserva antes
de aplicar las ventanas amplias. Los porcentajes del motor y las observaciones
no se modifican por esta actualización documental. Las cifras meteorológicas actuales quedan
inventariadas en el [anexo de datos](../reports/prediction-map-species-literature-review-2026-09-13.json).

### 4.1. Amanita caesarea

ID conservado: `amanita_caesarea`. **R01: [revisión por especie](literature/prediction/amanita_caesarea_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar quercíneas —encina, alcornoque y robles— y castaño; coinciden Marc, Sporas y R01. El trabajo de Daza utiliza aislados procedentes de ejemplares asociados a alcornoque/castaño, pero no valida un peso 0,95 o 0,85. Los arbustos acompañantes son contexto, no nuevos hospedadores demostrados.

**Altitud y época.** Mantener como descripción la preferencia termófila y de cotas bajas/medias de las fuentes locales. No elevar el mínimo a 300 m solo porque lo publique Sporas. Proponer noviembre como posibilidad regional de otoño suave; no convertirlo en mes principal nacional. Los 1.000 m actuales son ámbito típico descrito, no un techo científico universal. En el Pirineo a 2.000 m no hay respaldo aquí para recomendarla.

**pH y litología.** Preferencia ácida/silícea, tolerancia próxima a neutro y a calizas descalcificadas según Marc; registrar esa salvedad. pH numérico de campo: desconocido. El 6–7 de Daza es crecimiento en cultivo, no rango de fructificación.[^daza]

**Revisión propuesta.** No convertir las orientaciones N/NE/E/SE en requisito: el carácter cálido/abierto y la conservación de humedad dependen del sitio y de la época. Revisar el contraste con las solanas descritas por Sporas, sin invertir automáticamente la lista.

### 4.2. Boletus aereus

ID conservado: `boletus_aereus`. **R02: [revisión por especie](literature/prediction/boletus_aereus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar quercíneas y castaño, bosque cálido y relativamente abierto. R02 aporta contextos mediterráneos y estivales. Las jaras del sotobosque no autorizan por sí solas a copiar la asociación específica de *B. edulis–Cistus ladanifer* a esta especie.

**Altitud y época.** La ficha local y Marc se concentran en cotas bajas/medias; Sporas llega a 1.200 m. Proponer describir el intervalo actual como ámbito regional, manteniendo el extremo superior pendiente. Conservar junio–noviembre como conjunto de meses ya representados; distinguir el verano tras lluvias del máximo otoñal. No excluir julio/agosto por ser secundarios.

**pH y litología.** Mantener preferencia acidófila/silícea cualitativa. R02 no justifica pH o litología universales; `lith_limestone` desfavorable no debe convertirse en veto a una parcela cuyo suelo superficial sea apropiado.

**Revisión propuesta.** Mantener relaciones útiles y poner sus pesos, retardos 5–21 días y mínimos de lluvia en revisión cuantitativa; las descripciones de termofilia no validan esos números.

### 4.3. Boletus edulis

ID conservado: `boletus_edulis`. **R03: [revisión por especie](literature/prediction/boletus_edulis_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** La ficha concentra coníferas montanas, haya y abedul. Completar la revisión de robles/castaño citados en R03 y añadir como propuesta respaldada la asociación *Cistus ladanifer*, documentada en España.[^cistus] El catálogo de plantas y las relaciones de esta seta son dos mantenimientos distintos.

**Altitud y época.** Retirar 1.000 m como mínimo de exclusión nacional. Sporas publica 600–1.800 m y menciona cotas menores atlánticas; Marc describe descenso de cota con la estación. La página 2 original no formula un mínimo absoluto. No sustituir automáticamente por 600 m. Mantener julio local; la tabla de Sporas lo pone a cero pero Marc lo describe expresamente. Primavera y diciembre son propuestas de ventanas regionales a contrastar, no extensión indiscriminada.

**pH.** Afinidad ácida como preferencia, sin límites numéricos. El intervalo de parcelas de Ponce no es el rango de la especie. Admitir contexto calizo acidificado, que Marc menciona.[^marc]

**Revisión propuesta.** Revisar la discordancia 2.100/2.200 m y añadir procedencia a ambos valores antes de elegir. El preprint de hayedo sirve para estudiar funciones meteorológicas regionales; no para imponer su óptimo a todos los pinares españoles.

### 4.4. Boletus pinophilus

ID conservado: `boletus_pinophilus`. **R04: [revisión por especie](literature/prediction/boletus_pinophilus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener pinos como asociación principal. R04 recoge ocurrencias con *Picea*, *Abies* y castaño; proponer completar esas relaciones con su grado de evidencia, sin etiquetar toda ocurrencia en rodal como micorriza confirmada. No transferir automáticamente todos los hospedadores del complejo *B. edulis*.

**Altitud y época.** Revisar mínimo 1.000 y máximo 2.300 m como ámbito regional. La normalización de Marc conserva 1.700 m de máximo, mientras la página original describe aparición a distintas cotas según fecha. Sporas añade primavera y otoño avanzado: proponer mayo y noviembre como ventanas secundarias candidatas, revisar octubre como principal en los ámbitos que corresponda. Abril/diciembre necesitan aclarar el contraste tabla/texto antes de incorporarse.

**pH.** Preferencia acidófila/silícea descriptiva; no pH obligatorio. R04 §4.4 no acredita litología única. La caliza acidificada de Marc impide tratar una clase de roca como exclusión automática.

**Revisión propuesta.** No recomendar en costa solo por coincidencia genérica con pinos. Exigir ámbito ecológico aplicable y resolver la insuficiencia como no evaluable; no inventar un mínimo nuevo ni una excepción exclusiva para «pinícola».

### 4.5. Calocybe gambosa

ID conservado: `calocybe_gambosa`. **R05: [revisión por especie](literature/prediction/calocybe_gambosa_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar prados/herbazales y bordes frescos; no exigir árboles. El modo actual `trophic_saprotrophic_or_plant_associated_grassland` permite conservar la cautela sobre interacciones con herbáceas. Graziosi et al. (2025) documentan colonización de raíces y efectos sobre plantas, por lo que sería demasiado tajante reducir toda su ecología a descomposición sin interacciones. Esto no exige añadir una especie herbácea obligatoria al filtro.[^graziosi] La presencia de árboles en el jardín estudiado tampoco los convierte en hospedadores obligatorios.

**Altitud y época.** Mantener abril–junio y marzo/julio como posibilidades regionales. Sporas 400–1.800 frente a local 500–1.900 m es diferencia de descripción, no prueba de tolerancia exacta. La progresión primaveral de cota en Marc no justifica un filtro nacional idéntico en marzo y junio. Registros otoñales excepcionales de las síntesis no deben activar todo el otoño por defecto.

**pH.** Mantener tendencia caliza/básica de las fichas divulgativas, sin intervalo de exclusión. El descenso de pH del frente activo observado por Zotti es un efecto del hongo y no un rango necesario antes de la fructificación.[^calocybe]

**Revisión propuesta.** Hacer de la cobertura herbácea un contexto evaluable independiente del arbolado. No trasladar el pH de un medio de cultivo ni un mínimo de lluvia al filtro ecológico.

### 4.6. Cantharellus cibarius

ID conservado: `cantharellus_cibarius_sl`. **R06: [revisión por especie](literature/prediction/cantharellus_cibarius_sensu_lato_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Taxón y plantas.** Conservar explícitamente *sensu lato*. R06 advierte de especies próximas y de estudios norteamericanos que no representan sin más el taxón europeo. La ficha ya contiene varias frondosas y pinos; revisar *Picea* y otras asociaciones citadas con su ámbito, sin importar un conjunto mundial de hospedadores.

**Altitud y época.** El contraste local 400–2.300 / Sporas 50–1.500 m es demasiado grande para convertir cualquiera en veto. Marc describe contextos costeros húmedos y alta montaña. Proponer ámbitos diferenciados; conservar la ventana mayo–diciembre representada, distinguiendo meses habituales y colas regionales. «Casi todo el año» en una síntesis no significa doce meses igualmente aptos en cada punto.

**pH.** Preferencia ácida/silícea, pero el grupo y los contextos no permiten un intervalo numérico único. La afinidad negativa por caliza sigue siendo preferencia revisable, no exclusión geológica.

**Revisión propuesta.** No aplicar umbrales de un rebozuelo americano a todo el grupo. La humedad/microhábitat y la identidad taxonómica merecen evidencia separada; pH min/max quedan desconocidos.

### 4.7. Cantharellus lutescens

ID conservado: `cantharellus_lutescens`. **R07: [revisión por especie](literature/prediction/cantharellus_lutescens_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Taxón y plantas.** Conservar el ID histórico y reflejar la nomenclatura *Craterellus lutescens* como sinónimo/nombre revisado. Mantener pinares y bosques mixtos húmedos. Sporas cita también hayedos/castañares; antes de añadirlos como hospedadores estrictos, distinguir contexto de rodal y relación micorrícica.

**Altitud y época.** Convertir el óptimo 0–0 y el retardo 0–0 en desconocidos tras revisar la procedencia; no confundir el mínimo 0 con el mismo problema. Mantener octubre–diciembre principales y septiembre/enero/febrero secundarios. El propio texto de Sporas admite febrero aunque su tabla lo marque cero. Revisar el máximo 1.600 frente a 1.800 m sin tomar uno como límite biológico.

**pH.** Tolerancia edáfica amplia o preferencia numérica no resuelta. Marc describe calizos y silíceos; Sporas reconoce explícitamente diferencias norte de Europa/Iberia y destaca musgo/humedad. No hay aquí contradicción que deba resolverse eligiendo solo ácido o básico.

**Revisión propuesta.** Priorizar hábitat húmedo y época; no construir una exclusión por pH. Los ceros de afinidad de pinos no significan ausencia de afinidad.

### 4.8. Craterellus cornucopioides

ID conservado: `craterellus_cornucopioides`. **R08: [revisión por especie](literature/prediction/craterellus_cornucopioides_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** R08 destaca frondosas, especialmente haya/robles y otros contextos de hoja ancha. Revisar las relaciones primarias con abeto y pino que provienen de descripciones de bosques mixtos. Conservarlas como contexto por verificar, sin suprimir información histórica ni exigir coníferas.

**Altitud y época.** Óptimo 0–0 pendiente de representar como desconocido; proponer también mínimo desconocido: el mínimo local es 0 y la normalización contiene `null`, sin documentar allí una cota litoral. Esa diferencia no reconstruye por sí sola cómo se guardó el cero. El otoño está respaldado por las síntesis; Sporas presenta septiembre–noviembre y posibilidades estivales, mientras la ficha desplaza principales a octubre–diciembre y admite enero. Proponer contextualizar ambos calendarios por región y clima; no sustituir enero por cero ni añadir automáticamente junio/julio a todos los puntos.

**pH.** Discrepancia de énfasis: Marc ácido/silíceo/neutro y tolerancia, Sporas tendencia básica/caliza con presencia en silíceos. Registrar «preferencia no resuelta/tolerancia documentada»; no sacar un promedio de pH ni escoger la fuente más reciente como árbitro.

**Revisión propuesta.** Filtrar por hábitat compatible y época suficientemente descritos. Los arbolados genéricos y el pH discordante reducen la certeza, no prueban incompatibilidad.

### 4.9. Hygrophorus latitabundus

ID conservado: `hygrophorus_latitabundus`. **R09: [revisión por especie](literature/prediction/hygrophorus_latitabundus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener pinos, con especial respaldo en R09 para *P. sylvestris* y *P. nigra*. Revisar la incorporación de *P. pinaster*, ausente de su lista específica local pero citado por R09 en estudios ibéricos; conservar la diferencia entre inventario de rodal y hospedador probado. No extender a cualquier conífera.

**Altitud y época.** Conservar otoño tardío e invierno suave regional. Los ejemplos de Marc por encima de 1.000 m en octubre y por debajo de 600 en diciembre describen movimiento estacional, no min/max generales. El intervalo 100–1.600 m permanece descriptivo y pendiente de validar como filtro.

**pH.** Preferencia caliza/rica en bases concordante; sin min/max universal acreditado. Marc usa una formulación más estricta que la revisión científica local, que la califica como preferencia y no requisito absoluto demostrado.

**Revisión propuesta.** La segunda comprobación confirma ecuaciones específicas en las tablas 4 y 6 de Martínez de Aragón et al. (2007). Predicen producción regional, no probabilidad diaria; no importar coeficientes al visor.[^aragon] La nota breve que no encuentra un modelo se refiere a otro conjunto de fuentes y debe acotar esa afirmación.

### 4.10. Hygrophorus marzuolus

ID conservado: `hygrophorus_marzuolus`. **R10: [revisión por especie](literature/prediction/hygrophorus_marzuolus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener *Abies* y *Pinus* del contexto montano; revisar por fuente las relaciones adicionales con haya y otras plantas. Sporas menciona rareza en abetales muy densos: densidad desfavorable no significa que *Abies* sea un hospedador incompatible.

**Altitud y época.** Diferenciar el calendario enero–junio de la ficha y el máximo local abril–mayo de la referencia Sporas febrero–abril. Proponer calendarios regionales con retraso de montaña, no un calendario nacional único. El contraste 600–1.900 / 900–2.000 m queda abierto como ámbito, sin justificar reemplazo mecánico.

**pH.** Mantener preferencia ácida/silícea de la ficha como descriptiva. R10 no acredita pH óptimo ni litología obligatoria; conservar la posibilidad de suelos descalcificados y no inferir el pH por la roca.

**Revisión propuesta.** Deshielo es contexto relevante, no requisito binario de nieve previa en toda localización. El retardo 10–50 días y los umbrales térmicos heredados necesitan evidencia propia; no proceden de la mera etiqueta «marzuelo».

### 4.11. Lactarius deliciosus

ID conservado: `lactarius_deliciosus`. **R11: [revisión por especie](literature/prediction/lactarius_deliciosus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener *Pinus*, incluyendo los taxones específicos ya presentes; no exigir uno cuando el mapa solo resuelva el género. Separar datos de *L. deliciosus* estricto de estudios de sección *Deliciosi* o agregados comerciales de níscalos, como advierte R11.

**Altitud y época.** Óptimos 0–0 desconocidos. Conservar máximo otoñal; diciembre no es incompatibilidad por figurar secundario. Junio en Marc/local es posibilidad contextual, no prueba de campaña primaveral general. Diferencia 1.900 m local / 1.600 m Sporas: no usar para un descarte hasta definir ámbito.

**pH.** Marc destaca permeabilidad y silíceos, Sporas introduce preferencia caliza o poco ácida, y R11 recoge respuesta de *Lactarius* en pinares ácidos. Esa última respuesta agregada no valida el óptimo del taxón estricto. Proponer tolerancia/desacuerdo documentado, sin intervalo numérico obligatorio.

**Revisión propuesta.** Evitar que calizo/ácido excluyan por sí solos. Mantener información de drenaje como atributo distinto. Los bloques meteorológicos a cero son provisionales, no umbrales de lluvia o viento.

### 4.12. Lactarius salmonicolor / quieticolor

ID conservado: `lactarius_salmonicolor_quieticolor_group`. **R12: [revisión por especie](literature/prediction/lactarius_salmonicolor_quieticolor_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Taxón y plantas.** Se conserva la ficha agrupada por decisión del usuario. La clave de Nuytinck/Verbeken separa *L. salmonicolor* asociado a abetos; R12 diferencia *L. quieticolor* asociado a pinos.[^deliciosi] Esa diferencia científica se documenta, pero no se crean subperfiles ni se divide la ficha. Admitir abetos o pinos como alternativas de la ventana amplia.

**Altitud y época.** El ámbito 1.200–2.300 m y julio–octubre refleja principalmente uso pirenaico. No representa automáticamente todas las poblaciones de ambos taxones. El óptimo exactamente 1.200–1.200 necesita revisión de procedencia, no una nueva curva estrecha.

**pH.** R12 diferencia una tendencia neutra/básica para *salmonicolor* de contextos ácidos para *quieticolor*, mientras Marc describe los setales pirenaicos agrupados. La decisión operativa es conservar un rango amplio para la ficha agrupada, a partir de cifras de suelo utilizables de ambos conceptos; su ámbito se conserva en la fuente, sin exigir una separación taxonómica previa.

**Decisión vigente.** Una ficha agrupada y ventanas amplias. No se plantea separar sus observaciones ni mostrar dos curvas específicas; la relación con el conjunto predictivo Rovelló se aborda en §8.2.

### 4.13. Lactarius sanguifluus

ID conservado: `lactarius_sanguifluus`. **R13: [revisión por especie](literature/prediction/lactarius_sanguifluus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar pinos; R13 cita también *P. pinaster*, que merece incorporarse como propuesta de relación documentada tras precisar fuente. No fusionar con *L. vinosus*: la separación tiene respaldo molecular/morfológico.[^deliciosi]

**Altitud y época.** Mantener septiembre–noviembre y diciembre posible como calendario descriptivo. El rango 0–1.700 m y óptimo 300–1.200 no queda validado como distribución completa por las referencias examinadas. Revisar su uso por región, sin excluir cotas límite únicamente por esos valores.

**pH.** Tendencia caliza/rica en bases concordante en R13, pero su propio apartado de limitaciones rechaza un pH/carbonato universal de fructificación. Mantener preferencia y separar litología de suelo; la afinidad negativa silícea no es un veto cuantitativo calibrado.

**Revisión propuesta.** Preservar relaciones y fenología útiles con procedencia. No importar la ecología silícea de *vinosus* ni copiar sus porcentajes o coeficientes por pertenecer a la misma sección.

### 4.14. Lactarius vinosus

ID conservado: `lactarius_vinosus`. **R14: [revisión por especie](literature/prediction/lactarius_vinosus_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar pinos y dar trazabilidad a *P. pinaster*, ya presente con afinidad 0. R14 y el estudio de campo de Poblet lo sitúan en ese contexto. Encinas codominantes en parcelas no demuestran que sean hospedadores de este lactario.

**Altitud y época.** **Proponer retirar el máximo 700 m como exclusión.** La tabla 3 de Castaño contiene producción media positiva en parcelas a 903 y 1.010 m, además de otras intermedias.[^vinosus] Mantener «baja cota/cálido» como descripción del uso local original, no como límite del taxón. No sustituir por 1.010 m universal. Octubre–diciembre sigue respaldado; enero es posibilidad local, no resultado de ese muestreo otoñal.

**pH.** Corregir la incoherencia editorial: `soil_acidic` figura primario con afinidad −0,55; `soil_siliceous`, primario 0, convive con caliza/dolomía/marga preferidas. Marc favorece silíceos. Proponer conservar esa tendencia descriptiva y marcar lo contradictorio pendiente; el artículo de esporas no aporta un rango de pH.

**Revisión propuesta.** No confundir los dos máximos de micelio de R14 con dos campañas demostradas de carpóforos. La actividad subterránea y la recolección son respuestas distintas.

### 4.15. Lepista nuda

ID conservado: `lepista_nuda`. **R15: [revisión por especie](literature/prediction/lepista_nuda_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener su carácter descomponedor y la materia orgánica/hojarasca. Los pinos, robles, encinas y prados de la ficha son contextos; no deben exigirse como hospedadores micorrícicos. La nomenclatura moderna discutida por R15 se registra como equivalencia revisable conservando el ID.

**Altitud y época.** Convertir óptimo 0–0 en desconocido. Conservar otoño–invierno y posibilidad primaveral, con descenso de cota según avance del frío descrito por Marc. No considerar que los meses secundarios marzo/abril o enero/febrero están fuera de época por no ser principales. El máximo 1.800 m permanece pendiente como límite estricto.

**pH.** Marc admite calizos ricos en humus y silíceos. R15 describe muestras ácidas de unos pocos hábitats y avisa de que no prueban exclusividad acidófila. Proponer tolerancia amplia/desconocida cuantitativamente; no sacar min/max del cultivo.

**Revisión propuesta.** Compatibilidad basada en ambiente orgánico adecuado, no en presencia obligatoria de un árbol. No completar los ceros meteorológicos con óptimos de laboratorio. El estudio de 2007 también incluye una regresión regional para esta especie; no equivale a un predictor diario universal.[^aragon]

### 4.16. Macrolepiota procera

ID conservado: `macrolepiota_procera`. **R16: [revisión por especie](literature/prediction/macrolepiota_procera_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar modo saprótrofo, prados, claros, bordes y aporte orgánico. Un prado apto no requiere arbolado; tampoco toda cubierta forestal cerrada demuestra un claro apto a escala del punto.

**Altitud y época.** Óptimo 0–0 desconocido. La ficha conserva mayo/junio y agosto/noviembre secundarios; Sporas añade julio y diciembre a su tabla. Proponer revisar esas dos colas por región, manteniendo otoño como referencia. El máximo local 1.800 frente a Sporas 1.400 no se resuelve eligiendo el más bajo: Marc ya describe arranque estival en cotas de 1.400–1.600.

**pH.** Marc describe ambos sustratos y mayor importancia de materia orgánica. R16 distingue crecimiento micelial en cultivo de fructificación natural. Proponer tolerancia amplia cualitativa, min/max desconocidos.

**Revisión propuesta.** No usar un óptimo de medio de cultivo ni el intervalo divulgativo más estrecho como filtro. La amplitud de hábitat no equivale a compatibilidad garantizada en cualquier terreno.

### 4.17. Marasmius oreades

ID conservado: `marasmius_oreades`. **R17: [revisión por especie](literature/prediction/marasmius_oreades_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar herbazales, prados y céspedes/corros. No exigir bosque ni un árbol. R17 describe interacciones con plantas y suelo; ello no transforma las gramíneas en hospedadores arbóreos obligatorios.

**Altitud y época.** **Proponer sustituir tanto mínimo como máximo 0 por desconocidos**: ambos eran `null` en la normalización original. Revisar también el óptimo 0–0. No inventar límites a partir de otra especie de prado. Mantener primavera y posibilidades de verano/otoño; la persistencia visual de un corro durante el año no demuestra carpóforos todo el año.

**pH.** Marc no proporciona una señal numérica; R17 no acredita un intervalo universal. Materia orgánica, humedad y microhábitat herbáceo son descriptores más defendibles. Proponer pH desconocido, sin exclusión ni peso cuantitativo añadido.

**Revisión propuesta.** Caso obligatorio de prueba: prado a altitud positiva y sin árboles no puede descartarse por el máximo 0 ni por ausencia de MFE forestal. Se mantiene exigencia de época/contexto y de modelo aplicable.

### 4.18. Morchella elata complex

ID conservado: `morchella_elata_complex`. **R18: [revisión por especie](literature/prediction/morchella_elata_complex_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Taxón y hábitat.** No equiparar el complejo local a *M. esculenta* de Sporas ni al agregado *esculenta/conica* de Marc. R18 diferencia especies y respuestas a incendios/perturbación. Proponer documentar el alcance del grupo y conservar datos sin asignación artificial a una especie estricta.

**Plantas, altitud y época.** Las listas de ribera/coníferas son contexto, no una exigencia micorrícica universal. Mantener primavera y desplazamiento a cotas altas con el avance de temporada como hipótesis regional; los 0–2.000 m no delimitan por sí solos todo el complejo. Una especie pirófila no permite exigir incendio reciente a todos sus miembros.

**pH.** Desconocido para el grupo como intervalo único. No importar preferencia caliza de *esculenta* ni interpretar «indiferencia edáfica total» del agregado divulgativo como resultado demostrado para cada especie.

**Revisión propuesta.** Separar identidad, perturbación y hábitat antes del filtro. Si no hay capa de perturbación, registrar ausencia de información; no inventar una condición favorable a partir de la lluvia.

### 4.19. Russula virescens

ID conservado: `russula_virescens`. **R19: [revisión por especie](literature/prediction/russula_virescens_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener frondosas ya incluidas, con prioridad de revisión de la relación concreta y su ámbito. R19 advierte de complejos asiáticos/nombres semejantes: no incorporar hospedadores o respuestas tropicales a la especie europea por coincidencia nominal.

**Altitud y época.** Óptimo 0–0 desconocido. Proponer mínimo desconocido: el 0 local corresponde a `null` en la normalización. Mantener junio/julio/septiembre principales y agosto/octubre/noviembre secundarios como descripción inicial, incorporando la diferencia atlántica/catalana de Marc. Sus fechas muy concretas de comienzo de verano son observaciones regionales, no una ventana diaria rígida. Máximo 1.600 m aún sin validación como veto.

**pH.** Preferencia acidófila/silícea descriptiva de la ficha; R19 no acredita pH óptimo ni litología obligatoria. Mantener min/max desconocidos y evitar confundir esta preferencia con una regla de ausencia sobre cualquier geología carbonatada.

**Revisión propuesta.** Resolver ceros de afinidad y separar confianza taxonómica de confianza climática; la aceptación del nombre no valida automáticamente umbrales.

### 4.20. Tricholoma terreum

ID conservado: `tricholoma_terreum`. **R20: [revisión por especie](literature/prediction/tricholoma_terreum_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Mantener *Pinus*. R20 aporta respaldo experimental/taxonómico para asociación con pinos; revisar la relación de *Abies* de la ficha, cuya fuente local describe abetales pero no demuestra por ello hospedador estricto. No eliminar esa descripción histórica: cambiar su nivel de evidencia.

**Altitud y época.** Óptimo 0–0 desconocido. Mantener octubre–enero principales y las colas regionales de febrero/marzo, mayo y agosto/septiembre. La presencia excepcional de montaña en agosto no valida el mismo calendario costero. El máximo 1.800 m sigue pendiente como límite biológico.

**pH.** Calizo/rico en bases como preferencia, con tolerancia silícea explícita de Marc. R20 rechaza min/max universal. No usar dos relaciones a cero para inferir neutralidad ni una preferencia numérica inexistente.

**Revisión propuesta.** Conservación de frío/humedad/época tardía como contexto; no extrapolar fructificación controlada a umbrales meteorológicos diarios universales. La tabla 4 del estudio de 2007 incluye una regresión regional para esta especie: evitar afirmar que no existen modelos específicos.[^aragon]

### 4.21. Tuber melanosporum

ID conservado: `tuber_melanosporum`. **R21: [revisión por especie](literature/prediction/tuber_melanosporum_revision_bibliografica_rainmapper.md)**, apartados de evidencia, hábitat/suelo, fenología y limitaciones; contraste con Marc y, cuando existe ficha equivalente, Sporas.

**Plantas y hábitat.** Conservar quercíneas y avellano con sus fuentes; separar plantas indicadoras como boj/enebros de hospedadores comprobados. La calcicolía y un suelo aireado tienen respaldo, pero no garantizan producción.[^truffle]

**Altitud y época.** **Proponer mínimo y máximo 0 como desconocidos**: ambos campos son `null` en la normalización consultada y 0 en el fichero local. No se atribuye esa diferencia a una migración concreta sin comprobar su historia. Revisar también los óptimos 0–0. Mantener invierno como maduración/recolección del perfil actual. No tratarlo como una florada epigea desencadenada por lluvia de la última semana: R21 describe un ciclo largo y efectos estivales sobre producción invernal.

**pH.** Proponer afinidad de suelo carbonatado/rico en bases; mantener separados pH, carbonato activo, aireación y profundidad. García-Montero estudia primeros 30 cm y también controles sin producción. No copiar a la especie el rango 7,2–8,8 de `soil_calcareous` ni deducir que todo suelo en él sea trufero.[^truffle]

**Revisión propuesta.** Antes de mostrar una curva semanal, definir qué predice el motor para este taxón: madurez/disponibilidad no equivale a nueva aparición. Si no existe modelo aplicable a esa respuesta, mostrar estado sin modelo, aunque la ecología sea compatible.

## 5. pH: qué añadir y qué no inferir

**Propuesta posterior preparada por petición expresa del usuario (13/09):**
[rangos provisionales por especie](prediction-map-species-ph-proposal-es.md).
Concreta cifras y su origen. La decisión posterior del usuario aplica las 21
ventanas como filtros provisionales, incluidas las diez coberturas amplias
inicialmente recomendadas solo como contexto. Se revisarán con setales conocidos. La traducción explícita de preferencias
a clases numéricas es una aproximación propuesta ahora; no modifica lo que la
revisión original encontró ni transforma esos números en límites biológicos.
Las secciones siguientes conservan la evidencia y las precauciones de interpretación.

### 5.1. Tres conceptos diferentes

El catálogo local contiene, por ejemplo, `soil_acidic` 3,5–6,5,
`soil_slightly_acidic` 5,5–6,8, `soil_neutral` 6,5–7,5 y
`soil_basic` 7,2–8,8. Esos intervalos se solapan. También asigna rangos a
«silíceo» o «calizo». Son atributos del vocabulario existente, **no límites de
cada seta ni una clasificación mineralógica demostrada por pH**.[^local]

Separar:

- **pH cartografiado del punto:** estimación de SoilGrids por profundidad, con
  mediana e intervalo; no análisis de laboratorio de ese setal.
- **Afinidad edáfica de la especie:** preferencia o tolerancia descrita por una
  fuente; puede ser cualitativa y regional.
- **Litología/carbonatos:** material geológico y composición del suelo. Un
  substrato calizo puede sostener un horizonte superficial acidificado; un
  valor de pH por sí solo no identifica carbonato activo ni hospedadores.

La página original de Marc para los dos ceps admite suelos calizos acidificados.
Por tanto, convertir `lith_limestone` en veto automático contradice esa fuente.
No se deben sumar tres penalizaciones por una misma evidencia traducida a
«roca caliza», «suelo básico» y «pH alto».[^marc]

### 5.2. Evidencia numérica que sí puede guardarse, con su significado

| Fuente y taxón | Dato comprobado | Representación propuesta | Uso que no justifica |
|---|---|---|---|
| Daza et al., *A. caesarea* | Mayor crecimiento radial de aislados en cultivo a pH 6–7 | Registro experimental, tipo de medio/aislado y variable «crecimiento micelial» | `ph_min=6`, `ph_max=7` para aparición de setas en el campo. |
| Ponce et al., comunidad de *P. uncinata* con *B. edulis* y *B. pinophilus* | Tabla de parcelas con pH 4,7–5,3; muestras de 20 cm de profundidad y suspensión suelo/agua 1:2,5 | Intervalo observado del estudio, no de cada especie | Asignar 4,7–5,3 como nicho de ambos boletos o compararlo sin más con 0–5 cm. |
| García-Montero et al., *T. melanosporum* | Estudio de horizontes superficiales hasta 30 cm, carbonatos y productividad | Evidencia edáfica multivariable de campo, con ámbito Alto Tajo | Que un pH «adecuado» garantice producción o que 0–5 cm represente toda la zona de fructificación. |
| Zotti et al., *C. gambosa* | Descenso de pH asociado al frente del corro | Efecto observado de la actividad del hongo | Tratar el pH modificado por el propio hongo como requisito causal previo. |

Fuentes: Daza,[^daza] Ponce,[^ponce] García-Montero[^truffle] y Zotti.[^calocybe]

### 5.3. Campos propuestos en la ficha

Añadir un bloque **«pH del suelo»** en Ecología, mantenido desde la misma ficha:

La primera implementación prioriza **mínimo y máximo editables** y reutiliza
la procedencia/revisión existente. El diseño más detallado de la tabla siguiente
se conserva como referencia; no obliga a añadir ahora todos esos controles ni
un segundo intervalo de óptimos para poder avanzar.

| Campo conceptual propuesto | Contenido |
|---|---|
| Preferencia cualitativa | Ácido, próximo a neutro, rico en bases, tolerancia amplia o desconocido; sin traducir automáticamente a números. |
| Intervalo preferente min/max | Opcional; vacío hasta tener evidencia comparable y ámbito definido. |
| Límite de incompatibilidad min/max | Separado del preferente; inicialmente sin límites numéricos activados. |
| Naturaleza de la evidencia | Campo con fructificación, presencia, micelio/raíces, cultivo experimental o síntesis. |
| Método y profundidad | Agua, KCl/CaCl₂ u otro/no informado; horizonte o profundidad. No aplicar una conversión fija entre métodos. |
| Ámbito y taxón | Región, hábitat, especie estricta/grupo y condiciones observadas. |
| Fuente, localizador y revisión | Referencia, página/tabla, responsable, fecha y estado de aceptación. |

Son campos de diseño, **no nombres de API ya implementados**. Un dato ausente
se representa como `null`/desconocido, no 0. No trasladar automáticamente a
`null` un mínimo altitudinal 0 válido ni una temperatura de congelación: revisar
origen y significado campo por campo.

La revisión inicial de §4 no fijó límites numéricos. La decisión posterior
autoriza preparar los extremos amplios de pH utilizables como configuración
operativa provisional, con revisión futura. El mínimo y máximo deben poder
editarse en la ficha, no quedar ocultos solo en JSON. Sin dato utilizable, se
conserva vacío y el pH no excluye. No se generan pesos meteorológicos nuevos
a partir de esta decisión.

### 5.4. Uso de SoilGrids en la futura compatibilidad

Conservar las tres profundidades disponibles y sus cuantiles; no reducir todo
al número superficial de la cabecera. Si se estableciera un intervalo validado,
el solapamiento de la incertidumbre cartográfica con él impediría un descarte
tajante. Incluso un intervalo estimado completamente exterior exigiría revisar
método, profundidad, representatividad y fuerza del límite antes de excluir.
Un cuantil del suelo **no es una probabilidad de presencia de la seta**.

Geología o pH sin datos producen «desconocido». Una discrepancia entre fuentes
se conserva como discrepancia; no se elige automáticamente la más favorable.
No hacen falta nuevas descargas ni auditorías nacionales para este trabajo.

## 6. Revisión transversal de los otros parámetros

### Hospedadores y hábitat

La cadena compartida sigue siendo código GIS → mapping revisado → ID de
catálogo → relación de especie. El catálogo describe plantas y sus alias;
añadir una planta no demuestra por sí mismo que hospede una seta.

Se respeta el acuerdo de aceptar la generalización cartográfica: un pino
silvestre pertenece a «pinos», y una capa genérica de pinos puede satisfacer
operativamente una relación específica con pinos cuando no hay mayor detalle.
La salida conserva ese **nivel genérico**, sin afirmar haber identificado
*P. sylvestris*. La misma regla se aplica a otros grupos compatibles, pero no
a dos ramas distintas: «encina» no demuestra «haya», ni «coníferas» resuelve
por sí sola el contraste *Abies*/*Pinus* de los lactarios agrupados.

Separar relaciones positivas, toleradas, desfavorables y desconocidas, con
procedencia. Una afinidad heredada 0 no es «incompatible»; una lista positiva
incompleta tampoco implica que todo ID no listado sea imposible. La ausencia
de arbolado en una capa no impide especies de prado o descomponedoras. Los
huecos de información forestal aceptados por el usuario permanecen como tales.

### Altitud y época

Aplicar el mismo procedimiento a todas las especies: ámbito regional,
preferencia respaldada y límites explícitos. Para el mapa inicial, cuando solo
hay un ámbito típico documentado, una ubicación exterior puede quedar
**«fuera del ámbito ecológico validado»**, sin aparecer en la lista principal;
no se declara imposible ni se devuelve 0 %. Esto permite no recomendar
*A. caesarea* a 2.000 m en el ámbito pirenaico considerado, sin inventar un
límite universal ni extrapolarlo a otras regiones.

El ejemplo de *B. pinophilus* en costa se trata igual: no basta con que haya
algún pino y lluvia. Exige un ámbito ecológico aplicable; si falta evidencia
regional, queda no evaluable. No se construye una excepción con el nombre de
esa especie ni se fija por intuición una cota costera prohibida.

Evaluar cada fecha de los siete días. Una semana que cruza de mes puede incluir
una especie si hay días con época aplicable; los restantes se identifican como
fuera de ventana, no como cambio arbitrario de familia/modelo. Mes secundario
cuenta como posibilidad; un registro excepcional no convierte automáticamente
todo ese mes en temporada habitual nacional.

### Lluvia, temperatura, humedad, viento y retardos

El inventario adjunto conserva los valores por especie, incluidos los bloques
completamente a cero. **No se propone copiarlos a un filtro nuevo ni convertir
los umbrales de una síntesis en coeficientes entrenados.** Ejemplos concretos:

- *A. caesarea* guarda retardo 5–21 días y lluvia de 15 días mínima 25 mm.
  El experimento de Daza no valida esos valores: estudia micelio en cultivo.
- *B. edulis* guarda retardo 6–24 días. El preprint local analiza ventanas de
  temperatura de 20 días y lluvia de 26 días; una ventana explicativa no es un
  tiempo de espera obligatorio tras cada lluvia.[^porcini]
- Karavani evalúa asociaciones mensuales en comunidades de pinar. Reformular
  la síntesis que dice «lag de un mes exacto»: no prueba un reloj de 30 días ni
  que el suelo tarde un mes en humedecerse.[^karavani]
- La evidencia general de desecación no valida los números 18/42 km/h de viento
  de una ficha ni convierte una estación próxima en viento interpolado del
  punto. Los cambios en estos pesos quedan fuera de la activación automática.
- Los máximos/minimos térmicos diarios del aire, la temperatura media de varios
  días y la temperatura del suelo no son variables intercambiables.

La [revisión de periodos secos](literature/prediction/rainmapper_dry_spell_variable_review.md)
se conserva como referencia específica. Esta revisión no modifica el contador
ni reabre decisiones anteriores del motor. Pesos de puntuación y mínimos de
observaciones para calibrar son decisiones del modelo; no se consideran
demostrados por compartir ficha con datos bibliográficos.

## 7. Incongruencias y correcciones documentales propuestas

| Elemento | Problema comprobado | Corrección propuesta |
|---|---|---|
| Marc, texto vs normalización numérica | La página 2 habla de cotas según avance de temporada; el JSON normalizado introduce intervalos generales. | Conservar ejemplos estacionales y su ámbito; no atribuir a la página un límite universal que no formula. |
| Normalización vs fichero local | Máximo *B. edulis* 2.200 m en normalización y 2.100 m local; *B. pinophilus* 1.700 frente a 2.300 m. | Registrar discrepancia, sin restaurar automáticamente uno de los valores. |
| *L. vinosus*, ficha | Ácido con afinidad negativa pero relación primaria; silíceo primario y litologías carbonatadas preferidas. | Revisar el conjunto y su procedencia; no resolverlo sumando puntuaciones opuestas. |
| Sporas, tabla mensual vs texto | *C. lutescens*: febrero a cero en tabla pero posible en texto. *B. pinophilus*: primavera/cola tardía no expresadas igual en todos los apartados. | Distinguir temporada habitual y posibilidad excepcional/regional; no dar al cero tabular significado de prohibición. |
| Sporas vs Marc, suelos | *C. cornucopioides* y *L. deliciosus* tienen énfasis edáficos distintos; *C. lutescens* reconoce expresamente diversidad regional. | Mantener desacuerdo/ámbito y tolerancia; no imponer el texto más reciente por fecha. |
| Notas cortas de fenología | Afirmaciones sobre ausencia de modelos proceden de una búsqueda limitada; el original de Martínez de Aragón sí incluye regresiones por especie. | Decir «no localizado en estas fuentes/para este objetivo»; distinguir producción regional de probabilidad diaria. |
| Kauserud 2008/2012 | Comparar sensibilidad al retraso con longitud de temporada entre grupos como si fueran el mismo resultado. | Separar las dos métricas y ámbitos. Una temporada ECM relativamente más corta puede a la vez alargarse con el tiempo.[^kauserud] |
| Preprint de porcini | La nota lo cita como 2025/v1; el PDF local indica versión del 8 de junio de 2026 y da autores. | Identificar la versión efectivamente leída, autores y estado de preprint; no asegurar revisión por pares. |
| *Morchella* | Sporas trata *M. esculenta*; Marc agrupa *esculenta/conica*; el perfil es `morchella_elata_complex`. | Impedir una transferencia directa de suelo, hospedadores y cifras entre conceptos taxonómicos. |
| Datos de cultivo o micelio | Algunos números pueden parecer óptimos de fructificación cuando describen otra variable. | Etiquetar variable de respuesta y mantenerlos fuera del filtro de aparición de carpóforos. |
| R21, referencia 4 de trufa | El enlace PMC8775154 lleva a *Life Cycle and Phylogeography of True Truffles*, no al artículo de Le Tacon citado. | Citar Le Tacon mediante su DOI confirmado; mantener el otro artículo como referencia diferente si se utiliza.[^truffle-citations] |
| R21, referencia 9 de trufa | El artículo enlazado sobre profundidad/peso/madurez es de *Journal of Fungi* 7, 102, no la referencia *Agronomy* 11, 498 indicada. | Corregir título/revista/DOI a partir de la publicación enlazada.[^truffle-citations] |
| Mínimos de altitud heredados | Además de ceros, aparecen 100 m en *A. caesarea*, *B. aereus*, *H. latitabundus* y 400 m en *C. cibarius* s.l. donde la normalización tenía `null`. | No atribuir esas cifras a Marc; buscar la procedencia adicional o dejarlas sin uso excluyente. |

Estas correcciones se proponen aquí sin sobrescribir los documentos fuente:
deben conservarse la redacción y la procedencia originales para poder auditar
qué cambió y por qué.

## 8. Pendientes después de las cuatro decisiones

### 8.1. Orden de implementación

1. **Completado en local (§1.1):** tabla **valor local → ventana amplia elegida → fuentes** para
   las 21 fichas, incluyendo las del conjunto Rovelló por separado y conservando
   salmonicolor/quieticolor unido. Resolver ceros provisionales; no reabrir una
   auditoría bibliográfica exhaustiva como condición de avance.
2. **Completado en local (§1.1):** pH mínimo/máximo en esquema y mantenimiento, con
   traducciones ES/CA/EN, persistencia y compatibilidad de perfiles antiguos.
   Aplicar las ventanas a las fichas locales preservando IDs, observaciones,
   procedencia y campos ajenos. Aplicado y comprobado; no supone activar todavía la predicción real.
3. Conectar el evaluador de compatibilidad con esas fichas: meses, hábitat,
   hospedadores, altitud y pH disponible; orientación fuera de los requisitos.
4. Implementar la correspondencia entre fichas y objetivo predictivo Rovelló
   y la preparación conjunta de sus observaciones, siguiendo §8.2. Conservar
   el motor único HA/worker y su selección semanal; validar el modelo del grupo
   antes de activarlo.
5. Integrar predicción real primero en servidor local/HA. Comparar con worker
   cuando el cálculo completo funcione. Publicación y trabajos siguen fuera
   de esta actualización documental.

La regionalización fina y el uso de orientaciones dejan de ser requisitos para
esta primera versión; no se planifica separar salmonicolor/quieticolor.
La revisión de las ventanas se retomará si los resultados lo requieren.

### 8.2. Rovelló: propuesta de agrupación reemplazada

**Última decisión del usuario, 13/09:** mostrar las especies por separado con
probabilidades propias; conservar ficha conjunta salmonicolor/quieticolor.
Implementado en preview con metadatos locales. No crear dataset derivado, fusionar
observaciones ni sustituir modelos entre miembros. Esta decisión reemplaza las
instrucciones de agrupación que siguen, conservadas como histórico de la propuesta.
[Estado y pruebas](../reports/prediction-map-engine-integration-2026-09-13.json).

**Comprobación del 13/09, datos locales y código actual; no inspección de HA real:**

- La ficha `lactarius_deliciosus` tiene como primer nombre común «Rovelló».
  La UI toma ese nombre de la ficha; no implica una agrupación de modelos
  (`mushroom_predictor_ui.py:391`).
- Las observaciones locales conservan cuatro IDs: deliciosus **56**,
  sanguifluus **7**, vinosus **2**, salmonicolor/quieticolor **1**. Son recuentos
  brutos, no episodios elegibles de entrenamiento ni una auditoría taxonómica
  de lo observado. No sabemos si parte de las 56 observaciones de deliciosus
  se introdujo con «Rovelló» en sentido amplio.
- El informe local `mushroom_ml_v0_report.json`, `species_results`, solo incluye
  deliciosus entre esos cuatro IDs. La UI cruza informe y modelos disponibles
  (`mushroom_predictor_ui.py:360`); el cargador selecciona artefacto por ID
  (`mushroom_ml_predictor.py:402`). El agregador de episodios conserva
  `species_id` en su clave (`mushroom_ml_trainer.py:174`). Estos caminos
  comprobados no acreditan que ya exista un entrenamiento conjunto.

**Decisión posterior del usuario: segunda opción, agrupación derivada para
entrenar/predecir. Se conservan las observaciones independientes.**

Funcionamiento acordado e implementación prevista:

1. Mantener las cuatro fichas ecológicas y declarar una correspondencia
   explícita con el objetivo predictivo «Rovelló». No hacerla depender del texto
   traducido del nombre común. Los nombres de campos/IDs de grupo aún no se fijan.
2. Evaluar la compatibilidad de cada ficha con sus ventanas amplias. El grupo
   puede aparecer si **al menos una ficha completa es compatible**: no mezclar
   el host de una con la altitud o el mes de otra para fabricar una coincidencia.
3. Mostrar **una fila y una curva de Rovelló**, con el detalle de las fichas
   compatibles. No cuatro copias del porcentaje de deliciosus ni sumar sus
   probabilidades. No afirmar cuál fructificará si el modelo responde al conjunto.
4. Conservar cada observación con su `species_id` original y una correspondencia
   explícita de las cuatro fichas con «Rovelló». El conjunto de entrenamiento
   derivado reunirá sus observaciones elegibles, guardando los IDs originales
   y sus referencias. El usuario elige esta vía para poder entrenar predicciones
   separadas en el futuro si se dispone de suficientes observaciones.
   El modelo conjunto debe aprender de esos datos: cambiar el nombre al modelo
   actual de deliciosus no cumple la decisión. No se suman ni promedian curvas
   independientes para sustituir ese entrenamiento.
5. La selección de versión/familia para siete días se hará una vez por objetivo
   predictivo y punto, con las mismas condiciones del motor existente en HA y
   worker. El filtrado diario de fichas compatibles no cambia esa familia.

**Controles técnicos de la agrupación:**

- Conservar observaciones, fotos, identificaciones y modelos actuales. La
  pertenencia al grupo es una configuración explícita y versionada, compartida
  por preparación, entrenamiento, evaluación y ejecutores HA/worker.
- Aplicar las reglas de elegibilidad y episodios existentes al objetivo conjunto:
  varias variedades registradas en el mismo episodio no crean varias salidas
  predictivas ni duplican su peso sin justificación. Mantener sus referencias.
  No convertir ausencia de una variedad en ausencia de todo Rovelló.
- Mantener un episodio completo en el mismo conjunto de entrenamiento o
  validación; agrupar no debe introducir duplicados a ambos lados de la evaluación.
- Distinguir artefactos del grupo y de especies individuales. Conservar la
  trazabilidad de qué miembros y versión de agrupación usó el modelo. Las
  predicciones futuras por variedad podrán reutilizar las observaciones originales.
- Usar las ventanas de las fichas para la compatibilidad de cada punto y mostrar
  «Rovelló» como grupo; no adjudicar al usuario una variedad concreta a partir
  de la curva conjunta ni denominar científicamente a todo el grupo *L. deliciosus*.

**Pendiente:** implementar y validar esta preparación y el entrenamiento del
objetivo conjunto, conservando la selección semanal existente. La decisión
sobre la agrupación queda cerrada; no queda por elegir entre aproximación con
deliciosus y grupo entrenado. Este acuerdo documental no ha lanzado trabajos
ni alterado el Predictor operativo.

Casos mínimos que debe cubrir esa implementación futura:

| Caso | Resultado esperado |
|---|---|
| *M. oreades* en prado a una cota positiva | El antiguo máximo 0 no descarta; no exige un árbol. |
| *L. vinosus* en el contexto publicado a 903/1.010 m | El antiguo límite 700 no genera incompatibilidad. |
| *B. edulis* en jaral con asociación documentada | No exigir un árbol; sí el contexto ecológico aplicable. |
| *A. caesarea* a 2.000 m, ámbito pirenaico | No aparece como recomendación compatible por simple meteorología favorable. |
| Pino genérico frente a relación específica de pinos | Coincidencia operativa al nivel admitido, con detalle cartográfico no inventado. |
| *Salmonicolor/quieticolor* | Una ficha conservada, ventanas amplias y abeto o pino como alternativas; observaciones intactas. |
| Orientación desfavorable para cualquier especie | No excluye por orientación en esta fase. |
| Varias fichas de Rovelló compatibles | Una salida del objetivo conjunto, sin duplicar porcentajes ni sumar probabilidades. |
| Host compatible solo con una ficha y altitud/mes solo con otra | No declarar compatible el conjunto sin una ficha que reúna los criterios. |
| Cartografía de árboles ausente | Estado desconocido, no ausencia demostrada. |
| Caliza con horizonte ácido | Conservar ambas evidencias; no veto litológico automático a acidófilas. |
| Cuantiles de pH cruzando un intervalo | Incertidumbre explícita; no exclusión por mediana sola. |
| Semana cruzando mes y meses secundarios | Evaluación por día, continuidad semanal del motor conservada. |
| Especie sin modelo aplicable | No inventar curva ni confundir falta de modelo con incompatibilidad ecológica. |

El documento no es un paquete importable ni una aceptación de una release.
Antes de aplicar cambios deben verificarse los consumidores de campos,
importación/exportación, comparación de resultados y tratamiento de nulos.
No requiere modificar el visor meteorológico existente, publicar HA, ejecutar
entrenamientos/precálculos ni alterar destinos de workers.

## 9. Segunda revisión realizada sobre el primer borrador

Después de terminar el primer documento se conservó su huella y se realizó
una segunda pasada sobre ese texto. Se volvieron a contrastar las 21 filas de
altitud/calendario con las fichas locales, las diferencias con Sporas y los
casos de mayor impacto con sus fuentes. No es una revisión por un segundo
experto independiente; es una comprobación secuencial adicional del documento.

Correcciones incorporadas al texto final:

| Comprobación | Corrección del borrador |
|---|---|
| Altitudes nulas en la normalización y ceros en las fichas | Precisar los seis campos candidatos y distinguir diferencia comprobada de historia de migración no acreditada. |
| Tablas 4–6 de Martínez de Aragón | Reconocer regresiones específicas regionales de *H. latitabundus*, *L. nuda* y *T. terreum*; no confundirlas con un predictor diario universal. |
| Interacciones de *C. gambosa* con herbáceas | Incorporar Graziosi 2025 y evitar reducir su ecología a descomposición sin interacciones con plantas. |
| Referencias 4 y 9 de la revisión de trufa | Identificar el enlace que lleva a otro artículo y corregir revista/título/DOI en la propuesta bibliográfica. |
| Datos numéricos de pH | Mantener cultivo, parcelas observadas y efecto del hongo separados de límites de fructificación; no activar min/max numéricos por especie. |

La segunda pasada no convierte las propuestas pendientes en hechos validados.
Se han contrastado directamente los originales señalados, no todos los artículos
externos de las bibliografías. Las fuentes locales y las fichas operativas se
conservan; las correcciones anteriores se aplicaron a este documento de propuestas.

## Fuentes y localizadores

Las referencias `R01`–`R21` de §4 son los informes locales por especie;
cada enlace identifica el documento y los apartados pertinentes. La auditoría
adjunta conserva inventario, valores locales y comprobaciones de la segunda
pasada. Las fuentes web siguientes se consultaron el 13/09/2026; donde solo se
leyó el resumen editorial se limita la afirmación a ese contenido.

[^local]: Datos locales: `docker-data/mushroom-data/mushroom_profiles.json`, rutas `species_profiles[*].ecology`, `.phenology`, `.topography`, `.weather_model`, `.metadata`; catálogo `docker-data/mushroom-data/mushroom_reference_catalogs.json`, `catalogs.soil_types`. Copia de campos relevantes y huellas en el anexo, sin modificación del original.
[^marc]: [Conclusiones de Marc](literature/marc-estevez-species-conclusions-es.md), apartados por especie, y [JSON normalizado](literature/marc-estevez-v0-source-normalized.json). PDF local `literature/Marc_EstevezSpecies.pdf`, página 2, «Calendari de recol·lecció» y «Vegetació associada i sòls», comprobada visualmente; el PDF puede no estar incluido en el repositorio.
[^vinosus]: Castaño et al. (2017), [Mushroom Emergence Detected by Combining Spore Trapping with Molecular Techniques](https://pmc.ncbi.nlm.nih.gov/articles/PMC5478987/), tabla 3 y «Study area». Tabla con altitud y producción media 2008–2014; no confundir con el muestreo de esporas de otoño de 2014. DOI 10.1128/AEM.00600-17.
[^cistus]: Alonso Ponce et al. (2011), [Rockroses and Boletus edulis ectomycorrhizal association: realized niche and climatic suitability in Spain](https://doi.org/10.1016/j.funeco.2010.10.002), resumen editorial: asociación *Cistus ladanifer–B. edulis* en España. Evidencia de esa asociación, no de todos los taxones del género *Cistus*.
[^daza]: Daza et al. (2006), [Effect of carbon and nitrogen sources, pH and temperature on in vitro culture of several isolates of Amanita caesarea](https://link.springer.com/article/10.1007/s00572-005-0025-6), resumen editorial; variable: crecimiento de aislados en cultivo.
[^ponce]: Ponce et al. (2023), [PDF local](literature/fruiting-phenology/ponce2023-pinus-uncinata.pdf), §2.1–2.2, tabla 1, inventario de especies y resultados; DOI [10.1016/j.foreco.2023.121256](https://doi.org/10.1016/j.foreco.2023.121256). Rodales subalpinos, no determinación de los límites de distribución de cada seta.
[^truffle]: García-Montero et al. (2006), [Soil factors that influence the fruiting of Tuber melanosporum](https://www.researchgate.net/profile/Luis-Garcia-Montero/publication/262956680_Soil_factors_that_influence_the_fruiting_of_Tuber_melanosporum_black_truffle/links/55eab87d08aeb6516265ec7b/Soil-factors-that-influence-the-fruiting-of-Tuber-melanosporum-black-truffle.pdf), pp. 731–732, métodos y resultados. DOI 10.1071/SR06046; estudio de 20 horizontes, incluidos controles sin producción.
[^calocybe]: Zotti et al. (2021), [Riding the wave: Response of bacterial and fungal microbiota associated with the spread of the fairy ring fungus Calocybe gambosa](https://www.sciencedirect.com/science/article/pii/S0929139321000846), resumen y descripción del sitio; DOI 10.1016/j.apsoil.2021.103963. No se adopta un pH mínimo del suelo a partir del efecto del micelio.
[^porcini]: Brejon Lamartiniere y Hoffman, [PDF local del preprint](literature/fruiting-phenology/boletus-biorxiv.pdf), portada, resumen y modelos; DOI [10.64898/2025.12.12.693895](https://doi.org/10.64898/2025.12.12.693895). La portada dice «this version posted June 8, 2026», no certificado por revisión por pares. Hayedo próximo a Bielefeld, 2015–2024.
[^karavani]: Karavani et al. (2018), [PDF local](literature/fruiting-phenology/karavani2018-mushroom-productivity.pdf), métodos y discusión de relaciones mensuales; DOI [10.1016/j.agrformet.2017.10.024](https://doi.org/10.1016/j.agrformet.2017.10.024). No confundir desfase estadístico mensual con espera causal fija.
[^kauserud]: Kauserud et al., [2008](literature/fruiting-phenology/kauserud2008-pnas.pdf), DOI 10.1073/pnas.0709037105, y [2012](literature/fruiting-phenology/kauserud2012-pnas.pdf), DOI 10.1073/pnas.1200789109, resúmenes y comparación entre grupos. Datos agregados y ámbitos distintos; no límites mensuales por especie para España.
[^deliciosi]: Nuytinck y Verbeken, [clave europea de Lactarius sección Deliciosi](https://www2.muse.it/russulales-news/id_deliciosi.asp), separación por hospedador; y [Lactarius sanguifluus versus Lactarius vinosus — Molecular and morphological analyses](https://link.springer.com/article/10.1007/s11557-006-0060-5), resumen editorial, 2003. El año 2003 y ese DOI están confirmados por la editorial, aunque el identificador contenga «006».
[^graziosi]: Graziosi et al. (2025), [Analysis of Plant–Fungus Interactions in Calocybe gambosa Fairy Rings](https://pmc.ncbi.nlm.nih.gov/articles/PMC12473715/), resumen, resultados y discusión; DOI 10.3390/plants14182884. Evidencia de interacciones con herbáceas, no de un árbol obligatorio ni un rango de pH de fructificación.
[^aragon]: Martínez de Aragón et al. (2007), [texto aportado por los autores](https://www.researchgate.net/publication/223514260_Productivity_of_ectomycorrhizal_and_selected_edible_saprotrophic_fungi_in_pine_forests_of_the_pre-Pyrenees_mountains_Spain_Predictive_equations_for_forest_management_of_mycological_resources), tablas 4–6 y definiciones de variables; DOI 10.1016/j.foreco.2007.06.040. Producción regional con variables mensuales y de rodal.
[^truffle-citations]: [Le Tacon et al., artículo correcto](https://link.springer.com/article/10.1007/s13595-015-0461-1); [artículo al que dirige PMC8775154](https://pmc.ncbi.nlm.nih.gov/articles/PMC8775154/); [artículo de profundidad/peso/madurez](https://pmc.ncbi.nlm.nih.gov/articles/PMC7912816/), DOI 10.3390/jof7020102. Son verificaciones bibliográficas; no añaden límites ecológicos nuevos.
