from __future__ import annotations

import copy
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from rainmapper_core import mushroom_gbif_import as gbif, mushroom_observations
from rainmapper_core.mushroom_store import MushroomDataStore

ROOT = Path(__file__).resolve().parents[1]


def package_bytes(records=None, *, bad_hash=False, extra=None, compressed=False):
    photo = io.BytesIO()
    Image.new("RGB", (12, 8), (42, 70, 30)).save(photo, "JPEG")
    photo = photo.getvalue()
    digest = hashlib.sha256(photo).hexdigest()
    record = {"gbif_id": "12345", "species_id": "fixture_species", "observed_at": "2025-08-03",
              "lat": 42.123, "lon": 2.123, "coordinate_uncertainty_m": None,
              "original": {"eventDate": "2025-08-03T12:00:00", "occurrenceID": "provider/12345", "recordedBy": "Original author", "habitat": "Woodland"},
              "review": {"status": "approved"},
              "photos": [{"asset": digest, "creator": "Photographer", "license": "CC-BY"},
                         {"asset": digest, "creator": "Another attribution", "license": None}]}
    records = copy.deepcopy(records) if records is not None else [record]
    manifest = {"schema": gbif.SCHEMA, "version": 1,
                "export": {"batch_id": "fixture", "snapshot_sha256": "a" * 64},
                "records": records, "assets": {digest: {"bytes": len(photo)}}}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("media/" + digest, photo[:-1] + b"x" if bad_hash else photo)
        if extra:
            archive.writestr(*extra)
    return output.getvalue(), record


class GBIFImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.store = MushroomDataStore(defaults_dir=ROOT / "mushroom-data", data_dir=self.path / "data")
        self.store.data_dir.mkdir()
        # Copy public catalogs only. Never load private observations for fixture tests.
        for kind in ("profiles", "catalogs", "gis"):
            self.store.persistent_path(kind).write_bytes(self.store.default_path(kind).read_bytes())
        self.store.persistent_path("observations").write_bytes((ROOT / "rainmapper-app/defaults/mushroom_observations.json").read_bytes())
        self.species = self.store.load("profiles")["species_profiles"][0]["species_id"]
        _, self.record = package_bytes()
        self.record["species_id"] = self.species

    def upload(self, records=None, **kwargs):
        content, _ = package_bytes(records or [self.record], **kwargs)
        return gbif.receive(self.store, (content[i:i+103] for i in range(0, len(content), 103)), "owner")

    def test_roundtrip_keeps_photos_authorship_unknown_and_pending(self):
        token, package = self.upload()
        row = package["rows"][0]["observation"]
        self.assertEqual(("normal", "draft", "review"), (row["flush_abundance"], row["validation_status"], row["calibration_use"]))
        self.assertEqual(500, row["location"]["precision_m"])
        self.assertIsNone(row["external_source"]["coordinate_uncertainty_m"])
        self.assertTrue(row["external_source"]["uncertainty_assumed"])
        self.assertEqual("GBIF", row["observer"]["name"])
        self.assertEqual(2, len(row["media"]))
        self.assertEqual("Photographer", row["media"][0]["attribution"]["creator"])
        self.assertIsNone(row["media"][1]["attribution"]["license"])
        result = gbif.commit(self.store, token, "owner", ["12345"], [])
        self.assertEqual(1, result["created"])
        stored = self.store.load("observations")["observations"][0]
        for photo in stored["media"]:
            self.assertEqual(photo["sha256"], hashlib.sha256((self.store.data_dir / photo["path"]).read_bytes()).hexdigest())
        self.assertEqual(result, gbif.commit(self.store, token, "owner", ["12345"], []))
        self.assertEqual(1, len(self.store.load("observations")["observations"]))
        self.assertTrue(list(self.store.backup_dir().iterdir()))

    def test_declared_radius_is_preserved_without_rounding(self):
        self.record["coordinate_uncertainty_m"] = 725.25
        _, package = self.upload()
        row = package["rows"][0]["observation"]
        self.assertEqual(725.25, row["location"]["precision_m"])
        self.assertEqual("declared", row["location"]["precision_origin"])
        self.assertFalse(row["external_source"]["uncertainty_assumed"])

    def test_existing_snapshot_geography_is_preserved_without_running_gis(self):
        self.record["geography"] = {"latitude": self.record["lat"], "longitude": self.record["lon"],
                                    "elevation": {"status": "available", "value_m": 651.8, "resolution_m": 5, "source_id": "dem_5m"},
                                    "municipality": {"name": "Fixture"}}
        token, package = self.upload()
        row = package["rows"][0]["observation"]
        self.assertEqual(651.8, row["altitude"]["meters"])
        self.assertEqual(self.record["geography"], row["external_source"]["geography"])
        gbif.commit(self.store, token, "owner", ["12345"], [])

    def test_legacy_source_links_also_detect_duplicate_and_provider_conflict(self):
        _, package = self.upload()
        for url, expected in (("https://www.gbif.org/occurrence/12345", "duplicate"), ("provider/12345", "conflict")):
            with self.subTest(url=url):
                existing = {"observation_id": "legacy", "source": {"url": url}}
                self.assertEqual(expected, gbif.preview(package, [existing])[0]["status"])

    def test_zero_negative_infinite_and_boolean_uncertainty_never_pass(self):
        for value in (0, -1, True):
            with self.subTest(value=value):
                self.record["coordinate_uncertainty_m"] = value
                token, package = self.upload()
                self.assertEqual("uncertainty", package["rows"][0]["error"])
                gbif.cancel(self.store, token, "owner")
        self.assertRaises(ValueError, gbif.strict_json, '{"x":Infinity}')

    def test_corrupted_photo_and_unsafe_zip_are_rejected_without_staging(self):
        for kwargs in ({"bad_hash": True}, {"extra": ("../private.json", "x")}, {"compressed": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(gbif.ImportError):
                self.upload(**kwargs)
        self.assertEqual([], list(gbif.stage_root(self.store).iterdir()))

    def test_incomplete_date_and_absence_are_not_importable(self):
        for field, value, code in (("eventDate", "2025-08", "date"), ("eventDate", "2025-08-03/2025-08-04", "date"), ("occurrenceStatus", "ABSENT", "presence")):
            with self.subTest(field=field, value=value):
                record = copy.deepcopy(self.record)
                record["original"][field] = value
                token, package = self.upload([record])
                self.assertEqual(code, package["rows"][0]["error"])
                self.assertRaises(gbif.ImportError, gbif.commit, self.store, token, "owner", ["12345"], [])
                gbif.cancel(self.store, token, "owner")

    def test_duplicates_and_archive_do_not_overwrite(self):
        token, package = self.upload()
        existing = package["rows"][0]["observation"]
        existing["validation_status"] = "valid"
        existing["calibration_use"] = "include"
        self.assertEqual("duplicate", gbif.preview(package, [existing])[0]["status"])
        result = gbif.commit(self.store, token, "owner", ["12345"], [existing])
        self.assertEqual(0, result["created"])
        self.assertEqual([], self.store.load("observations")["observations"])
        self.assertEqual("valid", existing["validation_status"])

    def existing_duplicate(self, archived=False):
        token, package = self.upload()
        row = copy.deepcopy(package["rows"][0]["observation"])
        row["observation_id"] = "existing-identity"
        row["validation_status"] = "valid"
        row["calibration_use"] = "include"
        row["source"]["notes"] = "reviewed locally"
        if archived:
            path = self.store.data_dir / "archived/mushroom_observations_archived.json"
            path.parent.mkdir()
            gbif.write_json_atomic(path, {"observations": [row], "metadata": {"note": "preserve"}})
        else:
            payload = self.store.load("observations")
            payload["observations"] = [row]
            self.assertTrue(self.store.replace("observations", payload).ok)
        return token, package, row

    def test_explicit_replace_preserves_id_resets_review_and_retries(self):
        token, package, old = self.existing_duplicate()
        match = gbif.preview(package, [old])[0]
        self.assertTrue(match["replaceable"])
        decision = {"12345": match["existing_revision"]}
        result = gbif.commit(self.store, token, "owner", [], [], decision)
        self.assertEqual(1, result["replaced"])
        saved = self.store.load("observations")["observations"]
        self.assertEqual(1, len(saved))
        self.assertEqual(old["observation_id"], saved[0]["observation_id"])
        self.assertEqual(("draft", "review", "normal"), tuple(saved[0][key] for key in ("validation_status", "calibration_use", "flush_abundance")))
        self.assertEqual("", saved[0]["source"]["notes"])
        self.assertEqual(result, gbif.commit(self.store, token, "owner", [], [], decision))

    def test_keep_and_concurrent_edit_do_not_replace(self):
        token, package, old = self.existing_duplicate()
        revision = gbif.preview(package, [old])[0]["existing_revision"]
        payload = self.store.load("observations")
        payload["observations"][0]["source"]["notes"] = "edited after preview"
        self.store.replace("observations", payload)
        with self.assertRaisesRegex(gbif.ImportError, "changed"):
            gbif.commit(self.store, token, "owner", [], [], {"12345": revision})
        result = gbif.commit(self.store, token, "owner", [], [])
        self.assertEqual(0, result["replaced"])
        self.assertEqual("edited after preview", self.store.load("observations")["observations"][0]["source"]["notes"])

    def test_archived_replacement_restores_and_keeps_archive_backup(self):
        token, package, old = self.existing_duplicate(archived=True)
        match = gbif.preview(package, [], [old])[0]
        self.assertTrue(match["archived"] and match["replaceable"])
        result = gbif.commit(self.store, token, "owner", [], [old], {"12345": match["existing_revision"]})
        self.assertEqual(1, result["replaced"])
        self.assertEqual("draft", self.store.load("observations")["observations"][0]["validation_status"])
        archive = json.loads((self.store.data_dir / "archived/mushroom_observations_archived.json").read_text())
        self.assertEqual([], archive["observations"])
        self.assertEqual("preserve", archive["metadata"]["note"])
        backup = json.loads((gbif.stage_path(self.store, token) / "archive-before.json").read_text())
        self.assertEqual([old], backup["observations"])

    def test_restore_recovers_after_crash_between_active_and_archive(self):
        token, package, old = self.existing_duplicate(archived=True)
        decision = {"12345": gbif.preview(package, [], [old])[0]["existing_revision"]}
        with patch.object(gbif, "finish_restorations", side_effect=OSError("crash")):
            self.assertRaises(OSError, gbif.commit, self.store, token, "owner", [], [old], decision)
        result = gbif.commit(self.store, token, "owner", [], [old], decision)
        self.assertEqual(1, result["replaced"])
        self.assertEqual(1, len(self.store.load("observations")["observations"]))
        self.assertEqual([], json.loads((self.store.data_dir / "archived/mushroom_observations_archived.json").read_text())["observations"])

    def test_duplicate_identity_ambiguity_cannot_replace(self):
        token, package, old = self.existing_duplicate()
        other = copy.deepcopy(old)
        other["observation_id"] = "other"
        self.assertFalse(gbif.preview(package, [old, other])[0]["replaceable"])

    def test_merged_package_preserves_each_records_source(self):
        self.record["source_export"] = {"snapshot_sha256": "b" * 64, "batch_id": "previous-export"}
        _, package = self.upload()
        external = package["rows"][0]["observation"]["external_source"]
        self.assertEqual("b" * 64, external["snapshot_sha256"])
        self.assertEqual("previous-export", external["batch_id"])

    def test_preparation_recovers_gis_dem_and_unique_site_then_commits(self):
        from rainmapper_core import mushroom_gis_recovery as gis
        token, _ = self.upload()
        host = self.store.load("catalogs")["catalogs"]["host_taxa"][0]["id"]
        sites = {"areas": [{"area_id": "area"}], "micro_areas": [{"micro_area_id": "micro", "area_id": "area", "geometry": {"type": "Polygon", "coordinates": [[[2, 42], [3, 42], [3, 43], [2, 43], [2, 42]]]}}]}
        gbif.write_json_atomic(self.store.data_dir / "mushroom_known_sites.json", sites)
        report = {"version": 1, "location": gis.point(42.123, 2.123), "values": {"host_ids": [host]}, "sources": {"host_ids": ["mfe25"]}, "forest": {"status": "available"}, "gaps": [], "altitude_m": 789, "altitude_source": "dem_5m"}
        with patch.object(gis, "observation_preview", return_value=report) as recover:
            prepared = gbif.prepare_record(self.store, token, "owner", "12345")
            self.assertTrue(prepared["gis_gaps"])  # Other GIS fields remain unavailable.
            self.assertEqual("micro", prepared["micro_area_id"])
            gbif.prepare_record(self.store, token, "owner", "12345")
            recover.assert_called_once()
        gbif.commit(self.store, token, "owner", ["12345"], [], require_prepared=True)
        row = self.store.load("observations")["observations"][0]
        self.assertEqual("micro", row["micro_area_id"])
        self.assertEqual(789, row["altitude"]["meters"])
        self.assertEqual([host], row["site_context"]["gis_recovery"]["values"]["host_ids"])
        self.assertEqual([], row["site_context"]["observed_host_ids"])
        self.assertEqual("gbif_import", row["site_context"]["gis_recovery"]["recovery_mode"])

    def test_preparation_failure_keeps_draft_with_explicit_gap(self):
        from rainmapper_core import mushroom_gis_recovery as gis
        token, _ = self.upload()
        with self.assertRaisesRegex(gbif.ImportError, "preparation"):
            gbif.commit(self.store, token, "owner", ["12345"], [], require_prepared=True)
        with patch.object(gis, "observation_preview", side_effect=OSError("unavailable")):
            self.assertTrue(gbif.prepare_record(self.store, token, "owner", "12345")["gis_gaps"])
        gbif.commit(self.store, token, "owner", ["12345"], [], require_prepared=True)
        row = self.store.load("observations")["observations"][0]
        self.assertEqual("draft", row["validation_status"])
        self.assertIn("gis_recovery_unavailable", row["site_context"]["gis_recovery"]["gaps"])

    def test_site_assignment_respects_holes_archives_and_nearest_tie(self):
        _, package = self.upload()
        row = package["rows"][0]["observation"]
        outer = [[2,42],[3,42],[3,43],[2,43],[2,42]]
        hole = [[2.1,42.1],[2.2,42.1],[2.2,42.2],[2.1,42.2],[2.1,42.1]]
        first = {"micro_area_id":"one","area_id":"area","geometry":{"type":"Polygon","coordinates":[outer,hole]}}
        sites = {"areas":[{"area_id":"area"}],"micro_areas":[first]}
        gbif.assign_known_micro_area(row, sites)
        self.assertIsNone(row["micro_area_id"])
        first["geometry"]["coordinates"] = [outer]
        second = copy.deepcopy(first);second["micro_area_id"] = "two";sites["micro_areas"].append(second)
        gbif.assign_known_micro_area(row, sites)
        self.assertEqual("assigned", row["external_source"]["site_assignment"]["status"])
        self.assertEqual("containing_nearest_centre", row["external_source"]["site_assignment"]["method"])
        second["archived"] = True
        gbif.assign_known_micro_area(row, sites)
        self.assertEqual("one", row["micro_area_id"])
        sites["areas"][0]["archived"] = True
        gbif.assign_known_micro_area(row, sites)
        self.assertIsNone(row["micro_area_id"])

    def test_other_gbif_id_same_provider_record_is_conflict(self):
        token, package = self.upload()
        existing = copy.deepcopy(package["rows"][0]["observation"])
        existing["observation_id"] = "obs_gbif_999"
        existing["external_source"]["gbif_id"] = "999"
        self.assertEqual("conflict", gbif.preview(package, [existing])[0]["status"])
        self.assertRaises(gbif.ImportError, gbif.commit, self.store, token, "owner", ["12345"], [existing])

    def test_new_duplicates_within_batch_are_not_imported_twice(self):
        token, package = self.upload([self.record, self.record])
        self.assertRaises(gbif.ImportError, gbif.commit, self.store, token, "owner", ["12345"], [])
        self.assertEqual([], self.store.load("observations")["observations"])

    def test_concurrent_import_is_rechecked(self):
        first, _ = self.upload()
        second, _ = self.upload()
        gbif.commit(self.store, first, "owner", ["12345"], [])
        result = gbif.commit(self.store, second, "owner", ["12345"], [])
        self.assertEqual((0, 1), (result["created"], result["skipped"]))

    def test_rejection_and_owner_preserve_observations(self):
        token, _ = self.upload()
        self.assertRaises(gbif.ImportError, gbif.cancel, self.store, token, "other")
        gbif.cancel(self.store, token, "owner")
        self.assertFalse(gbif.stage_path(self.store, token).exists())
        self.assertEqual([], self.store.load("observations")["observations"])

    def test_invalid_version_or_excess_size_rejected_before_materializing(self):
        with patch.object(gbif, "MAX_PACKAGE_BYTES", 10):
            self.assertRaises(gbif.ImportError, self.upload)
        self.assertEqual([], list(gbif.stage_root(self.store).iterdir()))
        token, _ = self.upload()
        with patch.object(gbif, "MAX_OBSERVATIONS_BYTES", 100):
            self.assertRaises(gbif.ImportError, gbif.commit, self.store, token, "owner", ["12345"], [])
        self.assertFalse((self.store.data_dir / "media").exists())

    def test_retry_after_write_before_receipt_is_idempotent(self):
        token, _ = self.upload()
        real_write = gbif.write_json_atomic
        def fail_receipt(path, payload):
            if payload.get("status") == "complete":
                raise OSError("simulated disconnect after commit")
            return real_write(path, payload)
        with patch.object(gbif, "write_json_atomic", side_effect=fail_receipt):
            self.assertRaises(OSError, gbif.commit, self.store, token, "owner", ["12345"], [])
        result = gbif.commit(self.store, token, "owner", ["12345"], [])
        self.assertEqual(1, result["skipped"])
        self.assertEqual(1, len(self.store.load("observations")["observations"]))

    def test_edit_and_copy_keep_original_but_new_point_drops_declared_radius(self):
        _, package = self.upload()
        original = package["rows"][0]["observation"]
        edited = copy.deepcopy(original)
        edited["location"]["precision_m"] = 100
        mushroom_observations.preserve_observation_provenance(edited, original, precision_supplied=True)
        self.assertEqual("manual", edited["location"]["precision_origin"])
        self.assertEqual(original["external_source"], edited["external_source"])
        moved = copy.deepcopy(original)
        moved["location"]["lat"] += 1
        mushroom_observations.preserve_observation_provenance(moved, original, precision_supplied=True)
        self.assertEqual(0, moved["location"]["precision_m"])
        copied = copy.deepcopy(original)
        copied["observation_id"] = "copy"
        mushroom_observations.preserve_observation_provenance(copied, original, duplicate=True)
        self.assertTrue(copied["external_source"]["is_copy"])
        self.assertEqual(({}, {}), gbif.identity_index([copied]))

    def test_legacy_null_becomes_zero_only_when_saved(self):
        original = {"location": {"lat": 42, "lon": 2, "precision_m": None}}
        edited = copy.deepcopy(original)
        mushroom_observations.preserve_observation_provenance(edited, original)
        self.assertEqual(0, edited["location"]["precision_m"])
        self.assertEqual("legacy_default_zero", edited["location"]["precision_origin"])
        self.assertIsNone(original["location"]["precision_m"])

    def test_form_roundtrip_preserves_external_media_metadata_and_radius(self):
        from tests.test_web_server_auth import load_web_server_module
        web = load_web_server_module()
        _, package = self.upload()
        original = package["rows"][0]["observation"]
        original["metadata"]["custom_note"] = "preserve"
        form = {k: [str(v)] for k, v in {
            "observation_species_id": self.species, "observed_at": original["observed_at"],
            "location_lat": 42.123, "location_lon": 2.123, "location_source": "gbif",
            "location_precision_m": 500, "flush_abundance": "normal", "source_type": "gbif",
            "source_label": "GBIF", "source_quality": 0.75, "validation_status": "draft", "calibration_use": "review",
            "observer_name": "GBIF", "observer_expertise": "unknown",
        }.items()}
        saved = web.observation_payload_from_form(form, [original], original)
        self.assertEqual(original["external_source"], saved["external_source"])
        self.assertEqual(original["media"], saved["media"])
        self.assertEqual("preserve", saved["metadata"]["custom_note"])
        self.assertEqual("assumed_unknown_500m", saved["location"]["precision_origin"])
        form["draft_map_source_observation_id"] = [original["observation_id"]]
        copied = web.observation_payload_from_form(form, [original])
        self.assertTrue(copied["external_source"]["is_copy"])
        self.assertNotEqual(original["observation_id"], copied["observation_id"])

    def test_multiple_photo_modal_reaches_next_photo(self):
        from tests.test_web_server_auth import load_web_server_module
        load_web_server_module()
        import mushroom_profiles_ui as ui
        row = {"observation_id": "fixture", "media": [
            {"kind": "photo", "url": "./one.jpg", "path": "media/one.jpg"},
            {"kind": "photo", "url": "./two.jpg", "path": "media/two.jpg"},
        ]}
        first = ui.render_observation_photo_modal(row, row["media"][0], 0)
        second_id = ui.observation_photo_modal_id("fixture", row["media"][1], 1)
        self.assertIn('href="#' + second_id + '"', first)
        self.assertIn('1 / 2', first)
        self.assertIn('loading="lazy"', first)
        self.assertIn('2 / 2', ui.render_observation_photo_modal(row, row["media"][1], 1))

    def test_optional_provenance_does_not_make_drafts_eligible(self):
        from rainmapper_core.mushroom_rebuild_pipeline import eligible_observation_ids
        from rainmapper_core.mushroom_ml_trainer import filter_eligible
        _, package = self.upload()
        row = package["rows"][0]["observation"]
        row.update(micro_area_id="fixture", prediction_target="favorable")
        self.assertEqual([], eligible_observation_ids([row]))
        self.assertEqual([], filter_eligible([row], self.species))
        row.update(validation_status="valid", calibration_use="include")
        self.assertEqual([row["observation_id"]], eligible_observation_ids([row]))
        self.assertEqual([row], filter_eligible([row], self.species))

    def test_trusted_context_and_custom_header_required_before_reading_upload(self):
        import sys
        from unittest.mock import Mock
        sys.path.insert(0, str(ROOT / "rainmapper-app/app"))
        import mushroom_gbif_ui as ui
        handler = Mock()
        handler.headers = {}
        ui.handle(handler, self.store, None, None)
        self.assertEqual(403, handler.send_json.call_args.args[0])
        handler.iter_artifact_request_body.assert_not_called()
        handler.headers = {"X-Rainmapper-GBIF": "1"}
        handler.trusted_worker_control_request.return_value = False
        handler.require_admin_api.return_value = None
        ui.handle(handler, self.store, None, None)
        handler.iter_artifact_request_body.assert_not_called()

    def test_cancel_after_failed_save_removes_only_unreferenced_new_media(self):
        token, package = self.upload()
        with patch.object(self.store, "replace", side_effect=OSError("disk failure")):
            self.assertRaises(OSError, gbif.commit, self.store, token, "owner", ["12345"], [])
        photo = self.store.data_dir / package["rows"][0]["observation"]["media"][0]["path"]
        self.assertTrue(photo.exists())
        gbif.cancel(self.store, token, "owner")
        self.assertFalse(photo.exists())
        self.assertEqual([], self.store.load("observations")["observations"])

    def plan_sites_fixture(self, records=None, *, dem_report=None):
        from rainmapper_core import mushroom_gbif_sites as sites
        token, package = self.upload(records)
        target = gbif.stage_path(self.store, token)
        for item in package['rows']:
            item['prepared'] = True
        gbif.write_json_atomic(target / 'preview.json', package)
        accepted = [i['gbif_id'] for i in package['rows']]
        plan = sites.plan(self.store, target, package, accepted, {}, [])
        report = {'dem_status': 'ok', 'altitude_min_m': 100, 'altitude_max_m': 120,
                  'altitude_mean_m': 110, 'gis': {'host_ids': []},
                  'slope_mean_deg': 2.3, 'slope_min_deg': 1.2, 'slope_max_deg': 3.4}
        if dem_report is not None:
            report = dem_report
        from rainmapper_core import mushroom_soilgrids as sg
        def soil_fixture(_root, geometry, *, ensure_missing):
            self.assertFalse(ensure_missing)
            return sg.pending_context(geometry, tile_ids=[], reasons=['fixture_no_coverage'])
        with patch('rainmapper_core.mushroom_gis_lab.derive_site_gis_dem', return_value=report), patch.object(sg, 'resolve_geometry_context', side_effect=soil_fixture):
            for change in plan['changes']:
                sites.prepare_site(self.store, target, plan['id'], change['id'])
        return token, target, accepted, plan

    def test_sites_batch_reuses_created_micro_and_expands_without_shrinking(self):
        import math
        from rainmapper_core import mushroom_gbif_sites as sites
        def record(gid, offset):
            return {'gbif_id': str(gid), 'lat': 42, 'lon': 2 + offset/(111320*math.cos(math.radians(42)))}
        result = sites.geometry_plan({'areas': [], 'micro_areas': []}, [record(3, 700), record(2, 498), record(1, 0)])
        self.assertEqual(1, len(result['sites']['areas']))
        self.assertEqual(2, len(result['sites']['micro_areas']))
        self.assertEqual(result['assignments']['2']['micro_area_id'], result['assignments']['3']['micro_area_id'])
        self.assertNotEqual(result['assignments']['1']['micro_area_id'], result['assignments']['2']['micro_area_id'])
        bounds = result['sites']['areas'][0]['derived_context']['geometry']['bbox']
        self.assertLess(bounds[0], 2)
        self.assertGreater(bounds[2], record(0, 990)['lon'])
        again = sites.geometry_plan({'areas': [], 'micro_areas': []}, [record(1, 0), record(2, 498), record(3, 700)])
        self.assertEqual(result['sites']['areas'][0]['geometry'], again['sites']['areas'][0]['geometry'])

    def test_sites_overlap_chooses_closest_containing_centre_and_keeps_ids(self):
        import math
        from rainmapper_core import mushroom_gbif_sites as sites
        records = [{'gbif_id': str(i), 'lat': 42, 'lon': 2+d/(111320*math.cos(math.radians(42)))} for i,d in ((1,0),(2,600),(3,400))]
        result = sites.geometry_plan({'areas': [], 'micro_areas': []}, records)
        self.assertEqual(2, len(result['sites']['areas']))
        self.assertEqual(result['assignments']['2']['micro_area_id'], result['assignments']['3']['micro_area_id'])
        self.assertEqual(2, len(result['assignments']['3']['candidates']))
        again = sites.geometry_plan(result['sites'], records)
        self.assertEqual([], again['changes'])

    def test_sites_manual_area_expands_preserves_origin_and_holes_are_not_membership(self):
        from rainmapper_core import mushroom_gbif_sites as sites
        base = sites.geometry_plan({'areas': [], 'micro_areas': []}, [{'gbif_id':'1','lat':42,'lon':2}])['sites']
        base['micro_areas'] = []
        area = base['areas'][0]
        area['provenance'] = {'source':'manual','creation_source':'manual'}
        area['name'] = 'Manual fixture'
        area['derived_context']['gis_dem'] = {'old': True}
        result = sites.geometry_plan(base, [{'gbif_id':'2','lat':42,'lon':2.003}])
        expanded = result['sites']['areas'][0]
        self.assertEqual('Manual fixture', expanded['name'])
        self.assertEqual('manual', expanded['provenance']['source'])
        self.assertNotIn('gis_dem', expanded['derived_context'])
        self.assertEqual('expanded', result['changes'][0]['action'])
        # A real polygon hole cannot capture a new observation.
        area['geometry'] = {'type':'Polygon','coordinates':[[[1,41],[3,41],[3,43],[1,43],[1,41]],[[1.9,41.9],[1.9,42.1],[2.1,42.1],[2.1,41.9],[1.9,41.9]]]}
        result = sites.geometry_plan(base, [{'gbif_id':'3','lat':42,'lon':2}])
        self.assertEqual(2, len(result['sites']['areas']))

    def test_sites_commit_persists_names_origin_and_does_not_change_uncertainty(self):
        token, target, accepted, plan = self.plan_sites_fixture()
        self.assertFalse((self.store.data_dir/'mushroom_known_sites.json').exists())
        result = gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'], site_names={'gbif_area_12345':'Municipio fixture'})
        sites = gbif.known_sites(self.store)
        self.assertEqual(1, result['areas_created'])
        self.assertEqual(1, result['micro_areas_created'])
        self.assertEqual('Municipio fixture', sites['areas'][0]['name'])
        self.assertEqual('gbif', sites['areas'][0]['provenance']['creation_source'])
        self.assertEqual('gbif', sites['micro_areas'][0]['provenance']['creation_source'])
        self.assertEqual('pending', sites['micro_areas'][0]['derived_context']['soilgrids_water']['status'])
        self.assertEqual('DEM: media 2.3°, rango 1.2°-3.4°', sites['micro_areas'][0]['topography']['slope_notes'])
        self.assertEqual(2.3, sites['micro_areas'][0]['derived_context']['gis_dem']['slope_mean_deg'])
        row = self.store.load('observations')['observations'][0]
        self.assertEqual(sites['micro_areas'][0]['micro_area_id'], row['micro_area_id'])
        self.assertEqual(500, row['location']['precision_m'])
        self.assertEqual('draft', row['validation_status'])
        self.assertEqual(result, gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id']))

    def test_sites_commit_preserves_zero_dem_slope(self):
        report = {'dem_status': 'ok', 'slope_mean_deg': 0.0, 'slope_min_deg': 0.0, 'slope_max_deg': 0.0}
        token, _, accepted, plan = self.plan_sites_fixture(dem_report=report)
        gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'])
        micro = gbif.known_sites(self.store)['micro_areas'][0]
        self.assertEqual('DEM: media 0.0°, rango 0.0°-0.0°', micro['topography']['slope_notes'])

    def test_sites_commit_without_dem_does_not_invent_slope_notes(self):
        token, _, accepted, plan = self.plan_sites_fixture(dem_report={'dem_status': 'unavailable'})
        gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'])
        micro = gbif.known_sites(self.store)['micro_areas'][0]
        self.assertEqual('', micro['topography']['slope_notes'])

    def test_sites_failed_observation_write_rolls_back_then_retries(self):
        token, target, accepted, plan = self.plan_sites_fixture()
        with patch.object(self.store, 'replace', side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):
                gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'])
        self.assertFalse((self.store.data_dir/'mushroom_known_sites.json').exists())
        self.assertEqual([], self.store.load('observations')['observations'])
        result = gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'])
        self.assertEqual(1, result['areas_created'])

    def test_sites_crash_after_site_write_cancel_rolls_back_only_our_sites(self):
        from rainmapper_core import mushroom_gbif_sites as sites
        token, target, accepted, plan = self.plan_sites_fixture()
        internal = gbif.strict_json((target/'sites-plan.json').read_bytes())
        sites.install(self.store, target, internal)
        self.assertTrue((self.store.data_dir/'mushroom_known_sites.json').exists())
        gbif.cancel(self.store, token, 'owner')
        self.assertFalse((self.store.data_dir/'mushroom_known_sites.json').exists())

    def test_sites_plan_detects_concurrent_geometry_and_selection_changes(self):
        token, target, accepted, plan = self.plan_sites_fixture()
        from rainmapper_core import mushroom_gbif_sites as sites
        with self.assertRaisesRegex(ValueError, 'changed'):
            sites.apply_plan(self.store, target, plan['id'], [], {}, [], {})
        gbif.write_json_atomic(self.store.data_dir/'mushroom_known_sites.json', {'areas':[], 'micro_areas':[], 'metadata':{'fixture':'concurrent'}})
        with self.assertRaisesRegex(ValueError, 'changed'):
            gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'])
        self.assertEqual([], self.store.load('observations')['observations'])

    def test_sites_archived_zones_are_not_reused_and_municipality_names_are_distinct(self):
        from rainmapper_core import mushroom_gbif_sites as sites
        record = {'gbif_id':'1', 'lat':42, 'lon':2, 'municipality':'Municipio fixture'}
        first = sites.geometry_plan({'areas':[], 'micro_areas':[]}, [record])
        self.assertIn('Municipio fixture', first['sites']['areas'][0]['name'])
        first['sites']['areas'][0]['archived'] = True
        result = sites.geometry_plan(first['sites'], [record])
        self.assertEqual(2, len(result['sites']['areas']))
        self.assertNotEqual(first['assignments']['1']['micro_area_id'], result['assignments']['1']['micro_area_id'])


    def test_site_provenance_survives_manual_edit_and_remains_visible(self):
        import sys
        sys.path.insert(0, str(ROOT / 'rainmapper-app/app'))
        import web_server as web
        import mushroom_known_sites_ui as ui
        from rainmapper_core import mushroom_known_sites as known
        micro = known.empty_micro_area('fixture_micro', 'fixture_area')
        micro['provenance'] = {'source':'gbif_import', 'creation_source':'gbif',
                               'gbif_creation':{'gbif_id':'12345'}, 'import_token':'a'*32}
        edited = web.known_site_micro_area_from_form({'micro_area_id':['fixture_micro'], 'area_id':['fixture_area'],
                          'name':['Renamed'], 'provenance_source':['manual edit']}, micro)
        self.assertEqual('gbif', edited['provenance']['creation_source'])
        self.assertEqual('12345', edited['provenance']['gbif_creation']['gbif_id'])
        self.assertIn('GBIF', ui._creation_origin(edited))

    def test_site_crash_after_observation_write_keeps_zones_on_cancel(self):
        token, target, accepted, plan = self.plan_sites_fixture()
        real_write = gbif.write_json_atomic
        def fail_receipt(path, payload):
            if path.name == 'state.json' and payload.get('status') == 'complete':
                raise OSError('fixture crash after commit')
            return real_write(path, payload)
        with patch.object(gbif, 'write_json_atomic', side_effect=fail_receipt):
            with self.assertRaises(OSError):
                gbif.commit(self.store, token, 'owner', accepted, [], sites_plan_id=plan['id'])
        gbif.cancel(self.store, token, 'owner')
        self.assertEqual(1, len(gbif.known_sites(self.store)['micro_areas']))
        self.assertEqual(1, len(self.store.load('observations')['observations']))


if __name__ == "__main__":
    unittest.main()
