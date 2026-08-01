#!/usr/bin/env python3
"""
Paso 7 del proceso de importación masiva de observaciones.

Para cada foto con micro_area_id asignado, busca la observación Rainmapper más
cercana geográficamente dentro de esa misma micro-área y copia sus campos
site_context como evidencia de campo sugerida.

Campos que añade/actualiza en review_table.json:
    observed_host_ids, observed_forest_type_ids, observed_soil_tendency_ids,
    observed_habitat_feature_ids, observed_aspect_ids  (nombres reales del schema)
    evidence_source_obs_id, evidence_source_dist_m, evidence_status

evidence_status values:
    "suggested"        — evidencia copiada de obs más cercana, pendiente de revisión
    "no_area"          — micro_area_id es null o "pending"
    "no_obs_in_area"   — micro-área sin observaciones de referencia

Uso:
    .venv/bin/python scripts/observations-mass-import/02_assign_evidence.py \
        --review-table "/ruta/a/candidates/review_table.json" \
        --observations docker-data/mushroom-data/mushroom_observations.json

    # Dry-run (no escribe):
    .venv/bin/python scripts/observations-mass-import/02_assign_evidence.py \
        --review-table "/ruta/a/candidates/review_table.json" \
        --observations docker-data/mushroom-data/mushroom_observations.json \
        --dry-run
"""

import argparse
import json
import math


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2)
    return 2 * R * math.asin(math.sqrt(a))


EVIDENCE_FIELDS = [
    'observed_host_ids',
    'observed_forest_type_ids',
    'observed_soil_tendency_ids',
    'observed_habitat_feature_ids',
    'observed_aspect_ids',
]


def build_obs_index(observations):
    """Indexa observaciones por micro_area_id con sus coordenadas y site_context."""
    index = {}
    for o in observations:
        mid = o.get('micro_area_id')
        if not mid:
            continue
        loc = o.get('location') or {}
        lat = loc.get('lat') or o.get('lat')
        lon = loc.get('lon') or o.get('lon')
        if lat is None or lon is None:
            continue
        index.setdefault(mid, []).append({
            'obs_id': o.get('observation_id') or o.get('id'),
            'lat': lat,
            'lon': lon,
            'site_context': o.get('site_context') or {},
        })
    return index


def assign_evidence(table, obs_index):
    stats = {'suggested': 0, 'no_area': 0, 'no_obs_in_area': 0}

    for row in table:
        mid = row.get('micro_area_id')
        plat = row.get('lat')
        plon = row.get('lon')

        if not mid or mid == 'pending' or plat is None or plon is None:
            for f in EVIDENCE_FIELDS:
                row[f] = []
            row['evidence_source_obs_id'] = None
            row['evidence_source_dist_m'] = None
            row['evidence_status'] = 'no_area'
            stats['no_area'] += 1
            continue

        candidates = obs_index.get(mid, [])
        if not candidates:
            for f in EVIDENCE_FIELDS:
                row[f] = []
            row['evidence_source_obs_id'] = None
            row['evidence_source_dist_m'] = None
            row['evidence_status'] = 'no_obs_in_area'
            stats['no_obs_in_area'] += 1
            continue

        nearest = min(candidates, key=lambda c: haversine(plat, plon, c['lat'], c['lon']))
        dist = round(haversine(plat, plon, nearest['lat'], nearest['lon']))
        sc = nearest['site_context']

        for f in EVIDENCE_FIELDS:
            row[f] = sc.get(f) or []
        row['evidence_source_obs_id'] = nearest['obs_id']
        row['evidence_source_dist_m'] = dist
        row['evidence_status'] = 'suggested'
        stats['suggested'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description='Asigna evidencia de campo desde obs más cercana')
    parser.add_argument('--review-table', required=True, help='Ruta a review_table.json')
    parser.add_argument('--observations', required=True, help='Ruta a mushroom_observations.json')
    parser.add_argument('--dry-run', action='store_true', help='No escribir cambios')
    args = parser.parse_args()

    with open(args.review_table) as f:
        table = json.load(f)
    with open(args.observations) as f:
        obs_data = json.load(f)

    obs_index = build_obs_index(obs_data['observations'])
    stats = assign_evidence(table, obs_index)

    print(f"Sugeridas:          {stats['suggested']}")
    print(f"Sin área/pending:   {stats['no_area']}")
    print(f"Sin obs en micro-área: {stats['no_obs_in_area']}")

    dists = sorted(r['evidence_source_dist_m'] for r in table if r.get('evidence_source_dist_m'))
    if dists:
        print(f"\nDistancias a obs de referencia:")
        print(f"  mín:     {dists[0]} m")
        print(f"  mediana: {dists[len(dists)//2]} m")
        print(f"  p90:     {dists[int(len(dists)*0.9)]} m")
        print(f"  máx:     {dists[-1]} m")

    far = [(r['fname'], r['micro_area_id'], r['evidence_source_dist_m'])
           for r in table if (r.get('evidence_source_dist_m') or 0) > 1000]
    if far:
        print(f"\nFotos con obs de referencia >1 km ({len(far)}):")
        for fname, mid, d in far:
            print(f"  {fname}  micro={mid}  dist={d} m")

    if not args.dry_run:
        with open(args.review_table, 'w') as f:
            json.dump(table, f, ensure_ascii=False, indent=2)
        print(f"\nEscrito: {args.review_table}")
    else:
        print("\nDry-run: no se ha escrito nada.")


if __name__ == '__main__':
    main()
