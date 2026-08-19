import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rainmapper_core import mushroom_ml_benchmark_reports as reports


class MushroomMLBenchmarkReportsTests(TestCase):
    def _write_report(self, root: Path) -> dict[str, object]:
        source = root / "source.jsonl"
        rows = [
            {
                "version_id": "biology_v3",
                "profile_id": "core",
                "species_id": species_id,
                "temporal_contract_id": "fixed_gap_7d_biology_v3",
                "horizon_days": 7,
                "y_true": index % 2,
                "estimator_probabilities": {"logistic_regression_reduced_v1": 0.2},
            }
            for index, species_id in enumerate(("species_a", "species_b"))
        ]
        source.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        empty = root / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        plan = {
            "batch_id": "benchmark-a",
            "snapshot_id": "sha256:" + "a" * 64,
            "version_ids": ["biology_v3"],
            "profile_keys": ["biology_v3/core"],
            "species_ids": ["species_a", "species_b"],
            "fit_count": 1,
            "fits": [],
        }
        fit_results = [
            {
                "artifact_ref": {
                    "version_id": "biology_v3",
                    "profile_id": "core",
                    "temporal_contract_id": "fixed_gap_7d_biology_v3",
                    "species_id": "species_a",
                    "estimator_id": "logistic_regression_reduced_v1",
                },
                "status": "complete",
                "duration_seconds": 1.25,
            }
        ]
        quality = {
            "entries": [
                {
                    "version_id": "biology_v3",
                    "profile_id": "core",
                    "temporal_family": "fixed",
                    "horizon_days": 7,
                    "species_id": species_id,
                    "estimator_id": "logistic_regression_reduced_v1",
                    "brier_score": 0.1 + index,
                }
                for index, species_id in enumerate(("species_a", "species_b"))
            ]
        }
        return reports.write_report(
            root,
            job_id="worker_job_report",
            training_plan=plan,
            selected_profiles=[
                {
                    "profile_key": "biology_v3/core",
                    "version_id": "biology_v3",
                    "profile_id": "core",
                    "profile_name": "Core",
                }
            ],
            quality_catalog=quality,
            fit_results=fit_results,
            failed_fits=[],
            v2_v5_predictions_path=source,
            v6_predictions_path=empty,
            created_at="2026-08-18T12:00:00+00:00",
        )

    def test_report_persists_selection_rows_metrics_and_durations_without_average(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self._write_report(root)
            report = reports.validate_report(result["report"], root=root)

        self.assertEqual(report["selection"]["profile_keys"], ["biology_v3/core"])
        self.assertEqual(report["summary"]["holdout_prediction_count"], 2)
        self.assertEqual(
            {row["species_id"] for row in report["metrics"]},
            {"species_a", "species_b"},
        )
        self.assertEqual(report["duration_summary"]["total_fit_seconds"], 1.25)
        self.assertTrue(report["species_metrics_are_never_averaged"])
        self.assertFalse(report["winner_declared"])

    def test_archive_history_loads_valid_reports_and_rejects_tampering(self) -> None:
        with TemporaryDirectory() as temporary:
            models_root = Path(temporary) / "models"
            archive = models_root / "benchmarks" / "benchmark-a"
            archive.mkdir(parents=True)
            self._write_report(archive)

            self.assertEqual(reports.list_reports(models_root)[0]["batch_id"], "benchmark-a")
            self.assertEqual(reports.load_report(models_root, "benchmark-a")["batch_id"], "benchmark-a")
            (archive / reports.PREDICTIONS_NAME).write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integrity"):
                reports.load_report(models_root, "benchmark-a")

