# Especificación Biology V6 — retardos suaves y pooling parcial

Estado: **CONTRATO IMPLEMENTADO Y TÉCNICAMENTE PROMOCIONABLE POR ELECCIÓN MANUAL**.
Fecha original: 2026-08-16. Corrección de contrato: 2026-08-17.

Contratos corregidos: `fixed_gap_7d_biology_v6_smooth_hierarchical_v2` y
`lag_event_biology_v6_smooth_hierarchical_v2`. Los identificadores v1 quedan
reservados para la ejecución histórica sobre cinco canales y no son
compatibles con esta matriz.

Actualización 2026-08-19: el perfil canónico completo puede producir una
candidata operativa con los miembros `species`, `shared` y `partial_pooling`.
La activación sigue siendo manual y no implica que V6 sea científicamente
superior; cada miembro solo aporta el score de una celda si mejora la
prevalencia fuera de muestra y obtiene el menor Brier validado.

## Pregunta

Comprobar si la meteorología diaria raw contiene señal generalizable cuando se
reduce la libertad día-a-día de V5 y se comparte información entre especies,
sin imponer ventanas estacionales fijas.

## Entradas e invariantes

- Snapshot canónico inmutable:
  `docker-data/audits/mushroom-ml-snapshot-20260816`.
- Matrices V5 raw365 locales del directorio
  `docker-data/audits/mushroom-ml-v5-raw-discovery-20260816`.
- Matriz canónica V5 completa: cinco canales primarios IDW, ET0, balance
  climático y SMI diario, más los resúmenes físicos escalares registrados.
- Los perfiles sin calendario, sin derivados o sin SMI son ablaciones; no
  definen el runtime canónico V6.
- Se conservan observaciones, targets, cortes causales y grupos 7/14.
- En lag existe un ajuste conjunto por contrato+estimador+split; 1/2/3/7
  filtran el mismo hold-out y nunca reentrenan.
- No se escribe modelo, candidato operativo, HA, worker, GHCR o release.

## Representación temporal suave

Cada uno de los ocho canales diarios conserva sus 365 días. El eje
`lag_000..lag_364` se transforma de
forma determinista a `log1p(lag)` y se representa mediante diez bases B-spline
cúbicas. Los pesos de cada base se normalizan y producen diez exposiciones
suaves por canal: 80 exposiciones temporales en total. Los resúmenes físicos
SMI de corte se añaden como escalares estandarizados dentro de train y no se
proyectan sobre bases temporales.

La escala logarítmica concede resolución a días recientes y mantiene capacidad
para representar señal lenta, sin fijar límites entre micelio y fructificación.
La imputación diaria se aprende exclusivamente en train antes de proyectar las
bases. Se evalúa además una base lineal uniforme como ablación de suavidad.

## Estimadores

1. `smooth_species_logistic_v1`: logística regularizada independiente por
   especie sobre las 80 exposiciones y los estados escalares. Controla si la
   compresión temporal basta.
2. `smooth_shared_logistic_v1`: un único modelo con coeficientes meteorológicos
   compartidos y un intercepto por especie.
3. `smooth_partial_pooling_logistic_v1`: coeficientes compartidos más
   desviaciones especie×variable, escaladas para recibir una penalización mayor.
   Es pooling parcial determinista, no un modelo bayesiano completo.

Los hiperparámetros (`C` y fuerza relativa de las desviaciones) se eligen por
Brier en folds cronológicos internos y nunca consultan el hold-out.

## Evaluación

- Hold-outs cronológicos emparejados de grupos 7 y 14 para fixed y lag.
- Sensibilidad de campañas `area_id+target_year` completas.
- Brier, log-loss, calibración, AUC y matrices por especie; nunca Brier medio
  entre especies.
- Comparación contra prevalencia, fenología y el mejor miembro individual
  V2/V3/V4/V5 en las mismas filas.
- Errores compartidos por especie, horizonte y fase.

V6 solo merece otro paso si mejora de forma repetida por especie, mantiene la
mejora por campaña y supera tanto al estimador suave por especie como al mejor
miembro anterior. Ningún resultado autoriza automáticamente una publicación.
