import json
from pathlib import Path
import unittest

from rainmapper_core.mushroom_model_labels import model_input_details, valid_model_details
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_smooth_hierarchical as smooth
from rainmapper_core import mushroom_ml_biology_v4 as v4


class ModelInputDetailsTests(unittest.TestCase):
    def test_actual_feature_contracts_distinguish_smi_and_direct_balance(self):
        cases = [
            (v4.predictive_columns(v4.LAG_EVENT_BIOLOGY_V4_ID, 'extended_weather'), False, False),
            (v4.predictive_columns(v4.LAG_EVENT_BIOLOGY_V4_ID, 'climatic_balance'), False, True),
            (v4.predictive_columns(v4.LAG_EVENT_BIOLOGY_V4_ID, 'soil_water'), True, True),
            (smooth.raw_columns(), True, True),
            (smooth.raw_columns(channels=raw.RAW_CHANNELS, window_days=30), True, False),
        ]
        reference = dict(version_id='same_version', profile_id='specific_profile',
                         estimator_id='smooth_partial_pooling_logistic_v1')
        profiles = [{**reference, 'input_requirements': {'predictive_window_days': 30}}]
        for columns, smi, balance in cases:
            detail = model_input_details(reference, columns, profiles)
            self.assertEqual('smi' in detail['inputs'], smi)
            self.assertEqual('balance' in detail['inputs'], balance)
            self.assertEqual(detail['window_days'], 30)
            self.assertTrue(valid_model_details(detail))
            self.assertLess(len(json.dumps(detail)), 300)
        self.assertIsNone(model_input_details(reference, [], profiles))
        self.assertIsNone(model_input_details(reference, ['temp_min_c'], [])['window_days'])

    def test_localized_tooltip_keys_have_all_three_languages(self):
        labels = json.loads(Path('mushroom-data/mushroom_labels.json').read_text())
        keys = [key for key in labels if key.startswith('ui.prediction_map_model_')]
        self.assertGreater(len(keys), 20)
        for key in keys:
            self.assertTrue(all(labels[key].get(lang) for lang in ('es', 'ca', 'en')), key)

    def test_descriptor_validation_rejects_unbounded_or_unknown_metadata(self):
        good = dict(estimator='extra_trees_restricted_v1', inputs=['rain'], window_days=60)
        for bad in [dict(good, inputs=['unknown']), dict(good, inputs=['rain']*100),
                    dict(good, window_days=True), dict(good, window_days=366),
                    dict(good, estimator='unknown'), dict(good, extra='x')]:
            self.assertFalse(valid_model_details(bad))
