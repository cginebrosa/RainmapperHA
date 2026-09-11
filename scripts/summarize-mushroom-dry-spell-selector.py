#!/usr/bin/env python3
"""Validate saved A/B replay results and produce observation-weighted summaries."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import numpy as np


def mean_or_none(values):
    return float(np.mean(values)) if values else None


def by_observation_mean(rows, fn):
    groups=collections.defaultdict(list)
    for row in rows: groups[row['observation_id']].append(fn(row))
    return mean_or_none([float(np.mean(v)) for v in groups.values()])


def paired_summary(rows):
    index={(r['arm'],r['observation_id'],r['horizon']):r for r in rows}
    keys=sorted({(r['observation_id'],r['horizon']) for r in rows})
    pairs=[(index['current',*k],index['off',*k]) for k in keys]
    result={'observations':len({k[0] for k in keys}),'scenarios':len(keys),'arms':{}}
    for arm in ('current','off'):
        values=[index[arm,*k] for k in keys];available=[r for r in values if r['probability'] is not None]
        calls=[r for r in available if r['probability']>=.6]
        good=sum(r['y'] for r in calls);bad=len(calls)-good
        positive=sum(r['y'] for r in values)
        result['arms'][arm]={'predictions':len(available),'abstentions':len(values)-len(available),
            'coverage_pct':100*len(available)/len(values) if values else None,
            'brier_available':by_observation_mean(available,lambda r:(r['y']-r['probability'])**2),
            'favorable_scenarios':len(calls),'true_favorable_scenarios':good,'false_favorable_scenarios':bad,
            'favorable_precision':good/len(calls) if calls else None,
            'positive_scenarios':positive,'positive_not_recommended_scenarios':positive-good,
            'favorable_recall':good/positive if positive else None,
            'winner_versions':dict(collections.Counter(r['chosen']['version_id'] for r in available)),
            'season_abstentions':sum(r['reason']=='out_of_season' for r in values),
            'weekly_statuses':dict(collections.Counter(str(r['weekly_status']) for r in values)),
            'exclusions':dict(sum((collections.Counter(r['exclusions']) for r in values if r['probability'] is None),collections.Counter()))}
    common=[(a,b) for a,b in pairs if a['probability'] is not None and b['probability'] is not None]
    changed=[(a,b) for a,b in pairs if a['probability']!=b['probability'] or a['chosen']!=b['chosen']]
    obs_delta=collections.defaultdict(list);obs_a=collections.defaultdict(list);groups={}
    for a,b in common:
        oid=a['observation_id'];groups[oid]=a['validation_group_14d']
        obs_delta[oid].append((a['y']-b['probability'])**2-(a['y']-a['probability'])**2)
        obs_a[oid].append((a['y']-a['probability'])**2)
    delta=mean_or_none([np.mean(v) for v in obs_delta.values()]);baseline=mean_or_none([np.mean(v) for v in obs_a.values()])
    interval=None
    if obs_delta:
        by_group=collections.defaultdict(list)
        for oid,v in obs_delta.items():by_group[groups[oid]].append(float(np.mean(v)))
        ordered=sorted(by_group);sums=np.array([sum(by_group[g]) for g in ordered]);counts=np.array([len(by_group[g]) for g in ordered])
        rng=np.random.default_rng(20260911);indices=rng.integers(len(ordered),size=(2000,len(ordered)))
        values=sums[indices].sum(axis=1)/counts[indices].sum(axis=1);interval=np.quantile(values,[.025,.975]).tolist()
    result['paired']={'common_scenarios':len(common),'common_observations':len(obs_delta),
        'current_brier_common':baseline,'off_brier_common':baseline+delta if baseline is not None else None,
        'delta_brier':delta,'relative_error_reduction_pct':-100*delta/baseline if baseline else None,
        'conditional_group_bootstrap_95':interval,'changed_scenarios':len(changed),
        'gained_predictions':sum(a['probability'] is None and b['probability'] is not None for a,b in pairs),
        'lost_predictions':sum(a['probability'] is not None and b['probability'] is None for a,b in pairs),
        'changed_common_winner':sum(a['chosen']!=b['chosen'] for a,b in common)}
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);args=p.parse_args();root=args.directory
    preflight=json.loads((root/'preflight.json').read_text());fold=preflight['fold'];path=root/fold
    split=json.loads((path/'split.json').read_text());fits=json.loads((path/'fits.json').read_text())
    rows=json.loads((path/'replay/selector-results.json').read_text());keys=set()
    for r in rows:
        key=(r['arm'],r['mode'],r['observation_id'],r['horizon']);assert key not in keys;keys.add(key)
        assert split['stages'][r['observation_id']]=='test'
        assert r['y']==split['tests'][r['observation_id']]['y']
        if r['chosen']:
            assert r['probability'] is not None and r['season_phase']!='out_of_season'
            if r['weekly_status']=='weekly_family' and r['mode']=='weekly':
                assert r['chosen']['temporal_contract_id'].startswith('lag')
                assert r['chosen']['horizon_days']==r['horizon']
    for r in fits:
        for oid in r.get('training_observation_ids',[]):assert split['stages'][oid]=='train'
    for arm in ('current','off'):
        with (path/f'{arm}-evidence.jsonl').open() as f:
            for line in f:
                r=json.loads(line);assert split['stages'][r['observation_id']]=='evidence'
    # Independent per-model scores, only the observed date (diagonal of each week).
    models={};shared=0
    with (path/'model-predictions.jsonl').open() as f:
        for line in f:
            r=json.loads(line);oid=r['observation_id'];m=split['tests'][oid]
            assert split['stages'][oid]=='test'
            ref=r['ref'];key=(ref['version_id'],ref['profile_id'],ref['temporal_contract_id'],ref['estimator_id'],m['species_id'])
            if r['arm']=='shared':
                assert ref['version_id'] not in ('altitude_v2','biology_v3','biology_v4');shared+=1
                continue
            models.setdefault(key,{}).setdefault(r['arm'],{})[oid]=r
    model_scores=[]
    for key,arms in models.items():
        if set(arms)!= {'current','off'}:continue
        ids=set(arms['current'])&set(arms['off']);a=[];b=[]
        for oid in ids:
            y=split['tests'][oid]['y'];pa=arms['current'][oid]['probabilities'];pb=arms['off'][oid]['probabilities']
            indices=[h for h in range(7) if pa[h][h] is not None and pb[h][h] is not None]
            if not indices:continue
            a.append(float(np.mean([(y-pa[h][h])**2 for h in indices])))
            b.append(float(np.mean([(y-pb[h][h])**2 for h in indices])))
        if a:model_scores.append(dict(version=key[0],profile=key[1],contract=key[2],estimator=key[3],species=key[4],
                          observations=len(a),current=float(np.mean(a)),off=float(np.mean(b)),delta=float(np.mean(b)-np.mean(a))))
    summary={'fold':fold,'checks':'disjoint train/evidence/test, output identities and weekly horizons verified',
             'shared_reference_records':shared,'selector':{},'model_summary':{},'failures':dict(collections.Counter(r.get('reason') for r in fits if r['status']=='failed')),
             'fit_status':dict(collections.Counter(r['status'] for r in fits)),
             'source_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (path/'replay/selector-results.json',path/'fits.json')}}
    for mode in ('daily','weekly'):
        subset=[r for r in rows if r['mode']==mode]
        summary['selector'][mode]={'all':paired_summary(subset),'species':{},'horizons':{}}
        for sp in sorted({r['species_id'] for r in subset}):
            summary['selector'][mode]['species'][sp]=paired_summary([r for r in subset if r['species_id']==sp])
        for h in range(1,8):summary['selector'][mode]['horizons'][str(h)]=paired_summary([r for r in subset if r['horizon']==h])
    for version in sorted({r['version'] for r in model_scores}):
        subset=[r for r in model_scores if r['version']==version];a=float(np.mean([r['current'] for r in subset]));b=float(np.mean([r['off'] for r in subset]))
        summary['model_summary'][version]={'cases':len(subset),'current':a,'off':b,'relative_error_reduction_pct':100*(a-b)/a,
            'improve':sum(r['delta'] < -1e-8 for r in subset),'worse':sum(r['delta'] > 1e-8 for r in subset),'ties':sum(abs(r['delta'])<=1e-8 for r in subset)}
    with (root/'summary.json').open('x') as f:json.dump(summary,f,ensure_ascii=False,allow_nan=False,indent=2)
    with (root/'model-comparison.csv').open('x') as f:
        writer=csv.DictWriter(f,fieldnames=list(model_scores[0]));writer.writeheader();writer.writerows(model_scores)
    with (root/'selector-comparison.csv').open('x') as f:
        fields=['mode','observation_id','species_id','area_id','target_date','horizon','y','current_probability','off_probability','current_model','off_model']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();index={(r['mode'],r['observation_id'],r['horizon'],r['arm']):r for r in rows}
        for r in rows:
            if r['arm']!='current':continue
            other=index[r['mode'],r['observation_id'],r['horizon'],'off']
            item={k:r[k] for k in fields[:7]};item.update(current_probability=r['probability'],off_probability=other['probability'],current_model=json.dumps(r['chosen']),off_model=json.dumps(other['chosen']));w.writerow(item)
    print(json.dumps({k:v for k,v in summary.items() if k!='selector'},ensure_ascii=False))
    for mode in summary['selector']:print(mode,json.dumps(summary['selector'][mode]['all'],ensure_ascii=False))


if __name__=='__main__':main()
