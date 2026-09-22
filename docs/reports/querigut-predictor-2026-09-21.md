# Querigut, IFF 99–90 de deliciosus — HA real, 21/09/2026

## Fuente real comprobada

El análisis usa el precálculo **activo de HA real**, leído por SMB desde
`/Volumes/media/rainmapper/results/predictor-precompute/active.sqlite3`.
Se copió a diagnóstico privado local, verificando SHA, tamaño, recibo y estabilidad
del archivo durante la lectura. No se utilizó el precálculo del HA local.

- Revisión del recibo: **211**, distinta de la 210 revisada antes.
- Tamaño: 45.510.656 bytes.
- SHA del archivo: `a9aa1973ee5ad6e2b45b467c34c785355257dba6fa3f6479820d6db8c2c5a7fb`.
- Artefacto: `sha256:25f79c9d3c79d9bc7f37453c93907c4c92570ea3de848236d4de54fdeac42c71`.
- Lote de modelos: `operational_20260921T134830Z`, el mismo lote nuevo usado
  en la auditoría de cinco especies y simulaciones del filtro.

El usuario confirma que en HA local no ha entrenado ni precalculado estas entradas.
Los análisis offline se ejecutan en el Mac con artefactos copiados y verificados
de HA real. Esta distinción debe mantenerse al explicar los resultados.

## Qué reproduce exactamente la captura

Especie `lactarius_deliciosus`, área `querigut`. Seleccionado Elastic Net V5w,
ventana de 60 días, contrato `lag_event_biology_v5_raw365_v2`, perfil
`raw_window_60d_plus_physical_state`. El mismo modelo durante la semana.

| Fecha | IFF sin redondear |
|---|---:|
| 21/09 | 98,7779 |
| 22/09 | 98,2507 |
| 23/09 | 97,5028 |
| 24/09 | 96,4480 |
| 25/09 | 94,9723 |
| 26/09 | 92,9309 |
| 27/09 | 90,1498 |

Se reprodujeron los siete valores con los pesos verificados y las features
**ya persistidas** en HA real, mediante el lector de inferencia oficial. No se
reconstruyó meteorología, estado hídrico o runtime, ni se entrenó o precalculó.
El 99 es redondeo de 98,7779, no un error aritmético de presentación.

Los siete resultados comparten corte meteorológico 20/09. Las entradas que
cambian son horizonte y seno/coseno de fecha objetivo; la metadata de edad de
lluvia también avanza. La edad de lluvia no forma parte de las 310 columnas de
este modelo. La curva descendente no representa nueva meteorología pronosticada
para cada día de esa semana.

## Por qué se eligió este modelo

La selección persistida identifica el mejor clasificado por evidencia agregada
como **Extra Trees V3 físico**, pero el modelo servido es **el décimo** de la
clasificación de calidad. Política persistida:
`maximum_weekly_coverage_then_aggregate_evidence`; la familia elegida cubre 7/7
días. Por tanto, la cobertura operativa se prioriza antes que la posición de
calidad histórica. No se elige simplemente el primer modelo de la auditoría.

Para h1, la evidencia decisiva es global de especie: **6 aciertos entre 8 llamadas
favorables**, 18 observaciones de prueba, 15 grupos. Límite Wilson inferior
0,4093. No hay evidencia de validación específica del área (`area: null`).
La salida persistida etiqueta el soporte estadístico como `limited` y la
confianza de interpretación como `moderate`, aunque la puntuación sea 99.

La rama técnica del miembro contiene otra evaluación, split de 7 días y 19
observaciones; no confundirla con la evidencia decisiva del selector (split
oficial de 14 días y 18 observaciones). La explicación al usuario debe indicar
la evidencia que realmente decide, no mezclar denominadores de ambas.

Fuente de código: `rainmapper_core/mushroom_ml_multiversion_comparison.py:613`
(`prioritize_weekly_resolutions_by_applicability`). El artefacto final conserva
el miembro elegido, no todas las exclusiones que llevaron a descartar las
familias anteriores. **No se ha demostrado la causa individual de exclusión
de las nueve familias anteriores.**

## Por qué su número es tan alto

Elastic Net es una regresión logística: combina 310 variables mediante pesos
aprendidos. La descomposición exacta del primer día reproduce el logit 4,39228,
que convertido por el modelo da 0,987779. Contribuciones agrupadas en escala
interna (no puntos de IFF ni efectos causales):

| Componente | Aportación al logit |
|---|---:|
| Intercepto aprendido, referencia de variables estandarizadas | +3,5183 |
| Temperaturas mínimas históricas | +1,8010 |
| Temperaturas máximas históricas | -1,8517 |
| Humedades mínimas históricas | +0,6479 |
| Humedades máximas históricas | +1,5090 |
| Lluvia histórica | -2,0398 |
| Horizonte h1 | +1,0808 |
| Fecha objetivo (seno/coseno) | -0,1831 |
| Variables hídricas rellenadas | -0,0900 |

Así, la lluvia acumulada de 103,63 mm en 60 días **no explica por sí sola** el
IFF alto; la suma ponderada de lluvia en este caso resta respecto a la referencia
estandarizada. El intercepto no es una probabilidad basal real de Querigut.
Algunas variables de humedad diaria tienen signos opuestos según su retardo;
no traducir sus pesos como reglas ecológicas demostradas.

Como comprobación algebraica, neutralizar las contribuciones de humedad hacia
la referencia estandarizada reduciría el IFF de 98,78 a 90,34. Esto no representa
un cambio meteorológico físicamente realizable ni una probabilidad corregida.
Las contribuciones correlacionadas no son atribuciones causales independientes.

## Siete datos hídricos ausentes

Todos los días tienen siete features físicas `None` y cero observaciones de
fracción de agua del suelo en los bloques meteorológicos persistidos. El
preprocesador usa `SimpleImputer(strategy='median')`, con valores del entrenamiento:
fracción media 0,703933, mínima 0,691099 y otros cinco resúmenes de cambio,
recarga, déficit y secado. **No son mediciones ni estimaciones específicas de
Querigut**. La inferencia declara siete features ausentes.

Su aportación directa conjunta es pequeña (-0,0900 en escala interna); no se
debe afirmar que rellenarlas explica el 99. Sí constituye una limitación relevante
para presentar una recomendación como «Óptima» sin aviso visible.

La rama V5/V6 de `build_runtime_features` marca `inference_eligible=True`; el
chequeo de rango del predictor omite valores `None`. Por ello puede aparecer
`within_observed_range` pese a que faltan esas entradas. La rama V3 físico sí
comprueba disponibilidad de estado y variables. Es una diferencia de tratamiento
que debe revisarse antes de asumir que los filtros de calidad son equivalentes.

Fuentes: `rainmapper_core/mushroom_ml_runtime_features.py:126`,
`rainmapper_core/mushroom_ml_runtime_inference.py:168` y
`rainmapper_core/mushroom_ml_biology_v3_physical.py:72`.
**La causa original de la ausencia del estado hídrico no queda identificada por
este precálculo**. No atribuirla sin más a ubicación en Francia, cobertura GIS
o falta de una estación. No se ha regenerado el estado para investigarla.

## Consecuencias para el trabajo autorizado

El usuario acepta implementar el filtro reversible y tolera inicialmente su
coste, pero pide explicar cada recomendación y revisar Querigut antes.
La explicación debe contener: familia servida, razón de selección, evidencia
decisiva y su alcance, limitaciones de datos y resultado del filtro de acuerdo.

Texto orientativo para este caso, respaldado por el artefacto:

> Usamos Elastic Net V5 porque cubre los siete días con las reglas actuales.
> No es el modelo mejor clasificado por calidad histórica. En este plazo acertó
> 6 de 8 recomendaciones evaluadas para la especie; no hay validación específica
> de Querigut. Faltan siete datos del agua del suelo y se han rellenado con valores
> del entrenamiento. El IFF 99 es una puntuación del modelo, no una garantía del
> 99% de encontrar setas.

Esta inspección confirma un límite de las simulaciones anteriores: se fijaban
las familias preferidas por evidencia, **antes** de la selección por cobertura
de cada área. En Querigut el ganador servido es distinto. El beneficio 39/10 del
filtro no se puede prometer para el selector completo sin medir ese circuito.
Además, deliciosus quedó fuera del ámbito inicial del filtro; ese filtro por sí
solo no resolvería este 99. No ampliar el ámbito silenciosamente por esta captura.

Se mantienen las observaciones GBIF pendientes de revisión fuera de la nueva
evidencia admitida. No se han importado, validado o usado como nuevas etiquetas
en esta investigación. Cuando el usuario las revise aportarán casos adicionales;
su utilidad y elegibilidad deberán comprobarse, no asumirse por su cantidad.

Evidencia privada en `tmp/querigut-review-20260921/`: copia SQLite, recibo,
`identity.json`, `members.json`, `response.json`, `decompose.py` y
`decomposition.json`. No se han modificado HA real, modelos, políticas o datos.

## Ampliación 22/09: alternativas, suelo y cobertura meteorológica

Revalidación SMB: el activo ha pasado a **revisión 212**, SHA
`1a5df5fa0c61e3689af6d0f80d505fdf54e3730d2c657dce3d1ce30d548ca60a`,
45.436.928 bytes. Copia verificada contra recibo y estabilidad del origen.
Los siete miembros de Querigut conservan exactamente modelo, entradas, IFF y
resúmenes meteorológicos de 365 días de la revisión 211. Por tanto esta
comparación sigue correspondiendo al caso actual comprobado, no a HA local.

Comparadas 33 familias del ranking semanal sellado para deliciosus, siete
horizontes, con los artefactos del mismo lote verificados por SHA. Se preparó
solo la meteorología de Querigut con los 49 objetos del snapshot verificados y
las exclusiones selladas. Reproducidas todas las columnas del modelo elegido y
los resúmenes de todos los canales/bloques persistidos. Se calculó ETo para esas
dos microáreas; **no se regeneró el estado hídrico**, ni un runtime operativo,
entrenamiento o precálculo. Se conservaron las siete variables hídricas ausentes
registradas en el resultado real. Script/resultados privados: `compare.py`,
`area-series.json`, `alternatives.json`, `members-revision212.json`.

### Causa concreta de exclusión de las nueve familias anteriores

Todos los adaptadores de las posiciones 1–9 rechazan **71/90 días de lluvia**:
requieren al menos 81. Faltan 19 días, del 29/06 al 17/07 inclusive. Las posiciones
1–3, V3 físico, además rechazan la ausencia del estado hídrico. V5/V6 admiten
la fila y rellenan ausencias; no aplican ese mismo mínimo. Es una diferencia
entre requisitos de entrada, no nueve modelos perdiendo por dar un IFF menor.

Después del último hueco quedan 65 días consecutivos hasta el 20/09. El cálculo
hídrico exige al menos 90 consecutivos y convergencia; el hueco impide cumplir
el primer requisito. Esto explica la ausencia en este contexto sin atribuirla
a una prohibición por país ni ejecutar otra simulación hidrológica.
Fuente: `mushroom_water_physics.py:159`, `mushroom_soil_water_state.py:163`.

### Qué dicen las alternativas

| Familia / posición de calidad | IFF 21/09 | IFF 22/09 | IFF 27/09 | Entradas admitidas por su adaptador |
|---|---:|---:|---:|---|
| Elastic Net V5 60d / 10, servido | 98,78 | 98,25 | 90,15 | Sí, 7 variables rellenadas |
| Elastic Net V5 90d / 11 | 88,89 | 84,71 | 46,96 | Sí, 102 variables rellenadas |
| Partial V6 90d / 12 | 61,01 | 61,50 | 63,90 | Sí, 102 variables rellenadas |
| Partial V6 30d / 13 | 55,33 | 55,72 | 57,67 | Sí, 7 variables rellenadas |
| Partial V6 60d / 15 | 56,80 | 57,15 | 58,86 | Sí, 7 variables rellenadas |

«Entradas admitidas» no significa datos completos ni certificación de calidad.
Las V6 son más moderadas y relativamente próximas, pero no mejores en todas
las métricas históricas: Brier semanal del servido 0,196 frente a 0,215–0,242
de esas tres V6 (menor es mejor); precisión media de llamadas favorables 72,2%
frente a 65,1–66,6%. No son porcentajes de acierto propios de Querigut. El V5 90d
tiene Brier 0,199 y precisión media 68,1%. No sustituir por V6 solo porque el
resultado parezca más razonable; tampoco hay consenso que respalde 99.

Se obtuvieron además salidas numéricas diagnósticas forzando los estimadores
de las familias inhabilitadas: ET físico 44,88, RF físico 44,36 y LR físico 22,81
en h1. **No son predicciones operativamente válidas**: sus adaptadores rechazan
las entradas; no usarlas como votos ni alternativas recomendables. Ni siquiera
las nueve familias mejor clasificadas coinciden: LR V3 core da 88,02 y LR V2
8,00 en esa ejecución forzada. El ranking tampoco significa superioridad en
todas las métricas: el servido tiene mejor Brier h1 que los tres primeros.

### Aclaración sobre Francia y tipos de suelo

Las dos microáreas del snapshot tienen `soilgrids_water.status=complete`,
`coverage_fraction=1.0`, capas de retención completas y sin exclusiones. Sus
listas GIS de hosts/tendencias de suelo sí están vacías. Son fuentes distintas.
Ninguna de las columnas de las 33 familias inspeccionadas incluye hosts, tipo
de suelo o pH; varias sí incluyen estado hídrico derivado de meteorología y
retención. La frase general «los modelos no usan suelo» era imprecisa.

La captura aportada por el usuario del punto 42,69311 / 2,10379 muestra capacidad
46,9 L/m² y pH aproximado 5,7; agua disponible ausente, suelo no determinado,
vegetación sin información y abstención por falta de terreno compatible.
`mushroom_map_ecology.py:291` diferencia suelo desconocido/incompatible y
comprueba hosts, altitud y pH. No atribuir esta captura a un veto genérico por
Francia, ni equiparar ese punto con las dos microáreas agregadas del Predictor.

Conclusión de decisión: el 99 está reproducido, pero no respaldado por acuerdo
de alternativas ni evidencia local suficiente para venderlo como certeza.
Revisar visibilidad y coherencia de los requisitos de datos antes de sustituir
el modelo; no activar otra familia automáticamente. No se ha cambiado selector,
filtro, política, datos privados ni despliegue.
