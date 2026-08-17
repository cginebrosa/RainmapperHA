# Especificación de Biology V4: agua disponible y continuidad de floradas

Estado: **IMPLEMENTACIÓN LOCAL POR FASES; NO OPERATIVO**.

El punto 1 de la fase 1 —contexto estático SoilGrids cacheado por microárea—
quedó implementado y validado localmente el 2026-08-15. El progreso verificable
se mantiene en
[`mushroom-ml-biology-v4-progress-es.md`](mushroom-ml-biology-v4-progress-es.md).
No hay integración HA/worker, entrenamiento, artefacto ni promoción V4.

Este documento convierte la revisión científica de
[`literature/fruiting-phenology/`](literature/fruiting-phenology/README.md) en
un plan reproducible para el sucesor de Biology V3. No autoriza a cambiar el
Predictor, entrenar un candidato operativo, promover artefactos, modificar HA o
el worker ni publicar una release.

La descarga, caché, alta/edición de microáreas, persistencia en `known_sites` y
transporte al worker de SoilGrids se especifican separadamente en
[`biology-v4-soilgrids-cache-contract-es.md`](biology-v4-soilgrids-cache-contract-es.md).

V4 no reemplaza todavía a Biology V3. V3 debe permanecer congelado como
referencia emparejada y sus contratos de lluvia IDW, target, calidad, altitud y
unidad de observación se heredan sin reinterpretarlos.

V4 se incorporará al registro declarativo
`mushroom-data/mushroom_ml_version_registry.json`; no reemplazará ni borrará V2
o V3. Sus benchmarks se compararán mediante el ciclo de vida descrito en
[`mushroom-ml-version-lifecycle-es.md`](mushroom-ml-version-lifecycle-es.md).
El paso de `proposed` a `candidate` exigirá implementación y benchmark; el paso
a `active` exigirá seleccionar una generación de modelos concreta con gates
superados. Diseñar V4 no cambia por sí solo la versión operativa.

## Resumen ejecutivo

Biology V4 debe responder a dos carencias concretas:

1. la lluvia acumulada no representa por sí sola cuánto agua continúa
   disponible en el suelo después de evaporación, drenaje y retención;
2. una florada es un episodio de especie y área que suele mantenerse varios
   días, no una colección de predicciones diarias independientes que puedan
   alternar arbitrariamente entre sí y no.

Las decisiones de diseño ya cerradas para V4 son:

- lluvia, Tmin, Tmax, RHmin y RHmax usan series IDW por microárea y agregación
  posterior al área; no se reducen a una estación ni al centroide. Para Tmin y
  Tmax cada lectura se corrige primero a la altitud de la microárea y luego se
  interpola. La humedad relativa no lleva corrección altitudinal;
- lluvia, temperatura, humedad relativa y estado hídrico del suelo se
  conservan como variables distintas: ninguna sustituye automáticamente a las
  demás;
- no se codifica una lluvia mínima suficiente ni un umbral universal de
  fructificación: los datos deben aprender cantidad, periodo y combinaciones;
- temperatura y humedad relativa mantienen máximos y mínimos; sus medias se
  materializan si hacen falta para auditoría o para una ecuación física, pero
  no entran directamente en `X`;
- el histórico oficial conserva observaciones por estación. Los IDW se
  construyen después, sensibles al corte, al materializar las variables del
  benchmark o predictor; un backfill no escribe valores interpolados como si
  fueran observaciones de la fuente;
- cada IDW combina Meteocat, AEMET, Meteoclimatic y Wunderground cuando la
  fuente y lectura son elegibles en ese corte. Una estación válida dentro del
  radio basta para producir valor; cantidad de contribuyentes y distancia son
  calidad separada. Las reglas visuales de MapLibre —incluido no pintar lluvia
  formada solo por ceros— no convierten el predictor en ausente;
- cada observación original continúa siendo una muestra; no se fusiona ni se
  elimina por pertenecer a una misma florada;
- las floradas y los grupos de validación son de `species_id + area_id`; el
  área no entra en `X` ni segmenta train/test en modelos distintos por área;
- los seis estimadores reciben exactamente la misma `X` dentro de cada
  especie, contrato temporal y comparación;
- una variable desactivada se sigue calculando, validando y documentando. No se
  borra ni cambia de significado para poder reactivarla posteriormente;
- cualquier humedad del suelo no medida se llama **estimada** o **índice
  hídrico**. No se presentará como porcentaje volumétrico medido ni como
  porcentaje de capacidad de campo sin calibración suficiente.

## 1. Qué permite afirmar la literatura

### Evidencia utilizable

| Hallazgo | Fuente y alcance | Consecuencia para V4 |
| --- | --- | --- |
| La precipitación fue el predictor más consistente de productividad y el número de días lluviosos añadió información sobre su distribución. | Karavani et al. 2018, comunidad de 28 parcelas de *Pinus pinaster*. | Conservar acumulados y añadir recuentos de días lluviosos por ventanas disjuntas. |
| La precipitación presentó aproximadamente un mes de anticipación y la humedad del suelo coincidió más con el inicio de fructificación. | Karavani et al. 2018, datos mensuales de comunidad. | Evaluar memoria hídrica hasta 30 días y construir un estado del suelo; no copiar un umbral. |
| Para *B. edulis*, las mejores ventanas fueron 20 días de temperatura y 26 días de precipitación; 26–32 días en dos sitios productivos. | Preprint bioRxiv 2026, diez años en hayedo de Alemania; no revisado por pares. | Activar en el benchmark la comparación 22–30 días. La cifra no se convierte en regla general ni específica para otros hábitats. |
| Máximas y mínimas revelaron efectos que las medias podían ocultar; la humedad relativa máxima aportó señal. | Karavani et al. 2018. | Mantener extremos térmicos y de humedad relativa como variables separadas. |
| El inicio depende de lluvia de final de verano y la prolongación de precipitación sostenida durante la campaña. | Ponce et al. 2023, comunidad de *Pinus uncinata* pirenaica. | Medir recarga y persistencia, no solo el total de un episodio de lluvia. |
| La fenología cambia entre regiones, años, especies y grupos tróficos. | Kauserud et al. 2008 y 2012. | No fijar calendarios rígidos ni asumir una respuesta idéntica entre especies. |

### Límites que V4 debe respetar

- Karavani reconstruyó humedad del suelo con un modelo físico alimentado por
  estructura forestal, suelo y meteorología, calibrado contra sondas a
  12–15 cm. Una parcela pedregosa no pudo modelizarse correctamente. Rainmapper
  no puede presentar una estimación sin calibrar como equivalente.
- En Karavani, los modelos de precipitación obtuvieron menor error que los de
  humedad del suelo en varias comparaciones de rendimiento. La humedad del
  suelo es un mecanismo más próximo, pero no un predictor universalmente mejor.
- El resultado 20/26 días es directamente de *B. edulis* en un hayedo
  centroeuropeo. Para el resto de especies es una ventana candidata, no una
  transferencia automática.
- Ponce y Karavani estudian principalmente comunidades o grupos comerciales.
  No justifican parámetros numéricos por especie salvo donde el resultado esté
  realmente desagregado.
- La colección no demuestra que toda florada dure exactamente 7 o 14 días.
  Esos máximos continúan como hipótesis biológica y sensibilidad de validación,
  no como etiqueta diaria inventada.
- Para *Hygrophorus marzuolus* falta una señal cuantitativa de nieve y deshielo;
  el patrón otoñal común no se le puede aplicar sin otro módulo y otras fuentes.

## 2. Alcance

V4 incluye:

1. congelar Biology V3 como referencia;
2. ampliar la memoria de lluvia hasta 30 días y representar su distribución;
3. calcular un balance climático de agua reproducible;
4. investigar un estado hídrico del suelo por microárea y agregarlo al área;
5. comparar por bloques si cada incorporación mejora la predicción por especie;
6. medir y, solo si los datos lo permiten, modelar la continuidad diaria de una
   florada;
7. conservar calidad, procedencia y limitaciones fuera de `X`.

Queda fuera de alcance hasta una autorización posterior:

- modificar los contratos V3 existentes;
- activar V4 en el Predictor;
- elegir o promover estimadores operativos;
- rellenar observaciones ausentes con etiquetas sintéticas;
- imponer un mínimo de lluvia, temperatura o humedad decidido manualmente;
- crear un modelo distinto por área;
- instalar datos o software en HA o M1;
- publicar imágenes o releases.

## 3. Genealogía e identificadores propuestos

V4 hereda sin cambios:

```text
target_contract_id: outing_value_area_v1
episode_contract_id: area_microarea_evidence_v1
quality_contract_id: observed_weather_quality_v1
rainfall_contract_id: daily_rain_idw_radius15km_power2_duplicate_zero_v2
area_rainfall_contract_id: area_daily_mean_microarea_idw_duplicate_zero_v2
```

Identificadores propuestos para congelar solo cuando sus fórmulas, fuentes y
unidades estén auditadas:

```text
soil_context_contract_id: microarea_soilgrids_water_context_v1
climatic_water_balance_contract_id: microarea_climatic_water_balance_v1
soil_water_state_contract_id: microarea_soil_water_state_v1
area_soil_water_contract_id: area_daily_soil_water_summary_v1
flush_continuity_contract_id: species_area_flush_continuity_v1
feature_set_id: fixed_gap_7d_biology_v4
feature_set_id: lag_event_biology_v4
```

Un identificador congelado nunca puede reutilizarse para otra fórmula, fuente,
ventana, inicialización o lista de columnas.

## 4. Flujo de datos previsto

```text
lluvia IDW por microárea ─┐
temperatura mín/máx ──────┼─> balance climático diario ─┐
latitud y fecha ──────────┘                              │
                                                        ├─> estado hídrico
SoilGrids: retención por profundidad e incertidumbre ──┘    por microárea
                                                                  │
                                      todas las microáreas del área│
                                                                  v
                                              resumen diario del área
                                                                  │
lluvia + temperatura + humedad relativa + estado hídrico ─────────┤
                                                                  v
                               seis estimadores por especie y contrato
                                                                  │
                                                                  v
                               probabilidad cruda + evaluación de continuidad
```

La meteorología y el estado hídrico se materializan usando únicamente fechas
iguales o anteriores al `cutoff_date` de la muestra. El mismo constructor debe
servir a entrenamiento e inferencia.

## 5. Contrato espacial

### Lluvia

La lluvia mantiene íntegramente los contratos V3:

- IDW diario por cada microárea, radio 15 km y potencia 2;
- todos los ceros observados participan;
- un `N/A` cuya causa trazable sea una repetición positiva del día anterior
  aporta `0 mm`, conforme a la decisión de calidad ya cerrada;
- otras ausencias, anomalías y estaciones retiradas no participan;
- media diaria de los IDW disponibles de todas las microáreas configuradas del
  área;
- sin estación única, sin centroide del área y sin penalizar por red de origen.

Este cambio respecto al primer prototipo queda identificado como
`daily_rain_idw_radius15km_power2_duplicate_zero_v2` y
`area_daily_mean_microarea_idw_duplicate_zero_v2`. Calidad conserva por
separado cuántos días proceden de esa imputación y nunca confunde un ausente
genérico con lluvia cero.

### Temperatura y humedad relativa

En la primera versión de V4 reutilizan el selector V2 sensible al corte.
La temperatura conserva la corrección por altitud; la humedad relativa no se
corrige por altitud. Sustituirlas por campos espaciales sería un contrato
posterior y una comparación separada.

Para las series largas necesarias por ET0 y suelo, la estación escogida por el
selector V2 sigue siendo la primaria. Si un día carece de Tmin o Tmax, se puede
usar la siguiente estación real a menos de 15 km que supere los mismos gates en
ese `cutoff_date` y disponga de altitud; su medición se corrige a la altitud del
área. La fuente diaria queda auditada. No se interpola, no se rellena con medias
y no se consulta información posterior al corte.

El balance inicial usa la misma temperatura corregida a la altitud
representativa del área que V2/V3. Corregir una segunda serie a la altitud de
cada microárea sería otra modificación meteorológica y deberá compararse bajo
otro identificador; no se introduce silenciosamente dentro del contrato
hídrico.

### Suelo estático por microárea

La consulta se realiza sobre la geometría completa de la microárea, no solo
sobre su punto representativo. Al crear o cambiar una microárea se cruzan las
capas SoilGrids locales y se cachean en `known_sites`:

```text
source_id/version y hashes de assets
geometry_hash
cobertura y píxeles válidos
wv0010/wv0033/wv1500
seis profundidades
Q0.05/Q0.50/Q0.95
estado y motivos de exclusión
```

El resultado vive en
`derived_context.soilgrids_water`. La forma exacta, invalidación, manifest,
caché compartida, alta/edición UI y transporte al worker están en
`biology-v4-soilgrids-cache-contract-es.md`.

Cambiar nombre, descripción, aliases, observaciones o perfiles no recalcula el
suelo. Cambiar la geometría sí. La creación o edición conserva errores
independientes: que falle SoilGrids no borra una altitud válida, ni al revés.
Una reconstrucción masiva produce una copia candidata y solo reemplaza
`known_sites` después de validarla y crear backup.

### Alternativa ICGC auditada y descartada como base general

El mapa ICGC `sols-25000-v1r1-202512` contiene clases de capacidad de retención
de agua (`CRAD`), profundidad y drenaje, pero su propia auditoría documenta
cobertura parcial y huecos amplios, especialmente problemáticos para áreas
forestales. Por tanto:

- sirve para auditoría y contraste en su zona cubierta, no como base operativa
  general;
- la auditoría 58/58 queda congelada en este documento y no se repite en cada
  alta;
- no se inventan milímetros de capacidad a partir de etiquetas ordinales;
- una conversión a capacidad numérica exige rangos oficiales, textura con una
  función de transferencia documentada o una calibración explícita;
- geología o sustrato pueden ser fallback descriptivo, pero nunca se etiquetan
  silenciosamente como suelo medido;
- la falta de suelo no elimina la observación del benchmark general. Solo la
  excluye de la comparación que requiera estado hídrico edáfico.

#### Auditoría real de cobertura — snapshot 2026-08-14

El cruce reproducible se ejecutó con
`scripts/audit-biology-v4-soil-coverage.py` sobre la copia local
`docker-data/mushroom-data/mushroom_known_sites.json`, sin modificarla:

```text
known_sites sha256:
ef9363a1ae3c37cdb8ed72109e925ddd7f2e508cb06e4ac35563b9ac530d2ac7

dataset edáfico compuesto sha256:
84d15b4f226ab9d3550cc53c5b39afb8a82bc3ed8cc4dfdce921954e2b6245ae
```

Las 58/58 microáreas tenían polígono y fueron cruzadas por superficie completa
en EPSG:25831. Resultado:

| Medida | Completa | Parcial | Ninguna | Cobertura ponderada por superficie |
| --- | ---: | ---: | ---: | ---: |
| Algún polígono del mapa de suelos | 5 | 1 | 52 | 8,91 % |
| CRAD + profundidad + drenaje utilizables | 2 | 4 | 52 | 8,73 % |

Superficie total auditada: 3.646,4119 ha. Detalle de las únicas seis
microáreas con alguna cobertura:

| Microárea | Mapa | Hidráulica utilizable | Lectura dominante |
| --- | ---: | ---: | --- |
| `selva_del_camp_casa_perros` | 100 % | 100 % | 99,69 % retención muy baja, suelo somero y bien drenado. |
| `selva_del_camp_mas_de_sant_josep` | 100 % | 100 % | 100 % retención muy baja, suelo somero y drenaje rápido. |
| `coll_de_la_batalla_principal` | 100 % | 98,94 % | 63,31 % muy baja/somero/rápido y 26,01 % muy baja/moderadamente profundo/rápido; 1,06 % miscelánea. |
| `el_perello_lo_burgar` | 100 % | 98,84 % | Mosaico principalmente de retención baja o muy baja, suelo muy somero y drenaje bueno, rápido o muy rápido; 1,16 % miscelánea. |
| `selva_del_camp_mas_de_la_cabrera` | 100 % | 81,68 % | Retención muy baja y drenaje rápido; 51,70 % somero, 29,98 % moderadamente profundo y 18,32 % miscelánea. |
| `els_ports_la_mola` | 9,04 % | 9,04 % | Solo una fracción pequeña cubierta; predominan retención baja, suelo somero y buen drenaje. |

Las otras 52 microáreas tienen `no_coverage` en esta fuente. El resultado
descarta usar el mapa ICGC como base general de SMI: solo permite una prueba
edáfica muy acotada y obliga a buscar otra cobertura para las áreas restantes.
El balance climático, que no requiere suelo, sigue siendo comparable en todas
las microáreas con meteorología suficiente.

### Candidato global prioritario: SoilGrids 2.0

La búsqueda de una fuente complementaria identifica SoilGrids 2.0 como
candidato prioritario para una prueba local reproducible. Es un producto global
predictivo, no una medición de cada microárea: 250 m de resolución, seis
intervalos estándar de profundidad entre 0 y 200 cm y cuantiles Q0.05, Q0.50 y
Q0.95 que permiten conservar incertidumbre. La documentación oficial publica:

- `sand`, `silt` y `clay`;
- carbono orgánico `soc`, densidad aparente `bdod` y fragmentos gruesos `cfvo`;
- contenido volumétrico de agua `wv0010` a 10 kPa, `wv0033` a 33 kPa y
  `wv1500` a 1500 kPa, expresado en unidades convertibles a mm/m;
- licencia CC BY 4.0 y acceso por WCS/WebDAV.

Fuentes primarias:

- https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
- https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html
- https://doi.org/10.5194/soil-7-217-2021
- https://doi.org/10.1016/j.iswcr.2023.01.001

El primer cálculo candidato de capacidad disponible por capa es conceptual:

```text
available_water_mm[layer] =
    max(0, water_at_field_capacity - water_at_wilting_point)
    * layer_thickness_m
    * correction_for_coarse_fragments
```

Para suelos donde 10 kPa represente mejor la capacidad de campo que 33 kPa se
compararán explícitamente ambas variantes; no se elegirá una por tipo de roca.
La suma vertical se publica inicialmente para varios espesores fijos, por
ejemplo 0–30, 0–60 y 0–100 cm. No se elige una profundidad desde la cobertura
vegetal ni se supone que todo el perfil hasta 2 m esté disponible para el
hongo.

SoilGrids debe clasificarse como `inferred`, porque sus capas son predicciones
globales obtenidas mediante ML. La propia documentación advierte que está
orientado a escalas globales/continentales y que no debe tratarse como verdad
de parcela. Por ello V4 exige antes de usarlo:

1. auditar cobertura real de las 58 geometrías usando polígonos completos y no
   centroides;
2. descargar/cortar localmente solo la extensión necesaria mediante WCS o
   WebDAV y no depender del REST beta durante predicción;
3. cachear media, rango espacial, Q0.05/Q0.50/Q0.95 y número de píxeles por
   microárea, profundidad y propiedad;
4. comprobar unidades y cierre vertical con casos manuales;
5. contrastar sus valores en las seis microáreas donde existe contexto ICGC y
   contra el balance climático;
6. conservar la versión, licencia, cita y hashes de todos los recortes.

#### Auditoría parcial real: mediana 0–5 cm

El 2026-08-14 se descargaron mediante WCS tres recortes temporales de Q0.50 para
`wv0010`, `wv0033` y `wv1500`, con resolución nativa de 250 m y extensión que
contiene las 58 microáreas. El cruce ponderó el área exacta de cada polígono
dentro de cada píxel, no usó centroides. Resultado:

| Medida | Resultado |
| --- | ---: |
| Microáreas auditadas | 58 |
| Cobertura completa en las tres capas | 58 |
| Cobertura parcial/sin cobertura | 0 / 0 |
| Agua disponible Q0.50, 33–1500 kPa, solo capa 0–5 cm | 5,710–9,733 mm |
| Agua disponible Q0.50, 10–1500 kPa, solo capa 0–5 cm | 9,823–13,388 mm |

El detalle por microárea, hashes de geometría y de cada GeoTIFF, número de
píxeles y medias ponderadas queda congelado en
`docs/mushrooms/biology-v4-soilgrids-topsoil-audit-2026-08-14.json`. Se reproduce
con `scripts/audit-biology-v4-soilgrids.py`. Los GeoTIFF fueron material
temporal de auditoría en `/private/tmp`; no se incorporaron al repositorio, HA
ni M1.

Esta auditoría 0–5 cm fue posteriormente ampliada: el snapshot del 2026-08-15
contiene las 54 coberturas de retención (tres tensiones × seis profundidades ×
tres cuantiles) para 58/58 microáreas. No incluye todavía textura, carbono,
densidad o fragmentos gruesos. Por ello el primer depósito implementado se
denomina índice de **tierra fina sin corrección por fragmentos**, nunca
capacidad total calibrada del suelo.

La European Soil Database v2 ofrece a 1 km clases de capacidad de agua
disponible, profundidad a roca/capa impermeable, textura y tipo
hidrogeológico. Puede servir de contraste europeo, pero su resolución es cuatro
veces más gruesa linealmente que SoilGrids y no será la primera fuente para
microáreas: https://esdac.jrc.ec.europa.eu/content/european-soil-database-v2-raster-library-1kmx1km

Como SoilGrids cubre las 58 microáreas en esta primera prueba, geología y MVC50
no se usan para fabricar una capacidad ausente. Conservan valor como evidencia
y posibles comparaciones futuras, fuera del SMI inicial.

Los resultados ICGC son evidencia del snapshot, no caché operativo. No se
materializan en `known_sites` para el primer SMI. El script queda disponible
para auditoría o una comparación científica posterior.

### Inferencia opcional mediante otras capas GIS

Esta alternativa queda fuera del SMI inicial tras comprobar la cobertura de
SoilGrids. Si se investiga en el futuro, no debe llamar a todos los niveles
«suelo conocido». La jerarquía sería:

1. `direct`: CRAD, profundidad y drenaje cartografiados sobre suficiente
   superficie de la microárea;
2. `inferred`: textura o perfiles de suelo permiten aplicar una función de
   transferencia publicada para capacidad de campo, punto de marchitez y
   conductividad/infiltración;
3. `proxy`: geología/sustrato, vegetación, pendiente, orientación y cobertura
   permiten aproximar permeabilidad, escorrentía, interceptación, sombra,
   profundidad radicular y velocidad de secado;
4. `none`: solo balance climático, sin depósito edáfico.

Papel de las capas auxiliares:

| Entrada | Qué puede aportar | Qué no permite afirmar por sí sola |
| --- | --- | --- |
| Tipo/textura de suelo | Capacidad de campo, punto de marchitez e infiltración mediante una función de transferencia trazable. | Humedad diaria sin lluvia y pérdidas. |
| Geología y sustrato | Prior de permeabilidad, pedregosidad y drenaje. | Capacidad exacta en milímetros. |
| Vegetación/cobertura | Interceptación, sombra, demanda evaporativa y profundidad radicular aproximada. | Tipo hidráulico exacto del suelo. |
| Pendiente | Potencial de escorrentía y drenaje lateral. | Agua almacenada sin conocer suelo y meteorología. |
| Orientación y DEM | Exposición solar, temperatura y demanda de secado. | Humedad edáfica medida. |

El nivel `proxy` solo se implementará después de documentar mappings físicos o
funciones publicadas. No se asignarán números porque «pinar» parezca seco o
«caliza» parezca drenante. Se comparará contra `climate_only` y, donde coincida
espacialmente, contra el nivel `direct`. Método, fuentes, hashes, mappings,
cobertura y confianza quedan en quality/metadata, nunca en `X`.

La auditoría geométrica local del mismo snapshot obtuvo:

| Capa auxiliar | Completa | Parcial | Ninguna | Cobertura ponderada |
| --- | ---: | ---: | ---: | ---: |
| Vegetación/cobertura MVC50 | 54 | 1 | 3 | 95,83 % |
| Geología territorial 1:50.000 | 55 | 0 | 3 | 96,39 % |

`guils_la_socarrada` tiene 86,13 % de MVC50. MVC50 y geología no cubren
`ordino_cota_2100`, `puertomingalvo_pm_arriba` ni
`puertomingalvo_mas_del_sapo`; las dos últimas sí disponen de DEM IGN y Ordino
de DEM andorrano, pero un DEM no sustituye suelo/geología/cobertura. Por tanto,
las capas actuales permiten investigar un proxy en 55 microáreas, no un SMI
edáfico homogéneo en las 58.

El primer SMI no cachea este contexto auxiliar en `known_sites` ni depende de
sus mappings. Una futura comparación que decida persistirlo tendrá contrato y
hashes independientes; no invalidará SoilGrids, lluvia ni altitud.

El resultado íntegro por microárea de este snapshot queda conservado en
`docs/mushrooms/biology-v4-gis-proxy-audit-2026-08-14.json`. Incluye para las
58 microáreas la cobertura de cada capa, `geometry_hash`, cada componente MVC50
con substrato, grupo de vegetación y composición forestal, y cada componente
geológico con código, descripción oficial, metamorfismo, protolito y fracción
de superficie. No es necesario repetir el cruce para consultar estos valores.
El fichero se regenera únicamente si cambia una geometría, una capa o el
contrato de intersección, mediante
`scripts/audit-biology-v4-gis-proxies.py`.

### Geología, cobertura y catálogos fuera del SMI inicial

La copia persistente de HA fue inspeccionada en modo lectura. A fecha del
snapshot, `mushroom_reference_catalogs.json` y `mushroom_gis_mappings.json` son
idénticos byte a byte a sus copias versionadas en `mushroom-data/`:

```text
mushroom_reference_catalogs.json sha256:
849a32954345f5cc76074602922a3bc98d7333961ba12d5c4cec248457adca86

mushroom_gis_mappings.json sha256:
891e0d4dea7a083faa77c8cfd203d7bf33b55e77895429966aaa5ec24aba6799
```

El catálogo ya contiene 18 `soil_types` y 18 `lithology_types`, y el fichero de
mappings contiene reglas revisables para geología, MVC50 y CORINE. Son útiles
para hábitat, hosts y contexto biológico, pero SoilGrids hace innecesario
convertir esas clases en propiedades hidráulicas para el SMI inicial.

La prueba de las reglas actuales contra los 53 códigos geológicos observados
en las microáreas detectó que el matching textual por subcadena no es apto para
un parámetro físico. Por ejemplo, el patrón catalán `gres` coincide dentro de
`negres`: `JCd`, cuya descripción oficial es `Dolomies negres`, recibe además
una sugerencia arenosa/silícea incorrecta. También las unidades mixtas pueden
activar tendencias incompatibles sin expresar qué fracción corresponde a cada
litología. El problema queda registrado para el laboratorio GIS, pero deja de
bloquear V4 porque:

- el SMI inicial no consume ningún mapping geológico o de cobertura;
- las reglas de texto continúan sirviendo para crear propuestas, nunca para
  asignar parámetros hidráulicos;
- el matching genérico deberá usar límites léxicos y pruebas negativas como
  `negres`/`gres` como mantenimiento independiente.

Decisión V4: no se modifica `mushroom_reference_catalogs.json` ni
`mushroom_gis_mappings.json` para calcular el primer SMI. Tampoco se introducen
coeficientes geología → agua o vegetación → agua. Los hashes anteriores quedan
solo como evidencia de qué catálogo fue inspeccionado.

### Persistencia SoilGrids en `known_sites`

Este apartado fija la decisión de dominio. El contrato técnico completo,
incluidos manifest, tiles, fallos, UI y pruebas, está en
`biology-v4-soilgrids-cache-contract-es.md` y prevalece para la implementación
operativa de la caché.

Al crear una microárea o cambiar su geometría, el mantenimiento cruza el
polígono completo con los recortes SoilGrids y guarda los valores estáticos. El
bloque candidato es:

```json
{
  "soilgrids_water_context": {
    "contract_id": "microarea_soilgrids_water_context_v1",
    "geometry_hash": "sha256:...",
    "generated_at": "...",
    "source_id": "soilgrids_2_water_retention",
    "source_version": "...",
    "source_crs": "+proj=igh +datum=WGS84 +no_defs",
    "pixel_size_m": 250,
    "source_asset_hashes": {},
    "coverage_fraction": 1.0,
    "depths": [
      {
        "depth_top_cm": 0,
        "depth_bottom_cm": 5,
        "intersecting_valid_pixels": 13,
        "area_weighted": {
          "Q0.05": {"wv0010_mm_per_m": 0, "wv0033_mm_per_m": 0, "wv1500_mm_per_m": 0},
          "Q0.50": {"wv0010_mm_per_m": 0, "wv0033_mm_per_m": 0, "wv1500_mm_per_m": 0},
          "Q0.95": {"wv0010_mm_per_m": 0, "wv0033_mm_per_m": 0, "wv1500_mm_per_m": 0}
        }
      }
    ],
    "status": "complete|partial|no_coverage|stale|error",
    "exclusion_reasons": []
  }
}
```

Se guardan los tres valores originales por profundidad y cuantíl, no solo una
capacidad ya restada. Así se puede cambiar de 33 a 10 kPa, variar el espesor del
perfil o corregir una fórmula sin volver a consultar SoilGrids. La diferencia
de cuantiles marginales no se etiqueta automáticamente como cuantíl de la
diferencia; el método de propagación de incertidumbre se versiona por separado.

El caché se invalida únicamente al cambiar `geometry_hash`, `contract_id`,
versión o hashes de SoilGrids. No depende de los catálogos GIS. El SMI diario
registra el `soilgrids_context_hash` y su propio `water_balance_contract_id`;
si cambia la fórmula, se reconstruye desde los valores SoilGrids guardados sin
repetir el cruce espacial.

La ruta de mantenimiento usa recortes SoilGrids locales y versionados para que
un alta no dependa de Internet. Los raster no se duplican por microárea ni por
área y tampoco siguen límites administrativos. Se mantiene una caché GIS
compartida que cubre la envolvente conjunta de las microáreas configuradas más
un margen, o bloques alineados equivalentes. Catalunya dejaría fuera
Puertomingalvo y España no describe correctamente Ordino; la extensión dinámica
es el contrato espacial adecuado.

Disposición candidata:

```text
/media/rainmapper/mushroom-GIS/soilgrids/
  manifest.json
  water_retention/<source_version>/<depth>/<quantile>/
    wv0010.tif
    wv0033.tif
    wv1500.tif
```

El manifiesto conserva bbox, CRS nativo, tamaño de píxel, identificadores WCS,
fecha de descarga, licencia, versión y SHA-256 de cada fichero. La caché local
de desarrollo vive bajo `mushroom-GIS/soilgrids/`, ignorada por Git; HA usa el
árbol equivalente de `/media`. Los raster no se incluyen en la imagen ni en
`known_sites`.

Los tres primeros recortes de prueba sobre la extensión conjunta ocupan entre
0,63 y 0,71 MB cada uno. Por extrapolación, las 54 capas básicas de retención
—tres tensiones, seis profundidades y tres cuantiles— estarán alrededor de
35–40 MB para la cobertura actual, pendiente de medir tras la descarga final.
No se justifica descargar España completa.

Si una geometría nueva cae fuera del recorte, una tarea controlada obtiene solo
la ampliación o bloque necesario por WCS, valida CRS, alineación, resolución,
cobertura y hash y después completa el bloque. Mientras falte, la microárea
queda con estado explícito `stale` o `error` y el SMI no confunde ausencia con
suelo seco. El worker no necesita los raster: consume los valores ya agregados
que viajan en el snapshot de `known_sites`.

Geología y MVC50 pueden seguir guardándose o mostrándose por su utilidad
biológica, pero esa es una mejora independiente: no son requisito ni entrada
del depósito hídrico V4 inicial.

## 6. Balance climático y humedad del suelo inferida

### Dos productos distintos

V4 no debe mezclar estos conceptos:

1. **Balance climático:** lluvia IDW menos demanda evaporativa estimada. Puede
   calcularse sin conocer la capacidad del suelo.
2. **Estado hídrico del suelo:** almacenamiento acotado por capacidad,
   infiltración y drenaje de cada microárea. Requiere contexto edáfico válido.

Ambos se conservan junto con la lluvia bruta para que el benchmark pueda saber
cuál aporta información y para evitar que una variable derivada oculte sus
entradas.

### Demanda evaporativa

La serie diaria actual ofrece temperatura mínima/máxima, humedad relativa
mínima/máxima, fecha, coordenadas y altitud; no ofrece de forma homogénea
radiación y viento históricos para todas las redes. La fase de auditoría debe:

1. verificar la cobertura real de cada entrada;
2. seleccionar una fórmula de evapotranspiración compatible y documentada;
3. comparar su implementación con una referencia;
4. versionar fórmula, constantes y unidades;
5. conservar sus entradas y calidad fuera de `X`.

Hargreaves-Samani es el candidato inicial cuando solo existen mínimas,
máximas, latitud y fecha. Es una decisión de ingeniería pendiente de validación,
no una conclusión de los artículos micológicos. Si dentro de una ecuación
física se calcula una temperatura media auxiliar, esa media no se expone como
predictor: `X` recibe el balance o la demanda evaporativa resultante.

#### Decisión cerrada para el contrato inicial — 2026-08-15

El contrato `microarea_climatic_water_balance_v1` usa
`hargreaves_samani_fao56_temperature_v1`. La elección se apoya en que el
histórico disponible sí ofrece temperatura mínima/máxima, fecha y latitud, pero
no radiación y viento homogéneos para todas las redes. Penman-Monteith FAO-56
continúa siendo la referencia cuando estén disponibles todas sus entradas; no
se rellenarán radiación o viento inventando climatologías locales.

La implementación sigue las ecuaciones astronómicas FAO-56 para radiación
extraterrestre diaria y aplica:

```text
Ra_mm = 0,408 × Ra_MJ_m2_d
ET0_mm_d = 0,0023 × (Taux + 17,8) × sqrt(Tmax - Tmin) × Ra_mm
balance_climático_mm_d = lluvia_IDW_mm_d - ET0_mm_d
```

`Taux = (Tmin + Tmax) / 2` es exclusivamente un término interno de la ecuación;
no se registra como predictor. La conversión `0,408` es obligatoria: aplicar
la constante de Hargreaves directamente a `Ra` en MJ/m²/día inflaría ET0 unas
2,45 veces. Las fuentes de referencia son los capítulos FAO-56 sobre
[datos meteorológicos](https://www.fao.org/4/X0490E/x0490e06.htm),
[radiación extraterrestre](https://www.fao.org/4/X0490E/x0490e07.htm) y
[ET0 con datos limitados](https://www.fao.org/4/X0490E/x0490e08.htm).

La humedad relativa mínima/máxima permanece como entrada predictiva directa de
V4. Hargreaves-Samani no la consume, pero eso no la desactiva ni la sustituye.
ET0 y balance son variables derivadas adicionales cuya aportación se decidirá
en el benchmark emparejado.

Un día sin cualquiera de lluvia IDW, Tmin o Tmax queda ausente, con motivo
legible; nunca se convierte en cero. Una ventana de balance solo se materializa
si están presentes todos sus días, evitando comparar sumas parciales con
soportes temporales distintos. Esta exigencia no elimina la observación: cambia
su elegibilidad para el bloque `climatic_balance` y conserva la fila y su razón.

La auditoría local reproducible está en
`biology-v4-climatic-balance-audit-2026-08-15.json`. Sobre 399 filas conservó
las 399, auditó 362 e identificó 37 sin eje fuente alineado mediante gates V3;
62 tenían las cuatro ventanas completas, exactamente las elegibles del mismo
snapshot V3, por lo que el cálculo no añadió pérdidas. No hubo fallos de
cómputo y el error máximo de cierre fue `4,95e-7 mm`. La ET0 diaria observada
quedó entre 0,506 y 8,009 mm/día (mediana 4,866). Estas cifras validan unidades,
cobertura e invariantes, no valor predictivo.

Mientras temperatura sea común al área, el balance es lineal respecto a la
lluvia: calcularlo sobre la media diaria de los IDW de microárea equivale a
promediar sus balances diarios. Esto conserva exactamente el contrato de
lluvia de área V3. El depósito de suelo del punto 3 no es lineal y sí deberá
calcularse primero por microárea.

### Depósito de suelo

La forma conceptual, que deberá concretarse y congelarse antes de implementar,
es:

```text
S[t] = limitar(S[t-1] + lluvia_efectiva[t]
              - evapotranspiración_real[t]
              - drenaje[t], 0, capacidad_del_suelo)
```

Cada término debe tener una única semántica y unidad. La implementación debe
publicar el cierre de masa diario y rechazar estados negativos o superiores a
la capacidad.

#### Contrato experimental implementado — 2026-08-15

`microarea_soil_water_state_v1` implementa inicialmente
`bounded_fine_earth_bucket_v1`. Para cada capa SoilGrids calcula:

```text
capacidad_tierra_fina_mm =
    (wv0033_mm_m - wv1500_mm_m) × espesor_m
```

y conserva como variantes explícitas `wv0010-wv1500`, además de los perfiles
0–30, 0–60 y 0–100 cm. La mediana `Q0.50` es la primera variante computable;
no se restan cuantiles marginales distintos ni se selecciona aún una variante
ganadora. La corrección por fragmentos gruesos figura como
`not_applied_context_unavailable`: deberá versionarse cuando `cfvo` forme parte
del contexto persistido. Ninguna de estas limitaciones se oculta en `X`.

El paso diario, sin parámetros ajustados, es:

```text
disponible = S_anterior + lluvia_IDW_microárea
ET_real = min(ET0, disponible)
resto = disponible - ET_real
drenaje = max(0, resto - capacidad)
S = min(capacidad, resto)
demanda_no_satisfecha = ET0 - ET_real
```

Esto conserva masa y acota `S` entre cero y capacidad. No simula todavía
interceptación forestal, escorrentía, raíces, vegetación o drenaje lateral. Es
un `uncalibrated_physical_index`, coherente con la literatura como experimento
pero mucho más sencillo que `medfate`: Karavani et al. usaron capas 0–30 y
30–150 cm, estructura forestal y distribución de raíces calibrada con sondas.

Cada microárea se simula antes de agregar. El área publica media, mínimo,
cambio 7/14 días, recarga positiva acumulada 7 días, déficit al corte y secado
acumulado 7 días. Las microáreas no disponibles siguen presentes en calidad;
el área usa las disponibles y solo pierde el bloque edáfico cuando ninguna
tiene un estado válido. Esto no segmenta ni elimina observaciones.

La auditoría `biology-v4-soil-water-state-audit-2026-08-15.json` usa 365 días
hasta 2026-08-11 y el snapshot combinado de 58 altitudes DEM + 58 contextos
SoilGrids. En las seis variantes, 45/58 microáreas de 20/28 áreas convergen ya
con 90 días. Las otras 13, repartidas en ocho áreas, carecen de alguna lluvia o
ET0 dentro del calentamiento; ninguna variante mostró una no-convergencia real
con entradas completas. Para `wv0033`, las capacidades de tierra fina fueron
34,81–55,96 mm en 0–30 cm y 104,11–181,42 mm en 0–100 cm. El resultado valida
motor, límites, cierre y cobertura actual; no elige profundidad ni demuestra
valor predictivo. La convergencia deberá repetirse en cada corte histórico del
benchmark, no generalizarse desde este único día.

La inicialización no puede asumir arbitrariamente suelo seco o saturado. Se
compararán periodos de calentamiento de 90, 180 y 365 días y se congelará el
mínimo que produzca convergencia suficiente en las microáreas auditadas. Los
días de calentamiento usan solo meteorología anterior al corte.

Sin calibración contra sondas, el resultado operativo del cálculo es un índice
relativo entre 0 y 1 o un almacenamiento estimado en milímetros, según el nivel
de soporte del suelo. No se denomina humedad volumétrica medida.

El informe distingue tres estados de validación:

```text
uncalibrated_physical_index
externally_checked
sensor_calibrated
```

Las invariantes físicas y una comparación con una fuente externa son
obligatorias antes del benchmark. Instalar sondas representativas no es un
requisito para construir el índice, pero sí la vía adecuada para llamarlo
calibrado y cuantificar su error local. Un producto satelital de resolución
insuficiente puede servir como contraste regional, nunca como verdad puntual
de una microárea.

La serie diaria se cachea por microárea, fecha, contrato, hashes de suelo y
meteorología. El cálculo ordinario añade días incrementalmente; una
reconstrucción completa debe producir exactamente los mismos estados. Así no se
recalcula todo el histórico cada vez que se solicita una predicción.

La reconstrucción local ya implementa el primer nivel de esta caché: filtra una
vez las estaciones a 15 km, materializa por microárea la serie IDW larga y ET0,
y extrae ventanas exactas para cada corte. La paridad con la reconstrucción
anterior se verificó por SHA en V3/V4 fixed/lag y en los seis catálogos de
suelo. La persistencia incremental entre ejecuciones y su invalidación por
hash siguen perteneciendo a la futura integración operativa.

### Agregación al área

El estado se calcula primero por microárea. Para cada día del área se guardan:

```text
soil_water_area_mean
soil_water_area_min
soil_water_area_max
soil_water_microareas_available
soil_water_microareas_total
soil_water_area_coverage_fraction
```

La media es la candidata predictiva inicial; mínimo, máximo, dispersión,
cobertura y procedencia permanecen como comparación o calidad hasta demostrar
valor. Un día sin ninguna microárea válida es ausente, nunca suelo seco.

## 7. Registro de variables V4

Cada muestra conserva la separación V3:

```json
{
  "predictive_features": {},
  "quality": {},
  "metadata": {}
}
```

### Núcleo heredado

Se conserva el núcleo activo V3:

- lluvia IDW disjunta 0–3, 4–7, 8–14 y 15–21 días;
- racha seca observada;
- temperatura máxima y mínima corregidas por altitud;
- humedad relativa máxima y mínima en ventanas disjuntas;
- `horizon_days` solamente en `lag_event`.

### Incorporaciones prioritarias del benchmark V4

```text
rain_cutoff_22_30d_mm
rainy_days_cutoff_0_7d
rainy_days_cutoff_8_14d
rainy_days_cutoff_15_21d
rainy_days_cutoff_22_30d
temp_max_cutoff_8_14d_c
temp_min_cutoff_8_14d_c
temp_max_cutoff_15_21d_c
temp_min_cutoff_15_21d_c
temp_max_cutoff_22_30d_c
temp_min_cutoff_22_30d_c
humidity_max_cutoff_22_30d_pct
humidity_min_cutoff_22_30d_pct
climatic_water_balance_cutoff_0_7d_mm
climatic_water_balance_cutoff_8_14d_mm
climatic_water_balance_cutoff_15_21d_mm
climatic_water_balance_cutoff_22_30d_mm
```

`rainy_days` significa días observados con IDW diario mayor que cero; es una
definición instrumental, no un mínimo biológico de lluvia.

Las edades son exactamente las heredadas de V3: `0_7d` abarca 0–6 días antes
del corte, `8_14d` abarca 7–13, `15_21d` abarca 14–20 y `22_30d` abarca 21–29.
La misma definición se aplica a lluvia, extremos y balance climático; el
nombre visible de la ventana no altera sus límites inclusivos.

### Variables edáficas experimentales

```text
soil_water_area_mean_at_cutoff
soil_water_area_min_at_cutoff
soil_water_change_7d
soil_water_change_14d
soil_water_recharge_7d
soil_water_deficit_at_cutoff
soil_water_drydown_7d
```

Los nombres y fórmulas finales se congelarán después del audit de suelo y del
cierre de masa. Permanecen `experimental` hasta superar una comparación
emparejada. Las clases estáticas de suelo sirven inicialmente para calcular el
estado y auditarlo; no entran automáticamente en `X`, evitando que funcionen
como un identificador indirecto del área.

### Variables que permanecen inactivas

- medias directas de temperatura y humedad relativa;
- mes seno/coseno;
- altitud directa, aunque siga corrigiendo temperatura y apoyando el balance;
- relojes heredados basados en 2 y 5 mm;
- variables posteriores a una «lluvia significativa» basada en umbral humano;
- ventanas 31–60 y 61–90 días, salvo comparación científica separada;
- cualquier campo de calidad, cobertura, procedencia o identidad.

Inactivo no significa eliminado: se materializa, prueba y documenta.

## 8. Comparaciones por bloques

No se entrenará V4 con todas las candidatas a la vez. Cada paso añade un bloque
sobre las mismas filas elegibles:

| Comparación | Contenido |
| --- | --- |
| `v3_core` | Núcleo V3 congelado. |
| `rain_30d` | V3 + lluvia 22–30 días. |
| `rain_distribution` | Anterior + número de días lluviosos por ventana. |
| `climatic_balance` | Anterior + demanda evaporativa/balance climático. |
| `soil_water_state` | Anterior + estado hídrico estimado, solo en filas con contexto válido. |
| `soil_without_raw_rain` | Diagnóstico para saber si el estado hídrico sustituye o pierde información; nunca candidato mínimo por defecto. |
| `without_temperature`, `without_humidity`, `without_rain` | Controles heredados para cuantificar la aportación de cada familia. |

Para `soil_water_state`, su comparación principal usa la intersección exacta de
filas con `climatic_balance`. El informe muestra además cuántas observaciones
quedan fuera por falta de suelo. No se atribuye al nuevo bloque una mejora
producida por cambiar la muestra.

## 9. Floradas y continuidad temporal

### Unidad

Una florada sigue siendo de `species_id + area_id`. Dos observaciones próximas
de áreas distintas no son la misma florada. Dos observaciones próximas de la
misma especie y área pueden aportar evidencia del mismo episodio, pero ambas
continúan como muestras independientes.

Los grupos de 7 y 14 días se conservan para impedir que evidencia muy próxima
cruce train/test y para representar floradas cortas/largas. No transforman diez
observaciones en un único episodio de entrenamiento ni exigen miles de nuevas
observaciones para obtener pocos ejemplos.

### Primera defensa contra el parpadeo diario

El estado hídrico es una variable con memoria y debe evolucionar gradualmente.
Antes de añadir reglas de continuidad, se comprobará si este estado reduce por
sí solo secuencias físicamente incoherentes como sí/no/sí en tres días.

El informe diario añadirá, por especie y área:

```text
isolated_positive_days
isolated_negative_days
probability_total_variation
prediction_run_lengths
observed_label_reversals
```

### Modelo de continuidad experimental

Solo si persiste el parpadeo se comparará una capa de estado
`species_area_flush_continuity_v1`. Requisitos:

- entrada: probabilidades crudas y variables meteorológicas/hídricas conocidas
  en cada fecha; nunca observaciones futuras;
- parámetros aprendidos únicamente en train;
- distinguir inicio, mantenimiento y final del episodio sin fijar manualmente
  una lluvia mínima;
- no convertir los máximos de 7/14 días en duración obligatoria;
- conservar en la respuesta probabilidad cruda, probabilidad ajustada, estado
  anterior y motivo de transición;
- una observación desfavorable real no se borra ni se reetiqueta para mantener
  una florada visualmente bonita;
- si mejora continuidad pero empeora Brier o calibración, no se activa.

Modelos de estado, suavizado o histéresis son alternativas a comparar, no una
decisión tomada por anticipado. La opción elegida deberá ser explicable y
versionada.

## 10. Particiones y evaluación

Se mantienen los dos contratos temporales:

- `fixed_gap_7d_biology_v4`: vista principal de salida semanal;
- `lag_event_biology_v4`: diagnóstico en horizontes 1, 2, 3 y 7.

`lag_event` define un solo modelo por especie y estimador. El horizonte forma
parte de `X`; no crea cuatro modelos independientes. Las métricas y el consenso
de 1/2/3/7 días se calculan filtrando las predicciones del mismo hold-out del
modelo completo, sin reentrenar por horizonte. El informe debe declarar este
método para impedir que una implementación futura multiplique el coste o cambie
silenciosamente la pregunta científica.

La evaluación mantiene:

- corte cronológico 70/30 por especie;
- grupos completos de florada de 14 días como referencia y 7 días como
  sensibilidad;
- ninguna observación eliminada o fusionada por cercanía;
- LR, RF, ET, HGB, KNN y SVM RBF calibrada sobre la misma `X` y mismas filas;
- Brier por especie, contrato y estimador frente a la prevalencia de train;
- Brier agregado entre especies solo como diagnóstico;
- log loss, calibración y consenso fila a fila entre las 15 parejas;
- hashes de fuentes, features, particiones, mappings y fórmulas.

Un bloque se propone para activación por especie únicamente cuando:

1. mejora Brier sobre filas emparejadas y no solo en el agregado;
2. el resultado mantiene dirección en grupos 7/14 y en repeticiones temporales
   razonables;
3. calibración y log loss no sufren una regresión relevante;
4. no aparece una regresión grave en una clase con soporte suficiente;
5. su aportación no depende de campos de calidad, área o identidad;
6. el soporte y los intervalos de incertidumbre se publican junto al resultado.

No se exige que una variable funcione igual en todas las especies. Sí se exige
que, dentro de la comparación de una especie, los seis algoritmos reciban las
mismas columnas. Cualquier módulo específico de especie debe tener otro
`feature_set_id`; nunca se oculta una `X` distinta bajo el mismo nombre.

## 11. Quality y metadata, nunca `X`

V4 añade como mínimo:

```text
evapotranspiration_method
evapotranspiration_input_coverage
water_balance_spinup_days
water_balance_initialized
water_balance_mass_error_mm
soil_source_id
soil_source_version
soil_coverage_fraction
soil_context_status
soil_context_exclusion_reasons
soil_water_microareas_available
soil_water_microareas_total
soil_water_area_coverage_fraction
soil_water_is_calibrated
soil_water_validation_source
continuity_contract_id
raw_probability
continuity_adjusted_probability
continuity_transition_reason
```

Método, cobertura, número de microáreas, fuente, calibración, motivos de
exclusión y probabilidad previa son calidad o metadata. No pueden entrar en
`X`. La falta de suelo no se imputa mediante una mediana ni mediante el área.

## 12. Pruebas obligatorias

### Herencia y separación

- V3 conserva IDs, columnas y fórmulas idénticas;
- lluvia V4 reproduce exactamente el IDW V3;
- temperatura/humedad seleccionan estación con el mismo corte que V2/V3;
- ninguna columna de quality, metadata, área o identidad entra en `X`;
- todas las medias meteorológicas directas permanecen fuera de `X`;
- los seis estimadores reciben columnas y filas idénticas en cada comparación.

### Suelo y balance hídrico

- cambiar la geometría invalida el caché estático; guardar sin cambiarla lo
  reutiliza;
- `no_coverage` no se transforma en suelo seco ni en una clase media;
- lluvia ausente y lluvia cero producen estados distintos;
- el balance diario cierra dentro de una tolerancia documentada;
- almacenamiento nunca es negativo ni supera capacidad;
- drenaje y evaporación no usan días posteriores al corte;
- el calentamiento solo consume historia anterior;
- reconstrucción completa e incremental producen la misma serie;
- una microárea no válida no invalida otras y la cobertura del área queda
  visible;
- si ninguna microárea es válida, el estado del área es ausente;
- train e inferencia construyen las mismas variables.

### Observaciones y floradas

- el número de observaciones originales no disminuye al crear grupos 7/14;
- los grupos nunca mezclan especie ni área;
- ningún grupo cruza train/test;
- cuatro horizontes de `lag_event` no se cuentan como cuatro observaciones
  independientes en el informe;
- la continuidad no consulta observaciones o meteorología futura;
- probabilidad cruda y ajustada permanecen auditables;
- una etiqueta observada nunca se modifica por suavizado.

## 13. Fases de implementación

### Fase 0 — auditoría y congelación previa

1. auditar cobertura CRAD/profundidad/drenaje en todas las microáreas;
2. localizar rangos numéricos o textura trazable y documentar licencias;
3. auditar cobertura temporal de entradas evaporativas;
4. seleccionar y validar fórmula de evapotranspiración;
5. medir convergencia de inicialización 90/180/365 días;
6. congelar IDs, fórmulas, mappings y ejemplos de referencia.

Salida: informe sin entrenamiento y decisión explícita sobre si existe soporte
para un depósito de suelo o solo para balance climático.

### Fase 1 — motor hídrico local

1. implementar contexto estático cacheado por microárea; **completado en local
   el 2026-08-15**;
2. implementar balance climático diario; **completado en local el 2026-08-15**;
3. implementar depósito de suelo solo si la fase 0 lo permite; **motor
   experimental completado en local el 2026-08-15; selección/calibración
   permanecen abiertas**;
4. añadir quality/metadata y cierre de masa; **completado en local el
   2026-08-15**;
5. ejecutar pruebas sintéticas y con microáreas reales, sin HA ni worker;
   **completado en local el 2026-08-15**.

### Fase 2 — benchmark V4

La comparación controlada V2/V3/V4 parte obligatoriamente de una única capa
meteorológica diaria IDW multifuente. No es válido atribuir a la biología una
diferencia causada porque V2 use una estación y V3/V4 interpolación. Para la
comparación, las tres versiones reciben las mismas series de lluvia, Tmin,
Tmax, RHmin y RHmax, las mismas observaciones, targets, cortes y particiones.
Cada versión conserva después su transformación propia de esas entradas. La V2
operativa histórica se reproduce y archiva aparte, sin reescribir su contrato.

1. crear registros `fixed_gap` y `lag_event` separados; **completado**;
2. conservar todas las observaciones y motivos de elegibilidad por perfil;
   **completado**;
3. materializar las comparaciones por bloques; **completado**;
4. verificar paridad train/inferencia y ausencia de quality en `X`;
   **ausencia de fugas cubierta por pruebas y paridad local exacta sobre
   399/1.596 muestras para core/balance/suelo; paridad de empaquetado operativo
   pendiente de la futura integración**;
5. generar informe reproducible sin artefacto operativo; **completado en local
   el 2026-08-15**.

### Fase 3 — evaluación científica y estadística

1. ejecutar los seis estimadores sobre filas emparejadas; **completado para
   grupos de 7 y 14 días**;
2. comparar por especie, contrato y grupos 7/14; **completado**;
3. medir aportación de lluvia 22–30, días lluviosos, balance y suelo; **informe,
   dirección por especie y perfiles meteorológicos separados completados**;
4. publicar calibración, Brier, log loss, consenso y soporte; **persistido en el
   archivo local, no publicado como release**;
5. mantener cada bloque activo, inactivo o experimental según evidencia;
   **todas las variantes de suelo permanecen experimentales**.

La comparación genérica V2/V3/V4 se repitió el 2026-08-16 tras reparar el
histórico y unificar lluvia, Tmin, Tmax, RHmin y RHmax IDW. Usa 350 filas
`fixed_gap` y 1.400 `lag_event` idénticas por perfil, conserva fuera de la
intersección todas las filas originales y no escribe modelos. V4 `core`
reproduce exactamente V3, que actúa como control del procedimiento. Los
perfiles ampliados muestran efectos por especie: no existe evidencia para
activar V4 como sustituto universal y no se ha calculado un Brier medio entre
especies. El consenso y la calidad de los seis algoritmos se detallan en
`docs/reports/V2_V3_V4_consensus_report001.md`.

### Fase 4 — continuidad

1. generar secuencias diarias históricas por especie y área; **completado para
   `fixed_gap` y `lag_event` horizontes 1/2/3/7, grupos 7/14 y ventanas ±14
   días del hold-out**;
2. medir parpadeo del modelo crudo; **completado para `core` y balance sobre
   filas idénticas en ambos contratos**;
3. comprobar cuánto corrige el estado hídrico sin reglas adicionales;
   **completado: el balance reduce la variación y el parpadeo global; el
   depósito `wv0033_0_30cm` no mejora y queda no seleccionado**;
4. si hace falta, comparar una capa de continuidad aprendida; **gate no
   superado: solo 50 etiquetas únicas semanales en las secuencias evaluables;
   contrato conservado pero desactivado**;
5. rechazarla si mejora apariencia pero empeora predicción observada.

### Fase 5 — integración, solo tras nueva decisión

Requiere autorización separada y gate superado: empaquetado de datos GIS,
compatibilidad HA/worker, entrenamiento de candidato, UI, promoción coordinada
y release. No forma parte del trabajo de diseño o benchmark local de V4.

Evaluación 2026-08-15: **el gate no se supera**. V4 no muestra una mejora de
Brier consistente frente a V3/V2 por especie y contrato; el balance sí reduce
parpadeo global, pero el suelo empeora continuidad. `biology_v4` permanece
`proposed`, sin entrenamiento candidato ni integración. Esta decisión no mata
la versión: sus contratos, benchmarks, informes y variables se conservan para
reevaluación.

## 14. Decisiones pendientes y cómo se resolverán

| Decisión | Quién/base | Criterio |
| --- | --- | --- |
| Fuente edáfica suficiente fuera y dentro de Cataluña | Auditoría local de cobertura y metadatos oficiales. | Cobertura real de microáreas, atributos numéricos trazables y licencia. |
| Conversión de CRAD/profundidad/drenaje a parámetros | Documentación oficial o función de transferencia científica reproducible. | No inventar equivalencias ordinales en milímetros. |
| Fórmula evaporativa | **Cerrada para V4 inicial:** Hargreaves-Samani con radiación extraterrestre FAO-56 y unidades auditadas. | Reabrir solo si radiación y viento históricos homogéneos permiten comparar Penman-Monteith sobre las mismas filas. |
| Calentamiento del depósito | Prueba 90/180/365 días. | Convergencia del estado sin usar futuro. |
| Variables que entran en `X` | Benchmark emparejado. | Brier/calibración/estabilidad por especie y contrato. |
| Necesidad de continuidad explícita | **No activada en V4 inicial:** el balance ya reduce la variación; solo existen 50 etiquetas únicas semanales para aprender estados. | Reabrir con más observaciones diarias/episódicas y exigir mejora física sin empeorar Brier o calibración. |
| Módulo de nieve para *H. marzuolus* | Revisión científica específica y disponibilidad de datos. | No reutilizar el contrato otoñal sin respaldo. |

La implementación puede tomar las decisiones técnicas reproducibles a partir
de estos criterios y dejarlas documentadas. Solo requerirán intervención del
usuario una ampliación material de datos/infraestructura, una elección de
producto visible o cualquier promoción operativa.

## 15. Criterio de cierre de V4 local

V4 local se considera técnicamente cerrado cuando:

- la inferencia hídrica tiene fórmula, unidades, fuentes, caché y calidad
  reproducibles;
- lluvia IDW, extremos térmicos y humedad relativa se conservan;
- ninguna observación se pierde por agrupar floradas;
- las comparaciones usan filas emparejadas y los seis estimadores equivalentes;
- el informe permite saber, por especie, si el mes de lluvia, su distribución,
  el balance climático y el suelo aportan o solo añaden ruido;
- la continuidad se mide y no se arregla mediante etiquetas inventadas;
- no se escribe ni promociona un modelo operativo.

Que una salida parezca micológicamente razonable no sustituye estos gates.

Estos criterios quedaron satisfechos localmente el 2026-08-15. El cierre
técnico no equivale a candidatura: el gate predictivo falló y V4 permanece no
operativa.
