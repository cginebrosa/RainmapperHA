import os
from datetime import date

import requests


DEFAULT_API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
API_URL = "https://api.weather.com/v2/pws/history/daily"
INCH_TO_MM = 25.4


class WundergroundDailyApiError(Exception):
    pass


def station_id_from_url(weather_station_url: str) -> str:
    return weather_station_url.rstrip("/").split("/")[-1].upper()


def daily_api_key() -> str:
    return os.environ.get("RAINMAPPER_WUNDERGROUND_API_KEY", DEFAULT_API_KEY)


def fetch_daily_observations(
    station_id: str,
    start_date: date,
    end_date: date,
    session=None,
    timeout=5,
    api_key=None,
):
    requester = session or requests
    params = {
        "stationId": station_id.upper(),
        "format": "json",
        "units": "e",
        "startDate": start_date.strftime("%Y%m%d"),
        "endDate": end_date.strftime("%Y%m%d"),
        "numericPrecision": "decimal",
        "apiKey": api_key or daily_api_key(),
    }
    try:
        response = requester.get(API_URL, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise WundergroundDailyApiError(str(exc)) from exc

    if response.status_code != 200:
        raise WundergroundDailyApiError(f"HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise WundergroundDailyApiError("invalid JSON response") from exc

    observations = payload.get("observations")
    if not observations:
        raise WundergroundDailyApiError("empty observations")
    return observations


def imperial_to_metric(observation: dict) -> dict:
    imperial = observation.get("imperial") or {}
    return {
        "temp_high_c": fahrenheit_to_celsius(imperial.get("tempHigh")),
        "temp_avg_c": fahrenheit_to_celsius(imperial.get("tempAvg")),
        "temp_low_c": fahrenheit_to_celsius(imperial.get("tempLow")),
        "dew_high_c": fahrenheit_to_celsius(imperial.get("dewptHigh")),
        "dew_avg_c": fahrenheit_to_celsius(imperial.get("dewptAvg")),
        "dew_low_c": fahrenheit_to_celsius(imperial.get("dewptLow")),
        "humidity_high": number_or_na(observation.get("humidityHigh")),
        "humidity_avg": number_or_na(observation.get("humidityAvg")),
        "humidity_low": number_or_na(observation.get("humidityLow")),
        "speed_high_kmh": mph_to_kmh(imperial.get("windspeedHigh")),
        "speed_avg_kmh": mph_to_kmh(imperial.get("windspeedAvg")),
        "speed_low_kmh": mph_to_kmh(imperial.get("windspeedLow")),
        "pressure_high_hpa": inhg_to_hpa(imperial.get("pressureMax")),
        "pressure_low_hpa": inhg_to_hpa(imperial.get("pressureMin")),
        "rain_mm": inch_to_mm(imperial.get("precipTotal")),
    }


def observation_date(observation: dict) -> str:
    local_time = observation.get("obsTimeLocal") or ""
    if len(local_time) >= 10:
        return local_time[:10]
    raise WundergroundDailyApiError("observation without local date")


def build_monthly_rows(
    observations,
    station_id,
    station_name,
    location_name,
    elevation,
    latitude,
    longitude,
):
    rows = []
    for observation in observations:
        metrics = imperial_to_metric(observation)
        rows.append({
            "StationID": station_id,
            "Date": observation_date(observation),
            "Time": "02:00:01",
            "StationName": station_name,
            "Comarca": "Not set yet",
            "Municipi": location_name,
            "Provincia": "Not set yet",
            "Elevation": elevation,
            "Latitude": latitude,
            "Longitude": longitude,
            "High": metrics["temp_high_c"],
            "Avg": metrics["temp_avg_c"],
            "Low": metrics["temp_low_c"],
            "High_1": metrics["dew_high_c"],
            "Avg_1": metrics["dew_avg_c"],
            "Low_1": metrics["dew_low_c"],
            "High_2": metrics["humidity_high"],
            "Avg_2": metrics["humidity_avg"],
            "Low_2": metrics["humidity_low"],
            "High_3": metrics["speed_high_kmh"],
            "Avg_3": metrics["speed_avg_kmh"],
            "Low_3": metrics["speed_low_kmh"],
            "High_4": metrics["pressure_high_hpa"],
            "Low_4": metrics["pressure_low_hpa"],
            "Sum": metrics["rain_mm"],
        })
    return rows


def number_or_na(value):
    if value is None:
        return "NA"
    return round(float(value), 2)


def fahrenheit_to_celsius(value):
    if value is None:
        return "NA"
    return round((float(value) - 32) * 5 / 9, 2)


def mph_to_kmh(value):
    if value is None:
        return "NA"
    return round(float(value) * 1.609, 2)


def inhg_to_hpa(value):
    if value is None:
        return "NA"
    return round(float(value) * 33.86389, 2)


def inch_to_mm(value):
    if value is None:
        return "NA"
    return round(float(value) * INCH_TO_MM, 2)
