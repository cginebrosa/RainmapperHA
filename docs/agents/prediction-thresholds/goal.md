# Goal completado: umbral de recomendación favorable

## Autorización y alcance

El 03/10/2026 el usuario pidió documentar este encargo y lanzar el agente con este
goal y sus reglas. Esta instrucción autoriza preparar código de investigación,
verificarlo y ejecutar los experimentos locales acotados descritos aquí. Sustituye
la restricción previa de limitarse a explicar/documentar, sólo para este estudio.
No autoriza trabajos operativos, despliegues, cambios del worker ni escrituras en
HA real. El agente principal de esta conversación mantiene el goal; puede delegar
una auditoría acotada de código y método, conservando una única ejecución de cálculo.

## Objetivo del estudio completado

> Completar una investigación local reproducible para Boletus aereus y Amanita
> caesarea siguiendo docs/agents/prediction-thresholds/goal.md y metodo.md. Comprobar la cohorte
> utilizable, fijar particiones temporales por episodios y comparar el procedimiento
> actual con una variante de recomendaciones más conservadoras mediante modelos,
> ranking y ajustes experimentales independientes de sus casos de prueba. Entregar
> evidencia reproducible por especie sobre falsos favorables, oportunidades
> favorables perdidas, cobertura e incertidumbre. Concluir qué cambios están
> respaldados, cuáles son provisionales o qué evidencia falta, dentro de los límites
> definidos, conservando datos originales, modelos activos, HA real y configuración
> del worker. La insuficiencia de evidencia documentada es una conclusión válida;
> no se exige encontrar ni desplegar una mejora.

La activación se registra en [estado.md](estado.md). Un goal pertenece a esta
conversación y mantiene el trabajo entre turnos; no instala un servicio adicional.
Referencia funcional: [OpenAI Docs — Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex).

## Reglas científicas

- Preferencia del usuario: penalizar más un falso favorable que el error contrario,
  conservando utilidad. No aceptar «siempre desfavorable» o «siempre abstenerse»
  como mejora. El usuario no ha fijado una proporción numérica entre costes.
- Los registros `normal`, incluidos los GBIF, son favorables con el mismo criterio.
  No excluirlos, penalizarlos ni reabrir su clasificación por su procedencia.
- El entrenamiento productivo del 28/09/2026 es la referencia esperada. Su antiguo
  30 % de evaluación no es independiente del ajuste final. No relanzarlo para
  actualizarlo como requisito de este estudio.
- Reutilizar el histórico mediante nuevos ajustes experimentales. Separar todo el
  procedimiento: preprocesamiento, modelo, catálogo/ranking, calibración y umbral.
  No usar artefactos que hayan aprendido de los casos externos reservados.
- Mantener juntos episodios relacionados y horizontes de una observación. Evitar
  contaminación entre especies para los modelos compartidos. Los grupos técnicos
  de 14 días no garantizan por sí solos independencia; justificar los cortes.
- Fijar cohortes, cortes, candidatos y criterio de selección antes de mirar el
  rendimiento externo. Ajustar con desarrollo; evaluar la candidata cerrada fuera.
  Repetir particiones no aumenta el número de episodios independientes.
- Distinguir datos meteorológicos disponibles al emitir de reconstrucciones con
  datos observados posteriores. Si no se puede reproducir una predicción histórica
  emitida, etiquetar el ejercicio como retrospectivo y delimitar qué demuestra.
- No inventar negativos, resultados, independencia, cobertura o equivalencia con
  el mapa completo. Una aproximación debe quedar identificada; no sustituir la
  referencia completa por un modelo simplificado sin explicarlo.

## Primera comparación y cierre del diseño

La ejecución inicial sólo comprende:

1. **A: referencia.** Procedimiento actual de selección y recomendación, reproducido
   con ajustes internos independientes cuando se evalúe retrospectivamente.
2. **B: umbral conservador.** Mismo selector y filtros, variando el umbral de
   recomendación favorable. Reutilizar sus inferencias; no duplicar entrenamientos
   por cada umbral.

Hasta tres cortes temporales externos si la cohorte lo permite. Para B, explorar
en desarrollo una cuadrícula fija de umbrales `0.60, 0.65, 0.70, 0.75, 0.80, 0.85,
0.90, 0.95`; `0.60` sirve de control, no implica que una recomendación dependa sólo
de ese umbral. Conservar los demás filtros y la política de recomendación auditada.

Antes del primer ajuste, guardar un protocolo de ejecución con cortes exactos,
cohorte, modelos necesarios, regla de elección de B, mínimos de utilidad y soporte,
coste estimado y limitaciones. Los mínimos técnicos que fije el agente son supuestos
del experimento, no preferencias numéricas atribuidas al usuario. Mostrar también
el compromiso entre errores sin imponer una equivalencia de costes no acordada.
No seleccionar a posteriori el mejor umbral en la prueba externa.

Las variantes de ranking, cobertura semanal, selección diaria, conjuntos de modelos
y nuevos contratos de variables quedan fuera de este primer goal. Se podrán
recomendar como trabajo posterior, con evidencia que lo justifique.

## Recursos y protección de datos

Lectura inicial de recursos: `sysctl -n hw.memsize hw.logicalcpu` devolvió
34.359.738.368 bytes de RAM y 10 CPU lógicas; `os.statvfs` del workspace mostró
163.735.502.848 bytes libres. Son medidas de arranque, no reserva exclusiva.

Límites iniciales conservadores elegidos por el agente:

- Un proceso de cálculo experimental a la vez; un hilo de ajuste/BLAS/OpenMP.
- Máximo **8 GiB de RSS por proceso**, autorizado expresamente por el usuario
  el 03/10/2026 tras detenerse la primera preparación al superar el límite inicial
  de 4 GiB. Mantener 2 GiB de archivos experimentales nuevos.
- Máximo 45 minutos por lote y 120 minutos acumulados de cálculo experimental.
- Medir cardinalidad y tamaño antes de materializar datos; incorporar vigilancia
  de memoria, tiempo y espacio antes de lanzar el primer lote. Reducir el alcance
  o informar limitaciones al alcanzar límites; no aumentarlos automáticamente.
- Este presupuesto es de recursos locales. No se ha solicitado ni configurado
  un presupuesto de tokens para el goal.

La vigilancia de RSS se realiza por muestreo cada 0,5 segundos: registra el máximo
observado y detiene el proceso al detectar exceso; no garantiza que nunca exista
un pico breve entre muestras. La ampliación autorizada de memoria no amplía los
demás límites ni permite modificar servicios o trabajos operativos.

Entradas: copia local confirmada en `docker-data/`, `docker-media/rainmapper/`,
registro y código pertinentes. Leer originales; no modificarlos ni duplicar
geografía o modelos productivos de forma masiva. No abrir fotos ni contenido
personal ajeno a los campos necesarios para el estudio.

Guardar scripts nuevos de investigación bajo `scripts/prediction_research/`,
comprobaciones dirigidas bajo `tests/` sólo cuando validen propiedades importantes,
y documentación agregada en esta carpeta. Antes de crear datos privados, verificar
que el destino `tmp/prediction-research/` está ignorado por Git. Sus manifiestos,
filas por caso, modelos y diagnósticos privados no se añaden al repositorio.

No modificar código operativo para facilitar el experimento. No instalar
dependencias, construir/recrear contenedores, acceder a HA real, lanzar jobs del
coordinador, promover artefactos, limpiar archivos ni cambiar configuración del
worker. Usar el entorno Python local disponible y scripts aislados del estudio.

## Entregables y criterio de terminación

1. Manifiesto de entradas/cohorte y diagnóstico de cobertura utilizable.
2. Protocolo cerrado de particiones, candidatos, métricas y presupuesto.
3. Scripts y configuración reproducibles, con verificaciones de separación y
   contabilización de errores; registro de ejecuciones y recursos consumidos.
4. Resultados por especie y horizonte: matriz completa, falsos favorables,
   oportunidades detectadas/perdidas, abstenciones, cobertura, soporte y
   estimación de incertidumbre adecuada a los episodios.
5. Informe final que distinga referencia preferible, mejora respaldada, candidata
   provisional o insuficiencia de evidencia, con limitaciones y siguiente paso.

No marcar el goal completado por haber redactado este archivo o iniciado un
proceso. Comprobar los entregables contra archivos y salidas reales. Si una parte
no es viable, documentar causa, evidencia y qué resultados parciales sí son válidos;
no llamar comparación completada a una reproducción incompleta del selector.

Mantener [estado.md](estado.md) con hechos, siguiente acción y enlaces, y emitir
progreso breve aproximadamente cada minuto durante el trabajo. Una dificultad no
autoriza cambiar de objetivo ni dar por terminado el estudio. Respetar las pausas
o correcciones explícitas del usuario y no confundir presupuesto agotado con éxito.
