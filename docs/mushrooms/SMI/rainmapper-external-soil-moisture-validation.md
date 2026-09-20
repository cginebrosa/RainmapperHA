# Rainmapper — Validación externa del balance hídrico y SMI en Catalunya

**Fecha de investigación:** 2026-09-19
**Objetivo:** investigar e implementar una forma de contrastar el balance hídrico / SMI calculado por Rainmapper con fuentes externas independientes para cualquier punto de Catalunya.

---

## 1. Contexto

Rainmapper ya calcula internamente variables de estado hídrico a partir de meteorología, entre ellas:

- balance hídrico;
- Soil Moisture Index (SMI) o variable equivalente de humedad disponible;
- evolución temporal del secado/humectación del suelo.

La intención de este trabajo **no es sustituir el cálculo actual**, sino disponer de una o varias referencias externas que permitan comprobar si Rainmapper está reproduciendo de forma razonable:

- la respuesta del suelo después de episodios de lluvia;
- la velocidad de secado;
- las tendencias de varias semanas;
- los periodos de estrés hídrico;
- la recuperación después de lluvia significativa;
- el comportamiento relativo entre zonas húmedas y secas.

La validación debe poder hacerse, idealmente, introduciendo una coordenada `lat/lon` de Catalunya.

---

# 2. Principio importante: no comparar números absolutos sin más

No debemos esperar que:

```text
Rainmapper SMI = Copernicus SWI = EDO SMI
```

aunque todos describan el estado hídrico del suelo.

Cada producto utiliza:

- diferentes modelos;
- diferentes profundidades efectivas;
- distintas fuentes meteorológicas;
- distinta parametrización del suelo;
- distintas escalas;
- diferentes normalizaciones.

Por tanto, el objetivo principal debe ser comparar:

```text
tendencias
eventos de humectación
eventos de secado
velocidad de dry-down
duración del estrés hídrico
posición relativa húmedo/seco
```

y sólo después estudiar si existe una transformación razonable entre escalas.

---

# 3. Fuentes identificadas

## 3.1. Copernicus Land Monitoring Service — Soil Water Index (SWI)

### Prioridad

**P0 — fuente principal recomendada para la primera prueba.**

### Producto

**Soil Water Index (SWI), Europe, daily, 1 km**

Página actual:

https://land.copernicus.eu/en/products/soil-moisture/daily-soil-water-index-europe-1km-v2

Página general de Soil Moisture:

https://land.copernicus.eu/en/products/soil-moisture

### Características verificadas

Producto actual V2:

- cobertura: Europa;
- resolución espacial aproximada: **1 km**;
- frecuencia: **diaria**;
- proyección: **EPSG:4326**;
- sensores principales: **Sentinel-1 C-SAR + Metop ASCAT**;
- latencia operacional: aproximadamente **2 días**;
- periodo V2: desde **2025-07-13 hasta actualidad**.

Producto histórico V1:

https://land.copernicus.eu/en/products/soil-moisture/daily-soil-water-index-europe-1km

- resolución: 1 km;
- frecuencia diaria;
- periodo: **2015-01-01 a 2025-07-12**;
- actualmente marcado como superseded, pero útil para histórico.

Por tanto, combinando V1 + V2 debería ser posible construir una serie desde 2015 hasta la actualidad.

### Acceso

Copernicus indica varias formas:

- Copernicus Browser;
- descarga;
- **OData API**;
- **S3 / EODATA**.

Para V2, la propia página enlaza al Copernicus Data Space Ecosystem.

### Por qué es interesante para Rainmapper

Es probablemente la mejor referencia para la primera validación porque:

1. tiene resolución espacial de 1 km;
2. es diaria;
3. cubre Catalunya;
4. puede automatizarse;
5. procede de observaciones satelitales;
6. es independiente del modelo meteorológico/hídrico de Rainmapper;
7. dispone de histórico suficientemente largo.

### Trabajo solicitado a Codex

Investigar exactamente:

1. formato de los productos SWI;
2. nombres de bandas/variables;
3. unidades;
4. valores `nodata`;
5. distintas profundidades o constantes temporales disponibles;
6. cuál de ellas es conceptualmente más comparable con el SMI de Rainmapper;
7. método más ligero para obtener **un único píxel por coordenada y día** sin descargar Europa completa cada vez.

Preferencia:

```text
lat/lon + fecha -> valor SWI
```

o, si no existe endpoint puntual:

```text
descarga/caché del raster diario -> extracción del píxel
```

No integrar todavía en producción hasta comprobar cómo funciona.

---

# 3.2. Copernicus Land Monitoring Service — Surface Soil Moisture (SSM)

### Prioridad

**P1 — complemento al SWI.**

Producto:

https://land.copernicus.eu/en/products/soil-moisture/daily-surface-soil-moisture-v1.0

### Características verificadas

- Europa;
- **1 km**;
- **diario**;
- desde **2014 hasta actualidad**;
- Sentinel-1 C-SAR;
- producto validado;
- acceso mediante Copernicus Browser, OData API y S3/EODATA.

### Diferencia respecto a SWI

No confundir:

```text
SSM = humedad superficial
SWI = estado hídrico estimado a mayor profundidad / distintas escalas temporales
```

SSM debería reaccionar mucho más deprisa a:

- lluvia débil;
- rocío / humedad superficial;
- secado rápido;
- radiación y viento.

Para setas, el SWI probablemente resulte más interesante que SSM como referencia principal, pero SSM puede ayudar a explicar discrepancias.

### Uso propuesto

Guardar ambos durante el experimento:

```text
Copernicus_SSM
Copernicus_SWI
```

y comprobar cuál se correlaciona mejor con el SMI usado por Rainmapper y con las observaciones micológicas.

---

# 3.3. Copernicus European Drought Observatory (EDO) — SMI / Soil Moisture Anomaly

### Prioridad

**P1 — referencia conceptual muy interesante porque utiliza literalmente un SMI.**

Portal:

https://drought.emergency.copernicus.eu/

WMS:

https://drought.emergency.copernicus.eu/data/wms-service

WCS:

https://drought.emergency.copernicus.eu/data/wcs-service

Factsheet de Soil Moisture:

https://drought.emergency.copernicus.eu/data/factsheets/factsheet_soilmoisture.pdf

### Características metodológicas verificadas

EDO utiliza el modelo hidrológico **LISFLOOD**.

El documento técnico describe:

- humedad del suelo calculada diariamente;
- resolución espacial de aproximadamente **5 km**;
- cobertura europea;
- cálculo de un **Soil Moisture Index (SMI)**;
- normalización respecto al punto de marchitez y capacidad de campo;
- SMI aproximadamente en escala **0–1**.

Conceptualmente:

```text
SMI ≈ 0 -> extremadamente seco / alrededor del wilting point
SMI ≈ 1 -> humedad igual o superior a field capacity
```

También calcula una anomalía:

```text
SMA = desviación del SMI actual respecto a la climatología
```

expresada en unidades de desviación estándar.

Esto es especialmente interesante porque separa dos preguntas:

```text
¿Cuánta humedad disponible hay?
```

y:

```text
¿Está este lugar más seco o húmedo de lo normal para esta época?
```

Ambas podrían tener utilidad biológica distinta en Rainmapper.

### Servicio actual

El portal actual ofrece WMS para, entre otras capas:

- `SMI Anomaly (EDO)`;
- otros indicadores de sequía.

Endpoint de capacidades:

https://drought.emergency.copernicus.eu/api/wms?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1

Existe también WCS para algunos indicadores, pero en la documentación pública revisada el listado explícito de WCS no incluye actualmente el SMI/SMA de EDO de la misma manera que el WMS.

### IMPORTANTE

**No asumir que WMS sirve para recuperar directamente el valor numérico de un punto.**

Codex debe investigar:

1. `GetCapabilities`;
2. nombre exacto de la capa SMI/SMA;
3. si existe `GetFeatureInfo`;
4. si existe descarga directa del raster;
5. si el portal de descarga utiliza una API interna;
6. si existe endpoint de series temporales para `lat/lon`;
7. si hay una forma oficial de obtener el SMI absoluto además de la anomalía;
8. licencia y límites de uso.

Usar DevTools/network del navegador si fuera necesario para entender qué petición hace el portal oficial.

### Ventaja y limitación

Ventaja:

- la definición de SMI es conceptualmente muy cercana a lo que queremos validar.

Limitación:

- aproximadamente 5 km;
- modelo LISFLOOD, no observación directa;
- no debemos asumir equivalencia numérica con Rainmapper.

---

# 3.4. AEMET — Balance Hídrico Nacional

### Prioridad

**P2 — contraste oficial español, especialmente útil como comprobación visual/macrorregional.**

Página:

https://www.aemet.es/es/serviciosclimaticos/vigilancia_clima/balancehidrico

Estadísticas:

https://www.aemet.es/es/datos_abiertos/estadisticas/balance_hidrico

### Variables disponibles

AEMET calcula diariamente parámetros relacionados con:

- precipitación;
- evapotranspiración potencial;
- humedad del suelo.

Publica mapas de:

- precipitación acumulada;
- ETP acumulada;
- humedad de suelo superficial:
  - `% Reserva / 25 mm`;
- humedad total:
  - `% Reserva / Máxima`.

Los mapas públicos se actualizan aproximadamente cada **7 días**.

El Boletín Hídrico Nacional se publica aproximadamente cada **10 días**.

### Metodología relevante

La documentación de AEMET indica que el balance se calcula diariamente.

En boletines técnicos recientes se indica el uso de:

- análisis en rejilla del modelo meteorológico de AEMET;
- resolución aproximada de entrada de **0,05°**;
- estaciones sinópticas;
- estaciones automáticas;
- evapotranspiración de referencia mediante **Penman-Monteith**.

### Uso recomendado

No parece, a priori, la opción más sencilla para:

```text
lat/lon -> humedad diaria exacta
```

pero puede ser una excelente validación independiente y oficial para comprobar que:

```text
zona húmeda/seca Rainmapper
≈
zona húmeda/seca AEMET
```

y que la evolución general después de lluvias importantes tenga sentido.

### Trabajo solicitado a Codex

Investigar si existe:

- endpoint de AEMET OpenData;
- fichero raster;
- GeoTIFF;
- GRIB;
- NetCDF;
- CSV espacial;
- URL interna utilizada para generar los mapas;
- datos diarios accesibles aunque la web sólo actualice el mapa cada 7 días.

No hacer scraping frágil de una imagen si existe una fuente de datos mejor.

---

# 3.5. isardSAT — Earth Food Security

### Prioridad

**P3 — científicamente muy interesante, pero comprobar condiciones de acceso/coste/licencia.**

Portal:

https://earthfoodsecurity.isardsat.cat/

API:

https://earthfoodsecurity.isardsat.cat/api-documentation

### Producto

isardSAT ofrece:

- humedad del suelo satelital;
- superficie;
- root-zone;
- índices de sequía;
- cobertura global;
- resolución aproximada **1 km**;
- frecuencia típica **cada 2–3 días o mejor**;
- histórico desde aproximadamente **2010**.

La metodología combina observaciones de microondas y otros sensores mediante técnicas de desagregación.

El propio portal indica productos para:

```text
surface soil moisture
root-zone soil moisture
drought indices
```

### API

Existe API documentada.

La documentación revisada indica:

- API basada en JSON;
- trabajos/jobs para generar productos;
- parámetros como:
  - `productType`;
  - `depth`;
  - `aoi`;
  - `startDate`;
  - `endDate`;
  - `periodicity`;
- salida potencial en GeoTIFF;
- autenticación mediante Firebase;
- token Bearer de duración limitada.

Por tanto, técnicamente parece integrable, pero **no debemos asumir que el acceso completo sea gratuito o apropiado para una futura aplicación comercial**.

### Trabajo solicitado a Codex

Investigar:

1. si puede crearse una cuenta normal;
2. qué productos pueden obtenerse gratuitamente;
3. límites;
4. licencia;
5. condiciones para aplicación comercial;
6. si existe acceso puntual o requiere definir un AOI/job;
7. coste potencial.

No utilizar credenciales hardcodeadas.

---

# 4. Orden recomendado para la prueba

Implementar primero sólo un **prototipo de validación**, sin modificar el algoritmo productivo de Rainmapper.

Orden:

```text
1. Copernicus SWI 1 km
2. Copernicus SSM 1 km
3. EDO SMI / SMI Anomaly
4. AEMET Balance Hídrico
5. isardSAT
```

---

# 5. Primera prueba práctica propuesta

Elegir uno o varios puntos conocidos de Catalunya donde Rainmapper ya tenga datos meteorológicos suficientes.

Ejemplo conceptual:

```text
lat = 42.xxxxxx
lon = 1.xxxxxx

periodo:
últimos 90 días
```

Obtener:

```text
date
rainmapper_rain_mm
rainmapper_et0_or_etp
rainmapper_water_balance
rainmapper_smi

copernicus_swi
copernicus_ssm

edo_smi              # si se consigue
edo_smi_anomaly

aemet_soil_surface
aemet_soil_total

isardsat_surface_sm
isardsat_rootzone_sm
```

No es necesario que todas las columnas estén disponibles en la primera iteración.

---

# 6. Salida del prototipo

Generar un CSV de diagnóstico, por ejemplo:

```text
date,
rain_mm,
rainmapper_balance,
rainmapper_smi,
copernicus_swi,
copernicus_ssm,
edo_smi,
edo_smi_anomaly
```

y gráficos independientes:

1. lluvia diaria;
2. Rainmapper SMI;
3. Copernicus SWI;
4. Copernicus SSM;
5. EDO SMI/SMA si está disponible.

Después generar un gráfico normalizado para comparar tendencias.

Ejemplo:

```text
valor_norm = (x - percentile_5) / (percentile_95 - percentile_5)
```

o utilizar z-score si resulta más apropiado.

Evitar comparar directamente valores absolutos de productos con definiciones diferentes.

---

# 7. Métricas de validación

No quedarse únicamente con correlación Pearson.

Calcular como mínimo:

## 7.1. Correlación

```text
Pearson
Spearman
```

entre:

```text
Rainmapper SMI vs Copernicus SWI
Rainmapper SMI vs Copernicus SSM
Rainmapper SMI vs EDO SMI
```

si hay datos suficientes.

## 7.2. Correlación de cambios

Comparar también:

```text
ΔSMI(t) = SMI(t) - SMI(t-1)
```

Esto permite saber si ambos sistemas detectan:

```text
humectación
secado
```

en el mismo momento.

## 7.3. Lag temporal

Probar desplazamientos:

```text
-7 ... +7 días
```

para detectar si Rainmapper responde más deprisa o más despacio que SWI/SMI externo.

## 7.4. Respuesta a lluvia

Detectar automáticamente eventos significativos, por ejemplo:

```text
rain_24h >= 10 mm
rain_72h >= 20 mm
```

Los umbrales exactos pueden modificarse.

Para cada evento medir:

```text
SMI antes
SMI +1 día
SMI +2 días
SMI +3 días
SMI +7 días
```

para Rainmapper y fuente externa.

## 7.5. Dry-down

Seleccionar periodos sin lluvia significativa y comparar:

```text
pendiente de secado Rainmapper
vs
pendiente de secado Copernicus
```

Este punto puede ser especialmente importante para el modelo de fructificación.

---

# 8. Diferencias de escala espacial

Hay que documentar siempre la resolución de cada dato.

Ejemplo:

```text
Rainmapper:
meteorología/interpolación propia

Copernicus SWI:
~1 km

Copernicus SSM:
~1 km

EDO LISFLOOD:
~5 km

AEMET:
escala de varios km / producto nacional
```

No asumir que el píxel represente exactamente el microhábitat de una observación de setas.

Especialmente en Catalunya pueden existir dentro de pocos kilómetros:

- diferencias importantes de altitud;
- orientación;
- bosque;
- suelo;
- precipitación;
- exposición;
- costa/interior.

Por ello, para la validación sería mejor probar posteriormente varios tipos de zona:

```text
Pirineo
Prepirineo
interior
prelitoral
litoral
```

y distintas altitudes.

---

# 9. Profundidad del suelo

Este punto es crítico.

Rainmapper debe documentar qué representa exactamente su SMI actual.

Codex debe revisar la implementación existente y responder:

```text
¿Qué reserva máxima se utiliza?
¿Qué profundidad de suelo representa?
¿Cómo se calcula field capacity?
¿Cómo se calcula wilting point?
¿Cómo interviene el tipo de suelo?
¿Cómo entra la evapotranspiración?
¿Cómo se limita el drenaje?
¿Cómo se inicializa el balance?
```

Después comparar estas hipótesis con:

```text
Copernicus SWI
EDO LISFLOOD root-zone SMI
isardSAT root-zone
```

No modificar el algoritmo en esta fase.

Primero documentar las diferencias.

---

# 10. Arquitectura recomendada del experimento

No acoplar la descarga externa directamente al motor de predicción.

Crear una capa separada, conceptualmente:

```text
external_soil_validation/
    providers/
        copernicus_clms
        edo
        aemet
        isardsat
    cache/
    analysis/
```

La estructura concreta debe adaptarse al proyecto Rainmapper real; no crear carpetas innecesarias si ya existe una arquitectura equivalente.

Interfaz conceptual:

```python
get_soil_moisture(
    provider,
    lat,
    lon,
    start_date,
    end_date
)
```

Resultado normalizado internamente:

```python
{
    "provider": "...",
    "date": "...",
    "lat": ...,
    "lon": ...,
    "variable": "...",
    "value": ...,
    "unit": "...",
    "spatial_resolution_m": ...,
    "source_product": "...",
}
```

Conservar siempre también el valor original sin transformar.

---

# 11. Caché

Evitar descargar repetidamente los mismos productos.

Para productos raster diarios:

```text
provider/product/date
```

puede ser clave de caché.

Ejemplo conceptual:

```text
cache/copernicus/swi/2026/09/2026-09-19.tif
```

o guardar únicamente los valores extraídos si no es necesario conservar el raster.

Antes de elegir estrategia, medir:

- tamaño de raster;
- número de puntos consultados;
- frecuencia;
- coste de red;
- tiempo de extracción.

Si Rainmapper consulta miles de puntos del mismo día, descargar un único raster y muestrearlo localmente puede ser mucho más eficiente que hacer miles de requests.

---

# 12. Uso futuro dentro de Rainmapper

**No integrar todavía estos valores como feature del modelo ML.**

Primera fase:

```text
validación independiente
```

Segunda fase, sólo si demuestra utilidad:

```text
variable auxiliar / feature
```

Hay que evitar circularidad.

Por ejemplo, si el producto externo se deriva en gran medida de la misma meteorología que Rainmapper, una correlación alta no significa necesariamente que Rainmapper esté reproduciendo perfectamente la humedad real del suelo.

Copernicus SSM/SWI es especialmente útil precisamente porque aporta observación satelital y un procesamiento independiente.

---

# 13. Criterio de éxito inicial

Considerar la prueba satisfactoria si para varios puntos y periodos:

1. Rainmapper y SWI muestran las principales humectaciones en fechas semejantes;
2. ambos muestran periodos de secado semejantes;
3. no existen divergencias sistemáticas prolongadas;
4. las divergencias pueden explicarse por:
   - profundidad;
   - escala espacial;
   - lluvia local;
   - evapotranspiración;
   - suelo;
   - cobertura vegetal;
5. el lag óptimo no es excesivo;
6. la relación se mantiene en distintas estaciones del año.

No establecer un umbral de correlación arbitrario antes de ver los datos.

---

# 14. Preguntas concretas que Codex debe responder

## Copernicus CLMS

- [ ] ¿Cuál es la forma más sencilla de consultar SWI para una coordenada?
- [ ] ¿Hay API puntual o debemos descargar raster?
- [ ] ¿Qué variables/bandas SWI existen?
- [ ] ¿Qué representa cada una?
- [ ] ¿Qué profundidad efectiva sería más comparable con Rainmapper?
- [ ] ¿Cómo unir correctamente V1 y V2?
- [ ] ¿Existe discontinuidad relevante entre V1 y V2?
- [ ] ¿Cómo autenticar contra CDSE?
- [ ] ¿Qué límites de uso existen?
- [ ] ¿Podemos automatizarlo legalmente en una aplicación comercial?

## Copernicus SSM

- [ ] ¿Unidad exacta?
- [ ] ¿Rango?
- [ ] ¿Nodata?
- [ ] ¿Cómo se extrae el píxel?
- [ ] ¿Es útil en bosque denso?
- [ ] ¿Qué quality flags deben aplicarse?

## EDO

- [ ] ¿Podemos recuperar SMI absoluto por lat/lon?
- [ ] ¿Podemos recuperar SMI Anomaly numérico?
- [ ] ¿Existe `GetFeatureInfo`?
- [ ] ¿Existe descarga raster?
- [ ] ¿Existe endpoint de serie temporal?
- [ ] ¿Cuál es actualmente la resolución exacta?
- [ ] ¿Se mantiene la definición 0–1 descrita en el factsheet?
- [ ] ¿Qué periodo climatológico usa actualmente SMA?

## AEMET

- [ ] ¿Existen datos de balance hídrico espacial descargables?
- [ ] ¿AEMET OpenData expone humedad de suelo?
- [ ] ¿Existe raster diario?
- [ ] ¿Podemos obtener un valor aproximado para una coordenada?
- [ ] ¿Qué metodología actual usa para reserva máxima?

## isardSAT

- [ ] ¿Acceso gratuito?
- [ ] ¿Licencia?
- [ ] ¿Uso comercial?
- [ ] ¿Cómo solicitar surface/root-zone?
- [ ] ¿Coste?
- [ ] ¿Se puede solicitar un AOI pequeño?
- [ ] ¿Disponibilidad histórica para Catalunya?

---

# 15. Entregables solicitados a Codex

No modificar inicialmente el funcionamiento de Rainmapper.

Preparar:

### Entregable 1 — Informe técnico corto

```text
external-soil-moisture-validation-findings.md
```

con:

- resultados de la investigación;
- APIs/endpoints comprobados;
- autenticación;
- formatos;
- licencias;
- limitaciones;
- recomendación final.

### Entregable 2 — Prototipo

Script o módulo independiente capaz de:

```bash
<command> --lat 42.x --lon 1.x --start 2026-06-01 --end 2026-09-01
```

y obtener como mínimo:

```text
Copernicus SWI
```

Idealmente también:

```text
Copernicus SSM
EDO SMI/SMA
```

### Entregable 3 — CSV

Serie temporal consolidada.

### Entregable 4 — gráficos

Comparación temporal Rainmapper vs fuentes externas.

### Entregable 5 — conclusiones

Responder expresamente:

```text
1. ¿Rainmapper sigue razonablemente la evolución hídrica externa?
2. ¿Dónde diverge?
3. ¿Existe lag?
4. ¿El secado de Rainmapper parece demasiado rápido o demasiado lento?
5. ¿Qué producto externo es la mejor referencia?
6. ¿Tiene sentido utilizarlo sólo para validación o también como futura feature?
```

---

# 16. Restricciones

- No romper ni sustituir el cálculo actual.
- No cambiar parámetros del modelo basándose en una sola localización.
- No añadir dependencias pesadas sin justificarlo.
- No introducir credenciales en código.
- No hacer scraping de interfaces si existe API/raster oficial.
- Respetar términos/licencias de cada proveedor.
- Mantener trazabilidad de:
  - proveedor;
  - producto;
  - versión;
  - fecha;
  - coordenadas;
  - resolución;
  - unidades.
- No llamar "ground truth" a ninguno de estos productos.

Son **referencias externas**, no verdad absoluta.

---

# 17. Recomendación inicial

La primera implementación debería centrarse en:

```text
Copernicus CLMS Soil Water Index (SWI) 1 km diario
```

y, en paralelo:

```text
Copernicus Surface Soil Moisture (SSM) 1 km
```

porque parecen ofrecer la mejor combinación de:

- resolución;
- actualización;
- histórico;
- independencia;
- automatización;
- disponibilidad europea.

Después añadir:

```text
EDO SMI / SMI Anomaly
```

como segunda referencia especialmente útil para evaluar el estado hídrico relativo y la sequía.

AEMET debe utilizarse inicialmente como referencia oficial adicional.

isardSAT merece investigación porque su producto root-zone a 1 km puede ser muy interesante para Rainmapper, pero antes hay que aclarar acceso, licencia y coste.

---

# 18. Fuentes

## Copernicus Land Monitoring Service

Soil Water Index V2:

https://land.copernicus.eu/en/products/soil-moisture/daily-soil-water-index-europe-1km-v2

Soil Water Index histórico V1:

https://land.copernicus.eu/en/products/soil-moisture/daily-soil-water-index-europe-1km

Surface Soil Moisture:

https://land.copernicus.eu/en/products/soil-moisture/daily-surface-soil-moisture-v1.0

Soil Moisture overview:

https://land.copernicus.eu/en/products/soil-moisture

## Copernicus European Drought Observatory

Portal:

https://drought.emergency.copernicus.eu/

WMS:

https://drought.emergency.copernicus.eu/data/wms-service

WCS:

https://drought.emergency.copernicus.eu/data/wcs-service

Soil Moisture factsheet:

https://drought.emergency.copernicus.eu/data/factsheets/factsheet_soilmoisture.pdf

## AEMET

Balance Hídrico:

https://www.aemet.es/es/serviciosclimaticos/vigilancia_clima/balancehidrico

Estadística del Balance Hídrico:

https://www.aemet.es/es/datos_abiertos/estadisticas/balance_hidrico

## isardSAT

Earth Food Security:

https://earthfoodsecurity.isardsat.cat/

API:

https://earthfoodsecurity.isardsat.cat/api-documentation

---

# 19. Nota final para Codex

Antes de escribir código definitivo:

1. revisar cómo calcula actualmente Rainmapper `water balance` y `SMI`;
2. documentar su escala y significado exactos;
3. probar manualmente un único punto con Copernicus;
4. confirmar unidades/bandas;
5. sólo entonces construir la serie temporal y comparación.

La pregunta que queremos responder no es:

> "¿Da exactamente el mismo número?"

sino:

> "¿La dinámica hídrica que calcula Rainmapper para un punto de Catalunya es coherente con observaciones/modelos independientes del estado hídrico del suelo?"

Ese debe ser el criterio central de la investigación.
