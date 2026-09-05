# Rainmapper – Integración de estaciones meteorológicas francesas
## Météo-France + Infoclimat/StatIC
**Fecha de investigación:** 4 de septiembre de 2026

**Objetivo:** ampliar Rainmapper en Cerdanya francesa / Capcir / Donezan / Haute-Ariège, inicialmente alrededor de Font-Romeu, Les Angles, Formiguères, Quérigut, Osséja y Mérens-les-Vals.

---

## 1. Resumen ejecutivo

La recomendación es implementar **dos proveedores franceses**:

1. **Météo-France** como proveedor oficial y principal.
2. **Infoclimat/StatIC** únicamente como proveedor complementario para estaciones que no estén disponibles en Météo-France o aporten una ubicación realmente distinta.

No debe utilizarse Infoclimat como réplica de estaciones Météo-France cuando ambas fuentes representen el mismo emplazamiento.

### Decisión principal

Para Rainmapper:

```text
AEMET
Meteocat
MeteoFrance       <- proveedor francés principal
Infoclimat        <- proveedor complementario, sólo estaciones adicionales
```

### Descubrimiento clave

La API climatológica diaria de Météo-France puede proporcionar en una misma descarga los parámetros necesarios para Rainmapper, incluyendo:

- `RR` – precipitación diaria
- `TN` – temperatura mínima
- `TX` – temperatura máxima
- `TM` – temperatura media
- `FFM` – viento medio diario
- `FXI` / `FXI3S` – racha máxima
- `DXI` / `DXI3S` – dirección de la racha
- `UN` – humedad relativa mínima
- `UX` – humedad relativa máxima
- `UM` – humedad relativa media

Por tanto, **no es necesario construir la humedad diaria agregando obligatoriamente datos horarios** si esos parámetros diarios están disponibles para la estación concreta.

Los CSV públicos diarios del bloque básico `RR-T-Vent` no contienen todos los parámetros de humedad, pero la **API climatológica diaria completa sí puede devolverlos**.

---

# 2. Météo-France

## 2.1 Fuente recomendada

API oficial:

`https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesClimatologie`

Base pública usada por clientes:

`https://public-api.meteofrance.fr/public/DPClim/v1/`

Dataset oficial diario:

`https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes`

Dataset diario de estaciones complementarias:

`https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes-stations-complementaires`

Metadatos / catálogo de estaciones:

`https://www.data.gouv.fr/datasets/informations-sur-les-stations-metadonnees`

Documentación general data.gouv.fr:

`https://guides.data.gouv.fr/guides/reutiliser-des-donnees/prise-en-main-des-donnees-meteorologiques`

## 2.2 Autenticación

La API climatológica requiere:

- cuenta gratuita Météo-France;
- suscripción gratuita a la API de datos climatológicos;
- token/API key.

Límite publicado:

```text
50 requests/minute
```

Fuente:

`https://www.data.gouv.fr/dataservices/api-donnees-climatologiques`

El mecanismo usado por ejemplos de Météo-France es compatible con API key/token.

## 2.3 Flujo de descarga

La API climatológica trabaja mediante una **orden asíncrona**.

### Paso 1 – solicitar datos diarios de una estación

Endpoint:

```text
GET /public/DPClim/v1/commande-station/quotidienne
```

Parámetros típicos:

```text
id-station
date-deb-periode
date-fin-periode
apikey
```

Ejemplo conceptual:

```python
params = {
    "id-station": station_id,
    "date-deb-periode": "2026-08-01T00:00:00Z",
    "date-fin-periode": "2026-09-01T00:00:00Z",
    "apikey": token,
}
```

La respuesta contiene un identificador de pedido.

### Paso 2 – recuperar el CSV generado

Endpoint:

```text
GET /public/DPClim/v1/commande/fichier
```

Parámetros:

```text
id-cmde
apikey
```

Referencia técnica útil:

`https://github.com/mmandem/Meteo-France_API/blob/main/extrait_obs_BDCLIM_viaAPI_Meteo-France.py`

Ese ejemplo está firmado por personal Météo-France/CNRM y fue actualizado en enero de 2026.

## 2.4 Formato temporal

Las fechas de petición se manejan en UTC:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Rainmapper debe tratar explícitamente la diferencia entre:

- UTC usado por Météo-France;
- `Europe/Paris`;
- definición climatológica de día.

No se debe asumir que una agregación local 00:00–24:00 reproduce exactamente el día climatológico oficial.

---

# 3. Parámetros Météo-France relevantes para Rainmapper

## 3.1 Precipitación

```text
RR
```

Significado:

```text
precipitación diaria acumulada [mm]
```

Campo de calidad asociado:

```text
QRR
```

## 3.2 Temperatura

```text
TN      temperatura mínima diaria [°C]
TX      temperatura máxima diaria [°C]
TM      temperatura media diaria [°C]
TNTXM   (TN + TX) / 2
```

También pueden existir:

```text
HTN     hora de TN
HTX     hora de TX
```

Campos de calidad:

```text
QTN
QTX
QTM
...
```

## 3.3 Humedad relativa

La respuesta diaria completa puede contener:

```text
UN      humedad relativa mínima diaria [%]
UX      humedad relativa máxima diaria [%]
UM      humedad relativa media diaria [%]
HUN     hora de UN
HUX     hora de UX
```

y sus flags:

```text
QUN
QUX
QUM
QHUN
QHUX
```

Esto está confirmado por ejemplos reales de respuesta de la API climatológica diaria.

Por tanto, en Rainmapper:

```text
humidity_min_pct  <- UN
humidity_max_pct  <- UX
humidity_mean_pct <- UM
```

No calcular `UM = (UN + UX) / 2`.

Si `UM` no está disponible pero existen datos horarios `U`, se puede calcular como fallback a partir de observaciones horarias válidas.

## 3.4 Viento

Variables relevantes:

```text
FFM      media diaria de la fuerza del viento medio de 10 min a 10 m [m/s]
FF2M     equivalente a 2 m, si existe

FXY      máximo diario del viento medio de 10 min
DXY      dirección de FXY [grados]
HXY      hora de FXY

FXI      máximo diario del viento instantáneo
DXI      dirección de FXI [grados]
HXI      hora de FXI

FXI3S    racha máxima diaria promediada sobre 3 s
DXI3S    dirección de FXI3S
HXI3S    hora de FXI3S
```

### Normalización propuesta

```text
wind_mean_ms       <- FFM
wind_gust_ms       <- first_available(FXI3S, FXI)
wind_direction_deg <- first_available(DXI3S, DXI)
```

No convertir a km/h en almacenamiento interno. Mantener SI (`m/s`) y convertir únicamente en presentación.

---

# 4. Flags de calidad Météo-France

Cada valor puede venir acompañado de un campo `Qxxx`.

Rainmapper debe conservar el flag original.

Ejemplos observados en la documentación/ecosistema Météo-France:

```text
0 = dato protegido/validado definitivamente
1 = dato validado
2 = dato dudoso en verificación
9 = dato filtrado / ha superado controles iniciales
```

No se recomienda descartar todos los valores que no sean `0` o `1` sin estudiar primero el comportamiento real del feed.

### Esquema recomendado

```text
rain_mm
rain_quality

temp_min_c
temp_min_quality

temp_max_c
temp_max_quality

humidity_min_pct
humidity_min_quality

...
```

O alternativamente guardar un JSON de calidad por observación.

---

# 5. Estaciones Météo-France investigadas

## 5.1 Formiguères

### Identidad correcta

**Corrección respecto a la investigación preliminar:**

el identificador actual que aparece asociado a la estación activa de Formiguères es:

```text
MF66082004
```

Indicativo visible en Infoclimat:

```text
07737
```

No usar `66082401`; ese identificador aparecido en una búsqueda preliminar no corresponde al puesto operativo que interesa.

Datos:

```text
Nombre: Formiguères
Lat: ~42.62
Lon: ~2.11
Altitud: 1495 m
Inicio de serie visible: 01/07/2005
Red: Météo-France
```

En 2026 hay observaciones actuales con:

```text
temperatura
precipitación
viento
racha
humedad
punto de rocío
```

Fuentes:

`https://www.infoclimat.fr/observations-meteo/temps-reel/formigueres/07737.html`

`https://www.infoclimat.fr/climatologie/annee/2026/formigueres/valeurs/07737.html`

### Prioridad Rainmapper

```text
MUY ALTA
```

Es la estación francesa más completa y consolidada de las investigadas en el sector Capcir.

---

## 5.2 Les Angles

Identificador:

```text
MF66004401
```

Datos:

```text
Nombre: Les Angles
Lat: ~42.57
Lon: ~2.05
Altitud: 2108 m
Inicio visible: 21/12/1983
Red: Météo-France
```

En la climatología visible de 2026 aparecen datos en invierno/inicio de primavera, pero no una continuidad anual completa.

Fuente:

`https://www.infoclimat.fr/climatologie/annee/2026/test-mf-csv-les-angles/valeurs/MF66004401.html`

### Interpretación

Parece una estación de alta montaña/nivológica con posible funcionamiento estacional o disponibilidad parcial.

### Prioridad Rainmapper

```text
ALTA como estación de montaña
pero NO confiar en ella como única fuente continua
```

Rainmapper debe tolerar huecos amplios.

---

## 5.3 Quérigut

Identificador investigado:

```text
MF09239005
```

Datos:

```text
Nombre: Quérigut
Lat: ~42.68
Lon: ~2.12
Altitud: 1430 m
Inicio visible: 01/10/2008
Red: Météo-France
```

Fuente:

`https://www.infoclimat.fr/observations-meteo/temps-reel/test-mf-csv-querigut/MF09239005.html`

Sin embargo, la evidencia pública disponible no demuestra continuidad reciente equivalente a Formiguères. La climatología visible de Infoclimat es muy incompleta para este identificador.

También existen puestos anteriores:

```text
MF09239004  ~1220 m
MF09239001  ~1200 m
```

sin datos actuales visibles en 2026.

### Decisión

**No tratar Quérigut como estación activa garantizada hasta consultar los metadatos de la API Météo-France con token.**

Codex debe implementar el proveedor de forma que la selección final de estaciones pueda activarse/desactivarse por configuración.

```text
status = candidate_pending_api_verification
```

---

# 6. Infoclimat / StatIC

## 6.1 Fuente

Open Data:

`https://www.infoclimat.fr/opendata/`

La plataforma incluye:

- algunas estaciones oficiales nacionales;
- estaciones de la asociación Infoclimat;
- estaciones de colaboradores StatIC que han autorizado reutilización.

## 6.2 Autenticación

La automatización requiere API key.

Es necesario:

1. crear cuenta;
2. declarar el tipo de reutilización;
3. generar la clave API.

Infoclimat documenta un máximo habitual de:

```text
7 días consecutivos por petición
```

excepto para propietarios de estaciones.

Fuente:

`https://www.infoclimat.fr/opendata/`

### Consecuencia para Rainmapper

El downloader debe trocear automáticamente rangos grandes:

```python
for chunk in split_date_range(start, end, days=7):
    fetch(chunk)
```

Esto es especialmente importante para backfill histórico.

---

# 7. Licencias Infoclimat

La licencia es **por estación**.

Tipos relevantes:

```text
Open
Non-commercial
Closed
```

Infoclimat considera uso personal como no comercial.

Rainmapper, mientras sea un proyecto personal/no lucrativo, puede utilizar estaciones con licencia `Non-commercial`, respetando atribución.

### Regla de implementación

Guardar en metadatos:

```text
license_type
license_text
license_checked_at
```

y no asumir que una estación mantiene siempre la misma licencia.

Infoclimat señala que un cambio de licencia puede ser retroactivo.

---

# 8. Estaciones StatIC investigadas

## 8.1 Font-Romeu-Odeillo-Via – nueva estación

ID:

```text
STATIC0478
```

Datos:

```text
Lat: 42.506
Lon: 2.040
Altitud: 1952 m
Apertura: 22/06/2026
Red: StatIC
Propietario: Météo Pyrénées
Modelo: Davis Vantage Pro 2 inalámbrica
```

Instrumentación:

```text
thermo/hygro
anemómetro
veleta
pluviómetro
barómetro
```

La observación real muestra:

```text
temperatura
precipitación
viento
racha
humedad
punto de rocío
presión
```

Fuentes:

`https://www.infoclimat.fr/stations/metadonnees.php?id=STATIC0478`

`https://www.infoclimat.fr/observations-meteo/temps-reel/font-romeu-odeillo-via/STATIC0478.html`

### Problema de licencia

En la ficha consultada:

```text
Licence des données: non saisi
```

Por tanto:

```text
NO asumir acceso API todavía
```

La estación debe quedar como:

```text
candidate_pending_license
```

hasta que una llamada real a la API OpenData confirme que está incluida.

### Prioridad

Meteorológicamente:

```text
MUY ALTA
```

Por acceso programático:

```text
PENDIENTE
```

---

## 8.2 Osséja

ID:

```text
000EN
```

Datos:

```text
Lat: 42.414
Lon: 1.982
Altitud: 1350 m
Apertura: 25/06/2016
Red: StatIC
Modelo: Davis Vantage Pro 2 inalámbrica
```

Licencia:

```text
non-commercial (CC BY-NC)
```

La ficha indica calidad:

```text
Temperatura / humedad: Très bonne
```

Existe instrumentación y observaciones de:

```text
temperatura
humedad
pluviómetro
viento
dirección
```

Fuentes:

`https://www.infoclimat.fr/stations/metadonnees.php?id=000EN`

`https://www.infoclimat.fr/observations-meteo/temps-reel/osseja/000EN.html`

### Prioridad

```text
MUY ALTA para Rainmapper personal
```

Es especialmente útil para Cerdanya por su posición y altitud.

---

## 8.3 Mérens-les-Vals

ID:

```text
000BR
```

Datos:

```text
Lat: 42.650
Lon: 1.833
Altitud: 1070 m
Apertura: 24/08/2015
Red: StatIC
Modelo: Davis Vantage Pro 2 inalámbrica
```

Instrumentación:

```text
thermo/hygro
anemómetro
veleta
pluviómetro
```

Calidad declarada del emplazamiento:

```text
Temperatura / humedad: moyenne
Vent: moyenne
Pluviométrie: moyenne
```

por vegetación alrededor y anemómetro a 2 m.

Fuente:

`https://www.infoclimat.fr/stations/metadonnees.php?id=000BR`

Observaciones:

`https://www.infoclimat.fr/observations-meteo/temps-reel/merens-les-vals/000BR.html`

### Problema de licencia

En la ficha examinada:

```text
Licence des données: non saisi
```

Por tanto:

```text
candidate_pending_license
```

hasta verificar presencia en API.

---

# 9. Antigua estación Font-Romeu

ID anterior:

```text
000RX
```

Datos:

```text
Altitud: 1788 m
Inicio: 17/06/2020
Red: StatIC / Météo Pyrénées
```

Esta estación fue sustituida/trasladada en 2026.

Debe conservarse para histórico como una **serie distinta**.

No fusionar directamente:

```text
000RX      1788 m
STATIC0478 1952 m
```

aunque ambas tengan nombre Font-Romeu.

La diferencia de ~164 m de altitud y de emplazamiento es meteorológicamente significativa.

---

# 10. Deduplicación de estaciones

## 10.1 No deduplicar por nombre

Incorrecto:

```python
if station.name == other.name:
    duplicate = True
```

## 10.2 Regla propuesta

Crear una entidad física de estación separada del identificador del proveedor.

Ejemplo:

```text
weather_station
weather_station_source
```

### `weather_station`

```text
id
canonical_name
latitude
longitude
altitude_m
country
region
active_from
active_to
```

### `weather_station_source`

```text
station_id
provider
provider_station_id
provider_station_name
license
source_priority
active
metadata_json
```

## 10.3 Detección de posibles duplicados

Usar:

```text
distance <= 300 m
AND altitude difference <= 30 m
AND overlapping operational dates
```

como señal de revisión, no como fusión automática.

Para montaña conviene ser conservador:

- 300 m horizontales pueden ser importantes;
- diferencias de altitud >30–50 m pueden representar otro microclima;
- un traslado debe generar una nueva serie física.

## 10.4 Prioridad de proveedor

Si una misma estación física aparece en ambos:

```text
1. METEOFRANCE
2. INFOCLIMAT
```

No descargar la réplica Infoclimat si ya se obtiene el dato oficial directamente.

---

# 11. Modelo normalizado recomendado

```python
DailyWeatherObservation:
    station_id: str
    provider: str
    provider_station_id: str

    date: date

    rain_mm: float | None

    temp_min_c: float | None
    temp_max_c: float | None
    temp_mean_c: float | None

    humidity_min_pct: float | None
    humidity_max_pct: float | None
    humidity_mean_pct: float | None

    wind_mean_ms: float | None
    wind_gust_ms: float | None
    wind_direction_deg: float | None

    source_timestamp: datetime | None

    quality: dict | None
    raw_payload: dict | None
```

No rellenar con `0` los valores ausentes.

```text
null != 0
```

especialmente para lluvia, viento y humedad.

---

# 12. Mapeo Météo-France -> Rainmapper

```python
METEOFRANCE_DAILY_MAPPING = {
    "RR": "rain_mm",

    "TN": "temp_min_c",
    "TX": "temp_max_c",
    "TM": "temp_mean_c",

    "UN": "humidity_min_pct",
    "UX": "humidity_max_pct",
    "UM": "humidity_mean_pct",

    "FFM": "wind_mean_ms",

    # Preferencia para racha
    "FXI3S": "wind_gust_ms",
    "FXI": "wind_gust_ms_fallback",

    "DXI3S": "wind_direction_deg",
    "DXI": "wind_direction_deg_fallback",
}
```

Resolver precedencias después del parseo:

```python
wind_gust_ms = first_not_none(FXI3S, FXI)
wind_direction_deg = (
    DXI3S if FXI3S is not None and DXI3S is not None
    else DXI
)
```

---

# 13. Mapeo Infoclimat -> Rainmapper

La API debe encapsularse detrás de un adaptador independiente.

```python
class InfoclimatProvider(WeatherProvider):
    ...
```

El formato exacto de respuesta debe capturarse mediante una petición real con API key antes de fijar nombres de campos en código.

No codificar el parser basándose en HTML de Infoclimat.

El HTML se ha utilizado únicamente para validar que las estaciones miden realmente:

```text
temperatura
precipitación
viento
racha
humedad
```

La implementación productiva debe usar exclusivamente la API OpenData autorizada.

---

# 14. Proveedores

Interfaz propuesta:

```python
class WeatherProvider(ABC):

    @abstractmethod
    def list_stations(self) -> list[ProviderStation]:
        ...

    @abstractmethod
    def fetch_daily(
        self,
        station_id: str,
        start_date: date,
        end_date: date,
    ) -> list[DailyWeatherObservation]:
        ...
```

Implementaciones:

```text
AemetProvider
MeteocatProvider
MeteoFranceProvider
InfoclimatProvider
```

---

# 15. Configuración

Ejemplo:

```yaml
weather_providers:

  meteofrance:
    enabled: true
    api_key: "${METEOFRANCE_API_KEY}"
    departments:
      - "09"
      - "66"

  infoclimat:
    enabled: true
    api_key: "${INFOCLIMAT_API_KEY}"
    usage: "non-commercial"
```

No almacenar tokens en repositorio.

---

# 16. Catálogo inicial de estaciones

Propuesta de configuración inicial:

```yaml
france_weather_stations:

  - provider: meteofrance
    id: "66082004"
    name: "Formiguères"
    altitude_m: 1495
    enabled: true
    priority: 100

  - provider: meteofrance
    id: "66004401"
    name: "Les Angles"
    altitude_m: 2108
    enabled: true
    priority: 80
    notes: "Posible disponibilidad estacional/parcial"

  - provider: meteofrance
    id: "09239005"
    name: "Quérigut"
    altitude_m: 1430
    enabled: false
    status: "pending_api_verification"

  - provider: infoclimat
    id: "000EN"
    name: "Osséja"
    altitude_m: 1350
    enabled: true
    license: "CC BY-NC"
    priority: 90

  - provider: infoclimat
    id: "STATIC0478"
    name: "Font-Romeu-Odeillo-Via"
    altitude_m: 1952
    enabled: false
    status: "pending_license_api_verification"
    priority: 100

  - provider: infoclimat
    id: "000BR"
    name: "Mérens-les-Vals"
    altitude_m: 1070
    enabled: false
    status: "pending_license_api_verification"
    priority: 70
```

---

# 17. Estrategia de descarga

## 17.1 Incremental diario

Guardar:

```text
last_successful_date
```

por estación y proveedor.

Ejemplo:

```python
start = last_successful_date + timedelta(days=1)
end = yesterday
```

No volver a descargar todo el histórico cada día.

## 17.2 Ventana de revisión

Los proveedores pueden corregir datos recientes.

Recomendación:

```text
re-fetch últimos 7 días cada ejecución
```

y hacer upsert.

## 17.3 Histórico

Météo-France:

- puede hacer backfill mediante la API climatológica o CSV oficiales;
- para grandes históricos puede ser más eficiente usar los CSV comprimidos por departamento.

Infoclimat:

- trocear en intervalos máximos de 7 días;
- respetar límites y términos de servicio.

---

# 18. Persistencia e idempotencia

Clave única:

```text
(provider, provider_station_id, date)
```

o, si los datos ya se consolidan por estación física:

```text
(station_source_id, date)
```

Usar UPSERT.

Un segundo run del mismo día no debe crear filas duplicadas.

---

# 19. Gestión de fallos

El fallo de una estación no debe abortar todo el proceso.

Ejemplo:

```text
Formiguères OK
Les Angles no data
Osséja timeout
...
```

Resultado global:

```text
completed_with_errors
```

con logging por estación.

Usar:

- timeout HTTP;
- reintentos exponenciales;
- respeto de `429 Too Many Requests`;
- no reintentar errores permanentes `401/403` indefinidamente.

---

# 20. Validaciones de datos

Aplicar validación básica:

```text
0 <= humidity <= 100

rain >= 0

-50 <= temperature <= 55    # sanity check regional, configurable

0 <= wind_direction < 360

wind_speed >= 0
```

Las validaciones no deben eliminar silenciosamente datos: marcar anomalía y conservar raw payload cuando sea posible.

---

# 21. Uso para el Mushroom Predictor

La red francesa añade un rango altitudinal especialmente útil:

```text
Mérens-les-Vals      1070 m
Osséja               1350 m
Quérigut             1430 m   (pendiente)
Formiguères          1495 m
Font-Romeu           1952 m   (pendiente API)
Les Angles           2108 m
```

Para interpolación de montaña no usar únicamente distancia horizontal.

El selector/interpolador debería poder ponderar como mínimo:

```text
horizontal_distance
altitude_difference
```

y posteriormente:

```text
aspect/orientation
terrain barriers
vegetation
```

aprovechando el DEM ya existente en Rainmapper.

---

# 22. Fases de implementación recomendadas

## Fase 1 – Météo-France

1. Añadir configuración y secreto.
2. Implementar autenticación.
3. Implementar catálogo de estaciones.
4. Implementar `commande-station/quotidienne`.
5. Implementar polling/descarga de `commande/fichier`.
6. Parsear CSV.
7. Mapear RR/T/Humidity/Wind.
8. Conservar flags de calidad.
9. Activar inicialmente Formiguères.
10. Probar Les Angles.
11. Consultar metadatos reales de Quérigut y decidir si se activa.

## Fase 2 – Infoclimat

1. Crear API key para uso personal/no comercial.
2. Implementar downloader con ventanas <=7 días.
3. Probar Osséja (`000EN`).
4. Verificar si `STATIC0478` aparece en la API.
5. Verificar si `000BR` aparece en la API.
6. No hacer scraping HTML.
7. Guardar licencia por estación.

## Fase 3 – deduplicación

1. Importar catálogo MF.
2. Importar catálogo StatIC.
3. Comparar coordenadas + altitud.
4. Marcar `same_physical_station`.
5. Priorizar MF cuando haya solapamiento.
6. Mantener traslados como estaciones físicas distintas.

---

# 23. Tests que Codex debe crear

## Unit tests

### Météo-France parser

Casos:

```text
RR normal
RR null
TN/TX/TM
UN/UX/UM
FFM
FXI3S presente
FXI3S ausente -> usar FXI
dirección asociada correcta
flags Qxxx
```

### Infoclimat chunking

```text
1 día       -> 1 request
7 días      -> 1 request
8 días      -> 2 requests
31 días     -> 5 requests
```

### Deduplicación

Casos:

```text
mismo nombre pero 164 m de diferencia de altitud -> NO fusionar
mismo punto, mismo periodo, dos proveedores       -> candidato a duplicado
mismo punto, periodos no solapados                 -> posible continuidad/traslado, revisar
```

## Integration tests

Con secrets presentes:

```text
Météo-France Formiguères: recuperar al menos un día
Météo-France: validar RR/TN/TX
Météo-France: validar humedad si existe
Météo-France: validar viento si existe

Infoclimat Osséja: recuperar observaciones
```

Los tests con API externa deben estar marcados para no ejecutarse siempre en CI.

---

# 24. Criterios de aceptación

La implementación puede considerarse terminada cuando:

- [ ] existe `MeteoFranceProvider`;
- [ ] existe `InfoclimatProvider`;
- [ ] los tokens se leen de secretos/configuración;
- [ ] Formiguères descarga datos diarios correctamente;
- [ ] Rainmapper guarda lluvia, Tmin, Tmax, Tmedia;
- [ ] Rainmapper guarda humedad min/max/media cuando existe;
- [ ] Rainmapper guarda viento medio, racha y dirección cuando existe;
- [ ] los `null` permanecen como `null`;
- [ ] se conservan flags de calidad Météo-France;
- [ ] Infoclimat respeta ventanas máximas de 7 días;
- [ ] Osséja funciona como estación StatIC;
- [ ] Font-Romeu sólo se activa tras verificar licencia/API;
- [ ] Mérens sólo se activa tras verificar licencia/API;
- [ ] no se duplica una estación Météo-France vía Infoclimat;
- [ ] los traslados se mantienen como series físicas diferentes;
- [ ] el proceso es incremental e idempotente;
- [ ] el fallo de una estación no aborta todas las demás.

---

# 25. Fuentes principales

## Météo-France / data.gouv.fr

API climatológica:

https://www.data.gouv.fr/dataservices/api-donnees-climatologiques

Datos climatológicos diarios:

https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes

Estaciones complementarias:

https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes-stations-complementaires

Datos horarios:

https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-horaires

Guía de reutilización:

https://guides.data.gouv.fr/guides/reutiliser-des-donnees/prise-en-main-des-donnees-meteorologiques

Ejemplo técnico API (Météo-France/CNRM):

https://github.com/mmandem/Meteo-France_API/blob/main/extrait_obs_BDCLIM_viaAPI_Meteo-France.py

Ejemplo de respuesta diaria con `UN`, `UX`, `UM`:

https://rstudio-pubs-static.s3.amazonaws.com/1318486_62868950ab914f6b9b0c0ec646e228f8.html

## Infoclimat

OpenData:

https://www.infoclimat.fr/opendata/

Font-Romeu metadata:

https://www.infoclimat.fr/stations/metadonnees.php?id=STATIC0478

Font-Romeu observations:

https://www.infoclimat.fr/observations-meteo/temps-reel/font-romeu-odeillo-via/STATIC0478.html

Osséja metadata:

https://www.infoclimat.fr/stations/metadonnees.php?id=000EN

Osséja observations:

https://www.infoclimat.fr/observations-meteo/temps-reel/osseja/000EN.html

Mérens-les-Vals metadata:

https://www.infoclimat.fr/stations/metadonnees.php?id=000BR

Mérens observations:

https://www.infoclimat.fr/observations-meteo/temps-reel/merens-les-vals/000BR.html

Formiguères:

https://www.infoclimat.fr/observations-meteo/temps-reel/formigueres/07737.html

Les Angles:

https://www.infoclimat.fr/climatologie/annee/2026/test-mf-csv-les-angles/valeurs/MF66004401.html

Quérigut:

https://www.infoclimat.fr/observations-meteo/temps-reel/test-mf-csv-querigut/MF09239005.html

---

# 26. Instrucción final para Codex

Implementar la integración siguiendo este documento, pero **antes de activar una estación como producción**, consultar los metadatos reales obtenidos mediante la API correspondiente.

No inferir disponibilidad de parámetros a partir del nombre de la estación.

La disponibilidad debe ser dinámica:

```python
station.capabilities = {
    "rain": bool,
    "temperature": bool,
    "humidity": bool,
    "wind": bool,
}
```

y derivarse de los parámetros realmente ofrecidos por la fuente.

Especialmente:

```text
Quérigut       -> verificar actividad actual en Météo-France
Font-Romeu     -> verificar licencia/inclusión API Infoclimat
Mérens-les-Vals-> verificar licencia/inclusión API Infoclimat
```

La primera estación de referencia para validar end-to-end Météo-France debe ser:

```text
Formiguères / MF66082004 / 1495 m
```

y para Infoclimat:

```text
Osséja / 000EN / 1350 m
```
