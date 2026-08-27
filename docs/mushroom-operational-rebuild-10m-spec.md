# Especificación: reconstrucción y reentrenamiento operativo en ≤10 minutos

Estado: especificación aprobada; entregas A y B implementadas y validadas localmente

Fecha: 2026-08-26

Ámbito: flujo local «Reconstruir y reentrenar operativo»

Informe reproducible de implementación y validación:
`docs/reports/operational-rebuild-10m-lab-2026-08-26.md`.

## 1. Objetivo

Reducir el tiempo total monotónico del flujo operativo a un máximo de 600
segundos, manteniendo:

- la integridad científica de las particiones y métricas;
- la cancelación y el retry;
- el staging, rollback y promoción atómica;
- la producción completa de artefactos operativos;
- los contratos de inferencia actuales;
- la política de retención actual.

El objetivo no se limita a acelerar el volumen actual. El diseño debe admitir
40.000 observaciones sin un límite artificial por número de observaciones. La
admisión se decidirá por una estimación previa de bytes y trabajo, no por un
contador fijo de filas.

## 2. Estado comprobado

La línea base local de 2026-08-26 utilizó 374 observaciones, 16 especies
seleccionables y un plan operativo efectivo de 9 especies, 5 versiones, 11
perfiles y 714 fits finales.

| Fase | Fría | Caliente |
|---|---:|---:|
| Total | 1.158,499 s | 1.168,757 s |
| Reconstrucción y verificación | 101,125 s | 101,130 s |
| Preparación operativa | 808,503 s | 821,304 s |
| Entrenamiento final | 220,917 s | 222,255 s |
| Instalación y promoción | 3,287 s | 3,448 s |

Fuentes primarias locales:

- `docker-data/performance-lab/20260825T232803Z/telemetry/cold.json`
- `docker-data/performance-lab/20260825T232803Z/telemetry/warm.json`
- `docker-data/mushroom-data/ml_models/batches/local_operational_20260826T000305Z/benchmark-report.json`

La ejecución caliente no mejoró la preparación y durante esa fase se observó
aproximadamente un núcleo de CPU ocupado. La compactación de cola, las
peticiones de red y la telemetría no están justificadas como objetivos de esta
refactorización.

El plan final comprobado se distribuye así:

| Versión | Perfiles | Estimadores | Fits finales |
|---|---:|---:|---:|
| altitude_v2 | 1 | 6 | 108 |
| biology_v3 | 2 | 6 | 216 |
| biology_v4 | 2 | 6 | 216 |
| biology_v5_windowed_raw_weather | 3 | 2 | 108 |
| biology_v6_windowed_smooth_hierarchical | 3 | 3 | 66 |
| Total | 11 | — | 714 |

## 3. Diagnóstico

La fase denominada «preparación» mezcla dos trabajos distintos:

1. materialización de features y benchmarks;
2. búsqueda y evaluación científica mediante miles de fits internos.

El flujo actual carga a la vez los benchmarks V3, V4 y V5, fixed y lag, en
`scripts/run-mushroom-ml-multiversion-job.py`. Después,
`mushroom_ml_runtime_trainer.write_batch` conserva esos objetos durante los 714
fits y cada llamada a `fit_artifact` vuelve a extraer matrices por
versión/perfil/especie.

En V5, `_select_v5` vuelve a imputar y escalar los mismos pliegues dentro de
cada configuración. En V6, `select_joint_config` vuelve a construir el diseño
parcial para cada combinación de `C` y `deviation_scale`, aunque el diseño no
depende de `C`.

La optimización de matrices por sí sola no elimina los fits. Su ahorro estimado
es de 2 a 4 minutos y no basta para alcanzar el objetivo. El camino operativo
también debe dejar de repetir automáticamente una búsqueda científica completa
de hiperparámetros ya validados.

## 4. Presupuesto temporal obligatorio

| Trabajo | Presupuesto máximo |
|---|---:|
| Snapshot, reconstrucción, verificación y V0 | 130 s |
| Workspace, materialización y validación operativa | 230 s |
| Entrenamiento final | 225 s |
| Verificación, instalación y promoción | 10 s |
| Margen | 5 s |
| Total | 600 s |

Una implementación que no proyecte una preparación de 230 segundos o menos no
continuará hacia una reescritura más amplia. El ahorro de I/O o matrices no
podrá utilizarse para ocultar un número de fits incompatible con este
presupuesto.

## 5. Separación de retune y rebuild operativo

### 5.1 Retune científico

El retune científico es el único flujo que explora grids de hiperparámetros.
Produce un catálogo inmutable y verificable de decisiones de tuning. No forma
parte automáticamente de cada reconstrucción operativa.

Cada entrada del catálogo se identifica por:

- versión;
- contrato temporal;
- perfil;
- estimador;
- especie o ámbito conjunto;
- fingerprint del contrato de features;
- fingerprint de la implementación y del espacio de búsqueda.

También conserva la configuración elegida, snapshot de origen, particiones,
métricas, disponibilidad y hashes de los informes que justifican la decisión.

### 5.2 Rebuild operativo rápido

El rebuild operativo:

1. valida la compatibilidad del catálogo de tuning activo;
2. reconstruye las features con los datos actuales;
3. recalcula las métricas holdout usando una configuración ya elegida, sin
   volver a explorar el grid;
4. aplica los umbrales de calidad actuales;
5. reentrena los 714 artefactos finales con todos los datos elegibles;
6. verifica y promueve atómicamente el batch.

Reutilizar una configuración no significa reutilizar un modelo: todos los
modelos finales se vuelven a ajustar con los datos actuales.

### 5.3 Fallo cerrado

El rebuild nunca ejecutará silenciosamente un retune completo. Exigirá retune
si falta una decisión o cambia cualquiera de estos elementos:

- contrato o procedencia de una feature;
- versión o perfil;
- estimador o implementación relevante;
- espacio de búsqueda;
- especie o ámbito conjunto requerido por el plan.

La incorporación de nuevas observaciones no invalida por sí sola el catálogo.
Las métricas holdout actuales siguen siendo obligatorias y pueden impedir la
promoción. El informe debe mostrar la edad y snapshot de las decisiones para
que el retune científico pueda solicitarse explícitamente.

## 6. Workspace compacto común

### 6.1 Ejes

El workspace mantiene en RAM dos universos compatibles:

- fixed: una fila por observación fija;
- lag: una fila por observación y horizonte.

Cada universo contiene:

- una matriz `float64` inmutable de features;
- objetivo binario;
- especie codificada como entero;
- índices compactos de observación, fechas, horizonte y grupos de validación;
- registro de columnas y procedencia.

No se conservarán diccionarios predictivos completos una vez validada y
materializada su información en arrays compactos.

### 6.2 Unión de columnas

Los artefactos locales actuales contienen una unión nominal de 510 columnas
fixed y 511 lag para las cinco versiones. Esta cifra no autoriza deduplicar por
nombre: dos columnas solo comparten almacenamiento si una prueba de contrato
confirma la misma procedencia, orientación temporal y valores.

Cada perfil se representa como un vector inmutable de índices de columna. Un
perfil no construye una matriz base propia.

### 6.3 Ciclo de vida de transformaciones

No habrá una caché LRU de tamaño arbitrario. El orden de ejecución determinará
la memoria viva:

```text
temporal
  → partición
    → especie o ámbito conjunto
      → pliegue
        → transformación ancha
          → perfiles
            → estimadores/configuraciones
```

Para V2–V5, cada bloque produce como máximo:

- una vista imputada para estimadores que no escalan;
- una vista imputada y escalada para estimadores que escalan;
- vistas de columnas por perfil.

El bloque se libera antes de materializar el siguiente. Las medianas, medias y
desviaciones siempre se ajustan exclusivamente con el train correspondiente;
nunca se mezclan especies o datos de validación.

V6 conserva su ámbito conjunto. El diseño parcial se materializa una vez por
`deviation_scale`; todos los valores de `C` se evalúan antes de liberarlo. No se
materializa de nuevo para cada `C`.

## 7. Representación persistente

Los JSON actuales dejan de ser la representación interna del cálculo. Los
informes auditables continúan siendo JSON, pero las entradas reutilizables del
workspace deben ser columnares, tipadas y verificables mediante hashes.

La primera implementación podrá construir el workspace desde los benchmarks
actuales para limitar el cambio. La siguiente puerta sustituirá la cadena de
benchmarks duplicados por una representación compacta producida una sola vez.
Ambas rutas deben generar el mismo workspace lógico y superar una comparación
de equivalencia antes de retirar la ruta antigua.

La escritura persistente seguirá el patrón staging + fsync + rename y no
cambiará la retención.

## 8. Paralelismo acotado

La validación de especies independientes puede ejecutarse concurrentemente
dentro del mismo contenedor local. Esto no crea otro servicio ni otro worker.

Reglas:

- un solo nivel de paralelismo para evitar sobresuscripción;
- límite derivado de CPU y del presupuesto de memoria por bloque;
- orden determinista de resultados antes de escribir informes;
- semillas actuales preservadas;
- cancelación comprobada entre tareas y fits;
- ningún proceso concurrente escribe directamente el manifest final.

Antes de elegir hilos o procesos se realizará un benchmark dirigido. Si el
backend altera resultados, cancelación o memoria, se mantendrá ejecución
secuencial y se revisará el presupuesto temporal.

El entrenamiento final puede permanecer secuencial en la primera entrega, ya
que actualmente consume unos 221 segundos y cabe en el presupuesto. La primera
prioridad de paralelismo es la validación operativa.

## 9. Presupuesto de memoria para 40.000 observaciones

Supuestos comprobables del plan actual:

- 40.000 filas fixed;
- siete horizontes lag: 280.000 filas;
- 510/511 columnas nominales;
- 9 especies operativas;
- diseño V6 parcial máximo observado: 1.035 columnas.

| Estructura | Tamaño aproximado |
|---|---:|
| Base fixed | 155,6 MiB |
| Base lag | 1.091,6 MiB |
| Ambas bases | 1.247,3 MiB |
| Ambas bases por cada 100 observaciones | 3,12 MiB |
| Mayor transformación lag por especie equilibrada | 121,3 MiB |
| Mayor diseño V6 lag conjunto | 2,16 GiB |
| Pico estructural estimado antes de copias del estimador | ~3,5 GiB |

El proceso realizará un preflight con filas, columnas, dtype, mayor especie,
contratos temporales y expansión V6 reales. La estimación incluirá un factor
medido para copias internas del estimador, no un multiplicador inventado.

Presupuesto recomendado para validar 40.000 observaciones: 12 GiB. Un límite de
16 GiB ofrece margen cómodo en el M1 de 32 GiB. Esta especificación no cambia
el límite del worker normal ni el de HA real.

## 10. Telemetría y evidencia

La telemetría monotónica persistente debe añadir, además de los contadores de
I/O ya instrumentados:

- filas y columnas por universo;
- bytes base y bytes por cada 100 observaciones;
- bytes máximos de transformaciones vivas;
- RSS máximo observado;
- matrices construidas y reutilizaciones;
- fits planificados, iniciados, completados, fallidos y evitados;
- fits separados en tuning, validación y entrenamiento final;
- tiempo por versión, perfil, estimador y familia de trabajo;
- fingerprint y edad del catálogo de tuning.

Los eventos deben permanecer acotados. Los contadores agregados son
persistentes; no se escribirá un evento a disco por cada iteración interna.

## 11. Compatibilidad e integridad

La refactorización debe demostrar:

- mismas filas elegibles y mismas claves de comparación;
- mismas particiones y ausencia de leakage;
- mismos vectores de features por perfil;
- mismas estadísticas de imputación y escalado;
- mismas configuraciones cuando se ejecuta el retune de referencia;
- probabilidades y métricas equivalentes dentro de una tolerancia declarada;
- mismo conjunto de artefactos y estados de disponibilidad;
- mismo comportamiento ante cancelación y fallo parcial;
- ningún cambio del batch activo antes de completar verificación y promoción.

No se exige que los bytes serializados de joblib sean idénticos si el formato
incluye detalles no deterministas, pero sí igualdad contractual y numérica del
modelo cargado.

## 12. Plan de entrega y puertas de parada

### Entrega A: catálogo de tuning y contador real de fits

- Extraer o producir el catálogo desde una ejecución científica validada.
- Añadir fingerprints y validación de compatibilidad.
- Hacer que el rebuild operativo use configuraciones congeladas.
- Medir el número exacto de fits evitados.

Puerta: si la preparación no proyecta una reducción mínima del 50 %, no se
continúa sin revisar el plan.

Evidencia local de la entrega A:

- catálogo determinista `sha256:e9730b7c0e82ef37c321f5ea2cfc04f8e08f1ea6976b6d9559140291972f6e99`;
- 714 decisiones compatibles para los 714 fits del batch de origen
  `local_operational_20260826T000305Z`;
- 714 artefactos comprobados por hash antes de extraer su configuración;
- 6,465 s para verificar y cargar el catálogo completo en una lectura local;
- 1.620 fits internos máximos eliminados del entrenamiento final V5;
- 3.240 fits internos máximos eliminados de las dos validaciones cronológicas
  V5 y 432 de las tres validaciones V6;
- 5.292 fits internos máximos eliminados en total para el plan actual.
- preparación operativa congelada completa: 459,101 s;
- reducción frente a las líneas base de 808,503 y 821,304 s: 349,402 y
  362,203 s, aproximadamente un 43–44 %;
- materialización V3/V4/V5: aproximadamente 360 s; holdout V2–V6 e informes:
  aproximadamente 99 s, según los artefactos persistidos de la ejecución;
- proyección total, incluyendo los 6,465 s del catálogo: aproximadamente
  813–816 s, unos 13 min 33 s–13 min 36 s.

Los recuentos de fits son máximos estructurales: el código anterior podía
abortar una configuración concreta antes de completar todos sus pliegues si el
estimador fallaba. La reducción temporal extremo a extremo aún no se presenta
como medida, porque no se repitieron reconstrucción, entrenamiento final ni
promoción. La puerta de A no se supera: la preparación queda 189 s por encima
de 270 s y la reducción es inferior al 50 %. La revisión de la puerta atribuye
el residual dominante a cinco materializaciones consecutivas de bases V3
fixed, V3 lag, V4 fixed, V4 lag y V5 fixed/lag. No se ampliará el catálogo; la
siguiente decisión debe limitarse al workspace común de la entrega B.

### Entrega B: workspace desde entradas actuales

- Construir matrices comunes fixed/lag.
- Añadir vistas de perfiles y transformaciones por bloque.
- Adaptar evaluación y entrenamiento a una única instancia del workspace.
- Mantener la ruta antigua solo como oráculo de equivalencia en pruebas.

Puerta: equivalencia completa en un subconjunto que incluya las cinco
versiones, los once perfiles y las nueve especies.

Evidencia local de la entrega B (2026-08-26):

- preparación operativa completa sobre el mismo snapshot congelado, los once
  perfiles seleccionados y el catálogo de la entrega A: aproximadamente
  185,4 s;
- reducción frente a los 459,101 s de la entrega A: aproximadamente 273,7 s,
  un 59,6 % adicional; frente a las líneas base originales de 808,503 y
  821,304 s: aproximadamente 77,1–77,4 %;
- una única base máxima `2011-11-11..2026-08-20`, 293 estaciones cargadas y
  62 series de microárea construidas; 124 reutilizaciones de serie y 124 de
  vista exacta;
- 1.048 estados de suelo operativos conservados en memoria y reutilizados por
  V5;
- igualdad semántica exacta de V3 fixed/lag, V4 fixed/lag para
  `wv0033_0_30cm` y V5 fixed/lag frente a los artefactos congelados; solo se
  normalizaron rutas/metadatos de materialización y se omitieron las otras
  cinco variantes de suelo exclusivamente científicas;
- `heldout-predictions.jsonl` idénticos byte por byte: 16.640 filas V2--V5,
  SHA-256 `2c55f6ad3eca1696ee41bcb9ad5263f7ba323236ba03e8ed68b3ff21d02b2447`,
  y 10.656 filas V6, SHA-256
  `2aba4cc28e020645d4c575561c97030e982d77078a623f1d503c51930a4d444c`.

La puerta queda superada para los ocho artefactos operativos realmente
consumidos. El catálogo de tuning y los hold-out cubren las cinco versiones,
los once perfiles seleccionados y todas las especies elegibles del snapshot.
No se ejecutó el entrenamiento final ni promoción.

### Entrega C: paralelismo de validación

- Benchmark de backend y nivel de concurrencia.
- Límite por memoria y control de sobresuscripción.
- Pruebas de orden determinista, cancelación y fallo.

Puerta: reducción proyectada de preparación a ≤230 segundos.

### Entrega D: representación compacta persistente

- Evitar la materialización y carga simultánea de benchmarks JSON duplicados.
- Mantener informes y hashes auditables.
- Validar proyecciones de 4.000 y 40.000 observaciones sin entrenamientos
  completos de esas escalas.

### Aceptación final local

- pruebas unitarias y de contrato dirigidas;
- comparación numérica antigua/nueva;
- un flujo frío completo ≤600 segundos;
- un flujo caliente completo ≤600 segundos;
- cero fits fallidos no previstos;
- promoción y rollback comprobados;
- `git diff --check` limpio.

No se realizará build, publicación, instalación, bump o release como parte de
esta especificación.

## 13. Riesgos abiertos

1. **Configuraciones congeladas envejecidas.** Se mitiga mostrando procedencia
   y edad, recalculando métricas con datos actuales y ofreciendo retune
   explícito; nunca mediante retune silencioso.
2. **Deduplicación incorrecta de features.** Se usan fingerprints de contrato y
   pruebas de valores, no solo nombres.
3. **Leakage por transformación global.** Toda estadística aprendida permanece
   ligada al train de especie/partición o al ámbito conjunto declarado por V6.
4. **Copias ocultas de sklearn.** Se miden RSS y memoria por estimador antes de
   fijar la concurrencia.
5. **No determinismo concurrente.** Se conservan semillas, se ordenan resultados
   y el cambio se rechaza si altera predicciones o contratos.
6. **Complejidad de migración.** La ruta nueva se introduce detrás de pruebas de
   equivalencia y la ruta antigua se conserva como oráculo hasta superar las
   puertas, no como fallback silencioso en producción.
7. **Ahorro insuficiente.** El proyecto se detiene en cualquier puerta que no
   sustente el presupuesto de 600 segundos; no se amplía la refactorización por
   intuición.

## 14. Fuera de alcance inicial

- reescribir kernels en C antes de perfilar el workspace optimizado;
- compactar la cola sin evidencia nueva;
- cambiar retención;
- modificar HA real o el worker normal;
- crear otro servicio worker;
- cambiar modelos, grids o umbrales científicos para conseguir tiempo.
