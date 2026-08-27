import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "prepare-mushroom-ml-multiversion-inputs.py"
)


class MushroomMLMultiversionInputPreparationTests(unittest.TestCase):
    def test_script_bootstraps_repository_root_when_run_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--help"],
                cwd=temporary,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONNOUSERSITE": "1",
                },
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--source-snapshot-id", completed.stdout)

    def test_operational_v3_version_prepares_core_and_physical_inputs_only(self) -> None:
        spec = importlib.util.spec_from_file_location("prepare_multiversion_v3", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "prepared"
            calls = []

            def fake_run_script(path, arguments, **_kwargs):
                calls.append(Path(path).name)
                if "--output" in arguments:
                    destination = Path(arguments[arguments.index("--output") + 1])
                    destination.write_text(
                        json.dumps({"feature_set": {}, "samples": []}), encoding="utf-8"
                    )
                if Path(path).name == "evaluate-biology-v5-raw-benchmark.py":
                    evaluation_root = Path(arguments[arguments.index("--v5-dir") + 1])
                    (evaluation_root / "heldout-predictions.jsonl").write_text(
                        "", encoding="utf-8"
                    )

            argv = [
                str(SCRIPT), "--data-dir", str(root / "weather"),
                "--observations", str(root / "observations.json"),
                "--known-sites", str(root / "known-sites.json"),
                "--observation-features", str(root / "features.json"),
                "--stations-file", str(root / "stations.txt"),
                "--output-dir", str(output),
                "--source-snapshot-id", "sha256:" + "d" * 64,
                "--job-purpose", "operational",
                "--tuning-catalog", str(root / "tuning-catalog.json"),
                "--profile-key", "biology_v3/core",
                "--profile-key", "biology_v3/common_idw_plus_physical_state",
            ]
            workspace = mock.Mock()
            workspace.stats.return_value = {"mode": "test"}
            with mock.patch.object(module, "run_script", side_effect=fake_run_script), mock.patch.object(
                module.mushroom_ml_weather_workspace,
                "activate_operational_workspace",
                return_value=workspace,
            ), mock.patch.object(sys, "argv", argv):
                self.assertEqual(module.main(), 0)

            prepared = json.loads((output / "prepared-inputs.json").read_text())
            self.assertEqual(
                calls,
                [
                    "build-biology-v3-benchmark.py",
                    "build-biology-v3-benchmark.py",
                    "build-biology-v4-benchmark.py",
                    "build-biology-v4-benchmark.py",
                    "evaluate-biology-v5-raw-benchmark.py",
                ],
            )
            self.assertEqual(
                set(prepared["inputs"]),
                {
                    "v3_fixed", "v3_lag", "v4_fixed", "v4_lag",
                    "v2_v5_heldout", "v6_heldout",
                },
            )
            self.assertTrue((output / "v5").exists())
            self.assertTrue((output / "v6").exists())

    def test_operational_preparation_stops_after_v2_fixed_and_lag_sources(self) -> None:
        spec = importlib.util.spec_from_file_location("prepare_multiversion_inputs", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "prepared"
            calls = []

            def fake_run_script(_path, arguments, **_kwargs):
                calls.append(list(arguments))
                destination = Path(arguments[arguments.index("--output") + 1])
                destination.write_text(
                    json.dumps({"feature_set": {}, "samples": []}),
                    encoding="utf-8",
                )

            argv = [
                str(SCRIPT),
                "--data-dir", str(root / "weather"),
                "--observations", str(root / "observations.json"),
                "--known-sites", str(root / "known-sites.json"),
                "--observation-features", str(root / "features.json"),
                "--stations-file", str(root / "stations.txt"),
                "--output-dir", str(output),
                "--source-snapshot-id", "sha256:" + "a" * 64,
                "--job-purpose", "operational",
                "--tuning-catalog", str(root / "tuning-catalog.json"),
            ]
            workspace = mock.Mock()
            workspace.stats.return_value = {"mode": "test"}
            with mock.patch.object(module, "run_script", side_effect=fake_run_script), mock.patch.object(
                module.mushroom_ml_weather_workspace,
                "activate_operational_workspace",
                return_value=workspace,
            ), mock.patch.object(sys, "argv", argv):
                self.assertEqual(module.main(), 0)

            prepared = json.loads((output / "prepared-inputs.json").read_text())
            self.assertEqual(len(calls), 2)
            self.assertEqual(prepared["job_purpose"], "operational")
            self.assertEqual(
                set(prepared["inputs"]),
                {"v3_fixed", "v3_lag", "v2_v5_heldout", "v6_heldout"},
            )
            self.assertTrue((output / "v5").exists())
            self.assertTrue((output / "v6").exists())

    def test_v3_benchmark_prepares_and_evaluates_only_selected_profile(self) -> None:
        spec = importlib.util.spec_from_file_location("prepare_multiversion_inputs", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "prepared"
            calls = []

            def fake_run_script(path, arguments, **_kwargs):
                calls.append((Path(path).name, list(arguments)))
                if "--output" in arguments:
                    destination = Path(arguments[arguments.index("--output") + 1])
                    destination.write_text(
                        json.dumps({"feature_set": {}, "samples": []}),
                        encoding="utf-8",
                    )
                if Path(path).name == "evaluate-biology-v5-raw-benchmark.py":
                    evaluation_root = Path(arguments[arguments.index("--v5-dir") + 1])
                    (evaluation_root / "heldout-predictions.jsonl").write_text(
                        "", encoding="utf-8"
                    )

            argv = [
                str(SCRIPT),
                "--data-dir", str(root / "weather"),
                "--observations", str(root / "observations.json"),
                "--known-sites", str(root / "known-sites.json"),
                "--observation-features", str(root / "features.json"),
                "--stations-file", str(root / "stations.txt"),
                "--output-dir", str(output),
                "--source-snapshot-id", "sha256:" + "b" * 64,
                "--job-purpose", "benchmark",
                "--profile-key", "biology_v3/core",
            ]
            with mock.patch.object(module, "run_script", side_effect=fake_run_script), mock.patch.object(
                sys, "argv", argv
            ):
                self.assertEqual(module.main(), 0)

            prepared = json.loads((output / "prepared-inputs.json").read_text())
            self.assertEqual(
                [name for name, _arguments in calls],
                [
                    "build-biology-v3-benchmark.py",
                    "build-biology-v3-benchmark.py",
                    "evaluate-biology-v5-raw-benchmark.py",
                ],
            )
            self.assertEqual(prepared["profile_keys"], ["biology_v3/core"])
            self.assertEqual(
                set(prepared["inputs"]),
                {"v3_fixed", "v3_lag", "v2_v5_heldout", "v6_heldout"},
            )
            self.assertIn("biology_v3/core", calls[-1][1])
            self.assertFalse((output / "snapshot/biology-v4-fixed.json").exists())
            self.assertFalse((output / "v5/biology-v5-fixed.json").exists())

    def test_v3_physical_prepares_v4_sources_without_v5_or_v6(self) -> None:
        spec = importlib.util.spec_from_file_location("prepare_multiversion_inputs", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "prepared"
            calls = []

            def fake_run_script(path, arguments, **_kwargs):
                calls.append((Path(path).name, list(arguments)))
                if "--output" in arguments:
                    destination = Path(arguments[arguments.index("--output") + 1])
                    destination.write_text(
                        json.dumps({"feature_set": {}, "samples": []}),
                        encoding="utf-8",
                    )
                if Path(path).name == "evaluate-biology-v5-raw-benchmark.py":
                    evaluation_root = Path(arguments[arguments.index("--v5-dir") + 1])
                    (evaluation_root / "heldout-predictions.jsonl").write_text(
                        "", encoding="utf-8"
                    )

            argv = [
                str(SCRIPT),
                "--data-dir", str(root / "weather"),
                "--observations", str(root / "observations.json"),
                "--known-sites", str(root / "known-sites.json"),
                "--observation-features", str(root / "features.json"),
                "--stations-file", str(root / "stations.txt"),
                "--output-dir", str(output),
                "--source-snapshot-id", "sha256:" + "c" * 64,
                "--job-purpose", "benchmark",
                "--profile-key", "biology_v3/common_idw_plus_physical_state",
            ]
            with mock.patch.object(module, "run_script", side_effect=fake_run_script), mock.patch.object(
                sys, "argv", argv
            ):
                self.assertEqual(module.main(), 0)

            self.assertEqual(
                [name for name, _arguments in calls],
                [
                    "build-biology-v3-benchmark.py",
                    "build-biology-v3-benchmark.py",
                    "build-biology-v4-benchmark.py",
                    "build-biology-v4-benchmark.py",
                    "evaluate-biology-v5-raw-benchmark.py",
                ],
            )
            prepared = json.loads((output / "prepared-inputs.json").read_text())
            self.assertEqual(
                prepared["profile_keys"],
                ["biology_v3/common_idw_plus_physical_state"],
            )
            self.assertIn("v4_fixed", prepared["inputs"])
            self.assertIn("v4_lag", prepared["inputs"])
            self.assertFalse((output / "v5/biology-v5-fixed.json").exists())
            self.assertFalse((output / "v6/biology-v6-fixed.json").exists())


if __name__ == "__main__":
    unittest.main()
