# SMI-04 · Ensayo local de dos capas

Protocolo fijado antes de ejecutar las métricas de este ensayo. Autorización:
continuar autónomamente en local; no tocar HA real ni el worker activo, no crear
imágenes ni contenedores, no hacer limpieza destructiva.

## Pregunta y decisión

¿Separar la reserva superficial de la profunda mejora la cronología de recarga y
secado respecto al regulado de una capa? **IDW es la evaluación principal**, porque
es la entrada disponible al predecir puntos. La lluvia medida es un diagnóstico
secundario. No elegir una versión porque gane únicamente con el pluviómetro.

Reutilizar las 22 estaciones y entradas archivadas en SMI-03: 365 días hasta
18/09/2026, evaluar los últimos 60. No descargar de nuevo ni ajustar parámetros.
Los 17 pluviómetros completos reemplazan solo esos 60 días; antes continúa IDW.
Mismas fechas, capacidades totales, ET y reglas de calidad de sondas en cada par.

## Prototipo y controles

Es un experimento de depósitos en cascada, **no una solución de Richards ni una
estimación de la velocidad de infiltración**. El archivo tiene capacidad total
0–30 cm, no capacidades por horizonte ni conductividad hidráulica. Se supone
capacidad uniforme por espesor: C1=C/3 (0–10 cm), C2=2C/3 (10–30 cm).
Conservar C total permite aislar estructura sin aumentar agua artificialmente.

La lluvia entra al depósito superior; su exceso sobre C1 pasa al inferior, cuyo
exceso sale del perfil. Transferencia en el mismo día, sin retraso calibrado. El
agua necesaria para recargar abajo depende del déficit superior, no de un umbral
fijo de 5/10/15 mm. Es una hipótesis restrictiva: no representa transporte por
debajo de capacidad de campo, ascenso capilar ni flujo preferencial salvo en la
sensibilidad explícita. No pretende demostrar que la lluvia pequeña nunca llegue.

ET₀ y las respuestas de disponibilidad permanecen las de SMI-03: evaporación
lineal con reserva relativa, transpiración Ks, p=0,5; reparto potencial E/T=50/50.
Usar la integración analítica archivada, sin descuento Euler de un día.

Escenarios fijados (todos con Hargreaves y ET nueva, sin seleccionar el mejor):

1. **Una capa:** referencia regulada existente.
2. **Control repartido:** dos depósitos que reciben lluvia y demanda en proporción
   a su capacidad. Debe reproducir exactamente una capa; control de implementación.
3. **Cascada repartida:** cambiar solo la distribución de lluvia a cascada.
4. **Cascada superficial:** además, toda la demanda evaporativa va a la capa
   superior; transpiración repartida por capacidad, sin compensación entre capas.
   Es el candidato conceptual principal, no una distribución de raíces medida.
5. Sensibilidades de cascada superficial: capa superior de 5 o 15 cm (C/6 o C/2),
   y escenario con 25% de lluvia entrando directamente abajo (resto en cascada).
   Son hipótesis, no intervalos de confianza ni parámetros estimados del terreno.

No cambiar simple/regulado al comparar estructura. SMI-03 conserva esa comparación.
Comparar cada escenario con una capa usando la **misma ET** y lluvia. No atribuir
la diferencia de cascada superficial solo al transporte: cambia ubicación de E.

## Controles físicos y observaciones

- Ejecutar desde extremos seco y lleno durante toda la historia. Hueco de entrada
  reinicia incertidumbre; no lo sustituye por cero. Publicar tras ≥90 días válidos
  consecutivos y convergencia por capa ≤max(0,25 mm, 1% de su capacidad).
- Balance diario y acumulado: entrada = cambio de reserva + E + T + drenaje.
  Reserva acotada por capa; pérdidas nunca superiores al agua existente.
- Pruebas sintéticas de conservación, control idéntico a una capa, lluvia con
  déficit superficial, estado previo húmedo, bypass, huecos y ventanas visuales.
- Sondas: 0<VWC≤1, ≥44 registros/día; lluvia medida 48 instantes únicos/día.
  Mantener los ceros dudosos como huecos. No ajustar desfases ni borrar casos malos.
- Comparar reserva superior contra 5 cm e inferior contra 20 cm. Publicar también
  el total 0–30 contra ambas para mostrar el efecto del cambio de magnitud. Ninguna
  sonda puntual equivale exactamente al promedio de capa; 5 cm queda en el límite
  de la sensibilidad de capa superior 5 cm. No convertir VWC en SMI sin FC/WP.
- Pearson, Spearman y correlación de cambios diarios con fechas comunes por par;
  ≥30 pares (29 cambios), mitades temporales con ≥20. Informar pérdida de cobertura.

## Episodios, sin ajustar contra resultados

Agrupar días con ≥1 mm medido, separados por al menos dos días por debajo de 1 mm;
los huecos invalidan el episodio/ventana. Evaluar inicio y fin, lluvia de ambas
fuentes, reserva previa y cambio al día posterior al final respecto al día previo
al inicio. También máximo en los tres días siguientes al final, siempre que no
empiece otro episodio: es ventana descriptiva fija, no desfase óptimo.
Publicar cambios de VWC y SMI en sus propias unidades; no definir 'acierto' con un
umbral instrumental desconocido. Revisar Batlliu y Nerets y resultados adversos.

## Límites y salida

Red descrita como viñedos, no validación forestal. Sin QC instrumental ni zona
horaria confirmados; medias diarias vs estado calculado al final del día. Sin
riego, nieve, interceptación, raíces profundas, pendientes ni conductividades.
Muestra ya explorada, no prueba ciega. Un mejor r no valida litros ni causalidad.
No promover nada al mapa automáticamente: informe, CSV, gráficos comprensibles,
huellas de entradas/código y decisión razonada; cálculos operativos intactos.

Fuentes conceptuales primarias (no suministran parámetros para este prototipo):
[FAO: suelo y agua](https://www.fao.org/4/R4082E/r4082e03.htm),
[FAO: movimiento del agua y estado antecedente](https://www.fao.org/4/y4690e/y4690e07.htm),
[FAO-56: estrés hídrico](https://www.fao.org/4/x0490e/x0490e0e.htm).
