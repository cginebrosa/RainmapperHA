# Informe 002 de consenso entre algoritmos — V2, V3 y V4

Fecha del análisis: 2026-08-16.

## 1. Alcance y corrección metodológica

Este informe reemplaza al informe 001 para cualquier decisión. Usa el snapshot
canónico actual de 395 observaciones, 352 filas `fixed_gap` utilizables y 1.408
tareas `lag_event` utilizables. Incluye las dos observaciones revisadas
`obs_20200625_0003` y `obs_20200625_0005`.

Compara, sobre meteorología IDW común y filas idénticas:

- V2 conservando su contrato de variables, pero sin la estación única histórica;
- V3;
- V4 con meteorología ampliada;
- V4 con meteorología ampliada y balance climático.

V4 core no se presenta como otra versión distinta porque reproduce V3. Se
mantienen los seis algoritmos: LR, RF, ET, HGB, KNN y SVM RBF calibrada. No se
calcula un Brier medio entre especies ni se escribe ningún modelo.

Se corrigió además `lag_event`: cada especie+contrato+algoritmo se ajusta una
sola vez. Los diagnósticos de horizonte 1/2/3/7 filtran las probabilidades del
mismo hold-out; no entrenan cuatro modelos adicionales. Esto corrige tanto el
coste como la pregunta científica.

## 2. Filas, observaciones y soporte

Una fila `fixed_gap` representa una observación. Una fila `lag_event` representa
una tarea de predicción observación+horizonte; por eso una observación genera
cuatro filas. Las 1.408 tareas lag no son 1.408 observaciones independientes.

Nueve especies permiten alguna evaluación. El rango cambia ligeramente entre
grupos de florada de 7 y 14 días:

| Especie | Observaciones train | Observaciones test |
|---|---:|---:|
| `amanita_caesarea` | 41–42 | 24–25 |
| `boletus_aereus` | 41–43 | 26–28 |
| `boletus_edulis` | 21 | 11 |
| `boletus_pinophilus` | 34 | 25 |
| `cantharellus_cibarius_sl` | 6 | 4 |
| `hygrophorus_latitabundus` | 7 | 4 |
| `hygrophorus_marzuolus` | 19 | 6 |
| `lactarius_deliciosus` | 30 | 16 |
| `morchella_elata_complex` | 11–12 | 5–6 |

`boletus_edulis` requiere una salvedad: con grupos de 7 días su partición de
entrenamiento queda con una sola clase (20 observaciones train y 12 test), por
lo que no se ajusta ningún algoritmo. Con grupos de 14 días sí es evaluable.
No se mueve el corte ni se eliminan filas para fabricar una métrica.

En total hay 34 contextos evaluables especie+contrato+partición, no 36. LR, RF,
ET y HGB están disponibles en los 34; KNN en 32 y SVM calibrada en 33 por sus
requisitos mínimos propios.

## 3. Qué se llama consenso útil

El acuerdo bruto mide qué pareja entrega probabilidades más próximas fila a
fila. Eso no basta: dos modelos malos pueden equivocarse juntos. El análisis
aplica este orden:

1. conservar solo algoritmos cuyo Brier supera la prevalencia de entrenamiento
   para esa especie y comparación;
2. buscar después la pareja más próxima dentro de ese conjunto de calidad;
3. exigir en un ensayo futuro que la combinación supere al mejor algoritmo
   individual antes de usarla.

RF+ET sigue siendo la pareja más cercana sin filtrar por calidad:

| Versión | RF+ET pareja más próxima | Contextos evaluables |
|---|---:|---:|
| V2 IDW común | 24 | 34 |
| V3 | 19 | 34 |
| V4 meteo | 21 | 34 |
| V4 balance | 22 | 34 |

Después de exigir que ambos modelos superen la prevalencia, el resultado es:

| Versión | Contextos con al menos dos modelos de calidad | RF+ET es la pareja de calidad más próxima |
|---|---:|---:|
| V2 IDW común | 17 | 4 |
| V3 | 19 | 13 |
| V4 meteo | 24 | 13 |
| V4 balance | 25 | 12 |

Por tanto, RF+ET es un control de estabilidad razonable, sobre todo en V3/V4,
pero no queda elegido como consenso operativo. El benchmark aún no calcula la
probabilidad combinada de cada pareja; sin demostrar que esa combinación vence
al mejor miembro individual, promocionarla sería injustificado.

## 4. Algoritmo con menor Brier

La tabla cuenta primeros puestos en los 34 contextos principales. Los empates
se conservan, por lo que una fila puede sumar más de 34. No es un promedio de
Brier.

| Contrato | LR | RF | ET | HGB | KNN | SVM |
|---|---:|---:|---:|---:|---:|---:|
| V2 IDW común | 1 | 4 | 6 | 7 | 7 | 11 |
| V3 | 8 | 7 | 1 | 2 | 8 | 8 |
| V4 meteo | 9 | 9 | 4 | 0 | 3 | 10 |
| V4 balance | 9 | 10 | 2 | 0 | 1 | 12 |

No existe un ganador universal. SVM acumula más primeros puestos en V2 y V4;
LR y RF ganan peso desde V3. HGB puede mejorar respecto a su propio resultado
anterior sin llegar a ser el mejor absoluto, por lo que esta tabla no sustituye
la comparación de cada algoritmo consigo mismo entre versiones.

## 5. Ganador más repetido por especie

Cada celda muestra el algoritmo que gana más veces entre `fixed_gap`/`lag_event`
y grupos 7/14. El denominador normal es cuatro; en `boletus_edulis` es dos por
la partición de clase única descrita antes.

| Especie | V2 | V3 | V4 meteo | V4 balance |
|---|---|---|---|---|
| `amanita_caesarea` | ET y RF, 2/4 | LR, 3/4 | RF, 3/4 | ET y RF, 2/4 |
| `boletus_aereus` | SVM, 3/4 | SVM, 4/4 | SVM, 3/4 | SVM, 3/4 |
| `boletus_edulis` | HGB y RF, 1/2 | LR y RF, 1/2 | LR y RF, 1/2 | LR y RF, 1/2 |
| `boletus_pinophilus` | SVM, 4/4 | RF, 4/4 | RF, 4/4 | RF, 4/4 |
| `cantharellus_cibarius_sl` | ET y HGB, 2/4 | HGB y RF, 2/4 | ET y LR, 2/4 | LR y RF, 2/4 |
| `hygrophorus_latitabundus` | SVM, 4/4 | KNN y SVM, 2/4 | KNN y SVM, 2/4 | SVM, 4/4 |
| `hygrophorus_marzuolus` | KNN, 4/4 | KNN y SVM, 2/4 | SVM, 4/4 | SVM, 4/4 |
| `lactarius_deliciosus` | HGB, 4/4 | LR, 4/4 | LR, 4/4 | LR, 4/4 |
| `morchella_elata_complex` | KNN, 3/4 | KNN, 4/4 | LR, 2/4 | LR, 2/4 |

La nueva observación de `boletus_pinophilus` sí importa: V4 pasa de no tener un
ganador estable en el informe 001 a RF 4/4 en meteorología y balance. Al mismo
tiempo, el cambio de `boletus_edulis` hace no evaluable la partición de 7 días.
Que dos revisiones alteren patrones concretos es evidencia de sensibilidad al
tamaño de muestra, no una razón para ignorarlas.

Los patrones más sólidos por ahora son SVM para `boletus_aereus`, RF para
`boletus_pinophilus`, LR para `lactarius_deliciosus` desde V3, y el paso de KNN
a SVM en `hygrophorus_marzuolus` al ampliar V4.

## 6. ¿El mejor algoritmo supera la prevalencia?

Se cuenta en cuántas comparaciones el mejor de los seis aporta más información
que predecir siempre la prevalencia de entrenamiento:

| Especie | V2 | V3 | V4 meteo | V4 balance |
|---|---:|---:|---:|---:|
| `amanita_caesarea` | 4/4 | 4/4 | 4/4 | 4/4 |
| `boletus_aereus` | 4/4 | 3/4 | 3/4 | 2/4 |
| `boletus_edulis` | 2/2 | 2/2 | 2/2 | 2/2 |
| `boletus_pinophilus` | 2/4 | 4/4 | 4/4 | 4/4 |
| `cantharellus_cibarius_sl` | 2/4 | 4/4 | 4/4 | 4/4 |
| `hygrophorus_latitabundus` | 4/4 | 2/4 | 4/4 | 4/4 |
| `hygrophorus_marzuolus` | 4/4 | 2/4 | 4/4 | 4/4 |
| `lactarius_deliciosus` | 4/4 | 4/4 | 4/4 | 4/4 |
| `morchella_elata_complex` | 4/4 | 3/4 | 2/4 | 2/4 |

V4 recupera señal en los dos `hygrophorus`, pero pierde robustez en
`boletus_aereus` y `morchella_elata_complex`. No hay una mejora general de V4.

## 7. Comparación de cada versión contra la anterior

Los siguientes recuentos comparan Brier de cada algoritmo sobre los mismos
contextos disponibles. Siguen sin promediar especies:

| Comparación | Algoritmo | Mejor | Igual | Peor |
|---|---|---:|---:|---:|
| V3 frente a V2 | LR | 19 | 0 | 15 |
|  | RF | 22 | 2 | 10 |
|  | ET | 24 | 0 | 10 |
|  | HGB | 22 | 4 | 8 |
|  | KNN | 16 | 0 | 16 |
|  | SVM | 19 | 0 | 14 |
| V4 meteo frente a V3 | LR | 17 | 0 | 17 |
|  | RF | 17 | 2 | 15 |
|  | ET | 13 | 0 | 21 |
|  | HGB | 20 | 4 | 10 |
|  | KNN | 16 | 0 | 16 |
|  | SVM | 18 | 1 | 14 |
| V4 balance frente a V3 | LR | 15 | 0 | 19 |
|  | RF | 19 | 0 | 15 |
|  | ET | 12 | 0 | 22 |
|  | HGB | 19 | 4 | 11 |
|  | KNN | 15 | 0 | 17 |
|  | SVM | 21 | 0 | 12 |

V3 sigue mejorando a V2 con más frecuencia en árboles, pero no domina todos
los casos. V4 meteo es prácticamente neutral para LR/KNN y desfavorable para
ET; ayuda con más frecuencia a HGB y SVM. El balance favorece más a RF/HGB/SVM,
pero empeora LR/ET/KNN con mayor frecuencia. Esto no supera el gate de mejora
consistente entre especies.

## 8. Diagnóstico corregido por horizonte

En las dos particiones lag hay 68 contextos evaluables
especie+grupo+horizonte. Son cortes repetidos de las mismas observaciones y no
se interpretan como 68 experimentos independientes. Los primeros puestos son:

| Contrato | LR | RF | ET | HGB | KNN | SVM |
|---|---:|---:|---:|---:|---:|---:|
| V2 IDW común | 6 | 5 | 12 | 10 | 14 | 21 |
| V3 | 11 | 11 | 8 | 4 | 10 | 24 |
| V4 meteo | 14 | 12 | 7 | 8 | 11 | 16 |
| V4 balance | 13 | 16 | 4 | 3 | 13 | 19 |

Los patrones más estables a través de horizontes son:

- V3: SVM gana 6/8 en `boletus_aereus`, 8/8 en
  `hygrophorus_latitabundus`, 6/8 en `hygrophorus_marzuolus` y KNN 8/8 en
  `morchella_elata_complex`;
- V4 meteo: LR gana 8/8 en `lactarius_deliciosus`, KNN 6/8 en
  `hygrophorus_latitabundus` y SVM 6/8 en `hygrophorus_marzuolus`;
- V4 balance: RF gana 8/8 en `boletus_pinophilus`, SVM 8/8 en
  `hygrophorus_marzuolus` y LR 8/8 en `lactarius_deliciosus`.

Esto sirve para valorar estabilidad del algoritmo dentro del contrato, no para
crear un modelo distinto por horizonte ni para contar cuatro veces el tamaño
de muestra.

## 9. Decisión actual y análisis siguiente

Los datos no justifican todavía un consenso operativo fijo ni la promoción de
V4. Tampoco justifican eliminar algoritmos o versiones:

- V2, V3 y V4 se preservan como versiones consultables;
- los seis algoritmos siguen activos o experimentales según configuración, no
  por código específico de una versión;
- RF+ET se conserva como referencia de estabilidad, pero no como ganador;
- cualquier combinación futura deberá generar probabilidades de ensemble y
  superar al mejor miembro individual por especie y contrato;
- las cuatro salidas negativas que el usuario incorporará después formarán un
  snapshot nuevo y se compararán sin sobrescribir este.

El análisis siguiente debe localizar falsos positivos y negativos compartidos
por especie, horizonte, fase de florada y meteorología. Solo después se decidirá
si conviene añadir una familia concreta: curva suave/GAM para respuestas no
lineales, estado temporal para duración y parpadeo, o jerarquía entre especies
para compartir soporte. No se añade un algoritmo simplemente por ampliar la
lista.

## 10. Evidencia canónica

Los cuatro JSON de comparación viven en
`docker-data/audits/mushroom-ml-snapshot-20260816/`:

- `comparison-fixed-groups7.json`;
- `comparison-fixed-groups14.json`;
- `comparison-lag-groups7.json`;
- `comparison-lag-groups14.json`.

El antiguo `comparison-lag-groups7.pre-horizon-projection.json` se conserva
solo para demostrar el cambio metodológico; no es candidato ni fuente de
decisión. `MANIFEST.json` fija hashes, recuentos y estado del snapshot.

Validación final del código y de los contratos: 801/801 pruebas locales pasan.
