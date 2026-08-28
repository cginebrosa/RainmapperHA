"""Contract tests for the external worker ML training command."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_ml_experiment_trainer, mushroom_ml_trainer
from rainmapper_core import mushroom_operational_training_scope


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT_DIR / "scripts" / "run-mushroom-ml-train-job.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("run_mushroom_ml_train_job_for_tests", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load run-mushroom-ml-train-job.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunMushroomMLTrainJobTests(unittest.TestCase):
    def test_sealed_scope_rejects_different_feature_inputs_before_training(self) -> None:
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            features_payload = {
                "rows": [
                    {
                        "species_id": "boletus_aereus",
                        "observed_at": f"2026-08-{day:02d}",
                        "micro_area_id": "ma-1",
                        "validation_status": "valid",
                        "calibration_use": "include",
                        "prediction_target": "favorable" if day == 1 else "unfavorable",
                    }
                    for day in range(1, 11)
                ]
            }
            known_sites_payload = {
                "micro_areas": [{"micro_area_id": "ma-1", "area_id": "area-1"}]
            }
            scope = mushroom_operational_training_scope.build_scope(
                features_payload, known_sites_payload
            )
            features_payload["rows"][0]["observed_at"] = "2026-07-31"
            job_spec = root / "job_spec.json"
            features = root / "features.json"
            known_sites = root / "known_sites.json"
            job_spec.write_text(
                json.dumps(
                    {
                        "job_id": "worker_job_scopemismatch",
                        "species_ids": scope["admitted_species_ids"],
                        "min_rows": scope["min_episodes"],
                        "cv_folds": 3,
                        "operational_scope": scope,
                    }
                ),
                encoding="utf-8",
            )
            features.write_text(json.dumps(features_payload), encoding="utf-8")
            known_sites.write_text(json.dumps(known_sites_payload), encoding="utf-8")
            argv = [
                str(SCRIPT_PATH),
                "--job-spec", str(job_spec),
                "--features", str(features),
                "--known-sites", str(known_sites),
                "--output-dir", str(root / "output"),
                "--quiet",
            ]
            with mock.patch.object(sys, "argv", argv), self.assertRaisesRegex(
                ValueError, "inputs do not match"
            ):
                module.main()

    def test_result_manifest_declares_report_and_model(self) -> None:
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job_spec = root / "job_spec.json"
            features = root / "features.json"
            known_sites = root / "known_sites.json"
            output = root / "output"
            job_spec.write_text(
                json.dumps(
                    {
                        "job_id": "worker_job_mltrain1234",
                        "species_ids": ["boletus_aereus"],
                        "min_rows": 10,
                        "cv_folds": 3,
                    }
                ),
                encoding="utf-8",
            )
            features.write_text("{}", encoding="utf-8")
            known_sites.write_text("{}", encoding="utf-8")
            captured_run_kwargs = {}

            def fake_run(*, models_dir: Path, report_path: Path, **kwargs):
                captured_run_kwargs.update(kwargs)
                report = {
                    "schema_version": "0.1",
                    "kind": "mushroom_ml_v0_report",
                    "species_results": [
                        {"species_id": "boletus_aereus", "skipped": False}
                    ],
                }
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(report), encoding="utf-8")
                models_dir.mkdir(parents=True, exist_ok=True)
                (models_dir / "mushroom_ml_v0_boletus_aereus.joblib").write_bytes(
                    b"joblib-model"
                )
                return report

            def fake_shadow_run(*, models_dir: Path, report_path: Path, **kwargs):
                model_paths = []
                feature_sets = []
                for feature_set_id in mushroom_ml_experiment_trainer.DEFAULT_FEATURE_SET_IDS:
                    model_path = models_dir / (
                        f"mushroom_ml_experiment_{feature_set_id}_boletus_aereus.joblib"
                    )
                    model_path.write_bytes(f"shadow-{feature_set_id}".encode())
                    model_paths.append(model_path)
                    feature_sets.append(
                        {
                            "feature_set_id": feature_set_id,
                            "species_results": [
                                {
                                    "species_id": "boletus_aereus",
                                    "model_path": str(model_path),
                                }
                            ],
                        }
                    )
                report = {
                    "schema_version": "1.0",
                    "kind": "mushroom_ml_experiment_report",
                    "feature_sets": feature_sets,
                }
                report_path.write_text(json.dumps(report), encoding="utf-8")
                return report

            argv = [
                str(SCRIPT_PATH),
                "--job-spec",
                str(job_spec),
                "--features",
                str(features),
                "--known-sites",
                str(known_sites),
                "--output-dir",
                str(output),
                "--quiet",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(mushroom_ml_trainer, "run", side_effect=fake_run),
                mock.patch.object(
                    mushroom_ml_experiment_trainer,
                    "run",
                    side_effect=fake_shadow_run,
                ),
                redirect_stdout(io.StringIO()),
            ):
                module.main()

            manifest = json.loads((output / "ml_train_result.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "0.2")
            by_path = {row["path"]: row for row in manifest["artifacts"]}
            self.assertEqual(
                set(by_path),
                {
                    "ml_train_report.json",
                    "ml_models/mushroom_ml_v0_boletus_aereus.joblib",
                    "ml_models/mushroom_ml_experiment_fixed_gap_7d_altitude_v2_boletus_aereus.joblib",
                    "ml_models/mushroom_ml_experiment_lag_event_altitude_v2_boletus_aereus.joblib",
                },
            )
            self.assertEqual(
                manifest["shadow_feature_set_ids"],
                list(mushroom_ml_experiment_trainer.DEFAULT_FEATURE_SET_IDS),
            )
            for logical_path, row in by_path.items():
                content = (output / logical_path).read_bytes()
                self.assertEqual(row["size_bytes"], len(content))
                self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())

            self.assertEqual(captured_run_kwargs["min_rows"], 10)
            self.assertEqual(captured_run_kwargs["cv_folds"], 3)
            merged_report = json.loads(
                (output / "ml_train_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                merged_report["shadow_experiments"]["kind"],
                "mushroom_ml_experiment_report",
            )


if __name__ == "__main__":
    unittest.main()
