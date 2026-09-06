# Rainmapper — GIS/DEM para Cerdanya francesa
## Handoff simple para Codex

**Fecha:** 6 septiembre 2026
**Objetivo:** añadir a Rainmapper capas GIS francesas útiles para la Cerdanya francesa sin complicar la arquitectura.

---

## 1. Qué fuentes usar

Para una primera implementación usar sólo estas cuatro:

| Necesidad | Fuente | Producto | Prioridad |
|---|---|---|---|
| Altitud / relieve | IGN | MNT LiDAR HD | Muy alta |
| Bosque / vegetación forestal | IGN / OPenIG | BD Forêt V2 D66 | Muy alta |
| Litología | BRGM | BD Charm-50 D66 | Muy alta |
| Uso/cobertura del suelo | OPenIG / IGN | OCSID D66 2021 | Alta |

Opcional después:

- BD TOPO sólo si queremos hidrografía o distancias a cursos de agua.
- No añadir por ahora CarHab, suelos, ortofoto, MNH, bosque histórico, etc.

---

## 2. DEM — IGN MNT LiDAR HD

Fuente oficial:

https://www.data.gouv.fr/datasets/mnt-lidar-hd

Mapa de disponibilidad:

https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD

Características verificadas:

- GeoTIFF
- teselas de 1 km × 1 km
- resolución de 50 cm
- Licence Ouverte 2.0
- cobertura nacional francesa
- producto oficial IGN

Para Rainmapper no hace falta trabajar a 50 cm.

### Recomendación

Descargar únicamente las teselas que cubran el área francesa de interés y generar un DEM de trabajo a:

```text
5 m
```

El DEM debe permitir obtener como mínimo:

```text
elevation
slope
aspect
```

Si Rainmapper ya calcula pendiente/orientación a partir del DEM español, reutilizar exactamente el mismo procedimiento.

No crear una nueva arquitectura sólo para Francia.

---

## 3. Bosque — BD Forêt V2 Pyrénées-Orientales

Dataset:

https://www.data.gouv.fr/datasets/bdforet-v2-pyrenees-orientales-2019

Es una base vectorial oficial de referencia para formaciones forestales.

Características:

- formato Shapefile
- departamento 66 completo
- distingue composición y esencia/formación dominante
- Licence Ouverte 2.0
- versión D66: 2019

Esto es especialmente útil para el predictor de setas.

### Implementación

1. Descargar el Shapefile.
2. Inspeccionar los campos y códigos reales.
3. Recortar a la zona usada por Rainmapper.
4. Mapear los tipos franceses a la taxonomía forestal que ya use Rainmapper.

No inventar mappings antes de inspeccionar los valores reales.

Ejemplo conceptual:

```text
BD Forêt source class
        ↓
gis_mapping
        ↓
Rainmapper forest / host type
```

---

## 4. Litología — BRGM BD Charm-50

Fuente oficial:

https://infoterre.brgm.fr/formulaire/telechargement-cartes-geologiques-departementales-150-000-bd-charm-50

Información BRGM:

https://infoterre.brgm.fr/page/telechargement-cartes-geologiques

Producto:

```text
BD Charm-50
```

Es la cartografía geológica vectorial armonizada de Francia a escala 1:50.000.

Para la Cerdanya francesa seleccionar:

```text
Département 66 — Pyrénées-Orientales
```

Si después Rainmapper se extiende a Quérigut:

```text
Département 09 — Ariège
```

La descarga BRGM se hace mediante formulario y entrega datos SIG en formato Shapefile.

### Implementación

1. Descargar manualmente D66.
2. Guardar el ZIP como fuente raw.
3. Inspeccionar los campos.
4. Recortar al área Rainmapper.
5. Crear mapping a la taxonomía litológica ya existente.

Ejemplo:

```text
BRGM geological unit
        ↓
gis_mapping
        ↓
granite / schist / limestone / alluvium / etc.
```

No intentar automatizar el formulario BRGM ni su CAPTCHA.

---

## 5. Uso del suelo — OCSID D66 2021

Dataset:

https://www.data.gouv.fr/datasets/ocsid-occupation-du-sol-interdepartementale-pyrenees-orientales66

OCSID es una versión más detallada/adaptada para Occitanie de OCS GE.

Características:

- cobertura de Pyrénées-Orientales
- millésime 2021
- Shapefile
- Licence Ouverte 2.0
- separa cobertura y uso del suelo

Usarlo para complementar BD Forêt:

```text
forest
shrubland
grassland
agriculture
bare/open
urban
water
etc.
```

### Prioridad

BD Forêt debe ser la fuente principal para bosque.

OCSID debe servir como contexto general de cobertura del suelo.

---

## 6. Zona geográfica inicial

Para empezar, limitar la descarga a la Cerdanya francesa / Capcir:

```text
Bourg-Madame
Osséja
Saillagouse
Font-Romeu
Bolquère
Mont-Louis
Les Angles
Formiguères
```

No hace falta descargar todo Francia.

Puede definirse una bbox o polígono ligeramente mayor que la zona actual de Rainmapper.

---

## 7. Integración con Rainmapper

La idea debe ser muy simple:

```text
fuente francesa
    ↓
descarga
    ↓
reproyección si hace falta
    ↓
recorte a zona Rainmapper
    ↓
mismo formato interno usado por las capas españolas
```

No crear un sistema GIS francés paralelo.

La frontera sólo debe afectar a la descarga de datos, no al predictor.

Rainmapper debería acabar viendo simplemente:

```text
DEM
forest
lithology
landcover
```

independientemente de si el dato viene de España o Francia.

---

## 8. CRS

Los productos IGN franceses suelen usar:

```text
RGF93 / Lambert-93
EPSG:2154
```

Antes de transformar nada, Codex debe comprobar qué CRS usa actualmente Rainmapper para las capas españolas.

Después reproyectar las capas francesas al CRS interno ya existente.

No cambiar el CRS general de Rainmapper sólo por añadir Francia.

---

## 9. Orden de trabajo para Codex

### Paso 1 — inspeccionar Rainmapper

Localizar:

- cómo se almacena el DEM actual;
- qué CRS usa;
- cómo se calculan altitud, pendiente y orientación;
- cómo funcionan `gis_mappings`;
- qué formatos usa para vegetación y litología.

### Paso 2 — DEM

Probar una pequeña zona alrededor de Font-Romeu:

1. descargar MNT LiDAR HD;
2. unir las teselas necesarias;
3. reducir a 5 m;
4. reproyectar al CRS Rainmapper;
5. comprobar elevaciones.

### Paso 3 — bosque

1. descargar BD Forêt V2 D66;
2. inspeccionar atributos;
3. recortar;
4. proponer mapping al catálogo Rainmapper.

### Paso 4 — geología

1. descargar BD Charm-50 D66;
2. inspeccionar unidades;
3. recortar;
4. proponer mapping de litología.

### Paso 5 — cobertura del suelo

1. descargar OCSID D66 2021;
2. inspeccionar clases;
3. recortar;
4. mapear sólo las categorías necesarias.

---

## 10. Lo que NO hacer todavía

No añadir en esta primera fase:

```text
CarHab
MNH / canopy height
bosques antiguos
suelos detallados
ortofoto
índices topográficos avanzados
descargas WMS en tiempo real
```

Primero conseguir que funcionen bien:

```text
DEM + bosque + litología + landcover
```

---

## 11. Criterio de éxito

La adaptación francesa estará lista cuando Rainmapper pueda consultar, para cualquier punto de la Cerdanya francesa:

```text
altitude
slope
aspect
forest_type
lithology_type
landcover_type
```

usando el mismo modelo interno que ya utiliza para España.

---

## 12. Fuentes verificadas

### DEM IGN

https://www.data.gouv.fr/datasets/mnt-lidar-hd

El dataset oficial indica GeoTIFF, teselas 1×1 km, paso de 50 cm y Licence Ouverte 2.0.

### BD Forêt V2 D66

https://www.data.gouv.fr/datasets/bdforet-v2-pyrenees-orientales-2019

Dataset específico de Pyrénées-Orientales, formato Shapefile, con composición/formación forestal y especie dominante.

### OCSID D66

https://www.data.gouv.fr/datasets/ocsid-occupation-du-sol-interdepartementale-pyrenees-orientales66

Cobertura/uso del suelo adaptado para Pyrénées-Orientales.

### BRGM BD Charm-50

https://infoterre.brgm.fr/formulaire/telechargement-cartes-geologiques-departementales-150-000-bd-charm-50

Cartografía geológica vectorial armonizada a escala 1:50.000.

---

## 13. Instrucción final para Codex

Mantener la implementación sencilla.

Antes de escribir nuevos componentes, reutilizar el pipeline GIS existente de Rainmapper.

El objetivo inmediato no es crear un framework GIS genérico, sino conseguir que las capas francesas sean compatibles con las españolas:

```text
France source
→ transform
→ existing Rainmapper format
```

Si durante la implementación aparece una diferencia importante de CRS, formato o taxonomía, documentarla y resolverla localmente antes de introducir nuevas abstracciones.
