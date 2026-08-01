# Importación masiva de observaciones desde fotos de campo

Proceso para clasificar un lote de fotos/vídeos de campo y preparar las observaciones
para importarlas a Rainmapper. Documentado a partir de la campaña de agosto 2026
(818 archivos, sesiones de trabajo con Claude Code).

## Requisitos previos

- Python 3.11 (`../.venv/bin/python`)
- Acceso a `mushroom-data/mushroom_known_sites.json` (áreas y micro-áreas con geometría)
- Acceso a `mushroom-data/mushroom_observations.json` (observaciones existentes)
- `exiftool` instalado (`brew install exiftool` en macOS)

## Estructura de trabajo

```
<directorio-fotos>/
  candidates/
    review_table.json       # tabla de trabajo — generada y actualizada en cada paso
    README.md               # resumen del lote (generado)
  identified/
    valid/                  # fotos con confianza "valid"
    draft/                  # fotos con confianza "draft"
    doubtful/               # fotos con confianza "doubtful"
  unidentified/             # fotos sin identificar
```

---

## Paso 1 — Revisión visual y clasificación

**Manual.** Revisar cada foto/vídeo individualmente y asignar:

| Campo | Valores | Notas |
|-------|---------|-------|
| `species` | Nombre científico | Texto libre; múltiples especies separadas por ` + ` |
| `confidence` | `confirmed`, `confirmed/probable`, `confirmed/doubtful`, `probable`, `probable/doubtful`, `doubtful`, `unidentified` | Ver mapeo en paso 2 |
| `notes` | Texto libre | Descripción morfológica, contexto, dudas |

Resultado: borrador de `review_table.json` con un objeto por archivo.

---

## Paso 2 — Mapeo de confianza a estados Rainmapper

Los valores de confianza propios se mapean al campo `validation_status` de Rainmapper:

| Confianza propia | `validation_status` Rainmapper |
|-----------------|-------------------------------|
| `confirmed` | `valid` |
| `confirmed/probable` | `draft` |
| `confirmed/doubtful` | `doubtful` |
| `probable` | `draft` |
| `probable/doubtful` | `doubtful` |
| `doubtful` | `doubtful` |
| `unidentified` | — (no importar) |

El campo `calibration_use` se fija a `"review"` para **todas** las observaciones
importadas, independientemente del `validation_status`. Esto permite filtrarlas en
la UI de Rainmapper y asegura que no entran en el modelo hasta que se revisen
manualmente y se pasen a `"include"`. Las observaciones de campo directo del
usuario tienen `calibration_use: "include"`.

---

## Paso 3 — Extracción de metadatos EXIF

Para cada archivo extraer con `exiftool`:

```bash
exiftool -csv -DateTimeOriginal -GPSLatitude -GPSLatitudeRef \
         -GPSLongitude -GPSLongitudeRef -GPSAltitude \
         identified/ unidentified/ > exif_raw.csv
```

Campos relevantes:
- `DateTimeOriginal` → `date` (formato `YYYY-MM-DD`)
- `GPSLatitude` + `GPSLatitudeRef` → `lat`
- `GPSLongitude` + `GPSLongitudeRef` → `lon`
- `GPSAltitude` → `alt`

**Fallback de fecha:** si un archivo no tiene `DateTimeOriginal`, usar el `birthtime`
del sistema de ficheros (fecha de creación en macOS/Finder). Los archivos deben
**moverse** (`mv`), no copiarse (`cp`), para preservar ese `birthtime`.

---

## Paso 4 — Estandarización de coordenadas a decimal WGS84

Las coordenadas GPS del EXIF suelen venir en formato DMS
(grados°minutos'segundos"). Convertir siempre a decimal WGS84:

```
decimal = grados + minutos/60 + segundos/3600
```

Negativo para Sur (S) y Oeste (W).

**Importante:** hacer doble check de la conversión antes de actualizar el JSON.
Rainmapper almacena siempre en decimal WGS84. Nunca usar formato DMS.

Verificación rápida: coordenadas de Cataluña → latitud ~40–43°N, longitud ~0–3°E.
Longitudes fuera de ese rango son anomalías GPS (marcar en `notes`).

---

## Paso 5 — Organización de archivos en carpetas

Mover cada archivo a la carpeta correspondiente a su estado Rainmapper:

```
identified/valid/      ← confidence == "valid"
identified/draft/      ← confidence == "draft"
identified/doubtful/   ← confidence == "doubtful"
unidentified/          ← unidentified
```

Usar `mv` (no `cp`) para preservar el `birthtime` de Finder.

Añadir el campo `folder` a cada fila del `review_table.json` con la ruta relativa
(ej. `"identified/valid"`). Este campo facilita saber dónde está cada archivo
cuando se vaya a subir a Rainmapper.

---

## Paso 6 — Asignación de área y micro-área

Script: [`01_assign_areas.py`](01_assign_areas.py)

Algoritmo ray-casting point-in-polygon contra los polígonos de
`mushroom_known_sites.json`. Para cada foto:

1. Si cae dentro de un área y dentro de una micro-área → asigna ambos IDs.
2. Si cae dentro de un área pero fuera de todas las micro-áreas → busca la
   micro-área más cercana por distancia al centroide. Si está a ≤3 km, la asigna;
   si está a >3 km → `micro_area_id: "pending"` (hay que crear una nueva micro-área).
3. Si no cae en ningún área → `area_id: null`, `micro_area_id: null`.

Campos que añade al `review_table.json`: `area_id`, `micro_area_id`.

```bash
.venv/bin/python scripts/observations-mass-import/01_assign_areas.py \
  --review-table "/ruta/a/candidates/review_table.json" \
  --known-sites docker-data/mushroom-data/mushroom_known_sites.json
```

---

## Paso 7 — Asignación de evidencia de campo

Script: [`02_assign_evidence.py`](02_assign_evidence.py)

Para cada foto con `micro_area_id` asignado (no `null` ni `"pending"`), busca la
observación Rainmapper más cercana geográficamente dentro de esa misma micro-área
y copia sus campos `site_context`.

Campos que añade al `review_table.json` (nombres reales del schema de Rainmapper):
- `observed_host_ids`
- `observed_forest_type_ids`
- `observed_soil_tendency_ids`
- `observed_habitat_feature_ids`
- `observed_aspect_ids`

Campos de gestión del proceso:
- `evidence_source_obs_id` — ID de la observación usada como referencia
- `evidence_source_dist_m` — distancia en metros a esa observación
- `evidence_status` — `"suggested"` (sugerencia automática), `"no_area"` (sin micro-área), `"no_obs_in_area"` (micro-área sin obs existentes)

Todos los valores con `evidence_status: "suggested"` deben revisarse manualmente
antes de importar. El campo `evidence_source_dist_m` ayuda a priorizar: distancias
grandes (>500 m) merecen más atención.

```bash
.venv/bin/python scripts/observations-mass-import/02_assign_evidence.py \
  --review-table "/ruta/a/candidates/review_table.json" \
  --observations docker-data/mushroom-data/mushroom_observations.json
```

---

## Pasos completados (fase actual)

### Paso 8 — Mapeo especie → species_id ✓

Script: [`03_map_species.py`](03_map_species.py)

Mapea el campo `species` (texto libre) al `species_id` de Rainmapper. Gestiona
especies simples, multi-especie y sin perfil. Añade a `review_table.json`:
- `species_ids` — lista de species_id mapeados
- `species_unmapped` — partes sin perfil
- `species_mapping_status` — `mapped`, `no_profile`, `multi_full`, `multi_partial`, `multi_none`, `unidentified`

**Aliases de usuario** (en `USER_NAME_ALIASES` del script) — especies "sp." que
este usuario identifica siempre a nivel de especie concreta:
- `Tricholoma sp.` → `tricholoma_terreum` (el único Tricholoma que recoge)
- `Morchella sp.` → `morchella_elata_complex`
- `Russula sp.` → `russula_virescens` (pendiente de revisión individual)

**Reglas contextuales** (en `CONTEXT_RULES`) — `Boletus sp.` resuelto por contexto:
- `Boletus sp.` + `Amanita caesarea` → `boletus_aereus` (co-fructificación encinar)
- `Boletus sp.` + `Lactarius deliciosus` → `boletus_edulis` (por época)
- `Boletus sp.` + `Tricholoma terreum` → `boletus_edulis` (por época)
- `Boletus sp.` + `Boletus edulis` → `boletus_edulis`

**Regla por altitud/época** para `Boletus sp.` standalone:
- < 1000 m → `boletus_aereus`
- ≥ 1000 m + otoño (sep–nov) → `boletus_edulis`
- ≥ 1000 m + otra época → `boletus_pinophilus`

**Especies sin perfil** (18 especies, ~47 fotos): se ignoran — no se importan,
no se mueven los archivos. Si se crea un perfil nuevo, basta con relanzar el
script para que se mapeen automáticamente.

**Fotos multi-especie** (`"Boletus aereus + Amanita caesarea"`): generan una
observación por cada `species_id` mapeado, con todos los campos idénticos excepto
`species_id`.

```bash
.venv/bin/python scripts/observations-mass-import/03_map_species.py \
  --review-table "/ruta/a/candidates/review_table.json" \
  --profiles docker-data/mushroom-data/mushroom_profiles.json
```

**Resultado campaña agosto 2026:** 679 observaciones importables de 818 archivos
(846 antes de eliminar 148 por MOVs Live Photo companion, 44 sin perfil, 3 no identificadas).

---

### Paso 9 — Creación de micro-áreas pendientes (en Rainmapper UI)

Las 5 fotos con `micro_area_id: "pending"` se importan con `micro_area_id: null`
hasta que se creen las micro-áreas correspondientes en Rainmapper.

---

## Pasos completados (continuación)

### Paso 9b — Eliminación de MOVs Live Photo ✓

Los iPhones graban Live Photos como un par HEIC+MOV con el mismo nombre base.
El MOV companion no aporta valor (≈2 s sin contexto) y genera una observación
duplicada de la misma captura.

El script `04_generate_observations.py` detecta automáticamente estos pares
(mismo `folder` + mismo stem, uno `.heic`/`.heif` y otro `.mov`) y omite el MOV.
No requiere intervención manual.

**Campaña agosto 2026:** 154 MOVs companion detectados y omitidos → 148
observaciones eliminadas (algunas eran multi-especie).

---

### Paso 10 — Generación del JSON de observaciones con media ✓

Script: [`04_generate_observations.py`](04_generate_observations.py)
Módulo de media: [`media_utils.py`](media_utils.py)

Genera observaciones desde `review_table.json`, procesa la media asociada y
fusiona directamente con `mushroom_observations.json` existente.

Comportamiento:
- Para cada foto, procesa el archivo fuente (`<photos-dir>/<folder>/<fname>`)
  vía `media_utils` y adjunta el resultado al campo `media` de la observación.
- **Idempotente**: si el fichero de destino ya existe en `media/`, salta el
  procesado y reconstruye el entry desde el existente. Se puede relanzar tras
  un fallo sin rehacer trabajo previo.
- **Multi-especie**: la misma foto genera N observaciones que comparten la misma
  media entry (el fichero solo se procesa una vez).
- Validación programática antes de escribir: sin IDs duplicados, campos
  obligatorios presentes, species_ids válidos.
- Salida: fichero JSON fusionado (existentes + nuevas).

**Media — imágenes** (JPG, HEIC, HEIF) via `media_utils.process_image()`:
- Redimensionado a máximo **1600 px** por lado, JPEG calidad **86**, EXIF preservado
- Destino: `mushroom-data/media/observation-photos/<año>/<nombre>.jpg`

**Media — vídeos** (MOV, MP4) via `media_utils.process_video()`:
- Convertido con `ffmpeg` a máximo **30 s**, resolución **854×480**
- Destino: `mushroom-data/media/observation-videos/<año>/<nombre>.mp4`
- Requiere `ffmpeg` instalado (`brew install ffmpeg` en macOS)

```bash
.venv/bin/python scripts/observations-mass-import/04_generate_observations.py \
  --review-table "/ruta/a/candidates/review_table.json" \
  --observations docker-data/mushroom-data/mushroom_observations.json \
  --photos-dir "/ruta/a/candidates" \
  --media-dir docker-data/mushroom-data \
  --profiles docker-data/mushroom-data/mushroom_profiles.json \
  --output "/ruta/a/candidates/mushroom_observations_merged.json"
```

**Resultado campaña agosto 2026:** 846 observaciones, validación OK.

## Pasos pendientes

### Paso 11 — Subida a HA (pendiente)

Reemplazar `mushroom_observations.json` en HA (vía SSH o acceso directo a
`/share/rainmapper/mushroom-data/`) con el fichero generado y validado localmente.
Copiar también la carpeta `media/` con los archivos procesados.
No mezclar con datos de HA ni tocar `users.json`, `devices.json` ni históricos
meteorológicos.

---

## Resultados de la campaña agosto 2026

| Estado | Fotos |
|--------|------:|
| Con micro-área asignada + evidencia sugerida | 625 |
| Con micro-área pendiente de crear | 5 |
| Sin área conocida | 188 |
| No identificadas | 3 |
| **Total** | **818** |

Distancias foto → observación de referencia: mediana **51 m** · p90 **445 m** · máximo **2.080 m**.
