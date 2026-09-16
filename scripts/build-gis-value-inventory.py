#!/usr/bin/env python3
"""Extract attribute inventories locally; never infer or accept classifications.

Run when publishing a new GIS edition, not on HA startup or map requests.
Requires ogrinfo. Reads attributes only and packages no geometries.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess


def build(geology, mvc50, ogrinfo):
    with sqlite3.connect(f"file:{geology.resolve()}?mode=ro", uri=True) as db:
        units = db.execute('SELECT DISTINCT Codi, Descripcio FROM "_04_unitats_geologiques_50000" ORDER BY Codi').fetchall()
    if len({code for code, _ in units}) != len(units):
        raise ValueError('Conflicting descriptions for the same geological code')
    sources = [{
        'source_id': 'geology_50000',
        'edition': '2024-12', 'field': 'Codi', 'source_file': geology.name,
        'values': [{'raw_value': code, 'description': description} for code, description in units],
    }]
    for field in ('LLFISCAT_t', 'LLVA_niv2t', 'LLVA_Subst'):
        query = f'SELECT DISTINCT "{field}" FROM "{mvc50.stem}" WHERE "{field}" IS NOT NULL ORDER BY "{field}" LIMIT 4097'
        result = subprocess.run([ogrinfo, '-ro', '-json', '-features', '-al', '-geom=NO', '-dialect', 'SQLITE', '-sql', query, str(mvc50)], check=True, capture_output=True, text=True)
        values = json.loads(result.stdout)['layers'][0]['features']
        sources.append({'source_id': 'mvc50', 'edition': '2019-11', 'field': field,
                        'source_file': mvc50.name,
                        'values': [{'raw_value': feature['properties'][field]} for feature in values if feature['properties'][field].strip()]})
    return {'schema_version': 1, 'purpose': 'Source values only; presence is not scientific acceptance.', 'sources': sources}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geology', type=Path, required=True)
    parser.add_argument('--mvc50', type=Path, required=True)
    parser.add_argument('--ogrinfo', default='ogrinfo')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.geology, args.mvc50, args.ogrinfo)
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n'
    if len(raw.encode()) > 1024 * 1024 or sum(len(s['values']) for s in payload['sources']) > 4096:
        raise ValueError('Inventory exceeds publication budget')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(raw)
    print(json.dumps({'bytes': len(raw.encode()), 'counts': {s['source_id'] + '/' + s['field']: len(s['values']) for s in payload['sources']}}))
