from __future__ import annotations

import copy
import io
import json
import os
import sqlite3
import tempfile
import unittest
import zlib
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from rainmapper_core import mushroom_ml_multiversion_comparison
from rainmapper_core.mushroom_predictor_precompute import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactIdentity,
    ArtifactReader,
    BasePredictionRow,
    CoverageCell,
    OperationalMemberKey,
    OperationalMemberRow,
    PrecomputeArtifactError,
    PrecomputedResponse,
    RuntimeVersionIdentity,
    build_weekly_artifact,
    lookup_artifact,
    lookup_active_artifact,
    plan_artifact_identity,
    resolve_with_fallback,
    scientific_response_payload,
    validate_artifact,
    write_artifact,
)
from rainmapper_core.mushroom_predictor_service import (
    REQUEST_KIND,
    RESPONSE_KIND,
    SCHEMA_VERSION,
)
from rainmapper_core.mushroom_predictor_precompute_control import (
    activate_worker_copy,
    advance_desired_state,
    cancel_desired_state,
    load_desired_state,
    publish_received_artifact,
)


class PredictorPrecomputeArtifactTests(unittest.TestCase):
    issue_date = date(2026, 8, 30)
    runtime_a = "sha256:" + "a" * 64
    runtime_b = "sha256:" + "b" * 64

    def member_key(self, horizon_days: int) -> OperationalMemberKey:
        return OperationalMemberKey.create(
            version_id="biology_v4",
            temporal_contract_id="fixed",
            profile_id="extended_weather",
            estimator_id="random_forest",
            horizon_days=horizon_days,
        )

    def identity(self, *, runtime: str | None = None) -> ArtifactIdentity:
        return ArtifactIdentity.create(
            runtime_fingerprint=runtime or self.runtime_a,
            issue_date=self.issue_date,
            trained_species_ids=["boletus_edulis"],
            installed_versions=[
                RuntimeVersionIdentity.create(
                    version_id="biology_v4",
                    generation_id="generation-v4",
                    profile_ids=["extended_weather"],
                )
            ],
            expected_counts={
                "species": 1,
                "areas": 1,
                "days": 7,
                "versions": 1,
                "members": 7,
            },
        )

    def request(self, **changes: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "kind": REQUEST_KIND,
            "view": "query",
            "species_id": "boletus_edulis",
            "area_id": "montseny",
            "target_date": self.issue_date.isoformat(),
            "filter_mode": "",
            "compare_models": False,
            "multiversion_selection": [],
            "issue_date": self.issue_date.isoformat(),
            "trained_species_ids": ["boletus_edulis"],
        }
        payload.update(changes)
        return payload

    def prediction(self, day: date) -> dict[str, object]:
        return {
            "species_id": "boletus_edulis",
            "area_id": "montseny",
            "target_date": day.isoformat(),
            "lr_probability": 0.61,
            "rf_probability": 0.72,
            "ensemble_probability": 0.68,
            "label": "favorable",
            "weather_station_code": "station",
            "weather_station_distance_km": 3.2,
            "weather_coverage_days": 90,
            "feature_gaps": [],
            "features_used": {"rain_7d_mm": 14.0},
            "season_phase": "in_season",
        }

    def fixture(self, identity: ArtifactIdentity | None = None):
        identity = identity or self.identity()
        coverage = []
        predictions = []
        members = []
        prediction_map = {}
        comparison_map = {}
        for offset in range(7):
            day = self.issue_date + timedelta(days=offset)
            member = self.member_key(offset + 1)
            coverage.append(
                CoverageCell.create(
                    species_id="boletus_edulis",
                    area_id="montseny",
                    target_date=day,
                    has_base_prediction=True,
                    member_keys=[member],
                )
            )
            prediction = self.prediction(day)
            predictions.append(
                BasePredictionRow("boletus_edulis", "montseny", day.isoformat(), prediction)
            )
            member_payload = {
                "probability": 0.74,
                "interpretation": {"verdict": "favorable"},
            }
            members.append(
                OperationalMemberRow(
                    "boletus_edulis", "montseny", day.isoformat(), member, member_payload
                )
            )
            prediction_map[day.isoformat()] = prediction
            comparison_map[day.isoformat()] = member_payload
        request = self.request()
        response = {
            "schema_version": SCHEMA_VERSION,
            "kind": RESPONSE_KIND,
            "runtime_fingerprint": identity.runtime_fingerprint,
            "request": request,
            "data": {
                "species": {
                    "boletus_edulis": {
                        "areas": ["montseny"],
                        "predictions": {"montseny": prediction_map},
                        "model_comparisons": {"montseny": comparison_map},
                    }
                },
                "model_catalog": {"preferred_version_id": "biology_v4"},
            },
            "metrics": {"backend_seconds": 12.4, "response_cache_status": "miss"},
        }
        stored = PrecomputedResponse(request, response, tuple(coverage))
        return identity, coverage, predictions, members, stored

    def write_fixture(self, path: Path, identity: ArtifactIdentity | None = None):
        identity, coverage, predictions, members, stored = self.fixture(identity)
        manifest = write_artifact(
            path,
            identity=identity,
            coverage=coverage,
            base_predictions=predictions,
            operational_members=members,
            responses=[stored],
            diagnostics={"units": {"completed": 7, "total": 7}},
        )
        return identity, stored, manifest

    def test_identity_is_canonical_and_excludes_volatile_telemetry(self) -> None:
        first = self.identity()
        second = ArtifactIdentity.create(
            runtime_fingerprint=self.runtime_a,
            issue_date="2026-08-30",
            trained_species_ids=["boletus_edulis", "boletus_edulis"],
            installed_versions=list(reversed(first.installed_versions)),
            expected_counts=dict(reversed(first.expected_counts)),
        )

        self.assertEqual(first.artifact_id, second.artifact_id)
        self.assertEqual(first.coverage_end, "2026-09-05")

    def test_writer_reader_round_trip_preserves_canonical_response(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, manifest = self.write_fixture(target)

            validated = validate_artifact(
                target,
                expected_identity=identity,
                expected_file_sha256=manifest.file_sha256,
            )
            lookup = lookup_artifact(target, identity=identity, request=stored.request)

        self.assertTrue(lookup.hit)
        self.assertEqual(lookup.reason, None)
        self.assertEqual(lookup.artifact_id, identity.artifact_id)
        self.assertEqual(lookup.response, stored.response)
        self.assertEqual(validated.file_sha256, manifest.file_sha256)
        self.assertEqual(validated.table_counts["coverage"], 7)
        self.assertEqual(validated.table_counts["base_predictions"], 7)
        self.assertEqual(validated.table_counts["operational_members"], 7)

    def test_all_areas_query_reuses_canonical_preferred_response(self) -> None:
        identity, coverage, predictions, members, stored = self.fixture()
        canonical_request = self.request(area_id="")
        canonical_response = copy.deepcopy(stored.response)
        canonical_response["request"] = canonical_request
        canonical_response["data"]["species"]["boletus_edulis"] = {
            "areas": ["montseny"],
            "rankings": {
                self.issue_date.isoformat(): [self.prediction(self.issue_date)]
            },
            "model_comparisons": {
                "montseny": {
                    self.issue_date.isoformat(): {"available": True}
                }
            },
        }
        requested = {
            **canonical_request,
            "compare_models": True,
            "multiversion_selection": [self.member_key(1).as_dict()],
        }
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            write_artifact(
                target,
                identity=identity,
                coverage=coverage,
                base_predictions=predictions,
                operational_members=members,
                responses=[
                    PrecomputedResponse(
                        canonical_request,
                        canonical_response,
                        tuple(coverage),
                    )
                ],
            )
            lookup = lookup_artifact(target, identity=identity, request=requested)

        self.assertTrue(lookup.hit, lookup.reason)
        self.assertEqual(lookup.response["request"], requested)
        self.assertEqual(
            lookup.response["data"], canonical_response["data"]
        )

    def test_equivalence_ignores_only_execution_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            live = mock.Mock(return_value={**stored.response, "metrics": {"backend_seconds": 31.0}})

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=stored.request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "precompute")
        self.assertEqual(
            scientific_response_payload(resolved.response),
            scientific_response_payload(live.return_value),
        )
        live.assert_not_called()

    def test_missing_artifact_falls_back_to_complete_live_response(self) -> None:
        identity, _coverage, _predictions, _members, stored = self.fixture()
        live = mock.Mock(return_value=stored.response)
        missing = Path(tempfile.gettempdir()) / "rainmapper-does-not-exist.sqlite"

        resolved = resolve_with_fallback(
            missing,
            identity=identity,
            request=stored.request,
            live_predictor=live,
        )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "artifact_missing")
        self.assertEqual(resolved.response, stored.response)
        live.assert_called_once_with(stored.request)

    def test_history_view_always_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            request = self.request(view="history")
            live_response = {**stored.response, "request": request}
            live = mock.Mock(return_value=live_response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "view_not_precomputed")
        live.assert_called_once_with(request)

    def test_date_outside_window_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            request = self.request(target_date="2026-09-06")
            live_response = {**stored.response, "request": request}
            live = mock.Mock(return_value=live_response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "outside_coverage")
        live.assert_called_once_with(request)

    def test_partial_coverage_falls_back_without_mixing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            connection = sqlite3.connect(target)
            with connection:
                connection.execute(
                    "DELETE FROM base_predictions WHERE target_date=?",
                    ((self.issue_date + timedelta(days=3)).isoformat(),),
                )
            connection.close()
            live = mock.Mock(return_value=stored.response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=stored.request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "coverage_partial")
        self.assertEqual(resolved.response, stored.response)
        live.assert_called_once()

    def test_unrepresented_model_selection_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            request = self.request(
                compare_models=True,
                multiversion_selection=[self.member_key(1).as_dict()],
            )
            live_response = {**stored.response, "request": request}
            live = mock.Mock(return_value=live_response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "selection_not_precomputed")

    def test_reader_composes_arbitrary_represented_multiversion_subset(self) -> None:
        versions = ("biology_v4", "biology_v6_windowed_smooth_hierarchical")
        identity = ArtifactIdentity.create(
            runtime_fingerprint=self.runtime_a,
            issue_date=self.issue_date,
            trained_species_ids=["boletus_edulis"],
            installed_versions=[
                RuntimeVersionIdentity.create(
                    version_id=version_id,
                    generation_id=f"generation-{version_id}",
                    profile_ids=["extended_weather"],
                )
                for version_id in versions
            ],
            expected_counts={
                "species": 1,
                "areas": 1,
                "days": 7,
                "versions": 2,
                "members": 14,
            },
        )
        coverage = []
        predictions = []
        members = []
        comparisons = {}
        first_day_selections = []
        required = []
        for offset in range(7):
            target = self.issue_date + timedelta(days=offset)
            target_text = target.isoformat()
            keys = []
            payloads = []
            for version_index, version_id in enumerate(versions):
                key = OperationalMemberKey.create(
                    version_id=version_id,
                    temporal_contract_id=f"lag_event_{version_id}",
                    profile_id="extended_weather",
                    estimator_id="random_forest",
                    horizon_days=offset + 1,
                )
                probability = 0.62 + version_index * 0.08
                payload = {
                    "model_ref": key.as_dict(),
                    "available": True,
                    "prediction": {
                        "probability": probability,
                        "label": "favorable",
                        "applicability": {"status": "within_observed_range"},
                        "artifact_ref": {
                            "batch_id": "generation-batch",
                            "version_id": version_id,
                        },
                    },
                    "evaluation": {
                        "brier_score": 0.18,
                        "prevalence_brier_score": 0.25,
                        "brier_delta_vs_prevalence": 0.07,
                        "roc_auc": 0.75,
                        "n_test": 60,
                        "test_positive_count": 20,
                        "test_negative_count": 40,
                    },
                    "features_used": {
                        "significant_rain_found_90d": 1.0,
                        "days_since_significant_rain_at_target": 9.0,
                    },
                }
                keys.append(key)
                payloads.append(payload)
                members.append(
                    OperationalMemberRow(
                        "boletus_edulis", "montseny", target_text, key, payload
                    )
                )
                if offset == 0:
                    first_day_selections.append(key.as_dict())
            cell = CoverageCell.create(
                species_id="boletus_edulis",
                area_id="montseny",
                target_date=target,
                has_base_prediction=True,
                member_keys=keys,
            )
            coverage.append(cell)
            required.append(cell)
            predictions.append(
                BasePredictionRow(
                    "boletus_edulis",
                    "montseny",
                    target_text,
                    self.prediction(target),
                )
            )
            comparisons[target_text] = {
                "available": True,
                "batch_ids": {version_id: "generation-batch" for version_id in versions},
                "area_id": "montseny",
                "target_date": target_text,
                "members": payloads,
                "operational_comparison": mushroom_ml_multiversion_comparison.build_selected_operational_comparison(
                    payloads,
                    season_phase="in_season",
                    phenology={
                        "fruiting_delay_after_rain_days": {
                            "min": 5,
                            "optimal_min": 7,
                            "optimal_max": 14,
                            "max": 21,
                        }
                    },
                ),
                "consensus_computed": True,
                "ensemble_computed": False,
                "runtime_metrics": {},
            }
        template_request = self.request(
            compare_models=True,
            multiversion_selection=first_day_selections,
        )
        template_response = {
            "schema_version": SCHEMA_VERSION,
            "kind": RESPONSE_KIND,
            "runtime_fingerprint": identity.runtime_fingerprint,
            "request": template_request,
            "data": {
                "species": {
                    "boletus_edulis": {
                        "areas": ["montseny"],
                        "predictions": {
                            "montseny": {
                                row.target_date: dict(row.payload) for row in predictions
                            }
                        },
                        "model_comparisons": {"montseny": {}},
                        "multiversion_comparisons": comparisons,
                        "multiversion_comparison": comparisons[self.issue_date.isoformat()],
                    }
                },
                "model_catalog": {"preferred_version_id": "biology_v4"},
            },
            "metrics": {},
        }
        subset_request = {
            **template_request,
            "multiversion_selection": [first_day_selections[0]],
        }
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "weekly.sqlite"
            write_artifact(
                target,
                identity=identity,
                coverage=coverage,
                base_predictions=predictions,
                operational_members=members,
                responses=[
                    PrecomputedResponse(
                        template_request, template_response, tuple(required)
                    )
                ],
                species_context={
                    "boletus_edulis": {
                        "phenology": {
                            "fruiting_delay_after_rain_days": {
                                "min": 5,
                                "optimal_min": 7,
                                "optimal_max": 14,
                                "max": 21,
                            }
                        },
                        "season_phase_by_date": {
                            (self.issue_date + timedelta(days=offset)).isoformat(): "in_season"
                            for offset in range(7)
                        },
                    }
                },
            )
            lookup = lookup_artifact(
                target, identity=identity, request=subset_request
            )
            connection = sqlite3.connect(target)
            with connection:
                connection.execute(
                    """DELETE FROM operational_members
                        WHERE version_id='biology_v4' AND target_date=?""",
                    ((self.issue_date + timedelta(days=3)).isoformat(),),
                )
            connection.close()
            partial = lookup_artifact(
                target, identity=identity, request=subset_request
            )

        self.assertTrue(lookup.hit, lookup.reason)
        self.assertEqual(lookup.response["request"], subset_request)
        subset = lookup.response["data"]["species"]["boletus_edulis"]
        for comparison in subset["multiversion_comparisons"].values():
            self.assertEqual(
                comparison["operational_comparison"]["selected_version_ids"],
                ["biology_v4"],
            )
            self.assertTrue(
                all(
                    member["model_ref"]["version_id"] == "biology_v4"
                    for member in comparison["members"]
                )
            )
        self.assertFalse(partial.hit)
        self.assertEqual(partial.reason, "coverage_partial")

    def test_invalid_stored_response_falls_back_as_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            connection = sqlite3.connect(target)
            with connection:
                connection.execute(
                    "UPDATE response_payloads SET payload_json=?",
                    ('{"kind":"invalid"}',),
                )
            connection.close()
            live = mock.Mock(return_value=stored.response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=stored.request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "artifact_corrupt")

    def test_corrupt_sqlite_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            target.write_bytes(b"not a sqlite database")
            live = mock.Mock(return_value=stored.response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=stored.request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "artifact_corrupt")
        live.assert_called_once()

    def test_wrong_runtime_identity_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            _identity, stored, _manifest = self.write_fixture(target)
            active_identity = self.identity(runtime=self.runtime_b)
            active_response = {**stored.response, "runtime_fingerprint": self.runtime_b}
            live = mock.Mock(return_value=active_response)

            resolved = resolve_with_fallback(
                target,
                identity=active_identity,
                request=stored.request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "identity_mismatch")
        self.assertEqual(resolved.response["runtime_fingerprint"], self.runtime_b)

    def test_atomic_replacement_keeps_existing_reader_on_previous_inode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, first_manifest = self.write_fixture(target)
            reader = ArtifactReader(target, expected_identity=identity)
            try:
                fixture = self.fixture(identity)
                replacement_response = {
                    **fixture[4].response,
                    "metrics": {"backend_seconds": 99.0},
                }
                replacement = PrecomputedResponse(
                    fixture[4].request,
                    replacement_response,
                    fixture[4].required_coverage,
                )
                second_manifest = write_artifact(
                    target,
                    identity=fixture[0],
                    coverage=fixture[1],
                    base_predictions=fixture[2],
                    operational_members=fixture[3],
                    responses=[replacement],
                )
                old_lookup = reader.lookup(stored.request)
                new_lookup = lookup_artifact(
                    target, identity=identity, request=stored.request
                )
            finally:
                reader.close()

        self.assertEqual(old_lookup.response, stored.response)
        self.assertEqual(new_lookup.response, replacement_response)
        self.assertNotEqual(first_manifest.file_sha256, second_manifest.file_sha256)

    def test_published_sqlite_has_no_wal_or_journal_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            self.write_fixture(target)

            self.assertFalse(Path(str(target) + "-wal").exists())
            self.assertFalse(Path(str(target) + "-shm").exists())
            self.assertFalse(Path(str(target) + "-journal").exists())

    def test_failed_atomic_replace_preserves_previous_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, _stored, original = self.write_fixture(target)
            fixture = self.fixture(identity)

            with mock.patch.object(os, "replace", side_effect=OSError("simulated interruption")):
                with self.assertRaisesRegex(OSError, "simulated interruption"):
                    write_artifact(
                        target,
                        identity=fixture[0],
                        coverage=fixture[1],
                        base_predictions=fixture[2],
                        operational_members=fixture[3],
                        responses=[fixture[4]],
                    )

            current = validate_artifact(target, expected_identity=identity)
            temporary_files = list(Path(temporary).glob(".predictor-weekly.sqlite.*.tmp"))

        self.assertEqual(current.file_sha256, original.file_sha256)
        self.assertEqual(temporary_files, [])

    def test_full_validation_detects_logically_truncated_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, _stored, _manifest = self.write_fixture(target)
            connection = sqlite3.connect(target)
            with connection:
                connection.execute("DELETE FROM operational_members WHERE horizon_days=7")
            connection.close()

            with self.assertRaisesRegex(PrecomputeArtifactError, "counters"):
                validate_artifact(target, expected_identity=identity, full=True)

    def test_validation_rejects_wrong_file_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, _stored, _manifest = self.write_fixture(target)

            with self.assertRaisesRegex(PrecomputeArtifactError, "SHA-256"):
                validate_artifact(
                    target,
                    expected_identity=identity,
                    expected_file_sha256="sha256:" + "0" * 64,
                )

    def test_unknown_sqlite_schema_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "predictor-weekly.sqlite"
            identity, stored, _manifest = self.write_fixture(target)
            connection = sqlite3.connect(target)
            connection.execute("PRAGMA user_version=99")
            connection.close()
            live = mock.Mock(return_value=stored.response)

            resolved = resolve_with_fallback(
                target,
                identity=identity,
                request=stored.request,
                live_predictor=live,
            )

        self.assertEqual(resolved.source, "live")
        self.assertEqual(resolved.fallback_reason, "schema_unknown")


class PredictorPrecomputePublicationTests(PredictorPrecomputeArtifactTests):
    def test_identity_plan_counts_species_area_days_and_members_without_execution(self) -> None:
        selections = [
            {
                "version_id": "biology_v4",
                "temporal_contract_id": "lag_event_v1",
                "profile_id": "extended_weather",
                "estimator_id": "random_forest",
                "horizon_days": horizon,
            }
            for horizon in range(1, 8)
        ]
        identity = plan_artifact_identity(
            runtime_fingerprint=self.runtime_a,
            issue_date=self.issue_date,
            trained_species_ids=["boletus_edulis"],
            installed_versions=self.identity().installed_versions,
            area_ids_by_species={"boletus_edulis": ["montseny", "montseny", "bergueda"]},
            operational_selections_by_species={"boletus_edulis": selections},
        )
        self.assertEqual(
            {"species": 1, "areas": 2, "days": 7, "versions": 1, "members": 14},
            dict(identity.expected_counts),
        )

    def test_active_lookup_uses_runtime_identity_and_returns_explicit_miss(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.sqlite3"
            identity, stored, _manifest = self.write_fixture(path)
            hit = lookup_active_artifact(
                path,
                runtime_fingerprint=identity.runtime_fingerprint,
                request=stored.request,
            )
            mismatch = lookup_active_artifact(
                path,
                runtime_fingerprint=self.runtime_b,
                request=stored.request,
            )
            self.assertTrue(hit.hit)
            self.assertEqual(stored.response, hit.response)
            self.assertFalse(mismatch.hit)
            self.assertEqual("identity_mismatch", mismatch.reason)

    def test_scientific_payload_ignores_nested_runtime_metrics_and_area_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _identity, stored, _manifest = self.write_fixture(
                Path(temporary) / "active.sqlite3"
            )
        left = json.loads(json.dumps(stored.response))
        right = json.loads(json.dumps(stored.response))
        left["data"]["species"]["boletus_edulis"]["areas"] = ["montseny", "breda"]
        right["data"]["species"]["boletus_edulis"]["areas"] = ["breda", "montseny"]
        left["data"]["species"]["boletus_edulis"]["runtime_metrics"] = {
            "backend_seconds": 1.0
        }
        right["data"]["species"]["boletus_edulis"]["runtime_metrics"] = {
            "backend_seconds": 9.0
        }

        self.assertEqual(
            scientific_response_payload(left),
            scientific_response_payload(right),
        )

    def test_large_scientific_payloads_are_stored_as_compressed_blobs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active.sqlite3"
            self.write_fixture(path)
            connection = sqlite3.connect(path)
            try:
                for table in (
                    "base_predictions",
                    "operational_members",
                    "response_coverage",
                    "response_payloads",
                ):
                    storage_type, payload = connection.execute(
                        f"SELECT typeof(payload_json), payload_json FROM {table} LIMIT 1"
                    ).fetchone()
                    self.assertEqual("blob", storage_type)
                    decoded = json.loads(zlib.decompress(payload).decode("utf-8"))
                    self.assertIsInstance(
                        decoded,
                        list if table == "response_coverage" else dict,
                    )
            finally:
                connection.close()

    def test_two_phase_publication_keeps_identical_ha_and_worker_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, coverage, predictions, members, responses = self.fixture()
            source = root / "built.sqlite3"
            manifest = write_artifact(
                source,
                identity=identity,
                coverage=coverage,
                base_predictions=predictions,
                operational_members=members,
                responses=[responses],
            )
            desired_path = root / "desired.json"
            desired = advance_desired_state(
                desired_path,
                identity=identity,
                worker_id="worker_aaaaaaaa",
                trigger_origin="runtime",
            )
            receipt = publish_received_artifact(
                io.BytesIO(source.read_bytes()),
                content_length=manifest.size_bytes,
                expected_sha256=manifest.file_sha256,
                identity=identity,
                desired_state_path=desired_path,
                destination_path=root / "ha-active.sqlite3",
                receipt_path=root / "ha-receipt.json",
                desired_revision=desired["revision"],
                max_bytes=manifest.size_bytes,
            )
            worker_manifest = activate_worker_copy(
                source,
                destination_path=root / "worker-active.sqlite3",
                receipt=receipt,
                identity=identity,
            )
            self.assertEqual(manifest.file_sha256, worker_manifest.file_sha256)
            self.assertEqual(
                (root / "ha-active.sqlite3").read_bytes(),
                (root / "worker-active.sqlite3").read_bytes(),
            )

    def test_advance_desired_state_migrates_previous_artifact_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "desired.json"
            legacy_identity = self.identity().as_dict()
            legacy_identity["schema_version"] = "1.0"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "revision": 7,
                        "identity": legacy_identity,
                    }
                ),
                encoding="utf-8",
            )

            desired = advance_desired_state(
                path,
                identity=self.identity(),
                worker_id="",
                trigger_origin="manual",
            )

            self.assertEqual(8, desired["revision"])
            self.assertEqual(
                ARTIFACT_SCHEMA_VERSION,
                desired["identity"]["schema_version"],
            )

    def test_cancelled_desire_is_durable_and_next_revision_clears_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "desired.json"
            identity = self.identity()
            desired = advance_desired_state(
                path,
                identity=identity,
                worker_id="worker_aaaaaaaa",
                trigger_origin="manual",
            )

            cancelled = cancel_desired_state(
                path,
                desired_revision=int(desired["revision"]),
                artifact_id=identity.artifact_id,
                cancelled_at="2026-08-31T18:00:00+00:00",
            )

            self.assertEqual("cancelled", cancelled["terminal_status"])
            self.assertEqual(
                "cancelled", load_desired_state(path)["terminal_status"]
            )
            replacement = advance_desired_state(
                path,
                identity=identity,
                worker_id="worker_aaaaaaaa",
                trigger_origin="manual",
            )
            self.assertEqual(2, replacement["revision"])
            self.assertNotIn("terminal_status", replacement)

    def test_cancelled_desire_rejects_late_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, coverage, predictions, members, responses = self.fixture()
            source = root / "built.sqlite3"
            manifest = write_artifact(
                source,
                identity=identity,
                coverage=coverage,
                base_predictions=predictions,
                operational_members=members,
                responses=[responses],
            )
            desired_path = root / "desired.json"
            desired = advance_desired_state(
                desired_path,
                identity=identity,
                worker_id="worker_aaaaaaaa",
                trigger_origin="manual",
            )
            cancel_desired_state(
                desired_path,
                desired_revision=int(desired["revision"]),
                artifact_id=identity.artifact_id,
                cancelled_at="2026-08-31T18:00:00+00:00",
            )

            with self.assertRaisesRegex(ValueError, "no longer desired"):
                publish_received_artifact(
                    io.BytesIO(source.read_bytes()),
                    content_length=manifest.size_bytes,
                    expected_sha256=manifest.file_sha256,
                    identity=identity,
                    desired_state_path=desired_path,
                    destination_path=root / "ha-active.sqlite3",
                    receipt_path=root / "ha-receipt.json",
                    desired_revision=int(desired["revision"]),
                    max_bytes=manifest.size_bytes,
                )

    def test_superseded_upload_cannot_replace_active_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity, coverage, predictions, members, responses = self.fixture()
            source = root / "built.sqlite3"
            manifest = write_artifact(
                source,
                identity=identity,
                coverage=coverage,
                base_predictions=predictions,
                operational_members=members,
                responses=[responses],
            )
            desired_path = root / "desired.json"
            old = advance_desired_state(
                desired_path,
                identity=identity,
                worker_id="worker_aaaaaaaa",
                trigger_origin="runtime",
            )
            advance_desired_state(
                desired_path,
                identity=self.identity(runtime=self.runtime_b),
                worker_id="worker_aaaaaaaa",
                trigger_origin="runtime",
            )
            active = root / "active.sqlite3"
            active.write_bytes(b"preserve-me")
            with self.assertRaisesRegex(ValueError, "no longer desired"):
                publish_received_artifact(
                    io.BytesIO(source.read_bytes()),
                    content_length=manifest.size_bytes,
                    expected_sha256=manifest.file_sha256,
                    identity=identity,
                    desired_state_path=desired_path,
                    destination_path=active,
                    receipt_path=root / "receipt.json",
                    desired_revision=old["revision"],
                    max_bytes=manifest.size_bytes,
                )
            self.assertEqual(b"preserve-me", active.read_bytes())


class WeeklyPrecomputeBatchTests(unittest.TestCase):
    runtime = "sha256:" + "c" * 64
    issue_date = date(2026, 8, 30)

    class FakePredictor:
        def areas_with_species_observations(self):
            return ["montseny"]

        def season_phase(self, _target_date):
            return "in_season"

    class FakeService:
        def __init__(self, owner: "WeeklyPrecomputeBatchTests") -> None:
            self.owner = owner
            self.context_ids: list[int] = []
            self.prepared_weather_ids: list[int] = []
            self.calls: list[dict[str, object]] = []

        def predictor(self, _species_id: str):
            return WeeklyPrecomputeBatchTests.FakePredictor()

        def species_phenology(self, _species_id: str):
            return {"fruiting_delay_after_rain_days": {"minimum": 3, "maximum": 21}}

        def execute(self, request, *, progress=None, shared_context=None):
            self.context_ids.append(id(shared_context))
            self.prepared_weather_ids.append(
                id(shared_context.setdefault("prepared_weather_cache", {}))
            )
            self.calls.append(dict(request))
            if progress is not None:
                progress(50, "Fake execution", str(request["target_date"]))
            species = str(request["species_id"])
            area = str(request["area_id"])
            target = str(request["target_date"])
            days = [
                (self.owner.issue_date + timedelta(days=offset)).isoformat()
                for offset in range(7)
            ]
            predictions = {
                day: self.owner.prediction(species, "montseny", day) for day in days
            }
            member_comparisons = {
                day: {
                    "available": True,
                    "members": [self.owner.member(offset + 1)],
                    "operational_comparison": {"selected_winners": []},
                }
                for offset, day in enumerate(days)
            }
            species_payload: dict[str, object] = {"areas": ["montseny"]}
            if request["view"] == "recommender":
                species_payload.update(
                    {
                        "season_phase": "in_season",
                        "rankings": {target: []},
                        "model_comparisons": {"montseny": {target: {}}},
                    }
                )
            elif request["view"] == "query" and not area:
                species_payload.update(
                    {
                        "rankings": {target: [predictions[target]]},
                        "model_comparisons": {"montseny": {target: {}}},
                    }
                )
            else:
                species_payload.update(
                    {
                        "predictions": {"montseny": predictions},
                        "model_comparisons": {
                            "montseny": {day: {} for day in days}
                        },
                    }
                )
                if request["view"] == "query":
                    species_payload["multiversion_comparisons"] = member_comparisons
                    species_payload["multiversion_comparison"] = member_comparisons[target]
            return {
                "schema_version": SCHEMA_VERSION,
                "kind": RESPONSE_KIND,
                "runtime_fingerprint": self.owner.runtime,
                "request": dict(request),
                "data": {
                    "species": {species: species_payload},
                    "model_catalog": {"preferred_version_id": "biology_v4"},
                },
                "metrics": {"backend_seconds": 0.1},
            }

    def prediction(self, species: str, area: str, target_date: str):
        return {
            "species_id": species,
            "area_id": area,
            "target_date": target_date,
            "lr_probability": 0.6,
            "rf_probability": 0.7,
            "ensemble_probability": 0.65,
            "label": "favorable",
            "weather_station_code": "station",
            "weather_station_distance_km": 2.0,
            "weather_coverage_days": 90,
            "feature_gaps": [],
            "features_used": {},
            "season_phase": "in_season",
        }

    def member(self, horizon: int):
        return {
            "model_ref": {
                "version_id": "biology_v4",
                "temporal_contract_id": "lag_event_biology_v4",
                "profile_id": "extended_weather",
                "estimator_id": "random_forest",
                "horizon_days": horizon,
            },
            "available": True,
            "prediction": {"probability": 0.72},
            "evaluation": {"brier_score": 0.18},
        }

    def identity(self):
        return ArtifactIdentity.create(
            runtime_fingerprint=self.runtime,
            issue_date=self.issue_date,
            trained_species_ids=["boletus_edulis"],
            installed_versions=[
                RuntimeVersionIdentity.create(
                    version_id="biology_v4",
                    generation_id="generation-v4",
                    profile_ids=["extended_weather"],
                )
            ],
            expected_counts={
                "species": 1,
                "areas": 1,
                "days": 7,
                "versions": 1,
                "members": 7,
            },
        )

    def selections(self):
        return [
            {
                "version_id": "biology_v4",
                "temporal_contract_id": "lag_event_biology_v4",
                "profile_id": "extended_weather",
                "estimator_id": "random_forest",
                "horizon_days": horizon,
            }
            for horizon in range(1, 8)
        ]

    def test_batch_reuses_one_context_and_matches_service_response(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "weekly.sqlite"
            service = self.FakeService(self)
            progress: list[tuple[int, int]] = []

            result = build_weekly_artifact(
                target,
                identity=self.identity(),
                predictor_service=service,
                operational_selections=self.selections(),
                progress=lambda completed, total, _unit: progress.append(
                    (completed, total)
                ),
            )
            query = next(
                request
                for request in service.calls
                if request["view"] == "query" and request["area_id"]
            )
            stored = lookup_artifact(target, identity=self.identity(), request=query)
            live = self.FakeService(self).execute(query, shared_context={})
            final_day_query = dict(query)
            final_day = self.issue_date + timedelta(days=6)
            final_day_query["target_date"] = final_day.isoformat()
            final_day_query["multiversion_selection"] = (
                mushroom_ml_multiversion_comparison.operational_selections(
                    self.selections(),
                    target_date=final_day,
                    issue_date=self.issue_date,
                )
            )
            final_day_stored = lookup_artifact(
                target, identity=self.identity(), request=final_day_query
            )
            final_day_live = self.FakeService(self).execute(
                final_day_query, shared_context={}
            )
            connection = sqlite3.connect(target)
            try:
                response_row_count = connection.execute(
                    "SELECT COUNT(*) FROM responses"
                ).fetchone()[0]
                payload_row_count = connection.execute(
                    "SELECT COUNT(*) FROM response_payloads"
                ).fetchone()[0]
            finally:
                connection.close()

        self.assertEqual(result.request_count, 28)
        self.assertEqual(result.executed_request_count, 16)
        self.assertEqual(response_row_count, 28)
        self.assertEqual(payload_row_count, 16)
        self.assertEqual(len(service.calls), 16)
        self.assertEqual(result.coverage_count, 7)
        self.assertEqual(result.base_prediction_count, 7)
        self.assertEqual(result.operational_member_count, 7)
        self.assertEqual(len(set(service.context_ids)), 1)
        self.assertEqual(len(set(service.prepared_weather_ids)), 1)
        self.assertTrue(any(0 < completed < 1 for completed, _total in progress))
        self.assertEqual(progress[-1], (16, 16))
        self.assertTrue(stored.hit)
        self.assertEqual(
            scientific_response_payload(stored.response),
            scientific_response_payload(live),
        )
        self.assertTrue(final_day_stored.hit, final_day_stored.reason)
        self.assertEqual(
            scientific_response_payload(final_day_stored.response),
            scientific_response_payload(final_day_live),
        )

    def test_batch_checks_cancellation_between_requests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "weekly.sqlite"
            service = self.FakeService(self)
            checks = 0

            def cancel():
                nonlocal checks
                checks += 1
                if checks == 3:
                    raise InterruptedError("superseded")

            with self.assertRaisesRegex(InterruptedError, "superseded"):
                build_weekly_artifact(
                    target,
                    identity=self.identity(),
                    predictor_service=service,
                    operational_selections=self.selections(),
                    cancel_check=cancel,
                )

        self.assertFalse(target.exists())
        self.assertEqual(len(service.calls), 2)

    def test_batch_deduplicates_multiple_species_in_one_shared_context(self) -> None:
        identity = ArtifactIdentity.create(
            runtime_fingerprint=self.runtime,
            issue_date=self.issue_date,
            trained_species_ids=["boletus_edulis", "boletus_pinophilus"],
            installed_versions=[
                RuntimeVersionIdentity.create(
                    version_id="biology_v4",
                    generation_id="generation-v4",
                    profile_ids=["extended_weather"],
                )
            ],
            expected_counts={
                "species": 2,
                "areas": 2,
                "days": 7,
                "versions": 1,
                "members": 14,
            },
        )
        service = self.FakeService(self)
        selections = {
            species_id: self.selections()
            for species_id in identity.trained_species_ids
        }
        with tempfile.TemporaryDirectory() as temporary:
            result = build_weekly_artifact(
                Path(temporary) / "weekly.sqlite",
                identity=identity,
                predictor_service=service,
                operational_selections=selections,
            )

        self.assertEqual(result.request_count, 49)
        self.assertEqual(result.executed_request_count, 25)
        self.assertEqual(len(set(service.context_ids)), 1)
        self.assertEqual(len(set(service.prepared_weather_ids)), 1)


if __name__ == "__main__":
    unittest.main()
