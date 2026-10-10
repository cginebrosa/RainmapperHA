# Corrección técnica del caso ya diario

Registrada tras el primer preflight de evaluación 2025 y antes del reintento.
No se han consultado métricas comparativas A/B/C ni modificado sus criterios.
Se conserva el intento fallido y su fuente exacta. El protocolo principal y el
primer anexo permanecen intactos.

## Hallazgo verificable sin nuevas inferencias

El catálogo B de aereus2025 no tiene familia semanal común y la ruta nativa cae
en `daily_fallback`: **B ya selecciona por día en ese caso**. En el día 5, su
lote de 12 candidatos preparaba 365 días de meteorología con física; el C inicial
preparó aisladamente V3/core/lag/logistic con 90 días y sin física. La identidad
calculada desde el plan coincide con el hash discrepante del control detenido.

El intento se detuvo antes de guardar una emisión comparativa completa. No es un
resultado favorable o desfavorable de C: evidencia que su arnés inicial alteraba
las entradas además de seleccionar diariamente.

## Regla determinista corregida

Antes de inferir, obtener desde el catálogo B el modo del plan nativo, conservando
hash del catálogo, cadenas originales y plan agregado:

- Si B ya usa `daily_fallback`, C es idéntico por definición al mismo primer
  candidato aplicable por día. Reutilizar una copia de resultado y contratos B,
  con modo `reuse_B_native_daily_fallback_v1`; conservar su preparación nativa.
- Si B tiene selección semanal, C mantiene la selección diaria propia por
  familia, modo `independent_daily_family_v1`, con los controles de entradas
  previamente fijados.

La rama se decide por metadatos de desarrollo, sin consultar etiquetas externas
ni probabilidades del punto. No se sustituye ningún requisito meteorológico ni
se modifica A/B. Distinguir miembros reutilizados de inferencias nuevas al medir
coste. Mantener la parada ante cualquier otra diferencia de entradas; esta
corrección no permite tolerar discrepancias posteriores.

Esto implementa el contraste previsto: C cambia la selección sólo cuando B
realmente impone una familia semanal. No constituye una nueva candidata elegida
por sus resultados ni una mejora operativa comprobada.

## Conservación de 2024

Comprobado sobre sus planes: B tiene familia semanal común en ambas especies y
en sus siete días; no entra en `daily_fallback`. La corrección no modifica la
rama ejecutada allí. Se conservan sus 259 emisiones verificadas con su código
exacto archivado, sin repetirlas ni atribuirles retroactivamente la fuente nueva.

Las pruebas dirigidas deben acreditar la elección de rama antes de inferir, la
equivalencia nativa en fallback, la copia sin alias mutable y la contabilidad
de reutilización. El análisis conserva el límite retrospectivo original.
