"""Convert Rainmapper Tomap CSV files into GeoJSON for web viewers.

This module is the canonical GeoJSON entrypoint. Run it with
`python -m rainmapper_core.geojson`. Keeping the logic here lets the project
reduce root/app duplication without maintaining separate wrapper scripts.
"""

import argparse
import json
import math
import os
from datetime import date, datetime
from pathlib import Path

import pandas as pd


TOMAP_FILES = {
    "01_Tomap_Last_day.csv": "01d.geojson",
    "02_Tomap_Last_week.csv": "07d.geojson",
    "03_Tomap_Last_two_weeks.csv": "14d.geojson",
    "04_Tomap_Last_three_weeks.csv": "21d.geojson",
    "05_Tomap_Last_month.csv": "30d.geojson",
    "06_Tomap_Last_two_months.csv": "60d.geojson",
    "07_Tomap_Last_three_months.csv": "90d.geojson",
}


DEFAULT_IGNORE_STATIONS_FILE = os.environ.get(
    "RAINMAPPER_IGNORE_STATIONS_TOMAP_FILE",
    "ignore_stations_tomap.txt",
)


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def load_ignore_station_codes(ignore_stations_file):
    if not ignore_stations_file:
        return set()

    path = Path(ignore_stations_file)
    if not path.exists():
        return set()

    station_codes = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            station_codes.add(line.upper())
    return station_codes


def filter_ignored_stations(df, ignore_station_codes):
    if not ignore_station_codes:
        return df, 0

    if "Codi Estació" not in df.columns:
        print("Cannot filter ignored stations: column 'Codi Estació' is missing.")
        return df, 0

    station_codes = df["Codi Estació"].astype(str).str.strip().str.upper()
    keep_rows = ~station_codes.isin(ignore_station_codes)
    ignored_count = int((~keep_rows).sum())
    if ignored_count == 0:
        return df, 0

    return df.loc[keep_rows].copy(), ignored_count


def infer_station_source(station_code):
    code = str(station_code or "").strip().upper()
    if code.startswith("AEMET:"):
        return "AEMET"
    if code.startswith("ES") and len(code) >= 15:
        return "Meteoclimatic"
    if code.startswith("I"):
        return "Wunderground"
    if len(code) == 2:
        return "Meteocat"
    return "Unknown"


def add_station_sources(df):
    if "Codi Estació" not in df.columns:
        print("Cannot infer station sources: column 'Codi Estació' is missing.")
        return df, []

    result = df.copy()
    inferred_sources = result["Codi Estació"].apply(infer_station_source)
    if "Source" not in result.columns:
        result["Source"] = inferred_sources
    else:
        empty_source = result["Source"].isna() | (result["Source"].astype(str).str.strip() == "")
        result.loc[empty_source, "Source"] = inferred_sources.loc[empty_source]

    unknown_codes = sorted(
        {
            str(code).strip().upper()
            for code, source in zip(result["Codi Estació"], result["Source"])
            if str(source).strip().lower() == "unknown" and str(code).strip()
        }
    )
    return result, unknown_codes


def dataframe_to_geojson(df, generated_at=None):
    features = []
    for record in df.to_dict(orient="records"):
        try:
            lat = float(record.get("Latitud"))
            lon = float(record.get("Longitud"))
        except (TypeError, ValueError):
            continue

        if math.isnan(lat) or math.isnan(lon):
            continue

        properties = {
            key: clean_value(value)
            for key, value in record.items()
            if key not in ("Latitud", "Longitud")
        }
        if not properties.get("Source"):
            properties["Source"] = infer_station_source(properties.get("Codi Estació"))
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated_at": generated_at,
        },
        "features": features,
    }


def convert_file(input_file, output_file, ignore_station_codes):
    df = pd.read_csv(input_file)
    missing_columns = {"Latitud", "Longitud"} - set(df.columns)
    if missing_columns:
        raise ValueError(f"{input_file} is missing columns: {', '.join(sorted(missing_columns))}")

    df, ignored_count = filter_ignored_stations(df, ignore_station_codes)
    df, unknown_station_codes = add_station_sources(df)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    geojson = dataframe_to_geojson(
        df,
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    output_file.write_text(
        json.dumps(geojson, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    if unknown_station_codes:
        preview = ", ".join(unknown_station_codes[:20])
        suffix = "..." if len(unknown_station_codes) > 20 else ""
        print(
            f"WARNING: {input_file} has {len(unknown_station_codes)} station code(s) with unknown source: {preview}{suffix}"
        )
    return len(geojson["features"]), ignored_count


def convert_all(input_dir, output_dir, ignore_stations_file):
    ignore_station_codes = load_ignore_station_codes(ignore_stations_file)
    if ignore_station_codes:
        print(
            f"Ignoring {len(ignore_station_codes)} station code(s) from {ignore_stations_file} when generating GeoJSON."
        )

    converted = []
    for csv_name, geojson_name in TOMAP_FILES.items():
        input_file = input_dir / csv_name
        output_file = output_dir / geojson_name
        if not input_file.exists():
            print(f"Skipping missing Tomap file: {input_file}")
            continue

        feature_count, ignored_count = convert_file(input_file, output_file, ignore_station_codes)
        converted.append(output_file)
        ignored_text = f", ignored {ignored_count} station(s)" if ignored_count else ""
        print(f"Generated {output_file} with {feature_count} station(s){ignored_text}")

    return converted


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Rainmapper Tomap CSV files to mobile-friendly GeoJSON files."
    )
    parser.add_argument(
        "--input-dir",
        default="Tomap",
        help="Directory containing Tomap CSV files. Default: Tomap",
    )
    parser.add_argument(
        "--output-dir",
        default="PublicData",
        help="Directory where GeoJSON files will be written. Default: PublicData",
    )
    parser.add_argument(
        "--ignore-stations-file",
        default=DEFAULT_IGNORE_STATIONS_FILE,
        help=(
            "Text file with one station code per line to ignore when generating GeoJSON. "
            "Empty lines and lines starting with # are ignored."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    converted = convert_all(input_dir, output_dir, args.ignore_stations_file)

    if not converted:
        raise SystemExit("No GeoJSON files were generated.")


if __name__ == "__main__":
    main()
