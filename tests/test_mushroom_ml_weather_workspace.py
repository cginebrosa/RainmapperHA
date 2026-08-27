import unittest
from datetime import date, timedelta
from pathlib import Path

from rainmapper_core import mushroom_ml_biology_v3 as biology_v3
from rainmapper_core import mushroom_ml_weather_workspace as workspace_module
from rainmapper_core import mushroom_observation_context as weather_context
from rainmapper_core import mushroom_weather_idw


class OperationalWeatherWorkspaceTests(unittest.TestCase):
    def station(
        self,
        code: str,
        records: dict[date, float],
    ) -> weather_context.WeatherStation:
        return weather_context.WeatherStation(
            source="test",
            station_code=code,
            station_name=code,
            lat=0.0,
            lon=0.0,
            altitude_m=500.0,
            records_by_day={
                day: weather_context.DailyWeatherRecord(
                    source="test",
                    station_code=code,
                    station_name=code,
                    day=day,
                    lat=0.0,
                    lon=0.0,
                    rain_mm=rain,
                    temp_max_c=20.0,
                    temp_min_c=10.0,
                    humidity_max_pct=80.0,
                    humidity_min_pct=50.0,
                    wind_avg_kmh=None,
                    wind_gust_kmh=None,
                    wind_direction_deg=None,
                )
                for day, rain in records.items()
            },
        )

    def workspace(
        self, stations: dict[tuple[str, str], weather_context.WeatherStation]
    ) -> workspace_module.OperationalWeatherWorkspace:
        first = min(day for station in stations.values() for day in station.records_by_day)
        last = max(day for station in stations.values() for day in station.records_by_day)
        workspace = object.__new__(workspace_module.OperationalWeatherWorkspace)
        workspace.data_dir = Path("/test/weather")
        workspace.known_sites = Path("/test/sites.json")
        workspace.stations_file = Path("/test/stations.txt")
        workspace.start_day = first
        workspace.end_day = last
        workspace.days = (last - first).days + 1
        workspace.disabled = frozenset()
        workspace.stations = stations
        workspace.duplicate_dates = {
            key: mushroom_weather_idw.suppressed_rain_dates(station)
            for key, station in stations.items()
        }
        workspace._station_views = {}
        workspace._weather_base = {}
        workspace._eto_base = {}
        workspace._weather_views = {}
        workspace._soil = {}
        workspace.series_built = 0
        workspace.series_reused = 0
        workspace.view_reused = 0
        return workspace

    def test_maximum_series_view_exactly_matches_direct_range(self) -> None:
        first = date(2026, 8, 1)
        days = [first + timedelta(days=offset) for offset in range(4)]
        stations = {
            ("test", "A"): self.station(
                "A", {days[0]: 5.0, days[1]: 5.0, days[2]: 5.0, days[3]: 1.0}
            ),
            ("test", "ONLY_BEFORE"): self.station("ONLY_BEFORE", {days[0]: 2.0}),
        }
        workspace = self.workspace(stations)
        context = biology_v3.MicroAreaContext(
            micro_area_id="micro-1",
            area_id="area-1",
            lat=0.0,
            lon=0.0,
            location_source="test",
            altitude_m=500.0,
        )

        shared = workspace.weather_for_contexts(
            [context], start_day=days[1], end_day=days[3]
        )[context.micro_area_id]
        view_stations = workspace.stations_for_view(days[1], days[3])
        direct = mushroom_weather_idw.build_daily_weather_idw_series(
            view_stations,
            target_lat=context.lat,
            target_lon=context.lon,
            target_altitude_m=context.altitude_m,
            end_day=days[3],
            days=3,
            duplicate_dates_by_station={
                key: mushroom_weather_idw.suppressed_rain_dates(station)
                for key, station in view_stations.items()
            },
        )

        self.assertEqual(shared, direct)
        self.assertEqual(workspace.series_built, 1)

    def test_one_base_is_reused_across_contract_views(self) -> None:
        first = date(2026, 8, 1)
        days = [first + timedelta(days=offset) for offset in range(5)]
        stations = {
            ("test", "A"): self.station(
                "A", {day: float(index) for index, day in enumerate(days)}
            )
        }
        workspace = self.workspace(stations)
        context = biology_v3.MicroAreaContext(
            micro_area_id="micro-1",
            area_id="area-1",
            lat=0.0,
            lon=0.0,
            location_source="test",
            altitude_m=500.0,
        )

        workspace.weather_for_contexts(
            [context], start_day=days[0], end_day=days[3]
        )
        workspace.weather_for_contexts(
            [context], start_day=days[1], end_day=days[4]
        )

        self.assertEqual(workspace.series_built, 1)
        self.assertEqual(workspace.series_reused, 1)

    def test_soil_bundle_is_shared_by_area_cutoff_identity(self) -> None:
        day = date(2026, 8, 1)
        workspace = self.workspace({("test", "A"): self.station("A", {day: 0.0})})
        bundle = workspace_module.AreaSoilBundle(
            aggregated={"predictive_features": {"soil": 0.5}},
            daily_fraction_mean=[0.5],
        )
        workspace.store_soil_bundle(
            workspace_module.DEFAULT_SOIL_VARIANT_ID, "area-1", day, bundle
        )

        self.assertIs(
            workspace.soil_bundle(
                workspace_module.DEFAULT_SOIL_VARIANT_ID, "area-1", day
            ),
            bundle,
        )


if __name__ == "__main__":
    unittest.main()
