# Plan de trabajo de la investigación

**Primera comparación del goal completada el 03/10/2026.** Ver
[resultado](resultados-2026-10-03.md), [tablas](tablas-2026-10-03.md) y
[reproducción](reproducibilidad.md). Este plan conserva la lista amplia de diseño;
sus casillas originales no son el registro actual de ejecución. El alcance cerrado
fue A frente a B, sin otras variantes de ranking ni seguimiento prospectivo.

El [informe del 03/10/2026](inventario-inicial-2026-10-03.md) recoge lo comprobado
tras la descarga del usuario y las limitaciones del inventario inicial. El
[objetivo](README.md), el
[método](metodo.md) y las [reglas de ejecución autorizadas](goal.md) forman parte
del encargo. Consultar [estado.md](estado.md) para el avance; la primera comparación
autorizada se limita a referencia y umbral conservador.

## Fases y entregables propuestos

### 0. Preparación por el usuario y definición de ejecución

- [x] El usuario confirma la descarga de observaciones, setales y meteorología a
  local; se comprueban archivos y montajes en lectura. La ejecución de experimentos
  locales acotados está autorizada mediante el goal; falta cerrar el diseño concreto.
- [ ] Confirmar qué datos se han incorporado y qué recursos locales se pueden
  emplear, sin consultar HA real para completar huecos por iniciativa propia.
- [ ] Fijar dónde guardar evidencia privada y artefactos experimentales, límites
  de CPU, memoria, disco, duración y número de variantes. Medir primero tamaños
  y cardinalidades; no asignar recursos por suposición.
- [ ] Revalidar sólo código, configuración y contratos necesarios para el estudio.
  No repetir comprobaciones cerradas de release, geografía, WhatsApp o disco.

**Salida:** alcance de ejecución, presupuesto y procedencia de las entradas.
Esta fase no requiere cambiar el coordinador del worker ni activar artefactos.

### 1. Inventario y viabilidad

- [ ] Preparar un manifiesto reproducible de entradas, versiones y huellas sin
  añadir archivos privados a Git ni hacer copias masivas innecesarias.
- [ ] Comprobar etiquetas efectivas, negativos explícitos, duplicados, episodios,
  horizontes y disponibilidad temporal de variables y meteorología.
- [ ] Auditar pertenencia a entrenamiento y a decisiones de ajuste/selección;
  registrar procedencia desconocida en lugar de inferir independencia.
- [ ] Separar el histórico reutilizable mediante modelos experimentales nuevos
  de los casos independientes del modelo instalado y de su selección. Contar
  episodios positivos y negativos en ambas vías; no confundir el antiguo 30 %
  de evaluación con una reserva frente al ajuste productivo final.
- [ ] Presentar soporte independiente por especie y carencias que impidan medir
  falsos favorables o generalización.

**Salida:** inventario y dictamen de viabilidad. Si faltan negativos o independencia,
determinar si nuevos ajustes permiten una comparación retrospectiva útil, si sólo
cabe un análisis descriptivo o si hace falta recogida prospectiva. No prometer una
comparación concluyente ni fabricar negativos.

### 2. Auditoría descriptiva del selector actual

- [ ] Reproducir decisiones en una cohorte acotada de puntos/fechas pertinentes.
- [ ] Registrar ranking, cobertura semanal, filtros, alternativas calculadas,
  modelo ganador, IFF/salida numérica y recomendación final con sus motivos.
- [ ] Separar casos usados, no usados y de pertenencia desconocida en entrenamiento.
- [ ] Medir frecuencia de familias ganadoras por especie y los motivos de cambio.

**Salida:** explicación trazable de «parece elegir siempre el mismo modelo».
No presentar este análisis como rendimiento predictivo independiente.

### 3. Cierre del diseño experimental

- [ ] Definir casos, episodios, cortes temporales y separación de setales según
  las preguntas que los datos permitan responder.
- [ ] Reservar la prueba final y sellar su manifiesto. Mantenerla fuera del ajuste
  de modelos, catálogo, umbrales y reglas. Si no hay una reserva adecuada, declarar
  el alcance exploratorio y dejar la confirmación pendiente de nuevos datos.
- [ ] Documentar qué decisiones de diseño ya estuvieron influidas por el histórico;
  repartirlo de nuevo no elimina ese conocimiento previo.
- [ ] Fijar matriz inicial, límites de búsqueda, métricas, controles simples y
  tratamiento de abstenciones/fallos según el método.
- [ ] Presentar al usuario el equilibrio de costes en ejemplos de salidas y fijar
  mínimos de utilidad, soporte y mejora práctica antes de abrir la prueba final.
- [ ] Determinar si bastan inferencias existentes independientes o si hacen falta
  ajustes experimentales desde cero. Para la comparación retrospectiva, reconstruir
  dentro de cada partición modelos, ranking y demás ajustes, incluida la referencia;
  no reutilizar selecciones que hayan visto los resultados reservados.

**Salida:** protocolo cerrado y manifiesto de particiones. Reutilizar componentes
existentes sólo tras verificar que cumplen la separación requerida.

### 4. Experimentos locales en desarrollo

- [ ] Ejecutar la referencia y variantes acotadas, con igual población y entradas.
- [ ] Para nuevos ajustes retrospectivos, conservar artefactos experimentales
  separados de los activos y verificar la exclusión de los episodios de prueba
  de todos los ajustes y decisiones de selección correspondientes.
- [ ] Reutilizar predicciones compatibles; evitar repetir ajustes o materializar
  estructuras por toda la geografía para comparar unas pocas reglas.
- [ ] Registrar configuración, artefactos, semillas, consumo y causas de fallo.
- [ ] Comparar riesgo favorable, oportunidades detectadas, cobertura, calibración
  y soporte, con incertidumbre y desglose por especie/horizonte.
- [ ] Elegir una candidata o mantener la referencia; cerrar su configuración.

**Salida:** tabla pareada de desarrollo y justificación de la candidata. Si se
necesita ampliar experimentos fuera del alcance acordado, describir primero la
necesidad; no convertir el encargo en una búsqueda ilimitada.

### 5. Prueba independiente, si es viable, y conclusión

- [ ] Si existe una prueba final adecuada, evaluar una vez la candidata cerrada
  y la referencia. Si no existe, informar la limitación sin fabricar validación.
- [ ] Aplicar los criterios prefijados, informar diferencias e incertidumbre y
  conservar todos los casos, también abstenciones y fallos técnicos.
- [ ] Revisar ejemplos de errores con sus causas como hipótesis, sin ajustar la
  candidata a posteriori sobre esa prueba.
- [ ] Concluir según el soporte: cambio respaldado, referencia preferible,
  candidata provisional pendiente de confirmación o evidencia insuficiente.

**Salida:** informe final con límites, recomendación y, cuando proceda, propuesta
concreta de implementación. Una candidata exploratoria no equivale a una mejora
operativa acreditada. Nada se instala o promociona por obtener una métrica mejor.
La revisión e implementación serían un encargo posterior separado.

### 6. Seguimiento prospectivo propuesto

- [ ] Acordar periodo o condición de cierre antes de empezar; no detenerse justo
  cuando los resultados favorezcan una opción.
- [ ] Guardar predicciones fechadas antes de las salidas, manteniendo reglas y
  versiones identificables; registrar resultados positivos y negativos explícitos.
- [ ] Comparar con la misma definición y métricas, describiendo el sesgo de las
  visitas realizadas. Una salida no realizada nunca es un negativo.

**Salida:** evidencia futura bajo condiciones reales de uso. Su ejecución también
queda pendiente; no se programa ninguna automatización al guardar este plan.

## Función del agente autorizado

El agente organiza el protocolo y ejecuta herramientas reproducibles dentro
del alcance autorizado: comprobar entradas, preparar particiones, lanzar la matriz
acotada, revisar fugas de información y producir informes con fuentes. Los cálculos
y decisiones estadísticas deben quedar en código/configuración reproducibles; el
texto del agente no sustituye evidencia ni asigna etiquetas por intuición.

Cada ejecución tendrá un identificador y un manifiesto que vincule datos, código,
configuración, particiones y resultados. Guardará un registro de variantes
descartadas y errores, para que el informe no seleccione sólo resultados favorables.
El diagnóstico detallado se conservará fuera del contrato operativo del mapa.

El agente no podrá cambiar la definición del objetivo tras ver resultados,
consultar repetidamente la prueba final para afinar, alterar datos originales,
crear nuevas dependencias operativas, promover artefactos ni decidir despliegues.
Tampoco podrá cambiar el destino del worker. Cualquier uso futuro del worker exige
un alcance específico y conservar su configuración; este plan no lo autoriza.

## Evidencia que deberá dejar

Los siguientes son entregables futuros, no archivos ya producidos:

- Inventario y evaluación de calidad/suficiencia de los datos.
- Protocolo cerrado, manifiestos de entradas y particiones, configuración y
  registro de ejecuciones con recursos consumidos.
- Evidencia privada por caso para reproducir selección, recomendación y resultado.
- Tablas agregadas por especie/horizonte, frecuencia de ganadores y motivos,
  matrices de errores y gráficos de riesgo frente a utilidad/cobertura.
- Informe de comparación con incertidumbre, límites de generalización, decisión
  recomendada y necesidades de seguimiento prospectivo.

## Cuándo detenerse o reducir el alcance

Detener la comparación concluyente si no se puede acreditar independencia,
las etiquetas son incompatibles, faltan negativos/episodios suficientes o no se
puede reconstruir qué información existía al emitir la predicción. Explicar qué
análisis descriptivo sigue siendo válido y qué evidencia falta.

Detener una ejecución ante incumplimiento del presupuesto, riesgo para originales,
necesidad de modificar HA real/worker o ampliación no autorizada. Conservar el
diagnóstico; no elevar límites ni relanzar trabajos costosos automáticamente.

La investigación termina con un informe reproducible y una conclusión honesta.
No exige encontrar un modelo nuevo, cambiar de ganador ni desplegar una mejora.
