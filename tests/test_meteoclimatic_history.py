import unittest

import pandas as pd

from rainmapper_core.meteoclimatic_history import (
    build_meteoclimatic_daily_incremental,
    update_meteoclimatic_observations,
)


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


if __name__ == "__main__":
    unittest.main()
