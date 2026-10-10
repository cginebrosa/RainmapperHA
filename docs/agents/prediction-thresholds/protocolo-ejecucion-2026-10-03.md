# Protocolo cerrado antes de calcular resultados

Este documento concreta [goal.md](goal.md). Se ha fijado después de inventariar
etiquetas, fechas y episodios, **antes de ajustar modelos o consultar su rendimiento**.
La preparación de variables puede ejecutarse mientras se verifica el arnés; no
selecciona modelos ni umbrales. Los originales y artefactos operativos se conservan.

## Cohorte y cortes

`scripts/prediction_research/freeze.py` produjo el manifiesto privado
`tmp/prediction-research/cohort-v2.json`: 499 observaciones con objetivo canónico,
validación `valid` y uso `include`, dentro de las diez especies del diseño instalado.
Son 86 aereus y 98 caesarea; todas tienen coordenadas de observación. Otras 26 filas
pertenecen a especies ajenas a ese ámbito y 19 no cumplen el objetivo/uso canónico.
No hay exclusiones por ser GBIF. La elegibilidad meteorológica aún debe medirse.

El universo compartido de diez especies se congela como parte del diseño actual,
no como una decisión que hubiera podido tomarse históricamente sin conocer datos
posteriores. El informe será una evaluación retrospectiva de ese diseño.

Tres cortes externos, sin cambiar fechas después de ver resultados:

| Externo | Ajuste inicial | Evidencia para ranking | Selección del umbral B | Prueba externa |
|---|---|---|---|---|
| 2024 | Hasta 2021 | 2022 | 2023 | 2024 |
| 2025 | Hasta 2022 | 2023 | 2024 | 2025 |
| 2026 | Hasta 2023 | 2024 | 2025 | 2026, hasta la descarga |

Las fronteras son 1 de enero. Agrupar visitas de una misma área, **entre especies**,
uniendo fechas consecutivas separadas por un máximo de 14 días. Excluir de ese
corte el grupo completo si cruza una frontera o contiene una visita a 14 días o
menos de ella. No son episodios biológicos acreditados: es una agrupación técnica
conservadora. Mantener todos los horizontes del mismo registro juntos. La partición
temporal se aplica también a las otras especies de modelos compartidos. La revisión
v2 incluye también el final del año externo, para no partir un episodio entre
externo y futuro. Se corrigió antes de ajustar modelos; no cambia las filas ni
los recuentos objetivo publicados abajo. El primer manifiesto se conserva.

Recuento previo a comprobar la meteorología (filas favorables/desfavorables):

| Especie / externo | Ajuste | Ranking | Umbral | Externo | Grupos externos |
|---|---:|---:|---:|---:|---:|
| aereus / 2024 | 10/7 | 2/4 | 5/3 | 12/5 | 9 |
| aereus / 2025 | 12/11 | 5/3 | 12/5 | 15/8 | 7 |
| aereus / 2026 | 17/14 | 12/5 | 15/8 | 9/6 | 4 |
| caesarea / 2024 | 21/4 | 4/4 | 3/1 | 14/6 | 15 |
| caesarea / 2025 | 25/8 | 3/1 | 14/6 | 13/13 | 11 |
| caesarea / 2026 | 28/9 | 14/6 | 13/13 | 8/7 | 5 |

No se purga ninguna observación objetivo en estos cortes. Los externos suman 116
observaciones distintas: 55 aereus y 61 caesarea. Que un caso externo de un corte
forme parte del desarrollo de otro posterior es normal en una evaluación sucesiva;
no se vuelve a contar como prueba externa. No cambiar reglas después de mirar
el primer corte. Por su escaso soporte, varios ajustes de umbral podrían quedar
sin candidato admisible; eso se informa, no se corrige desplazando las fronteras.

## Qué se reproduce

La auditoría de código local confirmó cinco versiones instaladas: V2, V3, V4,
V5 windowed y V6 windowed, con los perfiles 30/60/90 que declara el registro.
El universo completo se obtiene del registro, sin seleccionar sólo ganadores del
catálogo productivo. Incluir contratos lag y fijo para conservar los fallbacks.
Sólo son necesarios modelos propios de las dos especies objetivo y los modelos
compartidos; éstos reciben todas las especies del ámbito congelado, recortadas
temporalmente. No hacen falta modelos propios de las otras ocho especies.

La política efectiva local está en `mushroom_ml_prediction_policy.json` y su modo
es `shadow`. Conservarlo. El consenso afecta a caesarea pero no a aereus; en shadow
no veta la recomendación. No activar `prudent` como parte de B.

Para cada corte:

1. Preparar variables sin etiquetas externas como predictores. Ajustar modelos y
   tuning usando sólo la ventana inicial; aplicar preprocesadores y soporte del
   entrenamiento calculados sólo con sus filas.
2. Puntuar candidatos en la ventana de ranking. Construir un catálogo nuevo con
   las métricas y exclusiones existentes; conservar el split oficial de grupos
   de 14 días en su contrato, registrando estas fronteras temporales explícitas.
3. Congelar configuración y catálogo. Reajustar los modelos con ajuste + ranking
   para predecir la ventana de umbral, manteniéndola fuera de esos ajustes.
4. Seleccionar un umbral por especie con la regla siguiente. Reajustar los modelos
   con ajuste + ranking + umbral para puntuar el externo. Mantener el catálogo,
   la configuración y el umbral sellados. El externo no participa en ninguna decisión.

Estas cuatro ventanas sustituyen deliberadamente las proporciones 70/30 del
entrenamiento ordinario para separar el nuevo ajuste de umbral. Se evalúa el
selector y consejo actuales bajo esta partición, no el artefacto del 28/09 ni
una réplica exacta de sus tamaños de entrenamiento. El reajuste final reproduce
el uso de todos los datos de desarrollo autorizados; no se interpretará su prueba
interna como independiente del modelo final.

Reutilizar `fit_artifact`, `predict_bundle_many`, la construcción de catálogo y
`resolve_species_week`. La calibración interna SVM actual divide filas: mantenerla
en A y B no contamina el externo excluido, pero impide afirmar que toda su
calibración interna esté agrupada. V6 debe ajustar el preprocesador sobre el ámbito
real de cada artefacto; el script histórico de evaluación no es intercambiable
automáticamente con el runtime. Registrar las elecciones de tuning y sus límites.

Detalle del arnés, fijado antes del primer ajuste: V6 por especie conserva C=0,1;
V6 compartido/partial reutiliza la cuadrícula y selector existentes únicamente
en ajuste inicial, con su limitación de preprocesamiento previo a subdivisiones
internas. Esas subdivisiones mantienen los grupos originales por especie/área:
pueden separar especies de una misma visita. No se afirmará independencia interna
completa; ranking, umbral y externo sí quedan fuera de ese ajuste inicial mediante
los grupos entre especies del estudio. V5 usa la selección interna existente,
también sólo en ajuste inicial.
Los reajustes posteriores heredan esas configuraciones; no vuelven a escogerlas
con ranking, umbral o externos. La evidencia interna usa la probabilidad de la
API de runtime, redondeada a seis decimales; no usa sus vetos de aplicabilidad
para descartar filas de ranking. Éstos se aplican al resolver el punto.

El catálogo experimental contiene sólo la evidencia de la ventana de ranking de
este protocolo, bajo el contrato oficial de 14 días; sus métricas alimentan
también los filtros de calidad. No mezcla el split productivo adicional de siete
días. Es otra diferencia explícita del diseño de evaluación respecto a aquel
lote, compartida por A/B, y limita la equivalencia con el artefacto instalado.
Los errores imprevistos de contrato detienen el arnés; no se contabilizan como
falta de soporte científico de un candidato.

## Semana, punto y momento meteorológico

Para una observación en T y horizonte h, emitir en `T − (h − 1)`, materializar los
siete targets de esa emisión y puntuar sólo T. Los siete horizontes de T son siete
emisiones distintas; **no constituyen una semana de predicción**.

En lag, el corte meteorológico de la semana es emisión − 1. El código actual usa
histórico hasta ese corte: no hace falta introducir meteorología futura ni exigir
previsiones archivadas para reproducir esa entrada. Sin embargo, el histórico
descargado puede contener revisiones o incorporaciones posteriores. El ejercicio
es retrospectivo y no prueba qué habría publicado el sistema entonces.

Entrenar con las variables de área del contrato existente; inferir en coordenadas
del punto con `PointWeatherReader` y contexto físico de celda nativa. No sustituir
el punto por el agregado del setal. Conservar filtros territoriales, fenología,
aplicabilidad y abstenciones para poder hablar del mapa completo. Si falta una
parte, identificar el resultado como parcial y precisar la limitación.

Compartir preparación únicamente entre claves idénticas. Conservar por separado
las combinaciones 90/sin físico, 90/con físico y 365/con físico cuando se soliciten;
no asumir que recortar 365 días reproduce preparar 90. El contrato fijo tiene su
propio corte por target. No multiplicar copias meteorológicas por modelo.

## B: selección cerrada y utilidad mínima

`B favorable = A favorable y probabilidad del ganador >= τ`.
Un favorable de A que no supera el umbral pasa a **sin recomendación por umbral**;
no se convierte en una afirmación desfavorable. Conservar las demás decisiones.
Usar el consejo final, no sólo el IFF del mapa. El control τ=0,60 debe igualar A.
No modificar el umbral de reliability audit: eso alteraría también el ranking.

Cuadrícula: 0,60; 0,65; 0,70; 0,75; 0,80; 0,85; 0,90; 0,95. Elegir un único τ por
especie/corte con la ventana de umbral; no elegir uno por horizonte con tan pocos
datos. Cada observación aporta en total peso 1, repartido entre sus siete emisiones,
incluyendo como abstenciones las emisiones sin consejo válido.

Mínimos técnicos fijados para este experimento, **no preferencias numéricas del
usuario**: al menos cinco observaciones de cada clase y tres grupos que contengan
cada clase en la ventana de umbral. Para admitir τ>0,60, conservar al menos el 80 %
de los verdaderos favorables de A, detectar al menos el 25 % de los favorables
observados, emitir al menos cinco recomendaciones equivalentes y cubrir al menos
tres grupos con alguna recomendación favorable.

Entre candidatos admisibles, minimizar falsos favorables; desempatar por más
verdaderos favorables y después menor umbral. Exigir reducción estricta del falso
favorable frente a 0,60; si no existe o falta soporte, conservar 0,60 con razón
explícita. Mostrar toda la curva de desarrollo. Ningún resultado externo permite
escoger retrospectivamente otro umbral. Esta regla busca un compromiso acotado;
no presupone una proporción monetaria entre errores ni acredita una mejora universal.

## Resultados, incertidumbre y recursos

Por especie, corte y horizonte: observaciones, grupos, clase real frente a consejo
favorable/desfavorable/abstención, falsos favorables, verdaderos favorables, falsos
desfavorables y positivos perdidos por abstención. Incluir cobertura, motivos y
frecuencia del ganador. Contraste A/B pareado, sin elegir el mejor corte a posteriori.

Presentar resultados por horizonte y un promedio con peso total 1 por observación;
no tratar siete emisiones como siete casos independientes. Para incertidumbre,
remuestrear grupos completos, estratificando por corte, con semilla 20261003 y
2.000 repeticiones. Advertir el soporte pequeño y la dependencia espacial residual.
Un intervalo bootstrap degenerado con cero errores no demuestra riesgo cero:
acompañarlo del número de grupos recomendados y un límite binomial exploratorio
por grupo, cuya independencia tampoco está acreditada. No proclamar superioridad
operativa sólo por una diferencia puntual o por abstenerse casi siempre.

Antes de materializar: 499 observaciones × 8 filas (fijo + siete lag) como máximo
para las bases; se comparten por perfiles. La cardinalidad de punto depende de
las emisiones utilizadas y se medirá antes de prepararlas. El supervisor
`scripts/prediction_research/bounded.py` impone un proceso de cálculo, un hilo,
8 GiB RSS/proceso, 2 GiB de salidas, 45 minutos/lote y 120 minutos acumulados.
La preparación también consume ese presupuesto. Registros en `tmp/prediction-research/runs/`.

El límite inicial era 4 GiB. La primera preparación se detuvo por memoria después
de 240,3 segundos, con máximo RSS observado de 4.422.696.960 bytes. El usuario
autorizó expresamente ampliarlo a 8 GiB. La vigilancia es por muestreo, no una
garantía de ausencia de picos breves. Mantener la proyección de variables a las
ventanas instaladas 30/60/90: no se necesitan columnas de modelos full-365 no
instalados. Conservar los 365 días de calentamiento físico y verificar paridad
de los valores retenidos. Se guardan el lote detenido y sus salidas parciales.

El sandbox de macOS bloqueó `ps` en la primera prueba mínima del supervisor; el
usuario aprobó su ejecución fuera del sandbox y la segunda prueba terminó bien.
Esto permite vigilar memoria de procesos propios; no amplía el alcance científico
ni autoriza escrituras operativas. No instalar paquetes ni modificar servicios.

La preparación usa únicamente en memoria `OperationalWeatherWorkspace`; su nombre
no significa que se lance un trabajo del coordinador. La auditoría detectó que su
lector genérico creaba/retiraba un lease operativo durante la primera preparación.
Se corrigió con un adaptador experimental que fija el manifiesto sin escribir
locks/leases y verifica todos los hashes meteorológicos antes y después. La prueba
real de lectura pasó: metadatos de locks/leases iguales y escritura ajena rechazada.
La primera ejecución pudo crear metadatos de acceso; no alteró valores del histórico.

Las ejecuciones posteriores incorporan protección de escrituras Python fuera del
estudio, límites de Arrow y comprobación final de disco/tiempo y descendientes.
No equivalen a un sandbox del sistema para llamadas nativas: los lectores GIS usan
modo lectura y GDAL tiene desactivados sidecars y acceso de red. Los metadatos de
geografía se congelan; los rásteres grandes se identifican mediante los manifiestos
y sellos publicados, sin duplicarlos ni afirmar un nuevo hash completo de todos.

Verificar huellas de entradas antes y después, conservar trazas de fallos y no
ocultar una reproducción incompleta. Los scripts experimentales se sellarán junto
a su configuración antes del primer ajuste, una vez verificado el arnés.

## Auditoría de trazabilidad durante la ejecución

Después del externo 2024 se reforzó el evaluador sin cambiar los candidatos,
particiones, regla B ni inferencias previstas: se sellan también la geografía
preparada y la elección B, contrastándola con el hash previo al reajuste externo.
El universo de versiones procede explícitamente de la cohorte; la ausencia total
de evidencia se representa como `no_model`, y una semana incompleta sigue siendo
un error. En 2024 estaban presentes las cinco versiones y las siete resoluciones.
La fuente original del evaluador se conserva por SHA-256 en el archivo privado.

El evaluador de 2026 añade además el hash final de sus predicciones al resumen de
cierre. En 2024/2025 ese hash se registra al analizar, no al terminar la inferencia;
no atribuirles un sello retroactivo. La geografía de 2024 tampoco estaba incluida
en su sello original de evaluación. Se conservan las salidas y se declaran estas
limitaciones de procedencia; no se repiten cálculos ni se alteran resultados.

Los intervalos remuestrean casos con modelos, ranking y umbrales ya fijados; no
incluyen la variación que produciría repetir todo el entrenamiento y la selección.
Informar cuántas de las 2.000 réplicas tienen denominador válido para cada tasa.
