"""The indexed replay must preserve the native audit, including tie ordering."""
import random
import unittest
from rainmapper_core import mushroom_ml_reliability_audit as audit
from rainmapper_core import mushroom_competing_columns as columns
from rainmapper_core import mushroom_map_competing as competing
from rainmapper_core.mushroom_competing_audit import CaseAudit


class CaseAuditTests(unittest.TestCase):
    def test_exact_native_audit_for_missing_populations_ties_and_group_subsets(self):
        rng = random.Random(9241)
        candidates = [['v', 'p', 'fixed_gap_test', 7, 'constant']]
        candidates += [['v', 'p', 'fixed_gap_test', 7, 'varied']]
        candidates += [['v', 'p', 'lag_test', h, 'varied'] for h in range(1, 8)]
        cases = [[0, f'2026-06-{i%28+1:02d}', i%2, f'case-{i}'] for i in range(48)]
        context = {c[3]: {'area':f'área-{i%3}', 'group':f'episode-{i%7}'} for i,c in enumerate(cases)}
        cells = [[i, j, .7 if j == 0 else rng.choice([.2,.3,.5,.6,.7,.8]), i%2]
                 for i in range(48) for j in range(len(candidates)) if j < 2 or (i+j)%11]
        value = dict(species=['s'], candidates=candidates, cases=cases, baselines=[.4,.5], cells=cells)
        for packed in (False, True):
            if packed:
                value = {k:v for k,v in value.items() if k != 'cells'}
                value['packed_cells'] = columns.pack(cells)
            indexed = CaseAudit(value, context)
            for valid in ((), tuple(range(1)), tuple(range(3)), tuple(range(48)), tuple(range(0,48,2)), tuple(range(9,40))):
                rows = []
                for oid,cid,p,base in cells:
                    if oid not in valid: continue
                    row = dict(zip(competing.FIELDS, candidates[cid], strict=True))
                    identity = cases[oid][3]
                    rows.append({**row, 'species_id':'s', 'area_id':context[identity]['area'],
                        'observation_id':identity, 'validation_group_id':context[identity]['group'],
                        'split_id':audit.OFFICIAL_SELECTION_SPLIT_ID, 'y_true':cases[oid][2],
                        'train_prevalence_probability':value['baselines'][base],
                        'estimator_probabilities':{row['estimator_id']:p}})
                expected = audit.audit_rows(rows, include_candidates=True, include_stability=False, include_area_scopes=False)
                actual = indexed.report('s',valid)
                self.assertEqual(actual['species_scopes'], expected['species_scopes'])
                self.assertEqual(audit.build_selection_catalog(actual), audit.build_selection_catalog(expected))

    def test_auc_ties_matches_pairwise_definition(self):
        import numpy as np
        rng = random.Random(9400)
        for n in (2, 3, 9, 63, 128):
            y = np.asarray([i%2 for i in range(n)])
            p = np.asarray([rng.choice([.1,.2,.3,.8]) for _ in range(n)])
            positive, negative = p[y==1], p[y==0]
            expected = sum((a>b)+.5*(a==b) for a in positive for b in negative)/(len(positive)*len(negative))
            self.assertEqual(audit._binary_roc_auc(y,p), expected)


    def test_bulk_metrics_match_scalar_reductions_at_bin_boundaries(self):
        import numpy as np
        from rainmapper_core.mushroom_competing_audit import _evaluate_many
        rng = np.random.default_rng(481)
        policy = audit.AuditPolicy()
        for n in (1, 2, 7, 63, 1000):
            y = rng.integers(0, 2, n)
            for width in (1, 3, 32):
                p = rng.random((width, n))
                p[0] = np.resize(np.asarray([0., .2, .4, .6, .8, 1.]), n)
                if width > 1:
                    p[1] = .6
                baseline = rng.random((width, n))
                candidates = [('v','p','lag_test',1,str(i)) for i in range(width)]
                expected = [audit._evaluate_arrays(c,y,p[i],baseline[i],policy,
                    population_id='population',validation_group_count=3) for i,c in enumerate(candidates)]
                self.assertEqual(_evaluate_many(candidates,y,p,baseline,policy,'population',3), expected)
