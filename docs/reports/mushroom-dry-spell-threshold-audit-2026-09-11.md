# Auditoría de racha seca: plan y resultados

**Ampliación posterior:** se ejecutó también la [comparación con el selector
real](mushroom-dry-spell-selector-audit-2026-09-11.md). La retirada no mejoró de
forma estable y produjo pérdidas de cobertura en uno de los exámenes. La
recomendación posterior es conservar el contador; los resultados de esta
primera auditoría se mantienen aquí como antecedente exploratorio.

## Plan registrado antes de ejecutar

Autorizada por el usuario el 11/09/2026. Objetivo: decidir si merece la pena
retirar el contador de días secos, cambiar su umbral o sustituirlo por un reloj
de lluvia acumulada. No se activa ningún modelo, no se modifica el Predictor,
no se lanza precálculo ni se publica HA.

### Entradas y alcance

Reutilizar las entradas meteorológicas persistidas del 05/09: snapshot de
`mushroom-dry-spell-ablation-20260905` para las cinco especies de aquella prueba;
complementar las otras especies desde `mushroom-hydric-ablation-20260905/prepared/snapshot`.
No mezclar filas de una especie entre snapshots. Registrar SHA256, fechas,
filas, observaciones y grupos. Son datos históricos ya examinados: los resultados
serán exploratorios, no confirmación prospectiva sobre observaciones nuevas.
Inventariar todas las especies disponibles; excluir de ajuste las que no tengan
dos clases y grupos suficientes, indicando el motivo.

Seis configuraciones controladas ya utilizadas: V2 logística/RF, V3 core HGB,
V3 con estado físico logística y V4 con balance climático logística/KNN.
V5/V6 son referencia estructural sin contador; no añadirles una variable ni
atribuir una comparación causal a sus porcentajes operativos.

### Nueve variantes, fijadas antes de ver resultados

1. Actual: rompe con `P > 0`.
2. Sin contador ni indicador de censura del contador.
3. Cinco umbrales diarios: rompe con `P >= 1, 2, 3, 4, 5 mm`.
4. Dos relojes: días desde el último fin de ventana de 3 días completos con
   suma `>= 5` o `>= 10 mm`. No llamarlos recarga medida del suelo.

Los valores ausentes son desconocidos: detienen la búsqueda y censuran el
contador; no se imputan como cero al construirlo. Mantener cantidades originales
en el resto de entradas. Comprobar casos artificiales de trazas, 2 mm diarios
durante diez días, lluvia concentrada y huecos; son pruebas del cálculo, no
evidencia de fructificación.

### Selección y evaluación

- Mismos algoritmos e hiperparámetros entre variantes; ningún tuning adicional.
- Dos agrupaciones históricas, 14 días principal y 7 días de estabilidad.
  Mantener cada observación y sus horizontes en el mismo lado.
- Reservar cronológicamente el 30 % final de grupos. Purgar del entrenamiento
  los grupos que se solapen en fechas con la evaluación; registrar el efecto.
- Dentro del entrenamiento, tres validaciones sucesivas: entrenar con los
  primeros 50/65/80 % de grupos y validar con el siguiente 15/15/20 %.
  Purgar solapamientos temporales. Exigir ambas clases y al menos dos grupos
  de validación; al menos dos particiones internas válidas para elegir.
- Elegir umbral diario y ventana por Brier interno. Elegir también una política
  adaptativa entre todas las variantes. Si quitar el contador está dentro de
  un error estándar del mejor resultado interno, preferir quitarlo por simplicidad.
  Es una regla experimental de selección, no prueba formal de equivalencia.
- Congelar elecciones antes de evaluar el bloque externo. Informar todas las
  alternativas fijas como exploración, pero decidir la política adaptativa por
  los resultados internos, nunca por escoger a posteriori el mejor externo.
- Brier medio por observación (sus horizontes comparten peso), ROC-AUC,
  calibración, falsas señales positivas al corte diagnóstico 0,5 y cambios de
  clasificación. No confundir ese corte con el selector/recomendación de la UI.
- Informar magnitudes por especie/configuración y media con igual peso entre
  configuraciones; incertidumbre por remuestreo de grupos completos. No contar
  modelos u horizontes repetidos como experimentos independientes.
- No se simula activación ni selector operativo completo: su cobertura y sus
  abstenciones requerirían validación posterior del contrato elegido. Informar
  cobertura de la auditoría, sin inventar abstenciones del Predictor.

### Recursos, comprobaciones y decisión

Runner reproducible en `scripts/audit-mushroom-dry-spell-thresholds.py`, con
proceso único, un hilo numérico y matrices pequeñas reutilizadas; sin copias
meteorológicas por candidato. Preflight con máximo de ajustes y salida limitada.
Modelos solo en memoria. Resultados bajo `docker-data/audits/`, informe resumido
versionado aquí. Conservar huellas de observaciones y precálculo antes/después.

La decisión final pertenece al usuario. Una mejora media puede ser útil aunque
no mejore cada combinación: cuantificar ganancia, peor perjuicio, especies
perjudicadas y estabilidad. Si la evidencia no distingue un umbral del modelo
sin contador, preferir el candidato sencillo sin afirmar universalidad.

## Resultados

### Ampliación por cobertura, registrada antes de ejecutarla

La selección interna terminó con 36 casos (tres especies × seis configuraciones
× dos agrupaciones). Edulis, Rovelló y Cantharellus carecen de dos particiones
internas válidas con ambas clases. Para no perder su comparación, ejecutar
`--external-only`: las nueve alternativas fijas con la misma partición externa,
sin selección de ganador ni flexibilizar los requisitos del experimento principal.
No repetir casos ya completos. Los resultados de esta ampliación serán
descriptivos; no usar su mejor umbral para anunciar una política validada.
El runner exacto de la ejecución principal se conserva junto al JSON.

### Resultado para decidir

**La opción más prometedora es quitar el contador, no subir su umbral.** En la
comparación descriptiva completa, el error medio baja 1,05 % con agrupación de
14 días y 1,27 % con la de 7 días. No son puntos porcentuales de acierto ni una
mejora medida en la UI. La ventaja es modesta y no beneficia a todas las especies.

La evaluación más estricta, que elige usando exclusivamente el entrenamiento,
solo puede completarse para Ou de reig, Aereus y Pinícola. En ella quitar el
contador reduce el error 0,30 % y 0,66 %, respectivamente. Su incertidumbre
incluye mejora y empeoramiento: todavía no prueba una ventaja definitiva.
Los umbrales escogidos dentro del entrenamiento no muestran una mejora estable.

**Propuesta posterior a la auditoría, pendiente del usuario:** conservar los
modelos operativos mientras se decide si preparar contratos candidatos sin
contador y validarlos con el selector real. No recomendar un umbral diario o
acumulado universal. No interpretar estos resultados como evidencia de que
el agua del suelo no importa: solo se ha examinado una forma de resumirla.

### Ejecución y cobertura

- 1.602 ajustes aislados: 1.296 de selección interna y evaluación, más 306
  de comparación descriptiva. Un proceso y un hilo numérico; modelos únicamente
  en memoria. Tiempo medido de cálculo: 56,63 s, sin contar preparación del
  runner, comprobaciones ni redacción. No es entrenamiento operativo completo:
  reutiliza entradas preparadas, sin reconstrucción meteorológica ni GIS.
- Se inventariaron 17 especies. Seis permiten alguna comparación externa:
  Ou de reig, Aereus, Edulis, Pinícola, Rovelló y Cantharellus.
- 35 combinaciones especie/configuración por agrupación: seis configuraciones
  en las primeras cinco especies y cinco en Cantharellus. Sus 132 observaciones
  externas únicas con grupos de 14 días y 107 con grupos de 7 días no se cuentan
  repetidamente como observaciones independientes al comparar modelos.
- Tres especies permiten elegir candidatos internamente: Ou de reig, Aereus y
  Pinícola, 18 combinaciones por agrupación. Las otras tres solo permiten
  comparación descriptiva. Edulis y Rovelló tienen únicamente una de las tres
  particiones internas con ambas clases; no se flexibilizó la regla para elegir
  su mejor umbral. Cantharellus tiene diez observaciones elegibles en el snapshot;
  la configuración fija HGB tampoco supera el mínimo externo de entrenamiento.
- Marzuolus, Morchella y Latitabundus no superan los requisitos de clases/grupos
  de estas particiones. Las restantes tienen muy pocos grupos o ninguna fila
  elegible. El detalle de cada exclusión está en `inventories`/`cases` de los JSON.
- Fuentes de 05/09 congeladas, con SHA256 y selección de especie disjunta entre
  snapshots; no se añadieron las observaciones actuales posteriores. Esta
  ejecución no equivale a evaluar las nueve especies hoy instaladas con sus
  modelos de septiembre ni constituye una confirmación prospectiva.
- V5/V6 quedan como referencia estructural: no tienen el contador. No se les
  reajustó ni se mezclaron sus porcentajes operativos con estas métricas.
- Las particiones conservan grupos y observaciones completos. Se verificó la
  purga temporal; no fue necesario retirar grupos del entrenamiento en los casos
  evaluados. El desempate
  de grupos con igual fecha es explícito por identificador, por lo que no se
  exige identidad numérica con el orden incidental del runner anterior.

### Alternativas fijas: comparación descriptiva completa

Cambio negativo de Brier significa menor error. La media da el mismo peso a
cada configuración/especie; no representa la frecuencia real de consultas.

| Variante | Brier 14 d | Cambio 14 d | Reducción relativa del error 14 d | Reducción relativa 7 d |
|---|---:|---:|---:|---:|
| Actual | 0,289563 | 0,000000 | 0.00 % | 0.00 % |
| Sin contador | 0,286510 | -0,003053 | 1.05 % | 1.27 % |
| Umbral diario 1 mm | 0,289591 | 0,000029 | -0.01 % | 1.54 % |
| Umbral diario 2 mm | 0,289486 | -0,000077 | 0.03 % | 0.76 % |
| Umbral diario 3 mm | 0,289702 | 0,000139 | -0.05 % | 0.38 % |
| Umbral diario 4 mm | 0,288677 | -0,000885 | 0.31 % | 0.89 % |
| Umbral diario 5 mm | 0,289384 | -0,000178 | 0.06 % | 1.15 % |
| 5 mm acumulados en 3 días | 0,289853 | 0,000290 | -0.10 % | 0.61 % |
| 10 mm acumulados en 3 días | 0,292739 | 0,003177 | -1.10 % | -0.86 % |

Un signo negativo en las columnas de reducción relativa indica empeoramiento.
El umbral fijo de 1 mm es el mejor de esta lista en el corte de 7 días, pero
no mejora en el principal de 14 días. No se debe elegir retrospectivamente el
umbral o la agrupación que más favorezca una conclusión.

### Quitar el contador: diferencias por especie

| Especie | Cambio Brier 14 d | Reducción relativa 14 d | Reducción relativa 7 d |
|---|---:|---:|---:|
| Ou de reig | 0,001729 | -0.60 % | 1.36 % |
| Aereus | 0,001772 | -0.64 % | -0.25 % |
| Edulis | -0,008691 | 2.25 % | 2.16 % |
| Pinícola | -0,006189 | 1.81 % | 0.84 % |
| Cantharellus | -0,000709 | 0.21 % | 0.21 % |
| Rovelló | -0,005840 | 4.89 % | 4.89 % |

Con grupos de 14 días, 21 combinaciones mejoran, 11 empeoran y 3 empatan.
La mejor mejora individual es Edulis/V2 RF: 0,373462 → 0,339108.
El peor retroceso es Cantharellus/V2 RF: 0,339724 → 0,353116; le siguen Ou de
reig/V4 KNN: 0,277008 → 0,290087 y Ou de reig/V2 logística:
0,354688 → 0,365793. No ocultar estos casos por una media favorable.

### Elección dentro del entrenamiento y examen posterior

Esta tabla solo usa las tres especies que superan los requisitos internos.
Los porcentajes no son comparables directamente con la tabla completa, que
incluye seis especies.

| Política elegida sin mirar el examen final | Reducción error 14 d | Reducción error 7 d |
|---|---:|---:|
| Adaptativa entre todas; acaba sin contador | 0.30 % | 0.66 % |
| Elegir entre umbrales diarios de 1–5 mm | -1.06 % | 0.66 % |
| Elegir entre las dos ventanas acumuladas | -1.39 % | -0.65 % |

La política adaptativa elige `off` en los 36 casos por la regla de preferir
simplicidad cuando está dentro de un error estándar del mínimo interno.
**No significa que `off` obtenga el mínimo interno en todos los casos.** La
variabilidad entre las tres particiones hace que varias alternativas resulten
poco distinguibles. La regla y su elección fueron comprobadas desde las
puntuaciones internas, independientemente de los resultados externos.

El remuestreo pareado de grupos (2.000 réplicas) para quitar el contador da,
con 14 días, intervalo de cambio Brier [−0,004588, +0,002942] en el subconjunto
con selección interna. Incluye cero: no establece una superioridad firme.
En el conjunto descriptivo es [−0,005632, −0,000474], compatible con una
mejora media en esa muestra. Son intervalos condicionales a estos ajustes y
estos históricos ya consultados; no incluyen toda la incertidumbre del
entrenamiento ni autorizan declarar una mejora prospectiva.

Al remuestrear se usa la misma selección de grupos para las configuraciones
que comparten especie, evitando tratar sus predicciones correlacionadas como
casos independientes. Las agrupaciones de 7 y 14 días tampoco son réplicas
independientes de nuevos datos.

### Falsas señales, ordenación y cobertura

Sin contador, la tasa de falsos positivos al corte diagnóstico 0,5 cambia
+0,04 puntos porcentuales en la media descriptiva de 14 días y +0,13 en la de
7 días. La mejora del error probabilístico no demuestra menos salidas fallidas.
El AUC medio cambia −0,001724 y −0,002048, respectivamente; la medida de error
de calibración mejora −0,002643 y −0,000957. Se conserva todo por caso en CSV/JSON.

No se ha ejecutado el selector operativo con los artefactos alternativos ni
calculado nuevos soportes de aplicabilidad: no atribuir cambios de cobertura,
abstenciones o recomendaciones de la UI a esta auditoría. Es la siguiente
validación necesaria si se decide preparar una candidata.

### Ejemplos de lluvia repartida y límites de los relojes

Los casos artificiales comprueban el significado del contador:

- Tras 20 días sin lluvia, 2 mm/día durante 10 días: el umbral diario de 3 mm
  conserva 30 días secos censurados; la ventana de 5 mm/3 días detecta un
  episodio vigente (edad 0). Ambos mantienen los 20 mm en las cantidades.
- Una única lluvia de 20 mm seguida de 9 días sin lluvia: el contador diario
  marca 9; el reloj de 3 días marca 7 porque cuenta desde el final de la última
  ventana que todavía incluía aquella lluvia. No son el mismo concepto.
- Datos ausentes detienen y censuran la búsqueda; nunca cuentan como 0 mm.

Ejemplo real de los inputs congelados: Pinícola/Sant Joan, observación
`obs_20230621_0005`, corte 20/06/2023: los tres últimos días acumulan
2,828254 + 2,879498 + 0,240195 = 5,947947 mm. Ninguno supera 3 mm, pero juntos
sí superan 5 mm. Demuestra la diferencia de representación; no prueba que
esos milímetros llegaran íntegramente al suelo ni una mejora de fructificación.

### Validaciones, artefactos y reproducción

- Pruebas de límites, trazas, lluvia repetida/concentrada, huecos y purga temporal.
- Recalculo independiente de todas las puntuaciones desde las probabilidades
  persistidas; elecciones internas y separación de observaciones verificadas.
- Cero advertencias de ajuste registradas. Ningún modelo escrito ni activado.
- Observaciones protegidas del repositorio, observaciones vivas locales, SQLite
  activo y recibo de activación: SHA256 idénticos antes y después de ambas ejecuciones.
- Resultado principal: `docker-data/audits/mushroom-dry-spell-thresholds-20260911/results.json`.
- Complemento: `descriptive.json`; resumen verificado: `final-summary.json`;
  detalle legible: `final-case-results.csv`, todos en el mismo directorio.
- `runner-main.py` conserva el código exacto de la primera ejecución; el runner
  versionado incorpora también el modo complementario. Los JSON conservan sus
  huellas de código y entradas. Salidas con nombres nuevos para no sobrescribir.

Comandos de reproducción (usar un directorio nuevo):

```bash
.venv/bin/python scripts/audit-mushroom-dry-spell-thresholds.py --selftest
.venv/bin/python scripts/audit-mushroom-dry-spell-thresholds.py --output docker-data/audits/<nueva-ejecucion>/results.json
.venv/bin/python scripts/audit-mushroom-dry-spell-thresholds.py --external-only --output docker-data/audits/<nueva-ejecucion>/descriptive.json
.venv/bin/python scripts/summarize-mushroom-dry-spell-thresholds.py docker-data/audits/<nueva-ejecucion>
```

Huellas de los resultados de esta ejecución:

- `results.json`: `6eb013ff83fd548932f9049f48443f419094b65e5cdc0391c49a2cff788f2111`.
- `descriptive.json`: `0dcfe8c057437f5c0484920ab205bf3118d12c258ea60b978461fb5357442e6c`.
