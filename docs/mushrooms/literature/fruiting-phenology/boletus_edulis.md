# Condiciones de fructificación y duración de florada — *Boletus edulis*

Ver fuentes completas y estado de descarga en [`README.md`](README.md). Esta ficha extrae solo lo aplicable a *B. edulis*.

## Fuente principal: preprint bioRxiv 2025 (porcini en hayedo, Europa central)

*Predicting porcini: a decade of sporocarp monitoring reveals the meteorological triggers of Boletus edulis fruiting in central European beech forests.* bioRxiv, 2025. https://www.biorxiv.org/content/10.64898/2025.12.12.693895v1 — PDF local: `boletus-biorxiv.pdf`.

Diez años (2015–2024) de monitorización casi exhaustiva de carpóforos en un hayedo (*Fagus*) cerca de Bielefeld, Alemania. No es hábitat mediterráneo ni pinar, pero es el estudio más centrado en el desencadenante meteorológico inmediato de *B. edulis* de toda la búsqueda.

- **Ventanas seleccionadas: temperatura media de los 20 días precedentes y precipitación acumulada de 26 días** para el conjunto de sitios; en los sitios productivos analizados individualmente, la precipitación seleccionó ventanas de **26–32 días**.
- **Óptimo térmico no lineal en 13,2 °C** — ni el frío ni el calor extremos maximizan la fructificación.
- Relación con precipitación aproximadamente **lineal creciente** en la ventana seleccionada, sin techo de saturación detectado dentro de las condiciones observadas en el estudio.
- Proyección: otoños más cálidos y secos → **menor fructificación** esperada.

## Fuente complementaria mediterránea: Karavani et al. 2018

Karavani, De Cáceres, Martínez de Aragón, Bonet, de Miguel (2018). *Effect of climatic and soil moisture conditions on mushroom productivity and related ecosystem services in Mediterranean pine stands facing climate change.* Agricultural and Forest Meteorology. DOI 10.1016/j.agrformet.2017.10.024. **PDF local disponible: `karavani2018-mushroom-productivity.pdf`** (manuscrito aceptado, repositorio UdL, texto completo verificado).

28 parcelas en *Pinus pinaster* del NE ibérico, muestreo semanal durante la temporada de fructificación otoñal 2008–2015. La estación meteorológica virtual de cada parcela se interpola de estaciones reales cercanas con el paquete R `meteoland` a partir de precipitación, temperatura (mín/máx/media) y humedad relativa (mín/máx/media) — el mismo tipo de variables diarias con las que trabaja Rainmapper. La humedad del suelo se mide con sondas TDR en campo (2013–2015) y se reconstruye para toda la serie 2008–2015 con un **modelo de balance hídrico de base física** (paquete R `medfate`, De Cáceres et al. 2015), expresada como % respecto a la capacidad de campo del suelo (estimada con las ecuaciones edafológicas de Saxton a partir de la textura del suelo).

- **Precipitación = predictor individual más significativo** de producción anual de setas en pinar mediterráneo, junto con el número de días de lluvia del mes (a veces más predictivo que la precipitación acumulada, porque captura también la distribución temporal, no solo la cantidad).
- **Lag de un mes exacto entre precipitación y producción**: la lluvia (acumulada y nº de días de lluvia) de un mes concreto se vuelve significativa como predictor **un mes antes** del inicio de la temporada de setas, y deja de serlo un mes antes de que termine la temporada. Es decir, el efecto de la lluvia está desplazado un mes completo respecto a la fructificación, no es un lag de días.
- **La humedad del suelo aparece como predictor significativo un mes después que la precipitación** — es decir, coincide justo con el inicio de la fructificación (encajando con la lluvia del mes anterior). Esto sugiere una cadena causal: lluvia → sube humedad del suelo con ~1 mes de desfase → fructificación.
- La **humedad relativa máxima del aire** (no la humedad del suelo) resultó significativa en el mes inmediatamente anterior a la fructificación — probablemente por su alta correlación con la precipitación de ese mes.
- Interpretación de los propios autores: el retraso se explicaría por la necesidad de que el hongo acumule primero "potencial de fructificación" antes de iniciar la formación de carpóforos (no es solo un efecto hídrico instantáneo).
- Temperaturas altas **limitan** la producción al principio de la temporada de fructificación, pero **la favorecen** hacia el final de la temporada — efecto no constante a lo largo de la campaña.
- Producción máxima en los escenarios de cambio climático solo si el calentamiento va acompañado de **más humedad simultáneamente**, no con calor solo; en los escenarios evaluados la tendencia proyectada es hacia una **elongación de la temporada de fructificación** (no un acortamiento), por el efecto combinado de más precipitación a inicio de temporada y temperaturas más cálidas al final.

## Contexto pirenaico: Ponce et al. 2023 (*Pinus uncinata*)

Ponce, Alday, Bonet, Martínez de Aragón, de-Miguel (2023). *Fungal sporocarp productivity and diversity shaped by weather conditions in Pinus uncinata stands.* Forest Ecology and Management 545:121256. DOI 10.1016/j.foreco.2023.121256. **PDF local: `ponce2023-pinus-uncinata.pdf`** (texto completo verificado).

Pinar subalpino de Meranges (Pirineo catalán, Girona), 5 años de muestreo semanal (desde junio hasta las primeras heladas) — geográficamente el más próximo al ámbito de Andorra/Pirineo de Rainmapper. Clima continental de montaña: temperatura media mínima invernal -6,4 °C, media máxima estival 23,7 °C, lluvia media anual 1039 mm muy variable entre años. No aísla *B. edulis* de otras especies ectomicorrícicas, pero sí desagrega por grupo trófico (ECM vs. saprótrofo).

- Ventana de fructificación dominante de las familias ectomicorrícicas dominantes (Russulaceae, Tricholomataceae): **mediados de agosto a finales de septiembre**. Los saprótrofos tienen ventana más amplia (mediados de agosto a finales de noviembre).
- Productividad ectomicorrícica media: **21,6 kg/ha/año** peso seco; saprótrofos **1,76 kg/ha/año**. 255 especies fúngicas registradas en total (133 ECM, 125 saprótrofas).
- **Precipitación acumulada de agosto y septiembre** afecta positiva y significativamente a la riqueza y uniformidad de especies (total, ECM y saprótrofa combinadas).
- **Precipitación de octubre** afecta positiva y significativamente a productividad y riqueza saprótrofa (no ECM).
- **Temperatura de agosto** afecta negativamente a la riqueza y uniformidad ectomicorrícica.
- **Temperatura media de noviembre** afecta positivamente a la productividad total, ectomicorrícica y saprótrofa, y a la riqueza total.
- Precipitación anual de referencia de la zona: **1039 mm**, alta variabilidad interanual.

## Nota

Complementar con la revisión previa ya existente en [`../prediction/boletus_edulis_revision_bibliografica_rainmapper.md`](../prediction/boletus_edulis_revision_bibliografica_rainmapper.md) (otras fuentes, sesión anterior) antes de fijar cualquier parámetro.
