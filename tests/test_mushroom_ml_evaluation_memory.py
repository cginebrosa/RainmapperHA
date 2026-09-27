"""Evaluation input lifetime and numerical parity on small synthetic fixtures."""
import contextlib
import copy
import gc
import importlib.util
import io
import json
import tempfile
import sys
import unittest
import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TrackedDict(dict):
    pass


class EvaluationMemoryTests(unittest.TestCase):
    def setUp(self):
        self.v5 = script("evaluate-biology-v5-raw-benchmark")
        self.v6 = script("evaluate-biology-v6-smooth-hierarchical")

    def test_shared_sources_loaded_once_and_released_after_last_consumer(self):
        """V5 and V6 see the same object; no previous temporal survives loading."""
        refs, loads, consumed = [], [], []

        def load(path):
            if str(path).endswith("v3-lag.json"):
                gc.collect()
                self.assertTrue(all(ref() is None for ref in refs))
            source = TrackedDict(samples=[])
            refs.append(weakref.ref(source))
            loads.append(path.name)
            return source

        def evaluate(args, temporal, source, selected, tuning):
            consumed.append((temporal, id(source["v5"])))
            return {}, [], []

        def after(temporal, benchmark):
            self.assertEqual(consumed[-1], (temporal, id(benchmark)))
            # Other source families have already been released.
            self.assertIsNone(refs[-3]())
            self.assertIsNone(refs[-2]())
            self.assertIs(refs[-1](), benchmark)

        args = SimpleNamespace(snapshot=Path("snapshot"), v5_dir=Path("v5"))
        with mock.patch.object(self.v5, "_load", side_effect=load), mock.patch.object(
            self.v5, "evaluate_temporal", side_effect=evaluate
        ):
            for temporal in ("fixed", "lag"):
                self.v5.load_and_evaluate_temporal(args, temporal, set(), None, True, True, after)
        self.assertEqual(len(loads), 6)
        self.assertEqual(len(set(loads)), 6)
        self.assertTrue(all(ref() is None for ref in refs))

    def test_sources_are_released_when_consumer_fails(self):
        refs = []

        def load(path):
            source = TrackedDict(samples=[])
            refs.append(weakref.ref(source))
            return source

        args = SimpleNamespace(snapshot=Path("snapshot"), v5_dir=Path("v5"))
        with mock.patch.object(self.v5, "_load", side_effect=load), mock.patch.object(
            self.v5, "evaluate_temporal", return_value=({}, [], [])
        ):
            def fail(*args):
                raise ValueError("consumer failed")
            with self.assertRaisesRegex(ValueError, "consumer failed"):
                self.v5.load_and_evaluate_temporal(args, "fixed", set(), None, True, True, fail)
        gc.collect()
        self.assertTrue(all(ref() is None for ref in refs))

    def test_v6_standalone_loads_each_source_once_and_releases_it(self):
        refs, loads = [], []
        evaluations = []

        def evaluate(*args, **kwargs):
            # A Mock would itself retain benchmark arguments in call_args_list.
            evaluations.append(kwargs["profile_id"])
            return {}, []

        def load(path):
            self.assertTrue(all(ref() is None for ref in refs))
            source = TrackedDict(samples=[])
            refs.append(weakref.ref(source))
            loads.append(path.name)
            return source

        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            (root / "MANIFEST.json").write_text("{}")
            argv = ["v6", "--snapshot", temp, "--v5-dir", temp, "--output-dir", temp]
            for days in (30, 60, 90):
                argv += ["--profile-key", f"{self.v6.smooth.WINDOWED_VERSION_ID}/{self.v6.smooth.windowed_profile_id(days)}"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                self.v6, "load", side_effect=load
            ), mock.patch.object(self.v6, "evaluate_split", new=evaluate):
                self.assertEqual(self.v6.main(), 0)
                self.assertEqual(len(evaluations), 18)
            self.assertEqual(loads, ["biology-v5-fixed.json", "biology-v5-lag.json"])
            self.assertTrue(all(ref() is None for ref in refs))

    def test_finalizing_shared_v6_does_not_reload_or_reevaluate(self):
        profiles = self.v6._selected_profiles(set())
        precomputed = {(p["profile_id"], t): ([], {}) for p in profiles for t in ("fixed", "lag")}
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            (Path(temp) / "MANIFEST.json").write_text("{}")
            argv = ["v6", "--snapshot", temp, "--v5-dir", temp, "--output-dir", temp]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                self.v6, "load", side_effect=AssertionError("source reloaded")
            ), mock.patch.object(self.v6, "evaluate_split", side_effect=AssertionError("reevaluated")):
                self.assertEqual(self.v6.main(precomputed_results=precomputed), 0)

    def test_preparation_run_script_passes_shared_consumer(self):
        prepare = script("prepare-mushroom-ml-multiversion-inputs")
        received = []
        callback = object()
        with mock.patch.object(prepare.runpy, "run_path", return_value={
            "main": lambda **kwargs: received.append(kwargs)
        }):
            prepare.run_script(Path("evaluation.py"), [], main_kwargs={"after_temporal": callback})
        self.assertIs(received[0]["after_temporal"], callback)

    def test_joint_v5_v6_pipeline_reads_each_benchmark_once(self):
        loads, normalizations = [], []
        profiles = self.v6._selected_profiles({
            f"{self.v6.smooth.WINDOWED_VERSION_ID}/{self.v6.smooth.windowed_profile_id(days)}"
            for days in (30, 60, 90)
        })
        normalize = self.v5.holdout.eligible_samples

        def load(path):
            loads.append(path.name)
            return {"samples": [], "source": path.name}

        def normalized(benchmark):
            normalizations.append(benchmark["source"])
            return normalize(benchmark)

        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            (root / "MANIFEST.json").write_text("{}")
            output = root / "v6"
            output.mkdir()
            results = {}

            def after(temporal, benchmark):
                results.update(self.v6.evaluate_temporal(
                    benchmark, temporal=temporal, profiles=profiles,
                    output_dir=output, tuning_catalog=None,
                ))

            argv = ["v5", "--snapshot", temp, "--v5-dir", temp]
            for days in (30, 60, 90):
                argv += ["--profile-key", f"{self.v5.raw_weather.WINDOWED_VERSION_ID}/{self.v5.raw_weather.windowed_profile_id(days)}"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                self.v5, "_load", side_effect=load
            ), mock.patch.object(self.v5.holdout, "eligible_samples", side_effect=normalized), mock.patch.object(
                self.v5, "build_observation_altitude_v2_common_idw_benchmark", side_effect=lambda data: data
            ), mock.patch.object(self.v5.holdout, "evaluate_dataset", return_value=({}, [], [])), mock.patch.object(
                self.v6, "evaluate_split", return_value=({}, [])
            ):
                self.assertEqual(self.v5.main(after_temporal=after), 0)
            self.assertEqual(loads, ["biology-v3-fixed.json", "biology-v5-fixed.json", "biology-v3-lag.json", "biology-v5-lag.json"])
            self.assertEqual(normalizations, ["biology-v5-fixed.json"] * 2 + ["biology-v5-lag.json"] * 2)
            self.assertEqual(len(results), 6)
            argv = ["v6", "--snapshot", temp, "--v5-dir", temp, "--output-dir", str(output)]
            for profile in profiles:
                argv += ["--profile-key", f"{profile['version_id']}/{profile['profile_id']}"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                self.v6, "load", side_effect=AssertionError("shared source reloaded")
            ):
                self.assertEqual(self.v6.main(precomputed_results=results), 0)
            self.assertEqual(len(json.loads((output / "MANIFEST.json").read_text())["artifacts"]), 18)

    def test_v6_shares_normalization_and_matches_independent_evaluations(self):
        """Real small fits: source sharing must not change probabilities/reports."""
        rng = np.random.default_rng(42)
        profiles = self.v6._selected_profiles({
            f"{self.v6.smooth.WINDOWED_VERSION_ID}/{self.v6.smooth.windowed_profile_id(days)}"
            for days in (30, 60, 90)
        })
        profiles += self.v6._selected_profiles(set())  # Full 365-day contract too.
        columns = self.v6.smooth.raw_columns(include_phenology=True, include_horizon=True)
        # Include raw-only variables as well as full physical/state histories.
        columns = list(dict.fromkeys(columns + self.v6.smooth.raw_columns(
            include_phenology=True, include_horizon=True,
            channels=self.v6.raw_weather.RAW_CHANNELS, window_days=365,
        )))
        samples = []
        for species in ("a", "b"):
            for index in range(12):
                samples.append({
                    "sample_id": f"{species}-{index}",
                    "prediction_target": "favorable" if index % 2 else "unfavorable",
                    "predictive_features": dict(zip(columns, rng.normal(size=len(columns)))),
                    "metadata": {
                        "observation_id": f"{species}-{index}", "species_id": species,
                        "area_id": "area", "target_date": f"{2020 + index // 4}-09-{index % 4 + 1:02d}",
                        "temporal_contract_id": "lag_event_biology_v5_raw365_v2",
                        "horizon_days": 1, "validation_group_7d": f"{species}-{index}",
                        "validation_group_14d": f"{species}-{index}",
                    },
                })
        benchmark = {"samples": samples}
        original = copy.deepcopy(benchmark)
        expected = {}

        def frozen_config(*args, partial, **kwargs):
            return {"C": 0.1, "deviation_scale": 4.0 if partial else None}

        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()), mock.patch.object(
            self.v6, "select_joint_config", side_effect=frozen_config
        ):
            # Baseline: each profile has its own input and normalization.
            for profile in profiles:
                separate = copy.deepcopy(benchmark)
                reference = self.v6.holdout.eligible_samples(separate)
                for days in (7, 14, None):
                    train, test = (
                        self.v6.campaign_split(reference) if days is None
                        else self.v6.chronological_group_split(reference, group_days=days)
                    )
                    split = "campaign_area_year_70_30" if days is None else f"fruiting_groups_{days}d"
                    expected[(profile["profile_id"], split)] = self.v6.evaluate_split(
                        separate, train, test, split_id=split, group_days=days or 14,
                        version_id=profile["version_id"], profile_id=profile["profile_id"],
                        window_days=profile["window_days"],
                    )
            with mock.patch.object(
                self.v6.holdout, "eligible_samples", wraps=self.v6.holdout.eligible_samples
            ) as normalize:
                actual = self.v6.evaluate_temporal(
                    benchmark, temporal="lag", profiles=profiles,
                    output_dir=Path(temp), tuning_catalog=None,
                )
                self.assertEqual(normalize.call_count, 1)
            for profile in profiles:
                rows, artifacts = actual[(profile["profile_id"], "lag")]
                expected_rows = []
                for days in (7, 14, None):
                    split = "campaign_area_year_70_30" if days is None else f"fruiting_groups_{days}d"
                    report, split_rows = expected[(profile["profile_id"], split)]
                    expected_rows.extend(split_rows)
                    filename = (
                        f"sensitivity-{profile['profile_id']}-lag-campaign.json" if days is None
                        else f"comparison-{profile['profile_id']}-lag-groups{days}.json"
                    )
                    self.assertIn(filename, artifacts)
                    self.assertEqual(json.loads((Path(temp) / filename).read_text())["report"], report)
                self.assertEqual(rows, expected_rows)
        self.assertEqual(benchmark, original)


if __name__ == "__main__":
    unittest.main()
