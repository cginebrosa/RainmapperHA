from __future__ import annotations

import copy
from pathlib import Path
from unittest import TestCase

from rainmapper_core import mushroom_soilgrids
from rainmapper_core import mushroom_soilgrids_reconciler as reconciler


def geometry(offset: float = 0.0) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [offset, 0.0],
                [offset + 0.01, 0.0],
                [offset, 0.01],
                [offset, 0.0],
            ]
        ],
    }


def context(value: dict, status: str = "complete") -> dict:
    return {
        "contract_id": mushroom_soilgrids.CONTEXT_CONTRACT_ID,
        "geometry_hash": mushroom_soilgrids.geometry_sha256(value),
        "status": status,
        "source": {
            "source_id": mushroom_soilgrids.SOURCE_ID,
            "source_version": mushroom_soilgrids.SOURCE_VERSION,
            "cache_contract_id": mushroom_soilgrids.CACHE_CONTRACT_ID,
        },
    }


class MushroomSoilGridsReconcilerTests(TestCase):
    def payload(self) -> dict:
        first = geometry()
        second = geometry(1.0)
        return {
            "schema_version": "1.0",
            "areas": [],
            "micro_areas": [
                {
                    "micro_area_id": "current",
                    "area_id": "a",
                    "name": "Current",
                    "geometry": first,
                    "derived_context": {"soilgrids_water": context(first)},
                    "archived": False,
                },
                {
                    "micro_area_id": "pending",
                    "area_id": "a",
                    "name": "Pending",
                    "geometry": second,
                    "derived_context": {
                        "soilgrids_water": mushroom_soilgrids.pending_context(
                            second,
                            tile_ids=["x0_y0"],
                            reasons=["missing_cache_assets"],
                        )
                    },
                    "archived": False,
                },
            ],
        }

    def test_repairs_only_non_current_contexts_and_reports_io(self) -> None:
        payload = self.payload()
        calls: list[dict] = []
        progress_events: list[dict] = []

        def resolver(_root: Path, value: dict, **kwargs: object) -> dict:
            calls.append(value)
            telemetry = kwargs["telemetry"]
            assert isinstance(telemetry, dict)
            telemetry.update(
                {
                    "downloaded": 1,
                    "reused": 53,
                    "requests": 1,
                    "downloaded_bytes": 2048,
                    "files_promoted": 2,
                    "asset_hashes_checked": 108,
                    "manifest_writes": 1,
                    "fsyncs": 2,
                }
            )
            return context(value)

        candidate, report = reconciler.reconcile_payload(
            payload,
            Path("/cache"),
            resolver=resolver,
            progress_callback=progress_events.append,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(report["current_micro_areas"], 1)
        self.assertEqual(report["attempted_micro_areas"], 1)
        self.assertEqual(report["repaired_micro_areas"], 1)
        self.assertEqual(report["requests"], 1)
        self.assertEqual(report["downloaded_bytes"], 2048)
        self.assertEqual(report["health"]["current"], 2)
        self.assertEqual(report["warnings"], [])
        self.assertGreaterEqual(report["duration_ms"], 0)
        self.assertEqual(
            payload["micro_areas"][1]["derived_context"]["soilgrids_water"]["status"],
            "pending",
        )
        self.assertEqual(
            candidate["micro_areas"][1]["derived_context"]["soilgrids_water"]["status"],
            "complete",
        )
        self.assertTrue(progress_events)
        self.assertNotIn("derived_context", progress_events[0]["current_micro_area"])

    def test_local_failure_is_reported_without_aborting_other_microareas(self) -> None:
        payload = self.payload()
        before = copy.deepcopy(payload)

        def resolver(_root: Path, value: dict, **_kwargs: object) -> dict:
            pending = mushroom_soilgrids.pending_context(
                value,
                tile_ids=["x0_y0"],
                reasons=["soilgrids_resolution_error"],
            )
            pending["quality"].update(
                {"error_type": "TimeoutError", "error": "temporary timeout"}
            )
            return pending

        candidate, report = reconciler.reconcile_payload(
            payload,
            Path("/cache"),
            resolver=resolver,
        )

        self.assertEqual(report["current_micro_areas"], 1)
        self.assertEqual(report["repaired_micro_areas"], 0)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertEqual(report["warnings"][0]["error_type"], "TimeoutError")
        self.assertEqual(report["health"]["pending"], 1)
        self.assertEqual(payload, before)
        self.assertEqual(
            candidate["micro_areas"][0]["derived_context"],
            before["micro_areas"][0]["derived_context"],
        )

    def test_resolver_exception_keeps_pending_context_and_finishes_phase(self) -> None:
        payload = self.payload()

        def resolver(_root: Path, _value: dict, **kwargs: object) -> dict:
            telemetry = kwargs["telemetry"]
            assert isinstance(telemetry, dict)
            telemetry.update({"requests": 1, "downloaded_bytes": 17})
            raise mushroom_soilgrids.SoilGridsDownloadError("network unavailable")

        candidate, report = reconciler.reconcile_payload(
            payload,
            Path("/cache"),
            resolver=resolver,
        )

        self.assertEqual(report["processed_micro_areas"], 2)
        self.assertEqual(report["repaired_micro_areas"], 0)
        self.assertEqual(report["requests"], 1)
        self.assertEqual(report["downloaded_bytes"], 17)
        self.assertEqual(report["warnings"][0]["status"], "resolution_error")
        self.assertEqual(
            candidate["micro_areas"][1]["derived_context"]["soilgrids_water"]["status"],
            "pending",
        )

    def test_current_partial_context_remains_visible_as_not_model_complete(self) -> None:
        payload = self.payload()
        value = payload["micro_areas"][0]["geometry"]
        payload["micro_areas"][0]["derived_context"]["soilgrids_water"] = context(
            value, status="partial"
        )

        health = reconciler.inspect_payload(payload)

        self.assertEqual(health["current"], 1)
        self.assertEqual(health["partial"], 1)
        self.assertEqual(
            {row["micro_area_id"] for row in health["unresolved"]},
            {"current", "pending"},
        )


if __name__ == "__main__":
    from unittest import main

    main()
