import unittest
from datetime import date

import pandas as pd

from rainmapper_core.weather_official_backfill import (
    fetch_aemet_climatology,
    fetch_meteocat_block,
    normalize_aemet_climatology,
    normalize_meteocat_block,
)


class FakeMeteocatClient:
    def __init__(self):
        self.queries = []

    def get(self, dataset, **kwargs):
        self.queries.append((dataset, kwargs["query"]))
        if "codi_variable in ('35')" in kwargs["query"]:
            return [
                {
                    "codi_estacio": "CR",
                    "ultima_lectura": "2026-01-01T00:00:00.000",
                    "codi_variable": "35",
                    "valor_variable": "0",
                }
            ]
        return [
            {
                "codi_estacio": "CR",
                "ultima_lectura": "2026-01-02T00:00:00.000",
                "codi_variable": "3",
                "max_valor_variable": "90",
                "min_valor_variable": "40",
            }
        ]


class WeatherOfficialBackfillTests(unittest.TestCase):
    def test_aemet_fetch_uses_index_then_data_and_preserves_condition_only(self):
        calls = []

        def fetcher(url, **kwargs):
            calls.append((url, kwargs))
            if len(calls) == 1:
                return {"estado": 200, "datos": "https://example.test/data"}
            return [
                {
                    "indicativo": "0092X",
                    "fecha": "2013-09-24",
                    "tmax": "24,3",
                    "tmin": "12,5",
                    "hrMax": "90",
                    "hrMin": "54",
                }
            ]

        raw = fetch_aemet_climatology(
            date(2013, 9, 24),
            date(2013, 9, 24),
            api_key="test",
            fetcher=fetcher,
        )
        frame = normalize_aemet_climatology(raw, pd.DataFrame())
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(frame), 1)
        self.assertTrue(pd.isna(frame.iloc[0]["Total"]))
        self.assertEqual(frame.iloc[0]["max_humidity_percent"], 90.0)

    def test_meteocat_fetches_two_queries_and_keeps_union(self):
        client = FakeMeteocatClient()
        rain, conditions = fetch_meteocat_block(
            date(2026, 1, 1),
            date(2026, 1, 2),
            client=client,
            pause_seconds=0,
        )
        frame = normalize_meteocat_block(rain, conditions, pd.DataFrame())
        self.assertEqual(len(client.queries), 2)
        self.assertEqual(set(frame["Data Local"]), {"20260101", "20260102"})
        dry = frame.loc[frame["Data Local"] == "20260101"].iloc[0]
        humid = frame.loc[frame["Data Local"] == "20260102"].iloc[0]
        self.assertEqual(dry["Total"], "0")
        self.assertTrue(pd.isna(humid["Total"]))
        self.assertEqual(humid["max_humidity_percent"], "90")

    def test_both_sources_reject_more_than_fifteen_days(self):
        with self.assertRaisesRegex(ValueError, "15 days"):
            fetch_aemet_climatology(
                date(2026, 1, 1),
                date(2026, 1, 16),
                api_key="test",
            )
        with self.assertRaisesRegex(ValueError, "15 days"):
            fetch_meteocat_block(
                date(2026, 1, 1),
                date(2026, 1, 16),
                client=FakeMeteocatClient(),
                pause_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()
