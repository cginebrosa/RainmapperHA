from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "rainmapper-app" / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import mushroom_workers_ui  # noqa: E402


class MushroomWorkersPromotionUITests(unittest.TestCase):
    def test_benchmark_history_keeps_all_reports_in_scroll_container(self) -> None:
        reports = [
            {
                "batch_id": f"benchmark-{index}",
                "created_at": f"2026-08-19T10:0{index}:00+02:00",
                "selection": {
                    "profiles": [
                        {
                            "profile_key": "biology_v4/climatic_balance",
                            "profile_name": "Biology V4 climatic balance",
                        }
                    ]
                },
                "summary": {
                    "planned_fit_count": 108,
                    "successful_fit_count": 108,
                },
            }
            for index in range(6)
        ]

        rendered = mushroom_workers_ui.render_benchmark_history(reports)

        self.assertIn(
            'class="benchmark-history benchmark-history-scroll" data-preserve-refresh-scroll',
            rendered,
        )
        self.assertEqual(rendered.count('class="benchmark-history-row"'), 6)
        self.assertIn("benchmark-0", rendered)
        self.assertIn("benchmark-5", rendered)

    def test_complete_v3_report_offers_candidate_without_metric_gate(self) -> None:
        report = {
            "batch_id": "benchmark-v3",
            "snapshot_id": "sha256:" + "a" * 64,
            "selection": {
                "profiles": [
                    {"profile_id": "core", "profile_name": "Biology V3 core"},
                    {
                        "profile_id": "common_idw_plus_physical_state",
                        "profile_name": "Biology V3+ physical",
                    },
                ]
            },
            "summary": {"planned_fit_count": 2, "successful_fit_count": 2},
            "metrics": [],
        }

        rendered = mushroom_workers_ui.render_benchmark_report(
            report,
            promotion_versions=[
                {
                    "version_id": "biology_v3",
                    "version_name": "Biology V3",
                    "profile_keys": [
                        "biology_v3/core",
                        "biology_v3/common_idw_plus_physical_state",
                    ],
                }
            ],
        )

        self.assertIn('value="prepare_version_candidate"', rendered)
        self.assertIn('value="biology_v3"', rendered)
        self.assertIn('value="benchmark-v3"', rendered)

    def test_ready_candidate_requires_separate_explicit_promotion(self) -> None:
        rendered = mushroom_workers_ui.render_recent_jobs(
            [
                {
                    "job_id": "candidate-job",
                    "job_type": "local_ml_operational_candidate",
                    "job_purpose": "operational_candidate",
                    "status": "complete",
                    "result": {"candidate_id": "candidate-v3"},
                    "created_at": "2026-08-19T10:00:00+02:00",
                }
            ],
            [],
        )

        self.assertIn('value="promote_version_candidate"', rendered)
        self.assertIn('value="candidate-job"', rendered)

    def test_promoted_candidate_no_longer_offers_activation(self) -> None:
        rendered = mushroom_workers_ui.render_recent_jobs(
            [
                {
                    "job_id": "promotion-job",
                    "job_type": "local_ml_version_promotion",
                    "status": "complete",
                    "result": {
                        "candidate_id": "candidate-v3",
                        "rollback_available": True,
                    },
                },
                {
                    "job_id": "candidate-job",
                    "job_type": "local_ml_operational_candidate",
                    "status": "complete",
                    "result": {"candidate_id": "candidate-v3"},
                },
            ],
            [],
        )

        self.assertNotIn('value="promote_version_candidate"', rendered)
        self.assertIn('value="rollback_version_promotion"', rendered)


if __name__ == "__main__":
    unittest.main()
