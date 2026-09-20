# SMI-06 · Cuánto recarga y cuánto pierde la reserva

Ejecutado offline el 20/09/2026. **Mantener provisionalmente la referencia
regulada + ET nueva + una capa; sus litros todavía no están validados.**
La evaluación de cantidades no confirma un ganador único: dos capas mejora
algunas recargas, Hargreaves algunos secados, y la clasificación depende de
la métrica y de cómo reconstruimos el perfil observado.

No se han modificado los cálculos del mapa, HA real, worker, imágenes ni datos
operativos. Se reutilizan los datos ya archivados, sin nuevas descargas.

## Qué se ha comparado realmente

Se reconstruye agua total de **0–30 cm**, con sondas de 5/20/50 cm, y se compara
su cambio con el cambio de agua disponible de los cuatro candidatos regulados.
Los cálculos reciben la misma lluvia IDW y la misma capacidad que en SMI-05.
Se conserva la historia de 365 días usada allí; no reiniciamos el depósito en
cada episodio. El análisis abarca 21/07–18/09/2026.

Agua total y agua disponible no son el mismo valor. Restar dos fechas elimina
un nivel constante de agua no disponible **solo dentro de los límites de
marchitez/capacidad de campo**. Sin esos límites volumétricos por horizonte,
las diferencias de este informe son **residuos condicionados**. No equivalen
a un error certificado del SMI ni permiten afirmar que sus litros restantes
sean correctos. No se han recortado ni normalizado artificialmente las sondas.

El perfil principal interpola linealmente entre sondas, constante de 0 a 5 cm,
e integra hasta 30 cm. Pesos: 125, 158⅓ y 16⅔ mm. La sonda a 50 cm ayuda a
interpolar 20–30; no implica calcular un depósito de 50 cm. Se repite con dos
integraciones alternativas y con media diaria frente a lectura exacta 23:30.
El [protocolo previo](PROTOCOL.md) contiene filtros y fórmulas.

## Cobertura y viabilidad de una referencia absoluta

- 22 estaciones, 1.320 fechas. Perfil principal disponible: 60 días en 16
  estaciones; Clot 15, Bolvir 33, Clarella 51, Borda 55, Coll de Paller 56,
  Pessonada 58. Se mantienen visibles las estaciones incompletas.
- 1.206 cambios diarios consecutivos, 68 recargas comparables de 21 estaciones
  y 27 ventanas de secado de cinco días de 21 estaciones. Para secado confirmado
  por pluviómetro quedan 24 ventanas de 18 estaciones.
- La selección detectó 73 episodios IDW admisibles antes del filtro de sondas.
  Los episodios IDW no son los mismos grupos definidos con pluviómetro en SMI-04.
- **Cero estaciones con reserva disponible absoluta validada a partir de estos
  archivos.** Las fichas archivadas muestran retención gravimétrica; falta
  confirmar densidad aparente apropiada, retención completa por horizonte,
  piedras, calibración de las sondas y correspondencia del perfil con ellas.
  Esto no afirma que no existan esos datos en otras fuentes.
- Batlliu merece una revisión específica: la ficha examinada da retención
  28/16% gravimétrica solo para 0–12 cm, sin valores en C 12–25 y roca desde
  25 cm. No se extrapolan esos números a 30 cm. La presencia de sondas más
  profundas exige comprobar cómo se relacionan ambos emplazamientos.
- El inventario conserva los canales adicionales publicados. No se aprovechó
  una profundidad extra de una sola estación para cambiar el método general.
  No se ha confirmado zona horaria ni calibración instrumental; 23:30 es la
  hora publicada, no una coincidencia UTC demostrada.

## Diferencias de magnitud

Caso principal: perfil lineal, lectura 23:30. Cada estación tiene igual peso:
media de errores absolutos de sus casos y después mediana entre estaciones.
Todos los candidatos usan exactamente los mismos casos de cada fila.
Valores en L/m²; **menor residuo es mejor dentro de esta comparación condicionada**.

| Candidato regulado | Cambio diario (22 est.) | Recarga hasta día siguiente (21) | Recarga hasta día +3 (21) | Pérdida en 5 días (21) |
|---|---:|---:|---:|---:|
| Hargreaves · una capa | 1,04 | 4,68 | 3,35 | 1,38 |
| Hargreaves · dos capas | 1,09 | 4,31 | 3,60 | **1,12** |
| ET nueva · una capa | **1,03** | 4,55 | **3,25** | 1,69 |
| ET nueva · dos capas | 1,08 | **4,18** | 3,31 | 1,64 |

La referencia presenta un sesgo mediano por estación de **+2,49 L/m²** en la
recarga hasta el día siguiente y **+1,33 L/m²** en la pérdida a cinco días.
Los signos indican incremento o pérdida calculados excesivos, respectivamente.
No es un sesgo de los litros absolutos restantes. En los secados confirmados
por pluviómetro, el sesgo de pérdida sigue siendo positivo: **+1,19 L/m²**.
No se atribuye automáticamente a ET: también intervienen lluvia previa,
capacidad, integración de sondas y otros flujos no representados.

No hay una victoria uniforme por estaciones. Aunque la referencia gana la
mediana de error diario, dos capas con ET nueva reduce ese error en **15/22**
estaciones; su mejora pareada mediana es solo **0,009 L/m²**. En recargas,
dos capas con Hargreaves mejora frente a la referencia en **19/21**, con una
reducción pareada mediana de **0,44 L/m²**. En secado, ambos modelos de dos
capas mejoran en **17/21**, pero su estructura perdió recargas profundas en
SMI-04. No ocultar estos resultados favorables y adversos.

## Sensibilidad: cuánto depende de la forma de comparar

Las seis variantes de perfil × horario se contrastan sobre idénticos casos,
sin elegir la referencia que beneficia al modelo. Rangos de la mediana de MAE:

| Candidato | Diario | Recarga día +1 | Recarga día +3 | Secado 5 días |
|---|---:|---:|---:|---:|
| Hargreaves · una | 1,04–1,39 | 4,68–4,94 | 3,09–3,80 | 1,27–1,41 |
| Hargreaves · dos | 1,09–1,41 | 4,20–4,66 | 3,44–3,82 | 1,12–1,42 |
| ET nueva · una | 1,03–1,38 | 4,55–5,13 | 3,11–3,92 | 1,55–1,78 |
| ET nueva · dos | 1,08–1,40 | 4,18–4,72 | 3,21–3,72 | 1,55–1,85 |

Son rangos de escenarios, **no intervalos de confianza**. La referencia conserva
el primer puesto diario en las seis variantes. Dos capas gana recarga día +1,
pero cambia la ET ganadora. En recarga día +3 cambia también la estructura.
Hargreaves gana el secado en las seis variantes (cinco con dos capas, una con una).
Por tanto no es defendible declarar superioridad general de Penman–Monteith en
cantidades a partir de estas estaciones.

## Ejemplos que explican el problema

Siempre perfil principal y referencia regulada/ET nueva/una capa:

| Estación / intervalo entre estados | Cambio reconstruido | Cambio calculado | Lectura |
|---|---:|---:|---|
| Batlliu, 10–13 agosto | +9,42 L/m² | +20,88 L/m² | El modelo recarga mucho más, aunque la lluvia IDW del intervalo es menor que la medida: 37,50 frente a 53,10 mm |
| Batlliu, 23–25 agosto | +8,03 L/m² | +0,50 L/m² | IDW 3,20 frente a 37,70 mm medidos; el modelo recibe mucho menos agua |
| Batlliu, 27 agosto–1 septiembre | pérdida 5,39 L/m² | pérdida 5,87 L/m² | Buen acuerdo en ese secado concreto; ambas lluvias cero |
| MDF, 27 agosto–1 septiembre | pérdida 1,13 L/m² | pérdida 13,74 L/m² | Discrepancia grande en secado, ambas lluvias cero; requiere revisar entradas anteriores, capacidad y referencia instrumental |

No interpretar la reconstrucción de Batlliu como medición exacta de todo el
perfil: véase la discrepancia de horizontes indicada arriba. Estos ejemplos
permiten localizar fallos, no separar automáticamente sus causas.

## Decisión práctica y siguiente trabajo delimitado

1. **Mantener provisionalmente la referencia actual.** Las cantidades sí pueden
   cambiar la decisión, como anticipó el usuario; este ensayo muestra que su
   ventaja de correlación no se convierte en ventaja para todas las cantidades.
2. No calibrar litros a estos residuos todavía: falta una referencia volumétrica
   compatible con agua disponible. No reducir ET a mano para que una estación
   encaje ni cambiar a dos capas solo porque pierde menos en estos intervalos.
3. Siguiente comprobación útil: recuperar los FC/WP **ya estimados** usados para
   la capacidad en esos puntos y conservarlos por horizonte. Permitiría saber
   dónde las sondas estarían por debajo de WP o sobre FC según SoilGrids y
   construir una comparación **condicionada a esos umbrales**, etiquetada como
   tal. No validaría independientemente SoilGrids. Preferir caché local; no
   consultar ni modificar HA real/worker. Aún no ejecutado en SMI-06.
4. Para validación independiente de litros restantes, buscar metadatos públicos
   de densidad/retención y calibración por estación, empezando por perfiles
   completos. Esta pasada no ha hecho una búsqueda exhaustiva de esos datos ni
   contactado a ICGC. Si no aparecen, declarar la limitación y no prolongar
   indefinidamente una validación absoluta imposible con estos archivos.
   La [búsqueda complementaria](sources.md) localizó una pista adicional:
   sondas de potencial hídrico incorporadas a la red según la descripción de
   Torre Lluvià de 2024. Falta comprobar canales y cobertura, sin descargarlos
   masivamente. Se encontró también evidencia histórica de calibración de la
   red, pero no los coeficientes o controles de cada serie de este periodo.
5. Cualquier ajuste futuro debe evaluarse en otro periodo reservado antes de
   ajustar: estas 22 estaciones y este periodo ya fueron inspeccionados.

## Reproducción y archivos

```sh
.venv/bin/python docs/mushrooms/SMI/storage-2026-09-20/test_audit.py
.venv/bin/python docs/mushrooms/SMI/storage-2026-09-20/audit.py
```

Cinco pruebas pasan: conversión uniforme y cambio de 9 litros, integral de
perfil lineal conocida, cobertura/lectura final y duplicados, huecos internos,
segmentación de episodios. La ejecución verifica huellas previas y cobertura
idéntica de los cuatro candidatos. No vuelve a simular ni entrenar modelos.

- `inventory.csv`: cobertura por perfil, horario y canal; impedimento absoluto.
- `series.csv.gz`: 1.320 filas, reservas calculadas y perfiles reconstruidos.
- `episodes.csv`: 73 episodios IDW antes de exigir cobertura de sondas.
- `changes.csv.gz`: 32.856 filas = cuatro candidatos × perfiles/horarios/casos;
  **no son 32.856 observaciones independientes**.
- `excluded.csv.gz`: ventanas/casos descartados y razones.
- `station-metrics.csv`: errores por estación, sensibilidad y control de lluvia.
- `summary.json`: agregados, cobertura y SHA-256 de entradas, protocolo y código.
- `process.md`: recorrido, verificaciones y aclaración sobre HA local.

Este informe distingue datos archivados, hipótesis de integración y limitaciones
no resueltas. Fuente metodológica: [FAO, mediciones de humedad](https://www.fao.org/4/t0231e/t0231e05.htm).
