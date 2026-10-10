from datetime import date, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from rainmapper_core import mushroom_competing_comparison as comparison
from rainmapper_core import mushroom_competing_parallel as parallel
from rainmapper_core.mushroom_competing_panels import Panels, RAIN_FIELDS


class ParallelTests(unittest.TestCase):
    def test_striped_ranges_cover_every_visit_once_with_bounded_imbalance(self):
        for count in (1, 127, 128, 129, 1001, 5000):
            for workers in (2, 3, 4):
                ranges = parallel.partition_ranges(count, workers)
                parts = [[i for start, end in part for i in range(start, end)] for part in ranges]
                self.assertEqual(sorted(i for part in parts for i in part), list(range(count)))
                self.assertLessEqual(max(map(len, parts))-min(map(len, parts)), 128)
        with self.assertRaisesRegex(ValueError, 'plan_limit'):
            parallel.partition_ranges(5000, 5)

    def test_merge_preserves_exact_horizon_counts_and_common_exclusions(self):
        visits = [dict(id=str(i),species_id=str(i%2),day=(date(2025,1,1)+timedelta(days=i)).isoformat(),y=int(i%3==0)) for i in range(1001)]
        def replay(v, issue, k):
            if int(v['id'])%67==0:
                raise comparison.MissingReplay('fixture_missing')
            return {method:None if (int(v['id'])+index)%11==0 else (issue.day+index)%3==0
                    for index,method in enumerate(comparison.METHODS)}
        expected = comparison.evaluate(visits,k=3.7,cutoff='2030-01-01',replay=replay)
        for n in (2,3,4):
            parts = [comparison.evaluate([v for start,end in part for v in visits[start:end]],k=3.7,cutoff='2030-01-01',replay=replay)
                     for part in parallel.partition_ranges(len(visits),n)]
            self.assertEqual(parallel.merge_results(parts),expected)
        changed = dict(parts[0],k=4)
        with self.assertRaisesRegex(ValueError,'incompatible_parts'):
            parallel.merge_results([changed,*parts[1:]])

    def test_part_cache_reads_base_and_parent_merges_without_losing_days(self):
        day = date(2026,10,1)
        member = {'prediction':{'probability':.7,'applicability':{'status':'supported'}},'features_used':dict.fromkeys(RAIN_FIELDS)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);parent=Panels(root/'parent.sqlite')
            self.addCleanup(parent.close)
            parent.write('unit','species','visit',[(day.isoformat(),1,member)])
            base = Panels.readonly(root/'parent.sqlite');self.addCleanup(base.close)
            with self.assertRaises(sqlite3.OperationalError):
                base.db.execute('CREATE TABLE forbidden (n)')
            part = parallel._PartPanels(root/'part.sqlite',base,1024*1024)
            self.assertEqual(part.read('unit','species','visit',day,1)['prediction']['probability'],.7)
            part.write('unit','species','visit',[((day+timedelta(days=1)).isoformat(),2,member)],merge=True)
            part.close()
            self.assertEqual(len(parent._packet('unit','species','visit')),1)
            parent.merge_from(root/'part.sqlite')
            self.assertEqual(len(parent._packet('unit','species','visit')),2)
            parent.merge_from(root/'part.sqlite')
            self.assertEqual(len(parent._packet('unit','species','visit')),2)
