#!/usr/bin/env python3
"""Isolated, grouped dry-spell threshold audit. Never writes operational models."""
from __future__ import annotations

import os
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import argparse
import collections
import gc
import hashlib
import json
from pathlib import Path
import sys
import time
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
from rainmapper_core import mushroom_ml_biology_v3_evaluation as ev
from rainmapper_core import mushroom_ml_biology_v3_physical as physical
from rainmapper_core import mushroom_ml_biology_v4 as v4
from rainmapper_core import mushroom_ml_holdout as ho
from rainmapper_core import mushroom_ml_experiment_trainer as trainer

PRIMARY = ROOT / 'docker-data/audits/mushroom-dry-spell-ablation-20260905/snapshot'
SUPPLEMENT = ROOT / 'docker-data/audits/mushroom-hydric-ablation-20260905/prepared/snapshot'
PRIMARY_SPECIES = {'lactarius_deliciosus', 'boletus_edulis', 'boletus_pinophilus', 'boletus_aereus', 'amanita_caesarea'}
VARIANTS = ['current', 'off'] + [f'daily_{n}' for n in range(1, 6)] + ['window3_5', 'window3_10']
CONFIGS = [
    ('v2_lag_lr', 'v2', 'logistic_regression_reduced_v1'),
    ('v2_lag_rf', 'v2', 'random_forest_restricted_v1'),
    ('v3_core_fixed_hgb', 'v3', 'hist_gradient_boosting_restricted_v1'),
    ('v3_physical_lag_lr', 'physical', 'logistic_regression_reduced_v1'),
    ('v4_climatic_balance_lag_lr', 'v4', 'logistic_regression_reduced_v1'),
    ('v4_climatic_balance_lag_knn', 'v4', 'knn_distance_v1'),
]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def metadata(sample):
    m = sample.get('metadata') or {}
    return m.get('source_v3_metadata') or m


def clock(values, threshold, window=1):
    """Age of last qualifying complete trailing window; stop at unknown data."""
    run = 0
    for end in range(len(values), window - 1, -1):
        segment = values[end-window:end]
        if any(v is None or not np.isfinite(v) or v < 0 for v in segment):
            return (float(run) if run else np.nan), 1.0
        if sum(segment) >= threshold:
            return float(run), 0.0
        run += 1
    return (float(run) if run else np.nan), 1.0


def selftest():
    assert clock([12, 0, .001], 1) == (2., 0.)
    assert clock([0, 1], 1) == (0., 0.)
    assert clock([0, .999], 1) == (2., 1.)
    assert clock([0]*20 + [2]*10, 3) == (30., 1.)
    assert clock([0]*20 + [2]*10, 5, 3) == (0., 0.)
    assert clock([0]*20 + [20] + [0]*9, 5, 3) == (7., 0.)
    assert clock([None, 0, 0], 1) == (2., 1.)
    assert np.isnan(clock([5, None], 1)[0])
    assert np.isnan(clock([5, None, 0], 5, 3)[0])
    m = [dict(observation_id=str(i), target_date=f'2025-01-{i+1:02}', validation_group_14d=str(i)) for i in range(10)]
    groups = ordered_groups(m, 14)
    tr, va = indices(groups[:6], groups[6:8], m)
    assert len(tr) == 6 and len(va) == 2
    m[0]['target_date'] = '2025-01-08'
    tr, va = indices(groups[:6], groups[6:8], m)
    assert 0 not in tr
    print('selftest: trace, boundary, repeated rain, concentrated rain, missing data, temporal purge OK', flush=True)


def ordered_groups(meta, days):
    d = collections.defaultdict(list)
    for i, m in enumerate(meta):
        key = m.get(f'validation_group_{days}d')
        if not key or not m.get('observation_id') or not m.get('target_date'):
            raise ValueError('Missing grouping identity')
        d[key].append(i)
    return sorted(d.values(), key=lambda rows: (max(meta[i]['target_date'] for i in rows), meta[rows[0]][f'validation_group_{days}d']))


def indices(train_groups, valid_groups, meta):
    val = [i for g in valid_groups for i in g]
    if not val:
        return np.array([], dtype=int), np.array([], dtype=int)
    start = min(meta[i]['target_date'] for i in val)
    train = [i for g in train_groups if max(meta[j]['target_date'] for j in g) < start for i in g]
    assert not ({meta[i]['observation_id'] for i in train} & {meta[i]['observation_id'] for i in val})
    return np.asarray(train, dtype=int), np.asarray(val, dtype=int)


def row_weights(meta):
    count = collections.Counter(m['observation_id'] for m in meta)
    return np.array([1 / count[m['observation_id']] for m in meta])


def metrics(y, p, meta):
    w = row_weights(meta)
    b = float(np.average((y-p)**2, weights=w))
    pred = p >= .5
    ece = 0.
    for lo in np.arange(0, 1, .2):
        mask = (p >= lo) & ((p < lo+.2) if lo < .8 else (p <= 1))
        if mask.any():
            ece += w[mask].sum()/w.sum()*abs(np.average(y[mask]-p[mask], weights=w[mask]))
    return dict(brier=b, auc=float(roc_auc_score(y,p,sample_weight=w)) if len(set(y)) == 2 else None,
                calibration_error=float(ece), positive_signal_rate=float(np.average(pred,weights=w)),
                false_positive_rate=float(np.average(pred[y==0],weights=w[y==0])) if (y==0).any() else None,
                sensitivity=float(np.average(pred[y==1],weights=w[y==1])) if (y==1).any() else None)


def benchmark(kind):
    file = 'biology-v3-fixed.json' if kind == 'v3' else 'biology-v3-lag.json' if kind == 'v2' else 'biology-v4-lag.json'
    result = None
    for directory, primary in ((PRIMARY, True), (SUPPLEMENT, False)):
        source = json.loads((directory / file).read_text())
        source['samples'] = [s for s in source['samples']
                             if (metadata(s).get('species_id') in PRIMARY_SPECIES) == primary]
        if kind == 'v3':
            part = source
        elif kind == 'v2':
            part = ev.build_observation_altitude_v2_common_idw_benchmark(source)
        elif kind == 'physical':
            part = physical.materialize_benchmark(source)
        else:
            part = v4.materialize_comparison_benchmark(source, profile_id='climatic_balance')
        if result is None:
            result = part
        else:
            assert result['feature_set']['predictive_feature_cols'] == part['feature_set']['predictive_feature_cols']
            result['samples'].extend(part['samples'])
    return result


def candidate_matrices(samples, columns):
    X,y=ho.matrix(samples,columns)
    dry=columns.index('dry_spell_observed_at_cutoff')
    censor=columns.index('dry_spell_is_censored') if 'dry_spell_is_censored' in columns else None
    result={'current':X, 'off':X[:,[i for i in range(len(columns)) if i not in {dry,censor}]]}
    features={}
    for name in VARIANTS[2:]:
        window=3 if name.startswith('window') else 1
        threshold=float(name.split('_')[1]); changed=X.copy(); vals=[]
        for s in samples:
            series=metadata(s).get('weather_series',{}).get('daily_area_rain_idw_mean_mm')
            if not isinstance(series,list):
                raise ValueError('Missing frozen daily IDW series')
            # Confirm that series is known at cutoff, not at target.
            dates=metadata(s).get('weather_series',{}).get('daily_dates') or []
            if len(dates)!=len(series) or (dates and dates[-1] != metadata(s)['cutoff_date']):
                raise ValueError('Unaligned or future weather series')
            value,flag=clock(series[-90:],threshold,window)
            vals.append([value,flag])
        vals=np.array(vals);changed[:,dry]=vals[:,0]
        if censor is not None:changed[:,censor]=vals[:,1]
        result[name]=changed
        features[name]=vals[:,0]
    return result,y,features


def case(config, estimator, samples, columns, days, budget, external_only=False):
    started=time.monotonic(); meta=[metadata(s) for s in samples]; groups=ordered_groups(meta,days)
    out={'config':config,'species':meta[0]['species_id'],'group_days':days,'group_count':len(groups)}
    if len(groups)<8:
        return {**out,'status':'skipped','reason':'fewer_than_8_groups'}
    n=max(1,int(.7*len(groups))); tr,te=indices(groups[:n],groups[n:],meta)
    matrices,y,features=candidate_matrices(samples,columns)
    trainmeta=[meta[i] for i in tr]; testmeta=[meta[i] for i in te]
    out.update(n_train=len(tr),n_test=len(te),train_observations=len({m['observation_id'] for m in trainmeta}),
               test_observations=len({m['observation_id'] for m in testmeta}),
               purged_outer_rows=sum(len(g) for g in groups[:n])-len(tr))
    if len(tr)<8 or not len(te) or len(set(y[tr]))<2 or len(set(y[te]))<2:
        return {**out,'status':'skipped','reason':'outer_split_missing_classes_or_training_rows'}
    surviving=set(tr);tg=[g for g in groups[:n] if set(g)<=surviving]
    folds=[]
    for start,end in ((.5,.65),(.65,.8),(.8,1.)):
        lo=int(len(tg)*start);hi=int(len(tg)*end)
        a,b=indices(tg[:lo],tg[lo:hi],meta)
        if len(tg[lo:hi])>=2 and len(a)>=8 and len(set(y[a]))==2 and len(set(y[b]))==2:
            folds.append((a,b))
    out['inner_fold_count']=len(folds)
    if len(folds)<2 and not external_only:
        return {**out,'status':'skipped','reason':'fewer_than_2_valid_inner_temporal_folds'}
    if external_only and len(folds)>=2:
        return {**out,'status':'skipped','reason':'already_evaluated_in_nested_audit'}
    if external_only:
        folds=[]
    fits=0; fit_warnings=[]
    def predict(name,a,b):
        nonlocal fits
        if budget['fits']>=budget['limit']:raise RuntimeError('Fit preflight budget exceeded')
        fits+=1;budget['fits']+=1
        model=trainer._pipeline(estimator)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model.fit(matrices[name][a],y[a]);p=model.predict_proba(matrices[name][b])[:,1]
        fit_warnings.extend(str(w.message) for w in caught)
        if not np.isfinite(p).all():raise ValueError('Nonfinite probabilities')
        return p
    inner={}; chosen=None; daily=None; window=None
    if not external_only:
        for name in VARIANTS:
            scores=[metrics(y[b],predict(name,a,b),[meta[i] for i in b])['brier'] for a,b in folds]
            inner[name]={'scores':scores,'mean':float(np.mean(scores)),'se':float(np.std(scores,ddof=1)/np.sqrt(len(scores)))}
        best=min(VARIANTS,key=lambda k:inner[k]['mean'])
        chosen='off' if inner['off']['mean']<=inner[best]['mean']+inner[best]['se'] else best
        daily=min(VARIANTS[2:7],key=lambda k:inner[k]['mean']);window=min(VARIANTS[7:],key=lambda k:inner[k]['mean'])
    out.update(inner=inner,selected=chosen,selected_daily=daily,selected_window=window,external_only=external_only)
    # Freeze all choices above before external scoring.
    predictions={name:predict(name,tr,te) for name in VARIANTS}
    results={name:metrics(y[te],p,testmeta) for name,p in predictions.items()}
    for label,name in [('selected',chosen),('selected_daily',daily),('selected_window',window)]:
        if name is not None: results[label]=dict(results[name])
    base=predictions['current']; wt=row_weights(testmeta)
    rng=np.random.default_rng(42)
    unique=sorted({m[f'validation_group_{days}d'] for m in testmeta})
    boot=rng.integers(len(unique),size=(1000,len(unique)))
    for name,row in results.items():
        actual=out.get(name,name) if name.startswith('selected') else name
        p=predictions[actual];delta=(y[te]-p)**2-(y[te]-base)**2
        row['delta_brier']=row['brier']-results['current']['brier']
        row['classification_change_rate']=float(np.average((p>=.5)!=(base>=.5),weights=wt))
        sums=[];weights=[]
        for g in unique:
            mask=np.array([m[f'validation_group_{days}d']==g for m in testmeta])
            sums.append(float(np.sum(delta[mask]*wt[mask])));weights.append(float(wt[mask].sum()))
        dist=np.array(sums)[boot].sum(axis=1)/np.array(weights)[boot].sum(axis=1)
        row['paired_group_bootstrap_95']=np.quantile(dist,[.025,.975]).tolist()
    out.update(status='complete',results=results,fit_count=fits,elapsed_seconds=time.monotonic()-started,
               warnings=dict(collections.Counter(fit_warnings)),
               train_groups=sorted({m[f'validation_group_{days}d'] for m in trainmeta}),
               inner_splits=[{'train_observations':sorted({meta[i]['observation_id'] for i in a}),
                              'valid_observations':sorted({meta[i]['observation_id'] for i in b})} for a,b in folds],
               predictions=[dict(observation_id=m['observation_id'],area_id=m.get('area_id'),
                                 date=m['target_date'],group=m[f'validation_group_{days}d'],
                                 horizon=m.get('horizon_days'),target=int(y[i]),
                                 p={k:round(float(v[j]),10) for k,v in predictions.items()},
                                 dry_current=float(matrices['current'][i,columns.index('dry_spell_observed_at_cutoff')]),
                                 dry_candidates={k:float(v[i]) if np.isfinite(v[i]) else None for k,v in features.items()})
                            for j,(i,m) in enumerate(zip(te,testmeta))])
    return out


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--selftest',action='store_true')
    parser.add_argument('--external-only',action='store_true');parser.add_argument('--output',type=Path);parser.add_argument('--max-fits',type=int,default=6000)
    args=parser.parse_args();selftest()
    if args.selftest:return
    if args.output is None:parser.error('--output required')
    dest=args.output.resolve()
    if not dest.is_relative_to(ROOT/'docker-data/audits') or dest.exists():
        raise ValueError('Use a new output file under docker-data/audits; never overwrite results')
    paths=[d/f for d in (PRIMARY,SUPPLEMENT) for f in ('biology-v3-fixed.json','biology-v3-lag.json','biology-v4-lag.json')]
    if sum(p.stat().st_size for p in paths)>600_000_000:raise ValueError('Input size budget exceeded')
    protected=[ROOT/'mushroom-data/mushroom_observations.json',ROOT/'docker-data/mushroom-data/mushroom_observations.json',ROOT/'docker-media/rainmapper/predictor_precompute/active.sqlite3',ROOT/'docker-media/rainmapper/predictor_precompute/active-receipt.json']
    report=dict(kind='isolated_nested_dry_spell_threshold_audit',schema_version='1.0',operational=False,
                models_written=False,precompute_written=False,scope='historical exploratory snapshots 2026-09-05',external_only=args.external_only,
                inputs={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in paths},
                protected_before={str(p.relative_to(ROOT)):sha(p) for p in protected},
                code_sha256=sha(Path(__file__)),variants=VARIANTS,cases=[],inventories=[])
    dest.parent.mkdir(parents=True,exist_ok=True);budget={'fits':0,'limit':args.max_fits};started=time.monotonic()
    journal=dest.with_suffix('.jsonl')
    with journal.open('x') as log,threadpool_limits(limits=1):
        lastkind=None;b=None
        for config,kind,estimator in CONFIGS:
            if kind!=lastkind:
                b=None;gc.collect();b=benchmark(kind);lastkind=kind
            columns=b['feature_set']['predictive_feature_cols'];eligible=ho.eligible_samples(b)
            species=sorted({metadata(s)['species_id'] for s in b['samples']})
            for sp in species:
                ss=[s for s in eligible if metadata(s)['species_id']==sp]
                labels=collections.Counter(s['prediction_target'] for s in ss)
                report['inventories'].append(dict(config=config,species=sp,eligible_rows=len(ss),labels=dict(labels),
                   observations=len({metadata(s)['observation_id'] for s in ss})))
                if not ss:
                    report['cases'].append(dict(config=config,species=sp,status='skipped',reason='no_eligible_rows'));continue
                for days in (14,7):
                    item=case(config,estimator,ss,columns,days,budget,external_only=args.external_only)
                    log.write(json.dumps(item,allow_nan=False)+'\n');log.flush();report['cases'].append(item)
                    print(json.dumps({k:item.get(k) for k in ['config','species','group_days','status','reason','selected','fit_count']}),flush=True)
    report['fit_count']=budget['fits'];report['elapsed_seconds']=time.monotonic()-started
    report['protected_after']={str(p.relative_to(ROOT)):sha(p) for p in protected}
    report['protected_unchanged']=report['protected_before']==report['protected_after']
    data=json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2)
    if len(data.encode())>32_000_000:raise ValueError('Output size budget exceeded')
    dest.write_text(data+'\n');print(json.dumps(dict(output=str(dest),fits=budget['fits'],seconds=report['elapsed_seconds'],protected_unchanged=report['protected_unchanged'])),flush=True)


if __name__=='__main__':main()
