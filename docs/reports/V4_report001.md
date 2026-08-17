# Biology V4 — Informe 001

Fecha: 2026-08-15
Estado: evaluación técnica local completada, pero sus resultados meteorológicos
están en revisión por una auditoría posterior de las series históricas oficiales.
V4 no es candidata operativa.

> **Aviso de revisión (2026-08-15):** después de cerrar la primera evaluación se
> detectaron huecos sistemáticos en el histórico de Meteocat y una pérdida de
> variables en el normalizador histórico de AEMET. Además, el benchmark inicial
> no aplicó todavía el contrato IDW espacial a temperatura y humedad. Por tanto,
> las cifras de este informe describen fielmente la ejecución realizada, pero no
> deben utilizarse para decidir entre V2, V3 y V4 hasta reconstruir las series y
> repetir la comparación sobre las mismas observaciones.

Este informe desarrolla los resultados de Biology V4. Es importante separar
tres preguntas distintas:

1. si las nuevas variables mejoran la predicción;
2. si hacen las predicciones diarias físicamente más coherentes;
3. si el código calcula exactamente lo mismo al entrenar que al predecir.

## 1. Comparación V2/V3/V4 sobre filas idénticas

Para que la comparación fuera justa, cada enfrentamiento utilizó exactamente
las mismas observaciones en las tres versiones:

- `fixed_gap`: 167 filas comunes para `core`; 162 cuando se exigen las
  variables V4 ampliadas;
- `lag_event`: 674 filas comunes para `core`; 656 para los perfiles ampliados.

Las observaciones restantes no se han borrado: siguen en sus benchmarks, pero
no intervienen en esa comparación concreta porque alguna versión no dispone de
todos los datos necesarios.

Cada especie se evaluó separadamente con los seis algoritmos ML:

- regresión logística;
- random forest;
- extra trees;
- gradient boosting;
- KNN;
- SVM RBF.

No se calculó un «Brier medio de todas las especies», porque podría ocultar que
una versión mejora mucho una especie y empeora otra. Se comparó dirección por
dirección: especie, algoritmo, contrato y partición temporal. En Brier, cuanto
menor es el valor, mejor.

El resultado general es que no existe un ganador universal:

- V3 suele superar a V2, pero no en todas las especies y algoritmos;
- V4 ampliada no supera consistentemente a V3;
- algunas variables V4 ayudan a unas especies y perjudican a otras.

## 2. V4 `core` reproduce exactamente V3

El perfil V4 `core` contiene las mismas variables predictivas que V3:

- lluvia IDW del área hasta 21 días;
- racha seca;
- temperaturas mínima y máxima;
- humedad relativa mínima y máxima;
- horizonte, únicamente en `lag_event`.

Se ejecutaron V3 y V4 `core` con las mismas filas, particiones y algoritmos.
Todos los Brier resultaron idénticos.

Esto es una prueba de control importante: demuestra que el comparador no
favorece artificialmente a V4. Cuando V4 ampliada cambia un resultado, el
cambio procede de sus variables nuevas, no de diferencias accidentales en el
entrenamiento o en la división train/test.

## 3. El balance climático mejora continuidad, pero no siempre Brier

El balance climático combina causalmente:

- lluvia;
- temperatura mínima y máxima;
- evaporación estimada;
- memoria de los últimos 7, 14, 21 y 30 días.

La idea es aproximar si el agua recibida se conserva o se pierde por
evaporación. Esto introduce memoria física y evita que cada día se interprete
como un hecho independiente.

En las secuencias diarias, el resultado es favorable:

- `fixed_gap`, grupos de 7 días: los días aislados bajan de 98 a 77;
- `fixed_gap`, grupos de 14 días: bajan de 105 a 62;
- en los cuatro horizontes `lag_event` también baja el total de días aislados;
- la variación diaria de probabilidad disminuye en una mayoría clara de
  secuencias.

Es decir, aparecen menos casos del tipo «lunes sí, martes no, miércoles sí».

Pero al comparar contra observaciones reales mediante Brier, el resultado no
es general:

- en `fixed_gap`, el balance empeora más combinaciones especie–algoritmo de las
  que mejora;
- en `lag_event`, mejoras y empeoramientos quedan aproximadamente equilibrados;
- ayuda especialmente a *Boletus edulis* y *Boletus pinophilus*;
- perjudica claramente a *Boletus aereus* y *Morchella* en este conjunto de
  datos.

Por tanto, el balance produce curvas más coherentes, pero todavía no demuestra
que acierte mejor de forma general. Una predicción más suave no es
necesariamente una predicción más correcta.

## 4. SoilGrids 0–30 cm

El depósito de suelo intenta estimar cuánta agua queda disponible después de:

- lluvia;
- evapotranspiración;
- capacidad de retención SoilGrids;
- drenaje cuando se supera la capacidad;
- secado acumulado;
- recarga reciente.

Se calcula primero por microárea y luego se resume para el área. No se segmentan
las observaciones por microárea ni se crean modelos diferentes por área.

La variante principal probada fue `wv0033_0_30cm`, aproximadamente la capacidad
de agua disponible entre 0 y 30 cm usando la retención SoilGrids a 33 kPa.

Sus resultados fueron desfavorables:

- en `fixed_gap`, frente al balance, los días aislados pasan de 67 a 81 con
  grupos de 14;
- con grupos de 7 quedan prácticamente equilibrados, pero ligeramente peor:
  81 a 84;
- en `lag_event`, normalmente aumentan tanto los días aislados como la
  variación diaria;
- en el benchmark de Brier tampoco fue un ganador general.

Esto no significa que la humedad del suelo sea biológicamente irrelevante.
Significa que esta aproximación concreta es todavía demasiado simplificada o
que faltan observaciones para aprovecharla. Entre sus limitaciones están:

- SoilGrids es una estimación a 250 m;
- todavía no corrige fragmentos gruesos;
- no modela raíces por especie;
- no modela bien interceptación forestal, escorrentía o vegetación;
- no está calibrada con mediciones locales de humedad del suelo.

Por eso se conserva calculada, documentada, entrenable y validable, pero
desactivada para predicción. Reactivarla no requeriría rediseñarla desde cero.

## 5. Evaluación de continuidad

No se midió continuidad usando solamente fechas de salidas separadas, porque
eso habría confundido ausencia de observación con ausencia de setas.

Se reconstruyeron días consecutivos reales alrededor de las observaciones del
hold-out:

- ventanas de 14 días antes y después;
- meteorología disponible únicamente hasta el corte de cada día;
- por especie y área;
- seis algoritmos;
- `fixed_gap`;
- `lag_event` con horizontes 1, 2, 3 y 7;
- particiones de florada de 7 y 14 días.

Para cada secuencia se midieron:

- días positivos aislados: no/sí/no;
- días negativos aislados: sí/no/sí;
- variación total de la probabilidad;
- duración de las rachas;
- huecos reales de datos;
- cambios entre etiquetas observadas.

No se modificó ninguna probabilidad durante esta medición.

## 6. Solo hay 50 etiquetas semanales para aprender continuidad

Aunque se pueden reconstruir centenares de días meteorológicos, la mayoría no
tienen una salida de setas observada. Tener meteorología para un día no equivale
a saber si había setas ese día.

Dentro de las secuencias semanales evaluables hay 50 etiquetas únicas:

- 28 favorables;
- 22 desfavorables.

Además, están repartidas entre distintas especies y áreas. Eso es demasiado
poco para aprender honestamente tres estados como:

- inicio de florada;
- mantenimiento;
- final de florada.

Un modelo de continuidad entrenado ahora probablemente aprendería reglas
inestables o repetiría muchas veces la misma escasa evidencia.

Por eso no se añadió una regla manual del tipo «mantener la predicción positiva
siete días». Eso podría verse bien, pero impondría artificialmente la duración
que precisamente queremos que el sistema aprenda.

El contrato de continuidad queda diseñado y desactivado para reevaluarlo cuando
haya más observaciones.

## 7. Paridad entre entrenamiento e inferencia

Esta prueba comprueba que una misma fecha produce exactamente las mismas
variables mediante:

- la ruta que construye el benchmark de entrenamiento;
- la ruta que utilizaría una inferencia diaria.

Se compararon campo por campo:

| Contrato | Muestras | Perfiles |
| --- | ---: | --- |
| `fixed_gap` | 399 | core, balance y suelo |
| `lag_event` | 1.596 | core, balance y suelo |

Resultado:

- cero valores diferentes;
- cero discrepancias de elegibilidad;
- cero campos de calidad entrando en `X`.

Esto evita un problema peligroso: entrenar con una fórmula de lluvia,
temperatura o suelo y luego predecir con otra ligeramente distinta.

Lo pendiente es comprobar esa misma paridad dentro del empaquetado real
HA–worker. Eso solo tiene sentido cuando se decida integrar una versión.

## 8. Por qué V4 queda `proposed`

Los estados significan:

- `active`: versión usada en producción;
- `candidate`: implementación que justifica entrenar una generación candidata
  y pasar gates operativos;
- `proposed`: versión implementada y evaluable, pero que todavía no justifica
  una candidatura;
- `reference`: versión conservada aunque ya no sea activa.

V4 queda como `proposed` porque:

- no demuestra una mejora de Brier general frente a V3/V2;
- el resultado cambia bastante por especie;
- el balance mejora continuidad, pero no suficientemente el acierto observado;
- el suelo empeora los resultados generales;
- faltan etiquetas para aprender continuidad;
- no existe un perfil V4 único claramente preferible.

Esto no elimina V4 ni sus variables. Todo queda disponible para volver a
evaluarlo con más observaciones. Lo que evita es entrenar, desplegar y coordinar
HA/M1 con una versión que todavía no ha demostrado ser mejor.

## Conclusión de la primera evaluación

V4 ha producido conocimiento útil —especialmente sobre balance hídrico y
continuidad—, pero por ahora no justifica reemplazar V2 ni adelantar a V3 como
candidata operativa.

V4 permanece viva y reproducible. Sus variables desactivadas continúan
calculándose, entrenándose en los benchmarks, validándose y documentándose para
que puedan reactivarse cuando exista evidencia suficiente.

## 9. Auditoría posterior de los históricos oficiales

La reducción de 399 observaciones registradas a 167 filas comunes en el
contrato `fixed_gap` hizo revisar el origen de los datos, en vez de asumir que
faltaba meteorología oficial. La auditoría confirmó que una parte importante de
la pérdida no procede de las observaciones de setas ni de la disponibilidad real
de Meteocat y AEMET, sino de cómo se habían construido y conservado sus series
históricas.

### 9.1 Meteocat: se conservaron principalmente los días lluviosos

La fuente oficial ofrece por separado la lluvia y las variables de condiciones.
El proceso diario tomaba la tabla de lluvia como tabla principal y le añadía
temperatura y humedad mediante un `left join`. Si una estación tenía temperatura
y humedad pero no una fila de lluvia para ese día, se perdía el día completo.

La comprobación directa contra la fuente oficial muestra, por ejemplo, que las
estaciones CR y WM tienen 31 días de agosto de 2020 con temperatura y humedad.
En el histórico guardado solo aparecen 9 y 7 días respectivamente, todos con
lluvia positiva. No era una ausencia de medición meteorológica.

El patrón temporal encontrado es:

- entre 2017 y 2021 no hay filas almacenadas con lluvia igual a cero;
- en 2022 los ceros empiezan el 23 de octubre;
- desde 2023 la cobertura es mucho más continua, aunque persisten huecos
  puntuales: dos días en 2024, 42 en 2025 y nueve hasta el 10 de agosto de 2026
  para las estaciones de muestra CR y WM;
- varios días recientes ausentes sí existen en la fuente oficial, por lo que
  son huecos de adquisición o ejecución y no huecos del proveedor.

El backfill histórico anterior sí sabía unir lluvia y condiciones y conservar
lluvia cero, pero su rango de Meteocat terminaba el 19 de diciembre de 2016. Se
dio por completa la serie incremental posterior cuando en realidad no lo estaba.

### 9.2 AEMET: se descartaban días válidos sin precipitación informada

El normalizador del backfill de AEMET descartaba una estación y fecha completas
si el campo de precipitación venía vacío, aunque esa misma fila tuviera
temperatura y humedad válidas. Además, escribía siempre las humedades mínima y
máxima como `NA`, aunque los JSON oficiales ya contienen `hrMin` y `hrMax`.

Un caso comprobado es Berga (0092X), 24 de septiembre de 2013: AEMET conserva
temperatura máxima 24,3 °C, mínima 12,5 °C, humedad máxima 90 % y mínima 54 %,
pero no informa precipitación. El normalizador antiguo eliminaba todo el día.

Que la precipitación no esté informada no autoriza a inventar `0 mm`. La
corrección conserva el resto de variables y deja únicamente la lluvia como
desconocida. Esto distingue correctamente entre «cero observado» y «sin dato».

### 9.3 Correcciones implementadas

Ya están implementadas y probadas localmente estas correcciones:

- Meteocat combina lluvia y condiciones mediante la unión de estaciones y
  fechas presentes en cualquiera de las dos respuestas, en lugar de depender
  de que exista una fila de lluvia;
- una lluvia cero observada se conserva como cero;
- si solo hay condiciones, se conservan temperatura y humedad y la lluvia queda
  vacía, sin convertirla en día seco;
- AEMET conserva los días que tengan al menos una variable meteorológica útil;
- AEMET materializa `tmax`, `tmin`, `hrMax` y `hrMin` desde la climatología
  oficial;
- una precipitación ausente permanece ausente;
- las pruebas automáticas cubren tanto el día de solo condiciones como la
  preservación explícita de lluvia cero.

Una lluvia vacía significa «precipitación desconocida en esa estación y día».
No entra en el IDW como cero. Si hay otras estaciones elegibles, el IDW de la
microárea se calcula con ellas. Solo cuando ninguna aporta lluvia queda ausente
el IDW diario; si eso impide completar la ventana requerida, la fila no es
elegible para ese bloque predictivo y conserva un motivo de calidad legible.
La observación de setas no se borra: permanece en el benchmark y puede recuperar
elegibilidad al completar el histórico o participar en otros bloques. La única
conversión de `N/A` a cero es la causa específica ya versionada de duplicado
positivo suprimido; no se generaliza a precipitaciones desconocidas.

La suite dirigida pasa: 48 pruebas, cero fallos. Además de los
normalizadores, cubre la cola persistente de autorreparación: bloques máximos
de 15 días, deduplicación, recuperación parcial, espera entre reintentos,
persistencia, cursor de detección más allá del solape de siete días y apagado
del estado activo al completar el rango. También cubre el cierre transaccional:
histórico primero, CSV vivo después y reconocimiento final del lote. Si el
proceso cae entre esas fases, el siguiente runner termina el CSV antes de borrar
el pendiente.

El histórico y el CSV vivo tienen alcances distintos. Todo bloque recuperado se
incorpora al histórico particionado. El CSV vivo retiene solo 180 días: si el
bloque es anterior no cambia, y si está dentro de la ventana también recibe las
filas reparadas. Esto no limita la reparación histórica.

### 9.4 Reconstrucción local completada

Se descargó mediante el recurso SMB una copia inmutable de los datos actuales de
HA en:

`docker-data/audits/official-weather-gap-repair-20260815/ha-snapshot-20260815T2326/Data`

La copia contiene los 78 ficheros del origen y se verificaron por SHA-256 los
incrementales de Meteocat y AEMET y el manifiesto `weather-history/CURRENT.json`.
HA no se está modificando.

Sobre esa copia se preparó una generación candidata local que:

1. reconstruye AEMET desde el caché oficial ya descargado usando el normalizador
   corregido;
2. recupera de Meteocat los periodos sistemáticos y los huecos puntuales en
   bloques reanudables de 15 días, el tamaño ya validado con 220/220 consultas
   correctas en el backfill anterior;
3. fusiona sin sobrescribir valores válidos con valores vacíos;
4. valida fechas, duplicados, ceros reales, cobertura y continuidad;
5. conserva aparte el snapshot original para poder comparar y revertir.

#### Resultado AEMET

La reconstrucción AEMET ya terminó y superó el control de no pérdida. La
generación candidata pasó de 4.139.573 a 4.244.164 filas: recuperó 104.591
claves estación+día con alguna variable oficial útil y no perdió ninguna clave
anterior. Los 2.985.939 ceros de lluvia y las 1.153.634 lluvias positivas son
idénticos antes y después; por tanto, ninguna ausencia se reinterpretó como
lluvia cero ni se alteró una precipitación existente.

La corrección principal es la humedad que el normalizador antiguo descartaba:
las filas con humedad máxima disponible pasan de 44.259 a 4.018.362 y las de
humedad mínima, de 44.259 a 4.018.720. Las filas con temperatura máxima pasan
de 4.070.325 a 4.171.775. Los huecos internos estación+día entre la primera y
última fecha de cada estación bajan de 202.069 a 121.419; esta métrica no son
días completos de red y no debe confundirse con el detector conservador de
autocuración.

El candidato AEMET se archivó en la generación
`20260815T222006065288Z-3f116178a0a5`, con manifiesto SHA-256
`8dce68733e7c201c5213c02c993441b2fe106b18505780f1a09c32bee30de725`.
El CSV vivo retuvo 147.139 filas desde el corte 2026-02-17; las 4.097.025 filas
del lote anteriores a ese corte se repararon en el histórico particionado, no
se intentaron mantener en la cola viva de 180 días. Todos estos datos son
locales; HA no se modificó.

#### Resultado Meteocat y generación conjunta

La descarga reanudable completó 470/470 consultas —lluvia y condiciones para
235 bloques temporales—, con 468 recuperadas en esta ejecución y dos reutilizadas
de caché verificada. La normalización produjo 658.893 días-estación entre
2016-12-20 y 2026-08-14.

La generación final pasa de 615.087 a 946.815 filas Meteocat: añade 331.728
claves estación+día y no pierde ninguna anterior. Los ceros de lluvia observados
pasan de 387.350 a 655.283 y las lluvias positivas de 225.256 a 282.677. Las
filas con Tmin, Tmax, RHmin y RHmax disponibles pasan de unas 605.700 a unas
930.500. Los huecos internos estación+día bajan de 323.013 a 1.665.

AEMET queda sin ningún día completo de red ausente en 2012-06-19..2026-08-14.
Meteocat conserva tres días completos que tampoco existen al reconsultar la API
oficial en bloques estrechos: 2020-02-01, 2020-02-02 y 2020-11-25; tanto lluvia
como condiciones devuelven cero filas. No se falsifican como días secos. El IDW
multifuente podrá usar AEMET para esas fechas cuando haya estaciones elegibles.

La generación conjunta final es
`20260815T225412516277Z-b7d0a13766a8`, con manifiesto SHA-256
`0e64ac77e322ae1eee3e4a849342de6b9feb32c86262d8c8409fb0195bee944e`.
El control final AEMET+Meteocat registra cero claves antiguas perdidas. El CSV
vivo Meteocat retuvo 33.843 filas desde 2026-02-17; 625.237 filas anteriores se
repararon únicamente en el histórico. Todo permanece local y separado de HA.

Si durante el trabajo se ejecuta el runner programado de HA, no interfiere con
esta reconstrucción. Antes de una futura actualización de HA se tomará un
snapshot nuevo y se incorporarán los días generados desde este corte.

El runner normal ya relee un margen de siete días: Meteocat usa
`days_init: -7` y AEMET conserva y reconstruye siete días cerrados de su serie
horaria. Por tanto, una interrupción corta ya dispone de autocorrección. La
mejora preventiva implementada localmente no duplica el descargador diario:
detecta cualquier hueco oficial que sobreviva más allá de ese margen, lo añade
a una cola persistente y ejecuta como máximo un bloque por fuente en el runner
siguiente.

Como el runner es batch, ese control no debe abrir diálogos ni esperar
intervención. El contrato implementado localmente es: terminar el resto del
proceso, marcar la fuente como degradada —no fallida—, registrar
fuente/fechas/antigüedad en un informe persistente legible por el siguiente
runner y cerrar automáticamente el aviso cuando la continuidad se recupere. No implica
correo, push ni comunicación externa. La presentación específica del informe en
Diagnostics y Errors queda pendiente de UI. El detector limita el estado a días
oficiales completos que sigan ausentes después del solape de siete días; las
bajas/altas de estaciones no producen falsos avisos.

La revisión también detectó que una instalación virgen no inicializa hoy por sí
sola el histórico particionado. No existe una fecha inicial universal: el rango
se deduce de la observación de setas más antigua que se quiera soportar y del
lookback máximo del contrato. Resolver su bootstrap —mediante semilla, trabajo
separado o una combinación— queda expresamente como tarea futura no prioritaria
y fuera de esta reparación. AEMET necesitará una API key para descargar datos
nuevos; Meteocat puede recuperarse sin token.

### 9.5 Consecuencia para el benchmark V4

El benchmark anterior debe considerarse diagnóstico y provisional. Se repetirá
solo después de reparar los históricos y aplicar el mismo contrato espacial a
todas las variables meteorológicas:

- lluvia mediante IDW del área ya acordado;
- temperatura mínima y máxima como dos IDW independientes por microárea: cada
  estación elegible se corrige primero a la altitud de esa microárea, después
  se interpola por distancia y finalmente se agregan las microáreas al área;
- humedad relativa mínima y máxima mediante IDW y agregado por área;
- sin medias de temperatura ni de humedad como variables predictivas.

El backfill AEMET/Meteocat conserva observaciones originales por estación; no
calcula ni persiste el IDW dentro del histórico oficial. La interpolación se
realiza al construir las variables meteorológicas de cada microárea y corte,
para evitar confundir reparación de datos fuente con generación de predictores.

El IDW predictivo usa todas las fuentes disponibles —Meteocat, AEMET,
Meteoclimatic y Wunderground— después de sus controles de calidad. Una sola
estación válida dentro del radio basta para que el valor diario exista; el
número de contribuyentes y su distancia se conservan como calidad, no como
variables predictivas ni como un mínimo oculto de elegibilidad.

MapLibre también consume todas las fuentes habilitadas, pero su interpolador
vive en JavaScript y comparte función entre la capa visual y el punto pulsado,
no con el predictor Python. Además aplica reglas de pintura —por ejemplo, no
pintar un campo azul sostenido solo por lluvia cero— que no forman parte del
contrato biológico. Ambos deben compartir fórmula, parámetros versionados y
fixtures de paridad, no la semántica visual de disponibilidad.

#### Primer impacto sobre las observaciones

Al reconstruir los dos contratos V3 sobre el candidato reparado, `fixed_gap`
pasa de 204 a 350 muestras elegibles de 399 y `lag_event` de 816 a 1.400 de
1.596. De las 399 observaciones originales, 37 carecen de área y microárea y no
permiten calcular contexto espacial. Las 362 que sí tienen área disponen de los
90 días completos de lluvia IDW: ninguna pierde elegibilidad por lluvia ausente.

Las 49 observaciones no entrenables tienen target desconocido; 37 son además
las que no tienen ubicación. Por tanto, en el conjunto actual inferir como cero
una lluvia vacía de estación no recuperaría ninguna observación. Podría cambiar
ligeramente el valor IDW al añadir peso cero y deberá compararse como variante
auditable, pero no resuelve ahora una pérdida de filas. El histórico original
seguirá conservando el vacío.

No se eliminarán observaciones por estar próximas en el tiempo ni se segmentará
el entrenamiento por área. Las floradas se evaluarán como fenómenos locales al
área, con duraciones de referencia de 7 y 14 días, pero cada salida registrada
seguirá siendo evidencia y no se reducirá a una sola fila por episodio.

Hasta repetir esta evaluación, las afirmaciones de las secciones 1 a 8 sobre
Brier, continuidad y elegibilidad no son base suficiente para promocionar V4 ni
para descartar sus variables.

### 9.6 Base meteorológica común para comparar V2, V3 y V4

Decisión de 2026-08-16: la comparación principal no mezclará la V2 de estación
única con V3/V4 IDW. Los tres contratos se reconstruirán sobre la misma capa
meteorológica diaria y las mismas filas:

- AEMET, Meteocat, Meteoclimatic y Wunderground participan sin filtro de fuente;
- lluvia, Tmin, Tmax, RHmin y RHmax se calculan por IDW en cada microárea;
- cada temperatura de estación se corrige a la altitud DEM de la microárea
  antes de aplicar el peso espacial;
- las cuatro series de extremos se agregan después al área, igual que la lluvia;
- basta un contribuyente válido para producir el valor; número de estaciones,
  distancias, ausencias y altitudes descartadas son solo calidad y nunca `X`;
- V2, V3 y V4 reciben idénticas observaciones, etiquetas, fechas de corte,
  particiones y series meteorológicas; solo cambia cómo cada contrato construye
  sus variables.

La reproducción de la V2 desplegada, que seleccionaba una estación, se conserva
aparte como referencia histórica de producción. No se llamará V2 comparable a
esa reproducción: el benchmark controlado identificará expresamente la variante
V2 reconstruida sobre meteorología IDW común. Los benchmarks V2/V3/V4 calculados
antes de esta decisión quedan provisionales y deberán regenerarse.

El código local ya incorpora el núcleo IDW multicanal y pruebas unitarias para
temperatura corregida antes de ponderar, humedad sin corrección altitudinal y
participación conjunta de las cuatro fuentes. La integración del agregado por
área y de los consumidores V3/V4 está en curso; todavía no hay resultados Brier
nuevos ni candidato operativo.

El balance hídrico consumirá lluvia IDW y Tmin/Tmax IDW para calcular ET0 por
Hargreaves. El estado hídrico/SMI consumirá esa misma lluvia y ET0 junto con el
suelo de cada microárea. RHmin/RHmax IDW se mantienen como predictores directos;
Hargreaves no usa humedad y no se alterará su fórmula sin un contrato distinto.

Tras el backfill, las 49 filas no entrenables de `fixed_gap` no fallan por
meteorología: todas tienen target desconocido y 37 carecen además de área y
microárea. Las otras 12 requieren únicamente revisar el resultado registrado.

#### Primer resultado reconstruido con IDW común

La integración local mantiene 350/399 filas en V3 `fixed_gap` y 1.400/1.596 en
V3 `lag_event`. Para las 362 observaciones con ubicación, las cuatro series
Tmin/Tmax/RHmin/RHmax cumplen el contrato; no se pierde ninguna fila adicional
respecto a la lluvia.

V4 `fixed_gap` conserva las mismas 350 filas en core, meteorología ampliada y
balance climático. El bloque de suelo cambia sustancialmente frente al
diagnóstico provisional anterior:

| Variante de suelo | Filas utilizables |
|---|---:|
| `wv0033_0_30cm` | 350 |
| `wv0010_0_30cm` | 350 |
| `wv0033_0_60cm` | 350 |
| `wv0010_0_60cm` | 344 |
| `wv0033_0_100cm` | 338 |
| `wv0010_0_100cm` | 330 |

La caída previa a 122–166 filas no era una propiedad inevitable del SMI: estaba
dominada por el histórico incompleto y por calcular ET0 desde una estación
principal con reemplazos. El nuevo camino calcula por microárea lluvia IDW,
Tmin/Tmax IDW corregidas a su altitud y ET0, simula allí el depósito y solo
después agrega el estado al área. Estos recuentos miden disponibilidad, no
mejora predictiva; aún faltan la reconstrucción V4 `lag_event` y los Brier
emparejados V2/V3/V4.

V4 `lag_event` queda también reconstruida: core, meteorología ampliada y balance
conservan 1.400/1.596 muestras. Las seis variantes de suelo conservan,
respectivamente, 1.400, 1.400, 1.394, 1.358, 1.340 y 1.320. Por tanto, queda
pendiente la calidad predictiva comparada, no la reconstrucción de variables.

### 9.7 Resultado comparable V2/V3/V4 con IDW común

Se cerraron las cuatro comparaciones previstas: `fixed_gap` y `lag_event`, cada
una con agrupaciones temporales de 7 y 14 días. En cada comparación las tres
versiones reciben exactamente las mismas filas, etiquetas, cortes, particiones
y meteorología IDW. Se evaluaron por separado los seis algoritmos ML; el modelo
base de prevalencia de entrenamiento no se cuenta como uno de esos seis.

No se utiliza un Brier medio entre especies ni entre algoritmos. Los recuentos
siguientes solo indican en cuántas comparaciones emparejadas especie+partición
un contrato obtiene un Brier menor, igual o mayor. Sirven para detectar
regularidad, pero no convierten especies distintas en una falsa observación
promedio.

`biology_v4/core` reproduce exactamente `biology_v3`: cero diferencias de
Brier para todos los algoritmos, especies y las cuatro comparaciones en las que
existe métrica. Esto valida el comparador y confirma que cualquier diferencia
de las otras variantes procede de las variables V4, no de cambiar filas o
meteorología.

En el perfil core, V3 frente a V2 obtiene los siguientes recuentos acumulados
en las cuatro comparaciones:

| Algoritmo | V3 mejor | Igual | V3 peor | Casos |
|---|---:|---:|---:|---:|
| Regresión logística | 21 | 0 | 15 | 36 |
| Random forest | 24 | 2 | 10 | 36 |
| Extra trees | 26 | 0 | 10 | 36 |
| HistGradientBoosting | 23 | 4 | 9 | 36 |
| KNN por distancia | 18 | 0 | 16 | 34 |
| SVM RBF calibrada | 20 | 0 | 14 | 34 |

V3 mejora con más frecuencia que V2, especialmente con los tres algoritmos de
árboles, pero no la domina en todas las especies ni particiones. Por tanto,
V2 debe seguir preservada y consultable; este resultado no justifica matarla.

La meteorología ampliada V4 añade memoria hasta 30 días, número de días
lluviosos y extremos adicionales de temperatura y humedad. Frente a V3:

| Algoritmo | V4 mejor | Igual | V4 peor | Casos |
|---|---:|---:|---:|---:|
| Regresión logística | 18 | 0 | 18 | 36 |
| Random forest | 17 | 2 | 17 | 36 |
| Extra trees | 16 | 0 | 20 | 36 |
| HistGradientBoosting | 22 | 4 | 10 | 36 |
| KNN por distancia | 18 | 0 | 16 | 34 |
| SVM RBF calibrada | 19 | 1 | 14 | 34 |

El balance climático añade cuatro ventanas de lluvia menos ET0. Frente a V3:

| Algoritmo | V4 mejor | Igual | V4 peor | Casos |
|---|---:|---:|---:|---:|
| Regresión logística | 16 | 0 | 20 | 36 |
| Random forest | 21 | 0 | 15 | 36 |
| Extra trees | 13 | 0 | 23 | 36 |
| HistGradientBoosting | 21 | 4 | 11 | 36 |
| KNN por distancia | 19 | 0 | 15 | 34 |
| SVM RBF calibrada | 22 | 0 | 12 | 34 |

No hay una mejora general y consistente de V4. HistGradientBoosting es el que
más regularmente aprovecha la meteorología ampliada; SVM y random forest
aprovechan con mayor frecuencia el balance. Extra trees empeora más veces con
ambas ampliaciones. Esto es un patrón por algoritmo, no una selección operativa.

Por especie, las dos ampliaciones son favorables con especial regularidad para
`boletus_edulis`, `hygrophorus_latitabundus` y
`cantharellus_cibarius_sl`. Son desfavorables con mayor frecuencia para
`boletus_pinophilus`; el balance también resulta desfavorable de forma repetida
para `boletus_aereus`. Solo nueve especies tienen en estas particiones clases y
muestras de test suficientes para calcular Brier; las otras especies se
conservan, pero no se inventa una métrica sin soporte.

Conclusión actual: V4 queda cerrada localmente como versión `proposed` y debe
seguir viva para futuras observaciones. No supera el gate para convertirse en
candidata operativa. No se ha entrenado ni promovido ningún artefacto, ni se ha
modificado HA o el worker.

### 9.8 Coste de ejecución observado

La construcción V4 `lag_event` era el tramo lento porque recalculaba ventanas
diarias solapadas de hasta 365 días para cada microárea. Las comparaciones
pueden paralelizarse por perfil, pero tres procesos simultáneos permitieron que
las bibliotecas numéricas saturaran la CPU del M1. En futuras ejecuciones se
limitará la concurrencia a dos procesos y los hilos BLAS/OpenMP de cada proceso.

La optimización estructural ya está implementada localmente. Para cada
microárea:

- filtra una sola vez las estaciones incluidas en el radio contractual de 15 km;
- materializa una serie IDW larga de lluvia, Tmin, Tmax, RHmin y RHmax;
- calcula ET0 una sola vez por día;
- extrae ventanas exactas de esa caché para cada observación/corte;
- conserva la simulación de suelo por microárea y variante.

El cortador vive en el núcleo meteorológico común y devuelve la misma estructura
que la construcción directa. Por tanto, sirve para benchmarks y para materializar
los futuros conjuntos de entrenamiento/artefactos; no es una vía de cálculo
distinta.

Medición real, con un solo proceso:

| Reconstrucción | Filas | Tiempo real |
|---|---:|---:|
| V3 `fixed_gap` | 399 | 61,28 s |
| V3 `lag_event` | 1.596 | 68,53 s |
| V4 `fixed_gap`, incluido suelo | 399 | 73,59 s |
| V4 `lag_event`, incluido suelo | 1.596 | 95,41 s |

La paridad se verificó sobre datos reales mediante SHA-256 canónico:

- las muestras V3 antiguas y optimizadas coinciden exactamente en ambos
  contratos;
- las muestras V4 coinciden exactamente;
- los catálogos completos de estado de suelo de las seis variantes coinciden
  exactamente.

El snapshot local de observaciones usado en esta comprobación conserva el hash
del benchmark anterior. Las observaciones que el usuario acaba de revisar en HA
aún no están incorporadas y entrarán cuando se refresque expresamente el
snapshot local.

Actualización posterior: se copiaron conjuntamente desde HA las observaciones y
known sites actuales. El conjunto pasa a 395 observaciones y 59 microáreas. Dos
observaciones revisadas (`obs_20200625_0003` y `obs_20200625_0005`) pasan a ser
entrenables y `fixed_gap` sube de 350 a 352 filas. Las cuatro observaciones
eliminadas no eran entrenables. El snapshot canónico, sus hashes y copias
anteriores se registran en
`docker-data/audits/mushroom-ml-snapshot-20260816/MANIFEST.json`.

El known sites derivado se instaló después en HA con 59/59 contextos DEM y
59/59 SoilGrids completos. Hash instalado `bb96c4c...`; copia anterior
`e1da0f7e...` preservada en el mismo share. No se modificaron observaciones de
HA, modelos ni worker.

### 9.9 Corrección del coste y de la evaluación por horizonte

Durante la repetición con el snapshot de 395 observaciones se detectó que el
comparador `lag_event` no solo ajustaba el modelo definido por
especie+contrato+estimador. Después repetía el ajuste de V2, V3 y V4 por
separado para cada horizonte 1, 2, 3 y 7. No era un bucle infinito, pero sí un
multiplicador de cinco rondas completas; la SVM calibrada añadía además sus
ajustes internos.

Ese comportamiento era también metodológicamente incorrecto. En `lag_event`,
el horizonte es una variable predictiva dentro de un único contrato temporal;
no define cuatro modelos diferentes. La implementación corregida:

- ajusta una sola vez cada combinación especie+contrato+estimador;
- conserva las probabilidades del hold-out completo;
- calcula Brier, calibración y consenso de cada horizonte filtrando esas mismas
  predicciones, sin volver a ajustar;
- compara cada Brier de horizonte contra la prevalencia correspondiente a ese
  subconjunto;
- identifica expresamente el método como
  `filter_predictions_from_full_temporal_contract_model_no_refit`.

La prueba de regresión cuenta las evaluaciones y exige una por versión aunque
existan cuatro horizontes. La suite completa pasa 801/801. Una
medición real de `lag/core`, groups7, terminó en 104,14 s. Conservó exactamente
la cobertura, partición y todos los resultados del modelo completo del informe
anterior; solo cambia el análisis por horizonte, que antes procedía de modelos
reentrenados. Por ello, el antiguo informe lag queda como evidencia histórica,
pero no debe sustentar decisiones por horizonte. Las comparaciones canónicas
se regenerarán con el método corregido.

Este coste pertenece al laboratorio de benchmark. El Predictor operativo no
entrena estas combinaciones: carga artefactos ya ajustados y calcula
probabilidades, por lo que no requiere una CPU o RAM equivalentes al laboratorio.

El `lag/groups7` completo, con core, meteorología ampliada y balance, baja de
650,68 s a unos 157 s visibles. Se comprobó además que las seis familias de
variables corresponden a seis matrices de columnas diferentes en cada versión;
no queda una duplicación por dos nombres que representen la misma `X`. El coste
restante es el barrido deliberado de algoritmos, especies y familias. Los
bosques RF/ET usan paralelismo interno y, sobre datasets pequeños repetidos,
parte del tiempo se consume coordinando procesos.

Las cuatro comparaciones canónicas ya se regeneraron. Su análisis por especie,
algoritmo, calidad y horizonte está en
`docs/reports/V2_V3_V4_consensus_report002.md`; el informe 001 queda histórico.
