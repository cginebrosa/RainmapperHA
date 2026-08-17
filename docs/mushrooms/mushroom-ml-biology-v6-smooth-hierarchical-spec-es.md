# Especificación Biology V6 — retardos suaves y pooling parcial

Estado: **EXPERIMENTO LOCAL NO OPERATIVO**. Fecha: 2026-08-16.

## Pregunta

Comprobar si la meteorología diaria raw contiene señal generalizable cuando se
reduce la libertad día-a-día de V5 y se comparte información entre especies,
sin imponer ventanas estacionales fijas.

## Entradas e invariantes

- Snapshot canónico inmutable:
  `docker-data/audits/mushroom-ml-snapshot-20260816`.
- Matrices V5 raw365 locales del directorio
  `docker-data/audits/mushroom-ml-v5-raw-discovery-20260816`.
- Solo cinco canales primarios IDW comunes; perfil sin calendario para la
  comparación principal. ET0/balance quedan fuera para aislar la hipótesis.
- Se conservan observaciones, targets, cortes causales y grupos 7/14.
- En lag existe un ajuste conjunto por contrato+estimador+split; 1/2/3/7
  filtran el mismo hold-out y nunca reentrenan.
- No se escribe modelo, candidato operativo, HA, worker, GHCR o release.

## Representación temporal suave

Cada canal conserva sus 365 días. El eje `lag_000..lag_364` se transforma de
forma determinista a `log1p(lag)` y se representa mediante diez bases B-spline
cúbicas. Los pesos de cada base se normalizan y producen diez exposiciones
suaves por canal: 50 variables meteorológicas en total.

La escala logarítmica concede resolución a días recientes y mantiene capacidad
para representar señal lenta, sin fijar límites entre micelio y fructificación.
La imputación diaria se aprende exclusivamente en train antes de proyectar las
bases. Se evalúa además una base lineal uniforme como ablación de suavidad.

## Estimadores

1. `smooth_species_logistic_v1`: logística regularizada independiente por
   especie sobre las 50 exposiciones. Controla si la compresión temporal basta.
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
