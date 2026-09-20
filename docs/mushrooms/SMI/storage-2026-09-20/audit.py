"""SMI-06: conditional storage-change diagnostics; offline, stdlib only."""
import collections
import csv
from datetime import datetime, date
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics as stats
import unicodedata

ROOT = Path(__file__).resolve().parent
SMI = ROOT.parent
MODELS = tuple(f'regulated_{et}_{layers}' for et in ('hg', 'pm') for layers in ('one', 'two'))
PROFILES = {
    'linear_5_20_50': {'VWC_005': 125., 'VWC_020': 475/3, 'VWC_050': 50/3},
    'hold_20': {'VWC_005': 125., 'VWC_020': 175.},
    'blocks_10_20': {'VWC_005': 100., 'VWC_020': 200.},
}


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def num(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def normal(name):
    return ''.join(c for c in unicodedata.normalize('NFD', name.lower()) if c.isalnum())


def sensor(value):
    n = num(value)
    return n if n is not None and 0 < n <= 1 else None


def integrate(values, profile):
    weights = PROFILES[profile]
    assert abs(sum(weights.values()) - 300) < 1e-10
    if any(values.get(ch) is None for ch in weights):
        return None
    return sum(values[ch] * weight for ch, weight in weights.items())


def daily(rows, days):
    by_day = collections.defaultdict(dict)
    seen = set()
    for row in rows:
        instant = datetime.fromisoformat(row['TmStamp'])
        if instant in seen:
            raise ValueError('duplicate timestamp')
        seen.add(instant)
        by_day[instant.date().isoformat()][instant.strftime('%H:%M:%S')] = row
    expected = {f'{h:02}:{m:02}:00' for h in range(24) for m in (0, 30)}
    channels = sorted({ch for row in rows for ch in row if ch.startswith('VWC_')})
    out = []
    for day in days:
        slots = by_day[day]
        item = {'date': day, 'mean': {}, 'end': {}, 'count': {}}
        for ch in channels:
            values = [v for row in slots.values() if (v := sensor(row.get(ch))) is not None]
            item['count'][ch] = len(values)
            item['mean'][ch] = stats.mean(values) if len(values) >= 44 else None
            item['end'][ch] = sensor(slots.get('23:30:00', {}).get(ch)) if len(values) >= 44 else None
        rain = [num(row.get('Pluja_Tot')) for row in slots.values()]
        item['gauge'] = sum(rain) if set(slots) == expected and all(v is not None and v >= 0 for v in rain) else None
        out.append(item)
    return out, channels


def episodes(rain):
    groups = []
    for i, p in enumerate(rain):
        if p is not None and p >= 1:
            if groups and i - groups[-1][-1] <= 2 and all(v is not None for v in rain[groups[-1][-1]:i+1]):
                groups[-1].append(i)
            else:
                groups.append([i])
    accepted, rejected = [], []
    for group in groups:
        start, end = group[0], group[-1]
        reason = None
        if start < 2 or end + 3 >= len(rain):
            reason = 'window_outside_period'
        elif any(v is None for v in rain[start-2:end+4]):
            reason = 'rain_gap'
        elif any(v >= 1 for v in rain[start-2:start] + rain[end+1:end+4]):
            reason = 'adjacent_episode'
        (rejected if reason else accepted).append((start, end, reason))
    return accepted, rejected


def interval_delta(values, a, b):
    if not 0 <= a < b < len(values) or any(v is None for v in values[a:b+1]):
        return None
    return values[b] - values[a]


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'wt', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    base, first, factorial = (SMI / p for p in ('baseline-2026-09-19', 'contrast-2026-09-19', 'factorial-2026-09-20'))
    prior = json.loads((factorial/'summary.json').read_text())
    for filename, digest in prior['sha256'].items():
        assert sha(SMI/filename) == digest, filename
    local = read(base/'local-inputs.json.gz')
    original = {p['station']: p for p in read(first/'evidence.json.gz')['icgc']['points']}
    expanded = read(first/'expanded-stations.json.gz')
    raw = {normal(p['name']): p.get('rows', original.get(p['station'], {}).get('rows')) for p in expanded['points']}
    metadata = {p['code']: p for p in json.loads((base/'station-metadata.json').read_text())}
    with gzip.open(factorial/'series.csv.gz', 'rt') as f:
        predictions = {(r['code'], r['date']): r for r in csv.DictReader(f)}
    results, inventory, series, rejected, episode_catalog = [], [], [], [], []
    for point in local['points']:
        code, name, capacity = point['code'], point['name'], point['capacity_mm']
        days = point['inputs']['interpolated']['daily_dates'][-60:]
        assert len(set(days)) == 60
        assert all((date.fromisoformat(b)-date.fromisoformat(a)).days == 1 for a, b in zip(days, days[1:]))
        observations, channels = daily(raw[normal(name)], days)
        rain = point['inputs']['interpolated']['daily_rain_idw_mm'][-60:]
        model = {m: [num(predictions[(code, d)][m+'_total']) for d in days] for m in MODELS}
        for m in MODELS:
            model[m] = [None if v is None else v*capacity/100 for v in model[m]]
        refs = {(profile, timing): [integrate(day[timing], profile) for day in observations]
                for profile in PROFILES for timing in ('end', 'mean')}
        inv = dict(code=code, name=name, capacity_model_mm=capacity, channels=';'.join(channels),
                   absolute_available_water_validated=False,
                   absolute_blocker='volumetric_FC_WP_full_profile_and_probe_calibration_not_confirmed',
                   station_sheet=metadata[code]['source'], sheet_extraction=metadata[code]['extraction'])
        for (profile, timing), values in refs.items():
            inv[profile+'_'+timing+'_days'] = sum(v is not None for v in values)
        for ch in channels:
            inv[ch+'_end_days'] = sum(d['end'].get(ch) is not None for d in observations)
        inventory.append(inv)
        for i, d in enumerate(days):
            series.append(dict(code=code, date=d, rain_idw_mm=rain[i], rain_gauge_mm=observations[i]['gauge'],
                **{m+'_available_mm': v[i] for m, v in model.items()},
                **{p+'_'+t+'_total_mm': v[i] for (p, t), v in refs.items()}))
        good, bad = episodes(rain)
        rejected.extend(dict(code=code, kind='episode_selection', start=days[a], end=days[b], reason=why) for a, b, why in bad)
        windows = [('daily', i-1, i, None, None) for i in range(1, len(days))]
        for start, end, _ in good:
            gauge = [x['gauge'] for x in observations[start:end+1]]
            episode_catalog.append(dict(code=code, start=days[start], end=days[end],
                rain_idw_mm=sum(rain[start:end+1]),
                rain_gauge_mm=sum(gauge) if all(x is not None for x in gauge) else None))
            windows.extend([('recharge_next', start-1, end+1, start, end), ('recharge_day3', start-1, end+3, start, end)])
            if end+8 < len(days) and all(v is not None and v < 1 for v in rain[end+1:end+9]) and sum(rain[end+4:end+9]) <= 1:
                windows.append(('drying5', end+3, end+8, start, end))
            else:
                rejected.append(dict(code=code, kind='drying5', start=days[start], end=days[end], reason='no_complete_five_day_dry_window'))
        for kind, a, b, start, end in windows:
            deltas = {m: interval_delta(v, a, b) for m, v in model.items()}
            gauge = [x['gauge'] for x in observations[a+1:b+1]]
            gauge_total = sum(gauge) if all(x is not None for x in gauge) else None
            for (profile, timing), values in refs.items():
                observed = interval_delta(values, a, b)
                if observed is None or any(v is None for v in deltas.values()):
                    rejected.append(dict(code=code, kind=kind, profile=profile, timing=timing,
                        start=days[a], end=days[b], reason='profile_gap' if observed is None else 'model_gap'))
                    continue
                sign = -1 if kind == 'drying5' else 1
                for m, predicted in deltas.items():
                    results.append(dict(code=code, name=name, kind=kind, profile=profile, timing=timing,
                        start=days[a], end=days[b], duration_days=b-a, model=m,
                        observed_change_mm=sign*observed, predicted_change_mm=sign*predicted,
                        residual_mm=sign*(predicted-observed), absolute_residual_mm=abs(predicted-observed),
                        observed_per_day_mm=sign*observed/(b-a), predicted_per_day_mm=sign*predicted/(b-a),
                        rain_idw_mm=sum(rain[a+1:b+1]), rain_gauge_mm=gauge_total,
                        gauge_confirms_dry=gauge_total is not None and gauge_total <= 1 if kind == 'drying5' else None))
    # All candidates must use the same cases, with no independently selected coverage.
    cases = collections.defaultdict(set)
    for row in results:
        cases[tuple(row[k] for k in ('code', 'kind', 'profile', 'timing', 'start', 'end'))].add(row['model'])
    assert all(v == set(MODELS) for v in cases.values())
    # Sensitivity comparisons restricted to identical dates, profiles and timings.
    available = collections.defaultdict(set)
    for code, kind, profile, timing, start, end in cases:
        available[(code, kind, start, end)].add((profile, timing))
    paired = {k for k, v in available.items() if len(v) == len(PROFILES)*2}
    metrics = []
    for scope in ('all_valid', 'paired_sensitivities', 'gauge_dry'):
        groups = collections.defaultdict(list)
        for row in results:
            case = tuple(row[k] for k in ('code', 'kind', 'start', 'end'))
            if scope == 'paired_sensitivities' and case not in paired:
                continue
            if scope == 'gauge_dry' and (row['kind'] != 'drying5' or not row['gauge_confirms_dry']):
                continue
            groups[tuple(row[k] for k in ('code', 'name', 'kind', 'profile', 'timing', 'model'))].append(row)
        for (code, name, kind, profile, timing, m), rows in groups.items():
            metrics.append(dict(scope=scope, code=code, name=name, kind=kind, profile=profile, timing=timing, model=m,
                n=len(rows), mae_mm=stats.mean(r['absolute_residual_mm'] for r in rows),
                bias_mm=stats.mean(r['residual_mm'] for r in rows),
                observed_change_mm=stats.mean(r['observed_change_mm'] for r in rows),
                predicted_change_mm=stats.mean(r['predicted_change_mm'] for r in rows),
                observed_per_day_mm=stats.mean(r['observed_per_day_mm'] for r in rows),
                predicted_per_day_mm=stats.mean(r['predicted_per_day_mm'] for r in rows)))
    groups = collections.defaultdict(list)
    for row in metrics:
        groups[tuple(row[k] for k in ('scope', 'kind', 'profile', 'timing', 'model'))].append(row)
    aggregates = []
    for (scope, kind, profile, timing, m), rows in groups.items():
        aggregates.append(dict(scope=scope, kind=kind, profile=profile, timing=timing, model=m,
            stations=len(rows), cases=sum(r['n'] for r in rows), codes=[r['code'] for r in rows],
            **{key: stats.median(r[key] for r in rows) for key in ('mae_mm', 'bias_mm', 'observed_change_mm',
               'predicted_change_mm', 'observed_per_day_mm', 'predicted_per_day_mm')}))
    write_csv(ROOT/'inventory.csv', inventory)
    write_csv(ROOT/'series.csv.gz', series)
    write_csv(ROOT/'changes.csv.gz', results)
    write_csv(ROOT/'station-metrics.csv', metrics)
    write_csv(ROOT/'excluded.csv.gz', rejected)
    write_csv(ROOT/'episodes.csv', episode_catalog)
    paths = [ROOT/'audit.py', ROOT/'PROTOCOL.md', ROOT/'test_audit.py', base/'station-metadata.json',
             base/'local-inputs.json.gz', first/'expanded-stations.json.gz', first/'evidence.json.gz',
             factorial/'series.csv.gz', factorial/'summary.json']
    summary = dict(stations=len(inventory), validated_absolute_available_stations=0,
        station_days=len(series), result_rows=len(results), cases=len(cases), idw_episodes=len(episode_catalog),
        excluded_reasons=dict(collections.Counter(r['reason'] for r in rejected)),
        aggregates=aggregates, sha256={str(p.relative_to(SMI)): sha(p) for p in paths})
    (ROOT/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('aggregates', 'sha256')}, ensure_ascii=False))
    for row in aggregates:
        if row['scope'] == 'all_valid' and row['profile'] == 'linear_5_20_50' and row['timing'] == 'end':
            print(json.dumps(row, ensure_ascii=False))


if __name__ == '__main__':
    main()
