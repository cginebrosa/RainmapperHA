# D: efecto completo del procedimiento nativo y sus entradas

Registrado después de la parada del primer caso de2025, antes de guardar una
emisión completa de ese corte y sin modificar el coste, los mínimos ni el ranking.
El intento fallido y sus contratos se conservan íntegros.

## Hallazgo y alcance causal

Los catálogos sellados muestran, sin consultar resultados externos, que B de
aereus2025 y2026 cae en `daily_fallback`; D sí encuentra una familia semanal.
Las demás combinaciones de especie/corte conservan selección semanal enB yD.
La preparación meteorológica nativa depende del lote de candidatos: el primer
caso de2025 prepara paraB/C365días con física, mientras que D solicitaV3/core
con90días sin física. Dos peticiones de la misma familia/día quedan afectadas.

Esto no procede de cambiar el snapshot, el código o el contrato temporal: surge
de que el ranking ampliado cambia la ruta y la familia seleccionada por el
procedimiento semanal existente. Por tanto el contraste mide el **efecto total
de ampliar el histórico dentro del procedimiento nativo**, incluyendo ese cambio
de ruta y preparación; no aislará el efecto del ranking manteniendo fijas todas
las matrices meteorológicas de cada candidato.

Forzar365días enD o90enB crearía procedimientos nuevos ajenos a A/B/C/D. Se
conservan las peticiones nativas y se registra esta limitación, en vez de fabricar
una paridad mediante entradas distintas de las que produciría cada procedimiento.
No se cambia la selección semanal ni se añade una alternativa elegida tras
observar sus aciertos. Ningún código productivo cambia.

## Control concreto

- B/C mantiene igualdad estricta de requisitos para cada petición compartida.
- B/D mantiene ese control estricto cuando ambos planes sellados son semanales.
- Únicamente si el planB sellado es `daily_fallback` y el planD sellado es semanal,
  las diferencias nativas quedan marcadas como `native_route_effect`, con número
  de peticiones afectadas y requisitos completos. La rama se decide por catálogos,
  antes de las probabilidades del punto; no depende de etiquetas o utilidad.
- Las peticiones siguen observadas directamente desde `_weather_requirements`
  y `compare_prepared`, sin cambiar su retorno. Se conserva corte anterior a la
  emisión, snapshot común, identidad de artefactos y ausencia de datos futuros.
- Cualquier discrepancia fuera de ese caso detiene el lote. No se convierte una
  discrepancia inesperada en una abstención ni se elimina una observación.

El corte2024 ya completado no entra en esta rama y se conserva sin repetirlo.
El reintento2025 usa carpeta nueva;2026 se ejecutará una sola vez si no hay otro
fallo. Los contadores de tiempo/salidas incluyen los intentos anteriores.

El informe separará aereus2025/2026, afectados por este cambio de ruta, de
caesarea y2024. Una diferencia de utilidad no demostrará que más años sean
mejores por sí mismos: demuestra, como máximo, una señal exploratoria del
procedimiento completo evaluado. Sigue sin autorizar promoción ni despliegue.
