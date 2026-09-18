import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import date

spec = importlib.util.spec_from_file_location('station_research', Path(__file__).resolve().parents[1] / 'scripts/station_research.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name, value in {'candidates.json': [{'stationId':'ITEST1','rank':1}], 'stations.json': [],
                            'grid.json': [], 'search-points.json': [], 'baseline-summary.json':
                            {'known_wu':['IKNOWN'], 'excluded_codes':['IEXCLUDED']}}.items():
            (self.root / name).write_text(json.dumps(value))
        self.calls = []
        def fetch(endpoint, params):
            self.calls.append((endpoint, params))
            if endpoint.endswith('near'):
                return {'location': {'stationId':['INEW','ITEST1','IEXCLUDED','IKNOWN'],
                        'latitude':[41]*4, 'longitude':[1]*4, 'stationName':['name']*4}}
            return {'observations':[]}
        self.research = m.Research(self.root, fetch=fetch)

    def tearDown(self):
        self.research.db.close()
        self.temp.cleanup()

    def test_places_cached_and_separate_from_station_research(self):
        calls = []
        def fetch(params):
            calls.append(params)
            return {'features': [{'geometry': {'type':'Point','coordinates':[1.7,42.2]},
                                  'properties': {'name':'Pedraforca','city':'Saldes','country':'España'}},
                                 {'geometry': {'type':'Point','coordinates':[False,42]},'properties':{'name':'Bad'}},
                                 {'geometry': {'type':'Point','coordinates':[1,95]},'properties':{'name':'Bad'}}]}
        self.research.place_fetch = fetch
        before = self.research.state()
        result = self.research.search_places('  Pedraforca  ',42,1.7)
        self.assertEqual(result, self.research.search_places('pedraforca',42,1.7))
        self.assertEqual(len(calls),1)
        self.assertNotIn('apiKey',calls[0])
        self.assertEqual(result['results'][0]['label'],'Pedraforca · Saldes · España')
        self.assertEqual(len(result['results']),1)
        self.assertEqual(before,self.research.state())
        self.assertEqual(self.calls,[])
        other=m.Research(self.root,place_fetch=lambda _: self.fail('Should use persistent cache'))
        self.assertEqual(result,other.search_places('Pedraforca',42,1.7))
        other.db.close()

    def test_places_validation_empty_and_failed_responses(self):
        self.research.place_fetch=lambda _: {'features':[]}
        for query in (None,'a',' '*5,'a'*161):
            with self.assertRaises(ValueError):self.research.search_places(query)
        with self.assertRaises(ValueError):self.research.search_places('Molló',95,1)
        self.assertEqual(self.research.search_places('Molló'),{'results':[]})
        self.research.last_place_request=0
        self.research.place_fetch=lambda _: {'error':'unavailable'}
        with self.assertRaises(ValueError):self.research.search_places('Saldes')
        self.research.last_place_request=0
        self.research.place_fetch=lambda _: {'features':[]}
        self.assertEqual(self.research.search_places('Saldes'),{'results':[]})

    def test_presence_counts_zero_and_unique_dates_only(self):
        rows = [{'obsTimeLocal':d,'metric':{'precipTotal':rain}} for d,rain in
                [('2026-09-01',0),('2026-09-01',3),('2026-09-02',None),('2026-09-03',-1),
                 ('2026-09-04',float('nan')),('2026-09-05',False),('2026-08-01',1),('2026-10-01',3)]]
        result = m.summarize(rows,date(2026,9,1),date(2026,9,30))
        self.assertEqual(result['days'],1)
        self.assertEqual(result['window'],30)
        self.assertNotIn('2026-10-01',result['rainfall_mm'])

    def test_reviews_survive_restart_and_bootstrap(self):
        self.research.review('ITEST1','rejected')
        other = m.Research(self.root)
        self.assertEqual(other.get('ITEST1')['review_status'],'rejected')
        other.db.close()
        with self.assertRaises(ValueError):self.research.review('ITEST1','whatever')
        self.assertEqual(self.research.get('ITEST1')['review_status'],'rejected')

    def test_discovery_deduplicates_preserves_reviews_and_caches(self):
        self.research.review('ITEST1','accepted')
        result = self.research.near(41,1)
        self.research.near(41,1)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len(result['records']),3)
        self.assertEqual(self.research.get('ITEST1')['review_status'],'accepted')
        self.assertEqual(self.research.get('ITEST1')['kind'],'candidate')
        self.assertEqual(self.research.get('INEW')['kind'],'preliminary')

    def test_current_stations_omitted_from_search_and_old_candidates_preserved(self):
        # Old research may already contain reviews of a station in the operational catalog.
        row={'stationId':'IKNOWN','status':'ya conocida'}
        self.research.db.execute('INSERT INTO records VALUES (?,?,?,?)',
                                ('IKNOWN','candidate','accepted',json.dumps(row)))
        self.research.db.commit()
        result=self.research.near(41,1)
        self.assertEqual(result['ignored_current'],1)
        self.assertNotIn('IKNOWN',[r['stationId'] for r in result['records']])
        self.assertNotIn('IKNOWN',[r['stationId'] for r in self.research.state()['records']])
        self.assertEqual(self.research.get('IKNOWN')['review_status'],'accepted')
        self.assertIn('IKNOWN',[r['stationId'] for r in self.research.records(include_current=True)])
        other=m.Research(self.root)
        self.assertNotIn('IKNOWN',[r['stationId'] for r in other.state()['records']])
        self.assertEqual(other.get('IKNOWN')['review_status'],'accepted')
        other.db.close()

    def test_current_station_id_deduplication_is_not_coordinate_deduplication(self):
        self.research.current.add('INEW')
        result=self.research.near(41,1)
        self.assertEqual(result['ignored_current'],2)
        # ITEST1 shares coordinates with INEW but is a distinct station: keep it.
        self.assertIn('ITEST1',[r['stationId'] for r in result['records']])
        self.assertNotIn('INEW',[r['stationId'] for r in result['records']])

    def test_promotion_protects_exclusions_and_is_idempotent(self):
        self.research.near(41,1)
        for code in ('IEXCLUDED','IKNOWN'):
            with self.assertRaises(ValueError):self.research.promote(code)
        self.research.promote('INEW')
        self.research.review('INEW','doubtful')
        self.research.promote('INEW')
        self.assertEqual(self.research.get('INEW')['review_status'],'doubtful')
        self.assertEqual(self.research.get('INEW')['kind'],'candidate')
        self.assertEqual(len(self.research.records()),3)

    def test_clear_only_preliminary_preserves_promotions_and_reviews(self):
        self.research.near(41,1)
        self.research.promote('INEW')
        self.research.review('INEW','accepted')
        self.assertEqual(self.research.clear_preliminary()['removed'],1)
        self.assertEqual(len(self.research.records()),2)
        self.assertEqual(self.research.get('INEW')['review_status'],'accepted')
        self.assertEqual(self.research.clear_preliminary()['removed'],0)

    def test_clear_queries_survives_restart_without_touching_stations(self):
        self.research.near(41,1)
        self.research.review('ITEST1','accepted')
        before=self.research.records()
        self.assertEqual(len(self.research.state()['searches']),1)
        self.research.clear_queries()
        self.assertEqual(self.research.records(),before)
        other=m.Research(self.root)
        self.assertEqual(other.state()['searches'],[])
        other.db.close()
        self.research.near(41,1)
        self.assertEqual(len(self.research.state()['searches']),1)

    def test_availability_caches_and_rejects_unknown(self):
        a=self.research.availability('ITEST1')
        self.research.availability('ITEST1')
        self.assertEqual(len(self.calls),2)
        self.assertEqual((date.fromisoformat(a['end'])-date.fromisoformat(a['start'])).days,29)
        self.assertEqual(a['days'],0)
        with self.assertRaises(ValueError):self.research.availability('../file')
        with self.assertRaises(ValueError):self.research.availability('UNKNOWN')

    def test_api_errors_are_not_cached_as_zero(self):
        def fail(*args):raise ValueError('WU failed')
        self.research.fetch=fail
        with self.assertRaises(ValueError):self.research.availability('ITEST1')
        self.assertEqual(self.research.db.execute('SELECT count(*) FROM cache').fetchone()[0],0)

    def test_invalid_coordinates_never_query(self):
        for lat,lon in ((float('nan'),1),(91,1),(41,181),('41',1)):
            with self.assertRaises(ValueError):self.research.near(lat,lon)
        self.assertEqual(self.calls,[])

if __name__ == '__main__':unittest.main()
