# Handoff a Codex — GBIF para ampliar/validar observaciones de Rainmapper

**Fecha del handoff:** 2026-09-16\
**Proyecto:** Rainmapper / predictor de fructificación de setas\
**Estado:** fase de exploración y recuento. **NO descargar todavía datasets ni ocurrencias en masa.**

---

## 1. Objetivo

Rainmapper dispone actualmente de unas **450 observaciones propias** de distintas especies y utiliza datos meteorológicos e información ambiental para entrenar/validar modelos de predicción de fructificación.

Se está evaluando **GBIF (Global Biodiversity Information Facility)** como fuente adicional de observaciones históricas de presencia de setas.

La idea futura sería poder utilizar registros GBIF con fecha y geolocalización suficientes para reconstruir, en la fecha de cada observación:

- lluvia acumulada previa;
- temperatura;
- humedad;
- balance hídrico;
- SMI;
- días de sequía u otras variables meteorológicas;
- altitud;
- vegetación / árboles huéspedes;
- litología / suelo;
- otras variables GIS disponibles en Rainmapper.

**Pero la tarea inmediata NO es importar datos.**\
Primero hay que saber **de qué volumen de registros estamos hablando**.

---

## 2. Ventana temporal relevante

Rainmapper tiene meteorología histórica disponible aproximadamente desde:

**2012-06-19**

Por tanto, para este análisis inicial solo interesan ocurrencias con:

```text
eventDate >= 2012-06-19
```

En la API de GBIF se puede expresar como rango abierto:

```text
eventDate=2012-06-19,*
```

URL-encoded:

```text
eventDate=2012-06-19%2C%2A
```

---

## 3. Área geográfica

El área inicial es **Cataluña**.

GBIF permite filtrar ocurrencias por regiones administrativas GADM mediante `gadmGid`.

El identificador GADM usado para Cataluña es:

```text
ESP.6_1
```

Antes de automatizar nada, verificarlo contra el endpoint GADM actual de GBIF, por ejemplo:

```text
https://api.gbif.org/v1/geocode/gadm/ESP.6_1
```

o mediante la búsqueda GADM documentada por GBIF.

Preferir `gadmGid` frente a `stateProvince`, porque `stateProvince` puede depender del texto suministrado por cada dataset y ser menos consistente.

---

## 4. Especies iniciales

La primera tanda de análisis incluye estas siete:

```text
Lactarius deliciosus
Lactarius sanguifluus
Lactarius vinosus
Boletus edulis
Boletus pinophilus
Boletus aereus
Amanita caesarea
Higrophorus latitabundus
Cantharellus cibarius
```

No ampliar la lista todavía sin indicación del usuario.

---

## 5. API de GBIF

Documentación principal:

- API general: https://techdocs.gbif.org/en/openapi/
- Occurrence API: https://techdocs.gbif.org/en/openapi/v1/occurrence
- Species API: https://techdocs.gbif.org/en/openapi/v1/species
- Interpretación taxonómica: https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation

Base URL:

```text
https://api.gbif.org/
```

La API es REST y devuelve normalmente JSON.

Para las consultas GET ordinarias de búsqueda no se necesita autenticación.

GBIF puede aplicar rate limiting si se hacen muchas consultas. Para siete especies y consultas de conteo no debería ser un problema, pero el código debe comprobar códigos HTTP y no hacer reintentos agresivos.

---

## 6. Cómo obtener SOLO el recuento, sin descargar observaciones

La forma ya comprobada es usar:

```text
/v1/occurrence/search
```

con:

```text
limit=0
```

La respuesta contiene algo de este estilo:

```json
{
  "offset": 0,
  "limit": 0,
  "endOfRecords": false,
  "count": 752,
  "results": [],
  "facets": []
}
```

El valor importante es:

```text
count
```

Con `limit=0`, no necesitamos recuperar los registros de ocurrencia para esta primera fase.

### Consulta de control que YA se ha probado

Se probó manualmente:

```text
https://api.gbif.org/v1/occurrence/search?scientificName=Boletus+edulis&country=ES&eventDate=2012-06-19%2C%2A&limit=0
```

El resultado observado fue:

```text
count = 752
```

Esto significa:

**Boletus edulis + España + desde 2012-06-19 + todas las fuentes que GBIF recupera con ese filtro.**

IMPORTANTE: este valor es solo un **control para España**, no el recuento de Cataluña y no debe usarse como resultado final del análisis.

---

## 7. No confiar únicamente en `scientificName`

Para los recuentos finales conviene resolver primero cada nombre contra la taxonomía de GBIF.

GBIF dispone del Species Match API. Preferir la versión actual:

```text
GET /v2/species/match
```

Ejemplo conceptual:

```text
https://api.gbif.org/v2/species/match?scientificName=Boletus%20edulis
```

Guardar para cada especie, como mínimo:

```text
nombre solicitado
nombre aceptado por GBIF
usage/taxon key
rank
status
canonicalName
```

Después usar el identificador taxonómico devuelto para consultar ocurrencias.

GBIF soporta filtros por `taxonKey` / `taxon_key` en Occurrence Search. Codex debe mirar la forma exacta recomendada por la versión actual de la documentación y usarla consistentemente.

### Por qué hacer esto

Una búsqueda textual por:

```text
scientificName=...
```

puede comportarse de forma distinta frente a:

```text
taxonKey=...
```

especialmente con:

- sinónimos;
- recombinaciones;
- nombres históricos;
- infraespecies;
- cambios taxonómicos.

Para un estudio reproducible es mejor registrar explícitamente qué taxón resolvió GBIF y qué key se utilizó.

---

## 8. Caso especial: `Lactarius vinosus`

Este punto es **muy importante**.

Actualmente GBIF / Catalogue of Life relaciona:

```text
Lactarius vinosus
```

con:

```text
Lactarius sanguifluus
```

En GBIF aparecen, entre otros, como sinónimos/combinaciones de `Lactarius sanguifluus`:

```text
Lactarius vinosus (Quél.) Bataille
Lactarius sanguifluus var. vinosus Quél.
Lactarius sanguifluus f. vinosus (Quél.) Lalli & Pacioni
Lactarius vinosus Maire, Dumée & L. Lutz
```

Referencias:

- https://www.gbif.org/es/taxon/3RS8C
- https://www.gbif.org/species/8134570

Rainmapper, sin embargo, **mantiene `Lactarius sanguifluus` y `Lactarius vinosus` como entidades distintas**.

Por tanto:

**NO aceptar sin más un recuento de `taxonKey` de `L. vinosus` si GBIF lo resuelve a `L. sanguifluus`.**

Hay que investigar qué está contando realmente la consulta.

Como mínimo, para este caso comparar:

1. `scientificName=Lactarius vinosus`
2. la consulta por el taxon/usage key que devuelva Species Match;
3. `verbatimScientificName=Lactarius vinosus`, si el endpoint actual permite ese filtro;
4. registros bajo `Lactarius sanguifluus` cuyo nombre original/verbatim contenga `vinosus`;
5. si procede, variantes `var. vinosus` / `f. vinosus`.

El objetivo es poder distinguir:

```text
identificación originalmente publicada como vinosus
```

de:

```text
registro normalizado por GBIF bajo sanguifluus
```

No mezclar ambas especies automáticamente.

---

## 9. Consulta objetivo para los recuentos de Cataluña

Conceptualmente, cada consulta debe aplicar:

```text
taxon = especie resuelta
gadmGid = ESP.6_1
eventDate = 2012-06-19,*
limit = 0
```

Ejemplo con nombre científico, útil como consulta de control:

```text
https://api.gbif.org/v1/occurrence/search?scientificName=Boletus+edulis&gadmGid=ESP.6_1&eventDate=2012-06-19%2C%2A&limit=0
```

Para el resultado definitivo, comparar esa consulta con la equivalente por `taxonKey`.

---

## 10. Primera tarea concreta que debe ejecutar Codex

### Fase A — validar taxonomía

Para cada una de las siete especies:

1. llamar a Species Match;
2. guardar la respuesta relevante;
3. identificar nombre aceptado, status y key;
4. señalar cualquier caso ambiguo o sinónimo.

### Fase B — obtener recuentos

Para cada especie:

1. contar ocurrencias en Cataluña;
2. desde `2012-06-19`;
3. sin aplicar todavía filtros de licencia;
4. sin exigir todavía coordenadas;
5. sin exigir todavía precisión geográfica;
6. sin descargar registros;
7. usar `limit=0`.

### Resultado esperado

Entregar una tabla como:

| Especie solicitada | Nombre aceptado GBIF | Taxon/usage key | Count Cataluña desde 2012-06-19 | Count usando `scientificName` | Observaciones |
|---|---|---:|---:|---:|---|
| Lactarius deliciosus | ... | ... | ... | ... | ... |
| Lactarius sanguifluus | ... | ... | ... | ... | ... |
| Lactarius vinosus | ... | ... | ... | ... | revisar sinonimia |
| Boletus edulis | ... | ... | ... | ... | ... |
| Boletus pinophilus | ... | ... | ... | ... | ... |
| Boletus aereus | ... | ... | ... | ... | ... |
| Amanita caesarea | ... | ... | ... | ... | ... |

Además, incluir la **URL exacta de cada consulta** o los parámetros exactos usados para que el resultado sea reproducible.

---

## 11. Script mínimo sugerido para esta fase

No es obligatorio usar exactamente este código; es solo una guía.

```python
import requests

BASE = "https://api.gbif.org"

species = [
    "Lactarius deliciosus",
    "Lactarius sanguifluus",
    "Lactarius vinosus",
    "Boletus edulis",
    "Boletus pinophilus",
    "Boletus aereus",
    "Amanita caesarea",
]

session = requests.Session()
session.headers.update({
    "User-Agent": "Rainmapper-GBIF-exploration/1.0"
})

def species_match(name: str) -> dict:
    r = session.get(
        f"{BASE}/v2/species/match",
        params={"scientificName": name},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def occurrence_count_by_name(name: str) -> tuple[int, str]:
    params = {
        "scientificName": name,
        "gadmGid": "ESP.6_1",
        "eventDate": "2012-06-19,*",
        "limit": 0,
    }
    r = session.get(
        f"{BASE}/v1/occurrence/search",
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["count"], r.url

for name in species:
    match = species_match(name)
    count_name, url_name = occurrence_count_by_name(name)

    print("=" * 80)
    print("Requested:", name)
    print("Match:", match)
    print("Count by scientificName:", count_name)
    print("URL:", url_name)
```

Después de inspeccionar la forma exacta del JSON de Species Match, añadir la consulta por `taxonKey`.

No asumir a ciegas qué campo del JSON contiene la key: usar el campo documentado por la respuesta actual (`usage.key`, `taxonKey`, etc., según la versión).

---

## 12. FungaCAT: fuente especialmente relevante

Existe en GBIF el dataset:

**FungaCAT: Banco de datos de los hongos de Cataluña**

GBIF dataset UUID:

```text
8583f4f6-f762-11e1-a439-00145eb45e9a
```

DOI:

```text
10.15468/ttivpp
```

Página:

https://www.gbif.org/es/dataset/8583f4f6-f762-11e1-a439-00145eb45e9a

Publicador:

```text
Banc de dades de biodiversitat de Catalunya
```

Licencia:

```text
CC BY-NC 4.0
```

FungaCAT está orientado específicamente a recopilar registros bibliográficos y de distribución de hongos de Cataluña.

También dispone de archivo fuente Darwin Core Archive (DwC-A), pero:

**NO descargarlo en esta fase.**

Más adelante puede ser útil comparar:

```text
GBIF total
vs
FungaCAT
vs
iNaturalist
vs
otros datasets
```

para saber de dónde proceden realmente los registros.

---

## 13. Licencias: decisión actual del proyecto

BoletRadar aparentemente excluye registros `CC BY-NC` y trabaja con licencias más permisivas como CC0 / CC BY.

Rainmapper es actualmente un **proyecto personal y de uso no comercial**.

Por tanto, en este análisis:

**NO excluir CC BY-NC.**

FungaCAT debe entrar en los recuentos.

Aun así, para cualquier uso posterior:

- conservar `license`;
- conservar dataset / publisher;
- conservar la atribución;
- no eliminar metadatos de procedencia.

Si Rainmapper se publicara o cambiara de modelo de uso, revisar de nuevo las condiciones de licencia antes de redistribuir datos.

---

## 14. Qué información puede recuperarse de una ocurrencia GBIF

En una fase posterior, si se decide importar registros, interesan especialmente estos campos.

### Identidad / taxonomía

```text
key / gbifID
occurrenceID
scientificName
canonicalName
acceptedScientificName
verbatimScientificName
taxonKey
acceptedTaxonKey
speciesKey
taxonRank
taxonomicStatus
```

### Fecha

```text
eventDate
year
month
day
```

Para Rainmapper, la fecha completa es crítica porque hay que reconstruir la meteorología previa al día de fructificación/observación.

### Geolocalización

```text
decimalLatitude
decimalLongitude
coordinateUncertaintyInMeters
country
stateProvince
locality
gadm.*
elevation
```

### Calidad / tipo de registro

```text
basisOfRecord
occurrenceStatus
issues
hasCoordinate
```

En una fase de filtrado interesará además detectar problemas geoespaciales.

### Procedencia y licencia

```text
datasetKey
datasetName
publishingOrgKey
institutionCode
collectionCode
catalogNumber
license
references
```

### Autoría / identificación

```text
recordedBy
identifiedBy
identificationRemarks
occurrenceRemarks
```

### Información ecológica potencial

Si el dataset la proporciona:

```text
habitat
associatedTaxa
samplingProtocol
```

No todos los registros tendrán todos estos campos.

---

## 15. Segunda fase posible — NO ejecutar todavía

Después de conocer los recuentos brutos, se podrá preguntar:

> ¿Cuántos de esos registros son realmente útiles para Rainmapper?

Entonces se harán conteos escalonados, por ejemplo:

```text
A. total desde 2012-06-19
B. + coordenadas
C. + fecha completa día/mes/año
D. + sin problemas geoespaciales relevantes
E. + coordinateUncertaintyInMeters <= 100 m
F. + <= 500 m
G. + <= 1 km
H. desglose por dataset
I. desglose por basisOfRecord
J. desglose por año
```

Esto permitirá saber la diferencia entre:

```text
"GBIF tiene X registros"
```

y:

```text
"Rainmapper puede usar realmente Y registros para reconstrucción meteorológica precisa"
```

No ejecutar esta fase hasta que se revisen los primeros recuentos.

---

## 16. Posibles filtros de calidad futuros

Cuando llegue el momento, estudiar:

```text
hasCoordinate=true
occurrenceStatus=PRESENT
sin errores geoespaciales importantes
fecha completa
coordinateUncertaintyInMeters dentro de un umbral
```

No descartar automáticamente:

```text
PRESERVED_SPECIMEN
MATERIAL_CITATION
HUMAN_OBSERVATION
```

sin revisar primero qué significan en cada dataset.

Un espécimen de herbario con fecha exacta y localidad precisa puede ser tan útil o más fiable taxonómicamente que una observación de ciencia ciudadana.

---

## 17. Duplicados: problema a tratar más adelante

GBIF agrega datos de múltiples fuentes.

La misma observación podría aparecer:

- en iNaturalist;
- en un dataset institucional;
- en una base de datos micológica;
- en otro dataset derivado.

Por tanto, más adelante habrá que comprobar duplicados mediante combinaciones de:

```text
occurrenceID
gbifID
datasetKey
catalogNumber
coordinates
eventDate
recordedBy
```

Pero **no hace falta resolver duplicados para el recuento bruto inicial**.

---

## 18. Uso previsto dentro de Rainmapper

Una ocurrencia GBIF potencialmente válida podría terminar convertida conceptualmente en algo parecido a:

```text
species
observation_date
latitude
longitude
source = "GBIF"
source_dataset
source_occurrence_id
coordinate_uncertainty
taxonomic_name_original
taxonomic_name_accepted
license
```

Luego Rainmapper reconstruiría retrospectivamente las variables ambientales para esa coordenada y fecha.

Ejemplo conceptual:

```text
GBIF:
Boletus edulis
2021-10-23
42.x, 1.x

        ↓

Rainmapper recupera:
- lluvia 7/15/30/60 días
- Tmax/Tmin
- humedad
- balance hídrico
- SMI
- sequía
- DEM
- vegetación
- litología
- etc.

        ↓

registro enriquecido para validación / entrenamiento
```

---

## 19. Relación con BoletRadar

La investigación empezó al observar que BoletRadar muestra en su ayuda referencias a:

```text
"observacions GBIF"
```

La interpretación es que utiliza puntos de presencia procedentes de GBIF para contrastar/validar el modelo, no como avisos necesariamente recientes.

Esto llevó a plantear el uso de GBIF como fuente de observaciones externas para Rainmapper.

Rainmapper no tiene por qué copiar los filtros de licencia de BoletRadar, ya que el contexto de uso es distinto.

---

## 20. Qué NO debe hacer Codex todavía

No:

- descargar FungaCAT completo;
- pedir un GBIF Occurrence Download;
- importar registros a la base de datos de Rainmapper;
- modificar `mushroom_profiles.json`;
- entrenar modelos con GBIF;
- mezclar `Lactarius vinosus` con `Lactarius sanguifluus`;
- aplicar filtros arbitrarios de precisión sin mostrar antes el impacto;
- eliminar CC BY-NC;
- introducir cambios de código en producción.

La primera entrega es **solo investigación reproducible + recuentos**.

---

## 21. Entregable esperado de Codex

Crear preferiblemente un informe Markdown, por ejemplo:

```text
docs/gbif-occurrence-assessment.md
```

con:

1. fecha/hora de ejecución;
2. API y endpoints usados;
3. GADM de Cataluña validado;
4. resultado de Species Match para las siete especies;
5. taxon keys;
6. tabla de recuentos desde 2012-06-19;
7. comparación `taxonKey` vs `scientificName`;
8. explicación específica del caso `Lactarius vinosus`;
9. URLs / parámetros exactos usados;
10. errores, warnings o ambigüedades encontrados;
11. ninguna descarga masiva.

Si resulta sencillo, guardar también un script de consulta reproducible, por ejemplo:

```text
tools/gbif_counts.py
```

pero no integrar nada en Rainmapper todavía.

---

## 22. Criterio de éxito de esta primera investigación

Al acabar debemos poder responder con confianza:

> Entre el 19/06/2012 y hoy, ¿cuántos registros GBIF existen en Cataluña para cada una de estas siete especies, qué taxón está contando realmente GBIF y de qué manera se obtuvo el número?

Solo después se decidirá si merece la pena analizar calidad, precisión geográfica y posible incorporación a Rainmapper.

---

## 23. Referencias ya investigadas

### GBIF API

- https://techdocs.gbif.org/en/openapi/
- https://techdocs.gbif.org/en/openapi/v1/occurrence
- https://techdocs.gbif.org/en/openapi/v1/species
- https://techdocs.gbif.org/en/data-processing/taxonomy-interpretation

### FungaCAT

- https://www.gbif.org/es/dataset/8583f4f6-f762-11e1-a439-00145eb45e9a
- DOI: https://doi.org/10.15468/ttivpp

### Lactarius sanguifluus / vinosus

- https://www.gbif.org/es/taxon/3RS8C
- https://www.gbif.org/species/8134570

### GADM / Cataluña

- Código usado: `ESP.6_1`
- Validar siempre contra el servicio GADM actual de GBIF antes de ejecutar el lote.

---

## 24. Resumen ultra corto para empezar

Si Codex solo necesita saber qué hacer primero:

```text
1. Verifica que ESP.6_1 corresponde actualmente a Cataluña en GBIF.
2. Resuelve las 7 especies con /v2/species/match.
3. Para cada especie consulta /v1/occurrence/search.
4. Filtros:
   - Cataluña
   - eventDate=2012-06-19,*
   - limit=0
5. Obtén únicamente "count".
6. Compara taxonKey vs scientificName.
7. Trata Lactarius vinosus como caso especial por su sinonimia con L. sanguifluus.
8. No descargues registros ni datasets.
9. Devuelve tabla + URLs reproducibles.
```
