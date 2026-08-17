from datetime import date, timedelta
from unittest import TestCase

from rainmapper_core import mushroom_ml_model_catalog as catalog
from rainmapper_core import mushroom_ml_raw_weather as raw
from rainmapper_core import mushroom_ml_runtime_features as runtime_features


class MushroomMLRuntimeFeaturesTests(TestCase):
    def area_series(self):
        start = date(2024, 1, 1)
        result = {
            "daily_dates": [
                (start + timedelta(days=index)).isoformat()
                for index in range(raw.LOOKBACK_DAYS)
            ]
        }
        for key in raw.AREA_SERIES_KEYS.values():
            result[key] = [float(index % 17) for index in range(raw.LOOKBACK_DAYS)]
        return result

    def ref(self, *, version_id, contract, profile, estimator, horizon):
        return catalog.ModelRef(
            batch_id="batch-a",
            generation_id="generation-a",
            version_id=version_id,
            temporal_contract_id=contract,
            profile_id=profile,
            estimator_id=estimator,
            species_id="boletus_edulis",
            horizon_days=horizon,
        )

    def test_v5_lag_uses_complete_idw_physical_state_profile(self) -> None:
        result = runtime_features.build_runtime_features(
            self.ref(
                version_id="biology_v5_raw_weather_discovery",
                contract=raw.LAG_CONTRACT_ID,
                profile="raw_primary_plus_physical_state",
                estimator="elastic_net_logistic_raw365_v1",
                horizon=3,
            ),
            target_date=date(2024, 12, 31),
            area_id="area-a",
            area_context=None,
            area_series=self.area_series(),
            stations={},
        )
        features = result["predictive_features"]
        self.assertEqual(features["horizon_days"], 3.0)
        self.assertIn("target_day_sin", features)
        self.assertEqual(features["rain_mm__lag_000"], float(364 % 17))
        self.assertEqual(features["eto0_mm__lag_000"], float(364 % 17))
        self.assertEqual(
            features["soil_water_fraction__lag_000"], float(364 % 17)
        )
        self.assertIn("soil_water_area_mean_at_cutoff", features)

    def test_v6_uses_same_raw_series_without_four_horizon_fits(self) -> None:
        result = runtime_features.build_runtime_features(
            self.ref(
                version_id="biology_v6_smooth_hierarchical",
                contract="lag_event_biology_v6_smooth_hierarchical_v2",
                profile="smooth_weather_physical_state",
                estimator="smooth_partial_pooling_logistic_v1",
                horizon=7,
            ),
            target_date=date(2024, 12, 31),
            area_id="area-a",
            area_context=None,
            area_series=self.area_series(),
            stations={},
        )
        features = result["predictive_features"]
        self.assertEqual(
            len(features),
            len(raw.DAILY_CHANNELS) * 365
            + len(raw.PHYSICAL_STATE_SCALARS)
            + 3,
        )
        self.assertEqual(features["horizon_days"], 7.0)
        self.assertIn("target_day_sin", features)
        self.assertIn("soil_water_fraction__lag_000", features)
        self.assertEqual(result["metadata"]["horizon_days"], 7)
