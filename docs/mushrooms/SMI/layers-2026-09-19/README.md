# SMI-04 · Ensayo de dos capas con IDW

Iniciado el 19/09/2026 y completado el 20/09/2026. [Protocolo previo](PROTOCOL.md),
[gráficas](comparison.html), [tabla por estación](station-results.md).

## Decisión práctica

**No sustituir el cálculo del mapa por este prototipo.** Separar superficie y
profundidad ayuda a representar algunas recargas, pero la cascada ensayada bloquea
otras que sí registran las sondas, especialmente cuando IDW subestima la lluvia.
Además, empeora claramente la evolución de la capa superficial.

La conclusión se basa principalmente en **IDW**, como pidió el usuario: será la
entrada real al predecir un punto. Los resultados con pluviómetro se conservan
como diagnóstico; no justifican adoptar un cálculo que falle con IDW.

Se ha completado el experimento, no una mejora operativa. No se han editado ni
reiniciado HA real, el worker activo o el mapa, ni creado imágenes/contenedores.
No se han descargado nuevas series ni ajustado parámetros para maximizar r.

## Qué se comparó

22 estaciones ICGC, mismas entradas guardadas en SMI-03. Historia total de 365 días
hasta 18/09/2026; evaluación de 21/07 a 18/09. Cambiar la ventana visible no reinicia
el suelo ni elimina la lluvia de días anteriores.

Se mantiene la capacidad total 0–30 cm y se reparte por espesor: 1/3 arriba
(0–10 cm), 2/3 abajo (10–30 cm). **No son capacidades medidas por horizonte**:
el archivo de entrada conserva únicamente la capacidad total. La lluvia llena
primero arriba y su exceso pasa abajo en el mismo día. No hay velocidad de
infiltración calculada, transporte subsuperficial continuo ni retraso ajustado.

Controles sucesivos:

1. Una capa regulada existente.
2. Dos depósitos con lluvia y demanda repartidas por capacidad: control que
   reproduce una capa, hasta precisión numérica.
3. Lluvia en cascada, manteniendo la demanda repartida.
4. Cascada y evaporación concentrada arriba: candidato conceptual principal.

Se repite con Hargreaves y ET nueva, siempre comparando a ET fija. Sensibilidades
prefijadas: superficie de 5 o 15 cm y entrada directa del 25% de lluvia abajo.
La demanda E/T total sigue siendo 50/50, la transpiración se reparte por capacidad
y se conserva la misma respuesta de estrés. Esa distribución no está calibrada
para raíces de bosque. El cambio de escenario 3 a 4 mueve la evaporación: no
atribuir todo su efecto exclusivamente a la transferencia de lluvia.

En 17 estaciones con pluviómetro completo se repiten los escenarios cambiando
solo la lluvia reciente de 60 días; la historia anterior continúa IDW.

## Resultados con la entrada operativa IDW

Candidato de 0–10 / 10–30 cm con evaporación superficial, respecto a una capa:

| ET fija | Referencia | Mayor r / pares | Mediana del cambio de r |
|---|---|---:|---:|
| ET nueva | 5 cm frente a capa superior | 3/21 | −0,107 |
| ET nueva | 20 cm frente a capa inferior | 14/22 | +0,053 |
| Hargreaves | 5 cm frente a capa superior | 3/21 | −0,102 |
| Hargreaves | 20 cm frente a capa inferior | 13/22 | +0,050 |

Por tanto, **el problema superficial aparece con ambas fórmulas de ET**. No se
resuelve eligiendo Penman–Monteith frente a Hargreaves.

Con ET nueva, cambiar solo la distribución de lluvia a cascada mejora la mediana
de r a 20 cm en apenas +0,006. Al mover también la evaporación arriba se llega a
+0,053. El total integrado 0–30 cm cambia mucho menos: +0,012 de mediana de
diferencias. Comparar una capa integrada con una capa inferior cambia también la
magnitud representada; no significa que hayamos validado una mejor reserva total.

### Una correlación alta puede ser engañosa

**En nueve estaciones el candidato no transfiere agua abajo durante los 60 días.**
Su reserva inferior es un residuo casi nulo que decrece. Puede correlacionarse
con una sonda que también desciende aunque no represente las recargas.

Ejemplos con IDW y ET nueva:

- Ribera de Sió: r≈0,788, pero amplitud inferior de solo **0,000010 puntos**.
- Vilosell: r≈0,808, amplitud **0,000076 puntos**.
- Cantallops: r≈0,929, amplitud **0,076 puntos**, sin recarga inferior calculada.

Los otros casos sin recarga son Clot de les Peres, Nerets, Los Coscolls, El Miracle,
Garriguella y Pobla de Cérvoles. No se han eliminado de las métricas ni creado un
umbral a posteriori para mejorar el resultado. Tras detectar el problema se
añadieron amplitudes, flujos y r desde extremos iniciales como diagnóstico.
Los extremos iniciales dan aquí las mismas curvas: **no es un fallo de arranque**;
es una limitación de valorar correlaciones de residuos minúsculos.

En cambios diarios, la mediana de diferencias de r por estación es +0,055, pero
la mediana de r del grupo pasa de 0,163 a 0,152. Ambas cuentas son correctas y
distintas; los resultados son heterogéneos. No afirmar una mejora temporal general
a partir de uno de esos resúmenes ni de la correlación del periodo completo.

## Qué ocurre en episodios concretos

### Batlliu: mejora parcial, no solución completa

Con IDW y ET nueva, r a 20 cm pasa de 0,805 a 0,840, pero r de cambios diarios
baja de 0,271 a 0,255. La división atenúa la respuesta del 6 de agosto abajo;
el 8 todavía recarga de forma marcada antes de la respuesta grande de la sonda.
El 11 ambos representan una recarga importante. No prueba un umbral universal.

El 24/08 el pluviómetro registra **37,7 mm** y IDW **3,16 mm**. La sonda a 20 cm
sube; la capa inferior con IDW sigue secándose. Sustituir la lluvia por la medida
hace que el prototipo recargue, pero esa entrada no estará disponible en cualquier
punto. Con lluvia medida, r del candidato en Batlliu es 0,807 frente a 0,840 de
una capa regulada con la misma ET: tampoco gana en todos los casos controlados.

### Clot de les Peres y Garriguella: la cascada pierde recargas reales

- Clot, 24/08: pluviómetro **25,1 mm**, IDW **11,37 mm**. La sonda a 20 cm aumenta
  aproximadamente 0,103 m³/m³ entre el día anterior y el posterior. Con IDW el
  prototipo no recarga abajo; con lluvia medida sí. r del periodo pasa de 0,422
  (una capa IDW) a −0,418 (capa inferior IDW).
- Garriguella, 21/08: pluviómetro **25,5 mm**, IDW **12,88 mm**. Mismo problema:
  hay respuesta observada, pero la cascada con IDW no recarga abajo. r pasa de
  0,512 a −0,452.

Esto muestra que el requisito de llenar primero el depósito superior **puede
agravar una subestimación de lluvia IDW**. No demuestra que toda discrepancia
proceda de IDW: también son hipótesis la capacidad superior, la localización de
la evaporación y el esquema de transferencia.

`episodes.csv` recoge 72 episodios con ventanas completas según el protocolo.
Las lluvias cercanas se agrupan: las del 6, 8 y 11 de agosto en Batlliu no son
tres episodios independientes bajo esa regla. Las fechas individuales se revisan
en `series.csv.gz`. No hay ajuste de desfases ni clasificación de acierto con
un umbral instrumental desconocido.

## Sensibilidad y límites

Con superficie de 5 cm la mediana de diferencia de r inferior mejora más
(+0,101 con IDW/ET nueva), pero la superior empeora más (−0,214). **No elegir 5 cm
porque gane ese número**: sería seleccionar sobre la muestra ya inspeccionada.
La entrada directa del 25% abajo reduce la mejora inferior a +0,013; no se ha
estimado ese porcentaje del terreno. Las capacidades por horizonte y el transporte
requieren fundamento físico, no escoger la curva más agradable.

El suelo modelado es agua disponible entre marchitez y capacidad de campo. Su
0% no significa suelo sin agua. La cascada omite flujo no saturado y ascenso capilar,
y no dispone de conductividad, curva de retención local ni distribución de raíces.
Los datos diarios tampoco permiten reconstruir el tránsito dentro del episodio.
La explicación conceptual está en el [protocolo y sus fuentes FAO](PROTOCOL.md).

Las sondas son puntos, nuestras capas son promedios. Red descrita como viñedos;
sin QC instrumental, riego o zona horaria confirmados, no validación del bosque.
Clot tiene solo 15 días admisibles a 5 cm; Bolvir, 33 a 20 cm. No convertir VWC a
SMI ni comparar alturas de gráficos como error en litros.

## Verificaciones y reproducción

```sh
.venv/bin/python docs/mushrooms/SMI/layers-2026-09-19/test_model.py
.venv/bin/python docs/mushrooms/SMI/layers-2026-09-19/analyse.py
```

- **7 pruebas**: conservación, control equivalente a una capa, déficit previo,
  bypass, límites/agua inexistente, historia y huecos, y perturbación de 0,01 mm.
  En esta última, la reserva total no salta más que el agua añadida.
- **22 estaciones, 2.340 comparaciones, 1.320 filas diarias, 72 episodios**.
  Todas las simulaciones de capas convergen y conservan 60 días publicables;
  las comparaciones con sondas mantienen sus huecos y fechas comunes.
- Error máximo de conservación diario/acumulado: **9,67×10⁻¹³ mm** como cota
  redondeada del observado. ET, sondas y control reconstruidos contrastados con
  la evidencia de SMI-03; módulos archivados comprobados por SHA-256.
- HTML autónomo con selector de 22 estaciones, leyendas, zoom y valores al pasar
  el ratón. Probado en Chrome sin interfaz: Batlliu inicial, cambio real del
  desplegable a Clot, un único panel visible y cero excepciones JavaScript.
  Inspeccionadas ambas capturas; navegador temporal cerrado al terminar.

`summary.json` guarda flujos por escenario, cobertura,
métricas agregadas y huellas de código/entradas. Los parámetros explícitos están
en `model.py` y el protocolo. Datos de entrada reutilizados por referencia desde
SMI-01/03; ninguna credencial. Series nuevas comprimidas para no acumular copias.

## Próximo paso razonable

Mantener el regulado de una capa como **referencia experimental**, sin darlo por
validado, y no promover esta cascada. Antes de otro ajuste, buscar si las fuentes
ya disponibles permiten obtener capacidad por horizonte y justificar transporte
no saturado; diseñar un ensayo que compruebe simultáneamente superficie y
profundidad bajo IDW. Reservar otro periodo o estaciones antes de calibrar.

Este ensayo no decide simple frente a regulado ni Hargreaves frente a ET nueva:
esa comparación permanece en SMI-03. Confirma que añadir capas por sí solo no
basta y que el contraste operativo debe seguir usando IDW.
