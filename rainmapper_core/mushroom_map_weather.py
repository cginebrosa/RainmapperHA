"""Bounded observed-weather adapter for a map point; no forecasts or writes."""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from rainmapper_core import mushroom_observation_context as context
from rainmapper_core import mushroom_weather_idw as idw
from rainmapper_core.weather_history_dataset import resolve_weather_generation

CHANNELS = {
    "rain_mm": "daily_rain_idw_mm",
    "temp_min_c": "daily_temp_min_idw_c",
    "temp_max_c": "daily_temp_max_idw_c",
    "humidity_min_pct": "daily_humidity_min_idw_pct",
    "humidity_max_pct": "daily_humidity_max_idw_pct",
}
COUNTS = {key: value.rsplit("_", 1)[0]+"_station_count" for key,value in CHANNELS.items()}
COUNTS["rain_mm"] = "daily_rain_station_count"
MAX_STATIONS = 256
MAX_RESULT_BYTES = 32 * 1024
COLUMNS = ["source", "station_code", "station_name", "local_date", "lat", "lon", "altitude",
           "rain_mm", "min_temp_celsius", "max_temp_celsius", "min_humidity_percent",
           "max_humidity_percent", "wind_avg_kmh", "wind_gust_kmh"]


def map_today(calendar_timezone="Europe/Madrid"):
    """Map calendar day, independent of the executor/container operating timezone.

    The administrator-owned map configuration supplies the same calendar to all
    readers. A selected prediction date never substitutes for the actual clock.
    """
    return datetime.now(ZoneInfo(calendar_timezone)).date()


def finite(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def fingerprint(path):
    stat = Path(path).stat()
    return stat.st_size, stat.st_mtime_ns


class PointWeatherReader:
    """Resident reader; caller serializes requests. One generation per result."""

    def __init__(self, data_root: str, stations_file: str, *, calendar_timezone="Europe/Madrid"):
        ZoneInfo(calendar_timezone)  # Fail on invalid configuration before reading data.
        self.calendar_timezone = calendar_timezone
        self.data_root, self.stations_file = Path(data_root), Path(stations_file)
        self._identity = None
        self._cache = OrderedDict()
        self.last_metrics = {}

    def _refresh(self):
        import pyarrow.parquet as pq

        current = self.data_root/"weather-history/CURRENT.json"
        identity = (fingerprint(current), fingerprint(self.stations_file))
        if identity == self._identity:
            return
        generation = resolve_weather_generation(self.data_root, verify_hashes=False)
        if generation.catalog.rows > 10000 or generation.catalog.size_bytes > 4 * 1024 * 1024:
            raise ValueError("weather_catalog_limit")
        catalog_path = generation.object_path(generation.catalog.path)
        catalog = pq.ParquetFile(catalog_path).read(
            columns=["source","station_code","station_name","lat","lon","altitude"], use_threads=False).to_pylist()
        if len(catalog) != generation.catalog.rows:
            raise ValueError("weather_catalog_mismatch")
        if self.stations_file.stat().st_size > 1024 * 1024:
            raise ValueError("weather_station_file_limit")
        self.disabled = idw.disabled_wunderground_station_keys(self.stations_file)
        self.generation, self.catalog = generation, catalog
        self._catalog_path, self._catalog_stat = catalog_path, fingerprint(catalog_path)
        self._cache.clear()
        self._identity = identity

    def _nearby(self, lat, lon):
        nearby = {}
        for row in self.catalog:
            key = (row["source"], row["station_code"])
            y, x = finite(row["lat"]), finite(row["lon"])
            if y is None or x is None or not (-90 <= y <= 90 and -180 <= x <= 180):
                continue
            if (str(key[0]).lower(), str(key[1]).upper()) in self.disabled:
                continue
            distance = context.haversine_km(lat, lon, y, x)
            if distance <= idw.RAINFALL_IDW_RADIUS_KM:
                nearby[key] = row
                if len(nearby) > MAX_STATIONS:
                    raise ValueError("weather_station_limit")
        return nearby

    def _load(self, nearby, start, end, *, max_days=61):
        import pyarrow.dataset as ds

        stations, checks = {}, {self._catalog_path: self._catalog_stat}
        count = 0
        first, last = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
        for partition in self.generation.partitions:
            codes = [key[1] for key in nearby if key[0] == partition.source]
            if not codes or partition.max_local_date < first or partition.min_local_date > last:
                continue
            path = self.generation.object_path(partition.path)
            signature = fingerprint(path)
            if signature[0] != partition.size_bytes:
                raise ValueError("weather_partition_changed")
            checks[path] = signature
            dataset = ds.dataset(path, format="parquet")
            scanner = dataset.scanner(columns=COLUMNS, filter=(ds.field("station_code").isin(codes) &
                (ds.field("local_date") >= first) & (ds.field("local_date") <= last)),
                batch_size=1024, batch_readahead=0, fragment_readahead=0, use_threads=False)
            for batch in scanner.to_batches():
                count += batch.num_rows
                if count > len(nearby) * max_days:
                    raise ValueError("weather_row_limit")
                for row in batch.to_pylist():
                    key = (row["source"], row["station_code"])
                    if key not in nearby:
                        raise ValueError("weather_source_mismatch")
                    day = date.fromisoformat(row["local_date"])
                    if key not in stations:
                        y, x = finite(row["lat"]), finite(row["lon"])
                        if y is None or x is None or not (-90 <= y <= 90 and -180 <= x <= 180):
                            continue
                        altitude = finite(row["altitude"])
                        stations[key] = context.WeatherStation(row["source"], row["station_code"], row["station_name"] or "",
                            y, x, {}, altitude if altitude is not None else finite(nearby[key]["altitude"]))
                    station = stations[key]
                    if day in station.records_by_day:
                        raise ValueError("duplicate_weather_station_day")
                    station.records_by_day[day] = context.DailyWeatherRecord(
                        station.source, station.station_code, row["station_name"] or "", day, station.lat, station.lon,
                        finite(row["rain_mm"]), finite(row["max_temp_celsius"]), finite(row["min_temp_celsius"]),
                        finite(row["max_humidity_percent"]), finite(row["min_humidity_percent"]),
                        finite(row["wind_avg_kmh"]), finite(row["wind_gust_kmh"]), None)
        self._check_files(checks)
        return stations, checks, count

    @staticmethod
    def _check_files(checks):
        if any(fingerprint(path) != signature for path,signature in checks.items()):
            raise ValueError("weather_input_changed")

    def prepare_model_inputs(self, lat, lon, altitude_m, *, end_day: date,
                             lookback_days: int, include_physical_state: bool,
                             soilgrids_context=None, calendar_timezone=None):
        """Prepare one ephemeral point through the EXISTING area runtime.

        Internal executor input, not a browser response or a prediction. The
        caller supplies the installed profile's lookback and temporal cutoff,
        retains this once per request and must separately validate applicability.
        """
        from rainmapper_core import mushroom_ml_area_weather_runtime as runtime
        from rainmapper_core import mushroom_ml_biology_v3 as biology
        from rainmapper_core.mushroom_soilgrids import canonical_sha256

        started = time.perf_counter()
        if type(lookback_days) is not int or not 1 <= lookback_days <= 365:
            raise ValueError("invalid_model_weather_days")
        if type(include_physical_state) is not bool:
            raise ValueError("invalid_model_physical_state")
        if type(end_day) is not date or end_day >= map_today(calendar_timezone or self.calendar_timezone):
            raise ValueError("invalid_model_weather_cutoff")
        for value, limit in ((lat,90),(lon,180)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>limit:
                raise ValueError("invalid_point")
        altitude_m = finite(altitude_m)
        if soilgrids_context is not None and (
            not isinstance(soilgrids_context,dict)
            or soilgrids_context.get("contract_id") != "point_soilgrids_water_context_v1"
            or soilgrids_context.get("source",{}).get("spatial_support") != "native_cell"
        ):
            raise ValueError("invalid_point_soil_context")
        self._refresh()
        self._check_files({self._catalog_path:self._catalog_stat})
        nearby = self._nearby(lat,lon)
        stations,checks,count = self._load(nearby,end_day-timedelta(days=lookback_days),end_day,
                                          max_days=lookback_days+1)
        point_id = "map-point:"+canonical_sha256({"lat":lat,"lon":lon,"altitude_m":altitude_m,
            "generation":self.generation.generation_id,"soil":soilgrids_context})
        area = biology.AreaPredictionContext(area_id=point_id,lat=lat,lon=lon,altitude_m=altitude_m,
            location_source="map_query_point",altitude_source="point_dem_cell" if altitude_m is not None else None)
        point = biology.MicroAreaContext(micro_area_id=point_id,area_id=point_id,lat=lat,lon=lon,
            location_source=area.location_source,altitude_m=altitude_m,altitude_source=area.altitude_source,
            soilgrids_water=soilgrids_context)
        series = runtime.materialize_area_series(area_id=point_id,end_day=end_day,days=lookback_days,
            microareas_by_area={point_id:[point]},stations=stations,excluded_station_keys=self.disabled,
            include_physical_state=include_physical_state)
        self._check_files(checks)
        self.last_metrics = {"station_count":len(nearby),"rows_loaded":count,
            "lookback_days":lookback_days,"cutoff_date":end_day.isoformat(),
            "generation_id":self.generation.generation_id,
            "elapsed_ms":round((time.perf_counter()-started)*1000,3)}
        return area,series,stations

    def lookup(self, lat, lon, altitude_m, *, end_day: date, days: int = 60):
        start_time = time.perf_counter()
        if type(days) is not int or days not in (7, 15, 30, 60):
            raise ValueError("invalid_weather_days")
        for value, limit in ((lat,90),(lon,180)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>limit:
                raise ValueError("invalid_point")
        altitude_m = finite(altitude_m)
        self._refresh()
        self._check_files({self._catalog_path:self._catalog_stat})
        key = (lat,lon,altitude_m,end_day,days)
        if key in self._cache:
            result,checks = self._cache[key]
            self._check_files(checks)
            self._cache.move_to_end(key)
            self.last_metrics = {"cache_hit":True,"elapsed_ms":round((time.perf_counter()-start_time)*1000,3)}
            return deepcopy(result)
        nearby = self._nearby(lat,lon)
        stations,checks,row_count = self._load(nearby,end_day-timedelta(days=days),end_day)
        interpolated = idw.build_daily_weather_idw_series(stations, target_lat=lat,target_lon=lon,
            target_altitude_m=altitude_m,end_day=end_day,days=days,excluded_station_keys=self.disabled)
        series = {key: interpolated[field] for key,field in CHANNELS.items()}
        usable = sum(value is not None for values in series.values() for value in values)
        result = {"status":"available" if usable == 5*days else "partial" if usable else "no_data",
            "data_mode":"observed_idw", "history_days":days,"cutoff_date":end_day.isoformat(),
            "dates":interpolated["daily_dates"],"series":series,
            "station_counts":{key:interpolated[field] for key,field in COUNTS.items()},
            "rain_imputed_zero_counts":interpolated["daily_rain_imputed_duplicate_zero_station_count"],
            "generation_id":self.generation.generation_id,"radius_km":idw.RAINFALL_IDW_RADIUS_KM,
            "rainfall_contract_id":idw.RAINFALL_IDW_CONTRACT_ID,"weather_contract_id":idw.WEATHER_IDW_CONTRACT_ID,
            "sources":sorted({key[0] for key in stations}),"nearby_stations":len(nearby)}
        dates = [date.fromisoformat(day) for day in result["dates"]]
        for station in sorted(stations.values(),key=lambda s:(context.haversine_km(lat,lon,s.lat,s.lon),s.source,s.station_code)):
            distance = context.haversine_km(lat,lon,station.lat,station.lon)
            if distance > idw.RAINFALL_IDW_RADIUS_KM:
                continue
            def wind(metric):
                values = [getattr(station.records_by_day.get(day),metric,None) for day in dates]
                return [value if value is not None and value >= 0 else None for value in values]
            average,gust = wind("wind_avg_kmh"),wind("wind_gust_kmh")
            if any(value is not None for value in average+gust):
                result["wind"] = {"station_name":station.station_name,"source":station.source,
                    "station_code":station.station_code,"distance_km":round(distance,2),"avg_kmh":average,"gust_kmh":gust}
                break
        raw = json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()
        if len(raw)>MAX_RESULT_BYTES:
            raise ValueError("weather_result_limit")
        self._cache[key] = (result,checks)
        if len(self._cache)>4:
            self._cache.popitem(last=False)
        self.last_metrics = {"cache_hit":False,"station_count":len(nearby),"rows_loaded":row_count,
            "result_bytes":len(raw),"elapsed_ms":round((time.perf_counter()-start_time)*1000,3)}
        return deepcopy(result)
