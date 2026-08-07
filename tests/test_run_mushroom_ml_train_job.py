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

from rainmapper_core import mushroom_ml_trainer


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
                    }
                ),
                encoding="utf-8",
            )
            features.write_text("{}", encoding="utf-8")
            known_sites.write_text("{}", encoding="utf-8")

            def fake_run(*, models_dir: Path, report_path: Path, **_kwargs):
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
                },
            )
            for logical_path, row in by_path.items():
                content = (output / logical_path).read_bytes()
                self.assertEqual(row["size_bytes"], len(content))
                self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())


if __name__ == "__main__":
    unittest.main()
