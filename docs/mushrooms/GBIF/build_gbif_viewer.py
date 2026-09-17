"""Build the standalone MapLibre research viewer from the existing local snapshot."""
import argparse
import hashlib
import json
from pathlib import Path


def js_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--maplibre-js', type=Path, required=True)
    parser.add_argument('--maplibre-css', type=Path, required=True)
    args = parser.parse_args()
    root = args.snapshot
    assets = root / 'viewer'
    assets.mkdir(exist_ok=True)
    rows = json.loads((root / 'occurrences.json').read_text())
    memberships = json.loads((root / 'metadata/profile-memberships.json').read_text())
    profiles = json.loads((root / 'metadata/catalog.json').read_text())['species_profiles']
    media = {m['url']: m for m in json.loads((root / 'media/index.json').read_text())}
    datasets = {p.stem: json.loads(p.read_text())['title'] for p in (root / 'metadata/datasets').glob('*.json')}
    geography_path = root / 'metadata/geography.json'
    geography = json.loads(geography_path.read_text())['records'] if geography_path.exists() else {}
    if geography:
        assert set(geography) == {str(r['key']) for r in rows}, 'Geography does not match the snapshot'
    def original_value(original, name):
        return original.get('http://rs.tdwg.org/dwc/terms/' + name)
    compact = []
    for row in rows:
        original = json.loads((root / f'raw/verbatim/{row["key"]}.json').read_text())
        detail = {k: row.get(k) for k in ('key', 'scientificName', 'species', 'eventDate',
                  'decimalLatitude', 'decimalLongitude', 'coordinateUncertaintyInMeters',
                  'recordedBy', 'locality', 'habitat', 'individualCount', 'organismQuantity',
                  'organismQuantityType', 'occurrenceRemarks', 'informationWithheld',
                  'dataGeneralizations', 'license', 'basisOfRecord', 'issues')}
        for name in ('locality', 'habitat', 'occurrenceRemarks', 'recordedBy'):
            detail[name] = detail.get(name) or original_value(original, name)
        detail.update(profile_ids=sorted({m['profile_id'] for m in memberships[str(row['key'])]}),
                      dataset=datasets[row['datasetKey']],
                      originalName=original_value(original, 'scientificName'),
                      originalDate=original_value(original, 'eventDate'))
        detail['photos'] = [{**m, 'localPath': media[m['identifier']].get('path')}
                            for m in row.get('media', []) if m.get('type') == 'StillImage']
        detail['geography'] = geography.get(str(row['key']))
        if detail['geography']:
            assert (detail['geography']['latitude'], detail['geography']['longitude']) == (
                row['decimalLatitude'], row['decimalLongitude']), 'Geography coordinates changed'
        compact.append(detail)
    source_path = Path('rainmapper_core/viewers/maplibre-viewer/app.js')
    source = source_path.read_text()
    styles = source.split('const baseStyles = ', 1)[1].split('\nlet currentStyle', 1)[0].strip()
    assert styles.startswith('[') and styles.endswith(';')
    terrain_tiles = source.split('const TERRAIN_TILES = ', 1)[1].split(';', 1)[0]
    (assets / 'base-styles.js').write_text('const GBIF_BASE_STYLES = ' + styles + '\nconst GBIF_TERRAIN_TILES = ' + terrain_tiles + ';\n')
    payload = {'snapshot_sha256': hashlib.sha256((root / 'occurrences.json').read_bytes()).hexdigest(),
               'records': compact,
               'profiles': [{k: s[k] for k in ('species_id', 'scientific_name', 'common_names')} for s in profiles]}
    (assets / 'data.js').write_text('const GBIF_DATA = ' + js_json(payload) + ';\n')
    for src, dest in ((args.maplibre_js, 'maplibre-gl.js'), (args.maplibre_css, 'maplibre-gl.css')):
        (assets / dest).write_bytes(src.read_bytes())
    here = Path(__file__).parent
    for name in ('gbif-viewer.js', 'gbif-viewer.css', 'gbif-review-file.js'):
        (assets / name).write_bytes((here / name).read_bytes())
    # Preserve the initial full photo gallery and its validated data for comparison.
    if not (root / 'gallery.html').exists():
        (root / 'gallery.html').write_bytes((root / 'index.html').read_bytes())
    (root / 'index.html').write_bytes((here / 'gbif-viewer.html').read_bytes())
    provenance = {'base_styles_source': str(source_path),
                  'base_styles_source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  'maplibre_version': '4.7.1', 'records': len(compact), 'profiles': len(profiles),
                  'basemaps_require_network': True, 'photos_are_local': True,
                  'local_geography_records': len(geography),
                  'local_geography_sha256': hashlib.sha256(geography_path.read_bytes()).hexdigest() if geography else None,
                  'note': 'Same four base styles as the shared prediction viewer; not prediction/model layers.'}
    (assets / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(provenance, ensure_ascii=False))


if __name__ == '__main__':
    main()
