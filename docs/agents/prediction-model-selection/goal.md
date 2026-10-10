# Encargo del agente de selección de modelos

## Estado y alcance de este documento

El usuario autorizó lanzar esta investigación. Comparación y análisis completados
el 04/10/2026; protocolo cerrado ese día antes de inferir. El cierre técnico se
acredita en `tmp/prediction-model-selection/closure.json` y el cierre del goal
nativo, en el registro de la sesión. [Resultado](resultados-2026-10-04.md): mantener
la referencia por ahora, conservando las señales de caesarea como hipótesis.
El estado efectivo se mantiene en [estado.md](estado.md) y los criterios exactos
están en [protocolo-ejecucion-2026-10-04.md](protocolo-ejecucion-2026-10-04.md).

## Objetivo de la ejecución

> Investigar localmente la construcción del ranking y la selección del modelo
> ganador del mapa para Boletus aereus y Amanita caesarea. Verificar soporte,
> estabilidad, filtros y coste de la selección semanal. Cerrar antes de calcular
> una comparación acotada entre la referencia actual, evidencia de ranking
> acumulada mediante predicciones temporales fuera de ajuste y una variante de
> selección diaria con esa misma evidencia. Entregar comparación pareada de
> falsos favorables, oportunidades perdidas, cobertura, estabilidad e incertidumbre,
> distinguiendo exploración retrospectiva de confirmación independiente. Concluir
> si existe una candidata provisional, conviene mantener la referencia o falta
> evidencia. Conservar originales, estudio anterior, modelos activos, HA y worker.

No se exige encontrar ni desplegar una mejora. Un diagnóstico reproducible de
insuficiencia es un resultado válido; una documentación preparada no equivale
a haber completado la comparación.

## Reglas científicas

1. Mantener etiquetas y población acordadas. `normal` es favorable también si su
   origen es GBIF; no reabrir esa decisión ni crear negativos a partir de ausencias
   de registro. No interpretar el IFF como precisión garantizada.
2. Separar entrenamiento, preprocesamiento, tuning, calibración, evidencia del
   ranking y selección de reglas de sus casos de evaluación. El reajuste final
   con todos los datos permitidos no permite evaluar con esos mismos datos.
3. Conservar episodios entre especies y horizontes del mismo registro en el mismo
   ámbito temporal. Las predicciones del modelo compartido deben excluir también
   los registros relacionados de otras especies.
4. Los externos del primer estudio ya han influido en este diseño: identificarlos
   como evidencia reutilizada. No declararlos intactos por cambiar fechas o nombres.
5. Comparar como máximo A, B y C según [metodo.md](metodo.md). B−A mide añadir evidencia histórica anterior, incluida su distinta edad y
   tamaño de ajuste; C−B, la decisión diaria. No presentar C−A como un único
   cambio. No hacer una búsqueda ilimitada de familias, umbrales o combinaciones.
6. Mantener iguales los umbrales de consejo, etiquetas, filtros territoriales,
   temporada, suspensiones, aplicabilidad y política de recomendación. Revalidar
   su configuración al comenzar; no asumir que el snapshot anterior sigue vigente.
7. No elegir el modelo que más acierta en el propio caso reservado ni el que da
   mayor probabilidad favorable. La elección debe utilizar sólo información
   disponible antes del resultado observado.
8. No contar repeticiones, modelos u horizontes como observaciones nuevas. Cada
   registro aporta peso total 1 al promedio de horizontes. Abstenerse o fallar
   técnicamente no cuenta como acierto.
9. Registrar criterios, mínimos de utilidad y soporte, fechas y fórmulas antes
   de obtener las comparaciones. Los supuestos técnicos del agente no se atribuyen
   como preferencias numéricas del usuario. Mostrar el intercambio entre errores.

## Recursos y protección

Conservar como techo la autorización previa de **8 GiB RSS por proceso** y un único
cálculo experimental con un hilo. No reservar esa memoria ni asumir que continúa
disponible sin medirlo cuando se prepare el cálculo.

La preparación del presupuesto debe leer los ledgers anteriores: crear otra carpeta
no reinicia automáticamente los límites acordados de 2 GiB de salidas y 120 minutos
de lotes, con un máximo de 45 minutos por lote. Contabilizar ambos estudios y fijar
el saldo disponible antes de ejecutar; no aumentar límites silenciosamente.
Vigilar memoria por muestreo, tiempo, espacio y descendientes; conservar fallos.

Destinos utilizados, separados del estudio anterior:

- Documentación: `docs/agents/prediction-model-selection/`.
- Código experimental: `scripts/prediction_model_selection/`.
- Evidencia privada nueva: `tmp/prediction-model-selection/`, tras comprobar que
  está ignorada por Git. Reutilizar mediante referencias y hashes; no duplicar
  geografía, modelos o entradas completas sin necesidad medida.

No modificar `scripts/prediction_research/` ni sus resultados cerrados para adaptar
el nuevo experimento. Archivar la versión exacta de cada script antes de ejecutar,
sellar entradas, decisiones, contexto geográfico y predicciones al terminar.

Conservar datos originales y fuentes privadas. Consultar únicamente los campos
necesarios; no abrir fotos ni datos personales ajenos al estudio. Mantener lectores
en lectura y sin leases operativos. No instalar dependencias, cambiar código
operativo, reconstruir contenedores, lanzar trabajos del coordinador, acceder a
HA real, promover modelos, desplegar, limpiar ni cambiar el coordinador del worker.

## Entregables para completar la ejecución

1. Inventario revalidado, diagnóstico del selector y procedencia de cada evidencia.
2. Protocolo numérico fechado y sellado: particiones, candidatos, criterios,
   presupuesto y límites de independencia.
3. Arnés reproducible y comprobaciones de exclusión, cobertura de candidatos,
   reutilización válida, causalidad temporal y contabilidad de errores.
4. Tablas por especie/corte/horizonte y contrastes B−A y C−B, con abstenciones,
   incertidumbre por episodios, estabilidad de ganadores y costes de cálculo.
5. Informe que distinga candidata exploratoria, evidencia insuficiente y eventual
   confirmación independiente; propuesta prospectiva si sigue haciendo falta.

Una modificación operativa o seguimiento prospectivo será un encargo separado.
Informar del progreso brevemente aproximadamente cada minuto mientras se trabaja.
