"""Indexed historical evidence for the unchanged native reliability audit."""
import hashlib
import json
from collections import OrderedDict
import numpy as np

from rainmapper_core import mushroom_competing_columns as columns
from rainmapper_core import mushroom_competing_evidence as evidence_contract
from rainmapper_core import mushroom_ml_reliability_audit as audit


class CaseAudit:
    def __init__(self, evidence, context):
        self.evidence = evidence
        self.cells = evidence_contract.cell_rows(evidence)
        if not isinstance(self.cells, columns.Cells):
            self.cells = columns.unpack(columns.pack(self.cells))
        self.keys, self.fragments, groups = [], [], []
        for sid, day, y, identity in evidence['cases']:
            visit = context[identity]
            if not visit['area'] or not visit['group']:
                raise ValueError('comparison_case_context_missing')
            case = json.dumps([visit['area'], identity], separators=(',', ':'))
            group = json.dumps([visit['area'], visit['group']], separators=(',', ':'))
            self.keys.append(case); groups.append(group)
            self.fragments.append(json.dumps([case, y, group], separators=(',', ':')).encode())
        order = sorted(range(len(self.keys)), key=self.keys.__getitem__)
        self.order = np.empty(len(order), dtype=np.uint16)
        self.order[order] = np.arange(len(order), dtype=np.uint16)
        group_ids = {g:i for i,g in enumerate(sorted(set(groups)))}
        self.groups = np.asarray([group_ids[g] for g in groups], dtype=np.uint16)
        self.y = np.asarray([c[2] for c in evidence['cases']], dtype=int)
        self.baselines = np.asarray(evidence['baselines'], dtype=float)
        self.positions = {}
        self.populations = OrderedDict()
        self.population_bytes = 0

    def _positions(self, cid):
        if cid not in self.positions:
            self.cells._index()
            at = self.cells._order[self.cells._offsets[cid]:self.cells._offsets[cid+1]]
            self.positions[cid] = at[np.argsort(self.order[self.cells.oid[at]], kind='stable')]
        return self.positions[cid]

    def _population(self, oids):
        key = oids.tobytes()
        if key not in self.populations:
            h = hashlib.sha256(b'[')
            for n, oid in enumerate(oids):
                if n: h.update(b',')
                h.update(self.fragments[oid])
            h.update(b']')
            result = h.hexdigest()[:16], len(np.unique(self.groups[oids]))
            size = len(key) + 256
            while self.populations and self.population_bytes + size > 2*1024*1024:
                old = self.populations.popitem(last=False)
                self.population_bytes -= len(old[0]) + 256
            if size <= 2*1024*1024:
                self.populations[key] = result
                self.population_bytes += size
            return result
        self.populations.move_to_end(key)
        return self.populations[key]

    def report(self,sid,valid):
     report=audit.audit_rows((),include_candidates=True,include_stability=False,include_area_scopes=False)
     policy=audit.AuditPolicy();mask=np.zeros(len(self.y),dtype=np.bool_);mask[list(valid)]=True
     groups={};ordered=[];computed={};count=0
     for cid,raw in enumerate(self.evidence['candidates']):
      positions=self._positions(cid);positions=positions[mask[self.cells.oid[positions]]]
      if not len(positions):continue
      oids=self.cells.oid[positions];identity=oids.tobytes()
      group=groups.setdefault(identity,(oids,[]));group[1].append((cid,positions))
      ordered.append(cid);count+=len(positions)
     for oids,items in groups.values():
      population,group_count=self._population(oids);y=self.y[oids]
      step=max(1,min(32,262144//len(oids)))
      for start in range(0,len(items),step):
       part=items[start:start+step]
       candidates=[tuple(self.evidence['candidates'][cid]) for cid,_ in part]
       p=np.stack([self.cells.p[at] for _,at in part]);b=np.stack([self.baselines[self.cells.bid[at]] for _,at in part])
       for (cid,_),row in zip(part,_evaluate_many(candidates,y,p,b,policy,population,group_count)):computed[cid]=row
     results={};candidates={};constant=set()
     for cid in ordered:
      candidate=tuple(self.evidence['candidates'][cid]);result=computed[cid]
      results[candidate,None]=result;candidates[candidate]={}
      if policy.reject_constant_species_predictions and result['constant_prediction'] is True:constant.add(candidate)
     if candidates:
      report['encountered_split_ids']=report['audited_split_ids']=[policy.official_split_id]
      report['species_scope_count']=1
      report['species_scopes']=[dict(species_id=sid,split_id=policy.official_split_id,source_row_count=count,
       operational_days=audit._operational_days(candidates,policy,top=5,include_candidates=True,include_stability=False,
        constant_species_candidates=constant,evaluation_cache=results))]
     return report


def _evaluate_many(candidates,y,p,b,policy,population,group_count):
 n=len(y);positive=y==1;negative=y==0
 good=p>=audit.FAVORABLE_THRESHOLD;bad=p<=audit.UNFAVORABLE_THRESHOLD
 tp=np.sum(good & positive,axis=1);fp=np.sum(good & negative,axis=1)
 tn=np.sum(bad & negative,axis=1);fn=np.sum(bad & positive,axis=1)
 uncertain=np.sum(~good & ~bad,axis=1)
 positives=int(np.sum(positive));negatives=int(np.sum(negative));both=bool(positives and negatives)
 brier=np.mean(np.square(y-p),axis=1);baseline=np.mean(np.square(y-b),axis=1)
 means=np.mean(p,axis=1);stds=np.std(p,axis=1);spreads=np.max(p,axis=1)-np.min(p,axis=1)
 ece=np.zeros(len(p))
 for lower in (0.,.2,.4,.6,.8):
  upper=lower+.2;mask=(p>=lower)&(p<=upper if upper>=1. else p<upper)
  counts=np.sum(mask,axis=1)
  for count in np.unique(counts):
   if not count:continue
   ids=np.flatnonzero(counts==count)
   indices=np.nonzero(mask[ids])[1].reshape(len(ids),int(count))
   prob=np.take_along_axis(p[ids],indices,axis=1)
   labels=y[indices]
   ece[ids]+=float(int(count)/n)*np.abs(np.mean(prob,axis=1)-np.mean(labels,axis=1))
 results=[]
 for i,candidate in enumerate(candidates):
  true,false=int(tp[i]),int(fp[i]);calls=true+false
  delta=float(baseline[i])-float(brier[i]);reasons=[]
  if policy.require_both_classes and not both:reasons.append('single_class')
  if not calls:reasons.append('no_favorable_calls')
  if policy.require_brier_improvement and delta<=0:reasons.append('not_better_than_prevalence')
  results.append(dict(candidate=audit._candidate_payload(candidate),candidate_key=list(candidate),
   population_id=population,observation_count=n,validation_group_count=group_count,
   positive_observation_count=positives,negative_observation_count=negatives,
   favorable_call_count=calls,true_favorable_count=true,false_favorable_count=false,
   favorable_precision=true/calls if calls else None,wilson_lower_95_observations=audit.wilson_lower_95(true,calls),
   favorable_recall=true/positives if positives else None,true_unfavorable_count=int(tn[i]),false_unfavorable_count=int(fn[i]),
   uncertain_count=int(uncertain[i]),brier_score=float(brier[i]),prevalence_brier_score=float(baseline[i]),brier_delta_vs_prevalence=delta,
   roc_auc=audit._binary_roc_auc(y,p[i]) if both else None,expected_calibration_error=float(ece[i]),
   probability_mean=round(float(means[i]),12),probability_standard_deviation=round(float(stds[i]),12),
   probability_range=round(float(spreads[i]),12),constant_prediction=bool(spreads[i]<=policy.constant_probability_range_tolerance) if n>=2 else None,
   constant_species_prediction=False,eligible=not reasons,exclusion_reasons=reasons))
 return results
