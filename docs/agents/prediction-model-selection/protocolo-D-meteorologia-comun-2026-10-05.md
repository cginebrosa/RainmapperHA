# D: contraste nuevo con meteorología común · antes de inferencia puntual

El inventario D comprobó que el manifest meteorológico utilizado por los estudios
cerrados ya no está disponible en su ruta original; el CURRENT local y las
observaciones/áreas operativas también cambiaron. La cohorte privada, los
benchmarks, los modelos, la geografía preparada y los resultados cerrados siguen
sellados. El código científico coincide con el de esos estudios.

Comparar D calculada con meteorología actual frente a A/B/C antiguas confundiría
dos cambios. Para completar el estudio delegado se prepara **un contraste nuevo
A/B/C/D sobre un único snapshot meteorológico actual**, congelado antes de la
primera inferencia. No se repiten entrenamientos, generación de características
de desarrollo, geografía ni estudios antiguos; sus resultados quedan intactos.
Las nuevas inferencias de A/B/C son controles necesarios de este contraste.

Se mantienen exactamente los116casos, etiquetas, localizaciones y geografía
privados originales, los modelos finales por corte y catálogosA/B/C guardados,
y los catálogosD recién sellados. No se incorporan las nuevas observaciones ni
áreas operativas. Los únicos nuevos datos consumidos son el snapshot meteorológico
local común y su catálogo de estaciones. No hay descargas ni regeneraciones.

El criterioI4, coste4, mínimos de actividad/evidencia, bootstrap y contrastes del
protocoloD original permanecen sin cambios. No se ha calculado aún ningún consejo
D. Los diagnósticos de ranking ya obtenidos no se usan para modificar filtros,
seleccionar años ni fijar nuevas reglas de éxito.

El contraste principalD−B y los secundariosD−A/D−C usarán exclusivamente las
nuevas emisiones comunes. Se mostrará aparte cuánto cambianA/B/C respecto a sus
resultados guardados, sin atribuir esas diferencias aD. La interpretación sigue
siendo retrospectiva: la revisión meteorológica no prueba disponibilidad real
de esos datos al emitir una predicción histórica.

Se reutiliza la evaluación nativa semanal deA/B/D y la diaria ya validada deC,
incluido su plan previo de reutilización cuandoB ya resuelve las mismas cadenas
diarias. Cada petición conserva sus requisitos meteorológicos nativos; comparar
contratos de los mismos modelos y días entreB/C yB/D, deteniéndose si difieren.
Los días, modelos o perfiles ausentes no se inventan ni se completan con vecinos.

Preflight: sellarCURRENT, manifest y catálogo; verificar hashes de las particiones
mediante el lector y las entradas anteriores. Rechazar cualquier modificación
durante el cálculo. La nueva salida se guarda únicamente en `common-weather/`
dentro de la carpetaD; 812emisiones por método,3.248en total, siguen siendo116
observaciones distintas. A/B/C históricos no se sobrescriben ni se recalculan
para reemplazar su evidencia original.

Se conserva el presupuesto global nuevo de60min/512MiB/8GiB y un cálculo a la
vez. Los lotesD anteriores sumaron75,79s; no se reinicia el contador. Estimación
conservadora de esta etapa:15–25min, basada en las duraciones registradas de
evaluación multivariante anterior; la medición real prevalece. Si el snapshot
cambia o el límite se alcanza, conservar parciales y comunicar la causa concreta.
