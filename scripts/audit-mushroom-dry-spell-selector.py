#!/usr/bin/env python3
"""Offline chronological A/B audit using the production trainers and selector.

Writes only new audit artifacts. Never loads operational fitted estimators or
invokes jobs, activation, network, weather reconstruction or container control.
"""
from __future__ import annotations

import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import argparse
import collections
import copy
from datetime import date, timedelta
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from threadpoolctl import threadpool_limits
from rainmapper_core import mushroom_ml_biology_v3_evaluation as v3eval
from rainmapper_core import mushroom_ml_biology_v3 as biology
from rainmapper_core import mushroom_ml_biology_v3_physical as physical
from rainmapper_core import mushroom_ml_biology_v4 as v4
from rainmapper_core import mushroom_ml_holdout as holdout
from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_multiversion_comparison as comparison
from rainmapper_core import mushroom_ml_quality_catalog as quality
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_runtime_inference as inference
from rainmapper_core import mushroom_ml_runtime_trainer as trainer
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core import mushroom_predictor_precompute as precompute
from rainmapper_core.mushroom_ml_predictor import MushroomMLPredictor

PREPARED = ROOT / 'docker-data/audits/mushroom-hydric-ablation-20260905/prepared'
REGISTRY = ROOT / 'docker-data/mushroom-data/mushroom_ml_version_registry.json'
MANIFEST = ROOT / 'docker-media/rainmapper/mushroom-derived/ml_models/batches/operational_20260909T184116Z/manifest.json'
PROFILES = ROOT / 'docker-data/mushroom-data/mushroom_profiles.json'
PROTECTED = [ROOT / 'mushroom-data/mushroom_observations.json',
             ROOT / 'docker-data/mushroom-data/mushroom_observations.json', REGISTRY,
             MANIFEST, ROOT / 'docker-media/rainmapper/predictor_precompute/active.sqlite3',
             ROOT / 'docker-media/rainmapper/predictor_precompute/active-receipt.json']
REMOVED = {'dry_spell_observed_at_cutoff', 'dry_spell_is_censored'}
AFFECTED = {'altitude_v2', 'biology_v3', 'biology_v4'}
FOLDS = {'recent': (2022, 2024, 2026), 'earlier': (2020, 2022, 2024)}
STATUS = {'within_observed_range': 0, 'caution': 1, 'outside_domain': 2}
STATUS_NAMES = {v: k for k, v in STATUS.items()}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path, value):
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
    if len(encoded.encode()) > 100_000_000:
        raise ValueError('Audit JSON exceeds 100 MB budget')
    with path.open('x') as f:
        f.write(encoded + '\n')


def meta(sample):
    m = sample.get('metadata') or {}
    return m.get('source_v3_metadata') or m


def compact(benchmark):
    """Retain predictive values and identity; omit duplicated weather diagnostics."""
    result = {k: v for k, v in benchmark.items() if k != 'samples'}
    rows = []
    for sample in benchmark['samples']:
        m = meta(sample)
        mm = {k: m[k] for k in ('observation_id', 'species_id', 'area_id', 'target_date',
              'cutoff_date', 'horizon_days', 'validation_group_14d', 'validation_group_7d')}
        rain = (m.get('weather_series') or {}).get('daily_area_rain_idw_mean_mm')
        if rain is not None:
            mm['event_ages'] = {
                'days_since_rain_gt_2_at_target': biology._last_event_age(rain[-90:], biology.RAIN_EVENT_THRESHOLD_MM),
                'days_since_significant_rain_at_target': biology._last_event_age(rain[-90:], biology.SIGNIFICANT_RAIN_THRESHOLD_MM),
            }
        rows.append({'sample_id': sample['sample_id'], 'prediction_target': sample['prediction_target'],
                     'predictive_features': sample['predictive_features'],
                     'quality': {'training_eligible': bool(sample.get('quality', {}).get('training_eligible'))},
                     'metadata': mm})
    result['samples'] = rows
    return result


def benchmarks(registry):
    installed = [v for v in registry['versions'] if v.get('installed_generation_id')]
    for temporal in ('fixed', 'lag'):
        base3 = json.loads((PREPARED / f'snapshot/biology-v3-{temporal}.json').read_text())
        base4 = json.loads((PREPARED / f'snapshot/biology-v4-{temporal}.json').read_text())
        for version in installed:
            vid = version['version_id']
            if vid not in AFFECTED:
                continue
            contract = next(c for c in version['temporal_contract_ids'] if c.startswith('fixed' if temporal == 'fixed' else 'lag'))
            for profile in version['runtime']['profiles']:
                pid = profile['profile_id']
                b = (v3eval.build_observation_altitude_v2_common_idw_benchmark(base3) if vid == 'altitude_v2'
                     else base3 if vid == 'biology_v3' and pid == 'core'
                     else physical.materialize_benchmark(base4) if vid == 'biology_v3'
                     else v4.materialize_comparison_benchmark(base4, profile_id=pid))
                small = compact(b)
                yield vid, contract, profile, small
                del small, b
        del base3, base4
        gc.collect()
        base5 = json.loads((PREPARED / f'v5-current/biology-v5-{temporal}.json').read_text())
        base5 = compact(base5)
        for version in installed:
            vid = version['version_id']
            if vid in AFFECTED:
                continue
            assert vid in (raw.WINDOWED_VERSION_ID, smooth.WINDOWED_VERSION_ID)
            contract = next(c for c in version['temporal_contract_ids'] if c.startswith('fixed' if temporal == 'fixed' else 'lag'))
            for profile in version['runtime']['profiles']:
                yield vid, contract, profile, base5
        del base5
        gc.collect()


def population():
    d = json.loads((PREPARED / 'snapshot/biology-v3-fixed.json').read_text())
    obs = {}
    for s in d['samples']:
        m = meta(s)
        oid = m['observation_id']
        assert oid not in obs
        obs[oid] = {k: m[k] for k in ('species_id', 'area_id', 'target_date', 'validation_group_14d')}
        obs[oid].update(y=1 if s['prediction_target'] == 'favorable' else 0,
                        target_known=s['prediction_target'] in ('favorable', 'unfavorable'))
    return obs


def split_population(obs, fold):
    train_year, evidence_year, test_year = FOLDS[fold]
    train_end = date(train_year+1, 1, 1) - timedelta(days=15)
    evidence_start = date(train_year+1, 1, 1)
    evidence_end = date(evidence_year+1, 1, 1) - timedelta(days=15)
    test_start = date(evidence_year+1, 1, 1)
    test_end = date(test_year, 12, 31)
    groups = collections.defaultdict(list)
    for oid, m in obs.items():
        groups[m['validation_group_14d']].append(oid)
    stages = {}
    excluded = {}
    for group, ids in groups.items():
        ds = [date.fromisoformat(obs[i]['target_date']) for i in ids]
        a, b = min(ds), max(ds)
        stage = ('train' if b <= train_end else 'evidence' if a >= evidence_start and b <= evidence_end
                 else 'test' if a >= test_start and b <= test_end else None)
        if stage:
            stages.update({i: stage for i in ids})
        else:
            excluded[group] = {'dates': [a.isoformat(), b.isoformat()], 'observations': ids}
    assert not ({i for i, s in stages.items() if s == 'train'} & {i for i, s in stages.items() if s != 'train'})
    return stages, excluded


def retarget(features, old_date, old_horizon, new_horizon, event_ages=None):
    """Same cutoff, exact calendar/horizon formulas; no new weather values."""
    f = dict(features)
    target = date.fromisoformat(old_date) + timedelta(days=new_horizon-old_horizon)
    if 'horizon_days' in f:
        f['horizon_days'] = float(new_horizon)
    angle = 2 * math.pi * (target.month-1) / 12
    for key, value in [('target_month_sin', round(math.sin(angle), 6)), ('target_month_cos', round(math.cos(angle), 6))]:
        if key in f: f[key] = value
    angle = 2.0 * math.pi * ((target.timetuple().tm_yday-1) / 365.2425)
    for key, value in [('target_day_sin', math.sin(angle)), ('target_day_cos', math.cos(angle))]:
        if key in f: f[key] = value
    for key in ('days_since_rain_gt_2_at_target', 'days_since_significant_rain_at_target'):
        if key in f:
            assert event_ages is not None and key in event_ages
            age = event_ages[key]
            f[key] = float(min(biology.EVENT_LOOKBACK_DAYS, age + new_horizon)) if age is not None else float(biology.EVENT_LOOKBACK_DAYS)
    return f


def ref_key(ref):
    return (ref['version_id'], ref['profile_id'], ref['temporal_contract_id'], ref['estimator_id'])


def ref_for(base, sp, h):
    return {**base, 'species_id': sp, 'horizon_days': h}


def freeze_rows(samples, columns):
    return [{**s, 'predictive_features': {k: s['predictive_features'].get(k) for k in columns}} for s in samples]


def fit_one(ref, b, train, columns, budget):
    if budget['fits'] >= 2600:
        raise RuntimeError('Preflight maximum final fits exceeded')
    budget['fits'] += 1
    prepared = trainer._prepare_fit_inputs(ref, {**b, 'samples': train})
    assert list(prepared['columns']) == columns
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        bundle = trainer.fit_artifact(ref, b, snapshot_id='isolated_dry_selector', prepared_inputs=prepared)
    model = bundle['model']
    if hasattr(model, 'named_steps'):
        classifier = model.named_steps.get('classifier')
        if hasattr(classifier, 'n_jobs'): classifier.n_jobs = 1
    return bundle, dict(collections.Counter(str(w.message) for w in caught))


def audit_fold(dest, fold, registry, species, obs, preflight):
    stages, excluded = split_population(obs, fold)
    tests = {i: m for i, m in obs.items() if stages.get(i) == 'test' and m['species_id'] in species and m['target_known']}
    caches = {'current': collections.defaultdict(dict), 'off': collections.defaultdict(dict)}
    budget = {'fits': 0}
    summaries = []
    output = dest / fold
    output.mkdir()
    logs = {arm: (output / f'{arm}-evidence.jsonl').open('x') for arm in caches}
    prediction_log = (output / 'model-predictions.jsonl').open('x')
    started = time.monotonic()
    for vid, contract, profile, source in benchmarks(registry):
        eligible = [s for s in holdout.eligible_samples(source) if meta(s)['species_id'] in species]
        for s in eligible:
            m = meta(s); oid = m['observation_id']
            assert oid in obs and obs[oid]['species_id'] == m['species_id']
            assert obs[oid]['target_date'] == m['target_date']
            assert obs[oid]['y'] == int(s['prediction_target'] == 'favorable')
            assert (date.fromisoformat(m['target_date'])-date.fromisoformat(m['cutoff_date'])).days == m['horizon_days']
        for estimator in profile['estimator_ids']:
            pooled = vid == smooth.WINDOWED_VERSION_ID and estimator != 'smooth_species_logistic_v1'
            for sp in (['all_species'] if pooled else species):
                rows = [s for s in eligible if pooled or meta(s)['species_id'] == sp]
                train = [s for s in rows if stages.get(meta(s)['observation_id']) == 'train']
                evidence = [s for s in rows if stages.get(meta(s)['observation_id']) == 'evidence']
                test = [s for s in rows if meta(s)['observation_id'] in tests]
                base = dict(batch_id='isolated_dry_selector', generation_id='isolated_dry_selector',
                            version_id=vid, temporal_contract_id=contract, profile_id=profile['profile_id'],
                            estimator_id=estimator, species_id=sp)
                original_ref = catalog.ModelArtifactRef.from_mapping(base)
                original_columns = trainer._columns(original_ref, source)
                removed = sorted(set(original_columns) & REMOVED)
                if vid in AFFECTED: assert 'dry_spell_observed_at_cutoff' in removed
                else: assert not removed
                summary = dict(ref=base, train_observations=len({meta(s)['observation_id'] for s in train}),
                               evidence_observations=len({meta(s)['observation_id'] for s in evidence}),
                               test_observations=len({meta(s)['observation_id'] for s in test}), removed=removed)
                if summary['train_observations'] < 8 or len({s['prediction_target'] for s in train}) < 2 or not (test or evidence):
                    summaries.append({**summary, 'status': 'skipped', 'reason': 'insufficient_train_or_no_evaluation'})
                    continue
                arm_list = ['current', 'off'] if removed else ['shared']
                for arm in arm_list:
                    columns = [c for c in original_columns if arm != 'off' or c not in REMOVED]
                    # _columns for V2/V3/V4 reads this exact feature list.
                    b = {**source, 'feature_set': {**source['feature_set'], 'predictive_feature_cols': columns}}
                    tr = freeze_rows(train, columns)
                    item = {**summary, 'arm': arm}
                    tick = time.monotonic()
                    try:
                        bundle, warn = fit_one(original_ref, b, tr, columns, budget)
                    except (ValueError, FloatingPointError) as exc:
                        summaries.append({**item, 'status': 'failed', 'reason': str(exc), 'seconds': time.monotonic()-tick})
                        continue
                    destinations = ('current', 'off') if arm == 'shared' else (arm,)
                    prevalence = {}
                    for species_id in species:
                        ys = [int(s['prediction_target'] == 'favorable') for s in train if meta(s)['species_id'] == species_id]
                        if ys: prevalence[species_id] = float(np.mean(ys))
                    ev = freeze_rows(evidence, columns)
                    pred = inference.predict_bundle_many(bundle, [s['predictive_features'] for s in ev],
                                                         species_ids=[meta(s)['species_id'] for s in ev])
                    for s, p in zip(ev, pred):
                        m = meta(s)
                        if m['species_id'] not in prevalence: continue
                        row = dict(version_id=vid, profile_id=profile['profile_id'], temporal_contract_id=contract,
                                   species_id=m['species_id'], area_id=m['area_id'], observation_id=m['observation_id'],
                                   validation_group_id=m['validation_group_14d'], split_id='fruiting_groups_14d',
                                   horizon_days=m['horizon_days'], y_true=int(s['prediction_target']=='favorable'),
                                   train_prevalence_probability=prevalence[m['species_id']],
                                   estimator_probabilities={estimator:p['probability']})
                        for a in destinations: logs[a].write(json.dumps(row)+'\n')
                    # Batch inference for exact historical rows and their same-cutoff weeks.
                    features = []; positions = []
                    for s in test:
                        m = meta(s); h = m['horizon_days']; f = {c:s['predictive_features'].get(c) for c in columns}
                        if contract.startswith('lag'):
                            for j in range(1,8):
                                shifted = retarget(f, m['target_date'], h, j, m.get('event_ages'))
                                if j == h:
                                    assert shifted == f, 'Historical input parity failed'
                                features.append(shifted); positions.append((m['observation_id'],h,j,m['species_id']))
                        else:
                            features.append(f); positions.append((m['observation_id'],7,7,m['species_id']))
                    predicted = inference.predict_bundle_many(bundle, features, species_ids=[x[3] for x in positions])
                    by_observation = {}
                    for (oid,h,j,actual_sp), p in zip(positions, predicted):
                        if oid not in by_observation:
                            by_observation[oid] = (np.full((7,7),np.nan),np.full((7,7),3,dtype=np.uint8))
                        probs,statuses = by_observation[oid]
                        probs[h-1,j-1] = p['probability'];statuses[h-1,j-1] = STATUS[p['applicability']['status']]
                    for oid, arrays in by_observation.items():
                        for a in destinations: caches[a][oid][ref_key(base)] = (base, *arrays)
                        probs,statuses=arrays
                        prediction_log.write(json.dumps(dict(arm=arm,ref=base,observation_id=oid,
                            probabilities=[[None if not np.isfinite(v) else float(v) for v in row] for row in probs],
                            applicability=statuses.tolist()))+'\n')
                    summaries.append({**item,'status':'complete','seconds':time.monotonic()-tick,'warnings':warn,
                                      'fit_config':bundle['fit_config'], 'training_observation_ids':sorted({meta(s)['observation_id'] for s in train})})
                    del bundle, tr, features, predicted
                    if budget['fits'] % 20 == 0:
                        print(json.dumps(dict(fold=fold,fits=budget['fits'],version=vid,profile=profile['profile_id'],seconds=round(time.monotonic()-started))),flush=True)
        for log in logs.values(): log.flush()
    for log in logs.values(): log.close()
    prediction_log.close()
    write_json(output/'fits.json', summaries)
    write_json(output/'split.json', {'stages':stages,'excluded_groups':excluded,'tests':tests})
    print(json.dumps(dict(fold=fold,phase='selector',fits=budget['fits'])),flush=True)
    selected = replay(output, caches, tests, registry)
    return dict(fold=fold,fit_attempts=budget['fits'],seconds=time.monotonic()-started,
                statuses=dict(collections.Counter(r['status'] for r in summaries)),selected_cases=len(selected))


def replay(output, caches, tests, registry):
    replay_output = output / 'replay'
    replay_output.mkdir()
    (replay_output/'empty.jsonl').touch(exist_ok=False)
    result = []
    versions = [v['version_id'] for v in registry['versions'] if v.get('installed_generation_id')]
    predictors = {sp: MushroomMLPredictor(sp, profiles_path=PROFILES) for sp in {r['species_id'] for r in tests.values()}}
    for arm in ('current','off'):
        q = quality.build_catalog(output/f'{arm}-evidence.jsonl',replay_output/'empty.jsonl',
                                  snapshot_id='sha256:'+sha(output.parent/'preflight.json'))
        write_json(replay_output/f'{arm}-quality.json',q)
        # Include test areas even when the evidence has no observation there.
        from rainmapper_core import mushroom_ml_reliability_audit as reliability
        with (output/f'{arm}-evidence.jsonl').open() as f:
            report = reliability.audit_rows((json.loads(line) for line in f),include_candidates=True,include_stability=False)
        selections = reliability.build_selection_catalog(report,operational_species_areas={(m['species_id'],m['area_id']) for m in tests.values()})
        index = {(r['species_id'],r['area_id'],r['prediction_day']):r for r in selections['species_area_selections']}
        weekly = precompute.weekly_aggregate_resolution_index(index,installed_version_ids=versions)
        evaluations = {(r['species_id'],*ref_key(r),r['horizon_days']):r for r in q['entries']}
        for oid,m in tests.items():
            sp, area = m['species_id'],m['area_id']; phase = predictors[sp].season_phase(date.fromisoformat(m['target_date']))
            cache = caches[arm].get(oid,{})
            def members(cut_h, weekday=None):
                rows=[]
                for key,(base,probs,statuses) in cache.items():
                    fixed=base['temporal_contract_id'].startswith('fixed')
                    if weekday is not None and fixed: continue
                    h=7 if fixed else (weekday if weekday is not None else cut_h)
                    i=6 if fixed else cut_h-1;j=6 if fixed else h-1
                    p=probs[i,j];status=int(statuses[i,j])
                    if not np.isfinite(p):continue
                    rows.append(dict(model_ref=ref_for(base,sp,h),available=True,
                                     prediction={'probability':float(p),'applicability':{'status':STATUS_NAMES[status]}},
                                     evaluation=evaluations.get((sp,*key,h),{}),features_used={}))
                return rows
            for h in range(1,8):
                resolution=index.get((sp,area,h),{'selection_status':'abstain','candidate':None})
                daily=members(h)
                day_comp, day_res=comparison.build_reliability_selected_operational_comparison(daily,resolution,season_phase=phase)
                by_day={j:weekly.get((sp,area,j),{'selection_status':'abstain','candidate':None}) for j in range(1,8)}
                weekly_status=(by_day[h].get('weekly_model_selection') or {}).get('status')
                if weekly_status=='daily_fallback' or not by_day[h].get('candidate'):
                    week_comp,week_res=day_comp,day_res
                else:
                    week_members={j:members(h,j) for j in range(1,8)}
                    adjusted=comparison.prioritize_weekly_resolutions_by_applicability(by_day,week_members)
                    week_comp,week_res=comparison.build_reliability_selected_operational_comparison(week_members[h],adjusted[h],season_phase=phase)
                    weekly_status=(adjusted[h].get('weekly_model_selection') or {}).get('status')
                for mode,comp,res in [('daily',day_comp,day_res),('weekly',week_comp,week_res)]:
                    winner=comp['selected_winners'][0] if comp['selected_winners'] and res.get('runtime_selection_status')=='winner' and phase!='out_of_season' else None
                    failures=collections.Counter(reason for exc in res.get('runtime_candidate_exclusions',[]) for reason in exc.get('reasons',[]))
                    result.append(dict(arm=arm,mode=mode,observation_id=oid,**m,horizon=h,season_phase=phase,
                        probability=winner['probability'] if winner else None,chosen=winner['model_ref'] if winner else None,
                        selection_scope=res.get('selection_scope'),fallback_rank=res.get('fallback_rank'),
                        weekly_status=weekly_status if mode=='weekly' else None,
                        reason='out_of_season' if phase=='out_of_season' else res.get('runtime_selection_reason'),exclusions=dict(failures)))
    write_json(replay_output/'selector-results.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--preflight',action='store_true');p.add_argument('--replay-only',action='store_true');p.add_argument('--fold',choices=FOLDS,required=True);args=p.parse_args()
    dest=args.output.resolve()
    if args.replay_only:
        if not dest.is_relative_to(ROOT/'docker-data/audits'):
            raise ValueError('Replay only an existing isolated audit')
        initial=json.loads((dest/'preflight.json').read_text())
        assert initial['fold']==args.fold
        assert initial['protected_before']=={str(path.relative_to(ROOT)):sha(path) for path in PROTECTED}
        registry=json.loads(REGISTRY.read_text());output=dest/args.fold
        split=json.loads((output/'split.json').read_text());fits=json.loads((output/'fits.json').read_text())
        caches={'current':collections.defaultdict(dict),'off':collections.defaultdict(dict)}
        with (output/'model-predictions.jsonl').open() as f:
            for line in f:
                row=json.loads(line);arrays=(np.asarray(row['probabilities'],dtype=float),np.asarray(row['applicability'],dtype=np.uint8))
                for arm in (('current','off') if row['arm']=='shared' else (row['arm'],)):
                    caches[arm][row['observation_id']][ref_key(row['ref'])]=(row['ref'],*arrays)
        started=time.monotonic()
        with threadpool_limits(limits=1): selected=replay(output,caches,split['tests'],registry)
        result=dict(fold=args.fold,fit_attempts=sum(r['status']!='skipped' for r in fits),
                    replay_seconds=time.monotonic()-started,fit_seconds_sum=sum(r.get('seconds',0) for r in fits),
                    statuses=dict(collections.Counter(r['status'] for r in fits)),selected_cases=len(selected),
                    recovery='replay saved predictions after catalog snapshot identifier rejection; no refits',
                    replay_code_sha256=sha(Path(__file__)))
        result['protected_after']={str(path.relative_to(ROOT)):sha(path) for path in PROTECTED}
        assert result['protected_after']==initial['protected_before'];result['protected_unchanged']=True
        write_json(dest/'result.json',result);print(json.dumps(result),flush=True)
        return
    if not dest.is_relative_to(ROOT/'docker-data/audits') or dest.exists():
        raise ValueError('Use a new audit directory; never overwrite or activate')
    registry=json.loads(REGISTRY.read_text());manifest=json.loads(MANIFEST.read_text());species=sorted(manifest['species_ids'])
    paths=[PREPARED/f'snapshot/biology-v{v}-{t}.json' for v in (3,4) for t in ('fixed','lag')]+[PREPARED/f'v5-current/biology-v5-{t}.json' for t in ('fixed','lag')]
    total=sum(p.stat().st_size for p in paths)
    if total>900_000_000:raise ValueError('Input byte budget exceeded')
    obs=population();stages,excluded=split_population(obs,args.fold)
    inventory={sp:{stage:dict(collections.Counter(obs[i]['y'] for i,s in stages.items() if s==stage and obs[i]['species_id']==sp and obs[i]['target_known'])) for stage in ('train','evidence','test')} for sp in sorted({r['species_id'] for r in obs.values()})}
    initial=dict(kind='isolated_predictor_dry_counter_ab',fold=args.fold,operational=False,models_written=False,
                 inputs={str(path.relative_to(ROOT)):{'bytes':path.stat().st_size,'sha256':sha(path)} for path in paths},
                 protected_before={str(path.relative_to(ROOT)):sha(path) for path in PROTECTED},species=species,
                 inventory=inventory,code={str(path.relative_to(ROOT)):sha(path) for path in [Path(__file__),PROFILES,*[ROOT/f'rainmapper_core/{name}.py' for name in ('mushroom_ml_runtime_trainer','mushroom_ml_runtime_inference','mushroom_ml_reliability_audit','mushroom_ml_quality_catalog','mushroom_ml_multiversion_comparison','mushroom_predictor_precompute')]]},
                 input_bytes=total,maximum_final_fits=2600,preflight_only=args.preflight)
    dest.mkdir(parents=True)
    write_json(dest/'preflight.json',initial)
    print(json.dumps({'preflight':str(dest),'input_bytes':total,'inventory':inventory}),flush=True)
    if args.preflight:return
    with threadpool_limits(limits=1):
        result=audit_fold(dest,args.fold,registry,species,obs,initial)
    result['protected_after']={str(path.relative_to(ROOT)):sha(path) for path in PROTECTED}
    assert result['protected_after']==initial['protected_before']
    result['protected_unchanged']=True
    write_json(dest/'result.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
