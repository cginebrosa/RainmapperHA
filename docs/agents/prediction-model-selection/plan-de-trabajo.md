# Secuencia de trabajo

Plan ejecutado. [Estado de cierre](estado.md) y [resultado](resultados-2026-10-04.md).
Se conserva la secuencia como referencia; no autoriza repetir los cálculos.

## Preparación documental de este encargo

- Separar el estudio terminado en `prediction-thresholds/`, actualizando enlaces.
- Preparar README, objetivo, método, plan y estado del segundo estudio.
- Encargar la revisión del planteamiento a `prediction_model_selection`, en lectura.
- Verificar enlaces y diff. No repetir pruebas operativas por esta reorganización.

## Ejecución experimental

1. **Inventario y auditoría en lectura.** Revalidar código/configuración, soporte
   por modelo/especie/horizonte, particiones disponibles y contratos de cachés.
   Salida: diagnóstico y mapa de evidencias reutilizables, nuevas o contaminadas
   para confirmación por haber orientado ya el diseño.
2. **Viabilidad y protocolo cerrado.** Fijar cortes, ventanas internas temporales,
   purgas, A/B/C, fórmulas y mínimos de utilidad. Medir panel de candidatos, coste
   y presupuesto restante contando el primer estudio. Salida: protocolo sellado
   antes del primer cálculo de comparación; declarar si sólo cabe exploración.
3. **Arnés aislado y comprobaciones.** Archivar fuentes exactas; verificar exclusión
   entre ajuste/ranking/prueba, grupos entre especies, deduplicación y completitud
   del panel. Comprobar identidad de variantes donde deberían coincidir y que
   elegir por día no consulta resultados observados. Salida: código verificable
   y preflight; ninguna modificación de la operación.
4. **Comparación acotada.** Ejecutar una fase a la vez. Reutilizar ajustes válidos,
   completar sólo inferencias necesarias y conservar casos sin recomendación.
   Salida: artefactos privados y ledger con recursos, errores y hashes de cierre.
5. **Análisis y auditoría.** Informar B−A y C−B por especie/horizonte, incertidumbre,
   estabilidad, cobertura y coste. Explicar cambios de población/entrenamiento si
   los hubo. Salida: tablas agregadas y revisión de fugas y conclusiones.
6. **Cierre.** Concluir referencia preferible, candidata provisional o evidencia
   insuficiente; especificar qué confirmación falta. No promover ninguna variante.

El cierre requiere las evidencias de ejecución, no sólo estas instrucciones.
Los controles de viabilidad pueden concluir que no hay datos suficientes para
algún contraste; la limitación debe quedar demostrada y no sustituirse por una
variante oportunista. Estado y autorización efectiva en [estado.md](estado.md).
