#!/usr/bin/env python3
"""Read-only scoring checks and small summaries of isolated dry-spell audits."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def summarize(rows, variants, draws=2000):
    rng=np.random.default_rng(20260911)
    case_boot={}
    for sp in sorted({r['species'] for r in rows}):
        subset=[r for r in rows if r['species']==sp]
        groups=sorted({p['group'] for r in subset for p in r['predictions']})
        sampled=rng.integers(len(groups),size=(draws,len(groups)))
        for r in subset:
            pred=r['predictions'];counts=collections.Counter(p['observation_id'] for p in pred)
            w=np.array([1/counts[p['observation_id']] for p in pred]);y=np.array([p['target'] for p in pred])
            base=np.array([p['p']['current'] for p in pred]);weights=[];loss={k:[] for k in variants}
            for g in groups:
                mask=np.array([p['group']==g for p in pred]);weights.append(w[mask].sum())
                for k in variants:
                    actual=r.get(k,k) if k.startswith('selected') else k
                    p=np.array([p['p'][actual] for p in pred]);delta=(y-p)**2-(y-base)**2
                    loss[k].append((w[mask]*delta[mask]).sum())
            denominator=np.array(weights)[sampled].sum(axis=1)
            if np.any(denominator==0):raise ValueError('Empty group bootstrap replicate')
            case_boot[r['config'],sp]={k:np.array(loss[k])[sampled].sum(axis=1)/denominator for k in variants}
    result={}
    base=np.mean([r['results']['current']['brier'] for r in rows])
    for k in variants:
        delta=[r['results'][k]['delta_brier'] for r in rows]
        boot=np.mean([v[k] for v in case_boot.values()],axis=0)
        result[k]=dict(brier=float(base+np.mean(delta)),delta=float(np.mean(delta)),relative_error_reduction_pct=float(-100*np.mean(delta)/base),
                       improve=sum(d < -1e-8 for d in delta),worse=sum(d > 1e-8 for d in delta),tie=sum(abs(d)<=1e-8 for d in delta),
                       worst=float(max(delta)),best=float(min(delta)),paired_group_bootstrap_95=np.quantile(boot,[.025,.975]).tolist(),
                       delta_false_positive_rate=float(np.mean([r['results'][k]['false_positive_rate']-r['results']['current']['false_positive_rate'] for r in rows])),
                       delta_auc=float(np.mean([r['results'][k]['auc']-r['results']['current']['auc'] for r in rows])),
                       delta_calibration_error=float(np.mean([r['results'][k]['calibration_error']-r['results']['current']['calibration_error'] for r in rows])))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--prefix',default='');args=p.parse_args();root=args.directory
    paths=[root/'results.json',root/'descriptive.json'];documents=[json.loads(p.read_text()) for p in paths]
    assert documents[0]['inputs']==documents[1]['inputs']
    assert documents[0]['protected_before']==documents[1]['protected_after']
    assert all(d['protected_unchanged'] for d in documents)
    cases=[r for d in documents for r in d['cases'] if r['status']=='complete'];variants=documents[0]['variants']
    assert len({(r['config'],r['species'],r['group_days']) for r in cases})==len(cases)
    for r in cases:
        pred=r['predictions'];ids={p['observation_id'] for p in pred};counts=collections.Counter(p['observation_id'] for p in pred)
        for fold in r['inner_splits']:
            assert not (ids & set(fold['train_observations']))
            assert not (ids & set(fold['valid_observations']))
            assert not (set(fold['train_observations']) & set(fold['valid_observations']))
        if r['inner']:
            best=min(variants,key=lambda k:r['inner'][k]['mean'])
            chosen='off' if r['inner']['off']['mean']<=r['inner'][best]['mean']+r['inner'][best]['se'] else best
            assert r['selected']==chosen
        for k in variants:
            score=sum((p['target']-p['p'][k])**2/counts[p['observation_id']] for p in pred)/len(ids)
            assert abs(score-r['results'][k]['brier'])<1e-8
    out={'artifacts':{p.name:sha(p) for p in paths},'checks':'scores, choices, group separation, matching inputs and unchanged protected artifacts passed',
         'fits':sum(d['fit_count'] for d in documents),'seconds':sum(d['elapsed_seconds'] for d in documents),'scopes':{}}
    for days in (14,7):
        selected=[r for r in cases if r['group_days']==days]
        for label,rows in [('all_descriptive',selected),('nested_only',[r for r in selected if r['inner']])]:
            key=f'{label}_{days}'
            out['scopes'][key]={'cases':len(rows),'observations':len({p['observation_id'] for r in rows for p in r['predictions']}),
                               'variants':summarize(rows,variants + (['selected','selected_daily','selected_window'] if label=='nested_only' else [])), 'species':{}}
            for sp in sorted({r['species'] for r in rows}):
                ss=[r for r in rows if r['species']==sp]
                out['scopes'][key]['species'][sp]={'cases':len(ss),'off':summarize(ss,['current','off'])['off']}
    path=root/(args.prefix+'summary.json')
    with path.open('x') as f:json.dump(out,f,indent=2,ensure_ascii=False)
    with (root/(args.prefix+'case-results.csv')).open('x') as f:
        writer=csv.writer(f);writer.writerow(['species','config','group_days','scope','variant','brier','delta_brier','false_positive_rate','auc'])
        for r in cases:
            for k,v in r['results'].items():
                writer.writerow([r['species'],r['config'],r['group_days'],'nested' if r['inner'] else 'descriptive',k,v['brier'],v['delta_brier'],v['false_positive_rate'],v['auc']])
    print(json.dumps(out,ensure_ascii=False))


if __name__=='__main__':main()
