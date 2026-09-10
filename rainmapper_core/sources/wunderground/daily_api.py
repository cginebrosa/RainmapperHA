import os
from datetime import date, datetime, timedelta, timezone

import requests


DEFAULT_API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
API_URL = "https://api.weather.com/v2/pws/history/daily"
INCH_TO_MM = 25.4
SUPPORTED_CACHE_ENCODINGS = frozenset({"identity", "gzip", "deflate"})
DEFAULT_CACHE_ENCODINGS = ("gzip", "identity", "deflate")
CACHE_ENCODINGS_ENV = "RAINMAPPER_WUNDERGROUND_ENCODING_ORDER"
CACHE_STALE_AFTER_HOURS = 4


class WundergroundDailyApiError(Exception):
    pass


def cache_encodings(value=None):
    """Return one validated permutation of the supported CDN cache variants."""
    raw = (
        os.environ.get(CACHE_ENCODINGS_ENV, ",".join(DEFAULT_CACHE_ENCODINGS))
        if value is None
        else value
    )
    if isinstance(raw, str):
        encodings = tuple(part.strip().lower() for part in raw.split(","))
    else:
        encodings = tuple(str(part).strip().lower() for part in raw)
    if (
        len(encodings) != len(SUPPORTED_CACHE_ENCODINGS)
        or set(encodings) != SUPPORTED_CACHE_ENCODINGS
    ):
        raise WundergroundDailyApiError(
            "Wunderground encoding order must contain identity, gzip and deflate exactly once"
        )
    return encodings


def query_date_range(start_date: date, end_date: date, *, weekly: bool) -> tuple[date, date]:
    """Return the requested interval, capped to seven inclusive days in weekly mode."""
    if start_date > end_date:
        raise ValueError("Wunderground start date must not be after end date")
    if weekly:
        start_date = max(start_date, end_date - timedelta(days=6))
    return start_date, end_date


def station_id_from_url(weather_station_url: str) -> str:
    return weather_station_url.rstrip("/").split("/")[-1].upper()


def daily_api_key() -> str:
    return os.environ.get("RAINMAPPER_WUNDERGROUND_API_KEY", DEFAULT_API_KEY)


def _fetch_daily_observations_once(
    station_id: str,
    start_date: date,
    end_date: date,
    accept_encoding: str,
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
        response = requester.get(
            API_URL,
            params=params,
            headers={"Accept-Encoding": accept_encoding},
            timeout=timeout,
        )
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


def _observation_epoch(observation: dict):
    try:
        return float(observation.get("epoch"))
    except (TypeError, ValueError):
        pass

    utc_text = str(observation.get("obsTimeUtc") or "").strip()
    if not utc_text:
        return None
    try:
        parsed = datetime.fromisoformat(utc_text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _latest_observation_epoch(observations):
    epochs = [
        epoch
        for epoch in (_observation_epoch(observation) for observation in observations)
        if epoch is not None
    ]
    return max(epochs) if epochs else None


def _format_observation_time(epoch):
    if epoch is None:
        return "unknown"
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_daily_observations(
    station_id: str,
    start_date: date,
    end_date: date,
    session=None,
    timeout=5,
    api_key=None,
    diagnostics=None,
    now_utc=None,
    today=None,
    stale_after_hours=CACHE_STALE_AFTER_HOURS,
    encoding_order=None,
):
    """Fetch daily observations and escape stale CDN compression variants.

    Weather.com caches responses separately by ``Accept-Encoding``. For a
    request that includes today, retry alternate variants only when the latest
    observation is older than the accepted freshness window, then keep the
    response with the newest observation timestamp.
    """
    diagnostics_target = diagnostics if diagnostics is not None else {}
    current_time = now_utc or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    current_time = current_time.astimezone(timezone.utc)
    current_date = today or date.today()
    requesting_today = start_date <= current_date <= end_date
    stale_cutoff = current_time.timestamp() - (float(stale_after_hours) * 3600)
    ordered_encodings = cache_encodings(encoding_order)

    attempted_encodings = []
    retry_errors = []
    selected_observations = None
    selected_epoch = None
    selected_encoding = ordered_encodings[0]
    initial_epoch = None

    for index, accept_encoding in enumerate(ordered_encodings):
        if index > 0 and (not requesting_today or (selected_epoch is not None and selected_epoch >= stale_cutoff)):
            break
        try:
            observations = _fetch_daily_observations_once(
                station_id,
                start_date,
                end_date,
                accept_encoding,
                session=session,
                timeout=timeout,
                api_key=api_key,
            )
        except WundergroundDailyApiError as exc:
            if index == 0:
                raise
            attempted_encodings.append(accept_encoding)
            retry_errors.append(f"{accept_encoding}: {exc}")
            continue

        attempted_encodings.append(accept_encoding)
        latest_epoch = _latest_observation_epoch(observations)
        if index == 0:
            initial_epoch = latest_epoch
            selected_observations = observations
            selected_epoch = latest_epoch
            selected_encoding = accept_encoding
            continue
        if latest_epoch is not None and (selected_epoch is None or latest_epoch > selected_epoch):
            selected_observations = observations
            selected_epoch = latest_epoch
            selected_encoding = accept_encoding

    retry_attempted = len(attempted_encodings) > 1
    recovered = retry_attempted and selected_epoch is not None and (
        initial_epoch is None or selected_epoch > initial_epoch
    )
    stale_after_retries = bool(
        requesting_today and (selected_epoch is None or selected_epoch < stale_cutoff)
    )
    diagnostics_target.update({
        "cache_retry_attempted": retry_attempted,
        "cache_recovered": recovered,
        "stale_after_retries": stale_after_retries,
        "attempted_encodings": attempted_encodings,
        "selected_encoding": selected_encoding,
        "initial_observation_utc": _format_observation_time(initial_epoch),
        "selected_observation_utc": _format_observation_time(selected_epoch),
        "retry_errors": retry_errors,
    })
    return selected_observations


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
