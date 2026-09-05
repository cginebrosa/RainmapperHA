# Sporas.io — extracción estructurada de especies para Rainmapper

**Fecha de consulta:** 4 de septiembre de 2026

**Fuente principal:** https://sporas.io/especies
**Objetivo:** conservar en un único documento la información ecológica, fenológica, climática y geográfica publicada por Sporas.io para las 15 especies de su catálogo, con una estructura útil para evaluar su incorporación al predictor de setas de Rainmapper.

> **Nota metodológica**
>
> Este documento es una **síntesis estructurada** del contenido publicado por Sporas.io, no una copia literal de sus fichas. Se prioriza la información que puede convertirse en variables, reglas, filtros o evidencias para un modelo predictivo: hábitat, hospedadores, sustrato, altitud, orientación, humedad, precipitación, temperatura, fenología y distribución.
>
> Sporas indica que su visor cruza, según la especie, **pluviometría acumulada, altitud y arbolado real del Mapa Forestal de España**. En algunas especies el propio texto advierte que la capa de arbolado es solo un proxy ambiental y no un hospedador biológico.
>
> Las reglas temporales del tipo “X días después de la lluvia” deben tratarse como **orientaciones de campo**, no como umbrales científicos universales. Sporas insiste repetidamente en que el retardo depende del agua acumulada, estado previo del suelo, temperatura, exposición, altitud y estado del micelio.

---

## 1. Catálogo completo

| # | Especie | Nombre común en Sporas | Temporada principal | Altitud publicada |
|---:|---|---|---|---:|
| 1 | [*Amanita ponderosa*](#31-amanita-ponderosa--gurumelo) | Gurumelo | Feb–Abr | 100–800 m |
| 2 | [*Hygrophorus marzuolus*](#32-hygrophorus-marzuolus--marzuelo--seta-de-marzo) | Marzuelo / Seta de marzo | Feb–Abr | 900–2.000 m |
| 3 | [*Morchella esculenta*](#33-morchella-esculenta--colmenilla) | Colmenilla | Mar–May | 300–1.800 m |
| 4 | [*Calocybe gambosa*](#34-calocybe-gambosa--perrechico--seta-de-san-jorge) | Perrechico / Seta de San Jorge | Abr–Jun | 400–1.800 m |
| 5 | [*Boletus aestivalis*](#35-boletus-aestivalis--hongo-de-verano--boleto-reticulado) | Hongo de verano / Boleto reticulado | Jun–Sep | 300–1.600 m |
| 6 | [*Amanita caesarea*](#36-amanita-caesarea--oronja) | Oronja / Amanita de los Césares | Ago–Oct | 300–1.000 m |
| 7 | [*Boletus aereus*](#37-boletus-aereus--hongo-negro--boleto-bronce) | Hongo negro / Boleto bronce | Ago–Oct | 100–1.200 m |
| 8 | [*Cantharellus cibarius*](#38-cantharellus-cibarius--rebozuelo--chantarela) | Rebozuelo / Chantarela | Jun–Oct | 50–1.500 m |
| 9 | [*Boletus edulis*](#39-boletus-edulis--boleto--hongo) | Boleto / Hongo | Sep–Nov | 600–1.800 m |
| 10 | [*Boletus pinophilus*](#310-boletus-pinophilus--boleto-de-pino) | Boleto de pino / Boletus pinicola | Sep–Nov + repunte primaveral | 600–2.000 m |
| 11 | [*Craterellus cornucopioides*](#311-craterellus-cornucopioides--trompeta-negra) | Trompeta negra | Sep–Nov | 200–1.600 m |
| 12 | [*Macrolepiota procera*](#312-macrolepiota-procera--parasol--apagador) | Parasol / Apagador | Sep–Nov | 50–1.400 m |
| 13 | [*Cantharellus lutescens*](#313-cantharellus-lutescens--gula-de-monte--trompeta-amarilla) | Gula de monte / Trompeta amarilla | Oct–Dic | 400–1.800 m |
| 14 | [*Lactarius deliciosus*](#314-lactarius-deliciosus--n%C3%ADscalo--rovell%C3%B3) | Níscalo / Rovelló | Sep–Dic | 100–1.600 m |
| 15 | [*Pleurotus eryngii*](#315-pleurotus-eryngii--seta-de-cardo) | Seta de cardo | Abr–May y Oct–Nov | 0–1.500 m |

---

## 2. Fenología mensual publicada por Sporas

Leyenda: **0 = sin actividad**, **B = baja**, **M = media**, **A = alta**.

| Especie | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *Amanita ponderosa* | 0 | M | A | A | B | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| *Hygrophorus marzuolus* | B | M | A | A | B | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| *Morchella esculenta* | 0 | 0 | M | A | A | B | 0 | 0 | 0 | 0 | 0 | 0 |
| *Calocybe gambosa* | 0 | 0 | 0 | M | A | M | B | 0 | 0 | 0 | 0 | 0 |
| *Boletus aestivalis* | 0 | 0 | 0 | 0 | B | M | A | A | A | B | 0 | 0 |
| *Amanita caesarea* | 0 | 0 | 0 | 0 | 0 | B | B | M | A | A | B | 0 |
| *Boletus aereus* | 0 | 0 | 0 | 0 | 0 | B | B | M | A | A | B | 0 |
| *Cantharellus cibarius* | 0 | 0 | 0 | 0 | B | M | M | A | A | A | B | 0 |
| *Boletus edulis* | 0 | 0 | 0 | 0 | B | B | 0 | B | A | A | M | B |
| *Boletus pinophilus* | 0 | 0 | 0 | 0 | B | B | B | B | A | A | M | 0 |
| *Craterellus cornucopioides* | 0 | 0 | 0 | 0 | 0 | B | B | B | M | A | A | B |
| *Macrolepiota procera* | 0 | 0 | 0 | 0 | 0 | B | B | B | A | A | M | B |
| *Cantharellus lutescens* | B | 0 | 0 | 0 | 0 | 0 | 0 | 0 | B | M | A | M |
| *Lactarius deliciosus* | 0 | 0 | 0 | 0 | 0 | 0 | 0 | B | M | A | A | M |
| *Pleurotus eryngii* | 0 | B | B | M | M | B | 0 | 0 | B | A | A | B |

---

# 3. Fichas estructuradas por especie

## 3.1 *Amanita ponderosa* — Gurumelo

**Fuente:** https://sporas.io/especies/amanita-ponderosa

### Perfil básico
- Tipo trófico: **ectomicorrícico**.
- Hábitats principales: alcornocales, encinares y también eucaliptales/repoblaciones.
- Hospedadores principales: **Quercus suber** y **Quercus ilex**.
- Asociaciones secundarias citadas: pinar y *Quercus pyrenaica* en la periferia de su área.
- Altitud: **100–800 m**, con mejor producción en la mitad baja del rango.
- Paisaje característico: monte mediterráneo abierto, dehesa y montado.
- Sotobosque/indicadores: *Cistus ladanifer*, jaguarzo, retama, romero y brezo.
- Microhábitat: calveros o rodales con cubierta vegetal aclarada; fructificación semienterrada.

### Suelo y sustrato
- Preferencia marcada por **suelos ácidos**.
- Suelos pobres y con poca materia orgánica.
- Textura arenosa o desarrollados sobre **pizarras**.
- Jarales y jaguarzos se presentan como buenos indicadores de suelo compatible.

### Exposición y relieve
- Ambientes abiertos y soleados.
- Sporas menciona llanos soleados y umbrías suaves como zonas de búsqueda.
- La orientación aparece como factor que puede modificar el retraso de fructificación.

### Fenología y clima
- Temporada principal: febrero–abril; posible prolongación a mayo en zonas altas/norte.
- Máximos: marzo y abril.
- El disparador no sería una lluvia puntual, sino:
  1. **invierno bien llovido**;
  2. acumulación hídrica en el perfil del suelo;
  3. posterior **calentamiento del suelo**;
  4. subida de temperaturas mínimas.
- Una primavera cálida después de un invierno seco puede producir muy poco.
- Un invierno húmedo puede adelantar y prolongar la campaña.
- No se propone un número fijo de días tras lluvia.
- Variables que condicionan el retraso: suelo, orientación y profundidad del micelio.

### Distribución ibérica resumida
- Especie fuertemente suroccidental.
- Núcleo: Huelva, suroeste de Badajoz, Sierra Norte de Sevilla, Córdoba, Cáceres, suroeste de Salamanca y montados portugueses del Alentejo/Ribatejo/Algarve.
- Fuera del cuadrante suroccidental se considera rara.

### Variables candidatas para Rainmapper
- precipitación acumulada invernal;
- reserva hídrica antecedente;
- tendencia de temperatura mínima;
- temperatura del suelo o proxy;
- altitud;
- Quercus suber / Q. ilex;
- suelo ácido;
- litología pizarrosa/arenosa;
- apertura del bosque;
- presencia de matorral acidófilo.

---

## 3.2 *Hygrophorus marzuolus* — Marzuelo / Seta de marzo

**Fuente:** https://sporas.io/especies/hygrophorus-marzuolus

### Perfil básico
- Tipo trófico: **ectomicorrícico estricto**.
- Hospedadores principales:
  - *Pinus sylvestris*;
  - *Pinus uncinata*;
  - *Fagus sylvatica*;
  - secundariamente *Betula* spp.
- Raro bajo robles, abetales muy densos y repoblaciones jóvenes.
- Altitud: **900–2.000 m**.
- Bosques maduros con manto de hojarasca o acículas desarrollado.
- Fructifica semienterrado y puede hacerlo bajo nieve o inmediatamente después del deshielo.

### Suelo
- Preferencia por **suelos ácidos**.
- Bien drenados.
- Ricos en materia orgánica.

### Microclima y relieve
- Umbrías y rellanos de suelo profundo.
- Evita zonas muy expuestas a ciclos bruscos de helada/deshielo.
- La umbría puede alargar la ventana respecto a una solana a igual altitud.

### Fenología y clima
- Actividad testimonial en enero.
- Febrero: aumento.
- **Marzo: máximo**.
- Abril todavía fuerte.
- Mayo residual, especialmente en cotas altas.
- El calendario se retrasa con la altitud.
- Motor fenológico central: **nieve → protección térmica → deshielo lento → aporte sostenido de agua → calentamiento progresivo**.
- Sporas interpreta el ciclo nieve–deshielo como más relevante que una lluvia puntual.
- La ventana se cierra cuando el suelo se calienta demasiado.
- En el catálogo general se resume como una especie que puede aparecer alrededor de ~10 días después del deshielo, con suelo ya por encima de unos 4–5 °C y frenándose con temperaturas ambientales claramente más altas; debe considerarse una regla orientativa, no un umbral universal.

### Distribución ibérica
- Cordillera Cantábrica.
- Pirineos navarros, aragoneses y catalanes.
- Ripollès, Alt Urgell, Cerdanya, Pallars Sobirà, Val d'Aran.
- Sistema Central.
- Sistema Ibérico / Sierra de Albarracín.
- Pinares acidófilos de Soria y Burgos.
- Citas en montañas orientales de Galicia.
- Sporas no respalda una distribución general en el sur peninsular.

### Variables candidatas
- nieve acumulada;
- fecha de deshielo;
- agua de fusión;
- temperatura del suelo;
- tendencia térmica post-deshielo;
- altitud;
- orientación;
- sombreado;
- pinar/hayedo maduro;
- suelo ácido;
- profundidad de hojarasca/acículas.

---

## 3.3 *Morchella esculenta* — Colmenilla

**Fuente:** https://sporas.io/especies/morchella-esculenta

### Perfil básico
- Ascomiceto.
- Sporas subraya que el pino funciona más como **indicador de ambiente** que como hospedador ectomicorrícico obligatorio.
- Dos grandes ambientes:
  1. riberas: fresnedas, choperas, alamedas, olmedas y sotos;
  2. terrenos **perturbados**: incendios del año anterior, taludes, obras, pistas recién abiertas, huertas, jardines con mulch de madera/corteza.
- Pinar joven o alterado puede ser favorable; pinar viejo y cerrado con capa intacta de pinocha, no necesariamente.
- Altitud: **300–1.800 m**.

### Suelo
- Preferencia por suelos **básicos o calizos**.
- Sueltos, profundos y bien drenados.
- Con abundante materia orgánica.
- Suelo removido es una señal especialmente importante.

### Perturbación
- Variable ecológica excepcionalmente importante:
  - incendios del año previo;
  - movimientos de tierra;
  - avenidas y crecidas;
  - obras;
  - apertura reciente de pistas;
  - acolchados leñosos.
- Sporas destaca una irregularidad interanual muy alta.

### Fenología y clima
- Febrero: apariciones puntuales en cotas bajas/años suaves.
- Marzo: ascenso.
- **Abril: máximo**.
- Mayo todavía muy productivo, especialmente en altura.
- Junio: cola residual.
- Disparador:
  - suelo bien cargado de agua por lluvias de final de invierno/primavera;
  - calentamiento progresivo del terreno.
- Marcado escalonamiento altitudinal: valle antes, montaña después.

### Distribución
- Riberas y sotos del norte e interior.
- Cuencas del Ebro y Duero.
- La Rioja, Navarra, Aragón.
- Pirineo y Prepirineo.
- Cordillera Cantábrica.
- Sistema Ibérico / Albarracín.
- Pinares calizos de Castilla y Sistema Central.
- Sierras interiores de Cataluña.
- Más que una comarca, Sporas considera decisivo el **tipo de sitio y la perturbación**.

### Variables candidatas
- precipitación de final de invierno;
- humedad del suelo;
- calentamiento del suelo;
- altitud;
- litología caliza;
- distancia a ribera;
- humedad topográfica;
- incendio previo;
- años desde incendio;
- perturbación del suelo;
- edad/estructura del pinar;
- uso del suelo reciente.

---

## 3.4 *Calocybe gambosa* — Perrechico / Seta de San Jorge

**Fuente:** https://sporas.io/especies/calocybe-gambosa

### Perfil básico
- No micorrícica.
- Descomponedora de suelo de pradera.
- Hábitat principal: praderas y pastizales de montaña, majadas, prados de siega, claros, linderos y setos.
- Puede aparecer junto a hayedos/robledales, pero raramente dentro del bosque cerrado.
- Altitud: **400–1.800 m**.
- Forma corros, semicírculos e hileras y muestra fidelidad espacial durante años.

### Suelo
- Preferencia clara por **suelos calizos**, ricos en bases y bien drenados.

### Vegetación indicadora
- Espino albar (*Crataegus monogyna*).
- Endrino (*Prunus spinosa*).
- Rosales silvestres.
- Setos y muros de piedra tradicionales.
- Estos elementos proporcionan sombra parcial y retención local de humedad.

### Fenología
- Marzo: apariciones puntuales.
- Abril: arranque fuerte.
- **Mayo: máximo**.
- Junio: todavía importante.
- Julio: posible en alta montaña.
- No tiene una temporada otoñal útil.
- Fuerte desplazamiento con la altitud: cotas bajas pueden ir varias semanas por delante de pastizales altos.

### Clima
- Perfil general: **primavera húmeda y fresca**.
- Sporas utiliza precipitación acumulada + altitud para estimar el avance de la temporada.
- La capa forestal es secundaria; la variable de cobertura importante sería pradera/pasto.

### Distribución
- Norte e interior montañoso.
- Pirineos catalán y aragonés.
- Berguedà, Alt Urgell, Solsonès, Pallars, Ripollès, Cerdanya, Val d'Aran.
- Cordillera Cantábrica.
- País Vasco y Navarra.
- Sistema Ibérico / Albarracín.
- Soria y Burgos.
- Presencia más puntual en Sistema Central.
- Sporas no considera bien respaldada una distribución normal en sistemas cálidos del sur/suroeste.

### Variables candidatas
- precipitación acumulada de primavera;
- altitud;
- temperatura media/mínima de primavera;
- pradera/pastizal;
- suelo calizo;
- setos y bordes;
- arbustos indicadores;
- humedad de suelo;
- persistencia histórica del rodal.

---

## 3.5 *Boletus aestivalis* — Hongo de verano / Boleto reticulado

**Fuente:** https://sporas.io/especies/boletus-aestivalis

### Perfil básico
- Ectomicorrícico.
- Hospedadores principales:
  - *Quercus robur*;
  - *Q. petraea*;
  - *Q. pyrenaica*;
  - *Fagus sylvatica*;
  - *Castanea sativa*;
  - *Quercus ilex*.
- Coníferas solo de forma ocasional, especialmente abeto.
- Bosques maduros, abiertos y luminosos.
- Linderos, claros, caminos y bordes de pista.
- Altitud: **300–1.600 m**.

### Suelo
- Ácido o silíceo.
- Suelto y bien drenado.
- Poca hojarasca acumulada.

### Exposición
- Relativamente heliófilo dentro del grupo *edulis*, pero necesita humedad.
- Sporas destaca laderas frescas y **orientaciones norte/nordeste**.
- Umbrías favorables para conservar reserva hídrica durante el verano.

### Fenología y clima
- Ventana real junio–septiembre.
- **Máximo en agosto**.
- Cola en octubre.
- Umbral térmico más alto que otros boletos nobles.
- Factor limitante principal en verano: **agua disponible**, no el calor por sí solo.
- Escenario favorable:
  - tormenta de verano;
  - suelo que ya conserva reserva;
  - ladera fresca/umbría;
  - suelo todavía cálido.
- Brotes orientativos de **10–15 días** tras lluvia importante.
- El desfase depende de:
  - acumulado previo;
  - temperatura del suelo;
  - exposición;
  - estado del micelio.

### Distribución
- Mitad norte y cuadrante occidental.
- Bosques atlánticos y pirenaicos.
- Galicia, Asturias, Cantabria, País Vasco, Navarra.
- Pirineos.
- Noroeste, Sistema Central y Sistema Ibérico.
- Salamanca, Cáceres, Zamora.
- Norte de Portugal.

### Variables candidatas
- lluvia de tormenta;
- precipitación acumulada antecedente;
- reserva hídrica del suelo;
- temperatura del suelo;
- orientación N/NE;
- sombreado;
- cobertura de frondosas;
- edad/apertura del bosque;
- altitud;
- suelo silíceo/ácido.

---

## 3.6 *Amanita caesarea* — Oronja

**Fuente:** https://sporas.io/especies/amanita-caesarea

### Perfil básico
- Ectomicorrícica obligada.
- Hospedadores:
  - encina (*Quercus ilex*);
  - alcornoque (*Q. suber*);
  - robles y quejigos;
  - castaño (*Castanea sativa*).
- Las referencias bajo coníferas se consideran dudosas para el contexto ibérico.
- Altitud: **300–1.000 m**.
- Bosques mediterráneos de frondosas, dehesas y masas aclaradas.

### Suelo
- Fuerte preferencia por sustratos **silíceos y ácidos**.
- Bien drenados.
- Evita calizas compactas y suelos encharcados.

### Exposición
- **Termófila**.
- Claros soleados.
- Bordes de camino.
- Laderas de **solana**.
- Bosque aclarado y pastoreado.
- Evita la espesura umbría.

### Fenología y clima
- Final de verano y otoño.
- Agosto: arranque.
- Septiembre–octubre: periodo principal.
- Noviembre: cola según año.
- Primer disparador: recarga de agua del perfil del suelo.
- Segundo: **descenso térmico suave**, especialmente nocturno, después de lluvias/tormentas.
- Tormentas intensas se asocian a fructificaciones más abundantes.
- Los plazos citados varían desde unas 2 semanas hasta más de 6; Sporas rechaza un retraso fijo.
- Variables modificadoras: humedad previa, temperatura y suelo.

### Distribución
- Arco mediterráneo.
- Encinares, alcornocales, quejigares y castañares termófilos.
- Mayor afinidad por regiones con sustrato silíceo y clima cálido.

### Variables candidatas
- acumulado de precipitación;
- reserva hídrica;
- lluvia de tormenta;
- descenso de temperatura nocturna;
- temperatura del suelo;
- orientación/solana;
- radiación;
- altitud;
- Quercus/Castanea;
- suelo ácido/silíceo;
- drenaje.

---

## 3.7 *Boletus aereus* — Hongo negro / Boleto bronce

**Fuente:** https://sporas.io/especies/boletus-aereus

### Perfil básico
- Ectomicorrícico.
- Hospedadores:
  - encina;
  - alcornoque;
  - robles melojos y quejigos;
  - castaño.
- Sporas afirma que **no se asocia a coníferas**.
- Hábitat emblemático: dehesa y montado.
- Arbolado adulto, espaciado y abierto.
- Altitud: **100–1.200 m**.

### Suelo
- Ácido o silíceo.
- Suelto.
- Bien drenado.
- Pobre.

### Exposición y temperatura
- Muy **termófilo**.
- **Heliófilo**.
- Prefiere masas abiertas y soleadas.
- Necesita suelo caliente; se retira cuando llegan los primeros fríos.

### Fenología
- Apariciones puntuales en primavera lluviosa y cálida.
- Julio: repunte.
- Agosto: entrada en carga.
- **Septiembre: máximo**.
- Octubre: todavía bueno.
- Noviembre: retirada rápida.

### Lluvia y disparo
- Escenario ideal: tormenta de agosto/principios de septiembre sobre suelo caliente.
- Se citan ciclos de aproximadamente 1–2 semanas, pero Sporas los considera variables.
- Factores que modifican el retraso:
  - cantidad de agua;
  - temperatura posterior;
  - orientación;
  - suelo;
  - estado de la micorriza.

### Distribución
- Cuadrante suroeste y oeste.
- Extremadura.
- Andalucía occidental.
- Salamanca y Zamora.
- Galicia en carballo/castaño.
- Portugal.
- Localmente Cataluña, cornisa cantábrica, Navarra y Sistema Ibérico.

### Variables candidatas
- temperatura alta del suelo;
- lluvia de tormenta;
- precipitación antecedente;
- orientación/radiación;
- Quercus/Castanea;
- suelo silíceo;
- apertura de copa;
- altitud;
- llegada de primeras heladas.

---

## 3.8 *Cantharellus cibarius* — Rebozuelo / Chantarela

**Fuente:** https://sporas.io/especies/cantharellus-cibarius

### Perfil básico
- Ectomicorrícico.
- Hospedadores publicados:
  - roble;
  - haya;
  - castaño;
  - pino;
  - eucalipto.
- Sporas lo presenta como la especie con uno de los abanicos de hábitat más amplios del catálogo.
- Altitud: **50–1.500 m**.

### Suelo y litología
- Suelos ácidos, pobres y bien drenados.
- Sustratos silíceos:
  - granito;
  - gneis;
  - cuarcita;
  - esquisto;
  - pizarra.

### Microhábitat
- Ambientes húmedos.
- Taludes musgosos.
- Vaguadas.
- Márgenes de arroyo.
- Umbrías.
- El **musgo** se considera uno de los mejores indicadores porque retiene humedad y amortigua el calor estival.

### Fenología
- Abril/mayo: testimonial.
- Junio: apertura real de temporada.
- Julio/agosto: incremento.
- **Septiembre: máximo**.
- Octubre: muy alto.
- Noviembre: descenso.
- Diciembre: prácticamente cierre.
- Sporas lo describe como la ventana útil más larga del catálogo.

### Clima
- Responde más a **humedad sostenida** que a un episodio puntual.
- Es de las especies más exigentes en lluvia acumulada.
- Tres factores que alargan su campaña:
  - amplitud de hábitat;
  - clima atlántico con tormentas estivales;
  - musgo y umbrías que amortiguan calor y pérdida de agua.

### Distribución
- Iberia húmeda: cornisa cantábrica, Galicia, País Vasco, Pirineos, montañas del norte y noroeste.
- Castañares y eucaliptales húmedos.
- La ficha advierte que algunas citas antiguas mediterráneas atribuidas a *C. cibarius* pueden corresponder a *Cantharellus pallens*.

### Variables candidatas
- lluvia acumulada en ventana larga;
- humedad edáfica;
- humedad atmosférica;
- persistencia de humedad;
- cobertura de musgo;
- índice topográfico de humedad;
- proximidad a arroyos;
- orientación/umbría;
- litología silícea;
- hospedador;
- altitud.

---

## 3.9 *Boletus edulis* — Boleto / Hongo

**Fuente:** https://sporas.io/especies/boletus-edulis

### Perfil básico
- Ectomicorrícico.
- Hábitats/hospedadores:
  - pinares, especialmente *Pinus sylvestris* y pino negral;
  - hayedos;
  - robledales/melojares;
  - castañares;
  - abetales;
  - jarales de *Cistus ladanifer*.
- La asociación con *Cistus ladanifer* está documentada y ha sido objeto de trabajos de producción/micorrización.
- Altitud: **600–1.800 m**, algo menor en zonas atlánticas.

### Suelo
- Ácido a neutro.
- Suelto.
- Acículas/hojarasca no excesivamente compactadas.
- Claros, bordes y calveros frecuentemente favorables.
- Brezo, arándano y helecho aparecen como indicadores de ambiente compatible.

### Clima y agua
- Necesita **reserva de agua en el suelo**.
- Sporas destaca el contraste térmico: noches frescas y días templados.
- Temporada principal:
  - septiembre: arranque;
  - **octubre: máximo**;
  - noviembre: buena continuidad;
  - diciembre: descenso.
- Apariciones menores en primavera y agosto tras tormentas, pero sin constituir una segunda temporada.

### Variables explicativas destacadas por Sporas
- lluvia acumulada;
- descenso térmico;
- humedad mantenida;
- reserva previa de agua del suelo.
- Se mencionan series largas de pinares de *Pinus sylvestris* en Soria donde:
  - la precipitación de agosto–noviembre se relaciona con producción;
  - la reserva hídrica del suelo aparece como variable particularmente explicativa del inicio.
- Gran variabilidad interanual.
- No existe un “X días después de llover” universal.

### Distribución
- Sistema Ibérico.
- Soria, Burgos, Teruel/Albarracín.
- Pirineo/Prepirineo.
- Cordillera Cantábrica.
- Sistema Central.
- Serranía de Cuenca/Montes Universales.
- Sierras occidentales y suroccidentales en jaral.
- Portugal norte/centro.

### Variables candidatas
- precipitación 7/14/21/30+ días;
- acumulado agosto–noviembre;
- reserva hídrica antecedente;
- déficit hídrico previo;
- temperatura máxima/mínima;
- contraste día/noche;
- humedad relativa;
- altitud;
- hospedador;
- cobertura/madurez forestal;
- suelo ácido-neutro;
- apertura/borde;
- vegetación indicadora.

---

## 3.10 *Boletus pinophilus* — Boleto de pino

**Fuente:** https://sporas.io/especies/boletus-pinophilus

### Perfil básico
- Ectomicorrícico.
- Hospedador principal: **Pinus sylvestris**.
- Secundarios: hayas, robles y castaños; menciones de brezales.
- Preferencia por bosque maduro y árboles grandes.
- Altitud:
  - cabecera de ficha: **600–2.000 m**;
  - texto ecológico: núcleo habitual alrededor de **1.000–1.800/2.000 m**.
- Bosque aireado, con buena iluminación y poco sotobosque.
- Laderas/pendientes preferibles a zonas llanas encharcadas.

### Suelo
- Ácido.
- Suelto.
- Bien drenado.
- Rico en materia orgánica.

### Fenología
- Rasgo distintivo: **doble ventana**.
- Repunte primaveral menor: abril–junio.
- Gran campaña: septiembre–noviembre.
- **Octubre: máximo**.
- Cola posible en diciembre a baja cota.
- La altitud retrasa el calendario.

### Clima
- Requiere precipitación acumulada suficiente.
- Temperaturas suaves.
- Humedad ambiental sostenida.
- Penalizadores:
  - sequía;
  - golpes de calor;
  - heladas tempranas;
  - **viento seco**.
- Orientación de campo: alrededor de 10–15 días / unas dos semanas tras lluvias importantes.
- La propia ficha insiste en que es solo un promedio.

### Distribución
- Tercio norte y sistemas montañosos.
- Grandes pinares de Castilla y León.
- Soria, Segovia, Ávila, León.
- Albarracín.
- Pirineo/Prepirineo.
- Navarra.
- Sistema Ibérico y Central.
- Zonas montañosas occidentales.

### Variables candidatas
- Pinus sylvestris;
- madurez del pinar;
- altitud;
- lluvia acumulada;
- humedad ambiental;
- temperatura;
- viento / VPD;
- orientación;
- drenaje;
- suelo ácido;
- ventana primaveral vs otoñal separadas.

---

## 3.11 *Craterellus cornucopioides* — Trompeta negra

**Fuente:** https://sporas.io/especies/craterellus-cornucopioides

### Perfil básico
- Ectomicorrícica.
- Asociada principalmente a fagáceas:
  - robles/quejigos;
  - hayas;
  - castaños;
  - encinares y alcornocales frescos.
- Altitud: **200–1.600 m**.

### Suelo y microhábitat
- Suelos frescos.
- Mantillo abundante.
- Hojarasca profunda.
- Musgo.
- Umbrías.
- Vaguadas.
- Proximidad a arroyos.
- Tendencia a suelos básicos/calizos, aunque también aparece en sustratos silíceos; Sporas aconseja tratarlo como tendencia, no condición absoluta.

### Fenología
- Principalmente septiembre–noviembre.
- **Octubre: máximo**.
- Noviembre todavía muy favorable.
- Fructificaciones estivales solo testimoniales en bosques atlánticos muy húmedos.
- Presenta comportamiento vecero: algunos rodales mediterráneos pueden producir masivamente solo ciertos años.

### Clima
- Necesita:
  - lluvia acumulada suficiente;
  - hojarasca capaz de conservar esa humedad;
  - temperaturas otoñales suaves;
  - ausencia de heladas fuertes.
- Sin regla fija de días tras lluvia.

### Distribución
- Mitad norte: Cantábrico, Pirineo/Prepirineo, Sistema Ibérico, Galicia, Sistema Central.
- Más irregular en ambientes mediterráneos del sur/suroeste.
- También montañas béticas y Portugal.

### Variables candidatas
- lluvia acumulada;
- humedad de suelo;
- profundidad de hojarasca;
- índice de humedad topográfica;
- proximidad a cauces;
- sombra/orientación;
- temperatura otoñal;
- heladas;
- hospedadores fagáceos;
- tendencia calcícola;
- vecería/efecto interanual.

---

## 3.12 *Macrolepiota procera* — Parasol / Apagador

**Fuente:** https://sporas.io/especies/macrolepiota-procera

### Perfil básico
- **Saprófita**, no micorrícica.
- Se alimenta de materia orgánica en descomposición.
- Hábitat:
  - claros herbosos;
  - pastizales;
  - praderas;
  - linderos;
  - dehesas;
  - majadas;
  - cortafuegos;
  - bordes de camino;
  - cunetas.
- Las asociaciones de la ficha con roble, encina, pino y castaño son **indicadores ambientales**, no hospedadores obligados.
- Altitud: **50–1.400 m**.

### Suelo
- Rico en materia orgánica.
- Bien drenado.
- Cierta actividad ganadera puede ser favorable.

### Fenología
- Mayo/junio: testimonial.
- Julio: inicio.
- Agosto: ascenso tras tormentas.
- Septiembre: muy fuerte.
- **Octubre: máximo**.
- Noviembre: todavía importante.
- Diciembre: cierre con hielos.

### Clima
- Disparador:
  - precipitación acumulada suficiente;
  - temperaturas suaves.
- Penaliza:
  - calor extremo;
  - heladas.
- El retraso depende de temperatura del suelo, exposición y estado del pastizal.
- Su gran carpóforo es vulnerable al viento como factor físico, aunque esto no equivale necesariamente a un disparador de fructificación.

### Distribución
- Muy extendida por toda la Península.
- Sigue la presencia de pastizales, claros y linderos más que masas forestales concretas.

### Variables candidatas
- precipitación acumulada;
- temperatura;
- suelo/pasto;
- materia orgánica;
- actividad ganadera;
- cobertura abierta;
- borde de bosque;
- viento fuerte;
- altitud.

---

## 3.13 *Cantharellus lutescens* — Gula de monte / Trompeta amarilla

**Fuente:** https://sporas.io/especies/cantharellus-lutescens

### Perfil básico
- Micorrícica.
- Hábitat de referencia: pinares de montaña.
- Hospedadores citados:
  - *Pinus sylvestris*;
  - *Pinus nigra*.
- También hayedos y castañares húmedos.
- Altitud: **400–1.800 m**.

### Microhábitat
- El **musgo** es la constante ecológica más destacada.
- Zonas de acumulación de acículas.
- Bordes de arroyo.
- Manantiales.
- Laderas umbrías.
- Turberas/tremedales.
- Ambientes de humedad persistente.
- Especie umbrófila.

### pH / suelo
- Existe una contradicción bibliográfica que Sporas conserva explícitamente:
  - norte de Europa: asociación con suelos ácidos/turberas;
  - fuentes ibéricas: numerosos pinares calcáreos y preferencia básica/neutra.
- Conclusión de Sporas: el **pH no sería el factor limitante principal**; más importante sería la presencia de musgo y humedad sostenida.

### Fenología
- Septiembre: testimonial.
- Octubre: arranque fuerte.
- **Noviembre: máximo**.
- Diciembre: muy productivo.
- Enero: residual.
- Puede llegar incluso a febrero.
- Es la especie más tardía del catálogo.

### Clima
- Resiste primeras heladas mejor que muchos otros comestibles.
- Responde a:
  - acumulados de precipitación de **3–4 semanas**;
  - temperaturas suaves-frías;
  - humedad retenida por musgo.
- No hay una regla fija de días tras lluvia.

### Distribución
- Pinares húmedos y musgosos del norte.
- Sistemas montañosos ibéricos.
- Navarra, Aragón, Albarracín y otras áreas de pinar montano.
- También hayedos/castañares húmedos.

### Variables candidatas
- lluvia acumulada 21–30 días;
- humedad de suelo;
- cobertura de musgo;
- umbría;
- proximidad a manantiales/arroyos;
- pinar de montaña;
- altitud;
- temperatura fría pero no extrema;
- heladas moderadas;
- pH con peso bajo/incierto.

---

## 3.14 *Lactarius deliciosus* — Níscalo / Rovelló

**Fuente:** https://sporas.io/especies/lactarius-deliciosus

### Perfil básico
- Ectomicorrícico estricto de **Pinus**.
- Sin pino, Sporas considera descartable la especie.
- Pinos citados:
  - *Pinus sylvestris*;
  - *P. nigra*;
  - *P. pinaster*;
  - *P. halepensis*;
  - *P. pinea*;
  - *P. uncinata*.
- Altitud: **100–1.600 m**.

### Estructura forestal
- Preferencia notable por **pinares jóvenes o de pocas décadas** frente a masas viejas y densas.
- Mejor producción con:
  - árboles en crecimiento activo;
  - pinar aclarado;
  - pinocha no demasiado gruesa;
  - entrada de luz.
- Claros, taludes, cortafuegos, bordes de pista y linderos son especialmente favorables.

### Suelo
- Tolera un rango amplio.
- Preferencia por calizos o poco ácidos.

### Fenología
- Septiembre: arranque.
- Octubre: fuerte.
- **Noviembre: máximo**, casi empatado con octubre.
- Diciembre: cola notable.
- Puede prolongarse a baja cota hasta las primeras heladas fuertes.
- No hay temporada primaveral útil.

### Clima
- Disparador:
  - lluvia acumulada suficiente en semanas previas;
  - descenso térmico otoñal;
  - ausencia de heladas fuertes.
- Sporas lo considera relativamente regular/agradecido frente a otras especies.
- El retraso tras lluvia depende de:
  - agua total;
  - temperatura del suelo;
  - exposición;
  - estado/edad de la masa.

### Distribución
- Prácticamente todo el mapa peninsular de pinares.
- Castilla, Sistema Ibérico, Albarracín.
- Cataluña/Prepirineo/Pirineo.
- Sistema Central.
- Béticas.
- Galicia y norte de Portugal.
- Pinares mediterráneos litorales.

### Variables candidatas
- presencia obligatoria de Pinus;
- especie de pino;
- edad/estructura del pinar;
- cobertura de copa;
- espesor de pinocha;
- lluvia acumulada;
- descenso térmico;
- heladas;
- altitud;
- suelo calizo/poco ácido;
- borde/claros.

---

## 3.15 *Pleurotus eryngii* — Seta de cardo

**Fuente:** https://sporas.io/especies/pleurotus-eryngii

### Perfil básico
- No micorrícica.
- **Saprófita facultativa / parásita débil** de la raíz del cardo corredor (*Eryngium campestre*).
- El micelio coloniza raíces pivotantes senescentes o muertas.
- Fructifica muy cerca del cuello de la planta.
- Otras umbelíferas citadas para variedades relacionadas:
  - *Ferula communis*;
  - *Thapsia villosa*;
  - *Elaeoselinum asclepium*.
- Altitud: **0–1.500 m**.

### Hábitat
- Barbechos.
- Eriales.
- Páramos.
- Cunetas.
- Ribazos.
- Linderos.
- Pastizales.
- Secanos agrícolas/ganaderos.
- Preferencia por ambientes abiertos y soleados.
- La capa forestal tiene poca utilidad; lo importante es pradera/pastizal y, idealmente, la planta hospedante/sustrato.

### Suelo
- Básico o neutro.
- Suelto en superficie.
- Firme/compactado en profundidad.
- Puede favorecerle cierto pisoteo/compactación por ganado o maquinaria.

### Fenología
- **Bimodal**.
- Oleada principal:
  - octubre fuerte;
  - **noviembre máximo**;
  - diciembre residual.
- Segunda oleada:
  - marzo comienza;
  - abril–mayo productivos;
  - junio residual.
- Julio prácticamente nulo.

### Clima
- La raíz/sustrato está disponible todo el año; el limitante estacional es sobre todo **humedad suficiente**.
- Otoño: primeras lluvias sostenidas tras verano seco.
- Primavera: lluvias + subida moderada de temperatura antes del calor seco.
- La fructificación no es instantánea tras lluvia; Sporas recomienda dar unos días.
- No se proporciona un retraso universal.

### Distribución
- Meseta y valle del Ebro.
- Castilla y León.
- Castilla-La Mancha.
- Aragón.
- Navarra.
- Extremadura seca.
- Andalucía interior.
- Alentejo.
- Interior de Cataluña/Lleida.
- Rara en Galicia, cornisa cantábrica y bosques cerrados de montaña.

### Variables candidatas
- presencia/probabilidad de *Eryngium campestre*;
- pradera/pastizal/secano;
- uso agrícola/ganadero;
- humedad de suelo;
- lluvia otoñal y primaveral;
- temperatura moderada;
- suelo básico/neutro;
- compactación;
- exposición abierta;
- altitud.

---

# 4. Variables ecológicas recurrentes en el catálogo

La lectura transversal de las 15 fichas sugiere que Sporas organiza implícitamente la fructificación alrededor de varios bloques de variables.

## 4.1 Agua
Variables repetidas:
- precipitación acumulada en semanas previas;
- lluvia de tormenta;
- invierno húmedo;
- humedad mantenida;
- reserva hídrica antecedente;
- agua de deshielo;
- retención de agua por musgo/hojarasca;
- proximidad a vaguadas, manantiales o arroyos.

**Conclusión para Rainmapper:** no debería utilizarse solo precipitación acumulada. Conviene separar:
1. precipitación reciente;
2. reserva hídrica antecedente;
3. persistencia de humedad;
4. sequedad previa.

## 4.2 Temperatura
Patrones recurrentes:
- calentamiento de suelo en especies primaverales;
- suelo caliente + tormenta en especies termófilas;
- descenso térmico otoñal en especies de otoño;
- primeras heladas como factor de cierre;
- nieve/deshielo como señal fenológica específica.

## 4.3 Arbolado/hospedador
Hay especies donde es un filtro prácticamente obligatorio:
- *Lactarius deliciosus* → **Pinus**;
- *Boletus pinophilus* → fuerte prioridad de pino;
- *Boletus aereus* → frondosas mediterráneas;
- *Amanita caesarea* → Quercus/Castanea;
- *Hygrophorus marzuolus* → Pinus/Fagus/Betula.

En otras especies el arbolado es solo un **indicador de ambiente**:
- *Macrolepiota procera*;
- *Calocybe gambosa*;
- *Morchella esculenta*;
- *Pleurotus eryngii*.

## 4.4 Edad y estructura del bosque
Sporas diferencia explícitamente:
- bosque maduro favorable para varios boletos;
- pinar joven favorable para *Lactarius deliciosus*;
- masa densa desfavorable para varias especies;
- claros, linderos y bordes repetidamente favorables;
- bosque abierto/heliófilo frente a umbría/umbrófilo.

Esto sugiere que “tipo de bosque” es insuficiente: sería útil disponer de proxies de:
- edad;
- cierre de copa;
- densidad;
- borde forestal;
- distancia a claro/pista;
- estructura vertical.

## 4.5 Suelo y litología
Tendencias:
- ácido/silíceo: *B. edulis*, *B. pinophilus*, *B. aereus*, *B. aestivalis*, *A. caesarea*, *C. cibarius*, *H. marzuolus*, *A. ponderosa*;
- básico/calizo: *M. esculenta*, *C. gambosa*, tendencia de *C. cornucopioides*, *L. deliciosus*;
- amplio/contradictorio: *C. lutescens*;
- básico/neutro y secano: *P. eryngii*.

Litologías explícitas de interés:
- granito;
- gneis;
- cuarcita;
- esquisto;
- pizarra;
- caliza.

## 4.6 Orientación y microtopografía
Aparecen repetidamente:
- umbrías;
- solanas;
- N/NE;
- vaguadas;
- laderas;
- rellanos;
- proximidad a cauces;
- zonas de drenaje;
- terrenos encharcables como negativos.

El DEM de Rainmapper puede derivar buena parte de estas variables.

## 4.7 Viento
No es el predictor dominante en la mayoría de fichas, pero aparece de forma explícita:
- *Boletus pinophilus*: viento seco puede abortar/retrasar fructificación.
- *Macrolepiota procera*: carpóforo vulnerable físicamente al viento.

Para Rainmapper puede ser más útil modelar el viento junto con humedad y temperatura como proxy de **desecación / VPD / pérdida de humedad superficial**.

## 4.8 Perturbación
Especialmente importante en:
- *Morchella esculenta*: incendio previo, suelo removido, obras, crecidas, pistas.
- *Pleurotus eryngii*: uso agroganadero/compactación.
- *Macrolepiota procera*: actividad ganadera/materia orgánica.
- *Calocybe gambosa*: pastoreo, prados tradicionales, bordes y setos.

---

# 5. Posible clasificación de variables para Rainmapper

## Variables meteorológicas directas
- precipitación diaria;
- acumulado 3/7/14/21/30/45/60 días;
- días consecutivos húmedos;
- días desde última lluvia significativa;
- temperatura mínima;
- temperatura máxima;
- temperatura media;
- amplitud térmica;
- descenso térmico posterior a lluvia;
- humedad relativa;
- viento;
- heladas;
- nieve.

## Variables hidrológicas derivadas
- reserva hídrica estimada;
- déficit hídrico antecedente;
- índice de humedad persistente;
- secuencia lluvia → temperatura;
- agua de fusión de nieve.

## Variables DEM
- altitud;
- pendiente;
- orientación;
- insolación potencial;
- índice topográfico de humedad;
- vaguada/cresta;
- drenaje relativo.

## Variables de vegetación
- especie arbórea;
- tipo de bosque;
- cobertura;
- densidad;
- edad/madurez;
- borde forestal;
- distancia a claro;
- matorral indicador;
- musgo si existiera cartografía/proxy.

## Variables edáficas/geológicas
- pH o clase ácido/neutro/básico;
- litología;
- textura;
- drenaje;
- materia orgánica;
- profundidad;
- compactación.

## Variables de perturbación/uso
- incendio y años desde incendio;
- uso agrícola;
- pastizal;
- ganadería;
- pistas/caminos;
- áreas removidas.

---

# 6. Información de Sporas que NO debe convertirse directamente en un umbral

Los siguientes tipos de afirmaciones deben almacenarse como **evidencia cualitativa** hasta contrastarlas con bibliografía científica:

- “10–15 días después de la lluvia”.
- “unas dos semanas”.
- “temperaturas suaves”.
- “suelo caliente”.
- “lluvia abundante”.
- “humedad sostenida”.
- “bosque maduro”.
- “pinar joven”.
- “primavera húmeda”.
- “primeras heladas”.
- “suelos pobres”.
- “buena iluminación”.

La mejor práctica sería conservar:
- fuente;
- especie;
- variable;
- sentido del efecto;
- nivel cualitativo;
- ventana temporal;
- texto resumido;
- confianza;
- evidencia científica posterior.

---

# 7. Diferencias especialmente útiles para discriminar especies

| Especie | Rasgo predictivo diferencial |
|---|---|
| *Amanita ponderosa* | invierno lluvioso + calentamiento primaveral en dehesa ácida de baja cota |
| *H. marzuolus* | nieve/deshielo + pinar/hayedo montano + suelo frío |
| *M. esculenta* | perturbación del suelo/incendio + primavera |
| *C. gambosa* | pradera caliza + fuerte gradiente altitudinal de primavera |
| *B. aestivalis* | tormentas estivales + suelo cálido pero con reserva + N/NE |
| *A. caesarea* | suelo silíceo cálido + Quercus + solana + tormentas fin de verano |
| *B. aereus* | máxima termofilia + Quercus/Castanea + suelo cálido |
| *C. cibarius* | humedad persistente + musgo + amplia ventana estival/otoñal |
| *B. edulis* | reserva hídrica + descenso térmico + otoño de montaña |
| *B. pinophilus* | pino maduro + altitud + doble ventana + sensibilidad a viento seco |
| *C. cornucopioides* | hojarasca profunda + umbría húmeda + otoño |
| *M. procera* | pastizal/lindero + materia orgánica, sin dependencia micorrícica |
| *C. lutescens* | musgo + humedad persistente + ventana muy tardía |
| *L. deliciosus* | Pinus obligatorio + preferencia por pinar joven/aclarado |
| *P. eryngii* | cardo corredor + secano + bimodalidad primavera/otoño |

---

# 8. Observaciones sobre el modelo de Sporas

De las propias fichas se deduce que Sporas evita tratar el calendario mensual como predictor suficiente. Repite en numerosas especies que el visor combina:

- **pluviometría acumulada**;
- **altitud**;
- **arbolado real del Mapa Forestal de España**.

Dependiendo de la especie, la explicación textual añade factores no necesariamente visibles en el modelo publicado:
- temperatura;
- humedad del suelo;
- humedad ambiental;
- orientación;
- reserva hídrica;
- nieve/deshielo;
- viento seco;
- madurez del bosque;
- perturbación;
- musgo;
- litología.

Esto hace que las fichas sean especialmente interesantes para Rainmapper como **fuente de hipótesis y variables candidatas**, aunque no publiquen pesos, ecuaciones ni umbrales numéricos completos del predictor de Sporas.

## 8.1 Interpretación de «lluvia de activación»

El manual del visor distingue dos magnitudes:

- **lluvia acumulada**: milímetros sumados en los días inmediatamente previos
  dentro del periodo visible;
- **lluvia de activación**: lluvia de un periodo anterior, desplazado semanas
  respecto de la fecha consultada según la especie, que el sistema considera
  capaz de haber iniciado la fructificación y que interviene en su filtro de
  lluvia.

La segunda cifra debe interpretarse como un acumulado calculado, no como el
umbral mínimo de activación. Sin embargo, la interfaz no muestra las fechas de
inicio y fin, duración, umbral aplicado, fuentes y pesos meteorológicos ni la
transformación posterior. El término sugiere una relación causal que la
información pública no permite comprobar. Para Rainmapper se adopta el nombre
neutral **señal hídrica antecedente** mientras esa relación no se demuestre con
observaciones y evaluación fuera de muestra.

La idea útil que se conserva es la secuencia temporal:

`recarga hídrica -> espera biológica variable -> condiciones de fructificación -> florada`

No se conservarán como reglas los acumulados o filtros concretos de Sporas. Se
evaluarán como candidatas ventanas desplazadas, episodios de tormenta, días
desde lluvia, reserva hídrica, descenso térmico posterior y desecación. Si una
señal resulta útil deberá demostrar mejora de calibración y Brier en hold-out
agrupado por floradas y, posteriormente, en predicciones prospectivas.

## 8.2 Contrastes exploratorios del visor (2026-09-04)

Estos casos proceden de lecturas manuales del visor y sirven para detectar
preguntas, no para evaluar científicamente Rainmapper ni Sporas:

| Especie y zona | Sporas | Rainmapper | Observación |
|---|---:|---:|---|
| *Amanita caesarea*, Olvan | 63,4 % | 69 % | Coincidencia puntual con historiales de lluvia que no pudieron reconciliarse. |
| *Lactarius deliciosus*, Riu de Cerdanya | 9,5 % | 100 % | Divergencia extrema pese a lluvia reciente del mismo orden; Rainmapper usó fallback global de especie. |

En Olvan, Sporas mostró 18,1 mm en 15 días y un máximo diario de 13,4 mm el
24 de agosto. Las estaciones AEMET visibles de Berga y Prats de Lluçanès
mostraban respectivamente 3,0 y 0,0 mm en 15 días; la interfaz indicaba que la
celda interpolaba varias fuentes, pero no permitió reconstruir su valor.

En Riu de Cerdanya, Sporas mostró 22,7 mm en 15 días y Rainmapper 28,7 mm en
14 días, valores comparables a escala operativa. No obstante, la ficha de
Sporas mantuvo una altitud de 1.073 m al seleccionar dos puntos próximos a
curvas de nivel de aproximadamente 1.850 y 2.050 m. La estación SAIH Ebro
visible más cercana figuraba a 1.031 m y con 48 mm en 15 días, por lo que ni la
altitud ni la precipitación de la ficha coincidían directamente con el punto o
con esa estación. La información disponible no permite determinar si se trata
de una celda gruesa, un agregado, otra fuente o un defecto del visor.

Conclusiones metodológicas:

- los porcentajes de Sporas son una comparación externa exploratoria, no una
  variable objetivo ni una referencia de calibración;
- no deben compararse porcentajes sin asegurar igualdad de coordenada, fecha,
  definición, ventana meteorológica y escala espacial;
- la coincidencia de dos porcentajes puede ser casual y la divergencia no dice
  por sí sola cuál es correcto;
- la ventaja verificable que debe perseguir Rainmapper es la trazabilidad de
  cada entrada, transformación, artefacto y decisión;
- la verdad de evaluación será la florada observada posteriormente y registrada
  sin utilizar información futura.

## 8.3 Elementos de producto aprovechables

Sin copiar los umbrales opacos del visor, Rainmapper puede estudiar:

- separar visualmente lluvia reciente, señal antecedente y estado hídrico;
- mostrar una curva temporal y el día de máximo esperado;
- diferenciar datos observados, interpolados y previstos;
- presentar meteorología y predicción en una misma explicación;
- atribuir, cuando el método lo permita, qué ventana o episodio contribuye a la
  probabilidad y cuánto cambia esta al retirarlo;
- mostrar siempre procedencia, cobertura y resolución espacial, evitando una
  precisión puntual que los datos no sostengan.

---

# 9. Fuentes

- Catálogo general: https://sporas.io/especies
- *Amanita ponderosa*: https://sporas.io/especies/amanita-ponderosa
- *Hygrophorus marzuolus*: https://sporas.io/especies/hygrophorus-marzuolus
- *Morchella esculenta*: https://sporas.io/especies/morchella-esculenta
- *Calocybe gambosa*: https://sporas.io/especies/calocybe-gambosa
- *Boletus aestivalis*: https://sporas.io/especies/boletus-aestivalis
- *Amanita caesarea*: https://sporas.io/especies/amanita-caesarea
- *Boletus aereus*: https://sporas.io/especies/boletus-aereus
- *Cantharellus cibarius*: https://sporas.io/especies/cantharellus-cibarius
- *Boletus edulis*: https://sporas.io/especies/boletus-edulis
- *Boletus pinophilus*: https://sporas.io/especies/boletus-pinophilus
- *Craterellus cornucopioides*: https://sporas.io/especies/craterellus-cornucopioides
- *Macrolepiota procera*: https://sporas.io/especies/macrolepiota-procera
- *Cantharellus lutescens*: https://sporas.io/especies/cantharellus-lutescens
- *Lactarius deliciosus*: https://sporas.io/especies/lactarius-deliciosus
- *Pleurotus eryngii*: https://sporas.io/especies/pleurotus-eryngii

---

## 10. Uso recomendado del documento

Este archivo debería considerarse una **captura de conocimiento de Sporas.io** para comparación con los perfiles científicos de Rainmapper.

Siguiente fase recomendada, todavía no realizada en este documento:

1. localizar `mushroom_profiles.json`;
2. cruzar las especies existentes de Rainmapper con estas 15;
3. identificar especies nuevas;
4. comparar campo por campo;
5. generar una matriz:
   `Rainmapper actual | Sporas | literatura científica | discrepancia | acción propuesta`;
6. convertir únicamente las evidencias suficientemente respaldadas en parámetros del predictor.
