import unittest
from datetime import date
from tempfile import TemporaryDirectory

import pandas as pd

from rainmapper_core.meteoclimatic_history import (
    build_meteoclimatic_daily_incremental,
    read_meteoclimatic_observations,
    retain_meteoclimatic_observations,
    update_meteoclimatic_observations,
)
from rainmapper_core.incremental_upsert import upsert_incremental


def observation(station, timestamp, wind_avg, wind_gust, direction, rain=0.0):
    ts = pd.Timestamp(timestamp)
    return {
        "Codi Estació": station,
        "Data Lectura": ts,
        "Estació": "Station",
        "Comarca": "Comarca",
        "Municipi": "Municipi",
        "Provincia": "Provincia",
        "Altitud": "100",
        "Latitud": "41.0",
        "Longitud": "2.0",
        "Ultima Lectura": ts.strftime("%Y/%m/%d %H:%M:%S"),
        "Variable": "Precipitació",
        "Total": rain,
        "Unitat": "mm",
        "max_temp_celsius": 20.0,
        "min_temp_celsius": 10.0,
        "max_humidity_percent": 80.0,
        "min_humidity_percent": 40.0,
        "Data Local": ts.strftime("%Y%m%d"),
        "Hora Local": ts.strftime("%H:%M:%S"),
        "wind_avg_kmh": wind_avg,
        "wind_gust_kmh": wind_gust,
        "wind_direction_deg": direction,
    }


class MeteoclimaticHistoryTest(unittest.TestCase):
    def test_update_observations_deduplicates_by_station_and_timestamp(self):
        old = pd.DataFrame([observation("ES1", "2026-06-24 08:00:00", 4, 10, 350)])
        current = pd.DataFrame([
            observation("ES1", "2026-06-24 08:00:00", 5, 11, 355),
            observation("ES1", "2026-06-24 11:00:00", 7, 15, 10),
        ])

        result = update_meteoclimatic_observations(current, old)

        self.assertEqual(len(result), 2)
        updated = result[result["Data Lectura"] == pd.Timestamp("2026-06-24 08:00:00")].iloc[0]
        self.assertEqual(updated["wind_avg_kmh"], 5)

    def test_build_daily_incremental_aggregates_wind_observations(self):
        observations = pd.DataFrame([
            observation("ES1", "2026-06-24 08:00:00", 4, 10, 350, rain=0.2),
            observation("ES1", "2026-06-24 11:00:00", 8, 18, 10, rain=0.4),
        ])

        result = build_meteoclimatic_daily_incremental(observations)
        row = result.iloc[0]

        self.assertEqual(row["Total"], 0.4)
        self.assertEqual(row["wind_avg_kmh"], 6.0)
        self.assertEqual(row["wind_min_kmh"], 4.0)
        self.assertEqual(row["wind_max_kmh"], 8.0)
        self.assertEqual(row["wind_gust_kmh"], 18.0)
        self.assertEqual(row["wind_direction_deg"], 0.0)
        self.assertEqual(row["wind_observation_count"], 2)

    def test_read_observations_keeps_location_columns_as_strings(self):
        rows = [
            observation("ES1", "2026-06-24 08:00:00", 4, 10, 350),
            observation("ES2", "2026-06-24 09:00:00", 4, 10, 350),
        ]
        rows[1]["Altitud"] = "Not set yet"
        with TemporaryDirectory() as tmp_dir:
            path = f"{tmp_dir}/observations.csv"
            pd.DataFrame(rows).to_csv(path, decimal=",", index=False)

            result = read_meteoclimatic_observations(path)

        self.assertEqual(str(result["Altitud"].dtype), "string")
        self.assertEqual(result.loc[1, "Altitud"], "Not set yet")

    def test_retention_keeps_seven_closed_local_days_plus_current(self):
        observations = pd.DataFrame([
            observation("ES1", f"2026-08-{day:02d} 12:00:00", 4, 10, 350)
            for day in range(1, 12)
        ])

        retained, metrics = retain_meteoclimatic_observations(
            observations,
            reference_day=date(2026, 8, 11),
        )

        self.assertEqual(
            set(retained["Data Local"]),
            {f"202608{day:02d}" for day in range(4, 12)},
        )
        self.assertEqual(len(retained), 8)
        self.assertEqual(metrics["cutoff_day_inclusive"], "2026-08-04")
        self.assertEqual(metrics["removed_rows"], 3)

    def test_retention_does_not_invent_missing_dates_or_zero_rows(self):
        observations = pd.DataFrame([
            observation("ES1", "2026-08-03 12:00:00", 4, 10, 350, rain=1.0),
            observation("ES1", "2026-08-04 12:00:00", 4, 10, 350, rain=2.0),
            observation("ES1", "2026-08-06 12:00:00", 4, 10, 350, rain=3.0),
            observation("ES1", "2026-08-11 12:00:00", 4, 10, 350, rain=4.0),
        ])

        retained, _metrics = retain_meteoclimatic_observations(
            observations,
            reference_day=date(2026, 8, 11),
        )

        self.assertEqual(set(retained["Data Local"]), {"20260804", "20260806", "20260811"})
        self.assertEqual(set(retained["Total"]), {2.0, 3.0, 4.0})

    def test_retained_daily_tail_matches_full_rebuild_and_old_daily_survives(self):
        observations = pd.DataFrame([
            observation("ES1", "2026-08-03 08:00:00", 2, 4, 350, rain=1.0),
            observation("ES1", "2026-08-04 08:00:00", 4, 8, 350, rain=2.0),
            observation("ES1", "2026-08-04 16:00:00", 8, 12, 10, rain=2.5),
            observation("ES1", "2026-08-11 08:00:00", 6, 9, 90, rain=3.0),
        ])
        full_daily = build_meteoclimatic_daily_incremental(observations)
        retained, _metrics = retain_meteoclimatic_observations(
            observations,
            reference_day=date(2026, 8, 11),
        )
        retained_daily = build_meteoclimatic_daily_incremental(retained)
        expected_tail = full_daily[full_daily["Data Local"] >= "20260804"].reset_index(drop=True)

        pd.testing.assert_frame_equal(retained_daily, expected_tail)
        merged = upsert_incremental(retained_daily, full_daily)
        self.assertEqual(set(merged["Data Local"]), {"20260803", "20260804", "20260811"})


if __name__ == "__main__":
    unittest.main()
