import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zlib

from rainmapper_core import mushroom_competing_columns as columns
from rainmapper_core import mushroom_competing_evidence as evidence
from rainmapper_core import mushroom_competing_panels as panels
from rainmapper_core import mushroom_map_competing as competing
from tests import test_mushroom_map_prediction as fixtures


class ColumnTests(unittest.TestCase):
    def fixture(self, n=20, candidates=None):
        refs = candidates or [['biology_v3', 'profile-'+str(i), 'fixed_gap_7d_biology_v3', 7, 'lr'] for i in range(3)]
        # Dates deliberately interleaved, with some missing candidate rows.
        cases = [[0, '2025-09-'+str(1+(i*7)%27).zfill(2), i%2,
                  hashlib.sha256(str(i).encode()).hexdigest()[:24]] for i in range(n)]
        cells = [[oid, cid, ((oid*17+cid*13)%97)/100, oid%3]
                 for oid in range(n) for cid in range(len(refs)) if (oid+cid)%11]
        return {'kind': evidence.KIND, 'revision':'a'*64, 'batch_id':'b', 'snapshot_id':'s',
                'quality_sha256':'q', 'cutoff':'2026-10-01', 'species':['s'],
                'candidates':refs, 'cases':cases, 'baselines':[.3,.5,.7], 'cells':cells}

    def compact(self, value):
        return {**{k:v for k,v in value.items() if k!='cells'},
                'packed_cells': columns.pack(value['cells'])}

    def test_float64_roundtrip_candidate_views_and_subsets(self):
        value = self.fixture()
        packed = self.compact(value)
        evidence.validate(packed)
        cells = evidence.cell_rows(packed)
        self.assertEqual(list(cells), list(map(tuple, value['cells'])))
        self.assertIs(evidence.cell_rows(packed), cells)
        self.assertTrue(cells.has_case(5)); self.assertFalse(cells.has_case(100))
        wanted = (1, 4, 8)
        subset = cells.subset(wanted)
        self.assertEqual(len(subset), sum(r[0] in wanted for r in value['cells']))
        self.assertEqual(list(subset), [tuple(r) for r in value['cells'] if r[0] in wanted])
        self.assertIs(cells._order, subset._order)
        for cid in range(3):
            self.assertEqual(list(subset.candidate_rows(cid)),
                             [tuple(r) for r in value['cells'] if r[0] in wanted and r[1]==cid])
        with self.assertRaises(ValueError): cells.subset([-1])

    def test_daily_statistics_and_all_rankings_remain_exact(self):
        resolutions = fixtures.PointWeekTests().resolutions()
        refs = sorted({competing.identity(e['candidate'])
                       for r in resolutions.values() for e in r['candidate_chain']})
        value = self.fixture(40, refs); packed = self.compact(value)
        def rows(source):
            return {(sid,tuple(ref),day):stats for sid,ref,day,stats in evidence.expanded_rows(source)}
        self.assertEqual(rows(value), rows(packed))
        for method in 'ABCD':
            for k in (0,2,4,100):
                self.assertEqual(competing.rank(resolutions,value,'s','2026-01-01',method,k),
                                 competing.rank(resolutions,packed,'s','2026-01-01',method,k))

    def test_malformed_or_oversized_vectors_fail_before_expansion(self):
        packet = columns.pack(self.fixture()['cells'])
        for change in ({'count':columns.MAX_CELLS+1}, {'count':True}, {'sha256':'0'*64},
                       {'data':packet['data']+'!'}, {'format':'unknown'}):
            with self.assertRaises(ValueError): columns.unpack({**packet, **change})
        bomb = {**packet, 'count':1, 'data':base64.b64encode(zlib.compress(b'0'*1000000)).decode()}
        with self.assertRaises(ValueError): columns.unpack(bomb)
        for rows in ([[0,0,float('nan'),0]], [[0,0,.5,0],[0,0,.6,0]], [[65536,0,.5,0]]):
            with self.assertRaises(ValueError): columns.pack(rows)
        value = self.compact(self.fixture())
        value['baselines'] = []
        with self.assertRaises(ValueError): evidence.validate(value)

    def test_large_evidence_stays_columnar_across_private_and_public_storage(self):
        refs = [['v','p'+str(i),'fixed',7,'e'] for i in range(240)]
        value = self.fixture(250, refs)
        self.assertGreater(len(value['cells']), evidence.MAX_CASES)
        evidence.validate(value, private=True)
        wire = evidence.to_wire(value)
        self.assertNotIn('cells', wire)
        raw = evidence.encode(wire)
        self.assertLess(len(raw), evidence.MAX_BYTES)
        evidence.validate(json.loads(raw))
        with tempfile.TemporaryDirectory() as tmp:
            store = panels.Panels(Path(tmp)/'panels.sqlite')
            self.addCleanup(store.close)
            store.save_generation('r', {'evidence': value, 'visits':[], 'unit_index':{}})
            loaded = store.generation('r')
            self.assertNotIn('cells', loaded['evidence'])
            self.assertEqual(list(evidence.cell_rows(loaded['evidence'])), list(map(tuple,value['cells'])))
            store.db.execute('UPDATE generations SET payload=?', (b'RMG1'+b'bad',))
            with self.assertRaises(ValueError): store.generation('r')


if __name__ == '__main__':
    unittest.main()
