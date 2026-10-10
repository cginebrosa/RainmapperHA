import random
import unittest
from datetime import date
from rainmapper_core import mushroom_competing_evidence as evidence
from rainmapper_core import mushroom_competing_columns as columns
from rainmapper_core.mushroom_competing_statistics import DailyStatistics


class DailyStatisticsTests(unittest.TestCase):
    def test_exact_groups_with_unsorted_dates_windows_and_removed_first_case(self):
        rng = random.Random(3017)
        cases = [[i%2,f'2026-06-{rng.randrange(1,12):02d}',i%2,f'{i:024x}'] for i in range(80)]
        cells = [[i,j,rng.choice([.2,.6,.9]),i%3] for i in range(80) for j in range(9) if (i+j)%5]
        candidates = [['v','p','lag_example',j%7+1,str(j)] for j in range(9)]
        value = dict(species=['a','b'],cases=cases,candidates=candidates,baselines=[.1,.6,.7],cells=cells)
        typed = columns.unpack(columns.pack(cells))
        index = DailyStatistics(value,typed)
        for sid in ('a','b'):
            for bound in (date(2026,6,3),date(2026,6,9),date(2026,7,1)):
                for excluded in ([],[0,1,2,3,7],list(range(0,80,2)),list(range(80))):
                    valid = [i for i,c in enumerate(cases) if value['species'][c[0]]==sid and c[1]<bound.isoformat() and i not in excluded and typed.has_case(i)]
                    original = {**value,'cells':typed.subset(valid)}
                    original_rows = list(evidence.expanded_rows(original))
                    self.assertEqual(list(index.view(sid,bound,excluded)),
                                     [(s,c,d,tuple(stats)) for s,c,d,stats in original_rows])
                    selected = {tuple(candidates[i]) for i in (1,3,5)}
                    actual = list(index.view(sid,bound,excluded).rows_for(selected,date(2026,6,5),date(2026,6,10)))
                    expected = [(s,c,d,tuple(stats)) for s,c,d,stats in original_rows
                                if tuple(c) in selected and '2026-06-05' <= d < '2026-06-10']
                    self.assertEqual(actual,expected)
                    aggregates, years = index.view(sid,bound,excluded).aggregates_for(
                        selected,date(2026,6,5),date(2026,6,10))
                    parts = {}
                    for _,c,d,stats in expected:
                        parts.setdefault(tuple(c),[]).append((d,stats))
                    reference = {c: (*[sum(s[i] for _,s in rows) for i in range(6)],
                                     min(s[6] for _,s in rows), max(s[7] for _,s in rows),
                                     tuple(sorted((d,s[8]) for d,s in rows)))
                                 for c,rows in parts.items()}
                    self.assertEqual(aggregates,reference)
                    self.assertEqual(years,{int(row[2][:4]) for row in expected})
