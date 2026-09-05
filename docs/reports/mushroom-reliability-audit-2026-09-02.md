# Auditoría local de fiabilidad por especie y área

Fecha: 2026-09-02.

Estado: auditoría de los datos locales e implementación local del productor de
selecciones. El batch actualmente instalado sigue siendo anterior al catálogo
`1.2`; ningún resultado de este informe modifica todavía el precálculo o la UI.

## Fuente y alcance

Se leyó exclusivamente el hold-out local ya generado:

```text
docker-media/rainmapper/mushroom-derived/ml_models/batches/
local_operational_20260901T214532Z/holdout-predictions.jsonl
```

El manifiesto declara 28.160 filas y SHA-256
`c744477358392cf3b93e505b53c5a512840924a16498d970901f01499ad86b65`;
el digest se verificó contra el fichero local. No se ajustaron modelos, no se
ejecutó inferencia y no se consultó meteorología.

La unidad territorial es `area_id`. La auditoría no crea selecciones por
microárea.

## Herramienta reproducible

El ensayo quedó generalizado en:

- `rainmapper_core/mushroom_ml_reliability_audit.py`: agregación y ranking puro;
- `scripts/audit-mushroom-ml-reliability.py`: CLI para cualquier especie, área
  y split;
- `tests/test_mushroom_ml_reliability_audit.py`: separación de área/split,
  ranking conservador y rechazo de duplicados.

Ejemplo para Aereus/Olvan en el split oficial de 14 días:

```bash
.venv/bin/python scripts/audit-mushroom-ml-reliability.py \
  --holdout docker-media/rainmapper/mushroom-derived/ml_models/batches/local_operational_20260901T214532Z/holdout-predictions.jsonl \
  --species boletus_aereus \
  --area olvan \
  --output /private/tmp/aereus-olvan-reliability-audit.json
```

Omitir `--species` y `--area` produce la auditoría completa del split oficial.
Cada filtro puede repetirse. `--split` selecciona otro contrato de forma
explícita y `--all-splits` reproduce la comparación diagnóstica histórica sin
mezclarlos. `--no-stability` ofrece un primer barrido más rápido;
`--include-candidates` incorpora también cada descarte y sus motivos.

La salida se marca expresamente como
`selection_status=provisional_not_for_runtime`. Los splits siempre se informan
por separado y nunca se calcula un ganador cruzado entre ellos. Cada
`observation_id` cuenta individualmente contra su predicción. La retirada de
grupos temporales es solo un diagnóstico posterior: no modifica el ganador.

## Política acordada y resultado Aereus/Olvan

La política definitiva usa `fruiting_groups_14d`, no impone mínimos manuales de
observaciones, recomendaciones o recall y exige únicamente población
comparable, ambas clases, al menos una recomendación favorable, probabilidades
válidas y Brier estrictamente mejor que prevalencia. Wilson al 95 % gobierna el
ranking; ROC-AUC, recall, cobertura y calibración son contexto o desempates.

El ganador provisional de Aereus/Olvan es:

| Split | Candidato provisional | Evidencia al recomendar salir | Encuentra favorables | Estabilidad al retirar grupos |
|---|---|---:|---:|---:|
| `fruiting_groups_14d` | V6 windowed, 90 d + estado físico, lag, horizonte 1, `smooth_shared_logistic_v1` | 7/7 = 100 %; Wilson 64,6 % | 7/9 = 77,8 % | mismo ganador en 4/6 omisiones |

Los dos splits de grupos usan las mismas 20 observaciones de Olvan —9
favorables y 11 desfavorables—, pero las agrupan de forma distinta: ocho grupos
en 7 días y seis en 14 días. El split por campaña tiene 30 observaciones y diez
grupos, pero solo contiene 72 candidatos de V6; no permite una comparación
justa entre todas las versiones.

La justificación provisional del ganador oficial es directa: se evaluó sobre
20 observaciones comparables, recomendó salir siete veces y acertó las siete,
encontró siete de los nueve favorables, mejoró el Brier de prevalencia en
0,13460 y obtuvo ROC-AUC 0,94444. Al retirar grupos completos conserva el ganador
en cuatro de seis pruebas. Esa sensibilidad se muestra, pero no descuenta
aciertos ni reordena el resultado principal.

## Hallazgos de la auditoría completa

El batch contiene tres contratos de split. La comparación diagnóstica antigua
separaba 124 combinaciones especie/área/split. Bajo la política acordada, el
split oficial de 14 días contiene 43 ámbitos: 12 producen un candidato elegible
y 31 se abstienen. La cifra mayor de ganadores respecto a los gates provisionales
es el efecto esperado de retirar los cortes arbitrarios, no evidencia nueva.
Algunos ganadores tienen una sola recomendación favorable y Wilson 20,7 %: la
herramienta conserva esa debilidad visible en vez de convertirla en un descarte
mediante un número elegido a mano.

El catálogo instalado no es válido como fuente directa del futuro selector: se
generó con una clave que no incluía `split_id` y acumuló filas de 7 días y 14
días; V6 pudo acumular además las del split por campaña.

El productor `rainmapper_core/mushroom_ml_quality_catalog.py` queda corregido:
incluye el split real en la clave y en cada entrada, rechaza filas que no lo
declaran y permite lookup explícito por split. Para compatibilidad, `entries`
contiene solo el split de 7 días y `alternate_split_entries` conserva 14 días y
campaña sin mezclarlos. La prueba sobre el hold-out local produce 6.308 entradas
separadas —2.866 de 7 días, 2.866 de 14 días y 576 de campaña— y ningún `n_test`
supera 41; antes la mezcla alcanzaba 98. El catálogo instalado no se modifica:
la corrección se materializará en un futuro entrenamiento autorizado.

## Reauditoría del batch nuevo por los siete días operativos

Después de descargar observaciones y meteorología histórica actuales se generó
e instaló coherentemente el batch
`local_operational_20260902T145853Z`, snapshot
`sha256:f3ff8a52755976e2618f067e6f9635229609f81f7fc1e890b96434d67108a36a`.
Las cinco versiones instaladas apuntan a ese mismo batch y declaran
`promotion_gate_status=passed`. La auditoría leyó sus 83 MiB de predicciones
hold-out; no ejecutó modelos ni meteorología.

La herramienta se corrigió a esquema `0.2-audit`: ya no proclama un ganador
único mezclando horizontes. Para el día operativo `N` compara exclusivamente
`lag hN` con `fixed h7`, conserva el `temporal_contract_id` exacto y publica
ganador o abstención. Resultado abreviado de los cinco ámbitos solicitados:

| Especie/área | Día | Candidato provisional | Fiabilidad al recomendar salir | Prueba |
|---|---:|---|---:|---:|
| Aereus/Olvan | 1 | V6 smooth 90, lag h1, shared logistic | 100 % · 8/8 | 21 obs. · 6 floradas |
| Aereus/Olvan | 2 | V6 smooth 90, lag h2, shared logistic | 100 % · 7/7 | 21 obs. · 6 floradas |
| Aereus/Olvan | 3 | V6 smooth 30, fixed h7, shared logistic | 71,4 % · 10/14 | 21 obs. · 6 floradas |
| Aereus/Olvan | 4 | V6 smooth 90, lag h4, shared logistic | 85,7 % · 6/7 | 21 obs. · 6 floradas |
| Aereus/Olvan | 5–7 | V6 smooth 30, fixed h7, shared logistic | 71,4 % · 10/14 | 21 obs. · 6 floradas |
| Aereus/Santa Maria de Merlès | 1–7 | Abstención | — | 5 obs. · 2 floradas |
| Ous de reig/Olvan | 1 | V6 smooth 90, lag h1, partial pooling | 60 % · 6/10 | 21 obs. · 6 floradas |
| Ous de reig/Olvan | 2 | V4 climatic balance, lag h2, logistic | 80 % · 4/5 | 21 obs. · 6 floradas |
| Ous de reig/Olvan | 3 | V6 smooth 90, lag h3, shared logistic | 75 % · 6/8 | 21 obs. · 6 floradas |
| Ous de reig/Olvan | 4 | V6 smooth 90, lag h4, partial pooling | 75 % · 6/8 | 21 obs. · 6 floradas |
| Ous de reig/Olvan | 5–6 | V4 extended, fixed h7, extra trees | 60 % · 6/10 | 21 obs. · 6 floradas |
| Ous de reig/Olvan | 7 | V4 extended, lag h7, logistic | 100 % · 4/4 | 21 obs. · 6 floradas |
| Pinicola/Salteguet | 1 | V3 physical, lag h1, KNN | 100 % · 4/4 | 6 obs. · 2 floradas |
| Pinicola/Salteguet | 2–3 | V2 common, lag hN, logistic | 100 % · 4/4 | 6 obs. · 2 floradas |
| Pinicola/Salteguet | 4 | V6 smooth 30, fixed h7, partial pooling | 100 % · 4/4 | 6 obs. · 2 floradas |
| Pinicola/Salteguet | 5 | V3 physical, lag h5, KNN | 100 % · 4/4 | 6 obs. · 2 floradas |
| Pinicola/Salteguet | 6–7 | V6 smooth 30, fixed h7, partial pooling | 100 % · 4/4 | 6 obs. · 2 floradas |
| Edulis/Salteguet | 1–3 | V3 physical, lag hN, logistic | 100 % · 4/4 | 5 obs. · 1 florada |
| Edulis/Salteguet | 4–7 | V2 common, lag hN, logistic | 100 % · 4/4 | 5 obs. · 1 florada |

Los rangos `hN` de la tabla significan que cada día conserva su horizonte
exacto; no se retargetea un único modelo. Los resultados de Salteguet tienen
evidencia temporal especialmente débil: una o dos floradas y estabilidad nula
en varias omisiones. Se conservan como candidatos provisionales porque no se
acordaron mínimos manuales, pero la UI deberá mostrar siempre observaciones y
floradas junto al porcentaje y la fracción.

## Materialización, fallbacks y abstenciones

Al aplicar el productor local `1.2` al batch nuevo se materializan 301
resoluciones —43 combinaciones especie/área por siete días—:

- 84 ganadores específicos del área (27,9 %);
- 161 fallbacks de la misma especie (53,5 %);
- 56 abstenciones (18,6 %).

El fallback hereda únicamente versión, perfil/ventana, contrato temporal,
horizonte y estimador desde el ganador agregado de la especie. La futura
probabilidad seguirá calculándose con la meteorología y las features del área
consultada. En consecuencia, no significa «probabilidad genérica de especie»:
significa «candidato demostrado para la especie, aplicado a esta área porque la
evidencia propia del área no permite elegir uno con suficiente fundamento».

Las 56 abstenciones están concentradas en tres especies durante sus siete días:

| Especie | Áreas | Observaciones únicas en 14 días | Clases presentes | Resoluciones abstención |
|---|---:|---:|---|---:|
| `hygrophorus_latitabundus` | 3 | 4 | 4 favorables, 0 desfavorables | 21 |
| `hygrophorus_marzuolus` | 2 | 6 | 6 favorables, 0 desfavorables | 14 |
| `morchella_elata_complex` | 3 | 5 | 0 favorables, 5 desfavorables | 21 |

No existe candidato agregado elegible para ellas porque el hold-out oficial no
contiene ambas clases. Sustituir esa abstención por la versión preferida
contradiría el objetivo de mostrar únicamente un candidato cuya fiabilidad haya
sido demostrada. Las nuevas observaciones podrán cambiar esta situación en un
entrenamiento posterior sin modificar manualmente la política.

## Conclusión

La herramienta permite auditar cualquier especie/área sin cálculo científico
nuevo y demuestra que el proceso es finito. Cada observación cuenta, Wilson
incorpora el tamaño de la evidencia y la estabilidad por grupos queda como
contexto. El productor local ya sella ganadores, fallbacks y abstenciones en el
catálogo `1.2`; falta comprobar el artefacto de un nuevo entrenamiento local y
después adaptar el precálculo y la UI. El batch actualmente instalado continúa
siendo anterior a este contrato.

## Verificación del primer reentrenamiento

El batch `local_operational_20260902T182212Z` completó 636/636 fits y fue
instalado, pero su catálogo permaneció en esquema `1.1` sin selecciones. La
causa no fue científica: el entrenamiento se lanzó desde una imagen HA local
construida antes de integrar el selector. El digest declarado del catálogo
coincidía con el fichero, por lo que era una publicación antigua coherente, no
una corrupción.

Se reconstruyó y recreó exclusivamente HA local. La comprobación dentro del
nuevo contenedor confirmó catálogo `1.2`, selector `1.0` y split oficial
`fruiting_groups_14d`. El validador nuevo rechazó el catálogo `1.1` con
`Quality catalog contract is invalid`; esta comprobación ocurre antes de los
fits operativos. Como prueba completa sin modificar el batch, la misma imagen
generó desde sus 27.328 filas un catálogo `1.2` en 12,756 s, validó sus
referencias contra los 636 fits y reprodujo las 301 resoluciones y el
`selection_id` esperados. Falta repetir el entrenamiento desde la imagen ya
actualizada para obtener una publicación atómica válida.
