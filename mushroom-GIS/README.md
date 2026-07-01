# Local mushroom GIS workspace

This directory is for local GIS layers used by the mushroom observation lab.

The actual GIS datasets are intentionally ignored by Git and must not be
included in the Home Assistant image. Keep downloaded shapefiles, rasters,
PDF manuals and derived local inspection files here only when they are needed
for local experiments.

Current local datasets:

- `MVC50mil/`: Mapa de vegetacio de Catalunya 1:50.000, inspected as the
  candidate v0 source for Catalonia vegetation, hosts, habitat and preferred
  substrate. This is the local copy of the unified MVC50 shapefile, not data to
  be committed.
  - `source/MVC50mil.zip`: original downloaded artifact from the UB source.
  - `extracted/`: expanded shapefile sidecar files and PDF documentation used
    by local inspection and future scripts.
- `sols-25000-v1r1-202512/`: discarded for mushroom predictor v0. It was
  inspected as an ICGC Mapa de suelos 1:25.000 candidate, but local QGIS/probe
  validation showed broad gaps and it does not map cleanly enough to the
  predictor's internal soil IDs. Keep it out of active reconstruction.
  - `source/sols-25000-v1r1-202512.zip`: original downloaded artifact from
    ICGC.
  - `extracted/`: expanded shapefile, layer styles, metadata HTML and technical
    specifications PDF used by local inspection and future scripts.
- `geologia-territorial-50000-geologic-v3r0-202412/`: ICGC Geologic 1:50,000
  territorial dataset, inspected as the candidate v0 source for Catalonia
  geology/lithology context.
  - `source/geologia-territorial-50000-geologic-v3r0-202412.zip`: original
    downloaded GeoPackage artifact from ICGC.
  - `extracted/`: GeoPackage, QGIS layer file, metadata HTML and technical PDF.
- `model-elevacions-terreny-topografic-catalunya-5m-2009-2018/`: ICGC
  topographic terrain elevation model for Catalonia, inspected as the candidate
  v0 DEM/topography source.
  - `extracted/model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif`:
    local GeoTIFF used for elevation sampling and future slope/aspect
    derivation.

## MVC50 origin and attribution

Source page:

- https://www.ub.edu/geoveg/cat/cartovegetacio.php

Official dataset page title:

- `Cartografia de la vegetacio de Catalunya 1:50.000`

Origin summary:

- The 1:50,000 vegetation map series started in 1983 with sheet 295
  `Banyoles`.
- The work was coordinated by the `Grup de Geobotanica i Cartografia de la
  Vegetacio` at the `Universitat de Barcelona`.
- The full sheet series was completed in 2016.
- In 2018 the sheet series was unified into a single cartographic document,
  with harmonized legends, continuity criteria between sheets and interpretation
  criteria.

Recommended citation from the source page:

- `Carrillo, E.; Ferre, A.; Illa, E.; Mercade, A. (editors) 2018. Mapa de
  vegetacio de Catalunya, E. 1:50.000. Universitat de Barcelona.`

Relevant source links:

- Unified MVC50 download, shapefile in ETRS89:
  http://atzavara.bio.ub.edu/mapes_descarrega/MVC50mil.zip
- Methodological document:
  http://atzavara.bio.ub.edu/geoveg/docs/MapaVegetacioCatalunya_50mil_2018.pdf
- SEMHAVEG map server, for visual inspection of habitats and vegetation maps:
  http://www.ub.edu/geoveg/cat/semhaveg.php

Other potentially useful resources on the source page:

- Original 1:50,000 sheets, available per sheet as shapefiles in ED50 and
  ETRS89 and as PDF maps.
- Some sheets include a `Memoria` PDF in the UB repository.
- A potential vegetation print figure is available as JPEG, but it should be
  treated as visual/reference material rather than a primary machine-readable
  predictor layer.

## Discarded ICGC soils candidate

Source page:

- https://www.icgc.cat/es/Ambitos-tematicos/Territorio-sostenible/Suelos/Mapa-de-suelos-125000-continuo

Official dataset page title:

- `Mapa de suelos 1:25.000 (continuo)`

Origin summary:

- The MSC25M soil map started in 2009 as a collaboration between the
  agricultural administration and the ICGC.
- Since 2021 the continuous soil cartography is distributed as a single Esri
  Shapefile.
- The ICGC page says the map is represented continuously across the territory
  with available coverage, and also states that detailed information is
  available for approximately 25% of Catalonia's agricultural surface.
- The page states the last update as December 2025.
- The dataset uses ETRS89 / UTM zone 31N, EPSG:25831.

Local validation note:

- The downloaded `sols-25000-v1r1-202512` layer shows broad gaps when opened in
  QGIS.
- The official "continuous" wording must therefore be read together with
  "available coverage" and the 25% detailed-information caveat, not as a
  guarantee that every point in Catalonia has soil polygon detail.
- Initial observation probes returned `no_coverage_at_point` for this layer
  while MVC50, geology and DEM returned data for the same point.
- Rainmapper must therefore not use this layer in v0 reconstruction. Predictive
  substrate comes from `MVC50.LLVA_Subst`.

License:

- ICGC geoinformation is stated as Creative Commons Attribution 4.0
  International, CC BY 4.0.

Relevant source links:

- Source page:
  https://www.icgc.cat/es/Ambitos-tematicos/Territorio-sostenible/Suelos/Mapa-de-suelos-125000-continuo
- Downloaded shapefile:
  https://datacloud.icgc.cat/datacloud/sols-25000/shp/sols-25000-v1r1-202512.zip
- Metadata:
  https://catalegs.ide.cat/geonetwork/srv/cat/catalog.search#/metadata/sols-25000-v1r1-202512
- Technical specifications v1.1:
  https://datacloud.ide.cat/especificacions/sols-25000-v1r1-20260121.pdf

## ICGC geology origin and attribution

Local dataset:

- `geologia-territorial-50000-geologic-v3r0-202412`

Source metadata:

- https://catalegs.ide.cat/geonetwork/srv/cat/catalog.search#/metadata/geologia-territorial-50000-geologic-v3r0-202412

Local inspection result:

- The GeoPackage contains polygon layer `_04_unitats_geologiques_50000`, which
  has geological unit codes, descriptions, age fields, metamorphism fields and
  protolith fields.

## ICGC DEM origin and attribution

Local dataset:

- `model-elevacions-terreny-topografic-catalunya-5m-2009-2018`

Source metadata:

- https://catalegs.ide.cat/geonetwork/srv/cat/catalog.search#/metadata/model-elevacions-terreny-topografic-catalunya-5m-2009-2018

Source download:

- https://datacloud.icgc.cat/datacloud/model-elevacions-terreny/tif_unzip/model-elevacions-terreny-topografic-catalunya-5m-2009-2018.tif

Local inspection result:

- GeoTIFF with one `Float32` elevation band.
- ETRS89 / UTM zone 31N, EPSG:25831.
- 5 m pixel size.
- `NoData = -9999`.
- Internal overviews are present.

Rules:

- Do not commit real GIS layers.
- Do not copy these files into `rainmapper-app/` or versioned defaults.
- Keep source metadata and licensing notes in `docs/mushrooms/gis-layer-inventory-es.md`.
