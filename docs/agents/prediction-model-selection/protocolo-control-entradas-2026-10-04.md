# Concreción técnica antes de inferir

Complementa el protocolo cerrado, sin cambiar variantes, particiones ni criterios.

El resolver diario C materializa candidatos por familia en el orden de su cadena.
Puede detenerse cuando encuentra el primer candidato que supera los filtros,
aunque su probabilidad produzca consejo incierto. Una prueba sintética contrasta
esa ejecución con la exhaustiva: mismo ganador, interpretación y fallback.

El evaluador observa los requisitos meteorológicos efectivos sin modificarlos.
Para cada modelo/fecha objetivo/corte presente tanto en B como en C comprueba
igual lookback y uso de física; contexto y artefacto son comunes por construcción.
También rechaza que un método prepare dos veces ese mismo modelo/corte con
requisitos distintos. Las comparaciones se guardan y una discrepancia detiene
el lote. No se corrige silenciosamente la referencia ni se atribuye una diferencia
de datos a la selección diaria.

El control técnico antiguo conserva su ruta de ejecución y compara todos los
campos científicos, incluidas las trazas. El uso compartido entre métodos se
limita a meteorología con claves exactas y una LRU de ocho entradas por observación.
Las evaluaciones de calidad y las predicciones de los modelos no se comparten.
