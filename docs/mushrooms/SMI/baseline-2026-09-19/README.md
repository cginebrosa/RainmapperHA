# SMI-03 · Auditoría ampliada: 22 estaciones y separación de factores

Ejecutada el 19/09/2026. [Protocolo previo](PROTOCOL.md),
[gráficas interactivas](comparison.html), [tabla por estación](station-results.md).

## Conclusión práctica

La ventaja de la extracción regulada no se limita a Batlliu: aparece en buena
parte de la muestra. Pero sigue fallando en varios lugares y su concordancia
con los cambios diarios es mucho menor que con las tendencias generales.

Estos resultados apoyan mantener la extracción regulada como hipótesis de trabajo.
**No validan los litros disponibles, la evapotranspiración real ni los bosques.**
La descripción oficial del ICGC sitúa esta red en viñedos. Aumentar su tamaño no
elimina esa limitación de representatividad.

El paso hacia un prototipo por capas sigue siendo razonable como experimento,
pero esta auditoría no demuestra que las capas resuelvan los desacuerdos. No se
ha implementado todavía ni se han cambiado parámetros o modelos operativos.

## Qué se ejecutó

- Cálculos locales en las 22 coordenadas de las fichas oficiales, con 365 días
  de historia hasta 18/09/2026. Evaluación de 21/07 a 18/09: 60 días.
- Cuatro combinaciones: depósito simple o regulado, con ET₀ anterior (Hargreaves)
  o nueva (Penman–Monteith con las aproximaciones del código del mapa).
- En 17 estaciones con lluvia completa, otras cuatro combinaciones reemplazando
  solo los 60 días recientes de IDW por el pluviómetro. Historia anterior idéntica,
  todavía IDW. No se rellenaron huecos con ceros.
- 1.320 filas diarias y 468 comparaciones de modelo/profundidad. Algunas métricas
  son indefinidas por curvas constantes o por no alcanzar 30 pares válidos.
- Referencias a 5 y 20 cm; 50 cm como contexto. No se transformó VWC en SMI.
- Parámetros fijados, sin entrenamiento ni ajuste a las observaciones.

## Resultados

Comparación directa del cálculo anterior con el regulado actual, usando IDW:

| Referencia | Estaciones con r definido en ambos | Mayor r con regulada | Mediana r anterior / regulada, mismas estaciones |
|---|---:|---:|---:|
| Sonda 5 cm | 19 | 17 | 0,371 / 0,723 |
| Sonda 20 cm | 20 | 16 | 0,236 / 0,579 |

No interpretar «mayor r» como aceptación física ni 17/19 como tasa de acierto.
Una correlación puede mejorar y seguir siendo negativa. Los casos con r indefinido
se conservan en CSV y gráficas: en Ribera de Sió y Vilosell, por ejemplo, la
referencia simple a 20 cm no permite calcular r por su curva constante.

El regulado actual tiene correlación negativa a 20 cm en **seis estaciones**:
Ribera de Sió, Camí dels Nerets, Cantallops, Aguilar de Segarra, Pobla de Cérvoles
y Vilosell. No se han eliminado del balance de resultados.

### Separar extracción y ET₀ cambia la interpretación

- Manteniendo la ET₀ nueva, el regulado supera al simple a 20 cm en 15 de 19
  comparaciones definidas; mediana de la diferencia de r: +0,253.
- Manteniendo el regulado, cambiar de Hargreaves a ET₀ nueva mejora r a 20 cm
  en 12 de 22 estaciones; mediana de la diferencia: **+0,003**. Esta muestra no
  demuestra una ventaja general clara de la fórmula nueva a esa profundidad.
- La comparación de depósitos incluye también su distinto orden de drenaje y
  extracción. No atribuir toda la diferencia solo al coeficiente de estrés.

La mediana de r de los **cambios diarios** del regulado actual frente a 20 cm es
solo 0,163, aunque varias tendencias generales se parezcan. Por eso no basta con
optimizar una curva suave o la correlación del periodo completo.

### La lluvia importa, pero no explica todos los fallos

Con el regulado y ET₀ nueva fijados, sustituir la lluvia reciente por el pluviómetro
mejora r a 20 cm en 10 de 17 estaciones; mediana de la diferencia de r: +0,020.
La mediana de r del grupo pasa de 0,422 a 0,690. La diferencia entre medianas no
es la mediana de diferencias: los resultados individuales son heterogéneos.

Ejemplos del mismo regulado, IDW → lluvia medida:

- Clot de les Peres: 0,422 → 0,690.
- El Boixer: 0,420 → 0,715.
- Batlliu: 0,805 → 0,840.
- Aguilar de Segarra: −0,068 → −0,242; empeora y no encaja.

En Batlliu, con lluvia medida, el simple + ET anterior alcanza r=0,881 y supera
al regulado + ET nueva (0,840). **El éxito relativo inicial en Batlliu no basta
para atribuir la mejora a un único mecanismo.**

Estos números comparan las fechas publicadas, sin desfase optimizado. La
ambigüedad de zona horaria y la agregación diaria limitan la interpretación de
respuestas rápidas. No se infiere un umbral universal de lluvia ni un tiempo fijo
de infiltración a partir de estas correlaciones.

## Control de datos y limitaciones descubiertas

### Coordenadas y perfiles

Se consultaron las 22 fichas PDF oficiales enlazadas por el visor. Se conservaron
URL, SHA-256, texto extraído y coordenadas en `station-metadata.json`. Los PDF
temporales se eliminaron tras la extracción para no acumular descargas.

Se transformaron las coordenadas UTM ETRS89 de las fichas (zona 31N, como indica
el visor). Todas coinciden con los marcadores publicados dentro de 40,42 m.
Se usaron esas coordenadas de ficha y no los campos X/Y duplicados del GeoJSON.
La ficha de Batlliu se inspeccionó visualmente; las demás coordenadas OCR se
contrastaron con los marcadores. No se ha inspeccionado visualmente cada horizonte
de las 22 fichas ni convertido automáticamente su retención gravimétrica a volumen.

La altitud DEM utilizada difiere menos de 30 m de la publicada en todas las fichas.
El perfil descrito en una ficha no garantiza que una celda SoilGrids represente
exactamente la instalación de las sondas. Las capacidades siguen siendo las del mapa.

### Calidad de sondas

La cobertura preliminar del inventario aceptaba numéricamente ceros. En este
contraste se conservan en evidencia pero se censuran como valores dudosos:

- **Clot de les Peres, 5 cm:** 2.046 registros cero; quedan 15 días con cobertura
  suficiente. No se calcula r a esa profundidad. A 20 cm hay 60 días válidos.
- **Bolvir, 20 cm:** 1.260 registros cero; quedan 33 días con cobertura suficiente.
  Se calcula r con esos días y se muestra la limitación, sin rellenar el resto.
- Clarella tiene 51 días completos: se conserva como comparación exploratoria.

Por tanto, las 22 estaciones no son 22 réplicas de igual calidad o independencia.
No se conocen aquí calibración instrumental, historial de mantenimiento, riego ni
zona horaria confirmada para cada estación. No se atribuye causalidad a una curva
adversa sin revisar esos factores.

## Verificación y reproducción

Las huellas de los cinco módulos relevantes del contenedor local coincidieron con
el código del repositorio. Se archivaron únicamente los tres módulos de física
necesarios para repetir este cálculo offline, en `snapshot/rainmapper_core`.
No son otra implementación activa ni una imagen Docker.

`analyse.py` comprueba al ejecutarse:

- Huellas de la física archivada frente a las de la exportación.
- Fechas consecutivas, 365 días, timestamps únicos y días completos de lluvia.
- Paridad de las 22 series de ET₀ y de ambos SMIs reconstruidos con la salida
  efectiva del mapa local, dentro de su redondeo de publicación.
- Reserva entre 0 y capacidad, convergencia entre estados iniciales extremos y
  conservación de masa inferior a 1e-7 mm en las simulaciones.
- No unir diferencias diarias a través de huecos ni crear observaciones de cero.

Desde la raíz del repositorio:

```sh
.venv/bin/python docs/mushrooms/SMI/baseline-2026-09-19/analyse.py
```

Regenera CSV, resumen y HTML sin red ni contenedores. `local-inputs.json.gz` contiene
las entradas locales; las observaciones externas se referencian desde el ensayo
anterior para no duplicarlas. `export_local.py` es la receta de exportación original:
requiere anteponer `POINTS` con name/code/lat/lon de `station-metadata.json` y ejecutarse
en HA local. No repetir exportaciones para consultar los resultados ya guardados.

El HTML se revisó en Chrome sin interfaz. Una primera disposición de 22 pestañas
desbordaba el ancho; se sustituyó por un selector de estación.

## Decisión y siguiente ensayo

Conservar el regulado como referencia experimental y ensayar una estructura por
capas manteniendo ET₀ y entradas fijadas, si se continúa. Evaluar recarga y secado
por episodios, sin descartar lugares donde no encaja. Revisar primero las sondas
con ceros y evitar ajustar una capa superficial contra una sonda averiada.

Para validar el bosque harán falta referencias adecuadas de ese entorno. Para
declarar mejora de un modelo ajustado harán falta estaciones o periodos reservados;
este conjunto ya se ha inspeccionado y no debe presentarse como una prueba ciega.

Fuentes: [visor XMS-Cat](https://visors.icgc.cat/mesurasols/), fichas oficiales
individuales enlazadas en `station-metadata.json`,
[descripción de la red ICGC](https://www.icgc.cat/es/node/23771).
