# SMI-06 · Cambios de almacenamiento en litros

Protocolo fijado antes de calcular los resultados, 20/09/2026.
Solo auditoría offline. Cuatro candidatos regulados de SMI-05, sin recalibración,
misma lluvia IDW, capacidad y calendario. No cambia mapa, HA real ni worker.

## Qué puede y qué no puede medir

Las sondas VWC permiten reconstruir **agua total**, con incertidumbre espacial.
El modelo produce **agua disponible**. Comparar incrementos elimina un nivel
constante de agua no disponible, pero solo sería una validación equivalente si
el perfil permanece entre marchitez y capacidad de campo. Esos umbrales
volumétricos por horizonte no están confirmados en los datos archivados.
Por tanto los errores son **residuos condicionados**, no errores absolutos
certificados del SMI. Ninguna estación se declarará validada en litros restantes.

Las fichas contienen retención gravimétrica; no se inventará densidad aparente
ni se tomarán mínimos/máximos observados como marchitez/capacidad de campo.
No se usará SoilGrids como referencia independiente de sí mismo.

## Referencia, profundidad y tiempo

- Perfil principal: interpolación lineal entre sondas 5, 20 y 50 cm; mantener
  constante 0–5, integrar solo 0–30 cm. Pesos en mm: 125, 158⅓, 16⅔.
- Sensibilidad A: 5/20 cm, mantener valor de 20 hasta 30: pesos 125/175 mm.
- Sensibilidad B: bloques 0–10 y 10–30 con 5/20 cm: pesos 100/200 mm.
  Son hipótesis fijas de integración, no horizontes medidos ni un intervalo de
  confianza. No elegir retrospectivamente la que favorezca a un candidato.
- Sondas admisibles: 0<VWC≤1, ≥44 lecturas válidas por día; duplicados de
  timestamp son error. Perfil exige todos sus canales, sin rellenar huecos.
- Principal: lectura exacta 23:30 de cada fecha publicada, después de exigir
  cobertura diaria. Sensibilidad: media diaria con el mismo filtro. Modelo:
  estado al terminar ese día. Zona horaria publicada no confirmada: alineación
  nominal, sin afirmar coincidencia UTC ni optimizar desfases.
- 50 cm solo ayuda a interpolar el tramo 20–30, nunca se añaden 20 cm de espesor.
  Posibles discrepancias perfil edáfico/sondas, como roca desde 25 cm en la ficha
  de Batlliu, impiden considerar el perfil reconstruido una verdad instrumental.

## Episodios y métricas

- Selección de episodios exclusivamente por IDW, umbral descriptivo 1 mm/día.
  Unir días húmedos separados por como máximo un día seco. No es un umbral de
  infiltración; no eliminar del cálculo la lluvia inferior a 1 mm.
- Exigir dos días previos <1 mm y tres días posteriores <1 mm, todos conocidos.
  Recarga neta: fin+1 menos inicio−1; sensibilidad fija fin+3, sin buscar máximo.
- Secado: desde fin+3 hasta fin+8; todos esos días posteriores secos y total de
  lluvia IDW entre fin+4 y fin+8 ≤1 mm. Ventana fija de cinco días. No se exige
  que las sondas desciendan: eso seleccionaría el resultado deseado.
- No usar un episodio si hay huecos del perfil dentro del intervalo comparado.
  Los cuatro candidatos deben tener exactamente la misma cobertura por métrica.
- Error firmado = cambio modelado − cambio reconstruido. Secado usa pérdida
  positiva = estado inicial − final; error positivo significa pérdida excesiva.
- Informar MAE, sesgo, pérdida/día, amplitudes observadas y modeladas; primero
  media por estación, después mediana entre estaciones, sin favorecer las que
  tienen más episodios. También cambios diarios consecutivos (sin cruzar huecos).
- Lluvia medida solo diagnóstico: anotar discrepancias y subconjunto de secado
  con pluviómetro completo y suma ≤1 mm, sin sustituir el IDW de los modelos.
- Conservar estaciones/episodios excluidos y razones. Sensibilidades de perfil
  y tiempo se comparan sobre la misma intersección de casos cuando se contrasten.

## Decisión y trazabilidad

Mantener como referencia regulada + ET nueva + una capa salvo evidencia robusta
y físicamente comparable; no convertir un ganador de residuos condicionados en
modelo validado. La muestra ya fue inspeccionada: no es evaluación ciega.
Registrar huellas, cobertura y pasos pendientes. Pruebas de conversión/integración,
cobertura temporal, segmentación y correspondencia exacta de candidatos.

Fuentes: [FAO, mediciones de humedad, ecuaciones 6 y 10](https://www.fao.org/4/t0231e/t0231e05.htm)
y fichas ICGC en `../baseline-2026-09-19/station-metadata.json`.
