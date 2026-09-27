# Muestreo del histórico entre fuentes — 26/09/2026

## Alcance y método

Lectura y análisis local, sin modificar históricos, ejecutar runner, entrenamiento
o precálculo. Se utiliza la copia reparada `tmp/meteocat-repair-20260926/candidate/`
con generación `20260926T194213372640Z-00b560dfee2a`: incluye la reparación Meteocat
01/08–25/09; los meses anteriores y las otras fuentes no se alteraron en ella.
No confundir sus resultados de agosto/septiembre con los datos previos al arreglo.

Se verificaron hashes de las particiones leídas y se examinaron las columnas de
lluvia de 5.550.603 registros, 2012–2026. Comparación espacial seleccionada:
668 pares de distintas fuentes, entre 799 estaciones del catálogo, con distancia
máxima 5 km y diferencia de altitud máxima 300 m; 136 estaciones Meteocat tienen
parejas en esta selección. Hasta dos vecinas por fuente para cada Meteocat y una
en las comparaciones de control entre otras redes. Se usan coordenadas actuales
del catálogo: no se han auditado posibles cambios históricos de ubicación.

10.103 comparaciones mensuales de pares con al menos 15 días comunes. Se suman
solamente las mismas fechas con valor numérico en ambas estaciones; ausente no
se convierte en cero. Meses parciales, especialmente septiembre de 2026, siguen
siendo parciales. Hay además detección exploratoria en ventanas de tres días,
que puede señalar desfases de fecha y requiere inspección del episodio completo.
Son acumulados almacenados, antes de las reglas de duplicados del IDW.

## Resultado general

No aparece un déficit generalizado de Meteocat durante todo el histórico:
en 3.121 comparaciones mensuales Meteocat–AEMET donde la suma de ambos acumulados
supera o iguala 40 mm, la mediana del cociente Meteocat/AEMET es **1,0231**.
Sólo dos tienen Meteocat por debajo del 25 % del acumulado AEMET. Esto no certifica
cada fecha, ni descarta fallos locales. Las parejas y meses no son independientes;
estaciones casi coincidentes pueden compartir origen instrumental.

Se consultó además el API oficial Socrata `nzvn-apee`, variable 35, tomando lecturas
crudas y sumando los valores no negativos de días UTC completos, conforme al
contrato actual. **88 jornadas de siete estaciones coinciden exactamente con el
histórico local**:

- Febrero de 2026: CG (26 jornadas disponibles), YA (28), X5/PN dels Ports (28).
- DF y YP: 05 y 06/07/2025.
- UO: 25/07/2026.
- YB: 17/10/2024.

Las consultas mensuales agregadas agotaron el timeout. Las consultas crudas
acotadas sí permitieron estas verificaciones; no se consideran verificadas las
consultas fallidas. No se contrastó de nuevo todo el histórico oficial.

## Casos que requieren distinguir causas

| Caso | Meteocat guardado | Vecinas guardadas | Contraste oficial |
| --- | ---: | ---: | --- |
| La Bisbal, 06/07/2025 | DF: 0 mm | Meteoclimatic A: 55,1; C: 64,3 mm | DF oficial: 0 mm, **28 lecturas**, únicamente 00:00–13:30 UTC |
| Palafrugell, 06/07/2025 | YP: 0,1 mm | Meteoclimatic C: 50,8 mm | YP oficial: 0,1 mm, 48 lecturas |
| Fornells, 25/07/2026 | UO: 9,1 mm | AEMET 0367: 37,9; WU IQUART61: 23,62 mm | UO oficial: 9,1 mm, 48 lecturas, estado V |
| Molló, 12/02/2026 | CG: 0,6 mm | WU IMOLL7: 49,78 mm | CG oficial: 0,6 mm, 48 lecturas |
| Olot, 17/10/2024 | YB: 49,1 mm | Meteoclimatic A: 0 mm | YB oficial: 49,1 mm, 48 lecturas |

La Bisbal: en las mismas 22 fechas de julio/2025, DF suma 14,3 mm frente a 82,6 y
93,9 mm de ambas vecinas, a 1,983 km y con 8 m de diferencia de altitud. El catálogo
da las mismas coordenadas a las dos vecinas; no se ha probado independencia de
sensores. Coincidencia entre ellas es una señal de contraste, no una verdad oficial.

El dato DF del 06/07 es temporalmente incompleto en el API: sumar sus ceros no
demuestra ausencia de lluvia durante las horas sin lecturas. El JSON de esas
lecturas no informa `codi_estat`; no se interpreta su ausencia como una marca
explícita de invalidez. En YP hay 48 lecturas y discrepancia fuerte: cobertura
temporal completa tampoco demuestra que un sensor funcione bien. Falta diagnóstico
instrumental/contraste adicional para atribuirlo a sensor, publicación u otra causa.

En Fornells la coincidencia mensual aparente WU/AEMET (47,24/46,9 mm frente a
9,1 mm Meteocat) requiere cuidado: WU repite 23,62 mm los días 25 y 26. La regla
actual del IDW suprime el segundo positivo repetido, asignándole cero. No se debe
presentar el total bruto WU como el valor que realmente entra en el IDW.

## ¿Podemos fechar el inicio del fallo corregido?

No puede garantizarse que todo el histórico anterior a mediados de agosto esté
libre de errores. La auditoría oficial anterior a la reparación empezó el 01/08:

- 01–08/08: las 188 estaciones comparadas cada día coincidían en los cinco campos.
- 09/08: primeras diferencias pequeñas; no prueban por sí solas el mismo defecto.
- 13/08: primeras pérdidas de al menos 5 mm detectadas en esa auditoría, p. ej.
  UI 0 → 8,8 mm, ZE 0 → 13,2 mm y MV 2,5 → 9,8 mm.
- Desde 14–15/08 la discrepancia se extiende a muchas más estaciones.

La lógica antigua de agrupación diaria y conversión de límites horarios ya existe
en el código de `2bc3ef9` (20/06/2026), pero eso no fecha el daño persistido: un
backfill posterior puede haber repuesto días. En los 88 casos anteriores contrastados
ahora no se observa pérdida respecto a las lecturas oficiales actuales. Sí hay
datos oficiales incompletos/anómalos que no resuelve volver a importar lo mismo.

## Consecuencia para IDW y modelos

`rainmapper_core/mushroom_weather_idw.py`, `usable_daily_rain` y
`estimate_daily_rain_idw`: un cero numérico válido entra en la media; un ausente se
excluye. Peso inverso de distancia al cuadrado, radio 15 km y suelo de distancia
0,1 km. Por tanto, un valor indebidamente bajo reduce el IDW respecto al valor
correcto cuando esa estación participa; su efecto exacto depende del punto y
del resto de estaciones. No se ha reconstruido un IDW operativo ni predicción.

El esquema diario conserva lluvia pero no número de lecturas esperadas/recibidas
ni estado de validación de cada lectura. La suma de un día incompleto puede entrar
como si fuera un día seco completo. Es una limitación distinta del recorte horario
ya corregido y merece control de calidad antes del IDW/entrenamiento.

Propuesta inicial, antes del piloto local descrito al final: contrastes espaciales por episodio con
varias vecinas, preservar cobertura/estado de origen y distinguir seco de incompleto.
No sustituir automáticamente Meteocat por la media de aficionados. Evaluar las
reglas con casos de distintas redes y conservar observaciones originales. No se
ha demostrado aún cuánto de las asociaciones anómalas del rovelló procede de estos
datos: requiere ligar los episodios al conjunto concreto de entrenamiento.

## Evidencia reproducible

`tmp/weather-cross-source-20260926/`: `sample.py`, `coverage.json`, `pairs.csv`,
`monthly.csv`, `dry-vs-wet-3day.csv`, `emporda-july2025.csv`,
`official-spot-checks.csv`, consultas `.soql` y respuestas `*-official.json`.
La comparación oficial contiene hash de cada respuesta. Origen:
[API oficial XEMA](https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json).
Auditoría de agosto: `tmp/meteocat-repair-20260926/audit-raw.json`.

## Propuesta inicial: IDW con control de calidad espacial

El usuario plantea ponderar o descartar valores atípicos mediante estaciones
cercanas. En esta fase inicial sólo se había autorizado investigar; después
autorizó el piloto local resumido al final. Los ejemplos
de la tabla no eran el total: el detector exploratorio generó 444 avisos en
ventanas de tres días, repartidos entre 162 pares y 211 fechas finales. Hay
solapamientos, desfases horarios y diferencias reales; no son 444 errores
confirmados ni una estimación de la tasa de fallos.

Propuesta preliminar: mantener IDW y añadir una calidad por estación/fecha,
separada del dato original. Primero evaluar cobertura y estado del origen;
después contrastar con vecinas, excluyendo del contraste la propia estación.
Evitar votos duplicados de un mismo sensor publicado en distintas redes o
coordenadas coincidentes. Considerar distancia, relieve, desfases de día y
persistencia temporal; no descartar automáticamente una lluvia intensa aislada.
Una desviación sospechosa podría reducir el peso, reservando la exclusión para
evidencia fuerte. Si faltan vecinas comparables, no fingir consenso.

La calidad podría multiplicar el peso actual inverso de distancia al cuadrado;
la función de calidad y sus umbrales estaban por definir y validar. Evaluarla
una vez por estación/día y reutilizarla evitaría repetir comparaciones en cada
punto del mapa. El almacenamiento y contrato deberían seguir siendo compactos.
Si se adoptase, entrenamiento e inferencia necesitarían la misma política
versionada, sin utilizar información posterior al corte temporal correspondiente.

El siguiente paso propuesto fue un ensayo local diagnóstico con el IDW actual y la
alternativa sobre episodios secos, lluvia generalizada y tormentas localizadas;
validación con estaciones de referencia apartadas de la estimación y cobertura
comprobada. Medir error, exclusiones incorrectas y pérdida de cobertura antes de
decidir si compensa. No modificar producción ni históricos originales por ahora.

Fundamento consultado: [El Hachem et al., 2024](https://hess.copernicus.org/articles/28/4715/2024/)
compara tres controles de calidad de lluvia de estaciones personales y señala
que la elección depende de disponibilidad y contexto. [RainGaugeQC, adaptación
2025](https://amt.copernicus.org/articles/18/3229/2025/) estudia calidad gradual y
consistencia espacial en redes profesionales y no profesionales. La alta
variabilidad espacial de precipitación y redes escasas limitan un descarte por
simple mayoría. Estas publicaciones apoyan investigar el enfoque, no validan
todavía una política concreta para Rainmapper.

## Seguimiento: piloto local realizado y decisión

Tras la autorización del usuario se sincronizó la meteorología en `docker-data`
y se ejecutó el ensayo local: 24 referencias oficiales, 23.631 jornadas y
3.331 semanas. Las 48 comprobaciones contra el IDW canónico coincidieron.
El MAE diario pasó de 1,091417 mm a 1,091530 al reducir pesos y a 1,091566
al descartar ceros sospechosos; tampoco mejoró el error semanal. La cobertura
del contraste fue limitada y no hubo casos que activaran el filtro de altos
persistentes. No son resultados de una evaluación ciega ni certifican cada dato.

**Recomendación: mantener el IDW operativo actual.** No se modificaron
históricos originales ni producción. Reglas exactas, generación, métricas,
sesgos de selección y posibles ampliaciones en el
[README del piloto](../../local-apps/rainfall-qc/README.md). La preservación de
cobertura subdiaria sigue siendo una propuesta independiente, no implementada.
