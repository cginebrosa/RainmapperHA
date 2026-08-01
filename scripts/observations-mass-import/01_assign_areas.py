#!/usr/bin/env python3
"""
Paso 6 del proceso de importación masiva de observaciones.

Asigna area_id y micro_area_id a cada fila de review_table.json usando
point-in-polygon (ray-casting) contra los polígonos de mushroom_known_sites.json.

Uso:
    .venv/bin/python scripts/observations-mass-import/01_assign_areas.py \
        --review-table "/ruta/a/candidates/review_table.json" \
        --known-sites docker-data/mushroom-data/mushroom_known_sites.json

    # Dry-run (no escribe):
    .venv/bin/python scripts/observations-mass-import/01_assign_areas.py \
        --review-table "/ruta/a/candidates/review_table.json" \
        --known-sites docker-data/mushroom-data/mushroom_known_sites.json \
        --dry-run
"""

import argparse
import json
import math


def point_in_polygon(lat, lon, polygon_coords):
    """Ray-casting algorithm. polygon_coords: lista de [lon, lat] (formato GeoJSON)."""
    x, y = lon, lat
    inside = False
    n = len(polygon_coords)
    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos puntos WGS84."""
    R = 6371000
    p = math.pi / 180
    a = (0.5 - math.cos((lat2 - lat1) * p) / 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2)
    return 2 * R * math.asin(math.sqrt(a))


def centroid(polygon_coords):
    """Centroide simple de un polígono GeoJSON ([lon, lat] por punto)."""
    lons = [c[0] for c in polygon_coords]
    lats = [c[1] for c in polygon_coords]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def assign_areas(table, areas, micro_areas, pending_threshold_m=3000):
    stats = {'assigned': 0, 'pending': 0, 'no_area': 0}

    micro_by_area = {}
    for m in micro_areas:
        micro_by_area.setdefault(m['area_id'], []).append(m)

    for row in table:
        lat = row.get('lat')
        lon = row.get('lon')
        if lat is None or lon is None:
            row['area_id'] = None
            row['micro_area_id'] = None
            stats['no_area'] += 1
            continue

        matched_area = None
        for area in areas:
            coords = area['geometry']['coordinates'][0]
            if point_in_polygon(lat, lon, coords):
                matched_area = area
                break

        if not matched_area:
            row['area_id'] = None
            row['micro_area_id'] = None
            stats['no_area'] += 1
            continue

        row['area_id'] = matched_area['area_id']

        # Buscar micro-área dentro del área
        matched_micro = None
        for m in micro_by_area.get(matched_area['area_id'], []):
            coords = m['geometry']['coordinates'][0]
            if point_in_polygon(lat, lon, coords):
                matched_micro = m
                break

        if matched_micro:
            row['micro_area_id'] = matched_micro['micro_area_id']
            stats['assigned'] += 1
            continue

        # No está dentro de ninguna micro-área: buscar la más cercana por centroide
        candidates = micro_by_area.get(matched_area['area_id'], [])
        if not candidates:
            row['micro_area_id'] = 'pending'
            stats['pending'] += 1
            continue

        nearest = None
        nearest_dist = float('inf')
        for m in candidates:
            coords = m['geometry']['coordinates'][0]
            clat, clon = centroid(coords)
            d = haversine(lat, lon, clat, clon)
            if d < nearest_dist:
                nearest_dist = d
                nearest = m

        if nearest_dist <= pending_threshold_m:
            row['micro_area_id'] = nearest['micro_area_id']
            stats['assigned'] += 1
        else:
            row['micro_area_id'] = 'pending'
            stats['pending'] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description='Asigna area_id y micro_area_id a review_table.json')
    parser.add_argument('--review-table', required=True, help='Ruta a review_table.json')
    parser.add_argument('--known-sites', required=True, help='Ruta a mushroom_known_sites.json')
    parser.add_argument('--pending-threshold-m', type=int, default=3000,
                        help='Distancia máxima (m) para asignar micro-área más cercana (default: 3000)')
    parser.add_argument('--dry-run', action='store_true', help='No escribir cambios')
    args = parser.parse_args()

    with open(args.review_table) as f:
        table = json.load(f)
    with open(args.known_sites) as f:
        sites = json.load(f)

    areas = sites['areas']
    micro_areas = sites['micro_areas']

    stats = assign_areas(table, areas, micro_areas, args.pending_threshold_m)

    print(f"Asignadas:          {stats['assigned']}")
    print(f"Pendiente (>thresh): {stats['pending']}")
    print(f"Sin área:           {stats['no_area']}")

    if not args.dry_run:
        with open(args.review_table, 'w') as f:
            json.dump(table, f, ensure_ascii=False, indent=2)
        print(f"\nEscrito: {args.review_table}")
    else:
        print("\nDry-run: no se ha escrito nada.")


if __name__ == '__main__':
    main()
