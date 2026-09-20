"""Read local DEM and municipal polygons once for a separate GBIF research snapshot.

Run with the local GDAL-enabled Python; never downloads or changes operational data.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from rainmapper_core.mushroom_map_municipalities import MunicipalityReader
from rainmapper_core.mushroom_map_terrain import TerrainReader


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    root = args.snapshot
    index = Path('mushroom-map-GIS/terrain-index/point-inputs-2026-09-12.sqlite')
    municipalities = Path('mushroom-map-GIS/ign-municipios/prepared/municipalities-2026-08-10.gpkg')
    roots = {'regional': 'mushroom-GIS', 'dem': 'mushroom-map-GIS/ign-mdt25',
             'soil': 'mushroom-map-GIS/soilgrids-shared'}
    manifest = json.loads((root / 'manifest.json').read_text())
    guarded = [*manifest['protected_sha256_before'], str(root / 'occurrences.json')]
    before = {p: sha(p) for p in guarded}
    records = json.loads((root / 'occurrences.json').read_text())
    cache, result, used_assets = {}, {}, {}
    terrain = TerrainReader(str(index), roots)
    municipal = MunicipalityReader(str(municipalities), edition='2026-08-10')
    try:
        for row in records:
            lat, lon = row['decimalLatitude'], row['decimalLongitude']
            key = (lat, lon)
            if key not in cache:
                terrain._validate_point(lat, lon)
                # Use only the existing elevation reader, not lookup(), which also reads soil pH.
                elevation = terrain._elevation(lat, lon)
                cache[key] = {'latitude': lat, 'longitude': lon, 'elevation': elevation,
                              'municipality': municipal.lookup(lat, lon)}
                for asset_id in terrain._datasets:
                    asset = dict(terrain._db.execute('SELECT * FROM assets WHERE id=?', (asset_id,)).fetchone())
                    used_assets[str(asset_id)] = {k: asset[k] for k in ('root_key','path','source','bytes','mtime_ns')}
            result[str(row['key'])] = cache[key]
            if len(result) % 250 == 0:
                print(f'Geografía local: {len(result)}/{len(records)} observaciones', flush=True)
    finally:
        terrain.close()
        municipal.close()
    assert before == {p: sha(p) for p in guarded}, 'Input or operational data changed'
    summary = {'records': len(result), 'unique_coordinates': len(cache),
               'elevation_status': dict(Counter(v['elevation']['status'] for v in result.values())),
               'elevation_sources': dict(Counter(v['elevation'].get('source_id') for v in result.values())),
               'municipality_status': dict(Counter(v['municipality']['status'] for v in result.values()))}
    output = {'generated_at': datetime.now(timezone.utc).isoformat(), 'summary': summary,
              'method': 'DEM pixel and containing municipal polygon at published coordinates; no uncertainty-area inference.',
              'terrain_index': {'path': str(index), 'sha256': sha(index)},
              'municipalities': {'path': str(municipalities), 'sha256': sha(municipalities), 'edition': '2026-08-10'},
              'dem_assets': used_assets, 'roots': roots, 'records': result,
              'input_and_operational_sha256': before}
    target = root / 'metadata/geography.json'
    if target.exists():
        raise FileExistsError('Geography is already captured; review it before regenerating')
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
