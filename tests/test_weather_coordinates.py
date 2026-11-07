import json
import os
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import pandas as pd
import pyarrow.parquet as pq

from rainmapper_core import weather_coordinates as coords
from rainmapper_core.geojson import dataframe_to_geojson
from rainmapper_core.weather_history_dataset import resolve_weather_generation, sha256_file
from rainmapper_core.weather_history_archive import archive_and_close_pending
from rainmapper_core.weather_history_capture import capture_fresh_weather_rows
from rainmapper_core.weather_history_writer import archive_pending_batches, acknowledge_archived_pending, InjectedWeatherHistoryFailure
from tests import test_weather_history_writer as fixtures


class CoordinateProtectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WeatherHistoryWriterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.data = self.fixture.data_dir

    def frame(self, code="A", lat=42.0, lon=2.0):
        return pd.DataFrame([{"Codi Estació": code, "Estació": "Station", "Latitud": lat, "Longitud": lon,
                             "Altitud": 17.0, "Municipi": "Received town", "Total": 9.5, "Data Local": "20260101"}])

    def catalog(self):
        g = resolve_weather_generation(self.data, verify_hashes=True)
        return {(r["source"], r["station_code"]): r for r in pq.read_table(g.object_path(g.catalog.path)).to_pylist()}

    def test_successive_jumps_do_not_move_anchor_or_weather_and_only_raw_metadata_heals(self):
        for lat in (42.05, 42.08, 42.08):
            frame = self.frame(lat=lat)
            out = coords.protect_frame(self.data, "meteocat", frame, fresh=True)
            self.assertEqual((out.iloc[0].Latitud, out.iloc[0].Longitud, out.iloc[0].Total), (42, 2, 9.5))
            self.assertEqual(out.iloc[0].Altitud, 700)
            self.assertTrue(pd.isna(out.iloc[0].Municipi))
        e = coords.review(self.data, "meteocat", "A")
        since = e["first_seen"]
        coords.protect_frame(self.data, "meteocat", self.frame(), fresh=False)
        self.assertEqual(coords.review(self.data, "meteocat", "A")["first_seen"], since)
        self.assertEqual(e["accepted"]["lat"], 42)
        self.assertEqual(e["received"]["lat"], 42.08)
        coords.protect_frame(self.data, "meteocat", self.frame(lat=42.005), fresh=True)
        self.assertNotIn("meteocat:A", coords.read_state(self.data)["exceptions"])
        self.assertEqual(self.catalog()["meteocat", "A"]["lat"], 42)

    def test_sources_are_independent_and_new_sources_use_same_policy(self):
        for source in ["aemet", "meteoclimatic", "wunderground", "future_source"]:
            with coords.transaction(self.data) as state:
                state["accepted_moves"][coords.station_key(source, "A")] = {"lat": 41, "lon": 1}
            out = coords.protect_frame(self.data, source, self.frame(lat=49), fresh=True)
            self.assertEqual(out.iloc[0].Latitud, 41)
        out = coords.protect_frame(self.data, "meteocat", self.frame(lat=42.1), fresh=True)
        self.assertEqual(out.iloc[0].Latitud, 42)
        self.assertEqual(len(coords.read_state(self.data)["exceptions"]), 5)
        self.assertEqual(coords.station_key("AEMET", "AEMET:123"), "aemet:AEMET:123")

    def test_older_hourly_outlier_cannot_reinfect_a_recovered_latest_location(self):
        old = self.frame(lat=49).assign(**{"Data Lectura": "2026-01-01 01:00:00"})
        new = self.frame().assign(**{"Data Lectura": "2026-01-01 02:00:00"})
        coords.protect_frame(self.data, "meteocat", old, fresh=True)
        corrected = coords.protect_frame(self.data, "meteocat", pd.concat([new, old], ignore_index=True), fresh=True)
        self.assertEqual(list(corrected.Latitud), [42, 42])
        self.assertEqual(list(corrected.Total), [9.5, 9.5])
        self.assertFalse(coords.read_state(self.data)["exceptions"])

    def test_rebuilt_old_metadata_is_corrected_without_creating_a_new_provider_incident(self):
        out = coords.protect_frame(self.data, "meteocat", self.frame(lat=49))
        self.assertEqual(out.iloc[0].Latitud, 42)
        self.assertFalse(coords.read_state(self.data)["exceptions"])

    def test_text_location_metadata_survives_correction_and_real_parquet_capture(self):
        for source, fields in [("meteoclimatic", ("Latitud", "Longitud", "Altitud")),
                               ("meteocat", ("Altitud",))]:
            with self.subTest(source=source):
                with coords.transaction(self.data) as state:
                    state["accepted_moves"][source + ":A"] = {"lat": 42., "lon": 2., "altitude": 700.}
                frame = pd.concat([self.frame("B", lat=42), self.frame("A", lat=49)], ignore_index=True)
                for field in fields:
                    frame[field] = frame[field].astype(str).str.replace(".", ",", regex=False)
                original = frame.copy(deep=True)
                guarded = coords.protect_frame(self.data, source, frame, fresh=True)
                pd.testing.assert_frame_equal(frame, original)
                pd.testing.assert_series_equal(guarded.Total, original.Total)
                self.assertEqual(list(guarded.Latitud), [42., 42.])
                self.assertEqual(list(guarded.Altitud), [17., 700.])
                self.assertTrue(all(pd.api.types.is_numeric_dtype(guarded[name])
                                    for name in ("Latitud", "Longitud", "Altitud")))
                with mock.patch.dict(os.environ, {"RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true"}):
                    pending = capture_fresh_weather_rows(self.data, source, guarded, chunk_rows=1)
                rows = {row["station_code"]: row for row in pq.ParquetFile(pending.data_path).read().to_pylist()}
                self.assertEqual(len(rows), 2)
                self.assertEqual((rows["A"]["lat"], rows["A"]["altitude"], rows["A"]["rain_mm"]), (42, 700, 9.5))
                self.assertEqual(rows["B"]["rain_mm"], 9.5)

    def test_mixed_location_types_are_normalized_even_without_a_coordinate_change(self):
        frame = pd.concat([self.frame("B"), self.frame("C")], ignore_index=True)
        for field in ("Latitud", "Longitud", "Altitud"):
            frame[field] = frame[field].astype(object)
            frame.loc[0, field] = str(frame.loc[0, field]).replace(".", ",")
        with mock.patch.dict(os.environ, {"RAINMAPPER_PARTITIONED_WEATHER_HISTORY": "true"}):
            pending = capture_fresh_weather_rows(self.data, "meteocat", frame)
        rows = pq.ParquetFile(pending.data_path).read().to_pylist()
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["rain_mm"] for row in rows], [9.5, 9.5])
        self.assertFalse(coords.read_state(self.data)["exceptions"])

    def test_empty_text_location_columns_accept_known_metadata_without_dtype_warning(self):
        with coords.transaction(self.data) as state:
            state['accepted_moves']['future_source:X'] = {
                'lat': 42., 'lon': 2., 'municipality': 'Accepted town', 'province': 'Accepted province',
            }
        frame = self.frame('X', lat=49).assign(Municipi=float('nan'), Provincia=float('nan'),
                                             Comarca=float('nan'))
        original = frame.copy(deep=True)
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            result = coords.protect_frame(self.data, 'future_source', frame, fresh=True)
        pd.testing.assert_frame_equal(frame, original)
        pd.testing.assert_series_equal(result.Total, original.Total)
        self.assertEqual((result.iloc[0].Latitud, result.iloc[0].Longitud), (42., 2.))
        self.assertEqual(result.iloc[0].Municipi, 'Accepted town')
        self.assertEqual(result.iloc[0].Provincia, 'Accepted province')
        self.assertTrue(pd.isna(result.iloc[0].Comarca))

    def test_legacy_entry_heals_with_comments_preserved(self):
        path = self.data.parent / coords.LEGACY_FILE
        path.write_text("# operator note\nCODE 42 2 # reason\nOTHER 41 1\n")
        coords.protect_frame(self.data, "meteoclimatic", self.frame("CODE", lat=49), fresh=True)
        e = coords.review(self.data, "meteoclimatic", "CODE")
        self.assertTrue(e["legacy_age_unknown"])
        coords.protect_frame(self.data, "meteoclimatic", self.frame("CODE"), fresh=True)
        self.assertEqual(coords.load_fixed_coordinates(self.data), {"OTHER": {"lat": 41, "lon": 1}})
        self.assertIn("# operator note", path.read_text())
        self.assertIn("# reason", path.read_text())
        self.assertFalse(coords.read_state(self.data)["exceptions"])

    def test_acceptance_is_exact_idempotent_and_applied_at_next_boundary(self):
        coords.protect_frame(self.data, "meteocat", self.frame(lat=42.05), fresh=True)
        old = coords.review(self.data, "meteocat", "A")
        coords.protect_frame(self.data, "meteocat", self.frame(lat=42.08), fresh=True)
        with self.assertRaises(LookupError):
            coords.approve(self.data, "meteocat", "A", old["revision"], "carlos")
        current = coords.review(self.data, "meteocat", "A")
        for _ in range(2):
            coords.approve(self.data, "meteocat", "A", current["revision"], "carlos")
        self.assertEqual(len([e for e in coords.read_state(self.data)["audit"] if e["event"] == "approved"]), 1)
        self.assertEqual(self.catalog()["meteocat", "A"]["lat"], 42)
        coords.activate_approvals(self.data)
        # Older pending dates must not prevent an explicitly accepted relocation.
        pending = self.fixture._pending([self.fixture.row("meteocat", "A", "20251230", 8, lat=42.08)])
        archive_pending_batches(self.data, reserve_bytes=0)
        self.assertEqual(self.catalog()["meteocat", "A"]["lat"], 42.08)
        self.assertEqual(self.catalog()["meteocat", "A"]["metadata_date"], "20251231")
        self.assertFalse(coords.read_state(self.data)["exceptions"])
        acknowledge_archived_pending(self.data, pending.batch_id)
        out = coords.protect_frame(self.data, "meteocat", self.frame(lat=42.08), fresh=True)
        self.assertEqual(out.iloc[0].Latitud, 42.08)
        self.assertFalse(coords.read_state(self.data)["exceptions"])

    def test_pending_archive_and_crash_replay_use_same_location(self):
        pending = self.fixture._pending([self.fixture.row("meteocat", "A", "20260101", 12, lat=48, altitude=90)])
        digest = sha256_file(pending.data_path)
        with self.assertRaises(InjectedWeatherHistoryFailure):
            archive_pending_batches(self.data, reserve_bytes=0, fail_after="current")
        self.assertEqual(self.catalog()["meteocat", "A"]["lat"], 42)
        self.assertEqual(sha256_file(pending.data_path), digest)
        # Change live policy after CURRENT: replay must use committed receipts.
        coords.protect_frame(self.data, "meteocat", self.frame(), fresh=True)
        with mock.patch.dict(os.environ, {"RAINMAPPER_WEATHER_REFERENCE_DAY": "2026-01-02"}):
            report = archive_and_close_pending(self.data)
        self.assertEqual(report["acknowledged_batch_ids"], [pending.batch_id])
        row = pd.read_csv(self.data / "Meteocat_incremental.csv", decimal=",").iloc[0]
        self.assertEqual((row.Latitud, row.Altitud, row.Total), (42, 700, 12))
        self.assertFalse(coords.read_state(self.data)["exceptions"])

    def test_invalid_new_location_is_unlocated_and_not_fabricated(self):
        for lat in (49, float("nan")):
            out = coords.protect_frame(self.data, "meteocat", self.frame("NEW", lat=lat), fresh=True)
            self.assertTrue(pd.isna(out.iloc[0].Latitud))
            self.assertEqual(out.iloc[0].Total, 9.5)
        self.assertIsNone(coords.review(self.data, "meteocat", "NEW")["accepted"])
        coords.protect_frame(self.data, "meteocat", self.frame("NEW"), fresh=True)
        self.assertNotIn("meteocat:NEW", coords.read_state(self.data)["exceptions"])

    def test_geojson_uses_accepted_point_and_minimal_flag_then_removes_it(self):
        frame = self.frame(lat=49).assign(Source="Meteocat")
        coords.protect_frame(self.data, "meteocat", frame, fresh=True)
        exceptions = coords.read_state(self.data)["exceptions"]
        feature = dataframe_to_geojson(frame, coordinate_exceptions=exceptions)["features"][0]
        self.assertEqual(feature["geometry"]["coordinates"], [2, 42])
        self.assertTrue(feature["properties"]["coordinate_exception"])
        self.assertNotIn("received", json.dumps(feature))
        coords.protect_frame(self.data, "meteocat", self.frame(), fresh=True)
        feature = dataframe_to_geojson(self.frame(), coordinate_exceptions=coords.read_state(self.data)["exceptions"])["features"][0]
        self.assertNotIn("coordinate_exception", feature["properties"])

    def test_parallel_source_updates_preserve_all_exceptions_and_log_groups(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(coords.protect_frame, self.data, source, self.frame(code, lat=48), fresh=True)
                       for source, code in [("meteocat", "A"), ("wunderground", "W")]]
            for future in futures:
                future.result()
        state = coords.read_state(self.data)
        self.assertEqual(len(state["exceptions"]), 2)
        log = coords.summary(self.data)
        self.assertEqual(log.count("=== Coordenadas"), 1)
        self.assertIn("meteocat: 1 excepciones", log)
        self.assertIn("wunderground: 1 excepciones", log)
        self.assertLess((self.data / coords.STATE_FILE).stat().st_size, 4096)


class CoordinateApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_web_server_auth import load_web_server_module
        cls.web = load_web_server_module()

    def handler(self, user):
        handler = object.__new__(self.web.RainmapperHandler)
        handler.authenticated_user = mock.Mock(return_value=user)
        handler.send_json = mock.Mock()
        handler.path = "/api/weather/coordinates?source=meteocat&station_code=A"
        handler.read_json_payload = mock.Mock(return_value={"source": "meteocat", "station_code": "A", "revision": "old"})
        return handler

    def test_reads_and_writes_require_authenticated_administrator_on_server(self):
        for user, expected in [(None, 401), ({"role": "free"}, 403), ({"role": "pro"}, 403)]:
            for accept in (True, False):
                h = self.handler(user)
                with mock.patch.object(coords, "approve") as approve, mock.patch.object(coords, "review") as review:
                    h.coordinate_api(accept=accept)
                self.assertEqual(h.send_json.call_args.args[0], expected)
                approve.assert_not_called(); review.assert_not_called()

    def test_stale_candidate_returns_conflict_and_post_is_bounded(self):
        h = self.handler({"role": "admin", "username": "carlos"})
        with mock.patch.object(coords, "approve", side_effect=LookupError("changed")):
            h.coordinate_api(accept=True)
        self.assertEqual(h.send_json.call_args.args[0], 409)
        h.path = "/api/weather/coordinates/accept"
        self.assertEqual(h.request_body_limit(), 2048)


if __name__ == "__main__":
    unittest.main()
