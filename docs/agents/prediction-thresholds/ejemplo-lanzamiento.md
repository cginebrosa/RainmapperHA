# Ejemplo de lanzamiento del agente de umbrales

Mensaje basado en el encargo ejecutado, con las rutas actuales de la carpeta.
El estudio terminó el 03/10/2026; la comprobación inicial evita repetirlo al copiar
este ejemplo. Guardar el archivo no lanza cálculos ni reactiva el goal.

```text
Prepara el lanzamiento o continuación del agente de investigación de
docs/agents/prediction-thresholds/ en el proyecto RainmapperHA.

Lee primero docs/codex-start-here.md y docs/active-context.md.
Después lee README.md, goal.md, metodo.md, plan-de-trabajo.md,
protocolo-ejecucion-2026-10-03.md y estado.md de esa carpeta.

Comprueba el estado y las evidencias existentes antes de crear un goal.
Si el estudio ya está completado, presenta su resultado y los enlaces,
sin repetir entrenamientos ni inferencias. Si quedan fases pendientes,
crea o continúa el goal persistente descrito en goal.md y complétalas.

El objetivo es comparar, para Boletus aereus y Amanita caesarea,
el procedimiento actual con una variante de umbral favorable más
conservador, manteniendo el mismo selector y los demás filtros.
No amplíes esta comparación a variantes de ranking o selección diaria.

Autorizo los scripts y experimentos locales pendientes dentro de los
límites documentados. Reutiliza las entradas y resultados válidos;
conserva los artefactos cerrados y contabiliza los recursos ya consumidos.
Mantén como techo 8 GiB RSS por proceso, un cálculo y un hilo a la vez,
2 GiB de salidas, 45 minutos por lote y 120 minutos acumulados.

Respeta las particiones y el protocolo fijados. Excluye los casos de
prueba del ajuste, ranking y elección del umbral. Los registros normal,
incluidos GBIF, son favorables. No inventes negativos ni independencia.
Penaliza los falsos favorables conservando utilidad; no aceptes siempre
desfavorable o siempre abstenerse como mejora.

Entrega resultados por especie y horizonte: falsos favorables,
oportunidades perdidas, abstenciones, cobertura e incertidumbre por
episodios. La insuficiencia de evidencia es una conclusión válida.
Actualiza estado.md y enlaza el informe con sus evidencias reproducibles.

Conserva fuentes, datos privados y modelos activos. No modifiques
HA real, el worker ni su coordinador. No lances trabajos operativos,
despliegues, limpiezas ni promociones de modelos.
Informa brevemente del progreso aproximadamente cada minuto.
```

Instrucciones completas: [goal.md](goal.md) y
[protocolo de ejecución](protocolo-ejecucion-2026-10-03.md).
Resultado del encargo ya ejecutado: [informe final](resultados-2026-10-03.md).
