"""Download a separate, reproducible GBIF research snapshot; never import it."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://api.gbif.org/v1/'
CATALOG = 'docker-data/mushroom-data/mushroom_profiles.json'
GUARDED_PATHS = (
    'mushroom-data/mushroom_observations.json',
    'docker-data/mushroom-data/mushroom_observations.json',
    'docker-data/mushroom-data/mushroom_known_sites.json',
    CATALOG,
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    started = utc()
    before = {p: sha(Path(p).read_bytes()) for p in GUARDED_PATHS}
    dump(out / 'run-started.json', {'started_at': started, 'protected_sha256': before})
    request_log = []
    lock = threading.Lock()
    throttle = threading.Lock()
    next_request = [0.0]

    def fetch(url, relative):
        if not url.startswith('https://api.gbif.org/'):
            raise ValueError('Only GBIF API URLs are fetched')
        for attempt in range(3):
            with throttle:
                delay = max(0, next_request[0] - time.monotonic())
                if delay:
                    time.sleep(delay)
                next_request[0] = time.monotonic() + .25
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Rainmapper-GBIF-local-research/1.0',
                'Accept': 'application/json',
            })
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    body = response.read(10_000_001)
                if len(body) > 10_000_000:
                    raise ValueError('Unexpected JSON response over 10 MB')
                data = json.loads(body)
                path = out / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
                entry = {'url': url, 'path': relative, 'fetched_at': utc(),
                         'bytes': len(body), 'sha256': sha(body)}
                with lock:
                    request_log.append(entry)
                return data
            except urllib.error.HTTPError as error:
                if error.code not in (429, 502, 503, 504) or attempt == 2:
                    raise
                retry = error.headers.get('Retry-After', '')
                time.sleep(min(30, int(retry) if retry.isdigit() else 2 ** (attempt + 1)))

    def search(params, relative):
        return fetch(BASE + 'occurrence/search?' + urllib.parse.urlencode(params), relative)

    region = fetch(BASE + 'geocode/gadm/ESP.6_1', 'metadata/gadm.json')
    assert region['id'] == 'ESP.6_1' and region['name'] == 'Cataluña'
    catalog_bytes = Path(CATALOG).read_bytes()
    (out / 'metadata/catalog.json').write_bytes(catalog_bytes)
    profiles = json.loads(catalog_bytes)['species_profiles']
    queries = {}
    for profile in profiles:
        name = profile['scientific_name']
        names = [name]
        note = None
        if profile['species_id'] == 'lactarius_salmonicolor_quieticolor_group':
            names = ['Lactarius salmonicolor', 'Lactarius quieticolor']
            note = 'Operational group queried as two separate named taxa.'
        elif profile['species_id'] == 'morchella_elata_complex':
            names = ['Morchella elata']
            note = 'Named taxon only; not exhaustive coverage of the operational species complex.'
        elif profile['species_id'] == 'cantharellus_cibarius_sl':
            note = 'Named taxon only; no inferred expansion of sensu lato membership.'
        for query_name in names:
            queries.setdefault(query_name, []).append({'profile_id': profile['species_id'],
                                                       'catalog_name': name, 'note': note})
    records, taxonomies, counts, memberships = [], [], [], {}
    accepted_queries = {}
    for name, mappings in queries.items():
        slug = name.lower().replace(' ', '_')
        match = fetch('https://api.gbif.org/v2/species/match?' +
                      urllib.parse.urlencode({'scientificName': name}),
                      f'metadata/taxonomy-{slug}.json')
        usage = match['usage']
        assert usage['canonicalName'] == name and usage['rank'] == 'SPECIES'
        assert match['diagnostics']['matchType'] == 'EXACT'
        accepted = match.get('acceptedUsage', usage)
        assert accepted['rank'] == 'SPECIES'
        taxonomies.append({'query_name': name, 'usage': usage, 'accepted_usage': accepted,
                           'profiles': mappings})
        accepted_queries.setdefault(accepted['key'], {'name': accepted['canonicalName'],
                                                     'profiles': []})['profiles'].extend(mappings)
    dump(out / 'metadata/taxonomy-map.json', taxonomies)
    for taxon_key, query in accepted_queries.items():
        name = query['name']
        slug = name.lower().replace(' ', '_')
        params = {'taxonKey': taxon_key, 'gadmGid': 'ESP.6_1',
                  'eventDate': '2012-06-19,2026-09-16', 'limit': 0}
        count = search(params, f'counts/{slug}-before.json')['count']
        if count > 50000 or len(records) + count > 50000:
            raise ValueError('Unexpected count beyond this bounded research snapshot')
        selected = []
        offset = 0
        while offset < count:
            page = search({**params, 'limit': 300, 'offset': offset},
                          f'raw/search/{slug}-{offset:06d}.json')
            assert page['count'] == count, 'GBIF count changed during pagination'
            assert page['offset'] == offset and page['results']
            selected.extend(page['results'])
            offset += len(page['results'])
        assert len(selected) == count and len({r['key'] for r in selected}) == count
        records.extend(selected)
        for row in selected:
            memberships.setdefault(str(row['key']), []).extend(query['profiles'])
        counts.append({'name': name, 'taxon_key': taxon_key, 'count': count,
                       'profiles': query['profiles'],
                       'params': params})
        print(f'{name}: {len(selected)} full interpreted records saved', flush=True)

    # An accepted taxon shared by several operational profiles is fetched only once.
    records = list({r['key']: r for r in records}.values())
    dump(out / 'metadata/profile-memberships.json', memberships)
    dump(out / 'occurrences.json', records)
    datasets = {}
    for key in sorted({r['datasetKey'] for r in records}):
        datasets[key] = fetch(BASE + 'dataset/' + key, f'metadata/datasets/{key}.json')
    print(f'{len(records)} records; {len(datasets)} complete dataset metadata documents. '
          'Downloading original verbatim fields...', flush=True)

    def verbatim(row):
        key = row['key']
        result = fetch(BASE + f'occurrence/{key}/verbatim', f'raw/verbatim/{key}.json')
        assert result['key'] == key
        return key

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(verbatim, row) for row in records]
        done = 0
        for future in concurrent.futures.as_completed(futures):
            future.result()
            done += 1
            if done % 50 == 0 or done == len(records):
                print(f'Original verbatim records: {done}/{len(records)}', flush=True)

    for count in counts:
        slug = count['name'].lower().replace(' ', '_')
        final_count = search(count['params'], f'counts/{slug}-after.json')['count']
        assert final_count == count['count'], 'GBIF count changed during download'

    def precision(row):
        value = row.get('coordinateUncertaintyInMeters')
        if value is None:
            return 'unknown'
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            return 'invalid'
        return 'le_1000m' if value <= 1000 else 'gt_1000m'

    columns = ['gbifID', 'species', 'eventDate', 'latitude', 'longitude',
               'coordinateUncertaintyInMeters', 'precision_group', 'dataset',
               'basisOfRecord', 'occurrenceStatus', 'individualCount', 'organismQuantity',
               'organismQuantityType', 'samplingProtocol', 'samplingEffort',
               'recordedBy', 'occurrenceRemarks', 'informationWithheld',
               'dataGeneralizations', 'license', 'occurrenceID', 'gbif_url', 'verbatim_file']
    review = []
    for row in records:
        item = {k: row.get(k) for k in columns}
        item.update(gbifID=row['key'], species=row.get('species', row.get('scientificName')),
                    latitude=row.get('decimalLatitude'), longitude=row.get('decimalLongitude'),
                    precision_group=precision(row), dataset=datasets[row['datasetKey']]['title'],
                    gbif_url=f"https://www.gbif.org/occurrence/{row['key']}",
                    verbatim_file=f"raw/verbatim/{row['key']}.json")
        review.append(item)
    dump(out / 'review.json', review)
    # The CSV is only a convenience view; complete API data remain unchanged above.
    with (out / 'review.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in review:
            safe = {}
            for key, value in row.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')):
                    value = "'" + value
                safe[key] = value
            writer.writerow(safe)

    summary = {'total': len(records), 'species': counts,
               'precision': dict(Counter(precision(r) for r in records)),
               'datasets': dict(Counter(datasets[r['datasetKey']]['title'] for r in records)),
               'with_individual_count': sum(r.get('individualCount') is not None for r in records),
               'with_organism_quantity': sum(r.get('organismQuantity') is not None for r in records),
               'with_sampling_effort': sum(r.get('samplingEffort') is not None for r in records),
               'with_information_withheld': sum(bool(r.get('informationWithheld')) for r in records)}
    dump(out / 'summary.json', summary)
    after = {p: sha(Path(p).read_bytes()) for p in GUARDED_PATHS}
    assert before == after, 'Operational local data changed during the snapshot'
    files = {str(p.relative_to(out)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
             for p in sorted(out.rglob('*')) if p.is_file()
             and 'media' not in p.relative_to(out).parts and p.name != 'index.html'}
    manifest = {'status': 'complete', 'started_at': started, 'completed_at': utc(),
                'scope': {'species': list(queries), 'catalog_path': CATALOG,
                          'catalog_profiles': len(profiles), 'gadmGid': 'ESP.6_1',
                          'eventDate': '2012-06-19,2026-09-16',
                          'uncertainty_filter': None, 'license_filter': None,
                          'dataset_filter': None},
                'record_count': len(records), 'verbatim_count': len(records),
                'dataset_metadata_count': len(datasets), 'requests': sorted(request_log, key=lambda r: r['path']),
                'files': files, 'protected_sha256_before': before, 'protected_sha256_after': after,
                'limitations': ['GBIF live API, not a transactional DOI download; counts checked before/after.',
                                'Interpreted records and verbatim records captured at their respective request times.',
                                'Photo binaries are handled separately by download_gbif_media.py.',
                                'Operational complexes queried through explicit named taxa; see taxonomy-map.json.',
                                'No records imported, labels assigned, training or precompute performed.']}
    dump(out / 'manifest.json', manifest)
    print(json.dumps({'status': 'complete', 'directory': str(out), 'summary': summary,
                      'total_bytes': sum(x['bytes'] for x in files.values())}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
