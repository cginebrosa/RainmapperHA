# Reproducir y auditar el estudio

El código experimental está en [scripts/prediction_research](../../../scripts/prediction_research/).
Los datos detallados están únicamente en `tmp/prediction-research/`, ignorado por
Git. No copiar observaciones, coordenadas, modelos ni trazas privadas al repositorio.
El [protocolo](protocolo-ejecucion-2026-10-03.md) fija las reglas científicas y las
limitaciones; [goal.md](goal.md) fija las autorizaciones y recursos.

## Auditar lo ya ejecutado

- `cohort-v2.json`: hashes de entradas, población, ámbito compartido, grupos y
  pertenencia a cada ventana. `cohort.json` conserva el primer manifiesto.
- `benchmarks/manifest.json`: 22 contratos de entrada y cobertura por especie.
- `geography.jsonl`: contexto de los 128 puntos de desarrollo/externo; privado.
- `fold-AAAA/ranking/`: decisiones del ajuste inicial, predicciones de ranking y
  `quality.json` reconstruido exclusivamente con esa ventana.
- `fold-AAAA/threshold/`: modelos reajustados y predicciones de desarrollo.
- `fold-AAAA/threshold-choice.json`: curva completa, soporte, umbral y razón.
- `fold-AAAA/external/`: modelos reajustados, sello previo que incluye la elección
  B, resumen y predicciones externas. Las filas guardan todos los horizontes,
  abstenciones y trazas de las semanas completas; sólo se etiqueta el día observado.
- `analysis/results.json`: matrices, tasas, intervalos, diagnósticos y elecciones.
  `paired-decisions.jsonl` materializa A/B usando exclusivamente esas elecciones.
- `runs/*.json`: comando exacto, duración, consumo máximo observado y estado de
  cada lote. `*.log` conserva fallos y progreso. Se guardan los intentos fallidos.
- `source-archive/`: versiones anteriores del evaluador conservadas por su hash.

`analyze.py` verifica las entradas y procedencia, la exclusión temporal y las
identidades de los casos; rechaza cambios en el umbral sellado antes del reajuste.
No busca otro umbral con externos. Los ficheros históricos sin hash de cierre se
identifican en el protocolo: su sello al analizar no prueba inmutabilidad anterior.

## Ejecución desde un destino experimental vacío

Los scripts rechazan sobrescribir sus resultados. **No ejecutar esta secuencia
sobre el estudio completado ni borrar sus evidencias para repetirlo.** Requiere
otra copia de trabajo con las mismas entradas privadas disponibles en sus rutas,
el mismo código y entorno, y un destino experimental vacío. Comprobar los hashes;
datos nuevos constituyen otro estudio. No instalar dependencias ni tocar servicios.

Intérpretes utilizados: `.venv/bin/python` para ML y el Python con GDAL existente
`/opt/homebrew/opt/python@3.14/bin/python3.14` para geografía. El supervisor necesita
consultar `ps`; macOS requirió ejecutar ese comando fuera del sandbox. El prefijo
fue autorizado para esta investigación. No cambiar coordinadores del worker.

Preparación, secuencial:

```sh
.venv/bin/python -B scripts/prediction_research/freeze.py --revision v2
.venv/bin/python -B scripts/prediction_research/bounded.py verify-readonly .venv/bin/python -B scripts/prediction_research/verify_readonly.py
.venv/bin/python -B scripts/prediction_research/bounded.py prepare-features .venv/bin/python -B scripts/prediction_research/prepare_features.py
.venv/bin/python -B scripts/prediction_research/bounded.py prepare-windowed .venv/bin/python -B scripts/prediction_research/prepare_windowed.py
.venv/bin/python -B scripts/prediction_research/bounded.py prepare-geography /opt/homebrew/opt/python@3.14/bin/python3.14 -B scripts/prediction_research/prepare_geography.py
.venv/bin/python -B scripts/prediction_research/bounded.py compact-inputs .venv/bin/python -B scripts/prediction_research/compact_inputs.py
```

Para cada año `2024`, `2025`, `2026`, sustituir literalmente `AAAA` en los cinco
comandos siguientes. Terminar un lote y comprobar su estado antes de iniciar otro:

```sh
.venv/bin/python -B scripts/prediction_research/bounded.py ranking-AAAA .venv/bin/python -B scripts/prediction_research/train_fold.py --fold AAAA --phase ranking
.venv/bin/python -B scripts/prediction_research/bounded.py threshold-fit-AAAA .venv/bin/python -B scripts/prediction_research/train_fold.py --fold AAAA --phase threshold
.venv/bin/python -B scripts/prediction_research/bounded.py threshold-evaluate-AAAA .venv/bin/python -B scripts/prediction_research/evaluate_fold.py --fold AAAA --phase threshold
.venv/bin/python -B scripts/prediction_research/bounded.py external-fit-AAAA .venv/bin/python -B scripts/prediction_research/train_fold.py --fold AAAA --phase external
.venv/bin/python -B scripts/prediction_research/bounded.py external-evaluate-AAAA .venv/bin/python -B scripts/prediction_research/evaluate_fold.py --fold AAAA --phase external
```

Sólo después de los tres cortes:

```sh
.venv/bin/python -B scripts/prediction_research/bounded.py analyze .venv/bin/python -B scripts/prediction_research/analyze.py
.venv/bin/python -B scripts/prediction_research/render_tables.py
```

El supervisor conserva un único cálculo, 8 GiB RSS por proceso, 2 GiB de salidas,
45 minutos por lote y 120 acumulados, con un hilo de cálculo. Muestrea memoria
cada 0,5 s; el máximo observado no es una garantía sobre picos entre muestras.
El lote inicial histórico usó 4 GiB y se interrumpió: esta secuencia usa los
scripts corregidos y no reproduce deliberadamente ese fallo ni sus leases.

## Verificación dirigida

```sh
.venv/bin/python -B -m unittest discover -s tests -p test_prediction_research_protocol.py
git diff --check
```

Las pruebas sintéticas comprueban agrupación entre especies, purgas, separación
previa a preprocesar, variables 30/60/90 frente al original de 365 días, protección
de destinos, regla B, peso por observación y denominadores no estimables. No
demuestran precisión de campo ni sustituyen las evaluaciones externas.
