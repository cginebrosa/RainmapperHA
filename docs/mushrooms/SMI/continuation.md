# Continuación de las auditorías SMI

Snapshot actualizado: 20/09/2026. Revalidar código, configuración y fuentes antes de describir
su estado actual. No es una autorización para tocar HA real o el worker activo.

## Actualización SMI-07 · prevalece sobre el historial inferior

El usuario ha aceptado **regulada + Penman–Monteith + una capa** para todas las
rutas. Implementación en el checkout local, con el simple solo para comparación
en el mapa. [Decisión, pruebas, consumidores y migración](adoption-2026-09-20/README.md).
`mushroom_water_physics.py` es el núcleo compartido; el antiguo archivo de física
del mapa solo reexporta funciones. Contrato `regulated_pm_single_layer_v1`.
No reutilizar pesos físicos antiguos: los contratos los rechazan hasta reconstruir
datos/reentrenar. Runtime/precálculo también cambian de identidad.

No se han construido imágenes ni modificado contenedores/HA real/worker activo.
La verificación es offline + navegador de pruebas, **no un despliegue en HA local**.
Antes de publicación falta el circuito local equivalente exigido por AGENTS y
la autorización compatible con la prohibición vigente de tocar el worker/crear
imágenes. No deshacer esa restricción por inferencia.

Se conserva toda la evidencia SMI-01…06. Sus conclusiones provisionales eran el
estado de esas auditorías; la adopción es una decisión posterior del usuario.
Mycora se revisó como página pública: [hallazgos y límites](adoption-2026-09-20/mycora.md).

## Actualización SMI-06 · leer antes del historial inferior

Ejecutada la auditoría de **cambios de reserva en litros**, autorizada por el
usuario. [Informe](storage-2026-09-20/README.md), [protocolo previo](storage-2026-09-20/PROTOCOL.md)
y [registro del proceso](storage-2026-09-20/process.md). Reutilización offline,
sin cambios de modelos ni servicios. Cinco pruebas dirigidas pasan.

- Agua total reconstruida de sondas 5/20/50 hasta 30 cm frente a cambios del
  agua disponible modelada. Dos integraciones y un horario alternativos.
  **Comparación condicionada**: umbrales volumétricos FC/WP y calibración no
  confirmados; cero estaciones declaradas validadas en litros disponibles absolutos.
- 22 estaciones, 1.206 cambios diarios, 68 recargas de 21 estaciones y 27
  ventanas de cinco días secos de 21; 24 de esas ventanas en 18 estaciones
  también confirmadas secas por pluviómetro. Cobertura incompleta visible.
- La referencia PM/regulada/una capa tiene mediana de MAE diario 1,034 L/m²;
  recarga +1: 4,554; secado cinco días: 1,692. No llamar a esos residuos
  «precisión del SMI». Dos capas mejora recargas; Hargreaves mejora secados.
  Ventaja PM pequeña/no uniforme, sin ganador general de cantidades.
- Sesgo de referencia: +2,49 en recargas y +1,33 L/m² en pérdidas de cinco
  días; con pluviómetro seco +1,19. No atribuir todo a ET ni aplicar corrección
  universal. Batlliu 24/08 tiene fuerte error de lluvia IDW; MDF fuerte
  discrepancia de secado aun con lluvia cero en el intervalo.
- **Mantener referencia provisional**, no promover la cascada ensayada. La
  auditoría cuestiona amplitudes aunque las curvas correlacionen.
- Próximo paso concreto todavía no ejecutado: recuperar FC/WP estimados que
  originaron la capacidad, por horizonte, de caché local si existe. Servirán
  para comparación condicionada a SoilGrids, no validación independiente.
  Para esta última faltan densidad/retención/calibración/emplazamiento fiable;
  no se ha agotado la búsqueda de metadatos públicos.
  La búsqueda dirigida posterior localizó una pista sobre sondas de potencial
  hídrico a 20/100 cm (Torre Lluvià, comunicación 2024): comprobar canales y
  cobertura antes de descargar. [Fuentes](storage-2026-09-20/sources.md).

El usuario pidió aclarar si la referencia ya estaba en HA local: sí, se
comprobaron huellas de física e hidrología en el contenedor local, iguales al
repo y a la física de la auditoría. «No cambiar el mapa» en SMI-05 significa
no hacer un nuevo cambio: la implementación regulada ya existía. PM tiene
alternativa Hargreaves cuando faltan entradas. Ver huellas y límites de la
comprobación en el registro de proceso; no se reinició ni alteró nada.

## Elección posterior SMI-05 · lectura prioritaria

El usuario **aceptó explícitamente** regulada + ET nueva + una capa como SMI de
referencia. Preguntó cómo contrastar mejor las cantidades absolutas. Se documentó
el [siguiente enfoque](absolute-water-plan.md). El contraste de cambios de
litros quedó ejecutado después en SMI-06; la validación absoluta sigue pendiente.
No se cambió el mapa/worker en esta aceptación.

El usuario pidió elegir para avanzar, y señaló que el factorial contiene ocho
opciones. Se añadieron simple + dos capas con ambas ET. Ver [informe](factorial-2026-09-20/README.md)
y [ranking](factorial-2026-09-20/ranking.md). **Recomendación: regulada + ET nueva
(PM aproximada actual) + una capa de 0–30 cm.** No se ha activado ningún cambio.

La evidencia conserva las 22 estaciones; el ranking del total usa 18 comunes
con ambas sondas y las ocho correlaciones definidas. Promedio igual de r de 5/20
por estación, después mediana: primera 0,667, regulada PM dos capas 0,640,
regulada HG una capa 0,624. También primera en cambios diarios; Spearman total
favorece ligeramente dos capas. Comparando cada sonda con su capa quedan 13
estaciones comunes y vuelve a quedar primera la regulada PM de una capa.
No decir que haya 22 pares completos ni que r mida exactitud de litros.

Cuatro pruebas nuevas, 44 simulaciones adicionales, control del orden de drenaje,
704 métricas y 1.320 filas diarias. Sin servicios ni Docker. Esta selección práctica
no requiere esperar a otra investigación; no demuestra que la ET nueva sea mucho
mejor ni valida agua absoluta. El mapa y worker siguen fuera del alcance de cambios.

## Actualización tras SMI-04

**El ensayo de dos capas ya está implementado y ejecutado offline.**
[Informe](layers-2026-09-19/README.md), [protocolo](layers-2026-09-19/PROTOCOL.md),
[resultados por estación](layers-2026-09-19/station-results.md).
Los apartados inferiores conservan el historial SMI-01/03; sus frases «multicapa
pendiente» describen ese momento, no el estado al cerrar SMI-04.

- Usuario confirmó que las predicciones de puntos usarán IDW. **IDW es criterio
  principal de decisión**; pluviómetro solo control diagnóstico.
- Usadas las mismas 22 estaciones y 365 días guardados, sin servicios ni nuevas
  descargas. Capacidad total archivada, no capacidad por horizonte: reparto por
  espesor explícito. No afirmar que se hayan obtenido conductividades o capas reales.
- Referencia regulada, control de dos depósitos equivalente a una capa, lluvia
  en cascada y después evaporación superficial; ET fija en cada comparación.
  Sensibilidades prefijadas 5/10/15 cm y bypass 25%, sin ajuste ni selección.
- 2.340 métricas, 1.320 filas diarias comprimidas, 72 episodios. 7 pruebas y
  balance de masa, paridad de control y calidad de datos comprobados.
- Con IDW/ET nueva, capa inferior mejora r frente a 20 cm en 14/22, pero la
  superior empeora frente a 5 cm en 18/21. Hargreaves reproduce el patrón.
- **Nueve estaciones sin recarga inferior**: correlaciones altas pueden describir
  residuos prácticamente cero. Revisar amplitudes y transferencias antes de
  interpretar r. No se descartaron estas estaciones ni se ajustaron umbrales.
- Casos adversos: Clot 24/08 (25,1 mm medidos, 11,37 IDW), Garriguella 21/08
  (25,5 frente a 12,88). La cascada IDW pierde recargas observadas a 20 cm.
  Batlliu 24/08: 37,7 frente a 3,16 mm; tampoco puede reconstruir esa recarga.
- **No promover esta cascada al mapa.** Mantener una capa como referencia
  experimental; esto no valida litros, bosque ni la elección de ET.
- No se tocó HA real, worker, mapa ni imágenes Docker. Solo código y documentación
  del experimento. Gráfico probado en Chrome y navegador temporal cerrado.

Antes de otro ensayo: fundamentar capacidades por horizonte y transporte no
saturado con datos disponibles, evaluar superficie y profundidad conjuntamente
con IDW y reservar nuevos periodos/estaciones antes de calibrar. No convertir el
escenario de 5 cm en ganador por su r inferior: empeora aún más la superficie.

## Historial: actualización tras SMI-03 (23:25)

Se completó la comparación en **22 estaciones**. Ver [informe actualizado](baseline-2026-09-19/README.md)
y [protocolo ejecutado](baseline-2026-09-19/PROTOCOL.md). Los apartados siguientes
conservan el contexto previo; sus pendientes de coordenadas, exportación ampliada
y separación de factores se resolvieron en SMI-03 con las limitaciones allí descritas.

- 22 fichas consultadas; coordenadas PDF contrastadas con marcadores (máximo 40,42 m).
- Red descrita por ICGC como viñedos: la ampliación no valida el bosque.
- 22 exportaciones locales con 365 días, sin tocar HA real, worker ni imágenes.
- 4 combinaciones depósito/ET₀ por estación; 4 adicionales con lluvia reciente
  medida en las 17 sin huecos. 468 comparaciones, 1.320 filas diarias.
- A 20 cm, regulado actual supera referencia anterior en 16/20 comparaciones
  definidas, pero sigue con r negativo en seis estaciones. Cambio de ET₀ con
  regulado fijo: mediana de mejora de r solo +0,003; no atribuirle toda la ventaja.
- En Batlliu, al usar lluvia medida, simple + ET anterior alcanza r=0,881 y
  regulado + ET nueva 0,840. Las conclusiones cambian al controlar las entradas.
- Clot de les Peres: sonda de 5 cm contiene muchos ceros; quedan solo 15 días
  admisibles y no se calcula r. Bolvir a 20 cm queda en 33 días.
- Se archivaron datos y tres módulos de física para reproducción offline. No hay
  parámetros ajustados. La reserva futura de estaciones/periodos sigue pendiente;
  el conjunto ya inspeccionado no es una evaluación ciega.
- **SMI-04 multicapa continúa pendiente.** No confundir SMI-03, ya ejecutado,
  con el ensayo de dos capas propuesto en la conversación.

## Lo que ya se hizo

- Contraste de 60 días (21/07–18/09/2026), con cálculos locales reconstruidos sobre
  un historial total de 365 días. La ventana visual no reinició el depósito.
- El cálculo nuevo combina una ET₀ distinta con extracción regulada. La comparación
  inicial cambia ambos factores a la vez y no permite atribuir la mejora a uno solo.
- Correlación de evolución favorable en Vallcebre y Batlliu; mejora inconsistente
  en Olvan y resultado adverso en Nerets. No se validaron litros, porcentajes absolutos
  ni evapotranspiración real. Véase el informe para métricas y limitaciones.
- Descarga de las 22 estaciones anunciadas por el visor ICGC. 21 cumplen cobertura
  preliminar de 54/60 días; Clarella tiene 51. Esto no es aceptación instrumental.
- Revisión de intervalos de media hora, además de medias diarias, en episodios
  concretos comentados por el usuario (sección siguiente).

## Observaciones por episodio que motivan el experimento

Los números siguientes proceden de `evidence.json.gz → icgc.points[].rows`.
Son fechas y horarios publicados, cuya zona horaria no se confirmó.

- **Batlliu, 6 de agosto:** 15 mm medidos; VWC a 20 cm prácticamente estable
  (media 0,17440 m³/m³, mínimo 0,174, máximo 0,175).
- **Batlliu, 8 de agosto:** 14,4 mm; la media a 20 cm sube de 0,17629 ese día
  a 0,18165 el día 10. Hay una respuesta pequeña que apenas se aprecia en el gráfico.
- **Batlliu, 11 de agosto:** 49,3 mm; máximo de VWC a 20 cm 0,289 y media del
  día 12 de 0,24669. Es compatible con una humectación importante a esa profundidad,
  pero no prueba un umbral universal de lluvia ni separa el efecto de lluvias previas.
- **Nerets, 20 de agosto:** 8,7 mm entre 22:00 y 23:30; la media diaria mezcla
  casi un día entero previo a la lluvia con pocas medidas posteriores.
- **Nerets, 24 de agosto:** 15,2 mm; pequeña respuesta en 5 y 20 cm ese día,
  seguida de descenso. La subida de días posteriores no prueba por sí sola un
  retraso de infiltración. No se ha identificado la causa.

## Hipótesis, no conclusiones aceptadas

Nuestro depósito representa la reserva integrada **0–30 cm**, no una sonda puntual
a 30 cm. Una lluvia puede aumentar la reserva superficial sin provocar una respuesta
equivalente en una sonda a 20 cm. Por eso no exigir coincidencia de magnitudes ni
respuesta idéntica a cada lluvia entre el depósito y esa sonda.

Propuesta pendiente: probar capas 0–10 y 10–30 cm, con transferencia y balance
conservativo. Esa división es un diseño inicial a evaluar, no una parametrización
ya justificada. No introducir un umbral fijo de 5/10/15 mm ni un retraso fijo para
hacer coincidir las curvas. El transporte depende del estado previo y del suelo.

## Antes de ejecutar el experimento ampliado

1. Revisar coordenadas exactas y emplazamiento, suelo, vegetación, posible riego,
   profundidad/instalación y calidad de sondas. El GeoJSON público tiene metadatos
   inconsistentes: declara EPSG:3857 aunque las geometrías parecen lon/lat y algunos
   campos X/Y están repetidos. No resolverlo automáticamente tomando cualquier campo.
2. Verificar horarios y significado de los acumulados de lluvia; revisar ceros,
   saltos y tramos casi constantes. El filtro de cobertura no lo hace.
3. Seleccionar estaciones de evaluación reservadas antes de ajustar parámetros,
   teniendo en cuenta agrupaciones geográficas y entornos. La selección aún no existe.
4. Preparar entradas locales para las estaciones añadidas, con historia anterior
   suficiente y estado inicial controlado. No arrancar el depósito vacío al comienzo
   de los 60 días de comparación. Las series locales añadidas aún no existen.
5. Comparar con lluvia medida como experimento separado de IDW. En Batlliu los
   totales difieren mucho (161,5 frente a 91,2 mm); no compensarlo afinando ET₀.
6. Aislar cambios: una comparación debe mantener ET₀ fija para evaluar la estructura
   de capas; otra puede evaluar ET₀ con la misma estructura. No cambiar todo a la vez.

Evaluar recarga, momento de respuesta, persistencia y secado por episodio, además
de tendencias generales. Priorizar sondas a 5 y 20 cm; usar 50 cm como contexto.
Clot de les Peres tiene también 10 y 30 cm. No equiparar m³/m³ a porcentaje de agua
disponible sin conocer capacidad de campo y punto de marchitez del emplazamiento.

## Pendientes que no se deben perder

- Semántica de SSF=2 en la colección Copernicus consultada: discrepancia de escala
  entre documentación y STAC. El contraste satelital sigue siendo exploratorio.
- Calidad y zona horaria de las observaciones ICGC; representatividad forestal de
  cada estación y pertinencia del muestreo de suelo local.
- Posible efecto de la agregación diaria sobre la respuesta a lluvias nocturnas.
- Esos dos trabajos, pendientes al redactar este apartado histórico, quedaron
  completados en SMI-03/04; consultar las actualizaciones superiores.

## Exportación local original

`contrast-2026-09-19/export_local.py` conserva el script de extracción utilizado.
El comando histórico fue:

```sh
docker exec -i rainmapper-local-rainmapper-ha-ui-1 python - < docs/mushrooms/SMI/contrast-2026-09-19/export_local.py > /private/tmp/rainmapper-smi-contrast-local.json
```

No hace falta repetirlo para leer o reproducir las métricas guardadas. Antes de
usarlo otra vez, verificar que el contenedor sigue siendo local, que existen las
rutas de configuración y que las huellas del código corresponden al ensayo previsto.
El script no contiene los puntos nuevos ni fija los datos meteorológicos del futuro.
No presentar una ejecución nueva como reproducción exacta sin comparar entradas y huellas.
