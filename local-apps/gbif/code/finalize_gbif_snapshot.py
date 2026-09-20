"""Validate and document an already downloaded GBIF archive without network access."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def precision(row):
    value = row.get('coordinateUncertaintyInMeters')
    return 'unknown' if value is None else 'le_1000m' if value <= 1000 else 'gt_1000m'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    root = args.snapshot
    manifest_path = root / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['status'] == 'complete'
    rows = json.loads((root / 'occurrences.json').read_text())
    assert len(rows) == manifest['record_count'] == len({r['key'] for r in rows})
    geography_summary = None
    geography_path = root / 'metadata/geography.json'
    if geography_path.exists():
        geography = json.loads(geography_path.read_text())
        assert set(geography['records']) == {str(r['key']) for r in rows}
        for row in rows:
            geo = geography['records'][str(row['key'])]
            assert (geo['latitude'], geo['longitude']) == (row['decimalLatitude'], row['decimalLongitude'])
        for path, expected in geography['input_and_operational_sha256'].items():
            assert sha(Path(path)) == expected, path
        geography_summary = geography['summary']
    browser_path = root / 'viewer/browser-validation.json'
    if browser_path.exists():
        browser = json.loads(browser_path.read_text())
        assert browser['status'] == 'passed'
        for path, expected in browser['sha256'].items():
            assert sha(root / path) == expected, path
    originals = {}
    original_media_checked = 0
    for row in rows:
        key = row['key']
        original = json.loads((root / f'raw/verbatim/{key}.json').read_text())
        assert original['key'] == key and original['datasetKey'] == row['datasetKey']
        originals[key] = original
        media_urls = {m['identifier'] for m in row.get('media', [])}
        for extension, items in original.get('extensions', {}).items():
            if 'Multimedia' not in extension:
                continue
            for item in items:
                url = (item.get('http://rs.tdwg.org/ac/terms/accessURI') or
                       item.get('http://purl.org/dc/terms/identifier'))
                if url:
                    assert url in media_urls, (key, url)
                    original_media_checked += 1
    for request in manifest['requests']:
        assert sha(root / request['path']) == request['sha256'], request['path']
    for path, expected in manifest['protected_sha256_before'].items():
        assert sha(Path(path)) == expected, path
    photos = json.loads((root / 'media/index.json').read_text())
    refs = json.loads((root / 'media/references.json').read_text())
    expected_urls = {m['identifier'] for row in rows for m in row.get('media', [])
                     if m.get('type') == 'StillImage'}
    assert expected_urls == {p['url'] for p in photos} == {r['url'] for r in refs}
    assert len(photos) == len(expected_urls)
    image_formats = Counter()
    for photo in photos:
        if photo['status'] != 'downloaded':
            continue
        path = root / photo['path']
        assert path.stat().st_size == photo['bytes'] and sha(path) == photo['sha256'], path
        with Image.open(path) as image:
            image_formats[image.format] += 1
            image.verify()
    class OfflineLinks(HTMLParser):
        def __init__(self):
            super().__init__()
            self.articles = 0
            self.images = 0

        def handle_starttag(self, tag, attrs):
            self.articles += tag == 'article'
            self.images += tag == 'img'
            for name, value in attrs:
                if name not in ('href', 'src') or not value:
                    continue
                assert not value.startswith(('http:', 'https:', '//')), value
                assert (root / value).is_file(), value

    links = OfflineLinks()
    gallery = root / ('gallery.html' if (root / 'gallery.html').exists() else 'index.html')
    links.feed(gallery.read_text())
    assert links.articles == len(rows)
    assert links.images == sum(p['status'] == 'downloaded' for p in photos)
    # Inspect all source terms offline; keep the raw records untouched.
    term_counts = {'interpreted': dict(Counter(k for r in rows for k in r)),
                   'verbatim': dict(Counter(k for r in originals.values() for k in r))}
    dump(root / 'field-inventory.json', term_counts)
    species = {}
    for row in rows:
        name = row.get('species', row.get('scientificName'))
        species.setdefault(name, Counter()).update([precision(row)])
    dump(root / 'species-precision.json', species)
    # Exclude concurrently produced media/HTML from the record-phase inventory.
    manifest['files'] = {p: info for p, info in manifest['files'].items()
                         if not p.startswith('media/') and p != 'index.html'}
    for path, info in manifest['files'].items():
        assert sha(root / path) == info['sha256'], path
    if (root / 'IN_PROGRESS.json').exists():
        (root / 'IN_PROGRESS.json').rename(root / 'run-started.json')
        manifest['files']['run-started.json'] = manifest['files'].pop('IN_PROGRESS.json')
    dump(manifest_path, manifest)
    media_summary = json.loads((root / 'media/summary.json').read_text())
    table = ['| Taxón GBIF | Total | ≤1 km | >1 km | Desconocida |',
             '| --- | ---: | ---: | ---: | ---: |']
    for name, counts in sorted(species.items()):
        table.append(f'| {name} | {sum(counts.values())} | {counts["le_1000m"]} | '
                     f'{counts["gt_1000m"]} | {counts["unknown"]} |')
    readme = f'''# GBIF: copia local para investigación

Captura de la API pública realizada el 16/09/2026. **{len(rows):,} registros únicos**
de los 21 perfiles del catálogo local, resueltos como 22 taxones consultables.
Catalunya según GADM `ESP.6_1`, fechas 19/06/2012–16/09/2026.
Sin filtros por proveedor, licencia, incertidumbre o calidad. La delimitación GADM
depende de las coordenadas: no incluye registros sin localización que solo nombren Catalunya.

## Consultar la copia local

- Abrir [index.html](index.html): visor MapLibre, selector de especie/todas y filtros de
  incertidumbre; clic en un punto para detalles y fotos. `Mostrar incertidumbre` activa
  los círculos azul claro semitransparentes de las citas con radio conocido. Las desconocidas
  se representan en rojo con 500 m de radio exclusivamente visual; su dato sigue siendo desconocido.
  Los cuatro fondos cartográficos habituales requieren Internet; observaciones y fotos son locales.
  El filtro «≤1 km y desconocidas» incluye todos los registros salvo los de incertidumbre
  declarada >1 km. Altitud (DEM local) y municipio (polígonos IGN locales) aparecen debajo
  de las coordenadas y se refieren al punto publicado, no al conjunto del círculo.
  El mapa ocupa toda la anchura y se ajusta a la ventana; la ficha se abre como panel
  superpuesto con cierre y desplazamiento propio, sin navegador lateral permanente.
  Las fotos se muestran primero y sin recortar; los campos secundarios permanecen
  accesibles en «Más datos y procedencia».
- [gallery.html](gallery.html): galería de fotografías utilizable también sin conexión.
- [review.csv](review.csv) / [review.json](review.json): tabla abreviada para revisar.
- [occurrences.json](occurrences.json): todos los campos interpretados devueltos por la API.
- `raw/search/`: respuestas originales completas y paginadas.
- `raw/verbatim/<GBIF-ID>.json`: todos los campos originales publicados que expone GBIF,
  incluidas extensiones; no se descartan campos desconocidos.
- `metadata/datasets/`: metadatos completos de los cinco datasets proveedores.
- [metadata/taxonomy-map.json](metadata/taxonomy-map.json): nombres originales,
  sinónimos, taxones aceptados y correspondencias con los perfiles de Rainmapper.
- [metadata/profile-memberships.json](metadata/profile-memberships.json): correspondencias
  de consulta, sin convertirlas en importaciones ni etiquetas definitivas de entrenamiento.
- [field-inventory.json](field-inventory.json): campos disponibles y cuántos registros los contienen.
- [metadata/geography.json](metadata/geography.json): resultados locales por observación,
  estados de cobertura, coordenadas usadas y procedencia de DEM y cartografía municipal.
- [media/index.json](media/index.json): URL, ruta local, fecha, tamaño, SHA-256 y resultado de cada foto.
- [media/references.json](media/references.json): relación foto–observación y metadatos
  completos de autoría, licencia y proveedor; la licencia de la foto puede diferir de la del registro.

## Fotografías

URLs únicas: **{len(photos)}**. Descargadas: **{media_summary['statuses'].get('downloaded', 0)}**.
Errores: **{media_summary['statuses'].get('error', 0)}**. Tamaño: **{media_summary['bytes'] / 1024**2:.1f} MiB**.
Se conserva el archivo enlazado por GBIF sin redimensionar ni transformar, no una captura
de pantalla. No se inventan URLs para recuperar fotos adicionales. El visor no consulta GBIF
ni descarga las fotos de nuevo; solo sus fondos cartográficos son externos. La galería funciona
sin recursos externos. Los enlaces de procedencia siguen documentados.

## Cobertura y cautelas taxonómicas

- `Lactarius salmonicolor / quieticolor` se consulta como dos especies.
- `Cantharellus lutescens` resuelve al nombre aceptado `Craterellus lutescens`.
- GBIF reconoce separadamente `Lactarius sanguifluus` y `Lactarius vinosus` en esta captura.
- `Morchella elata complex` se representa aquí solo por el taxón nominal `Morchella elata`:
  no implica cobertura exhaustiva de todas las especies del complejo.
- `Cantharellus cibarius` se consulta por su taxón nominal, sin ampliar de oficio el grupo sensu lato.

## Incertidumbre espacial

{chr(10).join(table)}

El límite ≤1 km es solo un primer criterio de selección posterior, no una garantía de
calidad taxonómica, fecha exacta o independencia de observaciones. Los valores desconocidos
se conservan como desconocidos, nunca como cero. No se corrigen ni descartan registros de esta copia.
Todos los registros de esta captura declaran `PRESENT`: no aportan ausencias para entrenar
por sí solos un clasificador binario. No se ha inferido abundancia «Normal» en los datos originales.

## Revisión manual

Todas las citas empiezan Pendientes. La ficha permite elegir Pendiente, Dudosa, Aceptada o
Rechazada, y el filtro Revisión combina ese estado con los demás selectores.
Cada cambio se guarda automáticamente en este navegador. «Activar guardado en
archivo» permite elegir una carpeta en Chrome: `gbif-revision-autoguardado.json`
se actualiza tras cada cambio. La interfaz confirma «Guardado en archivo» después
de completar la escritura. El archivo se recuerda al reabrir; si falta permiso,
pulsar «Reanudar guardado». Si se borran los datos del navegador, elegir de nuevo
la misma carpeta. Exportar revisión crea una copia voluntaria independiente;
esa exportación no se actualiza sola. Esperar al fin del guardado antes de cerrar.
Importar revisión conserva la decisión más reciente de cada ID y rechaza datos
incompatibles. No hace falta importar al abrir el mismo visor en el mismo navegador.
El CSV original permanece sin estos estados; las observaciones GBIF no se modifican.

Los botones 2D/3D y ↑N bajo el zoom activan el relieve Terrarium online del mapa
de predicción y orientan al norte conservando centro, zoom e inclinación.

## Reproducibilidad e integridad

[manifest.json](manifest.json) conserva URLs, consultas, tiempos, SHA-256 y recuentos
comprobados antes/después. Es una captura de la API viva, no una descarga transaccional con DOI;
que coincidan los recuentos no garantiza que GBIF no haya editado un registro durante la captura.
[validation.json](validation.json) recoge la validación local y
[offline-manifest.json](offline-manifest.json) inventaría el paquete final.
[viewer/browser-validation.json](viewer/browser-validation.json) recoge la prueba del
visor en navegador. Los grupos numerados reúnen puntos por proximidad en pantalla;
no son zonas de fructificación inferidas. Un radio desconocido no se convierte en cero ni
en 500 m en el dato original; los 500 m rojos solo son una convención visual del visor.

La copia reúne los registros de este ámbito y todos sus campos disponibles en los endpoints
consultados; no descarga los datasets mundiales completos de Observation.org o iNaturalist,
ni contenido privado, revisiones históricas o páginas externas enlazadas.

No se han insertado observaciones ni creado setales operativos. Las huellas de observaciones,
setales y catálogo locales se verifican antes/después. La carpeta está excluida de Git y de
Docker; se conserva localmente. No se ha publicado ni relanzado entrenamiento/precálculo.
'''
    (root / 'README.md').write_text(readme)
    validation = {'validated_at': datetime.now(timezone.utc).isoformat(),
                  'records': len(rows), 'verbatim': len(originals),
                  'photos': media_summary['statuses'], 'image_formats_verified': dict(image_formats),
                  'original_media_urls_checked': original_media_checked,
                  'offline_html_articles': links.articles, 'offline_html_images': links.images,
                  'offline_html_local_links_verified': True,
                  'request_hashes_verified': len(manifest['requests']),
                  'protected_files_unchanged': True,
                  'local_geography': geography_summary,
                  'declared_precision': dict(Counter(precision(r) for r in rows)),
                  'occurrence_status': dict(Counter(r.get('occurrenceStatus') for r in rows))}
    dump(root / 'validation.json', validation)
    scripts_dir = root / 'metadata/scripts'
    scripts_dir.mkdir(exist_ok=True)
    for script in ('download_gbif_snapshot.py', 'download_gbif_media.py', 'finalize_gbif_snapshot.py',
                   'build_gbif_viewer.py', 'check_gbif_viewer.mjs', 'enrich_gbif_geography.py'):
        (scripts_dir / script).write_bytes(Path(__file__).with_name(script).read_bytes())
    files = {str(p.relative_to(root)): {'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'offline-manifest.json'}
    dump(root / 'offline-manifest.json', {'completed_at': validation['validated_at'],
         'status': 'complete' if not media_summary['statuses'].get('error') else 'complete_with_media_errors',
         'total_bytes': sum(f['bytes'] for f in files.values()), 'files': files})
    print(json.dumps(validation, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
