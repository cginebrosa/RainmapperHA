# Protocolo cerrado antes de las inferencias

Fecha: 04/10/2026, Europe/Madrid. El usuario autorizó lanzar el nuevo agente de
selección. Goal nativo activo; el estudio de umbrales permanece cerrado.

## Diseño y procedencia

Se conservan los tres cortes externos 2024, 2025 y 2026 porque existen modelos
válidos y observaciones de ambas clases en todos ellos. No se eligen por sus
resultados. Son externos al ajuste, pero ya vistos al diseñar las hipótesis:
**comparación exploratoria retrospectiva, sin confirmación independiente**.

Para cada año externo Y:

| Variante | Evidencia que ordena candidatos | Resolución |
|---|---|---|
| A | Año Y−1, predicho por bundles `threshold` del mismo corte, ajustados hasta Y−2 | Semanal actual |
| B | Y−2 del ranking original, más las mismas filas Y−1 de A | Semanal actual |
| C | Exactamente el catálogo B | Diaria, sin agregación semanal |

Todos utilizan los mismos bundles finales `external`, ajustados hasta Y−1. El
tuning de cada corte queda fijado en su ajuste inicial anterior a Y−2. Nunca se
puntúa Y−1 con el modelo final. Se mantienen los grupos de visitas de 14 días entre
especies, purgas en fronteras, elegibilidad por perfil y particiones del primer
estudio. El inventario verifica exclusión también para modelos compartidos.

A reproduce el **procedimiento** actual en una partición temporal reciente; no
reproduce el reparto operativo 70/30 ni el antiguo A, cuyo ranking era Y−2. Este
último se ejecuta exclusivamente como control técnico contra sus 812 emisiones
guardadas, sin incorporarlo como cuarta candidata.

B−A mide añadir historia anterior a la reciente: cambia soporte, edad y mezcla
temporal de evidencia. Sus dos ventanas proceden de modelos con distintos tamaños
de entrenamiento y configuración inicial común; no es el efecto puro de aumentar
n ni la evaluación de un único artefacto fijo. C−B mide selección diaria; C−A
modifica ambos componentes. No se ajustan modelos nuevos ni umbrales.

Cada observación/perfil/contrato/horizonte tendrá una predicción por candidato;
rechazar duplicados. La prevalencia de referencia viene del ajuste de esa fila,
especie y perfil. No rellenar huecos ni sumar horizontes para superar el mínimo
operativo de ocho casos. El panel nuevo de área contiene 1.056, 3.232 y 4.312 filas
en 2024, 2025 y 2026 respectivamente, cada una con sus estimadores. En caesarea
2025 faltan tres casos Y−1 del perfil físico V3: conservar su ausencia y el
denominador externo completo. A caesarea 2024 tiene sólo cuatro casos de ranking.

## Inferencia del punto y controles

Conservar geografía, temporada, aplicabilidad, suspensiones, fórmula de ranking,
umbral favorable 0,60 y política vigente verificada (`shadow`). C usa las cadenas
originales por día y el mismo selector del primer candidato aplicable: nunca
elige el máximo de probabilidad ni consulta el resultado observado. Su diagnóstico
de consenso semanal no es equivalente; en modo shadow no modifica el consejo.

Las 116 observaciones externas generan 812 emisiones por variante: 55 aereus y
61 caesarea, cada una en horizontes 1–7. Para cada emisión se resuelven los siete
días completos; sólo se evalúa el día con observación. Las trazas diferidas antiguas
no son un panel completo. Antes de inferir se registra la cardinalidad solicitada
y su cota superior; sólo se materializan candidatos necesarios de esos puntos.

Reproducir corte meteorológico de cada contrato. Conservar los requisitos de cada
petición: agrupar familias puede cambiar los días de historia o la física y, por
tanto, las entradas. Caché meteorológica acotada por contexto/corte/requisitos;
no compartir evaluaciones de calidad entre catálogos. No reutilizar inferencias
entre artefactos o contextos diferentes. El histórico meteorológico revisado no
demuestra disponibilidad exacta de esos datos en la fecha original.

El control exige igualdad de decisión, probabilidad, ganador, motivos de abstención
y resultados de los siete días; excluye tiempos y orden de trazas. Una diferencia
detiene el lote y se conserva para diagnosticarla. Errores técnicos no son aciertos
ni abstenciones científicas: se registran y bloquean la conclusión comparativa.

## Métricas y criterio predefinido

Por especie, año y horizonte, y promedio de horizontes: matriz 2×3, falsos
favorables (FP), verdaderos favorables (TP), oportunidades perdidas (desfavorables
y abstenciones sobre positivos), precisión, FPR, recall, cobertura de consejo y
cobertura favorable. Cada observación pesa 1/7 por horizonte en el promedio.
Denominador cero = no estimable. Mantener controles siempre desfavorable y siempre
abstención, con recall cero; no premiarlos por carecer de falsos favorables.

Contrastes pareados B−A, C−B y C−A. Bootstrap: 2.000 réplicas, semilla 20261004,
remuestreo de episodios completos estratificado por corte, percentiles 2,5/97,5,
incluyendo número de réplicas con denominador válido. Los modelos quedan fijos:
el intervalo no recoge toda la incertidumbre del aprendizaje. Separar especies;
no contar episodios compartidos como nuevos al agregarlas.

Regla **exploratoria del agente**, no una relación de costes elegida por el usuario:
una alternativa puede proponerse para confirmación sólo si, por especie y sobre
el promedio conjunto de horizontes, satisface todos estos mínimos:

- Al menos cinco observaciones positivas y cinco negativas externas; al menos
  cinco recomendaciones favorables ponderadas y tres episodios recomendados.
- Recall ≥25%, TP ≥80% del comparador y cobertura de consejo ≥80% del comparador.
- O bien reduce FP al menos 0,5 observaciones ponderadas, o bien no aumenta FP y
  añade al menos un TP ponderado.
- Ningún corte aumenta FP en más de una observación ponderada; en cortes con
  TP del comparador ≥2, conserva al menos la mitad de esos TP.

Mostrar también los valores sin dicotomizar y sus intervalos. Una regla superada
con intervalos amplios sólo produce candidata exploratoria; nunca autorización
de cambio operativo. Si B y C pasan frente a A, ordenar por menos FP, después más
TP y después preferir B por menor cambio. C−B siempre se presenta por separado.
Si ninguna pasa, mantener referencia e indicar qué evidencia falta.

Diagnósticos: concentración/frecuencia de familias, cambios entre días y cortes,
causas de exclusión separando insuficiencia de soporte de mal Brier, calibración
descriptiva del ganador disponible y sensibilidad del ranking al retirar un
episodio de desarrollo cada vez, sin usar resultados externos para cambiar reglas.

## Presupuesto y sellado

Inventario previo: primer estudio 1.229.992.044 bytes y 1.178,965958 segundos de
lotes. Saldo inicial máximo: 917.491.604 bytes y 6.021,034042 segundos. El guard
recalcula ambos estudios antes de cada lote: techo conjunto 2 GiB, 120 minutos,
45 minutos por lote; 8 GiB RSS muestreado por proceso, un cálculo y un hilo de
BLAS/OpenMP/Arrow. La máquina informó 32 GiB RAM y 162,27 GB libres; no se reserva
esa memoria. Medir consumo real y detener ante límites, sin elevarlos.

Guardar fuentes exactas antes de cada lote, referencias/hash de entradas y modelos
reutilizados, protocolo, cardinalidad, predicciones y cierre. Salidas sólo en
`tmp/prediction-model-selection/`, ignorado por Git. Conservar fallos y versiones
del código. No modificar fuentes/resultados del estudio anterior, originales,
código operativo, contenedores, modelos activos, HA real ni worker/coordinador.
