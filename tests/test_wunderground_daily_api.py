import unittest
from datetime import date, datetime, timezone

from rainmapper_core.sources.wunderground.daily_api import (
    WundergroundDailyApiError,
    build_monthly_rows,
    cache_encodings,
    fetch_daily_observations,
    inch_to_mm,
    monthly_query_date_range,
    query_date_range,
    station_id_from_url,
)


class FakeResponse:
    status_code = 200

    def __init__(self, observation):
        self.observation = observation

    def json(self):
        return {"observations": [self.observation]}


class FakeSession:
    def __init__(self, observations):
        self.responses = [FakeResponse(observation) for observation in observations]
        self.encodings = []

    def get(self, _url, *, params, headers, timeout):
        self.encodings.append(headers["Accept-Encoding"])
        return self.responses.pop(0)


def observation_at(utc_text):
    epoch = datetime.fromisoformat(utc_text.replace("Z", "+00:00")).timestamp()
    return {
        "epoch": epoch,
        "obsTimeUtc": utc_text,
        "obsTimeLocal": utc_text.replace("T", " ").replace("Z", ""),
        "imperial": {"precipTotal": 0},
    }


class WundergroundDailyApiTest(unittest.TestCase):
    def test_cache_encoding_order_requires_one_complete_permutation(self):
        self.assertEqual(
            cache_encodings("deflate,gzip,identity"),
            ("deflate", "gzip", "identity"),
        )
        with self.assertRaisesRegex(WundergroundDailyApiError, "exactly once"):
            cache_encodings("gzip,gzip,identity")
        with self.assertRaisesRegex(WundergroundDailyApiError, "exactly once"):
            cache_encodings("gzip,,identity,deflate")

    def test_station_id_from_url_normalizes_case(self):
        self.assertEqual(
            station_id_from_url("https://www.wunderground.com/dashboard/pws/IORDiN1"),
            "IORDIN1",
        )

    def test_inch_to_mm_matches_wunderground_metric_display(self):
        self.assertEqual(inch_to_mm(1.82), 46.23)

    def test_weekly_query_uses_seven_inclusive_days_across_month_boundary(self):
        self.assertEqual(
            query_date_range(date(2026, 8, 1), date(2026, 9, 3), weekly=True),
            (date(2026, 8, 28), date(2026, 9, 3)),
        )

    def test_monthly_query_preserves_requested_range(self):
        self.assertEqual(
            query_date_range(date(2026, 8, 1), date(2026, 9, 3), weekly=False),
            (date(2026, 8, 1), date(2026, 9, 3)),
        )

    def test_monthly_refresh_uses_current_calendar_month_after_first_week(self):
        self.assertEqual(
            monthly_query_date_range(
                date(2026, 9, 3),
                date(2026, 9, 10),
                explicit_dates=False,
            ),
            (date(2026, 9, 1), date(2026, 9, 10)),
        )

    def test_monthly_refresh_also_revisits_previous_month_during_first_week(self):
        self.assertEqual(
            monthly_query_date_range(
                date(2026, 8, 29),
                date(2026, 9, 4),
                explicit_dates=False,
            ),
            (date(2026, 8, 1), date(2026, 9, 4)),
        )

    def test_monthly_backfill_preserves_explicit_dates(self):
        self.assertEqual(
            monthly_query_date_range(
                date(2025, 2, 12),
                date(2025, 4, 18),
                explicit_dates=True,
            ),
            (date(2025, 2, 12), date(2025, 4, 18)),
        )

    def test_fresh_preferred_response_does_not_retry_cache_variants(self):
        session = FakeSession([
            observation_at("2026-09-09T20:30:00Z"),
        ])
        diagnostics = {}

        observations = fetch_daily_observations(
            "IOLVAN3",
            date(2026, 9, 1),
            date(2026, 9, 9),
            session=session,
            api_key="test",
            diagnostics=diagnostics,
            now_utc=datetime(2026, 9, 9, 22, 0, tzinfo=timezone.utc),
            today=date(2026, 9, 9),
        )

        self.assertEqual(session.encodings, ["gzip"])
        self.assertEqual(observations[-1]["obsTimeUtc"], "2026-09-09T20:30:00Z")
        self.assertFalse(diagnostics["cache_retry_attempted"])
        self.assertFalse(diagnostics["cache_recovered"])
        self.assertFalse(diagnostics["stale_after_retries"])

    def test_stale_preferred_response_uses_fresher_second_variant(self):
        session = FakeSession([
            observation_at("2026-09-09T01:44:50Z"),
            observation_at("2026-09-09T21:00:00Z"),
        ])
        diagnostics = {}

        observations = fetch_daily_observations(
            "IOLVAN3",
            date(2026, 9, 1),
            date(2026, 9, 9),
            session=session,
            api_key="test",
            diagnostics=diagnostics,
            now_utc=datetime(2026, 9, 9, 22, 0, tzinfo=timezone.utc),
            today=date(2026, 9, 9),
        )

        self.assertEqual(session.encodings, ["gzip", "identity"])
        self.assertEqual(observations[-1]["obsTimeUtc"], "2026-09-09T21:00:00Z")
        self.assertTrue(diagnostics["cache_retry_attempted"])
        self.assertTrue(diagnostics["cache_recovered"])
        self.assertEqual(diagnostics["selected_encoding"], "identity")
        self.assertFalse(diagnostics["stale_after_retries"])

    def test_all_old_variants_are_reported_and_newest_is_kept(self):
        session = FakeSession([
            observation_at("2026-09-09T01:00:00Z"),
            observation_at("2026-09-09T01:30:00Z"),
            observation_at("2026-09-09T02:00:00Z"),
        ])
        diagnostics = {}

        observations = fetch_daily_observations(
            "IOLVAN3",
            date(2026, 9, 1),
            date(2026, 9, 9),
            session=session,
            api_key="test",
            diagnostics=diagnostics,
            now_utc=datetime(2026, 9, 9, 22, 0, tzinfo=timezone.utc),
            today=date(2026, 9, 9),
        )

        self.assertEqual(session.encodings, ["gzip", "identity", "deflate"])
        self.assertEqual(observations[-1]["obsTimeUtc"], "2026-09-09T02:00:00Z")
        self.assertEqual(diagnostics["selected_encoding"], "deflate")
        self.assertTrue(diagnostics["stale_after_retries"])

    def test_recent_previous_day_timestamp_is_fresh_across_midnight(self):
        session = FakeSession([
            observation_at("2026-09-09T23:30:00Z"),
        ])
        diagnostics = {}

        fetch_daily_observations(
            "IOLVAN3",
            date(2026, 9, 1),
            date(2026, 9, 10),
            session=session,
            api_key="test",
            diagnostics=diagnostics,
            now_utc=datetime(2026, 9, 10, 0, 30, tzinfo=timezone.utc),
            today=date(2026, 9, 10),
        )

        self.assertEqual(session.encodings, ["gzip"])
        self.assertFalse(diagnostics["stale_after_retries"])

    def test_fetch_uses_explicit_configured_encoding_order(self):
        session = FakeSession([
            observation_at("2026-09-09T20:30:00Z"),
        ])

        fetch_daily_observations(
            "IOLVAN3",
            date(2026, 9, 1),
            date(2026, 9, 9),
            session=session,
            api_key="test",
            now_utc=datetime(2026, 9, 9, 22, 0, tzinfo=timezone.utc),
            today=date(2026, 9, 9),
            encoding_order=("deflate", "identity", "gzip"),
        )

        self.assertEqual(session.encodings, ["deflate"])

    def test_build_monthly_rows_maps_precipitation_and_weather_fields(self):
        rows = build_monthly_rows(
            [
                {
                    "obsTimeLocal": "2026-07-10 19:39:52",
                    "humidityHigh": 88,
                    "humidityAvg": 54.9,
                    "humidityLow": 19,
                    "imperial": {
                        "tempHigh": 91.4,
                        "tempAvg": 66,
                        "tempLow": 53.2,
                        "dewptHigh": 61.2,
                        "dewptAvg": 47,
                        "dewptLow": 41.7,
                        "windspeedHigh": 9.6,
                        "windspeedAvg": 1,
                        "windspeedLow": 0,
                        "pressureMax": 30.08,
                        "pressureMin": 29.97,
                        "precipTotal": 1.82,
                    },
                }
            ],
            "IORDIN1",
            "La Cortinada",
            "Ordino",
            "1344",
            42.571926,
            1.519332,
        )

        self.assertEqual(rows[0]["Date"], "2026-07-10")
        self.assertEqual(rows[0]["StationID"], "IORDIN1")
        self.assertEqual(rows[0]["Sum"], 46.23)
        self.assertEqual(rows[0]["High"], 33.0)
        self.assertEqual(rows[0]["High_3"], 15.45)


if __name__ == "__main__":
    unittest.main()
