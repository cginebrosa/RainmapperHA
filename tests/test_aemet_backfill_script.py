import importlib.util
import unittest
from pathlib import Path

import pandas as pd


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "aemet-backfill-30-days.py"
SPEC = importlib.util.spec_from_file_location("aemet_backfill_30_days", SCRIPT_PATH)
aemet_backfill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aemet_backfill)


class AemetBackfillScriptTests(unittest.TestCase):
    def test_parse_aemet_dms_coordinates(self):
        self.assertEqual(aemet_backfill.parse_aemet_dms("413515N"), 41.5875)
        self.assertEqual(aemet_backfill.parse_aemet_dms("0021031E"), 2.175278)
        self.assertEqual(aemet_backfill.parse_aemet_dms("0034210W"), -3.702778)
        self.assertTrue(pd.isna(aemet_backfill.parse_aemet_dms("")))

    def test_parse_aemet_precipitation_handles_decimal_comma_and_trace(self):
        self.assertEqual(aemet_backfill.parse_aemet_precipitation("12,4"), 12.4)
        self.assertEqual(aemet_backfill.parse_aemet_precipitation("Ip"), 0.0)
        self.assertTrue(pd.isna(aemet_backfill.parse_aemet_precipitation("")))

    def test_build_daily_incremental_from_climatology_uses_station_catalog_metadata(self):
        rows = [
            {
                "fecha": "2026-06-20",
                "indicativo": "9632X",
                "nombre": "REUS AEROPUERTO",
                "provincia": "TARRAGONA",
                "prec": "7,5",
                "tmax": "26,1",
                "tmin": "14,2",
            },
            {
                "fecha": "2026-06-20",
                "indicativo": "BAD",
                "prec": "",
            },
        ]
        stations = pd.DataFrame(
            [
                {
                    "Codi Estació": "AEMET:9632X",
                    "aemet_id": "9632X",
                    "Estació": "Reus Aeroport",
                    "Comarca": "Baix Camp",
                    "Municipi": "Reus",
                    "Provincia": "Tarragona",
                    "Altitud": 71,
                    "Latitud": 41.147,
                    "Longitud": 1.167,
                }
            ],
            columns=aemet_backfill.STATION_COLUMNS,
        )

        result = aemet_backfill.build_daily_incremental_from_climatology(rows, stations)

        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row["Codi Estació"], "AEMET:9632X")
        self.assertEqual(row["Data Local"], "20260620")
        self.assertEqual(row["Hora Local"], "23:59:00")
        self.assertEqual(row["Total"], 7.5)
        self.assertEqual(row["Estació"], "Reus Aeroport")
        self.assertEqual(row["Municipi"], "Reus")
        self.assertEqual(row["max_temp_celsius"], 26.1)
        self.assertEqual(row["min_temp_celsius"], 14.2)

    def test_merge_station_catalog_preserves_existing_enriched_fields(self):
        inventory = pd.DataFrame(
            [
                {
                    "Codi Estació": "AEMET:9632X",
                    "aemet_id": "9632X",
                    "Estació": "REUS AEROPUERTO",
                    "Comarca": "",
                    "Municipi": "",
                    "Provincia": "TARRAGONA",
                    "Altitud": 71,
                    "Latitud": 41.147,
                    "Longitud": 1.167,
                }
            ],
            columns=aemet_backfill.STATION_COLUMNS,
        )
        existing = pd.DataFrame(
            [
                {
                    "Codi Estació": "AEMET:9632X",
                    "aemet_id": "9632X",
                    "Estació": "Reus Aeroport",
                    "Comarca": "Baix Camp",
                    "Municipi": "Reus",
                    "Provincia": "Tarragona",
                    "Altitud": 71,
                    "Latitud": 41.147,
                    "Longitud": 1.167,
                }
            ],
            columns=aemet_backfill.STATION_COLUMNS,
        )

        result = aemet_backfill.merge_station_catalog(inventory, existing)

        row = result.iloc[0]
        self.assertEqual(row["Estació"], "Reus Aeroport")
        self.assertEqual(row["Comarca"], "Baix Camp")
        self.assertEqual(row["Municipi"], "Reus")
        self.assertEqual(row["Provincia"], "Tarragona")

    def test_merge_existing_incremental_keeps_backfill_for_duplicate_station_day(self):
        existing = pd.DataFrame(
            [
                {
                    "Codi Estació": "AEMET:9632X",
                    "Data Lectura": "2026-06-20 23:59:00",
                    "Estació": "Old",
                    "Comarca": "",
                    "Municipi": "",
                    "Provincia": "",
                    "Altitud": "",
                    "Latitud": "",
                    "Longitud": "",
                    "Ultima Lectura": "2026/06/20 23:59:00",
                    "Variable": "Precipitacion",
                    "Total": 1.0,
                    "Unitat": "mm",
                    "Data Local": "20260620",
                    "Hora Local": "23:59:00",
                    "max_temp_celsius": pd.NA,
                    "min_temp_celsius": pd.NA,
                    "max_humidity_percent": pd.NA,
                    "min_humidity_percent": pd.NA,
                }
            ],
            columns=aemet_backfill.DAILY_COLUMNS,
        )
        backfill = existing.copy()
        backfill.at[0, "Estació"] = "New"
        backfill.at[0, "Total"] = 5.0

        result = aemet_backfill.merge_existing_incremental(backfill, existing)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Estació"], "New")
        self.assertEqual(result.iloc[0]["Total"], 5.0)


if __name__ == "__main__":
    unittest.main()
