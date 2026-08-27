from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

from rainmapper_core import mushroom_ml_holdout as holdout


class _FakeLogistic:
    saga_fits = 0

    def __init__(self, *, solver="lbfgs", **_kwargs):
        self.solver = solver

    def fit(self, X, _y):
        if self.solver == "saga":
            type(self).saga_fits += 1
        self.coef_ = np.zeros((1, X.shape[1]))
        self.intercept_ = np.zeros(1)
        self.n_iter_ = np.ones(1, dtype=int)
        self.classes_ = np.asarray([0, 1])
        return self

    def predict_proba(self, X):
        return np.column_stack((np.full(len(X), 0.5), np.full(len(X), 0.5)))


class _FakeSparse(_FakeLogistic):
    fits = 0

    def __init__(self, **_kwargs):
        super().__init__()
        self.converged_ = True

    def fit(self, X, y):
        type(self).fits += 1
        return super().fit(X, y)


def _sample(observation, horizon, target, day):
    contract = "lag_event_biology_v5_raw365_v1"
    return {
        "sample_id": f"{observation}|{contract}|h{horizon}",
        "prediction_target": target,
        "predictive_features": {"target_day_sin": float(day), "target_day_cos": float(-day), "horizon_days": horizon},
        "quality": {},
        "metadata": {
            "observation_id": observation, "species_id": "species_a", "area_id": "area_a",
            "micro_area_id": "micro_a", "target_date": f"2025-01-0{day}", "cutoff_date": "2025-01-01",
            "horizon_days": horizon, "temporal_contract_id": contract,
            "validation_group_7d": f"group_{day}",
        },
    }


class HoldoutEvaluationTests(unittest.TestCase):
    def test_frozen_tuning_skips_v5_inner_search(self):
        train = [_sample("train_a", 1, "unfavorable", 1), _sample("train_b", 2, "favorable", 2)]
        test = [_sample("test", 1, "favorable", 3)]
        benchmark = {
            "feature_set": {"profiles": {"raw_primary": ["target_day_sin", "target_day_cos", "horizon_days"]}},
            "samples": train + test,
        }
        scopes = []
        for estimator_id, fit_config in (
            (
                holdout.V5_ESTIMATORS[0],
                {"C": 0.1, "l1_ratio": 0.9, "class_weight": None, "inner_selection_available": True},
            ),
            (
                holdout.V5_ESTIMATORS[1],
                {"regularization": 0.1, "l1_ratio": 0.5, "inner_selection_available": True},
            ),
        ):
            scope = {
                "version_id": "biology_v5_raw_weather_discovery",
                "temporal_contract_id": "lag_event_biology_v5_raw365_v1",
                "profile_id": "raw_primary",
                "estimator_id": estimator_id,
                "species_id": "species_a",
            }
            scopes.append(
                {
                    "key": "|".join(scope[key] for key in (
                        "version_id", "temporal_contract_id", "profile_id", "estimator_id", "species_id"
                    )),
                    "scope": scope,
                    "fit_config": fit_config,
                }
            )
        with (
            patch.object(holdout, "LogisticRegression", _FakeLogistic),
            patch.object(holdout, "SparseGroupLogisticClassifier", _FakeSparse),
            patch.object(holdout, "_select_v5", side_effect=AssertionError("must not retune")),
        ):
            report, _rows, _selections = holdout.evaluate_dataset(
                benchmark,
                version_id="biology_v5_raw_weather_discovery",
                profile_id="raw_primary",
                group_days=7,
                train_keys={holdout.comparison_key(row) for row in train},
                test_keys={holdout.comparison_key(row) for row in test},
                mode="v5",
                tuning_catalog={"decisions": scopes},
            )

        self.assertTrue(
            all(row["available"] for row in report["species"]["species_a"]["estimators"].values())
        )

    def test_lag_horizons_reuse_one_fit_per_estimator(self):
        train = [_sample("train_a", 1, "unfavorable", 1), _sample("train_b", 2, "favorable", 2)]
        test = [_sample("test", horizon, "favorable", 3) for horizon in (1, 2, 3, 7)]
        benchmark = {
            "feature_set": {"profiles": {"raw_primary": ["target_day_sin", "target_day_cos", "horizon_days"]}},
            "samples": train + test,
        }
        _FakeLogistic.saga_fits = 0
        _FakeSparse.fits = 0
        with (
            patch.object(holdout, "LogisticRegression", _FakeLogistic),
            patch.object(holdout, "SparseGroupLogisticClassifier", _FakeSparse),
            patch.object(holdout, "_select_v5", return_value=({}, False)),
        ):
            _report, rows, _selections = holdout.evaluate_dataset(
                benchmark, version_id="biology_v5_raw_weather_discovery", profile_id="raw_primary",
                group_days=7,
                train_keys={holdout.comparison_key(row) for row in train},
                test_keys={holdout.comparison_key(row) for row in test}, mode="v5",
            )
        self.assertEqual(_FakeLogistic.saga_fits, 1)
        self.assertEqual(_FakeSparse.fits, 1)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({row["row_key"] for row in rows}), 4)
        self.assertEqual({row["horizon_days"] for row in rows}, {1, 2, 3, 7})
        self.assertEqual({row["temporal_contract_id"] for row in rows}, {"lag_event_biology_v5_raw365_v1"})


if __name__ == "__main__":
    unittest.main()
