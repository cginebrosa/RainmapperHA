"""Bounded official-source adapters used by automatic gap repair."""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Callable, Mapping

import pandas as pd

from rainmapper_core.create_aemet import (
    AEMET_STATION_PREFIX,
    DAILY_COLUMNS,
    fetch_json,
    first_non_empty,
    parse_optional_float,
)
from rainmapper_core.sources.sodapy_local import Socrata


MAX_BACKFILL_DAYS = 15
AEMET_DAILY_URL_TEMPLATE = (
    "https://opendata.aemet.es/opendata/api/valores/climatologicos/diarios/datos/"
    "fechaini/{start}T00:00:00UTC/fechafin/{end}T23:59:59UTC/todasestaciones"
)
AEMET_DATASET_LABEL = "daily climatology"
METEOCAT_DOMAIN = "analisi.transparenciacatalunya.cat"
METEOCAT_DATASET = "nzvn-apee"


def validate_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError("Official weather backfill start must not be after end")
    if (end - start).days + 1 > MAX_BACKFILL_DAYS:
        raise ValueError("Official weather backfill blocks cannot exceed 15 days")


def parse_aemet_precipitation(value: Any) -> float | Any:
    if value is None or pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    if text.lower() in {"ip", "tr"}:
        return 0.0
    return parse_optional_float(text)


def _station_lookup(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if frame is None or frame.empty:
        return {}
    return {
        str(row.get("Codi Estació") or "").strip(): row
        for row in frame.to_dict("records")
        if str(row.get("Codi Estació") or "").strip()
    }


def normalize_aemet_climatology(
    rows: list[Mapping[str, Any]],
    station_catalog: pd.DataFrame,
) -> pd.DataFrame:
    stations = _station_lookup(station_catalog)
    output: list[dict[str, Any]] = []
    for raw in rows:
        station_id = str(raw.get("indicativo") or "").strip()
        day_text = str(raw.get("fecha") or "").strip()
        if not station_id or not day_text:
            continue
        try:
            day = date.fromisoformat(day_text)
        except ValueError:
            continue
        rain = parse_aemet_precipitation(raw.get("prec"))
        values = {
            "max_temp_celsius": parse_optional_float(raw.get("tmax")),
            "min_temp_celsius": parse_optional_float(raw.get("tmin")),
            "max_humidity_percent": parse_optional_float(raw.get("hrMax")),
            "min_humidity_percent": parse_optional_float(raw.get("hrMin")),
        }
        if pd.isna(rain) and all(pd.isna(value) for value in values.values()):
            continue
        code = f"{AEMET_STATION_PREFIX}{station_id}"
        station = stations.get(code, {})
        output.append(
            {
                "Codi Estació": code,
                "Data Lectura": f"{day.isoformat()} 23:59:00",
                "Estació": first_non_empty(station.get("Estació"), raw.get("nombre")),
                "Comarca": first_non_empty(station.get("Comarca")),
                "Municipi": first_non_empty(station.get("Municipi")),
                "Provincia": first_non_empty(station.get("Provincia"), raw.get("provincia")),
                "Altitud": first_non_empty(station.get("Altitud")),
                "Latitud": first_non_empty(station.get("Latitud")),
                "Longitud": first_non_empty(station.get("Longitud")),
                "Ultima Lectura": day.strftime("%Y/%m/%d 23:59:00"),
                "Variable": "Precipitacion",
                "Total": round(float(rain), 1) if not pd.isna(rain) else pd.NA,
                "Unitat": "mm",
                "Data Local": day.strftime("%Y%m%d"),
                "Hora Local": "23:59:00",
                **values,
            }
        )
    if not output:
        return pd.DataFrame(columns=DAILY_COLUMNS)
    frame = pd.DataFrame(output)
    for column in DAILY_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return (
        frame[DAILY_COLUMNS]
        .drop_duplicates(["Codi Estació", "Data Local"], keep="last")
        .sort_values(["Codi Estació", "Data Local"], ascending=[True, False])
        .reset_index(drop=True)
    )


def fetch_aemet_climatology(
    start: date,
    end: date,
    *,
    api_key: str,
    timeout: int = 60,
    fetcher: Callable[..., Any] = fetch_json,
) -> list[Mapping[str, Any]]:
    validate_range(start, end)
    if not api_key:
        raise ValueError("AEMET API key is required for automatic gap repair")
    url = AEMET_DAILY_URL_TEMPLATE.format(start=start.isoformat(), end=end.isoformat())
    index = fetcher(
        url,
        api_key=api_key,
        timeout=timeout,
        request_label=f"AEMET {AEMET_DATASET_LABEL} index",
    )
    if int(index.get("estado", 0)) != 200 or not index.get("datos"):
        raise RuntimeError(f"AEMET did not return a climatology data URL: {index}")
    payload = fetcher(
        index["datos"],
        timeout=timeout,
        request_label=f"AEMET {AEMET_DATASET_LABEL} data",
    )
    if not isinstance(payload, list):
        raise RuntimeError("AEMET climatology response is not a list")
    return payload


def meteocat_query(kind: str, start: date, end: date) -> str:
    validate_range(start, end)
    start_text = f"{start.isoformat()}T00:00:00.000"
    end_text = f"{end.isoformat()}T23:59:59.999"
    if kind == "rain":
        return (
            "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, "
            "codi_variable, sum(valor_lectura) as valor_variable "
            f"WHERE (data_lectura BETWEEN '{start_text}' AND '{end_text}') "
            "AND codi_variable in ('35') AND valor_lectura >= 0 "
            "GROUP BY codi_estacio, codi_variable, ultima_lectura "
            "ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"
        )
    if kind != "conditions":
        raise ValueError(f"Unknown Meteocat query kind: {kind}")
    return (
        "SELECT codi_estacio, date_trunc_ymd(data_lectura) as ultima_lectura, "
        "codi_variable, max(valor_lectura) as max_valor_variable, "
        "min(valor_lectura) as min_valor_variable "
        f"WHERE (data_lectura BETWEEN '{start_text}' AND '{end_text}') "
        "AND codi_variable in ('40','42','3','44') "
        "GROUP BY codi_estacio, codi_variable, ultima_lectura "
        "ORDER BY ultima_lectura, codi_estacio ASC LIMIT 200000"
    )


def fetch_meteocat_block(
    start: date,
    end: date,
    *,
    timeout: int = 90,
    attempts: int = 3,
    pause_seconds: float = 5.0,
    client: Any | None = None,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    validate_range(start, end)
    owns_client = client is None
    client = client or Socrata(METEOCAT_DOMAIN, None, timeout=timeout)
    results: dict[str, list[Mapping[str, Any]]] = {}
    try:
        for index, kind in enumerate(("rain", "conditions")):
            failure: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    payload = client.get(
                        METEOCAT_DATASET,
                        query=meteocat_query(kind, start, end),
                        exclude_system_fields="true",
                    )
                    if not isinstance(payload, list):
                        raise RuntimeError("Meteocat response is not a list")
                    if len(payload) >= 200_000:
                        raise RuntimeError("Meteocat response reached LIMIT 200000")
                    results[kind] = payload
                    break
                except Exception as exc:
                    failure = exc
                    if attempt < attempts:
                        time.sleep(min(5 * attempt, 30))
            if kind not in results:
                raise RuntimeError(f"Meteocat {kind} repair failed: {failure}")
            if index == 0 and pause_seconds > 0:
                time.sleep(pause_seconds)
    finally:
        if owns_client:
            client.close()
    return results["rain"], results["conditions"]


def normalize_meteocat_block(
    rain_rows: list[Mapping[str, Any]],
    condition_rows: list[Mapping[str, Any]],
    station_catalog: pd.DataFrame,
) -> pd.DataFrame:
    stations = _station_lookup(station_catalog)
    daily: dict[tuple[str, str], dict[str, Any]] = {}
    for kind, rows in (("rain", rain_rows), ("conditions", condition_rows)):
        for raw in rows:
            station_code = str(raw.get("codi_estacio") or "").strip()
            day = str(raw.get("ultima_lectura") or "")[:10]
            if not station_code or len(day) != 10:
                continue
            values = daily.setdefault((station_code, day), {})
            code = str(raw.get("codi_variable") or "")
            if kind == "rain" and code == "35":
                values["Total"] = raw.get("valor_variable")
            elif code == "40":
                values["max_temp_celsius"] = raw.get("max_valor_variable")
            elif code == "42":
                values["min_temp_celsius"] = raw.get("min_valor_variable")
            elif code == "3":
                values["max_humidity_percent"] = raw.get("max_valor_variable")
            elif code == "44":
                values["min_humidity_percent"] = raw.get("min_valor_variable")
    output: list[dict[str, Any]] = []
    for (station_code, day), values in sorted(daily.items()):
        if not any(pd.notna(value) for value in values.values()):
            continue
        station = stations.get(station_code, {})
        output.append(
            {
                "Codi Estació": station_code,
                "Data Lectura": f"{day} 02:00:01",
                "Estació": station.get("Estació", station_code),
                "Comarca": station.get("Comarca", ""),
                "Municipi": station.get("Municipi", ""),
                "Provincia": station.get("Provincia", ""),
                "Altitud": station.get("Altitud", ""),
                "Latitud": station.get("Latitud", ""),
                "Longitud": station.get("Longitud", ""),
                "Ultima Lectura": f"{day.replace('-', '/')} 02:00:01",
                "Variable": "Precipitació",
                "Total": values.get("Total"),
                "Unitat": "mm",
                "Data Local": day.replace("-", ""),
                "Hora Local": "02:00:01",
                **values,
            }
        )
    return pd.DataFrame(output)
