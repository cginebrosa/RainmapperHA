"""Recompute coverage of the expanded station sample offline, without network."""
import collections
import datetime as dt
import gzip
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent
report = json.loads(gzip.decompress((ROOT / 'expanded-stations.json.gz').read_bytes()))
original = json.loads(gzip.decompress((ROOT / 'evidence.json.gz').read_bytes()))
reused = {p['station']: p for p in original['icgc']['points']}
dates = [(dt.date(2026, 7, 21) + dt.timedelta(days=i)).isoformat() for i in range(60)]
summary = []
def valid(v, channel):
    if v is None or isinstance(v, bool):
        return False
    try:
        v = float(v)
    except (ValueError, TypeError):
        return False
    return math.isfinite(v) and (v >= 0 if channel == 'Pluja_Tot' else 0 <= v <= 1)

for p in report['points']:
    rows = reused[p['station']]['rows'] if 'evidence_reference' in p else p['rows']
    days = collections.defaultdict(list)
    seen = set()
    duplicates = 0
    for row in rows:
        timestamp = row['TmStamp']
        if timestamp in seen:
            duplicates += 1
            continue
        seen.add(timestamp)
        days[timestamp[:10]].append(row)
    tested = [c for c in p['channels'] if c.startswith('VWC_') or c == 'Pluja_Tot']
    coverage = {}
    ranges = {}
    for c in tested:
        coverage[c] = sum(sum(valid(r.get(c), c) for r in days[d]) >= 44 for d in dates)
        vals = [float(r[c]) for d in dates for r in days[d] if valid(r.get(c), c)]
        ranges[c] = [min(vals), max(vals)] if vals else None
    paired = sum(all(sum(valid(r.get(c), c) for r in days[d]) >= 44
                     for c in ('VWC_005', 'VWC_020', 'Pluja_Tot')) for d in dates)
    summary.append({'name': p['name'], 'station': p['station'], 'days_with_44_valid_records': coverage,
                    'paired_days_5_20_rain': paired, 'duplicate_timestamps': duplicates,
                    'raw_ranges': ranges,
                    'coverage_candidate': paired >= 54 and duplicates == 0})
(ROOT / 'expanded-stations-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
print('Verified',len(summary),'stations;',sum(p['coverage_candidate'] for p in summary),'coverage candidates')
