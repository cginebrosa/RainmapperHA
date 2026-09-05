# Predictor P0: pruebas pendientes y batería Python de auditoría

Fecha de revisión: 5 de septiembre de 2026.

Este documento separa lo que ya se ha medido de lo que debe esperar a disponer
de observaciones útiles. No propone cambios en V2--V6, no reserva una V7 y no
requiere conservar los precálculos diarios.

## Tres especies aplazadas

La auditoría multiversión ya cubre Rovelló, Edulis, Pinícola, Aereus y Ou de
reig. Se comprobó la evidencia de las otras tres especies operativas sobre el
benchmark actual:

| Especie | Observaciones brutas | Elegibles | Favorables / desfavorables elegibles | Hold-out 14 d | Grupos externos | Decisión |
|---|---:|---:|---:|---:|---:|---|
| Llanega negra | 11 | 11 | 8 / 3 | 4 favorables, 0 desfavorables | 3 | Aplazar |
| Marçot | 39 | 25 | 21 / 4 | 6 favorables, 0 desfavorables | 4 | Aplazar |
| Múrgola negra | 19 | 17 | 4 / 13 | 0 favorables, 5 desfavorables | 3 | Aplazar |

El problema decisivo no es solo el número total. En las tres especies, el
conjunto externo contiene una sola clase. Con esos casos se puede comprobar que
el runner funciona y medir sensibilidad, pero no comparar seriamente acierto,
discriminación o calibración entre variantes. El corte alternativo de 7 días
tiene el mismo problema.

La prueba se repetirá cuando el hold-out externo de cada especie contenga tanto
casos favorables como desfavorables y varios episodios independientes. No se
fija ahora un número mínimo arbitrario: se informarán siempre observaciones,
clases y grupos antes de interpretar el resultado.

## Pruebas que quedan pendientes

1. Repetir la auditoría multiversión para Llanega negra, Marçot y Múrgola negra
   cuando sus grupos externos incluyan ambas clases.
2. Ampliar la evaluación por zona solo en las combinaciones especie/zona que
   tengan ambas clases y varios grupos independientes. Por ahora, Olvan en
   Aereus y Ou de reig son los únicos ejemplos con una base mínimamente
   interpretable; el resto se conserva únicamente como sensibilidad.
3. Reproducir V4 de Ou de reig con exactitud si se recupera el snapshot
   meteorológico completo del entrenamiento. El Brier del tramo elegido
   coincide, pero las probabilidades individuales no quedaron suficientemente
   próximas para usar V4 en una conclusión fuerte.
4. Si se decide modificar KNN, comparar una calibración estrictamente fuera de
   muestra con el KNN actual y con el candidato sustituto V6. La auditoría
   transversal de extremos ya está completada: no respalda eliminar KNN ni
   recortar 0/100 de forma cosmética, pero demuestra que sus unos exactos no son
   certeza.
5. Política de lluvia implementada y validada el 5 de septiembre: una
   desviación de precipitación queda como advertencia y no causa por sí sola
   una abstención. Las demás variables conservan el veto. La comprobación
   directa de Rovelló/La Masella del 8 de septiembre aceptó el candidato V5w
   (`99,8511 %`); los `32,14` mm quedaron trazados como aviso. La alternativa
   `log1p` permanece descartada.
6. Repetir la evaluación hold-out agrupada cada vez que se incorporen suficientes
   observaciones nuevas. Esta es la validación prevista: no hace falta guardar
   cada precálculo diario ni organizar salidas al campo según la predicción.

La interacción explícita entre lluvia antecedente y humedad previa del suelo ya
no figura como pendiente: fue probada el 5 de septiembre y no mejoró de forma
estable a los ganadores actuales. No se reabrirá como candidata operativa sin
nuevos datos independientes.

La redefinición del contador de racha seca tampoco queda pendiente. Tras añadir
las observaciones positivas de Edulis y Rovelló del 5 de septiembre se ejecutó
la comparación controlada entre la definición actual, el umbral diario de 1 mm
y la ausencia de contador. El umbral de 1 mm no mejoró de forma estable y no se
abrió la búsqueda secundaria de eventos de recarga en tres días. Sí queda
pendiente repetir esta comparación cuando se acumulen nuevos grupos externos,
en especial casos negativos.

## Batería Python preparada

### Código común versionado

- `scripts/audit-mushroom-hydric-ablation.py`: runner general de ablaciones
  controladas sobre benchmarks congelados.
- `rainmapper_core/mushroom_ml_hydric_ablation.py`: selección de familias de
  variables, métricas y utilidades comunes de la auditoría.
- `tests/test_mushroom_ml_hydric_ablation.py`: pruebas dirigidas de esas
  utilidades.

### Runners locales y aislados de esta auditoría

Están bajo
`docker-data/audits/mushroom-hydric-ablation-20260905/`. Escriben únicamente
JSON de auditoría bajo ese mismo árbol; no generan modelos operativos,
registros, precálculos ni observaciones.

- `fixed_feature_ablation.py`: ablaciones de los candidatos V2--V4 y de V3
  `core` conservando estimador y hold-out.
- `v5_ablation_audit.py`: ablaciones del ganador V5 de Rovelló, incluida la
  lluvia diaria por bandas de retardo.
- `v6_ablation_audit.py`: ablaciones V6 para ventanas de 30, 60 y 90 días,
  perfiles compartido y parcialmente compartido, y cortes de 7/14 días.
- `v6_hydric_interaction_audit.py`: prueba multiespecie de lluvia por bandas
  multiplicada por el estado del suelo inmediatamente anterior.
- `v5_hydric_interaction_audit.py`: la misma pregunta aplicada al ganador V5 de
  Rovelló, incluida la banda 31--59 días.
- `remaining_species_evidence_audit.py`: recuento reproducible de observaciones,
  clases y grupos externos de las tres especies aplazadas.
- `mushroom-dry-spell-ablation-20260905/run_controlled_dry_spell_audit.py`:
  comparación D0/D1/D2 y ablaciones hídricas sobre el snapshot que incluye las
  dos observaciones del 5 de septiembre. El runner vive bajo `docker-data/audits`
  y no escribe modelos ni precálculos.
- `scripts/audit-mushroom-rain-applicability.py`: reconstruye el soporte sin
  los grupos externos y compara el veto actual, una cola `log1p` y lluvia como
  advertencia sin veto.
- `scripts/audit-mushroom-probability-extremes.py`: mide extremos exactos y
  bandas 1/5/95/99 %, reproduce los contextos operativos y simula la exclusión
  diagnóstica de KNN.

### Resultados principales

Los JSON reproducibles están en el subdirectorio `results/`:

- `v6-controlled-ablation-all.json`;
- `rovello-v5-raw60-ablation.json`;
- `edulis-v3-core-hgb-fixed-ablation.json`;
- `v2-selected-winners-ablation.json`;
- `ou-de-reig-v4-climatic-balance-ablation.json`;
- `v6-hydric-interaction-challenger.json`;
- `rovello-v5-hydric-interaction-challenger.json`;
- `deferred-species-evidence.json`.
- `mushroom-dry-spell-ablation-20260905/results/controlled-dry-spell-ablation.json`.
- `mushroom-rain-applicability-20260905/results/rain-applicability-gates.json`.
- `mushroom-probability-extremes-20260905/results/extreme-probability-calibration.json`.

La interpretación científica y la decisión sobre las versiones actuales están
en
`docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.

`MOD_0001` permanece fuera de discusión en toda esta batería: la ecología sigue
disponible como diagnóstico, pero no veta ni modifica predicciones.
