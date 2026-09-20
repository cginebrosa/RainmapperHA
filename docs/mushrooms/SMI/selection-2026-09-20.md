# Elección práctica tras SMI-03/04

**Actualización:** se completaron las dos combinaciones que faltaban en
[SMI-05](factorial-2026-09-20/README.md). El [ranking de ocho](factorial-2026-09-20/ranking.md)
mantiene la recomendación de regulada + ET nueva + una capa. El texto siguiente
conserva la comparación inicial de seis alternativas y no debe presentarse como
el factorial completo.

Consulta del usuario: escoger la combinación que más se aproxima a las estaciones
disponibles, usando IDW, para avanzar hacia un SMI útil. Comparación calculada el
20/09/2026 leyendo los CSV actuales de ambas auditorías. No modifica el mapa.

**Recomendación: extracción regulada, una capa 0–30 cm, ET nueva
(Penman–Monteith con las aproximaciones actuales).** Segunda opción muy cercana:
la misma estructura y Hargreaves. No promover la cascada superficial ensayada.

## Criterio explícito de esta decisión

La recomendación prioriza representar conjuntamente superficie y profundidad.
Para cada estación se promedian los r de 5 y 20 cm con igual peso, y después se
toma la mediana entre estaciones. Es una decisión de evaluación posterior a los
experimentos, no un criterio preregistrado ni validación independiente.

Se utilizan únicamente lluvia IDW y fechas comunes de SMI-03/04. Para comparar
las seis alternativas en el mismo conjunto quedan **18 estaciones** con r
definido en ambas profundidades y todos los modelos. No imputar cero a una
correlación indefinida ni presentarlo como ranking con 22 pares completos. Los
otros resultados se conservan: Clot tiene poca cobertura a 5 cm y algunas curvas
simples son constantes. Excluirlas del ranking común no convierte esas curvas
constantes en un resultado aceptable.

| Combinación | r conjunto, mediana | r cambios diarios, mediana | Spearman conjunto, mediana |
|---|---:|---:|---:|
| Regulada · ET nueva · una capa | 0,667 | 0,204 | 0,727 |
| Regulada · Hargreaves · una capa | 0,624 | 0,188 | 0,718 |
| Regulada · ET nueva · dos capas superficiales | 0,597 | 0,167 | 0,639 |
| Regulada · Hargreaves · dos capas superficiales | 0,545 | 0,152 | 0,641 |
| Simple · ET nueva · una capa | 0,376 | 0,162 | 0,351 |
| Simple · Hargreaves · una capa | 0,321 | 0,145 | 0,354 |

«Dos capas superficiales» designa el escenario `surface` de SMI-04: 0–10 y
10–30 cm con evaporación arriba. El control `cascade` mantiene E repartida;
las variantes de espesor y bypass son sensibilidades, no modelos seleccionados.
Simple + dos capas **no se ha ensayado**: no se afirma haber comparado las ocho
combinaciones del producto cartesiano.

Al comparar únicamente las dos fórmulas de ET con regulada de una capa, hay
21 estaciones con ambas sondas utilizables. ET nueva obtiene mayor r conjunto
en 17/21, pero la mediana de la diferencia por estación es solo **+0,0093**.
La ventaja decisiva es la estructura regulada de una capa, no una superioridad
grande demostrada de Penman–Monteith. La diferencia de medianas del ranking
no equivale a esta mediana de diferencias pareadas.

## Evidencia y reproducción de la agregación

- `baseline-2026-09-19/metrics.csv`: modelos `idw_simple_hg`, `idw_simple_pm`,
  `idw_regulated_hg`, `idw_regulated_pm`; columnas `pearson`, `change_r`, `spearman`.
- `layers-2026-09-19/metrics.csv`: `forcing=idw`, `scenario=surface`, `et=hg/pm`;
  `VWC_005/upper` y `VWC_020/lower`; columnas `r`, `change_r`, `rho`.
- Para cada métrica, intersección de claves `(code, channel)` con valor definido
  en las seis alternativas; conservar estaciones con ambos canales. Promedio
  de sus dos correlaciones, después mediana de los 18 promedios. No promediar
  primero las medianas por profundidad ni mezclar lluvia medida con IDW.

Los r indican concordancia temporal, no porcentajes de acierto ni error de litros.
El resultado no valida los niveles absolutos del SMI. La muestra es principalmente
de viñedos y ya explorada; tampoco demuestra la fiabilidad en todos los bosques.
SMI-04 identifica nueve curvas inferiores casi nulas y sin recarga: sus r no deben
utilizarse solos para preferir dos capas. Ver los informes completos para casos
adversos y calidad instrumental.

Esta elección permite avanzar con un modelo de referencia concreto y mantener
sus limitaciones explícitas. No requiere activar la cascada ni esperar a terminar
una investigación de todas las combinaciones posibles.
