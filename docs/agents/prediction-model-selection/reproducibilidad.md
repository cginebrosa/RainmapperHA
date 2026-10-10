# Ejecución y verificación

La evidencia privada está en `tmp/prediction-model-selection/`; las entradas y
modelos reutilizados permanecen en `tmp/prediction-research/`. Ambas carpetas
cuentan para el mismo presupuesto. No contiene cambios operativos.

## Orden del cálculo

Los comandos se ejecutan desde la raíz del repositorio, uno cada vez. Son el
registro del procedimiento, no una instrucción para repetir etapas ya cerradas.
Los scripts rechazan sobrescribir sus resultados.

```sh
.venv/bin/python -B scripts/prediction_model_selection/bounded.py inventory-retry .venv/bin/python -B -m scripts.prediction_model_selection.inventory
.venv/bin/python -B scripts/prediction_model_selection/bounded.py ranking-2024 .venv/bin/python -B -m scripts.prediction_model_selection.ranking --fold 2024
.venv/bin/python -B scripts/prediction_model_selection/bounded.py evaluate-2024 .venv/bin/python -B -m scripts.prediction_model_selection.evaluate --fold 2024
```

La secuencia ranking/evaluate se aplica después a 2025 y 2026, con nombre de lote
propio. Una vez completos los tres cortes:

```sh
.venv/bin/python -B scripts/prediction_model_selection/bounded.py analysis .venv/bin/python -B -m scripts.prediction_model_selection.analyze
.venv/bin/python -B scripts/prediction_model_selection/bounded.py closure .venv/bin/python -B -m scripts.prediction_model_selection.close
```

La presencia de estos comandos no demuestra que hayan terminado. Consultar los
ledgers `runs/*.json`, resúmenes de cada corte y [estado.md](estado.md).

## Qué conserva cada etapa

- `inventory.json`: hashes de originales, protocolo y cada archivo del estudio
  anterior, recuentos y presupuesto usado.
- `runs/`: comandos, PID, estado, tiempo, máximos muestreados de RSS y bytes,
  fallos conservados y manifiesto de fuentes antes de cada ejecución.
- `source-archive/`: bytes exactos de cada versión ejecutada, por SHA-256.
- `fold-AAAA/recent-*.jsonl`: predicciones de área Y−1 fuera de ajuste.
  `combined-*.jsonl` añade Y−2; `quality-A/B.json` conserva la fórmula nativa.
- `ranking-provenance.json`: modelos, entrenamiento, entradas, código y hashes
  de salidas. `ranking-summary.json` acredita completitud y reproducción exacta
  del catálogo antiguo.
- `fold-AAAA/evaluation/`: 812 emisiones en total por variante, distribuidas por
  año, con trazas; control técnico del antiguo selector y equivalencia de entradas
  B/C por emisión; sellos anteriores y hashes posteriores.
- `analysis/`: matrices, contrastes pareados, intervalos, sensibilidad, regla
  exploratoria y tablas agregadas sin identificadores privados.
- `closure.json`, si existe: comprobación de originales, archivos antiguos,
  controles, análisis, fuentes archivadas y documentación entregada.

## Pruebas dirigidas

```sh
.venv/bin/python -B -m unittest tests.test_prediction_model_selection_ranking tests.test_prediction_model_selection_daily tests.test_prediction_model_selection_resources tests.test_prediction_model_selection_analysis
git diff --check
```

Las pruebas comprueban exclusión/etiquetas/prevalencia/cobertura, selección diaria
conservando el orden, equivalencia diferida/exhaustiva, contratos meteorológicos,
presupuesto combinado, contabilidad de matrices y bootstrap, mínimos de utilidad
y controles completos. No son una validación de HA ni de una release.

No borrar resultados fallidos para reintentar. Resolver la causa, preservar su
sello y dar nombre nuevo al lote; si existe salida parcial, conservarla con su
procedencia antes de autorizar una ejecución que necesite esa ruta. Al reanudar,
comprobar los procesos y ledgers actuales; no asumir que un `running` histórico
continúa vivo ni omitir su consumo.

## Incidente de validación de exclusiones

El primer `ranking-2025` se detuvo en el preflight al intentar tratar como texto
los objetos de `training_exclusion_reasons`. No llegó a crear `fold-2025` ni a
inferir. Se conserva su ledger y la versión exacta del código. La corrección sólo
extrae los códigos de esos objetos y mantiene las tres exclusiones ya fijadas.
El corte 2024, sin esas exclusiones, conserva su fuente ejecutada archivada y sus
resultados; no se vuelve a calcular por ese ajuste de validación.

## Incidente de paridad meteorológica

El primer `evaluate-2025` detectó requisitos B/C distintos y se detuvo antes de
cerrar una fila. Sus archivos se conservan en
`fold-2025/evaluation-failed-input-contracts/`, y su ledger mantiene el nombre
original. La corrección determinista y su justificación están en el
[anexo daily-fallback](protocolo-correccion-daily-fallback-2026-10-04.md).
El reintento lleva el nombre de lote `evaluate-2025-retry`; no modifica la evidencia
anterior ni tolera otros desacuerdos de entradas.

La verificación del cierre acepta una fuente Python histórica sólo si sus bytes
exactos están archivados y su hash coincide. Datos, modelos y protocolos conservan
comprobación estricta del archivo original; el archivo de código no se utiliza
para permitir alteraciones de entradas o resultados.
