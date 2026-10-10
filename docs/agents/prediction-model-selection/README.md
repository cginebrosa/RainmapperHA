# Investigación de selección del modelo ganador

**Estado: comparación completada el 04/10/2026.**
[Informe y conclusión](resultados-2026-10-04.md): ninguna alternativa supera todos
los criterios predefinidos. Aereus no mejora; la selección diaria muestra una
señal prometedora para caesarea, todavía exploratoria y variable entre campañas.
Mantener la operación actual no demuestra que sea óptima. Ver [estado](estado.md).

## Pregunta

Para **Boletus aereus** y **Amanita caesarea**, determinar qué procedimiento para
construir el ranking y resolver el ganador del punto ofrece un equilibrio más
útil entre falsos favorables, oportunidades detectadas y cobertura. Examinar
estabilidad por episodios y campañas y suficiencia de la evidencia de selección.
Cambiar de modelo más veces no es un objetivo de calidad por sí mismo.

La preferencia del usuario se mantiene: un favorable erróneo cuesta más que el
error contrario, sin dejar de recomendar oportunidades interesantes. No se ha
acordado una proporción numérica entre costes.

## Qué aporta el estudio anterior

[prediction-thresholds](../prediction-thresholds/README.md) comparó el umbral de
recomendación con el mismo selector. No demostró que el selector actual fuese el
mejor. Su [informe](../prediction-thresholds/resultados-2026-10-03.md) encontró
abstención completa en dos cortes experimentales cuyo ranking tenía sólo seis y
cuatro observaciones. Los filtros exigían mayor soporte. Es evidencia histórica
de ese experimento, no una comprobación del comportamiento presente de HA.

Se compararon una referencia y dos alternativas:

| Procedimiento | Cambio | Contraste que responde |
|---|---|---|
| A. Referencia | Selección actual reconstruida dentro de cada partición. | Punto de partida con todos sus filtros. |
| B. Ranking con evidencia temporal acumulada | Predicciones de varias ventanas anteriores, cada una fuera de su propio ajuste; misma fórmula de ranking y misma resolución semanal. | B−A: efecto de la forma de obtener evidencia para el ranking. |
| C. Selección diaria | Mismos modelos, ranking y filtros que B; elegir por día en vez de imponer una familia semanal. | C−B: efecto de la elección diaria. C−A cambia dos componentes. |

A utiliza el último año de evidencia fuera de ajuste; B añade el anterior;
C usa el catálogo B con elección diaria. Se conservaron el umbral de favorable
y todos los filtros, sin nuevos entrenamientos. El informe distingue las señales
positivas, los fallos por campaña y el veto posterior de una familia semanal
con ROC insuficiente en B caesarea2025. No se modificó la operación.

## Una limitación decisiva

Los resultados de 2024–2026 del primer estudio ya han orientado estas hipótesis.
Reutilizarlos permite explorar una comparación retrospectiva, pero **no constituye
una confirmación nueva e intacta**. Nuevas particiones no borran ese conocimiento.
Una candidata prometedora necesitará evidencia aún no utilizada en su diseño,
preferentemente predicciones registradas antes de nuevas salidas.

## Documentos

- [Resultados](resultados-2026-10-04.md) y [tablas completas](tablas-2026-10-04.md).
- [Goal y reglas del cálculo](goal.md): objetivo, límites y criterio de cierre.
- [Método](metodo.md): contrastes, separación, reutilización y métricas.
- [Plan de trabajo](plan-de-trabajo.md): pasos y entregables.
- [Protocolo numérico](protocolo-ejecucion-2026-10-04.md): ventanas, mínimos, métricas y presupuesto.
- [Control de entradas](protocolo-control-entradas-2026-10-04.md) y
  [corrección del fallback diario](protocolo-correccion-daily-fallback-2026-10-04.md).
- [Inventario](inventario-2026-10-04.md): procedencia y soporte revalidados.
- [Reproducibilidad](reproducibilidad.md): comandos, artefactos y controles.
- [Estado](estado.md): cierre y límites de la conclusión.
- [Ejemplo de lanzamiento](ejemplo-lanzamiento.md): mensaje listo para copiar en Codex.

El usuario autorizó posteriormente lanzar el nuevo agente. La comparación sigue
siendo exploratoria y no autoriza cambios operativos.
