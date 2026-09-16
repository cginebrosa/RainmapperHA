# IFF en las interfaces de predicción

El mapa y el predictor presentan la salida del modelo como IFF (Índice de
Favorabilidad de Fructificación / Índex de Favorabilitat de Fructificació /
Index of Fruiting Favorability). Es una escala de favorabilidad relativa,
no una probabilidad calibrada ni una garantía de presencia o ausencia.

## Escala inicial de presentación

| IFF | Castellano | Català | English |
| --- | --- | --- | --- |
| 0–19 | Desfavorable | Desfavorable | Unfavorable |
| 20–39 | Poco favorable | Poc favorable | Slightly favorable |
| 40–59 | Moderadamente favorable | Moderadament favorable | Moderately favorable |
| 60–79 | Favorable | Favorable | Favorable |
| 80–94 | Muy favorable | Molt favorable | Very favorable |
| 95–100 | Óptima | Òptima | Optimal |

Estos intervalos son una convención de presentación propuesta por el usuario;
no representan umbrales validados contra observaciones. El entero mostrado
se calcula redondeando `valor * 100` al entero más próximo (mitades hacia arriba).
La categoría usa ese mismo entero. Así, 0,65 se muestra como `IFF:65/100`,
y 0,596691 como `IFF:60/100 · Favorable`.

Una salida ausente o inválida no se convierte en cero ni recibe categoría.
«Sin IFF calculado» también permite abrir la ayuda. Los intervalos entre modelos
se conservan: no se inventa un promedio. Si cruzan categorías, se muestran
las categorías de ambos extremos.

La ayuda en catalán dice: «L’IFF és un índex de favorabilitat relativa, no una
probabilitat. Un valor de 100 indica condicions òptimes segons el model, però no
garanteix que hi hagi fructificació.» Hay traducciones equivalentes en castellano
e inglés, y el acrónimo IFF se conserva.

## Alcance

El cambio afecta a presentación y textos. Los contratos JSON siguen usando
`probability`/`probabilities` con los valores originales de 0 a 1. No cambia
entrenamiento, selección de modelos, filtros ecológicos, ordenación operativa,
artefactos, transporte ni precálculo. Las métricas de precisión y demás
porcentajes de validación conservan sus unidades. No hay que regenerar mapas
o precálculos para adoptar esta presentación.

Los helpers de presentación están en `prediction-mode.js` y
`mushroom_predictor_ui.py`; las traducciones están en `mushroom_labels.json`.
Las pruebas comprueban los mismos límites y el mismo redondeo en JavaScript y
Python, incluidos valores ausentes. La prueba de navegador comprueba también
idiomas, ayuda sin cálculo y tamaños móviles.

## Validación inicial local del 16 de septiembre de 2026 (anterior a la release)

HA local reconstruido; huellas de los cuatro archivos ejecutados (JS, CSS,
etiquetas y renderer del predictor) coincidentes con el worktree. Pasaron 51
pruebas del predictor y seis dirigidas a IFF y tarjetas multiversión, además del
recorrido de navegador del mapa. La consulta real del predictor semanal local
respondió HTTP 200, indicó «Precálculo: usado» y mostró IFF con la ayuda nueva.
No se reconstruyó ni reinició el worker, ni se publicó una versión de HA real.

## Colores en el mapa

El valor IFF, su descripción y el máximo semanal usan los mismos seis tramos:
rojo, naranja oscuro, ocre, verde oliva, verde y verde oscuro. La ausencia de
cálculo mantiene el color neutro. El texto y la puntuación siguen visibles;
los colores identificativos de las especies y sus curvas no cambian.
La prueba de navegador comprueba coherencia, contraste mínimo 4,5:1 sobre
el fondo claro del popup y ausencia de desbordamiento móvil.

## Cierre de release 0.2.307

La validación inicial anterior fue seguida de reconstrucción de HA local y del
único worker existente, con paridad de 200/107 ficheros efectivos. Pasaron el
smoke final (1613 tests, 48 omitidos) y la prueba de navegador con tamaños móviles.
La imagen 0.2.307 se verificó en GHCR para amd64/arm64 tras aceptación del usuario.
Véase el [informe de release](../reports/ha-release-0.2.307.json).
