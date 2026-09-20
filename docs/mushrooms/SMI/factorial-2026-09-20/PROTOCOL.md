# SMI-05 · Completar las ocho combinaciones

Petición del usuario: elegir entre simple/regulada × Hargreaves/ET nueva ×
una/dos capas. SMI-03/04 solo proporcionaba seis combinaciones principales.
Protocolo escrito antes de calcular las dos que faltan. Solo auditoría offline.

## Qué se añade

Dos capas con extracción simple, con ambas ET. Misma cascada que `surface` en
SMI-04: capacidad C/3 y 2C/3, lluvia primero arriba, desborde abajo, E potencial
50% arriba y T potencial 50% repartida por capacidad. Cambia únicamente la
extracción: consumir demanda completa mientras exista agua en cada capa, sin
reducción gradual por sequedad ni compensación desde otra capa. Repartir E/T
real proporcionalmente a sus demandas cuando no alcance el agua.

La cascada drena antes de extraer, como en SMI-04; la referencia simple de una
capa histórica extrae antes de drenar. Esta diferencia ya existía entre simple y
regulada. Añadir un control simple de una capa con drenaje previo para detectar
si afecta a la recomendación; no contarlo como una novena opción principal.

No se afirma probar todos los modelos multicapa posibles: las ocho combinaciones
corresponden a esta estructura prefijada de dos capas. No ajustar espesores,
repartos o retrasos para mejorar la métrica.

## Entradas, calidad y comparación

IDW es la entrada principal. Reutilizar los 365 días y sondas de las 22 estaciones;
evaluar los mismos 60 días de SMI-03/04. No nuevas descargas ni cambios operativos.
ET recalculada a partir de entradas congeladas y verificada contra SMI-03/04.
Extremos seco/lleno, ≥90 días y convergencia por capa, huecos no son ceros.

Reproducir las seis series anteriores por referencia, añadir las dos nuevas.
Comparar sondas 5/20 cm con una capa integrada o capas superior/inferior. Como
diagnóstico adicional, comparar también el total de dos capas frente a ambas:
el SMI que se desea presentar sigue siendo la reserva del perfil 0–30 cm.

Elección conjunta: promedio de las dos correlaciones por estación, igual peso
a profundidades; después mediana entre estaciones. Fechas comunes por estación
y sonda para todos los candidatos. Para el ranking pareado, conservar estaciones
con r definido en ambas profundidades en las ocho combinaciones; publicar su
número, sin imputar ceros a r indefinidos. Mostrar también cada profundidad
con toda su cobertura utilizable y los casos de curvas constantes.

Además de Pearson, cambios diarios y Spearman; al menos 30 pares diarios (29
cambios). No seleccionar exclusivamente por r: mostrar amplitud/curvas sin recarga
de SMI-04 y resultados de superficie. No convertir r en porcentaje de exactitud.

Es una selección práctica sobre datos explorados, no validación independiente,
ni demostración de valores absolutos en litros o fiabilidad forestal. La diferencia
pequeña entre ET puede justificar elegir una sin declararla físicamente superior.

Salida: tabla de las ocho combinaciones, recomendación explícita y reproducible,
pruebas de conservación/monotonicidad y documentación para siguientes sesiones.
